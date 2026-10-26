"""M4-CD1: chỉ SQLite DEMO tự tạo. PG riêng kho_test_* do lead cấp DSN.

Không import/chạy vendor; lấy hằng SCHEMA bằng AST từ mã đã chép trong repo.
Không mở server, không xóa CSDL PG; lead kiểm/dọn kho_test_* sau nghiệm thu.
"""

from __future__ import annotations

import ast
import copy
import io
import json
import logging
import os
import sqlite3
import tempfile
import unittest
import uuid
from contextlib import closing, nullcontext, redirect_stderr, redirect_stdout
from datetime import datetime
from decimal import Decimal, localcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from kho_tri_thuc.ha_tang.primitives import DataError
from tools import chuyen_review_sqlite_sang_pg as chuyen
from kho_tri_thuc.m4 import review_doi_chieu as dc

try:
    import psycopg
    from psycopg import conninfo, sql
except ImportError:
    psycopg = None

DSN = os.environ.get("KHO_PG_DSN_TEST")
CHUP = "2026-10-26T07:00:00+07:00"
TEN_GIA = "DEMO_TEN_DOI_TAC_KHONG_DUOC_IN"
SO_HD = "DEMO_SO_HD_KHONG_DUOC_IN"
MA_HD = "DEMO_MA_HD_KHONG_DUOC_IN"
MAPPING = {MA_HD: (str(uuid.UUID(int=1)), str(uuid.UUID(int=2)))}


def schema_demo():
    source = Path(__file__).resolve().parents[1] / "src/kho_tri_thuc/m4/review_goc/csdl_hop_dong.py"
    tree = ast.parse(source.read_text(encoding="utf-8-sig"))
    return next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "SCHEMA" for t in node.targets))


def tao_demo(path):
    rows = {
        "hop_dong": [dict(ma_hd=MA_HD, so_hd=SO_HD, phan_loai=TEN_GIA, gia_tri_hd=1200.125, vat=0.08, gom_vat="Chưa VAT")],
        "tham_so": [dict(ma_hd=MA_HD, ma_ts="DEMO-TS", ten=TEN_GIA, gia_tri="", trich_dan=TEN_GIA)],
        "tham_so_nguon": [dict(ma_hd=MA_HD, ma_ts="DEMO-TS", gia_tri_ai=TEN_GIA, gia_tri="", muc=2, model=TEN_GIA)],
        "phu_luc": [dict(id=1, ma_hd=MA_HD, so_pl="DEMO-PL", ngay_ky="2026-01-01", ngay_hieu_luc="2026-01-02",
                         doi_boq=1, gt_truoc_vat=-10.125, gt_hd_sau_pl=None, trang_thai="Đã ký", noi_dung=TEN_GIA)],
        "thay_doi_tham_so": [dict(pl_id=1, ma_ts="DEMO-TS", gia_tri_cu=None, gia_tri_moi="", trich_dan=TEN_GIA)],
        "boq_dong": [dict(id=1, ma_hd=MA_HD, thao_tac="GOC", ma_hm="DEMO-HM", ten=TEN_GIA,
                          kl=2.5, don_gia=100.125, thanh_tien_ghi=250.3),
                     dict(id=2, ma_hd=MA_HD, pl_id=1, thao_tac="THAY", ma_hm="DEMO-HM", ten=TEN_GIA,
                          kl=-0.5, don_gia=None, thanh_tien_ghi=-10.125)],
        "dot_thanh_toan": [dict(ma_hd=MA_HD, dot=dot, ngay_nghiem_thu="DEMO ngày nguồn", gt_ky=100.125 * dot,
                                gt_luy_ke=100.125 * dot, giu_lai=None, thu_hoi_tu=0, gt_tt_ky=-0.125)
                           for dot in (1, 2)],
        "kl_thanh_toan": [dict(ma_hd=MA_HD, dot=dot, ma_hm="DEMO-HM", kl_ky=0.1, kl_luy_ke=0.2 * dot,
                               don_gia_tt=100.125, vi_tri_nguon=TEN_GIA) for dot in (1, 2)],
        "khop_hang_muc": [dict(ma_hd=MA_HD, khoa_hstt=TEN_GIA, ma_hm="DEMO-HM", nguoi_xac_nhan=TEN_GIA)],
        "canh_bao": [dict(id=1, ma_hd=MA_HD, pl_id=1, dot=1, noi_dung=TEN_GIA),
                     dict(id=2, ma_hd=None, noi_dung=TEN_GIA)],
        "nhat_ky": [dict(id=1, ma_hd=MA_HD, nguoi=TEN_GIA, chi_tiet=TEN_GIA),
                    dict(id=2, ma_hd="", nguoi=TEN_GIA, chi_tiet=TEN_GIA)],
    }
    with closing(sqlite3.connect(str(path))) as con:
        con.executescript(schema_demo())
        for table in chuyen.BANG_NGUON:
            for row in rows.get(table, []):
                con.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", tuple(row.values()))
        con.commit()


class ChuyenReviewTinhTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory(prefix="m4_cd1_demo_"))
        self.root = Path(self.temp)
        # URI phải giữ đúng ký tự đặc biệt, không coi #/? là query/fragment.
        self.source = self.root / "nguồn DEMO #1.db"
        tao_demo(self.source)
        self.csv = self.root / "anh-xa.csv"
        self.config = self.root / "ket-noi.json"
        self.config.write_text(json.dumps({"admin_dsn": "DEMO_DSN_BI_MAT"}), encoding="utf-8")
        self.csv.write_text("ma_hd,hop_dong_id,du_an_id\n" + MA_HD + "," + ",".join(MAPPING[MA_HD]) + "\n", encoding="utf-8")

    def args(self, *extra):
        return ["--nguon", str(self.source), "--anh-xa", str(self.csv), "--dsn-tep", str(self.config),
                "--nguon-id", "DEMO-CD1", "--chup-luc", CHUP, *extra]

    def run_cli(self, *extra):
        output = io.StringIO()
        with redirect_stdout(output):
            code = chuyen.main(self.args(*extra))
        raw = output.getvalue()
        return code, [json.loads(line) for line in raw.splitlines()], raw

    def test_12_bang_dung_ddl_vendor_va_giu_nguyen_sha(self):
        before = chuyen.sha256_tep(self.source)
        announcements = []
        real_open = chuyen.mo_nguon

        def open_after_report(path):
            self.assertEqual(announcements, [{"sha256_truoc": before}])
            return real_open(path)

        with patch.object(chuyen, "mo_nguon", side_effect=open_after_report):
            data, digest = chuyen.doc_nguon(self.source, bao_truoc=announcements.append)
        self.assertEqual(set(data), set(chuyen.BANG_NGUON))
        self.assertEqual(len(data), 12)
        for table, rows in data.items():
            self.assertTrue(rows, table)
            self.assertEqual(set(rows[0]), set(chuyen.COT[table]))
        self.assertEqual(digest, before)
        self.assertEqual(chuyen.sha256_tep(self.source), before)
        chuyen.kiem_du_lieu(data, MAPPING)

    def test_uri_chi_doc_ke_ca_tat_query_only(self):
        before = chuyen.sha256_tep(self.source)
        with closing(chuyen.mo_nguon(self.source)) as con:
            con.execute("PRAGMA query_only=OFF")
            with self.assertRaises(sqlite3.OperationalError):
                con.execute("INSERT INTO nhat_ky(id) VALUES(99)")
        self.assertEqual(chuyen.sha256_tep(self.source), before)

    def test_nguon_khong_ton_tai_khong_tao_db(self):
        missing = self.root / "DEMO-khong-co.db"
        with self.assertRaises(FileNotFoundError):
            chuyen.mo_nguon(missing)
        self.assertFalse(missing.exists())

    def test_thu_khong_goi_pg_va_bao_cao_khong_lo_du_lieu(self):
        before = chuyen.sha256_tep(self.source)
        driver = Mock()
        with patch.dict("sys.modules", {"psycopg": driver}), patch.object(chuyen, "ghi_pg") as write:
            code, reports, raw = self.run_cli("--thu")
        self.assertEqual(code, 0)
        write.assert_not_called()
        driver.connect.assert_not_called()
        self.assertEqual(set(reports[0]), {"sha256_truoc"})
        report = reports[-1]
        self.assertEqual(report["trang_thai"], "THU_KHONG_GHI")
        self.assertEqual(report["sha256_sau"], before)
        for table, count in report["bang"].items():
            self.assertGreater(count["da_doc"], 0)
            self.assertEqual(count["da_ghi_moi"], 0)
            self.assertIsNone(count["da_co_dich"])
        for secret in (TEN_GIA, SO_HD, MA_HD, "DEMO_DSN_BI_MAT", str(self.source)):
            self.assertNotIn(secret, raw)
        self.assertEqual(chuyen.sha256_tep(self.source), before)

    def test_tong_control_giu_null_am_decimal_va_khong_cong_luy_ke(self):
        data, _ = chuyen.doc_nguon(self.source)
        totals = chuyen.tong_kiem_soat(data)
        self.assertEqual(totals["gia_tri_hd_goc"], {"tong": "1200.125", "so_null": 0})
        boq = totals["boq_theo_thao_tac"]
        self.assertEqual(boq["GOC"]["thanh_tien_ghi"]["tong"], "250.3")
        self.assertEqual(boq["GOC"]["kl_nhan_don_gia_chua_lam_tron"]["tong"], "250.3125")
        self.assertEqual(boq["THAY"]["thanh_tien_ghi"]["tong"], "-10.125")
        self.assertIsNone(boq["THAY"]["kl_nhan_don_gia_chua_lam_tron"]["tong"])
        dots = totals["tung_dot"]
        self.assertEqual([r["thu_tu"] for r in dots], [1, 2])
        self.assertEqual([r["gt_luy_ke"]["tong"] for r in dots], ["100.125", "200.25"])
        self.assertEqual(dots[0]["giu_lai"], {"tong": None, "so_null": 1})

    def test_thieu_anh_xa_dung_truoc_ket_noi(self):
        self.csv.write_text("ma_hd,hop_dong_id,du_an_id\n", encoding="utf-8")
        with patch.object(chuyen, "ghi_pg") as write:
            code, reports, raw = self.run_cli()
        self.assertEqual(code, 1)
        self.assertEqual(reports[-1]["ma_loi"], "M4_REVIEW_THIEU_ANH_XA")
        self.assertEqual(reports[-1]["bang"], "hop_dong.ma_hd")
        write.assert_not_called()
        self.assertNotIn(MA_HD, raw)

    def test_csv_trung_khoa_uuid_sai_va_thua_cot_dung(self):
        valid = MA_HD + "," + ",".join(MAPPING[MA_HD]) + "\n"
        for suffix in (valid + valid, MA_HD + ",DEMO,DEMO\n", valid.rstrip() + ",DEMO\n"):
            with self.subTest(suffix=suffix):
                self.csv.write_text("ma_hd,hop_dong_id,du_an_id\n" + suffix, encoding="utf-8")
                with self.assertRaises(DataError):
                    chuyen.doc_anh_xa(self.csv)

    def test_thieu_bang_khong_nap_mot_phan(self):
        other = self.root / "DEMO-thieu.db"
        with closing(sqlite3.connect(other)) as con:
            con.execute("CREATE TABLE che_do(id INTEGER, sua INTEGER)")
        with self.assertRaises(DataError) as caught:
            chuyen.doc_nguon(other)
        self.assertEqual(caught.exception.code, "M4_REVIEW_LUOC_DO_SAI")

    def test_sha_doi_trong_luc_doc_thi_dung(self):
        real_open = chuyen.mo_nguon

        def changed(path):
            con = real_open(path)
            with self.source.open("ab") as stream:
                stream.write(b"DEMO file changed")
            return con

        with patch.object(chuyen, "mo_nguon", side_effect=changed), self.assertRaises(DataError) as caught:
            chuyen.doc_nguon(self.source)
        self.assertEqual(caught.exception.code, "M4_REVIEW_NGUON_DA_DOI")

    def test_wal_chua_checkpoint_bi_chan(self):
        Path(str(self.source) + "-wal").write_bytes(b"DEMO pending WAL")
        with self.assertRaises(DataError) as caught:
            chuyen.doc_nguon(self.source)
        self.assertEqual(caught.exception.code, "M4_REVIEW_NGUON_DANG_GHI")

    def test_schema_cu_thieu_ma_rieng_chi_dien_null_khong_alter(self):
        other = self.root / "DEMO-cu.db"
        ddl = schema_demo().replace("ghi_chu TEXT,\n    ma_rieng TEXT", "ghi_chu TEXT")
        with closing(sqlite3.connect(other)) as con:
            con.executescript(ddl)
            con.execute("INSERT INTO hop_dong(ma_hd,so_hd) VALUES('DEMO','DEMO')")
            con.execute("INSERT INTO boq_dong(id,ma_hd,thao_tac,ma_hm) VALUES(1,'DEMO','GOC','DEMO')")
            con.commit()
        before = chuyen.sha256_tep(other)
        data, _ = chuyen.doc_nguon(other)
        self.assertIsNone(data["boq_dong"][0]["ma_rieng"])
        self.assertEqual(chuyen.sha256_tep(other), before)
        with closing(chuyen.mo_nguon(other)) as con:
            self.assertNotIn("ma_rieng", {r[1] for r in con.execute("PRAGMA table_info(boq_dong)")})

    def test_du_lieu_sai_fk_kieu_nan_trung_khoa_dung(self):
        original, _ = chuyen.doc_nguon(self.source)
        for kind in ("orphan", "text", "nan", "trung", "phu_luc", "boq", "unique"):
            data = copy.deepcopy(original)
            if kind == "orphan":
                data["kl_thanh_toan"][0]["dot"] = 99
            elif kind == "text":
                data["nhat_ky"][0]["chi_tiet"] = 1
            elif kind == "nan":
                data["dot_thanh_toan"][0]["gt_ky"] = float("nan")
            elif kind == "trung":
                data["canh_bao"].append(dict(data["canh_bao"][0]))
            elif kind == "phu_luc":
                data["thay_doi_tham_so"][0]["pl_id"] = 999
            elif kind == "boq":
                data["boq_dong"][1]["pl_id"] = 999
            else:
                data["phu_luc"].append(dict(data["phu_luc"][0], id=2))
            with self.subTest(kind=kind), self.assertRaises(DataError):
                chuyen.kiem_du_lieu(data, MAPPING)

    def test_loi_driver_khong_in_dsn_hay_payload(self):
        driver = Mock()
        driver.connect.side_effect = RuntimeError("DEMO_DSN_BI_MAT " + TEN_GIA)
        with patch.dict("sys.modules", {"psycopg": driver}):
            code, reports, raw = self.run_cli()
        self.assertEqual(code, 1)
        self.assertEqual(reports[-1]["ma_loi"], "M4_REVIEW_CHUYEN_LOI")
        self.assertNotIn(TEN_GIA, raw)
        self.assertNotIn("DEMO_DSN_BI_MAT", raw)

    def test_stdout_cp1252_loi_driver_khong_lo_traceback_hay_bi_mat(self):
        driver = Mock()
        driver.connect.side_effect = RuntimeError('invalid percent-encoded token: "BI_MAT_DEMO_123"')
        output = io.BytesIO()
        errors = io.StringIO()
        with io.TextIOWrapper(output, encoding="cp1252") as stream:
            with patch.dict("sys.modules", {"psycopg": driver}), redirect_stdout(stream), redirect_stderr(errors):
                code = chuyen.main(self.args())
            stream.flush()
            raw = output.getvalue().decode("cp1252")
        self.assertNotEqual(code, 0)
        driver.connect.assert_called_once()
        self.assertEqual(json.loads(raw.splitlines()[-1])["ma_loi"], "M4_REVIEW_CHUYEN_LOI")
        for text in (raw, errors.getvalue()):
            self.assertNotIn("Traceback", text)
            self.assertNotIn("BI_MAT_DEMO_123", text)

    def test_ctrl_c_khi_ghi_va_khi_rollback_khong_lo_exception_goc(self):
        for rollback in (False, True):
            with self.subTest(rollback=rollback):
                driver = MagicMock()
                con = driver.connect.return_value.__enter__.return_value
                transaction = con.transaction.return_value
                if rollback:
                    failure = RuntimeError("DETAIL: BI_MAT_DEMO_456")

                    def interrupt(*args):
                        raise KeyboardInterrupt

                    transaction.__exit__.side_effect = interrupt
                else:
                    failure = KeyboardInterrupt()
                errors = io.StringIO()
                with patch.dict("sys.modules", {"psycopg": driver}), \
                        patch.object(chuyen, "ReviewDataPG") as base, redirect_stderr(errors):
                    base.return_value.ghi_lan_chup.side_effect = failure
                    code, _, raw = self.run_cli()
                self.assertEqual(code, 130)
                driver.connect.assert_called_once()
                transaction.__exit__.assert_called_once()
                self.assertIs(transaction.__exit__.call_args.args[1], failure)
                self.assertEqual(errors.getvalue(), "M4_REVIEW_CHUYEN_DUNG\n")
                for text in (raw, errors.getvalue()):
                    self.assertNotIn("Traceback", text)
                    self.assertNotIn("BI_MAT_DEMO_456", text)

    def test_base_exception_khac_duoc_bao_loi_chung(self):
        driver = Mock()
        driver.connect.side_effect = BaseException("DETAIL: BI_MAT_DEMO_456")
        errors = io.StringIO()
        with patch.dict("sys.modules", {"psycopg": driver}), redirect_stderr(errors):
            code, reports, raw = self.run_cli()
        self.assertEqual(code, 1)
        self.assertEqual(reports[-1]["ma_loi"], "M4_REVIEW_CHUYEN_LOI")
        for text in (raw, errors.getvalue()):
            self.assertNotIn("Traceback", text)
            self.assertNotIn("BI_MAT_DEMO_456", text)

    def test_logger_psycopg_warning_khong_ra_stderr(self):
        driver = MagicMock()

        def warning(con, data, mapping, **kwargs):
            logging.getLogger("psycopg").warning("DETAIL: BI_MAT_DEMO_456")
            logging.getLogger("psycopg.connection").warning("DETAIL: BI_MAT_DEMO_456")
            # CLI cần số đếm đủ 12 bảng để tạo báo cáo hoàn tất.
            return {table: {"da_ghi_moi": len(rows), "da_co_dich": len(rows)}
                    for table, rows in data.items()}

        errors = io.StringIO()
        with patch.dict("sys.modules", {"psycopg": driver}), \
                patch.object(chuyen, "ghi_pg", side_effect=warning) as write, redirect_stderr(errors):
            code, reports, _ = self.run_cli()
        self.assertEqual(code, 0)
        driver.connect.assert_called_once()
        write.assert_called_once()
        self.assertEqual(reports[-1]["trang_thai"], "HOAN_TAT")
        self.assertEqual(errors.getvalue(), "")

    def test_console_hong_khi_bao_loi_van_thoat_khong_lo_exception_goc(self):
        driver = Mock()
        driver.connect.side_effect = RuntimeError('invalid percent-encoded token: "BI_MAT_DEMO_123"')
        for stderr_broken in (False, True):
            with self.subTest(stderr_broken=stderr_broken):
                output = io.StringIO()
                errors = Mock() if stderr_broken else io.StringIO()
                if stderr_broken:
                    errors.write.side_effect = OSError("BI_MAT_DEMO_123")
                real_print = print

                def print_until_error(text, **kwargs):
                    if json.loads(text).get("trang_thai") == "LOI":
                        raise OSError("BI_MAT_DEMO_123")
                    real_print(text, **kwargs)

                with patch.dict("sys.modules", {"psycopg": driver}), redirect_stdout(output), redirect_stderr(errors), \
                        patch("builtins.print", side_effect=print_until_error):
                    code = chuyen.main(self.args())
                self.assertNotEqual(code, 0)
                self.assertNotIn("Traceback", output.getvalue())
                self.assertNotIn("BI_MAT_DEMO_123", output.getvalue())
                if stderr_broken:
                    errors.write.assert_called_once_with("M4_REVIEW_CHUYEN_LOI\n")
                else:
                    self.assertEqual(errors.getvalue(), "M4_REVIEW_CHUYEN_LOI\n")

    def test_hop_dong_da_xoa_khong_doi_anh_xa_dem_mo_coi_theo_bang(self):
        deleted = "DEMO_MA_HD_DA_XOA_KHONG_DUOC_IN"
        with closing(sqlite3.connect(self.source)) as con:
            con.executemany("INSERT INTO nhat_ky(id,ma_hd) VALUES(?,?)", [(3, deleted), (4, deleted)])
            con.execute("INSERT INTO canh_bao(id,ma_hd) VALUES(3,?)", (deleted,))
            con.commit()
        code, reports, raw = self.run_cli("--thu")
        self.assertEqual(code, 0)
        expected = {t: 0 for t in chuyen.BANG_NGUON}
        expected.update(nhat_ky=2, canh_bao=1)
        self.assertEqual({t: r["so_dong_mo_coi"] for t, r in reports[-1]["bang"].items()}, expected)
        self.assertNotIn(deleted, raw)
        data, _ = chuyen.doc_nguon(self.source)
        con = Mock()
        # Kể cả CSV còn ánh xạ cũ, dòng mồ côi phải ghi cả hai UUID là NULL.
        for mapping in (MAPPING, {**MAPPING, deleted: MAPPING[MA_HD]}):
            chuyen.kiem_du_lieu(data, mapping)
            con.reset_mock()
            with patch.object(chuyen, "_rows", return_value=[]):
                chuyen._ghi_con_lai(con, data, mapping, "DEMO", False)
            orphan_count = 0
            for call in con.execute.call_args_list:
                query, params = call.args
                columns = query.split("(", 1)[1].split(")", 1)[0].split(",")
                row = dict(zip(columns, params))
                if row.get("ma_hd") == deleted:
                    orphan_count += 1
                    self.assertIsNone(row["hop_dong_id"])
                    self.assertIsNone(row["du_an_id"])
            self.assertEqual(orphan_count, 3)

    def test_bao_loi_bang_cot_chi_tu_hang_khong_in_gia_tri(self):
        original, _ = chuyen.doc_nguon(self.source)
        for table, column, value, expected in (
            ("nhat_ky", "chi_tiet", 1, "nhat_ky.chi_tiet"),
            ("dot_thanh_toan", "gt_ky", float("nan"), "dot_thanh_toan.gt_ky"),
            ("phu_luc", "ma_hd", "DEMO_DA_XOA", "phu_luc.ma_hd"),
        ):
            with self.subTest(table=table, column=column):
                data = copy.deepcopy(original)
                data[table][0][column] = value
                with patch.object(chuyen, "doc_nguon", return_value=(data, "0" * 64)):
                    code, reports, raw = self.run_cli("--thu")
                self.assertNotEqual(code, 0)
                self.assertEqual(reports[-1]["bang"], expected)
                for secret in (TEN_GIA, SO_HD, MA_HD, "DEMO_DA_XOA"):
                    self.assertNotIn(secret, raw)
        error = DataError("M4_REVIEW_DU_LIEU_SAI", TEN_GIA, locator=MA_HD)
        with patch.object(chuyen, "doc_nguon", side_effect=error):
            code, reports, raw = self.run_cli("--thu")
        self.assertEqual(code, 1)
        self.assertIsNone(reports[-1]["bang"])
        self.assertNotIn(MA_HD, raw)
        self.assertNotIn(TEN_GIA, raw)

    def test_sha256_nguon_truyen_tu_cli_vao_mo_ta_dl2(self):
        digest = chuyen.sha256_tep(self.source)
        data, _ = chuyen.doc_nguon(self.source)
        driver = MagicMock()
        con = driver.connect.return_value.__enter__.return_value
        with patch.dict("sys.modules", {"psycopg": driver}), \
                patch.object(chuyen, "ReviewDataPG") as base, patch.object(chuyen, "ReviewPhuLucPG"), \
                patch.object(chuyen, "_ghi_con_lai"):
            base.return_value.ghi_lan_chup.return_value = 5
            con.execute.side_effect = [Mock(fetchone=Mock(return_value=(len(data[t]),))) for t in chuyen.BANG_NGUON]
            code, reports, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(reports[-1]["trang_thai"], "HOAN_TAT")
        self.assertEqual(base.return_value.ghi_lan_chup.call_args.kwargs["mo_ta"], "sha256:" + digest)

    def test_metadata_thieu_timezone_dung_truoc_doc(self):
        args = self.args("--thu")
        args[args.index("--chup-luc") + 1] = "2026-10-26T07:00:00"
        with redirect_stdout(io.StringIO()), patch.object(chuyen, "doc_nguon") as read:
            self.assertEqual(chuyen.main(args), 1)
        read.assert_not_called()

    def test_dl2_dl3_cung_connection_loi_thoat_outer_transaction(self):
        data, _ = chuyen.doc_nguon(self.source)
        con = MagicMock()
        with patch.object(chuyen, "ReviewDataPG") as base, patch.object(chuyen, "ReviewPhuLucPG") as pl:
            base.return_value.ghi_lan_chup.return_value = 5
            pl.return_value.ghi_trong_giao_dich.side_effect = RuntimeError("DEMO failure")
            with self.assertRaises(RuntimeError):
                chuyen.ghi_pg(con, data, MAPPING, nguon_id="DEMO", chup_luc=CHUP)
        base.assert_called_once_with(con)
        pl.assert_called_once_with(con)
        self.assertIs(con.transaction.return_value.__exit__.call_args.args[0], RuntimeError)
        con.commit.assert_not_called()

    def test_5_bang_hash_replay_va_khong_tao_fk_cho_log_orphan(self):
        data, _ = chuyen.doc_nguon(self.source)
        con = Mock()
        # Ghi vào kết nối giả, lưu nguyên tham số INSERT làm ảnh đích replay.
        with patch.object(chuyen, "_rows", return_value=[]):
            chuyen._ghi_con_lai(con, data, MAPPING, "DEMO", False)
        saved = {t: [] for t in chuyen.CON_LAI}
        for call in con.execute.call_args_list:
            query, params = call.args
            table = query.split("m4.review_chep_", 1)[1].split(" ", 1)[0]
            columns = query.split("(", 1)[1].split(")", 1)[0].split(",")
            saved[table].append(dict(zip(columns, params)))
        self.assertEqual({t: len(rows) for t, rows in saved.items()},
                         {t: len(data[t]) for t in chuyen.CON_LAI})
        for row in saved["nhat_ky"] + saved["canh_bao"]:
            if row["ma_hd"] in (None, ""):
                self.assertIsNone(row["hop_dong_id"])
                self.assertIsNone(row["du_an_id"])

        def existing(con, query, params):
            table = query.split("m4.review_chep_", 1)[1].split(" ", 1)[0]
            return saved[table]

        con.reset_mock()
        with patch.object(chuyen, "_rows", side_effect=existing):
            chuyen._ghi_con_lai(con, data, MAPPING, "DEMO", True)
        con.execute.assert_not_called()
        for table in chuyen.CON_LAI:
            for kind in ("doi", "them", "bot"):
                changed = copy.deepcopy(data)
                if kind == "doi":
                    col = next(c for c in chuyen.COT[table] if c not in chuyen.PK[table] and c != "ma_hd")
                    changed[table][0][col] = None if changed[table][0][col] is not None else "DEMO đổi"
                elif kind == "them":
                    row = dict(changed[table][0])
                    key = chuyen.PK[table][-1]
                    row[key] = row[key] + 99 if isinstance(row[key], int) else row[key] + "DEMO"
                    changed[table].append(row)
                else:
                    changed[table].pop()
                with self.subTest(table=table, kind=kind), patch.object(chuyen, "_rows", side_effect=existing):
                    with self.assertRaises(DataError) as caught:
                        chuyen._ghi_con_lai(con, changed, MAPPING, "DEMO", True)
                    self.assertEqual(caught.exception.code, "M4_REVIEW_REPLAY_KHAC")


class PGGiaDoiChieu:
    """Ảnh PG giả có numeric Decimal, chỉ nhận SELECT snapshot của CD2."""

    def __init__(self, source):
        self.data = {}
        with closing(sqlite3.connect(source)) as con:
            con.row_factory = sqlite3.Row
            tables = (r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'"))
            for table in tables:
                if table == "sqlite_sequence":
                    continue
                self.data[table] = [dict(r) for r in con.execute(f'SELECT * FROM "{table}"')]
        # SQLite trả REAL; PG thực trả numeric. Không gọi chuyển kiểu của CD1/DL2.
        for rows in self.data.values():
            for row in rows:
                for key, value in row.items():
                    if type(value) is float:
                        row[key] = Decimal(repr(value))
        contracts = {r["ma_hd"] for r in self.data["hop_dong"]}
        for rows in self.data.values():
            for row in rows:
                if "ma_hd" in row:
                    row["hop_dong_id"] = uuid.UUID(int=1) if row["ma_hd"] in contracts else None
        self.mo_ta = "sha256:" + chuyen.sha256_tep(source)
        self.queries = []

    def transaction(self):
        return nullcontext()

    def execute(self, query, params=()):
        self.queries.append((query, params))
        if query == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY":
            return None
        if params != ("DEMO-CD2",):
            raise AssertionError("Mọi SELECT phải ghim nguon_id")
        if query == "SELECT chup_luc,mo_ta FROM m4.review_chep_nguon WHERE id=%s":
            rows = [{"chup_luc": datetime.fromisoformat(CHUP), "mo_ta": self.mo_ta}]
            columns = ["chup_luc", "mo_ta"]
        else:
            columns = query.split("SELECT ", 1)[1].split(" FROM ", 1)[0].split(",")
            table = query.split("m4.review_chep_", 1)[1].split(" ", 1)[0]
            if not query.endswith(" WHERE nguon_id=%s"):
                raise AssertionError("SELECT không giới hạn lần chụp")
            rows = [{c: r[c] for c in columns} for r in self.data[table]]
        return SimpleNamespace(description=[SimpleNamespace(name=c) for c in columns],
                               fetchall=lambda: rows)


class DoiChieuReviewTinhTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="m4_cd2_demo_")))
        self.source = self.root / "DEMO #nguồn.db"
        tao_demo(self.source)
        self.pg = PGGiaDoiChieu(self.source)

    def report(self):
        return dc.doi_chieu(self.source, self.pg, nguon_id="DEMO-CD2")

    def doi_nguon(self, query, params=()):
        with closing(sqlite3.connect(self.source)) as con:
            con.execute(query, params)
            con.commit()

    def test_khop_12_bang_decimal_khong_dung_ma_cd1(self):
        before = chuyen.sha256_tep(self.source)
        with patch.object(chuyen, "doc_nguon", side_effect=AssertionError("CD1")), \
                patch.object(chuyen, "tong_kiem_soat", side_effect=AssertionError("CD1")), \
                patch.object(chuyen, "real_sang_decimal", side_effect=AssertionError("CD1")):
            report = self.report()
        self.assertTrue(report["khop"])
        self.assertEqual(len(report["bang"]), 12)
        self.assertEqual(report["so_dong_loi"], 0)
        self.assertEqual(report["tong_sqlite"], report["tong_pg"])
        self.assertEqual(report["tong_pg"]["tung_hd"][0]["khoa"], "HD0001")
        self.assertEqual(report["tong_pg"]["tung_hd"][0]["boq"]["GOC"]["kl_nhan_don_gia"]["tong"], "250.3125")
        self.assertEqual(chuyen.sha256_tep(self.source), before)
        self.assertEqual(len(self.pg.queries), 14)
        self.assertTrue(self.pg.queries[0][0].startswith("SET TRANSACTION"))

    def test_dem_mo_coi_ke_ca_ma_null_rong_va_hd_da_xoa(self):
        deleted = "DEMO_HD_DA_XOA"
        self.doi_nguon("INSERT INTO canh_bao(id,ma_hd) VALUES(3,?)", (deleted,))
        self.doi_nguon("INSERT INTO nhat_ky(id,ma_hd) VALUES(3,?)", (deleted,))
        self.doi_nguon("INSERT INTO khop_hang_muc(ma_hd,khoa_hstt,ma_hm) VALUES(?,'DEMO','DEMO')", (deleted,))
        self.pg = PGGiaDoiChieu(self.source)
        report = self.report()
        self.assertTrue(report["khop"])
        for table in dc._COT:
            if "ma_hd" in dc._COT[table]:
                expected = {"canh_bao": 2, "nhat_ky": 2, "khop_hang_muc": 1}.get(table, 0)
                self.assertEqual(report["bang"][table]["so_dong_mo_coi"], {"sqlite": expected, "pg": expected})

    def test_gan_hd_sai_ke_ca_mo_coi_va_thieu_lien_ket(self):
        for table, index, value in (("canh_bao", 1, uuid.UUID(int=1)),
                                     ("nhat_ky", 0, uuid.UUID(int=99)),
                                     ("khop_hang_muc", 0, None)):
            with self.subTest(table=table):
                self.pg = PGGiaDoiChieu(self.source)
                self.pg.data[table][index]["hop_dong_id"] = value
                report = self.report()
                self.assertFalse(report["khop"])
                self.assertEqual([(r["bang"], r["ma_loi"]) for r in report["dong_loi"]], [(table, "GAN_HD_SAI")])

    def test_tong_lech_doc_lap_du_tung_o_khop(self):
        source = dc._doc_sqlite(self.source)
        totals = dc._thong_ke(source, {MA_HD: "HD0001"})
        for kind in ("tung_hd", "tung_dot"):
            changed = copy.deepcopy(totals)
            field = "gia_tri_hd" if kind == "tung_hd" else "gt_ky"
            changed[kind][0][field]["tong"] = "999"
            with self.subTest(kind=kind), patch.object(dc, "_doc_sqlite", return_value=source), \
                    patch.object(dc, "_thong_ke", side_effect=[totals, changed]):
                report = self.report()
            self.assertFalse(report["khop"])
            self.assertTrue(report["sha256_khop"])
            self.assertEqual(report["so_dong_loi"], 0)
            expected = {"khoa": "HD0001", "chi_tieu": field + ".tong",
                        "tong_sqlite": totals[kind][0][field]["tong"], "tong_pg": "999"}
            if kind == "tung_dot":
                expected["dot"] = 1
            self.assertEqual(report["tong_lech_hd" if kind == "tung_hd" else "tong_lech_dot"], [expected])
            for secret in (TEN_GIA, SO_HD, MA_HD):
                self.assertNotIn(secret, json.dumps(report))

    def test_sha_khac_thieu_va_nguon_doi_trong_khi_doc(self):
        for mo_ta in (None, "sha256:" + "0" * 64):
            with self.subTest(mo_ta=mo_ta):
                self.pg.mo_ta = mo_ta
                report = self.report()
                self.assertFalse(report["sha256_khop"])
                self.assertFalse(report["khop"])
                self.assertEqual(report["so_dong_loi"], 0)
        self.pg = PGGiaDoiChieu(self.source)
        digest = chuyen.sha256_tep(self.source)
        with patch.object(dc, "_sha256_tep", side_effect=[digest, "0" * 64]):
            self.assertFalse(self.report()["sha256_khop"])

    def test_nguon_chi_doc_va_khong_tao_file_sai(self):
        real_connect = sqlite3.connect

        def connect(database, **kwargs):
            self.assertIn("mode=ro&immutable=1", database)
            con = real_connect(database, **kwargs)
            con.execute("PRAGMA query_only=OFF")
            with self.assertRaises(sqlite3.OperationalError):
                con.execute("UPDATE hop_dong SET gia_tri_hd=0")
            con.rollback()
            return con

        with patch.object(dc.sqlite3, "connect", side_effect=connect):
            self.assertTrue(self.report()["khop"])
        missing = self.root / "khong-co.db"
        with self.assertRaises(FileNotFoundError):
            dc.doi_chieu(missing, self.pg, nguon_id="DEMO-CD2")
        self.assertFalse(missing.exists())

    def test_lech_boq_dung_hd_va_khong_tin_hash(self):
        self.pg.data["boq_dong"][0]["thanh_tien_ghi"] += Decimal("0.001")
        self.pg.data["boq_dong"][0]["dong_sha256"] = "0" * 64
        report = self.report()
        self.assertFalse(report["khop"])
        self.assertEqual(report["dong_loi"], [{"bang": "boq_dong", "khoa_dong": "K000001", "khoa": "HD0001",
                                               "ma_loi": "GIA_TRI_LECH", "cot": ["thanh_tien_ghi"]}])

    def test_hai_hd_lech_triet_tieu_tong_chung(self):
        second = "ZZ_DEMO_HD_BI_MAT"
        self.doi_nguon("INSERT INTO hop_dong(ma_hd,so_hd,gia_tri_hd) VALUES(?,?,?)", (second, "ZZ_BI_MAT", 100))
        self.doi_nguon("INSERT INTO boq_dong(id,ma_hd,ma_hm,thao_tac,kl,don_gia,thanh_tien_ghi) VALUES(9,?,'HM2','GOC',1,100,100)", (second,))
        self.pg = PGGiaDoiChieu(self.source)
        self.pg.data["hop_dong"][0]["gia_tri_hd"] += 10
        self.pg.data["hop_dong"][1]["gia_tri_hd"] -= 10
        self.pg.data["boq_dong"][0]["thanh_tien_ghi"] += 10
        self.pg.data["boq_dong"][2]["thanh_tien_ghi"] -= 10
        report = self.report()
        self.assertFalse(report["khop"])
        self.assertEqual(report["tong_sqlite"]["gia_tri_hd"], report["tong_pg"]["gia_tri_hd"])
        self.assertEqual({r["khoa"] for r in report["dong_loi"]}, {"HD0001", "HD0002"})
        for side in ("tong_sqlite", "tong_pg"):
            self.assertEqual(sum(Decimal(h["boq"]["GOC"]["thanh_tien_ghi"]["tong"]) for h in report[side]["tung_hd"]), Decimal("350.3"))

    def test_hai_dot_lech_triet_tieu_va_lech_dong_trong_cung_dot(self):
        self.pg.data["dot_thanh_toan"][0]["gt_ky"] += 10
        self.pg.data["dot_thanh_toan"][1]["gt_ky"] -= 10
        report = self.report()
        self.assertFalse(report["khop"])
        self.assertEqual({r["dot"] for r in report["dong_loi"]}, {1, 2})
        self.assertEqual(sum(Decimal(r["gt_ky"]["tong"]) for r in report["tong_pg"]["tung_dot"]), Decimal("300.375"))
        self.doi_nguon("INSERT INTO kl_thanh_toan(ma_hd,dot,ma_hm,kl_ky,don_gia_tt) VALUES(?,1,'HM2',0.1,100.125)", (MA_HD,))
        self.pg = PGGiaDoiChieu(self.source)
        self.pg.data["kl_thanh_toan"][0]["kl_ky"] += Decimal("0.01")
        self.pg.data["kl_thanh_toan"][-1]["kl_ky"] -= Decimal("0.01")
        report = self.report()
        self.assertFalse(report["khop"])
        self.assertEqual(report["tong_sqlite"], report["tong_pg"])
        self.assertEqual(report["bang"]["kl_thanh_toan"]["so_dong_loi"], 2)

    def test_khoa_thieu_hai_phia_du_so_dong_tong(self):
        self.pg.data["khop_hang_muc"][0]["khoa_hstt"] = "DEMO_KHOA_BI_MAT_MOI"
        report = self.report()
        table = report["bang"]["khop_hang_muc"]
        self.assertEqual(table["sqlite"], table["pg"])
        self.assertEqual(len(table["thieu_pg"]), 1)
        self.assertEqual(len(table["thieu_sqlite"]), 1)
        self.assertEqual(table["so_dong_loi"], 2)
        self.assertNotIn("DEMO_KHOA_BI_MAT_MOI", json.dumps(report))

    def test_null_khac_zero_va_sua_noi_dung_duoc_bao_khong_lo_gia_tri(self):
        self.pg.data["dot_thanh_toan"][0]["giu_lai"] = Decimal(0)
        self.pg.data["nhat_ky"][0]["chi_tiet"] = "DEMO_CHI_TIET_BI_MAT"
        report = self.report()
        self.assertFalse(report["khop"])
        raw = json.dumps(report, ensure_ascii=True)
        for secret in (TEN_GIA, SO_HD, MA_HD, "DEMO_CHI_TIET_BI_MAT", "DEMO-HM", "DEMO-TS", "DEMO-PL"):
            self.assertNotIn(secret, raw)
        raw.encode("ascii")

    def test_co_can_xem_lai_dl3_tai_ngay_chup(self):
        self.assertEqual(self.report()["so_hd_can_xem_lai"], 0)
        self.doi_nguon("INSERT INTO phu_luc(id,ma_hd,so_pl,ngay_ky,ngay_hieu_luc,doi_boq,trang_thai) VALUES(9,?,'PL2','2026-01-01','2026-01-02',0,'Đã ký')", (MA_HD,))
        self.pg = PGGiaDoiChieu(self.source)
        report = self.report()
        self.assertTrue(report["khop"])
        self.assertEqual(report["so_hd_can_xem_lai"], 1)

    def test_decimal_khong_phu_thuoc_context_va_khong_dung_tolerance(self):
        with localcontext() as ctx:
            ctx.prec = 3
            self.assertTrue(self.report()["khop"])
        self.pg.data["hop_dong"][0]["gia_tri_hd"] = Decimal("1200.125000000000000000000000001")
        with localcontext() as ctx:
            ctx.prec = 3
            report = self.report()
        self.assertFalse(report["khop"])
        self.assertEqual(report["tong_pg"]["gia_tri_hd"]["tong"], "1200.125000000000000000000000001")

    def test_wal_schema_cu_va_nguon_rong(self):
        other = self.root / "cu.db"
        with closing(sqlite3.connect(other)) as con:
            con.executescript(schema_demo().replace("ghi_chu TEXT,\n    ma_rieng TEXT", "ghi_chu TEXT"))
            con.commit()
        self.assertTrue(dc.doi_chieu(other, PGGiaDoiChieu(other), nguon_id="DEMO-CD2")["khop"])
        Path(str(self.source) + "-wal").write_bytes(b"DEMO WAL")
        with self.assertRaises(DataError):
            self.report()

    def test_cli_chay_rieng_khong_doc_anh_xa_khong_ghi_va_ma_thoat(self):
        config = self.root / "ket-noi.json"
        config.write_text(json.dumps({"admin_dsn": "DEMO_DSN_BI_MAT"}), encoding="utf-8")
        driver = MagicMock()
        driver.connect.return_value.__enter__.return_value = self.pg
        args = ["--nguon", str(self.source), "--dsn-tep", str(config), "--nguon-id", "DEMO-CD2", "--doi-chieu"]
        for changed in (False, True):
            if changed:
                self.pg.data["boq_dong"][0]["kl"] = Decimal(999)
            output = io.StringIO()
            with patch.dict("sys.modules", {"psycopg": driver}), redirect_stdout(output), \
                    patch.object(chuyen, "ghi_pg", side_effect=AssertionError("Không nạp")), \
                    patch.object(chuyen, "doc_anh_xa", side_effect=AssertionError("Không ánh xạ")), \
                    patch.object(chuyen, "doc_nguon", side_effect=AssertionError("Không đọc CD1")):
                code = chuyen.main(args)
            self.assertEqual(code, 2 if changed else 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report["trang_thai"], "DOI_CHIEU_LECH" if changed else "DOI_CHIEU_KHOP")
            for secret in (TEN_GIA, SO_HD, MA_HD, "DEMO_DSN_BI_MAT"):
                self.assertNotIn(secret, output.getvalue())
            output.getvalue().encode("ascii")

    def test_cli_nap_roi_doc_lai_doc_lap_va_thu_khong_mo_pg(self):
        config, mapping = self.root / "ket-noi.json", self.root / "anh-xa.csv"
        config.write_text(json.dumps({"admin_dsn": "DEMO_DSN_BI_MAT"}), encoding="utf-8")
        mapping.write_text("ma_hd,hop_dong_id,du_an_id\n" + MA_HD + "," + ",".join(MAPPING[MA_HD]) + "\n", encoding="utf-8")
        driver = MagicMock()
        driver.connect.return_value.__enter__.return_value = self.pg
        args = ["--nguon", str(self.source), "--dsn-tep", str(config), "--nguon-id", "DEMO-CD2", "--doi-chieu",
                "--anh-xa", str(mapping), "--chup-luc", CHUP]
        def loaded(*args, **kwargs):
            # Sai lệch được gây sau khi nạp, CD2 phải đọc đích thay vì tổng CD1.
            self.pg.data["boq_dong"][0]["thanh_tien_ghi"] += 1
            return {t: {"da_ghi_moi": len(rows), "da_co_dich": len(rows)} for t, rows in self.pg.data.items()}
        output = io.StringIO()
        with patch.dict("sys.modules", {"psycopg": driver}), redirect_stdout(output), \
                patch.object(chuyen, "ghi_pg", side_effect=loaded) as write:
            self.assertEqual(chuyen.main(args), 2)
        write.assert_called_once()
        self.assertEqual(json.loads(output.getvalue().splitlines()[-1])["trang_thai"], "DOI_CHIEU_LECH")
        driver.reset_mock()
        with patch.dict("sys.modules", {"psycopg": driver}), redirect_stdout(io.StringIO()):
            self.assertEqual(chuyen.main([*args, "--thu"]), 1)
        driver.connect.assert_not_called()

    def test_cli_loi_doi_chieu_khong_lo_traceback_hay_bi_mat(self):
        config = self.root / "ket-noi.json"
        config.write_text(json.dumps({"admin_dsn": "DEMO_DSN_BI_MAT"}), encoding="utf-8")
        driver = MagicMock()
        output, errors = io.StringIO(), io.StringIO()
        with patch.dict("sys.modules", {"psycopg": driver}), redirect_stdout(output), redirect_stderr(errors), \
                patch.object(chuyen, "doi_chieu", side_effect=RuntimeError(TEN_GIA + " DEMO_DSN_BI_MAT")):
            code = chuyen.main(["--nguon", str(self.source), "--dsn-tep", str(config), "--nguon-id", "DEMO-CD2", "--doi-chieu"])
        self.assertEqual(code, 1)
        for secret in (TEN_GIA, "DEMO_DSN_BI_MAT", "Traceback"):
            self.assertNotIn(secret, output.getvalue() + errors.getvalue())

    def test_cli_thong_bao_dung_giai_doan_va_hoan_tat_truoc_doi_chieu(self):
        config, mapping = self.root / "ket-noi.json", self.root / "anh-xa.csv"
        config.write_text(json.dumps({"admin_dsn": "DEMO_DSN_BI_MAT"}), encoding="utf-8")
        mapping.write_text("ma_hd,hop_dong_id,du_an_id\n" + MA_HD + "," + ",".join(MAPPING[MA_HD]) + "\n", encoding="utf-8")
        base = ["--nguon", str(self.source), "--dsn-tep", str(config), "--nguon-id", "DEMO-CD2", "--doi-chieu"]
        nap = [*base, "--anh-xa", str(mapping), "--chup-luc", CHUP]
        for phase, args in (("NAP", nap), ("DOI_CHIEU", nap), ("DOI_CHIEU", base)):
            output = io.StringIO()
            counts = {t: {"da_ghi_moi": len(rows), "da_co_dich": len(rows)} for t, rows in self.pg.data.items()}

            def fail_comparison(*args, **kwargs):
                if "--anh-xa" in current_args:
                    self.assertEqual(json.loads(output.getvalue().splitlines()[-1])["trang_thai"], "HOAN_TAT")
                raise RuntimeError(TEN_GIA)

            current_args = args
            with self.subTest(phase=phase, nap="--anh-xa" in args), \
                    patch.dict("sys.modules", {"psycopg": MagicMock()}), redirect_stdout(output), \
                    patch.object(chuyen, "ghi_pg", side_effect=RuntimeError(TEN_GIA) if phase == "NAP" else None,
                                 return_value=counts), \
                    patch.object(chuyen, "doi_chieu", side_effect=fail_comparison):
                self.assertEqual(chuyen.main(args), 1)
            reports = [json.loads(line) for line in output.getvalue().splitlines()]
            error = reports[-1]
            self.assertEqual(error["giai_doan"], phase)
            self.assertEqual(error["thong_bao"], "Nạp không hoàn tất; không ghi gì (đã hoàn tác)." if phase == "NAP" else
                             "Đối chiếu không hoàn tất; dữ liệu đã nạp vẫn được giữ.")
            self.assertEqual(sum(r.get("trang_thai") == "HOAN_TAT" for r in reports),
                             int(phase == "DOI_CHIEU" and "--anh-xa" in args))
            self.assertNotIn(TEN_GIA, output.getvalue())
            output.getvalue().encode("ascii")


@unittest.skipUnless(DSN and psycopg is not None, "Thiếu KHO_PG_DSN_TEST/psycopg — PG do lead chạy (NOT_RUN)")
class ChuyenReviewPGTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.ha_tang import postgres as pg
        cls.db = "kho_test_m4_cd1_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.dsn = conninfo.make_conninfo(DSN, dbname=cls.db)
        cls.con = psycopg.connect(cls.dsn, autocommit=True)
        cls.addClassCleanup(cls.con.close)
        pg.migrate(cls.con)
        cls.pn = cls.con.execute("INSERT INTO master.phap_nhan (ma,ten) VALUES ('DEMO_CD1','Pháp nhân DEMO CD1') RETURNING id").fetchone()[0]
        cls.da = cls.con.execute("INSERT INTO master.du_an (phap_nhan_id,ma_junsky,ten) VALUES (%s,'DEMO_CD1','Dự án DEMO CD1') RETURNING id", (cls.pn,)).fetchone()[0]

    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory(prefix="m4_cd1_pg_demo_"))
        self.source = Path(self.temp) / "DEMO.db"
        tao_demo(self.source)
        self.data, self.sha = chuyen.doc_nguon(self.source)
        code = "DEMO-CD1-" + uuid.uuid4().hex
        self.hd = self.con.execute("""INSERT INTO master.hop_dong
            (phap_nhan_id,du_an_id,loai,module_chu,ma_noi_bo,so_hop_dong,trang_thai)
            VALUES (%s,%s,'XAY_DUNG','M4',%s,%s,'SOAN_THAO') RETURNING id""", (self.pn, self.da, code, code)).fetchone()[0]
        self.con.execute("""INSERT INTO m4.ho_so_hop_dong (hop_dong_id,phap_nhan_id,du_an_id,ten,tao_boi)
            VALUES (%s,%s,%s,'DEMO CD1','MO_PHONG_DEMO')""", (self.hd, self.pn, self.da))
        self.mapping = {MA_HD: (str(self.hd), str(self.da))}
        self.nguon_id = code

    def ghi(self, data=None, **changes):
        args = dict(nguon_id=self.nguon_id, chup_luc=CHUP, sha256_nguon=self.sha)
        args.update(changes)
        return chuyen.ghi_pg(self.con, self.data if data is None else data, self.mapping, **args)

    def counts(self):
        result = {t: self.con.execute(f"SELECT count(*) FROM m4.review_chep_{t} WHERE nguon_id=%s", (self.nguon_id,)).fetchone()[0]
                  for t in chuyen.BANG_NGUON}
        result["nguon"] = self.con.execute("SELECT count(*) FROM m4.review_chep_nguon WHERE id=%s", (self.nguon_id,)).fetchone()[0]
        return result

    def test_nap_du_12_bang_so_dem_khop_va_tong_giu_nguyen(self):
        report = self.ghi()
        for t, rows in self.data.items():
            self.assertEqual(report[t], {"da_ghi_moi": len(rows), "da_co_dich": len(rows)})
        actual = {}
        for t in chuyen.BANG_NGUON:
            cursor = self.con.execute(f"SELECT {','.join(chuyen.COT[t])} FROM m4.review_chep_{t} WHERE nguon_id=%s", (self.nguon_id,))
            actual[t] = [dict(zip(chuyen.COT[t], r)) for r in cursor.fetchall()]
        self.assertEqual(chuyen.tong_kiem_soat(actual), chuyen.tong_kiem_soat(self.data))
        self.assertEqual(chuyen.sha256_tep(self.source), self.sha)

    def test_cd2_nap_xong_doi_chieu_doc_lap_khop(self):
        self.ghi()
        report = dc.doi_chieu(self.source, self.con, nguon_id=self.nguon_id)
        self.assertTrue(report["khop"])
        self.assertEqual(report["so_dong_loi"], 0)
        self.assertEqual(report["tong_sqlite"], report["tong_pg"])
        raw = json.dumps(report, ensure_ascii=True)
        for secret in (TEN_GIA, SO_HD, MA_HD):
            self.assertNotIn(secret, raw)

    def gan_canh_bao_sai_trong_csdl_test(self, row_id, hd):
        # Fixture hỏng có chủ đích: chỉ trong kho_test_* tự tạo. FK/append-only
        # bình thường chặn UPDATE; replica chỉ hiệu lực trong transaction này.
        self.assertTrue(self.db.startswith("kho_test_"))
        with self.con.transaction():
            self.con.execute("SET LOCAL session_replication_role = replica")
            self.con.execute("UPDATE m4.review_chep_canh_bao SET hop_dong_id=%s,du_an_id=%s WHERE nguon_id=%s AND id=%s",
                             (hd, self.da, self.nguon_id, row_id))

    def test_cd2_canh_bao_mo_coi_bi_gan_hd(self):
        with closing(sqlite3.connect(self.source)) as con:
            con.execute("INSERT INTO canh_bao(id,ma_hd) VALUES(3,'DEMO_HD_DA_XOA')")
            con.commit()
        self.data, self.sha = chuyen.doc_nguon(self.source)
        self.ghi()
        self.gan_canh_bao_sai_trong_csdl_test(3, self.hd)
        report = dc.doi_chieu(self.source, self.con, nguon_id=self.nguon_id)
        self.assertFalse(report["khop"])
        self.assertTrue(report["sha256_khop"])
        self.assertEqual([(r["bang"], r["ma_loi"]) for r in report["dong_loi"]], [("canh_bao", "GAN_HD_SAI")])
        self.assertEqual(report["bang"]["canh_bao"]["so_dong_mo_coi"], {"sqlite": 2, "pg": 1})

    def test_cd2_canh_bao_gan_nham_hd_khac_cung_lan_chup(self):
        second = "DEMO_HD_THU_HAI"
        code = "DEMO-CD2b-" + uuid.uuid4().hex
        hd2 = self.con.execute("""INSERT INTO master.hop_dong
            (phap_nhan_id,du_an_id,loai,module_chu,ma_noi_bo,so_hop_dong,trang_thai)
            VALUES (%s,%s,'XAY_DUNG','M4',%s,%s,'SOAN_THAO') RETURNING id""",
                               (self.pn, self.da, code, code)).fetchone()[0]
        self.con.execute("""INSERT INTO m4.ho_so_hop_dong (hop_dong_id,phap_nhan_id,du_an_id,ten,tao_boi)
            VALUES (%s,%s,%s,'DEMO CD2b','MO_PHONG_DEMO')""", (hd2, self.pn, self.da))
        with closing(sqlite3.connect(self.source)) as con:
            con.execute("INSERT INTO hop_dong(ma_hd,so_hd) VALUES(?,?)", (second, second))
            con.commit()
        self.mapping[second] = (str(hd2), str(self.da))
        self.data, self.sha = chuyen.doc_nguon(self.source)
        self.ghi()
        self.gan_canh_bao_sai_trong_csdl_test(1, hd2)
        report = dc.doi_chieu(self.source, self.con, nguon_id=self.nguon_id)
        self.assertFalse(report["khop"])
        self.assertTrue(report["sha256_khop"])
        self.assertEqual([(r["bang"], r["ma_loi"]) for r in report["dong_loi"]], [("canh_bao", "GAN_HD_SAI")])

    def test_cd2_sha_khac_metadata_du_tung_o_khop(self):
        self.ghi(sha256_nguon="0" * 64)
        report = dc.doi_chieu(self.source, self.con, nguon_id=self.nguon_id)
        self.assertFalse(report["sha256_khop"])
        self.assertFalse(report["khop"])
        self.assertEqual(report["so_dong_loi"], 0)
        self.assertEqual(report["tong_sqlite"], report["tong_pg"])

    def test_cd2_cli_loi_doi_chieu_da_in_hoan_tat_va_giu_du_lieu(self):
        config, mapping = Path(self.temp) / "ket-noi.json", Path(self.temp) / "anh-xa.csv"
        config.write_text(json.dumps({"admin_dsn": self.dsn}), encoding="utf-8")
        mapping.write_text("ma_hd,hop_dong_id,du_an_id\n" + MA_HD + "," + ",".join(self.mapping[MA_HD]) + "\n", encoding="utf-8")
        output = io.StringIO()

        def fail_comparison(*args, **kwargs):
            self.assertEqual(json.loads(output.getvalue().splitlines()[-1])["trang_thai"], "HOAN_TAT")
            self.assertEqual(self.counts(), {**{t: len(rows) for t, rows in self.data.items()}, "nguon": 1})
            raise RuntimeError(TEN_GIA)

        with redirect_stdout(output), patch.object(chuyen, "doi_chieu", side_effect=fail_comparison):
            code = chuyen.main(["--nguon", str(self.source), "--dsn-tep", str(config), "--nguon-id", self.nguon_id,
                                "--anh-xa", str(mapping), "--chup-luc", CHUP, "--doi-chieu"])
        self.assertEqual(code, 1)
        reports = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([r.get("trang_thai") for r in reports], [None, "HOAN_TAT", "LOI"])
        self.assertEqual(reports[-1]["giai_doan"], "DOI_CHIEU")
        self.assertEqual(self.counts(), {**{t: len(rows) for t, rows in self.data.items()}, "nguon": 1})
        self.assertTrue(dc.doi_chieu(self.source, self.con, nguon_id=self.nguon_id)["khop"])
        self.assertNotIn(TEN_GIA, output.getvalue())

    def test_cd2_nguon_khac_boq_phat_hien_dung_hd(self):
        self.ghi()
        # Đích append-only; dùng nguồn giả khác sau nạp, không tắt trigger PG.
        with closing(sqlite3.connect(self.source)) as con:
            con.execute("UPDATE boq_dong SET thanh_tien_ghi=thanh_tien_ghi+1 WHERE id=1")
            con.commit()
        report = dc.doi_chieu(self.source, self.con, nguon_id=self.nguon_id)
        self.assertFalse(report["khop"])
        self.assertEqual(report["dong_loi"][0]["bang"], "boq_dong")
        self.assertEqual(report["dong_loi"][0]["khoa"], "HD0001")

    def test_cd2_hai_lech_triet_tieu_tung_hd_va_dot(self):
        second = "ZZ_DEMO_CD2_BI_MAT"
        with closing(sqlite3.connect(self.source)) as con:
            con.execute("INSERT INTO hop_dong(ma_hd,so_hd,gia_tri_hd) VALUES(?,?,100)", (second, second))
            con.execute("INSERT INTO boq_dong(id,ma_hd,ma_hm,thao_tac,kl,don_gia,thanh_tien_ghi) VALUES(9,?,'HM2','GOC',1,100,100)", (second,))
            con.commit()
        master_code = "DEMO-CD2-" + uuid.uuid4().hex
        hd2 = self.con.execute("""INSERT INTO master.hop_dong
            (phap_nhan_id,du_an_id,loai,module_chu,ma_noi_bo,so_hop_dong,trang_thai)
            VALUES (%s,%s,'XAY_DUNG','M4',%s,%s,'SOAN_THAO') RETURNING id""",
                               (self.pn, self.da, master_code, master_code)).fetchone()[0]
        self.con.execute("""INSERT INTO m4.ho_so_hop_dong (hop_dong_id,phap_nhan_id,du_an_id,ten,tao_boi)
            VALUES (%s,%s,%s,'DEMO CD2','MO_PHONG_DEMO')""", (hd2, self.pn, self.da))
        self.mapping[second] = (str(hd2), str(self.da))
        self.data, self.sha = chuyen.doc_nguon(self.source)
        self.ghi()
        with closing(sqlite3.connect(self.source)) as con:
            con.execute("UPDATE hop_dong SET gia_tri_hd=gia_tri_hd+10 WHERE ma_hd=?", (MA_HD,))
            con.execute("UPDATE hop_dong SET gia_tri_hd=gia_tri_hd-10 WHERE ma_hd=?", (second,))
            con.execute("UPDATE boq_dong SET thanh_tien_ghi=thanh_tien_ghi+10 WHERE id=1")
            con.execute("UPDATE boq_dong SET thanh_tien_ghi=thanh_tien_ghi-10 WHERE id=9")
            con.execute("UPDATE dot_thanh_toan SET gt_ky=gt_ky+10 WHERE dot=1")
            con.execute("UPDATE dot_thanh_toan SET gt_ky=gt_ky-10 WHERE dot=2")
            con.commit()
        report = dc.doi_chieu(self.source, self.con, nguon_id=self.nguon_id)
        self.assertFalse(report["khop"])
        self.assertEqual(report["so_dong_loi"], 6)
        self.assertEqual(report["tong_sqlite"]["gia_tri_hd"], report["tong_pg"]["gia_tri_hd"])
        self.assertEqual({r["khoa"] for r in report["dong_loi"]}, {"HD0001", "HD0002"})
        for side in ("tong_sqlite", "tong_pg"):
            self.assertEqual(sum(Decimal(h["boq"]["GOC"]["thanh_tien_ghi"]["tong"]) for h in report[side]["tung_hd"]), Decimal("350.3"))
            self.assertEqual(sum(Decimal(d["gt_ky"]["tong"]) for d in report[side]["tung_dot"]), Decimal("300.375"))
        for secret in (TEN_GIA, SO_HD, MA_HD, second):
            self.assertNotIn(secret, json.dumps(report))

    def test_replay_khong_tang_dong_hay_doi_id(self):
        self.ghi()
        before = self.counts()
        ids = self.con.execute("SELECT chep_id FROM m4.review_chep_boq_dong WHERE nguon_id=%s ORDER BY id", (self.nguon_id,)).fetchall()
        report = self.ghi({t: list(reversed(rows)) for t, rows in self.data.items()})
        self.assertEqual(self.counts(), before)
        self.assertEqual({r["da_ghi_moi"] for r in report.values()}, {0})
        self.assertEqual(self.con.execute("SELECT chep_id FROM m4.review_chep_boq_dong WHERE nguon_id=%s ORDER BY id", (self.nguon_id,)).fetchall(), ids)

    def test_replay_doi_chup_luc_dung(self):
        self.ghi()
        before = self.counts()
        with self.assertRaises(DataError) as caught:
            self.ghi(chup_luc="2026-10-27T07:00:00+07:00")
        self.assertEqual(caught.exception.code, "M4_REVIEW_REPLAY_KHAC")
        self.assertEqual(self.counts(), before)

    def test_replay_doi_du_lieu_ke_ca_5_bang_con_lai_dung(self):
        self.ghi()
        before = self.counts()
        for t in chuyen.BANG_NGUON:
            data = copy.deepcopy(self.data)
            # Bớt một dòng ở mọi bảng: phải đối chiếu cả tập khóa, kể cả rỗng.
            # Bảng có con sẽ bị preflight FK chặn trước, vẫn không ghi gì.
            data[t].pop()
            with self.subTest(table=t), self.assertRaises(DataError):
                self.ghi(data)
            self.assertEqual(self.counts(), before)
        data = copy.deepcopy(self.data)
        data["nhat_ky"][0]["chi_tiet"] = "DEMO thay đổi"
        with self.assertRaises(DataError) as caught:
            self.ghi(data)
        self.assertEqual(caught.exception.code, "M4_REVIEW_REPLAY_KHAC")
        self.assertEqual(self.counts(), before)

    def test_loi_giua_chung_rollback_ca_12_bang_va_nguon(self):
        real = chuyen._ghi_con_lai

        def fail_after_remaining(*args, **kwargs):
            real(*args, **kwargs)
            raise RuntimeError("DEMO lỗi sau bảng cuối")

        with patch.object(chuyen, "_ghi_con_lai", side_effect=fail_after_remaining), self.assertRaises(RuntimeError):
            self.ghi()
        self.assertEqual(set(self.counts().values()), {0})
        self.ghi()
        self.assertEqual(self.counts()["nguon"], 1)

    def test_sha_doi_truoc_commit_rollback_ca_lan_chup(self):
        with self.source.open("ab") as stream:
            stream.write(b"DEMO changed")
        with self.assertRaises(DataError):
            self.ghi(truoc_commit=lambda: chuyen.kiem_sha(self.source, self.sha))
        self.assertEqual(set(self.counts().values()), {0})


if __name__ == "__main__":
    unittest.main()
