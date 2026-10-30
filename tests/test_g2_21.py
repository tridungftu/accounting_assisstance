"""G2-21: mock/thuần + Python con loopback Windows + PG opt-in.

Không tài khoản/ACL/dịch vụ thật; không xóa tệp hoặc CSDL. --child chỉ là
runtime DEMO nhận mọi tham số qua stdin, không mở dữ liệu người dùng.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
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
        if ten in ('san_sang', 'tra', 'loi_khoi_dong', 'gia_han'):
            assert (d['giu_boi'], d['the_he']) == (str(ts[1]), ts[2])
        if ten == 'san_sang':
            d['trang_thai'] = 'CON_GIU'
        if ten == 'tra':
            d.update(trang_thai='TRONG', giu_boi=None)
        if ten == 'loi_khoi_dong':
            d.update(trang_thai='LOI', ma_loi=ts[-1])
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
        self.assertEqual([t for t, _ in self.so.go], ['doc', 'nhan', 'san_sang'])
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
        self.assertEqual(self.so.dong['trang_thai'], 'LOI')
        self.assertNotIn('san_sang', [t for t, _ in self.so.go])

    def test_bind_bi_chiem_khong_doi_cong_khong_diet_ung_dung_la(self):
        self.nghe.bind.side_effect = OSError('CANARY OS message')
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'CONG_BI_CHIEM') as bat:
            self.c.khoi_dong()
        self.assertEqual(self.nghe.bind.call_count, 1)
        self.assertEqual(self.so.dong['cong'], 19121)
        self.assertEqual(self.so.dong['ma_loi'], 'CONG_BI_CHIEM')
        self.assertEqual(self.so.go[-1][1][1:3], (self.c.instance_id, 1))
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
        self.assertEqual(self.so.dong['ma_loi'], 'KHOI_DONG_QUA_HAN')

    def test_engine_nhan_ma_chu_tu_ho_so(self):
        self.so.dong.update(module=None, engine_ho_so_id=str(uuid4()))
        self.c._ma_chu = 'e_demo'
        self.c.khoi_dong()
        self.assertEqual(self.cfg['module'], 'e_demo')


class BootstrapThuanTest(unittest.TestCase):
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
                self.assertEqual(so.dong['trang_thai'], 'LOI')
                self.assertNotIn('san_sang', [t for t, _ in so.go])

    def test_con_chet_thu_hoi_cung_listener(self):
        c, so = self._tao({'chet': True})
        c.khoi_dong()
        c._proc.wait(5)
        self.assertTrue(c.kiem_con())
        self.assertEqual(so.dong['trang_thai'], 'TRONG')
        self.assertEqual(c._nghe.getsockname()[1], so.dong['cong'])

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
            self.assertEqual((so.dong['cong'], so.dong['ma_loi']), (cong, 'CONG_BI_CHIEM'))
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

    def test_bind_loi_khoa_dung_the_he_va_giu_sau_controller_moi(self):
        self.nghe.bind.side_effect = OSError('DEMO_OCCUPIED')
        with patch.object(tt.Trich6Host, '_don'):
            with self.assertRaisesRegex(tt.LoiTienTrinh, 'CONG_BI_CHIEM'):
                self.c.khoi_dong()
        d = self._doc()
        self.assertEqual((d['trang_thai'], d['ma_loi'], d['the_he']), ('LOI', 'CONG_BI_CHIEM', 1))
        self.assertEqual(d['giu_boi'], str(self.c.instance_id))
        moi = tt.TienTrinhCore(so_cong_id=self.id, giao_dich=self._tx,
            lenh=['DEMO_APPROVED'], phien_ban='1', issuer='core-demo', contracts=[])
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'KHOI_DONG_BI_KHOA'):
            moi.khoi_dong()


if __name__ == '__main__':
    if '--child' in sys.argv:
        _child()
    else:
        unittest.main()
