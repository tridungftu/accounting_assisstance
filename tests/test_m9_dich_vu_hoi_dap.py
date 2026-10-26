"""M9-2c: đoạn hợp đồng DEMO trong bộ nhớ, cổng AI giả, không mạng."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from kho_tri_thuc.m9 import hoi_dap_vay
from kho_tri_thuc.m9.chi_muc_vay import ChiMucVay
from kho_tri_thuc.m9.dich_vu_hoi_dap import hoi
from kho_tri_thuc.tri_thuc.cong_ai import CongAI, KetQuaAI, TruongAI


CAU_TRICH = "Lãi suất cho vay DEMO là 8,5%/năm."
TRA_LOI = "8,5%/năm"
CAU_HOI = "Cho hỏi lãi suất cho vay DEMO là bao nhiêu?"


class DichVuHoiDapTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.socket", "kho_tri_thuc.tri_thuc.cong_ai._goi_json"):
            guard = patch(target, side_effect=AssertionError("Cấm mạng/AI thật"))
            guard.start()
            self.addCleanup(guard.stop)
        self.chi_muc = ChiMucVay()
        self.doan = [{
            "trang_dau": 2, "trang_cuoi": 2, "dieu": "2. Lãi suất DEMO",
            "khoan": "1", "diem": None, "ma_doan": "doan-DEMO-A",
            "cau": [CAU_TRICH],
        }]
        self.chi_muc.them("DEMO-A", "DEMO-A.docx", self.doan)
        self.cong = Mock(spec=CongAI)
        self.cong.goi.return_value = KetQuaAI(
            "HOI_DAP_VAY", "VANG",
            {"tra_loi": TruongAI("tra_loi", TRA_LOI, CAU_TRICH, "LOCAL")},
            "LOCAL", "Đề xuất DEMO",
        )
        self.ghi = Mock()

    def hoi_demo(self, cau_hoi=CAU_HOI, **kwargs):
        return hoi(cau_hoi, chi_muc=self.chi_muc, cong_ai=self.cong,
                   nguoi_hoi="nguoi-DEMO", ghi_nhat_ky=self.ghi, **kwargs)

    def kiem_nhat_ky(self, ket_qua, cau_hoi=CAU_HOI):
        self.ghi.assert_called_once()
        ban_ghi = self.ghi.call_args.args[0]
        self.assertEqual(set(ban_ghi), {
            "nguoi_hoi", "luc", "cau_hoi", "trang_thai", "so_trich_dan",
            "ma_doan_trich_dan",
        })
        self.assertEqual(ban_ghi["nguoi_hoi"], "nguoi-DEMO")
        self.assertEqual(ban_ghi["cau_hoi"], cau_hoi)
        self.assertEqual(ban_ghi["trang_thai"], ket_qua["trang_thai"])
        self.assertEqual(ban_ghi["so_trich_dan"], len(ket_qua["trich_dan"]))
        self.assertEqual(ban_ghi["ma_doan_trich_dan"],
                         ["doan-DEMO-A"] if ket_qua["trich_dan"] else [])
        luc = datetime.fromisoformat(ban_ghi["luc"])
        self.assertEqual(luc.utcoffset(), timedelta(hours=7))
        self.assertLess(abs(datetime.now(timezone.utc) - luc), timedelta(seconds=10))
        noi_dung = json.dumps(ban_ghi, ensure_ascii=False)
        for cam in (CAU_TRICH, TRA_LOI, "Không thấy trong hợp đồng."):
            self.assertNotIn(cam, noi_dung)

    def test_luong_du_giu_nguyen_ket_qua_tra_loi(self):
        with patch.object(hoi_dap_vay, "tra_loi", wraps=hoi_dap_vay.tra_loi) as tra:
            ket_qua = self.hoi_demo()
        self.assertEqual(ket_qua, {
            "trang_thai": "CO_TRA_LOI", "tra_loi": TRA_LOI, "muc": "VANG",
            "trich_dan": [self.chi_muc.tim(CAU_HOI)[0]["trich_dan"]],
        })
        tra.assert_called_once_with(
            CAU_HOI, ket_qua["trich_dan"], cong_ai=self.cong,
        )
        self.cong.goi.assert_called_once()
        self.assertEqual(self.cong.goi.call_args.args[0].loai_viec, "HOI_DAP_VAY")
        self.kiem_nhat_ky(ket_qua)

    def test_khong_co_trich_dan_khong_goi_cong(self):
        cau_hoi = "Bảo hiểm cháy nổ DEMO?"
        ket_qua = self.hoi_demo(cau_hoi)
        self.assertEqual(ket_qua, {
            "trang_thai": "KHONG_THAY", "tra_loi": "Không thấy trong hợp đồng.",
            "trich_dan": [],
        })
        self.cong.goi.assert_not_called()
        self.kiem_nhat_ky(ket_qua, cau_hoi)

    def test_cau_hoi_rong_van_ghi_moi_luot(self):
        with patch.object(self.chi_muc, "tim") as tim:
            for cau_hoi in ("", "  ", "\t\r\n "):
                with self.subTest(cau_hoi=cau_hoi):
                    self.ghi.reset_mock()
                    ket_qua = self.hoi_demo(cau_hoi)
                    self.assertEqual(ket_qua["trang_thai"], "KHONG_THAY")
                    self.assertEqual(ket_qua["trich_dan"], [])
                    self.kiem_nhat_ky(ket_qua, cau_hoi)
            tim.assert_not_called()
        self.cong.goi.assert_not_called()

    def test_chi_trich_dan_khi_ai_khong_co_can_cu(self):
        self.cong.goi.return_value = KetQuaAI("HOI_DAP_VAY", "DO", {}, "LOCAL", "DEMO")
        ket_qua = self.hoi_demo()
        self.assertEqual(ket_qua["trang_thai"], "CHI_TRICH_DAN")
        self.assertIsNone(ket_qua["tra_loi"])
        self.kiem_nhat_ky(ket_qua)

    def test_loc_va_so_ket_qua_truyen_thang_xuong(self):
        loc = {"DEMO-A"}
        with patch.object(self.chi_muc, "tim", wraps=self.chi_muc.tim) as tim:
            ket_qua = self.hoi_demo(loc_tai_lieu=loc, so_ket_qua=1)
        tim.assert_called_once_with(CAU_HOI, loc_tai_lieu=loc, so_ket_qua=1)
        self.assertIs(tim.call_args.kwargs["loc_tai_lieu"], loc)
        self.assertEqual(ket_qua["trang_thai"], "CO_TRA_LOI")
        self.kiem_nhat_ky(ket_qua)

    def test_loc_rong_khong_goi_cong(self):
        ket_qua = self.hoi_demo(loc_tai_lieu=set())
        self.assertEqual(ket_qua["trang_thai"], "KHONG_THAY")
        self.cong.goi.assert_not_called()
        self.kiem_nhat_ky(ket_qua)

    def test_nhieu_tai_lieu_khong_loc_van_chay(self):
        doan_b = [{**self.doan[0], "ma_doan": "doan-DEMO-B"}]
        self.chi_muc.them("DEMO-B", "DEMO-B.docx", doan_b)
        ket_qua = self.hoi_demo()
        self.assertEqual(ket_qua["trang_thai"], "CO_TRA_LOI")
        self.assertEqual({m["ten_tep"] for m in ket_qua["trich_dan"]},
                         {"DEMO-A.docx", "DEMO-B.docx"})
        self.ghi.assert_called_once()
        ban_ghi = self.ghi.call_args.args[0]
        self.assertEqual(ban_ghi["so_trich_dan"], 2)
        self.assertEqual(ban_ghi["ma_doan_trich_dan"], ["doan-DEMO-A", "doan-DEMO-B"])

    def test_tra_dung_doi_tuong_ket_qua(self):
        ket_qua = {"trang_thai": "CHI_TRICH_DAN", "tra_loi": None, "trich_dan": []}
        with patch.object(hoi_dap_vay, "tra_loi", return_value=ket_qua):
            self.assertIs(self.hoi_demo(), ket_qua)
        self.kiem_nhat_ky(ket_qua)

    def test_m9_khong_chuoi_cam_va_hai_tep_utf8_khong_bom(self):
        goc = Path(__file__).resolve().parents[1]
        thu_muc = goc / "src" / "kho_tri_thuc" / "m9"
        for tep in thu_muc.rglob("*.py"):
            for cam in ("api.anthropic.com", "api.openai.com", "mask"):
                self.assertNotIn(cam, tep.read_text(encoding="utf-8").lower(), tep.name)
        for tep in (thu_muc / "dich_vu_hoi_dap.py", Path(__file__)):
            raw = tep.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), tep.name)
            raw.decode("utf-8")


if __name__ == "__main__":
    unittest.main()
