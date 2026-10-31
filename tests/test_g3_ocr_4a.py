"""OCR-4a: Core/việc/OCR giả; bootstrap/socket/Windows Job/tiến trình thật.

Wire DEMO dưới đây chỉ là seam của test, không phải API/capability engine.
Không PostgreSQL, ABBYY, tài khoản riêng, nguồn OCR hoặc dịch vụ bên ngoài.
"""

from datetime import datetime, timedelta, timezone
import io
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
from kho_tri_thuc.engines.e_ocr import chay as ocr
from kho_tri_thuc.sdk_core import bootstrap as bs
from kho_tri_thuc.sdk_core.engine import KenhCore, LoiEngine, SDKEngine

try:
    from .test_g2_21 import SoGia, _dong
except ImportError:
    from test_g2_21 import SoGia, _dong


VAN_BAN = 'DEMO hóa đơn 0001: 1.234.567 đồng; 31/10/2026'
METADATA = dict(bien_the='ocr_demo', ma_contract='khung_ocr_demo',
    phien_ban_contract='1', trang_thai='DEMO', ly_do=None,
    revision_truoc=0, nguon=[])


def _lease():
    return GiuViec(viec_id=uuid4(), buoc_viec_id=uuid4(), lan_thu_id=uuid4(),
        phap_nhan_id=uuid4(), module='demo', hanh_dong='DEMO:OCR:LAP',
        instance_id=uuid4(), the_he=1,
        giu_den=datetime.now(timezone.utc) + timedelta(minutes=2),
        ma=MaBiMat('n' * 43))


class KenhGia(KenhCore):
    def __init__(self, conn=None, giu=False, loi_lan_dau=False):
        self.conn, self.giu = conn, giu
        self.loi_lan_dau = loi_lan_dau
        self.luong = None
        self.da_goi = []
        self.raw = None

    def goi(self, operation, giu_viec, **payload):
        self.da_goi.append(operation)
        if operation == 'doc_dau_vao':
            return dict(van_ban_demo=VAN_BAN, du_lieu_ket_qua=dict(METADATA),
                        revision_tep_truoc=0)
        if operation != 'ghi_ket_qua':
            raise AssertionError('Operation ngoài test')
        self.raw = payload['luong'].read()
        assert payload['du_lieu'] == METADATA
        assert payload['revision_tep_truoc'] == 0
        if self.conn is not None:
            if self.loi_lan_dau:
                self.luong = payload['luong']
                self.loi_lan_dau = False
                self.conn.sendall(b'loi_ban_giao\n')
                raise RuntimeError('OCR4A_CANARY')
            if self.luong is not None:
                assert payload['luong'] is self.luong and not self.luong.closed
                assert self.raw == VAN_BAN.encode('utf-8')
                self.conn.sendall(b'thu_lai\n')
            if self.giu:
                self.conn.sendall(b'cho_core\n')
                assert self.conn.recv(32) == b'core_da_nhan\n'
            self.conn.sendall(self.raw + b'\n')
        return {'ket_qua_id': 'DEMO_DA_NHAN'}


def _child():
    def nhan_viec(conn, bo_doc):
        # Không triển khai IPC thật hoặc bỏ kiểm chữ ký trong mã runtime.
        # Test chỉ cấp một lease giả sau marker DEMO cố định.
        raw = conn.recv(64)
        assert raw in (b'DEMO_OCR4A\n', b'DEMO_OCR4A_GIU\n', b'DEMO_OCR4A_LOI\n')
        loi = raw == b'DEMO_OCR4A_LOI\n'
        return SDKEngine(_lease(), kenh_core=KenhGia(conn,
            giu=loi or raw.endswith(b'_GIU\n'), loi_lan_dau=loi))

    def khong_nhan_the(sig, msg):
        raise ValueError('Test này không cấp thẻ request')

    ocr.chay(kiem_chu_ky=khong_nhan_the, nhan_viec=nhan_viec)


class OCRThuanTest(unittest.TestCase):
    def test_backend_gia_bao_toan_unicode_tien_ngay(self):
        backend = ocr.BackendOCRGia()
        self.assertTrue(backend.san_sang())
        self.assertEqual(backend.xu_ly(VAN_BAN).decode('utf-8'), VAN_BAN)
        for value in (None, b'bytes', 123, 'x' * 16385):
            with self.subTest(value=type(value)), self.assertRaises(ValueError):
                backend.xu_ly(value)

    def test_viec_chi_doc_va_ban_giao_qua_sdk_core(self):
        kenh = KenhGia()
        kq = ocr.xu_ly_viec(SDKEngine(_lease(), kenh_core=kenh),
                           backend=ocr.BackendOCRGia())
        self.assertEqual(kenh.da_goi, ['doc_dau_vao', 'ghi_ket_qua'])
        self.assertEqual(kenh.raw, VAN_BAN.encode('utf-8'))
        self.assertEqual(kq, {'ket_qua_id': 'DEMO_DA_NHAN'})

    def test_mat_lease_khong_chay_backend_hoac_ban_giao(self):
        from dataclasses import replace
        lease = replace(_lease(), giu_den=datetime.now(timezone.utc) - timedelta(seconds=1))
        kenh, backend = KenhGia(), MagicMock()
        with self.assertRaisesRegex(LoiEngine, 'VIEC_MAT_LEASE'):
            ocr.xu_ly_viec(SDKEngine(lease, kenh_core=kenh), backend=backend)
        self.assertEqual(kenh.da_goi, [])
        backend.xu_ly.assert_not_called()

    def test_seam_phai_cap_sdk_engine(self):
        with self.assertRaises(TypeError):
            ocr.xu_ly_viec(object(), backend=ocr.BackendOCRGia())

    def test_preflight_chua_dat_khong_worker_khong_capability(self):
        b = bs.Bootstrap()
        b.socket, b.bo_doc = MagicMock(), MagicMock()
        b._duoc_accept, b._ra = False, io.BytesIO()
        backend = MagicMock()
        backend.san_sang.return_value = False
        with patch.object(ocr.Bootstrap, 'nhan', return_value=b), \
                patch.object(ocr._VongNhan, 'bat_dau') as start:
            with self.assertRaisesRegex(bs.LoiBootstrap, 'CHUA_SAN_SANG'):
                ocr.chay(kiem_chu_ky=lambda *_: None, nhan_viec=lambda *_: None,
                         backend=backend)
        start.assert_not_called()
        b.socket.close.assert_called_once()
        self.assertEqual(b._ra.getvalue(), b'')

    def test_retry_giu_cung_luong_tua_lai_va_chi_dong_sau_ack(self):
        loi = RuntimeError('OCR4A_CANARY')
        kenh = KenhGia()
        goi = kenh.goi
        da_loi, cho_ack, ack = (threading.Event() for _ in range(3))
        cac_luong, ket_qua = [], []
        def ghi_loi(operation, *args, **payload):
            if operation == 'ghi_ket_qua':
                cac_luong.append(payload['luong'])
                if len(cac_luong) == 1:
                    self.assertEqual(payload['luong'].read(), VAN_BAN.encode('utf-8'))
                    da_loi.set()
                    raise loi
                cho_ack.set()
                if not ack.wait(3):
                    raise TimeoutError()
            return goi(operation, *args, **payload)
        kenh.goi = ghi_loi
        backend = MagicMock(wraps=ocr.BackendOCRGia())
        luong = threading.Thread(target=lambda: ket_qua.append(ocr.xu_ly_viec(
            SDKEngine(_lease(), kenh_core=kenh), backend=backend)))
        luong.start()
        try:
            self.assertTrue(da_loi.wait(2))
            self.assertTrue(cho_ack.wait(2))
            self.assertTrue(luong.is_alive())
            self.assertEqual(ket_qua, [])
            self.assertIs(cac_luong[0], cac_luong[1])
            self.assertFalse(cac_luong[0].closed)
        finally:
            ack.set()
            luong.join(3)
        self.assertFalse(luong.is_alive())
        self.assertEqual(ket_qua, [{'ket_qua_id': 'DEMO_DA_NHAN'}])
        self.assertEqual(kenh.raw, VAN_BAN.encode('utf-8'))
        self.assertTrue(cac_luong[0].closed)
        backend.xu_ly.assert_called_once_with(VAN_BAN)
        self.assertNotIn('OCR4A_CANARY', repr(loi))


@unittest.skipUnless(os.name == 'nt' and hasattr(socket.socket, 'share'),
                     'CHUA_KIEM: cần Windows share/fromshare và Job')
class OCRTienTrinhTest(unittest.TestCase):
    def setUp(self):
        self.controllers = []
        self.addCleanup(self._dong)

    def _dong(self):
        for c in self.controllers:
            if c._proc is not None:
                try:
                    c.thu_hoi(timeout=5)
                except tt.LoiTienTrinh:
                    # Chỉ Job test sở hữu; không PID/dịch vụ bên ngoài.
                    c._job.ket_thuc()
                    c._proc.wait(5)
                    c.kiem_con()
            c.dong()

    def _tao(self, cong=None, **doi):
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
            phien_ban=ocr.PHIEN_BAN, issuer='core-demo', contracts=[], ma_chu='e_ocr',
            cho_khoi_dong=10, cho_dung=0.2, **doi)
        self.controllers.append(c)
        return c, so

    def _ket_noi(self, so):
        conn = socket.create_connection(('127.0.0.1', so.dong['cong']), timeout=3)
        self.addCleanup(conn.close)
        return conn

    def test_khoi_dong_job_ready_viec_gia_va_drain_cung_listener(self):
        c, so = self._tao()
        c.khoi_dong()
        proc, job = c._proc, c._job
        self.assertEqual((c.trang_thai, c.chu_accept), ('ready', 'con'))
        # Python launcher có thể tạo thêm tiến trình Python bên trong Job.
        self.assertGreaterEqual(job.so_tien_trinh(), 1)
        self.assertEqual(so.dong['trang_thai'], 'CON_GIU')
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'CORE_KHONG_CO_QUYEN_ACCEPT'):
            c.accept()
        with self._ket_noi(so) as conn:
            conn.sendall(b'DEMO_OCR4A\n')
            with conn.makefile('rb') as reader:
                self.assertEqual(reader.readline(), VAN_BAN.encode('utf-8') + b'\n')
        self.assertTrue(c.thu_hoi(timeout=5))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual((c.chu_accept, so.dong['trang_thai']), ('core', 'TRONG'))
        # Core vẫn sở hữu listener cùng cổng sau khi con và Job kết thúc.
        with self._ket_noi(so):
            accepted, _ = c.accept(timeout=3)
            accepted.close()

    def test_drain_cho_core_xac_nhan_khong_kill_khong_nhan_viec_moi(self):
        c, so = self._tao()
        c.khoi_dong()
        proc, job = c._proc, c._job
        conn = self._ket_noi(so)
        conn.sendall(b'DEMO_OCR4A_GIU\n')
        reader = conn.makefile('rb')
        self.addCleanup(reader.close)
        self.assertEqual(reader.readline(), b'cho_core\n')
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'DUNG_CHUA_XAC_NHAN'):
            c.thu_hoi(timeout=0.05)
        # ACK chậm hơn timeout 5 giây cũ: entrypoint vẫn giữ kết nối/Job.
        time.sleep(6)
        self.assertIsNone(proc.poll())
        self.assertGreaterEqual(job.so_tien_trinh(), 1)
        self.assertEqual((c.trang_thai, c.chu_accept), ('dang_dung', 'con'))
        self.assertNotIn('tra', [ten for ten, _ in so.go])
        # Listener vẫn giữ ở Core; kết nối này chỉ được xếp backlog.
        moi = self._ket_noi(so)
        moi.sendall(b'DEMO_OCR4A\n')
        moi.settimeout(0.1)
        with self.assertRaises(socket.timeout):
            moi.recv(1024)
        conn.sendall(b'core_da_nhan\n')
        self.assertEqual(reader.readline(), VAN_BAN.encode('utf-8') + b'\n')
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
            conn.sendall(b'DEMO_OCR4A\n')
            with conn.makefile('rb') as reader:
                self.assertEqual(reader.readline(), VAN_BAN.encode('utf-8') + b'\n')
        self.assertTrue(c.thu_hoi(timeout=5))

    def test_loi_truoc_ack_tien_trinh_song_retry_roi_drain_dat(self):
        c, so = self._tao()
        c.khoi_dong()
        proc, job = c._proc, c._job
        conn = self._ket_noi(so)
        conn.sendall(b'DEMO_OCR4A_LOI\n')
        reader = conn.makefile('rb')
        self.addCleanup(reader.close)
        self.assertEqual(reader.readline(), b'loi_ban_giao\n')
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'DUNG_CHUA_XAC_NHAN'):
            c.thu_hoi(timeout=0.05)
        status = tt._doc_dong(proc.stdout, 3)
        self.assertIsNotNone(status)
        self.assertEqual(bs.doc_thong_diep(status),
            {'protocol': bs.PROTOCOL, 'kieu': 'drain_chua_xong'})
        self.assertEqual(reader.readline(), b'thu_lai\n')
        self.assertEqual(reader.readline(), b'cho_core\n')
        self.assertIsNone(proc.poll())
        self.assertGreaterEqual(job.so_tien_trinh(), 1)
        self.assertEqual((c.trang_thai, c.chu_accept), ('dang_dung', 'con'))
        self.assertNotIn('tra', [ten for ten, _ in so.go])
        moi = self._ket_noi(so)
        moi.sendall(b'DEMO_OCR4A\n')
        moi.settimeout(0.1)
        with self.assertRaises(socket.timeout):
            moi.recv(1024)
        conn.sendall(b'core_da_nhan\n')
        self.assertEqual(reader.readline(), VAN_BAN.encode('utf-8') + b'\n')
        self.assertEqual(bs.doc_thong_diep(tt._doc_dong(proc.stdout, 3)),
            {'protocol': bs.PROTOCOL, 'kieu': 'da_thu_hoi'})
        proc.wait(5)
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(c.kiem_con())
        self.assertEqual(so.dong['trang_thai'], 'TRONG')

    def test_version_sai_khong_ready(self):
        c, so = self._tao()
        c._phien_ban = 'KHAC_BAN_RUNTIME'
        self._kiem_ba_lan_loi_khoi_dong(c, so, 'TIEN_TRINH_KHONG_HOP_LE')
        self.assertNotIn('san_sang', [ten for ten, _ in so.go])

    def _kiem_ba_lan_loi_khoi_dong(self, c, so, ma_loi):
        for lan, giay in ((1, 2), (2, 4), (3, None)):
            truoc = datetime.now(timezone.utc)
            ma = ma_loi if lan < 3 else 'KHOI_DONG_BI_KHOA'
            with self.assertRaisesRegex(tt.LoiTienTrinh, ma):
                c.khoi_dong()
            sau = datetime.now(timezone.utc)
            self.assertEqual(so.dong['so_loi_khoi_dong'], lan)
            self.assertEqual(so.dong['trang_thai'], 'LOI' if lan == 3 else 'CORE_GIU')
            self.assertEqual(so.dong['ma_loi'], ma_loi if lan == 3 else None)
            self.assertEqual(so.dong['ma_loi_khoi_dong'], ma_loi)
            if giay is not None:
                han = datetime.fromisoformat(so.dong['thu_lai_sau'])
                self.assertGreaterEqual(han, truoc + timedelta(seconds=giay))
                self.assertLessEqual(han, sau + timedelta(seconds=giay))
                with patch.object(tt, 'datetime', wraps=datetime) as dong_ho:
                    dong_ho.now.return_value = han - timedelta(seconds=giay)
                    with self.assertRaisesRegex(tt.LoiTienTrinh, 'KHOI_DONG_LOI') as bat:
                        c.khoi_dong()
                self.assertEqual(bat.exception.headers, {'Retry-After': str(giay)})
                self.assertEqual(so.dong['so_loi_khoi_dong'], lan)
                # Cho hết hạn trong fixture, giữ nguyên counter và mã lỗi.
                so.dong['thu_lai_sau'] = (truoc - timedelta(seconds=1)).isoformat()
            else:
                self.assertIsNone(so.dong['thu_lai_sau'])
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'KHOI_DONG_BI_KHOA'):
            c.khoi_dong()
        self.assertEqual(so.dong['so_loi_khoi_dong'], 3)

    def test_cong_bi_chiem_khong_doi_cong_khong_dung_chu_listener(self):
        with socket.socket() as la:
            la.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            la.bind(('127.0.0.1', 0))
            la.listen()
            cong = la.getsockname()[1]
            c, so = self._tao(cong)
            self._kiem_ba_lan_loi_khoi_dong(c, so, 'CONG_BI_CHIEM')
            self.assertEqual((so.dong['cong'], so.dong['ma_loi']), (cong, 'CONG_BI_CHIEM'))
            with self._ket_noi(so):
                accepted, _ = la.accept()
                accepted.close()


if __name__ == '__main__':
    if '--child' in sys.argv:
        _child()
    else:
        unittest.main()
