"""G2-05: cửa registry dùng transaction/kết nối do Core quản lý.

Không đọc manifest hay chạy mã gói. G2-24/25 kiểm schema, nguồn/hash và bằng
chứng duyệt trước khi ghi bằng LOGIN cài đặt. Không tự commit, không cấp quyền
đọc module khi đăng ký contract. Resolver trả binding đã kiểm cho G2-06 gọi
đúng ABI của contract; không nhận tên hàm từ request runtime.
"""

from __future__ import annotations

import json
import re
from uuid import UUID

from .phien import MaBiMat


CAC_LOAI_DOC = frozenset(('module', 'phien_ban_module', 'engine', 'contract', 'ham_module'))
CAC_LOAI_GHI = frozenset((*CAC_LOAI_DOC, 'trang_thai_module', 'trang_thai_contract',
                         'sap_ngung_contract', 'dung_contract', 'thoi_dung_contract'))
CAC_TRANG_THAI_CONTRACT = frozenset(('nhap', 'anh_duyet', 'dang_dung', 'ngung'))


class LoiDangKy(RuntimeError):
    """Giữ SQLSTATE an toàn, bỏ thông báo driver có thể chứa mã phiên/DSN."""

    def __init__(self, ma: str):
        self.ma = ma
        super().__init__(ma)


def _goi(ket_noi, cau_sql, tham_so):
    ma_loi = 'DANG_KY_THAT_BAI'
    try:
        return ket_noi.execute(cau_sql, tham_so).fetchone()[0]
    except Exception as exc:
        trang_thai = getattr(exc, 'sqlstate', None)
        if isinstance(trang_thai, str) and re.fullmatch(r'[0-9A-Z]{5}', trang_thai):
            ma_loi = trang_thai
    tham_so = None
    raise LoiDangKy(ma_loi)


def _chuoi(gia_tri, ten):
    if not isinstance(gia_tri, str) or not gia_tri.strip():
        raise ValueError('Trường không hợp lệ: ' + ten)
    return gia_tri


def ghi_dang_ky(ket_noi, *, loai: str, du_lieu: dict) -> UUID:
    """Chỉ gọi từ cổng cài đặt đã kiểm; CSDL kiểm LOGIN và mọi ràng buộc.

    Không nhận ``actor``/SQL; danh tính audit do CSDL lấy từ session_user.
    Binding chỉ được gỡ sau khi bên cài đặt kiểm hết module/việc ghim bản cũ.
    """
    if not isinstance(loai, str) or loai not in CAC_LOAI_GHI:
        raise ValueError('Loại đăng ký không hợp lệ')
    if not isinstance(du_lieu, dict):
        raise ValueError('Dữ liệu đăng ký phải là object')
    if any(k in du_lieu for k in ('actor', 'nguoi_dung_id', 'dang_nhap_csdl', 'sql')):
        raise ValueError('Không nhận danh tính hoặc SQL từ dữ liệu đăng ký')
    noi_dung = json.dumps(du_lieu, ensure_ascii=False, allow_nan=False)
    return _goi(ket_noi, 'SELECT loi.ghi_dang_ky(%s, %s::jsonb)', (loai, noi_dung))


def doc_dang_ky(ket_noi, *, loai: str, ma: str | None = None) -> list[dict]:
    if not isinstance(loai, str) or loai not in CAC_LOAI_DOC:
        raise ValueError('Loại đăng ký không hợp lệ')
    if ma is not None:
        _chuoi(ma, 'ma')
    return _goi(ket_noi, 'SELECT loi.doc_dang_ky(%s, %s)', (loai, ma))


def chuyen_trang_thai_contract(ket_noi, *, ma: str, phien_ban: str,
                              trang_thai: str, bang_chung_duyet: str | None = None) -> UUID:
    _chuoi(ma, 'ma')
    _chuoi(phien_ban, 'phien_ban')
    if not isinstance(trang_thai, str) or trang_thai not in CAC_TRANG_THAI_CONTRACT:
        raise ValueError('Trạng thái contract không hợp lệ')
    du_lieu = dict(ma=ma, phien_ban=phien_ban, trang_thai=trang_thai)
    if bang_chung_duyet is not None:
        du_lieu['bang_chung_duyet'] = _chuoi(bang_chung_duyet, 'bang_chung_duyet')
    return ghi_dang_ky(ket_noi, loai='trang_thai_contract', du_lieu=du_lieu)


def phan_giai_ham_module(ket_noi, *, module: str, loai_ham: str,
                        phien_ban_contract: str, ma: MaBiMat, phap_nhan_id: UUID,
                        hanh_dong: str, viec_id: UUID | None = None,
                        the_he: int | None = None) -> dict:
    """Phiên sai → lỗi quyền; thiếu module/hàm/contract sẵn dùng → ``CHO``.

    Kết quả ``DAT`` gồm binding nội bộ đã đối chiếu catalog, không phải kết
    quả nghiệp vụ hay quyền đọc dữ liệu. G2-06 phải gọi trong cùng transaction
    và kiểm kết quả resolver trước khi ghi. Không tự chọn bản mới nhất.
    """
    if not isinstance(module, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,30}', module):
        raise ValueError('Mã module không hợp lệ')
    if not isinstance(loai_ham, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,62}', loai_ham):
        raise ValueError('Loại hàm không hợp lệ')
    _chuoi(phien_ban_contract, 'phien_ban_contract')
    _chuoi(hanh_dong, 'hanh_dong')
    if not isinstance(ma, MaBiMat):
        raise ValueError('Mã phiên phải là MaBiMat')
    if (viec_id is None) != (the_he is None) or (
        the_he is not None and (type(the_he) is not int or the_he < 1)
    ):
        raise ValueError('Việc và thế hệ phải đi cùng nhau')
    return _goi(ket_noi, '''SELECT loi.phan_giai_ham_module(
        %s, %s, %s, %s, %s, %s, %s, %s)''', (
        module, loai_ham, phien_ban_contract, ma.lay_de_truyen(),
        UUID(str(phap_nhan_id)), hanh_dong,
        None if viec_id is None else UUID(str(viec_id)), the_he,
    ))
