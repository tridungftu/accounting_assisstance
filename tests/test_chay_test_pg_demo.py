"""L0-8 vòng 2: test thuần sổ sở hữu/biên xuất, tuyệt đối không nối PostgreSQL."""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools import chay_test_theo_module as R


class _Sql(str):
    def format(self, identifier):
        return _Sql(str(self).replace("{}", '"' + identifier.ten.replace('"', '""') + '"'))

    def as_string(self, connection=None):
        return str(self)


class _Identifier:
    def __init__(self, ten):
        self.ten = ten


class _PgError(Exception):
    pass


class _Duplicate(_PgError):
    pass


class _Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.result = None

    def execute(self, query, params=None, **kwargs):
        self.result = self.connection.raw(query, params)
        return self

    def fetchone(self):
        return self.result


class _Connection:
    def __init__(self, databases=None):
        self.databases = set(databases or ())
        self.info = types.SimpleNamespace(host="127.0.0.1", port=5432)
        self.sql = []
        self.truoc_create = None

    def execute(self, query, params=None):
        return _Cursor(self).execute(query, params)

    def raw(self, query, params=None):
        self.sql.append(str(query))
        if str(query).startswith("SELECT 1 FROM pg_database"):
            return (1,) if params[0] in self.databases else None
        m = re.match(r'(CREATE|DROP) DATABASE "([^"]+)"', str(query))
        if m:
            if m[1] == "CREATE":
                if self.truoc_create:
                    self.truoc_create(m[2])
                if m[2] in self.databases:
                    raise _Duplicate()
                self.databases.add(m[2])
            else:
                self.databases.remove(m[2])
        return None


class PgDemoThuanTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="l08-v2-mock-"))
        self.repo = Path(__file__).resolve().parents[1]
        self.cum = {"host": "127.0.0.1", "port": "5432"}
        self.ma = "a" * 32
        self.tep = self.root / R.SO_GHI_TEN
        self.c = _Connection({"postgres", "kho_test_co_san"})
        self.so = R._SoHuuPg.tao_moi(self.tep, self.ma, self.cum, self.c.databases)
        fake_pg = types.ModuleType("psycopg")
        fake_pg.Cursor = _Cursor
        fake_pg.Error = _PgError
        fake_pg.errors = types.SimpleNamespace(ObjectInUse=type("Busy", (_PgError,), {}), DuplicateDatabase=_Duplicate)
        fake_pg.sql = types.SimpleNamespace(SQL=_Sql, Identifier=Mock(side_effect=_Identifier))
        fake_pg.connect = Mock(side_effect=AssertionError("Test thuần cấm mọi kết nối CSDL"))
        self.pg = fake_pg
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(sys.modules, {"psycopg": fake_pg}))
        self.stack.enter_context(patch.object(R, "_LOC", R._LocBiMat()))
        self.stack.enter_context(patch.object(sys, "stdout", sys.stdout))
        self.stack.enter_context(patch.object(sys, "stderr", sys.stderr))
        self.stack.enter_context(patch.object(_Cursor, "execute", _Cursor.execute))

    def _pg_demo(self):
        pg = object.__new__(R._PgDemo)
        pg.so, pg.so_huu, pg.ma, pg.cum = self.tep, self.so, self.ma, self.cum
        pg.truoc = {"postgres", "kho_test_co_san"}
        pg.chua_xoa, pg.canh_bao, pg.vai_moi = {}, [], []
        pg.da_tao, pg.da_xoa = [], []
        pg.repo, pg.python, pg.phu_thuoc = self.repo, sys.executable, ()
        pg.nhat_ky, pg.thu_muc_tam = self.root, self.root / "tam" / "_pg"
        pg.tep = self.root / "ket-noi-gia.json"
        pg.env_chung, pg.chua_ho_tro = {}, set()
        pg.khoa = None
        return pg

    def _hook(self, pw="bi-mat-gia-123"):
        kn = {"admin_dsn": f"postgresql://demo:{pw}@127.0.0.1:5432/postgres"}
        tkn = types.SimpleNamespace(nap_tep=lambda p: kn)
        with patch.dict(os.environ, {"KHO_PG_DEMO_SO": str(self.tep), "KHO_PG_DEMO_MA": self.ma,
                                    "KHO_PG_DEMO_KET_NOI": "khong-doc-tep-that"}), patch.object(R, "_nap_tien_ich_dsn", return_value=tkn):
            R._bat_bao_ve_con()

    def test_csdl_tien_trinh_khac_xuat_hien_khong_bi_nhan_so_huu(self):
        self.so.dang_ky("kho_test_cua_minh", self.c)
        self.c.databases.update({"kho_test_cua_minh", "kho_test_tien_trinh_khac"})
        pg = self._pg_demo()

        def goi(viec, *args):
            if viec == "liet-ke":
                return {"csdl": sorted(self.c.databases)}
            self.assertEqual(args[:2], (str(self.tep), self.ma))
            return self.so.xoa(self.c, args[2:])

        pg._goi = Mock(side_effect=goi)
        self.assertEqual(pg.don()["da_xoa"], 1)
        self.assertIn("kho_test_tien_trinh_khac", self.c.databases)
        self.assertNotIn("kho_test_tien_trinh_khac", self.so.doc()["muc"])

    def test_chet_sau_create_don_so_xoa_dung_mot_lan(self):
        ten = "kho_test_chet_sau_create"
        self.so.dang_ky(ten, self.c)
        self.c.databases.add(ten)  # tiến trình chết trước khi ghi da_tao/da_xoa
        pg = self._pg_demo()
        pg._goi = Mock(side_effect=lambda viec, path, ma, *names: R._SoHuuPg(Path(path), ma, self.cum).xoa(self.c, names))
        with patch.object(R, "_khoa_loai_tru_pg", return_value=None), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(R._don_theo_so(pg, self.tep), 0)
            self.assertEqual(self.so.doc()["muc"][ten]["trang_thai"], "da_xoa")
            self.c.databases.add(ten)  # người khác dùng lại tên sau khi DROP thành công
            self.assertEqual(R._don_theo_so(pg, self.tep), 0)
        self.assertIn(ten, self.c.databases)
        self.assertEqual(sum(q.startswith("DROP DATABASE") for q in self.c.sql), 1)
        self.assertEqual(pg._goi.call_count, 1)
        with self.assertRaises(ValueError):
            self.so.dang_ky(ten, self.c)

    def test_so_khac_cum_bi_tu_choi_truoc_ket_noi(self):
        kn = {"admin_dsn": "postgresql://demo:gia@127.0.0.1:5433/postgres"}
        with self.assertRaisesRegex(ValueError, "cụm"):
            R._pg_xoa(None, kn, self.tep, self.ma, ["kho_test_a"])
        self.pg.connect.assert_not_called()

    def test_sai_lan_chay_anh_chup_va_ten_la_khong_drop(self):
        with self.assertRaises(ValueError):
            R._SoHuuPg(self.tep, "b" * 32, self.cum)
        d = self.so.doc()
        for ten in ("kho_test_co_san", "postgres", "kho_test_A", "kho_test_a\n"):
            d["muc"][ten] = {"ma_lan_chay": self.ma, "cum": self.cum, "trang_thai": "da_tao"}
        R._ghi_ben(self.tep, d)
        kq = self.so.xoa(self.c, [*d["muc"], "kho_test_khong_so"])
        self.assertEqual(len(kq["tu_choi"]), 5)
        self.assertFalse(any(q.startswith("DROP") for q in self.c.sql))

    def test_ten_khong_con_phai_danh_dau_hoan_tat(self):
        ten = "kho_test_chua_create"
        self.so.dang_ky(ten, self.c)
        self.assertEqual(self.so.xoa(self.c, [ten])["khong_co"], [ten])
        self.c.databases.add(ten)
        self.assertEqual(self.so.xoa(self.c, [ten])["tu_choi"], [ten])
        self.assertIn(ten, self.c.databases)

    def test_hook_ghi_ben_truoc_create_drop_chung_lop_khong_force(self):
        self._hook()
        ten = "kho_test_hook"
        self.c.truoc_create = lambda t: self.assertEqual(self.so.doc()["muc"][t]["trang_thai"], "dang_tao")
        self.c.execute(f'CREATE DATABASE "{ten}"')
        self.assertEqual(self.so.doc()["muc"][ten]["trang_thai"], "da_tao")
        self.c.execute(f'DROP DATABASE "{ten}" WITH (FORCE)')
        self.assertEqual(self.so.doc()["muc"][ten]["trang_thai"], "da_xoa")
        self.pg.sql.Identifier.assert_called_with(ten)
        self.assertFalse(any("FORCE" in q for q in self.c.sql))
        with self.assertRaises(ValueError):
            self.c.execute('DROP DATABASE "kho_test_co_san"')

    def test_create_trung_ten_giua_chung_huy_muc_khong_drop(self):
        self._hook()
        ten = "kho_test_race"
        self.c.truoc_create = lambda t: self.c.databases.add(t)
        with self.assertRaises(_Duplicate):
            self.c.execute(f'CREATE DATABASE "{ten}"')
        self.assertEqual(self.so.doc()["muc"][ten]["trang_thai"], "da_huy")
        self.assertEqual(self.so.xoa(self.c, [ten])["tu_choi"], [ten])
        self.assertIn(ten, self.c.databases)

    def test_drop_dau_ghi_ben_truoc_drop_tiep_theo(self):
        for ten in ("kho_test_a", "kho_test_b"):
            self.so.dang_ky(ten, self.c)
            self.c.databases.add(ten)
        goc = self.c.raw

        def raw(q, p=None):
            if str(q) == 'DROP DATABASE "kho_test_b"':
                self.assertEqual(self.so.doc()["muc"]["kho_test_a"]["trang_thai"], "da_xoa")
                raise KeyboardInterrupt()  # mô phỏng chết trước DROP thứ hai
            return goc(q, p)

        self.c.raw = raw
        with self.assertRaises(KeyboardInterrupt):
            self.so.xoa(self.c, ["kho_test_a", "kho_test_b"])
        self.assertEqual(self.so.doc()["muc"]["kho_test_a"]["trang_thai"], "da_xoa")

    def test_probe_rong_loi_ngoai_nhat_ky_khong_ghi_pth(self):
        pg = self._pg_demo()
        for rc, out in ((0, ""), (1, str(self.root / "site")), (0, str(self.root.parent)),
                        (0, str(self.root / "site" / ".." / ".." / "ngoai"))):
            with self.subTest(rc=rc, out=out), patch.object(R.subprocess, "run", return_value=types.SimpleNamespace(returncode=rc, stdout=out)):
                with self.assertRaisesRegex(RuntimeError, "không ghi .pth"):
                    pg._site_phu_thuoc()
        self.assertEqual(list(self.root.rglob("*.pth")), [])

    def test_probe_hop_le_chi_ghi_trong_nhat_ky_va_co_hook_con(self):
        pg = self._pg_demo()
        site = self.root / "tam" / "site-phu-thuoc" / "site-packages"
        with patch.object(R.subprocess, "run", return_value=types.SimpleNamespace(returncode=0, stdout=str(site))):
            pg._site_phu_thuoc()
        pth = site / "ktt-phu-thuoc.pth"
        self.assertTrue(pth.resolve().is_relative_to(self.root))
        self.assertIn("_bat_bao_ve_pth", pth.read_text(encoding="utf-8"))

    def test_pth_bao_ve_loi_phai_dung_khong_tiep_tuc_python(self):
        with patch.object(R, "_bat_bao_ve_con", side_effect=ValueError("sổ sai")), patch.object(R.os, "_exit") as thoat, contextlib.redirect_stderr(io.StringIO()):
            R._bat_bao_ve_pth()
        thoat.assert_called_once_with(2)

    def _site_that(self, pg):
        pg._site_phu_thuoc()
        return next(self.root.rglob("ktt-phu-thuoc.pth")).parent

    def _chay_pth(self, site, ma, env=None):
        # -S + addsitedir thực thi .pth thật nhưng không dùng user site của máy chạy test.
        return subprocess.run([sys.executable, "-X", "utf8", "-S", "-c",
                               "import site; site.addsitedir(" + repr(str(site)) + "); " + ma],
                              env=env or R._moi_truong(self.repo, self.root, them={"KHO_PG_DEMO_SO": str(self.tep)}),
                              cwd=self.root, capture_output=True, timeout=10)

    def test_pth_nap_tep_loi_thoat_ma_2_khong_chay_test_con(self):
        site = self._site_that(self._pg_demo())
        ma = "import importlib.util; importlib.util.spec_from_file_location = lambda *a: None; "
        r = subprocess.run([sys.executable, "-X", "utf8", "-S", "-c",
                            ma + "import site; site.addsitedir(" + repr(str(site)) + "); print('TEST_DA_CHAY')"],
                           env=R._moi_truong(self.repo, self.root, them={"KHO_PG_DEMO_SO": str(self.tep)}),
                           capture_output=True, timeout=10)
        self.assertEqual(r.returncode, 2, r.stderr.decode("utf-8", errors="replace"))
        self.assertNotIn(b"TEST_DA_CHAY", r.stdout)

    def test_pth_hook_loi_thuc_te_thoat_ma_2(self):
        site = self._site_that(self._pg_demo())
        # Không có tệp kết nối/sổ hợp lệ: hook phải dừng dù import chính nó thành công.
        r = self._chay_pth(site, "print('TEST_DA_CHAY')")
        self.assertEqual(r.returncode, 2)
        self.assertNotIn(b"TEST_DA_CHAY", r.stdout)

    def test_pth_repo_khac_van_nap_dung_bao_ve_tu_duong_dan(self):
        repo_cu = self.root / "worktree-cu"
        (repo_cu / "tools").mkdir(parents=True)
        (repo_cu / "tools" / "__init__.py").write_text("", encoding="utf-8")
        (repo_cu / "tools" / "chay_test_theo_module.py").write_text("# Bản cũ chưa có bảo vệ\n", encoding="utf-8")
        (repo_cu / "psycopg.py").write_text(
            "class Cursor:\n def execute(self, *a, **kw): raise AssertionError('Cấm nối CSDL')\n", encoding="utf-8")
        pg = self._pg_demo()
        pg.repo = repo_cu
        dsn = "postgresql://demo:gia@127.0.0.1:5432/postgres"
        pg.tep.write_text(json.dumps({"phien_ban": 1, "admin_dsn": dsn, "app_dsn": dsn}), encoding="utf-8")
        site = self._site_that(pg)
        env = R._moi_truong(repo_cu, self.root, them={**pg._env_so()})
        r = self._chay_pth(site, "import sys, psycopg; "
                           "assert psycopg.Cursor.execute._pg_demo; "
                           "print(sys.modules[psycopg.Cursor.execute.__module__].__file__)", env)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", errors="replace"))
        self.assertEqual(Path(r.stdout.decode("utf-8").strip()).resolve(), Path(R.__file__).resolve())

    def test_timeout_giet_ca_chau_giu_stdout_va_tra_treo_dung_han(self):
        pid_chau = self.root / "pid-chau.txt"
        goc_popen = subprocess.Popen
        da_tao = []
        pw = "bi-mat-trong-stdout-123"
        R._LOC = R._LocBiMat({"admin_dsn": f"postgresql://demo:{pw}@127.0.0.1/postgres"})
        ma_chau = "import os, time; from pathlib import Path; " + f"Path({str(pid_chau)!r}).write_text(str(os.getpid()), encoding='utf-8'); time.sleep(600)"

        def popen(cmd, **kwargs):
            self.assertEqual(kwargs["stdout"], subprocess.PIPE)
            # Tiến trình giả thay test con PostgreSQL: không cần driver/kết nối CSDL.
            ma = ("import subprocess, sys, time; from pathlib import Path; "
                  f"Path({cmd[-1]!r}).write_text('{{\"e\":\"bd\",\"id\":\"test_gia.treo\"}}\\n', encoding='utf-8'); "
                  f"subprocess.Popen([sys.executable, '-c', {ma_chau!r}]); "
                  f"print({pw!r}, flush=True); time.sleep(600)")
            proc = goc_popen([sys.executable, "-X", "utf8", "-c", ma], **kwargs)
            da_tao.append(proc)
            return proc

        try:
            bd = time.monotonic()
            # taskkill phải dùng Popen thật, chỉ thay lệnh --con.
            def chon(cmd, **kwargs):
                return popen(cmd, **kwargs) if "--con" in cmd else goc_popen(cmd, **kwargs)
            with patch.object(R.subprocess, "Popen", side_effect=chon):
                r = R._chay_mot_module(self.repo, "test_gia_treo", 3, self.root, sys.executable,
                                       them_env={"KHO_PG_DEMO_SO": str(self.tep)})
            self.assertLess(time.monotonic() - bd, 8)
            self.assertEqual(r["treo"], 1)
            self.assertEqual(r["test_treo"], "test_gia.treo")
            self.assertGreaterEqual(r["giay"], 3)
            self.assertLess(r["giay"], 8)
            self.assertTrue(pid_chau.exists(), "Cháu phải khởi động trước timeout")
            pid = int(pid_chau.read_text(encoding="utf-8"))
            if os.name == "nt":
                import ctypes
                from ctypes import wintypes as W
                k = ctypes.WinDLL("kernel32", use_last_error=True)
                k.OpenProcess.argtypes, k.OpenProcess.restype = (W.DWORD, W.BOOL, W.DWORD), W.HANDLE
                k.WaitForSingleObject.argtypes, k.WaitForSingleObject.restype = (W.HANDLE, W.DWORD), W.DWORD
                k.CloseHandle.argtypes, k.CloseHandle.restype = (W.HANDLE,), W.BOOL
                handle = k.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE; không dựa vào tasklist bị sandbox cấm.
                if handle:
                    try:
                        self.assertEqual(k.WaitForSingleObject(handle, 0), 0, "Cháu vẫn còn chạy")
                    finally:
                        k.CloseHandle(handle)
                else:
                    self.assertEqual(ctypes.get_last_error(), 87, "Không xác minh được cháu đã thoát")
            else:
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
            log = (self.root / "test_gia_treo.log").read_text(encoding="utf-8")
            self.assertNotIn(pw, log)
            self.assertIn("DA_AN", log)
        finally:
            # Chỉ dọn cây do ca này tạo nếu assertion sớm thất bại.
            for proc in da_tao:
                if proc.poll() is None:
                    R._giet_cay(proc)
                    proc.wait(timeout=5)

    def test_pipe_va_close_bi_giu_van_khong_keo_dai_timeout(self):
        tha = threading.Event()

        class OngGiu(io.RawIOBase):
            def readable(self):
                return True

            def readinto(self, buf):
                tha.wait()
                return 0

            def close(self):
                tha.wait()  # Mô phỏng khóa CRT khi luồng khác còn đọc pipe.
                super().close()

        proc = Mock(stdout=OngGiu())
        proc.wait.side_effect = [subprocess.TimeoutExpired("gia", 3), 1]
        canh = threading.Timer(8, tha.set)
        canh.start()
        try:
            bd = time.monotonic()
            with patch.object(R.subprocess, "Popen", return_value=proc), patch.object(R, "_gan_job_windows", return_value=None), patch.object(R, "_giet_cay") as giet:
                r = R._chay_mot_module(self.repo, "test_ong_giu", 3, self.root, sys.executable)
            self.assertLess(time.monotonic() - bd, 5)
            self.assertEqual(r["treo"], 1)
            giet.assert_called_once_with(proc)
            proc.communicate.assert_not_called()
            self.assertEqual([c.kwargs["timeout"] for c in proc.wait.call_args_list], [3, 2])
        finally:
            tha.set()
            canh.cancel()

    def test_noi_bo_pg_xoa_khong_so_bi_chan(self):
        kn = {"admin_dsn": "postgresql://demo:gia@127.0.0.1:5432/postgres"}
        with patch.object(R, "_nap_tien_ich_dsn", return_value=types.SimpleNamespace(nap_tep=lambda p: kn)), patch.object(sys, "path", sys.path.copy()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(R._chay_viec_pg(["xoa", "tep-gia", str(self.repo), "kho_test_co_san"]), 1)
        self.pg.connect.assert_not_called()

    def test_drop_tu_choi_ket_noi_thuc_te_khac_cum(self):
        self.so.dang_ky("kho_test_a", self.c)
        self.c.info.port = 5433
        with self.assertRaisesRegex(ValueError, "cụm"):
            self.so.xoa(self.c, ["kho_test_a"])
        self.assertFalse(any(q.startswith("DROP") for q in self.c.sql))

    def test_cap_csdl_hai_module_va_skip_ca_vai_tro_duoi_pg_demo(self):
        pg = self._pg_demo()
        pg.env_chung = {"KHO_PG_DEMO_SO": str(self.tep)}
        pg._goi, pg.ho_cua = Mock(return_value={}), Mock(return_value=[])
        for module in ("test_ket_noi", "test_pg_schema"):
            env, _ = R._chuan_bi_pg_module(pg, self.repo, module)
            self.assertTrue(R._RE_TEN_TAM.fullmatch(env["KHO_PG_DEMO_DB"]))
            pg._goi.assert_called_with("tao-vide", env["KHO_PG_DEMO_DB"])
        from tests.test_pg_schema import PostgresSchemaTest
        case = PostgresSchemaTest("test_t15_vai_tro_ke_toan_khong_thay_bao_mat")
        with patch.dict(os.environ, pg.env_chung), self.assertRaisesRegex(unittest.SkipTest, "vai trò cấp cụm"):
            case.test_t15_vai_tro_ke_toan_khong_thay_bao_mat()
        self.pg.connect.assert_not_called()

    def test_clone_trung_ten_phai_dung_truoc_migrate_seed(self):
        from kho_tri_thuc.k2 import crm_khoi_dong as KD
        dsn = "postgresql://demo:gia@127.0.0.1:5432/postgres"
        with patch.object(R, "_pg_tao_vide", side_effect=ValueError("Tên đã có")), patch.object(KD, "chuan_bi") as chuan_bi:
            with self.assertRaisesRegex(ValueError, "Tên đã có"):
                R._pg_tao_clone(None, {"admin_dsn": dsn, "app_dsn": dsn}, "kho_test_trung", "02c")
        chuan_bi.assert_not_called()
        self.pg.connect.assert_not_called()

    def test_mat_khau_traceback_stdout_khong_lo_o_bat_ky_bien_xuat(self):
        pw = "gia!MatKhau-123"
        dsn = f"postgres://demo:{pw}@127.0.0.1:5432/postgres"
        R._LOC = R._LocBiMat({"admin_dsn": dsn})
        console = io.StringIO()
        ghi = []
        goc = Path.write_text

        def write_text(path, data, *args, **kwargs):
            ghi.append(data)
            return goc(path, data, *args, **kwargs)

        def popen(cmd, **kwargs):
            self.assertEqual(kwargs["stdout"], R.subprocess.PIPE)
            proc = Mock(returncode=0)

            def wait(**kw):
                with Path(cmd[-1]).open("a", encoding="utf-8") as f:
                    kq = R._KetQuaGhiTienDo(f)

                    class Hong(unittest.TestCase):
                        def runTest(self):
                            raise RuntimeError(f"{pw} {dsn} password='{pw}'")

                    kq._ghi(e="tong", n=1)
                    Hong().run(kq)
                    kq._ghi(e="het")
                return 0

            proc.stdout = io.BytesIO(f"stdout {pw}\nstderr {dsn}\npassword='{pw}'\n".encode())
            proc.wait.side_effect = wait
            return proc

        with contextlib.redirect_stdout(console), contextlib.redirect_stderr(console), patch.object(Path, "write_text", write_text), patch.object(R.subprocess, "Popen", side_effect=popen):
            R._gan_loc({"admin_dsn": dsn}, None)
            r = R._chay_mot_module(self.repo, "test_gia", 1, self.root, sys.executable,
                                   them_env={"KHO_PG_DEMO_SO": str(self.tep)})
            R._ghi_json(self.root / "ket-qua.json", {"test_gia": r})
            print(r["_tb_dau"])
            print(dsn, file=sys.stderr)
        # Chạy luồng main hoàn toàn bằng mock: kiểm cả JSON chi tiết và console tổng kết.
        pg = self._pg_demo()
        pg.khoi_dong = Mock()
        pg.ket_thuc = Mock(return_value={"loi_don": pw, "sot_theo_so": [], "ro_ri_mat_khau_so_tep": 0})
        pg.quet_ro_ri = Mock(return_value=0)
        pg.don = Mock(return_value={})
        pg.tep.write_text("{}", encoding="utf-8")
        r["loi_dau"] = r["_tb_dau"] = pw + " " + dsn
        r["_dong_loi"] = [pw + " password='" + pw + "'"]
        with contextlib.redirect_stdout(console), contextlib.redirect_stderr(console), patch.object(Path, "write_text", write_text), patch.object(R, "_PgDemo", return_value=pg), patch.object(R, "_tim_module", return_value=["test_gia"]), patch.object(R, "_chuan_bi_pg_module", return_value=({}, {"ho": []})), patch.object(R, "_chay_mot_module", return_value=r), patch.object(R.subprocess, "run", return_value=types.SimpleNamespace(returncode=0, stdout="gia")):
            R._gan_loc({"admin_dsn": dsn}, None)
            self.assertEqual(R.main([str(self.repo), "--pg-demo", str(pg.tep), "--nhat-ky", str(self.root), "--ra", str(self.root / "main.json")]), 1)
        self.assertEqual(r["error"], 1)
        self.assertNotIn(pw, console.getvalue())
        self.assertNotIn(dsn, console.getvalue())
        for data in ghi:
            self.assertNotIn(pw, data)
        for p in self.root.rglob("*"):
            if p.is_file():
                self.assertNotIn(pw.encode(), p.read_bytes(), str(p))
                self.assertNotIn(dsn.encode(), p.read_bytes(), str(p))
        self.assertIn("DA_AN", (self.root / "test_gia.log").read_text(encoding="utf-8"))

    def test_bo_loc_khong_bo_qua_mat_khau_ngan_va_json_escape(self):
        tkn = R._nap_tien_ich_dsn()
        for pw in ("a!", "giả\\'bí\nmật"):
            dsn = "host=127.0.0.1 password='" + pw.replace("\\", "\\\\").replace("'", "\\'") + "'"
            loc = R._LocBiMat({"admin_dsn": dsn}, tkn)
            self.assertNotIn(pw, loc.text(pw))
            self.assertNotIn(json.dumps(pw)[1:-1], loc.text(json.dumps(pw)))

    def test_luong_log_loc_ca_mat_khau_co_xuong_dong(self):
        pw = "bi-mat-dong-mot\nbi-mat-dong-hai"
        loc = R._LocBiMat({"admin_dsn": "host=127.0.0.1 password='" + pw + "'"}, R._nap_tien_ich_dsn())
        log = self.root / "log-da-loc.txt"
        R._doc_log_con(io.BytesIO(("stdout " + pw + "\n").encode()), log, threading.Event(), loc)
        sach = log.read_text(encoding="utf-8")
        for manh in pw.splitlines():
            self.assertNotIn(manh, sach)
        self.assertIn("DA_AN", sach)


if __name__ == "__main__":
    unittest.main()
