"""XS-4A: dữ liệu giả/bản khai CRM, không DB/server, file tạm hay xóa file.

Chạy: PYTHONPATH=src python -B -X utf8 -m unittest discover -s tests
      -p test_xs4_khai_bao.py -v
Không cần KHO_PG_DSN_TEST; dùng được dưới guard CODEX_NO_DELETE_FILES.
"""

from copy import deepcopy
from dataclasses import replace
import unittest
import warnings
from unittest.mock import patch

from kho_tri_thuc.ha_tang.danh_ba_engine import DanhBaEngine
from kho_tri_thuc.ha_tang.engine import Engine, KhaiBaoEngine
from kho_tri_thuc.ha_tang.khai_bao_module import (
    CheDoModule, HANH_DONG, KhaiBaoModule, PhanModule, TheDem,
    kiem_tra_danh_sach_module, tu_khai_bao_crm, ve_khai_bao_crm,
)


def phan_gia(**doi):
    return PhanModule(**{
        "ma": "danh_sach", "ten": "Danh sách giả", "duong_dan": "#gia/danh-sach",
        "quyen_xem": {"module": "GIA", "vai": ["XEM"]},
        "hanh_dong": ("XEM", "LAP", "SUA", "KIEM", "DUYET", "HUY"), **doi,
    })


def the_gia(**doi):
    return TheDem(**{
        "ma": "cho", "nhan": "Việc giả chờ", "dem": "dem_gia",
        "giai_thich": "Chỉ dùng dữ liệu giả.",
        "loc": {"phan": "danh_sach", "tham_so": {"trang_thai": "CHO"}}, **doi,
    })


def module_gia(**doi):
    return KhaiBaoModule(**{
        "ma": "gia", "ten": "Module giả", "icon": "gia", "nhom_mau": "gia",
        "thu_tu": 10, "phan": (phan_gia(),), "the": {"XEM": (the_gia(),)}, **doi,
    })


class EngineGia(Engine):
    def __init__(self, phien_ban="v1"):
        super().__init__(KhaiBaoEngine("E-GIA", phien_ban, dict, dict))

    def xu_ly(self, dau_vao):
        raise AssertionError("Kiểm khai báo không được thực thi engine.")


class KhaiBaoModuleTests(unittest.TestCase):
    def test_hop_le_du_metadata_va_mac_dinh_tat(self):
        module = module_gia()
        self.assertEqual(module.mac_dinh_cong_tac, CheDoModule.TAT)
        self.assertEqual(set(module.phan[0].hanh_dong), HANH_DONG)
        self.assertEqual(module.danh_muc_hanh_dong(), {"danh_sach": module.phan[0].hanh_dong})
        kiem_tra_danh_sach_module((module,))

    def test_ba_che_do_va_tu_choi_che_do_sai(self):
        for che_do in CheDoModule:
            with self.subTest(che_do=che_do):
                self.assertEqual(module_gia(mac_dinh_cong_tac=che_do.value).mac_dinh_cong_tac, che_do)
        with self.assertRaises(ValueError):
            module_gia(mac_dinh_cong_tac="BAT")

    def test_ma_ten_va_thu_tu_khong_hop_le(self):
        for doi in ({"ma": ""}, {"ma": " gia"}, {"ten": " "},
                    {"icon": None}, {"nhom_mau": ""}, {"thu_tu": True}, {"thu_tu": 1.5}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                module_gia(**doi)

    def test_ma_module_va_phan_phai_duy_nhat(self):
        with self.assertRaisesRegex(ValueError, "Mã module bị trùng"):
            kiem_tra_danh_sach_module((module_gia(), module_gia()))
        with self.assertRaisesRegex(ValueError, "Mã phần bị trùng"):
            module_gia(phan=(phan_gia(), phan_gia()))
        # Mã phần chỉ cần duy nhất trong module, không phải toàn hệ thống.
        kiem_tra_danh_sach_module((module_gia(), module_gia(ma="gia2")))

    def test_duong_dan_bat_dau_hash(self):
        for duong in ("/gia", "https://gia.invalid", "", None):
            with self.subTest(duong=duong), self.assertRaises(ValueError):
                phan_gia(duong_dan=duong)

    def test_hanh_dong_sai_hoac_trung_bi_tu_choi(self):
        for cac_ma in (("XUAT",), ("xem",), ("XEM", "XEM"), ("XEM", "")):
            with self.subTest(cac_ma=cac_ma), self.assertRaises(ValueError):
                phan_gia(hanh_dong=cac_ma)

    def test_the_trung_trong_vai_va_tham_chieu_phan_sai(self):
        with self.assertRaisesRegex(ValueError, "Mã thẻ trong nhóm bị trùng"):
            module_gia(the={"XEM": (the_gia(), the_gia())})
        with self.assertRaisesRegex(ValueError, "tham chiếu phần"):
            module_gia(the={"XEM": (the_gia(loc={"phan": "khong_co", "tham_so": {}}),)})
        # Một thẻ có thể xuất hiện ở hai nhóm vai, giống CRM hiện có.
        module_gia(the={"XEM": (the_gia(),), "CFO": (the_gia(),)})

    def test_kiem_lai_sau_khi_chinh_du_lieu(self):
        module = module_gia()
        module.phan[0].hanh_dong = ("XUAT",)
        with self.assertRaises(ValueError):
            module.danh_muc_hanh_dong()

    def test_khong_tu_sap_xep_man_hay_hanh_dong(self):
        truoc = phan_gia(ma="truoc", thu_tu=90, hanh_dong=("DUYET", "XEM"))
        sau = phan_gia(ma="sau", thu_tu=10, hanh_dong=("LAP", "XEM"))
        module = module_gia(phan=(truoc, sau), the={})
        self.assertEqual(list(module.danh_muc_hanh_dong().items()),
                         [("truoc", ("DUYET", "XEM")), ("sau", ("LAP", "XEM"))])


class DanhBaModuleTests(unittest.TestCase):
    def test_engine_ton_tai_khong_thuc_thi_hay_chon_version(self):
        danh_ba = DanhBaEngine()
        danh_ba.dang_ky(EngineGia())
        danh_ba.dang_ky(EngineGia("v2"), phien_ban_moi=True)
        self.assertEqual(module_gia(engine_dung=("E-GIA",)).kiem_tra_engine(danh_ba), ())

    def test_thieu_engine_tu_choi_mac_dinh(self):
        with self.assertRaisesRegex(ValueError, "E-THIEU"):
            module_gia(engine_dung=("E-THIEU",)).kiem_tra_engine(DanhBaEngine())

    def test_thieu_engine_canh_bao_theo_co_va_giu_thu_tu(self):
        module = module_gia(engine_dung=("E-Z", "E-A"))
        with self.assertWarnsRegex(UserWarning, "E-Z, E-A"):
            self.assertEqual(module.kiem_tra_engine(DanhBaEngine(), nghiem_ngat=False), ("E-Z", "E-A"))
        self.assertEqual(module.engine_dung, ("E-Z", "E-A"))

    def test_khong_khai_engine_khong_canh_bao(self):
        with warnings.catch_warnings(record=True) as canh_bao:
            warnings.simplefilter("always")
            self.assertEqual(module_gia().kiem_tra_engine(DanhBaEngine()), ())
        self.assertEqual(canh_bao, [])

    def test_ma_engine_trung_va_co_sai(self):
        with self.assertRaises(ValueError):
            module_gia(engine_dung=("E-GIA", "E-GIA"))
        with self.assertRaises(ValueError):
            module_gia().kiem_tra_engine(DanhBaEngine(), nghiem_ngat="False")


class ChuyenCrmTests(unittest.TestCase):
    def test_crm_round_trip_moi_truong_va_thu_tu(self):
        from kho_tri_thuc.giao_dien.khung_khai_bao import MODULE

        truoc = deepcopy(MODULE["crm"])
        module = tu_khai_bao_crm()
        sau = ve_khai_bao_crm(module)
        self.assertEqual(sau, truoc)
        self.assertEqual([p.ma for p in module.phan], [p["ma"] for p in truoc["phan"]])
        self.assertEqual(list(module.the), list(truoc["the"]))
        for vai in truoc["the"]:
            self.assertEqual([t.ma for t in module.the[vai]], [t["ma"] for t in truoc["the"][vai]])
        self.assertEqual(module.mac_dinh_cong_tac, CheDoModule.VAN_HANH)
        self.assertEqual(module.engine_dung, ())
        self.assertTrue(all(not p.hanh_dong for p in module.phan))
        self.assertEqual(MODULE["crm"], truoc)

    def test_ban_sao_khong_sua_quyen_va_bo_loc_nguon(self):
        from kho_tri_thuc.giao_dien.khung_khai_bao import MODULE

        truoc = deepcopy(MODULE["crm"])
        module = tu_khai_bao_crm()
        ra = ve_khai_bao_crm(module)
        ra["phan"][0]["quyen"]["vai"].append("VAI_GIA")
        module.phan[0].quyen_xem["vai"].append("VAI_KHAC")
        module.the["BAN_HANG"][0].loc["tham_so"]["trang_thai"] = "GIA"
        self.assertEqual(MODULE["crm"], truoc)
        self.assertNotIn("VAI_GIA", module.phan[0].quyen_xem["vai"])

    def test_giu_truong_bo_sung_va_tam_dung(self):
        from kho_tri_thuc.giao_dien.khung_khai_bao import MODULE

        nguon = deepcopy(MODULE["crm"])
        nguon["tam_dung"] = True
        nguon["mo_rong"] = {"gia": [1, 2]}
        nguon["phan"][0]["mo_rong"] = ["gia"]
        nguon["the"]["BAN_HANG"][0]["mo_rong"] = {"gia": True}
        with patch.dict(MODULE, {"crm": nguon}):
            module = tu_khai_bao_crm()
            self.assertEqual(module.mac_dinh_cong_tac, CheDoModule.TAT)
            self.assertEqual(ve_khai_bao_crm(module), nguon)

    def test_khong_lam_mat_metadata_moi_khi_xuat_crm_cu(self):
        for doi in ({"mac_dinh_cong_tac": CheDoModule.THU}, {"engine_dung": ("E-GIA",)},
                    {"phan": (phan_gia(),), "the": {}}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                ve_khai_bao_crm(replace(tu_khai_bao_crm(), **doi))


if __name__ == "__main__":
    unittest.main()
