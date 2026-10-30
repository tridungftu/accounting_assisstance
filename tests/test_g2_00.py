"""G2-00: chỉ dữ liệu DEMO giả và mock, không kết nối PG/đọc cấu hình máy."""

from __future__ import annotations

import io
import json
import sys
import types
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import tao_core_demo as demo


CANARY = "MAT_KHAU_DEMO_CANARY"
DSN = f"host=127.0.0.1 port=5432 dbname=kho_crm_demo user=admin_demo password='{CANARY}'"
NGUON = {"phien_ban": 1, "app_dsn": DSN, "admin_dsn": DSN}


class KiemDichTests(unittest.TestCase):
    def test_ten_sai_va_dich_that(self):
        for ten in ("kho_that", "postgres", "kho_core_demo_g2_", "kho_core_demo_g2_A",
                    "kho_core_demo_g2_a;DROP DATABASE x", "kho_core_demo_g2_a\n",
                    demo.TIEN_TO + "a" * 47):
            with self.subTest(ten=ten), self.assertRaises(demo.TuChoi):
                demo.kiem_ten_csdl(ten)
        demo.kiem_ten_csdl(demo.TIEN_TO + "a" * 46)

    def test_ma_sai_khong_doc_tep_khong_connect(self):
        with patch.object(demo, "nap_tep") as doc:
            for ma in ("../that", "a/b", "A", "", "a\n", None):
                with self.subTest(ma=ma), self.assertRaises(demo.TuChoi):
                    demo.tao_core_demo(ma)
            doc.assert_not_called()

    def test_duong_dan_cam_ke_ca_windows_tren_linux(self):
        for path in (r"D:\DU-LIEU-KE-TOAN", r"d:/du-lieu-ke-toan/kho",
                     r"C:\repo\var\plhn-that\kho", r"C:\repo\VAR\WEB-THAT\kho",
                     r"C:\repo\var\demo\..\web-that\kho", r"C:\repo\var\web-that.\kho",
                     r"\\?\D:\DU-LIEU-KE-TOAN\kho", r"C:\repo\.env"):
            with self.subTest(path=path), self.assertRaises(demo.TuChoi):
                demo.kiem_duong_dan_cam(path)
        demo.kiem_duong_dan_cam(r"C:\repo\var\core-demo\g2_00\bi-mat")

    def test_tu_choi_chuyen_huong_truoc_doc(self):
        path = Path.cwd() / "var" / "core-demo" / "g2_00"
        with patch.object(Path, "resolve", return_value=Path.cwd() / "noi-khac"):
            with self.assertRaises(demo.TuChoi):
                demo._duong_dan_an_toan(path)

    def test_dsn_khong_demo_hoac_gian_tiep(self):
        for dsn in (DSN.replace("kho_crm_demo", "kho_that"), DSN.replace("127.0.0.1", "10.1.1.1"),
                    DSN + " hostaddr=10.1.1.1", DSN + " service=that", DSN + " options='-c x=y'",
                    DSN + " dbname=kho_that", DSN.replace("port=5432 ", ""),
                    DSN.replace(f"password='{CANARY}'", ""), "password='loi"):
            with self.subTest(dsn=dsn), self.assertRaises(demo.TuChoi):
                demo._tham_so_dsn(dsn)

    def test_uri_va_dsn_chi_thay_ten_csdl(self):
        for dsn in (DSN, f"postgresql://admin_demo:{CANARY}@127.0.0.1:5432/kho_crm_demo?sslmode=disable"):
            demo._tham_so_dsn(dsn)
            cu, moi = demo.thay_ten_csdl(dsn, demo.TIEN_TO + "g2_00")
            self.assertEqual(cu, "kho_crm_demo")
            self.assertEqual(moi, dsn.replace("kho_crm_demo", demo.TIEN_TO + "g2_00"))


class DungDemoTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.chinh = demo.REPO
        self.cum = demo.cum_mac_dinh(self.chinh)
        self.tep = {}  # filesystem RAM; test không tạo/xóa tệp trên đĩa.
        self.conn = MagicMock()
        self.da_co_db = False
        self.so_tao = 0
        self.thong_tin_cum = None

        def execute(sql, params=None):
            result = MagicMock()
            if "current_setting('data_directory')" in sql:
                result.fetchone.return_value = self.thong_tin_cum or (
                    "kho_crm_demo", "127.0.0.1", 5432, str(self.cum.data_dir), "160015")
            elif "FROM pg_database" in sql:
                result.fetchone.return_value = (1,) if self.da_co_db else None
            elif sql.startswith("CREATE DATABASE"):
                self.so_tao += 1
                self.da_co_db = True
            else:
                self.fail("SQL ngoài phạm vi G2-00: " + sql)
            return result

        self.conn.execute.side_effect = execute
        self.driver = types.SimpleNamespace(connect=MagicMock(),
                                            errors=types.SimpleNamespace(DuplicateDatabase=type("TrungCSDL", (Exception,), {})))
        self.driver.connect.return_value.__enter__.return_value = self.conn
        self.stack.enter_context(patch.dict(sys.modules, {"psycopg": self.driver}))
        self.stack.enter_context(patch.object(demo, "tim_repo_chinh", return_value=self.chinh))
        # Mô phỏng đường dẫn vật lý, không đọc thư mục dữ liệu PG trên máy.
        self.resolve = self.stack.enter_context(patch.object(
            Path, "resolve", autospec=True, side_effect=lambda p, *, strict=False: p.absolute()))
        self.acl = self.stack.enter_context(patch.object(demo, "_dat_quyen_tep", return_value=True))
        self.doc = self.stack.enter_context(patch.object(demo, "nap_tep", side_effect=self._doc))
        self.stack.enter_context(patch.object(Path, "exists", lambda p: p in self.tep))
        self.stack.enter_context(patch.object(Path, "is_file", lambda p: p in self.tep))
        self.stack.enter_context(patch.object(Path, "is_dir", return_value=True))
        self.mkdir = self.stack.enter_context(patch.object(Path, "mkdir", autospec=True))
        self.stack.enter_context(patch.object(Path, "open", lambda path, mode, **kw: self._mo(path, mode, **kw)))

    def _doc(self, path):
        if path == self.chinh / "var" / "web" / "crm-demo" / demo.TEN_TEP:
            return dict(NGUON)
        return json.loads(self.tep[path])

    def _mo(self, path, mode, **kwargs):
        self.assertEqual(mode, "x")
        self.assertEqual(kwargs["encoding"], "utf-8")
        if path in self.tep:
            raise FileExistsError
        stream = io.StringIO()
        ctx = MagicMock()
        ctx.__enter__.return_value = stream
        ctx.__exit__.side_effect = lambda *args: self.tep.update({path: stream.getvalue()}) or False
        return ctx

    def test_tao_rong_va_chay_lai_khong_tao_de(self):
        mot = demo.tao_core_demo("g2_00")
        ban_dau = dict(self.tep)
        hai = demo.tao_core_demo("g2_00")
        self.assertEqual(mot["csdl_trang_thai"], "DA_TAO")
        self.assertEqual(hai["csdl_trang_thai"], "DA_CO")
        self.assertEqual(hai["cau_hinh_trang_thai"], "DA_CO")
        self.assertEqual(self.tep, ban_dau)
        self.assertEqual(self.so_tao, 1)
        root = demo.REPO / "var" / "core-demo" / "g2_00"
        for path in (root, root / "kho-tep", root / "bi-mat"):
            self.mkdir.assert_any_call(path, parents=True, exist_ok=True)
        cau_hinh = json.loads(self.tep[root / demo.TEN_TEP])
        self.assertEqual(self.acl.call_count, 2)
        self.acl.assert_called_with(root / demo.TEN_TEP)
        self.assertEqual(cau_hinh["admin_dsn"], DSN.replace("kho_crm_demo", mot["csdl"]))
        kw = self.driver.connect.call_args.kwargs
        self.assertEqual(kw["password"], CANARY)
        self.assertEqual(kw["dbname"], "kho_crm_demo")
        self.assertTrue(kw["autocommit"])

    def test_db_da_co_khong_chay_create(self):
        self.da_co_db = True
        self.assertEqual(demo.tao_core_demo("g2_00")["csdl_trang_thai"], "DA_CO")
        self.assertEqual(self.so_tao, 0)

    def test_hai_luot_tao_db_dong_thoi_khong_drop(self):
        execute = self.conn.execute.side_effect

        def trung_db(sql, params=None):
            if sql.startswith("CREATE DATABASE"):
                raise self.driver.errors.DuplicateDatabase(CANARY)
            return execute(sql, params)

        self.conn.execute.side_effect = trung_db
        self.assertEqual(demo.tao_core_demo("g2_00")["csdl_trang_thai"], "DA_CO")

    def test_tep_xuat_hien_dong_thoi_khong_ghi_de(self):
        root = demo.REPO / "var" / "core-demo" / "g2_00"
        noi_dung = {k: v.replace("kho_crm_demo", demo.TIEN_TO + "g2_00") if isinstance(v, str) else v
                    for k, v in NGUON.items()}

        def da_tao(path, mode, **kw):
            self.tep[path] = json.dumps(noi_dung)
            raise FileExistsError

        with patch.object(Path, "open", da_tao):
            self.assertEqual(demo.tao_core_demo("g2_00")["cau_hinh_trang_thai"], "DA_CO")
        self.assertEqual(json.loads(self.tep[root / demo.TEN_TEP]), noi_dung)

    def test_cum_that_hoac_sai_cum_khong_create(self):
        for data_dir, host, port in ((r"D:\DU-LIEU-KE-TOAN\postgresql", "127.0.0.1", 5432),
                                     (r"C:\pg-that\data", "127.0.0.1", 5432),
                                     (str(self.cum.data_dir), "10.0.0.1", 5432),
                                     (str(self.cum.data_dir), "127.0.0.1", 5433)):
            self.thong_tin_cum = ("kho_crm_demo", host, port, data_dir, "160015")
            with self.subTest(data_dir=data_dir, host=host, port=port), self.assertRaises(demo.TuChoi):
                demo.tao_core_demo("g2_00")
        self.assertTrue(callable(self.conn.execute.side_effect))
        self.assertEqual(self.conn.execute.call_count, 4)
        self.assertTrue(all("current_setting('data_directory')" in c.args[0]
                            for c in self.conn.execute.call_args_list))
        self.assertEqual(self.so_tao, 0)
        self.mkdir.assert_not_called()
        self.assertEqual(self.tep, {})

    def test_junction_cum_data_dir_vao_vung_cam_khong_connect(self):
        for dich in (Path("D:/DU-LIEU-KE-TOAN/postgresql"),
                     self.chinh / "var" / "web-that" / "postgresql",
                     self.chinh / "var" / "plhn-that" / "postgresql"):
            def resolve(path, *, strict=False):
                return dich if path == self.cum.data_dir else path.absolute()

            self.resolve.side_effect = resolve
            with self.subTest(dich=dich), self.assertRaises(demo.TuChoi):
                demo.tao_core_demo("g2_00")
        self.resolve.assert_any_call(self.cum.data_dir, strict=True)
        self.driver.connect.assert_not_called()
        self.conn.execute.assert_not_called()
        self.mkdir.assert_not_called()
        self.acl.assert_not_called()
        self.assertEqual(self.tep, {})

    def test_junction_data_directory_server_khong_create(self):
        alias = self.chinh / "var" / "pg-alias-demo"
        self.thong_tin_cum = ("kho_crm_demo", "127.0.0.1", 5432, str(alias), "160015")
        self.resolve.side_effect = lambda p, *, strict=False: (
            Path("D:/DU-LIEU-KE-TOAN/postgresql") if p == alias else p.absolute())
        with self.assertRaises(demo.TuChoi):
            demo.tao_core_demo("g2_00")
        self.resolve.assert_any_call(alias, strict=True)
        self.assertEqual(self.conn.execute.call_count, 1)
        self.assertIn("current_setting('data_directory')", self.conn.execute.call_args.args[0])
        self.assertEqual(self.so_tao, 0)
        self.mkdir.assert_not_called()
        self.assertEqual(self.tep, {})

    def test_khong_resolve_duoc_cum_khong_connect(self):
        def resolve(path, *, strict=False):
            if path == self.cum.data_dir:
                self.assertTrue(strict)
                raise FileNotFoundError(CANARY)
            return path.absolute()

        self.resolve.side_effect = resolve
        with self.assertRaises(demo.TuChoi) as caught:
            demo.tao_core_demo("g2_00")
        self.assertNotIn(CANARY, str(caught.exception))
        self.driver.connect.assert_not_called()
        self.conn.execute.assert_not_called()

    def test_thu_acl_truoc_ghi_dsn_va_khong_can_quyen_quan_tri(self):
        root = demo.REPO / "var" / "core-demo" / "g2_00"
        ghi_json = json.dump

        def ghi(noi_dung, stream, **kwargs):
            self.acl.assert_called_once_with(root / demo.TEN_TEP)
            self.assertEqual(stream.getvalue(), "")
            return ghi_json(noi_dung, stream, **kwargs)

        self.acl.return_value = False  # Môi trường không cho đặt ACL: vẫn tạo cấu hình DEMO.
        with patch.object(demo.json, "dump", side_effect=ghi):
            self.assertEqual(demo.tao_core_demo("g2_00")["cau_hinh_trang_thai"], "DA_TAO")
        self.assertEqual(json.loads(self.tep[root / demo.TEN_TEP])["phien_ban"], 1)

    def test_cau_hinh_khac_khong_ghi_de_khong_connect(self):
        root = demo.REPO / "var" / "core-demo" / "g2_00"
        self.tep[root / demo.TEN_TEP] = json.dumps(NGUON)
        with self.assertRaises(demo.TuChoi):
            demo.tao_core_demo("g2_00")
        self.driver.connect.assert_not_called()
        self.assertEqual(json.loads(self.tep[root / demo.TEN_TEP]), NGUON)

    def test_nguon_sai_moi_truong_khong_connect(self):
        self.doc.side_effect = None
        self.doc.return_value = {**NGUON, "admin_dsn": DSN.replace("kho_crm_demo", "kho_that")}
        with self.assertRaises(demo.TuChoi):
            demo.tao_core_demo("g2_00")
        self.driver.connect.assert_not_called()

    def test_loi_giua_chung_chay_lai_phuc_hoi_khong_drop(self):
        self.mkdir.side_effect = OSError(CANARY)
        with self.assertRaises(demo.TuChoi) as caught:
            demo.tao_core_demo("g2_00")
        self.assertNotIn(CANARY, str(caught.exception))
        self.mkdir.side_effect = None
        self.assertEqual(demo.tao_core_demo("g2_00")["csdl_trang_thai"], "DA_CO")
        self.assertEqual(self.so_tao, 1)

    def test_loi_create_khong_sinh_cau_hinh(self):
        execute = self.conn.execute.side_effect

        def loi_create(sql, params=None):
            if sql.startswith("CREATE DATABASE"):
                raise RuntimeError(DSN)
            return execute(sql, params)

        self.conn.execute.side_effect = loi_create
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(demo.main(["--ma", "g2_00"]), 1)
        self.assertNotIn(CANARY, stdout.getvalue() + stderr.getvalue())
        self.assertEqual(self.tep, {})
        self.mkdir.assert_not_called()

    def test_khong_in_credential_ca_thanh_cong_loi_driver_va_cli(self):
        for loi in (None, RuntimeError(DSN), KeyboardInterrupt(DSN)):
            self.driver.connect.side_effect = loi
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = demo.main(["--ma", "g2_00"])
            out = stdout.getvalue() + stderr.getvalue()
            self.assertNotIn(CANARY, out)
            self.assertNotIn(DSN, out)
            self.assertEqual(rc, 1 if loi else 0)
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(demo.main(["--ma", "g2_00", "--in", CANARY]), 1)
        self.assertNotIn(CANARY, stdout.getvalue() + stderr.getvalue())


class QuyenTepTests(unittest.TestCase):
    def test_acl_windows_chi_sid_hien_tai_khong_ke_thua_khong_in_dsn(self):
        tep = Path("var/core-demo/g2_00/ket-noi.local.json")
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(demo.sys, "platform", "win32"), \
                patch.dict(demo.os.environ, {"SystemRoot": "C:/Windows"}), \
                patch.object(demo.subprocess, "run") as chay, \
                redirect_stdout(stdout), redirect_stderr(stderr):
            chay.return_value.returncode = 0
            chay.return_value.stdout = chay.return_value.stderr = DSN
            self.assertTrue(demo._dat_quyen_tep(tep))
        args, kwargs = chay.call_args
        self.assertEqual(args[0][0], str(Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")))
        lenh = args[0][-1]
        self.assertIn("WindowsIdentity]::GetCurrent().User", lenh)
        self.assertIn("New-Object System.Security.AccessControl.FileSecurity", lenh)
        self.assertIn("SetAccessRuleProtection($true, $false)", lenh)
        self.assertIn("FileSystemAccessRule($sid, 'FullControl', 'Allow')", lenh)
        self.assertIn("Set-Acl -LiteralPath $p -AclObject $acl", lenh)
        self.assertEqual(kwargs["input"], str(tep))
        self.assertTrue(kwargs["capture_output"])
        self.assertEqual(kwargs["creationflags"], 0x08000000)
        self.assertNotIn(DSN, str(chay.call_args))
        self.assertEqual(stdout.getvalue() + stderr.getvalue(), "")

    def test_acl_khong_ho_tro_hoac_loi_khong_lo_credential(self):
        for loi in (None, OSError(DSN), demo.subprocess.TimeoutExpired("powershell.exe", 15, output=DSN)):
            stdout, stderr = io.StringIO(), io.StringIO()
            with self.subTest(loai=type(loi).__name__), \
                    patch.object(demo.sys, "platform", "win32"), \
                    patch.dict(demo.os.environ, {"SystemRoot": "C:/Windows"}), \
                    patch.object(demo.subprocess, "run", side_effect=loi) as chay, \
                    redirect_stdout(stdout), redirect_stderr(stderr):
                chay.return_value.returncode = 1
                chay.return_value.stdout = chay.return_value.stderr = DSN
                self.assertFalse(demo._dat_quyen_tep(Path("ket-noi.local.json")))
            self.assertEqual(stdout.getvalue() + stderr.getvalue(), "")

    def test_quyen_tep_posix(self):
        tep = Path("ket-noi.local.json")
        with patch.object(demo.sys, "platform", "linux"), \
                patch.object(Path, "chmod", autospec=True) as chmod, \
                patch.object(demo.subprocess, "run") as chay:
            self.assertTrue(demo._dat_quyen_tep(tep))
            chmod.assert_called_once_with(tep, 0o600)
            chay.assert_not_called()


if __name__ == "__main__":
    unittest.main()
