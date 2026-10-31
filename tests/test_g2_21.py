"""G2-21: mock/thuần + Python con loopback Windows + PG opt-in.

Không tài khoản/ACL/dịch vụ thật; không xóa tệp hoặc CSDL. --child chỉ là
runtime DEMO nhận mọi tham số qua stdin, không mở dữ liệu người dùng.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
from threading import Event
import time
import traceback
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import so_cong as sc, tien_trinh as tt
from kho_tri_thuc.sdk_core import bootstrap as bs
from kho_tri_thuc.sdk_core.ngu_canh import NhanRequest

try:
    from . import test_g2_16 as g216
except ImportError:
    import test_g2_16 as g216


def _child():
    b = bs.Bootstrap.nhan(kiem_chu_ky=lambda sig, msg: None)
    # Kiểm canary môi trường trong runtime thật, trả kết quả qua socket đã chuyển.
    assert 'KHO_G221_CANARY' not in os.environ
    assert 'PGPASSWORD' not in os.environ
    assert all('G221_SECRET' not in arg for arg in sys.argv)
    assert isinstance(b.bo_doc, NhanRequest)
    assert b.bo_doc._nonce_khoi_dong == b._cfg['nonce_khoi_dong']
    if b.tham_so.get('sai'):
        b._cfg[b.tham_so['sai']] = b.tham_so['gia_tri']
    b.bao_san_sang(phien_ban=b.tham_so.get('version', '1'), contracts=['demo/v1'],
                   kiem_san_sang=lambda: True)
    if b.tham_so.get('stdout_lon'):
        print('x' * (256 * 1024), flush=True)
        os.write(sys.stdout.fileno(), b'y' * (256 * 1024))
    if b.tham_so.get('chet'):
        return
    if b.tham_so.get('echo'):
        conn, _ = b.accept()
        with conn:
            assert conn.recv(100) == b'ping'
            conn.sendall(str(os.getpid()).encode('ascii'))
    b.cho_thu_hoi(ngung_accept=lambda: None,
                  drain=lambda: (time.sleep(b.tham_so.get('drain_giay', 0)) or True))


def _dong(**doi):
    return dict(id=str(uuid4()), may_chu_id=str(uuid4()), module='demo',
                engine_ho_so_id=None, dia_chi_nghe='127.0.0.1', cong=19121,
                the_he=0, giu_boi=None, trang_thai='TRONG', **doi)


class SoGia:
    """Giả driver sổ cổng, vẫn đi qua wrapper và transaction thật của controller."""

    def __init__(self, dong=None):
        self.dong = dong or _dong()
        self.info = MagicMock(transaction_status=2)
        self.go = []
        self.trong_tx = False
        self.so_commit = 0
        self.phien = None

    @contextmanager
    def giao_dich(self):
        assert not self.trong_tx
        self.trong_tx = True
        try:
            yield self
            self.so_commit += 1
        finally:
            self.trong_tx = False

    def execute(self, cau, ts):
        assert self.trong_tx
        ten = cau.split('loi.so_cong_', 1)[1].split('(', 1)[0]
        self.go.append((ten, ts))
        d = self.dong
        if ten == 'nhan':
            assert d['the_he'] == ts[2] and d['giu_boi'] is None
            d.update(the_he=d['the_he'] + 1, giu_boi=str(ts[1]), trang_thai='CORE_GIU')
            self.phien = dict(id=str(ts[1]), the_he=d['the_he'], pid=ts[4],
                              dinh_danh_lan_tao=ts[5], ten_job=None)
        if ten == 'ghi_job':
            self.phien['ten_job'] = ts[3]
        if ten == 'doc_phien':
            return MagicMock(fetchone=lambda: (deepcopy(self.phien),))
        if ten == 'doi_chieu':
            assert (d['giu_boi'], d['the_he']) == (str(ts[1]), ts[2])
            assert ts[3] is not None
            d.update(giu_boi=None, trang_thai='LOI' if d['trang_thai']=='LOI' else 'TRONG')
        if ten in ('san_sang', 'xac_nhan_accept', 'tra', 'loi_khoi_dong', 'gia_han'):
            assert (d['giu_boi'], d['the_he']) == (str(ts[1]), ts[2])
        if ten == 'san_sang':
            d.update(trang_thai='CON_GIU')
        if ten == 'xac_nhan_accept':
            assert d['trang_thai'] == 'CON_GIU'
            d.update(so_loi_khoi_dong=0, thu_lai_sau=None, ma_loi_khoi_dong=None)
        if ten == 'tra':
            d.update(trang_thai='TRONG', giu_boi=None)
        if ten in ('loi_khoi_dong', 'loi_chua_nhan'):
            n = d.get('so_loi_khoi_dong', 0) + 1
            d.update(trang_thai='LOI' if n == 3 else ('CORE_GIU' if ten=='loi_khoi_dong' else 'TRONG'),
                     ma_loi=ts[-1] if n == 3 else None, ma_loi_khoi_dong=ts[-1],
                     so_loi_khoi_dong=n, thu_lai_sau=(datetime.now(timezone.utc)
                     + timedelta(seconds=n*2)).isoformat() if n<3 else None)
        return MagicMock(fetchone=lambda: (deepcopy(d),))


def _control(so, **doi):
    return tt.TienTrinhCore(so_cong_id=so.dong['id'], giao_dich=so.giao_dich,
        lenh=[sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()), '--child'],
        phien_ban='1', issuer='core-demo', contracts=['demo/v1'], **doi)


class TienTrinhThuanTest(unittest.TestCase):
    def setUp(self):
        self.so = SoGia()
        self.proc = MagicMock(pid=12345)
        self.proc.poll.return_value = None
        self.proc.stdin = io.BytesIO()
        self.job = MagicMock()
        self.job.so_tien_trinh.return_value = 0
        self.nghe = MagicMock()
        self.nghe.share.return_value = b'DEMO_SHARE'
        self.spawn = MagicMock(return_value=self.proc)
        self.c = _control(self.so, popen=self.spawn, job_factory=lambda: self.job,
            doc_lan_tao=lambda p: 'CREATE_DEMO', socket_factory=lambda *a: self.nghe,
            doc_dong=self._ready, cho_dung=0.1)
        # Dọn mock không spawn/kill gì; kiểm riêng việc tái dùng cleanup của host.
        self.don = patch.object(tt.Trich6Host, '_don', self._don_mock)
        self.don.start()
        self.addCleanup(self.don.stop)
        self.addCleanup(self._dong)

    def _dong(self):
        self.proc.poll.return_value = 0
        if self.c._proc is not None:
            self.c.kiem_con()
        self.c.dong()

    def _don_mock(self, don, proc, job):
        if proc is not None:
            self.proc.poll.return_value = 0

    def _ready(self, stream, han):
        assert not self.so.trong_tx and self.so.so_commit >= 2
        assert self.c.chu_accept == 'con'
        self.job.gan.assert_called_once_with(self.proc)
        cfg = json.loads(self.proc.stdin.getvalue().splitlines()[0])
        self.cfg = cfg
        return (json.dumps({**cfg, 'kieu': 'san_sang', 'contracts': ['demo/v1'],
                            'san_sang': True}) + '\n').encode('ascii')

    def test_ban_giao_co_dinh_doc_so_cas_ready_va_chan_accept_core(self):
        self.c.khoi_dong()
        self.assertEqual([t for t, _ in self.so.go], ['doc', 'nhan', 'san_sang', 'xac_nhan_accept'])
        self.assertEqual(self.so.dong['trang_thai'], 'CON_GIU')
        self.assertEqual((self.c.trang_thai, self.c.chu_accept), ('ready', 'con'))
        self.nghe.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        self.nghe.bind.assert_called_once_with(('127.0.0.1', 19121))
        self.nghe.share.assert_called_once_with(self.proc.pid)
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'CORE_KHONG_CO_QUYEN_ACCEPT'):
            self.c.accept()
        self.nghe.accept.assert_not_called()
        self.assertEqual(json.loads(self.proc.stdin.getvalue().splitlines()[1])['kieu'], 'nhan_accept')

    def test_tham_so_chi_tren_stdin_sau_job_khong_args_env_repr(self):
        self.c._tham_so = {'credential': 'G221_SECRET'}
        with patch.dict(os.environ, {'PGPASSWORD': 'G221_SECRET', 'KHO_G221_CANARY': 'G221_SECRET'}):
            self.c.khoi_dong()
        args, kwargs = self.spawn.call_args
        self.assertNotIn('G221_SECRET', repr(args) + repr(kwargs) + repr(self.c))
        self.assertFalse(kwargs['shell'])
        self.assertTrue(kwargs['close_fds'])
        self.assertIs(kwargs['stderr'], subprocess.DEVNULL)
        self.assertIn(b'G221_SECRET', self.proc.stdin.getvalue())

    def test_readiness_sai_tung_danh_tinh_khong_ghi_ready(self):
        for ten, sai in (('pid', 99), ('pid', True), ('dinh_danh_lan_tao', 'PID_TAI_SU_DUNG'),
                ('nonce_khoi_dong', 'x'*43), ('phien_ban', '2'), ('instance_id', str(uuid4())),
                ('module', 'khac'), ('contracts', []), ('cong', 19122), ('the_he', 2),
                ('san_sang', False)):
            with self.subTest(ten=ten, sai=sai):
                self.c.instance_id, self.c.the_he = uuid4(), 1
                self.c._module, self.c._nonce, self.c._lan_tao = 'demo', 'n'*43, 'CREATE_DEMO'
                self.c._proc = self.proc
                hs = dict(protocol=bs.PROTOCOL, kieu='san_sang', san_sang=True, module='demo',
                    instance_id=str(self.c.instance_id), the_he=1, pid=12345, cong=19121,
                    dinh_danh_lan_tao='CREATE_DEMO', nonce_khoi_dong='n'*43,
                    phien_ban='1', contracts=['demo/v1'])
                hs[ten] = sai
                with self.assertRaisesRegex(tt.LoiTienTrinh, 'TIEN_TRINH_KHONG_HOP_LE'):
                    self.c._kiem_san_sang(hs, self.so.dong)
                self.c._proc = None
        self.assertFalse(self.so.go)

    def test_os_lan_tao_thay_doi_bi_tu_choi_va_khoa_loi(self):
        self.c._doc_lan_tao = MagicMock(side_effect=['CREATE_DEMO', 'TAI_SU_DUNG'])
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'TIEN_TRINH_KHONG_HOP_LE'):
            self.c.khoi_dong()
        self.assertEqual((self.so.dong['trang_thai'], self.so.dong['so_loi_khoi_dong']),
                         ('CORE_GIU', 1))
        self.assertNotIn('san_sang', [t for t, _ in self.so.go])

    def test_bind_bi_chiem_khong_doi_cong_khong_diet_ung_dung_la(self):
        self.nghe.bind.side_effect = OSError('CANARY OS message')
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'CONG_BI_CHIEM') as bat:
            self.c.khoi_dong()
        self.assertEqual(self.nghe.bind.call_count, 1)
        self.assertEqual(self.so.dong['cong'], 19121)
        self.assertEqual(self.so.dong['ma_loi_khoi_dong'], 'CONG_BI_CHIEM')
        loi = next(ts for t, ts in self.so.go if t == 'loi_khoi_dong')
        self.assertEqual(loi[1:3], (self.c.instance_id, 1))
        self.nghe.share.assert_not_called()
        self.assertIsNone(bat.exception.__context__)
        self.assertNotIn('CANARY', ''.join(traceback.format_exception(bat.exception)))

    def test_loi_ben_vung_va_chu_cu_chua_doi_chieu_khong_spawn(self):
        for doi, ma in (({'trang_thai': 'LOI'}, 'KHOI_DONG_BI_KHOA'),
                        ({'giu_boi': str(uuid4())}, 'CONG_CAN_DOI_CHIEU')):
            with self.subTest(ma=ma):
                self.so.dong.update(trang_thai='TRONG', giu_boi=None)
                self.so.dong.update(doi)
                with self.assertRaisesRegex(tt.LoiTienTrinh, ma):
                    self.c.khoi_dong()
        self.spawn.assert_not_called()

    def test_hai_request_cung_mot_khoi_dong(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            ds = list(pool.map(lambda _: self.c.khoi_dong(), range(2)))
        self.assertEqual(ds[0], ds[1])
        self.spawn.assert_called_once()
        khac = _control(self.so)
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'CONG_CAN_DOI_CHIEU'):
            khac.khoi_dong()

    def test_con_chet_tra_dung_the_he_giu_socket_restart_nonce_moi(self):
        self.c.khoi_dong()
        nonce_cu, instance_cu = self.c._nonce, self.c.instance_id
        self.proc.poll.return_value = 0
        self.assertTrue(self.c.kiem_con())
        self.assertEqual(self.so.go[-1][0], 'tra')
        self.assertEqual(self.so.dong['trang_thai'], 'TRONG')
        self.nghe.close.assert_not_called()
        self.assertEqual(self.c.chu_accept, 'core')
        self.proc.stdin = io.BytesIO()
        self.proc.poll.return_value = None
        self.job.reset_mock()
        self.c.khoi_dong()
        self.assertNotEqual((self.c._nonce, self.c.instance_id), (nonce_cu, instance_cu))
        self.assertEqual(self.c.the_he, 2)
        self.nghe.bind.assert_called_once()

    def test_drain_qua_han_khong_kill_tra_hoac_chuyen_accept(self):
        self.c.khoi_dong()
        self.proc.wait.side_effect = subprocess.TimeoutExpired('demo', 0.01)
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'DUNG_CHUA_XAC_NHAN'):
            self.c.thu_hoi(timeout=0.01)
        self.assertEqual((self.c.trang_thai, self.c.chu_accept), ('dang_dung', 'con'))
        self.assertNotIn('tra', [t for t, _ in self.so.go])
        self.job.ket_thuc.assert_not_called()
        self.proc.kill.assert_not_called()
        self.nghe.close.assert_not_called()
        self.proc.poll.return_value = 0
        self.c.kiem_con()
        self.assertEqual(self.c.trang_thai, 'stopped')

    def _kiem_mat_lease(self, thu_hoi):
        proc, job = self.c._proc, self.c._job
        def tra_loi(*args):
            # Lỗi thật xảy ra trước khi sổ thay đổi; quyền trong máy phải đã thu.
            self.assertIsNone(self.c._proc)
            self.assertIsNone(self.c._job)
            self.assertEqual((self.c.trang_thai, self.c.chu_accept), ('stopped', 'core'))
            job.dong.assert_called_once()
            self.assertTrue(proc.stdin.closed)
            self.assertTrue(self.c._nonce is None and not self.c._da_nhan)
            raise sc.LoiSoCong('CONG_MAT_LEASE')
        with patch.object(sc, 'tra', side_effect=tra_loi):
            with self.assertRaisesRegex(tt.LoiTienTrinh, 'CONG_MAT_LEASE') as bat:
                thu_hoi()
        self.assertEqual(bat.exception.ma, 'CONG_MAT_LEASE')
        self.assertIsNone(bat.exception.__context__)
        self.nghe.close.assert_not_called()
        self.c.accept()
        self.assertFalse(self.c.kiem_con())
        self.assertTrue(self.c.thu_hoi())
        # G2-22: bằng chứng PID terminal + Job rỗng được đối chiếu qua CAS/audit.
        d = self.c.doi_chieu()
        self.assertEqual(d['trang_thai'], 'TRONG')
        self.assertIsNotNone(next(ts[3] for t, ts in self.so.go if t == 'doi_chieu'))
        self.assertEqual(self.spawn.call_count, 1)
        self.proc.stdin = io.BytesIO()
        self.proc.poll.return_value = None
        self.job.reset_mock()
        self.c.khoi_dong()
        self.assertEqual((self.c.trang_thai, self.c.the_he), ('ready', 2))
        self.nghe.bind.assert_called_once()

    def test_lease_het_khi_con_chet_khong_ket_controller(self):
        self.c.khoi_dong()
        self.proc.poll.return_value = 0
        self._kiem_mat_lease(self.c.kiem_con)

    def test_lease_het_trong_drain_khong_ket_controller(self):
        self.c.khoi_dong()
        def dung(*args):
            self.assertEqual(self.c.trang_thai, 'dang_dung')
            self.proc.poll.return_value = 0
        self.proc.wait.side_effect = dung
        self._kiem_mat_lease(lambda: self.c.thu_hoi(timeout=0.1))

    def test_loi_transaction_tra_khong_pha_thu_hoi_noi_bo(self):
        self.c.khoi_dong()
        self.proc.poll.return_value = 0
        with patch.object(sc, 'tra', side_effect=RuntimeError('G221_SECRET')):
            with self.assertRaisesRegex(tt.LoiTienTrinh, 'CONG_THAT_BAI') as bat:
                self.c.kiem_con()
        self.assertIsNone(self.c._proc)
        self.assertEqual(self.c.chu_accept, 'core')
        self.assertNotIn('G221_SECRET', ''.join(traceback.format_exception(bat.exception)))

    def test_don_loi_giua_chung_giu_job_de_kiem_con_thu_lai(self):
        self.don.stop()  # Dùng cleanup host thật, chỉ giả các thao tác OS.
        self.c._doc_dong = lambda *_: None
        def dung(*args):
            self.proc.poll.return_value = 0
        self.proc.wait.side_effect = dung
        self.job.so_tien_trinh.side_effect = [
            tt.LoiHost('JOB_TRUY_VAN_LOI', 'G221_SECRET'), 0]
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'DUNG_CHUA_XAC_NHAN'):
            self.c.khoi_dong()
        self.assertIs(self.c._proc, self.proc)
        self.assertIs(self.c._job, self.job)
        self.job.dong.assert_not_called()
        self.assertEqual(self.c.chu_accept, 'con')
        self.assertTrue(self.c.kiem_con())
        self.job.dong.assert_called_once()
        self.assertIsNone(self.c._proc)
        self.assertIsNone(self.c._job)
        self.assertEqual(self.c.chu_accept, 'core')

    def test_kiem_con_loi_job_tra_loi_tien_trinh_co_ma(self):
        self.c.khoi_dong()
        self.proc.poll.return_value = 0
        with patch.object(self.job, 'so_tien_trinh', side_effect=
                          tt.LoiHost('JOB_TRUY_VAN_LOI', 'G221_SECRET')):
            with self.assertRaisesRegex(tt.LoiTienTrinh, 'JOB_TRUY_VAN_LOI') as bat:
                self.c.kiem_con()
        self.assertEqual(bat.exception.ma, 'JOB_TRUY_VAN_LOI')
        self.assertIsNone(bat.exception.__context__)
        self.assertNotIn('G221_SECRET', ''.join(traceback.format_exception(bat.exception)))
        self.assertIs(self.c._proc, self.proc)
        self.job.dong.assert_not_called()
        self.assertEqual(self.c.chu_accept, 'con')
        self.assertTrue(self.c.kiem_con())

    def test_con_chet_nhung_job_con_worker_khong_thu_hoi(self):
        self.c.khoi_dong()
        self.proc.poll.return_value = 0
        self.job.so_tien_trinh.return_value = 1
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'DUNG_CHUA_XAC_NHAN'):
            self.c.kiem_con()
        self.assertEqual(self.c.chu_accept, 'con')
        self.assertNotIn('tra', [t for t, _ in self.so.go])
        self.job.so_tien_trinh.return_value = 0

    def test_qua_han_bat_tay_khoa_loi(self):
        self.c._doc_dong = lambda *_: None
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'KHOI_DONG_QUA_HAN'):
            self.c.khoi_dong()
        self.assertEqual(self.so.dong['ma_loi_khoi_dong'], 'KHOI_DONG_QUA_HAN')

    def test_loi_lan_1_2_gian_2_4_giay_lan_3_moi_khoa(self):
        self.c._doc_dong = lambda *_: None
        for n, giay in ((1, 2), (2, 4), (3, None)):
            self.proc.poll.return_value = None
            self.proc.stdin = io.BytesIO()
            truoc = datetime.now(timezone.utc)
            ma = 'KHOI_DONG_QUA_HAN' if n < 3 else 'KHOI_DONG_BI_KHOA'
            with self.assertRaisesRegex(tt.LoiTienTrinh, ma):
                self.c.khoi_dong()
            self.assertEqual(self.so.dong['so_loi_khoi_dong'], n)
            self.assertEqual(self.so.dong['trang_thai'], 'LOI' if n == 3 else 'CORE_GIU')
            if giay:
                han = datetime.fromisoformat(self.so.dong['thu_lai_sau'])
                self.assertGreaterEqual((han-truoc).total_seconds(), giay)
                self.assertLess((han-truoc).total_seconds(), giay+0.5)
                with self.assertRaisesRegex(tt.LoiTienTrinh, 'KHOI_DONG_LOI') as bat:
                    self.c.khoi_dong()
                self.assertEqual(bat.exception.headers, {'Retry-After': str(giay)})
                self.assertEqual(self.spawn.call_count, n)
                self.so.dong['thu_lai_sau'] = (truoc-timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'KHOI_DONG_BI_KHOA'):
            self.c.khoi_dong()
        self.assertEqual(self.spawn.call_count, 3)

    def test_dispatch_tra_ngay_503_khi_drain_chua_xong(self):
        self.c.khoi_dong()
        vao, ra = Event(), Event()
        def cho(*args):
            vao.set()
            if not ra.wait(3):
                raise subprocess.TimeoutExpired('demo', 3)
            self.proc.poll.return_value = 0
        self.proc.wait.side_effect = cho
        with ThreadPoolExecutor(max_workers=2) as pool:
            drain = pool.submit(self.c.thu_hoi, timeout=3)
            try:
                self.assertTrue(vao.wait(1))
                for goi in (self.c.khoi_dong, self.c.accept):
                    truoc = time.monotonic()
                    with self.assertRaisesRegex(tt.LoiTienTrinh, 'TIEN_TRINH_DANG_DUNG') as bat:
                        pool.submit(goi).result(timeout=0.5)
                    self.assertLess(time.monotonic()-truoc, 0.5)
                    self.assertEqual(bat.exception.http_status, 503)
                    self.assertEqual(bat.exception.headers, {'Retry-After': '2'})
                self.assertFalse(drain.done())
            finally:
                ra.set()
            self.assertTrue(drain.result(timeout=1))

    def test_loi_pipe_sau_readiness_lan_3_khoa_khong_reset_som(self):
        def loi_pipe(kieu):
            self.assertEqual(kieu, 'nhan_accept')
            self.assertEqual(self.so.dong['trang_thai'], 'CON_GIU')
            self.assertEqual(self.so.dong.get('so_loi_khoi_dong', 0), n-1)
            raise BrokenPipeError('G221_SECRET')
        with patch.object(self.c, '_gui', side_effect=loi_pipe):
            for n in range(1, 4):
                self.proc.poll.return_value = None
                self.proc.stdin = io.BytesIO()
                self.job.reset_mock()
                ma = 'KHOI_DONG_LOI' if n < 3 else 'KHOI_DONG_BI_KHOA'
                with self.assertRaisesRegex(tt.LoiTienTrinh, ma):
                    self.c.khoi_dong()
                self.assertEqual(self.so.dong['so_loi_khoi_dong'], n)
                self.assertEqual(self.so.dong['trang_thai'], 'LOI' if n == 3 else 'CORE_GIU')
                if n < 3:
                    self.so.dong['thu_lai_sau'] = (datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
        self.assertEqual(sum(t == 'san_sang' for t, _ in self.so.go), 3)
        self.assertNotIn('xac_nhan_accept', [t for t, _ in self.so.go])
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'KHOI_DONG_BI_KHOA'):
            self.c.khoi_dong()
        self.assertEqual(self.spawn.call_count, 3)

    def test_reset_dem_chi_sau_gui_accept_va_commit_core(self):
        self.so.dong.update(so_loi_khoi_dong=2, ma_loi_khoi_dong='DEMO_LOI',
                            thu_lai_sau=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())
        gui = self.c._gui
        def nhan_accept(kieu):
            self.assertEqual(self.so.dong['so_loi_khoi_dong'], 2)
            self.assertEqual(self.so.dong['trang_thai'], 'CON_GIU')
            self.assertEqual(self.c.trang_thai, 'starting')
            gui(kieu)
        xac_nhan = tt._xac_nhan_accept
        def xac_nhan_core(*args):
            self.assertEqual(json.loads(self.proc.stdin.getvalue().splitlines()[1])['kieu'], 'nhan_accept')
            self.assertEqual(self.c.trang_thai, 'starting')
            return xac_nhan(*args)
        with patch.object(self.c, '_gui', side_effect=nhan_accept), \
                patch.object(tt, '_xac_nhan_accept', side_effect=xac_nhan_core):
            self.c.khoi_dong()
        self.assertEqual((self.so.dong['so_loi_khoi_dong'], self.so.dong['thu_lai_sau'],
                          self.so.dong['ma_loi_khoi_dong']), (0, None, None))
        self.assertEqual(self.c.trang_thai, 'ready')

    def test_loi_xac_nhan_core_sau_gui_accept_van_tinh_mot_loi(self):
        self.so.dong['so_loi_khoi_dong'] = 1
        with patch.object(tt, '_xac_nhan_accept', side_effect=sc.LoiSoCong('CONG_CAS')):
            with self.assertRaisesRegex(tt.LoiTienTrinh, 'KHOI_DONG_LOI'):
                self.c.khoi_dong()
        self.assertEqual(json.loads(self.proc.stdin.getvalue().splitlines()[1])['kieu'], 'nhan_accept')
        self.assertEqual((self.so.dong['so_loi_khoi_dong'], self.so.dong['trang_thai']), (2, 'CORE_GIU'))

    def test_loi_popen_chua_co_pid_van_dem_ben_vung_va_khoa_lan_3(self):
        self.spawn.side_effect = OSError('G221_SECRET')
        for n in range(1, 4):
            ma = 'KHOI_DONG_LOI' if n < 3 else 'KHOI_DONG_BI_KHOA'
            with self.assertRaisesRegex(tt.LoiTienTrinh, ma):
                self.c.khoi_dong()
            self.assertEqual(self.so.dong['so_loi_khoi_dong'], n)
            self.assertIsNone(self.so.dong['giu_boi'])
            self.assertEqual(self.so.dong['the_he'], 0)
            if n < 3:
                with self.assertRaisesRegex(tt.LoiTienTrinh, 'KHOI_DONG_LOI'):
                    self.c.khoi_dong()
                self.assertEqual(self.spawn.call_count, n)
                self.so.dong['thu_lai_sau'] = (datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
        self.assertEqual(self.so.dong['trang_thai'], 'LOI')

    def test_dispatch_tra_ngay_khi_pid_da_chet_job_van_drain(self):
        self.c.khoi_dong()
        vao, ra = Event(), Event()
        def cho(*args):
            self.proc.poll.return_value = 0
        def so_con():
            vao.set()
            return 0 if ra.is_set() else 1
        self.proc.wait.side_effect = cho
        self.job.so_tien_trinh.side_effect = so_con
        with ThreadPoolExecutor(max_workers=2) as pool:
            drain = pool.submit(self.c.thu_hoi, timeout=1)
            try:
                self.assertTrue(vao.wait(1))
                truoc = time.monotonic()
                with self.assertRaisesRegex(tt.LoiTienTrinh, 'TIEN_TRINH_DANG_DUNG') as bat:
                    pool.submit(self.c.khoi_dong).result(timeout=0.5)
                self.assertLess(time.monotonic()-truoc, 0.5)
                self.assertEqual(bat.exception.headers, {'Retry-After': '2'})
                self.assertFalse(drain.done())
            finally:
                ra.set()
            self.assertTrue(drain.result(timeout=1))

    def test_doi_chieu_restart_kiem_os_job_va_cas_dung_phien(self):
        self.c.khoi_dong()
        cu = self.c.instance_id
        self.proc.poll.return_value = 0
        self.c._thu_sau_khi_chet()
        self.c.dong()
        self.so.dong.update(giu_boi=str(cu), trang_thai='CON_GIU')
        moi = _control(self.so)
        for ket_qua in (False, True):
            dong = deepcopy(self.so.dong)
            with patch.object(tt, '_phien_da_dung', return_value=ket_qua) as os_kiem:
                if not ket_qua:
                    with self.assertRaisesRegex(tt.LoiTienTrinh, 'CONG_CAN_DOI_CHIEU'):
                        moi.doi_chieu()
                    self.assertEqual(self.so.dong['giu_boi'], str(cu))
                else:
                    self.assertIsNone(moi.doi_chieu()['giu_boi'])
                os_kiem.assert_called_once_with(self.so.phien, dong)
        self.assertIsNotNone(next(ts[3] for t, ts in self.so.go if t == 'doi_chieu'))

    def test_doi_chieu_loi_os_khong_tra_cong(self):
        self.so.dong.update(giu_boi=str(uuid4()), the_he=1, trang_thai='CON_GIU')
        self.so.phien = dict(id=self.so.dong['giu_boi'], the_he=1, pid=12345,
                             dinh_danh_lan_tao='CU', ten_job='DEMO')
        with patch.object(tt, '_phien_da_dung', side_effect=OSError('G221_SECRET')):
            with self.assertRaisesRegex(tt.LoiTienTrinh, 'CONG_CAN_DOI_CHIEU'):
                self.c.doi_chieu()
        self.assertNotIn('doi_chieu', [t for t, _ in self.so.go])

    def test_engine_nhan_ma_chu_tu_ho_so(self):
        self.so.dong.update(module=None, engine_ho_so_id=str(uuid4()))
        self.c._ma_chu = 'e_demo'
        self.c.khoi_dong()
        self.assertEqual(self.cfg['module'], 'e_demo')


class BootstrapThuanTest(unittest.TestCase):
    def test_migration_022_giu_owner_acl_va_khong_sua_016(self):
        p = Path(tt.__file__).with_name('sql') / '022_vong_doi.sql'
        sql = p.read_text(encoding='utf-8')
        moc = re.findall(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', sql)
        self.assertEqual((moc[0], moc[-1]), ('$$', '$$'))
        self.assertTrue(all(a == b for a, b in zip(moc[1:-1:2], moc[2:-1:2])))
        self.assertFalse(p.read_bytes().startswith(b'\xef\xbb\xbf'))
        self.assertIn("SET LOCAL ROLE %I", sql)
        self.assertIn('REVOKE ALL ON FUNCTION', sql)
        self.assertIn("PERFORM loi.so_cong_chi_core()", sql)
        self.assertNotRegex(sql, r'(?i)\bDROP\b|CREATE\s+ROLE')

    def test_doc_tu_choi_json_trung_khoa_khong_dong_va_vuot_gioi_han(self):
        for raw in (b'{"a":1,"a":2}\n', b'{}', b'x'*bs.TOI_DA+b'\n'):
            with self.subTest(raw=raw[:30]), self.assertRaises((bs.LoiBootstrap, ValueError)):
                bs.doc_thong_diep(raw)

    def test_socket_fromshare_va_bo_doc_nonce(self):
        cfg = dict(protocol=bs.PROTOCOL, kieu='khoi_dong', issuer='core-demo', module='demo',
            instance_id=str(uuid4()), pid=os.getpid(), dinh_danh_lan_tao='DEMO',
            nonce_khoi_dong='n'*43, cong=19121, the_he=1, dia_chi_nghe='127.0.0.1',
            phien_ban='1', tham_so={}, socket='REVNTw==')
        nghe = MagicMock()
        nghe.getsockname.return_value = ('127.0.0.1', 19121)
        vao, ra = io.BytesIO(), io.BytesIO()
        bs.gui_thong_diep(vao, cfg)
        bs.gui_thong_diep(vao, {'protocol': bs.PROTOCOL, 'kieu': 'nhan_accept'})
        bs.gui_thong_diep(vao, {'protocol': bs.PROTOCOL, 'kieu': 'thu_hoi'})
        vao.seek(0)
        with patch.object(bs, 'dinh_danh_lan_tao', return_value='DEMO'), \
                patch.object(bs.socket, 'fromshare', return_value=nghe, create=True) as nhan:
            b = bs.Bootstrap.nhan(kiem_chu_ky=lambda s, m: None, stdin=vao, stdout=ra)
        nhan.assert_called_once_with(b'DEMO')
        self.assertEqual(b.bo_doc._nonce_khoi_dong, 'n'*43)
        self.assertNotIn('n'*43, repr(b))
        with self.assertRaisesRegex(bs.LoiBootstrap, 'CHUA_CO_QUYEN_ACCEPT'):
            b.accept()
        b.bao_san_sang(phien_ban='THUC_TE', contracts=['demo/v1'], kiem_san_sang=lambda: True)
        self.assertEqual(json.loads(ra.getvalue().splitlines()[0])['phien_ban'], 'THUC_TE')
        b.accept()
        ngung, drain = MagicMock(), MagicMock(return_value=True)
        b.cho_thu_hoi(ngung_accept=ngung, drain=drain)
        ngung.assert_called_once()
        drain.assert_called_once()
        nghe.close.assert_called_once()
        self.assertFalse(b._duoc_accept)

    def test_bootstrap_sai_pid_khong_import_socket_va_khong_ro_nonce(self):
        vao = io.BytesIO(b'{"protocol":"ktt.bootstrap.v1","kieu":"khoi_dong",'
                         b'"pid":0,"nonce_khoi_dong":"G221_SECRET"}\n')
        with patch.object(bs.socket, 'fromshare', create=True) as nhan:
            with self.assertRaises(bs.LoiBootstrap) as bat:
                bs.Bootstrap.nhan(kiem_chu_ky=lambda s, m: None, stdin=vao, stdout=io.BytesIO())
        nhan.assert_not_called()
        self.assertNotIn('G221_SECRET', ''.join(traceback.format_exception(bat.exception)))
        self.assertIsNone(bat.exception.__context__)

    def test_preflight_chua_dat_khong_gui_ready(self):
        b = bs.Bootstrap()
        b._duoc_accept = False
        b._ra = io.BytesIO()
        with self.assertRaisesRegex(bs.LoiBootstrap, 'CHUA_SAN_SANG'):
            b.bao_san_sang(phien_ban='1', contracts=[], kiem_san_sang=lambda: False)
        self.assertEqual(b._ra.getvalue(), b'')


class PhienTruocNangCapTest(unittest.TestCase):
    def test_khong_ten_job_can_pid_da_dung_va_bind_loai_tru_moi_ghi_bang_chung(self):
        import ctypes
        # PID mat, PID tai su dung moi hon, cung PID da dung; con lai phai giu.
        for handle, loi, tao, wait, cu, bind_loi, da_dung in (
                (0, 87, None, None, '100', None, True),
                (12, 0, '101', 258, '100', None, True),
                (12, 0, '100', 0, '100', None, True),
                (0, 87, None, None, '100', 'bind', False),
                (12, 0, '101', 258, '100', 'bind', False),
                (12, 0, '100', 0, '100', 'bind', False),
                (0, 87, None, None, '100', 'setsockopt', False),
                (12, 0, '100', 258, '100', None, False),
                (12, 0, '100', 0xffffffff, '100', None, False),
                (12, 0, '99', 0, '100', None, False),
                (12, 0, 'KHONG_RO', 0, '100', None, False),
                (12, 0, '101', 0, 'KHONG_RO', None, False),
                (0, 5, None, None, '100', None, False)):
            with self.subTest(handle=handle, loi=loi, tao=tao, wait=wait, cu=cu, bind_loi=bind_loi):
                so = SoGia()
                so.dong.update(giu_boi=str(uuid4()), the_he=1, trang_thai='CON_GIU')
                so.phien = dict(id=so.dong['giu_boi'], the_he=1, pid=12345,
                                dinh_danh_lan_tao=cu, ten_job=None)
                kernel = MagicMock()
                kernel.OpenProcess.return_value = handle
                kernel.WaitForSingleObject.return_value = wait
                nghe = MagicMock()
                if bind_loi:
                    getattr(nghe, bind_loi).side_effect = OSError('DEMO_KHONG_CO_BANG_CHUNG')
                c = _control(so)
                with patch.object(tt.os, 'name', 'nt'), \
                        patch.object(ctypes, 'WinDLL', return_value=kernel, create=True), \
                        patch.object(ctypes, 'get_last_error', return_value=loi, create=True), \
                        patch.object(tt, 'dinh_danh_lan_tao', return_value=tao), \
                        patch.object(tt.socket, 'socket') as tao_socket:
                    tao_socket.return_value.__enter__.return_value = nghe
                    if da_dung:
                        self.assertIsNone(c.doi_chieu()['giu_boi'])
                        self.assertEqual(so.dong['trang_thai'], 'TRONG')
                        self.assertIsNotNone(next(ts[3] for t, ts in so.go if t == 'doi_chieu'))
                    else:
                        with self.assertRaisesRegex(tt.LoiTienTrinh, 'CONG_CAN_DOI_CHIEU'):
                            c.doi_chieu()
                        self.assertEqual(so.dong['giu_boi'], so.phien['id'])
                        self.assertNotIn('doi_chieu', [t for t, _ in so.go])
                kernel.OpenProcess.assert_called_once_with(0x100000 | 0x1000, False, 12345)
                kernel.OpenJobObjectW.assert_not_called()
                kernel.TerminateProcess.assert_not_called()
                kernel.TerminateJobObject.assert_not_called()
                if tao_socket.called:
                    tao_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
                    nghe.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                    if bind_loi != 'setsockopt':
                        nghe.bind.assert_called_once_with(('127.0.0.1', 19121))
                    tao_socket.return_value.__exit__.assert_called_once()
                if handle:
                    kernel.CloseHandle.assert_called_once_with(handle)
                else:
                    kernel.CloseHandle.assert_not_called()
                c.dong()

    def test_khong_ten_job_thieu_dich_bind_khong_duoc_suy_tu_pid_mat(self):
        import ctypes
        phien = dict(pid=12345, dinh_danh_lan_tao='100', ten_job=None)
        kernel = MagicMock()
        kernel.OpenProcess.return_value = 0
        for dong in (None, {}, {'dia_chi_nghe': '0.0.0.0', 'cong': 19121},
                     {'dia_chi_nghe': '127.0.0.1', 'cong': True}):
            with self.subTest(dong=dong), patch.object(tt.os, 'name', 'nt'), \
                    patch.object(ctypes, 'WinDLL', return_value=kernel, create=True), \
                    patch.object(ctypes, 'get_last_error', return_value=87, create=True), \
                    patch.object(tt.socket, 'socket') as tao_socket:
                self.assertFalse(tt._phien_da_dung(phien, dong))
                tao_socket.assert_not_called()


@unittest.skipUnless(os.name == 'nt' and hasattr(socket.socket, 'share'),
                     'CHUA_KIEM: cần Windows share/fromshare')
class TienTrinhLoopbackTest(unittest.TestCase):
    def setUp(self):
        self.ds = []
        self.addCleanup(self._dong)

    def _dong(self):
        for c in self.ds:
            if c._proc is not None:
                try:
                    c.thu_hoi(timeout=5)
                except tt.LoiTienTrinh:
                    # Chỉ Job/Popen test sở hữu; không PID lạ, không dừng dịch vụ.
                    c._job.ket_thuc()
                    c._proc.wait(5)
                    c.kiem_con()
            c.dong()

    def _tao(self, tham_so=None, so=None, **doi):
        if so is None:
            with socket.socket() as tam:
                tam.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                tam.bind(('127.0.0.1', 0))
                cong = tam.getsockname()[1]
            self.assertNotIn(cong, (8766, 8767, 8768))
            dong = _dong()
            dong['cong'] = cong
            so = SoGia(dong)
        c = _control(so, tham_so=tham_so, cho_khoi_dong=10, cho_dung=0.2, **doi)
        self.ds.append(c)
        return c, so

    def test_share_fromshare_con_accept_core_thu_hoi_dung_cong_nonce(self):
        c, so = self._tao({'echo': True, 'credential': 'G221_SECRET'})
        with patch.dict(os.environ, {'KHO_G221_CANARY': 'G221_SECRET', 'PGPASSWORD': 'G221_SECRET'}):
            c.khoi_dong()
        nonce = c._nonce
        pid = c._proc.pid
        with self.assertRaises(tt.LoiTienTrinh):
            c.accept()
        with socket.create_connection(('127.0.0.1', so.dong['cong']), timeout=3) as client:
            client.sendall(b'ping')
            self.assertEqual(client.recv(100), str(pid).encode('ascii'))
        c.thu_hoi(timeout=5)
        self.assertEqual((c.chu_accept, so.dong['trang_thai']), ('core', 'TRONG'))
        with socket.create_connection(('127.0.0.1', so.dong['cong']), timeout=3) as client:
            conn, _ = c.accept(timeout=3)
            conn.close()
        c._tham_so = {}
        c.khoi_dong()
        self.assertEqual(c.the_he, 2)
        self.assertNotEqual(nonce, c._nonce)

    def test_readiness_sai_pid_nonce_version_lan_tao_tu_choi_that(self):
        for ts in ({'sai': 'pid', 'gia_tri': 1}, {'sai': 'nonce_khoi_dong', 'gia_tri': 'x'*43},
                   {'version': '2'}, {'sai': 'dinh_danh_lan_tao', 'gia_tri': 'GIA'}):
            with self.subTest(ts=ts):
                c, so = self._tao(ts)
                with self.assertRaisesRegex(tt.LoiTienTrinh, 'TIEN_TRINH_KHONG_HOP_LE'):
                    c.khoi_dong()
                self.assertEqual((so.dong['trang_thai'], so.dong['so_loi_khoi_dong']),
                                 ('CORE_GIU', 1))
                self.assertNotIn('san_sang', [t for t, _ in so.go])

    def test_con_chet_thu_hoi_cung_listener(self):
        c, so = self._tao({'chet': True})
        c.khoi_dong()
        c._proc.wait(5)
        self.assertTrue(c.kiem_con())
        self.assertEqual(so.dong['trang_thai'], 'TRONG')
        self.assertEqual(c._nghe.getsockname()[1], so.dong['cong'])

    def test_doi_chieu_os_pid_lan_tao_job_con_worker_va_job_da_dong(self):
        so_id, instance = uuid4(), uuid4()
        ten = tt._ten_job(so_id, instance)
        job = tt._job(ten)
        ds = []
        try:
            for _ in range(2):
                p = subprocess.Popen([sys.executable, '-B', '-c',
                    'import sys; sys.stdin.buffer.read(1)'], stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=tt.env_con(),
                    close_fds=True, creationflags=0x08000000)
                ds.append(p)
                job.gan(p)
            goc, worker = ds
            phien = dict(pid=goc.pid, dinh_danh_lan_tao=bs.dinh_danh_lan_tao(goc), ten_job=ten)
            self.assertFalse(tt._phien_da_dung(phien))
            # PID khac lan tao van phai doi Job rong, khong giet PID tai su dung.
            self.assertFalse(tt._phien_da_dung({**phien, 'dinh_danh_lan_tao': 'CU'}))
            goc.stdin.close()
            goc.wait(5)
            self.assertIsNone(worker.poll())
            self.assertFalse(tt._phien_da_dung(phien))
            worker.stdin.close()
            worker.wait(5)
            self.assertTrue(tt.Trich6Host._cho_job_rong(None, job, 1))
            self.assertTrue(tt._phien_da_dung(phien))
            self.assertTrue(tt._phien_da_dung({**phien, 'pid': os.getpid(),
                                              'dinh_danh_lan_tao': 'PID_CU'}))
            job.dong()
            self.assertTrue(tt._phien_da_dung(phien))
            self.assertFalse(tt._phien_da_dung({**phien, 'ten_job': None}))
        finally:
            # Chỉ các tiến trình test sở hữu; EOF và chờ terminal trước đóng Job.
            for p in ds:
                if not p.stdin.closed:
                    p.stdin.close()
                p.wait(5)
            job.dong()

    def test_thieu_ten_job_goc_chet_worker_giu_listener_chan_tra_den_khi_worker_dung(self):
        for dia_chi in ('127.0.0.1', '::1'):
            with self.subTest(dia_chi=dia_chi):
                so_id, instance = uuid4(), uuid4()
                job = tt._job(tt._ten_job(so_id, instance))
                ds = []
                try:
                    for code in (
                            'import sys; sys.stdin.buffer.read(1)',
                            'import socket,sys; '
                            's=socket.socket(socket.AF_INET6 if ":" in sys.argv[1] else socket.AF_INET); '
                            's.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1); '
                            's.bind((sys.argv[1],0)); s.listen(); '
                            'print(s.getsockname()[1],flush=True); sys.stdin.buffer.read(1)'):
                        p = subprocess.Popen([sys.executable, '-B', '-c', code, dia_chi],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            env=tt.env_con(), close_fds=True, creationflags=0x08000000)
                        ds.append(p)
                        job.gan(p)
                    goc, worker = ds
                    cong = int(tt._doc_dong(worker.stdout, 5))
                    self.assertNotIn(cong, (8766, 8767, 8768))
                    so = SoGia()
                    so.dong.update(id=str(so_id), giu_boi=str(instance), the_he=1,
                                   trang_thai='CON_GIU', dia_chi_nghe=dia_chi, cong=cong)
                    so.phien = dict(id=str(instance), the_he=1, pid=goc.pid, ten_job=None,
                                    dinh_danh_lan_tao=bs.dinh_danh_lan_tao(goc))
                    c = _control(so)
                    self.addCleanup(c.dong)
                    goc.stdin.close()
                    goc.wait(5)
                    self.assertIsNone(worker.poll())
                    with self.assertRaisesRegex(tt.LoiTienTrinh, 'CONG_CAN_DOI_CHIEU'):
                        c.doi_chieu()
                    self.assertEqual((so.dong['giu_boi'], so.dong['trang_thai']),
                                     (str(instance), 'CON_GIU'))
                    self.assertNotIn('doi_chieu', [t for t, _ in so.go])
                    self.assertIsNone(worker.poll())
                    worker.stdin.close()
                    worker.wait(5)
                    self.assertIsNone(c.doi_chieu()['giu_boi'])
                    self.assertEqual(so.dong['trang_thai'], 'TRONG')
                    doi_chieu = [ts for t, ts in so.go if t == 'doi_chieu']
                    self.assertEqual(len(doi_chieu), 1)
                    self.assertIsNotNone(doi_chieu[0][3])
                finally:
                    for p in ds:
                        if not p.stdin.closed:
                            p.stdin.close()
                        p.wait(5)
                        p.stdout.close()
                    job.dong()

    def test_stdout_hon_64kb_sau_readiness_khong_chan_accept_va_drain(self):
        c, so = self._tao({'stdout_lon': True, 'echo': True})
        c.khoi_dong()
        pid = c._proc.pid
        # Core không xả stdout sau readiness; con vẫn đi qua print/os.write
        # hơn 64 KB rồi accept và nhận lệnh drain qua kênh bootstrap riêng.
        with socket.create_connection(('127.0.0.1', so.dong['cong']), timeout=3) as client:
            client.sendall(b'ping')
            self.assertEqual(client.recv(100), str(pid).encode('ascii'))
        self.assertTrue(c.thu_hoi(timeout=5))
        self.assertEqual((c.chu_accept, so.dong['trang_thai']), ('core', 'TRONG'))

    def test_drain_qua_han_khong_kill_va_thu_sau_terminal(self):
        c, so = self._tao({'drain_giay': 0.4})
        c.khoi_dong()
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'DUNG_CHUA_XAC_NHAN'):
            c.thu_hoi(timeout=0.01)
        self.assertIsNone(c._proc.poll())
        self.assertEqual(so.dong['trang_thai'], 'CON_GIU')
        c._proc.wait(5)
        self.assertTrue(c.kiem_con())

    def test_cong_bi_tien_trinh_la_chiem_khong_doi_khong_kill(self):
        # Tiến trình Python ngoài controller giữ listener qua stdout báo cổng 0.
        code = ('import socket,sys; s=socket.socket(); '
                's.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1); '
                's.bind(("127.0.0.1",0)); s.listen(); '
                'print(s.getsockname()[1],flush=True); sys.stdin.buffer.read(1)')
        la = subprocess.Popen([sys.executable, '-B', '-c', code], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=tt.env_con())
        try:
            cong = int(tt._doc_dong(la.stdout, 5))
            self.assertNotIn(cong, (8766, 8767, 8768))
            d = _dong()
            d['cong'] = cong
            c, so = self._tao(so=SoGia(d))
            with self.assertRaisesRegex(tt.LoiTienTrinh, 'CONG_BI_CHIEM'):
                c.khoi_dong()
            self.assertIsNone(la.poll())
            self.assertEqual((so.dong['cong'], so.dong['ma_loi_khoi_dong']), (cong, 'CONG_BI_CHIEM'))
            with socket.create_connection(('127.0.0.1', cong), timeout=2):
                pass
        finally:
            la.stdin.close()
            la.wait(5)
            la.stdout.close()


@unittest.skipUnless(g216.psycopg is not None and g216.g205.ADMIN_DSN,
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class TienTrinhPostgresTest(unittest.TestCase):
    """CSDL kho_test_* do fixture G2-16 cấp, nghiệp vụ qua login Core thật.

    Transport/OS giả; các ca Windows thật nằm riêng bên trên. Không DROP/dịch vụ.
    """

    _ghi = g216.SoCongPostgresTest._ghi
    _phien_admin = g216.SoCongPostgresTest._phien_admin

    @classmethod
    def setUpClass(cls):
        g216.SoCongPostgresTest.setUpClass.__func__(cls)

    def setUp(self):
        g216.SoCongPostgresTest.setUp(self)
        self.proc = MagicMock(pid=12345, stdin=io.BytesIO())
        self.proc.poll.return_value = None
        self.job = MagicMock()
        self.job.so_tien_trinh.return_value = 0
        self.nghe = MagicMock()
        self.nghe.share.return_value = b'DEMO'
        self.c = tt.TienTrinhCore(so_cong_id=self.id, giao_dich=self._tx,
            lenh=['DEMO_APPROVED'], phien_ban='1', issuer='core-demo', contracts=['demo/v1'],
            popen=lambda *a, **k: self.proc, job_factory=lambda: self.job,
            socket_factory=lambda *a: self.nghe, doc_lan_tao=lambda p: 'CREATE_DEMO',
            doc_dong=self._ready)
        self.addCleanup(self._dong)

    @contextmanager
    def _tx(self):
        with self.core.transaction():
            yield self.core

    def _ready(self, *a):
        cfg = json.loads(self.proc.stdin.getvalue().splitlines()[0])
        cfg.update(kieu='san_sang', san_sang=True, contracts=['demo/v1'])
        return (json.dumps(cfg) + '\n').encode('ascii')

    def _dong(self):
        self.proc.poll.return_value = 0
        if self.c._proc is not None:
            self.c.kiem_con()
        self.c.dong()

    def _doc(self):
        with self._tx() as conn:
            return sc.doc(conn, self.id)

    def test_san_sang_tra_va_the_he_cu_bi_chan(self):
        self.assertEqual(self.core.execute('SELECT session_user,current_user').fetchone(),
                         (self.core.info.user,)*2)
        self.c.khoi_dong()
        instance, the_he = self.c.instance_id, self.c.the_he
        self.assertEqual(self._doc()['trang_thai'], 'CON_GIU')
        self.assertIsNotNone(self.conn.execute(
            'SELECT san_sang_luc FROM loi.module_phien_chay WHERE id=%s', (instance,)).fetchone()[0])
        self.proc.poll.return_value = 0
        self.c.kiem_con()
        self.assertEqual(self._doc()['trang_thai'], 'TRONG')
        self.proc.poll.return_value = None
        self.proc.stdin = io.BytesIO()
        self.c.khoi_dong()
        self.assertEqual(self.c.the_he, the_he+1)
        for ham, kwargs in ((sc.san_sang, {'bang_chung_id': uuid4()}),
                            (sc.loi_khoi_dong, {'ma_loi': 'CONG_BI_CHIEM'})):
            with self.subTest(ham=ham.__name__), self.assertRaises(sc.LoiSoCong), self._tx() as conn:
                ham(conn, self.id, instance, the_he, **kwargs)
        self.assertEqual(self._doc()['trang_thai'], 'CON_GIU')

    def test_bind_loi_lan_3_moi_khoa_va_giu_sau_controller_moi(self):
        self.nghe.bind.side_effect = OSError('DEMO_OCCUPIED')
        for n, giay in ((1, 2), (2, 4), (3, None)):
            self.proc.stdin = io.BytesIO()
            self.proc.poll.return_value = None
            ma = 'CONG_BI_CHIEM' if n < 3 else 'KHOI_DONG_BI_KHOA'
            with patch.object(tt.Trich6Host, '_don'):
                with self.assertRaisesRegex(tt.LoiTienTrinh, ma):
                    self.c.khoi_dong()
            d = self._doc()
            self.assertEqual(d['so_loi_khoi_dong'], n)
            self.assertEqual(d['trang_thai'], 'LOI' if n == 3 else 'CORE_GIU')
            moi = tt.TienTrinhCore(so_cong_id=self.id, giao_dich=self._tx,
                lenh=['DEMO_APPROVED'], phien_ban='1', issuer='core-demo', contracts=[])
            if giay:
                with patch.object(tt, '_phien_da_dung', return_value=True):
                    with self.assertRaisesRegex(tt.LoiTienTrinh, 'KHOI_DONG_LOI') as bat:
                        moi.khoi_dong()
                self.assertEqual(bat.exception.headers, {'Retry-After': str(giay)})
                # Admin fixture chỉ rút ngắn đồng hồ test, counter vẫn qua LOGIN Core.
                self.conn.execute("UPDATE loi.so_cong SET thu_lai_sau=clock_timestamp()-interval '1 second' WHERE id=%s", (self.id,))
        d = self._doc()
        self.assertEqual((d['trang_thai'], d['ma_loi'], d['the_he']), ('LOI', 'CONG_BI_CHIEM', 3))
        self.assertEqual(d['giu_boi'], str(self.c.instance_id))
        moi = tt.TienTrinhCore(so_cong_id=self.id, giao_dich=self._tx,
            lenh=['DEMO_APPROVED'], phien_ban='1', issuer='core-demo', contracts=[])
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'KHOI_DONG_BI_KHOA'):
            moi.khoi_dong()

    def test_restart_doi_chieu_phien_mo_coi_ghi_uuid_audit_va_chan_cas_cu(self):
        self.c.khoi_dong()
        instance, the_he = self.c.instance_id, self.c.the_he
        self.proc.poll.return_value = 0
        self.c._don_loi()
        self.c.dong()  # đóng Core cũ, để nguyên dòng CON_GIU và lease còn hạn.
        moi = tt.TienTrinhCore(so_cong_id=self.id, giao_dich=self._tx,
            lenh=['DEMO_APPROVED'], phien_ban='1', issuer='core-demo', contracts=[])
        with self._tx() as conn:
            p = tt._doc_phien(conn, self.id)
        self.assertEqual((p['id'], p['the_he'], p['pid'], p['dinh_danh_lan_tao']),
                         (str(instance), the_he, 12345, 'CREATE_DEMO'))
        with patch.object(tt, '_phien_da_dung', return_value=False):
            with self.assertRaisesRegex(tt.LoiTienTrinh, 'CONG_CAN_DOI_CHIEU'):
                moi.doi_chieu()
        self.assertEqual(self._doc()['giu_boi'], str(instance))
        with patch.object(tt, '_phien_da_dung', return_value=True):
            d = moi.doi_chieu()
        self.assertEqual((d['trang_thai'], d['giu_boi']), ('TRONG', None))
        audit = self.conn.execute("SELECT request_id FROM loi.nhat_ky_kiem_toan WHERE doi_tuong_id=%s AND hanh_dong='CORE:CONG:DOI_CHIEU'", (self.id,)).fetchall()
        self.assertEqual(len(audit), 1)
        self.assertIsNotNone(audit[0][0])
        with self.assertRaisesRegex(sc.LoiSoCong, 'CONG_CAS'), self._tx() as conn:
            tt._doi_chieu(conn, self.id, instance, the_he, uuid4())

    def test_pg_loi_pipe_sau_readiness_lan_3_moi_khoa(self):
        def loi_pipe(kieu):
            self.assertEqual(kieu, 'nhan_accept')
            d = self._doc()
            self.assertEqual((d['trang_thai'], d['so_loi_khoi_dong']), ('CON_GIU', n-1))
            raise BrokenPipeError('DEMO_PIPE')
        with patch.object(self.c, '_gui', side_effect=loi_pipe), \
                patch.object(tt.Trich6Host, '_don'):
            for n in range(1, 4):
                self.proc.stdin = io.BytesIO()
                self.proc.poll.return_value = None
                ma = 'KHOI_DONG_LOI' if n < 3 else 'KHOI_DONG_BI_KHOA'
                with self.assertRaisesRegex(tt.LoiTienTrinh, ma):
                    self.c.khoi_dong()
                d = self._doc()
                self.assertEqual((d['so_loi_khoi_dong'], d['trang_thai']),
                                 (n, 'LOI' if n == 3 else 'CORE_GIU'))
                self.assertIsNotNone(self.conn.execute(
                    'SELECT san_sang_luc FROM loi.module_phien_chay WHERE id=%s',
                    (self.c.instance_id,)).fetchone()[0])
                if n < 3:
                    self.conn.execute("UPDATE loi.so_cong SET thu_lai_sau=clock_timestamp()-interval '1 second' WHERE id=%s", (self.id,))
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'KHOI_DONG_BI_KHOA'):
            self.c.khoi_dong()

    def test_pg_xac_nhan_accept_can_readiness_lease_va_moi_reset_dem(self):
        for n in (1, 2):
            with self._tx() as conn:
                tt._loi_chua_nhan(conn, self.id, 0, 'DEMO_LOI')
            self.conn.execute("UPDATE loi.so_cong SET thu_lai_sau=clock_timestamp()-interval '1 second' WHERE id=%s", (self.id,))
        gui = self.c._gui
        def nhan_accept(kieu):
            self.assertEqual((self._doc()['so_loi_khoi_dong'], self.c.trang_thai), (2, 'starting'))
            gui(kieu)
        with patch.object(self.c, '_gui', side_effect=nhan_accept):
            self.c.khoi_dong()
        d = self._doc()
        self.assertEqual((d['so_loi_khoi_dong'], d['thu_lai_sau'], d['ma_loi_khoi_dong']),
                         (0, None, None))
        instance, the_he = self.c.instance_id, self.c.the_he
        with self.assertRaisesRegex(sc.LoiSoCong, 'CONG_MAT_LEASE'), self._tx() as conn:
            tt._xac_nhan_accept(conn, self.id, uuid4(), the_he)
        self.proc.poll.return_value = 0
        self.c.kiem_con()
        self.instance = uuid4()
        g216.SoCongPostgresTest._nhan(self, the_he_cu=the_he)
        with self.assertRaisesRegex(sc.LoiSoCong, 'CONG_CAS'), self._tx() as conn:
            tt._xac_nhan_accept(conn, self.id, self.instance, the_he+1)
        with self.assertRaisesRegex(sc.LoiSoCong, 'CONG_MAT_LEASE'), self._tx() as conn:
            tt._xac_nhan_accept(conn, self.id, instance, the_he)

    def test_pg_nang_cap_dong_phien_khong_ten_job_doi_chieu_va_audit(self):
        import ctypes
        instance = uuid4()
        now = datetime.now(timezone.utc)
        with self._tx() as conn:
            sc.nhan(conn, self.id, instance, 0, pid=12345, dinh_danh_lan_tao='100',
                    phien_ban='1', nhan_yeu_cau_luc=now, bat_dau_luc=now)
            sc.san_sang(conn, self.id, instance, 1, bang_chung_id=uuid4())
        # Dong theo G2-21 khong ghi ten Job; ap 022 van phai doi chieu duoc.
        self.conn.execute((Path(tt.__file__).with_name('sql') / '022_vong_doi.sql').read_text(encoding='utf-8'))
        with self._tx() as conn:
            self.assertIsNone(tt._doc_phien(conn, self.id)['ten_job'])
        kernel = MagicMock()
        kernel.OpenProcess.return_value = 12
        nghe = MagicMock()
        with patch.object(ctypes, 'WinDLL', return_value=kernel, create=True), \
                patch.object(tt.os, 'name', 'nt'), \
                patch.object(tt, 'dinh_danh_lan_tao', return_value='101'), \
                patch.object(tt.socket, 'socket') as tao_socket:
            tao_socket.return_value.__enter__.return_value = nghe
            nghe.bind.side_effect = OSError('DEMO_WORKER_GIU_LISTENER')
            with self.assertRaisesRegex(tt.LoiTienTrinh, 'CONG_CAN_DOI_CHIEU'):
                self.c.doi_chieu()
            self.assertEqual(self._doc()['giu_boi'], str(instance))
            self.assertEqual(self.conn.execute("SELECT count(*) FROM loi.nhat_ky_kiem_toan WHERE doi_tuong_id=%s AND hanh_dong='CORE:CONG:DOI_CHIEU'", (self.id,)).fetchone()[0], 0)
            nghe.bind.side_effect = None
            d = self.c.doi_chieu()
        self.assertEqual((d['trang_thai'], d['giu_boi']), ('TRONG', None))
        kernel.OpenJobObjectW.assert_not_called()
        audit = self.conn.execute("SELECT request_id FROM loi.nhat_ky_kiem_toan WHERE doi_tuong_id=%s AND hanh_dong='CORE:CONG:DOI_CHIEU'", (self.id,)).fetchall()
        self.assertEqual(len(audit), 1)
        self.assertIsNotNone(audit[0][0])

    def test_admin_mo_khoa_reset_dem_van_doi_chieu_danh_tinh_cu(self):
        self.nghe.bind.side_effect = OSError('DEMO')
        for n in range(1, 4):
            self.proc.stdin = io.BytesIO()
            self.proc.poll.return_value = None
            with patch.object(tt.Trich6Host, '_don'):
                with self.assertRaises(tt.LoiTienTrinh):
                    self.c.khoi_dong()
            if n < 3:
                self.conn.execute("UPDATE loi.so_cong SET thu_lai_sau=clock_timestamp()-interval '1 second' WHERE id=%s", (self.id,))
        d = self._doc()
        instance = d['giu_boi']
        ma, pn = self._phien_admin()
        with self._tx() as conn:
            d = sc.mo_khoa(conn, self.id, d['phien_ban_dong'], ma=ma,
                           phap_nhan_id=pn, request_id=uuid4())
        self.assertEqual((d['so_loi_khoi_dong'], d['thu_lai_sau'], d['giu_boi']),
                         (0, None, instance))
        self.c._da_dung.clear()  # mô phỏng Core mới không có bằng chứng RAM.
        with patch.object(tt, '_phien_da_dung', return_value=False):
            with self.assertRaisesRegex(tt.LoiTienTrinh, 'CONG_CAN_DOI_CHIEU'):
                self.c.doi_chieu()
        with patch.object(tt, '_phien_da_dung', return_value=True):
            self.assertIsNone(self.c.doi_chieu()['giu_boi'])
        self.nghe.bind.side_effect = None
        self.proc.poll.return_value = None
        self.proc.stdin = io.BytesIO()
        self.c.khoi_dong()
        self.assertEqual(self._doc()['so_loi_khoi_dong'], 0)

    def test_cua_022_chi_core_va_khong_lo_quyen_bang(self):
        for conn in (self.module, self.cai_dat):
            for cau, ts in (
                ('SELECT loi.so_cong_doc_phien(%s)', (self.id,)),
                ('SELECT loi.so_cong_xac_nhan_accept(%s,%s,%s)', (self.id, uuid4(), 1)),
                ('SELECT loi.so_cong_doi_chieu(%s,%s,%s,%s)', (self.id, uuid4(), 1, uuid4())),
                ('SELECT loi.so_cong_loi_chua_nhan(%s,%s,%s)', (self.id, 0, 'DEMO_LOI'))):
                with self.subTest(cau=cau, login=conn.info.user), self.assertRaises(g216.psycopg.errors.InsufficientPrivilege):
                    conn.execute(cau, ts)
        with self.assertRaises(g216.psycopg.errors.InsufficientPrivilege):
            self.core.execute('SELECT so_loi_khoi_dong FROM loi.so_cong')


if __name__ == '__main__':
    if '--child' in sys.argv:
        _child()
    else:
        unittest.main()
