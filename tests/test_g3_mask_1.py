"""MASK-1: dự thảo offline, không nhập/chạy Mask, không đăng ký contract.

G2-17 bắt capability không rỗng và hồ sơ chạy; MASK-1 chưa có adapter/schema
được duyệt nên engine.json cố ý chưa cài được. Không điền năng lực giả để
làm xanh validator. Meta-schema đầy đủ là CHUA_KIEM nếu thiếu jsonschema.
"""

from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

import test_g2_17 as contract_tests


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'src/kho_tri_thuc/engines/e_mask'
SCHEMA_NAMES = {'che_van_ban_vao', 'che_van_ban_ra', 'mo_che_vao', 'mo_che_ra'}


class Mask1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = contract_tests._json((ENGINE / 'engine.json').read_text('utf-8'))
        cls.draft = contract_tests._json((ENGINE / 'contract/du_thao.json').read_text('utf-8'))
        cls.schemas = cls.draft['schemas']
        contract_tests.BundleContractTest.setUpClass()
        cls.core = contract_tests.BundleContractTest()
        # Chỉ bộ kiểm test nhìn thấy schema nháp; không thêm vào registry Core.
        cls.private_schemas = {s['$id']: s for s in cls.schemas.values()}
        if contract_tests.Draft202012Validator:
            def offline(uri):
                raise contract_tests.NoSuchResource(ref=uri)
            cls.private_registry = contract_tests.Registry(retrieve=offline).with_resources(
                (key, contract_tests.Resource.from_contents(schema))
                for key, schema in cls.private_schemas.items())

    def validate(self, name, value):
        schema = self.schemas[name]
        with patch('socket.socket', side_effect=AssertionError('MASK-1 cấm mạng')):
            contract_tests._minimal(value, schema, schema, self.private_schemas)
            if contract_tests.Draft202012Validator:
                contract_tests.Draft202012Validator(
                    schema, registry=self.private_registry).validate(value)

    def reject(self, name, value):
        # Luôn kiểm nhánh fallback; jsonschema nếu có cũng được chạy ở ca dương.
        with self.assertRaises(ValueError):
            self.validate(name, value)

    def example(self, name):
        return deepcopy(self.schemas[name]['examples'][0])

    def test_bon_schema_deu_la_du_thao_chua_kich_hoat(self):
        self.assertEqual(set(self.schemas), SCHEMA_NAMES)
        self.assertEqual(self.draft['trang_thai'], 'du_thao_cho_Anh_duyet')
        self.assertIs(self.draft['kich_hoat'], False)
        self.assertIs(self.draft['dang_ky'], False)
        for name, schema in self.schemas.items():
            with self.subTest(name=name):
                self.assertEqual(schema['$id'], 'urn:ktt:du-thao:e_mask:' + name + '.v1')
                self.assertEqual(schema['$schema'], contract_tests.DRAFT)
                self.assertIn('CHƯA DUYỆT/ĐĂNG KÝ/KÍCH HOẠT', schema['$comment'])
                self.assertIs(schema['additionalProperties'], False)

    @unittest.skipUnless(contract_tests.Draft202012Validator,
                         'CHUA_KIEM: thiếu jsonschema; fallback không thay meta-schema 2020-12')
    def test_meta_schema_day_du_offline(self):
        with patch('socket.socket', side_effect=AssertionError('MASK-1 cấm mạng')):
            for schema in self.schemas.values():
                contract_tests.Draft202012Validator.check_schema(schema)

    def test_schema_nhap_khong_co_trong_so_contract_core(self):
        self.assertTrue(self.private_schemas.keys().isdisjoint(self.core.schemas))
        for schema_id in self.private_schemas:
            with self.subTest(schema=schema_id), self.assertRaises(KeyError):
                contract_tests._resolve(schema_id, {}, self.core.schemas)
        # Không có $ref sang bản nháp, kể cả nhánh không chạy, trong bundle dùng chung.
        for schema in self.core.schemas.values():
            for node in contract_tests._nodes(schema):
                self.assertNotIn('du-thao', node.get('$ref', ''))

    def test_manifest_khong_quang_ba_nang_luc_chua_duyet(self):
        self.assertEqual(self.manifest['ma'], 'e_mask')
        self.assertEqual(self.manifest['loai'], 'engine')
        self.assertEqual(self.manifest['capability'], [])
        self.assertEqual(self.manifest['ket_noi_ngoai'], [])
        self.assertNotIn('adapter', self.manifest)
        self.assertNotIn('ho_so_chay_mau', self.manifest)
        self.assertNotIn('contract', self.manifest)
        self.assertIn('draft', self.manifest['phien_ban'])
        self.core.reject('urn:ktt:manifest:engine.v1', self.manifest)
        # Chặn kích hoạt ngay cả khi ai đó bổ sung hồ sơ chạy mẫu:
        # chưa được phép thêm capability để vượt điều kiện này.
        candidate = deepcopy(self.core.examples['urn:ktt:manifest:engine.v1'])
        candidate['ma'] = 'e_mask'
        candidate['capability'] = self.manifest['capability']
        self.core.reject('urn:ktt:manifest:engine.v1', candidate)

    def test_vi_du_tong_hop_hop_le(self):
        for name in self.schemas:
            with self.subTest(name=name):
                self.validate(name, self.example(name))

    def test_thieu_truong_bat_buoc_deu_bi_chan(self):
        for name, schema in self.schemas.items():
            for field in schema['required']:
                with self.subTest(name=name, field=field):
                    value = self.example(name)
                    value.pop(field)
                    self.reject(name, value)

    def test_khong_nhan_mapping_bi_mat_hay_id_core_thay_ma_luot(self):
        for name in self.schemas:
            for field in ('mapping', 'mat_khau', 'api_key', 'luot_che_id', 'quy_tac_revision'):
                with self.subTest(name=name, field=field):
                    value = self.example(name)
                    value[field] = 'DEMO'
                    self.reject(name, value)
        value = self.example('mo_che_vao')
        value['luot_che_id'] = value.pop('ma_luot')
        self.reject('mo_che_vao', value)

    def test_dinh_danh_chuoi_object_va_mac_dinh_dung_nguon(self):
        name = 'che_van_ban_vao'
        self.validate(name, {'van_ban': 'DEMO'})
        self.validate(name, {'van_ban': 'DEMO', 'dinh_danh_da_biet': [
            'DEMO tên', {'gia_tri': 'DEMO mã'}, {'gia_tri': 'DEMO mã', 'nhom': 'GIAY_TO'}]})
        props = self.schemas[name]['properties']
        self.assertEqual(props['dinh_danh_da_biet']['default'], [])
        self.assertEqual(props['dinh_danh_da_biet']['items']['anyOf'][1]
                         ['properties']['nhom']['default'], 'KHAC')
        for item in (None, 123, {}, {'gia_tri': 'DEMO', 'mapping': {}},
                     {'gia_tri': 'a' * 301}, {'gia_tri': 'DEMO', 'nhom': 'a' * 21}):
            with self.subTest(item=type(item).__name__):
                self.reject(name, {'van_ban': 'DEMO', 'dinh_danh_da_biet': [item]})
        self.validate(name, {'van_ban': 'DEMO', 'dinh_danh_da_biet': ['a' * 300] * 500})
        self.reject(name, {'van_ban': 'DEMO', 'dinh_danh_da_biet': ['DEMO'] * 501})

    def test_gioi_han_van_ban_va_ma_luot(self):
        for name in ('che_van_ban_vao', 'mo_che_vao'):
            value = self.example(name)
            value['van_ban'] = 'a' * 500000
            self.validate(name, value)
            value['van_ban'] += 'a'
            self.reject(name, value)
        for name in ('mo_che_vao', 'che_van_ban_ra'):
            value = self.example(name)
            value['ma_luot'] = 'a' * 64
            self.validate(name, value)
            for bad in ('', 'a' * 65, None, 123):
                value['ma_luot'] = bad
                self.reject(name, value)

    def test_phan_hoi_che_khong_nhan_loi_hoac_con_sot(self):
        name = 'che_van_ban_ra'
        for field, bad in (('gui_duoc', False), ('gui_duoc', 1),
                           ('con_sot', ['DEMO']), ('con_sot', None),
                           ('danh_muc', 'khoa'), ('het_han_sau_giay', 0),
                           ('so_cho_thay', -1), ('so_cho_thay', True)):
            with self.subTest(field=field, bad=bad):
                value = self.example(name)
                value[field] = bad
                self.reject(name, value)
        # Mô tả đúng HTTP nguồn, không biến schema thành quyền gửi Cloud.
        value = self.example(name)
        value['danh_muc'] = 'chua_co'
        self.validate(name, value)

    def test_truong_chi_tiet_phan_hoi_che(self):
        name = 'che_van_ban_ra'
        value = self.example(name)
        value['bi_danh'] = [{'bi_danh': '[DEMO_1]', 'nhom': 'KHAC', 'nguon': 'phat_hien_moi'}]
        value['cum_moi'] = [{'cum': 'DEMO cụm', 'bi_danh': '[DEMO_1]', 'nhom': 'KHAC'}]
        value['cho_duyet']['so_cum_vua_them'] = 1
        value['canh_bao'] = ['DEMO cảnh báo']
        self.validate(name, value)
        for field, bad in (('bi_danh', [{'bi_danh': '[DEMO_1]'}]),
                           ('cum_moi', [{'cum': 'DEMO cụm'}]),
                           ('cho_duyet', {'so_cum_vua_them': -1}), ('canh_bao', [1])):
            invalid = deepcopy(value)
            invalid[field] = bad
            self.reject(name, invalid)

    def test_mo_che_don_luot_va_bi_danh_chua_ro(self):
        name = 'mo_che_vao'
        value = self.example(name)
        value.pop('ket_thuc_luot')
        self.validate(name, value)
        self.assertIs(self.schemas[name]['properties']['ket_thuc_luot']['default'], False)
        for bad in ('false', 0, None):
            value['ket_thuc_luot'] = bad
            self.reject(name, value)
        name = 'mo_che_ra'
        value = self.example(name)
        value.update(van_ban='DEMO [LA_1]', bi_danh_khong_ro=['[LA_1]'], luot_con_giu=True)
        self.validate(name, value)
        for field, bad in (('so_cho_mo', -1), ('bi_danh_khong_ro', [1]), ('luot_con_giu', 1)):
            invalid = deepcopy(value)
            invalid[field] = bad
            self.reject(name, invalid)


if __name__ == '__main__':
    unittest.main()
