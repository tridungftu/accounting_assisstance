"""M9-4a: dữ liệu DEMO giả, tính thuần và đọc Excel trong bộ nhớ."""

from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal, localcontext
from io import BytesIO
import unittest

from openpyxl import load_workbook

from kho_tri_thuc.m9.bao_cao_lai_suat import lap_bao_cao, xuat_excel


_NGAY = date(2026, 10, 26)
_MOC = "26/10/2026 08:30"


def _khoan(ma="DEMO-01", **thay):
    return {
        "phap_nhan": "Pháp nhân DEMO Sao Giấy",
        "ngan_hang": "Ngân hàng DEMO Mây Tím",
        "ma_khoan_vay": ma, "tien_te": "VND",
        "du_no": Decimal("100000000"), "lai_suat_nam": Decimal("6"),
        "cach_tinh": "CO_DINH", "ky_dieu_chinh_ke_tiep": None,
        "ngay_dao_han": date(2027, 10, 26), **thay,
    }


def _snapshot(*khoan):
    return {"moc": _MOC, "nguon": "Sheet", "khoan_vay": list(khoan)}


def _ba_khoan():
    # Số tay: (100 triệu * 6 + 200 triệu * 8 + 400 triệu * 11) / 700 triệu = 66/7.
    return [
        _khoan(),
        _khoan("DEMO-02", du_no=Decimal("200000000"), lai_suat_nam=Decimal("8")),
        _khoan("DEMO-03", du_no=Decimal("400000000"), lai_suat_nam=Decimal("11"),
               cach_tinh="THA_NOI", lai_co_so=Decimal("7"), bien_do=Decimal("4")),
    ]


def _lap(*khoan):
    return lap_bao_cao(_snapshot(*khoan), ngay_bao_cao=_NGAY)


class BaoCaoLaiSuatTests(unittest.TestCase):
    def test_so_tay_binh_quan_xep_hang_va_lai_tra_them(self):
        with localcontext() as ctx:
            ctx.prec = 28
            bc = _lap(*_ba_khoan())
        self.assertEqual(bc["binh_quan_theo_tien_te"]["VND"],
                         Decimal("9.428571428571428571428571429"))
        self.assertEqual(bc["tong_du_no_theo_tien_te"], {"VND": Decimal("700000000")})
        self.assertEqual([k["ma_khoan_vay"] for k in bc["khoan_vay"]],
                         ["DEMO-03", "DEMO-02", "DEMO-01"])
        cao = bc["khoan_vay"][0]
        self.assertEqual(cao["chenh_lech"], Decimal("1.571428571428571428571428571"))
        self.assertEqual(cao["lai_tra_them_uoc_tinh_nam"],
                         Decimal("6285714.285714285714285714284"))
        self.assertTrue(cao["lai_cao"])
        self.assertEqual(cao["don_vi_lai_tra_them"], "VND")
        self.assertIn("ước tính", cao["nhan_lai_tra_them"])
        self.assertEqual(bc["so_khoan_lai_cao"], 1)
        for k in bc["khoan_vay"][1:]:
            self.assertFalse(k["lai_cao"])
            self.assertIsNone(k["lai_tra_them_uoc_tinh_nam"])

    def test_usd_tach_binh_quan_khong_quy_doi(self):
        vnd = _lap(*_ba_khoan())
        bc = _lap(*_ba_khoan(), _khoan("DEMO-USD", tien_te="USD",
                  du_no=Decimal("987654321.25"), lai_suat_nam=Decimal("3.5")))
        self.assertEqual(bc["binh_quan_theo_tien_te"]["VND"], vnd["binh_quan_theo_tien_te"]["VND"])
        self.assertEqual(bc["binh_quan_theo_tien_te"]["USD"], Decimal("3.5"))
        self.assertEqual(bc["tong_du_no_theo_tien_te"]["USD"], Decimal("987654321.25"))
        usd = bc["khoan_vay"][0]
        self.assertEqual(usd["tien_te"], "USD")
        self.assertEqual(usd["chenh_lech"], Decimal(0))
        self.assertFalse(usd["lai_cao"])

    def test_thieu_lai_khong_la_khong_khong_vao_binh_quan(self):
        bc = _lap(*_ba_khoan(), _khoan("DEMO-THIEU", du_no=Decimal("5000000000"),
                                     lai_suat_nam=None))
        self.assertEqual(bc["binh_quan_theo_tien_te"], _lap(*_ba_khoan())["binh_quan_theo_tien_te"])
        self.assertEqual(bc["tong_du_no_theo_tien_te"]["VND"], Decimal("5700000000"))
        thieu = bc["khoan_vay"][-1]
        self.assertEqual(thieu["ma_khoan_vay"], "DEMO-THIEU")
        self.assertEqual(thieu["trang_thai"], "THIEU_DU_LIEU")
        for truong in ("lai_suat_nam", "chenh_lech", "lai_cao", "lai_tra_them_uoc_tinh_nam"):
            self.assertIsNone(thieu[truong])
        self.assertIn("Cần Anh/lead", thieu["ghi_chu"])

    def test_khong_khoan_du_du_lieu_khong_chia_khong(self):
        bc = _lap(_khoan(lai_suat_nam=None), _khoan("DEMO-KHONG", du_no=Decimal(0)))
        self.assertEqual(bc["binh_quan_theo_tien_te"], {"VND": None})
        self.assertEqual(bc["so_khoan_lai_cao"], 0)
        self.assertTrue(all(k["trang_thai"] == "THIEU_DU_LIEU" for k in bc["khoan_vay"]))
        thieu_het = _lap(_khoan(du_no=None))
        self.assertIsNone(thieu_het["tong_du_no_theo_tien_te"]["VND"])
        rong = _lap()
        self.assertEqual(rong["binh_quan_theo_tien_te"], {})
        self.assertEqual(rong["khoan_vay"], [])

    def test_lai_suat_khong_la_so_lieu_hop_le(self):
        bc = _lap(_khoan(lai_suat_nam=Decimal(0)), _khoan("DEMO-02", lai_suat_nam=Decimal("10")))
        self.assertEqual(bc["binh_quan_theo_tien_te"]["VND"], Decimal("5"))
        self.assertEqual(bc["khoan_vay"][-1]["trang_thai"], "DU_DU_LIEU")

    def test_bien_canh_bao_hom_nay_30_31_va_qua_ky(self):
        for so_ngay, mong_doi in ((0, "SAP_DIEU_CHINH"), (30, "SAP_DIEU_CHINH"),
                                  (31, None), (-1, "DA_QUA_KY")):
            with self.subTest(so_ngay=so_ngay):
                ky = _NGAY + timedelta(days=so_ngay)
                # Cảnh báo vẫn có khi khoản thiếu lãi suất.
                bc = _lap(_khoan(ky_dieu_chinh_ke_tiep=ky, lai_suat_nam=None))
                self.assertEqual(bc["khoan_vay"][0]["canh_bao"], [mong_doi] if mong_doi else [])
                self.assertEqual([c["loai"] for c in bc["canh_bao"]], [mong_doi] if mong_doi else [])
                if mong_doi:
                    self.assertEqual(bc["canh_bao"][0]["ky_dieu_chinh_ke_tiep"], ky)
                    self.assertEqual(bc["canh_bao"][0]["ma_khoan_vay"], "DEMO-01")
        self.assertEqual(_lap(_khoan())["canh_bao"], [])

    def test_xep_thieu_cuoi_tung_dong_tien(self):
        bc = _lap(_khoan("DEMO-VND-THIEU", lai_suat_nam=None), *_ba_khoan(),
                  _khoan("DEMO-USD-THIEU", tien_te="USD", du_no=None),
                  _khoan("DEMO-USD-DU", tien_te="USD"))
        self.assertEqual([k["ma_khoan_vay"] for k in bc["khoan_vay"]], [
            "DEMO-USD-DU", "DEMO-USD-THIEU", "DEMO-03", "DEMO-02", "DEMO-01", "DEMO-VND-THIEU",
        ])

    def test_so_sai_kieu_khong_huu_han_du_no_am_deu_khong_tinh(self):
        for du_no, lai in ((Decimal("-1"), Decimal("6")), (1.5, Decimal("6")),
                           (Decimal("NaN"), Decimal("6")), (Decimal("Infinity"), Decimal("6")),
                           (Decimal("100"), Decimal("sNaN")), (Decimal("100"), "6"),
                           (Decimal("100"), 6.0)):
            with self.subTest(du_no=du_no, lai=lai):
                bc = _lap(_khoan(du_no=du_no, lai_suat_nam=lai))
                self.assertIsNone(bc["binh_quan_theo_tien_te"]["VND"])
                self.assertIsNone(bc["khoan_vay"][0]["lai_cao"])

    def test_thieu_tien_te_khong_doan_vnd(self):
        bc = _lap(_khoan(tien_te=None))
        self.assertEqual(bc["binh_quan_theo_tien_te"], {})
        self.assertEqual(bc["tong_du_no_theo_tien_te"], {})
        self.assertEqual(bc["khoan_vay"][0]["trang_thai"], "THIEU_DU_LIEU")

    def test_nguon_va_moc_bat_buoc_khong_tu_dien(self):
        for thay in ({"nguon": None}, {"nguon": "Hợp đồng DEMO"}, {"moc": None},
                     {"moc": "1/1/2026 8:30"}, {"moc": "31/02/2026 08:30"},
                     {"khoan_vay": None}):
            with self.subTest(thay=thay):
                with self.assertRaisesRegex(ValueError, "Cần Anh/lead"):
                    lap_bao_cao({**_snapshot(_khoan()), **thay}, ngay_bao_cao=_NGAY)

    def test_moc_nguon_ngay_va_dau_vao_khong_bi_sua(self):
        snapshot = _snapshot(*_ba_khoan())
        truoc = deepcopy(snapshot)
        bc = lap_bao_cao(snapshot, ngay_bao_cao=_NGAY)
        self.assertEqual(snapshot, truoc)
        self.assertEqual((bc["moc"], bc["nguon"], bc["ngay_bao_cao"]), (_MOC, "Sheet", _NGAY))
        for k in bc["khoan_vay"]:
            self.assertEqual(k["dieu_khoan_lien_quan_toi_dam_phan"], "")
            self.assertIn("chờ nối trích dẫn hợp đồng (M9-2)", k["ghi_chu"])

    def test_ngay_sai_kieu_danh_dau_can_lead(self):
        bc = _lap(_khoan(ky_dieu_chinh_ke_tiep="26/10/2026"))
        self.assertEqual(bc["canh_bao"], [])
        self.assertIn("chuẩn hóa ky_dieu_chinh_ke_tiep", bc["can_anh"][0])
        with self.assertRaises(ValueError):
            lap_bao_cao(_snapshot(_khoan()), ngay_bao_cao=datetime(2026, 10, 26))

    def test_khong_float_de_quy(self):
        bc = _lap(*_ba_khoan(), _khoan("DEMO-FLOAT", du_no=1.5, lai_co_so=4.5,
                  bien_do=0.5, du_lieu_ngoai={"float": 1.2}))

        def duyet(v):
            self.assertNotIsInstance(v, float)
            if isinstance(v, dict):
                for khoa, gia_tri in v.items():
                    duyet(khoa)
                    duyet(gia_tri)
            elif isinstance(v, (list, tuple)):
                for gia_tri in v:
                    duyet(gia_tri)

        duyet(bc)


class XuatExcelTests(unittest.TestCase):
    def _doc(self, bc):
        raw = xuat_excel(bc)
        self.assertIsInstance(raw, bytes)
        wb = load_workbook(BytesIO(raw), data_only=False)
        self.addCleanup(wb.close)
        self.assertEqual(len(wb.worksheets), 1)
        ws = wb.active
        dong = next(o.row for hang in ws for o in hang if o.value == "Mã khoản vay")
        cot = {o.value: o.column for o in ws[dong] if o.value is not None}
        return ws, dong, cot

    def test_excel_tieu_de_so_ngay_khong_cong_thuc(self):
        bc = _lap(*_ba_khoan(), _khoan("DEMO-THIEU", lai_suat_nam=None))
        truoc = deepcopy(bc)
        ws, dong, cot = self._doc(bc)
        self.assertEqual(bc, truoc)
        self.assertEqual(ws["A2"].value, "Nguồn: Sheet theo dõi khoản vay, mốc " + _MOC)
        self.assertEqual(ws["B3"].number_format, "dd/mm/yyyy")
        self.assertEqual(ws["B3"].value.date(), _NGAY)
        for ten in ("Dư nợ (đồng tiền)", "Lãi trả thêm ước tính một năm (đồng tiền)"):
            o = ws.cell(dong + 1, cot[ten])
            self.assertEqual(o.data_type, "n")
            self.assertIsInstance(o.value, (int, float))
            self.assertEqual(o.number_format, "#,##0")
        self.assertEqual(ws.cell(dong + 1, cot["Dư nợ (đồng tiền)"]).value, 400000000)
        self.assertEqual(ws.cell(dong + 1, cot["Lãi trả thêm ước tính một năm (đồng tiền)"]).value, 6285714)
        o_ngay = ws.cell(dong + 1, cot["Ngày đáo hạn"])
        self.assertEqual(o_ngay.value.date(), date(2027, 10, 26))
        self.assertEqual(o_ngay.number_format, "dd/mm/yyyy")
        for hang in ws:
            for o in hang:
                self.assertNotEqual(o.data_type, "f")
        self.assertIsNone(ws.cell(dong + 4, cot["Lãi suất áp dụng (%/năm)"]).value)
        self.assertIsNone(ws.cell(dong + 1, cot["Điều khoản liên quan tới đàm phán"]).value)
        self.assertIn("chờ nối trích dẫn hợp đồng (M9-2)", ws.cell(dong + 1, cot["Ghi chú"]).value)
        self.assertEqual(ws.cell(ws.max_row, 1).value,
                         "Lãi trả thêm là ước tính; không gửi ra ngoài khi chưa duyệt.")

    def test_excel_lam_tron_vnd_usd_half_up_chi_khi_xuat(self):
        bc = _lap(_khoan("DEMO-VND", du_no=Decimal("100.5")),
                  _khoan("DEMO-USD", tien_te="USD", du_no=Decimal("100.125")))
        ws, dong, cot = self._doc(bc)
        self.assertEqual(ws.cell(dong + 1, cot["Dư nợ (đồng tiền)"]).value, 100.13)
        self.assertEqual(ws.cell(dong + 1, cot["Dư nợ (đồng tiền)"]).number_format, "#,##0.00")
        self.assertEqual(ws.cell(dong + 2, cot["Dư nợ (đồng tiền)"]).value, 101)
        self.assertEqual(bc["khoan_vay"][0]["du_no"], Decimal("100.125"))
        self.assertEqual(bc["khoan_vay"][1]["du_no"], Decimal("100.5"))

    def test_excel_usd_lai_tra_them_co_don_vi_va_ngay_dieu_chinh(self):
        bc = _lap(_khoan("DEMO-USD-1", tien_te="USD", du_no=Decimal("100.25"),
                        lai_suat_nam=Decimal("6"), ky_dieu_chinh_ke_tiep=_NGAY),
                  _khoan("DEMO-USD-2", tien_te="USD", du_no=Decimal("100.25"),
                        lai_suat_nam=Decimal("4")))
        ws, dong, cot = self._doc(bc)
        self.assertEqual(bc["khoan_vay"][0]["lai_tra_them_uoc_tinh_nam"], Decimal("1.0025"))
        self.assertEqual(ws.cell(dong + 1, cot["Đồng tiền"]).value, "USD")
        self.assertEqual(ws.cell(dong + 1, cot["Lãi trả thêm ước tính một năm (đồng tiền)"]).value, 1)
        o = ws.cell(dong + 1, cot["Kỳ điều chỉnh kế tiếp"])
        self.assertEqual(o.value.date(), _NGAY)
        self.assertEqual(o.number_format, "dd/mm/yyyy")
        self.assertEqual(ws.cell(dong + 1, cot["Cảnh báo"]).value, "SAP_DIEU_CHINH")

    def test_excel_ten_bat_dau_dau_bang_la_van_ban(self):
        bc = _lap(_khoan(phap_nhan='=HYPERLINK("DEMO")', ngan_hang="#N/A",
                        ma_khoan_vay="=1+1"))
        ws, dong, cot = self._doc(bc)
        self.assertEqual(ws.cell(dong + 1, cot["Mã khoản vay"]).value, "=1+1")
        for hang in ws:
            for o in hang:
                self.assertNotEqual(o.data_type, "f")
                if isinstance(o.value, str):
                    self.assertEqual(o.data_type, "s")

    def test_excel_rong_thieu_het_va_dong_tien_chua_chot(self):
        for bc in (_lap(), _lap(_khoan(du_no=None, lai_suat_nam=None)),
                   _lap(_khoan(tien_te="DEMO", du_no=Decimal("123.4567")))):
            with self.subTest(tien=list(bc["binh_quan_theo_tien_te"])):
                ws, _, _ = self._doc(bc)
                self.assertIn(_MOC, ws["A2"].value)
        self.assertTrue(any("chốt số lẻ tiền DEMO" in s for s in bc["can_anh"]))


if __name__ == "__main__":
    unittest.main()
