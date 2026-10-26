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
    MA_LOI_NHAT_KY, LOI_NHAT_KY, LOI_CAU_HINH, LOI_THAY_DOI, LOI_PHONG_NGUNG, THONG_BAO, _payload,
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
        self.recipient = {'trang_thai': 'HOAT_DONG'}
        self.room = {'phap_nhan_id': PN, 'hoat_dong': True}
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
        elif 'FROM master.nguoi_dung WHERE id=' in sql:
            r.fetchone.return_value = self.recipient
        elif 'FROM master.mtq_phong WHERE id=' in sql:
            r.fetchone.return_value = self.room
        elif 'SELECT phap_nhan_id FROM master.mtq_gan_vai WHERE id=' in sql:
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
        self.assertEqual(result['message'], 'Bản nháp đã thay đổi; tải lại trước khi lưu.')
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
        self.assertIs(result['la_admin'], False)
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
        mine = http(self.svc, HTTP.PREFIX + 'cua-toi')[1]
        self.assertFalse(mine['admin'])
        self.assertIs(mine['la_admin'], True)
        self.assertTrue(any('mtq_la_admin()' in sql for sql, _ in self.mau.c.calls))
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


def quan_tri_payload(route, *, thu_hoi=False, **kwargs):
    fields = {
        'phong': {'thao_tac': 'TAO', 'phap_nhan_id': PN, 'ma': 'KT', 'ten': 'Kế toán DEMO'},
        'gan-vai': {'thao_tac': 'CAP', 'nguoi_dung_id': USER, 'phong_id': ROOM, 'vai': 'CFO'},
        'pham-vi': {'thao_tac': 'CAP', 'gan_vai_id': DONG, 'loai': 'PHAP_NHAN', 'khoa_pham_vi': PN},
        'admin': {'thao_tac': 'CAP', 'nguoi_dung_id': USER},
    }[route]
    if thu_hoi:
        fields = {'thao_tac': 'THU_HOI', 'id': DONG}
    return {'expected_revision': 0, 'ly_do': 'Quản trị DEMO', 'khoa': str(uuid.uuid4()), **fields, **kwargs}


class MtqQuanTriMock(unittest.TestCase):
    ROUTES = ('phong', 'gan-vai', 'pham-vi', 'admin')

    def setUp(self):
        self.mau = Infrastructure()
        self.svc = MaTranThamQuyenK2(self.mau)
        self.svc._sql = MagicMock(return_value={'id': DONG, 'phap_nhan_id': PN, 'revision': 1})

    def post(self, route, body, **kwargs):
        return http(self.svc, HTTP.PREFIX + route, body, post=True, **kwargs)

    def variants(self):
        for route in self.ROUTES:
            yield route, quan_tri_payload(route), route.upper().replace('-', '_')
        update = quan_tri_payload('phong', thao_tac='SUA', id=ROOM, expected_revision=1, hoat_dong=False)
        for key in ('ma', 'phap_nhan_id'):
            update.pop(key)
        yield 'phong', update, 'PHONG'
        for route, command in (('gan-vai', 'THU_HOI_VAI'), ('pham-vi', 'THU_HOI_PHAM_VI'), ('admin', 'THU_HOI_ADMIN')):
            yield route, quan_tri_payload(route, thu_hoi=True, expected_revision=1), command

    def test_admin_cap_thu_hoi_dung_lenh_va_suy_phap_nhan(self):
        for route, original, command in self.variants():
            with self.subTest(route=route, command=command):
                p = dict(original)
                self.svc._sql.return_value = {'id': DONG, 'revision': 1}
                if route != 'admin':
                    self.svc._sql.return_value['phap_nhan_id'] = PN
                status, result = self.post(route, p)
                self.assertEqual(status, 200)
                self.assertFalse(result['lap_lai'])
                call = self.svc._sql.call_args.args
                self.assertEqual((call[1], call[2], call[4], call[5]),
                                 (p['khoa'], command, p['expected_revision'], p['ly_do']))
                data = call[3]
                self.assertNotIn('actor', data)
                self.assertNotIn('thao_tac', data)
                if command in ('GAN_VAI', 'PHAM_VI'):
                    self.assertEqual(data['phap_nhan_id'], PN)
                    self.assertNotIn('phap_nhan_id', p)
                if command == 'PHAM_VI':
                    self.assertEqual((data['khoa'], data['quan_he']), (PN, {}))
                receipt = self.mau.c.journal[-1]
                self.assertEqual(receipt[0:2], (p['khoa'], None if route == 'admin' else PN))
                self.assertIsNone(receipt[3])  # id quản trị không phải id phiên bản.
                self.assertEqual(receipt[7:9], (ADMIN, DT['dang_nhap']))

    def test_nonadmin_403_truoc_sql_va_ghi_tu_choi_sau_rollback(self):
        self.mau.c.admin = False
        for route in self.ROUTES:
            with self.subTest(route=route):
                status, result = self.post(route, quan_tri_payload(route))
                self.assertEqual((status, result['error']), (403, 'MTQ_CHI_ADMIN'))
                self.assertEqual(self.mau.trace[-2:], [('begin', DT, False), 'commit'])
                self.assertIn('rollback', self.mau.trace)
                self.assertEqual(self.mau.c.denials[-1][-2:], ('MTQ_CHI_ADMIN', 'Chỉ quản trị đang hoạt động được sửa ma trận.'))
        self.svc._sql.assert_not_called()

    def test_cas_409_tat_ca_route(self):
        error = RuntimeError('Chi tiết DEMO')
        error.diag = type('Diag', (), {'message_primary': 'MTQ_REVISION: cũ'})()
        self.svc._sql.side_effect = error
        for route in self.ROUTES:
            with self.subTest(route=route):
                status, result = self.post(route, quan_tri_payload(route, expected_revision=99))
                self.assertEqual((status, result['error'], result['message']),
                                 (409, 'MTQ_REVISION', LOI_THAY_DOI))
        self.assertEqual(self.mau.c.journal, [])

    def test_replay_ben_khong_ghi_trung_va_noi_dung_khac_409(self):
        for route in self.ROUTES:
            with self.subTest(route=route):
                self.mau.c.receipt = None
                p = quan_tri_payload(route)
                first = self.post(route, p)[1]
                receipt = self.mau.c.journal[-1]
                self.mau.c.receipt = {'actor_id': ADMIN, 'doi_tuong': json.loads(receipt[2]),
                    'loai_su_kien': receipt[5], 'sau': json.loads(receipt[6])}
                before = len(self.mau.c.journal)
                self.svc._sql.reset_mock()
                fresh = MaTranThamQuyenK2(self.mau)
                fresh._sql = self.svc._sql
                status, replay = http(fresh, HTTP.PREFIX + route, p, post=True)
                self.assertEqual((status, replay['ket_qua'], replay['lap_lai']), (200, first['ket_qua'], True))
                self.svc._sql.assert_not_called()
                self.assertEqual(len(self.mau.c.journal), before)
                status, result = self.post(route, {**p, 'ly_do': 'Nội dung khác'})
                self.assertEqual((status, result['message']), (409, THONG_BAO['MTQ_IDEMPOTENCY_KHAC']))
                self.mau.c.admin = False
                self.assertEqual(self.post(route, p)[0], 403)
                self.mau.c.admin = True

    def test_than_la_400_truoc_khoa_va_ket_noi(self):
        for route in self.ROUTES:
            p = quan_tri_payload(route)
            bad = [None, [], {**p, 'actor_id': ADMIN}, {**p, 'diff': {}}, {**p, 'quan_he': {}},
                   {**p, 'expected_revision': True}, {**p, 'expected_revision': '0'},
                   {**p, 'expected_revision': -1}, {**p, 'expected_revision': 2**63},
                   {**p, 'ly_do': ' '}, {**p, 'ly_do': 'x' * 2001}, {**p, 'khoa': 'sai'},
                   {**p, 'thao_tac': []}, {**p, 'thao_tac': 'DELETE'}]
            bad += [{k: v for k, v in p.items() if k != field}
                    for field in ('khoa', 'ly_do', 'expected_revision', 'thao_tac')]
            if route != 'phong':
                bad.append({**p, 'phap_nhan_id': PN2})
            for body in bad:
                with self.subTest(route=route, body=body):
                    app = App()
                    app.mutation_lock = MagicMock()
                    self.assertEqual(self.post(route, body, app=app)[0], 400)
                    app.mutation_lock.__enter__.assert_not_called()
                    app.crm_phien.assert_not_called()
                    app.crm.assert_not_called()
                    app._m5_ket_noi_chu.assert_not_called()
        self.svc._sql.assert_not_called()

    def test_tham_so_nghiep_vu_sai_va_khong_tron_cap_thu_hoi(self):
        cases = [('phong', {'ma': ' '}), ('phong', {'ten': 5}),
                 ('gan-vai', {'vai': 'ADMIN'}), ('gan-vai', {'nguoi_dung_id': 'sai'}),
                 ('pham-vi', {'loai': 'TU_Y'}), ('pham-vi', {'khoa_pham_vi': 'sai'}),
                 ('admin', {'nguoi_dung_id': None}), ('admin', {'id': DONG})]
        for route, changes in cases:
            with self.subTest(route=route, changes=changes):
                self.assertEqual(self.post(route, quan_tri_payload(route, **changes))[0], 400)
        self.assertEqual(self.post('phong', {'thao_tac': 'SUA', 'id': ROOM, 'hoat_dong': 'false',
            'expected_revision': 1, 'khoa': str(uuid.uuid4()), 'ly_do': 'DEMO'})[0], 400)
        for route in ('gan-vai', 'pham-vi', 'admin'):
            p = quan_tri_payload(route, thu_hoi=True, nguoi_dung_id=USER)
            self.assertEqual(self.post(route, p)[0], 400)
        self.svc._sql.assert_not_called()

    def test_phong_gan_vai_khong_con_hoat_dong_khong_cap(self):
        with patch.object(self.svc, '_one', side_effect=[None, None, None, None]):
            for route in ('gan-vai', 'pham-vi'):
                self.assertEqual(self.post(route, quan_tri_payload(route))[0], 400)
        self.svc._sql.assert_not_called()

    def test_admin_cuoi_409_va_cau_goc_trong_ly_do(self):
        self.svc._sql.side_effect = DataError('MTQ_ADMIN_CUOI', 'Chi tiết DEMO')
        status, result = self.post('admin', quan_tri_payload('admin', thu_hoi=True, expected_revision=1))
        self.assertEqual((status, result['error'], result['message']),
                         (409, 'MTQ_ADMIN_CUOI', THONG_BAO['MTQ_ADMIN_CUOI']))
        self.assertEqual(self.mau.c.denials[-1][-2:], ('MTQ_ADMIN_CUOI', 'Chi tiết DEMO'))
        self.assertEqual(self.mau.c.journal, [])

    def test_8_cau_theo_ma_va_ma_khac_cau_chung(self):
        expected = {
            'MTQ_THIEU_DONG': 'Chưa đủ 5 vai cho mỗi phòng đang dùng; bổ sung trước khi công bố.',
            'MTQ_CHUA_NOI_MTQ4': 'Chưa bật được: các phân hệ chưa nối xong với ma trận.',
            'MTQ_REVISION': 'Dữ liệu đã thay đổi; tải lại trước khi thao tác.',
            'MTQ_ADMIN_CUOI': 'Không thể thu hồi Admin hoạt động cuối cùng; cấp thêm Admin trước khi thu hồi.',
            'MTQ_PHAM_VI': 'Phạm vi không hợp lệ, khác pháp nhân hoặc gán vai đã bị thu hồi; kiểm tra lại.',
            'MTQ_CHI_ADMIN': 'Chỉ Admin đang hoạt động được quản trị ma trận thẩm quyền.',
            'MTQ_BAT_BIEN': 'Bản đã công bố hoặc lịch sử cấp quyền không thể sửa; hãy tạo bản mới.',
            'MTQ_IDEMPOTENCY_KHAC': 'Yêu cầu này đã được gửi với nội dung khác; tải lại rồi thử lại.',
        }
        for code, message in {**expected, 'MTQ_KHAC': LOI_CAU_HINH}.items():
            with self.subTest(code=code):
                error = RuntimeError('Nội dung SQL DEMO không được lộ')
                error.diag = type('Diag', (), {'message_primary': code + ': nội bộ'})()
                self.svc._sql.side_effect = error
                result = self.post('phong', quan_tri_payload('phong'))[1]
                self.assertEqual(result, {'error': code, 'message': message})
                self.assertEqual(self.mau.c.denials[-1][-2:], (code, code + ': nội bộ'))

    def test_token_va_phien_bat_buoc_tung_route(self):
        for route in self.ROUTES:
            with self.subTest(route=route):
                p = quan_tri_payload(route)
                self.assertEqual(self.post(route, p, token=False)[0], 403)
                app = App()
                app.crm_phien.side_effect = DataError('CRM_PHIEN', 'Không có phiên')
                self.assertEqual(self.post(route, p, app=app)[0], 403)
        self.svc._sql.assert_not_called()

    def test_nhat_ky_loi_503_tung_route(self):
        for route in self.ROUTES:
            with self.subTest(route=route):
                self.mau.c.fail_audit = RuntimeError('DEMO lỗi ghi')
                self.assertEqual(self.post(route, quan_tri_payload(route)),
                                 (503, {'error': MA_LOI_NHAT_KY, 'message': LOI_NHAT_KY}))
                self.assertEqual(self.mau.c.journal, [])
                self.assertEqual(self.mau.trace[-1], 'rollback')
                self.mau.c.admin = False
                self.mau.c.fail_denial = RuntimeError('DEMO lỗi ghi từ chối')
                self.assertEqual(self.post(route, quan_tri_payload(route))[0], 503)
                self.mau.c.admin = True

    def test_trung_va_khoa_ngoai_chuyen_ma_khong_lo_chi_tiet(self):
        messages = {'MTQ_DA_CAP': 'Đã cấp trước đó; tải lại để xem bản hiện hành.',
                    'MTQ_KHONG_THAY': 'Pháp nhân, phòng hoặc người dùng không tồn tại.'}
        for route in self.ROUTES:
            for state, code, status in (('23505', 'MTQ_DA_CAP', 409),
                                        ('23503', 'MTQ_KHONG_THAY', 400)):
                with self.subTest(route=route, state=state):
                    error = RuntimeError('DETAIL: dữ liệu hồ sơ DEMO')
                    error.sqlstate = state
                    primary = 'duplicate key violates unique constraint' if state == '23505' else 'insert violates foreign key constraint'
                    error.diag = type('Diag', (), {'message_primary': primary,
                        'message_detail': 'dữ liệu hồ sơ DEMO'})()
                    self.svc._sql.side_effect = error
                    self.assertEqual(self.post(route, quan_tri_payload(route)),
                                     (status, {'error': code, 'message': messages[code]}))
                    self.assertEqual(self.mau.c.denials[-1][-2:], (code, primary))
                    self.assertIn('rollback', self.mau.trace)
                    self.assertEqual(self.mau.trace[-1], 'commit')
        self.assertEqual(self.mau.c.journal, [])

    def test_nguoi_nhan_mat_hoac_ngung_khong_thanh_loi_nguoi_thao_tac(self):
        messages = {'MTQ_KHONG_THAY': 'Pháp nhân, phòng hoặc người dùng không tồn tại.',
                    'MTQ_NGUOI_NHAN_NGUNG': 'Người được cấp không còn hoạt động.'}
        for route in ('gan-vai', 'admin'):
            for recipient, code in ((None, 'MTQ_KHONG_THAY'),
                                    ({'trang_thai': 'DUNG'}, 'MTQ_NGUOI_NHAN_NGUNG')):
                with self.subTest(route=route, recipient=recipient):
                    self.mau.c.recipient = recipient
                    self.assertEqual(self.post(route, quan_tri_payload(route)),
                                     (400, {'error': code, 'message': messages[code]}))
                    self.assertEqual(self.mau.c.denials[-1][-2:], (code, messages[code]))
        self.svc._sql.assert_not_called()
        calls = [sql for sql, _ in self.mau.c.calls]
        self.assertLess(next(i for i, sql in enumerate(calls) if 'pg_advisory_xact_lock' in sql),
                        next(i for i, sql in enumerate(calls) if 'FOR SHARE' in sql))
        self.mau.c.recipient = {'trang_thai': 'HOAT_DONG'}
        self.svc._sql.side_effect = DataError('MTQ_DANH_TINH', 'Người thao tác DEMO')
        self.assertEqual(self.post('admin', quan_tri_payload('admin')),
                         (403, {'error': 'MTQ_DANH_TINH', 'message': THONG_BAO['MTQ_DANH_TINH']}))

    def test_phong_mat_va_phong_ngung_co_cau_rieng(self):
        for room, code, message in ((None, 'MTQ_KHONG_THAY', THONG_BAO['MTQ_KHONG_THAY']),
                                   ({'phap_nhan_id': PN, 'hoat_dong': False}, 'MTQ_PHAM_VI', LOI_PHONG_NGUNG)):
            with self.subTest(room=room):
                self.mau.c.room = room
                self.assertEqual(self.post('gan-vai', quan_tri_payload('gan-vai')),
                                 (400, {'error': code, 'message': message}))
                self.assertEqual(self.mau.c.denials[-1][-2:], (code, message))
        self.svc._sql.assert_not_called()

    def test_thu_hoi_revision_cu_khong_noi_ban_nhap(self):
        self.svc._sql.side_effect = DataError('MTQ_REVISION', 'Bản ghi cũ DEMO')
        for route in ('gan-vai', 'admin', 'pham-vi'):
            with self.subTest(route=route):
                self.assertEqual(self.post(route, quan_tri_payload(route, thu_hoi=True, expected_revision=1)),
                                 (409, {'error': 'MTQ_REVISION', 'message': LOI_THAY_DOI}))

    def test_sql_chi_co_ma_van_ghi_ly_do_co_nghia(self):
        error = RuntimeError('MTQ_REVISION')
        error.diag = type('Diag', (), {'message_primary': 'MTQ_REVISION'})()
        self.svc._sql.side_effect = error
        self.assertEqual(self.post('phong', quan_tri_payload('phong', expected_revision=99))[0], 409)
        self.assertEqual(self.mau.c.denials[-1][-2:], ('MTQ_REVISION', LOI_THAY_DOI))

    def test_khoi_phuc_de_lat_sau_khong_mo_route(self):
        from kho_tri_thuc.k2.sql_ma_tran_tham_quyen import MA_TRAN_THAM_QUYEN_SQL
        sql = next(s for s in MA_TRAN_THAM_QUYEN_SQL if s.startswith('CREATE FUNCTION master.mtq_cau_hinh_ghi('))
        self.assertNotIn("'KHOI_PHUC'", sql)
        self.assertEqual(self.post('khoi-phuc', {})[0], 404)
        self.svc._sql.assert_not_called()


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

    def post(self, route, p, *, login=None):
        return http(self.svc, HTTP.PREFIX + route, p, post=True, app=App(login or self.admin[1]))

    def count_log(self, key):
        return self.c.execute('SELECT count(*) AS n FROM nhat_ky.mtq_thay_doi WHERE request_id=%s::uuid', (key,)).fetchone()['n']

    def assert_denied(self, route, p, status, code, message):
        self.assertEqual(self.post(route, p), (status, {'error': code, 'message': message}))
        self.assertEqual(self.count_log(p['khoa']), 0)
        denial = self.c.execute('SELECT ma,ly_do FROM nhat_ky.mtq_tu_choi WHERE request_id=%s::uuid',
                                (p['khoa'],)).fetchone()
        self.assertEqual(denial['ma'], code)
        self.assertTrue(denial['ly_do'])
        self.assertNotEqual(denial['ly_do'], code)

    def test_loi_trung_sql_that_409_va_audit(self):
        assignment = self.svc.gan_vai(self.admin[1], quan_tri_payload('gan-vai',
            nguoi_dung_id=self.user[0], phong_id=self.room))['ket_qua']
        scope = quan_tri_payload('pham-vi', gan_vai_id=assignment['id'], khoa_pham_vi=self.pn)
        self.svc.pham_vi(self.admin[1], scope)
        cases = (
            ('phong', quan_tri_payload('phong', phap_nhan_id=self.pn, ma='KT')),
            ('gan-vai', quan_tri_payload('gan-vai', nguoi_dung_id=self.user[0], phong_id=self.room)),
            ('gan-vai', quan_tri_payload('gan-vai', nguoi_dung_id=self.user[0], phong_id=self.room, vai='NGUOI_XEM')),
            ('pham-vi', {**scope, 'khoa': str(uuid.uuid4())}),
            ('admin', quan_tri_payload('admin', nguoi_dung_id=self.admin[0])),
        )
        for route, p in cases:
            with self.subTest(route=route, vai=p.get('vai')):
                self.assert_denied(route, p, 409, 'MTQ_DA_CAP',
                                   'Đã cấp trước đó; tải lại để xem bản hiện hành.')

    def test_doi_tuong_mat_va_nguoi_nhan_ngung_sql_that_400(self):
        missing = str(uuid.uuid4())
        cases = (
            ('phong', quan_tri_payload('phong', phap_nhan_id=missing)),
            ('gan-vai', quan_tri_payload('gan-vai', nguoi_dung_id=missing, phong_id=self.room)),
            ('gan-vai', quan_tri_payload('gan-vai', nguoi_dung_id=self.user[0], phong_id=missing)),
            ('admin', quan_tri_payload('admin', nguoi_dung_id=missing)),
        )
        for route, p in cases:
            with self.subTest(route=route, p=p):
                self.assert_denied(route, p, 400, 'MTQ_KHONG_THAY',
                                   'Pháp nhân, phòng hoặc người dùng không tồn tại.')
        stopped = self.c.execute("""INSERT INTO master.nguoi_dung
            (ten,dang_nhap,vai_tro,mo_phong,trang_thai) VALUES ('DEMO ngừng',%s,'XEM',true,'DUNG')
            RETURNING id""", ('MO_PHONG_MTQ2D_' + uuid.uuid4().hex,)).fetchone()
        for route, extra in (('admin', {}), ('gan-vai', {'phong_id': self.room})):
            with self.subTest(route=route):
                p = quan_tri_payload(route, nguoi_dung_id=str(stopped['id']), **extra)
                self.assert_denied(route, p, 400, 'MTQ_NGUOI_NHAN_NGUNG',
                                   'Người được cấp không còn hoạt động.')

    def test_cau_theo_ngu_canh_sql_that(self):
        assignment = self.svc.gan_vai(self.admin[1], quan_tri_payload('gan-vai',
            nguoi_dung_id=self.user[0], phong_id=self.room))['ket_qua']
        admin = self.c.execute('SELECT id,revision FROM master.mtq_admin WHERE nguoi_dung_id=%s::uuid AND thu_hoi_luc IS NULL',
                               (self.admin[0],)).fetchone()
        for route, item in (('gan-vai', assignment), ('admin', admin)):
            with self.subTest(route=route):
                p = quan_tri_payload(route, thu_hoi=True, id=str(item['id']), expected_revision=item['revision'] - 1)
                self.assert_denied(route, p, 409, 'MTQ_REVISION',
                                   'Dữ liệu đã thay đổi; tải lại trước khi thao tác.')
        self.svc.phong(self.admin[1], {'thao_tac': 'SUA', 'id': self.room, 'hoat_dong': False,
            'expected_revision': 1, 'ly_do': 'DEMO ngừng phòng', 'khoa': str(uuid.uuid4())})
        self.assert_denied('gan-vai', quan_tri_payload('gan-vai', nguoi_dung_id=self.admin[0], phong_id=self.room),
                           400, 'MTQ_PHAM_VI', LOI_PHONG_NGUNG)
        status, result = http(self.svc, HTTP.PREFIX + 'ma-tran', app=App(self.user[1]))
        self.assertEqual(status, 403)
        self.assertIn('xem Quyền của tôi', result['message'])

    def test_la_admin_theo_phien_va_thu_hoi_sql_that(self):
        def mine(login):
            status, result = http(self.svc, HTTP.PREFIX + 'cua-toi', app=App(login))
            self.assertEqual(status, 200)
            self.assertIs(result['admin'], False)
            return result['la_admin']
        self.assertIs(mine(self.admin[1]), True)
        self.assertIs(mine(self.user[1]), False)
        login = 'MO_PHONG_MTQ2D_' + uuid.uuid4().hex
        other = self.c.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro,mo_phong) VALUES ('DEMO MTQ2d',%s,'XEM',true) RETURNING id",
                               (login,)).fetchone()
        granted = self.svc.admin(self.admin[1], quan_tri_payload('admin', nguoi_dung_id=str(other['id'])))['ket_qua']
        try:
            self.assertIs(mine(login), True)
        finally:
            self.svc.admin(self.admin[1], quan_tri_payload('admin', thu_hoi=True,
                id=granted['id'], expected_revision=granted['revision']))
        self.assertIs(mine(login), False)

    def check_route(self, route, p):
        """Đi qua HTTP/service và master.mtq_cau_hinh_ghi thật, không mock SQL."""
        self.assertEqual(self.post(route, p, login=self.user[1])[0], 403)
        self.assertEqual(self.post(route, {**p, 'expected_revision': 999})[0], 409)
        self.assertEqual(self.count_log(p['khoa']), 0)
        self.assertEqual(self.post(route, {**p, 'actor_id': self.admin[0]})[0], 400)
        status, result = self.post(route, p)
        self.assertEqual(status, 200, result)
        count = self.count_log(p['khoa'])
        self.assertGreaterEqual(count, 2)  # Diff trigger + biên nhận HTTP.
        replay_status, replay = self.post(route, p)
        self.assertEqual((replay_status, replay['ket_qua'], replay['lap_lai']), (200, result['ket_qua'], True))
        self.assertEqual(self.count_log(p['khoa']), count)
        self.assertEqual(self.post(route, {**p, 'ly_do': 'Nội dung khác DEMO'})[0], 409)
        receipts = self.c.execute("SELECT actor_id,actor_login,phien_ban_id FROM nhat_ky.mtq_thay_doi WHERE request_id=%s::uuid AND doi_tuong_bang='HTTP'", (p['khoa'],)).fetchall()
        self.assertEqual(len(receipts), 1)
        self.assertEqual((str(receipts[0]['actor_id']), receipts[0]['actor_login'], receipts[0]['phien_ban_id']),
                         (self.admin[0], self.admin[1], None))
        changes = self.c.execute("SELECT actor_id,actor_login,truoc,sau FROM nhat_ky.mtq_thay_doi WHERE request_id=%s::uuid AND doi_tuong_bang<>'HTTP'", (p['khoa'],)).fetchall()
        self.assertTrue(changes)
        for change in changes:
            self.assertEqual((str(change['actor_id']), change['actor_login']), (self.admin[0], self.admin[1]))
            self.assertEqual(str(change['sau']['id']), result['ket_qua']['id'])
            if p['thao_tac'] in ('CAP', 'TAO'):
                self.assertIsNone(change['truoc'])
            else:
                self.assertEqual(change['sau']['revision'], change['truoc']['revision'] + 1)
        return result['ket_qua']

    def test_route_phong_tao_sua_cas_replay_403_than_la(self):
        p = quan_tri_payload('phong', phap_nhan_id=self.pn, ma='KT2')
        room = self.check_route('phong', p)
        update = {'id': room['id'], 'thao_tac': 'SUA', 'ten': 'Kế toán mới DEMO', 'hoat_dong': False,
                  'expected_revision': room['revision'], 'ly_do': 'Ngừng phòng DEMO', 'khoa': str(uuid.uuid4())}
        changed = self.check_route('phong', update)
        self.assertEqual((changed['ten'], changed['hoat_dong'], changed['revision']),
                         ('Kế toán mới DEMO', False, room['revision'] + 1))

    def test_route_gan_vai_pham_vi_cap_thu_hoi_cas_replay_403_than_la(self):
        assignment = self.check_route('gan-vai', quan_tri_payload('gan-vai', nguoi_dung_id=self.user[0], phong_id=self.room))
        self.assertEqual(assignment['phap_nhan_id'], self.pn)
        scope = self.check_route('pham-vi', quan_tri_payload('pham-vi', gan_vai_id=assignment['id'], khoa_pham_vi=self.pn))
        self.assertEqual(scope['phap_nhan_id'], self.pn)
        for route, item in (('pham-vi', scope), ('gan-vai', assignment)):
            p = quan_tri_payload(route, thu_hoi=True, id=item['id'], expected_revision=item['revision'])
            revoked = self.check_route(route, p)
            self.assertIsNotNone(revoked['thu_hoi_luc'])
            self.assertEqual(revoked['thu_hoi_boi'], self.admin[0])
            self.assertEqual(revoked['revision'], item['revision'] + 1)

    def test_route_admin_cap_thu_hoi_va_admin_cuoi_bi_chan(self):
        current = self.c.execute('SELECT id,revision FROM master.mtq_admin WHERE nguoi_dung_id=%s::uuid AND thu_hoi_luc IS NULL', (self.admin[0],)).fetchone()
        last = quan_tri_payload('admin', thu_hoi=True, id=str(current['id']), expected_revision=current['revision'])
        status, result = self.post('admin', last)
        self.assertEqual((status, result['error'], result['message']), (409, 'MTQ_ADMIN_CUOI', THONG_BAO['MTQ_ADMIN_CUOI']))
        self.assertEqual(self.count_log(last['khoa']), 0)
        denial = self.c.execute('SELECT ma,ly_do FROM nhat_ky.mtq_tu_choi WHERE request_id=%s::uuid', (last['khoa'],)).fetchone()
        self.assertEqual((denial['ma'], denial['ly_do']), ('MTQ_ADMIN_CUOI', 'MTQ_ADMIN_CUOI: không được thu hồi Admin hoạt động cuối'))
        # Danh tính mới riêng, không để người thử 403 trở thành Admin.
        login = 'MO_PHONG_MTQ2C_' + uuid.uuid4().hex
        other = self.c.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro,mo_phong) VALUES ('DEMO MTQ2c',%s,'XEM',true) RETURNING id", (login,)).fetchone()
        granted = self.check_route('admin', quan_tri_payload('admin', nguoi_dung_id=str(other['id'])))
        try:
            p = quan_tri_payload('admin', thu_hoi=True, id=granted['id'], expected_revision=granted['revision'])
            revoked = self.check_route('admin', p)
            self.assertIsNotNone(revoked['thu_hoi_luc'])
        finally:
            # Chỉ thu hồi qua lệnh thật nếu một assertion trước thu hồi thất bại.
            row = self.c.execute('SELECT revision FROM master.mtq_admin WHERE id=%s::uuid AND thu_hoi_luc IS NULL', (granted['id'],)).fetchone()
            if row is not None:
                self.svc.admin(self.admin[1], quan_tri_payload('admin', thu_hoi=True,
                    id=granted['id'], expected_revision=row['revision']))

    def test_route_pham_vi_sai_phap_nhan_giu_ma_goc(self):
        assignment = self.svc.gan_vai(self.admin[1], quan_tri_payload('gan-vai', nguoi_dung_id=self.user[0], phong_id=self.room))['ket_qua']
        p = quan_tri_payload('pham-vi', gan_vai_id=assignment['id'], khoa_pham_vi=PN2)
        status, result = self.post('pham-vi', p)
        self.assertEqual((status, result['error'], result['message']), (400, 'MTQ_PHAM_VI', THONG_BAO['MTQ_PHAM_VI']))
        self.assertEqual(self.count_log(p['khoa']), 0)
        denial = self.c.execute('SELECT ma,ly_do FROM nhat_ky.mtq_tu_choi WHERE request_id=%s::uuid', (p['khoa'],)).fetchone()
        self.assertEqual((denial['ma'], denial['ly_do']), ('MTQ_PHAM_VI', 'MTQ_PHAM_VI: sai pháp nhân'))


if __name__ == '__main__':
    unittest.main()
