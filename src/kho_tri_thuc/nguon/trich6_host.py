"""CRM-41-01-06 — host nhỏ của engine trích DÙNG CHUNG #6 cho bản DEMO: central sở hữu MỘT tiến trình con chạy CHÍNH factory nguồn thật
(`may_chu.server.tao_may_chu(0)`) trên dữ liệu DEMO riêng, chỉ mở các route common/v1, có quyền nội bộ theo instance.

Không phải lõi trích, không chép/sửa mã nguồn #6, không framework. Hai nửa trong một tệp:
- PARENT (`Trich6Host`): chỉ được `serve()`/CLI DEMO tạo và khởi động (KHÔNG trong LocalApp constructor). Dùng đúng python hiện hành
  (`sys.executable`) và PYTHONPATH runtime/guard đang chạy; Windows Job `KILL_ON_JOB_CLOSE` gán TRƯỚC khi gửi cấu hình qua stdin; token ngẫu nhiên
  chỉ trong bộ nhớ (không argv/env/tệp/URL/log/health). Dừng: EOF stdin → con đóng server, chờ việc hữu hạn; quá hạn → kết thúc Job của mình.
- CHILD (`python -m kho_tri_thuc.nguon.trich6_host --child`): đọc MỘT dòng cấu hình từ stdin TRƯỚC mọi import nguồn; đặt HD_* vào thư mục DEMO
  riêng; gọi factory thật; bọc Handler THEO INSTANCE trên `srv.RequestHandlerClass` (không đổi ROUTES/PORT/Handler toàn cục ngoài những gì factory
  vốn làm); báo bắt tay một dòng JSON trên kênh stdout riêng; phục vụ tới khi stdin EOF. Không gọi main()/thăm dò AI/_thay_ban_cu.
"""

from __future__ import annotations

import hmac
import http.client
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

# Nguồn #6 do HOST tin cậy quyết định (quyết định engine dùng chung) — không nhận từ trình duyệt, không dò/chép.
NGUON_MAC_DINH = Path("D:/Claude/Ho tro review ho so xay dung/review_xaydung")
CONTRACT = "trich-tham-so-common/v1"
HEADER_TOKEN = "X-Trich6-Token"
KIEU_CAU_HINH, KIEU_SAN_SANG, KIEU_LOI = "trich6_host_cau_hinh/v1", "trich6_host_san_sang/v1", "trich6_host_loi/v1"
RE_LUOT = re.compile(r"\d{8}_\d{6}(?:_\d+)?")
RE_HEX64 = re.compile(r"[0-9a-f]{64}")
# SOURCE6-G5-E5: biến thể tagged `doi_chieu_ban_ky` trên CÙNG common lifecycle — cổng chỉ mở body ĐÚNG 13 khóa (8 legacy + 5 E5), JSON nghiêm.
MODE_E5 = "doi_chieu_ban_ky"
KHOA_E5 = frozenset({"contract", "mode", "loai_hop_dong", "catalog_id", "catalog_sha256", "source_sha256", "request_id", "tham_so",
                     "signed_pdf_sha256", "expected", "expected_sha256", "catalog_binding", "catalog_binding_sha256"})
# Môi trường con: CHỈ runtime/guard + kỹ thuật cần chạy. Không PG*/DSN/API key/cloud/KHO_*/HD_* của parent.
# 06A/06B: giữ CẢ HAI đường khởi động guard hiện hành — PYTHONUSERBASE (tệp `.pth` trong user site-packages `import codex_no_delete_guard`,
# KHÔNG phải usercustomize) và PYTHONPATH (sitecustomize) — cùng cờ CODEX_NO_DELETE_FILES.
ENV_GIU = frozenset(k.upper() for k in ("SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "TEMP", "TMP", "PATH", "PATHEXT", "COMSPEC", "NUMBER_OF_PROCESSORS",
                                        "PROCESSOR_ARCHITECTURE", "PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE", "CODEX_NO_DELETE_FILES"))
SRC_CENTRAL = Path(__file__).resolve().parents[2]
# 06A: guard giữ tệp A517 phải được nạp TỪ KHỞI ĐỘNG (không import bù), đúng bytes, cờ bật, hook xóa/ghi đè THẬT đang cài, bytecode tắt.
GUARD_MODULE = "codex_no_delete_guard"
GUARD_SHA256 = "a517c5359ceada062900edd34280d4dc7daa2a001d5e05c84a9eae174813a229"
HAM_XOA = (("os", "remove"), ("os", "unlink"), ("os", "rmdir"), ("os", "removedirs"), ("os", "replace"), ("os", "rename"), ("os", "renames"),
           ("shutil", "rmtree"), ("shutil", "move"), ("pathlib", "Path.unlink"), ("pathlib", "Path.rmdir"), ("pathlib", "Path.replace"),
           ("pathlib", "Path.rename"))
# 06B: guard A517 trực tiếp cài ĐÚNG ba điểm này — cả ba phải là hook thật từ tệp guard (tập con khác/thiếu một → không đạt).
HOOK_BAT_BUOC = frozenset({"os.unlink", "os.remove", "shutil.rmtree"})


def _bat(v) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes", "on")


def chung_cu_guard() -> dict:
    """Chứng cứ guard KHÔNG bí mật của CHÍNH tiến trình này, chỉ đọc: module guard có trong `sys.modules` từ khởi động (KHÔNG import), SHA-256
    bytes tệp guard đang nạp, cờ CODEX_NO_DELETE_FILES, các điểm vào xóa/ghi đè đang là hàm định nghĩa TRONG tệp guard đó (hook thật), bytecode
    tắt theo cờ khởi động. Không trả đường dẫn."""
    import hashlib
    import importlib
    m = sys.modules.get(GUARD_MODULE)
    tep = getattr(m, "__file__", None) if m is not None else None
    sha = None
    if isinstance(tep, str) and os.path.isfile(tep):
        with open(tep, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
    chuan = os.path.normcase(os.path.realpath(tep)) if isinstance(tep, str) else None
    hooks = []
    for mod, ten in HAM_XOA:
        obj = sys.modules.get(mod) or importlib.import_module(mod)   # os/shutil/pathlib stdlib — không phải guard
        for phan in ten.split("."):
            obj = getattr(obj, phan, None)
        code = getattr(obj, "__code__", None)
        f = getattr(code, "co_filename", "") if code is not None else ""
        if chuan and f and not f.startswith("<") and os.path.normcase(os.path.realpath(f)) == chuan:
            hooks.append(f"{mod}.{ten}")
    return {"module": m is not None, "sha256": sha, "flag": _bat(os.environ.get("CODEX_NO_DELETE_FILES")), "hooks": hooks,
            "bytecode_tat": bool(sys.flags.dont_write_bytecode)}


def guard_hop_le(cc) -> str | None:
    """None nếu chứng cứ guard đạt; ngược lại mã lỗi ngắn (NOT_READY). Kiểm cả hai phía (cha và con) bằng cùng quy tắc."""
    if not isinstance(cc, dict) or cc.get("module") is not True:
        return "GUARD_KHONG_NAP"
    if cc.get("sha256") != GUARD_SHA256:
        return "GUARD_SHA_SAI"
    if cc.get("flag") is not True:
        return "GUARD_CO_TAT"
    hooks = cc.get("hooks")
    if not isinstance(hooks, list) or not all(isinstance(x, str) for x in hooks) or not set(hooks) <= {f"{m}.{t}" for m, t in HAM_XOA} \
            or not HOOK_BAT_BUOC <= set(hooks):   # 06B: ĐỦ BA hook bắt buộc, không chấp nhận tập con không rỗng bất kỳ
        return "GUARD_KHONG_HOOK"
    if cc.get("bytecode_tat") is not True:
        return "GUARD_BYTECODE_BAT"
    return None


class LoiHost(Exception):
    """Lỗi vòng đời host (mã ngắn, không chứa token/đường dẫn bí mật)."""

    def __init__(self, ma: str, thong_bao: str):
        super().__init__(thong_bao)
        self.ma = ma


# ================================================================================================== PARENT
def env_con(goc_env=None) -> dict:
    """Môi trường của tiến trình con: lọc theo danh sách giữ; PYTHONPATH = src central + PYTHONPATH runtime/guard hiện hành; không ghi bytecode."""
    goc_env = os.environ if goc_env is None else goc_env
    env = {k: v for k, v in goc_env.items() if k.upper() in ENV_GIU}
    pp = next((v for k, v in env.items() if k.upper() == "PYTHONPATH"), "")
    env = {k: v for k, v in env.items() if k.upper() != "PYTHONPATH"}
    env["PYTHONPATH"] = str(SRC_CENTRAL) + (os.pathsep + pp if pp else "")
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    return env


def lenh_con(python: str) -> list:
    """argv của tiến trình con — KHÔNG chứa token/cấu hình (đi qua stdin sau khi gán Job)."""
    return [python, "-X", "utf8", "-m", "kho_tri_thuc.nguon.trich6_host", "--child"]


class _JobWindows:
    """Windows Job Object `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`: đóng handle (kể cả khi central bị buộc dừng) → mọi tiến trình con/worker lồng chết."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self._c, self._w = ctypes, wintypes
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.CreateJobObjectW.restype = wintypes.HANDLE
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        k.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        self._k = k

        class Acct(ctypes.Structure):   # JOBOBJECT_BASIC_ACCOUNTING_INFORMATION
            _fields_ = [("TotalUserTime", ctypes.c_int64), ("TotalKernelTime", ctypes.c_int64), ("ThisPeriodTotalUserTime", ctypes.c_int64),
                        ("ThisPeriodTotalKernelTime", ctypes.c_int64), ("TotalPageFaultCount", wintypes.DWORD), ("TotalProcesses", wintypes.DWORD),
                        ("ActiveProcesses", wintypes.DWORD), ("TotalTerminatedProcesses", wintypes.DWORD)]
        self._Acct = Acct

        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                                                          "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class Basic(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64), ("LimitFlags", wintypes.DWORD),
                        ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

        class Ext(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", IO), ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]
        h = k.CreateJobObjectW(None, None)
        if not h:
            raise LoiHost("JOB_TAO_LOI", "Không tạo được Windows Job cho engine DEMO.")
        info = Ext()
        info.BasicLimitInformation.LimitFlags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not k.SetInformationJobObject(h, 9, ctypes.byref(info), ctypes.sizeof(info)):  # JobObjectExtendedLimitInformation
            k.CloseHandle(h)
            raise LoiHost("JOB_CAU_HINH_LOI", "Không đặt được KILL_ON_JOB_CLOSE cho Job engine DEMO.")
        self._h = h

    def gan(self, proc):
        if not self._k.AssignProcessToJobObject(self._h, self._w.HANDLE(int(proc._handle))):
            raise LoiHost("JOB_GAN_LOI", "Không gán được tiến trình engine DEMO vào Job.")

    def ket_thuc(self):
        """Kết thúc MỌI tiến trình trong ĐÚNG Job của instance này (không quét tên tiến trình, không chạm PID ngoài Job)."""
        if not self._h or not self._k.TerminateJobObject(self._h, 1):
            raise LoiHost("JOB_KET_THUC_LOI", "Không kết thúc được Job engine DEMO.")

    def so_tien_trinh(self) -> int:
        """Số tiến trình còn ACTIVE trong Job (truy vấn hữu hạn trên handle còn hợp lệ). Lỗi → LoiHost (không đoán là rỗng)."""
        a = self._Acct()
        if not self._h or not self._k.QueryInformationJobObject(self._h, 1, self._c.byref(a), self._c.sizeof(a), None):
            raise LoiHost("JOB_TRUY_VAN_LOI", "Không truy vấn được Job engine DEMO.")
        return int(a.ActiveProcesses)

    def dong(self):
        if self._h:
            self._k.CloseHandle(self._h)
            self._h = None


def _doc_dong(stream, han: float):
    """Đọc MỘT dòng bắt tay trong hạn (luồng phụ, không chặn vô hạn)."""
    kq = []
    t = threading.Thread(target=lambda: kq.append(stream.readline(64 * 1024)), daemon=True)
    t.start()
    t.join(han)
    return kq[0] if kq else None


class Trich6Host:
    """Tiến trình engine #6 DEMO do central sở hữu. Khởi tạo KHÔNG spawn; `start()` mới spawn (chỉ serve()/CLI DEMO gọi)."""

    def __init__(self, data_root, nguon=NGUON_MAC_DINH, *, python: str | None = None, cho_khoi_dong: float = 90.0, cho_dung: float = 30.0):
        self.data_root = Path(data_root)
        self.nguon = Path(nguon)
        self.python = python or sys.executable
        self.cho_khoi_dong, self.cho_dung = cho_khoi_dong, cho_dung
        self.instance_id = secrets.token_hex(8)   # định danh KHÔNG bí mật của instance (health/báo cáo)
        self._khoa = threading.Lock()
        self._proc = self._job = self._token = self._port = self._pid = self._impl = None
        self._trang_thai = "CHUA_KHOI_DONG"
        self.cho_job = 10.0          # 06A: hạn hữu hạn chờ Job rỗng sau khi kết thúc
        self._guard_con = None       # chứng cứ guard KHÔNG bí mật của tiến trình con (bắt tay)
        self._chung_dung = None      # witness khi dừng CHƯA xác nhận: {popen_pid, pid, pha, ma}

    def __repr__(self):
        return f"Trich6Host(instance={self.instance_id}, trang_thai={self._trang_thai})"  # không lộ token/cổng

    # ------------------------------------------------------------------ vòng đời
    def start(self):
        with self._khoa:
            if self._proc is not None:
                raise LoiHost("DA_KHOI_DONG", "Engine DEMO của instance này đã khởi động.")
            self._trang_thai = "DANG_KHOI_DONG"
            nguon = self.nguon.resolve()
            if not (nguon / "may_chu" / "server.py").is_file() or not (nguon / "trich_xuat").is_dir():
                self._trang_thai = "NGUON_KHONG_CO"
                raise LoiHost("NGUON_KHONG_CO", "Không thấy mã nguồn engine #6 tại vị trí host đã chốt.")
            ma_guard = guard_hop_le(chung_cu_guard())   # 06A: cha cũng phải có guard A517 THẬT từ khởi động — thiếu thì không spawn
            if ma_guard:
                self._trang_thai = ma_guard
                raise LoiHost(ma_guard, "Guard giữ tệp của tiến trình central chưa đạt — không mở engine DEMO.")
            self.data_root.mkdir(parents=True, exist_ok=True)
            token = secrets.token_urlsafe(32)
            job = proc = None
            try:
                job = _JobWindows() if os.name == "nt" else None
                proc = subprocess.Popen(lenh_con(self.python), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        cwd=str(self.data_root), env=env_con(), close_fds=True,
                                        creationflags=(0x08000000 if os.name == "nt" else 0))  # CREATE_NO_WINDOW: chạy ẩn
                if job is not None:
                    job.gan(proc)        # Job TRƯỚC khi con nhận cấu hình/bí mật; con chưa nhận input thì chưa import nguồn
                cfg = {"kieu": KIEU_CAU_HINH, "token": token, "nguon": str(nguon), "du_lieu": str(self.data_root.resolve()),
                       "instance_id": self.instance_id}
                proc.stdin.write((json.dumps(cfg, ensure_ascii=False) + "\n").encode("utf-8"))
                proc.stdin.flush()
                dong = _doc_dong(proc.stdout, self.cho_khoi_dong)
                try:
                    hs = json.loads(dong.decode("utf-8")) if dong else None
                except (ValueError, UnicodeDecodeError):
                    hs = None
                if not isinstance(hs, dict) or hs.get("kieu") != KIEU_SAN_SANG or hs.get("instance_id") != self.instance_id \
                        or type(hs.get("port")) is not int or not 0 < hs["port"] < 65536 or type(hs.get("pid")) is not int \
                        or not isinstance(hs.get("implementation_sha256"), str) or not RE_HEX64.fullmatch(hs["implementation_sha256"]):
                    ma = hs.get("ma") if isinstance(hs, dict) and hs.get("kieu") == KIEU_LOI else "BAT_TAY_SAI"
                    raise LoiHost(str(ma)[:40] if str(ma).startswith("GUARD_") else "KHOI_DONG_LOI", f"Engine DEMO không khởi động được ({str(ma)[:60]}).")
                ma_guard = guard_hop_le(hs.get("guard"))   # 06A: chứng cứ guard của CON, cùng bắt tay instance/implementation
                if ma_guard:
                    raise LoiHost(ma_guard, "Guard giữ tệp của engine DEMO chưa đạt.")
                self._guard_con = hs["guard"]
                self._proc, self._job, self._token, self._port, self._pid, self._impl = proc, job, token, hs["port"], hs["pid"], hs["implementation_sha256"]
                ok, ly_do = self._kiem_song()   # sẵn sàng THẬT: preflight có xác thực, đúng implementation đã bắt tay
                if not ok:
                    raise LoiHost("KHOI_DONG_LOI", f"Engine DEMO không qua kiểm sẵn sàng ({ly_do}).")
                self._trang_thai = "SAN_SANG"
            except BaseException as exc:
                self._proc = self._job = self._token = self._port = self._pid = self._impl = None
                ma = exc.ma if isinstance(exc, LoiHost) else type(exc).__name__
                try:
                    self._don(proc, job)
                    self._trang_thai = "KHOI_DONG_LOI:" + ma
                except LoiHost as e2:          # dọn chưa xác nhận: KHÔNG che lỗi gốc, giữ witness để đối soát
                    self._chung_dung = {"popen_pid": getattr(proc, "pid", None), "pid": None, "pha": getattr(e2, "pha", None), "ma": e2.ma}
                    self._trang_thai = "KHOI_DONG_LOI:" + ma + "+DUNG_CHUA_XAC_NHAN"
                raise

    def stop(self):
        """Dừng có XÁC NHẬN: chỉ công bố DA_DUNG khi tiến trình đúng của instance đã kết thúc VÀ Job sở hữu không còn tiến trình active (Windows).
        Chưa xác nhận được → LoiHost DUNG_CHUA_XAC_NHAN + trạng thái/witness (popen_pid/pid/pha), KHÔNG báo đã dừng."""
        with self._khoa:
            proc, job, pid = self._proc, self._job, self._pid
            if proc is None and job is None:
                if self._trang_thai in ("SAN_SANG", "DANG_KHOI_DONG", "CHUA_KHOI_DONG"):
                    self._trang_thai = "DA_DUNG"
                return
            self._token = self._port = None   # không phục vụ client mới trong lúc dừng
            self._trang_thai = "DANG_DUNG"
            try:
                self._don(proc, job)
            except LoiHost as e:
                self._chung_dung = {"popen_pid": getattr(proc, "pid", None), "pid": pid, "pha": getattr(e, "pha", None), "ma": e.ma}
                self._proc = self._job = None   # handle Job đã đóng trong finally của _don; witness giữ ở _chung_dung
                self._trang_thai = "DUNG_CHUA_XAC_NHAN"
                raise LoiHost("DUNG_CHUA_XAC_NHAN", f"Chưa xác nhận engine DEMO đã dừng ({e.ma}).") from None
            self._proc = self._job = None
            self._chung_dung = None
            self._trang_thai = "DA_DUNG"

    def _cho_job_rong(self, job, han):
        het = time.monotonic() + han
        while True:
            n = job.so_tien_trinh()
            if n == 0:
                return True
            if time.monotonic() >= het:
                return False
            time.sleep(0.05)

    def _don(self, proc, job):
        """Dừng ĐÚNG tiến trình/Job của instance này, có xác nhận hữu hạn: EOF stdin → chờ grace → (quá hạn) kết thúc ĐÚNG Job/kill đúng Popen →
        chờ terminal; sau khi con đã thoát vẫn kiểm Job: còn worker active → kết thúc Job rồi chờ Job rỗng. Bất kỳ bước nào quá hạn/thất bại →
        LoiHost có `pha` (không nuốt). `finally` luôn đóng đúng handle Job sở hữu; không quét tên tiến trình, không chạm PID ngoài."""
        pha = "BAT_DAU"
        try:
            if proc is not None:
                pha = "EOF"
                try:
                    proc.stdin.close()
                except (OSError, AttributeError):
                    pass
                try:
                    proc.wait(self.cho_dung)
                except subprocess.TimeoutExpired:
                    pha = "KET_THUC_SAU_GRACE"
                    if job is not None:
                        job.ket_thuc()
                    else:
                        proc.kill()
                    pha = "CHO_TERMINAL"
                    proc.wait(10)                  # quá hạn → TimeoutExpired → chưa xác nhận
                if proc.poll() is None:
                    raise LoiHost("TIEN_TRINH_CON_SONG", "Tiến trình engine DEMO chưa kết thúc.")
            if job is not None:
                pha = "KIEM_JOB"
                if job.so_tien_trinh() > 0:        # con đã thoát nhưng worker lồng còn sống → chốt đúng Job sở hữu
                    pha = "KET_THUC_WORKER"
                    job.ket_thuc()
                pha = "CHO_JOB_RONG"
                if not self._cho_job_rong(job, self.cho_job):
                    raise LoiHost("JOB_CON_TIEN_TRINH", "Job engine DEMO vẫn còn tiến trình sau khi kết thúc.")
        except subprocess.TimeoutExpired:
            e = LoiHost("CHO_TERMINAL_QUA_HAN", "Quá hạn chờ engine DEMO kết thúc.")
            e.pha = pha
            raise e from None
        except LoiHost as e:
            e.pha = getattr(e, "pha", None) or pha
            raise
        except OSError as exc:
            e = LoiHost("DUNG_LOI_HE_THONG", f"Lỗi hệ thống khi dừng engine DEMO ({type(exc).__name__}).")
            e.pha = pha
            raise e from None
        finally:
            if proc is not None:
                try:
                    proc.stdout.close()
                except (OSError, AttributeError):
                    pass
            if job is not None:
                job.dong()

    # ------------------------------------------------------------------ sẵn sàng / health
    def _kiem_song(self):
        """Preflight common/v1 THẬT có token tới đúng cổng đã bắt tay; implementation phải khớp danh tính lúc khởi động."""
        if self._proc is None or self._proc.poll() is not None:
            return False, "ENGINE_DA_DUNG"
        c = http.client.HTTPConnection("127.0.0.1", self._port, timeout=3)
        try:
            c.request("GET", "/api/trich_xuat/common", headers={"Host": f"127.0.0.1:{self._port}", HEADER_TOKEN: self._token})
            r = c.getresponse()
            st, b = r.status, r.read()
        except (OSError, http.client.HTTPException):
            return False, "KHONG_KET_NOI"
        finally:
            c.close()
        try:
            v = json.loads(b.decode("utf-8")) if st == 200 else None
        except (ValueError, UnicodeDecodeError):
            v = None
        if not isinstance(v, dict) or v.get("kieu") != "nang_luc_common/v1" or v.get("contract") != CONTRACT:
            return False, f"PREFLIGHT_{st}"
        if v.get("implementation_sha256") != self._impl:
            return False, "IMPLEMENTATION_KHAC"
        if v.get("san_sang") is not True:
            return False, "ENGINE_CHUA_SAN_SANG"
        return True, None

    def suc_khoe(self) -> dict:
        """Readiness KHÔNG bí mật cho /api/health: không URL/cổng/đường dẫn/token. Kiểm sống thật mỗi lần (không bool đệm)."""
        out = {"quan_ly": True, "instance": self.instance_id}
        if self._chung_dung is not None:   # 06A: dừng chưa xác nhận → NOT_READY kèm witness không bí mật (pid/pha/mã)
            out["chung_dung"] = dict(self._chung_dung)
        if self._proc is None or self._token is None:
            return {**out, "san_sang": False, "ly_do": self._trang_thai}
        ok, ly_do = self._kiem_song()
        return {**out, "san_sang": ok, "ly_do": ly_do, "pid": self._pid, "implementation_sha256": self._impl}

    def client(self, goc):
        """Client chung của consumer (CRM/M4) cho instance này. Engine chưa sẵn sàng/đã chết → client NOT_READY tường minh (base_url ""),
        KHÔNG rơi về KHO_TRICH6_URL môi trường."""
        from .trich_chung_6 import Trich6Client
        if self._proc is not None and self._proc.poll() is None and self._port:
            return Trich6Client(f"http://127.0.0.1:{self._port}", goc=goc, token=self._token)
        return Trich6Client("", goc=goc)


# ================================================================================================== CHILD
def lop_handler_so_huu(Goc, dv, token: str):
    """Handler THEO INSTANCE bọc Handler của factory nguồn: Host/Origin/X-HD theo cổng thật của server này + token bộ nhớ (hmac.compare_digest)
    cho MỌI request; cổng method/path đứng TRƯỚC route legacy/tĩnh và trước nhánh riêng `/api/tat`. Chỉ mở common/v1."""
    tb = token.encode("utf-8")
    common = dv.CONTRACT_COMMON

    class HandlerSoHuu(Goc):
        def _hop_le(self, ghi):
            port = self.server.server_port   # KHÔNG dùng PORT toàn cục của nguồn
            host = (self.headers.get("Host") or "").lower()
            if host not in (f"localhost:{port}", f"127.0.0.1:{port}"):
                return False
            origin = self.headers.get("Origin")
            if origin and origin.lower() not in (f"http://localhost:{port}", f"http://127.0.0.1:{port}"):
                return False
            return not ghi or self.headers.get("X-HD") == "1"

        def _tu_choi(self, ma_http, ma):
            self._send(ma_http, {"loi": "Không được phép trên engine DEMO sở hữu", "chi_tiet": {"ma": ma}})
            return False

        def _cong(self, method):
            path = urlsplit(self.path).path
            if not self._hop_le(method != "GET"):
                return self._tu_choi(403, "OWNED_HOST_ORIGIN")
            if not hmac.compare_digest((self.headers.get(HEADER_TOKEN) or "").encode("utf-8"), tb):
                return self._tu_choi(403, "OWNED_TOKEN")
            try:
                ok = self._cho_phep(method, path)
            except dv.LoiNguoiDung as e:
                self._send(e.ma, {"loi": e.thong_bao, "chi_tiet": e.chi_tiet})
                return False
            except Exception:  # noqa: BLE001 — dữ kiện không kiểm được ở cổng → từ chối hữu hạn, không chạm legacy
                return self._tu_choi(400, "OWNED_KHONG_KIEM_DUOC")
            return True if ok else self._tu_choi(404, "OWNED_KHONG_MO")

        def _body_json(self):
            try:
                v = json.loads(self.raw().decode("utf-8"))  # raw() của nguồn đệm body → route thật đọc lại đúng bytes
            except (ValueError, UnicodeDecodeError):
                return {}
            return v if isinstance(v, dict) else {}

        def _body_json_e5(self):
            """SOURCE6-G5-E5: body JSON NGHIÊM cho biến thể đối chiếu bản ký — khóa trùng ở bất kỳ mức nào, NaN/Infinity, không phải object →
            None (cổng từ chối, không chạm route)."""
            def mot_lan(cap):
                d = {}
                for k, v in cap:
                    if k in d:
                        raise ValueError("khóa trùng")
                    d[k] = v
                return d

            def hang(_x):
                raise ValueError("hằng số JSON không hữu hạn")
            try:
                v = json.loads(self.raw().decode("utf-8"), object_pairs_hook=mot_lan, parse_constant=hang)
            except (ValueError, UnicodeDecodeError):
                return None
            return v if isinstance(v, dict) else None

        def _e5_hop_le(self, y):
            """Thân E5 đúng tag: đủ ĐÚNG 13 khóa, contract common, mode E5, source = PDF ký. Kiểm cấu trúc sâu do nguồn làm (_kiem_common)."""
            return isinstance(y, dict) and set(y) == KHOA_E5 and y.get("contract") == common and y.get("mode") == MODE_E5 \
                and isinstance(y.get("source_sha256"), str) and RE_HEX64.fullmatch(y["source_sha256"]) is not None \
                and y.get("signed_pdf_sha256") == y["source_sha256"]

        def _la_common(self, luot):
            if not RE_LUOT.fullmatch(luot):
                return False
            d = dv._thu_muc_luot(luot)
            return d.is_dir() and dv._la_luot_common(luot, d)

        def _ket_qua_niem_phong(self, rel):
            goc = dv.ch.thu_muc_du_lieu().resolve()
            kq = dv.ch.thu_muc_ket_qua().resolve()
            p = (goc / rel).resolve()
            if kq not in p.parents:
                return False
            luot = p.relative_to(kq).parts[0]
            if not self._la_common(luot):
                return False
            _la, rec = dv._cong_bo(luot, kq / luot)
            if not dv._da_niem_phong(rec):
                return False
            return p.is_file() and p == (kq / luot / rec["seal"]["ref"]).resolve()   # đúng tệp kết quả đã niêm phong, không tệp nguồn tùy ý

        def _cho_phep(self, method, path):
            if method == "GET":
                if path == "/api/trich_xuat/common":
                    return True
                m = re.fullmatch(r"/api/trich_xuat/([^/]+)", path)
                if m:
                    return self._la_common(m.group(1))
                if path.startswith("/tai/"):
                    return self._ket_qua_niem_phong(unquote(path[5:]))
                return False
            if method != "POST":
                return False
            if path == "/api/trich_xuat":
                b = self._body_json()
                y = b.get("yeu_cau")
                if isinstance(y, dict) and y.get("mode") == MODE_E5:   # SOURCE6-G5-E5: chỉ thân tagged đúng 13 khóa, JSON nghiêm
                    b = self._body_json_e5()
                    return b is not None and set(b) == {"contract", "request_id", "yeu_cau"} and b["contract"] == common \
                        and self._e5_hop_le(b["yeu_cau"]) and b["request_id"] == b["yeu_cau"].get("request_id")
                return set(b) == {"contract", "request_id", "yeu_cau"} and b["contract"] == common and isinstance(y, dict) \
                    and y.get("contract") == common and y.get("mode") == "RULE_ONLY"
            m = re.fullmatch(r"/api/trich_xuat/([^/]+)/(tep|chay|dung)", path)
            if not m or not self._la_common(m.group(1)):
                return False
            if m.group(2) == "chay":
                b = self._body_json()
                if b.get("mode") == MODE_E5:
                    return self._e5_hop_le(self._body_json_e5())
                return b.get("contract") == common and b.get("mode") == "RULE_ONLY"
            return True

        def do_GET(self):
            if self._cong("GET"):
                super().do_GET()

        def do_POST(self):
            if self._cong("POST"):
                super().do_POST()

        def _cam(self):
            self._cong(self.command)

        do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _cam

    HandlerSoHuu.__name__ = HandlerSoHuu.__qualname__ = "HandlerSoHuu"
    return HandlerSoHuu


# L0-7: thư viện nặng mà luồng worker (`chay` → `tc_theo_quy_tac` → `import master_hd` → `import openpyxl`) sẽ import LƯỜI. openpyxl tự import
# numpy nếu máy có; lần import numpy ĐẦU TIÊN ở luồng phụ khi luồng chính đang `serve_forever` bị kẹt ở `create_module` của
# `numpy._core._multiarray_umath` (client timeout → TRICH6_KHONG_KET_NOI). Nạp sẵn ở LUỒNG CHÍNH trước khi phục vụ thì lệnh trích đầu tiên chạy bình thường.
# Không bắt buộc có từng mô-đun: thiếu/lỗi → ghi log ngắn (tên mô-đun + loại lỗi, không đường dẫn) rồi đi tiếp.
THU_VIEN_NAP_SAN = ("numpy", "openpyxl", "openpyxl.styles", "openpyxl.utils", "openpyxl.worksheet.datavalidation", "docx")


def nap_san_thu_vien(ds=THU_VIEN_NAP_SAN, ghi_log=None) -> dict:
    """Nạp sẵn các mô-đun trong `ds` (gọi ở luồng chính của tiến trình con, TRƯỚC khi phục vụ). Không bao giờ ném lỗi; trả {tên: "ok"|"khong_co"|"loi"}."""
    import importlib
    ghi_log = ghi_log or (lambda m: print(m, file=sys.stderr, flush=True))
    kq = {}
    for ten in ds:
        try:
            importlib.import_module(ten)
            kq[ten] = "ok"
        except ImportError as e:
            kq[ten] = "khong_co"
            ghi_log(f"trich6_host: nap san {ten} khong duoc ({type(e).__name__}) - bo qua")
        except Exception as e:  # noqa: BLE001 — nạp sẵn chỉ là tối ưu an toàn, lỗi gì cũng không được chặn khởi động
            kq[ten] = "loi"
            ghi_log(f"trich6_host: nap san {ten} loi {type(e).__name__} - bo qua")
    return kq


def _con(stdin=None, kenh=None) -> int:
    """Entry tiến trình con. Đọc cấu hình rồi KIỂM GUARD A517 (chứng cứ thật trong tiến trình) TRƯỚC mọi mkdir/HD_*/import nguồn — thiếu/sai →
    báo mã ngắn và thoát, không mở nguồn. Kênh bắt tay `kenh` (text) do entry `__main__` tạo từ bản sao fd stdout."""
    stdin = stdin or sys.stdin.buffer

    def bao(v):
        kenh.write(json.dumps(v, ensure_ascii=False) + "\n")
        kenh.flush()
    dong = stdin.readline(64 * 1024)
    try:
        cfg = json.loads(dong.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        cfg = None
    if not isinstance(cfg, dict) or cfg.get("kieu") != KIEU_CAU_HINH or not isinstance(cfg.get("token"), str) or len(cfg["token"]) < 32 \
            or not all(isinstance(cfg.get(k), str) and cfg[k] for k in ("nguon", "du_lieu", "instance_id")):
        bao({"kieu": KIEU_LOI, "ma": "CAU_HINH_SAI"})
        return 2
    cc = chung_cu_guard()                     # 06A: guard từ KHỞI ĐỘNG (không import bù), hook thật, cờ bật, bytecode tắt
    ma_guard = guard_hop_le(cc)
    if ma_guard:
        bao({"kieu": KIEU_LOI, "ma": ma_guard})
        return 4                              # fail closed: chưa mkdir, chưa đặt HD_*, chưa import nguồn, chưa mở server
    sys.dont_write_bytecode = True   # nguồn thật CHỈ ĐỌC: không ghi __pycache__
    try:
        goc = Path(cfg["du_lieu"])
        dl = goc / "du_lieu"
        for p in (dl, dl / "ket_qua", dl / "danh_muc_hd", goc / "khoa"):
            p.mkdir(parents=True, exist_ok=True)
        for k in [k for k in os.environ if k.upper().startswith("HD_")] + ["OLLAMA_URL", "AI_MODEL", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]:
            os.environ.pop(k, None)
        os.environ.update(HD_DU_LIEU=str(dl), HD_OUT_DIR=str(dl / "ket_qua"), HD_DANH_MUC_HD=str(dl / "danh_muc_hd"),
                          HD_CSDL=str(dl / "hop_dong.db"), HD_THU_MUC_KHOA=str(goc / "khoa"))   # TRƯỚC import nguồn
        nap_san_thu_vien()                         # L0-7: nạp numpy/openpyxl/docx ở LUỒNG CHÍNH trước khi phục vụ (luồng worker import lười sẽ kẹt)
        sys.path.insert(0, cfg["nguon"])
        from may_chu import dich_vu as dv          # noqa: E402 — chỉ sau khi đặt HD_*
        from may_chu import server as sv           # noqa: E402
        srv = sv.tao_may_chu(0)                    # factory thật, cổng loopback ngẫu nhiên
        srv.RequestHandlerClass = lop_handler_so_huu(srv.RequestHandlerClass, dv, cfg["token"])   # theo instance, trước serve
        impl = dv._implementation()["sha256"]
    except Exception as e:  # noqa: BLE001
        bao({"kieu": KIEU_LOI, "ma": type(e).__name__})
        return 3
    cfg["token"] = None
    th = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True)
    th.start()
    bao({"kieu": KIEU_SAN_SANG, "instance_id": cfg["instance_id"], "pid": os.getpid(), "port": srv.server_address[1], "implementation_sha256": impl,
         "guard": chung_cu_guard()})   # chứng cứ guard lấy LẠI sau khi nạp nguồn (hook vẫn còn), không đường dẫn/token
    try:
        while stdin.read(4096):   # sống tới khi owner đóng stdin (EOF) hoặc chết (Job đóng)
            pass
    finally:
        srv.shutdown()
        srv.server_close()
        th.join(10)
        het = time.monotonic() + 25
        while dv.QLV.dang_chay() and time.monotonic() < het:   # chờ worker hữu hạn; quá hạn parent kết thúc Job
            time.sleep(0.2)
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--child"]:
        _kenh = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8")
        sys.stdout = sys.stderr   # bản in của mã nguồn không làm hỏng kênh bắt tay
        sys.exit(_con(kenh=_kenh))
    sys.exit(2)
