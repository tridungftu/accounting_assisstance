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
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

for _p in (Path(__file__).resolve().parent.parent, Path(__file__).resolve().parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from tests import test_m2_00b_tinh as gia
from tests.test_m2_00e_http import AppHttp, thong_so_tu
from tests.test_m2_tai_tat_ca import HandlerGia, KetNoiTen, BoTai, TienTrinh, CHON
from tests.test_m2_00b_tien_trinh import ProcGia, JobGia, KhachGia
from kho_tri_thuc.giao_dien import m2_tai_hoa_don as mod
from kho_tri_thuc.m2.tai_hoa_don import LoiTienTrinh, TienTrinhNode
from kho_tri_thuc.m2.tai_hoa_don.khach import LoiKhach
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
        self.assertEqual(self.node.goi, [("GET", "/api/config")] * 2)  # Chỉ kiểm phản hồi, không tải/profile.

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

    def test_co_m2_nhung_khong_co_ho_so_duoc_tai_bi_chan(self):
        for truong in ("nguon_duoc", "anh_xa"):
            with self.subTest(truong=truong):
                with patch.object(self.conn, truong, set() if truong == "nguon_duoc" else []):
                    self.assertEqual(self.goi()[0], 403)
                    self.assertFalse(self.goi(ten="", post=False)[1]["duoc_khoi_dong_lai"])
        self.assertEqual((self.tt.so_dung, self.tt.so_start), (0, 0))

    def test_phien_khac_dang_tai_phan_hoi_409_treo_cho_phep_va_ghi_run(self):
        sid_khac = "sid-demo-ke-toan-khac"
        self.app.dat_phien(sid_khac, "MO_PHONG_KE_TOAN")
        r = self.dv.start(sid_khac, gia.CoSoM2B.chon(cty=gia.CTY_B))
        self.conn.nhat_ky.clear()
        status, body = self.goi()
        self.assertEqual((status, body["error"]), (409, "M2K_DANG_TAI"))
        self.assertIn("Đợi tải xong", body["message"])
        self.assertEqual((self.tt.so_dung, self.tt.so_start), (0, 0))
        self.assertEqual(self.conn.nhat_ky, [])
        self.assertEqual(self.dv._dang_chay, r["run_handle"])
        self.node.ngat = True
        self.assertEqual(self.goi()[0], 200)
        self.assertIsNone(self.dv._dang_chay)
        self.assertTrue(all(log["lan_tai_bi_ngat"] == [r["run_handle"]] for log in self.ket_qua_nhat_ky()))

    def test_hang_doi_phien_khac_giua_hai_job_van_bi_chan(self):
        self.dv._hang_doi = q = {"ma": "hang-doi-demo-khac", "chu": ("phien-khac", "MO_PHONG_KE_TOAN"),
                                "dang_chay": True, "dung": threading.Event(), "khoa_job": threading.RLock(),
                                "muc": [{"trang_thai": "Chờ", "run_handle": None}]}
        status, body = self.goi()
        self.assertEqual((status, body["error"]), (409, "M2K_DANG_TAI"))
        self.assertFalse(q["dung"].is_set())
        self.assertEqual(q["muc"][0]["trang_thai"], "Chờ")
        self.assertEqual(self.conn.nhat_ky, [])
        self.assertEqual(self.tt.so_dung, 0)
        self.node.ngat = True
        self.assertEqual(self.goi()[0], 200)
        self.assertTrue(q["dung"].is_set())
        self.assertTrue(all(log["hang_doi_bi_ngat"] == q["ma"] for log in self.ket_qua_nhat_ky()))

    def test_phan_hoi_qua_han_cho_phep_nhung_tu_choi_rpc_khong_duoc_dung(self):
        self.dv.start(gia.SID_KT, gia.CoSoM2B.chon())
        khach = type(self.dv._khach())
        with patch.object(khach, "config", side_effect=mod.LoiKhach("CAPABILITY_INVALID", 401)):
            self.assertEqual(self.goi()[0], 502)
        self.assertEqual(self.tt.so_dung, 0)
        with patch.object(khach, "config", side_effect=mod.LoiKhach("KHACH_QUA_HAN")):
            self.assertEqual(self.goi()[0], 200)
        self.assertEqual(self.tt.so_dung, 1)

    def test_config_tien_trinh_that_chua_mo_khong_them_treo_false(self):
        with patch.dict(self.app.__dict__, {"_tai_hoa_don_dv": None, "_tai_hoa_don": None,
                        "demo_config": SimpleNamespace(tai_hoa_don=thong_so_tu(self.cfg))}):
            status, body = self.goi(ten="", post=False)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["bo_tai"], {"san_sang": False, "trang_thai": "CHUA_KHOI_DONG"})

    def test_config_cham_khong_giu_khoa_app_hay_giao_dich(self):
        # Lock thật: RLock có thể che lỗi giữ khóa trong cùng luồng.
        self.assertIs(type(self.app.mutation_lock), type(threading.Lock()))
        for co_hang_doi in (False, True):
            with self.subTest(hang_doi=co_hang_doi):
                self.dv._hang_doi = ({"dang_chay": True, "dung": threading.Event(),
                                      "khoa_job": threading.Lock(), "muc": []} if co_hang_doi else None)
                vao, tiep = threading.Event(), threading.Event()
                results, loi = [], []

                def config_cham():
                    self.assertEqual(self.conn._tx, [])
                    vao.set()
                    if not tiep.wait(3):
                        raise AssertionError("Test không nhả RPC config")
                    raise LoiKhach("KHACH_QUA_HAN")

                def khoi_dong_lai():
                    try:
                        results.append(self.goi())
                    except Exception as exc:
                        loi.append(exc)

                with patch.object(self.dv, "_khach", return_value=SimpleNamespace(config=config_cham)):
                    t = threading.Thread(target=khoi_dong_lai, daemon=True)
                    t.start()
                    try:
                        self.assertTrue(vao.wait(3), loi)
                        lay_duoc = self.app.mutation_lock.acquire(blocking=False)
                        if lay_duoc:
                            self.app.mutation_lock.release()
                        self.assertTrue(lay_duoc, "config chậm đang chặn mutation_lock")
                        self.assertEqual(self.conn.nhat_ky, [])
                    finally:
                        tiep.set()
                        t.join(4)
                self.assertFalse(t.is_alive())
                self.assertEqual(loi, [])
                self.assertEqual(results[0][0], 200, results)
                self.conn.nhat_ky.clear()

    def test_kiem_lai_phien_va_quyen_sau_config_truoc_khi_dung(self):
        for doi in ("phien", "quyen", "danh_tinh"):
            with self.subTest(doi=doi):
                def config():
                    if doi == "phien":
                        self.app.dat_phien(gia.SID_KT, "MO_PHONG_XEM_A")
                    elif doi == "quyen":
                        self.conn.nguoi_dung["MO_PHONG_KE_TOAN"]["vai_tro"] = "XEM"
                    else:
                        self.conn.nguoi_dung["MO_PHONG_KE_TOAN"]["id"] = gia.U_XA
                    raise LoiKhach("KHACH_QUA_HAN")

                with patch.object(self.dv, "_khach", return_value=SimpleNamespace(config=config)):
                    self.assertIn(self.goi()[0], (403, 409))
                self.assertEqual((self.tt.so_dung, self.tt.so_start), (0, 0))
                self.assertEqual(self.conn.nhat_ky, [])
                self.app.dat_phien(gia.SID_KT, "MO_PHONG_KE_TOAN")
                self.conn.nguoi_dung["MO_PHONG_KE_TOAN"].update(vai_tro="KE_TOAN", id=gia.U_KT)

    def test_chi_qua_han_va_mat_ket_noi_duoc_coi_la_treo(self):
        for ma in ("KHACH_QUA_HAN", "KHACH_KHONG_KET_NOI", "KHACH_TU_CHOI", "KHACH_DTO_SAI", "KHACH_CONTENT_TYPE"):
            with self.subTest(ma=ma):
                with patch.object(self.tt, "khach", side_effect=LoiKhach(ma)):
                    status, body = self.goi(ten="", post=False)
                    self.assertEqual(status, 200, body)
                    self.assertTrue(all(m["ly_do"] == "NODE_" + ma for m in body["muc"]))
                    if ma in ("KHACH_QUA_HAN", "KHACH_KHONG_KET_NOI"):
                        self.assertIs(body["bo_tai"]["treo"], True)
                        self.assertEqual(self.goi()[0], 200)
                    else:
                        # Không điều kiện nào để JS hiện nút khởi động lại.
                        self.assertEqual(body["bo_tai"], {"san_sang": True, "trang_thai": None})
                        status, loi = self.goi()
                        self.assertEqual((status, loi["error"]), (502, "M2_00B_" + ma))
                        self.assertEqual(loi["message"], "Chưa xác nhận được trạng thái bộ tải. Kiểm tra rồi thử lại.")
                self.conn.nhat_ky.clear()

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
        self.node.ngat = True
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
        self.assertNotIn("treo", body["bo_tai"])
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
