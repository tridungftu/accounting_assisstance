"""E1-3: DOCX DEMO tối thiểu, đọc bằng bản vá E3 có sẵn; cấm Office/AI/cloud.

Namespace cô lập dùng lại dependency thuần của test E1-2. Không tạo overlay,
không xóa thư mục tạm; mọi DOCX mới được tạo bằng zipfile ngay trong test.
"""
from __future__ import annotations

import copy
import datetime
import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]


def _nap(ten, path):
    spec = importlib.util.spec_from_file_location(ten, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


E2 = _nap("_e3_dung_e2", ROOT / "tests/test_e1_mua_quy_tac.py")
DHD = _nap("_e3_docx_demo", ROOT / "tools/source6_docx_tables/doc_hop_dong.py")
CU = _nap("_e3_fixture_cu", ROOT / "tests/test_source6_docx_tables.py")
Q, D = E2.Q, E2.D
MODS = {**E2.MODS, E2.TEN + ".doc_hop_dong": DHD}
with patch.dict(sys.modules, MODS):
    Q_CU = _nap(E2.TEN + ".quy_trinh_cu", ROOT / "tools/source6_docx_tables/quy_trinh.py")


def _p(s):
    return '<w:p><w:r><w:t xml:space="preserve">' + escape(s) + '</w:t></w:r></w:p>'


def _o(s, pr=""):
    return '<w:tc>' + ('<w:tcPr>' + pr + '</w:tcPr>' if pr else '') + _p(s) + '</w:tc>'


def _r(*cells):
    return '<w:tr>' + ''.join(cells) + '</w:tr>'


def _tbl(headers, rows):
    return ('<w:tbl><w:tblGrid>' + '<w:gridCol/>' * len(headers) + '</w:tblGrid>'
            + _r(*[_o(s) for s in headers]) + ''.join(rows) + '</w:tbl>')


HANG = ["Mã hàng", "Tên hàng hóa", "ĐVT", "Số lượng", "Đơn giá (VND)", "Thành tiền (VND)"]
LICH = ["Đợt thanh toán", "Tỷ lệ (%)", "Số tiền", "Hạn thanh toán"]


class NgayCoDinh(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 25, 12, 0, 0)


class E1BangTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tam = Path(tempfile.mkdtemp(prefix="e1_bang_DEMO_"))
        cls.dem = 0
        good = [_r(*map(_o, [f"DEMO-{i}", f"Vật tư DEMO {i}", "bộ", "2,5", "20000", "50000"])) for i in range(1, 6)]
        schedule = [_r(*map(_o, [f"Đợt DEMO {i}", v, "100000", f"2026-{i + 9:02d}-25"]))
                    for i, v in enumerate(("30%", "30%", "40%"), 1)]
        cls.tot = cls.docx(_tbl(HANG, good) + _tbl(LICH, schedule))
        bad = [
            _r(_o("DEMO-A"), _o("Hàng DEMO A"), _o("bộ"), _o(""), _o("1.000"), _o("0")),
            _r(_o("DEMO-B"), _o("Gộp DEMO", '<w:gridSpan w:val="2"/>'), _o("2"), _o("20000"), _o("")),
            _r(_o("DEMO-C"), _o("Tên DEMO", '<w:vMerge w:val="restart"/>'), _o("bộ"), _o("3"), _o("20000"), _o("60000")),
            _r(_o("DEMO-D"), _o("", '<w:vMerge/>'), _o("bộ"), _o("3"), _o("20000")),
            _r(*[_o("") for _ in HANG]),
        ]
        bad_schedule = [
            _r(*map(_o, ["Kỳ DEMO 1", "20–30%", "", "Sau nghiệm thu DEMO"])),
            _r(*map(_o, ["Kỳ DEMO 2", "50%", "100000", "01/02/2026"])),
            _r(*map(_o, ["Kỳ DEMO 3", "50%", "100000", "31/02/2026"])),
        ]
        cls.loi = cls.docx(_tbl(HANG, bad) + _tbl(LICH, bad_schedule))

    @classmethod
    def docx(cls, body):
        cls.dem += 1
        path = cls.tam / f"DEMO_{cls.dem}.docx"
        xml = ('<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="' + DHD.W_NS
               + '"><w:body>' + _p("HỢP ĐỒNG DEMO") + body + '</w:body></w:document>')
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as z:
            z.writestr("word/document.xml", xml.encode("utf-8"))
        return path

    def info(self, path):
        with patch.object(DHD, "_word", side_effect=E2._cam), patch.object(DHD, "chuyen_docx", side_effect=E2._cam):
            return DHD.read_contract(str(path))

    def bang(self, path, loai="MUA_HH"):
        info = self.info(path)
        snapshot = copy.deepcopy(info["bang_nguon"])
        result = DHD.trich_bang_tham_so(info["bang_nguon"], loai)
        self.assertEqual(info["bang_nguon"], snapshot)
        return result

    @staticmethod
    def cell(b, row, ma):
        return next(c for c in b["dong"][row]["o"] if c["ma"] == ma)

    def chay(self, path, loai="MUA_HH", qt=Q, ai=None, params=None):
        reg = D.CATALOG_COMMON[loai]
        meta = {"loai_hop_dong": loai, "catalog_id": reg["catalog_id"], "catalog_sha256": reg["sha256"]}
        params = params if params is not None else [D.to_param(m, "DEMO", "DEMO bảng", bk="demo") for m in ("TT-05", "TT-20")]
        with patch.dict(sys.modules, MODS):
            tx = qt.TrichXuat(params, out_dir=str(self.tam / "out"), meta=meta, ai=ai, ra_lai=False)
            def ghi(kq, out):
                dest = Path(out, "DEMO_KET_QUA.json")
                dest.write_text(json.dumps(kq, ensure_ascii=False), encoding="utf-8")
                self.assertEqual(json.loads(dest.read_text(encoding="utf-8")), kq)
            with patch.object(qt, "read_contract", side_effect=lambda p: self.info(p)), patch.object(qt, "save"), \
                 patch.object(tx, "tc_theo_quy_tac", return_value={}), \
                 patch.object(MODS[E2.TEN + ".xuat"], "ghi_ket_qua_hd", side_effect=ghi), \
                 patch.object(qt.time, "time", return_value=100), patch.object(qt.datetime, "datetime", NgayCoDinh):
                return tx.xu_ly(str(path))

    def test_hang_5_dong_6_cot_lich_3_dot_4_cot(self):
        for loai in ("MUA_HH", "NHAP_KHAU", "DV_KY", "THUE_TS"):
            with self.subTest(loai=loai):
                b = self.bang(self.tot, loai)
                for ma, so, cols in (("TT-05", 5, 6), ("TT-20", 3, 4)):
                    self.assertEqual(len(b[ma]), 1)
                    table = b[ma][0]
                    self.assertEqual((len(table["dong"]), len(table["cot"])), (so, cols))
                    self.assertFalse(table["can_ra_soat"])
                    self.assertTrue(all(len(r["o"]) == cols for r in table["dong"]))
                c = self.cell(b["TT-05"][0], 0, "so_luong")
                self.assertEqual((c["goc"], c["chuan"]), ("2,5", "2.5"))
                self.assertEqual(self.cell(b["TT-20"][0], 2, "han")["chuan"], "2026-12-25")
                self.assertEqual(self.cell(b["TT-20"][0], 1, "ty_le")["chuan"], "30")

    def test_o_trong_ngang_doc_thieu_khong_copy_khong_tinh(self):
        b = self.bang(self.loi)["TT-05"][0]
        self.assertEqual(len(b["dong"]), 5)
        for row, ma in ((0, "so_luong"), (0, "don_gia"), (1, "ten_hang"), (1, "don_vi"),
                        (1, "thanh_tien"), (2, "ten_hang"), (3, "ten_hang"), (3, "thanh_tien")):
            with self.subTest(row=row, ma=ma):
                c = self.cell(b, row, ma)
                self.assertTrue(c["can_ra_soat"])
                self.assertIsNone(c["chuan"])
        self.assertEqual(self.cell(b, 0, "thanh_tien")["chuan"], "0")
        self.assertEqual(self.cell(b, 3, "ten_hang")["goc"], "")
        self.assertEqual(self.cell(b, 3, "thanh_tien")["ly_do"], ["THIEU_O"])
        self.assertTrue(b["can_ra_soat"])

    def test_lich_khong_suy_ty_le_han_tuong_doi_ngay_mo_ho(self):
        b = self.bang(self.loi)["TT-20"][0]
        self.assertEqual(len(b["dong"]), 3)
        for row, ma in ((0, "ty_le"), (0, "so_tien"), (0, "han"), (1, "han"), (2, "han")):
            c = self.cell(b, row, ma)
            self.assertTrue(c["can_ra_soat"])
            self.assertIsNone(c["chuan"])
        self.assertEqual(self.cell(b, 0, "ty_le")["goc"], "20–30%")

    def test_so_ngay_chi_chuan_hoa_khi_chac_chan(self):
        for raw, want in (("1.000", None), ("1,000", None), ("1.000.000", "1000000"),
                          ("1,234.50", "1234.50"), ("1.234,50", "1234.50"), ("0", "0"),
                          ("20000 VND", None), ("2 x 3", None)):
            with self.subTest(raw=raw):
                self.assertEqual(DHD._e1_chuan(raw, "don_gia"), want)
        self.assertEqual(DHD._e1_chuan("25/10/2026", "han"), "2026-10-25")
        self.assertIsNone(DHD._e1_chuan("2026-02-31", "han"))

    def test_tieu_de_dao_cot_khong_dau_ma_hang_va_don_gia_ky(self):
        for headers, rows, loai, col in (
            (["THANH TIEN", "MA HANG", "DON GIA", "DVT"], [["20000", "DEMO-1", "20000", "bo"]], "NHAP_KHAU", "ma_hang"),
            (["Kỳ tính phí", "Đơn giá kỳ"], [["Tháng DEMO 1", "20000"]], "DV_KY", "ky"),
            (["Tên tài sản", "ĐVT", "Đơn giá thuê"], [["Máy DEMO", "tháng", "20000"]], "THUE_TS", "ten_hang"),
        ):
            with self.subTest(headers=headers):
                path = self.docx(_p("Chú thích DEMO") + _tbl(headers, [_r(*map(_o, r)) for r in rows]))
                b = self.bang(path, loai)["TT-05"][0]
                self.assertFalse(b["can_ra_soat"])
                self.assertIsNotNone(self.cell(b, 0, col)["chuan"])

    def test_khong_lay_bang_khac_hoac_xd_lam_tt05(self):
        path = self.docx(_tbl(["Tên DEMO", "Giá DEMO"], [_r(_o("DEMO"), _o("123"))]))
        self.assertEqual(self.bang(path), {"TT-20": [], "TT-05": []})
        self.assertEqual(self.bang(self.tot, "XD"), {})
        self.assertNotIn("TT-05", self.bang(self.tot, "DV"))

    def test_nhieu_bang_tieu_de_lap_va_dong_tong_khong_mat(self):
        rows = [_r(*map(_o, ["DEMO", "Hàng DEMO", "bộ", "1", "20000", "20000"])),
                _r(*map(_o, HANG)), _r(*map(_o, ["", "Tổng DEMO", "", "", "", "20000"]))]
        path = self.docx(_tbl(HANG, rows) * 2)
        tables = self.bang(path)["TT-05"]
        self.assertEqual([len(b["dong"]) for b in tables], [2, 2])
        self.assertNotEqual(tables[0]["bang_id"], tables[1]["bang_id"])
        self.assertEqual(self.cell(tables[0], 1, "ten_hang")["goc"], "Tổng DEMO")

    def test_tieu_de_trung_va_gop_can_ra_soat(self):
        path = self.docx(_tbl(["Tên hàng", "ĐVT", "Đơn giá", "Đơn giá"],
                             [_r(*map(_o, ["DEMO", "bộ", "20000", "30000"]))]))
        b = self.bang(path)["TT-05"][0]
        self.assertIn("TIEU_DE_MO_HO", b["ly_do"])
        self.assertTrue(all(c["chuan"] is None for c in b["dong"][0]["o"] if c["ma"] == "don_gia"))
        header = _r(_o("Tên hàng", '<w:gridSpan w:val="2"/>'), _o("Đơn giá"))
        path = self.docx('<w:tbl><w:tblGrid><w:gridCol/><w:gridCol/><w:gridCol/></w:tblGrid>'
                         + header + _r(_o("DEMO"), _o("bộ"), _o("20000")) + '</w:tbl>')
        b = self.bang(path)["TT-05"][0]
        self.assertTrue(b["can_ra_soat"])
        self.assertIsNone(self.cell(b, 0, "ten_hang")["chuan"])
        self.assertEqual(b["dong"][0]["o"][-1]["goc"], "bộ")
        self.assertEqual(b["dong"][0]["o"][-1]["ly_do"], ["COT_NGOAI_TIEU_DE"])

    def test_cot_chua_biet_giu_chu_goc_va_bao_ra_soat(self):
        path = self.docx(_tbl(["Tên hàng", "Đơn giá kỳ", "Cột DEMO chưa biết"],
                             [_r(_o("DEMO"), _o("20000"), _o("Chữ gốc DEMO"))]))
        b = self.bang(path, "DV_KY")["TT-05"][0]
        c = b["dong"][0]["o"][2]
        self.assertEqual((c["goc"], c["chuan"]), ("Chữ gốc DEMO", None))
        self.assertTrue(c["can_ra_soat"])

    def test_pipeline_ghi_bang_canh_gia_tri_don_va_loc_ma(self):
        for loai in ("MUA_HH", "NHAP_KHAU", "DV_KY", "THUE_TS"):
            with self.subTest(loai=loai):
                raw = self.chay(self.tot, loai)
                for d, n in zip(raw["bang"], (5, 3)):
                    self.assertEqual(d["gia_tri"], "")
                    self.assertEqual(len(d["bang"][0]["dong"]), n)
                    self.assertFalse(d["bang_can_ra_soat"])
                raw = self.chay(self.loi, loai)
                self.assertTrue(all(d["bang_can_ra_soat"] for d in raw["bang"]))
        raw = self.chay(self.tot, params=[D.to_param("TT-02", "DEMO", "DEMO", bk="demo")])
        self.assertNotIn("bang", raw["bang"][0])

    def test_khong_day_du_khong_xuat_bang_gia_thanh_cong(self):
        bn = self.info(self.tot)["bang_nguon"]
        for status in ("INCOMPLETE", "KHONG_HO_TRO"):
            self.assertEqual(DHD.trich_bang_tham_so({**bn, "trang_thai": status}, "MUA_HH"), {"TT-20": [], "TT-05": []})
        path = self.docx(_p("DEMO không có bảng"))
        raw = self.chay(path)
        self.assertTrue(all(d["bang"] == [] and d["bang_can_ra_soat"] for d in raw["bang"]))

    def test_bang_khong_ghi_de_gia_tri_don_co_san(self):
        class AIGia:
            # Transport giả tại chỗ; không API/mạng, không đọc đáp án thật.
            tok_vao = tok_ra = 0
            model = url = "DEMO"

            def hoi_trich(self, *a):
                return ([{"ma": m, "gia_tri": "DEMO giá trị đơn", "trich_dan": "HỢP ĐỒNG DEMO"}
                         for m in ("TT-05", "TT-20")], 0, 0)
        with patch.object(Q, "load_key", return_value=None), patch.object(Q, "tim_dap_an", return_value=None):
            raw = self.chay(self.tot, ai=AIGia())
        self.assertTrue(all(d["gia_tri"] == "DEMO giá trị đơn" and d["bang"] for d in raw["bang"]))

    def test_xd_trung_pipeline_cu_tren_fixture_xd_hien_co(self):
        # So nguyên kết quả với pipeline bảng trước E1; hai khóa E4 đã tồn tại
        # từ E1-2 được kiểm riêng, không thuộc thay đổi E3.
        params = [D.to_param(r[0], r[1], r[2], tk=r[3], bk=r[4], muc=r[5], bat_buoc=r[6], loai_tru=r[7])
                  for r in D.MAC_DINH]
        for body in (''.join(CU.p(s) for s in CU.DOAN_XD), ''.join(CU.p(s) for s in CU.DOAN_XD) + CU.BANG_XD):
            path = self.docx(body)
            with self.subTest(bang="<w:tbl>" in body), patch.object(DHD, "trich_bang_tham_so", side_effect=E2._cam):
                old = self.chay(path, "XD", qt=Q_CU, params=params)
                new = self.chay(path, "XD", params=params)
            self.assertEqual(new.pop("loai_hop_dong"), "XD")
            self.assertEqual(new.pop("phien_ban_danh_muc"), D.CATALOG_COMMON["XD"]["sha256"])
            self.assertEqual(new, old)
            self.assertTrue(all("bang" not in d for d in new["bang"]))


if __name__ == "__main__":
    unittest.main()
