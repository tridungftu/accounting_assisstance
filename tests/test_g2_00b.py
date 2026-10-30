"""G2-00b: chẩn đoán migration an toàn; PG chỉ chạy khi lead cấp DSN test.

Không khởi động/dừng dịch vụ, không DROP; DB kho_test_* giữ cho lead dọn.
"""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import traceback
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import doi_cau_truc as dc

try:
    from .test_g2_01 import _kiem_dich_test, psycopg
except ImportError:
    from test_g2_01 import _kiem_dich_test, psycopg

if psycopg is not None:
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict

ADMIN_DSN = os.environ.get('KHO_PG_DSN_TEST')
CANARY = 'CANARY_G200B_BI_MAT'
TEP = [Path('001_demo.sql'), Path('012_danh_muc.sql'), Path('013_lien_ket.sql')]


class LoiDriverGia(RuntimeError):
    def __init__(self, sqlstate='42601', context=None, primary=None):
        super().__init__(f'postgresql://user:{CANARY}@localhost/kho_test_demo')
        self.sqlstate = sqlstate
        self.diag = SimpleNamespace(context=context, message_primary=primary,
                                    message_detail=CANARY)


class ChanDoanThuanTest(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.cur = self.conn.cursor.return_value.__enter__.return_value
        self.cur.fetchone.side_effect = [('kho_test_g2_00b_mock',),
                                        ('loi.lich_su_doi_cau_truc',)]
        self.cur.fetchall.return_value = []

    def _bat(self, driver, *, so=12, tep=TEP, luc=None):
        def execute(cau_sql, *args):
            if cau_sql == f'SELECT {so}' or (luc and cau_sql.startswith(luc)):
                raise driver

        self.cur.execute.side_effect = execute
        noi_dung = [f'SELECT {int(p.name[:3])}'.encode() for p in tep]
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            with patch.object(Path, 'read_bytes', side_effect=noi_dung):
                with self.assertRaises(dc.LoiDoiCauTruc) as bat:
                    dc.ap_doi_cau_truc(self.conn, iter(tep))
        self.assertEqual(out.getvalue() + err.getvalue(), '')
        exc = bat.exception
        self.assertTrue(str(exc).startswith('DOI_CAU_TRUC_THAT_BAI'))
        self.assertEqual(exc.ma, 'DOI_CAU_TRUC_THAT_BAI')
        self.assertIsNone(exc.__context__)
        self.assertIsNone(exc.__cause__)
        hien = (str(exc) + repr(exc) + repr(vars(exc))
                + ''.join(traceback.format_exception(exc)))
        self.assertNotIn(CANARY, hien)
        for marker in ('postgresql://', 'postgres://', 'password=', 'host='):
            self.assertNotIn(marker, hien.lower())
        return exc

    def test_lop_42_co_vi_tri_sqlstate_context_va_primary(self):
        exc = self._bat(LoiDriverGia(
            context=f'PL/pgSQL function {CANARY}(text) line 17 at SQL statement',
            primary=f'syntax error at or near "{CANARY}"'))
        self.assertEqual((exc.so_phien_ban, exc.ten_tep, exc.sqlstate),
                         (12, '012_danh_muc.sql', '42601'))
        self.assertEqual(exc.context, 'PL/pgSQL function [DA_LOC] line 17 at SQL statement')
        self.assertEqual(exc.message_primary, 'syntax error at or near [DA_LOC]')
        for gia_tri in ('012_danh_muc.sql', '42601', 'line 17'):
            self.assertIn(gia_tri, str(exc))
        # Transaction thoát bằng lỗi driver, không nuốt lỗi rồi commit một phần.
        thoat = self.conn.transaction.return_value.__exit__.call_args.args
        self.assertIs(thoat[0], LoiDriverGia)
        self.conn.commit.assert_not_called()

    def test_dung_tep_dang_ap_va_chi_giu_basename(self):
        tep = [Path(CANARY) / p for p in TEP]
        exc = self._bat(LoiDriverGia(), so=13, tep=tep)
        self.assertEqual((exc.so_phien_ban, exc.ten_tep), (13, '013_lien_ket.sql'))

    def test_ngoai_lop_42_chi_giu_sqlstate_va_vi_tri(self):
        for state in ('23505', '22P02', 'P0001', '28000', '08006'):
            with self.subTest(state=state):
                self.setUp()
                exc = self._bat(LoiDriverGia(
                    sqlstate=state, context='PL/pgSQL function demo() line 2 at RAISE',
                    primary='syntax error at end of input'))
                self.assertEqual(exc.sqlstate, state)
                self.assertEqual(exc.so_phien_ban, 12)
                self.assertIsNone(exc.context)
                self.assertIsNone(exc.message_primary)

    def test_sqlstate_thieu_sai_kieu_hoac_chua_bi_mat(self):
        for state in (None, '', 42601, object(), CANARY, '42\n01', '42abc',
                      f'42601 password={CANARY}'):
            with self.subTest(state=type(state).__name__):
                self.setUp()
                exc = self._bat(LoiDriverGia(
                    sqlstate=state, context=CANARY, primary=CANARY))
                self.assertIsNone(exc.sqlstate)
                self.assertIsNone(exc.context)
                self.assertIsNone(exc.message_primary)

    def test_loc_dsn_password_host_khong_phan_biet_hoa_thuong(self):
        for bi_mat in (f'postgresql://demo:{CANARY}@localhost/db',
                       f'POSTGRES://demo:{CANARY}@localhost/db',
                       f'password={CANARY}', f'PASSWORD = "{CANARY}"',
                       f'host={CANARY}', f'HoSt\n= {CANARY}'):
            with self.subTest(bi_mat=bi_mat):
                self.setUp()
                exc = self._bat(LoiDriverGia(
                    context=f'PL/pgSQL function {bi_mat} line 3 at SQL statement',
                    primary=f'syntax error at or near "{bi_mat}"'))
                self.assertEqual(exc.context, '[DA_LOC]')
                self.assertEqual(exc.message_primary, '[DA_LOC]')

    def test_context_khong_giu_sql_bind_hoac_van_ban_tu_do(self):
        exc = self._bat(LoiDriverGia(context=(
            f'SQL statement "SELECT {CANARY}"\n'
            f'unnamed portal parameter $1 = \'{CANARY}\'\n'
            f'PL/pgSQL function {CANARY}(text) line 7 at EXECUTE\n'
            f'compilation of PL/pgSQL function {CANARY} near line 9\n'
            f'{CANARY}'), primary=CANARY))
        self.assertEqual(exc.context, 'PL/pgSQL function [DA_LOC] line 7 at EXECUTE\n'
                         'compilation of PL/pgSQL function [DA_LOC] near line 9')
        self.assertEqual(exc.message_primary, '[DA_LOC]')

    def test_primary_khong_giu_token_dinh_danh_hoac_tham_so(self):
        cac_mau = (
            (f'syntax error at or near "{CANARY}"', 'syntax error at or near [DA_LOC]'),
            (f'syntax error at or near {CANARY}', 'syntax error at or near [DA_LOC]'),
            (f'unterminated dollar-quoted string at or near $$\n{CANARY}',
             'unterminated dollar-quoted string at or near [DA_LOC]'),
            (f'relation "{CANARY}" does not exist', 'relation [DA_LOC] does not exist'),
            (f'function demo({CANARY}) does not exist', 'function [DA_LOC] does not exist'),
            (f'column "{CANARY}" is ambiguous', 'column [DA_LOC] is ambiguous'),
            (f'custom error {CANARY}', '[DA_LOC]'),
        )
        for primary, mong_doi in cac_mau:
            with self.subTest(primary=primary):
                self.setUp()
                self.assertEqual(self._bat(LoiDriverGia(primary=primary)).message_primary,
                                 mong_doi)

    def test_thong_bao_co_dinh_an_toan_duoc_giu(self):
        exc = self._bat(LoiDriverGia(primary='syntax error at end of input'))
        self.assertEqual(exc.message_primary, 'syntax error at end of input')

    def test_diag_thieu_hoac_sai_kieu_khong_goi_str(self):
        for diag in (None, object(), SimpleNamespace(context=object(), message_primary=object())):
            with self.subTest(diag=type(diag).__name__):
                self.setUp()
                driver = LoiDriverGia()
                driver.diag = diag
                exc = self._bat(driver)
                self.assertEqual(exc.sqlstate, '42601')
                self.assertIsNone(exc.context)
                self.assertIsNone(exc.message_primary)

    def test_property_diag_loi_khong_lam_mat_sqlstate(self):
        class DriverPropertyLoi(RuntimeError):
            sqlstate = '42601'

            @property
            def diag(self):
                raise RuntimeError(CANARY)

        exc = self._bat(DriverPropertyLoi(CANARY))
        self.assertEqual(exc.sqlstate, '42601')
        self.assertIsNone(exc.context)

    def test_driver_khong_co_chan_doan_van_co_ten_tep(self):
        exc = self._bat(RuntimeError(CANARY))
        self.assertEqual(exc.ten_tep, '012_danh_muc.sql')
        self.assertIsNone(exc.sqlstate)

    def test_loi_truoc_ddl_khong_gan_nham_tep(self):
        exc = self._bat(LoiDriverGia(), luc='SELECT current_database')
        self.assertEqual(str(exc), 'DOI_CAU_TRUC_THAT_BAI')
        self.assertIsNone(exc.so_phien_ban)
        self.assertIsNone(exc.ten_tep)

    def test_loi_luc_thoat_transaction_khong_gan_nham_tep_cu(self):
        self.conn.transaction.return_value.__exit__.side_effect = LoiDriverGia()
        exc = self._bat(LoiDriverGia(), so=999)
        self.assertEqual(str(exc), 'DOI_CAU_TRUC_THAT_BAI')
        self.assertIsNone(exc.ten_tep)

    def test_loi_ghi_so_giu_vi_tri_tep(self):
        exc = self._bat(LoiDriverGia(sqlstate='23505'), luc='INSERT INTO')
        self.assertEqual((exc.so_phien_ban, exc.ten_tep), (1, '001_demo.sql'))
        self.assertEqual(exc.sqlstate, '23505')

    def test_ma_loi_nghiep_vu_khong_doi(self):
        self.cur.fetchone.side_effect = [('kho_that',)]
        with patch.object(Path, 'read_bytes', return_value=b'SELECT 1'):
            with self.assertRaises(dc.LoiDoiCauTruc) as bat:
                dc.ap_doi_cau_truc(self.conn, TEP)
        self.assertEqual(str(bat.exception), 'DICH_KHONG_AN_TOAN')
        self.assertIsNone(bat.exception.__context__)
        self.assertIsNone(bat.exception.__cause__)


@unittest.skipUnless(psycopg is not None and ADMIN_DSN,
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class ChanDoanPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        thong_tin = _kiem_dich_test(conninfo_to_dict(ADMIN_DSN))
        admin = psycopg.connect(**thong_tin, autocommit=True)
        cls.addClassCleanup(admin.close)
        db = 'kho_test_g2_00b_' + uuid4().hex[:12]
        admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(db)))
        cls.conn = psycopg.connect(**{**thong_tin, 'dbname': db}, autocommit=True)
        cls.addClassCleanup(cls.conn.close)
        cls.conn.execute('SET log_parameter_max_length = 0')
        cls.conn.execute('SET log_parameter_max_length_on_error = 0')
        # Chỉ runner provisioning; không có ca nghiệp vụ đóng giả runtime/owner.
        cls.conn.execute('CREATE SCHEMA loi')
        cls.conn.execute('''CREATE TABLE loi.lich_su_doi_cau_truc (
            ma_goi text, so_phien_ban integer, ma_bam text, nguon_lich_su jsonb)''')

    def test_sql_sai_co_tep_42601_va_rollback_ca_so_ddl(self):
        noi_dung = [b'CREATE TABLE loi.g200b_rollback(id integer)', b'SELEC 1']
        with patch.object(Path, 'read_bytes', side_effect=noi_dung):
            with self.assertRaises(dc.LoiDoiCauTruc) as bat:
                dc.ap_doi_cau_truc(self.conn, TEP[:2])
        exc = bat.exception
        self.assertEqual((exc.so_phien_ban, exc.ten_tep, exc.sqlstate),
                         (12, '012_danh_muc.sql', '42601'))
        self.assertIn('012_danh_muc.sql', str(exc))
        self.assertIn('42601', str(exc))
        self.assertIsNone(exc.__context__)
        self.assertIsNone(exc.__cause__)
        self.assertIsNone(self.conn.execute("SELECT to_regclass('loi.g200b_rollback')").fetchone()[0])
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.lich_su_doi_cau_truc').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
