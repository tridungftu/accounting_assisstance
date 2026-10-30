"""Sổ cổng nội bộ Core; caller giữ transaction, xác minh tiến trình/socket ở G2-21.

Không bind/dò cổng hoặc gọi engine, không tạo login. Hồ sơ/đối số/tham chiếu bí
mật chỉ từ gói đã kiểm. Các UUID bằng chứng là tham chiếu do Core cung cấp sau
đối chiếu OS/readiness, không phải bằng chứng được sổ tự xác minh.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from ipaddress import ip_address
import json
import math
import re
from uuid import UUID

from .phien import _ma
from .tiep_nhan import _tx


_LOI = {'CONG_CHI_CORE', 'CONG_CHI_CAI_DAT', 'CONG_CHI_ADMIN', 'CONG_DAU_VAO',
        'CONG_CHU', 'CONG_CO_DINH', 'CONG_KHONG_THAY', 'CONG_CAS', 'CONG_KHOA_LOI',
        'CONG_MAT_LEASE', 'CONG_CAN_DOI_CHIEU'}


class LoiSoCong(RuntimeError):
    def __init__(self, ma):
        self.ma = ma
        super().__init__('Thao tác sổ cổng thất bại (' + ma + ')')


def _goi(conn, ham, ts):
    _tx(conn)
    ma = 'CONG_THAT_BAI'
    try:
        row = conn.execute('SELECT loi.' + ham + '(' + ','.join(['%s'] * len(ts)) + ') AS r', ts).fetchone()
        return row['r'] if isinstance(row, Mapping) else row[0]
    except Exception as exc:
        chinh = getattr(getattr(exc, 'diag', None), 'message_primary', None)
        if isinstance(chinh, str) and chinh in _LOI:
            ma = chinh
    ts = None
    raise LoiSoCong(ma)


def _so(v, nho=0, lon=2**63-1):
    if type(v) is not int or not nho <= v <= lon:
        raise ValueError('Số nguyên ngoài giới hạn')
    return v


def _gio(v):
    if not isinstance(v, datetime) or v.tzinfo is None or v.utcoffset() is None:
        raise ValueError('Cần datetime có múi giờ')
    return v


def _giu(so_cong_id, instance_id, the_he):
    return UUID(str(so_cong_id)), UUID(str(instance_id)), _so(the_he, 1)


def cap(conn, may_chu_id, cong, *, module=None, engine_ho_so_id=None, dia_chi_nghe='127.0.0.1'):
    """Cấp cổng cấu hình cố định; cấp lại cùng chủ trả cùng dòng, không đổi cổng."""
    if (module is None) == (engine_ho_so_id is None):
        raise ValueError('Cần đúng một module hoặc hồ sơ engine')
    if module is not None and (not isinstance(module, str) or not module.strip()):
        raise ValueError('Mã module không hợp lệ')
    dia_chi = str(ip_address(dia_chi_nghe))
    if dia_chi not in ('127.0.0.1', '::1'):
        raise ValueError('Chỉ nghe loopback')
    return _goi(conn, 'so_cong_cap', (UUID(str(may_chu_id)), dia_chi, _so(cong, 1024, 65535),
                 module, UUID(str(engine_ho_so_id)) if engine_ho_so_id is not None else None))


def doc(conn, so_cong_id):
    return _goi(conn, 'so_cong_doc', (UUID(str(so_cong_id)),))


def tao_ho_so(conn, *, engine_id, may_chu_id, executable, doi_so,
              so_viec_dong_thoi=1, timeout_giay=900, ranh_giay=300, tham_chieu_bi_mat=None):
    """Cửa cài đặt; chỉ nhận đường chạy/đối số đã kiểm, bí mật là tham chiếu."""
    if (not isinstance(executable, str) or not executable.strip()
            or not isinstance(doi_so, list) or not all(isinstance(x, str) for x in doi_so)
            or (tham_chieu_bi_mat is not None and not isinstance(tham_chieu_bi_mat, str))):
        raise ValueError('Hồ sơ không hợp lệ')
    p = dict(engine_id=str(UUID(str(engine_id))), may_chu_id=str(UUID(str(may_chu_id))),
             executable=executable, doi_so=doi_so, tham_chieu_bi_mat=tham_chieu_bi_mat,
             so_viec_dong_thoi=_so(so_viec_dong_thoi, 1, 1000),
             timeout_giay=_so(timeout_giay, 1, 86400), ranh_giay=_so(ranh_giay, 1, 86400))
    return _goi(conn, 'so_cong_tao_ho_so', (json.dumps(p, ensure_ascii=False),))


def nhan(conn, so_cong_id, instance_id, the_he_cu, *, pid, dinh_danh_lan_tao,
         phien_ban, nhan_yeu_cau_luc, bat_dau_luc, lease_giay=120, doi_chieu_id=None):
    if (not isinstance(dinh_danh_lan_tao, str) or not 1 <= len(dinh_danh_lan_tao.strip()) <= 200
            or not isinstance(phien_ban, str) or not phien_ban.strip()):
        raise ValueError('Cần danh tính lần tạo và phiên bản thực')
    if _gio(nhan_yeu_cau_luc) > _gio(bat_dau_luc):
        raise ValueError('Bắt đầu phải sau khi nhận yêu cầu')
    return _goi(conn, 'so_cong_nhan', (UUID(str(so_cong_id)), UUID(str(instance_id)), _so(the_he_cu),
        _so(lease_giay, 1, 3600), _so(pid, 1, 2**31-1), dinh_danh_lan_tao, phien_ban,
        nhan_yeu_cau_luc, bat_dau_luc, UUID(str(doi_chieu_id)) if doi_chieu_id is not None else None))


def gia_han(conn, so_cong_id, instance_id, the_he, *, lease_giay=120):
    return _goi(conn, 'so_cong_gia_han', (*_giu(so_cong_id, instance_id, the_he), _so(lease_giay, 1, 3600)))


def san_sang(conn, so_cong_id, instance_id, the_he, *, bang_chung_id):
    """Chỉ ghi mốc và bằng chứng sẵn sàng lần đầu cho mỗi instance/thế hệ."""
    return _goi(conn, 'so_cong_san_sang', (*_giu(so_cong_id, instance_id, the_he), UUID(str(bang_chung_id))))


def tra(conn, so_cong_id, instance_id, the_he):
    return _goi(conn, 'so_cong_tra', _giu(so_cong_id, instance_id, the_he))


def loi_khoi_dong(conn, so_cong_id, instance_id, the_he, *, ma_loi):
    if not isinstance(ma_loi, str) or not re.fullmatch('[A-Z][A-Z0-9_]{0,79}', ma_loi):
        raise ValueError('Cần mã lỗi trung tính')
    return _goi(conn, 'so_cong_loi_khoi_dong', (*_giu(so_cong_id, instance_id, the_he), ma_loi))


def mo_khoa(conn, so_cong_id, phien_ban_dong, *, ma, phap_nhan_id, request_id):
    return _goi(conn, 'so_cong_mo_khoa', (UUID(str(so_cong_id)), _so(phien_ban_dong, 1),
                 _ma(ma), UUID(str(phap_nhan_id)), UUID(str(request_id))))


def het_hieu_luc(conn, so_cong_id, phien_ban_dong):
    return _goi(conn, 'so_cong_het_hieu_luc', (UUID(str(so_cong_id)), _so(phien_ban_dong, 1)))


def ghi_so_do(conn, so_cong_id, instance_id, the_he, *, cua_so_tu, cua_so_den,
              chay_viec_ms=None, ranh_ms=None, ram_dinh_byte=None, ram_trung_binh_byte=None, cpu_ms=None):
    tu, den = _gio(cua_so_tu), _gio(cua_so_den)
    if den < tu:
        raise ValueError('Cửa sổ đo đảo ngược')
    p = dict(cua_so_tu=tu.isoformat(), cua_so_den=den.isoformat())
    for ten, v in (('chay_viec_ms', chay_viec_ms), ('ranh_ms', ranh_ms), ('cpu_ms', cpu_ms)):
        if v is not None and (type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v < 1e18):
            raise ValueError('Số đo không hợp lệ')
        p[ten] = v
    p['ram_dinh_byte'] = _so(ram_dinh_byte) if ram_dinh_byte is not None else None
    p['ram_trung_binh_byte'] = _so(ram_trung_binh_byte) if ram_trung_binh_byte is not None else None
    if ram_dinh_byte is not None and ram_trung_binh_byte is not None and ram_trung_binh_byte > ram_dinh_byte:
        raise ValueError('RAM trung bình vượt RAM đỉnh')
    return _goi(conn, 'so_cong_ghi_so_do', (*_giu(so_cong_id, instance_id, the_he), json.dumps(p, allow_nan=False)))
