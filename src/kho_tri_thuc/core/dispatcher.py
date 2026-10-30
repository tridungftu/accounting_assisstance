"""Route tường minh, quyền trước dispatch, biên nhận và commit trước HTTP.

Core đăng ký Route bằng contract đã duyệt; ``nap_goi`` lấy thao_tac từ
GoiDaKiem G2-24 và đối chiếu phiên bản/hash G2-05 mỗi lần gọi. Không nhận
URL/host/cổng từ request. ``kenh_module(route, context)`` là seam transport
G2-19/21: không nhận cookie hoặc mã phiên Core, chỉ trả PhanHoi sau commit.
Phía module dùng ``thuc_hien_module`` với kết nối runtime và mã ủy nhiệm.
Không dùng biên nhận Core để thay biên nhận nghiệp vụ module.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field, replace
import hashlib
import hmac
import json
import re
import threading
import time
from uuid import UUID

from . import dang_ky, goi, mtq, phien, tiep_nhan, viec
from .http import LoiHTTP, PhanHoi
from .tai_lieu import LoiTaiLieu


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


def _schema_goi(package, ref):
    prefix = 'https://goi.invalid/' + package.manifest['ma'] + '/' + package.sha256_goi + '/'
    if ref.startswith(('schema/', 'contract/')):
        ref = prefix + ref
    elif not ref.startswith('urn:'):
        ref = 'urn:ktt:contract:' + ref
    return {'$ref': ref}


class KiemSchema:
    """G2-24 validator 2020-12 + format + registry offline, không fallback."""

    def __init__(self, schemas=None):
        try:
            self.validator, self.checker, registry, Resource = goi._bo_schema()
        except goi.LoiGoi:
            raise LoiHTTP(503) from None
        bundle = json.loads((goi.THU_MUC_CONTRACT / 'ky_thuat.json').read_text(encoding='utf-8'))
        if any(uri in bundle and bundle[uri] != schema for uri, schema in (schemas or {}).items()):
            raise ValueError('Không định nghĩa lại contract kỹ thuật')
        for uri, schema in {**bundle, **(schemas or {})}.items():
            self.validator.check_schema(schema)
            registry = registry.with_resource(uri, Resource.from_contents(schema))
        self.registry = registry

    def them_goi(self, package):
        """Nạp snapshot G2-24; URI local tách theo module/hash tránh đè gói khác."""
        if not isinstance(package, goi.GoiDaKiem):
            raise ValueError('Cần gói đã kiểm')
        _, _, _, Resource = goi._bo_schema()
        resources = {}
        for name, raw in package.cac_tep.items():
            if name.endswith('.json') and name.startswith(('schema/', 'contract/')):
                schema = goi.doc_json(raw, goi.GioiHan())
                if isinstance(schema, dict) and schema.get('$schema') == goi.DRAFT:
                    resources[_schema_goi(package, name)['$ref']] = schema
                    if schema.get('$id'):
                        resources[schema['$id']] = schema
        registry = self.registry
        for uri, schema in resources.items():
            existing = registry.get(uri)
            if existing is not None and existing.contents != schema:
                raise ValueError('Gói định nghĩa lại schema đã ghim')
            registry = registry.with_resource(uri, Resource.from_contents(schema))
        self.registry = registry

    def kiem(self, schema, value):
        try:
            _json(value)
            return self.validator(schema, registry=self.registry,
                                  format_checker=self.checker).is_valid(value)
        except Exception:
            return False


class ConTro:
    """Con trỏ HMAC, TTL 15 phút; khóa do Core cấp, giữ ổn định qua restart."""

    def __init__(self, khoa, *, dong_ho=time.time):
        if not isinstance(khoa, bytes) or len(khoa) < 32:
            raise ValueError('Cần khóa cursor ít nhất 32 byte')
        self._khoa, self._luc = khoa, dong_ho

    def __repr__(self):
        return 'ConTro(<an>)'

    def tao(self, ngu_canh, khoa_sau):
        raw = _json({'pham_vi': hashlib.sha256(_json(ngu_canh)).hexdigest(),
                     'sau': khoa_sau, 'het_han': int(self._luc()) + 900})
        result = base64.urlsafe_b64encode(hmac.digest(self._khoa, raw, 'sha256') + raw).decode().rstrip('=')
        if len(result) > 4096:
            raise LoiHTTP(502)
        return result

    def doc(self, token, ngu_canh):
        try:
            if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{44,4096}', token):
                raise ValueError()
            raw = base64.b64decode(token + '=' * (-len(token) % 4), altchars=b'-_', validate=True)
            if not hmac.compare_digest(raw[:32], hmac.digest(self._khoa, raw[32:], 'sha256')):
                raise ValueError()
            data = json.loads(raw[32:])
            if (data['pham_vi'] != hashlib.sha256(_json(ngu_canh)).hexdigest()
                    or type(data['het_han']) is not int
                    or not self._luc() < data['het_han'] <= self._luc() + 900
                    or not isinstance(data['sau'], list)):
                raise ValueError()
            return data['sau']
        except (ValueError, TypeError, KeyError, UnicodeError):
            raise LoiHTTP(400) from None


@dataclass(frozen=True)
class Trang:
    kich_thuoc: int
    khoa_sau: list | None


@dataclass(frozen=True)
class DuLieuTrang:
    """Handler lọc quyền hiện tại, query keyset ORDER BY khóa + UUID, LIMIT n+1.

    Mỗi khóa là list JSON theo đúng thứ tự công bố, phần cuối là UUID duy nhất.
    Không OFFSET, không cần COUNT hoặc tải toàn bộ dữ liệu.
    """

    danh_sach: list
    cac_khoa: list


@dataclass(frozen=True)
class ViecMoi:
    loai: str
    tham_chieu_id: UUID
    bang_tham_chieu: str
    phien_ban: int = 1
    tuy_chon: dict = field(default_factory=dict)


@dataclass(frozen=True, repr=False)
class NguCanh:
    request_id: str
    nguoi_dung_id: UUID | None
    phap_nhan_id: UUID | None
    module: str
    operation: str
    hanh_dong: str
    doi_tuong: dict
    body: object
    path: dict
    query: dict
    khoa: str | None
    trang: Trang | None = None


@dataclass(frozen=True, repr=False)
class Route:
    method: str
    duong_dan: str
    module: str
    operation: str
    hanh_dong: str
    dau_vao: object
    dau_ra: dict  # HTTP status -> JSON Schema
    doi_tuong: object  # (path, body) -> tham chiếu do máy chủ xác lập
    handler: object = None  # Core: (conn, NguCanh) -> PhanHoi / ViecMoi / DuLieuTrang
    quyen_doc: object = None  # (context, body thực) -> căn cứ đọc biên nhận
    chu_so_huu: str = 'core'
    phien_ban_contract: str = '1'
    truong_cas: tuple = ()
    query_schema: object = field(default_factory=lambda: {'type': 'object', 'additionalProperties': False})
    path_schema: object = None
    thu_tu: str | None = None
    viec_lau: bool = False
    ma_loi: dict = field(default_factory=dict)  # (status, ma) -> thông điệp đã duyệt
    phien_ban_goi: str | None = None
    ma_bam_goi: str | None = None
    phien: str = 'bat_buoc'  # bat_buoc / tien_phien / khong
    pham_vi: str = 'phap_nhan'  # phap_nhan / he_thong

    @property
    def ghi(self):
        return self.method in {'POST', 'PATCH', 'PUT', 'DELETE'}

    @property
    def chong_trung(self):
        return self.method in {'POST', 'PATCH', 'PUT'} and self.duong_dan != '/api/v1/phien'


class Registry:
    def __init__(self):
        self._routes = []

    def dang_ky(self, route):
        """Route ghi phạm vi hệ thống chưa được hỗ trợ, chờ G2-11c."""
        if (not isinstance(route, Route) or route.method not in {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD'}
                or not route.duong_dan.startswith('/api/v1/') or route.chu_so_huu not in {'core', 'module'}
                or any(c in route.duong_dan for c in ('?', '#', '%', '\\', '*'))
                or route.phien not in {'bat_buoc', 'tien_phien', 'khong'}
                or route.pham_vi not in {'phap_nhan', 'he_thong'}
                or not re.fullmatch(r'[a-z][a-z0-9_]{0,30}', route.module)):
            raise ValueError('Route không hợp lệ')
        if route.ghi and route.pham_vi == 'he_thong':
            raise LoiDangKyRoute('ROUTE_GHI_HE_THONG_CHUA_HO_TRO')
        if route.phien != 'bat_buoc' and (route.chu_so_huu != 'core' or route.pham_vi != 'he_thong'):
            raise ValueError('Route tiền phiên chỉ thuộc Core, phạm vi hệ thống')
        if route.chu_so_huu == 'module' and route.pham_vi != 'phap_nhan':
            raise ValueError('Module phải có ngữ cảnh pháp nhân')
        if route.chu_so_huu == 'module' and not route.duong_dan.startswith('/api/v1/module/' + route.module + '/'):
            raise ValueError('Sai namespace module')
        if route.method in {'GET', 'HEAD'} and route.viec_lau:
            raise ValueError('GET không tạo việc')
        segments, params, pattern = route.duong_dan.split('/'), [], []
        for segment in segments:
            if segment.startswith('{') and segment.endswith('}'):
                name = segment[1:-1]
                if not re.fullmatch('[a-z][a-z0-9_]*', name) or name in params:
                    raise ValueError('Path parameter không hợp lệ')
                params.append(name)
                pattern.append('([^/]+)')
            else:
                if '{' in segment or '}' in segment:
                    raise ValueError('Path parameter không hợp lệ')
                pattern.append(re.escape(segment))
        shape = re.sub(r'\{[^}]+\}', '{}', route.duong_dan)
        for old, _, _ in self._routes:
            if old.method == route.method and re.sub(r'\{[^}]+\}', '{}', old.duong_dan) == shape:
                raise ValueError('Route trùng')
        self._routes.append((route, re.compile('/'.join(pattern)), params))
        # Literal /mau/so-sanh phải thắng /mau/{id}.
        self._routes.sort(key=lambda r: len(r[2]))

    def nap_goi(self, package, tao_route):
        """Chỉ seam cài đặt gọi sau kiểm G2-24 và duyệt; không thực thi mã gói.

        tao_route là adapter Core sở hữu: ghép quyền/MTQ, schema, CAS và operation
        đã duyệt cho từng thao_tac. Không tự suy quyền MTQ từ chuỗi quyen manifest.
        """
        if not isinstance(package, goi.GoiDaKiem) or package.manifest['loai'] != 'module':
            raise ValueError('Cần gói module đã kiểm')
        # Không để một route của gói lỗi hoạt động một phần.
        staged = Registry()
        staged._routes = list(self._routes)
        for operation in package.manifest['thao_tac']:
            route = tao_route(operation)
            expected = '/api/v1/module/' + package.manifest['ma'] + operation['duong_dan']
            if (route.duong_dan != expected or route.method != operation['phuong_thuc']
                    or route.chu_so_huu != 'module' or route.module != package.manifest['ma']
                    or route.viec_lau != (operation['kieu'] == 'viec')
                    or route.chong_trung != operation['chong_trung']
                    or route.dau_vao != _schema_goi(package, operation['dau_vao'])
                    or any(schema != _schema_goi(package, operation['dau_ra']) for status, schema in route.dau_ra.items() if status < 400)
                    or (operation.get('kiem_row_version') and 'row_version' not in route.truong_cas)
                    or not set(route.ma_loi) <= {(e['http'], e['ma']) for e in package.manifest['ma_loi']}):
                raise ValueError('Route khác manifest')
            staged.dang_ky(replace(route, phien_ban_goi=package.manifest['phien_ban'],
                                  ma_bam_goi=package.sha256_goi))
        self._routes = staged._routes

    def tra(self, method, path):
        allowed = set()
        for route, pattern, params in self._routes:
            matched = pattern.fullmatch(path)
            if matched:
                allowed.add(route.method)
                if method == route.method:
                    return route, dict(zip(params, matched.groups()))
        if allowed:
            raise LoiHTTP(405, headers={'Allow': ', '.join(sorted(allowed))})
        raise LoiHTTP(404)


class LoiDangKyRoute(ValueError):
    """Lỗi cấu hình route có mã ổn định để bên đăng ký xử lý."""

    def __init__(self, ma):
        self.ma = ma
        super().__init__(ma)


def _kiem_phan_hoi(route, result, kiem, request_id=None):
    if not isinstance(result, PhanHoi) or type(result.status) is not int or result.status not in route.dau_ra:
        raise LoiHTTP(502)
    if not kiem.kiem(route.dau_ra[result.status], result.body):
        raise LoiHTTP(502)
    if result.status >= 400:
        ma = result.body.get('ma') if isinstance(result.body, dict) else None
        message = route.ma_loi.get((result.status, ma))
        if (message is None or not kiem.kiem({'$ref': 'urn:ktt:contract:loi_chuan.v1'}, result.body)):
            raise LoiHTTP(502)
        # Chỉ thông điệp đã duyệt ở registry, không tin văn bản module.
        result = replace(result, body={name: result.body[name] for name in
            ('ma', 'request_id', 'thu_lai_duoc')} | {'thong_diep': message})
    if request_id is not None and isinstance(result.body, dict) and 'request_id' in result.body:
        result = replace(result, body={**result.body, 'request_id': request_id})
    headers = {}  # Không chuyển Set-Cookie, Location nội bộ, CORS hay header module.
    if result.status in {429, 503}:
        value = result.headers.get('Retry-After', '2')
        if not isinstance(value, str) or not re.fullmatch('[1-9][0-9]{0,4}', value):
            raise LoiHTTP(502)
        headers['Retry-After'] = value
    if result.status == 202:
        try:
            id_ = str(UUID(result.body['viec_id']))
        except (TypeError, KeyError, ValueError):
            raise LoiHTTP(502) from None
        if not route.viec_lau:
            raise LoiHTTP(502)
        headers = {'Location': '/api/v1/viec/' + id_, 'Retry-After': '2'}
    elif route.viec_lau and result.status < 400:
        raise LoiHTTP(502)
    return replace(result, headers=headers)


def _kiem_trang(data, context):
    n = context.trang.kich_thuoc
    try:
        if (len(data.danh_sach) != len(data.cac_khoa) or len(data.danh_sach) > n + 1
                or any(not isinstance(k, list) or not k for k in data.cac_khoa)):
            raise ValueError()
        keys = data.cac_khoa
        for key in keys:
            UUID(key[-1])
        if any(a >= b for a, b in zip(keys, keys[1:])) or (
                keys and context.trang.khoa_sau is not None and keys[0] <= context.trang.khoa_sau):
            raise ValueError()
    except (TypeError, ValueError, AttributeError):
        raise LoiHTTP(502) from None
    return n, keys


def _trang_phan_hoi(data, context, route, cursor):
    n, keys = _kiem_trang(data, context)
    con = len(data.danh_sach) > n
    return PhanHoi(200, {'danh_sach': data.danh_sach[:n], 'con_tiep': con,
        'con_tro_tiep': cursor.tao(_pham_vi_trang(context, route), keys[n-1]) if con else None})


def _pham_vi_trang(context, route):
    return {'nguoi': str(context.nguoi_dung_id), 'pn': str(context.phap_nhan_id),
            'module': context.module, 'operation': context.operation, 'path': context.path,
            'loc': context.query, 'thu_tu': route.thu_tu}


def khoa_viec(context):
    # G2-14 unique (pháp nhân,module,key); tách operation và người tạo theo API.
    return 'http:' + hashlib.sha256(_json([str(context.nguoi_dung_id), context.operation, context.khoa])).hexdigest()


def _kiem_dau_vao(route, body, path, query, kiem):
    """Core và module cùng kiểm, trước transaction/handler/biên nhận."""
    if (not kiem.kiem(route.dau_vao, body)
            or (route.path_schema is not None and not kiem.kiem(route.path_schema, path))
            or not kiem.kiem(route.query_schema, query)):
        raise LoiHTTP(422)
    for name in route.truong_cas:
        value = body.get(name) if isinstance(body, dict) else None
        if name == 'row_version':
            try:
                viec._cas(value)
            except ValueError:
                raise LoiHTTP(422) from None
        elif value is None:
            raise LoiHTTP(422)


def _thuc_hien(conn, route, context, ma, *, kiem, cursor, core):
    """Được gọi trong transaction đang mở; mọi exception phải rollback toàn tx."""
    tiep_nhan._tx(conn)
    ctx = dict(ma=ma, module=context.module, phap_nhan_id=context.phap_nhan_id,
               hanh_dong=context.hanh_dong)
    ts = dict(operation=context.operation, khoa=context.khoa,
              noi_dung={'body': context.body, 'path': context.path, 'query': context.query},
              doi_tuong=context.doi_tuong, phien_ban_contract=route.phien_ban_contract, **ctx)
    if route.chong_trung:
        cu = (tiep_nhan.tra_core if core else tiep_nhan.tra_thao_tac)(conn, **ts)
        if cu is not None:
            value = cu['ket_qua']
            return _kiem_phan_hoi(route, PhanHoi(value['status'], value['body']), kiem, context.request_id)
    # CAS nghiệp vụ chỉ ở handler và CSDL; phát lại không kiểm CAS lần nữa.
    result = route.handler(conn, context)
    if isinstance(result, ViecMoi):
        if not route.viec_lau or not route.chong_trung:
            raise LoiHTTP(502)
        id_ = viec.tao_viec(conn, result.loai, result.phien_ban, khoa_viec(context),
            result.tham_chieu_id, bang_tham_chieu=result.bang_tham_chieu,
            phien_ban_contract=route.phien_ban_contract, **result.tuy_chon, **ctx)
        result = PhanHoi(202, {'viec_id': str(id_), 'trang_thai': 'queued',
                             'request_id': context.request_id})
    elif route.viec_lau and not (isinstance(result, PhanHoi)
                                and type(result.status) is int and result.status >= 400):
        raise LoiHTTP(502)  # Không nhận 202 tự khai mà chưa tạo việc trên tx.
    elif isinstance(result, DuLieuTrang):
        if context.trang is None or route.ghi:
            raise LoiHTTP(502)
        if not core:
            # Payload nội bộ của seam transport; Core ký cursor rồi kiểm schema
            # public. Không cấp khóa HMAC Core cho tiến trình module.
            _kiem_trang(result, context)
            tiep_nhan._tx(conn)
            return PhanHoi(200, result)
        if cursor is None:
            raise LoiHTTP(503)
        result = _trang_phan_hoi(result, context, route, cursor)
    result = _kiem_phan_hoi(route, result, kiem, context.request_id)
    tiep_nhan._tx(conn)  # Handler không được tự commit.
    if result.status >= 400:
        raise LoiHTTP(result.status, ma=result.body['ma'], thong_diep=result.body['thong_diep'], headers=result.headers)
    if route.chong_trung:
        if not callable(route.quyen_doc):
            raise LoiHTTP(500)
        ghi = tiep_nhan.ghi_core if core else tiep_nhan.ghi_thao_tac
        extra = {'trang_thai': 'DANG_XU_LY' if result.status == 202 else 'HOAN_TAT'} if core else {}
        ghi(conn, ket_qua={'status': result.status, 'body': result.body},
            quyen_doc=route.quyen_doc(context, result.body), **extra, **ts)
    return result


def thuc_hien_module(conn, route, context, ma_uy_nhiem, *, kiem, cursor=None):
    """Seam SDK: LOGIN module thật, connection IDLE; trả SAU commit gốc.

    Module vẫn kiểm quyền nghiệp vụ trong handler; G2-11 kiểm quyền khi tra/
    ghi biên nhận. Không dùng connection/transaction của Core để ghi module.
    """
    if route.chu_so_huu != 'module' or conn.info.transaction_status != 0:
        raise LoiHTTP(500)
    _kiem_dau_vao(route, context.body, context.path, context.query, kiem)
    with conn.transaction():
        if (context.module != route.module or context.operation != route.operation
                or context.hanh_dong != route.hanh_dong):
            raise LoiHTTP(403)
        identity = phien.xac_minh_phien(conn, ma=ma_uy_nhiem, module=route.module,
            phap_nhan_id=context.phap_nhan_id, hanh_dong=route.hanh_dong)
        if identity is None or identity.nguoi_dung_id != context.nguoi_dung_id:
            raise LoiHTTP(404)
        result = _thuc_hien(conn, route, context, ma_uy_nhiem, kiem=kiem, cursor=cursor, core=False)
    if conn.info.transaction_status != 0:
        raise LoiHTTP(500)
    return replace(result, da_commit=True)


class Dispatcher:
    def __init__(self, registry, *, ket_noi, kiem=None, cursor=None, kenh_module=None,
                 quyen_he_thong=None):
        self.registry, self.ket_noi = registry, ket_noi
        self.kiem = kiem if kiem is not None else KiemSchema()
        self.cursor, self.kenh_module = cursor, kenh_module
        # (conn, NguCanh) -> True chỉ khi tài khoản backend có quyền Admin
        # cho operation/đối tượng. Không dùng cửa G2-03/MTQ yêu cầu UUID pháp nhân.
        self.quyen_he_thong = quyen_he_thong
        self._khoa = threading.Lock()
        self._dang_chay = set()

    def _context(self, request, route, path):
        if route.phien == 'bat_buoc' and (request.phien is None or request.phien.tien_phien
                                        or request.phien.nguoi_dung_id is None):
            raise LoiHTTP(401)
        if route.phien == 'tien_phien' and request.phien is None:
            raise LoiHTTP(401)
        pn = None
        if route.pham_vi == 'phap_nhan':
            pn = request.headers.get('x-phap-nhan-id')
            try:
                if not pn or not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', pn):
                    raise ValueError()
                pn = UUID(pn)
            except ValueError:
                raise LoiHTTP(400) from None
        key = request.headers.get('idempotency-key')
        if route.chong_trung:
            try:
                tiep_nhan._khoa(key)
            except ValueError:
                raise LoiHTTP(400) from None
        query = dict(request.query)
        token, size = None, None
        if route.thu_tu is not None:
            token, text = query.pop('con_tro', None), query.pop('kich_thuoc_trang', '25')
            if not re.fullmatch('[1-9][0-9]{0,2}', text) or int(text) > 100:
                raise LoiHTTP(400)
            size = int(text)
        _kiem_dau_vao(route, request.body, path, query, self.kiem)
        context = NguCanh(request.request_id, request.phien.nguoi_dung_id if request.phien else None, pn, route.module,
            route.operation, route.hanh_dong, route.doi_tuong(path, request.body), request.body,
            path, query, key)
        if size is not None:
            if self.cursor is None:
                raise LoiHTTP(503)
            sau = self.cursor.doc(token, _pham_vi_trang(context, route)) if token is not None else None
            context = replace(context, trang=Trang(size, sau))
        return context

    def _dispatch(self, request, route, context):
        with self.ket_noi() as conn:
            if conn.info.transaction_status != 0:
                raise LoiHTTP(500)  # Không cho 202 từ savepoint chưa commit gốc.
            with conn.transaction():
                if route.pham_vi == 'he_thong':
                    if route.phien == 'bat_buoc' and (self.quyen_he_thong is None
                            or self.quyen_he_thong(conn, context) is not True):
                        raise LoiHTTP(404)
                    result = _thuc_hien(conn, route, context, None,
                                       kiem=self.kiem, cursor=self.cursor, core=True)
                else:
                    result = self._dispatch_phap_nhan(conn, request, route, context)
            if conn.info.transaction_status != 0:
                raise LoiHTTP(500)
        if route.chu_so_huu == 'module':
            return self._dispatch_module(route, context)
        return result

    def _dispatch_phap_nhan(self, conn, request, route, context):
        ma = request.phien.lay_ma(route.module, context.phap_nhan_id)
        if not isinstance(ma, phien.MaBiMat):
            raise LoiHTTP(404)
        ctx = dict(ma=ma, module=route.module, phap_nhan_id=context.phap_nhan_id,
                   hanh_dong=route.hanh_dong)
        identity = phien.xac_minh_phien(conn, **ctx)
        if identity is None or identity.nguoi_dung_id != context.nguoi_dung_id:
            raise LoiHTTP(404)
        decision = mtq.quyet_dinh_phien(conn, doi_tuong=context.doi_tuong,
            phien_ban_contract=route.phien_ban_contract, **ctx)
        if decision.get('ket_luan') != 'DAT' or decision.get('cho_phep') is not True:
            raise LoiHTTP(404 if decision.get('ket_luan') != 'CHO' else 503)
        if route.chu_so_huu == 'module':
            versions = dang_ky.doc_dang_ky(conn, loai='phien_ban_module', ma=route.module)
            if not any(v['so_phien_ban'] == route.phien_ban_goi
                       and v['ma_bam_goi'] == route.ma_bam_goi
                       and v['trang_thai'] == 'da_cai' for v in versions):
                raise LoiHTTP(503)
        else:
            return _thuc_hien(conn, route, context, ma, kiem=self.kiem, cursor=self.cursor, core=True)

    def _dispatch_module(self, route, context):
        if self.kenh_module is None:
            raise LoiHTTP(503)
        try:
            result = self.kenh_module(route, context)
        except TimeoutError:
            raise LoiHTTP(504) from None
        if route.thu_tu is not None and isinstance(result, PhanHoi) and result.status < 400:
            if result.status != 200 or not isinstance(result.body, DuLieuTrang):
                raise LoiHTTP(502)
            result = replace(_trang_phan_hoi(result.body, context, route, self.cursor),
                             da_commit=result.da_commit)
        result = _kiem_phan_hoi(route, result, self.kiem, context.request_id)
        if result.status < 400 and result.da_commit is not True:
            raise LoiHTTP(502)
        if result.status >= 400:
            result = replace(result, body={**result.body, 'request_id': context.request_id})
        return result

    def dispatch(self, request):
        """Chặn cả route ghi hệ thống lọt đăng ký; chờ G2-11c."""
        route, path = self.registry.tra(request.method, request.path)
        if route.ghi and route.pham_vi == 'he_thong':
            raise LoiHTTP(503, headers={'Retry-After': '2'})
        context = self._context(request, route, path)
        lock_key = (context.nguoi_dung_id, context.phap_nhan_id, route.module, route.operation, context.khoa)
        held = False
        try:
            if route.chong_trung:
                with self._khoa:
                    if lock_key in self._dang_chay:
                        raise LoiHTTP(409, ma='YEU_CAU_DANG_XU_LY', headers={'Retry-After': '2'})
                    self._dang_chay.add(lock_key)
                    held = True
            return self._dispatch(request, route, context)
        except (tiep_nhan.LoiTiepNhan, viec.LoiViec, LoiTaiLieu) as exc:
            status = (409 if exc.ma == 'TAI_LIEU_REVISION' else
                      404 if exc.ma == 'TAI_LIEU_KHONG_THAY' else
                      403 if exc.ma in {'TAI_LIEU_PHIEN', 'TAI_LIEU_MTQ', 'TAI_LIEU_CONG_TAC'} else
                      getattr(exc, 'http_status', 500))
            # Unknown wrappers fail closed as 500, no driver text.
            if exc.ma.endswith('THAT_BAI'):
                status = 500
            if status == 409:
                if exc.ma in {'YEU_CAU_DANG_XU_LY', 'BIEN_NHAN_CORE_HET_HAN'}:
                    raise LoiHTTP(409, ma=exc.ma,
                        headers={'Retry-After': '2'} if exc.ma == 'YEU_CAU_DANG_XU_LY' else {}) from None
                raise LoiHTTP(409, ma=('KHOA_CHONG_TRUNG_KHAC_NOI_DUNG'
                    if exc.ma in {'KHOA_CHONG_TRUNG_KHAC_NOI_DUNG', 'VIEC_KHOA_KHAC_NOI_DUNG'}
                    else 'XUNG_DOT_PHIEN_BAN')) from None
            raise LoiHTTP(status if status in {400, 403, 404} else 500) from None
        finally:
            if held:
                with self._khoa:
                    self._dang_chay.remove(lock_key)
