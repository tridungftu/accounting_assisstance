"""M9 — adapter nguồn #9 (thuần, không DB): profile/header pin, shape native 16 key, precision theo field, khóa/trùng/mơ hồ, đồ thị typed
theo alias. Expected viết theo oracle tài liệu (REVIEW-CONTRACT-M9-INPUTS-01, proposal revision2), không lấy từ output sản phẩm."""

from __future__ import annotations

import json
import unittest
from datetime import date
from decimal import Decimal

from kho_tri_thuc.ha_tang.primitives import sha256
from kho_tri_thuc.kiem_chung import fixtures_m9 as F
from kho_tri_thuc.nguon import vay_9 as V


def _g(snap, cty="CT_DEMO_A", bang_lai=None):
    return V.do_thi(snap, bang_lai, {cty})


class GiaoDienTinhTests(unittest.TestCase):
    def test_trang_khoan_vay_trong_shell(self):
        import re
        from pathlib import Path
        assets = Path(__file__).resolve().parents[1] / "src" / "kho_tri_thuc" / "giao_dien" / "assets"
        html, js = (assets / "index.html").read_text(encoding="utf-8"), (assets / "app.js").read_text(encoding="utf-8")
        self.assertIn('data-page="khoanvay"', html)
        self.assertIn('id="page-khoanvay"', html)
        ids = set(re.findall(r'\$\("(m9-[a-z-]+)"\)', js))
        self.assertGreater(len(ids), 10)
        self.assertEqual({i for i in ids if f'id="{i}"' not in html}, set())  # mọi phần tử JS dùng đều có trong trang
        pages = re.search(r"const pages = \{([^}]*)\}", js).group(1)
        self.assertEqual({k for k in re.findall(r"(\w+):", pages) if f'id="page-{k}"' not in html}, set())
        self.assertNotIn("innerHTML", js)
        for path in ("mau", "lap", "anh-xa", "anh-xa/dong", "kiem", "duyet", "duyet-v4", "tu-choi", "pham-vi", "m1-sao-ke", "goi-y", "xem-truoc", "xac-nhan", "go", "file-soat"):
            self.assertRegex(js, rf'm9(Act|Post)\("{re.escape(path)}"', path)  # mọi thao tác API có nút thật


class ProfileTests(unittest.TestCase):
    def test_header_set_pin_khop_hash_tai_lieu(self):
        self.assertEqual(len(V.HEADER_TEXT.encode("utf-8")), 1042)
        self.assertEqual(sha256(V.HEADER_TEXT.encode("utf-8")), V.HEADER_SET_SHA256)  # 3d4d00… theo proposal §1.1
        self.assertEqual(len(V.NATIVE_KEYS), 16)
        self.assertEqual(V.profile_sha256(V.PROFILE_NATIVE), V.profile_sha256(json.loads(json.dumps(V.PROFILE_NATIVE))))

    def test_shape_day_du_thieu_key_key_la_version(self):
        ok = V.doc_native(F.bytes_cua(F.native_demo()))
        self.assertEqual((ok.state, ok.coverage_kind, ok.loi), ("VALIDATED", "FULL_SHAPE", []))
        thieu = V.doc_native(F.bytes_cua(F.native_demo(thieu_key=True)))  # S19: không tự thêm section rỗng
        self.assertEqual((thieu.state, thieu.coverage_kind), ("PARTIAL", "PARTIAL"))
        self.assertIn("THIEU_KEY:seqS,seqL,shortLoans,rates,bankCfg,manualRows", thieu.loi)
        la = F.native_demo()
        la["vayNganHan"] = []  # tên response `load` khác profile native `vayNH`
        self.assertEqual(V.doc_native(F.bytes_cua(la)).state, "REJECTED")
        v7 = F.native_demo()
        v7["version"] = 7
        self.assertEqual(V.doc_native(F.bytes_cua(v7)).loi, ["VERSION_KHONG_HO_TRO"])
        root = V.doc_native(F.bytes_cua(F.native_demo(profile_root=True)))  # S14: version 6 nhưng lịch gốc root thiếu maKheUoc
        self.assertEqual(root.state, "REJECTED")
        self.assertTrue(any(x.startswith("HEADER_KHONG_KHOP_PROFILE:LichTraGoc") for x in root.loi))
        dup = b'{"version":6,"version":6}'
        self.assertEqual(V.doc_native(dup).state, "REJECTED")
        nan = F.bytes_cua(F.native_demo()).replace(b'"hanMuc": 100000000', b'"hanMuc": NaN')
        self.assertEqual(V.doc_native(nan).state, "REJECTED")
        dao = F.native_demo()
        dao["longLoans"][0] = dict(reversed(list(dao["longLoans"][0].items())))  # đảo cột vật lý vẫn đọc theo tên
        self.assertEqual(V.noi_dung_typed(_g(V.doc_native(F.bytes_cua(dao)))[("DaiHan", "CT_DEMO_A", "KV-A-01")]),
                         V.noi_dung_typed(_g(ok)[("DaiHan", "CT_DEMO_A", "KV-A-01")]))


class SoVaThoiGianTests(unittest.TestCase):
    def test_precision_theo_field(self):
        self.assertEqual((V.tien(100000000, "VND").value, V.tien(100000000, "VND").precision), (100000000, "PROVEN"))
        self.assertEqual((V.tien("9007199254740993", "VND").value, V.tien("9007199254740993", "VND").precision), (9007199254740993, "PROVEN"))  # S09
        self.assertEqual(V.tien(9007199254740992, "VND").precision, "UNPROVEN")  # S10: đã qua Number, không phục hồi
        self.assertEqual(V.tien(Decimal("1000.5"), "USD").value, 100050)
        self.assertEqual(V.tien(Decimal("12345678901234567.89"), "USD").precision, "UNPROVEN")
        for v, cur, loi in ((True, "VND", "BOOLEAN_KHONG_PHAI_SO"), (Decimal("1.5"), "VND", "SAI_SCALE"), ("1.000", "VND", "SO_TEXT_PHAN_CACH_MO_HO"),
                            ("1,000", "VND", "SO_TEXT_PHAN_CACH_MO_HO"), (1, None, "THIEU_TIEN_TE"), (1, "EUR", "TIEN_TE_KHONG_HO_TRO"),
                            (10 ** 20, "VND", "VUOT_INT64")):
            self.assertEqual(V.tien(v, cur).loi, loi, (v, cur))
        self.assertEqual((V.tien(None, "VND").value, V.tien("", "VND").value, V.tien(0, "VND").value), (None, None, 0))  # NULL ≠ 0
        self.assertEqual(V.ty_le(7.5 if False else Decimal("7.5")).value, Decimal("7.5"))  # %/năm giữ 7.5 (không 0.075)
        self.assertEqual(V.ngay("2026-10-15").value, date(2026, 10, 15))
        self.assertEqual(V.ngay("15/10/2026").loi, "NGAY_SAI_DINH_DANG")


class DoThiTests(unittest.TestCase):
    def setUp(self):
        self.snap = V.doc_native(F.bytes_cua(F.native_demo()))

    def test_s01_hai_draw_cung_ky_va_namespace_cong_ty(self):
        g = _g(self.snap)[("DaiHan", "CT_DEMO_A", "KV-A-01")]
        self.assertEqual(sorted((x["nghia_vu_key"], x["amount"]) for x in g["lich"]),
                         [("DRAW/KU-A-01/1/GOC", 12000000), ("DRAW/KU-A-02/1/GOC", 8000000)])
        self.assertEqual(sorted(g["draws"]), ["KU-A-01", "KU-A-02"])
        self.assertEqual(g["blockers"], set())
        self.assertNotIn(("DaiHan", "CT_DEMO_B", "KV-B-01"), _g(self.snap))  # chỉ công ty đã map vào PN
        self.assertIn(("DaiHan", "CT_DEMO_B", "KV-B-01"), _g(self.snap, "CT_DEMO_B"))
        self.assertEqual([r["ap_dung_tu"] for r in sorted(g["rates"], key=lambda r: r["ap_dung_tu"])], [date(2026, 1, 16), date(2026, 4, 1)])  # S06

    def test_s03_s04_phat_sinh_trung_va_xung_dot(self):
        trung = _g(V.doc_native(F.bytes_cua(F.native_demo(phat_sinh_trung=True))))[("DaiHan", "CT_DEMO_A", "KV-A-01")]
        self.assertEqual(len(trung["events"]), 1)  # một sự kiện logic
        self.assertEqual(trung["blockers"], set())
        snap = V.doc_native(F.bytes_cua(F.native_demo(phat_sinh_xung_dot=True)))
        self.assertEqual([r.state for r in snap.rows if r.section == "PhatSinh"], ["XUNG_DOT", "XUNG_DOT"])  # cả hai raw giữ, không chọn dòng cuối
        g = _g(snap)[("DaiHan", "CT_DEMO_A", "KV-A-01")]
        self.assertEqual(g["events"], [])
        self.assertIn("TRUNG_KHOA_KHAC_NOI_DUNG:PhatSinh", g["blockers"])

    def test_s05_s16_pham_vi_va_rate_mo_ho(self):
        g = _g(V.doc_native(F.bytes_cua(F.native_demo(loan_overlap=True))))[("DaiHan", "CT_DEMO_A", "KV-A-01")]
        self.assertEqual(sorted(x["pham_vi"] for x in g["lich"]), ["DRAW", "DRAW", "LOAN"])  # giữ cả hai; CSDL chặn duyệt CHO_XAC_NHAN_PHAM_VI_LICH
        snap = V.doc_native(F.bytes_cua(F.native_demo(rate_mo_ho=True)))
        rates = [r for r in snap.rows if r.section == "LichLaiSuat" and r.raw["maKheUoc"] == "KU-A-01"]
        self.assertEqual({(r.state, r.error) for r in rates}, {("MO_HO", "AMBIGUOUS_RATE_PARENT")})
        self.assertEqual(_g(snap)[("DaiHan", "CT_DEMO_A", "KV-A-01")]["rates"], [])  # không gán theo thứ tự dòng

    def test_lc_va_nhan_no_cung_identity(self):
        lc = _g(self.snap)[("VayNganHan", "CT_DEMO_A", "NH-A-01")]
        nn = _g(V.doc_native(F.bytes_cua(F.native_demo(lc_nhan_no=True))))[("VayNganHan", "CT_DEMO_A", "NH-A-01")]
        self.assertEqual((lc["kind"], nn["kind"]), ("LC", "SHORT_TERM"))  # cùng khóa alias, kind chỉ ở revision
        self.assertEqual((lc["facts"]["so_vay_vnd_minor"], lc["facts"]["so_nguyen_te_minor"], lc["facts"]["nguyen_te_code"]), (None, 1000000, "USD"))  # S07
        self.assertEqual(nn["facts"]["so_vay_vnd_minor"], 250000000)
        self.assertEqual(lc["facts"]["source_fx_rate"], 25000)  # tỷ giá nguồn giữ riêng, không tự quy đổi

    def test_revision_hash_on_dinh_va_doi_khi_co_y_nghia(self):
        a = V.noi_dung_typed(_g(self.snap)[("DaiHan", "CT_DEMO_A", "KV-A-01")])
        b = F.native_demo()
        b["exportedAt"] = "2026-12-31T00:00:00+07:00"  # chỉ đổi thời điểm xuất → không revision mới
        self.assertEqual(V.noi_dung_typed(_g(V.doc_native(F.bytes_cua(b)))[("DaiHan", "CT_DEMO_A", "KV-A-01")]), a)
        c = V.noi_dung_typed(_g(V.doc_native(F.bytes_cua(F.native_demo(draw_doi_so=True))))[("DaiHan", "CT_DEMO_A", "KV-A-01")])
        self.assertNotEqual(c, a)

    def test_bang_lai_xac_nhan_thanh_nghia_vu_lai_phi(self):
        bl = V.doc_bang_lai(F.bytes_cua(F.bang_lai_demo()))
        self.assertEqual(bl.state, "VALIDATED")
        g = _g(self.snap, bang_lai=bl)[("DaiHan", "CT_DEMO_A", "KV-A-01")]
        lai = {x["nghia_vu_key"]: (x["amount"], x["amount_kind"]) for x in g["lich"] if x["cau_phan"] != "GOC"}
        self.assertEqual(lai, {"DRAW/KU-A-01/1/LAI": (800000, "CONFIRMED_ACCOUNTING_RESULT"), "DRAW/KU-A-01/1/PHI": (50000, "CONFIRMED_ACCOUNTING_RESULT")})
        sai = F.bang_lai_demo()
        sai["rows"][0]["tienTe"] = "USD"
        g = _g(self.snap, bang_lai=V.doc_bang_lai(F.bytes_cua(sai)))[("DaiHan", "CT_DEMO_A", "KV-A-01")]
        self.assertIn("KHAC_TIEN_TE_HOP_DONG:BangLai", g["blockers"])  # không quy đổi
        self.assertEqual(V.doc_bang_lai(b'{"format":"x"}').state, "REJECTED")


if __name__ == "__main__":
    unittest.main()
