"""OCR-4a: khung chạy giả lập, không phải capability OCR đã được công bố.

Dùng Bootstrap G2-21; Core sở hữu launcher, listener và Windows Job.
nhan_viec là seam do hồ sơ chạy/test cấp: kiểm request bằng bo_doc rồi trả
SDKEngine của việc được Core cấp. Không dựng IPC/lease hoặc cổng OCR khác.
Backend dưới đây chỉ mã hóa văn bản DEMO, không đọc tệp hay gọi ABBYY.
"""

from __future__ import annotations

import io
import socket
import threading

from ...sdk_core.bootstrap import Bootstrap, LoiBootstrap
from ...sdk_core.engine import SDKEngine
from ...sdk_core.ngu_canh import _xoa_loi


PHIEN_BAN = '0.1.0-demo.1'


class BackendOCRGia:
    def san_sang(self):
        return True

    def xu_ly(self, van_ban_demo):
        if not isinstance(van_ban_demo, str) or len(van_ban_demo) > 16384:
            raise ValueError('Cần văn bản DEMO tối đa 16384 ký tự')
        return van_ban_demo.encode('utf-8')


def xu_ly_viec(sdk, *, backend):
    """Chỉ dữ liệu DEMO; metadata/lease do Core giả cấp, không tự gắn nguồn.

    Bàn giao OCR thật/hạn mức thuộc OCR-5a. Lát này dùng kênh Core giả để
    kiểm drain chờ tới khi lời gọi ghi_ket_qua trả về, kể cả sau xử lý.
    """
    if not isinstance(sdk, SDKEngine):
        raise TypeError('Cần SDKEngine do Core cấp')
    dau_vao = sdk.doc_dau_vao()
    raw = backend.xu_ly(dau_vao['van_ban_demo'])
    with io.BytesIO(raw) as luong:
        return sdk.ghi_ket_qua(luong=luong, ten='ocr-demo.txt',
            du_lieu=dau_vao['du_lieu_ket_qua'],
            revision_tep_truoc=dau_vao['revision_tep_truoc'])


class _VongNhan:
    """Một worker tuần tự; ngừng nhận dưới cùng khóa với đăng ký việc.

    Không shutdown listener dùng chung với Core. Timeout accept chỉ để
    đánh thức worker; drain không đặt hạn hủy hoặc kill việc đang chạy.
    """

    def __init__(self, bootstrap, nhan_viec, backend):
        self.bootstrap, self.nhan_viec, self.backend = bootstrap, nhan_viec, backend
        self.khoa = threading.Lock()
        self.dung = False
        self.loi = False
        # Không tự giải phóng việc chưa bàn giao; giữ để Core/Admin xử lý.
        self._giu_khi_loi = threading.Event()
        self.worker = threading.Thread(target=self._chay, name='ocr-demo')

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
                    # Bootstrap thu quyền trước callback ngung_accept.
                    if exc.ma == 'CHUA_CO_QUYEN_ACCEPT':
                        return
                    raise
                with conn:
                    with self.khoa:
                        if self.dung:
                            return
                        # Việc đã được đăng ký trước ngừng nhận: drain phải chờ.
                    # Timeout listener chỉ đánh thức accept, không được cắt ACK.
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
        self.worker.join()
        return not self.loi


def chay(*, kiem_chu_ky, nhan_viec, backend=None):
    """Entrypoint tiêm seam, không có CLI/cấu hình tự mở backend thật.

    Readiness contracts=[]: listener/khung giả sẵn sàng không chứng minh
    ocr.trich_van_ban@1 hoặc ocr.trich_bang@1 đã hoạt động.
    """
    if not callable(kiem_chu_ky) or not callable(nhan_viec):
        raise TypeError('Cần bộ kiểm chữ ký và seam nhận việc của Core')
    backend = BackendOCRGia() if backend is None else backend
    bootstrap = Bootstrap.nhan(kiem_chu_ky=kiem_chu_ky)
    vong = _VongNhan(bootstrap, nhan_viec, backend)
    bat_dau = False
    try:
        bootstrap.bao_san_sang(phien_ban=PHIEN_BAN, contracts=[],
                               kiem_san_sang=backend.san_sang)
        vong.bat_dau()
        bat_dau = True
        bootstrap.cho_thu_hoi(ngung_accept=vong.ngung_accept, drain=vong.drain)
    finally:
        if bat_dau:
            vong.ngung_accept()
            if vong.drain():
                bootstrap.socket.close()
        else:
            bootstrap.socket.close()
