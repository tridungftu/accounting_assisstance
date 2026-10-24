"""CRM-01 sửa04 — nút mở DEMO: validator DSN chung, bảo đảm cluster PostgreSQL đã có, thứ tự side effect của tool chuẩn bị.

Toàn bộ là test THUẦN/STUB: không mạng, không SQL thật, không chạy pg_ctl/launcher/cluster thật. `psycopg.connect` bị thay bằng bẫy
hoặc kết nối giả; thao tác hệ điều hành (pg_ctl, netstat, tiến trình) đi qua `StubHDH`. DSN giả không có mật khẩu.
Kết quả ở đây KHÔNG chứng minh nút mở thật, cold-start host hay GUI — các phần đó Codex chạy trên host sau terminal.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import string
import tempfile
import threading
import time
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from psycopg.conninfo import conninfo_to_dict

from kho_tri_thuc.ha_tang import pg_cum
from kho_tri_thuc.ha_tang.pg_migrations import PG_MIGRATIONS, PG_SCHEMA_VERSION
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import crm_khoi_dong as kd

ROOT = Path(__file__).resolve().parents[1]
DB = "kho_crm_demo_v1"
APP = f"host=127.0.0.1 port=5432 dbname={DB} user=demo_app"
ADMIN = f"host=127.0.0.1 port=5432 dbname={DB} user=demo_admin"


class _Bay:
    """Bẫy connector: ghi lại mọi lần gọi; test âm yêu cầu số lần gọi = 0."""

    def __init__(self):
        self.goi = []

    def __call__(self, *a, **kw):
        self.goi.append(a[0] if a else kw)
        raise AssertionError("connector bị gọi trước khi kiểm cấu hình")


def _ma(test, code, fn):
    with test.assertRaises(DataError) as ctx:
        fn()
    test.assertEqual(ctx.exception.code, code)
    test.assertNotIn("user=", str(ctx.exception))
    return ctx.exception


class ValidatorTests(unittest.TestCase):
    def test_e01_e03_endpoint_khong_tuong_minh_bi_tu_choi(self):
        with patch.dict(os.environ, {"PGHOST": "10.9.9.9", "PGHOSTADDR": "10.9.9.9", "PGPORT": "6543", "PGSERVICE": "khac"}):
            _ma(self, "KET_NOI_THIEU_ENDPOINT", lambda: kd.chuan_hoa_dsn(f"port=5432 dbname={DB} user=x"))            # E01 thiếu host (PGHOST)
            _ma(self, "KET_NOI_THIEU_ENDPOINT", lambda: kd.chuan_hoa_dsn(f"dbname={DB} user=x"))                      # E02 thiếu host (PGHOSTADDR)
            _ma(self, "KET_NOI_KHOA_KHONG_HO_TRO", lambda: kd.chuan_hoa_dsn(f"service=kho dbname={DB}"))             # E03 service
            _ma(self, "KET_NOI_KHOA_KHONG_HO_TRO", lambda: kd.chuan_hoa_dsn(f"service=kho host=127.0.0.1 port=5432 dbname={DB}"))
            _ma(self, "KET_NOI_THIEU_ENDPOINT", lambda: kd.chuan_hoa_dsn(f"host=127.0.0.1 dbname={DB}"))             # thiếu port (PGPORT)
            # control dương: đủ endpoint tường minh → chuỗi kết nối dựng lại có hostaddr loopback, môi trường không đổi được đích
            n = kd.chuan_hoa_dsn(APP)
            d = conninfo_to_dict(n["conninfo"])
            self.assertEqual((d["host"], d["hostaddr"], d["port"], d["dbname"]), ("127.0.0.1", "127.0.0.1", "5432", DB))
            self.assertNotIn("service", d)

    def test_tham_so_va_host_khong_ho_tro(self):
        for dsn, code in ((f"host=127.0.0.1 hostaddr=10.0.0.1 port=5432 dbname={DB}", "KET_NOI_KHOA_KHONG_HO_TRO"),
                          (f"host=127.0.0.1,::1 port=5432 dbname={DB}", "KET_NOI_KHONG_LOCAL"),
                          (f"host=127.0.0.1 port=5432,5433 dbname={DB}", "KET_NOI_KHONG_LOCAL"),
                          (f"host=10.0.0.5 port=5432 dbname={DB}", "KET_NOI_KHONG_LOCAL"),
                          (f"host=127.0.0.1 port=5432 dbname={DB} options='-c search_path=x'", "KET_NOI_KHOA_KHONG_HO_TRO"),
                          ("host=127.0.0.1 port=5432 dbname=kho_that", "KET_NOI_DB_KHONG_DEMO"),
                          ("host=127.0.0.1 port=5432 dbname=kho_test_x", "KET_NOI_DB_KHONG_DEMO"),
                          (f"host=127.0.0.1 port=99999 dbname={DB}", "KET_NOI_SAI_DINH_DANG"), ("không phải dsn ===", "KET_NOI_SAI_DINH_DANG")):
            _ma(self, code, lambda dsn=dsn: kd.chuan_hoa_dsn(dsn))
        # servicefile: tùy bản libpq là khóa lạ (không đọc được) hoặc khóa không hỗ trợ — cả hai đều từ chối trước kết nối
        with self.assertRaises(DataError) as ctx:
            kd.chuan_hoa_dsn(f"host=127.0.0.1 port=5432 dbname={DB} servicefile=x")
        self.assertIn(ctx.exception.code, ("KET_NOI_KHOA_KHONG_HO_TRO", "KET_NOI_SAI_DINH_DANG"))

    def test_control_loopback_hop_le(self):
        for host, hostaddr in (("127.0.0.1", "127.0.0.1"), ("localhost", "127.0.0.1"), ("::1", "::1"), ("LOCALHOST", "127.0.0.1")):
            n = kd.chuan_hoa_dsn(f"host={host} port=5432 dbname={DB} user=x")
            self.assertEqual((n["hostaddr"], n["port"], n["dbname"]), (hostaddr, 5432, DB))
        self.assertEqual(kd.chuan_hoa_dsn(f"postgresql://x@127.0.0.1:5432/{DB}")["port"], 5432)
        self.assertEqual(kd.chuan_hoa_dsn("host=127.0.0.1 port=5432 dbname=kho_test_x", kd.TIEN_TO_DB_KIEM_THU)["dbname"], "kho_test_x")

    def test_c04_cap_khac_cong_hoac_db(self):
        _ma(self, "KET_NOI_KHAC_ENDPOINT", lambda: kd.kiem_cap(f"host=127.0.0.1 port=6543 dbname={DB}", ADMIN))   # C04
        _ma(self, "KET_NOI_KHAC_ENDPOINT", lambda: kd.kiem_cap(f"host=::1 port=5432 dbname={DB}", ADMIN))
        _ma(self, "KET_NOI_KHAC_DB", lambda: kd.kiem_cap(APP, "host=127.0.0.1 port=5432 dbname=kho_crm_demo_khac"))
        cap = kd.kiem_cap(f"host=localhost port=5432 dbname={DB} user=a", ADMIN)  # control: localhost ≡ 127.0.0.1 sau chuẩn hóa
        self.assertEqual((cap["db"], cap["endpoint"]), (DB, ("127.0.0.1", 5432)))
        path = Path(tempfile.mkdtemp(prefix="ktt-kd-")) / "ket-noi.local.json"
        path.write_text(json.dumps({"phien_ban": 1, "app_dsn": f"host=127.0.0.1 port=6543 dbname={DB}", "admin_dsn": ADMIN}), encoding="utf-8")
        _ma(self, "KET_NOI_KHAC_ENDPOINT", lambda: kd.doc_ket_noi(path))


@contextmanager
def _seed_bo_sung_gia(seed):
    # Các gói M5/M2/L11/M4/CRM-G đã thêm bootstrap; test nút mở vẫn dùng seed giả, không chạy SQL seed thật.
    with ExitStack() as stack:
        for ten in ("m5", "m2", "l11", "m4", "crm_g"):
            stack.enter_context(patch(f"kho_tri_thuc.k2.{ten}_demo.khoi_tao",
                                      lambda c, ten=ten: seed.append(ten) or {"stub": ten}))
        yield


class _KetNoiGia:
    """Kết nối PostgreSQL giả cho chuan_bi: trả hàng cố định theo câu truy vấn. Ghi lại thứ tự để kiểm."""

    def __init__(self, ten, nhat_ky, dich=("127.0.0.1", 5432, 777, DB), role=("demo_app", DB, False, False, True, False, 0, 0), history=None):
        self.ten, self.nhat_ky, self.dich, self.role = ten, nhat_ky, dich, role
        self.history = ([(i, hashlib.sha256("\n".join(m).encode("utf-8")).hexdigest())
                         for i, m in enumerate(PG_MIGRATIONS, 1)] if history is None else history)
        self._rows = []

    @contextmanager
    def transaction(self, savepoint_name=None, force_rollback=False):
        # Giao diện psycopg dùng trong ha_tang/postgres.py; không đóng connection khi thoát transaction.
        self.nhat_ky.append((self.ten, "begin"))
        try:
            yield
        except BaseException:
            self.nhat_ky.append((self.ten, "rollback"))
            raise
        else:
            self.nhat_ky.append((self.ten, "rollback" if force_rollback else "commit"))

    @contextmanager
    def cursor(self):
        yield self

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        rows, self._rows = self._rows, []
        return rows

    def __iter__(self):
        return iter(self.fetchall())

    def execute(self, sql, params=None):
        self.nhat_ky.append((self.ten, sql.split()[0] + ":" + ("dich" if "inet_server_addr" in sql else "role" if "pg_roles" in sql else
                                                                "ver" if "schema_migrations" in sql else "khac")))
        if "inet_server_addr" in sql:
            row = self.dich
        elif "pg_roles" in sql:
            row = self.role
        elif "SELECT version, checksum" in sql:
            self._rows = list(self.history)
            return self
        elif "schema_migrations" in sql:
            row = (PG_SCHEMA_VERSION,)
        else:
            self._rows = []
            return self
        self._rows = [row]
        return self

    def close(self):
        self.nhat_ky.append((self.ten, "close"))

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class ChuanBiStubTests(unittest.TestCase):
    """D03–D05: kiểm cả hai DSN trước MỌI kết nối/seed. Control dương bằng kết nối giả (stub, không DB thật)."""

    def _chay(self, kn, **gia):
        nhat_ky, ket_noi, seed = [], [], []

        def connect(ci, **kw):
            ket_noi.append(conninfo_to_dict(ci))
            return _KetNoiGia("admin" if conninfo_to_dict(ci).get("user") == "demo_admin" else "app", nhat_ky, **gia.get(conninfo_to_dict(ci).get("user"), {}))
        with patch("psycopg.connect", connect), patch("kho_tri_thuc.k2.crm_demo.khoi_tao", lambda c: seed.append(1) or {"PN_DEMO_A": 1, "PN_DEMO_B": 2}), \
                _seed_bo_sung_gia(seed), \
                patch("kho_tri_thuc.ha_tang.postgres.schema_version", lambda c: PG_SCHEMA_VERSION):
            try:
                return kd.chuan_bi(kn), ket_noi, seed, nhat_ky
            except DataError as exc:
                return exc, ket_noi, seed, nhat_ky

    def test_d03_d05_tu_choi_truoc_moi_side_effect(self):
        for app, code in ((f"host=10.1.1.1 port=5432 dbname={DB} user=demo_app", "KET_NOI_KHONG_LOCAL"),          # D03 app remote
                          (f"host=127.0.0.1 port=6543 dbname={DB} user=demo_app", "KET_NOI_KHAC_ENDPOINT"),       # D04 app khác cổng
                          ("host=127.0.0.1 port=5432 dbname=kho_crm_demo_khac user=demo_app", "KET_NOI_KHAC_DB"),  # D05 app khác DB
                          (None, "KET_NOI_SAI_DINH_DANG")):
            out, ket_noi, seed, _ = self._chay({"app_dsn": app, "admin_dsn": ADMIN})
            self.assertIsInstance(out, DataError, app)
            self.assertEqual((out.code, ket_noi, seed), (code, [], []), app)
        out, ket_noi, seed, _ = self._chay({"app_dsn": APP, "admin_dsn": f"host=10.1.1.1 port=5432 dbname={DB} user=demo_admin"})
        self.assertEqual((out.code, ket_noi, seed), ("KET_NOI_KHONG_LOCAL", [], []))

    def test_control_duong_va_kiem_sau_ket_noi(self):
        out, ket_noi, seed, nhat_ky = self._chay({"app_dsn": APP, "admin_dsn": ADMIN})
        self.assertEqual((out["trang_thai"], out["endpoint"], out["schema_sau"], seed),
                         ("SAN_SANG", "127.0.0.1:5432", PG_SCHEMA_VERSION, [1, "m5", "m2", "l11", "m4", "crm_g"]))
        self.assertEqual([d["hostaddr"] for d in ket_noi], ["127.0.0.1", "127.0.0.1"])  # kết nối bằng chuỗi đã chuẩn hóa
        self.assertEqual(nhat_ky[0], ("admin", "SELECT:dich"))
        # đích thực khác (OID DB khác) → từ chối; app là chủ bảng → từ chối; app superuser → từ chối
        out, *_ = self._chay({"app_dsn": APP, "admin_dsn": ADMIN}, demo_app={"dich": ("127.0.0.1", 5432, 999, DB)})
        self.assertEqual(out.code, "KET_NOI_KHAC_DB")
        out, *_ = self._chay({"app_dsn": APP, "admin_dsn": ADMIN}, demo_app={"role": ("demo_app", DB, False, False, True, False, 0, 3)})
        self.assertEqual(out.code, "ROLE_UNG_DUNG_LA_CHU")
        out, *_ = self._chay({"app_dsn": APP, "admin_dsn": ADMIN}, demo_app={"role": ("demo_app", DB, False, False, True, True, 0, 0)})
        self.assertEqual(out.code, "ROLE_UNG_DUNG_LA_CHU")
        out, *_ = self._chay({"app_dsn": APP, "admin_dsn": ADMIN}, demo_app={"role": ("demo_app", DB, True, False, True, False, 0, 0)})
        self.assertEqual(out.code, "ROLE_UNG_DUNG_SAI")
        # Không stub cổng lineage: có max(version) đúng nhưng checksum sai vẫn phải bị chặn.
        hist = _KetNoiGia("app", []).history
        sai = hist[:-1] + [(PG_SCHEMA_VERSION, "0" * 64)]
        for history, code in ((sai, "MIGRATION_CHANGED"), (hist[:-1], "SCHEMA_CHUA_NANG_CAP")):
            out, *_ = self._chay({"app_dsn": APP, "admin_dsn": ADMIN}, demo_app={"history": history})
            self.assertIsInstance(out, DataError)
            self.assertEqual(out.code, code)


class ServerEnvTests(unittest.TestCase):
    """S02/S03: đường biến môi trường của server dùng cùng validator, TRƯỚC connector."""

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.giao_dien.server import LocalApp
        with patch.dict(os.environ, {}, clear=False):
            for k in (LocalApp.CRM_ENV, LocalApp.CRM_ENV_ADMIN, LocalApp.CRM_ENV_DB_KIEM_THU, "KTT_CRM_DEMO_KET_NOI"):
                os.environ.pop(k, None)
            cls.app = LocalApp(ROOT / "cau_hinh.toml", Path(tempfile.mkdtemp(prefix="ktt-kd-web-")) / "web")
        cls.LocalApp = LocalApp

    def _env(self, **env):
        base = {k: "" for k in (self.LocalApp.CRM_ENV, self.LocalApp.CRM_ENV_ADMIN, self.LocalApp.CRM_ENV_DB_KIEM_THU, "KTT_CRM_DEMO_KET_NOI")}
        return patch.dict(os.environ, {**base, **env})

    def test_s02_s03_tu_choi_truoc_connector(self):
        bay = _Bay()
        for dsn, code in ((f"host=10.2.2.2 port=5432 dbname={DB}", "KET_NOI_KHONG_LOCAL"), ("host=127.0.0.1 port=5432 dbname=kho_that", "KET_NOI_DB_KHONG_DEMO"),
                          ("host=127.0.0.1 port=5432 dbname=kho_test_crm_x", "KET_NOI_DB_KHONG_DEMO"), (f"port=5432 dbname={DB}", "KET_NOI_THIEU_ENDPOINT")):
            with self._env(**{self.LocalApp.CRM_ENV: dsn}), patch("psycopg.connect", bay):
                self.app._crm = None
                _ma(self, code, self.app.crm)
        with self._env(**{self.LocalApp.CRM_ENV: APP, self.LocalApp.CRM_ENV_ADMIN: f"host=127.0.0.1 port=6543 dbname={DB}"}), patch("psycopg.connect", bay):
            self.app._crm = None
            _ma(self, "KET_NOI_KHAC_ENDPOINT", self.app.crm)
        self.assertEqual(bay.goi, [])

    def test_control_dsn_demo_va_fixture_ro(self):
        with self._env(**{self.LocalApp.CRM_ENV: APP}):
            app_ci, admin_ci = self.app._crm_ket_noi()
        self.assertEqual((conninfo_to_dict(app_ci)["hostaddr"], admin_ci), ("127.0.0.1", None))
        with self._env(**{self.LocalApp.CRM_ENV: "host=127.0.0.1 port=5432 dbname=kho_test_crm_x", self.LocalApp.CRM_ENV_DB_KIEM_THU: "1"}):
            self.assertEqual(conninfo_to_dict(self.app._crm_ket_noi()[0])["dbname"], "kho_test_crm_x")
        with self._env(), patch("psycopg.connect", _Bay()):  # thiếu cấu hình: báo rõ, không gọi connector
            self.app._crm = None
            self.assertEqual(self.app.crm_state("MO_PHONG_KT_A")["cau_hinh"], False)


class StubHDH(pg_cum.HeDieuHanh):
    """Hệ điều hành giả: trạng thái cluster/cổng/tiến trình trong bộ nhớ; ghi lại mọi argv."""

    def __init__(self, cum, *, dang_chay=False, pid=4242, nghe=None, exe=None, cmd=None, status_ma=None, start_ma=0, start_len=True, cham=0.0):
        super().__init__()
        self.cum, self.dang_chay, self.pid, self.status_ma, self.start_ma, self.start_len, self.cham = cum, dang_chay, pid, status_ma, start_ma, start_len, cham
        self.nghe = nghe if nghe is not None else ({cum.port: pid} if dang_chay else {})
        self.exe = exe or str(cum.postgres)
        self.cmd = cmd or f'"{cum.postgres}" -D "{cum.data_dir}" -h {cum.host} -p {cum.port}'
        self.lenh, self.lock = [], threading.Lock()

    def chay(self, argv, timeout=None):
        with self.lock:
            self.lenh.append(list(argv))
        if argv[1] == "status":
            if self.status_ma is not None:
                return self.status_ma, ""
            return (0, f"pg_ctl: server is running (PID: {self.pid})\n") if self.dang_chay else (3, "pg_ctl: no server running\n")
        if argv[1] == "start":
            time.sleep(self.cham)
            if self.start_len:
                self.dang_chay, self.nghe = True, {self.cum.port: self.pid}
            return self.start_ma, ""
        raise AssertionError("lệnh không mong đợi: " + argv[1])

    def pid_dang_nghe(self, host, port):
        return self.nghe.get(port)

    def tien_trinh(self, pid):
        return {"exe": self.exe, "cmd": self.cmd} if pid == self.pid else {"exe": r"C:\khac\khac.exe", "cmd": "khac"}


class CumTests(unittest.TestCase):
    """Bảo đảm cluster đã có — stub hệ điều hành; tệp runtime/data là tệp giả trong thư mục tạm."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ktt-cum-"))
        (self.tmp / "bin").mkdir()
        (self.tmp / "bin" / "pg_ctl.exe").write_bytes(b"pg_ctl gia DEMO")
        (self.tmp / "bin" / "postgres.exe").write_bytes(b"postgres gia DEMO")
        (self.tmp / "data").mkdir()
        (self.tmp / "data" / "PG_VERSION").write_text("16\n", encoding="ascii")
        self.cum = pg_cum.Cum(self.tmp / "bin" / "pg_ctl.exe", self.tmp / "data", pg_ctl_sha256=hashlib.sha256(b"pg_ctl gia DEMO").hexdigest())
        self.log, self.khoa = self.tmp / "logs", self.tmp / "khoa"

    def _chay(self, hdh, cum=None):
        return pg_cum.bao_dam_cum(cum or self.cum, self.log, self.khoa, hdh=hdh, timeout_start=5)

    def _cam(self, hdh):
        for argv in hdh.lenh:
            joined = " ".join(argv).lower()
            for tu in ("stop", "kill", "initdb", "register", "restart", "password", "dsn", "promote"):
                self.assertNotIn(tu, argv[1:2] + [joined] if tu in ("password", "dsn") else argv[1:2], argv)

    def test_dinh_danh_sai_khong_chay_lenh(self):
        import dataclasses
        for cum, code in ((dataclasses.replace(self.cum, pg_ctl_sha256="0" * 64), "CUM_SAI_RUNTIME"),
                          (dataclasses.replace(self.cum, data_dir=self.tmp / "khong-co"), "CUM_KHONG_TRUY_CAP"),
                          (dataclasses.replace(self.cum, pg_version="15"), "CUM_PG_VERSION"),
                          (dataclasses.replace(self.cum, pg_ctl=self.tmp / "bin" / "khong-co.exe"), "CUM_SAI_RUNTIME")):
            hdh = StubHDH(cum)
            _ma(self, code, lambda: self._chay(hdh, cum))
            self.assertEqual(hdh.lenh, [])
        vang = next((c for c in string.ascii_uppercase[::-1] if not Path(f"{c}:\\").exists()), None) if os.name == "nt" else None
        if vang:
            cum = dataclasses.replace(self.cum, data_dir=Path(f"{vang}:\\pg\\data"))
            _ma(self, "CUM_O_DIA_VANG", lambda: self._chay(StubHDH(cum), cum))

    def test_status_khong_ro_hoac_khong_truy_cap_khong_start(self):
        for ma, code in ((4, "CUM_KHONG_TRUY_CAP"), (1, "CUM_TRANG_THAI_KHONG_RO"), (2, "CUM_TRANG_THAI_KHONG_RO"), (-1, "CUM_TRANG_THAI_KHONG_RO")):
            hdh = StubHDH(self.cum, status_ma=ma)
            _ma(self, code, lambda: self._chay(hdh))
            self.assertEqual([a[1] for a in hdh.lenh], ["status"])

    def test_dang_chay_dung_cum_thi_dung_lai(self):
        hdh = StubHDH(self.cum, dang_chay=True)
        self.assertEqual(self._chay(hdh), {"ket_qua": "DUNG_LAI", "pid": 4242, "endpoint": "127.0.0.1:5432"})
        self.assertEqual([a[1] for a in hdh.lenh], ["status"])
        self.assertFalse(self.log.exists())  # dùng lại: không tạo log start

    def test_dang_chay_khong_xac_minh_duoc_thi_dung(self):
        cases = (StubHDH(self.cum, dang_chay=True, nghe={5432: 9999}),                                   # cổng thuộc PID khác
                 StubHDH(self.cum, dang_chay=True, exe=r"C:\runtime-khac\bin\postgres.exe"),              # runtime khác
                 StubHDH(self.cum, dang_chay=True, cmd=f'"{self.cum.postgres}" -D "{self.cum.data_dir}2" -p 5432'),  # data dir khác (tiền tố chung)
                 StubHDH(self.cum, dang_chay=True, cmd=f'"{self.cum.postgres}" -p 5432'),                 # không có -D
                 StubHDH(self.cum, dang_chay=True, nghe={}))                                              # status chạy nhưng không nghe đúng cổng
        for hdh in cases:
            _ma(self, "CUM_KHONG_XAC_MINH", lambda: self._chay(hdh))
            self.assertEqual([a[1] for a in hdh.lenh], ["status"])

    def test_dung_va_cong_bi_chiem_thi_khong_start(self):
        hdh = StubHDH(self.cum, nghe={5432: 31337})
        _ma(self, "CUM_CONG_BI_CHIEM", lambda: self._chay(hdh))
        self.assertEqual([a[1] for a in hdh.lenh], ["status"])

    def test_dung_va_cong_trong_thi_start_dung_argv_log_moi(self):
        self.log.mkdir()
        cu = self.log / "pg-start-cu.log"
        cu.write_text("log cũ", encoding="utf-8")
        hdh = StubHDH(self.cum)
        kq = self._chay(hdh)
        self.assertEqual((kq["ket_qua"], kq["pid"], kq["start_ma"]), ("DA_KHOI_DONG", 4242, 0))
        start = [a for a in hdh.lenh if a[1] == "start"]
        self.assertEqual(len(start), 1)
        self.assertEqual(start[0], [str(self.cum.pg_ctl), "start", "-D", str(self.cum.data_dir), "-l", str(self.log / kq["log"]), "-w", "-t", "5",
                                    "-o", "-h 127.0.0.1 -p 5432"])
        self.assertTrue((self.log / kq["log"]).is_file())
        self.assertEqual(cu.read_text(encoding="utf-8"), "log cũ")
        kq2 = self._chay(StubHDH(self.cum))
        self.assertNotEqual(kq["log"], kq2["log"])  # mỗi lần start một log mới
        self._cam(hdh)

    def test_start_timeout_nhung_server_len_va_start_hong(self):
        hdh = StubHDH(self.cum, start_ma=1)  # pg_ctl báo lỗi/timeout nhưng server vẫn lên
        kq = self._chay(hdh)
        self.assertEqual((kq["ket_qua"], kq["start_ma"], [a[1] for a in hdh.lenh]), ("DA_KHOI_DONG", 1, ["status", "start", "status"]))
        hdh = StubHDH(self.cum, start_ma=1, start_len=False)
        _ma(self, "CUM_KHONG_KHOI_DONG", lambda: self._chay(hdh))
        self.assertEqual([a[1] for a in hdh.lenh], ["status", "start", "status"])  # không spawn lại
        self._cam(hdh)

    def test_hai_lan_mo_dong_thoi_chi_mot_start(self):
        hdh = StubHDH(self.cum, cham=0.4)
        kq, loi = [], []

        def mo():
            try:
                kq.append(self._chay(hdh)["ket_qua"])
            except Exception as exc:  # noqa: BLE001
                loi.append(exc)
        ts = [threading.Thread(target=mo) for _ in range(2)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(20)
        self.assertEqual(loi, [])
        self.assertEqual(sorted(kq), ["DA_KHOI_DONG", "DUNG_LAI"])
        self.assertEqual(sum(1 for a in hdh.lenh if a[1] == "start"), 1)
        self.assertEqual(len(list(self.khoa.iterdir())), 1)  # tệp khóa giữ lại

    def test_doc_cum_mac_dinh_va_tep_cau_hinh(self):
        cum = pg_cum.cum_mac_dinh(ROOT)
        self.assertEqual(cum.pg_ctl, ROOT.resolve().parent / "var" / "postgresql16-16.15-runtime" / "bin" / "pg_ctl.exe")
        self.assertEqual((cum.data_dir, cum.host, cum.port, cum.pg_version, cum.pg_ctl_sha256),
                         (ROOT.resolve().parent / "var" / "postgresql-ktt-16" / "data", "127.0.0.1", 5432, "16", pg_cum.PG_CTL_SHA256))
        root = self.tmp / "web"
        (root / "crm-demo").mkdir(parents=True)
        (root / "crm-demo" / "cum-pg.local.json").write_text(json.dumps({"phien_ban": 1, "pg_ctl": "x", "data_dir": "y", "host": "10.0.0.1"}), encoding="utf-8")
        _ma(self, "CUM_CAU_HINH_SAI", lambda: pg_cum.doc_cum(root, ROOT))
        (root / "crm-demo" / "cum-pg.local.json").write_text(json.dumps({"phien_ban": 1, "pg_ctl": "x", "data_dir": "y", "port": 6543}), encoding="utf-8")
        self.assertEqual(pg_cum.doc_cum(root, ROOT).port, 6543)


class ToolTests(unittest.TestCase):
    """Thứ tự side effect của tools/chuan_bi_crm_demo.py::chay — cluster và bootstrap là stub."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("chuan_bi_crm_demo_t", ROOT / "tools" / "chuan_bi_crm_demo.py")
        cls.tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.tool)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ktt-tool-"))
        self.root = self.tmp / "web"
        (self.root / "crm-demo").mkdir(parents=True)
        (self.tmp / "bin").mkdir()
        (self.tmp / "bin" / "pg_ctl.exe").write_bytes(b"pg_ctl gia")
        (self.tmp / "bin" / "postgres.exe").write_bytes(b"postgres gia")
        (self.tmp / "data").mkdir()
        (self.tmp / "data" / "PG_VERSION").write_text("16", encoding="ascii")
        (self.root / "crm-demo" / "cum-pg.local.json").write_text(json.dumps({
            "phien_ban": 1, "pg_ctl": str(self.tmp / "bin" / "pg_ctl.exe"), "data_dir": str(self.tmp / "data"),
            "pg_ctl_sha256": hashlib.sha256(b"pg_ctl gia").hexdigest()}), encoding="utf-8")
        self.ket_noi = self.root / "crm-demo" / "ket-noi.local.json"

    def _cfg(self, app=APP, admin=ADMIN):
        self.ket_noi.write_text(json.dumps({"phien_ban": 1, "app_dsn": app, "admin_dsn": admin}), encoding="utf-8")

    def _chay(self, hdh=None, bootstrap=None):
        env = {k: "" for k in ("KTT_CRM_DEMO_KET_NOI",)}
        with patch.dict(os.environ, env):
            os.environ.pop("KTT_CRM_DEMO_KET_NOI")
            return self.tool.chay(ROOT / "cau_hinh.toml", self.root, hdh=hdh, bootstrap=bootstrap, thu_muc_khoa=self.tmp / "khoa")

    def test_kho_that_bo_qua_hoan_toan(self):
        bay = _Bay()
        with patch.object(self.tool.Config, "load", lambda p: SimpleNamespace(environment="that")), patch.object(self.tool, "doc_ket_noi", bay), \
                patch.object(self.tool, "bao_dam_cum", bay):
            self.assertEqual(self.tool.chay(ROOT / "cau_hinh.toml", self.root), (0, {"trang_thai": "BO_QUA_KHO_THAT"}))
        self.assertEqual(bay.goi, [])

    def test_chua_cau_hinh_hoac_cau_hinh_sai_khong_dung_cum(self):
        bay = _Bay()
        with patch.object(self.tool, "bao_dam_cum", bay):
            code, st = self._chay(bootstrap=bay)
            self.assertEqual((code, st["ma"]), (2, "CRM_CHUA_CAU_HINH"))
            for app, admin, ma in ((f"host=10.0.0.1 port=5432 dbname={DB}", ADMIN, "KET_NOI_KHONG_LOCAL"),
                                   (f"host=127.0.0.1 port=6543 dbname={DB}", f"host=127.0.0.1 port=6543 dbname={DB}", "KET_NOI_KHONG_DUNG_CUM"),
                                   (f"port=5432 dbname={DB}", ADMIN, "KET_NOI_THIEU_ENDPOINT")):
                self._cfg(app, admin)
                code, st = self._chay(bootstrap=bay)
                self.assertEqual((code, st["ma"]), (3, ma))
        self.assertEqual(bay.goi, [])

    def test_loi_cum_thi_khong_bootstrap(self):
        self._cfg()
        bay = _Bay()
        cum = pg_cum.doc_cum(self.root, ROOT)
        code, st = self._chay(hdh=StubHDH(cum, nghe={5432: 31337}), bootstrap=bay)
        self.assertEqual((code, st["ma"], bay.goi), (3, "CUM_CONG_BI_CHIEM", []))

    def test_cum_dung_roi_bootstrap(self):
        self._cfg()
        cum = pg_cum.doc_cum(self.root, ROOT)
        goi = []
        for hdh, ket_qua in ((StubHDH(cum), "DA_KHOI_DONG"), (StubHDH(cum, dang_chay=True), "DUNG_LAI")):
            code, st = self._chay(hdh=hdh, bootstrap=lambda kn: goi.append(kn) or {"trang_thai": "SAN_SANG", "db": kn["db"]})
            self.assertEqual((code, st["trang_thai"], st["cum"]["ket_qua"]), (0, "SAN_SANG", ket_qua))
        self.assertEqual([(k["db"], conninfo_to_dict(k["admin_dsn"])["hostaddr"]) for k in goi], [(DB, "127.0.0.1")] * 2)


class _KetNoiGiaDict(_KetNoiGia):
    """Như _KetNoiGia nhưng trả dict_row (như server) và có `adapters` cho CrmK2."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.adapters = SimpleNamespace(register_dumper=lambda *x: None)

    def execute(self, sql, params=None):
        super().execute(sql, params)
        names = {"pg_roles": ("ten", "db", "sup", "byp", "app_web", "chu_db", "chu_schema", "chu_bang"),
                 "schema_migrations": ("version", "checksum") if "SELECT version, checksum" in sql else ("v",)}
        key = "pg_roles" if "pg_roles" in sql else "schema_migrations" if "schema_migrations" in sql else None
        if key:
            self._rows = [dict(zip(names[key], row)) for row in self._rows]
        return self


class ChuoiNutTests(unittest.TestCase):
    """Sửa05 P1: chuỗi THẬT của nút — raw → JSON → doc_ket_noi → chuan_bi → connector (stub) và env → server → connector.
    Không mock kiem_cap/chuan_hoa_dsn; chỉ connector, seed và schema_version là stub."""

    def test_chuan_hoa_idempotent(self):
        for raw in (APP, f"host=localhost port=5432 dbname={DB} user=a", f"host=::1 port=5432 dbname={DB}", f"postgresql://x@127.0.0.1:5432/{DB}",
                    f"host=127.0.0.1 port=5432 dbname={DB} user=a password=khong_phai_bi_mat sslmode=disable"):
            n = kd.chuan_hoa_dsn(raw)
            self.assertEqual(kd.chuan_hoa_dsn(n["conninfo"]), n, raw)
        ok = kd.chuan_hoa_dsn(f"host=127.0.0.1 hostaddr=127.0.0.1 port=5432 dbname={DB}")
        self.assertEqual(ok["hostaddr"], "127.0.0.1")
        for dsn in (f"host=localhost hostaddr=::1 port=5432 dbname={DB}", f"host=::1 hostaddr=127.0.0.1 port=5432 dbname={DB}",
                    f"host=127.0.0.1 hostaddr=127.0.0.1,127.0.0.1 port=5432 dbname={DB}", f"host=127.0.0.1 hostaddr=10.0.0.1 port=5432 dbname={DB}",
                    f"hostaddr=127.0.0.1 port=5432 dbname={DB}"):
            with self.assertRaises(DataError, msg=dsn) as ctx:
                kd.chuan_hoa_dsn(dsn)
            self.assertIn(ctx.exception.code, ("KET_NOI_KHOA_KHONG_HO_TRO", "KET_NOI_THIEU_ENDPOINT"), dsn)

    def _tep(self, value):
        path = Path(tempfile.mkdtemp(prefix="ktt-chuoi-")) / "ket-noi.local.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_raw_json_doc_ket_noi_chuan_bi_toi_connector(self):
        ket_noi, seed = [], []

        def connect(ci, **kw):
            ket_noi.append(conninfo_to_dict(ci))
            return _KetNoiGia("admin" if conninfo_to_dict(ci).get("user") == "demo_admin" else "app", [])
        path = self._tep({"phien_ban": 1, "app_dsn": f"host=localhost port=5432 dbname={DB} user=demo_app", "admin_dsn": ADMIN})
        with patch.dict(os.environ, {"PGHOSTADDR": "10.9.9.9", "PGSERVICE": "khac", "PGPORT": "6543"}), patch("psycopg.connect", connect), \
                patch("kho_tri_thuc.k2.crm_demo.khoi_tao", lambda c: seed.append(1) or {"PN_DEMO_A": 1, "PN_DEMO_B": 2}), \
                _seed_bo_sung_gia(seed), \
                patch("kho_tri_thuc.ha_tang.postgres.schema_version", lambda c: PG_SCHEMA_VERSION):
            parsed = kd.doc_ket_noi(path)
            out = kd.chuan_bi(parsed)  # bootstrap thật kiểm lại đầu ra của doc_ket_noi
            again = kd.chuan_bi(kd.doc_ket_noi(self._tep({"phien_ban": 1, "app_dsn": parsed["app_dsn"], "admin_dsn": parsed["admin_dsn"]})))
        self.assertEqual((out["trang_thai"], again["trang_thai"], seed),
                         ("SAN_SANG", "SAN_SANG", [1, "m5", "m2", "l11", "m4", "crm_g"] * 2))
        self.assertEqual(len(ket_noi), 4)
        self.assertTrue(all((d["hostaddr"], d["port"], d["dbname"]) == ("127.0.0.1", "5432", DB) for d in ket_noi))  # môi trường không đổi đích
        self.assertNotIn("service", "".join(json.dumps(d) for d in ket_noi))

    def test_env_server_toi_connector_raw_va_da_chuan_hoa(self):
        from kho_tri_thuc.giao_dien.server import LocalApp
        with patch.dict(os.environ, {}, clear=False):
            for k in (LocalApp.CRM_ENV, LocalApp.CRM_ENV_ADMIN, LocalApp.CRM_ENV_DB_KIEM_THU, "KTT_CRM_DEMO_KET_NOI"):
                os.environ.pop(k, None)
            app = LocalApp(ROOT / "cau_hinh.toml", Path(tempfile.mkdtemp(prefix="ktt-chuoi-web-")) / "web")
        for dsn in (APP, kd.chuan_hoa_dsn(APP)["conninfo"]):
            goi = []

            def connect(ci, **kw):
                goi.append(conninfo_to_dict(ci))
                return _KetNoiGiaDict("app", [])
            with patch.dict(os.environ, {LocalApp.CRM_ENV: dsn, LocalApp.CRM_ENV_ADMIN: "", "PGHOSTADDR": "10.9.9.9"}), patch("psycopg.connect", connect):
                os.environ.pop(LocalApp.CRM_ENV_ADMIN)
                app._crm = None
                crm = app.crm()
            self.assertIsNotNone(crm)
            self.assertEqual([(d["hostaddr"], d["port"], d["dbname"]) for d in goi], [("127.0.0.1", "5432", DB)])

    def test_thieu_driver_bao_ma_sach(self):
        import sys
        from kho_tri_thuc.giao_dien.server import LocalApp
        with patch.dict(os.environ, {}, clear=False):
            for k in (LocalApp.CRM_ENV, LocalApp.CRM_ENV_ADMIN, LocalApp.CRM_ENV_DB_KIEM_THU, "KTT_CRM_DEMO_KET_NOI"):
                os.environ.pop(k, None)
            app = LocalApp(ROOT / "cau_hinh.toml", Path(tempfile.mkdtemp(prefix="ktt-driver-web-")) / "web")
        with patch.dict(sys.modules, {"psycopg": None}):
            _ma(self, "RUNTIME_THIEU_DRIVER", lambda: kd.chuan_hoa_dsn(APP))
            _ma(self, "RUNTIME_THIEU_DRIVER", lambda: kd.chuan_bi({"app_dsn": APP, "admin_dsn": ADMIN}))
            with patch.dict(os.environ, {LocalApp.CRM_ENV: APP}):
                app._crm = None
                _ma(self, "RUNTIME_THIEU_DRIVER", app.crm)


class RuntimeTests(unittest.TestCase):
    """Sửa05 §2: chọn runtime app (tools/chon_runtime.py). Probe là stub ghi argv/env, TRỪ lớp KhaNangThatTests chạy probe thật."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("chon_runtime_t", ROOT / "tools" / "chon_runtime.py")
        cls.cr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.cr)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ktt-rt-"))
        self.root = self.tmp / "web"
        (self.root / "crm-demo").mkdir(parents=True)
        self.py = self.tmp / "rt" / "python.exe"
        self.py.parent.mkdir()
        self.py.write_bytes(b"python gia")
        self.dep = self.tmp / "rt" / "site-packages"
        self.dep.mkdir()
        self.kd = self.tmp / "guard"
        self.kd.mkdir()
        (self.kd / "sitecustomize.py").write_text("# guard gia cho test cau hinh\n", encoding="utf-8")

    def _cfg(self, **sua):
        v = {"phien_ban": 1, "python": str(self.py), "duong_dan_phu_thuoc": [str(self.dep)], "thu_muc_khoi_dong": str(self.kd), **sua}
        (self.root / "crm-demo" / "runtime.local.json").write_text(json.dumps(v), encoding="utf-8")

    @staticmethod
    def _probe(**sua):
        return json.dumps({"python": [3, 13, 14], "isolated": False, "ignore_env": False, "dont_write_bytecode": True, "openpyxl": True, "psycopg": True,
                           "phu_thuoc_tren_path": True, "khoi_dong": True, **sua})

    def _stub(self, theo_python):
        goi = []

        def chay(argv, env):
            goi.append((argv, env))
            out = theo_python.get(argv[0])
            return (0, out) if out is not None else (1, "")
        return chay, goi

    def test_doc_runtime_hop_dong_cau_hinh(self):
        self.assertIsNone(self.cr.doc_runtime(self.root))
        self._cfg()
        self.assertEqual(self.cr.doc_runtime(self.root), {"python": str(self.py), "phu_thuoc": [str(self.dep)], "khoi_dong": str(self.kd)})
        for sua, ma in (({"phien_ban": 2}, "RUNTIME_CAU_HINH_SAI"), ({"dsn": "x"}, "RUNTIME_CAU_HINH_SAI"), ({"python": "python.exe"}, "RUNTIME_PYTHON_KHONG_CO"),
                        ({"python": str(self.tmp / "khong.exe")}, "RUNTIME_PYTHON_KHONG_CO"), ({"duong_dan_phu_thuoc": ["tuong-doi"]}, "RUNTIME_PHU_THUOC_KHONG_CO"),
                        ({"thu_muc_khoi_dong": str(self.dep)}, "RUNTIME_KHOI_DONG_KHONG_CO")):
            self._cfg(**sua)
            with self.assertRaises(self.cr.LoiRuntime) as ctx:
                self.cr.doc_runtime(self.root)
            self.assertEqual(ctx.exception.ma, ma, sua)

    def test_moi_truong_con_ke_thua_dung(self):
        base = {"PYTHONPATH": r"C:\rieng\cua\caller", "PYTHONUSERBASE": r"C:\ub", "KHAC": "1"}
        env = self.cr.moi_truong(base, ROOT / "src", [str(self.dep)], str(self.kd))
        self.assertEqual(env["PYTHONPATH"].split(os.pathsep), [str(ROOT / "src"), str(self.dep), str(self.kd)])
        self.assertEqual((env["PYTHONDONTWRITEBYTECODE"], env["PYTHONUTF8"], env["PYTHONUSERBASE"], env["KHAC"]), ("1", "1", r"C:\ub", "1"))
        self.assertEqual(base["PYTHONPATH"], r"C:\rieng\cua\caller")  # không sửa môi trường caller

    def test_runtime_local_du_va_cung_moi_truong(self):
        self._cfg()
        chay, goi = self._stub({str(self.py): self._probe()})
        kq = self.cr.chon(self.root, base_env={"USERPROFILE": str(self.tmp)}, chay=chay)
        self.assertEqual((kq["ok_app"], kq["crm"], kq["python"], kq["nguon"]), (True, True, str(self.py), "runtime_local"))
        [(argv, env)] = goi
        self.assertEqual(argv[:4], [str(self.py), "-X", "utf8", str(self.cr.PROBE)])
        self.assertEqual(json.loads(argv[4]), {"phu_thuoc": [str(self.dep)], "khoi_dong": str(self.kd)})
        self.assertEqual(kq["pythonpath"], env["PYTHONPATH"])  # probe, bước chuẩn bị và server dùng cùng PYTHONPATH
        self.assertEqual(env["PYTHONDONTWRITEBYTECODE"], "1")

    def test_runtime_local_thieu_kha_nang_khong_roi_ve_ung_vien_khac(self):
        bundled = self.tmp / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "python" / "python.exe"
        bundled.parent.mkdir(parents=True)
        bundled.write_bytes(b"bundled gia")
        self._cfg()
        for sua, ma in (({"psycopg": False}, "RUNTIME_THIEU_DRIVER"), ({"isolated": True}, "RUNTIME_ISOLATED"), ({"ignore_env": True}, "RUNTIME_ISOLATED"),
                        ({"phu_thuoc_tren_path": False}, "RUNTIME_PHU_THUOC_KHONG_NAP"), ({"khoi_dong": False}, "RUNTIME_GUARD_KHONG_NAP")):
            chay, goi = self._stub({str(self.py): self._probe(**sua), str(bundled): self._probe()})
            kq = self.cr.chon(self.root, base_env={"USERPROFILE": str(self.tmp)}, chay=chay)
            self.assertEqual((kq["ok_app"], kq["crm"], kq["ma"], kq["python"], len(goi)), (True, False, ma, str(self.py), 1), sua)
        chay, goi = self._stub({str(self.py): self._probe(python=[3, 10, 0])})
        kq = self.cr.chon(self.root, base_env={}, chay=chay)
        self.assertEqual((kq["ok_app"], kq["ma"]), (False, "RUNTIME_KHONG_DUNG_DUOC"))
        chay, _ = self._stub({})
        self.assertEqual(self.cr.chon(self.root, base_env={}, chay=chay)["ung_vien"][0]["thieu_crm"], "RUNTIME_PROBE_LOI")

    def test_python_tuong_minh_chi_dung_python_do(self):
        self._cfg()
        exp = str(self.tmp / "tuong-minh" / "python.exe")
        chay, goi = self._stub({exp: self._probe()})
        kq = self.cr.chon(self.root, explicit=exp, base_env={}, chay=chay)
        self.assertEqual((kq["python"], kq["nguon"], kq["crm"], len(goi)), (exp, "tuong_minh", True, 1))
        self.assertEqual(json.loads(goi[0][0][4])["phu_thuoc"], [str(self.dep)])

    def test_khong_cau_hinh_thu_ung_vien_va_bao_ro(self):
        bundled = self.tmp / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "python" / "python.exe"
        bundled.parent.mkdir(parents=True)
        bundled.write_bytes(b"bundled gia")
        path_py = str(self.tmp / "path" / "python.exe")
        with patch.object(self.cr.shutil, "which", lambda name: path_py):
            chay, goi = self._stub({str(bundled): self._probe(psycopg=False, khoi_dong=None), path_py: self._probe(khoi_dong=None)})
            kq = self.cr.chon(self.root, base_env={"USERPROFILE": str(self.tmp)}, chay=chay)
            self.assertEqual((kq["crm"], kq["python"], [g[0][0] for g in goi]), (True, path_py, [str(bundled), path_py]))
            chay, goi = self._stub({str(bundled): self._probe(psycopg=False), path_py: self._probe(psycopg=False)})
            kq = self.cr.chon(self.root, base_env={"USERPROFILE": str(self.tmp)}, chay=chay)
            self.assertEqual((kq["ok_app"], kq["crm"], kq["ma"], kq["python"]), (True, False, "RUNTIME_CHUA_CAU_HINH", str(bundled)))
        with patch.object(self.cr.shutil, "which", lambda name: None):
            kq = self.cr.chon(self.root, base_env={"USERPROFILE": str(self.tmp / "khong-co")}, chay=self._stub({})[0])
        self.assertEqual((kq["ok_app"], kq["ma"]), (False, "RUNTIME_KHONG_CO_PYTHON"))

    def test_launcher_dung_chung_runtime(self):
        ps = (ROOT / "start-web.ps1").read_text(encoding="utf-8")
        self.assertIn("tools\\chon_runtime.py", ps)
        self.assertEqual(ps.count("Set-KttChildEnv"), 3)  # định nghĩa + bước chuẩn bị CRM + server
        self.assertIn("-not $kttIsThat -and $kttRt.crm", ps)
        self.assertNotIn("$env:PYTHONPATH = Join-Path $PSScriptRoot 'src'", ps)  # không còn PYTHONPATH chỉ src
        self.assertNotIn("$env:PYTHONPATH = $kttSrc", ps)
        for cam in ("Remove-Item", "DROP ", "_dsn", "KHO_PG_DSN", "pip install"):
            self.assertNotIn(cam, ps)


class TransportPowerShellTests(unittest.TestCase):
    """Sửa06: JSON máy Python → Windows PowerShell 5.1. PS 5.1 giải mã stdout tiến trình con bằng codepage console (437) /
    OutputEncoding 20127 (US-ASCII). Gọi main() THẬT của hai tool (probe/bootstrap là stub), lấy đúng stdout, mô phỏng transport byte
    → giải mã cp437/ascii → json.loads phải ra lại nguyên đường dẫn tiếng Việt có khoảng trắng. Không chạy PowerShell/launcher thật."""

    @staticmethod
    def _nap(ten, tep):
        spec = importlib.util.spec_from_file_location(ten, ROOT / "tools" / tep)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def _qua_ps51(out: str) -> list[dict]:
        raw = out.encode("ascii")  # stdout phải thuần ASCII — UnicodeEncodeError = hỏng phương án
        return [json.loads(raw.decode(cp).strip().splitlines()[-1]) for cp in ("cp437", "ascii")]

    def test_chon_runtime_main_duong_dan_viet_qua_cp437(self):
        import contextlib
        import io
        cr = self._nap("chon_runtime_ps", "chon_runtime.py")
        goc = Path(tempfile.mkdtemp(prefix="ktt thư mục có dấu "))
        root = goc / "Phần mềm kho tri thức" / "web"
        (root / "crm-demo").mkdir(parents=True)
        py = goc / "Thời gian chạy" / "python.exe"
        py.parent.mkdir()
        py.write_bytes(b"python gia")
        deps = [goc / "Thời gian chạy" / "Lib" / "site-packages", goc / "phụ thuộc ứng dụng"]
        for d in deps:
            d.mkdir(parents=True)
        guard = goc / "bảo vệ giữ tệp"
        guard.mkdir()
        (guard / "sitecustomize.py").write_text("# guard gia\n", encoding="utf-8")
        (root / "crm-demo" / "runtime.local.json").write_text(json.dumps({"phien_ban": 1, "python": str(py), "duong_dan_phu_thuoc": [str(d) for d in deps],
                                                                          "thu_muc_khoi_dong": str(guard)}, ensure_ascii=False), encoding="utf-8")
        probe = json.dumps({"python": [3, 13, 14], "isolated": False, "ignore_env": False, "dont_write_bytecode": True, "openpyxl": True, "psycopg": True,
                            "phu_thuoc_tren_path": True, "khoi_dong": True})
        buf = io.StringIO()
        with patch.object(cr, "_chay_that", lambda argv, env: (0, probe)), contextlib.redirect_stdout(buf):
            code = cr.main(["--root", str(root)])
        out = buf.getvalue()
        mong = os.pathsep.join([str(ROOT / "src"), *(str(d) for d in deps), str(guard)])
        self.assertEqual(code, 0)
        for kq in self._qua_ps51(out):
            self.assertEqual((kq["crm"], kq["python"], kq["pythonpath"]), (True, str(py), mong))
            self.assertTrue(all(Path(p).is_dir() for p in kq["pythonpath"].split(os.pathsep)))  # cả src/deps/guard tồn tại sau transport
        # oracle nhân quả: bản cũ (UTF-8 thô) qua cùng transport cp437 làm hỏng đường dẫn
        hong = json.loads(json.dumps(json.loads(out), ensure_ascii=False).encode("utf-8").decode("cp437"))
        self.assertNotEqual(hong["pythonpath"], mong)
        [log] = list((root / "logs").glob("runtime-*.json"))
        noi_dung = log.read_text(encoding="utf-8")
        self.assertIn("Phần mềm kho tri thức", noi_dung)  # log UTF-8 giữ chữ Việt thật, không bị thoát
        self.assertEqual(json.loads(noi_dung)["pythonpath"], mong)

    def test_chuan_bi_main_thong_diep_unicode_qua_cp437(self):
        import contextlib
        import io
        tool = self._nap("chuan_bi_ps", "chuan_bi_crm_demo.py")
        root = Path(tempfile.mkdtemp(prefix="ktt thư mục ")) / "Dữ liệu web"
        thong_diep = "Không kết nối được PostgreSQL DEMO — đường dẫn “Phần mềm kho tri thức”"
        buf = io.StringIO()
        with patch.object(tool, "chay", lambda c, r: (3, {"trang_thai": "LOI", "ma": "PG_KHONG_KET_NOI", "thong_diep": thong_diep})), \
                contextlib.redirect_stdout(buf):
            code = tool.main(["--config", str(ROOT / "cau_hinh.toml"), "--root", str(root)])
        self.assertEqual(code, 3)
        for st in self._qua_ps51(buf.getvalue()):
            self.assertEqual((st["ma"], st["thong_diep"], st["ma_thoat"]), ("PG_KHONG_KET_NOI", thong_diep, 3))
            ten = st["tep_trang_thai"]
        noi_dung = (root / "crm-demo" / ten).read_text(encoding="utf-8")
        self.assertIn(thong_diep, noi_dung)
        self.assertEqual(json.loads(noi_dung)["thong_diep"], thong_diep)


class KhaNangThatTests(unittest.TestCase):
    """Probe THẬT (tools/kiem_runtime.py) chạy dưới Python hiện tại — kiểm phát hiện isolated và thư mục phụ thuộc không nạp.
    Không tạo sitecustomize lạ (không che guard của tiến trình con)."""

    def _probe(self, expect, *flags, them_path=None):
        import subprocess
        import sys
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        if them_path:
            env["PYTHONPATH"] = os.pathsep.join([them_path, *([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])])
        r = subprocess.run([sys.executable, *flags, "-X", "utf8", str(ROOT / "tools" / "kiem_runtime.py"), json.dumps(expect)],
                           env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_probe_that_phu_thuoc_va_isolated(self):
        spec = importlib.util.spec_from_file_location("chon_runtime_t2", ROOT / "tools" / "chon_runtime.py")
        cr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cr)
        dep = tempfile.mkdtemp(prefix="ktt-dep-")
        kq = self._probe({"phu_thuoc": [dep]}, them_path=dep)
        self.assertEqual((kq["phu_thuoc_tren_path"], kq["openpyxl"], kq["isolated"], kq["khoi_dong"]), (True, True, False, None))
        self.assertIsInstance(kq["psycopg"], bool)
        khong = self._probe({"phu_thuoc": [tempfile.mkdtemp(prefix="ktt-dep-khong-")]}, them_path=dep)
        self.assertFalse(khong["phu_thuoc_tren_path"])
        iso = self._probe({"phu_thuoc": [dep]}, "-I", them_path=dep)  # Python isolated bỏ qua PYTHONPATH
        self.assertEqual((iso["isolated"], iso["phu_thuoc_tren_path"]), (True, False))
        self.assertEqual(cr.phan_loai(iso, False), (True, "RUNTIME_ISOLATED"))
        g = self._probe({"phu_thuoc": [], "khoi_dong": dep}, them_path=dep)  # thư mục không có sitecustomize → guard không nạp từ đó
        self.assertFalse(g["khoi_dong"])
        self.assertEqual(cr.phan_loai(g, True)[1], "RUNTIME_GUARD_KHONG_NAP")


if __name__ == "__main__":
    unittest.main()
