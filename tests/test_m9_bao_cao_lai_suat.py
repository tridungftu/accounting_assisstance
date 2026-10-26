"""M9-4a/b: DEMO giả, tính thuần, trích hợp đồng và đọc Excel trong bộ nhớ."""

from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal, localcontext
from io import BytesIO
import unittest
from unittest.mock import call, patch

from openpyxl import load_workbook

from kho_tri_thuc.m9.bao_cao_lai_suat import lap_bao_cao, xuat_excel
from kho_tri_thuc.m9.chi_muc_vay import ChiMucVay


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


def _kiem_cau_trung_tinh(test, cau):
    test.assertNotIn("cần anh", cau.lower())
    test.assertNotIn("lead", cau.lower())
    test.assertNotIn("_", cau)
    test.assertNotIn("M9-2", cau)


_CHU_DE = ("biên độ lãi suất", "điều chỉnh lãi suất", "phí trả nợ trước hạn")
_CAU_DEMO = (
    "Biên độ lãi suất DEMO là 2,75%/năm; giữ NGUYÊN chữ gốc.",
    "Điều chỉnh lãi suất DEMO định kỳ 03 tháng một lần.",
    '=Phí trả nợ trước hạn DEMO là 1,25% số tiền trả trước; "nguyên văn".',
)


def _chi_muc_demo():
    chi_muc = ChiMucVay()
    for ma, ten, cac_cau in (
            ("HD-DEMO-A", "Hợp đồng DEMO A.docx", _CAU_DEMO),
            ("HD-DEMO-B", "Hợp đồng DEMO B.docx", _CAU_DEMO[:2]),
            ("HD-DEMO-KHAC", "Hợp đồng DEMO khác.docx", (
                "Biên độ lãi suất khoản KHÁC là 99%/năm.",
                "Điều chỉnh lãi suất khoản KHÁC mỗi ngày.",
                "Phí trả nợ trước hạn khoản KHÁC là 99%.",
            ))):
        chi_muc.them(ma, ten, [
            {"trang_dau": i + 2, "trang_cuoi": i + 3,
             "dieu": str(i + 4), "khoan": str(i + 1), "diem": None,
             "ma_doan": f"DEMO-{i}", "cau": [cau]}
            for i, cau in enumerate(cac_cau)
        ])
    return chi_muc


def _lap_co_trich_dan(*khoan):
    return lap_bao_cao(
        _snapshot(*khoan), ngay_bao_cao=_NGAY, chi_muc=_chi_muc_demo(),
        tai_lieu_theo_khoan_vay={"DEMO-01": {"HD-DEMO-A"}, "DEMO-02": {"HD-DEMO-B"}},
    )


class TrichDanHopDongTests(unittest.TestCase):
    def test_du_ba_chu_de_nguyen_van_va_nguon_khong_sua_dau_vao(self):
        chi_muc = _chi_muc_demo()
        snapshot = _snapshot(_khoan())
        anh_xa = {"DEMO-01": {"HD-DEMO-A"}}
        truoc = deepcopy((snapshot, anh_xa, chi_muc.to_dict()))
        bc = lap_bao_cao(snapshot, ngay_bao_cao=_NGAY, chi_muc=chi_muc,
                         tai_lieu_theo_khoan_vay=anh_xa)
        self.assertEqual((snapshot, anh_xa, chi_muc.to_dict()), truoc)
        k = bc["khoan_vay"][0]
        self.assertEqual(k["dieu_khoan_lien_quan_toi_dam_phan"], [
            {"chu_de": chu_de, "ten_tep": "Hợp đồng DEMO A.docx",
             "trang": f"{i + 2}-{i + 3}", "dieu": str(i + 4),
             "khoan": str(i + 1), "cau": _CAU_DEMO[i]}
            for i, chu_de in enumerate(_CHU_DE)
        ])
        self.assertEqual(k["ghi_chu"], "")
        # Chỉ thêm trích dẫn, không suy số từ tỷ lệ ghi trong hợp đồng.
        cu = _lap(_khoan())["khoan_vay"][0]
        for truong in cu.keys() - {"ghi_chu", "dieu_khoan_lien_quan_toi_dam_phan"}:
            self.assertEqual(k[truong], cu[truong])

    def test_thieu_phi_va_khong_lay_cau_tu_hop_dong_khac(self):
        bc = _lap_co_trich_dan(_khoan(), _khoan("DEMO-02"))
        k = next(k for k in bc["khoan_vay"] if k["ma_khoan_vay"] == "DEMO-02")
        muc = k["dieu_khoan_lien_quan_toi_dam_phan"]
        self.assertEqual([m["cau"] for m in muc[:2]], list(_CAU_DEMO[:2]))
        self.assertTrue(all(m["ten_tep"] == "Hợp đồng DEMO B.docx" for m in muc[:2]))
        self.assertEqual(muc[2], {
            "chu_de": "phí trả nợ trước hạn", "ten_tep": None, "trang": None,
            "dieu": None, "khoan": None, "cau": "Không thấy trong hợp đồng",
        })

    def test_dung_ba_truy_van_moi_khoan_toi_da_mot_cau(self):
        chi_muc = _chi_muc_demo()
        anh_xa = {"DEMO-01": {"HD-DEMO-A"}, "DEMO-02": {"HD-DEMO-B"}}
        with patch.object(chi_muc, "tim", wraps=chi_muc.tim) as tim:
            lap_bao_cao(_snapshot(_khoan(), _khoan("DEMO-02")),
                         ngay_bao_cao=_NGAY, chi_muc=chi_muc,
                         tai_lieu_theo_khoan_vay=anh_xa)
        self.assertEqual(tim.call_args_list, [
            call(chu_de, so_ket_qua=1, loc_tai_lieu=anh_xa[ma])
            for ma in ("DEMO-01", "DEMO-02") for chu_de in _CHU_DE
        ])

    def test_anh_xa_rong_thieu_ma_rong_id_va_id_khong_ton_tai_khong_tim_toan_bo(self):
        for anh_xa in ({}, {"DEMO-KHAC": {"HD-DEMO-KHAC"}},
                        {"DEMO-01": set()}, {"DEMO-01": {"KHONG-CO"}}):
            with self.subTest(anh_xa=anh_xa):
                chi_muc = _chi_muc_demo()
                with patch.object(chi_muc, "tim", wraps=chi_muc.tim) as tim:
                    bc = lap_bao_cao(_snapshot(_khoan()), ngay_bao_cao=_NGAY,
                                     chi_muc=chi_muc, tai_lieu_theo_khoan_vay=anh_xa)
                self.assertEqual(tim.call_count, 3)
                muc = bc["khoan_vay"][0]["dieu_khoan_lien_quan_toi_dam_phan"]
                self.assertEqual([m["cau"] for m in muc], ["Không thấy trong hợp đồng"] * 3)
                self.assertTrue(all(m["ten_tep"] is None for m in muc))

    def test_thieu_mot_tham_so_giu_nguyen_toan_bo_bao_cao_cu(self):
        snapshot = _snapshot(*_ba_khoan(), _khoan("DEMO-THIEU", lai_suat_nam=None))
        cu = lap_bao_cao(snapshot, ngay_bao_cao=_NGAY)
        for tham_so in ({"chi_muc": _chi_muc_demo()},
                         {"tai_lieu_theo_khoan_vay": {"DEMO-01": {"HD-DEMO-A"}}},
                         {"chi_muc": None, "tai_lieu_theo_khoan_vay": None}):
            with self.subTest(tham_so=tham_so):
                self.assertEqual(lap_bao_cao(snapshot, ngay_bao_cao=_NGAY, **tham_so), cu)


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
        self.assertIn("Thiếu dữ liệu: lãi suất.", thieu["ghi_chu"])

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
        for thay, cau in (
                ({"nguon": None}, "Chỉ nhận dữ liệu từ Sheet có mốc thời gian."),
                ({"nguon": "Hợp đồng DEMO"}, "Chỉ nhận dữ liệu từ Sheet có mốc thời gian."),
                ({"moc": None}, "Mốc dữ liệu phải có dạng dd/mm/yyyy hh:mm."),
                ({"moc": "1/1/2026 8:30"}, "Mốc dữ liệu phải có dạng dd/mm/yyyy hh:mm."),
                ({"moc": "31/02/2026 08:30"}, "Mốc dữ liệu phải có dạng dd/mm/yyyy hh:mm."),
                ({"khoan_vay": None}, "Thiếu danh sách khoản vay đã chuẩn hóa."),
                ({"khoan_vay": [None]}, "Dữ liệu khoản vay chưa đúng cấu trúc đã chuẩn hóa.")):
            with self.subTest(thay=thay):
                with self.assertRaises(ValueError) as loi:
                    lap_bao_cao({**_snapshot(_khoan()), **thay}, ngay_bao_cao=_NGAY)
                self.assertEqual(str(loi.exception), cau)
                _kiem_cau_trung_tinh(self, str(loi.exception))

    def test_moc_nguon_ngay_va_dau_vao_khong_bi_sua(self):
        snapshot = _snapshot(*_ba_khoan())
        truoc = deepcopy(snapshot)
        bc = lap_bao_cao(snapshot, ngay_bao_cao=_NGAY)
        self.assertEqual(snapshot, truoc)
        self.assertEqual((bc["moc"], bc["nguon"], bc["ngay_bao_cao"]), (_MOC, "Sheet", _NGAY))
        for k in bc["khoan_vay"]:
            self.assertEqual(k["dieu_khoan_lien_quan_toi_dam_phan"], "")
            self.assertIn("Chờ bổ sung trích dẫn hợp đồng.", k["ghi_chu"])

    def test_ngay_sai_kieu_danh_dau_can_xem_lai(self):
        for truong, nhan in (("ky_dieu_chinh_ke_tiep", "Ngày kỳ điều chỉnh kế tiếp"),
                             ("ngay_dao_han", "Ngày đáo hạn")):
            with self.subTest(truong=truong):
                bc = _lap(_khoan(**{truong: "26/10/2026"}))
                self.assertEqual(bc["canh_bao"], [])
                self.assertEqual(bc["can_xem_lai"], [nhan + " chưa đúng định dạng ngày."])
                _kiem_cau_trung_tinh(self, bc["can_xem_lai"][0])
        with self.assertRaises(ValueError) as loi:
            lap_bao_cao(_snapshot(_khoan()), ngay_bao_cao=datetime(2026, 10, 26))
        self.assertEqual(str(loi.exception), "Ngày báo cáo chưa đúng định dạng ngày.")
        _kiem_cau_trung_tinh(self, str(loi.exception))

    def test_cau_hien_trong_ket_qua_trung_tinh_va_khong_giu_khoa_cu(self):
        for bc in (
                _lap(), _lap(*_ba_khoan()),
                _lap(_khoan(tien_te=None, du_no=None, lai_suat_nam=None,
                            ky_dieu_chinh_ke_tiep="26/10/2026", ngay_dao_han="27/10/2026")),
                _lap(_khoan(tien_te="DEMO")),
                _lap_co_trich_dan(_khoan(du_no=None, lai_suat_nam=None))):
            with self.subTest(bc=bc):
                self.assertNotIn("can_anh", bc)
                for cau in [bc["ghi_chu"], *bc["can_xem_lai"]]:
                    _kiem_cau_trung_tinh(self, cau)
                for k in bc["khoan_vay"]:
                    # Các mã nội bộ và danh sách trường thiếu vẫn giữ nguyên.
                    _kiem_cau_trung_tinh(self, k["ghi_chu"])
                    _kiem_cau_trung_tinh(self, k["nhan_lai_tra_them"])
        thieu = _lap_co_trich_dan(_khoan(du_no=None, lai_suat_nam=None))
        self.assertEqual(thieu["khoan_vay"][0]["ghi_chu"],
                         "Thiếu dữ liệu: dư nợ dương, lãi suất.")
        self.assertEqual(thieu["khoan_vay"][0]["thieu_truong"], ["du_no > 0", "lai_suat_nam"])

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
        for hang in ws:
            for o in hang:
                if isinstance(o.value, str):
                    _kiem_cau_trung_tinh(self, o.value)
        dong = next(o.row for hang in ws for o in hang if o.value == "Mã khoản vay")
        cot = {o.value: o.column for o in ws[dong] if o.value is not None}
        return ws, dong, cot

    def test_excel_dieu_khoan_nguyen_van_co_trich_dan_va_khong_cong_thuc(self):
        bc = _lap_co_trich_dan(_khoan(), _khoan("DEMO-02"))
        truoc = deepcopy(bc)
        ws, dong, cot = self._doc(bc)
        self.assertEqual(bc, truoc)
        for i, (ma, ten) in enumerate((("DEMO-01", "A"), ("DEMO-02", "B")), 1):
            self.assertEqual(ws.cell(dong + i, cot["Mã khoản vay"]).value, ma)
            mong_doi = []
            for j, chu_de in enumerate(_CHU_DE):
                if ten == "B" and j == 2:
                    mong_doi.append(chu_de + ": Không thấy trong hợp đồng")
                else:
                    mong_doi.append(
                        f"{chu_de}: {_CAU_DEMO[j]} (Hợp đồng DEMO {ten}.docx, "
                        f"trang {j + 2}-{j + 3}, Điều {j + 4}, Khoản {j + 1})")
            o = ws.cell(dong + i, cot["Điều khoản liên quan tới đàm phán"])
            self.assertEqual(o.value, "\n".join(mong_doi))
            self.assertEqual(o.data_type, "s")
        for hang in ws:
            for o in hang:
                self.assertNotEqual(o.data_type, "f")
                if isinstance(o.value, str):
                    self.assertNotIn("Chờ bổ sung trích dẫn hợp đồng.", o.value)

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
        self.assertIn("Chờ bổ sung trích dẫn hợp đồng.", ws.cell(dong + 1, cot["Ghi chú"]).value)
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
        self.assertEqual(ws.cell(dong + 1, cot["Cảnh báo"]).value, "Sắp đến kỳ điều chỉnh")

    def test_excel_ngay_sai_qua_ky_va_thieu_du_lieu_dung_nhan_tieng_viet(self):
        bc = _lap(_khoan(du_no=None, lai_suat_nam=None,
                         ky_dieu_chinh_ke_tiep=_NGAY - timedelta(days=1),
                         ngay_dao_han="27/10/2026"))
        ws, dong, cot = self._doc(bc)
        self.assertEqual(ws.cell(dong + 1, cot["Trạng thái"]).value, "Thiếu dữ liệu")
        self.assertEqual(ws.cell(dong + 1, cot["Cảnh báo"]).value, "Đã quá kỳ điều chỉnh")
        self.assertIn("Ngày đáo hạn chưa đúng định dạng ngày.",
                      ws.cell(dong + 1, cot["Ghi chú"]).value)
        self.assertEqual(bc["khoan_vay"][0]["canh_bao"], ["DA_QUA_KY"])

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
        self.assertEqual(bc["can_xem_lai"], [
            "Chưa có quy tắc làm tròn cho đồng tiền DEMO; số xuất chưa làm tròn.",
        ])


if __name__ == "__main__":
    unittest.main()
