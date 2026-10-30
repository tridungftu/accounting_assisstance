"""SDK module tối thiểu; mọi lời gọi dùng GiaoDich đang mở của caller.

Không nhận danh tính từ payload, không commit hoặc giữ connection sau request.
Tệp đọc qua KhoTep Core; cửa tải lên/bàn giao bytes vẫn thuộc Core G2-10.
"""

from __future__ import annotations

import time
from uuid import UUID

from ..core import su_kien as _bus, tai_lieu as _tl, tiep_nhan as _tn, viec as _viec
from .giao_dich import GiaoDich, LoiGiaoDich
from .ngu_canh import NguCanh, _DA_KIEM, _xoa_loi


class LoiDichVu(RuntimeError):
    def __init__(self, ma='SDK_DICH_VU', http_status=400):
        self.ma, self.http_status = ma, http_status
        super().__init__(ma)


class _DichVu:
    __slots__ = ()

    def __repr__(self):
        return 'DichVuSDK(<an>)'

    def __reduce__(self):
        raise TypeError('Không serialize dịch vụ SDK')


def _ctx(tx):
    if not isinstance(tx, GiaoDich):
        raise LoiGiaoDich('SDK_NGU_CANH', 401)
    tx._kiem()
    ctx = tx.ngu_canh
    if (not isinstance(ctx, NguCanh) or ctx._da_kiem is not _DA_KIEM
            or time.time() >= ctx.hieu_luc_den):
        raise LoiGiaoDich('SDK_NGU_CANH', 401)
    return ctx


def _danh_tinh(ctx):
    return dict(ma=ctx.ma, module=ctx.module, phap_nhan_id=ctx.phap_nhan_id,
                hanh_dong=ctx.hanh_dong)


def _goi(tx, ham, **tham_so):
    ctx = _ctx(tx)
    if set(tham_so) & {'ma', 'module', 'phap_nhan_id', 'hanh_dong', 'nguoi_dung_id',
                        'actor', 'request_id', 'viec_id', 'the_he'}:
        raise LoiDichVu('SDK_DANH_TINH', 403)
    loi = None
    try:
        return ham(tx, **tham_so, **_danh_tinh(ctx))
    except Exception as exc:
        # GiaoDich đã lọc driver. Vẫn xóa lỗi từ callback/KhoTep và chain Core.
        ma = getattr(exc, 'ma', '')
        if ma in _tl._LOI or ma in _viec._LOI or ma in _tn._LOI or ma in _bus._LOI:
            loi = ma
        _xoa_loi(exc)
    finally:
        tham_so = ham = ma = None
    raise LoiDichVu(loi or 'SDK_DICH_VU') from None


def _sql(tx, cau, ts):
    _ctx(tx)
    status = 500
    loi = 'SDK_DICH_VU'
    try:
        return tx.execute(cau, ts).fetchone()[0]
    except Exception as exc:
        chinh = getattr(getattr(exc, 'diag', None), 'message_primary', None)
        if isinstance(chinh, str) and (chinh in _tl._LOI or chinh in _viec._LOI):
            loi = chinh
        state = getattr(exc, 'sqlstate', None)
        status = 403 if state == '42501' else 409 if state in {'40001', '55000'} else 400 if (
            isinstance(state, str) and state.startswith(('22', '23'))) else 500
        _xoa_loi(exc)
    finally:
        cau = ts = state = chinh = None
    raise LoiDichVu(loi, status) from None


class _KetQua(_DichVu):
    __slots__ = ()

    def ghi(self, tx, *, tai_lieu_id, du_lieu, giu_viec=None):
        # Nợ §3.3: bổ sung khoa chống trùng ở lát tiếp nhận/Dispatcher sau.
        ctx = _ctx(tx)
        data = _tl._truong(du_lieu, {'tep_id', 'bien_the', 'ma_contract',
            'phien_ban_contract', 'trang_thai', 'ly_do', 'revision_truoc', 'nguon'}, {'goc_id'})
        _tl._bien_the(data['bien_the'])
        _tl._so(data['revision_truoc'])
        ts = (ctx.ma.lay_de_truyen(), ctx.module, ctx.phap_nhan_id, ctx.hanh_dong)
        job = (None, None)
        if giu_viec is not None:
            if (not isinstance(giu_viec, _viec.GiuViec) or giu_viec.module != ctx.module
                    or giu_viec.phap_nhan_id != ctx.phap_nhan_id
                    or giu_viec.hanh_dong != ctx.hanh_dong):
                raise LoiDichVu('SDK_DANH_TINH', 403)
            # Core kiểm lại phiên của lease/thế hệ và lấy bước/lần thử từ hàng việc.
            ts = (giu_viec.ma.lay_de_truyen(), ctx.module, ctx.phap_nhan_id, ctx.hanh_dong)
            job = (giu_viec.viec_id, giu_viec.the_he)
        # SQL kiểm lại schema, nguồn/hash/revision và gắn nguồn Core đã xác minh.
        try:
            return _sql(tx, 'SELECT loi_tai_lieu.ghi_ket_qua_v2(%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)',
                (*ts, UUID(str(tai_lieu_id)), _tn._json(data), ctx.request_id, *job))
        finally:
            ts = job = None

    def tao_revision(self, tx, *, tai_lieu_id, ket_qua_id, revision_truoc, du_lieu):
        # Kết quả cũ bất biến; SQL đối chiếu gốc và revision hiện hành.
        if set(du_lieu) & {'goc_id', 'revision_truoc'}:
            raise LoiDichVu('SDK_DAU_VAO')
        return self.ghi(tx, tai_lieu_id=tai_lieu_id, du_lieu={**du_lieu,
            'goc_id': str(UUID(str(ket_qua_id))), 'revision_truoc': revision_truoc})

    def lay(self, tx, *, tai_lieu_id, ket_qua_id, bien_the):
        view = _goi(tx, _tl.lay, tai_lieu_id=tai_lieu_id, bien_the=bien_the)
        for row in view['ket_qua']:
            if row['id'] == str(UUID(str(ket_qua_id))):
                return row
        raise LoiDichVu('TAI_LIEU_KHONG_THAY', 404)


class _Tep(_DichVu):
    __slots__ = ('__kho',)

    def __init__(self, kho):
        self.__kho = kho

    def tham_chieu(self, tx, *, tai_lieu_id, tep_id, bien_the):
        return _goi(tx, self.__kho.tham_chieu, tai_lieu_id=tai_lieu_id,
                    tep_id=tep_id, bien_the=bien_the)

    def mo_doc(self, tx, *, tai_lieu_id, tep_id, bien_the):
        # KhoTep kiểm quyền hiện hành/hash trước khi trả luồng có thể đóng.
        return _goi(tx, self.__kho.mo_doc, tai_lieu_id=tai_lieu_id,
                    tep_id=tep_id, bien_the=bien_the)


class _Viec(_DichVu):
    __slots__ = ()

    def tao(self, tx, **tham_so):
        return _goi(tx, _viec.tao_viec, **tham_so)


class _Audit(_DichVu):
    __slots__ = ()

    def ghi(self, tx, *, doi_tuong, doi_tuong_id, ket_luan, phien_ban_contract='1'):
        # Nợ: doi_tuong hiện do caller chọn (Core chỉ kiểm regex và MTQ).
        ctx = _ctx(tx)
        return _sql(tx, 'SELECT loi.ghi_kiem_toan_v2(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (ctx.ma.lay_de_truyen(), ctx.module, ctx.phap_nhan_id, ctx.hanh_dong,
             doi_tuong, UUID(str(doi_tuong_id)), ket_luan, ctx.request_id, phien_ban_contract))


class _BienNhan(_DichVu):
    __slots__ = ()

    def tra(self, tx, **tham_so):
        ctx = _ctx(tx)
        return _goi(tx, _tn.tra_thao_tac, operation=ctx.operation, khoa=ctx.khoa, **tham_so)

    def ghi(self, tx, **tham_so):
        ctx = _ctx(tx)
        return _goi(tx, _tn.ghi_thao_tac, operation=ctx.operation, khoa=ctx.khoa, **tham_so)


class _SuKien(_DichVu):
    __slots__ = ()

    def phat(self, tx, *, loai, phien_ban, tham_chieu, khoa):
        return _goi(tx, _bus.phat, loai=loai, phien_ban=phien_ban,
                    tham_chieu=tham_chieu, khoa=khoa)

    def nhan(self, tx, *, loai=None, gioi_han=100):
        return _goi(tx, _bus.nhan, loai=loai, gioi_han=gioi_han)

    def xac_nhan(self, tx, su_kien_id):
        return _goi(tx, _bus.ack, su_kien_id=su_kien_id)


ket_qua, viec, audit, bien_nhan, su_kien = _KetQua(), _Viec(), _Audit(), _BienNhan(), _SuKien()


class DichVu(_DichVu):
    """Bootstrap gắn KhoTep tin cậy; request không được chọn kho hay danh tính."""

    __slots__ = ('tep', 'ket_qua', 'viec', 'audit', 'bien_nhan', 'su_kien')

    def __init__(self, kho_tep):
        self.tep = _Tep(kho_tep)
        self.ket_qua, self.viec, self.audit = ket_qua, viec, audit
        self.bien_nhan, self.su_kien = bien_nhan, su_kien
