"""Chạy test từng module trong tiến trình con riêng, có giới hạn thời gian; ghi ok/ERROR/FAIL/skip/TREO.

Mục đích (L0-1, 24/10/2026): có "nền test" đo được để "xanh" = không thêm lỗi so với nền, và để một test treo
không kéo cả bộ test treo theo (bộ chạy cũ `tests/run_suite.py` chạy tất cả trong một tiến trình).

Dùng:
    python -X utf8 tools/chay_test_theo_module.py <duong_dan_repo> [--ra nen-test.json] [--module test_m1 ...]
                                                  [--gioi-han 180] [--nhat-ky <thu_muc>] [--runtime runtime.local.json]
                                                  [--pg-demo ket-noi.local.json [--pg-demo-don-so pg-demo-so-ghi.json]]

- <duong_dan_repo>: thư mục gốc có `src\\` và `tests\\` (worktree hiện tại, hay worktree đo nhánh khác).
- Cách tìm test và môi trường giống `test.ps1` → `tests/run_suite.py`: `tests/test_*.py`, PYTHONPATH gồm <repo>/src và <repo>, `-X utf8`,
  engine sqlite (bỏ mọi biến KHO_* và PG* khỏi môi trường tiến trình con để không chạm PostgreSQL).
- Mỗi module chạy một tiến trình con; quá --gioi-han giây (mặc định 180) thì giết cả cây tiến trình, ghi treo=1 và test đang chạy.
- --ra: JSON module -> {ok, error, fail, skip, treo, giay} (+ tong, ids_loi, test_treo, loi_dau). Ghi lại sau mỗi module.
- --runtime: dùng python, duong_dan_phu_thuoc và thu_muc_khoi_dong (provider guard như launcher DEMO); đường dẫn tương đối tính từ tệp runtime.
- Không sửa gì trong repo được đo; log và thư mục tạm của test nằm trong --nhat-ky (mặc định thư mục tạm hệ điều hành).
  Runtime có thu_muc_khoi_dong: tiến trình test nạp guard, bật CODEX_NO_DELETE_FILES=1;
  provider có thể chuyển TEMP sang var\\codex-dieu-phoi\\retained-temp để giữ tệp.
- Không dùng dữ liệu thật; mặc định không PostgreSQL, không mạng.

--pg-demo <ket-noi.local.json> (L0-8, QD-20261025-10): bật các test PostgreSQL trên cụm DEMO loopback. Cần --runtime (hoặc --python) có psycopg.
- Đọc DSN quản trị/ứng dụng BẰNG CHƯƠNG TRÌNH từ tệp kết nối; đặt `KHO_PG_DSN_TEST` (DSN chủ trỏ CSDL `postgres`) CHỈ trong môi trường tiến
  trình con của test. Không in/log/ghi DSN hay mật khẩu; cuối lần chạy quét nhật ký để chắc chắn mật khẩu không lọt vào tệp nào.
- Hook psycopg đăng ký bền TRƯỚC CREATE của test/clone. Sổ `pg-demo-so-ghi.json` gồm mã lần chạy ngẫu nhiên, cụm nguồn host:port,
  ảnh chụp tên CSDL TRƯỚC khi chạy và trạng thái từng mục. Sau MỖI module (kể cả lỗi/treo) và cuối cùng, lớp DROP kiểm tại chỗ:
  tên `kho_test_[a-z0-9_]+`, mục chưa hoàn tất đúng sổ/lần chạy/cụm, tên không có ở ảnh chụp trước; không nhận sở hữu từ chênh lệch danh sách.
  Sau từng DROP kiểm lại pg_database rồi mới ghi bền "đã xóa"; còn thì ghi con_lai_sau_xoa và cảnh báo.
  Tiến trình quản trị PG của bộ chạy không nạp provider khởi động; tiến trình test vẫn giữ guard.
  Không dùng lại mục đã hoàn tất. Không DROP CSDL khác hoặc vai trò.
  DROP không dùng FORCE: CSDL còn phiên kết nối thì chờ rồi bỏ qua và báo.
- Module cần "bản sao DEMO sở hữu" (biến *_CLONE_*): trước module công cụ dựng riêng một CSDL `kho_test_pgd_<hex>` bằng đúng lớp của dự án
  (`k2.crm_khoi_dong.chuan_bi`: migrate + seed DEMO), ghi dấu nguồn/checksum lên `master.he_thong` rồi đặt biến; xóa sau module.
  Họ 03A/03B dùng seed M4 với ma trận kế toán DEMO riêng và nhận hóa đơn fixture qua HoaDonK2; không dựng giả lịch sử trước migration.
- Tiến trình con do test tự sinh (PYTHONPATH=src ghi đè đường dẫn phụ thuộc của runtime) vẫn thấy psycopg nhờ một PYTHONUSERBASE tạm có
  tệp .pth trỏ tới phụ thuộc/provider khởi động và chuyển tiếp user site gốc, giữ hook giữ tệp bên cạnh hook sở hữu PG.
  Probe lỗi/rỗng hoặc user site tạm resolve ngoài nhật ký thì dừng, không ghi .pth.
- Chỉ một lần chạy --pg-demo cùng lúc (khóa tệp trong thư mục tạm). `--pg-demo-don-so <sổ>`: dọn các CSDL còn trong sổ của lần chạy bị chết giữa chừng.

Kết thúc: mã 0 nếu không module nào có ERROR/FAIL/treo, ngược lại 1 (mã chỉ để tham khảo; nền được so bằng JSON).
"""
from __future__ import annotations

import argparse
import contextlib
import fnmatch
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

GIOI_HAN_MAC_DINH = 180
TB_TOI_DA = 3000  # ký tự traceback giữ lại cho mỗi lỗi trong nhật ký tiến độ


class _LocBiMat:
    """Lọc tại biên xuất, kể cả bí mật đứng riêng trong traceback/JSON."""

    def __init__(self, kn=None, tkn=None):
        mau = set()
        for dsn in (kn or {}).values():
            if not isinstance(dsn, str):
                continue
            mau.add(dsn)
            try:
                if re.match(r"^postgres(ql)?://", dsn, re.I):
                    pw = unquote(urlsplit(dsn).password or "")
                else:
                    pw = next((tkn._gia_tri(dsn[a:b]) for k, a, b in tkn._quet_cap_khoa_gia_tri(dsn) if k == "password"), "")
                if pw:
                    mau.update((pw, quote(pw, safe=""), json.dumps(pw, ensure_ascii=True)[1:-1],
                                json.dumps(pw, ensure_ascii=False)[1:-1]))
            except Exception:
                pass  # DSN hỏng vẫn bị lọc bằng mẫu URI/password bên dưới.
        self.mau = sorted(mau - {""}, key=len, reverse=True)

    def text(self, s):
        for m in self.mau:
            s = s.replace(m, "[DA_AN]")
        s = re.sub(r"postgres(?:ql)?://[^\s\"'<>]+", "[DSN_DA_AN]", s, flags=re.I)
        return re.sub(r"\bpassword\s*=\s*(?:'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|[^\s,;]+)",
                      "password=[DA_AN]", s, flags=re.I)

    def data(self, obj):
        if isinstance(obj, str):
            return self.text(obj)
        if isinstance(obj, dict):
            return {self.text(str(k)): self.data(v) for k, v in obj.items()}
        if isinstance(obj, (tuple, list)):
            return [self.data(v) for v in obj]
        return obj


_LOC = _LocBiMat()


class _LuongSach:
    def __init__(self, goc):
        self.goc = goc

    def write(self, s):
        self.goc.write(_LOC.text(s))
        return len(s)

    def flush(self):
        self.goc.flush()

    def __getattr__(self, ten):
        return getattr(self.goc, ten)


# --------------------------------------------------------------------------- tiến trình con
class _KetQuaGhiTienDo(unittest.TestResult):
    """Ghi từng sự kiện ra file JSON-lines ngay khi xảy ra, để tiến trình cha còn đọc được nếu con bị giết giữa chừng."""

    def __init__(self, tep):
        super().__init__()
        self._tep = tep

    def _ghi(self, **sk):
        self._tep.write(json.dumps(_LOC.data(sk), ensure_ascii=False) + "\n")
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
        return _LOC.text(test.id())[:200]

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
        self._ghi(e="skip", id=self._id(test), ly_do=_LOC.text(str(reason))[:200])

    def addError(self, test, err):
        super().addError(test, err)
        tb = _LOC.text(self._exc_info_to_string(err, test))
        self._ghi(e="error", id=self._id(test), dong=self._dong_cuoi(tb), tb=tb[-TB_TOI_DA:], tb_dau=tb[:TB_TOI_DA])

    def addFailure(self, test, err):
        super().addFailure(test, err)
        tb = _LOC.text(self._exc_info_to_string(err, test))
        self._ghi(e="fail", id=self._id(test), dong=self._dong_cuoi(tb), tb=tb[-TB_TOI_DA:], tb_dau=tb[:TB_TOI_DA])

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._ghi(e="fail", id=self._id(test), dong="unexpected success", tb="", tb_dau="")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is None:
            return
        tb = _LOC.text(self._exc_info_to_string(err, test))
        loai = "fail" if issubclass(err[0], test.failureException) else "error"
        self._ghi(e=loai, id=self._id(subtest), dong=self._dong_cuoi(tb), tb=tb[-TB_TOI_DA:], tb_dau=tb[:TB_TOI_DA])


def _chay_con(repo: Path, module: str, tep_tien_do: Path) -> int:
    """Chế độ con: nạp đúng một module test và chạy, ghi tiến độ ra tep_tien_do."""
    if os.environ.get("KHO_PG_DEMO_SO"):
        _bat_bao_ve_con()
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


# --------------------------------------------------------------------------- PostgreSQL DEMO (L0-8)
_RE_TEN_TAM = re.compile(r"^kho_test_[a-z0-9_]{1,54}$")  # tên CSDL tạm của test: tiền tố kho_test_ + [a-z0-9_] (PostgreSQL <= 63 ký tự)
_RE_DB_QUAN_TRI = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
HOST_LOOPBACK = ("127.0.0.1", "localhost", "::1")
KHOA_DSN_DUNG = {"host", "port", "user", "password", "dbname"}
KHOA_DSN_BO_QUA = {"connect_timeout", "application_name", "sslmode"}  # chấp nhận nhưng không đưa vào URI của test
SO_GHI_TEN = "pg-demo-so-ghi.json"


def _cum(p):
    return {"host": p["host"], "port": str(p["port"])}


def _ghi_ben(tep, data):
    tam = tep.with_name(tep.name + ".tmp")
    with tam.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(_LOC.data(data), ensure_ascii=False, indent=1) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tam, tep)


@contextlib.contextmanager
def _khoa_so(tep):
    """Các tiến trình con cùng lần chạy phải cập nhật sổ tuần tự."""
    with tep.with_name(tep.name + ".lock").open("a+b") as f:
        if os.name == "nt":
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)


class _SoHuuPg:
    """Điểm DUY NHẤT thực thi DROP; sổ bền trước CREATE, hoàn tất từng tên sau DROP.

    Sổ cũ thiếu run id/cụm/ảnh chụp bị từ chối. Mục hoàn tất/hủy không được dùng lại.
    """

    def __init__(self, tep, ma_lan_chay, cum):
        self.tep, self.ma, self.cum = Path(tep), ma_lan_chay, cum
        self.doc()

    @classmethod
    def tao_moi(cls, tep, ma, cum, truoc):
        if Path(tep).exists():
            raise ValueError("Sổ lần chạy đã tồn tại; phải dùng thư mục nhật ký mới.")
        _ghi_ben(Path(tep), {"phien_ban": 2, "ma_lan_chay": ma, "cum": cum,
                            "truoc": sorted(truoc), "muc": {}})
        return cls(tep, ma, cum)

    def doc(self):
        d = json.loads(self.tep.read_text(encoding="utf-8"))
        if (d.get("phien_ban") != 2 or not re.fullmatch(r"[a-f0-9]{32}", self.ma or "")
                or d.get("ma_lan_chay") != self.ma or d.get("cum") != self.cum
                or not isinstance(d.get("truoc"), list) or not all(isinstance(x, str) for x in d["truoc"])
                or not isinstance(d.get("muc"), dict)):
            raise ValueError("Sổ sở hữu sai lần chạy/cụm nguồn hoặc thiếu ảnh chụp trước.")
        return d

    def _hop_le(self, d, ten):
        m = d["muc"].get(ten, {})
        return (isinstance(ten, str) and _RE_TEN_TAM.fullmatch(ten) and ten not in d["truoc"]
                and isinstance(m, dict)
                and m.get("ma_lan_chay") == self.ma and m.get("cum") == self.cum
                and m.get("trang_thai") in ("dang_tao", "da_tao", "con_lai_sau_xoa"))

    def dang_ky(self, ten, c):
        self._kiem_cum(c)
        with _khoa_so(self.tep):
            d = self.doc()
            if (not _RE_TEN_TAM.fullmatch(ten) or ten in d["truoc"] or ten in d["muc"]
                    or c.execute("SELECT 1 FROM pg_database WHERE datname = %s", (ten,)).fetchone()):
                raise ValueError("Từ chối CREATE: tên có sẵn/đã dùng hoặc không hợp lệ.")
            d["muc"][ten] = {"ma_lan_chay": self.ma, "cum": self.cum, "trang_thai": "dang_tao"}
            _ghi_ben(self.tep, d)

    def trang_thai(self, ten, trang_thai):
        with _khoa_so(self.tep):
            d = self.doc()
            if not self._hop_le(d, ten):
                raise ValueError("Mục sở hữu đã hoàn tất hoặc không hợp lệ.")
            d["muc"][ten]["trang_thai"] = trang_thai
            _ghi_ben(self.tep, d)

    def xoa(self, c, ten_csdl):
        import psycopg
        from psycopg import sql as S
        self._kiem_cum(c)
        kq = {"da_xoa": [], "khong_co": [], "con_phien": [], "con_lai_sau_xoa": [], "tu_choi": [], "loi": []}
        for ten in ten_csdl:
            with _khoa_so(self.tep):
                d = self.doc()  # kiểm đủ ba điều kiện ngay tại nơi thực thi SQL
                if not self._hop_le(d, ten):
                    kq["tu_choi"].append(str(ten)[:70])
                    continue
                if c.execute("SELECT 1 FROM pg_database WHERE datname = %s AND NOT datistemplate", (ten,)).fetchone() is None:
                    kq["khong_co"].append(ten)
                else:
                    for lan in range(20):
                        try:
                            c.execute(S.SQL("DROP DATABASE {}").format(S.Identifier(ten)))
                            if c.execute("SELECT 1 FROM pg_database WHERE datname = %s", (ten,)).fetchone() is not None:
                                kq["con_lai_sau_xoa"].append(ten)
                                d["muc"][ten]["trang_thai"] = "con_lai_sau_xoa"
                                _ghi_ben(self.tep, d)
                                break
                            kq["da_xoa"].append(ten)
                            break
                        except psycopg.errors.ObjectInUse:
                            time.sleep(1)
                        except psycopg.Error as exc:
                            kq["loi"].append(f"{ten}: {_loi_pg_sach(exc)}")
                            break
                    else:
                        kq["con_phien"].append(ten)
                    if ten not in kq["da_xoa"]:
                        continue
                # Không còn cũng là hoàn tất: không được DROP tên người khác tạo lại.
                d["muc"][ten]["trang_thai"] = "da_xoa"
                _ghi_ben(self.tep, d)
        return kq

    def _kiem_cum(self, c):
        if _cum({"host": c.info.host, "port": c.info.port}) != self.cum:
            raise ValueError("Kết nối khác cụm nguồn trong sổ sở hữu.")


def _gan_loc(kn, tkn):
    global _LOC
    _LOC = _LocBiMat(kn, tkn)
    for ten in ("stdout", "stderr"):
        goc = getattr(sys, ten)
        if not isinstance(goc, _LuongSach):
            setattr(sys, ten, _LuongSach(goc))


def _bat_bao_ve_con():
    """Bắt CREATE/DROP của test hiện hữu qua Cursor chung, không suy sở hữu từ danh sách.

    Không ghi sổ chứa DSN. Mọi CREATE ghi bền trước SQL; DROP của test cũng vào cùng lớp.
    """
    import psycopg
    tkn = _nap_tien_ich_dsn()
    kn = tkn.nap_tep(Path(os.environ["KHO_PG_DEMO_KET_NOI"]))
    _gan_loc(kn, tkn)
    p = _tach_dsn(tkn, kn["admin_dsn"])
    so = _SoHuuPg(Path(os.environ["KHO_PG_DEMO_SO"]), os.environ["KHO_PG_DEMO_MA"], _cum(p))
    # .pth nạp trước sitecustomize; guard có thể bọc execute mà không chép _pg_demo.
    # _chay_con còn nạp tệp này dưới tên module khác: giữ dấu trên psycopg dùng chung,
    # không dựa vào hàm ngoài cùng và không tháo/ghi đè guard khi cài lại.
    khoa_hook = (str(so.tep.resolve()), so.ma, so.cum)
    da_cai = getattr(psycopg, "_ktt_pg_demo_hook", None)
    if da_cai is not None:
        if da_cai[0] != khoa_hook:
            raise ValueError("Hook PostgreSQL DEMO đã thuộc sổ/lần chạy/cụm khác.")
        return
    goc = psycopg.Cursor.execute

    def execute(cur, query, params=None, **kwargs):
        text = query if isinstance(query, str) else query.as_string(cur.connection) if hasattr(query, "as_string") else ""
        m = re.match(r'^\s*(CREATE|DROP)\s+DATABASE\s+(?:"([^"]+)"|([a-zA-Z0-9_]+))', text, re.I)
        if not m:
            return goc(cur, query, params, **kwargs)
        if _cum({"host": cur.connection.info.host, "port": cur.connection.info.port}) != so.cum:
            raise ValueError("Từ chối DDL trên cụm khác sổ sở hữu.")
        ten = m[2] or m[3]

        class Raw:
            info = cur.connection.info

            def execute(self, q, p=None):
                return goc(cur, q, p)

        if m[1].upper() == "DROP":
            kq = so.xoa(Raw(), [ten])
            if kq["tu_choi"] or kq["loi"] or kq["con_phien"] or kq["con_lai_sau_xoa"]:
                raise ValueError("Từ chối/không thể DROP theo sổ sở hữu.")
            return cur
        so.dang_ky(ten, Raw())
        from psycopg import sql as S
        tao = S.SQL("CREATE DATABASE {}").format(S.Identifier(ten)) + S.SQL(text[m.end():])
        try:
            kq = goc(cur, tao, params, **kwargs)
        except psycopg.errors.DuplicateDatabase:
            so.trang_thai(ten, "da_huy")
            raise
        so.trang_thai(ten, "da_tao")
        return kq

    execute._pg_demo = True
    psycopg.Cursor.execute = execute
    psycopg._ktt_pg_demo_hook = (khoa_hook, execute)


def _bat_bao_ve_pth():
    # Python thường chỉ in lỗi .pth rồi tiếp tục: ở đây phải dừng trước khi test chạy.
    try:
        _bat_bao_ve_con()
    except BaseException:
        try:
            sys.stderr.write("Không khởi tạo được bảo vệ sổ PostgreSQL DEMO; dừng tiến trình con.\n")
            sys.stderr.flush()
        finally:
            os._exit(2)

# Họ "bản sao DEMO sở hữu" (biến *_CLONE_*): biến DSN chủ / DSN ứng dụng, biến tên CSDL (nếu có) và mẫu nhận ra module cần họ.
# Mỗi module một bản sao MỚI: nhiều ca cuối bộ thu hồi quyền không đảo ngược ("clone sau đó không dùng lại").
HO_CLONE = {
    "02c": {"dsn": ("KHO_M4_02C_CLONE_DSN", "KHO_M4_02C_CLONE_APP_DSN"), "db": "KHO_M4_02C_CLONE_DB",
            "mau": r"KHO_M4_02C_CLONE_|from tests\.test_m4_02c_pg import (?:\([^)]*\bENV_CHU\b|[^\n(]*\bENV_CHU\b)"},
    "03a": {"dsn": ("KHO_M4_03A_CLONE_DSN", "KHO_M4_03A_CLONE_APP_DSN"), "db": "KHO_M4_03A_CLONE_DB",
            "mau": (r'(?m)^ENV_CHU,\s*ENV_APP,\s*ENV_DB,\s*ENV_NGUON,\s*ENV_M24\s*=\s*\("KHO_M4_03A_CLONE_DSN"'
                    r'|^ENV_DA_AP_DUNG\s*=\s*"KHO_M4_03B_DA_AP_DUNG"')},
    "mc": {"dsn": ("KHO_M4_MC_CLONE_DSN", "KHO_M4_MC_CLONE_APP_DSN"), "db": "KHO_M4_MC_CLONE_DB",
           "mau": r"KHO_M4_MC_CLONE_|from tests\.test_m4_master_dung_chung_pg import (?:\([^)]*\bENV_CHU\b|[^\n(]*\bENV_CHU\b)"},
    "04a": {"dsn": ("KHO_M4_04A_CLONE_DSN", "KHO_M4_04A_CLONE_APP_DSN"), "db": "KHO_M4_04A_CLONE_DB",
            "mau": r"KHO_M4_04A_CLONE_|from tests\.test_m4_request_pg import (?:\([^)]*\bENV_CHU\b|[^\n(]*\bENV_CHU\b)"},
    "g6a": {"dsn": ("KTT_G6A_CLONE_OWNER_DSN", "KTT_G6A_CLONE_APP_DSN"), "db": None,
            "mau": r"KTT_G6A_CLONE_|\btest_crm_kiem_hd\b"},
}
# Họ nhận ra nhưng chưa dựng được: không đặt biến → test skip như cũ.
HO_CHUA_HO_TRO = {}


def _nap_tien_ich_dsn():
    """Nạp tools/tao_ket_noi_demo_rieng.py (L0-4b) theo đường dẫn — dùng lại hàm đọc tệp kết nối và thay tên CSDL trong DSN, không in DSN."""
    import importlib.util
    duong_dan = Path(__file__).resolve().with_name("tao_ket_noi_demo_rieng.py")
    spec = importlib.util.spec_from_file_location("ktt_tao_ket_noi_demo_rieng", duong_dan)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _tach_dsn(tkn, dsn: str) -> dict:
    """DSN (khóa=giá_trị hoặc URI) -> {host, port, user, password, dbname}. Từ chối: host không loopback, khóa lạ (service, hostaddr, options…).
    Lỗi chỉ có thông điệp chung, không chứa nội dung DSN."""
    if re.match(r"^\s*postgres(ql)?://", dsn, re.I):
        sp = urlsplit(dsn.strip())
        d = {"host": sp.hostname or "", "port": str(sp.port or 5432), "user": unquote(sp.username or ""), "password": unquote(sp.password or ""),
             "dbname": unquote(sp.path[1:]) if sp.path.startswith("/") else ""}
        thua = set(re.findall(r"([A-Za-z_]+)=", sp.query)) - KHOA_DSN_BO_QUA
    else:
        d = {k: tkn._gia_tri(dsn[a:b]) for k, a, b in tkn._quet_cap_khoa_gia_tri(dsn)}
        thua = set(d) - KHOA_DSN_DUNG - KHOA_DSN_BO_QUA
        d.setdefault("port", "5432")
    if thua:
        raise ValueError("Chuỗi kết nối có khóa không được hỗ trợ.")
    if d.get("host") not in HOST_LOOPBACK:
        raise ValueError("Chuỗi kết nối phải trỏ loopback (127.0.0.1 / localhost / ::1).")
    if not (d.get("user") and d.get("password") and re.fullmatch(r"[0-9]{1,5}", d.get("port", "")) and _RE_DB_QUAN_TRI.match(d.get("dbname", ""))):
        raise ValueError("Chuỗi kết nối thiếu user/password/port hoặc tên CSDL lạ.")
    return {k: d[k] for k in KHOA_DSN_DUNG}


def _uri(p: dict, dbname: str) -> str:
    """URI postgresql://user:pw@host:port/dbname (user/password mã hóa phần trăm) — dạng test mong đợi: `DSN.rsplit('/', 1)[0] + '/' + tên`."""
    if not _RE_DB_QUAN_TRI.match(dbname):
        raise ValueError("Tên CSDL không hợp lệ.")
    host = f"[{p['host']}]" if ":" in p["host"] else p["host"]
    return f"postgresql://{quote(p['user'], safe='')}:{quote(p['password'], safe='')}@{host}:{p['port']}/{dbname}"


def _sha_sql(dong) -> str:
    import hashlib
    return hashlib.sha256("\n".join(dong).encode("utf-8")).hexdigest()


def _dac_ta_ho(ho: str, db: str) -> tuple[dict, dict]:
    """(hàng ghi vào master.he_thong của bản sao, biến môi trường không bí mật) cho một họ. Giá trị "Root ghim" = định nghĩa SQL hiện tại của
    chính repo được đo (cổng của test so ba nơi: bản sao = định nghĩa = biến). Nguồn gốc (provenance) là mã ngẫu nhiên gắn lần chạy này."""
    ma = "L08-" + uuid.uuid4().hex
    if ho == "02c":
        from kho_tri_thuc.m4.sql_duyet import M0024_M4_DUYET
        return {"m4_02c_clone_provenance": ma}, {"KHO_M4_02C_CLONE_PROVENANCE": ma, "KHO_M4_02C_M24_SHA256": _sha_sql(M0024_M4_DUYET)}
    if ho == "03a":
        from tools.pg_demo_ho_03a import dac_ta
        return dac_ta(ma)
    if ho == "mc":
        from kho_tri_thuc.m4.sql_master_dung_chung import M4_MASTER_DUNG_CHUNG_SQL
        sha = _sha_sql(M4_MASTER_DUNG_CHUNG_SQL)
        return {"m4_mc_clone_provenance": ma, "m4_mc_sql_sha256": sha}, {"KHO_M4_MC_CLONE_PROVENANCE": ma, "KHO_M4_MC_SQL_SHA256": sha}
    if ho == "04a":
        from kho_tri_thuc.m4.sql_request_nhap import M4_REQUEST_NHAP
        sha = _sha_sql(M4_REQUEST_NHAP)
        return {"m4_04a_clone_provenance": ma, "m4_04a_request_sql_sha256": sha}, {"KHO_M4_04A_CLONE_PROVENANCE": ma, "KHO_M4_04A_SQL_SHA256": sha}
    if ho == "g6a":
        return {}, {"KTT_G6A_CLONE_PROVENANCE": f"OWNED_DEMO_CLONE:{db}:{ma}", "KTT_G6A_CLONE_CHO_GHI": "1"}
    raise ValueError("Họ bản sao lạ.")


# ---- việc chạy trong tiến trình con riêng (python của runtime có psycopg): in đúng một dòng JSON ASCII, không bao giờ in DSN
class LoiPgViec(RuntimeError):
    """Việc PostgreSQL ở tiến trình con thất bại; thông điệp chỉ gồm tên việc + loại lỗi/mã do con báo (đã làm sạch)."""


def _loi_pg_sach(exc: BaseException) -> str:
    """Chỉ tên loại lỗi + mã (DataError.code / sqlstate): thông điệp ngoại lệ có thể chứa nội dung chuỗi kết nối."""
    if isinstance(exc, LoiPgViec):
        return _LOC.text(str(exc))
    ma = getattr(exc, "code", None) or getattr(exc, "sqlstate", None) or ""
    return type(exc).__name__ + (f"({ma})" if isinstance(ma, str) and re.fullmatch(r"[A-Za-z0-9_]{1,60}", ma) else "")


def _pg_ket_noi_quan_tri(kn: dict):
    """Kết nối quản trị tới CSDL `postgres` (mặc định) hoặc, nếu không vào được, đúng CSDL ghi trong DSN. Trả (kết nối, tên CSDL)."""
    import psycopg
    from psycopg.conninfo import make_conninfo
    try:
        return psycopg.connect(make_conninfo(kn["admin_dsn"], dbname="postgres"), autocommit=True), "postgres"
    except psycopg.OperationalError:
        c = psycopg.connect(kn["admin_dsn"], autocommit=True)
        return c, c.execute("SELECT current_database()").fetchone()[0]


def _pg_liet_ke(tkn, kn: dict) -> dict:
    _tach_dsn(tkn, kn["admin_dsn"])  # kiểm loopback trước khi kết nối
    c, db_qt = _pg_ket_noi_quan_tri(kn)
    with c:
        csdl = [r[0] for r in c.execute("SELECT datname FROM pg_database ORDER BY 1").fetchall()]
        vai = [r[0] for r in c.execute(r"SELECT rolname FROM pg_roles WHERE rolname ~ '^(ktt|kho)_test_' ORDER BY 1").fetchall()]
    return {"db_quan_tri": db_qt, "csdl": csdl, "vai_tro": vai}


def _pg_tao_clone(tkn, kn: dict, ten: str, ho: str) -> dict:
    """Dựng bản sao DEMO: CREATE DATABASE + migrate + seed DEMO bằng `crm_khoi_dong.chuan_bi` (tiền tố kho_test_), rồi ghi dấu nguồn lên he_thong."""
    if not _RE_TEN_TAM.match(ten) or ho not in HO_CLONE:
        raise ValueError("Tên bản sao hoặc họ không hợp lệ.")
    _tach_dsn(tkn, kn["admin_dsn"])
    _tach_dsn(tkn, kn["app_dsn"])
    import psycopg
    from kho_tri_thuc.k2 import crm_khoi_dong as KD
    # Đặt quyền sở hữu trước khi KD có thể mở/migrate một CSDL cùng tên đã tồn tại.
    _pg_tao_vide(kn, ten)
    _, app = tkn.thay_ten_csdl(kn["app_dsn"], ten)
    _, adm = tkn.thay_ten_csdl(kn["admin_dsn"], ten)
    kq = KD.chuan_bi({"app_dsn": app, "admin_dsn": adm}, tien_to=KD.TIEN_TO_DB_KIEM_THU)
    he, env = _dac_ta_ho(ho, ten)
    if ho == "03a":
        from tools.pg_demo_ho_03a import dung_du_lieu
        env.update(dung_du_lieu(adm, app, ten))
    if he:
        with psycopg.connect(KD.chuan_hoa_dsn(adm, KD.TIEN_TO_DB_KIEM_THU)["conninfo"], autocommit=True) as c:
            for khoa, gia_tri in he.items():
                c.execute("INSERT INTO master.he_thong (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING", (khoa, gia_tri))
    return {"db": ten, "ho": ho, "env": env, "schema": kq.get("schema_sau")}


def _pg_xoa(tkn, kn: dict, tep_so: Path, ma: str, ten_csdl: list[str]) -> dict:
    p = _tach_dsn(tkn, kn["admin_dsn"])
    so = _SoHuuPg(tep_so, ma, _cum(p))  # từ chối sổ khác cụm trước cả kết nối
    c, _ = _pg_ket_noi_quan_tri(kn)
    with c:
        return so.xoa(c, ten_csdl)


def _pg_tao_vide(kn, ten):
    from psycopg import sql as S
    c, _ = _pg_ket_noi_quan_tri(kn)
    with c:
        c.execute(S.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(S.Identifier(ten)))
    return {"db": ten}


def _chay_viec_pg(a: list[str]) -> int:
    """Chế độ con nội bộ: python script.py --pg <viec> <tep_ket_noi> <repo> [tham số…]. Kết quả: một dòng JSON ASCII ở cuối stdout."""
    viec, tep_kn, repo = a[0], Path(a[1]), Path(a[2]).resolve()
    tkn = _nap_tien_ich_dsn()  # nạp TRƯỚC khi bỏ thư mục tools khỏi sys.path
    thu_muc_script = str(Path(__file__).resolve().parent)
    sys.path[:] = [p for p in sys.path if p and str(Path(p).resolve()) != thu_muc_script]
    for p in (repo, repo / "src"):
        sys.path.insert(0, str(p))
    try:
        kn = tkn.nap_tep(tep_kn)
        _gan_loc(kn, tkn)
        if viec in ("tao-clone", "tao-vide"):
            _bat_bao_ve_con()
        if viec == "liet-ke":
            kq = _pg_liet_ke(tkn, kn)
        elif viec == "tao-clone":
            kq = _pg_tao_clone(tkn, kn, a[3], a[4])
        elif viec == "xoa":
            if len(a) < 6:
                raise ValueError("DROP cần sổ sở hữu và mã lần chạy.")
            kq = _pg_xoa(tkn, kn, Path(a[3]), a[4], a[5:])
        elif viec == "tao-vide":
            kq = _pg_tao_vide(kn, a[3])
        else:
            raise ValueError("Việc lạ.")
        print(json.dumps({"ok": True, **kq}, ensure_ascii=True))
        return 0
    except Exception as exc:  # noqa: BLE001 — biên tiến trình con: chỉ in loại lỗi
        print(json.dumps({"ok": False, "loi": _loi_pg_sach(exc)}, ensure_ascii=True))
        return 1


# ---- phía cha
def _khoa_loai_tru_pg():
    """Khóa tệp (tự nhả khi tiến trình chết) giữa các lần chạy --pg-demo."""
    f = open(Path(tempfile.gettempdir()) / "ktt-pg-demo-test.lock", "a+b")
    try:
        if os.name == "nt":
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        raise RuntimeError("Đang có một lần chạy --pg-demo khác trên máy này; chờ nó xong rồi chạy lại.") from None
    return f


class _PgDemo:
    """Quản lý CSDL tạm qua sổ sở hữu trên cụm DEMO; không ghi/in DSN."""

    def __init__(self, tep_ket_noi: Path, python: str, phu_thuoc: tuple, repo: Path, nhat_ky: Path):
        self.tep, self.python, self.phu_thuoc, self.repo = tep_ket_noi.resolve(), python, phu_thuoc, repo
        self.thu_muc_tam = nhat_ky / "tam" / "_pg"
        self.thu_muc_tam.mkdir(parents=True, exist_ok=True)
        self.so = nhat_ky / SO_GHI_TEN
        tkn = _nap_tien_ich_dsn()
        try:
            kn = tkn.nap_tep(self.tep)
            _gan_loc(kn, tkn)
            self.admin, self.app = _tach_dsn(tkn, kn["admin_dsn"]), _tach_dsn(tkn, kn["app_dsn"])
            if _cum(self.admin) != _cum(self.app):
                raise ValueError("DSN quản trị và ứng dụng phải cùng cụm.")
        except Exception as exc:  # noqa: BLE001 — không để thông điệp (có thể chứa DSN) lọt ra
            raise ValueError(f"Không đọc được tệp kết nối PostgreSQL DEMO ({_loi_pg_sach(exc)}).") from None
        self.bi_mat = [self.admin["password"], self.app["password"]]
        self.ma = uuid.uuid4().hex
        self.cum = _cum(self.admin)
        self.nhat_ky = nhat_ky.resolve()
        self.so_huu = None
        self.khoa = None
        self.db_qt = "postgres"
        self.truoc: set[str] = set()
        self.vai_truoc: set[str] = set()
        self.da_tao: list[str] = []
        self.da_xoa: list[str] = []
        self.chua_xoa: dict[str, str] = {}
        self.canh_bao: list[str] = []
        self.chua_ho_tro: set[str] = set()
        self.vai_moi: list[str] = []  # vai trò test để lại (chỉ ghi sổ để Anh/lead quyết dọn; công cụ KHÔNG xóa vai trò)
        self.env_chung: dict = {}

    # -- gọi việc ở tiến trình con
    def _goi(self, viec: str, *tham_so: str, timeout: int = 900) -> dict:
        lenh = [self.python, "-X", "utf8", str(Path(__file__).resolve()), "--pg", viec, str(self.tep), str(self.repo), *tham_so]
        # QD-20261025-10: bộ chạy được DROP đúng CSDL nó sở hữu. Chỉ tiến trình
        # quản trị này bỏ provider khởi động, kể cả provider .pth ở user site.
        deps = tuple(p for p in self.phu_thuoc if not (p / "sitecustomize.py").is_file()
                     and not (p / "codex_no_delete_guard.py").is_file())
        env = _moi_truong(self.repo, self.thu_muc_tam, deps, self._env_so())
        env["PYTHONPATH"] = os.pathsep.join(str(p) for p in dict.fromkeys((self.repo / "src", self.repo, *deps)))
        env["PYTHONNOUSERSITE"] = "1"
        r = subprocess.run(lenh, cwd=str(self.repo), env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        dong = [d for d in _LOC.text(r.stdout).splitlines() if d.strip()]
        try:
            kq = json.loads(dong[-1])
        except (IndexError, ValueError):
            raise LoiPgViec(f"{viec}: tiến trình con thoát mã {r.returncode} không có kết quả") from None
        if not kq.get("ok"):
            raise LoiPgViec(f"{viec}: {str(kq.get('loi', 'lỗi'))[:120]}")
        return kq

    def _env_so(self):
        return {"KHO_PG_DEMO_SO": str(self.so), "KHO_PG_DEMO_MA": self.ma,
                "KHO_PG_DEMO_KET_NOI": str(self.tep)}

    def _doc_so(self):
        d = self.so_huu.doc()
        self.da_tao = list(d["muc"])
        self.da_xoa = [t for t, m in d["muc"].items() if m["trang_thai"] == "da_xoa"]
        return d

    def _ghi_so(self):
        with _khoa_so(self.so):
            d = self._doc_so()
            d.update(vai_tro_test_de_lai=self.vai_moi, canh_bao=self.canh_bao)
            _ghi_ben(self.so, d)

    def _site_phu_thuoc(self) -> str:
        """Nhiều test tự sinh tiến trình con với PYTHONPATH=src (ghi đè đường dẫn phụ thuộc của runtime) nên không thấy psycopg (lỗi PG_DRIVER).
        Cho python thấy thư mục phụ thuộc qua "user site" của một PYTHONUSERBASE tạm (tệp .pth) — PYTHONPATH bị ghi đè không ảnh hưởng.
        Chỉ ghi trong thư mục nhật ký; không đụng runtime."""
        co_so = self.thu_muc_tam.parent / "site-phu-thuoc"
        probe = subprocess.run([self.python, "-c", "import site; print(site.getusersitepackages())"], capture_output=True, text=True, timeout=60,
                               env={**_moi_truong(self.repo, self.thu_muc_tam, self.phu_thuoc), "PYTHONUSERBASE": str(co_so)})
        if probe.returncode != 0 or not probe.stdout.strip():
            raise RuntimeError("Probe user site lỗi hoặc stdout rỗng; không ghi .pth.")
        thu_muc = Path(probe.stdout.strip()).resolve()
        if not thu_muc.is_relative_to(self.nhat_ky) or thu_muc == self.nhat_ky:
            raise RuntimeError("User site nằm ngoài thư mục nhật ký lần chạy; không ghi .pth.")
        thu_muc.mkdir(parents=True, exist_ok=True)
        # Bọc cả bước nạp tệp: lỗi import trong .pth thường chỉ được Python in rồi bỏ qua.
        # Đường dẫn tuyệt đối giữ đúng phiên bản bảo vệ khi repo được đo là worktree cũ.
        nap = ("try:\n"
               " import importlib.util, sys\n"
               f" s = importlib.util.spec_from_file_location('_ktt_pg_demo_bao_ve', {str(Path(__file__).resolve())!r})\n"
               " m = importlib.util.module_from_spec(s)\n"
               " sys.modules[s.name] = m\n"
               " s.loader.exec_module(m)\n"
               " m._bat_bao_ve_pth()\n"
               "except BaseException:\n"
               " os._exit(2)\n")
        dong = [str(p) for p in dict.fromkeys((*self.phu_thuoc, *_duong_khoi_dong()))] + [
                f"import os; os.environ.get('KHO_PG_DEMO_SO') and exec({nap!r})"]
        # User base tạm thay thế user base của caller: chuyển tiếp provider .pth
        # ban đầu, không chép/vá guard. Host lọc KHO_* vẫn cần hook giữ tệp này.
        cu = subprocess.run([self.python, "-c", "import site; print(site.getusersitepackages())"],
                            capture_output=True, text=True, timeout=60,
                            env=_moi_truong(self.repo, self.thu_muc_tam, self.phu_thuoc))
        if cu.returncode != 0 or not cu.stdout.strip():
            raise RuntimeError("Probe user site gốc lỗi hoặc rỗng; không ghi .pth.")
        site_cu = Path(cu.stdout.strip()).resolve()
        if site_cu != thu_muc:
            nap_cu = ("try:\n import site\n"
                      f" site.addsitedir({str(site_cu)!r})\n"
                      "except BaseException:\n os._exit(2)\n")
            # Phụ thuộc runtime vẫn đứng trước các package của user site gốc.
            dong.insert(len(dong) - 1, f"import os; exec({nap_cu!r})")
        (thu_muc / "ktt-phu-thuoc.pth").write_text(_LOC.text("\n".join(dong) + "\n"), encoding="utf-8")
        return str(co_so)

    def khoi_dong(self):
        self.khoa = _khoa_loai_tru_pg()
        kq = self._goi("liet-ke")
        self.db_qt, self.truoc, self.vai_truoc = kq["db_quan_tri"], set(kq["csdl"]), set(kq["vai_tro"])
        self.so_huu = _SoHuuPg.tao_moi(self.so, self.ma, self.cum, self.truoc)
        self.env_chung = {"KHO_PG_DSN_TEST": _uri(self.admin, self.db_qt), **self._env_so()}
        self.env_chung["PYTHONUSERBASE"] = self._site_phu_thuoc()
        self._ghi_so()
        n_tam = sum(1 for d in self.truoc if _RE_TEN_TAM.match(d))
        print(f"[pg-demo] cụm DEMO loopback: {len(self.truoc)} CSDL trước khi chạy (trong đó {n_tam} kho_test_* có sẵn — không đụng), "
              f"{len(self.vai_truoc)} vai trò ktt_test_/kho_test_* có sẵn; sổ ghi: {self.so}", flush=True)

    # -- bản sao DEMO cho module cần
    def ho_cua(self, noi_dung: str) -> list[str]:
        for ma, mau in HO_CHUA_HO_TRO.items():
            if re.search(mau, noi_dung):
                self.chua_ho_tro.add(ma)
        return [ma for ma, h in HO_CLONE.items() if re.search(h["mau"], noi_dung)]

    def dung_clone(self, ho: str) -> dict:
        """Dựng bản sao cho một họ; trả {env, db}. Tên được ghi vào sổ TRƯỚC khi tạo (chết giữa chừng vẫn dọn được)."""
        ten = "kho_test_pgd_" + uuid.uuid4().hex[:12]
        kq = self._goi("tao-clone", ten, ho, timeout=1500)
        spec = HO_CLONE[ho]
        env = dict(kq["env"])
        env[spec["dsn"][0]] = _uri(self.admin, ten)
        env[spec["dsn"][1]] = _uri(self.app, ten)
        if spec["db"]:
            env[spec["db"]] = ten
        return {"env": env, "db": ten}

    # -- dọn
    def don(self) -> dict:
        """Chỉ DROP mục chưa hoàn tất của sổ; CSDL lạ mới chỉ được quan sát."""
        kq = self._goi("liet-ke")
        hien = set(kq["csdl"])
        moi = sorted(d for d in hien - self.truoc if _RE_TEN_TAM.match(d))
        la = sorted(d for d in hien - self.truoc if not _RE_TEN_TAM.match(d))
        mat = sorted(self.truoc - hien)
        for d in la:
            self._canh_bao(f"CSDL không phải kho_test_* xuất hiện mới (không đụng): {d}")
        for d in mat:
            self._canh_bao(f"CSDL có sẵn biến mất (không phải do công cụ này): {d}")
        d = self._doc_so()
        can_xoa = [t for t in d["muc"] if self.so_huu._hop_le(d, t)]
        dem = {"moi": len(moi), "da_xoa": 0, "con_phien": 0, "con_lai_sau_xoa": 0}
        if can_xoa:
            xk = self._goi("xoa", str(self.so), self.ma, *can_xoa)
            self._doc_so()
            dem["da_xoa"] = len(xk["da_xoa"])
            dem["con_phien"] = len(xk["con_phien"])
            dem["con_lai_sau_xoa"] = len(xk["con_lai_sau_xoa"])
            for d in xk["da_xoa"] + xk["khong_co"]:
                self.chua_xoa.pop(d, None)
            for d in xk["con_phien"]:
                self.chua_xoa[d] = "còn phiên kết nối"
            for d in xk["con_lai_sau_xoa"]:
                self.chua_xoa[d] = "còn trong pg_database sau DROP"
                self._canh_bao(f"CSDL còn lại sau DROP: {d}")
            for d in xk["loi"] + xk["tu_choi"]:
                self._canh_bao(f"không xóa được: {d}")
        self._ghi_so()
        return dem

    def _canh_bao(self, thong_diep: str):
        if thong_diep not in self.canh_bao:
            self.canh_bao.append(thong_diep)

    def ket_thuc(self, thu_muc_quet: list[Path]) -> dict:
        """Dọn lần cuối (thử lại tối đa 3 lần), kiểm không sót, kiểm các CSDL khác không đổi, quét rò rỉ mật khẩu. Không ném lỗi."""
        tong = {}
        try:
            for lan in range(3):
                self.don()
                if not self.chua_xoa:
                    break
                time.sleep(5)
            kq = self._goi("liet-ke")
            hien = set(kq["csdl"])
            d = self._doc_so()
            sot = sorted(t for t in hien if self.so_huu._hop_le(d, t))
            tam_khac = sorted(t for t in hien - self.truoc if _RE_TEN_TAM.fullmatch(t) and t not in d["muc"])
            khac_moi = sorted(d for d in hien - self.truoc if not _RE_TEN_TAM.match(d))
            mat = sorted(self.truoc - hien)
            vai_moi = sorted(set(kq["vai_tro"]) - self.vai_truoc)
            self.vai_moi = vai_moi
            tong = {"truoc": len(self.truoc), "sau": len(hien), "tao_trong_lan_chay": len(set(self.da_tao) | set(self.da_xoa)), "da_xoa": len(set(self.da_xoa)),
                    "sot": sot, "csdl_tam_khong_thuoc_so": tam_khac, "csdl_khac_moi": khac_moi, "csdl_co_san_mat": mat,
                    "vai_tro_moi_khong_xoa": len(vai_moi), "canh_bao": self.canh_bao}
        except Exception as exc:  # noqa: BLE001
            tong = {"loi_don": _loi_pg_sach(exc), "sot_theo_so": sorted(set(self.da_tao) - set(self.da_xoa)), "canh_bao": self.canh_bao}
        tong["ro_ri_mat_khau_so_tep"] = self.quet_ro_ri(thu_muc_quet)
        self._ghi_so()
        return tong

    def quet_ro_ri(self, goc: list[Path]) -> int:
        """Đếm tệp trong các thư mục/tệp `goc` có chứa mật khẩu (dạng thô hoặc mã hóa phần trăm). Chỉ trả số, không in gì khác."""
        mau = [m.encode("utf-8") for b in self.bi_mat for m in {b, quote(b, safe="")}]
        dem = 0
        for g in goc:
            tep = [g] if g.is_file() else sorted(p for p in g.rglob("*") if p.is_file()) if g.is_dir() else []
            for p in tep:
                try:
                    raw = p.read_bytes()
                except OSError:
                    continue
                if any(m in raw for m in mau):
                    dem += 1
        return dem


# --------------------------------------------------------------------------- tiến trình cha
def _gan_job_windows(proc: subprocess.Popen):
    """Giữ handle Job riêng cho đúng cây con; sandbox có thể cấm taskkill."""
    if os.name != "nt" or not isinstance(proc._handle, int):
        return None
    import ctypes
    from ctypes import wintypes as W
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateJobObjectW.argtypes, k.CreateJobObjectW.restype = (ctypes.c_void_p, W.LPCWSTR), W.HANDLE
    k.AssignProcessToJobObject.argtypes, k.AssignProcessToJobObject.restype = (W.HANDLE, W.HANDLE), W.BOOL
    k.TerminateJobObject.argtypes, k.TerminateJobObject.restype = (W.HANDLE, W.UINT), W.BOOL
    k.CloseHandle.argtypes, k.CloseHandle.restype = (W.HANDLE,), W.BOOL
    job = k.CreateJobObjectW(None, None)
    if not job:
        return None
    if not k.AssignProcessToJobObject(job, int(proc._handle)):
        k.CloseHandle(job)
        return None  # taskkill vẫn là đường dự phòng nếu Windows cấm Job lồng nhau.
    return k, job


def _giet_cay(proc: subprocess.Popen):
    try:
        if os.name == "nt":
            job = proc.__dict__.get("_job_windows")
            if not job or not job[0].TerminateJobObject(job[1], 1):
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=3)
        else:
            import signal
            os.killpg(proc.pid, signal.SIGKILL)
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass


def _doc_log_con(ong, tep_log: Path, dung: threading.Event, loc: _LocBiMat):
    """Chỉ luồng nền chờ EOF; luồng điều phối luôn có thể bỏ luồng này sau hạn.

    Luồng giữ riêng bộ đệm và tệp log; mọi lần ghi đều kiểm tra tín hiệu dừng.
    """
    # Khi ghi theo dòng, bí mật chứa xuống dòng phải che cả các phần riêng lẻ.
    manh = sorted({p for m in loc.mau if "\n" in m or "\r" in m for p in m.splitlines() if p},
                  key=len, reverse=True)
    try:
        with io.BufferedReader(ong) as doc, tep_log.open("w", encoding="utf-8") as log:
            for dong in doc:
                if dung.is_set():
                    break
                sach = loc.text(dong.decode("utf-8", errors="replace"))
                for p in manh:
                    sach = sach.replace(p, "[DA_AN]")
                log.write(sach)
                log.flush()
    except (OSError, ValueError):
        pass  # Ống bị đóng khi hết hạn; không in dữ liệu chưa lọc ra stderr.


def _doc_runtime(tep: Path) -> tuple[str, tuple[Path, ...]]:
    """Lấy runtime và đường khởi động guard như launcher; không đọc cấu hình kết nối."""
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
    khoi_dong = data.get("thu_muc_khoi_dong")
    if khoi_dong is not None:
        if not isinstance(khoi_dong, str) or not khoi_dong.strip():
            raise ValueError("thu_muc_khoi_dong cần là đường dẫn không rỗng.")
        startup = duong_dan(khoi_dong)
        if not (startup / "sitecustomize.py").is_file():
            raise ValueError("Không thấy sitecustomize.py trong thu_muc_khoi_dong.")
        dependencies += (startup,)
    if not executable.is_file():
        raise ValueError("Không thấy file Python của runtime.")
    if any(not p.is_dir() for p in dependencies):
        raise ValueError("Không thấy thư mục phụ thuộc của runtime.")
    return str(executable), dependencies


def _duong_khoi_dong() -> tuple[Path, ...]:
    # Giữ provider khởi động của caller, không kéo src của worktree khác vào test.
    startup = [Path(p).resolve() for p in os.environ.get("PYTHONPATH", "").split(os.pathsep)
               if p and (Path(p) / "sitecustomize.py").is_file()
               and (Path(p) / "codex_no_delete_guard.py").is_file()]
    site_tep = getattr(sys.modules.get("sitecustomize"), "__file__", None)
    if site_tep and (Path(site_tep).resolve().parent / "codex_no_delete_guard.py").is_file():
        startup.append(Path(site_tep).resolve().parent)
    return tuple(dict.fromkeys(startup))


def _moi_truong(repo: Path, thu_muc_tam: Path, phu_thuoc: tuple[Path, ...] = (), them: dict | None = None) -> dict:
    env = {k: v for k, v in os.environ.items() if not (k.upper().startswith("KHO_") or k.upper().startswith("PG"))}
    env.update(them or {})  # --pg-demo: KHO_PG_DSN_TEST và biến bản sao DEMO — chỉ vào tiến trình con của test, không in/ghi
    duong = dict.fromkeys((repo / "src", repo, *phu_thuoc, *_duong_khoi_dong()))
    env["PYTHONPATH"] = os.pathsep.join(str(p) for p in duong)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["TEMP"] = env["TMP"] = env["TMPDIR"] = str(thu_muc_tam)
    return env


def _chay_mot_module(repo: Path, module: str, gioi_han: int, thu_muc_nhat_ky: Path, python: str,
                    phu_thuoc: tuple[Path, ...] = (), them_env: dict | None = None) -> dict:
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
    tep_log.write_text("", encoding="utf-8")
    proc = subprocess.Popen(lenh, cwd=str(repo), env=_moi_truong(repo, thu_muc_tam, phu_thuoc, them_env), stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, **kwargs)
    proc._job_windows = _gan_job_windows(proc)
    dung = threading.Event()
    doc = threading.Thread(target=_doc_log_con, args=(proc.stdout, tep_log, dung, _LOC), daemon=True)
    doc.start()
    try:
        ma_ra = proc.wait(timeout=gioi_han)
    except subprocess.TimeoutExpired:
        treo = True
        _giet_cay(proc)
        try:
            ma_ra = proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
    finally:
        # Kể cả con đã thoát, cháu có thể còn giữ stdout. Không chờ EOF vô hạn.
        doc.join(timeout=2)
        dung.set()
        if doc.is_alive():
            # Windows CRT có thể khóa cả FileIO.close khi read đang chờ trên pipe.
            # Yêu cầu đóng bằng luồng daemon riêng, không kéo dài hạn của module.
            threading.Thread(target=proc.stdout.close, daemon=True).start()
        else:
            proc.stdout.close()
        if proc._job_windows:
            proc._job_windows[0].CloseHandle(proc._job_windows[1])
            proc._job_windows = None
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
    duong_dan.write_text(json.dumps(_LOC.data(sach), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


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


def _chuan_bi_pg_module(pg: "_PgDemo", repo: Path, module: str) -> tuple[dict, dict]:
    """Môi trường PostgreSQL cho một module: KHO_PG_DSN_TEST + (nếu module cần) bản sao DEMO mới của từng họ. Dựng lỗi -> module chạy không có biến
    của họ đó (test skip/NOT_VERIFIED) và lỗi được ghi vào kết quả; không dừng cả bộ."""
    tep = repo / "tests" / f"{module}.py"
    try:
        noi_dung = tep.read_text(encoding="utf-8", errors="replace")
    except OSError:
        noi_dung = ""
    env, ho_dung, loi = dict(pg.env_chung), [], []
    if module in ("test_ket_noi", "test_pg_schema"):
        ten = "kho_test_pgd_" + uuid.uuid4().hex
        pg._goi("tao-vide", ten)
        env["KHO_PG_DEMO_DB"] = ten
    for ho in pg.ho_cua(noi_dung):
        try:
            kq = pg.dung_clone(ho)
            env.update(kq["env"])
            ho_dung.append(ho)
        except Exception as exc:  # noqa: BLE001
            loi.append(f"{ho}: {_loi_pg_sach(exc)}")
    thong_tin = {"ho": ho_dung}
    if loi:
        thong_tin["loi_dung_ban_sao"] = loi
    return env, thong_tin


def _in_tom_tat_pg(pg: "_PgDemo", t: dict):
    print("\n[pg-demo] KẾT THÚC DỌN CSDL TẠM")
    if "loi_don" in t:
        print(f"  LỖI khi dọn lần cuối ({t['loi_don']}); còn trong sổ chưa xóa: {t.get('sot_theo_so')}  → chạy lại với --pg-demo-don-so {pg.so}")
    else:
        print(f"  CSDL trước/sau: {t['truoc']} / {t['sau']} · tạo trong lần chạy: {t['tao_trong_lan_chay']} · đã xóa: {t['da_xoa']} · "
              f"còn sót kho_test_* thuộc sổ: {len(t['sot'])} {t['sot'] or ''}")
        print(f"  kho_test_* mới ngoài sổ (không đụng): {len(t.get('csdl_tam_khong_thuoc_so', []))}")
        print(f"  CSDL khác xuất hiện mới: {len(t['csdl_khac_moi'])} · CSDL có sẵn bị mất: {len(t['csdl_co_san_mat'])} · "
              f"vai trò ktt_test_*/kho_test_* test để lại (không xóa): {t['vai_tro_moi_khong_xoa']}")
    if pg.chua_ho_tro:
        print(f"  họ bản sao chưa dựng được (biến không đặt, test skip như cũ): {', '.join(sorted(pg.chua_ho_tro))}")
    for cb in t.get("canh_bao", []):
        print(f"  CẢNH BÁO: {cb}")
    print(f"  tệp nhật ký/kết quả chứa mật khẩu kết nối: {t['ro_ri_mat_khau_so_tep']}")


def _don_theo_so(pg: "_PgDemo", tep_so: Path) -> int:
    """--pg-demo-don-so: dọn các CSDL còn trong sổ ghi của lần chạy cũ (mỗi tên phải khớp ^kho_test_… ; chỉ DROP tên có trong sổ)."""
    pg.khoa = _khoa_loai_tru_pg()
    try:
        data = json.loads(tep_so.read_text(encoding="utf-8"))
        so = _SoHuuPg(tep_so, data.get("ma_lan_chay"), pg.cum)
        d = so.doc()
        ten = [t for t in d["muc"] if so._hop_le(d, t)]
    except (OSError, ValueError, AttributeError, TypeError):
        print("Không đọc được sổ sở hữu đúng cụm/ảnh chụp trước.", file=sys.stderr)
        return 2
    if not ten:
        print("[pg-demo] sổ ghi không còn CSDL nào cần xóa.")
        return 0
    kq = pg._goi("xoa", str(tep_so.resolve()), so.ma, *ten)
    print(f"[pg-demo] đã xóa {len(kq['da_xoa'])}, không còn {len(kq['khong_co'])}, còn phiên kết nối {len(kq['con_phien'])}, lỗi/từ chối {len(kq['loi']) + len(kq['tu_choi'])}")
    if kq["con_lai_sau_xoa"]:
        print(f"[pg-demo] CẢNH BÁO: CSDL còn lại sau DROP: {kq['con_lai_sau_xoa']}")
    return 0 if not (kq["con_phien"] or kq["loi"] or kq["tu_choi"] or kq["con_lai_sau_xoa"]) else 1


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "--con":  # nội bộ: python script.py --con <repo> <module> <tep_tien_do>
        return _chay_con(Path(argv[1]).resolve(), argv[2], Path(argv[3]))
    if argv and argv[0] == "--pg":  # nội bộ (--pg-demo): python script.py --pg <viec> <tep_ket_noi> <repo> [tham số…]
        return _chay_viec_pg(argv[1:])

    ap = argparse.ArgumentParser(description="Chạy test từng module trong tiến trình riêng, giới hạn thời gian.")
    ap.add_argument("repo", type=Path, help="thư mục gốc repo/worktree cần đo (có src\\ và tests\\)")
    ap.add_argument("--module", action="append", default=[], help="chỉ chạy module này (tên, có thể dùng * ; lặp được). Mặc định: tất cả tests/test_*.py")
    ap.add_argument("--gioi-han", type=int, default=GIOI_HAN_MAC_DINH, help="giây tối đa cho mỗi module (mặc định 180)")
    ap.add_argument("--ra", type=Path, help="ghi JSON kết quả (module -> {ok,error,fail,skip,treo,giay,...}) vào file này")
    ap.add_argument("--nhat-ky", type=Path, help="thư mục log + thư mục tạm của test (mặc định: thư mục tạm hệ điều hành)")
    ap.add_argument("--pg-demo", type=Path, metavar="KET_NOI_JSON",
                    help="bật test PostgreSQL trên cụm DEMO loopback: ket-noi.local.json (khóa admin_dsn, app_dsn). Tạo CSDL tạm kho_test_* và xóa chính nó sau khi chạy (xem đầu tệp)")
    ap.add_argument("--pg-demo-don-so", type=Path, metavar="SO_GHI_JSON",
                    help="chỉ với --pg-demo: không chạy test, dọn các CSDL kho_test_* còn trong sổ ghi của một lần chạy bị chết giữa chừng")
    runtime = ap.add_mutually_exclusive_group()
    runtime.add_argument("--python", default=sys.executable, help="python.exe dùng chạy test (mặc định: chính python đang chạy script)")
    runtime.add_argument("--runtime", type=Path, help="runtime.local.json: dùng python, duong_dan_phu_thuoc, thu_muc_khoi_dong; kết nối PostgreSQL chỉ đến từ --pg-demo")
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
    if args.pg_demo_don_so and not args.pg_demo:
        ap.error("--pg-demo-don-so cần đi kèm --pg-demo")

    pg = None
    if args.pg_demo:
        if not args.pg_demo.is_file():
            ap.error("Không thấy tệp kết nối PostgreSQL DEMO (--pg-demo).")
        if subprocess.run([args.python, "-c", "import psycopg"], capture_output=True, timeout=60,
                          env=_moi_truong(repo, nhat_ky, phu_thuoc)).returncode != 0:
            ap.error("--pg-demo cần python có psycopg: dùng --runtime runtime.local.json của bản DEMO.")
        try:
            pg = _PgDemo(args.pg_demo, args.python, phu_thuoc, repo, nhat_ky)
            if args.pg_demo_don_so:
                return _don_theo_so(pg, args.pg_demo_don_so)
            pg.khoi_dong()
        except (ValueError, RuntimeError) as exc:
            print(f"--pg-demo: {exc}", file=sys.stderr)
            return 2

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
    try:
        for i, m in enumerate(modules, 1):
            them_env, thong_tin_pg, dem = {}, None, {}
            if pg:
                them_env, thong_tin_pg = _chuan_bi_pg_module(pg, repo, m)
            try:
                r = _chay_mot_module(repo, m, args.gioi_han, nhat_ky, args.python, phu_thuoc, them_env)
            finally:
                if pg:  # dọn ngay sau module (kể cả lỗi/treo): CSDL tạm của module này và bản sao dựng cho nó
                    try:
                        dem = pg.don()
                    except Exception as exc:  # noqa: BLE001 — dọn lỗi thì để ket_thuc() thử lại; không làm mất kết quả test
                        dem = {"loi_don": _loi_pg_sach(exc)}
            ket_qua[m] = r
            if pg:
                r["pg"] = {**thong_tin_pg, **dem}
            co = "TREO" if r["treo"] else ("LOI" if (r["error"] or r["fail"]) else "ok")
            print(f"[{i:>3}/{len(modules)}] {co:<4} {m:<42} ok={r['ok']:<4} ERROR={r['error']:<4} FAIL={r['fail']:<3} skip={r['skip']:<4} {r['giay']:>6}s"
                  + (f"  treo-o={r.get('test_treo', '')[:80]}" if r["treo"] else "")
                  + (f"  pg[ho={','.join(r['pg']['ho']) or '-'} tao={r['pg'].get('moi', '?')} xoa={r['pg'].get('da_xoa', '?')}]" if pg else ""), flush=True)
            if args.ra:
                _ghi_json(args.ra, ket_qua)
    finally:
        if pg:  # kể cả Ctrl+C / lỗi: dọn lần cuối, kiểm không sót, quét rò rỉ mật khẩu
            _in_tom_tat_pg(pg, pg.ket_thuc([nhat_ky] + ([args.ra] if args.ra else [])))

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
        if pg and pg.quet_ro_ri([args.ra]):
            print("CẢNH BÁO: tệp kết quả chứa mật khẩu kết nối — KHÔNG commit; báo lead.", file=sys.stderr)
    # Giữ bản chi tiết (traceback đầu tiên mỗi module, nhóm dòng lỗi) cạnh nhật ký để dò nguyên nhân gốc.
    (nhat_ky / "chi-tiet.json").write_text(json.dumps(
        _LOC.data({m: {"loi_dau": r["loi_dau"], "tb_dau_tien": r["_tb_dau"], "dong_loi": r["_dong_loi"], "ids_loi": r["ids_loi"], "test_treo": r.get("test_treo", "")}
         for m, r in sorted(ket_qua.items())}), ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if not (tong["error"] or tong["fail"] or tong["treo"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
