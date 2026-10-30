"""AI-4a: khung chạy provider giả, không công bố capability ai.hoi@1.

Theo vòng đời OCR-4a: Bootstrap G2-21 nhận listener/Job do Core sở hữu;
nhan_viec là seam Core cấp SDKEngine, không phải giao thức IPC mới.
Chỉ dùng DTO AI-1a; không tạo cổng AI, model Local, client hay kết nối mạng.
Local thật không mặc định luôn chạy; launcher/provider thật thuộc AI-4b.
"""

from __future__ import annotations

from dataclasses import asdict
import io
import json
import socket
import threading

from ...sdk_core.bootstrap import Bootstrap, LoiBootstrap
from ...sdk_core.engine import SDKEngine
from ...sdk_core.ngu_canh import _xoa_loi
from .dto import KetQuaAI, TruongAI, YeuCauAI


PHIEN_BAN = '0.1.0-demo.1'


class ProviderAIGia:
    """Echo DEMO xác định được; LOCAL dưới đây chỉ là nguồn giả lập."""

    def san_sang(self):
        return True

    def goi(self, yeu_cau):
        if not isinstance(yeu_cau, YeuCauAI):
            raise TypeError('Cần DTO YeuCauAI')
        if not isinstance(yeu_cau.van_ban, str) or len(yeu_cau.van_ban) > 16384:
            raise ValueError('Cần văn bản DEMO tối đa 16384 ký tự')
        truong = {ten: TruongAI(ten, yeu_cau.van_ban, yeu_cau.van_ban, 'LOCAL')
                  for ten in (yeu_cau.truong or ('van_ban_demo',))}
        return KetQuaAI(yeu_cau.loai_viec, 'VANG', truong, 'LOCAL',
                        'Kết quả DEMO từ provider giả, chưa được duyệt.',
                        ly_do=('GIA_LAP',))


def xu_ly_viec(sdk, *, provider):
    """Đầu vào/metadata DEMO do Core cấp; chờ Core nhận xong mới kết thúc.

    Đây không là adapter JSON Schema ai.hoi@1/chỉ Local (AI-1b/AI-2).
    Không tự gắn nguồn hoặc tạo lease; không fallback sang provider thật.
    """
    if not isinstance(sdk, SDKEngine):
        raise TypeError('Cần SDKEngine do Core cấp')
    dau_vao = sdk.doc_dau_vao()
    yeu_cau = dau_vao['yeu_cau_demo']
    if not isinstance(yeu_cau, YeuCauAI):
        raise TypeError('Cần DTO YeuCauAI')
    ket_qua = provider.goi(yeu_cau)
    if not isinstance(ket_qua, KetQuaAI):
        raise TypeError('Cần DTO KetQuaAI')
    raw = json.dumps(asdict(ket_qua), ensure_ascii=False, allow_nan=False).encode('utf-8')
    with io.BytesIO(raw) as luong:
        return sdk.ghi_ket_qua(luong=luong, ten='ai-demo.json',
            du_lieu=dau_vao['du_lieu_ket_qua'],
            revision_tep_truoc=dau_vao['revision_tep_truoc'])


class _VongNhan:
    """Một worker tuần tự; ngừng nhận và drain cả lời gọi bàn giao Core.

    Không shutdown listener dùng chung với Core; không kill việc khi drain.
    """

    def __init__(self, bootstrap, nhan_viec, provider):
        self.bootstrap, self.nhan_viec, self.provider = bootstrap, nhan_viec, provider
        self.khoa = threading.Lock()
        self.dung = False
        self.loi = False
        self.worker = threading.Thread(target=self._chay, name='ai-demo')

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
                        # Đã đăng ký việc trước ngừng nhận: drain phải chờ.
                    conn.settimeout(5)
                    sdk = self.nhan_viec(conn, self.bootstrap.bo_doc)
                    # Việc đã nhận phải chờ Core ACK, kể cả khi đang drain.
                    conn.settimeout(None)
                    xu_ly_viec(sdk, provider=self.provider)
        except Exception as exc:
            _xoa_loi(exc)
            self.loi = True

    def ngung_accept(self):
        with self.khoa:
            self.dung = True

    def drain(self):
        self.worker.join()
        return not self.loi


def chay(*, kiem_chu_ky, nhan_viec, provider=None):
    """Chỉ khởi động khi Core gọi; readiness giả có contracts=[]."""
    if not callable(kiem_chu_ky) or not callable(nhan_viec):
        raise TypeError('Cần bộ kiểm chữ ký và seam nhận việc của Core')
    provider = ProviderAIGia() if provider is None else provider
    bootstrap = Bootstrap.nhan(kiem_chu_ky=kiem_chu_ky)
    vong = _VongNhan(bootstrap, nhan_viec, provider)
    bat_dau = False
    try:
        bootstrap.bao_san_sang(phien_ban=PHIEN_BAN, contracts=[],
                               kiem_san_sang=provider.san_sang)
        vong.bat_dau()
        bat_dau = True
        bootstrap.cho_thu_hoi(ngung_accept=vong.ngung_accept, drain=vong.drain)
    finally:
        if bat_dau:
            vong.ngung_accept()
        if not bat_dau or vong.drain():
            bootstrap.socket.close()
