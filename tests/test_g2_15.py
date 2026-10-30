"""G2-15: thuần/mock và PG opt-in, dữ liệu giả, login runtime thật.

Không DROP, không bật/tắt dịch vụ. Lead chạy PG khi có KHO_PG_DSN_TEST.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sys
import traceback
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import doi_cau_truc as dc, phien, su_kien as bus

try:
    from . import test_g2_09 as g209
except ImportError:
    import test_g2_09 as g209

psycopg = g209.psycopg
if psycopg is not None:
    from psycopg import sql

SQL_PATH = dc.THU_MUC_SQL / '015_su_kien.sql'
SQL = SQL_PATH.read_text(encoding='utf-8')
BANG = ('su_kien', 'hop_nhan_su_kien', 'ack_su_kien', 'dang_ky_nhan_su_kien')
CHU_KY = ('su_kien_phat(text,text,uuid,text,text,integer,text,jsonb,uuid,bigint)',
          'su_kien_nhan(text,text,uuid,text,text,integer,uuid,bigint)',
          'su_kien_ack(text,text,uuid,text,uuid,uuid,bigint)')
SCHEMA = dict(type='object', additionalProperties=False, required=['moc_id'], properties={
    'moc_id': dict(type='string', format='uuid'),
    'nguon_ids': dict(type='array', items=dict(type='string', format='uuid'))})


class SuKienThuanTest(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.conn.info.transaction_status = 2
        self.ctx = dict(ma=phien.MaBiMat('CANARY_BI_MAT'), module='crm',
                        phap_nhan_id=uuid4(), hanh_dong=g209.LAP)
        self.obj = uuid4()
        self.ts = dict(loai='demo.moc', phien_ban=1, tham_chieu={'moc_id': str(self.obj)}, khoa='DEMO-15')

    def test_phat_bind_va_khong_quan_ly_transaction(self):
        self.conn.execute.return_value.fetchone.return_value = (self.obj,)
        self.assertEqual(bus.phat(self.conn, **self.ts, **self.ctx), self.obj)
        cau, ts = self.conn.execute.call_args.args
        self.assertIn('loi.su_kien_phat', cau)
        self.assertNotIn('CANARY', cau)
        self.assertEqual(ts[:4], ('CANARY_BI_MAT', 'crm', self.ctx['phap_nhan_id'], g209.LAP))
        self.assertEqual(json.loads(ts[7]), self.ts['tham_chieu'])
        self.assertEqual(ts[8:], (None, None))
        for ten in ('connect', 'transaction', 'commit', 'rollback'):
            getattr(self.conn, ten).assert_not_called()

    def test_nhan_dict_row_va_ack_lap(self):
        self.conn.execute.return_value.fetchone.return_value = {'r': []}
        self.assertEqual(bus.nhan(self.conn, **self.ctx), [])
        self.conn.execute.return_value.fetchone.return_value = {'r': False}
        self.assertFalse(bus.ack(self.conn, self.obj, **self.ctx))

    def test_bat_buoc_transaction_cua_caller(self):
        for tt in (0, 1, 3, 4):
            self.conn.info.transaction_status = tt
            for goi in (lambda: bus.phat(self.conn, **self.ts, **self.ctx),
                        lambda: bus.nhan(self.conn, **self.ctx),
                        lambda: bus.ack(self.conn, self.obj, **self.ctx)):
                with self.subTest(tt=tt), self.assertRaises(ValueError):
                    goi()
        self.conn.execute.assert_not_called()

    def test_payload_uuid_don_va_mang(self):
        bus.phat(self.conn, **{**self.ts, 'tham_chieu': {'moc_id': str(self.obj), 'nguon_ids': [str(uuid4())]}}, **self.ctx)

    def test_tu_choi_du_lieu_nghiep_vu_truoc_sql(self):
        for p in ({}, {'tien': '100'}, {'moc_id': 'DEMO'}, {'moc_id': None}, {'nguon_ids': [1]},
                  {'noi_dung': {'moc_id': str(self.obj)}}, {1: str(self.obj)}):
            with self.subTest(p=p), self.assertRaises(ValueError):
                bus.phat(self.conn, **{**self.ts, 'tham_chieu': p}, **self.ctx)
        self.conn.execute.assert_not_called()

    def test_tu_choi_dau_vao_va_sai_hanh_dong(self):
        for doi in ({'phien_ban': True}, {'phien_ban': 0}, {'phien_ban': 2**31},
                    {'khoa': ' '}, {'khoa': 'x'*201}, {'loai': 'DEMO'}, {'loai': None}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                bus.phat(self.conn, **{**self.ts, **doi}, **self.ctx)
        with self.assertRaises(ValueError):
            bus.phat(self.conn, **self.ts, **{**self.ctx, 'hanh_dong': g209.XEM})
        for n in (True, 0, 1001):
            with self.assertRaises(ValueError):
                bus.nhan(self.conn, gioi_han=n, **self.ctx)
        self.conn.execute.assert_not_called()

    def test_truyen_uy_nhiem_viec_va_the_he(self):
        v = uuid4()
        bus.nhan(self.conn, **self.ctx, viec_id=v, the_he=3)
        self.assertEqual(self.conn.execute.call_args.args[1][-2:], (v, 3))

    def test_xu_ly_dung_ket_noi_handler_truoc_ack(self):
        sk = {'id': str(uuid4())}
        self.conn.execute.return_value.fetchone.side_effect = [([sk],), (True,)]
        def handler(conn, event):
            self.assertIs(conn, self.conn)
            self.assertEqual(event, sk)
            self.assertEqual(conn.execute.call_count, 1)
        self.assertEqual(bus.xu_ly(self.conn, handler, **self.ctx), 1)
        self.assertIn('su_kien_ack', self.conn.execute.call_args.args[0])
        self.conn.commit.assert_not_called()

    def test_handler_loi_khong_ack_va_khong_nuot_loi(self):
        self.conn.execute.return_value.fetchone.return_value = ([{'id': str(uuid4())}],)
        def handler(conn, sk):
            raise RuntimeError('DEMO_ROLLBACK')
        with self.assertRaisesRegex(RuntimeError, 'DEMO_ROLLBACK'):
            bus.xu_ly(self.conn, handler, **self.ctx)
        self.assertEqual(self.conn.execute.call_count, 1)

    def test_che_loi_driver_va_ma_phien(self):
        for ma in ('BUS_PAYLOAD', 'CANARY_DSN_PASSWORD'):
            exc = RuntimeError('CANARY_BI_MAT_DSN')
            exc.diag = MagicMock(message_primary=ma)
            self.conn.execute.side_effect = exc
            with self.assertRaises(bus.LoiSuKien) as bat:
                bus.nhan(self.conn, **self.ctx)
            self.assertEqual(bat.exception.ma, ma if ma == 'BUS_PAYLOAD' else 'BUS_THAT_BAI')
            self.assertNotIn('CANARY', ''.join(traceback.format_exception(bat.exception)))

    def test_sql_quote_bien_gioi_bat_bien(self):
        moc = re.findall(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', SQL)
        self.assertEqual((moc[0], moc[-1]), ('$$', '$$'))
        self.assertTrue(all(a == b for a, b in zip(moc[1:-1:2], moc[2:-1:2])))
        self.assertNotRegex(SQL, r'(?i)\bDROP\s+(?:TABLE|FUNCTION|DATABASE|ROLE)')
        self.assertNotRegex(SQL, r'(?i)\b(?:UPDATE|DELETE FROM)\s+loi\.')
        self.assertNotRegex(SQL, r'(?i)(?:FROM|JOIN|REFERENCES)\s+(?:mod_|master\.|bus\.)')
        self.assertFalse(SQL_PATH.read_bytes().startswith(b'\xef\xbb\xbf'))


@unittest.skipUnless(psycopg is not None and g209.ADMIN_DSN,
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class SuKienPostgresTest(unittest.TestCase):
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
        cls.tep_sql = sorted(dc.THU_MUC_SQL.glob('[0-9][0-9][0-9]_*.sql'),
                             key=lambda p: int(p.name.split('_', 1)[0]))
        dc.ap_doi_cau_truc(cls.conn, cls.tep_sql)
        for ck in CHU_KY:
            cls.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION loi.' + ck + ' TO {}')
                             .format(sql.Identifier(cls.module_login)))

    def setUp(self):
        g209.TaiLieuPostgresTest.setUp(self)
        self.conn.execute('CREATE TABLE IF NOT EXISTS mod_crm.tac_dong_g215(id uuid PRIMARY KEY, su_kien_id uuid NOT NULL)')
        self.conn.execute(sql.SQL('GRANT USAGE ON SCHEMA mod_crm TO {}').format(sql.Identifier(self.module_login)))
        self.conn.execute(sql.SQL('GRANT INSERT,SELECT ON mod_crm.tac_dong_g215 TO {},{}')
                          .format(sql.Identifier(self.module_login), sql.Identifier(self.core.info.user)))
        self.ma_module = phien.cap_phien(self.core, nguoi_dung_id=self.nd, module='crm', phap_nhan_id=self.pn,
            dang_nhap_csdl=self.module_login, pham_vi_hanh_dong=[g209.LAP, g209.XEM],
            loai='UY_NHIEM_PHIEN', ma_goc=self.ma,
            hieu_luc_den=datetime.now(timezone.utc)+timedelta(minutes=5)).ma
        self.loai = self._su_kien_contract()

    def _su_kien_contract(self, *, active=True, schema=None, module='crm'):
        ma = 'demo.sk_' + uuid4().hex[:12]
        self._ghi('contract', ma=ma, phien_ban='1', module_so_huu=module, lop='nghiep_vu',
            muc_dich='DEMO bus UUID', sieu_du_lieu={'truong': []}, luoc_do=SCHEMA if schema is None else schema, ma_bam='a'*64)
        if active:
            self._trang_thai(ma, '1', 'anh_duyet', bang_chung_duyet='CD-DEMO-Anh-duyet')
            self._trang_thai(ma, '1', 'dang_dung')
        return ma

    def _dang_ky(self, loai=None):
        loai = loai or self.loai
        self._ghi('dung_contract', ma_contract=loai, phien_ban_contract='1', module='crm', phien_ban_module='1')
        self.cai_dat.execute('SELECT loi.su_kien_dang_ky_nhan(%s,%s,%s,%s)', ('crm', '1', loai, '1'))

    def _ctx_module(self, **doi):
        return {**self._ctx(), 'ma': self.ma_module, **doi}

    def _phat(self, conn=None, **doi):
        conn = conn or self.module
        with conn.transaction():
            return bus.phat(conn, **{**dict(loai=self.loai, phien_ban=1, tham_chieu={'moc_id': str(self.obj)},
                khoa=uuid4().hex), **self._ctx_module(), **doi})

    def _nhan(self, conn=None, **doi):
        conn = conn or self.module
        return bus.nhan(conn, loai=self.loai, **{**self._ctx_module(), **doi})

    def _handler(self, conn, sk):
        # Khong dung ON CONFLICT/dedupe nghiep vu de che loi giao lap cua bus.
        conn.execute('INSERT INTO mod_crm.tac_dong_g215 VALUES (%s,%s)', (uuid4(), sk['id']))

    def _dem(self, bang, id):
        return self.conn.execute(sql.SQL('SELECT count(*) FROM loi.{} WHERE {}=%s')
            .format(sql.Identifier(bang), sql.Identifier('id' if bang == 'su_kien' else 'su_kien_id')), (id,)).fetchone()[0]

    def test_chuoi_sql_theo_so_chay_lai_va_login_that(self):
        self.assertEqual(dc.ap_doi_cau_truc(self.conn, self.tep_sql), max(dc._doc_chuoi(self.tep_sql)))
        for conn in (self.module, self.core):
            self.assertEqual(conn.execute('SELECT session_user,current_user').fetchone(), (conn.info.user,)*2)

    def test_rollback_nghiep_vu_khong_co_outbox(self):
        sk = None
        with self.assertRaisesRegex(RuntimeError, 'DEMO_ROLLBACK'):
            with self.module.transaction():
                sk = self._phat()
                self._handler(self.module, {'id': sk})
                raise RuntimeError('DEMO_ROLLBACK')
        self.assertEqual(self._dem('su_kien', sk), 0)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM mod_crm.tac_dong_g215 WHERE su_kien_id=%s', (sk,)).fetchone()[0], 0)

    def test_giao_lai_hai_lan_tac_dong_mot_lan_ack_lap_false(self):
        self._dang_ky()
        sk = self._phat()
        for _ in range(2):
            with self.module.transaction():
                self.assertEqual(self._nhan()[0]['id'], str(sk))
        for n in (1, 0):
            with self.module.transaction():
                self.assertEqual(bus.xu_ly(self.module, self._handler, loai=self.loai, **self._ctx_module()), n)
        with self.module.transaction():
            self.assertFalse(bus.ack(self.module, sk, **self._ctx_module()))
        self.assertEqual(self._dem('hop_nhan_su_kien', sk), 1)
        self.assertEqual(self._dem('ack_su_kien', sk), 1)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM mod_crm.tac_dong_g215 WHERE su_kien_id=%s', (sk,)).fetchone()[0], 1)

    def test_rollback_sau_ack_giao_lai_duoc_va_ket_qua_cung_rollback(self):
        self._dang_ky()
        sk = self._phat()
        with self.assertRaisesRegex(RuntimeError, 'DEMO_ROLLBACK'):
            with self.module.transaction():
                bus.xu_ly(self.module, self._handler, loai=self.loai, **self._ctx_module())
                raise RuntimeError('DEMO_ROLLBACK')
        self.assertEqual(self._dem('ack_su_kien', sk), 0)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM mod_crm.tac_dong_g215 WHERE su_kien_id=%s', (sk,)).fetchone()[0], 0)
        with self.module.transaction():
            self.assertEqual(bus.xu_ly(self.module, self._handler, loai=self.loai, **self._ctx_module()), 1)

    def test_hai_receiver_canh_tranh_khong_nhan_tac_dong(self):
        self._dang_ky()
        sk = self._phat()
        def xu_ly(_):
            with psycopg.connect(**self.cac_thong_tin['core'], autocommit=True) as conn:
                conn.execute("SET statement_timeout='10s'")
                with conn.transaction():
                    return bus.xu_ly(conn, self._handler, loai=self.loai, **self._ctx())
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(xu_ly, range(2))), 1)
        self.assertEqual(self._dem('ack_su_kien', sk), 1)

    def test_payload_sql_tu_choi_ngoai_uuid_ngoai_khai_bao_va_thieu_bat_buoc(self):
        for p in ({'moc_id': str(self.obj), 'tien': 100}, {'moc_id': str(self.obj), 'khac_id': str(uuid4())},
                  {'moc_id': 'sai'}, {'nguon_ids': []}, {'moc_id': None}, {'moc_id': str(self.obj), 'nguon_ids': [1]}):
            with self.subTest(p=p), self.assertRaises(psycopg.errors.InvalidParameterValue), self.module.transaction():
                self.module.execute('SELECT loi.su_kien_phat(%s,%s,%s,%s,%s,1,%s,%s::jsonb)',
                    (self.ma_module.lay_de_truyen(), 'crm', self.pn, g209.LAP, self.loai, uuid4().hex, json.dumps(p)))

    def test_schema_khong_ho_tro_bi_chan_khong_bo_qua_keyword(self):
        loai = self._su_kien_contract(schema={**SCHEMA, 'maxProperties': 1})
        with self.assertRaises(bus.LoiSuKien) as bat:
            self._phat(loai=loai)
        self.assertEqual(bat.exception.ma, 'BUS_PAYLOAD')

    def test_tu_choi_contract_nhap_ngung_chua_dang_ky_va_sai_chu(self):
        nhap = self._su_kien_contract(active=False)
        ngung = self._su_kien_contract()
        self._trang_thai(ngung, '1', 'ngung')
        self._ghi('module', ma='sk_khac', ten='DEMO')
        khac = self._su_kien_contract(module='sk_khac')
        for loai in (nhap, ngung, khac, 'demo.khong_ton_tai'):
            with self.subTest(loai=loai), self.assertRaises(bus.LoiSuKien) as bat:
                self._phat(loai=loai)
            self.assertEqual(bat.exception.ma, 'BUS_CONTRACT')

    def test_binding_dung_contract_chua_dang_ky_doc_khong_thay(self):
        sk = self._phat()
        self._ghi('dung_contract', ma_contract=self.loai, phien_ban_contract='1', module='crm', phien_ban_module='1')
        with self.module.transaction():
            self.assertEqual(self._nhan(), [])
        self.cai_dat.execute('SELECT loi.su_kien_dang_ky_nhan(%s,%s,%s,%s)', ('crm', '1', self.loai, '1'))
        with self.module.transaction():
            self.assertEqual(self._nhan()[0]['id'], str(sk))

    def test_thoi_dung_contract_thu_hoi_doc(self):
        self._dang_ky()
        self._phat()
        self._ghi('thoi_dung_contract', ma_contract=self.loai, phien_ban_contract='1', module='crm', phien_ban_module='1')
        with self.module.transaction():
            self.assertEqual(self._nhan(), [])

    def test_ack_chua_nhan_xung_dot_va_sai_phap_nhan_chan(self):
        self._dang_ky()
        sk = self._phat()
        with self.assertRaises(bus.LoiSuKien) as bat, self.module.transaction():
            bus.ack(self.module, sk, **self._ctx_module())
        self.assertEqual(bat.exception.ma, 'BUS_CHUA_NHAN')
        with self.assertRaises(bus.LoiSuKien) as bat, self.module.transaction():
            self._nhan(phap_nhan_id=self.pn_khac)
        self.assertEqual(bat.exception.ma, 'BUS_PHIEN')
        with self.assertRaises(bus.LoiSuKien) as bat:
            self._phat(phap_nhan_id=self.pn_khac)
        self.assertEqual(bat.exception.ma, 'BUS_PHIEN')

    def test_sai_login_va_gia_guc_khong_vuot_phien(self):
        self._dang_ky()
        self._phat()
        with self.assertRaises(bus.LoiSuKien), self.module.transaction():
            self.module.execute("SELECT set_config('ktt.phap_nhan_id',%s,true)", (str(self.pn),))
            self._nhan(ma=self.ma)

    def test_dedupe_cung_noi_dung_va_khoa_khac_noi_dung(self):
        khoa = uuid4().hex
        sk = self._phat(khoa=khoa)
        self.assertEqual(self._phat(khoa=khoa), sk)
        with self.assertRaises(bus.LoiSuKien) as bat:
            self._phat(khoa=khoa, tham_chieu={'moc_id': str(uuid4())})
        self.assertEqual(bat.exception.ma, 'BUS_DEDUPE_XUNG_DOT')

    def test_runtime_khong_ghi_doc_bang_khong_tu_cap_subscription(self):
        for conn in (self.module, self.core):
            for bang in BANG:
                cot = 'module' if bang == 'dang_ky_nhan_su_kien' else 'phap_nhan_id'
                for cau in ('SELECT * FROM loi.{}', 'INSERT INTO loi.{} DEFAULT VALUES',
                            'UPDATE loi.{} SET ' + cot + '=' + cot):
                    with self.subTest(bang=bang, cau=cau), self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        conn.execute(sql.SQL(cau).format(sql.Identifier(bang)))
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute('SELECT loi.su_kien_dang_ky_nhan(%s,%s,%s,%s)', ('crm', '1', self.loai, '1'))
        self.assertEqual(self.conn.execute("SELECT count(*) FROM pg_class WHERE relnamespace='loi'::regnamespace AND relname=ANY(%s) AND relrowsecurity AND relforcerowsecurity", (list(BANG),)).fetchone()[0], len(BANG))


if __name__ == '__main__':
    unittest.main()
