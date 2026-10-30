"""G2-10: bytes DEMO tạm, mock thuần và PG opt-in bằng runtime login thật.

Không khởi động/dừng dịch vụ, không xóa CSDL/role/tệp. Thư mục tạm và staging
giữ lại cho lead đối chiếu; không đọc cấu hình hoặc dữ liệu thật.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4, UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import tep, ket_qua, tai_lieu, phien, dang_ky
from kho_tri_thuc.ha_tang.primitives import DataError

try:
    from . import test_g2_09 as g209
except ImportError:
    import test_g2_09 as g209


def kho_tam():
    return tep.KhoTep(Path(tempfile.mkdtemp(prefix='kho_g2_10_demo_')) /
                      'var' / 'core-demo' / 'g2_10' / 'kho-file')


class TepThuanTest(unittest.TestCase):
    def setUp(self):
        self.kho = kho_tam()
        self.kn = MagicMock()
        self.kn.info.transaction_status = 2
        self.tai_lieu_id, self.request_id, self.tep_id = (uuid4() for _ in range(3))
        self.ctx = dict(ma=phien.MaBiMat('CANARY_PHIEN'), module='crm',
                        phap_nhan_id=uuid4(), hanh_dong=g209.LAP)
        self.ghi = self.enterContext(patch.object(tai_lieu, 'ghi_tep_da_kiem', return_value=self.tep_id))
        self.gan = self.enterContext(patch.object(tai_lieu, 'gan_bien_the'))
        self.lay = self.enterContext(patch.object(tai_lieu, 'lay', return_value={'tep': [], 'ket_qua': []}))
        self.ref = None

    def upload(self, content=b'DEMO', **doi):
        return self.kho.tai_len(self.kn, **{**dict(luong=io.BytesIO(content), ten='DEMO.txt',
            tai_lieu_id=self.tai_lieu_id, bien_the='goc', revision_truoc=0,
            request_id=self.request_id, **self.ctx), **doi})

    def view(self, ref):
        return {'tep': [dict(so_phien_ban=1, bien_the='goc', tham_chieu=ref)], 'ket_qua': []}

    def doc(self, ref=None, **doi):
        return self.kho.mo_doc(self.kn, tai_lieu_id=self.tai_lieu_id,
            tep_id=(ref or self.ref)['tep_id'], bien_the='goc',
            **{**self.ctx, 'hanh_dong': g209.XEM, **doi})

    def test_hash_bat_bien_va_boc_ham_cu(self):
        with patch.object(tep, 'write_immutable', wraps=tep.write_immutable) as ghi_cu:
            ref = self.upload()
        self.assertGreaterEqual(ghi_cu.call_count, 3)
        self.assertEqual(ref['sha256'], hashlib.sha256(b'DEMO').hexdigest())
        self.assertEqual(set(ref), {'contract', 'phien_ban', 'tep_id', 'ten_tep', 'mime',
                                    'kich_thuoc', 'sha256', 'het_han_luc'})
        with self.assertRaises(DataError):
            self.kho._ghi('raw/' + ref['sha256'], b'GIA')
        self.assertEqual((self.kho.root / 'raw' / ref['sha256']).read_bytes(), b'DEMO')

    def test_cung_hash_tai_su_dung_bytes_nhung_ghi_metadata_rieng(self):
        a = self.upload()
        self.ghi.return_value = uuid4()
        rid_khac = uuid4()
        b = self.upload(request_id=rid_khac, tai_lieu_id=uuid4())
        self.assertEqual(a['sha256'], b['sha256'])
        self.assertNotEqual(a['tep_id'], b['tep_id'])
        self.assertEqual(len(list((self.kho.root / 'raw').glob('[0-9a-f]' * 64))), 1)
        self.assertEqual(self.ghi.call_count, 2)
        self.assertFalse((self.kho.root / 'staging' / str(rid_khac) / 'noi_dung').exists())

    def test_20_mib_duoc_va_them_mot_byte_bi_chan_ngay(self):
        ref = self.upload(b'x' * tep.TOI_DA)
        self.assertEqual(ref['kich_thuoc'], tep.TOI_DA)
        stream = io.BytesIO(b'x' * (tep.TOI_DA + 10))
        with self.assertRaises(tep.LoiTep) as bat:
            self.upload(luong=stream, request_id=uuid4())
        self.assertEqual(bat.exception.ma, 'TEP_QUA_LON')
        self.assertEqual(stream.tell(), tep.TOI_DA + 1)
        self.assertEqual(self.ghi.call_count, 1)

    def test_capability_nho_hon_va_luong_sai(self):
        with self.assertRaises(tep.LoiTep):
            self.upload(b'12345', gioi_han=4)
        for limit in (True, 0, -1, tep.TOI_DA + 1):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.upload(gioi_han=limit)
        with self.assertRaises(ValueError):
            self.upload(luong=io.StringIO('GIA'))
        self.ghi.assert_not_called()

    def test_doc_kiem_quyen_moi_lan_truoc_mo_file(self):
        self.ref = self.upload()
        self.lay.return_value = self.view(self.ref)
        with self.doc() as stream:
            self.assertEqual(stream.read(), b'DEMO')
        self.lay.side_effect = tai_lieu.LoiTaiLieu('TAI_LIEU_NOI_DUNG')
        with patch.object(self.kho, '_doc_kiem') as doc_bytes, self.assertRaises(tai_lieu.LoiTaiLieu):
            self.doc()
        doc_bytes.assert_not_called()
        self.assertEqual(self.lay.call_count, 2)

    def test_id_cung_hash_khong_thuoc_tai_lieu_bi_chan(self):
        self.ref = self.upload()
        self.lay.return_value = self.view({**self.ref, 'tep_id': str(uuid4())})
        with patch.object(self.kho, '_doc_kiem') as doc_bytes, self.assertRaises(tep.LoiTep):
            self.doc()
        doc_bytes.assert_not_called()

    def test_doc_hash_hoac_size_bi_thay_bi_chan(self):
        self.ref = self.upload()
        self.lay.return_value = self.view(self.ref)
        (self.kho.root / 'raw' / self.ref['sha256']).write_bytes(b'GIA!')
        with self.assertRaises(tep.LoiTep) as bat:
            self.doc()
        self.assertEqual(bat.exception.ma, 'TEP_HASH')

    def test_het_han_khong_mo_bytes(self):
        self.ref = self.upload()
        self.lay.return_value = self.view({**self.ref, 'het_han_luc':
            (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()})
        with patch.object(self.kho, '_doc_kiem') as doc_bytes, self.assertRaises(tep.LoiTep) as bat:
            self.doc()
        self.assertEqual(bat.exception.ma, 'TEP_HET_HAN')
        doc_bytes.assert_not_called()

    def test_crash_sau_ghi_staging_phuc_hoi_khong_can_ram_cu(self):
        with patch.object(self.kho, '_ghi_metadata', side_effect=RuntimeError('CRASH')):
            with self.assertRaisesRegex(RuntimeError, 'CRASH'):
                self.upload()
        kho_moi = tep.KhoTep(self.kho.root)
        ref = kho_moi.phuc_hoi(self.kn, request_id=self.request_id, **self.ctx)
        self.assertEqual((self.kho.root / 'raw' / ref['sha256']).read_bytes(), b'DEMO')
        intents = list(self.kho.root.glob('staging/*/y_dinh.json'))
        self.assertEqual(len(intents), 1)
        self.assertNotIn('CANARY', intents[0].read_text(encoding='utf-8'))

    def test_phuc_hoi_sau_commit_khong_nhan_doi_metadata(self):
        ref = self.upload()
        self.lay.return_value = self.view(ref)
        self.ghi.reset_mock()
        self.assertEqual(self.kho.phuc_hoi(self.kn, request_id=self.request_id, **self.ctx), ref)
        self.ghi.assert_not_called()

    def test_crash_sau_kich_hoat_truoc_commit_phuc_hoi_tu_y_dinh(self):
        kich_hoat = self.kho._kich_hoat

        def crash(intent):
            kich_hoat(intent)
            raise RuntimeError('CRASH_TRUOC_COMMIT')

        with patch.object(self.kho, '_kich_hoat', side_effect=crash):
            with self.assertRaisesRegex(RuntimeError, 'CRASH_TRUOC_COMMIT'):
                self.upload()
        self.assertTrue((self.kho.root / 'raw' / hashlib.sha256(b'DEMO').hexdigest()).exists())
        # Mock metadata trống tương ứng transaction bị rollback khi crash.
        kho_moi = tep.KhoTep(self.kho.root)
        ref = kho_moi.phuc_hoi(self.kn, request_id=self.request_id, **self.ctx)
        self.lay.return_value = self.view(ref)
        with kho_moi.mo_doc(self.kn, tai_lieu_id=self.tai_lieu_id, tep_id=ref['tep_id'],
                bien_the='goc', **{**self.ctx, 'hanh_dong': g209.XEM}) as stream:
            self.assertEqual(stream.read(), b'DEMO')

    def test_phuc_hoi_khong_nhan_nham_tep_cung_hash_khac_han(self):
        han = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        ref = self.upload(het_han_luc=han)
        self.lay.return_value = self.view({**ref, 'het_han_luc': None})
        with self.assertRaises(tep.LoiTep) as bat:
            self.kho.phuc_hoi(self.kn, request_id=self.request_id, **self.ctx)
        self.assertEqual(bat.exception.ma, 'TEP_XUNG_DOT_PHUC_HOI')

    def test_phuc_hoi_xung_dot_hoac_sai_pn_khong_ghi(self):
        ref = self.upload()
        self.lay.return_value = self.view({**ref, 'sha256': 'f' * 64})
        self.ghi.reset_mock()
        with self.assertRaises(tep.LoiTep):
            self.kho.phuc_hoi(self.kn, request_id=self.request_id, **self.ctx)
        with self.assertRaises(tep.LoiTep):
            self.kho.phuc_hoi(self.kn, request_id=self.request_id,
                             **{**self.ctx, 'phap_nhan_id': uuid4()})
        self.ghi.assert_not_called()

    def test_cung_request_khac_bytes_bi_chan_khong_ghi_de(self):
        ref = self.upload()
        with self.assertRaises(DataError):
            self.upload(b'GIA')
        self.assertEqual((self.kho.root / 'raw' / ref['sha256']).read_bytes(), b'DEMO')
        self.assertEqual(self.ghi.call_count, 1)

    def test_mime_thuc_ten_an_toan_va_khong_nhan_path(self):
        ref = self.upload(b'%PDF-1.7\nDEMO', ten='GIA.txt')
        self.assertEqual(ref['mime'], 'application/pdf')
        for name in ('../GIA', 'C:\\GIA', 'a\r\nX: y', '', '..', 'a\x00b'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.upload(ten=name)
        with self.assertRaises(TypeError):
            self.upload(mime='application/pdf')

    def test_chi_dich_demo_va_khong_traversal(self):
        for path in ('D:/DU-LIEU-KE-TOAN/var/core-demo/g2_10/kho-file',
                     'var/plhn-that/var/core-demo/g2_10/kho-file',
                     'var/web-that/var/core-demo/g2_10/kho-file',
                     '.env/var/core-demo/g2_10/kho-file',
                     'var/core-demo/g2_10/kho-tep', 'var/core-demo/../kho-file'):
            with self.subTest(path=path), self.assertRaises(tep.LoiTep):
                tep.KhoTep(path)
        with self.assertRaises((tep.LoiTep, DataError)):
            self.kho._path('../../../../GIA')

    def test_symlink_bi_chan(self):
        link = self.kho.root / 'raw'
        target = self.kho.root / 'ngoai'
        target.mkdir()
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest('CHUA_KIEM symlink: Windows không cấp quyền tạo link')
        with self.assertRaises((tep.LoiTep, DataError)):
            self.upload()

    def test_khong_tu_commit_va_tu_choi_ket_noi_idle(self):
        self.upload()
        self.kn.commit.assert_not_called()
        self.kn.rollback.assert_not_called()
        self.kn.info.transaction_status = 0
        with self.assertRaises(tep.LoiTep):
            self.upload(request_id=uuid4())


class KetQuaThuanTest(unittest.TestCase):
    def setUp(self):
        self.kn = MagicMock()
        self.kn.info.transaction_status = 2
        self.ctx = dict(ma=phien.MaBiMat('CANARY'), module='crm', phap_nhan_id=uuid4(), hanh_dong=g209.LAP)
        self.source = ket_qua.NguonCore('crm', self.ctx['phap_nhan_id'], '1', uuid4(), 'demo.tao', '1',
                                       uuid4(), 3, uuid4(), uuid4())
        self.xac_minh = MagicMock(return_value=self.source)
        self.kho = MagicMock()
        self.kho.tai_len.return_value = dict(tep_id=str(uuid4()))
        self.svc = ket_qua.BanGiaoKetQua(self.kho, xac_minh_core=self.xac_minh)
        self.ghi = self.enterContext(patch.object(tai_lieu, 'ghi_ket_qua_core', return_value=uuid4()))
        self.data = dict(bien_the='ocr', ma_contract='demo.v1', phien_ban_contract='1',
            trang_thai='thanh_cong', ly_do='DEMO', revision_truoc=0,
            nguon=[dict(tep_id=str(uuid4()), sha256=hashlib.sha256(b'DEMO').hexdigest())])
        self.handle = object()
        self.tid = uuid4()

    def ghi_kq(self, **doi):
        return self.svc.ghi(self.kn, **{**dict(giu_viec=self.handle, tai_lieu_id=self.tid,
            luong=io.BytesIO(b'DEMO'), ten='DEMO.txt', du_lieu=self.data, revision_tep_truoc=0,
            request_id=uuid4(), het_han_luc=None, **self.ctx), **doi})

    def test_nguon_core_va_viec_tu_handle_khong_tu_payload(self):
        ref = self.ghi_kq()
        self.assertFalse(ref['da_ban_giao'])
        self.xac_minh.assert_called_once_with(self.kn, self.handle)
        call = self.ghi.call_args.kwargs
        self.assertEqual(call['thong_tin_core']['engine_id'], self.source.engine_id)
        self.assertEqual(call['thong_tin_core']['phien_ban_ham'], '1')
        self.assertEqual(call['viec_id'], self.source.viec_id)
        self.assertEqual(call['the_he'], 3)
        self.assertEqual(call['du_lieu']['tep_id'], self.kho.tai_len.return_value['tep_id'])
        self.kn.commit.assert_not_called()

    def test_engine_khong_tu_khai_provenance_hoac_trang_thai_duyet(self):
        for key in ('engine_id', 'ham', 'phien_ban_ham', 'phien_ban_module', 'actor',
                    'viec_id', 'buoc_id', 'lan_thu_id', 'tep_id', 'trang_thai_duyet'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.ghi_kq(du_lieu={**self.data, key: 'GIA'})
        self.xac_minh.assert_not_called()
        self.kho.tai_len.assert_not_called()

    def test_sai_instance_lease_hoac_scope_bi_chan_truoc_bytes(self):
        for source in (None, {}, replace(self.source, module='m2'),
                       replace(self.source, phap_nhan_id=uuid4()), replace(self.source, the_he=True)):
            self.xac_minh.return_value = source
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.ghi_kq()
        self.kho.tai_len.assert_not_called()

    def test_khong_cho_gia_viec_qua_ctx(self):
        with self.assertRaises(ValueError):
            self.ghi_kq(viec_id=uuid4(), the_he=1)
        self.kho.tai_len.assert_not_called()

    def test_ack_chi_sau_commit_va_kiem_lai_bytes_quyen(self):
        kid, fid = str(uuid4()), str(uuid4())
        self.kn.autocommit = True
        self.kn.info.transaction_status = 0
        with patch.object(tai_lieu, 'lay', return_value={'ket_qua': [dict(id=kid, tep_id=fid)]}):
            ack = self.svc.xac_nhan_da_commit(self.kn, tai_lieu_id=self.tid, ket_qua_id=kid,
                bien_the='ocr', **{**self.ctx, 'hanh_dong': g209.XEM})
        self.assertTrue(ack['da_ban_giao'])
        self.kho.mo_doc.assert_called_once()
        self.kn.info.transaction_status = 2
        with self.assertRaises(tep.LoiTep):
            self.svc.xac_nhan_da_commit(self.kn, tai_lieu_id=self.tid, ket_qua_id=kid,
                bien_the='ocr', **{**self.ctx, 'hanh_dong': g209.XEM})

    def test_ack_khong_thay_hoac_thu_hoi_khong_giai_phong_ram(self):
        self.kn.autocommit = True
        self.kn.info.transaction_status = 0
        with patch.object(tai_lieu, 'lay', return_value={'ket_qua': []}), self.assertRaises(tep.LoiTep):
            self.svc.xac_nhan_da_commit(self.kn, tai_lieu_id=self.tid, ket_qua_id=uuid4(),
                bien_the='ocr', **{**self.ctx, 'hanh_dong': g209.XEM})
        self.kho.mo_doc.assert_not_called()


@unittest.skipUnless(g209.psycopg is not None and os.environ.get('KHO_PG_DSN_TEST'),
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class TepPostgresTest(unittest.TestCase):
    # Dùng lại provisioning kho_test_* 001..009; nghiệp vụ chỉ dùng self.core.
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

    def setUp(self):
        g209.TaiLieuPostgresTest.setUp(self)
        self.kho = kho_tam()
        self.request_id = uuid4()
        self.assertEqual(self.core.execute('SELECT current_user,session_user').fetchone(),
                         (self.cac_thong_tin['core']['user'],) * 2)

    def upload(self, content=b'DEMO', **doi):
        with self.core.transaction():
            return self.kho.tai_len(self.core, **{**dict(luong=io.BytesIO(content), ten='DEMO.txt',
                tai_lieu_id=self.tai_lieu_id, bien_the='goc', revision_truoc=0,
                request_id=self.request_id, **self._ctx()), **doi})

    def doc(self, ref, **doi):
        return self.kho.mo_doc(self.core, tai_lieu_id=self.tai_lieu_id, tep_id=ref['tep_id'],
            bien_the='goc', **self._ctx(g209.XEM, **doi))

    def test_hash_bat_bien_cung_hash_khac_quyen(self):
        a = self.upload()
        id_cu = self.tai_lieu_id
        self.tai_lieu_id = uuid4()
        self._tao()
        b = self.upload(request_id=uuid4())
        self.assertEqual(a['sha256'], b['sha256'])
        self.assertNotEqual(a['tep_id'], b['tep_id'])
        self.assertEqual(len(list((self.kho.root / 'raw').glob('[0-9a-f]' * 64))), 1)
        tai_lieu.cap_quyen(self.core, tai_lieu_id=self.tai_lieu_id,
            du_lieu=dict(nguoi_dung_id=str(self.nd), bien_the='goc', cho_phep=False, revision_truoc=0),
            request_id=uuid4(), **self._ctx(g209.DUYET))
        with self.assertRaises(tai_lieu.LoiTaiLieu):
            self.doc(b)
        self.tai_lieu_id = id_cu
        with self.doc(a) as stream:
            self.assertEqual(stream.read(), b'DEMO')
        with self.assertRaises(DataError):
            self.kho._ghi('raw/' + a['sha256'], b'GIA')

    def test_20_mib_cong_1_khong_metadata(self):
        with self.assertRaises(tep.LoiTep):
            self.upload(b'x' * (tep.TOI_DA + 1))
        view = tai_lieu.lay(self.core, tai_lieu_id=self.tai_lieu_id, bien_the='goc', **self._ctx(g209.XEM))
        self.assertEqual(view['tep'], [])

    def test_doc_sai_phien_phap_nhan_hoac_id_bi_chan(self):
        ref = self.upload()
        for doi in ({'ma': phien.MaBiMat('GIA' * 24)}, {'phap_nhan_id': self.pn_khac}):
            with self.subTest(doi=doi), self.assertRaises(tai_lieu.LoiTaiLieu):
                self.doc(ref, **doi)
        with self.assertRaises(tep.LoiTep):
            self.doc({**ref, 'tep_id': str(uuid4())})

    def test_crash_sau_ghi_file_truoc_commit_phuc_hoi(self):
        with self.assertRaisesRegex(RuntimeError, 'CRASH'):
            with self.core.transaction():
                ref = self.upload()
                self.assertTrue((self.kho.root / 'raw' / ref['sha256']).is_file())
                raise RuntimeError('CRASH')
        self.assertEqual(tai_lieu.lay(self.core, tai_lieu_id=self.tai_lieu_id, bien_the='goc',
                                     **self._ctx(g209.XEM))['tep'], [])
        kho_moi = tep.KhoTep(self.kho.root)
        with self.core.transaction():
            ref = kho_moi.phuc_hoi(self.core, request_id=self.request_id, **self._ctx())
        with self.doc(ref) as stream:
            self.assertEqual(stream.read(), b'DEMO')
        with self.core.transaction():
            replay = kho_moi.phuc_hoi(self.core, request_id=self.request_id, **self._ctx())
        self.assertEqual(ref, replay)
        self.assertEqual(len(tai_lieu.lay(self.core, tai_lieu_id=self.tai_lieu_id, bien_the='goc',
                                        **self._ctx(g209.XEM))['tep']), 1)

    def test_loi_gan_bien_the_rollback_ca_metadata(self):
        self.upload()
        with self.assertRaises(tai_lieu.LoiTaiLieu):
            self.upload(b'KHAC', request_id=uuid4())  # CAS 0 đã cũ.
        count = self.conn.execute('SELECT count(*) FROM loi_tai_lieu.tep_goc WHERE tai_lieu_id=%s',
                                  (self.tai_lieu_id,)).fetchone()[0]
        self.assertEqual(count, 1)

    def test_nguon_core_va_ack_truoc_sau_commit(self):
        ref_vao = self.upload()
        engine_ma = 'demo_' + uuid4().hex[:8]
        self._ghi('engine', ma=engine_ma, ten='DEMO', so_phien_ban='1', ma_bam_goi=g209.BAM,
            adapter={'ma': 'demo', 'phien_ban': '1'},
            capability=[dict(ma='demo.tao@1', dau_vao='tham_chieu_tep.v1', dau_ra=self.ct)], gioi_han={})
        engine = dang_ky.doc_dang_ky(self.core, loai='engine', ma=engine_ma)[0]
        source = ket_qua.NguonCore('crm', self.pn, '1', UUID(engine['id']), 'demo.tao', '1',
                                    uuid4(), 1, uuid4(), uuid4())
        ma_viec = phien.cap_phien(self.core, nguoi_dung_id=self.nd, module='crm', phap_nhan_id=self.pn,
            dang_nhap_csdl=self.cac_thong_tin['core']['user'], pham_vi_hanh_dong=[g209.LAP, g209.XEM],
            hieu_luc_den=datetime.now(timezone.utc)+timedelta(minutes=10), loai='UY_NHIEM_VIEC',
            viec_id=source.viec_id, the_he=1).ma
        svc = ket_qua.BanGiaoKetQua(self.kho, xac_minh_core=lambda conn, handle: source)
        reader = g209.psycopg.connect(**self.cac_thong_tin['core'], autocommit=True)
        self.addCleanup(reader.close)
        with self.core.transaction():
            kq = svc.ghi(self.core, giu_viec=object(), tai_lieu_id=self.tai_lieu_id,
                luong=io.BytesIO(b'KET QUA'), ten='DEMO.txt', du_lieu=dict(bien_the='ocr',
                    ma_contract=self.ct, phien_ban_contract='1', trang_thai='thanh_cong', ly_do='DEMO',
                    revision_truoc=0, nguon=[dict(tep_id=ref_vao['tep_id'], sha256=ref_vao['sha256'])]),
                revision_tep_truoc=0, request_id=uuid4(), het_han_luc=None, **self._ctx(ma=ma_viec))
            self.assertFalse(kq['da_ban_giao'])
            with self.assertRaises(tep.LoiTep):
                svc.xac_nhan_da_commit(self.core, tai_lieu_id=self.tai_lieu_id,
                    ket_qua_id=kq['ket_qua_id'], bien_the='ocr', **self._ctx(g209.XEM))
            with self.assertRaises(tep.LoiTep):
                svc.xac_nhan_da_commit(reader, tai_lieu_id=self.tai_lieu_id,
                    ket_qua_id=kq['ket_qua_id'], bien_the='ocr', **self._ctx(g209.XEM))
        ack = svc.xac_nhan_da_commit(reader, tai_lieu_id=self.tai_lieu_id,
            ket_qua_id=kq['ket_qua_id'], bien_the='ocr', **self._ctx(g209.XEM))
        self.assertTrue(ack['da_ban_giao'])
        # Owner chỉ đọc bằng chứng fixture; ghi nghiệp vụ ở trên dùng Core login.
        row = self.conn.execute('''SELECT engine_id,ham,phien_ban_ham,viec_id,buoc_id,lan_thu_id,the_he
            FROM loi_tai_lieu.ket_qua_xu_ly WHERE id=%s''', (kq['ket_qua_id'],)).fetchone()
        self.assertEqual(row, (source.engine_id, source.ham, '1', source.viec_id,
                               source.buoc_id, source.lan_thu_id, 1))


if __name__ == '__main__':
    unittest.main()
