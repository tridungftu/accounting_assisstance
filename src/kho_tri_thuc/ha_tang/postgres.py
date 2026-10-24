"""Kết nối và migration PostgreSQL (V13) — cùng cách làm với database.py của SQLite.

- DSN lấy từ biến môi trường KHO_PG_DSN (ghi trong .env, không vào git) hoặc tham số.
- Migration có checksum, ghi vào master.schema_migrations; không hạ phiên bản; không chạy trên CSDL lạ.
- Chỉ cần psycopg (v3). Không ORM.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .pg_migrations import LEGACY_FULL_M9_M0013_SHA256, PG_MIGRATION_TUONG_THICH, PG_MIGRATIONS, PG_SCHEMA_VERSION
from .primitives import DataError, now_utc, sha256

# Chuỗi tùy chỉnh `migrations=` chỉ để dựng lại DB lịch sử trong kiểm thử (≤ M0012); không cài/giả COMMON13/M5 14 bằng chuỗi khác.
SO_MIGRATION_LICH_SU_TOI_DA = 12

try:  # psycopg là phụ thuộc tùy chọn: chỉ cần khi engine = postgres
    import psycopg
except ImportError:  # pragma: no cover - báo lỗi rõ ràng khi thiếu thư viện
    psycopg = None  # type: ignore[assignment]

APP_MARKER_KEY = "application_id"
APP_MARKER_VALUE = "KTT1"  # cùng ý nghĩa với APPLICATION_ID của SQLite


def doc_env_file(path: "str | os.PathLike[str]") -> dict[str, str]:
    """Đọc .env (UTF-8, chịu được BOM của PowerShell — review C2). Không in giá trị ra ngoài."""
    out: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip().strip('"')
    except OSError:
        pass
    return out


def _env_candidates() -> list[str]:
    """Thứ tự tìm .env: KHO_ENV_FILE → .env ở thư mục làm việc → .env ở gốc phần mềm (cạnh pyproject.toml)."""
    out = []
    if os.environ.get("KHO_ENV_FILE"):
        out.append(os.environ["KHO_ENV_FILE"])
    out.append(".env")
    out.append(str(Path(__file__).resolve().parents[3] / ".env"))
    return out


def dsn_from_env(default: str | None = None, key: str = "KHO_PG_DSN") -> str:
    value = default or os.environ.get(key)  # DSN truyền tường minh luôn thắng biến môi trường
    if not value:
        for env_path in _env_candidates():
            value = doc_env_file(env_path).get(key)
            if value:
                break
    if not value:
        raise DataError("PG_DSN", f"Thiếu {key} trong .env (gốc phần mềm) — chạy «CÀI POSTGRESQL.cmd» để tạo.")
    return value


def connect(dsn: str | None = None, *, migrate_on_connect: bool = True, autocommit: bool = False) -> "psycopg.Connection[Any]":
    if psycopg is None:
        raise DataError("PG_DRIVER", "Thiếu thư viện psycopg; cài: pip install \"psycopg[binary]\".")
    conn = psycopg.connect(dsn_from_env(dsn), autocommit=autocommit)
    try:
        if migrate_on_connect:
            migrate(conn)
    except BaseException:
        conn.close()
        raise
    return conn


def _current_state(conn) -> tuple[int, dict[int, str], bool]:
    """Trả về (phiên bản hiện có, lịch sử checksum, có phải CSDL của ứng dụng)."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = 'master'")
        has_master = cur.fetchone() is not None
        if not has_master:
            if _dem_doi_tuong_nguoi_dung(cur) > 0:
                raise DataError("FOREIGN_DATABASE", "Không khởi tạo trên CSDL đã có đối tượng (bảng/hàm/kiểu/sequence…) của ứng dụng khác.")
            return 0, {}, True
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema='master' AND table_name='schema_migrations'")
        if cur.fetchone() is None:
            # S05/I-S02: có schema master nhưng thiếu lịch sử ⇒ chỉ coi là "mới" khi catalog KHÔNG có đối tượng người dùng nào (DB trống đã kiểm,
            # cả hàm/enum/sequence/view/… không chỉ bảng); schema rỗng và đối tượng thuộc extension đã cài không tính. Ngược lại từ chối trước DDL.
            if _dem_doi_tuong_nguoi_dung(cur) > 0:
                raise DataError("MIGRATION_HISTORY", "CSDL có đối tượng nhưng thiếu lịch sử migration — không khởi tạo/ghi đè (partial/foreign).")
            return 0, {}, True
        cur.execute("SELECT version, checksum FROM master.schema_migrations ORDER BY version")
        rows = [(_o(r, 0, "version"), _o(r, 1, "checksum")) for r in cur.fetchall()]
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema='master' AND table_name='he_thong'")
        row = None
        if cur.fetchone() is not None:
            cur.execute("SELECT value FROM master.he_thong WHERE key = %s", (APP_MARKER_KEY,))
            row = cur.fetchone()
        if row is not None and _o(row, 0, "value") != APP_MARKER_VALUE:
            raise DataError("FOREIGN_DATABASE", "CSDL thuộc ứng dụng khác.")
        if row is None:
            # S05: schema_migrations chỉ tồn tại sau một migrate đã commit — migrate luôn ghi marker cùng giao dịch. Thiếu marker ⇒ partial/foreign,
            # không coi là DB mới; chỉ DB trống thật (không master/không bảng) mới khởi tạo.
            raise DataError("MIGRATION_HISTORY", "CSDL có bảng lịch sử nhưng thiếu marker ứng dụng — partial/foreign, từ chối trước mọi ghi.")
        version = kiem_lich_su(rows)
        return version, {int(v): c for v, c in rows}, True


# I-S02: đối tượng người dùng thật trong catalog (ngoài schema hệ thống/temp/toast), trừ thành viên extension (pg_depend 'e'). Đếm quan hệ
# (bảng/view/sequence/matview/foreign table/kiểu composite; index đi kèm bảng nên không đếm riêng), hàm/thủ tục, kiểu độc lập (enum/domain/range/
# base; bỏ kiểu dòng của quan hệ và kiểu mảng tự sinh), collation, toán tử. Schema rỗng không tính.
_SQL_DOI_TUONG_NGUOI_DUNG = r"""
WITH ns AS (SELECT n.oid FROM pg_catalog.pg_namespace n
            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
              AND n.nspname NOT LIKE 'pg\_temp\_%' AND n.nspname NOT LIKE 'pg\_toast\_temp\_%'),
     ext AS (SELECT d.classid, d.objid FROM pg_catalog.pg_depend d WHERE d.deptype = 'e')
SELECT
  (SELECT count(*) FROM pg_catalog.pg_class c WHERE c.relnamespace IN (SELECT oid FROM ns) AND c.relkind NOT IN ('i', 'I')
     AND NOT EXISTS (SELECT 1 FROM ext WHERE ext.classid = 'pg_catalog.pg_class'::regclass AND ext.objid = c.oid)) AS so_quan_he,
  (SELECT count(*) FROM pg_catalog.pg_proc p WHERE p.pronamespace IN (SELECT oid FROM ns)
     AND NOT EXISTS (SELECT 1 FROM ext WHERE ext.classid = 'pg_catalog.pg_proc'::regclass AND ext.objid = p.oid)) AS so_ham,
  (SELECT count(*) FROM pg_catalog.pg_type t WHERE t.typnamespace IN (SELECT oid FROM ns) AND t.typrelid = 0
     AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_type a WHERE a.typarray = t.oid)
     AND NOT EXISTS (SELECT 1 FROM ext WHERE ext.classid = 'pg_catalog.pg_type'::regclass AND ext.objid = t.oid)) AS so_kieu,
  (SELECT count(*) FROM pg_catalog.pg_collation k WHERE k.collnamespace IN (SELECT oid FROM ns)
     AND NOT EXISTS (SELECT 1 FROM ext WHERE ext.classid = 'pg_catalog.pg_collation'::regclass AND ext.objid = k.oid)) AS so_collation,
  (SELECT count(*) FROM pg_catalog.pg_operator o WHERE o.oprnamespace IN (SELECT oid FROM ns)
     AND NOT EXISTS (SELECT 1 FROM ext WHERE ext.classid = 'pg_catalog.pg_operator'::regclass AND ext.objid = o.oid)) AS so_toan_tu,
  (SELECT count(*) FROM pg_catalog.pg_ts_config t WHERE t.cfgnamespace IN (SELECT oid FROM ns)
     AND NOT EXISTS (SELECT 1 FROM ext WHERE ext.classid = 'pg_catalog.pg_ts_config'::regclass AND ext.objid = t.oid)) AS so_ts_config,
  (SELECT count(*) FROM pg_catalog.pg_ts_dict t WHERE t.dictnamespace IN (SELECT oid FROM ns)
     AND NOT EXISTS (SELECT 1 FROM ext WHERE ext.classid = 'pg_catalog.pg_ts_dict'::regclass AND ext.objid = t.oid)) AS so_ts_dict,
  (SELECT count(*) FROM pg_catalog.pg_ts_parser t WHERE t.prsnamespace IN (SELECT oid FROM ns)
     AND NOT EXISTS (SELECT 1 FROM ext WHERE ext.classid = 'pg_catalog.pg_ts_parser'::regclass AND ext.objid = t.oid)) AS so_ts_parser,
  (SELECT count(*) FROM pg_catalog.pg_ts_template t WHERE t.tmplnamespace IN (SELECT oid FROM ns)
     AND NOT EXISTS (SELECT 1 FROM ext WHERE ext.classid = 'pg_catalog.pg_ts_template'::regclass AND ext.objid = t.oid)) AS so_ts_template,
  (SELECT count(*) FROM pg_catalog.pg_conversion t WHERE t.connamespace IN (SELECT oid FROM ns)
     AND NOT EXISTS (SELECT 1 FROM ext WHERE ext.classid = 'pg_catalog.pg_conversion'::regclass AND ext.objid = t.oid)) AS so_conversion,
  (SELECT count(*) FROM pg_catalog.pg_opfamily t WHERE t.opfnamespace IN (SELECT oid FROM ns)
     AND NOT EXISTS (SELECT 1 FROM ext WHERE ext.classid = 'pg_catalog.pg_opfamily'::regclass AND ext.objid = t.oid)) AS so_opfamily
"""
# Repair04: thêm text-search config/dictionary/parser/template, conversion, operator family (đối tượng có namespace không nằm trong 5 lớp trên;
# opclass luôn thuộc một opfamily nên đếm opfamily đủ). Inventory hữu hạn, cùng quy tắc ns/extension — schema rỗng, extension đã cài vẫn dương.
_COT_DOI_TUONG = ("so_quan_he", "so_ham", "so_kieu", "so_collation", "so_toan_tu", "so_ts_config", "so_ts_dict", "so_ts_parser", "so_ts_template",
                  "so_conversion", "so_opfamily")


def _dem_doi_tuong_nguoi_dung(cur) -> int:
    """Tổng đối tượng người dùng trong catalog thật (bằng quyền của kết nối migrate); tuple hoặc dict_row."""
    cur.execute(_SQL_DOI_TUONG_NGUOI_DUNG)
    row = cur.fetchone()
    return sum(int(_o(row, i, k) or 0) for i, k in enumerate(_COT_DOI_TUONG))


def _o(row, i, key):
    """Giá trị cột của một dòng psycopg (tuple hoặc dict_row)."""
    return row[key] if isinstance(row, dict) else row[i]


def kiem_lich_su(rows) -> int:
    """Kiểm hình dạng lịch sử (đúng list (version, checksum), không trùng, liên tục từ 1) và lineage đã biết TRƯỚC mọi DDL/marker/seed.

    - Có đúng checksum M0013 full-M9 lịch sử (root pin) ở version 13 → LEGACY_FULL_M9_LINEAGE, kể cả DB đã có version sau 13; giữ nguyên DB.
    - Mỗi version ≤ chuỗi mặc định phải khớp checksum chuỗi mặc định (hoặc hash tiền thân liệt kê chính xác ở PG_MIGRATION_TUONG_THICH);
      version vượt chuỗi → FUTURE_SCHEMA; checksum lạ → MIGRATION_CHANGED. Không alias/rewrite/skip checksum.
    Trả về version cao nhất."""
    if not isinstance(rows, (list, tuple)):
        raise DataError("MIGRATION_HISTORY", "Lịch sử migration phải là danh sách (version, checksum).")
    versions = []
    for item in rows:
        if not isinstance(item, (list, tuple)) or len(item) != 2 or isinstance(item[0], bool) or not isinstance(item[0], int) \
                or not isinstance(item[1], str):
            raise DataError("MIGRATION_HISTORY", "Dòng lịch sử migration sai hình dạng.")
        versions.append(item[0])
    if len(versions) != len(set(versions)):
        raise DataError("MIGRATION_HISTORY", "Lịch sử migration PostgreSQL có version trùng.")
    history = dict(rows)
    if history.get(13) == LEGACY_FULL_M9_M0013_SHA256:
        raise DataError("LEGACY_FULL_M9_LINEAGE", "CSDL đã cài M0013 full-M9 lịch sử — không nâng cấp/ghép COMMON13; giữ nguyên CSDL, dùng CSDL DEMO mới.")
    version = max(versions) if versions else 0
    if sorted(versions) != list(range(1, version + 1)):
        raise DataError("MIGRATION_HISTORY", "Lịch sử migration PostgreSQL không liên tục.")
    if version > len(PG_MIGRATIONS):
        raise DataError("FUTURE_SCHEMA", "CSDL có schema mới hơn hoặc lineage lạ; không hạ phiên bản.")
    for index in range(1, version + 1):
        digest = sha256("\n".join(PG_MIGRATIONS[index - 1]).encode())
        if history[index] != digest and history[index] not in PG_MIGRATION_TUONG_THICH.get(index, {}):
            raise DataError("MIGRATION_CHANGED", f"Migration PostgreSQL {index:04d} đã áp dụng không thuộc lineage đã biết.")
    return version


def kiem_chuoi_lich_su(migrations) -> None:
    """S06: chuỗi `migrations=` tùy chỉnh chỉ được là ĐÚNG tiền tố lịch sử đã review (từng phần tử trùng checksum M000k của chuỗi mặc định), riêng
    vị trí 10 cho phép đúng tiền thân M0010 đã liệt kê ở PG_MIGRATION_TUONG_THICH; tối đa M0012. Không ghép SQL khác (kể cả M0013 full-M9)."""
    if not isinstance(migrations, tuple) or not 1 <= len(migrations) <= SO_MIGRATION_LICH_SU_TOI_DA:
        raise DataError("MIGRATION_TUY_CHINH", "Chuỗi migration tùy chỉnh chỉ dựng lại lịch sử ≤ M0012; COMMON13/M5 14 chỉ qua chuỗi mặc định.")
    for index, statements in enumerate(migrations, 1):
        digest = sha256("\n".join(statements).encode())
        if digest != sha256("\n".join(PG_MIGRATIONS[index - 1]).encode()) and digest not in PG_MIGRATION_TUONG_THICH.get(index, {}):
            raise DataError("MIGRATION_TUY_CHINH", f"Phần tử {index:04d} của chuỗi tùy chỉnh không phải định nghĩa lịch sử đã review.")


def kiem_lineage_ung_dung(conn) -> int:
    """Cổng mở ứng dụng bằng login thường: lịch sử phải đúng lineage mặc định VÀ đang ở bản mới nhất (không chỉ so max(version))."""
    with conn.cursor() as cur:
        cur.execute("SELECT version, checksum FROM master.schema_migrations ORDER BY version")
        rows = [(_o(r, 0, "version"), _o(r, 1, "checksum")) for r in cur.fetchall()]
    version = kiem_lich_su(rows)
    if version != PG_SCHEMA_VERSION:
        raise DataError("SCHEMA_CHUA_NANG_CAP", f"Schema {version} chưa đúng bản phần mềm {PG_SCHEMA_VERSION}.")
    return version


def migrate(conn, target: int | None = None, *, migrations=None) -> int:
    """Áp các migration còn thiếu trong MỘT giao dịch; trả về phiên bản schema sau khi chạy.

    ``migrations`` chỉ dùng trong kiểm thử để dựng lại đúng một DB lịch sử (vd M0010 bản bàn giao đầu); mặc định PG_MIGRATIONS.
    Checksum đã ghi không bao giờ bị sửa: nếu một migration chưa phát hành được thay bằng bản sửa, chỉ hash cũ được liệt kê
    chính xác trong PG_MIGRATION_TUONG_THICH mới được chấp nhận, và việc chấp nhận được ghi vào master.migration_tuong_thich."""
    migrations = PG_MIGRATIONS if migrations is None else migrations
    if migrations is not PG_MIGRATIONS:
        kiem_chuoi_lich_su(migrations)
    target = len(migrations) if target is None else target
    if not 1 <= target <= len(migrations):
        raise DataError("SCHEMA_VERSION", "Phiên bản schema đích không hỗ trợ.")
    version, history, _ = _current_state(conn)  # lineage kiểm xong ở đây, trước mọi CREATE/INSERT
    if version > target:
        raise DataError("FUTURE_SCHEMA", "CSDL có schema mới hơn; không hạ phiên bản.")
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS master")
            cur.execute(
                "CREATE TABLE IF NOT EXISTS master.schema_migrations (version integer PRIMARY KEY, checksum text NOT NULL, applied_at text NOT NULL)"
            )
            cur.execute("CREATE TABLE IF NOT EXISTS master.he_thong (key text PRIMARY KEY, value text NOT NULL)")
            for index, statements in enumerate(migrations[:target], 1):
                digest = sha256("\n".join(statements).encode())
                if index <= version:
                    if history.get(index) != digest:
                        if history.get(index) in PG_MIGRATION_TUONG_THICH.get(index, {}) and migrations is PG_MIGRATIONS:
                            cur.execute("""CREATE TABLE IF NOT EXISTS master.migration_tuong_thich (version integer NOT NULL, checksum_da_ghi text NOT NULL,
                                           checksum_hien_tai text NOT NULL, ghi_nhan_luc text NOT NULL, ghi_chu text NOT NULL,
                                           PRIMARY KEY (version, checksum_da_ghi, checksum_hien_tai))""")
                            cur.execute("INSERT INTO master.migration_tuong_thich VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                                        (index, history[index], digest, now_utc(), PG_MIGRATION_TUONG_THICH[index][history[index]]))
                            continue
                        raise DataError("MIGRATION_CHANGED", f"Migration PostgreSQL {index:04d} đã áp dụng bị thay đổi.")
                    continue
                for statement in statements:
                    cur.execute(statement)
                cur.execute("INSERT INTO master.schema_migrations VALUES (%s, %s, %s)", (index, digest, now_utc()))
            cur.execute(
                "INSERT INTO master.he_thong VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (APP_MARKER_KEY, APP_MARKER_VALUE),
            )
    return max(version, target)


def schema_version(conn) -> int:
    version, _, _ = _current_state(conn)
    return version


def integrity(conn) -> dict:
    """Kiểm nhanh: số bảng mỗi schema, phiên bản, mở rộng đã cài."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_schema, count(*) FROM information_schema.tables WHERE table_schema IN ('master','kho','nhat_ky','bao_mat') GROUP BY 1 ORDER BY 1"
        )
        tables = {schema: int(n) for schema, n in cur.fetchall()}
        cur.execute("SELECT extname FROM pg_extension WHERE extname IN ('unaccent','pg_trgm','pgcrypto') ORDER BY 1")
        extensions = [r[0] for r in cur.fetchall()]
    return {"version": schema_version(conn), "tables": tables, "extensions": extensions,
            "ok": tables.get("master", 0) > 0 and set(extensions) == {"pg_trgm", "pgcrypto", "unaccent"}}
