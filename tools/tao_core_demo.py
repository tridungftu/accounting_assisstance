#!/usr/bin/env python3
"""Dựng Core DEMO rỗng, không migrate/seed hoặc khởi động PostgreSQL.

Lead chạy: python -X utf8 tools/tao_core_demo.py --ma g2_00
Nguồn cố định: <repo chính>/var/web/crm-demo/ket-noi.local.json.
Đích: <worktree>/var/core-demo/<ma>/{kho-tep,bi-mat,ket-noi.local.json}.
Két chỉ là thư mục rỗng; DPAPI và credential runtime thuộc G2-23/33.
Chỉ CREATE DATABASE từ template0 trên cụm DEMO mặc định đã có; không DROP,
không sửa cấu hình đã tồn tại, không in nội dung DSN hoặc ngoại lệ driver.
"""

from __future__ import annotations

import argparse
import json
import ntpath
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

# Cho phép gọi trực tiếp từ tools/ mà không cần cài package.
REPO = Path(__file__).resolve().parents[1]
for _goc in (REPO, REPO / "src"):
    if str(_goc) not in sys.path:
        sys.path.insert(0, str(_goc))

from tools.tao_ket_noi_demo_rieng import (  # noqa: E402
    TuChoi, _gia_tri, _quet_cap_khoa_gia_tri, nap_tep,
    thay_ten_csdl, tim_repo_chinh,
)
from kho_tri_thuc.ha_tang.pg_cum import cum_mac_dinh  # noqa: E402

TIEN_TO = "kho_core_demo_g2_"
TEN_TEP = "ket-noi.local.json"
_TEN = re.compile(r"kho_core_demo_g2_[a-z0-9_]+")
_KHOA_DSN = frozenset({
    "host", "hostaddr", "port", "dbname", "user", "password", "sslmode",
    "connect_timeout", "application_name",
})


def kiem_ten_csdl(ten: str) -> None:
    if not isinstance(ten, str) or not _TEN.fullmatch(ten) or len(ten) > 63:
        raise TuChoi("Tên CSDL phải là kho_core_demo_g2_<ma>, tối đa 63 ký tự.")


def kiem_duong_dan_cam(path) -> None:
    """Kiểm bằng cú pháp Windows cả khi test trên Linux, trước mọi truy cập tệp."""
    raw = str(path).replace("/", "\\")
    if raw.startswith(("\\\\?\\", "\\\\.\\")):
        raise TuChoi("Không nhận đường dẫn thiết bị Windows.")
    p = ntpath.normcase(ntpath.normpath(raw))
    cac_phan = [v.rstrip(" .") for v in p.split("\\")]
    if (p == r"d:\du-lieu-ke-toan" or p.startswith("d:\\du-lieu-ke-toan\\")
            or any(a == "var" and b in {"plhn-that", "web-that"}
                   for a, b in zip(cac_phan, cac_phan[1:]))
            or "du-lieu-ke-toan" in cac_phan
            or cac_phan[-1] in {".env", "cau_hinh.that.toml"}):
        raise TuChoi("Từ chối đường dẫn dữ liệu thật hoặc cấu hình thật.")


def _duong_dan_an_toan(path: Path, *, strict: bool = False) -> Path:
    kiem_duong_dan_cam(path)
    dich = path.resolve(strict=strict)
    kiem_duong_dan_cam(dich)
    # Không theo junction/symlink ra khỏi vùng đã chỉ định, kể cả tới tệp khác.
    if ntpath.normcase(str(dich)) != ntpath.normcase(str(path.absolute())):
        raise TuChoi("Đường dẫn bị chuyển hướng; cần lead kiểm môi trường.")
    return dich


def _tham_so_dsn(dsn: str) -> dict:
    """Dùng bộ quét libpq hiện có; từ chối tham số gián tiếp và trùng khóa."""
    try:
        if re.match(r"^\s*postgres(ql)?://", dsn, re.I):
            u = urlsplit(dsn.strip())
            cap = [("host", u.hostname or ""), ("port", str(u.port or "")),
                   ("dbname", unquote(u.path[1:])),
                   ("user", unquote(u.username or "")),
                   ("password", unquote(u.password or ""))]
            cap += parse_qsl(u.query, keep_blank_values=True, strict_parsing=True)
            if u.fragment:
                raise ValueError
        else:
            cap = [(k, _gia_tri(dsn[a:b])) for k, a, b in _quet_cap_khoa_gia_tri(dsn)]
        d = dict(cap)
        if len(d) != len(cap) or set(d) - _KHOA_DSN:
            raise ValueError
        host = d.get("host", "").lower()
        addr = {"localhost": "127.0.0.1", "127.0.0.1": "127.0.0.1", "::1": "::1"}.get(host)
        if not addr or d.get("hostaddr", addr) != addr:
            raise ValueError
        if not d.get("port", "").isdigit() or not 1 <= int(d["port"]) <= 65535:
            raise ValueError
        if not d.get("user") or not d.get("password"):
            raise ValueError
        if not re.fullmatch(r"kho_crm_demo(?:_[a-z0-9_]+)?", d.get("dbname", "")):
            raise ValueError
        # Giá trị tường minh ngăn PGHOSTADDR/PGOPTIONS/PGPASSWORD đổi đích.
        d.update(hostaddr=addr, options="", connect_timeout="5")
        return d
    except Exception:
        raise TuChoi("Nguồn phải là DSN CRM DEMO loopback tường minh, không tham số gián tiếp.") from None


def _kiem_cum(conn, tham_so: dict, cum) -> None:
    row = conn.execute("""SELECT current_database(), host(inet_server_addr()),
        inet_server_port(), current_setting('data_directory'),
        current_setting('server_version_num')""").fetchone()
    if not row or len(row) != 5:
        raise TuChoi("Không xác minh được cụm PostgreSQL DEMO.")
    db, host, port, data_dir, version = row
    data_dir = _duong_dan_an_toan(Path(data_dir), strict=True)
    du_lieu_cum = _duong_dan_an_toan(cum.data_dir, strict=True)
    if (db != tham_so["dbname"] or host != tham_so["hostaddr"]
            or int(port) != int(tham_so["port"]) or host != cum.host or int(port) != cum.port
            or ntpath.normcase(str(data_dir)) != ntpath.normcase(str(du_lieu_cum))
            or not 160000 <= int(version) < 170000):
        raise TuChoi("Cụm PostgreSQL không khớp cụm DEMO đã định danh; không tạo CSDL.")


def _kiem_tep_co_san(tep: Path, noi_dung: dict) -> bool:
    if not tep.exists():
        return False
    if not tep.is_file() or nap_tep(tep) != noi_dung:
        raise TuChoi("Cấu hình đích đã có nhưng khác nội dung; không ghi đè.")
    return True


def _dat_quyen_tep(tep: Path) -> bool:
    """Thử giới hạn tệp cho người dùng hiện tại, không nâng quyền/không in lỗi."""
    try:
        if sys.platform != "win32":
            tep.chmod(0o600)
            return True
        # DACL mới chỉ có một ACE, không giữ ACE cũ hoặc quyền kế thừa.
        lenh = """$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$p = [Console]::In.ReadToEnd()
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$acl = New-Object System.Security.AccessControl.FileSecurity
$acl.SetOwner($sid)
$acl.SetAccessRuleProtection($true, $false)
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule($sid, 'FullControl', 'Allow')
$acl.AddAccessRule($rule)
Set-Acl -LiteralPath $p -AclObject $acl
"""
        powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        ket_qua = subprocess.run(
            [str(powershell), "-NoProfile", "-NonInteractive", "-Command", lenh],
            input=str(tep), encoding="utf-8", capture_output=True, timeout=15,
            creationflags=0x08000000,
        )
        return ket_qua.returncode == 0
    except (OSError, KeyError, subprocess.SubprocessError):
        return False  # DEMO vẫn dùng *.local.json ngoài git khi môi trường không hỗ trợ ACL.


def tao_core_demo(ma: str) -> dict:
    """Kết quả chỉ có tên/trạng thái; toàn bộ lỗi ở biên đều che credential."""
    try:
        return _tao_core_demo(ma)
    except TuChoi:
        raise
    except (Exception, KeyboardInterrupt):
        raise TuChoi("Không dựng được Core DEMO; giữ nguyên dữ liệu, cần lead kiểm môi trường.") from None


def _tao_core_demo(ma: str) -> dict:
    ten = TIEN_TO + ma if isinstance(ma, str) else ""
    kiem_ten_csdl(ten)
    chinh = tim_repo_chinh(REPO)
    if chinh is None:
        raise TuChoi("Không xác định được repo chính; cần lead kiểm môi trường.")
    nguon = _duong_dan_an_toan(chinh / "var" / "web" / "crm-demo" / TEN_TEP)
    root = _duong_dan_an_toan(REPO / "var" / "core-demo" / ma)
    tep = _duong_dan_an_toan(root / TEN_TEP)
    cac_kho = [_duong_dan_an_toan(root / v) for v in ("kho-tep", "bi-mat")]
    for thu_muc in [root, *cac_kho]:
        if thu_muc.exists() and not thu_muc.is_dir():
            raise TuChoi("Vùng DEMO đã có tệp cản đường; không tạo đè.")
    goc = nap_tep(nguon)  # Chỉ chương trình đọc, tuyệt đối không in tệp/DSN.
    app, admin = _tham_so_dsn(goc["app_dsn"]), _tham_so_dsn(goc["admin_dsn"])
    if any(app[k] != admin[k] for k in ("hostaddr", "port", "dbname")):
        raise TuChoi("Hai DSN nguồn không cùng CSDL và endpoint DEMO.")
    moi = dict(goc)
    for khoa in ("app_dsn", "admin_dsn"):
        moi[khoa] = thay_ten_csdl(goc[khoa], ten)[1]
    da_co_tep = _kiem_tep_co_san(tep, moi)
    cum = cum_mac_dinh(chinh)  # Chỉ tính đường dẫn, không đọc/start/stop cụm.
    _duong_dan_an_toan(cum.data_dir, strict=True)
    import psycopg

    with psycopg.connect(**admin, autocommit=True) as conn:
        _kiem_cum(conn, admin, cum)  # Luôn kiểm cả khi DB đích đã tồn tại.
        da_co = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (ten,)).fetchone() is not None
        if not da_co:
            try:
                conn.execute(f'CREATE DATABASE "{ten}" ENCODING \'UTF8\' TEMPLATE template0')
            except psycopg.errors.DuplicateDatabase:
                da_co = True  # Lượt khác tạo trước; không DROP hoặc dựng đè.
    for thu_muc in [root, *cac_kho]:
        thu_muc.mkdir(parents=True, exist_ok=True)
    if not da_co_tep:
        try:
            with tep.open("x", encoding="utf-8", newline="\n") as f:
                _dat_quyen_tep(tep)  # Siết quyền trước khi ghi credential nếu hệ điều hành cho phép.
                # DEMO giữ *.local.json trong var/, ngoài git; CSDL thật dùng két DPAPI (G2-23).
                json.dump(moi, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except FileExistsError:
            _kiem_tep_co_san(tep, moi)
            da_co_tep = True
    if da_co_tep:
        _dat_quyen_tep(tep)
    return {"csdl": ten, "csdl_trang_thai": "DA_CO" if da_co else "DA_TAO",
            "cau_hinh_trang_thai": "DA_CO" if da_co_tep else "DA_TAO"}


def main(argv=None) -> int:
    # Không để argparse echo giá trị đối số không hợp lệ (có thể là bí mật).
    class BoPhanTich(argparse.ArgumentParser):
        def error(self, message):
            raise TuChoi("Tham số sai; dùng --ma <a-z, 0-9, gạch dưới>.")

    try:
        ap = BoPhanTich(description=__doc__.splitlines()[0])
        ap.add_argument("--ma", required=True)
        args = ap.parse_args(argv)
        ket_qua = tao_core_demo(args.ma)
    except (Exception, KeyboardInterrupt):
        print("TU_CHOI: Khong dung duoc Core DEMO; khong ghi de. Can lead kiem moi truong.", file=sys.stderr)
        return 1
    print(json.dumps(ket_qua, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
