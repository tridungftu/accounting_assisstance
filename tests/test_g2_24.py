"""G2-24: gói DEMO trong thư mục tạm; không PG, server hay dịch vụ ngoài."""

from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import cai_dat, goi


CO_JSONSCHEMA = all(importlib.util.find_spec(name) is not None
                   for name in ('jsonschema', 'referencing'))
CONTRACT_ID = 'urn:ktt:contract:ghi_chu_demo.v1'


def ghi_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


def manifest_demo():
    return {
        'phien_ban_manifest': 1, 'loai': 'module', 'ma': 'mau_demo',
        'ten': 'Gói kiểm DEMO', 'phien_ban': '1.0.0',
        'tuong_thich': {'core': '>=1.0.0 <2.0.0', 'api': 'v1',
                       'sdk_python': '>=1.0.0 <2.0.0', 'sdk_js': '>=1.0.0 <2.0.0',
                       'contract': ['viec.v1']},
        'goi': {'tep_kiem_ke': 'goi/kiem_ke.json', 'thuat_toan_ma_bam': 'sha256',
                'phu_thuoc_module': []},
        'contract': {
            'cong_bo': [{'ma': 'ghi_chu_demo.v1', 'phien_ban': '1.0.0',
                        'module_so_huu': 'mau_demo', 'tep_mo_ta': 'contract/mo_ta.json',
                        'schema': 'contract/ghi_chu.v1.schema.json',
                        'vi_du': 'contract/ghi_chu.v1.vi_du.json'}],
            'su_kien_phat': [], 'su_kien_nhan': [], 'dau_vao_nguon': []},
        'backend': {'diem_vao': 'mau_demo.chay'},
        'giao_dien': {'diem_vao': 'ui/chinh.js', 'tai_nguyen': ['ui/chinh.js'],
                     'icon': 'file', 'nhom_mau': 'demo', 'thu_tu': 1,
                     'trang_dau': '#mau_demo/chinh', 'thao_tac_khung': 'liet_ke',
                     'phan': [], 'the': [
                         {'ma': key, 'nhan': key, 'dem': key,
                          'loc': {'phan': 'chinh', 'tham_so': {}}}
                         for key in ('moi', 'cu')]},
        'thao_tac': [{'ma': 'liet_ke', 'phuong_thuc': 'GET', 'duong_dan': '/ghi-chu/{id}',
                      'dau_vao': 'contract/ghi_chu.v1.schema.json',
                      'dau_ra': 'contract/ghi_chu.v1.schema.json',
                      'quyen': 'mau_demo.ghi_chu.doc', 'kieu': 'dong_bo',
                      'chong_trung': False}],
        'du_lieu_rieng': {'bang': ['ghi_chu'], 'ham': [], 'phan_vung': 'phap_nhan_id',
                          'goi_migration': {'ma': 'mau_demo', 'phien_ban_du_lieu': 1,
                                            'tep_kiem_ke': 'migration/kiem_ke.json',
                                            'thu_muc': 'migration'},
                          'v2_ghi_chung': [], 'v3_danh_muc': [], 'v4_cong_bo_doc': [],
                          'cot_nhom_a': []},
        'ham_core_goi': [], 'ma_loi': [], 'quyen_yeu_cau': [], 'engine_dung': [],
        'quy_trinh': [],
        'cong_bo': [{'ma': 'ghi_chu_demo', 'phien_ban': '1.0.0', 'ham': 'ghi_chu_v1',
                    'schema': 'contract/ghi_chu.v1.schema.json', 'truong': ['id'],
                    'quyen_doc': 'mau_demo.ghi_chu.doc'}],
        'su_kien': {'phat': [], 'nhan': []},
        'tien_trinh': {'cong': {'nguon': 'core_cap', 'pham_vi': 'loopback'},
                       'nhan_listener': 'socket.fromshare', 'readiness': 'kenh_dieu_khien',
                       'thu_hoi': 'drain_va_xac_nhan', 'bi_mat': 'stdin_hoac_handle',
                       'che_do_mac_dinh': 'tu_kich_hoat_tu_dong', 'ranh_giay_de_xuat': 300},
        'cong_tac': {'mac_dinh': 'TAT'}}


class KiemDuongDanTests(unittest.TestCase):
    def test_snapshot_handle_hash_va_khong_import_ma_goi(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'contract').mkdir()
            (root / '__init__.py').write_bytes(b'raise RuntimeError("CAM IMPORT")')
            files, dirs = goi._snapshot(root, goi.GioiHan())
            self.assertEqual(dirs, {'contract'})
            self.assertEqual(files['__init__.py'], b'raise RuntimeError("CAM IMPORT")')
            hashes, sha = goi.bam_goi(files)
            self.assertEqual(hashes['__init__.py'], hashlib.sha256(files['__init__.py']).hexdigest())
            self.assertNotEqual(sha, goi.bam_goi({'doi_ten.py': files['__init__.py']})[1])

    def test_snapshot_gioi_han_va_hardlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'demo.txt').write_bytes(b'DEMO')
            for limits in (goi.GioiHan(moi_tep=3), goi.GioiHan(ca_goi=3)):
                with self.assertRaises(goi.LoiGoi):
                    goi._snapshot(root, limits)
            os.link(root / 'demo.txt', root / 'lien_ket.txt')
            with self.assertRaises(goi.LoiGoi):
                goi._snapshot(root, goi.GioiHan())

    def test_snapshot_symlink_that_khong_can_validator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'goi_demo'
            root.mkdir()
            outside = Path(tmp) / 'ngoai_demo'
            outside.mkdir()
            try:
                (root / 'lien_ket').symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest('NOT_RUN: không có quyền tạo symlink Windows')
            with self.assertRaises(goi.LoiGoi):
                goi._snapshot(root, goi.GioiHan())

    def test_staging_thieu_validator_phai_tu_choi(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / 'goi_demo'
            (package / 'contract').mkdir(parents=True)
            ghi_json(package / 'module.json', {})
            with patch.object(cai_dat, 'THU_MUC_DU_AN', root / 'du_an_demo'), \
                    patch.object(goi, '_bo_schema', side_effect=goi.LoiGoi('Thiếu validator.')):
                report = cai_dat.dua_vao_staging(package, ma_lat='g2-24', phien_ban_core='1.0.0')
            self.assertEqual(report.ket_luan, 'KHONG_DAT')
            self.assertIn('Thiếu validator.', report.ly_do)
            self.assertFalse((root / 'du_an_demo').exists())

    def test_duong_dan_windows_posix_ads_thoat_goi(self):
        for name in ('../x', 'a/../x', '/x', '//host/x', 'C:/x', 'a\\x',
                     'x:stream', 'a//b', 'a/./b', 'CON.txt', 'a/NUL', 'x.', 'x '):
            with self.subTest(name=name), self.assertRaises(goi.LoiGoi):
                goi.kiem_ten_tep(name)

    def test_khong_doc_dich_that_hoac_cau_hinh_rieng(self):
        for name in ('var/plhn-that/x', 'var/web-that/x', '.env',
                     'cau_hinh.that.toml', 'runtime.local.json', 'D:/DU-LIEU-KE-TOAN/x'):
            with self.subTest(name=name), self.assertRaises(goi.LoiGoi):
                goi.kiem_duong_dan(name)

    def test_reparse_point_junction_bi_chan_truoc_doc(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = Path.lstat

            def lstat(path, *args, **kwargs):
                if path == root:
                    return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
                return original(path, *args, **kwargs)

            with patch.object(Path, 'lstat', lstat), self.assertRaises(goi.LoiGoi):
                goi.kiem_duong_dan(root)

    def test_json_trung_khoa_so_vo_han_va_tran_float(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":{"a":1,"a":2}}',
                    b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e9999}'):
            with self.subTest(raw=raw), self.assertRaises(goi.LoiGoi):
                goi.doc_json(raw, goi.GioiHan())

    def test_semver_va_range_khong_doan_cu_phap_la(self):
        for version, spec in (('1.2.0', '>=1.0.0 <2.0.0'),
                              ('1.2.0-alpha.10', '>1.2.0-alpha.2 <1.2.0'),
                              ('1.0.0+demo', '=1.0.0')):
            goi.kiem_phien_ban(version, spec)
        for version, spec in (('2.0.0', '>=1.0.0 <2.0.0'), ('1.0.0', '^1.0.0'),
                              ('1.0.0', 'latest'), ('1.0.0', ''),
                              ('1.0.0-01', '>=1.0.0')):
            with self.subTest(version=version, spec=spec), self.assertRaises(goi.LoiGoi):
                goi.kiem_phien_ban(version, spec)


@unittest.skipUnless(CO_JSONSCHEMA, 'NOT_RUN: thiếu jsonschema/referencing')
class GoiDemoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='kho_test_g2_24_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.package = self.root / 'nguon_demo'
        self.manifest = manifest_demo()
        self.schema = {'$schema': goi.DRAFT, '$id': CONTRACT_ID, 'type': 'object',
                       'additionalProperties': False, 'required': ['id', 'ngay', 'luc'],
                       'properties': {'id': {'type': 'string', 'format': 'uuid'},
                                      'ngay': {'type': 'string', 'format': 'date'},
                                      'luc': {'type': 'string', 'format': 'date-time'}}}
        self.example = {'id': '10000000-0000-4000-8000-000000000001',
                        'ngay': '2026-10-30', 'luc': '2026-10-30T00:00:00Z'}
        self.save_manifest()
        self.save_schema()
        self.save_example()
        ghi_json(self.package / 'contract/mo_ta.json',
                 {'ma': 'ghi_chu_demo.v1', 'phien_ban': '1.0.0', 'muc_dich': 'DEMO'})
        for name, raw in {'mau_demo/__init__.py': b'raise RuntimeError("CAM IMPORT GOI")',
                          'mau_demo/chay.py': b'raise RuntimeError("CAM CHAY GOI")',
                          'ui/chinh.js': b'throw new Error("CAM CHAY ASSET");',
                          'goi/kiem_ke.json': b'{}', 'migration/kiem_ke.json': b'{}',
                          'migration/001_demo.sql': b'-- DEMO, khong duoc ap SQL'}.items():
            path = self.package / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        self.destination = self.root / 'du_an_demo'
        self.patcher = patch.object(cai_dat, 'THU_MUC_DU_AN', self.destination)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def save_manifest(self):
        ghi_json(self.package / 'module.json', self.manifest)

    def save_schema(self):
        ghi_json(self.package / 'contract/ghi_chu.v1.schema.json', self.schema)

    def save_example(self):
        ghi_json(self.package / 'contract/ghi_chu.v1.vi_du.json', self.example)

    def read(self, **kwargs):
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-24')):
            return goi.doc_goi(self.package, phien_ban_core='1.0.0', **kwargs)

    def stage(self, **kwargs):
        return cai_dat.dua_vao_staging(self.package, ma_lat='g2-24',
                                     phien_ban_core='1.0.0', **kwargs)

    def reject(self):
        with self.assertRaises(goi.LoiGoi):
            self.read()

    def test_goi_hop_le_hash_va_khong_chay_ma(self):
        package = self.read()
        self.assertNotIn('mau_demo', sys.modules)
        self.assertIn(b'CAM IMPORT GOI', package.cac_tep['mau_demo/__init__.py'])
        for name, raw in package.cac_tep.items():
            self.assertEqual(package.sha256_tung_tep[name], hashlib.sha256(raw).hexdigest())
        with self.assertRaises(TypeError):
            package.cac_tep['them.py'] = b''
        self.assertEqual(package.sha256_goi, self.read().sha256_goi)

    def test_staging_chi_demo_khong_ghi_de_khong_ap_sql(self):
        with patch('socket.socket', side_effect=AssertionError('Cấm mạng G2-24')):
            first, second = self.stage(), self.stage()
        self.assertEqual((first.ket_luan, second.ket_luan), ('DAT', 'DAT'))
        self.assertNotEqual(first.thu_muc_staging, second.thu_muc_staging)
        self.assertTrue(first.thu_muc_staging.is_relative_to(
            self.destination / 'var/core-demo/g2-24/goi'))
        self.assertEqual(first.sha256_goi, second.sha256_goi)
        for name, sha in first.sha256_tung_tep.items():
            self.assertEqual(hashlib.sha256((first.thu_muc_staging / name).read_bytes()).hexdigest(), sha)
        self.assertFalse((self.destination / 'kich_hoat').exists())

    def test_staging_sao_chep_snapshot_khong_doc_lai_nguon_da_doi(self):
        original = cai_dat.doc_goi

        def doc(path, **kwargs):
            package = original(path, **kwargs)
            if Path(path) == self.package:
                (self.package / 'ui/chinh.js').write_bytes(b'NGUON DA DOI')
            return package

        with patch.object(cai_dat, 'doc_goi', side_effect=doc):
            report = self.stage()
        self.assertEqual(report.ket_luan, 'DAT')
        self.assertNotEqual((report.thu_muc_staging / 'ui/chinh.js').read_bytes(), b'NGUON DA DOI')

    def test_staging_goi_loi_tra_ly_do_tieng_viet_khong_co_hash(self):
        self.manifest['tien_trinh']['cong'] = 9999
        self.save_manifest()
        report = self.stage()
        self.assertEqual(report.ket_luan, 'KHONG_DAT')
        self.assertTrue(report.ly_do)
        self.assertIsNone(report.sha256_goi)
        self.assertIsNone(report.thu_muc_staging)
        self.assertFalse(self.destination.exists())

    def test_khai_schema_role_cong_va_doi_tuong_cong_bo_bi_bac(self):
        original = deepcopy(self.manifest)
        for field in ('schema', 'role', 'cong'):
            with self.subTest(field=field):
                self.manifest = deepcopy(original)
                self.manifest[field] = 'DEMO'
                self.save_manifest()
                self.reject()
        for path, field, value in (
                (('du_lieu_rieng',), 'schema', 'mod_tuy_chon'),
                (('du_lieu_rieng', 'goi_migration'), 'vai', 'vai_tuy_chon'),
                (('tien_trinh',), 'cong', 9999),
                (('cong_bo', 0), 'doi_tuong', 'mod_khac.bang')):
            self.manifest = deepcopy(original)
            target = self.manifest
            for key in path:
                target = target[key]
            target[field] = value
            self.save_manifest()
            self.reject()

    def test_traversal_manifest_va_ref_khong_duoc_doc_ngoai_goi(self):
        for path in ('../that.json', '/that.json', 'C:/that.json',
                     'contract/../that.json', 'contract\\that.json'):
            with self.subTest(path=path):
                self.manifest['contract']['cong_bo'][0]['schema'] = path
                self.save_manifest()
                self.reject()

    def test_symlink_ngoai_goi_bi_chan(self):
        outside = self.root / 'ngoai_demo'
        outside.mkdir()
        ghi_json(outside / 'demo.json', {'demo': True})
        try:
            (self.package / 'lien_ket').symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('NOT_RUN: Windows không cấp quyền tạo symlink; reparse mock có ca riêng')
        self.reject()

    def test_hardlink_bi_chan(self):
        os.link(self.package / 'ui/chinh.js', self.package / 'ui/lien_ket.js')
        self.reject()

    def test_thieu_contract_bi_bac(self):
        (self.package / 'contract').rename(self.package / 'contract_thieu')
        self.reject()

    def test_thieu_schema_vi_du_phien_ban_va_file_mo_ta(self):
        original = deepcopy(self.manifest['contract']['cong_bo'][0])
        for field in ('schema', 'vi_du', 'phien_ban', 'tep_mo_ta'):
            entry = deepcopy(original)
            entry.pop(field)
            self.manifest['contract']['cong_bo'] = [entry]
            self.save_manifest()
            self.reject()
        self.manifest['contract']['cong_bo'] = [{**original, 'vi_du': 'contract/thieu.json'}]
        self.save_manifest()
        self.reject()

    def test_vi_du_sai_schema_uuid_ngay_va_thoi_diem(self):
        original = deepcopy(self.example)
        for field, value in (('id', 'sai-uuid'), ('ngay', '2026-02-30'),
                             ('luc', '2026-02-30T00:00:00Z'),
                             ('luc', '2026-10-30T00:00:00'), ('them', 'DEMO')):
            self.example = {**original, field: value}
            self.save_example()
            self.reject()

    def test_meta_schema_sai_va_id_trung_bi_bac(self):
        self.schema['type'] = 'sai_kieu'
        self.save_schema()
        self.reject()

    def test_ref_la_hoac_fragment_thieu_ke_ca_nhanh_khong_chay(self):
        for ref in ('https://example.invalid/x', '../ngoai_demo/schema.json',
                    'urn:ktt:contract:chua_co.v1', CONTRACT_ID + '#/$defs/thieu'):
            self.schema['anyOf'] = [{}, {'$ref': ref}]
            self.save_schema()
            self.reject()

    def test_ref_offline_chung_hop_le(self):
        self.schema['properties']['id'] = {'$ref': 'urn:ktt:contract:chung.v1#/$defs/id'}
        self.save_schema()
        self.read()

    def test_route_trung_ke_ca_doi_ten_path_parameter(self):
        original = deepcopy(self.manifest['thao_tac'][0])
        for path in ('/ghi-chu/{id}', '/ghi-chu/{ma}'):
            self.manifest['thao_tac'] = [original, {**original, 'ma': 'doc_lap', 'duong_dan': path}]
            self.save_manifest()
            self.reject()

    def test_route_khac_method_duoc_phep(self):
        original = self.manifest['thao_tac'][0]
        self.manifest['thao_tac'].append({**original, 'ma': 'ghi', 'phuong_thuc': 'POST',
                                          'chong_trung': True})
        self.save_manifest()
        self.read()

    def test_core_sdk_va_dependency_khong_tuong_thich(self):
        self.manifest['tuong_thich']['core'] = '>=2.0.0'
        self.save_manifest()
        self.reject()
        self.manifest['tuong_thich']['core'] = '>=1.0.0 <2.0.0'
        self.manifest['goi']['phu_thuoc_module'] = [{'ma': 'nguon_demo', 'phien_ban': '>=1.0.0 <2.0.0'}]
        self.save_manifest()
        self.reject()
        with self.assertRaises(goi.LoiGoi):
            self.read(module_da_co={'nguon_demo': '2.0.0'})
        self.read(module_da_co={'nguon_demo': '1.3.0'})
        with self.assertRaises(goi.LoiGoi):
            self.read(module_da_co={'nguon_demo': '1.3.0'}, phien_ban_sdk_python='2.0.0')

    def test_gioi_han_file_goi_json_so_muc_do_sau(self):
        for limits in (goi.GioiHan(moi_tep=10), goi.GioiHan(ca_goi=100),
                       goi.GioiHan(json=10), goi.GioiHan(so_muc=2)):
            with self.subTest(limits=limits), self.assertRaises(goi.LoiGoi):
                self.read(gioi_han=limits)
        (self.package / 'a/b/c').mkdir(parents=True)
        with self.assertRaises(goi.LoiGoi):
            self.read(gioi_han=goi.GioiHan(do_sau=1))

    def test_staging_tu_choi_ma_lat_duong_dan_va_junction(self):
        report = cai_dat.dua_vao_staging(self.package, ma_lat='../../web-that', phien_ban_core='1.0.0')
        self.assertEqual(report.ket_luan, 'KHONG_DAT')
        with patch.object(cai_dat, 'THU_MUC_DU_AN', self.root / 'web-that'):
            self.assertEqual(self.stage().ket_luan, 'KHONG_DAT')

    def test_loi_ghi_khong_tra_dat_khong_xoa_goi_nguon(self):
        with patch.object(cai_dat.os, 'fsync', side_effect=OSError('DEMO')):
            report = self.stage()
        self.assertEqual(report.ket_luan, 'KHONG_DAT')
        self.assertIsNone(report.sha256_goi)
        self.assertTrue((self.package / 'module.json').exists())


if __name__ == '__main__':
    unittest.main()
