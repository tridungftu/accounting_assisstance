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
from kho_tri_thuc.k2.ma_tran_tham_quyen import (
    MaTranThamQuyenK2, VAI, O_HOP_LE, MAX_DONG_LUU, MAX_O_LUU,
    MA_LOI_NHAT_KY, LOI_NHAT_KY, _payload,
)
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
        self.state = []
        self.audit_rows = []

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
        elif 'LEFT JOIN master.mtq_o' in sql:
            r.__iter__.return_value = copy.deepcopy(self.state)
        elif 'FROM nhat_ky.mtq_thay_doi ORDER BY' in sql:
            columns = sql.split('FROM', 1)[0].removeprefix('SELECT').replace(' ', '').replace('\n', '').split(',')
            r.__iter__.return_value = [{k: v for k, v in row.items() if k in columns}
                                       for row in self.audit_rows[:params[0]]]
        elif 'INSERT INTO nhat_ky.mtq_thay_doi' in sql:
            if self.fail_audit:
                raise self.fail_audit
            self.journal.append(params)
        elif 'INSERT INTO nhat_ky.mtq_tu_choi' in sql:
            if self.fail_denial:
                raise self.fail_denial
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
        self.mutation_lock = threading.Lock()
        self.login = login
        self.crm_phien = MagicMock(return_value=('cookie-may-chu', login, False))
        self.root = ROOT
        self.crm = MagicMock(return_value=MagicMock())
        self._m5_ket_noi_chu = MagicMock(return_value=MagicMock())

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
        self.mau.c.fail_audit = ValueError('DEMO lỗi ghi biên nhận')
        status, result = http(self.svc, HTTP.PREFIX + 'luu-nhap', payload(), post=True)
        self.assertEqual((status, result), (503, {'error': MA_LOI_NHAT_KY, 'message': LOI_NHAT_KY}))
        self.assertEqual(self.mau.trace[-1], 'rollback')
        self.assertEqual(self.mau.c.journal, [])
        self.mau.c.admin = False
        self.mau.c.fail_denial = DataError('DEMO_AUDIT', 'DEMO lỗi ghi từ chối')
        self.svc._sql.reset_mock()
        status, result = http(self.svc, HTTP.PREFIX + 'luu-nhap', payload(), post=True)
        self.assertEqual((status, result), (503, {'error': MA_LOI_NHAT_KY, 'message': LOI_NHAT_KY}))
        self.svc._sql.assert_not_called()
        self.assertEqual(self.mau.c.denials, [])

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
        result = self.svc.ma_tran(DT['dang_nhap'], cua_toi=True)
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

    def test_get_ma_tran_nonadmin_403_truoc_doc_du_lieu(self):
        self.mau.c.admin = False
        self.svc._many = MagicMock(return_value=[])
        status, result = http(self.svc, HTTP.PREFIX + 'ma-tran')
        self.assertEqual((status, result['message']),
                         (403, 'Chỉ quản trị xem được toàn bộ ma trận; xem Quyền của tôi.'))
        self.svc._many.assert_not_called()
        self.assertEqual(http(self.svc, HTTP.PREFIX + 'cua-toi')[0], 200)

    def test_body_sai_400_khong_khoa_khong_mo_ket_noi(self):
        bad = [None, [], payload(actor_id=ADMIN), payload(khoa='sai'),
               payload(expected_revision='1')]
        nested = payload()
        nested['dong'][0]['o'][0]['actor_id'] = ADMIN
        bad.append(nested)
        for action in ('luu-nhap', 'cong-bo', 'kich-hoat'):
            for body in bad:
                with self.subTest(action=action, body=body):
                    app = App()
                    # Giữ sẵn Lock: đọc body trong khóa sẽ treo; dùng thread có hạn chờ.
                    app.mutation_lock.acquire()
                    h = Handler(HTTP.PREFIX + action, body)
                    output = []
                    thread = threading.Thread(target=lambda: output.append(
                        HTTP.dieu_huong(h, app, True, h.path, {})), daemon=True)
                    try:
                        thread.start()
                        thread.join(1)
                        self.assertFalse(thread.is_alive(), 'Body sai đang đợi khóa')
                    finally:
                        app.mutation_lock.release()
                        thread.join(1)
                    self.assertEqual(output[0][0], 400)
                    app.crm_phien.assert_not_called()
                    app.crm.assert_not_called()
                    app._m5_ket_noi_chu.assert_not_called()
        app = App()
        h = Handler(HTTP.PREFIX + 'luu-nhap')
        h.json_body = MagicMock(side_effect=ValueError('JSON sai DEMO'))
        self.assertEqual(HTTP.dieu_huong(h, app, True, h.path, {})[0], 400)
        app._m5_ket_noi_chu.assert_not_called()

    def test_dich_vu_that_khong_treo_nha_khoa_dong_chu(self):
        for failure in (None, 'service', 'factory'):
            with self.subTest(failure=failure):
                app = App()
                h = Handler(HTTP.PREFIX + 'ma-tran')
                owner = app._m5_ket_noi_chu.return_value
                output, errors = [], []
                def run():
                    try:
                        output.append(HTTP.dieu_huong(h, app, False, h.path, {}))
                    except Exception as exc:
                        errors.append(exc)
                with patch('kho_tri_thuc.k2.crm_mau.CrmMauK2', return_value=self.mau) as factory:
                    if failure == 'factory':
                        factory.side_effect = ValueError('DEMO khởi tạo lỗi')
                    self.mau.c.admin = failure != 'service'
                    thread = threading.Thread(target=run, daemon=True)
                    thread.start()
                    thread.join(2)
                    self.assertFalse(thread.is_alive(), 'dich_vu thật bị treo với Lock')
                self.assertEqual(errors, [])
                self.assertEqual(output[0][0], 200 if failure is None else 403 if failure == 'service' else 400)
                owner.close.assert_called_once_with()
                app.crm.assert_called_once_with()
                factory.assert_called_once_with(app.crm.return_value.conn, ROOT / 'crm-g',
                    conn_tin_cay=owner, hom_nay=app.crm.return_value.hom_nay)
                self.assertTrue(app.mutation_lock.acquire(blocking=False))
                app.mutation_lock.release()

    def current_row(self, *, money=None, tick=True):
        self.mau.c.state = [{'id': DONG, 'phong_id': ROOM, 'vai': 'CFO',
                            'gioi_han_vnd': money, **CELL, 'cho_phep': tick}]

    def test_luu_khong_doi_khong_goi_lenh_ghi_cau_hinh(self):
        self.current_row(money=100)
        p = payload(phien_ban_id=PB, expected_revision=1)
        p['dong'][0]['gioi_han_vnd'] = '000100'
        self.svc._sql = MagicMock()
        result = self.svc.luu_nhap(DT['dang_nhap'], p)
        self.assertEqual(result['ket_qua'], VERSION)
        self.svc._sql.assert_not_called()
        self.assertEqual(len(self.mau.c.journal), 1)  # Vẫn có biên nhận để replay.
        self.assertEqual(sum('LEFT JOIN master.mtq_o' in sql for sql, _ in self.mau.c.calls), 1)
        self.assertEqual(sum('mtq_phien_ban WHERE id=' in sql for sql, _ in self.mau.c.calls), 1)
        receipt_sql = next(sql for sql, _ in self.mau.c.calls if 'actor_id,doi_tuong,loai_su_kien,sau' in sql)
        self.assertIn("doi_tuong_bang='HTTP'", receipt_sql)
        self.assertNotIn('LIKE', receipt_sql)

    def test_luu_chi_ghi_phan_doi_va_revision_tung_thay_doi(self):
        for money, tick, commands in ((None, False, ['O']), ('5', True, ['DONG']), ('5', False, ['DONG', 'O'])):
            with self.subTest(commands=commands):
                self.current_row(money=money, tick=tick)
                self.svc._sql = MagicMock(side_effect=[
                    {'phien_ban': {**VERSION, 'revision': 2 + i}, 'doi_tuong': {'id': DONG}}
                    for i in range(len(commands))])
                result = self.svc.luu_nhap(DT['dang_nhap'], payload(phien_ban_id=PB, expected_revision=1))
                calls = self.svc._sql.call_args_list
                self.assertEqual([c.args[2] for c in calls], commands)
                self.assertEqual([c.args[4] for c in calls], list(range(1, 1 + len(commands))))
                self.assertEqual(result['ket_qua']['revision'], 1 + len(commands))

    def test_o_chua_co_va_khong_tick_khong_ghi(self):
        self.mau.c.state = [{'id': DONG, 'phong_id': ROOM, 'vai': 'CFO', 'gioi_han_vnd': None,
                            'module': None, 'man': None, 'hanh_dong': None, 'cho_phep': None}]
        p = payload(phien_ban_id=PB, expected_revision=1)
        p['dong'][0]['o'][0]['cho_phep'] = False
        self.svc._sql = MagicMock()
        self.svc.luu_nhap(DT['dang_nhap'], p)
        self.svc._sql.assert_not_called()

    def test_sao_chep_doc_hien_trang_mot_lan_bo_qua_o_giong(self):
        self.current_row()
        self.svc._sql = MagicMock(return_value=dict(VERSION))
        self.svc.luu_nhap(DT['dang_nhap'], payload(nguon_id=PB))
        self.assertEqual([c.args[2] for c in self.svc._sql.call_args_list], ['NHAP'])
        self.assertEqual(sum('LEFT JOIN master.mtq_o' in sql for sql, _ in self.mau.c.calls), 1)

    def test_gioi_han_than_5_vai_mot_phong_theo_danh_muc(self):
        cells = [{'module': m, 'man': man, 'hanh_dong': a, 'cho_phep': False} for m, man, a in sorted(O_HOP_LE)]
        rows = [{'phong_id': ROOM, 'vai': v, 'gioi_han_vnd': None, 'o': copy.deepcopy(cells)} for v in sorted(VAI)]
        self.assertEqual(MAX_DONG_LUU, 5)
        self.assertEqual(sum(len(r['o']) for r in _payload(payload(dong=rows), luu=True)['dong']), MAX_O_LUU)
        for bad in (rows + [rows[0]], [{**rows[0], 'o': cells + [cells[0]]}],
                    [rows[0], {**rows[1], 'phong_id': str(uuid.uuid4())}]):
            with self.assertRaises(DataError):
                _payload(payload(dong=bad), luu=True)

    def test_doc_o_mot_truy_van_chi_cac_dong_da_loc(self):
        for mine in (False, True):
            with self.subTest(cua_toi=mine):
                ids = [DONG, str(uuid.uuid4())]
                def many(c, sql, params=()):
                    if 'FROM master.mtq_dong' in sql:
                        return [{'id': k} for k in ids]
                    if 'FROM master.mtq_o' in sql:
                        return [{'dong_id': ids[0], **CELL}]
                    return []
                self.svc._many = MagicMock(side_effect=many)
                result = self.svc.ma_tran(DT['dang_nhap'], cua_toi=mine)
                self.assertEqual([r['o'] for r in result['dong']], [[CELL], []])
                calls = [c for c in self.svc._many.call_args_list if 'FROM master.mtq_o' in c.args[1]]
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0].args[2], (ids,))
                self.assertIn('ANY(%s::uuid[])', calls[0].args[1])

    def test_nhat_ky_gioi_han_moi_nhat_khong_lo_vai_csdl(self):
        self.mau.c.audit_rows = [{'id': str(uuid.uuid4()), 'loai_su_kien': 'HTTP_LUU_NHAP',
                                 'boi_csdl': 'chu_bang_demo'} for _ in range(201)]
        result = self.svc.nhat_ky(DT['dang_nhap'])
        self.assertEqual(len(result['thay_doi']), 200)
        self.assertNotIn('boi_csdl', json.dumps(result))
        self.assertNotIn('chu_bang_demo', json.dumps(result))
        queries = [(sql, args) for sql, args in self.mau.c.calls if 'FROM nhat_ky.' in sql]
        self.assertEqual(len(queries), 2)
        for sql, args in queries:
            self.assertNotIn('SELECT *', sql)
            self.assertNotIn('boi_csdl', sql)
            self.assertIn('ORDER BY luc DESC,id DESC LIMIT %s', sql)
            self.assertEqual(args, (200,))
        self.mau.c.calls.clear()
        self.svc.nhat_ky(DT['dang_nhap'], gioi_han=10)
        self.assertEqual([args for sql, args in self.mau.c.calls if 'FROM nhat_ky.' in sql], [(10,), (10,)])
        for limit in (0, -1, 201, True, '10'):
            with self.assertRaises(DataError):
                self.svc.nhat_ky(DT['dang_nhap'], gioi_han=limit)

    def test_trigger_ghi_nhat_ky_loi_la_503_khong_ghi_tu_choi(self):
        error = ValueError('DEMO không được lộ')
        error.diag = type('Diag', (), {'context': 'PL/pgSQL function master.mtq_ghi_vet() line 20 at SQL statement'})()
        c = MagicMock()
        c.execute.side_effect = error
        with patch.object(self.svc, '_save', side_effect=lambda *_: MaTranThamQuyenK2._sql(c, '', '', {}, 0, '')):
            status, result = http(self.svc, HTTP.PREFIX + 'luu-nhap', payload(), post=True)
        self.assertEqual((status, result), (503, {'error': MA_LOI_NHAT_KY, 'message': LOI_NHAT_KY}))
        self.assertEqual(self.mau.c.denials, [])
        self.assertEqual(self.mau.trace[-1], 'rollback')

    def test_cau_nguoi_dung_khong_co_tu_ky_thuat(self):
        import ast
        for name in ('k2', 'giao_dien'):
            tree = ast.parse((ROOT / 'src' / 'kho_tri_thuc' / name / 'ma_tran_tham_quyen.py').read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    # Chỉ câu hiển thị tiếng Việt; bỏ mã SQL, tên khóa và docstring.
                    if any(ch in node.value for ch in 'ầềệượảớạịồôơư') and '\n' not in node.value:
                        for word in ('UUID', 'Revision', 'revision', 'snapshot', 'boolean', 'CSDL từ chối'):
                            self.assertNotIn(word, node.value)

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
        self.assertEqual(self.svc.ma_tran(self.user[1], cua_toi=True)['dong'], [])

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
        mine = self.svc.ma_tran(self.user[1], cua_toi=True)
        self.assertFalse(mine['admin'])
        self.assertTrue(mine['gan_vai'])
        self.assertTrue(all(x['nguoi_dung_id'] == self.user[0] for x in mine['gan_vai']))
        self.assertEqual(mine['dong'], [])  # Nháp chưa có hiệu lực dù có vai.
        self.assertEqual(mine['phien_ban'], [])
        self.assertNotIn(v['id'], json.dumps(mine))
        self.assertTrue(any(x['id'] == v['id'] for x in self.svc.ma_tran(self.admin[1])['phien_ban']))


if __name__ == '__main__':
    unittest.main()
