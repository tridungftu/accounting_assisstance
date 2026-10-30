"""G2-24: đọc snapshot gói, không import hoặc thực thi bất kỳ mã gói nào.

Chỉ kiểm tĩnh/offline; DAT ở đây không thay kiểm quyền, duyệt contract,
capability thực hoặc kích hoạt G2-25/26. jsonschema là dependency bắt buộc
khi kiểm schema; thiếu thì từ chối, không dùng validator giản lược.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
from types import MappingProxyType


DRAFT = 'https://json-schema.org/draft/2020-12/schema'
THU_MUC_CONTRACT = Path(__file__).with_name('contract')


class LoiGoi(ValueError):
    """Lỗi kiểm gói, thông điệp không phản chiếu dữ liệu gói."""


@dataclass(frozen=True)
class GioiHan:
    """Giới hạn vận hành của bộ đọc, caller Core có thể đặt thấp hơn."""

    moi_tep: int = 32 * 1024 * 1024
    ca_goi: int = 128 * 1024 * 1024
    json: int = 1024 * 1024
    so_muc: int = 4096
    do_sau: int = 32

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in vars(self).values()):
            raise LoiGoi('Giới hạn đọc gói phải là số nguyên dương.')


@dataclass(frozen=True)
class GoiDaKiem:
    manifest: dict
    cac_tep: object  # mapping bất biến: đường dẫn POSIX -> bytes đã kiểm
    cac_thu_muc: tuple[str, ...]
    sha256_tung_tep: object
    sha256_goi: str


def _cap_json(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise LoiGoi('JSON có khóa trùng.')
        obj[key] = value
    return obj


def _so_json(value):
    number = float(value)
    if not math.isfinite(number):
        raise LoiGoi('JSON có số không hữu hạn.')
    return number


def doc_json(raw, gioi_han):
    if len(raw) > gioi_han.json:
        raise LoiGoi('JSON vượt giới hạn kích thước.')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=_cap_json,
                          parse_float=_so_json, parse_constant=_so_json)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise LoiGoi('JSON không hợp lệ, khóa trùng hoặc số không hữu hạn.') from exc


def kiem_ten_tep(ten):
    """Cùng quy tắc trên Windows/POSIX; không cho ADS, UNC, device, alias."""
    if not isinstance(ten, str) or not ten or '\\' in ten or ':' in ten:
        raise LoiGoi('Đường dẫn tệp không an toàn.')
    parts = ten.split('/')
    for part in parts:
        if (part in ('', '.', '..') or part.endswith((' ', '.'))
                or re.search(r'[\x00-\x1f<>"|?*]', part)
                or re.fullmatch(r'(?i:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part)):
            raise LoiGoi('Đường dẫn tệp không an toàn.')
    return PurePosixPath(ten)


def kiem_duong_dan(duong_dan):
    """Kiểm từng tổ tiên bằng lstat, không resolve trước rồi mất dấu junction."""
    path = Path(os.path.abspath(duong_dan))
    cam = {'plhn-that', 'web-that', 'du-lieu-ke-toan', '.env',
           'cau_hinh.that.toml'}
    if any(p.casefold() in cam or p.casefold().endswith('.local.json') for p in path.parts):
        raise LoiGoi('Từ chối đường dẫn dữ liệu thật hoặc cấu hình riêng.')
    for item in (*reversed(path.parents), path):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(info.st_mode)
                or getattr(info, 'st_file_attributes', 0) & 0x400):
            raise LoiGoi('Không nhận symlink hoặc junction trong đường dẫn gói.')
    return path


def _kiem_handle(fd, path):
    """Windows: kiểm đích handle trước đọc/ghi, kể cả đổi junction khi mở."""
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise LoiGoi('Chỉ nhận tệp thường, không nhận hardlink.')
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        import msvcrt

        fn = ctypes.WinDLL('kernel32', use_last_error=True).GetFinalPathNameByHandleW
        fn.argtypes = (wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD)
        fn.restype = wintypes.DWORD
        buf = ctypes.create_unicode_buffer(32768)
        count = fn(msvcrt.get_osfhandle(fd), buf, len(buf), 0)
        if not count or count >= len(buf):
            raise LoiGoi('Không xác minh được đích handle tệp.')
        final = buf.value
        if final.startswith('\\\\?\\UNC\\'):
            final = '\\\\' + final[8:]
        elif final.startswith('\\\\?\\'):
            final = final[4:]
        if os.path.normcase(final) != os.path.normcase(str(path)):
            raise LoiGoi('Đích handle tệp đã đổi hoặc thoát gói.')
    elif Path('/proc/self/fd').is_dir():
        if os.readlink(f'/proc/self/fd/{fd}') != str(path):
            raise LoiGoi('Đích handle tệp đã đổi hoặc thoát gói.')
    return info


def _snapshot(thu_muc, gioi_han):
    root = kiem_duong_dan(thu_muc)
    if not root.is_dir():
        raise LoiGoi('Gói phải là thư mục tồn tại.')
    files, dirs, seen_names, tong, so_muc = {}, set(), set(), 0, 0
    pending = [(root, 0)]
    while pending:
        folder, depth = pending.pop()
        kiem_duong_dan(folder)
        if depth > gioi_han.do_sau:
            raise LoiGoi('Gói vượt giới hạn độ sâu thư mục.')
        with os.scandir(folder) as entries:
            for entry in entries:
                so_muc += 1
                if so_muc > gioi_han.so_muc:
                    raise LoiGoi('Gói vượt giới hạn số tệp/thư mục.')
                path = kiem_duong_dan(entry.path)
                name = path.relative_to(root).as_posix()
                kiem_ten_tep(name)
                if name.casefold() in seen_names:
                    raise LoiGoi('Tên tệp/thư mục trùng sau chuẩn hóa Windows.')
                seen_names.add(name.casefold())
                info = path.lstat()
                if stat.S_ISDIR(info.st_mode):
                    dirs.add(name)
                    pending.append((path, depth + 1))
                    continue
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise LoiGoi('Gói có tệp đặc biệt hoặc hardlink.')
                if info.st_size > gioi_han.moi_tep or tong + info.st_size > gioi_han.ca_goi:
                    raise LoiGoi('Gói vượt giới hạn kích thước.')
                fd = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0)
                             | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
                with os.fdopen(fd, 'rb') as stream:
                    before = _kiem_handle(stream.fileno(), path)
                    budget = min(gioi_han.moi_tep, gioi_han.ca_goi - tong)
                    raw = stream.read(budget + 1)
                    after = os.fstat(stream.fileno())
                kiem_duong_dan(path)
                if (before.st_size != len(raw) or before.st_mtime_ns != after.st_mtime_ns
                        or len(raw) > budget):
                    raise LoiGoi('Tệp đổi trong lúc đọc hoặc vượt giới hạn kích thước.')
                tong += len(raw)
                files[name] = raw
    return files, dirs


def bam_goi(files):
    """SHA256 bảng kê chuẩn: JSON UTF-8 [tên, số byte, SHA256], sắp theo tên.

    Bảng kê chỉ ở RAM/báo cáo; không tạo tệp hash hoặc vòng tự băm.
    """
    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(files.items())}
    raw = json.dumps([[n, len(files[n]), h] for n, h in hashes.items()],
                     ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return hashes, hashlib.sha256(raw).hexdigest()


def _kiem_kiem_ke(files, manifest, gioi_han):
    """Kiểm kê {phien_ban, tep: [{duong_dan, bytes, sha256}]}.

    Liệt kê đủ mọi tệp, kể cả module.json; chỉ trừ chính tệp kiểm kê để
    tránh vòng tự băm. Đối chiếu snapshot, không đọc lại đường dẫn nguồn.
    """
    name = manifest['goi']['tep_kiem_ke']
    inventory = doc_json(files[name], gioi_han)
    if (not isinstance(inventory, dict)
            or inventory.get('phien_ban') != manifest['phien_ban']
            or not isinstance(inventory.get('tep'), list)):
        raise LoiGoi('Kiểm kê gói thiếu phiên bản hoặc danh sách tệp hợp lệ.')
    seen = set()
    for item in inventory['tep']:
        if not isinstance(item, dict):
            raise LoiGoi('Mục kiểm kê gói không hợp lệ.')
        path = item.get('duong_dan')
        kiem_ten_tep(path)
        size, digest = item.get('bytes'), item.get('sha256')
        if (path == name or path in seen or path not in files
                or type(size) is not int or size < 0
                or not isinstance(digest, str)
                or not re.fullmatch(r'[0-9a-f]{64}', digest)):
            raise LoiGoi('Kiểm kê gói có mục trùng, thiếu, thừa hoặc sai định dạng.')
        seen.add(path)
        if size != len(files[path]) or digest != hashlib.sha256(files[path]).hexdigest():
            raise LoiGoi('Bytes hoặc SHA256 thực tế không khớp kiểm kê gói.')
    if seen != set(files) - {name}:
        raise LoiGoi('Kiểm kê gói không liệt kê đủ các tệp thực tế.')


def _kiem_mo_ta_contract(description, entry):
    """Metadata CD-032 phải đầy đủ và khớp mục contract đã ghim."""
    if not isinstance(description, dict):
        raise LoiGoi('Mô tả contract phải là object JSON.')
    for key in ('ma', 'phien_ban', 'module_so_huu', 'schema', 'vi_du'):
        if description.get(key) != entry[key]:
            raise LoiGoi('Mô tả contract thiếu hoặc không khớp metadata/đường dẫn manifest.')
    purpose = description.get('muc_dich')
    readers = description.get('module_duoc_doc')
    if (not isinstance(purpose, str) or not purpose.strip()
            or not isinstance(readers, list)
            or any(not isinstance(m, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', m)
                   for m in readers)
            or len(set(readers)) != len(readers)):
        raise LoiGoi('Mô tả contract thiếu mục đích hoặc danh sách module được đọc hợp lệ.')
    fields = description.get('truong')
    if not isinstance(fields, list) or not fields:
        raise LoiGoi('Mô tả contract thiếu bảng trường.')
    seen = set()
    for field in fields:
        if not isinstance(field, dict):
            raise LoiGoi('Mô tả trường contract không hợp lệ.')
        name = field.get('ten')
        if (not isinstance(name, str)
                or not re.fullmatch(r'[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*', name)
                or name in seen or type(field.get('bat_buoc')) is not bool
                or any(not isinstance(field.get(k), str) or not field[k].strip()
                       for k in ('nghia', 'don_vi', 'nguon'))):
            raise LoiGoi('Trường contract thiếu tên/nghĩa/bắt buộc/đơn vị/nguồn hợp lệ.')
        seen.add(name)


def _semver(value):
    match = re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)'
                         r'(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?'
                         r'(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?', value)
    if not match:
        raise LoiGoi('Phiên bản SemVer không hợp lệ.')
    major, minor, patch, pre, _ = match.groups()
    preparts = pre.split('.') if pre else []
    if any(p.isdigit() and len(p) > 1 and p.startswith('0') for p in preparts):
        raise LoiGoi('Phiên bản SemVer không hợp lệ.')
    # Release đứng sau mọi prerelease; chuỗi số so số, sau đó chuỗi chữ.
    return (int(major), int(minor), int(patch), 1 if pre is None else 0,
            tuple((0, int(p)) if p.isdigit() else (1, p) for p in preparts))


def kiem_phien_ban(version, khoang):
    """Range giao: các comparator phân cách bằng khoảng trắng, giao AND.

    Không đoán nghĩa cú pháp khác (caret/tilde/OR/wildcard): từ chối.
    """
    current = _semver(version)
    tokens = khoang.split()
    if not tokens:
        raise LoiGoi('Khoảng tương thích phiên bản rỗng.')
    for token in tokens:
        match = re.fullmatch(r'(>=|<=|>|<|=)?(.+)', token)
        op, target = match.groups()
        wanted = _semver(target)
        if not {'>=': current >= wanted, '<=': current <= wanted,
                '>': current > wanted, '<': current < wanted,
                '=': current == wanted, None: current == wanted}[op]:
            raise LoiGoi('Phiên bản Core/SDK hoặc module phụ thuộc không tương thích.')


def _bo_schema():
    try:
        from jsonschema import Draft202012Validator, FormatChecker
        from referencing import Registry, Resource
        from referencing.exceptions import NoSuchResource
    except ImportError as exc:
        raise LoiGoi('Thiếu jsonschema/referencing; chưa thể kiểm gói.') from exc

    checker = FormatChecker()

    @checker.checks('date', raises=ValueError)
    def check_date(value):
        if isinstance(value, str):
            if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
                raise ValueError('date')
            date.fromisoformat(value)
        return True

    @checker.checks('date-time', raises=ValueError)
    def check_time(value):
        if isinstance(value, str):
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}'
                                r'(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})', value):
                raise ValueError('date-time')
            datetime.fromisoformat(value.upper().replace('Z', '+00:00'))
        return True

    def offline(uri):
        raise NoSuchResource(ref=uri)

    return Draft202012Validator, checker, Registry(retrieve=offline), Resource


def doc_goi(thu_muc, *, phien_ban_core, phien_ban_sdk_python='1.0.0',
            phien_ban_sdk_js='1.0.0', module_da_co=None, gioi_han=None):
    """Đọc/kiểm offline, trả bytes và hash. Không cần/kết nối CSDL.

    module_da_co là snapshot mã -> SemVer do Core cấp; không nhận từ gói.
    Chưa có snapshot thì gói có phụ thuộc sẽ bị từ chối.
    """
    limits = gioi_han or GioiHan()
    try:
        files, dirs = _snapshot(thu_muc, limits)
        if 'module.json' not in files or 'contract' not in dirs:
            raise LoiGoi('Gói thiếu module.json hoặc thư mục contract/.')
        manifest = doc_json(files['module.json'], limits)
        Validator, checker, registry, Resource = _bo_schema()
        schemas = {}
        for name in ('manifest.json', 'ky_thuat.json'):
            schemas.update(doc_json((THU_MUC_CONTRACT / name).read_bytes(), limits))
        registry = registry.with_resources((key, Resource.from_contents(value))
                                            for key, value in schemas.items())
        Validator(schemas['urn:ktt:manifest:module.v1'], registry=registry,
                  format_checker=checker).validate(manifest)
        _semver(manifest['phien_ban'])
        for key, version in (('core', phien_ban_core), ('sdk_python', phien_ban_sdk_python),
                             ('sdk_js', phien_ban_sdk_js)):
            kiem_phien_ban(version, manifest['tuong_thich'][key])
        seen = set()
        for dep in manifest['goi']['phu_thuoc_module']:
            if dep['ma'] == manifest['ma'] or dep['ma'] in seen:
                raise LoiGoi('Module phụ thuộc trùng hoặc tự phụ thuộc.')
            seen.add(dep['ma'])
            if dep['ma'] not in (module_da_co or {}):
                raise LoiGoi('Thiếu module phụ thuộc trong snapshot Core.')
            kiem_phien_ban(module_da_co[dep['ma']], dep['phien_ban'])
        if manifest['du_lieu_rieng']['goi_migration']['ma'] != manifest['ma']:
            raise LoiGoi('Mã gói migration khác mã module.')
        operations, routes = set(), set()
        for op in manifest['thao_tac']:
            route = op['duong_dan']
            if not re.fullmatch(r'/(?:[a-z0-9_-]+|\{[a-z][a-z0-9_]*\})'
                                r'(?:/(?:[a-z0-9_-]+|\{[a-z][a-z0-9_]*\}))*|/', route):
                raise LoiGoi('Route có segment hoặc tham số không hợp lệ.')
            # Đổi tên placeholder không tạo một route mới.
            key = (op['phuong_thuc'], re.sub(r'\{[^}]+\}', '{}', route))
            if key in routes or op['ma'] in operations:
                raise LoiGoi('Trùng route hoặc mã thao tác trong gói.')
            operations.add(op['ma'])
            routes.add(key)

        def tep(name):
            kiem_ten_tep(name)
            if name not in files:
                raise LoiGoi('Thiếu tệp được manifest hoặc schema tham chiếu.')
            return files[name]

        # Kiểm tồn tại các entry point bằng đường dẫn, tuyệt đối không import.
        backend = manifest['backend']['diem_vao'].replace('.', '/')
        if backend + '.py' not in files and backend + '/__init__.py' not in files:
            raise LoiGoi('Thiếu entry point backend trong gói.')
        for name in [manifest['goi']['tep_kiem_ke'], manifest['giao_dien']['diem_vao'],
                     *manifest['giao_dien']['tai_nguyen'],
                     manifest['du_lieu_rieng']['goi_migration']['tep_kiem_ke'],
                     *(q['tep'] for q in manifest['quy_trinh']),
                     *(h['chu_ky'] for h in manifest['ham_core_goi'])]:
            tep(name)
        _kiem_kiem_ke(files, manifest, limits)
        migration_dir = manifest['du_lieu_rieng']['goi_migration']['thu_muc']
        kiem_ten_tep(migration_dir)
        if migration_dir not in dirs:
            raise LoiGoi('Thiếu thư mục migration trong gói.')

        local = {}
        for name in files:
            if name.startswith(('schema/', 'contract/')) and name.endswith('.json'):
                value = doc_json(files[name], limits)
                if (name.startswith('schema/') or name.endswith('.schema.json')
                        or isinstance(value, dict) and '$schema' in value):
                    local[name] = value
        contracts = []
        for group, entries in manifest['contract'].items():
            seen = set()
            for entry in entries:
                key = (entry['ma'], entry['phien_ban'])
                if key in seen:
                    raise LoiGoi('Trùng mã/phiên bản contract trong cùng nhóm.')
                seen.add(key)
                if not re.fullmatch(r'[1-9][0-9]*|(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)', entry['phien_ban']):
                    raise LoiGoi('Phiên bản contract không hợp lệ.')
                if group in ('cong_bo', 'su_kien_phat') and entry['module_so_huu'] != manifest['ma']:
                    raise LoiGoi('Sai module sở hữu contract công bố/phát.')
                description = doc_json(tep(entry['tep_mo_ta']), limits)
                _kiem_mo_ta_contract(description, entry)
                local[entry['schema']] = doc_json(tep(entry['schema']), limits)
                contracts.append(entry)
        for op in manifest['thao_tac']:
            for key in ('dau_vao', 'dau_ra'):
                ref = op[key]
                if ref.startswith(('schema/', 'contract/')):
                    local[ref] = doc_json(tep(ref), limits)
        for entry in manifest['cong_bo'] + manifest['du_lieu_rieng']['v4_cong_bo_doc']:
            ref = entry['schema']
            if ref.startswith(('schema/', 'contract/')):
                local[ref] = doc_json(tep(ref), limits)
        local_ids = set()
        for name, schema in local.items():
            Validator.check_schema(schema)
            if not isinstance(schema, dict) or schema.get('$schema') != DRAFT:
                raise LoiGoi('Schema gói phải dùng draft 2020-12.')
            uri = 'https://goi.invalid/' + name
            registry = registry.with_resource(uri, Resource.from_contents(schema))
            schema_id = schema.get('$id')
            if schema_id:
                if schema_id in local_ids:
                    raise LoiGoi('Trùng $id giữa các schema gói.')
                local_ids.add(schema_id)
                if schema_id in schemas and schemas[schema_id] != schema:
                    raise LoiGoi('Gói định nghĩa lại hoặc trùng $id schema.')
                schemas[schema_id] = schema
                registry = registry.with_resource(schema_id, Resource.from_contents(schema))
        for name, schema in local.items():
            # Giải cả ref trong nhánh ví dụ không đi qua; tuyệt đối không fetch.
            from referencing.jsonschema import DRAFT202012

            def check_refs(node, resolver):
                if not isinstance(node, dict):
                    return
                resolver = resolver.in_subresource(Resource.from_contents(
                    node, default_specification=DRAFT202012))
                for field in ('$ref', '$dynamicRef'):
                    if field in node:
                        resolver.lookup(node[field])
                for child in _schema_children(node):
                    check_refs(child, resolver)
            check_refs(schema, registry.resolver('https://goi.invalid/' + name))
        for entry in contracts:
            schema = local[entry['schema']]
            schema_id = schema.get('$id')
            if not isinstance(schema_id, str) or not schema_id:
                raise LoiGoi('Contract thiếu $id phiên bản.')
            version = entry['phien_ban']
            version = version + '.0.0' if version.isdigit() else version
            identity = re.fullmatch(r'urn:ktt:contract:[a-z][a-z0-9_]*\.v([1-9][0-9]*)'
                                    r'(?::([0-9]+\.[0-9]+\.[0-9]+))?', schema_id)
            if (not identity or int(identity[1]) != _semver(version)[0]
                    or (identity[2] or '1.0.0') != version):
                raise LoiGoi('Phiên bản contract không khớp $id đã ghim.')
            description = doc_json(tep(entry['tep_mo_ta']), limits)
            described = {field['ten'] for field in description['truong']}

            def check_fields(node, resolver, prefix='', visited=frozenset()):
                if not isinstance(node, dict):
                    return
                resolver = resolver.in_subresource(Resource.from_contents(
                    node, default_specification=DRAFT202012))
                for field in ('$ref', '$dynamicRef'):
                    if field in node and node[field] not in visited:
                        resolved = resolver.lookup(node[field])
                        check_fields(resolved.contents, resolved.resolver, prefix,
                                     visited | {node[field]})
                for key, child in node.get('properties', {}).items():
                    path = prefix + key
                    if path not in described:
                        raise LoiGoi('Bảng trường contract thiếu trường hoặc trường con trong schema.')
                    check_fields(child, resolver, path + '.', visited)
                for key in ('allOf', 'anyOf', 'oneOf', 'prefixItems'):
                    for child in node.get(key, []):
                        check_fields(child, resolver, prefix, visited)
                for key in ('items', 'if', 'then', 'else', 'dependentSchemas'):
                    if key == 'dependentSchemas':
                        for child in node.get(key, {}).values():
                            check_fields(child, resolver, prefix, visited)
                    elif key in node:
                        check_fields(node[key], resolver, prefix, visited)

            check_fields(schema, registry.resolver('https://goi.invalid/' + entry['schema']))
            example = doc_json(tep(entry['vi_du']), limits)
            Validator({'$ref': 'https://goi.invalid/' + entry['schema']}, registry=registry,
                      format_checker=checker).validate(example)
        refs = list(manifest['tuong_thich']['contract'])
        refs.extend(op[key] for op in manifest['thao_tac'] for key in ('dau_vao', 'dau_ra'))
        refs.extend(entry['schema'] for entry in
                    manifest['cong_bo'] + manifest['du_lieu_rieng']['v4_cong_bo_doc'])
        refs.extend(engine[key] for engine in manifest['engine_dung']
                    for key in ('dau_vao', 'dau_ra'))
        for ref in refs:
            if ref.startswith(('schema/', 'contract/')):
                ref = 'https://goi.invalid/' + ref
            elif not ref.startswith('urn:'):
                ref = 'urn:ktt:contract:' + ref
            registry.resolver().lookup(ref)
        hashes, total = bam_goi(files)
        return GoiDaKiem(manifest, MappingProxyType(files), tuple(sorted(dirs)),
                          MappingProxyType(hashes), total)
    except LoiGoi:
        raise
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        raise LoiGoi('Không đọc/kiểm được gói an toàn.') from exc
    except Exception as exc:
        # jsonschema/referencing có nhiều kiểu lỗi; không lộ input/đường dẫn qua báo cáo.
        raise LoiGoi('Manifest, schema, ví dụ hoặc tham chiếu offline không hợp lệ.') from exc


def _schema_children(node):
    for key in ('$defs', 'definitions', 'properties', 'patternProperties', 'dependentSchemas'):
        yield from node.get(key, {}).values()
    for key in ('allOf', 'anyOf', 'oneOf', 'prefixItems'):
        yield from node.get(key, [])
    for key in ('items', 'contains', 'if', 'then', 'else', 'not', 'additionalProperties',
                'unevaluatedProperties', 'propertyNames', 'unevaluatedItems', 'contentSchema'):
        if key in node:
            yield node[key]
