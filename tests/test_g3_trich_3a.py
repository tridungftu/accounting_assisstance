"""TRICH-3a: DOCX/AI/Core DEMO; bootstrap, listener và Windows Job thật.

Dùng fixture TRICH-1a, không sửa test/nguồn gốc. Tệp tạm được giữ lại,
không xóa; child cấm connect/DNS và không gọi Word/OCR/provider thật.
Wire/ACK/đường tệp dưới đây chỉ là seam test, không là contract IPC mới.
"""

from contextlib import ExitStack
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
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Core lọc USERPROFILE/HOME. Nguồn TRICH-1a tính đường khóa ngay khi import;
# seam child cấp đường DEMO vô hiệu, không đọc cấu hình/kho khóa của máy.
# Tích hợp thật cần lead xử lý import cấu hình nguồn ở TRICH-1b/3b.
if '--child' in sys.argv:
    os.environ['HD_THU_MUC_KHOA'] = str(Path(__file__).resolve().parent / 'DEMO-khong-co-khoa')

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import tien_trinh as tt
from kho_tri_thuc.engines.e_trich_xuat import chay as trich
from kho_tri_thuc.m4.review_goc.trich_xuat import cloud, doc_hop_dong, quy_trinh
from kho_tri_thuc.sdk_core import bootstrap as bs
from kho_tri_thuc.sdk_core.engine import KenhCore, LoiEngine, SDKEngine

try:
    from .test_g2_17 import _minimal
    from .test_g2_21 import SoGia, _dong
    from .test_g3_ocr_4a import _lease
    from .test_g3_trich_1a import AIGia, MA, PHAN_HOI, ROOT, TEP, TEXT, tao_docx
except ImportError:
    from test_g2_17 import _minimal
    from test_g2_21 import SoGia, _dong
    from test_g3_ocr_4a import _lease
    from test_g3_trich_1a import AIGia, MA, PHAN_HOI, ROOT, TEP, TEXT, tao_docx


def _metadata(ma):
    return dict(du_lieu_ket_qua=dict(bien_the='trich_demo', ma_contract=ma,
        phien_ban_contract='1.0.0', trang_thai='can_soat', ly_do='DEMO AI giả',
        revision_truoc=0, nguon=[]), revision_tep_truoc=0)


def _dau_vao():
    path = tao_docx('<w:p><w:del><w:r><w:delText>DEMO bỏ</w:delText></w:r></w:del>'
                    f'<w:ins><w:r><w:t>{TEXT}</w:t></w:r></w:ins></w:p>')
    return dict(docx=path, out_dir=path.parent / 'DEMO-out', tep_id=TEP,
        loai_hop_dong='XD', danh_muc_id='XD', danh_muc_sha256=trich.DANH_MUC_SHA256,
        phan_hoi=_metadata('phan_hoi_trich_demo'), tham_so=_metadata('tham_so'))


def _schema(value, bundle, urn):
    schemas = json.loads((ROOT / 'src/kho_tri_thuc/core/contract' / bundle).read_text(encoding='utf-8'))
    schema = schemas[urn]
    _minimal(value, schema, schema, schemas)
    try:
        from jsonschema import Draft202012Validator, FormatChecker
        from referencing import Registry, Resource
    except ImportError:
        return
    registry = Registry().with_resources((key, Resource.from_contents(item)) for key, item in schemas.items())
    Draft202012Validator(schema, registry=registry, format_checker=FormatChecker()).validate(value)


class KenhGia(KenhCore):
    def __init__(self, dau_vao=None, *, conn=None, giu=None, loi=None):
        self.dau_vao = _dau_vao() if dau_vao is None else dau_vao
        self.conn, self.giu, self.loi = conn, giu, loi
        self.go = []
        self.luong, self.raw, self.dem = {}, {}, {}
        self.cho_ack, self.ack = threading.Event(), threading.Event()

    def goi(self, operation, giu_viec, **payload):
        self.go.append((operation, giu_viec))
        if operation == 'doc_dau_vao':
            return self.dau_vao
        assert operation == 'ghi_ket_qua'
        ten = payload['ten']
        raw = payload['luong'].read()
        self.dem[ten] = self.dem.get(ten, 0) + 1
        if ten in self.raw:
            assert raw == self.raw[ten]
            assert payload['luong'] is self.luong[ten]
            assert not self.luong[ten].closed
        self.raw[ten], self.luong[ten] = raw, payload['luong']
        meta = self.dau_vao['phan_hoi' if ten == 'phan-hoi-nguon.json' else 'tham_so']
        assert payload['du_lieu'] == meta['du_lieu_ket_qua']
        assert payload['revision_tep_truoc'] == meta['revision_tep_truoc']
        if ten == self.loi and self.dem[ten] == 1:
            if self.conn is not None:
                self.conn.sendall(b'loi_truoc_ack\n')
            raise RuntimeError('TRICH3A_CANARY')
        if ten == self.giu:
            self.cho_ack.set()
            if self.conn is None:
                assert self.ack.wait(10)
            else:
                self.conn.sendall(b'cho_ack\n')
                assert self.conn.recv(32) == b'core_da_nhan\n'
        if ten == 'tham-so.json' and self.conn is not None:
            self.conn.sendall(b'da_xong_37\n')
        return {'tep_id': PHAN_HOI} if ten == 'phan-hoi-nguon.json' else {'ket_qua_id': 'DEMO_DA_NHAN'}


def _cam_mang(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo', 'socket.gethostbyname'):
        raise AssertionError('TRICH-3a cấm kết nối mạng/DNS')


def _child():
    sys.addaudithook(_cam_mang)

    def nhan_viec(conn, bo_doc):
        marker = conn.recv(64)
        assert marker in (b'DEMO_TRICH\n', b'DEMO_TRICH_NGUON\n', b'DEMO_TRICH_KQ\n')
        ten = {b'DEMO_TRICH_NGUON\n': 'phan-hoi-nguon.json',
               b'DEMO_TRICH_KQ\n': 'tham-so.json'}.get(marker)
        return SDKEngine(_lease(), kenh_core=KenhGia(conn=conn, giu=ten, loi=ten))

    def khong_nhan_the(*args):
        raise ValueError('Không cấp thẻ request trong seam DEMO')

    trich.chay(kiem_chu_ky=khong_nhan_the, nhan_viec=nhan_viec,
                backend=trich.BackendTrichXuat(ai=AIGia()))


class TrichThuanTests(unittest.TestCase):
    def test_manifest_chi_docx_tham_so_va_dat_schema(self):
        value = json.loads(Path(trich.__file__).with_name('engine.json').read_text(encoding='utf-8'))
        _schema(value, 'manifest.json', 'urn:ktt:manifest:engine.v1')
        self.assertEqual(value['phien_ban'], trich.PHIEN_BAN)
        self.assertEqual([(c['ma'], c['dau_vao'], c['dau_ra']) for c in value['capability']],
                         [('trich.tham_so_hop_dong@1', 'tham_chieu_tep.v1', 'tham_so.v1')])
        self.assertEqual(value['capability'][0]['mime'],
            ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'])
        self.assertTrue(value['ho_so_chay_mau']['headless'])
        self.assertFalse(value['ho_so_chay_mau']['login_csdl'])
        self.assertEqual(value['ket_noi_ngoai'], [])

    def test_docx_ai_gia_ban_giao_nguon_truoc_anh_xa_37(self):
        kenh, ai = KenhGia(), AIGia()
        before = kenh.dau_vao['docx'].read_bytes()
        lease = _lease()
        with ExitStack() as stack:
            for obj, ten in ((socket.socket, 'connect'), (subprocess, 'Popen'),
                             (doc_hop_dong, '_word'), (quy_trinh.TrichXuat, 'ocr_pdf'),
                             (cloud, 'kiem_tra_cloud')):
                stack.enter_context(patch.object(obj, ten, side_effect=AssertionError(ten)))
            result = trich.xu_ly_viec(SDKEngine(lease, kenh_core=kenh),
                                      backend=trich.BackendTrichXuat(ai=ai))
        self.assertEqual(result, {'ket_qua_id': 'DEMO_DA_NHAN'})
        self.assertEqual([op for op, _ in kenh.go], ['doc_dau_vao', 'ghi_ket_qua', 'ghi_ket_qua'])
        self.assertTrue(all(giu is lease for _, giu in kenh.go))
        self.assertGreater(ai.goi, 0)
        source = json.loads(kenh.raw['phan-hoi-nguon.json'])
        mapped = json.loads(kenh.raw['tham-so.json'])
        self.assertEqual(tuple(row['ma'] for row in source['bang']), MA)
        self.assertEqual(source['phieu_kiem_tra']['accept_by'], 'Python')
        self.assertEqual(mapped['phan_hoi_nguon_tep_id'], PHAN_HOI)
        self.assertEqual(tuple(row['ma'] for row in mapped['tham_so']), MA)
        self.assertTrue(all(row['gia_tri'] == {'kieu': 'van_ban', 'gia_tri': '00007'}
                            for row in mapped['tham_so']))
        self.assertTrue(all(row['dan_chung'][0]['trich_dan'] == TEXT for row in mapped['tham_so']))
        self.assertEqual(kenh.dau_vao['docx'].read_bytes(), before)
        self.assertTrue(all(luong.closed for luong in kenh.luong.values()))
        _schema(mapped, 'ky_thuat.json', 'urn:ktt:contract:tham_so.v1')

    def test_retry_ca_hai_ban_giao_giu_luong_va_khong_chay_lai_ai(self):
        for ten in ('phan-hoi-nguon.json', 'tham-so.json'):
            with self.subTest(ten=ten):
                kenh = KenhGia(giu=ten, loi=ten)
                backend = MagicMock(wraps=trich.BackendTrichXuat(ai=AIGia()))
                result, errors = [], []

                def run():
                    try:
                        result.append(trich.xu_ly_viec(SDKEngine(_lease(), kenh_core=kenh), backend=backend))
                    except Exception as exc:
                        errors.append(exc)

                worker = threading.Thread(target=run)
                worker.start()
                try:
                    self.assertTrue(kenh.cho_ack.wait(5))
                    self.assertTrue(worker.is_alive())
                    self.assertEqual(result, [])
                    self.assertEqual(kenh.dem[ten], 2)
                    self.assertFalse(kenh.luong[ten].closed)
                    if ten == 'phan-hoi-nguon.json':
                        self.assertNotIn('tham-so.json', kenh.raw)
                    self.assertTrue(kenh.dau_vao['out_dir'].exists())
                finally:
                    kenh.ack.set()
                    worker.join(5)
                self.assertFalse(worker.is_alive())
                self.assertEqual(errors, [])
                self.assertEqual(result, [{'ket_qua_id': 'DEMO_DA_NHAN'}])
                backend.xu_ly.assert_called_once()
                self.assertEqual(kenh.dem[ten], 2)
                self.assertTrue(all(luong.closed for luong in kenh.luong.values()))

    def test_sai_loai_catalog_pdf_cloud_khong_fallback(self):
        data, backend = _dau_vao(), trich.BackendTrichXuat(ai=AIGia())
        for changes in ({'loai_hop_dong': 'MUA_HH'}, {'danh_muc_id': ''},
                        {'danh_muc_sha256': '0' * 64}, {'docx': 'DEMO.pdf'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                backend.xu_ly(data | changes)
        for value in (None, MagicMock(la_cloud=True)):
            with self.assertRaisesRegex(ValueError, 'CLOUD_BI_CHAN'):
                trich.BackendTrichXuat(ai=value)
        backend.ai.la_cloud = True
        with self.assertRaisesRegex(ValueError, 'CLOUD_BI_CHAN'):
            backend.xu_ly(data)

    def test_sai_sdk_va_mat_lease_khong_chay_backend(self):
        backend = MagicMock()
        with self.assertRaises(TypeError):
            trich.xu_ly_viec(object(), backend=backend)
        lease = replace(_lease(), giu_den=datetime.now(timezone.utc) - timedelta(seconds=1))
        kenh = KenhGia()
        with self.assertRaisesRegex(LoiEngine, 'VIEC_MAT_LEASE'):
            trich.xu_ly_viec(SDKEngine(lease, kenh_core=kenh), backend=backend)
        backend.xu_ly.assert_not_called()
        self.assertEqual(kenh.go, [])

    def test_preflight_catalog_thieu_hoac_sai_khong_ready(self):
        for exc in (FileNotFoundError(), ValueError('TRICH_DANH_MUC_SAI_HASH')):
            b = bs.Bootstrap()
            b.socket, b._ra, b._duoc_accept = MagicMock(), io.BytesIO(), False
            with patch.object(trich.Bootstrap, 'nhan', return_value=b), \
                    patch.object(trich, 'danh_muc_xd', side_effect=exc), \
                    patch.object(trich._VongNhan, 'bat_dau') as start:
                with self.assertRaises(type(exc)):
                    trich.chay(kiem_chu_ky=lambda *_: None, nhan_viec=lambda *_: None,
                                backend=trich.BackendTrichXuat(ai=AIGia()))
            start.assert_not_called()
            b.socket.close.assert_called_once()
            self.assertEqual(b._ra.getvalue(), b'')

    def test_readiness_gia_khong_cong_bo_capability_that(self):
        b = MagicMock()
        with patch.object(trich.Bootstrap, 'nhan', return_value=b), \
                patch.object(trich, '_VongNhan') as vong:
            vong.return_value.drain.return_value = True
            trich.chay(kiem_chu_ky=lambda *_: None, nhan_viec=lambda *_: None,
                        backend=trich.BackendTrichXuat(ai=AIGia()))
        self.assertEqual(b.bao_san_sang.call_args.kwargs['contracts'], [])
        self.assertEqual(b.bao_san_sang.call_args.kwargs['phien_ban'], trich.PHIEN_BAN)


@unittest.skipUnless(os.name == 'nt' and hasattr(socket.socket, 'share'),
                     'CHUA_KIEM: cần Windows share/fromshare và Job')
class TrichTienTrinhTests(unittest.TestCase):
    def setUp(self):
        self.controllers = []
        self.addCleanup(self._dong)

    def _dong(self):
        for c in self.controllers:
            if c._proc is not None:
                try:
                    c.thu_hoi(timeout=5)
                except tt.LoiTienTrinh:
                    c._job.ket_thuc()
                    c._proc.wait(5)
                    c.kiem_con()
            c.dong()

    def _tao(self):
        with socket.socket() as tam:
            tam.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            tam.bind(('127.0.0.1', 0))
            cong = tam.getsockname()[1]
        d = _dong()
        d.update(module=None, engine_ho_so_id=str(uuid4()), cong=cong)
        so = SoGia(d)
        c = tt.TienTrinhCore(so_cong_id=d['id'], giao_dich=so.giao_dich,
            lenh=[sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()), '--child'],
            phien_ban=trich.PHIEN_BAN, issuer='core-demo', contracts=[],
            ma_chu='e_trich_xuat', cho_khoi_dong=15, cho_dung=0.2)
        self.controllers.append(c)
        return c, so

    def _ket_noi(self, so):
        conn = socket.create_connection(('127.0.0.1', so.dong['cong']), timeout=8)
        self.addCleanup(conn.close)
        return conn

    def test_khoi_dong_job_xu_ly_va_restart_giu_listener(self):
        c, so = self._tao()
        c.khoi_dong()
        nonce, listener = c._nonce, c._nghe
        for lan in (1, 2):
            self.assertEqual(c.the_he, lan)
            self.assertEqual((c.trang_thai, c.chu_accept), ('ready', 'con'))
            self.assertGreaterEqual(c._job.so_tien_trinh(), 1)
            with self._ket_noi(so) as conn:
                conn.sendall(b'DEMO_TRICH\n')
                with conn.makefile('rb') as reader:
                    self.assertEqual(reader.readline(), b'da_xong_37\n')
            self.assertTrue(c.thu_hoi(timeout=5))
            if lan == 1:
                c.khoi_dong()
                self.assertNotEqual(c._nonce, nonce)
                self.assertIs(c._nghe, listener)
        self.assertEqual((c.chu_accept, so.dong['trang_thai']), ('core', 'TRONG'))
        with self._ket_noi(so):
            accepted, _ = c.accept(timeout=3)
            accepted.close()

    def _kiem_drain(self, marker):
        c, so = self._tao()
        c.khoi_dong()
        proc, job = c._proc, c._job
        conn = self._ket_noi(so)
        conn.sendall(marker)
        reader = conn.makefile('rb')
        self.addCleanup(reader.close)
        self.assertEqual(reader.readline(), b'loi_truoc_ack\n')
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'DUNG_CHUA_XAC_NHAN'):
            c.thu_hoi(timeout=0.05)
        self.assertEqual(bs.doc_thong_diep(tt._doc_dong(proc.stdout, 5)),
                         {'protocol': bs.PROTOCOL, 'kieu': 'drain_chua_xong'})
        self.assertEqual(reader.readline(), b'cho_ack\n')
        self.assertIsNone(proc.poll())
        self.assertGreaterEqual(job.so_tien_trinh(), 1)
        self.assertEqual((c.trang_thai, c.chu_accept), ('dang_dung', 'con'))
        self.assertNotIn('tra', [ten for ten, _ in so.go])
        moi = self._ket_noi(so)
        moi.sendall(b'DEMO_TRICH\n')
        moi.settimeout(0.2)
        with self.assertRaises(socket.timeout):
            moi.recv(128)
        conn.sendall(b'core_da_nhan\n')
        self.assertEqual(reader.readline(), b'da_xong_37\n')
        self.assertEqual(bs.doc_thong_diep(tt._doc_dong(proc.stdout, 5)),
                         {'protocol': bs.PROTOCOL, 'kieu': 'da_thu_hoi'})
        proc.wait(5)
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(c.kiem_con())
        self.assertEqual(so.dong['trang_thai'], 'TRONG')

    def test_drain_cho_ack_phan_hoi_nguon_sau_retry(self):
        self._kiem_drain(b'DEMO_TRICH_NGUON\n')

    def test_drain_cho_ack_tham_so_sau_retry(self):
        self._kiem_drain(b'DEMO_TRICH_KQ\n')

    def test_khong_ready_khi_core_doi_capability_chua_dat(self):
        c, so = self._tao()
        c._contracts = ['trich.tham_so_hop_dong@1']
        with self.assertRaisesRegex(tt.LoiTienTrinh, 'TIEN_TRINH_KHONG_HOP_LE'):
            c.khoi_dong()
        self.assertNotIn('san_sang', [ten for ten, _ in so.go])


if __name__ == '__main__':
    if '--child' in sys.argv:
        _child()
    else:
        unittest.main()
