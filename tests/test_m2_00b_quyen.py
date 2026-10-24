"""M2-00B quyền/nhật ký — từ chối TRƯỚC IO và thu hồi SAU IO/giữa SSE qua helper quyền THẬT trên fake conn literal (xem test_m2_00b_tinh).

Trạng thái: AUTHORED_NOT_RUN. Mọi ca từ chối khẳng định: 0 gọi /api/start (0 credential/portal/artifact phía Node), 0 nhật ký commit, 0 binding.
Thu hồi khi run SỞ HỮU đang chạy → dừng hữu hạn tiến trình sở hữu (TienTrinhGia.so_dung), không trả kết quả, không tự chạy lại.
"""

from __future__ import annotations

import unittest

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2.hoa_don import HoaDonK2

from test_m2_00b_tinh import CTY_A, CTY_B, INST, MA_A, PAYLOAD, PN_A, PN_B, SHA, SHA_MOI, SID_KT, SID_XA, U_KT, CoSoM2B, KetNoiGia, _Cur


class M2BTuChoiTruocIO(CoSoM2B):
    def _tu_choi(self, sid, sel, ma):
        with self.assertRaises(DataError) as e:
            self.dp.start(sid, sel)
        self.assertEqual(e.exception.code, ma)
        self.assertEqual([p for _, p in self.node.goi if p == "/api/start"], [])
        self.assertEqual(self.conn.nhat_ky, [])
        thu_muc = self.cfg.goc_dieu_phoi / "m2-00b-binding"
        self.assertFalse(thu_muc.exists() and any(p.suffix == ".json" for p in thu_muc.iterdir()))

    def test_b05_khong_phien(self):
        self._tu_choi("sid-khong-ton-tai", self.chon(), "CRM_PHIEN")
        self._tu_choi("", self.chon(), "CRM_PHIEN")
        self.assertEqual(self.conn.sql, [])

    def test_b05_vai_khong_duoc_m2_read(self):
        self.app.dat_phien("sid-bh", "MO_PHONG_BAN_HANG")
        self._tu_choi("sid-bh", self.chon(), "KHONG_CO_QUYEN_HANH_DONG")

    def test_b05_thieu_mot_phia_quyen_nguon(self):
        self.app.dat_phien("sid-kn", "MO_PHONG_KHONG_NGUON")  # chỉ INTAKE, thiếu READ_SOURCE
        self._tu_choi("sid-kn", self.chon(), "NGUON_KHONG_CO_QUYEN")

    def test_b05_pn_ngoai_quyen(self):
        self._tu_choi(SID_XA, self.chon(CTY_B), "KHONG_CO_QUYEN_PHAP_NHAN")

    def test_b05_thieu_module(self):
        self.conn.phan_quyen = [{**q, "module": ["CRM"]} if q["nguoi_dung_id"] == U_KT and q["phap_nhan_id"] == PN_A else q for q in self.conn.phan_quyen]
        self._tu_choi(SID_KT, self.chon(), "KHONG_CO_QUYEN_MODULE")

    def test_b05_csdl_tu_choi_module_du_app_cho(self):
        goc = self.conn.execute

        def execute(sql, params=None):
            if "master.ktt_duoc(" in sql:
                goc(sql, params)
                return _Cur([{"ok": False}])
            return goc(sql, params)
        self.conn.execute = execute  # RLS/ktt_duoc của CSDL là cổng quyết định: false → từ chối (không phải patch guard True)
        self._tu_choi(SID_KT, self.chon(), "KHONG_CO_QUYEN_MODULE")

    def test_b05_mapping_vang_va_xung_dot(self):
        self.conn.anh_xa = [m for m in self.conn.anh_xa if m["subject_key"] != CTY_A]
        self._tu_choi(SID_KT, self.chon(), "M2_00B_PN_MAPPING_ABSENT")
        self.conn.anh_xa.append({**self.conn.anh_xa[0], "id": "c0000000-0000-4000-8000-00000000000c", "subject_key": CTY_B, "phap_nhan_id": PN_A})
        self._tu_choi(SID_KT, self.chon(CTY_B, "k-demo-0002"), "M2_00B_PN_MAPPING_CONFLICT")

    def test_b05_company_ngoai_pham_vi(self):
        self._tu_choi(SID_KT, self.chon("MST_0199999999"), "NGUON_PHAM_VI")

    def test_b05_instance_khong_hoat_dong_va_digest_profile_sai(self):
        self.conn.instance[INST] = "NGUNG"
        self._tu_choi(SID_KT, self.chon(), "NGUON_PROFILE")
        self.conn.instance[INST] = "HOAT_DONG"
        self.conn.profile[0]["payload"] = {**PAYLOAD, "version": 9}
        self._tu_choi(SID_KT, self.chon(), "NGUON_PROFILE_DIGEST")

    def test_b05_danh_tinh_phien_db_lech_hoac_khoa(self):
        self.conn.ai_ep = "MO_PHONG_XEM_A"
        self._tu_choi(SID_KT, self.chon(), "DANH_TINH")
        self.conn.ai_ep = None
        self.conn.nguoi_dung["MO_PHONG_KE_TOAN"]["trang_thai"] = "KHOA"
        self._tu_choi(SID_KT, self.chon(), "DANH_TINH")

    def test_b05_ket_noi_khac_nhau_tu_choi(self):
        khac = HoaDonK2(KetNoiGia(), self.app.root / "m2-k2")
        self.app.m2 = lambda: khac  # nhật ký CRM và kiểm quyền M2 trên hai connection khác nhau → từ chối trước SQL
        self._tu_choi(SID_KT, self.chon(), "M2_00B_KET_NOI_KHAC")

    def test_b12_nhat_ky_loi_truoc_start_khong_start(self):
        self.conn.loi_nhat_ky = True
        self._tu_choi(SID_KT, self.chon(), "M2_00B_NHAT_KY_LOI")


class M2BThuHoiSauIO(CoSoM2B):
    def _bo_quyen_pn_a(self):
        self.conn.phan_quyen = [q for q in self.conn.phan_quyen if not (q["nguoi_dung_id"] == U_KT and q["phap_nhan_id"] == PN_A)]

    def test_b06_thu_hoi_trong_luc_start_khong_tra_ket_qua_va_dung(self):
        self.node.khi_goi = lambda path: self._bo_quyen_pn_a() if path == "/api/start" else None
        with self.assertRaises(DataError) as e:
            self.dp.start(SID_KT, self.chon())
        self.assertEqual(e.exception.code, "KHONG_CO_QUYEN_PHAP_NHAN")
        self.assertEqual(self.tt.so_dung, 1)
        self.assertEqual(self.hanh_dong(), ["M2_00B_YEU_CAU_TAI"])

    def test_b06_thu_hoi_sau_chay_dai_truoc_status_khong_goi_node(self):
        r = self.dp.start(SID_KT, self.chon())
        so_goi = len(self.node.goi)
        self._bo_quyen_pn_a()
        with self.assertRaises(DataError):
            self.dp.status(SID_KT, r["run_handle"])
        self.assertEqual(len(self.node.goi), so_goi)
        self.assertEqual(self.tt.so_dung, 1)
        with self.assertRaises(DataError):  # không tự cấp lại/chạy lại: Node đã dừng → chưa sẵn sàng
            self.dp.reconcile(SID_KT, r["run_handle"])

    def test_b06_doi_revision_profile_lam_mat_hieu_luc_ket_qua(self):
        r = self.dp.start(SID_KT, self.chon())
        self.node.ket_thuc()
        moi = {**PAYLOAD, "version": 2}
        self.conn.profile[0].update(payload=moi, profile_sha256=SHA_MOI)
        for row in self.conn.pham_vi + self.conn.anh_xa:
            row["profile_sha256"] = SHA_MOI
        self.conn.nguon_duoc = {(u, i, ref, SHA_MOI if s == SHA else s, a) for (u, i, ref, s, a) in self.conn.nguon_duoc}
        with self.assertRaises(DataError) as e:
            self.dp.status(SID_KT, r["run_handle"])
        self.assertEqual(e.exception.code, "M2_00B_NGU_CANH_DOI")

    def test_b06_doi_vai_van_duoc_doc_nhung_ket_qua_cu_mat_hieu_luc(self):
        r = self.dp.start(SID_KT, self.chon())
        self.conn.nguoi_dung["MO_PHONG_KE_TOAN"]["vai_tro"] = "XEM"
        with self.assertRaises(DataError) as e:
            self.dp.status(SID_KT, r["run_handle"])
        self.assertEqual(e.exception.code, "M2_00B_NGU_CANH_DOI")
        self.assertEqual(self.tt.so_dung, 1)

    def test_b06_phien_doi_nguoi_hoac_het(self):
        r = self.dp.start(SID_KT, self.chon())
        self.app.dat_phien(SID_KT, "MO_PHONG_XEM_A")
        with self.assertRaises(DataError) as e:
            self.dp.status(SID_KT, r["run_handle"])
        self.assertIn(e.exception.code, ("M2_00B_NGU_CANH_DOI", "KHONG_CO_QUYEN_PHAP_NHAN"))
        self.app.bo_phien(SID_KT)
        with self.assertRaises(DataError) as e:
            self.dp.status(SID_KT, r["run_handle"])
        self.assertEqual(e.exception.code, "CRM_PHIEN")

    def test_b06_thu_hoi_giua_sse_dung_phat_va_dung_run(self):
        r = self.dp.start(SID_KT, self.chon())
        g = self.dp.events(SID_KT, r["run_handle"], 0)
        self.assertEqual(next(g)["type"], "phase")
        self._bo_quyen_pn_a()
        self.assertEqual(next(g), {"ket_thuc": "QUYEN_THAY_DOI"})
        self.assertEqual(self.tt.so_dung, 1)
        with self.assertRaises(StopIteration):
            next(g)

    def test_b06_profiles_giao_hai_lan_kiem(self):
        self.node.san_sang = {MA_A: (True, None)}

        def khi(path):
            if path == "/api/profiles":
                self.conn.phan_quyen = [q for q in self.conn.phan_quyen if not (q["nguoi_dung_id"] == U_KT and q["phap_nhan_id"] == PN_B)]
        self.node.khi_goi = khi
        r = self.dp.profiles(SID_KT)
        self.assertEqual([m["company_key"] for m in r["muc"]], [CTY_A])

    def test_b12_nhat_ky_sau_io_loi_bao_unknown_roi_ghi_lai(self):
        r = self.dp.start(SID_KT, self.chon())
        self.node.ket_thuc()
        self.conn.loi_nhat_ky = True
        s1 = self.dp.status(SID_KT, r["run_handle"])
        self.assertEqual((s1["trang_thai"], s1["nhat_ky"]), ("REPLAY", "UNKNOWN"))
        self.conn.loi_nhat_ky = False
        s2 = self.dp.status(SID_KT, r["run_handle"])
        self.assertEqual(s2["nhat_ky"], "DA_GHI")
        self.assertEqual(self.hanh_dong().count("M2_00B_KET_THUC"), 1)

    def test_b07_dut_ket_noi_khi_start_la_unknown_can_doi_soat(self):
        self.node.ngat = True
        r = self.dp.start(SID_KT, self.chon())
        self.assertEqual((r["trang_thai"], r["ma"], r["can_doi_soat"]), ("UNKNOWN", "KHACH_KHONG_KET_NOI", True))
        self.assertEqual(self.hanh_dong(), ["M2_00B_YEU_CAU_TAI", "M2_00B_START_KHONG_RO"])
        self.node.ngat = False
        r2 = self.dp.start(SID_KT, self.chon())  # cùng khóa → cùng context/nonce (không chạy mù run mới)
        self.assertEqual(r2["run_handle"], r["run_handle"])
        self.assertEqual(len(self.nonce), 1)

    def test_b11_node_tu_choi_4xx_ma_on_dinh(self):
        self.node.loi_start = (409, "JOB_BUSY")
        with self.assertRaises(DataError) as e:
            self.dp.start(SID_KT, self.chon())
        self.assertEqual(e.exception.code, "M2_00B_JOB_BUSY")
        self.assertEqual(self.hanh_dong(), ["M2_00B_YEU_CAU_TAI", "M2_00B_START_TU_CHOI"])
        for row in self.conn.nhat_ky:
            self.assertEqual(row["phap_nhan_id"], PN_A)
        self.assertNotIn(SID_KT, repr(e.exception))


if __name__ == "__main__":
    unittest.main()
