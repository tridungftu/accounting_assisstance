"""MTQ-5b: bộ chọn chung và phiên CRM; gọi Handler trực tiếp, không mở server.

PG tùy chọn tạo kho_test_* mới; giữ CSDL để lead dọn ngoài sandbox.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import uuid

from kho_tri_thuc.giao_dien import server, ma_tran_tham_quyen as mtq_http
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import crm_demo, crm_g_demo, m4_demo, mtq_demo, m5_demo


class DanhTinhSqlite:
    """Chạy SELECT bộ chọn thật trên dữ liệu giả; chỉ đổi cú pháp bind ANY của PG."""
    def __init__(self):
        self.c = sqlite3.connect(":memory:")
        self.c.row_factory = sqlite3.Row
        self.c.create_function("starts_with", 2, lambda value, prefix: value.startswith(prefix))
        self.c.execute("ATTACH DATABASE ':memory:' AS master")
        self.c.execute("""CREATE TABLE master.nguoi_dung
            (dang_nhap TEXT, vai_tro TEXT, mo_phong BOOLEAN, trang_thai TEXT)""")
        rows = [(n[0], n[3], True, "HOAT_DONG") for n in mtq_demo.NGUOI_DUNG]
        rows += [(mtq_demo.ADMIN, "XEM", True, "HOAT_DONG")]
        rows += [(n[0], n[1], True, "HOAT_DONG") for n in crm_demo.NGUOI_DUNG]
        rows += [(n, "XEM", True, "HOAT_DONG") for n in m5_demo.dang_nhap_m5()]
        # Tên gần giống tiền tố: không dùng LIKE với '_' thành wildcard.
        rows += [("MOXPHONGXMTQ_CU", "XEM", True, "HOAT_DONG"),
                 ("NGUOI_THAT", "XEM", False, "HOAT_DONG"),
                 ("MO_PHONG_NGUNG", "XEM", True, "NGUNG")]
        self.c.executemany("INSERT INTO master.nguoi_dung VALUES (?,?,?,?)", rows)

    def execute(self, sql, params=()):
        if "ANY(%s)" in sql:
            params = tuple(params[0])
            sql = sql.replace("= ANY(%s)", "IN (" + ",".join("?" for _ in params) + ")")
        return self.c.execute(sql.replace("%s", "?"), params)


def app_gia(conn):
    app = object.__new__(server.LocalApp)
    app.is_that, app.token = False, "token-demo"
    app.root = Path(__file__).resolve().parents[1]
    app.mutation_lock = threading.Lock()
    app._crm = MagicMock(conn=conn)
    app._crm.danh_sach.return_value = {"nguoi": {"dang_nhap": app.CRM_MAC_DINH}}
    app._crm_ket_noi = lambda: (None, None)
    app._crm_db = lambda fn, *args: fn(*args)
    return app


def goi(app, path, *, post=False, body=None, sid=None, token=True):
    h = object.__new__(server.Handler)
    h.server = SimpleNamespace(app=app, server_port=18783)
    h.path = path
    h.headers = {"Host": "127.0.0.1:18783", "X-KTT-Token": app.token if token else "sai"}
    if sid:
        h.headers["Cookie"] = f"{app.CRM_COOKIE}={sid}"
    h.json_body = lambda: body
    h.send_content = lambda status, data, mime=None, headers=None: setattr(h, "result", (status, data, headers or {}))
    h.handle_route(post)
    return h.result


class MtqDemoPhienTinh(unittest.TestCase):
    def setUp(self):
        self.conn = DanhTinhSqlite()
        self.addCleanup(self.conn.c.close)
        self.app = app_gia(self.conn)

    def test_nhom_mtq_dung_nam_vai_admin_tach(self):
        before = list(self.conn.c.execute("SELECT * FROM master.nguoi_dung"))
        data = self.app.demo_vai(self.app.CRM_MAC_DINH)
        self.assertEqual([g["ma"] for g in data["danh_tinh_demo_nhom"]], ["MTQ", "QUAN_TRI"])
        self.assertNotIn("CU", {g["ma"] for g in data["danh_tinh_demo_nhom"]})
        mtq, admin = data["danh_tinh_demo_nhom"]
        self.assertEqual(mtq["ten"], "Ma trận thẩm quyền (DEMO)")
        self.assertEqual([v["ten"] for v in mtq["vai"]],
                         ["Người thực hiện 1", "Người thực hiện 2", "Trưởng phòng", "CFO", "Người xem"])
        self.assertEqual([v["cap"] for v in mtq["vai"]], [n[2] for n in mtq_demo.NGUOI_DUNG])
        self.assertTrue(all(set(v) == {"dang_nhap", "ten", "cap"} for v in mtq["vai"]))
        self.assertEqual(admin, {"ma": "QUAN_TRI", "ten": "Quản trị DEMO",
                               "vai": [{"dang_nhap": mtq_demo.ADMIN, "ten": "Admin DEMO"}]})
        self.assertEqual(before, list(self.conn.c.execute("SELECT * FROM master.nguoi_dung")))

    def test_khong_hien_actor_ngung_hoac_khong_mo_phong(self):
        self.conn.c.execute("UPDATE master.nguoi_dung SET trang_thai='NGUNG' WHERE dang_nhap=?", (mtq_demo.ADMIN,))
        self.conn.c.execute("UPDATE master.nguoi_dung SET mo_phong=false WHERE dang_nhap=?", (mtq_demo.NGUOI_DUNG[0][0],))
        mtq, admin = self.app.demo_vai("cu")["danh_tinh_demo_nhom"]
        self.assertEqual(len(mtq["vai"]), 4)
        self.assertEqual(admin["vai"], [])

    def test_crm_m9_m5_khong_co_mtq(self):
        self.app._m9 = MagicMock(conn=self.conn)
        self.app._m9.danh_sach.return_value = {}
        m5 = MagicMock(conn=self.conn)
        m5.danh_sach.return_value = {}
        self.app.m5 = lambda: m5
        for data in (self.app.crm_state("cu"), self.app.m9_state("cu"), self.app.m5_state("cu", {})):
            with self.subTest(data=data["danh_tinh_demo"]):
                logins = {v["dang_nhap"] for v in data["danh_tinh_demo"]}
                self.assertTrue(logins)
                self.assertFalse(any(n.startswith("MO_PHONG_MTQ_") for n in logins))
                self.assertNotIn("NGUOI_THAT", logins)
                self.assertNotIn("MO_PHONG_NGUNG", logins)
        self.assertIn("MOXPHONGXMTQ_CU", {v["dang_nhap"] for v in self.app.crm_state("cu")["danh_tinh_demo"]})

    def test_get_cap_cookie_http_only_va_giu_phien(self):
        status, data, headers = goi(self.app, "/api/demo/vai")
        self.assertEqual(status, 200)
        self.assertIn("HttpOnly; SameSite=Strict", headers["Set-Cookie"])
        sid = headers["Set-Cookie"].split(";", 1)[0].split("=", 1)[1]
        self.assertEqual(self.app.crm_phien(sid)[1], data["dang_nhap"])
        self.assertEqual(goi(self.app, "/api/demo/vai", sid=sid)[2], {})

    def test_crm_chua_cau_hinh_tra_200_nhom_rong(self):
        self.app._crm = None
        status, data, _ = goi(self.app, "/api/demo/vai")
        self.assertEqual((status, data), (200, {"cau_hinh": False, "nhom": []}))

    def test_loi_crm_khac_khong_bi_coi_la_chua_cau_hinh(self):
        with patch.object(self.app, "crm", side_effect=DataError("CRM_LOI", "Lỗi fixture")):
            status, data, _ = goi(self.app, "/api/demo/vai")
        self.assertEqual((status, data["error"]), (400, "CRM_LOI"))

    def test_doi_du_sau_actor_dung_phien_khong_anh_huong_phien_khac(self):
        sid, _, _ = self.app.crm_phien(None, tao=True)
        sid_khac, cu, _ = self.app.crm_phien(None, tao=True)
        for login in [n[0] for n in mtq_demo.NGUOI_DUNG] + [mtq_demo.ADMIN]:
            status, data, _ = goi(self.app, "/api/crm/danh-tinh", post=True, body={"dang_nhap": login}, sid=sid)
            self.assertEqual((status, data), (200, {"dang_nhap": login}))
            self.app._crm.danh_tinh.assert_called_with(login)
            self.assertEqual(self.app.crm_phien(sid)[1], login)
            self.assertEqual(self.app.crm_phien(sid_khac)[1], cu)

    def test_danh_tinh_bi_tu_choi_khong_doi_phien(self):
        sid, cu, _ = self.app.crm_phien(None, tao=True)
        self.app._crm.danh_tinh.side_effect = DataError("DANH_TINH", "Không hoạt động")
        self.assertEqual(goi(self.app, "/api/crm/danh-tinh", post=True,
                            body={"dang_nhap": mtq_demo.ADMIN}, sid=sid)[0], 400)
        self.assertEqual(self.app.crm_phien(sid)[1], cu)

    def test_khong_tin_actor_client_khong_cap_phien_theo_cookie_tu_che(self):
        sid, cu, _ = self.app.crm_phien(None, tao=True)
        status, data, _ = goi(self.app, "/api/crm/danh-tinh", post=True,
                            body={"dang_nhap": mtq_demo.ADMIN, "actor": mtq_demo.ADMIN}, sid=sid)
        self.assertEqual((status, data["error"]), (400, "CRM_CLIENT_IDENTITY"))
        self.assertEqual(self.app.crm_phien(sid)[1], cu)
        self.assertEqual(goi(self.app, "/api/crm/danh-tinh", post=True,
                            body={"dang_nhap": mtq_demo.ADMIN}, sid="tu-che")[1]["error"], "CRM_PHIEN")

    def test_token_va_query(self):
        self.assertEqual(goi(self.app, "/api/demo/vai", token=False)[0], 403)
        for query in ("actor=x", "actor=", "actor"):
            self.assertEqual(goi(self.app, "/api/demo/vai?" + query)[0], 400)
        self.assertNotIn("_crm_phien", self.app.__dict__)

    def test_kho_that_khong_co_bo_chon_khong_cap_cookie(self):
        self.app.is_that = True
        with self.assertRaises(DataError) as exc:
            self.app.demo_vai("cu")
        self.assertEqual(exc.exception.code, "THAT_UI")
        status, data, headers = goi(self.app, "/api/demo/vai")
        self.assertEqual((status, data["error"]), (400, "THAT_UI"))
        self.assertNotIn("Set-Cookie", headers)
        self.assertNotIn("_crm_phien", self.app.__dict__)

    def test_utf8_khong_bom(self):
        for path in (Path(server.__file__), Path(__file__)):
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn("\ufffd", raw.decode("utf-8"))


try:
    import psycopg
except ImportError:
    psycopg = None

DSN = os.environ.get("KHO_PG_DSN_TEST")


@unittest.skipUnless(DSN and psycopg is not None, "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG ngoài sandbox")
class MtqDemoPhienPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        cls.db = "kho_test_mtq_phien_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as c:
            c.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.conninfo = make_conninfo(DSN, dbname=cls.db)
        cls.c = psycopg.connect(cls.conninfo, autocommit=True)
        cls.addClassCleanup(cls.c.close)
        crm_demo.khoi_tao(cls.c)
        m4_demo.khoi_tao(cls.c)
        crm_g_demo.khoi_tao(cls.c)
        if mtq_demo.khoi_tao(cls.c, demo=True)["trang_thai"] != "DU":
            raise AssertionError("Seed MTQ DEMO chưa đủ")

    def test_get_demo_vai_sql_pg_that(self):
        from psycopg.rows import dict_row
        from kho_tri_thuc.k2.crm import CrmK2
        with psycopg.connect(self.conninfo, autocommit=True, row_factory=dict_row) as c:
            app = app_gia(c)
            app._crm = CrmK2(c, app.root)
            # GET qua Handler thật; không thay execute hay cú pháp ANY của PostgreSQL.
            status, data, _ = goi(app, "/api/demo/vai")
            self.assertEqual(status, 200)
            self.assertEqual([g["ma"] for g in data["danh_tinh_demo_nhom"]], ["MTQ", "QUAN_TRI"])
            self.assertNotIn("CU", {g["ma"] for g in data["danh_tinh_demo_nhom"]})
            mtq, admin = data["danh_tinh_demo_nhom"]
            self.assertEqual(mtq, {"ma": "MTQ", "ten": "Ma trận thẩm quyền (DEMO)", "vai": [
                {"dang_nhap": login, "ten": ten.removesuffix(" DEMO"), "cap": cap}
                for login, ten, cap, _ in mtq_demo.NGUOI_DUNG]})
            self.assertEqual(len(mtq["vai"]), 5)
            self.assertEqual(admin, {"ma": "QUAN_TRI", "ten": "Quản trị DEMO",
                                    "vai": [{"dang_nhap": mtq_demo.ADMIN, "ten": "Admin DEMO"}]})
            # starts_with chỉ còn ở bộ chọn phân hệ sau khi bỏ nhóm CU.
            cu = app._demo_vai_cu(c)
            self.assertTrue({n[0] for n in crm_demo.NGUOI_DUNG} <= {v["dang_nhap"] for v in cu})
            self.assertFalse(any(v["dang_nhap"].startswith("MO_PHONG_MTQ_") for v in cu))

    def test_doi_admin_cua_toi_la_admin_theo_phien(self):
        from psycopg.rows import dict_row
        from kho_tri_thuc.k2.crm import CrmK2
        from kho_tri_thuc.k2.crm_mau import CrmMauK2
        from kho_tri_thuc.k2.ma_tran_tham_quyen import MaTranThamQuyenK2
        with psycopg.connect(self.conninfo, autocommit=True, row_factory=dict_row) as c:
            app = app_gia(c)
            app._crm = CrmK2(c, app.root)
            sid, _, _ = app.crm_phien(None, tao=True)
            status, _, _ = goi(app, "/api/crm/danh-tinh", post=True, body={"dang_nhap": mtq_demo.ADMIN}, sid=sid)
            self.assertEqual(status, 200)

            @contextmanager
            def service(_app):
                # Chỉ tiêm kết nối fixture; Handler, cookie, danh tính và SQL MTQ chạy thật.
                yield MaTranThamQuyenK2(CrmMauK2(c, app.root, conn_tin_cay=c))

            with patch.object(mtq_http, "dich_vu", service):
                status, data, _ = goi(app, "/api/tham-quyen/cua-toi", sid=sid)
                self.assertEqual(status, 200)
                self.assertIs(data["la_admin"], True)
                self.assertIs(data["admin"], False)
                goi(app, "/api/crm/danh-tinh", post=True, body={"dang_nhap": mtq_demo.NGUOI_DUNG[0][0]}, sid=sid)
                status, data, _ = goi(app, "/api/tham-quyen/cua-toi", sid=sid)
                self.assertEqual(status, 200)
                self.assertIs(data["la_admin"], False)


if __name__ == "__main__":
    unittest.main()
