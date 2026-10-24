"""Bộ dịch phương ngữ SQLite → PostgreSQL cho lõi V12 (V13 bước 5, phương án C — anh chốt 17/10/2026).

Lõi V12 viết SQL cho SQLite. Khi engine = postgres, mọi câu đi qua đây **trước khi** chạy:
- DML: ``?`` → ``%s`` (``%`` chữ → ``%%``), ``INSERT OR IGNORE`` → ``INSERT … ON CONFLICT DO NOTHING``,
  ``BEGIN IMMEDIATE`` → ``BEGIN``, ``LIKE`` → ``ILIKE`` (SQLite so khớp không phân biệt hoa/thường ASCII),
  ``MAX(a,b)``/``MIN(a,b)`` hai đối số → ``GREATEST``/``LEAST``; ``PRAGMA`` → bỏ (trả None).
- DDL (migration của database.py / feature_migrations.py): kiểu cột SQLite → PostgreSQL, ``INTEGER PRIMARY KEY``
  → identity, ``TEXT`` → ``text COLLATE "C"`` (thứ tự byte như SQLite), mọi bảng thêm cột cuối ``rowid`` identity
  (SQLite có rowid ẩn; lõi/test dùng ``ORDER BY rowid``; ket_noi ẩn cột này khỏi kết quả), trigger
  ``knowledge_epoch_*`` viết lại bằng plpgsql.
- ``json_extract(...)`` và phép so sánh ``text = số`` được giữ nguyên nhờ hàm/operator tạo trong schema
  (xem ``BOOT_STRAP``); ``rowid`` giữ nguyên vì chỉ dùng trên ``attempts``.

Chỉ xử lý chuỗi; không mở kết nối. Có test riêng (tests/test_ket_noi.py) không cần PostgreSQL.
"""

from __future__ import annotations

import re
from functools import lru_cache

# --- tách chuỗi ký tự khỏi mã SQL ---------------------------------------------------------------

def _segments(sql: str):
    """Trả về danh sách (is_code, text). Chuỗi '...' (có '' thoát) và "..." là is_code=False."""
    out, i, n, start = [], 0, len(sql), 0
    while i < n:
        ch = sql[i]
        if ch in ("'", '"'):
            if i > start:
                out.append((True, sql[start:i]))
            j = i + 1
            while j < n:
                if sql[j] == ch:
                    if ch == "'" and j + 1 < n and sql[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            out.append((False, sql[i:j + 1]))
            i = j + 1
            start = i
            continue
        if ch == "/" and i + 1 < n and sql[i + 1] == "*":  # chú thích khối (review #13)
            j = sql.find("*/", i + 2)
            j = n if j < 0 else j + 2
            if i > start:
                out.append((True, sql[start:i]))
            out.append((False, sql[i:j]))
            i = j
            start = i
            continue
        if ch == "-" and i + 1 < n and sql[i + 1] == "-":  # chú thích đến hết dòng
            j = sql.find("\n", i)
            j = n if j < 0 else j
            if i > start:
                out.append((True, sql[start:i]))
            out.append((False, sql[i:j]))
            i = j
            start = i
            continue
        i += 1
    if start < n:
        out.append((True, sql[start:]))
    return out


def _map_code(sql: str, fn) -> str:
    return "".join(fn(text) if is_code else text for is_code, text in _segments(sql))


# --- MAX/MIN hai đối số --------------------------------------------------------------------------

def _two_arg_minmax(sql: str) -> str:
    """Đổi MAX(a,b)/MIN(a,b) (có dấu phẩy ở mức ngoài cùng) thành GREATEST/LEAST; MAX(col) giữ nguyên."""
    segs = _segments(sql)
    text = "".join(t for _, t in segs)
    code_mask = []
    for is_code, t in segs:
        code_mask.extend([is_code] * len(t))
    result, i, n = [], 0, len(text)
    pattern = re.compile(r"\b(MAX|MIN)\s*\(", re.IGNORECASE)
    while i < n:
        m = pattern.search(text, i)
        if not m or not code_mask[m.start()]:
            if m and not code_mask[m.start()]:
                result.append(text[i:m.end()])
                i = m.end()
                continue
            result.append(text[i:])
            break
        # tìm ngoặc đóng tương ứng, chỉ đếm ở phần mã
        depth, j, top_comma = 1, m.end(), False
        while j < n and depth:
            c = text[j]
            if code_mask[j]:
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                elif c == "," and depth == 1:
                    top_comma = True
            j += 1
        name = m.group(1).upper()
        replacement = ("GREATEST(" if name == "MAX" else "LEAST(") if top_comma else m.group(0)
        result.append(text[i:m.start()] + replacement)
        i = m.end()
    return "".join(result)


# --- DML -----------------------------------------------------------------------------------------

_RE_INSERT_IGNORE = re.compile(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", re.IGNORECASE)
_RE_LIKE = re.compile(r"(?<!I)\bLIKE\b", re.IGNORECASE)
_RE_LIKE_OPERAND = re.compile(r"\bLIKE\s+(\?|'(?:[^']|'')*')", re.IGNORECASE)
_RE_RETURNING = re.compile(r"\bRETURNING\b", re.IGNORECASE)
_RE_BEGIN = re.compile(r"^\s*BEGIN(\s+(IMMEDIATE|DEFERRED|EXCLUSIVE))?\s*;?\s*$", re.IGNORECASE)
_RE_PRAGMA = re.compile(r"^\s*PRAGMA\b", re.IGNORECASE)


@lru_cache(maxsize=4096)
def dich_sql(sql: str) -> str | None:
    """Dịch một câu DML/điều khiển giao dịch. Trả None nếu câu không có ý nghĩa trên PostgreSQL (PRAGMA)."""
    if _RE_PRAGMA.match(sql):
        return None
    if _RE_BEGIN.match(sql):
        return "BEGIN"
    # bỏ chú thích (-- và /* */) để phần chèn thêm ở cuối câu không bị nuốt vào chú thích (review #13)
    sql = "".join(t if is_code or t[:1] in ("'", '"') else " " for is_code, t in _segments(sql))
    had_ignore = bool(_RE_INSERT_IGNORE.search(sql))

    def code(t: str) -> str:
        return _RE_INSERT_IGNORE.sub("INSERT INTO", t)

    out = _map_code(sql, code)
    # SQLite LIKE: không phân biệt hoa/thường ASCII, không có ký tự thoát mặc định → ILIKE … ESCAPE '' (review #14)
    out = _RE_LIKE_OPERAND.sub(lambda m: "ILIKE " + m.group(1) + " ESCAPE ''", out)
    if any(is_code and _RE_LIKE.search(t) for is_code, t in _segments(out)):
        raise ValueError("Mẫu LIKE không được bộ dịch hỗ trợ (vế phải không phải ? hoặc chuỗi).")
    out = _two_arg_minmax(out)
    if had_ignore:
        out = out.rstrip().rstrip(";")
        m = _RE_RETURNING.search(out)
        if m and all(is_code for is_code, t in _segments(out[m.start():m.start() + 9])):
            out = out[:m.start()].rstrip() + " ON CONFLICT DO NOTHING " + out[m.start():]
        else:
            out = out + " ON CONFLICT DO NOTHING"
    segs = _segments(out)
    if any(is_code and "?" in t for is_code, t in segs):
        # psycopg: khi có tham số, mọi '%' chữ (kể cả trong chuỗi 'CFO:%') phải viết thành '%%'
        out = "".join((t.replace("%", "%%").replace("?", "%s") if is_code else t.replace("%", "%%")) for is_code, t in segs)
    return out


# --- DDL -----------------------------------------------------------------------------------------

_RE_TRIGGER = re.compile(
    r"^\s*CREATE\s+TRIGGER\s+(\w+)\s+AFTER\s+(INSERT|UPDATE|DELETE)\s+ON\s+(\w+)\s+BEGIN\s+UPDATE\s+knowledge_epoch\b",
    re.IGNORECASE,
)
_RE_CREATE_TABLE = re.compile(r"^\s*CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\(", re.IGNORECASE)

EPOCH_FUNCTION = """CREATE OR REPLACE FUNCTION knowledge_epoch_bump() RETURNS trigger LANGUAGE plpgsql
SET search_path FROM CURRENT AS $$
BEGIN
    UPDATE knowledge_epoch SET revision = md5(random()::text || clock_timestamp()::text) WHERE id = 1;
    RETURN NULL;
END $$"""


def _types(t: str) -> str:
    t = re.sub(r"\bINTEGER\s+PRIMARY\s+KEY\b", "bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY", t, flags=re.IGNORECASE)
    t = re.sub(r"\bINTEGER\b", "bigint", t, flags=re.IGNORECASE)
    t = re.sub(r"\bTEXT\b", 'text COLLATE "C"', t, flags=re.IGNORECASE)
    t = re.sub(r"\bREAL\b", "double precision", t, flags=re.IGNORECASE)
    t = re.sub(r"\bBLOB\b", "bytea", t, flags=re.IGNORECASE)
    # khóa ngoại DEFERRABLE để bộ chép bảng (sao_chep_bang) có thể SET CONSTRAINTS ALL DEFERRED; bình thường vẫn kiểm ngay
    t = re.sub(r"\bREFERENCES\s+(\w+)\s*\(([^)]*)\)", r"REFERENCES \1(\2) DEFERRABLE INITIALLY IMMEDIATE", t, flags=re.IGNORECASE)
    return t


def dich_ddl(statement: str) -> list[str]:
    """Dịch một câu trong MIGRATIONS của SQLite thành 1..n câu PostgreSQL."""
    m = _RE_TRIGGER.match(statement)
    if m:
        name, event, table = m.group(1), m.group(2).upper(), m.group(3)
        return [f"CREATE TRIGGER {name} AFTER {event} ON {table} FOR EACH STATEMENT EXECUTE FUNCTION knowledge_epoch_bump()"]
    upper = statement.lstrip().upper()
    if upper.startswith(("CREATE TABLE", "ALTER TABLE")):
        out = _map_code(statement, _types)
        if _RE_CREATE_TABLE.match(statement):
            # SQLite: mọi bảng có rowid ẩn theo thứ tự chèn (lõi và test dùng ORDER BY rowid). PostgreSQL: cột identity
            # đặt cuối (INSERT positional ngắn hơn vẫn hợp lệ), GENERATED ALWAYS để chèn nhầm vị trí là lỗi rõ;
            # ket_noi ẩn cột này khỏi kết quả như SQLite.
            idx = out.rstrip().rstrip(";").rfind(")")
            out = out[:idx] + ", rowid bigint GENERATED ALWAYS AS IDENTITY" + out[idx:]
        return [out]
    if upper.startswith(("CREATE INDEX", "CREATE UNIQUE INDEX")):
        return [statement]
    if upper.startswith("INSERT"):
        return [dich_sql(statement) or statement]
    return [statement]


#: Chạy một lần khi tạo schema (CREATE OR REPLACE — chạy lại vô hại). Mọi tên không có schema: resolve theo search_path.
BOOT_STRAP = (
    # json_extract gần SQLite (review #5): đường dẫn strict (mảng không tự "mở"), boolean → 1/0, số theo dạng gọn
    # (1.50 → 1.5), chuỗi trả nguyên văn, object/mảng trả JSON. Khác biệt còn lại (không dùng trong lõi): object có dấu cách.
    """CREATE OR REPLACE FUNCTION json_extract(j text, p text) RETURNS text LANGUAGE sql IMMUTABLE STRICT
    SET search_path FROM CURRENT AS $$
    SELECT CASE jsonb_typeof(v)
             WHEN 'boolean' THEN CASE WHEN v = 'true'::jsonb THEN '1' ELSE '0' END
             WHEN 'number' THEN trim_scale((v #>> '{}')::numeric)::text
             WHEN 'null' THEN NULL
             ELSE v #>> '{}' END
    FROM (SELECT jsonb_path_query_first(j::jsonb, ('strict ' || p)::jsonpath, '{}'::jsonb, true) AS v) x $$""",
    # text = số: SQLite chỉ coi bằng khi giá trị JSON là số cùng trị số → so theo numeric khi vế trái có dạng số
    """CREATE OR REPLACE FUNCTION text_eq_num(a text, b numeric) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN a ~ '^-?[0-9]+(\\.[0-9]+)?([eE][-+]?[0-9]+)?$' THEN a::numeric = b ELSE false END $$""",
    """CREATE OR REPLACE FUNCTION text_eq_int(a text, b integer) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN a ~ '^-?[0-9]+(\\.[0-9]+)?([eE][-+]?[0-9]+)?$' THEN a::numeric = b ELSE false END $$""",
    """CREATE OR REPLACE FUNCTION text_eq_big(a text, b bigint) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN a ~ '^-?[0-9]+(\\.[0-9]+)?([eE][-+]?[0-9]+)?$' THEN a::numeric = b ELSE false END $$""",
    EPOCH_FUNCTION,
    # SQLite coi boolean là số nguyên nên MAX(action='APPROVE') hợp lệ; PostgreSQL cần aggregate riêng (bool_or/bool_and)
    """DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                       WHERE n.nspname = current_schema() AND p.proname = 'max' AND p.prokind = 'a') THEN
            CREATE AGGREGATE max(boolean) (SFUNC = boolor_statefunc, STYPE = boolean);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                       WHERE n.nspname = current_schema() AND p.proname = 'min' AND p.prokind = 'a') THEN
            CREATE AGGREGATE min(boolean) (SFUNC = booland_statefunc, STYPE = boolean);
        END IF;
    END $$""",
)

#: Operator = (text, số) để ``json_extract(...)=2`` của SQLite chạy được; tạo nếu chưa có (không có IF NOT EXISTS cho operator).
BOOT_STRAP_OPERATORS = (
    ("integer", "text_eq_int"),
    ("bigint", "text_eq_big"),
    ("numeric", "text_eq_num"),
)
