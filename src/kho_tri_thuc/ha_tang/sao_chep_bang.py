"""Chép nguyên trạng các bảng V12 giữa SQLite và PostgreSQL (schema V12) — hai chiều (V13 bước 5).

- SQLite → PostgreSQL: nạp kho thử lên PostgreSQL (``tools/chep_v12_sang_pg.py``). Giữ ``rowid`` của SQLite
  (lõi dùng ``ORDER BY rowid``) bằng cách ghi thẳng vào cột identity ``rowid`` rồi đặt lại sequence.
- PostgreSQL → SQLite: sao lưu kho PostgreSQL về file ``kho.sqlite`` (``backup.create_backup``) — cũng là
  đường lùi "đổi ``engine = sqlite``" của TL 39.

Chỉ đếm dòng; không in nội dung dòng. Đích phải là kho **mới tương thích** (``an_toan_sao_chep``: hợp đồng vật lý dựng từ DDL tin cậy,
lịch sử đúng, chỉ có seed migration). Guard chạy TRONG cùng một giao dịch ghi với việc chép, sau khi đã khóa người ghi:
- SQLite → PG: một giao dịch; khóa ``mo-kho:<schema>`` + khóa người ghi legacy ``hashtext(schema)`` (BEGIN IMMEDIATE của lõi)
  + ``LOCK TABLE … IN EXCLUSIVE MODE`` mọi bảng đến COMMIT → guard → KẾ HOẠCH SEQUENCE (biên/hết dải, identity sở hữu, quyền chủ
  sequence, ngữ nghĩa next/is_called) lập và kiểm TRƯỚC mọi hiệu ứng → thay seed → COPY (rowid cung cấp) → dấu nạp → FK → đối chiếu
  nội dung có kiểu + rowid thực với nguồn → ``ALTER SEQUENCE … RESTART`` (giao dịch: lỗi muộn bất kỳ hoàn tác cả sequence; không
  dùng ``setval`` phi giao dịch, không đổi identity mode) → COMMIT.
- PG → SQLite: ``BEGIN IMMEDIATE`` ở đích rồi mới kiểm; không đổi chế độ khóa ngoại (dùng ``defer_foreign_keys``); trong ảnh chụp đọc,
  bảng INTEGER PRIMARY KEY có rowid PG thực khác cột PK → ``PG_ROWID_ALIAS_LECH`` trước mọi ghi SQLite; đối chiếu nội dung
  có rowid trên CÙNG ảnh chụp đọc trước COMMIT; người gọi có thể kiểm độc lập thêm trên cùng ảnh chụp (``kiem_trong_anh_chup``).
Đích bị từ chối giữ nguyên dữ liệu/schema/lịch sử/identity/mọi sequence/chế độ khóa ngoại.
"""

from __future__ import annotations

import json
import re
import sqlite3

from . import database
from .primitives import DataError, now_utc

INT64_MAX = 2 ** 63 - 1


def bang_theo_thu_tu() -> list[str]:
    """Tên bảng theo thứ tự tạo trong MIGRATIONS (bảng cha trước bảng con) — cùng nguồn với guard đích."""
    from .an_toan_sao_chep import bang_ung_dung
    return bang_ung_dung()


def _cot_sqlite(conn: sqlite3.Connection, table: str) -> tuple[list[str], bool]:
    info = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    cols = [r[1] for r in info]
    pk = [r for r in info if r[5]]
    int_pk_alias = len(pk) == 1 and str(pk[0][2]).upper() == "INTEGER"
    return cols, int_pk_alias


def _cot_pg(raw, schema: str, table: str) -> list[str]:
    rows = raw.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s AND column_name <> 'rowid' ORDER BY ordinal_position",
        (schema, table),
    ).fetchall()
    return [r[0] for r in rows]


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def chep_sqlite_sang_pg(src: sqlite3.Connection, pg, *, schema: str | None = None) -> dict:
    """Chép mọi bảng V12 từ SQLite vào schema PostgreSQL của ``pg`` (KetNoiPG). Trả về số dòng mỗi bảng (nguồn, đích).
    Đọc nguồn trong một giao dịch đọc (một ảnh chụp nhất quán); ghi dấu "nạp xong" cùng giao dịch chép (review lần 2 #1, #7)."""
    import psycopg

    try:
        return _chep_sqlite_sang_pg(src, pg, schema=schema)
    except psycopg.Error as exc:
        from .ket_noi import loi_du_lieu
        raise loi_du_lieu(exc, "PG_CHEP") from None  # không lộ giá trị dòng trong thông điệp COPY (review lần 2 #6)


def _khoa_dich_pg(raw, schema: str, tables: list[str]) -> None:
    """Trong giao dịch đang mở: khóa theo thứ tự cố định — mở-kho → người ghi legacy → bảng (EXCLUSIVE, chặn mọi DML thô;
    vẫn cho đọc). Chỉ khóa bảng đang tồn tại (bảng thiếu/lạ để guard báo mã cụ thể, không thành lỗi driver)."""
    raw.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("mo-kho:" + schema,))
    raw.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (schema,))
    co = {r[0] for r in raw.execute(
        "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = %s AND c.relkind IN ('r','p')",
        (schema,)).fetchall()}
    thu_tu = [t for t in ["schema_migrations", *tables] if t in co] + sorted(co - set(tables) - {"schema_migrations"})
    for t in thu_tu:
        raw.execute(f"LOCK TABLE {_q(schema)}.{_q(t)} IN EXCLUSIVE MODE")


_RE_SEQ = re.compile(r'^("?[a-z_][a-z0-9_$]*"?)\.("?[a-z_][a-z0-9_$]*"?)$')


def _ke_hoach_sequence(raw, schema: str, tables: list[str], src: sqlite3.Connection) -> list[tuple[str, str, str, int]]:
    """(bảng, cột, sequence, giá trị kế tiếp) cho MỌI cột identity — lập từ nguồn (ảnh chụp đọc) TRƯỚC mọi hiệu ứng.
    Giá trị = max nguồn + 1 (workspace_meta tính cả dòng dấu nạp sẽ thêm), không thấp hơn seqmin; vượt seqmax/int64, bước không
    dương hoặc người chạy không có quyền chủ sequence (cần cho ALTER SEQUENCE) → từ chối có mã, chưa đổi gì."""
    from .ket_noi import DAU_NAP_XONG
    rows = raw.execute(
        """SELECT c.relname, a.attname, pg_get_serial_sequence(quote_ident(n.nspname) || '.' || quote_ident(c.relname), a.attname),
                  s.seqmin, s.seqmax, s.seqincrement, pg_has_role(current_user, sc.relowner, 'USAGE')
           FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid JOIN pg_namespace n ON n.oid = c.relnamespace
           JOIN pg_depend d ON d.refclassid = 'pg_class'::regclass AND d.refobjid = c.oid AND d.refobjsubid = a.attnum AND d.deptype = 'i'
                           AND d.classid = 'pg_class'::regclass
           JOIN pg_class sc ON sc.oid = d.objid AND sc.relkind = 'S' JOIN pg_sequence s ON s.seqrelid = sc.oid
           WHERE n.nspname = %s AND a.attidentity <> '' AND NOT a.attisdropped""", (schema,)).fetchall()
    theo_bang = {}
    for r in rows:
        theo_bang.setdefault(r[0], []).append(tuple(r))
    plan = []
    for table in tables:
        cols = sorted(theo_bang.get(table, []), key=lambda x: x[1])
        if "rowid" not in [c[1] for c in cols]:
            raise DataError("PG_SEQUENCE_KE_HOACH", f"Bảng {table} thiếu identity rowid — không lập được kế hoạch sequence.")
        for _, col, seq, seqmin, seqmax, step, chu in cols:
            m = src.execute(f'SELECT max({"rowid" if col == "rowid" else _q(col)}) FROM {_q(table)}').fetchone()[0]
            if m is not None and (isinstance(m, bool) or not isinstance(m, int)):
                raise DataError("PG_SEQUENCE_KE_HOACH", f"Giá trị identity nguồn {table}.{col} không phải số nguyên.")
            if table == "workspace_meta" and col == "rowid" and \
                    src.execute("SELECT 1 FROM workspace_meta WHERE key = ?", (DAU_NAP_XONG,)).fetchone() is None:
                m = (m if m is not None else 0) + 1  # dòng dấu nạp sẽ ghi rowid = max + 1
            value = max((m if m is not None else 0) + 1, int(seqmin))
            if not seq or not _RE_SEQ.match(seq):
                raise DataError("PG_SEQUENCE_KE_HOACH", f"Không xác định được sequence sở hữu {table}.{col}.")
            if int(step) <= 0:
                raise DataError("PG_SEQUENCE_KE_HOACH", f"Sequence {table}.{col} có bước không dương.")
            if value > int(seqmax) or value > INT64_MAX:
                raise DataError("PG_SEQUENCE_TRAN", f"Bảng {table}: identity {col} nguồn đã ở biên — giá trị kế tiếp vượt giới hạn sequence; "
                                                    "từ chối trước mọi thay đổi.")
            if not chu:
                raise DataError("PG_SEQUENCE_QUYEN", f"Tài khoản không có quyền chủ sequence của {table}.{col} (cần cho ALTER SEQUENCE RESTART).")
            plan.append((table, col, seq, value))
    return plan


def _dat_sequence(raw, seq: str, value: int) -> None:
    """ALTER SEQUENCE … RESTART WITH v: last_value = v, is_called = false (nextval kế tiếp trả v) — thay đổi giao dịch (relfilenode mới),
    hoàn tác cùng giao dịch chép khi có lỗi muộn; khác ``setval``."""
    if not _RE_SEQ.match(seq) or isinstance(value, bool) or not isinstance(value, int):
        raise DataError("PG_SEQUENCE_KE_HOACH", "Kế hoạch sequence không hợp lệ.")
    raw.execute(f"ALTER SEQUENCE {seq} RESTART WITH {int(value)}")


def _chep_sqlite_sang_pg(src: sqlite3.Connection, pg, *, schema: str | None = None) -> dict:
    from . import an_toan_sao_chep as at
    from .ket_noi import DAU_NAP_XONG, kiem_ten_schema
    raw = pg.raw
    schema = kiem_ten_schema(schema or pg.schema)
    tables = bang_theo_thu_tu()
    ket_qua = {}
    if pg.in_transaction:
        raise DataError("ACTIVE_TRANSACTION", "Kết nối PostgreSQL đích đang trong giao dịch của người gọi — không chép trong giao dịch đó.")
    src_version = src.execute("PRAGMA user_version").fetchone()[0]
    if src_version != database.SCHEMA_VERSION:
        raise DataError("SCHEMA_VERSION", "Nguồn và đích phải cùng phiên bản schema V12 trước khi chép.")
    doc_nguon = not src.in_transaction
    if doc_nguon:
        src.execute("BEGIN")  # ảnh chụp đọc nhất quán của SQLite (WAL)
    try:
        # MỘT giao dịch: khóa → guard → kế hoạch sequence → thay seed → COPY → dấu nạp → FK → đối chiếu nội dung → sequence → COMMIT
        with raw.transaction():
            _khoa_dich_pg(raw, schema, tables)
            at.tu_choi_neu_khong_moi(at.phan_loai_pg(raw, schema), dich="pg", ten=schema)
            plan = _ke_hoach_sequence(raw, schema, tables, src)
            raw.execute("SET CONSTRAINTS ALL DEFERRED")
            for table in at.hop_dong()["seed"]:  # chỉ dòng seed đã kiểm đúng nguyên văn; nguồn mang giá trị của nó
                raw.execute(f"DELETE FROM {_q(schema)}.{_q(table)}")
            for table in tables:
                cols, _ = _cot_sqlite(src, table)
                pg_cols = _cot_pg(raw, schema, table)
                if set(cols) != set(pg_cols):
                    raise DataError("COLUMN_MISMATCH", f"Bảng {table}: cột SQLite và PostgreSQL không khớp.")
                n = 0
                col_list = ", ".join(_q(c) for c in cols) + ", rowid"
                with raw.cursor() as cur:
                    with cur.copy(f"COPY {_q(schema)}.{_q(table)} ({col_list}) FROM STDIN") as copy:
                        for row in src.execute(f'SELECT rowid, {", ".join(_q(c) for c in cols)} FROM "{table}" ORDER BY rowid'):
                            values = tuple(row)
                            copy.write_row(values[1:] + (values[0],))
                            n += 1
                dich = raw.execute(f"SELECT count(*) FROM {_q(schema)}.{_q(table)}").fetchone()[0]
                ket_qua[table] = {"nguon": n, "dich": int(dich)}
            raw.execute(
                # rowid ghi tường minh (sequence chưa đặt lại ở bước này) để không trùng rowid đã chép
                f"INSERT INTO {_q(schema)}.workspace_meta (key, value, rowid) OVERRIDING SYSTEM VALUE VALUES (%s, %s, "
                f"(SELECT coalesce(max(rowid), 0) + 1 FROM {_q(schema)}.workspace_meta)) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (DAU_NAP_XONG, json.dumps({"luc": now_utc(), "tong_dong": sum(v["nguon"] for v in ket_qua.values())})),
            )
            raw.execute("SET CONSTRAINTS ALL IMMEDIATE")  # kiểm khóa ngoại trong giao dịch
            # đối chiếu canonical: giá trị có kiểu + rowid thực của mọi bảng (không chỉ số đếm) — vd cột tiền bị đổi kiểu làm mất đơn vị
            lech = sorted(t for t, v in doi_chieu_noi_dung(src, van_tay_pg(raw, schema), lambda t: _cot_pg(raw, schema, t)).items() if not v["khop"])
            if lech:
                raise DataError("PG_CHEP_LECH_NOI_DUNG", f"Nội dung chép vào PostgreSQL khác nguồn ở {len(lech)} bảng — hoàn tác toàn bộ.")
            for table, col, seq, value in plan:
                _dat_sequence(raw, seq, value)
            for table, col, seq, value in plan:  # hậu kiểm: giá trị kế tiếp lớn hơn mọi giá trị đã có
                m = raw.execute(f"SELECT max({_q(col)}) FROM {_q(schema)}.{_q(table)}").fetchone()[0]
                if m is not None and int(m) >= value:
                    raise DataError("PG_SEQUENCE_LECH", f"Sequence {table}.{col} không vượt giá trị đã có — hoàn tác toàn bộ.")
    finally:
        if doc_nguon and src.in_transaction:
            src.execute("ROLLBACK")
    return ket_qua


# --- đối chiếu nội dung nguồn/đích (V13 A5; F4: gồm giá trị rowid thực) -----------------------------

def khoa_meta_migration() -> tuple[str, ...]:
    """Khóa workspace_meta do bộ chép/migration tự thêm (không phải dữ liệu nghiệp vụ của kho nguồn)."""
    from .ket_noi import DAU_NAP_XONG
    return (DAU_NAP_XONG,)


def _gia_tri_chuan(v):
    if isinstance(v, (bytes, bytearray, memoryview)):
        return {"b": bytes(v).hex()}
    if isinstance(v, bool):
        return {"bool": int(v)}
    if isinstance(v, float):
        return {"f": repr(v)}
    if isinstance(v, int):
        return {"i": str(v)}  # số nguyên mang tag + chữ số đầy đủ (> 2^53 không qua số thực)
    if v is None:
        return None
    if isinstance(v, str):
        return {"s": v}
    return {"x": type(v).__name__, "v": str(v)}


def _van_tay_bang(execute, ten_sql: str, table: str, cols: list[str], ph: str, rowid_sql: str) -> tuple[int, str]:
    """(số dòng, sha256) của [giá trị rowid thực có tag] + giá trị các cột ``cols``, theo thứ tự rowid.
    ``rowid_sql``: SQLite ``rowid`` (bảng INTEGER PRIMARY KEY: rowid là cột đó); PG: cột identity ``rowid`` thực ở mọi bảng.
    workspace_meta bỏ khóa do migration thêm. Thứ tự giống nhau mà giá trị rowid khác vẫn bị phát hiện."""
    import hashlib

    where, params = "", ()
    if table == "workspace_meta":
        params = khoa_meta_migration()
        where = " WHERE key NOT IN (" + ",".join([ph] * len(params)) + ")"
    h, n = hashlib.sha256(), 0
    for row in execute(f"SELECT {rowid_sql} AS ktt_khoa_dong, {', '.join(_q(c) for c in cols)} FROM {ten_sql}{where} ORDER BY {rowid_sql}", params):
        h.update(json.dumps([_gia_tri_chuan(v) for v in row], ensure_ascii=False, separators=(",", ":")).encode() + b"\n")
        n += 1
    return n, h.hexdigest()


def van_tay_sqlite(conn: sqlite3.Connection):
    return lambda table, cols: _van_tay_bang(conn.execute, _q(table), table, cols, "?", "rowid")


def van_tay_pg(raw, schema: str):
    """Fingerprint PG theo rowid THỰC của PostgreSQL ở mọi bảng (kể cả bảng INTEGER PRIMARY KEY) — không thay bằng cột PK."""
    return lambda table, cols: _van_tay_bang(raw.execute, f"{_q(schema)}.{_q(table)}", table, cols, "%s", "rowid")


def kiem_rowid_alias_pg(raw, schema: str) -> None:
    """SQLite không biểu diễn được đồng thời cột INTEGER PRIMARY KEY và một rowid khác: mọi bảng alias của hợp đồng phải có
    rowid PG thực = cột PK ở MỌI dòng. Gọi trong ảnh chụp dùng để chép/kiểm; lệch → từ chối nghiệp vụ, không sửa dữ liệu nguồn."""
    from .an_toan_sao_chep import hop_dong
    lech = []
    for table, col in sorted(hop_dong()["alias"].items()):
        n = raw.execute(f"SELECT count(*) FROM {_q(schema)}.{_q(table)} WHERE rowid IS DISTINCT FROM {_q(col)}").fetchone()[0]
        if int(n):
            lech.append(table)
    if lech:
        raise DataError("PG_ROWID_ALIAS_LECH", f"Nguồn PostgreSQL có rowid thực khác cột INTEGER PRIMARY KEY ở {len(lech)} bảng "
                                                 f"({','.join(lech[:6])}) — SQLite không giữ được cả hai; từ chối, không chép/không công bố.")


def doi_chieu_noi_dung(src: sqlite3.Connection, van_tay_dich, cot_dich) -> dict:
    """So từng bảng V12: số dòng + hash nội dung có kiểu và rowid canonical tái tính hai phía (không dựa vào số đếm hay hash đã chép).
    ``cot_dich(table)`` → danh sách cột ở đích. Chỉ trả số đếm và cờ khớp, không in giá trị."""
    out = {}
    for table in bang_theo_thu_tu():
        cols, _ = _cot_sqlite(src, table)
        n_src, h_src = _van_tay_bang(src.execute, _q(table), table, cols, "?", "rowid")
        if set(cols) != set(cot_dich(table)):
            out[table] = {"nguon": n_src, "dich": None, "khop": False, "loi": "COLUMN_MISMATCH"}
            continue
        n_dst, h_dst = van_tay_dich(table, cols)
        out[table] = {"nguon": n_src, "dich": n_dst, "khop": n_src == n_dst and h_src == h_dst}
    return out


def chep_pg_sang_sqlite(pg, dst: sqlite3.Connection, *, kiem_trong_anh_chup=None) -> dict:
    """Chép mọi bảng V12 từ PostgreSQL về một kho SQLite **mới** (đã migrate). Giữ rowid; trả về số dòng mỗi bảng.
    Đọc PostgreSQL trong một giao dịch REPEATABLE READ READ ONLY: mọi bảng cùng một ảnh chụp (review lần 2 #7). Trước COMMIT đối chiếu
    nội dung có rowid trên cùng ảnh chụp. ``kiem_trong_anh_chup(raw)`` (tùy chọn) chạy SAU COMMIT SQLite, vẫn trong CÙNG ảnh chụp PG
    (F3: kiểm độc lập không so với ảnh chụp khác)."""
    import psycopg

    try:
        return _chep_pg_sang_sqlite(pg, dst, kiem_trong_anh_chup)
    except psycopg.Error as exc:
        from .ket_noi import loi_du_lieu
        raise loi_du_lieu(exc, "PG_CHEP") from None


def _chep_pg_sang_sqlite(pg, dst: sqlite3.Connection, kiem_trong_anh_chup=None) -> dict:
    import psycopg.rows

    from . import an_toan_sao_chep as at
    raw, schema = pg.raw, pg.schema
    tables = bang_theo_thu_tu()
    if dst.in_transaction:
        raise DataError("ACTIVE_TRANSACTION", "Kết nối SQLite đích đang trong giao dịch.")
    if pg.in_transaction:
        raise DataError("ACTIVE_TRANSACTION", "Kết nối PostgreSQL nguồn đang trong giao dịch.")
    if pg.schema_version() != database.SCHEMA_VERSION:
        raise DataError("SCHEMA_VERSION", "Nguồn và đích phải cùng phiên bản schema V12 trước khi chép.")
    ket_qua = {}
    try:
        # khóa ghi đích TRƯỚC khi kiểm; không đổi PRAGMA foreign_keys (đích bị từ chối giữ nguyên chế độ khóa ngoại)
        dst.execute("BEGIN IMMEDIATE")
        try:
            at.tu_choi_neu_khong_moi(at.phan_loai_sqlite(dst), dich="sqlite")
            dst.execute("PRAGMA defer_foreign_keys=ON")  # chỉ trong giao dịch này; tự hết khi COMMIT/ROLLBACK
            raw.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
            kiem_rowid_alias_pg(raw, schema)  # cùng ảnh chụp với chép + kiểm; trước mọi ghi/COMMIT SQLite
            for table in at.hop_dong()["seed"]:
                dst.execute(f'DELETE FROM "{table}"')
            for table in tables:
                cols, int_pk_alias = _cot_sqlite(dst, table)
                pg_cols = _cot_pg(raw, schema, table)
                if set(cols) != set(pg_cols):
                    raise DataError("COLUMN_MISMATCH", f"Bảng {table}: cột SQLite và PostgreSQL không khớp.")
                target_cols = list(cols) if int_pk_alias else ["rowid", *cols]
                placeholders = ",".join("?" * len(target_cols))
                sql = f'INSERT INTO "{table}" ({", ".join(_q(c) for c in target_cols)}) VALUES ({placeholders})'
                n = 0
                with raw.cursor(row_factory=psycopg.rows.tuple_row) as cur:
                    cur.execute(f"SELECT rowid, {', '.join(_q(c) for c in cols)} FROM {_q(schema)}.{_q(table)} ORDER BY rowid")
                    for row in cur:
                        values = tuple(row[1:]) if int_pk_alias else tuple(row)
                        dst.execute(sql, values)
                        n += 1
                ket_qua[table] = {"nguon": n, "dich": dst.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]}
            violations = dst.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise DataError("FOREIGN_KEY", f"Bản chép về SQLite vi phạm {len(violations)} khóa ngoại.")
            lech = sorted(t for t, v in doi_chieu_noi_dung(dst, van_tay_pg(raw, schema), lambda t: _cot_pg(raw, schema, t)).items() if not v["khop"])
            if lech:
                raise DataError("PG_CHEP_LECH_NOI_DUNG", f"Bản chép về SQLite khác nguồn ở {len(lech)} bảng — hoàn tác.")
            dst.commit()
        except BaseException:
            if dst.in_transaction:
                dst.rollback()
            raise
        if kiem_trong_anh_chup is not None:
            kiem_trong_anh_chup(raw)  # vẫn trong giao dịch đọc PG ở trên: cùng ảnh chụp với lần chép
    finally:
        if pg.in_transaction:
            raw.execute("ROLLBACK")
    return ket_qua
