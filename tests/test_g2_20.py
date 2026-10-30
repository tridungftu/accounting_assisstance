"""G2-20: SDK thuần và PG opt-in, login thật, dữ liệu DEMO.

Tái dùng provisioning/fixture G2-09/10/14/15/19, không khởi động dịch vụ.
Admin chỉ dựng fixture và đọc bằng chứng; mọi nghiệp vụ chạy login runtime.
"""

import ast
from contextlib import nullcontext
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import io
import json
import logging
import os
from pathlib import Path
import pickle
import re
import sys
import time
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import ket_qua as kq_core, phien, tai_lieu, viec
from kho_tri_thuc.sdk_core import dich_vu as dv, engine, giao_dich as gd, ngu_canh as nc

try:
    from . import test_g2_09 as g209, test_g2_10 as g210, test_g2_14 as g214, test_g2_19 as g219
except ImportError:
    import test_g2_09 as g209
    import test_g2_10 as g210
    import test_g2_14 as g214
    import test_g2_19 as g219

SQL_PATH = g209.dc.THU_MUC_SQL / '020_sdk_v2.sql'
SQL = SQL_PATH.read_text(encoding='utf-8')
LAP = g209.LAP


def _context(**doi):
    ctx = nc.NguCanh(**(dict(nguoi_dung_id=uuid4(), module='crm', instance_id=uuid4(),
        phap_nhan_id=uuid4(), module_nguon='core', operation='CRM.DEMO.LAP', hanh_dong=LAP,
        request_id=uuid4(), khoa=uuid4().hex, hieu_luc_den=time.time()+30,
        ma=phien.MaBiMat('CANARY_UY_NHIEM_'+'x'*32)) | doi))
    # Chỉ fixture thuần; PG dùng chữ ký thật BoTheDemo G2-19.
    object.__setattr__(ctx, '_da_kiem', nc._DA_KIEM)
    return ctx


def _giu(**doi):
    return viec.GiuViec(**(dict(viec_id=uuid4(), buoc_viec_id=uuid4(), lan_thu_id=uuid4(),
        phap_nhan_id=uuid4(), module='crm', hanh_dong=LAP, instance_id=uuid4(), the_he=1,
        giu_den=datetime.now(timezone.utc)+timedelta(seconds=60),
        ma=phien.MaBiMat('CANARY_LEASE_'+'x'*32)) | doi))


def _data(tep_id=None, contract='demo.kq'):
    return dict(tep_id=str(tep_id or uuid4()), bien_the='goc', ma_contract=contract,
        phien_ban_contract='1', trang_thai='thanh_cong', ly_do='DEMO',
        revision_truoc=0, nguon=[])


class DichVuThuanTest(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.conn.info.transaction_status = 2
        self.conn.execute.return_value.fetchone.return_value = (uuid4(),)
        self.ctx = _context()
        self.tx = gd.GiaoDich(self.conn, self.ctx)
        self.kho = MagicMock()
        self.sdk = dv.DichVu(self.kho)
        self.tid, self.fid = uuid4(), uuid4()

    def test_ket_qua_va_audit_dung_cung_tx_ngu_canh_khong_commit(self):
        self.sdk.ket_qua.ghi(self.tx, tai_lieu_id=self.tid, du_lieu=_data(self.fid))
        self.sdk.audit.ghi(self.tx, doi_tuong='doi_tuong', doi_tuong_id=uuid4(), ket_luan='DAT')
        calls = self.conn.execute.call_args_list
        self.assertIn('ghi_ket_qua_v2', calls[0].args[0])
        self.assertIn('ghi_kiem_toan_v2', calls[1].args[0])
        for call in calls:
            cau, ts = call.args
            self.assertNotIn('CANARY', cau)
            self.assertEqual(ts[:4], (self.ctx.ma.lay_de_truyen(), 'crm',
                                      self.ctx.phap_nhan_id, LAP))
            self.assertIn(self.ctx.request_id, ts)
        for method in ('transaction', 'commit', 'rollback', 'connect'):
            getattr(self.conn, method).assert_not_called()

    def test_tu_choi_nguon_tu_khai_va_duyet(self):
        for key in ('module', 'phien_ban_module', 'engine_id', 'ham', 'phien_ban_ham',
                    'viec_id', 'buoc_id', 'lan_thu_id', 'the_he', 'actor', 'trang_thai_duyet'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.sdk.ket_qua.ghi(self.tx, tai_lieu_id=self.tid, du_lieu=_data() | {key: 'GIA'})
        self.conn.execute.assert_not_called()

    def test_module_ghi_theo_handle_lease_khong_nhan_nguon_tu_khai(self):
        giu = _giu(phap_nhan_id=self.ctx.phap_nhan_id)
        self.sdk.ket_qua.ghi(self.tx,tai_lieu_id=self.tid,du_lieu=_data(),giu_viec=giu)
        sent = self.conn.execute.call_args.args[1]
        self.assertEqual(sent[0],giu.ma.lay_de_truyen())
        self.assertEqual(sent[-2:],(giu.viec_id,giu.the_he))
        for sai in (replace(giu,module='m2'),replace(giu,phap_nhan_id=uuid4())):
            with self.assertRaises(dv.LoiDichVu):
                self.sdk.ket_qua.ghi(self.tx,tai_lieu_id=self.tid,du_lieu=_data(),giu_viec=sai)

    def test_revision_tao_id_moi_khong_sua_noi_dung_cu(self):
        data = _data()
        del data['revision_truoc']
        self.sdk.ket_qua.tao_revision(self.tx, tai_lieu_id=self.tid, ket_qua_id=self.fid,
                                    revision_truoc=2, du_lieu=data)
        sent = json.loads(self.conn.execute.call_args.args[1][5])
        self.assertEqual((sent['goc_id'], sent['revision_truoc']), (str(self.fid), 2))

    def test_boc_core_viec_bus_bien_nhan_tren_chinh_tx(self):
        ts = dict(loai='DEMO', phien_ban=1, khoa_dedupe=uuid4().hex,
                  tham_chieu_id=uuid4(), bang_tham_chieu='doi_tuong')
        doi = dict(bang='doi_tuong', id=str(uuid4()))
        with patch.object(dv._viec, 'tao_viec') as job, patch.object(dv._bus, 'phat') as event, \
                patch.object(dv._tn, 'ghi_thao_tac') as receipt:
            self.sdk.viec.tao(self.tx, **ts)
            self.sdk.su_kien.phat(self.tx, loai='demo.sk', phien_ban=1,
                                  tham_chieu={'moc_id': str(uuid4())}, khoa=uuid4().hex)
            self.sdk.bien_nhan.ghi(self.tx, noi_dung={}, doi_tuong=doi, ket_qua={}, quyen_doc={})
        for call in (job.call_args, event.call_args, receipt.call_args):
            self.assertIs(call.args[0], self.tx)
            self.assertEqual(call.kwargs['module'], self.ctx.module)
            self.assertIs(call.kwargs['ma'], self.ctx.ma)
        self.assertEqual(receipt.call_args.kwargs['operation'], self.ctx.operation)
        self.assertEqual(receipt.call_args.kwargs['khoa'], self.ctx.khoa)

    def test_cac_cua_doc_ack_va_tham_chieu_tep(self):
        with patch.object(dv._bus, 'nhan') as receive, patch.object(dv._bus, 'ack') as ack, \
                patch.object(dv._tn, 'tra_thao_tac') as receipt:
            self.sdk.su_kien.nhan(self.tx)
            self.sdk.su_kien.xac_nhan(self.tx, uuid4())
            self.sdk.bien_nhan.tra(self.tx, noi_dung={}, doi_tuong={})
        for mock in (receive, ack, receipt):
            self.assertIs(mock.call_args.args[0], self.tx)
        for method in (self.sdk.tep.tham_chieu, self.sdk.tep.mo_doc):
            method(self.tx, tai_lieu_id=self.tid, tep_id=self.fid, bien_the='goc')
        for mock in (self.kho.tham_chieu, self.kho.mo_doc):
            self.assertIs(mock.call_args.args[0], self.tx)
            self.assertEqual(mock.call_args.kwargs['phap_nhan_id'], self.ctx.phap_nhan_id)

    def test_khong_nhan_danh_tinh_request_tu_khai(self):
        for key in ('module', 'ma', 'phap_nhan_id', 'nguoi_dung_id', 'actor', 'request_id', 'the_he'):
            with self.subTest(key=key), self.assertRaises(dv.LoiDichVu):
                self.sdk.viec.tao(self.tx, **{key: 'GIA'})
        self.conn.execute.assert_not_called()

    def test_chi_nhan_tx_da_xac_minh_va_chua_dong(self):
        for tx in (self.conn, gd.GiaoDich(self.conn, replace(self.ctx)),
                   gd.GiaoDich(self.conn, _context(hieu_luc_den=0))):
            with self.assertRaises(gd.LoiGiaoDich):
                self.sdk.audit.ghi(tx, doi_tuong='doi_tuong', doi_tuong_id=self.tid, ket_luan='DAT')
        self.tx._mo = False
        with self.assertRaises(gd.LoiGiaoDich):
            self.sdk.ket_qua.ghi(self.tx, tai_lieu_id=self.tid, du_lieu=_data())
        self.conn.execute.assert_not_called()

    def test_repr_pickle_khong_lo_bi_mat(self):
        for obj in (self.sdk, self.sdk.tep, self.sdk.ket_qua, self.sdk.audit,
                    self.sdk.viec, self.sdk.bien_nhan, self.sdk.su_kien):
            self.assertNotIn('CANARY', repr(obj))
            self.assertFalse(hasattr(obj, '__dict__'))
            with self.assertRaises(TypeError):
                pickle.dumps(obj)

    def test_loi_kho_va_driver_khong_lo_bi_mat_chain(self):
        for method, mock in (
                (lambda: self.sdk.tep.mo_doc(self.tx, tai_lieu_id=self.tid,
                            tep_id=self.fid, bien_the='goc'), self.kho.mo_doc),
                (lambda: self.sdk.audit.ghi(self.tx, doi_tuong='doi_tuong',
                            doi_tuong_id=self.tid, ket_luan='DAT'), self.conn.execute)):
            mock.side_effect = RuntimeError('CANARY_PASSWORD postgresql://CANARY:SECRET@localhost')
            with self.assertRaises((dv.LoiDichVu, gd.LoiGiaoDich)) as bat:
                method()
            self.assertNotIn('CANARY', ''.join(traceback.format_exception(bat.exception)))
            self.assertIsNone(bat.exception.__context__)

    def test_traceback_locals_khong_giu_ma_bind_ro(self):
        self.conn.execute.side_effect = RuntimeError('CANARY_DRIVER')
        try:
            self.sdk.ket_qua.ghi(self.tx,tai_lieu_id=self.tid,du_lieu=_data())
        except dv.LoiDichVu as exc:
            for frame, _ in traceback.walk_tb(exc.__traceback__):
                if frame.f_code.co_filename.endswith('dich_vu.py'):
                    self.assertNotIn('CANARY',repr(frame.f_locals))
        else:
            self.fail('Phải từ chối')

    def test_sql_quote_owner_va_acl(self):
        moc = re.findall(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', SQL)
        self.assertEqual((moc[0], moc[-1]), ('$$', '$$'))
        self.assertTrue(all(a == b for a, b in zip(moc[1:-1:2], moc[2:-1:2])))
        self.assertFalse(SQL_PATH.read_bytes().startswith(b'\xef\xbb\xbf'))
        self.assertNotRegex(SQL, r'(?i)\bDROP\s+(TABLE|FUNCTION|ROLE|DATABASE)')
        self.assertIn("trang_thai='da_cai' FOR SHARE", SQL)
        self.assertIn('REVOKE ALL ON FUNCTION loi_tai_lieu.ghi_ket_qua_v2', SQL)
        self.assertIn('REVOKE ALL ON FUNCTION loi.ghi_kiem_toan_v2', SQL)
        self.assertIn("tt||'vai_chay_mod_'", SQL)

    def test_core_giu_nguyen_logic_cu_ngoai_nhanh_module(self):
        original = (SQL_PATH.parent / '009_tai_lieu.sql').read_text(encoding='utf-8')
        start = '    CREATE OR REPLACE FUNCTION loi_tai_lieu.ghi_metadata('
        end = '    CREATE OR REPLACE FUNCTION loi_tai_lieu.doc_metadata('
        old = original[original.index(start):original.index(end)].strip()
        new = SQL[SQL.index(start):SQL.index('    CREATE OR REPLACE FUNCTION loi_tai_lieu.ghi_ket_qua_v2(')].strip()
        new_branch = new[new.index("            IF p_loai IS DISTINCT FROM 'ket_qua'"):
                         new.index('        END IF;\n        muc :=')]
        new = new.replace(new_branch, "            RAISE EXCEPTION 'TAI_LIEU_CHI_CORE' USING ERRCODE='42501';\n")
        self.assertEqual(new, old)


class EngineThuanTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.giu = _giu()
        self.kenh = MagicMock(spec=['goi'])
        self.sdk = engine.SDKEngine(self.giu, kenh_core=self.kenh, dong_ho=lambda: self.now)
        self.data = _data()
        del self.data['tep_id']

    def test_engine_api_dir_dict_khong_co_sql_ket_noi_dsn(self):
        self.assertFalse(hasattr(self.sdk, '__dict__'))
        for obj in (self.sdk, self.giu):
            names = set(dir(obj)) | set(getattr(obj, '__dict__', {}))
            self.assertFalse(names & {'execute', 'cursor', 'connection', 'conn', 'dsn', 'commit',
                                     'rollback', '_conn', '_ctx', 'transaction', 'ngu_canh'})
        source = Path(engine.__file__).read_text(encoding='utf-8')
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, {'execute', 'cursor', 'connect', 'connection', 'dsn'})
        self.assertNotRegex(source, r'(?i)\b(?:SELECT|INSERT|UPDATE|DELETE)\s+')

    def test_doc_dau_vao_tep_va_ghi_chi_qua_kenh_core(self):
        self.sdk.doc_dau_vao()
        self.sdk.mo_doc(uuid4())
        self.sdk.ghi_ket_qua(luong=io.BytesIO(b'DEMO'), ten='demo.txt',
                            du_lieu=self.data, revision_tep_truoc=0)
        calls = self.kenh.goi.call_args_list
        self.assertEqual([c.args[0] for c in calls], ['doc_dau_vao', 'mo_doc', 'ghi_ket_qua'])
        self.assertTrue(all(c.args[1] is self.giu for c in calls))

    def test_nguon_engine_tu_khai_bi_bac_truoc_goi_core(self):
        for key in ('engine_id', 'module', 'actor', 'ham', 'phien_ban_ham', 'phien_ban_module',
                    'viec_id', 'the_he', 'tep_id', 'trang_thai_duyet'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.sdk.ghi_ket_qua(luong=io.BytesIO(b'DEMO'), ten='demo.txt',
                    du_lieu=self.data | {key: 'GIA'}, revision_tep_truoc=0)
        self.kenh.goi.assert_not_called()

    def test_lease_het_chan_doc_ghi_heartbeat_khong_cham_core(self):
        self.now = self.giu.giu_den
        for goi in (self.sdk.doc_dau_vao, lambda: self.sdk.mo_doc(uuid4()), self.sdk.heartbeat,
                    lambda: self.sdk.ghi_ket_qua(luong=io.BytesIO(), ten='demo.txt',
                        du_lieu=self.data, revision_tep_truoc=0)):
            with self.assertRaises(engine.LoiEngine) as bat:
                goi()
            self.assertEqual(bat.exception.ma, 'VIEC_MAT_LEASE')
        self.kenh.goi.assert_not_called()

    def test_heartbeat_chi_doi_han_khong_doi_lease(self):
        self.kenh.goi.return_value = replace(self.giu, giu_den=self.giu.giu_den+timedelta(seconds=60))
        self.assertTrue(self.sdk.heartbeat(lease_giay=60))
        self.now = self.giu.giu_den
        self.sdk.doc_dau_vao()
        self.assertGreater(self.kenh.goi.call_args.args[1].giu_den, self.giu.giu_den)
        self.kenh.goi.return_value = replace(self.giu, the_he=2)
        with self.assertRaises(engine.LoiEngine):
            self.sdk.heartbeat()

    def test_core_bac_lease_va_loi_transport_khong_lo_token(self):
        for ma in ('VIEC_MAT_LEASE', 'KHAC'):
            exc = RuntimeError('CANARY_LEASE postgresql://CANARY:SECRET@localhost')
            exc.ma = ma
            self.kenh.goi.side_effect = exc
            with self.assertRaises(engine.LoiEngine) as bat:
                self.sdk.doc_dau_vao()
            self.assertNotIn('CANARY', ''.join(traceback.format_exception(bat.exception)))
            self.assertEqual(bat.exception.ma, 'VIEC_MAT_LEASE' if ma == 'VIEC_MAT_LEASE' else 'ENGINE_CORE')
            self.assertIsNone(bat.exception.__context__)

    def test_repr_log_pickle_asdict_khong_lo_bi_mat(self):
        with self.assertLogs('demo-g220',logging.INFO) as log:
            logging.getLogger('demo-g220').info('%r %s',self.sdk,self.giu)
        self.assertNotIn('CANARY',''.join(log.output))
        for obj in (self.sdk, self.giu):
            self.assertNotIn('CANARY', '%r' % obj)
            with self.assertRaises(TypeError):
                pickle.dumps(obj)
        with self.assertRaises(TypeError):
            asdict(self.giu)


@unittest.skipUnless(g214.psycopg is not None and os.environ.get('KHO_PG_DSN_TEST')
                     and g219.Ed25519PrivateKey is not None,
                     'CHUA_KIEM PG: thiếu psycopg/KHO_PG_DSN_TEST/cryptography')
class SDKPostgresTest(unittest.TestCase):
    _ghi = g219.SDKPostgresTest._ghi
    _contract = g219.SDKPostgresTest._contract
    _trang_thai = g219.SDKPostgresTest._trang_thai
    _cap = g219.SDKPostgresTest._cap
    _ctx = g219.SDKPostgresTest._ctx
    _tao = g219.SDKPostgresTest._tao
    _resolver = g219.SDKPostgresTest._resolver
    _moi = g219.SDKPostgresTest._moi
    _su_kien_contract = g219.SDKPostgresTest._su_kien_contract
    _nhan = g214.ViecPostgresTest._nhan
    _het_han = g214.ViecPostgresTest._het_han

    @classmethod
    def setUpClass(cls):
        g219.SDKPostgresTest.setUpClass.__func__(cls)

    def setUp(self):
        g219.SDKPostgresTest.setUp(self)
        self.kho = g210.kho_tam()
        self.sdk = dv.DichVu(self.kho)
        with self.core.transaction():
            self.ref = self.kho.tai_len(self.core, tai_lieu_id=self.tai_lieu_id,
                luong=io.BytesIO(b'DEMO'), ten='demo.txt', bien_the='goc', revision_truoc=0,
                request_id=uuid4(), **self._ctx())
        self.data = _data(self.ref['tep_id'], self.ct)
        self.data['nguon'] = [dict(tep_id=self.ref['tep_id'], sha256=self.ref['sha256'])]

    def _ghi_kq(self, tx, **doi):
        return self.sdk.ket_qua.ghi(tx, tai_lieu_id=self.tai_lieu_id, du_lieu=self.data | doi)

    def _ngu_canh(self):
        khoa = uuid4().hex
        return self.bo.nhan(self.bo.the(khoa=khoa), khoa=khoa)

    def test_module_ket_qua_audit_bien_nhan_viec_bus_cung_tx_rollback_0_dong(self):
        for rollback in (False, True):
            ctx = self._ngu_canh()
            with self.assertRaises(gd.LoiGiaoDich) if rollback else nullcontext():
                with self.cua.giao_dich(ctx) as tx:
                    self.assertEqual(tx.execute('SELECT session_user,current_user').fetchone(),
                                     (self.module_login,)*2)
                    kid = self._ghi_kq(tx)
                    aid = self.sdk.audit.ghi(tx, doi_tuong='doi_tuong', doi_tuong_id=self.obj, ket_luan='DAT')
                    job = self.sdk.viec.tao(tx, loai='DEMO', phien_ban=1,
                        khoa_dedupe=ctx.khoa, tham_chieu_id=self.obj, bang_tham_chieu='doi_tuong')
                    event = self.sdk.su_kien.phat(tx, loai=self.loai, phien_ban=1,
                        khoa=ctx.khoa, tham_chieu={'moc_id': str(self.obj)})
                    self.sdk.bien_nhan.ghi(tx, noi_dung={'demo': True},
                        doi_tuong={'bang': 'doi_tuong', 'id': str(self.obj)},
                        ket_qua={'id': str(kid), 'viec_id': str(job)},
                        quyen_doc=dict(hanh_dong=g209.XEM,
                            doi_tuong={'bang': 'doi_tuong', 'id': str(self.obj)},
                            phien_ban_contract='1', tai_lieu_id=str(self.tai_lieu_id), bien_the='goc'))
                    # Kết nối observer chưa thấy gì trước commit: SDK không tự commit.
                    self.assertEqual(self.conn.execute('SELECT count(*) FROM loi_tai_lieu.ket_qua_xu_ly WHERE id=%s',
                                                       (kid,)).fetchone()[0], 0)
                    if rollback:
                        raise RuntimeError('DEMO_ROLLBACK')
            for bang, cot, value in (('loi_tai_lieu.ket_qua_xu_ly','id',kid),
                    ('loi.nhat_ky_kiem_toan','id',aid), ('loi.nhat_ky_kiem_toan','request_id',ctx.request_id),
                    ('loi.hang_viec','id',job), ('loi.su_kien','id',event),
                    ('loi_tai_lieu.bien_nhan_thao_tac','khoa_chong_trung',ctx.khoa)):
                count = self.conn.execute('SELECT count(*) FROM '+bang+' WHERE '+cot+'=%s', (value,)).fetchone()[0]
                self.assertGreater(count, 0) if not rollback else self.assertEqual(count, 0)

    def test_core_gan_nguon_module_actor_va_duyet_rieng(self):
        ctx = self._ngu_canh()
        with self.cua.giao_dich(ctx) as tx:
            kid = self._ghi_kq(tx)
            aid = self.sdk.audit.ghi(tx, doi_tuong='doi_tuong', doi_tuong_id=self.obj, ket_luan='DAT')
        row = self.conn.execute('''SELECT module,phien_ban_module,engine_id,ham,phien_ban_ham,
            viec_id,buoc_id,lan_thu_id,the_he,tao_boi FROM loi_tai_lieu.ket_qua_xu_ly WHERE id=%s''', (kid,)).fetchone()
        self.assertEqual(row, ('crm','1',None,LAP,'1',None,None,None,None,self.nd))
        audit = self.conn.execute('''SELECT nguoi_dung_id,module,phap_nhan_id,request_id,dang_nhap_csdl
            FROM loi.nhat_ky_kiem_toan WHERE id=%s''', (aid,)).fetchone()
        self.assertEqual(audit, (self.nd,'crm',self.pn,ctx.request_id,self.module_login))
        self.assertEqual(self.conn.execute('SELECT trang_thai_duyet FROM loi_tai_lieu.ket_qua_duyet WHERE ket_qua_id=%s',
                                          (kid,)).fetchone(), ('chua_duyet',))
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi_tai_lieu.ket_qua_cong_bo WHERE ket_qua_id=%s',
                                          (kid,)).fetchone()[0], 0)

    def test_module_lease_core_gan_viec_buoc_lan_thu_va_bac_lease_cu(self):
        giu = self._nhan(module=True)
        with self.cua.giao_dich(self._ngu_canh()) as tx:
            kid = self.sdk.ket_qua.ghi(tx,tai_lieu_id=self.tai_lieu_id,
                                       du_lieu=self.data,giu_viec=giu)
        row = self.conn.execute('''SELECT viec_id,buoc_id,lan_thu_id,the_he,engine_id
            FROM loi_tai_lieu.ket_qua_xu_ly WHERE id=%s''',(kid,)).fetchone()
        self.assertEqual(row,(giu.viec_id,giu.buoc_viec_id,giu.lan_thu_id,giu.the_he,None))
        self._het_han(giu)
        with self.assertRaises(gd.LoiGiaoDich):
            with self.cua.giao_dich(self._ngu_canh()) as tx:
                self.sdk.ket_qua.ghi(tx,tai_lieu_id=self.tai_lieu_id,
                                    du_lieu=self.data,giu_viec=giu)

    def test_module_khac_va_phap_nhan_khac_bi_bac(self):
        for module, pn in (('m2',self.pn), ('crm',self.pn_khac)):
            with self.assertRaises(g214.psycopg.Error):
                self.module.execute('SELECT loi_tai_lieu.ghi_ket_qua_v2(%s,%s,%s,%s,%s,%s::jsonb,%s)',
                    (self.uy.lay_de_truyen(),module,pn,LAP,self.tai_lieu_id,json.dumps(self.data),uuid4()))
            with self.assertRaises(g214.psycopg.Error):
                self.module.execute('SELECT loi.ghi_kiem_toan_v2(%s,%s,%s,%s,%s,%s,%s,%s)',
                    (self.uy.lay_de_truyen(),module,pn,LAP,'doi_tuong',self.obj,'DAT',uuid4()))

    def test_nguon_tu_khai_bi_bac_ca_goi_sql_truc_tiep(self):
        for key in ('module','engine_id','phien_ban_module','ham','actor','viec_id','trang_thai_duyet'):
            with self.subTest(key=key), self.assertRaises(g214.psycopg.Error):
                self.module.execute('SELECT loi_tai_lieu.ghi_ket_qua_v2(%s,%s,%s,%s,%s,%s::jsonb,%s)',
                    (self.uy.lay_de_truyen(),'crm',self.pn,LAP,self.tai_lieu_id,
                     json.dumps(self.data | {key:'GIA'}),uuid4()))

    def test_module_khong_ghi_ket_qua_thuoc_module_khac(self):
        # Fixture giữ cùng pháp nhân/quyền MTQ nhưng tài liệu thuộc module khác.
        self._ghi('module', ma='m2', ten='DEMO m2')
        tid = uuid4()
        self.conn.execute('''INSERT INTO loi_tai_lieu.tai_lieu
            (id,phap_nhan_id,module,loai,ten,bang_doi_tuong,doi_tuong_id,phien_ban_contract,tao_boi)
            VALUES (%s,%s,'m2','DEMO','DEMO','doi_tuong',%s,'1',%s)''', (tid,self.pn,self.obj,self.nd))
        with self.assertRaises(gd.LoiGiaoDich):
            with self.cua.giao_dich(self._ngu_canh()) as tx:
                self.sdk.ket_qua.ghi(tx, tai_lieu_id=tid, du_lieu=self.data)

    def test_revision_hash_va_thieu_tep_giu_quy_tac_g209(self):
        with self.cua.giao_dich(self._ngu_canh()) as tx:
            kid = self._ghi_kq(tx)
        for doi in ({'goc_id':str(kid),'revision_truoc':0},
                    {'nguon':[dict(tep_id=self.ref['tep_id'],sha256='b'*64)]}):
            with self.assertRaises(gd.LoiGiaoDich):
                with self.cua.giao_dich(self._ngu_canh()) as tx:
                    self._ghi_kq(tx, **doi)
        with self.cua.giao_dich(self._ngu_canh()) as tx:
            kid2 = self._ghi_kq(tx, goc_id=str(kid), revision_truoc=1)
            missing = self._ghi_kq(tx, tep_id=None, nguon=[])
        self.assertNotEqual(kid, kid2)
        for target in (kid2, missing):
            self.assertEqual(self.conn.execute('SELECT trang_thai_duyet FROM loi_tai_lieu.ket_qua_duyet WHERE ket_qua_id=%s',
                                               (target,)).fetchone(), ('chua_duyet',))
        with self.assertRaises(tai_lieu.LoiTaiLieu) as bat:
            tai_lieu.cong_bo(self.core,tai_lieu_id=self.tai_lieu_id,ket_qua_id=missing,
                            request_id=uuid4(),**self._ctx(g209.DUYET))
        self.assertEqual(bat.exception.ma,'TAI_LIEU_THIEU_TEP_HASH')

    def test_mtq_bac_va_uy_nhiem_het_han_khong_ghi(self):
        self.conn.execute('UPDATE loi.mtq_o SET cho_phep=false WHERE dong_id IN '
            '(SELECT id FROM loi.mtq_dong WHERE phap_nhan_id=%s)', (self.pn,))
        with self.assertRaises(gd.LoiGiaoDich):
            with self.cua.giao_dich(self._ngu_canh()) as tx:
                self._ghi_kq(tx)
        self.conn.execute('UPDATE loi.phien_xac_thuc SET tao_luc=clock_timestamp()-interval \'1 hour\', '
                          'hieu_luc_den=clock_timestamp()-interval \'1 second\' '
                          'WHERE phap_nhan_id=%s', (self.pn,))
        with self.assertRaises(gd.LoiGiaoDich):
            with self.cua.giao_dich(self._ngu_canh()):
                self.fail('Phiên hết hạn phải bị từ chối')

    def test_acl_definer_va_runtime_khong_dml_bang_chung(self):
        for ten in ('loi_tai_lieu.ghi_ket_qua_v2','loi.ghi_kiem_toan_v2'):
            r = self.conn.execute('SELECT prosecdef,proconfig FROM pg_proc WHERE oid=%s::regproc',(ten,)).fetchone()
            self.assertTrue(r[0])
            self.assertIn('search_path=pg_catalog, pg_temp',r[1])
            self.assertFalse(self.conn.execute('''SELECT EXISTS(SELECT FROM pg_proc p,
                LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
                WHERE p.oid=%s::regproc AND a.grantee=0 AND a.privilege_type='EXECUTE')''', (ten,)).fetchone()[0])
        for bang in ('loi_tai_lieu.ket_qua_xu_ly','loi.nhat_ky_kiem_toan'):
            with self.assertRaises(g214.psycopg.errors.InsufficientPrivilege):
                self.module.execute('INSERT INTO '+bang+' DEFAULT VALUES')
        with self.assertRaises(g214.psycopg.errors.InsufficientPrivilege):
            self.module.execute('SELECT loi_tai_lieu.ghi_metadata(%s,%s,%s,%s,%s,%s,%s::jsonb,%s)',
                (self.uy.lay_de_truyen(),'crm',self.pn,LAP,'ket_qua',self.tai_lieu_id,json.dumps(self.data),uuid4()))

    def test_engine_lease_hop_le_core_gan_nguon_va_mat_lease_tu_choi(self):
        # Kênh fixture đóng vai Core IPC: connection chỉ ở phía server này.
        # Engine chỉ được thấy đối tượng transport với goi(), không nhận conn.
        engine_id = self.conn.execute("SELECT id FROM loi.engine_dinh_nghia WHERE ma='demo_g214'").fetchone()[0]
        job = self._moi(engine_id=engine_id)
        # Chỉ nhận việc engine vừa tạo, tránh việc module CHO của fixture.
        self.conn.execute("UPDATE loi.hang_viec SET thu_lai_sau=clock_timestamp()+interval '1 day' WHERE id=%s",(self.viec_id,))
        giu = self._nhan()
        self.assertEqual(giu.viec_id,job)
        def verify(conn, handle):
            viec.trang_thai_lease(conn, handle)
            return kq_core.NguonCore('crm',self.pn,'1',engine_id,'DEMO_ENGINE','1',
                handle.viec_id,handle.the_he,handle.buoc_viec_id,handle.lan_thu_id)
        service = kq_core.BanGiaoKetQua(self.kho,xac_minh_core=verify)
        def goi(op, handle, **payload):
            with self.core.transaction():
                # Core lại kiểm lease trước đọc bytes/ghi; giữ khóa đến commit.
                viec.trang_thai_lease(self.core,handle)
                if op == 'heartbeat':
                    return viec.gia_han(self.core,handle,**payload)
                if op == 'doc_dau_vao':
                    return {'tai_lieu_id':str(self.tai_lieu_id)}
                if op == 'mo_doc':
                    if str(payload['tep_id']) != self.ref['tep_id']:
                        raise ValueError('Tệp ngoài đầu vào được cấp')
                    return self.kho.mo_doc(self.core,tai_lieu_id=self.tai_lieu_id,
                        bien_the='goc',**payload,**self._ctx(g209.XEM))
                return service.ghi(self.core,giu_viec=handle,tai_lieu_id=self.tai_lieu_id,
                    request_id=uuid4(),het_han_luc=None,**payload,**self._ctx(ma=handle.ma))
        transport = SimpleNamespace(goi=goi)
        api = engine.SDKEngine(giu,kenh_core=transport)
        self.assertEqual(api.doc_dau_vao()['tai_lieu_id'],str(self.tai_lieu_id))
        with api.mo_doc(self.ref['tep_id']) as stream:
            self.assertEqual(stream.read(),b'DEMO')
        self.assertTrue(api.heartbeat())
        data = dict(self.data,bien_the='ocr')
        del data['tep_id']
        result = api.ghi_ket_qua(luong=io.BytesIO(b'DEMO OUTPUT'),ten='out.txt',du_lieu=data,revision_tep_truoc=0)
        row = self.conn.execute('''SELECT module,engine_id,viec_id,buoc_id,lan_thu_id,the_he
            FROM loi_tai_lieu.ket_qua_xu_ly WHERE id=%s''',(result['ket_qua_id'],)).fetchone()
        self.assertEqual(row,('crm',engine_id,giu.viec_id,giu.buoc_viec_id,giu.lan_thu_id,giu.the_he))
        self._het_han(giu)
        before = self.conn.execute('SELECT count(*) FROM loi_tai_lieu.ket_qua_xu_ly WHERE tai_lieu_id=%s',
                                   (self.tai_lieu_id,)).fetchone()[0]
        with self.assertRaises(engine.LoiEngine) as bat:
            api.ghi_ket_qua(luong=io.BytesIO(b'NO WRITE'),ten='out.txt',du_lieu=data,revision_tep_truoc=1)
        self.assertEqual(bat.exception.ma,'VIEC_MAT_LEASE')
        self.assertEqual(before,self.conn.execute('SELECT count(*) FROM loi_tai_lieu.ket_qua_xu_ly WHERE tai_lieu_id=%s',
                                                 (self.tai_lieu_id,)).fetchone()[0])


if __name__ == '__main__':
    unittest.main()
