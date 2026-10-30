"""G2-09: thuần/mock; PG16 login thật + phiên, chỉ KHO_PG_DSN_TEST.

PG tạo kho_test_* và role riêng; không DROP, không khởi động/dừng dịch vụ.
Admin chỉ dựng schema/fixture; ca nghiệp vụ dùng kết nối Core/module thật.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
from threading import Barrier
import traceback
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import tai_lieu as tl, doi_cau_truc as dc, phien, cong_tac

try:
    from . import test_g2_06 as g206
except ImportError:
    import test_g2_06 as g206

psycopg = g206.psycopg
if psycopg is not None:
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict

ADMIN_DSN = os.environ.get('KHO_PG_DSN_TEST')
SQL_PATH = dc.THU_MUC_SQL / '009_tai_lieu.sql'
SQL_TL = SQL_PATH.read_text(encoding='utf-8')
LAP, SUA, XEM, DUYET = ('CRM:TIEP_NHAN:' + h for h in ('LAP', 'SUA', 'XEM', 'DUYET'))
BAM = hashlib.sha256(b'DEMO').hexdigest()
CORE = dict(phien_ban_module='1', ham='demo.tao', phien_ban_ham='1')
BANG = ('tai_lieu', 'tep_goc', 'tai_lieu_tep', 'quyen_tai_lieu', 'ket_qua_xu_ly',
        'nguon_ket_qua', 'ket_qua_duyet', 'ket_qua_cong_bo')


class TaiLieuThuanTest(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.id = uuid4()
        self.ctx = dict(ma=phien.MaBiMat('CANARY_PHIEN'), module='crm', phap_nhan_id=uuid4(), hanh_dong=LAP)
        self.thong_tin = dict(loai='DEMO', ten='DEMO', doi_tuong={'bang': 'doi_tuong', 'id': str(uuid4())},
                             phien_ban_contract='1')
        self.kq = dict(tep_id=None, bien_the='ocr', ma_contract='demo.v1', phien_ban_contract='1',
                       trang_thai='thanh_cong', ly_do='DEMO', revision_truoc=0,
                       nguon=[dict(tep_id=str(uuid4()), sha256=BAM)])

    def _tao(self, **doi):
        return tl.tao(self.conn, tai_lieu_id=self.id, thong_tin=doi.pop('thong_tin', self.thong_tin),
                      request_id=uuid4(), **{**self.ctx, **doi})

    def _ket_qua(self, **doi):
        return tl.ghi_ket_qua_core(self.conn, tai_lieu_id=self.id, du_lieu=doi.pop('du_lieu', self.kq),
            thong_tin_core=doi.pop('thong_tin_core', CORE), request_id=uuid4(), **{**self.ctx, **doi})

    def test_bind_khong_tu_commit(self):
        self._tao()
        cau, ts = self.conn.execute.call_args.args
        self.assertNotIn('CANARY', cau)
        self.assertEqual(ts[:6], ('CANARY_PHIEN', 'crm', self.ctx['phap_nhan_id'], LAP, 'tai_lieu', self.id))
        self.assertEqual(json.loads(ts[6]), self.thong_tin)
        for ten in ('commit', 'rollback', 'transaction'):
            getattr(self.conn, ten).assert_not_called()

    def test_khong_nhan_actor_nguon_tu_khai_trong_payload(self):
        for khoa in ('actor', 'module', 'engine_id', 'ham', 'phien_ban_module', 'viec_id', 'trang_thai_duyet'):
            with self.subTest(khoa=khoa), self.assertRaises(ValueError):
                self._ket_qua(du_lieu={**self.kq, khoa: 'GIA'})
        self.conn.execute.assert_not_called()

    def test_thong_tin_core_tach_rieng_va_revision_khong_phai_duyet(self):
        self._ket_qua()
        data = json.loads(self.conn.execute.call_args.args[1][6])
        self.assertEqual(data['ham'], CORE['ham'])
        self.assertNotIn('trang_thai_duyet', data)
        tl.duyet(self.conn, tai_lieu_id=self.id, ket_qua_id=uuid4(), row_version='3',
            trang_thai_duyet='da_duyet', request_id=uuid4(), **{**self.ctx, 'hanh_dong': DUYET})
        data = json.loads(self.conn.execute.call_args.args[1][6])
        self.assertEqual(data['row_version'], '3')
        self.assertNotIn('revision', data)

    def test_revision_va_cas_khong_nhan_bool_am_hoac_float(self):
        for ban in (True, -1, '1', 1.5, None, 9223372036854775808):
            with self.subTest(ban=ban), self.assertRaises(ValueError):
                self._ket_qua(du_lieu={**self.kq, 'revision_truoc': ban})
        for ban in (1, True, '0', '01', '9223372036854775808'):
            with self.subTest(ban=ban), self.assertRaises(ValueError):
                tl.duyet(self.conn, tai_lieu_id=self.id, ket_qua_id=uuid4(), row_version=ban,
                    trang_thai_duyet='da_duyet', request_id=uuid4(), **{**self.ctx, 'hanh_dong': DUYET})
        self.conn.execute.assert_not_called()

    def test_phien_module_hanh_dong_viec_khong_hop_le(self):
        for doi in ({'ma': 'THO'}, {'module': 'core'}, {'module': 'crm.sql'}, {'hanh_dong': XEM},
                    {'hanh_dong': 'M2:HOA_DON:LAP'}, {'viec_id': uuid4()}, {'the_he': 1},
                    {'viec_id': uuid4(), 'the_he': True}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                self._tao(**doi)
        self.conn.execute.assert_not_called()

    def test_nguon_chi_tham_chieu_va_hash_revision(self):
        for nguon in ([{}], [{'tep_id': str(uuid4()), 'sha256': 'GIA'}],
                      [{'tep_id': str(uuid4()), 'ket_qua_id': str(uuid4()), 'sha256': BAM}],
                      [{'ket_qua_id': str(uuid4()), 'sha256': BAM}],
                      [{'tep_id': str(uuid4()), 'sha256': BAM, 'revision': 1}],
                      [{**self.kq['nguon'][0], 'engine': 'OCR_GIA'}], None):
            with self.subTest(nguon=nguon), self.assertRaises(ValueError):
                self._ket_qua(du_lieu={**self.kq, 'nguon': nguon})
        self.conn.execute.assert_not_called()

    def test_tep_chi_nhan_hash_chuan_va_kich_thuoc_chinh_xac(self):
        tep = dict(ten_tep='DEMO.txt', sha256=BAM, kich_thuoc=4, mime='text/plain', khoa_luu_tru='raw/demo')
        for doi in ({'sha256': None}, {'sha256': 'A'*64}, {'kich_thuoc': True}, {'kich_thuoc': -1},
                    {'kich_thuoc': 9007199254740992}, {'duong_dan': 'C:/GIA'}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                tl.ghi_tep_da_kiem(self.conn, tai_lieu_id=self.id, thong_tin={**tep, **doi},
                    request_id=uuid4(), **self.ctx)
        self.conn.execute.assert_not_called()

    def test_gan_bien_the_cap_quyen_va_cong_bo_dung_cua(self):
        tl.gan_bien_the(self.conn, tai_lieu_id=self.id, tep_id=uuid4(), bien_the='da_che',
            revision_truoc=0, request_id=uuid4(), **self.ctx)
        self.assertEqual(self.conn.execute.call_args.args[1][4], 'bien_the')
        tl.cap_quyen(self.conn, tai_lieu_id=self.id, du_lieu=dict(nguoi_dung_id=str(uuid4()),
            bien_the='da_che', cho_phep=False, revision_truoc=1), request_id=uuid4(),
            **{**self.ctx, 'hanh_dong': DUYET})
        self.assertEqual(self.conn.execute.call_args.args[1][4], 'quyen')
        tl.cong_bo(self.conn, tai_lieu_id=self.id, ket_qua_id=uuid4(), request_id=uuid4(),
            **{**self.ctx, 'hanh_dong': DUYET})
        self.assertEqual(self.conn.execute.call_args.args[1][4], 'cong_bo')

    def test_doc_chi_bien_the_duoc_hoi_va_khong_nhan_actor(self):
        tl.lay(self.conn, tai_lieu_id=self.id, bien_the='da_che', **{**self.ctx, 'hanh_dong': XEM})
        self.assertEqual(self.conn.execute.call_args.args[1][5], 'da_che')
        with self.assertRaises(ValueError):
            tl.lay(self.conn, tai_lieu_id=self.id, bien_the='*', **{**self.ctx, 'hanh_dong': XEM})

    def test_loi_driver_khong_lo_token_hoac_sql(self):
        for ma in ('TAI_LIEU_REVISION', 'TAI_LIEU_THAT_BAI'):
            loi = RuntimeError('CANARY_PHIEN postgresql://CANARY:BI_MAT@localhost')
            loi.diag = MagicMock(message_primary=ma)
            self.conn.execute.side_effect = loi
            with self.assertRaises(tl.LoiTaiLieu) as bat:
                self._tao()
            self.assertEqual(bat.exception.ma, ma)
            self.assertIsNone(bat.exception.__context__)
            self.assertNotIn('CANARY', ''.join(traceback.format_exception(bat.exception)))

    def test_sql_bien_gioi_va_dollar_quote(self):
        moc = re.findall(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', SQL_TL)
        self.assertEqual((moc[0], moc[-1]), ('$$', '$$'))
        self.assertEqual(len(moc) % 2, 0)
        self.assertTrue(all(a == b for a, b in zip(moc[1:-1:2], moc[2:-1:2])))
        self.assertNotRegex(SQL_TL, r'(?i)\b(?:UPDATE|DELETE FROM)\s+loi_tai_lieu\.')
        self.assertNotRegex(SQL_TL, r'(?i)\bDROP\s+(?:TABLE|FUNCTION|DATABASE|ROLE)')
        self.assertNotRegex(SQL_TL, r'(?i)(?:FROM|JOIN|REFERENCES)\s+(?:mod_|master\.)')
        self.assertIn('WITH CHECK (phap_nhan_id IN', SQL_TL)
        self.assertFalse(SQL_PATH.read_bytes().startswith(b'\xef\xbb\xbf'))


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, 'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class TaiLieuPostgresTest(unittest.TestCase):
    _ghi = g206.MTQPostgresTest._ghi
    _contract = g206.MTQPostgresTest._contract
    _trang_thai = g206.MTQPostgresTest._trang_thai
    _resolver = g206.MTQPostgresTest._resolver

    @classmethod
    def setUpClass(cls):
        # Dùng fixture provisioning đã có; 001..009 áp đúng thứ tự và ghi sổ.
        g206.MTQPostgresTest.setUpClass.__func__(cls)
        dc.ap_doi_cau_truc(cls.conn, sorted(dc.THU_MUC_SQL.glob('00[1-9]_*.sql')))
        cls.module_login = cls.tien_to + 'dang_nhap_mod_crm'
        vai_module = cls.tien_to + 'vai_chay_mod_crm'
        mk = secrets.token_urlsafe(32)
        cls.conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN INHERIT NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB')
                         .format(sql.Identifier(vai_module)))
        cls.conn.execute(sql.SQL('CREATE ROLE {} LOGIN INHERIT NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB PASSWORD {}')
                         .format(sql.Identifier(cls.module_login), sql.Literal(mk)))
        cls.conn.execute(sql.SQL('GRANT {} TO {} WITH INHERIT TRUE, SET FALSE, ADMIN FALSE')
                         .format(sql.Identifier(vai_module), sql.Identifier(cls.module_login)))
        cls.conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier(cls.db), sql.Identifier(cls.module_login)))
        cls.conn.execute(sql.SQL('GRANT USAGE ON SCHEMA loi,loi_tai_lieu TO {}').format(sql.Identifier(vai_module)))
        cls.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION loi_tai_lieu.doc_metadata(text,text,uuid,text,uuid,text,uuid,bigint) TO {}')
                         .format(sql.Identifier(vai_module)))
        for khoa in ('log_parameter_max_length', 'log_parameter_max_length_on_error'):
            cls.conn.execute(sql.SQL('ALTER ROLE {} SET {}=0').format(sql.Identifier(cls.module_login), sql.Identifier(khoa)))
        cls.module = psycopg.connect(**{**cls.cac_thong_tin['core'], 'user': cls.module_login, 'password': mk}, autocommit=True)
        cls.addClassCleanup(cls.module.close)

    def setUp(self):
        self._resolver()
        self.nd, self.pn, self.pn_khac, self.obj = (uuid4() for _ in range(4))
        self.conn.execute("INSERT INTO loi.nguoi_dung(id,dang_nhap,ten,vai_tro) VALUES (%s,%s,'DEMO','XEM')", (self.nd, 'demo_'+self.nd.hex))
        for pn in (self.pn, self.pn_khac):
            self.conn.execute("INSERT INTO loi.phap_nhan(id,ma,ten) VALUES (%s,%s,'DEMO')", (pn, pn.hex))
            self.conn.execute('INSERT INTO loi.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,%s)', (self.nd, pn, ['crm', 'core']))
            phong, pb, dong, gan = (uuid4() for _ in range(4))
            self.conn.execute("INSERT INTO loi.mtq_phong(id,phap_nhan_id,ma,ten) VALUES (%s,%s,'DEMO','DEMO')", (phong, pn))
            self.conn.execute("INSERT INTO loi.mtq_phien_ban(id,phap_nhan_id,so_phien_ban,tao_boi,ly_do) VALUES (%s,%s,1,%s,'DEMO')", (pb, pn, self.nd))
            for vai in ('CFO', 'THUC_HIEN_1', 'THUC_HIEN_2', 'TRUONG_PHONG', 'NGUOI_XEM'):
                self.conn.execute('INSERT INTO loi.mtq_dong(id,phien_ban_id,phap_nhan_id,phong_id,vai) VALUES (%s,%s,%s,%s,%s)',
                                  (dong if vai == 'CFO' else uuid4(), pb, pn, phong, vai))
            for hd in ('XEM', 'LAP', 'SUA', 'DUYET'):
                self.conn.execute("INSERT INTO loi.mtq_o(dong_id,module,man,hanh_dong,cho_phep) VALUES (%s,'CRM','TIEP_NHAN',%s,true)", (dong, hd))
            self.conn.execute("UPDATE loi.mtq_phien_ban SET trang_thai='DA_CONG_BO',cong_bo_boi=%s,cong_bo_luc=now(),phien_ban_dong=2 WHERE id=%s", (self.nd, pb))
            self.conn.execute("INSERT INTO loi.mtq_gan_vai(id,nguoi_dung_id,phap_nhan_id,phong_id,vai,cap_boi,ly_do) VALUES (%s,%s,%s,%s,'CFO',%s,'DEMO')", (gan, self.nd, pn, phong, self.nd))
            self.conn.execute("INSERT INTO loi.mtq_pham_vi(gan_vai_id,phap_nhan_id,loai,khoa,cap_boi,ly_do) VALUES (%s,%s,'PHAP_NHAN',%s,%s,'DEMO')", (gan, pn, str(pn), self.nd))
            self.conn.execute('INSERT INTO loi.mtq_kich_hoat(phap_nhan_id,bat,phien_ban_id,bat_boi,bat_luc) VALUES (%s,true,%s,%s,now())', (pn, pb, self.nd))
        self.conn.execute('INSERT INTO mod_crm.doi_tuong(id,tap) VALUES (%s,%s::jsonb)',
            (self.obj, json.dumps([dict(pn=str(self.pn), hop_le=True, loai='TIEP_NHAN', so_tien_vnd='0')])))
        self.conn.execute("INSERT INTO loi.mtq_admin(nguoi_dung_id,cap_boi,ly_do) VALUES (%s,%s,'DEMO')", (self.nd, self.nd))
        ma = self._cap(module='core', hd=['CORE:MODULE:SUA'])
        cong_tac.doi_che_do(self.core, ma=ma, module='crm', phap_nhan_id=self.pn,
            payload=dict(row_version='1', che_do='VAN_HANH', nguoi_thu_ids=[]), request_id=uuid4())
        self.ma = self._cap()
        self.ct = self._contract('crm', ma='demo_'+uuid4().hex[:10])
        self.id = uuid4()
        self._tao()

    def _cap(self, module='crm', hd=None, pn=None):
        return phien.cap_phien(self.core, nguoi_dung_id=self.nd, module=module, phap_nhan_id=pn or self.pn,
            dang_nhap_csdl=self.cac_thong_tin['core']['user'], pham_vi_hanh_dong=hd or [LAP, SUA, XEM, DUYET],
            hieu_luc_den=datetime.now(timezone.utc)+timedelta(minutes=10)).ma

    def _ctx(self, hd=LAP, **doi):
        return {**dict(ma=self.ma, module='crm', phap_nhan_id=self.pn, hanh_dong=hd), **doi}

    def _tao(self):
        return tl.tao(self.core, tai_lieu_id=self.id, thong_tin=dict(loai='DEMO', ten='DEMO',
            doi_tuong=dict(bang='doi_tuong', id=str(self.obj)), phien_ban_contract='1'), request_id=uuid4(), **self._ctx())

    def _tep(self, bien_the='ocr', *, bam=BAM, **doi):
        tep = tl.ghi_tep_da_kiem(self.core, tai_lieu_id=self.id, thong_tin=dict(ten_tep='DEMO.txt', sha256=bam,
            kich_thuoc=4, mime='text/plain', khoa_luu_tru='raw/'+bam, **doi), request_id=uuid4(), **self._ctx())
        tl.gan_bien_the(self.core, tai_lieu_id=self.id, tep_id=tep, bien_the=bien_the, revision_truoc=0,
            request_id=uuid4(), **self._ctx())
        return tep

    def _ket_qua(self, tep=None, *, nguon=None, **doi):
        return tl.ghi_ket_qua_core(self.core, tai_lieu_id=self.id, du_lieu={
            'tep_id': str(tep) if tep else None, 'bien_the': 'ocr', 'ma_contract': self.ct,
            'phien_ban_contract': '1', 'trang_thai': 'thanh_cong', 'ly_do': 'DEMO', 'revision_truoc': 0,
            'nguon': nguon if nguon is not None else ([dict(tep_id=str(tep), sha256=BAM)] if tep else []), **doi},
            thong_tin_core=CORE, request_id=uuid4(), **self._ctx())

    def _lay(self, bien_the='ocr', **doi):
        return tl.lay(self.core, tai_lieu_id=self.id, bien_the=bien_the, **self._ctx(XEM, **doi))

    def _cong_bo(self, kq):
        return tl.cong_bo(self.core, tai_lieu_id=self.id, ket_qua_id=kq, request_id=uuid4(), **self._ctx(DUYET))

    def test_revision_tang_duyet_doc_lap_va_lich_su_bat_bien(self):
        tep = self._tep()
        kq = self._ket_qua(tep)
        self.assertEqual(self._lay()['ket_qua'][0]['trang_thai_duyet'], 'chua_duyet')
        self._cong_bo(kq)
        self.assertEqual(self._lay()['ket_qua'][0]['trang_thai_duyet'], 'chua_duyet')
        tl.duyet(self.core, tai_lieu_id=self.id, ket_qua_id=kq, row_version='1', trang_thai_duyet='da_duyet',
            request_id=uuid4(), **self._ctx(DUYET))
        kq2 = self._ket_qua(tep, goc_id=str(kq), revision_truoc=1)
        ket_qua = self._lay()['ket_qua']
        self.assertEqual([(k['revision'], k['trang_thai_duyet'], k['row_version']) for k in ket_qua],
                         [(1, 'da_duyet', '2'), (2, 'chua_duyet', '1')])
        self.assertNotEqual(kq, kq2)
        with self.assertRaises(tl.LoiTaiLieu) as bat:
            self._ket_qua(tep, goc_id=str(kq), revision_truoc=1)
        self.assertEqual(bat.exception.ma, 'TAI_LIEU_REVISION')

    def test_cung_pn_duoc_sai_pn_phien_va_fk_bi_chan(self):
        self.assertEqual(self._lay()['id'], str(self.id))
        for ctx in ({'phap_nhan_id': self.pn_khac}, {'ma': phien.MaBiMat('GIA'*24)}):
            with self.subTest(ctx=ctx), self.assertRaises(tl.LoiTaiLieu):
                self._lay(**ctx)
        ma = self._cap(pn=self.pn_khac)
        with self.assertRaises(tl.LoiTaiLieu) as bat:
            self._lay(ma=ma, phap_nhan_id=self.pn_khac)
        self.assertEqual(bat.exception.ma, 'TAI_LIEU_KHONG_THAY')
        tep = self._tep()
        id_cu = self.id
        self.id = uuid4()
        self._tao()
        with self.assertRaises(tl.LoiTaiLieu):
            tl.gan_bien_the(self.core, tai_lieu_id=self.id, tep_id=tep, bien_the='goc',
                revision_truoc=0, request_id=uuid4(), **self._ctx())
        self.id = id_cu

        # Tao ho so/tep PN B bang login Core + phien PN B, roi thu gan vao PN A.
        pn_cu, obj_cu, ma_cu = self.pn, self.obj, self.ma
        self.pn, self.obj = self.pn_khac, uuid4()
        self.conn.execute('INSERT INTO mod_crm.doi_tuong(id,tap) VALUES (%s,%s::jsonb)',
            (self.obj, json.dumps([dict(pn=str(self.pn), hop_le=True, loai='TIEP_NHAN', so_tien_vnd='0')])))
        cong_tac.doi_che_do(self.core, ma=self._cap(module='core', hd=['CORE:MODULE:SUA']), module='crm',
            phap_nhan_id=self.pn, payload=dict(row_version='1', che_do='VAN_HANH', nguoi_thu_ids=[]), request_id=uuid4())
        self.ma, self.id = self._cap(), uuid4()
        self._tao()
        tep_khac = self._tep()
        self.pn, self.obj, self.ma, self.id = pn_cu, obj_cu, ma_cu, id_cu
        with self.assertRaises(tl.LoiTaiLieu):
            tl.gan_bien_the(self.core, tai_lieu_id=self.id, tep_id=tep_khac, bien_the='da_che',
                revision_truoc=0, request_id=uuid4(), **self._ctx())

    def test_cong_bo_thieu_tep_hoac_nguon_bi_chan(self):
        # Bo qua Python validator de chung minh CSDL cung tu choi hash thieu.
        with self.assertRaises(psycopg.errors.NotNullViolation):
            self.core.execute('SELECT loi_tai_lieu.ghi_metadata(%s,%s,%s,%s,%s,%s,%s::jsonb,%s)',
                (self.ma.lay_de_truyen(), 'crm', self.pn, LAP, 'tep', self.id,
                 json.dumps(dict(ten_tep='DEMO.txt', kich_thuoc=4, mime='text/plain', khoa_luu_tru='raw/demo')), uuid4()))
        for tep in (None, self._tep()):
            kq = self._ket_qua(tep, nguon=[])
            with self.assertRaises(tl.LoiTaiLieu) as bat:
                self._cong_bo(kq)
            self.assertEqual(bat.exception.ma, 'TAI_LIEU_THIEU_TEP_HASH')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi_tai_lieu.ket_qua_cong_bo WHERE phap_nhan_id=%s', (self.pn,)).fetchone()[0], 0)

    def test_nguon_sai_hash_revision_hoac_tu_tham_chieu_khong_commit_do(self):
        tep = self._tep()
        kq = self._ket_qua(tep)
        for nguon in ([dict(tep_id=str(tep), sha256='b'*64)],
                      [dict(ket_qua_id=str(kq), revision=2, sha256=BAM)],
                      [dict(ket_qua_id=str(uuid4()), revision=1, sha256=BAM)]):
            with self.subTest(nguon=nguon), self.assertRaises(tl.LoiTaiLieu):
                self._ket_qua(tep, nguon=nguon)
        self.assertEqual(len(self._lay()['ket_qua']), 1)
        self._ket_qua(tep, nguon=[dict(ket_qua_id=str(kq), revision=1, sha256=BAM)])

    def test_module_khai_nguon_bi_bac_va_runtime_khong_ghi_thang(self):
        self.assertEqual(self.module.execute('SELECT current_user,session_user').fetchone(), (self.module_login,)*2)
        for kn in (self.core, self.module):
            for bang in BANG:
                with self.subTest(bang=bang, login=kn.info.user), self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    kn.execute(sql.SQL('INSERT INTO loi_tai_lieu.{} DEFAULT VALUES').format(sql.Identifier(bang)))
        goc = self.ma
        uy = phien.cap_phien(self.core, nguoi_dung_id=self.nd, module='crm', phap_nhan_id=self.pn,
            dang_nhap_csdl=self.module_login, pham_vi_hanh_dong=[LAP, XEM], loai='UY_NHIEM_PHIEN', ma_goc=goc,
            hieu_luc_den=datetime.now(timezone.utc)+timedelta(minutes=4)).ma
        with self.assertRaises(tl.LoiTaiLieu):
            tl.ghi_ket_qua_core(self.module, tai_lieu_id=self.id, du_lieu=dict(tep_id=None, bien_the='ocr',
                ma_contract=self.ct, phien_ban_contract='1', trang_thai='thanh_cong', ly_do='GIA',
                revision_truoc=0, nguon=[]), thong_tin_core=CORE, request_id=uuid4(), **self._ctx(ma=uy))
        self.assertEqual(self.module.execute('SELECT loi_tai_lieu.doc_metadata(%s,%s,%s,%s,%s,%s)',
            (uy.lay_de_truyen(), 'crm', self.pn, XEM, self.id, 'ocr')).fetchone()[0]['id'], str(self.id))
        chu_ky = 'loi_tai_lieu.ghi_metadata(text,text,uuid,text,text,uuid,jsonb,uuid,uuid,bigint)'
        # Ke ca provisioning cap nham EXECUTE, cua ghi van chan session_user module.
        self.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION '+chu_ky+' TO {}').format(sql.Identifier(self.module_login)))
        try:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege) as bat:
                self.module.execute('SELECT loi_tai_lieu.ghi_metadata(%s,%s,%s,%s,%s,%s,%s::jsonb,%s)',
                    (uy.lay_de_truyen(), 'crm', self.pn, LAP, 'ket_qua', self.id,
                     json.dumps(dict(engine_id=str(uuid4()), ham='OCR_GIA', nguon=[])), uuid4()))
            self.assertEqual(bat.exception.diag.message_primary, 'TAI_LIEU_CHI_CORE')
        finally:
            self.conn.execute(sql.SQL('REVOKE EXECUTE ON FUNCTION '+chu_ky+' FROM {}').format(sql.Identifier(self.module_login)))

    def test_rls_xac_minh_va_trigger_cam_sua_xoa(self):
        catalog = self.conn.execute('''SELECT relname,relrowsecurity,relforcerowsecurity,
            pg_get_userbyid(relowner) FROM pg_class WHERE relnamespace='loi_tai_lieu'::regnamespace
            AND relname=ANY(%s)''', (list(BANG),)).fetchall()
        self.assertEqual(len(catalog), len(BANG))
        self.assertTrue(all(r[1:] == (True, True, self.tien_to+'vai_doi_cau_truc_loi_tai_lieu') for r in catalog))
        # Owner chỉ dùng để kiểm policy/trigger, không giả runtime nghiệp vụ.
        with self.conn.transaction():
            self.conn.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(self.tien_to+'vai_doi_cau_truc_loi_tai_lieu')))
            self.assertEqual(self.conn.execute('SELECT id FROM loi_tai_lieu.tai_lieu').fetchall(), [])
            for cau in ('UPDATE loi_tai_lieu.tai_lieu SET ten=ten', 'DELETE FROM loi_tai_lieu.tai_lieu',
                        'TRUNCATE loi_tai_lieu.tai_lieu'):
                with self.subTest(cau=cau), self.assertRaises(psycopg.Error), self.conn.transaction():
                    self.conn.execute(cau)

    def test_quyen_bien_the_thu_hoi_va_cas_duyet(self):
        tep = self._tep()
        kq = self._ket_qua(tep)
        for cho_phep, ban in ((False, 0), (True, 1)):
            tl.cap_quyen(self.core, tai_lieu_id=self.id, du_lieu=dict(nguoi_dung_id=str(self.nd), bien_the='ocr',
                cho_phep=cho_phep, revision_truoc=ban), request_id=uuid4(), **self._ctx(DUYET))
            if cho_phep:
                self.assertEqual(len(self._lay()['tep']), 1)
            else:
                with self.assertRaises(tl.LoiTaiLieu) as bat:
                    self._lay()
                self.assertEqual(bat.exception.ma, 'TAI_LIEU_NOI_DUNG')
                self.assertEqual(self._lay('da_che')['tep'], [])
        tl.duyet(self.core, tai_lieu_id=self.id, ket_qua_id=kq, row_version='1',
            trang_thai_duyet='da_duyet', request_id=uuid4(), **self._ctx(DUYET))
        with self.assertRaises(tl.LoiTaiLieu) as bat:
            tl.duyet(self.core, tai_lieu_id=self.id, ket_qua_id=kq, row_version='1',
                trang_thai_duyet='tu_choi', request_id=uuid4(), **self._ctx(DUYET))
        self.assertEqual(bat.exception.ma, 'TAI_LIEU_REVISION')
        self.assertEqual(self._lay()['ket_qua'][0]['row_version'], '2')

    def test_tham_chieu_tep_khong_lo_duong_dan_va_dung_contract(self):
        tep = self._tep()
        tham_chieu = self._lay()['tep'][0]['tham_chieu']
        self.assertEqual(set(tham_chieu), {'contract', 'phien_ban', 'tep_id', 'ten_tep', 'mime', 'kich_thuoc', 'sha256', 'het_han_luc'})
        self.assertEqual(tham_chieu['tep_id'], str(tep))
        self.assertEqual(tham_chieu['sha256'], BAM)
        self.assertIsNone(tham_chieu['het_han_luc'])

    def test_cung_hash_khong_cung_quyen(self):
        self._tep()
        id_cu = self.id
        self.id = uuid4()
        self._tao()
        self._tep()
        tl.cap_quyen(self.core, tai_lieu_id=self.id, du_lieu=dict(nguoi_dung_id=str(self.nd), bien_the='ocr',
            cho_phep=False, revision_truoc=0), request_id=uuid4(), **self._ctx(DUYET))
        with self.assertRaises(tl.LoiTaiLieu) as bat:
            self._lay()
        self.assertEqual(bat.exception.ma, 'TAI_LIEU_NOI_DUNG')
        self.id = id_cu
        self.assertEqual(self._lay()['tep'][0]['tham_chieu']['sha256'], BAM)

    def test_tep_het_han_khong_cong_bo_duoc(self):
        tep = self._tep(het_han_luc=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())
        # Metadata cho luu de phuc hoi, cong bo van phai tu choi.
        kq = self._ket_qua(tep, nguon=[])
        with self.assertRaises(tl.LoiTaiLieu) as bat:
            self._cong_bo(kq)
        self.assertEqual(bat.exception.ma, 'TAI_LIEU_THIEU_TEP_HASH')

    def test_rollback_ket_qua_audit_cung_transaction(self):
        tep = self._tep()
        truoc = self.conn.execute('SELECT count(*) FROM loi.nhat_ky_kiem_toan WHERE phap_nhan_id=%s', (self.pn,)).fetchone()[0]
        with self.assertRaisesRegex(RuntimeError, 'DEMO_ROLLBACK'):
            with self.core.transaction():
                self._ket_qua(tep)
                raise RuntimeError('DEMO_ROLLBACK')
        self.assertEqual(self._lay()['ket_qua'], [])
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.nhat_ky_kiem_toan WHERE phap_nhan_id=%s', (self.pn,)).fetchone()[0], truoc)

    def test_hai_revision_canh_tranh_chi_mot_dat(self):
        tep = self._tep()
        kq = self._ket_qua(tep)
        hen = Barrier(2)

        def ghi(_):
            with psycopg.connect(**self.cac_thong_tin['core'], autocommit=True) as kn:
                hen.wait(timeout=10)
                try:
                    return tl.ghi_ket_qua_core(kn, tai_lieu_id=self.id, du_lieu=dict(tep_id=str(tep),
                        bien_the='ocr', ma_contract=self.ct, phien_ban_contract='1', trang_thai='thanh_cong',
                        ly_do='DEMO', revision_truoc=1, goc_id=str(kq), nguon=[dict(tep_id=str(tep), sha256=BAM)]),
                        thong_tin_core=CORE, request_id=uuid4(), **self._ctx())
                except tl.LoiTaiLieu as exc:
                    return exc.ma

        with ThreadPoolExecutor(max_workers=2) as pool:
            ket_qua = list(pool.map(ghi, range(2)))
        self.assertEqual(ket_qua.count('TAI_LIEU_REVISION'), 1)
        self.assertEqual([k['revision'] for k in self._lay()['ket_qua']], [1, 2])


if __name__ == '__main__':
    unittest.main()
