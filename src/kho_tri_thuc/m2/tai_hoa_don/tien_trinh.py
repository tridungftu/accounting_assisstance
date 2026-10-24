"""M2-00B — vòng đời tiến trình Node #7 SỞ HỮU (owned): spawn ghim, Job trước cấu hình, bắt tay, sẵn sàng, dừng hữu hạn có xác nhận.

Cùng mô hình host engine #6 (`nguon/trich6_host.py`), DÙNG LẠI `_JobWindows` và `_doc_dong` của host chung (không sửa host chung):
- Khởi tạo KHÔNG spawn. `start()` băm lại Node executable + tệp #7 đã ghim → `Popen(shell=False, CREATE_NO_WINDOW)` đúng
  `[node, <goc_7>/src/server.js, --owned]` → gán Windows Job KILL_ON_JOB_CLOSE TRƯỚC khi gửi cấu hình → một dòng JSON qua stdin (capability chỉ RAM,
  không argv/env/tệp/log/health) → đọc MỘT dòng bắt tay trong hạn: đúng protocol/instance/PID con/cổng/phiên bản → preflight `/api/config` có
  capability. Sai/quá hạn/thoát sớm/thiếu dependency/cổng bận → mã rõ + dừng ĐÚNG cây sở hữu; không cài đặt, không fallback server ngoài,
  không kill theo tên.
- `stop()`: EOF stdin → chờ grace → (quá hạn) kết thúc đúng Job → chờ terminal → Job rỗng. Chưa xác nhận → `DUNG_CHUA_XAC_NHAN` + witness
  (UNKNOWN), không báo đã dừng. Intent/receipt/tệp của producer giữ nguyên.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import subprocess
import threading
import time

from ...nguon.trich6_host import LoiHost, _doc_dong, _JobWindows
from .cau_hinh import CauHinhTaiHoaDon, kiem_khong_reparse
from .khach import KhachNode, LoiKhach

PROTOCOL = "source7-m2-owned/v1"
KIEU_CAU_HINH, KIEU_SAN_SANG, KIEU_LOI = "source7-m2-owned-config/v1", "source7-m2-owned-ready/v1", "source7-m2-owned-error/v1"
RE_MA_NODE = re.compile(r"[A-Z0-9][A-Z0-9_]{1,39}")
CREATE_NO_WINDOW = 0x08000000
# Môi trường Node: chỉ biến hệ thống cần chạy + chỗ cài Chromium của Playwright. Không TAX_*/PG*/DSN/NODE_OPTIONS/proxy/khóa của parent.
ENV_GIU = frozenset(k.upper() for k in ("SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "TEMP", "TMP", "PATH", "PATHEXT", "COMSPEC",
                                        "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "LOCALAPPDATA", "APPDATA", "USERPROFILE",
                                        "PROGRAMDATA", "PLAYWRIGHT_BROWSERS_PATH", "CODEX_NO_DELETE_FILES"))


class LoiTienTrinh(Exception):
    """Lỗi vòng đời Node sở hữu (mã ngắn, không token/đường dẫn)."""

    def __init__(self, ma: str, thong_bao: str = "", pha: str | None = None):
        super().__init__(thong_bao or ma)
        self.ma, self.pha = ma, pha


def env_node(goc_env=None) -> dict:
    goc_env = os.environ if goc_env is None else goc_env
    return {k: v for k, v in goc_env.items() if k.upper() in ENV_GIU}


def bam_tep(p, toi_da: int = 512 * 1024 * 1024) -> str:
    h, n = hashlib.sha256(), 0
    with open(p, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                return h.hexdigest()
            n += len(b)
            if n > toi_da:
                raise LoiTienTrinh("TEP_QUA_LON", "Tệp ghim vượt giới hạn băm.")
            h.update(b)


def _job_mac_dinh():
    if os.name != "nt":
        raise LoiTienTrinh("JOB_KHONG_HO_TRO", "Owned Node M2 cần Windows Job; nền tảng này chưa hỗ trợ.")
    return _JobWindows()


class TienTrinhNode:
    """Node #7 do máy chủ sở hữu. Seam kiểm thử: popen/job_factory/doc_dong/khach_factory/env (mặc định là bản thật)."""

    def __init__(self, cau_hinh: CauHinhTaiHoaDon, *, popen=subprocess.Popen, job_factory=_job_mac_dinh, doc_dong=_doc_dong,
                 khach_factory=KhachNode, env=None):
        if not isinstance(cau_hinh, CauHinhTaiHoaDon):
            raise LoiTienTrinh("CAU_HINH_SAI", "Cần CauHinhTaiHoaDon do máy chủ cấp.")
        self.cau_hinh = cau_hinh
        self._popen, self._job_factory, self._doc_dong, self._khach_factory = popen, job_factory, doc_dong, khach_factory
        self._env = env
        self.instance_id = secrets.token_hex(8)
        self._khoa = threading.Lock()
        self._proc = self._job = self._cap = self._port = self._pid = None
        self._trang_thai = "CHUA_KHOI_DONG"
        self._chung_dung = None

    def __repr__(self):
        return f"TienTrinhNode(instance={self.instance_id}, trang_thai={self._trang_thai})"

    @property
    def trang_thai(self) -> str:
        return self._trang_thai

    @property
    def chung_dung(self):
        return None if self._chung_dung is None else dict(self._chung_dung)

    # ------------------------------------------------------------------ khởi động
    def _kiem_pin(self):
        ch = self.cau_hinh
        try:
            kiem_khong_reparse(ch.node_exe, la_thu_muc=False)
        except Exception:
            raise LoiTienTrinh("NODE_KHONG_CO", "Không thấy Node executable đã ghim.") from None
        if bam_tep(ch.node_exe) != ch.node_sha256:
            raise LoiTienTrinh("NODE_SHA_SAI", "Node executable khác bản đã ghim.")
        for t in ch.tep_pin:
            p = ch.goc_7.joinpath(*t.rel.split("/"))
            try:
                kiem_khong_reparse(p, la_thu_muc=False)
            except Exception:
                raise LoiTienTrinh("TEP_PIN_KHONG_CO", "Thiếu tệp #7 đã ghim.") from None
            if bam_tep(p) != t.sha256:
                raise LoiTienTrinh("TEP_PIN_SAI", "Tệp #7 khác bản đã ghim.")

    def _kiem_bat_tay(self, hs, proc) -> int:
        ch = self.cau_hinh
        if isinstance(hs, dict) and hs.get("kieu") == KIEU_LOI:
            ma = hs.get("ma")
            raise LoiTienTrinh("NODE_" + (ma if isinstance(ma, str) and RE_MA_NODE.fullmatch(ma) else "LOI"), "Node báo lỗi khởi động.")
        if not isinstance(hs, dict) or hs.get("kieu") != KIEU_SAN_SANG or hs.get("protocol") != PROTOCOL \
                or hs.get("instance_id") != self.instance_id:
            raise LoiTienTrinh("BAT_TAY_SAI", "Bắt tay owned Node sai protocol/instance.")
        if type(hs.get("pid")) is not int or hs["pid"] != proc.pid:
            raise LoiTienTrinh("BAT_TAY_PID_SAI", "PID bắt tay không phải tiến trình con sở hữu.")
        port = hs.get("port")
        if type(port) is not int or not 0 < port < 65536 or (ch.cong and port != ch.cong):
            raise LoiTienTrinh("BAT_TAY_CONG_SAI", "Cổng bắt tay sai.")
        if hs.get("version") != ch.phien_ban_bo_tai:
            raise LoiTienTrinh("BAT_TAY_PHIEN_BAN_SAI", "Phiên bản bộ tải khác bản đã ghim.")
        return port

    def start(self) -> dict:
        with self._khoa:
            if self._proc is not None:
                raise LoiTienTrinh("DA_KHOI_DONG", "Owned Node của instance này đã khởi động.")
            self._trang_thai = "DANG_KHOI_DONG"
            ch = self.cau_hinh
            job = proc = None
            try:
                self._kiem_pin()
                cap = secrets.token_urlsafe(32)
                try:
                    job = self._job_factory()
                except LoiHost as e:
                    raise LoiTienTrinh(e.ma, "Không tạo được Job sở hữu.") from None
                try:
                    proc = self._popen([str(ch.node_exe), str(ch.server_js), "--owned"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL, cwd=str(ch.goc_7), env=env_node(self._env), shell=False, close_fds=True,
                                       creationflags=(CREATE_NO_WINDOW if os.name == "nt" else 0))
                except FileNotFoundError:
                    raise LoiTienTrinh("NODE_KHONG_CO", "Không chạy được Node executable đã ghim.") from None
                except OSError:
                    raise LoiTienTrinh("NODE_SPAWN_LOI", "Không spawn được owned Node.") from None
                try:
                    job.gan(proc)  # Job TRƯỚC khi con nhận capability/cấu hình
                except LoiHost as e:
                    raise LoiTienTrinh(e.ma, "Không gán được owned Node vào Job.") from None
                cfg = {"kieu": KIEU_CAU_HINH, "protocol": PROTOCOL, "capability": cap, "port": ch.cong, "instance_id": self.instance_id,
                       "roots": ch.roots_node(), "limits": ch.gioi_han.cho_node()}
                try:
                    proc.stdin.write((json.dumps(cfg, ensure_ascii=False) + "\n").encode("utf-8"))
                    proc.stdin.flush()
                except OSError:
                    raise LoiTienTrinh("NODE_THOAT_SOM", "Owned Node đóng stdin trước khi nhận cấu hình.") from None
                finally:
                    cfg = None
                dong = self._doc_dong(proc.stdout, ch.gioi_han.khoi_dong_s)
                if not dong:
                    raise LoiTienTrinh("NODE_THOAT_SOM" if proc.poll() is not None else "BAT_TAY_QUA_HAN", "Không nhận được bắt tay.")
                try:
                    hs = json.loads(dong.decode("utf-8"))
                except (UnicodeDecodeError, ValueError):
                    hs = None
                port = self._kiem_bat_tay(hs, proc)
                khach = self._khach_factory(port, cap, ch.gioi_han)
                try:
                    nl = khach.config()
                except LoiKhach as e:
                    raise LoiTienTrinh("SAN_SANG_LOI", f"Preflight owned Node lỗi ({e.ma}).") from None
                if nl.get("protocol") != PROTOCOL or nl.get("version") != ch.phien_ban_bo_tai:
                    raise LoiTienTrinh("SAN_SANG_SAI", "Preflight owned Node khác protocol/phiên bản.")
                self._proc, self._job, self._cap, self._port, self._pid = proc, job, cap, port, proc.pid
                self._trang_thai = "SAN_SANG"
                return {"trang_thai": "SAN_SANG", "pid": proc.pid, "port": port, "version": nl["version"], "instance": self.instance_id}
            except BaseException as exc:
                ma = exc.ma if isinstance(exc, LoiTienTrinh) else type(exc).__name__
                self._proc = self._job = self._cap = self._port = self._pid = None
                try:
                    self._don(proc, job)
                    self._trang_thai = "KHOI_DONG_LOI:" + ma
                except LoiTienTrinh as e2:
                    self._chung_dung = {"popen_pid": getattr(proc, "pid", None), "pha": e2.pha, "ma": e2.ma}
                    self._trang_thai = "KHOI_DONG_LOI:" + ma + "+DUNG_CHUA_XAC_NHAN"
                raise

    # ------------------------------------------------------------------ dừng
    def stop(self) -> dict:
        with self._khoa:
            proc, job, pid = self._proc, self._job, self._pid
            if proc is None and job is None:  # chưa khởi động / đã dừng / khởi động lỗi: giữ nguyên trạng thái + witness, không bịa DA_DUNG
                return {"trang_thai": self._trang_thai, "chung_dung": self.chung_dung}
            self._cap = self._port = None
            self._trang_thai = "DANG_DUNG"
            try:
                self._don(proc, job)
            except LoiTienTrinh as e:
                self._chung_dung = {"popen_pid": getattr(proc, "pid", None), "pid": pid, "pha": e.pha, "ma": e.ma}
                self._proc = self._job = None
                self._trang_thai = "DUNG_CHUA_XAC_NHAN"
                raise LoiTienTrinh("DUNG_CHUA_XAC_NHAN", f"Chưa xác nhận owned Node đã dừng ({e.ma}).", e.pha) from None
            self._proc = self._job = None
            self._chung_dung = None
            self._trang_thai = "DA_DUNG"
            return {"trang_thai": "DA_DUNG", "chung_dung": None}

    def _cho_job_rong(self, job, han: float) -> bool:
        het = time.monotonic() + han
        while True:
            if job.so_tien_trinh() == 0:
                return True
            if time.monotonic() >= het:
                return False
            time.sleep(0.05)

    def _don(self, proc, job):
        """Dừng ĐÚNG proc/Job sở hữu, hữu hạn; mọi bước quá hạn/thất bại → LoiTienTrinh có `pha`. finally đóng handle Job sở hữu."""
        gh = self.cau_hinh.gioi_han
        pha = "BAT_DAU"
        try:
            if proc is not None:
                pha = "EOF"
                try:
                    proc.stdin.close()
                except (OSError, AttributeError):
                    pass
                try:
                    proc.wait(gh.dung_s)
                except subprocess.TimeoutExpired:
                    pha = "KET_THUC_SAU_GRACE"
                    if job is not None:
                        job.ket_thuc()
                    else:
                        proc.kill()
                    pha = "CHO_TERMINAL"
                    proc.wait(10)
                if proc.poll() is None:
                    raise LoiTienTrinh("TIEN_TRINH_CON_SONG", "Owned Node chưa kết thúc.", pha)
            if job is not None:
                pha = "KIEM_JOB"
                if job.so_tien_trinh() > 0:  # Node đã thoát nhưng Chromium/worker lồng còn → chốt đúng Job sở hữu
                    pha = "KET_THUC_WORKER"
                    job.ket_thuc()
                pha = "CHO_JOB_RONG"
                if not self._cho_job_rong(job, gh.cho_job_s):
                    raise LoiTienTrinh("JOB_CON_TIEN_TRINH", "Job sở hữu còn tiến trình.", pha)
        except subprocess.TimeoutExpired:
            raise LoiTienTrinh("CHO_TERMINAL_QUA_HAN", "Quá hạn chờ owned Node kết thúc.", pha) from None
        except LoiHost as e:
            raise LoiTienTrinh(e.ma, "Lỗi Job sở hữu khi dừng.", pha) from None
        except LoiTienTrinh as e:
            e.pha = e.pha or pha
            raise
        except OSError as exc:
            raise LoiTienTrinh("DUNG_LOI_HE_THONG", f"Lỗi hệ thống khi dừng ({type(exc).__name__}).", pha) from None
        finally:
            if proc is not None:
                try:
                    proc.stdout.close()
                except (OSError, AttributeError):
                    pass
            if job is not None:
                job.dong()

    # ------------------------------------------------------------------ dùng
    def dang_chay(self) -> bool:
        return self._proc is not None and self._proc.poll() is None and self._cap is not None

    def khach(self) -> KhachNode:
        """Client của ĐÚNG instance này. Node chưa sẵn sàng/đã chết → LoiTienTrinh NODE_CHUA_SAN_SANG (không rơi về server ngoài)."""
        if not self.dang_chay():
            raise LoiTienTrinh("NODE_CHUA_SAN_SANG", "Owned Node chưa sẵn sàng.")
        return self._khach_factory(self._port, self._cap, self.cau_hinh.gioi_han)

    def suc_khoe(self) -> dict:
        """Readiness không bí mật: không cổng/đường dẫn/capability."""
        out = {"quan_ly": True, "instance": self.instance_id, "trang_thai": self._trang_thai}
        if self._chung_dung is not None:
            out["chung_dung"] = dict(self._chung_dung)
        out["san_sang"] = self.dang_chay()
        if out["san_sang"]:
            out["pid"] = self._pid
        return out
