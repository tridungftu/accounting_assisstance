"""M3-1a: SQL tĩnh và PG trên CSDL kho_test_* riêng, chỉ dữ liệu DEMO.

Không có KHO_PG_DSN_TEST/psycopg thì skip PG, không mở dịch vụ.
M2 chưa promote BAN_RA: chỉ thử candidate/FK/guard, không giả bản bán hợp lệ.
"""

from __future__ import annotations

import ast
from decimal import Decimal
import os
from pathlib import Path
import re
import unittest
import uuid

from kho_tri_thuc.ha_tang import postgres as pg
from kho_tri_thuc.ha_tang import pg_migrations as registry
from kho_tri_thuc.k2.sql_m3 import M3_CO_SO_SQL

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


class M3SqlTinh(unittest.TestCase):
    def test_module_chi_hang_sql_literal(self):
        tree = ast.parse(MODULE.read_text(encoding='utf-8'))
        self.assertEqual(len(tree.body), 2)
        self.assertIsInstance(tree.body[0], ast.Expr)  # docstring
        assignment = tree.body[1]
        self.assertIsInstance(assignment, ast.Assign)
        self.assertEqual([x.id for x in assignment.targets], ['M3_CO_SO_SQL'])
        self.assertEqual(ast.literal_eval(assignment.value), M3_CO_SO_SQL)
        self.assertTrue(all(isinstance(s, str) and s.strip() for s in M3_CO_SO_SQL))

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


@unittest.skipUnless(ADMIN_DSN and psycopg is not None, 'Thiếu KHO_PG_DSN_TEST hoặc psycopg — bỏ qua PG')
class M3Postgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner_cap = bool(os.environ.get('KHO_PG_DEMO_SO'))
        cls.db = os.environ.get('KHO_PG_DEMO_DB') if cls.runner_cap else 'kho_test_m3_' + uuid.uuid4().hex
        if not cls.db or not re.fullmatch(r'kho_test_[a-z0-9_]+', cls.db):
            raise unittest.SkipTest('Chỉ chạy M3 trên CSDL test riêng kho_test_*')
        if not cls.runner_cap:
            with psycopg.connect(ADMIN_DSN, autocommit=True) as admin:
                admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
            cls.addClassCleanup(cls._don_csdl)
        cls.c = psycopg.connect(make_conninfo(ADMIN_DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        pg.migrate(cls.c)

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
