"""BG-1a: phép tính thuần + seam service/HTTP giả, không PostgreSQL/Word/mạng/dữ liệu thật.

BG-1c (QD-20261025-01…04): dữ liệu mới là v2 (`tien_chinh = VND`): tổng/lịch/ghi đè bằng VND. Các ca ô thông minh viết cho USD là tiền chính
chạy trên dữ liệu CŨ (`tinh_cu` bỏ khóa `tien_chinh`) — đường đọc dữ liệu cũ vẫn được giữ; ca v2 nằm ở lớp `VndTienChinh` và các ca sửa."""
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


def tinh(d, **kw):
    return GK.tinh_bao_gia(GK.chuan_hoa_bao_gia(d), None, **kw)


def cu(d: dict) -> dict:
    """Dữ liệu đã lưu kiểu cũ (trước BG-1c): không có khóa tien_chinh → tiền chính = tiền tệ báo giá."""
    return {k: v for k, v in GK.chuan_hoa_bao_gia(d).items() if k != "tien_chinh"}


def tinh_cu(d):
    return GK.tinh_bao_gia(cu(d), None)


class OThongMinh(unittest.TestCase):
    def test_co_phan_tram_tinh_tien_vnd_chinh(self):
        t = tinh(bao_gia())  # 100 USD × 25.500 × 15.000 m² = 38.250.000.000 đ
        self.assertEqual((t["tien_te"], t["tien_te_don_gia"], t["tong_minor"]), ("VND", "USD", "38250000000"))
        x = t["dong"][0]
        self.assertEqual((x["ty_le"], x["so_tien_minor"], x["nguon_nhap"]), ("30", "11475000000", "TY_LE"))
        self.assertEqual(x["hien_thi_mo"], "= 11.475.000.000 VND")
        self.assertIsNone(t["vnd_tham_chieu"])
        self.assertEqual(t["usd_tham_chieu"]["tong_hien_thi"], "1.500.000,00 USD")
        self.assertEqual(t["chan_in"], [])

    def test_co_phan_tram_tinh_tien_va_vnd_du_lieu_cu(self):
        t = tinh_cu(bao_gia())
        x = t["dong"][0]
        self.assertEqual((x["ty_le"], x["so_tien"], x["so_tien_minor"], x["nguon_nhap"]), ("30", "45000000", "45000000", "TY_LE"))
        self.assertEqual(x["hien_thi_mo"], "= 450.000,00 USD · ≈ 11.475 tr VND")
        self.assertEqual(t["tong_minor"], "150000000")
        self.assertEqual(t["chan_in"], [])

    def test_khong_phan_tram_luon_la_tien_ke_ca_nho_hon_100(self):  # dữ liệu cũ: USD là tiền chính
        for v in ("30", "100", "0", "0,50"):
            with self.subTest(v=v):
                t = tinh_cu(bao_gia(v, gia={"tien_te": "USD", "tong": "100", "co_so_thue": "NET"}))
                x = t["dong"][0]
                self.assertEqual(x["nguon_nhap"], "SO_TIEN")
                self.assertEqual(x["so_tien"], str(int(v.replace(",", "")) if "," in v else int(v) * 100))
                self.assertTrue(x["hien_thi_mo"].startswith("= " + v.replace(",50", ",5") + "%"))

    def test_tien_khong_phan_tram_tinh_ty_le(self):  # dữ liệu cũ: USD là tiền chính
        t = tinh_cu(bao_gia("450.000", "1.050.000"))
        self.assertEqual([x["ty_le"] for x in t["dong"]], ["30", "70"])
        self.assertEqual(t["dong"][0]["hien_thi_mo"], "= 30% · ≈ 11.475 tr VND")
        self.assertTrue(t["tong_ty_le_khop"])
        self.assertTrue(t["tong_tien_khop"])

    def test_dau_cham_phay_kieu_viet(self):  # dữ liệu cũ: USD là tiền chính
        t = tinh_cu(bao_gia("1.500.000,50", gia={"tien_te": "USD", "tong": "1500000.50", "co_so_thue": "NET"}))
        self.assertEqual(t["dong"][0]["so_tien"], "150000050")
        self.assertEqual(t["dong"][0]["so_tien_hien_thi"], "1.500.000,50 USD")
        self.assertEqual(t["chan_in"], [])
        t = tinh_cu(bao_gia("30,5%", "69,5%"))
        self.assertEqual(t["dong"][0]["ty_le"], "30.5")
        self.assertEqual(t["dong"][0]["ty_le_hien_thi"], "30,5%")
        self.assertTrue(t["dong"][0]["hien_thi_mo"].startswith("= 457.500,00 USD"))
        self.assertTrue(t["tong_ty_le_khop"])

    def test_chuoi_sai_tra_ma_va_thong_bao_dung_dong(self):
        for v in ("abc", "1.50", "1,500.00", "1..000", "30%%", "%30", "30%5", "-1", "NaN", "1e3", "1 000", "1" * 25,
                  100, 0.5, True, None, [], {}, "100\n", "\t100", "100\x00", "100\x7f", "100\x85", " " * 101):
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

    def test_tuong_thich_truong_typed_cu_dau_cham_thap_phan(self):  # dữ liệu cũ: USD là tiền chính
        t = tinh_cu(bao_gia(lich=[{"loai": "PERCENT", "ty_le": "30.5"}, {"loai": "AMOUNT", "so_tien": "1042500.00", "tien_te": "USD"}]))
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

    def test_usd_thieu_fx_v2_khong_tinh_duoc_tong_vnd(self):
        t = tinh(bao_gia(fx=None))  # không có mặc định chung truyền vào → không đoán tỷ giá
        self.assertEqual(t["chan_in"][0]["ma"], "USD_THIEU_FX")
        self.assertEqual(t["chan_in"][0]["truong"], "fx.ty_gia")
        self.assertIsNone(t["tong_minor"])
        self.assertIsNone(t["ty_gia"])
        self.assertIn("THIEU_TONG_GIA_TRI", [x["ma"] for x in t["chan_in"]])

    def test_usd_thieu_fx_giu_nguyen_ma_chan_in(self):  # dữ liệu cũ
        t = tinh_cu(bao_gia(fx=None))
        self.assertEqual([x["ma"] for x in t["chan_in"]], ["USD_THIEU_FX"])
        self.assertEqual(t["dong"][0]["hien_thi_mo"], "= 450.000,00 USD")
        self.assertIsNone(t["vnd_tham_chieu"])

    def test_tu_tinh_ghi_de_vnd_chinh_khong_chan_in(self):
        t = tinh(bao_gia())
        self.assertEqual((t["tong_minor"], t["tong_tinh_minor"]), ("38250000000", "38250000000"))
        for sua in ({"tong_gia_tri_ghi_de": "38.000.000.000"},
                    {"gia": {"tien_te": "USD", "don_gia": "100", "dien_tich": "15000", "tong": "38000000000", "co_so_thue": "NET"}}):
            with self.subTest(sua=sua):
                t = tinh(bao_gia(**sua))
                self.assertEqual(t["tong_minor"], "38000000000")
                self.assertEqual([x["so_tien"] for x in t["dong"]], ["11400000000", "26600000000"])
                cb = next(x for x in t["canh_bao"] if x["ma"] == "TONG_LECH_DON_GIA_X_DIEN_TICH")
                self.assertEqual(cb["thong_bao"], "Khác tính toán: 38.000.000.000 VND; đơn giá × tỷ giá × diện tích = 38.250.000.000 VND.")
                self.assertEqual(t["chan_in"], [])
                self.assertEqual(t["tong_bang_chu"], "Ba mươi tám tỷ đồng")
        t = tinh(bao_gia(tong_gia_tri_ghi_de="1.400.000,50"))  # VND không có phần lẻ — không làm tròn ghi đè
        self.assertIsNone(t["tong_minor"])
        self.assertIn("TONG_KHONG_DUNG_SCALE", [x["ma"] for x in t["chan_in"]])

    def test_tu_tinh_ghi_de_moi_va_tong_cu_khong_chan_in(self):  # dữ liệu cũ
        t = tinh_cu(bao_gia())
        self.assertEqual((t["tong_minor"], t["tong_tinh_minor"]), ("150000000", "150000000"))
        for sua in ({"tong_gia_tri_ghi_de": "1400000"},
                    {"gia": {"tien_te": "USD", "don_gia": "100", "dien_tich": "15000", "tong": "1400000", "co_so_thue": "NET"}}):
            with self.subTest(sua=sua):
                t = tinh_cu(bao_gia(**sua))
                self.assertEqual(t["tong_minor"], "140000000")
                self.assertEqual([x["so_tien"] for x in t["dong"]], ["42000000", "98000000"])
                cb = next(x for x in t["canh_bao"] if x["ma"] == "TONG_LECH_DON_GIA_X_DIEN_TICH")
                self.assertEqual(cb["thong_bao"], "Khác tính toán: 1.400.000,00 USD; đơn giá × diện tích = 1.500.000,00 USD.")
                self.assertEqual(t["chan_in"], [])
                self.assertEqual(t["ly_do_chan_in"], "")

    def test_ghi_de_uu_tien_va_scale_khong_lam_tron(self):
        t = tinh(bao_gia(tong_gia_tri_ghi_de="0", lich=[{"gia_tri_nhap": "100%"}]))
        self.assertEqual(t["tong_minor"], "0")  # giá trị khai vẫn trả (0 khai báo ≠ chưa nhập) …
        self.assertIn(("TONG_NGOAI_MIEN", "tong_gia_tri_ghi_de"), [(e["ma"], e.get("truong")) for e in t["chan_in"]])  # … nhưng ngoài miền Ký
        self.assertEqual(t["ly_do_chan_chuyen"].split("\n")[:len(t["chan_in"])], [e["thong_bao"] for e in t["chan_in"]])
        for f in (tinh, tinh_cu):
            t = f(bao_gia(tong_gia_tri_ghi_de="1,001"))
            self.assertIsNone(t["tong_minor"])
            self.assertIn("TONG_KHONG_DUNG_SCALE", [x["ma"] for x in t["chan_in"]])
        t = tinh_cu(bao_gia("0,001"))
        self.assertIn("KHONG_DUNG_SCALE_TIEN_TE", t["dong"][0]["loi"])
        t = tinh(bao_gia("0,5"))  # v2: tiền đợt là VND — không có phần lẻ
        self.assertIn("KHONG_DUNG_SCALE_TIEN_TE", t["dong"][0]["loi"])

    def test_thieu_tien_te_khong_loi_may_chu(self):
        t = tinh(bao_gia("30", gia={}, fx=None))
        self.assertIn("THIEU_TIEN_TE", [x["ma"] for x in t["chan_in"]])
        self.assertIn("CHUA_CO_TIEN_TE", t["dong"][0]["loi"])

    def test_ty_le_khong_huu_han_chi_xap_xi_hien_thi(self):
        for tt in ("USD", "VND"):
            with self.subTest(tt=tt):
                t = tinh(bao_gia("500.000", "500.000", "500.000", gia={"tien_te": tt, "tong": "1500000", "co_so_thue": "NET"},
                                 **({"fx": None} if tt == "VND" else {})))
                self.assertEqual(t["chan_in"], [])
                self.assertEqual(t["ly_do_chan_chuyen"], "")
                self.assertTrue(t["tong_tien_khop"])
                self.assertTrue(t["tong_ty_le_khop"])
                self.assertEqual(t["tong_ty_le"], "100")
                self.assertEqual(t["tong_ty_le_hien_thi"], "≈ 100,00%")
                for x in t["dong"]:
                    self.assertEqual(x["loi"], [])
                    self.assertIsNone(x["ty_le"])
                    self.assertTrue(x["ty_le_xap_xi"])
                    self.assertEqual(x["ty_le_hien_thi"], "≈ 33,33%")

    def test_tien_100_tren_1500000_khong_bi_chan_khi_du_tong(self):  # dữ liệu cũ: USD là tiền chính
        for nhap in (("100", "1.499.900"), ("100", "50%", "749.900")):
            with self.subTest(nhap=nhap):
                t = tinh_cu(bao_gia(*nhap))
                self.assertEqual(t["chan_in"], [])
                self.assertEqual(t["dong"][0]["so_tien_minor"], "10000")
                self.assertEqual(t["dong"][0]["ty_le_hien_thi"], "≈ 0,01%")
                self.assertTrue(t["dong"][0]["ty_le_xap_xi"])
                self.assertEqual(t["tong_dong_minor"], "150000000")

    def test_tien_lech_chan_bang_cau_ly_do_tien(self):  # dữ liệu cũ: USD là tiền chính
        for nhap in (("500.000", "500.000", "499.999,99"), ("100", "1.499.899,99"), ("100", "50%", "749.900,01")):
            with self.subTest(nhap=nhap):
                t = tinh_cu(bao_gia(*nhap))
                self.assertEqual([x["ma"] for x in t["chan_in"]], ["TONG_TIEN_LECH"])
                self.assertEqual(t["ly_do_chan_in"], "Tổng tiền các đợt khác tổng giá trị.")
                self.assertEqual(t["ly_do_chan_chuyen"], t["ly_do_chan_in"])
                self.assertTrue(t["tong_ty_le_hien_thi"].startswith("≈ "))
                self.assertNotIn("chưa tính được%", t["tong_ty_le_hien_thi"])
                self.assertFalse(t["tong_tien_khop"])

    def test_phan_tram_nhap_giu_luat_cu_khong_lam_tron_tien(self):
        t = tinh(bao_gia("33,33%", "66,67%", gia={"tien_te": "VND", "tong": "3", "co_so_thue": "NET"}, fx=None))
        self.assertIn("KHONG_BIEU_DIEN_DUNG_SCALE", t["dong"][0]["loi"])
        self.assertIsNone(t["dong"][0]["so_tien_minor"])
        self.assertFalse(t["dong"][0]["ty_le_xap_xi"])
        self.assertEqual(t["dong"][0]["ty_le_hien_thi"], "33,33%")
        self.assertTrue(t["chan_in"])

    def test_tien_hien_thi_cung_dinh_dang_renderer_va_dung_scale(self):  # dữ liệu cũ: USD là tiền chính
        for tt, tong, nhap, hien_thi in (("USD", "1500000.50", "1.500.000,50", "1.500.000,50 USD"),
                                       ("USD", "450000", "450.000", "450.000,00 USD"),
                                       ("VND", "450000", "450.000", "450.000 VND")):
            with self.subTest(tt=tt, tong=tong):
                t = tinh_cu(bao_gia(nhap, gia={"tien_te": tt, "tong": tong, "co_so_thue": "NET"}))
                self.assertEqual(t["tong_hien_thi"], hien_thi)
                self.assertEqual(t["tong_dong_hien_thi"], hien_thi)
                self.assertEqual(t["dong"][0]["so_tien_hien_thi"], hien_thi)
                self.assertEqual(GK.R.tien_hien_thi(int(t["tong_minor"]), tt), hien_thi)

    def test_ghi_de_nhan_kieu_viet_va_loi_theo_truong(self):
        for nhap, minor in (("1.400.000", "140000000"), ("1.400.000,50", "140000050")):
            with self.subTest(nhap=nhap):
                t = tinh_cu(bao_gia(nhap, tong_gia_tri_ghi_de=nhap))
                self.assertEqual(t["tong_minor"], minor)
                self.assertEqual(t["chan_in"], [])
        for nhap in ("abc", "1.40", "1,400.00", "100%", 100, False, [], {}, "100\n", "100\x00"):
            with self.subTest(nhap=nhap):
                t = tinh(bao_gia(tong_gia_tri_ghi_de=nhap))
                self.assertIsNone(t["tong_minor"])  # Không rơi về tổng cũ/tích khi ghi đè sai.
                e = next(x for x in t["chan_in"] if x["ma"] == "TONG_GIA_TRI_GHI_DE_SAI")
                self.assertEqual(e["truong"], "tong_gia_tri_ghi_de")
                self.assertTrue(e["thong_bao"])

    def test_ghi_de_sai_scale_khong_lam_tron_va_tra_dung_truong(self):
        t = tinh(bao_gia(tong_gia_tri_ghi_de="1.400.000,501"))
        self.assertIsNone(t["tong_minor"])
        e = next(x for x in t["chan_in"] if x["ma"] == "TONG_KHONG_DUNG_SCALE")
        self.assertEqual(e["truong"], "tong_gia_tri_ghi_de")

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

    def test_xem_truoc_loi_gia_tri_tra_theo_dong_va_truong(self):
        self.m._mot.return_value = {"ok": True, "phap_nhan_id": "PN", "phap_nhan": "PN_THU", "phap_nhan_ten": "Pháp nhân thử",
                                   "loai_hinh": "KCN", "loai_hinh_ten": "Thuê đất khu công nghiệp"}
        kq = self.s.xem_truoc("nguoi-thu", du_lieu=bao_gia(100, "70%", tong_gia_tri_ghi_de="sai"))
        self.assertEqual(kq["tinh"]["dong"][0]["loi_chi_tiet"][0]["truong"], "lich.0.gia_tri_nhap")
        self.assertIn("TONG_GIA_TRI_GHI_DE_SAI", [x["ma"] for x in kq["tinh"]["chan_in"]])
        self.c.execute.assert_not_called()

    def test_http_chan_chuyen_409_cung_ly_do_may_chu(self):
        body = {"bao_gia_id": BG, "expected_revision": 1, "mau_phien_ban_id": LOAI, "khoa": "chuyen-http-thu"}
        h = SimpleNamespace(crm_sid=lambda: "sid", json_body=lambda: body, send_content=mock.Mock())
        app = SimpleNamespace(mutation_lock=nullcontext(), crm_phien=lambda sid: (None, "nguoi-thu", None),
                              _crm_db=lambda f, *a, **kw: f(*a, **kw))
        self.s._tra = mock.Mock(return_value=None)
        d = GK.chuan_hoa_bao_gia(bao_gia("30%", "60%"))
        self.s._bao_gia = mock.Mock(return_value={"du_lieu": d, "loai_hinh_id": LOAI})
        with mock.patch.object(HTTP, "dich_vu_gk", return_value=self.s):
            HTTP.dieu_huong(h, app, True, "/api/crm/bao-gia/chuyen", {})
        self.assertEqual(h.send_content.call_args.args, (409, {"error": "CRM_GK_CHAN_CHUYEN", "message": "Tổng % = 90, thiếu 10"}))
        self.c.execute.assert_not_called()

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
                          du_lieu=bao_gia(**({"tong_gia_tri_ghi_de": "38.000.000.000"} if ghi_de else {})), khoa="bg1-thu")

    def test_ghi_de_chi_ghi_nhat_ky_trong_giao_dich_luu(self):
        self.luu(True)
        calls = self.c.execute.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertIn("crm_gk_bao_gia_luu", calls[0].args[0])
        self.assertIn("INSERT INTO nhat_ky.su_kien", calls[1].args[0])
        self.assertIn("CRM_BAO_GIA_GHI_DE_TONG", calls[1].args[0])
        args = calls[1].args[1]
        self.assertEqual(args[0], "nguoi-thu")
        self.assertEqual(json.loads(args[2]), {"revision": 1, "tien_te": "VND", "tong_tinh_minor": "38250000000", "tong_ghi_de_minor": "38000000000"})
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


# ====================================================================== BG-1c — VND là tiền chính (thuần, không PostgreSQL)
def bao_gia_moi(*nhap, **sua):
    """Báo giá USD theo ví dụ của Anh: 100 USD/m² × 15.000 m², chưa nhập tỷ giá (máy chủ lấy mặc định chung)."""
    d = bao_gia(*nhap, **sua)
    if "fx" not in sua:
        d["fx"] = None
    return d


MAC_DINH = {"ty_gia": "26000", "ngay": None}


class VndTienChinh(unittest.TestCase):
    def test_vi_du_cua_anh_100_usd_26000_15000_m2(self):
        d = GK.chuan_hoa_bao_gia(bao_gia_moi(), fx_mac_dinh=MAC_DINH, hom_nay="2026-10-25")
        self.assertEqual((d["tien_chinh"], d["phien_ban_du_lieu"]), ("VND", "crm-bao-gia/v2"))
        self.assertEqual(d["fx"], {"cap": "USD/VND", "ty_gia": "26000", "ngay": "2026-10-25", "nguon": "MAC_DINH"})
        t = GK.tinh_bao_gia(d, None)
        self.assertEqual((t["tien_te"], t["tien_te_don_gia"], t["scale"], t["quy_uoc"]), ("VND", "USD", 0, "VND_CHINH"))
        self.assertEqual((t["tong_minor"], t["tong_tinh_minor"]), ("39000000000", "39000000000"))
        self.assertEqual(t["tong_hien_thi"], "39.000.000.000 VND")
        self.assertEqual(t["tong_bang_chu"], "Ba mươi chín tỷ đồng")
        self.assertEqual(t["phep_tinh"], "100 USD × 26.000 × 15.000 m² = 39.000.000.000 đ")
        self.assertFalse(t["tong_lam_tron"])
        self.assertEqual(t["ty_gia"], {"gia_tri": "26000", "hien_thi": "26.000", "khoa": False, "nguon": "MAC_DINH", "ngay": "2026-10-25",
                                       "ngay_hien_thi": "25/10/2026"})
        self.assertEqual(t["usd_tham_chieu"], {"tong_minor": "150000000", "tong": "1500000.00", "tong_hien_thi": "1.500.000,00 USD", "lam_tron": False,
                                               "cong_thuc": "Đơn giá × diện tích (USD, chỉ tham chiếu)"})
        self.assertEqual([x["so_tien_minor"] for x in t["dong"]], ["11700000000", "27300000000"])  # đợt % = % × Tổng VND
        self.assertEqual([x["hien_thi_mo"] for x in t["dong"]], ["= 11.700.000.000 VND", "= 27.300.000.000 VND"])
        self.assertEqual((t["tong_dong_hien_thi"], t["tong_tien_khop"], t["tong_ty_le_khop"]), ("39.000.000.000 VND", True, True))
        self.assertEqual(t["chan_in"], [])
        self.assertEqual(t["ly_do_chan_in"], "")

    def test_ty_gia_nhap_tay_ghi_de_mac_dinh_va_doi_ty_gia_doi_tong(self):
        for tg, tong in (("25500", "38250000000"), ("26000", "39000000000"), ("25999.5", "38999250000")):
            with self.subTest(tg=tg):
                d = GK.chuan_hoa_bao_gia(bao_gia_moi(fx={"cap": "USD/VND", "ty_gia": tg}), fx_mac_dinh=MAC_DINH, hom_nay="2026-10-25")
                self.assertEqual(d["fx"], {"cap": "USD/VND", "ty_gia": tg, "ngay": "2026-10-25"})  # ngày trống → hôm nay của máy chủ
                t = GK.tinh_bao_gia(d, None)
                self.assertEqual(t["tong_minor"], tong)
                self.assertEqual(t["ty_gia"]["nguon"], "NHAP")
                self.assertEqual(t["usd_tham_chieu"]["tong_minor"], "150000000")  # USD tham chiếu không đổi theo tỷ giá

    def test_lam_tron_den_dong_nua_len(self):
        f = GK.lam_tron_nua_len
        from fractions import Fraction as F
        self.assertEqual([f(F(5, 2)), f(F(7, 2)), f(F(249, 100)), f(F(251, 100)), f(F(0)), f(F(1, 2)), f(F(3))], [3, 4, 2, 3, 0, 1, 3])
        with self.assertRaises(ValueError):
            f(F(-1, 2))
        for don_gia, dien_tich, tong, tron in (("2.5", "1", "3", True), ("1.5", "3", "5", True), ("1.4", "1", "1", True), ("1234567", "100", "123456700", False)):
            with self.subTest(don_gia=don_gia, dien_tich=dien_tich):
                t = tinh(bao_gia_moi(gia={"tien_te": "VND", "don_gia": don_gia, "dien_tich": dien_tich, "co_so_thue": "NET"}, lich=[{"gia_tri_nhap": "100%"}]))
                self.assertEqual((t["tong_minor"], t["tong_lam_tron"]), (tong, tron))
                self.assertEqual(t["phep_tinh"].endswith("(đã làm tròn đến đồng)"), tron)
        # USD: 1,25 USD × 25.000,5 × 1 m² = 31.250,625 đ → 31.251 đ; USD tham chiếu 1,25 USD (không làm tròn)
        t = tinh(bao_gia_moi(gia={"tien_te": "USD", "don_gia": "1.25", "dien_tich": "1", "co_so_thue": "NET"}, fx={"cap": "USD/VND", "ty_gia": "25000.5",
                                                                                                                  "ngay": "2026-10-25"},
                             lich=[{"gia_tri_nhap": "31.251"}]))
        self.assertEqual(t["tong_minor"], "31251")
        self.assertEqual(t["phep_tinh"], "1,25 USD × 25.000,5 × 1 m² = 31.251 đ (đã làm tròn đến đồng)")
        self.assertEqual(t["usd_tham_chieu"]["tong_hien_thi"], "1,25 USD")
        self.assertEqual(t["chan_in"], [])
        # USD tham chiếu làm tròn đến cent (nửa lên): 0,125 × 1 → 0,13
        t = tinh(bao_gia_moi(gia={"tien_te": "USD", "don_gia": "0.125", "dien_tich": "1", "co_so_thue": "NET"}, fx={"cap": "USD/VND", "ty_gia": "26000",
                                                                                                                   "ngay": "2026-10-25"}))
        self.assertEqual((t["usd_tham_chieu"]["tong"], t["usd_tham_chieu"]["lam_tron"]), ("0.13", True))

    def test_bao_gia_vnd_ty_gia_khoa_bang_1(self):
        g = {"tien_te": "VND", "don_gia": "12000000", "dien_tich": "100", "co_so_thue": "NET"}
        for fx in (None, {}, {"ty_gia": "1"}, {"cap": "USD/VND", "ty_gia": "1.000", "ngay": "2026-10-25"}):
            with self.subTest(fx=fx):
                d = GK.chuan_hoa_bao_gia(bao_gia(gia=g, fx=fx), fx_mac_dinh=MAC_DINH, hom_nay="2026-10-25")
                self.assertIsNone(d["fx"])  # VND không nhận tỷ giá mặc định
                t = GK.tinh_bao_gia(d, None)
                self.assertEqual(t["ty_gia"], {"gia_tri": "1", "hien_thi": "1", "khoa": True, "nguon": "CO_DINH_VND", "ngay": None, "ngay_hien_thi": None})
                self.assertEqual((t["tong_minor"], t["phep_tinh"]), ("1200000000", "12.000.000 đ × 100 m² = 1.200.000.000 đ"))
                self.assertIsNone(t["usd_tham_chieu"])
                self.assertEqual(t["chan_in"], [])
        t = tinh(bao_gia(gia=g, fx={"cap": "USD/VND", "ty_gia": "25500", "ngay": "2026-10-24"}))
        e = next(x for x in t["chan_in"] if x["ma"] == "VND_TY_GIA_KHAC_1")
        self.assertEqual(e["truong"], "fx.ty_gia")
        self.assertIn("tỷ giá cố định bằng 1", t["ly_do_chan_in"])
        self.assertEqual(t["tong_minor"], "1200000000")  # lỗi theo trường, không đổi phép tính

    def test_lich_tien_va_ghi_de_bang_vnd(self):
        t = GK.tinh_bao_gia(GK.chuan_hoa_bao_gia(bao_gia_moi("11.700.000.000", "27.300.000.000"), fx_mac_dinh=MAC_DINH), None)
        self.assertEqual([x["ty_le"] for x in t["dong"]], ["30", "70"])
        self.assertEqual(t["dong"][0]["hien_thi_mo"], "= 30%")
        self.assertTrue(t["tong_tien_khop"])
        t = tinh(bao_gia(lich=[{"loai": "AMOUNT", "so_tien": "1500000", "tien_te": "USD"}]))  # đợt ghi USD: không cộng vào lịch VND
        self.assertIn("KHAC_TIEN_TE", t["dong"][0]["loi"])
        self.assertIn("tiền chính", t["dong"][0]["loi_chi_tiet"][0]["thong_bao"])
        d = GK.chuan_hoa_bao_gia(bao_gia_moi(tong_gia_tri_ghi_de="39.500.000.000"), fx_mac_dinh=MAC_DINH)
        t = GK.tinh_bao_gia(d, None)
        self.assertEqual((t["tong_minor"], t["tong_tinh_minor"]), ("39500000000", "39000000000"))
        self.assertEqual(t["tong_bang_chu"], "Ba mươi chín tỷ năm trăm triệu đồng")
        self.assertIn("TONG_LECH_DON_GIA_X_DIEN_TICH", [x["ma"] for x in t["canh_bao"]])
        self.assertEqual(t["chan_in"], [])  # ghi đè chỉ cảnh báo ở In/Chuyển; chặn ở Ký (M0030, QD-20261024-02)

    def test_du_lieu_cu_doc_nguyen_nghia_cu(self):
        t = tinh_cu(bao_gia())
        self.assertEqual((t["tien_te"], t["tien_te_don_gia"], t["quy_uoc"], t["tong_minor"]), ("USD", "USD", "CU_TIEN_TE_BAO_GIA", "150000000"))
        self.assertEqual(t["tong_bang_chu"], "Một triệu năm trăm nghìn đô la Mỹ")
        self.assertIsNone(t["usd_tham_chieu"])
        self.assertEqual(t["vnd_tham_chieu"]["tong"], "38250000000")
        q = GK.quy_uoc_bao_gia(cu(bao_gia()))
        self.assertEqual(q["ma"], "CU_TIEN_TE_BAO_GIA")
        self.assertIn("quy ước cũ", q["ghi_chu"])
        self.assertEqual(GK.quy_uoc_bao_gia(GK.chuan_hoa_bao_gia(bao_gia())), {"ma": "VND_CHINH", "ghi_chu": None})

    def test_khong_nhan_tien_chinh_khac_vnd_tu_trinh_duyet(self):
        self.assertEqual(GK.chuan_hoa_bao_gia(bao_gia(tien_chinh="VND"))["tien_chinh"], "VND")
        with self.assertRaises(DataError):
            GK.chuan_hoa_bao_gia(bao_gia(tien_chinh="USD"))


class BangChu(unittest.TestCase):
    """Bộ đọc số bằng chữ DÙNG LẠI `nguon/crm_docx.bang_chu` (cùng bộ của mẫu hợp đồng định dạng CHU) — không có bộ thứ hai."""

    def test_cac_ca_doc_so(self):
        for n, chu in ((0, "Không đồng"), (1, "Một đồng"), (10, "Mười đồng"), (11, "Mười một đồng"), (14, "Mười bốn đồng"),
                       (15, "Mười lăm đồng"), (21, "Hai mươi mốt đồng"), (24, "Hai mươi tư đồng"), (25, "Hai mươi lăm đồng"),
                       (55, "Năm mươi lăm đồng"), (101, "Một trăm lẻ một đồng"), (105, "Một trăm lẻ năm đồng"), (115, "Một trăm mười lăm đồng"),
                       (1_000, "Một nghìn đồng"), (2_005_000, "Hai triệu không trăm lẻ năm nghìn đồng"),
                       (1_000_005, "Một triệu không trăm lẻ năm đồng"), (1_500_000_000, "Một tỷ năm trăm triệu đồng"),
                       (39_000_000_000, "Ba mươi chín tỷ đồng"), (2_000_000_001, "Hai tỷ không trăm lẻ một đồng"),
                       (1_500_000_000_000, "Một nghìn năm trăm tỷ đồng"), (31_251, "Ba mươi mốt nghìn hai trăm năm mươi mốt đồng")):
            with self.subTest(n=n):
                self.assertEqual(GK.R.bang_chu(n, "VND"), chu)

    def test_tong_bang_chu_tu_phep_tinh(self):
        t = tinh(bao_gia_moi(gia={"tien_te": "VND", "don_gia": "15000000", "dien_tich": "100", "co_so_thue": "NET"}))
        self.assertEqual(t["tong_bang_chu"], "Một tỷ năm trăm triệu đồng")
        t = tinh(bao_gia_moi(gia={"tien_te": "VND", "co_so_thue": "NET"}))
        self.assertIsNone(t["tong_bang_chu"])  # chưa có tổng → không bịa chữ


class HaiBuoc(unittest.TestCase):
    """QD-20261025-03: In sơ bộ chỉ cần phần giá + lịch; khách + phí là điều kiện Chuyển."""

    def test_in_so_bo_khong_can_khach_chuyen_can_khach(self):
        t = GK.tinh_bao_gia(GK.chuan_hoa_bao_gia(bao_gia_moi(khach={}), fx_mac_dinh=MAC_DINH), None)
        self.assertEqual(t["chan_in"], [])
        self.assertEqual(t["ly_do_chan_in"], "")
        self.assertEqual([x["ma"] for x in t["chan_chuyen"]], ["THIEU_KHACH"])
        self.assertEqual(t["ly_do_chan_chuyen"], "Chưa có thông tin khách hàng.")
        self.assertEqual(t["chan_chuyen"][0]["truong"], "khach")

    def test_phi_chi_bat_buoc_khi_profile_co_phi(self):
        d = GK.chuan_hoa_bao_gia(bao_gia_moi(), fx_mac_dinh=MAC_DINH)
        self.assertEqual(GK.tinh_bao_gia(d, None, co_phi=False)["ly_do_chan_chuyen"], "")
        t = GK.tinh_bao_gia(d, None, co_phi=True)
        self.assertEqual(t["chan_in"], [])
        self.assertEqual(t["ly_do_chan_chuyen"], "Chưa nhập phí quản lý/bảo trì.")
        self.assertEqual(t["chan_chuyen"][0]["truong"], "phi_bao_tri.gia_tri")
        d = GK.chuan_hoa_bao_gia(bao_gia_moi(khach={}, phi_bao_tri={"gia_tri": "20000000", "tien_te": "VND"}), fx_mac_dinh=MAC_DINH)
        self.assertEqual(GK.tinh_bao_gia(d, None, co_phi=True)["ly_do_chan_chuyen"], "Chưa có thông tin khách hàng.")

    def test_profile_khai_phi(self):
        self.assertTrue(GK.loai_hinh_co_phi({"bao_gia": {"truong_ap_dung": ["don_gia", "phi_bao_tri"]}}))
        for ch in (None, {}, {"bao_gia": {}}, {"bao_gia": {"truong_ap_dung": ["don_gia"]}}, {"bao_gia": {"truong_ap_dung": "phi_bao_tri"}},
                   {"loai_hop_dong": "BAN_NHA"}, "x"):
            with self.subTest(ch=ch):
                self.assertFalse(GK.loai_hinh_co_phi(ch))  # không suy từ loại hợp đồng/tên

    def test_loi_gia_hoac_lich_van_chan_ca_hai(self):
        t = GK.tinh_bao_gia(GK.chuan_hoa_bao_gia(bao_gia_moi("30%", "60%", khach={}), fx_mac_dinh=MAC_DINH), None)
        self.assertEqual(t["ly_do_chan_in"], "Tổng % = 90, thiếu 10")
        self.assertEqual(t["ly_do_chan_chuyen"], "Tổng % = 90, thiếu 10\nChưa có thông tin khách hàng.")


class SeamBg1c(unittest.TestCase):
    """Seam service không PostgreSQL: tỷ giá mặc định đọc trong giao dịch, Lưu giữ tỷ giá đã dùng, chặn Chuyển thiếu khách/phí, In sơ bộ, cấu hình."""

    def setUp(self):
        self.c = mock.MagicMock()
        self.m = SimpleNamespace(root=".", danh_tinh=mock.Mock(return_value={"id": "U1", "dang_nhap": "nguoi-thu", "vai_tro": "KE_TOAN"}),
                                 _tx=mock.Mock(side_effect=lambda *a, **k: nullcontext(self.c)), _mot=mock.Mock(), _nhieu=mock.Mock(return_value=[]),
                                 hom_nay=lambda: date(2026, 10, 25), conn_tin_cay=object())
        self.s = GK.CrmGiaoKetK2(self.m)

    LOAI_ROW = {"ok": True, "phap_nhan_id": "PN", "phap_nhan": "PN_THU", "phap_nhan_ten": "Pháp nhân thử", "loai_hinh": "KCN",
                "loai_hinh_ten": "Thuê đất khu công nghiệp", "cau_hinh": {}}

    def test_xem_truoc_lay_ty_gia_mac_dinh_cau_hinh(self):
        self.m._mot.side_effect = [self.LOAI_ROW, {"id": "CH1", "gia_tri": {"cap": "USD/VND", "ty_gia": "25000"}, "nguoi_duyet": "kt-thu",
                                                   "ngay": "2026-10-20"}]
        kq = self.s.xem_truoc("nguoi-thu", du_lieu=bao_gia_moi())
        self.assertEqual(kq["tinh"]["tong_minor"], "37500000000")
        self.assertEqual(kq["tinh"]["ty_gia"]["nguon"], "MAC_DINH")
        self.assertEqual(kq["fx"], {"cap": "USD/VND", "ty_gia": "25000", "ngay": "2026-10-20", "nguon": "MAC_DINH"})
        self.assertEqual(kq["fx_ngay_hien_thi"], "20/10/2026")
        sql = self.m._mot.call_args_list[1].args[1]
        self.assertIn("master.cau_hinh", sql)
        self.assertIn("phap_nhan_id IS NULL", sql)
        self.assertEqual(self.m._mot.call_args_list[1].args[2], ("crm.bao_gia.ty_gia_usd_mac_dinh",))
        self.c.execute.assert_not_called()  # chỉ đọc

    def test_xem_truoc_chua_co_cau_hinh_dung_26000_va_vnd_khong_doc(self):
        self.m._mot.side_effect = [self.LOAI_ROW, None]
        kq = self.s.xem_truoc("nguoi-thu", du_lieu=bao_gia_moi())
        self.assertEqual((kq["tinh"]["tong_minor"], kq["tinh"]["ty_gia"]["gia_tri"]), ("39000000000", "26000"))
        self.assertEqual(kq["fx"]["ngay"], "2026-10-25")
        self.m._mot.side_effect = [self.LOAI_ROW]
        kq = self.s.xem_truoc("nguoi-thu", du_lieu=bao_gia_moi(gia={"tien_te": "VND", "don_gia": "1000", "dien_tich": "10", "co_so_thue": "NET"}))
        self.assertEqual(kq["tinh"]["tong_minor"], "10000")  # VND: không đọc cấu hình tỷ giá

    def test_xem_truoc_co_phi_theo_profile(self):
        self.m._mot.side_effect = [{**self.LOAI_ROW, "cau_hinh": {"bao_gia": {"truong_ap_dung": ["phi_bao_tri"]}}}]
        kq = self.s.xem_truoc("nguoi-thu", du_lieu=bao_gia())
        self.assertTrue(kq["co_phi"])
        self.assertEqual(kq["tinh"]["ly_do_chan_chuyen"], "Chưa nhập phí quản lý/bảo trì.")
        self.assertEqual(kq["tinh"]["ly_do_chan_in"], "")

    def luu(self, du_lieu, cau_hinh_row):
        kq = {"bao_gia_id": BG, "revision": 1, "so_bao_gia": "BG-THU", "trang_thai": "NHAP"}
        self.s._tra = mock.Mock(return_value=None)
        self.s._trung_don_vi = mock.Mock(return_value=[])
        self.m._mot.side_effect = [{"phap_nhan_id": "PN", "cau_hinh": {}}, cau_hinh_row]  # loại hình rồi cấu hình tỷ giá (cùng giao dịch)
        self.c.execute.reset_mock()
        self.c.execute.return_value.fetchone.return_value = {"r": {"ket_qua": kq, "lap_lai": False}}
        self.s.luu("nguoi-thu", bao_gia_id=None, expected_revision=None, du_lieu=du_lieu, khoa="bg1c-thu")
        args = self.c.execute.call_args_list[0].args[1]
        return json.loads(args[7]), json.loads(args[8]), self.s._tra.call_args.args[4]

    def test_luu_ghi_ty_gia_mac_dinh_vao_bao_gia_va_h_khong_phu_thuoc_cau_hinh(self):
        d1, t1, h1 = self.luu(bao_gia_moi(), {"id": "CH1", "gia_tri": {"ty_gia": "25000"}, "nguoi_duyet": "kt", "ngay": "2026-10-20"})
        self.assertEqual(d1["fx"]["ty_gia"], "25000")
        self.assertEqual((d1["fx"]["nguon"], d1["fx"]["nguoi_nhap"], d1["fx"]["nhap_ngay"]), ("MAC_DINH", "nguoi-thu", "2026-10-25"))
        self.assertEqual((t1["tien_te"], t1["tong_minor"]), ("VND", "37500000000"))
        self.assertEqual(d1["tien_chinh"], "VND")
        d2, t2, h2 = self.luu(bao_gia_moi(), None)  # cấu hình đổi/chưa có → báo giá MỚI nhận 26.000; H của cùng yêu cầu không đổi
        self.assertEqual((d2["fx"]["ty_gia"], t2["tong_minor"]), ("26000", "39000000000"))
        self.assertEqual(h1, h2)

    def test_luu_bao_gia_da_co_khong_gui_ty_gia_giu_ty_gia_da_luu(self):
        kq = {"bao_gia_id": BG, "revision": 2, "so_bao_gia": "BG-THU", "trang_thai": "NHAP"}
        da_luu = GK.chuan_hoa_bao_gia(bao_gia_moi(), fx_mac_dinh={"ty_gia": "25000", "ngay": "2026-10-20"})
        da_luu["fx"].update({"nguoi_nhap": "nguoi-truoc", "nhap_ngay": "2026-10-20"})
        self.s._tra = mock.Mock(return_value=None)
        self.s._trung_don_vi = mock.Mock(return_value=[])
        self.s._bao_gia = mock.Mock(return_value={"du_lieu": da_luu})
        self.m._mot.side_effect = [{"phap_nhan_id": "PN", "cau_hinh": {}}]  # KHÔNG đọc cấu hình tỷ giá
        self.c.execute.return_value.fetchone.return_value = {"r": {"ket_qua": kq, "lap_lai": False}}
        self.s.luu("nguoi-thu", bao_gia_id=BG, expected_revision=1, du_lieu=bao_gia_moi(), khoa="bg1c-sua")
        d = json.loads(self.c.execute.call_args_list[0].args[1][7])
        self.assertEqual(d["fx"], {**da_luu["fx"]})  # cùng tỷ giá/ngày/nguồn → giữ cả người nhập/ngày nhập
        self.assertEqual(json.loads(self.c.execute.call_args_list[0].args[1][8])["tong_minor"], "37500000000")
        self.assertEqual(self.m._mot.call_count, 1)

    def test_luu_bao_gia_vnd_tu_choi_ty_gia_khac_1_truoc_giao_dich(self):
        with self.assertRaises(DataError) as cm:
            self.s.luu("nguoi-thu", bao_gia_id=None, expected_revision=None, khoa="bg1c-vnd",
                       du_lieu=bao_gia(gia={"tien_te": "VND", "tong": "1000", "co_so_thue": "NET"}))
        self.assertEqual(cm.exception.code, "CRM_GK_FX_SAI")
        self.m._tx.assert_not_called()

    def chuyen(self, du_lieu, cau_hinh, dm=()):
        self.s._tra = mock.Mock(return_value=None)
        d = GK.chuan_hoa_bao_gia(du_lieu, fx_mac_dinh=MAC_DINH, hom_nay="2026-10-25")
        self.s._bao_gia = mock.Mock(return_value={"phap_nhan_id": "PN", "loai_hinh_id": LOAI, "du_lieu": d, "tinh": {}})
        self.m._mot.side_effect = None
        self.m._mot.return_value = {"cau_hinh": cau_hinh}
        self.m._nhieu.return_value = list(dm)
        self.c.execute.reset_mock()
        self.c.execute.return_value.fetchone.side_effect = [{"r": {"danh_muc_ref": "DM", "danh_muc_rev": 1}},
                                                            {"r": {"ket_qua": {"soan_id": "SOAN"}, "lap_lai": False}}]
        return self.s.chuyen("nguoi-thu", bao_gia_id=BG, expected_revision=1, mau_phien_ban_id=DU_AN, khoa="bg1c-chuyen")

    def test_chuyen_chan_thieu_khach_va_thieu_phi(self):
        for du_lieu, cau_hinh, ly_do in ((bao_gia_moi(khach={}), {}, "Chưa có thông tin khách hàng."),
                                         (bao_gia_moi(), {"bao_gia": {"truong_ap_dung": ["phi_bao_tri"]}}, "Chưa nhập phí quản lý/bảo trì.")):
            with self.subTest(ly_do=ly_do):
                with self.assertRaises(DataError) as cm:
                    self.chuyen(du_lieu, cau_hinh)
                self.assertEqual((cm.exception.code, str(cm.exception)), ("CRM_GK_CHAN_CHUYEN", ly_do))
                self.c.execute.assert_not_called()

    def test_chuyen_truyen_gia_tri_hop_dong_vnd_kem_usd_tham_chieu_va_ty_gia_khi_mau_co_cho(self):
        ch = {"kiem_tong": {"truong": "gia_tri_hop_dong", "co_so": "TIEN_THUE_DAT_CHUA_VAT"}}
        dm = [{"khoa": "gia_tri_hop_dong", "kieu": "tien"}, {"khoa": "gia_tri_usd_tham_chieu", "kieu": "tien"}, {"khoa": "ty_gia_usd_vnd", "kieu": "so"}]
        self.assertEqual(self.chuyen(bao_gia_moi(), ch, dm), {"soan_id": "SOAN", "lap_lai": False})
        du_lieu = json.loads(self.c.execute.call_args_list[-1].args[1][5])
        self.assertEqual(du_lieu["gia_tri_truong"], {"gia_tri_hop_dong": {"so_tien": "39000000000", "tien_te": "VND"},
                                                     "gia_tri_usd_tham_chieu": {"so_tien": "1500000.00", "tien_te": "USD"}, "ty_gia_usd_vnd": "26000"})
        self.assertEqual(du_lieu["bao_gia"]["tien_chinh"], "VND")
        for k, v in du_lieu["gia_tri_truong"].items():  # cùng validator typed của soạn
            self.assertEqual(GK.chuan_hoa_truong({"gia_tri_hop_dong": "tien", "gia_tri_usd_tham_chieu": "tien", "ty_gia_usd_vnd": "so"}[k], v), v)
        self.chuyen(bao_gia_moi(), ch, dm[:1])  # mẫu không có chỗ USD/tỷ giá → chỉ giá trị VND
        du_lieu = json.loads(self.c.execute.call_args_list[-1].args[1][5])
        self.assertEqual(list(du_lieu["gia_tri_truong"]), ["gia_tri_hop_dong"])

    def test_in_so_bo_khi_chua_co_khach(self):
        d = GK.chuan_hoa_bao_gia(bao_gia_moi(khach={}), fx_mac_dinh=MAC_DINH, hom_nay="2026-10-25")
        d["fx"].update({"nguoi_nhap": "nguoi-thu", "nhap_ngay": "2026-10-25"})
        cu_tinh = {"chan_in": [{"ma": "THIEU_KHACH", "thong_bao": "Chưa nhập khách hàng."}]}  # kết quả lưu từ luật cũ: không được dùng
        self.s._tra = mock.Mock(return_value=None)
        self.s._bao_gia = mock.Mock(return_value={"id": BG, "revision_hien_hanh": 1, "trang_thai": "NHAP", "loai_hinh_id": LOAI, "du_an_id": None,
                                                  "du_lieu": d, "tinh": cu_tinh, "g7": None, "khach_ten": None, "so_bao_gia": "BG-THU",
                                                  "ngay": "2026-10-25", "tao_boi": "nguoi-thu", "du_lieu_sha256": "0" * 64})
        self.m._nhieu.return_value = [{"noi_dung": "Điều khoản DEMO."}]
        self.s._dat_lan = mock.Mock(side_effect=lambda dt, kh: kh)
        kh = self.s.chuan_bi_in("nguoi-thu", bao_gia_id=BG, expected_revision=1, khoa="bg1c-in")
        nd = dict(kh["nd"]["thong_tin"])
        self.assertEqual(kh["nd"]["khach"], "Quý khách hàng")
        self.assertEqual(nd["Tổng giá trị"], "39.000.000.000 VND")
        self.assertEqual(nd["Bằng chữ"], "Ba mươi chín tỷ đồng")
        self.assertEqual((nd["Đơn giá"], nd["Diện tích"], nd["Tỷ giá USD/VND"]), ("100 USD", "15.000 m²", "26.000"))
        self.assertEqual(nd["Giá trị tham chiếu (USD)"], "1.500.000,00 USD")
        self.assertIn("Báo giá sơ bộ", nd["Loại bản in"])
        self.assertEqual(kh["nd"]["lich"][0][1], "30% — 11.700.000.000 VND")
        self.assertIn("Giá trị thanh toán tính bằng VND", kh["nd"]["fx_cau"])
        self.assertIn(("Ba mươi chín tỷ đồng", 1), kh["mong_doi"])

    def test_cau_hinh_doc_va_quyen(self):
        self.m._mot.side_effect = [{"doc": True, "sua": False}, None]
        kq = self.s.ty_gia_mac_dinh("nguoi-thu")
        self.assertEqual((kq["ty_gia"], kq["hien_thi"], kq["nguon"], kq["duoc_sua"], kq["khoa"]),
                         ("26000", "26.000", "PHAN_MEM", False, "crm.bao_gia.ty_gia_usd_mac_dinh"))
        self.assertEqual(self.m._mot.call_args_list[0].args[2], (["KE_TOAN", "KE_TOAN_TRUONG"],))
        self.m._mot.side_effect = [{"doc": False, "sua": False}]
        with self.assertRaises(DataError) as cm:
            self.s.ty_gia_mac_dinh("nguoi-thu")
        self.assertEqual(cm.exception.code, "CRM_G_KHONG_CO_QUYEN")

    def test_cau_hinh_sua_chi_ke_toan_co_nhat_ky(self):
        self.m._mot.side_effect = [{"doc": True, "sua": False}]
        with self.assertRaises(DataError) as cm:
            self.s.sua_ty_gia_mac_dinh("nguoi-thu", ty_gia="25.500")
        self.assertEqual(cm.exception.code, "CRM_G_KHONG_CO_QUYEN")
        self.c.execute.assert_not_called()
        moi = {"id": "CH2", "gia_tri": {"cap": "USD/VND", "ty_gia": "25500"}, "nguoi_duyet": "nguoi-thu", "ngay": "2026-10-25"}
        self.m._mot.side_effect = [{"doc": True, "sua": True}, {"id": "CH1", "gia_tri": {"ty_gia": "26000"}, "nguoi_duyet": "kt", "ngay": "2026-10-01"}, moi]
        self.c.execute.return_value.fetchone.return_value = {"id": "CH2"}
        kq = self.s.sua_ty_gia_mac_dinh("nguoi-thu", ty_gia="25.500", ly_do="Tỷ giá tháng 11 (DEMO)")
        self.assertEqual((kq["ty_gia"], kq["nguon"], kq["da_doi"]), ("25500", "CAU_HINH", True))
        sql = [x.args[0] for x in self.c.execute.call_args_list]
        self.assertEqual(len(sql), 4)
        self.assertIn("pg_advisory_xact_lock", sql[0])
        self.assertIn("UPDATE master.cau_hinh SET valid_to = now()", sql[1])
        self.assertIn("INSERT INTO master.cau_hinh", sql[2])
        self.assertIn("INSERT INTO nhat_ky.su_kien", sql[3])
        nk = self.c.execute.call_args_list[3].args[1]
        self.assertEqual((nk[0], json.loads(nk[2]), json.loads(nk[3])["ty_gia"], nk[4]),
                         ("nguoi-thu", {"ty_gia": "26000", "nguon": "CAU_HINH"}, "25500", "Tỷ giá tháng 11 (DEMO)"))
        self.assertEqual(json.loads(self.c.execute.call_args_list[2].args[1][1]), {"cap": "USD/VND", "ty_gia": "25500"})

    def test_cau_hinh_cung_gia_tri_khong_ghi_va_dau_vao_sai(self):
        row = {"id": "CH1", "gia_tri": {"ty_gia": "26000"}, "nguoi_duyet": "kt", "ngay": "2026-10-01"}
        self.m._mot.side_effect = [{"doc": True, "sua": True}, row, row]
        kq = self.s.sua_ty_gia_mac_dinh("nguoi-thu", ty_gia="26.000")
        self.assertFalse(kq["da_doi"])
        self.assertEqual(len(self.c.execute.call_args_list), 1)  # chỉ khóa, không ghi
        self.c.execute.reset_mock()
        for v in ("0", "abc", "26000%", "-1", None, 26000, "26,000.5"):
            with self.subTest(v=v):
                with self.assertRaises(DataError) as cm:
                    self.s.sua_ty_gia_mac_dinh("nguoi-thu", ty_gia=v)
                self.assertEqual(cm.exception.code, "CRM_GK_FX_SAI")
        self.c.execute.assert_not_called()

    def test_route_ty_gia_mac_dinh(self):
        self.assertTrue(HTTP.la_route(False, "/api/crm/bao-gia/ty-gia-mac-dinh"))
        self.assertEqual(HTTP.TRUONG_GK["bao-gia/ty-gia-mac-dinh"], {"ty_gia", "ly_do"})
        h = SimpleNamespace(crm_sid=lambda: "sid", send_content=mock.Mock())
        app = SimpleNamespace(mutation_lock=nullcontext(), crm_phien=lambda sid: (None, "nguoi-thu", None), _crm_db=lambda f, *a, **kw: f(*a, **kw))
        self.s.ty_gia_mac_dinh = mock.Mock(return_value={"ty_gia": "26000"})
        self.s.sua_ty_gia_mac_dinh = mock.Mock(return_value={"ty_gia": "25500"})
        with mock.patch.object(HTTP, "dich_vu_gk", return_value=self.s):
            HTTP.dieu_huong(h, app, False, "/api/crm/bao-gia/ty-gia-mac-dinh", {})
            self.assertEqual(h.send_content.call_args.args, (200, {"ty_gia": "26000"}))
            h.json_body = lambda: {"ty_gia": "25.500", "ly_do": "DEMO"}
            HTTP.dieu_huong(h, app, True, "/api/crm/bao-gia/ty-gia-mac-dinh", {})
            self.assertEqual(h.send_content.call_args.args, (200, {"ty_gia": "25500"}))
            self.s.sua_ty_gia_mac_dinh.assert_called_once_with("nguoi-thu", ty_gia="25.500", ly_do="DEMO")
            h.json_body = lambda: {"ty_gia": "25.500", "nguoi": "khac"}
            HTTP.dieu_huong(h, app, True, "/api/crm/bao-gia/ty-gia-mac-dinh", {})
            self.assertEqual(h.send_content.call_args.args[0], 403)  # danh tính không nhận từ trình duyệt


class LoiTheoTruong(unittest.TestCase):
    """Vòng 2 (review): lỗi nhập mang trường (DataError.locator) và HTTP giữ `truong` trong JSON lỗi — như lỗi theo trường của ô thông minh."""

    def test_ty_gia_don_gia_dien_tich_va_lich_co_truong(self):
        ca = [("fx.ty_gia", "CRM_GK_SO_SAI", {"fx": {"cap": "USD/VND", "ty_gia": v}}) for v in ("-1", "abc", "1" * 25, "1.5.0", "1,5", 25500)]
        ca += [("fx.ty_gia", "CRM_GK_FX_SAI", {"fx": {"cap": "USD/VND", "ty_gia": v}}) for v in ("0", "0.000")]
        ca += [("fx.cap", "CRM_GK_FX_SAI", {"fx": {"cap": "EUR/VND", "ty_gia": "25500"}}),
               ("fx.ngay", "CRM_G_YEU_CAU_SAI", {"fx": {"cap": "USD/VND", "ty_gia": "25500", "ngay": "25/10/2026"}}),
               ("fx", "CRM_GK_YEU_CAU_SAI", {"fx": {"ty_gia": "25500", "nguoi_nhap": "X"}}),
               ("gia.don_gia", "CRM_GK_SO_SAI", {"gia": {"tien_te": "USD", "don_gia": "-100", "dien_tich": "15000"}}),
               ("gia.dien_tich", "CRM_GK_SO_SAI", {"gia": {"tien_te": "USD", "don_gia": "100", "dien_tich": "15.000,5"}}),
               ("gia.tong", "CRM_GK_SO_SAI", {"gia": {"tien_te": "VND", "tong": "1e9"}}),
               ("gia.tien_te", "CRM_GK_YEU_CAU_SAI", {"gia": {"tien_te": "EUR"}}),
               ("phi_bao_tri.gia_tri", "CRM_GK_SO_SAI", {"phi_bao_tri": {"gia_tri": "-1", "tien_te": "VND"}}),
               ("lich.1.so_tien", "CRM_GK_SO_SAI", {"lich": [{"gia_tri_nhap": "30%"}, {"loai": "AMOUNT", "so_tien": "-5"}]}),
               ("lich.0.moc_ngay", "CRM_G_YEU_CAU_SAI", {"lich": [{"gia_tri_nhap": "100%", "moc_loai": "NGAY", "moc_ngay": "2026-02-30"}]}),
               ("het_han", "CRM_G_YEU_CAU_SAI", {"het_han": "31/12/2026"})]
        for truong, ma, sua in ca:
            with self.subTest(truong=truong, sua=sua):
                with self.assertRaises(DataError) as cm:
                    GK.chuan_hoa_bao_gia(bao_gia(**sua))
                self.assertEqual((cm.exception.code, cm.exception.locator), (ma, truong))
        with self.assertRaises(DataError) as cm:  # Lưu báo giá VND kèm tỷ giá khác 1
            GK._chan_ty_gia_vnd(GK.chuan_hoa_bao_gia(bao_gia(gia={"tien_te": "VND", "tong": "1000"})))
        self.assertEqual((cm.exception.code, cm.exception.locator), ("CRM_GK_FX_SAI", "fx.ty_gia"))

    def test_http_tra_truong_trong_json_loi(self):
        s = GK.CrmGiaoKetK2(SimpleNamespace(root=".", danh_tinh=mock.Mock(return_value={"id": "U1", "dang_nhap": "nguoi-thu"}),
                                            _tx=mock.Mock(side_effect=AssertionError("không mở giao dịch khi dữ liệu sai")),
                                            hom_nay=lambda: date(2026, 10, 25), conn_tin_cay=object()))
        h = SimpleNamespace(crm_sid=lambda: "sid", send_content=mock.Mock())
        app = SimpleNamespace(mutation_lock=nullcontext(), crm_phien=lambda sid: (None, "nguoi-thu", None), _crm_db=lambda f, *a, **kw: f(*a, **kw))
        with mock.patch.object(HTTP, "dich_vu_gk", return_value=s):
            for ty_gia, ma in (("-1", "CRM_GK_SO_SAI"), ("0", "CRM_GK_FX_SAI"), ("٢٥٩٩٩.٥", "CRM_GK_SO_SAI")):
                with self.subTest(ty_gia=ty_gia):
                    h.json_body = lambda ty_gia=ty_gia: {"du_lieu": bao_gia(fx={"cap": "USD/VND", "ty_gia": ty_gia})}
                    HTTP.dieu_huong(h, app, True, "/api/crm/bao-gia/xem-truoc", {})
                    code, body = h.send_content.call_args.args
                    self.assertEqual((code, body["error"], body["truong"]), (400, ma, "fx.ty_gia"))
                    self.assertTrue(body["message"])
            h.json_body = lambda: {"du_lieu": bao_gia(gia={"tien_te": "USD", "don_gia": "100", "dien_tich": "١٥٠٠٠"})}
            HTTP.dieu_huong(h, app, True, "/api/crm/bao-gia/xem-truoc", {})
            self.assertEqual(h.send_content.call_args.args[1]["truong"], "gia.dien_tich")
            h.json_body = lambda: {"du_lieu": bao_gia(), "nguoi": "khac"}  # lỗi không gắn trường: giữ nguyên hình dạng cũ
            HTTP.dieu_huong(h, app, True, "/api/crm/bao-gia/xem-truoc", {})
            self.assertEqual(set(h.send_content.call_args.args[1]), {"error", "message"})
        with mock.patch.object(HTTP, "dich_vu_gk", return_value=s):
            h.json_body = lambda: {"ty_gia": "26000%"}
            HTTP.dieu_huong(h, app, True, "/api/crm/bao-gia/ty-gia-mac-dinh", {})
            self.assertEqual(h.send_content.call_args.args[0], 400)
            self.assertEqual(h.send_content.call_args.args[1]["truong"], "ty_gia")


if __name__ == "__main__":
    unittest.main()
