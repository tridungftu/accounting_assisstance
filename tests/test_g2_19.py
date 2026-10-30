"""G2-19: chữ ký thật tại chỗ; PG opt-in bằng login runtime, dữ liệu DEMO."""

import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext
from dataclasses import FrozenInstanceError, asdict, replace
import json
import logging
import os
from pathlib import Path
import pickle
import secrets
import sys
import threading
import time
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import phien, su_kien as bus, tiep_nhan as tn, viec
from kho_tri_thuc.sdk_core import ngu_canh as nc, giao_dich as gd

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
except ImportError:
    Ed25519PrivateKey = None

try:
    from . import test_g2_14 as g214, test_g2_15 as g215
except ImportError:
    import test_g2_14 as g214
    import test_g2_15 as g215


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


class BoTheDemo:
    """Chỉ fixture giữ private key; production SDK không có hàm ký."""

    def __init__(self, *, nguoi=None, pn=None, ma=None):
        self.key = Ed25519PrivateKey.generate()
        self.instance = uuid4()
        self.now = time.time()
        self.nguoi, self.pn = nguoi or uuid4(), pn or uuid4()
        self.ma = ma or phien.MaBiMat('CANARY_UY_NHIEM_' + 'x' * 32)
        self.reader = self.bo_doc()

    def bo_doc(self):
        return nc.NhanRequest(issuer='core-demo', module='crm', instance_id=self.instance,
            kiem_chu_ky=self.key.public_key().verify, dong_ho=lambda: self.now)

    def payload(self, **doi):
        return dict(issuer='core-demo', module='crm', instance_id=str(self.instance),
            nguoi_dung_id=str(self.nguoi), phap_nhan_id=str(self.pn), module_nguon='core',
            operation='CRM.DEMO.LAP', hanh_dong=g214.LAP, request_id=str(uuid4()),
            ma_uy_nhiem=self.ma.lay_de_truyen(), khoa='DEMO-KEY', phat_luc=self.now,
            het_han=self.now + 30, nonce=uuid4().hex,
            hash_request=nc.bam_request('POST', '/demo?a=1', b'{"demo":true}')) | doi

    def ky_raw(self, raw):
        return phien.MaBiMat(b64(raw) + '.' + b64(self.key.sign(nc._MIEN_KY + raw)))

    def the(self, **doi):
        return self.ky_raw(json.dumps(self.payload(**doi), separators=(',', ':')).encode('utf-8'))

    def nhan(self, the=None, **doi):
        return self.reader.nhan_request(the or self.the(), **(dict(method='POST', duong_dan='/demo?a=1',
            body=b'{"demo":true}', operation='CRM.DEMO.LAP', hanh_dong=g214.LAP, khoa='DEMO-KEY') | doi))


class KetNoiDemo:
    def __init__(self):
        self.info = SimpleNamespace(transaction_status=0)
        self.login = 'dang_nhap_mod_crm'
        self.events = []
        self.closed = False
        self.loi_commit = self.loi_don = False

    @contextmanager
    def transaction(self):
        self.events.append('begin')
        self.info.transaction_status = 2
        try:
            yield
            if self.loi_commit and 'handler' in self.events:
                raise RuntimeError('CANARY_CREDENTIAL')
            self.events.append('commit')
        except BaseException:
            self.events.append('rollback')
            raise
        finally:
            self.info.transaction_status = 0

    def execute(self, cau, ts=None):
        if cau == gd._DON and self.loi_don:
            raise RuntimeError('CANARY_CREDENTIAL')
        if cau == 'SELECT session_user, current_user':
            return SimpleNamespace(fetchone=lambda: (self.login, self.login))
        return SimpleNamespace(fetchone=lambda: (1,))

    def close(self):
        self.closed = True


@unittest.skipUnless(Ed25519PrivateKey, 'CHUA_KIEM chữ ký: thiếu cryptography')
class NguCanhTest(unittest.TestCase):
    def setUp(self):
        self.bo = BoTheDemo()

    def test_chu_ky_that_context_bat_bien(self):
        ctx = self.bo.nhan()
        self.assertEqual(ctx.nguoi_dung_id, self.bo.nguoi)
        self.assertIs(ctx._da_kiem, nc._DA_KIEM)
        with self.assertRaises(FrozenInstanceError):
            ctx.module = 'm2'
        self.assertIsNone(replace(ctx, module='m2')._da_kiem)

    def test_thoi_gian_ttl_toi_da_30_va_bien_het_han(self):
        for doi in ({'het_han': self.bo.now + 30.001}, {'phat_luc': self.bo.now + 1},
                    {'het_han': self.bo.now}, {'phat_luc': self.bo.now - 31},
                    {'het_han': float('inf')}, {'phat_luc': True}, {'het_han': float('nan')}):
            with self.subTest(doi=doi), self.assertRaises(nc.LoiNguCanh):
                self.bo.nhan(self.bo.the(**doi))
        self.bo.nhan(self.bo.the(het_han=self.bo.now + .001))

    def test_sai_chu_ky_va_khong_tin_khoa_client(self):
        the = self.bo.the().lay_de_truyen().split('.')
        the[1] = b64(b'x' * 64)
        with self.assertRaises(nc.LoiNguCanh):
            self.bo.nhan(phien.MaBiMat('.'.join(the)))
        key = Ed25519PrivateKey.generate()
        raw = json.dumps(self.bo.payload()).encode()
        with self.assertRaises(nc.LoiNguCanh):
            self.bo.nhan(phien.MaBiMat(b64(raw) + '.' + b64(key.sign(nc._MIEN_KY + raw))))

    def test_sai_instance_issuer_module_operation_hanh_dong_khoa(self):
        for doi in ({'instance_id': str(uuid4())}, {'issuer': 'gia'}, {'module': 'm2'},
                    {'operation': 'CRM.KHAC'}, {'hanh_dong': 'CRM:DEMO:SUA'}, {'khoa': 'khac'},
                    {'khoa': None}, {'module_nguon': []}, {'phap_nhan_id': 'sai'}):
            with self.subTest(doi=doi), self.assertRaises(nc.LoiNguCanh):
                self.bo.nhan(self.bo.the(**doi))

    def test_hash_rang_buoc_bytes_method_path_query(self):
        for doi in ({'method': 'PATCH'}, {'duong_dan': '/demo?a=2'},
                    {'body': b'{ "demo": true }'}, {'body': b''}):
            with self.subTest(doi=doi), self.assertRaises(nc.LoiNguCanh):
                self.bo.nhan(**doi)
        self.assertNotEqual(nc.bam_request('POST', '/ab', b'c'), nc.bam_request('POST', '/a', b'bc'))

    def test_nonce_hai_luong_chi_mot_vao_va_chung_hai_bo_doc(self):
        the = self.bo.the()
        readers = [self.bo.reader, self.bo.bo_doc()]
        bat_dau = threading.Barrier(2)
        def nhan(i):
            bat_dau.wait()
            try:
                return readers[i].nhan_request(the, method='POST', duong_dan='/demo?a=1',
                    body=b'{"demo":true}', operation='CRM.DEMO.LAP', hanh_dong=g214.LAP, khoa='DEMO-KEY')
            except nc.LoiNguCanh:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(nhan, range(2)))
        self.assertEqual(sum(ctx is not None for ctx in result), 1)

    def test_sai_hash_khong_tieu_thu_nonce_retry_nghiep_vu_dung_nonce_moi(self):
        the = self.bo.the()
        with self.assertRaises(nc.LoiNguCanh):
            self.bo.nhan(the, body=b'sai')
        a = self.bo.nhan(the)
        with self.assertRaises(nc.LoiNguCanh):
            self.bo.nhan(the)
        b = self.bo.nhan()
        self.assertEqual(a.khoa, b.khoa)

    def test_thieu_truong_trung_truong_thua_truong_va_wire_sai(self):
        raw = json.dumps(self.bo.payload()).encode()
        for the in (phien.MaBiMat('sai'), phien.MaBiMat('x' * 17000),
                    self.bo.ky_raw(raw.replace(b'{', b'{"issuer":"gia",', 1)),
                    self.bo.the(alg='none'), self.bo.the(nonce='x'), self.bo.the(ma_uy_nhiem='SID')):
            with self.subTest(), self.assertRaises(nc.LoiNguCanh):
                self.bo.nhan(the)

    def test_repr_log_pickle_asdict_json_khong_lo(self):
        ctx = self.bo.nhan()
        with self.assertLogs('demo-g219', logging.INFO) as log:
            logging.getLogger('demo-g219').info('%s %r %s', ctx, self.bo.reader, self.bo.ma)
        self.assertNotIn('CANARY', ''.join(log.output))
        for obj in (ctx, self.bo.reader):
            with self.assertRaises(TypeError):
                pickle.dumps(obj)
        for goi in (lambda: asdict(ctx), lambda: json.dumps(ctx)):
            with self.assertRaises(TypeError):
                goi()

    def test_traceback_locals_khong_giu_the_uy_nhiem_credential(self):
        def verifier(sig, payload):
            credential = 'CANARY_CREDENTIAL'
            raise RuntimeError(credential + payload.decode(errors='replace'))
        reader = nc.NhanRequest(issuer='core-demo', module='crm', instance_id=self.bo.instance,
                               kiem_chu_ky=verifier)
        try:
            reader.nhan_request(self.bo.the(), method='POST', duong_dan='/demo?a=1', body=b'{}',
                operation='CRM.DEMO.LAP', hanh_dong=g214.LAP, khoa='DEMO-KEY')
        except nc.LoiNguCanh as exc:
            self.assertIsNone(exc.__context__)
            self.assertIsNone(exc.__cause__)
            for frame, _ in traceback.walk_tb(exc.__traceback__):
                if frame.f_code.co_filename.endswith('ngu_canh.py'):
                    self.assertNotIn('CANARY', repr(frame.f_locals))
            self.assertNotIn('CANARY', ''.join(traceback.format_exception(exc)))
        else:
            self.fail('Phải từ chối')


@unittest.skipUnless(Ed25519PrivateKey, 'CHUA_KIEM chữ ký: thiếu cryptography')
class GiaoDichTest(unittest.TestCase):
    def setUp(self):
        self.bo = BoTheDemo()
        self.ctx = self.bo.nhan()
        self.conn = KetNoiDemo()
        self.cua = gd.CuaGiaoDich(module='crm', dang_nhap_csdl=self.conn.login,
            ket_noi=lambda: nullcontext(self.conn), dong_ho=lambda: self.bo.now)
        identity = SimpleNamespace(nguoi_dung_id=self.ctx.nguoi_dung_id, module='crm',
            phap_nhan_id=self.ctx.phap_nhan_id, hanh_dong=self.ctx.hanh_dong, viec_id=None, the_he=None)
        self.xac = self.enterContext(patch.object(gd.phien, 'xac_minh_phien', return_value=identity))
        self.dat = self.enterContext(patch.object(gd.mtq, 'dat_ngu_canh'))

    def test_cung_ket_noi_core_va_handler_chi_commit_sau_handler(self):
        with self.cua.giao_dich(self.ctx) as tx:
            self.assertIs(tx._conn, self.conn)
            self.assertIs(tx.ngu_canh, self.ctx)
            self.assertEqual(tx.info.transaction_status, 2)
            self.assertFalse(hasattr(tx, 'commit'))
            self.assertEqual(self.conn.events, ['begin', 'commit', 'begin'])
            self.assertEqual(tx.execute('SELECT 1').fetchone(), (1,))
            self.xac.assert_called_once()
            self.dat.assert_called_once()
            self.assertIs(self.xac.call_args.args[0], self.conn)
            self.assertIs(self.dat.call_args.args[0], self.conn)
        self.assertEqual(self.conn.events[-1], 'commit')
        with self.assertRaises(gd.LoiGiaoDich):
            tx.execute('SELECT 1')

    def test_handler_loi_rollback_khong_nuot_va_don_pool(self):
        with self.assertRaises(gd.LoiGiaoDich) as bat:
            with self.cua.giao_dich(self.ctx):
                self.conn.events.append('handler')
                raise RuntimeError('CANARY_CREDENTIAL')
        self.assertIn('rollback', self.conn.events)
        self.assertEqual(self.conn.events[-1], 'commit')
        # contextlib có thể gắn lại exception đã throw vào generator; bản gốc
        # phải đã được xóa thông điệp, metadata và traceback trước khi gắn lại.
        self.assertTrue(bat.exception.__suppress_context__)
        if bat.exception.__context__ is not None:
            self.assertNotIn('CANARY', repr(bat.exception.__context__))
            self.assertIsNone(bat.exception.__context__.__traceback__)
        self.assertFalse(self.conn.closed)

    def test_sai_login_sai_actor_va_phien_thu_hoi_chan_truoc_handler(self):
        self.conn.login = 'dang_nhap_mod_m2'
        with self.assertRaises(gd.LoiGiaoDich) as bat:
            with self.cua.giao_dich(self.ctx):
                self.fail('Không được vào handler')
        self.assertEqual(bat.exception.http_status, 403)
        self.xac.assert_not_called()
        self.conn.login = 'dang_nhap_mod_crm'
        for identity in (None, SimpleNamespace(nguoi_dung_id=uuid4())):
            self.xac.return_value = identity
            with self.assertRaises(gd.LoiGiaoDich):
                with self.cua.giao_dich(self.ctx):
                    self.fail('Không được vào handler')

    def test_khong_cho_context_tu_dung_thay_doi_hoac_het_han(self):
        for ctx in (replace(self.ctx), replace(self.ctx, module='m2'), object()):
            with self.assertRaises(gd.LoiGiaoDich):
                with self.cua.giao_dich(ctx):
                    self.fail('Không được vào handler')
        self.bo.now += 30
        with self.assertRaises(gd.LoiGiaoDich):
            with self.cua.giao_dich(self.ctx):
                self.fail('Không được vào handler')
        self.assertEqual(self.conn.events, [])

    def test_login_bootstrap_khong_nhan_core_owner_module_khac(self):
        for login in ('dang_nhap_loi', 'dang_nhap_cai_dat', 'vai_doi_cau_truc_mod_crm', 'dang_nhap_mod_m2'):
            with self.assertRaises(gd.LoiGiaoDich):
                gd.CuaGiaoDich(module='crm', dang_nhap_csdl=login, ket_noi=lambda: None)

    def test_ket_noi_dang_tx_hoac_don_loi_phai_dong(self):
        self.conn.info.transaction_status = 2
        with self.assertRaises(gd.LoiGiaoDich):
            with self.cua.giao_dich(self.ctx):
                self.fail('Không được vào handler')
        self.assertTrue(self.conn.closed)
        self.conn.info.transaction_status = 0
        self.conn.closed = False
        self.conn.loi_don = True
        with self.assertRaises(gd.LoiGiaoDich):
            with self.cua.giao_dich(self.ctx):
                self.fail('Không được vào handler')
        self.assertTrue(self.conn.closed)

    def test_commit_loi_khong_tra_thanh_cong(self):
        self.conn.loi_commit = True
        with self.assertRaises(gd.LoiGiaoDich):
            with self.cua.giao_dich(self.ctx):
                self.conn.events.append('handler')
        self.assertIn('rollback', self.conn.events)

    def test_handle_va_loi_driver_khong_lo_traceback_locals(self):
        with self.cua.giao_dich(self.ctx) as tx:
            for obj in (tx, self.cua):
                self.assertNotIn('CANARY', repr(obj))
                with self.assertRaises(TypeError):
                    pickle.dumps(obj)
        def loi(conn, **kwargs):
            raw = kwargs['ma'].lay_de_truyen()
            raise RuntimeError('CANARY_CREDENTIAL ' + raw)
        self.xac.side_effect = loi
        try:
            with self.cua.giao_dich(self.ctx):
                self.fail('Không được vào handler')
        except gd.LoiGiaoDich as exc:
            self.assertIsNone(exc.__context__)
            for frame, _ in traceback.walk_tb(exc.__traceback__):
                if frame.f_code.co_filename.endswith('giao_dich.py'):
                    self.assertNotIn('CANARY', repr(frame.f_locals))
        else:
            self.fail('Phải từ chối')

    def test_giu_ma_loi_core_cas_va_dedupe_khi_dung_chung_tx(self):
        for ma in ('VIEC_CAS', 'BUS_DEDUPE_XUNG_DOT', 'KHOA_CHONG_TRUNG_KHAC_NOI_DUNG'):
            exc = RuntimeError('CANARY_DRIVER')
            exc.diag = SimpleNamespace(message_primary=ma)
            exc.sqlstate = 'P0001'
            def execute(cau, ts=None):
                if cau == 'SELECT demo':
                    raise exc
                return KetNoiDemo.execute(self.conn, cau, ts)
            with patch.object(self.conn, 'execute', side_effect=execute):
                with self.assertRaises(gd.LoiGiaoDich) as bat:
                    with self.cua.giao_dich(self.ctx) as tx:
                        if ma == 'VIEC_CAS':
                            viec._goi(tx, 'SELECT demo', ('CANARY_BIND',))
                        elif ma.startswith('BUS_'):
                            bus._goi(tx, 'SELECT demo', ('CANARY_BIND',))
                        else:
                            tn._goi(tx, 'SELECT demo', ('CANARY_BIND',))
            self.assertEqual((bat.exception.ma, bat.exception.http_status), (ma, 409))

    def test_pool_khong_duoc_bien_loi_handler_thanh_thanh_cong(self):
        @contextmanager
        def pool_sai():
            try:
                yield self.conn
            except Exception:
                pass
        self.cua._ket_noi = pool_sai
        with self.assertRaises(gd.LoiGiaoDich):
            with self.cua.giao_dich(self.ctx):
                raise RuntimeError('CANARY_CREDENTIAL')


@unittest.skipUnless(g214.psycopg is not None and os.environ.get('KHO_PG_DSN_TEST') and Ed25519PrivateKey,
                     'CHUA_KIEM PG login thật: thiếu DSN/psycopg/cryptography')
class SDKPostgresTest(unittest.TestCase):
    _ghi = g214.ViecPostgresTest._ghi
    _contract = g214.ViecPostgresTest._contract
    _trang_thai = g214.ViecPostgresTest._trang_thai
    _cap = g214.ViecPostgresTest._cap
    _ctx = g214.ViecPostgresTest._ctx
    _tao = g214.ViecPostgresTest._tao
    _resolver = g214.ViecPostgresTest._resolver
    _moi = g214.ViecPostgresTest._moi
    _su_kien_contract = g215.SuKienPostgresTest._su_kien_contract

    @classmethod
    def setUpClass(cls):
        g214.ViecPostgresTest.setUpClass.__func__(cls)
        for ck in g215.CHU_KY:
            cls.conn.execute(g214.sql.SQL('GRANT EXECUTE ON FUNCTION loi.' + ck + ' TO {}')
                             .format(g214.sql.Identifier(cls.module_login)))
        # Login module khác thật; chỉ cấp CONNECT, không SET ROLE giả runtime.
        login_khac = cls.tien_to + 'dang_nhap_mod_m2'
        mat_khau = secrets.token_urlsafe(32)
        cls.conn.execute(g214.sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS')
                         .format(g214.sql.Identifier(login_khac), g214.sql.Literal(mat_khau)))
        cls.conn.execute(g214.sql.SQL('GRANT CONNECT ON DATABASE {} TO {}')
                         .format(g214.sql.Identifier(cls.db), g214.sql.Identifier(login_khac)))
        cls.module_khac = g214.psycopg.connect(**(cls.cac_thong_tin['core'] |
            {'user': login_khac, 'password': mat_khau}), autocommit=True)
        cls.addClassCleanup(cls.module_khac.close)

    def setUp(self):
        g214.ViecPostgresTest.setUp(self)
        self.bo = BoTheDemo(nguoi=self.nd, pn=self.pn, ma=self.uy)
        self.loai = self._su_kien_contract()
        self.cua = gd.CuaGiaoDich(module='crm', dang_nhap_csdl=self.module_login,
                                 ket_noi=lambda: nullcontext(self.module))

    def test_nonce_dong_thoi_chi_mot_handler_dung_login_that(self):
        the, bat_dau = self.bo.the(), threading.Barrier(2)
        def goi(_):
            bat_dau.wait()
            try:
                ctx = self.bo.nhan(the)
            except nc.LoiNguCanh:
                return False
            with self.cua.giao_dich(ctx) as tx:
                self.assertEqual(tx.execute('SELECT session_user,current_user').fetchone(), (self.module_login,) * 2)
            return True
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(goi, range(2))), 1)

    def test_pool_commit_va_rollback_khong_giu_phien_cu(self):
        for rollback in (False, True):
            self.module.execute("SELECT set_config('ktt.ma_phien',%s,false)", (self.uy.lay_de_truyen(),))
            try:
                with self.cua.giao_dich(self.bo.nhan()) as tx:
                    self.assertEqual(tx.execute("SELECT current_setting('ktt.ma_phien',true)").fetchone()[0],
                                     self.uy.lay_de_truyen())
                    if rollback:
                        raise RuntimeError('DEMO_ROLLBACK')
            except gd.LoiGiaoDich:
                if not rollback:
                    raise
            with self.module.transaction():
                for ten in ('ma_phien', 'module', 'phap_nhan_id', 'hanh_dong', 'viec_id', 'the_he'):
                    self.assertFalse(self.module.execute('SELECT current_setting(%s,true)', ('ktt.' + ten,)).fetchone()[0])

    def test_handler_rollback_cung_nghiep_vu_bien_nhan_viec_bus(self):
        for rollback in (False, True):
            id_kq, khoa = uuid4(), uuid4().hex
            ctx = self.bo.nhan()
            try:
                with self.cua.giao_dich(ctx) as tx:
                    ts = self._ctx(ma=ctx.ma)
                    tx.execute('INSERT INTO mod_crm.ket_qua_g214 VALUES (%s,%s)', (id_kq, 'DEMO'))
                    job = viec.tao_viec(tx, loai='DEMO', phien_ban=1, khoa_dedupe=khoa,
                        tham_chieu_id=self.obj, bang_tham_chieu='doi_tuong', **ts)
                    event = bus.phat(tx, loai=self.loai, phien_ban=1, khoa=khoa,
                                     tham_chieu={'moc_id': str(self.obj)}, **ts)
                    tn.ghi_thao_tac(tx, operation=ctx.operation, khoa=khoa, noi_dung={'demo': True},
                        doi_tuong={'bang': 'doi_tuong', 'id': str(self.obj)},
                        ket_qua={'id': str(id_kq), 'viec_id': str(job)},
                        quyen_doc=dict(hanh_dong=g214.g209.XEM, doi_tuong={'bang': 'doi_tuong', 'id': str(self.obj)},
                            phien_ban_contract='1', tai_lieu_id=str(self.tai_lieu_id), bien_the='goc'), **ts)
                    if rollback:
                        raise RuntimeError('DEMO_ROLLBACK')
            except gd.LoiGiaoDich:
                if not rollback:
                    raise
            for bang, cot, gia_tri in (('mod_crm.ket_qua_g214', 'id', id_kq),
                ('loi_tai_lieu.bien_nhan_thao_tac', 'khoa_chong_trung', khoa),
                ('loi.hang_viec', 'id', job), ('loi.su_kien', 'id', event)):
                self.assertEqual(self.conn.execute('SELECT count(*) FROM ' + bang + ' WHERE ' + cot + '=%s',
                                                   (gia_tri,)).fetchone()[0], int(not rollback))

    def test_sai_login_thuc_te_va_uy_nhiem_sai_login_chan(self):
        # Module m2 có login riêng thật, không phải login crm được ghim.
        cua = gd.CuaGiaoDich(module='crm', dang_nhap_csdl=self.module_login,
                            ket_noi=lambda: nullcontext(self.module_khac))
        with self.assertRaises(gd.LoiGiaoDich) as bat:
            with cua.giao_dich(self.bo.nhan()):
                self.fail('Không được vào handler')
        self.assertEqual(bat.exception.ma, 'SDK_LOGIN')
        bo_sai = BoTheDemo(nguoi=self.nd, pn=self.pn, ma=self.ma)
        with self.assertRaises(gd.LoiGiaoDich) as bat:
            with self.cua.giao_dich(bo_sai.nhan()):
                self.fail('Không được vào handler')
        self.assertEqual(bat.exception.ma, 'SDK_UY_NHIEM')


if __name__ == '__main__':
    unittest.main()
