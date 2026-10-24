"""CRM-41-01-06 — host engine #6 DEMO do central sở hữu. CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN_CODE_ONLY).

Phân loại rõ:
- `HostDonViTests`: ĐƠN VỊ thuần (không spawn, không mạng): argv/env con không chứa token/bí mật; factory client theo app không rơi về biến môi
  trường ở chế độ quản lý; LocalApp constructor/serve tĩnh.
- `HandlerSoHuuTests`: HTTP THẬT trong tiến trình (loopback, cổng 0) nhưng Handler GỐC và `dv` là ĐỐI TƯỢNG GIẢ — chứng minh cổng auth/route
  của lớp bọc (token, Host/Origin/X-HD, /api/tat, `{}` create/chay, list, download) đứng TRƯỚC handler gốc; KHÔNG chứng minh nguồn thật.
- 06A `test_06a_*` trong `HostDonViTests`: quy tắc guard/chứng cứ hook/entry con thiếu guard — MOCK (ghi rõ trong từng ca); riêng
  `test_06a_guard_that_cua_tien_trinh_kiem` là THỰC trên tiến trình test (skip nếu runtime không bật cờ — không phải PASS).
- 06A `StopXacNhanTests`: MOCK Popen/Job tiêm lỗi (wait cuối quá hạn, Job không rỗng, kết thúc/ truy vấn lỗi) — không false-success.
- `VongDoiThatTests`: tiến trình con THẬT + mã nguồn #6 THẬT (chỉ đọc) trên DataRoot DEMO tạm; chỉ Windows và khi có nguồn tại vị trí host đã
  chốt — thiếu thì skip có lý do (skip KHÔNG phải PASS). Không dùng dữ liệu/cấu hình/khóa thật của người dùng; không cổng 8600/64900.
"""

from __future__ import annotations

import http.client
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from kho_tri_thuc.nguon import trich6_host as H
from kho_tri_thuc.nguon import trich_chung_6 as T6

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "kho_tri_thuc"
TOKEN = "t" * 43


class HostDonViTests(unittest.TestCase):
    def test_argv_env_con_khong_bi_mat(self):
        argv = H.lenh_con(sys.executable)
        self.assertEqual(argv[1:], ["-X", "utf8", "-m", "kho_tri_thuc.nguon.trich6_host", "--child"])
        goc = {"PATH": "p", "SYSTEMROOT": "C:\\Windows", "PYTHONPATH": "guard", "PGPASSWORD": "x", "ANTHROPIC_API_KEY": "x", "OPENAI_API_KEY": "x",
               "KHO_TRICH6_URL": "http://127.0.0.1:1", "HD_DU_LIEU": "D:/that", "AWS_SECRET_ACCESS_KEY": "x", "KTT_DSN": "postgres://x"}
        env = H.env_con(goc)
        self.assertEqual(set(env), {"PATH", "SYSTEMROOT", "PYTHONPATH", "PYTHONUTF8", "PYTHONIOENCODING", "PYTHONDONTWRITEBYTECODE"})
        self.assertEqual(env["PYTHONPATH"], str(H.SRC_CENTRAL) + os.pathsep + "guard")  # runtime/guard giữ nguyên, thêm src central
        self.assertEqual(env["PYTHONDONTWRITEBYTECODE"], "1")

    def test_06a_env_giu_hai_duong_guard(self):
        """06A — whitelist giữ PYTHONUSERBASE + CODEX_NO_DELETE_FILES (cùng PYTHONPATH runtime) và VẪN lọc bí mật/HD_* của parent."""
        goc = {"PATH": "p", "PYTHONPATH": "guard;deps", "PYTHONUSERBASE": "C:\\ub", "CODEX_NO_DELETE_FILES": "1", "PGPASSWORD": "x", "PGSERVICEFILE": "x",
               "KTT_DSN": "postgres://x", "ANTHROPIC_API_KEY": "x", "AZURE_CLIENT_SECRET": "x", "KHO_TRICH6_URL": "http://127.0.0.1:1", "HD_CSDL": "D:/that.db"}
        env = H.env_con(goc)
        self.assertEqual(set(env), {"PATH", "PYTHONPATH", "PYTHONUSERBASE", "CODEX_NO_DELETE_FILES", "PYTHONUTF8", "PYTHONIOENCODING",
                                    "PYTHONDONTWRITEBYTECODE"})
        self.assertEqual((env["PYTHONUSERBASE"], env["CODEX_NO_DELETE_FILES"]), ("C:\\ub", "1"))
        self.assertTrue(env["PYTHONPATH"].endswith(os.pathsep + "guard;deps"))

    def test_06a_quy_tac_guard_mock(self):
        """MOCK (dict chứng cứ): đủ module/SHA A517/cờ/hook/bytecode tắt mới đạt; thiếu từng điều → mã riêng."""
        # 06B: chứng cứ đạt phải có ĐỦ ba hook bắt buộc (guard A517 cài trực tiếp os.unlink/os.remove/shutil.rmtree)
        tot = {"module": True, "sha256": H.GUARD_SHA256, "flag": True, "hooks": ["os.remove", "os.unlink", "shutil.rmtree"], "bytecode_tat": True}
        self.assertIsNone(H.guard_hop_le(tot))
        self.assertIsNone(H.guard_hop_le({**tot, "hooks": tot["hooks"] + ["os.rename"]}))   # thêm hook trong HAM_XOA vẫn đạt; không đòi đủ 13
        for sua, ma in (({"module": False}, "GUARD_KHONG_NAP"), ({"sha256": "0" * 64}, "GUARD_SHA_SAI"), ({"sha256": None}, "GUARD_SHA_SAI"),
                        ({"flag": False}, "GUARD_CO_TAT"), ({"hooks": []}, "GUARD_KHONG_HOOK"), ({"hooks": ["os.chmod"]}, "GUARD_KHONG_HOOK"),
                        ({"hooks": tot["hooks"] + ["os.chmod"]}, "GUARD_KHONG_HOOK"), ({"hooks": "os.remove"}, "GUARD_KHONG_HOOK"),
                        ({"bytecode_tat": False}, "GUARD_BYTECODE_BAT")):
            self.assertEqual(H.guard_hop_le({**tot, **sua}), ma, sua)
        for thieu in (["os.remove"], ["os.unlink"], ["shutil.rmtree"], ["os.remove", "shutil.rmtree"], ["os.unlink", "shutil.rmtree"],
                      ["os.remove", "os.unlink"], ["os.remove", "shutil.rmtree", "os.rename"]):   # một/hai hook → KHÔNG đạt
            self.assertEqual(H.guard_hop_le({**tot, "hooks": thieu}), "GUARD_KHONG_HOOK", thieu)
        self.assertEqual(H.guard_hop_le(None), "GUARD_KHONG_NAP")

    def test_06b_cha_thieu_hook_khong_spawn_mock(self):
        """MOCK: nguồn tạm có hình dạng hợp lệ nhưng chứng cứ guard của CHA thiếu một hook → LoiHost GUARD_KHONG_HOOK, KHÔNG spawn, không mkdir."""
        nguon = Path(tempfile.mkdtemp(prefix="ktt_t6h_ng06b_"))
        (nguon / "may_chu").mkdir()
        (nguon / "may_chu" / "server.py").write_text("# nguồn DEMO giả: không được chạy\n", encoding="utf-8")
        (nguon / "trich_xuat").mkdir()
        dr = Path(tempfile.mkdtemp(prefix="ktt_t6h_dr06b_")) / "data"
        cc = {"module": True, "sha256": H.GUARD_SHA256, "flag": True, "hooks": ["os.remove", "shutil.rmtree"], "bytecode_tat": True}
        h = H.Trich6Host(dr, nguon)
        with mock.patch.object(H, "chung_cu_guard", lambda: cc), \
                mock.patch.object(subprocess, "Popen", side_effect=AssertionError("không được spawn khi guard cha thiếu hook")):
            with self.assertRaises(H.LoiHost) as cm:
                h.start()
        self.assertEqual(cm.exception.ma, "GUARD_KHONG_HOOK")
        self.assertFalse(dr.exists())
        self.assertEqual(h.suc_khoe()["ly_do"], "GUARD_KHONG_HOOK")

    def test_06a_chung_cu_guard_doc_hook_that_mock(self):
        """MOCK có kiểm soát: module guard GIẢ trong sys.modules (tệp tạm) + os.remove tạm thay bằng hàm định nghĩa TRONG tệp đó → hook được nhận
        đúng tên; SHA khác A517 → GUARD_SHA_SAI (không tin tên module). Hàm thay thế không xóa gì; os.remove khôi phục khi ra khỏi patch."""
        d = Path(tempfile.mkdtemp(prefix="ktt_t6h_gm_"))
        tep = d / "guard_gia.py"
        tep.write_text("def remove(*a, **k):\n    raise PermissionError('guard giả: không xóa')\n", encoding="utf-8")
        ns = {}
        exec(compile(tep.read_text(encoding="utf-8"), str(tep), "exec"), ns)
        gia = SimpleNamespace(__file__=str(tep))
        with mock.patch.dict(sys.modules, {H.GUARD_MODULE: gia}), mock.patch.object(os, "remove", ns["remove"]), \
                mock.patch.dict(os.environ, {"CODEX_NO_DELETE_FILES": "1"}):
            cc = H.chung_cu_guard()
        self.assertEqual((cc["module"], cc["flag"]), (True, True))
        self.assertIn("os.remove", cc["hooks"])
        self.assertEqual(H.guard_hop_le(cc), "GUARD_SHA_SAI")
        self.assertNotIn(str(d), json.dumps(cc))                                  # không lộ đường dẫn

    def test_06a_con_thieu_guard_khong_mo_nguon_mock(self):
        """MOCK trong tiến trình: entry con với chứng cứ guard thiếu/sai → mã GUARD_* trên kênh bắt tay, return 4; ZERO mkdir DataRoot, ZERO đặt HD_*,
        ZERO import may_chu/trich_xuat, không server."""
        import builtins
        import io
        goc_import = builtins.__import__
        for cc, ma in (({"module": False, "sha256": None, "flag": False, "hooks": [], "bytecode_tat": True}, "GUARD_KHONG_NAP"),
                       ({"module": True, "sha256": "0" * 64, "flag": True, "hooks": ["os.remove"], "bytecode_tat": True}, "GUARD_SHA_SAI"),
                       ({"module": True, "sha256": H.GUARD_SHA256, "flag": True, "hooks": [], "bytecode_tat": True}, "GUARD_KHONG_HOOK"),
                       ({"module": True, "sha256": H.GUARD_SHA256, "flag": True, "hooks": ["os.remove", "os.unlink"], "bytecode_tat": True},
                        "GUARD_KHONG_HOOK")):   # 06B: thiếu shutil.rmtree → con từ chối trước mkdir/HD_*/import nguồn
            dr = Path(tempfile.mkdtemp(prefix="ktt_t6h_ng_"))
            nhap = []

            def theo_doi(name, *a, **k):
                if name.split(".")[0] in ("may_chu", "trich_xuat", "master_hd"):
                    nhap.append(name)
                return goc_import(name, *a, **k)
            cfg = {"kieu": H.KIEU_CAU_HINH, "token": TOKEN, "nguon": str(dr / "khong_duoc_mo"), "du_lieu": str(dr / "data"), "instance_id": "i1"}
            kenh = io.StringIO()
            hd_truoc = {k: v for k, v in os.environ.items() if k.upper().startswith("HD_")}
            with mock.patch.object(H, "chung_cu_guard", lambda: cc), mock.patch.object(builtins, "__import__", theo_doi):
                rc = H._con(stdin=io.BytesIO((json.dumps(cfg) + "\n").encode()), kenh=kenh)
            self.assertEqual((rc, json.loads(kenh.getvalue())), (4, {"kieu": H.KIEU_LOI, "ma": ma}))
            self.assertEqual(nhap, [])
            self.assertEqual(list(dr.iterdir()), [])                                # không mkdir
            self.assertEqual({k: v for k, v in os.environ.items() if k.upper().startswith("HD_")}, hd_truoc)
            self.assertNotIn(str(dr), sys.path)

    def test_06a_guard_that_cua_tien_trinh_kiem(self):
        """THỰC (tiến trình đang chạy test): nếu runtime bật cờ giữ tệp thì guard A517 phải đạt đủ quy tắc. Không bật cờ → skip (KHÔNG phải PASS)."""
        if not H._bat(os.environ.get("CODEX_NO_DELETE_FILES")):
            self.skipTest("runtime test không bật CODEX_NO_DELETE_FILES — skip, không phải PASS")
        cc = H.chung_cu_guard()
        self.assertIsNone(H.guard_hop_le(cc), cc)
        self.assertTrue(H.HOOK_BAT_BUOC <= set(cc["hooks"]), cc["hooks"])
        # 06B: KHÔNG đòi sitecustomize/usercustomize — guard có thể nạp từ khởi động qua `.pth` của user site; test không import guard bù
        # (chung_cu_guard chỉ đọc sys.modules).

    def test_khoi_tao_host_khong_spawn(self):
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("không được spawn khi khởi tạo")):
            h = H.Trich6Host(Path(tempfile.mkdtemp(prefix="ktt_t6h_init_")), Path(tempfile.mkdtemp()))
        self.assertEqual(h.suc_khoe(), {"quan_ly": True, "instance": h.instance_id, "san_sang": False, "ly_do": "CHUA_KHOI_DONG"})
        self.assertNotIn("token", repr(h).lower())
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("không được spawn khi thiếu nguồn")):
            with self.assertRaises(H.LoiHost) as cm:
                h.start()   # nguồn tạm không có may_chu/server.py → lỗi rõ, không spawn
        self.assertEqual(cm.exception.ma, "NGUON_KHONG_CO")

    def test_factory_client_theo_app_khong_fallback_moi_truong(self):
        from kho_tri_thuc.giao_dien.server import LocalApp
        goc = Path(tempfile.mkdtemp(prefix="ktt_t6h_fac_"))
        with mock.patch.dict(os.environ, {T6.ENV_URL: "http://127.0.0.1:18600"}):
            app = SimpleNamespace(trich6_quan_ly=True, trich6_host=None)
            self.assertFalse(LocalApp.trich6_client(app, goc).san_sang)          # quản lý, chưa có host → NOT_READY, không lấy URL môi trường
            chet = H.Trich6Host(goc, goc)                                         # host chưa/không chạy → client NOT_READY
            app = SimpleNamespace(trich6_quan_ly=True, trich6_host=chet)
            self.assertFalse(LocalApp.trich6_client(app, goc).san_sang)
            app = SimpleNamespace(trich6_quan_ly=False, trich6_host=None)         # fixture tường minh không sở hữu host: seam cũ
            self.assertTrue(LocalApp.trich6_client(app, goc).san_sang)
        self.assertEqual(LocalApp.trich6_suc_khoe(SimpleNamespace(trich6_quan_ly=False)), {"quan_ly": False})

    def test_tinh_constructor_serve_consumer(self):
        sv = (SRC / "giao_dien" / "server.py").read_text(encoding="utf-8")
        init = sv[sv.index("    def __init__(self, config_path, root):"):sv.index("    def state(self):")]
        self.assertNotIn("Trich6Host", init)                                     # constructor không spawn
        s = sv[sv.index("def serve("):sv.index("def main(")]
        self.assertLess(s.index("app.trich6_host, app.trich6_quan_ly = host, True"), s.index("_mo_trich6"))  # quản lý TRƯỚC spawn
        self.assertIn("if not app.is_that:", s)
        self.assertIn("host.stop()", s[s.index("finally:"):])
        self.assertIn("self.trich6_client(self.root / \"crm-k2\")", sv)
        m4 = (SRC / "giao_dien" / "m4.py").read_text(encoding="utf-8")
        self.assertIn("app.trich6_client(svc.root)", m4)
        self.assertNotIn("Trich6Client(goc=svc.root)", m4)
        ps = (ROOT / "start-web.ps1").read_text(encoding="utf-8")
        self.assertIn("Assert-KttListener $kttHealth", ps)
        self.assertIn("Wait-KttTrich6", ps)
        self.assertNotIn("KHO_TRICH6_URL", ps)                                   # không cấp URL/token qua môi trường


# ------------------------------------------------------------------ L0-7: nạp sẵn thư viện nặng ở LUỒNG CHÍNH của tiến trình con (numpy treo ở luồng phụ)
class NapSanThuVienTests(unittest.TestCase):
    """Lỗi gốc: lệnh trích chạy ở luồng worker → `import openpyxl` → `import numpy` lần đầu ở luồng phụ khi luồng chính đang `serve_forever` → kẹt.
    Sửa: `_con` gọi `nap_san_thu_vien()` ở luồng chính TRƯỚC khi mở luồng phục vụ. MOCK trong tiến trình (không spawn, nguồn #6 là gói giả)."""

    def test_nap_san_khong_chan_khi_thieu_hoac_loi(self):
        import importlib
        log = []
        thuc = importlib.import_module

        def gia(ten, *a, **k):
            if ten == "ktt_mo_dun_loi":
                raise RuntimeError("hỏng khi nạp")
            return thuc(ten, *a, **k)
        with mock.patch.object(importlib, "import_module", gia):
            kq = H.nap_san_thu_vien(("ktt_mo_dun_khong_ton_tai", "ktt_mo_dun_loi", "json"), ghi_log=log.append)
        self.assertEqual(kq, {"ktt_mo_dun_khong_ton_tai": "khong_co", "ktt_mo_dun_loi": "loi", "json": "ok"})   # không ném lỗi, đi tiếp mô-đun sau
        self.assertEqual(len(log), 2)
        self.assertIn("ktt_mo_dun_khong_ton_tai", log[0])
        self.assertIn("RuntimeError", log[1])
        self.assertNotIn("hỏng khi nạp", " ".join(log))                              # chỉ ghi loại lỗi, không nội dung/đường dẫn

    def test_danh_sach_mac_dinh_co_openpyxl_va_numpy(self):
        self.assertIn("openpyxl", H.THU_VIEN_NAP_SAN)
        self.assertLess(H.THU_VIEN_NAP_SAN.index("numpy"), H.THU_VIEN_NAP_SAN.index("openpyxl"))   # numpy trước, tường minh
        kq = H.nap_san_thu_vien(("openpyxl",), ghi_log=lambda m: None)
        self.assertEqual(kq, {"openpyxl": "ok"})
        self.assertIn("openpyxl", sys.modules)

    def test_con_nap_san_o_luong_chinh_truoc_serve_forever(self):
        import io
        sk = []                                  # (sự kiện, id luồng)
        goc = Path(tempfile.mkdtemp(prefix="ktt_t6h_ns_"))
        nguon = goc / "nguon_gia"
        (nguon / "may_chu").mkdir(parents=True)
        (nguon / "may_chu" / "__init__.py").write_text("", encoding="utf-8")
        (nguon / "may_chu" / "dich_vu.py").write_text(
            "from types import SimpleNamespace\n"
            "QLV = SimpleNamespace(dang_chay=lambda: False)\n"
            "def _implementation():\n    return {'sha256': '0' * 64}\n", encoding="utf-8")
        (nguon / "may_chu" / "server.py").write_text("def tao_may_chu(cong):\n    return __import__('ktt_t6h_srv_gia').SRV\n", encoding="utf-8")

        class _Srv:
            RequestHandlerClass = object
            server_address = ("127.0.0.1", 0)

            def serve_forever(self, poll_interval=0.5):
                sk.append(("serve_forever", threading.get_ident()))

            def shutdown(self):
                pass

            def server_close(self):
                pass
        srv_mod = type(sys)("ktt_t6h_srv_gia")
        srv_mod.SRV = _Srv()
        cfg = {"kieu": H.KIEU_CAU_HINH, "token": TOKEN, "nguon": str(nguon), "du_lieu": str(goc / "data"), "instance_id": "i1"}
        cc_ok = {"module": True, "sha256": H.GUARD_SHA256, "flag": True, "hooks": sorted(H.HOOK_BAT_BUOC), "bytecode_tat": True}
        kenh = io.StringIO()
        luu_path, luu_bytecode = list(sys.path), sys.dont_write_bytecode

        def la_may_chu(k):
            return k == "may_chu" or k.startswith("may_chu.")
        luu_mod = {k: v for k, v in sys.modules.items() if la_may_chu(k)}
        for k in luu_mod:
            sys.modules.pop(k, None)
        try:
            with mock.patch.dict(os.environ), mock.patch.dict(sys.modules, {"ktt_t6h_srv_gia": srv_mod}),                     mock.patch.object(H, "chung_cu_guard", lambda: cc_ok),                     mock.patch.object(H, "lop_handler_so_huu", lambda Goc, dv, token: Goc),                     mock.patch.object(H, "nap_san_thu_vien", lambda *a, **k: sk.append(("nap_san", threading.get_ident()))):
                rc = H._con(stdin=io.BytesIO((json.dumps(cfg) + "\n").encode()), kenh=kenh)
        finally:
            sys.path[:] = luu_path
            sys.dont_write_bytecode = luu_bytecode
            for k in [k for k in sys.modules if la_may_chu(k)]:
                sys.modules.pop(k, None)
            sys.modules.update(luu_mod)
        self.assertEqual(rc, 0, kenh.getvalue())
        self.assertEqual(json.loads(kenh.getvalue().splitlines()[0])["kieu"], H.KIEU_SAN_SANG)
        ten = [e for e, _ in sk]
        self.assertEqual(ten, ["nap_san", "serve_forever"])                           # nạp sẵn TRƯỚC khi phục vụ
        self.assertEqual(sk[0][1], threading.get_ident())                             # nạp ở luồng gọi `_con` (luồng chính của tiến trình con)
        self.assertNotEqual(sk[1][1], threading.get_ident())                          # còn phục vụ chạy ở luồng phụ


# ------------------------------------------------------------------ 06A: dừng có xác nhận — MOCK tiến trình/Job (fault injection)
class _ProcGia:
    def __init__(self, thoat_sau_eof=True, thoat_sau_kill=True):
        self.pid, self.thoat, self.eof, self.kill_goi = 4242, False, False, 0
        self.thoat_sau_eof, self.thoat_sau_kill = thoat_sau_eof, thoat_sau_kill
        self.stdin = SimpleNamespace(close=self._dong_vao)
        self.stdout = SimpleNamespace(close=lambda: None)

    def _dong_vao(self):
        self.eof = True
        self.thoat = self.thoat or self.thoat_sau_eof

    def wait(self, t=None):
        if not self.thoat:
            raise subprocess.TimeoutExpired("con", t)
        return 0

    def poll(self):
        return 0 if self.thoat else None

    def kill(self):
        self.kill_goi += 1
        self.thoat = self.thoat_sau_kill


class _JobGia:
    def __init__(self, dem=(0,), proc=None, ket_thuc_loi=False, truy_van_loi=False, ket_thuc_lam_rong=True):
        self.dem, self.proc, self.ket_thuc_loi, self.truy_van_loi, self.ket_thuc_lam_rong = list(dem), proc, ket_thuc_loi, truy_van_loi, ket_thuc_lam_rong
        self.ket_thuc_goi = self.dong_goi = 0

    def ket_thuc(self):
        self.ket_thuc_goi += 1
        if self.ket_thuc_loi:
            raise H.LoiHost("JOB_KET_THUC_LOI", "giả lập")
        if self.proc is not None:
            self.proc.thoat = True
        if self.ket_thuc_lam_rong:
            self.dem = [0]

    def so_tien_trinh(self):
        if self.truy_van_loi:
            raise H.LoiHost("JOB_TRUY_VAN_LOI", "giả lập")
        return self.dem.pop(0) if len(self.dem) > 1 else self.dem[0]

    def dong(self):
        self.dong_goi += 1


class StopXacNhanTests(unittest.TestCase):
    """MOCK: Popen/Job giả để tiêm lỗi; chứng minh không false-success, finally đóng đúng handle Job, cleanup hữu hạn."""

    def host(self, proc, job):
        h = H.Trich6Host(Path(tempfile.mkdtemp(prefix="ktt_t6h_stop_")), Path("."), cho_dung=0.05)
        h.cho_job = 0.2
        h._proc, h._job, h._token, h._port, h._pid, h._trang_thai = proc, job, TOKEN, 1, 999, "SAN_SANG"
        return h

    def test_duong_tinh_eof_va_worker_con_song(self):
        p = _ProcGia()
        h = self.host(p, _JobGia(dem=(0,)))
        j = h._job
        h.stop()
        self.assertEqual((h._trang_thai, j.ket_thuc_goi, j.dong_goi, p.eof), ("DA_DUNG", 0, 1, True))
        p = _ProcGia()
        j = _JobGia(dem=(1,))                                                      # con đã thoát nhưng worker lồng còn active
        h = self.host(p, j)
        h.stop()
        self.assertEqual((h._trang_thai, j.ket_thuc_goi, j.dong_goi), ("DA_DUNG", 1, 1))   # chốt đúng Job rồi xác nhận rỗng
        self.assertNotIn("chung_dung", h.suc_khoe())

    def test_khong_false_success(self):
        ca = [("wait_cuoi_qua_han", _ProcGia(thoat_sau_eof=False), dict(ket_thuc_lam_rong=False), "CHO_TERMINAL"),
              ("job_khong_rong", _ProcGia(), dict(dem=(2,), ket_thuc_lam_rong=False), "CHO_JOB_RONG"),
              ("ket_thuc_loi", _ProcGia(thoat_sau_eof=False), dict(ket_thuc_loi=True), "KET_THUC_SAU_GRACE"),
              ("truy_van_loi", _ProcGia(), dict(truy_van_loi=True), "KIEM_JOB")]
        for ten, p, kw, pha in ca:
            j = _JobGia(**kw)
            h = self.host(p, j)
            with self.assertRaises(H.LoiHost, msg=ten) as cm:
                h.stop()
            self.assertEqual(cm.exception.ma, "DUNG_CHUA_XAC_NHAN", ten)
            self.assertEqual(h._trang_thai, "DUNG_CHUA_XAC_NHAN", ten)          # KHÔNG DA_DUNG
            self.assertEqual(j.dong_goi, 1, ten)                                  # finally vẫn đóng đúng handle Job sở hữu
            sk = h.suc_khoe()
            self.assertEqual((sk["san_sang"], sk["ly_do"]), (False, "DUNG_CHUA_XAC_NHAN"), ten)
            self.assertEqual((sk["chung_dung"]["popen_pid"], sk["chung_dung"]["pid"], sk["chung_dung"]["pha"]), (4242, 999, pha), ten)
            self.assertNotIn(TOKEN, json.dumps(sk))
            self.assertFalse(h.client(Path(".")).san_sang, ten)                   # không phục vụ client sau dừng chưa rõ

    def test_khong_job_kill_dung_popen(self):
        """Không có Job (ngoài Windows): quá grace → kill ĐÚNG Popen; kill không làm chết → chưa xác nhận."""
        p = _ProcGia(thoat_sau_eof=False)
        h = self.host(p, None)
        h.stop()
        self.assertEqual((h._trang_thai, p.kill_goi), ("DA_DUNG", 1))
        p = _ProcGia(thoat_sau_eof=False, thoat_sau_kill=False)
        h = self.host(p, None)
        with self.assertRaises(H.LoiHost):
            h.stop()
        self.assertEqual((h._trang_thai, p.kill_goi), ("DUNG_CHUA_XAC_NHAN", 1))


# ------------------------------------------------------------------ Handler gốc GIẢ (ghi lại lần tới được) để kiểm cổng của lớp bọc
class _LoiGia(Exception):
    def __init__(self, ma, thong_bao, chi_tiet=None):
        super().__init__(thong_bao)
        self.ma, self.thong_bao, self.chi_tiet = ma, thong_bao, chi_tiet


def _dv_gia(goc: Path):
    kq = goc / "ket_qua"
    luot = kq / "20261021_100001"
    (luot / "x").mkdir(parents=True, exist_ok=True)
    (luot / "x" / "x_KET_QUA.json").write_bytes(b"{}")
    (luot / "_common" ).mkdir(exist_ok=True)
    (luot / "_common" / "request.json").write_bytes(b"{}")
    (kq / "20261021_100002").mkdir(exist_ok=True)                                # lượt legacy (không common)
    ch = SimpleNamespace(thu_muc_du_lieu=lambda: goc, thu_muc_ket_qua=lambda: kq)
    return SimpleNamespace(CONTRACT_COMMON=T6.CONTRACT, LoiNguoiDung=_LoiGia, ch=ch, _thu_muc_luot=lambda l: kq / l,
                           _la_luot_common=lambda l, d: l == "20261021_100001",
                           _cong_bo=lambda l, d: (True, {"tt": "done", "seal": {"ref": "x/x_KET_QUA.json"}}),
                           _da_niem_phong=lambda rec: rec is not None and rec.get("tt") == "done")


class _GocGia(BaseHTTPRequestHandler):
    toi = []

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json", extra=None):
        b = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    _body = None

    def raw(self):
        if self._body is None:
            n = int(self.headers.get("Content-Length") or 0)
            self._body = self.rfile.read(n) if n else b""
        return self._body

    def _xu_ly(self, m):
        self.toi.append((m, self.path, self.raw()))
        self._send(200, {"ok": True})

    def do_GET(self):
        self._xu_ly("GET")

    def do_POST(self):
        if self.path == "/api/tat":
            self.toi.append(("TAT", self.path, b""))
        self._xu_ly("POST")


class HandlerSoHuuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.goc = Path(tempfile.mkdtemp(prefix="ktt_t6h_hd_"))
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), _GocGia)
        cls.srv.RequestHandlerClass = H.lop_handler_so_huu(cls.srv.RequestHandlerClass, _dv_gia(cls.goc), TOKEN)
        cls.port = cls.srv.server_address[1]
        cls.th = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.th.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.th.join(10)

    def goi(self, method, path, body=None, *, token=TOKEN, host=None, origin=None, xhd=True):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Host": host or f"127.0.0.1:{self.port}"}
        if token is not None:
            h[H.HEADER_TOKEN] = token
        if xhd:
            h["X-HD"] = "1"
        if origin:
            h["Origin"] = origin
        data = json.dumps(body).encode() if isinstance(body, dict) else body
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        out = r.read()
        c.close()
        return r.status, (json.loads(out) if out[:1] == b"{" else out)

    def test_duong_tinh_truoc_cac_route_common(self):
        _GocGia.toi.clear()
        yc = {"contract": T6.CONTRACT, "mode": "RULE_ONLY"}
        for m, p, b in (("GET", "/api/trich_xuat/common", None), ("POST", "/api/trich_xuat", {"contract": T6.CONTRACT, "request_id": "r", "yeu_cau": yc}),
                        ("GET", "/api/trich_xuat/20261021_100001", None), ("POST", "/api/trich_xuat/20261021_100001/tep?ten=a.docx", b"PK"),
                        ("POST", "/api/trich_xuat/20261021_100001/chay", yc), ("POST", "/api/trich_xuat/20261021_100001/dung", {}),
                        ("GET", "/tai/ket_qua/20261021_100001/x/x_KET_QUA.json", None)):
            st, r = self.goi(m, p, b)
            self.assertEqual(st, 200, (m, p, r))
        self.assertEqual(len(_GocGia.toi), 7)
        self.assertEqual(_GocGia.toi[1][2], json.dumps({"contract": T6.CONTRACT, "request_id": "r", "yeu_cau": yc}).encode())  # body đệm nguyên bytes

    def test_cong_chan_truoc_handler_goc(self):
        _GocGia.toi.clear()
        yc = {"contract": T6.CONTRACT, "mode": "RULE_ONLY"}
        ca = [("GET", "/api/trich_xuat/common", None, {"token": None}, 403), ("GET", "/api/trich_xuat/common", None, {"token": "sai" * 15}, 403),
              ("GET", "/api/trich_xuat/common", None, {"host": "evil:1"}, 403), ("GET", "/api/trich_xuat/common", None, {"origin": "http://evil"}, 403),
              ("POST", "/api/trich_xuat", {"contract": T6.CONTRACT, "request_id": "r", "yeu_cau": yc}, {"xhd": False}, 403),
              ("POST", "/api/tat", {}, {}, 404), ("POST", "/api/tat", {}, {"token": None}, 403),
              ("POST", "/api/trich_xuat", {}, {}, 404), ("POST", "/api/trich_xuat", {"contract": T6.CONTRACT, "request_id": "r",
                                                                                     "yeu_cau": {**yc, "mode": "AI"}}, {}, 404),
              ("POST", "/api/trich_xuat/20261021_100001/chay", {}, {}, 404), ("POST", "/api/trich_xuat/20261021_100001/chay", {"tham_so": "ALL"}, {}, 404),
              ("POST", "/api/trich_xuat/20261021_100002/chay", yc, {}, 404),                        # lượt legacy
              ("POST", "/api/trich_xuat/20261021_100002/tep?ten=a.docx", b"PK", {}, 404),
              ("GET", "/api/trich_xuat", None, {}, 404), ("GET", "/api/viec", None, {}, 404), ("GET", "/", None, {}, 404),
              ("GET", "/api/cai_dat", None, {}, 404), ("GET", "/api/ai", None, {}, 404), ("GET", "/api/trich_xuat/20261021_100002", None, {}, 404),
              ("GET", "/tai/ket_qua/20261021_100001/_common/request.json", None, {}, 404),          # không phải ref đã niêm phong
              ("GET", "/tai/../ngoai.txt", None, {}, 404), ("POST", "/api/trich_xuat/20261021_100001/nap_csdl", {}, {}, 404),
              ("POST", "/api/trich_xuat/20261021_100001/chay_lai", {}, {}, 404), ("DELETE", "/api/trich_xuat/20261021_100001", None, {}, 404),
              ("PUT", "/api/trich_xuat/common", None, {}, 404)]
        for m, p, b, kw, ma in ca:
            st, r = self.goi(m, p, b, **kw)
            self.assertEqual(st, ma, (m, p, kw, r))
        self.assertEqual(_GocGia.toi, [])   # KHÔNG yêu cầu nào tới handler gốc (kể cả /api/tat)


def _con_song(pid: int) -> bool:
    import ctypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = ctypes.c_void_p
    h = k.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
    if not h:
        return False
    try:
        return k.WaitForSingleObject(ctypes.c_void_p(h), 0) == 0x102  # WAIT_TIMEOUT = còn sống
    finally:
        k.CloseHandle(ctypes.c_void_p(h))


@unittest.skipUnless(os.name == "nt", "Windows Job/KILL_ON_JOB_CLOSE chỉ có trên Windows — skip KHÔNG phải PASS")
@unittest.skipUnless((H.NGUON_MAC_DINH / "may_chu" / "server.py").is_file(), "không có nguồn #6 tại vị trí host đã chốt — skip KHÔNG phải PASS")
class VongDoiThatTests(unittest.TestCase):
    """Tiến trình con + mã nguồn #6 THẬT (chỉ đọc), DataRoot DEMO tạm (giữ lại)."""

    def goi(self, host, method, path, body=None, token=True):
        c = http.client.HTTPConnection("127.0.0.1", host._port, timeout=30)
        h = {"Host": f"127.0.0.1:{host._port}", "X-HD": "1"}
        if token:
            h[H.HEADER_TOKEN] = host._token
        c.request(method, path, body=json.dumps(body).encode() if body is not None else None, headers=h)
        r = c.getresponse()
        out = r.read()
        c.close()
        return r.status, out

    def test_vong_doi_auth_common_only_va_dung(self):
        dr = Path(tempfile.mkdtemp(prefix="ktt_t6h_that_"))
        h = H.Trich6Host(dr, H.NGUON_MAC_DINH)
        try:
            h.start()
            sk = h.suc_khoe()
            self.assertEqual((sk["san_sang"], sk["instance"]), (True, h.instance_id), sk)
            self.assertNotIn(h._token, json.dumps(sk))
            self.assertNotIn(str(h._port), json.dumps({k: v for k, v in sk.items() if k != "pid"}))
            for p in ("du_lieu/ket_qua", "du_lieu/danh_muc_hd", "khoa"):
                self.assertTrue((dr / p).is_dir(), p)                             # HD_* trong DataRoot DEMO riêng
            st, b = self.goi(h, "GET", "/api/trich_xuat/common")
            v = json.loads(b)
            self.assertEqual((st, v["contract"], v["implementation_sha256"]), (200, T6.CONTRACT, sk["implementation_sha256"]))
            self.assertEqual(self.goi(h, "GET", "/api/trich_xuat/common", token=False)[0], 403)
            self.assertEqual(self.goi(h, "POST", "/api/tat", {})[0], 404)          # /api/tat bị chặn trước nhánh riêng
            self.assertTrue(h.suc_khoe()["san_sang"])                              # vẫn sống
            for p, body in (("/api/trich_xuat", {}), ("/api/trich_xuat/20000101_000000/chay", {})):
                self.assertEqual(self.goi(h, "POST", p, body)[0], 404)
            for p in ("/api/trich_xuat", "/api/viec", "/", "/api/cai_dat", "/api/ai", "/tai/hop_dong.db"):
                self.assertEqual(self.goi(h, "GET", p)[0], 404, p)
            c = h.client(dr / "y-dinh")                                            # client chung + token bộ nhớ
            self.assertEqual(c.nang_luc("XD")["implementation_sha256"], sk["implementation_sha256"])
            port, pid = h._port, sk["pid"]
            gc = h._guard_con                                                      # 06A: guard THẬT của con, cùng quy tắc với cha
            self.assertIsNone(H.guard_hop_le(gc), gc)
            self.assertEqual((gc["sha256"], gc["hooks"]), (H.GUARD_SHA256, H.chung_cu_guard()["hooks"]))
        finally:
            h.stop()
        self.assertEqual((h._trang_thai, h._chung_dung), ("DA_DUNG", None))       # 06A: chỉ DA_DUNG sau xác nhận terminal + Job rỗng
        self.assertFalse(h.suc_khoe()["san_sang"])
        het = time.monotonic() + 30
        while _con_song(pid) and time.monotonic() < het:
            time.sleep(0.2)
        self.assertFalse(_con_song(pid))
        with self.assertRaises(OSError):
            socket_ = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            socket_.request("GET", "/api/trich_xuat/common")
            socket_.getresponse()

    def test_hai_instance_doc_lap_va_buoc_dung_central(self):
        """Dừng instance A không đụng B; central (tiến trình đứng thay) bị buộc dừng → Job đóng → engine của nó chết, B vẫn sống."""
        a = H.Trich6Host(Path(tempfile.mkdtemp(prefix="ktt_t6h_a_")), H.NGUON_MAC_DINH)
        b = H.Trich6Host(Path(tempfile.mkdtemp(prefix="ktt_t6h_b_")), H.NGUON_MAC_DINH)
        p = None
        try:
            a.start()
            b.start()
            a.stop()
            self.assertTrue(b.suc_khoe()["san_sang"])
            ma = ("import json,sys; from pathlib import Path; from kho_tri_thuc.nguon import trich6_host as H\n"
                  "h=H.Trich6Host(Path(sys.argv[1]), H.NGUON_MAC_DINH); h.start(); print(json.dumps({'pid': h._pid}), flush=True)\n"
                  "import time\nwhile True: time.sleep(1)\n")
            env = {**os.environ, "PYTHONPATH": str(H.SRC_CENTRAL) + os.pathsep + os.environ.get("PYTHONPATH", "")}
            p = subprocess.Popen([sys.executable, "-X", "utf8", "-c", ma, tempfile.mkdtemp(prefix="ktt_t6h_c_")], stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, env=env)
            dong = H._doc_dong(p.stdout, 120)
            pid_con = json.loads(dong)["pid"]
            self.assertTrue(_con_song(pid_con))
            p.kill()                                                               # buộc dừng "central"
            p.wait(30)
            het = time.monotonic() + 30
            while _con_song(pid_con) and time.monotonic() < het:
                time.sleep(0.2)
            self.assertFalse(_con_song(pid_con))
            self.assertTrue(b.suc_khoe()["san_sang"])                              # instance khác không bị chạm
        finally:
            try:                                                                   # 06A: kill nếu cần VÀ wait đúng Popen
                if p is not None:
                    if p.poll() is None:
                        p.kill()
                    p.wait(30)
                    p.stdout.close()
            finally:
                try:
                    b.stop()                                                       # cả hai host sở hữu đều được dọn dù một nhánh lỗi
                finally:
                    a.stop()

    def test_06a_docx_that_all37_tap_con_seal_replay_va_tu_choi(self):
        """THỰC qua owned endpoint + client chung (không phải độ chính xác toàn 37 mã/loại, không phải central hai consumer/GUI): DOCX DEMO có đáp án
        ghim; ALL37 rồi tập con trên CÙNG host; seal khớp bytes raw; replay cùng ý định không thêm lượt; các từ chối vẫn giữ; dừng xác nhận; B không
        bị chạm."""
        from kho_tri_thuc.kiem_chung import fixtures_m4 as F
        from kho_tri_thuc.m4 import nguon_review as NR
        dong = ("HỢP ĐỒNG THI CÔNG XÂY DỰNG (DEMO)", "Số: 0001/2026", "Điều 1. Công việc DEMO")
        docx = F.hop_dong_docx(dong)
        dr = Path(tempfile.mkdtemp(prefix="ktt_t6h_docx_"))
        h = H.Trich6Host(dr, H.NGUON_MAC_DINH)
        b = H.Trich6Host(Path(tempfile.mkdtemp(prefix="ktt_t6h_docx_b_")), H.NGUON_MAC_DINH)
        try:
            h.start()
            b.start()
            sk_b = b.suc_khoe()
            impl = h.suc_khoe()["implementation_sha256"]
            c = h.client(dr / "y-dinh")
            kq_dir = dr / "du_lieu" / "ket_qua"

            def so_luot():
                return sorted(p.name for p in kq_dir.iterdir() if p.is_dir() and H.RE_LUOT.fullmatch(p.name))

            def kiem_seal(r):
                s = c.doc(r["luot"])
                seal = s["common"]["seal"]
                self.assertEqual((s["common"]["tt"], seal["sha256"], seal["byte_length"]), ("done", r["raw_sha256"], len(r["raw_ket_qua"])))
                self.assertEqual(T6.sha256(r["raw_ket_qua"]), r["raw_sha256"])
            a37 = c.trich(docx, ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="that06a:all37")
            self.assertEqual(sorted(a37["common"]["tham_so_da_dung"]), sorted(NR.MA_DANH_MUC))
            self.assertEqual(len(a37["common"]["tham_so_da_dung"]), 37)
            self.assertEqual(sorted(d["ma"] for d in a37["ket_qua"]["bang"]), sorted(NR.MA_DANH_MUC))
            self.assertEqual(a37["common"]["catalog_sha256"], T6.CATALOG["XD"]["catalog_sha256"])
            self.assertEqual(a37["common"]["implementation"]["sha256"], impl)      # cùng implementation lúc khởi động
            tc = next(d for d in a37["ket_qua"]["bang"] if d["ma"] == "TC-01")
            self.assertEqual(str(tc["gia_tri"]).strip(), "0001/2026")
            q = str(tc["trich_dan"]).strip()
            self.assertIn("0001/2026", q)
            self.assertTrue(any(q in d for d in dong), q)                          # dẫn chứng là nguyên văn của input
            kiem_seal(a37)
            sub = c.trich(docx, ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=["TC-01", "TT-02"], request_id="that06a:sub")
            self.assertEqual(sub["common"]["tham_so_da_dung"], ["TC-01", "TT-02"])
            self.assertEqual(sorted(d["ma"] for d in sub["ket_qua"]["bang"]), ["TC-01", "TT-02"])
            self.assertEqual((sub["common"]["implementation"]["sha256"], sub["common"]["catalog_sha256"]), (impl, T6.CATALOG["XD"]["catalog_sha256"]))
            self.assertNotEqual(sub["luot"], a37["luot"])
            kiem_seal(sub)
            truoc = so_luot()
            lai = c.trich(docx, ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="that06a:all37")   # replay đúng ý định
            self.assertEqual((lai["luot"], lai["raw_ket_qua"], lai["raw_sha256"]), (a37["luot"], a37["raw_ket_qua"], a37["raw_sha256"]))
            self.assertEqual(so_luot(), truoc)                                     # không thêm lượt
            # các từ chối vẫn giữ trong ca thật; engine còn sống
            self.assertEqual(self.goi(h, "GET", "/api/trich_xuat/common", token=False)[0], 403)
            tok, h._token = h._token, "sai" * 15
            try:
                self.assertEqual(self.goi(h, "GET", "/api/trich_xuat/common")[0], 403)
            finally:
                h._token = tok
            for m, p, body in (("POST", "/api/trich_xuat", {}), ("POST", f"/api/trich_xuat/{a37['luot']}/chay", {}), ("POST", "/api/tat", {}),
                               ("GET", "/", None), ("GET", "/api/cai_dat", None), ("GET", "/api/ai", None), ("GET", "/api/trich_xuat", None),
                               ("GET", f"/tai/ket_qua/{a37['luot']}/_common/request.json", None)):
                self.assertEqual(self.goi(h, m, p, body)[0], 404, (m, p))
            self.assertTrue(h.suc_khoe()["san_sang"])
            h.stop()                                                               # dừng có xác nhận terminal + Job rỗng
            self.assertEqual((h._trang_thai, h._chung_dung), ("DA_DUNG", None))
            sk_b2 = b.suc_khoe()
            self.assertEqual((sk_b2["san_sang"], sk_b2["instance"], sk_b2["pid"], sk_b2["implementation_sha256"]),
                             (True, sk_b["instance"], sk_b["pid"], sk_b["implementation_sha256"]))   # instance B sống, không đổi
        finally:
            try:
                h.stop()                                                           # đã dừng thì no-op; nhánh lỗi vẫn dọn
            finally:
                b.stop()

    def _bien_the_khoi_dong(self, env_sua, ten):
        dr = Path(tempfile.mkdtemp(prefix="ktt_t6h_bt_"))
        h = H.Trich6Host(dr, H.NGUON_MAC_DINH)
        try:
            with mock.patch.dict(os.environ, {k: v for k, v in env_sua.items() if v is not None}):   # khôi phục env khi ra
                for k in [k for k, v in env_sua.items() if v is None]:
                    os.environ.pop(k, None)
                h.start()
            self.assertIsNone(H.guard_hop_le(h._guard_con), (ten, h._guard_con))
            self.assertTrue(H.HOOK_BAT_BUOC <= set(h._guard_con["hooks"]), ten)   # 06B: đủ ba hook thật trong CON
        finally:
            h.stop()

    # 06B: hai đường khởi động guard là HAI test riêng (thay ca kết hợp 06A vốn lệ thuộc usercustomize — sai với máy thật). Mỗi nhánh tự dò
    # provider THẬT bằng đọc tệp (không import guard); thiếu provider → skip riêng có lý do, KHÔNG phải PASS.
    @staticmethod
    def _pp():
        return [x for x in os.environ.get("PYTHONPATH", "").split(os.pathsep) if x]

    @staticmethod
    def _co_sitecustomize(d):
        return (Path(d) / "sitecustomize.py").is_file()

    def test_06b_userbase_pth_only(self):
        """THỰC: guard của con nạp CHỈ qua PYTHONUSERBASE → user site-packages `*.pth` chứa `import codex_no_delete_guard` (không usercustomize).
        Bỏ mọi thư mục PYTHONPATH có sitecustomize.py, giữ phần còn lại (src/phụ thuộc). Con phải có guard hợp lệ đủ ba hook."""
        import sysconfig
        ub = os.environ.get("PYTHONUSERBASE")
        if not ub:
            self.skipTest("runtime không đặt PYTHONUSERBASE — provider USERBASE/.pth không có, skip KHÔNG phải PASS")
        scheme = "nt_user" if os.name == "nt" else "posix_user"
        site_u = Path(sysconfig.get_path("purelib", scheme, vars={"userbase": ub}))
        pth = [p for p in (site_u.glob("*.pth") if site_u.is_dir() else []) if H.GUARD_MODULE in p.read_text(encoding="utf-8", errors="replace")]
        if not pth:
            self.skipTest("không có tệp .pth nạp codex_no_delete_guard trong user site-packages — skip KHÔNG phải PASS")
        pp = self._pp()
        self._bien_the_khoi_dong({"PYTHONPATH": os.pathsep.join(x for x in pp if not self._co_sitecustomize(x))}, "USERBASE/.pth-only")

    def test_06b_pythonpath_sitecustomize_only(self):
        """THỰC: guard của con nạp CHỈ qua PYTHONPATH/sitecustomize — bỏ PYTHONUSERBASE. Con phải có guard hợp lệ đủ ba hook."""
        if not any(self._co_sitecustomize(x) for x in self._pp()):
            self.skipTest("không có sitecustomize.py trong PYTHONPATH — provider PYTHONPATH/sitecustomize không có, skip KHÔNG phải PASS")
        self._bien_the_khoi_dong({"PYTHONUSERBASE": None}, "PYTHONPATH/sitecustomize-only")


if __name__ == "__main__":
    unittest.main()
