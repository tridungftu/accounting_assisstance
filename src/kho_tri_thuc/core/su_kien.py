"""G2-15: nâng bus XS-1/M0052 sang Core, giữ dedupe và caller-owned tx.

Phát cùng transaction nghiệp vụ. Nhận giữ khóa inbox tới hết transaction;
ghi kết quả và ACK trên chính kết nối đó. Exception phải thoát transaction.
``xu_ly`` ghép nhận/handler/ACK theo quy tắc này; không tự mở/commit/rollback.
Giao ít nhất một lần, không bảo đảm exactly-once cho tác động ngoài PostgreSQL.
Contract chỉ tham chiếu UUID; schema chưa hỗ trợ bị từ chối ở SQL.
"""

from collections.abc import Mapping
import json
import re
from uuid import UUID

from .tai_lieu import _ngu_canh
from .tiep_nhan import _tx


class LoiSuKien(RuntimeError):
    def __init__(self, ma):
        self.ma = ma
        self.http_status = 409 if ma in {'BUS_DEDUPE_XUNG_DOT', 'BUS_CHUA_NHAN'} else (
            403 if ma in {'BUS_PHIEN', 'BUS_DANG_KY', 'BUS_CONG_TAC'} else 400)
        super().__init__('Thao tác sự kiện thất bại (' + ma + ')')


_LOI = {'BUS_PHIEN', 'BUS_DANG_KY', 'BUS_CONG_TAC', 'BUS_CONTRACT', 'BUS_PAYLOAD',
        'BUS_DAU_VAO', 'BUS_DEDUPE_XUNG_DOT', 'BUS_CHUA_NHAN', 'BUS_CAN_READ_COMMITTED'}


def _goi(conn, cau, ts):
    ma = 'BUS_THAT_BAI'
    try:
        row = conn.execute(cau, ts).fetchone()
        return row['r'] if isinstance(row, Mapping) else row[0]
    except Exception as exc:
        chinh = getattr(getattr(exc, 'diag', None), 'message_primary', None)
        if isinstance(chinh, str) and chinh in _LOI:
            ma = chinh
    ts = None
    raise LoiSuKien(ma)


def _ctx(conn, ctx):
    _tx(conn)
    return _ngu_canh(**ctx)


def _loai(loai):
    if not isinstance(loai, str) or not re.fullmatch('[a-z][a-z0-9_.]{0,95}', loai):
        raise ValueError('Loại sự kiện không hợp lệ')
    return loai


def phat(conn, loai, phien_ban, tham_chieu, khoa, **ctx):
    """Trả UUID, cùng khóa/cùng nội dung trả lại UUID cũ; không commit."""
    ts = _ctx(conn, ctx)
    _loai(loai)
    if (type(phien_ban) is not int or not 1 <= phien_ban <= 2**31-1
            or not isinstance(khoa, str) or not 1 <= len(khoa) <= 200 or khoa != khoa.strip()
            or not isinstance(tham_chieu, dict) or not tham_chieu
            or ts[3].split(':')[2] not in {'LAP', 'SUA', 'DUYET'}):
        raise ValueError('Thông tin sự kiện không hợp lệ')
    # SQL kiểm lại toàn bộ, kể cả trường UUID không được contract khai báo.
    for k, v in tham_chieu.items():
        if isinstance(k, str) and re.fullmatch('[a-z][a-z0-9_]*_id', k) and isinstance(v, str):
            UUID(v)
        elif isinstance(k, str) and re.fullmatch('[a-z][a-z0-9_]*_ids', k) and isinstance(v, list):
            for item in v:
                if not isinstance(item, str):
                    raise ValueError('Tham chiếu phải là UUID')
                UUID(item)
        else:
            raise ValueError('Payload chỉ chứa tham chiếu UUID')
    return _goi(conn, 'SELECT loi.su_kien_phat(%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s) AS r',
                (*ts[:4], loai, phien_ban, khoa, json.dumps(tham_chieu, allow_nan=False), *ts[4:]))


def nhan(conn, loai=None, gioi_han=100, **ctx):
    """Trả list dict, giữ khóa inbox cho đến khi caller commit/rollback."""
    ts = _ctx(conn, ctx)
    if loai is not None:
        _loai(loai)
    if type(gioi_han) is not int or not 1 <= gioi_han <= 1000:
        raise ValueError('Giới hạn phải từ 1 tới 1000')
    return _goi(conn, 'SELECT loi.su_kien_nhan(%s,%s,%s,%s,%s,%s,%s,%s) AS r',
                (*ts[:4], loai, gioi_han, *ts[4:]))


def ack(conn, su_kien_id, **ctx):
    """ACK đầu True, lặp False; chưa nhận bị từ chối. Cùng tx xử lý."""
    ts = _ctx(conn, ctx)
    return _goi(conn, 'SELECT loi.su_kien_ack(%s,%s,%s,%s,%s,%s,%s) AS r',
                (*ts[:4], UUID(str(su_kien_id)), *ts[4:]))


def xu_ly(conn, handler, loai=None, gioi_han=100, **ctx):
    """Handler nhận (conn, sự kiện); lỗi phải thoát transaction của caller."""
    so = 0
    for sk in nhan(conn, loai, gioi_han, **ctx):
        handler(conn, sk)
        ack(conn, sk['id'], **ctx)
        so += 1
    return so
