"""G2-CR1: schema/DEMO CRM, dùng lại G2-17 và G2-24, hoàn toàn offline.

CONTRACT-NGHIEP-VU.md:1012–1075 (sáu bảng), 688–696 (nhóm mốc).
Fallback G2-17 không thay chứng nhận meta-schema khi thiếu jsonschema.
"""

from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))
import test_g2_17 as g17
from kho_tri_thuc.core import goi

CONTRACT_DIR = ROOT / 'src/kho_tri_thuc/modules/crm/contract'
SPEC = ROOT / 'docs/47-core/g1/CONTRACT-NGHIEP-VU.md'
KEY = 'urn:ktt:contract:du_an_dang_ban.v1'
CHUNG = 'urn:ktt:contract:chung.v1#/$defs/'


class DuAnDangBanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = g17._json((CONTRACT_DIR / 'du_an_dang_ban.schema.json').read_text(encoding='utf-8'))
        cls.demo = g17._json((CONTRACT_DIR / 'du_an_dang_ban.demo.json').read_text(encoding='utf-8'))
        cls.schemas = {}
        for name in ('ky_thuat.json', 'manifest.json'):
            cls.schemas.update(g17._json((g17.CONTRACT_DIR / name).read_text(encoding='utf-8')))
        cls.schemas[KEY] = cls.schema
        cls.spec = SPEC.read_text(encoding='utf-8')
        cls.validator = None
        if g17.Draft202012Validator:
            Validator, checker, registry, Resource = goi._bo_schema()
            cls.registry = registry.with_resources(
                (key, Resource.from_contents(schema)) for key, schema in cls.schemas.items())
            cls.validator = Validator({'$ref': KEY}, registry=cls.registry, format_checker=checker)

    def validate(self, value):
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-CR1')):
            if self.validator:
                self.validator.validate(value)
            # Không viết bộ kiểm mới: kiểm cùng mẫu bằng fallback sẵn có G2-17.
            g17._minimal(value, self.schema, self.schema, self.schemas)

    def reject(self, value):
        # Mỗi backend phải độc lập bác mẫu âm.
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-CR1')):
            if self.validator:
                from jsonschema.exceptions import ValidationError
                with self.assertRaises(ValidationError):
                    self.validator.validate(value)
            with self.assertRaises(ValueError):
                g17._minimal(value, self.schema, self.schema, self.schemas)

    @unittest.skipUnless(g17.Draft202012Validator, 'CHUA_KIEM: thiếu jsonschema; fallback không thay meta-schema')
    def test_meta_schema_2020_12(self):
        g17.Draft202012Validator.check_schema(self.schema)
        self.assertEqual(self.schema['$schema'], g17.DRAFT)
        self.assertEqual(self.schema['$id'], KEY)

    def test_demo_dung_nguyen_vi_du_da_duyet(self):
        start = self.spec.index('### 3. `du_an_dang_ban.v1`')
        raw = re.search(r'```json\s*\n(.*?)\n```', self.spec[start:], re.DOTALL)[1]
        self.assertEqual(self.demo, g17._json(raw))
        self.assertIn('DEMO', self.demo['thong_tin']['mo_ta'])
        self.validate(self.demo)

    def test_moi_ref_phan_giai_offline_ke_ca_nhanh_khong_chay(self):
        count = 0
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-CR1')):
            # Kiểm cả tham chiếu bắc cầu trong bundle kỹ thuật.
            for key, schema in self.schemas.items():
                for node in g17._nodes(schema):
                    if '$ref' in node:
                        target, _ = g17._resolve(node['$ref'], schema, self.schemas)
                        self.assertIsInstance(target, dict)
                        if self.validator:
                            self.assertEqual(self.registry.resolver(key).lookup(node['$ref']).contents, target)
                        count += 1
        self.assertGreater(count, 100)

    def test_ref_la_khong_truy_cap_mang(self):
        if not self.validator:
            self.skipTest('CHUA_KIEM: thiếu jsonschema/referencing')
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-CR1')):
            from referencing.exceptions import Unresolvable
            with self.assertRaises(Unresolvable):
                self.registry.resolver(KEY).lookup('https://example.invalid/chua_duyet')

    def test_truong_va_bat_buoc_khop_bang_dac_ta(self):
        # Đọc bảng thật thay vì chỉ so với danh sách trong chính schema.
        def table(first, last):
            rows = []
            for line in self.spec.splitlines()[first - 1:last]:
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if cells and cells[0].startswith('`'):
                    rows.append((cells[0].strip('`'), cells[3]))
            self.assertTrue(rows, (first, last))
            return rows

        shell = self.schemas['urn:ktt:contract:chung.v1']['$defs']['vo_noi_dung']
        self.assertEqual(self.schema['allOf'], [{'$ref': CHUNG + 'vo_noi_dung'}])
        root_rows = table(1012, 1029)
        self.assertEqual(set(self.schema['properties']) | set(shell['properties']), {key for key, _ in root_rows})
        self.assertEqual(set(self.schema['required']) | set(shell['required']), {key for key, req in root_rows if req.startswith('B')})
        for name, first, last in (
            ('gia_thue', 1035, 1037), ('phi', 1043, 1048),
            ('moc_du_an', 1054, 1060), ('tien_do', 1066, 1069),
            ('lo_can', 1070, 1075), ('moc', 688, 696),
        ):
            rows = [(key.rsplit('.', 1)[-1], req) for key, req in table(first, last)]
            node = self.schema['$defs'][name]
            with self.subTest(group=name):
                self.assertEqual(set(node['properties']), {key for key, _ in rows})
                self.assertEqual(set(node['required']), {key for key, req in rows if req.startswith('B')})
                self.assertFalse(node['additionalProperties'])
                for field in node['properties'].values():
                    self.assertIn('description', field)
                    self.assertIn('dòng', field['description'])
        self.assertEqual(set(self.schema['$defs']['thong_tin']['properties']), {'vi_tri', 'mo_ta'})

    def test_thieu_moi_truong_bat_buoc_o_moi_khoi_bi_bac(self):
        # Đi qua tất cả object DEMO, kể cả tiền và từng nhánh mốc.
        def visit(value, path=()):
            if isinstance(value, dict):
                for field in value:
                    yield path, field
                for field, child in value.items():
                    yield from visit(child, path + (field,))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    yield from visit(child, path + (index,))

        optional = {'vi_tri', 'mo_ta', 'co_so_tinh', 'ten_tat', 'ghi_chu'}
        for path, field in visit(self.demo):
            if field in optional:
                continue
            # Giữ các ca bỏ từng trường, kể cả bộ tham chiếu mốc riêng.
            value = deepcopy(self.demo)
            target = value
            for part in path:
                target = target[part]
            target.pop(field)
            with self.subTest(path=path, field=field):
                self.reject(value)

    def test_moc_rieng_thieu_ca_bo_tham_chieu_bi_bac(self):
        value = deepcopy(self.demo)
        for field in ('moc_du_an_id', 'lan_moc', 'ngay_du_kien', 'ngay_thuc_te'):
            value['tien_do'][1]['moc'].pop(field)
        self.reject(value)

    def test_moc_rieng_chi_con_ngay_van_buoc_du_bo(self):
        # Ngày mốc riêng cũng là dấu hiệu đã khai, kể cả ngày thực tế null.
        for retained in ('ngay_du_kien', 'ngay_thuc_te'):
            value = deepcopy(self.demo)
            source = value['tien_do'][1]['moc']
            value['tien_do'][0]['moc'][retained] = source[retained]
            with self.subTest(retained=retained):
                self.reject(value)

    def test_moc_rieng_nullable_dung_dac_ta(self):
        value = deepcopy(self.demo)
        self.validate(value)  # Ngày thực tế null vẫn phải có trường.
        value['tien_do'][1]['moc']['ngay_thuc_te'] = '2026-12-02'
        self.validate(value)
        for field in ('moc_du_an_id', 'lan_moc', 'ngay_du_kien'):
            value = deepcopy(self.demo)
            value['tien_do'][1]['moc'][field] = None
            with self.subTest(field=field):
                self.reject(value)

    def test_cac_nhanh_moc_thieu_dong_thoi_truong_dieu_kien_bi_bac(self):
        for index, fields in ((0, ('su_kien', 'so_ngay_sau_moc')), (2, ('ngay',))):
            value = deepcopy(self.demo)
            for field in fields:
                value['tien_do'][index]['moc'].pop(field)
            with self.subTest(index=index):
                self.reject(value)

    def test_nguon_tep_rong_trung_null_sai_uuid_bi_bac(self):
        for invalid in ([], self.demo['nguon_tep_ids'] * 2, None, ['DEMO'], [None]):
            with self.subTest(value=invalid):
                self.reject({**self.demo, 'nguon_tep_ids': invalid})

    def test_sai_don_vi_o_tung_truong_tien_bi_bac(self):
        for group, field in (('gia_thue', 'don_gia_niem_yet'), ('gia_thue', 'gia_dat_tru_m2'), ('phi', 'muc')):
            for unit in ('EUR', 'vnd', 'M2', '%', None):
                value = deepcopy(self.demo)
                target = value[group][0] if group == 'phi' else value[group]
                target[field]['don_vi_tien'] = unit
                with self.subTest(group=group, field=field, unit=unit):
                    self.reject(value)
        value = deepcopy(self.demo)
        value['phi'][0]['don_vi_tinh'] = 'M2'
        self.reject(value)

    def test_catalog_thue_va_phi_giu_dung_nguon(self):
        for rate in ('10', '8', '5', '0', 'KCT', 'KKKNT'):
            value = deepcopy(self.demo)
            value['gia_thue']['thue_suat'] = rate
            self.validate(value)
        for rate in (10, '7', 'KHONG_THUE', None):
            value = deepcopy(self.demo)
            value['gia_thue']['thue_suat'] = rate
            self.reject(value)
        for field in ('loai', 'co_so_gia_tri', 'don_vi_tinh'):
            value = deepcopy(self.demo)
            value['phi'][0][field] = 'CHUA_DUYET'
            self.reject(value)

    def test_nullable_va_cac_khoi_duoc_rong(self):
        value = deepcopy(self.demo)
        value.update(thong_tin={}, phi=[], moc=[], tien_do=[], lo_can=[])
        value['gia_thue']['don_gia_niem_yet'] = None
        self.validate(value)
        for field in ('du_an_id', 'gia_dat_tru_m2', 'thue_suat'):
            value = deepcopy(self.demo)
            target = value if field == 'du_an_id' else value['gia_thue']
            target[field] = None
            self.reject(value)

    def test_decimal_khong_ep_so_va_scale_tien_chung(self):
        for invalid in (100, '1e2', '01', '1.0000001'):
            value = deepcopy(self.demo)
            value['gia_thue']['don_gia_niem_yet']['gia_tri'] = invalid
            self.reject(value)
        value = deepcopy(self.demo)
        value['gia_thue']['don_gia_niem_yet'] = {'gia_tri': '1.123456', 'don_vi_tien': 'USD'}
        self.validate(value)

    def test_dien_tich_duong_va_dinh_dang_ngay_uuid(self):
        for invalid in ('0', '0.000', '-1', '1e2', 100):
            value = deepcopy(self.demo)
            value['lo_can'][0]['dien_tich'] = invalid
            self.reject(value)
        value = deepcopy(self.demo)
        value['lo_can'][0]['dien_tich'] = '0.000001'
        self.validate(value)
        for field, invalid in (('id', 'DEMO'), ('ngay_du_kien', '2026-02-30'), ('ngay_thuc_te', '01/12/2026')):
            value = deepcopy(self.demo)
            value['moc'][0][field] = invalid
            self.reject(value)

    def test_integer_duong_boolean_va_phien_ban(self):
        for field, invalid in (('revision', 0), ('so_phien_ban', True), ('so_phien_ban', 1.5), ('dang_ban', 1), ('phien_ban', '2.0.0'), ('contract', 'bao_gia.v1'), ('ma_bam', 'DEMO')):
            self.reject({**self.demo, field: invalid})
        for group in ('moc', 'tien_do', 'lo_can'):
            value = deepcopy(self.demo)
            value[group][0]['lan'] = 0
            self.reject(value)

    def test_moc_su_kien_doi_lech_khong_am(self):
        value = deepcopy(self.demo)
        value['tien_do'][0]['moc']['so_ngay_sau_moc'] = -1
        self.reject(value)
        value['tien_do'][0]['moc']['so_ngay_sau_moc'] = 30
        self.validate(value)

    def test_khong_them_truong_nghiep_vu_ngoai_bang(self):
        for group in (None, 'thong_tin', 'gia_thue', 'phi', 'moc', 'tien_do', 'lo_can'):
            value = deepcopy(self.demo)
            target = value if group is None else value[group]
            if isinstance(target, list):
                target = target[0]
            target['truong_chua_duyet'] = 'DEMO'
            self.reject(value)
        for field in ('so_tien', 'gia_tri_nhap', 'giai_doan_g7'):
            value = deepcopy(self.demo)
            value['tien_do'][0][field] = 'DEMO'
            self.reject(value)

    def test_demo_tong_phan_tram_grain_va_tham_chieu_moc(self):
        # Chỉ đối chiếu DEMO, không phải validator runtime mới.
        self.assertEqual(sum((Decimal(row['ty_le']) for row in self.demo['tien_do']), Decimal(0)), Decimal(100))
        for group, keys in (('moc', ('id', 'lan')), ('tien_do', ('lan',)), ('lo_can', ('id', 'lan'))):
            grain = [tuple(row[key] for key in keys) for row in self.demo[group]]
            self.assertEqual(len(grain), len(set(grain)))
        source = self.demo['moc'][0]
        ref = self.demo['tien_do'][1]['moc']
        self.assertEqual((ref['moc_du_an_id'], ref['lan_moc']), (source['id'], source['lan']))
        for field in ('ngay_du_kien', 'ngay_thuc_te'):
            self.assertEqual(ref[field], source[field])

    def test_giu_cac_diem_cho_anh_khong_kich_hoat(self):
        self.assertIn('chờ Anh', self.schema['description'])
        self.assertIn('nhap', self.schema['$comment'])
        self.assertIn('Cần lead', self.schema['$comment'])
        for field in ('phien_ban_du_an_id', 'ma_bam'):
            self.assertIn('chờ Anh', self.schema['properties'][field]['description'])


if __name__ == '__main__':
    unittest.main()
