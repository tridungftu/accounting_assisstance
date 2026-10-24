"""Bảo đảm đúng cluster PostgreSQL ĐÃ CÓ đang chạy trước bước chuẩn bị CRM DEMO (nút mở DEMO; CRM-01 sửa04).

Phạm vi cố ý hẹp — chỉ dùng runtime + data directory đã được cài sẵn (CRM-03-TAI-SU-DUNG-KHOI-DONG-PG.md):
  - KHÔNG initdb, cài đặt, đăng ký service, nâng quyền/UAC; KHÔNG stop/kill tiến trình nào; KHÔNG xóa/sửa postmaster.pid, lock, WAL hay
    bất kỳ tệp nào của cluster; KHÔNG chạy trong request HTTP (chỉ launcher gọi qua tools/chuan_bi_crm_demo.py).
  - Vị trí mặc định theo bố cục thư mục cha của workspace (fact do Codex đã kiểm): `<cha>/var/postgresql16-16.15-runtime/bin/pg_ctl.exe`,
    data `<cha>/var/postgresql-ktt-16/data`, PG_VERSION 16, endpoint 127.0.0.1:5432; SHA256 pg_ctl.exe dự kiến ghi trong PG_CTL_SHA256.
    Có thể thay bằng tệp KHÔNG bí mật `<DataRoot>/crm-demo/cum-pg.local.json` (Codex/root cài một lần, tách khỏi tệp credentials):
      {"phien_ban": 1, "pg_ctl": "...", "data_dir": "...", "pg_version": "16", "host": "127.0.0.1", "port": 5432, "pg_ctl_sha256": "..."}

Luồng (pg_ctl 16: status 0 = đang chạy, 3 = không chạy, 4 = không truy cập được data directory; mã khác = không rõ → dừng):
  1. định danh: pg_ctl đúng tệp + hash, postgres.exe cùng thư mục, data dir tồn tại, PG_VERSION khớp; ổ đĩa vắng → lỗi riêng;
  2. tuần tự hóa: khóa tệp theo danh tính cluster (msvcrt/fcntl, chờ có hạn; tệp khóa không bao giờ bị xóa);
  3. status: đang chạy → xác minh PID của status = PID đang nghe đúng host:port, exe = postgres.exe của runtime này, đối số -D trỏ đúng data
     dir (so đường dẫn đã chuẩn hóa, không so chuỗi con) → dùng lại; không xác minh được → lỗi, không đụng tiến trình;
  4. không chạy (mã 3) và cổng KHÔNG có tiến trình nào nghe → `pg_ctl start -D <data> -l <log mới> -w -t <giây> -o "-h <host> -p <port>"`
     (ẩn cửa sổ, argv không DSN/mật khẩu); cổng bị tiến trình khác chiếm → lỗi, không giành cổng;
  5. start trả lỗi/timeout → kiểm status + định danh lại MỘT lần (server có thể vẫn đang lên); không spawn lại, không xóa lock.
Log mỗi lần start là tệp mới `pg-start-<UTC>-<pid>-<nonce>.log` (tạo độc quyền trước, không ghi đè/xóa log cũ).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .primitives import DataError

PG_CTL_SHA256 = "bed9ec9686fdf66b407f55d15be2466365827feb6b343fdb452c2dbcfbcfe0a1"
PHIEN_BAN_CUM = 1
HOST_CUM = frozenset({"127.0.0.1", "::1"})
CREATE_NO_WINDOW = 0x08000000


@dataclass(frozen=True)
class Cum:
    pg_ctl: Path
    data_dir: Path
    pg_version: str = "16"
    host: str = "127.0.0.1"
    port: int = 5432
    pg_ctl_sha256: str | None = PG_CTL_SHA256

    @property
    def postgres(self) -> Path:
        return self.pg_ctl.with_name("postgres.exe" if self.pg_ctl.suffix.lower() == ".exe" else "postgres")

    @property
    def danh_tinh(self) -> str:
        return hashlib.sha256(f"{_chuan(self.data_dir)}|{self.host}|{self.port}".encode()).hexdigest()[:16]


def _chuan(path) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(str(path))))


def cum_mac_dinh(repo_root) -> Cum:
    cha = Path(repo_root).resolve().parent
    return Cum(cha / "var" / "postgresql16-16.15-runtime" / "bin" / "pg_ctl.exe", cha / "var" / "postgresql-ktt-16" / "data")


def doc_cum(root, repo_root) -> Cum:
    """Cấu hình cluster không bí mật: tệp `<root>/crm-demo/cum-pg.local.json` nếu có, nếu không thì bố cục mặc định."""
    path = Path(root) / "crm-demo" / "cum-pg.local.json"
    if not path.is_file():
        return cum_mac_dinh(repo_root)
    try:
        v = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise DataError("CUM_CAU_HINH_SAI", "Tệp cấu hình cluster PostgreSQL DEMO không đọc được.") from None
    if not isinstance(v, dict) or v.get("phien_ban") != PHIEN_BAN_CUM or set(v) - {"phien_ban", "pg_ctl", "data_dir", "pg_version", "host", "port", "pg_ctl_sha256"} \
            or not isinstance(v.get("pg_ctl"), str) or not isinstance(v.get("data_dir"), str):
        raise DataError("CUM_CAU_HINH_SAI", "Tệp cấu hình cluster PostgreSQL DEMO sai định dạng.")
    if v.get("host", "127.0.0.1") not in HOST_CUM or not isinstance(v.get("port", 5432), int) or not 1 <= v.get("port", 5432) <= 65535:
        raise DataError("CUM_CAU_HINH_SAI", "Cluster DEMO chỉ nghe 127.0.0.1 hoặc ::1 với cổng hợp lệ.")
    return Cum(Path(v["pg_ctl"]), Path(v["data_dir"]), str(v.get("pg_version", "16")), v.get("host", "127.0.0.1"), v.get("port", 5432),
               v.get("pg_ctl_sha256", PG_CTL_SHA256))


# ------------------------------------------------------------------ thao tác hệ điều hành (thay được trong test bằng stub)
@dataclass
class HeDieuHanh:
    """Bộ thao tác thật. Test thay bằng stub; mọi lệnh đi qua `chay` để kiểm argv."""
    timeout_lenh: int = 30

    def chay(self, argv: list[str], timeout: int | None = None) -> tuple[int, str]:
        kw = {"creationflags": CREATE_NO_WINDOW} if sys.platform == "win32" else {}
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout or self.timeout_lenh, stdin=subprocess.DEVNULL, **kw)
        except subprocess.TimeoutExpired:
            return -1, ""
        return r.returncode, (r.stdout or "") + (r.stderr or "")

    def pid_dang_nghe(self, host: str, port: int) -> int | None:
        code, out = self.chay(["netstat", "-ano", "-p", "TCPv6" if ":" in host else "TCP"])
        if code != 0:
            raise DataError("CUM_KHONG_XAC_MINH", "Không đọc được bảng cổng đang nghe của hệ điều hành.")
        dia_chi = f"[{host}]:{port}" if ":" in host else f"{host}:{port}"
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0].upper().startswith("TCP") and parts[1] == dia_chi and parts[3].upper().startswith("LISTEN"):
                return int(parts[4])
        return None

    def tien_trinh(self, pid: int) -> dict | None:
        code, out = self.chay(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                               f"Get-CimInstance Win32_Process -Filter 'ProcessId = {int(pid)}' | Select-Object ExecutablePath,CommandLine | ConvertTo-Json -Compress"])
        if code != 0 or not out.strip():
            return None
        try:
            v = json.loads(out.strip().splitlines()[-1])
        except ValueError:
            return None
        return {"exe": v.get("ExecutablePath"), "cmd": v.get("CommandLine") or ""}

    def sha256(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------ khóa tuần tự theo cluster
@contextmanager
def khoa_cum(cum: Cum, thu_muc_khoa: Path, cho_giay: float = 120.0):
    """Khóa độc quyền theo danh tính cluster (tệp khóa giữ lại, không xóa). Hết thời gian chờ → lỗi, không vượt khóa."""
    thu_muc_khoa.mkdir(parents=True, exist_ok=True)
    path = thu_muc_khoa / f"ktt-pg-{cum.danh_tinh}.lock"
    f = open(path, "a+b")
    try:
        han = time.monotonic() + cho_giay
        while True:
            try:
                if sys.platform == "win32":
                    import msvcrt
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() > han:
                    raise DataError("CUM_DANG_BAN", "Một lần mở khác đang khởi động cluster PostgreSQL DEMO; thử lại sau.") from None
                time.sleep(0.2)
        try:
            yield
        finally:
            if sys.platform == "win32":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    finally:
        f.close()


# ------------------------------------------------------------------ kiểm định danh và trạng thái
def kiem_dinh_danh(cum: Cum, hdh: HeDieuHanh) -> None:
    anchor = Path(cum.data_dir.anchor or ".")
    if cum.data_dir.anchor and not anchor.exists():
        raise DataError("CUM_O_DIA_VANG", f"Ổ đĩa {cum.data_dir.anchor} chưa sẵn sàng — không tạo cluster ở nơi khác.")
    if not cum.pg_ctl.is_file() or cum.pg_ctl.name.lower() not in ("pg_ctl.exe", "pg_ctl"):
        raise DataError("CUM_SAI_RUNTIME", "Không thấy pg_ctl của runtime PostgreSQL đã cài.")
    if cum.pg_ctl_sha256 and hdh.sha256(cum.pg_ctl) != cum.pg_ctl_sha256:
        raise DataError("CUM_SAI_RUNTIME", "pg_ctl không khớp bản runtime đã định danh.")
    if not cum.postgres.is_file():
        raise DataError("CUM_SAI_RUNTIME", "Thiếu postgres cùng thư mục với pg_ctl.")
    if not cum.data_dir.is_dir():
        raise DataError("CUM_KHONG_TRUY_CAP", "Không thấy hoặc không truy cập được data directory của cluster đã cài.")
    try:
        version = (cum.data_dir / "PG_VERSION").read_text(encoding="ascii").strip()
    except OSError:
        raise DataError("CUM_KHONG_TRUY_CAP", "Không đọc được PG_VERSION của cluster.") from None
    if version != cum.pg_version:
        raise DataError("CUM_PG_VERSION", f"Cluster có PG_VERSION {version}, khác bản {cum.pg_version} đã định danh.")


def trang_thai(cum: Cum, hdh: HeDieuHanh) -> tuple[str, int | None]:
    code, out = hdh.chay([str(cum.pg_ctl), "status", "-D", str(cum.data_dir)])
    if code == 0:
        m = re.search(r"PID:\s*(\d+)", out)
        return "DANG_CHAY", int(m.group(1)) if m else None
    if code == 3:
        return "DUNG", None
    if code == 4:
        raise DataError("CUM_KHONG_TRUY_CAP", "pg_ctl báo không truy cập được data directory.")
    raise DataError("CUM_TRANG_THAI_KHONG_RO", f"pg_ctl status trả mã {code} — không suy là cluster đang dừng.")


def _doi_so_D(cmd: str) -> str | None:
    m = re.search(r'(?:^|\s)-D\s*(?:"([^"]+)"|(\S+))', cmd or "")
    return (m.group(1) or m.group(2)) if m else None


def xac_minh_dang_chay(cum: Cum, pid: int | None, hdh: HeDieuHanh) -> int:
    nghe = hdh.pid_dang_nghe(cum.host, cum.port)
    if pid is None or nghe != pid:
        raise DataError("CUM_KHONG_XAC_MINH", f"Tiến trình đang nghe {cum.host}:{cum.port} không phải cluster đã định danh (không đụng tới tiến trình đó).")
    tt = hdh.tien_trinh(pid)
    d = _doi_so_D(tt["cmd"]) if tt else None
    if not tt or not tt.get("exe") or _chuan(tt["exe"]) != _chuan(cum.postgres) or not d or _chuan(d) != _chuan(cum.data_dir):
        raise DataError("CUM_KHONG_XAC_MINH", "Không xác minh được tiến trình PostgreSQL thuộc đúng runtime + data directory đã định danh.")
    return pid


def _log_moi(thu_muc_log: Path) -> Path:
    thu_muc_log.mkdir(parents=True, exist_ok=True)
    for _ in range(5):
        path = thu_muc_log / f"pg-start-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{os.getpid()}-{secrets.token_hex(4)}.log"
        try:
            with open(path, "x", encoding="utf-8"):  # tạo độc quyền: không ghi đè log cũ
                pass
            return path
        except FileExistsError:
            continue
    raise DataError("CUM_LOG", "Không tạo được tệp log mới cho lần khởi động cluster.")


def bao_dam_cum(cum: Cum, thu_muc_log: Path, thu_muc_khoa: Path, *, hdh: HeDieuHanh | None = None, timeout_start: int = 60) -> dict:
    """Trả {"ket_qua": "DUNG_LAI"|"DA_KHOI_DONG", "pid", "log"?}. Mọi nhánh khác là DataError rõ mã; không có thao tác dừng/xóa."""
    hdh = hdh or HeDieuHanh()
    kiem_dinh_danh(cum, hdh)
    with khoa_cum(cum, thu_muc_khoa):
        state, pid = trang_thai(cum, hdh)
        if state == "DANG_CHAY":
            return {"ket_qua": "DUNG_LAI", "pid": xac_minh_dang_chay(cum, pid, hdh), "endpoint": f"{cum.host}:{cum.port}"}
        nghe = hdh.pid_dang_nghe(cum.host, cum.port)
        if nghe is not None:
            raise DataError("CUM_CONG_BI_CHIEM", f"Cổng {cum.host}:{cum.port} đang bị tiến trình khác dùng — không khởi động, không giành cổng.")
        log = _log_moi(thu_muc_log)
        code, _ = hdh.chay([str(cum.pg_ctl), "start", "-D", str(cum.data_dir), "-l", str(log), "-w", "-t", str(int(timeout_start)),
                            "-o", f"-h {cum.host} -p {int(cum.port)}"], timeout=timeout_start + 15)
        state, pid = trang_thai(cum, hdh)  # kiểm lại một lần kể cả khi start báo lỗi/timeout (server có thể vẫn đang lên)
        if state != "DANG_CHAY":
            raise DataError("CUM_KHONG_KHOI_DONG", f"Không khởi động được cluster PostgreSQL DEMO (mã {code}); xem log {log.name}.")
        return {"ket_qua": "DA_KHOI_DONG", "pid": xac_minh_dang_chay(cum, pid, hdh), "endpoint": f"{cum.host}:{cum.port}", "log": log.name,
                "start_ma": code}
