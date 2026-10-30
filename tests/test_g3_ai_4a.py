"""AI-4a: provider/Core giả; bootstrap/listener/Windows Job/tiến trình thật.

Wire DEMO là seam test; child cấm mọi connect/DNS, chỉ accept loopback Core.
Không model Local, Cloud, Mask, bí mật hoặc CSDL thật.
"""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import tien_trinh as tt
from kho_tri_thuc.core.phien import MaBiMat
from kho_tri_thuc.core.viec import GiuViec
from kho_tri_thuc.engines.e_hoi_ai import chay as ai
from kho_tri_thuc.engines.e_hoi_ai.dto import KetQuaAI, TruongAI, YeuCauAI
from kho_tri_thuc.sdk_core import bootstrap as bs
from kho_tri_thuc.sdk_core.engine import KenhCore, LoiEngine, SDKEngine

try:
    from .test_g2_21 import SoGia, _dong
except ImportError:
    from test_g2_21 import SoGia, _dong


VAN_BAN = 'DEMO hóa đơn 0001: 1.234.567 đồng; 31/10/2026'
YEU_CAU = YeuCauAI('DEMO', VAN_BAN, 'Echo DEMO', ('noi_dung',))
METADATA = dict(bien_the='ai_demo', ma_contract='khung_ai_demo',
    phien_ban_contract='1', trang_thai='DEMO', ly_do=None,
    revision_truoc=0, nguon=[])


def _lease():
    return GiuViec(viec_id=uuid4(), buoc_viec_id=uuid4(), lan_thu_id=uuid4(),
        phap_nhan_id=uuid4(), module='demo', hanh_dong='DEMO:AI:LAP',
        instance_id=uuid4(), the_he=1,
        giu_den=datetime.now(timezone.utc) + timedelta(minutes=2),
        ma=MaBiMat('n' * 43))


class KenhGia(KenhCore):
    def __init__(self, conn=None, giu=False):
        self.conn, self.giu = conn, giu
        self.da_goi = []
        self.raw = None

    def goi(self, operation, giu_viec, **payload):
        self.da_goi.append(operation)
        if operation == 'doc_dau_vao':
            return dict(yeu_cau_demo=YEU_CAU, du_lieu_ket_qua=dict(METADATA),
                        revision_tep_truoc=0)
        if operation != 'ghi_ket_qua':
            raise AssertionError('Operation ngoài test')
        self.raw = payload['luong'].read()
        assert payload['du_lieu'] == METADATA
        assert payload['revision_tep_truoc'] == 0
        assert payload['ten'] == 'ai-demo.json'
        if self.conn is not None:
            if self.giu:
                self.conn.sendall(b'cho_core\n')
                assert self.conn.recv(32) == b'core_da_nhan\n'
            self.conn.sendall(self.raw + b'\n')
        return {'ket_qua_id': 'DEMO_DA_NHAN'}


def _cam_mang(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo', 'socket.gethostbyname'):
        raise AssertionError('AI-4a không được kết nối mạng/DNS')


def _child():
    sys.addaudithook(_cam_mang)

    def nhan_viec(conn, bo_doc):
        # Chỉ lease DEMO sau marker test; runtime không bỏ kiểm chữ ký thật.
        raw = conn.recv(64)
        assert raw in (b'DEMO_AI4A\n', b'DEMO_AI4A_GIU\n')
        return SDKEngine(_lease(), kenh_core=KenhGia(conn, raw.endswith(b'_GIU\n')))

    def khong_nhan_the(sig, msg):
        raise ValueError('Test này không cấp thẻ request')

    ai.chay(kiem_chu_ky=khong_nhan_the, nhan_viec=nhan_viec)


class AIThuanTest(unittest.TestCase):
    def test_provider_gia_dung_dto_giu_unicode_tien_ngay(self):
        provider = ai.ProviderAIGia()
        self.assertTrue(provider.san_sang())
        with patch('socket.socket', side_effect=AssertionError('Mạng')), \
                patch('subprocess.Popen', side_effect=AssertionError('Local thật')):
            kq = provider.goi(YEU_CAU)
        self.assertIsInstance(kq, KetQuaAI)
        self.assertIsInstance(kq.truong['noi_dung'], TruongAI)
        self.assertEqual(kq.truong['noi_dung'].gia_tri, VAN_BAN)
        self.assertEqual(kq.truong['noi_dung'].trich_dan, VAN_BAN)
        self.assertEqual((kq.muc, kq.ly_do), ('VANG', ('GIA_LAP',)))
        for value in (None, b'bytes', 123, 'x' * 16385):
            with self.subTest(value=type(value)), self.assertRaises(ValueError):
                provider.goi(replace(YEU_CAU, van_ban=value))
        with self.assertRaises(TypeError):
            provider.goi({})

    def test_viec_chi_doc_va_ban_giao_qua_sdk_core(self):
        kenh = KenhGia()
        kq = ai.xu_ly_viec(SDKEngine(_lease(), kenh_core=kenh),
                          provider=ai.ProviderAIGia())
        self.assertEqual(kenh.da_goi, ['doc_dau_vao', 'ghi_ket_qua'])
        self.assertEqual(json.loads(kenh.raw)['truong']['noi_dung']['gia_tri'], VAN_BAN)
        self.assertEqual(kq, {'ket_qua_id': 'DEMO_DA_NHAN'})

    def test_mat_lease_khong_goi_provider_hoac_ban_giao(self):
        lease = replace(_lease(), giu_den=datetime.now(timezone.utc) - timedelta(seconds=1))
        kenh, provider = KenhGia(), MagicMock()
        with self.assertRaisesRegex(LoiEngine, 'VIEC_MAT_LEASE'):
            ai.xu_ly_viec(SDKEngine(lease, kenh_core=kenh), provider=provider)
        self.assertEqual(kenh.da_goi, [])
        provider.goi.assert_not_called()

    def test_seam_phai_cap_sdk_engine_va_provider_tra_dto(self):
        with self.assertRaises(TypeError):
            ai.xu_ly_viec(object(), provider=ai.ProviderAIGia())
        kenh = KenhGia()
        with self.assertRaises(TypeError):
            ai.xu_ly_viec(SDKEngine(_lease(), kenh_core=kenh),
                          provider=MagicMock(goi=lambda _: {}))
        self.assertEqual(kenh.da_goi, ['doc_dau_vao'])

    def test_preflight_chua_dat_khong_ready_khong_worker(self):
        b = bs.Bootstrap()
        b.socket, b.bo_doc = MagicMock(), MagicMock()
        b._duoc_accept, b._ra = False, io.BytesIO()
        provider = MagicMock()
        provider.san_sang.return_value = False
        with patch.object(ai.Bootstrap, 'nhan', return_value=b), \
                patch.object(ai._VongNhan, 'bat_dau') as start:
            with self.assertRaisesRegex(bs.LoiBootstrap, 'CHUA_SAN_SANG'):
                ai.chay(kiem_chu_ky=lambda *_: None, nhan_viec=lambda *_: None,
                        provider=provider)
        start.assert_not_called()
        provider.goi.assert_not_called()
        b.socket.close.assert_called_once()
        self.assertEqual(b._ra.getvalue(), b'')

    def test_loi_ban_giao_khong_bao_drain_thanh_cong_khong_ro_noi_dung(self):
        b, conn = bs.Bootstrap(), MagicMock()
        b.socket, b.bo_doc = MagicMock(), MagicMock()
        b._duoc_accept = True
        b._vao = io.BytesIO(b'{"protocol":"ktt.bootstrap.v1","kieu":"thu_hoi"}\n')
        b._ra = io.BytesIO()
        conn.__enter__.return_value = conn
        b.socket.accept.return_value = (conn, ('127.0.0.1', 1))
        kenh = KenhGia()
        goi = kenh.goi
        loi = RuntimeError('AI4A_CANARY')
        da_ban_giao = threading.Event()

        def ban_giao(operation, giu, **payload):
            if operation == 'ghi_ket_qua':
                kenh.da_goi.append(operation)
                da_ban_giao.set()
                raise loi
            return goi(operation, giu, **payload)

        kenh.goi = ban_giao
        cho_thu_hoi = b.cho_thu_hoi

        def thu_hoi(**callbacks):
            self.assertTrue(da_ban_giao.wait(2))
            return cho_thu_hoi(**callbacks)

        with patch.object(ai.Bootstrap, 'nhan', return_value=b), \
                patch.object(b, 'bao_san_sang'), \
                patch.object(b, 'cho_thu_hoi', side_effect=thu_hoi):
            with self.assertRaisesRegex(bs.LoiBootstrap, 'DRAIN_CHUA_XONG'):
                ai.chay(kiem_chu_ky=lambda *_: None,
                        nhan_viec=lambda *_: SDKEngine(_lease(), kenh_core=kenh))
        self.assertEqual(kenh.da_goi, ['doc_dau_vao', 'ghi_ket_qua'])
        conn.__exit__.assert_called_once()
        b.socket.close.assert_not_called()
        self.assertEqual(b._ra.getvalue(), b'')
        self.assertNotIn('AI4A_CANARY', repr(loi))

    def test_import_khong_khoi_dong_local_hay_mang(self):
        code = '''
import sys
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
with patch('socket.socket', side_effect=AssertionError('Không mở socket')), \\
     patch('socket.getaddrinfo', side_effect=AssertionError('Không DNS')), \\
     patch('subprocess.Popen', side_effect=AssertionError('Không chạy Local')), \\
     patch('threading.Thread.start', side_effect=AssertionError('Không worker')):
    from kho_tri_thuc.engines.e_hoi_ai import chay
'''
        p = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code,
                            str(Path(__file__).resolve().parents[1] / 'src')],
                           capture_output=True, timeout=15, env=tt.env_con())
        self.assertEqual(p.returncode, 0, p.stderr.decode('utf-8', errors='replace'))


@unittest.skipUnless(os.name == 'nt' and hasattr(socket.socket, 'share'),
                     'CHUA_KIEM: cần Windows share/fromshare và Job')
class AITienTrinhTest(unittest.TestCase):
    def setUp(self):
        self.controllers = []
        self.addCleanup(self._dong)

    def _dong(self):
        for c in self.controllers:
            if c._proc is not None:
                try:
                    c.thu_hoi(timeout=5)
                except tt.LoiTienTrinh:
                    c._job.ket_thuc()  # Chỉ Job test sở hữu.
                    c._proc.wait(5)
                    c.kiem_con()
            c.dong()

    def _tao(self, cong=None):
        if cong is None:
            with socket.socket() as tam:
                tam.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                tam.bind(('127.0.0.1', 0))
                cong = tam.getsockname()[1]
        d = _dong()
        d.update(module=None, engine_ho_so_id=str(uuid4()), cong=cong)
        so = SoGia(d)
        c = tt.TienTrinhCore(so_cong_id=d['id'], giao_dich=so.giao_dich,
            lenh=[sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()), '--child'],
            phien_ban=ai.PHIEN_BAN, issuer='core-demo', contracts=[], ma_chu='e_hoi_ai',
            cho_khoi_dong=10, cho_dung=0.2)
        self.controllers.append(c)
        return c, so

    def _ket_noi(self, so):
        conn = socket.create_connection(('127.0.0.1', so.dong['cong']), timeout=3)
        self.addCleanup(conn.close)
        return conn

    def _kiem_ket_qua(self, reader):
        kq = json.loads(reader.readline())
        self.assertEqual(kq['ly_do'], ['GIA_LAP'])
        self.assertEqual(kq['truong']['noi_dung']['gia_tri'], VAN_BAN)

    def test_khoi_dong_job_ready_viec_gia_va_drain_cung_listener(self):
        c, so = self._tao()
        c.khoi_dong()
        proc, job = c._proc, c._job
        self.assertEqual((c.trang_thai, c.chu_accept), ('ready', 'con'))
        self.assertGreaterEqual(job.so_tien_trinh(), 1)
        self.assertEqual(so.dong['trang_thai'], 'CON_GIU')
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'CORE_KHONG_CO_QUYEN_ACCEPT'):
            c.accept()
        with self._ket_noi(so) as conn:
            conn.sendall(b'DEMO_AI4A\n')
            with conn.makefile('rb') as reader:
                self._kiem_ket_qua(reader)
        self.assertTrue(c.thu_hoi(timeout=5))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual((c.chu_accept, so.dong['trang_thai']), ('core', 'TRONG'))
        with self._ket_noi(so):
            accepted, _ = c.accept(timeout=3)
            accepted.close()

    def test_drain_cho_core_ack_sau_6_giay_khong_kill_khong_nhan_viec_moi(self):
        c, so = self._tao()
        c.khoi_dong()
        proc, job = c._proc, c._job
        conn = self._ket_noi(so)
        conn.sendall(b'DEMO_AI4A_GIU\n')
        reader = conn.makefile('rb')
        self.addCleanup(reader.close)
        self.assertEqual(reader.readline(), b'cho_core\n')
        bat_dau_cho = time.monotonic()
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'DUNG_CHUA_XAC_NHAN'):
            c.thu_hoi(timeout=0.05)
        self.assertIsNone(proc.poll())
        self.assertGreaterEqual(job.so_tien_trinh(), 1)
        self.assertEqual((c.trang_thai, c.chu_accept), ('dang_dung', 'con'))
        self.assertNotIn('tra', [ten for ten, _ in so.go])
        moi = self._ket_noi(so)
        moi.sendall(b'DEMO_AI4A\n')
        moi.settimeout(0.1)
        with self.assertRaises(socket.timeout):
            moi.recv(1024)
        time.sleep(max(0, 6 - (time.monotonic() - bat_dau_cho)))
        self.assertIsNone(proc.poll())
        self.assertGreaterEqual(job.so_tien_trinh(), 1)
        self.assertEqual((c.trang_thai, c.chu_accept), ('dang_dung', 'con'))
        self.assertNotIn('tra', [ten for ten, _ in so.go])
        conn.sendall(b'core_da_nhan\n')
        self._kiem_ket_qua(reader)
        proc.wait(5)
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(c.kiem_con())
        self.assertEqual(so.dong['trang_thai'], 'TRONG')

    def test_ranh_thu_hoi_va_restart_doi_nonce_giu_cong(self):
        c, so = self._tao()
        c.khoi_dong()
        nonce, instance, listener = c._nonce, c.instance_id, c._nghe
        self.assertTrue(c.thu_hoi(timeout=5))
        c.khoi_dong()
        self.assertEqual(c.the_he, 2)
        self.assertNotEqual(c._nonce, nonce)
        self.assertNotEqual(c.instance_id, instance)
        self.assertIs(c._nghe, listener)
        with self._ket_noi(so) as conn:
            conn.sendall(b'DEMO_AI4A\n')
            with conn.makefile('rb') as reader:
                self._kiem_ket_qua(reader)
        self.assertTrue(c.thu_hoi(timeout=5))

    def test_version_hoac_capability_sai_khong_ready(self):
        for truong, value in (('_phien_ban', 'KHAC_BAN_RUNTIME'),
                              ('_contracts', ['ai.hoi@1'])):
            with self.subTest(truong=truong):
                c, so = self._tao()
                setattr(c, truong, value)
                with self.assertRaisesRegex(tt.LoiTienTrinh, 'TIEN_TRINH_KHONG_HOP_LE'):
                    c.khoi_dong()
                self.assertEqual(so.dong['trang_thai'], 'LOI')
                self.assertNotIn('san_sang', [ten for ten, _ in so.go])

    def test_cong_bi_chiem_khong_doi_cong_khong_dung_chu_listener(self):
        with socket.socket() as la:
            la.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            la.bind(('127.0.0.1', 0))
            la.listen()
            c, so = self._tao(la.getsockname()[1])
            with self.assertRaisesRegex(tt.LoiTienTrinh, 'CONG_BI_CHIEM'):
                c.khoi_dong()
            self.assertEqual(so.dong['ma_loi'], 'CONG_BI_CHIEM')
            with self._ket_noi(so):
                accepted, _ = la.accept()
                accepted.close()


if __name__ == '__main__':
    if '--child' in sys.argv:
        _child()
    else:
        unittest.main()
