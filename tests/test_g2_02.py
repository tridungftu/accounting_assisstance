"""G2-02: test thuần và PG16 qua login thật, không khởi động dịch vụ.

RLS hiện đóng chờ contract G2-03; không giả actor/GUC hoặc owner để làm xanh
ca nghiệp vụ. Các ca tạo/duy nhất hợp lệ còn CHUA_KIEM, cần lead tích hợp phiên.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import os
import secrets
import sys
import unittest
from unittest.mock import Mock
from uuid import uuid4


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import danh_tinh

try:
    from .test_g2_01 import _kiem_dich_test, CAC_VAI, SQL_VAI, psycopg
except ImportError:
    from test_g2_01 import _kiem_dich_test, CAC_VAI, SQL_VAI, psycopg

if psycopg is not None:
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict


SQL_DANH_TINH = (Path(__file__).resolve().parents[1]
                / 'src/kho_tri_thuc/core/sql/002_danh_tinh.sql').read_text(encoding='utf-8')
ADMIN_DSN = os.environ.get('KHO_PG_DSN_TEST')
CAC_BANG = ('nguoi_dung', 'phap_nhan', 'phap_nhan_boi_canh',
            'phan_quyen', 'vai_nghiep_vu')


class DanhTinhThuanTest(unittest.TestCase):
    def setUp(self):
        # spec không có commit/rollback/connect: hàm không được tự quản kết nối.
        self.ket_noi = Mock(spec=['execute'])
        self.nd, self.pn, self.tv = uuid4(), uuid4(), uuid4()

    def _tra(self, dong):
        self.ket_noi.execute.return_value.fetchone.return_value = dong

    def test_tao_nguoi_dung_bind_du_lieu_khong_noi_sql(self):
        ten = "DEMO '); SELECT 1; --"
        dong = (self.nd, 'demo_g202', ten, 'BAN_HANG', 'HOAT_DONG', False)
        self._tra(dong)
        ket_qua = danh_tinh.tao_nguoi_dung(
            self.ket_noi, dang_nhap='demo_g202', ten=ten, vai_tro='BAN_HANG')
        cau_sql, tham_so = self.ket_noi.execute.call_args.args
        self.assertNotIn(ten, cau_sql)
        self.assertEqual(tham_so, ('demo_g202', ten, 'BAN_HANG', False))
        self.assertEqual(ket_qua, danh_tinh.NguoiDung(*dong))
        with self.assertRaises(FrozenInstanceError):
            ket_qua.ten = 'khac'

    def test_giu_du_bay_vai_tro_cuoi(self):
        for vai_tro in danh_tinh.CAC_VAI_TRO:
            with self.subTest(vai_tro=vai_tro):
                self._tra((self.nd, 'demo_g202', 'DEMO', vai_tro, 'HOAT_DONG', False))
                danh_tinh.tao_nguoi_dung(self.ket_noi, dang_nhap='demo_g202',
                                       ten='DEMO', vai_tro=vai_tro)
        self.assertEqual(len(danh_tinh.CAC_VAI_TRO), 7)

    def test_tu_choi_nguoi_dung_sai_truoc_sql(self):
        cac_loi = ({'dang_nhap': ''}, {'ten': ' '}, {'vai_tro': 'ADMIN'},
                   {'vai_tro': []}, {'mo_phong': 1}, {'mo_phong': True})
        for loi in cac_loi:
            with self.subTest(loi=loi), self.assertRaises(ValueError):
                danh_tinh.tao_nguoi_dung(self.ket_noi, **{
                    'dang_nhap': 'demo_g202', 'ten': 'DEMO', **loi})
        self.ket_noi.execute.assert_not_called()

    def test_mo_phong_duoc_luu_nhung_khong_phai_xac_thuc(self):
        dong = (self.nd, 'MO_PHONG_DEMO', 'DEMO', 'XEM', 'HOAT_DONG', True)
        self._tra(dong)
        tao = danh_tinh.tao_nguoi_dung(self.ket_noi, dang_nhap=dong[1],
                                      ten='DEMO', mo_phong=True)
        tra = danh_tinh.tra_nguoi_dung(self.ket_noi, dang_nhap=dong[1])
        self.assertEqual(tao, tra)
        self.assertTrue(tra.mo_phong)

    def test_tao_va_tra_phap_nhan_giu_mst_co_so_khong_dau(self):
        dong = (self.pn, 'DEMO_02', 'Pháp nhân DEMO', '0012345678', 'HOAT_DONG')
        self._tra(dong)
        tao = danh_tinh.tao_phap_nhan(self.ket_noi, ma=dong[1], ten=dong[2], mst=dong[3])
        self.assertEqual(self.ket_noi.execute.call_args.args[1], dong[1:4])
        tra = danh_tinh.tra_phap_nhan(self.ket_noi, phap_nhan_id=str(self.pn))
        self.assertEqual(self.ket_noi.execute.call_args.args[1], (self.pn,))
        self.assertEqual(tao, tra)
        self.assertEqual(tra.mst, '0012345678')

    def test_phap_nhan_sai_khong_goi_sql(self):
        for loi in ({'ma': ''}, {'ten': None}, {'mst': 123}):
            with self.subTest(loi=loi), self.assertRaises(ValueError):
                danh_tinh.tao_phap_nhan(self.ket_noi, **{
                    'ma': 'DEMO', 'ten': 'DEMO', **loi})
        with self.assertRaises(ValueError):
            danh_tinh.tra_phap_nhan(self.ket_noi, phap_nhan_id='khong-phai-uuid')
        self.ket_noi.execute.assert_not_called()

    def test_thanh_vien_chi_ghi_phan_quyen_va_doc_view(self):
        dong = (self.tv, self.nd, self.pn, ['KIEM_TRA'], ['CRM'])
        self._tra(dong)
        tao = danh_tinh.tao_thanh_vien(self.ket_noi, nguoi_dung_id=self.nd,
                                      phap_nhan_id=self.pn,
                                      duyet_loai_viec=['KIEM_TRA'], module=['CRM'])
        cau_sql, tham_so = self.ket_noi.execute.call_args.args
        self.assertIn('INSERT INTO loi.phan_quyen', cau_sql)
        self.assertEqual(tham_so, (self.nd, self.pn, ['KIEM_TRA'], ['CRM']))
        tra = danh_tinh.tra_thanh_vien(self.ket_noi, nguoi_dung_id=self.nd,
                                      phap_nhan_id=self.pn)
        self.assertIn('FROM loi.thanh_vien', self.ket_noi.execute.call_args.args[0])
        self.assertEqual(tao, tra)
        self.assertEqual(tra.module, ('CRM',))
        self.assertEqual(tra.duyet_loai_viec, ('KIEM_TRA',))

    def test_thanh_vien_danh_sach_sai_khong_goi_sql(self):
        for loi in ({'module': 'CRM'}, {'module': [None]},
                    {'duyet_loai_viec': None}, {'duyet_loai_viec': [' ']}):
            with self.subTest(loi=loi), self.assertRaises(ValueError):
                danh_tinh.tao_thanh_vien(self.ket_noi, nguoi_dung_id=self.nd,
                                        phap_nhan_id=self.pn, **loi)
        self.ket_noi.execute.assert_not_called()

    def test_tra_khong_tim_thay_tra_none(self):
        self._tra(None)
        self.assertIsNone(danh_tinh.tra_nguoi_dung(self.ket_noi, dang_nhap='demo_g202'))
        self.assertIsNone(danh_tinh.tra_phap_nhan(self.ket_noi, phap_nhan_id=self.pn))
        self.assertIsNone(danh_tinh.tra_thanh_vien(
            self.ket_noi, nguoi_dung_id=self.nd, phap_nhan_id=self.pn))

    def test_loi_csdl_truyen_len_caller_khong_nuot_loi_hay_retry(self):
        loi = RuntimeError('LOI_CSDL_DEMO')
        self.ket_noi.execute.side_effect = loi
        with self.assertRaises(RuntimeError) as bat:
            danh_tinh.tao_phap_nhan(self.ket_noi, ma='DEMO', ten='DEMO')
        self.assertIs(bat.exception, loi)
        self.assertEqual(self.ket_noi.execute.call_count, 1)

    def test_khong_nhan_actor_client(self):
        with self.assertRaises(TypeError):
            danh_tinh.tao_phap_nhan(self.ket_noi, ma='DEMO', ten='DEMO', actor=self.nd)
        with self.assertRaises(TypeError):
            danh_tinh.tao_thanh_vien(self.ket_noi, nguoi_dung_id=self.nd,
                                    phap_nhan_id=self.pn, actor=self.nd)
        self.ket_noi.execute.assert_not_called()


@unittest.skipUnless(psycopg is not None and ADMIN_DSN,
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class DanhTinhPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.thong_tin = _kiem_dich_test(conninfo_to_dict(ADMIN_DSN))
        cls.admin = psycopg.connect(**cls.thong_tin, autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        if cls.admin.info.server_version < 160000:
            raise RuntimeError('Cần PostgreSQL 16+')
        if not cls.admin.execute(
            'SELECT rolsuper FROM pg_roles WHERE rolname=current_user'
        ).fetchone()[0]:
            raise RuntimeError('Cần lead cấp admin provisioning cho test')
        ma_lan = uuid4().hex[:12]
        cls.db = 'kho_test_g2_02_' + ma_lan
        cls.tien_to = 'ktt_test_g202_' + ma_lan + '_'
        cls.login = cls.tien_to + 'dang_nhap_loi'
        cls.chu = cls.tien_to + 'vai_doi_cau_truc_loi'
        cls.chay = cls.tien_to + 'vai_chay_loi'
        cls.cac_vai = [cls.tien_to + ten for ten in CAC_VAI]
        cls.admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(
            sql.Identifier(cls.db)))
        cls.addClassCleanup(cls._don_tai_nguyen)
        cls.conn = psycopg.connect(**{**cls.thong_tin, 'dbname': cls.db}, autocommit=True)
        cls.addClassCleanup(cls.conn.close)
        cls.conn.execute('SELECT set_config(%s, %s, false)',
                         ('kho_tri_thuc.tien_to_vai', cls.tien_to))
        with cls.conn.transaction():
            cls.conn.execute(SQL_VAI)
            cls.conn.execute(SQL_DANH_TINH)
        # Admin chỉ nạp fixture tổng hợp để kiểm có dữ liệu bị che; không dùng
        # hàm nghiệp vụ hoặc SET ROLE owner để thay cho các ca LOGIN thật.
        cls.nd_fixture, cls.pn_a, cls.pn_b = uuid4(), uuid4(), uuid4()
        with cls.conn.transaction():
            cls.conn.execute('''
                INSERT INTO loi.nguoi_dung (id, dang_nhap, ten, vai_tro)
                VALUES (%s, 'fixture_g202', 'DEMO fixture', 'XEM')
            ''', (cls.nd_fixture,))
            for pn, ma in ((cls.pn_a, 'FIXTURE_A'), (cls.pn_b, 'FIXTURE_B')):
                cls.conn.execute('''
                    INSERT INTO loi.phap_nhan (id, ma, ten) VALUES (%s, %s, 'DEMO fixture')
                ''', (pn, ma))
                cls.conn.execute('''
                    INSERT INTO loi.phan_quyen (nguoi_dung_id, phap_nhan_id)
                    VALUES (%s, %s)
                ''', (cls.nd_fixture, pn))
                cls.conn.execute('''
                    INSERT INTO loi.phap_nhan_boi_canh (phap_nhan_id, phien_ban, muc)
                    VALUES (%s, 1, 0)
                ''', (pn,))
        mat_khau = secrets.token_urlsafe(32)
        cls.conn.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(
            sql.Identifier(cls.login), sql.Literal(mat_khau)))
        cls.runtime = psycopg.connect(**{**cls.thong_tin, 'dbname': cls.db,
                                         'user': cls.login, 'password': mat_khau},
                                       autocommit=True)
        cls.addClassCleanup(cls.runtime.close)

    @classmethod
    def _don_tai_nguyen(cls):
        # Chỉ DB tự tạo; giữ role test, khóa mọi login, không DROP ROLE.
        for (login,) in cls.admin.execute('''
            SELECT rolname FROM pg_roles WHERE rolname=ANY(%s) AND rolcanlogin
        ''', (cls.cac_vai,)).fetchall():
            cls.admin.execute(sql.SQL('ALTER ROLE {} NOLOGIN').format(sql.Identifier(login)))
        cls.admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(cls.db)))

    def test_dung_login_that_khong_co_quyen_owner_ddl(self):
        self.assertEqual(self.runtime.execute('SELECT current_user, session_user').fetchone(),
                         (self.login, self.login))
        for cau_sql in ('CREATE TABLE loi.g202_cam(id int)',
                        'CREATE TEMP TABLE g202_cam(id int)',
                        'ALTER TABLE loi.phan_quyen ADD COLUMN g202_cam int',
                        sql.SQL('SET ROLE {}').format(sql.Identifier(self.chu))):
            with self.subTest(cau_sql=str(cau_sql)), self.assertRaises(
                psycopg.errors.InsufficientPrivilege
            ):
                self.runtime.execute(cau_sql)

    def test_owner_force_rls_va_view_khong_luu_ban_sao(self):
        rows = self.conn.execute('''
            SELECT c.relname, pg_get_userbyid(c.relowner), c.relrowsecurity,
                   c.relforcerowsecurity FROM pg_class c
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='loi' AND c.relname=ANY(%s)
        ''', (list(CAC_BANG),)).fetchall()
        self.assertEqual(set(rows), {(ten, self.chu, True, True) for ten in CAC_BANG})
        self.assertEqual(self.conn.execute('''
            SELECT relkind, reloptions FROM pg_class WHERE oid='loi.thanh_vien'::regclass
        ''').fetchone(), ('v', ['security_invoker=true']))
        self.assertEqual(self.runtime.execute('SELECT * FROM loi.thanh_vien').fetchall(), [])

    def test_khoa_duy_nhat_dung_nguon_chung(self):
        rows = self.conn.execute('''
            SELECT c.relname, pg_get_constraintdef(k.oid) FROM pg_constraint k
            JOIN pg_class c ON c.oid=k.conrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='loi' AND k.contype='u' AND c.relname=ANY(%s)
        ''', (list(CAC_BANG),)).fetchall()
        self.assertIn(('nguoi_dung', 'UNIQUE (dang_nhap)'), rows)
        self.assertIn(('phap_nhan', 'UNIQUE (ma)'), rows)
        self.assertIn(('phap_nhan', 'UNIQUE (ma_don_vi_junsky)'), rows)
        self.assertIn(('phan_quyen', 'UNIQUE (nguoi_dung_id, phap_nhan_id)'), rows)
        self.assertIn(('phap_nhan_boi_canh', 'UNIQUE (phap_nhan_id, muc, phien_ban)'), rows)

    def test_catalog_vai_chi_doc_khong_tu_cap_quyen(self):
        self.assertEqual({r[0] for r in self.runtime.execute(
            'SELECT ma FROM loi.vai_nghiep_vu').fetchall()}, danh_tinh.CAC_VAI_TRO)
        for cau_sql in ("INSERT INTO loi.vai_nghiep_vu VALUES ('QUAN_TRI', 'DEMO')",
                        'TRUNCATE loi.phan_quyen',
                        "UPDATE loi.nguoi_dung SET vai_tro='CFO'",
                        'DELETE FROM loi.phan_quyen'):
            with self.subTest(cau_sql=cau_sql), self.assertRaises(
                psycopg.errors.InsufficientPrivilege
            ):
                self.runtime.execute(cau_sql)

    def test_gia_actor_phap_nhan_khong_mo_rls(self):
        with self.runtime.transaction():
            for ten, gia_tri in (('ktt.nguoi_dung_id', str(self.nd_fixture)),
                                 ('ktt.nguoi_dung_dang_nhap', 'CFO'),
                                 ('ktt.phap_nhan_id', str(self.pn_a)),
                                 ('ktt.ma_phien', 'DEMO_GIA')):
                self.runtime.execute('SELECT set_config(%s, %s, true)', (ten, gia_tri))
            for ten in ('nguoi_dung', 'phap_nhan', 'phan_quyen', 'phap_nhan_boi_canh'):
                self.assertEqual(self.runtime.execute(
                    sql.SQL('SELECT * FROM loi.{}').format(sql.Identifier(ten))).fetchall(), [])
            for pn in (self.pn_a, self.pn_b):
                self.assertIsNone(danh_tinh.tra_phap_nhan(self.runtime, phap_nhan_id=pn))
                self.assertIsNone(danh_tinh.tra_thanh_vien(
                    self.runtime, nguoi_dung_id=self.nd_fixture, phap_nhan_id=pn))
            for tao in (
                lambda: danh_tinh.tao_nguoi_dung(self.runtime, dang_nhap='demo', ten='DEMO'),
                lambda: danh_tinh.tao_phap_nhan(self.runtime, ma='DEMO', ten='DEMO'),
                lambda: danh_tinh.tao_thanh_vien(self.runtime, nguoi_dung_id=self.nd_fixture,
                                               phap_nhan_id=self.pn_b),
            ):
                with self.assertRaisesRegex(psycopg.errors.InsufficientPrivilege,
                                            'row-level security'):
                    with self.runtime.transaction():
                        tao()

    def test_chay_lai_idempotent(self):
        def anh():
            return self.conn.execute('''
                SELECT c.oid, c.relname, c.relowner, c.relacl,
                       c.relrowsecurity, c.relforcerowsecurity, c.reloptions
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='loi' ORDER BY c.oid
            ''').fetchall(), self.conn.execute('''
                SELECT oid, polrelid, polname, polroles, pg_get_expr(polqual, polrelid),
                       pg_get_expr(polwithcheck, polrelid) FROM pg_policy ORDER BY oid
            ''').fetchall()
        truoc = anh()
        with self.conn.transaction():
            self.conn.execute(SQL_DANH_TINH)
        self.assertEqual(anh(), truoc)
        self.test_gia_actor_phap_nhan_khong_mo_rls()

    @unittest.skip('Cần lead: contract phiên/quyền G2-03; RLS G2-02 đang đóng mặc định')
    def test_nghiep_vu_tao_tra_va_trung_duoi_login_that(self):
        # Lead cần bổ sung ngữ cảnh phiên G2-03 trước khi bỏ skip.
        with self.runtime.transaction():
            nd = danh_tinh.tao_nguoi_dung(self.runtime, dang_nhap='demo_g202', ten='DEMO')
            pn = danh_tinh.tao_phap_nhan(self.runtime, ma='DEMO_G202', ten='DEMO')
            tv = danh_tinh.tao_thanh_vien(self.runtime, nguoi_dung_id=nd.id, phap_nhan_id=pn.id)
            self.assertEqual(danh_tinh.tra_nguoi_dung(
                self.runtime, dang_nhap=nd.dang_nhap), nd)
            self.assertEqual(danh_tinh.tra_phap_nhan(self.runtime, phap_nhan_id=pn.id), pn)
            self.assertEqual(danh_tinh.tra_thanh_vien(
                self.runtime, nguoi_dung_id=nd.id, phap_nhan_id=pn.id), tv)
            for tao in (
                lambda: danh_tinh.tao_nguoi_dung(self.runtime, dang_nhap=nd.dang_nhap, ten='DEMO'),
                lambda: danh_tinh.tao_phap_nhan(self.runtime, ma=pn.ma, ten='DEMO'),
                lambda: danh_tinh.tao_thanh_vien(self.runtime, nguoi_dung_id=nd.id, phap_nhan_id=pn.id),
            ):
                with self.assertRaises(psycopg.errors.UniqueViolation):
                    with self.runtime.transaction():
                        tao()


if __name__ == '__main__':
    unittest.main()
