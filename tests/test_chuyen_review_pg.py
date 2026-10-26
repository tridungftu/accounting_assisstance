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
from contextlib import closing, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from kho_tri_thuc.ha_tang.primitives import DataError
from tools import chuyen_review_sqlite_sang_pg as chuyen

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

        def warning(*args, **kwargs):
            logging.getLogger("psycopg").warning("DETAIL: BI_MAT_DEMO_456")
            logging.getLogger("psycopg.connection").warning("DETAIL: BI_MAT_DEMO_456")
            return {}

        errors = io.StringIO()
        with patch.dict("sys.modules", {"psycopg": driver}), \
                patch.object(chuyen, "ghi_pg", side_effect=warning), redirect_stderr(errors):
            code, _, _ = self.run_cli()
        self.assertEqual(code, 0)
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
        args = dict(nguon_id=self.nguon_id, chup_luc=CHUP)
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
