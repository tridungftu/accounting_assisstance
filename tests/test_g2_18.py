"""WSGI thuần/mock, không mở cổng; PG opt-in qua fixture kho_test_* G2-14.

KiemTest chỉ là test double dùng subset sẵn có G2-17 khi thiếu jsonschema.
Test validator production có skip riêng; không coi subset là chứng nhận schema.
Không đọc cấu hình thật, cài dependency, gọi mạng hoặc bật/tắt dịch vụ.
"""

from contextlib import contextmanager, nullcontext
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
from io import BytesIO
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import dispatcher as d, http as h, phien, tiep_nhan as tn, viec

try:
    from . import test_g2_17 as g217, test_g2_14 as g214
except ImportError:
    import test_g2_17 as g217
    import test_g2_14 as g214


CO_SCHEMA = all(importlib.util.find_spec(n) is not None for n in ('jsonschema', 'referencing'))
ORIGIN = 'https://core.demo'
PN, USER, OBJ = uuid4(), uuid4(), uuid4()
NOW = datetime.now(timezone.utc)
KEY = 'g2-18-khoa-demo-0001'
BODY = {'type': 'object', 'additionalProperties': False, 'required': ['row_version'],
        'properties': {'row_version': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}}}
OUT = {'type': 'object', 'additionalProperties': False, 'required': ['id', 'row_version'],
       'properties': {'id': {'type': 'string', 'format': 'uuid'}, 'row_version': {'type': 'string'}}}
ACCEPTED = {'$ref': 'urn:ktt:contract:viec.v1#/$defs/da_nhan'}
ERROR = {'$ref': 'urn:ktt:contract:loi_chuan.v1'}
LIST = {'type': 'object', 'additionalProperties': False,
        'required': ['danh_sach', 'con_tiep', 'con_tro_tiep'],
        'properties': {'danh_sach': {'type': 'array', 'items': OUT},
                       'con_tiep': {'type': 'boolean'},
                       'con_tro_tiep': {'type': ['string', 'null']}}}


class KiemTest:
    def __init__(self):
        self.bundle = json.loads((d.goi.THU_MUC_CONTRACT / 'ky_thuat.json').read_text(encoding='utf-8'))

    def kiem(self, schema, value):
        try:
            d._json(value)
            g217._minimal(value, schema, schema, self.bundle)
            return True
        except (ValueError, KeyError, TypeError):
            return False


class KetNoiGia:
    def __init__(self):
        self.info = SimpleNamespace(transaction_status=0)
        self.events = []
        self.loi_commit = False

    @contextmanager
    def transaction(self):
        self.info.transaction_status = 2
        self.events.append('begin')
        try:
            yield
            if self.loi_commit:
                raise RuntimeError('CANARY password driver commit')
        except Exception:
            self.events.append('rollback')
            raise
        else:
            self.events.append('commit')
        finally:
            self.info.transaction_status = 0


def route_demo(method='GET', **doi):
    values = dict(method=method, duong_dan='/api/v1/mau/{id}', module='crm',
        operation='CRM.DEMO.' + ('XEM' if method == 'GET' else 'SUA'),
        hanh_dong='CRM:TIEP_NHAN:' + ('XEM' if method == 'GET' else 'SUA'),
        dau_vao={'type': 'null'} if method == 'GET' else BODY, dau_ra={200: OUT},
        doi_tuong=lambda p, b: {'bang': 'doi_tuong', 'id': p['id']},
        handler=Mock(return_value=h.PhanHoi(200, {'id': str(OBJ), 'row_version': '2'})),
        quyen_doc=lambda c, b: {'hanh_dong': 'CRM:TIEP_NHAN:XEM', 'doi_tuong': c.doi_tuong,
                               'phien_ban_contract': '1'},
        path_schema={'type': 'object', 'properties': {'id': {'type': 'string', 'format': 'uuid'}},
                     'required': ['id'], 'additionalProperties': False})
    return d.Route(**(values | doi))


def wsgi(app, method='GET', path=None, *, body=None, headers=None, env_extra=None, on_send=None):
    path = path or '/api/v1/mau/' + str(OBJ)
    path, _, query = path.partition('?')
    raw = body if isinstance(body, bytes) else (b'' if body is None else json.dumps(body).encode('utf-8'))
    env = {'REQUEST_METHOD': method, 'PATH_INFO': path, 'QUERY_STRING': query,
           'CONTENT_LENGTH': str(len(raw)), 'CONTENT_TYPE': 'application/json', 'wsgi.input': BytesIO(raw)}
    base = {'Host': 'core.demo', 'Cookie': '__Host-ktt_phien=SID_CANARY', 'Origin': ORIGIN,
            'X-CSRF-Token': 'CSRF_CANARY', 'X-Phap-Nhan-Id': str(PN), 'Idempotency-Key': KEY}
    base.update(headers or {})
    env.update({'HTTP_' + k.upper().replace('-', '_'): v for k, v in base.items() if v is not None})
    env.update(env_extra or {})
    captured = {}
    def start(status, response_headers):
        captured.update(status=int(status.split()[0]), headers=dict(response_headers))
        if on_send:
            on_send(captured)
    raw_response = b''.join(app(env, start))
    captured['body'] = json.loads(raw_response) if raw_response else None
    return captured


class BienHTTPTest(unittest.TestCase):
    def setUp(self):
        self.csrf = phien.MaBiMat('CSRF_CANARY')
        self.ma = phien.MaBiMat('MA_CSDL_CANARY')
        self.session = h.PhienHTTP(USER, self.csrf, Mock(return_value=self.ma), NOW, NOW)
        self.doc_phien = Mock(return_value=self.session)
        self.conn = KetNoiGia()
        self.registry = d.Registry()
        self.route = route_demo()
        self.registry.dang_ky(self.route)
        self.kiem = KiemTest()
        self.cursor = d.ConTro(b'DEMO' * 8, dong_ho=lambda: 1000)
        self.dispatcher = d.Dispatcher(self.registry, ket_noi=lambda: nullcontext(self.conn),
                                       kiem=self.kiem, cursor=self.cursor)
        self.app = h.UngDungHTTP(self.dispatcher, origin=ORIGIN, doc_phien=self.doc_phien, dong_ho=lambda: NOW)
        self.xac = self.enterContext(patch.object(d.phien, 'xac_minh_phien',
            return_value=SimpleNamespace(nguoi_dung_id=USER)))
        self.mtq = self.enterContext(patch.object(d.mtq, 'quyet_dinh_phien',
            return_value={'ket_luan': 'DAT', 'cho_phep': True}))
        self.tra = self.enterContext(patch.object(tn, 'tra_core', return_value=None))
        self.ghi = self.enterContext(patch.object(tn, 'ghi_core'))

    def doi_route(self, method='PATCH', **doi):
        self.route = route_demo(method, **doi)
        self.registry = d.Registry()
        self.registry.dang_ky(self.route)
        self.dispatcher.registry = self.registry
        return self.route

    def test_cookie_chi_tra_hash_khong_dung_sid_lam_ma_csdl(self):
        r = wsgi(self.app)
        self.assertEqual(r['status'], 200)
        self.doc_phien.assert_called_once_with(hashlib.sha256(b'SID_CANARY').hexdigest())
        self.session.lay_ma.assert_called_once_with('crm', PN)
        self.assertIs(self.xac.call_args.kwargs['ma'], self.ma)
        self.assertEqual(self.conn.events, ['begin', 'commit'])

    def test_origin_csrf_bat_buoc_truoc_nghiep_vu(self):
        self.doi_route()
        for hd in ({'Origin': 'https://evil.demo'}, {'Origin': None}, {'X-CSRF-Token': None},
                   {'X-CSRF-Token': 'SAI'}, {'Cookie': None}, {'Sec-Fetch-Site': 'cross-site'},
                   {'Host': 'evil.demo'}):
            with self.subTest(headers=hd):
                self.assertEqual(wsgi(self.app, 'PATCH', body={'row_version': '1'}, headers=hd)['status'], 403)
        self.xac.assert_not_called()
        self.route.handler.assert_not_called()

    def test_phien_het_han_thu_hoi_va_tien_phien_khong_doc_nghiep_vu(self):
        for session in (None, replace(self.session, hoat_dong_luc=NOW-timedelta(minutes=30)),
                        replace(self.session, tao_luc=NOW-timedelta(hours=8)),
                        replace(self.session, tien_phien=True),
                        replace(self.session, tao_luc=NOW+timedelta(seconds=1))):
            self.doc_phien.return_value = session
            self.assertEqual(wsgi(self.app)['status'], 401)
        self.route.handler.assert_not_called()

    def test_cookie_trung_va_tls_lan_bi_tu_choi(self):
        r = wsgi(self.app, headers={'Cookie': '__Host-ktt_phien=a; __Host-ktt_phien=b'})
        self.assertEqual(r['status'], 400)
        with self.assertRaises(ValueError):
            h.UngDungHTTP(self.dispatcher, origin='http://192.0.2.1', doc_phien=self.doc_phien)

    def test_get_phien_khong_dang_nhap_khong_can_phap_nhan(self):
        schema = {'type': 'object', 'additionalProperties': False,
                  'required': ['da_dang_nhap'], 'properties': {'da_dang_nhap': {'type': 'boolean'}}}
        self.doi_route('GET', duong_dan='/api/v1/phien', phien='khong', pham_vi='he_thong',
                       path_schema={'type': 'object', 'additionalProperties': False},
                       doi_tuong=lambda p, b: {}, dau_ra={200: schema},
                       handler=Mock(return_value=h.PhanHoi(200, {'da_dang_nhap': False})))
        for cookie in (None, '__Host-ktt_tien_phien=PRE_CANARY'):
            self.doc_phien.return_value = replace(self.session, nguoi_dung_id=None, tien_phien=True)
            r = wsgi(self.app, path='/api/v1/phien', headers={'Cookie': cookie, 'X-Phap-Nhan-Id': None})
            self.assertEqual((r['status'], r['body']), (200, {'da_dang_nhap': False}))
        self.xac.assert_not_called()
        self.mtq.assert_not_called()
        self.assertIsNone(self.route.handler.call_args.args[1].nguoi_dung_id)
        self.assertIsNone(self.route.handler.call_args.args[1].phap_nhan_id)
        self.assertEqual(self.route.handler.call_count, 2)

    def test_tien_phien_theo_registry_van_bat_buoc_origin_csrf(self):
        # Giả lập route lọt đăng ký; biên HTTP vẫn kiểm Origin/CSRF trước.
        self.route = route_demo('DELETE', duong_dan='/api/v1/xac-thuc', phien='tien_phien', pham_vi='he_thong',
                       path_schema={'type': 'object', 'additionalProperties': False}, doi_tuong=lambda p, b: {})
        self.registry.tra = Mock(return_value=(self.route, {}))
        self.doc_phien.return_value = replace(self.session, nguoi_dung_id=None, tien_phien=True)
        hd = {'Cookie': '__Host-ktt_tien_phien=PRE_CANARY', 'X-Phap-Nhan-Id': None}
        for bad in ({'Origin': None}, {'Origin': 'https://evil.demo'}, {'X-CSRF-Token': None},
                    {'X-CSRF-Token': 'SAI'}, {'Cookie': None}, {'Sec-Fetch-Site': 'cross-site'}):
            with self.subTest(headers=bad):
                self.assertEqual(wsgi(self.app, 'DELETE', path='/api/v1/xac-thuc',
                                      body={'row_version': '1'}, headers=hd | bad)['status'], 403)
        self.route.handler.assert_not_called()
        self.assertEqual(self.conn.events, [])
        self.assertEqual(wsgi(self.app, 'DELETE', path='/api/v1/xac-thuc',
                              body={'row_version': '1'}, headers=hd)['status'], 503)
        self.route.handler.assert_not_called()
        self.assertEqual(self.conn.events, [])
        self.xac.assert_not_called()

    def test_post_phien_lot_dang_ky_van_bi_chan_va_kiem_han_tien_phien(self):
        self.route = route_demo('POST', duong_dan='/api/v1/phien', phien='tien_phien', pham_vi='he_thong',
                       path_schema={'type': 'object', 'additionalProperties': False}, doi_tuong=lambda p, b: {})
        self.registry.tra = Mock(return_value=(self.route, {}))
        pre = replace(self.session, nguoi_dung_id=None, tien_phien=True)
        hd = {'Cookie': '__Host-ktt_tien_phien=PRE_CANARY', 'X-Phap-Nhan-Id': None, 'Idempotency-Key': None}
        for session in (replace(pre, tao_luc=NOW-timedelta(minutes=10)), None):
            self.doc_phien.return_value = session
            self.assertEqual(wsgi(self.app, 'POST', path='/api/v1/phien',
                                  body={'row_version': '1'}, headers=hd)['status'], 403)
        self.route.handler.assert_not_called()
        self.assertEqual(self.conn.events, [])
        self.doc_phien.return_value = pre
        self.assertEqual(wsgi(self.app, 'POST', path='/api/v1/phien',
                              body={'row_version': '1'}, headers=hd)['status'], 503)
        self.route.handler.assert_not_called()
        self.assertEqual(self.conn.events, [])
        self.tra.assert_not_called()
        self.ghi.assert_not_called()

    def test_ghi_he_thong_lot_dang_ky_tra_loi_chuan_truoc_handler(self):
        policy = self.dispatcher.quyen_he_thong = Mock(return_value=True)
        for method in ('POST', 'PATCH', 'PUT', 'DELETE'):
            for che_do_phien in ('bat_buoc', 'tien_phien', 'khong'):
                with self.subTest(method=method, phien=che_do_phien):
                    route = route_demo(method, pham_vi='he_thong', phien=che_do_phien)
                    self.registry.tra = Mock(return_value=(route, {'id': str(OBJ)}))
                    # Thiếu key và sai schema vẫn không lọt tới biên nhận/handler.
                    result = wsgi(self.app, method, body={},
                                  headers={'X-Phap-Nhan-Id': None, 'Idempotency-Key': None})
                    self.assertEqual((result['status'], result['body']['ma']), (503, 'CHUA_SAN_SANG'))
                    self.assertEqual(set(result['body']),
                                     {'ma', 'thong_diep', 'request_id', 'thu_lai_duoc'})
                    self.assertTrue(self.kiem.kiem(ERROR, result['body']))
                    self.assertEqual(result['body']['request_id'], result['headers']['X-Request-Id'])
                    UUID(result['body']['request_id'])
                    self.assertEqual(result['headers']['Retry-After'], '2')
                    self.assertEqual(self.conn.events, [])
                    route.handler.assert_not_called()
        policy.assert_not_called()
        self.xac.assert_not_called()
        self.mtq.assert_not_called()
        self.session.lay_ma.assert_not_called()
        self.tra.assert_not_called()
        self.ghi.assert_not_called()

    def test_he_thong_khong_can_header_nhung_phai_duoc_cap_quyen(self):
        self.doi_route('GET', pham_vi='he_thong')
        hd = {'X-Phap-Nhan-Id': None}
        self.assertEqual(wsgi(self.app, headers=hd)['status'], 404)  # Không có policy: đóng.
        self.route.handler.assert_not_called()
        policy = self.dispatcher.quyen_he_thong = Mock(return_value=False)
        self.assertEqual(wsgi(self.app, headers=hd)['status'], 404)
        self.route.handler.assert_not_called()
        policy.return_value = True
        self.assertEqual(wsgi(self.app, headers=hd)['status'], 200)
        self.route.handler.assert_called_once()
        context = policy.call_args.args[1]
        self.assertEqual(context.nguoi_dung_id, USER)
        self.assertIsNone(context.phap_nhan_id)
        self.assertEqual(context.hanh_dong, self.route.hanh_dong)
        self.assertEqual(wsgi(self.app, headers=hd | {'Cookie': None})['status'], 401)
        self.assertEqual(policy.call_count, 2)
        self.xac.assert_not_called()
        self.mtq.assert_not_called()
        self.session.lay_ma.assert_not_called()

    def test_mac_dinh_bat_buoc_phien_va_phap_nhan(self):
        self.assertEqual((self.route.phien, self.route.pham_vi), ('bat_buoc', 'phap_nhan'))
        self.assertEqual(wsgi(self.app, headers={'Cookie': None, 'X-Phap-Nhan-Id': None})['status'], 401)
        self.assertEqual(wsgi(self.app, headers={'X-Phap-Nhan-Id': None})['status'], 400)
        self.assertEqual(self.conn.events, [])
        self.route.handler.assert_not_called()

    def test_stream_dung_ngay_byte_limit_cong_mot_khong_doc_tiep(self):
        self.doi_route()
        class Stream:
            def __init__(self):
                self.dem = 0
            def read(self, n):
                self.dem += n
                if self.dem > h.GIOI_HAN_JSON + 1:
                    raise AssertionError('Đã đọc sau byte vượt giới hạn')
                return b' ' * n
        stream = Stream()
        r = wsgi(self.app, 'PATCH', env_extra={'CONTENT_LENGTH': '', 'wsgi.input_terminated': True,
                                             'wsgi.input': stream})
        self.assertEqual(r['status'], 413)
        self.assertEqual(stream.dem, h.GIOI_HAN_JSON + 1)
        self.xac.assert_not_called()

    def test_json_dung_limit_va_content_length_khong_duoc_tin_thay_dem(self):
        raw = b'{' + b' ' * (h.GIOI_HAN_JSON-2) + b'}'
        self.assertEqual(h.doc_json(BytesIO(raw), len(raw)), {})
        for raw in (raw+b' ', b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'\xff', b'{'):
            with self.subTest(length=len(raw)), self.assertRaises(h.LoiHTTP):
                h.doc_json(BytesIO(raw), len(raw))
        self.doi_route()
        for extra, status in (({'CONTENT_LENGTH': str(h.GIOI_HAN_JSON+1)}, 413),
                              ({'CONTENT_LENGTH': '20'}, 400), ({'CONTENT_LENGTH': '-1'}, 400),
                              ({'CONTENT_LENGTH': '', 'wsgi.input_terminated': False}, 400),
                              ({'CONTENT_TYPE': 'text/plain'}, 415)):
            self.assertEqual(wsgi(self.app, 'PATCH', body={}, env_extra=extra)['status'], status)

    def test_envelope_khong_lo_trace_driver_request_id_do_core_sinh(self):
        self.route.handler.side_effect = RuntimeError('CANARY DSN SQL password traceback')
        r = wsgi(self.app, headers={'X-Request-Id': 'GIA'})
        self.assertEqual(r['status'], 500)
        self.assertEqual(set(r['body']), {'ma', 'thong_diep', 'request_id', 'thu_lai_duoc'})
        self.assertEqual(r['body']['request_id'], r['headers']['X-Request-Id'])
        UUID(r['body']['request_id'])
        self.assertNotIn('CANARY', json.dumps(r))
        self.assertEqual(r['headers']['Cache-Control'], 'no-store')

    def test_route_khong_dang_ky_404_method_sai_405_allow(self):
        self.assertEqual(wsgi(self.app, path='/api/v1/module/crm/bat-ky')['status'], 404)
        r = wsgi(self.app, 'POST', body={})
        self.assertEqual(r['status'], 405)
        self.assertEqual(r['headers']['Allow'], 'GET')
        self.route.handler.assert_not_called()

    def test_path_query_schema_va_khoa_chong_trung(self):
        self.doi_route(truong_cas=('row_version',))
        for value in (1, True, '0', '9223372036854775808'):
            self.assertEqual(wsgi(self.app, 'PATCH', body={'row_version': value})['status'], 422)
        self.assertEqual(wsgi(self.app, 'PATCH', body={'row_version': '1', 'actor': 'ADMIN'})['status'], 422)
        for key in (None, 'ngan', 'x'*129, 'ắ'*20):
            self.assertEqual(wsgi(self.app, 'PATCH', body={'row_version': '1'}, headers={'Idempotency-Key': key})['status'], 400)
        self.assertEqual(wsgi(self.app, 'PATCH', path='/api/v1/mau/sai', body={'row_version': '1'})['status'], 422)
        self.assertEqual(wsgi(self.app, 'PATCH', path='/api/v1/mau/'+str(OBJ)+'?sql=x', body={'row_version': '1'})['status'], 422)
        self.assertEqual(wsgi(self.app, 'PATCH', path='/api/v1/mau/'+str(OBJ)+'?x=1&x=2', body={'row_version': '1'})['status'], 400)
        self.route.handler.assert_not_called()
        self.assertEqual(self.conn.events, [])

    def test_kiem_phap_nhan_va_quyen_truoc_handler_receipt(self):
        self.doi_route()
        self.assertEqual(wsgi(self.app, 'PATCH', body={'row_version': '1'}, headers={'X-Phap-Nhan-Id': None})['status'], 400)
        self.xac.return_value = None
        self.assertEqual(wsgi(self.app, 'PATCH', body={'row_version': '1'})['status'], 404)
        self.xac.return_value = SimpleNamespace(nguoi_dung_id=USER)
        for decision, status in (({'ket_luan': 'CHO', 'cho_phep': False}, 503),
                                 ({'ket_luan': 'DAT', 'cho_phep': False}, 404)):
            self.mtq.return_value = decision
            self.assertEqual(wsgi(self.app, 'PATCH', body={'row_version': '1'})['status'], status)
        self.tra.assert_not_called()
        self.route.handler.assert_not_called()

    def test_sai_schema_502_rollback_truoc_bien_nhan(self):
        self.doi_route()
        self.route.handler.return_value = h.PhanHoi(200, {'id': 'CANARY SQL', 'row_version': 2})
        r = wsgi(self.app, 'PATCH', body={'row_version': '1'})
        self.assertEqual((r['status'], r['body']['ma']), (502, 'PHAN_HOI_SAI_CONTRACT'))
        self.assertNotIn('CANARY', json.dumps(r))
        self.ghi.assert_not_called()
        self.assertEqual(self.conn.events, ['begin', 'rollback'])

    def test_cas_va_bien_nhan_conflict_409(self):
        self.doi_route()
        for exc in (viec.LoiViec('VIEC_CAS'), d.LoiTaiLieu('TAI_LIEU_REVISION'),
                    tn.LoiTiepNhan('KHOA_CHONG_TRUNG_KHAC_NOI_DUNG')):
            self.route.handler.side_effect = exc
            self.assertEqual(wsgi(self.app, 'PATCH', body={'row_version': '1'})['status'], 409)
        self.ghi.assert_not_called()

    def test_replay_truoc_cas_va_van_kiem_quyen(self):
        self.doi_route(truong_cas=('row_version',))
        self.tra.return_value = {'ket_qua': {'status': 200, 'body': {'id': str(OBJ), 'row_version': '2'}}}
        self.route.handler.side_effect = viec.LoiViec('VIEC_CAS')
        self.assertEqual(wsgi(self.app, 'PATCH', body={'row_version': '1'})['status'], 200)
        self.route.handler.assert_not_called()
        self.ghi.assert_not_called()
        self.mtq.assert_called_once()
        self.mtq.return_value = {'ket_luan': 'TU_CHOI', 'cho_phep': False}
        self.assertEqual(wsgi(self.app, 'PATCH', body={'row_version': '1'})['status'], 404)
        self.assertEqual(self.tra.call_count, 1)

    def test_core_ghi_bien_nhan_tren_cung_transaction_truoc_commit(self):
        self.doi_route()
        def ghi(conn, **kwargs):
            self.assertIs(conn, self.conn)
            self.assertEqual(conn.info.transaction_status, 2)
            self.assertEqual(conn.events, ['begin'])
            self.assertEqual(kwargs['ket_qua']['status'], 200)
        self.ghi.side_effect = ghi
        r = wsgi(self.app, 'PATCH', body={'row_version': '1'},
                 on_send=lambda r: self.assertEqual(self.conn.events[-1], 'commit'))
        self.assertEqual(r['status'], 200)
        self.ghi.assert_called_once()

    def test_viec_202_sau_commit_va_replay_doi_request_id(self):
        id_ = uuid4()
        self.doi_route('POST', viec_lau=True, dau_ra={202: ACCEPTED})
        self.route.handler.return_value = d.ViecMoi('DEMO', OBJ, 'doi_tuong')
        with patch.object(viec, 'tao_viec', return_value=id_) as tao:
            r = wsgi(self.app, 'POST', body={'row_version': '1'},
                     on_send=lambda r: self.assertEqual(self.conn.events[-1], 'commit'))
            self.assertEqual(r['status'], 202)
            self.assertEqual(r['body']['trang_thai'], 'queued')
            self.assertEqual(r['headers']['Location'], '/api/v1/viec/'+str(id_))
            self.assertEqual(r['headers']['Retry-After'], '2')
            self.assertEqual(self.ghi.call_args.kwargs['trang_thai'], 'DANG_XU_LY')
            tao.assert_called_once()
            self.tra.return_value = {'ket_qua': {'status': 202, 'body': r['body']}}
            replay = wsgi(self.app, 'POST', body={'row_version': '1'})
            self.assertEqual(replay['body']['viec_id'], str(id_))
            self.assertNotEqual(replay['body']['request_id'], r['body']['request_id'])
            self.assertEqual(replay['body']['request_id'], replay['headers']['X-Request-Id'])
            tao.assert_called_once()

    def test_commit_loi_khong_gui_202_va_khong_nhan_savepoint(self):
        self.doi_route('POST', viec_lau=True, dau_ra={202: ACCEPTED})
        self.route.handler.return_value = d.ViecMoi('DEMO', OBJ, 'doi_tuong')
        self.conn.loi_commit = True
        with patch.object(viec, 'tao_viec', return_value=uuid4()):
            r = wsgi(self.app, 'POST', body={'row_version': '1'})
        self.assertEqual(r['status'], 500)
        self.assertEqual(self.conn.events[-1], 'rollback')
        self.assertNotIn('CANARY', json.dumps(r))
        self.conn.info.transaction_status = 2
        self.assertEqual(wsgi(self.app, 'POST', body={'row_version': '1'})['status'], 500)

    def test_202_tu_khai_khong_tao_viec_bi_chan(self):
        self.doi_route('POST', viec_lau=True, dau_ra={202: ACCEPTED})
        self.route.handler.return_value = h.PhanHoi(202, {'viec_id': str(uuid4()), 'trang_thai': 'queued', 'request_id': str(uuid4())})
        self.assertEqual(wsgi(self.app, 'POST', body={'row_version': '1'})['status'], 502)
        self.ghi.assert_not_called()

    def test_viec_lau_loi_da_khai_giu_422_sai_contract_moi_502(self):
        for owner in ('core', 'module'):
            route = self.doi_route('POST', chu_so_huu=owner,
                duong_dan='/api/v1/module/crm/mau/{id}' if owner == 'module' else '/api/v1/mau/{id}',
                viec_lau=True, dau_ra={202: ACCEPTED, 422: ERROR},
                ma_loi={(422, 'DEMO_SAI'): 'Dữ liệu không hợp lệ.'},
                phien_ban_goi='1', ma_bam_goi='a'*64)
            module_conn = KetNoiGia()
            self.dispatcher.kenh_module = lambda r, c: d.thuc_hien_module(
                module_conn, r, c, self.ma, kiem=self.kiem)
            error = {'ma': 'DEMO_SAI', 'thong_diep': 'CANARY SQL',
                     'request_id': str(uuid4()), 'thu_lai_duoc': False}
            with patch.object(tn, 'tra_thao_tac', return_value=None), \
                    patch.object(tn, 'ghi_thao_tac') as ghi, patch.object(viec, 'tao_viec') as tao, \
                    patch.object(d.dang_ky, 'doc_dang_ky', return_value=[{
                        'so_phien_ban': '1', 'ma_bam_goi': 'a'*64, 'trang_thai': 'da_cai'}]):
                for body, status in ((error, 422), (error | {'ma': 'CHUA_KHAI'}, 502),
                                     (error | {'thu_lai_duoc': 'sai'}, 502)):
                    with self.subTest(owner=owner, body=body):
                        route.handler.return_value = h.PhanHoi(422, body)
                        r = wsgi(self.app, 'POST', path=route.duong_dan.replace('{id}', str(OBJ)),
                                 body={'row_version': '1'})
                        self.assertEqual(r['status'], status)
                        self.assertNotIn('CANARY', json.dumps(r))
                        self.assertEqual(r['body']['request_id'], r['headers']['X-Request-Id'])
                        if status == 422:
                            self.assertEqual(r['body']['ma'], 'DEMO_SAI')
                            self.assertEqual(r['body']['thong_diep'], 'Dữ liệu không hợp lệ.')
                        self.assertEqual((module_conn if owner == 'module' else self.conn).events[-1], 'rollback')
                ghi.assert_not_called()
                tao.assert_not_called()
            self.ghi.assert_not_called()

    def test_khoa_dang_chay_khong_goi_handler_lan_hai(self):
        self.doi_route()
        lock_key = (USER, PN, 'crm', self.route.operation, KEY)
        self.dispatcher._dang_chay.add(lock_key)
        r = wsgi(self.app, 'PATCH', body={'row_version': '1'})
        self.assertEqual(r['status'], 409)
        self.assertEqual(r['headers']['Retry-After'], '2')
        self.route.handler.assert_not_called()
        self.assertIn(lock_key, self.dispatcher._dang_chay)

    def test_module_chi_nhan_context_khong_cookie_ma_core_va_loc_header(self):
        route = self.doi_route(chu_so_huu='module', duong_dan='/api/v1/module/crm/mau/{id}',
                              phien_ban_goi='1', ma_bam_goi='a'*64)
        remote = Mock(return_value=h.PhanHoi(200, {'id': str(OBJ), 'row_version': '2'},
            {'Set-Cookie': 'CANARY', 'Access-Control-Allow-Origin': '*'}, da_commit=True))
        self.dispatcher.kenh_module = remote
        with patch.object(d.dang_ky, 'doc_dang_ky', return_value=[{
            'so_phien_ban': '1', 'ma_bam_goi': 'a'*64, 'trang_thai': 'da_cai'}]):
            r = wsgi(self.app, 'PATCH', path='/api/v1/module/crm/mau/'+str(OBJ), body={'row_version': '1'})
        self.assertEqual(r['status'], 200)
        context = remote.call_args.args[1]
        self.assertIsInstance(context, d.NguCanh)
        self.assertEqual(context.khoa, KEY)
        for name in ('headers', 'cookie', 'phien', 'ma'):
            self.assertFalse(hasattr(context, name))
        self.assertNotIn('Set-Cookie', r['headers'])
        self.assertNotIn('Access-Control-Allow-Origin', r['headers'])
        route.handler.assert_not_called()
        self.tra.assert_not_called()

    def test_module_sai_contract_chua_commit_loi_chua_khai_va_timeout(self):
        self.doi_route(chu_so_huu='module', duong_dan='/api/v1/module/crm/mau/{id}',
                       phien_ban_goi='1', ma_bam_goi='a'*64, dau_ra={200: OUT, 409: ERROR},
                       ma_loi={(409, 'DEMO_XUNG_DOT'): 'Dữ liệu đã thay đổi.'})
        remote = self.dispatcher.kenh_module = Mock()
        path = '/api/v1/module/crm/mau/'+str(OBJ)
        with patch.object(d.dang_ky, 'doc_dang_ky', return_value=[{
            'so_phien_ban': '1', 'ma_bam_goi': 'a'*64, 'trang_thai': 'da_cai'}]):
            for response in (h.PhanHoi(200, {'id': 'CANARY'}),
                             h.PhanHoi(200, {'id': str(OBJ), 'row_version': '1'}),
                             h.PhanHoi(409, {'ma': 'CHUA_KHAI', 'thong_diep': 'CANARY',
                                           'request_id': str(uuid4()), 'thu_lai_duoc': False})):
                remote.return_value = response
                r = wsgi(self.app, 'PATCH', path=path, body={'row_version': '1'})
                self.assertEqual(r['status'], 502)
                self.assertNotIn('CANARY', json.dumps(r))
            remote.return_value = h.PhanHoi(409, {'ma': 'DEMO_XUNG_DOT', 'thong_diep': 'CANARY SQL',
                'request_id': str(uuid4()), 'thu_lai_duoc': False,
                'chi_tiet': [{'truong': 'CANARY', 'ma': 'SAI'}]})
            r = wsgi(self.app, 'PATCH', path=path, body={'row_version': '1'})
            self.assertEqual(r['status'], 409)
            self.assertNotIn('CANARY', json.dumps(r))
            self.assertEqual(r['body']['request_id'], r['headers']['X-Request-Id'])
            remote.side_effect = TimeoutError('CANARY')
            self.assertEqual(wsgi(self.app, 'PATCH', path=path, body={'row_version': '1'})['status'], 504)

    def test_module_chua_cai_hash_khac_khong_chuyen(self):
        self.doi_route(chu_so_huu='module', duong_dan='/api/v1/module/crm/mau/{id}')
        remote = self.dispatcher.kenh_module = Mock()
        with patch.object(d.dang_ky, 'doc_dang_ky', return_value=[]):
            self.assertEqual(wsgi(self.app, 'PATCH', path='/api/v1/module/crm/mau/'+str(OBJ),
                                  body={'row_version': '1'})['status'], 503)
        remote.assert_not_called()

    def test_cua_module_dung_bien_nhan_rieng_va_chi_tra_sau_commit(self):
        route = route_demo('PATCH', chu_so_huu='module', duong_dan='/api/v1/module/crm/mau/{id}')
        context = d.NguCanh(str(uuid4()), USER, PN, 'crm', route.operation, route.hanh_dong,
            {'bang': 'doi_tuong', 'id': str(OBJ)}, {'row_version': '1'}, {'id': str(OBJ)}, {}, KEY)
        conn = KetNoiGia()
        with patch.object(tn, 'tra_thao_tac', return_value=None) as tra, patch.object(tn, 'ghi_thao_tac') as ghi:
            result = d.thuc_hien_module(conn, route, context, self.ma, kiem=self.kiem)
            self.assertTrue(result.da_commit)
            self.assertEqual(conn.events, ['begin', 'commit'])
            ghi.assert_called_once()
            self.assertIs(ghi.call_args.args[0], conn)
            self.assertEqual(ghi.call_args.kwargs['khoa'], KEY)
            tra.return_value = {'ket_qua': {'status': 200, 'body': result.body}}
            route.handler.reset_mock()
            d.thuc_hien_module(conn, route, context, self.ma, kiem=self.kiem)
            route.handler.assert_not_called()
            self.assertEqual(ghi.call_count, 1)
        self.tra.assert_not_called()
        self.ghi.assert_not_called()

    def test_module_xac_minh_lai_danh_tinh_va_commit_loi_khong_co_xac_nhan(self):
        route = route_demo('PATCH', chu_so_huu='module', duong_dan='/api/v1/module/crm/mau/{id}')
        context = d.NguCanh(str(uuid4()), USER, PN, 'crm', route.operation, route.hanh_dong,
            {'bang': 'doi_tuong', 'id': str(OBJ)}, {'row_version': '1'}, {'id': str(OBJ)}, {}, KEY)
        conn = KetNoiGia()
        self.xac.return_value = None
        with self.assertRaises(h.LoiHTTP) as caught:
            d.thuc_hien_module(conn, route, context, self.ma, kiem=self.kiem)
        self.assertEqual(caught.exception.status, 404)
        route.handler.assert_not_called()
        self.xac.return_value = SimpleNamespace(nguoi_dung_id=USER)
        conn.loi_commit = True
        with patch.object(tn, 'tra_thao_tac', return_value=None), patch.object(tn, 'ghi_thao_tac'):
            with self.assertRaises(RuntimeError):
                d.thuc_hien_module(conn, route, context, self.ma, kiem=self.kiem)
        self.assertEqual(conn.events[-1], 'rollback')

    def test_module_kiem_input_truoc_handler_va_truoc_transaction(self):
        route = route_demo('PATCH', chu_so_huu='module', duong_dan='/api/v1/module/crm/mau/{id}',
                           truong_cas=('row_version',), query_schema={'type': 'object', 'additionalProperties': False,
                               'properties': {'loc': {'type': 'string'}}})
        context = d.NguCanh(str(uuid4()), USER, PN, 'crm', route.operation, route.hanh_dong,
            {'bang': 'doi_tuong', 'id': str(OBJ)}, {'row_version': '1'}, {'id': str(OBJ)}, {}, KEY)
        validators = [KiemTest()] + ([d.KiemSchema()] if CO_SCHEMA else [])
        invalid = [replace(context, body={'row_version': 1}),
                   replace(context, body={'row_version': '1', 'actor': 'ADMIN'}),
                   replace(context, body={'row_version': '9223372036854775808'}),
                   replace(context, path={'id': 'sai'}), replace(context, path={'id': str(OBJ), 'actor': 'ADMIN'}),
                   replace(context, query={'actor': 'ADMIN'}), replace(context, query={'loc': 1})]
        for kiem in validators:
            for bad in invalid:
                with self.subTest(validator=type(kiem).__name__, context=bad):
                    conn = KetNoiGia()
                    with patch.object(tn, 'tra_thao_tac') as tra, patch.object(tn, 'ghi_thao_tac') as ghi:
                        with self.assertRaises(h.LoiHTTP) as caught:
                            d.thuc_hien_module(conn, route, bad, self.ma, kiem=kiem)
                        self.assertEqual(caught.exception.status, 422)
                        self.assertEqual(conn.events, [])
                        self.assertEqual(conn.info.transaction_status, 0)
                        self.assertEqual(route.handler.call_count, 0)
                        tra.assert_not_called()
                        ghi.assert_not_called()
        self.xac.assert_not_called()

    def test_job_dedupe_tach_operation_va_nguoi_tao(self):
        context = d.NguCanh(str(uuid4()), USER, PN, 'crm', 'CRM.IN', 'CRM:TIEP_NHAN:LAP',
            {'bang': 'doi_tuong', 'id': str(OBJ)}, {}, {}, {}, KEY)
        original = d.khoa_viec(context)
        self.assertEqual(original, d.khoa_viec(replace(context, request_id=str(uuid4()))))
        self.assertNotEqual(original, d.khoa_viec(replace(context, operation='CRM.OUT')))
        self.assertNotEqual(original, d.khoa_viec(replace(context, nguoi_dung_id=uuid4())))
        self.assertNotIn(KEY, original)

    def test_trang_keyset_mac_dinh_toi_da_con_tiep_va_het(self):
        self.doi_route('GET', dau_ra={200: LIST}, thu_tu='ten,id')
        rows = [{'id': str(UUID(int=n)), 'row_version': '1'} for n in range(1, 28)]
        def handler(conn, ctx):
            n = ctx.trang.kich_thuoc
            keys = [['DEMO', row['id']] for row in rows]
            chosen = [(r, k) for r, k in zip(rows, keys) if ctx.trang.khoa_sau is None or k > ctx.trang.khoa_sau][:n+1]
            return d.DuLieuTrang([r for r, k in chosen], [k for r, k in chosen])
        self.route.handler.side_effect = handler
        first = wsgi(self.app)
        self.assertEqual(len(first['body']['danh_sach']), 25)
        self.assertTrue(first['body']['con_tiep'])
        token = first['body']['con_tro_tiep']
        last = wsgi(self.app, path='/api/v1/mau/'+str(OBJ)+'?con_tro='+token)
        self.assertEqual(len(last['body']['danh_sach']), 2)
        self.assertEqual((last['body']['con_tiep'], last['body']['con_tro_tiep']), (False, None))
        for size in ('0', '101', 'true'):
            self.assertEqual(wsgi(self.app, path='/api/v1/mau/'+str(OBJ)+'?kich_thuoc_trang='+size)['status'], 400)
        all_rows = wsgi(self.app, path='/api/v1/mau/'+str(OBJ)+'?kich_thuoc_trang=100')
        self.assertEqual(len(all_rows['body']['danh_sach']), 27)

    def test_cursor_gan_user_pn_loc_thu_tu_va_het_han_chong_sua(self):
        ctx = {'user': str(USER), 'pn': str(PN), 'loc': 'a', 'thu_tu': 'ten,id'}
        key = ['DEMO', str(OBJ)]
        token = self.cursor.tao(ctx, key)
        self.assertEqual(self.cursor.doc(token, ctx), key)
        for bad in (ctx | {'user': str(uuid4())}, ctx | {'pn': str(uuid4())},
                    ctx | {'loc': 'b'}, ctx | {'thu_tu': 'id,ten'}):
            with self.assertRaises(h.LoiHTTP):
                self.cursor.doc(token, bad)
        for bad in ('?'*50, token[:20]+'A'+token[21:], token+'x', ''):
            with self.assertRaises(h.LoiHTTP):
                self.cursor.doc(bad, ctx)
        with self.assertRaises(h.LoiHTTP):
            d.ConTro(b'DEMO'*8, dong_ho=lambda: 1900).doc(token, ctx)

    def test_trang_sai_thu_tu_hoac_trung_khoa_502(self):
        self.doi_route('GET', dau_ra={200: LIST}, thu_tu='ten,id')
        row = {'id': str(OBJ), 'row_version': '1'}
        self.route.handler.return_value = d.DuLieuTrang([row, row], [['a', str(OBJ)], ['a', str(OBJ)]])
        self.assertEqual(wsgi(self.app)['status'], 502)

    def test_module_phan_trang_core_ky_cursor_khong_chia_khoa_cho_module(self):
        route = self.doi_route('GET', chu_so_huu='module', duong_dan='/api/v1/module/crm/mau/{id}',
                               phien_ban_goi='1', ma_bam_goi='a'*64, dau_ra={200: LIST}, thu_tu='id')
        rows = [{'id': str(UUID(int=i)), 'row_version': '1'} for i in range(1, 4)]
        contexts = []
        conn = KetNoiGia()
        def handler(conn, context):
            contexts.append(context)
            chosen = [row for row in rows if context.trang.khoa_sau is None or [row['id']] > context.trang.khoa_sau]
            return d.DuLieuTrang(chosen[:context.trang.kich_thuoc+1], [[r['id']] for r in chosen[:context.trang.kich_thuoc+1]])
        route.handler.side_effect = handler
        self.dispatcher.kenh_module = lambda r, c: d.thuc_hien_module(conn, r, c, self.ma, kiem=self.kiem)
        path = '/api/v1/module/crm/mau/'+str(OBJ)
        with patch.object(d.dang_ky, 'doc_dang_ky', return_value=[{
            'so_phien_ban': '1', 'ma_bam_goi': 'a'*64, 'trang_thai': 'da_cai'}]):
            first = wsgi(self.app, path=path+'?kich_thuoc_trang=2')
            self.assertEqual(first['status'], 200)
            self.assertTrue(first['body']['con_tiep'])
            last = wsgi(self.app, path=path+'?kich_thuoc_trang=2&con_tro='+first['body']['con_tro_tiep'])
        self.assertEqual(last['status'], 200)
        self.assertEqual(last['body']['danh_sach'], rows[-1:])
        self.assertIsNone(last['body']['con_tro_tiep'])
        self.assertEqual(contexts[-1].trang.khoa_sau, [rows[1]['id']])
        self.assertFalse(hasattr(contexts[-1], 'cursor'))


class RegistrySchemaTest(unittest.TestCase):
    def test_dang_ky_ghi_he_thong_loi_dung_ma_khong_them_route(self):
        for method in ('POST', 'PATCH', 'PUT', 'DELETE'):
            for che_do_phien in ('bat_buoc', 'tien_phien', 'khong'):
                with self.subTest(method=method, phien=che_do_phien):
                    registry = d.Registry()
                    route = route_demo(method, pham_vi='he_thong', phien=che_do_phien)
                    with self.assertRaises(d.LoiDangKyRoute) as caught:
                        registry.dang_ky(route)
                    self.assertEqual(caught.exception.ma, 'ROUTE_GHI_HE_THONG_CHUA_HO_TRO')
                    self.assertEqual(str(caught.exception), caught.exception.ma)
                    self.assertEqual(registry._routes, [])
                    route.handler.assert_not_called()

    def test_khai_bao_phien_pham_vi_sai_bi_tu_choi(self):
        for doi in ({'phien': None}, {'phien': 'typo'}, {'pham_vi': None}, {'pham_vi': 'typo'},
                    {'phien': 'khong'}, {'phien': 'tien_phien'},
                    {'chu_so_huu': 'module', 'duong_dan': '/api/v1/module/crm/mau/{id}', 'pham_vi': 'he_thong'}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                d.Registry().dang_ky(route_demo(**doi))

    def test_namespace_khong_wildcard_va_trung_route(self):
        registry = d.Registry()
        for path in ('/api/v1/module/m2/x', '/api/v1/module/crm/*', 'https://evil.demo/a'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                registry.dang_ky(route_demo(chu_so_huu='module', duong_dan=path))
        registry.dang_ky(route_demo())
        with self.assertRaises(ValueError):
            registry.dang_ky(route_demo(duong_dan='/api/v1/mau/{khac}'))
        with self.assertRaises(ValueError):
            registry.dang_ky(route_demo(viec_lau=True))

    def test_literal_thang_tham_so(self):
        registry = d.Registry()
        registry.dang_ky(route_demo())
        literal = route_demo(duong_dan='/api/v1/mau/so-sanh')
        registry.dang_ky(literal)
        self.assertIs(registry.tra('GET', literal.duong_dan)[0], literal)

    def test_thieu_validator_phai_503_khong_fallback(self):
        with patch.object(d.goi, '_bo_schema', side_effect=d.goi.LoiGoi('CANARY')):
            with self.assertRaises(h.LoiHTTP) as caught:
                d.KiemSchema()
        self.assertEqual(caught.exception.status, 503)

    @unittest.skipUnless(CO_SCHEMA, 'CHUA_KIEM validator production: thiếu jsonschema/referencing')
    def test_validator_202012_offline_format_truong_la_khong_ep_kieu(self):
        kiem = d.KiemSchema()
        self.assertTrue(kiem.kiem(OUT, {'id': str(OBJ), 'row_version': '1'}))
        for value in ({'id': 'sai', 'row_version': '1'}, {'id': str(OBJ), 'row_version': 1},
                      {'id': str(OBJ), 'row_version': '1', 'actor': 'ADMIN'}):
            self.assertFalse(kiem.kiem(OUT, value))
        self.assertFalse(kiem.kiem({'$ref': 'https://khong-duoc-goi.demo/schema'}, {}))
        self.assertTrue(kiem.kiem(ACCEPTED, {'viec_id': str(OBJ), 'trang_thai': 'queued', 'request_id': str(uuid4())}))
        with self.assertRaises(ValueError):
            d.KiemSchema({'urn:ktt:contract:chung.v1': {'type': 'object'}})

    @unittest.skipUnless(CO_SCHEMA, 'CHUA_KIEM schema gói runtime: thiếu jsonschema/referencing')
    def test_schema_goi_local_duoc_ghim_va_khong_de_goi_dinh_nghia_lai_core(self):
        kiem = d.KiemSchema()
        schema = dict(OUT, **{'$schema': d.goi.DRAFT, '$id': 'urn:ktt:contract:demo.v1'})
        package = d.goi.GoiDaKiem({'ma': 'crm'}, {'contract/demo.json': json.dumps(schema).encode()}, (), {}, 'a'*64)
        kiem.them_goi(package)
        self.assertTrue(kiem.kiem(d._schema_goi(package, 'contract/demo.json'), {'id': str(OBJ), 'row_version': '1'}))
        bad_schema = dict(schema, **{'$id': 'urn:ktt:contract:chung.v1'})
        bad_package = replace(package, cac_tep={'contract/demo.json': json.dumps(bad_schema).encode()})
        with self.assertRaises(ValueError):
            kiem.them_goi(bad_package)

    def test_nap_goi_chi_route_manifest_va_ghim_hash(self):
        operation = dict(ma='sua', phuong_thuc='PATCH', duong_dan='/mau/{id}', kieu='dong_bo', chong_trung=True,
                         dau_vao='urn:ktt:contract:demo.in', dau_ra='urn:ktt:contract:demo.out')
        package = d.goi.GoiDaKiem({'loai': 'module', 'ma': 'crm', 'phien_ban': '1', 'thao_tac': [operation], 'ma_loi': []},
                                  {}, (), {}, 'a'*64)
        registry = d.Registry()
        route = route_demo('PATCH', chu_so_huu='module', duong_dan='/api/v1/module/crm/mau/{id}',
                           dau_vao={'$ref': operation['dau_vao']}, dau_ra={200: {'$ref': operation['dau_ra']}})
        registry.nap_goi(package, lambda op: route)
        found, _ = registry.tra('PATCH', '/api/v1/module/crm/mau/'+str(OBJ))
        self.assertEqual((found.phien_ban_goi, found.ma_bam_goi), ('1', 'a'*64))
        with self.assertRaises(ValueError):
            d.Registry().nap_goi(package, lambda op: replace(route, method='POST'))
        for doi in ({'dau_vao': {}}, {'dau_ra': {200: {}}}):
            with self.assertRaises(ValueError):
                d.Registry().nap_goi(package, lambda op: replace(route, **doi))
        self.assertEqual(d._schema_goi(package, 'viec.v1#/$defs/da_nhan'), ACCEPTED)

    def test_nap_goi_loi_khong_dang_ky_mot_phan(self):
        op = dict(phuong_thuc='PATCH', duong_dan='/a/{id}', kieu='dong_bo', chong_trung=True,
                  dau_vao='urn:demo.in', dau_ra='urn:demo.out')
        package = d.goi.GoiDaKiem({'loai': 'module', 'ma': 'crm', 'phien_ban': '1',
                                  'thao_tac': [op, op | {'duong_dan': '/b/{id}'}], 'ma_loi': []}, {}, (), {}, 'a'*64)
        registry = d.Registry()
        def tao(operation):
            return route_demo('PATCH', chu_so_huu='module',
                duong_dan='/api/v1/module/crm/a/{id}', dau_vao={'$ref': 'urn:demo.in'}, dau_ra={200: {'$ref': 'urn:demo.out'}})
        with self.assertRaises(ValueError):
            registry.nap_goi(package, tao)
        with self.assertRaises(h.LoiHTTP) as caught:
            registry.tra('PATCH', '/api/v1/module/crm/a/'+str(OBJ))
        self.assertEqual(caught.exception.status, 404)


@unittest.skipUnless(g214.psycopg is not None and os.environ.get('KHO_PG_DSN_TEST') and CO_SCHEMA,
                     'CHUA_KIEM PG login thật: thiếu DSN/psycopg/jsonschema')
class DispatcherPostgresTest(unittest.TestCase):
    _ghi = g214.ViecPostgresTest._ghi
    _contract = g214.ViecPostgresTest._contract
    _trang_thai = g214.ViecPostgresTest._trang_thai
    _cap = g214.ViecPostgresTest._cap
    _ctx = g214.ViecPostgresTest._ctx
    _tao = g214.ViecPostgresTest._tao
    _resolver = g214.ViecPostgresTest._resolver
    _moi = g214.ViecPostgresTest._moi

    @classmethod
    def setUpClass(cls):
        g214.ViecPostgresTest.setUpClass.__func__(cls)

    def setUp(self):
        g214.ViecPostgresTest.setUp(self)
        self.conn.execute(g214.sql.SQL('GRANT UPDATE ON mod_crm.ket_qua_g214 TO {}')
                         .format(g214.sql.Identifier(self.module_login)))
        self.result_id = uuid4()
        self.conn.execute('INSERT INTO mod_crm.ket_qua_g214 VALUES (%s,%s)', (self.result_id, '1'))
        self.kiem = d.KiemSchema()
        self.calls = 0

    def _app(self, *, long=False, output=None):
        def handler(conn, context):
            self.calls += 1
            changed = conn.execute('''UPDATE mod_crm.ket_qua_g214 SET noi_dung=(noi_dung::int+1)::text
                WHERE id=%s AND noi_dung=%s RETURNING noi_dung''',
                (self.result_id, context.body['row_version'])).fetchone()
            if changed is None:
                raise viec.LoiViec('VIEC_CAS')
            if long:
                return d.ViecMoi('DEMO', self.obj, 'doi_tuong')
            return h.PhanHoi(200, {'id': str(self.result_id), 'row_version': changed[0]})
        route = route_demo('POST' if long else 'PATCH', chu_so_huu='module',
            duong_dan='/api/v1/module/crm/mau/{id}', phien_ban_goi='1', ma_bam_goi='a'*64,
            handler=handler, viec_lau=long, dau_ra={202 if long else 200: output or (ACCEPTED if long else OUT)},
            truong_cas=('row_version',),
            quyen_doc=lambda c, b: {'hanh_dong': g214.g209.XEM, 'doi_tuong': c.doi_tuong,
                'phien_ban_contract': '1', 'tai_lieu_id': str(self.tai_lieu_id), 'bien_the': 'goc'})
        registry = d.Registry()
        registry.dang_ky(route)
        def remote(route, context):
            self.job_key = d.khoa_viec(context)
            return d.thuc_hien_module(self.module, route, context, self.uy, kiem=self.kiem)
        dispatcher = d.Dispatcher(registry, ket_noi=lambda: nullcontext(self.core),
                                  kiem=self.kiem, kenh_module=remote)
        now = datetime.now(timezone.utc)
        session = h.PhienHTTP(self.nd, phien.MaBiMat('CSRF_CANARY'), lambda module, pn: self.ma, now, now)
        return h.UngDungHTTP(dispatcher, origin=ORIGIN, doc_phien=lambda sid: session)

    def _goi(self, app, *, long=False, key=KEY, pn=None, row='1', on_send=None):
        return wsgi(app, 'POST' if long else 'PATCH', path='/api/v1/module/crm/mau/'+str(self.obj),
                    body={'row_version': row}, headers={'X-Phap-Nhan-Id': str(pn or self.pn), 'Idempotency-Key': key},
                    on_send=on_send)

    def test_login_that_replay_bien_nhan_module_khong_kiem_cas_lai(self):
        app = self._app()
        for conn in (self.core, self.module):
            self.assertEqual(conn.execute('SELECT current_user,session_user').fetchone(), (conn.info.user,)*2)
        self.assertEqual(self._goi(app)['status'], 200)
        self.assertEqual(self._goi(app)['status'], 200)
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.conn.execute('SELECT noi_dung FROM mod_crm.ket_qua_g214 WHERE id=%s',
                                          (self.result_id,)).fetchone()[0], '2')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi_tai_lieu.bien_nhan_thao_tac WHERE khoa_chong_trung=%s',
                                          (KEY,)).fetchone()[0], 1)

    def test_202_chi_sau_job_va_receipt_commit(self):
        app, seen = self._app(long=True), []
        key = uuid4().hex
        def send(response):
            if response['status'] == 202:
                seen.append(self.conn.execute('SELECT count(*) FROM loi.hang_viec WHERE khoa_chong_trung=%s', (self.job_key,)).fetchone()[0])
                seen.append(self.conn.execute('SELECT count(*) FROM loi_tai_lieu.bien_nhan_thao_tac WHERE khoa_chong_trung=%s', (key,)).fetchone()[0])
        response = self._goi(app, long=True, key=key, on_send=send)
        self.assertEqual(response['status'], 202)
        self.assertEqual(seen, [1, 1])

    def test_sai_contract_rollback_job_receipt_va_nghiep_vu(self):
        app, key = self._app(long=True, output={'type': 'null'}), uuid4().hex
        self.assertEqual(self._goi(app, long=True, key=key)['status'], 502)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.hang_viec WHERE khoa_chong_trung=%s', (self.job_key,)).fetchone()[0], 0)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi_tai_lieu.bien_nhan_thao_tac WHERE khoa_chong_trung=%s', (key,)).fetchone()[0], 0)
        self.assertEqual(self.conn.execute('SELECT noi_dung FROM mod_crm.ket_qua_g214 WHERE id=%s', (self.result_id,)).fetchone()[0], '1')

    def test_cas_atomic_409_khoa_moi_khong_ghi_de(self):
        app = self._app()
        self.assertEqual(self._goi(app, key=uuid4().hex)['status'], 200)
        self.assertEqual(self._goi(app, key=uuid4().hex)['status'], 409)
        self.assertEqual(self.conn.execute('SELECT noi_dung FROM mod_crm.ket_qua_g214 WHERE id=%s', (self.result_id,)).fetchone()[0], '2')

    def test_sai_phap_nhan_bi_chan_truoc_module(self):
        app = self._app()
        self.assertEqual(self._goi(app, key=uuid4().hex, pn=self.pn_khac)['status'], 404)
        self.assertEqual(self.calls, 0)


if __name__ == '__main__':
    unittest.main()
