"""Chỉ mục hợp đồng DEMO trong bộ nhớ, không dùng dữ liệu thật."""

import io
import json
import math
from pathlib import Path
import unicodedata
import unittest
import zipfile
from xml.sax.saxutils import escape

from kho_tri_thuc.m9.chi_muc_vay import KHONG_THAY, ChiMucVay, chuan_hoa
from kho_tri_thuc.m9.tai_lieu_vay import cat_doan, doc_docx


def _p(chu):
    return '<w:p><w:r><w:t>' + escape(chu) + '</w:t></w:r></w:p>'


def _demo():
    noi_dung = (
        _p("HỢP ĐỒNG VAY DEMO")
        + _p("Điều 1. Hạn mức DEMO")
        + _p("1. Số tiền vay là 1.000.000.000 VND ngày 01.02.2026.")
        + '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
        + _p("Điều 2. Lãi suất DEMO")
        + _p("1. Lãi suất cho vay là 8,5%/năm.")
        + _p("2. Kỳ điều chỉnh định kỳ sáu tháng.")
        + _p("Điều 3. Thanh toán DEMO")
        + _p("1. Bên vay trả nợ đúng hạn.")
        + _p("2. Phí trả nợ trước hạn là 2% số tiền trả trước.")
        + _p("a) Phí được thanh toán tại ngân hàng DEMO;")
        + _p("Giữ nguyên CÂU trích dẫn DEMO!")
    )
    bo_dem = io.BytesIO()
    with zipfile.ZipFile(bo_dem, "w", zipfile.ZIP_DEFLATED) as tep:
        tep.writestr("word/document.xml", (
            '<w:document xmlns:w="http://schemas.openxmlformats.org/'
            'wordprocessingml/2006/main"><w:body>'
            + noi_dung + '</w:body></w:document>'
        ))
    return cat_doan(doc_docx(bo_dem.getvalue()))


def _doan(cac_cau, *, trang_dau=1, trang_cuoi=1):
    return [{"trang_dau": trang_dau, "trang_cuoi": trang_cuoi,
             "dieu": "1. DEMO", "khoan": "2", "diem": "a",
             "ma_doan": "doan-DEMO", "cau": cac_cau}]


class ChuanHoaTests(unittest.TestCase):
    def test_tieng_viet_va_ky_tu_phan_cach(self):
        self.assertEqual(chuan_hoa("LÃI SUẤT_Đồng-vay, ABC123!"),
                         ["lai", "suat", "dong", "vay", "abc123"])
        self.assertEqual(chuan_hoa(unicodedata.normalize("NFD", "ĐẦU TƯ")),
                         ["dau", "tu"])

    def test_so_tien_ngay_ty_le(self):
        self.assertEqual(chuan_hoa("1.000.000.000; 01.02.2026; 8,5%."),
                         ["1.000.000.000", "01.02.2026", "8,5"])
        self.assertEqual(chuan_hoa("01/02/2026 2026-02-01 1000 VND"),
                         ["01/02/2026", "2026-02-01", "1000", "vnd"])

    def test_rong(self):
        self.assertEqual(chuan_hoa(" \n_%!?"), [])


class ChiMucVayTests(unittest.TestCase):
    def setUp(self):
        self.doan = _demo()
        self.chi_muc = ChiMucVay()
        self.chi_muc.them("DEMO-A", "DEMO-A.docx", self.doan)

    def test_lai_suat_co_va_khong_dau(self):
        co_dau = self.chi_muc.tim("lãi suất cho vay")
        self.assertEqual(co_dau, self.chi_muc.tim("lai suat cho vay"))
        self.assertTrue(co_dau)
        self.assertEqual(co_dau[0]["trich_dan"], {
            "ten_tep": "DEMO-A.docx", "trang": 2,
            "dieu": "2. Lãi suất DEMO", "khoan": "1", "diem": None,
            "cau": "1. Lãi suất cho vay là 8,5%/năm.",
        })
        self.assertEqual(co_dau[0]["tai_lieu_id"], "DEMO-A")
        self.assertIsInstance(co_dau[0]["diem"], float)

    def test_phi_tra_no_truoc_han(self):
        muc = self.chi_muc.tim("phí trả nợ trước hạn")[0]
        self.assertEqual(muc["trich_dan"]["khoan"], "2")
        self.assertEqual(muc["trich_dan"]["dieu"], "3. Thanh toán DEMO")
        self.assertEqual(muc["cau"], "2. Phí trả nợ trước hạn là 2% số tiền trả trước.")

    def test_chu_de_khong_co_va_chi_khop_tu_roi_rac(self):
        for hoi in ("thời tiết ngày mai", "bảo hiểm cháy nổ",
                    "vay bảo hiểm cháy nổ"):
            with self.subTest(hoi=hoi):
                self.assertEqual(self.chi_muc.tim(hoi), [])
        self.assertEqual(KHONG_THAY, "Không thấy trong hợp đồng.")

    def test_cau_hoi_tu_nhien_co_va_khong_dau(self):
        self.chi_muc.them("DEMO-TS", "DEMO-TS.docx", _doan([
            "Tài sản bảo đảm là nhà ở DEMO.",
        ]))
        for hoi, dieu, khoan in (
            ("Hỏi: phí trả nợ trước hạn bao nhiêu phần trăm vậy?", "3. Thanh toán DEMO", "2"),
            ("phi tra no truoc han bao nhieu phan tram?", "3. Thanh toán DEMO", "2"),
            ("cho hỏi lãi suất là bao nhiêu", "2. Lãi suất DEMO", "1"),
            ("cho hoi lai suat la bao nhieu", "2. Lãi suất DEMO", "1"),
            ("bao lâu thì điều chỉnh lãi một lần", "2. Lãi suất DEMO", "2"),
            ("bao lau thi dieu chinh lai mot lan", "2. Lãi suất DEMO", "2"),
            ("tài sản bảo đảm là gì vậy?", "1. DEMO", "2"),
            ("tai san bao dam la gi", "1. DEMO", "2"),
        ):
            with self.subTest(hoi=hoi):
                ket_qua = self.chi_muc.tim(hoi)
                self.assertTrue(ket_qua)
                self.assertEqual(ket_qua[0]["trich_dan"]["dieu"], dieu)
                self.assertEqual(ket_qua[0]["trich_dan"]["khoan"], khoan)
                self.assertIsNotNone(ket_qua[0]["khoan"])

    def test_lai_qua_han_khong_lay_lai_trong_han(self):
        for hoi in ("lãi suất quá hạn là bao nhiêu", "lai suat qua han la bao nhieu"):
            with self.subTest(hoi=hoi):
                self.assertEqual(self.chi_muc.tim(hoi), [])
        doan = cat_doan([
            {"trang": 1, "thu_tu": 1, "van_ban": "Điều 2. Lãi suất"},
            {"trang": 1, "thu_tu": 2, "van_ban": "1. Lãi suất cho vay là 8,5%/năm."},
            {"trang": 1, "thu_tu": 3,
             "van_ban": "2. Lãi suất quá hạn bằng 150% lãi suất trong hạn."},
        ])
        self.chi_muc.them("DEMO-A", "DEMO-A.docx", doan)
        for hoi in ("lãi suất quá hạn là bao nhiêu", "lai suat qua han la bao nhieu"):
            with self.subTest(hoi=hoi):
                ket_qua = self.chi_muc.tim(hoi)
                self.assertEqual(len(ket_qua), 1)
                self.assertEqual(ket_qua[0]["khoan"], "2")
                self.assertEqual(ket_qua[0]["cau"], doan[2]["cau"][0])

    def test_nguong_phai_lon_hon_mot_nua_ke_ca_ngu_canh(self):
        chi_muc = ChiMucVay()
        doan = _doan(["Phí."])
        doan[0]["dieu"] = "1. Lãi suất"
        chi_muc.them("DEMO", "DEMO.docx", doan)
        self.assertEqual(chi_muc.tim("lãi suất quá hạn"), [])
        self.assertTrue(chi_muc.tim("lãi suất quá"))
        self.assertEqual(chi_muc.tim("phí bảo hiểm cháy"), [])

    def test_giu_ca_hai_tu_phan_biet_nghia(self):
        for cum in ("quá hạn", "trước hạn", "trong hạn", "cố định", "thả nổi", "ân hạn"):
            khong_dau = " ".join(chuan_hoa(cum))
            for hoi in (cum, khong_dau,
                        "cho hỏi " + cum + " là gì vậy?",
                        "cho hoi " + khong_dau + " la gi?"):
                with self.subTest(cum=cum, hoi=hoi):
                    chi_muc = ChiMucVay()
                    chi_muc.them("DEMO", "DEMO.docx", _doan([cum + "."]))
                    self.assertTrue(chi_muc.tim(hoi))
                    for tu in cum.split():
                        chi_muc.them("DEMO", "DEMO.docx", _doan([tu + "."]))
                        self.assertEqual(chi_muc.tim(hoi), [])

    def test_co_chi_duoc_giu_khi_la_tu_khong_dau_trong_cap_nghiep_vu(self):
        chi_muc = ChiMucVay()
        chi_muc.them("DEMO", "DEMO.docx", _doan(["Định."]))
        for hoi in ("co dinh", "co định", "CHO HOI CO DINH LA GI?",
                    "cho hoi co co dinh la gi"):
            with self.subTest(hoi=hoi):
                self.assertEqual(chi_muc.tim(hoi), [])
        self.assertEqual(chi_muc.tim("co"), [])
        for hoi in ("co la dinh", "dinh co", "có định", "có dinh"):
            with self.subTest(hoi=hoi):
                self.assertEqual(chi_muc.tim(hoi), chi_muc.tim("định"))
        chi_muc.them("DEMO", "DEMO.docx", _doan(["Cố định."]))
        for hoi in ("co dinh", "co định", "CHO HOI CO DINH LA GI?",
                    "cho hoi co co dinh la gi"):
            with self.subTest(hoi=hoi):
                self.assertEqual(chi_muc.tim(hoi), chi_muc.tim("cố định"))

    def test_tieu_de_dieu_chuong_chi_la_ngu_canh_va_json_giu_nguyen(self):
        doan = cat_doan([
            {"trang": 1, "thu_tu": 1, "van_ban": "Chương I. Tín dụng"},
            {"trang": 1, "thu_tu": 2, "van_ban": "Điều 2. Lãi suất"},
            {"trang": 1, "thu_tu": 3, "van_ban": "1. Kỳ điều chỉnh là sáu tháng."},
            {"trang": 1, "thu_tu": 4, "van_ban": "2. Áp dụng cố định trong kỳ."},
        ])
        # Kiểm tra cả câu tiêu đề chỉ còn phần chữ sau nhãn.
        doan[0]["cau"].append("Tín dụng")
        doan[1]["cau"].append("Lãi suất")
        chi_muc = ChiMucVay()
        chi_muc.them("DEMO", "DEMO.docx", doan)
        for hoi in ("lãi suất", "tín dụng", "điều chỉnh lãi", "cố định lãi suất"):
            with self.subTest(hoi=hoi):
                ket_qua = chi_muc.tim(hoi, so_ket_qua=100)
                self.assertTrue(ket_qua)
                self.assertTrue(all(m["khoan"] is not None for m in ket_qua))
                self.assertTrue(all(m["cau"] in (doan[2]["cau"] + doan[3]["cau"])
                                    for m in ket_qua))
                moi = ChiMucVay.from_dict(json.loads(json.dumps(chi_muc.to_dict())))
                self.assertEqual(moi.tim(hoi, so_ket_qua=100), ket_qua)
        self.assertEqual(len(chi_muc.tim("lãi suất")), 2)

    def test_tu_cua_cau_co_trong_so_cao_hon_tieu_de(self):
        chi_muc = ChiMucVay()
        doan = _doan(["Nội dung.", "Lãi suất."])
        doan[0]["dieu"] = "1. Lãi suất"
        chi_muc.them("DEMO", "DEMO.docx", doan)
        ket_qua = chi_muc.tim("lãi suất")
        self.assertEqual([m["cau"] for m in ket_qua], ["Nội dung."])
        # Câu trùng hoàn toàn tiêu đề bị loại; thêm từ để là câu nội dung.
        doan[0]["cau"] = ["Nội dung khác.", "Lãi suất khác."]
        chi_muc.them("DEMO", "DEMO.docx", doan)
        ket_qua = chi_muc.tim("lãi suất")
        self.assertEqual([m["cau"] for m in ket_qua], ["Lãi suất khác.", "Nội dung khác."])
        self.assertGreater(ket_qua[0]["diem"], ket_qua[1]["diem"])

    def test_dung_ca_lead_khoan_7_2_va_khong_doi_chi_muc(self):
        chi_muc = ChiMucVay()
        doan = _doan(["Phí trả nợ trước hạn là 1% trên số tiền trả trước."])
        doan[0].update(dieu="7. DEMO", khoan="2")
        chi_muc.them("DEMO", "DEMO.docx", doan)
        truoc = chi_muc.to_dict()
        hoi = "Hỏi: phí trả nợ trước hạn bao nhiêu phần trăm vậy?"
        ket_qua = chi_muc.tim(hoi)
        self.assertTrue(ket_qua)
        self.assertEqual(ket_qua[0]["trich_dan"]["dieu"], "7. DEMO")
        self.assertEqual(ket_qua[0]["trich_dan"]["khoan"], "2")
        self.assertEqual(ket_qua[0]["trich_dan"]["cau"], doan[0]["cau"][0])
        self.assertEqual(chi_muc.to_dict(), truoc)
        self.assertEqual(ChiMucVay.from_dict(truoc).tim(hoi), ket_qua)
        self.assertEqual(chi_muc.tim("1%"), chi_muc.tim("1"))

    def test_cau_hoi_tu_nhien_chu_de_khong_co(self):
        for hoi in (
            "ngân hàng có được đơn phương tăng lãi không",
            "ngan hang co duoc don phuong tang lai khong",
            "phạt chậm nộp báo cáo tài chính",
            "cho hỏi bảo hiểm cháy nổ là gì vậy",
        ):
            with self.subTest(hoi=hoi):
                self.assertEqual(self.chi_muc.tim(hoi), [])

    def test_chi_hu_tu_va_vay_khong_thanh_vay(self):
        for hoi in (
            "hỏi cho hỏi là gì nào bao nhiêu bao lâu mấy có không được chưa vậy",
            "thì của theo như thế nào thế nào khi nào ở đâu ai tôi mình ạ nhé à hả phần trăm",
            "hoi cho hoi la gi nao bao nhieu bao lau may co khong duoc chua",
            "thi cua theo nhu the nao the nao khi nao o dau ai toi minh a nhe a ha phan tram",
            "VẬY?", unicodedata.normalize("NFD", "vậy"),
        ):
            with self.subTest(hoi=hoi):
                self.assertEqual(self.chi_muc.tim(hoi), [])
        chi_muc = ChiMucVay()
        chi_muc.them("DEMO", "DEMO.docx", _doan(["Vay."]))
        self.assertEqual(chi_muc.tim("vậy"), [])
        self.assertTrue(chi_muc.tim("vay"))
        self.assertEqual(chi_muc.tim("vay vậy"), chi_muc.tim("vay"))

    def test_khong_bo_tu_nghiep_vu_cua_cau_hoi(self):
        for tu in ("lãi", "suất", "phí", "trả", "nợ", "hạn", "vay", "gốc",
                   "kỳ", "điều chỉnh", "bảo đảm", "tài sản", "biên độ"):
            with self.subTest(tu=tu):
                chi_muc = ChiMucVay()
                chi_muc.them("DEMO", "DEMO.docx", _doan([tu + "."]))
                self.assertTrue(chi_muc.tim(tu))
                self.assertEqual(chi_muc.tim(tu), chi_muc.tim("cho hỏi " + tu + " là gì vậy?"))
                self.assertTrue(chi_muc.tim(" ".join(chuan_hoa(tu))))

    def test_loc_tai_lieu(self):
        self.chi_muc.them("DEMO-B", "DEMO-B.docx", self.doan)
        ket_qua = self.chi_muc.tim("lãi suất cho vay", loc_tai_lieu={"DEMO-B"})
        self.assertTrue(ket_qua)
        self.assertEqual({m["tai_lieu_id"] for m in ket_qua}, {"DEMO-B"})
        self.assertEqual(ket_qua[0]["trich_dan"]["ten_tep"], "DEMO-B.docx")
        self.assertEqual(self.chi_muc.tim("vay", loc_tai_lieu=set()), [])
        self.assertEqual(self.chi_muc.tim("vay", loc_tai_lieu={"khong-co"}), [])
        self.assertEqual(ket_qua, self.chi_muc.tim(
            "lãi suất cho vay", loc_tai_lieu={"DEMO-B", "khong-co"}))

    def test_xoa_tai_lieu_va_cap_nhat_thong_ke(self):
        self.chi_muc.them("DEMO-B", "DEMO-B.docx", self.doan)
        self.chi_muc.xoa("DEMO-A")
        self.chi_muc.xoa("khong-co")
        self.assertTrue(self.chi_muc.tim("lãi suất cho vay"))
        self.assertTrue(all(m["tai_lieu_id"] == "DEMO-B"
                            for m in self.chi_muc.tim("lãi suất cho vay")))
        self.assertEqual(self.chi_muc.tim("vay", loc_tai_lieu={"DEMO-A"}), [])
        chi_muc_b = ChiMucVay()
        chi_muc_b.them("DEMO-B", "DEMO-B.docx", self.doan)
        self.assertEqual(self.chi_muc.tim("vay"), chi_muc_b.tim("vay"))
        self.chi_muc.xoa("DEMO-B")
        self.assertEqual(self.chi_muc.tim("vay"), [])

    def test_them_cung_id_thay_phien_ban(self):
        self.chi_muc.them("DEMO-A", "DEMO-moi.docx", _doan(["Bảo đảm DEMO."]))
        self.assertEqual(self.chi_muc.tim("lãi suất cho vay"), [])
        self.assertEqual(self.chi_muc.tim("bảo đảm")[0]["ten_tep"], "DEMO-moi.docx")

    def test_json_vong_tron_va_thu_tu_on_dinh(self):
        self.chi_muc.them("DEMO-0", "DEMO-0.docx", self.doan)
        du_lieu = self.chi_muc.to_dict()
        chu_json = json.dumps(du_lieu, ensure_ascii=False, allow_nan=False)
        moi = ChiMucVay.from_dict(json.loads(chu_json))
        self.assertEqual(du_lieu, moi.to_dict())
        self.assertEqual(chu_json, json.dumps(moi.to_dict(), ensure_ascii=False,
                                             allow_nan=False))
        for hoi in ("lãi suất cho vay", "phí trả nợ trước hạn", "1.000.000.000"):
            with self.subTest(hoi=hoi):
                self.assertEqual(self.chi_muc.tim(hoi), moi.tim(hoi))
        dao_thu_tu = ChiMucVay()
        dao_thu_tu.them("DEMO-0", "DEMO-0.docx", self.doan)
        dao_thu_tu.them("DEMO-A", "DEMO-A.docx", self.doan)
        self.assertEqual(du_lieu, dao_thu_tu.to_dict())
        self.assertEqual(self.chi_muc.tim("vay"), dao_thu_tu.tim("vay"))

    def test_cau_va_metadata_dung_nguyen_van_cat_doan(self):
        tieu_de = {"Điều 1. Hạn mức DEMO", "Điều 2. Lãi suất DEMO",
                   "Điều 3. Thanh toán DEMO"}
        for doan in self.doan:
            for cau in doan["cau"]:
                ket_qua = self.chi_muc.tim(cau, so_ket_qua=100)
                khop = [m for m in ket_qua
                        if m["ma_doan"] == doan["ma_doan"] and m["cau"] == cau]
                self.assertFalse(any(m["cau"] in tieu_de for m in ket_qua))
                if cau in tieu_de:
                    self.assertEqual(khop, [])
                    continue
                self.assertEqual(len(khop), 1)
                self.assertEqual(khop[0]["trich_dan"]["cau"], cau)
                for khoa in ("trang_dau", "trang_cuoi", "dieu", "khoan"):
                    self.assertEqual(khop[0][khoa], doan[khoa])
                self.assertEqual(khop[0]["trich_dan"]["diem"], doan["diem"])

    def test_tim_so_tien_ngay_ty_le(self):
        for hoi, cau in (("1.000.000.000", "Số tiền vay"),
                         ("01.02.2026", "Số tiền vay"),
                         ("8,5%", "Lãi suất cho vay")):
            with self.subTest(hoi=hoi):
                self.assertIn(cau, self.chi_muc.tim(hoi)[0]["cau"])
        self.assertEqual(self.chi_muc.tim("1.000.000.001"), [])

    def test_diem_bm25_theo_cong_thuc(self):
        chi_muc = ChiMucVay()
        chi_muc.them("DEMO", "DEMO.docx", _doan(["vay vay.", "vay.", "khác."]))
        ket_qua = chi_muc.tim("vay")
        idf = math.log(1 + (3 - 2 + 0.5) / (2 + 0.5))
        diem = idf * 2 * 2.2 / (2 + 1.2 * (0.25 + 0.75 * 2 / (4 / 3)))
        self.assertEqual(ket_qua[0]["cau"], "vay vay.")
        self.assertAlmostEqual(ket_qua[0]["diem"], diem)

    def test_cong_diem_cum_hai_tu(self):
        chi_muc = ChiMucVay()
        chi_muc.them("DEMO", "DEMO.docx", _doan(["suất lãi.", "lãi suất."]))
        ket_qua = chi_muc.tim("lãi suất")
        self.assertEqual(ket_qua[0]["cau"], "lãi suất.")
        self.assertAlmostEqual(ket_qua[0]["diem"] - ket_qua[1]["diem"], 0.1)

    def test_ngat_trang_khong_doan_trang_cua_cau(self):
        chi_muc = ChiMucVay()
        chi_muc.them("DEMO", "DEMO.docx", _doan(["Vay DEMO."], trang_dau=2, trang_cuoi=3))
        muc = chi_muc.tim("vay")[0]
        self.assertEqual((muc["trang_dau"], muc["trang_cuoi"]), (2, 3))
        self.assertEqual(muc["trich_dan"]["trang"], "2-3")
        self.assertEqual(muc["trich_dan"]["diem"], "a")

    def test_rong_gioi_han_va_nguong(self):
        self.assertEqual(ChiMucVay().tim("vay"), [])
        for hoi in ("", "  ", "%?!"):
            self.assertEqual(self.chi_muc.tim(hoi), [])
        for n in (0, -1):
            self.assertEqual(self.chi_muc.tim("vay", so_ket_qua=n), [])
        self.assertEqual(len(self.chi_muc.tim("vay", so_ket_qua=1)), 1)
        chi_muc = ChiMucVay()
        chi_muc.them("DEMO", "DEMO.docx", _doan(["vay."] * 20))
        self.assertEqual(chi_muc.tim("vay"), [])
        chi_muc.them("DEMO", "DEMO.docx", _doan(["", " "]))
        self.assertEqual(chi_muc.tim("vay"), [])

    def test_ket_qua_va_json_khong_lam_bien_doi_chi_muc(self):
        truoc = self.chi_muc.tim("lãi suất cho vay")
        ket_qua = self.chi_muc.tim("lãi suất cho vay")
        ket_qua[0]["cau"] = "sửa DEMO"
        ket_qua[0]["trich_dan"]["cau"] = "sửa DEMO"
        du_lieu = self.chi_muc.to_dict()
        moi = ChiMucVay.from_dict(du_lieu)
        du_lieu["tai_lieu"][0]["doan_cat"].clear()
        self.doan.clear()
        self.assertEqual(self.chi_muc.tim("lãi suất cho vay"), truoc)
        self.assertEqual(moi.tim("lãi suất cho vay"), truoc)

    def test_json_rong_va_phien_ban_la(self):
        chi_muc = ChiMucVay()
        chi_muc.them("DEMO", "DEMO.docx", [])
        self.assertEqual(ChiMucVay.from_dict(chi_muc.to_dict()).to_dict(),
                         chi_muc.to_dict())
        with self.assertRaises(ValueError):
            ChiMucVay.from_dict({"phien_ban": 2, "tai_lieu": []})

    def test_grep_ma_m9_va_utf8_khong_bom(self):
        goc = Path(__file__).resolve().parents[1]
        cac_tep = list((goc / "src" / "kho_tri_thuc" / "m9").rglob("*.py"))
        for tep in cac_tep:
            raw = tep.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), tep.name)
            for cam in ("api.anthropic.com", "api.openai.com", "mask"):
                self.assertNotIn(cam, raw.decode("utf-8").lower(), tep.name)
        self.assertFalse(Path(__file__).read_bytes().startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
