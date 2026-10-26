"""AI-4a: DEMO, Local/Mask/Cloud và kết nối PG giả; không server, mạng hay tệp khóa."""
from __future__ import annotations

import json
import unittest
from dataclasses import replace
from unittest.mock import MagicMock, Mock, patch

from kho_tri_thuc.tri_thuc import cong_ai as ca


LOAI = "BOC_TACH_HOP_DONG"
LOAI_KHAC = "BOC_TACH_NGHIEM_THU"
TEN = "Công ty DEMO Kiểm xác suất"
GOC = f"Bên B: {TEN}. Giá trị: 123 đồng. Giá trị khác: 456 đồng."
LOCAL_CFG = {"enabled": True, "url": "http://127.0.0.1:1234/v1/chat/completions", "model": "demo-local"}


def tra_loi(gia_tri="123 đồng", *, ten=TEN, tin_cay=0.99):
    return json.dumps({"truong": [
        {"ten": "ben_b", "gia_tri": ten, "trich_dan": f"Bên B: {ten}."},
        {"ten": "gia_tri", "gia_tri": gia_tri,
         "trich_dan": "Giá trị: 123 đồng." if gia_tri == "123 đồng" else "Giá trị khác: 456 đồng."},
    ], "do_tin_cay": tin_cay}, ensure_ascii=False)


def yeu_cau(loai=LOAI, truong=("ben_b", "gia_tri")):
    return ca.YeuCauAI(loai, GOC, "Đọc bên B và giá trị DEMO.", truong, ((TEN, "CONG_TY"),))


class MaskGia:
    def __init__(self):
        self.che = Mock(side_effect=lambda text, dd: ca.LuotChe("luot-DEMO", text.replace(TEN, "[CONG_TY_001]")))
        self.mo_che = Mock(side_effect=lambda ma, text, **kw: text.replace("[CONG_TY_001]", TEN))
        self.ket_thuc = Mock()
        self.co_khoa = Mock(return_value=True)


class KiemXacSuatTests(unittest.TestCase):
    def setUp(self):
        # Lỗi tức thì nếu bất cứ đường test nào bỏ qua giả lập.
        self.net = patch("socket.socket", side_effect=AssertionError("Cấm mở mạng/server"))
        self.net.start()
        self.addCleanup(self.net.stop)
        self.http = patch.object(ca, "_goi_json", side_effect=AssertionError("Cấm HTTP thật"))
        self.http.start()
        self.addCleanup(self.http.stop)
        self.local_text = tra_loi()
        self.local = patch.object(ca.ai_cuc_bo, "ask_local", side_effect=lambda *args: self.local_text).start()
        self.addCleanup(patch.stopall)
        self.mask = MaskGia()
        self.cloud_text = tra_loi(ten="[CONG_TY_001]")
        self.cloud = Mock()
        self.cloud.tra_loi.side_effect = lambda *args, **kw: ca.PhanHoiCloud(self.cloud_text, "demo-cloud", 10, 5)

    def cong(self, *, cloud_bat=True, cfg=None, bo=None, moc=None):
        return ca.CongAI({"local_ai": LOCAL_CFG, "cong_ai": {
            "cloud_bat": cloud_bat, "kiem_xac_suat": cfg or {},
        }}, bo_ghi=bo if bo is not None else ca.BoGhiBoNho(), mask=self.mask,
            nha_cung_cap=self.cloud, moi_truong={"ANTHROPIC_API_KEY": "DEMO-KEY"}, kiem_xac_suat=moc)

    def tk(self, gate, loai=LOAI):
        return next(r for r in gate.thong_ke() if r["loai_viec"] == loai)

    def test_cloud_tat_100_phan_tram_khong_lay_mau_hay_goi_mask(self):
        moc = Mock(return_value=True)
        gate = self.cong(cloud_bat=False, cfg={"ty_le_ban_dau": 1}, moc=moc)
        with patch.object(gate.bo_ghi, "thong_ke", side_effect=AssertionError("Không cần đọc thống kê")):
            for _ in range(3):
                kq = gate.goi(yeu_cau())
                self.assertEqual(kq.duong, "LOCAL")
        moc.assert_not_called()
        self.mask.co_khoa.assert_not_called()
        self.mask.che.assert_not_called()
        self.cloud.tra_loi.assert_not_called()
        self.assertEqual(self.tk(gate)["so_kiem"], 0)
        self.assertEqual(self.tk(gate)["ty_le_kiem_hien_hanh"], 0)

    def test_chua_cau_hinh_giu_0_phan_tram_cloud_mac_dinh_tat(self):
        self.assertFalse(ca.cong_ai_settings({})["cloud_bat"])
        gate = self.cong()
        gate.goi(yeu_cau())
        self.cloud.tra_loi.assert_not_called()
        self.assertEqual(self.tk(gate)["ty_le_kiem_hien_hanh"], 0)

    def test_100_phan_tram_luon_chay_hai_duong_va_ghi_dung_sai_theo_truong(self):
        gate = self.cong(cfg={"ty_le_ban_dau": 1})
        gate.goi(yeu_cau())
        self.cloud_text = tra_loi("456 đồng", ten="[CONG_TY_001]")
        kq = gate.goi(yeu_cau())
        self.assertEqual(self.local.call_count, 2)
        self.assertEqual(self.mask.che.call_count, 2)
        self.assertEqual(self.mask.mo_che.call_count, 2)
        self.assertEqual(self.cloud.tra_loi.call_count, 2)
        rows = gate.bo_ghi.ban_ghi
        self.assertEqual([b.duong for b in rows], ["LOCAL", "CLOUD", "LOCAL", "CLOUD"])
        self.assertEqual(rows[0].ma_yeu_cau, rows[1].ma_yeu_cau)
        self.assertEqual(rows[1].ly_do, (ca.LOCAL_DUNG, "SO_TRUONG_DUNG_2", "SO_TRUONG_SAI_0"))
        self.assertEqual(rows[3].ly_do, (ca.LOCAL_SAI, "SO_TRUONG_DUNG_1", "SO_TRUONG_SAI_1"))
        self.assertEqual(kq.truong["gia_tri"].gia_tri_local, "123 đồng")
        self.assertEqual(kq.muc, "VANG")
        tk = self.tk(gate)
        self.assertEqual((tk["so_luot"], tk["so_kiem"], tk["phan_tram_chinh_xac"]), (2, 2, 50))

    def test_cloud_nhan_ban_da_che_va_python_kiem_sau_mo_che(self):
        gate = self.cong(cfg={"ty_le_ban_dau": 1})
        gate.goi(yeu_cau())
        _, user = self.cloud.tra_loi.call_args.args
        self.assertNotIn(TEN, user)
        self.assertIn("[CONG_TY_001]", user)
        self.assertIn("123 đồng", user)  # không che số tiền
        self.assertIn(ca.LOCAL_DUNG, gate.bo_ghi.ban_ghi[-1].ly_do)

    def test_kiem_xac_suat_van_chan_dinh_danh_con_sot(self):
        self.mask.che.side_effect = lambda text, dd: ca.LuotChe("luot-DEMO", text)
        gate = self.cong(cfg={"ty_le_ban_dau": 1})
        result = gate.goi(yeu_cau())
        self.assertEqual(result.duong, "LOCAL")
        self.assertIn("CON_SOT_DINH_DANH", result.ly_do)
        self.cloud.tra_loi.assert_not_called()
        self.assertEqual(self.tk(gate)["so_kiem"], 0)

    def test_so_truong_chuan_khoang_trang_va_hoa_thuong_khong_so_trich_dan(self):
        data = json.loads(self.cloud_text)
        data["truong"].reverse()  # thứ tự JSON không quyết định phép so
        data["truong"][0]["gia_tri"] = "123   ĐỒNG"
        data["truong"][0]["trich_dan"] = "Giá trị: 123 đồng. Giá trị khác: 456 đồng."
        self.cloud_text = json.dumps(data, ensure_ascii=False)
        gate = self.cong(cfg={"ty_le_ban_dau": 1})
        gate.goi(yeu_cau())
        self.assertIn(ca.LOCAL_DUNG, gate.bo_ghi.ban_ghi[-1].ly_do)

    def test_khong_ghi_van_ban_ten_truong_khoa_hay_bi_danh(self):
        gate = self.cong(cfg={"ty_le_ban_dau": 1})
        gate.goi(yeu_cau())
        text = json.dumps([b.thanh_dict() for b in gate.bo_ghi.ban_ghi], ensure_ascii=False)
        for bi_mat in (GOC, TEN, "123 đồng", "ben_b", "[CONG_TY_001]", "DEMO-KEY", self.cloud_text):
            self.assertNotIn(bi_mat, text)

    def test_ti_le_rieng_tung_loai_va_ranh_ngau_nhien(self):
        gate = self.cong(cfg={"ty_le_theo_loai": {LOAI: 0.20, LOAI_KHAC: 1.0}})
        with patch.object(ca.random, "random", side_effect=[0.20, 0.1999, 0.9999]):
            gate.goi(yeu_cau())  # bằng tỷ lệ → không chọn
            gate.goi(yeu_cau())
            gate.goi(yeu_cau(LOAI_KHAC))
        self.assertEqual(self.cloud.tra_loi.call_count, 2)
        self.assertEqual(self.tk(gate)["so_kiem"], 1)
        self.assertEqual(self.tk(gate, LOAI_KHAC)["so_kiem"], 1)

    def test_loai_chi_local_khong_goi_moc_kiem_ke_ca_100_phan_tram(self):
        moc = Mock(return_value=True)
        gate = self.cong(cfg={"ty_le_ban_dau": 1}, moc=moc)
        gate.goi(yeu_cau("CHON_UNG_VIEN"))
        moc.assert_not_called()
        self.mask.che.assert_not_called()
        self.cloud.tra_loi.assert_not_called()
        self.assertEqual(self.tk(gate, "CHON_UNG_VIEN")["ty_le_kiem_hien_hanh"], 0)

    def test_moc_cu_van_di_qua_mask_va_cham_diem(self):
        moc = Mock(return_value=True)
        gate = self.cong(moc=moc)
        gate.goi(yeu_cau())
        moc.assert_called_once_with(ca.LOAI_VIEC[LOAI])
        self.assertEqual(self.tk(gate)["so_kiem"], 1)

    def test_mask_chan_hoac_cloud_loi_khong_duoc_cham_la_local_sai(self):
        for buoc in ("mask", "cloud", "mo_che"):
            with self.subTest(buoc=buoc):
                mask, cloud = MaskGia(), Mock()
                cloud.tra_loi.return_value = ca.PhanHoiCloud(self.cloud_text, "demo-cloud", 1, 1)
                if buoc == "mask":
                    mask.che.side_effect = ca.MaskKhongGui("MASK_CON_SOT")
                elif buoc == "cloud":
                    cloud.tra_loi.side_effect = ca.CloudLoi("CLOUD_LOI")
                else:
                    mask.mo_che.side_effect = ca.MaskKhongGui("MASK_MO_CHE_LOI")
                gate = self.cong(cfg={"ty_le_ban_dau": 1})
                gate._mask, gate._nha_cung_cap = mask, cloud
                kq = gate.goi(yeu_cau())
                self.assertTrue(kq.co_ket_qua)
                self.assertEqual(self.tk(gate)["so_kiem"], 0)
                self.assertNotIn(ca.LOCAL_SAI, gate.bo_ghi.ban_ghi[-1].ly_do)
                if buoc == "mask":
                    cloud.tra_loi.assert_not_called()

    def test_cloud_duoi_nguong_thieu_truong_sai_trich_dan_khong_cham(self):
        data = json.loads(tra_loi(ten="[CONG_TY_001]"))
        hong = []
        hong.append({**data, "do_tin_cay": 0.1})
        hong.append({**data, "truong": data["truong"][:1]})
        hong.append({**data, "truong": [{**data["truong"][0], "trich_dan": "DEMO không có trong gốc"},
                                         data["truong"][1]]})
        for d in hong:
            with self.subTest(data=d):
                self.cloud_text = json.dumps(d, ensure_ascii=False)
                gate = self.cong(cfg={"ty_le_ban_dau": 1})
                gate.goi(yeu_cau())
                self.assertEqual(self.tk(gate)["so_kiem"], 0)
                self.assertIsNone(self.tk(gate)["phan_tram_chinh_xac"])

    def test_local_khong_chac_di_cloud_nhung_khong_tinh_vao_mau_ngau_nhien(self):
        self.local_text = tra_loi(tin_cay=0.4)
        gate = self.cong(cfg={"ty_le_ban_dau": 1})
        with patch.object(ca.random, "random", side_effect=AssertionError("Không lấy mẫu Local không chắc")):
            gate.goi(yeu_cau())
        self.cloud.tra_loi.assert_called_once()
        self.assertEqual(self.tk(gate)["so_kiem"], 0)
        self.assertNotIn(ca.LOCAL_DUNG, gate.bo_ghi.ban_ghi[-1].ly_do)

    def test_thieu_truong_cloud_khi_khong_khai_danh_sach_van_so_ca_hai_tap(self):
        self.cloud_text = json.dumps({"truong": json.loads(self.cloud_text)["truong"][:1], "do_tin_cay": 0.99})
        gate = self.cong(cfg={"ty_le_ban_dau": 1})
        gate.goi(yeu_cau(truong=()))
        self.assertIn(ca.LOCAL_SAI, gate.bo_ghi.ban_ghi[-1].ly_do)

    def test_python_tu_choi_cloud_thi_khong_cham(self):
        gate = self.cong(cfg={"ty_le_ban_dau": 1})
        gate.goi(yeu_cau(), kiem_tra=lambda rows, text: ["gia_tri"] if rows["gia_tri"].nguon == "CLOUD" else [])
        self.assertEqual(self.tk(gate)["so_kiem"], 0)

    def test_thong_ke_chi_doc_khong_goi_ai_khong_thay_doi_nhat_ky(self):
        gate = self.cong(cfg={"ty_le_ban_dau": 1})
        gate.goi(yeu_cau())
        truoc = list(gate.bo_ghi.ban_ghi)
        self.mask.che.reset_mock()
        self.mask.co_khoa.reset_mock()
        self.cloud.tra_loi.reset_mock()
        self.local.reset_mock()
        tk = gate.thong_ke()
        self.assertEqual(len(tk), len(ca.LOAI_VIEC))
        self.assertEqual(truoc, gate.bo_ghi.ban_ghi)
        self.mask.che.assert_not_called()
        self.mask.co_khoa.assert_not_called()
        self.cloud.tra_loi.assert_not_called()
        self.local.assert_not_called()

    def test_giam_qua_hai_bac_va_tang_lai_sau_khi_tut_trong_cua_so(self):
        gate = self.cong(cfg={"ty_le_theo_loai": {LOAI: 0.20}})
        with patch.object(ca.random, "random", return_value=0):
            for _ in range(49):
                gate.goi(yeu_cau())
            self.assertEqual(self.tk(gate)["ty_le_kiem_hien_hanh"], 0.20)
            gate.goi(yeu_cau())
            self.assertEqual(self.tk(gate)["ty_le_kiem_hien_hanh"], 0.10)
            for _ in range(50):
                gate.goi(yeu_cau())
            self.assertEqual(self.tk(gate)["ty_le_kiem_hien_hanh"], 0.05)
            self.cloud_text = tra_loi("456 đồng", ten="[CONG_TY_001]")
            for _ in range(11):
                gate.goi(yeu_cau())
        tk = self.tk(gate)
        self.assertEqual((tk["so_luot"], tk["so_kiem"], tk["so_kiem_cua_so"]), (111, 111, 100))
        self.assertEqual(tk["phan_tram_chinh_xac"], 89)
        self.assertEqual(tk["ty_le_kiem_hien_hanh"], 0.20)
        self.assertEqual(tk["canh_bao"], "LOCAL_DUOI_NGUONG_CHINH_XAC")
        # Tính lại từ nhật ký, không phụ thuộc đời sống một đối tượng CongAI.
        gate_moi = self.cong(cfg={"ty_le_theo_loai": {LOAI: 0.20}}, bo=gate.bo_ghi)
        self.assertEqual(self.tk(gate_moi), tk)
        self.assertEqual(self.tk(gate_moi, LOAI_KHAC)["so_kiem"], 0)

    def test_cua_so_cau_hinh_va_san_khong_tu_giam_ve_0(self):
        gate = self.cong(cfg={"ty_le_ban_dau": 0.2, "cua_so": 3, "ty_le_san": 0.07,
                              "bac_thang": [[3, 0.90, 0.0]]})
        with patch.object(ca.random, "random", return_value=0):
            for _ in range(5):
                gate.goi(yeu_cau())
        tk = self.tk(gate)
        self.assertEqual((tk["so_kiem"], tk["so_kiem_cua_so"], tk["ty_le_kiem_hien_hanh"]), (5, 3, 0.07))

    def test_dung_90_phan_tram_chua_du_dieu_kien_giam(self):
        cfg = ca.cai_dat_kiem_xac_suat({"ty_le_ban_dau": 0.2})
        self.assertEqual(ca.ty_le_kiem_hien_hanh(cfg, LOAI, {"so_kiem_cua_so": 100, "so_dung_cua_so": 90}), 0.2)
        self.assertEqual(ca.ty_le_kiem_hien_hanh(cfg, LOAI, {"so_kiem_cua_so": 100, "so_dung_cua_so": 91}), 0.1)

    def test_loi_doc_thong_ke_khong_giam_ti_le_va_khong_lo_noi_dung(self):
        bo = ca.BoGhiBoNho()
        bo.thong_ke = Mock(side_effect=RuntimeError("DEMO-bi-mat-DSN"))
        gate = self.cong(cfg={"ty_le_ban_dau": 0.2}, bo=bo)
        with self.assertLogs(ca.__name__, level="ERROR") as logs:
            tk = self.tk(gate)
            with patch.object(ca.random, "random", return_value=0.15):
                gate.goi(yeu_cau())
        self.assertFalse(tk["thong_ke_san_sang"])
        self.assertIsNone(tk["so_kiem"])
        self.assertEqual(tk["ty_le_kiem_hien_hanh"], 0.2)
        self.cloud.tra_loi.assert_called_once()
        self.assertNotIn("DEMO-bi-mat-DSN", repr(logs.output))

    def test_tham_so_hong_khong_the_mo_cloud_hay_lay_mau(self):
        for cfg in ({"ty_le_ban_dau": float("nan")}, {"ty_le_ban_dau": float("inf")},
                    {"ty_le_ban_dau": -1}, {"ty_le_ban_dau": True}, {"cua_so": 0},
                    {"ty_le_san": 0}, {"bac_thang": [[1, 0.8, 0.1]]},
                    {"ty_le_theo_loai": {"KHONG_CO": 1}}):
            with self.subTest(cfg=cfg):
                gate = self.cong(cfg=cfg)
                self.assertTrue(gate.cai_dat["loi"])
                gate.goi(yeu_cau())
        self.cloud.tra_loi.assert_not_called()
        self.mask.che.assert_not_called()


class ThongKePostgresGiaTests(unittest.TestCase):
    def test_cua_so_chon_theo_thoi_gian_khong_theo_thu_tu_doc(self):
        bo = ca.BoGhiBoNho()
        b = ca.BanGhiCongAI("yc-DEMO", "2026-10-26T00:00:03+00:00", LOAI, "CLOUD", "demo", "demo", True,
                           ket_qua="DAT", ly_do_chuyen_cloud=("KIEM_XAC_SUAT",), ly_do=(ca.LOCAL_SAI,))
        bo.ghi(b)
        bo.ghi(replace(b, luc="2026-10-26T00:00:01+00:00", ly_do=(ca.LOCAL_DUNG,)))
        bo.ghi(replace(b, luc="2026-10-26T00:00:02+00:00", ly_do=(ca.LOCAL_DUNG,)))
        self.assertEqual(bo.thong_ke(1)[LOAI]["so_dung_cua_so"], 0)
        self.assertEqual(bo.thong_ke(2)[LOAI]["so_dung_cua_so"], 1)

    def test_chi_select_tham_so_hoa_khong_noi_dung_va_tra_du_so_do(self):
        conn = MagicMock()
        conn.__enter__.return_value = conn
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = [(LOAI, 120, 110, 100, 96)]
        bo = ca.BoGhiPostgres(Mock(return_value=conn))
        rows = bo.thong_ke(100)
        self.assertEqual(rows[LOAI], dict(so_luot=120, so_kiem=110, so_kiem_cua_so=100, so_dung_cua_so=96))
        sql, params = cur.execute.call_args.args
        self.assertEqual(sql.count("%s"), len(params))
        self.assertEqual(params, (ca.LOCAL_DUNG, ca.LOCAL_DUNG, ca.LOCAL_SAI, 100, 100))
        self.assertNotRegex(sql.upper(), r"\b(INSERT|UPDATE|DELETE|TRUNCATE|CREATE|ALTER)\b")
        self.assertNotIn("ket_qua_tom_tat", sql)
        self.assertIn("PARTITION BY loai_viec ORDER BY luc DESC, id DESC", sql)

    def test_diem_duoc_luu_qua_bo_ghi_postgres_hien_co(self):
        conn = MagicMock()
        conn.__enter__.return_value = conn
        cur = conn.cursor.return_value.__enter__.return_value
        b = ca.BanGhiCongAI("yc-DEMO", "2026-10-26T00:00:00+00:00", LOAI, "CLOUD", "demo", "demo", True,
                           ly_do_chuyen_cloud=("KIEM_XAC_SUAT",), ket_qua="DAT",
                           ly_do=(ca.LOCAL_SAI, "SO_TRUONG_DUNG_1", "SO_TRUONG_SAI_1"))
        ca.BoGhiPostgres(Mock(return_value=conn)).ghi(b)
        sql, params = cur.execute.call_args.args
        self.assertEqual(params[18], list(b.ly_do))
        self.assertIn("NULL, NULL", sql)

    def test_nhat_ky_cu_va_luot_kiem_that_bai_khong_thanh_mau_dung(self):
        bo = ca.BoGhiBoNho()
        b = ca.BanGhiCongAI("yc-DEMO", "2026-10-26T00:00:00+00:00", LOAI, "CLOUD", "demo", "demo", True,
                           ket_qua="DAT", ly_do_chuyen_cloud=("KIEM_XAC_SUAT",))
        for row in (b, replace(b, da_gui=False, ly_do=(ca.LOCAL_DUNG,)),
                    replace(b, ket_qua="LOI", ly_do=(ca.LOCAL_DUNG,)),
                    replace(b, ly_do=(ca.LOCAL_DUNG, ca.LOCAL_SAI)),
                    replace(b, ly_do_chuyen_cloud=("DUOI_NGUONG",), ly_do=(ca.LOCAL_DUNG,))):
            bo.ghi(row)
        self.assertEqual(bo.thong_ke(10)[LOAI]["so_kiem"], 0)


if __name__ == "__main__":
    unittest.main()
