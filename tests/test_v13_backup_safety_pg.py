"""V13 legacy backup safety trên PostgreSQL thật (GIAO-SUA-V13-LEGACY-BACKUP-02). Chỉ legacy ``KetNoiPG`` + bộ chép + backup/restore
+ CLI ``tools/sao_luu_pg.py``; KHÔNG postgres.connect/migrate/integrity, KHÔNG SQL K2. DSN chỉ lấy từ runner retained trong tiến trình
(``KHO_PG_DSN_TEST``), đặt vào khóa resolver tường minh của test; không .env, không in DSN/dòng (assert bằng vị từ boolean + thông điệp
hằng, F7). Mỗi ca dùng schema DEMO mới trong một DB ``kho_test_v13_*`` mới; giữ lại DB/schema/tệp (không DROP/DELETE/cleanup).

Fixture tự chứa (F1): cấu hình DEMO viết mới, raw DEMO tạo độc quyền, kho SQLite seed SQL trực tiếp ĐỦ 49 bảng (không Store.ingest).
- P: SQLite DEMO → StorePG (autoload) → create/verify backup → restore vào schema mới → StorePG mở lại; oracle độc lập so 49 bảng
  [rowid canonical, giá trị có kiểu] với SQLite GỐC (không chỉ PG1↔PG2), raw/config bằng nhau, lịch sử version/checksum, dấu nạp riêng.
- R1: đích có dữ liệu/seed đổi/bảng lạ; cũ trống/cũ có dữ liệu/dở dang; tiền double precision; schema_migrations thiếu applied_at /
  không PK + dòng trùng; thiếu FK; trigger lạ sửa dữ liệu; trigger bắt buộc bị tắt; chỉ mục/sequence/view lạ; namespace chỉ có
  hàm / kiểu / operator → mã cụ thể; ảnh độc lập (catalog, định nghĩa hàm, lịch sử, dữ liệu, identity, MỌI sequence) nguyên.
- R2: sequence kế tiếp đúng sau chép (int64 > 2^53 / NULL / 0 giữ đúng kiểu); rowid ẩn BIGINT_MAX → từ chối trước hiệu ứng; lỗi
  muộn ở sequence thứ 6 → MỌI sequence (last_value/is_called) + dữ liệu như trước.
- 03/R1: nguồn PG hợp lệ có rowid thực ≠ cột INTEGER PRIMARY KEY (audit_events id 100/50 với rowid sinh độc lập) → PG→SQLite và CLI
  từ chối ``PG_ROWID_ALIAS_LECH`` trước COMMIT/công bố, nguồn + đích + bản cũ nguyên; control dương kiểm rowid thực ĐỘC LẬP
  (sqlite_master + PRAGMA + cột rowid PG, không dùng alias của sản phẩm). ``chuan_pg`` dùng rowid PG thực ở mọi bảng.
- 03/R3: oracle sequence strict (RESTART: last_value = max+1, is_called=false) CHỈ ở ranh giới chép trực tiếp (N02); sau Store
  (INSERT … ON CONFLICT DO NOTHING hợp lệ có thể tiêu thụ nextval) chỉ đòi giá trị sinh kế tiếp không trùng + phép đo INSERT thật
  tách dòng DEMO mới khỏi nội dung nền.
- 03/R2 CLI: final do bên khác tạo trước khi công bố → ``DESTINATION_EXISTS``, ``final_ben_khac``, không nhận/đụng bundle bên khác;
  lỗi metadata khi kiểm kê → giữ mã lỗi gốc, ``kiem_ke=UNKNOWN``, partial vẫn còn.
- Đồng thời (giới hạn: luồng trong tiến trình + barrier monkeypatch guard, không phải tiến trình con độc lập): actor 2 bị chặn với
  đúng PID chặn = người chép, đúng relation/mode; oracle full 49 + đúng dòng của người ghi.
- CLI (giới hạn: gọi ``main`` trong tiến trình; đồng hồ cố định để hai lần cùng giây): bundle mới độc quyền khác tên; bản/partial cũ
  nguyên; nội dung bundle khớp nguồn độc lập; người ghi commit giữa chép và kiểm → vẫn thành công đúng ảnh chụp; đổi rowid → bộ kiểm
  thật phát hiện; lỗi chép / sau SHA / khi công bố → không công bố, biên nhận đúng tệp còn lại; nguồn cũ bị từ chối, không nâng cấp.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sqlite3
import tempfile
import threading
import time
import unittest
import uuid
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

try:
    import psycopg
    from psycopg.conninfo import conninfo_to_dict
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang import an_toan_sao_chep as at
from kho_tri_thuc.ha_tang import database
from kho_tri_thuc.ha_tang import sao_chep_bang as scb
from kho_tri_thuc.ha_tang.config import Config
from kho_tri_thuc.ha_tang.ket_noi import DAU_NAP_XONG, KetNoiPG, ap_dung_migration, ke_hoach_migration
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.ha_tang.sao_chep_bang import chep_pg_sang_sqlite, chep_sqlite_sang_pg

from test_v13_backup_safety import CONFIG_DEMO, INT_LON, RAW_DEMO, chuan_tac_sqlite, tao_kho_demo

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
ROOT = Path(__file__).resolve().parents[1]
KEY = "KTT_V13_BACKUP_TEST_DSN"  # khóa resolver tường minh của test (không fallback .env)
CASH = "INSERT INTO {s}.cash_account_mappings (bank_account, cash_account, source, evidence_json, updated_at, actor) VALUES ('{k}','1121','MANUAL','[]','2026-08-01T00:00:00Z','MO_PHONG')"
KNOW = ("INSERT INTO {s}.knowledge_versions (id,category,logical_key,revision,payload_json,content_hash,valid_from,known_at,evidence_json,created_at,actor) "
        "VALUES ('{k}','KEYWORD','DEMO',1,'{{}}','h','2026-01-01','2026-01-01T00:00:00Z','{{}}','2026-01-01T00:00:00Z','MO_PHONG')")
INT64_MAX = 2 ** 63 - 1


def _s():
    return "v13_" + uuid.uuid4().hex[:12]


def _ten_loi(exc) -> str:
    """Nhận dạng lỗi đã làm sạch cho thông điệp assert (không str(exc), không giá trị dòng/DSN)."""
    return f"{type(exc).__name__}:{getattr(exc, 'code', '') or getattr(getattr(exc, 'diag', None), 'sqlstate', '') or ''}"


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — không chạy được (không tính đạt)")
class V13BackupSafetyPG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = "kho_test_v13_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.bi_mat = [x for x in (cls.dsn, ADMIN_DSN, conninfo_to_dict(ADMIN_DSN).get("password")) if x]
        cls.obs = psycopg.connect(cls.dsn, autocommit=True)  # người quan sát/thiết lập DEMO
        cls.tmp = Path(tempfile.mkdtemp(prefix="ktt_v13_backup_pg_"))
        cls.env = {k: v for k, v in os.environ.items() if not k.startswith("KHO_STORAGE_")} | {KEY: cls.dsn}
        cls.goc = tao_kho_demo(cls.tmp / "goc")  # fixture DEMO tự chứa: config + raw + 49 bảng (không Store.ingest)
        cls.cfg = Config.load(cls.goc["config"], cls.goc["kho"])
        cls.src_path = cls.goc["db"]
        with contextlib.closing(sqlite3.connect(cls.src_path)) as c:
            cls.chuan_goc = chuan_tac_sqlite(c)

    @classmethod
    def tearDownClass(cls):
        cls.obs.close()  # giữ DB/schema/tệp làm bằng chứng

    # ------------------------------------------------------------------ helper
    def co_bi_mat(self, text: str) -> bool:
        return any(b in text for b in self.bi_mat)

    def conn(self, schema, **kw):
        return KetNoiPG(self.dsn, schema, **kw)

    def x(self, sql, p=()):
        cur = self.obs.execute(sql, p)
        return cur.fetchall() if cur.description else cur.rowcount

    def anh(self, schema) -> dict:
        """Ảnh ĐỘC LẬP toàn namespace (không dùng hàm sản phẩm): catalog (cột/kiểu/NOT NULL/default/identity, ràng buộc, chỉ mục,
        trigger + trạng thái bật, hàm + định nghĩa, kiểu, operator), lịch sử đủ applied_at, nội dung mọi bảng theo thứ tự ổn định, MỌI
        sequence (last_value, is_called)."""
        q = lambda sql: sorted(tuple(str(v) for v in r) for r in self.x(sql, (schema,)))  # noqa: E731
        out = {
            "rel": q("SELECT c.relname, c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s"),
            "cot": q("SELECT c.relname, a.attnum, a.attname, format_type(a.atttypid,a.atttypmod), a.attnotnull, a.attidentity, "
                     "coalesce(pg_get_expr(d.adbin,d.adrelid),'') FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid "
                     "JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum "
                     "WHERE n.nspname=%s AND a.attnum>0 AND NOT a.attisdropped"),
            "rb": q("SELECT con.conname, pg_get_constraintdef(con.oid) FROM pg_constraint con JOIN pg_namespace n ON n.oid=con.connamespace WHERE n.nspname=%s"),
            "idx": q("SELECT i.relname, pg_get_indexdef(i.oid) FROM pg_index x JOIN pg_class i ON i.oid=x.indexrelid JOIN pg_namespace n ON n.oid=i.relnamespace WHERE n.nspname=%s"),
            "trg": q("SELECT c.relname, t.tgname, t.tgenabled FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace "
                     "WHERE n.nspname=%s AND NOT t.tgisinternal"),
            "ham": q("SELECT p.proname, pg_get_function_identity_arguments(p.oid), CASE WHEN p.prokind='f' THEN pg_get_functiondef(p.oid) ELSE p.prokind::text END "
                     "FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=%s"),
            "kieu": q("SELECT t.typname, t.typtype FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname=%s"),
            "op": q("SELECT o.oprname, o.oprcode::text FROM pg_operator o JOIN pg_namespace n ON n.oid=o.oprnamespace WHERE n.nspname=%s"),
        }
        for (name, kind) in [r for r in out["rel"]]:
            qn = f'"{schema}"."{name}"'
            if kind == "S":
                out["seq:" + name] = [tuple(r) for r in self.x(f"SELECT last_value, is_called FROM {qn}")]
            elif kind in ("r", "p"):
                h = hashlib.sha256()
                for row in sorted(repr([[type(v).__name__, v.hex() if isinstance(v, (bytes, memoryview)) else str(v)] for v in r]) for r in self.x(f"SELECT * FROM {qn}")):
                    h.update(row.encode())
                out["tbl:" + name] = h.hexdigest()
        return out

    def ma(self, code, fn):
        """Mã từ chối đúng; lỗi khác chỉ báo kiểu + mã/sqlstate (không message gốc)."""
        try:
            fn()
        except DataError as exc:
            self.assertEqual(exc.code, code)
            return
        except Exception as exc:  # noqa: BLE001
            self.fail("LOI_KHONG_PHAI_TU_CHOI_NGHIEP_VU " + _ten_loi(exc))
        self.fail("KHONG_TU_CHOI")

    def dich_moi(self, **kw) -> str:
        s = _s()
        self.conn(s, **kw).close()
        return s

    def nguon(self, path=None):
        return database.connect(path or self.src_path)

    def ban_sao_nguon(self, thu_muc: Path) -> Path:
        """Bản sao kho SQLite nguồn + raw vào thư mục kho mới (API backup SQLite + chép tệp tạo mới; nguồn giữ nguyên)."""
        (thu_muc / "raw").mkdir(parents=True)
        dst = thu_muc / "kho.sqlite"
        with contextlib.closing(sqlite3.connect(self.src_path)) as a, contextlib.closing(sqlite3.connect(dst)) as b:
            a.backup(b)
        raw = f"raw/{self.goc['raw_hash']}.bin"
        with open(thu_muc / raw, "xb") as f:
            f.write((self.goc["kho"] / raw).read_bytes())
        return dst

    def chuan_pg(self, schema) -> dict:
        """Oracle 49 bảng phía PG: [rowid THỰC của PostgreSQL (cột identity ``rowid``, quan sát trực tiếp ở MỌI bảng, không dùng lựa
        chọn alias của sản phẩm), giá trị có kiểu], workspace_meta bỏ đúng khóa dấu nạp (kiểm riêng). Danh sách bảng/cột lấy từ hợp đồng
        sản phẩm (``at.hop_dong``) — phần này dựa production contract, không phải inventory độc lập."""
        out = {}
        for t in at.bang_ung_dung():
            cols = at.hop_dong()["cols"][t]
            where = f" WHERE key <> '{DAU_NAP_XONG}'" if t == "workspace_meta" else ""
            out[t] = [tuple((type(v).__name__, bytes(v) if isinstance(v, memoryview) else v) for v in r) for r in self.x(
                f'SELECT "rowid", {", ".join(chr(34) + c + chr(34) for c in cols)} FROM "{schema}"."{t}"{where} ORDER BY "rowid"')]
        return out

    def lich_su(self, s):
        return [tuple(r) for r in self.x(f'SELECT version, checksum FROM "{s}".schema_migrations ORDER BY 1')]

    def _identity(self, s):
        rows = self.x("""SELECT c.relname, a.attname, pg_get_serial_sequence(format('%%I.%%I', n.nspname, c.relname), a.attname)
                         FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
                         WHERE n.nspname=%s AND a.attidentity <> ''""", (s,))
        self.assertGreaterEqual(len(rows), 49)
        for t, col, seq in rows:
            [(m,)] = self.x(f'SELECT max("{col}") FROM "{s}"."{t}"')
            [(last, called)] = self.x(f"SELECT last_value, is_called FROM {seq}")
            yield t, col, m, last, called

    def kiem_sequence_strict(self, s):
        """CHỈ dùng ngay ranh giới chép trực tiếp (trước Store/INSERT có thể gọi nextval): mọi cột identity ở trạng thái RESTART
        — last_value = max + 1, is_called = false."""
        for t, col, m, last, called in self._identity(s):
            self.assertTrue(called is False and last == (m or 0) + 1 or (m is None and last >= 1), "SEQUENCE_SAU_CHEP_SAI")

    def kiem_sequence_an_toan(self, s):
        """Sau Store open/backup/restore/reopen: INSERT ... ON CONFLICT DO NOTHING hợp lệ có thể đã tiêu thụ nextval mà không thêm dòng,
        nên không ép trạng thái RESTART; chỉ đòi giá trị sinh kế tiếp (bước 1) > mọi giá trị đã có — không trùng."""
        for t, col, m, last, called in self._identity(s):
            ke_tiep = last + 1 if called else last
            self.assertTrue(m is None or ke_tiep > m, "SEQUENCE_KE_TIEP_CO_THE_TRUNG")

    # ------------------------------------------------------------------ P: chuỗi thật StorePG → backup → restore → StorePG
    def test_p01_storepg_backup_restore_mo_lai_bang_sqlite_goc(self):
        from kho_tri_thuc.ha_tang.backup import create_backup, restore_backup, verify_backup
        from kho_tri_thuc.ha_tang.store import Store
        s1, s2 = _s(), _s()
        d1 = self.tmp / "p01-kho-pg"
        self.ban_sao_nguon(d1)
        c1 = replace(self.cfg, data_dir=d1.resolve(), storage_engine="postgres", storage_schema=s1, storage_dsn_key=KEY)
        c2 = replace(c1, data_dir=(self.tmp / "p01-phuc-hoi").resolve(), storage_schema=s2)
        with patch.dict(os.environ, self.env, clear=True):
            with Store(c1) as st:
                self.assertEqual(st.engine, "postgres")
                self.assertIsNotNone(st.conn.da_nhap_tu_sqlite)
                create_backup(st, self.tmp / "p01-backup")
            self.assertTrue(verify_backup(self.tmp / "p01-backup")["verified"])
            self.assertEqual(restore_backup(self.tmp / "p01-backup", c2.data_dir, c2)["schema_dich"], s2)
            with Store(c2) as st2:
                self.assertIsNotNone(st2.conn.da_nhap_tu_sqlite)
        self.assertEqual(sum(1 for v in self.chuan_goc.values() if v), 49)  # gốc thật sự đủ 49 bảng có dòng
        for s in (s1, s2):
            self.assertTrue(self.chuan_pg(s) == self.chuan_goc, "PG_KHAC_SQLITE_GOC")  # rowid + giá trị có kiểu, gồm int64/NULL/0, bytea config
            self.assertEqual(self.lich_su(s), sorted(at.hop_dong()["history"].items()))
            [(v,)] = self.x(f'SELECT value FROM "{s}".workspace_meta WHERE key = %s', (DAU_NAP_XONG,))
            self.assertEqual(set(json.loads(v)), {"luc", "tong_dong"})
            self.kiem_sequence_an_toan(s)  # sau Store (ON CONFLICT DO NOTHING có thể tiêu thụ nextval): chỉ đòi kế tiếp không trùng
            self.assertEqual(self.x("SELECT attidentity FROM pg_attribute WHERE attrelid = %s::regclass AND attname = 'rowid'",
                                    (f'"{s}".documents',)), [("a",)])  # identity mode giữ ALWAYS
        with contextlib.closing(sqlite3.connect(self.tmp / "p01-backup" / "kho.sqlite")) as b:
            self.assertTrue(chuan_tac_sqlite(b) == self.chuan_goc, "BACKUP_KHAC_SQLITE_GOC")
        raw = f"raw/{self.goc['raw_hash']}.bin"
        self.assertEqual((c2.data_dir / raw).read_bytes(), RAW_DEMO)
        [(cfg,)] = self.x(f'SELECT contents FROM "{s2}".config_history')
        self.assertEqual(bytes(cfg), CONFIG_DEMO)
        # phép đo identity sinh thật sau reopen: dòng DEMO MỚI do phép đo tạo, tách khỏi nội dung nền (nền vẫn bằng SQLite gốc)
        [(max_truoc,)] = self.x(f'SELECT max(rowid) FROM "{s2}".cash_account_mappings')
        c = self.conn(s2)
        try:
            c.execute("INSERT INTO cash_account_mappings VALUES ('P01-DO-SEQ','1121','MANUAL','[]','2026-08-01T00:00:00Z','MO_PHONG')")
            c.commit()
        finally:
            c.close()
        [(rid,)] = self.x(f"""SELECT rowid FROM "{s2}".cash_account_mappings WHERE bank_account = 'P01-DO-SEQ'""")
        self.assertTrue(rid > max_truoc, "IDENTITY_SINH_KHONG_VUOT_MAX")
        nen = self.chuan_pg(s2)
        nen["cash_account_mappings"] = [r for r in nen["cash_account_mappings"] if r[1] != ("str", "P01-DO-SEQ")]
        self.assertTrue(nen == self.chuan_goc, "NOI_DUNG_NEN_DOI_SAU_PHEP_DO")

    # ------------------------------------------------------------------ R1: SQLite → PG trực tiếp
    def _ca_dich_pg(self):
        return {
            "cash_only": ("PG_NAP_DO", lambda s: self.x(CASH.format(s=f'"{s}"', k="TGT-1"))),
            "knowledge_only": ("PG_NAP_DO", lambda s: self.x(KNOW.format(s=f'"{s}"', k="k-tgt"))),
            "seed_doi": ("PG_NAP_DO", lambda s: self.x(f'UPDATE "{s}".knowledge_epoch SET revision = %s', ("khac",))),
            "dong_them": ("PG_NAP_DO", lambda s: self.x(f'INSERT INTO "{s}".workspace_meta (key, value) VALUES (%s, %s)', ("ghi_chu", "DEMO"))),
            "dau_nap": ("PG_KHO_SQLITE_CON", lambda s: self.x(f'INSERT INTO "{s}".workspace_meta (key, value) VALUES (%s, %s)', (DAU_NAP_XONG, "{}"))),
            "bang_la": ("PG_DICH_KHONG_TUONG_THICH", lambda s: self.x(f'CREATE TABLE "{s}".demo_la (a integer)')),
            "bang_la_co_dong": ("PG_NAP_DO", lambda s: (self.x(f'CREATE TABLE "{s}".demo_la (a integer)'), self.x(f'INSERT INTO "{s}".demo_la VALUES (1)'))),
            "tien_double": ("PG_DICH_KHONG_TUONG_THICH", lambda s: self.x(f'ALTER TABLE "{s}".documents ALTER COLUMN amount_minor TYPE double precision')),
            "lich_su_thieu_applied_at": ("PG_DICH_KHONG_TUONG_THICH", lambda s: self.x(f'ALTER TABLE "{s}".schema_migrations RENAME COLUMN applied_at TO applied_at_khac')),
            "trigger_la_sua_tien": ("PG_DICH_KHONG_TUONG_THICH", lambda s: (
                self.x(f'CREATE FUNCTION "{s}".demo_sua_tien() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.amount_minor := 0; RETURN NEW; END $$'),
                self.x(f'CREATE TRIGGER demo_sua_tien BEFORE INSERT ON "{s}".documents FOR EACH ROW EXECUTE FUNCTION "{s}".demo_sua_tien()'))),
            "trigger_bat_buoc_tat": ("PG_DICH_KHONG_TUONG_THICH", lambda s: self.x(
                f'ALTER TABLE "{s}".knowledge_versions DISABLE TRIGGER knowledge_epoch_knowledge_versions_insert')),
            "chi_muc_la": ("PG_DICH_KHONG_TUONG_THICH", lambda s: self.x(f'CREATE INDEX demo_idx_la ON "{s}".documents (kind)')),
            "sequence_la": ("PG_DICH_KHONG_TUONG_THICH", lambda s: self.x(f'CREATE SEQUENCE "{s}".demo_seq_la')),
            "view_la": ("PG_DICH_KHONG_TUONG_THICH", lambda s: self.x(f'CREATE VIEW "{s}".demo_view_la AS SELECT 1 AS a')),
            "ham_la_them": ("PG_DICH_KHONG_TUONG_THICH", lambda s: self.x(f'CREATE FUNCTION "{s}".demo_ham_la() RETURNS int LANGUAGE sql AS $$ SELECT 1 $$')),
        }

    def _dich_hong(self, ten: str) -> str:
        """Đích hỏng dựng riêng (không sửa đích cũ, không DROP): migration thật với một thay đổi có chủ đích."""
        s = _s()
        self.x(f'CREATE SCHEMA "{s}"')
        with self.obs.transaction():
            self.x("SELECT set_config('search_path', %s, true)", (f'"{s}", public',))
            if ten == "lich_su_khong_pk_trung":
                self.x("CREATE TABLE schema_migrations (version bigint, checksum text NOT NULL, applied_at text NOT NULL)")
            plan = ke_hoach_migration(database.SCHEMA_VERSION)
            if ten == "thieu_fk":
                plan = [(i, [st.replace("first_attempt_id text COLLATE \"C\" NOT NULL REFERENCES attempts(id) DEFERRABLE INITIALLY IMMEDIATE",
                                        "first_attempt_id text COLLATE \"C\" NOT NULL") for st in stmts], h) for i, stmts, h in plan]
                assert any("first_attempt_id text COLLATE \"C\" NOT NULL," in st for _, stmts, _ in plan for st in stmts), "FIXTURE_THIEU_FK"
            ap_dung_migration(self.obs, s, plan, 0)
            if ten == "lich_su_khong_pk_trung":
                self.x("INSERT INTO schema_migrations SELECT version, checksum, applied_at FROM schema_migrations WHERE version = 1")
        return s

    def test_n01_sqlite_sang_pg_tu_choi_truoc_thay_doi(self):
        cases = [(ten, code, lambda setup=setup: (lambda s: (setup(s), s)[1])(self.dich_moi())) for ten, (code, setup) in self._ca_dich_pg().items()]
        cases += [(ten, "PG_DICH_KHONG_TUONG_THICH", lambda ten=ten: self._dich_hong(ten)) for ten in ("thieu_fk", "lich_su_khong_pk_trung")]
        for ten, code, tao in cases:
            with self.subTest(ten):
                s = tao()
                truoc = self.anh(s)
                c, src = self.conn(s, target=self._version(s)), self.nguon()
                try:
                    self.ma(code, lambda: chep_sqlite_sang_pg(src, c))
                    self.assertFalse(c.in_transaction)
                finally:
                    c.close(); src.close()
                self.assertTrue(self.anh(s) == truoc, "DICH_BI_DOI")
        s = self.dich_moi(target=database.SCHEMA_VERSION - 1)  # cũ không dữ liệu / cũ có dữ liệu (mở với target cũ: không migrate)
        c, src = self.conn(s, target=database.SCHEMA_VERSION - 1), self.nguon()
        try:
            truoc = self.anh(s)
            self.ma("PG_DICH_SCHEMA_CU", lambda: chep_sqlite_sang_pg(src, c))
            self.assertTrue(self.anh(s) == truoc, "DICH_BI_DOI")
            self.x(CASH.format(s=f'"{s}"', k="OLD-1"))
            truoc = self.anh(s)
            self.ma("PG_NAP_DO", lambda: chep_sqlite_sang_pg(src, c))
        finally:
            c.close(); src.close()
        self.assertTrue(self.anh(s) == truoc, "DICH_BI_DOI")

    def _version(self, s) -> int:
        """Version để mở đích hỏng mà KHÔNG migrate (đích lịch sử lỗi: mở với version hiện hành, _migrate sẽ không chạy DDL)."""
        try:
            return max(1, min(database.SCHEMA_VERSION, int(self.x(f'SELECT max(version) FROM "{s}".schema_migrations')[0][0] or 1)))
        except psycopg.Error:
            return database.SCHEMA_VERSION

    def test_n02_chep_duong_sequence_int64_null_0_va_giao_dich_nguoi_goi(self):
        s = self.dich_moi()
        c, src = self.conn(s), self.nguon()
        try:
            c.execute("BEGIN")
            self.ma("ACTIVE_TRANSACTION", lambda: chep_sqlite_sang_pg(src, c))
            self.assertTrue(c.in_transaction)  # không tự commit/rollback giao dịch người gọi
            c.execute("ROLLBACK")
            kq = chep_sqlite_sang_pg(src, c)
            self.assertTrue(all(v["nguon"] == v["dich"] for v in kq.values()))
            self.assertEqual([r[0] for r in self.x('SELECT attidentity FROM pg_attribute WHERE attrelid = %s::regclass AND attname = %s',
                                                   (f'"{s}".cash_account_mappings', "rowid"))], ["a"])  # identity luôn ALWAYS, không ALTER
            self.assertTrue(self.chuan_pg(s) == self.chuan_goc, "PG_KHAC_SQLITE_GOC")
            self.assertEqual(self.x(f'SELECT id, rowid, amount_minor FROM "{s}".documents ORDER BY rowid'),
                             [("DOC-0", 1, 0), ("DOC-NULL", 2, None), ("DOC-LON", INT_LON, INT_LON)])
            self.kiem_sequence_strict(s)  # ranh giới chép trực tiếp: trước mọi INSERT/Store
            [(m,)] = self.x(f'SELECT max(rowid) FROM "{s}".cash_account_mappings')
            c.execute("INSERT INTO cash_account_mappings VALUES ('SEQ-1','1121','MANUAL','[]','2026-08-01T00:00:00Z','MO_PHONG')")
            c.commit()
            self.assertEqual(self.x(f"""SELECT rowid FROM "{s}".cash_account_mappings WHERE bank_account = 'SEQ-1'"""), [(m + 1,)])
        finally:
            c.close(); src.close()

    def test_n02b_sequence_bien_va_loi_muon_khong_doi_sequence(self):
        # rowid ẩn BIGINT_MAX ở documents (TEXT PK): nguồn hợp lệ FK nhưng sequence kế tiếp tràn → từ chối trước mọi hiệu ứng
        p = self.tmp / f"n02b-max-{uuid.uuid4().hex[:6]}.sqlite"
        with contextlib.closing(sqlite3.connect(self.src_path)) as a, contextlib.closing(sqlite3.connect(p)) as b:
            a.backup(b)
            b.execute("PRAGMA foreign_keys=ON")
            b.execute('INSERT INTO documents (rowid, id, entity_id, kind, natural_key, business_date, currency, amount_minor, core_json, core_hash, '
                      "first_attempt_id) SELECT ?, 'DOC-MAX', entity_id, kind, 'NMAX', business_date, currency, 1, core_json, core_hash, first_attempt_id "
                      "FROM documents WHERE id = 'DOC-0'", (INT64_MAX,))
            b.commit()
        for ten, nguon_path, code, bay in (("bigint_max", p, "PG_SEQUENCE_TRAN", None), ("loi_sequence_thu_6", self.src_path, "DEMO_LOI_SEQUENCE_MUON", 6)):
            with self.subTest(ten):
                s = self.dich_moi()
                truoc = self.anh(s)
                goi = []
                goc = scb._dat_sequence

                def dat(raw, seq, value):
                    goi.append(seq)
                    if bay and len(goi) == bay:
                        raise DataError("DEMO_LOI_SEQUENCE_MUON", "lỗi sequence muộn DEMO")
                    return goc(raw, seq, value)
                c, src = self.conn(s), self.nguon(nguon_path)
                try:
                    with patch.object(scb, "_dat_sequence", dat):
                        self.ma(code, lambda: chep_sqlite_sang_pg(src, c))
                finally:
                    c.close(); src.close()
                self.assertEqual(len(goi), bay or 0)  # biên: chưa đặt sequence nào; lỗi muộn: 5 sequence đã RESTART trước lỗi
                sau = self.anh(s)
                self.assertTrue(sau == truoc, "DICH_HOAC_SEQUENCE_BI_DOI")  # MỌI sequence last_value/is_called + dữ liệu như trước
                self.assertTrue(any(k.startswith("seq:") for k in sau), "KHONG_CO_SEQUENCE_DE_DO")

    # ------------------------------------------------------------------ N: PG → SQLite trực tiếp
    def test_n03_pg_sang_sqlite_tu_choi_truoc_thay_doi(self):
        s = self.dich_moi()
        c, src = self.conn(s), self.nguon()
        chep_sqlite_sang_pg(src, c)
        src.close()
        cases = {"cash_only": "INSERT INTO cash_account_mappings VALUES ('X','1121','MANUAL','[]','2026-08-01T00:00:00Z','MO_PHONG')",
                 "knowledge_only": KNOW.format(s="main", k="k-dst"), "seed_doi": "UPDATE knowledge_epoch SET revision='khac'",
                 "dong_them": "INSERT INTO workspace_meta VALUES ('ghi_chu','DEMO')", "bang_la": "CREATE TABLE demo_la (a INTEGER)"}
        try:
            for ten, sql in cases.items():
                with self.subTest(ten):
                    dst = database.connect(self.tmp / f"n03-{ten}-{uuid.uuid4().hex[:6]}.sqlite")
                    dst.execute(sql)
                    truoc = self._anh_sqlite(dst)
                    self.ma("SQLITE_DICH_KHONG_TUONG_THICH" if ten == "bang_la" else "PG_NAP_DO", lambda: chep_pg_sang_sqlite(c, dst))
                    self.assertFalse(dst.in_transaction or c.in_transaction)
                    self.assertTrue(self._anh_sqlite(dst) == truoc, "DICH_SQLITE_BI_DOI")
                    dst.close()
            ok = database.connect(self.tmp / f"n03-moi-{uuid.uuid4().hex[:6]}.sqlite")
            self.assertTrue(all(v["nguon"] == v["dich"] for v in chep_pg_sang_sqlite(c, ok).values()))  # control dương
            self.assertEqual(ok.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertTrue(chuan_tac_sqlite(ok) == self.chuan_goc, "SQLITE_KHAC_GOC")
            self.assertTrue(self.rowid_thuc_khop(s, ok), "ROWID_THUC_KHONG_GIU")
            ok.close()
        finally:
            c.close()

    def rowid_thuc_khop(self, s, sq) -> bool:
        """Quan sát ĐỘC LẬP (không dùng hợp đồng/alias của sản phẩm): danh sách bảng từ sqlite_master của tệp SQLite; với mỗi bảng,
        rowid SQLite thực (``SELECT rowid``) = rowid PG thực (cột identity ``rowid``); bảng có INTEGER PRIMARY KEY (đọc PRAGMA) thì
        thêm rowid PG thực = cột PK ở mọi dòng. workspace_meta bỏ đúng khóa dấu nạp ở cả hai phía."""
        bang = [r[0] for r in sq.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('schema_migrations') "
                                         "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        if len(bang) != 49:
            return False
        for t in bang:
            where = f" WHERE key <> '{DAU_NAP_XONG}'" if t == "workspace_meta" else ""
            a = [r[0] for r in sq.execute(f'SELECT rowid FROM "{t}"{where} ORDER BY rowid')]
            b = [r[0] for r in self.x(f'SELECT rowid FROM "{s}"."{t}"{where} ORDER BY rowid')]
            if a != b:
                return False
            pk = [r for r in sq.execute(f'PRAGMA table_info("{t}")') if r[5]]
            if len(pk) == 1 and str(pk[0][2]).upper() == "INTEGER":
                if self.x(f'SELECT count(*) FROM "{s}"."{t}" WHERE rowid IS DISTINCT FROM "{pk[0][1]}"')[0][0]:
                    return False
        return True

    # ------------------------------------------------------------------ R1 (03): rowid PG thực ≠ cột INTEGER PRIMARY KEY → từ chối
    def test_n09_rowid_pg_lech_alias_bi_tu_choi_truoc_commit_va_cong_bo(self):
        s = self.dich_moi()
        c, src = self.conn(s), self.nguon()
        chep_sqlite_sang_pg(src, c)
        src.close()
        c.close()
        # nguồn PG hiện hành hợp lệ (history/DDL/FK): audit_events có id tường minh, rowid identity sinh độc lập → (100, r1), (50, r2)
        self.x(f"""INSERT INTO "{s}".audit_events (id, at, action, attempt_id, details_json) VALUES (100, '2026-10-19T00:00:00Z', 'DEMO_LECH', NULL, '{{}}')""")
        self.x(f"""INSERT INTO "{s}".audit_events (id, at, action, attempt_id, details_json) VALUES (50, '2026-10-19T00:00:01Z', 'DEMO_LECH', NULL, '{{}}')""")
        lech = self.x(f'SELECT id, rowid FROM "{s}".audit_events WHERE rowid IS DISTINCT FROM id ORDER BY id')
        self.assertEqual(len(lech), 2)  # tiền điều kiện quan sát trực tiếp: rowid thực khác id ở hai dòng
        truoc = self.anh(s)
        c = self.conn(s)
        try:
            dst = database.connect(self.tmp / f"n09-dich-{uuid.uuid4().hex[:6]}.sqlite")
            truoc_dst = self._anh_sqlite(dst)
            self.ma("PG_ROWID_ALIAS_LECH", lambda: chep_pg_sang_sqlite(c, dst))
            self.assertFalse(dst.in_transaction or c.in_transaction)
            self.assertTrue(self._anh_sqlite(dst) == truoc_dst, "DICH_SQLITE_BI_DOI")  # chưa COMMIT gì
            dst.close()
        finally:
            c.close()
        self.assertTrue(self.anh(s) == truoc, "NGUON_BI_DOI")
        # CLI: từ chối cùng mã, không công bố, staging giữ, bản cũ nguyên
        mod = self._cli()
        thu_muc = self.tmp / "n09-sao-luu"
        thu_muc.mkdir()
        (thu_muc / "ban-cu-demo.sqlite").write_bytes(b"BAN-CU-DEMO")
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, self.env, clear=True), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = mod.main(["--schema", s, "--dsn-key", KEY, "--thu-muc", str(thu_muc)])
        self.assertFalse(self.co_bi_mat(out.getvalue() + err.getvalue()), "LO_BI_MAT_TRONG_OUTPUT")
        e = json.loads(err.getvalue())
        self.assertEqual((rc, e["ma"], e["da_cong_bo"], e["kiem_ke"]), (2, "PG_ROWID_ALIAS_LECH", False, "DAY_DU"))
        moi = sorted(p.name for p in thu_muc.iterdir() if p.name != "ban-cu-demo.sqlite")
        self.assertEqual(len(moi), 1)
        self.assertTrue(".partial-" in moi[0] and e["partial_giu_lai"] == moi[0])
        self.assertEqual((thu_muc / "ban-cu-demo.sqlite").read_bytes(), b"BAN-CU-DEMO")
        self.assertTrue(self.anh(s) == truoc, "NGUON_BI_DOI")

    @staticmethod
    def _anh_sqlite(conn):
        out = {}
        for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            out[t] = [tuple(r) for r in conn.execute(f'SELECT rowid, * FROM "{t}" ORDER BY rowid')]
        out["pragma"] = [conn.execute(f"PRAGMA {p}").fetchone()[0] for p in ("foreign_keys", "user_version", "application_id")]
        return out

    # ------------------------------------------------------------------ constructor autoload: admission trước _migrate/bootstrap
    def test_n04_constructor_autoload_truoc_migrate(self):
        def ns(sql):
            def tao():
                s = _s()
                self.x(f'CREATE SCHEMA "{s}"')
                self.x(sql.format(s=s))
                return s
            return tao
        cases = {
            "cash_hien_hanh": ("PG_NAP_DO", lambda: (lambda s: (self.x(CASH.format(s=f'"{s}"', k="C-1")), s)[1])(self.dich_moi())),
            "knowledge_hien_hanh": ("PG_NAP_DO", lambda: (lambda s: (self.x(KNOW.format(s=f'"{s}"', k="k-c")), s)[1])(self.dich_moi())),
            "cu_trong": ("PG_DICH_SCHEMA_CU", lambda: self.dich_moi(target=database.SCHEMA_VERSION - 1)),
            "cu_co_du_lieu": ("PG_NAP_DO", lambda: (lambda s: (self.x(CASH.format(s=f'"{s}"', k="C-2")), s)[1])(self.dich_moi(target=database.SCHEMA_VERSION - 1))),
            "do_dang": ("PG_DICH_KHONG_TUONG_THICH", ns('CREATE TABLE "{s}".demo_do_dang (a integer)')),
            "chi_co_ham": ("PG_DICH_KHONG_TUONG_THICH", ns("""CREATE FUNCTION "{s}".json_extract(j text, p text) RETURNS text LANGUAGE sql AS $$ SELECT 'LA_DEMO' $$""")),
            "chi_co_kieu": ("PG_DICH_KHONG_TUONG_THICH", ns("""CREATE TYPE "{s}".demo_kieu AS ENUM ('a')""")),
            "chi_co_operator": ("PG_DICH_KHONG_TUONG_THICH", ns('CREATE OPERATOR "{s}".=== (LEFTARG = text, RIGHTARG = text, FUNCTION = pg_catalog.texteq)')),
            "tien_double": ("PG_DICH_KHONG_TUONG_THICH", lambda: (lambda s: (self.x(f'ALTER TABLE "{s}".documents ALTER COLUMN amount_minor TYPE double precision'), s)[1])(self.dich_moi())),
        }
        for ten, (code, tao) in cases.items():
            with self.subTest(ten):
                s = tao()
                truoc = self.anh(s)
                p = self.ban_sao_nguon(self.tmp / f"n04-{ten}")
                h = hashlib.sha256(p.read_bytes()).hexdigest()
                self.ma(code, lambda: self.conn(s, nhap_tu_sqlite=p))
                self.assertTrue(self.anh(s) == truoc, "DICH_BI_DOI")  # lịch sử/schema/hàm lạ/sequence/identity không đổi (không migrate/bootstrap)
                self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), h)  # nguồn không đổi tên/sửa
        # counterpart: đích cũ KHÔNG autoload → nâng cấp bình thường; vắng mặt / namespace thật sự trống + autoload → tạo mới rồi nạp
        s = self.dich_moi(target=database.SCHEMA_VERSION - 1)
        self.conn(s).close()
        self.assertEqual(self.x(f'SELECT max(version) FROM "{s}".schema_migrations')[0][0], database.SCHEMA_VERSION)
        for ten, s in (("vang_mat", _s()), ("trong_that_su", (lambda s: (self.x(f'CREATE SCHEMA "{s}"'), s)[1])(_s()))):
            with self.subTest(ten):
                c = self.conn(s, nhap_tu_sqlite=self.ban_sao_nguon(self.tmp / f"n04-moi-{ten}"))
                self.assertIsNotNone(c.da_nhap_tu_sqlite)
                c.close()
                self.assertTrue(self.chuan_pg(s) == self.chuan_goc, "PG_KHAC_SQLITE_GOC")

    # ------------------------------------------------------------------ restore preflight + late open
    def test_n05_restore_preflight_va_late_open(self):
        from kho_tri_thuc.ha_tang.backup import create_backup, restore_backup
        from kho_tri_thuc.ha_tang.store import Store
        s0 = _s()
        d0 = self.tmp / "n05-kho"
        self.ban_sao_nguon(d0)
        c0 = replace(self.cfg, data_dir=d0.resolve(), storage_engine="postgres", storage_schema=s0, storage_dsn_key=KEY)
        with patch.dict(os.environ, self.env, clear=True):
            with Store(c0) as st:
                create_backup(st, self.tmp / "n05-backup")
            for ten, code, tao in (("knowledge", "PG_NAP_DO", lambda: (lambda s: (self.x(KNOW.format(s=f'"{s}"', k="k-r")), s)[1])(self.dich_moi())),
                                   ("cash", "PG_NAP_DO", lambda: (lambda s: (self.x(CASH.format(s=f'"{s}"', k="R-1")), s)[1])(self.dich_moi())),
                                   ("chi_co_ham", "PG_DICH_KHONG_TUONG_THICH", lambda: (lambda s: (self.x(f'CREATE SCHEMA "{s}"'), self.x(
                                       f"""CREATE FUNCTION "{s}".json_extract(j text, p text) RETURNS text LANGUAGE sql AS $$ SELECT 'LA_DEMO' $$"""), s)[2])(_s()))):
                with self.subTest(ten):
                    s = tao()
                    truoc = self.anh(s)
                    dich = (self.tmp / f"n05-restore-{ten}").resolve()
                    self.ma(code, lambda: restore_backup(self.tmp / "n05-backup", dich, replace(c0, data_dir=dich, storage_schema=s)))
                    self.assertFalse(dich.exists())
                    self.assertEqual(list(self.tmp.glob(f"n05-restore-{ten}*")), [])  # không publish, không staging
                    self.assertTrue(self.anh(s) == truoc, "DICH_BI_DOI")
            # late open: preflight qua (schema vắng mặt), đối thủ tạo + ghi sau preflight → mở Store từ chối, không ghi đè
            s = _s()
            dich = (self.tmp / "n05-late").resolve()
            cfg = replace(c0, data_dir=dich, storage_schema=s)
            restore_backup(self.tmp / "n05-backup", dich, cfg)
            self.conn(s).close()
            self.x(CASH.format(s=f'"{s}"', k="LATE-1"))
            truoc, h = self.anh(s), hashlib.sha256((dich / "kho.sqlite").read_bytes()).hexdigest()
            self.ma("PG_NAP_DO", lambda: Store(cfg))
            self.assertTrue(self.anh(s) == truoc, "DICH_BI_DOI")
            self.assertEqual(hashlib.sha256((dich / "kho.sqlite").read_bytes()).hexdigest(), h)

    # ------------------------------------------------------------------ đồng thời: actor 2 thật tại barrier sau guard (giới hạn: luồng, monkeypatch)
    def _race(self, writer_sql_fn, chuan_bi):
        s = self.dich_moi()
        goc = at.tu_choi_neu_khong_moi
        qua_guard, writer_xong = threading.Event(), threading.Event()
        trang = {}

        def guard_co_barrier(tt, **kw):
            goc(tt, **kw)
            if kw.get("dich") == "pg" and kw.get("ten") == s and not qua_guard.is_set():
                qua_guard.set()
                for _ in range(400):  # chờ actor 2 THỰC SỰ bị chặn bởi CHÍNH người chép (pg_locks + pg_blocking_pids)
                    if writer_xong.is_set():
                        break
                    w = self.x("SELECT l.locktype, coalesce(c.relname, ''), l.mode, pg_blocking_pids(l.pid) FROM pg_locks l "
                               "LEFT JOIN pg_class c ON c.oid = l.relation WHERE l.pid = %s AND NOT l.granted", (trang.get("pid", -1),))
                    if w:
                        trang["bi_chan"] = (w[0][0], w[0][1], w[0][2], list(w[0][3]))
                        break
                    time.sleep(0.025)

        def writer():
            try:
                qua_guard.wait(30)
                trang["ket_qua"] = writer_sql_fn(s, trang)
            except Exception as exc:  # noqa: BLE001
                trang["loi"] = _ten_loi(exc)
            finally:
                writer_xong.set()

        t = threading.Thread(target=writer, daemon=True)
        chuan_bi(s, trang)
        t.start()
        c, src = self.conn(s), self.nguon()
        trang["pid_chep"] = c.raw.info.backend_pid
        try:
            with patch.object(at, "tu_choi_neu_khong_moi", guard_co_barrier):
                kq = chep_sqlite_sang_pg(src, c)
        finally:
            c.close(); src.close()
        t.join(30)
        return s, kq, trang

    def test_n06_race_dml_tho_va_nguoi_ghi_legacy_bi_chan_dong_con_sau_chep(self):
        def dml_tho(s, trang):
            w = psycopg.connect(self.dsn, autocommit=True)
            trang["pid"] = w.info.backend_pid
            with w.transaction():
                w.execute(CASH.format(s=f'"{s}"', k="RACE-THO"))
            w.close()
            return "COMMIT"

        def mo_legacy(s, trang):  # người ghi legacy đã mở kho TRƯỚC cửa sổ chép (khóa mở-kho đã nhả)
            trang["w"] = KetNoiPG(self.dsn, s)
            trang["pid"] = trang["w"].raw.info.backend_pid

        def legacy(s, trang):
            w = trang["w"]
            w.execute("BEGIN IMMEDIATE")
            w.execute("INSERT INTO cash_account_mappings VALUES ('RACE-LEGACY','1121','MANUAL','[]','2026-08-01T00:00:00Z','MO_PHONG')")
            w.commit()
            w.close()
            return "COMMIT"

        for ten, fn, chuan_bi, khoa in (("dml_tho", dml_tho, lambda s, trang: None, ("relation", "cash_account_mappings", "RowExclusiveLock")),
                                        ("legacy", legacy, mo_legacy, ("advisory", "", "ExclusiveLock"))):
            with self.subTest(ten):
                s, kq, trang = self._race(fn, chuan_bi)
                self.assertNotIn("loi", trang, trang.get("loi", ""))  # chỉ kiểu + mã đã làm sạch
                self.assertEqual(trang.get("bi_chan", ())[:3], khoa)  # đúng loại khóa/relation/mode
                self.assertEqual(trang.get("bi_chan", (0, 0, 0, []))[3], [trang["pid_chep"]])  # đúng PID chặn = người chép
                self.assertEqual(trang.get("ket_qua"), "COMMIT")
                k = "RACE-THO" if ten == "dml_tho" else "RACE-LEGACY"
                pg_ = self.chuan_pg(s)
                cash = pg_.pop("cash_account_mappings")
                goc_cash = self.chuan_goc["cash_account_mappings"]
                mong = dict(self.chuan_goc)
                mong.pop("cash_account_mappings")
                self.assertTrue(pg_ == mong, "48_BANG_KHAC_GOC")  # full 48 bảng còn lại đúng nguồn
                max_goc = max(r[0][1] for r in goc_cash)
                ghi = (("int", max_goc + 1), ("str", k), ("str", "1121"), ("str", "MANUAL"), ("str", "[]"), ("str", "2026-08-01T00:00:00Z"), ("str", "MO_PHONG"))
                self.assertTrue(cash == goc_cash + [ghi], "CASH_KHAC_NGUON_CONG_DONG_GHI")  # đúng dòng nguồn + đúng một dòng người ghi
                self.assertTrue(all(v["nguon"] == v["dich"] for v in kq.values()))

    def test_n07_writer_thang_truoc_admission_chep_tu_choi(self):
        s = self.dich_moi()
        w = psycopg.connect(self.dsn, autocommit=True)
        with w.transaction():
            w.execute(KNOW.format(s=f'"{s}"', k="k-first"))
        w.close()
        truoc = self.anh(s)
        c, src = self.conn(s), self.nguon()
        try:
            self.ma("PG_NAP_DO", lambda: chep_sqlite_sang_pg(src, c))
        finally:
            c.close(); src.close()
        self.assertTrue(self.anh(s) == truoc, "DICH_BI_DOI")

    # ------------------------------------------------------------------ CLI backup (giới hạn: main trong tiến trình)
    def _cli(self):
        spec = importlib.util.spec_from_file_location("sao_luu_pg_v13_test", ROOT / "tools" / "sao_luu_pg.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_n08_cli_bundle_snapshot_rowid_cong_bo_va_nguon_cu(self):
        mod = self._cli()
        s = self.dich_moi()
        c, src = self.conn(s), self.nguon()
        chep_sqlite_sang_pg(src, c)
        c.close(); src.close()
        thu_muc = self.tmp / "n08-sao-luu"
        thu_muc.mkdir()
        (thu_muc / f"{s}-20260101-0000.sqlite").write_bytes(b"BAN-CU-DEMO")
        (thu_muc / f"{s}-20260101-0000.sqlite.partial").write_bytes(b"PARTIAL-CU-DEMO")
        cu = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in thu_muc.iterdir()}

        class _Gio:
            @staticmethod
            def now():
                return datetime(2026, 10, 19, 12, 0, 0)

        def chay(*extra, schema=s):
            out, err = io.StringIO(), io.StringIO()
            with patch.dict(os.environ, self.env, clear=True), patch.object(mod, "datetime", _Gio), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = mod.main(["--schema", schema, "--dsn-key", KEY, "--thu-muc", str(thu_muc), *extra])
            self.assertFalse(self.co_bi_mat(out.getvalue() + err.getvalue()), "LO_BI_MAT_TRONG_OUTPUT")
            return rc, out.getvalue(), err.getvalue()

        def ban_moi(truoc):
            return sorted(set(p.name for p in thu_muc.iterdir()) - truoc)

        # hai lần cùng giây (đồng hồ cố định): bundle khác tên, tạo độc quyền; nội dung khớp nguồn độc lập (rowid + kiểu)
        r1, o1, _ = chay("--giu", "1")
        r2, o2, _ = chay()
        self.assertEqual((r1, r2), (0, 0))
        j1, j2 = json.loads(o1), json.loads(o2)
        self.assertNotEqual(j1["thu_muc_ban"], j2["thu_muc_ban"])
        self.assertTrue(j1["thu_muc_ban"].startswith(f"{s}-20261019-120000-") and j2["thu_muc_ban"].startswith(f"{s}-20261019-120000-"))
        self.assertEqual((j1["loai"], j1["giu"]["ap_dung"]), ("LEGACY_DB_FALLBACK", False))
        nguon_pg = self.chuan_pg(s)
        for j in (j1, j2):
            f = thu_muc / j["file"]
            self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(), j["sha256"])
            self.assertEqual((f.parent / (f.name + ".sha256")).read_text(encoding="utf-8").split()[0], j["sha256"])
            self.assertEqual(sorted(p.name for p in f.parent.iterdir()), sorted([f.name, f.name + ".sha256"]))
            with contextlib.closing(sqlite3.connect(f)) as b:
                self.assertEqual(b.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertTrue(chuan_tac_sqlite(b) == nguon_pg, "BUNDLE_KHAC_NGUON")
        self.assertEqual({n: hashlib.sha256((thu_muc / n).read_bytes()).hexdigest() for n in cu}, cu)  # bản cũ/partial cũ nguyên

        that = mod.chep_pg_sang_sqlite

        def boc(truoc_kiem):  # bọc chép THẬT: chèn hành động trước bộ kiểm thật (cùng ảnh chụp)
            def fake(conn, dst, *, kiem_trong_anh_chup):
                db = Path(dst.execute("PRAGMA database_list").fetchone()[2])
                return that(conn, dst, kiem_trong_anh_chup=lambda raw: (truoc_kiem(db), kiem_trong_anh_chup(raw)))
            return fake

        # F3: người ghi hợp lệ commit GIỮA chép và kiểm → vẫn thành công, bundle đúng ảnh chụp (không có dòng mới)
        def ghi_nguon(_db):
            with psycopg.connect(self.dsn, autocommit=True) as w:
                w.execute(CASH.format(s=f'"{s}"', k="GHI-GIUA-CHEP-KIEM"))
        with patch.object(mod, "chep_pg_sang_sqlite", boc(ghi_nguon)):
            rc, o3, _ = chay()
        self.assertEqual(rc, 0)
        self.assertEqual(self.x(f"""SELECT count(*) FROM "{s}".cash_account_mappings WHERE bank_account = 'GHI-GIUA-CHEP-KIEM'""")[0][0], 1)
        with contextlib.closing(sqlite3.connect(thu_muc / json.loads(o3)["file"])) as b:
            self.assertTrue(chuan_tac_sqlite(b) == nguon_pg, "BUNDLE_KHONG_DUNG_ANH_CHUP")

        # F4: đổi giá trị rowid (giữ thứ tự/nội dung) trong tệp vừa chép → bộ kiểm THẬT phát hiện, không công bố
        def doi_rowid(db):
            with contextlib.closing(sqlite3.connect(db)) as w:
                w.execute("UPDATE workspace_meta SET rowid = rowid + 1000")
                w.commit()
        sha_that = mod._ghi_sha

        def sha_roi_loi(staging, db):  # SHA đã ghi + kiểm xong, lỗi trước công bố
            sha_that(staging, db)
            raise DataError("DEMO_LOI_SAU_SHA", "lỗi sau SHA DEMO")
        for ten, bay, code, sha_co in (
                ("loi_chep", patch.object(mod, "chep_pg_sang_sqlite", side_effect=DataError("DEMO_LOI_CHEP", "lỗi chép DEMO")), "DEMO_LOI_CHEP", False),
                ("doi_rowid", patch.object(mod, "chep_pg_sang_sqlite", boc(doi_rowid)), "BACKUP_VERIFY", False),
                ("loi_sau_sha", patch.object(mod, "_ghi_sha", sha_roi_loi), "DEMO_LOI_SAU_SHA", True),
                ("loi_cong_bo", patch.object(mod, "_cong_bo", side_effect=OSError("DEMO")), None, True)):
            with self.subTest(ten):
                truoc = set(p.name for p in thu_muc.iterdir())
                with bay:
                    rc, _, err = chay()
                moi = ban_moi(truoc)
                e = json.loads(err)
                self.assertEqual(rc, 2)
                if code:
                    self.assertEqual(e["ma"], code)
                self.assertEqual((e["da_cong_bo"], len(moi)), (False, 1))  # chỉ một thư mục partial mới, không có bundle công bố
                self.assertTrue(".partial-" in moi[0] and e["partial_giu_lai"] == moi[0])
                ton_tai = sorted(f"{moi[0]}/{p.name}" for p in (thu_muc / moi[0]).iterdir())
                self.assertEqual(e["con_lai"], [moi[0] + "/"] + ton_tai)  # biên nhận đúng tệp thực còn lại
                self.assertEqual(any(n.endswith(".sha256") for n in ton_tai), sha_co)
                self.assertEqual((e["kiem_ke"], e["final_ben_khac"], e["khong_xac_dinh"]), ("DAY_DU", False, []))

        # R2 (03): final do bên khác tạo giữa precheck và công bố → từ chối; không nhận sở hữu, không liệt kê/đụng bundle bên khác
        def sha_roi_ben_khac(staging, db):
            sha_that(staging, db)
            ben_khac = staging.parent / staging.name.split(".partial-")[0]
            ben_khac.mkdir()
            (ben_khac / "cua-ben-khac.txt").write_bytes(b"BEN-KHAC-DEMO")
        truoc = set(p.name for p in thu_muc.iterdir())
        with patch.object(mod, "_ghi_sha", sha_roi_ben_khac):
            rc, _, err = chay()
        e, moi = json.loads(err), ban_moi(truoc)
        self.assertEqual((rc, e["ma"], e["da_cong_bo"], e["final_ben_khac"], e["kiem_ke"]), (2, "DESTINATION_EXISTS", False, True, "DAY_DU"))
        part = [n for n in moi if ".partial-" in n]
        ben_khac = [n for n in moi if ".partial-" not in n]
        self.assertEqual((len(part), len(ben_khac)), (1, 1))
        self.assertEqual(e["partial_giu_lai"], part[0])
        self.assertTrue(all(x.startswith(part[0]) for x in e["con_lai"]), "BIEN_NHAN_NHAN_TAI_SAN_BEN_KHAC")
        self.assertEqual([p.name for p in (thu_muc / ben_khac[0]).iterdir()], ["cua-ben-khac.txt"])
        self.assertEqual((thu_muc / ben_khac[0] / "cua-ben-khac.txt").read_bytes(), b"BEN-KHAC-DEMO")

        # R2 (03): lỗi đọc metadata khi kiểm kê sau lỗi chép → giữ mã lỗi GỐC, kiểm kê UNKNOWN rõ, partial vẫn trên đĩa
        truoc = set(p.name for p in thu_muc.iterdir())
        with patch.object(mod, "chep_pg_sang_sqlite", side_effect=DataError("DEMO_LOI_CHEP", "lỗi chép DEMO")), \
                patch.object(mod, "_liet_ke", side_effect=OSError("DEMO_METADATA")):
            rc, _, err = chay()
        e, moi = json.loads(err), ban_moi(truoc)
        self.assertEqual((rc, e["ma"], e["kiem_ke"], e["da_cong_bo"]), (2, "DEMO_LOI_CHEP", "UNKNOWN", False))
        self.assertEqual(len(moi), 1)
        self.assertEqual((e["partial_giu_lai"], e["con_lai"], e["khong_xac_dinh"]), (moi[0], [moi[0] + "/"], [moi[0] + "/*"]))
        self.assertTrue(any(True for _ in (thu_muc / moi[0]).iterdir()), "PARTIAL_BI_MAT")  # tệp partial thực vẫn còn
        self.assertEqual({n: hashlib.sha256((thu_muc / n).read_bytes()).hexdigest() for n in cu}, cu)

        # F5: nguồn schema cũ → từ chối, KHÔNG nâng cấp nguồn
        s_cu = self.dich_moi(target=database.SCHEMA_VERSION - 1)
        truoc_anh, truoc = self.anh(s_cu), set(p.name for p in thu_muc.iterdir())
        rc, _, err = chay(schema=s_cu)
        self.assertEqual((rc, json.loads(err)["ma"]), (2, "PG_NGUON_SCHEMA_CU"))
        self.assertTrue(self.anh(s_cu) == truoc_anh, "NGUON_BI_DOI")
        self.assertEqual(self.x(f'SELECT max(version) FROM "{s_cu}".schema_migrations')[0][0], database.SCHEMA_VERSION - 1)
        self.assertTrue(all(".partial-" in n for n in ban_moi(truoc)))


if __name__ == "__main__":
    unittest.main()
