"""S1 thuần/mock: dữ liệu DEMO, không driver/DSN, không đọc dữ liệu thật."""
import json
import unittest
from contextlib import contextmanager
from datetime import date
from unittest.mock import Mock

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2.crm_s1 import CrmDanhSachK2, SQL, _dong, bo_loc

NGAY = date(2026, 10, 25)


def dong(**sua):
    return {"id": "DEMO-HD-1", "phap_nhan": "PN_DEMO_A", "so_hop_dong": "HĐ DEMO 01", "ma_noi_bo": "HD01",
            "loai": "THUE_DAT", "khach": "KHÁCH DEMO", "ma_khach": "KH_DEMO", "du_an": "DA_DEMO",
            "lo_can": "A01", "gia_tri_minor": 9007199254740993, "tien_te": "VND", "ngay_ky": NGAY,
            "ngay_hieu_luc": NGAY, "trang_thai": "CHO_KY", "nguoi_phu_trach": ["MO_PHONG_BH"],
            "nguon": "MAU", "mau_phien_ban": 2, "lich": [], "so_junsky": [], **sua}


def lich(han="2026-10-25", tien="100", thu="20", tt="VND", dot=1):
    return {"id": f"DEMO-DOT-{dot}", "dot": dot, "han": han, "moc": "Mốc DEMO", "so_tien_minor": tien,
            "da_thu_minor": thu, "tien_te": tt}


class MauGia:
    """Chỉ mock biên DB: quyền thực được kiểm bằng test PG; ghi nhận scope SQL."""
    def __init__(self, rows):
        self.rows = rows
        self.c = Mock()
        self.c.execute.side_effect = lambda sql, params=(): self.rows
        self.danh_tinh = Mock(return_value={"id": "DEMO-USER", "dang_nhap": "MO_PHONG_BH"})
        self.rr = None

    def hom_nay(self):
        return NGAY

    @contextmanager
    def _tx(self, dt, *, rr=False):
        self.rr = rr
        yield self.c


class S1Tinh(unittest.TestCase):
    def doc(self, rows, **loc):
        self.m = MauGia(rows)
        return CrmDanhSachK2(self.m).danh_sach("MO_PHONG_BH", loc)

    def test_s1_b_chua_co_so_khong_phai_khong(self):
        r = self.doc([dong()])["hop_dong"][0]
        self.assertEqual((r["cong_no_junsky"]["hien_thi"], r["cong_no_junsky"]["so_du"]), ("chưa có sổ", []))
        self.assertEqual(r["thu_crm"]["trang_thai"], "CHUA_CO_LICH")

    def test_so_du_khong_la_so_da_co_so(self):
        r = _dong(dong(so_junsky=[{"ngay_so": NGAY, "tai_khoan": "1311", "tien_te": "VND", "so_du_minor": "0"}]), NGAY)
        self.assertEqual(r["cong_no_junsky"]["trang_thai"], "CO_SO")
        self.assertEqual(r["cong_no_junsky"]["so_du"][0]["so_du_minor"], "0")
        self.assertEqual(r["chenh_crm_junsky"]["trang_thai"], "KHONG_SO_SANH")

    def test_thu_khong_cong_hai_currency_khong_mat_chu_so(self):
        r = _dong(dong(lich=[lich(tien="9007199254740993"), lich(tt="USD", dot=2)]), NGAY)
        self.assertEqual(r["gia_tri_minor"], "9007199254740993")
        self.assertEqual(r["thu_crm"]["theo_tien_te"], [
            {"tien_te": "USD", "phai_thu_minor": "100", "da_thu_minor": "20", "con_lai_minor": "80"},
            {"tien_te": "VND", "phai_thu_minor": "9007199254740993", "da_thu_minor": "20", "con_lai_minor": "9007199254740973"}])

    def test_null_khong_bien_thanh_tong_mot_phan(self):
        r = _dong(dong(gia_tri_minor=None, lich=[lich(tien=None), lich(dot=2)]), NGAY)
        self.assertIsNone(r["gia_tri_minor"])
        self.assertEqual(r["thu_crm"]["trang_thai"], "THIEU_CAN_CU")
        self.assertIsNone(r["thu_crm"]["theo_tien_te"][0]["con_lai_minor"])

    def test_w5_bien_ngay_su_kien_da_thu_huy_khong_tu_qua_han(self):
        ds = [lich(han=None), lich(han="2026-10-24", dot=2), lich(han="2026-11-01", dot=3),
              lich(han="2026-11-02", dot=4), lich(thu="100", dot=5), lich(dot=6)]
        r = _dong(dong(lich=ds), NGAY)
        self.assertEqual(r["viec"]["W5"], 2)
        self.assertIn("QUA_HAN", r["co"])
        r = _dong(dong(lich=[lich(han=None)]), NGAY)
        self.assertNotIn("QUA_HAN", r["co"])
        self.assertEqual(r["dot_ke_tiep"]["trang_thai"], "MOC_CHUA_CO_NGAY")
        self.assertIn("l.trang_thai <> 'HUY'", SQL)

    def test_w1_bo_sung_mo_k5_w3_phu_luc(self):
        r = _dong(dong(trang_thai="HIEU_LUC", bo_sung_mo=True, pb_cho_kiem=True), NGAY)
        self.assertEqual((r["viec"]["W1"], r["viec"]["W3"]), (1, 1))

    def test_w4_chi_lech_hien_hanh_chua_xu_ly(self):
        ds = {"trang_thai": "LECH", "ket_qua_id": "DEMO-KQ", "lech": [{"ma": "GIATRI"}, {"ma": "NGAY"}]}
        self.assertEqual(_dong(dong(g5=ds), NGAY)["viec"]["W4"], 1)
        xl = [{"muc_tieu_id": "DEMO-KQ", "ma_lech": ma} for ma in ("GIATRI", "NGAY")]
        self.assertEqual(_dong(dong(g5=ds, xu_ly=xl), NGAY)["viec"]["W4"], 0)
        self.assertEqual(_dong(dong(g5={"trang_thai": "HOLD", "lech_mot_phan": [{"ma": "GIATRI"}]}), NGAY)["viec"]["W4"], 0)

    def test_w1_w2_w3_w4_w5_khong_doi_theo_trang(self):
        rows = [dong(id="DEMO-1"), dong(id="DEMO-2", trang_thai="CHO_BO_SUNG"),
                dong(id="DEMO-3", trang_thai="DA_KY", lich=[lich()])]
        r = self.doc(rows, kich_thuoc_trang="1", trang="2")
        self.assertEqual(r["tong"], 3)
        self.assertEqual([r["the_so"][w]["so_luong"] for w in ("W1", "W2", "W3", "W4", "W5")], [1, 1, 1, 0, 1])
        self.assertEqual(r["the_so"]["W2"]["trang_thai"], "MOT_PHAN")
        self.assertIsNone(r["the_so"]["W5"]["tien_chua_ro"])
        self.assertTrue(self.m.rr)
        self.assertEqual(self.m.c.execute.call_count, 2)
        self.m.c.execute.assert_any_call("SET TRANSACTION READ ONLY")
        self.m.c.execute.assert_any_call(SQL, (NGAY,))

    def test_loc_the_khong_lam_mat_the_khac(self):
        r = self.doc([dong(), dong(id="DEMO-2", trang_thai="CHO_BO_SUNG")], the="W1")
        self.assertEqual((r["tong"], r["the_so"]["W2"]["so_luong"]), (1, 1))

    def test_loc_tong_hop_va_ngay_bao_gom_hai_dau(self):
        r = self.doc([dong(), dong(id="DEMO-2", khach="DEMO KHAC", ngay_ky=None)],
                     phap_nhan="PN_DEMO_A", loai="THUE_DAT", du_an="DA_DEMO", trang_thai="CHO_KY",
                     nguoi_phu_trach="MO_PHONG_BH", ngay_ky_tu="2026-10-25", ngay_ky_den="2026-10-25", tim="khách demo")
        self.assertEqual(r["tong"], 1)
        self.assertEqual(self.doc([dong()], phap_nhan="PN_DEMO_B")["the_so"]["W2"]["so_luong"], 0)
        self.assertEqual(self.doc([dong()], tim="%' OR 1=1 --")["tong"], 0)

    def test_rong_khong_lo_so(self):
        r = self.doc([])
        self.assertEqual((r["hop_dong"], r["tong"]), ([], 0))
        self.assertTrue(all(t["so_luong"] == 0 for t in r["the_so"].values()))
        self.assertEqual(r["thong_bao"], "Không có hợp đồng trong phạm vi của bạn")

    def test_pii_whitelist_moi_vai_khong_raw_json(self):
        for vai in ("BAN_HANG", "KE_TOAN", "CFO", "XEM"):
            r = self.doc([dong(cccd_mh="DEMO_BI_MAT", stk_mh="DEMO_BI_MAT", lien_he="DEMO_BI_MAT",
                               du_lieu={"bi_mat": "DEMO_BI_MAT"}, vai_tro=vai)])
            self.assertNotIn("DEMO_BI_MAT", json.dumps(r, ensure_ascii=False))

    def test_scope_sql_phai_kiem_db_khong_suy_tu_nguoi_tao(self):
        scope = SQL.split(")\nSELECT h.id", 1)[0]
        for guard in ("MATERIALIZED", "master.ktt_danh_tinh()", "master.ktt_duoc(h.phap_nhan_id, 'CRM')",
                      "master.ktt_co_vai", "master.crm_ky_pham_vi_duoc(s.id)", "h.module_chu IS NULL", "'VAY','MUA'"):
            self.assertIn(guard, scope)
        self.assertNotIn("tao_boi", scope)
        for pii in ("cccd", "stk_mh", "lien_he", "ky_pdf", "r.du_lieu,"):
            self.assertNotIn(pii, SQL)
        self.assertIn("n.phap_nhan_id = h.phap_nhan_id", SQL)
        self.assertIn("GROUP BY n.ngay_chup, n.tai_khoan, n.tien_te", SQL)

    def test_tham_so_sai_khong_doc_db(self):
        for loc in ({"trang": "0"}, {"trang": "1.0"}, {"trang": True}, {"trang": ["1", "2"]},
                    {"kich_thuoc_trang": "101"}, {"tim": "a" * 201}, {"tim": "a\n"}, {"actor": "DEMO"},
                    {"trang_thai": "HACK"}, {"loai": "VAY"}, {"co": "HACK"}, {"the": "W9"},
                    {"ngay_ky_tu": "2026-02-30"}, {"ngay_hieu_luc_den": "20261025"},
                    {"ngay_ky_tu": "2026-10-26", "ngay_ky_den": "2026-10-25"}):
            with self.subTest(loc=loc):
                m = MauGia([])
                with self.assertRaises(DataError) as e:
                    CrmDanhSachK2(m).danh_sach("MO_PHONG_BH", loc)
                self.assertEqual(e.exception.code, "CRM_S1_THAM_SO_SAI")
                m.c.execute.assert_not_called()
        self.assertEqual(bo_loc({})["kich_thuoc_trang"], 25)


if __name__ == "__main__":
    unittest.main()
