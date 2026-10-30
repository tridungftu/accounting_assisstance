"""G2-14: cửa Core quanh hàng việc XS-2, dùng chính transaction của caller.

Giữ ngữ nghĩa ha_tang.hang_viec: dedupe, lease, retry an toàn, dừng hợp tác.
Engine gọi kênh Core; module chỉ nhận GiuViec theo login/instance đã xác thực.
Core phải xác minh instance và đối chiếu bằng chứng trước ``xep_lai``.
Không giữ mã HTTP để chạy nền. Không tự connect/commit/rollback hoặc mở tx.
Khi lưu kết quả: ghi nghiệp vụ rồi ``ket_thuc`` trong CÙNG tx; để exception
thoát transaction khi mất lease. Tác động ngoài CSDL không có exactly-once.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
import re
import secrets
from uuid import UUID

from .phien import MaBiMat, _ma
from .tai_lieu import _ngu_canh
from .tiep_nhan import _tx


class LoiViec(RuntimeError):
    def __init__(self, ma):
        self.ma = ma
        self.http_status = (409 if ma in {'VIEC_MAT_LEASE', 'VIEC_CAS', 'VIEC_KHOA_KHAC_NOI_DUNG'} else
                            404 if ma == 'VIEC_KHONG_THAY' else
                            403 if ma in {'VIEC_PHIEN', 'VIEC_MTQ', 'VIEC_CONG_TAC', 'VIEC_CHI_CORE'} else 400)
        super().__init__('Thao tác việc thất bại (' + ma + ')')


_LOI = {'VIEC_MAT_LEASE', 'VIEC_CAS', 'VIEC_KHOA_KHAC_NOI_DUNG', 'VIEC_KHONG_THAY',
        'VIEC_PHIEN', 'VIEC_MTQ', 'VIEC_CONG_TAC', 'VIEC_CHI_CORE', 'VIEC_DAU_VAO',
        'VIEC_CAN_DOI_CHIEU', 'VIEC_CAN_READ_COMMITTED'}


@dataclass(frozen=True, repr=False)
class GiuViec:
    """Handle nội bộ; không trả vào HTTP, JSON, pickle hoặc log.

    Mã là MaBiMat nên cả dataclasses.asdict cũng không xuất mã rõ.
    SQL xác minh lại mọi trường, kể cả khi caller tự dựng handle giả.
    """

    viec_id: UUID
    buoc_viec_id: UUID
    lan_thu_id: UUID
    phap_nhan_id: UUID
    module: str
    hanh_dong: str
    instance_id: UUID
    the_he: int
    giu_den: datetime
    ma: MaBiMat

    def __repr__(self):
        return 'GiuViec(<an>)'

    def __reduce__(self):
        raise TypeError('Không serialize GiuViec')


def _goi(conn, cau, ts):
    ma = 'VIEC_THAT_BAI'
    try:
        row = conn.execute(cau, ts).fetchone()
        return row['r'] if isinstance(row, Mapping) else row[0]
    except Exception as exc:
        chinh = getattr(getattr(exc, 'diag', None), 'message_primary', None)
        if isinstance(chinh, str) and chinh in _LOI:
            ma = chinh
    ts = None
    # Raise ngoài except: không giữ exception driver chứa mã/DSN ở context.
    raise LoiViec(ma)


def _so(v, nho, lon):
    if type(v) is not int or not nho <= v <= lon:
        raise ValueError('Số nguyên ngoài giới hạn')
    return v


def _ctx(conn, ctx):
    _tx(conn)
    ma, module, pn, hd, viec, the_he = _ngu_canh(**ctx)
    if viec is not None or the_he is not None:
        raise ValueError('Cần ngữ cảnh Core đã xác minh, không dùng lease để tạo/nhận việc')
    return ma, module, pn, hd


def _giu(conn, giu):
    _tx(conn)
    if not isinstance(giu, GiuViec):
        raise ValueError('Cần GiuViec')
    _so(giu.the_he, 1, 2**63-1)
    return (_ma(giu.ma), giu.module, UUID(str(giu.phap_nhan_id)), giu.hanh_dong,
            UUID(str(giu.viec_id)), UUID(str(giu.instance_id)), giu.the_he)


def tao_viec(conn, loai: str, phien_ban: int, khoa_dedupe: str, tham_chieu_id: UUID, *,
             bang_tham_chieu: str, phien_ban_contract='1', co_tac_dong_ngoai=False,
             thu_lai_an_toan=False, toi_da_lan_thu=3, thu_lai_giay=60, giu_ngay=None, **ctx):
    """Tạo/dedupe theo pháp nhân/module/khóa; chỉ giữ UUID tham chiếu."""
    ts = _ctx(conn, ctx)
    if (not isinstance(loai, str) or not re.fullmatch('[A-Z][A-Z0-9_-]{0,79}', loai)
            or not isinstance(khoa_dedupe, str) or not 1 <= len(khoa_dedupe) <= 200
            or khoa_dedupe != khoa_dedupe.strip()
            or not isinstance(bang_tham_chieu, str) or not bang_tham_chieu.strip()
            or not isinstance(phien_ban_contract, str) or not phien_ban_contract.strip()
            or type(co_tac_dong_ngoai) is not bool or type(thu_lai_an_toan) is not bool
            or ts[3].split(':')[2] not in {'LAP', 'SUA', 'DUYET'}):
        raise ValueError('Thông tin việc không hợp lệ')
    _so(phien_ban, 1, 2**31-1)
    _so(toi_da_lan_thu, 1, 100)
    _so(thu_lai_giay, 1, 86400)
    if giu_ngay is not None:
        _so(giu_ngay, 1, 36500)
    return _goi(conn, '''SELECT loi.viec_tao(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS r''',
                (*ts, loai, phien_ban, khoa_dedupe, bang_tham_chieu, UUID(str(tham_chieu_id)),
                 phien_ban_contract, co_tac_dong_ngoai, thu_lai_an_toan, toi_da_lan_thu, thu_lai_giay, giu_ngay))


def nhan(conn, worker_id: UUID, *, dang_nhap_csdl: str, lease_giay=120, **ctx) -> GiuViec | None:
    """Core cấp mã mới mỗi lease; chỉ trả handle sau khi caller commit."""
    ts = _ctx(conn, ctx)
    _so(lease_giay, 1, 3600)
    if not isinstance(dang_nhap_csdl, str) or not dang_nhap_csdl.strip():
        raise ValueError('Cần login runtime nhận việc')
    ma = MaBiMat(secrets.token_urlsafe(32))
    r = _goi(conn, 'SELECT loi.viec_nhan(%s,%s,%s,%s,%s,%s,%s,%s) AS r',
             (*ts, UUID(str(worker_id)), _ma(ma), dang_nhap_csdl, lease_giay))
    if r is None:
        return None
    return GiuViec(*(UUID(str(r[k])) for k in ('viec_id', 'buoc_viec_id', 'lan_thu_id', 'phap_nhan_id')),
                   r['module'], r['hanh_dong'], UUID(str(r['instance_id'])), int(r['the_he']),
                   datetime.fromisoformat(r['giu_den']), ma)


def gia_han(conn, giu_viec: GiuViec, *, lease_giay=120) -> GiuViec:
    ts = _giu(conn, giu_viec)
    _so(lease_giay, 1, 3600)
    den = _goi(conn, 'SELECT loi.viec_gia_han(%s,%s,%s,%s,%s,%s,%s,%s) AS r', (*ts, lease_giay))
    return replace(giu_viec, giu_den=den)


def ket_thuc(conn, giu_viec: GiuViec, trang_thai='XONG', *, ket_qua_id=None, ma_loi=None) -> bool:
    ts = _giu(conn, giu_viec)
    if (trang_thai not in {'XONG', 'LOI', 'DA_DUNG', 'CHUA_RO', 'CHO'}
            or (trang_thai in {'LOI', 'CHUA_RO', 'CHO'} and ma_loi is None)
            or (ma_loi is not None and (not isinstance(ma_loi, str)
                or not re.fullmatch('[A-Z][A-Z0-9_]{0,79}', ma_loi)))
            or (trang_thai != 'XONG' and ket_qua_id is not None)):
        raise ValueError('Kết luận lần thử không hợp lệ')
    return _goi(conn, 'SELECT loi.viec_ket_thuc(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS r',
                (*ts, trang_thai, None if ket_qua_id is None else UUID(str(ket_qua_id)), ma_loi))


def thu_lai(conn, giu_viec: GiuViec, ma_loi: str) -> bool:
    """Chỉ khi worker đã chứng minh lỗi an toàn; chưa rõ phải dùng CHUA_RO."""
    return ket_thuc(conn, giu_viec, 'CHO', ma_loi=ma_loi)


def trang_thai_lease(conn, giu_viec: GiuViec):
    return _goi(conn, 'SELECT loi.viec_trang_thai_lease(%s,%s,%s,%s,%s,%s,%s) AS r', _giu(conn, giu_viec))


def phuc_hoi(conn, *, instance_id=None, **ctx) -> int:
    """Core restart: truyền instance cũ đã xác minh; None chỉ quét lease hết hạn.

    Tối đa 100 việc/lượt; gọi lại đến 0. GIAN_DOAN/CHUA_RO không tự xếp lại.
    """
    ts = _ctx(conn, ctx)
    return _goi(conn, 'SELECT loi.viec_phuc_hoi(%s,%s,%s,%s,%s) AS r',
                (*ts, None if instance_id is None else UUID(str(instance_id))))


def _cas(row_version):
    if not isinstance(row_version, str) or not re.fullmatch('[1-9][0-9]{0,18}', row_version):
        raise ValueError('row_version phải là chuỗi số nguyên dương')
    return _so(int(row_version), 1, 2**63-1)


def yeu_cau_dung(conn, viec_id: UUID, *, row_version: str, **ctx) -> bool:
    ts = _ctx(conn, ctx)
    return _goi(conn, 'SELECT loi.viec_yeu_cau_dung(%s,%s,%s,%s,%s,%s) AS r',
                (*ts, UUID(str(viec_id)), _cas(row_version)))


def xep_lai(conn, viec_id: UUID, *, row_version: str, ma_doi_chieu: UUID, **ctx) -> bool:
    """Core gọi SAU đối chiếu bằng chứng/biên nhận và kiểm contract retry an toàn."""
    ts = _ctx(conn, ctx)
    return _goi(conn, 'SELECT loi.viec_xep_lai(%s,%s,%s,%s,%s,%s,%s) AS r',
                (*ts, UUID(str(viec_id)), _cas(row_version), UUID(str(ma_doi_chieu))))
