"""MTQ-4f1c: oracle CU, RLS từng dòng, B6 và READ ONLY.

Chỉ tạo kho_test_* từ KHO_PG_DSN_TEST; giữ CSDL cho lead kiểm tra.
Không đọc DSN DEMO, không tắt trigger, không ghim migration cuối.
"""

from __future__ import annotations

import os
import re
import unittest
import uuid

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.m4.sql_mtq import MTQ_M4_B_SQL
from tests import test_mtq_m4_ho_so_sql as ho_so
from tests import test_mtq_sql as nen

DSN = os.environ.get('KHO_PG_DSN_TEST')
psycopg = nen.psycopg
MIGRATION = PM.M0061_MTQ_M4_B
POSITION = next(i for i, m in enumerate(PM.PG_MIGRATIONS) if m is MIGRATION)
BEFORE = ho_so.definitions(PM.PG_MIGRATIONS[:POSITION])
AFTER = ho_so.definitions((MIGRATION,))
TABLES = (
    'ho_so_hop_dong', 'tep', 'trich_xuat', 'tham_so', 'tham_so_lich_su',
    'xac_nhan_tham_so', 'phu_luc', 'boq', 'boq_dong', 'dot', 'dot_tep', 'nop',
    'nhat_ky', 'bien_nhan', 'master_can_cu', 'master_can_cu_phien_ban',
    'review_chep_hop_dong', 'review_chep_tham_so', 'review_chep_phu_luc',
    'review_chep_thay_doi_tham_so', 'review_chep_boq_dong', 'review_chep_dot_thanh_toan',
    'review_chep_kl_thanh_toan', 'review_chep_khop_hang_muc', 'review_chep_canh_bao',
    'review_chep_nhat_ky', 'review_chep_tham_so_nguon',
)


class MtqM4DocTinh(unittest.TestCase):
    def test_registry_append_khong_doi_migration_cu(self):
        from pathlib import Path

        source = Path(PM.__file__).read_text(encoding='utf-8')
        marker = '# MTQ-4f1c — CD-012:'
        self.assertEqual(source.count(marker), 1)
        old = {'__name__': PM.__name__, '__package__': PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, 'exec'), old)
        self.assertEqual(PM.PG_MIGRATIONS[:POSITION], old['PG_MIGRATIONS'])
        self.assertEqual(sum(m is MIGRATION for m in PM.PG_MIGRATIONS), 1)

    def test_khong_doi_rls_nen_trigger_hay_guard_lenh(self):
        sql = '\n'.join(MIGRATION)
        self.assertNotRegex(sql, r'CREATE(?: OR REPLACE)? FUNCTION master\.')
        self.assertNotRegex(sql, r'\b(?:CREATE TABLE|ALTER TABLE|TRIGGER|DISABLE|INSERT INTO|UPDATE|DELETE FROM)\b')
        changed = set(AFTER) & set(BEFORE)
        self.assertEqual(changed, {
            'm4.digest_tham_so', 'm4.tep_da_nop', 'm4.thieu', 'm4.mc_co_ho_so',
            'm4.master_hop_dong_ds', 'm4.master_doi_tac_ds', 'm4.master_can_cu_doc',
            'm4.review_chep_hien_hanh',
        })
        for name in changed:
            self.assertEqual('SECURITY DEFINER' in BEFORE[name], 'SECURITY DEFINER' in AFTER[name])
            self.assertEqual('VOLATILE' in BEFORE[name], 'VOLATILE' in AFTER[name])

    def test_doc_chi_dung_mtq_duoc_doc_khong_khoa_khong_ghi(self):
        stmt = AFTER['m4.mtq_ho_so_doc']
        self.assertIn('STABLE SECURITY DEFINER', stmt)
        self.assertIn("phap_nhan_id = pn AND bat", stmt)
        self.assertIn("RETURN NULL", stmt)
        self.assertIn("master.mtq_duoc_doc('M4:HO_SO:' || p_hanh", stmt)
        self.assertNotIn('master.m4_duoc', stmt)
        self.assertNotRegex(stmt, r'FOR (?:UPDATE|SHARE)|advisory|mtq_quyet_dinh_phien')
        self.assertIn("IF pn IS NULL", stmt)

    def test_du_policy_va_khoa_theo_dong(self):
        sql = '\n'.join(MTQ_M4_B_SQL)
        for table in TABLES:
            with self.subTest(table=table):
                stmt = next(s for s in MTQ_M4_B_SQL if f'CREATE POLICY {table}_web ' in s)
                self.assertIn(f'DROP POLICY IF EXISTS {table}_web ON m4.{table}', stmt)
                self.assertIn('USING (', stmt)
                self.assertIn('coalesce(m4.mtq_ho_so_doc(', stmt)
        self.assertNotIn('GRANT SELECT', sql)
        self.assertNotIn('CREATE POLICY review_chep_nguon', sql)
        self.assertNotIn('CREATE POLICY review_chep_che_do', sql)
        self.assertIn("'m4.dot', dot_id, 'XEM'", sql)
        self.assertIn("'m4.tep', id, 'XEM'", sql)
        self.assertIn('p.hop_dong_id FROM m4.review_chep_phu_luc', sql)
        self.assertIn('d.hop_dong_id FROM m4.review_chep_dot_thanh_toan', sql)

    def test_b6_lap_theo_du_an_khong_doi_thanh_xem(self):
        self.assertIn("'master.du_an', p_du_an, 'LAP'", AFTER['m4.mau_duoc'])
        for name in ('m4.master_hop_dong_ds', 'm4.master_doi_tac_ds'):
            stmt = AFTER[name]
            self.assertIn("m4.mtq_ho_so_doc('master.du_an', p_du_an, 'LAP') IS NULL", stmt)
            self.assertIn('ELSIF NOT m4.mau_duoc(p_du_an)', stmt)
            self.assertLess(stmt.index('ELSIF NOT m4.mau_duoc'), stmt.index('SELECT coalesce(jsonb_agg'))
        self.assertIn("m4.mtq_ho_so_doc('master.hop_dong', h.id, 'LAP')", AFTER['m4.master_hop_dong_ds'])

    def test_o_xem_buoc_sau_giu_trang_thai_va_fk_that(self):
        stmt = AFTER['m4.mtq_ho_so_doc']
        self.assertLess(stmt.index("'M4:HO_SO:' || p_hanh"), stmt.index("IF p_hanh <> 'XEM'"))
        for screen in ('02A_REVIEW', '02B_CHUNG_TU', '02C_DUYET', '03A_KE_TOAN'):
            self.assertIn(f"'M4:{screen}:XEM'", stmt)
        self.assertEqual(stmt.count("d.trang_thai = 'DA_NOP'"), 2)
        self.assertIn("t.vai_tro_tai_lieu = 'HO_SO_DOT'", stmt)
        self.assertIn('k.tep_id = t.id AND k.du_an_id = t.du_an_id', stmt)
        self.assertIn('c.dot_id = d.id AND c.du_an_id = d.du_an_id AND c.hop_dong_id = d.hop_dong_id', stmt)
        self.assertIn("jsonb_build_object('bang', 'm4.duyet_kt_cho', 'id', c.id)", stmt)
        self.assertIn('Cần lead', stmt)

    def test_cau_tu_choi_tieng_viet_khong_khoa_ky_thuat(self):
        messages = re.findall(r"RAISE EXCEPTION '([^']*cần chọn dự án[^']*)'", '\n'.join(MIGRATION))
        self.assertEqual(len(messages), 2)
        for message in messages:
            self.assertNotRegex(message.split(': ', 1)[1], r'M4:|master\.|m4\.|\bPN\b')

    def test_than_ham_dollar_day_du(self):
        for stmt in MIGRATION:
            if re.match(r'CREATE(?: OR REPLACE)? FUNCTION ', stmt):
                with self.subTest(function=stmt.splitlines()[0]):
                    self.assertIn('AS $$', stmt)
                    self.assertEqual(stmt.count('$$'), 2)
                    self.assertTrue(stmt.rstrip().endswith('$$'))


class _M4DocPgFixture:
    nguoi = nen.MtqPostgres.nguoi
    actor = nen.MtqPostgres.actor
    ghi = nen.MtqPostgres.ghi
    nhap = nen.MtqPostgres.nhap
    sua_nhap = nen.MtqPostgres.sua_nhap
    san_sang = nen.MtqPostgres.san_sang
    insert = ho_so.MtqM4HoSoPostgres.insert
    fixture = ho_so.MtqM4HoSoPostgres.fixture
    legacy = ho_so.MtqM4HoSoPostgres.legacy
    configure = ho_so.MtqM4HoSoPostgres.configure

    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = 'kho_test_mtq_m4_doc_' + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as c:
            c.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_web') THEN CREATE ROLE app_web NOLOGIN; END IF; END $$")
            c.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.c = psycopg.connect(make_conninfo(DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c, target=POSITION)
        cls.old_policies = cls.c.execute(
            "SELECT schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check FROM pg_policies "
            "WHERE (schemaname='m4' AND tablename=ANY(%s)) OR "
            "(schemaname='master' AND policyname IN ('hop_dong_m4_rang_buoc','hop_dong_m4_du_an'))",
            (list(TABLES),)).fetchall()
        postgres.migrate(cls.c)

    def setUp(self):
        nen.MtqPostgres.setUp(self)
        # Fixture M0055 dùng các trigger thật: đối tác + mapping cùng PN,
        # chủ bảng ghi nguồn, baseline master, FK tệp/PL/BOQ/đợt đầy đủ.
        self.f = self.fixture(self.pn)
        self.g = self.fixture(self.pn, da=self.f['da'])
        self.h = self.fixture(self.pn)
        self.chep(self.f)
        self.chep(self.g)
        self.chep(self.h)
        self.insert('m4.nhat_ky', du_an_id=self.f['da'], hanh_dong='TAI_TEP', boi=self.admin[1])
        self.actor(self.user)

    def chep(self, f):
        source = uuid.uuid4().hex
        self.c.execute("INSERT INTO m4.review_chep_nguon(id,nhap_boi,chup_luc) VALUES (%s,%s,now())", (source, self.admin[1]))
        self.c.execute("INSERT INTO m4.review_chep_hop_dong(nguon_id,ma_hd,hop_dong_id,du_an_id,so_hd,dong_sha256,nhap_boi) "
                       "VALUES (%s,'GIA',%s,%s,%s,%s,%s)", (source, f['hd'], f['da'], uuid.uuid4().hex, 'a' * 64, self.admin[1]))
        self.c.execute("INSERT INTO m4.review_chep_phu_luc(nguon_id,ma_hd,hop_dong_id,du_an_id,id,so_pl,ngay_ky,ngay_hieu_luc,doi_boq,trang_thai,dong_sha256,nhap_boi) "
                       "VALUES (%s,'GIA',%s,%s,1,'PL-GIA','2026-01-01','2026-01-01',0,'Đã ký',%s,%s)",
                       (source, f['hd'], f['da'], 'a' * 64, self.admin[1]))
        self.c.execute("INSERT INTO m4.review_chep_thay_doi_tham_so(nguon_id,pl_id,du_an_id,ma_ts,dong_sha256,nhap_boi) "
                       "VALUES (%s,1,%s,'TC-01',%s,%s)", (source, f['da'], 'a' * 64, self.admin[1]))
        self.c.execute("INSERT INTO m4.review_chep_dot_thanh_toan(nguon_id,ma_hd,hop_dong_id,du_an_id,dot,dong_sha256,nhap_boi) "
                       "VALUES (%s,'GIA',%s,%s,1,%s,%s)", (source, f['hd'], f['da'], 'a' * 64, self.admin[1]))
        self.c.execute("INSERT INTO m4.review_chep_kl_thanh_toan(nguon_id,ma_hd,dot,ma_hm,du_an_id,dong_sha256,nhap_boi) "
                       "VALUES (%s,'GIA',1,'GIA',%s,%s,%s)", (source, f['da'], 'a' * 64, self.admin[1]))

    def oracle(self):
        from psycopg import sql

        for name in set(AFTER) & set(BEFORE):
            stmt = BEFORE[name]
            if stmt.startswith('CREATE FUNCTION '):
                stmt = stmt.replace('CREATE FUNCTION ', 'CREATE OR REPLACE FUNCTION ', 1)
            self.c.execute(stmt)
        for schema, table, name, mode, roles, cmd, qual, check in self.old_policies:
            target = sql.Identifier(schema, table)
            self.c.execute(sql.SQL('DROP POLICY {} ON {}').format(sql.Identifier(name), target))
            stmt = sql.SQL('CREATE POLICY {} ON {} AS {} FOR {} TO {} USING ({})').format(
                sql.Identifier(name), target, sql.SQL(mode), sql.SQL(cmd),
                sql.SQL(',').join(sql.SQL('PUBLIC') if r == 'public' else sql.Identifier(r) for r in roles), sql.SQL(qual))
            if check:
                stmt += sql.SQL(' WITH CHECK ({})').format(sql.SQL(check))
            self.c.execute(stmt)

    def snapshot(self, oracle=False, selectors=False):
        from psycopg import sql

        with self.c.transaction():
            # Luôn rollback cả policy/hàm oracle và SET ROLE, không để trạng
            # thái thử thấm sang lần so sau. Không sửa dữ liệu hay tắt trigger.
            self.c.execute('SAVEPOINT m4_doc_oracle')
            try:
                if oracle:
                    self.oracle()
                self.c.execute('SET LOCAL ROLE app_web')
                result = {}
                for table in TABLES:
                    target = sql.Identifier('m4', table)
                    rows = self.c.execute(sql.SQL('SELECT to_jsonb(t) FROM {} t ORDER BY to_jsonb(t)::text').format(target)).fetchall()
                    count = self.c.execute(sql.SQL('SELECT count(*) FROM {}').format(target)).fetchone()[0]
                    self.assertEqual(count, len(rows), table)
                    result[table] = [r[0] for r in rows]
                result['detail'] = self.c.execute('SELECT to_jsonb(h) FROM m4.ho_so_hop_dong h WHERE hop_dong_id=%s', (self.f['hd'],)).fetchall()
                result['master'] = self.c.execute('SELECT m4.master_can_cu_doc(%s)', (self.f['hd'],)).fetchone()[0]
                if selectors:
                    for name in ('master_hop_dong_ds', 'master_doi_tac_ds'):
                        result[name] = self.c.execute('SELECT m4.' + name + "(%s,'',50)", (self.f['da'],)).fetchone()[0]
                return result
            finally:
                self.c.execute('ROLLBACK TO SAVEPOINT m4_doc_oracle')
                self.c.execute('RELEASE SAVEPOINT m4_doc_oracle')


@unittest.skipUnless(DSN and psycopg is not None, 'NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG')
class MtqM4DocPostgres(_M4DocPgFixture, unittest.TestCase):
    def test_pn_tat_so_oracle_danh_sach_chi_tiet_so_dem(self):
        self.legacy(self.f, self.h)
        self.assertEqual(self.snapshot(), self.snapshot(oracle=True))

    def test_pn_tat_reviewer_giu_han_che_nhap_va_tep(self):
        self.c.execute("INSERT INTO master.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,ARRAY['M4'])", (self.user[0], self.pn))
        for f in (self.f, self.h):
            self.insert('m4.quyen_du_an', nguoi_dung_id=self.user[0], phap_nhan_id=self.pn, du_an_id=f['da'], vai='REVIEW')
        actual = self.snapshot()
        self.assertEqual(actual, self.snapshot(oracle=True))
        self.assertEqual(actual['dot'], [])
        self.assertTrue(actual['ho_so_hop_dong'])
        self.assertFalse(any(r['vai_tro_tai_lieu'] == 'HO_SO_DOT' for r in actual['tep']))

    def test_pn_tat_bo_chon_so_oracle(self):
        self.legacy(self.f)
        self.assertEqual(self.snapshot(selectors=True), self.snapshot(oracle=True, selectors=True))

    def test_pn_bat_pham_vi_du_an_va_dem(self):
        self.configure(actions=('XEM',), scope='DU_AN', key=self.f['da'])
        result = self.snapshot()
        expected = {str(self.f['hd']), str(self.g['hd'])}
        for table in ('ho_so_hop_dong', 'phu_luc', 'boq', 'dot', 'master_can_cu', 'review_chep_hop_dong'):
            self.assertEqual({r['hop_dong_id'] for r in result[table]}, expected, table)
        self.assertEqual(len(result['detail']), 1)
        self.assertIsNotNone(result['master'])
        self.assertEqual({r['du_an_id'] for r in result['tep']}, {str(self.f['da'])})
        self.assertEqual(len(result['review_chep_thay_doi_tham_so']), 2)
        self.assertEqual(len(result['review_chep_kl_thanh_toan']), 2)

    def test_pn_bat_pham_vi_hop_dong_khong_lan_ca_du_an(self):
        self.configure(actions=('XEM',), scope='HOP_DONG', key=self.f['hd'])
        result = self.snapshot()
        for table in ('ho_so_hop_dong', 'phu_luc', 'boq', 'dot', 'master_can_cu', 'review_chep_hop_dong'):
            self.assertEqual({r['hop_dong_id'] for r in result[table]}, {str(self.f['hd'])}, table)
        # Resolver M0048 của tệp chỉ có dự án: không đoán một HĐ để cấp tải.
        self.assertEqual(result['tep'], [])
        self.assertEqual(len(result['review_chep_thay_doi_tham_so']), 1)
        self.assertEqual(len(result['review_chep_kl_thanh_toan']), 1)

    def test_cung_pham_vi_review_chi_da_nop_ho_so_xem_ca_nhap(self):
        # Nộp bằng lệnh thật khi PN tắt; giữ nguyên trigger và căn cứ M17.
        self.legacy(self.f)
        self.c.execute('SELECT m4.nop(%s,%s,1,1)', (uuid.uuid4().hex, self.f['dot']))
        owner = self.nguoi('XEM')
        self.actor(self.admin)
        version = self.nhap()
        for phong in (self.phong, self.phong2):
            for vai in nen.VAI:
                row = self.sua_nhap(version, 'DONG', {'phong_id': phong, 'vai': vai, 'gioi_han_vnd': 0})
                if phong == self.phong and vai in ('TRUONG_PHONG', 'NGUOI_XEM'):
                    self.sua_nhap(version, 'O', {'dong_id': row['id'], 'module': 'M4',
                        'man': '02A_REVIEW' if vai == 'TRUONG_PHONG' else 'HO_SO',
                        'hanh_dong': 'XEM', 'cho_phep': True})
        self.sua_nhap(version, 'CONG_BO', {})
        for actor, vai in ((self.user, 'TRUONG_PHONG'), (owner, 'NGUOI_XEM')):
            grant = self.ghi('GAN_VAI', {'nguoi_dung_id': str(actor[0]), 'phap_nhan_id': str(self.pn),
                'phong_id': self.phong, 'vai': vai})
            self.ghi('PHAM_VI', {'gan_vai_id': grant['id'], 'phap_nhan_id': str(self.pn),
                'loai': 'DU_AN', 'khoa': str(self.f['da'])})
        self.san_sang()
        self.ghi('KICH_HOAT', {'phap_nhan_id': str(self.pn), 'phien_ban_id': version['id'], 'bat': True})
        self.actor(self.user)
        review = self.snapshot()
        self.assertEqual({r['id'] for r in review['dot']}, {str(self.f['dot'])})
        self.assertEqual({r['dot_id'] for r in review['dot_tep']}, {str(self.f['dot'])})
        self.assertEqual({r['id'] for r in review['tep']}, {str(self.f['t_dot'])})
        self.actor(owner)
        ho_so_doc = self.snapshot()
        self.assertEqual({r['id'] for r in ho_so_doc['dot']}, {str(self.f['dot']), str(self.g['dot'])})
        self.assertEqual({r['dot_id'] for r in ho_so_doc['dot_tep']}, {str(self.f['dot']), str(self.g['dot'])})
        self.assertEqual({r['id'] for r in ho_so_doc['tep']},
                         {str(f[key]) for f in (self.f, self.g) for key in ('t_hd', 't_hd2', 't_pl', 't_boq', 't_dot')})

    def test_khong_tick_xem_khong_fallback_soan_cu(self):
        self.legacy(self.f, self.h)
        self.configure(actions=(), scope='PHAP_NHAN')
        result = self.snapshot()
        self.assertTrue(all(result[t] == [] for t in TABLES))
        self.assertEqual(result['detail'], [])
        self.assertIsNone(result['master'])

    def test_b6_lap_co_du_an_khong_can_xem_va_khong_lo_hd_crm(self):
        crm = self.fixture(self.pn, da=self.f['da'], module=None)
        self.configure(actions=('LAP',), scope='DU_AN', key=self.f['da'])
        with self.c.transaction():
            self.c.execute('SET LOCAL ROLE app_web')
            self.assertTrue(self.c.execute('SELECT m4.mau_duoc(%s)', (self.f['da'],)).fetchone()[0])
            self.assertFalse(self.c.execute('SELECT m4.mau_duoc(NULL)').fetchone()[0])
            self.assertFalse(self.c.execute('SELECT m4.mau_duoc(%s)', (self.h['da'],)).fetchone()[0])
            result = self.c.execute("SELECT m4.master_hop_dong_ds(%s,'',50)", (self.f['da'],)).fetchone()[0]
            self.assertEqual({r['hop_dong_id'] for r in result['items']}, {str(self.f['hd']), str(self.g['hd'])})
            self.assertNotIn(str(crm['hd']), str(result))
            self.assertTrue(self.c.execute("SELECT m4.master_doi_tac_ds(%s,'',50)", (self.f['da'],)).fetchone()[0]['items'])
            self.assertEqual(self.c.execute('SELECT id FROM master.hop_dong WHERE id=%s', (crm['hd'],)).fetchall(), [])

    def test_b6_xem_khong_suy_thanh_lap_va_thieu_du_an_bi_chan(self):
        self.configure(actions=('XEM',), scope='DU_AN', key=self.f['da'])
        for name in ('master_hop_dong_ds', 'master_doi_tac_ds'):
            for project in (self.f['da'], None, uuid.uuid4()):
                with self.subTest(name=name, project=project):
                    with self.assertRaises(psycopg.Error) as cm:
                        with self.c.transaction():
                            self.c.execute('SET LOCAL ROLE app_web')
                            self.c.execute('SELECT m4.' + name + "(%s,'',50)", (project,))
                    self.assertIn('cần chọn dự án', str(cm.exception))

    def test_bo_chon_limit_100_bi_chan(self):
        self.configure(actions=('LAP',), scope='DU_AN', key=self.f['da'])
        for name in ('master_hop_dong_ds', 'master_doi_tac_ds'):
            with self.subTest(name=name):
                with self.assertRaises(psycopg.Error) as cm:
                    with self.c.transaction():
                        self.c.execute('SET LOCAL ROLE app_web')
                        self.c.execute('SELECT m4.' + name + "(%s,'',100)", (self.f['da'],))
                self.assertIn('M4_THAM_SO_SAI', str(cm.exception))

    def test_pn_a_bat_khong_doi_pn_b_tat(self):
        b = self.fixture(self.pn2)
        self.legacy(b)
        before = self.snapshot()
        self.configure(actions=(), scope='PHAP_NHAN')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.snapshot(), self.snapshot(oracle=True))

    def test_hd_crm_khong_mo_bang_quyen_xem_m4(self):
        crm = self.fixture(self.pn, da=self.f['da'], module=None)
        self.configure(actions=('XEM',), scope='DU_AN', key=self.f['da'])
        with self.c.transaction():
            self.c.execute('SET LOCAL ROLE app_web')
            self.assertFalse(self.c.execute("SELECT m4.mtq_ho_so_doc('master.hop_dong',%s,'XEM')", (crm['hd'],)).fetchone()[0])
            self.assertFalse(self.c.execute('SELECT m4.mc_co_ho_so(%s,%s)', (crm['hd'], crm['da'])).fetchone()[0])
            self.assertIsNone(self.c.execute('SELECT m4.master_can_cu_doc(%s)', (crm['hd'],)).fetchone()[0])
            rows = self.c.execute('SELECT id FROM master.hop_dong').fetchall()
            self.assertIn((self.f['hd'],), rows)
            self.assertNotIn((crm['hd'],), rows)

    def test_thu_hoi_pham_vi_chan_lan_doc_tiep(self):
        scope = self.configure(actions=('XEM',), scope='DU_AN', key=self.f['da'])
        self.assertTrue(self.snapshot()['detail'])
        self.actor(self.admin)
        self.ghi('THU_HOI_PHAM_VI', {'id': scope['id']}, scope['revision'])
        self.actor(self.user)
        self.assertEqual(self.snapshot()['detail'], [])

    def test_review_chep_hien_hanh_loc_owner_khong_mo_nguon_app(self):
        source = uuid.uuid4().hex
        self.c.execute("INSERT INTO m4.review_chep_nguon(id,nhap_boi,chup_luc) VALUES (%s,%s,now()+interval '1 second')", (source, self.admin[1]))
        self.c.execute("INSERT INTO m4.review_chep_hop_dong(nguon_id,ma_hd,hop_dong_id,du_an_id,so_hd,dong_sha256,nhap_boi) "
                       "VALUES (%s,'GIA',%s,%s,'GIA',%s,%s)", (source, self.f['hd'], self.f['da'], 'b' * 64, self.admin[1]))
        self.configure(actions=('XEM',), scope='HOP_DONG', key=self.f['hd'])
        self.assertEqual(self.c.execute('SELECT m4.review_chep_hien_hanh(%s)', (self.f['hd'],)).fetchone()[0], source)
        self.assertIsNone(self.c.execute('SELECT m4.review_chep_hien_hanh(%s)', (self.g['hd'],)).fetchone()[0])
        self.assertFalse(self.c.execute("SELECT has_table_privilege('app_web','m4.review_chep_nguon','SELECT')").fetchone()[0])


@unittest.skipUnless(DSN and psycopg is not None, 'NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG')
class MtqM4DocReadOnlyPostgres(_M4DocPgFixture, unittest.TestCase):
    def test_read_only_doc_dem_chi_tiet_va_bo_chon(self):
        self.configure(actions=('XEM', 'LAP'), scope='DU_AN', key=self.f['da'])
        # Dữ liệu giả được commit trong kho_test_* trước BEGIN READ ONLY thật.
        # CSDL được giữ theo guard; cleanup của setUp rollback phiên đọc.
        self.c.execute('COMMIT')
        self.c.execute('BEGIN READ ONLY')
        self.actor(self.user)
        self.c.execute('SET LOCAL ROLE app_web')
        self.assertEqual(self.c.execute('SHOW transaction_read_only').fetchone()[0], 'on')
        self.assertEqual(self.c.execute('SELECT count(*) FROM m4.ho_so_hop_dong').fetchone()[0], 2)
        self.assertIsNotNone(self.c.execute('SELECT m4.master_can_cu_doc(%s)', (self.f['hd'],)).fetchone()[0])
        self.assertIsNotNone(self.c.execute('SELECT m4.digest_tham_so(%s)', (self.f['hd'],)).fetchone()[0])
        self.assertTrue(self.c.execute('SELECT m4.tep_da_nop(%s)', (self.f['t_hd'],)).fetchone()[0] is False)
        self.assertEqual(self.c.execute('SELECT m4.thieu(%s)', (self.f['dot'],)).fetchone()[0], [])
        self.assertEqual(len(self.c.execute("SELECT m4.master_hop_dong_ds(%s,'',50)", (self.f['da'],)).fetchone()[0]['items']), 2)
        self.assertTrue(self.c.execute("SELECT m4.master_doi_tac_ds(%s,'',50)", (self.f['da'],)).fetchone()[0]['items'])


if __name__ == '__main__':
    unittest.main()
