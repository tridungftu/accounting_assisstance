"""Lớp kết nối hai engine cho lõi V12 (V13 bước 5, phương án C — anh Dũng chốt 17/10/2026).

- ``engine = sqlite`` (mặc định, kho thật): trả **đúng** ``sqlite3.Connection`` như V12 — không đổi hành vi.
- ``engine = postgres`` (kho thử T8): trả ``KetNoiPG`` — cùng giao diện ``execute/commit/rollback/close/in_transaction``,
  dòng kết quả kiểu ``sqlite3.Row`` (``row[0]``, ``row["col"]``, ``dict(row)``); SQL của lõi đi qua bộ dịch
  ``dich_sqlite_pg`` rồi chạy trên các bảng V12 nguyên trạng trong schema PostgreSQL (mặc định ``v12``).
- Khi engine = postgres, mỗi dòng ``activity_log`` (Đồng ý/Sửa/Bỏ qua/Hoàn tác/xuất…) được ghi thêm vào
  ``nhat_ky.su_kien`` của schema K2 nếu có (``ghi_su_kien``) — chỉ thêm, không sửa trạng thái ``kho.*``.

Không in dữ liệu dòng ra ngoài; lỗi PostgreSQL được gói lại chỉ với sqlstate + tên ràng buộc.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from pathlib import Path

from . import database
from .dich_sqlite_pg import BOOT_STRAP, BOOT_STRAP_OPERATORS, dich_ddl, dich_sql
from .primitives import DataError, now_utc, sha256

ENGINES = ("sqlite", "postgres")
_SCHEMA_RE = re.compile(r"^[a-z_][a-z0-9_]{0,40}$")
_SCHEMA_CAM = {"public", "master", "kho", "nhat_ky", "bao_mat", "giao_tiep", "information_schema", "du_an", "rq", "crm"}
_SCHEMA_TAM = re.compile(r"^v12_[0-9a-f]{12}$")  # schema "auto" (test, so song song) — không ghi nhật ký K2
DAU_NAP_XONG = "v13_nap_tu_sqlite"  # khóa workspace_meta: kho PostgreSQL đã nạp xong từ kho.sqlite (review lần 2 #1)


def kiem_ten_schema(schema: str) -> str:
    """Tên schema V12 hợp lệ: chữ thường/số/_, không trùng schema K2/hệ thống (review lần 2 #10)."""
    if not isinstance(schema, str) or not _SCHEMA_RE.match(schema) or schema in _SCHEMA_CAM or schema.startswith("pg_"):
        raise DataError("PG_SCHEMA_NAME", "Tên schema V12 không hợp lệ hoặc trùng schema hệ thống/K2.")
    return schema
_RE_BEGIN_KHOA = re.compile(r"^\s*BEGIN\s+(IMMEDIATE|EXCLUSIVE)\b", re.IGNORECASE)
_RE_CHANGES = re.compile(r"^\s*SELECT\s+changes\(\)\s*;?\s*$", re.IGNORECASE)
_RE_DML = re.compile(r"^\s*(INSERT|UPDATE|DELETE)\b", re.IGNORECASE)


# --- dòng kết quả --------------------------------------------------------------------------------

class Hang(tuple):
    """Dòng kết quả như ``sqlite3.Row``: chỉ số, tên cột, ``keys()``, ``dict(row)``."""

    def __new__(cls, values, names):
        obj = super().__new__(cls, values)
        obj._ten = names
        return obj

    def __getitem__(self, key):
        if isinstance(key, str):
            try:
                return tuple.__getitem__(self, self._ten.index(key))
            except ValueError:
                raise IndexError("No item with that key") from None
        return tuple.__getitem__(self, key)

    def keys(self):
        return list(self._ten)


def _hang_factory(cursor):
    """Dòng kiểu sqlite3.Row; cột ``rowid`` (identity thêm cho PostgreSQL) bị ẩn như rowid ngầm của SQLite."""
    names = [d.name for d in cursor.description] if cursor.description else []
    hidden = [i for i, n in enumerate(names) if n == "rowid"]
    if hidden:
        keep = [i for i in range(len(names)) if i not in hidden]
        names = [names[i] for i in keep]

        def make(values):
            return Hang([values[i] for i in keep], names)

        return make

    def make(values):
        return Hang(values, names)

    return make


class _ConTroGiaTri:
    """Con trỏ giả trả về sẵn một danh sách dòng (changes(), PRAGMA bị bỏ → rỗng)."""

    rowcount = 0
    description = None

    def __init__(self, rows=()):
        self._rows = list(rows)

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        rows, self._rows = self._rows, []
        return rows

    def fetchmany(self, n=1):
        rows, self._rows = self._rows[:n], self._rows[n:]
        return rows

    def __iter__(self):
        return iter(self.fetchall())


def _ConTroRong():
    return _ConTroGiaTri()


# --- lỗi -----------------------------------------------------------------------------------------

class LoiCSDL(sqlite3.OperationalError):
    """Lỗi PostgreSQL gói lại cho mã V12 đang bắt ``sqlite3.Error``; chỉ mang sqlstate và tên ràng buộc."""

    def __init__(self, sqlstate, constraint, primary):
        self.sqlstate, self.constraint = sqlstate, constraint
        super().__init__(f"PostgreSQL {sqlstate or '?'}: {constraint or primary or ''}")


class LoiRangBuoc(sqlite3.IntegrityError):
    def __init__(self, sqlstate, constraint, primary):
        self.sqlstate, self.constraint = sqlstate, constraint
        super().__init__(f"PostgreSQL {sqlstate or '?'}: {constraint or primary or ''}")


_MO_TA_LOI = {"23505": "trùng khóa", "23503": "vi phạm khóa ngoại", "23502": "thiếu giá trị bắt buộc", "23514": "vi phạm điều kiện CHECK",
              "22P02": "sai kiểu dữ liệu", "22003": "số vượt giới hạn", "40P01": "tắc nghẽn giao dịch", "55P03": "hết thời gian chờ khóa",
              "25P02": "giao dịch đã lỗi", "42501": "thiếu quyền", "57014": "câu lệnh bị hủy"}


def _doi_loi(exc):
    """Chỉ giữ sqlstate + tên ràng buộc + mô tả chung; KHÔNG giữ thông điệp gốc (có thể chứa giá trị dữ liệu — review lần 2 #6)."""
    diag = getattr(exc, "diag", None)
    sqlstate = getattr(diag, "sqlstate", None) or ""
    constraint = getattr(diag, "constraint_name", None)
    cls = LoiRangBuoc if sqlstate.startswith("23") else LoiCSDL
    return cls(sqlstate, constraint, _MO_TA_LOI.get(sqlstate, "lỗi CSDL"))


_RE_DINH_DANH = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def loi_sach(exc: BaseException) -> dict:
    """Lỗi đã làm sạch cho biên CLI của tool chuyển dữ liệu (V13 A4): chỉ sqlstate, tên ràng buộc/bảng (định danh schema),
    mã DataError và mô tả chung. KHÔNG dùng str(exc), diag.message_*, traceback hay DSN — chúng có thể chứa giá trị dòng."""
    diag = getattr(exc, "diag", None)
    if diag is None:
        out = {"loi": "KHAC", "kieu": type(exc).__name__, "thong_diep": "Lỗi khi chạy; không in chi tiết để tránh lộ dữ liệu."}
        code = getattr(exc, "code", None)
        if isinstance(exc, DataError) and isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", code):
            out["ma"] = code
        return out
    sqlstate = getattr(diag, "sqlstate", None) or ""
    sqlstate = sqlstate if re.fullmatch(r"[0-9A-Z]{5}", sqlstate) else "?"
    ten = lambda v: v if isinstance(v, str) and _RE_DINH_DANH.match(v) else None
    return {"loi": "PSYCOPG", "sqlstate": sqlstate, "rang_buoc": ten(getattr(diag, "constraint_name", None)),
            "bang": ten(getattr(diag, "table_name", None)), "thong_diep": _MO_TA_LOI.get(sqlstate, "lỗi CSDL")}


def loi_du_lieu(exc, code="PG_LOI") -> DataError:
    diag = getattr(exc, "diag", None)
    sqlstate = getattr(diag, "sqlstate", None) or "?"
    return DataError(code, f"PostgreSQL {sqlstate}: {_MO_TA_LOI.get(sqlstate, 'lỗi CSDL')}.")


# --- kết nối PostgreSQL --------------------------------------------------------------------------

def quyet_dinh_nap(co_dau: bool, co_du_lieu: bool, schema: str) -> str:
    """Thư mục kho có kho.sqlite lúc mở engine postgres: chỉ nạp khi schema còn trống.
    Schema đã nạp xong (có dấu) mà lại có kho.sqlite — ví dụ bản phục hồi từ backup vào thư mục mới với schema cố định —
    thì từ chối: nếu bỏ qua, phần mềm sẽ âm thầm mở dữ liệu hiện hành thay cho bản phục hồi (V13 A3)."""
    if co_dau:
        raise DataError("PG_KHO_SQLITE_CON", f"Schema {schema} đã nạp xong nhưng thư mục kho lại có kho.sqlite (vd bản phục hồi) — không mở, "
                                             "để không âm thầm dùng dữ liệu hiện hành thay bản phục hồi. Phục hồi: đặt [storage].schema là một "
                                             "schema mới còn trống; không phục hồi: dời kho.sqlite khỏi thư mục kho.")
    if co_du_lieu:
        raise DataError("PG_NAP_DO", "Kho PostgreSQL đã có dữ liệu nhưng thư mục kho vẫn còn kho.sqlite chưa nạp — không mở để tránh lẫn hai kho. "
                                     "Dời kho.sqlite khỏi thư mục kho, hoặc nạp lại bằng tool chép (có sao lưu trước).")
    return "NAP"


def ke_hoach_migration(target: int) -> list[tuple[int, list[str], str]]:
    """Kế hoạch migration V12 cho PostgreSQL tới ``target``: (version, câu đã dịch, checksum theo câu SQLite gốc như database.py —
    sửa bộ dịch DDL không làm kho cũ báo "migration bị thay đổi", #17). Một nguồn cho mở kho và hợp đồng tham chiếu."""
    return [(i, dich, sha256("\n".join(goc).encode())) for i, (dich, goc) in enumerate(zip(KetNoiPG.translated_migrations(), database.MIGRATIONS), 1)
            if i <= target]


def ap_dung_migration(raw, schema: str, plan, version: int) -> None:
    """Tạo đối tượng V12 trong ``schema`` (search_path đã trỏ vào nó, trong giao dịch của người gọi): bảng lịch sử, BOOT_STRAP,
    operator, rồi các migration > ``version``. Dùng chung cho mở kho (``_ap_migration``) và schema tham chiếu luôn hoàn tác
    (``an_toan_sao_chep``) — cùng câu lệnh, không có đường tạo đối tượng thứ hai."""
    raw.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version bigint PRIMARY KEY, checksum text NOT NULL, applied_at text NOT NULL)")
    for statement in BOOT_STRAP:
        raw.execute(statement)
    for right, fn in BOOT_STRAP_OPERATORS:
        have = raw.execute(
            "SELECT 1 FROM pg_operator o JOIN pg_namespace n ON n.oid = o.oprnamespace WHERE n.nspname = %s AND o.oprname = '=' "
            "AND o.oprleft = 'text'::regtype AND o.oprright = %s::regtype",
            (schema, right),
        ).fetchone()
        if not have:
            raw.execute(f"CREATE OPERATOR = (LEFTARG = text, RIGHTARG = {right}, FUNCTION = {fn})")
    for index, statements, digest in plan:
        if index <= version:
            continue
        for statement in statements:
            raw.execute(statement)
        raw.execute("INSERT INTO schema_migrations VALUES (%s, %s, %s)", (index, digest, now_utc()))


class KetNoiPG:
    engine = "postgres"

    def _mo_raw(self, dsn: str, schema: str):
        """Kết nối + kiểu dữ liệu + timeout (dùng chung cho mở kho thường và mở nguồn sao lưu chỉ đọc)."""
        try:
            import psycopg
            from psycopg import pq
            from psycopg.adapt import Dumper, Loader
            from psycopg.types.string import StrDumperUnknown
        except ImportError:  # pragma: no cover
            raise DataError("PG_DRIVER", "Thiếu thư viện psycopg; cài: pip install \"psycopg[binary]\".")
        kiem_ten_schema(schema)
        self._psycopg, self._pq = psycopg, pq
        self.schema = schema
        self.row_factory = None  # mã V12 có thể gán sqlite3.Row; bỏ qua
        self._co_nhat_ky = None
        self.moi_tao = False  # True khi chính lần mở này tạo schema (kho PostgreSQL trống)
        self.da_nhap_tu_sqlite = None
        self._so_dong_vua_doi = 0
        try:
            self.raw = psycopg.connect(dsn, autocommit=True, row_factory=_hang_factory)
        except psycopg.Error as exc:
            raise loi_du_lieu(exc, "PG_KET_NOI") from None
        try:
            self._dang_ky_kieu(Dumper, Loader, StrDumperUnknown)
            # SQLite có busy_timeout 15 s; PostgreSQL: chờ khóa tối đa 15 s, giao dịch treo quá 15 phút bị cắt (review lần 2 #18)
            self.raw.execute("SET lock_timeout = '15s'")
            self.raw.execute("SET idle_in_transaction_session_timeout = '15min'")
        except BaseException:
            self.raw.close()
            raise
        return psycopg

    @classmethod
    def mo_nguon_sao_luu(cls, dsn: str, schema: str) -> "KetNoiPG":
        """Mở schema V12 làm NGUỒN sao lưu (F5): preflight chỉ đọc (lịch sử đúng + đúng phiên bản hiện hành), KHÔNG bao giờ gọi
        _migrate/bootstrap — nguồn cũ/lạ bị từ chối thay vì bị nâng cấp trước khi sao lưu. Đường mở thường giữ nguyên."""
        from . import an_toan_sao_chep as at
        self = cls.__new__(cls)
        psycopg = self._mo_raw(dsn, schema)
        try:
            at.kiem_nguon_sao_luu(self.raw, schema)
            self.raw.execute(f'SET search_path TO "{schema}", public')
        except psycopg.Error as exc:
            self.raw.close()
            raise loi_du_lieu(exc, "PG_KET_NOI") from None
        except BaseException:
            self.raw.close()
            raise
        return self

    def __init__(self, dsn: str, schema: str, *, target: int = database.SCHEMA_VERSION, nhap_tu_sqlite: "Path | None" = None,
                 tao_moi: bool = True):
        psycopg = self._mo_raw(dsn, schema)
        try:
            # Khóa phiên suốt lúc tạo schema + migrate + nạp: tiến trình thứ hai chờ, không thấy kho trống giữa chừng (#1)
            self.raw.execute("SELECT pg_advisory_lock(hashtext(%s))", ("mo-kho:" + schema,))
            try:
                co_nguon = nhap_tu_sqlite is not None and Path(nhap_tu_sqlite).is_file()
                if co_nguon:
                    # Admission TRƯỚC _migrate khi sắp nạp kho.sqlite: schema đã có phải là kho hiện hành mới đúng seed;
                    # schema cũ/dở/lạ/có dữ liệu → từ chối trước mọi thay đổi schema/lịch sử. Vắng mặt/rỗng hoàn toàn → tạo mới.
                    self._kiem_dich_nap()
                self._migrate(target, tao_moi)
                self.raw.execute(f'SET search_path TO "{schema}", public')
                if co_nguon:
                    self._nap_neu_can(Path(nhap_tu_sqlite))
            finally:
                self.raw.execute("SELECT pg_advisory_unlock(hashtext(%s))", ("mo-kho:" + schema,))
        except psycopg.Error as exc:
            self.raw.close()
            raise loi_du_lieu(exc) from None
        except BaseException:
            self.raw.close()
            raise

    def _kiem_dich_nap(self):
        """Admission dưới khóa mở-kho, trước _migrate/bootstrap: dùng chung quy tắc ``an_toan_sao_chep`` (hợp đồng vật lý, không
        sentinel); phân loại chạy trong giao dịch luôn hoàn tác nên không đổi đích."""
        from . import an_toan_sao_chep as at
        at.tu_choi_neu_khong_moi(at.phan_loai_pg(self.raw, self.schema), dich="pg", ten=self.schema,
                                 cho_phep=(at.VANG_MAT, at.TRONG_HOAN_TOAN, at.MOI_KHOP))

    def _nap_neu_can(self, path: Path):
        """"Chuyển kho sang PostgreSQL = đổi một dòng cấu hình" (TL 39 bước 8): thư mục kho có kho.sqlite →
        nạp một lần, có dấu "nạp xong" ghi cùng giao dịch chép; xong thì đổi tên kho.sqlite để không ai mở nhầm bản cũ.
        Kho PostgreSQL không phải kho mới đúng seed (có dữ liệu ở BẤT KỲ bảng nào, có dấu, cũ/lạ) → từ chối (không đoán,
        không ghi đè, không âm thầm bỏ qua kho.sqlite). Kiểm lại toàn bộ trong giao dịch chép, dưới khóa người ghi + khóa bảng."""
        from .sao_chep_bang import chep_sqlite_sang_pg
        # nguồn mở CHỈ ĐỌC: không migrate/sửa kho.sqlite nguồn (nguồn khác phiên bản → bộ chép từ chối SCHEMA_VERSION)
        src = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=15, isolation_level=None)
        try:
            self.da_nhap_tu_sqlite = chep_sqlite_sang_pg(src, self)
        finally:
            src.close()
        stamp = now_utc().replace(":", "").replace("-", "")[:15]
        for suffix in ("", "-wal", "-shm"):
            f = path.with_name(path.name + suffix)
            if f.exists():
                f.rename(path.with_name(f"kho.sqlite.da-chuyen-pg-{stamp}{suffix}"))

    # SQLite động kiểu: int/str/bool gửi dạng "chưa rõ kiểu" để máy chủ suy theo ngữ cảnh; numeric → int/float; bool → 0/1.
    def _dang_ky_kieu(self, Dumper, Loader, StrDumperUnknown):
        class ChuaRoKieu(Dumper):
            oid = 0

            def dump(self, obj):
                return str(obj).encode()

        class BoolChuaRo(Dumper):
            oid = 0

            def dump(self, obj):
                return b"1" if obj else b"0"

        class SoLoader(Loader):
            def load(self, data):
                s = bytes(data).decode()
                try:
                    return int(s)
                except ValueError:
                    return float(s)

        class BoolLoader(Loader):
            def load(self, data):
                return 1 if bytes(data) in (b"t", b"true") else 0

        ad = self.raw.adapters
        ad.register_dumper(int, ChuaRoKieu)
        ad.register_dumper(bool, BoolChuaRo)
        ad.register_dumper(str, StrDumperUnknown)
        ad.register_loader("numeric", SoLoader)
        ad.register_loader("bool", BoolLoader)

    # --- giao diện như sqlite3.Connection ---
    @property
    def in_transaction(self) -> bool:
        return self.raw.info.transaction_status != self._pq.TransactionStatus.IDLE

    def execute(self, sql: str, params=()):
        dich = dich_sql(sql)
        if dich is None:
            return _ConTroRong()
        if _RE_CHANGES.match(sql):  # SQLite changes(): số dòng của câu DML vừa chạy
            return _ConTroGiaTri([Hang((self._so_dong_vua_doi,), ["changes()"])])
        try:
            cur = self.raw.execute(dich, tuple(params) if params else None)
            if dich == "BEGIN" and _RE_BEGIN_KHOA.match(sql):
                # SQLite BEGIN IMMEDIATE = một người ghi mỗi lúc; mô phỏng bằng khóa tư vấn theo schema (hết giao dịch tự nhả)
                self.raw.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (self.schema,))
            if _RE_DML.match(dich):
                self._so_dong_vua_doi = max(cur.rowcount, 0)
            return cur
        except self._psycopg.Error as exc:
            raise _doi_loi(exc) from None

    def executemany(self, sql: str, seq):
        for params in seq:
            self.execute(sql, params)

    def commit(self):
        status = self.raw.info.transaction_status
        if status == self._pq.TransactionStatus.INERROR:
            # PostgreSQL: câu lỗi giữa giao dịch làm COMMIT thành ROLLBACK lặng lẽ → báo lỗi rõ (review lần 2 #8)
            self.raw.execute("ROLLBACK")
            raise LoiCSDL("25P02", None, "giao dịch đã lỗi, đã hoàn tác toàn bộ")
        if status != self._pq.TransactionStatus.IDLE:
            self.raw.execute("COMMIT")

    def rollback(self):
        if self.in_transaction:
            self.raw.execute("ROLLBACK")

    def close(self):
        self.raw.close()

    def backup(self, *_args, **_kwargs):
        raise DataError("PG_BACKUP", "Kho PostgreSQL sao lưu bằng pg_dump (script sao lưu V13), không dùng backup của SQLite.")

    # --- schema V12 trong PostgreSQL ---
    def _migrate(self, target: int, tao_moi: bool = True):
        raw, schema = self.raw, self.schema
        if not 1 <= target <= database.SCHEMA_VERSION:
            raise DataError("SCHEMA_VERSION", "Phiên bản schema đích không hỗ trợ.")
        exists = raw.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", (schema,)).fetchone()
        if not exists and not tao_moi:
            raise DataError("PG_SCHEMA_MISSING", f"Chưa có schema {schema} trên PostgreSQL.")
        if not exists:
            try:
                raw.execute(f'CREATE SCHEMA "{schema}"')
                self.moi_tao = True
            except self._psycopg.errors.InsufficientPrivilege:
                raise DataError("PG_SCHEMA_MISSING", f"Chưa có dữ liệu V12 trong PostgreSQL (schema {schema}). Chạy «CHUYỂN DỮ LIỆU SANG POSTGRESQL (kho thử).cmd» trước.") from None
        raw.execute(f'SET search_path TO "{schema}", public')
        has_table = raw.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = 'schema_migrations'", (schema,)
        ).fetchone()
        history = dict(raw.execute("SELECT version, checksum FROM schema_migrations").fetchall()) if has_table else {}
        version = max(history) if history else 0
        if version > target:
            raise DataError("FUTURE_SCHEMA", "Schema V12 trên PostgreSQL mới hơn mã; không hạ phiên bản.")
        if set(history) != set(range(1, version + 1)):
            raise DataError("MIGRATION_HISTORY", "Lịch sử migration V12 trên PostgreSQL không liên tục.")
        # checksum theo câu SQLite gốc (như database.py) — sửa bộ dịch DDL không làm kho cũ báo "migration bị thay đổi" (#17)
        plan = ke_hoach_migration(target)
        for index, statements, digest in plan:
            if index <= version and history[index] != digest:
                raise DataError("MIGRATION_CHANGED", f"Migration V12 {index:04d} trên PostgreSQL đã áp dụng bị thay đổi.")
        if version == target:
            return
        try:
            self._ap_migration(plan, version)
        except self._psycopg.errors.InsufficientPrivilege:
            raise DataError("PG_QUYEN", "Schema V12 cần cập nhật nhưng tài khoản ứng dụng không có quyền — chạy «CHUYỂN DỮ LIỆU SANG POSTGRESQL (kho thử).cmd» (tài khoản chủ CSDL).") from None

    def _ap_migration(self, plan, version):
        with self.raw.transaction():
            ap_dung_migration(self.raw, self.schema, plan, version)

    @staticmethod
    def translated_migrations() -> list[list[str]]:
        return [[pg for stmt in group for pg in dich_ddl(stmt)] for group in database.MIGRATIONS]

    def schema_version(self) -> int:
        row = self.raw.execute("SELECT max(version) FROM schema_migrations").fetchone()
        return int(row[0] or 0)

    def integrity(self) -> dict:
        n = self.raw.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE'", (self.schema,)
        ).fetchone()[0]
        expected = sum(1 for group in database.MIGRATIONS for s in group if s.lstrip().upper().startswith("CREATE TABLE")) + 1
        ok = int(n) == expected and self.schema_version() == database.SCHEMA_VERSION
        return {"ok": ok, "integrity": ["ok"] if ok else [f"tables={n} expected={expected}"], "foreign_keys": [], "engine": "postgres", "schema": self.schema}

    # --- nhật ký K2 ---
    def co_nhat_ky(self) -> bool:
        if self._co_nhat_ky is None:
            row = self.raw.execute("SELECT to_regclass('nhat_ky.su_kien') IS NOT NULL, to_regclass('master.phap_nhan') IS NOT NULL").fetchone()
            self._co_nhat_ky = bool(row[0]) and bool(row[1])
        return self._co_nhat_ky


# --- mở kết nối theo cấu hình --------------------------------------------------------------------

def _cho_phep_env() -> bool:
    """Biến môi trường KHO_STORAGE_* chỉ có hiệu lực khi chạy bộ test (run_suite đặt cờ) — một biến sót lại không thể
    làm kho thật mở trên PostgreSQL (review lần 2 #9)."""
    return os.environ.get("KHO_STORAGE_CHO_PHEP_ENV") == "1"


def engine_cua(config) -> str:
    engine = (os.environ.get("KHO_STORAGE_ENGINE") if _cho_phep_env() else None) or getattr(config, "storage_engine", "sqlite")
    if engine not in ENGINES:
        raise DataError("STORAGE_ENGINE", "[storage].engine chỉ nhận sqlite hoặc postgres.")
    return engine


def ten_schema(config, db_path: Path) -> str:
    schema = (os.environ.get("KHO_STORAGE_SCHEMA") if _cho_phep_env() else None) or getattr(config, "storage_schema", "v12")
    if schema == "auto":  # mỗi kho một schema (dùng cho test): đặt theo đường dẫn kho
        schema = "v12_" + sha256(str(Path(db_path).resolve()).lower().encode())[:12]
    return schema


def mo_ket_noi(config, db_path: Path):
    """Trả về kết nối theo ``[storage]`` (hoặc biến môi trường KHO_STORAGE_ENGINE/KHO_STORAGE_SCHEMA khi chạy test)."""
    if engine_cua(config) == "sqlite":
        return database.connect(db_path)
    from . import postgres

    dsn = postgres.dsn_from_env(None, key=getattr(config, "storage_dsn_key", "KHO_PG_DSN"))
    return KetNoiPG(dsn, ten_schema(config, db_path), nhap_tu_sqlite=Path(db_path))


def engine_cua_ket_noi(conn) -> str:
    return getattr(conn, "engine", "sqlite")


def da_khoi_tao(config, db_path: Path) -> bool:
    """Kho đã `init` chưa — SQLite: có file kho.sqlite; PostgreSQL: schema V12 đã tồn tại (không tự tạo)."""
    if engine_cua(config) == "sqlite":
        return Path(db_path).is_file()
    import psycopg

    from . import postgres

    dsn = postgres.dsn_from_env(None, key=getattr(config, "storage_dsn_key", "KHO_PG_DSN"))
    try:
        with psycopg.connect(dsn, autocommit=True) as raw:
            row = raw.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = 'workspace_meta'", (ten_schema(config, db_path),)).fetchone()
    except psycopg.Error as exc:
        raise loi_du_lieu(exc, "PG_KET_NOI") from None
    return row is not None or Path(db_path).is_file()  # có kho.sqlite → lần mở đầu sẽ tự nạp


def _trang_thai_schema(dsn: str, schema: str) -> tuple[bool, bool]:
    """(có dấu nạp xong, có dữ liệu) của schema V12 trên PostgreSQL theo quy tắc chung ``an_toan_sao_chep`` (mọi bảng,
    đúng seed, hợp đồng vật lý — không dùng sentinel); schema chưa có/rỗng hoàn toàn → (False, False). Schema cũ/dở/lạ/chỉ có
    hàm-kiểu-operator → từ chối với mã cụ thể. Không đổi đích: một ảnh chụp REPEATABLE READ trong giao dịch luôn hoàn tác (hợp đồng
    tham chiếu dựng trong schema tạm của chính giao dịch đó)."""
    import psycopg

    from . import an_toan_sao_chep as at

    kiem_ten_schema(schema)
    try:
        with psycopg.connect(dsn, autocommit=True) as raw:
            with raw.transaction(force_rollback=True):
                raw.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                tt = at.phan_loai_pg(raw, schema)
    except psycopg.Error as exc:
        raise loi_du_lieu(exc, "PG_KET_NOI") from None
    if tt["trang_thai"] == at.CO_DU_LIEU:
        return tt["dau"], True
    at.tu_choi_neu_khong_moi(tt, dich="pg", ten=schema, cho_phep=(at.VANG_MAT, at.TRONG_HOAN_TOAN, at.MOI_KHOP))
    return tt["dau"], False


def kiem_dich_phuc_hoi(config, db_path: Path) -> str | None:
    """Trước khi restore vào thư mục mới (V13 A3): engine postgres thì schema đích phải còn trống, nếu không từ chối
    ngay — trước khi chép file — thay vì để lần mở sau âm thầm dùng schema hiện hành. SQLite: không kiểm (đường lùi giữ nguyên).
    Trả về tên schema đích (postgres) hoặc None (sqlite)."""
    if config is None or engine_cua(config) == "sqlite":
        return None
    from . import postgres

    schema = kiem_ten_schema(ten_schema(config, db_path))
    dsn = postgres.dsn_from_env(None, key=getattr(config, "storage_dsn_key", "KHO_PG_DSN"))
    co_dau, co_du_lieu = _trang_thai_schema(dsn, schema)
    quyet_dinh_nap(co_dau, co_du_lieu, schema)
    return schema


def integrity(conn) -> dict:
    if engine_cua_ket_noi(conn) == "postgres":
        return conn.integrity()
    return database.integrity(conn)


# --- ghi nhật ký K2 khi engine = postgres --------------------------------------------------------

_LOAI = {"QUICK_DECIDE": "QUYET_DINH", "APPROVE": "QUYET_DINH", "REJECT": "QUYET_DINH", "UNDO": "QUYET_DINH", "DECIDE": "QUYET_DINH",
         "QUICK_EXPORT": "LO", "EXPORT": "LO", "AI_NOTE": "GHI_CHU_AI"}


def _loai_su_kien(module: str, action: str) -> str:
    if module == "M2" and action in ("APPROVE", "IMPORT_KNOWLEDGE_PENDING", "REVOKE"):
        return "TRI_THUC"
    if "KNOWLEDGE" in action or "LABEL" in action:
        return "TRI_THUC"
    return _LOAI.get(action, "HE_THONG")


def ghi_su_kien(conn, entity_id: str, module: str, action: str, subject, actor: str, event_at: str, details: dict) -> bool:
    """Ghi thêm một dòng ``nhat_ky.su_kien`` (chỉ khi kết nối là PostgreSQL và schema K2 có mặt). Trả True nếu đã ghi."""
    if engine_cua_ket_noi(conn) != "postgres" or not conn.co_nhat_ky():
        return False
    # nhật ký K2 không xóa được → không ghi hành động mô phỏng (actor MO_PHONG_*) hay kho tạm (schema auto) — review lần 2 #4
    if str(actor).startswith("MO_PHONG_") or _SCHEMA_TAM.match(conn.schema):
        return False
    doi_tuong_id = None
    try:
        doi_tuong_id = str(uuid.UUID(str(subject))) if subject else None
    except ValueError:
        doi_tuong_id = None
    # "kho" = schema V12 nguồn: phân biệt hành động trên kho thử (v12_thu_t8…) với kho khác cùng pháp nhân
    sau = {"subject_id": subject, "details": details, "recorded_at": now_utc(), "nguon": "v12.activity_log", "kho": conn.schema}
    try:
        conn.raw.execute(
            "INSERT INTO nhat_ky.su_kien (phap_nhan_id, luc, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau) "
            "VALUES ((SELECT id FROM master.phap_nhan WHERE ma = %s LIMIT 1), %s::timestamptz, %s, %s, %s, %s::uuid, %s, %s::jsonb)",
            (entity_id, event_at, actor, _loai_su_kien(module, action), f"v12.{module}", doi_tuong_id, action, json.dumps(sau, ensure_ascii=False, default=str)),
        )
    except conn._psycopg.Error as exc:
        raise _doi_loi(exc) from None
    return True
