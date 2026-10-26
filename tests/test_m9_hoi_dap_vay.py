"""M9-2b: hợp đồng DEMO, cổng/Local giả; cấm mạng, không mở server."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from kho_tri_thuc.m9.hoi_dap_vay import tra_loi
from kho_tri_thuc.tri_thuc import cong_ai as ca


CAU_LAI = "Lãi suất theo hợp đồng DEMO là 8,5%/năm."
CAU_VAY = "Hạn mức vay DEMO là 1.000.000.000 VND, kỳ hạn 12 tháng."


def nguon(cau, *, trang=2):
    return {"ten_tep": "hop-dong-DEMO.pdf", "trang": trang, "dieu": "5",
            "khoan": "2", "diem": None, "cau": cau}


def ket_qua(gia_tri, cau, *, duong="LOCAL"):
    return ca.KetQuaAI(
        "HOI_DAP_VAY", "VANG", {"tra_loi": ca.TruongAI("tra_loi", gia_tri, cau, duong)},
        duong, "Đề xuất DEMO",
    )


class HoiDapVayTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.socket", "kho_tri_thuc.tri_thuc.cong_ai._goi_json"):
            guard = patch(target, side_effect=AssertionError("Cấm mạng/server thật"))
            guard.start()
            self.addCleanup(guard.stop)

    def goi(self, gia_tri, cau, *, cac_cau=None):
        cong = Mock(spec=ca.CongAI)
        cong.goi.return_value = ket_qua(gia_tri, cau)
        return tra_loi("Điều khoản vay DEMO?", cac_cau or [nguon(CAU_LAI)], cong_ai=cong)

    def cong_local(self, noi_dung):
        local = Mock(return_value=noi_dung)
        bao_ve, cloud, chon_kiem = Mock(), Mock(), Mock(return_value=True)
        bo_ghi = ca.BoGhiBoNho()
        cong = ca.CongAI({
            "local_ai": {"enabled": True, "url": "http://127.0.0.1:1234/v1/chat/completions",
                         "model": "DEMO-local"},
            "cong_ai": {"cloud_bat": True, "kiem_xac_suat": {"ty_le_ban_dau": 1}},
        }, bo_ghi=bo_ghi, local_transport=local, mask=bao_ve, nha_cung_cap=cloud,
            moi_truong={"ANTHROPIC_API_KEY": "DEMO-KEY"}, kiem_xac_suat=chon_kiem)
        cache = patch.dict(ca.ai_cuc_bo._CONNECTION_FAILURES, {}, clear=True)
        cache.start()
        self.addCleanup(cache.stop)
        return cong, local, bao_ve, cloud, chon_kiem

    def test_loai_viec_chi_local(self):
        self.assertIs(ca.LOAI_VIEC["HOI_DAP_VAY"].duoc_dung_cloud, False)
        self.assertEqual(ca.LOAI_VIEC["HOI_DAP_VAY"].nguong_tin_cay, 0.80)

    def test_khong_trich_dan_khong_goi_cong(self):
        cong = Mock(spec=ca.CongAI)
        self.assertEqual(tra_loi("Dư nợ bao nhiêu?", [], cong_ai=cong), {
            "trang_thai": "KHONG_THAY", "tra_loi": "Không thấy trong hợp đồng.", "trich_dan": [],
        })
        cong.goi.assert_not_called()

    def test_cau_rong_khong_goi_cong(self):
        cong = Mock(spec=ca.CongAI)
        self.assertEqual(tra_loi("DEMO?", [nguon("  ")], cong_ai=cong)["trang_thai"], "KHONG_THAY")
        cong.goi.assert_not_called()

    def test_yeu_cau_giu_nguyen_cau_va_dung_loai_viec(self):
        cac_cau = [nguon("Câu DEMO  có  hai khoảng trắng."), nguon(CAU_LAI, trang=3)]
        ban_dau = [dict(item) for item in cac_cau]
        cong = Mock(spec=ca.CongAI)
        cong.goi.return_value = ket_qua("8,5%/năm", CAU_LAI)
        result = tra_loi("Lãi suất theo hợp đồng?", cac_cau, cong_ai=cong)
        yc = cong.goi.call_args.args[0]
        self.assertIsInstance(yc, ca.YeuCauAI)
        self.assertEqual(yc.loai_viec, "HOI_DAP_VAY")
        self.assertEqual(yc.truong, ("tra_loi",))
        self.assertEqual(yc.van_ban, f"[1] {cac_cau[0]['cau']}\n[2] {CAU_LAI}")
        self.assertIn("Lãi suất theo hợp đồng?", yc.chi_dan)
        self.assertEqual(result, {"trang_thai": "CO_TRA_LOI", "tra_loi": "8,5%/năm",
                                  "trich_dan": [cac_cau[1], cac_cau[0]], "muc": "VANG"})
        self.assertEqual(cac_cau, ban_dau)

    def test_so_bia_khong_co_trong_cau_duoc_dan(self):
        for gia_tri in ("Lãi suất 9%", "Kỳ hạn 12 tháng", "Ngày 26/10/2026"):
            with self.subTest(gia_tri=gia_tri):
                self.assertEqual(self.goi(gia_tri, CAU_LAI), {
                    "trang_thai": "CHI_TRICH_DAN", "tra_loi": None, "trich_dan": [nguon(CAU_LAI)],
                })

    def test_khong_muon_so_tu_cau_khac(self):
        result = self.goi("12 tháng", CAU_LAI, cac_cau=[nguon(CAU_LAI), nguon(CAU_VAY)])
        self.assertEqual(result["trang_thai"], "CHI_TRICH_DAN")

    def test_so_phai_nguyen_van_khong_phai_chuoi_con(self):
        for gia_tri, cau in (("9%", "Lãi suất DEMO 19%."), ("5%", CAU_LAI),
                             ("12 tháng", "Kỳ hạn DEMO 120 tháng."),
                             ("1.000 VND", "Số tiền DEMO 11.000 VND."),
                             ("8.5%", CAU_LAI), ("9%", "Lãi suất DEMO -9%."),
                             ("26/11/2026", "Đáo hạn ngày 26/10/2026.")):
            with self.subTest(gia_tri=gia_tri, cau=cau):
                self.assertEqual(self.goi(gia_tri, cau, cac_cau=[nguon(cau)])["trang_thai"], "CHI_TRICH_DAN")

    def test_cau_trich_sai_hoac_chi_la_mot_phan_bi_chan(self):
        for cau in (CAU_LAI.replace("8,5", "9"), "8,5%/năm", CAU_LAI + " ",
                    CAU_LAI.replace("là ", "là  "), f"[1] {CAU_LAI}"):
            with self.subTest(cau=cau):
                self.assertEqual(self.goi("8,5%/năm", cau)["trang_thai"], "CHI_TRICH_DAN")

    def test_tien_thieu_don_vi_chi_trich_dan(self):
        for cau in ("Số tiền vay DEMO là 1.000.000.", "Số tiền vay DEMO là 100 triệu."):
            with self.subTest(cau=cau):
                self.assertEqual(self.goi(cau, cau, cac_cau=[nguon(cau)])["trang_thai"], "CHI_TRICH_DAN")

    def test_tien_co_don_vi_trong_tra_loi_hoac_cau_trich(self):
        for don_vi in ("VND", "USD", "đồng"):
            for gia_tri in ("1.000.000", f"1.000.000 {don_vi}"):
                with self.subTest(don_vi=don_vi, gia_tri=gia_tri):
                    cau = f"Số tiền vay DEMO là 1.000.000 {don_vi}."
                    self.assertEqual(self.goi(gia_tri, cau, cac_cau=[nguon(cau)])["trang_thai"], "CO_TRA_LOI")

    def test_ty_le_ngay_ky_han_khong_phai_tien(self):
        for cau in (CAU_LAI, "Đáo hạn ngày 26/10/2026.", "Kỳ hạn vay DEMO 12 tháng.",
                    "Bên vay thông báo trước 30 ngày.", "Điều 5 quy định nghĩa vụ thông báo."):
            with self.subTest(cau=cau):
                self.assertEqual(self.goi(cau, cau, cac_cau=[nguon(cau)])["trang_thai"], "CO_TRA_LOI")

    def test_khong_so_van_can_cau_trich(self):
        cau = "Bên vay phải thông báo bằng văn bản."
        self.assertEqual(self.goi(cau, cau, cac_cau=[nguon(cau)])["trang_thai"], "CO_TRA_LOI")
        self.assertEqual(self.goi(cau, "Không có câu này.")["trang_thai"], "CHI_TRICH_DAN")

    def test_khong_nhan_ket_qua_cloud_hoac_thieu_truong(self):
        for kq in (ket_qua("8,5%/năm", CAU_LAI, duong="CLOUD"),
                   ca.KetQuaAI("HOI_DAP_VAY", "DO", {}, "KHONG", "DEMO chưa có kết quả"),
                   ket_qua("", CAU_LAI)):
            with self.subTest(kq=kq):
                cong = Mock(spec=ca.CongAI)
                cong.goi.return_value = kq
                self.assertEqual(tra_loi("DEMO?", [nguon(CAU_LAI)], cong_ai=cong)["trang_thai"], "CHI_TRICH_DAN")

    def test_cloud_bat_local_khong_chac_hoac_khong_chay_van_chi_local(self):
        for noi_dung in ("không chắc", json.dumps({"truong": [{"ten": "tra_loi", "gia_tri": "8,5%/năm",
                            "trich_dan": CAU_LAI}], "do_tin_cay": 0.4}, ensure_ascii=False)):
            with self.subTest(noi_dung=noi_dung):
                cong, local, bao_ve, cloud, chon_kiem = self.cong_local(noi_dung)
                result = tra_loi("Lãi suất theo hợp đồng?", [nguon(CAU_LAI)], cong_ai=cong)
                self.assertIn(result["trang_thai"], ("CHI_TRICH_DAN", "CO_TRA_LOI"))
                local.assert_called_once()
                self.assertEqual(bao_ve.mock_calls, [])
                self.assertEqual(cloud.mock_calls, [])
                chon_kiem.assert_not_called()
                self.assertFalse(any(b.da_gui and b.duong == "CLOUD" for b in cong.bo_ghi.ban_ghi))
                self.assertIn("LOAI_VIEC_KHONG_DUNG_CLOUD", cong.bo_ghi.ban_ghi[-1].ly_do_khong_gui)

    def test_cong_that_local_gia_dat_va_nhat_ky_khong_noi_dung(self):
        noi_dung = json.dumps({"truong": [{"ten": "tra_loi", "gia_tri": "8,5%/năm", "trich_dan": CAU_LAI}],
                               "do_tin_cay": 0.99}, ensure_ascii=False)
        cong, local, bao_ve, cloud, chon_kiem = self.cong_local(noi_dung)
        cau_hoi = "Lãi suất trong hợp đồng DEMO là bao nhiêu?"
        result = tra_loi(cau_hoi, [nguon(CAU_LAI)], cong_ai=cong)
        self.assertEqual(result["trang_thai"], "CO_TRA_LOI")
        self.assertEqual(result["muc"], "VANG")
        local.assert_called_once()
        self.assertEqual(bao_ve.mock_calls, [])
        self.assertEqual(cloud.mock_calls, [])
        chon_kiem.assert_not_called()
        logs = json.dumps([b.thanh_dict() for b in cong.bo_ghi.ban_ghi], ensure_ascii=False)
        for bi_mat in (cau_hoi, CAU_LAI, result["tra_loi"]):
            self.assertNotIn(bi_mat, logs)

    def test_m9_khong_chua_chuoi_cam(self):
        thu_muc = Path(__file__).resolve().parents[1] / "src" / "kho_tri_thuc" / "m9"
        for tep in thu_muc.rglob("*.py"):
            with self.subTest(tep=tep.name):
                noi_dung = tep.read_text(encoding="utf-8").lower()
                for chuoi in ("api.anthropic.com", "api.openai.com", "mask"):
                    self.assertNotIn(chuoi, noi_dung)


if __name__ == "__main__":
    unittest.main()
