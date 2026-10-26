"""XS-4b: test thuần + PG tùy chọn, chỉ KHO_PG_DSN_TEST tạo kho_test_*.

Không mở server, không xóa CSDL/vai/tệp. Fixture giả qua trigger thật.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
import re
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_module import MODULE_CONG_TAC_SQL

try:
    import psycopg
except ImportError:
    psycopg = None

DSN = os.environ.get('KHO_PG_DSN_TEST')
SQL = '\n'.join(MODULE_CONG_TAC_SQL)
TABLES = ('module_danh_muc', 'module_cong_tac', 'module_nguoi_thu')
FLAGS = ('hien_luoi', 'cho_xem', 'cho_ghi', 'cho_xuat_ngoai',
         'cong_bo_chinh_thuc', 'dai_dang_thu')


class ModuleTinh(unittest.TestCase):
    def test_registry_chi_append_khong_ghim_migration_cuoi(self):
        source = Path(PM.__file__).read_text(encoding='utf-8')
        marker = '# XS-4b — CD-017:'
        self.assertEqual(source.count(marker), 1)
        old = {'__name__': PM.__name__, '__package__': PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, 'exec'), old)
        previous = old['PG_MIGRATIONS']
        self.assertEqual(PM.PG_MIGRATIONS[:len(previous)], previous)
        self.assertIs(PM.PG_MIGRATIONS[len(previous)], MODULE_CONG_TAC_SQL)
        self.assertEqual(sum(m is MODULE_CONG_TAC_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_it_bang_va_khong_them_bang_nhat_ky(self):
        tables = re.findall(r'CREATE TABLE ([\w.]+)', SQL)
        self.assertEqual(tables, ['master.' + t for t in TABLES])
        for table in TABLES:
            self.assertIn('ALTER TABLE master.' + table + ' ENABLE ROW LEVEL SECURITY', SQL)
        self.assertIn('INSERT INTO nhat_ky.su_kien', SQL)
        self.assertIn('master.mtq_la_admin()', SQL)
        self.assertNotIn('CREATE ROLE', SQL)
        self.assertNotIn('ktt_duoc(', SQL)

    def test_ham_doc_stable_chi_doc_danh_tinh_phien(self):
        read = next(s for s in MODULE_CONG_TAC_SQL
                    if s.startswith('CREATE FUNCTION master.module_trang_thai('))
        self.assertIn('STABLE SECURITY DEFINER', read)
        self.assertIn('master.ktt_danh_tinh()', read)
        self.assertNotRegex(read, r'\b(?:INSERT|UPDATE|DELETE|PERFORM|LOCK|EXECUTE)\b')
        for flag in FLAGS:
            self.assertIn("'" + flag + "'", read)
        for function in (s for s in MODULE_CONG_TAC_SQL if s.startswith('CREATE FUNCTION')):
            self.assertIn('SET search_path = pg_catalog, master, nhat_ky, pg_temp', function)

    def test_acl_va_s5_khong_dua_vao_nhat_ky_de_mo_quyen(self):
        self.assertIn('FROM PUBLIC', SQL)
        grant = SQL.split('GRANT EXECUTE ON FUNCTION', 1)[1].split(';', 1)[0]
        self.assertNotIn('module_kiem_admin', grant)
        self.assertIn('master.module_danh_sach_nguoi_thu(text,uuid)', grant)
        self.assertNotRegex(SQL, r'GRANT (?:ALL|SELECT|INSERT|UPDATE|DELETE)')
        change = next(s for s in MODULE_CONG_TAC_SQL
                      if s.startswith('CREATE FUNCTION master.module_doi_che_do('))
        self.assertIn('MODULE_CHUA_DU_DIEU_KIEN_GO_LIVE', change)
        self.assertIn('p_revision_cu IS DISTINCT FROM rev', change)
        self.assertNotIn('FROM nhat_ky.su_kien', change)

    def test_nhat_ky_nguoi_thu_khong_ghi_ca_dong_hay_danh_tinh_nguoi_duoc_cap(self):
        for name in ('module_cap_nguoi_thu', 'module_thu_hoi_nguoi_thu'):
            function = next(s for s in MODULE_CONG_TAC_SQL
                            if s.startswith('CREATE FUNCTION master.' + name + '('))
            audit = function.split('INSERT INTO nhat_ky.su_kien', 1)[1]
            self.assertNotIn('to_jsonb', audit)
            self.assertNotIn('nguoi_dung_id', audit)
            self.assertNotIn('p_nguoi', audit)

    def test_moi_than_ham_sql_mo_dong_dollar_day_du(self):
        for statement in MODULE_CONG_TAC_SQL:
            if statement.startswith('CREATE FUNCTION'):
                self.assertEqual(statement.count('AS $$'), 1)
                self.assertEqual(statement.count('$$'), 2)
                self.assertTrue(statement.endswith('END $$'))
            elif statement.startswith('DO $$'):
                self.assertEqual(statement.count('$$'), 2)
                self.assertTrue(statement.endswith('END $$'))

    def test_utf8_khong_bom_lf_va_hang_sql_thuan(self):
        path = ROOT / 'src/kho_tri_thuc/k2/sql_module.py'
        for item in (path, Path(PM.__file__), Path(__file__)):
            raw = item.read_bytes()
            self.assertFalse(raw.startswith(b'\xef\xbb\xbf'))
            self.assertNotIn('\ufffd', raw.decode('utf-8'))
            self.assertNotIn(b'\r', raw)
        tree = ast.parse(path.read_text(encoding='utf-8'))
        self.assertEqual(ast.literal_eval(tree.body[1].value), MODULE_CONG_TAC_SQL)


@unittest.skipUnless(DSN and psycopg is not None,
                     'NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG')
class ModulePostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = 'kho_test_xs4_' + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_web') "
                          "THEN CREATE ROLE app_web NOLOGIN; END IF; END $$")
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0")
                          .format(sql.Identifier(cls.db)))
        cls.test_dsn = make_conninfo(DSN, dbname=cls.db)
        cls.c = psycopg.connect(cls.test_dsn, autocommit=True)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c)
        # Một Admin thật theo MTQ, commit riêng để kết nối READ ONLY nhìn thấy.
        # Mọi fixture từng test vẫn rollback; không xóa hoặc tắt trigger.
        with cls.c.transaction():
            login = 'MO_PHONG_XS4_ADMIN_' + uuid.uuid4().hex
            key = cls.c.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro) "
                                "VALUES ('Admin giả XS4',%s,'XEM') RETURNING id", (login,)).fetchone()[0]
            cls.admin_fixture = key, login
            cls.c.execute("SELECT master.mtq_bootstrap_admin(%s,%s,'Khởi tạo Admin giả XS4')",
                          (key, uuid.uuid4()))
            cls.c.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true),"
                          "set_config('ktt.nguoi_dung_dang_nhap',%s,true)", (str(key), login))
            cls.read_pn = cls.c.execute("INSERT INTO master.phap_nhan (ma,ten) "
                                       "VALUES (%s,'Pháp nhân chỉ đọc giả XS4') RETURNING id",
                                       (uuid.uuid4().hex,)).fetchone()[0]
            for module, cd in (('CRM', 'THU'), ('M2', 'TAT')):
                cls.c.execute('SELECT master.module_doi_che_do(%s,%s,%s,%s,0)',
                              (module, cls.read_pn, cd, 'Fixture chỉ đọc giả XS4'))

    def setUp(self):
        self.c.execute('BEGIN')
        self.addCleanup(self.c.execute, 'ROLLBACK')
        self.pn = self.phap_nhan()
        self.pn2 = self.phap_nhan()
        self.admin = self.admin_fixture
        self.tester = self.nguoi('CFO')
        self.other = self.nguoi('KE_TOAN_TRUONG')
        self.actor(self.admin)

    def phap_nhan(self):
        return self.c.execute("INSERT INTO master.phap_nhan (ma,ten) "
                              "VALUES (%s,'Pháp nhân giả XS4') RETURNING id",
                              (uuid.uuid4().hex,)).fetchone()[0]

    def nguoi(self, role):
        login = 'MO_PHONG_XS4_' + uuid.uuid4().hex
        key = self.c.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro) "
                             "VALUES ('Người giả XS4',%s,%s) RETURNING id", (login, role)).fetchone()[0]
        return key, login

    def actor(self, actor):
        self.c.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true),"
                       "set_config('ktt.nguoi_dung_dang_nhap',%s,true)", (str(actor[0]), actor[1]))

    def doc(self, module='CRM', pn=None):
        return self.c.execute('SELECT master.module_trang_thai(%s,%s)',
                              (module, self.pn if pn is None else pn)).fetchone()[0]

    def doi(self, cd, rev=0, module='CRM', pn=None, reason='Đổi công tắc giả XS4'):
        return self.c.execute('SELECT master.module_doi_che_do(%s,%s,%s,%s,%s)',
                              (module, self.pn if pn is None else pn, cd, reason, rev)).fetchone()[0]

    def cap(self, reason='Cấp thử giả XS4', pn=None):
        return self.c.execute('SELECT master.module_cap_nguoi_thu(%s,%s,%s,%s)',
                              ('CRM', self.pn if pn is None else pn, self.tester[0], reason)).fetchone()[0]

    def thu_hoi(self, reason='Thu hồi thử giả XS4'):
        return self.c.execute('SELECT master.module_thu_hoi_nguoi_thu(%s,%s,%s,%s)',
                              ('CRM', self.pn, self.tester[0], reason)).fetchone()[0]

    def danh_sach(self, module='CRM', pn=None):
        return self.c.execute('SELECT to_jsonb(t) FROM master.module_danh_sach_nguoi_thu(%s,%s) t',
                              (module, self.pn if pn is None else pn)).fetchall()

    def loi(self, code, fn):
        with self.assertRaises(psycopg.Error) as cm:
            with self.c.transaction():
                fn()
        self.assertIn(code, str(cm.exception))

    def co(self, result, cd, flags):
        self.assertEqual(result['che_do'], cd)
        self.assertEqual(set(result), {'che_do', 'revision', *FLAGS})
        self.assertEqual(tuple(result[f] for f in FLAGS), flags)
        self.assertTrue(all(type(result[f]) is bool for f in FLAGS))

    def test_mac_dinh_s3_tung_ma_va_ma_chua_khai_bao(self):
        self.c.execute('SET LOCAL ROLE app_web')
        for ma in ('CRM', 'M2', 'M4', 'M0', 'M3', 'M9', 'M10', 'CHUA_KHAI_BAO'):
            with self.subTest(module=ma):
                van_hanh = ma in ('CRM', 'M2', 'M4', 'M0')
                result = self.doc(ma)
                self.co(result, 'VAN_HANH' if van_hanh else 'TAT',
                        (True,) * 6 if van_hanh else (False, True, False, False, False, False))
                self.assertEqual(result['revision'], 0)

    def test_ba_che_do_nhan_ba_danh_tinh_dung_tung_co(self):
        self.cap()
        self.c.execute('SET LOCAL ROLE app_web')
        rev = 0
        for cd in ('TAT', 'THU', 'VAN_HANH'):
            self.actor(self.admin)
            rev = self.doi(cd, rev)
            for actor in (self.admin, self.tester, self.other):
                with self.subTest(che_do=cd, actor=actor[1]):
                    self.actor(actor)
                    expected = ((True,) * 6 if cd == 'VAN_HANH' else
                                (False, True, False, False, False, False) if cd == 'TAT' else
                                (False,) * 6 if actor == self.other else
                                (True, True, True, False, False, True))
                    self.co(self.doc(), cd, expected)
                    self.assertEqual(self.doc()['revision'], rev)

    def test_chi_admin_ca_ba_ham_ghi_va_danh_tinh_gia(self):
        self.c.execute('SET LOCAL ROLE app_web')
        for actor in (self.tester, self.other, (self.admin[0], self.other[1]),
                      ('', '')):
            self.actor(actor)
            for fn in (lambda: self.doi('THU'), self.cap, self.thu_hoi):
                self.loi('MODULE_CHI_ADMIN', fn)
            self.assertEqual(self.doc()['revision'], 0)

    def test_ly_do_revision_va_dau_vao_bi_chan_khong_ghi_nhat_ky(self):
        self.c.execute('SET LOCAL ROLE app_web')
        for reason in (None, '', '   '):
            for fn in (lambda: self.doi('THU', reason=reason),
                       lambda: self.cap(reason), lambda: self.thu_hoi(reason)):
                self.loi('MODULE_CAN_LY_DO', fn)
        for revision in (None, -1, 1):
            self.loi('MODULE_REVISION', lambda: self.doi('THU', revision))
        self.loi('MODULE_CHE_DO', lambda: self.doi('SAI'))
        self.loi('MODULE_CHE_DO', lambda: self.doi(None))
        self.loi('MODULE_DAU_VAO', lambda: self.doi('THU', module='CHUA_KHAI_BAO'))
        self.loi('MODULE_DAU_VAO', lambda: self.doi('THU', pn=uuid.uuid4()))
        self.assertEqual(self.doi('THU'), 1)
        self.loi('MODULE_REVISION', lambda: self.doi('TAT', 0))
        self.c.execute('RESET ROLE')
        self.assertEqual(len(self.audit()), 1)

    def test_s5_m9_thu_khong_go_live_crm_khoi_phuc(self):
        self.c.execute('SET LOCAL ROLE app_web')
        self.loi('MODULE_CHUA_DU_DIEU_KIEN_GO_LIVE', lambda: self.doi('VAN_HANH', module='M9'))
        self.assertEqual(self.doi('THU', module='M9'), 1)
        self.loi('MODULE_CHUA_DU_DIEU_KIEN_GO_LIVE',
                 lambda: self.doi('VAN_HANH', 1, module='M9'))
        self.assertEqual(self.doc('M9')['revision'], 1)
        self.assertEqual(self.doi('TAT'), 1)
        self.assertEqual(self.doi('VAN_HANH', 1), 2)

    def test_s5_lich_su_van_hanh_cung_pn_khong_muon_pn_khac(self):
        # Mô phỏng dữ liệu lịch sử do migration tin cậy đưa vào, không tắt trigger.
        self.c.execute("INSERT INTO master.module_cong_tac "
                       "(module,phap_nhan_id,che_do,revision,da_van_hanh,ly_do,doi_boi) "
                       "VALUES ('M9',%s,'TAT',1,true,'Lịch sử giả đã vận hành',%s)",
                       (self.pn, self.admin[0]))
        self.c.execute('SET LOCAL ROLE app_web')
        self.assertEqual(self.doi('VAN_HANH', 1, module='M9'), 2)
        self.loi('MODULE_CHUA_DU_DIEU_KIEN_GO_LIVE',
                 lambda: self.doi('VAN_HANH', module='M9', pn=self.pn2))

    def audit(self):
        return self.c.execute("SELECT nguoi,luc,hanh_dong,truoc,sau,ly_do,phap_nhan_id "
                              "FROM nhat_ky.su_kien WHERE phap_nhan_id=%s "
                              "AND doi_tuong_bang IN ('master.module_cong_tac','master.module_nguoi_thu') "
                              "ORDER BY id", (self.pn,)).fetchall()

    def test_nhat_ky_day_du_cap_thu_hoi_cap_lai_khong_xoa_dong(self):
        self.c.execute('SET LOCAL ROLE app_web')
        self.doi('THU')
        key = self.cap()
        self.assertEqual(self.thu_hoi(), key)
        new_key = self.cap()
        self.assertNotEqual(key, new_key)
        self.doi('TAT', 1)
        self.c.execute('RESET ROLE')
        rows = self.audit()
        self.assertEqual([r[2] for r in rows], ['MODULE_DOI_CHE_DO', 'MODULE_CAP_NGUOI_THU',
                         'MODULE_THU_HOI_NGUOI_THU', 'MODULE_CAP_NGUOI_THU', 'MODULE_DOI_CHE_DO'])
        for actor, luc, action, before, after, reason, pn in rows:
            self.assertEqual(actor, str(self.admin[0]))
            self.assertIsNotNone(luc)
            self.assertTrue(reason.strip())
            self.assertEqual(pn, self.pn)
            self.assertEqual(after['module'], 'CRM')
            self.assertEqual(after['phap_nhan_id'], str(self.pn))
        self.assertEqual(rows[0][3]['che_do'], 'VAN_HANH')
        self.assertEqual(rows[0][4]['che_do'], 'THU')
        self.assertEqual(rows[-1][3]['che_do'], 'THU')
        self.assertEqual(rows[-1][4]['che_do'], 'TAT')
        for row, row_id, action in ((rows[1], key, 'CAP'), (rows[2], key, 'THU_HOI'),
                                    (rows[3], new_key, 'CAP')):
            self.assertIsNone(row[3])
            self.assertEqual(row[4], {'id': str(row_id), 'module': 'CRM',
                                     'phap_nhan_id': str(self.pn), 'hanh_dong': action,
                                     'ly_do': row[5], 'nguoi_thuc_hien': str(self.admin[0])})
        history = self.c.execute('SELECT count(*),count(thu_hoi_luc) FROM master.module_nguoi_thu '
                                 'WHERE module=%s AND phap_nhan_id=%s', ('CRM', self.pn)).fetchone()
        self.assertEqual(history, (2, 1))

    def test_app_web_khong_admin_doc_nhat_ky_khong_lo_nguoi_duoc_cap(self):
        self.c.execute('INSERT INTO master.phan_quyen (nguoi_dung_id,phap_nhan_id) VALUES (%s,%s)',
                       (self.other[0], self.pn))
        self.c.execute('SET LOCAL ROLE app_web')
        key = self.cap()
        self.assertEqual(self.thu_hoi(), key)
        self.actor(self.other)
        self.loi('MODULE_CHI_ADMIN', self.danh_sach)
        rows = self.c.execute("SELECT to_jsonb(s) FROM nhat_ky.su_kien s "
                              "WHERE phap_nhan_id=%s AND doi_tuong_bang='master.module_nguoi_thu'",
                              (self.pn,)).fetchall()
        self.assertEqual(len(rows), 2)  # Thực sự đọc được nhật ký qua RLS, không xanh vì rỗng.
        self.assertEqual({r[0]['hanh_dong'] for r in rows},
                         {'MODULE_CAP_NGUOI_THU', 'MODULE_THU_HOI_NGUOI_THU'})
        for (row,) in rows:
            self.assertEqual(row['doi_tuong_id'], str(key))
            self.assertIsNone(row['truoc'])
            self.assertEqual(set(row['sau']),
                             {'id', 'module', 'phap_nhan_id', 'hanh_dong', 'ly_do', 'nguoi_thuc_hien'})
            self.assertNotIn(str(self.tester[0]), str(row))
            self.assertNotIn('nguoi_dung_id', str(row))

    def test_danh_sach_admin_dung_module_pn_va_lich_su_khong_ghi_nhat_ky(self):
        self.c.execute('SET LOCAL ROLE app_web')
        key = self.cap()
        self.thu_hoi()
        new_key = self.cap()
        other_pn_key = self.cap(pn=self.pn2)
        self.c.execute("SELECT master.module_cap_nguoi_thu('M9',%s,%s,'Thử module khác')",
                       (self.pn, self.other[0]))
        self.c.execute('RESET ROLE')
        before = len(self.audit())
        self.c.execute('SET LOCAL ROLE app_web')
        rows = [r[0] for r in self.danh_sach()]
        self.assertEqual([r['id'] for r in rows], [str(key), str(new_key)])
        for row in rows:
            self.assertEqual(row['nguoi_dung_id'], str(self.tester[0]))
            self.assertEqual(row['module'], 'CRM')
            self.assertEqual(row['phap_nhan_id'], str(self.pn))
            self.assertEqual(row['cap_boi'], str(self.admin[0]))
        self.assertIsNotNone(rows[0]['thu_hoi_luc'])
        self.assertEqual(rows[0]['thu_hoi_boi'], str(self.admin[0]))
        self.assertIsNone(rows[1]['thu_hoi_luc'])
        self.assertEqual([r[0]['id'] for r in self.danh_sach(pn=self.pn2)], [str(other_pn_key)])
        self.assertEqual([r[0]['nguoi_dung_id'] for r in self.danh_sach('M9')], [str(self.other[0])])
        self.assertEqual(self.danh_sach('M10'), [])
        self.loi('MODULE_DAU_VAO', lambda: self.danh_sach('CHUA_KHAI_BAO'))
        self.loi('MODULE_DAU_VAO', lambda: self.danh_sach(pn=uuid.uuid4()))
        self.c.execute('RESET ROLE')
        self.assertEqual(len(self.audit()), before)

    def test_danh_sach_chan_khong_admin_va_danh_tinh_gia_ke_ca_khi_rong(self):
        self.c.execute('SET LOCAL ROLE app_web')
        for actor in (self.tester, self.other, (self.admin[0], self.other[1]), ('', '')):
            self.actor(actor)
            for module in ('CRM', 'CHUA_KHAI_BAO'):
                self.loi('MODULE_CHI_ADMIN', lambda: self.danh_sach(module))
        self.actor(self.admin)
        self.assertEqual(self.danh_sach(), [])
        self.cap()
        self.actor(self.tester)
        self.loi('MODULE_CHI_ADMIN', self.danh_sach)

    def test_danh_sach_chan_admin_vua_bi_thu_hoi(self):
        from psycopg.types.json import Jsonb

        grant = self.c.execute("SELECT master.mtq_cau_hinh_ghi(%s,'ADMIN',%s,0,'Admin giả tạm thời')",
                               (uuid.uuid4(), Jsonb({'nguoi_dung_id': str(self.other[0])}))).fetchone()[0]
        self.cap()
        self.c.execute('SET LOCAL ROLE app_web')
        self.actor(self.other)
        self.assertEqual(self.danh_sach()[0][0]['nguoi_dung_id'], str(self.tester[0]))
        self.c.execute('RESET ROLE')
        self.actor(self.admin)
        self.c.execute("SELECT master.mtq_cau_hinh_ghi(%s,'THU_HOI_ADMIN',%s,%s,'Thu hồi Admin giả')",
                       (uuid.uuid4(), Jsonb({'id': grant['id']}), grant['revision']))
        self.c.execute('SET LOCAL ROLE app_web')
        self.actor(self.other)
        self.loi('MODULE_CHI_ADMIN', self.danh_sach)

    def test_thu_hoi_mat_quyen_phap_nhan_b_doc_lap(self):
        self.c.execute('SET LOCAL ROLE app_web')
        self.doi('THU')
        self.doi('THU', pn=self.pn2)
        self.cap()
        self.actor(self.tester)
        self.assertTrue(self.doc()['hien_luoi'])
        self.co(self.doc(pn=self.pn2), 'THU', (False,) * 6)
        self.actor(self.admin)
        self.thu_hoi()
        self.actor(self.tester)
        self.co(self.doc(), 'THU', (False,) * 6)
        self.actor(self.admin)
        self.doi('TAT', 1)
        self.assertEqual(self.doc(pn=self.pn2)['che_do'], 'THU')
        self.assertEqual(self.doc(pn=self.pn2)['revision'], 1)

    def test_app_web_khong_doc_bang_khong_dml_khong_goi_helper(self):
        self.c.execute('SET LOCAL ROLE app_web')
        for table in TABLES:
            for statement in ('SELECT * FROM master.' + table,
                              'INSERT INTO master.' + table + ' DEFAULT VALUES',
                              'UPDATE master.' + table + ' SET module=module' if table != 'module_danh_muc'
                              else 'UPDATE master.module_danh_muc SET ma=ma',
                              'DELETE FROM master.' + table, 'TRUNCATE master.' + table):
                self.loi('permission denied', lambda: self.c.execute(statement))
        self.loi('permission denied', lambda: self.c.execute(
            "SELECT master.module_kiem_admin('CRM',%s,'Không cấp helper')", (self.pn,)))
        self.assertEqual(self.doc()['che_do'], 'VAN_HANH')

    def test_doc_trong_read_only_khong_ghi_nhat_ky(self):
        before = self.c.execute('SELECT count(*) FROM nhat_ky.su_kien').fetchone()[0]
        with psycopg.connect(self.test_dsn, autocommit=True) as read:
            read.execute('BEGIN READ ONLY')
            try:
                read.execute('SET LOCAL ROLE app_web')
                read.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true),"
                             "set_config('ktt.nguoi_dung_dang_nhap',%s,true)",
                             (str(self.admin[0]), self.admin[1]))
                for module, cd, flags in (
                    ('CRM', 'THU', (True, True, True, False, False, True)),
                    ('M2', 'TAT', (False, True, False, False, False, False)),
                    ('M4', 'VAN_HANH', (True,) * 6),
                ):
                    result = read.execute('SELECT master.module_trang_thai(%s,%s)',
                                          (module, self.read_pn)).fetchone()[0]
                    self.co(result, cd, flags)
            finally:
                read.execute('ROLLBACK')
        self.assertEqual(self.c.execute('SELECT count(*) FROM nhat_ky.su_kien').fetchone()[0], before)


if __name__ == '__main__':
    unittest.main()
