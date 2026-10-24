"""M2-00B vòng đời owned Node — popen/Job/đọc bắt tay/khách là seam fake literal; KHÔNG spawn, KHÔNG Job Windows thật, KHÔNG mạng.

Trạng thái: AUTHORED_NOT_RUN. Phủ: khởi tạo không spawn, pin hash, argv/env/stdin cấu hình (capability chỉ stdin), Job gán TRƯỚC cấu hình,
bắt tay sai/trễ/quá hạn/thoát sớm/PID/cổng/phiên bản/kiểu lỗi, preflight, dừng sạch, dừng chưa xác nhận (witness UNKNOWN), Job còn worker.
Kèm kiểm `KhachNode` thật: header Host/capability, không query, SSE sai thứ tự/khác job/JSON hỏng/dòng lạ/quá lớn → mã dừng.
"""

from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from kho_tri_thuc.m2.tai_hoa_don import KhachNode, LoiKhach, LoiTienTrinh, TienTrinhNode
from kho_tri_thuc.m2.tai_hoa_don.tien_trinh import KIEU_CAU_HINH, KIEU_LOI, KIEU_SAN_SANG, PROTOCOL
from kho_tri_thuc.nguon.trich6_host import LoiHost

from test_m2_00b_tinh import PHIEN_BAN, tao_cau_hinh

PID = 4242
CONG = 47002
ENV_CHA = {"PATH": "C:\\demo\\bin", "SYSTEMROOT": "C:\\Windows", "TAX_PASSWORD": "DEMO-CANARY-TAX", "PGPASSWORD": "DEMO-CANARY-PG",
           "NODE_OPTIONS": "--require=evil", "HTTPS_PROXY": "http://demo-proxy"}


class _Stdin:
    def __init__(self, log):
        self.log, self.data, self.dong = log, b"", False

    def write(self, b):
        self.log.append("stdin.write")
        self.data += b

    def flush(self):
        pass

    def close(self):
        self.log.append("stdin.close")
        self.dong = True


class _Stdout:
    def close(self):
        pass


class ProcGia:
    def __init__(self, log, *, khong_chet=False, da_thoat=False):
        self.log, self.pid, self.khong_chet = log, PID, khong_chet
        self.returncode = 1 if da_thoat else None
        self.stdin, self.stdout = _Stdin(log), _Stdout()

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.log.append("wait")
        if self.khong_chet:
            raise subprocess.TimeoutExpired("node", timeout)
        self.returncode = 0
        return 0

    def kill(self):
        self.log.append("kill")


class JobGia:
    def __init__(self, log, *, worker=0, loi_gan=None):
        self.log, self.worker, self.loi_gan = log, worker, loi_gan
        self.da_dong = False

    def gan(self, proc):
        self.log.append("job.gan")
        if self.loi_gan:
            raise LoiHost(self.loi_gan, "DEMO")

    def ket_thuc(self):
        self.log.append("job.ket_thuc")

    def so_tien_trinh(self):
        return self.worker

    def dong(self):
        self.da_dong = True


class KhachGia:
    def __init__(self, port, cap, gh, *, loi=None, version=PHIEN_BAN):
        self.port, self.cap, self.loi, self.version = port, cap, loi, version

    def config(self):
        if self.loi:
            raise LoiKhach(self.loi, 401)
        return {"protocol": PROTOCOL, "version": self.version, "running": False}


class CoSoTienTrinh(unittest.TestCase):
    GIOI_HAN = {"cho_job_s": 0.1}

    def setUp(self):
        self._tam = tempfile.TemporaryDirectory(prefix="m2-00b-tt-", ignore_cleanup_errors=True)
        self.addCleanup(self._tam.cleanup)
        self.cfg = tao_cau_hinh(Path(self._tam.name).resolve() / "cfg", **self.GIOI_HAN)
        self.log = []
        self.popen_goi = []
        self.khach_goi = []

    def tao(self, *, hs=None, dong=None, proc_kw=None, job_kw=None, khach_kw=None, job_factory=None):
        proc = ProcGia(self.log, **(proc_kw or {}))
        job = JobGia(self.log, **(job_kw or {}))
        self.proc, self.job = proc, job

        def popen(argv, **kw):
            self.log.append("popen")
            self.popen_goi.append((argv, kw))
            return proc

        def doc_dong(stream, han):
            self.han_doc = han
            if dong is not None:
                return dong
            v = {"kieu": KIEU_SAN_SANG, "protocol": PROTOCOL, "version": PHIEN_BAN, "port": CONG, "pid": PID, "instance_id": tt.instance_id}
            v.update(hs or {})
            return (json.dumps(v) + "\n").encode("utf-8")

        def khach_factory(port, cap, gh):
            self.khach_goi.append((port, cap))
            return KhachGia(port, cap, gh, **(khach_kw or {}))

        tt = TienTrinhNode(self.cfg, popen=popen, job_factory=job_factory or (lambda: job), doc_dong=doc_dong, khach_factory=khach_factory,
                           env=dict(ENV_CHA))
        return tt

    def loi_start(self, tt, ma):
        with self.assertRaises(LoiTienTrinh) as e:
            tt.start()
        self.assertEqual(e.exception.ma, ma)
        self.assertFalse(tt.dang_chay())
        return e.exception


class M2BTienTrinh(CoSoTienTrinh):
    def test_b01_khoi_tao_khong_spawn(self):
        tt = self.tao()
        self.assertEqual(self.popen_goi, [])
        self.assertEqual(tt.trang_thai, "CHUA_KHOI_DONG")
        self.assertFalse(tt.suc_khoe()["san_sang"])
        with self.assertRaises(LoiTienTrinh) as e:
            tt.khach()
        self.assertEqual(e.exception.ma, "NODE_CHUA_SAN_SANG")
        self.assertEqual(tt.stop(), {"trang_thai": "CHUA_KHOI_DONG", "chung_dung": None})

    def test_b01_start_argv_env_job_truoc_cau_hinh(self):
        tt = self.tao()
        r = tt.start()
        argv, kw = self.popen_goi[0]
        self.assertEqual(argv, [str(self.cfg.node_exe), str(self.cfg.server_js), "--owned"])
        self.assertIs(kw["shell"], False)
        self.assertEqual(kw["env"], {"PATH": "C:\\demo\\bin", "SYSTEMROOT": "C:\\Windows"})
        self.assertEqual(self.log[:3], ["popen", "job.gan", "stdin.write"])
        cfg = json.loads(self.proc.stdin.data.decode("utf-8"))
        self.assertEqual(set(cfg), {"kieu", "protocol", "capability", "port", "instance_id", "roots", "limits"})
        self.assertEqual((cfg["kieu"], cfg["protocol"], cfg["instance_id"]), (KIEU_CAU_HINH, PROTOCOL, tt.instance_id))
        self.assertEqual(cfg["roots"], self.cfg.roots_node())
        cap = cfg["capability"]
        self.assertGreaterEqual(len(cap), 43)
        self.assertNotIn(cap, json.dumps([argv, kw["env"]]))
        self.assertEqual(self.khach_goi, [(CONG, cap)])
        self.assertEqual(r["trang_thai"], "SAN_SANG")
        for v in (json.dumps(r), repr(tt), json.dumps(tt.suc_khoe()), repr(self.cfg)):
            self.assertNotIn(cap, v)
        self.assertEqual(self.han_doc, self.cfg.gioi_han.khoi_dong_s)
        self.assertTrue(tt.dang_chay())
        self.assertEqual(self.loi_start_lai(tt), "DA_KHOI_DONG")

    def loi_start_lai(self, tt):
        with self.assertRaises(LoiTienTrinh) as e:
            tt.start()
        return e.exception.ma

    def test_b02_pin_sai_khong_spawn(self):
        self.cfg.node_exe.write_bytes(b"DEMO-NODE-DA-DOI")
        self.loi_start(self.tao(), "NODE_SHA_SAI")
        self.assertEqual(self.popen_goi, [])

    def test_b02_tep_7_sai_khong_spawn(self):
        (self.cfg.goc_7 / "src" / "job.js").write_bytes(b"// DEMO doi")
        self.loi_start(self.tao(), "TEP_PIN_SAI")
        self.assertEqual(self.popen_goi, [])

    def test_b02_job_khong_tao_duoc_khong_spawn(self):
        def hong():
            raise LoiHost("JOB_LOI", "DEMO")
        self.loi_start(self.tao(job_factory=hong), "JOB_LOI")
        self.assertEqual(self.popen_goi, [])

    def test_b02_gan_job_loi_khong_gui_cau_hinh(self):
        tt = self.tao(job_kw={"loi_gan": "JOB_GAN_LOI"})
        self.loi_start(tt, "JOB_GAN_LOI")
        self.assertNotIn("stdin.write", self.log)
        self.assertTrue(self.job.da_dong)

    def test_b02_bat_tay_sai_tung_truong(self):
        ca = [({"kieu": KIEU_LOI, "ma": "ADDRESS_IN_USE"}, "NODE_ADDRESS_IN_USE"),
              ({"kieu": KIEU_LOI, "ma": "DEPENDENCY_MISSING"}, "NODE_DEPENDENCY_MISSING"),
              ({"kieu": KIEU_LOI, "ma": "x/../y"}, "NODE_LOI"),
              ({"protocol": "khac/v1"}, "BAT_TAY_SAI"),
              ({"instance_id": "0" * 16}, "BAT_TAY_SAI"),
              ({"pid": PID + 1}, "BAT_TAY_PID_SAI"),
              ({"pid": str(PID)}, "BAT_TAY_PID_SAI"),
              ({"port": 0}, "BAT_TAY_CONG_SAI"),
              ({"port": 70000}, "BAT_TAY_CONG_SAI"),
              ({"version": "khac"}, "BAT_TAY_PHIEN_BAN_SAI")]
        for hs, ma in ca:
            with self.subTest(ma=ma, hs=hs):
                self.log.clear()
                tt = self.tao(hs=hs)
                self.loi_start(tt, ma)
                self.assertEqual(tt.trang_thai, "KHOI_DONG_LOI:" + ma)
                self.assertIn("stdin.close", self.log)
                self.assertTrue(self.job.da_dong)

    def test_b02_bat_tay_khong_json_tre_thoat_som(self):
        self.loi_start(self.tao(dong=b"not-json\n"), "BAT_TAY_SAI")
        self.loi_start(self.tao(dong=b""), "BAT_TAY_QUA_HAN")  # bắt tay đến sau hạn = không có dòng trong hạn
        self.loi_start(self.tao(dong=b"", proc_kw={"da_thoat": True}), "NODE_THOAT_SOM")

    def test_b02_preflight_sai(self):
        self.loi_start(self.tao(khach_kw={"loi": "CAPABILITY_INVALID"}), "SAN_SANG_LOI")
        self.loi_start(self.tao(khach_kw={"version": "khac"}), "SAN_SANG_SAI")

    def test_b02_khoi_dong_loi_va_don_chua_xac_nhan_giu_witness(self):
        tt = self.tao(hs={"pid": 1}, proc_kw={"khong_chet": True})
        self.loi_start(tt, "BAT_TAY_PID_SAI")
        self.assertEqual(tt.trang_thai, "KHOI_DONG_LOI:BAT_TAY_PID_SAI+DUNG_CHUA_XAC_NHAN")
        self.assertEqual(tt.chung_dung["ma"], "CHO_TERMINAL_QUA_HAN")
        self.assertIn("job.ket_thuc", self.log)
        self.assertNotIn("kill", self.log)  # có Job → chốt đúng Job, không kill rời

    def test_b08_dung_sach(self):
        tt = self.tao()
        tt.start()
        self.log.clear()
        self.assertEqual(tt.stop(), {"trang_thai": "DA_DUNG", "chung_dung": None})
        self.assertEqual(self.log[:2], ["stdin.close", "wait"])
        self.assertTrue(self.job.da_dong)
        self.assertFalse(tt.dang_chay())
        self.assertEqual(tt.stop(), {"trang_thai": "DA_DUNG", "chung_dung": None})

    def test_b08_dung_chua_xac_nhan_khong_bao_da_dung(self):
        tt = self.tao()
        tt.start()
        self.proc.khong_chet = True
        with self.assertRaises(LoiTienTrinh) as e:
            tt.stop()
        self.assertEqual((e.exception.ma, e.exception.pha), ("DUNG_CHUA_XAC_NHAN", "CHO_TERMINAL"))
        self.assertEqual(tt.trang_thai, "DUNG_CHUA_XAC_NHAN")
        self.assertEqual(tt.chung_dung["pid"], PID)
        self.assertEqual(tt.stop()["trang_thai"], "DUNG_CHUA_XAC_NHAN")  # không bịa DA_DUNG
        self.assertFalse(tt.dang_chay())

    def test_b08_job_con_worker_sau_khi_node_thoat(self):
        tt = self.tao(job_kw={"worker": 1})
        tt.start()
        with self.assertRaises(LoiTienTrinh) as e:
            tt.stop()
        self.assertEqual(e.exception.ma, "DUNG_CHUA_XAC_NHAN")
        self.assertEqual(tt.chung_dung["ma"], "JOB_CON_TIEN_TRINH")
        self.assertIn("job.ket_thuc", self.log)


class _HttpGhi:
    def __init__(self, ghi, phan_hoi):
        self.ghi, self.phan_hoi = ghi, phan_hoi

    def request(self, method, path, body=None, headers=None):
        self.ghi.append((method, path, dict(headers or {}), body))

    def getresponse(self):
        return self.phan_hoi

    def close(self):
        pass


class _Resp:
    def __init__(self, status, ct, data):
        self.status, self._ct, self._b = status, ct, io.BytesIO(data)

    def getheader(self, k, d=None):
        return self._ct if k.lower() == "content-type" else d

    def read(self, n=-1):
        return self._b.read(n)

    def readline(self, n=-1):
        return self._b.readline(n)


class M2BKhach(CoSoTienTrinh):
    CAP = "DEMOcapDEMOcapDEMOcapDEMOcapDEMOcapDEMOcap1"
    CTX = {"run": {"run_id": "20261023-093000"}}
    DG = "d" * 64

    def khach(self, resp):
        self.ghi = []
        return KhachNode(CONG, self.CAP, self.cfg.gioi_han, ket_noi=lambda host, port, timeout=None: _HttpGhi(self.ghi, resp))

    def test_b03_header_host_capability_khong_query(self):
        k = self.khach(_Resp(200, "application/json", json.dumps({"ok": True, "protocol": PROTOCOL, "version": PHIEN_BAN, "running": False}).encode()))
        self.assertEqual(k.config()["version"], PHIEN_BAN)
        method, path, hd, body = self.ghi[0]
        self.assertEqual((method, path, body), ("GET", "/api/config", None))
        self.assertEqual(hd["Host"], f"127.0.0.1:{CONG}")
        self.assertEqual(hd["X-Source7-M2-Cap"], self.CAP)
        self.assertNotIn(self.CAP, repr(k))
        k2 = self.khach(_Resp(401, "application/json", b'{"ok":false,"code":"CAPABILITY_INVALID"}'))
        with self.assertRaises(LoiKhach) as e:
            k2.config()
        self.assertEqual((e.exception.ma, e.exception.http_status), ("CAPABILITY_INVALID", 401))
        self.assertNotIn(self.CAP, repr(e.exception))
        k3 = self.khach(_Resp(200, "text/html", b"<html>"))
        with self.assertRaises(LoiKhach) as e:
            k3.config()
        self.assertEqual(e.exception.ma, "KHACH_CONTENT_TYPE")

    def _sse(self, text, con_hop_le=lambda: True):
        k = self.khach(_Resp(200, "text/event-stream; charset=utf-8", text.encode("utf-8")))
        return list(k.events(self.CTX, self.DG, 0, con_hop_le=con_hop_le))

    def _frame(self, seq, **kw):
        v = {"seq": seq, "type": "log", "payload": {}, "ts": None, "run_id": "20261023-093000", "context_digest": self.DG, **kw}
        return f"id: {seq}\ndata: {json.dumps(v)}\n\n"

    def test_b09_sse_hop_le_va_loi_co_ma(self):
        ok = self._sse(": open\n\n" + self._frame(1) + ": hb\n\n" + self._frame(2) + 'event: end\ndata: {"reason":"DONE"}\n\n')
        self.assertEqual([e.get("seq") for e in ok], [1, 2, None])
        self.assertEqual(ok[-1], {"ket_thuc": "DONE"})
        self.assertEqual(self._sse(self._frame(1)), [self._sse(self._frame(1))[0], {"ket_thuc": "EOF_KHONG_END"}])
        ca = [(self._frame(2) + self._frame(1), "SSE_THU_TU_SAI"), (self._frame(1, run_id="20261023-093001"), "SSE_KHAC_JOB"),
              (self._frame(1, context_digest="e" * 64), "SSE_KHAC_JOB"), ("data: {hong\n\n", "SSE_JSON_HONG"), ("retry: 1\n\n", "SSE_DONG_LA"),
              (self._frame(1, type="exec"), "SSE_DTO_SAI"), ("data: " + "x" * (self.cfg.gioi_han.dong_sse_bytes + 10) + "\n\n", "SSE_DONG_QUA_LON"),
              ("data: {}", "SSE_CAT_CUT")]
        for text, ma in ca:
            with self.subTest(ma=ma):
                with self.assertRaises(LoiKhach) as e:
                    self._sse(text)
                self.assertEqual(e.exception.ma, ma)

    def test_b09_sse_kiem_quyen_truoc_moi_chunk_va_nhip(self):
        dem = []

        def con():
            dem.append(1)
            return len(dem) < 3
        out = self._sse(": open\n\n" + self._frame(1) + self._frame(2), con_hop_le=con)
        self.assertEqual(out, [{"ket_thuc": "QUYEN_THAY_DOI"}])  # lần 1: trước đọc; lần 2: nhịp ': open'; lần 3: trước chunk 1 → dừng
        self.assertEqual(len(dem), 3)


if __name__ == "__main__":
    unittest.main()
