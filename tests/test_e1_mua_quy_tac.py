"""E1-2: kiểm thuần/offline trên code bản vá; mọi đầu vào đều DEMO.

Nạp dependency thuần từ review_goc, cô lập namespace; thay các cổng IO/AI bằng
stub cấm gọi. Thư mục tạm giữ lại theo AGENTS.md, không mở engine/dữ liệu thật.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
GOC = ROOT / "src/kho_tri_thuc/m4/review_goc/trich_xuat"
VA = ROOT / "tools/source6_g5_e5/trich_xuat"
SHA_GOC = "f7cfcf37ff2293d8f8ea994f1ae0a69f57d1d1d9a844f0620f018a3d285a4452"
TEN = "_e1_quy_tac_demo"


def _cam(*a, **kw):
    raise AssertionError("Không được gọi IO/AI/cloud trong test thuần")


def _nap():
    mods = {}
    pkg = types.ModuleType(TEN)
    pkg.__path__ = [str(VA)]
    mods[TEN] = pkg
    def stub(ten, **attrs):
        m = types.ModuleType(TEN + "." + ten)
        m.__dict__.update(attrs)
        mods[m.__name__] = m
    stub("cau_hinh", DANH_MUC_THAM_SO=VA / "DANH_MUC_THAM_SO.xlsx")
    stub("ai_local", CTX_MUC_LUC=1, AILoi=type("AILoi", (Exception,), {}), DaDung=type("DaDung", (Exception,), {}))
    stub("cloud", kiem_tra_cloud=_cam)
    stub("doc_hop_dong", read_contract=_cam, bang_nguon_khong_ho_tro=lambda *a: {"DEMO": True})
    stub("xuat", ghi_ket_qua_hd=_cam)
    with patch.dict(sys.modules, mods):
        for name, path in (("cau_truc", GOC / "cau_truc.py"), ("kiem_tra", GOC / "kiem_tra.py"),
                           ("xlsx_mini", GOC / "xlsx_mini.py"), ("logic_goc", GOC / "logic.py"),
                           ("danh_muc", VA / "danh_muc.py"), ("logic", VA / "logic.py"),
                           ("quy_trinh", VA / "quy_trinh.py")):
            spec = importlib.util.spec_from_file_location(TEN + "." + name, path)
            m = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = m
            mods[spec.name] = m
            spec.loader.exec_module(m)
    return mods


MODS = _nap()
L = MODS[TEN + ".logic"]
OLD = MODS[TEN + ".logic_goc"]
D = MODS[TEN + ".danh_muc"]
Q = MODS[TEN + ".quy_trinh"]
LOAI_MUA = ("DV", "MUA_HH", "THUE_TS", "NHAP_KHAU")


def _it(v, q="", **kw):
    return {"gia_tri": v, "trich_dan": q, **kw}


def _kiem(data, loai):
    return L.kiem_tra_logic(data, [{"ma": m} for m in data], loai_hop_dong=loai)


class E2QuyTacTests(unittest.TestCase):
    def test_xd_y_het_ham_goc_tren_cac_ca_gia(self):
        params = [{"ma": m, "bat_buoc": ["phạt"], "loai_tru": ["bên a"]}
                  for m in ("TT-20", "TT-21", "TT-52", "TT-53", "TT-54", "TT-55")]
        cases = [
            {},
            {"TT-20": _it("90%"), "TT-21": _it("10%")},
            {"TT-20": _it("80%"), "TT-21": _it("10%")},
            {"TT-20": _it("30%; 60%"), "TT-21": _it("5%")},
            {"TT-20": _it("90%", "đợt đầu 80%, lần sau 90%")},
            {"TT-20": _it("Không quy định", "Điều 2 phạt 3% ngày 01/01/2026")},
            {"TT-52": _it("0,1%; 0,2%", "phạt 0,1% và 0,2%", _row="R1"), "TT-53": _it("Không quy định")},
            {"TT-52": _it("0,1%", "0,1% rồi 0,2%"), "TT-53": _it("0,1%")},
            {"TT-53": _it("0,1%; 0,2%", "0,1% rồi 0,2%"), "TT-54": _it("0,2%", "bên a phạt 0,1% hoặc 0,2%")},
        ]
        rows = {"R1": {"tieu_de_dieu": "Phạt", "tieu_de_khoan": "DEMO"}}
        for data in cases:
            with self.subTest(data=data):
                expected = OLD.kiem_tra_logic(copy.deepcopy(data), params, rows)
                self.assertEqual(L.kiem_tra_logic(data, params, rows, "XD"), expected)
                self.assertEqual(L.kiem_tra_logic(data, params, rows), expected)
        self.assertEqual(hashlib.sha256((GOC / "logic.py").read_bytes()).hexdigest(), SHA_GOC)
        self.assertIn(SHA_GOC, L.__doc__)

    def test_lich_duoi_bang_va_vuot_100_dem_ca_ty_le_trung(self):
        for loai in LOAI_MUA:
            for lich, sai in (("30%; 60%", False), ("50%; 50%", False), ("100%", False),
                               ("50%; 50%; 10%", True), ("100%; 1%", True), ("60%; 50%", True)):
                with self.subTest(loai=loai, lich=lich):
                    got = _kiem({"TT-20": _it(lich), "TT-21": _it("10%"), "TT-80": _it("12 tháng")}, loai)
                    self.assertEqual(bool(got), sai)
                    if sai:
                        self.assertIn("L2:", got["TT-20"][0])

    def test_lich_ty_le_tach_don_vi(self):
        for loai in LOAI_MUA:
            for v, sai in (("100", False), ("90", False), ("100,01", True)):
                with self.subTest(loai=loai, v=v):
                    data = {"TT-20": _it(v, don_vi="%"), "TT-80": _it("12 tháng")}
                    self.assertEqual(bool(_kiem(data, loai)), sai)

    def test_coc_rieng_khong_cong_vao_lich_nhung_coc_trong_lich_can_ra_soat(self):
        for loai in LOAI_MUA:
            with self.subTest(loai=loai):
                data = {"TT-20": _it("100%"), "TT-13": _it("20%"), "TT-80": _it("12 tháng")}
                self.assertEqual(_kiem(data, loai), {})
                for lich in ("đặt cọc 20%; thanh toán 80%", "ký quỹ 10%; thanh toán 90%", "TT-13: 20%; trả 80%"):
                    data["TT-20"] = _it(lich)
                    self.assertIn("TT-13", " ".join(_kiem(data, loai)["TT-20"]))

    def test_dv_thue_can_tt80_ke_ca_khong_chon_ma_tt80(self):
        for loai in ("DV", "THUE_TS"):
            for han in (None, "", "Không quy định", "Không quy định (để trống)", "Không áp dụng"):
                with self.subTest(loai=loai, han=han):
                    data = {"TT-20": _it("90%")}
                    if han is not None:
                        data["TT-80"] = _it(han)
                    got = _kiem(data, loai)
                    self.assertIn("TT-20", got)
                    self.assertIn("TT-80", got)
            self.assertEqual(_kiem({"TT-20": _it("90%"), "TT-80": _it("12 tháng")}, loai), {})
        for loai in ("MUA_HH", "NHAP_KHAU"):
            self.assertEqual(_kiem({"TT-20": _it("90%")}, loai), {})

    def test_phat_ngay_nho_bang_lon_hon_8_phan_vi_pham(self):
        for loai in LOAI_MUA:
            for ma in ("TT-54", "TT-55"):
                for ngay, sai in ((39, False), (40, False), (41, True)):
                    with self.subTest(loai=loai, ma=ma, ngay=ngay):
                        got = _kiem({ma: _it(f"0,2%/ngày trên giá trị phần vi phạm trong {ngay} ngày")}, loai)
                        self.assertEqual(bool(got), sai)
                        if sai:
                            self.assertIn("cần rà soát", got["TT-55"][0])

    def test_phat_gia_tri_ngan_chi_tiet_o_trich_dan(self):
        for loai in LOAI_MUA:
            for ngay, sai in ((40, False), (41, True)):
                with self.subTest(loai=loai, ngay=ngay):
                    q = f"Phạt 0,2%/ngày trong {ngay} ngày trên giá trị phần nghĩa vụ hợp đồng bị vi phạm"
                    data = {"TT-54": _it("0,2", q, don_vi="%/ngày")}
                    self.assertEqual(bool(_kiem(data, loai)), sai)

    def test_khong_lay_tt80_lam_ngay_phat_khong_quy_doi_toan_hd(self):
        self.assertEqual(_kiem({"TT-54": _it("0,2%/ngày phần vi phạm"), "TT-80": _it("365 ngày")}, "DV"), {})
        got = _kiem({"TT-54": _it("0,2%/ngày giá trị hợp đồng trong 50 ngày")}, "DV")
        self.assertIn("chưa xác định", got["TT-55"][0])
        self.assertEqual(_kiem({"TT-55": _it("8% phần vi phạm")}, "DV"), {})

    def test_loai_chua_co_quy_tac_dung_chung_va_noi_ro(self):
        for loai in ("DV_KY", "DV_1L", "DEMO_LA"):
            got = _kiem({"TT-20": _it("60%; 50%"), "TT-21": _it("10%")}, loai)
            self.assertIn("quy tắc chung an toàn", got["TT-20"][0])
            self.assertTrue(any("110%" in s for s in got["TT-20"]))


class E4PhienBanTests(unittest.TestCase):
    def setUp(self):
        self.ctx = patch.dict(sys.modules, MODS)
        self.ctx.start()
        self.addCleanup(self.ctx.stop)
        self.tam = Path(tempfile.mkdtemp(prefix="e1_quytac_demo_"))
        self.cat = self.tam / "DANH_MUC_DEMO.xlsx"
        D.create_catalog(self.cat)
        self.sha = hashlib.sha256(self.cat.read_bytes()).hexdigest()
        self.reg = {k: {"catalog_id": k, "sha256": self.sha, "path": self.cat} for k in D.CATALOG_COMMON}
        self.ctx_reg = patch.dict(D.CATALOG_COMMON, self.reg)
        self.ctx_reg.start()
        self.addCleanup(self.ctx_reg.stop)
        self.params = [D.to_param("TT-20", "DEMO", "Lịch DEMO", bk="demo")]

    def _meta(self, loai):
        return {"loai_hop_dong": loai, "catalog_id": loai, "catalog_sha256": self.sha}

    def test_phien_ban_dung_sha_catalog_theo_loai_legacy_va_snapshot(self):
        for loai in self.reg:
            with self.subTest(loai=loai):
                tx = Q.TrichXuat(self.params, loai_hop_dong=loai)
                self.assertEqual((tx.loai_hop_dong, tx.phien_ban_danh_muc), (loai, self.sha))
                meta = self._meta(loai)
                tx = Q.TrichXuat(self.params, che_do="RULE_ONLY", meta=meta)
                meta["catalog_sha256"] = "0" * 64
                self.assertEqual(tx.phien_ban_danh_muc, self.sha)
                self.assertEqual(tx.meta["catalog_sha256"], self.sha)

    def test_tu_choi_snapshot_thieu_sai_va_loai_mau_thuan(self):
        with self.assertRaises(ValueError):
            Q.TrichXuat(self.params, meta=[])
        for changes in ({"catalog_sha256": "0" * 64}, {"catalog_id": "XD"}, {"loai_hop_dong": None}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                Q.TrichXuat(self.params, meta={**self._meta("DV"), **changes})
        with self.assertRaises(ValueError):
            Q.TrichXuat(self.params, meta=self._meta("DV"), loai_hop_dong="XD")
        with self.assertRaises(ValueError):
            Q.TrichXuat(self.params, loai_hop_dong="DEMO_LA")
        self.cat.write_bytes(b"DEMO thay doi")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            Q.TrichXuat(self.params, loai_hop_dong="DV")

    def _ghi(self, kq, out):
        Path(out, "DEMO_KET_QUA.json").write_text(json.dumps(kq, ensure_ascii=False), encoding="utf-8")

    def test_output_json_thuc_su_co_loai_va_phien_ban_truoc_khi_ghi(self):
        info = {"text": "DEMO lịch thanh toán", "chunks": ["DEMO lịch thanh toán"], "bang_nguon": {"DEMO": True},
                "report": {"file": "DEMO.docx", "words": 4, "articles": 0, "warnings": []}}
        for loai in LOAI_MUA + ("XD",):
            with self.subTest(loai=loai):
                tx = Q.TrichXuat(self.params, out_dir=str(self.tam / loai), che_do="RULE_ONLY", meta=self._meta(loai))
                with patch.object(Q, "read_contract", return_value=copy.deepcopy(info)), patch.object(Q, "save"), \
                     patch.object(tx, "tc_theo_quy_tac", return_value={}), \
                     patch.object(MODS[TEN + ".xuat"], "ghi_ket_qua_hd", side_effect=self._ghi), \
                     patch.object(Q, "kiem_tra_logic", wraps=L.kiem_tra_logic) as check:
                    kq = tx.xu_ly("DEMO.docx")
                self.assertEqual(kq["loai_hop_dong"], loai)
                self.assertEqual(kq["phien_ban_danh_muc"], self.sha)
                disk = next((self.tam / loai).rglob("DEMO_KET_QUA.json"))
                self.assertEqual(json.loads(disk.read_text(encoding="utf-8"))["phien_ban_danh_muc"], self.sha)
                if loai == "XD":
                    check.assert_not_called()
                else:
                    self.assertEqual(check.call_args.args[3], loai)

    def test_output_e5_khong_doc_duoc_cung_co_phien_ban(self):
        import time
        meta = {**self._meta("XD"), "mode": Q.MODE_E5}
        tx = Q.TrichXuat(self.params, che_do="RULE_ONLY", meta=meta)
        with patch.object(Q, "g5_khong_doc_duoc", return_value={"trang_thai": "CHUA_DOI_CHIEU_DUOC"}), \
             patch.object(MODS[TEN + ".xuat"], "ghi_ket_qua_hd", side_effect=self._ghi):
            kq = tx._xu_ly_e5_khong_doc("DEMO.pdf", "DEMO.pdf", "DEMO", str(self.tam), time.time(), "DEMO không đọc được")
        self.assertEqual((kq["loai_hop_dong"], kq["phien_ban_danh_muc"]), ("XD", self.sha))
