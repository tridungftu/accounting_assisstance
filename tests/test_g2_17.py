"""G2-17: bundle schema da chot, vi du va ca am hoan toan offline.

Neu co jsonschema: kiem meta-schema 2020-12 va dung Registry khong retrieval.
Neu thieu: chi dung bo kiem toi thieu cho tap keyword cua bundle nay;
kiem meta-schema day du la CHUA_KIEM, khong coi fallback la chung nhan.
Khong cai dependency, goi dich vu, truy cap PostgreSQL hoac du lieu that.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
import json
import math
from pathlib import Path
import re
import unittest
from unittest.mock import patch
from urllib.parse import unquote
import uuid

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry, Resource
    from referencing.exceptions import NoSuchResource
except ImportError:
    Draft202012Validator = None


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = ROOT / 'src/kho_tri_thuc/core/contract'
SPEC = ROOT / 'docs/47-core/g1/CONTRACT-DU-LIEU.md'
SDK_SPEC = ROOT / 'docs/47-core/g1/DAC-TA-SDK.md'
DRAFT = 'https://json-schema.org/draft/2020-12/schema'
TECH_NAMES = (
    'chung', 'tham_chieu_tep', 'van_ban_tai_lieu', 'du_lieu_bang',
    'tham_so', 'noi_dung_da_che', 'tra_loi_ai', 'hoa_don', 'loi_chuan', 'viec', 'hoi_ai',
)
EXPECTED = {
    'ky_thuat.json': {'urn:ktt:contract:' + name + '.v1' for name in TECH_NAMES},
    'manifest.json': {'urn:ktt:manifest:module.v1', 'urn:ktt:manifest:engine.v1'},
}


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Khoa JSON trung: ' + key)
        result[key] = value
    return result


def _constant(value):
    raise ValueError('JSON khong huu han: ' + value)


def _json(text):
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)


def _blocks(path):
    text = path.read_text(encoding='utf-8')
    return [_json(raw) for raw in re.findall(
        r'^```json[^\S\n]*\n(.*?)^```', text, re.MULTILINE | re.DOTALL)]


def _nodes(schema):
    """Duyet schema con, khong nham ten truong du lieu voi keyword."""
    yield schema
    for key in ('$defs', 'properties'):
        for child in schema.get(key, {}).values():
            yield from _nodes(child)
    for key in ('allOf', 'anyOf', 'oneOf'):
        for child in schema.get(key, []):
            yield from _nodes(child)
    for key in ('items', 'contains', 'if', 'then', 'else', 'not'):
        if key in schema:
            yield from _nodes(schema[key])


def _resolve(ref, root, schemas):
    resource_id, _, fragment = ref.partition('#')
    resource = schemas[resource_id] if resource_id else root
    target = resource
    if fragment:
        if not fragment.startswith('/'):
            raise ValueError('Chi ho tro JSON Pointer trong bundle')
        for key in unquote(fragment)[1:].split('/'):
            target = target[key.replace('~1', '/').replace('~0', '~')]
    return target, resource


def _equal(left, right):
    # JSON Schema phan biet boolean va number (Python True == 1).
    return _json_key(left) == _json_key(right)


def _json_key(value):
    if isinstance(value, bool):
        return ('boolean', value)
    if isinstance(value, (int, float)):
        return ('number', value)
    if isinstance(value, dict):
        return ('object', tuple(sorted((k, _json_key(v)) for k, v in value.items())))
    if isinstance(value, list):
        return ('array', tuple(_json_key(v) for v in value))
    return (type(value).__name__, value)


def _format(value, kind):
    if kind == 'uuid':
        if not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', value):
            raise ValueError('uuid')
        uuid.UUID(value)
    elif kind == 'date':
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
            raise ValueError('date')
        date.fromisoformat(value)
    elif kind == 'date-time':
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})', value):
            raise ValueError('date-time')
        datetime.fromisoformat(value.upper().replace('Z', '+00:00'))
    else:
        raise RuntimeError('Format chua ho tro: ' + kind)


def _minimal(value, schema, root, schemas):
    """Chi cho test: subset 2020-12 hien dung, tra properties da danh gia."""
    evaluated = set()

    def require(ok, keyword):
        if not ok:
            raise ValueError(keyword)

    def check(child):
        return _minimal(value, child, root, schemas)

    def valid(child):
        try:
            return True, check(child)
        except ValueError:
            return False, set()

    if '$ref' in schema:
        target, ref_root = _resolve(schema['$ref'], root, schemas)
        evaluated.update(_minimal(value, target, ref_root, schemas))
    types = {
        'object': isinstance(value, dict), 'array': isinstance(value, list),
        'string': isinstance(value, str), 'boolean': isinstance(value, bool),
        'null': value is None,
        'number': type(value) in (int, float),
        'integer': type(value) in (int, float) and value % 1 == 0,
    }
    if 'type' in schema:
        names = schema['type'] if isinstance(schema['type'], list) else [schema['type']]
        require(any(types[name] for name in names), 'type')
    if 'const' in schema:
        require(_equal(value, schema['const']), 'const')
    if 'enum' in schema:
        require(any(_equal(value, item) for item in schema['enum']), 'enum')
    if 'not' in schema:
        require(not valid(schema['not'])[0], 'not')
    for child in schema.get('allOf', []):
        evaluated.update(check(child))
    for key in ('anyOf', 'oneOf'):
        if key in schema:
            matches = [props for ok, props in map(valid, schema[key]) if ok]
            require(bool(matches) if key == 'anyOf' else len(matches) == 1, key)
            for props in matches:
                evaluated.update(props)
    if 'if' in schema:
        ok, props = valid(schema['if'])
        if ok:
            evaluated.update(props)
        evaluated.update(check(schema.get('then' if ok else 'else', {})))
    if isinstance(value, dict):
        require(set(schema.get('required', [])) <= value.keys(), 'required')
        properties = schema.get('properties', {})
        for key in value.keys() & properties.keys():
            _minimal(value[key], properties[key], root, schemas)
            evaluated.add(key)
        if schema.get('additionalProperties') is False:
            require(value.keys() <= properties.keys(), 'additionalProperties')
        for key, dependencies in schema.get('dependentRequired', {}).items():
            if key in value:
                require(set(dependencies) <= value.keys(), 'dependentRequired')
        if schema.get('unevaluatedProperties') is False:
            require(value.keys() <= evaluated, 'unevaluatedProperties')
    if isinstance(value, list):
        require(len(value) >= schema.get('minItems', 0), 'minItems')
        require(len(value) <= schema.get('maxItems', math.inf), 'maxItems')
        if schema.get('uniqueItems'):
            require(len({_json_key(item) for item in value}) == len(value), 'uniqueItems')
        if 'items' in schema:
            for item in value:
                _minimal(item, schema['items'], root, schemas)
        if 'contains' in schema:
            found = False
            for item in value:
                try:
                    _minimal(item, schema['contains'], root, schemas)
                    found = True
                except ValueError:
                    pass
            require(found, 'contains')
    if isinstance(value, str):
        require(len(value) >= schema.get('minLength', 0), 'minLength')
        require(len(value) <= schema.get('maxLength', math.inf), 'maxLength')
        if 'pattern' in schema:
            require(re.search(schema['pattern'], value) is not None, 'pattern')
        if 'format' in schema:
            _format(value, schema['format'])
    if type(value) in (int, float):
        require(math.isfinite(value), 'finite')
        require(value >= schema.get('minimum', -math.inf), 'minimum')
        require(value <= schema.get('maximum', math.inf), 'maximum')
        require(value > schema.get('exclusiveMinimum', -math.inf), 'exclusiveMinimum')
    return evaluated


class BundleContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundles = {name: _json((CONTRACT_DIR / name).read_text(encoding='utf-8'))
                       for name in EXPECTED}
        cls.schemas = {}
        for bundle in cls.bundles.values():
            cls.schemas.update(bundle)
        blocks = _blocks(SPEC)
        cls.originals = {obj['$id']: obj for obj in blocks if '$id' in obj}
        cls.examples = {}
        current = None
        for obj in blocks:
            if '$id' in obj:
                current = obj['$id']
            else:
                key = current + '#/$defs/da_nhan' if 'viec_id' in obj else current
                cls.examples[key] = obj
        for obj in _blocks(SDK_SPEC):
            if obj.get('loai') in ('module', 'engine'):
                cls.examples['urn:ktt:manifest:' + obj['loai'] + '.v1'] = obj
        if Draft202012Validator:
            # Khong phu thuoc rfc3339-validator hay checker tuy chon cua runtime.
            cls.format_checker = FormatChecker()
            for kind in ('date', 'date-time'):
                def check(value, kind=kind):
                    if isinstance(value, str):
                        _format(value, kind)
                    return True
                cls.format_checker.checks(kind, raises=ValueError)(check)

            def offline(uri):
                raise NoSuchResource(ref=uri)
            cls.registry = Registry(retrieve=offline).with_resources(
                (key, Resource.from_contents(schema)) for key, schema in cls.schemas.items())

    def validate(self, key, value, *, minimal=False):
        schema, root = _resolve(key, {}, self.schemas)
        # Bat moi thu ket noi ngay trong test, ke ca khi doi cach tao registry.
        with patch('socket.socket', side_effect=AssertionError('Cam mang trong test G2-17')):
            if Draft202012Validator and not minimal:
                validator = Draft202012Validator(schema, registry=self.registry,
                                                 format_checker=self.format_checker)
                # Subschema co ref # can giu base URI cua tai nguyen goc.
                validator = validator.evolve(schema={'$ref': key})
                validator.validate(value)
            else:
                _minimal(value, schema, root, self.schemas)

    def reject(self, key, value, *, minimal=False):
        if Draft202012Validator and not minimal:
            from jsonschema.exceptions import ValidationError
            error = ValidationError
        else:
            error = ValueError
        with self.assertRaises(error):
            self.validate(key, value, minimal=minimal)

    def example(self, name):
        key = 'urn:ktt:contract:' + name + '.v1'
        return key, deepcopy(self.examples[key])

    def test_dung_13_id_khong_them_schema_con_cho(self):
        self.assertEqual(set(self.schemas), set(self.originals))
        for name, ids in EXPECTED.items():
            with self.subTest(file=name):
                self.assertEqual(set(self.bundles[name]), ids)
                for key, schema in self.bundles[name].items():
                    self.assertEqual(key, schema['$id'])
                    self.assertEqual(schema['$schema'], DRAFT)

    def test_noi_dung_trung_nguyen_van_sau_parse_json(self):
        for key, schema in self.schemas.items():
            with self.subTest(id=key):
                original = deepcopy(self.originals[key])
                if key == 'urn:ktt:manifest:engine.v1':
                    # CD-038 chi sua ngoai le man hinh; phan con lai van khop G1.
                    profile = original['properties']['ho_so_chay_mau']
                    profile['properties']['headless'] = {'type': 'boolean'}
                    profile['properties']['ngoai_le_man_hinh'] = {
                        'type': 'object', 'additionalProperties': False,
                        'required': ['ma_quyet_dinh', 'ly_do'],
                        'properties': {
                            'ma_quyet_dinh': {'enum': ['CD-038-ENGINE-2A',
                                                      'CD-038-ENGINE-3A']},
                            'ly_do': {'type': 'string', 'minLength': 1, 'pattern': r'\S'},
                        },
                    }
                    profile['if'] = {'properties': {'headless': {'const': False}}}
                    profile['then'] = {'required': ['ngoai_le_man_hinh']}
                    profile['else'] = {'not': {'required': ['ngoai_le_man_hinh']}}
                # Giu moi ky tu trong gia tri, chi bo qua whitespace cua JSON.
                self.assertEqual(schema, original)

    @unittest.skipUnless(Draft202012Validator, 'CHUA_KIEM: thieu jsonschema; fallback khong thay meta-schema 2020-12')
    def test_meta_schema_2020_12_day_du(self):
        for key, schema in self.schemas.items():
            with self.subTest(id=key):
                Draft202012Validator.check_schema(schema)

    def test_cau_truc_schema_toi_thieu_va_keyword_fallback(self):
        annotations = {'$schema', '$id', '$comment', 'title', 'default'}
        supported = annotations | {
            '$defs', '$ref', 'type', 'const', 'enum', 'properties', 'required',
            'additionalProperties', 'unevaluatedProperties', 'dependentRequired',
            'allOf', 'anyOf', 'oneOf', 'if', 'then', 'else', 'not', 'items', 'contains',
            'uniqueItems', 'minItems', 'maxItems', 'minLength', 'maxLength',
            'pattern', 'format', 'minimum', 'maximum', 'exclusiveMinimum',
        }
        for key, schema in self.schemas.items():
            for node in _nodes(schema):
                with self.subTest(id=key, node=node):
                    self.assertIsInstance(node, dict)
                    self.assertFalse(set(node) - supported)
                    if 'type' in node:
                        names = node['type'] if isinstance(node['type'], list) else [node['type']]
                        self.assertTrue(set(names) <= {'object', 'array', 'string', 'integer', 'number', 'boolean', 'null'})
                    for keyword in ('required', 'enum', 'allOf', 'anyOf', 'oneOf'):
                        if keyword in node:
                            self.assertIsInstance(node[keyword], list)
                    if 'required' in node:
                        self.assertEqual(len(set(node['required'])), len(node['required']))
                    if 'pattern' in node:
                        re.compile(node['pattern'])

    def test_moi_ref_giai_offline_ke_ca_nhanh_khong_chay(self):
        count = 0
        for key, schema in self.schemas.items():
            for node in _nodes(schema):
                if '$ref' in node:
                    with self.subTest(id=key, ref=node['$ref']):
                        target, _ = _resolve(node['$ref'], schema, self.schemas)
                        self.assertIsInstance(target, dict)
                        if Draft202012Validator:
                            resolved = self.registry.resolver(key).lookup(node['$ref'])
                            self.assertEqual(resolved.contents, target)
                        count += 1
        self.assertGreater(count, 100)

    def test_ref_la_khong_duoc_tai_mang(self):
        for ref in ('https://example.invalid/schema', 'urn:ktt:contract:chua_duyet.v1',
                    'urn:ktt:contract:chung.v1#/$defs/khong_co'):
            with self.subTest(ref=ref), self.assertRaises(KeyError):
                _resolve(ref, {}, self.schemas)

    def test_du_11_vi_du_contract_va_2_manifest_deu_qua(self):
        self.assertEqual(len(self.examples), 13)
        self.assertEqual(set(self.examples), set(self.schemas) - {'urn:ktt:contract:chung.v1'}
                         | {'urn:ktt:contract:viec.v1#/$defs/da_nhan'})
        for key, value in self.examples.items():
            with self.subTest(id=key):
                self.validate(key, value)
                self.validate(key, value, minimal=True)

    def test_thieu_truong_bat_buoc_bi_bac_o_moi_vi_du(self):
        for key, example in self.examples.items():
            schema, root = _resolve(key, {}, self.schemas)
            required = set(schema.get('required', []))
            for child in schema.get('allOf', []):
                if '$ref' in child:
                    target, _ = _resolve(child['$ref'], root, self.schemas)
                    required.update(target.get('required', []))
            for field in required:
                value = deepcopy(example)
                value.pop(field)
                with self.subTest(id=key, field=field):
                    self.reject(key, value)

    def test_truong_la_va_sai_kieu_bi_bac_o_moi_vi_du(self):
        for key, example in self.examples.items():
            with self.subTest(id=key):
                self.reject(key, {**example, 'truong_chua_khai': 'DEMO'})
                self.reject(key, [])
                self.reject(key, None)

    def test_sai_phien_ban_contract_va_manifest(self):
        for key, example in self.examples.items():
            for field in ('phien_ban', 'contract', 'phien_ban_manifest'):
                if field in example and not key.startswith('urn:ktt:manifest:'):
                    with self.subTest(id=key, field=field):
                        self.reject(key, {**example, field: 'chua_duyet'})
            if key.startswith('urn:ktt:manifest:'):
                self.reject(key, {**example, 'phien_ban_manifest': 2})
                self.reject(key, {**example, 'loai': 'sai'})
                self.reject(key, {**example, 'phien_ban': 'v1'})

    def test_cloud_thieu_luot_che_o_ca_ba_duong_bi_bac(self):
        for source in ('duong', 'truong', 'mo_hinh'):
            key, value = self.example('tra_loi_ai')
            if source == 'duong':
                value['duong'] = 'CLOUD'
            elif source == 'truong':
                value['truong'][0]['nguon'] = 'CLOUD'
            else:
                value['mo_hinh'][0]['duong'] = 'CLOUD'
            value['kiem_tra']['mo_che'] = 'dat'
            with self.subTest(source=source):
                self.reject(key, value)
                value['luot_che_id'] = '10000000-0000-4000-8000-000000000003'
                # Gan LOCAL khong ne duoc CLOUD trong truong/model.
                if source != 'duong':
                    self.reject(key, value)
                value['duong'] = 'LOCAL+CLOUD'
                self.validate(key, value)
                value['kiem_tra']['mo_che'] = 'khong_ap_dung'
                self.reject(key, value)
                value['kiem_tra']['mo_che'] = 'dat'
                value['luot_che_id'] = None
                self.reject(key, value)

    def test_mask_con_sot_danh_muc_khoa_va_mat_tien_ngay(self):
        for field, invalid in (('so_con_sot', 1), ('danh_muc', 'da_khoa'),
                               ('giu_nguyen_tien_ngay', False)):
            key, value = self.example('noi_dung_da_che')
            value['kiem_tra'][field] = invalid
            with self.subTest(field=field):
                self.reject(key, value)

    def test_format_uuid_ngay_va_thoi_diem_bat_buoc(self):
        cases = (
            ('id', 'khong-phai-uuid'), ('ngay', '2026-02-30'),
            ('ngay', '30/10/2026'), ('thoi_diem', '2026-02-30T04:00:00Z'),
            ('thoi_diem', '2026-10-30T04:00:00'),
            ('thoi_diem', '2026-10-30T04:00:00+00:00'),
        )
        for name, value in cases:
            with self.subTest(name=name, value=value):
                self.reject('urn:ktt:contract:chung.v1#/$defs/' + name, value)
        self.validate('urn:ktt:contract:chung.v1#/$defs/ngay', '2028-02-29')

    def test_tien_decimal_khong_ep_kieu_khong_vuot_mien(self):
        key = 'urn:ktt:contract:chung.v1#/$defs/tien'
        for amount in (1000, '1.000.000', '01', '1e3', '1000000000000000000', '0.1234567'):
            with self.subTest(amount=amount):
                self.reject(key, {'gia_tri': amount, 'don_vi_tien': 'VND'})
        self.reject(key, {'gia_tri': '0', 'don_vi_tien': 'vnd'})
        self.validate(key, {'gia_tri': '999999999999999999.123456', 'don_vi_tien': 'VND'})

    def test_vi_tri_bbox_can_khung_va_gia_tri_can_ly_do(self):
        key = 'urn:ktt:contract:chung.v1#/$defs/vi_tri'
        value = {'tep_id': '10000000-0000-4000-8000-000000000001',
                 'dinh_vi': 'DEMO', 'bbox': [0, 0, 1, 1]}
        self.reject(key, value)
        value['khung_toa_do'] = {'don_vi': 'pixel', 'rong': 10, 'cao': 10}
        self.validate(key, value)
        self.reject('urn:ktt:contract:chung.v1#/$defs/gia_tri', {'kieu': 'chua_ro'})

    def test_hoa_don_khong_tu_nang_trang_thai_va_decimal_thieu(self):
        for field, invalid in (('trang_thai_thue', 'VALID'),
                               ('ghi_nhan_nghiep_vu', 'PERFORMED')):
            key, value = self.example('hoa_don')
            value[field] = invalid
            self.reject(key, value)
        key, value = self.example('hoa_don')
        value['dong'][0]['so_luong'] = {'trang_thai': 'ABSENT', 'gia_tri': '0'}
        self.reject(key, value)
        value['dong'][0]['so_luong']['gia_tri'] = None
        self.validate(key, value)

    def test_viec_polling_va_bien_nhan_khong_thay_the_nhau(self):
        key = 'urn:ktt:contract:viec.v1'
        receipt = key + '#/$defs/da_nhan'
        self.reject(key, self.examples[receipt])
        self.reject(receipt, self.examples[key])
        for progress in (-1, 101, True):
            self.reject(key, {**self.examples[key], 'tien_do': progress})

    def test_module_contract_du_bon_nhom_va_duong_dan(self):
        key = 'urn:ktt:manifest:module.v1'
        original = self.examples[key]
        for group in ('cong_bo', 'su_kien_phat', 'su_kien_nhan', 'dau_vao_nguon'):
            value = deepcopy(original)
            value['contract'].pop(group)
            with self.subTest(group=group):
                self.reject(key, value)
        value = deepcopy(original)
        value['contract'] = {group: [] for group in original['contract']}
        self.validate(key, value)
        for field in ('tep_mo_ta', 'schema', 'vi_du'):
            for path in ('../that.json', '/contract/x.json', 'schema/x.json', 'contract/../x.json'):
                value = deepcopy(original)
                value['contract']['cong_bo'][0][field] = path
                with self.subTest(field=field, path=path):
                    self.reject(key, value)

    def test_module_viec_dung_bien_nhan_va_get_khong_tao_viec(self):
        key = 'urn:ktt:manifest:module.v1'
        original = self.examples[key]
        index = next(i for i, op in enumerate(original['thao_tac']) if op['kieu'] == 'viec')
        for field, invalid in (('dau_ra', 'urn:ktt:contract:viec.v1'),
                               ('chong_trung', False), ('phuong_thuc', 'GET')):
            value = deepcopy(original)
            value['thao_tac'][index][field] = invalid
            with self.subTest(field=field):
                self.reject(key, value)

    def test_manifest_khong_nhan_bi_mat_role_schema_hay_cong_tu_chon(self):
        for kind in ('module', 'engine'):
            key = 'urn:ktt:manifest:' + kind + '.v1'
            for field in ('password', 'role', 'schema', 'cong'):
                with self.subTest(kind=kind, field=field):
                    self.reject(key, {**self.examples[key], field: 'DEMO'})
        key = 'urn:ktt:manifest:module.v1'
        value = deepcopy(self.examples[key])
        value['du_lieu_rieng']['goi_migration']['vai'] = 'DEMO'
        self.reject(key, value)

    def test_engine_khong_login_csdl_va_tai_nguyen_trong_mien(self):
        key = 'urn:ktt:manifest:engine.v1'
        original = self.examples[key]
        value = deepcopy(original)
        value['ho_so_chay_mau']['login_csdl'] = True
        self.reject(key, value)
        for field, invalid in (('ram_toi_da_mib_de_xuat', 0),
                               ('cpu_phan_tram_toi_da_de_xuat', 101)):
            value = deepcopy(original)
            value['tai_nguyen'][field] = invalid
            self.reject(key, value)
        value = deepcopy(original)
        value['readiness'].pop('kiem')
        self.reject(key, value)

    def test_engine_co_man_hinh_chi_qua_voi_ngoai_le_cd038(self):
        key = 'urn:ktt:manifest:engine.v1'
        for code in ('CD-038-ENGINE-2A', 'CD-038-ENGINE-3A'):
            value = deepcopy(self.examples[key])
            value['ho_so_chay_mau'].update({
                'headless': False,
                'ngoai_le_man_hinh': {'ma_quyet_dinh': code,
                                     'ly_do': 'DEMO: phien Windows rieng co man hinh'},
            })
            for minimal in (False, True):
                with self.subTest(code=code, minimal=minimal):
                    self.validate(key, value, minimal=minimal)

    def test_engine_co_man_hinh_thieu_ngoai_le_hoac_ma_la_bi_bac(self):
        key = 'urn:ktt:manifest:engine.v1'
        for exception in (None, {}, {'ly_do': 'DEMO'},
                          {'ma_quyet_dinh': 'CD-038-ENGINE-4A', 'ly_do': 'DEMO'},
                          {'ma_quyet_dinh': 'CD-038', 'ly_do': 'DEMO'}):
            value = deepcopy(self.examples[key])
            value['ho_so_chay_mau']['headless'] = False
            if exception is not None:
                value['ho_so_chay_mau']['ngoai_le_man_hinh'] = exception
            for minimal in (False, True):
                with self.subTest(exception=exception, minimal=minimal):
                    self.reject(key, value, minimal=minimal)

    def test_engine_ngoai_le_phai_co_ly_do_va_dung_cau_truc(self):
        key = 'urn:ktt:manifest:engine.v1'
        approved = {'ma_quyet_dinh': 'CD-038-ENGINE-3A', 'ly_do': 'DEMO'}
        exceptions = [None, [], 'CD-038-ENGINE-3A',
                      {'ma_quyet_dinh': 'CD-038-ENGINE-3A'},
                      {**approved, 'tu_duyet': True}]
        exceptions += [{**approved, 'ly_do': reason}
                       for reason in ('', ' \t\n', None, 123)]
        for exception in exceptions:
            value = deepcopy(self.examples[key])
            value['ho_so_chay_mau'].update({
                'headless': False, 'ngoai_le_man_hinh': exception})
            for minimal in (False, True):
                with self.subTest(exception=exception, minimal=minimal):
                    self.reject(key, value, minimal=minimal)

    def test_engine_headless_khong_duoc_khai_ngoai_le(self):
        key = 'urn:ktt:manifest:engine.v1'
        for code in ('CD-038-ENGINE-2A', 'CD-038-ENGINE-3A'):
            value = deepcopy(self.examples[key])
            value['ho_so_chay_mau']['ngoai_le_man_hinh'] = {
                'ma_quyet_dinh': code, 'ly_do': 'DEMO'}
            for minimal in (False, True):
                with self.subTest(code=code, minimal=minimal):
                    self.reject(key, value, minimal=minimal)

    def test_engine_headless_van_bat_buoc_dung_kieu_boolean(self):
        key = 'urn:ktt:manifest:engine.v1'
        for headless in (None, 0, 1, 'false'):
            value = deepcopy(self.examples[key])
            value['ho_so_chay_mau'].update({
                'headless': headless,
                'ngoai_le_man_hinh': {'ma_quyet_dinh': 'CD-038-ENGINE-2A',
                                     'ly_do': 'DEMO'},
            })
            for minimal in (False, True):
                with self.subTest(headless=headless, minimal=minimal):
                    self.reject(key, value, minimal=minimal)

    def test_engine_capability_van_bat_buoc_khong_rong_ke_ca_ngoai_le(self):
        key = 'urn:ktt:manifest:engine.v1'
        for code in (None, 'CD-038-ENGINE-2A', 'CD-038-ENGINE-3A'):
            for capability in (None, [], '', [{}]):
                value = deepcopy(self.examples[key])
                if code is not None:
                    value['ho_so_chay_mau'].update({
                        'headless': False,
                        'ngoai_le_man_hinh': {'ma_quyet_dinh': code, 'ly_do': 'DEMO'},
                    })
                if capability is None:
                    value.pop('capability')
                else:
                    value['capability'] = capability
                for minimal in (False, True):
                    with self.subTest(code=code, capability=capability, minimal=minimal):
                        self.reject(key, value, minimal=minimal)

    def test_doc_json_chan_khoa_trung_va_so_khong_huu_han(self):
        for raw in ('{"x":1,"x":2}', '{"x":{"a":1,"a":2}}',
                    '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                _json(raw)


if __name__ == '__main__':
    unittest.main()
