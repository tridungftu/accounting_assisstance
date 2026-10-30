"""Cổng MTQ Core dùng mã phiên G2-03 và transaction do caller quản lý.

Nâng cổng hỏi/đọc/ghi từ chối M0057–58; không quyết định quyền trong Python,
không nhận actor, số tiền hay pháp nhân đối tượng do client khai. Resolver
module lấy căn cứ CSDL qua binding đã kiểm. ``cac_ma`` cung cấp mã riêng cho
từng pháp nhân của cùng người dùng. CHO luôn có ``cho_phep=False``.
Mọi pháp nhân dùng cùng số tiền từ resolver; ``hop_le=False`` trả TU_CHOI
với mã MTQ_DOI_TUONG và lý do module, ghi qua ``ghi_tu_choi_phien``.

Sau rollback nghiệp vụ, caller mở transaction mới để ghi từ chối rồi commit.
Hàm đọc/hỏi không tự ghi audit. Lỗi driver không giữ thông báo hoặc tham số.
Các hàm ghi trực tiếp cũ của danh_tinh.py không còn ACL sau 006; dùng cửa
tao_danh_tinh có kiểm MTQ. Bootstrap workspace đầu tiên do lead provisioning.
"""

from __future__ import annotations

import json
import re
from uuid import UUID

from .phien import MaBiMat


class LoiMTQ(RuntimeError):
    def __init__(self, ma: str):
        self.ma = ma
        super().__init__('Thao tác thẩm quyền thất bại (' + ma + ')')


def _goi(ket_noi, cau_sql, tham_so):
    ma_loi = 'MTQ_THAT_BAI'
    try:
        return ket_noi.execute(cau_sql, tham_so).fetchone()[0]
    except Exception as exc:
        trang_thai = getattr(exc, 'sqlstate', None)
        if isinstance(trang_thai, str) and re.fullmatch(r'[0-9A-Z]{5}', trang_thai):
            ma_loi = trang_thai
    tham_so = None
    raise LoiMTQ(ma_loi)


def _ma(ma):
    if not isinstance(ma, MaBiMat):
        raise ValueError('Cần mã phiên bí mật')
    return ma.lay_de_truyen()


def _viec(viec_id, the_he):
    if (viec_id is None) != (the_he is None) or (
        the_he is not None and (type(the_he) is not int or not 0 < the_he <= 9223372036854775807)
    ):
        raise ValueError('Việc và thế hệ không hợp lệ')
    return None if viec_id is None else UUID(str(viec_id)), the_he


def _pham_vi(module, phap_nhan_id, hanh_dong):
    if not isinstance(module, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,30}', module):
        raise ValueError('Module không hợp lệ')
    if (not isinstance(hanh_dong, str) or not re.fullmatch(r'[A-Z0-9_]+:[A-Z0-9_]+:[A-Z_]+', hanh_dong)
            or hanh_dong.split(':')[0] != module.upper()):
        raise ValueError('Hành động không thuộc module')
    return module, UUID(str(phap_nhan_id)), hanh_dong


def _tham_so(*, ma, module, phap_nhan_id, hanh_dong, doi_tuong,
             phien_ban_contract='1', cac_ma=(), viec_id=None, the_he=None):
    _pham_vi(module, phap_nhan_id, hanh_dong)
    if (not isinstance(doi_tuong, dict) or set(doi_tuong) - {'bang', 'id', 'phong_id'}
            or not {'bang', 'id'} <= set(doi_tuong)
            or not isinstance(doi_tuong['bang'], str) or not doi_tuong['bang'].strip()):
        raise ValueError('Chỉ nhận tham chiếu đối tượng máy chủ')
    doi_tuong = dict(doi_tuong)
    doi_tuong['id'] = str(UUID(str(doi_tuong['id'])))
    if doi_tuong.get('phong_id') is not None:
        doi_tuong['phong_id'] = str(UUID(str(doi_tuong['phong_id'])))
    if not isinstance(phien_ban_contract, str) or not phien_ban_contract.strip():
        raise ValueError('Cần phiên bản contract đã ghim')
    if not isinstance(cac_ma, (list, tuple)):
        raise ValueError('Cần danh sách mã phiên')
    viec_id, the_he = _viec(viec_id, the_he)
    return (_ma(ma), module, UUID(str(phap_nhan_id)), hanh_dong,
            json.dumps(doi_tuong, ensure_ascii=False, allow_nan=False), phien_ban_contract,
            [_ma(m) for m in cac_ma], viec_id, the_he)


def quyet_dinh_phien(ket_noi, **tham_so) -> dict:
    """Chỉ DAT và cho_phep=True mới cho phép; không tự xử lý CHO thành fallback."""
    return _goi(ket_noi, '''SELECT loi.mtq_quyet_dinh_phien(
        %s,%s,%s,%s,%s::jsonb,%s,%s::text[],%s,%s)''', _tham_so(**tham_so))


def duoc_doc(ket_noi, **tham_so) -> bool:
    return _goi(ket_noi, '''SELECT loi.mtq_duoc_doc(
        %s,%s,%s,%s,%s::jsonb,%s,%s::text[],%s,%s)''', _tham_so(**tham_so))


def ghi_tu_choi_phien(ket_noi, *, request_id: UUID, **tham_so) -> UUID:
    return _goi(ket_noi, '''SELECT loi.mtq_ghi_tu_choi_phien(
        %s,%s,%s,%s,%s,%s::jsonb,%s,%s::text[],%s,%s)''',
        (UUID(str(request_id)), *_tham_so(**tham_so)))


def dat_ngu_canh(ket_noi, *, ma: MaBiMat, module: str, phap_nhan_id: UUID,
                 hanh_dong: str, viec_id: UUID | None = None, the_he: int | None = None) -> None:
    """Gọi bên trong transaction. SET LOCAL không phải cache kết quả xác minh."""
    module, phap_nhan_id, hanh_dong = _pham_vi(module, phap_nhan_id, hanh_dong)
    viec_id, the_he = _viec(viec_id, the_he)
    hop_le = _goi(ket_noi, '''SELECT EXISTS (SELECT FROM loi.xac_minh_phien(
        %s,%s,%s,%s,%s,%s))''', (_ma(ma), module, phap_nhan_id, hanh_dong, viec_id, the_he))
    if not hop_le:
        raise LoiMTQ('42501')
    _goi(ket_noi, '''SELECT set_config('ktt.ma_phien',%s,true),
        set_config('ktt.module',%s,true), set_config('ktt.phap_nhan_id',%s,true),
        set_config('ktt.hanh_dong',%s,true), set_config('ktt.viec_id',%s,true),
        set_config('ktt.the_he',%s,true)''',
        (_ma(ma), module, str(phap_nhan_id), hanh_dong,
         '' if viec_id is None else str(viec_id), '' if the_he is None else str(the_he)))


def tao_danh_tinh(ket_noi, *, ma: MaBiMat, phap_nhan_id: UUID, loai: str,
                  du_lieu: dict, viec_id: UUID | None = None, the_he: int | None = None) -> UUID:
    """MTQ kiểm CORE:DANH_TINH:LAP ở workspace hiện hành. Người nhận là target.

    Tạo workspace mới tự thêm người thao tác làm thành viên Core và thu hồi
    phiên cũ theo G2-03; caller phải cấp phiên mới trước thao tác tiếp theo.
    """
    cac_khoa = {
        'nguoi_dung': {'dang_nhap', 'ten', 'vai_tro', 'mo_phong'},
        'phap_nhan': {'ma', 'ten', 'mst'},
        'thanh_vien': {'nguoi_dung_id', 'module', 'duyet_loai_viec'},
    }
    if not isinstance(loai, str) or loai not in cac_khoa or not isinstance(du_lieu, dict):
        raise ValueError('Loại hoặc dữ liệu danh tính không hợp lệ')
    if set(du_lieu) - cac_khoa[loai]:
        raise ValueError('Dữ liệu có trường ngoài phạm vi')
    du_lieu = dict(du_lieu)
    if 'nguoi_dung_id' in du_lieu:
        du_lieu['nguoi_dung_id'] = str(UUID(str(du_lieu['nguoi_dung_id'])))
    for ten in ('module', 'duyet_loai_viec'):
        if ten in du_lieu and (not isinstance(du_lieu[ten], (list, tuple)) or any(
            not isinstance(v, str) or not v.strip() for v in du_lieu[ten]
        )):
            raise ValueError('Danh sách quyền không hợp lệ')
    viec_id, the_he = _viec(viec_id, the_he)
    return _goi(ket_noi, 'SELECT loi.mtq_tao_danh_tinh(%s,%s,%s,%s::jsonb,%s,%s)',
                (_ma(ma), UUID(str(phap_nhan_id)), loai,
                 json.dumps(du_lieu, ensure_ascii=False, allow_nan=False), viec_id, the_he))
