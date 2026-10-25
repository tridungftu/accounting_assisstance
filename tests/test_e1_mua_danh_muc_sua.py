"""E1-4a: CLI và giao dịch sửa danh mục DEMO; offline, giữ thư mục tạm."""
import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
VA = ROOT / "tools/source6_g5_e5/trich_xuat"
GOC = ROOT / "src/kho_tri_thuc/m4/review_goc/trich_xuat"
TEN = "_e1_sua_demo"
PKG = types.ModuleType(TEN)
PKG.__path__ = [str(VA)]
CONFIG = types.ModuleType(TEN + ".cau_hinh")
CONFIG.DANH_MUC_THAM_SO = VA / "DANH_MUC_THAM_SO.xlsx"
MODS = {TEN: PKG, CONFIG.__name__: CONFIG}
with patch.dict(sys.modules, MODS):
    for name, path in (("xlsx_mini", GOC / "xlsx_mini.py"),
                       ("danh_muc", VA / "danh_muc.py"), ("__main__", VA / "__main__.py")):
        spec = importlib.util.spec_from_file_location(TEN + "." + name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        MODS[spec.name] = mod
        spec.loader.exec_module(mod)
D = MODS[TEN + ".danh_muc"]
CLI = MODS[TEN + ".__main__"]


class E1SuaDanhMucTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="e1_sua_DEMO_"))
        self.path = self.tmp / "DANH_MUC_THAM_SO_DV.xlsx"
        row = dict(ma="DEMO-01", nhom="DEMO", mo_ta="Mô tả DEMO", tk="demo", bk="",
                   dung=True, muc=2, bat_buoc="", loai_tru="", luon_cloud=False)
        D._ghi(self.path, [row])
        self.raw = self.path.read_bytes()
        self.sha = hashlib.sha256(self.raw).hexdigest()
        self.reg = {"DV": dict(catalog_id="DV", path=self.path, sha256=self.sha)}
        self.registry = patch.dict(D.CATALOG_COMMON, self.reg)
        self.registry.start()
        self.addCleanup(self.registry.stop)
        self.journal = D.duong_dan_nhat_ky(self.path)

    def call(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = CLI.main(list(args))
        return rc, out.getvalue(), err.getvalue()

    def edit(self, loai="DV", ma="DEMO-01", field="mo_ta", value="Mô tả DEMO mới"):
        return self.call("danh-muc", "sua", loai, ma, "--truong", field,
                         "--gia-tri", value, "--nguoi", "Kế toán DEMO", "--ly-do", "Rà soát DEMO")

    def test_xem_bang_tieng_viet_khong_ghi(self):
        self.assertEqual(self.call("danh-muc", "xem", "DV")[0], 0)
        text = self.call("danh-muc", "xem", "DV")[1]
        self.assertIn("Mã | Nhóm | Mô tả cho AI", text)
        self.assertIn("DEMO-01", text)
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.assertFalse(self.journal.exists())

    def test_sua_hop_le_phien_ban_nhat_ky_sao_luu(self):
        rc, out, err = self.edit()
        self.assertEqual((rc, err), (0, ""))
        new_sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.assertNotEqual(new_sha, self.sha)
        self.assertIn(new_sha, out)
        self.assertEqual(D.read_catalog(self.path)[0]["mo_ta"], "Mô tả DEMO mới")
        lines = self.journal.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        event = json.loads(lines[0])
        self.assertIsNotNone(datetime.datetime.fromisoformat(event.pop("thoi_diem")).tzinfo)
        self.assertEqual(event, dict(nguoi="Kế toán DEMO", ly_do="Rà soát DEMO", loai="DV",
                                    ma="DEMO-01", truong="mo_ta", gia_tri_cu="Mô tả DEMO",
                                    gia_tri_moi="Mô tả DEMO mới", phien_ban_cu=self.sha,
                                    phien_ban_moi=new_sha))
        backups = list((self.tmp / "danh_muc_sao_luu").glob("*.xlsx"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), self.raw)
        self.assertFalse(self.journal.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertEqual(D.danh_muc_theo_loai("DV"), self.path)
        self.assertEqual(list(self.tmp.glob("*.tmp")), [])

    def test_hai_lan_sua_va_nap_lai_tien_trinh(self):
        self.assertEqual(self.edit()[0], 0)
        self.assertEqual(self.edit(field="muc", value="3")[0], 0)
        events = [json.loads(x) for x in self.journal.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["phien_ban_moi"], events[1]["phien_ban_cu"])
        self.assertEqual(list(self.tmp.glob("*.tmp")), [])
        # Registry vẫn ghim SHA gốc; subprocess mới chỉ dùng dependency thuần của repo.
        code = """
import importlib.machinery, runpy, sys, types
from pathlib import Path
pkg = types.ModuleType('trich_xuat')
pkg.__path__ = sys.argv[1:3]
pkg.__spec__ = importlib.machinery.ModuleSpec('trich_xuat', loader=None, is_package=True)
sys.modules['trich_xuat'] = pkg
cfg = types.ModuleType('trich_xuat.cau_hinh')
cfg.DANH_MUC_THAM_SO = Path(sys.argv[3])
sys.modules[cfg.__name__] = cfg
from trich_xuat import danh_muc as d
d.CATALOG_COMMON['DV'] = dict(catalog_id='DV', path=Path(sys.argv[3]), sha256=sys.argv[4])
sys.argv = ['trich_xuat', 'danh-muc', 'xem', 'DV']
runpy.run_module('trich_xuat', run_name='__main__')
"""
        result = subprocess.run([sys.executable, "-X", "utf8", "-c", code, str(VA), str(GOC),
                                 str(self.path), self.sha], capture_output=True, text=True,
                                encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Mô tả DEMO mới", result.stdout)

    def test_loai_ma_truong_la_xd_khong_ghi_gi(self):
        for kwargs, message in ((dict(loai="LA"), "chưa đăng ký"),
                                (dict(ma="LA"), "Mã tham số"),
                                (dict(field="LA"), "không được sửa"),
                                (dict(field="ma"), "không được sửa"),
                                (dict(loai="XD"), "XD không được sửa")):
            with self.subTest(kwargs=kwargs):
                before = sorted(p.name for p in self.tmp.iterdir())
                rc, _, err = self.edit(**kwargs)
                self.assertNotEqual(rc, 0)
                self.assertIn(message, err)
                self.assertEqual(self.path.read_bytes(), self.raw)
                self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), before)

    def test_luu_thanh_cong_chi_don_tep_tam_cua_lan_luu(self):
        other = self.tmp / (self.path.name + ".giu_lai.tmp")
        other.write_bytes(b"DEMO chan doan cu")
        for journal in (False, True):
            with self.subTest(journal=journal):
                if journal:
                    self.assertEqual(self.edit()[0], 0)
                else:
                    D.save_catalog(D.read_catalog(self.path), self.path)
                    self.reg["DV"]["sha256"] = hashlib.sha256(self.path.read_bytes()).hexdigest()
                self.assertEqual(list(self.tmp.glob("*.tmp")), [other])
                self.assertEqual(other.read_bytes(), b"DEMO chan doan cu")

    def test_gia_tri_khong_hop_le_khong_ghi(self):
        for field, value in (("muc", "4"), ("muc", "hai"), ("dung", "sai"),
                             ("luon_cloud", "sai"), ("mo_ta", ""), ("mo_ta", "Mô tả DEMO")):
            with self.subTest(field=field, value=value):
                self.assertNotEqual(self.edit(field=field, value=value)[0], 0)
                self.assertEqual(self.path.read_bytes(), self.raw)
                self.assertFalse(self.journal.exists())

    def test_boolean_giu_dung_kieu(self):
        self.assertEqual(self.edit(field="dung", value="Không")[0], 0)
        self.assertIs(D.read_catalog(self.path)[0]["dung"], False)
        self.assertIs(json.loads(self.journal.read_text(encoding="utf-8"))["gia_tri_moi"], False)

    def test_ghi_xlsx_do_dang_khong_mat_ban_cu(self):
        def fail(path, rows):
            Path(path).write_bytes(b"DEMO incomplete")
            raise OSError("Lỗi ghi DEMO")
        with patch.object(D, "_ghi", side_effect=fail):
            self.assertNotEqual(self.edit()[0], 0)
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.assertFalse(self.journal.exists())
        self.assertTrue(list(self.tmp.glob("*.tmp")))

    def test_loi_doi_ten_catalog_hoac_nhat_ky_rollback(self):
        real = os.replace
        for destination in (self.path, self.journal):
            with self.subTest(destination=destination):
                def fail(src, dst):
                    if Path(dst) == destination:
                        raise OSError("Lỗi đổi tên DEMO")
                    return real(src, dst)
                with patch.object(D.os, "replace", side_effect=fail):
                    self.assertNotEqual(self.edit()[0], 0)
                self.assertEqual(self.path.read_bytes(), self.raw)
                self.assertFalse(self.journal.exists())

    def test_loi_nhat_ky_giu_ca_lich_su_cu(self):
        self.assertEqual(self.edit()[0], 0)
        old, log = self.path.read_bytes(), self.journal.read_bytes()
        real = os.replace
        def fail(src, dst):
            if Path(dst) == self.journal:
                raise OSError("Lỗi nhật ký DEMO")
            return real(src, dst)
        with patch.object(D.os, "replace", side_effect=fail):
            self.assertNotEqual(self.edit(field="muc", value="3")[0], 0)
        self.assertEqual(self.path.read_bytes(), old)
        self.assertEqual(self.journal.read_bytes(), log)
        self.assertEqual(D.danh_muc_theo_loai("DV"), self.path)

    def test_khong_nhan_file_sua_ngoai_nhat_ky(self):
        self.assertEqual(self.edit()[0], 0)
        self.path.write_bytes(self.raw)
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            D.danh_muc_theo_loai("DV")


if __name__ == "__main__":
    unittest.main()
