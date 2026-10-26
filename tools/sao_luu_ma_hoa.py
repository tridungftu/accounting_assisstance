"""SL-1: binary pg_dump -> GPG; chỉ ciphertext xuống đĩa, không tự xóa.

CLI: sao-luu --pg-dump ... --gpg ... --homedir ... --fingerprint ...
     --ket-noi ... --goc ... --min-free-bytes <ngân sách dung lượng đã duyệt>
     --bien-ban <biên bản JSONL hiện có của đợt>
     [--vai-tro app|admin] [--timeout 3600]
     giu --goc ... ; chep --nguon ...gpg --sha256 ... --dich ...

30 bản ngày = bản cuối mỗi ngày trong 30 ngày có bản gần nhất; 12 bản
tháng = bản cuối mỗi tháng trong 12 tháng có bản gần nhất (có thể trùng).
Không bao gồm file/roles/globals; chưa xác nhận giải mã/restore (SL-2).
Không truyền stderr hoặc nội dung lỗi chương trình con ra log.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

# Tái dùng helper chuẩn thư viện của repo, không đọc cấu hình khi import.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tao_ket_noi_demo_rieng import (  # noqa: E402
    _gia_tri, _quet_cap_khoa_gia_tri, nap_tep, tim_repo_chinh,
)

REPO = Path(__file__).resolve().parents[1]
_PG = {
    "host": "PGHOST", "hostaddr": "PGHOSTADDR", "port": "PGPORT",
    "user": "PGUSER", "password": "PGPASSWORD", "dbname": "PGDATABASE",
    "sslmode": "PGSSLMODE", "sslrootcert": "PGSSLROOTCERT",
    "sslcert": "PGSSLCERT", "sslkey": "PGSSLKEY",
    "connect_timeout": "PGCONNECT_TIMEOUT", "application_name": "PGAPPNAME",
    "service": "PGSERVICE", "servicefile": "PGSERVICEFILE",
    "passfile": "PGPASSFILE", "options": "PGOPTIONS",
}


class LoiSaoLuu(Exception):
    """Chỉ mang token lỗi cố định; tuyệt đối không gắn lỗi gốc/DSN."""

    def __init__(self, ma: str):
        self.ma = ma
        super().__init__(ma)


def _moi_truong_sach() -> dict:
    # Không chuyển KHO_PG_DSN hoặc bí mật của ứng dụng sang GPG.
    cho_phep = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT",
                "TEMP", "TMP", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA"}
    return {k: v for k, v in os.environ.items() if k.upper() in cho_phep}


def moi_truong_ket_noi(path: Path, vai_tro: str = "admin") -> dict:
    """Đọc qua helper hiện có; chỉ ánh xạ DSN sang env, không connect.

    Dùng bộ quét libpq hiện có cho key=value, urllib chuẩn cho URI.
    Khóa chưa hỗ trợ bị từ chối, không bỏ qua để tránh đổi đích kết nối.
    """
    try:
        if vai_tro not in ("app", "admin"):
            raise ValueError
        dsn = nap_tep(Path(path))[vai_tro + "_dsn"]
        if re.match(r"^postgres(?:ql)?://", dsn):
            u = urlsplit(dsn)
            d = dict(parse_qsl(u.query, keep_blank_values=True, strict_parsing=True))
            for k, v in (("host", u.hostname), ("port", u.port),
                         ("user", unquote(u.username) if u.username else None),
                         ("password", unquote(u.password) if u.password else None),
                         ("dbname", unquote(u.path[1:]) if u.path[1:] else None)):
                if v is not None:
                    d.setdefault(k, str(v))  # query libpq ưu tiên hơn phần URI
            if u.fragment:
                raise ValueError
        else:
            d = {k: _gia_tri(dsn[a:b]) for k, a, b in _quet_cap_khoa_gia_tri(dsn)}
        if set(d) - _PG.keys() or (not d.get("dbname") and not d.get("service")):
            raise ValueError
        env = _moi_truong_sach()
        env.update({_PG[k]: v for k, v in d.items()})
        return env
    except Exception:
        raise LoiSaoLuu("SL_KET_NOI") from None


def _goc_cam() -> tuple[Path, ...]:
    chinh = tim_repo_chinh(REPO)
    return (REPO.resolve(),) + ((chinh.resolve(),) if chinh else ())


def _ngoai_repo(path: Path, goc_cam: tuple[Path, ...] | None = None) -> Path:
    p = Path(path).resolve()
    roots = _goc_cam() if goc_cam is None else tuple(Path(g).resolve() for g in goc_cam)
    if any(p == g or g in p.parents for g in roots):
        raise LoiSaoLuu("SL_DICH_TRONG_REPO")
    return p


def _chuong_trinh(command) -> list[str]:
    # Chuỗi executable cấu hình; sequence chỉ để test Python + script giả.
    cmd = [str(command)] if isinstance(command, (str, Path)) else list(command)
    if not cmd or not shutil.which(cmd[0]):
        raise LoiSaoLuu("SL_THIEU_CHUONG_TRINH")
    return cmd


def _chay(cmd: list[str], env: dict, timeout: float) -> bytes:
    try:
        r = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, env=env, timeout=timeout,
                           check=False)
        if r.returncode:
            raise LoiSaoLuu("SL_KIEM_TRA")
        return r.stdout
    except (OSError, subprocess.TimeoutExpired):
        raise LoiSaoLuu("SL_KIEM_TRA") from None


def _phien_ban(cmd: list[str], env: dict, timeout: float, ten: str) -> str:
    out = _chay(cmd + ["--version"], env, timeout).decode("ascii", errors="ignore")
    # Chỉ trích số từ dòng phiên bản đã nhận diện, không lưu output tùy ý.
    pattern = r"^pg_dump \(PostgreSQL\) (\d+(?:\.\d+){0,3})\b" if ten == "pg_dump" else r"^gpg \(GnuPG\) (\d+(?:\.\d+){0,3})\b"
    m = re.match(pattern, out)
    if not m:
        raise LoiSaoLuu("SL_PHIEN_BAN")
    return m.group(1)


def _kiem_khoa(gpg: list[str], home: Path, fingerprint: str, env: dict, timeout: float) -> str:
    fp = fingerprint.upper()
    if not re.fullmatch(r"[0-9A-F]{40}|[0-9A-F]{64}", fp):
        raise LoiSaoLuu("SL_FINGERPRINT")
    out = _chay(gpg + ["--no-options", "--homedir", str(home), "--batch",
                       "--with-colons", "--fingerprint", "--list-keys", fp], env, timeout)
    primary = False
    for line in out.decode("ascii", errors="ignore").splitlines():
        c = line.split(":")
        if c[0] == "pub":
            primary = len(c) > 11 and c[1] not in ("r", "e", "d", "i") and "e" in c[11].lower()
            if len(c) > 6 and c[6] and (not c[6].isdigit() or (int(c[6]) != 0 and int(c[6]) <= time.time())):
                primary = False
        elif c[0] == "fpr":
            if primary and len(c) > 9 and c[9] == fp:
                return fp
            primary = False  # không nhận fingerprint subkey thay primary ghim
    raise LoiSaoLuu("SL_FINGERPRINT")


def _du_dung_luong(path: Path, min_free_bytes: int) -> None:
    if min_free_bytes <= 0:
        raise LoiSaoLuu("SL_NGAN_SACH_DUNG_LUONG")
    p = path
    while not p.exists():
        p = p.parent
    if shutil.disk_usage(p).free < min_free_bytes:
        raise LoiSaoLuu("SL_THIEU_DUNG_LUONG")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _ong_dan(pg: list[str], gpg: list[str], env_pg: dict, env_gpg: dict,
             partial: Path, timeout: float) -> dict:
    dump = encrypt = None
    start = time.monotonic()
    done = {}
    try:
        with partial.open("xb") as output:
            try:
                dump = subprocess.Popen(pg + ["--format=custom", "--no-password"],
                                        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, env=env_pg)
            except OSError:
                raise LoiSaoLuu("SL_PG_DUMP") from None
            try:
                try:
                    encrypt = subprocess.Popen(gpg, stdin=dump.stdout, stdout=output,
                                               stderr=subprocess.DEVNULL, env=env_gpg)
                except OSError:
                    raise LoiSaoLuu("SL_GPG") from None
            finally:
                dump.stdout.close()  # EOF/BrokenPipe tới producer nếu GPG thoát sớm
            while len(done) < 2:
                elapsed = time.monotonic() - start
                for name, process in (("pg_dump", dump), ("gpg", encrypt)):
                    if name not in done and process.poll() is not None:
                        done[name] = round(elapsed, 6)
                if encrypt.poll() is not None and dump.poll() is None and encrypt.returncode != 0:
                    raise LoiSaoLuu("SL_GPG")
                if elapsed >= timeout:
                    raise LoiSaoLuu("SL_TIMEOUT")
                if len(done) < 2:
                    time.sleep(0.01)
            if encrypt.returncode:
                raise LoiSaoLuu("SL_GPG")
            if dump.returncode:
                raise LoiSaoLuu("SL_PG_DUMP")
            output.flush()
            os.fsync(output.fileno())
        return done
    finally:
        for process in (encrypt, dump):
            if process is not None:
                if process.poll() is None:
                    process.kill()
                process.wait()


def sao_luu(*, pg_dump, gpg, homedir: Path, fingerprint: str, ket_noi: Path,
            goc: Path, bien_ban: Path, min_free_bytes: int,
            vai_tro: str = "admin", timeout: float = 3600,
            thoi_diem: datetime | None = None,
            goc_cam: tuple[Path, ...] | None = None) -> dict:
    """Lỗi giữ nguyên partial; chỉ SHA/công bố sau khi cả hai exit 0.

    goc_cam cho phép tiêm thư mục cấm khi test; None giữ repo hiện hành/chính.
    """
    try:
        start = time.monotonic()
        root = _ngoai_repo(goc, goc_cam)
        home = _ngoai_repo(homedir, goc_cam)
        if not math.isfinite(timeout) or timeout <= 0 or not home.is_dir():
            raise LoiSaoLuu("SL_CAU_HINH")
        pg, gp = _chuong_trinh(pg_dump), _chuong_trinh(gpg)
        env = _moi_truong_sach()
        env_pg = moi_truong_ket_noi(ket_noi, vai_tro)
        _du_dung_luong(root, min_free_bytes)
        versions = {"pg_dump": _phien_ban(pg, env, min(timeout, 30), "pg_dump"),
                    "gpg": _phien_ban(gp, env, min(timeout, 30), "gpg")}
        fp = _kiem_khoa(gp, home, fingerprint, env, min(timeout, 30))
        preflight = time.monotonic() - start
        run_id = (thoi_diem or datetime.now()).strftime("%Y%m%d-%H%M%S")
        root.mkdir(parents=True, exist_ok=True)
        folder = root / run_id
        folder.mkdir()  # độc quyền, trùng giây -> lỗi, không ghi đè
        partial, final = folder / "postgresql.partial.gpg", folder / "postgresql.gpg"
        cmd = gp + ["--no-options", "--homedir", str(home), "--encrypt",
                    "--recipient", fp, "--cipher-algo", "AES256", "--trust-model",
                    "always", "--batch", "--no-tty"]
        durations = _ong_dan(pg, cmd, env_pg, env, partial, timeout)
        start_hash = time.monotonic()
        digest = sha256(partial)
        row = {"ma_lan": run_id, "dung_luong": partial.stat().st_size,
               "sha256": digest, "giay": {"kiem_tra": round(preflight, 6), **durations,
               "sha256": round(time.monotonic() - start_hash, 6)}, "phien_ban": versions,
               "khoi_phuc": "CHUA_KIEM_SL_2"}
        # Thư mục lần chạy thuộc riêng runner; Windows rename từ chối đích có sẵn.
        if final.exists():
            raise LoiSaoLuu("SL_DICH_DA_CO")
        partial.rename(final)
        try:
            with Path(bien_ban).open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
        except OSError:
            # Không xóa; trả ciphertext về partial nếu biên bản không ghi được.
            try:
                final.rename(partial)
            except OSError:
                raise LoiSaoLuu("SL_BIEN_BAN_SAU_CONG_BO") from None
            raise LoiSaoLuu("SL_BIEN_BAN") from None
        return row
    except LoiSaoLuu:
        raise
    except FileExistsError:
        raise LoiSaoLuu("SL_DICH_DA_CO") from None
    except Exception:
        raise LoiSaoLuu("SL_IO") from None


def phan_loai_giu(goc: Path) -> dict:
    """Chỉ xem tên thư mục và bản đã công bố; không đọc/xóa partial."""
    days, months, all_runs = {}, {}, []
    for folder in sorted(Path(goc).iterdir(), reverse=True):
        try:
            when = datetime.strptime(folder.name, "%Y%m%d-%H%M%S")
        except ValueError:
            continue
        final = folder / "postgresql.gpg"
        if folder.is_symlink() or not folder.is_dir() or final.is_symlink() or not final.is_file():
            continue
        all_runs.append(folder.name)
        days.setdefault(when.strftime("%Y%m%d"), folder.name)
        months.setdefault(when.strftime("%Y%m"), folder.name)
    daily, monthly = list(days.values())[:30], list(months.values())[:12]
    keep = set(daily + monthly)
    return {"giu_ngay": daily, "giu_thang": monthly,
            "ngoai_han_de_xuat": [r for r in all_runs if r not in keep],
            "tu_dong_xoa": False}


def chep_ban_ma(nguon: Path, dich: Path, sha_du_kien: str, *,
                goc_cam: tuple[Path, ...] | None = None) -> dict:
    """Đích mới độc quyền; sai SHA/lỗi giữ .partial.gpg để lead kiểm.

    goc_cam cho phép tiêm thư mục cấm khi test; None giữ repo hiện hành/chính.
    """
    try:
        source, target = Path(nguon).resolve(), _ngoai_repo(dich, goc_cam)
        if source.suffix != ".gpg" or ".partial" in source.name or target.suffix != ".gpg" or ".partial" in target.name:
            raise LoiSaoLuu("SL_CHI_BAN_MA")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", sha_du_kien) or sha256(source) != sha_du_kien.lower():
            raise LoiSaoLuu("SL_SHA_NGUON")
        if target.exists():
            raise LoiSaoLuu("SL_DICH_DA_CO")
        _du_dung_luong(target.parent, max(source.stat().st_size, 1))
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.stem + ".partial.gpg")
        with source.open("rb") as src, partial.open("xb") as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)
            dst.flush()
            os.fsync(dst.fileno())
        if sha256(partial) != sha_du_kien.lower():
            raise LoiSaoLuu("SL_SHA_CHEP")
        if target.exists():
            raise LoiSaoLuu("SL_DICH_DA_CO")
        partial.rename(target)
        return {"sha256": sha_du_kien.lower(), "dung_luong": target.stat().st_size}
    except LoiSaoLuu:
        raise
    except FileExistsError:
        raise LoiSaoLuu("SL_DICH_DA_CO") from None
    except Exception:
        raise LoiSaoLuu("SL_CHEP_IO") from None


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise LoiSaoLuu("SL_THAM_SO")  # argparse mặc định có thể echo bí mật nhập nhầm


def main(argv=None) -> int:
    try:
        parser = _Parser(description=__doc__)
        sub = parser.add_subparsers(dest="lenh", required=True, parser_class=_Parser)
        b = sub.add_parser("sao-luu")
        for name in ("pg-dump", "gpg", "homedir", "fingerprint", "ket-noi", "goc", "bien-ban"):
            b.add_argument("--" + name, required=True)
        b.add_argument("--min-free-bytes", type=int, required=True)
        b.add_argument("--timeout", type=float, default=3600)
        b.add_argument("--vai-tro", choices=("app", "admin"), default="admin")
        sub.add_parser("giu").add_argument("--goc", required=True)
        c = sub.add_parser("chep")
        for name in ("nguon", "dich", "sha256"):
            c.add_argument("--" + name, required=True)
        args = vars(parser.parse_args(argv))
        command = args.pop("lenh")
        if command == "sao-luu":
            result = sao_luu(**args)
        elif command == "giu":
            result = phan_loai_giu(Path(args["goc"]))
        else:
            result = chep_ban_ma(Path(args["nguon"]), Path(args["dich"]), args["sha256"])
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"ma_loi": exc.ma if isinstance(exc, LoiSaoLuu) else "SL_IO"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
