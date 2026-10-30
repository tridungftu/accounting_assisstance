"""Cửa danh mục V2; dùng chính transaction/kết nối của caller, không commit.

ID đích được handler xác lập trước; resolver MTQ đã đăng ký phải xác minh
tham chiếu ``danh_muc.<loai>, id`` kể cả lúc tạo mới. Thiếu resolver từ chối.
Module Manager cấp EXECUTE đúng chữ ký SQL, không cấp DML bảng chung.
Nhóm A chờ cổng mã hóa G2-23; cửa này không nhận CCCD/STK/MST cá nhân rõ.
"""

from __future__ import annotations

from datetime import date
import re
from uuid import UUID

from .tai_lieu import _ngu_canh, _so, _truong
from .tiep_nhan import _json, _khoa, _tx


class LoiDanhMuc(RuntimeError):
    def __init__(self, ma):
        self.ma = ma
        self.http_status = (404 if ma in {'DANH_MUC_KHONG_THAY', 'BIEN_NHAN_KHONG_THAY'} else
            409 if ma in {'DANH_MUC_XUNG_DOT', 'KY_DA_KHOA', 'KHOA_CHONG_TRUNG_KHAC_NOI_DUNG',
                         'YEU_CAU_DANG_XU_LY', 'BIEN_NHAN_CORE_HET_HAN'} else
            403 if ma in {'TAI_LIEU_PHIEN', 'TAI_LIEU_MTQ', 'TAI_LIEU_CONG_TAC'} else 400)
        super().__init__('Thao tác danh mục thất bại (' + ma + ')')


_LOI = {'DANH_MUC_KHONG_THAY', 'DANH_MUC_XUNG_DOT', 'DANH_MUC_DAU_VAO', 'DANH_MUC_BAT_BIEN',
        'DANH_MUC_CAN_READ_COMMITTED', 'KY_DA_KHOA', 'TAI_LIEU_PHIEN', 'TAI_LIEU_MTQ',
        'TAI_LIEU_CONG_TAC', 'BIEN_NHAN_KHONG_THAY', 'KHOA_CHONG_TRUNG_KHAC_NOI_DUNG',
        'YEU_CAU_DANG_XU_LY', 'BIEN_NHAN_CORE_HET_HAN'}
_TRUONG = {
    'doi_tac': ({'ten_phap_ly', 'ten_chuan_hoa', 'loai'}, {'mst', 'vai_tro'}),
    'du_an': ({'ma_junsky', 'ten'}, {'cha_id', 'giai_doan', 'trang_thai', 'ngay_chuyen_van_hanh'}),
    'hop_dong': ({'loai', 'ma_noi_bo', 'so_hop_dong'}, {'doi_tac_id', 'du_an_id', 'ngay_ky'}),
    'chung_tu': ({'loai', 'khoa_nguon', 'ngay_nghiep_vu', 'ma_bam'},
                 {'so_tien_minor', 'tien_te', 'thang_tien', 'chieu', 'doi_tac_id', 'du_an_id'}),
    'hoa_don_danh_tinh': ({'chieu', 'mst_ban', 'mau_so', 'ky_hieu', 'so_chuan', 'nguon_cai_dat_id'}, set()),
    'khoa_ky': ({'ky'}, set()),
}


def _goi(conn, cau, ts):
    ma = 'DANH_MUC_THAT_BAI'
    try:
        return conn.execute(cau, ts).fetchone()[0]
    except Exception as exc:
        chinh = getattr(getattr(exc, 'diag', None), 'message_primary', None)
        if isinstance(chinh, str) and chinh in _LOI:
            ma = chinh
        elif getattr(exc, 'sqlstate', None) == '23505':
            ma = 'DANH_MUC_XUNG_DOT'
    ts = None
    raise LoiDanhMuc(ma)


def _du_lieu(loai, data):
    data = _truong(data, *_TRUONG[loai])
    for ten in ('doi_tac_id', 'du_an_id', 'cha_id'):
        if data.get(ten) is not None:
            data[ten] = str(UUID(str(data[ten])))
    for ten in ('ngay_nghiep_vu', 'ngay_ky', 'ngay_chuyen_van_hanh'):
        if data.get(ten) is not None:
            if not isinstance(data[ten], str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', data[ten]):
                raise ValueError('Ngày phải có dạng YYYY-MM-DD')
            date.fromisoformat(data[ten])
    if loai == 'doi_tac' and data['loai'] == 'CN' and data.get('mst') is not None:
        raise ValueError('MST cá nhân phải đi qua cổng mã hóa Core')
    if loai == 'chung_tu':
        if not isinstance(data['ma_bam'], str) or not re.fullmatch('[0-9a-f]{64}', data['ma_bam']):
            raise ValueError('Cần SHA-256 nguồn')
        tien = {'so_tien_minor', 'tien_te', 'thang_tien'} & set(data)
        if tien and (len(tien) != 3 or not isinstance(data['so_tien_minor'], str)
                     or not re.fullmatch(r'(0|[1-9][0-9]{0,37})', data['so_tien_minor'])
                     or not isinstance(data['tien_te'], str) or not re.fullmatch('[A-Z]{3}', data['tien_te'])
                     or type(data['thang_tien']) is not int or not 0 <= data['thang_tien'] <= 12):
            raise ValueError('Cần số tiền minor nguyên dạng chuỗi, tiền tệ và thang tiền; thiếu không điền 0')
    if loai == 'khoa_ky' and (not isinstance(data['ky'], str)
                              or not re.fullmatch(r'[0-9]{4}-(0[1-9]|1[0-2])', data['ky'])):
        raise ValueError('Kỳ phải có dạng YYYY-MM')
    return data


def _ghi(conn, loai, doi_tuong_id, khoa, du_lieu, ctx, phien_ban_contract='1', *, het=False):
    _tx(conn)
    ma, module, pn, hd, viec, the_he = _ngu_canh(**ctx)
    can = 'SUA' if het else 'DUYET' if loai == 'khoa_ky' else 'LAP'
    if hd.split(':')[2] != can or not isinstance(phien_ban_contract, str) or not phien_ban_contract.strip():
        raise ValueError('Hành động hoặc phiên bản contract không hợp lệ')
    return _goi(conn, '''SELECT danh_muc.ghi_v2(
        %s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)''',
        (ma, module, pn, hd, loai, UUID(str(doi_tuong_id)), _khoa(khoa),
         _json(du_lieu), phien_ban_contract, viec, the_he))


def ghi(conn, *, loai, doi_tuong_id, khoa, du_lieu, phien_ban_contract='1', **ctx):
    """Thêm bản ghi; không upsert/ghi đè bản cũ hoặc nhận actor từ request."""
    if loai not in _TRUONG:
        raise ValueError('Loại danh mục không được ghi qua cửa này')
    return _ghi(conn, loai, doi_tuong_id, khoa, _du_lieu(loai, du_lieu), ctx, phien_ban_contract)


def ghi_doi_tac(conn, **ts):
    return ghi(conn, loai='doi_tac', **ts)


def ghi_du_an(conn, **ts):
    return ghi(conn, loai='du_an', **ts)


def ghi_hop_dong(conn, **ts):
    return ghi(conn, loai='hop_dong', **ts)


def ghi_chung_tu(conn, **ts):
    return ghi(conn, loai='chung_tu', **ts)


def ghi_hoa_don_danh_tinh(conn, **ts):
    return ghi(conn, loai='hoa_don_danh_tinh', **ts)


def khoa_ky(conn, *, ky, **ts):
    return ghi(conn, loai='khoa_ky', du_lieu={'ky': ky}, **ts)


def het_hieu_luc(conn, *, loai, doi_tuong_id, khoa, row_version, phien_ban_contract='1', **ctx):
    if loai not in _TRUONG or loai == 'khoa_ky':
        raise ValueError('Không được hết hiệu lực loại này')
    data = {'row_version': str(_so(row_version, chuoi=True))}
    return _ghi(conn, loai, doi_tuong_id, khoa, data, ctx, phien_ban_contract, het=True)


def kiem_khoa_ky(conn, *, chung_tu_id, phien_ban_contract='1', **ctx):
    """Adapter gọi trong transaction trước duyệt; khóa được giữ đến commit."""
    _tx(conn)
    ma, module, pn, hd, viec, the_he = _ngu_canh(**ctx)
    if hd.split(':')[2] not in {'LAP', 'SUA', 'DUYET'}:
        raise ValueError('Cần hành động ghi/duyệt')
    return _goi(conn, 'SELECT danh_muc.kiem_khoa_ky_v2(%s,%s,%s,%s,%s,%s,%s,%s)',
                (ma, module, pn, hd, UUID(str(chung_tu_id)), phien_ban_contract, viec, the_he))
