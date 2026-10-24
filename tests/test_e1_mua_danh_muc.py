"""E1-1: registry bản vá #6, thuần/offline, không nạp test_source6_g5_e5 hay #6 thật.

Overlay chỉ chứa ba tệp vá. Cấu hình thử chỉ cấp đường dẫn XD; xlsx_mini dùng
nguyên bộ đọc/ghi đã có trong repo. Namespace riêng không làm bẩn trich_xuat.
Danh mục thiết kế chỉ đọc; thiếu trên máy thì skip riêng từng loại, có lý do.
Thư mục DEMO tạm giữ lại, không xóa theo AGENTS.md.
"""
from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "tools" / "source6_g5_e5"
REFERENCE = ROOT / "docs" / "M4-REVIEW-REFERENCE-20261020" / "trich_xuat"
THIET_KE = Path(r"D:\Claude\Phan mem ho tro ke toan\THIET-KE-MODULE-DE-CHOT-2026-10-20\tham-so-hop-dong")
XD_SHA = "05846a2acd60f2cde708d13a163a137ee3fb0b4e08fd84f85a7e14e7ef861bcd"
XD_PATH = OVERLAY / "trich_xuat" / "DANH_MUC_THAM_SO.xlsx"
SO_MA = {"DV": 30, "MUA_HH": 46, "THUE_TS": 44, "NHAP_KHAU": 49, "DV_KY": 45, "DV_1L": 42}


def _nap_danh_muc():
    """Nạp đúng code overlay; chỉ cấp các dependency thuần, không cấu hình/AI nguồn."""
    ten = "_e1_catalog_test"
    goi = types.ModuleType(ten)
    goi.__path__ = [str(OVERLAY / "trich_xuat")]
    cau_hinh = types.ModuleType(ten + ".cau_hinh")
    cau_hinh.DANH_MUC_THAM_SO = XD_PATH
    # Cùng cách đặt sys.path như tiến trình con của test_source6_g5_e5,
    # nhưng không import/chạy module đó và không cần cây #6 ngoài repo.
    with patch.object(sys, "path", [str(OVERLAY), *sys.path]), patch.dict(
        sys.modules, {ten: goi, ten + ".cau_hinh": cau_hinh}
    ):
        for mod, path in (("xlsx_mini", REFERENCE / "xlsx_mini.py"),
                          ("danh_muc", OVERLAY / "trich_xuat" / "danh_muc.py")):
            spec = importlib.util.spec_from_file_location(ten + "." + mod, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
        return module


D = _nap_danh_muc()


class E1RegistryTests(unittest.TestCase):
    def test_dung_cac_loai_va_duong_dan_canh_xd(self):
        self.assertEqual(set(D.CATALOG_COMMON), {"XD", *SO_MA})
        for loai, reg in list(D.CATALOG_COMMON.items()):
            with self.subTest(loai=loai):
                self.assertEqual(set(reg), {"catalog_id", "sha256", "path"})
                self.assertEqual(reg["catalog_id"], loai)
                self.assertRegex(reg["sha256"], r"^[0-9a-f]{64}$")
                ten = "DANH_MUC_THAM_SO.xlsx" if loai == "XD" else f"DANH_MUC_THAM_SO_{loai}.xlsx"
                self.assertEqual(Path(reg["path"]), XD_PATH.with_name(ten))

    def test_nap_du_7_loai_qua_ham_bang_file_demo(self):
        tam = Path(tempfile.mkdtemp(prefix="e1_catalog_demo_"))
        for loai, reg in list(D.CATALOG_COMMON.items()):
            with self.subTest(loai=loai):
                path = tam / Path(reg["path"]).name
                D.create_catalog(path)
                sha = hashlib.sha256(path.read_bytes()).hexdigest()
                with patch.dict(D.CATALOG_COMMON, {loai: {**reg, "path": path, "sha256": sha}}):
                    got = D.danh_muc_theo_loai(loai)
                    self.assertIsInstance(got, Path)
                    self.assertEqual(got, path)
                    self.assertEqual(len(D.read_catalog(got)), 37)

    def test_loai_la_thieu_sai_kieu_khong_fallback(self):
        with patch.object(Path, "read_bytes", side_effect=AssertionError("Không được đọc XD")):
            for loai in ("LA", "KCN", "", "xd", " DV", None, [], {}):
                with self.subTest(loai=loai), self.assertRaisesRegex(ValueError, "chưa đăng ký"):
                    D.danh_muc_theo_loai(loai)

    def test_thieu_file_khong_tu_tao_danh_muc_xd(self):
        tam = Path(tempfile.mkdtemp(prefix="e1_catalog_thieu_"))
        for loai, reg in list(D.CATALOG_COMMON.items()):
            with self.subTest(loai=loai):
                path = tam / Path(reg["path"]).name
                with patch.dict(D.CATALOG_COMMON, {loai: {**reg, "path": path}}):
                    with self.assertRaisesRegex(FileNotFoundError, "Thiếu danh mục.*" + loai):
                        D.danh_muc_theo_loai(loai)
                self.assertFalse(path.exists())

    def test_sha_lech_khong_tra_file_khong_fallback(self):
        tam = Path(tempfile.mkdtemp(prefix="e1_catalog_sha_"))
        for loai, reg in list(D.CATALOG_COMMON.items()):
            with self.subTest(loai=loai):
                path = tam / Path(reg["path"]).name
                raw = b"DEMO: khong phai danh muc da ghim"
                path.write_bytes(raw)
                with patch.dict(D.CATALOG_COMMON, {loai: {**reg, "path": path}}):
                    with self.assertRaisesRegex(ValueError, "SHA-256.*" + loai + ".*lệch"):
                        D.danh_muc_theo_loai(loai)
                self.assertEqual(path.read_bytes(), raw)

    def test_xd_giu_nguyen_sha_path_va_bo_trich_e5(self):
        self.assertEqual(D.CATALOG_COMMON["XD"], {"catalog_id": "XD", "sha256": XD_SHA, "path": XD_PATH})
        self.assertEqual(D.bo_trich_e5("XD"), {
            "TC-01": ("QUY_TAC_TC", "text"), "TC-02": ("QUY_TAC_TC", "ngay"),
            "TT-02": ("NEO_DONG", "tien"), "TT-04": ("NEO_DONG", "so"),
            "TT-10": ("NEO_DONG", "so"), "TT-20": ("BANG_DONG", "bang"),
        })

    def test_loai_mua_chua_co_anh_xa_e5(self):
        self.assertEqual(set(D.BO_TRICH_E5), {"XD"})
        for loai in SO_MA:
            with self.subTest(loai=loai):
                self.assertEqual(D.bo_trich_e5(loai), {})


class E1DanhMucThietKeTests(unittest.TestCase):
    def _kiem_thiet_ke(self, loai):
        path = THIET_KE / f"DANH_MUC_THAM_SO_{loai}.xlsx"
        if not path.is_file():
            self.skipTest(f"Không có danh mục thiết kế {loai} trên máy: {path}; chưa kiểm số mã/cột/SHA")
        reg = D.CATALOG_COMMON[loai]
        # Chỉ đổi vị trí file trong test; giữ nguyên SHA production để phát hiện lệch thiết kế.
        with patch.dict(D.CATALOG_COMMON, {loai: {**reg, "path": path}}):
            da_kiem = D.danh_muc_theo_loai(loai)
            rows = D.read_catalog(da_kiem)
            params = D.load_params(da_kiem)
        head = D.read_xlsx(da_kiem)[0]
        self.assertEqual(len(head), 10)
        # Cùng mười cột nhận diện bằng tiền tố như read_catalog, chấp nhận khóa/khoá.
        prefixes = ("mã", "nhóm", "mô tả", "từ khoá tiêu đề", "từ khoá nội dung", "dùng",
                    "mức", "từ khoá bắt buộc", "từ khoá loại trừ", "luôn hỏi")
        for h, prefix in zip(head, prefixes):
            self.assertTrue(str(h).strip().lower().replace("khóa", "khoá").startswith(prefix), h)
        self.assertEqual(len(rows), SO_MA[loai])
        self.assertTrue(all(set(r) == set(D.KHOA) and r["ma"] and r["mo_ta"] for r in rows))
        self.assertEqual(len({r["ma"] for r in rows}), len(rows), "Trùng mã danh mục")
        self.assertEqual([p["ma"] for p in params], [r["ma"] for r in rows if r["dung"]])
        if loai == "DV":
            self.assertEqual(len(params), 27)

    def test_dv_30_ma_10_cot(self):
        self._kiem_thiet_ke("DV")

    def test_mua_hh_46_ma_10_cot(self):
        self._kiem_thiet_ke("MUA_HH")

    def test_thue_ts_44_ma_10_cot(self):
        self._kiem_thiet_ke("THUE_TS")

    def test_nhap_khau_49_ma_10_cot(self):
        self._kiem_thiet_ke("NHAP_KHAU")

    def test_dv_ky_45_ma_10_cot(self):
        self._kiem_thiet_ke("DV_KY")

    def test_dv_1l_42_ma_10_cot(self):
        self._kiem_thiet_ke("DV_1L")


if __name__ == "__main__":
    unittest.main()
