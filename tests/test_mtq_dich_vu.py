"""MTQ-2: mock + PostgreSQL tùy chọn; không mở server hoặc PostgreSQL.

PG chỉ tạo CSDL kho_test_* mới khi lead cấp KHO_PG_DSN_TEST; giữ nguyên
CSDL sau test, không xóa file/dữ liệu/vai. HTTP gọi Handler trực tiếp.
"""

from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import MagicMock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2.ma_tran_tham_quyen import MaTranThamQuyenK2, VAI, _payload
from kho_tri_thuc.giao_dien import ma_tran_tham_quyen as HTTP

ADMIN, USER, PN, PN2, ROOM, PB, DONG = (str(uuid.uuid4()) for _ in range(7))
DT = {'id': ADMIN, 'dang_nhap': 'MO_PHONG_MTQ_ADMIN'}
VERSION = {'id': PB, 'phap_nhan_id': PN, 'revision': 1, 'trang_thai': 'NHAP'}
CELL = {'module': 'CRM', 'man': 'TIEP_NHAN', 'hanh_dong': 'DUYET', 'cho_phep': True}


def payload(**kwargs):
    return {'expected_revision': 0, 'ly_do': 'Cấu hình DEMO', 'khoa': str(uuid.uuid4()),
            'dong': [{'phong_id': ROOM, 'vai': 'CFO', 'gioi_han_vnd': None, 'o': [dict(CELL)]}], **kwargs}


class Connection:
    """Seam driver có rollback; không mô phỏng lại lệnh cấu hình SQL."""
    def __init__(self):
        self.admin = True
        self.receipt = None
        self.calls = []
        self.journal = []
        self.denials = []
        self.fail_audit = False
        self.fail_denial = False

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        r = MagicMock()
        if 'mtq_la_admin()' in sql:
            r.fetchone.return_value = {'ok': self.admin}
        elif 'actor_id,doi_tuong,loai_su_kien,sau' in sql:
            r.fetchone.return_value = self.receipt
        elif 'SELECT 1 FROM nhat_ky.mtq_thay_doi' in sql:
            r.fetchone.return_value = None
        elif 'FROM master.mtq_phien_ban WHERE id=' in sql:
            r.fetchone.return_value = dict(VERSION)
        elif 'FROM master.mtq_phong WHERE id=' in sql:
            r.fetchone.return_value = {'phap_nhan_id': PN}
        elif 'INSERT INTO nhat_ky.mtq_thay_doi' in sql:
            if self.fail_audit:
                raise RuntimeError('DEMO lỗi ghi biên nhận')
            self.journal.append(params)
        elif 'INSERT INTO nhat_ky.mtq_tu_choi' in sql:
            if self.fail_denial:
                raise RuntimeError('DEMO lỗi audit từ chối')
            self.denials.append(params)
        else:
            r.fetchone.return_value = None
        return r


class Infrastructure:
    def __init__(self):
        self.c = Connection()
        self.trace = []
        self.danh_tinh = MagicMock(return_value=DT)

    @contextmanager
    def _tx(self, dt, *, rr=False):
        self.trace.append(('begin', dt, rr))
        before = copy.deepcopy(self.c.journal)
        try:
            yield self.c
        except Exception:
            self.c.journal = before
            self.trace.append('rollback')
            raise
        else:
            self.trace.append('commit')


class Handler:
    def __init__(self, path, body=None, token=True):
        self.path, self.body, self.token = path, body, token
        self.auth = []

    def authorize(self, private=False):
        self.auth.append(private)
        if not self.token:
            raise DataError('SESSION_TOKEN', 'Token DEMO sai')

    def crm_sid(self):
        return 'cookie-may-chu'

    def json_body(self):
        return self.body

    def send_content(self, status, value):
        return status, value


class App:
    def __init__(self, login=DT['dang_nhap']):
        self.mutation_lock = threading.RLock()
        self.login = login
        self.crm_phien = MagicMock(return_value=('cookie-may-chu', login, False))

    @staticmethod
    def _crm_db(fn, *args):
        return fn(*args)


@contextmanager
def service(svc):
    yield svc


def http(svc, path, body=None, *, post=False, token=True, query=None, app=None):
    h = Handler(path, body, token)
    with patch.object(HTTP, 'dich_vu', lambda app: service(svc)):
        result = HTTP.dieu_huong(h, app or App(), post, path.split('?')[0], query or {})
    return result


class MtqMock(unittest.TestCase):
    def setUp(self):
        self.mau = Infrastructure()
        self.svc = MaTranThamQuyenK2(self.mau)

    def sql_save(self):
        self.svc._sql = MagicMock(side_effect=[dict(VERSION),
            {'phien_ban': {**VERSION, 'revision': 2}, 'doi_tuong': {'id': DONG}},
            {'phien_ban': {**VERSION, 'revision': 3}, 'doi_tuong': CELL}])

    def test_admin_luu_dung_lenh_cas_actor_pn_may_chu(self):
        self.sql_save()
        status, result = http(self.svc, HTTP.PREFIX + 'luu-nhap', payload(), post=True)
        self.assertEqual(status, 200)
        self.assertEqual(result['ket_qua']['revision'], 3)
        calls = self.svc._sql.call_args_list
        self.assertEqual([x.args[2] for x in calls], ['NHAP', 'DONG', 'O'])
        self.assertEqual([x.args[4] for x in calls], [0, 1, 2])
        self.assertEqual(calls[0].args[3]['phap_nhan_id'], PN)
        self.assertEqual(self.mau.c.journal[0][-3:-1], (ADMIN, DT['dang_nhap']))
        self.mau.danh_tinh.assert_called_once_with(DT['dang_nhap'])

    def test_admin_cong_bo(self):
        v = {**VERSION, 'revision': 2, 'trang_thai': 'DA_CONG_BO'}
        self.svc._sql = MagicMock(return_value={'phien_ban': v})
        p = {'phien_ban_id': PB, 'expected_revision': 1, 'khoa': str(uuid.uuid4()), 'ly_do': 'Công bố DEMO'}
        status, result = http(self.svc, HTTP.PREFIX + 'cong-bo', p, post=True)
        self.assertEqual(status, 200)
        self.assertEqual(result['ket_qua'], v)
        self.assertEqual(self.svc._sql.call_args.args[2], 'CONG_BO')
        self.assertFalse(any('KICH_HOAT' in str(c) for c in self.mau.c.calls))

    def test_nonadmin_403_va_audit_sau_rollback(self):
        self.mau.c.admin = False
        self.svc._sql = MagicMock()
        for action in ('luu-nhap', 'cong-bo', 'kich-hoat'):
            p = payload() if action == 'luu-nhap' else {'phien_ban_id': PB, 'expected_revision': 1, 'khoa': str(uuid.uuid4()), 'ly_do': 'DEMO'}
            status, result = http(self.svc, HTTP.PREFIX + action, p, post=True)
            self.assertEqual((status, result['error']), (403, 'MTQ_CHI_ADMIN'))
        self.svc._sql.assert_not_called()
        self.assertEqual(len(self.mau.c.denials), 3)
        self.assertIn('rollback', self.mau.trace)
        self.assertEqual(self.mau.trace[-1], 'commit')
        self.assertEqual(http(self.svc, HTTP.PREFIX + 'nhat-ky')[0], 403)

    def test_cas_409_khong_ghi_de(self):
        self.svc._sql = MagicMock()
        p = payload(phien_ban_id=PB, expected_revision=10)
        status, result = http(self.svc, HTTP.PREFIX + 'luu-nhap', p, post=True)
        self.assertEqual((status, result['error']), (409, 'MTQ_REVISION'))
        self.svc._sql.assert_not_called()
        self.assertEqual(self.mau.c.journal, [])

    def test_sql_readiness_409_va_khong_tat_legacy(self):
        self.svc._sql = MagicMock(side_effect=DataError('MTQ_CHUA_NOI_MTQ4', 'Chưa bao phủ'))
        p = {'phien_ban_id': PB, 'expected_revision': 0, 'khoa': str(uuid.uuid4()), 'ly_do': 'DEMO'}
        self.assertEqual(http(self.svc, HTTP.PREFIX + 'kich-hoat', p, post=True)[0], 409)
        self.assertIs(self.svc._sql.call_args.args[3]['bat'], True)
        p['bat'] = False
        self.assertEqual(http(self.svc, HTTP.PREFIX + 'kich-hoat', p, post=True)[0], 400)

    def test_replay_ben_va_khac_noi_dung_409(self):
        p = payload()
        self.sql_save()
        first = self.svc.luu_nhap(DT['dang_nhap'], p)
        receipt = self.mau.c.journal[0]
        self.mau.c.receipt = {'actor_id': ADMIN, 'doi_tuong': json.loads(receipt[2]),
                            'loai_su_kien': receipt[5], 'sau': json.loads(receipt[6])}
        self.svc._sql.reset_mock()
        second = MaTranThamQuyenK2(self.mau).luu_nhap(DT['dang_nhap'], p)
        self.assertEqual(second['ket_qua'], first['ket_qua'])
        self.assertTrue(second['lap_lai'])
        self.svc._sql.assert_not_called()
        self.assertEqual(len(self.mau.c.journal), 1)
        p['ly_do'] = 'Đổi lý do'
        self.assertEqual(http(self.svc, HTTP.PREFIX + 'luu-nhap', p, post=True)[0], 409)
        self.mau.c.admin = False
        self.assertEqual(http(self.svc, HTTP.PREFIX + 'luu-nhap', p, post=True)[0], 403)

    def test_audit_failure_rollback_khong_thanh_cong(self):
        self.sql_save()
        self.mau.c.fail_audit = True
        with self.assertRaisesRegex(RuntimeError, 'biên nhận'):
            self.svc.luu_nhap(DT['dang_nhap'], payload())
        self.assertEqual(self.mau.trace[-1], 'rollback')
        self.assertEqual(self.mau.c.journal, [])
        self.mau.c.admin = False
        self.mau.c.fail_denial = True
        with self.assertRaisesRegex(RuntimeError, 'audit từ chối'):
            self.svc.luu_nhap(DT['dang_nhap'], payload())

    def test_sql_exception_ma_an_toan_va_audit_sau_rollback(self):
        exc = RuntimeError('DEMO chi tiết không được trả cho browser')
        exc.diag = type('Diag', (), {'message_primary': 'MTQ_REVISION: chi tiết DEMO'})()
        self.svc._sql = MagicMock(side_effect=exc)
        status, result = http(self.svc, HTTP.PREFIX + 'luu-nhap', payload(), post=True)
        self.assertEqual((status, result['error']), (409, 'MTQ_REVISION'))
        self.assertNotIn('chi tiết DEMO', result['message'])
        self.assertEqual(len(self.mau.c.denials), 1)

    def test_actor_phap_nhan_tham_so_la_400(self):
        for key in ('actor', 'actor_id', 'dang_nhap', 'phap_nhan_id', 'bat', 'request_id', 'admin'):
            with self.subTest(key=key):
                self.assertEqual(http(self.svc, HTTP.PREFIX + 'luu-nhap', payload(**{key: ADMIN}), post=True)[0], 400)
        for p in (None, [], {'expected_revision': 0}):
            self.assertEqual(http(self.svc, HTTP.PREFIX + 'luu-nhap', p, post=True)[0], 400)
        p = payload()
        p['dong'][0]['o'][0]['actor'] = ADMIN
        self.assertEqual(http(self.svc, HTTP.PREFIX + 'luu-nhap', p, post=True)[0], 400)
        for url in ('ma-tran?actor=', 'nhat-ky?phap_nhan_id=', 'cua-toi?x=&x=1', 'luu-nhap?x='):
            self.assertEqual(http(self.svc, HTTP.PREFIX + url, payload(), post=url.startswith('luu'))[0], 400)

    def test_tien_null_zero_va_tick_strict(self):
        for value, expected in ((None, None), ('', None), (0, '0'), ('0005', '5'), ('99999999999999999999', '99999999999999999999')):
            p = payload()
            p['dong'][0]['gioi_han_vnd'] = value
            self.assertEqual(_payload(p, luu=True)['dong'][0]['gioi_han_vnd'], expected)
        for value in (True, False, -1, 1.2, 'NaN', 'Infinity', '-1', '1.0', '1e3', '9' * 21, '１２'):
            p = payload()
            p['dong'][0]['gioi_han_vnd'] = value
            with self.subTest(value=value), self.assertRaises(DataError):
                _payload(p, luu=True)
        for value in (1, 'true', None):
            p = payload()
            p['dong'][0]['o'][0]['cho_phep'] = value
            with self.assertRaises(DataError):
                _payload(p, luu=True)

    def test_phong_khac_pn_khong_luu(self):
        self.svc._one = MagicMock(side_effect=[None, VERSION, {'phap_nhan_id': PN2}])
        self.svc._sql = MagicMock()
        with self.assertRaises(DataError):
            self.svc.luu_nhap(DT['dang_nhap'], payload(phien_ban_id=PB, expected_revision=1))
        self.svc._sql.assert_not_called()

    def test_doc_cua_toi_loc_sql_truoc_khi_doc_o(self):
        self.mau.c.admin = False
        self.svc._many = MagicMock(return_value=[])
        result = self.svc.ma_tran(DT['dang_nhap'])
        self.assertFalse(result['admin'])
        self.assertEqual(result['phien_ban'], [])
        sql, args = self.svc._many.call_args_list[0].args[1:]
        for required in ('g.nguoi_dung_id=%s::uuid', 'g.thu_hoi_luc IS NULL', 'k.bat', 'g.vai=d.vai', 'g.phong_id=d.phong_id'):
            self.assertIn(required, sql)
        self.assertEqual(args, (ADMIN,))

    def test_doc_admin_day_du_va_cua_toi_khong_lo_nguoi_khac(self):
        self.svc._many = MagicMock(return_value=[])
        self.assertTrue(self.svc.ma_tran(DT['dang_nhap'])['admin'])
        self.assertTrue(any('SELECT * FROM master.mtq_phien_ban' in str(x) for x in self.svc._many.call_args_list))
        self.svc._many.reset_mock()
        self.assertFalse(self.svc.ma_tran(DT['dang_nhap'], cua_toi=True)['admin'])
        self.assertFalse(any('SELECT * FROM master.mtq_phien_ban' in str(x) for x in self.svc._many.call_args_list))

    def test_token_csrf_phien_khong_duoc_bo_qua(self):
        self.assertEqual(http(self.svc, HTTP.PREFIX + 'ma-tran', token=False)[0], 403)
        app = App()
        app.crm_phien.side_effect = DataError('CRM_PHIEN', 'Không có phiên')
        self.assertEqual(http(self.svc, HTTP.PREFIX + 'ma-tran', app=app)[0], 403)
        from kho_tri_thuc.giao_dien.server import Handler as RealHandler
        h = Handler(HTTP.PREFIX + 'luu-nhap')
        h.headers = {'Host': '127.0.0.1:8899', 'X-KTT-Token': 'DEMO_TOKEN', 'Origin': 'https://example.invalid'}
        h.server = type('Server', (), {'server_port': 8899, 'app': type('Token', (), {'token': 'DEMO_TOKEN'})()})()
        with self.assertRaises(DataError) as cm:
            RealHandler.authorize(h, private=True)
        self.assertEqual(cm.exception.code, 'CROSS_ORIGIN')
        h.headers.pop('Origin')
        h.headers['X-KTT-Token'] = 'SAI'
        with self.assertRaises(DataError) as cm:
            RealHandler.authorize(h, private=True)
        self.assertEqual(cm.exception.code, 'SESSION_TOKEN')

    def test_khong_route_bootstrap_lenh_tuy_y_va_utf8(self):
        for post in (False, True):
            for name in ('bootstrap', 'bootstrap-admin', 'admin/bootstrap', 'sql', 'khoi-phuc', 'luu-nhap/extra'):
                path = HTTP.PREFIX + name
                self.assertFalse(HTTP.la_route(post, path))
                self.assertEqual(http(self.svc, path, payload(), post=post)[0], 404)
        for name in ('src/kho_tri_thuc/k2/ma_tran_tham_quyen.py', 'src/kho_tri_thuc/giao_dien/ma_tran_tham_quyen.py', 'tests/test_mtq_dich_vu.py'):
            raw = (ROOT / name).read_bytes()
            self.assertFalse(raw.startswith(b'\xef\xbb\xbf'))
            self.assertNotIn('\ufffd', raw.decode('utf-8'))


try:
    import psycopg
except ImportError:
    psycopg = None


@unittest.skipUnless(os.environ.get('KHO_PG_DSN_TEST') and psycopg is not None, 'NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG')
class MtqPG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from psycopg.rows import dict_row
        from kho_tri_thuc.ha_tang import postgres
        from kho_tri_thuc.k2.crm_mau import CrmMauK2
        dsn = os.environ['KHO_PG_DSN_TEST']
        db = 'kho_test_mtq2_' + uuid.uuid4().hex[:12]
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(db)))
        cls.c = psycopg.connect(make_conninfo(dsn, dbname=db), autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c)
        cls.admin, cls.user = [], []
        for target, role in ((cls.admin, 'XEM'), (cls.user, 'CFO')):
            login = 'MO_PHONG_MTQ2_' + uuid.uuid4().hex
            row = cls.c.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro,mo_phong) VALUES ('DEMO MTQ2',%s,%s,true) RETURNING id", (login, role)).fetchone()
            target.extend((str(row['id']), login))
        cls.c.execute("SELECT master.mtq_bootstrap_admin(%s::uuid,%s::uuid,'DEMO tin cậy')", (cls.admin[0], str(uuid.uuid4())))
        cls.mau = CrmMauK2(cls.c, ROOT, conn_tin_cay=cls.c)
        cls.svc = MaTranThamQuyenK2(cls.mau)

    def setUp(self):
        self.pn = str(self.c.execute("INSERT INTO master.phap_nhan (ma,ten) VALUES (%s,'DEMO MTQ2') RETURNING id", (uuid.uuid4().hex,)).fetchone()['id'])
        with self.mau._tx(self.mau.danh_tinh(self.admin[1])) as c:
            self.room = self.svc._sql(c, str(uuid.uuid4()), 'PHONG', {'phap_nhan_id': self.pn, 'ma': 'KT', 'ten': 'Kế toán DEMO'}, 0, 'DEMO')['id']

    def draft(self):
        p = payload(dong=[{'phong_id': self.room, 'vai': v, 'gioi_han_vnd': '500000000', 'o': [dict(CELL)]} for v in sorted(VAI)])
        return p, self.svc.luu_nhap(self.admin[1], p)['ket_qua']

    def request(self, version, revision=None):
        return {'phien_ban_id': version['id'], 'expected_revision': version['revision'] if revision is None else revision,
                'ly_do': 'Thử DEMO MTQ2', 'khoa': str(uuid.uuid4())}

    def test_admin_luu_cong_bo_nhat_ky_cu_moi_va_replay(self):
        p, v = self.draft()
        before = self.c.execute('SELECT count(*) AS n FROM nhat_ky.mtq_thay_doi').fetchone()['n']
        self.assertTrue(self.svc.luu_nhap(self.admin[1], p)['lap_lai'])
        self.assertEqual(before, self.c.execute('SELECT count(*) AS n FROM nhat_ky.mtq_thay_doi').fetchone()['n'])
        p2 = payload(phien_ban_id=v['id'], expected_revision=v['revision'], dong=[{'phong_id': self.room, 'vai': 'CFO', 'gioi_han_vnd': '0', 'o': [{**CELL, 'cho_phep': False}]}])
        updated = self.svc.luu_nhap(self.admin[1], p2)['ket_qua']
        log = self.svc.nhat_ky(self.admin[1])['thay_doi']
        changes = [x for x in log if x['request_id'] == p2['khoa']]
        money = next(x for x in changes if x['doi_tuong_bang'] == 'master.mtq_dong')
        cell = next(x for x in changes if x['doi_tuong_bang'] == 'master.mtq_o')
        self.assertEqual((money['truoc']['gioi_han_vnd'], money['sau']['gioi_han_vnd']), (500000000, 0))
        self.assertEqual((cell['truoc']['cho_phep'], cell['sau']['cho_phep']), (True, False))
        self.assertTrue(all(x['actor_id'] == self.admin[0] for x in changes))
        result = self.svc.cong_bo(self.admin[1], self.request(updated))['ket_qua']
        self.assertEqual(result['trang_thai'], 'DA_CONG_BO')
        self.assertFalse(self.c.execute('SELECT EXISTS(SELECT 1 FROM master.mtq_kich_hoat WHERE bat) AS bat').fetchone()['bat'])

    def test_cas_nonadmin_readiness_http_va_audit_ben(self):
        _, v = self.draft()
        app = App(self.user[1])
        self.assertEqual(http(self.svc, HTTP.PREFIX + 'cong-bo', self.request(v), post=True, app=app)[0], 403)
        app = App(self.admin[1])
        self.assertEqual(http(self.svc, HTTP.PREFIX + 'cong-bo', self.request(v, v['revision'] - 1), post=True, app=app)[0], 409)
        published = self.svc.cong_bo(self.admin[1], self.request(v))['ket_qua']
        self.assertEqual(http(self.svc, HTTP.PREFIX + 'kich-hoat', self.request(published, 0), post=True, app=app)[0], 409)
        log = self.svc.nhat_ky(self.admin[1])['tu_choi']
        self.assertTrue({'MTQ_CHI_ADMIN', 'MTQ_REVISION', 'MTQ_CHUA_NOI_MTQ4'} <= {x['ma'] for x in log})
        self.assertEqual(self.svc.ma_tran(self.user[1])['dong'], [])

    def test_audit_failure_rollback_toan_bo_save(self):
        _, v = self.draft()
        p = payload(phien_ban_id=v['id'], expected_revision=v['revision'], dong=[{'phong_id': self.room, 'vai': 'CFO', 'gioi_han_vnd': None, 'o': []}])
        # Chặn sổ HTTP sau khi SQL đã ghi tick/hạn mức để kiểm rollback thực.
        original = self.svc._save
        def fail(c, data):
            original(c, data)
            raise RuntimeError('DEMO audit thất bại')
        with patch.object(self.svc, '_save', fail), self.assertRaises(RuntimeError):
            self.svc.luu_nhap(self.admin[1], p)
        actual = self.c.execute('SELECT revision FROM master.mtq_phien_ban WHERE id=%s::uuid', (v['id'],)).fetchone()['revision']
        self.assertEqual(actual, v['revision'])
        self.assertEqual(self.c.execute('SELECT count(*) AS n FROM nhat_ky.mtq_thay_doi WHERE request_id=%s::uuid', (p['khoa'],)).fetchone()['n'], 0)

    def test_cua_toi_khong_lo_nhap_va_nguoi_khac(self):
        _, v = self.draft()
        with self.mau._tx(self.mau.danh_tinh(self.admin[1])) as c:
            for actor, role in ((self.user, 'CFO'), (self.admin, 'NGUOI_XEM')):
                self.svc._sql(c, str(uuid.uuid4()), 'GAN_VAI', {'nguoi_dung_id': actor[0], 'phap_nhan_id': self.pn,
                    'phong_id': self.room, 'vai': role}, 0, 'DEMO phạm vi')
        mine = self.svc.ma_tran(self.user[1])
        self.assertFalse(mine['admin'])
        self.assertTrue(mine['gan_vai'])
        self.assertTrue(all(x['nguoi_dung_id'] == self.user[0] for x in mine['gan_vai']))
        self.assertEqual(mine['dong'], [])  # Nháp chưa có hiệu lực dù có vai.
        self.assertEqual(mine['phien_ban'], [])
        self.assertNotIn(v['id'], json.dumps(mine))
        self.assertTrue(any(x['id'] == v['id'] for x in self.svc.ma_tran(self.admin[1])['phien_ban']))


if __name__ == '__main__':
    unittest.main()
