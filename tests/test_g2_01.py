"""G2-01: bootstrap role/schema; PG do lead chay, khong khoi dong dich vu.

KHO_PG_DSN_TEST tro toi admin localhost (postgres/Core DEMO/kho_test_*).
Tao DB kho_test_* va login thu rieng; khong doi mat khau hai login Core.
Ca quyen dung ket noi LOGIN that ke thua cac vai chay, khong SET ROLE owner.
Chi don DB kho_test_*; giu role ktt_test_* theo chinh sach repo.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import secrets
import unittest
import uuid

try:
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict
except ImportError:
    psycopg = None


SQL_PATH = Path(__file__).resolve().parents[1] / 'src/kho_tri_thuc/core/sql/001_vai.sql'
SQL_VAI = SQL_PATH.read_text(encoding='utf-8')
CAC_KHOI = ('loi', 'loi_tai_lieu', 'danh_muc')
CAC_VAI_CHAY = tuple('vai_chay_' + k for k in CAC_KHOI)
CAC_VAI_CHU = tuple('vai_doi_cau_truc_' + k for k in CAC_KHOI)
CAC_VAI = CAC_VAI_CHAY + CAC_VAI_CHU + ('dang_nhap_loi', 'dang_nhap_cai_dat')
ADMIN_DSN = os.environ.get('KHO_PG_DSN_TEST')


def _kiem_dich_test(thong_tin):
    """Chan dich that/ngoai may truoc khi ket noi, khong dua DSN vao loi."""
    ten_db = thong_tin.get('dbname', '')
    if not re.fullmatch(r'postgres|kho_core_demo_g2_[a-z0-9_]+|kho_test_[a-z0-9_]+', ten_db):
        raise ValueError('Chi dung admin DB postgres/Core DEMO/kho_test_*')
    if thong_tin.get('service') or thong_tin.get('options'):
        raise ValueError('Khong nhan service/options an dich hoac vai')
    for truong in ('host', 'hostaddr'):
        if thong_tin.get(truong, 'localhost') not in ('localhost', '127.0.0.1', '::1'):
            raise ValueError('Test chi dung PostgreSQL localhost')
    # Khong de PGHOST/PGHOSTADDR/PGOPTIONS moi truong doi dich da kiem.
    host = thong_tin.get('host', '127.0.0.1')
    hostaddr = thong_tin.get('hostaddr', '::1' if host == '::1' else '127.0.0.1')
    if hostaddr == 'localhost':
        hostaddr = '127.0.0.1'
    return {**thong_tin, 'host': host, 'hostaddr': hostaddr, 'options': ''}


class GuardDichTest(unittest.TestCase):
    def test_dich_demo_va_test(self):
        for db in ('postgres', 'kho_core_demo_g2_01', 'kho_test_g2_01_abc'):
            ket_qua = _kiem_dich_test({'dbname': db, 'host': '127.0.0.1'})
            self.assertEqual(ket_qua['dbname'], db)
            self.assertEqual(ket_qua['hostaddr'], '127.0.0.1')

    def test_khoa_default_ket_noi_khong_lay_tu_moi_truong(self):
        ket_qua = _kiem_dich_test({'dbname': 'postgres'})
        self.assertEqual((ket_qua['host'], ket_qua['hostaddr'], ket_qua['options']),
                         ('127.0.0.1', '127.0.0.1', ''))

    def test_chan_dich_that_va_ten_gan_dung(self):
        for db in ('', 'kho_that', 'kho_core_demo', 'kho_test_', 'kho_test_x/that'):
            with self.subTest(db=db), self.assertRaises(ValueError):
                _kiem_dich_test({'dbname': db})

    def test_chan_chuyen_huong_ket_noi(self):
        for extra in ({'host': 'may-that'}, {'hostaddr': '10.0.0.1'},
                      {'host': 'localhost,10.0.0.1'}, {'service': 'that'},
                      {'options': '-c role=postgres'}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                _kiem_dich_test({'dbname': 'postgres', **extra})


@unittest.skipUnless(psycopg is not None and ADMIN_DSN,
                     'CHUA_KIEM PG: thieu psycopg hoac KHO_PG_DSN_TEST')
class VaiPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.thong_tin = _kiem_dich_test(conninfo_to_dict(ADMIN_DSN))
        cls.admin = psycopg.connect(**cls.thong_tin, autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        if cls.admin.info.server_version < 160000:
            raise RuntimeError('Can PostgreSQL 16+ de nghiem thu membership')
        if not cls.admin.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user').fetchone()[0]:
            raise RuntimeError('Can lead cap admin provisioning cho test')
        ma_lan = uuid.uuid4().hex[:12]
        cls.db = 'kho_test_g2_01_' + ma_lan
        cls.tien_to = 'ktt_test_g201_' + ma_lan + '_'
        cls.cac_vai_chay = tuple(cls.tien_to + v for v in CAC_VAI_CHAY)
        cls.cac_vai_chu = tuple(cls.tien_to + v for v in CAC_VAI_CHU)
        cls.cac_vai = tuple(cls.tien_to + v for v in CAC_VAI)
        cls.dang_nhap_loi = cls.tien_to + 'dang_nhap_loi'
        cls.admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(cls.db)))
        cls.addClassCleanup(cls._don_tai_nguyen)
        cls.conn = psycopg.connect(**{**cls.thong_tin, 'dbname': cls.db}, autocommit=True)
        cls.addClassCleanup(cls.conn.close)
        cls.conn.execute('SELECT set_config(%s, %s, false)',
                         ('kho_tri_thuc.tien_to_vai', cls.tien_to))
        with cls.conn.transaction():
            cls.conn.execute(SQL_VAI)
        # Chi admin tao fixture duoi owner; ca quyen ben duoi dung LOGIN that.
        with cls.conn.transaction():
            for khoi, owner in zip(CAC_KHOI, cls.cac_vai_chu):
                cls.conn.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(owner)))
                cls.conn.execute(sql.SQL('CREATE TABLE {}.thu_bang(id int)').format(sql.Identifier(khoi)))
                cls.conn.execute(sql.SQL('CREATE SEQUENCE {}.thu_day_so').format(sql.Identifier(khoi)))
                cls.conn.execute(sql.SQL('CREATE TYPE {}.thu_kieu AS ENUM (\'DEMO\')').format(sql.Identifier(khoi)))
                cls.conn.execute(sql.SQL('CREATE FUNCTION {}.thu_ham() RETURNS integer LANGUAGE sql AS $$ SELECT 1 $$').format(sql.Identifier(khoi)))
            cls.conn.execute('RESET ROLE')
        # LOGIN rieng de khong thay password/login cua DEMO dang dung.
        cls.login = cls.tien_to + 'thu_chay'
        cls.login_cai_dat = cls.tien_to + 'thu_cai_dat'
        cls.ket_noi_chay = []
        for login, cac_vai in ((cls.login, cls.cac_vai_chay), (cls.login_cai_dat, ())):
            mat_khau = secrets.token_urlsafe(32)
            with cls.conn.transaction():
                cls.conn.execute(sql.SQL('CREATE ROLE {} LOGIN INHERIT NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOREPLICATION PASSWORD {}').format(sql.Identifier(login), sql.Literal(mat_khau)))
                for vai in cac_vai:
                    cls.conn.execute(sql.SQL('GRANT {} TO {} WITH INHERIT TRUE, SET FALSE, ADMIN FALSE').format(sql.Identifier(vai), sql.Identifier(login)))
            runtime = psycopg.connect(**{**cls.thong_tin, 'dbname': cls.db,
                                         'user': login, 'password': mat_khau}, autocommit=True)
            cls.ket_noi_chay.append(runtime)
            cls.addClassCleanup(runtime.close)
        cls.runtime, cls.cai_dat = cls.ket_noi_chay

    @classmethod
    def _don_tai_nguyen(cls):
        # Chi DB UUID do lan test tao; giu nguyen moi role ktt_test_*.
        cls.admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(cls.db)))

    def _bi_chan(self, ket_noi, cau_sql):
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            ket_noi.execute(cau_sql)

    def test_membership_pg16(self):
        rows = self.conn.execute('''
            SELECT duoc_cap.rolname, thanh_vien.rolname,
                   m.inherit_option, m.set_option, m.admin_option
            FROM pg_auth_members m JOIN pg_roles duoc_cap ON duoc_cap.oid=m.roleid
            JOIN pg_roles thanh_vien ON thanh_vien.oid=m.member
            WHERE thanh_vien.rolname = ANY(%s)
        ''', (list(self.cac_vai),)).fetchall()
        self.assertEqual(set(rows), {(r, self.dang_nhap_loi, True, False, False) for r in self.cac_vai_chay})

    def test_thuoc_tinh_va_owner(self):
        rows = self.conn.execute('''
            SELECT rolname, rolcanlogin, rolsuper, rolbypassrls, rolcreaterole,
                   rolcreatedb, rolreplication FROM pg_roles WHERE rolname=ANY(%s)
        ''', (list(self.cac_vai),)).fetchall()
        self.assertEqual(len(rows), 8)
        for ten, login, *quyen_nguy_hiem in rows:
            self.assertEqual(login, ten in (self.dang_nhap_loi, self.tien_to + 'dang_nhap_cai_dat'))
            self.assertFalse(any(quyen_nguy_hiem))
        self.assertEqual(set(self.conn.execute('''
            SELECT nspname, pg_get_userbyid(nspowner) FROM pg_namespace
            WHERE nspname=ANY(%s)
        ''', (list(CAC_KHOI),)).fetchall()), set(zip(CAC_KHOI, self.cac_vai_chu)))

    def test_login_that_khong_ddl_hoac_set_role(self):
        for conn, login in ((self.runtime, self.login), (self.cai_dat, self.login_cai_dat)):
            self.assertEqual(conn.execute('SELECT current_user, session_user').fetchone(), (login, login))
            for khoi, owner in zip(CAC_KHOI, self.cac_vai_chu):
                self._bi_chan(conn, sql.SQL('CREATE TABLE {}.khong_duoc_tao(id int)').format(sql.Identifier(khoi)))
                self._bi_chan(conn, sql.SQL('ALTER TABLE {}.thu_bang ADD COLUMN bi_chan int').format(sql.Identifier(khoi)))
                self._bi_chan(conn, sql.SQL('SET ROLE {}').format(sql.Identifier(owner)))
            self._bi_chan(conn, 'CREATE SCHEMA khong_duoc_tao')
            self._bi_chan(conn, 'CREATE TEMP TABLE khong_duoc_tao(id int)')
            self._bi_chan(conn, sql.SQL('CREATE ROLE {}').format(
                sql.Identifier(self.tien_to + 'khong_duoc_tao')))
        for vai in self.cac_vai_chay:
            self.assertTrue(self.runtime.execute('SELECT pg_has_role(current_user, %s, \'USAGE\')', (vai,)).fetchone()[0])
            self._bi_chan(self.runtime, sql.SQL('SET ROLE {}').format(sql.Identifier(vai)))

    def test_public_khong_co_quyen_schema(self):
        rows = self.conn.execute('''
            SELECT n.nspname FROM pg_namespace n,
            LATERAL aclexplode(coalesce(n.nspacl, acldefault('n', n.nspowner))) a
            WHERE n.nspname=ANY(%s) AND a.grantee=0
        ''', (list(CAC_KHOI),)).fetchall()
        self.assertEqual(rows, [])
        for khoi in CAC_KHOI:
            self.assertTrue(self.runtime.execute('SELECT has_schema_privilege(current_user, %s, \'USAGE\')', (khoi,)).fetchone()[0])

    def test_default_privileges_duoi_dung_owner(self):
        for catalog, namespace, owner_col, acl, kind, dieu_kien in (
            ('pg_class', 'relnamespace', 'relowner', 'relacl', 'r', "o.relkind='r'"),
            ('pg_class', 'relnamespace', 'relowner', 'relacl', 'S', "o.relkind='S'"),
            ('pg_proc', 'pronamespace', 'proowner', 'proacl', 'f', 'true'),
            # Array/rowtype tu sinh dung ACL cua kieu goc, khong phai TYPE khai bao.
            ('pg_type', 'typnamespace', 'typowner', 'typacl', 'T', "o.typtype='e'"),
        ):
            rows = self.conn.execute(sql.SQL('''
                SELECT n.nspname FROM {} o JOIN pg_namespace n ON n.oid=o.{}
                CROSS JOIN LATERAL aclexplode(coalesce(o.{}, acldefault(%s::"char", o.{}))) a
                WHERE n.nspname=ANY(%s) AND a.grantee=0 AND {}
            ''').format(*(sql.Identifier(v) for v in (catalog, namespace, acl, owner_col)), sql.SQL(dieu_kien)),
                (kind, list(CAC_KHOI))).fetchall()
            self.assertEqual(rows, [], catalog)
            owners = self.conn.execute(sql.SQL('''
                SELECT DISTINCT n.nspname, pg_get_userbyid(o.{})
                FROM {} o JOIN pg_namespace n ON n.oid=o.{} WHERE n.nspname=ANY(%s)
            ''').format(*(sql.Identifier(v) for v in (owner_col, catalog, namespace))),
                (list(CAC_KHOI),)).fetchall()
            self.assertEqual(set(owners), set(zip(CAC_KHOI, self.cac_vai_chu)))
        for khoi in CAC_KHOI:
            self._bi_chan(self.runtime, sql.SQL('SELECT * FROM {}.thu_bang').format(sql.Identifier(khoi)))
            self._bi_chan(self.runtime, sql.SQL('INSERT INTO {}.thu_bang VALUES (1)').format(sql.Identifier(khoi)))
            self._bi_chan(self.runtime, sql.SQL('SELECT nextval({})').format(sql.Literal(khoi + '.thu_day_so')))
            self._bi_chan(self.runtime, sql.SQL('SELECT {}.thu_ham()').format(sql.Identifier(khoi)))

    def _anh_quyen(self):
        cac_anh = tuple(self.conn.execute(query, (list(self.cac_vai),)).fetchall() for query in (
            '''SELECT rolname, rolcanlogin, rolsuper, rolbypassrls, rolcreatedb,
                      rolcreaterole, rolinherit, rolreplication
               FROM pg_roles WHERE rolname=ANY(%s) ORDER BY rolname''',
            '''SELECT m.roleid, m.member, m.grantor, m.inherit_option, m.set_option, m.admin_option
               FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
               WHERE r.rolname=ANY(%s) ORDER BY m.roleid,m.member,m.grantor''',
            '''SELECT nspname,nspowner,nspacl::text FROM pg_namespace
               WHERE nspowner IN (SELECT oid FROM pg_roles WHERE rolname=ANY(%s)) ORDER BY nspname''',
            '''SELECT defaclrole,defaclnamespace,defaclobjtype,defaclacl::text FROM pg_default_acl
               WHERE defaclrole IN (SELECT oid FROM pg_roles WHERE rolname=ANY(%s))
               ORDER BY defaclrole,defaclnamespace,defaclobjtype''',
            '''SELECT c.oid,c.relowner,c.relacl::text FROM pg_class c
               WHERE c.relowner IN (SELECT oid FROM pg_roles WHERE rolname=ANY(%s)) ORDER BY c.oid''',
            '''SELECT p.oid,p.proowner,p.proacl::text FROM pg_proc p
               WHERE p.proowner IN (SELECT oid FROM pg_roles WHERE rolname=ANY(%s)) ORDER BY p.oid''',
            '''SELECT t.oid,t.typowner,t.typacl::text FROM pg_type t
               WHERE t.typowner IN (SELECT oid FROM pg_roles WHERE rolname=ANY(%s)) ORDER BY t.oid''',
        ))
        return cac_anh + (self.conn.execute('''
            SELECT datdba,datacl::text FROM pg_database WHERE datname=current_database()
        ''').fetchall(),)

    def test_chay_lai_khong_noi_quyen(self):
        truoc = self._anh_quyen()
        for lan in (2, 3):
            with self.subTest(lan=lan):
                self.conn.execute(SQL_VAI)
                self.assertEqual(self._anh_quyen(), truoc)
        self.test_login_that_khong_ddl_hoac_set_role()

    def test_thu_hoi_public_doi_tuong_co_san_va_chay_lai(self):
        with self.conn.transaction():
            for khoi in CAC_KHOI:
                self.conn.execute(sql.SQL('GRANT SELECT ON TABLE {}.thu_bang TO PUBLIC').format(sql.Identifier(khoi)))
                self.conn.execute(sql.SQL('GRANT USAGE ON SEQUENCE {}.thu_day_so TO PUBLIC').format(sql.Identifier(khoi)))
                self.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION {}.thu_ham() TO PUBLIC').format(sql.Identifier(khoi)))
            self.conn.execute(SQL_VAI)
            self.test_default_privileges_duoi_dung_owner()
            truoc = self._anh_quyen()
            self.conn.execute(SQL_VAI)
            self.assertEqual(self._anh_quyen(), truoc)
            raise psycopg.Rollback()

    def test_chan_tien_to_khong_hop_le(self):
        truoc = self._anh_quyen()
        for tien_to in ('x\"; SELECT 1; --', 'x' * 64 + '_', 'thieu_dau_gach'):
            with self.subTest(tien_to=tien_to), self.conn.transaction():
                self.conn.execute('SELECT set_config(%s, %s, true)',
                                  ('kho_tri_thuc.tien_to_vai', tien_to))
                with self.assertRaisesRegex(psycopg.errors.RaiseException, 'tien to role khong hop le'):
                    with self.conn.transaction():
                        self.conn.execute(SQL_VAI)
                self.assertEqual(self._anh_quyen(), truoc)
                raise psycopg.Rollback()

    def test_chan_membership_owner_co_san(self):
        with self.conn.transaction():
            self.conn.execute(sql.SQL('GRANT {} TO {} WITH INHERIT TRUE, SET FALSE, ADMIN FALSE').format(
                sql.Identifier(self.cac_vai_chu[0]), sql.Identifier(self.cac_vai_chay[0])))
            with self.assertRaisesRegex(psycopg.errors.RaiseException, 'membership ngoai pham vi'):
                with self.conn.transaction():
                    self.conn.execute(SQL_VAI)
            raise psycopg.Rollback()

    def test_chan_membership_sai_thuoc_tinh(self):
        with self.conn.transaction():
            self.conn.execute(sql.SQL('GRANT {} TO {} WITH SET TRUE').format(
                sql.Identifier(self.cac_vai_chay[0]), sql.Identifier(self.dang_nhap_loi)))
            with self.assertRaisesRegex(psycopg.errors.RaiseException, 'membership PG16 sai'):
                with self.conn.transaction():
                    self.conn.execute(SQL_VAI)
            raise psycopg.Rollback()

    def test_chan_runtime_bypassrls_co_san(self):
        with self.conn.transaction():
            self.conn.execute(sql.SQL('ALTER ROLE {} BYPASSRLS').format(sql.Identifier(self.cac_vai_chay[0])))
            with self.assertRaisesRegex(psycopg.errors.RaiseException, 'thuoc tinh role sai'):
                with self.conn.transaction():
                    self.conn.execute(SQL_VAI)
            raise psycopg.Rollback()

    def test_chan_schema_sai_owner(self):
        with self.conn.transaction():
            self.conn.execute(sql.SQL('ALTER SCHEMA loi OWNER TO {}').format(sql.Identifier(self.cac_vai_chu[2])))
            with self.assertRaisesRegex(psycopg.errors.RaiseException, 'schema sai owner'):
                with self.conn.transaction():
                    self.conn.execute(SQL_VAI)
            raise psycopg.Rollback()


if __name__ == '__main__':
    unittest.main()
