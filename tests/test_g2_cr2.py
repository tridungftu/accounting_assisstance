"""G2-CR2: schema báo giá và minh chứng số học CD-038 1A/2B, offline.

Bộ kiểm Decimal chỉ dùng trong test, không phải mã nghiệp vụ/runtime mới.
Schema dùng lại các nhóm CR1, G2-17 và registry G2-24; không tự chốt catalog.
"""

from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP, localcontext
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
KEY = 'urn:ktt:contract:bao_gia.v1'
CR1 = 'urn:ktt:contract:du_an_dang_ban.v1'
CHUNG = 'urn:ktt:contract:chung.v1#/$defs/'


def _kiem_bat_bien(value):
    """Kiểm lịch đủ căn cứ trước in, sau kiểm schema; không suy ngược ô gốc.

    N/V là tổng đã có căn cứ, không tự tính V=N*thuế suất: có đất trừ/miễn thuế.
    Dùng đúng công thức phân bổ B,V trước dồn VAT tại NV-CRM §1 dòng 716.
    """
    def require(ok, message):
        if not ok:
            raise ValueError(message)

    with localcontext() as context:
        # Không mất chính xác khi N tối đa 18 chữ số và tỷ lệ có nhiều số lẻ.
        context.prec = max(80, len(str(value)) * 2)
        rows = sorted(value['lich_thanh_toan'], key=lambda row: row['lan'])
        require(bool(rows), 'Lịch chưa đủ trước in')
        for field in ('lan', 'nghia_vu_id'):
            require(len({row[field] for row in rows}) == len(rows), 'Trùng ' + field)
        require(all(row['loai_khoan'] == 'GIA_BAN' for row in rows), 'Phí ngoài lịch giá bán')
        non_deposits = [i for i, row in enumerate(rows) if not row['la_dat_coc']]
        require(bool(non_deposits), 'Lịch toàn cọc')
        price = value['gia_thue']
        require(all(price[field] is not None for field in ('tong_truoc_vat', 'tong_vat', 'tong_gom_vat')), 'Tổng chưa xác định')
        unit = price['tong_truoc_vat']['don_vi_tien']
        require(unit in ('VND', 'USD'), 'Đơn vị CRM')
        quantum = Decimal('1') if unit == 'VND' else Decimal('0.01')

        def money(item):
            require(item['don_vi_tien'] == unit, 'Không cộng khác tiền tệ')
            amount = Decimal(item['gia_tri'])
            require(amount.is_finite() and amount >= 0, 'Tiền không âm/hữu hạn')
            require(amount == amount.quantize(quantum), 'Sai thang tiền kết quả')
            return amount

        n, v, g = (money(price[field]) for field in ('tong_truoc_vat', 'tong_vat', 'tong_gom_vat'))
        require(n + v == g, 'N+V=G')
        percentages = [Decimal(row['ty_le']) for row in rows]
        require(all(p.is_finite() and p >= 0 for p in percentages), 'Tỷ lệ không âm/hữu hạn')
        require(sum(percentages) == Decimal(100), 'Σ%=100')

        def allocate(total):
            result = [(total * p / 100).quantize(quantum, rounding=ROUND_HALF_UP) for p in percentages[:-1]]
            result.append(total - sum(result))
            require(all(amount >= 0 for amount in result), 'Phần dư ngoài miền')
            return result

        bases, vats = allocate(n), allocate(v)
        expected_t = [Decimal(0) for _ in rows]
        for i, row in enumerate(rows):
            target = i
            if row['la_dat_coc']:
                after = [j for j in non_deposits if j > i]
                target = after[0] if after else max(j for j in non_deposits if j < i)
            expected_t[target] += vats[i]
        actual_t, actual_a = [], []
        for i, row in enumerate(rows):
            t, a = money(row['trong_do_vat']), money(row['gia_tri_gom_vat'])
            require(t <= a, 'T≤A')
            require(not row['la_dat_coc'] or t == 0, 'T cọc=0')
            require(t == expected_t[i], 'Sai đích dồn VAT 2B')
            require(a == bases[i] + t, 'A=B+T')
            actual_t.append(t)
            actual_a.append(a)
        require(sum(actual_t) == v, 'ΣT=V')
        require(sum(actual_a) == g, 'ΣA=G')
        require(sum(a - t for a, t in zip(actual_a, actual_t)) == n, 'Σ(A−T)=N')


class BaoGiaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = g17._json((CONTRACT_DIR / 'bao_gia.schema.json').read_text(encoding='utf-8'))
        cls.demo = g17._json((CONTRACT_DIR / 'bao_gia.demo.json').read_text(encoding='utf-8'))
        cls.spec = (ROOT / 'docs/47-core/g1/CONTRACT-NGHIEP-VU.md').read_text(encoding='utf-8')
        cls.schemas = {KEY: cls.schema, CR1: g17._json((CONTRACT_DIR / 'du_an_dang_ban.schema.json').read_text(encoding='utf-8'))}
        for name in ('ky_thuat.json', 'manifest.json'):
            cls.schemas.update(g17._json((g17.CONTRACT_DIR / name).read_text(encoding='utf-8')))
        cls.validator = None
        if g17.Draft202012Validator:
            Validator, checker, registry, Resource = goi._bo_schema()
            cls.registry = registry.with_resources((key, Resource.from_contents(schema)) for key, schema in cls.schemas.items())
            cls.validator = Validator({'$ref': KEY}, registry=cls.registry, format_checker=checker)

    def validate(self, value):
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-CR2')):
            if self.validator:
                self.validator.validate(value)
            g17._minimal(value, self.schema, self.schema, self.schemas)

    def reject(self, value):
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-CR2')):
            if self.validator:
                from jsonschema.exceptions import ValidationError
                with self.assertRaises(ValidationError):
                    self.validator.validate(value)
            with self.assertRaises(ValueError):
                g17._minimal(value, self.schema, self.schema, self.schemas)

    def case(self, percentages, deposits, amounts, vats, n='1000000000', v='100000000', g='1100000000', unit='VND'):
        """Fixture từ kết quả tính tay, không gọi lại bộ phân bổ để sinh đáp án."""
        value = deepcopy(self.demo)
        for field, amount in zip(('tong_truoc_vat', 'tong_vat', 'tong_gom_vat'), (n, v, g)):
            value['gia_thue'][field] = {'gia_tri': amount, 'don_vi_tien': unit}
        value['lich_thanh_toan'] = []
        for i, (p, deposit, amount, vat) in enumerate(zip(percentages, deposits, amounts, vats), 1):
            row = deepcopy(self.demo['lich_thanh_toan'][0])
            row.update(lan=i, nghia_vu_id=f'20000000-0000-4000-8000-{i:012d}', ty_le=p, la_dat_coc=deposit)
            row['gia_tri_nhap'] = {'kieu': 'so', 'gia_tri': p, 'don_vi': '%'}
            row['gia_tri_gom_vat'] = {'gia_tri': amount, 'don_vi_tien': unit}
            row['trong_do_vat'] = {'gia_tri': vat, 'don_vi_tien': unit}
            value['lich_thanh_toan'].append(row)
        return value

    @unittest.skipUnless(g17.Draft202012Validator, 'CHUA_KIEM: thiếu jsonschema; fallback không thay meta-schema')
    def test_meta_schema_2020_12(self):
        g17.Draft202012Validator.check_schema(self.schema)
        self.assertEqual(self.schema['$schema'], g17.DRAFT)
        self.assertEqual(self.schema['$id'], KEY)

    def test_demo_hop_schema_va_bat_bien_co_hai_coc_lien_va_coc_cuoi(self):
        self.validate(self.demo)
        _kiem_bat_bien(self.demo)
        self.assertEqual([row['la_dat_coc'] for row in self.demo['lich_thanh_toan']], [True, True, False, True])
        self.assertIn('DEMO', self.demo['ghi_chu'])
        self.assertTrue(self.demo['phi'])

    def test_vi_du_goc_dac_ta_va_ba_trich_doan_cd038(self):
        section = self.spec.split('### 2. `bao_gia.v1`', 1)[1]
        original = g17._json(re.search(r'```json\s*\n(.*?)\n```', section, re.DOTALL)[1])
        self.validate(original)
        _kiem_bat_bien(original)
        examples = self.spec.split('#### Ba ví dụ JSON DEMO theo CD-038 câu 2B', 1)[1].split('#### Ví dụ JSON DEMO', 1)[0]
        snippets = re.findall(r'```json\s*\n(.*?)\n```', examples, re.DOTALL)
        self.assertEqual(len(snippets), 3)
        for raw in snippets:
            fields_rows = g17._json(raw)['lich_thanh_toan']
            value = deepcopy(self.demo)
            value['lich_thanh_toan'] = value['lich_thanh_toan'][:len(fields_rows)]
            for row, fields in zip(value['lich_thanh_toan'], fields_rows):
                row.update(fields)
            self.validate(value)
            _kiem_bat_bien(value)

    def test_moi_ref_phan_giai_offline_ca_nhanh_khong_chay(self):
        count = 0
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-CR2')):
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
        from referencing.exceptions import Unresolvable
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-CR2')):
            with self.assertRaises(Unresolvable):
                self.registry.resolver(KEY).lookup('https://example.invalid/chua_duyet')

    def test_truong_khop_dac_ta_va_khong_cong_bo_dich_hieu_luc(self):
        def fields(start, end):
            text = self.spec.split(start, 1)[1].split(end, 1)[0]
            return {match[1]: match[2] for match in re.finditer(r'^\| `([^`]+)` \|.*? \| ([^|]+) \| [^|]* \| [^|]* \|$', text, re.MULTILINE)}

        root = fields('### 2. `bao_gia.v1`', '**Quy tắc:**')
        self.assertEqual(set(self.schema['properties']), set(root))
        shell = self.schemas['urn:ktt:contract:chung.v1']['$defs']['vo_noi_dung']
        self.assertEqual(self.schema['allOf'], [{'$ref': CHUNG + 'vo_noi_dung'}])
        self.assertEqual(set(self.schema['required']) | set(shell['required']), {name for name, req in root.items() if req.strip().startswith('B')})
        for name, start, end in (
            ('gia_thue', '**`GiaCrm`:**', '`thue_suat` giữ phân biệt'),
            ('dong_lich', '**`DongLichCrm`:**', '**Các trường trong `moc`:**'),
        ):
            expected = set(fields(start, end)) - {'module_nghia_vu', 'loai_nghia_vu', 'khoa_nghia_vu'}
            self.assertEqual(set(self.schema['$defs'][name]['properties']), expected)
        for node in (self.schema, self.schema['$defs']['gia_thue'], self.schema['$defs']['dong_lich'], self.schema['$defs']['ty_gia']):
            for field in node['properties'].values():
                self.assertIn('description', field)
                self.assertIn('dòng', field['description'])
        for field in ('module_nghia_vu', 'loai_nghia_vu', 'khoa_nghia_vu', 'dong_id', 'lich_thu_id'):
            value = deepcopy(self.demo)
            value['lich_thanh_toan'][0][field] = 'DEMO'
            self.reject(value)

    def test_coc_cuoi_hai_coc_lien_coc_xen_giua_va_mot_khong_coc(self):
        cases = (
            (['30', '50', '20'], [False, False, True], ['330000000', '570000000', '200000000'], ['30000000', '70000000', '0']),
            (['20', '30', '50'], [True, True, False], ['200000000', '300000000', '600000000'], ['0', '0', '100000000']),
            (['30', '20', '50'], [False, True, False], ['330000000', '200000000', '570000000'], ['30000000', '0', '70000000']),
            (['100'], [False], ['1100000000'], ['100000000']),
        )
        for args in cases:
            with self.subTest(deposits=args[1]):
                value = self.case(*args)
                self.validate(value)
                _kiem_bat_bien(value)

    def test_dung_khong_coc_gan_nhat_theo_lan_ca_khi_mang_dao(self):
        value = self.case(['10', '20', '30', '20', '20'], [False, True, False, False, True],
                          ['110000000', '200000000', '350000000', '240000000', '200000000'],
                          ['10000000', '0', '50000000', '40000000', '0'])
        value['lich_thanh_toan'].reverse()
        self.validate(value)
        _kiem_bat_bien(value)
        # Chuyển nhầm VAT cọc giữa sang phía trước: vẫn bảo toàn mọi tổng.
        value['lich_thanh_toan'][4]['trong_do_vat']['gia_tri'] = '30000000'
        value['lich_thanh_toan'][4]['gia_tri_gom_vat']['gia_tri'] = '130000000'
        value['lich_thanh_toan'][2]['trong_do_vat']['gia_tri'] = '30000000'
        value['lich_thanh_toan'][2]['gia_tri_gom_vat']['gia_tri'] = '330000000'
        self.validate(value)
        with self.assertRaisesRegex(ValueError, 'đích dồn VAT'):
            _kiem_bat_bien(value)

    def test_lam_tron_half_up_du_cuoi_truoc_don_vat_vnd_usd(self):
        for unit, n, v, g, amounts, vats in (
            ('VND', '105', '15', '120', ['13', '24', '83'], ['2', '13', '0']),
            ('USD', '1.05', '0.15', '1.20', ['0.13', '0.24', '0.83'], ['0.02', '0.13', '0']),
        ):
            with self.subTest(unit=unit):
                value = self.case(['10', '10', '80'], [False, False, True], amounts, vats, n, v, g, unit)
                self.validate(value)
                _kiem_bat_bien(value)
                # V cuối phân bổ là 11/0.11, khác làm tròn độc lập 12/0.12.
                delta = Decimal('1') if unit == 'VND' else Decimal('0.01')
                value['lich_thanh_toan'][1]['trong_do_vat']['gia_tri'] = str(Decimal(vats[1]) + delta)
                with self.assertRaises(ValueError):
                    _kiem_bat_bien(value)

    def test_sai_tong_phan_tram_bi_do_du_schema_dat(self):
        value = deepcopy(self.demo)
        value['lich_thanh_toan'][-1]['ty_le'] = '19.9999999999999999999999999999'
        self.validate(value)
        with self.assertRaisesRegex(ValueError, 'Σ%=100'):
            _kiem_bat_bien(value)

    def test_toan_coc_ke_ca_mot_coc_bi_do(self):
        for count in (1, 4):
            value = deepcopy(self.demo)
            value['lich_thanh_toan'] = value['lich_thanh_toan'][:count]
            for row in value['lich_thanh_toan']:
                row['la_dat_coc'] = True
            self.reject(value)
            with self.assertRaisesRegex(ValueError, 'toàn cọc'):
                _kiem_bat_bien(value)

    def test_sai_tong_tien_vat_coc_va_phan_bo_bi_do(self):
        for group, field, amount in (
            ('gia_thue', 'tong_gom_vat', '1100000001'),
            ('lich_thanh_toan', 'gia_tri_gom_vat', '100000001'),
            ('lich_thanh_toan', 'trong_do_vat', '1'),
            ('lich_thanh_toan', 'trong_do_vat', '100000001'),
        ):
            value = deepcopy(self.demo)
            target = value['gia_thue'] if group == 'gia_thue' else value['lich_thanh_toan'][0]
            target[field]['gia_tri'] = amount
            self.validate(value)
            with self.subTest(group=group, field=field, amount=amount), self.assertRaises(ValueError):
                _kiem_bat_bien(value)

    def test_phi_rieng_khong_doi_tong_va_khong_duoc_chen_vao_lich(self):
        value = deepcopy(self.demo)
        value['phi'][0]['muc']['gia_tri'] = '999999999'
        self.validate(value)
        _kiem_bat_bien(value)
        value['phi'] = []
        self.validate(value)
        _kiem_bat_bien(value)
        value['lich_thanh_toan'][0]['loai_khoan'] = 'PHI'
        self.reject(value)
        with self.assertRaisesRegex(ValueError, 'Phí ngoài lịch'):
            _kiem_bat_bien(value)

    def test_nguon_tep_ids_bat_buoc_khong_rong_trung_null_sai_uuid(self):
        for invalid in ([], None, [None], ['DEMO'], self.demo['nguon_tep_ids'] * 2):
            with self.subTest(invalid=invalid):
                self.reject({**self.demo, 'nguon_tep_ids': invalid})
        value = deepcopy(self.demo)
        value.pop('nguon_tep_ids')
        self.reject(value)

    def test_moi_truong_bat_buoc_o_cac_khoi(self):
        for path, schema in (((), self.schema), (('gia_thue',), self.schema['$defs']['gia_thue']),
                             (('lich_thanh_toan', 0), self.schema['$defs']['dong_lich'])):
            for field in schema['required']:
                value = deepcopy(self.demo)
                target = value
                for part in path:
                    target = target[part]
                target.pop(field)
                with self.subTest(path=path, field=field):
                    self.reject(value)

    def test_dieu_kien_ghim_phien_ban_va_moc(self):
        for field in ('phien_ban_du_an_id', 'ma_bam_du_an'):
            value = deepcopy(self.demo)
            value.pop(field)
            self.reject(value)
            value['nguon_lich'] = 'KHACH'
            self.reject(value)
        for field in ('su_kien', 'so_ngay_sau_moc', 'lan_moc', 'ngay_du_kien', 'ngay_thuc_te'):
            value = deepcopy(self.demo)
            value['lich_thanh_toan'][2]['moc'].pop(field)
            self.reject(value)
        value = deepcopy(self.demo)
        value['lich_thanh_toan'][0]['moc'].pop('ngay')
        self.reject(value)

    def test_nullable_lich_rong_nhap_khong_tu_coi_la_du_dieu_kien_in(self):
        value = deepcopy(self.demo)
        value.update(doi_tuong_id=None, du_an_id=None, nguon_lich='KHACH', phi=[], lich_thanh_toan=[])
        for field in ('so_bao_gia', 'lo_can_id', 'phien_ban_du_an_id', 'ma_bam_du_an'):
            value.pop(field)
        for field in ('tong_truoc_vat', 'tong_vat', 'tong_gom_vat'):
            value['gia_thue'][field] = None
        self.validate(value)
        with self.assertRaises(ValueError):
            _kiem_bat_bien(value)
        value['lich_thanh_toan'] = deepcopy(self.demo['lich_thanh_toan'])
        self.validate(value)
        with self.assertRaisesRegex(ValueError, 'chưa xác định'):
            _kiem_bat_bien(value)

    def test_catalog_da_chot_va_gia_tri_nhap_chi_phan_tram_hoac_tien(self):
        for rate in ('10', '8', '5', '0', 'KCT', 'KKKNT'):
            value = deepcopy(self.demo)
            value['gia_thue']['thue_suat'] = rate
            self.validate(value)
        for field, invalid in (('thue_suat', 10), ('thue_suat', '7'), ('co_so_thue', 'CHUA_RO')):
            value = deepcopy(self.demo)
            value['gia_thue'][field] = invalid
            self.reject(value)
        for invalid in ({'kieu': 'so', 'gia_tri': '10', 'don_vi': 'M2'},
                        {'kieu': 'so', 'gia_tri': '-1', 'don_vi': '%'},
                        {'kieu': 'tien', 'gia_tri': '-1', 'don_vi_tien': 'VND'},
                        {'kieu': 'tien', 'gia_tri': '10', 'don_vi_tien': 'EUR'},
                        {'kieu': 'van_ban', 'gia_tri': 'DEMO'}, {'kieu': 'chua_ro', 'ly_do': 'DEMO'}):
            value = deepcopy(self.demo)
            value['lich_thanh_toan'][0]['gia_tri_nhap'] = invalid
            self.reject(value)

    def test_tien_decimal_don_vi_thang_va_khong_am(self):
        for invalid in (100, '1e2', '01', '1.0000001', '-1'):
            value = deepcopy(self.demo)
            value['lich_thanh_toan'][0]['trong_do_vat']['gia_tri'] = invalid
            self.reject(value)
        for invalid in ('EUR', 'vnd', None):
            value = deepcopy(self.demo)
            value['gia_thue']['tong_vat']['don_vi_tien'] = invalid
            self.reject(value)
        value = deepcopy(self.demo)
        value['lich_thanh_toan'][0]['gia_tri_gom_vat']['don_vi_tien'] = 'USD'
        self.validate(value)
        with self.assertRaisesRegex(ValueError, 'khác tiền tệ'):
            _kiem_bat_bien(value)
        value = deepcopy(self.demo)
        value['lich_thanh_toan'][0]['gia_tri_gom_vat']['gia_tri'] = '100000000.1'
        self.reject(value)
        with self.assertRaisesRegex(ValueError, 'thang tiền'):
            _kiem_bat_bien(value)
        value['lich_thanh_toan'][0]['gia_tri_gom_vat'] = {'gia_tri': '1.001', 'don_vi_tien': 'USD'}
        self.reject(value)
        # Tiền nguồn vẫn giữ nguyên đến 6 số lẻ, không ép theo scale kết quả.
        value = deepcopy(self.demo)
        value['gia_thue']['don_gia']['gia_tri'] = '10000000.123456'
        self.validate(value)

    def test_ty_gia_du_bon_truong_va_khong_ep_kieu(self):
        value = deepcopy(self.demo)
        value['gia_thue']['ty_gia'] = {'cap': 'USD/VND', 'gia_tri': '25000.1234567', 'ngay': '2026-10-30', 'nguoi_nhap': 'DEMO'}
        self.validate(value)
        for field in ('cap', 'gia_tri', 'ngay', 'nguoi_nhap'):
            invalid = deepcopy(value)
            invalid['gia_thue']['ty_gia'].pop(field)
            self.reject(invalid)
        for path, field, invalid in (((), 'revision', True), ((), 'ngay_lap', '2026-02-30'),
                                      (('lich_thanh_toan', 0), 'lan', 0), (('lich_thanh_toan', 0), 'la_dat_coc', 1)):
            value = deepcopy(self.demo)
            target = value
            for part in path:
                target = target[part]
            target[field] = invalid
            self.reject(value)

    def test_khoa_dong_du_kien_va_lan_khong_trung(self):
        for field in ('lan', 'nghia_vu_id'):
            value = deepcopy(self.demo)
            value['lich_thanh_toan'][1][field] = value['lich_thanh_toan'][0][field]
            self.validate(value)
            with self.assertRaisesRegex(ValueError, 'Trùng'):
                _kiem_bat_bien(value)

    def test_khong_them_truong_ngoai_dac_ta(self):
        for path in ((), ('gia_thue',), ('lich_thanh_toan', 0), ('phi', 0), ('lich_thanh_toan', 0, 'moc')):
            value = deepcopy(self.demo)
            target = value
            for part in path:
                target = target[part]
            target['truong_chua_duyet'] = 'DEMO'
            self.reject(value)

    def test_giu_diem_cho_anh_khong_tu_chot_hoac_kich_hoat(self):
        self.assertIn('nhap', self.schema['$comment'])
        self.assertIn('Cần lead', self.schema['$comment'])
        for field in ('trang_thai', 'so_bao_gia'):
            self.assertIn('chờ Anh', self.schema['properties'][field]['description'])
        self.assertNotIn('enum', self.schema['properties']['trang_thai'])
        self.assertIn('chờ Anh', self.schema['$defs']['gia_tri_nhap']['description'])


if __name__ == '__main__':
    unittest.main()
