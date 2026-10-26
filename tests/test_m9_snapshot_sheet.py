"""M9-3a: chỉ dùng Sheet giả, pháp nhân/ngân hàng DEMO; không mạng/ghi đĩa."""

from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, localcontext
import unittest

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m9.bao_cao_lai_suat import lap_bao_cao
from kho_tri_thuc.m9.snapshot_sheet import CAU_HINH_MAU, lap_snapshot


_KEO_LUC = datetime(2026, 10, 26, 8, 30)


def _hang(**thay):
    return {
        "phap_nhan": "Pháp nhân DEMO Sao Giấy",
        "ngan_hang": "Ngân hàng DEMO Mây Tím",
        "ma_khoan_vay": "DEMO-01", "tien_te": "VND",
        "du_no": "1.234.567.890", "lai_suat_nam": "8,5%",
        "cach_tinh": "THA_NOI", "lai_co_so": "6.5", "bien_do": "2%",
        "ky_dieu_chinh_ke_tiep": "10/11/2026", "ngay_dao_han": "26/10/2027",
        **thay,
    }


def _sheet(*hang, cau_hinh=None):
    cfg = CAU_HINH_MAU if cau_hinh is None else cau_hinh
    cot = cfg["anh_xa_cot"]
    return [list(cot)] + [[h[v] for v in cot.values()] for h in hang]


def _lap(gia_tri=None, *, cau_hinh=None, keo_luc=_KEO_LUC):
    return lap_snapshot(
        _sheet(_hang()) if gia_tri is None else gia_tri,
        cau_hinh=CAU_HINH_MAU if cau_hinh is None else cau_hinh,
        keo_luc=keo_luc, nguon_id="DEMO-SHEET-KHONG-CO-THAT",
    )


class SnapshotSheetTests(unittest.TestCase):
    def test_doc_du_truong_va_moc_nguon(self):
        kq = _lap()
        self.assertEqual(kq["moc"], "26/10/2026 08:30")
        self.assertEqual(kq["nguon"], "Sheet")
        self.assertEqual(kq["nguon_id"], "DEMO-SHEET-KHONG-CO-THAT")
        self.assertEqual(kq["tab"], CAU_HINH_MAU["ten_tab"])
        self.assertEqual(kq["dong_loi"], [])
        self.assertEqual(kq["so_dong_doc"], 1)
        self.assertEqual(kq["khoan_vay"], [{
            **_hang(), "du_no": Decimal("1234567890"),
            "lai_suat_nam": Decimal("8.5"), "lai_co_so": Decimal("6.5"),
            "bien_do": Decimal("2"), "ky_dieu_chinh_ke_tiep": date(2026, 11, 10),
            "ngay_dao_han": date(2027, 10, 26),
        }])

    def test_dao_cot_va_thu_tu_dict_cau_hinh_khong_doi_ket_qua(self):
        tho = _sheet(_hang(), _hang(ma_khoan_vay="DEMO-02"))
        cfg = deepcopy(CAU_HINH_MAU)
        cfg["anh_xa_cot"] = dict(reversed(list(cfg["anh_xa_cot"].items())))
        self.assertEqual(_lap(tho), _lap([list(reversed(h)) for h in tho], cau_hinh=cfg))

    def test_tieu_de_tu_dat_va_dong_tieu_de_khong_phai_dong_mot(self):
        cfg = deepcopy(CAU_HINH_MAU)
        cfg["dong_tieu_de"] = 3
        cfg["anh_xa_cot"] = {"DEMO " + v: v for v in cfg["anh_xa_cot"].values()}
        tho = [["DEMO - chỉ dữ liệu giả"], []] + _sheet(_hang(du_no="sai"), cau_hinh=cfg)
        kq = _lap(tho, cau_hinh=cfg)
        self.assertEqual(kq["so_dong_doc"], 1)
        self.assertEqual(kq["khoan_vay"], [])
        self.assertEqual(kq["dong_loi"][0]["so_dong"], 4)
        self.assertEqual(kq["dong_loi"][0]["ten_cot"], "DEMO du_no")

    def test_thieu_cot_neu_ten_cot_va_ma_loi(self):
        for ten in CAU_HINH_MAU["anh_xa_cot"]:
            with self.subTest(cot=ten):
                tho = _sheet(_hang())
                i = tho[0].index(ten)
                for h in tho:
                    h.pop(i)
                with self.assertRaises(DataError) as bat:
                    _lap(tho)
                self.assertEqual(bat.exception.code, "M9_SHEET_THIEU_COT")
                self.assertIn(ten, str(bat.exception))

    def test_sheet_rong_va_khong_co_dong_tieu_de(self):
        for tho in ([], [[]]):
            with self.subTest(tho=tho), self.assertRaises(DataError) as bat:
                _lap(tho)
            self.assertEqual(bat.exception.code, "M9_SHEET_THIEU_COT")
        self.assertEqual(_lap(_sheet())["khoan_vay"], [])

    def test_tieu_de_trung_khong_chon_cot(self):
        tho = _sheet(_hang())
        tho[0].append(tho[0][0])
        tho[1].append("Pháp nhân DEMO Khác")
        with self.assertRaises(DataError) as bat:
            _lap(tho)
        self.assertEqual(bat.exception.code, "M9_SHEET_TRUNG_COT")

    def test_tien_theo_locale_va_khong_phu_thuoc_decimal_context(self):
        for dau, chu, so in (
            (",", "1.234.567.890", "1234567890"),
            (",", "1.234.567,89", "1234567.89"),
            (".", "1,234,567,890.50", "1234567890.50"),
            (".", "1234.50", "1234.50"),
            (",", "0", "0"),
        ):
            with self.subTest(dau=dau, chu=chu), localcontext() as ctx:
                ctx.prec = 4
                cfg = deepcopy(CAU_HINH_MAU)
                cfg["dau_thap_phan"] = dau
                kq = _lap(_sheet(_hang(du_no=chu)), cau_hinh=cfg)
                self.assertEqual(kq["khoan_vay"][0]["du_no"], Decimal(so))
        cfg.pop("dau_thap_phan")
        self.assertEqual(_lap(cau_hinh=cfg)["khoan_vay"][0]["du_no"], Decimal("1234567890"))

    def test_lai_phan_tram_khong_chia_mot_tram(self):
        for chu in ("8,5%", "8.5", " 8.5 % ", "8,5"):
            with self.subTest(chu=chu):
                k = _lap(_sheet(_hang(lai_suat_nam=chu, lai_co_so=chu, bien_do=chu)))["khoan_vay"][0]
                for truong in ("lai_suat_nam", "lai_co_so", "bien_do"):
                    self.assertEqual(k[truong], Decimal("8.5"))

    def test_o_trong_va_o_cuoi_bi_luoc_bo_la_none(self):
        k = _lap(_sheet(_hang(**{v: "  " for v in CAU_HINH_MAU["anh_xa_cot"].values()
                                if v != "ma_khoan_vay"})))["khoan_vay"][0]
        self.assertTrue(all(v is None for t, v in k.items() if t != "ma_khoan_vay"))
        tho = _sheet(_hang())
        tho[1] = tho[1][:7]
        k = _lap(tho)["khoan_vay"][0]
        for t in ("lai_co_so", "bien_do", "ky_dieu_chinh_ke_tiep", "ngay_dao_han"):
            self.assertIsNone(k[t])

    def test_ngay_sai_vao_dong_loi_khong_lo_noi_dung_o(self):
        for t in ("ky_dieu_chinh_ke_tiep", "ngay_dao_han"):
            for sai in ("31/02/2026", "2026-10-26", "1/11/2026"):
                with self.subTest(truong=t, sai=sai):
                    kq = _lap(_sheet(_hang(**{t: sai}), _hang(ma_khoan_vay="DEMO-02")))
                    self.assertEqual([k["ma_khoan_vay"] for k in kq["khoan_vay"]], ["DEMO-02"])
                    loi = kq["dong_loi"][0]
                    self.assertEqual(loi["so_dong"], 2)
                    self.assertEqual(loi["ten_cot"], next(k for k, v in CAU_HINH_MAU["anh_xa_cot"].items() if v == t))
                    self.assertEqual(loi["ma_loi"], "M9_SHEET_NGAY_SAI")
                    self.assertIn("Cần Anh/lead", loi["ghi_chu"])
                    self.assertNotIn(sai, str(kq["dong_loi"]))

    def test_so_sai_khong_doan_dau_khong_nhan_nan_inf_cong_thuc(self):
        for t, sai in (
            ("du_no", "1,234,567,890.50"), ("du_no", "12.34.567"),
            ("du_no", "1 234"), ("du_no", "NaN"), ("du_no", "Infinity"),
            ("du_no", "1e9"), ("du_no", "=SUM(A1:A2)"),
            ("lai_suat_nam", "8,5.1%"), ("lai_co_so", "NaN"), ("bien_do", "#N/A"),
        ):
            with self.subTest(truong=t, sai=sai):
                kq = _lap(_sheet(_hang(**{t: sai})))
                self.assertEqual(kq["khoan_vay"], [])
                self.assertEqual(kq["dong_loi"][0]["ma_loi"], "M9_SHEET_SO_SAI")
                self.assertNotIn(sai, str(kq["dong_loi"]))

    def test_trung_ma_loai_tat_ca_ke_ca_dong_da_co_loi_khac(self):
        kq = _lap(_sheet(_hang(du_no="sai"), _hang(),
                         _hang(ma_khoan_vay=" DEMO-01 "), _hang(ma_khoan_vay="DEMO-02")))
        self.assertEqual([k["ma_khoan_vay"] for k in kq["khoan_vay"]], ["DEMO-02"])
        self.assertEqual([e["so_dong"] for e in kq["dong_loi"] if e["ma_loi"] == "TRUNG_MA"], [2, 3, 4])
        self.assertTrue(all(e["ten_cot"] == "Mã khoản vay DEMO" for e in kq["dong_loi"] if e["ma_loi"] == "TRUNG_MA"))

    def test_ma_trong_khong_bi_xem_la_trung(self):
        kq = _lap(_sheet(_hang(ma_khoan_vay=""), _hang(ma_khoan_vay=" ")))
        self.assertEqual(kq["dong_loi"], [])
        self.assertEqual([k["ma_khoan_vay"] for k in kq["khoan_vay"]], [None, None])

    def test_dong_trong_bo_qua_nhung_dem_so_dong_doc(self):
        tho = _sheet(_hang()) + [[], ["", "  "]]
        kq = _lap(tho)
        self.assertEqual(kq["so_dong_doc"], 3)
        self.assertEqual(len(kq["khoan_vay"]), 1)
        self.assertEqual(kq["dong_loi"], [])

    def test_hash_on_dinh_khong_gom_gio_va_doi_o_thi_khac(self):
        tho = _sheet(_hang())
        goc = _lap(tho)["sha256"]
        self.assertRegex(goc, r"^[0-9a-f]{64}$")
        self.assertEqual(goc, _lap(deepcopy(tho), keo_luc=datetime(2026, 10, 27, 9, 40))["sha256"])
        for h, i in ((0, 0), (1, 0), (1, 4)):
            sua = deepcopy(tho)
            # Đổi tiêu đề kèm cấu hình để vẫn hợp lệ.
            cfg = deepcopy(CAU_HINH_MAU)
            if h == 0:
                v = cfg["anh_xa_cot"].pop(sua[h][i])
                cfg["anh_xa_cot"][sua[h][i] + " DEMO"] = v
            sua[h][i] += " DEMO"
            self.assertNotEqual(goc, _lap(sua, cau_hinh=cfg)["sha256"])

    def test_hash_giu_gia_tri_tho_dong_loi_va_cot_khong_anh_xa(self):
        a = _sheet(_hang(du_no="sai"))
        b = _sheet(_hang(du_no="sai khac"))
        self.assertNotEqual(_lap(a)["sha256"], _lap(b)["sha256"])
        a[0].append("Ghi chú DEMO")
        a[1].append("DEMO A")
        b = deepcopy(a)
        b[1][-1] = "DEMO B"
        self.assertNotEqual(_lap(a)["sha256"], _lap(b)["sha256"])
        self.assertNotEqual(_lap()["sha256"], _lap(_sheet(_hang(du_no="1234567890")))["sha256"])

    def test_hash_o_cuoi_trong_va_bi_luoc_la_nhu_nhau_thu_tu_dong_duoc_giu(self):
        a = _sheet(_hang(ngay_dao_han=""))
        b = deepcopy(a)
        b[1].pop()
        self.assertEqual(_lap(a)["sha256"], _lap(b)["sha256"])
        a = _sheet(_hang(), _hang(ma_khoan_vay="DEMO-02"))
        b = [a[0], a[2], a[1]]
        self.assertNotEqual(_lap(a)["sha256"], _lap(b)["sha256"])

    def test_khong_sua_dau_vao_cau_hinh(self):
        tho, cfg = _sheet(_hang()), deepcopy(CAU_HINH_MAU)
        truoc = deepcopy((tho, cfg, CAU_HINH_MAU))
        _lap(tho, cau_hinh=cfg)
        self.assertEqual((tho, cfg, CAU_HINH_MAU), truoc)

    def test_cau_hinh_sai_dung_an_toan(self):
        for thay in ({"dong_tieu_de": 0}, {"dong_tieu_de": True},
                     {"dau_thap_phan": ";"}, {"ten_tab": ""}, {"anh_xa_cot": {}}):
            with self.subTest(thay=thay), self.assertRaises(DataError) as bat:
                _lap(cau_hinh={**deepcopy(CAU_HINH_MAU), **thay})
            self.assertEqual(bat.exception.code, "M9_SHEET_CAU_HINH")

    def test_tich_hop_bao_cao_va_khong_float_de_quy(self):
        snap = _lap(_sheet(_hang(), _hang(ma_khoan_vay="DEMO-02", du_no="100.000.000",
                                        lai_suat_nam="10%"),
                          _hang(ma_khoan_vay="DEMO-03", du_no="", lai_suat_nam="")))
        bc = lap_bao_cao(snap, ngay_bao_cao=date(2026, 10, 26))
        self.assertEqual(bc["tong_du_no_theo_tien_te"], {"VND": Decimal("1334567890")})
        self.assertEqual(bc["so_khoan_lai_cao"], 1)
        self.assertEqual(bc["khoan_vay"][0]["ma_khoan_vay"], "DEMO-02")
        self.assertEqual(bc["khoan_vay"][-1]["trang_thai"], "THIEU_DU_LIEU")

        def kiem(v):
            self.assertNotIsInstance(v, float)
            if isinstance(v, dict):
                for k, con in v.items():
                    kiem(k)
                    kiem(con)
            elif isinstance(v, (list, tuple)):
                for con in v:
                    kiem(con)
        kiem(snap)
        kiem(bc)


if __name__ == "__main__":
    unittest.main()
