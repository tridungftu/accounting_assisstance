"""Nguồn danh tính Core, dùng kết nối/transaction do bên gọi quản lý.

Các hàm chỉ tạo/tra hồ sơ, không xác thực đăng nhập, cấp phiên hoặc quyết định
quyền. RLS của CSDL quyết định phạm vi; không đặt GUC danh tính, không nhận
actor từ client. ``nguoi_dung_id`` khi tạo thành viên là người được thêm.
Không tự mở kết nối, commit, rollback hay ghi log tham số/kết nối.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


CAC_VAI_TRO = frozenset((
    'KE_TOAN', 'KE_TOAN_TRUONG', 'CFO', 'NHAP_JUNSKY', 'XEM', 'BAN_HANG', 'DU_AN',
))


@dataclass(frozen=True)
class NguoiDung:
    id: UUID
    dang_nhap: str
    ten: str
    vai_tro: str
    trang_thai: str
    mo_phong: bool


@dataclass(frozen=True)
class PhapNhan:
    id: UUID
    ma: str
    ten: str
    mst: str | None
    trang_thai: str


@dataclass(frozen=True)
class ThanhVien:
    id: UUID
    nguoi_dung_id: UUID
    phap_nhan_id: UUID
    duyet_loai_viec: tuple[str, ...]
    module: tuple[str, ...]


def _chuoi_bat_buoc(gia_tri: str) -> str:
    if not isinstance(gia_tri, str) or not gia_tri.strip():
        raise ValueError('Trường bắt buộc phải là chuỗi không rỗng')
    return gia_tri


def _danh_sach_chuoi(gia_tri) -> list[str]:
    if not isinstance(gia_tri, (list, tuple)) or any(
        not isinstance(phan_tu, str) or not phan_tu.strip() for phan_tu in gia_tri
    ):
        raise ValueError('Danh sách phải gồm các chuỗi không rỗng')
    return list(gia_tri)


def _thanh_vien(dong) -> ThanhVien | None:
    if dong is None:
        return None
    return ThanhVien(*dong[:3], tuple(dong[3]), tuple(dong[4]))


def tao_nguoi_dung(ket_noi, *, dang_nhap: str, ten: str,
                  vai_tro: str = 'XEM', mo_phong: bool = False) -> NguoiDung:
    _chuoi_bat_buoc(dang_nhap)
    _chuoi_bat_buoc(ten)
    if not isinstance(vai_tro, str) or vai_tro not in CAC_VAI_TRO:
        raise ValueError('Vai trò không hợp lệ')
    if type(mo_phong) is not bool:
        raise ValueError('Cờ mô phỏng phải là boolean')
    if mo_phong and not dang_nhap.startswith('MO_PHONG_'):
        raise ValueError('Tên tài khoản mô phỏng phải bắt đầu bằng MO_PHONG_')
    dong = ket_noi.execute('''
        INSERT INTO loi.nguoi_dung (dang_nhap, ten, vai_tro, mo_phong)
        VALUES (%s, %s, %s, %s)
        RETURNING id, dang_nhap, ten, vai_tro, trang_thai, mo_phong
    ''', (dang_nhap, ten, vai_tro, mo_phong)).fetchone()
    return NguoiDung(*dong)


def tra_nguoi_dung(ket_noi, *, dang_nhap: str) -> NguoiDung | None:
    """Tra hồ sơ (kể cả mô phỏng); kết quả không phải bằng chứng xác thực."""
    _chuoi_bat_buoc(dang_nhap)
    dong = ket_noi.execute('''
        SELECT id, dang_nhap, ten, vai_tro, trang_thai, mo_phong
        FROM loi.nguoi_dung WHERE dang_nhap = %s
    ''', (dang_nhap,)).fetchone()
    return None if dong is None else NguoiDung(*dong)


def tao_phap_nhan(ket_noi, *, ma: str, ten: str, mst: str | None = None) -> PhapNhan:
    _chuoi_bat_buoc(ma)
    _chuoi_bat_buoc(ten)
    if mst is not None and not isinstance(mst, str):
        raise ValueError('Mã số thuế phải là chuỗi hoặc None')
    dong = ket_noi.execute('''
        INSERT INTO loi.phap_nhan (ma, ten, mst) VALUES (%s, %s, %s)
        RETURNING id, ma, ten, mst, trang_thai
    ''', (ma, ten, mst)).fetchone()
    return PhapNhan(*dong)


def tra_phap_nhan(ket_noi, *, phap_nhan_id: UUID) -> PhapNhan | None:
    dong = ket_noi.execute('''
        SELECT id, ma, ten, mst, trang_thai FROM loi.phap_nhan WHERE id = %s
    ''', (UUID(str(phap_nhan_id)),)).fetchone()
    return None if dong is None else PhapNhan(*dong)


def tao_thanh_vien(ket_noi, *, nguoi_dung_id: UUID, phap_nhan_id: UUID,
                   duyet_loai_viec=(), module=()) -> ThanhVien:
    dong = ket_noi.execute('''
        INSERT INTO loi.phan_quyen
            (nguoi_dung_id, phap_nhan_id, duyet_loai_viec, module)
        VALUES (%s, %s, %s, %s)
        RETURNING id, nguoi_dung_id, phap_nhan_id, duyet_loai_viec, module
    ''', (UUID(str(nguoi_dung_id)), UUID(str(phap_nhan_id)),
          _danh_sach_chuoi(duyet_loai_viec), _danh_sach_chuoi(module))).fetchone()
    return _thanh_vien(dong)


def tra_thanh_vien(ket_noi, *, nguoi_dung_id: UUID,
                   phap_nhan_id: UUID) -> ThanhVien | None:
    dong = ket_noi.execute('''
        SELECT id, nguoi_dung_id, phap_nhan_id, duyet_loai_viec, module
        FROM loi.thanh_vien WHERE nguoi_dung_id = %s AND phap_nhan_id = %s
    ''', (UUID(str(nguoi_dung_id)), UUID(str(phap_nhan_id)))).fetchone()
    return _thanh_vien(dong)
