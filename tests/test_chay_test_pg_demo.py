"""L0-8: test thuần sổ sở hữu/biên xuất, tuyệt đối không nối PostgreSQL."""
from __future__ import annotations

import contextlib
import functools
import importlib.util
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
from tools import pg_demo_ho_03a as H03


def _co_lap_provider(test):
    """Chỉ tiến trình thử dùng provider tự dựng; không đổi hook đã nạp của caller."""
    @functools.wraps(test)
    def chay(self):
        with patch.dict(sys.modules, {"sitecustomize": None}), patch.dict(os.environ, {
                "PYTHONPATH": str(self.repo / "src"),
                "PYTHONUSERBASE": str(self.root / "userbase-trong"),
                "PYTHONNOUSERSITE": ""}):
            return test(self)
    return chay


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
        fake_pg.Connection = _Connection
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
        self.stack.enter_context(patch.object(_Connection, "execute", _Connection.execute))

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

    def _hook(self, pw="bi-mat-gia-123", bo_chay=R):
        kn = {"admin_dsn": f"postgresql://demo:{pw}@127.0.0.1:5432/postgres"}
        tkn = types.SimpleNamespace(nap_tep=lambda p: kn)
        with patch.dict(os.environ, {"KHO_PG_DEMO_SO": str(self.tep), "KHO_PG_DEMO_MA": self.ma,
                                    "KHO_PG_DEMO_KET_NOI": "khong-doc-tep-that"}), patch.object(bo_chay, "_nap_tien_ich_dsn", return_value=tkn):
            bo_chay._bat_bao_ve_con()

    def _hook_qua_guard(self):
        # Thứ tự thật: .pth cài sở hữu -> sitecustomize bọc guard -> _chay_con cài lại.
        self._hook()
        cursor_goc, connection_goc = self.pg.Cursor.execute, self.pg.Connection.execute
        goi_guard = []

        def cursor_guard(cur, query, params=None, **kwargs):
            goi_guard.append(("cursor", str(query)))
            if str(query).lstrip().upper().startswith("DROP DATABASE"):
                return cur  # A517 giữ DROP lại, không gọi lớp bên trong.
            return cursor_goc(cur, query, params, **kwargs)

        def connection_guard(c, query, params=None):
            goi_guard.append(("connection", str(query)))
            if str(query).lstrip().upper().startswith("DROP DATABASE"):
                return _Cursor(c)
            return connection_goc(c, query, params)

        # Cố ý không sao chép _pg_demo/__wrapped__, như guard bọc ngoài A517.
        self.pg.Cursor.execute, self.pg.Connection.execute = cursor_guard, connection_guard
        self.assertFalse(getattr(cursor_guard, "_pg_demo", False))
        self._hook()
        return goi_guard, cursor_guard, connection_guard

    def test_guard_boc_ngoai_create_chi_dang_ky_mot_lan(self):
        goi_guard, cursor_guard, connection_guard = self._hook_qua_guard()
        dang_ky_goc = R._SoHuuPg.dang_ky
        with patch.object(R._SoHuuPg, "dang_ky", autospec=True, side_effect=dang_ky_goc) as dang_ky:
            for qua_cursor in (False, True):
                ten = "kho_test_guard_cursor" if qua_cursor else "kho_test_guard_connection"
                c = _Cursor(self.c) if qua_cursor else self.c
                self.c.truoc_create = lambda t: self.assertEqual(self.so.doc()["muc"][t]["trang_thai"], "dang_tao")
                with self.subTest(qua_cursor=qua_cursor):
                    c.execute(f'CREATE DATABASE "{ten}"')
                    self.assertEqual(self.so.doc()["muc"][ten]["trang_thai"], "da_tao")
                    self.assertEqual(len(self.so.doc()["muc"]), 1 + qua_cursor)
                    self.assertEqual(dang_ky.call_count, 1 + qua_cursor)
            self.assertEqual(dang_ky.call_count, 2)  # một lần cho mỗi lệnh/kết nối, hai tên khác nhau
        self.assertEqual(len(self.so.doc()["muc"]), 2)
        self.assertEqual(sum(q.startswith("CREATE DATABASE") for q in self.c.sql), 2)
        self.assertEqual(sum(q.startswith("CREATE DATABASE") for _, q in goi_guard), 3)
        self.assertIs(self.pg.Cursor.execute, cursor_guard)
        self.assertIs(self.pg.Connection.execute, connection_guard)
        self.pg.connect.assert_not_called()

    def test_hook_nap_ten_module_khac_khong_cai_lai_qua_guard(self):
        _, cursor_guard, connection_guard = self._hook_qua_guard()
        spec = importlib.util.spec_from_file_location("_l08_thu_nap_pth", R.__file__)
        ban_pth = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ban_pth)
        self._hook(bo_chay=ban_pth)
        self.assertIs(self.pg.Cursor.execute, cursor_guard)
        self.assertIs(self.pg.Connection.execute, connection_guard)
        self.c.execute('CREATE DATABASE "kho_test_guard_module_khac"')
        self.assertEqual(len(self.so.doc()["muc"]), 1)
        self.assertEqual(sum(q.startswith("CREATE DATABASE") for q in self.c.sql), 1)
        self.pg.connect.assert_not_called()

    def test_hook_da_cai_khong_chap_nhan_so_khac(self):
        _, cursor_guard, _ = self._hook_qua_guard()
        tep_khac = self.root / "so-khac.json"
        R._SoHuuPg.tao_moi(tep_khac, self.ma, self.cum, self.c.databases)
        with patch.object(self, "tep", tep_khac), self.assertRaisesRegex(ValueError, "sổ/lần chạy/cụm khác"):
            self._hook()
        self.assertIs(self.pg.Cursor.execute, cursor_guard)
        self.assertEqual(self.so.doc()["muc"], {})
        self.pg.connect.assert_not_called()

    def test_guard_boc_ngoai_ten_co_san_van_tu_choi(self):
        self._hook_qua_guard()
        self.c.databases.add("kho_test_moi_cua_nguoi_khac")  # xuất hiện sau ảnh chụp
        for ten in ("kho_test_co_san", "kho_test_moi_cua_nguoi_khac"):
            with self.subTest(ten=ten), self.assertRaisesRegex(ValueError, "tên có sẵn/đã dùng"):
                self.c.execute(f'CREATE DATABASE "{ten}"')
        self.assertEqual(self.so.doc()["muc"], {})
        self.assertFalse(any(q.startswith("CREATE DATABASE") for q in self.c.sql))

    def test_guard_boc_ngoai_lenh_create_moi_khong_duoc_dung_lai_ten(self):
        self._hook_qua_guard()
        ten = "kho_test_guard_khong_dung_lai"
        self.c.execute(f'CREATE DATABASE "{ten}"')
        c_khac = _Connection(self.c.databases)
        for c in (self.c, c_khac):
            with self.subTest(cung_ket_noi=c is self.c), self.assertRaisesRegex(ValueError, "tên có sẵn/đã dùng"):
                c.execute(f'CREATE DATABASE "{ten}"')
        self.assertEqual(sum(q.startswith("CREATE DATABASE") for q in self.c.sql + c_khac.sql), 1)
        self.assertEqual(len(self.so.doc()["muc"]), 1)

    def test_guard_giu_drop_cua_test_de_goi_don_sau_module(self):
        goi_guard, _, _ = self._hook_qua_guard()
        ten = "kho_test_guard_giu_drop"
        self.c.execute(f'CREATE DATABASE "{ten}"')
        for c in (self.c, _Cursor(self.c)):
            c.execute(f'DROP DATABASE "{ten}"')
        self.assertIn(ten, self.c.databases)
        self.assertEqual(self.so.doc()["muc"][ten]["trang_thai"], "da_tao")
        self.assertFalse(any(q.startswith("DROP DATABASE") for q in self.c.sql))
        pg = self._pg_demo()
        # _goi là tiến trình quản trị không guard: dùng raw giả, không đi qua execute đã vá.
        class Raw:
            info = self.c.info

            def execute(_, query, params=None):
                result = self.c.raw(query, params)
                return types.SimpleNamespace(fetchone=lambda: result)

        def goi(viec, *args):
            if viec == "liet-ke":
                return {"csdl": sorted(self.c.databases)}
            self.assertEqual((viec, args[:2]), ("xoa", (str(self.tep), self.ma)))
            return self.so.xoa(Raw(), args[2:])

        pg._goi = Mock(side_effect=goi)
        so_goi_guard = len(goi_guard)
        self.assertEqual(pg.don()["da_xoa"], 1)
        self.assertEqual(len(goi_guard), so_goi_guard)
        self.assertNotIn(ten, self.c.databases)
        self.assertEqual(self.so.doc()["muc"][ten]["trang_thai"], "da_xoa")
        self.assertEqual(sum(q.startswith("DROP DATABASE") for q in self.c.sql), 1)
        self.pg.connect.assert_not_called()

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

    def test_drop_bi_nuot_khong_bao_da_xoa_va_don_so_thu_lai_duoc(self):
        ten = "kho_test_drop_bi_nuot"
        self.so.dang_ky(ten, self.c)
        self.c.databases.add(ten)
        raw = self.c.raw

        def nuot_drop(q, p=None):
            if str(q).startswith("DROP DATABASE"):
                self.c.sql.append(str(q))
                return None
            return raw(q, p)

        self.c.raw = nuot_drop
        kq = self.so.xoa(self.c, [ten])
        self.assertEqual(kq["da_xoa"], [])
        self.assertEqual(kq["con_lai_sau_xoa"], [ten])
        self.assertEqual(self.so.doc()["muc"][ten]["trang_thai"], "con_lai_sau_xoa")
        self.assertEqual(self.c.sql[-1], "SELECT 1 FROM pg_database WHERE datname = %s")
        pg = self._pg_demo()
        pg.vai_truoc = set()
        pg.quet_ro_ri = Mock(return_value=0)

        def goi(viec, *args):
            if viec == "liet-ke":
                return {"csdl": sorted(self.c.databases), "vai_tro": []}
            return self.so.xoa(self.c, args[2:])

        pg._goi = Mock(side_effect=goi)
        with patch.object(R.time, "sleep"):
            tong = pg.ket_thuc([])
        self.assertEqual(tong["sot"], [ten])
        self.assertEqual(tong["da_xoa"], 0)
        self.assertIn(ten, pg.chua_xoa)
        self.assertTrue(any(ten in cb for cb in tong["canh_bao"]))
        console = io.StringIO()
        with patch.object(R, "_khoa_loai_tru_pg", return_value=None), contextlib.redirect_stdout(console):
            self.assertEqual(R._don_theo_so(pg, self.tep), 1)
            self.c.raw = raw
            self.assertEqual(R._don_theo_so(pg, self.tep), 0)
        self.assertIn("CẢNH BÁO", console.getvalue())
        self.assertNotIn(ten, self.c.databases)
        self.assertEqual(self.so.doc()["muc"][ten]["trang_thai"], "da_xoa")

    def test_kiem_sau_drop_loi_khong_ghi_hoan_tat(self):
        ten = "kho_test_kiem_drop_loi"
        self.so.dang_ky(ten, self.c)
        self.c.databases.add(ten)
        raw = self.c.raw

        def hong_select(q, p=None):
            if str(q) == "SELECT 1 FROM pg_database WHERE datname = %s":
                raise _PgError("không kiểm được")
            return raw(q, p)

        self.c.raw = hong_select
        kq = self.so.xoa(self.c, [ten])
        self.assertEqual(kq["da_xoa"], [])
        self.assertEqual(len(kq["loi"]), 1)
        self.assertEqual(self.so.doc()["muc"][ten]["trang_thai"], "dang_tao")
        self.c.raw = raw
        self.assertEqual(self.so.xoa(self.c, [ten])["khong_co"], [ten])

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

    def test_probe_user_site_goc_loi_khong_ghi_pth(self):
        pg = self._pg_demo()
        site = self.root / "tam" / "site-phu-thuoc" / "site-packages"
        for rc, out in ((1, ""), (0, "")):
            with self.subTest(rc=rc), patch.object(R.subprocess, "run", side_effect=[
                    types.SimpleNamespace(returncode=0, stdout=str(site)),
                    types.SimpleNamespace(returncode=rc, stdout=out)]):
                with self.assertRaisesRegex(RuntimeError, "không ghi .pth"):
                    pg._site_phu_thuoc()
        self.assertEqual(list(self.root.rglob("*.pth")), [])

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

    @_co_lap_provider
    def test_pth_nap_tep_loi_thoat_ma_2_khong_chay_test_con(self):
        site = self._site_that(self._pg_demo())
        ma = "import importlib.util; importlib.util.spec_from_file_location = lambda *a: None; "
        r = subprocess.run([sys.executable, "-X", "utf8", "-S", "-c",
                            ma + "import site; site.addsitedir(" + repr(str(site)) + "); print('TEST_DA_CHAY')"],
                           env=R._moi_truong(self.repo, self.root, them={"KHO_PG_DEMO_SO": str(self.tep)}),
                           capture_output=True, timeout=10)
        self.assertEqual(r.returncode, 2, r.stderr.decode("utf-8", errors="replace"))
        self.assertNotIn(b"TEST_DA_CHAY", r.stdout)

    @_co_lap_provider
    def test_pth_hook_loi_thuc_te_thoat_ma_2(self):
        site = self._site_that(self._pg_demo())
        # Không có tệp kết nối/sổ hợp lệ: hook phải dừng dù import chính nó thành công.
        r = self._chay_pth(site, "print('TEST_DA_CHAY')")
        self.assertEqual(r.returncode, 2)
        self.assertNotIn(b"TEST_DA_CHAY", r.stdout)

    @_co_lap_provider
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

    def _provider_guard_thu(self, thu_muc, sitecustomize=True):
        """Provider TEST có hook thật; SHA khác A517 nên không được host chấp nhận."""
        thu_muc.mkdir(parents=True, exist_ok=True)
        (thu_muc / "codex_no_delete_guard.py").write_text(
            "import os, shutil\n"
            "def chan(*a, **kw):\n    raise PermissionError('DEMO giữ tệp')\n"
            "os.remove = os.unlink = shutil.rmtree = chan\n", encoding="utf-8")
        if sitecustomize:
            (thu_muc / "sitecustomize.py").write_text("import codex_no_delete_guard\n", encoding="utf-8")
        else:
            (thu_muc / "guard-thu.pth").write_text("import codex_no_delete_guard\n", encoding="utf-8")

    def _kiem_hook_con_va_chau(self, env, ma_host="GUARD_SHA_SAI"):
        # Chỉ import/đọc chứng cứ trong các tiến trình thật: không mở host/server/CSDL.
        kiem = ("from kho_tri_thuc.nguon import trich6_host as H; "
                "from kho_tri_thuc.m4.review_compute import guard_dang_nap; "
                "cc = H.chung_cu_guard(); "
                "assert cc['module'] and cc['flag'] and cc['bytecode_tat'], cc; "
                "assert H.HOOK_BAT_BUOC <= set(cc['hooks']), cc; "
                "assert guard_dang_nap()[0], guard_dang_nap(); "
                f"assert H.guard_hop_le(cc) == {ma_host!r}, cc")
        ma = ("import subprocess, sys; " + kiem + "; "
              "from kho_tri_thuc.k2.xay_dung import XayDungK2; "
              "envs = [H.env_con(), XayDungK2._env_worker()]; "
              "assert all('KHO_PG_DEMO_SO' not in e for e in envs); "
              f"rs = [subprocess.run([sys.executable, '-X', 'utf8', '-c', {kiem!r}], "
              "env=e, capture_output=True, timeout=15) for e in envs]; "
              "assert all(r.returncode == 0 for r in rs), [(r.stdout, r.stderr) for r in rs]")
        r = subprocess.run([sys.executable, "-X", "utf8", "-c", ma], env=env, cwd=self.root,
                           capture_output=True, timeout=40)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", errors="replace"))

    @_co_lap_provider
    def test_runtime_khoi_dong_cai_hook_o_con_va_chau(self):
        kd = self.root / "khởi động"
        self._provider_guard_thu(kd)
        runtime = self.root / "runtime.json"
        runtime.write_text(json.dumps({"python": sys.executable, "duong_dan_phu_thuoc": [],
                                       "thu_muc_khoi_dong": kd.name}), encoding="utf-8")
        py, deps = R._doc_runtime(runtime)
        self.assertEqual(py, sys.executable)
        self.assertIn(kd, deps)
        env = R._moi_truong(self.repo, self.root, deps, {"CODEX_NO_DELETE_FILES": "1",
                                                       "PYTHONUSERBASE": str(self.root / "userbase-trong")})
        self._kiem_hook_con_va_chau(env)
        # .pth PG cũng giữ provider khi test tự ghi đè PYTHONPATH=src.
        pg = self._pg_demo()
        pg.phu_thuoc = deps
        with patch.dict(os.environ, {"PYTHONUSERBASE": env["PYTHONUSERBASE"]}):
            env["PYTHONUSERBASE"] = pg._site_phu_thuoc()
        env["PYTHONPATH"] = str(self.repo / "src")
        self._kiem_hook_con_va_chau(env)

    def test_runtime_tu_choi_duong_khoi_dong_sai(self):
        runtime = self.root / "runtime.json"
        for kd in (1, "", "khong-co"):
            with self.subTest(kd=kd):
                runtime.write_text(json.dumps({"python": sys.executable, "duong_dan_phu_thuoc": [],
                                               "thu_muc_khoi_dong": kd}), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "thu_muc_khoi_dong"):
                    R._doc_runtime(runtime)

    @_co_lap_provider
    def test_giu_provider_pythonpath_cua_caller(self):
        kd = self.root / "provider-caller"
        self._provider_guard_thu(kd)
        with patch.dict(os.environ, {"PYTHONPATH": str(kd) + os.pathsep + str(self.root / "repo-khac")}):
            env = R._moi_truong(self.repo, self.root, them={"CODEX_NO_DELETE_FILES": "1",
                                                          "PYTHONUSERBASE": str(self.root / "userbase-trong")})
        self.assertNotIn(str(self.root / "repo-khac"), env["PYTHONPATH"])
        self._kiem_hook_con_va_chau(env)

    @_co_lap_provider
    def test_userbase_pg_chuyen_tiep_pth_guard_goc_cho_chau(self):
        import sysconfig
        ub = self.root / "userbase-goc"
        scheme = "nt_user" if os.name == "nt" else "posix_user"
        site = Path(sysconfig.get_path("purelib", scheme, vars={"userbase": str(ub)}))
        self._provider_guard_thu(site, sitecustomize=False)
        with patch.dict(os.environ, {"PYTHONUSERBASE": str(ub), "PYTHONPATH": str(self.repo / "src")}):
            pg = self._pg_demo()
            moi = pg._site_phu_thuoc()
            env = R._moi_truong(self.repo, self.root, them={"PYTHONUSERBASE": moi, "CODEX_NO_DELETE_FILES": "1"})
        self._kiem_hook_con_va_chau(env)

    @_co_lap_provider
    def test_duong_khoi_dong_bo_sitecustomize_khong_co_guard(self):
        la = self.root / "site-packages-la"
        la.mkdir()
        tep = la / "sitecustomize.py"
        tep.write_text("# Không phải provider guard\n", encoding="utf-8")
        kd = self.root / "provider-hop-le"
        self._provider_guard_thu(kd)
        with patch.dict(os.environ, {"PYTHONPATH": os.pathsep.join((str(la), str(kd)))}), \
                patch.dict(sys.modules, {"sitecustomize": types.SimpleNamespace(__file__=str(tep))}):
            self.assertEqual(R._duong_khoi_dong(), (kd,))
        with patch.dict(sys.modules, {"sitecustomize": types.SimpleNamespace(__file__=str(kd / "sitecustomize.py"))}):
            self.assertEqual(R._duong_khoi_dong(), (kd,))

    @_co_lap_provider
    def test_goi_pg_khong_nap_provider_nhung_test_van_giu_guard(self):
        pg = self._pg_demo()
        kd = self.root / "provider-runtime"
        caller = self.root / "provider-caller"
        deps = self.root / "phu-thuoc"
        deps.mkdir()
        self._provider_guard_thu(kd)
        self._provider_guard_thu(caller)
        runtime = self.root / "runtime.json"
        runtime.write_text(json.dumps({"python": sys.executable, "duong_dan_phu_thuoc": [deps.name],
                                       "thu_muc_khoi_dong": kd.name}), encoding="utf-8")
        pg.python, pg.phu_thuoc = R._doc_runtime(runtime)
        with patch.dict(os.environ, {"PYTHONPATH": str(caller), "CODEX_NO_DELETE_FILES": "1"}), \
                patch.dict(sys.modules, {"sitecustomize": types.SimpleNamespace(__file__=str(caller / "sitecustomize.py"))}), \
                patch.object(R.subprocess, "run", return_value=types.SimpleNamespace(stdout='{"ok": true}', returncode=0)) as run:
            for viec in ("liet-ke", "tao-clone", "xoa"):
                pg._goi(viec)
                env = run.call_args.kwargs["env"]
                self.assertEqual(env["PYTHONPATH"].split(os.pathsep), [str(self.repo / "src"), str(self.repo), str(deps)])
                self.assertEqual(env["PYTHONNOUSERSITE"], "1")
                self.assertEqual(env["CODEX_NO_DELETE_FILES"], "1")
                self.assertEqual(env["KHO_PG_DEMO_SO"], str(self.tep))
            env_test = R._moi_truong(self.repo, self.root, pg.phu_thuoc)
        self.assertIn(str(kd), env_test["PYTHONPATH"].split(os.pathsep))
        self.assertIn(str(caller), env_test["PYTHONPATH"].split(os.pathsep))
        self.assertEqual(env_test["CODEX_NO_DELETE_FILES"], "1")
        self.pg.connect.assert_not_called()

    def test_thieu_hook_tien_trinh_that_van_dung_guard_khong_nap(self):
        # -I bỏ cả hai provider, -B vẫn giữ yêu cầu không bytecode. Không import bù guard.
        cfg = {"kieu": "trich6_host_cau_hinh/v1", "token": "d" * 40, "nguon": str(self.root / "nguon-khong-mo"),
               "du_lieu": str(self.root / "khong-duoc-tao"), "instance_id": "demo"}
        ma = (f"import sys; sys.path.insert(0, {str(self.repo / 'src')!r}); "
              "from kho_tri_thuc.m4 import review_compute as C; "
              f"assert C.main([{cfg['du_lieu']!r}]) == C.MA_GUARD_KHONG_NAP == 4; "
              "from kho_tri_thuc.nguon import trich6_host as H; sys.exit(H._con(kenh=sys.stdout))")
        env = R._moi_truong(self.repo, self.root, them={"CODEX_NO_DELETE_FILES": "1"})
        r = subprocess.run([sys.executable, "-I", "-B", "-c", ma], env=env, cwd=self.root,
                           input=json.dumps(cfg).encode("utf-8"), capture_output=True, timeout=15)
        self.assertEqual(r.returncode, 4, r.stderr.decode("utf-8", errors="replace"))
        self.assertEqual(json.loads(r.stdout)["ma"], "GUARD_KHONG_NAP")
        self.assertIn(b"GUARD_KHONG_NAP", r.stderr)
        self.assertFalse(Path(cfg["du_lieu"]).exists())

    def test_guard_a517_that_o_chau_khi_runtime_co_provider(self):
        from kho_tri_thuc.nguon import trich6_host as H
        cc = H.chung_cu_guard()
        if not cc["module"]:
            self.skipTest("runtime không có provider guard A517 thật — lead chạy test với --runtime DEMO")
        self.assertIsNone(H.guard_hop_le(cc), cc)
        pg = self._pg_demo()
        env = R._moi_truong(self.repo, self.root, them={"PYTHONUSERBASE": pg._site_phu_thuoc()})
        env["PYTHONPATH"] = str(self.repo / "src")
        self._kiem_hook_con_va_chau(env, ma_host=None)

    @_co_lap_provider
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

    def test_ho_03a_nhan_dung_hai_module_khong_bat_test_thuan(self):
        pg = self._pg_demo()
        nhan = {p.stem for p in (self.repo / "tests").glob("test_*.py")
                if "03a" in pg.ho_cua(p.read_text(encoding="utf-8"))}
        self.assertEqual(nhan, {"test_m4_03a_pg", "test_m4_03b_common_pg"})
        self.assertNotIn("03a", R.HO_CHUA_HO_TRO)
        self.assertEqual(pg.chua_ho_tro, set())

    def test_03a_ghim_ordinal_checksum_registry_hien_hanh(self):
        from kho_tri_thuc.ha_tang.pg_migrations import PG_MIGRATIONS
        from kho_tri_thuc.m4.sql_duyet import M0024_M4_DUYET
        from kho_tri_thuc.m4.sql_ke_toan_nghiem_thu import M4_03A_SQL
        he, env = R._dac_ta_ho("03a", "kho_test_pgd_0123456789ab")
        self.assertEqual(he["m4_03a_clone_provenance"], env["KHO_M4_03A_CLONE_PROVENANCE"])
        self.assertIs(PG_MIGRATIONS[int(env["KHO_M4_03A_VERSION"]) - 1], M4_03A_SQL)
        self.assertEqual(env["KHO_M4_03A_M24_SHA256"], R._sha_sql(M0024_M4_DUYET))
        self.assertEqual(env["KHO_M4_03A_SHA256"], R._sha_sql(M4_03A_SQL))
        self.assertEqual(env["KHO_M4_03B_DA_AP_DUNG"], "1")
        self.assertEqual(len({env["KHO_M4_03A_" + k] for k in ("KT1", "KT2", "KT_KHAC")}), 3)

    def test_03a_registry_thieu_m33_khong_cap_co_da_ap_dung(self):
        from kho_tri_thuc.ha_tang import pg_migrations as PGM
        from kho_tri_thuc.k2.sql_ghi_nhan_so_tien import M4_03B_SO_TIEN_SQL
        with patch.object(PGM, "PG_MIGRATIONS", tuple(s for s in PGM.PG_MIGRATIONS if s is not M4_03B_SO_TIEN_SQL)):
            with self.assertRaisesRegex(ValueError, "Registry"):
                H03.dac_ta("nguon-gia")

    def test_03a_clone_moi_moi_module_du_env_khong_log_dsn_va_don_dung_so(self):
        from kho_tri_thuc.k2 import crm_khoi_dong as KD
        from kho_tri_thuc.ha_tang.pg_migrations import PG_SCHEMA_VERSION
        pg = self._pg_demo()
        pg.admin = dict(host="127.0.0.1", port="5432", user="chu", password="gia-bi-mat-chu", dbname="kho_crm_demo")
        pg.app = {**pg.admin, "user": "web", "password": "gia-bi-mat-web"}
        kn = {"admin_dsn": R._uri(pg.admin, "kho_crm_demo"), "app_dsn": R._uri(pg.app, "kho_crm_demo")}
        self.pg.connect.side_effect = lambda *a, **k: contextlib.nullcontext(Mock())
        tkn = R._nap_tien_ich_dsn()
        optional = {"KHO_M4_03B_HOA_DON_ID": "hoa-don-demo", "KHO_M4_03B_DONG_ID": "dong-demo"}
        tao = []

        def tao_vide(kn, ten):
            self.assertRegex(ten, r"^kho_test_[a-z0-9_]+$")
            self.so.dang_ky(ten, self.c)
            self.c.databases.add(ten)
            tao.append(ten)

        def goi(viec, ten, ho, **kw):
            self.assertEqual((viec, ho), ("tao-clone", "03a"))
            result = R._pg_tao_clone(tkn, kn, ten, ho)
            # JSON trả từ tiến trình dựng clone không được mang DSN.
            sach = json.dumps(result)
            self.assertNotIn("postgresql://", sach)
            self.assertNotIn("gia-bi-mat", sach)
            return result

        pg._goi = Mock(side_effect=goi)
        console = io.StringIO()
        with patch.object(R, "_pg_tao_vide", side_effect=tao_vide), \
                patch.object(KD, "chuan_bi", return_value={"schema_sau": PG_SCHEMA_VERSION}) as boot, \
                patch.object(KD, "chuan_hoa_dsn", side_effect=lambda dsn, _: {"conninfo": dsn}), \
                patch.object(H03, "dung_du_lieu", return_value=optional) as seed, contextlib.redirect_stdout(console):
            for module in ("test_m4_03a_pg", "test_m4_03b_common_pg"):
                env, info = R._chuan_bi_pg_module(pg, self.repo, module)
                self.assertEqual(info, {"ho": ["03a"]})
                du = {"KHO_M4_03A_" + k for k in ("CLONE_DSN", "CLONE_APP_DSN", "CLONE_DB", "CLONE_PROVENANCE",
                                                       "M24_SHA256", "VERSION", "SHA256", "KT1", "KT2", "KT_KHAC")}
                du |= {"KHO_M4_03B_" + k for k in ("DA_AP_DUNG", "HOA_DON_ID", "DONG_ID", "CFO", "XEM")}
                self.assertEqual(set(env), du)
                ten = env["KHO_M4_03A_CLONE_DB"]
                self.assertNotIn("kho_crm_demo", env["KHO_M4_03A_CLONE_DSN"])
                self.assertTrue(env["KHO_M4_03A_CLONE_DSN"].endswith("/" + ten))
                self.assertTrue(env["KHO_M4_03A_CLONE_APP_DSN"].endswith("/" + ten))
                # Tiến trình con test nhận đủ biến, biến môi trường của cha giữ nguyên.
                self.assertEqual({k: v for k, v in R._moi_truong(self.repo, self.root, them=env).items() if k in du}, env)
                seed.assert_called_with(boot.call_args.args[0]["admin_dsn"], boot.call_args.args[0]["app_dsn"], ten)
                R._ghi_json(self.root / (module + ".json"), {module: info})
                self.assertEqual(self.so.xoa(self.c, [ten])["da_xoa"], [ten])
        self.assertEqual(len(set(tao)), 2)
        self.assertNotIn("postgresql://", console.getvalue())
        self.assertNotIn("gia-bi-mat", console.getvalue())
        self.assertFalse(any("kho_crm_demo" in sql for sql in self.c.sql))
        for p in self.root.glob("*.json"):
            self.assertNotIn("gia-bi-mat", p.read_text(encoding="utf-8"))

    def test_03a_khong_nhan_so_huu_hay_drop_csdl_crm_demo(self):
        for ten in ("kho_crm_demo", "kho_crm_demo_lt_l08d"):
            with self.assertRaises(ValueError):
                self.so.dang_ky(ten, self.c)
            self.assertEqual(self.so.xoa(self.c, [ten])["tu_choi"], [ten])
            with self.assertRaises(ValueError):
                R._pg_tao_clone(None, {}, ten, "03a")
        self.pg.connect.assert_not_called()

    def test_03a_helper_chan_db_demo_va_cap_dsn_khac_clone_truoc_connect(self):
        from kho_tri_thuc.k2 import crm_khoi_dong as KD
        rows = types.ModuleType("psycopg.rows")
        rows.dict_row = object()
        with patch.dict(sys.modules, {"psycopg.rows": rows}), patch.object(KD, "kiem_cap", return_value={"db": "kho_crm_demo"}):
            for ten in ("kho_crm_demo", "kho_crm_demo_lt_l08d", "kho_test_pgd_0123456789ab"):
                with self.subTest(ten=ten), self.assertRaises(ValueError):
                    H03.dung_du_lieu("chu-gia", "app-gia", ten)
        self.pg.connect.assert_not_called()

    def test_03a_helper_kiem_lineage_va_owner_truoc_nhan_m2_dong_ket_noi(self):
        from kho_tri_thuc.k2 import crm_khoi_dong as KD, hoa_don
        from kho_tri_thuc.ha_tang import postgres as PG
        rows = types.ModuleType("psycopg.rows")
        rows.dict_row = object()
        db = "kho_test_pgd_0123456789ab"
        admin, app, chu = Mock(), Mock(), Mock()
        self.pg.connect.side_effect = [contextlib.nullcontext(c) for c in (admin, app, chu)]
        cap = {"db": db, "admin": {"conninfo": "chu-clone-gia"}, "app": {"conninfo": "app-clone-gia"}}
        thu_tu = Mock()
        with patch.dict(sys.modules, {"psycopg.rows": rows}), patch.object(KD, "kiem_cap", return_value=cap), \
                patch.object(PG, "kiem_lineage_ung_dung") as lineage, patch.object(H03, "_seed_ke_toan") as seed, \
                patch.object(KD, "kiem_ket_noi_chu") as owner, patch.object(hoa_don, "HoaDonK2") as service, \
                patch.object(H03.tempfile, "mkdtemp", return_value=str(self.root)), \
                patch.object(H03, "_nhan_hoa_don", return_value={"KHO_M4_03B_HOA_DON_ID": "hd-demo"}) as nhan:
            for ten, fn in (("lineage", lineage), ("seed", seed), ("owner", owner), ("nhan", nhan)):
                thu_tu.attach_mock(fn, ten)
            self.assertEqual(H03.dung_du_lieu("chu-gia", "app-gia", db), {"KHO_M4_03B_HOA_DON_ID": "hd-demo"})
            self.assertEqual([c[0] for c in thu_tu.mock_calls], ["lineage", "seed", "owner", "nhan"])
            lineage.assert_called_once_with(admin)
            owner.assert_called_once_with(chu, app)
            service.assert_called_once_with(app, self.root, conn_chu=chu)
            nhan.assert_called_once_with(admin, service.return_value)

    def test_03a_seed_dung_ham_m4_ma_tran_rieng_khong_doi_module_san_pham(self):
        from kho_tri_thuc.k2 import m4_demo
        marker, actors = m4_demo.MARKER_DUYET, m4_demo.NGUOI_DUNG_DUYET
        seed = types.SimpleNamespace(khoi_tao_duyet=Mock(return_value={"trang_thai": "DU"}))
        admin = Mock()
        with patch.object(m4_demo, "khoi_tao_duyet", return_value={"trang_thai": "DU"}) as duyet, \
                patch.object(H03.importlib.util, "module_from_spec", return_value=seed), \
                patch.object(H03.importlib.util, "spec_from_file_location", return_value=types.SimpleNamespace(loader=Mock())):
            H03._seed_ke_toan(admin)
        duyet.assert_called_once_with(admin)
        seed.khoi_tao_duyet.assert_called_once_with(admin)
        self.assertEqual(seed.NGUOI_DUNG_DUYET, H03.ACTOR)
        self.assertNotEqual(seed.MARKER_DUYET, marker)
        self.assertEqual((m4_demo.MARKER_DUYET, m4_demo.NGUOI_DUNG_DUYET), (marker, actors))
        self.assertIn("M2", H03.ACTOR[0][2]["PN_DEMO_A"])
        self.assertNotIn("M2", H03.ACTOR[1][2]["PN_DEMO_A"])  # c15: KT2 không có M2
        self.assertTrue(all(a[3] == [("DA_XD_A1", "KE_TOAN")] for a in H03.ACTOR))

    def test_03a_seed_thieu_duyet_dung_khong_tu_cap_lai(self):
        from kho_tri_thuc.k2 import m4_demo
        with patch.object(m4_demo, "khoi_tao_duyet", return_value={"trang_thai": "THIEU"}), \
                patch.object(H03.importlib.util, "spec_from_file_location") as nap:
            with self.assertRaisesRegex(ValueError, "không tự cấp lại"):
                H03._seed_ke_toan(Mock())
        nap.assert_not_called()

    def test_03b_nhan_fixture_va_map_bang_service_that_khong_insert_gia(self):
        from kho_tri_thuc.k2 import m2_demo
        admin, svc = Mock(), Mock()
        admin.execute.return_value.fetchone.side_effect = [("hd-demo",), ("dong-demo",)]
        fact = next(f for f in m2_demo.doc_ung_vien_dong(m2_demo.doc_khai_bao())
                    if f["source_artifact_relative_path"] == "inputs/G01-wrapped-positive.xml")
        svc.chi_tiet.return_value = {"expected_graph": "graph-demo", "dong_nguon_hien_hanh": [
            {"source_row_id": "row-demo", "source_ordinal": fact["source_ordinal"], "locator": fact["source_locator"]}]}
        env = H03._nhan_hoa_don(admin, svc)
        self.assertEqual(env, {"KHO_M4_03B_HOA_DON_ID": "hd-demo", "KHO_M4_03B_DONG_ID": "dong-demo"})
        nhan = svc.nhan.call_args
        self.assertEqual(nhan.args, (H03.INTAKE,))
        self.assertEqual(nhan.kwargs["native"], m2_demo.mau("inputs/G01-wrapped-positive.xml")[1])
        self.assertEqual(nhan.kwargs["source_instance"], fact["source_instance"])
        svc.mapping_line.assert_called_once_with(H03.CFO, client_key="pg-demo-03a-map-g01", hoa_don_id="hd-demo",
                                                expected_graph="graph-demo", source_row_id="row-demo",
                                                logical_line_key=fact["logical_line_key"], evidence_ref=fact["mapping_ref"],
                                                evidence_revision=fact["revision"], reason="CFO DEMO map dòng cho test 03B")
        self.assertTrue(all(c.args[0].lstrip().startswith("SELECT ") for c in admin.execute.call_args_list))

    def test_03b_khong_co_hoa_don_chinh_thuc_de_test_tu_skip(self):
        admin, svc = Mock(), Mock()
        admin.execute.return_value.fetchone.return_value = None
        self.assertEqual(H03._nhan_hoa_don(admin, svc), {})
        svc.mapping_line.assert_not_called()
        svc.chi_tiet.assert_not_called()

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
