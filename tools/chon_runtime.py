#!/usr/bin/env python3
"""Chọn Python + môi trường con cho app khi bấm nút mở (start-web.ps1 gọi). Chỉ thư viện chuẩn, chạy được bằng bất kỳ Python 3.8+.

INTERFACE runtime app (root/Codex cài sau review; KHÔNG chứa DSN/mật khẩu/token):
  `<DataRoot>/crm-demo/runtime.local.json`
    {"phien_ban": 1,
     "python": "<đường dẫn TUYỆT ĐỐI python.exe của runtime app>",
     "duong_dan_phu_thuoc": ["<thư mục TUYỆT ĐỐI chứa psycopg/openpyxl/tzdata… của runtime app>", ...],
     "thu_muc_khoi_dong": "<thư mục TUYỆT ĐỐI chứa sitecustomize.py (guard giữ file) do root quản lý>"   (tùy chọn)}

Thứ tự ứng viên: -PythonExecutable tường minh (KHÔNG rơi về ứng viên khác) → `python` trong runtime.local.json (KHÔNG rơi về ứng viên
khác) → Python kèm workspace → `python` trên PATH. Mỗi ứng viên được probe THỰC bằng tools/kiem_runtime.py chạy dưới chính nó với
đúng môi trường con: Python ≥ 3.11 + openpyxl = chạy được app; thêm psycopg, không isolated/không bỏ qua biến môi trường, thư mục phụ
thuộc có trong sys.path, guard nạp từ đúng thư mục (nếu cấu hình) = có CRM. Không có ứng viên đủ CRM → vẫn chọn ứng viên chạy được app
nhưng `crm=false` với mã cụ thể (launcher in rõ, bỏ bước CRM) — không âm thầm mất CRM.

Môi trường con (dùng CHUNG cho probe, bước chuẩn bị CRM và server): sao từ môi trường caller, PYTHONPATH = src;phụ thuộc…;khởi động
(không gộp PYTHONPATH riêng của caller để không phụ thuộc môi trường kiểm thử), PYTHONDONTWRITEBYTECODE=1, PYTHONUTF8=1.
In một dòng JSON {ok_app, crm, ma, thong_diep, python, pythonpath, ung_vien[]} và ghi tệp trạng thái mới `<root>/logs/runtime-<UTC>-<pid>.json`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PHIEN_BAN = 1
KHOA = {"phien_ban", "python", "duong_dan_phu_thuoc", "thu_muc_khoi_dong"}
REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "tools" / "kiem_runtime.py"
CREATE_NO_WINDOW = 0x08000000


class LoiRuntime(Exception):
    def __init__(self, ma: str, thong_diep: str):
        super().__init__(thong_diep)
        self.ma = ma


def duong_dan_runtime(root) -> Path:
    return Path(root) / "crm-demo" / "runtime.local.json"


def doc_runtime(root) -> dict | None:
    path = duong_dan_runtime(root)
    if not path.is_file():
        return None
    try:
        v = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise LoiRuntime("RUNTIME_CAU_HINH_SAI", "Tệp runtime.local.json không đọc được.") from None
    if not isinstance(v, dict) or v.get("phien_ban") != PHIEN_BAN or set(v) - KHOA or not isinstance(v.get("python"), str) \
            or not isinstance(v.get("duong_dan_phu_thuoc", []), list) or not all(isinstance(x, str) for x in v.get("duong_dan_phu_thuoc", [])) \
            or not isinstance(v.get("thu_muc_khoi_dong", ""), (str, type(None))):
        raise LoiRuntime("RUNTIME_CAU_HINH_SAI", "runtime.local.json sai định dạng (phien_ban 1, python, duong_dan_phu_thuoc, thu_muc_khoi_dong).")
    py = Path(v["python"])
    if not py.is_absolute() or not py.is_file() or not py.name.lower().startswith("python"):
        raise LoiRuntime("RUNTIME_PYTHON_KHONG_CO", "Python trong runtime.local.json phải là đường dẫn tuyệt đối tới python.exe có thật.")
    deps = [Path(x) for x in v.get("duong_dan_phu_thuoc", [])]
    if any(not d.is_absolute() or not d.is_dir() for d in deps):
        raise LoiRuntime("RUNTIME_PHU_THUOC_KHONG_CO", "Mỗi thư mục phụ thuộc phải là đường dẫn tuyệt đối có thật.")
    kd = Path(v["thu_muc_khoi_dong"]) if v.get("thu_muc_khoi_dong") else None
    if kd and (not kd.is_absolute() or not (kd / "sitecustomize.py").is_file()):
        raise LoiRuntime("RUNTIME_KHOI_DONG_KHONG_CO", "thu_muc_khoi_dong phải là thư mục tuyệt đối chứa sitecustomize.py.")
    return {"python": str(py), "phu_thuoc": [str(d) for d in deps], "khoi_dong": str(kd) if kd else None}


def moi_truong(base: dict, src: Path, phu_thuoc: list[str], khoi_dong: str | None) -> dict:
    env = dict(base)  # không sửa môi trường caller
    env["PYTHONPATH"] = os.pathsep.join([str(src), *phu_thuoc, *([khoi_dong] if khoi_dong else [])])
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    return env


def _chay_that(argv: list[str], env: dict) -> tuple[int, str]:
    kw = {"creationflags": CREATE_NO_WINDOW} if sys.platform == "win32" else {}
    try:
        r = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL, **kw)
    except (OSError, subprocess.TimeoutExpired):
        return -1, ""
    return r.returncode, r.stdout or ""


def phan_loai(kq: dict | None, can_khoi_dong: bool) -> tuple[bool, str | None]:
    """(chạy được app, mã thiếu cho CRM hoặc None nếu đủ)."""
    if not kq:
        return False, "RUNTIME_PROBE_LOI"
    if tuple(kq.get("python") or (0,)) < (3, 11) or not kq.get("openpyxl"):
        return False, "RUNTIME_PYTHON_CU_HOAC_THIEU_OPENPYXL"
    if kq.get("isolated") or kq.get("ignore_env"):
        return True, "RUNTIME_ISOLATED"
    if not kq.get("phu_thuoc_tren_path"):
        return True, "RUNTIME_PHU_THUOC_KHONG_NAP"
    if can_khoi_dong and not kq.get("khoi_dong"):
        return True, "RUNTIME_GUARD_KHONG_NAP"
    if not kq.get("psycopg"):
        return True, "RUNTIME_THIEU_DRIVER"
    return True, None


def ung_vien(explicit: str | None, cfg: dict | None, home: str | None) -> list[tuple[str, str, bool]]:
    """[(nhãn, python, chỉ ứng viên này)]."""
    if explicit:
        return [("tuong_minh", explicit, True)]
    if cfg:
        return [("runtime_local", cfg["python"], True)]
    out = []
    if home:
        bundled = Path(home) / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "python" / "python.exe"
        if bundled.is_file():
            out.append(("kem_workspace", str(bundled), False))
    path_py = shutil.which("python")
    if path_py:
        out.append(("path", path_py, False))
    return out


def chon(root, *, explicit: str | None = None, base_env: dict | None = None, chay=_chay_that, src: Path = REPO / "src") -> dict:
    base_env = dict(os.environ if base_env is None else base_env)
    try:
        cfg = doc_runtime(root)
    except LoiRuntime as exc:
        return {"ok_app": False, "crm": False, "ma": exc.ma, "thong_diep": str(exc), "python": None, "pythonpath": None, "ung_vien": []}
    ds, chay_duoc, xet = ung_vien(explicit, cfg, base_env.get("USERPROFILE") or base_env.get("HOME")), None, []
    for nhan, py, _ in ds:
        deps = cfg["phu_thuoc"] if cfg else []  # cấu hình root áp cho cả Python tường minh (probe phát hiện nếu không tương thích)
        kd = cfg["khoi_dong"] if cfg else None
        env = moi_truong(base_env, src, deps, kd)
        code, out = chay([py, "-X", "utf8", str(PROBE), json.dumps({"phu_thuoc": deps, "khoi_dong": kd})], env)
        try:
            kq = json.loads(out.strip().splitlines()[-1]) if code == 0 and out.strip() else None
        except ValueError:
            kq = None
        app_ok, thieu = phan_loai(kq, bool(kd))
        xet.append({"nguon": nhan, "python": py, "chay_app": app_ok, "thieu_crm": thieu})
        ket = {"ok_app": True, "python": py, "pythonpath": env["PYTHONPATH"], "nguon": nhan, "ung_vien": xet}
        if app_ok and thieu is None:
            return {**ket, "crm": True, "ma": None, "thong_diep": "Runtime đủ cho app và CRM DEMO."}
        if app_ok and chay_duoc is None:
            chay_duoc = {**ket, "crm": False, "ma": thieu}
    if chay_duoc:
        ma = chay_duoc["ma"] if (explicit or cfg) else "RUNTIME_CHUA_CAU_HINH"
        return {**chay_duoc, "ung_vien": xet, "ma": ma,
                "thong_diep": f"App mở được nhưng CRM DEMO chưa dùng được ({ma}): cần runtime app đã cài (crm-demo/runtime.local.json)."}
    ma = "RUNTIME_KHONG_CO_PYTHON" if not ds else "RUNTIME_KHONG_DUNG_DUOC"
    return {"ok_app": False, "crm": False, "ma": ma, "thong_diep": "Không có Python 3.11+ có openpyxl dùng được cho app.", "python": None,
            "pythonpath": None, "ung_vien": xet}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--python")
    args = ap.parse_args(argv)
    kq = chon(args.root.resolve(), explicit=args.python or None, chay=_chay_that)
    kq = {"luc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **kq}
    try:
        logs = args.root.resolve() / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        with open(logs / f"runtime-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{os.getpid()}.json", "x", encoding="utf-8") as f:
            json.dump(kq, f, ensure_ascii=False)
    except OSError:
        pass
    # stdout là JSON MÁY cho Windows PowerShell 5.1 (giải mã bằng codepage console, vd 437): chỉ ASCII, Unicode thoát \uXXXX —
    # ConvertFrom-Json/json.loads phục hồi nguyên đường dẫn có dấu/khoảng trắng. Tệp log UTF-8 ở trên giữ chữ Việt.
    print(json.dumps(kq, ensure_ascii=True))
    return 0 if kq["ok_app"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
