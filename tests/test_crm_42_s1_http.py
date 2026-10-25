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
from kho_tri_thuc.ha_tang.primitives import DataError
from test_crm_42_s1_tinh import MauGia, dong, lich

DICH_VU_S1_GOC = crm_g.dich_vu_s1

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
                              "DEMO_XEM": "MO_PHONG_XEM_A", "DEMO_NO_CRM": "MO_PHONG_KT_KHONG_CRM_A",
                              "DEMO_BH2": "MO_PHONG_CRM_G_BH_A", "DEMO_KT_NO_M1": "MO_PHONG_CRM_G_KT_A"}
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
        app.mutation_lock = threading.RLock()
        chu, crm = Mock(), Mock()
        app.crm.return_value = crm
        app._m5_ket_noi_chu.return_value = chu
        with patch.object(crm_g, "dich_vu") as ghi, patch.object(crm_g, "_khoi_dong_g5") as worker, \
                patch("kho_tri_thuc.k2.crm_mau.CrmMauK2", return_value=self.m):
            with DICH_VU_S1_GOC(app) as svc:
                self.assertIs(svc, self.m)
            ghi.assert_not_called()
            worker.assert_not_called()
            chu.close.assert_called_once_with()
        self.assertNotIn("_crm_g", app.__dict__)

    def test_factory_loi_cau_hinh_dataerror_thanh_503_json(self):
        self.factory.stop()
        with patch.object(self.app, "crm", return_value=Mock()), \
                patch.object(self.app, "_m5_ket_noi_chu", side_effect=DataError("M5_CHU_SAI", "DEMO bí mật")):
            st, r, _ = self.goi()
        self.assertEqual((st, r["error"]), (503, "CRM_G_CHUA_SAN_SANG"))
        self.assertNotIn("DEMO bí mật", json.dumps(r, ensure_ascii=False))

    def test_factory_thieu_ket_noi_khong_dung_singleton_chung(self):
        self.factory.stop()
        with patch.object(self.app, "crm", return_value=Mock()), \
                patch.object(self.app, "_m5_ket_noi_chu", return_value=None), \
                patch.object(self.app, "_crm_g", Mock(), create=True):
            st, r, _ = self.goi()
        self.assertEqual((st, r["error"]), (503, "CRM_G_CHUA_SAN_SANG"))

    def test_doc_nang_khong_giu_mutation_lock(self):
        execute = self.m.c.execute.side_effect
        def doc(sql, params=()):
            if sql != "SET TRANSACTION READ ONLY":
                ket_qua = []
                def thu_khoa():
                    duoc = self.app.mutation_lock.acquire(timeout=0.2)
                    ket_qua.append(duoc)
                    if duoc:
                        self.app.mutation_lock.release()
                t = threading.Thread(target=thu_khoa)
                t.start()
                t.join(1)
                self.assertEqual(ket_qua, [True])
            return execute(sql, params)
        self.m.c.execute.side_effect = doc
        self.assertEqual(self.goi()[0], 200)

    def test_xem_khong_tien_va_thieu_module_co_co_quyen(self):
        self.m.rows = [dong(xem_tien=False, lich=[lich()])]
        self.m.danh_tinh.return_value.update(vai_tro="XEM", quyen={"DEMO-PN-A": {"module": ["CRM"]}})
        st, r, _ = self.goi(sid="DEMO_XEM")
        self.assertEqual(st, 200, r)
        self.assertTrue(r["hop_dong"][0]["khong_quyen_xem_tien"])
        self.assertIsNone(r["hop_dong"][0]["thu_crm"])
        self.assertIsNone(r["the_so"]["W5"]["so_luong"])
        self.m.rows = []
        self.m.danh_tinh.return_value["quyen"] = {}
        st, r, _ = self.goi(sid="DEMO_NO_CRM")
        self.assertEqual((st, r["tong"], r["khong_quyen"]), (200, 0, True))

    def test_xem_che_co_tien_va_loc_khong_lo_hop_dong(self):
        raw = dong(gia_tri_minor=None, lich=[lich(han="2026-10-24"), lich(tien=None, dot=2)],
                   thieu_gia_tri=True)
        self.m.rows = [raw]
        for co in ("QUA_HAN", "THIEU_CAN_CU"):
            st, r, _ = self.goi("?co=" + co)
            self.assertEqual((st, r["tong"]), (200, 1), r)
            self.assertIn(co, r["hop_dong"][0]["co"])
        self.m.rows = [{**raw, "xem_tien": False}]
        self.m.danh_tinh.return_value.update(vai_tro="XEM", quyen={"DEMO-PN-A": {"module": ["CRM"]}})
        st, r, _ = self.goi(sid="DEMO_XEM")
        self.assertEqual((st, r["tong"]), (200, 1), r)
        self.assertEqual(r["hop_dong"][0]["co"], [])
        self.assertEqual(r["the_so"]["W2"]["so_luong"], 1)
        for co in ("QUA_HAN", "THIEU_CAN_CU"):
            st, r, _ = self.goi("?co=" + co, sid="DEMO_XEM")
            self.assertEqual((st, r["tong"], r["hop_dong"]), (200, 0, []), r)
            self.assertTrue(r["khong_quyen_xem_tien"])
            self.assertIsNone(r["the_so"]["W5"]["so_luong"])
            self.assertTrue(all(r["the_so"][w]["so_luong"] == 0 for w in ("W1", "W2", "W3", "W4")))

    def test_ban_hang_co_tien_va_the_duong_qua_http(self):
        self.m.rows = [dong(lich=[lich()])]
        self.m.danh_tinh.return_value.update(vai_tro="BAN_HANG", quyen={"DEMO-PN-A": {"module": ["CRM"]}})
        st, r, _ = self.goi(sid="DEMO_BH")
        self.assertEqual((st, r["tong"]), (200, 1), r)
        self.assertEqual(r["hop_dong"][0]["gia_tri_minor"], "9007199254740993")
        self.assertEqual((r["the_so"]["W2"]["so_luong"], r["the_so"]["W5"]["so_luong"]), (1, 1))
        self.assertFalse(r["khong_quyen_xem_tien"])

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
        from kho_tri_thuc.k2 import crm_demo, crm_g_demo
        from kho_tri_thuc.k2.crm import CrmK2
        from kho_tri_thuc.k2.crm_mau import CrmMauK2
        from kho_tri_thuc.kiem_chung import fixtures_crm as F
        from test_crm_42_s1_tinh import NGAY
        from psycopg.conninfo import conninfo_to_dict, make_conninfo
        cfg = conninfo_to_dict(os.environ["KHO_PG_DSN_TEST"])
        if cfg.get("host") not in ("localhost", "127.0.0.1", "::1"):
            raise unittest.SkipTest("S1 chỉ chạy PostgreSQL cục bộ DEMO")
        cls.db = "kho_test_crms1_" + uuid.uuid4().hex[:8]
        with psycopg.connect(make_conninfo(**cfg), autocommit=True) as a:
            a.execute(psycopg.sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(psycopg.sql.Identifier(cls.db)))
        cfg["dbname"] = cls.db
        cls.admin_dsn = make_conninfo(**cfg)
        cls.admin = psycopg.connect(cls.admin_dsn, autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        pg.migrate(cls.admin)
        ids = crm_demo.khoi_tao(cls.admin)
        crm_g_demo.khoi_tao(cls.admin)
        cls.ids = ids
        role, pw = "ktt_test_crms1_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(psycopg.sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE IN ROLE app_web")
                          .format(psycopg.sql.Identifier(role), psycopg.sql.Literal(pw)))
        cfg.update(user=role, password=pw)
        cls.conn = psycopg.connect(make_conninfo(**cfg), autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(cls.conn.close)
        cls.admin.row_factory = dict_row  # seed hiện hành dùng tuple; service G dùng dict.
        cls.mo_app()
        crm = CrmK2(cls.conn, cls.tam / "crm-k2")
        cls.app._crm = crm
        cls.app._m5_ket_noi_chu = lambda app_conn: psycopg.connect(cls.admin_dsn, autocommit=True, row_factory=dict_row)
        # Dùng đúng giao dịch/quyền tin cậy G; không khởi động worker G5 khi kiểm S1.
        cls.app._crm_g = CrmMauK2(cls.conn, cls.tam / "crm-g", conn_tin_cay=cls.admin, hom_nay=lambda: NGAY)
        crm.hom_nay = lambda: NGAY
        crm.nhan_ket_qua_6("MO_PHONG_BAN_HANG", canonical_json(F.kcn_goc()).encode(),
                          F.env("PN_DEMO_A", "DT-KCN-THUE-DAT-DEMO", "GOC", "HD_S1_DEMO",
                                ma_hop_dong_chung="HDC-S1-DEMO", doi_tac_object_id="KH_DEMO.A01", du_an="DA_KCN_DEMO"),
                          van_ban_nguon=F.VB_KCN)
        cls.admin.execute("INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong, trang_thai) "
                          "VALUES (%s, 'BAN_NHA', 'HD-S1-DEMO-B', 'HD-S1-DEMO-B', 'CHO_DUYET')", (ids["PN_DEMO_B"],))
        cls.tao_soan_va_binding()
        cls.tao_so_junsky()

    @classmethod
    def q(cls, sql, params=()):
        return next(iter(cls.admin.execute(sql, params).fetchone().values()))

    @classmethod
    def cap_phan_cong(cls, login, soan):
        """Cùng mẫu test_crm_ky_ket_http: chủ DB cấp phân công, không tự cấp qua HTTP."""
        return cls.q("""INSERT INTO master.phan_cong_hanh_dong
            (nguoi_dung_id, phap_nhan_id, module, hanh_dong, loai_hinh_id, cap_boi)
            SELECT n.id, s.phap_nhan_id, 'CRM', 'CRM_KY_KET', s.loai_hinh_id, 'TEST:DEMO-S1'
            FROM master.nguoi_dung n, master.crm_hd_soan s
            WHERE n.dang_nhap = %s AND s.id = %s RETURNING id""", (login, soan))

    @classmethod
    def cap_pham_vi(cls, pc, soan, khach_sha=None):
        return cls.q("""INSERT INTO master.crm_ky_pham_vi
            (phan_cong_id, phap_nhan_id, hop_dong_id, soan_id, du_an_id, khach_du_thao_sha256, cap_boi)
            SELECT %s, s.phap_nhan_id, s.hop_dong_id, s.id, h.du_an_id,
                   coalesce(%s::text, encode(sha256(convert_to((r.du_lieu->'bao_gia'->'khach'->'du_thao')::text, 'UTF8')), 'hex')),
                   'TEST:DEMO-S1'
            FROM master.crm_hd_soan s JOIN master.hop_dong h ON h.id = s.hop_dong_id
            JOIN master.crm_hd_soan_rev r ON r.soan_id = s.id AND r.revision = s.revision_hien_hanh
            WHERE s.id = %s RETURNING id""", (pc, khach_sha, soan))

    @classmethod
    def tao_soan_va_binding(cls):
        """Mẫu duyệt và bản soạn qua service thật; không xuất PDF/không Word COM."""
        from kho_tri_thuc.k2.crm_giao_ket import CrmGiaoKetK2
        from test_crm_giao_ket import BAN_DO_TEN, mau_docx
        from test_crm_42_s1_tinh import NGAY
        m = cls.app._crm_g
        tai, kt, cfo = "MO_PHONG_CRM_G_TAI_A", "MO_PHONG_CRM_G_KT_A", "MO_PHONG_CRM_G_CFO_A"
        loai = str(cls.q("SELECT id FROM master.loai_hinh_doanh_thu WHERE phap_nhan_id = %s AND valid_to IS NULL", (cls.ids["PN_DEMO_A"],)))
        da = str(cls.q("SELECT id FROM master.du_an WHERE phap_nhan_id = %s AND ma_junsky = 'DA_KCN_DEMO'", (cls.ids["PN_DEMO_A"],)))
        da_khac = str(cls.q("INSERT INTO master.du_an (phap_nhan_id, ma_junsky, ten) VALUES (%s, 'DA_DEMO_S1_KHAC', 'Dự án DEMO khác') RETURNING id", (cls.ids["PN_DEMO_A"],)))
        pb = m.tai_mau(tai, mau_docx(), loai_hinh_id=loai, ma_mau="HD_DEMO_S1", ten_tep="DEMO.docx", khoa="DEMO:s1:tai")["phien_ban_id"]
        m.luu_anh_xa(kt, version_id=pb, map=BAN_DO_TEN, expected_graph=m.chi_tiet(kt, pb)["token"], khoa="DEMO:s1:map")
        m.gui_kiem(kt, version_id=pb, expected_graph=m.chi_tiet(kt, pb)["token"], khoa="DEMO:s1:gui")
        m.kiem_mau(kt, version_id=pb, expected_graph=m.chi_tiet(kt, pb)["token"], khoa="DEMO:s1:kiem")
        m.duyet_mau(cfo, version_id=pb, valid_from=NGAY.isoformat(), expected_graph=m.chi_tiet(cfo, pb)["token"], khoa="DEMO:s1:duyet")
        g = CrmGiaoKetK2(m)
        cls.soan = []
        for tag, project, ten in (("MINE", da, "KHÁCH DEMO S1"), ("PROJECT", da_khac, "KHÁCH DEMO S1"),
                                  ("CUSTOMER", da, "KHÁCH DEMO KHÁC")):
            data = {"loai_hinh_id": loai, "du_an_id": project, "nguon_lich": "KHACH", "don_vi": {"ma": "DEMO-" + tag},
                    "khach": {"du_thao": {"ten": ten, "lien_he": "CCCD_DEMO_BI_MAT STK_DEMO_BI_MAT"}},
                    "gia": {"tien_te": "VND", "tong": "1000000000", "co_so_thue": "NET"},
                    "phi_bao_tri": {"gia_tri": "20000000", "tien_te": "VND", "co_so": "DEMO"},
                    "lich": [{"lan": "1", "loai": "PERCENT", "ty_le": "100"}]}
            bg = g.luu("MO_PHONG_BAN_HANG", bao_gia_id=None, expected_revision=None, du_lieu=data, khoa="DEMO:s1:bg:" + tag)
            soan = g.chuyen("MO_PHONG_BAN_HANG", bao_gia_id=bg["bao_gia_id"], expected_revision=1,
                            mau_phien_ban_id=pb, khoa="DEMO:s1:chuyen:" + tag)
            cls.soan.append(soan)
        pc = cls.cap_phan_cong("MO_PHONG_BAN_HANG", cls.soan[0]["soan_id"])
        cls.cap_pham_vi(pc, cls.soan[0]["soan_id"])
        # Fixture chủ DB cho projection: có tiền thật và thẻ chờ ký dương, không cần engine xuất.
        cls.admin.execute("UPDATE master.crm_hd_soan SET trang_thai = 'CHO_KY' WHERE id = %s",
                          (cls.soan[0]["soan_id"],))
        cls.admin.execute("UPDATE master.hop_dong SET gia_tri_minor = 1000000000, "
                          "crm_giao_ket = 'CHO_KY', trang_thai = 'CHO_KY' WHERE id = %s",
                          (cls.soan[0]["hop_dong_id"],))
        # Binding hợp lệ lúc cấp; HĐ đổi dự án làm binding cũ lệch, phải ẩn.
        cls.cap_pham_vi(pc, cls.soan[1]["soan_id"])
        cls.admin.execute("UPDATE master.hop_dong SET du_an_id = %s WHERE id = %s",
                          (da, cls.soan[1]["hop_dong_id"]))
        # Khách sai digest: có phân công + dòng binding nhưng vẫn phải fail closed.
        cls.cap_pham_vi(pc, cls.soan[2]["soan_id"], "0" * 64)

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
        self.assertEqual((st, cfo["tong"]), (200, 7), cfo)

    def test_ban_hang_binding_duong_va_nguoi_cung_pn_khong_binding(self):
        st, r, _ = self.goi(sid="DEMO_BH")
        self.assertEqual((st, r["tong"]), (200, 1), r)
        self.assertEqual(r["hop_dong"][0]["id"], self.soan[0]["hop_dong_id"])
        self.assertFalse(r["hop_dong"][0]["khong_quyen_xem_tien"])
        self.assertEqual(r["hop_dong"][0]["gia_tri_minor"], "1000000000")
        self.assertIsNotNone(r["hop_dong"][0]["thu_crm"])
        self.assertIsNone(r["hop_dong"][0]["nhan_tien"])
        self.assertEqual(r["the_so"]["W2"]["so_luong"], 1)
        for query in ("?du_an=DA_DEMO_S1_KHAC", "?tim=KH%C3%81CH%20DEMO%20KH%C3%81C"):
            self.assertEqual(self.goi(query, sid="DEMO_BH")[1]["tong"], 0)
        st, r, _ = self.goi(sid="DEMO_BH2")
        self.assertEqual((st, r["tong"]), (200, 0), r)
        self.assertTrue(all(t["so_luong"] == 0 for t in r["the_so"].values()))

    def test_ban_hang_binding_lech_du_an_an_hop_dong(self):
        hd = self.soan[1]["hop_dong_id"]
        self.assertTrue(self.q("""SELECT b.du_an_id IS DISTINCT FROM h.du_an_id
            FROM master.crm_ky_pham_vi b JOIN master.hop_dong h ON h.id = b.hop_dong_id
            WHERE h.id = %s AND b.thu_hoi_luc IS NULL""", (hd,)))
        # KT vẫn thấy HĐ; BH có dòng binding nhưng lệch dự án nên không thấy.
        for sid in ("DEMO_KT_A", "DEMO_BH"):
            st, r, _ = self.goi(sid=sid)
            self.assertEqual(st, 200, r)
            self.assertEqual(str(hd) in {h["id"] for h in r["hop_dong"]}, sid == "DEMO_KT_A")

    def test_xem_khong_co_va_khong_loc_duoc_co_tien(self):
        st, kt, _ = self.goi("?co=THIEU_CAN_CU", sid="DEMO_KT_A")
        self.assertEqual(st, 200, kt)
        self.assertGreater(kt["tong"], 0)  # Đối chứng có cờ tiền trong dữ liệu cùng PN.
        for sid in ("DEMO_XEM", "DEMO_KT_NO_M1"):
            st, r, _ = self.goi(sid=sid)
            self.assertEqual(st, 200, r)
            self.assertGreater(r["tong"], 0)
            self.assertTrue(r["khong_quyen_xem_tien"])
            for h in r["hop_dong"]:
                self.assertTrue({"QUA_HAN", "THIEU_CAN_CU"}.isdisjoint(h["co"]))
            self.assertEqual(r["the_so"]["W2"]["so_luong"], 1)
            for co in ("QUA_HAN", "THIEU_CAN_CU"):
                st, r, _ = self.goi("?co=" + co, sid=sid)
                self.assertEqual((st, r["tong"], r["hop_dong"]), (200, 0, []), r)
                self.assertTrue(r["khong_quyen_xem_tien"])
                self.assertIsNone(r["the_so"]["W5"]["so_luong"])

    def test_khong_module_rong_junsky_chua_co_so(self):
        st, r, _ = self.goi(sid="DEMO_NO_CRM")
        self.assertEqual((st, r["tong"]), (200, 0), r)
        self.assertIs(r["khong_quyen"], True)
        st, r, _ = self.goi("?tim=HDC-S1-DEMO", sid="DEMO_KT_A")
        self.assertEqual(st, 200, r)
        self.assertEqual(r["hop_dong"][0]["cong_no_junsky"]["hien_thi"], "chưa có sổ")
        self.assertEqual(r["hop_dong"][0]["thu_crm"]["trang_thai"], "CHUA_CO_LICH")

    def test_xem_va_kt_thieu_m1_null_tien_pii_tren_json_that(self):
        for sid in ("DEMO_BH", "DEMO_XEM", "DEMO_KT_A", "DEMO_KT_NO_M1", "DEMO_CFO"):
            st, r, _ = self.goi(sid=sid)
            self.assertEqual(st, 200, r)
            self.assertGreater(r["tong"], 0)
            raw = json.dumps(r, ensure_ascii=False).casefold()
            for bi_mat in ("cccd", "stk", '"du_lieu"', "lien_he"):
                self.assertNotIn(bi_mat, raw)
            if sid in ("DEMO_XEM", "DEMO_KT_NO_M1"):
                for h in r["hop_dong"]:
                    for k in ("gia_tri_minor", "thu_crm", "cong_no_junsky"):
                        self.assertIsNone(h[k])
                    self.assertTrue(h["khong_quyen_xem_tien"])
                self.assertIsNone(r["the_so"]["W5"]["so_luong"])

    def test_so_junsky_moi_nhat_null_va_hai_hd_cung_khach(self):
        st, r, _ = self.goi("?tim=DEMO-SO-", sid="DEMO_KT_A")
        self.assertEqual((st, r["tong"]), (200, 2), r)
        so = [h["cong_no_junsky"]["so_du"] for h in r["hop_dong"]]
        self.assertEqual(so[0], so[1])
        self.assertEqual(so[0], [{"ngay_so": "2026-10-25", "tai_khoan": "1311", "tien_te": "VND", "so_du_minor": "100"},
                                 {"ngay_so": "2026-10-25", "tai_khoan": "1312", "tien_te": "USD", "so_du_minor": None}])
        st, r, _ = self.goi("?tim=DEMO-SO-", sid="DEMO_XEM")
        self.assertEqual((st, r["tong"]), (200, 2), r)
        self.assertTrue(all(h["cong_no_junsky"] is None for h in r["hop_dong"]))

    @classmethod
    def tao_so_junsky(cls):
        """Sổ DEMO cấp khách; cùng fixture cho mọi test, không phụ thuộc thứ tự chạy."""
        with cls.admin.transaction():
            doi_tac = cls.q("SELECT doi_tac_id FROM master.doi_tac_ma_junsky WHERE phap_nhan_id = %s AND object_id_junsky = 'KH_DEMO.CHUNG_A'", (cls.ids["PN_DEMO_A"],))
            for i in (1, 2):
                cls.admin.execute("""INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong, doi_tac_id)
                    VALUES (%s, 'THUE_DAT', %s, %s, %s)""", (cls.ids["PN_DEMO_A"], f"DEMO-SO-{i}", f"DEMO-SO-{i}", doi_tac))
            for ngay, tk, tt, con in (("2026-10-01", "1311", "VND", 999), ("2026-10-25", "1311", "VND", 40),
                                       ("2026-10-25", "1311", "VND", 60), ("2026-10-25", "1312", "USD", 10),
                                       ("2026-10-25", "1312", "USD", None)):
                cls.admin.execute("""INSERT INTO kho.cong_no_mo
                    (phap_nhan_id, ngay_chup, tai_khoan, doi_tac_junsky, item_key, loai, so_tien_minor, con_lai_minor, tien_te)
                    VALUES (%s,%s,%s,'KH_DEMO.CHUNG_A',%s,'KHAC',100,%s,%s)""",
                    (cls.ids["PN_DEMO_A"], ngay, tk, "DEMO-" + uuid.uuid4().hex, con, tt))


if __name__ == "__main__":
    unittest.main()
