"""G2-04: mock và PG16 tự tạo kho_test_*, không khởi động/dọn dịch vụ.

Ca audit dùng LOGIN Core thật. Migration dùng provisioning của lead, không
SET ROLE đóng giả owner. G2-25 mới mở cửa áp gói cho login cài đặt.
Không DROP ROLE/DATABASE; lead dọn tài nguyên test sau.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import traceback
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import doi_cau_truc as dc, phien

try:
    from .test_g2_01 import _kiem_dich_test, psycopg
except ImportError:
    from test_g2_01 import _kiem_dich_test, psycopg

if psycopg is not None:
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict

SQL_KIEM_TOAN = (dc.THU_MUC_SQL / '004_kiem_toan.sql').read_text(encoding='utf-8')
CAC_TEP = sorted(dc.THU_MUC_SQL.glob('[0-9][0-9][0-9]_*.sql'))[:4]
ADMIN_DSN = os.environ.get('KHO_PG_DSN_TEST')


class DoiCauTrucThuanTest(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.cur = self.conn.cursor.return_value.__enter__.return_value
        self.cur.fetchone.side_effect = [('kho_test_g2_04_mock',), ('loi.lich_su_doi_cau_truc',)]
        self.cur.fetchall.return_value = []
        self.tep = [Path('001_demo.sql'), Path('002_demo.sql')]

    def _ap(self, noi_dung=(b'SELECT 1', b'SELECT 2'), **kwargs):
        with patch.object(Path, 'read_bytes', side_effect=noi_dung):
            return dc.ap_doi_cau_truc(self.conn, self.tep, **kwargs)

    def test_thu_tu_checksum_bind_va_cung_transaction(self):
        self.assertEqual(self._ap(), 2)
        cac_lenh = self.cur.execute.call_args_list
        them = [c.args for c in cac_lenh if c.args[0].startswith('INSERT INTO')]
        self.assertEqual([c[1][1] for c in them], [1, 2])
        self.assertEqual(them[0][1][2], hashlib.sha256(b'SELECT 1').hexdigest())
        self.assertEqual(json.loads(them[0][1][3]), dc.NGUON_CORE)
        self.assertNotIn('core', them[0][0])  # dữ liệu gói được bind
        self.conn.transaction.assert_called_once_with()
        self.conn.commit.assert_not_called()

    def test_chay_lai_khong_ap_sql_hoac_them_so(self):
        self.cur.fetchall.return_value = [(1, hashlib.sha256(b'SELECT 1').hexdigest()),
                                         (2, hashlib.sha256(b'SELECT 2').hexdigest())]
        self.assertEqual(self._ap(), 2)
        lenh = [c.args[0] for c in self.cur.execute.call_args_list]
        self.assertNotIn('SELECT 1', lenh)
        self.assertNotIn('SELECT 2', lenh)
        self.assertFalse(any(s.startswith('INSERT') for s in lenh))

    def test_lech_checksum_chan_truoc_ddl(self):
        self.cur.fetchall.return_value = [(1, '0' * 64)]
        with self.assertRaises(dc.LoiDoiCauTruc) as bat:
            self._ap()
        self.assertEqual(bat.exception.ma, 'MIGRATION_CHANGED')
        self.assertNotIn('SELECT 2', [c.args[0] for c in self.cur.execute.call_args_list])

    def test_chan_ha_phien_ban_va_so_thieu_dong(self):
        for lich_su, dich, ma in (([(1, 'a'), (2, 'b')], 1, 'FUTURE_SCHEMA'),
                                  ([(2, 'b')], 2, 'MIGRATION_ORDER')):
            with self.subTest(ma=ma):
                self.setUp()
                self.cur.fetchall.return_value = lich_su
                with self.assertRaises(dc.LoiDoiCauTruc) as bat:
                    self._ap(so_phien_ban=dich)
                self.assertEqual(bat.exception.ma, ma)

    def test_loi_sql_thoat_transaction_bang_exception_va_an_dsn(self):
        bi_mat = 'postgresql://CANARY:BI_MAT@localhost/kho_test_demo'
        def thuc_hien(cau_sql, *args):
            if cau_sql == 'SELECT 2':
                raise RuntimeError(bi_mat)
        self.cur.execute.side_effect = thuc_hien
        with self.assertRaises(dc.LoiDoiCauTruc) as bat:
            self._ap()
        self.assertEqual(bat.exception.ma, 'DOI_CAU_TRUC_THAT_BAI')
        thoat = self.conn.transaction.return_value.__exit__.call_args.args
        self.assertIs(thoat[0], RuntimeError)
        self.assertNotIn(bi_mat, ''.join(traceback.format_exception(bat.exception)))
        self.assertIsNone(bat.exception.__context__)
        self.assertIsNone(bat.exception.__cause__)

    def test_tu_choi_dich_that_truoc_ddl(self):
        self.cur.fetchone.side_effect = [('kho_that',)]
        with self.assertRaises(dc.LoiDoiCauTruc) as bat:
            self._ap()
        self.assertEqual(bat.exception.ma, 'DICH_KHONG_AN_TOAN')
        self.assertEqual(self.cur.execute.call_count, 1)

    def test_loi_ket_noi_khong_lo_dsn(self):
        bi_mat = 'postgresql://CANARY:BI_MAT@localhost/kho_test_demo'
        self.conn.transaction.side_effect = RuntimeError(bi_mat)
        with self.assertRaises(dc.LoiDoiCauTruc) as bat:
            self._ap()
        self.assertNotIn(bi_mat, ''.join(traceback.format_exception(bat.exception)))
        self.assertIsNone(bat.exception.__context__)

    def test_thieu_so_khong_commit_bootstrap_nua_chung(self):
        self.cur.fetchone.side_effect = [('kho_test_demo',), (None,)]
        with self.assertRaises(dc.LoiDoiCauTruc) as bat:
            self._ap()
        self.assertEqual(bat.exception.ma, 'CAN_BOOTSTRAP_004')

    def test_bootstrap_ghi_bon_dong_ngay_sau_004_truoc_005(self):
        self.cur.fetchone.side_effect = [('kho_test_demo',), (None,), (None,), (None,),
                                       (None,), ('loi.lich_su_doi_cau_truc',)]
        with patch.object(Path, 'read_bytes', side_effect=[f'SELECT {n}'.encode() for n in range(1, 6)]):
            dc.ap_doi_cau_truc(self.conn, [Path(f'{n:03d}_demo.sql') for n in range(1, 6)])
        lenh = [c.args for c in self.cur.execute.call_args_list]
        vi_tri_5 = next(i for i, c in enumerate(lenh) if c[0] == 'SELECT 5')
        self.assertEqual(sum(c[0].startswith('INSERT INTO') for c in lenh[:vi_tri_5]), 4)

    def test_sai_thu_tu_va_dich_khong_chay_sql(self):
        for tep in ([Path('002_demo.sql')], [Path('001_demo.sql'), Path('001_khac.sql')]):
            with self.subTest(tep=tep), patch.object(Path, 'read_bytes', return_value=b'SELECT 1'):
                with self.assertRaises(dc.LoiDoiCauTruc):
                    dc.ap_doi_cau_truc(self.conn, tep)
        for dich in (True, 0, 3, '1'):
            with self.subTest(dich=dich), self.assertRaises(dc.LoiDoiCauTruc):
                self._ap(so_phien_ban=dich)
        self.conn.transaction.assert_not_called()

    def test_lineage_chi_la_can_cu_khong_gia_lich_su_cu(self):
        self.assertEqual(dc.NGUON_CORE['loai'], 'DUNG_MOI')
        self.assertEqual(dc.NGUON_CORE['lineage_doi_chieu'],
                         ['M0013_COMMON', 'M0017_SQL_IMPORT_HIEN_HANH'])
        self.assertNotIn('ha_tang.pg_migrations', Path(dc.__file__).read_text(encoding='utf-8'))


@unittest.skipUnless(psycopg is not None and ADMIN_DSN,
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class KiemToanPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.thong_tin = _kiem_dich_test(conninfo_to_dict(ADMIN_DSN))
        cls.admin = psycopg.connect(**cls.thong_tin, autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        if cls.admin.info.server_version < 160000 or not cls.admin.execute(
            'SELECT rolsuper FROM pg_roles WHERE rolname=current_user').fetchone()[0]:
            raise RuntimeError('Cần lead provisioning admin PG16+')
        ma = uuid4().hex[:12]
        cls.db = 'kho_test_g2_04_' + ma
        cls.tien_to = 'ktt_test_g204_' + ma + '_'
        cls.login = cls.tien_to + 'dang_nhap_loi'
        cls.admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(cls.db)))
        cls.conn = psycopg.connect(**{**cls.thong_tin, 'dbname': cls.db}, autocommit=True)
        cls.addClassCleanup(cls.conn.close)
        cls.conn.execute('SELECT set_config(%s,%s,false)', ('kho_tri_thuc.tien_to_vai', cls.tien_to))
        cls.conn.execute('SET log_parameter_max_length = 0')
        cls.conn.execute('SET log_parameter_max_length_on_error = 0')
        dc.ap_doi_cau_truc(cls.conn, CAC_TEP)
        mat_khau = secrets.token_urlsafe(32)
        cls.conn.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(
            sql.Identifier(cls.login), sql.Literal(mat_khau)))
        for ten in ('log_parameter_max_length', 'log_parameter_max_length_on_error'):
            cls.conn.execute(sql.SQL('ALTER ROLE {} SET {}=0').format(
                sql.Identifier(cls.login), sql.Identifier(ten)))
        cls.core = psycopg.connect(**{**cls.thong_tin, 'dbname': cls.db,
                                     'user': cls.login, 'password': mat_khau}, autocommit=True)
        cls.addClassCleanup(cls.core.close)
        # Giữ DB/role cho lead đối soát và dọn; không DROP hoặc thay membership.

    def _ghi(self, **doi):
        tham_so = dict(hanh_dong='DOC', doi_tuong='tai_lieu', doi_tuong_id=uuid4(),
                       ket_luan='DAT', ma=None, module=None, pn=None)
        tham_so.update(doi)
        return self.core.execute('SELECT loi.ghi_kiem_toan(%s,%s,%s,%s,%s,%s,%s)',
                                 tuple(tham_so.values())).fetchone()[0]

    def test_audit_login_that_khong_tin_actor_guc(self):
        self.assertEqual(self.core.execute('SELECT current_user,session_user').fetchone(),
                         (self.login, self.login))
        nd, pn = uuid4(), uuid4()
        self.conn.execute("INSERT INTO loi.nguoi_dung(id,dang_nhap,ten,vai_tro) VALUES (%s,%s,'DEMO','XEM')",
                          (nd, 'demo_' + nd.hex))
        self.conn.execute("INSERT INTO loi.phap_nhan(id,ma,ten) VALUES (%s,%s,'DEMO')", (pn, pn.hex))
        p = phien.cap_phien(self.core, nguoi_dung_id=nd, module='CRM', phap_nhan_id=pn,
                            dang_nhap_csdl=self.login, pham_vi_hanh_dong=['DOC'],
                            hieu_luc_den=datetime.now(timezone.utc) + timedelta(minutes=5))
        with self.core.transaction():
            self.core.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true)", (str(uuid4()),))
            ma = self._ghi(ma=p.ma.lay_de_truyen(), module='CRM', pn=pn)
        dong = self.conn.execute('''SELECT nguoi_dung_id,phap_nhan_id,dang_nhap_csdl,tao_luc,
            row_to_json(n)::text FROM loi.nhat_ky_kiem_toan n WHERE id=%s''', (ma,)).fetchone()
        self.assertEqual(dong[:3], (nd, pn, self.login))
        self.assertIsNotNone(dong[3])
        self.assertNotIn(p.ma.lay_de_truyen(), dong[4])
        self.assertNotIn(str(p.id), dong[4])
        phien.thu_hoi_phien(self.core, ma=p.ma)
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self._ghi(ma=p.ma.lay_de_truyen(), module='CRM', pn=pn)

    def test_context_sai_khong_ha_xuong_audit_he_thong(self):
        for doi in ({'ma': 'GIA'}, {'module': 'CRM'}, {'pn': uuid4()}):
            with self.subTest(doi=doi), self.assertRaises(psycopg.errors.InsufficientPrivilege):
                self._ghi(**doi)

    def test_khong_nhan_toan_van_hoac_json_bi_mat(self):
        for doi in ({'doi_tuong': 'Toan van tai lieu demo'}, {'ket_luan': '{"secret":"CANARY"}'},
                    {'hanh_dong': 'DOC\nCANARY'}):
            with self.subTest(doi=doi), self.assertRaises(psycopg.errors.CheckViolation):
                self._ghi(**doi)

    def test_audit_bat_bien_ke_ca_khi_lo_cap_quyen_dml(self):
        ma = self._ghi()
        # Cố ý cấp thừa ACL đã commit để chứng minh trigger, vẫn LOGIN runtime.
        self.conn.execute(sql.SQL('GRANT UPDATE,DELETE,TRUNCATE ON loi.nhat_ky_kiem_toan TO {}').format(sql.Identifier(self.login)))
        try:
            for lenh in ('UPDATE loi.nhat_ky_kiem_toan SET ket_luan=\'LOI\'',
                         'DELETE FROM loi.nhat_ky_kiem_toan', 'TRUNCATE loi.nhat_ky_kiem_toan'):
                with self.subTest(lenh=lenh), self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
                    self.core.execute(lenh)
        finally:
            self.conn.execute(sql.SQL('REVOKE UPDATE,DELETE,TRUNCATE ON loi.nhat_ky_kiem_toan FROM {}').format(sql.Identifier(self.login)))
        self.assertEqual(self.conn.execute('SELECT ket_luan FROM loi.nhat_ky_kiem_toan WHERE id=%s', (ma,)).fetchone(), ('DAT',))

    def test_runtime_khong_ghi_truc_tiep_so_va_audit(self):
        for bang in ('nhat_ky_kiem_toan', 'lich_su_doi_cau_truc'):
            for lenh in (f'INSERT INTO loi.{bang} DEFAULT VALUES', f'UPDATE loi.{bang} SET tao_luc=now()'
                         if bang == 'nhat_ky_kiem_toan' else f'UPDATE loi.{bang} SET ma_bam=ma_bam',
                         f'DELETE FROM loi.{bang}', f'TRUNCATE loi.{bang}'):
                with self.subTest(lenh=lenh), self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    self.core.execute(lenh)

    def test_chay_lai_idempotent_va_checksum_dung_nguon(self):
        truoc = self.conn.execute('SELECT * FROM loi.lich_su_doi_cau_truc ORDER BY so_phien_ban').fetchall()
        self.assertEqual(dc.ap_doi_cau_truc(self.conn, CAC_TEP), 4)
        self.assertEqual(truoc, self.conn.execute('SELECT * FROM loi.lich_su_doi_cau_truc ORDER BY so_phien_ban').fetchall())
        self.assertEqual([d[2] for d in truoc], [hashlib.sha256(p.read_bytes()).hexdigest() for p in CAC_TEP])
        self.assertTrue(all(d[5] == dc.NGUON_CORE for d in truoc))

    def test_so_chan_checksum_ha_ban_va_sua_truc_tiep(self):
        for ban, bam, thong_diep in ((1, '0' * 64, 'MIGRATION_CHANGED'),
                                     (1, hashlib.sha256(CAC_TEP[0].read_bytes()).hexdigest(), 'FUTURE_SCHEMA'),
                                     (6, '0' * 64, 'MIGRATION_ORDER')):
            with self.subTest(ban=ban, thong_diep=thong_diep):
                with self.assertRaises(psycopg.errors.CheckViolation) as bat:
                    self.conn.execute('''INSERT INTO loi.lich_su_doi_cau_truc
                        (ma_goi,so_phien_ban,ma_bam,nguon_lich_su) VALUES ('core',%s,%s,'{}')''', (ban, bam))
                self.assertIn(thong_diep, str(bat.exception))
        for lenh in ("UPDATE loi.lich_su_doi_cau_truc SET ma_bam=ma_bam",
                     'DELETE FROM loi.lich_su_doi_cau_truc', 'TRUNCATE loi.lich_su_doi_cau_truc'):
            with self.subTest(lenh=lenh), self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
                self.conn.execute(lenh)

    def test_goi_doc_lap_va_nguoi_ap_dung_tu_session_user(self):
        goi = 'demo_' + uuid4().hex
        with self.conn.transaction(force_rollback=True):
            for ban in (1, 2):
                self.conn.execute('''INSERT INTO loi.lich_su_doi_cau_truc
                    (ma_goi,so_phien_ban,ma_bam,nguon_lich_su,nguoi_ap_dung)
                    VALUES (%s,%s,%s,'{}','GIA')''', (goi, ban, '0' * 64))
            self.assertEqual(self.conn.execute('''SELECT DISTINCT nguoi_ap_dung=session_user
                FROM loi.lich_su_doi_cau_truc WHERE ma_goi=%s''', (goi,)).fetchall(), [(True,)])

    def test_rollback_audit_cung_transaction_nghiep_vu(self):
        with self.core.transaction(force_rollback=True):
            ma = self._ghi()
        self.assertIsNone(self.conn.execute('SELECT id FROM loi.nhat_ky_kiem_toan WHERE id=%s', (ma,)).fetchone())

    def test_owner_policy_force_rls_va_cua_ghi_an_toan(self):
        chu = self.tien_to + 'vai_doi_cau_truc_loi'
        dong = self.conn.execute('''SELECT relname,pg_get_userbyid(relowner),relrowsecurity,relforcerowsecurity
            FROM pg_class WHERE oid IN ('loi.nhat_ky_kiem_toan'::regclass,
            'loi.lich_su_doi_cau_truc'::regclass)''').fetchall()
        self.assertEqual(len(dong), 2)
        self.assertTrue(all(d[1:] == (chu, True, True) for d in dong))
        ham = self.conn.execute('''SELECT pg_get_userbyid(proowner),prosecdef,proconfig
            FROM pg_proc WHERE pronamespace='loi'::regnamespace AND proname='ghi_kiem_toan' ''').fetchone()
        self.assertEqual(ham, (chu, True, ['search_path=pg_catalog, pg_temp']))

    def test_lech_checksum_chan(self):
        truoc = self.conn.execute('SELECT count(*) FROM loi.lich_su_doi_cau_truc').fetchone()
        doc_goc = Path.read_bytes
        def doc(tep):
            return doc_goc(tep) + (b'\n-- changed' if tep == CAC_TEP[0] else b'')
        with patch.object(Path, 'read_bytes', doc), self.assertRaises(dc.LoiDoiCauTruc) as bat:
            dc.ap_doi_cau_truc(self.conn, CAC_TEP)
        self.assertEqual(bat.exception.ma, 'MIGRATION_CHANGED')
        self.assertEqual(truoc, self.conn.execute('SELECT count(*) FROM loi.lich_su_doi_cau_truc').fetchone())

    def test_ha_phien_ban_chan(self):
        with self.assertRaises(dc.LoiDoiCauTruc) as bat:
            dc.ap_doi_cau_truc(self.conn, CAC_TEP, so_phien_ban=3)
        self.assertEqual(bat.exception.ma, 'FUTURE_SCHEMA')

    def test_loi_sql_rollback_ca_so_va_ddl_trong_transaction_ngoai(self):
        truoc = self.conn.execute('SELECT count(*) FROM loi.lich_su_doi_cau_truc').fetchone()
        doc_goc = Path.read_bytes
        def doc(tep):
            if tep.name == '005_demo.sql':
                return b'CREATE TABLE loi.g204_demo(id integer)'
            if tep.name == '006_demo.sql':
                return b'SELECT 1/0'
            return doc_goc(tep)
        with self.conn.transaction(), patch.object(Path, 'read_bytes', doc):
            with self.assertRaises(dc.LoiDoiCauTruc):
                dc.ap_doi_cau_truc(self.conn, [*CAC_TEP, Path('005_demo.sql'), Path('006_demo.sql')])
            self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.lich_su_doi_cau_truc').fetchone(), truoc)
            self.assertIsNone(self.conn.execute("SELECT to_regclass('loi.g204_demo')").fetchone()[0])

    def test_sql_chay_lai_khong_noi_quyen(self):
        self.conn.execute(SQL_KIEM_TOAN)
        self.test_runtime_khong_ghi_truc_tiep_so_va_audit()


if __name__ == '__main__':
    unittest.main()
