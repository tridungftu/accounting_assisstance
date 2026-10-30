"""G2-03: mock và PG16 trên DB tự tạo, ca nghiệp vụ dùng LOGIN thật.

Không mở/dừng dịch vụ; không đọc cấu hình thật. Giữ role test, khóa NOLOGIN
khi xong, chỉ dọn DB kho_test_* của chính lượt chạy, giống G2-01/02.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import secrets
import sys
import traceback
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import phien

try:
    from .test_g2_01 import _kiem_dich_test, SQL_VAI, psycopg
    from .test_g2_02 import SQL_DANH_TINH
except ImportError:
    from test_g2_01 import _kiem_dich_test, SQL_VAI, psycopg
    from test_g2_02 import SQL_DANH_TINH

if psycopg is not None:
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict

SQL_PHIEN = (Path(__file__).resolve().parents[1]
             / 'src/kho_tri_thuc/core/sql/003_phien.sql').read_text(encoding='utf-8')
ADMIN_DSN = os.environ.get('KHO_PG_DSN_TEST')


class PhienThuanTest(unittest.TestCase):
    def setUp(self):
        self.conn = Mock(spec=['execute'])
        self.nd, self.pn, self.id = uuid4(), uuid4(), uuid4()
        self.han = datetime.now(timezone.utc) + timedelta(minutes=10)
        self.conn.execute.return_value.fetchone.return_value = (self.id,)
        self.tham_so = dict(nguoi_dung_id=self.nd, module='CRM', phap_nhan_id=self.pn,
                           dang_nhap_csdl='dang_nhap_loi', pham_vi_hanh_dong=['DOC'],
                           hieu_luc_den=self.han)

    def test_sinh_ngau_nhien_256_bit_va_bind(self):
        with patch.object(phien.secrets, 'token_urlsafe', return_value='B' * 43) as sinh:
            ket_qua = phien.cap_phien(self.conn, **self.tham_so)
        sinh.assert_called_once_with(32)
        cau_sql, tham_so = self.conn.execute.call_args.args
        self.assertEqual(cau_sql.count('%s'), 11)
        self.assertNotIn('B' * 43, cau_sql)
        self.assertEqual(tham_so, ('B' * 43, self.nd, 'CRM', self.pn, 'dang_nhap_loi',
                                 ['DOC'], self.han, 'NGUOI_DUNG', None, None, None))
        self.assertEqual(ket_qua.id, self.id)
        with self.assertRaises(FrozenInstanceError):
            ket_qua.id = uuid4()

    def test_ma_moi_khong_trung_va_repr_an_ma(self):
        a = phien.cap_phien(self.conn, **self.tham_so)
        b = phien.cap_phien(self.conn, **self.tham_so)
        self.assertNotEqual(a.ma.lay_de_truyen(), b.ma.lay_de_truyen())
        for doi_tuong in (a, a.ma, {'ma': a.ma}, [a]):
            self.assertNotIn(a.ma.lay_de_truyen(), repr(doi_tuong))
            self.assertNotIn(a.ma.lay_de_truyen(), str(doi_tuong))

    def test_cap_uy_nhiem_bind_ma_goc_va_the_he(self):
        ma_goc, viec = phien.MaBiMat('G' * 43), uuid4()
        phien.cap_phien(self.conn, **{**self.tham_so, 'loai': 'UY_NHIEM_VIEC',
                                     'ma_goc': ma_goc, 'viec_id': viec, 'the_he': 2})
        cau_sql, tham_so = self.conn.execute.call_args.args
        self.assertNotIn('G' * 43, cau_sql)
        self.assertEqual(tham_so[-4:], ('UY_NHIEM_VIEC', 'G' * 43, viec, 2))

    def test_xac_minh_tra_danh_tinh_bat_bien_khong_dung_guc(self):
        dong = (self.id, self.nd, 'CRM', self.pn, 'DOC', None, None, self.han)
        self.conn.execute.return_value.fetchone.return_value = dong
        ket_qua = phien.xac_minh_phien(self.conn, ma=phien.MaBiMat('X' * 43),
                                      module='CRM', phap_nhan_id=self.pn, hanh_dong='DOC')
        self.assertEqual(ket_qua, phien.DanhTinhDaXacMinh(*dong))
        cau_sql, tham_so = self.conn.execute.call_args.args
        self.assertNotIn('X' * 43, cau_sql)
        self.assertNotIn('set_config', cau_sql)
        self.assertEqual(tham_so, ('X' * 43, 'CRM', self.pn, 'DOC', None, None))
        with self.assertRaises(FrozenInstanceError):
            ket_qua.nguoi_dung_id = uuid4()

    def test_khong_hop_le_tra_none(self):
        self.conn.execute.return_value.fetchone.return_value = None
        self.assertIsNone(phien.xac_minh_phien(
            self.conn, ma=phien.MaBiMat('X' * 43), module='CRM',
            phap_nhan_id=self.pn, hanh_dong='DOC'))

    def test_thu_hoi_bind(self):
        phien.thu_hoi_phien(self.conn, ma=phien.MaBiMat('H' * 43))
        self.assertEqual(self.conn.execute.call_args.args,
                         ('SELECT loi.thu_hoi_phien(%s)', ('H' * 43,)))
        phien.thu_hoi_phien_nguoi_dung(self.conn, nguoi_dung_id=self.nd)
        self.assertEqual(self.conn.execute.call_args.args,
                         ('SELECT loi.thu_hoi_phien_nguoi_dung(%s)', (self.nd,)))
        viec = uuid4()
        phien.thu_hoi_uy_nhiem_viec(self.conn, viec_id=viec, the_he=3)
        self.assertEqual(self.conn.execute.call_args.args,
                         ('SELECT loi.thu_hoi_uy_nhiem_viec(%s, %s)', (viec, 3)))

    def test_loi_driver_khong_lo_ma_hoac_giu_exception_goc(self):
        bi_mat = 'CANARY_BI_MAT_' + secrets.token_urlsafe(32)
        self.conn.execute.side_effect = RuntimeError(bi_mat)
        cac_lenh = (
            lambda: phien.cap_phien(self.conn, **self.tham_so),
            lambda: phien.xac_minh_phien(self.conn, ma=phien.MaBiMat(bi_mat),
                module='CRM', phap_nhan_id=self.pn, hanh_dong='DOC'),
            lambda: phien.thu_hoi_phien(self.conn, ma=phien.MaBiMat(bi_mat)),
            lambda: phien.thu_hoi_phien_nguoi_dung(self.conn, nguoi_dung_id=self.nd),
            lambda: phien.thu_hoi_uy_nhiem_viec(self.conn, viec_id=uuid4(), the_he=1),
        )
        for lenh in cac_lenh:
            with self.subTest(lenh=lenh), self.assertRaises(phien.LoiPhien) as bat:
                lenh()
            self.assertNotIn(bi_mat, ''.join(traceback.format_exception(bat.exception)))
            self.assertIsNone(bat.exception.__context__)
            self.assertIsNone(bat.exception.__cause__)

    def test_tham_so_sai_khong_goi_sql(self):
        for loi in ({'hieu_luc_den': datetime.now()}, {'module': ''},
                    {'pham_vi_hanh_dong': ['*']}, {'pham_vi_hanh_dong': []},
                    {'loai': 'UY_NHIEM_PHIEN'}, {'loai': 'UY_NHIEM_VIEC'},
                    {'loai': 'UY_NHIEM_VIEC', 'viec_id': uuid4(), 'the_he': True},
                    {'the_he': 1}, {'loai': 'KHAC'}):
            with self.subTest(loi=loi), self.assertRaises(ValueError):
                phien.cap_phien(self.conn, **{**self.tham_so, **loi})
        self.conn.execute.assert_not_called()

    def test_khong_nhan_actor_hoac_ma_thuan(self):
        with self.assertRaises(TypeError):
            phien.cap_phien(self.conn, **self.tham_so, actor=self.nd)
        with self.assertRaises(ValueError):
            phien.thu_hoi_phien(self.conn, ma='MA_THUAN')
        self.conn.execute.assert_not_called()


@unittest.skipUnless(psycopg is not None and ADMIN_DSN,
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class PhienPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.thong_tin = _kiem_dich_test(conninfo_to_dict(ADMIN_DSN))
        cls.admin = psycopg.connect(**cls.thong_tin, autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        if cls.admin.info.server_version < 160000 or not cls.admin.execute(
            'SELECT rolsuper FROM pg_roles WHERE rolname=current_user'
        ).fetchone()[0]:
            raise RuntimeError('Cần lead cấp provisioning admin PG16+')
        ma_lan = uuid4().hex[:12]
        cls.db = 'kho_test_g2_03_' + ma_lan
        cls.tien_to = 'ktt_test_g203_' + ma_lan + '_'
        cls.login = cls.tien_to + 'dang_nhap_loi'
        cls.chu = cls.tien_to + 'vai_doi_cau_truc_loi'
        cls.login_mod = cls.tien_to + 'dang_nhap_mod_demo'
        cls.login_sai = cls.tien_to + 'dang_nhap_mod_sai'
        cls.cac_login = [cls.login, cls.tien_to + 'dang_nhap_cai_dat', cls.login_mod, cls.login_sai]
        cls.admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(cls.db)))
        cls.addClassCleanup(cls._don_tai_nguyen)
        cls.conn = psycopg.connect(**{**cls.thong_tin, 'dbname': cls.db}, autocommit=True)
        cls.addClassCleanup(cls.conn.close)
        cls.conn.execute("SET log_parameter_max_length = 0")
        cls.conn.execute("SET log_parameter_max_length_on_error = 0")
        cls.conn.execute('SELECT set_config(%s, %s, false)',
                         ('kho_tri_thuc.tien_to_vai', cls.tien_to))
        with cls.conn.transaction():
            cls.conn.execute(SQL_VAI)
            cls.conn.execute(SQL_DANH_TINH)
            cls.conn.execute(SQL_PHIEN)
        cls.runtime = {}
        for login in (cls.login, cls.login_mod, cls.login_sai):
            mat_khau = secrets.token_urlsafe(32)
            if login != cls.login:
                cls.conn.execute(sql.SQL('CREATE ROLE {} LOGIN INHERIT NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOREPLICATION').format(sql.Identifier(login)))
                cls.conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(
                    sql.Identifier(cls.db), sql.Identifier(login)))
                cls.conn.execute(sql.SQL('GRANT USAGE ON SCHEMA loi TO {}').format(sql.Identifier(login)))
                cls.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION loi.xac_minh_phien(text,text,uuid,text,uuid,bigint) TO {}').format(sql.Identifier(login)))
            cls.conn.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(
                sql.Identifier(login), sql.Literal(mat_khau)))
            for tham_so in ('log_parameter_max_length', 'log_parameter_max_length_on_error'):
                cls.conn.execute(sql.SQL('ALTER ROLE {} SET {} = 0').format(
                    sql.Identifier(login), sql.Identifier(tham_so)))
            chay = psycopg.connect(**{**cls.thong_tin, 'dbname': cls.db,
                                     'user': login, 'password': mat_khau}, autocommit=True)
            cls.addClassCleanup(chay.close)
            cls.runtime[login] = chay
        cls.core, cls.mod, cls.sai = (cls.runtime[l] for l in (cls.login, cls.login_mod, cls.login_sai))

    @classmethod
    def _don_tai_nguyen(cls):
        for (login,) in cls.admin.execute(
            'SELECT rolname FROM pg_roles WHERE rolname=ANY(%s) AND rolcanlogin',
            (cls.cac_login,)).fetchall():
            cls.admin.execute(sql.SQL('ALTER ROLE {} NOLOGIN').format(sql.Identifier(login)))
        cls.admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(cls.db)))

    def setUp(self):
        self.nd, self.pn, self.pn_khac = uuid4(), uuid4(), uuid4()
        # Admin chỉ tạo fixture tổng hợp, không thực hiện ca cấp/xác minh.
        self.conn.execute('''INSERT INTO loi.nguoi_dung(id,dang_nhap,ten,vai_tro)
            VALUES (%s,%s,'DEMO','XEM')''', (self.nd, 'demo_' + self.nd.hex))
        for pn in (self.pn, self.pn_khac):
            self.conn.execute("INSERT INTO loi.phap_nhan(id,ma,ten) VALUES (%s,%s,'DEMO')",
                              (pn, 'demo_' + pn.hex))
        self.conn.execute('INSERT INTO loi.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,%s)',
                          (self.nd, self.pn, ['CRM']))
        self.han = datetime.now(timezone.utc) + timedelta(minutes=10)

    def _cap(self, **doi):
        return phien.cap_phien(self.core, **{
            'nguoi_dung_id': self.nd, 'module': 'CRM', 'phap_nhan_id': self.pn,
            'dang_nhap_csdl': self.login, 'pham_vi_hanh_dong': ['DOC', 'GHI'],
            'hieu_luc_den': self.han, **doi})

    def _uy_nhiem(self, **doi):
        goc = self._cap()
        return self._cap(loai='UY_NHIEM_PHIEN', ma_goc=goc.ma,
                         dang_nhap_csdl=self.login_mod, **doi)

    def _xac_minh(self, ma, conn=None, **doi):
        return phien.xac_minh_phien(self.core if conn is None else conn, **{
            'ma': ma, 'module': 'CRM', 'phap_nhan_id': self.pn, 'hanh_dong': 'DOC', **doi})

    def test_login_that_va_luong_hop_le(self):
        for login, conn in self.runtime.items():
            self.assertEqual(conn.execute('SELECT current_user,session_user').fetchone(), (login, login))
            self.assertEqual(conn.execute('SHOW log_parameter_max_length').fetchone(), ('0',))
            self.assertEqual(conn.execute('SHOW log_parameter_max_length_on_error').fetchone(), ('0',))
        p = self._cap()
        self.assertEqual(self._xac_minh(p.ma).nguoi_dung_id, self.nd)
        u = self._uy_nhiem()
        self.assertEqual(self._xac_minh(u.ma, self.mod).nguoi_dung_id, self.nd)

    def test_gia_guc_khong_tao_hoac_doi_danh_tinh(self):
        p = self._cap()
        with self.core.transaction():
            for ten, gia_tri in (('ktt.nguoi_dung_id', str(uuid4())),
                                 ('ktt.nguoi_dung_dang_nhap', 'ADMIN'),
                                 ('ktt.ngay_hieu_luc', '1900-01-01'),
                                 ('ktt.phap_nhan_id', str(self.pn_khac)),
                                 ('ktt.ma_phien', 'GIA'), ('ktt.da_xac_minh', 'true')):
                self.core.execute('SELECT set_config(%s,%s,true)', (ten, gia_tri))
            self.assertIsNone(self._xac_minh(phien.MaBiMat('GIA')))
            self.assertEqual(self._xac_minh(p.ma).nguoi_dung_id, self.nd)

    def test_sai_login(self):
        u = self._uy_nhiem()
        self.assertIsNone(self._xac_minh(u.ma, self.sai))
        self.assertIsNone(self._xac_minh(u.ma, self.core))

    def test_sai_module(self):
        self.assertIsNone(self._xac_minh(self._cap().ma, module='M4'))

    def test_sai_phap_nhan(self):
        self.assertIsNone(self._xac_minh(self._cap().ma, phap_nhan_id=self.pn_khac))

    def test_sai_hanh_dong(self):
        self.assertIsNone(self._xac_minh(self._cap().ma, hanh_dong='XOA'))

    def test_het_han_ke_ca_transaction_da_mo(self):
        han = datetime.now(timezone.utc) + timedelta(seconds=2)
        p = self._cap(hieu_luc_den=han)
        with self.core.transaction():
            self.assertIsNotNone(self._xac_minh(p.ma))
            # Chờ đúng hạn (tối đa 2 giây), chứng minh không dùng now() của đầu tx.
            self.core.execute('SELECT pg_sleep(greatest(0, extract(epoch FROM (%s::timestamptz-clock_timestamp()))) + 0.02)', (han,))
            self.assertIsNone(self._xac_minh(p.ma))
        with self.assertRaises(phien.LoiPhien):
            self._cap(hieu_luc_den=datetime.now(timezone.utc) - timedelta(seconds=1))

    def test_thu_hoi_va_dang_xuat_thu_hoi_con(self):
        goc = self._cap()
        con = self._cap(loai='UY_NHIEM_PHIEN', ma_goc=goc.ma, dang_nhap_csdl=self.login_mod)
        self.assertIsNotNone(self._xac_minh(con.ma, self.mod))
        phien.thu_hoi_phien(self.core, ma=goc.ma)
        phien.thu_hoi_phien(self.core, ma=goc.ma)  # idempotent
        self.assertIsNone(self._xac_minh(goc.ma))
        self.assertIsNone(self._xac_minh(con.ma, self.mod))
        with self.assertRaises(phien.LoiPhien):
            self._cap(loai='UY_NHIEM_PHIEN', ma_goc=goc.ma, dang_nhap_csdl=self.login_mod)

    def test_uy_nhiem_khong_dai_hon_phien(self):
        goc = self._cap()
        with self.assertRaises(phien.LoiPhien):
            self._cap(loai='UY_NHIEM_PHIEN', ma_goc=goc.ma, dang_nhap_csdl=self.login_mod,
                      hieu_luc_den=self.han + timedelta(seconds=1))

    def test_uy_nhiem_khong_mo_rong_pham_vi(self):
        goc = self._cap(pham_vi_hanh_dong=['DOC'])
        with self.assertRaises(phien.LoiPhien):
            self._cap(loai='UY_NHIEM_PHIEN', ma_goc=goc.ma, dang_nhap_csdl=self.login_mod)

    def test_khong_ghep_phien_goc_nguoi_module_phap_nhan_khac(self):
        goc = self._cap()
        for doi in ({'phap_nhan_id': self.pn_khac}, {'module': 'M4'}, {'ma_goc': phien.MaBiMat('SAI')}):
            with self.subTest(doi=doi), self.assertRaises(phien.LoiPhien):
                self._cap(**{'loai': 'UY_NHIEM_PHIEN', 'ma_goc': goc.ma,
                             'dang_nhap_csdl': self.login_mod, **doi})

    def test_ma_viec_sai_the_he_va_sai_viec(self):
        viec = uuid4()
        p = self._cap(loai='UY_NHIEM_VIEC', dang_nhap_csdl=self.login_mod, viec_id=viec, the_he=1)
        self.assertIsNotNone(self._xac_minh(p.ma, self.mod, viec_id=viec, the_he=1))
        for doi in ({'viec_id': viec, 'the_he': 2}, {'viec_id': uuid4(), 'the_he': 1}, {}):
            with self.subTest(doi=doi):
                self.assertIsNone(self._xac_minh(p.ma, self.mod, **doi))
        self.assertIsNone(self._xac_minh(self._cap().ma, viec_id=viec, the_he=1))

    def test_the_he_moi_vo_hieu_the_he_cu_ke_ca_gui_dung_so_cu(self):
        viec = uuid4()
        a = self._cap(loai='UY_NHIEM_VIEC', viec_id=viec, the_he=1)
        b = self._cap(loai='UY_NHIEM_VIEC', viec_id=viec, the_he=2)
        self.assertIsNone(self._xac_minh(a.ma, viec_id=viec, the_he=1))
        self.assertIsNotNone(self._xac_minh(b.ma, viec_id=viec, the_he=2))
        for the_he in (1, 2):
            with self.subTest(the_he=the_he), self.assertRaises(phien.LoiPhien):
                self._cap(loai='UY_NHIEM_VIEC', viec_id=viec, the_he=the_he)

    def test_doi_quyen_thu_hoi_ma_phien_va_viec(self):
        p, u = self._cap(), self._uy_nhiem()
        viec = uuid4()
        v = self._cap(loai='UY_NHIEM_VIEC', viec_id=viec, the_he=1)
        self.conn.execute('UPDATE loi.phan_quyen SET module=%s WHERE nguoi_dung_id=%s', (['M4'], self.nd))
        self.assertIsNone(self._xac_minh(p.ma))
        self.assertIsNone(self._xac_minh(u.ma, self.mod))
        self.assertIsNone(self._xac_minh(v.ma, viec_id=viec, the_he=1))

    def test_khoa_tai_khoan_khong_hoi_sinh_ma_khi_mo_lai(self):
        p = self._cap()
        for trang_thai in ('KHOA', 'HOAT_DONG'):
            self.conn.execute('UPDATE loi.nguoi_dung SET trang_thai=%s WHERE id=%s', (trang_thai, self.nd))
            self.assertIsNone(self._xac_minh(p.ma))

    def test_cua_thu_hoi_khi_mtq_doi(self):
        p = self._cap()
        phien.thu_hoi_phien_nguoi_dung(self.core, nguoi_dung_id=self.nd)
        self.assertIsNone(self._xac_minh(p.ma))

    def test_mat_lease_thu_hoi_bang_viec_va_the_he_khong_can_ma_goc(self):
        viec = uuid4()
        p = self._cap(loai='UY_NHIEM_VIEC', viec_id=viec, the_he=1)
        phien.thu_hoi_uy_nhiem_viec(self.core, viec_id=viec, the_he=1)
        self.assertIsNone(self._xac_minh(p.ma, viec_id=viec, the_he=1))
        moi = self._cap(loai='UY_NHIEM_VIEC', viec_id=viec, the_he=2)
        phien.thu_hoi_uy_nhiem_viec(self.core, viec_id=viec, the_he=1)
        self.assertIsNotNone(self._xac_minh(moi.ma, viec_id=viec, the_he=2))

    def test_phap_nhan_khoa_roi_mo_khong_hoi_sinh_ma(self):
        p = self._cap()
        for trang_thai in ('KHOA', 'HOAT_DONG'):
            self.conn.execute('UPDATE loi.phap_nhan SET trang_thai=%s WHERE id=%s', (trang_thai, self.pn))
            self.assertIsNone(self._xac_minh(p.ma))

    def test_runtime_khong_select_dml_bang_phien(self):
        for conn in (self.core, self.mod, self.sai):
            for cau_sql in ('SELECT * FROM loi.phien_xac_thuc',
                            'INSERT INTO loi.phien_xac_thuc DEFAULT VALUES',
                            'UPDATE loi.phien_xac_thuc SET thu_hoi_luc=NULL',
                            'DELETE FROM loi.phien_xac_thuc', 'TRUNCATE loi.phien_xac_thuc'):
                with self.subTest(cau_sql=cau_sql), self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    conn.execute(cau_sql)

    def test_module_khong_cap_hoac_thu_hoi_ke_ca_gia_guc(self):
        p = self._cap()
        with self.assertRaises(phien.LoiPhien):
            phien.thu_hoi_phien(self.mod, ma=p.ma)
        with self.assertRaises(phien.LoiPhien):
            phien.thu_hoi_phien_nguoi_dung(self.mod, nguoi_dung_id=self.nd)
        with self.assertRaises(phien.LoiPhien):
            phien.thu_hoi_uy_nhiem_viec(self.mod, viec_id=uuid4(), the_he=1)
        with self.assertRaises(phien.LoiPhien):
            phien.cap_phien(self.mod, nguoi_dung_id=self.nd, module='CRM',
                phap_nhan_id=self.pn, dang_nhap_csdl=self.login_mod,
                pham_vi_hanh_dong=['DOC'], hieu_luc_den=self.han)
        self.assertIsNotNone(self._xac_minh(p.ma))

    def test_bang_chi_co_bam_khong_chua_ma_goc_va_repr_an_ma(self):
        p, u = self._cap(), self._uy_nhiem()
        for ma in (p, u):
            dong = self.conn.execute('SELECT ma_bam,row_to_json(p)::text FROM loi.phien_xac_thuc p WHERE id=%s', (ma.id,)).fetchone()
            self.assertEqual(bytes(dong[0]), hashlib.sha256(ma.ma.lay_de_truyen().encode()).digest())
            self.assertNotIn(ma.ma.lay_de_truyen(), dong[1])
            self.assertNotIn(ma.ma.lay_de_truyen(), repr(ma))

    def test_catalog_definer_stable_owner_path_force_rls_va_chi_muc(self):
        rows = self.conn.execute('''SELECT proname,pg_get_userbyid(proowner),prosecdef,provolatile,proconfig
            FROM pg_proc WHERE pronamespace='loi'::regnamespace
            AND proname IN ('cap_phien','xac_minh_phien','thu_hoi_phien','thu_hoi_phien_nguoi_dung','thu_hoi_uy_nhiem_viec','thu_hoi_phien_khi_doi_quyen')''').fetchall()
        self.assertEqual(len(rows), 6)
        for ten, owner, definer, volatility, config in rows:
            self.assertEqual(owner, self.chu)
            self.assertTrue(definer)
            self.assertEqual(config, ['search_path=pg_catalog, pg_temp'])
            if ten == 'xac_minh_phien':
                self.assertEqual(volatility, 's')
        self.assertEqual(self.conn.execute("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='loi.phien_xac_thuc'::regclass").fetchone(), (True, True))
        self.assertTrue(self.conn.execute("SELECT EXISTS (SELECT FROM pg_indexes WHERE schemaname='loi' AND tablename='phien_xac_thuc' AND indexdef LIKE 'CREATE UNIQUE INDEX%%(ma_bam)')").fetchone()[0])

    def test_chay_lai_giu_ma_va_khong_noi_quyen(self):
        p = self._cap()
        self.conn.execute(SQL_PHIEN)
        self.assertIsNotNone(self._xac_minh(p.ma))
        self.test_runtime_khong_select_dml_bang_phien()
        self.test_module_khong_cap_hoac_thu_hoi_ke_ca_gia_guc()


if __name__ == '__main__':
    unittest.main()
