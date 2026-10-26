"""M3-1a: SQL tĩnh và PG trên CSDL kho_test_* riêng, chỉ dữ liệu DEMO.

Không có KHO_PG_DSN_TEST/psycopg thì skip PG, không mở dịch vụ.
M2 chưa promote BAN_RA: chỉ thử candidate/FK/guard, không giả bản bán hợp lệ.
M3-1c kiểm riêng trigger và SELECT trên bảng tạm không có FK/trigger nguồn;
đây là test SQL cô lập, không phải xác minh luồng bán ra đầu-cuối của M2.
"""

from __future__ import annotations

import ast
from decimal import Decimal
import os
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
import uuid

from kho_tri_thuc.ha_tang import postgres as pg
from kho_tri_thuc.ha_tang import pg_migrations as registry
from kho_tri_thuc.k2.m3 import M3K2, tinh_ba_dang_thuc
from kho_tri_thuc.k2.sql_m3 import M3_CO_SO_SQL, M3_CO_SO_B_SQL, M3_CO_SO_C_SQL
from tests.test_m3_dang_thuc import demo

try:
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
except ImportError:
    psycopg = None


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'src/kho_tri_thuc/k2/sql_m3.py'
REGISTRY = ROOT / 'src/kho_tri_thuc/ha_tang/pg_migrations.py'
DDL = '\n'.join(M3_CO_SO_SQL)
TABLES = ('hop_dong_co_so', 'hoa_don_hop_dong', 'policy_hinh_thuc_doanh_thu')
ADMIN_DSN = os.environ.get('KHO_PG_DSN_TEST')


def migration_b_index():
    tail = REGISTRY.read_text(encoding='utf-8').split('# M3-1c — CD-013:', 1)[1]
    name = re.search(r'^(\w+_M3_CO_SO_B) = M3_CO_SO_B_SQL$', tail, re.MULTILINE).group(1)
    migration = getattr(registry, name)
    return next(i for i, m in enumerate(registry.PG_MIGRATIONS) if m is migration)


def migration_c_index():
    tail = REGISTRY.read_text(encoding='utf-8').split('# M3-1d — CD-013:', 1)[1]
    name = re.search(r'^(\w+_M3_CO_SO_C) = M3_CO_SO_C_SQL$', tail, re.MULTILINE).group(1)
    migration = getattr(registry, name)
    return next(i for i, m in enumerate(registry.PG_MIGRATIONS) if m is migration)


class M3SqlTinh(unittest.TestCase):
    def test_module_chi_hang_sql_literal(self):
        tree = ast.parse(MODULE.read_text(encoding='utf-8'))
        self.assertIsInstance(tree.body[0], ast.Expr)  # docstring
        constants = {}
        for assignment in tree.body[1:]:
            self.assertIsInstance(assignment, ast.Assign)
            self.assertEqual(len(assignment.targets), 1)
            constants[assignment.targets[0].id] = ast.literal_eval(assignment.value)
        self.assertEqual(constants, {'M3_CO_SO_SQL': M3_CO_SO_SQL, 'M3_CO_SO_B_SQL': M3_CO_SO_B_SQL,
                                     'M3_CO_SO_C_SQL': M3_CO_SO_C_SQL})
        self.assertTrue(all(isinstance(s, str) and s.strip() for statements in constants.values() for s in statements))

    def test_khong_co_cot_hay_literal_so_hach_toan(self):
        self.assertNotIn('tài khoản', DDL.lower())
        self.assertNotIn('tai_khoan', DDL.lower())
        self.assertNotRegex(DDL.lower(), r'\b(?:acct|account|tk_\w*)\b')
        table_ddl = '\n'.join(s for s in M3_CO_SO_SQL if s.startswith('CREATE TABLE '))
        self.assertNotRegex(table_ddl, r"'\d{3,}'")  # SQLSTATE của hàm không phải dữ liệu nghiệp vụ
        self.assertNotIn('INSERT INTO m3.policy_', DDL)

    def test_registry_append_theo_dau_khong_ghim_thu_tu(self):
        source = REGISTRY.read_text(encoding='utf-8')
        marker = '# M3-1a — CD-013:'
        self.assertEqual(source.count(marker), 1)
        tail = source.split(marker, 1)[1]
        self.assertIn('from ..k2.sql_m3 import M3_CO_SO_SQL', tail)
        self.assertRegex(tail, r'PG_MIGRATIONS = \(\*PG_MIGRATIONS, \w+_M3_CO_SO\)')
        self.assertEqual(sum(m is M3_CO_SO_SQL for m in registry.PG_MIGRATIONS), 1)
        self.assertEqual(registry.PG_SCHEMA_VERSION, len(registry.PG_MIGRATIONS))

    def test_migration_b_append_khong_ghim_so_hay_hash(self):
        source = REGISTRY.read_text(encoding='utf-8')
        marker = '# M3-1c — CD-013:'
        self.assertEqual(source.count(marker), 1)
        tail = source.split(marker, 1)[1]
        self.assertIn('from ..k2.sql_m3 import M3_CO_SO_B_SQL', tail)
        self.assertRegex(tail, r'PG_MIGRATIONS = \(\*PG_MIGRATIONS, \w+_M3_CO_SO_B\)')
        migrations = registry.PG_MIGRATIONS
        self.assertEqual(sum(m is M3_CO_SO_B_SQL for m in migrations), 1)
        i = migration_b_index()
        self.assertIs(migrations[i], M3_CO_SO_B_SQL)
        self.assertIn(M3_CO_SO_SQL, registry.PG_MIGRATIONS[:i])

    def test_migration_b_trigger_invoker_khoa_va_chi_xet_ban_hien_hanh(self):
        ddl = '\n'.join(M3_CO_SO_B_SQL)
        self.assertNotIn('CREATE UNIQUE INDEX', ddl)
        self.assertNotIn('SECURITY DEFINER', ddl)
        self.assertIn('SET search_path = pg_catalog, m3, pg_temp', ddl)
        self.assertIn('BEFORE INSERT ON m3.hoa_don_hop_dong', ddl)
        self.assertIn('pg_catalog.pg_advisory_xact_lock', ddl)
        self.assertIn('pg_catalog.hashtextextended(NEW.hoa_don_id::text, 0)', ddl)
        self.assertIn("IF NEW.trang_thai = 'DA_XAC_NHAN' THEN", ddl)
        self.assertIn('l.khoa_lien_ket <> NEW.khoa_lien_ket', ddl)
        self.assertIn('SELECT 1 FROM m3.hoa_don_hop_dong s WHERE s.thay_cho_id = l.id', ddl)
        self.assertIn("ERRCODE = '23505'", ddl)

    def test_migration_c_append_sau_b_khong_ghim_so_hay_hash(self):
        source = REGISTRY.read_text(encoding='utf-8')
        marker = '# M3-1d — CD-013:'
        self.assertEqual(source.count(marker), 1)
        tail = source.split(marker, 1)[1]
        self.assertIn('from ..k2.sql_m3 import M3_CO_SO_C_SQL', tail)
        self.assertRegex(tail, r'PG_MIGRATIONS = \(\*PG_MIGRATIONS, \w+_M3_CO_SO_C\)')
        self.assertEqual(sum(m is M3_CO_SO_C_SQL for m in registry.PG_MIGRATIONS), 1)
        self.assertGreater(migration_c_index(), migration_b_index())

    def test_migration_c_chi_them_tien_to_khoa_giu_nguyen_b(self):
        old = M3_CO_SO_B_SQL[0]
        self.assertIn('hashtextextended(NEW.hoa_don_id::text, 0)', old)
        self.assertNotIn('M3_HD_XAC_NHAN|', old)
        self.assertEqual(M3_CO_SO_C_SQL, (
            old.replace('CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION', 1)
               .replace('hashtextextended(NEW.hoa_don_id::text, 0)',
                        "hashtextextended('M3_HD_XAC_NHAN|' || NEW.hoa_don_id::text, 0)"),))
        self.assertIn("'M3_HD_XAC_NHAN|'", M3_CO_SO_C_SQL[0])

    def test_utf8_khong_bom_registry_lf(self):
        for path in (MODULE, REGISTRY, Path(__file__)):
            with self.subTest(file=path.name):
                data = path.read_bytes()
                self.assertFalse(data.startswith(b'\xef\xbb\xbf'))
                data.decode('utf-8', errors='strict')
        self.assertNotIn(b'\r', REGISTRY.read_bytes())

    def test_tien_exact_thieu_khong_mac_dinh_khong_tinh_tu_m2(self):
        basis = next(s for s in M3_CO_SO_SQL if s.startswith('CREATE TABLE m3.hop_dong_co_so'))
        for name in ('gia_tri_truoc_vat', 'tong_gia_dat_duoc_tru', 'phan_chiu_thue', 'vat', 'tong_thanh_toan'):
            self.assertIn(name + ' numeric CHECK', basis)
            self.assertNotRegex(basis, name + r' numeric[^\n]*DEFAULT')
        self.assertNotRegex(DDL.lower(), r'\b(float|real|double precision|dien_tich|gia_dat_tru)\b')
        self.assertIn('phan_chiu_thue IS NOT DISTINCT FROM gia_tri_truoc_vat - tong_gia_dat_duoc_tru', basis)
        self.assertNotIn('CREATE TABLE m3.hoa_don_phien_ban', DDL)

    def test_fk_ghim_phien_ban_va_quan_sat_m2(self):
        for ref in ('master.hop_dong (phap_nhan_id, id)', 'master.hop_dong_phien_ban (id, hop_dong_id)',
                    'kho.hoa_don_danh_tinh (phap_nhan_id, id)',
                    'kho.hoa_don_phien_ban (phap_nhan_id, hoa_don_id, id)',
                    'kho.hoa_don_quan_sat (phap_nhan_id, hoa_don_id, id, phien_ban_id)'):
            self.assertIn('REFERENCES ' + ref, DDL)
        self.assertIn("h.chieu <> 'BAN_RA'", DDL)
        self.assertIn("h.chieu = 'BAN_RA'", DDL)

    def test_owner_rls_va_nhat_ky_theo_mau(self):
        for fragment in ('master.crm_g_bat_bien()', 'nhat_ky.chan_truncate()',
                         'INSERT INTO nhat_ky.su_kien', 'ENABLE ROW LEVEL SECURITY',
                         "master.ktt_duoc(phap_nhan_id, %L)", "t || '_web', t, 'M3'",
                         'GRANT SELECT ON m3.%I TO app_web'):
            self.assertIn(fragment, DDL)
        self.assertNotIn('SECURITY DEFINER', DDL)
        self.assertNotRegex(DDL, r'GRANT\s+(?:ALL|INSERT|UPDATE|DELETE)')


class M31cDangThucThuan(unittest.TestCase):
    """Gom test bổ sung tại đây để handoff chỉ đổi tổng cộng bốn tệp."""

    def test_cau_hien_trung_tinh_ke_ca_cac_nhanh_thieu_can_cu(self):
        for case in ('co_so', 'nguon', 'ung_vien', 'hoa_don', 'tien', 'thue', 'du_dot', 'trung'):
            with self.subTest(case=case):
                c, links, kw = demo()
                if case == 'co_so':
                    c['trang_thai'] = 'PENDING'
                elif case == 'nguon':
                    c['nguon'] = None
                    links[0]['co_so_id'] = 'DEMO-khac'
                elif case == 'ung_vien':
                    links[0]['trang_thai'] = 'PENDING'
                elif case == 'hoa_don':
                    links[0]['hoa_don'] = None
                elif case == 'tien':
                    c['currency'] = None
                    c['tong_thanh_toan'] = None
                    links[0]['hoa_don']['currency'] = None
                elif case == 'thue':
                    kw['policy_thue'] = None
                elif case == 'du_dot':
                    kw['can_cu_du_dot'] = None
                else:
                    links.append(links[0])
                reasons = '\n'.join(reason for r in tinh_ba_dang_thuc(c, links, **kw)
                                    for reason in r.ra_man_hinh()['ly_do'])
                self.assertTrue(reasons)
                for token in ('Cần Anh', 'policy', '#7'):
                    self.assertNotIn(token, reasons)

    def test_thieu_don_vi_tien_va_khong_xem_duoc_khong_bao_khac_dong_tien(self):
        for case in ('co_so', 'hoa_don', 'khong_xem_duoc'):
            with self.subTest(case=case):
                c, links, kw = demo()
                if case == 'co_so':
                    c['currency'] = None
                    expected = 'đơn vị tiền của cơ sở hợp đồng'
                elif case == 'hoa_don':
                    links[0]['hoa_don']['currency'] = None
                    expected = 'đơn vị tiền của hóa đơn'
                else:
                    links[0]['hoa_don'] = None
                    expected = 'Không xem được hóa đơn'
                for r in tinh_ba_dang_thuc(c, links, **kw):
                    self.assertEqual(r.trang_thai, 'PENDING')
                    self.assertTrue(any(expected in reason for reason in r.ly_do))
                    self.assertFalse(any('đồng tiền khác nhau' in reason for reason in r.ly_do))

    def test_thay_the_huy_hoac_mat_eligible_khong_cong_ban_ghim(self):
        for changes in ({'eligible_content_id': 'DEMO-v2'}, {'eligible_content_id': None},
                        {'co_ban_thay_the': True}, {'native_fiscal_status': 'CANCELLED'}):
            with self.subTest(changes=changes):
                c, links, kw = demo()
                links[0]['hoa_don'].update(eligible_content_id=links[0]['hoa_don_phien_ban_id'])
                links[0]['hoa_don'].update(changes)
                for r, expected in zip(tinh_ba_dang_thuc(c, links, **kw), (54, 10, 40)):
                    self.assertEqual(r.trang_thai, 'PENDING')
                    self.assertEqual(r.ve_trai, Decimal(expected))
                    self.assertIn('Hóa đơn đã được thay thế/điều chỉnh, cần xác nhận lại liên kết.', r.ly_do)
                    self.assertFalse(next(n for n in r.nguon if n.id == links[0]['id']).duoc_tinh)
                self.assertEqual(links[0]['hoa_don_phien_ban_id'], 'DEMO-hoa-don-1-v1')

    def test_eligible_hien_hanh_duoc_tinh(self):
        c, links, kw = demo()
        for link in links:
            link['hoa_don'].update(eligible_content_id=link['hoa_don_phien_ban_id'],
                                  co_ban_thay_the=False, native_fiscal_status='UNKNOWN')
        self.assertEqual([r.trang_thai for r in tinh_ba_dang_thuc(c, links, **kw)], ['KHOP'] * 3)

    def test_reader_truyen_trang_thai_hien_hanh_vao_phep_tinh(self):
        c, links, kw = demo()
        link = links[0]
        row = {**c, 'lien_ket_id': link['id'], 'lien_ket_revision': 1,
               'lien_ket_trang_thai': 'DA_XAC_NHAN', 'lien_ket_nguon': 'DEMO',
               'nguon_ref': 'DEMO', 'lien_ket_vi_tri': None, 'can_cu': 'DEMO',
               **{k: link[k] for k in ('hoa_don_id', 'hoa_don_phien_ban_id', 'hoa_don_quan_sat_id')},
               'chieu': 'BAN_RA', 'hoa_don_phien_ban': 1, 'tien_te': 'VND',
               'eligible_content_id': link['hoa_don_phien_ban_id'],
               'co_ban_thay_the': False, 'native_fiscal_status': 'UNKNOWN'}
        calls = []

        class Connection:
            def execute(inner, query, params):
                calls.append(query)
                return SimpleNamespace(description=[SimpleNamespace(name=k) for k in row],
                                       fetchall=lambda: [row])

        reason = 'Hóa đơn đã được thay thế/điều chỉnh, cần xác nhận lại liên kết.'
        for changes in ({}, {'eligible_content_id': 'DEMO-v2'}, {'eligible_content_id': None},
                        {'co_ban_thay_the': True}, {'native_fiscal_status': 'CANCELLED'}):
            with self.subTest(changes=changes):
                original = dict(row)
                row.update(changes)
                result = M3K2(Connection()).ba_dang_thuc(
                    c['phap_nhan_id'], c['hop_dong_id'], c['hop_dong_phien_ban_id'], pham_vi=c['pham_vi'])
                self.assertEqual([reason in r.ly_do for r in result], [bool(changes)] * 3)
                self.assertEqual([r.trang_thai for r in result], ['PENDING'] * 3)
                self.assertEqual(next(n for n in result[0].nguon if n.loai == 'Hóa đơn').id,
                                 link['hoa_don_phien_ban_id'])
                row.update(original)
        self.assertTrue(all('d.eligible_content_id' in query and 'successor.supersedes_id' in query
                            and 'latest.native_fiscal_status' in query for query in calls))


@unittest.skipUnless(ADMIN_DSN and psycopg is not None, 'Thiếu KHO_PG_DSN_TEST hoặc psycopg — bỏ qua PG')
class M3Postgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = 'kho_test_m3_' + uuid.uuid4().hex
        with psycopg.connect(ADMIN_DSN, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.addClassCleanup(cls._don_csdl)
        cls.c = psycopg.connect(make_conninfo(ADMIN_DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        i = migration_b_index()
        pg.migrate(cls.c, target=i)  # đúng tiền tố PG_MIGRATIONS[:i], kể cả khi lead thêm migration
        pg.migrate(cls.c, target=i + 1)
        i = migration_c_index()
        pg.migrate(cls.c, target=i)
        cls.function_before_c = cls.c.execute("""SELECT oid, proowner, proacl, prosecdef, proconfig
            FROM pg_proc WHERE oid='m3.lien_ket_mot_xac_nhan()'::regprocedure""").fetchone()
        pg.migrate(cls.c, target=i + 1)

    @classmethod
    def _don_csdl(cls):
        # Chỉ CSDL mới do chính class tạo; không DROP role/dịch vụ/dữ liệu ngoài.
        assert re.fullmatch(r'kho_test_m3_[a-f0-9]+', cls.db)
        with psycopg.connect(ADMIN_DSN, autocommit=True) as admin:
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(cls.db)))

    def setUp(self):
        self.c.execute('BEGIN')
        self.addCleanup(lambda: self.c.execute('ROLLBACK'))
        self.pn, self.other_pn = [self.c.execute(
            'INSERT INTO master.phap_nhan (ma, ten) VALUES (%s,%s) RETURNING id',
            ('DEMO_M3_' + uuid.uuid4().hex, 'Pháp nhân DEMO M3')).fetchone()[0] for _ in range(2)]
        self.hd = self.c.execute("""INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong)
            VALUES (%s,'THUE_DAT','DEMO-M3','DEMO/M3') RETURNING id""", (self.pn,)).fetchone()[0]
        self.pb = self.c.execute("""INSERT INTO master.hop_dong_phien_ban (hop_dong_id, phien_ban, nguon)
            VALUES (%s,1,'TAY') RETURNING id""", (self.hd,)).fetchone()[0]
        self.lh = self.c.execute("""INSERT INTO master.loai_hinh_doanh_thu (phap_nhan_id, ma, ten)
            VALUES (%s,'DEMO-M3','Loại hình DEMO') RETURNING id""", (self.pn,)).fetchone()[0]

    def basis(self, **changes):
        values = dict(phap_nhan_id=self.pn, hop_dong_id=self.hd, hop_dong_phien_ban_id=self.pb,
                      pham_vi='DEMO toàn hợp đồng', revision=1, nguon='Hợp đồng DEMO', tao_boi='DEMO')
        values.update(changes)
        return self.insert('hop_dong_co_so', values)

    def insert(self, table, values):
        query = sql.SQL('INSERT INTO m3.{} ({}) VALUES ({}) RETURNING id').format(
            sql.Identifier(table), sql.SQL(',').join(map(sql.Identifier, values)),
            sql.SQL(',').join(sql.Placeholder() for _ in values))
        return self.c.execute(query, tuple(values.values())).fetchone()[0]

    def rejected(self, code, fn):
        with self.assertRaises(psycopg.Error) as caught:
            with self.c.transaction():
                fn()
        self.assertEqual(caught.exception.sqlstate, code)

    def policy(self, day, form=None, revision=1):
        values = dict(phap_nhan_id=self.pn, loai_hinh_id=self.lh, hieu_luc_tu=day, revision=revision,
                      hinh_thuc=form, nguon='Quyết định DEMO', tao_boi='DEMO')
        if form is not None:
            values.update(trang_thai='DA_XAC_NHAN', xac_nhan_boi='DEMO', xac_nhan_luc='2026-01-01T00:00:00Z')
        return self.insert('policy_hinh_thuc_doanh_thu', values)

    def test_phan_chiu_thue_dung_sai_va_null(self):
        self.basis(gia_tri_truoc_vat=Decimal('100.01'), tong_gia_dat_duoc_tru=Decimal('20.001'),
                   phan_chiu_thue=Decimal('80.009'))
        for taxable in (Decimal('80.01'), None):
            self.rejected('23514', lambda: self.basis(revision=2, gia_tri_truoc_vat=100,
                          tong_gia_dat_duoc_tru=20, phan_chiu_thue=taxable))
        self.basis(revision=2)  # thiếu vẫn là NULL/PENDING, không thành 0
        self.basis(revision=3, gia_tri_truoc_vat=100, tong_gia_dat_duoc_tru=0, phan_chiu_thue=100)
        self.rejected('23514', lambda: self.basis(revision=4, gia_tri_truoc_vat=10,
                      tong_gia_dat_duoc_tru=20, phan_chiu_thue=0))

    def test_tien_khong_am_va_huu_han(self):
        for field in ('gia_tri_truoc_vat', 'tong_gia_dat_duoc_tru', 'phan_chiu_thue', 'vat', 'tong_thanh_toan'):
            for value in ('-0.01', 'NaN', 'Infinity', '-Infinity'):
                with self.subTest(field=field, value=value):
                    self.rejected('23514', lambda: self.basis(**{field: Decimal(value)}))

    def test_revision_moi_giu_ban_cu_va_nhat_ky(self):
        old = self.basis(gia_tri_truoc_vat=100)
        new = self.basis(revision=2, gia_tri_truoc_vat=120)
        rows = self.c.execute('SELECT id, gia_tri_truoc_vat FROM m3.hop_dong_co_so ORDER BY revision').fetchall()
        self.assertEqual(rows, [(old, Decimal(100)), (new, Decimal(120))])
        self.rejected('P0001', lambda: self.c.execute('UPDATE m3.hop_dong_co_so SET vat=1 WHERE id=%s', (old,)))
        self.rejected('P0001', lambda: self.c.execute('DELETE FROM m3.hop_dong_co_so WHERE id=%s', (old,)))
        self.rejected('P0001', lambda: self.c.execute('TRUNCATE m3.hop_dong_co_so CASCADE'))
        count = self.c.execute("SELECT count(*) FROM nhat_ky.su_kien WHERE doi_tuong_bang='m3.hop_dong_co_so' AND doi_tuong_id IN (%s,%s)", (old, new)).fetchone()[0]
        self.assertEqual(count, 2)

    def test_xac_nhan_can_du_tien_va_crm_duyet(self):
        self.rejected('23514', lambda: self.basis(trang_thai='DA_XAC_NHAN'))
        self.rejected('23514', lambda: self.basis(trang_thai='DA_XAC_NHAN', xac_nhan_boi='DEMO',
                      xac_nhan_luc='2026-01-01T00:00:00Z', ngay_nghiep_vu='2026-01-01', hieu_luc_tu='2026-01-01',
                      gia_tri_truoc_vat=100, tong_gia_dat_duoc_tru=20, phan_chiu_thue=80, vat=8,
                      tong_thanh_toan=108, currency='VND'))  # CRM đang CHO_DUYET

    def test_co_so_khong_ghep_sai_phap_nhan_hoac_phien_ban(self):
        self.rejected('23503', lambda: self.basis(phap_nhan_id=self.other_pn))
        hd2 = self.c.execute("""INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong)
            VALUES (%s,'THUE_DAT','DEMO-M3-2','DEMO/M3/2') RETURNING id""", (self.pn,)).fetchone()[0]
        self.rejected('23503', lambda: self.basis(hop_dong_id=hd2))

    def test_mapping_candidate_revision_va_fk_m2(self):
        basis = self.basis()
        values = dict(phap_nhan_id=self.pn, co_so_id=basis, revision=1, nguon='M2 source candidate DEMO',
                      nguon_ref='DEMO/source/1', tao_boi='DEMO', khoa_lien_ket=uuid.uuid4())
        old = self.insert('hoa_don_hop_dong', values)
        self.insert('hoa_don_hop_dong', {**values, 'revision': 2, 'thay_cho_id': old})
        self.assertEqual(self.c.execute('SELECT count(*) FROM m3.hoa_don_hop_dong').fetchone()[0], 2)
        self.rejected('23514', lambda: self.insert('hoa_don_hop_dong', {**values, 'revision': 4, 'thay_cho_id': old}))
        self.rejected('23503', lambda: self.insert('hoa_don_hop_dong', {**values, 'khoa_lien_ket': uuid.uuid4(),
                      'hoa_don_id': uuid.uuid4(), 'hoa_don_phien_ban_id': uuid.uuid4(), 'hoa_don_quan_sat_id': uuid.uuid4()}))
        self.rejected('23514', lambda: self.insert('hoa_don_hop_dong', {**values, 'khoa_lien_ket': uuid.uuid4(),
                      'hoa_don_id': uuid.uuid4()}))
        self.rejected('23514', lambda: self.insert('hoa_don_hop_dong', {**values, 'khoa_lien_ket': uuid.uuid4(),
                      'trang_thai': 'DA_XAC_NHAN', 'xac_nhan_boi': 'DEMO', 'xac_nhan_luc': '2026-01-01', 'can_cu': 'DEMO'}))
        refs = {r[0] for r in self.c.execute("""SELECT confrelid::regclass::text FROM pg_constraint
            WHERE conrelid='m3.hoa_don_hop_dong'::regclass AND contype='f'""").fetchall()}
        self.assertTrue({'kho.hoa_don_danh_tinh', 'kho.hoa_don_phien_ban', 'kho.hoa_don_quan_sat'} <= refs)

    def test_mapping_chan_hoa_don_mua(self):
        self.c.execute("INSERT INTO master.nguon_instance (source_instance_id) VALUES ('M3_DEMO')")
        invoice = self.c.execute("""INSERT INTO kho.hoa_don_danh_tinh
            (phap_nhan_id,chieu,mst_ban,mau_so,ky_hieu,so_chuan,source_instance_id,created_by)
            VALUES (%s,'MUA_VAO','0000000001','DEMO','DEMO','1','M3_DEMO','DEMO') RETURNING id""", (self.pn,)).fetchone()[0]
        self.rejected('23514', lambda: self.insert('hoa_don_hop_dong', dict(phap_nhan_id=self.pn,
                      co_so_id=self.basis(), revision=1, nguon='M2 DEMO', nguon_ref='DEMO', tao_boi='DEMO',
                      hoa_don_id=invoice, hoa_don_phien_ban_id=uuid.uuid4(), hoa_don_quan_sat_id=uuid.uuid4())))

    def mapping_snapshot(self):
        # Cô lập trigger mới; giữ CHECK/index, không nới FK/guard M2 trên bảng gốc.
        self.c.execute('CREATE TEMP TABLE m3c_lien_ket (LIKE m3.hoa_don_hop_dong INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES)')
        for statement in (*M3_CO_SO_B_SQL, *M3_CO_SO_C_SQL):
            self.c.execute(statement.replace('m3.hoa_don_hop_dong', 'pg_temp.m3c_lien_ket')
                           .replace('m3.lien_ket_mot_xac_nhan', 'pg_temp.m3c_mot_xac_nhan'))
        invoice, version, observation = (uuid.uuid4() for _ in range(3))

        def add(basis, confirmed, *, chain=None, revision=1, replaces=None, invoice_version=version):
            return self.c.execute("""INSERT INTO pg_temp.m3c_lien_ket
                (phap_nhan_id,co_so_id,khoa_lien_ket,revision,thay_cho_id,
                 hoa_don_id,hoa_don_phien_ban_id,hoa_don_quan_sat_id,
                 nguon,nguon_ref,tao_boi,trang_thai,can_cu,xac_nhan_boi,xac_nhan_luc)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'DEMO','DEMO','DEMO',%s,'DEMO',%s,%s) RETURNING id""",
                (self.pn, basis, chain or uuid.uuid4(), revision, replaces, invoice, invoice_version, observation,
                 'DA_XAC_NHAN' if confirmed else 'PENDING',
                 'DEMO' if confirmed else None, '2026-01-01' if confirmed else None)).fetchone()[0]

        return add

    def test_cung_chuoi_revision_2_xac_nhan_lai_duoc(self):
        add = self.mapping_snapshot()
        basis, chain = uuid.uuid4(), uuid.uuid4()
        old = add(basis, True, chain=chain)
        new_version = uuid.uuid4()
        new = add(basis, True, chain=chain, revision=2, replaces=old, invoice_version=new_version)
        self.assertEqual(self.c.execute('SELECT id FROM pg_temp.m3c_lien_ket ORDER BY revision').fetchall(),
                         [(old,), (new,)])
        # Cùng chuỗi có thể chuyển tiếp sang revision mới của cơ sở hợp đồng.
        add(uuid.uuid4(), True, chain=chain, revision=3, replaces=new, invoice_version=new_version)

    def test_chuoi_cu_da_pending_chuoi_moi_xac_nhan_duoc(self):
        add = self.mapping_snapshot()
        basis, chain = uuid.uuid4(), uuid.uuid4()
        old = add(basis, True, chain=chain)
        add(basis, False, chain=chain, revision=2, replaces=old)
        new = add(uuid.uuid4(), True)
        self.assertEqual(self.c.execute("""SELECT id FROM pg_temp.m3c_lien_ket l
            WHERE l.trang_thai='DA_XAC_NHAN' AND NOT EXISTS (
                SELECT 1 FROM pg_temp.m3c_lien_ket s WHERE s.thay_cho_id=l.id)""").fetchall(), [(new,)])
        self.assertEqual(self.c.execute('SELECT count(*) FROM pg_temp.m3c_lien_ket').fetchone()[0], 3)

    def test_hai_chuoi_hien_hanh_cung_xac_nhan_bi_tu_choi(self):
        add = self.mapping_snapshot()
        bases = [uuid.uuid4(), uuid.uuid4()]
        add(bases[0], True)
        for basis in bases:
            with self.subTest(basis=basis):
                with self.assertRaises(psycopg.errors.UniqueViolation) as caught:
                    with self.c.transaction():
                        add(basis, True)
                self.assertEqual(caught.exception.sqlstate, '23505')
                self.assertIn('Hóa đơn đã có liên kết hiện hành được xác nhận', str(caught.exception))
        self.assertEqual(self.c.execute('SELECT count(*) FROM pg_temp.m3c_lien_ket').fetchone()[0], 1)

    def test_mot_hoa_don_hai_hop_dong_chi_ung_vien_duoc_trung(self):
        add = self.mapping_snapshot()
        bases = [uuid.uuid4(), uuid.uuid4()]
        for basis in bases:
            add(basis, False)
        add(bases[0], True)
        self.rejected('23505', lambda: add(bases[1], True))
        add(bases[1], False)  # vẫn là ứng viên được, dù HĐ thứ nhất đã xác nhận
        self.assertEqual(self.c.execute('SELECT count(*) FROM pg_temp.m3c_lien_ket').fetchone()[0], 4)

    def test_trigger_moi_da_cai_tren_bang_goc(self):
        definition, definer, config = self.c.execute("""SELECT pg_get_triggerdef(t.oid), p.prosecdef, p.proconfig
            FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid
            WHERE t.tgrelid='m3.hoa_don_hop_dong'::regclass
              AND t.tgname='hoa_don_hop_dong_mot_xac_nhan'""").fetchone()
        self.assertIn('BEFORE INSERT ON m3.hoa_don_hop_dong', definition)
        self.assertIn('m3.lien_ket_mot_xac_nhan()', definition)
        self.assertFalse(definer)
        self.assertIn('search_path=pg_catalog, m3, pg_temp', config)

    def test_migration_c_ham_da_co_tien_to_giu_quyen_va_search_path(self):
        definition = self.c.execute("SELECT pg_get_functiondef('m3.lien_ket_mot_xac_nhan()'::regprocedure)").fetchone()[0]
        self.assertIn("'M3_HD_XAC_NHAN|'", definition)
        self.assertEqual(self.c.execute("""SELECT oid, proowner, proacl, prosecdef, proconfig
            FROM pg_proc WHERE oid='m3.lien_ket_mot_xac_nhan()'::regprocedure""").fetchone(),
            self.function_before_c)

    def test_hai_giao_dich_cung_hoa_don_hai_hop_dong_bi_tu_choi(self):
        # Bảng dùng chung để hai connection thấy cùng dữ liệu; vẫn là SQL cô lập
        # như mapping_snapshot, không giả luồng promote BAN_RA đầu-cuối của M2.
        dsn = make_conninfo(ADMIN_DSN, dbname=self.db)
        with psycopg.connect(dsn, autocommit=True) as first, psycopg.connect(dsn, autocommit=True) as second:
            first.execute('CREATE TABLE m3.m3d_lien_ket (LIKE m3.hoa_don_hop_dong INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES)')
            for statement in (*M3_CO_SO_B_SQL, *M3_CO_SO_C_SQL):
                first.execute(statement.replace('m3.hoa_don_hop_dong', 'm3.m3d_lien_ket')
                              .replace('m3.lien_ket_mot_xac_nhan', 'm3.m3d_mot_xac_nhan'))
            second.execute("SET lock_timeout = '500ms'")
            invoice, version, observation = (uuid.uuid4() for _ in range(3))

            def confirm(connection, basis):
                connection.execute("""INSERT INTO m3.m3d_lien_ket
                    (phap_nhan_id,co_so_id,khoa_lien_ket,revision,
                     hoa_don_id,hoa_don_phien_ban_id,hoa_don_quan_sat_id,
                     nguon,nguon_ref,tao_boi,trang_thai,can_cu,xac_nhan_boi,xac_nhan_luc)
                    VALUES (%s,%s,%s,1,%s,%s,%s,'DEMO','DEMO','DEMO','DA_XAC_NHAN','DEMO','DEMO','2026-01-01')""",
                    (self.pn, basis, uuid.uuid4(), invoice, version, observation))

            bases = [uuid.uuid4(), uuid.uuid4()]
            with first.transaction():
                confirm(first, bases[0])
                # Khóa UUID trần của miền khác không bị khóa M3 giữ chỗ.
                self.assertTrue(second.execute('SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0))',
                                               (str(invoice),)).fetchone()[0])
                with self.assertRaises(psycopg.errors.LockNotAvailable):
                    confirm(second, bases[1])
            with self.assertRaises(psycopg.errors.UniqueViolation) as caught:
                confirm(second, bases[1])
            self.assertEqual(caught.exception.sqlstate, '23505')
            self.assertIn('Hóa đơn đã có liên kết hiện hành được xác nhận', str(caught.exception))
            self.assertEqual(first.execute('SELECT count(*) FROM m3.m3d_lien_ket').fetchone()[0], 1)

    def test_reader_pg_ban_ghim_khac_eligible_hoac_co_successor_pending(self):
        # Thực thi SELECT của reader trên snapshot bảng tạm; không sửa CHECK,
        # trigger hay dữ liệu M2 để dựng giả luồng promote bán ra đã chạy được.
        tables = {'m3.hop_dong_co_so': 'm3c_co_so', 'master.hop_dong_phien_ban': 'm3c_pb',
                  'm3.hoa_don_hop_dong': 'm3c_mapping', 'kho.hoa_don_phien_ban': 'm3c_version',
                  'kho.hoa_don_danh_tinh': 'm3c_invoice', 'kho.hoa_don_quan_sat': 'm3c_observation'}
        for original, temporary in tables.items():
            self.c.execute(sql.SQL('CREATE TEMP TABLE {} AS SELECT * FROM {} WITH NO DATA').format(
                sql.Identifier(temporary), sql.Identifier(*original.split('.'))))
        basis = self.basis(currency='VND', gia_tri_truoc_vat=100, tong_gia_dat_duoc_tru=20,
                           phan_chiu_thue=80, vat=8, tong_thanh_toan=108)
        self.c.execute('INSERT INTO m3c_co_so SELECT * FROM m3.hop_dong_co_so WHERE id=%s', (basis,))
        self.c.execute("UPDATE m3c_co_so SET trang_thai='DA_XAC_NHAN'")
        self.c.execute('INSERT INTO m3c_pb SELECT * FROM master.hop_dong_phien_ban WHERE id=%s', (self.pb,))
        self.c.execute("UPDATE m3c_pb SET trang_thai='DA_DUYET'")
        invoice, version, observation, link = (uuid.uuid4() for _ in range(4))
        self.c.execute("""INSERT INTO m3c_invoice (id,phap_nhan_id,chieu,eligible_content_id,latest_observation_id)
            VALUES (%s,%s,'BAN_RA',%s,%s)""", (invoice, self.pn, version, observation))
        self.c.execute("""INSERT INTO m3c_version (id,phap_nhan_id,hoa_don_id,phien_ban,tien_te,money_basis_state)
            VALUES (%s,%s,%s,1,'VND','UNPROVEN_NO_MINOR')""", (version, self.pn, invoice))
        self.c.execute("""INSERT INTO m3c_observation (id,phap_nhan_id,hoa_don_id,native_fiscal_status)
            VALUES (%s,%s,%s,'UNKNOWN')""", (observation, self.pn, invoice))
        self.c.execute("""INSERT INTO m3c_mapping
            (id,khoa_lien_ket,revision,phap_nhan_id,co_so_id,hoa_don_id,hoa_don_phien_ban_id,
             hoa_don_quan_sat_id,nguon,nguon_ref,can_cu,trang_thai)
            VALUES (%s,%s,1,%s,%s,%s,%s,%s,'DEMO','DEMO','DEMO','DA_XAC_NHAN')""",
            (link, uuid.uuid4(), self.pn, basis, invoice, version, observation))
        connection = self.c

        class SnapshotConnection:
            def execute(inner, query, params):
                for original, temporary in tables.items():
                    query = query.replace(original, temporary)
                return connection.execute(query, params)

        def read():
            return M3K2(SnapshotConnection()).ba_dang_thuc(
                self.pn, self.hd, self.pb, pham_vi='DEMO toàn hợp đồng')

        reason = 'Hóa đơn đã được thay thế/điều chỉnh, cần xác nhận lại liên kết.'
        self.assertFalse(any(reason in r.ly_do for r in read()))
        for case in ('eligible_khac', 'eligible_null', 'successor', 'huy'):
            with self.subTest(case=case), self.c.transaction(force_rollback=True):
                if case.startswith('eligible'):
                    self.c.execute('UPDATE m3c_invoice SET eligible_content_id=%s',
                                   (uuid.uuid4() if case == 'eligible_khac' else None,))
                elif case == 'successor':
                    self.c.execute("""INSERT INTO m3c_version (id,phap_nhan_id,hoa_don_id,supersedes_id,phien_ban)
                        VALUES (%s,%s,%s,%s,2)""", (uuid.uuid4(), self.pn, invoice, version))
                else:
                    self.c.execute("UPDATE m3c_observation SET native_fiscal_status='CANCELLED'")
                for r in read():
                    self.assertEqual(r.trang_thai, 'PENDING')
                    self.assertIn(reason, r.ly_do)
                    self.assertIsNone(r.ve_trai)
                    source = next(n for n in r.nguon if n.loai == 'Hóa đơn')
                    self.assertEqual(source.id, str(version))
                    self.assertFalse(source.duoc_tinh)

    def test_policy_theo_ngay_hieu_luc_va_pending(self):
        first = self.policy('2026-01-01', 'GHI_NHAN_LUON')
        second = self.policy('2026-06-01', 'PHAN_BO')
        for day, expected in (('2025-12-31', None), ('2026-01-01', first), ('2026-05-31', first), ('2026-06-01', second)):
            rows = self.c.execute('SELECT id FROM m3.policy_tai_ngay(%s,%s,%s)', (self.pn, self.lh, day)).fetchall()
            self.assertEqual(rows, [] if expected is None else [(expected,)])
        pending = self.policy('2026-06-01', revision=2)
        self.assertEqual(self.c.execute("SELECT id, hinh_thuc, trang_thai FROM m3.policy_tai_ngay(%s,%s,'2026-07-01')",
                                       (self.pn, self.lh)).fetchone(), (pending, None, 'PENDING'))
        self.rejected('P0001', lambda: self.c.execute("UPDATE m3.policy_hinh_thuc_doanh_thu SET hinh_thuc='PHAN_BO' WHERE id=%s", (first,)))

    def test_app_web_chi_doc_dung_phap_nhan_khong_ghi(self):
        basis = self.basis()
        self.policy('2026-01-01', 'PHAN_BO')
        self.insert('hoa_don_hop_dong', dict(phap_nhan_id=self.pn, co_so_id=basis, revision=1,
                    nguon='DEMO', nguon_ref='DEMO', tao_boi='DEMO'))
        other_lh = self.c.execute("""INSERT INTO master.loai_hinh_doanh_thu (phap_nhan_id,ma,ten)
            VALUES (%s,'DEMO-KHAC','DEMO') RETURNING id""", (self.other_pn,)).fetchone()[0]
        other_hd = self.c.execute("""INSERT INTO master.hop_dong (phap_nhan_id,loai,ma_noi_bo,so_hop_dong)
            VALUES (%s,'THUE_DAT','DEMO-KHAC','DEMO/KHAC') RETURNING id""", (self.other_pn,)).fetchone()[0]
        other_pb = self.c.execute("""INSERT INTO master.hop_dong_phien_ban (hop_dong_id,phien_ban,nguon)
            VALUES (%s,1,'TAY') RETURNING id""", (other_hd,)).fetchone()[0]
        other_basis = self.basis(phap_nhan_id=self.other_pn, hop_dong_id=other_hd, hop_dong_phien_ban_id=other_pb)
        self.insert('hoa_don_hop_dong', dict(phap_nhan_id=self.other_pn, co_so_id=other_basis, revision=1,
                    nguon='DEMO KHÁC', nguon_ref='DEMO/KHAC', tao_boi='DEMO'))
        self.insert('policy_hinh_thuc_doanh_thu', dict(phap_nhan_id=self.other_pn, loai_hinh_id=other_lh,
                    revision=1, hieu_luc_tu='2026-01-01', nguon='DEMO', tao_boi='DEMO'))
        login = 'DEMO_M3_' + uuid.uuid4().hex
        user = self.c.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro) VALUES ('DEMO',%s,'XEM') RETURNING id", (login,)).fetchone()[0]
        self.c.execute("INSERT INTO master.phan_quyen (nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,ARRAY['M3'])", (user, self.pn))
        self.c.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true),set_config('ktt.nguoi_dung_dang_nhap',%s,true)", (str(user), login))
        self.c.execute('SET LOCAL ROLE app_web')
        for table in TABLES:
            with self.subTest(table=table):
                rows = self.c.execute(sql.SQL('SELECT DISTINCT phap_nhan_id FROM m3.{}').format(sql.Identifier(table))).fetchall()
                self.assertEqual(rows, [(self.pn,)])
                for command in ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE'):
                    allowed = self.c.execute('SELECT has_table_privilege(current_user,%s,%s)', ('m3.' + table, command)).fetchone()[0]
                    self.assertFalse(allowed)
                self.rejected('42501', lambda: self.c.execute(sql.SQL('UPDATE m3.{} SET tao_boi=tao_boi').format(sql.Identifier(table))))
                self.rejected('42501', lambda: self.c.execute(sql.SQL('INSERT INTO m3.{} DEFAULT VALUES').format(sql.Identifier(table))))
        self.assertEqual(self.c.execute("SELECT count(*) FROM m3.policy_tai_ngay(%s,%s,'2026-02-01')", (self.other_pn, other_lh)).fetchone()[0], 0)
        self.c.execute('RESET ROLE')
        self.c.execute("UPDATE master.phan_quyen SET module=ARRAY['CRM'] WHERE nguoi_dung_id=%s", (user,))
        self.c.execute('SET LOCAL ROLE app_web')
        for table in TABLES:
            self.assertEqual(self.c.execute(sql.SQL('SELECT count(*) FROM m3.{}').format(sql.Identifier(table))).fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
