"""BG-1a: phép tính thuần + seam service/HTTP giả, không PostgreSQL/Word/mạng/dữ liệu thật."""
from __future__ import annotations

import json
import unittest
from contextlib import nullcontext
from datetime import date
from types import SimpleNamespace
from unittest import mock

from kho_tri_thuc.giao_dien import crm_g as HTTP
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import crm_giao_ket as GK


LOAI = "11111111-1111-4111-8111-111111111111"
DU_AN = "22222222-2222-4222-8222-222222222222"
BG = "33333333-3333-4333-8333-333333333333"


def bao_gia(*nhap, **sua):
    return {"loai_hinh_id": LOAI, "gia": {"tien_te": "USD", "don_gia": "100", "dien_tich": "15000", "co_so_thue": "NET"},
            "khach": {"du_thao": {"ten": "Khách tổng hợp BG1"}}, "don_vi": {"ma": "LO-THU"},
            "fx": {"cap": "USD/VND", "ty_gia": "25500", "ngay": "2026-10-24"},
            "lich": [{"gia_tri_nhap": v} for v in (nhap or ("30%", "70%"))], **sua}


def tinh(d):
    return GK.tinh_bao_gia(GK.chuan_hoa_bao_gia(d), None)


class OThongMinh(unittest.TestCase):
    def test_co_phan_tram_tinh_tien_va_vnd(self):
        t = tinh(bao_gia())
        x = t["dong"][0]
        self.assertEqual((x["ty_le"], x["so_tien"], x["so_tien_minor"], x["nguon_nhap"]), ("30", "45000000", "45000000", "TY_LE"))
        self.assertEqual(x["hien_thi_mo"], "= 450.000 USD · ≈ 11.475 tr VND")
        self.assertEqual(t["tong_minor"], "150000000")
        self.assertEqual(t["chan_in"], [])

    def test_khong_phan_tram_luon_la_tien_ke_ca_nho_hon_100(self):
        for v in ("30", "100", "0", "0,50"):
            with self.subTest(v=v):
                t = tinh(bao_gia(v, gia={"tien_te": "USD", "tong": "100", "co_so_thue": "NET"}))
                x = t["dong"][0]
                self.assertEqual(x["nguon_nhap"], "SO_TIEN")
                self.assertEqual(x["so_tien"], str(int(v.replace(",", "")) if "," in v else int(v) * 100))
                self.assertTrue(x["hien_thi_mo"].startswith("= " + v.replace(",50", ",5") + "%"))

    def test_tien_khong_phan_tram_tinh_ty_le(self):
        t = tinh(bao_gia("450.000", "1.050.000"))
        self.assertEqual([x["ty_le"] for x in t["dong"]], ["30", "70"])
        self.assertEqual(t["dong"][0]["hien_thi_mo"], "= 30% · ≈ 11.475 tr VND")
        self.assertTrue(t["tong_ty_le_khop"])
        self.assertTrue(t["tong_tien_khop"])

    def test_dau_cham_phay_kieu_viet(self):
        t = tinh(bao_gia("1.500.000,50", gia={"tien_te": "USD", "tong": "1500000.50", "co_so_thue": "NET"}))
        self.assertEqual(t["dong"][0]["so_tien"], "150000050")
        self.assertEqual(t["dong"][0]["so_tien_hien_thi"], "1.500.000,5 USD")
        self.assertEqual(t["chan_in"], [])
        t = tinh(bao_gia("30,5%", "69,5%"))
        self.assertEqual(t["dong"][0]["ty_le"], "30.5")
        self.assertEqual(t["dong"][0]["ty_le_hien_thi"], "30,5%")
        self.assertTrue(t["dong"][0]["hien_thi_mo"].startswith("= 457.500 USD"))
        self.assertTrue(t["tong_ty_le_khop"])

    def test_chuoi_sai_tra_ma_va_thong_bao_dung_dong(self):
        for v in ("abc", "1.50", "1,500.00", "1..000", "30%%", "%30", "30%5", "-1", "NaN", "1e3", "1 000", "1" * 25):
            with self.subTest(v=v):
                t = tinh(bao_gia("30%", v))
                self.assertEqual(t["dong"][0]["loi"], [])
                x = t["dong"][1]
                self.assertEqual(x["loi"], ["GIA_TRI_NHAP_SAI"])
                self.assertEqual(x["loi_chi_tiet"][0]["truong"], "lich.1.gia_tri_nhap")
                self.assertEqual(x["loi_chi_tiet"][0]["dong"], 2)
                self.assertIn("Dòng 2:", x["loi_chi_tiet"][0]["thong_bao"])
                self.assertFalse(t["tong_ty_le_khop"])
                self.assertTrue(t["chan_in"])

    def test_rong_la_chua_nhap_khong_suy_tu_truong_cu(self):
        for v in ("", "   "):
            t = tinh(bao_gia(lich=[{"gia_tri_nhap": v, "loai": "PERCENT", "ty_le": "100"}]))
            self.assertEqual(t["dong"][0]["loi"], ["CHUA_CO_GIA_TRI"])
            self.assertIsNone(t["dong"][0]["so_tien"])
            self.assertEqual(t["dong"][0]["hien_thi_mo"], "")

    def test_o_moi_uu_tien_hon_truong_cu_va_tien_te_dong(self):
        t = tinh(bao_gia(lich=[{"gia_tri_nhap": " 100% ", "loai": "AMOUNT", "so_tien": "sai cu", "tien_te": "VND"}]))
        self.assertEqual(t["chan_in"], [])
        self.assertEqual(t["dong"][0]["nguon_nhap"], "TY_LE")

    def test_tuong_thich_truong_typed_cu_dau_cham_thap_phan(self):
        t = tinh(bao_gia(lich=[{"loai": "PERCENT", "ty_le": "30.5"}, {"loai": "AMOUNT", "so_tien": "1042500.00", "tien_te": "USD"}]))
        self.assertEqual([x["ty_le"] for x in t["dong"]], ["30.5", "69.5"])
        self.assertEqual(t["chan_in"], [])

    def test_tong_90_va_110_co_cau_ly_do(self):
        for v, msg in (("60%", "Tổng % = 90, thiếu 10"), ("80%", "Tổng % = 110, thừa 10"),
                       ("60,5%", "Tổng % = 90,5, thiếu 9,5")):
            with self.subTest(v=v):
                t = tinh(bao_gia("30%", v))
                self.assertFalse(t["tong_ty_le_khop"])
                self.assertEqual(t["chan_in"][0]["ma"], "TONG_TY_LE_KHAC_100")
                self.assertEqual(t["ly_do_chan_in"], msg)
                self.assertEqual(t["ly_do_chan_chuyen"], msg)

    def test_usd_thieu_fx_giu_nguyen_ma_chan_in(self):
        t = tinh(bao_gia(fx=None))
        self.assertEqual([x["ma"] for x in t["chan_in"]], ["USD_THIEU_FX"])
        self.assertEqual(t["dong"][0]["hien_thi_mo"], "= 450.000 USD")
        self.assertIsNone(t["vnd_tham_chieu"])

    def test_tu_tinh_ghi_de_moi_va_tong_cu_khong_chan_in(self):
        t = tinh(bao_gia())
        self.assertEqual((t["tong_minor"], t["tong_tinh_minor"]), ("150000000", "150000000"))
        for sua in ({"tong_gia_tri_ghi_de": "1400000"},
                    {"gia": {"tien_te": "USD", "don_gia": "100", "dien_tich": "15000", "tong": "1400000", "co_so_thue": "NET"}}):
            with self.subTest(sua=sua):
                t = tinh(bao_gia(**sua))
                self.assertEqual(t["tong_minor"], "140000000")
                self.assertEqual([x["so_tien"] for x in t["dong"]], ["42000000", "98000000"])
                cb = next(x for x in t["canh_bao"] if x["ma"] == "TONG_LECH_DON_GIA_X_DIEN_TICH")
                self.assertEqual(cb["thong_bao"], "Khác tính toán: 1.400.000 USD; đơn giá × diện tích = 1.500.000 USD.")
                self.assertEqual(t["chan_in"], [])
                self.assertEqual(t["ly_do_chan_in"], "")

    def test_ghi_de_uu_tien_va_scale_khong_lam_tron(self):
        t = tinh(bao_gia(tong_gia_tri_ghi_de="0", lich=[{"gia_tri_nhap": "100%"}]))
        self.assertEqual(t["tong_minor"], "0")
        self.assertEqual(t["chan_in"], [])
        t = tinh(bao_gia(tong_gia_tri_ghi_de="1.001"))
        self.assertIsNone(t["tong_minor"])
        self.assertIn("TONG_KHONG_DUNG_SCALE", [x["ma"] for x in t["chan_in"]])
        t = tinh(bao_gia("0,001"))
        self.assertIn("KHONG_DUNG_SCALE_TIEN_TE", t["dong"][0]["loi"])

    def test_thieu_tien_te_khong_loi_may_chu(self):
        t = tinh(bao_gia("30", gia={}, fx=None))
        self.assertIn("THIEU_TIEN_TE", [x["ma"] for x in t["chan_in"]])
        self.assertIn("CHUA_CO_TIEN_TE", t["dong"][0]["loi"])

    def test_ty_le_khong_huu_han_giu_chan_in(self):
        t = tinh(bao_gia("1", gia={"tien_te": "VND", "tong": "3", "co_so_thue": "NET"}, fx=None))
        self.assertIn("TY_LE_SUY_RA_KHONG_HUU_HAN", t["dong"][0]["loi"])
        self.assertTrue(t["chan_in"])

    def test_moc_chuan_va_ngay_hien_thi(self):
        rows = [{"gia_tri_nhap": "20%", "moc_loai": "SU_KIEN", "moc_su_kien": ma}
                for ma in ("KY_HD", "BAN_GIAO", "SO", "XONG_TANG_5", "SAU_KY_30")]
        t = tinh(bao_gia(lich=rows))
        self.assertEqual([x["moc_hien_thi"] for x in t["dong"]], ["Ký", "Bàn giao", "Sổ", "Xây xong tầng 5", "Sau ký + 30 ngày"])
        t = tinh(bao_gia(lich=[{"gia_tri_nhap": "100%", "moc_loai": "NGAY", "moc_ngay": "2026-12-31"}]))
        self.assertEqual(t["dong"][0]["moc_ngay_hien_thi"], "31/12/2026")
        self.assertEqual(GK.danh_muc_moc_chuan()["moc_tham_so"][1]["mau_ma"], "SAU_KY_<n>")


class SeamKhongPostgres(unittest.TestCase):
    def setUp(self):
        self.c = mock.MagicMock()
        self.m = SimpleNamespace(root=".", danh_tinh=mock.Mock(return_value={"dang_nhap": "nguoi-thu", "vai_tro": "BAN_HANG"}),
                                 _tx=mock.Mock(side_effect=lambda *a, **k: nullcontext(self.c)), _mot=mock.Mock(), _nhieu=mock.Mock(),
                                 hom_nay=lambda: date(2026, 10, 24), conn_tin_cay=object())
        self.s = GK.CrmGiaoKetK2(self.m)

    def test_xem_truoc_nhan_ngay_khong_ghi(self):
        self.m._mot.side_effect = [{"ok": True, "phap_nhan_id": "PN", "phap_nhan": "PN_THU", "phap_nhan_ten": "Pháp nhân thử",
                                    "loai_hinh": "KCN", "loai_hinh_ten": "Thuê đất khu công nghiệp"}, {"ma": "DA_THU", "ten": "Dự án thử"}]
        kq = self.s.xem_truoc("nguoi-thu", du_lieu=bao_gia(du_an_id=DU_AN, het_han="2026-11-01"))
        self.assertEqual(kq["nhan"]["phap_nhan"]["ten"], "Pháp nhân thử")
        self.assertEqual(kq["nhan"]["loai_hinh"]["ten"], "Thuê đất khu công nghiệp")
        self.assertEqual(kq["nhan"]["du_an"]["ten"], "Dự án thử")
        self.assertEqual((kq["het_han_hien_thi"], kq["fx_ngay_hien_thi"]), ("01/11/2026", "24/10/2026"))
        self.assertEqual(len(kq["du_lieu_sha256"]), 64)
        self.c.execute.assert_not_called()

    def test_xem_truoc_khong_tra_nhan_du_an_ngoai_pham_vi(self):
        self.m._mot.side_effect = [{"ok": True, "phap_nhan_id": "PN"}, None]
        with self.assertRaises(DataError) as cm:
            self.s.xem_truoc("nguoi-thu", du_lieu=bao_gia(du_an_id=DU_AN))
        self.assertEqual(cm.exception.code, "CRM_G_KHONG_THAY")

    def test_danh_sach_nhan_ten_va_ngay(self):
        self.m._nhieu.side_effect = [[], [], [], [{"ngay": "2026-10-24", "phap_nhan_ten": "Pháp nhân thử", "loai_hinh_ten": "Thuê đất",
            "du_an_ten": "Dự án thử", "du_lieu": {"het_han": "2026-11-01"}, "tinh": {}, "khach_ten": "Khách thử"}], []]
        kq = self.s.danh_sach("nguoi-thu")["bao_gia"][0]
        self.assertEqual((kq["ngay_hien_thi"], kq["het_han_hien_thi"]), ("24/10/2026", "01/11/2026"))
        self.assertEqual(kq["du_an_ten"], "Dự án thử")
        sql = "\n".join(call.args[1] for call in self.m._nhieu.call_args_list)
        self.assertIn("p.ten AS phap_nhan_ten", sql)
        self.assertIn("l.ten AS loai_hinh_ten", sql)

    def luu(self, ghi_de, *, lap_lai=False, cu=None):
        kq = {"bao_gia_id": BG, "revision": 1, "so_bao_gia": "BG-THU", "trang_thai": "NHAP"}
        self.s._tra = mock.Mock(return_value=cu)
        self.s._trung_don_vi = mock.Mock(return_value=[])
        self.m._mot.return_value = {"phap_nhan_id": "PN"}
        self.c.execute.return_value.fetchone.return_value = {"r": {"ket_qua": kq, "lap_lai": lap_lai}}
        return self.s.luu("nguoi-thu", bao_gia_id=None, expected_revision=None,
                          du_lieu=bao_gia(**({"tong_gia_tri_ghi_de": "1400000"} if ghi_de else {})), khoa="bg1-thu")

    def test_ghi_de_chi_ghi_nhat_ky_trong_giao_dich_luu(self):
        self.luu(True)
        calls = self.c.execute.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertIn("crm_gk_bao_gia_luu", calls[0].args[0])
        self.assertIn("INSERT INTO nhat_ky.su_kien", calls[1].args[0])
        self.assertIn("CRM_BAO_GIA_GHI_DE_TONG", calls[1].args[0])
        args = calls[1].args[1]
        self.assertEqual(args[0], "nguoi-thu")
        self.assertEqual(json.loads(args[2]), {"revision": 1, "tien_te": "USD", "tong_tinh_minor": "150000000", "tong_ghi_de_minor": "140000000"})
        self.assertEqual(args[-1], BG)
        self.m._tx.assert_called_once()

    def test_tong_khop_khong_ghi_su_kien_ghi_de(self):
        self.luu(False)
        self.assertEqual(self.c.execute.call_count, 1)

    def test_replay_ca_hai_duong_khong_ghi_them_nhat_ky(self):
        self.luu(True, cu={"bao_gia_id": BG, "lap_lai": True})
        self.c.execute.assert_not_called()
        self.luu(True, lap_lai=True)
        self.assertEqual(self.c.execute.call_count, 1)

    def test_route_moc_chuan_dung_phien_khong_can_csdl(self):
        h = SimpleNamespace(crm_sid=lambda: "sid", send_content=mock.Mock())
        app = SimpleNamespace(mutation_lock=nullcontext(), crm_phien=mock.Mock(return_value=(None, "nguoi-thu", None)))
        self.assertTrue(HTTP.la_route(False, "/api/crm/bao-gia/moc-chuan"))
        HTTP.dieu_huong(h, app, False, "/api/crm/bao-gia/moc-chuan", {})
        app.crm_phien.assert_called_once_with("sid")
        self.assertEqual(h.send_content.call_args.args, (200, GK.danh_muc_moc_chuan()))
        app.crm_phien.side_effect = DataError("SESSION_TOKEN", "Phiên không hợp lệ.")
        HTTP.dieu_huong(h, app, False, "/api/crm/bao-gia/moc-chuan", {})
        self.assertEqual(h.send_content.call_args.args[0], 403)


if __name__ == "__main__":
    unittest.main()
