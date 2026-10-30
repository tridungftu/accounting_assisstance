"""Metadata kho Core G2-09; caller giữ transaction và kết nối login Core.

Không đọc/ghi bytes, không tự kết nối/commit. ``ghi_ket_qua_core`` chỉ nhận
metadata nguồn do tầng Core đã xác minh, không chuyển payload module vào
``thong_tin_core``. SQL kiểm login lần nữa. G2-10 nối kho bất biến/hash hiện có;
G2-14/16 nối kiểm instance, bước/lần thử và lease trước cửa ghi này.
"""

from __future__ import annotations

import json
import re
from uuid import UUID

from .phien import MaBiMat


class LoiTaiLieu(RuntimeError):
    def __init__(self, ma):
        self.ma = ma
        super().__init__('Thao tác tài liệu thất bại (' + ma + ')')


_LOI = {'TAI_LIEU_PHIEN', 'TAI_LIEU_MTQ', 'TAI_LIEU_CONG_TAC', 'TAI_LIEU_CHI_CORE',
        'TAI_LIEU_DAU_VAO', 'TAI_LIEU_KHONG_THAY', 'TAI_LIEU_REVISION',
        'TAI_LIEU_NGUON', 'TAI_LIEU_THIEU_TEP_HASH', 'TAI_LIEU_NOI_DUNG'}
_BIEN_THE = {'goc', 'ocr', 'da_che', 'noi_dung', 'phan_hoi_nguon'}
_NGUON_CORE = {'phien_ban_module', 'engine_id', 'ham', 'phien_ban_ham', 'buoc_id', 'lan_thu_id'}


def _goi(conn, cau, ts):
    ma = 'TAI_LIEU_THAT_BAI'
    try:
        return conn.execute(cau, ts).fetchone()[0]
    except Exception as exc:
        chinh = getattr(getattr(exc, 'diag', None), 'message_primary', None)
        if isinstance(chinh, str) and chinh in _LOI:
            ma = chinh
    ts = None
    raise LoiTaiLieu(ma)


def _truong(data, can, tuy_chon=()):
    if not isinstance(data, dict) or not set(can) <= set(data) or set(data) - set(can) - set(tuy_chon):
        raise ValueError('Thiếu trường bắt buộc hoặc có trường ngoài phạm vi')
    return dict(data)


def _so(so, *, chuoi=False):
    if chuoi:
        if not isinstance(so, str) or not re.fullmatch(r'[1-9][0-9]{0,18}', so):
            raise ValueError('row_version phải là chuỗi số nguyên dương')
        so = int(so)
    if type(so) is not int or not (1 if chuoi else 0) <= so <= 9223372036854775807:
        raise ValueError('Revision không hợp lệ')
    return so


def _bien_the(bt):
    if not isinstance(bt, str) or bt not in _BIEN_THE:
        raise ValueError('Biến thể không hợp lệ')
    return bt


def _ngu_canh(*, ma, module, phap_nhan_id, hanh_dong, viec_id=None, the_he=None):
    if not isinstance(ma, MaBiMat):
        raise ValueError('Cần mã phiên bí mật')
    if not isinstance(module, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,30}', module) or module == 'core':
        raise ValueError('Module không hợp lệ')
    if (not isinstance(hanh_dong, str) or not re.fullmatch(r'[A-Z0-9_]+:[A-Z0-9_]+:[A-Z_]+', hanh_dong)
            or hanh_dong.split(':')[0] != module.upper()):
        raise ValueError('Hành động không thuộc module')
    if (viec_id is None) != (the_he is None) or (the_he is not None and (
        type(the_he) is not int or not 0 < the_he <= 9223372036854775807
    )):
        raise ValueError('Việc và thế hệ không hợp lệ')
    return (ma.lay_de_truyen(), module, UUID(str(phap_nhan_id)), hanh_dong,
            None if viec_id is None else UUID(str(viec_id)), the_he)


def _ghi(conn, loai, tai_lieu_id, data, request_id, ctx):
    ma, module, pn, hd, viec, the_he = _ngu_canh(**ctx)
    can = {'DUYET'} if loai in ('quyen', 'duyet', 'cong_bo') else {'LAP', 'SUA'}
    if hd.split(':')[2] not in can:
        raise ValueError('Hành động không phù hợp thao tác')
    return _goi(conn, '''SELECT loi_tai_lieu.ghi_metadata(
        %s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)''',
        (ma, module, pn, hd, loai, UUID(str(tai_lieu_id)),
         json.dumps(data, ensure_ascii=False, allow_nan=False), UUID(str(request_id)), viec, the_he))


def tao(conn, *, tai_lieu_id, thong_tin, request_id, **ctx):
    """Tham chiếu đối tượng từ máy chủ; MTQ resolver kiểm lại, thiếu thì từ chối."""
    data = _truong(thong_tin, {'loai', 'ten', 'doi_tuong', 'phien_ban_contract'})
    doi = _truong(data['doi_tuong'], {'bang', 'id'})
    doi['id'] = str(UUID(str(doi['id'])))
    if not isinstance(doi['bang'], str) or not doi['bang'].strip():
        raise ValueError('Cần tham chiếu đối tượng')
    data['doi_tuong'] = doi
    return _ghi(conn, 'tai_lieu', tai_lieu_id, data, request_id, ctx)


def ghi_tep_da_kiem(conn, *, tai_lieu_id, thong_tin, request_id, **ctx):
    """Chỉ Core gọi sau khi kho đã ghi bất biến và kiểm hash/size/MIME thực."""
    data = _truong(thong_tin, {'ten_tep', 'sha256', 'kich_thuoc', 'mime', 'khoa_luu_tru'}, {'het_han_luc'})
    if not isinstance(data['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', data['sha256']):
        raise ValueError('SHA-256 không hợp lệ')
    if type(data['kich_thuoc']) is not int or not 0 <= data['kich_thuoc'] <= 9007199254740991:
        raise ValueError('Kích thước không hợp lệ')
    return _ghi(conn, 'tep', tai_lieu_id, data, request_id, ctx)


def gan_bien_the(conn, *, tai_lieu_id, tep_id, bien_the, revision_truoc, request_id, **ctx):
    return _ghi(conn, 'bien_the', tai_lieu_id, dict(tep_id=str(UUID(str(tep_id))),
        bien_the=_bien_the(bien_the), revision_truoc=_so(revision_truoc)), request_id, ctx)


def cap_quyen(conn, *, tai_lieu_id, du_lieu, request_id, **ctx):
    data = _truong(du_lieu, {'nguoi_dung_id', 'bien_the', 'cho_phep', 'revision_truoc'}, {'hieu_luc_den'})
    data['nguoi_dung_id'] = str(UUID(str(data['nguoi_dung_id'])))
    if data['bien_the'] != '*':
        _bien_the(data['bien_the'])
    if type(data['cho_phep']) is not bool:
        raise ValueError('Cờ quyền không hợp lệ')
    _so(data['revision_truoc'])
    return _ghi(conn, 'quyen', tai_lieu_id, data, request_id, ctx)


def ghi_ket_qua_core(conn, *, tai_lieu_id, du_lieu, thong_tin_core, request_id, **ctx):
    """Cửa nội bộ: payload không được chứa actor/engine/function hay trạng thái duyệt.

    Nguồn là tham chiếu đã kiểm, SQL đối chiếu hash/revision/pháp nhân. Sửa nội
    dung tạo ID mới trong cùng goc_id; duyệt luôn bắt đầu lại ở chua_duyet.
    """
    data = _truong(du_lieu, {'tep_id', 'bien_the', 'ma_contract', 'phien_ban_contract',
        'trang_thai', 'ly_do', 'revision_truoc', 'nguon'}, {'goc_id'})
    core = _truong(thong_tin_core, {'phien_ban_module', 'ham', 'phien_ban_ham'},
                   _NGUON_CORE - {'phien_ban_module', 'ham', 'phien_ban_ham'})
    _bien_the(data['bien_the'])
    _so(data['revision_truoc'])
    if data['trang_thai'] not in ('cho', 'dang_xu_ly', 'thanh_cong', 'loi'):
        raise ValueError('Trạng thái xử lý không hợp lệ')
    for khoa in ('tep_id', 'goc_id'):
        if data.get(khoa) is not None:
            data[khoa] = str(UUID(str(data[khoa])))
    if not isinstance(data['nguon'], list):
        raise ValueError('Cần danh sách tham chiếu nguồn')
    nguon = []
    for n in data['nguon']:
        n = _truong(n, {'sha256'}, {'tep_id', 'ket_qua_id', 'revision', 'trang', 'dinh_vi', 'trich_dan'})
        if (n.get('tep_id') is None) == (n.get('ket_qua_id') is None):
            raise ValueError('Cần đúng một tham chiếu nguồn')
        if not isinstance(n['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', n['sha256']):
            raise ValueError('SHA-256 nguồn không hợp lệ')
        if n.get('ket_qua_id') is not None:
            if _so(n.get('revision')) < 1:
                raise ValueError('Cần revision nguồn')
        elif 'revision' in n:
            raise ValueError('Revision chỉ áp dụng nguồn kết quả')
        for khoa in ('tep_id', 'ket_qua_id'):
            if n.get(khoa) is not None:
                n[khoa] = str(UUID(str(n[khoa])))
        nguon.append(n)
    data['nguon'] = nguon
    for khoa in ('engine_id', 'buoc_id', 'lan_thu_id'):
        if core.get(khoa) is not None:
            core[khoa] = str(UUID(str(core[khoa])))
    return _ghi(conn, 'ket_qua', tai_lieu_id, {**data, **core}, request_id, ctx)


def duyet(conn, *, tai_lieu_id, ket_qua_id, row_version, trang_thai_duyet, request_id, **ctx):
    _so(row_version, chuoi=True)
    if trang_thai_duyet not in ('chua_duyet', 'da_duyet', 'tu_choi'):
        raise ValueError('Trạng thái duyệt không hợp lệ')
    return _ghi(conn, 'duyet', tai_lieu_id, dict(ket_qua_id=str(UUID(str(ket_qua_id))),
        row_version=row_version, trang_thai_duyet=trang_thai_duyet), request_id, ctx)


def cong_bo(conn, *, tai_lieu_id, ket_qua_id, request_id, **ctx):
    """SQL kiểm lại quyền nội dung hiện hành của kết quả và các nguồn trước công bố."""
    return _ghi(conn, 'cong_bo', tai_lieu_id, {'ket_qua_id': str(UUID(str(ket_qua_id)))}, request_id, ctx)


def lay(conn, *, tai_lieu_id, bien_the, **ctx):
    """Mỗi lần đọc đều kiểm lại quyền hiện hành, kể cả nguồn của kết quả đã công bố."""
    ma, module, pn, hd, viec, the_he = _ngu_canh(**ctx)
    if hd.split(':')[2] != 'XEM':
        raise ValueError('Cần hành động xem')
    return _goi(conn, 'SELECT loi_tai_lieu.doc_metadata(%s,%s,%s,%s,%s,%s,%s,%s)',
        (ma, module, pn, hd, UUID(str(tai_lieu_id)), _bien_the(bien_the), viec, the_he))
