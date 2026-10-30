"""G2-16: mock + PG opt-in; runtime LOGIN thật, không DROP/dịch vụ/socket.

Admin chỉ provisioning/fixture và ép lease hết; nghiệp vụ dùng Core login.
PG giữ lại kho_test_* để lead đối soát. Không đọc file cấu hình kết nối.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import secrets
import sys
from threading import Barrier
import traceback
import unittest
from unittest.mock import MagicMock
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import doi_cau_truc as dc, phien, so_cong as sc

try:
    from . import test_g2_05 as g205
except ImportError:
    import test_g2_05 as g205

psycopg = g205.psycopg
if psycopg is not None:
    from psycopg import sql

SQL_PATH = dc.THU_MUC_SQL / '016_so_cong.sql'
SQL = SQL_PATH.read_text(encoding='utf-8')
BANG = ('engine_ho_so_chay', 'so_cong', 'module_phien_chay', 'engine_phien_chay', 'so_do_phien_chay')
MO_KHOA = 'CORE:CONG:MO_KHOA'


class SoCongThuanTest(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.conn.info.transaction_status = 2
        self.id, self.instance, self.may = (uuid4() for _ in range(3))
        self.now = datetime.now(timezone.utc)
        self.conn.execute.return_value.fetchone.return_value = ({'id': str(self.id)},)

    def test_cap_bind_co_dinh_khong_tu_quan_ly_transaction(self):
        sc.cap(self.conn, self.may, 19016, module='demo')
        cau, ts = self.conn.execute.call_args.args
        self.assertEqual(cau, 'SELECT loi.so_cong_cap(%s,%s,%s,%s,%s) AS r')
        self.assertEqual(ts, (self.may, '127.0.0.1', 19016, 'demo', None))
        for ten in ('connect', 'commit', 'rollback', 'transaction'):
            getattr(self.conn, ten).assert_not_called()

    def test_bat_buoc_transaction_caller_cho_moi_cua(self):
        for tt in (0, 1, 3, 4):
            self.conn.info.transaction_status = tt
            for goi in (lambda: sc.cap(self.conn, self.may, 19016, module='demo'),
                        lambda: sc.doc(self.conn, self.id),
                        lambda: sc.gia_han(self.conn, self.id, self.instance, 1),
                        lambda: sc.tra(self.conn, self.id, self.instance, 1),
                        lambda: sc.het_hieu_luc(self.conn, self.id, 1)):
                with self.subTest(tt=tt), self.assertRaises(ValueError):
                    goi()
        self.conn.execute.assert_not_called()

    def test_dung_mot_chu_va_loopback(self):
        for ctx in ({}, {'module': 'demo', 'engine_ho_so_id': uuid4()},
                    {'module': 'demo', 'dia_chi_nghe': '0.0.0.0'}, {'module': ''}):
            with self.subTest(ctx=ctx), self.assertRaises(ValueError):
                sc.cap(self.conn, self.may, 19016, **ctx)
        self.conn.execute.assert_not_called()
        ho_so = uuid4()
        sc.cap(self.conn, self.may, 19016, engine_ho_so_id=ho_so, dia_chi_nghe='::1')
        self.assertEqual(self.conn.execute.call_args.args[1][-2:], (None, ho_so))

    def test_tu_choi_cong_sai(self):
        for v in (True, 0, 1023, 65536, '19016'):
            with self.subTest(v=v), self.assertRaises(ValueError):
                sc.cap(self.conn, self.may, v, module='demo')
        self.conn.execute.assert_not_called()

    def test_nhan_truyen_day_du_danh_tinh_va_doi_chieu(self):
        bang_chung = uuid4()
        sc.nhan(self.conn, self.id, self.instance, 0, pid=123,
                dinh_danh_lan_tao='DEMO-CREATE-TIME', phien_ban='1',
                nhan_yeu_cau_luc=self.now, bat_dau_luc=self.now, doi_chieu_id=bang_chung)
        ts = self.conn.execute.call_args.args[1]
        self.assertEqual(ts, (self.id, self.instance, 0, 120, 123, 'DEMO-CREATE-TIME', '1', self.now, self.now, bang_chung))

    def test_nhan_tu_choi_danh_tinh_thieu_va_gio_naive(self):
        p = dict(pid=1, dinh_danh_lan_tao='DEMO', phien_ban='1', nhan_yeu_cau_luc=self.now, bat_dau_luc=self.now)
        for doi in ({'pid': True}, {'pid': 0}, {'dinh_danh_lan_tao': ' '},
                    {'phien_ban': ''}, {'nhan_yeu_cau_luc': datetime.now()}, {'lease_giay': 3601},
                    {'bat_dau_luc': self.now-timedelta(seconds=1)}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                sc.nhan(self.conn, self.id, self.instance, 0, **{**p, **doi})
        self.conn.execute.assert_not_called()

    def test_cua_lease_khong_cho_the_he_zero(self):
        for v in (True, 0, -1, 2**63):
            with self.subTest(v=v), self.assertRaises(ValueError):
                sc.gia_han(self.conn, self.id, self.instance, v)
        self.conn.execute.assert_not_called()

    def test_san_sang_va_tra_ghi_loi_bind_instance_the_he(self):
        sc.san_sang(self.conn, self.id, self.instance, 3, bang_chung_id=uuid4())
        self.assertEqual(self.conn.execute.call_args.args[1][:3], (self.id, self.instance, 3))
        sc.tra(self.conn, self.id, self.instance, 3)
        self.assertEqual(self.conn.execute.call_args.args[1], (self.id, self.instance, 3))
        sc.loi_khoi_dong(self.conn, self.id, self.instance, 3, ma_loi='CONG_BI_CHIEM')
        self.assertEqual(self.conn.execute.call_args.args[1][-1], 'CONG_BI_CHIEM')

    def test_ma_loi_khong_nhan_noi_dung_tu_do(self):
        for v in ('password=CANARY', 'sai', '', None):
            with self.subTest(v=v), self.assertRaises(ValueError):
                sc.loi_khoi_dong(self.conn, self.id, self.instance, 1, ma_loi=v)
        self.conn.execute.assert_not_called()

    def test_mo_khoa_ma_bi_mat_bind_khong_log(self):
        sc.mo_khoa(self.conn, self.id, 3, ma=phien.MaBiMat('CANARY'), phap_nhan_id=self.may, request_id=uuid4())
        cau, ts = self.conn.execute.call_args.args
        self.assertNotIn('CANARY', cau)
        self.assertEqual(ts[:4], (self.id, 3, 'CANARY', self.may))

    def test_ho_so_chi_tham_chieu_va_gioi_han(self):
        sc.tao_ho_so(self.conn, engine_id=self.id, may_chu_id=self.may,
                    executable='DEMO/engine.exe', doi_so=['--demo'], tham_chieu_bi_mat='ket:demo')
        p = json.loads(self.conn.execute.call_args.args[1][0])
        self.assertEqual(p['ranh_giay'], 300)
        self.assertEqual(p['tham_chieu_bi_mat'], 'ket:demo')
        with self.assertRaises(ValueError):
            sc.tao_ho_so(self.conn, engine_id=self.id, may_chu_id=self.may,
                        executable='DEMO', doi_so=[{}])

    def test_so_do_thieu_la_null_khong_tu_tinh_zero(self):
        sc.ghi_so_do(self.conn, self.id, self.instance, 1, cua_so_tu=self.now, cua_so_den=self.now)
        p = json.loads(self.conn.execute.call_args.args[1][-1])
        self.assertIsNone(p['cpu_ms'])
        self.assertIsNone(p['ram_dinh_byte'])
        self.assertIsNone(p['chay_viec_ms'])

    def test_so_do_am_nan_inf_bool_ram_va_cua_so_dao_bi_chan(self):
        for doi in ({'cpu_ms': -1}, {'cpu_ms': float('nan')}, {'chay_viec_ms': float('inf')},
                    {'ranh_ms': True}, {'ram_dinh_byte': -1}, {'ram_dinh_byte': 10, 'ram_trung_binh_byte': 11},
                    {'cua_so_den': self.now-timedelta(seconds=1)}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                sc.ghi_so_do(self.conn, self.id, self.instance, 1,
                    **{**dict(cua_so_tu=self.now, cua_so_den=self.now), **doi})
        self.conn.execute.assert_not_called()

    def test_dict_row(self):
        self.conn.execute.return_value.fetchone.return_value = {'r': {'the_he': 1}}
        self.assertEqual(sc.doc(self.conn, self.id), {'the_he': 1})

    def test_driver_loi_khong_ro_token_hoac_dsn(self):
        for ma in ('CONG_CAS', 'CANARY_PASSWORD'):
            exc = RuntimeError('CANARY_DSN_TOKEN')
            exc.diag = MagicMock(message_primary=ma)
            self.conn.execute.side_effect = exc
            with self.assertRaises(sc.LoiSoCong) as bat:
                sc.mo_khoa(self.conn, self.id, 3, ma=phien.MaBiMat('CANARY_TOKEN'),
                           phap_nhan_id=self.may, request_id=uuid4())
            self.assertEqual(bat.exception.ma, ma if ma == 'CONG_CAS' else 'CONG_THAT_BAI')
            self.assertIsNone(bat.exception.__context__)
            self.assertNotIn('CANARY', ''.join(traceback.format_exception(bat.exception)))

    def test_sql_quote_bien_gioi_va_schema(self):
        moc = re.findall(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', SQL)
        self.assertEqual((moc[0], moc[-1]), ('$$', '$$'))
        self.assertEqual(len(moc) % 2, 0)
        self.assertTrue(all(a == b for a, b in zip(moc[1:-1:2], moc[2:-1:2])))
        self.assertNotRegex(SQL, r'(?i)\bDROP\s+(?:TABLE|FUNCTION|DATABASE|ROLE)')
        self.assertNotRegex(SQL, r'(?i)(?:FROM|JOIN|REFERENCES)\s+(?:mod_|master\.)')
        self.assertNotRegex(SQL, r'(?i)CREATE\s+ROLE')
        self.assertFalse(SQL_PATH.read_bytes().startswith(b'\xef\xbb\xbf'))
        for bang in BANG:
            self.assertIn('CREATE TABLE IF NOT EXISTS loi.' + bang, SQL)


@unittest.skipUnless(psycopg is not None and g205.ADMIN_DSN,
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class SoCongPostgresTest(unittest.TestCase):
    _ghi = g205.DangKyPostgresTest._ghi

    @classmethod
    def setUpClass(cls):
        g205.DangKyPostgresTest.setUpClass.__func__(cls)
        cls.tep_sql = sorted(dc.THU_MUC_SQL.glob('[0-9][0-9][0-9]_*.sql'),
                             key=lambda p: int(p.name.split('_', 1)[0]))
        dc.ap_doi_cau_truc(cls.conn, cls.tep_sql)
        cls.module_login = cls.tien_to + 'dang_nhap_mod_demo'
        mk = secrets.token_urlsafe(32)
        cls.conn.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB PASSWORD {}')
                         .format(sql.Identifier(cls.module_login), sql.Literal(mk)))
        cls.conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier(cls.db), sql.Identifier(cls.module_login)))
        cls.conn.execute(sql.SQL('GRANT USAGE ON SCHEMA loi TO {}').format(sql.Identifier(cls.module_login)))
        for khoa in ('log_parameter_max_length', 'log_parameter_max_length_on_error'):
            cls.conn.execute(sql.SQL('ALTER ROLE {} SET {}=0').format(sql.Identifier(cls.module_login), sql.Identifier(khoa)))
        cls.module = psycopg.connect(**{**cls.cac_thong_tin['core'], 'user': cls.module_login, 'password': mk}, autocommit=True)
        cls.addClassCleanup(cls.module.close)

    def setUp(self):
        self.may, self.instance = uuid4(), uuid4()
        self.ma_module = 'demo_' + uuid4().hex[:12]
        self._ghi('module', ma=self.ma_module, ten='DEMO')
        self._ghi('phien_ban_module', module=self.ma_module, so_phien_ban='1', ma_bam_goi='a'*64, tuong_thich={})
        self._ghi('trang_thai_module', module=self.ma_module, so_phien_ban='1', trang_thai='da_cai')
        with self.core.transaction():
            self.s = sc.cap(self.core, self.may, 19016, module=self.ma_module)
        self.id = UUID(self.s['id'])

    def _nhan(self, conn=None, **doi):
        conn = conn or self.core
        now = datetime.now(timezone.utc)
        p = dict(pid=1234, dinh_danh_lan_tao='DEMO-CREATE-1', phien_ban='1',
                 nhan_yeu_cau_luc=now, bat_dau_luc=now, lease_giay=120)
        with conn.transaction():
            return sc.nhan(conn, self.id, doi.pop('instance_id', self.instance),
                           doi.pop('the_he_cu', 0), **{**p, **doi})

    def _doc(self, conn=None):
        conn = conn or self.core
        with conn.transaction():
            return sc.doc(conn, self.id)

    def _het_lease(self):
        self.conn.execute("UPDATE loi.so_cong SET giu_den=clock_timestamp()-interval '1 second' WHERE id=%s", (self.id,))

    def _phien_admin(self, *, admin=True, module='core'):
        nd, pn = uuid4(), uuid4()
        self.conn.execute("INSERT INTO loi.nguoi_dung(id,dang_nhap,ten,vai_tro) VALUES (%s,%s,'DEMO','XEM')", (nd, nd.hex))
        self.conn.execute("INSERT INTO loi.phap_nhan(id,ma,ten) VALUES (%s,%s,'DEMO')", (pn, pn.hex))
        self.conn.execute('INSERT INTO loi.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,%s)', (nd, pn, [module]))
        if admin:
            self.conn.execute("INSERT INTO loi.mtq_admin(nguoi_dung_id,cap_boi,ly_do) VALUES (%s,%s,'DEMO')", (nd, nd))
        ma = phien.cap_phien(self.core, nguoi_dung_id=nd, module=module, phap_nhan_id=pn,
            dang_nhap_csdl=self.core.info.user, pham_vi_hanh_dong=[MO_KHOA],
            hieu_luc_den=datetime.now(timezone.utc)+timedelta(minutes=5)).ma
        return ma, pn

    def _khoa(self):
        self._nhan()
        with self.core.transaction():
            sc.loi_khoi_dong(self.core, self.id, self.instance, 1, ma_loi='CONG_BI_CHIEM')
        return self._doc()

    def test_login_that_chuoi_theo_so_ap_lai_khong_doi(self):
        self.assertEqual(dc.ap_doi_cau_truc(self.conn, self.tep_sql), max(dc._doc_chuoi(self.tep_sql)))
        for conn in (self.core, self.module, self.cai_dat):
            self.assertEqual(conn.execute('SELECT session_user,current_user').fetchone(), (conn.info.user,)*2)
        self.conn.execute(SQL)
        self.assertEqual(self._doc(), self.s)

    def test_cong_co_dinh_unique_chu_va_cong(self):
        with self.core.transaction():
            self.assertEqual(sc.cap(self.core, self.may, 19016, module=self.ma_module), self.s)
        with self.assertRaises(sc.LoiSoCong) as bat, self.core.transaction():
            sc.cap(self.core, self.may, 19017, module=self.ma_module)
        self.assertEqual(bat.exception.ma, 'CONG_CO_DINH')
        for dia_chi, cong in (('127.0.0.1', 19017), ('::1', 19016)):
            with self.assertRaises(psycopg.errors.UniqueViolation):
                self.conn.execute('INSERT INTO loi.so_cong(may_chu_id,dia_chi_nghe,cong,module) VALUES (%s,%s,%s,%s)',
                                  (self.may, dia_chi, cong, self.ma_module))
        khac = 'demo_' + uuid4().hex[:12]
        self._ghi('module', ma=khac, ten='DEMO')
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.conn.execute('INSERT INTO loi.so_cong(may_chu_id,dia_chi_nghe,cong,module) VALUES (%s,%s,%s,%s)',
                              (self.may, '127.0.0.1', 19016, khac))

    def test_hai_ket_noi_cas_chi_mot_nhan(self):
        rao = Barrier(2)
        def chay(_):
            with psycopg.connect(**self.cac_thong_tin['core'], autocommit=True) as conn:
                conn.execute("SET statement_timeout='10s'")
                rao.wait(timeout=10)
                try:
                    self._nhan(conn, instance_id=uuid4())
                    return 'DAT'
                except sc.LoiSoCong as exc:
                    return exc.ma
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(chay, range(2))), ['DAT', 'CONG_CAS'])
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.module_phien_chay WHERE so_cong_id=%s AND ket_thuc_luc IS NULL',
                                         (self.id,)).fetchone()[0], 1)

    def test_lease_het_can_doi_chieu_the_he_cu_bi_chan(self):
        self._nhan()
        self._het_lease()
        with self.assertRaises(sc.LoiSoCong) as bat:
            self._nhan(instance_id=uuid4(), the_he_cu=1)
        self.assertEqual(bat.exception.ma, 'CONG_CAN_DOI_CHIEU')
        moi = self._nhan(instance_id=uuid4(), the_he_cu=1, doi_chieu_id=uuid4())
        self.assertEqual(moi['the_he'], 2)
        self.assertEqual(self.conn.execute('SELECT ly_do_ket_thuc FROM loi.module_phien_chay WHERE id=%s',
                                         (self.instance,)).fetchone()[0], 'GIAN_DOAN')
        for goi in (lambda: sc.gia_han(self.core, self.id, self.instance, 1),
                    lambda: sc.tra(self.core, self.id, self.instance, 1),
                    lambda: sc.loi_khoi_dong(self.core, self.id, self.instance, 1, ma_loi='DEMO'),
                    lambda: sc.san_sang(self.core, self.id, self.instance, 1, bang_chung_id=uuid4()),
                    lambda: sc.ghi_so_do(self.core, self.id, self.instance, 1,
                        cua_so_tu=datetime.now(timezone.utc), cua_so_den=datetime.now(timezone.utc))):
            with self.assertRaises(sc.LoiSoCong) as bat, self.core.transaction():
                goi()
            self.assertEqual(bat.exception.ma, 'CONG_MAT_LEASE')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.module_phien_chay WHERE so_cong_id=%s', (self.id,)).fetchone()[0], 2)

    def test_gia_han_khong_rut_ngan_va_khong_hoi_sinh_lease(self):
        truoc = self._nhan(lease_giay=3600)
        with self.core.transaction():
            sau = sc.gia_han(self.core, self.id, self.instance, 1, lease_giay=1)
        self.assertEqual(sau['giu_den'], truoc['giu_den'])
        self._het_lease()
        with self.assertRaises(sc.LoiSoCong) as bat, self.core.transaction():
            sc.gia_han(self.core, self.id, self.instance, 1)
        self.assertEqual(bat.exception.ma, 'CONG_MAT_LEASE')

    def test_cung_pid_khac_instance_khong_gia_han_duoc(self):
        self._nhan()
        with self.assertRaises(sc.LoiSoCong), self.core.transaction():
            sc.gia_han(self.core, self.id, uuid4(), 1)
        with self.assertRaises(sc.LoiSoCong), self.core.transaction():
            sc.tra(self.core, self.id, self.instance, 2)

    def test_tra_giu_cong_va_lich_su_khong_xoa(self):
        self._nhan()
        with self.core.transaction():
            sc.tra(self.core, self.id, self.instance, 1)
        self.assertEqual(self._doc()['cong'], 19016)
        self.assertEqual(self._doc()['trang_thai'], 'TRONG')
        self.assertEqual(self._nhan(instance_id=uuid4(), the_he_cu=1)['the_he'], 2)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.module_phien_chay WHERE so_cong_id=%s', (self.id,)).fetchone()[0], 2)

    def test_khoa_loi_con_sau_restart_va_ap_lai_sql(self):
        khoa = self._khoa()
        self.conn.execute(SQL)
        with psycopg.connect(**self.cac_thong_tin['core'], autocommit=True) as moi:
            self.assertEqual(self._doc(moi), khoa)
            with self.assertRaises(sc.LoiSoCong) as bat:
                self._nhan(moi, instance_id=uuid4(), the_he_cu=1, doi_chieu_id=uuid4())
            self.assertEqual(bat.exception.ma, 'CONG_KHOA_LOI')
        with self.assertRaises(sc.LoiSoCong), self.core.transaction():
            sc.tra(self.core, self.id, self.instance, 1)

    def test_admin_mo_khoa_cas_co_audit_va_van_can_doi_chieu(self):
        khoa = self._khoa()
        ma, pn = self._phien_admin()
        request = uuid4()
        with self.core.transaction():
            sc.mo_khoa(self.core, self.id, khoa['phien_ban_dong'], ma=ma, phap_nhan_id=pn, request_id=request)
        audit = self.conn.execute('SELECT nguoi_dung_id,phap_nhan_id,request_id FROM loi.nhat_ky_kiem_toan WHERE doi_tuong_id=%s AND hanh_dong=%s',
                                  (self.id, MO_KHOA)).fetchone()
        self.assertIsNotNone(audit[0])
        self.assertEqual(audit[1:], (pn, request))
        with self.assertRaises(sc.LoiSoCong), self.core.transaction():
            sc.mo_khoa(self.core, self.id, khoa['phien_ban_dong'], ma=ma, phap_nhan_id=pn, request_id=uuid4())
        self.assertEqual(self._nhan(instance_id=uuid4(), the_he_cu=1, doi_chieu_id=uuid4())['the_he'], 2)

    def test_mo_khoa_sai_admin_module_phap_nhan_va_ma_gia(self):
        khoa = self._khoa()
        for admin, module in ((False, 'core'), (True, self.ma_module)):
            ma, pn = self._phien_admin(admin=admin, module=module)
            with self.assertRaises(sc.LoiSoCong), self.core.transaction():
                sc.mo_khoa(self.core, self.id, khoa['phien_ban_dong'], ma=ma, phap_nhan_id=pn, request_id=uuid4())
        ma, pn = self._phien_admin()
        for token, workspace in ((ma, uuid4()), (phien.MaBiMat('GIA'*24), pn)):
            with self.assertRaises(sc.LoiSoCong), self.core.transaction():
                sc.mo_khoa(self.core, self.id, khoa['phien_ban_dong'], ma=token, phap_nhan_id=workspace, request_id=uuid4())
        self.assertEqual(self._doc(), khoa)

    def test_rollback_mo_khoa_cung_audit(self):
        khoa = self._khoa()
        ma, pn = self._phien_admin()
        request = uuid4()
        with self.assertRaisesRegex(RuntimeError, 'DEMO'), self.core.transaction():
            sc.mo_khoa(self.core, self.id, khoa['phien_ban_dong'], ma=ma, phap_nhan_id=pn, request_id=request)
            raise RuntimeError('DEMO')
        self.assertEqual(self._doc(), khoa)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.nhat_ky_kiem_toan WHERE request_id=%s', (request,)).fetchone()[0], 0)

    def test_engine_dung_registry_khong_them_role_login(self):
        truoc = self.conn.execute('SELECT oid FROM pg_roles WHERE rolcanlogin ORDER BY oid').fetchall()
        engine = self._ghi('engine', ma='e_demo_'+uuid4().hex[:8], ten='DEMO', so_phien_ban='1', ma_bam_goi='a'*64,
            adapter={'ma': 'demo', 'phien_ban': '1'}, capability=[dict(ma='demo.doc@1', dau_vao='tham_chieu_tep.v1',
            dau_ra='demo.v1', mime=['application/pdf'], tep_toi_da_mib=20, trang_toi_da=60, thoi_han_giay=900)], gioi_han={})
        with self.cai_dat.transaction():
            ho_so = sc.tao_ho_so(self.cai_dat, engine_id=engine, may_chu_id=self.may,
                                 executable='DEMO/engine.exe', doi_so=['--demo'])
        with self.core.transaction():
            so = sc.cap(self.core, self.may, 19017, engine_ho_so_id=ho_so)
        self.id = UUID(so['id'])
        self._nhan()
        self.assertEqual(self.conn.execute('SELECT oid FROM pg_roles WHERE rolcanlogin ORDER BY oid').fetchall(), truoc)
        self.assertEqual(self.conn.execute('SELECT engine_ho_so_id FROM loi.engine_phien_chay WHERE id=%s', (self.instance,)).fetchone()[0], ho_so)
        with self.assertRaises(sc.LoiSoCong), self.core.transaction():
            sc.cap(self.core, uuid4(), 19018, engine_ho_so_id=ho_so)

    def test_module_core_cai_dat_khong_doc_ghi_thang_bang(self):
        for conn in (self.core, self.module, self.cai_dat):
            for bang in BANG:
                for cau in ('SELECT * FROM loi.{}', 'INSERT INTO loi.{} DEFAULT VALUES',
                            'UPDATE loi.{} SET id=id', 'DELETE FROM loi.{}', 'TRUNCATE loi.{}'):
                    with self.subTest(login=conn.info.user, bang=bang, cau=cau), self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        conn.execute(sql.SQL(cau).format(sql.Identifier(bang)))
        catalog = self.conn.execute("SELECT relrowsecurity,relforcerowsecurity,pg_get_userbyid(relowner) FROM pg_class WHERE relnamespace='loi'::regnamespace AND relname=ANY(%s)", (list(BANG),)).fetchall()
        self.assertEqual(len(catalog), len(BANG))
        self.assertTrue(all(r == (True, True, self.tien_to+'vai_doi_cau_truc_loi') for r in catalog))

    def test_module_duoc_cap_nham_execute_van_khong_gia_core(self):
        ck = 'loi.so_cong_doc(uuid)'
        self.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION '+ck+' TO {}').format(sql.Identifier(self.module_login)))
        try:
            with self.assertRaises(sc.LoiSoCong) as bat, self.module.transaction():
                sc.doc(self.module, self.id)
            self.assertEqual(bat.exception.ma, 'CONG_CHI_CORE')
        finally:
            self.conn.execute(sql.SQL('REVOKE EXECUTE ON FUNCTION '+ck+' FROM {}').format(sql.Identifier(self.module_login)))

    def test_so_do_readiness_va_ket_thuc_ben_vung(self):
        self._nhan()
        now = datetime.now(timezone.utc)
        with self.core.transaction():
            sc.san_sang(self.core, self.id, self.instance, 1, bang_chung_id=uuid4())
            so_do = sc.ghi_so_do(self.core, self.id, self.instance, 1,
                cua_so_tu=now-timedelta(seconds=1), cua_so_den=now, cpu_ms=12.5, ram_dinh_byte=4096)
            sc.tra(self.core, self.id, self.instance, 1)
        row = self.conn.execute('SELECT cpu_ms,ram_dinh_byte,ram_trung_binh_byte,chay_viec_ms FROM loi.so_do_phien_chay WHERE id=%s', (so_do,)).fetchone()
        self.assertEqual(tuple(row), (12.5, 4096, None, None))
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.so_do_phien_chay WHERE module_phien_id=%s', (self.instance,)).fetchone()[0], 4)
        with self.assertRaises(psycopg.Error):
            self.conn.execute('UPDATE loi.so_do_phien_chay SET cpu_ms=0 WHERE id=%s', (so_do,))

    def test_het_hieu_luc_va_khong_xoa_lich_su(self):
        with self.core.transaction():
            sc.het_hieu_luc(self.core, self.id, self.s['phien_ban_dong'])
        self.assertIsNotNone(self._doc()['het_hieu_luc_luc'])
        with self.assertRaises(sc.LoiSoCong):
            self._nhan()
        for bang in BANG:
            with self.subTest(bang=bang), self.assertRaises(psycopg.Error):
                self.conn.execute(sql.SQL('DELETE FROM loi.{}').format(sql.Identifier(bang)))

    def test_rollback_nhan_khong_de_phien_mo_coi(self):
        with self.assertRaisesRegex(RuntimeError, 'DEMO'), self.core.transaction():
            self._nhan()
            raise RuntimeError('DEMO')
        self.assertEqual(self._doc(), self.s)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.module_phien_chay WHERE so_cong_id=%s', (self.id,)).fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
