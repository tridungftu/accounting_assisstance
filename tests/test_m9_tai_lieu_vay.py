"""Hợp đồng DEMO hoàn toàn trong bộ nhớ, chỉ dùng thư viện chuẩn."""

import hashlib
import io
import json
from pathlib import Path
import unittest
import zipfile
from xml.sax.saxutils import escape

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m9.chi_muc_vay import ChiMucVay
from kho_tri_thuc.m9.tai_lieu_vay import cat_doan, doc_docx, nhan_thong_tin


_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _p(chu):
    return '<w:p><w:r><w:t xml:space="preserve">' + escape(chu) + '</w:t></w:r></w:p>'


def _docx(noi_dung):
    bo_dem = io.BytesIO()
    with zipfile.ZipFile(bo_dem, "w", zipfile.ZIP_DEFLATED) as tep:
        tep.writestr("[Content_Types].xml", (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>'
        ))
        tep.writestr("_rels/.rels", (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="word/document.xml" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"/>'
            '</Relationships>'
        ))
        tep.writestr("word/document.xml", f'<w:document xmlns:w="{_NS}"><w:body>{noi_dung}</w:body></w:document>')
    return bo_dem.getvalue()


def _demo():
    return _docx(
        _p("HỢP ĐỒNG TÍN DỤNG DEMO")
        + _p("Chương I. Quy định DEMO")
        + _p("Điều 1. Hạn mức DEMO")
        + _p("Số tiền vay 1.000.000.000 VND ngày 01.02.2026. Giữ nguyên chứng cứ;")
        + '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
        + _p("ĐIỀU 2: Nghĩa vụ DEMO")
        + _p("1. Trả nợ đúng hạn.")
        + _p("a) Gửi thông báo;")
        + _p("Nội dung tiếp theo.")
        + _p("b. Đối chiếu chứng từ.")
        + _p("2.1 Hồ sơ DEMO.")
        + _p("Khoản 3. Xác nhận DEMO.")
        + '<w:tbl><w:tr><w:tc>' + _p("Ngân hàng DEMO") + '</w:tc><w:tc>'
        + _p("1.000.000.000 VND") + '</w:tc></w:tr><w:tr><w:tc>'
        + _p("01.02.2026") + '</w:tc><w:tc>' + _p("Lãi suất theo thỏa thuận")
        + '</w:tc></w:tr></w:tbl>'
    )


class TaiLieuVayTests(unittest.TestCase):
    def test_thu_tu_trang_bang_va_chu_goc(self):
        doan = doc_docx(_demo())
        self.assertEqual([d["thu_tu"] for d in doan], list(range(1, len(doan) + 1)))
        self.assertEqual([d["trang"] for d in doan[:4]], [1] * 4)
        self.assertTrue(all(d["trang"] == 2 for d in doan[4:]))
        self.assertEqual([d["van_ban"] for d in doan if d.get("la_bang")], [
            "Ngân hàng DEMO", "1.000.000.000 VND", "01.02.2026", "Lãi suất theo thỏa thuận",
        ])
        self.assertEqual(doc_docx(_docx(_p("  Giữ  chữ\tViệt  ")))[0]["van_ban"], "Giữ chữ Việt")

    def test_dieu_khoan_diem_va_phan_mo_dau(self):
        doan = cat_doan(doc_docx(_demo()))
        self.assertEqual([(d["dieu"], d["khoan"], d["diem"]) for d in doan], [
            ("MO_DAU", None, None), ("MO_DAU", None, None),
            ("1. Hạn mức DEMO", None, None), ("2: Nghĩa vụ DEMO", None, None),
            ("2: Nghĩa vụ DEMO", "1", None), ("2: Nghĩa vụ DEMO", "1", "a"),
            ("2: Nghĩa vụ DEMO", "1", "b"), ("2: Nghĩa vụ DEMO", "2.1", None),
            ("2: Nghĩa vụ DEMO", "3", None),
        ])
        self.assertEqual(doan[2]["chuong"], "I. Quy định DEMO")
        self.assertEqual(doan[5]["cau"], ["a) Gửi thông báo;", "Nội dung tiếp theo."])
        self.assertEqual((doan[2]["trang_dau"], doan[2]["trang_cuoi"]), (1, 1))
        self.assertEqual((doan[3]["trang_dau"], doan[3]["trang_cuoi"]), (2, 2))

    def test_cau_khong_cat_so_tien_ngay_va_giu_dau(self):
        doan = cat_doan(doc_docx(_demo()))
        self.assertEqual(doan[2]["cau"], [
            "Điều 1. Hạn mức DEMO",
            "Số tiền vay 1.000.000.000 VND ngày 01.02.2026.",
            "Giữ nguyên chứng cứ;",
        ])
        cau = [c for d in doan for c in d["cau"]]
        self.assertIn("1.000.000.000 VND", cau)
        self.assertIn("01.02.2026", cau)

    def test_ma_on_dinh_va_phan_biet_vi_tri_noi_dung(self):
        dau_vao = doc_docx(_demo())
        lan_1, lan_2 = cat_doan(dau_vao), cat_doan(doc_docx(_demo()))
        self.assertEqual(lan_1, lan_2)
        self.assertEqual(len({d["ma_doan"] for d in lan_1}), len(lan_1))
        sua = [dict(d) for d in dau_vao]
        sua[0]["van_ban"] += " sửa"
        self.assertNotEqual(cat_doan(sua)[0]["ma_doan"], lan_1[0]["ma_doan"])
        sua[0] = {**dau_vao[0], "thu_tu": 99}
        self.assertNotEqual(cat_doan(sua)[0]["ma_doan"], lan_1[0]["ma_doan"])

    def test_ngat_trang_giua_doan_va_rendered(self):
        raw = _docx('<w:p><w:r><w:t>Đầu trang.</w:t><w:br w:type="page"/>'
                    '<w:t>Trang hai;</w:t><w:lastRenderedPageBreak/>'
                    '<w:t>Trang ba.</w:t></w:r></w:p>')
        doc = doc_docx(raw)
        self.assertEqual([(d["trang"], d["van_ban"]) for d in doc], [
            (1, "Đầu trang."), (2, "Trang hai;"), (3, "Trang ba."),
        ])
        ket_qua = cat_doan(doc)
        self.assertEqual((ket_qua[0]["trang_dau"], ket_qua[0]["trang_cuoi"]), (1, 3))

    def test_noi_run_tab_va_ngat_dong(self):
        raw = _docx('<w:p><w:r><w:t>Hợp</w:t></w:r><w:r><w:t>đồng</w:t>'
                    '<w:tab/><w:t>DEMO</w:t><w:br/><w:t>tiếp</w:t></w:r></w:p>')
        self.assertEqual(doc_docx(raw), [{"trang": 1, "thu_tu": 1, "van_ban": "Hợpđồng DEMO tiếp"}])

    def test_rendered_sau_ngat_tuong_minh_chi_tang_mot_trang(self):
        for khoang_giua in (
            '',
            '</w:r><w:r>',
            '</w:r></w:p><w:p><w:r>',
            '</w:r></w:p><w:p/><w:p><w:r><w:t>  </w:t><w:tab/><w:br/>',
        ):
            with self.subTest(khoang_giua=khoang_giua):
                raw = _docx('<w:p><w:r><w:t>Trang một.</w:t><w:br w:type="page"/>'
                            + khoang_giua + '<w:lastRenderedPageBreak/>'
                            '<w:t>Trang hai.</w:t></w:r></w:p>')
                self.assertEqual([(d["trang"], d["van_ban"]) for d in doc_docx(raw)], [
                    (1, "Trang một."), (2, "Trang hai."),
                ])
                self.assertEqual(nhan_thong_tin(
                    raw, ten_tep="DEMO.docx", loai_tai_lieu="PHU_LUC",
                )["so_trang"], 2)

    def test_hai_rendered_khong_co_chu_chi_tang_mot_trang(self):
        for khoang_giua in ('', '</w:r></w:p><w:p><w:r><w:t> </w:t>'):
            with self.subTest(khoang_giua=khoang_giua):
                raw = _docx('<w:p><w:r><w:t>Trang một.</w:t><w:lastRenderedPageBreak/>'
                            + khoang_giua + '<w:lastRenderedPageBreak/>'
                            '<w:t>Trang hai.</w:t></w:r></w:p>')
                self.assertEqual([d["trang"] for d in doc_docx(raw)], [1, 2])
                self.assertEqual(nhan_thong_tin(
                    raw, ten_tep="DEMO.docx", loai_tai_lieu="PHU_LUC",
                )["so_trang"], 2)

    def test_rendered_dung_mot_minh_van_tang_trang(self):
        raw = _docx(_p("Trang một.") + '<w:p><w:r><w:lastRenderedPageBreak/>'
                    '<w:t>Trang hai.</w:t></w:r></w:p>')
        self.assertEqual([d["trang"] for d in doc_docx(raw)], [1, 2])
        self.assertEqual(nhan_thong_tin(
            raw, ten_tep="DEMO.docx", loai_tai_lieu="PHU_LUC",
        )["so_trang"], 2)

    def test_ngat_tuong_minh_lien_tiep_giu_trang_trang(self):
        raw = _docx(_p("Trang một.") + '<w:p><w:r><w:br w:type="page"/>'
                    '<w:lastRenderedPageBreak/><w:br w:type="page"/>'
                    '<w:lastRenderedPageBreak/><w:t>Trang ba.</w:t></w:r></w:p>')
        self.assertEqual([d["trang"] for d in doc_docx(raw)], [1, 3])
        self.assertEqual(nhan_thong_tin(
            raw, ten_tep="DEMO.docx", loai_tai_lieu="PHU_LUC",
        )["so_trang"], 3)

    def test_loi_doc_tai_lieu_trung_tinh(self):
        for doc in (doc_docx, lambda raw: nhan_thong_tin(
            raw, ten_tep="DEMO.docx", loai_tai_lieu="PHU_LUC",
        )):
            with self.subTest(doc=doc), self.assertRaises(DataError) as loi:
                doc(b"DEMO khong phai DOCX")
            self.assertNotIn("Anh", str(loi.exception))
            self.assertEqual(str(loi.exception),
                             "Không đọc được tài liệu. Hãy tải lên tệp Word (.docx) hợp lệ.")

    def test_dieu_chuong_khong_dau_cau_can_chu_hoa(self):
        for nhan, cap in (("Điều", "dieu"), ("Chương", "chuong")):
            for tieu_de in ("Lãi suất cho vay", "LÃI SUẤT", "Đầu tư", "Ứng vốn"):
                for tien_to in (nhan, nhan.upper()):
                    with self.subTest(nhan=tien_to, tieu_de=tieu_de):
                        doan = cat_doan(doc_docx(_docx(_p(f"{tien_to} 5 {tieu_de}"))))
                        self.assertEqual(doan[0][cap], f"5 {tieu_de}")
            for duoi in (" của hợp đồng này quy định", " lãi suất", "Lãi Suất", " 5 ngày"):
                with self.subTest(nhan=nhan, duoi=duoi):
                    doan = cat_doan(doc_docx(_docx(_p(f"{nhan} 5{duoi}"))))
                    self.assertEqual(doan[0][cap], "MO_DAU" if cap == "dieu" else None)

    def test_dieu_dung_rieng_gop_tieu_de_va_giu_khoan(self):
        raw = _docx(_p("Điều 4. DEMO") + _p("4.1 Nội dung trước.")
                    + _p("ĐIỀU 5") + _p("LÃI SUẤT CHO VAY")
                    + _p("5.1 Lãi suất là 8,5%/năm."))
        doan = cat_doan(doc_docx(raw))
        self.assertEqual(doan[-1]["dieu"], "5 LÃI SUẤT CHO VAY")
        self.assertEqual(doan[-1]["khoan"], "5.1")
        self.assertEqual(doan[-1]["cau"], ["5.1 Lãi suất là 8,5%/năm."])
        self.assertEqual(doan[-2]["cau"], [])
        self.assertNotIn("LÃI SUẤT CHO VAY", [c for d in doan for c in d["cau"]])

    def test_dieu_co_cham_gop_tieu_de_giu_nguyen_cau(self):
        raw = _docx(_p("Điều 6.") + _p("Trả nợ trước hạn")
                    + _p("Bên vay được trả nợ trước hạn."))
        doan = cat_doan(doc_docx(raw))
        self.assertEqual(len(doan), 1)
        self.assertEqual(doan[0]["dieu"], "6 Trả nợ trước hạn")
        self.assertEqual(doan[0]["cau"], ["Bên vay được trả nợ trước hạn."])

    def test_nhan_dung_rieng_khong_tieu_de_chi_giu_so(self):
        for nhan, cap, so in (("Điều 5", "dieu", "5"), ("ĐIỀU 5", "dieu", "5"),
                              ("Chương 5", "chuong", "5"), ("CHƯƠNG IV", "chuong", "IV")):
            for dau in ("", ".", ":"):
                with self.subTest(nhan=nhan, dau=dau):
                    doan = cat_doan(doc_docx(_docx(_p(nhan + dau))))
                    self.assertEqual(doan[0][cap], so)

    def test_khong_gop_nhan_khoan_diem_dieu_chuong_lam_tieu_de(self):
        for sau in ("1. Nội dung DEMO", "5.1 Nội dung DEMO", "Khoản 1. Nội dung DEMO",
                    "a) Nội dung DEMO", "b. Nội dung DEMO", "Điểm a) Nội dung DEMO",
                    "Điều 8", "Điều 8. DEMO", "Điều 5 của hợp đồng này quy định",
                    "Chương IV", "Chương IV. DEMO"):
            with self.subTest(sau=sau):
                raw = _docx(_p("Điều 4. DEMO") + _p("a) Nội dung trước.")
                            + _p("Điều 7") + _p(sau))
                doan = cat_doan(doc_docx(raw))
                dieu_moi = doan[2]
                self.assertEqual(dieu_moi["dieu"], "7")
                self.assertIsNone(dieu_moi["khoan"])
                self.assertIsNone(dieu_moi["diem"])
                if sau not in ("Điều 8", "Chương IV"):
                    self.assertIn(sau, [c for d in doan for c in d["cau"]])
                if sau.startswith("1."):
                    self.assertEqual((doan[-1]["dieu"], doan[-1]["khoan"]), ("7", "1"))

    def test_tieu_de_tach_gioi_han_do_dai_va_dau_cau(self):
        for sau in ("A" * 120, "A" * 121,
                    *("Bên vay được trả nợ trước hạn" + dau for dau in ".,;:!?…")):
            with self.subTest(sau=sau):
                raw = _docx(_p("Điều 6") + _p(sau) + _p("Nội dung tiếp theo"))
                doan = cat_doan(doc_docx(raw))
                if sau == "A" * 120:
                    self.assertEqual(doan[0]["dieu"], "6 " + sau)
                    self.assertNotIn(sau, doan[0]["cau"])
                else:
                    self.assertEqual(doan[0]["dieu"], "6")
                    self.assertIn(sau, doan[0]["cau"])
                self.assertIn("Nội dung tiếp theo", doan[0]["cau"])

    def test_chuong_tach_reset_cap_va_khong_gop_tieu_de_bang(self):
        bang = '<w:tbl><w:tr><w:tc>' + _p("Nội dung bảng DEMO") + '</w:tc></w:tr></w:tbl>'
        raw = _docx(_p("Điều 4. DEMO") + _p("1. Nội dung trước.")
                    + _p("a) Nội dung điểm.") + _p("CHƯƠNG IV:") + bang
                    + _p("ĐẦU TƯ TÀI CHÍNH") + _p("Điều 5")
                    + _p("1. Nội dung sau."))
        doan = cat_doan(doc_docx(raw))
        chuong = doan[-3]
        self.assertEqual(chuong["chuong"], "IV ĐẦU TƯ TÀI CHÍNH")
        self.assertEqual((chuong["dieu"], chuong["khoan"], chuong["diem"]), ("MO_DAU", None, None))
        self.assertEqual(chuong["cau"], ["Nội dung bảng DEMO"])
        self.assertEqual(doan[-1]["chuong"], "IV ĐẦU TƯ TÀI CHÍNH")
        self.assertEqual((doan[-1]["dieu"], doan[-1]["khoan"]), ("5", "1"))
        chi_bang = cat_doan(doc_docx(_docx(_p("Điều 5") + bang)))
        self.assertEqual(chi_bang[0]["dieu"], "5")
        self.assertIn("Nội dung bảng DEMO", chi_bang[0]["cau"])
        nhan_trong_bang = _docx('<w:tbl><w:tr><w:tc>' + _p("Điều 5")
                               + '</w:tc></w:tr></w:tbl>' + _p("LÃI SUẤT"))
        self.assertEqual(cat_doan(doc_docx(nhan_trong_bang))[0]["dieu"], "MO_DAU")

    def test_gop_tieu_de_giu_nguon_ma_va_trang(self):
        raw = _docx(_p("Điều 5") + '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
                    + _p("LÃI SUẤT") + _p("1. Nội dung DEMO."))
        nguon = doc_docx(raw)
        doan = cat_doan(nguon)
        self.assertEqual(doan, cat_doan(doc_docx(raw)))
        self.assertEqual(len({d["ma_doan"] for d in doan}), len(doan))
        self.assertEqual((doan[0]["trang_dau"], doan[0]["trang_cuoi"]), (1, 2))
        # Cách băm vị trí/chữ gốc giữ nguyên, kể cả đoạn tiêu đề đã gộp.
        vi_tri_noi_dung = [[i, muc["thu_tu"], muc["trang"], muc["van_ban"]]
                          for i, muc in enumerate(nguon[:2])]
        self.assertEqual(doan[0]["ma_doan"], hashlib.sha256(json.dumps(
            vi_tri_noi_dung, ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")).hexdigest())
        sua = [dict(muc) for muc in nguon]
        sua[1]["van_ban"] = "Lãi suất"
        self.assertNotEqual(cat_doan(sua)[0]["ma_doan"], doan[0]["ma_doan"])
        self.assertEqual(cat_doan(sua)[1]["ma_doan"], doan[1]["ma_doan"])
        self.assertEqual(set(doan[0]), {"chuong", "dieu", "khoan", "diem", "trang_dau",
                                        "trang_cuoi", "cau", "ma_doan"})

    def test_tieu_de_tach_chi_lam_ngu_canh_chi_muc(self):
        raw = _docx(_p("Chương I") + _p("TÍN DỤNG") + _p("Điều 5")
                    + _p("LÃI SUẤT CHO VAY") + _p("1. Kỳ điều chỉnh là sáu tháng."))
        chi_muc = ChiMucVay()
        chi_muc.them("DEMO", "DEMO.docx", cat_doan(doc_docx(raw)))
        for hoi in ("lãi suất cho vay", "tín dụng"):
            with self.subTest(hoi=hoi):
                ket_qua = chi_muc.tim(hoi, so_ket_qua=100)
                self.assertTrue(ket_qua)
                self.assertTrue(all(m["khoan"] == "1" for m in ket_qua))
                self.assertTrue(all(m["cau"] == "1. Kỳ điều chỉnh là sáu tháng." for m in ket_qua))
                self.assertEqual(ket_qua[0]["trich_dan"]["dieu"], "5 LÃI SUẤT CHO VAY")

    def test_chuong_so_la_ma_khong_dau_cau_va_dau_cau_cu(self):
        for tieu_de in ("Chương IV Đầu tư", "CHƯƠNG IV ĐẦU TƯ", "Chương 5. lãi suất",
                        "Điều 5: lãi suất"):
            with self.subTest(tieu_de=tieu_de):
                doan = cat_doan(doc_docx(_docx(_p(tieu_de))))
                cap = "dieu" if tieu_de.startswith("Điều") else "chuong"
                self.assertEqual(doan[0][cap], tieu_de.split(maxsplit=1)[1])

    def test_nhan_thong_tin_khong_luu_tep(self):
        raw = _demo()
        self.assertEqual(nhan_thong_tin(raw, ten_tep="DEMO.docx", loai_tai_lieu="HD_TIN_DUNG"), {
            "sha256": hashlib.sha256(raw).hexdigest(), "so_trang": 2,
            "so_doan": 9, "loai_tai_lieu": "HD_TIN_DUNG",
        })
        for loai in ("KHE_UOC_NHAN_NO", "PHU_LUC", "HD_BAO_DAM", "THONG_BAO_LAI_SUAT"):
            with self.subTest(loai=loai):
                self.assertEqual(nhan_thong_tin(raw, ten_tep="DEMO.docx", loai_tai_lieu=loai)["loai_tai_lieu"], loai)
        trang_trang = _docx(_p("DEMO") + '<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
        self.assertEqual(nhan_thong_tin(trang_trang, ten_tep="DEMO.docx", loai_tai_lieu="PHU_LUC")["so_trang"], 2)

    def test_docx_hong_ma_loi_va_khong_lo_duong_dan(self):
        bo_dem = io.BytesIO()
        with zipfile.ZipFile(bo_dem, "w") as tep:
            tep.writestr("khac.xml", "DEMO")
        hong_xml = io.BytesIO()
        with zipfile.ZipFile(hong_xml, "w") as tep:
            tep.writestr("word/document.xml", "<hong>")
        for raw in (b"DEMO khong phai DOCX", bo_dem.getvalue(), hong_xml.getvalue(),
                    _docx("").replace(b"word/document.xml", b"word/khong_co.xml")):
            with self.subTest(raw=raw[:8]):
                for doc in (doc_docx, lambda r: nhan_thong_tin(r, ten_tep=r"C:\DEMO\bi_mat.docx", loai_tai_lieu="PHU_LUC")):
                    with self.assertRaises(DataError) as loi:
                        doc(raw)
                    self.assertEqual(loi.exception.code, "M9_TAI_LIEU_KHONG_DOC_DUOC")
                    self.assertNotIn("C:\\", str(loi.exception))
                    self.assertNotIn("bi_mat", str(loi.exception))

    def test_loai_tai_lieu_la(self):
        for loai in ("KHAC", "", None, []):
            with self.subTest(loai=loai), self.assertRaises(DataError) as loi:
                nhan_thong_tin(_demo(), ten_tep="DEMO.docx", loai_tai_lieu=loai)
            self.assertEqual(loi.exception.code, "M9_LOAI_TAI_LIEU_KHONG_HOP_LE")

    def test_khong_doi_cap_do_so_tien_va_o_bang(self):
        raw = _docx(_p("Điều 1. DEMO") + _p("1.000.000.000 VND được giữ nguyên.")
                    + '<w:tbl><w:tr><w:tc>' + _p("2. Nhãn trong bảng") + '</w:tc></w:tr></w:tbl>')
        doan = cat_doan(doc_docx(raw))
        self.assertEqual(len(doan), 1)
        self.assertIsNone(doan[0]["khoan"])

    def test_tai_lieu_rong(self):
        self.assertEqual(doc_docx(_docx("")), [])
        self.assertEqual(cat_doan([]), [])

    def test_reset_cap_va_khoan_nhieu_cap_co_dau_cham_cuoi(self):
        raw = _docx(_p("Chương I. DEMO") + _p("Điều 1. DEMO")
                    + _p("1.1. Nội dung DEMO.") + _p("a. Điểm DEMO.")
                    + _p("2. Khoản kế tiếp.") + _p("Điều 2. DEMO")
                    + _p("Chương II. DEMO") + _p("Điều 3. DEMO"))
        doan = cat_doan(doc_docx(raw))
        self.assertEqual(doan[2]["khoan"], "1.1")
        self.assertEqual(doan[2]["cau"], ["1.1. Nội dung DEMO."])
        self.assertEqual(doan[3]["diem"], "a")
        self.assertIsNone(doan[4]["diem"])
        self.assertIsNone(doan[5]["khoan"])
        self.assertIsNone(doan[5]["diem"])
        self.assertEqual(doan[-1]["chuong"], "II. DEMO")

    def test_xml_khong_phai_document_word(self):
        for xml in ("<document><body/></document>", f'<w:document xmlns:w="{_NS}"/>'):
            bo_dem = io.BytesIO()
            with zipfile.ZipFile(bo_dem, "w") as tep:
                tep.writestr("word/document.xml", xml)
            with self.subTest(xml=xml), self.assertRaises(DataError) as loi:
                doc_docx(bo_dem.getvalue())
            self.assertEqual(loi.exception.code, "M9_TAI_LIEU_KHONG_DOC_DUOC")

    def test_grep_ma_m9_va_utf8_khong_bom(self):
        thu_muc = Path(__file__).resolve().parents[1] / "src" / "kho_tri_thuc" / "m9"
        for tep in thu_muc.rglob("*.py"):
            raw = tep.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), tep.name)
            chu = raw.decode("utf-8").lower()
            for cam in ("api.anthropic.com", "api.openai.com", "mask"):
                self.assertNotIn(cam, chu, tep.name)
        self.assertFalse(Path(__file__).read_bytes().startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
