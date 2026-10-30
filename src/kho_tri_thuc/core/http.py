"""Biên WSGI JSON v1; không mở cổng hoặc thay đường phục vụ cũ.

``doc_phien(hash_sid)`` là kho phiên backend: kiểm hạn/thu hồi rồi cập nhật last-used
nguyên tử và trả PhienHTTP. SID browser không phải mã CSDL G2-03. Bộ ghép ứng
dụng cung cấp kho này; không dùng danh tính client hoặc kho phiên DEMO cũ.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from http import HTTPStatus
from http.cookies import SimpleCookie, CookieError
import json
import re
import secrets
from urllib.parse import parse_qsl, urlsplit
from uuid import UUID, uuid4

from . import goi
from .phien import MaBiMat


GIOI_HAN_JSON = 1024 * 1024
_LOI = {
    400: ('YEU_CAU_KHONG_HOP_LE', 'Yêu cầu không hợp lệ.'),
    401: ('CHUA_DANG_NHAP', 'Anh đăng nhập lại để tiếp tục.'),
    403: ('KHONG_DU_QUYEN', 'Yêu cầu không được phép.'),
    404: ('KHONG_TIM_THAY', 'Không tìm thấy tài nguyên.'),
    405: ('PHUONG_THUC_KHONG_HO_TRO', 'Phương thức không được hỗ trợ.'),
    409: ('XUNG_DOT_PHIEN_BAN', 'Dữ liệu đã thay đổi. Anh tải lại trước khi lưu.'),
    410: ('KET_QUA_HET_HAN', 'Tệp hoặc kết quả tạm đã hết hạn.'),
    413: ('JSON_QUA_LON', 'Nội dung JSON vượt quá 1 MiB.'),
    415: ('MIME_KHONG_HO_TRO', 'Cần nội dung JSON UTF-8.'),
    422: ('SAI_SCHEMA', 'Dữ liệu không đúng contract.'),
    429: ('VUOT_HAN_MUC', 'Đã vượt hạn mức xử lý. Anh thử lại sau.'),
    500: ('LOI_NOI_BO', 'Không xử lý được yêu cầu.'),
    502: ('PHAN_HOI_SAI_CONTRACT', 'Phản hồi không đúng contract.'),
    503: ('CHUA_SAN_SANG', 'Dịch vụ chưa sẵn sàng.'),
    504: ('HET_THOI_HAN', 'Hết thời hạn chờ phản hồi.'),
}


class LoiHTTP(Exception):
    """Chỉ mã/thông điệp do Core sở hữu, không nhận thông báo exception."""

    def __init__(self, status, *, ma=None, thong_diep=None, headers=None):
        self.status = status
        mac_dinh = _LOI[status]
        self.ma = ma or mac_dinh[0]
        self.thong_diep = thong_diep or mac_dinh[1]
        self.headers = headers or {}
        super().__init__(self.ma)


@dataclass(frozen=True, repr=False)
class PhienHTTP:
    nguoi_dung_id: UUID | None
    csrf: MaBiMat
    lay_ma: object  # (module, phap_nhan_id) -> MaBiMat G2-03, chỉ Core gọi
    tao_luc: datetime
    hoat_dong_luc: datetime
    tien_phien: bool = False

    def con_han(self, luc):
        try:
            tuoi = (luc - self.tao_luc).total_seconds()
            ranh = (luc - self.hoat_dong_luc).total_seconds()
            return (0 <= tuoi < (600 if self.tien_phien else 28800)
                    and 0 <= ranh < (600 if self.tien_phien else 1800))
        except (TypeError, ValueError):
            return False


@dataclass(frozen=True, repr=False)
class YeuCauHTTP:
    method: str
    path: str
    headers: dict = field(repr=False)
    query: dict
    body: object
    request_id: str
    phien: PhienHTTP | None = field(repr=False)


@dataclass(frozen=True, repr=False)
class PhanHoi:
    status: int
    body: object = None
    headers: dict = field(default_factory=dict)
    da_commit: bool = False  # Kênh module chỉ đặt sau khi transaction thoát thành công.


def loi_response(loi, request_id):
    return PhanHoi(loi.status, dict(ma=loi.ma, thong_diep=loi.thong_diep,
        request_id=request_id, thu_lai_duoc=loi.status in {503}), loi.headers)


def doc_json(stream, length=None):
    """Đọc tối đa limit+1 byte, chặn ngay byte vượt; không đọc hết luồng trước."""
    if length is not None and length > GIOI_HAN_JSON:
        raise LoiHTTP(413)
    chunks, tong = [], 0
    while length is None or tong < length:
        n = min(65536, GIOI_HAN_JSON + 1 - tong)
        if length is not None:
            n = min(n, length - tong)
        raw = stream.read(n)
        if not isinstance(raw, bytes) or len(raw) > n:
            raise LoiHTTP(400)
        if not raw:
            if length is not None and tong != length:
                raise LoiHTTP(400)
            break
        tong += len(raw)
        if tong > GIOI_HAN_JSON:
            raise LoiHTTP(413)
        chunks.append(raw)
    if not tong:
        return None
    try:
        return goi.doc_json(b''.join(chunks), goi.GioiHan(json=GIOI_HAN_JSON))
    except goi.LoiGoi:
        pass
    raise LoiHTTP(400)


class UngDungHTTP:
    def __init__(self, dispatcher, *, origin, doc_phien, dong_ho=None):
        parsed = urlsplit(origin)
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname
                or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment
                or (parsed.scheme != 'https' and parsed.hostname not in {'127.0.0.1', 'localhost', '::1'})):
            raise ValueError('Nguồn Core phải dùng TLS hoặc DEMO loopback')
        self.dispatcher, self.origin, self.host = dispatcher, origin, parsed.netloc
        self.doc_phien = doc_phien
        self.dong_ho = dong_ho or (lambda: datetime.now(timezone.utc))

    def _phien(self, cookie, *, tien_phien=False):
        ten = '__Host-ktt_tien_phien' if tien_phien else '__Host-ktt_phien'
        # Cookie trùng tên bị từ chối, không chọn tùy tiện first/last.
        if sum(p.strip().split('=', 1)[0] == ten for p in cookie.split(';')) > 1:
            raise LoiHTTP(400)
        try:
            jar = SimpleCookie()
            jar.load(cookie)
            sid = jar[ten].value if ten in jar else ''
        except CookieError:
            raise LoiHTTP(400) from None
        if not sid or len(sid) > 4096:
            return None
        phien = self.doc_phien(hashlib.sha256(sid.encode('utf-8')).hexdigest())
        if (not isinstance(phien, PhienHTTP) or phien.tien_phien != tien_phien
                or not isinstance(phien.csrf, MaBiMat) or not phien.con_han(self.dong_ho())):
            return None
        return phien

    def _nhan(self, env, request_id):
        headers = {k[5:].replace('_', '-').lower(): v
                   for k, v in env.items() if k.startswith('HTTP_')}
        if headers.get('host') != self.host or headers.get('sec-fetch-site') == 'cross-site':
            raise LoiHTTP(403)
        method, path = env.get('REQUEST_METHOD', ''), env.get('PATH_INFO', '')
        if headers.get('origin') and headers['origin'] != self.origin:
            raise LoiHTTP(403)
        phien = self._phien(headers.get('cookie', ''))
        if phien is None:
            route, _ = self.dispatcher.registry.tra(method, path)
            if route.phien in {'tien_phien', 'khong'}:
                phien = self._phien(headers.get('cookie', ''), tien_phien=True)
        if method not in {'GET', 'HEAD', 'OPTIONS'}:
            csrf = headers.get('x-csrf-token', '')
            if (headers.get('origin') != self.origin or phien is None
                    or not secrets.compare_digest(csrf.encode('utf-8'),
                                                  phien.csrf.lay_de_truyen().encode('utf-8'))):
                raise LoiHTTP(403)
        try:
            raw_query = env.get('QUERY_STRING', '')
            if re.search(r'%(?![0-9A-Fa-f]{2})', raw_query):
                raise ValueError()
            pairs = parse_qsl(raw_query, keep_blank_values=True,
                              encoding='utf-8', errors='strict', max_num_fields=100)
            query = dict(pairs)
            if len(query) != len(pairs):
                raise ValueError()
        except (ValueError, UnicodeError):
            raise LoiHTTP(400) from None
        length = env.get('CONTENT_LENGTH', '')
        if length and (len(length) > 12 or not length.isascii() or not length.isdigit()):
            raise LoiHTTP(400)
        if headers.get('transfer-encoding') and length:
            raise LoiHTTP(400)
        length = int(length) if length else None
        terminated = env.get('wsgi.input_terminated', False)
        if length is None and not terminated:
            if method in {'POST', 'PUT', 'PATCH'}:
                raise LoiHTTP(400)
            length = 0
        body = None
        if length != 0:
            mime = env.get('CONTENT_TYPE', '').lower().replace(' ', '')
            if mime not in {'application/json', 'application/json;charset=utf-8'}:
                raise LoiHTTP(415)
            body = doc_json(env['wsgi.input'], length)
        return YeuCauHTTP(method, path, headers, query, body, request_id, phien)

    def __call__(self, env, start_response):
        request_id = str(uuid4())  # Không tin X-Request-Id client.
        try:
            request = self._nhan(env, request_id)
            response = self.dispatcher.dispatch(request)
            raw = b'' if response.status == 204 else json.dumps(
                response.body, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
        except LoiHTTP as exc:
            response = loi_response(exc, request_id)
            raw = json.dumps(response.body, ensure_ascii=False).encode('utf-8')
        except Exception:
            response = loi_response(LoiHTTP(500), request_id)
            raw = json.dumps(response.body, ensure_ascii=False).encode('utf-8')
        headers = {'Content-Type': 'application/json; charset=utf-8', 'Content-Length': str(len(raw)),
                   'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                   **response.headers, 'X-Request-Id': request_id}
        start_response(f'{response.status} {HTTPStatus(response.status).phrase}', list(headers.items()))
        return [b'' if env.get('REQUEST_METHOD') == 'HEAD' else raw]
