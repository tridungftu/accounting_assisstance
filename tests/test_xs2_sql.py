"""XS-2a: PG tự tạo kho_test_*, chỉ dữ liệu giả, giữ CSDL sau kiểm.

Không mở server/đọc cấu hình thật/xóa tệp hoặc CSDL; chạy được với guard giữ tệp.
Fixture commit để hai kết nối độc lập tranh nhận được; mỗi ca có PN/ID riêng.
Chạy: python -X utf8 -m unittest tests.test_xs2_sql -v
PG chỉ chạy khi lead cấp KHO_PG_DSN_TEST (quyền tạo DB, migration và SET ROLE).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import sys
from threading import Barrier
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_hang_viec import HANG_VIEC_B_SQL, HANG_VIEC_SQL

try:
    import psycopg
except ImportError:
    psycopg = None

DSN = os.environ.get('KHO_PG_DSN_TEST')
SQL = '\n'.join(HANG_VIEC_SQL)
SIGNATURES = (
    'viec.tao(uuid,text,text,integer,text,uuid,boolean,integer,integer,integer)',
    'viec.nhan(uuid,text,uuid,integer)', 'viec.phuc_hoi(uuid,text)',
    'viec.gia_han(uuid,uuid,uuid,uuid,integer)', 'viec.tien_do(uuid,uuid,uuid,uuid,integer)',
    'viec.ket_thuc(uuid,uuid,uuid,uuid,text,uuid,text)',
    'viec.thu_lai(uuid,uuid,uuid,uuid,text)', 'viec.yeu_cau_dung(uuid,uuid)',
    'viec.trang_thai_lease(uuid,uuid,uuid,uuid)',
)
PRIVATE = ('viec._kiem_quyen(uuid,text)', 'viec._giu(uuid,uuid,uuid,uuid)', 'viec._nhat_ky()')
KHONG_GIU = {'con_giu': False, 'yeu_cau_dung': None, 'het_han_luc': None, 'trang_thai': None}


class HangViecTinh(unittest.TestCase):
    def test_migration_chi_noi_them_khong_ghim_migration_cuoi(self):
        source = Path(PM.__file__).read_text(encoding='utf-8')
        marker = '# XS-2a — CD-017:'
        self.assertEqual(source.count(marker), 1)
        old = {'__name__': PM.__name__, '__package__': PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, 'exec'), old)
        previous = old['PG_MIGRATIONS']
        self.assertEqual(PM.PG_MIGRATIONS[:len(previous)], previous)
        self.assertIs(PM.PG_MIGRATIONS[len(previous)], HANG_VIEC_SQL)
        self.assertEqual(sum(m is HANG_VIEC_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_migration_b_chi_noi_them_giu_nguyen_m0060(self):
        source = Path(PM.__file__).read_text(encoding='utf-8')
        marker = '# XS-2a2 — CD-017:'
        self.assertEqual(source.count(marker), 1)
        old = {'__name__': PM.__name__, '__package__': PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, 'exec'), old)
        previous = old['PG_MIGRATIONS']
        # Chỉ kiểm tiền tố: không ghim migration cuối (lát sau được nối thêm).
        self.assertEqual(PM.PG_MIGRATIONS[:len(previous) + 1], (*previous, HANG_VIEC_B_SQL))
        self.assertIs(old['M0060_HANG_VIEC'], HANG_VIEC_SQL)
        self.assertIs(PM.M0062_HANG_VIEC_B, HANG_VIEC_B_SQL)
        self.assertEqual(sum(m is HANG_VIEC_B_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_chi_mot_bang_chung_khong_sua_quyen_hay_hang_viec_cu(self):
        self.assertEqual(re.findall(r'CREATE TABLE ([\w.]+)', SQL), ['viec.hang_viec'])
        self.assertNotRegex(SQL, r'(?:ALTER|DROP) (?:TABLE|FUNCTION) (?:master|m4)\.')
        self.assertNotRegex(SQL, r'\b(?:DELETE|TRUNCATE|CREATE ROLE|COMMIT)\b')
        self.assertIn('INSERT INTO nhat_ky.su_kien', SQL)


@unittest.skipUnless(DSN and psycopg is not None,
                     'NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG')
class HangViecPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = 'kho_test_xs2_' + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0")
                          .format(sql.Identifier(cls.db)))
        cls.test_dsn = make_conninfo(DSN, dbname=cls.db)
        c = psycopg.connect(cls.test_dsn, autocommit=True)
        cls.addClassCleanup(c.close)
        postgres.migrate(c)
        with c.transaction():
            login = 'MO_PHONG_XS2_ADMIN_' + uuid.uuid4().hex
            actor = c.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro) "
                              "VALUES ('Admin giả XS2',%s,'XEM') RETURNING id", (login,)).fetchone()[0]
            c.execute("SELECT master.mtq_bootstrap_admin(%s,%s,'Admin giả XS2')", (actor, uuid.uuid4()))
            cls.admin_actor = actor, login

    def setUp(self):
        self.c = psycopg.connect(self.test_dsn, autocommit=True)
        self.addCleanup(self.c.close)
        with self.c.transaction():
            self.pn = self.them_pn()
            self.pn2 = self.them_pn()
            self.actor = self.them_nguoi()
            self.other = self.them_nguoi()
            for actor, pn, modules in ((self.actor, self.pn, ['M2', 'M4']),
                                       (self.actor, self.pn2, ['M2', 'M4']),
                                       (self.other, self.pn2, ['M2'])):
                self.c.execute('INSERT INTO master.phan_quyen '
                               '(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,%s)',
                               (actor[0], pn, modules))
        self.worker = uuid.uuid4()
        self.ref = uuid.uuid4()
        self.danh_tinh(self.c, self.actor)

    def them_pn(self):
        return self.c.execute("INSERT INTO master.phap_nhan (ma,ten) "
                              "VALUES (%s,'Pháp nhân giả XS2') RETURNING id",
                              ('XS2_' + uuid.uuid4().hex,)).fetchone()[0]

    def them_nguoi(self):
        login = 'MO_PHONG_XS2_' + uuid.uuid4().hex
        key = self.c.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro) "
                             "VALUES ('Người giả XS2',%s,'XEM') RETURNING id", (login,)).fetchone()[0]
        return key, login

    def danh_tinh(self, c, actor):
        c.execute('RESET ROLE')
        c.execute("SELECT set_config('ktt.nguoi_dung_id',%s,false), "
                  "set_config('ktt.nguoi_dung_dang_nhap',%s,false)", (str(actor[0]), actor[1]))
        c.execute('SET ROLE app_web')
        c.execute("SET statement_timeout = '5s'")

    def ket_noi(self):
        c = psycopg.connect(self.test_dsn, autocommit=True)
        self.addCleanup(c.close)
        self.danh_tinh(c, self.actor)
        return c

    def tao(self, key='gia', *, pn=None, module='M2', ngoai=False, toi_da=3,
            cho=1, giu=90, ref=None, version=1, c=None):
        return (c or self.c).execute('SELECT viec.tao(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                                     (pn or self.pn, module, 'E-GIA', version, key,
                                      ref or self.ref, ngoai, toi_da, cho, giu)).fetchone()[0]

    def nhan(self, *, c=None, pn=None, module='M2', worker=None, giay=120):
        return [r[0] for r in (c or self.c).execute(
            'SELECT to_jsonb(v) FROM viec.nhan(%s,%s,%s,%s) v',
            (pn or self.pn, module, worker or self.worker, giay)).fetchall()]

    def cap_nhat(self, v, ham='ket_thuc', *args, pn=None, worker=None, token=None, c=None):
        params = (pn or self.pn, v['id'], worker or v['lease_boi'],
                  token or v['lease_token'], *args)
        # Tên hàm chỉ do test cung cấp, không lấy đầu vào người dùng.
        return (c or self.c).execute('SELECT viec.' + ham + '(' + ','.join(['%s'] * len(params)) + ')',
                                     params).fetchone()[0]

    def doc(self, key):
        row = self.c.execute('SELECT to_jsonb(v) FROM viec.hang_viec v WHERE id=%s', (key,)).fetchone()
        return None if row is None else row[0]

    def owner_sql(self, sql, args=()):
        self.c.execute('RESET ROLE')
        try:
            return self.c.execute(sql, args).fetchall()
        finally:
            self.c.execute('SET ROLE app_web')

    def het_lease(self, key):
        self.owner_sql("UPDATE viec.hang_viec SET lease_den=clock_timestamp()-interval '1 second' "
                       'WHERE id=%s RETURNING id', (key,))

    def den_luot(self, key):
        self.owner_sql("UPDATE viec.hang_viec SET thu_lai_sau=clock_timestamp()-interval '1 second' "
                       'WHERE id=%s RETURNING id', (key,))

    def phuc_hoi(self, pn=None):
        return self.c.execute("SELECT viec.phuc_hoi(%s,'M2')", (pn or self.pn,)).fetchone()[0]

    def loi(self, code, fn):
        with self.assertRaises(psycopg.Error) as cm:
            with self.c.transaction():
                fn()
        self.assertIn(code, str(cm.exception))

    def test_tao_rollback_khong_con_viec_va_nhat_ky(self):
        with self.assertRaisesRegex(RuntimeError, 'rollback giả'):
            with self.c.transaction():
                key = self.tao()
                self.assertIsNotNone(self.doc(key))
                raise RuntimeError('rollback giả')
        self.assertIsNone(self.doc(key))
        count = self.owner_sql('SELECT count(*) FROM nhat_ky.su_kien '
                               "WHERE doi_tuong_bang='viec.hang_viec' AND doi_tuong_id=%s", (key,))
        self.assertEqual(count[0][0], 0)

    def test_dedupe_cung_khoa_mot_viec_khac_hop_dong_tu_choi(self):
        key = self.tao()
        self.assertEqual(self.tao(), key)
        for kwargs in ({'ref': uuid.uuid4()}, {'version': 2}, {'ngoai': True},
                       {'toi_da': 4}, {'cho': 3}, {'giu': None}):
            self.loi('VIEC_DEDUPE_XUNG_DOT', lambda: self.tao(**kwargs))
        self.assertNotEqual(self.tao(pn=self.pn2), key)
        self.assertNotEqual(self.tao(module='M4'), key)
        v = self.nhan()[0]
        self.assertTrue(self.cap_nhat(v, 'ket_thuc', 'XONG'))
        self.assertEqual(self.tao(), key)
        self.assertEqual(self.nhan(), [])

    def test_hai_worker_dong_thoi_chi_mot_nguoi_nhan(self):
        key = self.tao()
        c1, c2 = self.ket_noi(), self.ket_noi()
        barrier = Barrier(2)

        def run(c):
            barrier.wait(timeout=5)
            return self.nhan(c=c, worker=uuid.uuid4())

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1, f2 = pool.submit(run, c1), pool.submit(run, c2)
            received = f1.result(timeout=10) + f2.result(timeout=10)
        self.assertEqual([v['id'] for v in received], [str(key)])
        self.assertEqual(self.doc(key)['so_lan_thu'], 1)

    def test_skip_locked_khong_cho_transaction_worker_khac(self):
        key = self.tao()
        c1, c2 = self.ket_noi(), self.ket_noi()
        with c1.transaction():
            self.assertEqual(self.nhan(c=c1)[0]['id'], str(key))
            self.assertEqual(self.nhan(c=c2, worker=uuid.uuid4()), [])

    def test_lease_het_worker_cu_khong_gia_han_tien_do_ket_thuc_thu_lai(self):
        key = self.tao()
        old = self.nhan()[0]
        self.het_lease(key)
        for ham, args in (('gia_han', (120,)), ('tien_do', (50,)),
                          ('ket_thuc', ('XONG',)), ('thu_lai', ('LOI_GIA',))):
            self.assertFalse(self.cap_nhat(old, ham, *args))
        self.assertEqual(self.phuc_hoi(), 1)
        self.assertEqual(self.doc(key)['trang_thai'], 'CHO')
        self.assertEqual(self.nhan(worker=uuid.uuid4()), [])  # Có khoảng chờ.
        self.den_luot(key)
        new = self.nhan(worker=uuid.uuid4())[0]
        self.assertNotEqual(old['lease_token'], new['lease_token'])
        self.assertFalse(self.cap_nhat(old, 'ket_thuc', 'XONG'))
        self.assertTrue(self.cap_nhat(new, 'ket_thuc', 'XONG', uuid.uuid4()))

    def test_cung_worker_id_luot_moi_van_tu_choi_token_cu(self):
        key = self.tao()
        old = self.nhan()[0]
        self.het_lease(key)
        self.phuc_hoi()
        self.den_luot(key)
        new = self.nhan()[0]
        self.assertFalse(self.cap_nhat(old, 'ket_thuc', 'XONG'))
        self.assertTrue(self.cap_nhat(new, 'ket_thuc', 'XONG'))

    def test_lease_het_trong_cung_transaction_van_tu_choi(self):
        self.tao()
        with self.c.transaction():
            v = self.nhan(giay=1)[0]
            self.c.execute('SELECT pg_sleep(1.1)')
            self.assertFalse(self.cap_nhat(v, 'gia_han', 120))
            self.assertFalse(self.cap_nhat(v, 'ket_thuc', 'XONG'))

    def test_nhan_tu_phuc_hoi_lease_nhung_giu_khoang_cho(self):
        key = self.tao()
        self.nhan()
        self.het_lease(key)
        self.assertEqual(self.nhan(), [])
        self.assertEqual(self.doc(key)['trang_thai'], 'CHO')
        self.den_luot(key)
        self.assertEqual(self.nhan()[0]['so_lan_thu'], 2)

    def test_tac_dong_ngoai_het_lease_chua_ro_khong_tu_chay_lai(self):
        key = self.tao(ngoai=True)
        old = self.nhan()[0]
        self.het_lease(key)
        self.assertEqual(self.phuc_hoi(), 1)
        v = self.doc(key)
        self.assertEqual(v['trang_thai'], 'CHUA_RO')
        self.assertIsNone(v['ket_thuc_luc'])
        self.den_luot(key)
        self.assertEqual(self.nhan(), [])
        self.assertFalse(self.cap_nhat(old, 'thu_lai', 'LOI_GIA'))
        self.assertEqual(self.phuc_hoi(), 0)

    def test_dung_hop_tac_worker_tu_xac_nhan(self):
        key = self.tao()
        v = self.nhan()[0]
        self.assertTrue(self.c.execute('SELECT viec.yeu_cau_dung(%s,%s)', (self.pn, key)).fetchone()[0])
        self.assertTrue(self.doc(key)['yeu_cau_dung'])
        self.assertEqual(self.doc(key)['trang_thai'], 'DANG_CHAY')
        self.assertTrue(self.cap_nhat(v, 'gia_han', 180))
        self.assertTrue(self.cap_nhat(v, 'ket_thuc', 'DA_DUNG'))
        self.assertEqual(self.doc(key)['trang_thai'], 'DA_DUNG')
        self.assertIsNotNone(self.doc(key)['ket_thuc_luc'])
        self.assertEqual(self.nhan(), [])

    def test_trang_thai_lease_nguoi_giu_thay_yeu_cau_dung_tu_ket_noi_khac(self):
        key = self.tao()
        v = self.nhan()[0]
        before = self.cap_nhat(v, 'trang_thai_lease')
        self.assertEqual(before['con_giu'], True)
        self.assertEqual(before['yeu_cau_dung'], False)
        self.assertEqual(before['trang_thai'], 'DANG_CHAY')
        self.assertEqual(before['het_han_luc'], v['lease_den'])
        c = self.ket_noi()
        self.assertTrue(c.execute('SELECT viec.yeu_cau_dung(%s,%s)', (self.pn, key)).fetchone()[0])
        self.assertEqual(self.cap_nhat(v, 'trang_thai_lease'), {**before, 'yeu_cau_dung': True})

    def test_trang_thai_lease_sai_token_worker_null_khong_lo(self):
        key = self.tao()
        v = self.nhan()[0]
        self.c.execute('SELECT viec.yeu_cau_dung(%s,%s)', (self.pn, key))
        for worker, token in ((v['lease_boi'], uuid.uuid4()),
                              (uuid.uuid4(), v['lease_token']),
                              (None, v['lease_token']), (v['lease_boi'], None)):
            with self.subTest(worker=worker, token=token):
                result = self.c.execute('SELECT viec.trang_thai_lease(%s,%s,%s,%s)',
                                        (self.pn, key, worker, token)).fetchone()[0]
                self.assertEqual(result, KHONG_GIU)

    def test_trang_thai_lease_het_han_khong_lo_du_chua_phuc_hoi(self):
        key = self.tao()
        v = self.nhan()[0]
        self.c.execute('SELECT viec.yeu_cau_dung(%s,%s)', (self.pn, key))
        self.het_lease(key)
        self.assertEqual(self.cap_nhat(v, 'trang_thai_lease'), KHONG_GIU)

    def test_trang_thai_lease_het_trong_cung_transaction(self):
        self.tao()
        with self.c.transaction():
            v = self.nhan(giay=1)[0]
            self.assertTrue(self.cap_nhat(v, 'trang_thai_lease')['con_giu'])
            self.c.execute('SELECT pg_sleep(1.1)')
            self.assertEqual(self.cap_nhat(v, 'trang_thai_lease'), KHONG_GIU)

    def test_trang_thai_lease_chua_nhan_da_dong_va_id_khong_co_khong_lo(self):
        key = self.tao()
        for key_doc in (key, uuid.uuid4(), None):
            with self.subTest(key=key_doc):
                result = self.c.execute('SELECT viec.trang_thai_lease(%s,%s,%s,%s)',
                                        (self.pn, key_doc, self.worker, uuid.uuid4())).fetchone()[0]
                self.assertEqual(result, KHONG_GIU)
        v = self.nhan()[0]
        self.assertTrue(self.cap_nhat(v, 'ket_thuc', 'XONG'))
        self.assertEqual(self.cap_nhat(v, 'trang_thai_lease'), KHONG_GIU)

    def test_trang_thai_lease_sai_pn_bi_chan_nhu_m0060(self):
        self.tao()
        v = self.nhan()[0]
        self.assertEqual(self.cap_nhat(v, 'trang_thai_lease', pn=self.pn2), KHONG_GIU)
        self.danh_tinh(self.c, self.other)
        self.loi('VIEC_PHAM_VI', lambda: self.cap_nhat(v, 'trang_thai_lease'))

    def test_trang_thai_lease_khac_danh_tinh_va_thu_hoi_module(self):
        self.tao(pn=self.pn2)
        v = self.nhan(pn=self.pn2)[0]
        self.danh_tinh(self.c, self.other)
        self.assertEqual(self.cap_nhat(v, 'trang_thai_lease', pn=self.pn2), KHONG_GIU)
        self.danh_tinh(self.c, self.actor)
        self.owner_sql("UPDATE master.phan_quyen SET module=ARRAY['M4']::text[] "
                       'WHERE nguoi_dung_id=%s AND phap_nhan_id=%s RETURNING id',
                       (self.actor[0], self.pn2))
        self.loi('VIEC_PHAM_VI', lambda: self.cap_nhat(v, 'trang_thai_lease', pn=self.pn2))

    def test_trang_thai_lease_stable_goi_duoc_read_only(self):
        key = self.tao()
        v = self.nhan()[0]
        self.c.execute('SELECT viec.yeu_cau_dung(%s,%s)', (self.pn, key))
        volatility = self.c.execute("SELECT provolatile FROM pg_proc "
                                    "WHERE oid='viec.trang_thai_lease(uuid,uuid,uuid,uuid)'"
                                    '::regprocedure').fetchone()[0]
        self.assertEqual(volatility, 's')
        before = self.doc(key)
        with self.c.transaction():
            self.c.execute('SET TRANSACTION READ ONLY')
            self.assertEqual(self.c.execute('SHOW transaction_read_only').fetchone()[0], 'on')
            self.assertEqual(self.cap_nhat(v, 'trang_thai_lease'), {
                'con_giu': True, 'yeu_cau_dung': True,
                'het_han_luc': v['lease_den'], 'trang_thai': 'DANG_CHAY'})
            self.assertEqual(self.cap_nhat(v, 'trang_thai_lease', token=uuid.uuid4()), KHONG_GIU)
        self.assertEqual(self.doc(key), before)

    def test_trang_thai_lease_khong_cho_khoa_dong_worker_khac(self):
        self.tao()
        v = self.nhan()[0]
        c = self.ket_noi()
        with c.transaction():
            self.assertTrue(self.cap_nhat(v, 'gia_han', 180, c=c))
            # Đọc snapshot đã commit dù kết nối kia đang giữ khóa UPDATE.
            self.assertTrue(self.cap_nhat(v, 'trang_thai_lease')['con_giu'])

    def test_dung_viec_cho_va_dung_khong_bien_unknown_thanh_an_toan(self):
        key = self.tao()
        self.assertTrue(self.c.execute('SELECT viec.yeu_cau_dung(%s,%s)', (self.pn, key)).fetchone()[0])
        self.assertEqual(self.doc(key)['trang_thai'], 'DA_DUNG')
        self.assertEqual(self.nhan(), [])
        external = self.tao('ngoai', ngoai=True)
        self.nhan()
        self.c.execute('SELECT viec.yeu_cau_dung(%s,%s)', (self.pn, external))
        self.het_lease(external)
        self.phuc_hoi()
        self.assertEqual(self.doc(external)['trang_thai'], 'CHUA_RO')

    def test_thu_lai_co_lich_den_gioi_han_loi(self):
        key = self.tao(toi_da=2)
        first = self.nhan()[0]
        self.assertTrue(self.cap_nhat(first, 'thu_lai', 'THU_LAI_GIA'))
        self.assertEqual(self.doc(key)['trang_thai'], 'CHO')
        self.assertIsNone(self.doc(key)['ket_thuc_luc'])
        self.assertEqual(self.nhan(), [])
        self.den_luot(key)
        last = self.nhan()[0]
        self.assertTrue(self.cap_nhat(last, 'thu_lai', 'THU_LAI_GIA'))
        self.assertEqual(self.doc(key)['trang_thai'], 'LOI')
        self.assertEqual(self.doc(key)['so_lan_thu'], 2)
        self.assertIsNotNone(self.doc(key)['ket_thuc_luc'])
        self.den_luot(key)
        self.assertEqual(self.nhan(), [])

    def test_het_lease_o_lan_cuoi_khong_thu_vuot_gioi_han(self):
        key = self.tao(toi_da=1)
        self.nhan()
        self.het_lease(key)
        self.phuc_hoi()
        self.assertEqual(self.doc(key)['trang_thai'], 'LOI')
        self.assertIsNotNone(self.doc(key)['ket_thuc_luc'])

    def test_module_tat_pn_a_chan_nhan_pn_b_van_nhan(self):
        key = self.tao()
        key2 = self.tao(pn=self.pn2)
        self.danh_tinh(self.c, self.admin_actor)
        self.c.execute("SELECT master.module_doi_che_do('M2',%s,'TAT','Giả XS2',0)", (self.pn,))
        self.danh_tinh(self.c, self.actor)
        self.assertEqual(self.nhan(), [])
        self.assertEqual(self.doc(key)['trang_thai'], 'CHO')
        self.assertEqual(self.nhan(pn=self.pn2)[0]['id'], str(key2))
        self.loi('VIEC_MODULE_TAT', lambda: self.tao('moi'))

    def test_module_thu_chi_nguoi_duoc_thu_nhan(self):
        self.tao()
        self.danh_tinh(self.c, self.admin_actor)
        self.c.execute("SELECT master.module_doi_che_do('M2',%s,'THU','Giả XS2',0)", (self.pn,))
        self.danh_tinh(self.c, self.actor)
        self.assertEqual(self.nhan(), [])
        self.danh_tinh(self.c, self.admin_actor)
        self.c.execute("SELECT master.module_cap_nguoi_thu('M2',%s,%s,'Giả XS2')", (self.pn, self.actor[0]))
        self.danh_tinh(self.c, self.actor)
        self.assertEqual(len(self.nhan()), 1)

    def test_tat_module_khong_ngan_worker_dang_chay_ket_thuc(self):
        self.tao()
        v = self.nhan()[0]
        self.danh_tinh(self.c, self.admin_actor)
        self.c.execute("SELECT master.module_doi_che_do('M2',%s,'TAT','Giả XS2',0)", (self.pn,))
        self.danh_tinh(self.c, self.actor)
        self.assertTrue(self.cap_nhat(v, 'ket_thuc', 'XONG'))

    def test_sai_pn_khong_thay_khong_sua_va_thieu_module_bi_chan(self):
        key = self.tao()
        v = self.nhan()[0]
        self.danh_tinh(self.c, self.other)
        self.assertIsNone(self.doc(key))
        for fn in (self.nhan, self.tao, self.phuc_hoi,
                   lambda: self.cap_nhat(v, 'ket_thuc', 'XONG'),
                   lambda: self.c.execute('SELECT viec.yeu_cau_dung(%s,%s)', (self.pn, key))):
            self.loi('VIEC_PHAM_VI', fn)
        self.assertFalse(self.cap_nhat(v, 'ket_thuc', 'XONG', pn=self.pn2))
        self.danh_tinh(self.c, self.actor)
        self.loi('VIEC_PHAM_VI', lambda: self.nhan(module='M9'))
        self.loi('VIEC_PHAM_VI', lambda: self.tao(module='M9'))

    def test_lease_khac_worker_khac_danh_tinh_va_quyen_thu_hoi(self):
        key = self.tao(pn=self.pn2)
        v = self.nhan(pn=self.pn2)[0]
        self.assertFalse(self.cap_nhat(v, 'ket_thuc', 'XONG', pn=self.pn2, worker=uuid.uuid4()))
        self.assertFalse(self.cap_nhat(v, 'ket_thuc', 'XONG', pn=self.pn2, token=uuid.uuid4()))
        self.danh_tinh(self.c, self.other)
        self.assertFalse(self.cap_nhat(v, 'ket_thuc', 'XONG', pn=self.pn2))
        self.danh_tinh(self.c, self.actor)
        self.owner_sql("UPDATE master.phan_quyen SET module=ARRAY['M4']::text[] "
                       'WHERE nguoi_dung_id=%s AND phap_nhan_id=%s RETURNING id',
                       (self.actor[0], self.pn2))
        self.assertIsNone(self.doc(key))
        self.loi('VIEC_PHAM_VI', lambda: self.cap_nhat(v, 'ket_thuc', 'XONG', pn=self.pn2))

    def test_gia_danh_tinh_khong_thay_khong_nhan(self):
        key = self.tao()
        self.c.execute("SELECT set_config('ktt.nguoi_dung_dang_nhap','KHONG_KHOP',false)")
        self.assertIsNone(self.doc(key))
        self.loi('VIEC_PHAM_VI', self.nhan)
        self.loi('VIEC_PHAM_VI', self.tao)

    def test_tien_do_gia_han_ket_qua_va_nhat_ky_chuyen_trang_thai(self):
        key = self.tao()
        v = self.nhan()[0]
        self.assertTrue(self.cap_nhat(v, 'tien_do', 40))
        self.assertEqual(self.doc(key)['tien_do'], 40)
        self.loi('VIEC_TIEN_DO', lambda: self.cap_nhat(v, 'tien_do', 39))
        self.assertTrue(self.cap_nhat(v, 'gia_han', 180))
        self.assertGreater(self.doc(key)['lease_den'], v['lease_den'])
        result = uuid.uuid4()
        self.assertTrue(self.cap_nhat(v, 'ket_thuc', 'XONG', result))
        after = self.doc(key)
        self.assertEqual(after['ket_qua_id'], str(result))
        self.assertEqual(after['tien_do'], 100)
        self.assertIsNone(after['lease_token'])
        self.assertEqual(after['giu_ngay'], 90)
        self.assertIsNotNone(after['ket_thuc_luc'])
        audit = self.owner_sql('SELECT hanh_dong FROM nhat_ky.su_kien '
                               "WHERE doi_tuong_bang='viec.hang_viec' AND doi_tuong_id=%s ORDER BY id", (key,))
        self.assertEqual([r[0] for r in audit], ['VIEC_CHO', 'VIEC_DANG_CHAY', 'VIEC_XONG'])

    def test_dau_vao_gioi_han_va_ma_loi_khong_nhan_noi_dung_tu_do(self):
        for kwargs in ({'toi_da': 0}, {'toi_da': 101}, {'cho': 0}, {'cho': 86401},
                       {'giu': 0}, {'giu': 36501}, {'version': 0}, {'key': ' '}):
            with self.assertRaises(psycopg.Error):
                with self.c.transaction():
                    self.tao(**kwargs)
        self.tao(giu=None)
        for giay in (None, 0, 3601):
            self.loi('VIEC_LEASE_DAU_VAO', lambda: self.nhan(giay=giay))
        v = self.nhan()[0]
        self.loi('VIEC_KET_THUC_DAU_VAO', lambda: self.cap_nhat(v, 'ket_thuc', 'DA_DUNG'))
        self.loi('VIEC_KET_THUC_DAU_VAO', lambda: self.cap_nhat(v, 'thu_lai', None))
        with self.assertRaises(psycopg.errors.CheckViolation):
            with self.c.transaction():
                self.cap_nhat(v, 'thu_lai', 'Nội dung lỗi chứng từ giả')
        self.assertEqual(self.doc(v['id'])['trang_thai'], 'DANG_CHAY')

    def test_acl_sd_search_path_rls_va_public(self):
        self.tao()
        self.assertTrue(self.c.execute("SELECT relrowsecurity FROM pg_class "
                                       "WHERE oid='viec.hang_viec'::regclass").fetchone()[0])
        for privilege in ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER'):
            self.assertFalse(self.c.execute("SELECT has_table_privilege('app_web','viec.hang_viec',%s)",
                                            (privilege,)).fetchone()[0])
        public_table = self.c.execute("SELECT count(*) FROM pg_class t, "
                                      "LATERAL aclexplode(coalesce(t.relacl,acldefault('r',t.relowner))) a "
                                      "WHERE t.oid='viec.hang_viec'::regclass AND a.grantee=0").fetchone()[0]
        self.assertEqual(public_table, 0)
        for signature in SIGNATURES + PRIVATE:
            definer, config = self.c.execute('SELECT prosecdef,proconfig FROM pg_proc '
                                             'WHERE oid=%s::regprocedure', (signature,)).fetchone()
            self.assertTrue(definer)
            self.assertIn('search_path=pg_catalog, viec, master, nhat_ky, pg_temp', config)
            self.assertEqual(self.c.execute("SELECT has_function_privilege('app_web',%s,'EXECUTE')",
                                            (signature,)).fetchone()[0], signature in SIGNATURES)
            public = self.c.execute("SELECT count(*) FROM pg_proc p, "
                                    "LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a "
                                    "WHERE p.oid=%s::regprocedure AND a.grantee=0 "
                                    "AND a.privilege_type='EXECUTE'", (signature,)).fetchone()[0]
            self.assertEqual(public, 0)
        for role, in self.c.execute("SELECT rolname FROM pg_roles "
                                    "WHERE rolname IN ('app_ke_toan','app_doc','app_cong_ai')"):
            self.assertFalse(self.c.execute("SELECT has_schema_privilege(%s,'viec','USAGE')", (role,)).fetchone()[0])
            for signature in SIGNATURES:
                self.assertFalse(self.c.execute("SELECT has_function_privilege(%s,%s,'EXECUTE')",
                                                (role, signature)).fetchone()[0])
        for statement in ('INSERT INTO viec.hang_viec DEFAULT VALUES',
                          "UPDATE viec.hang_viec SET trang_thai='XONG'",
                          'SELECT viec._kiem_quyen(NULL,NULL)',
                          'SELECT viec._giu(NULL,NULL,NULL,NULL)'):
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with self.c.transaction():
                    self.c.execute(statement)


if __name__ == '__main__':
    unittest.main()
