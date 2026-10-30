"""Ngữ cảnh request đã kiểm; một NhanRequest được bootstrap cho mỗi instance.

Wire nội bộ: base64url(JSON UTF-8).base64url(chữ ký). Core ký chính bytes
``b'ktt.context.v1\\0' + JSON``; SDK chỉ nhận bộ kiểm chứng khóa công khai
``verify(signature, message)`` (thành công trả None, sai thì raise).
Không chọn thuật toán từ thẻ, không nhận khóa ký/credential trong context.
Thẻ phải được bọc MaBiMat ngay tại boundary; không log bytes đầu vào.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import math
import re
import threading
import time
import traceback
from uuid import UUID

from ..core.phien import MaBiMat


class LoiNguCanh(RuntimeError):
    http_status = 401

    def __init__(self):
        super().__init__('Ngữ cảnh request không hợp lệ')


_DA_KIEM = object()
_KHOA_NONCE = threading.Lock()
_NONCE = {}
_MIEN_KY = b'ktt.context.v1\0'


def _xoa_loi(exc):
    """Không giữ frame driver/parser có raw secret qua exception chaining."""
    da_xoa = set()
    cho = [exc]
    while cho:
        exc = cho.pop()
        if exc is None or id(exc) in da_xoa:
            continue
        da_xoa.add(id(exc))
        traceback.clear_frames(exc.__traceback__)
        cho.extend((exc.__context__, exc.__cause__))
        cho.extend(getattr(exc, 'exceptions', ()))
        # contextlib có thể gắn lại chính exception được throw vào generator.
        # Xóa cả thông điệp/metadata gốc trước khi trả quyền cho contextlib.
        exc.args = ('Lỗi nội bộ đã ẩn',)
        exc.__dict__.clear()
        exc.__traceback__ = exc.__context__ = exc.__cause__ = None


@dataclass(frozen=True, slots=True, repr=False)
class NguCanh:
    nguoi_dung_id: UUID
    module: str
    instance_id: UUID
    phap_nhan_id: UUID
    module_nguon: str
    operation: str
    hanh_dong: str
    request_id: UUID
    khoa: str | None
    hieu_luc_den: float
    ma: MaBiMat = field(repr=False)
    _da_kiem: object = field(default=None, init=False, repr=False, compare=False)

    def __repr__(self):
        return 'NguCanh(<an>)'

    def __reduce__(self):
        raise TypeError('Không serialize NguCanh')


def bam_request(method: str, duong_dan: str, body: bytes) -> str:
    """Hash bytes thực nhận; path gồm cả query, không chuẩn hóa lại JSON/URL."""
    if (not isinstance(method, str) or not re.fullmatch('[A-Z]+', method)
            or not isinstance(duong_dan, str) or not duong_dan.startswith('/')
            or type(body) is not bytes):
        raise LoiNguCanh()
    bam = hashlib.sha256(b'ktt.request.v1\0')
    for phan in (method.encode('ascii'), duong_dan.encode('utf-8'), body):
        bam.update(len(phan).to_bytes(8, 'big'))
        bam.update(phan)
    return bam.hexdigest()


def _b64(text):
    if not re.fullmatch('[A-Za-z0-9_-]+', text):
        raise ValueError()
    raw = base64.b64decode(text + '=' * (-len(text) % 4), altchars=b'-_', validate=True)
    if base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii') != text:
        raise ValueError()
    return raw


def _json_cac_cap(cac_cap):
    ket_qua = {}
    for khoa, gia_tri in cac_cap:
        if khoa in ket_qua:
            raise ValueError()
        ket_qua[khoa] = gia_tri
    return ket_qua


class NhanRequest:
    """Bộ kiểm chứng từ bootstrap tin cậy; nonce chung trong một tiến trình.

    Bất biến: Core cấp nonce_khoi_dong ngẫu nhiên (ít nhất 256 bit) riêng cho
    từng tiến trình nhận, đổi sau mọi restart, kể cả khi giữ instance_id.
    Core ký nonce này trong thẻ và chỉ chuyển thẻ tới đúng tiến trình đó.
    Các bộ đọc trong cùng tiến trình dùng chung nonce bootstrap và sổ RAM;
    các tiến trình khác không được dùng chung nonce bootstrap. Vì vậy thẻ
    cũ bị từ chối dù sổ nonce RAM đã mất hoặc instance có nhiều tiến trình.

    Caller truyền operation/hành động lấy từ registry, không lấy từ client.
    Khóa chống trùng là header thực nhận (None cho request không có header).
    Không lưu lại thẻ; mã CSDL tiếp tục được Core kiểm trên từng transaction.
    """

    __slots__ = ('issuer', 'module', 'instance_id', '_nonce_khoi_dong', '_kiem_chu_ky', '_dong_ho')

    def __init__(self, *, issuer, module, instance_id, nonce_khoi_dong,
                 kiem_chu_ky, dong_ho=time.time):
        if (not isinstance(issuer, str) or not issuer
                or not re.fullmatch('[a-z][a-z0-9_]{0,30}', module)
                or not callable(kiem_chu_ky)
                or not isinstance(nonce_khoi_dong, str)
                or not re.fullmatch('[A-Za-z0-9_-]{43,128}', nonce_khoi_dong)):
            raise LoiNguCanh()
        self.issuer, self.module = issuer, module
        self.instance_id = UUID(str(instance_id))
        self._nonce_khoi_dong = nonce_khoi_dong
        self._kiem_chu_ky, self._dong_ho = kiem_chu_ky, dong_ho

    def __repr__(self):
        return 'NhanRequest(<an>)'

    def __reduce__(self):
        raise TypeError('Không serialize bộ kiểm ngữ cảnh')

    def nhan_request(self, the: MaBiMat, *, method, duong_dan, body,
                     operation, hanh_dong, khoa=None) -> NguCanh:
        raw = payload = chu_ky = du_lieu = cac_phan = None
        try:
            if not isinstance(the, MaBiMat):
                raise ValueError()
            raw = the.lay_de_truyen()
            if not isinstance(raw, str) or len(raw) > 16384:
                raise ValueError()
            cac_phan = raw.split('.')
            if len(cac_phan) != 2:
                raise ValueError()
            payload, chu_ky = map(_b64, cac_phan)
            if self._kiem_chu_ky(chu_ky, _MIEN_KY + payload) is not None:
                raise ValueError()
            du_lieu = json.loads(payload, object_pairs_hook=_json_cac_cap)
            bat_buoc = {'issuer', 'module', 'instance_id', 'nguoi_dung_id', 'ma_uy_nhiem',
                        'phap_nhan_id', 'module_nguon', 'operation', 'hanh_dong',
                        'request_id', 'khoa', 'phat_luc', 'het_han', 'nonce', 'hash_request',
                        'nonce_khoi_dong'}
            if not isinstance(du_lieu, dict) or set(du_lieu) != bat_buoc:
                raise ValueError()
            now = self._dong_ho()
            tu, den = du_lieu['phat_luc'], du_lieu['het_han']
            if (any(type(t) not in (int, float) or not math.isfinite(t) for t in (tu, den, now))
                    or not tu <= now < den or not 0 < den - tu <= 30):
                raise ValueError()
            if (du_lieu['issuer'] != self.issuer or du_lieu['module'] != self.module
                    or UUID(du_lieu['instance_id']) != self.instance_id
                    or not isinstance(du_lieu['nonce_khoi_dong'], str)
                    or not hmac.compare_digest(du_lieu['nonce_khoi_dong'], self._nonce_khoi_dong)
                    or du_lieu['operation'] != operation or du_lieu['hanh_dong'] != hanh_dong
                    or du_lieu['khoa'] != khoa):
                raise ValueError()
            if (not isinstance(operation, str) or not operation or len(operation) > 200
                    or not isinstance(hanh_dong, str)
                    or not re.fullmatch(self.module.upper() + r':[A-Z0-9_]+:[A-Z_]+', hanh_dong)
                    or not isinstance(du_lieu['module_nguon'], str)
                    or not re.fullmatch('[a-z][a-z0-9_]{0,30}', du_lieu['module_nguon'])
                    or (khoa is not None and (not isinstance(khoa, str) or not 1 <= len(khoa) <= 200))
                    or (method not in ('GET', 'HEAD', 'OPTIONS') and not khoa)):
                raise ValueError()
            if (not isinstance(du_lieu['hash_request'], str)
                    or not hmac.compare_digest(du_lieu['hash_request'], bam_request(method, duong_dan, body))
                    or not isinstance(du_lieu['ma_uy_nhiem'], str)
                    or not re.fullmatch('[A-Za-z0-9_-]{43,128}', du_lieu['ma_uy_nhiem'])
                    or not isinstance(du_lieu['nonce'], str)
                    or not re.fullmatch('[A-Za-z0-9_-]{16,128}', du_lieu['nonce'])):
                raise ValueError()
            ctx = NguCanh(UUID(du_lieu['nguoi_dung_id']), self.module, self.instance_id,
                          UUID(du_lieu['phap_nhan_id']), du_lieu['module_nguon'], operation,
                          hanh_dong, UUID(du_lieu['request_id']), khoa, den,
                          MaBiMat(du_lieu['ma_uy_nhiem']))
            nonce = (self.issuer, self.module, self.instance_id, self._nonce_khoi_dong,
                     hashlib.sha256(du_lieu['nonce'].encode('ascii')).digest())
            with _KHOA_NONCE:
                for cu in [k for k, het_han in _NONCE.items() if het_han <= now]:
                    del _NONCE[cu]
                if nonce in _NONCE or len(_NONCE) >= 100000:
                    raise ValueError()
                _NONCE[nonce] = den
            object.__setattr__(ctx, '_da_kiem', _DA_KIEM)
            return ctx
        except Exception as exc:
            _xoa_loi(exc)
        finally:
            # Không để JSON chứa mã hoặc chữ ký trong locals của lỗi 401.
            raw = payload = chu_ky = du_lieu = cac_phan = None
            the = None
        raise LoiNguCanh()
