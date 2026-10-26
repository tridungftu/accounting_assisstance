"""XS-T1a: hợp đồng đọc hóa đơn; PG chỉ tạo kho_test_*, giữ mọi bằng chứng.

Fixture nhận XML giả qua HoaDonK2/trigger thật. Mọi lệnh gọi hợp đồng dùng
current_user=app_web và danh tính phiên, kể cả READ ONLY. Không server/DEMO.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_cong_bo_hoa_don import CONG_BO_HOA_DON_SQL

try:
    import psycopg
except ImportError:
    psycopg = None

DSN = os.environ.get('KHO_PG_DSN_TEST')
FUNCTION = 'master.hoa_don_cong_bo(uuid,uuid[])'
TABLES = ('hoa_don_danh_tinh', 'hoa_don_phien_ban', 'hoa_don_quan_sat',
          'hoa_don_dong_danh_tinh', 'hoa_don_dong_phien_ban')


class CongBoTinh(unittest.TestCase):
    def test_migration_append_khong_ghim_cuoi(self):
        source = Path(PM.__file__).read_text(encoding='utf-8')
        marker = '# XS-T1a — CD-017:'
        self.assertEqual(source.count(marker), 1)
        previous = {'__name__': PM.__name__, '__package__': PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, 'exec'), previous)
        old = previous['PG_MIGRATIONS']
        self.assertEqual(PM.PG_MIGRATIONS[:len(old)], old)
        self.assertIs(PM.PG_MIGRATIONS[len(old)], CONG_BO_HOA_DON_SQL)
        self.assertEqual(sum(m is CONG_BO_HOA_DON_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_chi_doc_khong_mo_quyen_bang_khong_tra_raw(self):
        source = '\n'.join(CONG_BO_HOA_DON_SQL)
        function = CONG_BO_HOA_DON_SQL[0]
        self.assertIn('STABLE SECURITY DEFINER', function)
        self.assertIn('SET search_path = pg_catalog, master, kho, giao_tiep, pg_temp', function)
        self.assertNotRegex(source, r'\b(?:INSERT|UPDATE|DELETE|CREATE TABLE|ALTER TABLE|LOCK|EXECUTE format)\b')
        self.assertNotRegex(source, r'GRANT\s+(?:ALL|SELECT|INSERT|UPDATE|DELETE)\b')
        self.assertIn('REVOKE ALL ON FUNCTION ' + FUNCTION + ' FROM PUBLIC', source)
        self.assertIn('GRANT EXECUTE ON FUNCTION ' + FUNCTION + ' TO app_web', source)
        self.assertNotIn('jsonb_build_object(\'raw_header_states\'', function)
        self.assertNotIn('raw_components', function)
        self.assertNotIn('hoa_don_dong_', function)
        self.assertNotIn('ban_ghi_nguon', function)

    def test_dollar_va_utf8_khong_bom(self):
        for statement in CONG_BO_HOA_DON_SQL:
            if statement.startswith('CREATE FUNCTION'):
                self.assertEqual(statement.count('AS $$'), 1)
                self.assertEqual(statement.count('$$'), 2)
                self.assertTrue(statement.endswith('END $$'))
            elif statement.startswith('DO $$'):
                self.assertEqual(statement.count('$$'), 2)
                self.assertTrue(statement.endswith('END $$'))
        path = ROOT / 'src/kho_tri_thuc/k2/sql_cong_bo_hoa_don.py'
        for item in (path, Path(PM.__file__), Path(__file__)):
            raw = item.read_bytes()
            self.assertFalse(raw.startswith(b'\xef\xbb\xbf'))
            self.assertNotIn('\ufffd', raw.decode('utf-8'))
        tree = ast.parse(path.read_text(encoding='utf-8'))
        self.assertEqual(ast.literal_eval(tree.body[1].value), CONG_BO_HOA_DON_SQL)


@unittest.skipUnless(DSN and psycopg is not None,
                     'NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG')
class CongBoPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from psycopg.rows import dict_row
        from kho_tri_thuc.ha_tang import postgres
        from kho_tri_thuc.k2 import m2_demo
        from kho_tri_thuc.k2.hoa_don import HoaDonK2

        cls.db = 'kho_test_xst1_' + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_web') "
                          "THEN CREATE ROLE app_web NOLOGIN NOINHERIT; END IF; END $$")
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0")
                          .format(sql.Identifier(cls.db)))
        cls.dsn = make_conninfo(DSN, dbname=cls.db)
        cls.c = psycopg.connect(cls.dsn, autocommit=True)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c)
        cls.pn = {}
        for suffix in ('A', 'B', 'C'):
            cls.pn[suffix] = cls.c.execute(
                "INSERT INTO master.phap_nhan (ma,ten) VALUES (%s,%s) RETURNING id",
                ('PN_DEMO_' + suffix, 'Pháp nhân giả XS-T1 ' + suffix)).fetchone()[0]
        m2_demo.khoi_tao(cls.c)
        cls.reader = cls.nguoi('KE_TOAN', ('A', 'B', 'C'), ['M2', 'M4'])
        cls.reader_a = cls.nguoi('XEM', ('A',), ['M2'])
        cls.no_m2 = cls.nguoi('KE_TOAN', ('A',), ['M4'])
        cls.admin_actor = cls.nguoi('XEM', (), [])
        cls.c.execute("SELECT master.mtq_bootstrap_admin(%s,%s,'Admin giả XS-T1')",
                      (cls.admin_actor[0], uuid.uuid4()))

        cls.app = psycopg.connect(cls.dsn, autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(cls.app.close)
        cls.app.execute('SET ROLE app_web')
        # C=Tắt committed để kiểm CHO trong READ ONLY, không làm thay đổi
        # revision công tắc A/B giữa các test (A/B luôn rollback).
        with cls.app.transaction():
            cls.app.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true),"
                            "set_config('ktt.nguoi_dung_dang_nhap',%s,true)",
                            (str(cls.admin_actor[0]), cls.admin_actor[1]))
            cls.app.execute("SELECT master.module_doi_che_do('M2',%s,'TAT','Chờ giả XS-T1',0)",
                            (cls.pn['C'],))
        owner = psycopg.connect(cls.dsn, autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(owner.close)
        # mkdtemp không tự xóa: tương thích guard giữ tệp/bằng chứng.
        cls.root = Path(tempfile.mkdtemp(prefix='kho_test_xst1_'))
        service = HoaDonK2(cls.app, cls.root, conn_chu=owner)
        fixtures = ROOT / 'tests/fixtures/m2_invoice_xml/inputs'
        raw_a = (fixtures / 'G01-wrapped-positive.xml').read_bytes()
        raw_b = (fixtures / 'G04-purchase-b-padded.xml').read_bytes()
        # A: v1 → v2 → tái xuất hiện v1. Hiện hành khác max(version), giữ HOLD.
        changed = raw_a.replace(b'DEMO hang A', b'DEMO hang A phien ban hai')
        if changed == raw_a:
            raise AssertionError('Fixture XML giả không còn mô tả dự kiến')
        for index, (raw, coverage) in enumerate((
                (raw_a, 'COMPLETE_INPUT'), (changed, 'COMPLETE_INPUT'),
                (raw_a, 'PARTIAL_INPUT'), (raw_b, 'COMPLETE_INPUT'))):
            service.nhan('MO_PHONG_M0_HD_INTAKE',
                         source_instance='DEMO_M2_XML_INSTANCE_A',
                         scope_ref='DEMO_M2_SCOPE_BOTH_COMPANIES_V1', coverage=coverage,
                         native=raw, client_key='xst1-fixture-' + str(index))
        cls.hd = {}
        for suffix in ('A', 'B'):
            ids = cls.c.execute('SELECT id FROM kho.hoa_don_danh_tinh WHERE phap_nhan_id=%s',
                               (cls.pn[suffix],)).fetchall()
            if len(ids) != 1:
                raise AssertionError('Cần đúng một hóa đơn giả mỗi PN')
            cls.hd[suffix] = ids[0][0]
        # ACL legacy M0015 đã có SELECT. Chỉ thu hồi trong DB test để chứng minh
        # gateway không cần SELECT nguồn; migration XS-T1a không đổi ACL bảng.
        for table in TABLES:
            cls.c.execute(sql.SQL('REVOKE SELECT ON kho.{} FROM app_web')
                          .format(sql.Identifier(table)))

    @classmethod
    def nguoi(cls, role, suffixes, modules):
        login = 'MO_PHONG_XST1_' + uuid.uuid4().hex
        key = cls.c.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro,mo_phong) "
                            "VALUES ('Người giả XS-T1',%s,%s,true) RETURNING id",
                            (login, role)).fetchone()[0]
        for suffix in suffixes:
            cls.c.execute('INSERT INTO master.phan_quyen (nguoi_dung_id,phap_nhan_id,module) '
                          'VALUES (%s,%s,%s)', (key, cls.pn[suffix], modules))
        return key, login

    def setUp(self):
        self.app.execute('BEGIN')
        self.addCleanup(self.app.execute, 'ROLLBACK')
        self.actor(self.reader)
        self.assertEqual(self.app.execute('SELECT current_user AS role').fetchone()['role'], 'app_web')

    def actor(self, actor):
        self.app.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true),"
                         "set_config('ktt.nguoi_dung_dang_nhap',%s,true)", (str(actor[0]), actor[1]))

    def doc(self, suffix='A', ids=None):
        return self.app.execute('SELECT master.hoa_don_cong_bo(%s,%s::uuid[]) AS result',
                                (self.pn[suffix], [self.hd[suffix]] if ids is None else ids)).fetchone()['result']

    def cho(self, result):
        self.assertEqual(result['trang_thai'], 'CHO')
        self.assertEqual(result['ly_do'], 'Chờ hóa đơn mua vào')
        self.assertEqual(result['hoa_don'], [])
        self.assertEqual(set(result), {'contract', 'phap_nhan_id', 'trang_thai', 'ly_do', 'hoa_don'})

    def doi(self, mode, revision):
        self.actor(self.admin_actor)
        result = self.app.execute(
            "SELECT master.module_doi_che_do('M2',%s,%s,'Công tắc giả XS-T1',%s) AS rev",
            (self.pn['A'], mode, revision)).fetchone()['rev']
        self.actor(self.reader)
        return result

    def test_van_hanh_dung_truong_hash_on_dinh_giu_null(self):
        result = self.doc()
        self.assertEqual(result, self.doc(ids=[self.hd['A'], self.hd['A']]))
        self.assertEqual(result['contract'], 'm2-hoa-don-cong-bo/v1')
        self.assertEqual(result['trang_thai'], 'CO_DU_LIEU')
        self.assertIsNone(result['ly_do'])
        self.assertEqual(len(result['hoa_don']), 1)
        row = result['hoa_don'][0]
        expected = self.c.execute(
            'SELECT v.id,v.phien_ban,v.semantic_sha256,v.raw_header_states,'
            'v.ngay_lap,v.tien_te,v.total_minor,o.id,o.classification,l.coverage,l.coverage_hieu_luc '
            'FROM kho.hoa_don_danh_tinh d JOIN kho.hoa_don_quan_sat o ON o.id=d.latest_observation_id '
            'JOIN kho.hoa_don_phien_ban v ON v.id=o.phien_ban_id '
            'JOIN giao_tiep.lan_tiep_nhan_nguon l ON l.id=o.lan_tiep_nhan_id WHERE d.id=%s',
            (self.hd['A'],)).fetchone()
        self.assertEqual((row['hoa_don_id'], row['phap_nhan_id']), (str(self.hd['A']), str(self.pn['A'])))
        self.assertEqual((row['phien_ban_id'], row['phien_ban'], row['semantic_sha256']),
                         (str(expected[0]), expected[1], expected[2]))
        self.assertRegex(row['semantic_sha256'], r'^[0-9a-f]{64}$')
        self.assertEqual(row['so_hoa_don'], expected[3]['SHDon'])
        self.assertEqual((row['so_chuan'], row['ky_hieu'], row['mau_so']), ('1', 'DEMO_SERIES_A', '1'))
        self.assertEqual((row['mst_ban'], row['mst_mua']), ('DEMO_M2_SUPPLIER', 'DEMO_M2_COMPANY_A'))
        self.assertEqual((row['ngay_lap'], row['tien_te']), (expected[4].isoformat(), expected[5]))
        self.assertEqual(row['tong_tien'], expected[3].get('TgTTTBSo'))
        self.assertEqual(row['total_minor'], expected[6])
        self.assertIsNone(row['tong_tien'])  # nguồn M2 hiện tại chưa lưu tổng tiền
        self.assertIsNone(row['total_minor'])
        self.assertEqual(row['money_basis_state'], 'UNPROVEN_NO_MINOR')
        self.assertEqual(row['trang_thai_nguon']['quan_sat_id'], str(expected[7]))
        self.assertEqual(row['trang_thai_nguon']['classification'], expected[8])
        self.assertEqual((row['coverage'], row['coverage_hieu_luc']), expected[9:11])
        self.assertEqual(row['coverage_hieu_luc'], 'PARTIAL_INPUT')
        self.assertEqual(row['period_completeness'], 'UNKNOWN')
        self.assertEqual(row['trang_thai_nguon']['native_fiscal_status'], 'UNKNOWN')
        self.assertEqual(set(row), {
            'hoa_don_id', 'phap_nhan_id', 'phien_ban_id', 'phien_ban', 'semantic_contract',
            'semantic_sha256', 'so_chuan', 'so_hoa_don', 'mau_so', 'ky_hieu', 'ngay_lap',
            'mst_ban', 'mst_mua', 'tien_te', 'tong_tien', 'total_minor', 'money_basis_state',
            'trang_thai_nguon', 'coverage', 'coverage_hieu_luc', 'period_completeness'})

    def test_phien_ban_theo_quan_sat_hien_hanh_khong_lay_max(self):
        highest = self.c.execute('SELECT max(phien_ban) FROM kho.hoa_don_phien_ban WHERE hoa_don_id=%s',
                                 (self.hd['A'],)).fetchone()[0]
        row = self.doc()['hoa_don'][0]
        self.assertEqual((row['phien_ban'], highest), (1, 2))
        self.assertIn('ANCESTOR_REAPPEARANCE_HOLD', row['trang_thai_nguon']['classification'])
        self.assertIsNone(row['trang_thai_nguon']['eligible_content_id'])

    def test_tat_thu_a_cho_b_khong_doi_bat_lai_khong_nhan_doi(self):
        before_a, before_b = self.doc(), self.doc('B')
        rev = 0
        for mode in ('TAT', 'THU', 'VAN_HANH'):
            rev = self.doi(mode, rev)
            if mode == 'VAN_HANH':
                self.assertEqual(self.doc(), before_a)
            else:
                self.cho(self.doc())
                if mode == 'THU':
                    self.actor(self.admin_actor)
                    self.app.execute("SELECT master.module_cap_nguoi_thu('M2',%s,%s,'Người thử giả XS-T1')",
                                     (self.pn['A'], self.reader[0]))
                    self.actor(self.reader)
                    flags = self.app.execute("SELECT master.module_trang_thai('M2',%s) AS result",
                                             (self.pn['A'],)).fetchone()['result']
                    self.assertTrue(flags['hien_luoi'])
                    self.assertFalse(flags['cong_bo_chinh_thuc'])
                    self.cho(self.doc())
            self.assertEqual(self.doc('B'), before_b)

    def test_sai_pn_mat_quyen_khong_gia_thanh_cho(self):
        self.actor(self.reader_a)
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with self.app.transaction():
                self.doc('B')
        self.cho(self.doc(ids=[self.hd['B']]))  # ID thuộc B không lộ qua PN A
        self.assertEqual(self.doc(ids=[self.hd['A'], self.hd['B']])['hoa_don'], self.doc()['hoa_don'])
        self.actor(self.no_m2)
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with self.app.transaction():
                self.doc()
        self.doi('TAT', 0)
        self.actor(self.no_m2)
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with self.app.transaction():
                self.doc()

    def test_khong_select_duoc_bang_nguon_nhung_goi_duoc_cong_bo(self):
        from psycopg import sql
        for table in TABLES:
            with self.subTest(table=table):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with self.app.transaction():
                        self.app.execute(sql.SQL('SELECT * FROM kho.{} LIMIT 1').format(sql.Identifier(table)))
        self.assertEqual(self.doc()['trang_thai'], 'CO_DU_LIEU')
        props = self.c.execute(
            "SELECT p.prosecdef,p.provolatile,p.proconfig,has_function_privilege('app_web',p.oid,'EXECUTE'),"
            "NOT EXISTS (SELECT 1 FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a "
            "WHERE a.grantee=0 AND a.privilege_type='EXECUTE') "
            "FROM pg_proc p WHERE p.oid=%s::regprocedure", (FUNCTION,)).fetchone()
        self.assertEqual((props[0], props[1], props[3], props[4]), (True, 's', True, True))
        self.assertIn('search_path=pg_catalog, master, kho, giao_tiep, pg_temp', props[2])

    def test_read_only_van_hanh_va_cho(self):
        expected = self.doc()
        self.app.execute('ROLLBACK')
        self.app.execute('BEGIN READ ONLY')
        self.actor(self.reader)
        self.assertEqual(self.doc(), expected)
        self.cho(self.doc('C', ids=[]))

    def test_thieu_id_khong_tra_hoa_don_khac(self):
        self.cho(self.doc(ids=[]))
        self.cho(self.doc(ids=[uuid.uuid4()]))
        for ids in (None, [None]):
            with self.subTest(ids=ids):
                with self.assertRaises(psycopg.errors.InvalidParameterValue):
                    with self.app.transaction():
                        self.app.execute('SELECT master.hoa_don_cong_bo(%s,%s::uuid[])',
                                         (self.pn['A'], ids))


if __name__ == '__main__':
    unittest.main()
