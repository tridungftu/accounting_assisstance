"""XS-4c2: Handler trực tiếp, kiểm tĩnh và PG tùy chọn trên CSDL giả mới.

PG chỉ dùng KHO_PG_DSN_TEST; giữ CSDL cho lead, không có thao tác xóa.
"""

import ast
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import re
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

from kho_tri_thuc.giao_dien import module_cong_tac as http
from kho_tri_thuc.giao_dien.server import Handler
from kho_tri_thuc.ha_tang.primitives import DataError

try:
    import psycopg
except ImportError:
    psycopg = None

ROOT = Path(__file__).resolve().parents[1]
DSN = os.environ.get('KHO_PG_DSN_TEST')
PN_A = '00000000-0000-0000-0000-000000000001'
PN_B = '00000000-0000-0000-0000-000000000002'
TESTER = '00000000-0000-0000-0000-000000000003'
LOGIN = 'MO_PHONG_XS4C2_PHIEN'
CATALOG = ('CRM', 'M2', 'M4', 'M0', 'M3', 'M9', 'M10')
FLAGS = {
    PN_A: {'che_do': 'THU', 'revision': 4, 'hien_luoi': True, 'cho_xem': True,
           'cho_ghi': True, 'cho_xuat_ngoai': False, 'cong_bo_chinh_thuc': False,
           'dai_dang_thu': True},
    PN_B: {'che_do': 'TAT', 'revision': 2, 'hien_luoi': False, 'cho_xem': True,
           'cho_ghi': False, 'cho_xuat_ngoai': False, 'cong_bo_chinh_thuc': False,
           'dai_dang_thu': False},
}
FLAGS_TAT = {'che_do': 'TAT', 'revision': 0, 'hien_luoi': False, 'cho_xem': True,
             'cho_ghi': False, 'cho_xuat_ngoai': False, 'cong_bo_chinh_thuc': False,
             'dai_dang_thu': False}


class Rows(list):
    def fetchone(self):
        return self[0] if self else None


class ModuleHttpTests(unittest.TestCase):
    def setUp(self):
        self.app = SimpleNamespace(mutation_lock=threading.Lock(), token='TOKEN-DEMO-XS4C2',
                                   CRM_COOKIE='CRM_DEMO', is_that=False)
        self.app.crm_phien = Mock(return_value=('sid-demo', LOGIN, False))
        self.app._crm_db = Mock(side_effect=lambda fn, *a: fn(*a))
        self.admin = True
        self.allowed = [PN_A, PN_B]
        self.catalog = set(CATALOG)
        self.error = None
        self.events = []
        self.conn = SimpleNamespace(execute=Mock(side_effect=self.sql))
        self.mau = SimpleNamespace(danh_tinh=Mock(return_value={
            'id': TESTER, 'dang_nhap': LOGIN, 'vai_tro': 'KE_TOAN'}), _tx=self.tx)
        self.svc = http._CongTacHttpK2(self.mau)
        self.factory = Mock(side_effect=self.service)
        self.route_patch = patch.object(http, 'dich_vu', self.factory)
        self.route_patch.start()
        self.addCleanup(self.route_patch.stop)

    @contextmanager
    def tx(self, dt, **kw):
        self.assertTrue(self.app.mutation_lock.locked())
        self.assertEqual(dt['dang_nhap'], LOGIN)
        self.events.append('begin')
        try:
            yield self.conn
        except Exception:
            self.events.append('rollback')
            raise
        else:
            self.events.append('commit')

    @contextmanager
    def service(self, app):
        self.assertIs(app, self.app)
        self.assertTrue(app.mutation_lock.locked())
        yield self.svc

    def deny(self, code):
        exc = RuntimeError('Chi tiết SQL không được trả về')
        exc.diag = SimpleNamespace(message_primary=code + ': riêng tư')
        raise exc

    def sql(self, sql, args=()):
        if sql == 'SET TRANSACTION READ ONLY':
            return Rows()
        if 'FROM master.phap_nhan' in sql:
            self.assertIn('p.id IN (SELECT master.ktt_pn_cho_phep())', sql)
            self.assertNotIn('master.ktt_duoc', sql)
            self.assertNotIn('master.ktt_co_vai', sql)
            self.assertEqual(args, ())
            return Rows([{'id': UUID(pn), 'ten': 'Pháp nhân giả ' + pn[-1]}
                         for pn in self.allowed])
        if sql.startswith('SELECT master.module_trang_thai('):
            return Rows([{'r': dict(FLAGS[args[1]] if args[0] in self.catalog else FLAGS_TAT)}])
        if 'master.module_' in sql:
            if not self.admin:
                self.deny('MODULE_CHI_ADMIN')
            if self.error:
                self.deny(self.error)
            if args[0] not in self.catalog:
                self.deny('MODULE_DAU_VAO')
            if 'module_doi_che_do' in sql:
                if args[-1] != FLAGS[args[1]]['revision']:
                    self.deny('MODULE_REVISION')
                return Rows([{'r': args[-1] + 1}])
            if 'module_danh_sach_nguoi_thu' in sql:
                return Rows([{'id': TESTER, 'module': args[0], 'phap_nhan_id': args[1],
                              'nguoi_dung_id': TESTER, 'thu_hoi_luc': None}])
            if 'module_cap_nguoi_thu' in sql or 'module_thu_hoi_nguoi_thu' in sql:
                return Rows([{'r': UUID(TESTER)}])
        self.fail('SQL ngoài phạm vi test: ' + sql)

    def handler(self, path, body=None):
        h = Handler.__new__(Handler)
        h.path = path
        h.server = SimpleNamespace(app=self.app, server_port=8765)
        raw = json.dumps(body).encode('utf-8') if body is not None else b''
        h.headers = {'Host': '127.0.0.1:8765', 'X-KTT-Token': self.app.token,
                     'Cookie': 'CRM_DEMO=sid-demo', 'Content-Length': str(len(raw))}
        h.rfile, h.wfile = io.BytesIO(raw), io.BytesIO()
        h.send_response, h.send_header, h.end_headers = Mock(), Mock(), Mock()
        return h

    def call(self, path='trang-thai?module=CRM', body=None, *, post=False, direct=False):
        h = self.handler(http.PREFIX + path, body)
        if direct:
            u = urlsplit(h.path)
            http.dieu_huong(h, self.app, post, u.path, parse_qs(u.query))
        else:
            (h.do_POST if post else h.do_GET)()
        self.assertFalse(self.app.mutation_lock.locked())
        h.send_header.assert_any_call('Cache-Control', 'no-store')
        return h.send_response.call_args.args[0], json.loads(h.wfile.getvalue())

    def command(self, **kw):
        return {'module': 'CRM', 'phap_nhan_id': PN_B, 'che_do': 'THU',
                'ly_do': 'Thử dữ liệu giả', 'revision': 2, **kw}

    def tester(self, **kw):
        return {'module': 'CRM', 'phap_nhan_id': PN_B, 'nguoi_dung_id': TESTER,
                'ly_do': 'Thử dữ liệu giả', **kw}

    def test_trang_thai_danh_sach_pn_va_day_du_co(self):
        self.admin = False
        status, rows = self.call()
        self.assertEqual(status, 200)
        self.assertEqual(rows, [{**FLAGS[pn], 'phap_nhan_id': pn,
                                'ten_phap_nhan': 'Pháp nhân giả ' + pn[-1]} for pn in self.allowed])
        self.app.crm_phien.assert_called_once_with('sid-demo')
        self.mau.danh_tinh.assert_called_with(LOGIN)

    def test_khong_tra_pn_ngoai_pham_vi(self):
        self.admin = False
        self.allowed = [PN_B]
        status, rows = self.call()
        self.assertEqual(status, 200)
        self.assertEqual([r['phap_nhan_id'] for r in rows], [PN_B])
        calls = [c.args[1] for c in self.conn.execute.call_args_list if 'module_trang_thai(' in c.args[0]]
        self.assertEqual(calls, [('CRM', PN_B)])

    def test_du_an_co_m4_tai_pn_a_doc_trang_thai(self):
        self.admin = False
        self.allowed = [PN_A]
        self.mau.danh_tinh.return_value['vai_tro'] = 'DU_AN'
        status, rows = self.call('trang-thai?module=M4')
        self.assertEqual(status, 200)
        self.assertEqual(rows, [{**FLAGS[PN_A], 'phap_nhan_id': PN_A,
                                'ten_phap_nhan': 'Pháp nhân giả 1'}])
        self.conn.execute.assert_any_call(
            'SELECT master.module_trang_thai(%s,%s::uuid) AS r', ('M4', PN_A))

    def test_pham_vi_pn_khong_loc_theo_module(self):
        self.admin = False
        self.allowed = [PN_A]
        self.mau.danh_tinh.return_value['vai_tro'] = 'DU_AN'
        for module in CATALOG:
            with self.subTest(module=module):
                status, rows = self.call('trang-thai?module=' + module)
                self.assertEqual(status, 200)
                self.assertEqual([r['phap_nhan_id'] for r in rows], [PN_A])

    def test_khong_co_pn_tra_danh_sach_rong(self):
        self.admin = False
        self.allowed = []
        self.assertEqual(self.call(), (200, []))
        self.assertFalse(any('module_trang_thai(' in c.args[0]
                             for c in self.conn.execute.call_args_list))

    def test_module_tu_danh_muc_khong_hardcode_crm(self):
        for module in CATALOG:
            with self.subTest(module=module):
                self.assertEqual(self.call('trang-thai?module=' + module)[0], 200)
        self.catalog.add('MODULE_KHAI_BAO_MOI')
        self.allowed = []
        self.assertEqual(self.call('trang-thai?module=MODULE_KHAI_BAO_MOI'), (200, []))

    def test_get_module_chua_khai_bao_tra_tat_tu_ham_sql(self):
        self.admin = False
        status, rows = self.call('trang-thai?module=CHUA_KHAI_BAO')
        self.assertEqual(status, 200)
        self.assertEqual(rows, [{**FLAGS_TAT, 'phap_nhan_id': pn,
                                'ten_phap_nhan': 'Pháp nhân giả ' + pn[-1]}
                               for pn in self.allowed])
        self.conn.execute.assert_any_call(
            'SELECT master.module_trang_thai(%s,%s::uuid) AS r', ('CHUA_KHAI_BAO', PN_A))

    def test_query_sai_bi_chan_ke_ca_pn_rong_va_lap(self):
        queries = ('', '?module=CRM&phap_nhan_id=' + PN_A, '?module=CRM&phap_nhan_id=',
                   '?module=CRM&module=', '?module=', '?module=crm', '?module=CRM-M2',
                   '?module=CR%20M', '?module=CRM%20', '?module=CRM%0A', '?module=%C4%90',
                   '?module=%20CRM', '?module=CRM&actor=gia', '?module=' + '&x=1' * 11)
        for route in ('trang-thai', 'nguoi-thu'):
            for empty in (False, True):
                self.allowed = [] if empty else [PN_A, PN_B]
                for query in queries:
                    with self.subTest(route=route, empty=empty, query=query):
                        self.assertEqual(self.call(route + query)[0], 400)
        self.conn.execute.assert_not_called()

    def test_query_pn_bi_chan_khi_goi_module_truc_tiep(self):
        self.assertEqual(self.call('trang-thai?module=CRM&phap_nhan_id=', direct=True)[0], 400)
        self.factory.assert_not_called()

    def test_admin_doi_pn_ngoai_quyen_nghiep_vu(self):
        self.allowed = [PN_A]
        self.assertEqual(self.call('che-do', self.command(), post=True), (200, {'revision': 3}))
        call = next(c for c in self.conn.execute.call_args_list if 'module_doi_che_do(' in c.args[0])
        self.assertEqual(call.args[1], ('CRM', PN_B, 'THU', 'Thử dữ liệu giả', 2))

    def test_khong_admin_403_va_khong_lo_chi_tiet(self):
        self.admin = False
        status, result = self.call('che-do', self.command(), post=True)
        self.assertEqual((status, result['error']), (403, 'MODULE_CHI_ADMIN'))
        self.assertEqual(result['message'], http._THONG_BAO['MODULE_CHI_ADMIN'])
        self.assertEqual(self.events[-1], 'rollback')

    def test_sai_revision_409(self):
        status, result = self.call('che-do', self.command(revision=0), post=True)
        self.assertEqual((status, result['error']), (409, 'MODULE_REVISION'))
        self.assertNotIn('MODULE_', result['message'])
        self.assertEqual(self.events[-1], 'rollback')

    def test_du_lieu_sai_400_truoc_sql(self):
        bad = [self.command(revision=x) for x in (True, -1, 2 ** 63, '2', None)]
        bad += [self.command(che_do='SAI'), self.command(ly_do=' '),
                self.command(phap_nhan_id='SAI'), self.command(actor='gia'),
                self.command(expected_revision=2)]
        bad += [self.command(module=module) for module in
                (' CRM', 'CRM ', 'CRM\n', 'CR M', 'crm', 'CRM-M2', 'Đ', '', None, 1, [])]
        p = self.command()
        p.pop('revision')
        bad += [p, {}, []]
        for payload in bad:
            with self.subTest(payload=payload):
                self.assertEqual(self.call('che-do', payload, post=True)[0], 400)
        self.conn.execute.assert_not_called()

    def test_post_module_la_400(self):
        status, result = self.call('che-do', self.command(module='SAI'), post=True)
        self.assertEqual((status, result['error']), (400, 'MODULE_DAU_VAO'))
        self.assertEqual(result['message'], http._THONG_BAO['MODULE_DAU_VAO'])
        self.assertTrue(any('module_doi_che_do(' in c.args[0] for c in self.conn.execute.call_args_list))
        self.assertEqual(self.events[-1], 'rollback')

    def test_post_khong_nhan_query(self):
        for route in http.POST:
            with self.subTest(route=route):
                self.assertEqual(self.call(route[len(http.PREFIX):] + '?phap_nhan_id=',
                                           self.command(), post=True)[0], 400)
        self.factory.assert_not_called()

    def test_nguoi_thu_cap_thu_hoi_chi_admin(self):
        for route in ('nguoi-thu/cap', 'nguoi-thu/thu-hoi'):
            for admin in (False, True):
                with self.subTest(route=route, admin=admin):
                    self.admin = admin
                    status, result = self.call(route, self.tester(), post=True)
                    self.assertEqual(status, 200 if admin else 403)
                    self.assertEqual(result.get('id'), TESTER if admin else None)

    def test_nguoi_thu_trong_pham_vi_pn_chi_admin(self):
        self.allowed = [PN_A]
        self.admin = False
        self.assertEqual(self.call('nguoi-thu?module=CRM')[0], 403)
        self.admin = True
        status, rows = self.call('nguoi-thu?module=CRM')
        self.assertEqual(status, 200)
        self.assertEqual([r['phap_nhan_id'] for r in rows], self.allowed)
        self.assertTrue(all(r['nguoi_dung_id'] == TESTER for r in rows))
        calls = [c.args[1] for c in self.conn.execute.call_args_list
                 if 'module_danh_sach_nguoi_thu(' in c.args[0]]
        self.assertEqual(calls, [('CRM', PN_A), ('CRM', PN_A)])

    def test_xem_nguoi_thu_khong_co_pn_tra_rong_khong_lo_thong_tin(self):
        self.allowed = []
        for admin in (False, True):
            with self.subTest(admin=admin):
                self.admin = admin
                self.assertEqual(self.call('nguoi-thu?module=CRM'), (200, []))
        self.assertFalse(any('module_danh_sach_nguoi_thu(' in c.args[0]
                             for c in self.conn.execute.call_args_list))

    def test_nguoi_thu_than_sai_400(self):
        for route in ('nguoi-thu/cap', 'nguoi-thu/thu-hoi'):
            for p in (self.tester(nguoi_dung_id='SAI'), self.tester(actor='gia'), self.tester(ly_do='')):
                with self.subTest(route=route, payload=p):
                    self.assertEqual(self.call(route, p, post=True)[0], 400)
        self.factory.assert_not_called()

    def test_loi_nghiep_vu_cau_tieng_viet(self):
        for code in ('MODULE_DAU_VAO', 'MODULE_CHUA_DU_DIEU_KIEN_GO_LIVE',
                     'MODULE_DA_CAP', 'MODULE_CHUA_CAP'):
            self.error = code
            with self.subTest(code=code):
                status, result = self.call('che-do', self.command(), post=True)
                self.assertEqual((status, result['error']), (400, code))
                self.assertEqual(result['message'], http._THONG_BAO[code])

    def test_csdl_chua_san_sang_503(self):
        for code in http.MA_503:
            self.factory.side_effect = DataError(code, 'Chi tiết hạ tầng ' + code)
            for post, path, body in ((False, 'trang-thai?module=CRM', None),
                                     (True, 'che-do', self.command())):
                with self.subTest(code=code, post=post):
                    status, result = self.call(path, body, post=post)
                    self.assertEqual((status, result['error']), (503, code))
                    self.assertNotIn(code, result['message'])
                    self.assertNotIn('Chi tiết', result['message'])

    def test_csdl_tu_choi_khong_lo_ma_trong_cau(self):
        self.app._crm_db.side_effect = DataError('CSDL_TU_CHOI', 'CSDL từ chối (CSDL_TU_CHOI).')
        status, result = self.call()
        self.assertEqual(status, 400)
        self.assertNotIn('CSDL_TU_CHOI', result['message'])

    def test_phien_khong_hop_le_403(self):
        self.app.crm_phien.side_effect = DataError('CRM_PHIEN', 'Phiên đã hết hạn.')
        self.assertEqual(self.call()[0], 403)
        self.factory.assert_not_called()

    def test_route_la_va_sai_method_404(self):
        for post, paths in ((False, ('la', 'che-do', 'nguoi-thu/cap')),
                            (True, ('la', 'trang-thai', 'nguoi-thu'))):
            for path in paths:
                with self.subTest(path=path, post=post):
                    self.assertEqual(self.call(path, post=post)[0], 404)
        self.factory.assert_not_called()

    def test_dispatch_truoc_khoa_va_giu_query(self):
        for post, path in ((False, 'trang-thai?module=CRM'), (True, 'che-do')):
            h = self.handler(http.PREFIX + path)

            def dispatch(handler, app, is_post, route, query):
                self.assertFalse(app.mutation_lock.locked())
                self.assertEqual((handler, app, is_post), (h, self.app, post))
                return handler.send_content(200, {'demo': True})

            with self.subTest(post=post), patch.object(http, 'dieu_huong', side_effect=dispatch) as fn:
                (h.do_POST if post else h.do_GET)()
                u = urlsplit(h.path)
                fn.assert_called_once_with(h, self.app, post, u.path, parse_qs(u.query))

    def test_dispatch_chi_dung_tien_to(self):
        for path in ('/api/cong-tac-module', '/api/cong-tac-module-khac/trang-thai',
                     '/api/cong-tac-moduleXYZ/trang-thai'):
            for post in (False, True):
                with self.subTest(path=path, post=post):
                    h = self.handler(path)
                    with patch.object(http, 'dieu_huong') as fn:
                        (h.do_POST if post else h.do_GET)()
                    fn.assert_not_called()
                    h.send_response.assert_called_once_with(404)

    def test_csrf_chan_truoc_module_moi_route(self):
        for post, paths in ((False, http.GET), (True, http.POST)):
            for path in paths:
                for invalid in ('token', 'origin'):
                    with self.subTest(path=path, post=post, invalid=invalid):
                        h = self.handler(path)
                        if invalid == 'token':
                            h.headers.pop('X-KTT-Token')
                        else:
                            h.headers['Origin'] = 'https://example.invalid'
                        with patch.object(http, 'dieu_huong') as fn:
                            (h.do_POST if post else h.do_GET)()
                        fn.assert_not_called()
                        h.send_response.assert_called_once_with(403)

    def test_module_tu_authorize_private(self):
        h = self.handler(http.PREFIX + 'trang-thai?module=CRM')
        h.authorize = Mock(side_effect=DataError('SESSION_TOKEN', 'Phiên đã đổi.'))
        http.dieu_huong(h, self.app, False, http.PREFIX + 'trang-thai', {'module': ['CRM']})
        h.authorize.assert_called_once_with(private=True)
        h.send_response.assert_called_once_with(403)
        self.factory.assert_not_called()


class FactoryTests(unittest.TestCase):
    table_read = re.compile(
        r'\b(?:FROM|JOIN)\s+(?:ONLY\s+)?master\.module_[A-Z0-9_]+\b(?!\s*\()',
        re.IGNORECASE)

    def test_mau_doc_bang_phan_biet_loi_goi_ham(self):
        for clause in ('FROM', 'JOIN'):
            for spacing in ('', ' ', '\n\t'):
                with self.subTest(clause=clause, spacing=spacing):
                    self.assertIsNone(self.table_read.search(
                        f'SELECT * {clause} master.module_danh_sach_nguoi_thu{spacing}(%s)'))
            for suffix in ('', ' AS m', '\nWHERE true'):
                with self.subTest(clause=clause, suffix=suffix):
                    self.assertIsNotNone(self.table_read.search(
                        f'SELECT * {clause} master.module_nguoi_thu{suffix}'))

    def test_http_va_dich_vu_khong_select_truc_tiep_bang_module(self):
        for relative in ('giao_dien/module_cong_tac.py', 'k2/module.py'):
            with self.subTest(file=relative):
                tree = ast.parse((ROOT / 'src/kho_tri_thuc' / relative).read_text(encoding='utf-8'))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Constant) and isinstance(node.value, str):
                        self.assertIsNone(self.table_read.search(node.value),
                                          f'{relative}:{node.lineno}: FROM/JOIN master.module_ bị cấm')

    def test_http_va_dich_vu_khong_goi_mtq_la_admin(self):
        forbidden = re.compile(r'\bmtq_la_admin\s*\(', re.IGNORECASE)
        for relative in ('giao_dien/module_cong_tac.py', 'k2/module.py'):
            with self.subTest(file=relative):
                source = (ROOT / 'src/kho_tri_thuc' / relative).read_text(encoding='utf-8')
                self.assertIsNone(forbidden.search(source), relative)

    def test_tai_dung_factory_mtq_va_dong_ket_noi_khi_loi(self):
        mau, events = object(), []

        @contextmanager
        def factory(app):
            events.append('open')
            try:
                yield SimpleNamespace(mau=mau)
            finally:
                events.append('close')

        with patch.object(http.mtq_http, 'dich_vu', side_effect=factory):
            with self.assertRaisesRegex(RuntimeError, 'Thử lỗi'):
                with http.dich_vu(object()) as svc:
                    self.assertIs(svc.mau, mau)
                    raise RuntimeError('Thử lỗi')
        self.assertEqual(events, ['open', 'close'])


@unittest.skipUnless(DSN and psycopg is not None,
                     'NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG')
class ModuleHttpPostgres(unittest.TestCase):
    # Tái dùng Handler/serializer thật, chỉ thay factory bằng dịch vụ PG test.
    handler = ModuleHttpTests.handler
    call = ModuleHttpTests.call
    command = ModuleHttpTests.command

    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from psycopg.rows import dict_row
        from kho_tri_thuc.ha_tang import postgres
        from kho_tri_thuc.k2.crm_mau import CrmMauK2

        cls.db = 'kho_test_xs4c2_' + uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_web') "
                          "THEN CREATE ROLE app_web NOLOGIN NOINHERIT; END IF; END $$")
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0")
                          .format(sql.Identifier(cls.db)))
        test_dsn = make_conninfo(DSN, dbname=cls.db)
        owner = psycopg.connect(test_dsn, autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(owner.close)
        postgres.migrate(owner)
        with owner.transaction():
            cls.login = 'MO_PHONG_XS4C2_' + uuid4().hex
            actor = owner.execute(
                "INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro,mo_phong) "
                "VALUES ('Admin giả XS4c2',%s,'XEM',true) RETURNING id",
                (cls.login,)).fetchone()['id']
            owner.execute("SELECT master.mtq_bootstrap_admin(%s::uuid,%s::uuid,'Admin giả XS4c2')",
                          (actor, uuid4()))
            owner.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true),"
                          "set_config('ktt.nguoi_dung_dang_nhap',%s,true)",
                          (str(actor), cls.login))
            cls.pn = str(owner.execute(
                "INSERT INTO master.phap_nhan (ma,ten) VALUES (%s,'Pháp nhân giả XS4c2') RETURNING id",
                (uuid4().hex,)).fetchone()['id'])
            owner.execute("INSERT INTO master.phan_quyen (nguoi_dung_id,phap_nhan_id,module) "
                          "VALUES (%s,%s::uuid,ARRAY['CRM'])", (actor, cls.pn))
            cls.other_login = 'MO_PHONG_XS4C2_' + uuid4().hex
            other = owner.execute(
                "INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro,mo_phong) "
                "VALUES ('Người dùng giả XS4c2',%s,'XEM',true) RETURNING id",
                (cls.other_login,)).fetchone()['id']
            owner.execute("INSERT INTO master.phan_quyen (nguoi_dung_id,phap_nhan_id,module) "
                          "VALUES (%s,%s::uuid,ARRAY['CRM'])", (other, cls.pn))
        cls.c = psycopg.connect(test_dsn, autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(cls.c.close)
        # SET ROLE theo phiên để danh_tinh lẫn mọi _tx đều chạy dưới app_web.
        cls.c.execute('SET ROLE app_web')
        cls.mau = CrmMauK2(cls.c, ROOT, conn_tin_cay=cls.c)
        cls.svc = http._CongTacHttpK2(cls.mau)

    def setUp(self):
        self.app = SimpleNamespace(mutation_lock=threading.Lock(), token='TOKEN-DEMO-XS4C2-PG',
                                   CRM_COOKIE='CRM_DEMO', is_that=False)
        self.app.crm_phien = Mock(return_value=('sid-demo', self.login, False))
        self.app._crm_db = Mock(side_effect=lambda fn, *a: fn(*a))

        @contextmanager
        def service(app):
            self.assertIs(app, self.app)
            self.assertTrue(app.mutation_lock.locked())
            yield self.svc

        factory_patch = patch.object(http, 'dich_vu', side_effect=service)
        factory_patch.start()
        self.addCleanup(factory_patch.stop)

    def test_app_web_doc_phap_nhan_trang_thai_va_admin_post_khong_loi_quyen(self):
        self.assertEqual(self.c.execute('SELECT current_user AS vai').fetchone()['vai'], 'app_web')
        self.assertFalse(self.c.execute(
            "SELECT has_function_privilege(current_user,'master.mtq_la_admin()','EXECUTE') AS duoc"
        ).fetchone()['duoc'])
        for table in ('module_danh_muc', 'module_cong_tac', 'module_nguoi_thu'):
            with self.subTest(table=table):
                self.assertFalse(self.c.execute(
                    "SELECT has_table_privilege(current_user,%s,'SELECT') AS duoc",
                    ('master.' + table,)).fetchone()['duoc'])
        self.svc.kiem_danh_muc(self.login, 'CRM')
        for quan_tri in (False, True):
            with self.subTest(quan_tri=quan_tri):
                rows = self.svc.phap_nhan(self.login, 'CRM', quan_tri=quan_tri)
                self.assertIn(self.pn, [r['phap_nhan_id'] for r in rows])
        before = self.svc.trang_thai(self.login, 'CRM', self.pn)
        self.assertEqual((before['che_do'], before['revision']), ('VAN_HANH', 0))
        status, rows = self.call()
        self.assertEqual(status, 200)
        self.assertIn(self.pn, [r['phap_nhan_id'] for r in rows])
        with patch.object(self.svc, 'danh_sach_nguoi_thu',
                          wraps=self.svc.danh_sach_nguoi_thu) as danh_sach:
            self.assertEqual(self.call('nguoi-thu?module=CRM')[0], 200)
            danh_sach.assert_any_call(self.login, 'CRM', self.pn)
        self.assertEqual(self.call('che-do', self.command(phap_nhan_id=self.pn, revision=0), post=True),
                         (200, {'revision': 1}))
        after = self.svc.trang_thai(self.login, 'CRM', self.pn)
        self.assertEqual((after['che_do'], after['revision']), ('THU', 1))
        self.assertTrue(after['cho_ghi'])
        self.assertFalse(after['cho_xuat_ngoai'])
        status, rows = self.call('trang-thai?module=CHUA_KHAI_BAO')
        self.assertEqual(status, 200)
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual({key: row[key] for key in FLAGS_TAT}, FLAGS_TAT)
        status, result = self.call('che-do', self.command(
            module='CHUA_KHAI_BAO', phap_nhan_id=self.pn, revision=0), post=True)
        self.assertEqual((status, result['error']), (400, 'MODULE_DAU_VAO'))
        self.assertEqual(result['message'], http._THONG_BAO['MODULE_DAU_VAO'])

    def test_app_web_khong_admin_xem_nguoi_thu_403_trang_thai_200(self):
        self.assertEqual(self.c.execute('SELECT current_user AS vai').fetchone()['vai'], 'app_web')
        self.app.crm_phien.return_value = ('sid-demo', self.other_login, False)
        status, rows = self.call()
        self.assertEqual(status, 200)
        self.assertIn(self.pn, [r['phap_nhan_id'] for r in rows])
        status, result = self.call('nguoi-thu?module=CRM')
        self.assertEqual((status, result['error']), (403, 'MODULE_CHI_ADMIN'))
        self.assertEqual(result['message'], http._THONG_BAO['MODULE_CHI_ADMIN'])


if __name__ == '__main__':
    unittest.main()
