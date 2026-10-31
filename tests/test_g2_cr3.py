"""G2-CR3: contract mốc theo CD-041 mục 2, DEMO thuần/mock, offline.

Vỏ mô tả tham số phát; chỉ tham_chieu đi vào G2-15. Không đăng ký hay
kích hoạt contract, không cần PostgreSQL, không tự sinh UUID lịch sử thật.
"""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))
import test_g2_17 as g17
from kho_tri_thuc.core import goi, phien, su_kien as bus

CONTRACT_DIR = ROOT / 'src/kho_tri_thuc/modules/crm/contract'
KEY = 'urn:ktt:contract:moc_da_xay_ra.v1'


class MocDaXayRaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = g17._json((CONTRACT_DIR / 'moc_da_xay_ra.schema.json').read_text(encoding='utf-8'))
        cls.demo = g17._json((CONTRACT_DIR / 'moc_da_xay_ra.demo.json').read_text(encoding='utf-8'))
        cls.schemas = {KEY: cls.schema}
        for name in ('ky_thuat.json', 'manifest.json'):
            cls.schemas.update(g17._json((g17.CONTRACT_DIR / name).read_text(encoding='utf-8')))
        cls.validator = None
        if g17.Draft202012Validator:
            Validator, checker, registry, Resource = goi._bo_schema()
            cls.registry = registry.with_resources((key, Resource.from_contents(schema)) for key, schema in cls.schemas.items())
            cls.validator = Validator({'$ref': KEY}, registry=cls.registry, format_checker=checker)

    def validate(self, value):
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-CR3')):
            if self.validator:
                self.validator.validate(value)
            g17._minimal(value, self.schema, self.schema, self.schemas)

    def reject(self, value):
        # Hai backend phải bác độc lập; fallback không thay chứng nhận meta-schema.
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-CR3')):
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

    def test_demo_lan_dau_va_dieu_chinh_ghim_dung_lich_su(self):
        self.assertEqual(len(self.demo), 2)
        first, adjusted = self.demo
        self.assertEqual([row['loai'] for row in self.demo], ['moc_da_xay_ra', 'moc_da_xay_ra.dieu_chinh'])
        for row in self.demo:
            self.validate(row)
            refs = row['tham_chieu']
            self.assertEqual(row['khoa_dedupe'], row['loai'] + ':' + refs['lich_su_moc_id'])
            self.assertNotEqual(refs['moc_id'], refs['lich_su_moc_id'])
        self.assertEqual(first['tham_chieu']['moc_id'], adjusted['tham_chieu']['moc_id'])
        self.assertEqual(first['tham_chieu']['lich_su_moc_id'], adjusted['tham_chieu']['lich_su_moc_cu_id'])
        self.assertNotEqual(adjusted['tham_chieu']['lich_su_moc_id'], adjusted['tham_chieu']['lich_su_moc_cu_id'])
        self.assertNotEqual(first['khoa_dedupe'], adjusted['khoa_dedupe'])

    def test_moi_ref_offline_ke_ca_nhanh_khong_chay(self):
        count = 0
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-CR3')):
            for key, schema in self.schemas.items():
                for node in g17._nodes(schema):
                    if '$ref' in node:
                        target, _ = g17._resolve(node['$ref'], schema, self.schemas)
                        self.assertIsInstance(target, dict)
                        if self.validator:
                            self.assertEqual(self.registry.resolver(key).lookup(node['$ref']).contents, target)
                        count += 1
        self.assertGreater(count, 100)
        for route in self.schema['x-bus']:
            self.assertIn(route['payload'], {'#/$defs/phat_lan_dau', '#/$defs/dieu_chinh'})
            g17._resolve(route['payload'], self.schema, self.schemas)

    def test_ref_la_khong_truy_cap_mang(self):
        if not self.validator:
            self.skipTest('CHUA_KIEM: thiếu jsonschema/referencing')
        from referencing.exceptions import Unresolvable
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-CR3')):
            with self.assertRaises(Unresolvable):
                self.registry.resolver(KEY).lookup('https://example.invalid/chua_duyet')

    def test_ben_nhan_dung_cd041_khong_suy_quyen_tu_khai_bao(self):
        spec = (ROOT / 'docs/47-core/g1/CONTRACT-NGHIEP-VU.md').read_text(encoding='utf-8')
        section = spec.split('### 5.3. `moc_da_xay_ra.v1`', 1)[1].split('### 5.4.', 1)[0]
        self.assertIn('(c) module nhận: CRM, M3, M10;', section)
        self.assertEqual(self.schema['x-ben-phat'], 'CRM')
        self.assertEqual(self.schema['x-ben-nhan'], ['CRM', 'M3', 'M10'])

    def test_payload_khong_cho_du_lieu_ngoai_tham_chieu_ke_ca_uuid_la(self):
        for demo in self.demo:
            for field, extra in (
                ('lan', 2), ('ngay_thuc_te', '2026-10-31'), ('ngay_thuc_te', None),
                ('so_tien', '1000000'), ('ten', 'DEMO mốc'), ('loai', 'DIEU_CHINH'),
                ('phien_ban', 1), ('khoa_dedupe', 'DEMO'), ('tep', {'id': demo['phap_nhan_id']}),
                ('nguon_id', demo['phap_nhan_id']), ('nguon_ids', [demo['phap_nhan_id']]),
            ):
                value = deepcopy(demo)
                value['tham_chieu'][field] = extra
                with self.subTest(loai=demo['loai'], field=field):
                    self.reject(value)

    def test_moi_truong_bat_buoc_va_uuid_tham_chieu(self):
        for index, demo in enumerate(self.demo):
            for field in self.schema['required']:
                value = deepcopy(demo)
                value.pop(field)
                with self.subTest(index=index, missing=field):
                    self.reject(value)
            for field in demo['tham_chieu']:
                value = deepcopy(demo)
                value['tham_chieu'].pop(field)
                with self.subTest(index=index, missing_ref=field):
                    self.reject(value)
                for invalid in (None, 2, 'DEMO', '2026-10-31', [], {}, True):
                    value = deepcopy(demo)
                    value['tham_chieu'][field] = invalid
                    with self.subTest(index=index, field=field, invalid=invalid):
                        self.reject(value)

    def test_dieu_chinh_bat_buoc_lan_ghi_cu_lan_dau_khong_co(self):
        value = deepcopy(self.demo[1])
        value['tham_chieu'].pop('lich_su_moc_cu_id')
        self.reject(value)
        value = deepcopy(self.demo[0])
        value['tham_chieu']['lich_su_moc_cu_id'] = self.demo[1]['tham_chieu']['lich_su_moc_cu_id']
        self.reject(value)

    def test_loai_phien_ban_ben_phat_va_khoa_sai_bi_bac(self):
        for demo in self.demo:
            for field, invalid in (
                ('loai', 'moc_du_kien'), ('loai', 'DIEU_CHINH'),
                ('phien_ban', '1.0.0'), ('phien_ban', True), ('phien_ban', 2),
                ('ben_phat', 'M3'), ('phap_nhan_id', 'DEMO'),
                ('khoa_dedupe', 'DEMO:moc_da_xay_ra:MOC001:lan1'),
                ('khoa_dedupe', demo['loai'] + ':DEMO'), ('khoa_dedupe', ' '),
                ('khoa_dedupe', 'moc_du_kien:' + demo['tham_chieu']['lich_su_moc_id']),
                ('ngay_thuc_te', '2026-10-31'), ('contract', 'moc_da_xay_ra.v1'),
            ):
                with self.subTest(loai=demo['loai'], field=field, invalid=invalid):
                    self.reject({**demo, field: invalid})
            opposite = self.demo[1] if demo['loai'] == 'moc_da_xay_ra' else self.demo[0]
            self.reject({**demo, 'khoa_dedupe': opposite['khoa_dedupe']})

    def test_payload_dang_ky_dung_subset_g2_15_khong_ref_dieu_kien(self):
        # G2-15 SQL từ chối keyword ngoài subset; kiểm cả định nghĩa độc lập
        # để không vô tình đăng ký vỏ hoặc oneOf/$ref vào bus UUID-only.
        self.assertEqual(len(self.schema['x-bus']), 2)
        self.assertEqual({route['loai'] for route in self.schema['x-bus']}, {row['loai'] for row in self.demo})
        for route, demo in zip(self.schema['x-bus'], self.demo):
            self.assertEqual(route['phien_ban'], 1)
            self.assertEqual(route['loai'], demo['loai'])
            payload, _ = g17._resolve(route['payload'], self.schema, self.schemas)
            self.assertEqual(set(payload), {'type', 'additionalProperties', 'required', 'properties'})
            self.assertEqual(payload['type'], 'object')
            self.assertFalse(payload['additionalProperties'])
            self.assertEqual(set(payload['required']), set(payload['properties']))
            for name, field in payload['properties'].items():
                self.assertRegex(name, r'^[a-z][a-z0-9_]*_id$')
                self.assertLessEqual(set(field), {'type', 'format', 'description'})
                self.assertEqual((field['type'], field['format']), ('string', 'uuid'))
            with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-CR3')):
                g17._minimal(demo['tham_chieu'], payload, payload, self.schemas)
                if self.validator:
                    g17.Draft202012Validator(payload, format_checker=g17.FormatChecker()).validate(demo['tham_chieu'])

    def test_demo_goi_bus_that_bang_mock_ket_noi_chi_truyen_tham_chieu(self):
        for demo in self.demo:
            conn = MagicMock()
            conn.info.transaction_status = 2
            event_id = UUID('90000000-0000-4000-8000-000000000099')
            conn.execute.return_value.fetchone.return_value = (event_id,)
            with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-CR3')):
                actual = bus.phat(conn, loai=demo['loai'], phien_ban=demo['phien_ban'],
                                  tham_chieu=demo['tham_chieu'], khoa=demo['khoa_dedupe'],
                                  ma=phien.MaBiMat('DEMO_G2_CR3'), module=demo['ben_phat'].lower(),
                                  phap_nhan_id=UUID(demo['phap_nhan_id']), hanh_dong='CRM:MOC:SUA')
            self.assertEqual(actual, event_id)
            params = conn.execute.call_args.args[1]
            self.assertEqual(params[4:7], (demo['loai'], 1, demo['khoa_dedupe']))
            self.assertEqual(json.loads(params[7]), demo['tham_chieu'])
            for name in ('connect', 'transaction', 'commit', 'rollback'):
                getattr(conn, name).assert_not_called()


if __name__ == '__main__':
    unittest.main()
