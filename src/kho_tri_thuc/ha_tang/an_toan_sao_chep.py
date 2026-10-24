"""Nguồn quy tắc DUY NHẤT "đích chép/nạp legacy V12 còn mới" (V13 — GIAO-SUA-V13-LEGACY-BACKUP-01/02).

Đích chỉ được nhận khi là kho V12 **mới tương thích**: đúng hợp đồng vật lý của migration (49 bảng ứng dụng + ``schema_migrations``
là metadata), lịch sử version/checksum liên tục và đúng, và dữ liệu đúng bằng seed của migration (hiện chỉ
``knowledge_epoch = (1,'initial')``). Mọi dòng khác, seed bị đổi, đối tượng lạ/thiếu/lệch, schema cũ/dở/không rõ → từ chối.

Hợp đồng tham chiếu (một nguồn, không do caller khai):
- SQLite: dựng từ ``database.MIGRATIONS`` trên SQLite ``:memory:`` (đối tượng ``sqlite_master`` nguyên văn).
- PostgreSQL (R1): dựng bằng CHÍNH đường migration của ``ket_noi`` (``ke_hoach_migration`` + ``ap_dung_migration``: BOOT_STRAP,
  operator, DDL dịch) vào một schema tham chiếu tên ngẫu nhiên ``ktt_ref_*`` trong một SAVEPOINT **luôn rollback** — không tạo gì
  trong schema đích, không để lại đối tượng nào. Từ đó đọc mô tả catalog chuẩn hóa (tên schema thay bằng ``@S``): mọi relation
  (bảng/chỉ mục/sequence/kiểu hàng), cột theo thứ tự (kiểu+typmod, NOT NULL, default, identity, generated, collation), ràng buộc
  (PK/FK/UNIQUE/CHECK + deferrable/validated), chỉ mục, trigger (kể cả trạng thái bật; trigger nội bộ FK theo ràng buộc), rule,
  policy/RLS, hàm/aggregate (định nghĩa đầy đủ), operator, kiểu, sequence (tham số + cột sở hữu) và các đối tượng namespace khác.
  Đích phải TRÙNG KHỚP mô tả tham chiếu ở đúng version lịch sử của nó; đối tượng do PG tự tạo phụ thuộc đối tượng chuẩn (kiểu hàng,
  mảng, sequence identity, trigger FK) xuất hiện ở cả hai phía nên không bị coi là lạ. Cache theo (phiên bản máy chủ, version).
  Cần quyền CREATE trên database cho schema tham chiếu tạm; thiếu quyền → ``PG_HOP_DONG_THAM_CHIEU`` (fail-closed).
Shape ``schema_migrations`` được kiểm TRƯỚC khi đọc lịch sử (không đọc qua dict nên không che dòng trùng).
Chỉ đọc đích; trả số đếm/mã/tên đối tượng, không trả giá trị dòng.
"""

from __future__ import annotations

import re
import sqlite3
import uuid
from functools import lru_cache

from . import database
from .primitives import DataError, sha256

_RE_TABLE = re.compile(r"^\s*CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?(\w+)", re.IGNORECASE)

# Trạng thái đích
VANG_MAT = "VANG_MAT"                  # schema/DB chưa tồn tại (sẽ được tạo mới có thẩm quyền)
TRONG_HOAN_TOAN = "TRONG_HOAN_TOAN"    # namespace tồn tại nhưng KHÔNG có bất kỳ đối tượng nào (relation/hàm/kiểu/operator/…)
MOI_KHOP = "MOI_KHOP"                  # schema hiện hành, đúng hợp đồng vật lý, chỉ có seed
CO_DU_LIEU = "CO_DU_LIEU"              # có dòng ngoài seed / seed bị đổi / bảng lạ có dòng
CU = "CU"                              # lịch sử + vật lý đúng nhưng phiên bản cũ hơn mã, không có dữ liệu
KHONG_TUONG_THICH = "KHONG_TUONG_THICH"  # dở dang / lạ / lịch sử sai / tương lai / lệch vật lý / chỉ có hàm-kiểu-operator

# Shape schema_migrations theo DDL bootstrap của ket_noi (``ap_dung_migration``); tự kiểm khớp tham chiếu dựng từ DDL.
SCHEMA_MIGRATIONS_COT = (("version", "bigint", True, "", "", ""), ("checksum", "text", True, "", "", ""),
                         ("applied_at", "text", True, "", "", ""))
SCHEMA_MIGRATIONS_RANG_BUOC = (("p", "PRIMARY KEY (version)"),)


@lru_cache(maxsize=None)
def hop_dong(version: int | None = None) -> dict:
    """Hợp đồng SQLite ở ``version`` (mặc định hiện hành): bảng theo thứ tự tạo, cột theo thứ tự, bảng có INTEGER PRIMARY KEY
    (rowid = cột đó), đối tượng schema SQLite nguyên văn, checksum lịch sử toàn bộ, seed."""
    version = database.SCHEMA_VERSION if version is None else version
    tables = [m.group(2) for group in database.MIGRATIONS[:version] for s in group for m in [_RE_TABLE.match(s)] if m]
    ref = sqlite3.connect(":memory:", isolation_level=None)
    try:
        if version:
            database.migrate(ref, version)
        cols, alias = {}, {}
        for t in tables:
            info = ref.execute(f'PRAGMA table_info("{t}")').fetchall()
            cols[t] = [r[1] for r in info]
            pk = [r for r in info if r[5]]
            if len(pk) == 1 and str(pk[0][2]).upper() == "INTEGER":
                alias[t] = pk[0][1]
        objects = frozenset(tuple(r) for r in ref.execute("SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
        seed = {}
        for t in tables:
            rows = [tuple(r) for r in ref.execute(f'SELECT {", ".join(_q(c) for c in cols[t])} FROM "{t}" ORDER BY rowid')]
            if rows:
                seed[t] = rows
    finally:
        ref.close()
    history = {i: sha256("\n".join(stmts).encode()) for i, stmts in enumerate(database.MIGRATIONS, 1)}
    return {"version": version, "tables": tuple(tables), "cols": cols, "alias": alias, "sqlite_objects": objects, "history": history, "seed": seed}


def bang_ung_dung() -> list[str]:
    return list(hop_dong()["tables"])


def cot_alias_rowid(table: str) -> str | None:
    """Bảng có INTEGER PRIMARY KEY: rowid SQLite chính là cột này (giá trị rowid canonical); None nếu rowid ẩn."""
    return hop_dong()["alias"].get(table)


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _lich_su(rows: list) -> tuple[str | None, int]:
    """(lỗi, version) từ DANH SÁCH dòng (version, checksum): không trùng, liên tục 1..n, checksum đúng, n ≤ phiên bản mã."""
    ref = hop_dong()["history"]
    versions = [int(r[0]) for r in rows]
    if len(versions) != len(set(versions)):
        return "LICH_SU_TRUNG", max(versions)
    history = {int(r[0]): r[1] for r in rows}
    version = max(history) if history else 0
    if set(history) != set(range(1, version + 1)):
        return "LICH_SU_KHONG_LIEN_TUC", version
    if version > len(ref):
        return "SCHEMA_TUONG_LAI", version
    if any(history[i] != ref[i] for i in history):
        return "LICH_SU_CHECKSUM_LECH", version
    return None, version


def _du_lieu(dem, doc_seed, tables_co, seed, doc_duoc) -> tuple[list[str], list[str]]:
    """(bảng có dữ liệu ngoài seed, bảng seed không đọc được để so). ``doc_duoc(t)``: bảng đúng hợp đồng nên đọc theo cột được."""
    ds, khong_doc = [], []
    for t in tables_co:
        n = dem(t)
        if t in seed:
            if not doc_duoc(t):
                if n:
                    khong_doc.append(t)
                continue
            if n == len(seed[t]) and doc_seed(t) == seed[t]:
                continue
            ds.append(t)  # seed bị đổi/xóa/thêm dòng: đích đã bị đụng tới, không phải "mới"
        elif n:
            ds.append(t)
    return ds, khong_doc


# ---------------------------------------------------------------- PostgreSQL: mô tả catalog chuẩn hóa

_MO_TA_SQL = {
    "class": """SELECT c.relname, c.relkind::text, c.relpersistence::text, c.relrowsecurity, c.relforcerowsecurity,
                       coalesce(array_to_string(c.reloptions, ','), ''), c.relispartition
                FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = %s""",
    "cot": """SELECT c.relname, row_number() OVER (PARTITION BY c.oid ORDER BY a.attnum), a.attname, format_type(a.atttypid, a.atttypmod),
                     a.attnotnull, coalesce(pg_get_expr(ad.adbin, ad.adrelid), ''), a.attidentity::text, a.attgenerated::text,
                     coalesce(co.collname, ''), a.attislocal, a.attinhcount
              FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid JOIN pg_namespace n ON n.oid = c.relnamespace
              LEFT JOIN pg_attrdef ad ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
              LEFT JOIN pg_collation co ON co.oid = a.attcollation
              WHERE n.nspname = %s AND a.attnum > 0 AND NOT a.attisdropped""",
    "rang_buoc": """SELECT coalesce(c.relname, t.typname, ''), con.conname, con.contype::text, pg_get_constraintdef(con.oid, true),
                           con.condeferrable, con.condeferred, con.convalidated, con.connoinherit
                    FROM pg_constraint con JOIN pg_namespace n ON n.oid = con.connamespace
                    LEFT JOIN pg_class c ON c.oid = con.conrelid LEFT JOIN pg_type t ON t.oid = con.contypid WHERE n.nspname = %s""",
    "chi_muc": """SELECT c.relname, i.relname, pg_get_indexdef(i.oid), x.indisunique, x.indisprimary, x.indisvalid, x.indisready,
                         x.indimmediate, x.indisexclusion
                  FROM pg_index x JOIN pg_class i ON i.oid = x.indexrelid JOIN pg_class c ON c.oid = x.indrelid
                  JOIN pg_namespace n ON n.oid = i.relnamespace WHERE n.nspname = %s""",
    "trigger": """SELECT c.relname, CASE WHEN t.tgisinternal THEN coalesce(con.conname, '') ELSE t.tgname END,
                         CASE WHEN t.tgisinternal THEN t.tgfoid::regprocedure::text || '/' || t.tgtype ELSE pg_get_triggerdef(t.oid, true) END,
                         t.tgenabled::text, t.tgisinternal
                  FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_namespace n ON n.oid = c.relnamespace
                  LEFT JOIN pg_constraint con ON con.oid = t.tgconstraint WHERE n.nspname = %s""",
    "rule": """SELECT c.relname, r.rulename, pg_get_ruledef(r.oid, true), r.ev_enabled::text
               FROM pg_rewrite r JOIN pg_class c ON c.oid = r.ev_class JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = %s""",
    "policy": """SELECT c.relname, p.polname, p.polcmd::text, p.polpermissive, coalesce(pg_get_expr(p.polqual, p.polrelid), ''),
                        coalesce(pg_get_expr(p.polwithcheck, p.polrelid), '')
                 FROM pg_policy p JOIN pg_class c ON c.oid = p.polrelid JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = %s""",
    "ham": """SELECT p.proname, pg_get_function_identity_arguments(p.oid), p.prokind::text,
                     CASE WHEN p.prokind IN ('f','p','w') THEN pg_get_functiondef(p.oid) ELSE '' END,
                     coalesce(array_to_string(p.proconfig, ';'), ''), p.provolatile::text, p.proisstrict, p.prosecdef,
                     coalesce(ag.aggtransfn::regprocedure::text, ''), coalesce(ag.aggfinalfn::text, ''),
                     coalesce(format_type(ag.aggtranstype, NULL), ''), coalesce(ag.agginitval, '')
              FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace LEFT JOIN pg_aggregate ag ON ag.aggfnoid = p.oid
              WHERE n.nspname = %s""",
    "operator": """SELECT o.oprname, format_type(o.oprleft, NULL), format_type(o.oprright, NULL), o.oprcode::regprocedure::text,
                          format_type(o.oprresult, NULL), o.oprcom::regoperator::text, o.oprnegate::regoperator::text
                   FROM pg_operator o JOIN pg_namespace n ON n.oid = o.oprnamespace WHERE n.nspname = %s""",
    "kieu": """SELECT t.typname, t.typtype::text, t.typcategory::text, coalesce(c.relname, ''), coalesce(c.relkind::text, ''),
                      format_type(t.typelem, NULL)
               FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace LEFT JOIN pg_class c ON c.oid = t.typrelid WHERE n.nspname = %s""",
    "sequence": """SELECT c.relname, format_type(s.seqtypid, NULL), s.seqstart, s.seqincrement, s.seqmax, s.seqmin, s.seqcache, s.seqcycle,
                          coalesce(dt.relname, ''), coalesce(da.attname, ''), coalesce(d.deptype::text, '')
                   FROM pg_sequence s JOIN pg_class c ON c.oid = s.seqrelid JOIN pg_namespace n ON n.oid = c.relnamespace
                   LEFT JOIN pg_depend d ON d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.refclassid = 'pg_class'::regclass
                                        AND d.deptype IN ('a','i')
                   LEFT JOIN pg_class dt ON dt.oid = d.refobjid LEFT JOIN pg_attribute da ON da.attrelid = d.refobjid AND da.attnum = d.refobjsubid
                   WHERE n.nspname = %s""",
    "khac": """SELECT 'collation', collname FROM pg_collation x JOIN pg_namespace n ON n.oid = x.collnamespace WHERE n.nspname = %(s)s
               UNION ALL SELECT 'conversion', conname FROM pg_conversion x JOIN pg_namespace n ON n.oid = x.connamespace WHERE n.nspname = %(s)s
               UNION ALL SELECT 'opclass', opcname FROM pg_opclass x JOIN pg_namespace n ON n.oid = x.opcnamespace WHERE n.nspname = %(s)s
               UNION ALL SELECT 'opfamily', opfname FROM pg_opfamily x JOIN pg_namespace n ON n.oid = x.opfnamespace WHERE n.nspname = %(s)s
               UNION ALL SELECT 'ts_config', cfgname FROM pg_ts_config x JOIN pg_namespace n ON n.oid = x.cfgnamespace WHERE n.nspname = %(s)s
               UNION ALL SELECT 'ts_dict', dictname FROM pg_ts_dict x JOIN pg_namespace n ON n.oid = x.dictnamespace WHERE n.nspname = %(s)s
               UNION ALL SELECT 'ts_parser', prsname FROM pg_ts_parser x JOIN pg_namespace n ON n.oid = x.prsnamespace WHERE n.nspname = %(s)s
               UNION ALL SELECT 'ts_template', tmplname FROM pg_ts_template x JOIN pg_namespace n ON n.oid = x.tmplnamespace WHERE n.nspname = %(s)s
               UNION ALL SELECT 'statistic_ext', stxname FROM pg_statistic_ext x JOIN pg_namespace n ON n.oid = x.stxnamespace WHERE n.nspname = %(s)s
               UNION ALL SELECT 'extension', extname FROM pg_extension x JOIN pg_namespace n ON n.oid = x.extnamespace WHERE n.nspname = %(s)s""",
}


def _chuan_hoa(v, schema: str):
    if isinstance(v, str):
        return re.sub(r'(?<![A-Za-z0-9_$])("?)' + re.escape(schema) + r'\1(?![A-Za-z0-9_$])', "@S", v)
    return v


def _mo_ta_pg(raw, schema: str) -> dict:
    """Mô tả catalog chuẩn hóa của namespace ``schema`` (multiset theo nhóm). Gọi trong một savepoint luôn rollback: đặt
    search_path = pg_catalog để mọi tên trong định nghĩa được định danh đầy đủ rồi thay tên schema bằng ``@S``."""
    raw.execute("SELECT set_config('search_path', 'pg_catalog', true)")
    out = {}
    for nhom, sql in _MO_TA_SQL.items():
        params = {"s": schema} if nhom == "khac" else (schema,)
        out[nhom] = tuple(sorted((tuple(_chuan_hoa(x, schema) for x in r) for r in raw.execute(sql, params).fetchall()), key=repr))
    return out


_THAM_CHIEU: dict = {}


def _tham_chieu_pg(raw, version: int) -> dict:
    """Mô tả catalog THAM CHIẾU ở ``version``: dựng bằng đường migration của ket_noi vào schema ``ktt_ref_*`` trong savepoint luôn
    rollback (không tác động schema đích, không để lại đối tượng)."""
    import psycopg

    from .ket_noi import ap_dung_migration, ke_hoach_migration
    key = (raw.info.server_version, version)
    if key not in _THAM_CHIEU:
        ref = "ktt_ref_" + uuid.uuid4().hex[:16]
        try:
            with raw.transaction(force_rollback=True):
                raw.execute(f'CREATE SCHEMA "{ref}"')
                raw.execute(f"SELECT set_config('search_path', %s, true)", (f'"{ref}", public',))
                ap_dung_migration(raw, ref, ke_hoach_migration(version), 0)
                mo_ta = _mo_ta_pg(raw, ref)
        except psycopg.errors.InsufficientPrivilege:
            raise DataError("PG_HOP_DONG_THAM_CHIEU", "Không dựng được hợp đồng tham chiếu (cần quyền CREATE trên database cho schema tạm "
                                                      "luôn hoàn tác) — từ chối, không đoán.") from None
        cot = tuple(r[2:8] for r in sorted(x for x in mo_ta["cot"] if x[0] == "schema_migrations"))
        if tuple((a, b, c, d, e, f) for a, b, c, d, e, f in cot) != SCHEMA_MIGRATIONS_COT:
            raise DataError("PG_HOP_DONG_MAU_THUAN", "Shape schema_migrations tham chiếu khác hằng hợp đồng — dừng.")
        _THAM_CHIEU[key] = mo_ta
    return _THAM_CHIEU[key]


def _lech(dich: dict, ref: dict) -> list[str]:
    """Danh sách mã lệch (chỉ tên nhóm/đối tượng, không giá trị dòng). Multiset: trùng lặp cũng là lệch."""
    out = []
    for nhom in _MO_TA_SQL:
        a, b = list(dich.get(nhom, ())), list(ref.get(nhom, ()))
        if a == b:
            continue
        thua = [x for x in a if a.count(x) > b.count(x)]
        thieu = [x for x in b if b.count(x) > a.count(x)]
        for x in sorted(set(thua), key=repr):
            out.append(f"LA:{nhom}:{x[0]}")
        for x in sorted(set(thieu), key=repr):
            out.append(f"THIEU:{nhom}:{x[0]}")
    return out


def _bang_lech(lech: list[str]) -> set[str]:
    return {x.split(":", 2)[2] for x in lech}


def _kiem_schema_migrations(raw, schema: str) -> str | None:
    """Shape ``schema_migrations`` trước khi đọc lịch sử: bảng thường, đúng cột/kiểu/NOT NULL/không default/identity, đúng một PK(version),
    không trigger/rule/RLS. None = đúng."""
    row = raw.execute("SELECT c.oid, c.relkind::text, c.relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                      "WHERE n.nspname = %s AND c.relname = 'schema_migrations'", (schema,)).fetchone()
    if row is None:
        return "THIEU_SCHEMA_MIGRATIONS"
    oid = row[0]
    if row[1] != "r" or row[2]:
        return "SCHEMA_MIGRATIONS_LECH"
    cot = tuple(tuple(r) for r in raw.execute(
        "SELECT a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull, coalesce(pg_get_expr(d.adbin, d.adrelid), ''), "
        "a.attidentity::text, a.attgenerated::text FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum "
        "WHERE a.attrelid = %s AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum", (oid,)).fetchall())
    rb = tuple(tuple(r) for r in raw.execute("SELECT contype::text, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = %s ORDER BY 1, 2",
                                             (oid,)).fetchall())
    phu = raw.execute("SELECT (SELECT count(*) FROM pg_trigger WHERE tgrelid = %s) + (SELECT count(*) FROM pg_rewrite WHERE ev_class = %s)",
                      (oid, oid)).fetchone()[0]
    if cot != SCHEMA_MIGRATIONS_COT or rb != SCHEMA_MIGRATIONS_RANG_BUOC or int(phu):
        return "SCHEMA_MIGRATIONS_LECH"
    return None


def phan_loai_pg(raw, schema: str) -> dict:
    """Phân loại schema đích PostgreSQL. ``raw``: kết nối psycopg (autocommit hoặc đang trong giao dịch). Mọi đọc + dựng tham chiếu
    chạy trong một savepoint/giao dịch LUÔN rollback; không thay đổi đích. Dòng truy cập theo chỉ số."""
    with raw.transaction(force_rollback=True):
        return _phan_loai_pg(raw, schema)


def _phan_loai_pg(raw, schema: str) -> dict:
    one = lambda sql, p=(): raw.execute(sql, p).fetchone()  # noqa: E731
    if not one("SELECT 1 FROM pg_namespace WHERE nspname = %s", (schema,)):
        return {"trang_thai": VANG_MAT, "dau": False, "chi_tiet": []}
    with raw.transaction(force_rollback=True):
        dich = _mo_ta_pg(raw, schema)
    if not any(dich.values()):
        return {"trang_thai": TRONG_HOAN_TOAN, "dau": False, "chi_tiet": []}
    qs = _q(schema)
    loi, version, lech = [], 0, []
    loi_sm = _kiem_schema_migrations(raw, schema)
    if loi_sm:
        loi.append(loi_sm)
    else:
        loi_ls, version = _lich_su(raw.execute(f"SELECT version, checksum FROM {qs}.schema_migrations").fetchall())
        if loi_ls:
            loi.append(loi_ls)
    if not loi:
        lech = _lech(dich, _tham_chieu_pg(raw, version))
    hd = hop_dong(version if not loi else None)
    bang_lech = _bang_lech(lech) if not loi else {t for t in hd["tables"]}
    rels = {r[0]: r[1] for r in dich["class"]}
    known = [t for t in hd["tables"] if rels.get(t) in ("r", "p")]
    # bảng lạ: chỉ đếm dòng nếu không có policy/rule (đọc không chạy mã của đích)
    co_ma = {r[0] for r in dich["policy"]} | {r[0] for r in dich["rule"]}
    extra = sorted(t for t, k in rels.items() if k in ("r", "p") and t not in hd["tables"] and t != "schema_migrations" and t not in co_ma)
    dem = lambda t: int(one(f"SELECT count(*) FROM {qs}.{_q(t)}")[0])  # noqa: E731
    doc = lambda t: [tuple(r) for r in raw.execute(f'SELECT {", ".join(_q(c) for c in hd["cols"][t])} FROM {qs}.{_q(t)} ORDER BY rowid').fetchall()]  # noqa: E731
    ds, khong_doc = _du_lieu(dem, doc, [t for t in known if t not in co_ma], hd["seed"], lambda t: t not in bang_lech)
    ds += [t for t in extra if dem(t)]
    dau = False
    if "workspace_meta" in known and "workspace_meta" not in bang_lech:
        from .ket_noi import DAU_NAP_XONG
        dau = one(f"SELECT 1 FROM {qs}.workspace_meta WHERE key = %s", (DAU_NAP_XONG,)) is not None
    if ds:
        return {"trang_thai": CO_DU_LIEU, "dau": dau, "chi_tiet": sorted(set(ds))}
    loi += lech + [f"SEED_KHONG_DOC:{t}" for t in khong_doc]
    if loi:
        return {"trang_thai": KHONG_TUONG_THICH, "dau": dau, "chi_tiet": sorted(set(loi))}
    if version < database.SCHEMA_VERSION:
        return {"trang_thai": CU, "dau": dau, "chi_tiet": [f"VERSION_{version}"]}
    return {"trang_thai": MOI_KHOP, "dau": dau, "chi_tiet": []}


def kiem_nguon_sao_luu(raw, schema: str) -> int:
    """Preflight CHỈ ĐỌC cho nguồn sao lưu (F5): namespace có, shape ``schema_migrations`` đúng, lịch sử không trùng/liên tục/đúng
    checksum và ĐÚNG phiên bản hiện hành — để mở nguồn không bao giờ nâng cấp/ghi schema. Trả version."""
    with raw.transaction(force_rollback=True):
        raw.execute("SET TRANSACTION READ ONLY")
        if not raw.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", (schema,)).fetchone():
            raise DataError("PG_SCHEMA_MISSING", f"Chưa có schema {schema} trên PostgreSQL.")
        loi = _kiem_schema_migrations(raw, schema)
        if loi:
            raise DataError("PG_NGUON_KHONG_TUONG_THICH", f"Nguồn sao lưu không đúng hợp đồng lịch sử ({loi}) — không mở, không nâng cấp.")
        loi, version = _lich_su(raw.execute(f"SELECT version, checksum FROM {_q(schema)}.schema_migrations").fetchall())
    if loi == "SCHEMA_TUONG_LAI":
        raise DataError("FUTURE_SCHEMA", "Schema V12 nguồn mới hơn mã; không sao lưu bằng mã cũ.")
    if loi:
        raise DataError("PG_NGUON_KHONG_TUONG_THICH", f"Lịch sử migration nguồn không hợp lệ ({loi}) — không mở, không nâng cấp.")
    if version != database.SCHEMA_VERSION:
        raise DataError("PG_NGUON_SCHEMA_CU", "Nguồn có schema V12 cũ hơn phần mềm — đường sao lưu không nâng cấp nguồn; nâng cấp riêng "
                                              "(có sao lưu trước) rồi chạy lại.")
    return version


def phan_loai_sqlite(conn: sqlite3.Connection) -> dict:
    """Phân loại DB SQLite đích (đã mở). Kiểm shape ``schema_migrations`` trước khi đọc lịch sử; so đối tượng schema đúng từng câu SQL
    với hợp đồng ở đúng version. Chỉ đọc."""
    objects = {tuple(r) for r in conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}
    app = conn.execute("PRAGMA application_id").fetchone()[0]
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if not objects and not version and not app:
        return {"trang_thai": TRONG_HOAN_TOAN, "dau": False, "chi_tiet": []}
    loi = []
    if app != database.APPLICATION_ID:
        loi.append("APPLICATION_ID_LA")
    sm_mau = {o for o in hop_dong()["sqlite_objects"] if o[2] == "schema_migrations"}
    sm = {o for o in objects if o[2] == "schema_migrations"}
    v_ls = 0
    if not sm:
        loi.append("THIEU_SCHEMA_MIGRATIONS")
    elif sm != sm_mau:
        loi.append("SCHEMA_MIGRATIONS_LECH")
    else:
        loi_ls, v_ls = _lich_su(conn.execute("SELECT version, checksum FROM schema_migrations").fetchall())
        if loi_ls:
            loi.append(loi_ls)
    if v_ls != version:
        loi.append("USER_VERSION_LECH")
    hd = hop_dong(v_ls if not loi and 1 <= v_ls <= database.SCHEMA_VERSION else None)
    tables = {o[1] for o in objects if o[0] == "table"}
    known = [t for t in hd["tables"] if t in tables]
    extra = sorted(tables - set(hd["tables"]) - {"schema_migrations"})
    lech_obj = not loi and objects != set(hd["sqlite_objects"])
    dem = lambda t: conn.execute(f"SELECT count(*) FROM {_q(t)}").fetchone()[0]  # noqa: E731
    doc = lambda t: [tuple(r) for r in conn.execute(f'SELECT {", ".join(_q(c) for c in hd["cols"][t])} FROM {_q(t)} ORDER BY rowid')]  # noqa: E731
    doc_duoc = lambda t: [r[1] for r in conn.execute(f'PRAGMA table_info("{t}")')] == hd["cols"][t]  # noqa: E731
    ds, khong_doc = _du_lieu(dem, doc, known, hd["seed"], doc_duoc)
    ds += [t for t in extra if dem(t)]
    from .ket_noi import DAU_NAP_XONG
    dau = "workspace_meta" in tables and doc_duoc("workspace_meta") and \
        conn.execute("SELECT 1 FROM workspace_meta WHERE key = ?", (DAU_NAP_XONG,)).fetchone() is not None
    if ds:
        return {"trang_thai": CO_DU_LIEU, "dau": dau, "chi_tiet": sorted(set(ds))}
    if lech_obj:
        loi.append("DOI_TUONG_SCHEMA_LECH")
    if extra:
        loi.append("BANG_LA")
    loi += [f"SEED_KHONG_DOC:{t}" for t in khong_doc]
    if loi:
        return {"trang_thai": KHONG_TUONG_THICH, "dau": dau, "chi_tiet": sorted(set(loi))}
    if version < database.SCHEMA_VERSION:
        return {"trang_thai": CU, "dau": dau, "chi_tiet": [f"VERSION_{version}"]}
    return {"trang_thai": MOI_KHOP, "dau": dau, "chi_tiet": []}


def tu_choi_neu_khong_moi(tt: dict, *, dich: str, ten: str = "", cho_phep: tuple[str, ...] = (MOI_KHOP,)) -> None:
    """Từ chối đích không phải "mới" với mã nghiệp vụ cụ thể. ``dich``: 'pg' (schema ``ten``) hoặc 'sqlite'.
    Có dữ liệu → mã legacy ``PG_NAP_DO`` (PG có dấu nạp → ``PG_KHO_SQLITE_CON``); cũ → ``*_DICH_SCHEMA_CU``; còn lại → ``*_DICH_KHONG_TUONG_THICH``."""
    trang_thai = tt["trang_thai"]
    if trang_thai in cho_phep:
        return
    if trang_thai == CO_DU_LIEU:
        if dich == "pg":
            from .ket_noi import quyet_dinh_nap
            quyet_dinh_nap(tt["dau"], True, ten)  # luôn raise: PG_KHO_SQLITE_CON (có dấu nạp) / PG_NAP_DO
        raise DataError("PG_NAP_DO", f"Kho SQLite đích đã có dữ liệu ({len(tt['chi_tiet'])} bảng ngoài seed) — không chép đè. "
                                     "Chép vào một kho SQLite mới vừa khởi tạo.")
    tien_to = "PG" if dich == "pg" else "SQLITE"
    if trang_thai == CU:
        raise DataError(f"{tien_to}_DICH_SCHEMA_CU", "Đích có schema V12 cũ hơn phần mềm — không nâng cấp/chép đè trong đường nạp/chép; dùng đích mới.")
    if trang_thai in (VANG_MAT, TRONG_HOAN_TOAN):
        raise DataError(f"{tien_to}_DICH_CHUA_KHOI_TAO", "Đích chưa được khởi tạo schema V12 hiện hành.")
    raise DataError(f"{tien_to}_DICH_KHONG_TUONG_THICH", "Đích không đúng hợp đồng kho V12 mới (" + ",".join(tt["chi_tiet"][:6]) + ") — không chép.")
