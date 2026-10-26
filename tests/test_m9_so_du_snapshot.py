"""M9-2d: snapshot DEMO trong bộ nhớ, cổng giả; cấm mạng/AI thật."""
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal, localcontext
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from kho_tri_thuc.m9.dich_vu_hoi_dap import hoi
from kho_tri_thuc.m9.snapshot_sheet import CAU_HINH_MAU, lap_snapshot
from kho_tri_thuc.m9.so_du_snapshot import tra_so_du
from kho_tri_thuc.tri_thuc.cong_ai import KetQuaAI, TruongAI


MOC = "26/10/2026 09:30"
DUOI = "(nguồn Sheet, mốc " + MOC + ")"


class SoDuSnapshotTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.socket", "kho_tri_thuc.tri_thuc.cong_ai._goi_json"):
            guard = patch(target, side_effect=AssertionError("Cấm mạng/AI thật"))
            guard.start()
            self.addCleanup(guard.stop)
        self.snapshot = lap_snapshot(
            [list(CAU_HINH_MAU["anh_xa_cot"]),
             ["Công ty DEMO", "NH B", "A", "VND", "123.456.789,12", "8,5%",
              "THA_NOI", "6", "2,5", "01/11/2026", "31/12/2027"],
             ["Công ty DEMO", "NH B", "A-1", "USD", "1.234,56", "7,25%",
              "CO_DINH", "", "", "", "30/06/2028"],
             ["Công ty KHÁC", "NH C", "C", "VND", "0", "0",
              "CO_DINH", "", "", "", "31/12/2028"]],
            cau_hinh=CAU_HINH_MAU, keo_luc=datetime(2026, 10, 26, 9, 30),
            nguon_id="sheet-DEMO",
        )
        self.assertEqual(self.snapshot["dong_loi"], [])
        self.chi_muc = Mock()
        self.cong = Mock()
        self.ghi = Mock()

    def hoi_demo(self, cau_hoi, **kwargs):
        return hoi(cau_hoi, chi_muc=self.chi_muc, cong_ai=self.cong,
                   nguoi_hoi="nguoi-DEMO", ghi_nhat_ky=self.ghi, **kwargs)

    def kiem_moc(self, ket_qua):
        self.assertEqual(ket_qua["nguon"], "Sheet")
        self.assertEqual(ket_qua["moc"], MOC)
        self.assertTrue(ket_qua["tra_loi"].endswith(DUOI))

    def test_du_no_co_dau_va_khong_dau(self):
        for cau in ("dư nợ khoản vay A là bao nhiêu", "du no khoan A",
                    "SỐ DƯ MÃ a?", "số dư A", "DƯ NỢ KHOẢN VAY A."):
            with self.subTest(cau=cau):
                kq = tra_so_du(cau, self.snapshot)
                self.assertEqual(kq["trang_thai"], "TU_SNAPSHOT")
                self.assertEqual(kq["dong"], [{
                    "ma_khoan_vay": "A", "ngan_hang": "NH B", "phap_nhan": "Công ty DEMO",
                    "truong": "du_no", "gia_tri": Decimal("123456789.12"), "don_vi": "VND",
                }])
                self.assertIn("123456789,12 VND", kq["tra_loi"])
                self.kiem_moc(kq)

    def test_lai_suat_ngan_hang(self):
        for cau in ("lãi suất hiện hành NH B", "lai suat hien hanh nh b",
                    "lãi suất hiện hành ngân hàng NH B"):
            with self.subTest(cau=cau):
                kq = tra_so_du(cau, self.snapshot)
                self.assertEqual([d["gia_tri"] for d in kq["dong"]],
                                 [Decimal("8.5"), Decimal("7.25")])
                self.assertEqual({d["don_vi"] for d in kq["dong"]}, {"%/năm"})
                self.assertIn("8,5 %/năm", kq["tra_loi"])
                self.assertIn("7,25 %/năm", kq["tra_loi"])
                self.kiem_moc(kq)

    def test_lai_suat_khop_dinh_danh_khong_can_tu_hien_tai(self):
        for cau, ma in (("lãi suất khoản A", ["A"]),
                        ("lãi suất khoản vay A", ["A"]),
                        ("lãi suất khoản A-1", ["A-1"]),
                        ("lãi suất khoản vay A-1", ["A-1"]),
                        ("lãi suất A", ["A"]),
                        ("lãi suất NH B", ["A", "A-1"]),
                        ("lai suat phap nhan Cong ty KHAC", ["C"])):
            with self.subTest(cau=cau):
                kq = tra_so_du(cau, self.snapshot)
                self.assertEqual(kq["trang_thai"], "TU_SNAPSHOT")
                self.assertEqual([d["ma_khoan_vay"] for d in kq["dong"]], ma)
                self.assertTrue(all(d["truong"] == "lai_suat_nam" for d in kq["dong"]))
                self.kiem_moc(kq)
        self.assertEqual(tra_so_du("lãi suất khoản A", self.snapshot)["dong"][0]["gia_tri"],
                         Decimal("8.5"))

    def test_lai_suat_tu_hien_tai_o_moi_vi_tri(self):
        for tu in ("hiện nay", "hiện tại", "hiện hành", "bây giờ", "đang"):
            for mau in ("{} lãi suất NH B", "lãi suất {} của NH B",
                        "lãi suất NH B {}", "lãi suất khoản {} A"):
                cau = mau.format(tu)
                with self.subTest(cau=cau):
                    kq = tra_so_du(cau, self.snapshot)
                    self.assertEqual(kq["trang_thai"], "TU_SNAPSHOT")
                    ma = ["A"] if "khoản" in cau else ["A", "A-1"]
                    self.assertEqual([d["ma_khoan_vay"] for d in kq["dong"]], ma)
                    self.kiem_moc(kq)

    def test_so_lieu_khop_dinh_danh_khong_can_tu_hien_tai(self):
        for tu, truong in (("dư nợ", "du_no"), ("lãi suất", "lai_suat_nam"),
                          ("kỳ điều chỉnh", "ky_dieu_chinh_ke_tiep"),
                          ("đáo hạn", "ngay_dao_han")):
            with self.subTest(tu=tu):
                kq = tra_so_du(tu + " khoản A", self.snapshot)
                self.assertEqual(kq["trang_thai"], "TU_SNAPSHOT")
                self.assertEqual([(d["ma_khoan_vay"], d["truong"]) for d in kq["dong"]],
                                 [("A", truong)])
                self.kiem_moc(kq)

    def test_lai_suat_thieu_dinh_danh_va_ma_la(self):
        for cau in ("lãi suất", "lãi suất khoản A-10"):
            with self.subTest(cau=cau):
                self.assertIsNone(tra_so_du(cau, self.snapshot))
        kq = tra_so_du("lãi suất khoản A-10 hiện nay", self.snapshot)
        self.assertEqual(kq["trang_thai"], "KHONG_THAY_TRONG_SNAPSHOT")
        self.assertEqual(kq["dong"], [])
        self.kiem_moc(kq)

    def test_ngay_va_ky_dieu_chinh(self):
        for tu in ("kỳ điều chỉnh", "ky dieu chinh", "ngày đáo hạn", "ngay dao han"):
            with self.subTest(tu=tu):
                kq = tra_so_du(tu + " khoản vay A", self.snapshot)
                ngay = date(2026, 11, 1) if "chỉnh" in tu or "chinh" in tu else date(2027, 12, 31)
                self.assertEqual(kq["dong"][0]["gia_tri"], ngay)
                self.assertIn(ngay.strftime("%d/%m/%Y"), kq["tra_loi"])
                self.kiem_moc(kq)

    def test_nhieu_truong_cung_luot(self):
        kq = tra_so_du("Dư nợ và lãi suất hiện hành khoản vay A", self.snapshot)
        self.assertEqual([d["truong"] for d in kq["dong"]], ["du_no", "lai_suat_nam"])
        self.kiem_moc(kq)

    def test_nhieu_ma_khoan_vay_cung_luot(self):
        kq = tra_so_du("du no khoan vay A va A-1", self.snapshot)
        self.assertEqual([d["ma_khoan_vay"] for d in kq["dong"]], ["A", "A-1"])

    def test_ma_truc_tiep_khong_khop_tien_to(self):
        for cau in ("dư nợ A-10", "du no A/1", "du no A.1", "du no KHONG-CO",
                    "du no A10", "du no A-10 tai NH B"):
            with self.subTest(cau=cau):
                kq = tra_so_du(cau, self.snapshot)
                self.assertEqual(kq["trang_thai"], "KHONG_THAY_TRONG_SNAPSHOT")
                self.assertEqual(kq["dong"], [])
                self.kiem_moc(kq)
        for cau, ma in (("dư nợ A", "A"), ("dư nợ a-1", "A-1")):
            with self.subTest(cau=cau):
                kq = tra_so_du(cau, self.snapshot)
                self.assertEqual([d["ma_khoan_vay"] for d in kq["dong"]], [ma])
                self.kiem_moc(kq)

    def test_ten_co_so_khong_bi_hieu_la_ma_khoan_vay(self):
        for truong, ten in (("ngan_hang", "NH DEMO-10"),
                            ("phap_nhan", "Cong ty DEMO10")):
            with self.subTest(truong=truong):
                snapshot = deepcopy(self.snapshot)
                snapshot["khoan_vay"][0][truong] = ten
                kq = tra_so_du("du no " + ten, snapshot)
                self.assertEqual([d["ma_khoan_vay"] for d in kq["dong"]], ["A"])
                self.kiem_moc(kq)

    def test_ma_co_tien_to_trung_nhan_khong_bi_tach(self):
        for ma in ("MA-A", "NH-A", "MA/A", "NH.A", "CUA-A", "VA-A"):
            with self.subTest(ma=ma):
                snapshot = deepcopy(self.snapshot)
                snapshot["khoan_vay"][0]["ma_khoan_vay"] = ma
                kq = tra_so_du("du no khoan vay " + ma, snapshot)
                self.assertEqual([d["ma_khoan_vay"] for d in kq["dong"]], [ma])

    def test_loc_phap_nhan_va_ket_hop_cac_dieu_kien(self):
        for cau, ma in (("du no phap nhan cong ty khac", ["C"]),
                        ("du no Cong ty KHÁC", ["C"]),
                        ("du no khoan A tai ngan hang NH B cua phap nhan Công ty DEMO", ["A"])):
            with self.subTest(cau=cau):
                kq = tra_so_du(cau, self.snapshot)
                self.assertEqual([d["ma_khoan_vay"] for d in kq["dong"]], ma)

    def test_khong_khop_mo_va_khong_bo_qua_loc_la(self):
        for cau in ("du no khoan KHONG-CO", "du no khoan CUA-A", "du no khoan VA-A",
                    "du no khoan A-10", "du no khoan A/1",
                    "du no khoan A.1", "du no ngan hang NH BB", "du no NH B Plus",
                    "du no phap nhan Cong ty DEM", "du no khoan A tai NH C",
                    "du no khoan KHONG-CO tai NH B"):
            with self.subTest(cau=cau):
                kq = tra_so_du(cau, self.snapshot)
                self.assertEqual(kq["trang_thai"], "KHONG_THAY_TRONG_SNAPSHOT")
                self.assertEqual(kq["dong"], [])
                self.kiem_moc(kq)

    def test_nhieu_khoan_khac_tien_te_chi_liet_ke(self):
        kq = tra_so_du("số dư NH B", self.snapshot)
        self.assertEqual([d["ma_khoan_vay"] for d in kq["dong"]], ["A", "A-1"])
        self.assertIn("123456789,12 VND", kq["tra_loi"])
        self.assertIn("1234,56 USD", kq["tra_loi"])
        self.assertNotIn("Tổng", kq["tra_loi"])
        self.kiem_moc(kq)

    def test_khong_loc_tra_tat_ca_va_giu_so_khong(self):
        kq = tra_so_du("dư nợ các khoản vay là bao nhiêu", self.snapshot)
        self.assertEqual(len(kq["dong"]), 3)
        self.assertEqual(kq["dong"][-1]["gia_tri"], Decimal("0"))
        self.assertIn("0 VND", kq["tra_loi"])

    def test_tong_du_no_khong_cong_khac_dong_tien(self):
        kq = tra_so_du("tổng dư nợ", self.snapshot)
        self.assertEqual([d["ma_khoan_vay"] for d in kq["dong"]], ["A", "A-1", "C"])
        self.assertEqual([d["don_vi"] for d in kq["dong"]], ["VND", "USD", "VND"])
        for so in ("123456789,12 VND", "1234,56 USD", "0 VND"):
            self.assertIn(so, kq["tra_loi"])
        self.assertNotIn("Tổng", kq["tra_loi"])
        self.kiem_moc(kq)

    def test_cau_dieu_khoan_khong_tra_snapshot(self):
        for cau in ("phí trả nợ trước hạn", "phi tra no truoc han", "lãi suất theo hợp đồng", ""):
            with self.subTest(cau=cau):
                self.assertIsNone(tra_so_du(cau, self.snapshot))

    def test_so_lieu_theo_hop_dong_khong_tra_snapshot(self):
        for cau in ("Theo hợp đồng, kỳ điều chỉnh khoản vay A là bao nhiêu?",
                    "Hợp đồng quy định dư nợ khoản A là bao nhiêu?",
                    "Điều khoản về ngày đáo hạn khoản A",
                    "Quy định kỳ điều chỉnh khoản A",
                    "Dư nợ khoản A theo Điều 3", "Du no A theo khoan 2",
                    "THEO HOP DONG LAI SUAT HIEN HANH NH B",
                    "lãi suất theo khoản 3 của hợp đồng",
                    "lãi suất khoản A theo Khoản 2.1",
                    "lãi suất NH B hiện nay theo hợp đồng",
                    "lãi suất khoản A theo Điều 3",
                    "hợp đồng quy định lãi suất khoản A",
                    "điều khoản lãi suất khoản A", "quy định lãi suất khoản A"):
            with self.subTest(cau=cau):
                self.assertIsNone(tra_so_du(cau, self.snapshot))

    def test_ky_dieu_chinh_tiep_theo_van_tra_snapshot(self):
        kq = tra_so_du("kỳ điều chỉnh tiếp theo của khoản A", self.snapshot)
        self.assertEqual(kq["trang_thai"], "TU_SNAPSHOT")
        self.assertEqual([d["ma_khoan_vay"] for d in kq["dong"]], ["A"])
        self.assertEqual(kq["dong"][0]["gia_tri"], date(2026, 11, 1))
        self.kiem_moc(kq)

    def test_snapshot_rong_co_moc(self):
        kq = tra_so_du("du no khoan A", {**self.snapshot, "khoan_vay": []})
        self.assertEqual(kq["trang_thai"], "KHONG_THAY_TRONG_SNAPSHOT")
        self.kiem_moc(kq)

    def test_tu_choi_nguon_va_moc_khong_hop_le(self):
        for sua in ({"nguon": "Hợp đồng"}, {"moc": None}, {"moc": "1/1/2026 9:30"},
                    {"moc": "31/02/2026 09:30"}, {"khoan_vay": None}):
            with self.subTest(sua=sua), self.assertRaises(ValueError):
                tra_so_du("du no", {**self.snapshot, **sua})

    def test_thieu_du_lieu_khong_suy_ra_so_khong(self):
        for truong, cau in (("du_no", "du no"), ("lai_suat_nam", "lai suat hien hanh"),
                           ("ngay_dao_han", "ngay dao han")):
            with self.subTest(truong=truong):
                snapshot = deepcopy(self.snapshot)
                snapshot["khoan_vay"][0][truong] = None
                kq = tra_so_du(cau + " khoan A", snapshot)
                self.assertIsNone(kq["dong"][0]["gia_tri"])
                self.assertIn("Chưa có dữ liệu", kq["tra_loi"])
                self.kiem_moc(kq)

    def test_tien_thieu_don_vi_khong_hien_so(self):
        snapshot = deepcopy(self.snapshot)
        snapshot["khoan_vay"][0]["tien_te"] = None
        kq = tra_so_du("du no khoan A", snapshot)
        self.assertIsNone(kq["dong"][0]["gia_tri"])
        self.assertNotIn("123456789", kq["tra_loi"])

    def test_khong_float_khong_lam_tron_khong_sua_dau_vao(self):
        snapshot = deepcopy(self.snapshot)
        snapshot["khoan_vay"][0]["du_no"] = Decimal("12345678901234567890.123456789")
        truoc = deepcopy(snapshot)
        with localcontext() as ctx:
            ctx.prec = 3
            kq = tra_so_du("du no khoan A", snapshot)
        self.assertEqual(kq["dong"][0]["gia_tri"], truoc["khoan_vay"][0]["du_no"])
        self.assertIn("12345678901234567890,123456789 VND", kq["tra_loi"])
        self.assertEqual(snapshot, truoc)
        self.assertFalse(any(isinstance(v, float) for d in kq["dong"] for v in d.values()))

    def test_khong_chuyen_float_va_so_khong_huu_han(self):
        for so in (8.5, Decimal("NaN"), Decimal("Infinity")):
            with self.subTest(so=so):
                snapshot = deepcopy(self.snapshot)
                snapshot["khoan_vay"][0]["lai_suat_nam"] = so
                kq = tra_so_du("lai suat hien hanh khoan A", snapshot)
                self.assertIsNone(kq["dong"][0]["gia_tri"])

    def test_hoi_snapshot_khong_tim_hop_dong_khong_goi_ai_van_ghi_log(self):
        for cau, trang_thai in (("du no khoan A", "TU_SNAPSHOT"),
                               ("du no khoan KHONG-CO", "KHONG_THAY_TRONG_SNAPSHOT")):
            with self.subTest(cau=cau):
                self.ghi.reset_mock()
                kq = self.hoi_demo(cau, snapshot=self.snapshot)
                self.assertEqual(kq["trang_thai"], trang_thai)
                self.cong.goi.assert_not_called()
                self.chi_muc.tim.assert_not_called()
                self.ghi.assert_called_once()
                log = self.ghi.call_args.args[0]
                self.assertEqual(log["trang_thai"], trang_thai)
                self.assertEqual(log["nguoi_hoi"], "nguoi-DEMO")
                self.assertEqual(log["cau_hoi"], cau)
                self.assertEqual(log["so_trich_dan"], 0)
                self.assertEqual(log["ma_doan_trich_dan"], [])
                self.assertEqual(datetime.fromisoformat(log["luc"]).utcoffset(), timedelta(hours=7))
                self.assertNotIn("tra_loi", log)
                self.assertNotIn("dong", log)
                self.kiem_moc(kq)

    def test_hoi_dieu_khoan_van_di_luong_hop_dong(self):
        cau = "phí trả nợ trước hạn"
        trich = {"cau": "Phí trả nợ trước hạn DEMO là 1%.", "ten_tep": "DEMO.docx",
                 "trang": 1, "dieu": "2", "khoan": None}
        self.chi_muc.tim.return_value = [{"ma_doan": "DEMO-1", "trich_dan": trich}]
        self.cong.goi.return_value = KetQuaAI(
            "HOI_DAP_VAY", "VANG",
            {"tra_loi": TruongAI("tra_loi", "1%", trich["cau"], "LOCAL")}, "LOCAL", "DEMO",
        )
        kq = self.hoi_demo(cau, snapshot=self.snapshot)
        self.assertEqual(kq["trang_thai"], "CO_TRA_LOI")
        self.assertEqual(kq["tra_loi"], "1%")
        self.cong.goi.assert_called_once()
        self.chi_muc.tim.assert_called_once_with(cau, loc_tai_lieu=None, so_ket_qua=5)
        self.ghi.assert_called_once()

    def test_hoi_khong_snapshot_giu_luong_cu(self):
        self.chi_muc.tim.return_value = []
        kq = self.hoi_demo("du no khoan A")
        self.assertEqual(kq["trang_thai"], "KHONG_THAY")
        self.chi_muc.tim.assert_called_once()
        self.cong.goi.assert_not_called()
        self.ghi.assert_called_once()

    def test_ba_tep_utf8_khong_bom(self):
        goc = Path(__file__).resolve().parents[1]
        for tep in (goc / "src/kho_tri_thuc/m9/so_du_snapshot.py",
                    goc / "src/kho_tri_thuc/m9/dich_vu_hoi_dap.py", Path(__file__)):
            raw = tep.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            raw.decode("utf-8")


if __name__ == "__main__":
    unittest.main()
