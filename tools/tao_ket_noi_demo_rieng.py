#!/usr/bin/env python3
"""Tạo tệp kết nối CRM DEMO trỏ tới CSDL RIÊNG (L0-4b) — chỉ thư viện chuẩn, không kết nối PostgreSQL.

Dùng: python -X utf8 tools/tao_ket_noi_demo_rieng.py --hau-to p8783 --data-root <DataRoot> [--nguon <ket-noi.local.json>]

- Đọc tệp kết nối nguồn (mặc định `<repo chính>/var/web/crm-demo/ket-noi.local.json`) BẰNG CHƯƠNG TRÌNH (`json.load`), chỉ thay TÊN CSDL
  trong cả hai DSN (`app_dsn`, `admin_dsn`) bằng `kho_crm_demo_lt_<hậu tố>`; giữ nguyên mọi phần còn lại của DSN (máy chủ, cổng, login, mật
  khẩu). Ghi `<DataRoot>/crm-demo/ket-noi.local.json`.
- Không tạo CSDL, login hay mật khẩu: `tools/chuan_bi_crm_demo.py` (qua `k2/crm_khoi_dong.chuan_bi`) tự CREATE DATABASE khi CSDL chưa có,
  rồi migrate + seed bằng đúng login quản trị trong DSN; CSDL mới được tạo với chủ là login quản trị, login ứng dụng chỉ nhận quyền qua
  vai trò `app_web` đã có sẵn trong cụm.
- Không in/log DSN, mật khẩu hay nội dung tệp: chỉ in tên CSDL mới và đường dẫn tệp đã ghi. Lỗi chỉ có thông điệp chung.
- Từ chối: ghi đè tệp nguồn; DataRoot nằm trong `var/web`, `var/web-that`, `var/plhn-*` (của repo chính hoặc của worktree); hậu tố sai
  mẫu `[a-z0-9_]`; tệp đích là tệp kết nối TỰ chuẩn bị (không phải bản sao của tệp nguồn, cũng không phải tệp do script này tạo).
Mã thoát: 0 = đã ghi / đã đúng sẵn; 1 = từ chối hoặc lỗi; 2 = chưa có tệp nguồn.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

TIEN_TO_RIENG = "kho_crm_demo_lt_"
TIEN_TO_DEMO = "kho_crm_demo"
_HAU_TO = re.compile(r"^[a-z0-9_]{1,47}$")  # tiền tố 16 ký tự + hậu tố <= 63 (giới hạn tên CSDL PostgreSQL)
_TEN_DB = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
KHOA_TEP = {"phien_ban", "app_dsn", "admin_dsn"}
TEN_TEP = "ket-noi.local.json"


class TuChoi(Exception):
    """Từ chối/lỗi có thông điệp chung (không chứa nội dung tệp kết nối)."""

    def __init__(self, thong_diep: str, ma: int = 1):
        super().__init__(thong_diep)
        self.ma = ma


# ------------------------------------------------------------------ đường dẫn
def _chuan(p) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(str(p))))


def _duoi(p, goc) -> bool:
    a, b = _chuan(p), _chuan(goc)
    return a == b or a.startswith(b.rstrip("\\/") + os.sep)


def tim_repo_chinh(wt: Path) -> Path | None:
    """Repo chính của một worktree: `.git` là tệp `gitdir: …` → commondir → cha của thư mục `.git` chung (không gọi git)."""
    dot_git = wt / ".git"
    if dot_git.is_dir():
        return wt
    if not dot_git.is_file():
        return None
    try:
        dong = dot_git.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, UnicodeError, IndexError):
        return None
    if not dong.startswith("gitdir:"):
        return None
    gd = Path(dong.split(":", 1)[1].strip())
    if not gd.is_absolute():
        gd = wt / gd
    gd = gd.resolve()
    cd_file = gd / "commondir"
    if not cd_file.is_file():
        return None
    try:
        cd = cd_file.read_text(encoding="utf-8").splitlines()[0].strip()
    except (OSError, UnicodeError, IndexError):
        return None
    return (gd / cd).resolve().parent


def kiem_data_root(root: Path, goc_repo: list[Path]) -> None:
    """Từ chối DataRoot nằm trong var/web, var/web-that, var/plhn-* của bất kỳ repo nào trong `goc_repo`."""
    for base in goc_repo:
        var = base / "var"
        for cam in ("web", "web-that"):
            if _duoi(root, var / cam):
                raise TuChoi("DataRoot không được là hoặc nằm trong var\\web / var\\web-that.")
        if _duoi(root, var) and _chuan(root) != _chuan(var):
            dau = Path(_chuan(root)[len(_chuan(var)):].lstrip("\\/")).parts[0]
            if dau.startswith("plhn-"):
                raise TuChoi("DataRoot không được nằm trong var\\plhn-* (kho thật/kho thử).")


# ------------------------------------------------------------------ thay tên CSDL trong một DSN (không in DSN)
def _quet_cap_khoa_gia_tri(s: str) -> list[tuple[str, int, int]]:
    """DSN dạng `khóa=giá_trị …` của libpq: trả [(khóa, đầu, cuối)] — đoạn [đầu:cuối] là NGUYÊN VĂN giá trị (kể cả dấu nháy)."""
    n, i, ket_qua = len(s), 0, []
    while True:
        while i < n and s[i].isspace():
            i += 1
        if i >= n:
            return ket_qua
        k0 = i
        while i < n and s[i] != "=" and not s[i].isspace():
            i += 1
        khoa = s[k0:i]
        while i < n and s[i].isspace():
            i += 1
        if not khoa or i >= n or s[i] != "=":
            raise TuChoi("Chuỗi kết nối không đọc được.")
        i += 1
        while i < n and s[i].isspace():
            i += 1
        v0 = i
        if i < n and s[i] == "'":
            i += 1
            while i < n and s[i] != "'":
                i += 2 if s[i] == "\\" else 1
            if i >= n:
                raise TuChoi("Chuỗi kết nối không đọc được.")
            i += 1
        else:
            while i < n and not s[i].isspace():
                i += 2 if s[i] == "\\" else 1
        ket_qua.append((khoa, v0, min(i, n)))


def _gia_tri(raw: str) -> str:
    if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
        raw = raw[1:-1]
    return re.sub(r"\\(.)", r"\1", raw)


def thay_ten_csdl(dsn: str, moi: str) -> tuple[str, str]:
    """(tên CSDL cũ, DSN mới) — chỉ đổi tên CSDL; mọi byte khác của DSN giữ nguyên. Hỗ trợ `khóa=giá_trị` và `postgresql://…`."""
    if not isinstance(dsn, str) or not dsn.strip():
        raise TuChoi("Tệp kết nối thiếu chuỗi kết nối.")
    if re.match(r"^\s*postgres(ql)?://", dsn, re.I):
        sp = urlsplit(dsn.strip())
        if "dbname" in sp.query.lower():
            raise TuChoi("Chuỗi kết nối dạng URI có dbname trong tham số — không hỗ trợ.")
        cu = unquote(sp.path[1:]) if sp.path.startswith("/") else ""
        if not cu or "/" in cu:
            raise TuChoi("Chuỗi kết nối không ghi rõ tên CSDL.")
        return cu, urlunsplit((sp.scheme, sp.netloc, "/" + moi, sp.query, sp.fragment))
    cap = [c for c in _quet_cap_khoa_gia_tri(dsn) if c[0] == "dbname"]
    if len(cap) != 1:
        raise TuChoi("Chuỗi kết nối phải ghi đúng một tên CSDL (dbname).")
    _, v0, v1 = cap[0]
    return _gia_tri(dsn[v0:v1]), dsn[:v0] + moi + dsn[v1:]


def _ten_csdl(dsn: str) -> str:
    return thay_ten_csdl(dsn, "x")[0]


# ------------------------------------------------------------------ nạp / ghi
def nap_tep(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8-sig") as f:
            v = json.load(f)
    except (OSError, UnicodeError, ValueError):
        raise TuChoi("Tệp kết nối không đọc được.") from None
    if (not isinstance(v, dict) or set(v) - KHOA_TEP or v.get("phien_ban") != 1
            or not isinstance(v.get("app_dsn"), str) or not isinstance(v.get("admin_dsn"), str)):
        raise TuChoi("Tệp kết nối sai định dạng (cần phien_ban 1, app_dsn, admin_dsn).")
    return v


def _bam_byte(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tao_noi_dung(nguon: dict, ten_moi: str) -> dict:
    """Bản sao của nội dung nguồn với tên CSDL của cả hai DSN đổi thành `ten_moi`; kiểm hai DSN cùng một CSDL nguồn kiểu DEMO."""
    cu_app, app = thay_ten_csdl(nguon["app_dsn"], ten_moi)
    cu_adm, adm = thay_ten_csdl(nguon["admin_dsn"], ten_moi)
    if cu_app != cu_adm:
        raise TuChoi("Hai chuỗi kết nối trong tệp nguồn trỏ hai CSDL khác nhau.")
    if not cu_app.startswith(TIEN_TO_DEMO) or not _TEN_DB.match(cu_app):
        raise TuChoi("Tệp nguồn không trỏ CSDL CRM DEMO (tên phải bắt đầu bằng kho_crm_demo).")
    if cu_app == ten_moi:
        raise TuChoi("Tệp nguồn đã trỏ chính CSDL riêng này; chọn hậu tố khác.")
    kq = dict(nguon)
    kq["app_dsn"], kq["admin_dsn"] = app, adm
    # kiểm lại: đọc ngược phải ra đúng tên mới ở cả hai DSN
    if _ten_csdl(kq["app_dsn"]) != ten_moi or _ten_csdl(kq["admin_dsn"]) != ten_moi:
        raise TuChoi("Không thay được tên CSDL trong chuỗi kết nối.")
    return kq


def ghi_tep(dich: Path, noi_dung: dict) -> None:
    dich.parent.mkdir(parents=True, exist_ok=True)
    tam = dich.with_name(dich.name + f".tmp-{os.getpid()}")
    try:
        with open(tam, "w", encoding="utf-8", newline="\n") as f:
            json.dump(noi_dung, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tam, dich)
    finally:
        if tam.exists():
            try:
                tam.unlink()
            except OSError:
                pass


def tao_ket_noi_rieng(hau_to: str, data_root: Path, nguon: Path | None = None, repo_chinh: Path | None = None) -> dict:
    """Trả {"db", "tep", "trang_thai"} (không chứa bí mật). Ném TuChoi khi từ chối."""
    if not isinstance(hau_to, str) or not _HAU_TO.match(hau_to):
        raise TuChoi("Hậu tố chỉ gồm a-z, 0-9, gạch dưới (tối đa 47 ký tự).")
    ten_moi = TIEN_TO_RIENG + hau_to
    wt = Path(__file__).resolve().parents[1]
    chinh = repo_chinh or tim_repo_chinh(wt)
    goc = [wt] + ([chinh] if chinh else [])
    root = Path(data_root).resolve()
    kiem_data_root(root, goc)
    if nguon is None:
        if not chinh:
            raise TuChoi("Không xác định được repo chính để lấy tệp kết nối nguồn; truyền --nguon.")
        nguon = chinh / "var" / "web" / "crm-demo" / TEN_TEP
    nguon = Path(nguon).resolve()
    dich = root / "crm-demo" / TEN_TEP
    if _chuan(dich) == _chuan(nguon):
        raise TuChoi("Tệp đích trùng tệp nguồn — từ chối ghi đè tệp kết nối nguồn.")
    if not nguon.is_file():
        raise TuChoi("Chưa có tệp kết nối nguồn (CSDL DEMO chung chưa được cấu hình).", 2)
    moi = tao_noi_dung(nap_tep(nguon), ten_moi)

    if dich.is_file():
        # chỉ ghi đè bản sao của tệp nguồn hoặc tệp do script này tạo; tệp khác = Anh/root tự chuẩn bị → giữ nguyên
        try:
            hien = nap_tep(dich)
            ten_hien = _ten_csdl(hien["app_dsn"])
        except TuChoi:
            raise TuChoi("Tệp kết nối trong DataRoot không đọc được; không ghi đè.") from None
        if hien == moi:
            return {"db": ten_moi, "tep": str(dich), "trang_thai": "DA_CO"}
        la_cua_ta = ten_hien.startswith(TIEN_TO_RIENG)
        la_ban_sao = _bam_byte(dich) == _bam_byte(nguon)
        if not (la_cua_ta or la_ban_sao):
            raise TuChoi("Tệp kết nối trong DataRoot là tệp tự chuẩn bị (không phải bản sao tệp nguồn); không ghi đè.")
        trang_thai = "DA_CAP_NHAT"
    else:
        trang_thai = "DA_TAO"
    ghi_tep(dich, moi)
    return {"db": ten_moi, "tep": str(dich), "trang_thai": trang_thai}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hau-to", required=True, help="hậu tố [a-z0-9_]; CSDL = kho_crm_demo_lt_<hậu tố>")
    ap.add_argument("--data-root", required=True, type=Path)
    ap.add_argument("--nguon", type=Path, help="tệp kết nối nguồn (mặc định: <repo chính>/var/web/crm-demo/ket-noi.local.json)")
    args = ap.parse_args(argv)
    for luong in (sys.stdout, sys.stderr):  # console cp1252 không in được đường dẫn có chữ Việt → không để lỗi in làm hỏng lệnh sau khi đã ghi
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8", errors="replace")
    try:
        kq = tao_ket_noi_rieng(args.hau_to, args.data_root, args.nguon)
    except TuChoi as exc:
        print("TU_CHOI: " + str(exc))
        print(json.dumps({"loi": str(exc), "ma": exc.ma}, ensure_ascii=True))  # dòng cuối: JSON ASCII cho launcher
        return exc.ma
    except Exception:  # noqa: BLE001 — biên CLI: không in ngoại lệ (có thể chứa nội dung tệp kết nối)
        thong_diep = "Lỗi không xác định khi tạo tệp kết nối riêng."
        print("TU_CHOI: " + thong_diep)
        print(json.dumps({"loi": thong_diep, "ma": 1}, ensure_ascii=True))
        return 1
    print("CSDL rieng: " + kq["db"])
    print("Tep ket noi: " + kq["tep"] + " (" + kq["trang_thai"] + ")")
    print(json.dumps(kq, ensure_ascii=True))  # dòng cuối: JSON ASCII cho launcher (Windows PowerShell 5.1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
