"""UI-2: thuần/mock biên CSDL, chạy service G1/G2/S1 thật, không mở server."""
import json
import threading
import unittest
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from unittest.mock import Mock, patch

from kho_tri_thuc.giao_dien import crm_g
from kho_tri_thuc.giao_dien.khung_khai_bao import CrmKhungK2, MODULE
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2.crm_mau import CrmMauK2
from kho_tri_thuc.k2.crm_s1 import CrmDanhSachK2
from test_crm_42_s1_tinh import MauGia, dong, lich


class MauKhungGia(MauGia):
    """Chỉ giả kết quả SQL; lọc, phân trang, đếm dùng code sản phẩm."""
    danh_sach = CrmMauK2.danh_sach

    def __init__(self, vai="BAN_HANG", rows=None, modules=None):
        if rows is None:
            rows = [dong(id="DEMO-CHO-KY"), dong(id="DEMO-CHO-KIEM", trang_thai="DA_KY"),
                    dong(id="DEMO-HIEU-LUC", trang_thai="HIEU_LUC",
                         lich=[lich(), lich(dot=2), lich(han="2026-10-24", dot=3)]),
                    dong(id="DEMO-BO-SUNG", trang_thai="CHO_BO_SUNG")]
        rows = deepcopy(rows)
        if vai == "XEM" or modules == ["CRM"] and vai != "BAN_HANG":
            for r in rows:
                r["xem_tien"] = False
        super().__init__(rows)
        self.danh_tinh.return_value.update(dang_nhap="MO_PHONG_" + vai, vai_tro=vai,
                                          quyen={"DEMO-PN-A": {"module": modules if modules is not None else ["CRM", "M1"]}})
        self.conn_tin_cay = object()
        self.root = Path("DEMO-KHONG-GHI")
        self.bg = [{"id": "DEMO-BG-1", "trang_thai": "NHAP", "ngay": "2026-10-25",
                    "du_lieu": {}, "tinh": {}, "khach_ten": "KHÁCH DEMO"},
                   {"id": "DEMO-BG-2", "trang_thai": "DA_CHUYEN", "ngay": "2026-10-25",
                    "du_lieu": {}, "tinh": {}, "khach_ten": "KHÁCH DEMO"}]
        self.mau_rows = [{"phien_ban_id": "DEMO-MAU-1", "trang_thai": "CHO_CFO", "quyen_doc": "DAY_DU"},
                         {"phien_ban_id": "DEMO-MAU-2", "trang_thai": "CHO_KIEM", "quyen_doc": "DAY_DU"}]
        self.sql_quyen = []

    def execute(self, sql, params=()):
        if "AS duoc" in sql:
            self.sql_quyen.append((sql, params))
            dt = self.danh_tinh.return_value
            duoc = any("CRM" in q["module"] for q in dt["quyen"].values()) and dt["vai_tro"] in params[0]
            return Mock(fetchone=lambda: {"duoc": duoc})
        return super().execute(sql, params)

    def _nhieu(self, c, sql, params=()):
        if "FROM master.crm_bao_gia b" in sql:
            return deepcopy(self.bg)
        if "FROM master.crm_mau m" in sql:
            return deepcopy(self.mau_rows)
        return []


def doc_route(mau, path="/api/khung/module/crm", phien=True, loi=None):
    app = Mock()
    app.mutation_lock = threading.RLock()
    app.crm_phien.side_effect = None if phien else DataError("CRM_PHIEN", "Phiên CRM đã hết.")
    app.crm_phien.return_value = ("DEMO-SID", mau.danh_tinh.return_value["dang_nhap"], False)
    app._crm_db.side_effect = loi or (lambda fn, *args: fn(*args))
    h = Mock(path=path)
    h.crm_sid.return_value = "DEMO-SID"
    h.send_content.side_effect = lambda status, data, **kwargs: (status, data, kwargs)
    with patch.object(crm_g, "dich_vu_s1", return_value=nullcontext(mau)), \
            patch.object(crm_g, "dich_vu") as ghi, patch.object(crm_g, "_khoi_dong_g5") as g5:
        r = crm_g.dieu_huong(h, app, False, urlsplit(path).path, parse_qs(urlsplit(path).query))
        ghi.assert_not_called()
        g5.assert_not_called()
    return r


class KhungCrmTinh(unittest.TestCase):
    def test_bon_vai_demo_dung_phan_va_the_khong_lo_ngoai_vai(self):
        mong_doi = {
            "BAN_HANG": ["bao_gia_nhap", "hd_dot_den_han"],
            "KE_TOAN": ["hd_cho_kiem", "hd_dot_qua_han"],
            "CFO": ["mau_cho_duyet", "hd_dot_qua_han", "hd_hieu_luc"],
            "XEM": ["hd_hieu_luc"],  # QD-15/22: người xem không được đếm tiền.
        }
        for vai, the in mong_doi.items():
            with self.subTest(vai=vai):
                m = MauKhungGia(vai)
                status, r, headers = doc_route(m)
                self.assertEqual(status, 200)
                self.assertEqual([x["ma"] for x in r["the"]], the)
                self.assertEqual([x["ma"] for x in r["phan"]],
                                 ["hop_dong", "thu_tien", "bao_cao"] if vai == "XEM" else
                                 ["hop_dong", "bao_gia", "mau", "tiep_nhan", "thu_tien", "bao_cao"])
                self.assertEqual(headers["headers"]["Cache-Control"], "no-store")
                self.assertEqual(r["lam_moi_sau_giay"], 60)
                for sql, params in m.sql_quyen:
                    self.assertIn("master.ktt_duoc(p.id, 'CRM')", sql)
                    self.assertIn("master.ktt_co_vai", sql)
                    self.assertEqual(params, ([vai],))

    def test_ke_toan_truong_cung_nhom_ke_toan(self):
        a = CrmKhungK2(MauKhungGia("KE_TOAN")).module("MO_PHONG_KE_TOAN")
        b = CrmKhungK2(MauKhungGia("KE_TOAN_TRUONG")).module("MO_PHONG_KE_TOAN_TRUONG")
        self.assertEqual(a, b)

    def test_moi_the_so_bang_danh_sach_loc_cung_service(self):
        for vai in ("BAN_HANG", "KE_TOAN", "CFO", "XEM"):
            m = MauKhungGia(vai)
            for t in CrmKhungK2(m).module("MO_PHONG_" + vai)["the"]:
                loc = t["loc"]
                with self.subTest(vai=vai, the=t["ma"]):
                    if loc["phan"] == "hop_dong":
                        ds = CrmDanhSachK2(m).danh_sach("MO_PHONG_" + vai, loc["tham_so"])
                        self.assertEqual(t["so"], ds["tong"])
                        self.assertEqual(t["so"], len(ds["hop_dong"]))
                    else:
                        path = "/api/crm/" + loc["phan"].replace("_", "-") + "?" + urlencode(loc["tham_so"])
                        st, ds, _ = doc_route(m, path)
                        self.assertEqual(st, 200)
                        self.assertEqual(t["so"], ds["tong"])
                        self.assertEqual(t["so"], len(ds["bao_gia" if loc["phan"] == "bao_gia" else "phien_ban"]))

    def test_w5_dem_hop_dong_khong_nham_hai_dot_thanh_hai_dong(self):
        m = MauKhungGia()
        ds = CrmDanhSachK2(m).danh_sach("MO_PHONG_BAN_HANG", {"the": "W5"})
        self.assertEqual((ds["the_so"]["W5"]["so_luong"], ds["tong"]), (2, 1))
        t = CrmKhungK2(m).module("MO_PHONG_BAN_HANG")["the"][1]
        self.assertEqual(t["so"], 1)
        self.assertIn("Hợp đồng", t["nhan"])

    def test_khong_quyen_module_tra_rong_khong_doc_nguon(self):
        m = MauKhungGia(modules=["M1"])
        st, r, _ = doc_route(m)
        self.assertEqual(st, 200)
        self.assertEqual((r["the"], r["phan"], r["khong_quyen"]), ([], [], True))
        self.assertEqual(m.c.execute.call_count, 2)

    def test_quyen_csdl_thu_hoi_thang_danh_tinh_da_nap(self):
        m = MauKhungGia()
        m.c.execute.side_effect = lambda *args: Mock(fetchone=lambda: {"duoc": False})
        r = CrmKhungK2(m).module("MO_PHONG_BAN_HANG")
        self.assertEqual((r["the"], r["phan"], r["khong_quyen"]), ([], [], True))

    def test_dem_toan_tap_khong_cat_o_trang_25_hay_100(self):
        m = MauKhungGia("KE_TOAN", rows=[dong(id=f"DEMO-{i}", trang_thai="DA_KY") for i in range(205)])
        r = CrmKhungK2(m).module("MO_PHONG_KE_TOAN")
        t = next(t for t in r["the"] if t["ma"] == "hd_cho_kiem")
        ds = CrmDanhSachK2(m).danh_sach("MO_PHONG_KE_TOAN", t["loc"]["tham_so"])
        self.assertEqual((t["so"], ds["tong"], len(ds["hop_dong"])), (205, 205, 25))

    def test_nguon_rong_van_tra_so_khong_khong_bia_cho_phan_chua_co_nguon(self):
        m = MauKhungGia(rows=[])
        m.bg, m.mau_rows = [], []
        r = CrmKhungK2(m).module("MO_PHONG_BAN_HANG")
        self.assertTrue(all(t["so"] == 0 for t in r["the"]))
        p = {p["ma"]: p for p in r["phan"]}
        for ma in ("hop_dong", "bao_gia", "thu_tien"):
            self.assertEqual(p[ma]["so_viec"], 0)
            self.assertFalse(p[ma]["qua_han"])
        for ma in ("mau", "tiep_nhan", "bao_cao"):
            self.assertNotIn("so_viec", p[ma])

    def test_khong_tien_an_the_so_tien_ca_khi_co_du_lieu(self):
        for vai in ("KE_TOAN", "CFO"):
            with self.subTest(vai=vai):
                r = CrmKhungK2(MauKhungGia(vai, modules=["CRM"])).module("MO_PHONG_" + vai)
                self.assertNotIn("hd_dot_qua_han", [t["ma"] for t in r["the"]])
                self.assertNotIn("so_viec", next(p for p in r["phan"] if p["ma"] == "thu_tien"))

    def test_phan_qua_han_dung_nguon_khong_to_do_cho_ky_chua_co_nguong(self):
        r = CrmKhungK2(MauKhungGia("KE_TOAN")).module("MO_PHONG_KE_TOAN")
        self.assertTrue(next(p for p in r["phan"] if p["ma"] == "thu_tien")["qua_han"])
        self.assertFalse(next(p for p in r["phan"] if p["ma"] == "hop_dong")["qua_han"])
        bh = CrmKhungK2(MauKhungGia()).module("MO_PHONG_BAN_HANG")
        self.assertFalse(next(p for p in bh["phan"] if p["ma"] == "hop_dong")["qua_han"])
        self.assertNotIn("hd_cho_ky_qua_han", [t["ma"] for t in bh["the"]])

    def test_bao_gia_cham_tran_khong_tra_tong_cat_cut(self):
        m = MauKhungGia()
        m.bg = [deepcopy(m.bg[0]) for _ in range(200)]
        r = CrmKhungK2(m).module("MO_PHONG_BAN_HANG")
        self.assertNotIn("bao_gia_nhap", [t["ma"] for t in r["the"]])
        self.assertNotIn("so_viec", next(p for p in r["phan"] if p["ma"] == "bao_gia"))

    def test_dem_chi_doc_tom_tat_khong_doc_g5_lich_so_cong_no(self):
        m = MauKhungGia("KE_TOAN")
        CrmKhungK2(m).module("MO_PHONG_KE_TOAN")
        for call in m.c.execute.call_args_list:
            sql = call.args[0]
            for nang in ("crm_kiem_g5_xet(", "crm_da_lien_ket(", "kho.cong_no_mo", "AS lich"):
                self.assertNotIn(nang, sql)

    def test_ten_nhan_tieng_viet_khong_tra_ma_ky_thuat(self):
        for vai in ("BAN_HANG", "KE_TOAN", "CFO", "XEM"):
            r = CrmKhungK2(MauKhungGia(vai)).module("MO_PHONG_" + vai)
            for v in [p["ten"] for p in r["phan"]] + [t["nhan"] for t in r["the"]]:
                self.assertNotRegex(v, r"W[1-5]|G[1-8]|NHAP|CHO_CFO|HIEU_LUC|_")
                self.assertNotIn("?", v)
            self.assertEqual(json.loads(json.dumps(r, ensure_ascii=False)), r)
        self.assertEqual(MODULE["crm"]["ten"], "CRM · Hợp đồng bán hàng")

    def test_route_module_la_unknown_va_post_khong_cuop_route_cu(self):
        self.assertTrue(crm_g.la_route(False, "/api/khung/module/crm"))
        self.assertFalse(crm_g.la_route(True, "/api/khung/module/crm"))
        self.assertFalse(crm_g.la_route(True, "/api/crm/mau"))
        self.assertEqual(doc_route(MauKhungGia(), "/api/khung/module/khong-co")[0], 404)

    def test_phien_va_query_khong_gia_mao_authority(self):
        self.assertEqual(doc_route(MauKhungGia(), phien=False)[0], 400)
        for query in ("vai=CFO", "module=CRM", "trang_thai=HIEU_LUC"):
            self.assertEqual(doc_route(MauKhungGia(), "/api/khung/module/crm?" + query)[0], 400)
        for query in ("trang_thai=NHAP&vai=CFO", "trang_thai=NHAP&trang_thai=NHAP", "trang_thai=SAI", "trang_thai="):
            self.assertEqual(doc_route(MauKhungGia(), "/api/crm/bao-gia?" + query)[0], 400)
        self.assertEqual(doc_route(MauKhungGia("XEM"), "/api/crm/mau?trang_thai=CHO_CFO")[0], 403)

    def test_csdl_loi_503_co_cau_truc_khong_lo_chi_tiet(self):
        for ma in ("CRM_G_CHUA_SAN_SANG", "PG_KHONG_KET_NOI", "CSDL_TU_CHOI"):
            st, r, _ = doc_route(MauKhungGia(), loi=DataError(ma, "DEMO chi tiết kết nối kín"))
            self.assertEqual((st, r["error"]), (503, "CRM_G_CHUA_SAN_SANG"))
            self.assertNotIn("kín", r["message"])


if __name__ == "__main__":
    unittest.main()
