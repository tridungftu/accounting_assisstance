"""G2-11: cửa V2 tiếp nhận và biên nhận; không mở kết nối/transaction/commit.

Module dùng ``thuc_hien_thao_tac`` TRONG transaction nghiệp vụ: tra và giữ khóa,
gọi nghiệp vụ bằng chính kết nối đó, rồi ghi biên nhận. Exception phải thoát
transaction để caller rollback cả nghiệp vụ lẫn biên nhận. Quyen_doc do handler
module dựng từ kết quả thực, không lấy từ request; SQL kiểm quyền hiện hành.

Fingerprint tính trong CSDL từ operation + body JSONB logic (gồm pháp nhân,
tham chiếu đích, contract và nội dung). Alias route dùng cùng các giá trị này.
Biên nhận Core hết hạn bị chặn để đối soát, không tự thực hiện lại nghiệp vụ.
G2-29 nối dọn payload; G2-14 nối trạng thái việc bền vững vào ghi_core.
"""

from __future__ import annotations

import json
import re
from uuid import UUID

from .tai_lieu import _ngu_canh


class LoiTiepNhan(RuntimeError):
    def __init__(self, ma):
        self.ma = ma
        self.http_status = 404 if ma in {'BIEN_NHAN_KHONG_THAY', 'TIEP_NHAN_KHONG_THAY'} else (
            409 if ma in {'KHOA_CHONG_TRUNG_KHAC_NOI_DUNG', 'YEU_CAU_DANG_XU_LY', 'BIEN_NHAN_CORE_HET_HAN'} else 400)
        super().__init__('Thao tác tiếp nhận thất bại (' + ma + ')')


_LOI = {'TIEP_NHAN_CHI_CORE', 'TIEP_NHAN_DAU_VAO', 'TIEP_NHAN_KHONG_THAY',
        'BIEN_NHAN_DAU_VAO', 'BIEN_NHAN_KHONG_THAY', 'BIEN_NHAN_CORE_HET_HAN',
        'KHOA_CHONG_TRUNG_KHAC_NOI_DUNG', 'YEU_CAU_DANG_XU_LY',
        'TAI_LIEU_PHIEN', 'TAI_LIEU_MTQ', 'TAI_LIEU_CONG_TAC'}


def _tx(conn):
    # psycopg pq.TransactionStatus.INTRANS=2; không import driver ở đường thuần.
    if conn.info.transaction_status != 2:
        raise ValueError('Cần transaction đang mở trên chính kết nối nghiệp vụ')


def _json(data):
    def kiem(v):
        if isinstance(v, dict):
            if any(not isinstance(k, str) for k in v):
                raise ValueError('Khóa JSON phải là chuỗi')
            for x in v.values():
                kiem(x)
        elif isinstance(v, list):
            for x in v:
                kiem(x)
    kiem(data)
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _khoa(khoa):
    if not isinstance(khoa, str) or not re.fullmatch(r'[A-Za-z0-9._:-]{16,128}', khoa):
        raise ValueError('Khóa chống trùng phải có 16–128 ký tự ASCII an toàn')
    return khoa


def _goi(conn, cau, ts):
    ma = 'TIEP_NHAN_THAT_BAI'
    try:
        return conn.execute(cau, ts).fetchone()[0]
    except Exception as exc:
        chinh = getattr(getattr(exc, 'diag', None), 'message_primary', None)
        if isinstance(chinh, str) and chinh in _LOI:
            ma = chinh
    # Không nối lỗi driver chứa bind/token; raise sau except để bỏ __context__.
    ts = None
    raise LoiTiepNhan(ma)


def _than(noi_dung, doi_tuong, phap_nhan_id, phien_ban_contract):
    if not isinstance(noi_dung, dict) or not isinstance(doi_tuong, dict) or set(doi_tuong) != {'bang', 'id'}:
        raise ValueError('Cần body logic và tham chiếu đối tượng')
    if not isinstance(doi_tuong['bang'], str) or not doi_tuong['bang'].strip():
        raise ValueError('Tham chiếu đối tượng không hợp lệ')
    if not isinstance(phien_ban_contract, str) or not phien_ban_contract.strip():
        raise ValueError('Cần phiên bản contract')
    return _json(dict(phap_nhan_id=str(UUID(str(phap_nhan_id))),
        doi_tuong=dict(bang=doi_tuong['bang'], id=str(UUID(str(doi_tuong['id'])))),
        phien_ban_contract=phien_ban_contract, noi_dung=noi_dung))


def _bien_nhan(conn, *, core, ghi, operation, khoa, noi_dung, doi_tuong,
               phien_ban_contract='1', ket_qua=None, quyen_doc=None, trang_thai='HOAN_TAT', **ctx):
    _tx(conn)
    ma, module, pn, hd, viec, the_he = _ngu_canh(**ctx)
    if not isinstance(operation, str) or not re.fullmatch(r'[A-Za-z0-9._:-]{3,120}', operation):
        raise ValueError('Operation không hợp lệ')
    if hd.split(':')[2] not in {'LAP', 'SUA', 'DUYET', 'HUY'}:
        raise ValueError('Cần quyền hành động nghiệp vụ')
    than = _than(noi_dung, doi_tuong, pn, phien_ban_contract)
    ts = (ma, module, pn, hd, operation, _khoa(khoa), than)
    if ghi and (ket_qua is None or not isinstance(quyen_doc, dict)):
        raise ValueError('Cần kết quả và căn cứ đọc kết quả do handler xác lập')
    if core:
        if trang_thai not in {'DANG_XU_LY', 'CHUA_RO', 'HOAN_TAT'}:
            raise ValueError('Trạng thái biên nhận Core không hợp lệ')
        return _goi(conn, '''SELECT loi_tai_lieu.bien_nhan_core_v2(
            %s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s::jsonb,%s,%s,%s)''',
            ts + (ghi, _json(ket_qua) if ghi else None, _json(quyen_doc) if ghi else None, trang_thai, viec, the_he))
    if ghi:
        return _goi(conn, '''SELECT loi_tai_lieu.ghi_bien_nhan_thao_tac_v2(
            %s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s)''',
            ts + (_json(ket_qua), _json(quyen_doc), viec, the_he))
    return _goi(conn, '''SELECT loi_tai_lieu.tra_bien_nhan_thao_tac_v2(
        %s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)''', ts + (viec, the_he))


def tra_thao_tac(conn, **ts):
    return _bien_nhan(conn, core=False, ghi=False, **ts)


def ghi_thao_tac(conn, **ts):
    return _bien_nhan(conn, core=False, ghi=True, **ts)


def thuc_hien_thao_tac(conn, *, thuc_hien, quyen_doc, **ts):
    """Callable nghiệp vụ nhận đúng conn; callable quyen_doc nhận kết quả thực."""
    cu = tra_thao_tac(conn, **ts)
    if cu is not None:
        return cu
    ket_qua = thuc_hien(conn)
    _tx(conn)
    return ghi_thao_tac(conn, ket_qua=ket_qua,
        quyen_doc=quyen_doc(ket_qua) if callable(quyen_doc) else quyen_doc, **ts)


def tra_core(conn, **ts):
    return _bien_nhan(conn, core=True, ghi=False, **ts)


def ghi_core(conn, **ts):
    """Chỉ Core gọi; HOAN_TAT chỉ sau kết quả cuối, CHUA_RO giữ đến đối soát."""
    return _bien_nhan(conn, core=True, ghi=True, **ts)


def nhan_nguon(conn, *, nguon_cai_dat, tham_chieu, ma_bam_ho_so, khong_gian, khoa, du_lieu, **ctx):
    """Core nhận dữ liệu đã kiểm; không nhận actor/pháp nhân định tuyến từ client.

    ``ctx.phap_nhan_id`` là workspace thật của phiên, không phải pháp nhân của
    dữ liệu nguồn. Hai bảng prePN giữ NULL cho đến bước định tuyến riêng.
    """
    _tx(conn)
    ma, module, pn, hd, viec, the_he = _ngu_canh(**ctx)
    if viec is not None or the_he is not None or hd.split(':')[2] not in {'LAP', 'SUA'}:
        raise ValueError('Ngữ cảnh tiếp nhận không hợp lệ')
    if (not isinstance(nguon_cai_dat, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,120}', nguon_cai_dat)
        or not isinstance(tham_chieu, str) or not 1 <= len(tham_chieu) <= 300
        or not isinstance(ma_bam_ho_so, str) or not re.fullmatch('[0-9a-f]{64}', ma_bam_ho_so)
        or not isinstance(khong_gian, str) or not 1 <= len(khong_gian) <= 120 or not isinstance(du_lieu, dict)):
        raise ValueError('Thông tin nguồn không hợp lệ')
    return _goi(conn, '''SELECT loi_tai_lieu.tiep_nhan_v2(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)''',
        (ma, module, pn, hd, nguon_cai_dat, tham_chieu, ma_bam_ho_so, khong_gian, _khoa(khoa), _json(du_lieu)))


def doc_vung_tam(conn, *, lan_tiep_nhan_id, **ctx):
    _tx(conn)
    ma, module, pn, hd, viec, the_he = _ngu_canh(**ctx)
    if hd.split(':')[2] != 'XEM' or viec is not None or the_he is not None:
        raise ValueError('Cần phiên đọc nguồn')
    return _goi(conn, 'SELECT loi_tai_lieu.doc_vung_tam_v2(%s,%s,%s,%s,%s)',
        (ma, module, pn, hd, UUID(str(lan_tiep_nhan_id))))
