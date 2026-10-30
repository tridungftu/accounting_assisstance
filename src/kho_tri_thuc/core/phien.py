"""Mã CSDL bí mật; caller giữ kết nối, transaction và kênh trao mã.

Core phải xác thực/kiểm quyền trước cấp mã; SDK chỉ nhận mã ủy nhiệm.
Không đặt GUC danh tính, không log, không commit hoặc mở kết nối.
Lỗi driver được thay bằng lỗi cố định, không giữ exception chứa tham số.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import secrets
from uuid import UUID


class LoiPhien(RuntimeError):
    pass


class MaBiMat:
    __slots__ = ('__gia_tri',)

    def __init__(self, gia_tri: str):
        self.__gia_tri = gia_tri

    def __repr__(self):
        return 'MaBiMat(<an>)'

    def __str__(self):
        return '<ma bi mat>'

    def lay_de_truyen(self) -> str:
        """Chỉ dùng cho bind/kênh bootstrap được bảo vệ; không log kết quả."""
        return self.__gia_tri


@dataclass(frozen=True)
class PhienDaCap:
    id: UUID
    ma: MaBiMat


@dataclass(frozen=True)
class DanhTinhDaXacMinh:
    phien_id: UUID
    nguoi_dung_id: UUID
    module: str
    phap_nhan_id: UUID
    hanh_dong: str
    viec_id: UUID | None
    the_he: int | None
    hieu_luc_den: datetime


def _goi(ket_noi, cau_sql, tham_so, *, lay_dong=True):
    try:
        con_tro = ket_noi.execute(cau_sql, tham_so)
        return con_tro.fetchone() if lay_dong else None
    except Exception:
        pass
    # Raise ngoài except: không lưu exception driver trong __context__/__cause__.
    raise LoiPhien('Thao tác phiên thất bại')


def _ma(ma):
    if not isinstance(ma, MaBiMat):
        raise ValueError('Cần mã bí mật')
    return ma.lay_de_truyen()


def cap_phien(ket_noi, *, nguoi_dung_id: UUID, module: str, phap_nhan_id: UUID,
              dang_nhap_csdl: str, pham_vi_hanh_dong, hieu_luc_den: datetime,
              loai='NGUOI_DUNG', ma_goc: MaBiMat | None = None,
              viec_id: UUID | None = None, the_he: int | None = None) -> PhienDaCap:
    if (not isinstance(hieu_luc_den, datetime) or hieu_luc_den.utcoffset() is None
            or not isinstance(module, str) or not module.strip()
            or not isinstance(dang_nhap_csdl, str) or not dang_nhap_csdl.strip()
            or not isinstance(pham_vi_hanh_dong, (list, tuple)) or not pham_vi_hanh_dong
            or any(not isinstance(h, str) or not h.strip() or h == '*' for h in pham_vi_hanh_dong)):
        raise ValueError('Tham số cấp phiên không hợp lệ')
    if (loai not in ('NGUOI_DUNG', 'UY_NHIEM_PHIEN', 'UY_NHIEM_VIEC')
            or (loai == 'UY_NHIEM_PHIEN' and ma_goc is None)
            or (loai == 'NGUOI_DUNG' and ma_goc is not None)
            or (loai == 'UY_NHIEM_VIEC' and (viec_id is None or type(the_he) is not int or the_he <= 0))
            or (loai != 'UY_NHIEM_VIEC' and (viec_id is not None or the_he is not None))):
        raise ValueError('Loại phiên hoặc thế hệ không hợp lệ')
    ma = MaBiMat(secrets.token_urlsafe(32))
    dong = _goi(ket_noi, '''SELECT loi.cap_phien(
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', (
        _ma(ma), UUID(str(nguoi_dung_id)), module, UUID(str(phap_nhan_id)),
        dang_nhap_csdl, list(pham_vi_hanh_dong), hieu_luc_den, loai,
        None if ma_goc is None else _ma(ma_goc),
        None if viec_id is None else UUID(str(viec_id)), the_he))
    return PhienDaCap(dong[0], ma)


def xac_minh_phien(ket_noi, *, ma: MaBiMat, module: str, phap_nhan_id: UUID,
                   hanh_dong: str, viec_id: UUID | None = None,
                   the_he: int | None = None) -> DanhTinhDaXacMinh | None:
    dong = _goi(ket_noi, '''SELECT * FROM loi.xac_minh_phien(%s, %s, %s, %s, %s, %s)''', (
        _ma(ma), module, UUID(str(phap_nhan_id)), hanh_dong,
        None if viec_id is None else UUID(str(viec_id)), the_he))
    return None if dong is None else DanhTinhDaXacMinh(*dong)


def thu_hoi_phien(ket_noi, *, ma: MaBiMat) -> None:
    _goi(ket_noi, 'SELECT loi.thu_hoi_phien(%s)', (_ma(ma),), lay_dong=False)


def thu_hoi_phien_nguoi_dung(ket_noi, *, nguoi_dung_id: UUID) -> None:
    _goi(ket_noi, 'SELECT loi.thu_hoi_phien_nguoi_dung(%s)',
         (UUID(str(nguoi_dung_id)),), lay_dong=False)


def thu_hoi_uy_nhiem_viec(ket_noi, *, viec_id: UUID, the_he: int) -> None:
    if type(the_he) is not int or the_he <= 0:
        raise ValueError('Thế hệ việc không hợp lệ')
    _goi(ket_noi, 'SELECT loi.thu_hoi_uy_nhiem_viec(%s, %s)',
         (UUID(str(viec_id)), the_he), lay_dong=False)
