"""AI-2: adapter thật + Local/Cloud/Mask giả, không AI hoặc mạng thật.

Ca M9 chỉ là mẫu module giả; lead grep mọi lời gọi M9 thật ở cổng kiểm.
Thiếu jsonschema thì dùng seam kiểm tối thiểu của bộ test G2-17;
meta-schema đầy đủ được ghi CHUA_KIEM, không coi fallback là chứng nhận.
"""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_g2_17 as bundle

from kho_tri_thuc.engines.e_hoi_ai.hoi import AdapterHoiAI, HOI, TRA_LOI
from kho_tri_thuc.tri_thuc import cong_ai as ca


TEP = '00000000-0000-4000-8000-000000000001'
PHAP_NHAN = '00000000-0000-4000-8000-000000000002'
VIEC = '00000000-0000-4000-8000-000000000003'
LUOT = '00000000-0000-4000-8000-000000000004'
VAN_BAN = 'Lãi suất DEMO 8%/năm, điều chỉnh 9%/năm.'
NGUON = dict(revision=1, nguon_tep_ids=[TEP],
             vi_tri={'tep_id': TEP, 'dinh_vi': 'doan:1'},
             phap_nhan_id=PHAP_NHAN, viec_id=VIEC)


def dau_vao(**changes):
    return dict(loai_viec='BOC_TACH_HOP_DONG', van_ban=VAN_BAN,
                chi_dan='Trích lãi suất DEMO.', truong=['lai_suat'], **changes)


def tra_loi(value='8%/năm', do_tin_cay=0.95, trich_dan=VAN_BAN):
    return json.dumps({'truong': [{'ten': 'lai_suat', 'gia_tri': value,
                                  'trich_dan': trich_dan}],
                       'do_tin_cay': do_tin_cay}, ensure_ascii=False)


def m9_gia_hoi(sdk_core):
    """Ca mẫu: module M9 giả, không thay cổng grep M9 thật của lead."""
    return sdk_core.goi('ai.hoi@1', {
        **dau_vao(chi_cuc_bo=True), 'loai_viec': 'HOI_DAP_VAY'})


class MaskGia:
    """Chỉ dữ liệu DEMO không có định danh; không chứng nhận bộ che thật."""

    def __init__(self):
        self.che = Mock(side_effect=lambda text, ids: ca.LuotChe('mask-DEMO', text))
        self.mo_che = Mock(side_effect=lambda ma, text, **kw: text)
        self.ket_thuc = Mock()
        self.co_khoa = Mock(return_value=True)


class AdapterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = {}
        for name in ('ky_thuat.json', 'manifest.json'):
            cls.schemas.update(json.loads(
                (bundle.CONTRACT_DIR / name).read_text(encoding='utf-8')))
        if bundle.Draft202012Validator:
            def offline(uri):
                raise bundle.NoSuchResource(ref=uri)
            cls.registry = bundle.Registry(retrieve=offline).with_resources(
                (uri, bundle.Resource.from_contents(schema))
                for uri, schema in cls.schemas.items())

    def kiem(self, schema, value):
        try:
            # Luôn chạy fallback chỉ trong test, đồng thời chạy validator đầy đủ nếu có.
            bundle._minimal(value, schema, schema, self.schemas)
            if bundle.Draft202012Validator:
                bundle.Draft202012Validator(schema, registry=self.registry,
                    format_checker=bundle.FormatChecker()).validate(value)
            return True
        except ValueError:
            return False
        except Exception as exc:
            if bundle.Draft202012Validator:
                from jsonschema.exceptions import ValidationError
                if isinstance(exc, ValidationError):
                    return False
            raise

    def setUp(self):
        self.enterContext(patch('socket.socket', side_effect=AssertionError('Cấm mạng')))
        self.enterContext(patch.object(ca, 'doc_khoa_mask',
                                      side_effect=AssertionError('Cấm đọc tệp khóa')))
        self.local = Mock(return_value=tra_loi())
        self.cloud = Mock()
        self.cloud.tra_loi.return_value = ca.PhanHoiCloud(tra_loi('9%/năm'),
                                                       'cloud-DEMO-thuc', 10, 20)
        self.mask = MaskGia()
        self.ghi = ca.BoGhiBoNho()
        self.chon_kiem = Mock(return_value=True)
        self.cong = ca.CongAI({
            'local_ai': {'enabled': True, 'model': 'local-DEMO',
                         'url': 'http://127.0.0.1:1234/v1/chat/completions'},
            'cong_ai': {'cloud_bat': True}}, bo_ghi=self.ghi,
            nha_cung_cap=self.cloud, mask=self.mask, local_transport=self.local,
            moi_truong={'ANTHROPIC_API_KEY': 'khoa-DEMO'},
            kiem_xac_suat=self.chon_kiem)
        self.luot = Mock(return_value=LUOT)
        self.adapter = AdapterHoiAI(self.cong, kiem_schema=self.kiem,
                                    tham_chieu_luot_che=self.luot)

    def goi(self, payload=None, **source):
        result = self.adapter.goi(dau_vao() if payload is None else payload,
                                 **{**deepcopy(NGUON), **source})
        self.assertTrue(self.kiem({'$ref': TRA_LOI}, result))
        return result

    def test_chi_local_khi_local_loi(self):
        self.local.side_effect = ValueError('Local DEMO lỗi')
        out = self.goi(dau_vao(chi_cuc_bo=True))
        self.assertEqual((out['duong'], out['muc']), ('KHONG', 'DO'))
        self.assertIn('CLOUD_TAT', out['ly_do'])
        self.cloud.tra_loi.assert_not_called()
        self.mask.che.assert_not_called()

    def test_dan_chung_chuan_hoa_khoang_trang_qua_adapter(self):
        for van_ban in (VAN_BAN.replace('DEMO ', 'DEMO\n'),
                        VAN_BAN.replace(' ', '   \t ')):
            for chi_cuc_bo in (True, False):
                with self.subTest(van_ban=van_ban, chi_cuc_bo=chi_cuc_bo):
                    out = self.goi({**dau_vao(chi_cuc_bo=chi_cuc_bo),
                                    'van_ban': van_ban})
                    self.assertEqual(out['duong'], 'LOCAL' if chi_cuc_bo else 'CLOUD')
                    self.assertEqual(out['truong'][0]['dan_chung'],
                                     [dict(vi_tri=NGUON['vi_tri'], trich_dan=VAN_BAN)])
                    self.assertEqual(out['kiem_tra']['trich_dan'], 'dat')
                    self.assertEqual(out['truong_bi_loai'], [])

    def test_dan_chung_ngoai_van_ban_bi_cong_goc_loai_qua_adapter(self):
        answer = tra_loi(trich_dan='Lãi suất DEMO 10%/năm.')
        self.local.return_value = answer
        self.cloud.tra_loi.return_value = ca.PhanHoiCloud(answer, 'cloud-DEMO-thuc', 10, 20)
        yc = ca.YeuCauAI('BOC_TACH_HOP_DONG', VAN_BAN, 'Trích lãi suất DEMO.',
                         ('lai_suat',))
        for chi_cuc_bo in (True, False):
            with self.subTest(chi_cuc_bo=chi_cuc_bo):
                goc = ca.danh_gia(ca.doc_json_tra_loi(answer), yc,
                                  ca.loai_viec(yc.loai_viec),
                                  'LOCAL' if chi_cuc_bo else 'CLOUD')
                self.assertEqual(goc.bi_loai, {'lai_suat': 'TRICH_DAN_SAI'})
                out = self.goi(dau_vao(chi_cuc_bo=chi_cuc_bo))
                self.assertEqual(out['truong'], [])
                self.assertEqual(out['truong_bi_loai'], list(goc.bi_loai))
                self.assertIn('TRICH_DAN_SAI', out['ly_do'])
                self.assertEqual(out['kiem_tra']['trich_dan'], 'chua_kiem')

    def test_chi_local_khi_khong_chac(self):
        self.local.return_value = tra_loi(do_tin_cay=0.4)
        out = self.goi(dau_vao(chi_cuc_bo=True))
        self.assertEqual(out['duong'], 'LOCAL')
        self.assertIn('CLOUD_TAT', out['ly_do'])
        self.cloud.tra_loi.assert_not_called()
        self.mask.che.assert_not_called()

    def test_chi_local_chan_chon_kiem_xac_suat(self):
        self.chon_kiem.return_value = True
        self.goi(dau_vao(chi_cuc_bo=True))
        self.chon_kiem.assert_not_called()
        self.cloud.tra_loi.assert_not_called()
        self.mask.che.assert_not_called()
        # Cùng bộ chọn đó có thể gửi Cloud khi request không hạn chế.
        self.goi(dau_vao(chi_cuc_bo=False))
        self.chon_kiem.assert_called_once()
        self.cloud.tra_loi.assert_called_once()

    def test_hai_request_khac_co_chay_xen_ke(self):
        entered, release = threading.Event(), threading.Event()
        original = deepcopy(self.cong.cai_dat)

        def transport(url, body):
            if threading.current_thread().name.startswith('local-only'):
                entered.set()
                if not release.wait(5):
                    raise AssertionError('Không hoàn tất xen kẽ')
            return tra_loi()

        self.local.side_effect = transport
        with ThreadPoolExecutor(1, thread_name_prefix='local-only') as pool:
            first = pool.submit(self.goi, dau_vao(chi_cuc_bo=True))
            try:
                self.assertTrue(entered.wait(5))
                second = self.goi(dau_vao(chi_cuc_bo=False))
                self.assertEqual(second['duong'], 'CLOUD')
                self.assertEqual(self.cong.cai_dat, original)
            finally:
                release.set()
            self.assertEqual(first.result(5)['duong'], 'LOCAL')
        self.cloud.tra_loi.assert_called_once()
        self.assertEqual(self.cong.cai_dat, original)
        self.assertIs(self.cong.bo_ghi, self.ghi)

    def test_false_khong_tu_bat_cloud_toan_cuc(self):
        self.cong.cai_dat['cloud_bat'] = False
        for answer in (tra_loi(), tra_loi(do_tin_cay=0.4), None):
            with self.subTest(answer=answer):
                self.local.return_value = answer
                self.goi(dau_vao(chi_cuc_bo=False))
        self.cloud.tra_loi.assert_not_called()
        self.mask.che.assert_not_called()
        self.assertIs(self.cong.cai_dat['cloud_bat'], False)

    def test_mac_dinh_va_anh_xa_dto_khong_sua_payload(self):
        payload = dau_vao(dinh_danh_da_biet=[
            'Công ty DEMO', ['Công ty DEMO B', 'CONG_TY'],
            {'gia_tri': 'DEMO-01', 'nhom': ''}])
        original = deepcopy(payload)
        calls = []
        goi_goc = ca.CongAI.goi

        def record(cong, yc, **kw):
            calls.append((cong, yc))
            return goi_goc(cong, yc, **kw)

        with patch.object(ca.CongAI, 'goi', record):
            self.goi(payload)
        cong, yc = calls[0]
        self.assertIsNot(cong, self.cong)
        self.assertIsNot(cong.cai_dat, self.cong.cai_dat)
        self.assertEqual(yc.truong, ('lai_suat',))
        self.assertEqual(yc.dinh_danh_da_biet[1], ('Công ty DEMO B', 'CONG_TY'))
        self.assertEqual((yc.phap_nhan_id, yc.viec_id), (PHAP_NHAN, VIEC))
        self.assertEqual(payload, original)
        self.cloud.tra_loi.assert_called_once()

    def test_dau_vao_sai_schema_bi_bac_truoc_ai(self):
        invalid = [None, [], {}, {**dau_vao(), 'chi_cuc_bo': 'true'},
                   {**dau_vao(), 'chi_cuc_bo': 1},
                   {**dau_vao(), 'chi_cuc_bo': None},
                   {**dau_vao(), 'van_ban': ' \n\t'},
                   {**dau_vao(), 'truong': ['']},
                   {**dau_vao(), 'dinh_danh_da_biet': None},
                   {**dau_vao(), 'dinh_danh_da_biet': [['DEMO']]},
                   {**dau_vao(), 'dinh_danh_da_biet': [{'gia_tri': 'DEMO'}]},
                   {**dau_vao(), 'phap_nhan_id': PHAP_NHAN},
                   {**dau_vao(), 'loai_viec': 'KHONG_CO'}]
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.adapter.goi(payload, **deepcopy(NGUON))
        self.local.assert_not_called()
        self.cloud.tra_loi.assert_not_called()

    def test_tra_loi_giu_gia_tri_local_dan_chung_va_model(self):
        out = self.goi()
        field = out['truong'][0]
        self.assertIsNone(out['cau_tra_loi'])
        self.assertEqual(field['gia_tri'], {'kieu': 'van_ban', 'gia_tri': '9%/năm'})
        self.assertEqual(field['gia_tri_local']['gia_tri'], '8%/năm')
        self.assertEqual(field['dan_chung'], [dict(vi_tri=NGUON['vi_tri'], trich_dan=VAN_BAN)])
        self.assertEqual(out['luot_che_id'], LUOT)
        self.luot.assert_called_once_with('mask-DEMO', phap_nhan_id=PHAP_NHAN, viec_id=VIEC)
        self.assertEqual(out['kiem_tra'], {'trich_dan': 'dat', 'mo_che': 'dat'})
        self.assertEqual([(m['ten'], m['can_cu']) for m in out['mo_hinh']],
                         [('local-DEMO', 'cau_hinh'), ('cloud-DEMO-thuc', 'thuc_te')])
        self.assertTrue(all(r.viec_id == VIEC for r in self.ghi.ban_ghi))

    def test_cloud_loi_khong_bien_ket_qua_local_thanh_cloud(self):
        self.cloud.tra_loi.side_effect = ValueError('Cloud DEMO lỗi')
        out = self.goi()
        self.assertEqual(out['duong'], 'LOCAL')
        self.assertNotIn('luot_che_id', out)
        self.assertEqual([m['duong'] for m in out['mo_hinh']], ['LOCAL'])
        self.assertIn('CLOUD_LOI', out['ly_do'])

    def test_cloud_khong_duoc_tu_tao_uuid_luot_che(self):
        self.adapter._tham_chieu_luot_che = None
        with self.assertRaises(ValueError):
            self.goi()
        self.adapter._tham_chieu_luot_che = Mock(return_value='mask-DEMO')
        with self.assertRaises(ValueError):
            self.goi()

    def test_nguon_khong_hop_le_bi_bac_truoc_ai(self):
        for changes in ({'revision': 0}, {'nguon_tep_ids': []},
                        {'vi_tri': {'tep_id': LUOT, 'dinh_vi': 'doan:1'}},
                        {'viec_id': 'gia-mao'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.goi(**changes)
        self.local.assert_not_called()

    def test_khong_fallback_env_hoac_tep_khoa(self):
        for name in ('_moi_truong', '_mask'):
            cong = deepcopy(self.cong)
            setattr(cong, name, None)
            with self.subTest(name=name), self.assertRaises(ValueError):
                AdapterHoiAI(cong, kiem_schema=self.kiem)
        self.cong._moi_truong = {}
        with patch.dict(ca.os.environ, {'ANTHROPIC_API_KEY': 'khoa-env-DEMO'}):
            self.local.return_value = tra_loi(do_tin_cay=0.4)
            out = self.goi()
        self.assertIn('CHUA_CO_KHOA_API', out['ly_do'])
        self.cloud.tra_loi.assert_not_called()

    def test_m9_luon_gui_chi_cuc_bo_true_ca_mau(self):
        sdk = Mock()
        sdk.goi.side_effect = lambda capability, payload: self.goi(payload)
        out = m9_gia_hoi(sdk)
        capability, payload = sdk.goi.call_args.args
        self.assertEqual(capability, 'ai.hoi@1')
        self.assertIs(payload['chi_cuc_bo'], True)
        self.assertEqual(out['duong'], 'LOCAL')
        self.cloud.tra_loi.assert_not_called()

    def test_manifest_schema_g2_17b_va_chi_capability_da_kiem(self):
        manifest = json.loads((bundle.ROOT / 'src/kho_tri_thuc/engines/e_hoi_ai/engine.json')
                              .read_text(encoding='utf-8'))
        self.assertTrue(self.kiem({'$ref': 'urn:ktt:manifest:engine.v1'}, manifest))
        self.assertEqual([(c['ma'], c['dau_vao'], c['dau_ra']) for c in manifest['capability']],
                         [('ai.hoi@1', 'hoi_ai.v1', 'tra_loi_ai.v1')])
        self.assertIs(manifest['ho_so_chay_mau']['headless'], True)
        self.assertIs(manifest['ho_so_chay_mau']['login_csdl'], False)
        self.assertEqual(manifest['ban_giao_ket_qua'], 'core_xac_nhan_truoc_giai_phong')

    @unittest.skipUnless(bundle.Draft202012Validator,
                         'CHUA_KIEM: thiếu jsonschema kiểm meta-schema 2020-12')
    def test_meta_schema_day_du(self):
        for ref in (HOI, TRA_LOI, 'urn:ktt:manifest:engine.v1'):
            bundle.Draft202012Validator.check_schema(self.schemas[ref])


if __name__ == '__main__':
    unittest.main()
