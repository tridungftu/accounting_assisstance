"""Chạy test từng module trong tiến trình con riêng, có giới hạn thời gian; ghi ok/ERROR/FAIL/skip/TREO.

Mục đích (L0-1, 24/10/2026): có "nền test" đo được để "xanh" = không thêm lỗi so với nền, và để một test treo
không kéo cả bộ test treo theo (bộ chạy cũ `tests/run_suite.py` chạy tất cả trong một tiến trình).

Dùng:
    python -X utf8 tools/chay_test_theo_module.py <duong_dan_repo> [--ra nen-test.json] [--module test_m1 ...]
                                                  [--gioi-han 180] [--nhat-ky <thu_muc>] [--runtime runtime.local.json]

- <duong_dan_repo>: thư mục gốc có `src\\` và `tests\\` (worktree hiện tại, hay worktree đo nhánh khác).
- Cách tìm test và môi trường giống `test.ps1` → `tests/run_suite.py`: `tests/test_*.py`, PYTHONPATH gồm <repo>/src và <repo>, `-X utf8`,
  engine sqlite (bỏ mọi biến KHO_* và PG* khỏi môi trường tiến trình con để không chạm PostgreSQL).
- Mỗi module chạy một tiến trình con; quá --gioi-han giây (mặc định 180) thì giết cả cây tiến trình, ghi treo=1 và test đang chạy.
- --ra: JSON module -> {ok, error, fail, skip, treo, giay} (+ tong, ids_loi, test_treo, loi_dau). Ghi lại sau mỗi module.
- --runtime: chỉ dùng python và duong_dan_phu_thuoc; đường dẫn tương đối tính từ thư mục chứa file runtime.
- Không sửa gì trong repo được đo; log và thư mục tạm của test nằm trong --nhat-ky (mặc định thư mục tạm hệ điều hành).
- Không dùng dữ liệu thật; không PostgreSQL; không mạng.

Kết thúc: mã 0 nếu không module nào có ERROR/FAIL/treo, ngược lại 1 (mã chỉ để tham khảo; nền được so bằng JSON).
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from collections import Counter
from datetime import datetime
from pathlib import Path

GIOI_HAN_MAC_DINH = 180
TB_TOI_DA = 3000  # ký tự traceback giữ lại cho mỗi lỗi trong nhật ký tiến độ


# --------------------------------------------------------------------------- tiến trình con
class _KetQuaGhiTienDo(unittest.TestResult):
    """Ghi từng sự kiện ra file JSON-lines ngay khi xảy ra, để tiến trình cha còn đọc được nếu con bị giết giữa chừng."""

    def __init__(self, tep):
        super().__init__()
        self._tep = tep

    def _ghi(self, **sk):
        self._tep.write(json.dumps(sk, ensure_ascii=False) + "\n")
        self._tep.flush()

    @staticmethod
    def _dong_cuoi(tb):
        """Dòng đầu của ngoại lệ cuối cùng ('TênLỗi: nội dung'); không có thì dòng cuối. Bỏ các dòng diff của assertEqual."""
        dong = [d for d in tb.strip().splitlines() if d.strip()]
        for d in reversed(dong):
            if re.match(r"^[A-Za-z_][\w.]*(: |$)", d):
                return d.strip()[:300]
        return dong[-1].strip()[:300] if dong else ""

    @staticmethod
    def _id(test):
        return test.id()[:200]

    def startTest(self, test):
        super().startTest(test)
        self._ghi(e="bd", id=self._id(test))

    def addSuccess(self, test):
        super().addSuccess(test)
        self._ghi(e="ok", id=self._id(test))

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._ghi(e="ok", id=self._id(test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._ghi(e="skip", id=self._id(test), ly_do=str(reason)[:200])

    def addError(self, test, err):
        super().addError(test, err)
        tb = self._exc_info_to_string(err, test)
        self._ghi(e="error", id=self._id(test), dong=self._dong_cuoi(tb), tb=tb[-TB_TOI_DA:], tb_dau=tb[:TB_TOI_DA])

    def addFailure(self, test, err):
        super().addFailure(test, err)
        tb = self._exc_info_to_string(err, test)
        self._ghi(e="fail", id=self._id(test), dong=self._dong_cuoi(tb), tb=tb[-TB_TOI_DA:], tb_dau=tb[:TB_TOI_DA])

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._ghi(e="fail", id=self._id(test), dong="unexpected success", tb="", tb_dau="")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is None:
            return
        tb = self._exc_info_to_string(err, test)
        loai = "fail" if issubclass(err[0], test.failureException) else "error"
        self._ghi(e=loai, id=self._id(subtest), dong=self._dong_cuoi(tb), tb=tb[-TB_TOI_DA:], tb_dau=tb[:TB_TOI_DA])


def _chay_con(repo: Path, module: str, tep_tien_do: Path) -> int:
    """Chế độ con: nạp đúng một module test và chạy, ghi tiến độ ra tep_tien_do."""
    # Bỏ thư mục chứa script này (tools/) khỏi sys.path để không che module của repo được đo.
    thu_muc_script = str(Path(__file__).resolve().parent)
    sys.path[:] = [p for p in sys.path if p and str(Path(p).resolve()) != thu_muc_script]
    # Giữ tests/ để nạp tên module ngắn, thêm repo để from tests.xxx hoạt động.
    for p in (repo, repo / "src", repo / "tests"):
        sys.path.insert(0, str(p))
    os.chdir(repo)
    with open(tep_tien_do, "a", encoding="utf-8", buffering=1) as tep:
        kq = _KetQuaGhiTienDo(tep)
        bo = unittest.defaultTestLoader.loadTestsFromName(module)
        kq._ghi(e="tong", n=bo.countTestCases())
        try:
            bo.run(kq)
        finally:
            kq._ghi(e="het")
    return 0


# --------------------------------------------------------------------------- tiến trình cha
def _giet_cay(proc: subprocess.Popen):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=30)
        else:
            import signal
            os.killpg(proc.pid, signal.SIGKILL)
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass


def _doc_runtime(tep: Path) -> tuple[str, tuple[Path, ...]]:
    """Chỉ lấy hai khóa runtime; không nạp cấu hình kết nối hay guard của app."""
    tep = tep.resolve()
    data = json.loads(tep.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("Runtime phải là JSON object.")
    python = data.get("python")
    phu_thuoc = data.get("duong_dan_phu_thuoc")
    if not isinstance(python, str) or not python.strip():
        raise ValueError("Runtime cần khóa python là đường dẫn không rỗng.")
    if not isinstance(phu_thuoc, list) or any(not isinstance(p, str) or not p.strip() for p in phu_thuoc):
        raise ValueError("Runtime cần duong_dan_phu_thuoc là danh sách đường dẫn thư mục.")

    def duong_dan(p: str) -> Path:
        path = Path(p)
        return (path if path.is_absolute() else tep.parent / path).resolve()

    executable = duong_dan(python)
    dependencies = tuple(duong_dan(p) for p in phu_thuoc)
    if not executable.is_file():
        raise ValueError("Không thấy file Python của runtime.")
    if any(not p.is_dir() for p in dependencies):
        raise ValueError("Không thấy thư mục phụ thuộc của runtime.")
    return str(executable), dependencies


def _moi_truong(repo: Path, thu_muc_tam: Path, phu_thuoc: tuple[Path, ...] = ()) -> dict:
    env = {k: v for k, v in os.environ.items() if not (k.upper().startswith("KHO_") or k.upper().startswith("PG"))}
    env["PYTHONPATH"] = os.pathsep.join(str(p) for p in (repo / "src", repo, *phu_thuoc))
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["TEMP"] = env["TMP"] = env["TMPDIR"] = str(thu_muc_tam)
    return env


def _chay_mot_module(repo: Path, module: str, gioi_han: int, thu_muc_nhat_ky: Path, python: str,
                    phu_thuoc: tuple[Path, ...] = ()) -> dict:
    tep_tien_do = thu_muc_nhat_ky / f"{module}.tiendo.jsonl"
    tep_log = thu_muc_nhat_ky / f"{module}.log"
    thu_muc_tam = thu_muc_nhat_ky / "tam" / module
    thu_muc_tam.mkdir(parents=True, exist_ok=True)
    tep_tien_do.write_text("", encoding="utf-8")
    lenh = [python, "-X", "utf8", str(Path(__file__).resolve()), "--con", str(repo), module, str(tep_tien_do)]
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    treo = False
    ma_ra = None
    bat_dau = time.monotonic()
    with open(tep_log, "wb") as log:
        proc = subprocess.Popen(lenh, cwd=str(repo), env=_moi_truong(repo, thu_muc_tam, phu_thuoc), stdin=subprocess.DEVNULL,
                                stdout=log, stderr=subprocess.STDOUT, **kwargs)
        try:
            ma_ra = proc.wait(timeout=gioi_han)
        except subprocess.TimeoutExpired:
            treo = True
            _giet_cay(proc)
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass
    giay = round(time.monotonic() - bat_dau, 1)

    dem = Counter()
    ids_loi, dong_loi, tb_dau_tien = [], [], None
    tong = None
    dang_chay = None
    ket_thuc = False
    for dong in tep_tien_do.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            sk = json.loads(dong)
        except ValueError:
            continue  # dòng cuối bị cắt do bị giết giữa chừng
        e = sk.get("e")
        if e == "tong":
            tong = sk["n"]
        elif e == "bd":
            dang_chay = sk["id"]
        elif e == "het":
            ket_thuc = True
        elif e in ("ok", "skip"):
            dem[e] += 1
            if sk["id"] == dang_chay:
                dang_chay = None
        elif e in ("error", "fail"):
            dem[e] += 1
            ids_loi.append(sk["id"])
            dong_loi.append(sk.get("dong", ""))
            if tb_dau_tien is None:
                tb_dau_tien = sk.get("tb_dau", "")
            if sk["id"] == dang_chay:
                dang_chay = None

    ket = {"ok": dem["ok"], "error": dem["error"], "fail": dem["fail"], "skip": dem["skip"], "treo": 1 if treo else 0, "giay": giay}
    ket["tong"] = tong
    ket["ids_loi"] = ids_loi
    ket["loi_dau"] = dong_loi[0] if dong_loi else ""
    if treo:
        ket["test_treo"] = dang_chay or ""
    elif not ket_thuc:
        # Tiến trình con chết/thoát trước khi chạy hết (nạp module hỏng, sys.exit trong test, lỗi phần mềm...).
        ket["error"] += 1
        ket["ids_loi"].append(f"TIEN_TRINH_CON_CHET(ma={ma_ra}) khi chay {dang_chay or 'nap module'}")
        cuoi_log = [d.strip() for d in tep_log.read_text(encoding="utf-8", errors="replace").splitlines() if d.strip()]
        ket["loi_dau"] = ket["loi_dau"] or (cuoi_log[-1][:300] if cuoi_log else f"tien trinh con thoat ma {ma_ra} truoc khi chay het")
        ket["test_treo"] = ""
    ket["_dong_loi"] = dong_loi  # chỉ dùng để thống kê, bỏ trước khi ghi JSON
    ket["_tb_dau"] = tb_dau_tien or ""
    return ket


def _ghi_json(duong_dan: Path, ket_qua: dict):
    sach = {m: {k: v for k, v in r.items() if not k.startswith("_")} for m, r in sorted(ket_qua.items())}
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    duong_dan.write_text(json.dumps(sach, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _tim_module(repo: Path, mau: list[str]) -> list[str]:
    tat_ca = sorted(p.stem for p in (repo / "tests").glob("test_*.py"))
    if not mau:
        return tat_ca
    chon = []
    for m in tat_ca:
        if any(fnmatch.fnmatch(m, x.removesuffix(".py")) for x in mau):
            chon.append(m)
    thieu = [x for x in mau if not any(fnmatch.fnmatch(m, x.removesuffix(".py")) for m in tat_ca)]
    if thieu:
        print(f"CẢNH BÁO: không thấy module test khớp {thieu}", file=sys.stderr)
    return chon


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "--con":  # nội bộ: python script.py --con <repo> <module> <tep_tien_do>
        return _chay_con(Path(argv[1]).resolve(), argv[2], Path(argv[3]))

    ap = argparse.ArgumentParser(description="Chạy test từng module trong tiến trình riêng, giới hạn thời gian.")
    ap.add_argument("repo", type=Path, help="thư mục gốc repo/worktree cần đo (có src\\ và tests\\)")
    ap.add_argument("--module", action="append", default=[], help="chỉ chạy module này (tên, có thể dùng * ; lặp được). Mặc định: tất cả tests/test_*.py")
    ap.add_argument("--gioi-han", type=int, default=GIOI_HAN_MAC_DINH, help="giây tối đa cho mỗi module (mặc định 180)")
    ap.add_argument("--ra", type=Path, help="ghi JSON kết quả (module -> {ok,error,fail,skip,treo,giay,...}) vào file này")
    ap.add_argument("--nhat-ky", type=Path, help="thư mục log + thư mục tạm của test (mặc định: thư mục tạm hệ điều hành)")
    runtime = ap.add_mutually_exclusive_group()
    runtime.add_argument("--python", default=sys.executable, help="python.exe dùng chạy test (mặc định: chính python đang chạy script)")
    runtime.add_argument("--runtime", type=Path, help="runtime.local.json: dùng python và duong_dan_phu_thuoc, không dùng kết nối PostgreSQL")
    args = ap.parse_args(argv)

    phu_thuoc = ()
    if args.runtime:
        try:
            args.python, phu_thuoc = _doc_runtime(args.runtime)
        except (OSError, ValueError) as exc:
            ap.error(f"Không đọc được runtime: {exc}")

    repo = args.repo.resolve()
    if not (repo / "tests").is_dir() or not (repo / "src").is_dir():
        print(f"Không thấy src\\ hoặc tests\\ trong {repo}", file=sys.stderr)
        return 2
    nhat_ky = (args.nhat_ky or Path(tempfile.gettempdir()) / f"ktt-theo-module-{datetime.now():%Y%m%d-%H%M%S}").resolve()
    nhat_ky.mkdir(parents=True, exist_ok=True)
    modules = _tim_module(repo, args.module)

    print(f"Repo: {repo}")
    try:
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=30).stdout.strip()
        print(f"Commit: {head}")
    except Exception:
        pass
    try:
        phien_ban = subprocess.run([args.python, "-c", "import sys; print(sys.version.split()[0])"], capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        phien_ban = "?"
    print(f"Python: {args.python} ({phien_ban}) · giới hạn {args.gioi_han}s/module · {len(modules)} module · nhật ký: {nhat_ky}", flush=True)

    ket_qua = {}
    bat_dau = time.monotonic()
    for i, m in enumerate(modules, 1):
        r = _chay_mot_module(repo, m, args.gioi_han, nhat_ky, args.python, phu_thuoc)
        ket_qua[m] = r
        co = "TREO" if r["treo"] else ("LOI" if (r["error"] or r["fail"]) else "ok")
        print(f"[{i:>3}/{len(modules)}] {co:<4} {m:<42} ok={r['ok']:<4} ERROR={r['error']:<4} FAIL={r['fail']:<3} skip={r['skip']:<4} {r['giay']:>6}s"
              + (f"  treo-o={r.get('test_treo', '')[:80]}" if r["treo"] else ""), flush=True)
        if args.ra:
            _ghi_json(args.ra, ket_qua)

    tong = Counter()
    for r in ket_qua.values():
        for k in ("ok", "error", "fail", "skip", "treo"):
            tong[k] += r[k]
    print(f"\nTỔNG: ok={tong['ok']} ERROR={tong['error']} FAIL={tong['fail']} skip={tong['skip']} module-TREO={tong['treo']}"
          f" · {len(ket_qua)} module · {round(time.monotonic() - bat_dau)}s")

    nhom = Counter()
    for r in ket_qua.values():
        nhom.update(r["_dong_loi"])
    if nhom:
        print("\nDòng lỗi cuối phổ biến nhất (số lần · dòng):")
        for dong, so in nhom.most_common(15):
            print(f"  {so:>4} · {dong[:160]}")
    if args.ra:
        _ghi_json(args.ra, ket_qua)
        print(f"\nĐã ghi {args.ra}")
    # Giữ bản chi tiết (traceback đầu tiên mỗi module, nhóm dòng lỗi) cạnh nhật ký để dò nguyên nhân gốc.
    (nhat_ky / "chi-tiet.json").write_text(json.dumps(
        {m: {"loi_dau": r["loi_dau"], "tb_dau_tien": r["_tb_dau"], "dong_loi": r["_dong_loi"], "ids_loi": r["ids_loi"], "test_treo": r.get("test_treo", "")}
         for m, r in sorted(ket_qua.items())}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if not (tong["error"] or tong["fail"] or tong["treo"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
