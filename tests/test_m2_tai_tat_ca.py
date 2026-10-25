"""M2-00-02: route/điều phối thật, bộ tải giả M2e; không socket, mạng hay dữ liệu thật."""
from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

for _p in (Path(__file__).resolve().parent.parent, Path(__file__).resolve().parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from tests import test_m2_00b_tinh as gia
from tests.test_m2_00e_http import AppHttp
from kho_tri_thuc.giao_dien import m2_tai_hoa_don as mod


TEN = {gia.PN_A: "Công ty DEMO Ánh Dương", gia.PN_B: "Công ty DEMO Bình Minh"}
CHON = {"mode": "month", "year": 2026, "month": 9, "types": ["purchase", "sold"], "formats": ["xml", "pdf"]}


class KetNoiTen(gia.KetNoiGia):
    def execute(self, sql, params=()):
        if " ".join(sql.split()) == "SELECT ten FROM master.phap_nhan WHERE id = %s":
            return gia._Cur([{"ten": TEN[params[0]]}])
        return super().execute(sql, params)


class BoTai(gia.NodeGia):
    def __init__(self):
        super().__init__()
        self.khoa = threading.RLock()
        self.chong = 0
        self.mat_phan_hoi_start = False

    def xu_ly(self, method, path, hd, body):
        with self.khoa:
            if path == "/api/start" and self.running:
                self.chong += 1
            r = super().xu_ly(method, path, hd, body)
            if path == "/api/start" and self.mat_phan_hoi_start:
                self.mat_phan_hoi_start = False
                raise ConnectionResetError("DEMO: đã nhận lệnh nhưng mất phản hồi")
            return r

    def xong(self, loi=False):
        with self.khoa:
            key = self.running
            self.ket_thuc(key)
            if loi:
                self.jobs[key]["receipt"]["trang_thai"] = "FAILED"
                for r in self.jobs[key]["receipt"]["runs"]:
                    r["trang_thai"] = "FAILED"
                    r["loi"] = [{"code": "LOGIN_TIMEOUT"}]


class HandlerGia:
    def __init__(self, body, sid):
        self.body, self.sid = body, sid

    def json_body(self, _gioi_han):
        return self.body

    def crm_sid(self):
        return self.sid

    def send_content(self, status, body, headers=None):
        self.kq = (status, body)
        return self.kq


class TienTrinh(gia.TienTrinhGia):
    def stop(self):
        with self.node.khoa:
            self.node.running = None  # Dừng tiến trình thật cũng dừng job đang chạy.
        return super().stop()


class TaiTatCaTest(unittest.TestCase):
    def setUp(self):
        # Fake DB chỉ ghi nhận register_dumper, không mã hóa/IO PostgreSQL.
        # Khi sandbox thiếu driver, thay đúng lớp đăng ký kiểu; mọi guard/SQL vẫn chạy thật.
        try:
            from psycopg.types.string import StrDumperUnknown  # noqa: F401
        except ModuleNotFoundError:
            string = ModuleType("psycopg.types.string")
            string.StrDumperUnknown = type("StrDumperUnknownGia", (), {})
            self.driver = patch.dict(sys.modules, {"psycopg.types.string": string})
            self.driver.start()
            self.addCleanup(self.driver.stop)
        self.tam = tempfile.TemporaryDirectory(prefix="m2h-demo-", ignore_cleanup_errors=True)
        self.addCleanup(self.tam.cleanup)
        root = Path(self.tam.name)
        self.conn = KetNoiTen()
        self.app = AppHttp(self.conn, root / "app")
        self.app.dat_phien(gia.SID_KT, "MO_PHONG_KE_TOAN")
        self.app.dat_phien(gia.SID_XA, "MO_PHONG_XEM_A")
        self.cfg = gia.tao_cau_hinh(root / "cfg", nhip_poll_s=0.01)
        self.node = BoTai()
        self.node.san_sang = {gia.MA_A: (True, None), gia.MA_B: (True, None)}
        self.tt = TienTrinh(self.node, self.cfg.gioi_han)
        self.app._tai_hoa_don = {"cau_hinh": self.cfg, "tien_trinh": self.tt}
        self.dv = mod.dich_vu(self.app)
        self.addCleanup(self.dung_va_cho)

    def dung_va_cho(self):
        mod.dung(self.app)
        if self.dv._hang_doi:
            self.cho(lambda: not self.dv._hang_doi["dang_chay"])

    def goi(self, post=True, ten="tai-tat-ca", body=None, sid=gia.SID_KT):
        h = HandlerGia(dict(CHON) if body is None else body, sid)
        mod.dieu_huong(h, self.app, post, mod.TIEN_TO + "/" + ten, {})
        return h.kq

    def cho(self, fn):
        han = time.monotonic() + 4
        while time.monotonic() < han:
            if fn():
                return
            time.sleep(0.005)
        self.fail("Bộ tải giả không đến trạng thái mong đợi trong 4 giây")

    def cho_job(self, so):
        self.cho(lambda: self.node.so_start == so)

    def cho_xong(self):
        self.cho(lambda: not self.dv._hang_doi["dang_chay"])
        return self.goi(False, "hang-doi")[1]

    def test_m2_00_02_hai_profile_thu_muc_rieng_tuan_tu(self):
        status, q = self.goi()
        self.assertEqual(status, 200, q)
        self.cho_job(1)
        self.assertEqual(self.node.so_start, 1)
        status, q = self.goi(False, "hang-doi")
        self.assertEqual(status, 200)
        self.assertEqual([m["trang_thai"] for m in q["muc"]], ["Đang tải", "Chờ"])
        self.assertEqual([m["phap_nhan_ten"] for m in q["muc"]], list(TEN.values()))
        self.node.xong()
        self.cho_job(2)
        q = self.goi(False, "hang-doi")[1]
        self.assertEqual([m["trang_thai"] for m in q["muc"]], ["Xong", "Đang tải"])
        self.node.xong()
        q = self.cho_xong()
        self.assertEqual([m["trang_thai"] for m in q["muc"]], ["Xong", "Xong"])
        jobs = list(self.node.jobs.values())
        self.assertEqual([j["ctx"]["profile"]["ref"] for j in jobs], [gia.MA_A, gia.MA_B])
        self.assertEqual([j["ctx"]["phap_nhan"]["uuid"] for j in jobs], [gia.PN_A, gia.PN_B])
        for j in jobs:
            self.assertEqual(j["ctx"]["request"], CHON)
            for run in j["receipt"]["runs"]:
                self.assertEqual(run["run_rel"].split("/")[0], j["ctx"]["profile"]["ref"])
                self.assertTrue(run["run_rel"].endswith(j["ctx"]["run"]["run_id"]))
        self.assertEqual(self.node.chong, 0)
        text = json.dumps(q, ensure_ascii=False)
        for cam in (gia.CAP, gia.SID_KT, str(self.cfg.goc_profile), "company_key", "client_key", "revision", "nonce"):
            self.assertNotIn(cam, text)

    def test_bam_lan_hai_va_tai_le_bi_chan(self):
        self.assertEqual(self.goi()[0], 200)
        self.cho_job(1)
        status, q = self.goi(sid=gia.SID_XA)
        self.assertEqual(status, 409)
        self.assertEqual(q["error"], "M2_00H_DANG_CO_HANG_DOI")
        self.assertIn("Đang có hàng đợi", q["message"])
        sel = {**CHON, "source_instance": gia.INST, "scope_ref": gia.SCOPE, "company_key": gia.CTY_A, "khoa": "m2h-demo-0001"}
        self.assertEqual(self.goi(ten="bat-dau", body=sel)[0], 409)
        self.assertEqual(self.node.so_start, 1)

    def test_hai_lenh_dong_thoi_chi_mot_hang_doi(self):
        r, gate = [], threading.Barrier(3)

        def gui():
            gate.wait()
            r.append(self.goi()[0])
        threads = [threading.Thread(target=gui) for _ in range(2)]
        for t in threads:
            t.start()
        gate.wait()
        for t in threads:
            t.join(4)
        self.assertEqual(sorted(r), [200, 409])
        self.cho_job(1)
        self.assertEqual(self.node.chong, 0)

    def test_phap_nhan_khong_co_quyen_bi_loai(self):
        self.assertEqual(self.goi(sid=gia.SID_XA)[0], 200)
        self.cho_job(1)
        self.node.xong()
        self.cho(lambda: not self.dv._hang_doi["dang_chay"])
        q = self.goi(False, "hang-doi", sid=gia.SID_XA)[1]
        self.assertEqual([m["phap_nhan_ten"] for m in q["muc"]], [TEN[gia.PN_A]])
        self.assertEqual(self.node.so_start, 1)

    def test_chi_lay_phap_nhan_co_profile(self):
        self.node.san_sang[gia.MA_A] = (False, "PROFILE_NOT_FOUND")
        self.assertEqual(self.goi()[0], 200)
        self.cho_job(1)
        self.node.xong()
        q = self.cho_xong()
        self.assertEqual([m["phap_nhan_ten"] for m in q["muc"]], [TEN[gia.PN_B]])

    def test_loi_job_truoc_van_chay_job_sau(self):
        self.assertEqual(self.goi()[0], 200)
        self.cho_job(1)
        self.node.xong(loi=True)
        self.cho_job(2)
        self.node.xong()
        q = self.cho_xong()
        self.assertEqual([m["trang_thai"] for m in q["muc"]], ["Lỗi", "Xong"])
        self.assertIn("Quá hạn chờ đăng nhập", q["muc"][0]["ly_do"])
        self.assertEqual(self.node.chong, 0)

    def test_loi_start_mot_cong_ty_khong_chan_cong_ty_sau(self):
        # Callback đếm yêu cầu, không thay logic tạo job của bộ tải giả.
        count = []
        def tu_choi_dau(path):
            if path == "/api/start":
                count.append(path)
                self.node.loi_start = (400, "PROFILE_NOT_FOUND") if len(count) == 1 else None
        self.node.khi_goi = tu_choi_dau
        self.assertEqual(self.goi()[0], 200)
        self.cho_job(1)
        self.node.xong()
        q = self.cho_xong()
        self.assertEqual([m["trang_thai"] for m in q["muc"]], ["Lỗi", "Xong"])

    def test_kiem_lai_quyen_truoc_job_sau(self):
        self.assertEqual(self.goi()[0], 200)
        self.cho_job(1)
        with self.app.mutation_lock:
            self.conn.phan_quyen = [r for r in self.conn.phan_quyen if r["phap_nhan_id"] != gia.PN_B]
        self.node.xong()
        self.cho_xong()
        self.assertEqual(self.node.so_start, 1)
        self.assertEqual(self.dv._hang_doi["muc"][1]["trang_thai"], "Lỗi")
        self.assertEqual(len(self.goi(False, "hang-doi")[1]["muc"]), 1)

    def test_mat_ket_noi_khong_chay_chong(self):
        self.assertEqual(self.goi()[0], 200)
        self.cho_job(1)
        self.node.ngat = True
        self.cho(lambda: bool(self.dv._hang_doi["muc"][0]["ly_do"]))
        self.assertEqual(self.node.so_start, 1)
        self.assertEqual(self.goi()[0], 409)
        self.node.ngat = False
        self.node.xong()
        self.cho_job(2)
        self.node.xong()
        self.cho_xong()
        self.assertEqual(self.node.chong, 0)

    def test_phien_khac_khong_thay_tien_do(self):
        self.assertEqual(self.goi()[0], 200)
        status, q = self.goi(False, "hang-doi", sid=gia.SID_XA)
        self.assertEqual(status, 200)
        self.assertEqual(q["muc"], [])
        self.assertTrue(q["dang_co_hang_doi"])

    def test_mat_phan_hoi_start_doi_soat_truoc_job_sau(self):
        self.node.mat_phan_hoi_start = True
        self.assertEqual(self.goi()[0], 200)
        self.cho_job(1)
        self.cho(lambda: any(path == "/api/reconcile" for _, path in self.node.goi))
        self.assertEqual(self.node.so_start, 1)
        self.node.xong()
        self.cho_job(2)
        self.node.xong()
        self.cho_xong()
        self.assertEqual(self.node.chong, 0)

    def test_hang_doi_xong_co_the_tai_dot_moi(self):
        for so in (1, 3):
            self.assertEqual(self.goi()[0], 200)
            self.cho_job(so)
            self.node.xong()
            self.cho_job(so + 1)
            self.node.xong()
            self.cho_xong()
        self.assertEqual(len(self.node.jobs), 4)
        self.assertEqual(self.node.chong, 0)

    def test_tu_choi_truong_quyen_ky_sai_va_khong_profile(self):
        for them in ({"profile": "DEMO"}, {"phap_nhan": "DEMO"}, {"path": "DEMO"}, {"actor": "DEMO"}):
            self.assertEqual(self.goi(body={**CHON, **them})[0], 403)
        self.assertEqual(self.goi(body={**CHON, "month": 13})[0], 400)
        self.node.san_sang = {}
        self.assertEqual(self.goi()[0], 400)
        self.assertEqual(self.node.so_start, 0)

    def test_tai_le_dang_chay_khong_tao_hang_doi(self):
        sel = {**CHON, "source_instance": gia.INST, "scope_ref": gia.SCOPE, "company_key": gia.CTY_A, "khoa": "m2h-demo-0001"}
        self.assertEqual(self.goi(ten="bat-dau", body=sel)[0], 200)
        self.assertEqual(self.goi()[0], 409)
        self.assertIsNone(self.dv._hang_doi)

    def test_job_treo_qua_han_dung_truoc_khi_chay_phap_nhan_sau(self):
        self.dv.cau_hinh = replace(self.cfg, gioi_han=replace(self.cfg.gioi_han, cho_moi_job_s=1))
        self.assertEqual(self.goi()[0], 200)
        self.cho_job(2)  # Job đầu không bao giờ hoàn tất, job sau vẫn phải khởi chạy.
        self.assertEqual(self.tt.so_dung, 1)
        self.assertEqual(self.tt.so_start, 1)
        self.node.xong()
        q = self.cho_xong()
        self.assertEqual([m["trang_thai"] for m in q["muc"]], ["Lỗi", "Xong"])
        self.assertEqual(q["muc"][0]["ly_do"], "Quá hạn chờ")
        self.assertEqual(self.node.chong, 0)
        self.assertIsNone(self.dv._dang_chay)
        self.assertEqual(self.goi()[0], 200, "Hàng đợi mới không bị khóa sau quá hạn")

    def test_unknown_mai_cung_qua_han(self):
        self.dv.cau_hinh = replace(self.cfg, gioi_han=replace(self.cfg.gioi_han, cho_moi_job_s=1))
        self.node.mat_phan_hoi_start = True
        with patch.object(self.dv, "reconcile", return_value={"trang_thai": "UNKNOWN", "run_handle": "a" * 64}):
            self.assertEqual(self.goi()[0], 200)
            self.cho_job(2)
            self.node.xong()
            q = self.cho_xong()
        self.assertEqual(q["muc"][0]["ly_do"], "Quá hạn chờ")
        self.assertEqual(q["muc"][1]["trang_thai"], "Xong")
        self.assertEqual(self.node.chong, 0)

    def test_dung_may_chu_danh_thuc_nhip_poll_dai_va_mo_khoa(self):
        self.dv.cau_hinh = replace(self.cfg, gioi_han=replace(self.cfg.gioi_han, nhip_poll_s=60))
        self.assertEqual(self.goi()[0], 200)
        self.cho_job(1)
        mod.dung(self.app)
        q = self.cho_xong()  # Không phải đợi hết nhịp poll 60 giây.
        self.assertEqual([m["trang_thai"] for m in q["muc"]], ["Đã hủy", "Đã hủy"])
        self.assertIsNone(self.node.running)
        self.assertEqual(self.node.so_start, 1)

    def test_ngoai_le_khong_phai_data_error_dung_va_mo_khoa(self):
        with patch.object(self.dv, "status", side_effect=RuntimeError("DEMO: lỗi driver")):
            self.assertEqual(self.goi()[0], 200)
            q = self.cho_xong()
        self.assertEqual(q["muc"][0]["trang_thai"], "Lỗi")
        self.assertEqual(self.tt.so_dung, 1)
        self.assertIsNone(self.dv._dang_chay)
        self.assertEqual(self.node.so_start, 1)
        self.dv.khoi_dong_neu_can()
        self.assertEqual(self.goi()[0], 200)

    def test_huy_chi_chu_hang_doi_duoc_dung_job_va_cac_dong_cho(self):
        self.assertEqual(self.goi()[0], 200)
        self.cho_job(1)
        status, _ = self.goi(ten="huy-hang-doi", body={}, sid=gia.SID_XA)
        self.assertEqual(status, 403)
        self.assertEqual(self.tt.so_dung, 0)
        self.assertTrue(self.dv._hang_doi["dang_chay"])
        self.assertEqual(self.goi(ten="huy-hang-doi", body={}), (200, {"da_huy": True}))
        q = self.cho_xong()
        self.assertEqual([m["trang_thai"] for m in q["muc"]], ["Đã hủy", "Đã hủy"])
        self.assertEqual(self.tt.so_dung, 1)
        self.assertIsNone(self.node.running)
        self.assertIsNone(self.dv._dang_chay)
        self.assertEqual(self.node.so_start, 1)
        self.dv.khoi_dong_neu_can()
        self.assertEqual(self.goi()[0], 200, "Cờ hủy cũ không được hủy đợt mới")
        self.cho_job(2)
        self.node.xong()
        self.cho_job(3)
        self.node.xong()
        self.cho_xong()

    def test_huy_giu_khoa_den_khi_bo_tai_dung(self):
        self.assertEqual(self.goi()[0], 200)
        self.cho_job(1)
        vao, tiep = threading.Event(), threading.Event()
        stop = self.dv.stop

        def dung_cham():
            vao.set()
            self.assertTrue(tiep.wait(3))
            return stop()

        r = []
        with patch.object(self.dv, "stop", side_effect=dung_cham):
            t = threading.Thread(target=lambda: r.append(self.goi(ten="huy-hang-doi", body={})))
            t.start()
            try:
                self.assertTrue(vao.wait(3))
                self.assertEqual(self.goi()[0], 409)
            finally:
                tiep.set()
                t.join(4)
        self.assertFalse(t.is_alive())
        self.assertEqual(r, [(200, {"da_huy": True})])
        self.cho_xong()
        self.assertEqual(self.node.so_start, 1)

    def test_tai_le_xong_khong_poll_thi_tai_tat_ca_khong_409(self):
        sel = {**CHON, "source_instance": gia.INST, "scope_ref": gia.SCOPE, "company_key": gia.CTY_A, "khoa": "m2h-demo-0001"}
        self.assertEqual(self.goi(ten="bat-dau", body=sel)[0], 200)
        self.node.xong()
        self.assertIsNotNone(self.dv._dang_chay, "Mô phỏng tab đóng, không gọi status")
        self.assertEqual(self.goi()[0], 200)
        self.cho_job(2)
        self.assertEqual(self.node.chong, 0)

    def test_co_tai_le_cu_mat_ket_noi_tra_loi_tieng_viet(self):
        for ma in ("KHACH_KHONG_KET_NOI", "KHACH_QUA_HAN"):
            with self.subTest(ma=ma):
                self.dv._dang_chay = "DEMO-cu"
                khach = self.tt.khach()
                with patch.object(self.dv, "_khach", return_value=khach), patch.object(khach, "config", side_effect=mod.LoiKhach(ma)):
                    status, body = self.goi()
                self.assertEqual(status, 502)
                self.assertEqual(body["error"], "M2_00B_" + ma)
                self.assertIn("bộ tải", body["message"])
                self.assertIsNone(self.dv._hang_doi)
                self.assertEqual(self.dv._dang_chay, "DEMO-cu")
        self.assertEqual(self.node.so_start, 0)

    def test_loi_tao_va_start_thread_khong_giu_hang_doi(self):
        for diem in ("Thread", "Thread.start"):
            dich, ten = (mod.threading, "Thread") if diem == "Thread" else (mod.threading.Thread, "start")
            with self.subTest(diem=diem), patch.object(dich, ten, side_effect=RuntimeError("DEMO")):
                with self.assertRaises(RuntimeError):
                    self.dv.tai_tat_ca(gia.SID_KT, CHON)
                self.assertIsNone(self.dv._hang_doi)
        self.assertEqual(self.goi()[0], 200, "Có thể tạo lại hàng đợi sau lỗi luồng")
        self.cho_job(1)

    def dung_chua_xac_nhan(self):
        self.tt.san = False
        self.tt.chung_dung = {"popen_pid": 123, "ma": "DEMO_CHUA_DUNG"}
        return {"trang_thai": "DUNG_CHUA_XAC_NHAN", "chung_dung": self.tt.chung_dung}

    def test_huy_chua_dung_tra_canh_bao_va_khong_mo_bo_tai_thu_hai(self):
        self.assertEqual(self.goi()[0], 200)
        self.cho_job(1)
        with patch.object(self.tt, "stop", side_effect=self.dung_chua_xac_nhan):
            status, body = self.goi(ten="huy-hang-doi", body={})
            q = self.cho_xong()
        self.assertEqual(status, 502)
        self.assertEqual(body["message"], mod.CANH_BAO_DUNG)
        self.assertNotIn("da_huy", body)
        self.assertTrue(all(m["ly_do"] == mod.CANH_BAO_DUNG for m in q["muc"]))
        self.assertIsNotNone(self.node.running, "Bộ tải cũ còn chạy trong mô phỏng")
        with self.assertRaises(mod.DataError) as err:
            self.dv.khoi_dong_neu_can()
        self.assertEqual(err.exception.code, "M2_00B_DUNG_CHUA_XAC_NHAN")
        self.assertEqual(self.tt.so_start, 0)
        self.assertEqual(self.node.so_start, 1)

    def test_ngoai_le_stop_chua_xac_nhan_giu_canh_bao(self):
        with patch.object(self.dv, "status", side_effect=RuntimeError("DEMO")), patch.object(self.tt, "stop", side_effect=self.dung_chua_xac_nhan):
            self.assertEqual(self.goi()[0], 200)
            q = self.cho_xong()
        self.assertEqual([m["trang_thai"] for m in q["muc"]], ["Lỗi", "Đã hủy"])
        self.assertTrue(all(m["ly_do"] == mod.CANH_BAO_DUNG for m in q["muc"]))
        with self.assertRaises(mod.DataError):
            self.dv.khoi_dong_neu_can()
        self.assertEqual(self.tt.so_start, 0)
        self.assertEqual(self.node.so_start, 1)

    def test_khoi_dong_lai_chi_sau_khi_stop_xac_nhan(self):
        self.tt.san = False
        loi = mod.DataError("M2_00B_DA_KHOI_DONG", "DEMO")
        with patch.object(self.dv, "khoi_dong", side_effect=loi) as mo, patch.object(self.tt, "stop", side_effect=self.dung_chua_xac_nhan):
            with self.assertRaises(mod.DataError) as err:
                self.dv.khoi_dong_neu_can()
        self.assertEqual(err.exception.code, "M2_00B_DUNG_CHUA_XAC_NHAN")
        self.assertEqual(mo.call_count, 1, "Không thử khởi động lần hai khi chưa dừng")

    def test_profiles_doc_tien_do_khong_giu_khoa_hang_doi(self):
        self.assertEqual(self.goi()[0], 200)
        self.cho_job(1)
        profiles = self.dv.profiles
        vao, tiep = threading.Event(), threading.Event()

        def profiles_cham(sid):
            vao.set()
            self.assertTrue(tiep.wait(3))
            return profiles(sid)

        r = []
        with patch.object(self.dv, "profiles", side_effect=profiles_cham):
            t = threading.Thread(target=lambda: r.append(self.goi(False, "hang-doi")))
            t.start()
            try:
                self.assertTrue(vao.wait(3))
                self.node.xong()
                self.cho_job(2)  # RPC đọc tiến độ treo không cản worker cập nhật/chạy tiếp.
            finally:
                tiep.set()
                t.join(4)
        self.assertEqual(r[0][0], 200)

    def test_trang_thai_dung_chung_profiles_khong_quet_hai_lan(self):
        self.assertEqual(self.goi()[0], 200)
        self.cho_job(1)
        with patch.object(self.dv, "profiles", wraps=self.dv.profiles) as profiles:
            self.assertEqual(self.goi(False, "")[0], 200)
        self.assertEqual(profiles.call_count, 1)
