"""XS-2b: mock + PG/engine giả; không mở server, không xóa tệp/CSDL.

PG tự tạo kho_test_*, migrate thật, mọi lời gọi worker dưới app_web với danh
tính thật; owner chỉ dựng fixture/giả lập đồng hồ. Không đọc bảng module.
Chạy: PYTHONPATH=src python -B -X utf8 -m unittest discover -s tests
      -p test_xs2_worker.py -v
Thiếu Python: NOT_RUN; PG thiếu DSN/psycopg: skip để lead chạy sau.
"""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
from threading import Barrier, Event, Lock
import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from kho_tri_thuc.ha_tang import hang_viec as hv
from kho_tri_thuc.ha_tang.chay_engine import ChayEngine
from kho_tri_thuc.ha_tang.danh_ba_engine import DanhBaEngine
from kho_tri_thuc.ha_tang.engine import Engine, KhaiBaoEngine, KetQuaXuLy, hash_du_lieu

try:
    import psycopg
except ImportError:
    psycopg = None

DSN = os.environ.get('KHO_PG_DSN_TEST')


class EngineGia(Engine):
    def __init__(self, xu_ly=None, version='v1'):
        super().__init__(KhaiBaoEngine('E-GIA', version, dict, dict))
        self.ham = xu_ly or (lambda x: KetQuaXuLy('XONG', 'DA_XONG', 'Đã xử lý mẫu giả.', x))
        self.so_lan = 0
        self.lock = Lock()

    def xu_ly(self, dau_vao):
        with self.lock:
            self.so_lan += 1
        return self.ham(dau_vao)


class HangViecPython(unittest.TestCase):
    def test_ham_sql_tham_so_hoa_khong_tu_commit_ke_ca_dict_row(self):
        c = MagicMock(spec=['cursor'])
        cur = c.cursor.return_value.__enter__.return_value
        pn, key, worker, token, ref = (uuid4() for _ in range(5))
        calls = [
            (lambda: hv.tao_viec(c, "E-'_%s", 2, "khoa_'_%s", ref,
                                 phap_nhan_id=pn, module='M2'),
             'SELECT viec.tao(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS r',
             (pn, 'M2', "E-'_%s", 2, "khoa_'_%s", ref, False, 3, 60, None)),
            (lambda: hv.gia_han(c, key, worker, token, phap_nhan_id=pn),
             'SELECT viec.gia_han(%s,%s,%s,%s,%s) AS r', (pn, key, worker, token, 120)),
            (lambda: hv.tien_do(c, key, worker, token, 20, phap_nhan_id=pn),
             'SELECT viec.tien_do(%s,%s,%s,%s,%s) AS r', (pn, key, worker, token, 20)),
            (lambda: hv.ket_thuc(c, key, worker, token, 'XONG', phap_nhan_id=pn,
                                 ket_qua_id=ref),
             'SELECT viec.ket_thuc(%s,%s,%s,%s,%s,%s,%s) AS r',
             (pn, key, worker, token, 'XONG', ref, None)),
            (lambda: hv.thu_lai(c, key, worker, token, 'GIA_LOI', phap_nhan_id=pn),
             'SELECT viec.thu_lai(%s,%s,%s,%s,%s) AS r', (pn, key, worker, token, 'GIA_LOI')),
            (lambda: hv.yeu_cau_dung(c, key, phap_nhan_id=pn),
             'SELECT viec.yeu_cau_dung(%s,%s) AS r', (pn, key)),
            (lambda: hv.trang_thai_lease(c, key, worker, token, phap_nhan_id=pn),
             'SELECT viec.trang_thai_lease(%s,%s,%s,%s) AS r', (pn, key, worker, token)),
        ]
        for row in ((ref,), {'r': ref}):
            for fn, statement, params in calls:
                with self.subTest(statement=statement, dict_row=isinstance(row, dict)):
                    cur.fetchone.return_value = row
                    self.assertEqual(fn(), ref)
                    cur.execute.assert_called_with(statement, params)
        viec = {'id': str(key)}
        for row in ((viec,), {'r': viec}, None):
            cur.fetchone.return_value = row
            self.assertEqual(hv.nhan(c, worker, phap_nhan_id=pn, module='M2'),
                             None if row is None else viec)
            cur.execute.assert_called_with(
                'SELECT to_jsonb(v) AS r FROM viec.nhan(%s,%s,%s,%s) v', (pn, 'M2', worker, 120))

    def test_loi_sql_truyen_ra_caller(self):
        c = MagicMock(spec=['cursor'])
        error = RuntimeError('Lỗi SQL giả')
        c.cursor.return_value.__enter__.return_value.execute.side_effect = error
        with self.assertRaises(RuntimeError) as cm:
            hv.yeu_cau_dung(c, uuid4(), phap_nhan_id=uuid4())
        self.assertIs(cm.exception, error)


class WorkerPython(unittest.TestCase):
    def setUp(self):
        self.engine = EngineGia()
        self.db = DanhBaEngine()
        self.db.dang_ky(self.engine)
        self.depth = 0
        self.events = []
        self.conn = object()

        @contextmanager
        def tx():
            self.depth += 1
            try:
                yield self.conn
            except Exception:
                self.events.append('rollback')
                raise
            else:
                self.events.append('commit')
            finally:
                self.depth -= 1

        self.worker = ChayEngine(self.db, tx, phap_nhan_id=uuid4(), module='M2')
        self.luu = MagicMock(return_value=uuid4())
        self.nap = MagicMock(return_value={'gia': 1})
        self.worker.dang_ky('E-GIA', 1, ma_engine='E-GIA', phien_ban_engine='v1',
                           nap_dau_vao=self.nap, luu_ket_qua=self.luu)
        self.job = {'id': str(uuid4()), 'loai': 'E-GIA', 'phien_ban': 1,
                    'lease_token': str(uuid4()), 'co_tac_dong_ngoai': False}
        self.hv = patch.multiple(hv, nhan=MagicMock(return_value=self.job),
                                 trang_thai_lease=MagicMock(return_value={
                                     'con_giu': True, 'yeu_cau_dung': False}),
                                 tien_do=MagicMock(return_value=True),
                                 ket_thuc=MagicMock(return_value=True),
                                 thu_lai=MagicMock(return_value=True))
        self.hv.start()
        self.addCleanup(self.hv.stop)

    def test_engine_ngoai_giao_dich_va_luu_co_bang_chung(self):
        def run(x):
            self.assertEqual(self.depth, 0)
            return KetQuaXuLy('XONG', 'DA_XONG', 'Mẫu giả.', x)
        self.engine.ham = run
        self.assertTrue(self.worker.chay_mot())
        ket_qua = self.luu.call_args.args[2]
        self.assertEqual(ket_qua.bang_chung.hash_vao, hash_du_lieu({'gia': 1}))
        self.assertEqual(ket_qua.bang_chung.phien_ban_engine, 'v1')
        self.assertEqual(hv.ket_thuc.call_args.args[-1], 'XONG')
        self.assertNotIn('rollback', self.events)

    def test_cas_tu_choi_rollback_callback_luu(self):
        hv.ket_thuc.return_value = False
        with self.assertLogs('kho_tri_thuc.ha_tang.chay_engine', level='WARNING') as log:
            self.assertTrue(self.worker.chay_mot())
        self.luu.assert_called_once()
        self.assertEqual(self.events[-1], 'rollback')
        self.assertIn('WORKER_MAT_LEASE', log.output[0])
        self.assertEqual(hv.ket_thuc.call_count, 1)

    def test_dung_sau_nap_khong_goi_engine(self):
        hv.trang_thai_lease.side_effect = [
            {'con_giu': True, 'yeu_cau_dung': False},
            {'con_giu': True, 'yeu_cau_dung': True},
            {'con_giu': True, 'yeu_cau_dung': True}]
        self.worker.chay_mot()
        self.assertEqual(self.engine.so_lan, 0)
        self.luu.assert_not_called()
        self.assertEqual(hv.ket_thuc.call_args.args[-1], 'DA_DUNG')

    def test_mat_lease_khong_luu_khong_ket_thuc(self):
        hv.trang_thai_lease.return_value = {'con_giu': False, 'yeu_cau_dung': None}
        with self.assertLogs('kho_tri_thuc.ha_tang.chay_engine', level='WARNING'):
            self.worker.chay_mot()
        self.nap.assert_not_called()
        self.luu.assert_not_called()
        hv.ket_thuc.assert_not_called()

    def test_ngoai_le_khong_log_noi_dung_nhay_cam(self):
        def run(x):
            raise RuntimeError('NOI_DUNG_NHAY_CAM_GIA')
        self.engine.ham = run
        for ngoai, tt in ((False, 'LOI'), (True, 'CHUA_RO')):
            self.job['co_tac_dong_ngoai'] = ngoai
            with self.assertLogs('kho_tri_thuc.ha_tang.chay_engine', level='ERROR') as log:
                self.worker.chay_mot()
            self.assertEqual(hv.ket_thuc.call_args.args[-1], tt)
            self.assertEqual(hv.ket_thuc.call_args.kwargs['ma_loi'], 'WORKER_NGOAI_LE')
            self.assertNotIn('NOI_DUNG_NHAY_CAM_GIA', ''.join(log.output))

    def test_cho_va_loi_dung_ham_sql_khong_tu_retry(self):
        for tt in ('CHO', 'LOI'):
            self.engine.ham = lambda x: KetQuaXuLy(tt, 'CHO_GIA', 'Lý do giả.')
            hv.ket_thuc.reset_mock()
            hv.thu_lai.reset_mock()
            self.worker.chay_mot()
            if tt == 'CHO':
                self.assertEqual(hv.ket_thuc.call_args.args[-1], 'CHO')
                self.assertEqual(hv.ket_thuc.call_args.kwargs['ma_loi'], 'CHO_GIA')
                hv.thu_lai.assert_not_called()
            else:
                hv.thu_lai.assert_called_once()
                hv.ket_thuc.assert_not_called()
        self.assertEqual(self.engine.so_lan, 2)

    def test_thieu_dang_ky_khong_fallback_engine(self):
        self.job['phien_ban'] = 2
        with self.assertLogs('kho_tri_thuc.ha_tang.chay_engine', level='ERROR'):
            self.worker.chay_mot()
        self.assertEqual(self.engine.so_lan, 0)
        self.assertEqual(hv.ket_thuc.call_args.kwargs['ma_loi'], 'WORKER_NGOAI_LE')

    def test_vong_poll_dung_khong_nhan_them(self):
        dung = Event()
        dung.set()
        self.worker.chay(dung)
        hv.nhan.assert_not_called()
        hv.nhan.return_value = None
        self.assertFalse(self.worker.chay_mot())


@unittest.skipUnless(DSN and psycopg is not None,
                     'NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG')
class WorkerPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = 'kho_test_xs2b_' + uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as c:
            c.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0")
                      .format(sql.Identifier(cls.db)))
        cls.test_dsn = make_conninfo(DSN, dbname=cls.db)
        with psycopg.connect(cls.test_dsn, autocommit=True) as c:
            postgres.migrate(c)
            with c.transaction():
                login = 'MO_PHONG_XS2B_ADMIN_' + uuid4().hex
                actor = c.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro) "
                                  "VALUES ('Admin giả XS2B',%s,'XEM') RETURNING id",
                                  (login,)).fetchone()[0]
                c.execute("SELECT master.mtq_bootstrap_admin(%s,%s,'Admin giả XS2B')", (actor, uuid4()))
                cls.admin_actor = actor, login
                # Bảng riêng của test lưu DTO/bằng chứng giả, không đụng bảng module.
                c.execute('CREATE TABLE public.xs2b_ket_qua '
                          '(id uuid PRIMARY KEY, viec_id uuid NOT NULL, noi_dung jsonb NOT NULL)')
                c.execute('GRANT SELECT, INSERT ON public.xs2b_ket_qua TO app_web')

    def setUp(self):
        self.pn, self.pn2 = uuid4(), uuid4()
        self.actor = uuid4(), 'MO_PHONG_XS2B_' + uuid4().hex
        self.ref = uuid4()
        with psycopg.connect(self.test_dsn, autocommit=True) as c:
            with c.transaction():
                for pn in (self.pn, self.pn2):
                    c.execute("INSERT INTO master.phap_nhan (id,ma,ten) "
                              "VALUES (%s,%s,'Pháp nhân giả XS2B')", (pn, 'XS2B_' + uuid4().hex))
                c.execute("INSERT INTO master.nguoi_dung (id,ten,dang_nhap,vai_tro) "
                          "VALUES (%s,'Người giả XS2B',%s,'XEM')", self.actor)
                for pn in (self.pn, self.pn2):
                    c.execute('INSERT INTO master.phan_quyen (nguoi_dung_id,phap_nhan_id,module) '
                              'VALUES (%s,%s,%s)', (self.actor[0], pn, ['M2']))
        self.engine = EngineGia()
        self.danh_ba = DanhBaEngine()
        self.danh_ba.dang_ky(self.engine)
        self.nap_hook = None
        self.luu_hook = None

    @contextmanager
    def tx(self, actor=None):
        with psycopg.connect(self.test_dsn, autocommit=True) as c:
            with c.transaction():
                key, login = actor or self.actor
                c.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true), "
                          "set_config('ktt.nguoi_dung_dang_nhap',%s,true)", (str(key), login))
                c.execute('SET LOCAL ROLE app_web')
                c.execute("SET LOCAL statement_timeout = '5s'")
                self.assertEqual(c.execute('SELECT current_user').fetchone()[0], 'app_web')
                yield c

    def owner(self, statement, params):
        with psycopg.connect(self.test_dsn, autocommit=True) as c:
            c.execute(statement, params)

    def tao(self, *, pn=None, ngoai=False, toi_da=3):
        with self.tx() as c:
            return hv.tao_viec(c, 'E-GIA', 1, uuid4().hex, self.ref,
                               phap_nhan_id=pn or self.pn, module='M2',
                               co_tac_dong_ngoai=ngoai, toi_da_lan_thu=toi_da, thu_lai_giay=1)

    def nap(self, c, viec):
        # Không SELECT bảng module: dữ liệu giả từ callback đăng ký + UUID tham chiếu.
        self.assertEqual(viec['tham_chieu_id'], str(self.ref))
        if self.nap_hook:
            self.nap_hook(viec)
        return {'gia': 'Mẫu giả XS2B'}

    def luu(self, c, viec, ket_qua):
        key = uuid4()
        c.execute('INSERT INTO public.xs2b_ket_qua VALUES (%s,%s,%s::jsonb)',
                  (key, viec['id'], json.dumps(asdict(ket_qua), default=str, ensure_ascii=False)))
        if self.luu_hook:
            self.luu_hook(viec)
        return key

    def worker(self, *, pn=None, lease=30, nhip=None, tx=None):
        w = ChayEngine(self.danh_ba, tx or self.tx, phap_nhan_id=pn or self.pn,
                       module='M2', lease_giay=lease, gia_han_giay=nhip)
        w.dang_ky('E-GIA', 1, ma_engine='E-GIA', phien_ban_engine='v1',
                  nap_dau_vao=self.nap, luu_ket_qua=self.luu)
        return w

    def doc(self, key):
        with self.tx() as c:
            return c.execute('SELECT to_jsonb(v) FROM viec.hang_viec v WHERE id=%s', (key,)).fetchone()[0]

    def ket_qua(self, key):
        with self.tx() as c:
            return c.execute('SELECT id,noi_dung FROM public.xs2b_ket_qua WHERE viec_id=%s',
                             (key,)).fetchall()

    def het_lease(self, key):
        self.owner("UPDATE viec.hang_viec SET lease_den=clock_timestamp()-interval '1 second' "
                   'WHERE id=%s', (key,))

    def den_luot(self, key):
        self.owner("UPDATE viec.hang_viec SET thu_lai_sau=clock_timestamp()-interval '1 second' "
                   'WHERE id=%s', (key,))

    def tat(self, pn):
        with self.tx(self.admin_actor) as c:
            c.execute("SELECT master.module_doi_che_do('M2',%s,'TAT','Mẫu giả XS2B',0)", (pn,))

    def test_xong_ghi_ket_qua_va_bang_chung_engine(self):
        key = self.tao()
        self.assertTrue(self.worker().chay_mot())
        viec = self.doc(key)
        rows = self.ket_qua(key)
        self.assertEqual(viec['trang_thai'], 'XONG')
        self.assertEqual(viec['tien_do'], 100)
        self.assertEqual(len(rows), 1)
        self.assertEqual(viec['ket_qua_id'], str(rows[0][0]))
        bc = rows[0][1]['bang_chung']
        self.assertEqual((bc['ma_engine'], bc['phien_ban_engine']), ('E-GIA', 'v1'))
        self.assertEqual(bc['hash_vao'], hash_du_lieu({'gia': 'Mẫu giả XS2B'}))
        self.assertEqual(len(bc['hash_ra']), 64)
        self.assertFalse(self.worker().chay_mot())

    def test_engine_cho_co_ly_do_va_bang_chung(self):
        self.engine.ham = lambda x: KetQuaXuLy('CHO', 'THIEU_CAN_CU', 'Chờ căn cứ giả.')
        key = self.tao()
        self.worker().chay_mot()
        viec = self.doc(key)
        self.assertEqual((viec['trang_thai'], viec['ma_loi']), ('CHO', 'THIEU_CAN_CU'))
        self.assertIsNone(viec['ket_qua_id'])
        self.assertEqual(self.ket_qua(key)[0][1]['ly_do'], 'Chờ căn cứ giả.')

    def test_engine_loi_sql_thu_lai_den_gioi_han(self):
        self.engine.ham = lambda x: KetQuaXuLy('LOI', 'GIA_LOI', 'Lỗi giả an toàn.')
        key = self.tao(toi_da=3)
        w = self.worker()
        for n in range(1, 4):
            self.assertTrue(w.chay_mot())
            viec = self.doc(key)
            self.assertEqual(viec['so_lan_thu'], n)
            self.assertEqual(viec['trang_thai'], 'LOI' if n == 3 else 'CHO')
            self.assertEqual(viec['ma_loi'], 'GIA_LOI')
            if n < 3:
                self.den_luot(key)
        self.assertFalse(w.chay_mot())
        self.assertEqual(self.engine.so_lan, 3)
        self.assertEqual(len(self.ket_qua(key)), 3)

    def test_hai_worker_cung_chay_khong_trung(self):
        key = self.tao()
        barrier = Barrier(2)
        entered, release = Event(), Event()

        def engine(x):
            entered.set()
            if not release.wait(10):
                raise RuntimeError('Test hết thời gian chờ')
            return KetQuaXuLy('XONG', 'DA_XONG', 'Mẫu giả.', x)
        self.engine.ham = engine

        def run(w):
            barrier.wait(5)
            return w.chay_mot()
        with ThreadPoolExecutor(max_workers=2) as pool:
            f1, f2 = [pool.submit(run, self.worker()) for _ in range(2)]
            try:
                self.assertTrue(entered.wait(5))
                done, _ = wait((f1, f2), timeout=5, return_when=FIRST_COMPLETED)
                self.assertEqual(len(done), 1)
                self.assertFalse(next(iter(done)).result())
            finally:
                release.set()
            self.assertEqual(sorted([f1.result(10), f2.result(10)]), [False, True])
        self.assertEqual(self.engine.so_lan, 1)
        self.assertEqual(len(self.ket_qua(key)), 1)

    def test_lease_het_ket_qua_cu_bi_tu_choi(self):
        key = self.tao()

        def run(x):
            self.het_lease(key)
            return KetQuaXuLy('XONG', 'DA_XONG', 'Mẫu giả.', x)
        self.engine.ham = run
        with self.assertLogs('kho_tri_thuc.ha_tang.chay_engine', level='WARNING'):
            self.worker().chay_mot()
        self.assertEqual(self.ket_qua(key), [])
        self.assertIsNone(self.doc(key)['ket_qua_id'])
        with self.tx() as c:
            self.assertEqual(c.execute("SELECT viec.phuc_hoi(%s,'M2')", (self.pn,)).fetchone()[0], 1)
        self.assertEqual(self.doc(key)['trang_thai'], 'CHO')

    def test_het_lease_sau_callback_rollback_bang_chung(self):
        key = self.tao()
        self.luu_hook = lambda v: self.het_lease(key)
        with self.assertLogs('kho_tri_thuc.ha_tang.chay_engine', level='WARNING'):
            self.worker().chay_mot()
        self.assertEqual(self.ket_qua(key), [])
        self.assertIsNone(self.doc(key)['ket_qua_id'])

    def test_cas_tu_choi_rollback_ca_ket_qua_va_cap_nhat_hang_viec(self):
        key = self.tao()
        original = hv.ket_thuc

        def tu_choi(*args, **kwargs):
            self.assertTrue(original(*args, **kwargs))
            return False
        with patch.object(hv, 'ket_thuc', side_effect=tu_choi):
            with self.assertLogs('kho_tri_thuc.ha_tang.chay_engine', level='WARNING'):
                self.worker().chay_mot()
        self.assertEqual(self.ket_qua(key), [])
        self.assertEqual(self.doc(key)['trang_thai'], 'DANG_CHAY')
        self.assertIsNone(self.doc(key)['ket_qua_id'])

    def test_worker_cu_khong_ghi_de_ket_qua_token_moi(self):
        key = self.tao()
        entered, release = Event(), Event()

        def run(x):
            entered.set()
            if not release.wait(10):
                raise RuntimeError('Test hết thời gian chờ')
            return KetQuaXuLy('XONG', 'DA_XONG', 'Kết quả cũ giả.', x)
        self.engine.ham = run
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertLogs('kho_tri_thuc.ha_tang.chay_engine', level='WARNING'):
                old = pool.submit(self.worker().chay_mot)
                try:
                    self.assertTrue(entered.wait(5))
                    self.het_lease(key)
                    self.assertFalse(self.worker().chay_mot())  # Phục hồi và chờ retry SQL.
                    self.den_luot(key)
                    self.engine.ham = lambda x: KetQuaXuLy('XONG', 'DA_XONG', 'Kết quả mới giả.', x)
                    self.assertTrue(self.worker().chay_mot())
                finally:
                    release.set()
                self.assertTrue(old.result(10))
        self.assertEqual(self.doc(key)['trang_thai'], 'XONG')
        self.assertEqual(self.doc(key)['so_lan_thu'], 2)
        rows = self.ket_qua(key)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1]['ly_do'], 'Kết quả mới giả.')

    def test_tac_dong_ngoai_het_lease_khong_tu_chay_lai(self):
        key = self.tao(ngoai=True)
        self.engine.ham = lambda x: (self.het_lease(key) or
                                     KetQuaXuLy('XONG', 'DA_XONG', 'Mẫu giả.', x))
        w = self.worker()
        with self.assertLogs('kho_tri_thuc.ha_tang.chay_engine', level='WARNING'):
            w.chay_mot()
        self.assertFalse(w.chay_mot())
        self.assertEqual(self.doc(key)['trang_thai'], 'CHUA_RO')
        self.assertEqual(self.engine.so_lan, 1)

    def test_dung_sau_nap_truoc_buoc_engine(self):
        key = self.tao()

        def dung(v):
            with self.tx() as c:
                self.assertTrue(hv.yeu_cau_dung(c, key, phap_nhan_id=self.pn))
        self.nap_hook = dung
        self.worker().chay_mot()
        self.assertEqual(self.doc(key)['trang_thai'], 'DA_DUNG')
        self.assertEqual(self.engine.so_lan, 0)
        self.assertEqual(self.ket_qua(key), [])

    def test_dung_trong_engine_khong_luu_o_buoc_ke(self):
        key = self.tao()

        def run(x):
            with self.tx() as c:
                hv.yeu_cau_dung(c, key, phap_nhan_id=self.pn)
            return KetQuaXuLy('XONG', 'DA_XONG', 'Mẫu giả.', x)
        self.engine.ham = run
        self.worker().chay_mot()
        self.assertEqual(self.doc(key)['trang_thai'], 'DA_DUNG')
        self.assertEqual(self.ket_qua(key), [])

    def test_module_tat_pn_a_khong_nhan_pn_b_van_chay(self):
        key_a, key_b = self.tao(), self.tao(pn=self.pn2)
        self.tat(self.pn)
        self.assertFalse(self.worker().chay_mot())
        self.assertTrue(self.worker(pn=self.pn2).chay_mot())
        self.assertEqual(self.doc(key_a)['trang_thai'], 'CHO')
        self.assertEqual(self.doc(key_b)['trang_thai'], 'XONG')

    def test_s4_tat_giua_chung_viec_dang_chay_van_hoan_tat(self):
        key = self.tao()
        self.engine.ham = lambda x: (self.tat(self.pn) or
                                     KetQuaXuLy('XONG', 'DA_XONG', 'Mẫu giả.', x))
        w = self.worker()
        self.assertTrue(w.chay_mot())
        self.assertEqual(self.doc(key)['trang_thai'], 'XONG')
        self.assertFalse(w.chay_mot())

    def test_ngoai_le_la_loi_co_ma_khong_lo_noi_dung(self):
        def run(x):
            raise RuntimeError('NOI_DUNG_NHAY_CAM_GIA')
        self.engine.ham = run
        for ngoai, tt in ((False, 'LOI'), (True, 'CHUA_RO')):
            key = self.tao(ngoai=ngoai)
            with self.assertLogs('kho_tri_thuc.ha_tang.chay_engine', level='ERROR') as log:
                self.worker().chay_mot()
            self.assertEqual(self.doc(key)['trang_thai'], tt)
            self.assertEqual(self.doc(key)['ma_loi'], 'WORKER_NGOAI_LE')
            self.assertNotIn('NOI_DUNG_NHAY_CAM_GIA', ''.join(log.output))
            self.assertEqual(self.ket_qua(key), [])

    def test_gia_han_trong_luc_engine_chay_ngoai_giao_dich(self):
        key = self.tao()
        renewed = Event()
        original = hv.gia_han

        def gia_han(*args, **kwargs):
            ok = original(*args, **kwargs)
            if ok:
                renewed.set()
            return ok

        def run(x):
            self.assertTrue(renewed.wait(5), 'Không gia hạn trong lúc engine chạy')
            # Một transaction khác vẫn nhận/đọc được, không bị giữ khóa dài.
            self.assertFalse(self.worker().chay_mot())
            return KetQuaXuLy('XONG', 'DA_XONG', 'Mẫu giả.', x)
        self.engine.ham = run
        with patch.object(hv, 'gia_han', side_effect=gia_han) as mock:
            self.worker(lease=3, nhip=0.1).chay_mot()
        self.assertGreaterEqual(mock.call_count, 1)
        self.assertEqual(self.doc(key)['trang_thai'], 'XONG')

    def test_loi_gia_han_khong_luu_ket_qua(self):
        key = self.tao()
        attempted = Event()

        def gia_han(*args, **kwargs):
            raise RuntimeError('Lỗi kết nối giả')

        # Đợi lúc worker đã đánh dấu mất lease, tránh chạy đua với catch của luồng gia hạn.
        from kho_tri_thuc.ha_tang.chay_engine import LOG
        original_log = LOG.error

        def bao_loi(*args, **kwargs):
            original_log(*args, **kwargs)
            attempted.set()

        def run(x):
            self.assertTrue(attempted.wait(5))
            return KetQuaXuLy('XONG', 'DA_XONG', 'Mẫu giả.', x)
        self.engine.ham = run
        with patch.object(hv, 'gia_han', side_effect=gia_han):
            with self.assertLogs('kho_tri_thuc.ha_tang.chay_engine', level='ERROR') as log:
                with patch.object(LOG, 'error', side_effect=bao_loi):
                    self.worker(lease=3, nhip=0.1).chay_mot()
        self.assertIn('WORKER_GIA_HAN_LOI', ''.join(log.output))
        self.assertEqual(self.ket_qua(key), [])
        self.assertIsNone(self.doc(key)['ket_qua_id'])

    def test_tao_viec_rollback_cung_nghiep_vu(self):
        key = None
        with self.assertRaisesRegex(RuntimeError, 'Rollback giả'):
            with self.tx() as c:
                key = hv.tao_viec(c, 'E-GIA', 1, uuid4().hex, self.ref,
                                  phap_nhan_id=self.pn, module='M2')
                raise RuntimeError('Rollback giả')
        with self.tx() as c:
            self.assertIsNone(c.execute('SELECT id FROM viec.hang_viec WHERE id=%s', (key,)).fetchone())


if __name__ == '__main__':
    unittest.main()
