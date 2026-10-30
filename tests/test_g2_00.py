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

        def execute(sql, params=None):
            result = MagicMock()
            if "current_setting('data_directory')" in sql:
                result.fetchone.return_value = ("kho_crm_demo", "127.0.0.1", 5432, str(self.cum.data_dir), "160015")
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
            self.conn.execute.side_effect = None
            self.conn.execute.return_value.fetchone.return_value = ("kho_crm_demo", host, port, data_dir, "160015")
            with self.subTest(data_dir=data_dir, host=host, port=port), self.assertRaises(demo.TuChoi):
                demo.tao_core_demo("g2_00")
        self.assertEqual(self.so_tao, 0)
        self.mkdir.assert_not_called()
        self.assertEqual(self.tep, {})

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


if __name__ == "__main__":
    unittest.main()
