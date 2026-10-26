"""SL-1: chỉ Python script giả, mỗi ca một mkdtemp, không cleanup/xóa.

Chạy: python -B -m unittest discover -s tests -p test_sao_luu_ma_hoa.py -v
Không dùng PATH pg_dump/gpg, PostgreSQL, dữ liệu thật hoặc thư mục vận hành.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import sao_luu_ma_hoa as sl


FP = "1234567890ABCDEF1234567890ABCDEF12345678"
PAYLOAD = bytes(range(256)) * 4096
SCRIPT = r'''
import json, os, sys, time
from pathlib import Path
kind, mode, trace, *args = sys.argv[1:]
with open(trace, "a", encoding="utf-8") as f:
    f.write(json.dumps({"kind": kind, "args": args,
        "pg": {k:v for k,v in os.environ.items() if k.startswith("PG")},
        "leaked_dsn": "KHO_PG_DSN" in os.environ}) + "\n")
if "--version" in args:
    print("pg_dump (PostgreSQL) 16.15" if kind == "dump" else "gpg (GnuPG) 2.4.9")
    sys.exit(0)
if "--list-keys" in args:
    fp = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" if mode == "badkey" else "1234567890ABCDEF1234567890ABCDEF12345678"
    validity = "r" if mode == "revoked" else "u"
    print("pub:" + validity + ":2048:1:ABC:0:0:::::e:")
    print("fpr:::::::::" + fp + ":")
    sys.exit(0)
sys.stderr.write("postgresql://CANARY_PASSWORD@local/db SECRET_KEY_PATH\n")
if kind == "dump":
    if mode == "hang":
        time.sleep(20)
        sys.exit(0)
    data = bytes(range(256)) * 4096
    try:
        sys.stdout.buffer.write(data[:16384] if mode == "fail" else data)
        sys.stdout.buffer.flush()
    except BrokenPipeError:
        os._exit(9)
    sys.exit(7 if mode == "fail" else 0)
if mode == "early":
    sys.exit(8)
if mode == "earlyok":
    sys.exit(0)
sys.stdout.buffer.write(b"FAKE_ENCRYPTED\x00")
while True:
    block = sys.stdin.buffer.read(4096)
    if not block:
        break
    sys.stdout.buffer.write(bytes(b ^ 0xA5 for b in block))
    if mode == "fail":
        sys.stdout.buffer.flush()
        sys.exit(8)
sys.exit(0)
'''


class SaoLuuMaHoaTests(unittest.TestCase):
    def setUp(self):
        # Chủ ý giữ thư mục tạm sau test theo lệnh không xóa của handoff.
        self.tmp = Path(tempfile.mkdtemp(prefix="sl1-fake-"))
        # Tách thư mục cấm giả để TEMP trong repo vẫn kiểm được nghiệp vụ.
        self.goc_cam = (Path(tempfile.mkdtemp(prefix="sl1-repo-gia-")),)
        self.script = self.tmp / "fake.py"
        self.script.write_text(SCRIPT, encoding="utf-8")
        self.home = self.tmp / "public-keyring-gia"
        self.home.mkdir()
        self.config = self.tmp / "ket-noi.local.json"
        self.dsn = "host=localhost port=5433 user=fake password='CANARY_PASSWORD' dbname=kho_test_sl1 sslmode=require"
        self.config.write_text(json.dumps({"phien_ban": 1, "app_dsn": self.dsn,
                                          "admin_dsn": self.dsn}), encoding="utf-8")
        self.trace = self.tmp / "argv.jsonl"
        self.root = self.tmp / "backup"
        self.journal = self.tmp / "bien-ban-dot.jsonl"
        self.when = datetime(2026, 10, 26, 23, 0, 0)

    def command(self, kind, mode):
        return [sys.executable, str(self.script), kind, mode, str(self.trace)]

    def backup(self, dump="ok", gpg="ok", **kwargs):
        args = dict(pg_dump=self.command("dump", dump), gpg=self.command("gpg", gpg),
                    homedir=self.home, fingerprint=FP, ket_noi=self.config,
                    goc=self.root, bien_ban=self.journal, min_free_bytes=1,
                    timeout=5, thoi_diem=self.when, goc_cam=self.goc_cam)
        args.update(kwargs)
        return sl.sao_luu(**args)

    @property
    def folder(self):
        return self.root / "20261026-230000"

    def assert_failure(self, code, **kwargs):
        with self.assertRaises(sl.LoiSaoLuu) as ctx:
            self.backup(**kwargs)
        self.assertEqual(ctx.exception.ma, code)
        self.assertNotIn("CANARY_PASSWORD", str(ctx.exception))
        self.assertFalse((self.folder / "postgresql.gpg").exists())
        self.assertTrue((self.folder / "postgresql.partial.gpg").is_file())
        self.assertFalse(self.journal.exists())

    def test_thanh_cong_binary_sha_bien_ban_khong_dump_ro(self):
        row = self.backup()
        ciphertext = b"FAKE_ENCRYPTED\x00" + bytes(b ^ 0xA5 for b in PAYLOAD)
        final = self.folder / "postgresql.gpg"
        self.assertEqual(final.read_bytes(), ciphertext)
        self.assertEqual(row["sha256"], hashlib.sha256(ciphertext).hexdigest())
        self.assertEqual(row["sha256"], hashlib.sha256(final.read_bytes()).hexdigest())
        self.assertEqual(row["dung_luong"], len(ciphertext))
        self.assertEqual(row["phien_ban"], {"pg_dump": "16.15", "gpg": "2.4.9"})
        self.assertEqual(set(row["giay"]), {"kiem_tra", "pg_dump", "gpg", "sha256"})
        self.assertEqual(json.loads(self.journal.read_text(encoding="utf-8")), row)
        self.assertEqual([p.name for p in self.folder.iterdir()], ["postgresql.gpg"])
        self.assertNotIn(PAYLOAD[:4096], final.read_bytes())
        self.assertEqual(set(p.name for p in self.tmp.rglob("*") if p.is_file()),
                         {"fake.py", "ket-noi.local.json", "argv.jsonl", "bien-ban-dot.jsonl", "postgresql.gpg"})

    def test_pg_dump_loi_giua_chung_giu_partial(self):
        self.assert_failure("SL_PG_DUMP", dump="fail")

    def test_gpg_loi_giu_partial(self):
        self.assert_failure("SL_GPG", gpg="fail")

    def test_gpg_thoat_som_khong_treo(self):
        self.assert_failure("SL_GPG", gpg="early")

    def test_gpg_thoat_zero_som_van_kiem_dump(self):
        self.assert_failure("SL_PG_DUMP", gpg="earlyok")

    def test_timeout_dung_hai_tien_trinh_giu_partial(self):
        self.assert_failure("SL_TIMEOUT", dump="hang", timeout=1)

    def test_gpg_khong_khoi_dong_ket_thuc_dump_giu_partial(self):
        original = sl.subprocess.Popen
        processes = []
        def start(*args, **kwargs):
            command = args[0]
            if "--encrypt" in command:
                raise OSError("CANARY_PASSWORD SECRET_KEY_PATH")
            process = original(*args, **kwargs)
            if "--format=custom" in command:
                processes.append(process)
            return process
        with patch.object(sl.subprocess, "Popen", side_effect=start):
            self.assert_failure("SL_GPG")
        self.assertTrue(processes)
        self.assertTrue(all(p.poll() is not None for p in processes))

    def test_bien_ban_loi_tra_ve_partial(self):
        missing = self.tmp / "chua-co-thu-muc" / "bien-ban.jsonl"
        self.assert_failure("SL_BIEN_BAN", bien_ban=missing)

    def test_bien_ban_mac_dinh_rieng_o_goc_va_sha_sau_ghi(self):
        original = sl.sha256
        reads = []
        journal = self.root / "bien-ban-sao-luu.jsonl"
        def read_hash(path):
            reads.append((path, journal.exists()))
            return original(path)
        with patch.object(sl, "sha256", side_effect=read_hash):
            row = self.backup(bien_ban=None)
        final = self.folder / "postgresql.gpg"
        self.assertEqual(reads, [(self.folder / "postgresql.partial.gpg", False),
                                 (final, True)])
        self.assertEqual(json.loads(journal.read_text(encoding="utf-8")), row)
        self.assertEqual(row["sha256"], hashlib.sha256(final.read_bytes()).hexdigest())
        self.assertEqual(row["dung_luong"], final.stat().st_size)
        self.assertEqual([p.name for p in self.folder.iterdir()], ["postgresql.gpg"])

    def test_bien_ban_trong_moi_thu_muc_lan_chan_truoc_dump(self):
        paths = [self.folder, self.folder / "bien-ban.jsonl",
                 self.folder / "con" / "bien-ban.jsonl",
                 self.folder / "postgresql.gpg",
                 self.folder / "postgresql.partial.gpg",
                 self.root / "20251026-230000" / "bien-ban.jsonl",
                 self.root / "20271026-230000" / "bien-ban.jsonl",
                 self.root / "con" / ".." / self.folder.name / "bien-ban.jsonl"]
        with patch.object(sl.subprocess, "run") as run, patch.object(sl, "_ong_dan") as pipe:
            for path in paths:
                with self.subTest(path=str(path)), self.assertRaises(sl.LoiSaoLuu) as ctx:
                    self.backup(bien_ban=path)
                self.assertEqual(ctx.exception.ma, "SL_BIEN_BAN_SAI")
            run.assert_not_called()
            pipe.assert_not_called()
        self.assertFalse(self.root.exists())
        self.assertFalse(self.trace.exists())

    def test_bien_ban_duoi_gpg_va_thu_muc_cam_chan_truoc_dump(self):
        paths = [self.root / "bien-ban.gpg", self.root / "bien-ban.partial.gpg",
                 self.tmp / "bien-ban.GPG", self.tmp / "bien-ban.PARTIAL.GPG",
                 self.goc_cam[0] / "bien-ban.jsonl", self.goc_cam[0], self.home]
        with patch.object(sl.subprocess, "run") as run, patch.object(sl, "_ong_dan") as pipe:
            for path in paths:
                with self.subTest(path=str(path)), self.assertRaises(sl.LoiSaoLuu) as ctx:
                    self.backup(bien_ban=path)
                self.assertEqual(ctx.exception.ma, "SL_BIEN_BAN_SAI")
            run.assert_not_called()
            pipe.assert_not_called()
        self.assertFalse(self.root.exists())
        self.assertFalse(self.trace.exists())

    def test_bien_ban_cam_repo_that_voi_goc_cam_mac_dinh(self):
        # Chỉ gọi helper kiểm đường, không tạo/đọc biên bản trong repo thật.
        for root in sl._goc_cam():
            with self.subTest(root=str(root)), self.assertRaises(sl.LoiSaoLuu) as ctx:
                sl._kiem_bien_ban(root / "bien-ban.jsonl", self.root.resolve(),
                                  self.folder / "postgresql.partial.gpg",
                                  self.folder / "postgresql.gpg", None)
            self.assertEqual(ctx.exception.ma, "SL_BIEN_BAN_SAI")

    def test_ban_ma_doi_sau_ghi_bien_ban_khong_tra_thanh_cong(self):
        original = sl.os.fsync
        final = self.folder / "postgresql.gpg"
        def sync_and_corrupt(fd):
            original(fd)
            if self.journal.exists():
                with final.open("ab") as f:
                    f.write(b"HONG_SAU_GHI_BIEN_BAN")
        with patch.object(sl.os, "fsync", side_effect=sync_and_corrupt):
            with self.assertRaises(sl.LoiSaoLuu) as ctx:
                self.backup()
        self.assertEqual(ctx.exception.ma, "SL_SHA_SAU_BIEN_BAN")
        row = json.loads(self.journal.read_text(encoding="utf-8"))
        self.assertNotEqual(row["sha256"], hashlib.sha256(final.read_bytes()).hexdigest())

    def test_cli_bien_ban_khong_bat_buoc(self):
        args = ["sao-luu", "--pg-dump", "fake-dump", "--gpg", "fake-gpg",
                "--homedir", str(self.home), "--fingerprint", FP,
                "--ket-noi", str(self.config), "--goc", str(self.root),
                "--min-free-bytes", "1"]
        with patch.object(sl, "sao_luu", return_value={}) as backup:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(sl.main(args), 0)
        self.assertIsNone(backup.call_args.kwargs["bien_ban"])

    def test_argv_khong_bi_mat_va_gpg_khong_nhan_pg_env(self):
        with patch.dict(sl.os.environ, {"KHO_PG_DSN": self.dsn,
                                      "PGDATABASE": "sai_dich", "PGPASSWORD": "MAT_KHAU_CU"}):
            self.backup()
        calls = [json.loads(line) for line in self.trace.read_text(encoding="utf-8").splitlines()]
        for call in calls:
            argv = json.dumps(call["args"])
            self.assertNotIn("CANARY_PASSWORD", argv)
            self.assertNotIn(self.dsn, argv)
            self.assertNotIn("postgresql://", argv)
            self.assertFalse(call["leaked_dsn"])
            if call["kind"] == "gpg" or "--version" in call["args"]:
                self.assertEqual(call["pg"], {})
        dump = next(c for c in calls if "--format=custom" in c["args"])
        self.assertEqual(dump["args"], ["--format=custom", "--no-password"])
        self.assertEqual(dump["pg"]["PGPASSWORD"], "CANARY_PASSWORD")
        self.assertEqual(dump["pg"]["PGDATABASE"], "kho_test_sl1")
        gpg = next(c for c in calls if "--encrypt" in c["args"])
        for flag in ("--batch", "--homedir", "--no-options", "--trust-model", "AES256", FP):
            self.assertIn(flag, gpg["args"])

    def test_doc_ket_noi_uri_va_escape_qua_helper(self):
        dsn = "postgresql://fake:p%40ss@localhost:5433/kho_test_sl1?sslmode=require"
        self.config.write_text(json.dumps({"phien_ban": 1, "app_dsn": dsn, "admin_dsn": dsn}), encoding="utf-8")
        env = sl.moi_truong_ket_noi(self.config)
        self.assertEqual(env["PGPASSWORD"], "p@ss")
        self.assertEqual(env["PGSSLMODE"], "require")
        self.assertEqual(env["PGPORT"], "5433")

    def test_tu_choi_khoa_khong_ho_tro_khong_echo_dsn(self):
        with patch.object(sl, "nap_tep", return_value={"admin_dsn": self.dsn + " khong_ho_tro=CANARY_PASSWORD"}):
            with self.assertRaises(sl.LoiSaoLuu) as ctx:
                sl.moi_truong_ket_noi(self.config)
        self.assertEqual(str(ctx.exception), "SL_KET_NOI")

    def test_sai_fingerprint_va_khoa_thu_hoi(self):
        for mode in ("badkey", "revoked"):
            with self.subTest(mode=mode), self.assertRaises(sl.LoiSaoLuu) as ctx:
                self.backup(gpg=mode)
            self.assertEqual(ctx.exception.ma, "SL_FINGERPRINT")
            self.assertFalse(self.root.exists())

    def test_thieu_chuong_trinh(self):
        with self.assertRaises(sl.LoiSaoLuu) as ctx:
            self.backup(pg_dump=self.tmp / "khong_co.exe")
        self.assertEqual(ctx.exception.ma, "SL_THIEU_CHUONG_TRINH")
        self.assertFalse(self.root.exists())

    def test_khong_du_dung_luong(self):
        with patch.object(sl.shutil, "disk_usage", return_value=shutil._ntuple_diskusage(100, 100, 0)):
            with self.assertRaises(sl.LoiSaoLuu) as ctx:
                self.backup()
        self.assertEqual(ctx.exception.ma, "SL_THIEU_DUNG_LUONG")
        self.assertFalse(self.root.exists())

    def test_dich_trong_repo_tu_choi_truoc_goi_tien_trinh(self):
        with patch.object(sl.subprocess, "run", side_effect=AssertionError("Không được chạy")):
            for root in sl._goc_cam():
                with self.subTest(root=str(root)), self.assertRaises(sl.LoiSaoLuu) as ctx:
                    sl.sao_luu(pg_dump=self.command("dump", "ok"),
                               gpg=self.command("gpg", "ok"), homedir=self.home,
                               fingerprint=FP, ket_noi=self.config,
                               goc=root / "backup-gia", bien_ban=self.journal,
                               min_free_bytes=1)
                self.assertEqual(ctx.exception.ma, "SL_DICH_TRONG_REPO")
                with self.subTest(chep=str(root)), self.assertRaises(sl.LoiSaoLuu) as ctx:
                    sl.chep_ban_ma(self.tmp / "nguon.gpg", root / "copy.gpg", "0" * 64)
                self.assertEqual(ctx.exception.ma, "SL_DICH_TRONG_REPO")
        self.assertFalse(self.trace.exists())

    def test_goc_cam_tiem_chan_dich_va_homedir(self):
        forbidden = self.goc_cam[0]
        with patch.object(sl.subprocess, "run", side_effect=AssertionError("Không được chạy")):
            for path in (forbidden, forbidden / "con"):
                for field in ("goc", "homedir"):
                    with self.subTest(path=str(path), field=field), self.assertRaises(sl.LoiSaoLuu) as ctx:
                        self.backup(**{field: path})
                    self.assertEqual(ctx.exception.ma, "SL_DICH_TRONG_REPO")
        self.assertFalse(self.trace.exists())
        self.assertFalse(self.root.exists())

    def test_chep_goc_cam_tiem_chan_dich(self):
        target = self.goc_cam[0] / "con" / "copy.gpg"
        with patch.object(sl, "sha256", side_effect=AssertionError("Không được đọc nguồn")):
            with self.assertRaises(sl.LoiSaoLuu) as ctx:
                sl.chep_ban_ma(self.tmp / "nguon.gpg", target, "0" * 64,
                              goc_cam=self.goc_cam)
        self.assertEqual(ctx.exception.ma, "SL_DICH_TRONG_REPO")
        self.assertFalse(target.parent.exists())

    def test_trung_ma_lan_khong_ghi_de(self):
        first = self.backup()
        with self.assertRaises(sl.LoiSaoLuu) as ctx:
            self.backup()
        self.assertEqual(ctx.exception.ma, "SL_DICH_DA_CO")
        self.assertEqual(sl.sha256(self.folder / "postgresql.gpg"), first["sha256"])
        self.assertEqual(len(self.journal.read_text(encoding="utf-8").splitlines()), 1)

    def test_phan_loai_30_ngay_12_thang_khong_xoa(self):
        self.root.mkdir()
        stamps = [self.when - timedelta(days=n) for n in range(35)]
        stamps += [datetime(2025, month, 1, 23) for month in range(1, 13)]
        stamps += [datetime(2026, month, 1, 23) for month in range(1, 10)]
        stamps += [self.when.replace(hour=10)]
        for dt in set(stamps):
            folder = self.root / dt.strftime("%Y%m%d-%H%M%S")
            folder.mkdir()
            (folder / "postgresql.gpg").write_bytes(b"CIPHERTEXT")
        partial_folder = self.root / "20271026-230000"
        partial_folder.mkdir()
        (partial_folder / "postgresql.partial.gpg").write_bytes(b"PARTIAL")
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = sl.phan_loai_giu(self.root)
        names = sorted({dt.strftime("%Y%m%d-%H%M%S") for dt in stamps}, reverse=True)
        expected_daily = [(self.when - timedelta(days=n)).strftime("%Y%m%d-%H%M%S") for n in range(30)]
        expected_monthly = ["20261026-230000", "20260930-230000", "20260801-230000",
                            "20260701-230000", "20260601-230000", "20260501-230000",
                            "20260401-230000", "20260301-230000", "20260201-230000",
                            "20260101-230000", "20251201-230000", "20251101-230000"]
        self.assertEqual(result["giu_ngay"], expected_daily)
        self.assertEqual(result["giu_thang"], expected_monthly)
        self.assertEqual(len(result["giu_ngay"]), 30)
        self.assertEqual(len(result["giu_thang"]), 12)
        self.assertEqual(set(result["ngoai_han_de_xuat"]), set(names) - set(result["giu_ngay"] + result["giu_thang"]))
        self.assertFalse(result["tu_dong_xoa"])
        self.assertEqual(before, {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_chep_sha_doc_lap_va_khong_ghi_de(self):
        source = self.tmp / "nguon.gpg"
        source.write_bytes(b"BAN_MA_GIA\x00\xff")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target = self.tmp / "o-ngoai-gia" / "copy.gpg"
        result = sl.chep_ban_ma(source, target, digest, goc_cam=self.goc_cam)
        self.assertEqual(result["sha256"], digest)
        self.assertEqual(target.read_bytes(), source.read_bytes())
        with self.assertRaises(sl.LoiSaoLuu) as ctx:
            sl.chep_ban_ma(source, target, digest, goc_cam=self.goc_cam)
        self.assertEqual(ctx.exception.ma, "SL_DICH_DA_CO")

    def test_chep_phat_hien_nguon_sai_sha(self):
        source = self.tmp / "nguon.gpg"
        source.write_bytes(b"BAN_MA_GIA")
        target = self.tmp / "o-ngoai-gia" / "copy.gpg"
        with self.assertRaises(sl.LoiSaoLuu) as ctx:
            sl.chep_ban_ma(source, target, "0" * 64, goc_cam=self.goc_cam)
        self.assertEqual(ctx.exception.ma, "SL_SHA_NGUON")
        self.assertFalse(target.parent.exists())

    def test_chep_phat_hien_sai_lech_giu_partial(self):
        source = self.tmp / "nguon.gpg"
        source.write_bytes(b"BAN_MA_GIA")
        target = self.tmp / "o-ngoai-gia" / "copy.gpg"
        def corrupt(src, dst, length):
            dst.write(b"HONG")
        with patch.object(sl.shutil, "copyfileobj", side_effect=corrupt):
            with self.assertRaises(sl.LoiSaoLuu) as ctx:
                sl.chep_ban_ma(source, target, hashlib.sha256(source.read_bytes()).hexdigest(),
                              goc_cam=self.goc_cam)
        self.assertEqual(ctx.exception.ma, "SL_SHA_CHEP")
        self.assertFalse(target.exists())
        self.assertEqual(target.with_name("copy.partial.gpg").read_bytes(), b"HONG")

    def test_cli_loi_khong_echo_bi_mat(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = sl.main(["sao-luu", "--khong-hop-le", "postgresql://CANARY_PASSWORD@local/db"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out.getvalue()), {"ma_loi": "SL_THAM_SO"})


if __name__ == "__main__":
    unittest.main()
