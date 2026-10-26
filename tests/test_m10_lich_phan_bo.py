"""M10-1a: dữ liệu DEMO, test thuần, không CSDL/tệp/Junsky."""

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime
from decimal import Decimal, Inexact, ROUND_HALF_EVEN, ROUND_HALF_UP, localcontext
import unittest

from kho_tri_thuc.m10.lich_phan_bo import (
    DotThu, HopDong, Policy, QuyTacLamTron, tinh_lich_phan_bo,
)


D = Decimal


def policy(phuong_phap="A", **thay):
    # Mặc định chỉ của fixture DEMO, engine bắt buộc nhận mọi tham số.
    return replace(Policy(phuong_phap, "THANG", "TRON_THANG", "TRON_THANG",
                          QuyTacLamTron(2, ROUND_HALF_UP, True)), **thay)


def hop_dong(**thay):
    return replace(HopDong("DEMO-HD", "DEMO-v1", date(2025, 1, 1),
                           date(2029, 12, 31), "DEMO"), **thay)


DOT_DEMO = (DotThu("DEMO-1", D("300"), date(2025, 1, 1)),
            DotThu("DEMO-2", D("300"), date(2025, 7, 1)))


class LichPhanBoTests(unittest.TestCase):
    def test_vi_du_74_cach_a_nam_1_120_va_catch_up(self):
        lich = tinh_lich_phan_bo(hop_dong(), DOT_DEMO, policy("A"))
        self.assertEqual(sum(d.doanh_thu_ky for d in lich.tong_hop_dong[:12]), D("120"))
        dot2 = lich.lich_tung_dot[1].cac_ky
        self.assertEqual((dot2[0].ky, dot2[0].doanh_thu_ky), ("2025-07", D("35")))
        self.assertEqual(dot2[1].doanh_thu_ky, D("5"))

    def test_vi_du_74_cach_b_nam_1_9336(self):
        lich = tinh_lich_phan_bo(hop_dong(), DOT_DEMO, policy("B"))
        dot2 = lich.lich_tung_dot[1].cac_ky
        thang = (D("300") / D("54")).quantize(D("0.01"), rounding=ROUND_HALF_UP)
        self.assertEqual(thang, D("5.56"))
        self.assertEqual(len(dot2), 54)
        self.assertEqual(dot2[0].doanh_thu_ky, thang)
        self.assertEqual(sum(d.doanh_thu_ky for d in lich.tong_hop_dong[:12]), D("93.36"))
        self.assertEqual(dot2[-1].doanh_thu_ky, D("5.32"))

    def test_tong_toan_ky_va_tong_hop_3387_chi_gom_dot_da_ghi(self):
        for pp in ("A", "B"):
            with self.subTest(pp=pp):
                lich = tinh_lich_phan_bo(hop_dong(), DOT_DEMO, policy(pp))
                self.assertEqual(len(lich.tong_hop_dong), 60)
                self.assertEqual(sum(d.doanh_thu_ky for d in lich.tong_hop_dong), D("600"))
                self.assertEqual(lich.so_du_3387_con_lai, D("0"))
                self.assertEqual(lich.tong_hop_dong[0].so_du_3387_cuoi_ky, D("295"))
                for dot in lich.lich_tung_dot:
                    self.assertEqual(sum(d.doanh_thu_ky for d in dot.cac_ky), D("300"))
                    self.assertEqual(dot.cac_ky[-1].luy_ke, D("300"))
                    self.assertEqual(dot.so_du_3387_con_lai, D("0"))
                for dong in lich.tong_hop_dong:
                    cung_ky = [d for dot in lich.lich_tung_dot for d in dot.cac_ky if d.ky == dong.ky]
                    self.assertEqual(dong.doanh_thu_ky, sum(d.doanh_thu_ky for d in cung_ky))
                    self.assertEqual(dong.so_du_3387_cuoi_ky, sum(d.so_du_3387_cuoi_ky for d in cung_ky))

    def test_dot_truoc_ban_giao_ca_a_b(self):
        hd = hop_dong(ngay_ban_giao=date(2025, 3, 16), ngay_ket_thuc_thue=date(2025, 5, 31))
        dot = (DotThu("DEMO-TRUOC", D("90"), date(2025, 1, 1)),)
        for pp in ("A", "B"):
            with self.subTest(pp=pp):
                lich = tinh_lich_phan_bo(hd, dot, policy(pp))
                self.assertEqual([d.ky for d in lich.lich_tung_dot[0].cac_ky],
                                 ["2025-03", "2025-04", "2025-05"])
                self.assertEqual(lich.tong_hop_dong[0].doanh_thu_ky, D("30"))

    def test_cham_dut_som_khong_don_so_du_vao_ky_cham_dut(self):
        hd = hop_dong(ngay_cham_dut=date(2025, 12, 31))
        for pp, so_du in (("A", D("480")), ("B", D("506.64"))):
            with self.subTest(pp=pp):
                lich = tinh_lich_phan_bo(hd, DOT_DEMO, policy(pp))
                self.assertEqual(len(lich.tong_hop_dong), 12)
                self.assertEqual(lich.tong_hop_dong[-1].ky, "2025-12")
                self.assertEqual(lich.so_du_3387_con_lai, so_du)
                self.assertEqual(sum(d.so_du_3387_con_lai for d in lich.lich_tung_dot), so_du)

    def test_thang_le_dau_cuoi_theo_ngay_va_nam_nhuan(self):
        hd = hop_dong(ngay_ban_giao=date(2024, 1, 16), ngay_ket_thuc_thue=date(2024, 3, 15))
        dot = (DotThu("DEMO-LE", D("62"), date(2024, 1, 1)),)
        for pp in ("A", "B"):
            with self.subTest(pp=pp):
                lich = tinh_lich_phan_bo(hd, dot, policy(pp, thang_le_dau="THEO_NGAY", thang_le_cuoi="THEO_NGAY"))
                self.assertEqual([d.doanh_thu_ky for d in lich.tong_hop_dong], [D("16"), D("31"), D("15")])
                tron = tinh_lich_phan_bo(hd, dot, policy(pp))
                self.assertEqual([d.doanh_thu_ky for d in tron.tong_hop_dong], [D("20.67"), D("20.67"), D("20.66")])

    def test_thang_hai_nhuan_va_cung_thang(self):
        hd = hop_dong(ngay_ban_giao=date(2024, 2, 15), ngay_ket_thuc_thue=date(2024, 3, 31))
        dot = (DotThu("DEMO-NHUAN", D("44"), date(2024, 2, 1)),)
        lich = tinh_lich_phan_bo(hd, dot, policy(thang_le_dau="THEO_NGAY"))
        self.assertEqual([d.doanh_thu_ky for d in lich.tong_hop_dong], [D("15"), D("29")])
        hd = replace(hd, ngay_ket_thuc_thue=date(2024, 2, 20))
        lich = tinh_lich_phan_bo(hd, dot, policy(thang_le_dau="THEO_NGAY", thang_le_cuoi="THEO_NGAY"))
        self.assertEqual(lich.tong_hop_dong[0].doanh_thu_ky, D("44"))

    def test_b_ghi_giua_thang_khong_catch_up(self):
        hd = hop_dong(ngay_ket_thuc_thue=date(2025, 3, 31))
        dot = (DotThu("DEMO-GIUA", D("59"), date(2025, 2, 14)),)
        lich = tinh_lich_phan_bo(hd, dot, policy("B", thang_le_dau="THEO_NGAY"))
        self.assertEqual([d.doanh_thu_ky for d in lich.tong_hop_dong], [D("0"), D("20.58"), D("38.42")])
        self.assertEqual(lich.tong_hop_dong[0].so_du_3387_cuoi_ky, D("0"))

    def test_cham_dut_giua_thang_theo_ngay_khong_doi_mau_so(self):
        hd = hop_dong(ngay_ket_thuc_thue=date(2025, 3, 31), ngay_cham_dut=date(2025, 2, 14))
        dot = (DotThu("DEMO-DUNG", D("84"), date(2025, 1, 1)),)
        lich = tinh_lich_phan_bo(hd, dot, policy(thang_le_cuoi="THEO_NGAY"))
        self.assertEqual([d.doanh_thu_ky for d in lich.tong_hop_dong], [D("28"), D("14")])
        self.assertEqual(lich.so_du_3387_con_lai, D("42"))

    def test_khong_don_phan_le_giu_nguyen_chenh_khac_0(self):
        hd = hop_dong(ngay_ket_thuc_thue=date(2025, 3, 31))
        dot = (DotThu("DEMO-LE", D("1"), date(2025, 1, 1)),)
        lich = tinh_lich_phan_bo(hd, dot, policy(lam_tron=QuyTacLamTron(2, ROUND_HALF_UP, False)))
        self.assertEqual([d.doanh_thu_ky for d in lich.tong_hop_dong], [D("0.33")] * 3)
        self.assertEqual(lich.so_du_3387_con_lai, D("0.01"))
        self.assertNotEqual(lich.so_du_3387_con_lai, D("0"))

    def test_hai_kieu_lam_tron_tai_diem_giua(self):
        hd = hop_dong(ngay_ket_thuc_thue=date(2025, 2, 28))
        dot = (DotThu("DEMO-ROUND", D("2.01"), date(2025, 1, 1)),)
        for kieu, dau, cuoi in ((ROUND_HALF_UP, "1.01", "1.00"), (ROUND_HALF_EVEN, "1.00", "1.01")):
            with self.subTest(kieu=kieu):
                lich = tinh_lich_phan_bo(hd, dot, policy(lam_tron=QuyTacLamTron(2, kieu, True)))
                self.assertEqual([d.doanh_thu_ky for d in lich.tong_hop_dong], [D(dau), D(cuoi)])

    def test_thieu_phuong_phap_hoac_lam_tron_khong_mac_dinh(self):
        with self.assertRaisesRegex(TypeError, "phuong_phap"):
            Policy(don_vi_ky="THANG", thang_le_dau="TRON_THANG", thang_le_cuoi="TRON_THANG",
                   lam_tron=QuyTacLamTron(2, ROUND_HALF_UP, True))
        with self.assertRaisesRegex(TypeError, "lam_tron"):
            Policy("A", "THANG", "TRON_THANG", "TRON_THANG")
        for pp in (None, "", "C"):
            with self.subTest(pp=pp), self.assertRaisesRegex(ValueError, "phuong_phap"):
                policy(pp)
        with self.assertRaisesRegex(ValueError, "lam_tron"):
            policy(lam_tron=None)

    def test_policy_thieu_hoac_sai_tham_so_khac(self):
        for thay in ({"don_vi_ky": None}, {"don_vi_ky": "NGAY"}, {"thang_le_dau": None},
                     {"thang_le_cuoi": "SAI"}):
            with self.subTest(thay=thay), self.assertRaises(ValueError):
                policy(**thay)
        for so in (-1, 2.0, True):
            with self.subTest(so=so), self.assertRaises(ValueError):
                QuyTacLamTron(so, ROUND_HALF_UP, True)
        with self.assertRaises(ValueError):
            QuyTacLamTron(2, "ROUND_DOWN", True)
        with self.assertRaises(TypeError):
            QuyTacLamTron(2, ROUND_HALF_UP, None)

    def test_tu_choi_float_va_gia_tri_khong_hop_le(self):
        for tien in (300.0, 300, "300", True):
            with self.subTest(tien=tien), self.assertRaisesRegex(TypeError, "Decimal"):
                DotThu("DEMO-SAI", tien, date(2025, 1, 1))
        for tien in (D("NaN"), D("sNaN"), D("Infinity"), D("-1")):
            with self.subTest(tien=tien), self.assertRaises(ValueError):
                DotThu("DEMO-SAI", tien, date(2025, 1, 1))

    def test_dau_vao_bat_bien_va_khong_bi_doi(self):
        hd, pol = hop_dong(), policy()
        for obj, ten, value in ((hd, "phien_ban", "khac"), (DOT_DEMO[0], "gia_tri_truoc_vat", D("1")),
                                (pol, "phuong_phap", "B"), (pol.lam_tron, "so_chu_so", 0)):
            with self.subTest(ten=ten), self.assertRaises(FrozenInstanceError):
                setattr(obj, ten, value)
        tinh_lich_phan_bo(hd, DOT_DEMO, pol)
        self.assertEqual(hd, hop_dong())
        self.assertEqual(DOT_DEMO[0].gia_tri_truoc_vat, D("300"))
        with self.assertRaises(ValueError):
            tinh_lich_phan_bo(hd, list(DOT_DEMO), pol)

    def test_hash_on_dinh_va_moi_tham_so_tham_gia_hash(self):
        hd, pol = hop_dong(), policy()
        lich = tinh_lich_phan_bo(hd, DOT_DEMO, pol)
        self.assertEqual(lich, tinh_lich_phan_bo(hop_dong(), DOT_DEMO, policy()))
        self.assertEqual((lich.ma_hop_dong, lich.phien_ban, lich.currency), ("DEMO-HD", "DEMO-v1", "DEMO"))
        self.assertEqual(len(lich.hash_dau_vao), 64)
        bien_the = [(replace(hd, **thay), DOT_DEMO, pol) for thay in (
            {"ma_hop_dong": "DEMO-KHAC"}, {"phien_ban": "DEMO-v2"}, {"currency": "VND"},
            {"ngay_ban_giao": date(2025, 1, 2)}, {"ngay_ket_thuc_thue": date(2029, 12, 30)},
            {"ngay_cham_dut": date(2029, 12, 30)})]
        bien_the += [(hd, (replace(DOT_DEMO[0], **thay), DOT_DEMO[1]), pol) for thay in (
            {"ma_dot": "DEMO-KHAC"}, {"gia_tri_truoc_vat": D("301")}, {"ngay_ghi_3387": date(2025, 1, 2)})]
        bien_the += [(hd, DOT_DEMO, replace(pol, **thay)) for thay in (
            {"phuong_phap": "B"}, {"thang_le_dau": "THEO_NGAY"}, {"thang_le_cuoi": "THEO_NGAY"},
            {"lam_tron": replace(pol.lam_tron, so_chu_so=3)},
            {"lam_tron": replace(pol.lam_tron, kieu_lam_tron=ROUND_HALF_EVEN)},
            {"lam_tron": replace(pol.lam_tron, don_phan_le_ky_cuoi=False)})]
        for args in bien_the:
            with self.subTest(args=args):
                self.assertNotEqual(lich.hash_dau_vao, tinh_lich_phan_bo(*args).hash_dau_vao)

    def test_khong_phu_thuoc_decimal_context_va_so_tien_lon(self):
        dot = (DotThu("DEMO-LON", D("123456789012345678901234567890.123456789"), date(2025, 1, 1)),)
        hd = hop_dong(ngay_ket_thuc_thue=date(2025, 3, 31))
        lich = tinh_lich_phan_bo(hd, dot, policy())
        with localcontext() as ctx:
            ctx.prec = 3
            ctx.traps[Inexact] = True
            self.assertEqual(lich, tinh_lich_phan_bo(hd, dot, policy()))
        self.assertEqual(lich.tong_hop_dong[-1].luy_ke, dot[0].gia_tri_truoc_vat)
        self.assertEqual(lich.so_du_3387_con_lai, D("0"))

    def test_ngay_va_dinh_danh_khong_hop_le(self):
        for thay in ({"ngay_ket_thuc_thue": date(2024, 1, 1)}, {"ngay_cham_dut": date(2024, 1, 1)},
                     {"ngay_cham_dut": date(2030, 1, 1)}, {"phien_ban": ""}, {"currency": ""}):
            with self.subTest(thay=thay), self.assertRaises(ValueError):
                hop_dong(**thay)
        with self.assertRaises(TypeError):
            hop_dong(ngay_ban_giao=datetime(2025, 1, 1))
        with self.assertRaises(ValueError):
            tinh_lich_phan_bo(hop_dong(), (DOT_DEMO[0], DOT_DEMO[0]), policy())
        with self.assertRaises(ValueError):
            tinh_lich_phan_bo(hop_dong(), (), policy())
        with self.assertRaisesRegex(ValueError, "ngay_ghi_3387"):
            tinh_lich_phan_bo(hop_dong(ngay_cham_dut=date(2025, 6, 30)), DOT_DEMO, policy())
        with self.assertRaisesRegex(ValueError, "ngay_ghi_3387"):
            tinh_lich_phan_bo(hop_dong(ngay_ket_thuc_thue=date(2025, 6, 30)), DOT_DEMO, policy())

    def test_ngay_bien_9999_khong_tran_va_gia_tri_0(self):
        hd = hop_dong(ngay_ban_giao=date(9999, 12, 31), ngay_ket_thuc_thue=date(9999, 12, 31))
        for tien in (D("0"), D("1.001")):
            with self.subTest(tien=tien):
                lich = tinh_lich_phan_bo(hd, (DotThu("DEMO-BIEN", tien, date(9999, 12, 31)),), policy())
                self.assertEqual(lich.tong_hop_dong[0].doanh_thu_ky, tien)
                self.assertEqual(lich.so_du_3387_con_lai, D("0"))


if __name__ == "__main__":
    unittest.main()
