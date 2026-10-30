"""Công tắc Core nâng M0056, kiem_module và trang_thai_cho của K2.

Phiên G2-03 là nguồn danh tính; Admin từ MTQ G2-06. Caller giữ transaction,
kiểm MTQ nghiệp vụ riêng và xác định pháp nhân từ phiên/đối tượng máy chủ.
Không commit, không mở kết nối, không đưa mã phiên/lỗi SQL ra ngoài.
THU chỉ người thử; TAT giữ quyền xem lịch sử nội bộ theo M0056.
"""

from __future__ import annotations

import re
from uuid import UUID

from .phien import MaBiMat


class LoiCongTac(RuntimeError):
    def __init__(self, ma):
        self.ma = ma
        super().__init__('Thao tác công tắc thất bại (' + ma + ')')


_MA_LOI = {'MODULE_CHI_ADMIN', 'MODULE_DAU_VAO', 'MODULE_NGUOI_THU',
           'MODULE_REVISION', 'MODULE_PHIEN', 'MODULE_CHUA_DU_DIEU_KIEN_GO_LIVE'}
_CO_CAN = {'xem': 'cho_xem', 'ghi': 'cho_ghi', 'xuat_ngoai': 'cho_xuat_ngoai',
           'cong_bo': 'cong_bo_chinh_thuc'}


def _goi(ket_noi, sql, tham_so):
    ma_loi = 'MODULE_THAT_BAI'
    try:
        return ket_noi.execute(sql, tham_so).fetchone()[0]
    except Exception as exc:
        chinh = getattr(getattr(exc, 'diag', None), 'message_primary', '')
        if isinstance(chinh, str) and chinh in _MA_LOI:
            ma_loi = chinh
    tham_so = None
    raise LoiCongTac(ma_loi)


def _dich(ma, module, phap_nhan_id):
    if not isinstance(ma, MaBiMat):
        raise ValueError('Cần mã phiên bí mật')
    if not isinstance(module, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,30}', module) or module == 'core':
        raise ValueError('Module không hợp lệ')
    return ma.lay_de_truyen(), module, UUID(str(phap_nhan_id))


def che_do(ket_noi, *, ma, module, phap_nhan_id):
    """GET quản trị: chỉ Admin MTQ; trả row_version, che_do, nguoi_thu_ids."""
    return _goi(ket_noi, 'SELECT loi.module_che_do(%s,%s,%s)', _dich(ma, module, phap_nhan_id))


def doi_che_do(ket_noi, *, ma, module, phap_nhan_id, payload, request_id):
    """PATCH CheDoModule: danh sách người thử và chế độ đổi nguyên tử bằng CAS.

    row_version là chuỗi số nguyên dương theo OpenAPI; mặc định chưa có là
    TAT/"1". CAS lệch trả MODULE_REVISION để HTTP boundary ánh xạ 409.
    Không nhận actor hoặc quyết định quyền do client khai.
    """
    if not isinstance(payload, dict) or set(payload) != {'row_version', 'che_do', 'nguoi_thu_ids'}:
        raise ValueError('Thiếu trường bắt buộc hoặc có trường ngoài phạm vi')
    ban = payload['row_version']
    if (not isinstance(ban, str) or not re.fullmatch(r'[1-9][0-9]{0,18}', ban)
            or int(ban) > 9223372036854775807):
        raise ValueError('Phiên bản dòng phải là chuỗi số nguyên dương bigint')
    cd = payload['che_do']
    if not isinstance(cd, str) or cd not in ('TAT', 'THU', 'VAN_HANH'):
        raise ValueError('Chế độ không hợp lệ')
    ds = payload['nguoi_thu_ids']
    if not isinstance(ds, list) or len(ds) > 1000:
        raise ValueError('Danh sách người thử không hợp lệ')
    ds = [UUID(str(n)) for n in ds]
    if len(ds) != len(set(ds)):
        raise ValueError('Danh sách người thử bị trùng')
    return _goi(ket_noi, 'SELECT loi.module_doi_che_do(%s,%s,%s,%s,%s,%s::uuid[],%s)',
                (*_dich(ma, module, phap_nhan_id), cd, int(ban), ds, UUID(str(request_id))))


def trang_thai(ket_noi, *, ma, module, phap_nhan_id, hanh_dong,
               module_phien=None, viec_id=None, the_he=None):
    """Cờ cho Core/module; module_phien là bên đọc, module là nguồn cần hỏi.

    Bên nhận được hỏi nguồn bằng chính phiên của mình để hiển thị CHO;
    không nhận phiên nguồn, không lộ danh sách người thử, không thay MTQ.
    """
    mp = module if module_phien is None else module_phien
    if (not isinstance(mp, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,30}', mp)
        or not isinstance(hanh_dong, str) or not re.fullmatch(
        r'[A-Z0-9_]+:[A-Z0-9_]+:[A-Z_]+', hanh_dong
    ) or hanh_dong.split(':')[0] != mp.upper()):
        raise ValueError('Hành động không thuộc module của phiên')
    if (viec_id is None) != (the_he is None) or (the_he is not None and (
        type(the_he) is not int or not 0 < the_he <= 9223372036854775807
    )):
        raise ValueError('Việc và thế hệ không hợp lệ')
    return _goi(ket_noi, 'SELECT loi.module_trang_thai(%s,%s,%s,%s,%s,%s,%s)',
                (*_dich(ma, module, phap_nhan_id), hanh_dong, mp,
                 None if viec_id is None else UUID(str(viec_id)), the_he))


def kiem_module(ket_noi, *, can, **tham_so):
    """Nâng cổng K2; cùng transaction nghiệp vụ. TAT vẫn xem lịch sử được."""
    if not isinstance(can, str) or can not in _CO_CAN:
        raise ValueError('Thao tác kiểm tra không hợp lệ')
    co = trang_thai(ket_noi, **tham_so)
    if co.get(_CO_CAN[can]) is True:
        return co
    if co.get('che_do') == 'TAT':
        raise LoiCongTac('MODULE_TAT')
    if co.get('che_do') == 'THU':
        if co.get('cho_xem') is not True:
            raise LoiCongTac('MODULE_CHI_NGUOI_THU')
        if can == 'xuat_ngoai':
            raise LoiCongTac('MODULE_THU_KHONG_XUAT')
        if can == 'cong_bo':
            raise LoiCongTac('MODULE_THU_KHONG_CONG_BO')
    raise LoiCongTac('MODULE_KHONG_CHO_PHEP')


def trang_thai_cho(ket_noi, **tham_so):
    """Nâng K2: dữ liệu nguồn TAT/THU chưa được dùng chính thức ở bên nhận."""
    co = trang_thai(ket_noi, **tham_so)
    if co.get('cho_xem') is True and co.get('cong_bo_chinh_thuc') is True:
        return None
    return {'ma': 'CHO_MODULE', 'ly_do': 'Chờ chức năng nguồn'}
