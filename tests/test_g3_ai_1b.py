"""AI-1b: contract hoi_ai.v1, DEMO và ca âm; chỉ kiểm offline.

Thiếu jsonschema thì meta-schema là CHUA_KIEM; fallback không thay chứng nhận.
Không gọi AI, dịch vụ ngoài hoặc đọc dữ liệu thật.
"""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_g2_17 as bundle


CONTRACT_ID = 'urn:ktt:contract:hoi_ai.v1'


class HoiAIContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = json.loads(
            (bundle.CONTRACT_DIR / 'ky_thuat.json').read_text(encoding='utf-8'))
        cls.schema = cls.schemas[CONTRACT_ID]
        blocks = bundle._blocks(bundle.SPEC)
        index = next(i for i, obj in enumerate(blocks)
                     if obj.get('$id') == CONTRACT_ID)
        cls.documented_schema, cls.demo = blocks[index:index + 2]
        if bundle.Draft202012Validator:
            def offline(uri):
                raise bundle.NoSuchResource(ref=uri)
            registry = bundle.Registry(retrieve=offline).with_resources(
                (key, bundle.Resource.from_contents(schema))
                for key, schema in cls.schemas.items())
            cls.validator = bundle.Draft202012Validator(cls.schema, registry=registry)

    def validate(self, value):
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng trong AI-1b')):
            if bundle.Draft202012Validator:
                self.validator.validate(value)
            bundle._minimal(value, self.schema, self.schema, self.schemas)

    def reject(self, **changes):
        value = {**deepcopy(self.demo), **changes}
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng trong AI-1b')):
            if bundle.Draft202012Validator:
                from jsonschema.exceptions import ValidationError
                with self.assertRaises(ValidationError):
                    self.validator.validate(value)
            with self.assertRaises(ValueError):
                bundle._minimal(value, self.schema, self.schema, self.schemas)

    @unittest.skipUnless(bundle.Draft202012Validator,
                         'CHUA_KIEM: thiếu jsonschema để kiểm meta-schema 2020-12')
    def test_meta_schema_2020_12(self):
        bundle.Draft202012Validator.check_schema(self.schema)

    def test_schema_khop_tai_lieu_va_ban_dau_khong_vo_noi_dung(self):
        self.assertEqual(self.schema, self.documented_schema)
        self.assertEqual(self.schema['$id'], CONTRACT_ID)
        self.assertEqual(self.schema['$schema'], bundle.DRAFT)
        self.assertIn('1.0.0', self.schema['$comment'])
        self.assertEqual(set(self.schema['required']), {'loai_viec', 'van_ban', 'chi_dan'})
        self.assertNotIn('vo_noi_dung', json.dumps(self.schema))
        self.assertEqual(self.schema['properties']['truong']['default'], [])
        self.assertEqual(self.schema['properties']['dinh_danh_da_biet']['default'], [])
        self.assertIs(self.schema['properties']['chi_cuc_bo']['default'], False)
        # Core chỉ duyệt schema object; false ở annotation/keyword vẫn hợp lệ.
        for node in bundle._nodes(self.schema):
            self.assertIsInstance(node, dict)
        pair = self.schema['$defs']['dinh_danh']['oneOf'][1]
        self.assertEqual(pair['prefixItems'], [{'type': 'string'}, {'type': 'string'}])
        self.assertEqual((pair['minItems'], pair['maxItems']), (2, 2))
        self.assertNotIn('items', pair)

    def test_demo_du_ba_dang_dinh_danh_dat(self):
        self.validate(deepcopy(self.demo))

    def test_bo_qua_tuy_chon_chi_dan_rong_va_nhom_rong_dat(self):
        value = {'loai_viec': 'HOI_DAP_VAY', 'van_ban': 'DEMO', 'chi_dan': ''}
        original = deepcopy(value)
        self.validate(value)
        self.assertEqual(value, original)  # default không tự điền payload.
        value.update(truong=[], chi_cuc_bo=False,
                     dinh_danh_da_biet=['', ['DEMO', ''], {'gia_tri': '', 'nhom': ''}])
        self.validate(value)

    def test_van_ban_chi_khoang_trang_bi_bac(self):
        self.reject(van_ban=' \t\r\n')

    def test_khoa_la_bi_bac(self):
        self.reject(khoa_la='DEMO')

    def test_ten_truong_rong_bi_bac(self):
        self.reject(truong=[''])

    def test_co_null_bi_bac(self):
        self.reject(chi_cuc_bo=None)

    def test_cap_dinh_danh_mot_phan_tu_bi_bac(self):
        self.reject(dinh_danh_da_biet=[['DEMO']])

    def test_object_dinh_danh_thieu_nhom_bi_bac(self):
        self.reject(dinh_danh_da_biet=[{'gia_tri': 'DEMO'}])

    def test_loai_viec_rong_bi_bac(self):
        self.reject(loai_viec='')

    def test_dinh_danh_da_biet_null_bi_bac(self):
        self.reject(dinh_danh_da_biet=None)

    def test_cap_dinh_danh_phai_dung_hai_chuoi_va_object_dong_khoa(self):
        for item in (['DEMO', 1], [1, 'CONG_TY'], ['DEMO', 'CONG_TY', 'THUA'],
                     {'gia_tri': 'DEMO', 'nhom': '', 'khoa_la': 'DEMO'}):
            with self.subTest(item=item):
                self.reject(dinh_danh_da_biet=[item])


if __name__ == '__main__':
    unittest.main()
