"""XS-1a: hợp đồng SQL và PG riêng từ KHO_PG_DSN_TEST (DSN quản trị).

Không mở server, không đọc cấu hình/DSN DEMO, không xóa CSDL, vai hay tệp.
PG giữ nguyên toàn bộ FK/trigger; dữ liệu chỉ gồm pháp nhân/người giả.
Chạy: python -X utf8 -m unittest discover -s tests -p test_xs1_sql.py -v
(PYTHONPATH=src). Thiếu Python/psycopg/DSN: NOT_RUN, lead chạy PG.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import unittest
import uuid

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_bus_su_kien import BUS_SU_KIEN_SQL

try:
    import psycopg
except ImportError:
    psycopg = None

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src/kho_tri_thuc/k2/sql_bus_su_kien.py"
DSN = os.environ.get("KHO_PG_DSN_TEST")
DDL = "\n".join(BUS_SU_KIEN_SQL)
SIGNATURES = (
    "bus.phat(uuid,text,text,integer,text,jsonb)",
    "bus.nhan(uuid,text,text,integer)",
    "bus.ack(uuid,text,uuid)",
)


class BusSqlTinh(unittest.TestCase):
    def test_chi_hang_sql_khong_them_phu_thuoc(self):
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        self.assertEqual(len(tree.body), 2)
        self.assertEqual(ast.literal_eval(tree.body[1].value), BUS_SU_KIEN_SQL)
        self.assertTrue(all(isinstance(s, str) and s.strip() for s in BUS_SU_KIEN_SQL))

    def test_registry_chi_append_khong_ghim_cuoi_hay_hash(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# XS-1a — CD-017:"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, "exec"), old)
        previous = old["PG_MIGRATIONS"]
        self.assertEqual(PM.PG_MIGRATIONS[:len(previous)], previous)
        self.assertIs(PM.PG_MIGRATIONS[len(previous)], BUS_SU_KIEN_SQL)
        self.assertEqual(sum(m is BUS_SU_KIEN_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_phan_phap_nhan_va_khong_sua_quyen_cu(self):
        for table in ("su_kien", "inbox"):
            self.assertIn(f"ALTER TABLE bus.{table} ENABLE ROW LEVEL SECURITY", DDL)
        self.assertIn("FOREIGN KEY (phap_nhan_id, su_kien_id)", DDL)
        self.assertIn("UNIQUE (phap_nhan_id, ben_phat, khoa_dedupe)", DDL)
        self.assertIn("PRIMARY KEY (phap_nhan_id, ben_nhan, su_kien_id)", DDL)
        self.assertNotRegex(DDL, r"(?:CREATE|ALTER|DROP).*FUNCTION master\.ktt_")
        self.assertNotIn("COMMIT", DDL)

    def test_ba_cong_definer_co_guard_va_search_path_co_dinh(self):
        for name in ("phat", "nhan", "ack"):
            definition = next(s for s in BUS_SU_KIEN_SQL if s.startswith(f"CREATE FUNCTION bus.{name}("))
            self.assertIn("SECURITY DEFINER", definition)
            self.assertIn("SET search_path = pg_catalog, bus, master, pg_temp", definition)
            self.assertIn("master.ktt_pn_cho_phep()", definition)
            self.assertIn("master.ktt_duoc(", definition)
            self.assertIn("BUS_PHAM_VI", definition)

    def test_acl_chi_doc_bang_va_goi_cong(self):
        self.assertIn("REVOKE ALL ON ALL FUNCTIONS IN SCHEMA bus FROM PUBLIC", DDL)
        self.assertIn("REVOKE ALL ON ALL TABLES IN SCHEMA bus FROM PUBLIC", DDL)
        self.assertIn("GRANT SELECT ON bus.su_kien, bus.inbox TO app_web", DDL)
        self.assertIn("GRANT EXECUTE ON FUNCTION bus.phat", DDL)
        self.assertNotRegex(DDL, r"GRANT (?:INSERT|UPDATE|DELETE|ALL).*TO app_web")

    def test_utf8_khong_bom_migration_lf(self):
        for path in (MODULE, Path(PM.__file__), Path(__file__)):
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn("\ufffd", raw.decode("utf-8"))
        self.assertNotIn(b"\r", Path(PM.__file__).read_bytes())


@unittest.skipUnless(DSN and psycopg is not None, "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class BusPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = "kho_test_xs1_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.c = psycopg.connect(make_conninfo(DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c)

    def setUp(self):
        self.c.execute("BEGIN")
        self.addCleanup(self.c.execute, "ROLLBACK")
        self.pn = self.them_pn()
        self.pn2 = self.them_pn()
        self.login = "XS1_GIA_" + uuid.uuid4().hex
        self.user = self.c.execute(
            "INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro) VALUES ('Người giả XS1',%s,'XEM') RETURNING id",
            (self.login,)).fetchone()[0]
        self.quyen(self.pn, ["M2", "M3", "M4"])
        self.payload = {"chung_tu_id": str(uuid.uuid4())}
        self.c.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true), "
                       "set_config('ktt.nguoi_dung_dang_nhap',%s,true)", (str(self.user), self.login))
        self.c.execute("SET LOCAL ROLE app_web")

    def them_pn(self):
        return self.c.execute("INSERT INTO master.phap_nhan (ma,ten) VALUES (%s,'Pháp nhân giả XS1') RETURNING id",
                              ("XS1_" + uuid.uuid4().hex,)).fetchone()[0]

    def quyen(self, pn, modules):
        self.c.execute("INSERT INTO master.phan_quyen (nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,%s)",
                       (self.user, pn, modules))

    def phat(self, key="gia-1", *, pn=None, ben="M2", loai="HOA_DON_DA_NHAN", version=1, payload=None):
        return self.c.execute("SELECT bus.phat(%s,%s,%s,%s,%s,%s::jsonb)",
                              (pn or self.pn, ben, loai, version, key,
                               json.dumps(self.payload if payload is None else payload))).fetchone()[0]

    def nhan(self, ben="M4", pn=None, loai=None, limit=100):
        return [r[0] for r in self.c.execute("SELECT id FROM bus.nhan(%s,%s,%s,%s)",
                                           (pn or self.pn, ben, loai, limit)).fetchall()]

    def ack(self, event, ben="M4", pn=None):
        return self.c.execute("SELECT bus.ack(%s,%s,%s)", (pn or self.pn, ben, event)).fetchone()[0]

    def loi(self, code, fn):
        with self.assertRaises(psycopg.Error) as cm:
            with self.c.transaction():
                fn()
        self.assertIn(code, str(cm.exception))

    def test_phat_rollback_cung_nghiep_vu_khong_con_su_kien(self):
        with self.assertRaisesRegex(RuntimeError, "rollback giả"):
            with self.c.transaction():
                self.c.execute("RESET ROLE")
                pn_nghiep_vu = self.them_pn()
                self.quyen(pn_nghiep_vu, ["M2"])
                self.c.execute("SET LOCAL ROLE app_web")
                event = self.phat(pn=pn_nghiep_vu)
                self.assertEqual(self.c.execute("SELECT count(*) FROM bus.su_kien WHERE id=%s", (event,)).fetchone()[0], 1)
                raise RuntimeError("rollback giả")
        self.c.execute("RESET ROLE")
        self.assertEqual(self.c.execute("SELECT count(*) FROM bus.su_kien WHERE id=%s", (event,)).fetchone()[0], 0)
        self.assertEqual(self.c.execute("SELECT count(*) FROM master.phap_nhan WHERE id=%s", (pn_nghiep_vu,)).fetchone()[0], 0)

    def test_dedupe_cung_noi_dung_mot_dong_hash_dung(self):
        payload = {**self.payload, "lien_ket_ids": [str(uuid.uuid4()), str(uuid.uuid4())]}
        event = self.phat(payload=payload)
        self.assertEqual(self.phat(payload=dict(reversed(list(payload.items())))), event)
        rows = self.c.execute("SELECT id,payload::text,payload_sha256 FROM bus.su_kien").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], hashlib.sha256(rows[0][1].encode("utf-8")).hexdigest())

    def test_dedupe_khac_noi_dung_loai_hoac_version_bi_tu_choi(self):
        event = self.phat()
        self.loi("BUS_DEDUPE_XUNG_DOT", lambda: self.phat(payload={"chung_tu_id": str(uuid.uuid4())}))
        self.loi("BUS_DEDUPE_XUNG_DOT", lambda: self.phat(loai="KHAC"))
        self.loi("BUS_DEDUPE_XUNG_DOT", lambda: self.phat(version=2))
        self.assertEqual(self.phat(), event)

    def test_dedupe_doc_lap_theo_ben_phat_va_phap_nhan(self):
        first = self.phat()
        second = self.phat(ben="M3")
        self.c.execute("RESET ROLE")
        self.quyen(self.pn2, ["M2"])
        self.c.execute("SET LOCAL ROLE app_web")
        third = self.phat(pn=self.pn2)
        self.assertEqual(len({first, second, third}), 3)

    def test_hai_ben_nhan_ack_mot_lan_doc_lap(self):
        event = self.phat()
        self.assertEqual(self.nhan("M4"), [event])
        self.assertEqual(self.nhan("M4"), [event])
        self.assertEqual(self.nhan("M3"), [event])
        self.assertTrue(self.ack(event, "M4"))
        before = self.c.execute("SELECT ack_luc,ack_boi FROM bus.inbox WHERE ben_nhan='M4'").fetchone()
        self.assertFalse(self.ack(event, "M4"))
        self.assertEqual(self.c.execute("SELECT ack_luc,ack_boi FROM bus.inbox WHERE ben_nhan='M4'").fetchone(), before)
        self.assertEqual(self.nhan("M4"), [])
        self.assertEqual(self.nhan("M3"), [event])
        self.assertTrue(self.ack(event, "M3"))
        self.assertFalse(self.ack(event, "M3"))
        self.assertEqual(self.nhan("M3"), [])
        self.assertEqual(self.c.execute("SELECT count(*) FROM bus.inbox WHERE trang_thai='DA_ACK'").fetchone()[0], 2)
        self.assertEqual(self.c.execute("SELECT trang_thai FROM bus.su_kien WHERE id=%s", (event,)).fetchone()[0], "DA_PHAT")

    def test_ack_rollback_cho_nhan_lai(self):
        event = self.phat()
        self.nhan()
        with self.assertRaisesRegex(RuntimeError, "rollback giả"):
            with self.c.transaction():
                self.assertTrue(self.ack(event))
                raise RuntimeError("rollback giả")
        self.assertEqual(self.nhan(), [event])
        self.assertTrue(self.ack(event))

    def test_nhan_rollback_khong_de_inbox(self):
        event = self.phat()
        with self.assertRaisesRegex(RuntimeError, "rollback giả"):
            with self.c.transaction():
                self.assertEqual(self.nhan(), [event])
                raise RuntimeError("rollback giả")
        self.assertEqual(self.c.execute("SELECT count(*) FROM bus.inbox").fetchone()[0], 0)
        self.assertEqual(self.nhan(), [event])

    def test_ack_phai_nhan_truoc(self):
        event = self.phat()
        self.loi("BUS_CHUA_NHAN", lambda: self.ack(event))
        self.loi("BUS_CHUA_NHAN", lambda: self.ack(uuid.uuid4()))

    def test_sai_phap_nhan_khong_thay_khong_phat_nhan_ack(self):
        event = self.phat()
        self.nhan()
        self.c.execute("RESET ROLE")
        other_login = "XS1_KHAC_" + uuid.uuid4().hex
        other_user = self.c.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro) "
                                    "VALUES ('Người khác giả XS1',%s,'XEM') RETURNING id", (other_login,)).fetchone()[0]
        self.c.execute("INSERT INTO master.phan_quyen (nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,%s)",
                       (other_user, self.pn2, ["M2", "M4"]))
        self.c.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true), "
                       "set_config('ktt.nguoi_dung_dang_nhap',%s,true)", (str(other_user), other_login))
        self.c.execute("SET LOCAL ROLE app_web")
        for table in ("su_kien", "inbox"):
            self.assertEqual(self.c.execute(f"SELECT count(*) FROM bus.{table}").fetchone()[0], 0)
        self.loi("BUS_PHAM_VI", self.phat)
        self.loi("BUS_PHAM_VI", self.nhan)
        self.loi("BUS_PHAM_VI", lambda: self.ack(event))
        self.loi("BUS_CHUA_NHAN", lambda: self.ack(event, pn=self.pn2))
        self.assertEqual(self.nhan(pn=self.pn2), [])

    def test_thieu_module_va_gia_danh_tinh_bi_chan(self):
        event = self.phat()
        self.loi("BUS_PHAM_VI", lambda: self.phat(ben="M9"))
        self.loi("BUS_PHAM_VI", lambda: self.nhan("M9"))
        self.loi("BUS_PHAM_VI", lambda: self.ack(event, "M9"))
        self.c.execute("SELECT set_config('ktt.nguoi_dung_dang_nhap','KHONG_KHOP',true)")
        self.assertEqual(self.c.execute("SELECT count(*) FROM bus.su_kien").fetchone()[0], 0)
        self.loi("BUS_PHAM_VI", self.phat)
        self.loi("BUS_PHAM_VI", self.nhan)
        self.loi("BUS_PHAM_VI", lambda: self.ack(event))

    def test_payload_chi_uuid_khong_noi_dung_chung_tu(self):
        for payload in ({}, [], None, {"noi_dung": "Nội dung giả"}, {"chung_tu_id": "văn bản"},
                        {"chung_tu_id": None}, {"chung_tu_id": {"id": str(uuid.uuid4())}},
                        {"chung_tu_ids": ["văn bản"]}, {"chung_tu_ids": [None]}, {"chung_tu_id": 42}):
            with self.subTest(payload=payload):
                # Truyền thẳng để kiểm cả JSON null, không dùng mặc định helper.
                self.loi("BUS_DAU_VAO", lambda: self.c.execute("SELECT bus.phat(%s,'M2','GIA',1,'sai',%s::jsonb)",
                                                             (self.pn, json.dumps(payload))))
        self.assertEqual(self.c.execute("SELECT count(*) FROM bus.su_kien").fetchone()[0], 0)

    def test_loc_loai_gioi_han_va_metadata_dau_vao(self):
        event = self.phat()
        self.phat("khac", loai="KHAC")
        self.assertEqual(self.nhan(loai="HOA_DON_DA_NHAN", limit=1), [event])
        for limit in (None, 0, -1, 1001):
            self.loi("BUS_GIOI_HAN", lambda: self.nhan(limit=limit))
        for data in ({"key": ""}, {"loai": None}, {"loai": " "}, {"version": None}, {"version": 0}):
            self.loi("BUS_DAU_VAO", lambda: self.phat(**data))

    def test_acl_thuc_te_va_search_path(self):
        event = self.phat()
        for statement in ("INSERT INTO bus.su_kien DEFAULT VALUES", "UPDATE bus.su_kien SET trang_thai='DA_PHAT'",
                          "DELETE FROM bus.su_kien", "TRUNCATE bus.su_kien", "INSERT INTO bus.inbox DEFAULT VALUES",
                          "UPDATE bus.inbox SET trang_thai='DA_ACK'", "DELETE FROM bus.inbox", "TRUNCATE bus.inbox"):
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with self.c.transaction():
                    self.c.execute(statement)
        self.assertEqual(self.c.execute("SELECT id FROM bus.su_kien WHERE id=%s", (event,)).fetchone()[0], event)
        for signature in SIGNATURES:
            definer, config = self.c.execute("SELECT prosecdef,proconfig FROM pg_proc WHERE oid=%s::regprocedure",
                                            (signature,)).fetchone()
            self.assertTrue(definer)
            self.assertIn("search_path=pg_catalog, bus, master, pg_temp", config)
            self.assertTrue(self.c.execute("SELECT has_function_privilege('app_web',%s,'EXECUTE')", (signature,)).fetchone()[0])
            public_execute = self.c.execute("SELECT EXISTS (SELECT 1 FROM pg_proc p, "
                                            "LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a "
                                            "WHERE p.oid=%s::regprocedure AND a.grantee=0 AND a.privilege_type='EXECUTE')",
                                            (signature,)).fetchone()[0]
            self.assertFalse(public_execute)
        self.assertFalse(self.c.execute("SELECT has_schema_privilege('app_web','bus','CREATE')").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
