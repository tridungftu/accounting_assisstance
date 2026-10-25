"""M2c — DEMO tự tạo; kết nối giả kiểm wiring, không chứng nhận SQL thật.

Consumer giả mô phỏng quy tắc semantic revision của SQL hiện có. Không che
khoảng thiếu: bytes-only/tthai chưa tạo revision, BANG_KE chưa promote.
Không cần psycopg, PostgreSQL, cổng thuế hay cấu hình/kho thật.
"""

from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import ExitStack, contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from test_m2_00_manifest_tinh import tao_run_demo
from kho_tri_thuc.ha_tang.primitives import DataError, sha256
from kho_tri_thuc.k2 import nguon_chung
from kho_tri_thuc.k2.hoa_don import HoaDonK2
from kho_tri_thuc.m2.tai_hoa_don.nhan import lap_ke_hoach_nhan, nhan_vao_k2
from kho_tri_thuc.m2.tai_hoa_don import nhan as nhan_module
from kho_tri_thuc.nguon.hoa_don_xml import CompanyFact, IDENTITY_PROFILE_REF, PROFILE_DOCUMENT_SHA256, PROFILE_REF


def xml_demo(*, tien='<DVTTe>VND</DVTTe>', them='', gia='12.5', so='000001'):
    return (f'<HDon><DLHDon><TTChung><KHMSHDon>1</KHMSHDon><KHHDon>DEMO</KHHDon>'
            f'<SHDon>{so}</SHDon><NLap>2026-10-24</NLap>{tien}{them}</TTChung>'
            '<NDHDon><NBan><MST>0000000001</MST></NBan><NMua><MST>0000000002</MST></NMua>'
            '<DSHHDVu><HHDVu><STT>1</STT><TChat>1</TChat><THHDVu>Hàng DEMO</THHDVu>'
            f'<DVTinh>CAI</DVTinh><SLuong>1</SLuong><DGia>{gia}</DGia><ThTien>12.5</ThTien>'
            '<TSuat>0</TSuat></HHDVu></DSHHDVu></NDHDon></DLHDon></HDon>').encode('utf-8')


class KetNoiGia:
    """Chỉ nhận đúng câu gọi consumer; stage/receipt giả trong test riêng này."""
    def __init__(self):
        self.stages, self.receipts, self.identities, self.observations = {}, {}, {}, []
        self.calls = []

    @contextmanager
    def transaction(self):
        yield

    def execute(self, sql, args):
        self.calls.append(sql)
        if 'set_config' in sql:
            return Mock(fetchone=lambda: {'ai': 'DEMO_ACTOR'})
        if 'kho.m2_tieu_thu_quan_sat' not in sql:
            raise AssertionError('Kết nối giả không cho chạy SQL ngoài consumer hiện hữu')
        du = self.stages[args[0]]['du']
        items = []
        for p in du['promote_m2']:
            key = tuple(p['identity'])
            versions = self.identities.setdefault(key, [])
            sem = p['semantic_sha256']
            moi = sem not in versions
            if moi:
                versions.append(sem)
            cls = 'FIRST_OBSERVATION' if not any(o['key'] == key for o in self.observations) else (
                'CHANGED_CONTENT_HOLD' if moi else 'SAME_CONTENT_REPEAT')
            item = {'observation_id': str(len(self.observations) + 1), 'hoa_don_id': str(len(self.identities)),
                    'phien_ban_id': str(versions.index(sem) + 1), 'classification': [cls]}
            self.observations.append({'key': key, **item})
            items.append(item)
        self.stages[args[0]]['items'] = items
        return Mock(fetchone=lambda: {'v': {'items': items}})


class NhanTinh(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='M2c-DEMO-', ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run, self.m = self.tao_run('20261024-120000')

    def tao_run(self, run_id, raw=None, chieu='purchase'):
        thu_muc_chieu = 'mua_vao' if chieu == 'purchase' else 'ban_ra'
        run = self.root / 'DEMO' / '2026-10' / thu_muc_chieu / run_id
        run.mkdir(parents=True)
        m = tao_run_demo(run)
        m.update(run_id=run_id, chieu=chieu, thu_muc_chieu=thu_muc_chieu)
        self.doi_xml(run, m, xml_demo() if raw is None else raw)
        self.ghi(run, m)
        return run, m

    @staticmethod
    def doi_xml(run, m, raw):
        h = m['hoa_don'][0]
        (run / h['file_xml']).write_bytes(raw)
        h.update(hash_xml=sha256(raw), xml_bytes=len(raw))
        h['xml_tep'][0].update(sha256=sha256(raw), bytes=len(raw))

    @staticmethod
    def ghi(run, m):
        (run / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False), encoding='utf-8')

    def plan(self, run=None):
        return lap_ke_hoach_nhan(run or self.run, ma_phap_nhan='DEMO')

    def nhan(self, p, service):
        return nhan_vao_k2(p, service, actor='DEMO_ACTOR', source_instance='DEMO', scope_ref='DEMO')

    def khong_xml(self, status):
        h = self.m['hoa_don'][0]
        h.update(xml_status=status, bang_chung='BANG_KE' if status == 'KHONG_XML_GOC' else None,
                 can_cu='DEMO_KHONG_XML_GOC' if status == 'KHONG_XML_GOC' else None,
                 file_xml=None, hash_xml=None, xml_bytes=None, xml_tep=[],
                 file_pdf=None, hash_pdf=None, vai_tro_pdf=None)
        self.m['tong'].update(xml_ok=0, pdf_ok=0,
                             khong_xml_goc=int(status == 'KHONG_XML_GOC'), xml_loi=int(status == 'LOI'),
                             xml_khong_yeu_cau=int(status == 'KHONG_YEU_CAU'))
        if status == 'LOI':
            h['loi'] = {'code': 'DEMO_HTTP_429', 'stage': 'EXPORT_XML', 'http_status': 429}
            self.m.update(trang_thai='PARTIAL', ly_do_partial=['XML_LOI'])
        self.ghi(self.run, self.m)

    @contextmanager
    def k2_gia(self, pn='DEMO', company_key='0000000002'):
        conn = KetNoiGia()
        service = object.__new__(HoaDonK2)  # __init__ cần psycopg; mọi đường nhận vẫn dùng code thật
        service.conn_chu, service.root = conn, self.root
        service.danh_tinh = lambda actor: {'id': 'DEMO_USER', 'dang_nhap': 'DEMO_ACTOR'}
        service.hom_nay = lambda: __import__('datetime').date(2026, 10, 24)
        profile = {'reference_id': PROFILE_REF, 'sha256': '1' * 64, 'payload': {
            'module': 'M2', 'profile_document_sha256': PROFILE_DOCUMENT_SHA256,
            'identity_profile': {'ref': IDENTITY_PROFILE_REF},
            'coverage_values': ['COMPLETE_INPUT', 'PARTIAL_INPUT'],
            'artifact_roles': [{'role': 'NATIVE', 'required': True, 'allowed_media_types': ['application/xml']},
                               {'role': 'CROSSWALK', 'required': False, 'media_type': 'application/json'}]}}
        scope = {'scope_ref': 'DEMO', 'scope_kind': 'INVOICE_SET', 'company_keys': [company_key],
                 'sections': ['XML_HEADER', 'XML_LINE']}

        def stage(c, dt, **kw):
            sid = str(len(conn.stages) + 1)
            conn.stages[sid] = {'du': kw['du_lieu'], 'key': kw['client_key'], 'h': kw['h']}
            return sid

        def final(c, sid, h, snapshot_moi, promote):
            s = conn.stages[sid]
            v = {'stage_id': sid, 'snapshot_moi': snapshot_moi, 'promote': {'items': s['items']}}
            conn.receipts[s['key']] = {'id': s['du']['receipt_id'], 'capture_sha256': h,
                                       'ket_qua': s['du']['ket_qua'], 'ket_qua_cuoi': v}
            return v

        with ExitStack() as stack:
            for target, name, value in (
                (nguon_chung, 'doc_profile', lambda *a: profile),
                (nguon_chung, 'doc_pham_vi', lambda *a: scope),
                (nguon_chung, 'tim_lan_nhan', lambda c, inst, prof, key: conn.receipts.get(key)),
                (nguon_chung, 'ghi_blob', lambda *a: None),
                (nguon_chung, 'ghi_stage', stage),
                (nguon_chung, 'tieu_thu_capture', lambda *a: {'moi': True, 'snapshot_moi': True}),
                (nguon_chung, 'chot_ket_qua', final),
                (service, '_cong_ty', lambda *a: ({company_key: {
                    'fact': CompanyFact(company_key, pn, 'DEMO_MAPPING', 1, 'DEMO'),
                    'mapping_id': 'DEMO_MAPPING', 'phap_nhan_id': 'DEMO_ID'}}, [])),
                (service, '_don_vi', lambda *a: (None, 'DON_VI_CHUA_KHAI_BAO')),
            ):
                stack.enter_context(patch.object(target, name, side_effect=value))
            stack.enter_context(patch('kho_tri_thuc.k2.hoa_don.quyen.kiem_nguon'))
            yield service, conn

    def test_03_replay_cung_manifest_khong_them_ban_ghi(self):
        p = self.plan()
        self.assertEqual(self.plan(), p)
        self.assertEqual(len(p['muc']), 1)
        with self.k2_gia() as (service, conn):
            a = self.nhan(p, service)
            dem = (len(conn.stages), len(conn.receipts), len(conn.identities), len(conn.observations))
            b = self.nhan(p, service)
            self.assertEqual(dem, (len(conn.stages), len(conn.receipts), len(conn.identities), len(conn.observations)))
            self.assertEqual(dem, (1, 1, 1, 1))
            self.assertFalse(a['ket_qua'][0]['lap_lai'])
            self.assertTrue(b['ket_qua'][0]['lap_lai'])
            b['ket_qua'][0]['lap_lai'] = False
            self.assertEqual(a, b)
            self.assertTrue(any('kho.m2_tieu_thu_quan_sat' in s for s in conn.calls))

    def test_03_hai_run_khac_noi_dung_thanh_revision_qua_consumer_gia(self):
        tep_cu = self.run / self.m['hoa_don'][0]['file_xml']
        raw_cu = tep_cu.read_bytes()
        run2, _ = self.tao_run('20261024-130000', xml_demo(gia='13.5'))
        with self.k2_gia() as (service, conn):
            self.nhan(self.plan(), service)
            r = self.nhan(self.plan(run2), service)
            self.assertEqual(len(conn.identities), 1)
            self.assertEqual(len(next(iter(conn.identities.values()))), 2)
            self.assertEqual(r['ket_qua'][0]['items'][0]['classification'], ['CHANGED_CONTENT_HOLD'])
        self.assertEqual(tep_cu.read_bytes(), raw_cu)

    def test_03_hai_run_cung_hash_them_quan_sat_khong_them_identity(self):
        run2, _ = self.tao_run('20261024-130000')
        with self.k2_gia() as (service, conn):
            self.nhan(self.plan(), service)
            r = self.nhan(self.plan(run2), service)
            self.assertEqual(len(conn.identities), 1)
            self.assertEqual(len(conn.observations), 2)
            self.assertEqual(len(next(iter(conn.identities.values()))), 1)
            self.assertEqual(r['ket_qua'][0]['items'][0]['classification'], ['SAME_CONTENT_REPEAT'])

    def test_03_doi_tthai_luu_raw_khong_gia_revision_k2(self):
        run2, m = self.tao_run('20261024-130000')
        m['hoa_don'][0]['tthai_cong'] = '009'
        self.ghi(run2, m)
        p = self.plan(run2)
        self.assertEqual(p['muc'][0]['tthai_cong'], '009')
        with self.k2_gia() as (service, conn):
            self.nhan(self.plan(), service)
            r = self.nhan(p, service)
            self.assertIn('K2_CHUA_REVISION_TTHAI_CONG', r['khoang_thieu_k2'])
            cw = conn.stages['2']['du']['rows'][-1]
            self.assertEqual(cw['section'], 'CROSSWALK')
            self.assertEqual(len(next(iter(conn.identities.values()))), 1)

    def test_03_hash_bytes_doi_nhung_semantic_giu_nguyen_bao_khoang_thieu(self):
        run2, _ = self.tao_run('20261024-130000', xml_demo().replace(b'<HDon>', b'<HDon>\n'))
        with self.k2_gia() as (service, conn):
            self.nhan(self.plan(), service)
            r = self.nhan(self.plan(run2), service)
            self.assertEqual(len(next(iter(conn.identities.values()))), 1)
            self.assertIn('K2_REVISION_THEO_SEMANTIC_KHONG_THEO_HASH_BYTES', r['khoang_thieu_k2'])

    def hoi_cuu_ngoai_run(self):
        """Chuyển run DEMO sang HOI_CUU: XML/PDF/bảng kê để tại chỗ ở thư mục dữ liệu cũ (đường dẫn tuyệt đối). Trả (thư mục cũ, gốc tin cậy nằm trong nó)."""
        cu = self.root / 'nguon-cu'
        goc = cu / 'goc'
        goc.mkdir(parents=True)
        h, bk = self.m['hoa_don'][0], self.m['tong']['bang_ke']
        for ten in (h['file_xml'], h['file_pdf'], bk['file']):
            (goc / ten).write_bytes((self.run / ten).read_bytes())
        h['file_xml'] = h['xml_tep'][0]['file'] = str(goc / h['file_xml'])
        h['file_pdf'] = str(goc / h['file_pdf'])
        bk.update(file=str(goc / bk['file']), so_cot=15)
        self.m.update(nguon='HOI_CUU', xap_xi=True, thu_muc_tep_goc=str(goc))
        self.ghi(self.run, self.m)
        return cu, goc

    def test_nhan_vao_k2_truyen_goc_hoi_cuu_tin_cay_xuong_lan_lap_lai(self):
        cu, goc = self.hoi_cuu_ngoai_run()
        p = lap_ke_hoach_nhan(self.run, ma_phap_nhan='DEMO', goc_hoi_cuu_tin_cay=goc)
        # manifest đổi giữa hai lần đọc: khai gốc rộng hơn (cha của gốc tin cậy). Đường dẫn tệp không đổi, thư mục cha không thêm tệp lạ
        # → lần lập lại KHÔNG kiểm gốc vẫn ra đúng kế hoạch cũ (đó là lỗ hổng của gốc None).
        self.m['thu_muc_tep_goc'] = str(cu)
        self.ghi(self.run, self.m)
        khong_goc = lap_ke_hoach_nhan(self.run, ma_phap_nhan='DEMO')
        bo_hash = lambda k: {a: b for a, b in k.items() if a != 'manifest_sha256'}  # noqa: E731
        self.assertEqual(bo_hash(khong_goc), bo_hash(p))  # chỉ hash manifest.json khác: gốc None không phát hiện đổi gốc
        self.assertNotEqual(khong_goc['manifest_sha256'], p['manifest_sha256'])
        service = Mock()
        service.nhan_theo_manifest.return_value = {'lan_tiep_nhan_id': 'DEMO_RECEIPT', 'lap_lai': False, 'promote': {'items': []}}
        with self.assertRaises(DataError) as ctx:
            nhan_vao_k2(p, service, actor='DEMO_ACTOR', source_instance='DEMO', scope_ref='DEMO', goc_hoi_cuu_tin_cay=goc)
        self.assertEqual(ctx.exception.code, 'M2_00_MANIFEST_HOI_CUU_GOC_KHONG_TIN_CAY')
        service.nhan_theo_manifest.assert_not_called()
        with self.assertRaises(DataError) as ctx:  # không truyền gốc: hash manifest.json trong kế hoạch vẫn chặn bản manifest đã đổi
            nhan_vao_k2(p, service, actor='DEMO_ACTOR', source_instance='DEMO', scope_ref='DEMO')
        self.assertEqual(ctx.exception.code, 'M2_00_NHAN_KE_HOACH_DA_DOI')
        (self.root / 'khac').mkdir()
        for danh_sach in ([goc], str(goc), (self.root / 'khac', goc)):  # nhiều gốc hoặc một chuỗi: chỉ cần gốc khai trong manifest nằm trong một gốc tin cậy
            with self.subTest(goc=danh_sach):
                self.m['thu_muc_tep_goc'] = str(goc)
                self.ghi(self.run, self.m)
                nhan_vao_k2(p, service, actor='DEMO_ACTOR', source_instance='DEMO', scope_ref='DEMO', goc_hoi_cuu_tin_cay=danh_sach)
        self.assertEqual(service.nhan_theo_manifest.call_count, 3)

    def test_lap_lai_day_du_false_chi_so_hash_manifest_khong_lap_lai_ke_hoach(self):
        p = self.plan()
        self.assertRegex(p['manifest_sha256'], r'^[0-9a-f]{64}$')
        service = Mock()
        service.nhan_theo_manifest.return_value = {'lan_tiep_nhan_id': 'DEMO_RECEIPT', 'lap_lai': False, 'promote': {'items': []}}
        with patch('kho_tri_thuc.m2.tai_hoa_don.nhan.lap_ke_hoach_nhan', side_effect=AssertionError('không được lập lại kế hoạch trong khóa')) as lap:
            r = nhan_vao_k2(p, service, actor='DEMO_ACTOR', source_instance='DEMO', scope_ref='DEMO', lap_lai_day_du=False)
        lap.assert_not_called()
        service.nhan_theo_manifest.assert_called_once()
        self.assertEqual(r['ket_qua'][0]['trang_thai'], 'GIU_CHO_K2')  # items rỗng (Mock): chỉ kiểm đường đi, không kiểm K2

    def test_lap_lai_day_du_false_van_chan_manifest_doi_xml_doi_va_ke_hoach_gia(self):
        p = self.plan()
        service = Mock()
        service.nhan_theo_manifest.return_value = {'lan_tiep_nhan_id': 'DEMO_RECEIPT', 'lap_lai': False, 'promote': {'items': []}}

        def tu_choi(ke_hoach, ma):
            with self.assertRaises(DataError) as ctx:
                nhan_vao_k2(ke_hoach, service, actor='DEMO_ACTOR', source_instance='DEMO', scope_ref='DEMO', lap_lai_day_du=False)
            self.assertEqual(ctx.exception.code, 'M2_00_NHAN_' + ma)
            service.nhan_theo_manifest.assert_not_called()
        tu_choi({k: v for k, v in p.items() if k != 'manifest_sha256'}, 'KE_HOACH_DA_DOI')  # kế hoạch không do lap_ke_hoach_nhan lập
        tu_choi({**p, 'manifest_sha256': '0' * 64}, 'KE_HOACH_DA_DOI')
        bytes_cu = (self.run / 'manifest.json').read_bytes()
        (self.run / 'manifest.json').write_bytes(bytes_cu + b' ')  # manifest đổi sau khi lập kế hoạch (dù nghĩa không đổi)
        tu_choi(p, 'KE_HOACH_DA_DOI')
        (self.run / 'manifest.json').write_bytes(bytes_cu)
        xml = self.run / self.m['hoa_don'][0]['file_xml']
        xml_cu = xml.read_bytes()
        xml.write_bytes(xml_cu.replace(b'12.5', b'99.5'))  # XML đổi sau khi lập kế hoạch: hash từng XML vẫn kiểm ngay trước khi ghi
        tu_choi(p, 'XML_DOI_SAU_KIEM_HASH')
        xml.write_bytes(xml_cu)
        nhan_vao_k2(p, service, actor='DEMO_ACTOR', source_instance='DEMO', scope_ref='DEMO', lap_lai_day_du=False)
        service.nhan_theo_manifest.assert_called_once()

    def test_ke_hoach_ghi_hash_manifest_va_manifest_doi_trong_luc_doc_bi_tu_choi(self):
        h1 = (self.run / 'manifest.json').read_bytes()
        self.assertEqual(self.plan()['manifest_sha256'], sha256(h1))
        that = nhan_module.doc_manifest

        def doc_roi_doi(*a, **kw):  # kẻ ghi đè manifest NGAY SAU khi đọc xong
            kq = that(*a, **kw)
            (self.run / 'manifest.json').write_bytes(h1 + b' ')
            return kq
        with patch.object(nhan_module, 'doc_manifest', doc_roi_doi), self.assertRaises(DataError) as ctx:
            self.plan()
        self.assertEqual(ctx.exception.code, 'M2_00_NHAN_MANIFEST_DOI_TRONG_LUC_DOC')

    def test_04_khong_xml_goc_la_bang_ke_khong_phai_tai_loi(self):
        self.khong_xml('KHONG_XML_GOC')
        p = self.plan()
        self.assertEqual(p['muc'][0]['bang_chung'], 'BANG_KE')
        self.assertEqual(p['ngoai_le'], [])
        service = Mock()
        r = self.nhan(p, service)
        service.nhan_theo_manifest.assert_not_called()
        self.assertEqual(r['ket_qua'][0]['ly_do'], 'K2_CHUA_NHAN_BANG_KE')

    def test_04_khong_xml_goc_thieu_bang_ke_khong_gan_bang_chung(self):
        self.khong_xml('KHONG_XML_GOC')
        for status in ('KHONG_YEU_CAU', 'LOI'):
            with self.subTest(status=status):
                self.m['tong'].update(bang_ke_trang_thai=status, bang_ke=None)
                self.m.update(trang_thai='PARTIAL' if status == 'LOI' else 'COMPLETE',
                              ly_do_partial=['BANG_KE_LOI'] if status == 'LOI' else [])
                self.ghi(self.run, self.m)
                p = self.plan()
                self.assertEqual(p['muc'], [])
                self.assertIn({'ma': 'BANG_KE_THIEU', 'item_ordinal': 1}, p['ngoai_le'])
                service = Mock()
                self.nhan(p, service)
                service.nhan_theo_manifest.assert_not_called()

    def test_04_bang_ke_hash_lech_van_dung_run(self):
        self.khong_xml('KHONG_XML_GOC')
        (self.run / self.m['tong']['bang_ke']['file']).write_bytes(b'DEMO_HASH_LECH')
        service = Mock()
        with self.assertRaises(DataError) as ctx:
            self.nhan(self.plan(), service)
        self.assertEqual(ctx.exception.code, 'M2_00_MANIFEST_HASH_LECH')
        service.nhan_theo_manifest.assert_not_called()

    def test_05_loi_tai_vao_ngoai_le_khong_vao_k2(self):
        self.khong_xml('LOI')
        p = self.plan()
        self.assertEqual(p['muc'], [])
        self.assertEqual(p['ngoai_le'][0]['ma'], 'TAI_LOI')
        self.assertEqual(p['ngoai_le'][0]['loi']['http_status'], 429)
        service = Mock()
        self.nhan(p, service)
        service.nhan_theo_manifest.assert_not_called()

    def test_05_nhom_bo_qua_va_loi_chung_khong_bi_bo_im_lang(self):
        e = {'code': 'DEMO_ZIP_HONG', 'stage': 'ZIP', 'http_status': None}
        self.m['nhom'][0].update(trang_thai='LOI', so_ban_ghi=None, so_moi=None, loi=e)
        self.m.update(loi_chung=[e], trang_thai='PARTIAL', ly_do_partial=['NHOM_LOI', 'LOI_CHUNG'])
        self.ghi(self.run, self.m)
        p = self.plan()
        self.assertEqual({e['ma'] for e in p['ngoai_le']}, {'TAI_LOI_NHOM', 'TAI_LOI_CHUNG', 'RUN_PARTIAL'})
        self.assertEqual(p['coverage'], 'PARTIAL_INPUT')

    def test_run_chi_complete_moi_khai_du_dau_vao(self):
        for status in ('COMPLETE', 'FAILED', 'PARTIAL'):
            with self.subTest(status=status):
                co_loi = status in ('FAILED', 'PARTIAL')
                self.m.update(trang_thai=status, ly_do_partial=['LOI_CHUNG'] if co_loi else [],
                              loi_chung=[{'code': 'DEMO_LIST_LOI', 'stage': 'LIST',
                                          'http_status': 500}] if co_loi else [])
                self.ghi(self.run, self.m)
                p = self.plan()
                self.assertEqual(len(p['muc']), 1)
                self.assertEqual(p['coverage'], 'COMPLETE_INPUT' if status == 'COMPLETE' else 'PARTIAL_INPUT')
                if status != 'COMPLETE':
                    self.assertIn('RUN_' + status, [e['ma'] for e in p['ngoai_le']])
                service = Mock()
                service.nhan_theo_manifest.return_value = {
                    'lan_tiep_nhan_id': 'DEMO_RECEIPT', 'lap_lai': False, 'promote': {'items': []}}
                self.nhan(p, service)
                kw = service.nhan_theo_manifest.call_args.kwargs
                self.assertEqual(kw['coverage'], p['coverage'])
                if status != 'COMPLETE':
                    self.assertIn('RUN_' + status, kw['reported_errors'])

    def test_10_file_ngoai_manifest_chua_ro_nguon_khong_de_xuat(self):
        for ten in ('NGOAI_DEMO.xml', 'NGOAI_DEMO.pdf', 'NGOAI_DEMO.xlsx', 'NGOAI_DEMO.txt'):
            (self.run / ten).write_bytes(b'DEMO')
        p = self.plan()
        self.assertEqual(len(p['muc']), 1)
        self.assertEqual(len(p['chua_ro_nguon']), 4)
        self.assertTrue(all(not f['vao_de_xuat'] for f in p['chua_ro_nguon']))

    def test_thieu_khoa_vao_ngoai_le_khong_vao_k2(self):
        h = self.m['hoa_don'][0]
        h['key_raw']['shdon'] = None
        h.update(key_canonical='0000000001|1|DEMO|', key_thieu=['shdon'])
        self.ghi(self.run, self.m)
        p = self.plan()
        self.assertEqual(p['muc'], [])
        self.assertEqual(p['ngoai_le'][0]['ma'], 'THIEU_KHOA')

    def test_identity_tu_key_khong_tu_ten_tep_va_giu_raw(self):
        p = self.plan()['muc'][0]
        self.assertEqual(p['identity'], ['DEMO', 'MUA_VAO', '0000000001', '1', 'DEMO', '1'])
        self.assertEqual(p['key_raw']['shdon'], '000001')

    def test_manifest_hoi_cuu_doc_tai_thu_muc_chieu_cu_khong_di_chuyen(self):
        run = self.root / 'DEMO_CU' / '2026-10' / 'mua_vao'
        run.mkdir(parents=True)
        m = tao_run_demo(run)
        self.doi_xml(run, m, xml_demo())
        m.update(nguon='HOI_CUU', xap_xi=True)
        self.ghi(run, m)
        p = self.plan(run)
        self.assertEqual(p['nguon'], 'HOI_CUU')
        self.assertTrue(p['xap_xi'])
        self.assertEqual(p['muc'][0]['identity'][1], 'MUA_VAO')

    def test_identity_xml_khac_manifest_la_ngoai_le(self):
        self.doi_xml(self.run, self.m, xml_demo(so='000002'))
        self.ghi(self.run, self.m)
        p = self.plan()
        self.assertEqual(p['muc'], [])
        self.assertEqual(p['ngoai_le'][0]['ma'], 'IDENTITY_XML_MANIFEST_KHAC')

    def test_so_hoa_don_bo_so_0_dau_khi_so_khop_nhung_giu_raw(self):
        h = self.m['hoa_don'][0]
        h['key_raw']['shdon'] = '1'
        h['key_canonical'] = '0000000001|1|DEMO|1'
        self.ghi(self.run, self.m)
        p = self.plan()
        self.assertEqual(p['ngoai_le'], [])
        self.assertEqual(p['muc'][0]['key_raw']['shdon'], '1')
        self.assertEqual(p['muc'][0]['identity'][-1], '1')
        self.assertIn(b'<SHDon>000001</SHDon>', (self.run / h['file_xml']).read_bytes())
        with self.k2_gia() as (service, conn):
            r = self.nhan(p, service)
            self.assertEqual(r['ket_qua'][0]['trang_thai'], 'DA_GHI_QUAN_SAT')
            self.assertEqual(len(conn.identities), 1)
        self.doi_xml(self.run, self.m, xml_demo(so='000002'))
        self.ghi(self.run, self.m)
        p = self.plan()
        self.assertEqual(p['muc'], [])
        self.assertEqual(p['ngoai_le'][0]['ma'], 'IDENTITY_XML_MANIFEST_KHAC')

    def test_phap_nhan_profile_va_chieu_thu_muc_phai_khop(self):
        with self.assertRaises(DataError):
            lap_ke_hoach_nhan(self.run, ma_phap_nhan='DEMO_KHAC')
        self.m.update(chieu='sold', thu_muc_chieu='ban_ra')
        self.ghi(self.run, self.m)
        with self.assertRaises(DataError):
            self.plan()

    def test_registry_k2_dan_xuat_khac_identity_bi_chan_truoc_stage(self):
        with self.k2_gia(pn='DEMO_KHAC') as (service, conn):
            r = self.nhan(self.plan(), service)
            self.assertEqual(r['ket_qua'][0]['trang_thai'], 'GIU_CHO_K2')
            self.assertEqual(r['ket_qua'][0]['ly_do'], 'M2_MANIFEST_IDENTITY_KHAC')
            self.assertEqual(r['giu_cho_k2'], r['ket_qua'])
            self.assertEqual(conn.stages, {})

    def test_loi_mot_muc_giu_cho_va_tiep_tuc_nhan_muc_sau(self):
        h = copy.deepcopy(self.m['hoa_don'][0])
        raw = xml_demo(so='000002')
        h['key_raw']['shdon'] = '000002'
        h.update(item_ordinal=2, key_canonical='0000000001|1|DEMO|000002',
                 file_xml='DEMO_2.xml', hash_xml=sha256(raw), xml_bytes=len(raw))
        h['xml_tep'][0].update(file=h['file_xml'], sha256=sha256(raw), bytes=len(raw))
        (self.run / h['file_xml']).write_bytes(raw)
        self.m['hoa_don'].append(h)
        self.m['tong'].update(tong_hd=2, xml_ok=2, pdf_ok=2)
        self.m['nhom'][0].update(so_ban_ghi=2, so_moi=2)
        self.ghi(self.run, self.m)
        for code in ('M2_MANIFEST_IDENTITY_KHAC', 'CAPTURE_KHAC_NOI_DUNG'):
            with self.subTest(code=code), self.k2_gia() as (service, conn):
                nhan_that = service.nhan_theo_manifest

                def nhan_tung_muc(*args, **kw):
                    if kw['identity'][-1] == '1':
                        raise DataError(code, 'DEMO giữ chờ kiểm tra mục 1.')
                    return nhan_that(*args, **kw)

                with patch.object(service, 'nhan_theo_manifest', side_effect=nhan_tung_muc) as call:
                    r = self.nhan(self.plan(), service)
                self.assertEqual(call.call_count, 2)
                self.assertEqual(r['ket_qua'][0], {
                    'item_ordinal': 1, 'file': self.m['hoa_don'][0]['file_xml'],
                    'trang_thai': 'GIU_CHO_K2', 'ly_do': code,
                    'thong_bao': 'DEMO giữ chờ kiểm tra mục 1.'})
                self.assertEqual(r['giu_cho_k2'], [r['ket_qua'][0]])
                self.assertEqual(r['ket_qua'][1]['item_ordinal'], 2)
                self.assertEqual(r['ket_qua'][1]['trang_thai'], 'DA_GHI_QUAN_SAT')
                self.assertEqual(len(conn.observations), 1)

    def test_ban_ra_giu_ung_vien_nguon_khong_tao_nghiep_vu_m2(self):
        run, _ = self.tao_run('20261024-130000', chieu='sold')
        p = self.plan(run)
        self.assertEqual(p['muc'][0]['identity'][1], 'BAN_RA')
        with self.k2_gia(company_key='0000000001') as (service, conn):
            r = self.nhan(p, service)
            self.assertEqual(conn.identities, {})
            self.assertEqual(len(conn.stages), 1)
            self.assertEqual(r['ket_qua'][0]['trang_thai'], 'GIU_CHO_K2')

    def test_pham_vi_khong_khop_khong_goi_k2(self):
        service = Mock()
        with self.assertRaises(DataError):
            nhan_vao_k2(self.plan(), service, actor='DEMO_ACTOR', source_instance='DEMO_KHAC', scope_ref='DEMO')
        service.nhan_theo_manifest.assert_not_called()

    def test_policy_thieu_dvtte_vnd_chi_la_de_xuat(self):
        raw = xml_demo(tien='')
        self.doi_xml(self.run, self.m, raw)
        self.ghi(self.run, self.m)
        p = self.plan()
        tien = p['muc'][0]['tien_te']
        self.assertEqual(tien['trang_thai'], 'DE_XUAT')
        self.assertEqual(tien['de_xuat_tien_te'], 'VND')
        self.assertTrue(tien['co_theo_policy'])
        self.assertEqual(tien['ma_policy'], 'POLICY-TIENTE-01')
        self.assertEqual((self.run / self.m['hoa_don'][0]['file_xml']).read_bytes(), raw)
        with self.k2_gia() as (service, conn):
            r = self.nhan(p, service)
            self.assertEqual(r['ket_qua'][0]['trang_thai'], 'GIU_CHO_K2')
            self.assertEqual(conn.identities, {})

    def test_policy_tgia_ngoai_te_chua_ro_va_mau_thuan_conflict(self):
        for tien, them, bk, state in (('', '<TGia>25000</TGia>', None, 'CHUA_RO'),
                                     ('<DVTTe>VND</DVTTe>', '', 'USD', 'XUNG_DOT'),
                                     ('<DVTTe/>', '', None, 'CHUA_RO')):
            with self.subTest(state=state, tien=tien):
                self.doi_xml(self.run, self.m, xml_demo(tien=tien, them=them))
                self.m['hoa_don'][0]['dvtte_cong'] = bk
                self.ghi(self.run, self.m)
                p = self.plan()
                self.assertEqual(p['muc'][0]['tien_te']['trang_thai'], state)
                self.assertIn('TIEN_TE_' + state, [e['ma'] for e in p['ngoai_le']])
                service = Mock()
                r = self.nhan(p, service)
                service.nhan_theo_manifest.assert_not_called()
                self.assertEqual(r['ket_qua'][0]['trang_thai'], 'GIU_CHO_K2')

    def test_quan_he_co_can_cu_khong_gop_so_tien(self):
        them = ('<TTHDLQuan><TCHDon>2</TCHDon><KHMSHDCLQuan>1</KHMSHDCLQuan>'
                '<KHHDCLQuan>DEMO_CU</KHHDCLQuan><SHDCLQuan>000003</SHDCLQuan></TTHDLQuan>')
        self.doi_xml(self.run, self.m, xml_demo(them=them))
        self.ghi(self.run, self.m)
        h = self.plan()['muc'][0]
        self.assertEqual(h['quan_he'][0]['raw']['TCHDon'], '2')
        self.assertNotIn('so_tien', h)
        self.assertIn('UNSUPPORTED_ELEMENT', h['issues_xml'])

    def test_quan_he_thieu_can_cu_khong_suy_tu_tthai(self):
        self.doi_xml(self.run, self.m, xml_demo(them='<TTHDLQuan><TCHDon>2</TCHDon></TTHDLQuan>'))
        self.ghi(self.run, self.m)
        p = self.plan()
        self.assertEqual(p['muc'][0]['quan_he'], [])
        self.assertIn('QUAN_HE_CHUA_RO', [e['ma'] for e in p['ngoai_le']])

    def test_hash_lech_tu_choi_dung_file(self):
        ten = self.m['hoa_don'][0]['file_xml']
        (self.run / ten).write_bytes(b'DEMO_HASH_LECH')
        with self.assertRaises(DataError) as ctx:
            self.plan()
        self.assertEqual(ctx.exception.code, 'M2_00_MANIFEST_HASH_LECH')
        self.assertEqual(ctx.exception.locator, ten)

    def test_ke_hoach_bi_sua_khong_duoc_nhan(self):
        p = self.plan()
        p['muc'][0]['tthai_cong'] = 999
        service = Mock()
        with self.assertRaises(DataError):
            self.nhan(p, service)
        service.nhan_theo_manifest.assert_not_called()

    def test_file_doi_sau_lap_ke_hoach_bi_chan(self):
        p = self.plan()
        self.doi_xml(self.run, self.m, xml_demo(gia='999'))
        self.ghi(self.run, self.m)
        service = Mock()
        with self.assertRaises(DataError):
            self.nhan(p, service)
        service.nhan_theo_manifest.assert_not_called()

    def test_credential_khong_co_trong_ket_qua_stdout_stderr(self):
        secret = 'DEMO_CREDENTIAL_KHONG_DUOC_LO'
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            p = self.plan()
            service = Mock()
            service.nhan_theo_manifest.return_value = {
                'lan_tiep_nhan_id': 'DEMO_RECEIPT', 'lap_lai': False, 'promote': {'items': []},
                'password': secret, 'log': secret}
            r = self.nhan(p, service)
        self.assertNotIn(secret, json.dumps([p, r], ensure_ascii=False) + out.getvalue() + err.getvalue())
        self.assertNotIn('native', p)

    def test_credential_manifest_bi_tu_choi_khong_phan_chieu(self):
        secret = 'DEMO_CREDENTIAL_KHONG_DUOC_LO'
        self.m['password'] = secret
        self.ghi(self.run, self.m)
        with self.assertRaises(DataError) as ctx:
            self.plan()
        self.assertEqual(ctx.exception.code, 'M2_00_MANIFEST_CO_BI_MAT')
        self.assertNotIn(secret, str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
