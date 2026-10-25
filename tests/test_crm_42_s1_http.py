"""S1 HTTP loopback thật trên LocalApp/LocalServer; mock DB tách khỏi PG.

Lớp PG dùng DB DEMO mới, không DROP/DELETE; thiếu psycopg/DSN thì skip.
Không Word, engine hay dịch vụ ngoài. Dữ liệu và actor đều DEMO/MO_PHONG.
"""
import http.client
import json
import os
import secrets
import tempfile
import threading
import unittest
import uuid
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock, patch

from kho_tri_thuc.giao_dien import crm_g
from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
from test_crm_42_s1_tinh import MauGia, dong

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None

CAU_HINH = '''[app]
entity_id = "PLHN_FIXTURE"
environment = "fixture"
data_dir = "data"
[money]
currency = "VND"
scale = 0
[operation]
junsky_export_enabled = false
junsky_import_enabled = false
[storage]
engine = "sqlite"
'''


class HttpMixin:
    @classmethod
    def mo_app(cls):
        cls.tam = Path(tempfile.mkdtemp(prefix="ktt_crm_s1_demo_"))  # giữ lại, không xóa
        cfg = cls.tam / "cau_hinh_fixture.toml"
        cfg.write_text(CAU_HINH, encoding="utf-8")
        cls.app = LocalApp(cfg, cls.tam / "web")
        cls.app._crm_phien = {"DEMO_KT_A": "MO_PHONG_KT_A", "DEMO_KT_B": "MO_PHONG_KT_B",
                              "DEMO_BH": "MO_PHONG_BAN_HANG", "DEMO_CFO": "MO_PHONG_CFO",
                              "DEMO_XEM": "MO_PHONG_XEM_A", "DEMO_NO_CRM": "MO_PHONG_KT_KHONG_CRM_A"}
        cls.server = LocalServer(cls.app, 0)
        cls.addClassCleanup(cls.server.server_close)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls.dung)

    @classmethod
    def dung(cls):
        cls.server.shutdown()
        cls.thread.join(10)

    def goi(self, query="", sid="DEMO_KT_A", token=True):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=20)
        headers = {"Cookie": f"{self.app.CRM_COOKIE}={sid}"} if sid else {}
        if token:
            headers["X-KTT-Token"] = self.app.token
        try:
            c.request("GET", "/api/crm/hop-dong" + query, headers=headers)
            r = c.getresponse()
            return r.status, json.loads(r.read()), dict(r.getheaders())
        finally:
            c.close()


class S1HttpMock(HttpMixin, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mo_app()
        cls.app._crm_db = lambda fn, *args: fn(*args)  # biên driver, không thay router/phiên/token

    def setUp(self):
        self.m = MauGia([dong()])
        self.factory = patch.object(crm_g, "dich_vu_s1", side_effect=lambda app: nullcontext(self.m))
        self.factory.start()
        self.addCleanup(self.factory.stop)

    def test_route_dung_phuong_thuc_khong_cuop_route_cu(self):
        self.assertTrue(crm_g.la_route(False, "/api/crm/hop-dong"))
        self.assertFalse(crm_g.la_route(True, "/api/crm/hop-dong"))
        self.assertFalse(crm_g.la_route(False, "/api/crm/hop-dong/DEMO"))
        self.assertFalse(crm_g.la_route(True, "/api/crm/mau"))

    def test_factory_doc_khong_khoi_dong_worker_g5(self):
        app = Mock(root=Path("DEMO"))
        chu, crm = Mock(), Mock()
        app.crm.return_value = crm
        app._m5_ket_noi_chu.return_value = chu
        with patch.object(crm_g, "dich_vu") as ghi, patch.object(crm_g, "_khoi_dong_g5") as worker, \
                patch("kho_tri_thuc.k2.crm_mau.CrmMauK2", return_value=self.m):
            with self.factory.temp_original(app) as svc:
                self.assertIs(svc, self.m)
            ghi.assert_not_called()
            worker.assert_not_called()
            chu.close.assert_called_once_with()
        self.assertNotIn("_crm_g", app.__dict__)

    def test_get_s1_json_lossless_va_khong_cache(self):
        st, r, h = self.goi()
        self.assertEqual(st, 200, r)
        self.assertEqual(r["hop_dong"][0]["gia_tri_minor"], "9007199254740993")
        self.assertEqual(r["hop_dong"][0]["cong_no_junsky"]["hien_thi"], "chưa có sổ")
        self.assertEqual(h["Cache-Control"], "no-store")
        self.m.danh_tinh.assert_called_once_with("MO_PHONG_KT_A")

    def test_actor_lay_tu_cookie_khong_nhan_tu_query(self):
        st, _, _ = self.goi(sid="DEMO_BH")
        self.assertEqual(st, 200)
        self.m.danh_tinh.assert_called_once_with("MO_PHONG_BAN_HANG")
        st, r, _ = self.goi("?actor=MO_PHONG_CFO")
        self.assertEqual((st, r["error"]), (400, "CRM_S1_THAM_SO_SAI"))

    def test_thieu_phien_token_khong_doc_db(self):
        st, r, _ = self.goi(sid=None)
        self.assertEqual((st, r["error"]), (400, "CRM_PHIEN"))
        st, _, _ = self.goi(token=False)
        self.assertEqual(st, 403)
        self.m.c.execute.assert_not_called()

    def test_http_kiem_kieu_lap_rong_dodai_truoc_factory(self):
        for query in ("?trang=0", "?trang=1&trang=", "?trang=", "?kich_thuoc_trang=101", "?trang=1.2",
                      "?vai=CFO", "?ngay_ky_tu=2026-02-30", "?tim=" + "a" * 201,
                      "?" + "&".join("tim=a" for _ in range(31))):
            with self.subTest(query=query[:70]):
                st, r, _ = self.goi(query)
                self.assertEqual((st, r["error"]), (400, "CRM_S1_THAM_SO_SAI"))
        self.m.c.execute.assert_not_called()

    def test_http_loc_trang_rong_khong_lo_tong_ngoai_loc(self):
        st, r, _ = self.goi("?phap_nhan=PN_DEMO_B")
        self.assertEqual((st, r["tong"], r["hop_dong"]), (200, 0, []))
        self.assertTrue(all(t["so_luong"] == 0 for t in r["the_so"].values()))


@unittest.skipUnless(psycopg is not None and os.environ.get("KHO_PG_DSN_TEST"),
                     "Thiếu psycopg hoặc KHO_PG_DSN_TEST — PG S1 NOT_RUN, không tính đạt")
class S1HttpPg(HttpMixin, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.ha_tang.primitives import canonical_json
        from kho_tri_thuc.k2 import crm_demo
        from kho_tri_thuc.k2.crm import CrmK2
        from kho_tri_thuc.k2.crm_mau import CrmMauK2
        from kho_tri_thuc.kiem_chung import fixtures_crm as F
        from psycopg.conninfo import conninfo_to_dict, make_conninfo
        cfg = conninfo_to_dict(os.environ["KHO_PG_DSN_TEST"])
        if cfg.get("host") not in ("localhost", "127.0.0.1", "::1"):
            raise unittest.SkipTest("S1 chỉ chạy PostgreSQL cục bộ DEMO")
        cls.db = "kho_test_crms1_" + uuid.uuid4().hex[:8]
        with psycopg.connect(make_conninfo(**cfg), autocommit=True) as a:
            a.execute(psycopg.sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(psycopg.sql.Identifier(cls.db)))
        cfg["dbname"] = cls.db
        cls.admin = psycopg.connect(make_conninfo(**cfg), autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(cls.admin.close)
        pg.migrate(cls.admin)
        ids = crm_demo.khoi_tao(cls.admin)
        role, pw = "ktt_test_crms1_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(psycopg.sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE IN ROLE app_web")
                          .format(psycopg.sql.Identifier(role), psycopg.sql.Literal(pw)))
        cfg.update(user=role, password=pw)
        cls.conn = psycopg.connect(make_conninfo(**cfg), autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(cls.conn.close)
        cls.mo_app()
        crm = CrmK2(cls.conn, cls.tam / "crm-k2")
        cls.app._crm = crm
        # Dùng đúng giao dịch/quyền tin cậy G; không khởi động worker G5 khi kiểm S1.
        cls.app._crm_g = CrmMauK2(cls.conn, cls.tam / "crm-g", conn_tin_cay=cls.admin)
        crm.nhan_ket_qua_6("MO_PHONG_BAN_HANG", canonical_json(F.kcn_goc()).encode(),
                          F.env("PN_DEMO_A", "DT-KCN-THUE-DAT-DEMO", "GOC", "HD_S1_DEMO",
                                ma_hop_dong_chung="HDC-S1-DEMO", doi_tac_object_id="KH_DEMO.A01", du_an="DA_KCN_DEMO"),
                          van_ban_nguon=F.VB_KCN)
        cls.admin.execute("INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong, trang_thai) "
                          "VALUES (%s, 'BAN_NHA', 'HD-S1-DEMO-B', 'HD-S1-DEMO-B', 'CHO_DUYET')", (ids["PN_DEMO_B"],))

    def test_scope_kt_cfo_va_the_so_theo_phap_nhan(self):
        st, a, _ = self.goi(sid="DEMO_KT_A")
        self.assertEqual(st, 200, a)
        self.assertEqual({r["phap_nhan"] for r in a["hop_dong"]}, {"PN_DEMO_A"})
        self.assertEqual(a["the_so"]["W3"]["so_luong"], 1)
        st, b, _ = self.goi(sid="DEMO_KT_B")
        self.assertEqual(st, 200, b)
        self.assertEqual({r["phap_nhan"] for r in b["hop_dong"]}, {"PN_DEMO_B"})
        self.assertEqual(b["the_so"]["W3"]["so_luong"], 0)
        st, cfo, _ = self.goi(sid="DEMO_CFO")
        self.assertEqual((st, cfo["tong"]), (200, 2), cfo)

    def test_ban_hang_khong_suy_scope_tu_nguoi_nop(self):
        st, r, _ = self.goi(sid="DEMO_BH")
        self.assertEqual((st, r["tong"]), (200, 0), r)
        self.assertTrue(all(t["so_luong"] == 0 for t in r["the_so"].values()))

    def test_khong_module_rong_junsky_chua_co_so(self):
        st, r, _ = self.goi(sid="DEMO_NO_CRM")
        self.assertEqual((st, r["tong"]), (200, 0), r)
        st, r, _ = self.goi(sid="DEMO_KT_A")
        self.assertEqual(st, 200, r)
        self.assertEqual(r["hop_dong"][0]["cong_no_junsky"]["hien_thi"], "chưa có sổ")
        self.assertEqual(r["hop_dong"][0]["thu_crm"]["trang_thai"], "CHUA_CO_LICH")


if __name__ == "__main__":
    unittest.main()
