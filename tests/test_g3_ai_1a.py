"""AI-1a: tái dùng DTO gốc, không client mới, không gọi AI/CSDL thật.

Phần manifest chưa được kiểm: schema G2-17 bắt buộc capability không rỗng,
trong khi schema đầu vào ai.hoi@1 thuộc AI-1b còn chờ duyệt.
"""

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path
import subprocess
import sys
import unittest

from kho_tri_thuc.engines.e_hoi_ai import dto
from kho_tri_thuc.tri_thuc import cong_ai


ROOT = Path(__file__).resolve().parents[1]


class DtoAI1aTests(unittest.TestCase):
    def test_dto_la_chinh_lop_goc(self):
        self.assertEqual(set(dto.__all__), {"YeuCauAI", "TruongAI", "KetQuaAI"})
        for ten in dto.__all__:
            with self.subTest(dto=ten):
                self.assertIs(getattr(dto, ten), getattr(cong_ai, ten))

    def test_giu_du_lieu_va_hanh_vi_dto_goc(self):
        yeu_cau = dto.YeuCauAI(
            "HOI_DAP_VAY", "Lãi suất DEMO 5%.", "Trích lãi suất.",
            ("lai_suat",), (("DEMO", "CONG_TY"),),
            "PN-DEMO", "VIEC-DEMO", "DX-DEMO",
        )
        truong = dto.TruongAI("lai_suat", "5%", yeu_cau.van_ban, "CLOUD", "4%")
        ket_qua = dto.KetQuaAI(
            yeu_cau.loai_viec, "VANG", {"lai_suat": truong}, "LOCAL+CLOUD",
            "Đề xuất DEMO.", ("DUOI_NGUONG",), ("truong_demo",), "YC-DEMO",
        )
        self.assertEqual(yeu_cau.dinh_danh_da_biet, (("DEMO", "CONG_TY"),))
        self.assertEqual(
            (yeu_cau.phap_nhan_id, yeu_cau.viec_id, yeu_cau.de_xuat_id),
            ("PN-DEMO", "VIEC-DEMO", "DX-DEMO"),
        )
        self.assertIs(ket_qua.truong["lai_suat"], truong)
        self.assertEqual(truong.gia_tri_local, "4%")
        self.assertEqual(ket_qua.ly_do, ("DUOI_NGUONG",))
        self.assertEqual(ket_qua.truong_bi_loai, ("truong_demo",))
        self.assertTrue(ket_qua.co_ket_qua)
        self.assertFalse(dto.KetQuaAI("HOI_DAP_VAY", "DO", {}, "KHONG", "DEMO").co_ket_qua)
        for doi_tuong, ten in ((yeu_cau, "van_ban"), (truong, "gia_tri"), (ket_qua, "muc")):
            with self.subTest(dto=type(doi_tuong).__name__):
                with self.assertRaises(FrozenInstanceError):
                    setattr(doi_tuong, ten, "thay đổi")

    def test_khong_them_import_client_mang_hay_csdl(self):
        # DTO gốc nằm trực tiếp trong cổng; transport chỉ dùng standard library.
        cay = ast.parse(Path(dto.__file__).read_text(encoding="utf-8"))
        imports = [node for node in ast.walk(cay) if isinstance(node, (ast.Import, ast.ImportFrom))]
        self.assertEqual(len(imports), 1)
        self.assertIsInstance(imports[0], ast.ImportFrom)
        self.assertEqual(imports[0].module, "kho_tri_thuc.tri_thuc.cong_ai")
        self.assertEqual({item.name for item in imports[0].names}, set(dto.__all__))
        self.assertFalse(any(isinstance(node, (ast.ClassDef, ast.Call)) for node in ast.walk(cay)))

    def test_import_trong_tien_trinh_moi_khong_goi_mang_hay_tao_cong(self):
        self._kiem_import_trong_tien_trinh_moi(gia_lap_thu_vien=False)

    def test_import_khong_cham_thu_vien_mang_csdl_gia_co_mat(self):
        self._kiem_import_trong_tien_trinh_moi(gia_lap_thu_vien=True)

    def _kiem_import_trong_tien_trinh_moi(self, *, gia_lap_thu_vien):
        # Runtime có thể nạp client từ sitecustomize trước khi mã test chạy.
        # Đo phần phát sinh do import và bắt cả import module đã có trong cache.
        ma = '''
import builtins
import sys
from types import ModuleType
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
cam = {"openai", "anthropic", "requests", "httpx", "psycopg", "psycopg2"}
thu_vien_gia = {}
da_cham = []
if sys.argv[2] == "1":
    def cham_thuoc_tinh(ten):
        da_cham.append(ten)
        raise AssertionError("Khong duoc cham client gia: " + ten)

    for ten in cam:
        module = ModuleType(ten)
        module.__getattr__ = cham_thuoc_tinh
        thu_vien_gia[ten] = module
    sys.modules.update(thu_vien_gia)

import_goc = builtins.__import__
def kiem_import(ten, *args, **kwargs):
    if ten.split(".")[0] in cam:
        da_cham.append(ten)
        raise AssertionError("Khong duoc import client: " + ten)
    return import_goc(ten, *args, **kwargs)

with patch("socket.socket", side_effect=AssertionError("Không được mở socket")), \\
     patch("socket.create_connection", side_effect=AssertionError("Không được kết nối")), \\
     patch("socket.getaddrinfo", side_effect=AssertionError("Không được tra DNS")), \\
     patch("builtins.__import__", side_effect=kiem_import):
    truoc = set(sys.modules)
    from kho_tri_thuc.tri_thuc import cong_ai
    with patch.object(cong_ai, "CongAI", side_effect=AssertionError("Không được tạo cổng")), \\
         patch.object(cong_ai, "BoGhiPostgres", side_effect=AssertionError("Không được tạo bộ ghi PG")):
        from kho_tri_thuc.engines.e_hoi_ai import dto
        for ten in dto.__all__:
            assert getattr(dto, ten) is getattr(cong_ai, ten)
phat_sinh = sorted(set(sys.modules) - truoc)
assert not any(ten.split(".")[0] in cam for ten in phat_sinh), phat_sinh
assert not da_cham, da_cham
for ten, module in thu_vien_gia.items():
    assert sys.modules[ten] is module, ten
'''
        ket_qua = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", "-c", ma, str(ROOT / "src"),
             "1" if gia_lap_thu_vien else "0"],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(ket_qua.returncode, 0, ket_qua.stderr)


if __name__ == "__main__":
    unittest.main()
