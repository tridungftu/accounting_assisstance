"""Liên kết MONEY V2, dùng một kết nối/transaction do caller quản lý.

Sửa = hủy dòng cũ + thêm ID mới; hủy giữ nguyên lịch sử. CHO không ghi dở.
Module Manager cấp EXECUTE lien_ket_v2 đúng chữ ký cho module được duyệt.
Resolver nghĩa vụ và đường giảm sức chứa phải tuân ABI ở 013_lien_ket.sql.
"""
from __future__ import annotations

import re
from uuid import UUID

from .tai_lieu import _ngu_canh, _truong
from .tiep_nhan import _json, _tx


class LoiLienKet(RuntimeError):
    def __init__(self, ma):
        self.ma = ma
        self.http_status = (403 if ma in {'TAI_LIEU_PHIEN', 'TAI_LIEU_MTQ', 'TAI_LIEU_CONG_TAC',
                                          'LIEN_KET_PHAM_VI', 'LIEN_KET_RESOLVER',
                                          'LIEN_KET_MODULE_KIEM', 'LIEN_KET_POLICY_KIEM'} else
                            409 if ma in {'LIEN_KET_XUNG_DOT', 'LIEN_KET_VUOT_CHUNG_TU',
                                          'LIEN_KET_VUOT_NGHIA_VU', 'KY_DA_KHOA'} else 400)
        super().__init__('Thao tác liên kết thất bại (' + ma + ')')


_LOI = {'TAI_LIEU_PHIEN', 'TAI_LIEU_MTQ', 'TAI_LIEU_CONG_TAC', 'LIEN_KET_PHAM_VI',
        'LIEN_KET_RESOLVER', 'LIEN_KET_MODULE_KIEM', 'LIEN_KET_POLICY_KIEM',
        'LIEN_KET_CAN_CU', 'LIEN_KET_XUNG_DOT', 'LIEN_KET_DAU_VAO',
        'LIEN_KET_BAT_BIEN', 'LIEN_KET_VUOT_CHUNG_TU', 'LIEN_KET_VUOT_NGHIA_VU',
        'LIEN_KET_CAN_READ_COMMITTED', 'KY_DA_KHOA',
        'DEMO_LIEN_KET_CHEO', 'DEMO_PHAP_NHAN', 'DEMO_CAN_READ_COMMITTED'}
_DICH = {'module_nghia_vu', 'loai_nghia_vu', 'nghia_vu_id', 'phien_ban_can_cu_id',
         'ma_bam_phien_ban_can_cu'}


def _tien(value):
    if not isinstance(value, str) or not re.fullmatch('[1-9][0-9]{0,37}', value):
        raise ValueError('Cần số tiền minor dương, nguyên dạng chuỗi')


def _dich(data):
    if not isinstance(data['module_nghia_vu'], str) or not re.fullmatch(
            '[a-z][a-z0-9_]{0,30}', data['module_nghia_vu']):
        raise ValueError('Module nghĩa vụ không hợp lệ')
    if not isinstance(data['loai_nghia_vu'], str) or not data['loai_nghia_vu'].strip():
        raise ValueError('Thiếu loại nghĩa vụ')
    for ten in ('nghia_vu_id', 'phien_ban_can_cu_id'):
        data[ten] = str(UUID(str(data[ten])))
    if not isinstance(data['ma_bam_phien_ban_can_cu'], str) or not re.fullmatch(
            '[0-9a-f]{64}', data['ma_bam_phien_ban_can_cu']):
        raise ValueError('Cần SHA-256 phiên bản căn cứ')
    return data


def _du_lieu(data):
    co = {'chung_tu_a_id', 'loai', 'mo_hinh_phan_bo', 'tien_te', 'thang_tien'}
    if not isinstance(data, dict):
        raise ValueError('Cần dữ liệu liên kết')
    direct = data.get('mo_hinh_phan_bo') == 'DIRECT'
    if data.get('mo_hinh_phan_bo') not in {'DIRECT', 'CHILD'}:
        raise ValueError('Cần mô hình DIRECT hoặc CHILD')
    data = _truong(data, co | (_DICH | {'so_tien_khop_minor'} if direct else {'phan_bo'}),
                   {'chung_tu_b_id'})
    for ten in ('chung_tu_a_id', 'chung_tu_b_id'):
        if data.get(ten) is not None:
            data[ten] = str(UUID(str(data[ten])))
    if (not isinstance(data['loai'], str) or not data['loai'].strip()
            or not isinstance(data['tien_te'], str) or not re.fullmatch('[A-Z]{3}', data['tien_te'])
            or type(data['thang_tien']) is not int or not 0 <= data['thang_tien'] <= 12
            or data['chung_tu_a_id'] == data.get('chung_tu_b_id')):
        raise ValueError('Loại, chứng từ hoặc đơn vị tiền không hợp lệ')
    if direct:
        _tien(data['so_tien_khop_minor'])
        _dich(data)
    else:
        if not isinstance(data['phan_bo'], list) or not data['phan_bo']:
            raise ValueError('Cần phân bổ con')
        con = []
        for dong in data['phan_bo']:
            dong = _dich(_truong(dong, _DICH | {'dich_logic_id', 'cau_phan', 'so_tien_minor'}, set()))
            dong['dich_logic_id'] = str(UUID(str(dong['dich_logic_id'])))
            _tien(dong['so_tien_minor'])
            if dong['cau_phan'] not in {'GOC', 'LAI', 'PHI', 'GIAI_NGAN'}:
                raise ValueError('Cấu phần không hợp lệ')
            con.append(dong)
        if len({d['dich_logic_id'] for d in con}) != len(con):
            raise ValueError('Đích logic bị trùng')
        data['phan_bo'] = con
    return data


def _goi(conn, lenh, lien_ket_id, data, phien_ban_contract, ctx):
    _tx(conn)
    ma, module, pn, hd, viec, the_he = _ngu_canh(**ctx)
    if hd.split(':')[2] != lenh or not isinstance(phien_ban_contract, str) or not phien_ban_contract.strip():
        raise ValueError('Hành động hoặc phiên bản contract không hợp lệ')
    ts = (ma, module, pn, hd, lenh, UUID(str(lien_ket_id)), _json(data), phien_ban_contract, viec, the_he)
    loi = 'LIEN_KET_THAT_BAI'
    try:
        return conn.execute('SELECT danh_muc.lien_ket_v2(%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)', ts).fetchone()[0]
    except Exception as exc:
        chinh = getattr(getattr(exc, 'diag', None), 'message_primary', None)
        if isinstance(chinh, str) and chinh in _LOI:
            loi = chinh
        elif getattr(exc, 'sqlstate', None) == '23505':
            loi = 'LIEN_KET_XUNG_DOT'
    ts = None
    raise LoiLienKet(loi)


def tao(conn, *, lien_ket_id, du_lieu, phien_ban_contract='1', **ctx):
    return _goi(conn, 'LAP', lien_ket_id, _du_lieu(du_lieu), phien_ban_contract, ctx)


def sua(conn, *, lien_ket_id, id_moi, ly_do, du_lieu, phien_ban_contract='1', **ctx):
    data = _du_lieu(du_lieu)
    if not isinstance(ly_do, str) or not ly_do.strip():
        raise ValueError('Cần lý do sửa')
    data.update(id_moi=str(UUID(str(id_moi))), ly_do_huy=ly_do)
    return _goi(conn, 'SUA', lien_ket_id, data, phien_ban_contract, ctx)


def huy(conn, *, lien_ket_id, ly_do, phien_ban_contract='1', **ctx):
    if not isinstance(ly_do, str) or not ly_do.strip():
        raise ValueError('Cần lý do hủy')
    return _goi(conn, 'HUY', lien_ket_id, {'ly_do_huy': ly_do}, phien_ban_contract, ctx)
