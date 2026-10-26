"""MTQ-5a: test thuần và PG tùy chọn; không mở server, không xóa CSDL/vai.

Lead chạy PG ngoài sandbox với KHO_PG_DSN_TEST; mỗi module tạo kho_test_*.
"""

from __future__ import annotations

import ast
from contextlib import ExitStack
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kho_tri_thuc.ha_tang import postgres as pg
from kho_tri_thuc.ha_tang.pg_migrations import PG_SCHEMA_VERSION
from kho_tri_thuc.k2 import crm_demo, crm_g_demo, crm_khoi_dong, m4_demo, mtq_demo as demo
from kho_tri_thuc.k2.sql_ma_tran_tham_quyen import _BANG, _CATALOG


class MtqDemoTinh(unittest.TestCase):
    def test_sau_actor_rieng_admin_khong_phai_vai_nghiep_vu(self):
        actors = [demo.ADMIN, *(n[0] for n in demo.NGUOI_DUNG)]
        self.assertEqual(len(set(actors)), 6)
        self.assertTrue(all(n.startswith("MO_PHONG_MTQ_") for n in actors))
        self.assertEqual({n[2] for n in demo.NGUOI_DUNG}, set(demo.GIOI_HAN_VND))
        self.assertNotIn("ADMIN", demo.GIOI_HAN_VND)
        self.assertTrue(set(actors).isdisjoint(n[0] for n in crm_demo.NGUOI_DUNG + crm_g_demo.NGUOI_DUNG + m4_demo.NGUOI_DUNG))

    def test_han_muc_truong_phong_va_cfo(self):
        self.assertEqual(demo.GIOI_HAN_VND["TRUONG_PHONG"], 500_000_000)
        self.assertIsNone(demo.GIOI_HAN_VND["CFO"])

    def test_tick_hop_catalog_nguoi_xem_chi_xem_m9_tam_dung(self):
        catalog = {(m, man, a) for m, man, actions, _ in _CATALOG for a in actions.split()}
        modules = set()
        for phong, roles in demo.O_MAU.items():
            self.assertEqual(set(roles), set(demo.GIOI_HAN_VND), phong)
            for vai, cells in roles.items():
                actions = {a for _, _, act in cells for a in act.split()}
                for m, man, act in cells:
                    modules.add(m)
                    self.assertNotEqual(m, "M9")
                    for a in act.split():
                        self.assertIn((m, man, a), catalog)
                if vai == "NGUOI_XEM":
                    self.assertEqual(actions, {"XEM"})
                elif vai == "THUC_HIEN_1":
                    self.assertTrue(actions <= {"XEM", "LAP", "SUA"})
                    self.assertIn("LAP", actions)
                elif vai == "THUC_HIEN_2":
                    self.assertEqual(actions, {"XEM", "KIEM"})
                else:
                    self.assertEqual(actions, {"XEM", "DUYET"})
        self.assertEqual(modules, {"CRM", "M1", "M2", "M4"})
        cfo_kt = {(m, man, a) for m, man, act in demo.O_MAU["KE_TOAN"]["CFO"] for a in act.split()}
        self.assertIn(("M2", "L11", "DUYET"), cfo_kt)
        self.assertNotIn(("M5", "L11", "DUYET"), cfo_kt)
        self.assertNotEqual(demo.O_MAU["KINH_DOANH"], demo.O_MAU["DU_AN"])

    def test_khong_chay_ngoai_demo_khong_cham_ket_noi(self):
        conn = MagicMock()
        for flag in (False, None, 1, "DEMO"):
            self.assertEqual(demo.khoi_tao(conn, demo=flag)["trang_thai"], "KHONG_PHAI_DEMO")
        self.assertEqual(demo.khoi_tao(conn)["trang_thai"], "KHONG_PHAI_DEMO")
        conn.execute.assert_not_called()
        conn.transaction.assert_not_called()

    def test_ten_db_that_bi_chan_truoc_transaction(self):
        for db in ("kho_that", "postgres", "kho_crm_dem", "kho_test_", "kho_crm_demo;sql", "kho_crm_demo-that"):
            conn = MagicMock()
            conn.execute.return_value.fetchone.return_value = (db,)
            self.assertEqual(demo.khoi_tao(conn, demo=True)["trang_thai"], "KHONG_PHAI_DEMO")
            conn.transaction.assert_not_called()
            self.assertEqual(conn.execute.call_count, 1)

    def test_marker_hoac_actor_cu_khong_ghi_cap_bu(self):
        for marker in (True, False):
            conn = MagicMock()

            def mot(c, sql, params=()):
                if "current_database" in sql:
                    return "kho_crm_demo_unit"
                if "to_regclass" in sql or "bool_and" in sql:
                    return True
                if "master.he_thong" in sql:
                    return marker if params == (demo.MARKER,) else True
                if "dang_nhap=ANY" in sql:
                    return True
                if "master.phap_nhan" in sql:
                    return False
                raise AssertionError(sql)

            with patch.object(demo, "_mot", side_effect=mot), patch.object(demo, "_ghi") as ghi:
                result = demo.khoi_tao(conn, demo=True)
            self.assertEqual(result["trang_thai"], "DA_SEED" if marker else "XUNG_DOT")
            ghi.assert_not_called()
            self.assertTrue(all(c.args[0].startswith("SELECT ") for c in conn.execute.call_args_list))

    def test_khong_ghi_truc_tiep_mtq_master_legacy_khong_bat(self):
        source = Path(demo.__file__).read_text(encoding="utf-8")
        strings = [n.value for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        sql = "\n".join(strings)
        for forbidden in ("INSERT INTO master.mtq_", "UPDATE master.mtq_", "INSERT INTO master.phap_nhan", "INSERT INTO master.du_an",
                          "INSERT INTO master.phan_quyen", "UPDATE master.nguoi_dung", "KICH_HOAT"):
            self.assertNotIn(forbidden, sql)
        self.assertIn("master.mtq_bootstrap_admin", sql)
        self.assertIn("master.mtq_cau_hinh_ghi", sql)
        self.assertIn("CONG_BO", strings)

    def _khoi_dong(self, seed_error=False):
        admin, app = MagicMock(), MagicMock()
        app.__enter__.return_value = app
        driver = SimpleNamespace(connect=MagicMock(side_effect=[admin, app]), OperationalError=RuntimeError)
        conninfo = ModuleType("psycopg.conninfo")
        conninfo.make_conninfo = lambda *args, **kwargs: "FAKE"
        order = []
        with ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules, {"psycopg.conninfo": conninfo}))
            stack.enter_context(patch.object(crm_khoi_dong, "nap_driver", return_value=driver))
            stack.enter_context(patch.object(crm_khoi_dong, "kiem_cap", return_value={
                "db": "kho_crm_demo_unit", "endpoint": ("127.0.0.1", 5432), "app": {"conninfo": "FAKE"}, "admin": {"conninfo": "FAKE"}}))
            stack.enter_context(patch.object(crm_khoi_dong, "dich_thuc", return_value=(1, 2, 3, 4)))
            stack.enter_context(patch.object(crm_khoi_dong, "kiem_role_ung_dung", return_value={k: False for k in
                ("ten", "superuser", "bypassrls", "app_web", "chu_db")}))
            for name in ("schema_version", "kiem_lineage_ung_dung"):
                stack.enter_context(patch.object(pg, name, return_value=PG_SCHEMA_VERSION))
            for name in ("crm", "m5", "m2", "l11", "m4", "crm_g"):
                stack.enter_context(patch("kho_tri_thuc.k2." + name + "_demo.khoi_tao",
                                          side_effect=lambda c, n=name: order.append(n) or {}))

            def seed(c, *, demo):
                self.assertIs(c, admin)
                self.assertIs(demo, True)
                order.append("mtq")
                if seed_error:
                    raise RuntimeError("Nội dung lỗi không được lộ ra log")
                return {"trang_thai": "DU"}

            stack.enter_context(patch.object(demo, "khoi_tao", side_effect=seed))
            result = crm_khoi_dong.chuan_bi({"app_dsn": "FAKE", "admin_dsn": "FAKE"})
        self.assertEqual(order, ["crm", "m5", "m2", "l11", "m4", "crm_g", "mtq"])
        self.assertEqual(result["trang_thai"], "SAN_SANG")
        admin.close.assert_called_once()
        return result

    def test_bootstrap_demo_goi_sau_cac_seed(self):
        self.assertEqual(self._khoi_dong()["mtq_seed"]["trang_thai"], "DU")

    def test_seed_loi_co_log_crm_van_san_sang(self):
        with self.assertLogs(crm_khoi_dong.__name__, level="WARNING") as logs:
            result = self._khoi_dong(seed_error=True)
        self.assertEqual(result["mtq_seed"]["trang_thai"], "LOI")
        self.assertIn("RuntimeError", " ".join(logs.output))
        self.assertNotIn("Nội dung lỗi", " ".join(logs.output))

    def test_utf8_khong_bom(self):
        for path in (Path(demo.__file__), Path(crm_khoi_dong.__file__), Path(__file__)):
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn("\ufffd", raw.decode("utf-8"))


try:
    import psycopg
except ImportError:
    psycopg = None

DSN = os.environ.get("KHO_PG_DSN_TEST")


@unittest.skipUnless(DSN and psycopg is not None, "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG ngoài sandbox")
class MtqDemoPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo

        cls.db = "kho_test_mtq_demo_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as c:
            c.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.c = psycopg.connect(make_conninfo(DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        crm_demo.khoi_tao(cls.c)
        m4_demo.khoi_tao(cls.c)
        crm_g_demo.khoi_tao(cls.c)

    def setUp(self):
        self.c.execute("BEGIN")
        self.addCleanup(self.c.execute, "ROLLBACK")

    def mot(self, sql, params=()):
        return self.c.execute(sql, params).fetchone()[0]

    def chup(self, tables):
        from psycopg import sql
        return {t: self.mot(sql.SQL("SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) FROM {} t").format(
            sql.Identifier(*t.split(".")))) for t in tables}

    def seed(self):
        return demo.khoi_tao(self.c, demo=True)

    def admin(self):
        k = self.mot("SELECT id FROM master.nguoi_dung WHERE dang_nhap=%s", (demo.ADMIN,))
        self.c.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true),set_config('ktt.nguoi_dung_dang_nhap',%s,true)", (str(k), demo.ADMIN))

    def test_lan_dau_du_master_cu_giu_nguyen_nhat_ky_va_chua_bat(self):
        tables = ("master.phap_nhan", "master.du_an", "master.phan_quyen", "master.phan_cong_hanh_dong", "m4.quyen_du_an")
        old = self.chup(tables)
        self.assertEqual(self.seed()["trang_thai"], "DU")
        self.assertEqual(self.chup(tables), old)
        self.assertEqual(self.mot("SELECT count(*) FROM master.nguoi_dung WHERE dang_nhap=ANY(%s)",
                                 ([demo.ADMIN, *(n[0] for n in demo.NGUOI_DUNG)],)), 6)
        self.assertEqual(self.mot("SELECT count(*) FROM master.mtq_admin"), 1)
        self.assertEqual(self.mot("SELECT count(*) FROM master.mtq_phong"), 6)
        self.assertEqual(self.mot("SELECT count(*) FROM master.mtq_dong"), 30)
        self.assertEqual(self.mot("SELECT count(*) FROM master.mtq_gan_vai"), 30)
        self.assertEqual(self.mot("SELECT count(*) FROM master.mtq_pham_vi"), 31)
        self.assertEqual(self.mot("SELECT count(*) FROM master.mtq_phien_ban WHERE trang_thai='DA_CONG_BO'"), 2)
        self.assertEqual(self.mot("SELECT count(*) FROM master.mtq_kich_hoat WHERE bat"), 0)
        self.assertGreater(self.mot("SELECT count(*) FROM nhat_ky.mtq_thay_doi WHERE actor_login=%s AND ly_do=%s", (demo.ADMIN, demo.LY_DO)), 0)
        self.assertTrue(self.mot("SELECT bool_and(gioi_han_vnd=500000000) FROM master.mtq_dong WHERE vai='TRUONG_PHONG'"))
        self.assertTrue(self.mot("SELECT bool_and(gioi_han_vnd IS NULL) FROM master.mtq_dong WHERE vai='CFO'"))
        self.assertEqual(self.mot("SELECT count(*) FROM master.mtq_o o JOIN master.mtq_dong d ON d.id=o.dong_id WHERE d.vai='NGUOI_XEM' AND o.hanh_dong<>'XEM' AND o.cho_phep"), 0)
        self.assertEqual(self.mot("SELECT count(*) FROM master.mtq_o WHERE module='M9'"), 0)
        for key in demo._GUCS:
            self.assertFalse(self.mot("SELECT current_setting(%s,true)", (key,)))

    def test_lan_hai_khong_doi_dong_revision_va_nhat_ky(self):
        self.seed()
        tables = (*_BANG, "master.he_thong", "master.nguoi_dung")
        old = self.chup(tables)
        self.assertEqual(self.seed()["trang_thai"], "DA_SEED")
        self.assertEqual(self.chup(tables), old)

    def test_thu_hoi_o_tren_ban_moi_seed_khong_cap_lai(self):
        self.seed()
        self.admin()
        old = self.c.execute("SELECT id,phap_nhan_id FROM master.mtq_phien_ban ORDER BY id LIMIT 1").fetchone()
        ban = demo._ghi(self.c, "NHAP", {"phien_ban_id": str(old[0]), "phap_nhan_id": str(old[1])})
        cell = self.c.execute("SELECT o.dong_id,o.module,o.man,o.hanh_dong FROM master.mtq_o o JOIN master.mtq_dong d ON d.id=o.dong_id WHERE d.phien_ban_id=%s AND o.cho_phep LIMIT 1", (ban["id"],)).fetchone()
        data = dict(zip(("dong_id", "module", "man", "hanh_dong"), (str(cell[0]), *cell[1:])))
        demo._sua_nhap(self.c, ban, "O", {**data, "cho_phep": False})
        demo._sua_nhap(self.c, ban, "CONG_BO", {})
        snapshot = self.chup(_BANG)
        self.seed()
        self.assertEqual(self.chup(_BANG), snapshot)
        self.assertIs(self.mot("SELECT cho_phep FROM master.mtq_o WHERE dong_id=%s AND module=%s AND man=%s AND hanh_dong=%s", cell), False)

    def test_thu_hoi_vai_pham_vi_admin_khong_cap_lai(self):
        self.seed()
        self.admin()
        # Admin thứ hai giữ điều kiện không thu hồi Admin cuối cùng.
        second = self.mot("SELECT id FROM master.nguoi_dung WHERE dang_nhap=%s", (demo.NGUOI_DUNG[0][0],))
        demo._ghi(self.c, "ADMIN", {"nguoi_dung_id": str(second)})
        for table, command in (("mtq_pham_vi", "THU_HOI_PHAM_VI"), ("mtq_gan_vai", "THU_HOI_VAI"), ("mtq_admin", "THU_HOI_ADMIN")):
            k, rev = self.c.execute("SELECT id,revision FROM master." + table + " ORDER BY cap_luc LIMIT 1").fetchone()
            demo._ghi(self.c, command, {"id": str(k)}, rev)
        old = self.chup(_BANG)
        self.seed()
        self.assertEqual(self.chup(_BANG), old)

    def test_actor_co_san_khong_marker_khong_cap_bu(self):
        self.c.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro,mo_phong) VALUES ('DEMO',%s,'XEM',true)", (demo.ADMIN,))
        old = self.chup((*_BANG, "master.nguoi_dung", "master.he_thong"))
        self.assertEqual(self.seed()["trang_thai"], "XUNG_DOT")
        self.assertEqual(self.chup((*_BANG, "master.nguoi_dung", "master.he_thong")), old)

    def test_loi_giua_chung_rollback_ca_actor_va_audit(self):
        old = self.chup((*_BANG, "master.nguoi_dung", "master.he_thong"))
        real = demo._ghi

        def fail(conn, lenh, *args, **kwargs):
            if lenh == "O":
                raise RuntimeError("DEMO lỗi giữa giao dịch")
            return real(conn, lenh, *args, **kwargs)

        with patch.object(demo, "_ghi", side_effect=fail), self.assertRaises(RuntimeError):
            self.seed()
        self.assertEqual(self.chup((*_BANG, "master.nguoi_dung", "master.he_thong")), old)

    def test_master_thieu_khong_tao_master_thu_hai(self):
        old = self.chup((*_BANG, "master.nguoi_dung", "master.he_thong", "master.du_an"))
        with patch.object(demo, "_phan_giai", return_value=None):
            self.assertEqual(self.seed()["trang_thai"], "CHUA_SAN_SANG")
        self.assertEqual(self.chup((*_BANG, "master.nguoi_dung", "master.he_thong", "master.du_an")), old)


if __name__ == "__main__":
    unittest.main()
