"""G2-11: thuần/mock; PG tạo kho_test_* qua fixture G2-09, runtime login thật.

Không DROP/cleanup dữ liệu, không khởi động hoặc dừng dịch vụ. Chỉ PG khi có
KHO_PG_DSN_TEST. Admin dựng fixture và mốc thời gian; không làm nghiệp vụ.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import traceback
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import tiep_nhan as tn, doi_cau_truc as dc, phien

try:
    from . import test_g2_04 as g204
    from . import test_g2_09 as g209
except ImportError:
    import test_g2_04 as g204
    import test_g2_09 as g209

psycopg = g209.psycopg
if psycopg is not None:
    from psycopg import sql

SQL_PATH = dc.THU_MUC_SQL / '011_tiep_nhan.sql'
SQL = SQL_PATH.read_text(encoding='utf-8')
LAP, XEM = g209.LAP, g209.XEM
BAM = 'a' * 64
KHOA = 'demo-khoa-0000001'


class TiepNhanThuanTest(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.conn.info.transaction_status = 2
        self.ctx = dict(ma=phien.MaBiMat('CANARY_PHIEN'), module='crm',
            phap_nhan_id=uuid4(), hanh_dong=LAP)
        self.ts = dict(operation='CRM.DEMO.LAP', khoa=KHOA, noi_dung={'b': 2, 'a': 1},
            doi_tuong=dict(bang='doi_tuong', id=str(uuid4())), **self.ctx)
        self.quyen = dict(hanh_dong=XEM, doi_tuong=self.ts['doi_tuong'], phien_ban_contract='1')

    def test_giu_ket_noi_bind_va_khong_tu_transaction_commit(self):
        tn.ghi_thao_tac(self.conn, ket_qua={'id': 'DEMO'}, quyen_doc=self.quyen, **self.ts)
        cau, ts = self.conn.execute.call_args.args
        self.assertIn('ghi_bien_nhan_thao_tac_v2', cau)
        self.assertNotIn('CANARY', cau)
        self.assertEqual(ts[:4], ('CANARY_PHIEN', 'crm', self.ctx['phap_nhan_id'], LAP))
        than = json.loads(ts[6])
        self.assertEqual(than['phap_nhan_id'], str(self.ctx['phap_nhan_id']))
        self.assertEqual(than['doi_tuong'], self.ts['doi_tuong'])
        self.assertEqual(than['noi_dung'], self.ts['noi_dung'])
        for ten in ('connect', 'commit', 'rollback', 'transaction'):
            getattr(self.conn, ten).assert_not_called()

    def test_can_transaction_dang_mo(self):
        for trang_thai in (0, 1, 3, 4):
            self.conn.info.transaction_status = trang_thai
            with self.subTest(trang_thai=trang_thai), self.assertRaises(ValueError):
                tn.tra_thao_tac(self.conn, **self.ts)
        self.conn.execute.assert_not_called()

    def test_body_chuan_hoa_khong_phu_thuoc_thu_tu_json(self):
        tn.tra_thao_tac(self.conn, **self.ts)
        truoc = self.conn.execute.call_args.args[1][6]
        tn.tra_thao_tac(self.conn, **{**self.ts, 'noi_dung': {'a': 1, 'b': 2}})
        self.assertEqual(truoc, self.conn.execute.call_args.args[1][6])
        for ngoai in ('path', 'method', 'client_key'):
            self.assertNotIn(ngoai, json.loads(truoc))

    def test_replay_khong_goi_nghiep_vu_va_khong_ghi_lai(self):
        cu = dict(ket_qua={'id': 'DEMO'}, lap_lai=True)
        self.conn.execute.return_value.fetchone.return_value = (cu,)
        nghiep_vu = MagicMock()
        self.assertEqual(tn.thuc_hien_thao_tac(self.conn, thuc_hien=nghiep_vu,
            quyen_doc=self.quyen, **self.ts), cu)
        nghiep_vu.assert_not_called()
        self.assertEqual(self.conn.execute.call_count, 1)

    def test_nghiep_vu_nhan_dung_conn_truoc_ghi_bien_nhan(self):
        self.conn.execute.return_value.fetchone.side_effect = [(None,), ({'lap_lai': False},)]
        def nghiep_vu(conn):
            self.assertIs(conn, self.conn)
            self.assertEqual(self.conn.execute.call_count, 1)
            return {'id': 'DEMO'}
        tn.thuc_hien_thao_tac(self.conn, thuc_hien=nghiep_vu, quyen_doc=self.quyen, **self.ts)
        self.assertEqual(self.conn.execute.call_count, 2)
        self.assertIn('ghi_bien_nhan_thao_tac_v2', self.conn.execute.call_args.args[0])

    def test_nghiep_vu_loi_khong_ghi_bien_nhan(self):
        self.conn.execute.return_value.fetchone.return_value = (None,)
        def nghiep_vu(conn):
            raise RuntimeError('DEMO_ROLLBACK')
        with self.assertRaisesRegex(RuntimeError, 'DEMO_ROLLBACK'):
            tn.thuc_hien_thao_tac(self.conn, thuc_hien=nghiep_vu, quyen_doc=self.quyen, **self.ts)
        self.assertEqual(self.conn.execute.call_count, 1)

    def test_khoa_noi_dung_va_context_khong_hop_le(self):
        for doi in ({'khoa': 'ngan'}, {'khoa': 'x'*129}, {'khoa': 'x'*16+'ắ'},
                    {'operation': 'x;SELECT'}, {'ma': 'CANARY'}, {'hanh_dong': XEM},
                    {'noi_dung': {'x': float('nan')}}, {'noi_dung': {1: 'GIA'}}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                tn.tra_thao_tac(self.conn, **{**self.ts, **doi})
        self.conn.execute.assert_not_called()

    def test_core_dung_bien_nhan_tach_rieng(self):
        tn.ghi_core(self.conn, ket_qua={'viec_id': str(uuid4())}, quyen_doc=self.quyen,
            trang_thai='CHUA_RO', **self.ts)
        cau, ts = self.conn.execute.call_args.args
        self.assertIn('bien_nhan_core_v2', cau)
        self.assertEqual(ts[7], True)
        self.assertEqual(ts[10], 'CHUA_RO')
        with self.assertRaises(ValueError):
            tn.ghi_core(self.conn, ket_qua={}, quyen_doc=self.quyen, trang_thai='GIA', **self.ts)

    def test_tiep_nhan_khong_nhan_actor_hoac_phap_nhan_dinh_tuyen(self):
        ts = dict(nguon_cai_dat='DEMO', tham_chieu='demo', ma_bam_ho_so=BAM,
            khong_gian='CAPTURE', khoa=KHOA, du_lieu={'demo': True}, **self.ctx)
        tn.nhan_nguon(self.conn, **ts)
        self.assertIn('tiep_nhan_v2', self.conn.execute.call_args.args[0])
        for doi in ({'actor': 'GIA'}, {'phap_nhan_dich': str(uuid4())}):
            with self.subTest(doi=doi), self.assertRaises(TypeError):
                tn.nhan_nguon(self.conn, **{**ts, **doi})

    def test_loi_khong_lo_token_va_404_tuong_duong(self):
        for ma in ('BIEN_NHAN_KHONG_THAY', 'KHOA_CHONG_TRUNG_KHAC_NOI_DUNG', 'GIA'):
            loi = RuntimeError('CANARY_PHIEN postgresql://CANARY:BI_MAT@localhost')
            loi.diag = MagicMock(message_primary=ma)
            self.conn.execute.side_effect = loi
            with self.assertRaises(tn.LoiTiepNhan) as bat:
                tn.tra_thao_tac(self.conn, **self.ts)
            self.assertIsNone(bat.exception.__context__)
            self.assertNotIn('CANARY', ''.join(traceback.format_exception(bat.exception)))
            if ma == 'BIEN_NHAN_KHONG_THAY':
                self.assertEqual(bat.exception.http_status, 404)

    def test_sql_dollar_quote_moi_truong_va_bien_nhan_bat_bien(self):
        moc = re.findall(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', SQL)
        self.assertEqual((moc[0], moc[-1]), ('$$', '$$'))
        self.assertEqual(len(moc) % 2, 0)
        self.assertTrue(all(a == b for a, b in zip(moc[1:-1:2], moc[2:-1:2])))
        self.assertIn('FORCE ROW LEVEL SECURITY', SQL)
        self.assertIn('WITH CHECK (loi.tiep_nhan_duoc_nguon', SQL)
        self.assertNotRegex(SQL, r'(?i)(?:UPDATE|DELETE FROM)\s+loi_tai_lieu\.bien_nhan_thao_tac')
        self.assertNotRegex(SQL, r'(?i)\bDROP\s+(?:TABLE|FUNCTION|DATABASE|ROLE)')
        self.assertIn("current_database() !~ '^(kho_core_demo", SQL)
        self.assertFalse(SQL_PATH.read_bytes().startswith(b'\xef\xbb\xbf'))


class DoiCauTrucKhoangTrongTest(unittest.TestCase):
    setUp = g204.DoiCauTrucThuanTest.setUp
    _ap = g204.DoiCauTrucThuanTest._ap

    def test_khoang_trong_dung_so_thuc_va_chay_lai(self):
        self.tep = [Path(f'{n:03d}_demo.sql') for n in (1, 3, 11)]
        noi_dung = (b'SELECT 1', b'SELECT 3', b'SELECT 11')
        self.cur.fetchall.return_value = [(n, hashlib.sha256(nd).hexdigest())
                                         for n, nd in zip((1, 3), noi_dung)]
        self.assertEqual(self._ap(noi_dung), 11)
        them = [c.args[1][1] for c in self.cur.execute.call_args_list
                if c.args[0].startswith('INSERT INTO')]
        self.assertEqual(them, [11])
        self.assertNotIn('SELECT 3', [c.args[0] for c in self.cur.execute.call_args_list])
        self.cur.reset_mock()
        self.cur.fetchone.side_effect = [('kho_test_demo',), ('loi.lich_su_doi_cau_truc',)]
        self.cur.fetchall.return_value.append((11, hashlib.sha256(noi_dung[2]).hexdigest()))
        self.assertEqual(self._ap(noi_dung), 11)
        self.assertFalse(any(c.args[0].startswith('INSERT INTO') for c in self.cur.execute.call_args_list))

    def test_khoang_trong_dich_la_so_phien_ban_khong_phai_so_tep(self):
        self.tep = [Path('001_demo.sql'), Path('011_demo.sql')]
        self.assertEqual(self._ap(so_phien_ban=11), 11)
        self.cur.reset_mock()
        with self.assertRaises(dc.LoiDoiCauTruc) as bat:
            self._ap(so_phien_ban=2)
        self.assertEqual(bat.exception.ma, 'SCHEMA_VERSION')
        self.conn.transaction.assert_called_once_with()
        self.cur.execute.assert_not_called()

    def test_khoang_trong_van_chan_checksum_lech_truoc_ddl(self):
        self.tep = [Path('001_demo.sql'), Path('011_demo.sql')]
        self.cur.fetchall.return_value = [(1, hashlib.sha256(b'SELECT 1').hexdigest()),
                                         (11, '0' * 64)]
        with self.assertRaises(dc.LoiDoiCauTruc) as bat:
            self._ap()
        self.assertEqual(bat.exception.ma, 'MIGRATION_CHANGED')
        self.assertNotIn('SELECT 2', [c.args[0] for c in self.cur.execute.call_args_list])

    def test_chan_chen_bu_so_nho_hon_ban_da_ap_truoc_ddl(self):
        self.tep.append(Path('003_demo.sql'))
        self.cur.fetchall.return_value = [(1, hashlib.sha256(b'SELECT 1').hexdigest()),
                                         (3, hashlib.sha256(b'SELECT 3').hexdigest())]
        with self.assertRaises(dc.LoiDoiCauTruc) as bat:
            self._ap((b'SELECT 1', b'SELECT 2', b'SELECT 3'))
        self.assertEqual(bat.exception.ma, 'MIGRATION_ORDER')
        self.assertNotIn('SELECT 2', [c.args[0] for c in self.cur.execute.call_args_list])


@unittest.skipUnless(psycopg is not None and os.environ.get('KHO_PG_DSN_TEST'),
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class NangCap004CuPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        g204.KiemToanPostgresTest.setUpClass.__func__(cls)

    def test_nen_004_cu_qua_009_010_len_011_giu_checksum(self):
        nen = sorted(dc.THU_MUC_SQL.glob('00[1-9]_*.sql'))
        tep_010 = Path('010_demo.sql')
        doc_goc = Path.read_bytes
        for co_010 in (False, True):
            with self.subTest(co_010=co_010), self.conn.transaction(force_rollback=True):
                lich_su_cu = self.conn.execute(
                    'SELECT * FROM loi.lich_su_doi_cau_truc ORDER BY so_phien_ban').fetchall()
                self.assertEqual([dong[1] for dong in lich_su_cu], [1, 2, 3, 4])
                self.assertEqual(lich_su_cu[3][2], hashlib.sha256(nen[3].read_bytes()).hexdigest())
                ham_cu = self.conn.execute(
                    "SELECT prosrc FROM pg_proc WHERE oid='loi.kiem_lich_su_doi_cau_truc()'::regprocedure").fetchone()[0]
                self.assertIn('NEW.so_phien_ban <> ban_cu + 1', ham_cu)
                # 010 là no-op DEMO trong bộ nhớ; dự án hiện chưa phát hành SQL 010.
                cac_tep = [*nen, *([tep_010] if co_010 else [])]
                with patch.object(Path, 'read_bytes', autospec=True,
                                  side_effect=lambda tep: b'SELECT 1' if tep == tep_010 else doc_goc(tep)):
                    self.assertEqual(dc.ap_doi_cau_truc(self.conn, cac_tep), 10 if co_010 else 9)
                    self.assertEqual(dc.ap_doi_cau_truc(self.conn, [*cac_tep, SQL_PATH]), 11)
                    self.assertEqual(dc.ap_doi_cau_truc(self.conn, [*cac_tep, SQL_PATH]), 11)
                self.assertEqual(self.conn.execute(
                    'SELECT * FROM loi.lich_su_doi_cau_truc WHERE so_phien_ban<=4 ORDER BY so_phien_ban'
                ).fetchall(), lich_su_cu)
                self.assertEqual(self.conn.execute(
                    "SELECT so_phien_ban FROM loi.lich_su_doi_cau_truc WHERE ma_goi='core' ORDER BY so_phien_ban"
                ).fetchall(), [(n,) for n in range(1, 11 if co_010 else 10)] + [(11,)])
                ham_moi = self.conn.execute(
                    "SELECT prosrc FROM pg_proc WHERE oid='loi.kiem_lich_su_doi_cau_truc()'::regprocedure").fetchone()[0]
                self.assertIn('NEW.so_phien_ban <= ban_cu', ham_moi)


@unittest.skipUnless(psycopg is not None and os.environ.get('KHO_PG_DSN_TEST'),
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class TiepNhanPostgresTest(unittest.TestCase):
    _ghi = g209.TaiLieuPostgresTest._ghi
    _contract = g209.TaiLieuPostgresTest._contract
    _trang_thai = g209.TaiLieuPostgresTest._trang_thai
    _resolver = g209.TaiLieuPostgresTest._resolver
    _cap = g209.TaiLieuPostgresTest._cap
    _ctx = g209.TaiLieuPostgresTest._ctx
    _tao = g209.TaiLieuPostgresTest._tao

    @classmethod
    def setUpClass(cls):
        g209.TaiLieuPostgresTest.setUpClass.__func__(cls)
        # G2-10 không có SQL 010; runner ghi đúng số 011 sau nền 001..009.
        dc.ap_doi_cau_truc(cls.conn, [*sorted(dc.THU_MUC_SQL.glob('00[1-9]_*.sql')), SQL_PATH])
        vai = cls.tien_to + 'vai_chay_mod_crm'
        for ck in (
            'tra_bien_nhan_thao_tac_v2(text,text,uuid,text,text,text,jsonb,uuid,bigint)',
            'ghi_bien_nhan_thao_tac_v2(text,text,uuid,text,text,text,jsonb,jsonb,jsonb,uuid,bigint)',
            'doc_vung_tam_v2(text,text,uuid,text,uuid)'):
            cls.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION loi_tai_lieu.'+ck+' TO {}').format(sql.Identifier(vai)))
        # _resolver được gọi lần đầu ở setUp; tạo business fixture tại đó.
        cls.vai_module = vai

    def setUp(self):
        g209.TaiLieuPostgresTest.setUp(self)
        if not self.conn.execute("SELECT to_regclass('mod_crm.tac_dong_demo')").fetchone()[0]:
            with self.conn.transaction():
                self.conn.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(self.tien_to+'vai_doi_cau_truc_mod_crm')))
                self.conn.execute('CREATE TABLE mod_crm.tac_dong_demo(id uuid PRIMARY KEY,phap_nhan_id uuid NOT NULL)')
                self.conn.execute(sql.SQL('GRANT USAGE ON SCHEMA mod_crm TO {}').format(sql.Identifier(self.vai_module)))
                self.conn.execute(sql.SQL('GRANT INSERT,SELECT ON mod_crm.tac_dong_demo TO {}').format(sql.Identifier(self.vai_module)))
        self._cap_lai_phien()
        self.ts = dict(operation='CRM.DEMO.LAP', khoa=KHOA, noi_dung={'demo': True},
            doi_tuong=dict(bang='doi_tuong', id=str(self.obj)), **self._ctx(ma=self.uy))
        self.quyen = dict(hanh_dong=XEM, doi_tuong=self.ts['doi_tuong'], phien_ban_contract='1',
            tai_lieu_id=str(self.tai_lieu_id), bien_the='goc')

    def _cap_lai_phien(self):
        # G2-06 thu hồi mọi phiên khi đổi vai/phạm vi, kể cả lúc thêm quyền.
        self.ma = self._cap()
        self.uy = phien.cap_phien(self.core, nguoi_dung_id=self.nd, module='crm', phap_nhan_id=self.pn,
            dang_nhap_csdl=self.module_login, pham_vi_hanh_dong=[LAP, g209.SUA, XEM, g209.DUYET],
            loai='UY_NHIEM_PHIEN', ma_goc=self.ma,
            hieu_luc_den=datetime.now(timezone.utc)+timedelta(minutes=4)).ma

    def _thuc_hien(self, conn=None, **doi):
        conn = conn or self.module
        def nghiep_vu(kn):
            self.assertIs(kn, conn)
            id_moi = uuid4()
            kn.execute('INSERT INTO mod_crm.tac_dong_demo VALUES (%s,%s)', (id_moi, self.pn))
            return {'id': str(id_moi)}
        return tn.thuc_hien_thao_tac(conn, thuc_hien=nghiep_vu, quyen_doc=self.quyen, **{**self.ts, **doi})

    def _core_ts(self):
        return {**self.ts, 'ma': self.ma}

    def test_runner_va_trigger_cho_khoang_trong_chan_so_nho_hon(self):
        goi = 'demo_' + uuid4().hex
        cac_tep = [Path(f'{n:03d}_demo.sql') for n in (1, 3, 11)]
        with self.conn.transaction(force_rollback=True), patch.object(Path, 'read_bytes', return_value=b'SELECT 1'):
            self.assertEqual(dc.ap_doi_cau_truc(self.conn, cac_tep, ma_goi=goi), 11)
            self.assertEqual(self.conn.execute('''SELECT so_phien_ban FROM loi.lich_su_doi_cau_truc
                WHERE ma_goi=%s ORDER BY so_phien_ban''', (goi,)).fetchall(), [(1,), (3,), (11,)])
            self.assertEqual(dc.ap_doi_cau_truc(self.conn, cac_tep, ma_goi=goi), 11)
            with self.assertRaises(dc.LoiDoiCauTruc) as bat:
                dc.ap_doi_cau_truc(self.conn, cac_tep, ma_goi=goi, so_phien_ban=3)
            self.assertEqual(bat.exception.ma, 'FUTURE_SCHEMA')
            with self.assertRaises(dc.LoiDoiCauTruc) as bat:
                dc.ap_doi_cau_truc(self.conn, [*cac_tep, Path('002_demo.sql')], ma_goi=goi)
            self.assertEqual(bat.exception.ma, 'MIGRATION_ORDER')
            with self.assertRaises(psycopg.errors.CheckViolation) as bat, self.conn.transaction():
                self.conn.execute('''INSERT INTO loi.lich_su_doi_cau_truc
                    (ma_goi,so_phien_ban,ma_bam,nguon_lich_su) VALUES (%s,2,%s,'{}')''', (goi, '0' * 64))
            self.assertIn('FUTURE_SCHEMA', str(bat.exception))

    def test_cung_khoa_cung_noi_dung_replay_va_khac_noi_dung_409(self):
        self.assertEqual(self.module.execute('SELECT current_user,session_user').fetchone(), (self.module_login,)*2)
        with self.module.transaction():
            dau = self._thuc_hien()
        with self.module.transaction():
            lap = self._thuc_hien()
        self.assertFalse(dau['lap_lai'])
        self.assertTrue(lap['lap_lai'])
        self.assertEqual(dau['ket_qua'], lap['ket_qua'])
        self.assertEqual(self.conn.execute('SELECT count(*) FROM mod_crm.tac_dong_demo WHERE phap_nhan_id=%s', (self.pn,)).fetchone()[0], 1)
        with self.assertRaises(tn.LoiTiepNhan) as bat, self.module.transaction():
            self._thuc_hien(noi_dung={'demo': False})
        self.assertEqual(bat.exception.ma, 'KHOA_CHONG_TRUNG_KHAC_NOI_DUNG')

    def test_rollback_nghiep_vu_va_bien_nhan_cung_ket_noi(self):
        with self.assertRaisesRegex(RuntimeError, 'DEMO_ROLLBACK'):
            with self.module.transaction():
                self._thuc_hien()
                raise RuntimeError('DEMO_ROLLBACK')
        for bang in ('mod_crm.tac_dong_demo', 'loi_tai_lieu.bien_nhan_thao_tac'):
            self.assertEqual(self.conn.execute('SELECT count(*) FROM '+bang+' WHERE phap_nhan_id=%s', (self.pn,)).fetchone()[0], 0)
        with self.module.transaction():
            self.assertIsNone(tn.tra_thao_tac(self.module, **self.ts))

    def test_module_bat_bien_va_khong_het_han(self):
        with self.module.transaction():
            dau = self._thuc_hien()
        row = self.conn.execute('SELECT * FROM loi_tai_lieu.bien_nhan_thao_tac WHERE id=%s', (dau['id'],))
        cot = [c.name for c in row.description]
        data = dict(zip(cot, row.fetchone()))
        # Fixture lịch sử trước một năm, rồi ca replay chạy bằng login module thật.
        data.update(id=uuid4(), khoa_chong_trung='demo-khoa-lich-su', tao_luc=datetime.now(timezone.utc)-timedelta(days=366))
        self.conn.execute('''INSERT INTO loi_tai_lieu.bien_nhan_thao_tac
            (id,phap_nhan_id,module,operation,khoa_chong_trung,ma_bam,ket_qua,quyen_doc,tao_boi,tao_luc)
            VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s)''',
            tuple(json.dumps(data[k]) if k in ('ket_qua','quyen_doc') else data[k]
                for k in ('id','phap_nhan_id','module','operation','khoa_chong_trung','ma_bam','ket_qua','quyen_doc','tao_boi','tao_luc')))
        with self.module.transaction():
            self.assertTrue(self._thuc_hien(khoa=data['khoa_chong_trung'])['lap_lai'])
        for cau in ('UPDATE loi_tai_lieu.bien_nhan_thao_tac SET ket_qua=ket_qua',
                    'DELETE FROM loi_tai_lieu.bien_nhan_thao_tac', 'TRUNCATE loi_tai_lieu.bien_nhan_thao_tac'):
            with self.subTest(cau=cau), self.assertRaises(psycopg.Error):
                self.conn.execute(cau)

    def test_core_dung_24_gio_giu_dang_chay_chua_ro_va_khong_retry_mu(self):
        moc = datetime(2026, 10, 1, tzinfo=timezone.utc)
        ck = 'loi_tai_lieu.bien_nhan_core_con_hieu_luc(%s,%s,%s)'
        for tt, cuoi, luc, dat in (
            ('HOAN_TAT', moc, moc+timedelta(hours=24, microseconds=-1), True),
            ('HOAN_TAT', moc, moc+timedelta(hours=24), False),
            ('DANG_XU_LY', None, moc+timedelta(days=40), True),
            ('CHUA_RO', None, moc+timedelta(days=40), True)):
            self.assertEqual(self.core.execute('SELECT '+ck, (tt, cuoi, luc)).fetchone()[0], dat)
        ts = self._core_ts()
        with self.core.transaction():
            dau = tn.ghi_core(self.core, ket_qua={'viec_id': str(uuid4())}, quyen_doc=self.quyen,
                trang_thai='CHUA_RO', **ts)
        self.assertIsNone(self.conn.execute('SELECT ket_qua_cuoi_luc FROM loi_tai_lieu.bien_nhan_core WHERE id=%s', (dau['id'],)).fetchone()[0])
        with self.core.transaction():
            tn.ghi_core(self.core, ket_qua={'id': 'DEMO'}, quyen_doc=self.quyen, **ts)
        final = self.conn.execute('SELECT ket_qua_cuoi_luc FROM loi_tai_lieu.bien_nhan_core WHERE id=%s', (dau['id'],)).fetchone()[0]
        with self.core.transaction():
            tn.ghi_core(self.core, ket_qua={'id': 'KHONG_DOI'}, quyen_doc=self.quyen, **ts)
        self.assertEqual(self.conn.execute('SELECT ket_qua_cuoi_luc FROM loi_tai_lieu.bien_nhan_core WHERE id=%s', (dau['id'],)).fetchone()[0], final)
        self.conn.execute("UPDATE loi_tai_lieu.bien_nhan_core SET ket_qua_cuoi_luc=clock_timestamp()-interval '24 hours' WHERE id=%s", (dau['id'],))
        with self.assertRaises(tn.LoiTiepNhan) as bat, self.core.transaction():
            tn.tra_core(self.core, **ts)
        self.assertEqual(bat.exception.ma, 'BIEN_NHAN_CORE_HET_HAN')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi_tai_lieu.bien_nhan_thao_tac WHERE phap_nhan_id=%s', (self.pn,)).fetchone()[0], 0)

    def test_nguoi_khac_co_quyen_hanh_dong_nhung_khong_doc_ket_qua_404(self):
        with self.module.transaction():
            self._thuc_hien()
        nd2 = uuid4()
        self.conn.execute("INSERT INTO loi.nguoi_dung(id,dang_nhap,ten,vai_tro) VALUES (%s,%s,'DEMO','XEM')", (nd2, 'demo_'+nd2.hex))
        self.conn.execute('INSERT INTO loi.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,%s)', (nd2,self.pn,['crm']))
        gan = uuid4()
        self.conn.execute('''INSERT INTO loi.mtq_gan_vai(id,nguoi_dung_id,phap_nhan_id,phong_id,vai,cap_boi,ly_do)
            SELECT %s,%s,phap_nhan_id,phong_id,vai,%s,'DEMO' FROM loi.mtq_gan_vai
            WHERE nguoi_dung_id=%s AND phap_nhan_id=%s''', (gan,nd2,self.nd,self.nd,self.pn))
        self.conn.execute("INSERT INTO loi.mtq_pham_vi(gan_vai_id,phap_nhan_id,loai,khoa,cap_boi,ly_do) VALUES (%s,%s,'PHAP_NHAN',%s,%s,'DEMO')", (gan,self.pn,str(self.pn),self.nd))
        self._cap_lai_phien()
        self.ts['ma'] = self.uy
        ma2 = phien.cap_phien(self.core, nguoi_dung_id=nd2, module='crm', phap_nhan_id=self.pn,
            dang_nhap_csdl=self.cac_thong_tin['core']['user'], pham_vi_hanh_dong=[LAP,XEM],
            hieu_luc_den=datetime.now(timezone.utc)+timedelta(minutes=4)).ma
        for noi_dung in ({'demo': True}, {'demo': False}):
            with self.subTest(noi_dung=noi_dung), self.assertRaises(tn.LoiTiepNhan) as bat, self.core.transaction():
                tn.tra_thao_tac(self.core, **{**self.ts, 'ma': ma2, 'noi_dung': noi_dung})
            self.assertEqual((bat.exception.ma, bat.exception.http_status), ('BIEN_NHAN_KHONG_THAY', 404))
        # Chính người tạo bị thu hồi quyền nội dung cũng không được phát lại.
        with self.core.transaction():
            tn.ghi_core(self.core, ket_qua={'id': 'DEMO'}, quyen_doc=self.quyen, **self._core_ts())
        g209.tl.cap_quyen(self.core, tai_lieu_id=self.tai_lieu_id, du_lieu=dict(nguoi_dung_id=str(self.nd),
            bien_the='goc', cho_phep=False, revision_truoc=0), request_id=uuid4(), **self._ctx(g209.DUYET))
        for kn, ts, tra, ghi in ((self.module, self.ts, tn.tra_thao_tac, tn.ghi_thao_tac),
                                 (self.core, self._core_ts(), tn.tra_core, tn.ghi_core)):
            for noi_dung in ({'demo': True}, {'demo': False}):
                for goi, them in ((tra, {}), (ghi, dict(ket_qua={'id': 'DEMO'}, quyen_doc=self.quyen))):
                    with self.subTest(core=kn is self.core, noi_dung=noi_dung, goi=goi.__name__):
                        with self.assertRaises(tn.LoiTiepNhan) as bat, kn.transaction():
                            goi(kn, **{**ts, 'noi_dung': noi_dung}, **them)
                        self.assertEqual((bat.exception.ma, bat.exception.http_status), ('BIEN_NHAN_KHONG_THAY', 404))

    def test_thieu_quyen_hanh_dong_chan_truoc_tra_bien_nhan(self):
        with self.module.transaction():
            self._thuc_hien()
        with self.core.transaction():
            tn.ghi_core(self.core, ket_qua={'id': 'DEMO'}, quyen_doc=self.quyen, **self._core_ts())
        self.conn.execute('''UPDATE loi.mtq_gan_vai SET thu_hoi_luc=now(),thu_hoi_boi=%s,
            phien_ban_dong=phien_ban_dong+1 WHERE nguoi_dung_id=%s AND phap_nhan_id=%s''',
            (self.nd, self.nd, self.pn))
        self._cap_lai_phien()
        self.ts['ma'] = self.uy
        for kn, ts, tra in ((self.module, self.ts, tn.tra_thao_tac),
                            (self.core, self._core_ts(), tn.tra_core)):
            # Phiên thật vẫn hợp lệ; lỗi phải đến từ MTQ trước khi tra key.
            self.assertIsNotNone(phien.xac_minh_phien(kn, ma=ts['ma'], module='crm',
                phap_nhan_id=self.pn, hanh_dong=LAP))
            for khoa in (KHOA, 'demo-khoa-chua-co'):
                for noi_dung in ({'demo': True}, {'demo': False}):
                    with self.subTest(core=kn is self.core, khoa=khoa, noi_dung=noi_dung):
                        with self.assertRaises(tn.LoiTiepNhan) as bat, kn.transaction():
                            tra(kn, **{**ts, 'khoa': khoa, 'noi_dung': noi_dung})
                        self.assertEqual(bat.exception.ma, 'TAI_LIEU_MTQ')

    def test_tiep_nhan_prePN_kiem_nguon_va_lan_khong_tin_guc(self):
        nguon = 'demo_'+uuid4().hex
        self.conn.execute('INSERT INTO loi.nguon_cai_dat(id) VALUES (%s)', (nguon,))
        self.conn.execute('INSERT INTO loi.ho_so_nguon(nguon_cai_dat,tham_chieu,ma_bam) VALUES (%s,%s,%s)', (nguon,'demo',BAM))
        ts = dict(nguon_cai_dat=nguon,tham_chieu='demo',ma_bam_ho_so=BAM,khong_gian='CAPTURE',
            khoa=KHOA,du_lieu={'demo': True}, **self._ctx())
        with self.assertRaises(tn.LoiTiepNhan), self.core.transaction():
            tn.nhan_nguon(self.core, **ts)
        for hd in ('INTAKE','READ_SOURCE'):
            self.conn.execute('''INSERT INTO loi.nang_luc_nguon(nguoi_dung_id,nguon_cai_dat,tham_chieu,ma_bam,hanh_dong,cap_boi)
                VALUES (%s,%s,'demo',%s,%s,%s)''', (self.nd,nguon,BAM,hd,self.nd))
        with self.core.transaction():
            dau = tn.nhan_nguon(self.core, **ts)
        with self.core.transaction():
            self.assertTrue(tn.nhan_nguon(self.core, **ts)['lap_lai'])
            vung = tn.doc_vung_tam(self.core, lan_tiep_nhan_id=dau['lan_tiep_nhan_id'], **self._ctx(XEM))
            self.assertIsNone(vung['phap_nhan_id'])
        self.assertIsNone(self.conn.execute('SELECT phap_nhan_id FROM loi_tai_lieu.lan_tiep_nhan_nguon WHERE id=%s', (dau['lan_tiep_nhan_id'],)).fetchone()[0])
        with self.assertRaises(tn.LoiTiepNhan) as bat, self.core.transaction():
            tn.nhan_nguon(self.core, **{**ts,'du_lieu': {'demo': False}})
        self.assertEqual(bat.exception.ma, 'KHOA_CHONG_TRUNG_KHAC_NOI_DUNG')
        self.conn.execute('UPDATE loi.nang_luc_nguon SET thu_hoi_luc=clock_timestamp() WHERE nguoi_dung_id=%s AND nguon_cai_dat=%s', (self.nd,nguon))
        with self.assertRaises(tn.LoiTiepNhan) as bat, self.core.transaction():
            self.core.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true)", (str(self.nd),))
            tn.doc_vung_tam(self.core, lan_tiep_nhan_id=dau['lan_tiep_nhan_id'], **self._ctx(XEM))
        self.assertEqual(bat.exception.http_status, 404)

    def test_runtime_khong_ghi_thang_khong_goi_cua_noi_bo(self):
        for kn in (self.core,self.module):
            for bang in ('bien_nhan_thao_tac','bien_nhan_core','lan_tiep_nhan_nguon','vung_tam_tin_cay'):
                with self.subTest(bang=bang,login=kn.info.user), self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    kn.execute('INSERT INTO loi_tai_lieu.'+bang+' DEFAULT VALUES')
        with self.assertRaises(psycopg.errors.InsufficientPrivilege), self.module.transaction():
            self.module.execute('SELECT loi_tai_lieu.bien_nhan_core_v2(%s,%s,%s,%s,%s,%s,%s::jsonb)',
                (self.uy.lay_de_truyen(),'crm',self.pn,LAP,'CRM.DEMO.LAP',KHOA,'{}'))


if __name__ == '__main__':
    unittest.main()
