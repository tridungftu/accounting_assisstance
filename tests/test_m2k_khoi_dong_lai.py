"""M2k: route thật, DB/proc/Windows Job giả; không server, socket hay Node thật."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

for _p in (Path(__file__).resolve().parent.parent, Path(__file__).resolve().parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from tests import test_m2_00b_tinh as gia
from tests.test_m2_00e_http import AppHttp
from tests.test_m2_tai_tat_ca import HandlerGia, KetNoiTen, BoTai, TienTrinh, CHON
from tests.test_m2_00b_tien_trinh import ProcGia, JobGia, KhachGia
from kho_tri_thuc.giao_dien import m2_tai_hoa_don as mod
from kho_tri_thuc.m2.tai_hoa_don import LoiTienTrinh, TienTrinhNode
from kho_tri_thuc.m2.tai_hoa_don.tien_trinh import KIEU_SAN_SANG, PROTOCOL


class KhoiDongLaiTest(unittest.TestCase):
    def setUp(self):
        try:
            from psycopg.types.string import StrDumperUnknown  # noqa: F401
        except ModuleNotFoundError:
            string = ModuleType("psycopg.types.string")
            string.StrDumperUnknown = type("StrDumperUnknownGia", (), {})
            p = patch.dict(sys.modules, {"psycopg.types.string": string})
            p.start()
            self.addCleanup(p.stop)
        self.tam = tempfile.TemporaryDirectory(prefix="m2k-demo-", ignore_cleanup_errors=True)
        self.addCleanup(self.tam.cleanup)
        root = Path(self.tam.name)
        self.conn = KetNoiTen()
        self.app = AppHttp(self.conn, root / "app")
        self.app.dat_phien(gia.SID_KT, "MO_PHONG_KE_TOAN")
        self.app.dat_phien(gia.SID_XA, "MO_PHONG_XEM_A")
        self.cfg = gia.tao_cau_hinh(root / "cfg")
        self.node = BoTai()
        self.node.san_sang = {gia.MA_A: (True, None), gia.MA_B: (True, None)}
        self.tt = TienTrinh(self.node, self.cfg.gioi_han)
        self.app._tai_hoa_don = {"cau_hinh": self.cfg, "tien_trinh": self.tt}
        self.dv = mod.dich_vu(self.app)
        # Bất cứ đường đi ngoài fake đều làm test thất bại ngay.
        for ten in ("socket.socket", "subprocess.Popen"):
            p = patch(ten, side_effect=AssertionError("Không được chạy tiến trình/mạng thật"))
            p.start()
            self.addCleanup(p.stop)

    def goi(self, sid=gia.SID_KT, body=None, ten="khoi-dong-lai", post=True):
        h = HandlerGia({} if body is None else body, sid)
        mod.dieu_huong(h, self.app, post, mod.TIEN_TO + ("/" + ten if ten else ""), {})
        return h.kq

    def ket_qua_nhat_ky(self):
        return [json.loads(r["sau"]) for r in self.conn.nhat_ky]

    def test_ke_toan_va_ke_toan_truong_duoc_ghi_ai_luc_ket_qua(self):
        for vai in ("KE_TOAN", "KE_TOAN_TRUONG"):
            with self.subTest(vai=vai):
                self.conn.nguoi_dung["MO_PHONG_KE_TOAN"]["vai_tro"] = vai
                status, body = self.goi()
                self.assertEqual(status, 200, body)
                self.assertEqual(body["nhat_ky"], "DA_GHI")
        self.assertEqual((self.tt.so_dung, self.tt.so_start), (2, 2))
        logs = self.ket_qua_nhat_ky()
        self.assertEqual([r["ket_qua"] for r in logs], ["YEU_CAU", "THANH_CONG"] * 2)
        self.assertEqual(logs[0]["thao_tac"], logs[1]["thao_tac"])
        self.assertRegex(logs[0]["luc"], r"\d{4}-\d{2}-\d{2}T.*\+07:00")
        self.assertTrue(all(r["nguoi"] == "MO_PHONG_KE_TOAN" for r in self.conn.nhat_ky))
        self.assertIs(self.dv.cau_hinh, self.cfg)
        self.assertEqual(self.node.goi, [])  # Khởi động lại không tải hóa đơn/profile.

    def test_vai_khac_khong_duoc_du_co_m2(self):
        for vai in ("XEM", "CFO", "BAN_HANG"):
            with self.subTest(vai=vai):
                self.conn.nguoi_dung["MO_PHONG_KE_TOAN"]["vai_tro"] = vai
                self.assertEqual(self.goi()[0], 403)
        self.assertEqual((self.tt.so_dung, self.tt.so_start), (0, 0))
        self.assertEqual(self.conn.nhat_ky, [])

    def test_ke_toan_thieu_module_m2_bi_chan(self):
        for q in self.conn.phan_quyen:
            if q["nguoi_dung_id"] == gia.U_KT:
                q["module"] = [m for m in q["module"] if m != "M2"]
        self.assertEqual(self.goi()[0], 403)
        self.assertEqual(self.tt.so_dung, 0)

    def test_phien_sai_va_danh_tinh_db_lech_bi_chan(self):
        self.assertEqual(self.goi(sid="sid-demo-het-han")[0], 400)
        self.conn.ai_ep = "MO_PHONG_XEM_A"
        self.assertEqual(self.goi()[0], 403)
        self.assertEqual(self.tt.so_dung, 0)

    def test_khong_nhan_pid_duong_dan_actor_tu_client_va_chi_post(self):
        for body in ({"pid": 1234}, {"path": "DEMO"}, {"actor": "CFO"}):
            self.assertIn(self.goi(body=body)[0], (400, 403))
        self.assertEqual(self.goi(post=False)[0], 404)
        self.assertEqual(self.tt.so_dung, 0)

    def test_bam_lap_va_mo_dong_thoi_khong_xep_hang_restart(self):
        for ten in ("khoi-dong-lai", "khoi-dong"):
            with self.subTest(lenh_dang_chay=ten):
                vao, tiep = threading.Event(), threading.Event()
                self.tt.san = False
                start = self.tt.start

                def treo():
                    vao.set()
                    if not tiep.wait(3):
                        raise AssertionError("Test không nhả khóa")
                    return start()

                results = []
                with patch.object(self.tt, "start", side_effect=treo):
                    t = threading.Thread(target=lambda: results.append(self.goi(ten=ten)))
                    t.start()
                    try:
                        self.assertTrue(vao.wait(3))
                        status, body = self.goi()
                        self.assertEqual((status, body["error"]), (409, "M2K_DANG_KHOI_DONG"))
                    finally:
                        tiep.set()
                        t.join(4)
                self.assertFalse(t.is_alive())
                self.assertEqual(results[0][0], 200)
        self.assertEqual(self.tt.so_start, 2)

    def test_dung_chua_xac_nhan_khong_spawn_va_ghi_that_bai(self):
        with patch.object(self.tt, "stop", return_value={"trang_thai": "DUNG_CHUA_XAC_NHAN"}):
            status, body = self.goi()
        self.assertEqual((status, body["error"]), (502, "M2_00B_DUNG_CHUA_XAC_NHAN"))
        self.assertEqual(self.tt.so_start, 0)
        self.assertEqual(self.ket_qua_nhat_ky()[-1]["ket_qua"], "THAT_BAI")
        self.assertFalse(mod._KHOI_DONG.locked())

    def test_witness_cu_khong_duoc_bo_qua(self):
        self.tt.chung_dung = {"ma": "JOB_CON_TIEN_TRINH"}
        self.assertEqual(self.goi()[0], 502)
        self.assertEqual((self.tt.so_dung, self.tt.so_start), (0, 0))

    def test_khoi_dong_loi_ghi_ma_khong_lo_bi_mat(self):
        with patch.object(self.tt, "start", side_effect=LoiTienTrinh("TEP_PIN_SAI", "DEMO_SECRET_PATH")):
            status, body = self.goi()
        self.assertEqual(status, 503)
        self.assertNotIn("DEMO_SECRET_PATH", repr(body) + repr(self.conn.nhat_ky))
        self.assertEqual(self.ket_qua_nhat_ky()[-1]["ma"], "M2_00B_TEP_PIN_SAI")

    def test_nhat_ky_loi_truoc_khong_dung_sau_khong_bao_thanh_cong(self):
        self.conn.loi_nhat_ky = True
        self.assertEqual(self.goi()[0], 503)
        self.assertEqual(self.tt.so_dung, 0)
        self.conn.loi_nhat_ky = False
        start = self.tt.start

        def start_roi_loi_log():
            kq = start()
            self.conn.loi_nhat_ky = True
            return kq

        with patch.object(self.tt, "start", side_effect=start_roi_loi_log):
            status, body = self.goi()
        self.assertEqual((status, body["error"]), (503, "M2_00B_NHAT_KY_LOI"))
        self.assertTrue(self.tt.san)  # Trạng thái đã đổi nhưng chưa ghi kết quả: trả lỗi trung thực.

    def test_doi_vai_trong_io_nhat_ky_van_dung_nguoi_yeu_cau(self):
        start = self.tt.start

        def doi_vai():
            self.app.dat_phien(gia.SID_KT, "MO_PHONG_XEM_A")
            return start()

        with patch.object(self.tt, "start", side_effect=doi_vai):
            self.assertEqual(self.goi()[0], 200)
        self.assertTrue(all(r["nguoi"] == "MO_PHONG_KE_TOAN" for r in self.conn.nhat_ky))

    def test_thu_hoi_quyen_khi_dang_dung_khong_spawn_moi(self):
        stop = self.tt.stop

        def thu_hoi():
            self.conn.nguoi_dung["MO_PHONG_KE_TOAN"]["vai_tro"] = "XEM"
            return stop()

        with patch.object(self.tt, "stop", side_effect=thu_hoi):
            self.assertEqual(self.goi()[0], 403)
        self.assertEqual(self.tt.so_start, 0)
        self.assertEqual(self.ket_qua_nhat_ky()[-1]["ket_qua"], "THAT_BAI")

    def test_hang_doi_treo_duoc_huy_truoc_restart_khong_tai_tiep(self):
        q = {"dang_chay": True, "dung": threading.Event(), "khoa_job": threading.RLock(),
             "muc": [{"trang_thai": s} for s in ("Xong", "Đang tải", "Chờ")]}
        self.dv._hang_doi = q
        self.assertEqual(self.goi()[0], 200)
        self.assertTrue(q["dung"].is_set())
        self.assertEqual([m["trang_thai"] for m in q["muc"]], ["Xong", "Đã hủy", "Đã hủy"])
        self.assertEqual((self.tt.so_dung, self.tt.so_start), (1, 1))
        self.assertEqual(self.node.so_start, 0)

    def test_hang_doi_dang_gui_lenh_khong_cho_khoa_hoac_dung_nham(self):
        khoa = threading.Lock()
        self.dv._hang_doi = {"dang_chay": True, "khoa_job": khoa}
        with khoa:
            self.assertEqual(self.goi()[0], 409)
        self.assertEqual(self.tt.so_dung, 0)
        self.assertEqual(self.conn.nhat_ky, [])

    def test_worker_hang_doi_that_dung_khong_chay_cong_ty_tiep(self):
        self.assertEqual(self.goi(ten="tai-tat-ca", body=dict(CHON))[0], 200)
        q = self.dv._hang_doi
        try:
            han = time.monotonic() + 3
            while not q["muc"][0]["run_handle"] and time.monotonic() < han:
                time.sleep(0.005)
            self.assertIsNotNone(q["muc"][0]["run_handle"])
            self.node.ngat = True
            self.assertEqual(self.goi()[0], 200)
        finally:
            q["dung"].set()
            han = time.monotonic() + 3
            while q["dang_chay"] and time.monotonic() < han:
                time.sleep(0.005)
        self.assertFalse(q["dang_chay"])
        self.assertEqual(self.node.so_start, 1)
        self.assertEqual([m["trang_thai"] for m in q["muc"]], ["Đã hủy", "Đã hủy"])

    def test_status_cap_quyen_va_phat_hien_treo_du_proc_con_song(self):
        status, body = self.goi(ten="", post=False)
        self.assertEqual(status, 200)
        self.assertTrue(body["duoc_khoi_dong_lai"])
        self.assertFalse(self.goi(sid=gia.SID_XA, ten="", post=False)[1]["duoc_khoi_dong_lai"])
        self.node.ngat = True
        self.assertTrue(self.goi(ten="", post=False)[1]["bo_tai"]["treo"])
        self.assertEqual(self.goi()[0], 200)  # Không RPC để kiểm quyền lúc Node treo.

    def test_chi_dung_job_so_huu_va_dung_truoc_spawn_ghim(self):
        log, procs, jobs = [], [], []
        ngoai = ProcGia([])

        class ProcTreo(ProcGia):
            def wait(proc, timeout=None):
                if proc.returncode is None:
                    raise subprocess.TimeoutExpired("node-demo", timeout)
                return proc.returncode

        class JobSoHuu(JobGia):
            def gan(job, proc):
                job.proc = proc
                super().gan(proc)

            def ket_thuc(job):
                super().ket_thuc()
                job.proc.returncode = 0

        def popen(argv, **kw):
            self.assertEqual(argv, [str(self.cfg.node_exe), str(self.cfg.server_js), "--owned"])
            self.assertIs(kw["shell"], False)
            log.append("spawn")
            p = ProcTreo(log)
            p.pid += len(procs)
            procs.append(p)
            return p

        def job_factory():
            j = JobSoHuu(log)
            jobs.append(j)
            return j

        def doc_dong(*_):
            return json.dumps({"kieu": KIEU_SAN_SANG, "protocol": PROTOCOL, "version": gia.PHIEN_BAN,
                               "port": 47002, "pid": procs[-1].pid, "instance_id": tt.instance_id}).encode("utf-8")

        tt = TienTrinhNode(self.cfg, popen=popen, job_factory=job_factory, doc_dong=doc_dong, khach_factory=KhachGia)
        tt.start()
        self.dv.tien_trinh = self.dv._tt = tt
        self.assertEqual(self.goi()[0], 200)
        self.assertEqual(len(procs), 2)
        self.assertEqual(procs[0].returncode, 0)
        self.assertIsNone(procs[1].returncode)
        self.assertIsNone(ngoai.returncode)
        self.assertEqual(ngoai.log, [])
        self.assertTrue(jobs[0].da_dong)
        self.assertLess(log.index("job.ket_thuc"), len(log) - 1 - log[::-1].index("spawn"))
        tt.stop()  # Chỉ dọn handle giả.


if __name__ == "__main__":
    unittest.main()
