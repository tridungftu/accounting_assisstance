"""TRICH-3a: khung Core/AI giả, dùng adapter TRICH-1a.

Vòng đời theo e_ocr/chay.py (OCR-4a): Bootstrap G2-21 và SDK G2-20;
không tự tạo listener, lease, AI client hoặc IPC. nhan_viec cấp SDKEngine
và đường DOCX/out_dir DEMO riêng theo việc. Hai metadata phan_hoi/tham_so
do Core cấp; ACK phản hồi nguồn có tep_id. Đây chỉ là seam giả lập.
Không dọn out_dir: quy tắc worker cấm xóa; Core/lead giữ quyền dọn sau ACK.
"""

from __future__ import annotations

import io
import json
import socket
import threading
import time

from ...sdk_core.bootstrap import Bootstrap, LoiBootstrap, PROTOCOL, gui_thong_diep
from ...sdk_core.engine import LoiEngine, SDKEngine
from ...sdk_core.ngu_canh import _xoa_loi
from .docx import read_contract
from .tham_so import DANH_MUC_ID, DANH_MUC_SHA256, TrichXuat, anh_xa_tham_so, danh_muc_xd

PHIEN_BAN = '0.1.0-demo.1'


class BackendTrichXuat:
    """Chỉ AI được tiêm cho test; không mặc định tạo provider thật."""

    def __init__(self, *, ai):
        TrichXuat._kiem_ai(ai, None)
        self.ai = ai

    def san_sang(self):
        TrichXuat._kiem_ai(self.ai, None)
        return len(danh_muc_xd()) == 37

    def xu_ly(self, dau_vao):
        if (dau_vao['loai_hop_dong'], dau_vao['danh_muc_id'],
                dau_vao['danh_muc_sha256']) != ('XD', DANH_MUC_ID, DANH_MUC_SHA256):
            raise ValueError('TRICH_DANH_MUC_KHONG_HO_TRO')
        tx = TrichXuat(ai=self.ai, cloud=None, out_dir=dau_vao['out_dir'])
        van_ban = read_contract(dau_vao['docx'])['text']
        return tx.xu_ly(dau_vao['docx']), van_ban


def _ban_giao(sdk, value, *, ten, metadata):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
    with io.BytesIO(raw) as luong:
        while True:
            luong.seek(0)
            try:
                return sdk.ghi_ket_qua(luong=luong, ten=ten,
                    du_lieu=metadata['du_lieu_ket_qua'],
                    revision_tep_truoc=metadata['revision_tep_truoc'])
            except LoiEngine as exc:
                # Core có thể đã đọc hết trước khi mất ACK; không trích lại.
                _xoa_loi(exc)
            time.sleep(0.1)


def xu_ly_viec(sdk, *, backend):
    if not isinstance(sdk, SDKEngine):
        raise TypeError('Cần SDKEngine do Core cấp')
    dau_vao = sdk.doc_dau_vao()
    phan_hoi, van_ban = backend.xu_ly(dau_vao)
    ack = _ban_giao(sdk, phan_hoi, ten='phan-hoi-nguon.json',
                    metadata=dau_vao['phan_hoi'])
    ket_qua = anh_xa_tham_so(phan_hoi, tep_id=dau_vao['tep_id'],
        phan_hoi_nguon_tep_id=ack['tep_id'], van_ban=van_ban,
        loai_hop_dong=dau_vao['loai_hop_dong'],
        danh_muc_id=dau_vao['danh_muc_id'],
        danh_muc_sha256=dau_vao['danh_muc_sha256'])
    return _ban_giao(sdk, ket_qua, ten='tham-so.json', metadata=dau_vao['tham_so'])


class _VongNhan:
    """Một worker tuần tự; drain chờ xử lý và cả hai ACK của Core."""

    def __init__(self, bootstrap, nhan_viec, backend):
        self.bootstrap, self.nhan_viec, self.backend = bootstrap, nhan_viec, backend
        self.khoa = threading.Lock()
        self.dung = self.loi = False
        self._giu_khi_loi = threading.Event()
        self.worker = threading.Thread(target=self._chay, name='trich-demo')

    def bat_dau(self):
        self.bootstrap.socket.settimeout(0.1)
        self.worker.start()

    def _chay(self):
        try:
            while True:
                with self.khoa:
                    if self.dung:
                        return
                try:
                    conn, _ = self.bootstrap.accept()
                except socket.timeout:
                    continue
                except LoiBootstrap as exc:
                    if exc.ma == 'CHUA_CO_QUYEN_ACCEPT':
                        return
                    raise
                with conn:
                    with self.khoa:
                        if self.dung:
                            return
                        # Việc đăng ký trước ngừng nhận phải được drain chờ.
                    conn.settimeout(None)
                    try:
                        sdk = self.nhan_viec(conn, self.bootstrap.bo_doc)
                        xu_ly_viec(sdk, backend=self.backend)
                    except Exception as exc:
                        _xoa_loi(exc)
                        self.loi = True
                        self.ngung_accept()
                        self._giu_khi_loi.wait()
                        return
        except Exception as exc:
            _xoa_loi(exc)
            self.loi = True

    def ngung_accept(self):
        with self.khoa:
            self.dung = True

    def drain(self):
        self.worker.join(0.1)
        if self.loi:
            self._giu_khi_loi.wait(0.1)
        return not self.worker.is_alive() and not self.loi


def chay(*, kiem_chu_ky, nhan_viec, backend):
    """Readiness contracts=[]: mock không chứng minh AI thật/độ chính xác."""
    if not callable(kiem_chu_ky) or not callable(nhan_viec):
        raise TypeError('Cần bộ kiểm chữ ký và seam nhận việc của Core')
    bootstrap = Bootstrap.nhan(kiem_chu_ky=kiem_chu_ky)
    vong = _VongNhan(bootstrap, nhan_viec, backend)
    bat_dau = False
    try:
        bootstrap.bao_san_sang(phien_ban=PHIEN_BAN, contracts=[],
                               kiem_san_sang=backend.san_sang)
        vong.bat_dau()
        bat_dau = True
        try:
            bootstrap.cho_thu_hoi(ngung_accept=vong.ngung_accept, drain=vong.drain)
        except LoiBootstrap as exc:
            if exc.ma != 'DRAIN_CHUA_XONG':
                raise
            _xoa_loi(exc)
            gui_thong_diep(bootstrap._ra,
                {'protocol': PROTOCOL, 'kieu': 'drain_chua_xong'})
            while not vong.drain():
                pass
            bootstrap.socket.close()
            gui_thong_diep(bootstrap._ra,
                {'protocol': PROTOCOL, 'kieu': 'da_thu_hoi'})
    finally:
        if bat_dau:
            vong.ngung_accept()
            while not vong.drain():
                pass
        bootstrap.socket.close()
