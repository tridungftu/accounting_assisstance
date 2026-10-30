"""G2-14: thuần/mock + PG opt-in, login thật, không DROP hoặc bật/tắt dịch vụ.

Admin chỉ provisioning/fixture giả và ép thời gian lease để không phải sleep.
Nghiệp vụ/chạy cạnh tranh dùng kết nối runtime, không SET ROLE giả runtime.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import pickle
import re
import sys
import traceback
import unittest
from unittest.mock import MagicMock
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import doi_cau_truc as dc, phien, viec

try:
    from . import test_g2_09 as g209
except ImportError:
    import test_g2_09 as g209

psycopg = g209.psycopg
if psycopg is not None:
    from psycopg import sql

SQL_PATH = dc.THU_MUC_SQL / '014_viec.sql'
SQL = SQL_PATH.read_text(encoding='utf-8')
LAP = g209.LAP
BANG = ('hang_viec', 'buoc_viec', 'lan_thu', 'lan_thu_trang_thai')
CHU_KY = ('viec_gia_han(text,text,uuid,text,uuid,uuid,bigint,integer)',
          'viec_ket_thuc(text,text,uuid,text,uuid,uuid,bigint,text,uuid,text)',
          'viec_trang_thai_lease(text,text,uuid,text,uuid,uuid,bigint)',
          'viec_rls(uuid,text,uuid)')


class ViecThuanTest(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.conn.info.transaction_status = 2
        self.ctx = dict(ma=phien.MaBiMat('CANARY_MA_GOC'), module='crm', phap_nhan_id=uuid4(), hanh_dong=LAP)
        self.ts = dict(loai='DEMO', phien_ban=1, khoa_dedupe='DEMO-14', tham_chieu_id=uuid4(),
                       bang_tham_chieu='doi_tuong', **self.ctx)
        self.giu = viec.GiuViec(*(uuid4() for _ in range(4)), 'crm', LAP, uuid4(), 1,
                               datetime.now(timezone.utc), phien.MaBiMat('CANARY_LEASE'))

    def test_tao_bind_khong_quan_ly_tx(self):
        viec.tao_viec(self.conn, **self.ts)
        cau, ts = self.conn.execute.call_args.args
        self.assertIn('loi.viec_tao', cau)
        self.assertNotIn('CANARY', cau)
        self.assertEqual(ts[:4], ('CANARY_MA_GOC', 'crm', self.ctx['phap_nhan_id'], LAP))
        self.assertEqual(ts[6], 'DEMO-14')
        for ten in ('connect', 'commit', 'rollback', 'transaction'):
            getattr(self.conn, ten).assert_not_called()

    def test_bat_buoc_cung_transaction(self):
        for tt in (0, 1, 3, 4):
            self.conn.info.transaction_status = tt
            for goi in (lambda: viec.tao_viec(self.conn, **self.ts),
                        lambda: viec.nhan(self.conn, uuid4(), dang_nhap_csdl='dang_nhap_loi', **self.ctx),
                        lambda: viec.ket_thuc(self.conn, self.giu),
                        lambda: viec.gia_han(self.conn, self.giu),
                        lambda: viec.phuc_hoi(self.conn, **self.ctx)):
                with self.subTest(tt=tt), self.assertRaises(ValueError):
                    goi()
        self.conn.execute.assert_not_called()

    def test_nhan_rong_va_ma_ngau_nhien_rieng_moi_lease(self):
        self.conn.execute.return_value.fetchone.return_value = (None,)
        self.assertIsNone(viec.nhan(self.conn, uuid4(), dang_nhap_csdl='dang_nhap_loi', **self.ctx))
        r = dict(viec_id=str(uuid4()), buoc_viec_id=str(uuid4()), lan_thu_id=str(uuid4()),
                 phap_nhan_id=str(self.ctx['phap_nhan_id']), module='crm', hanh_dong=LAP,
                 instance_id=str(uuid4()), the_he=2, giu_den=datetime.now(timezone.utc).isoformat())
        self.conn.execute.return_value.fetchone.return_value = {'r': r}
        a = viec.nhan(self.conn, uuid4(), dang_nhap_csdl='dang_nhap_loi', **self.ctx)
        b = viec.nhan(self.conn, uuid4(), dang_nhap_csdl='dang_nhap_loi', **self.ctx)
        self.assertEqual(a.the_he, 2)
        self.assertEqual(a.lan_thu_id, UUID(r['lan_thu_id']))
        self.assertRegex(a.ma.lay_de_truyen(), '^[A-Za-z0-9_-]{43}$')
        self.assertNotEqual(a.ma.lay_de_truyen(), b.ma.lay_de_truyen())

    def test_handle_khong_lo_bi_mat_hoac_serialize(self):
        self.assertEqual(repr(self.giu), 'GiuViec(<an>)')
        for goi in (lambda: pickle.dumps(self.giu), lambda: json.dumps(self.giu), lambda: asdict(self.giu)):
            with self.assertRaises(TypeError):
                goi()
        self.assertNotIn('CANARY', repr(self.giu.ma))

    def test_heartbeat_bat_bien_handle_va_cas_the_he(self):
        den = datetime.now(timezone.utc) + timedelta(minutes=2)
        self.conn.execute.return_value.fetchone.return_value = (den,)
        moi = viec.gia_han(self.conn, self.giu, lease_giay=20)
        self.assertIsNot(moi, self.giu)
        self.assertIs(moi.ma, self.giu.ma)
        self.assertEqual(moi.giu_den, den)
        ts = self.conn.execute.call_args.args[1]
        self.assertEqual(ts[4:7], (self.giu.viec_id, self.giu.instance_id, 1))
        self.assertEqual(ts[-1], 20)

    def test_ket_thuc_loi_huy_chua_ro_va_retry_an_toan(self):
        for tt, ma in (('XONG', None), ('LOI', 'DEMO'), ('DA_DUNG', None), ('CHUA_RO', 'DOI_CHIEU')):
            viec.ket_thuc(self.conn, self.giu, tt, ma_loi=ma)
            self.assertEqual(self.conn.execute.call_args.args[1][7:], (tt, None, ma))
        viec.thu_lai(self.conn, self.giu, 'LOI_AN_TOAN')
        self.assertEqual(self.conn.execute.call_args.args[1][7], 'CHO')
        viec.trang_thai_lease(self.conn, self.giu)
        self.assertIn('loi.viec_trang_thai_lease', self.conn.execute.call_args.args[0])

    def test_tu_choi_dau_vao_bool_so_hoac_loi_tu_do(self):
        for doi in ({'toi_da_lan_thu': True}, {'phien_ban': 0}, {'thu_lai_giay': 0}, {'giu_ngay': 0},
                    {'loai': 'sai'}, {'khoa_dedupe': ' '}, {'co_tac_dong_ngoai': 1},
                    {'thu_lai_an_toan': 'true'}, {'ma': 'ma ro'}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                viec.tao_viec(self.conn, **{**self.ts, **doi})
        for doi in ({'trang_thai': 'SAI'}, {'trang_thai': 'LOI'}, {'ma_loi': 'loi tu do'},
                    {'trang_thai': 'CHUA_RO', 'ma_loi': 'DEMO', 'ket_qua_id': uuid4()}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                viec.ket_thuc(self.conn, self.giu, **doi)
        for giay in (True, 0, 3601):
            with self.assertRaises(ValueError):
                viec.gia_han(self.conn, self.giu, lease_giay=giay)
        self.conn.execute.assert_not_called()

    def test_phuc_hoi_va_xep_lai_can_cas_bang_chung(self):
        instance = uuid4()
        viec.phuc_hoi(self.conn, instance_id=instance, **self.ctx)
        self.assertEqual(self.conn.execute.call_args.args[1][-1], instance)
        viec.yeu_cau_dung(self.conn, self.giu.viec_id, row_version='2', **self.ctx)
        self.assertEqual(self.conn.execute.call_args.args[1][-1], 2)
        bc = uuid4()
        viec.xep_lai(self.conn, self.giu.viec_id, row_version='3', ma_doi_chieu=bc, **self.ctx)
        self.assertEqual(self.conn.execute.call_args.args[1][-2:], (3, bc))
        for ban in (1, True, '0', '-1', '9223372036854775808'):
            with self.subTest(ban=ban), self.assertRaises(ValueError):
                viec.yeu_cau_dung(self.conn, self.giu.viec_id, row_version=ban, **self.ctx)

    def test_khong_dung_ma_lease_de_tao_viec_moi(self):
        with self.assertRaises(ValueError):
            viec.tao_viec(self.conn, **{**self.ts, 'viec_id': uuid4(), 'the_he': 1})
        with self.assertRaises(ValueError):
            viec.gia_han(self.conn, replace(self.giu, the_he=True))
        self.conn.execute.assert_not_called()

    def test_loi_driver_khong_ro_ma_dsn_stack(self):
        for ma, status in (('VIEC_MAT_LEASE', 409), ('VIEC_CAS', 409), ('VIEC_MTQ', 403),
                           ('VIEC_KHONG_THAY', 404), ('VIEC_CAN_DOI_CHIEU', 400), ('KHONG_BIET', 400)):
            exc = RuntimeError('CANARY_LEASE postgresql://CANARY:BI_MAT@localhost')
            exc.diag = MagicMock(message_primary=ma)
            self.conn.execute.side_effect = exc
            with self.assertRaises(viec.LoiViec) as bat:
                viec.ket_thuc(self.conn, self.giu)
            self.assertEqual(bat.exception.http_status, status)
            self.assertIsNone(bat.exception.__context__)
            self.assertIsNone(bat.exception.__cause__)
            self.assertNotIn('CANARY', ''.join(traceback.format_exception(bat.exception)))

    def test_sql_lich_su_bat_bien_va_quote(self):
        moc = re.findall(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', SQL)
        self.assertEqual((moc[0], moc[-1]), ('$$', '$$'))
        self.assertEqual(len(moc) % 2, 0)
        self.assertTrue(all(a == b for a, b in zip(moc[1:-1:2], moc[2:-1:2])))
        self.assertNotRegex(SQL, r'(?i)\bDROP\s+(?:TABLE|DATABASE|FUNCTION|ROLE|POLICY)')
        self.assertNotRegex(SQL, r'(?i)(?:REFERENCES|FROM|JOIN)\s+(?:mod_|master\.|viec\.)')
        self.assertNotRegex(SQL, r'(?i)(?:UPDATE|DELETE FROM)\s+loi\.(?:buoc_viec|lan_thu)\b')
        self.assertFalse(SQL_PATH.read_bytes().startswith(b'\xef\xbb\xbf'))


@unittest.skipUnless(psycopg is not None and os.environ.get('KHO_PG_DSN_TEST'),
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class ViecPostgresTest(unittest.TestCase):
    _ghi = g209.TaiLieuPostgresTest._ghi
    _contract = g209.TaiLieuPostgresTest._contract
    _trang_thai = g209.TaiLieuPostgresTest._trang_thai
    _cap = g209.TaiLieuPostgresTest._cap
    _ctx = g209.TaiLieuPostgresTest._ctx
    _tao = g209.TaiLieuPostgresTest._tao

    @classmethod
    def setUpClass(cls):
        g209.TaiLieuPostgresTest.setUpClass.__func__(cls)
        cls.tep_sql = sorted(dc.THU_MUC_SQL.glob('[0-9][0-9][0-9]_*.sql'),
                             key=lambda p: int(p.name.split('_', 1)[0]))
        dc.ap_doi_cau_truc(cls.conn, cls.tep_sql)
        for ck in CHU_KY:
            cls.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION loi.' + ck + ' TO {}')
                             .format(sql.Identifier(cls.module_login)))
        cls.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION loi.xac_minh_phien(text,text,uuid,text,uuid,bigint) TO {}')
                         .format(sql.Identifier(cls.module_login)))

    def _resolver(self):
        g209.TaiLieuPostgresTest._resolver(self)
        # Schema module duoc fixture g206 dung trong setUp, khong phai setUpClass.
        self.conn.execute('CREATE TABLE IF NOT EXISTS mod_crm.ket_qua_g214(id uuid PRIMARY KEY, noi_dung text NOT NULL)')
        self.conn.execute(sql.SQL('GRANT USAGE ON SCHEMA mod_crm TO {}').format(sql.Identifier(self.module_login)))
        self.conn.execute(sql.SQL('GRANT INSERT,SELECT ON mod_crm.ket_qua_g214 TO {},{}')
                          .format(sql.Identifier(self.module_login), sql.Identifier(self.core.info.user)))

    def setUp(self):
        g209.TaiLieuPostgresTest.setUp(self)
        self.instance = uuid4()
        self.viec_id = self._moi()

    def _moi(self, **doi):
        with self.core.transaction():
            ts = dict(loai='DEMO', phien_ban=1, khoa_dedupe=uuid4().hex,
                      tham_chieu_id=self.obj, bang_tham_chieu='doi_tuong', thu_lai_giay=1)
            return viec.tao_viec(self.core, **{**ts, **self._ctx(), **doi})

    def _nhan(self, *, conn=None, module=False, **doi):
        conn = conn or self.core
        with conn.transaction():
            return viec.nhan(conn, self.instance, dang_nhap_csdl=self.module_login if module else self.core.info.user,
                             **{**self._ctx(), **doi})

    def _trang(self, viec_id=None):
        return self.conn.execute('SELECT trang_thai,phien_ban_dong::text FROM loi.hang_viec WHERE id=%s',
                                 (viec_id or self.viec_id,)).fetchone()

    def _het_han(self, g):
        # Chi admin fixture dieu khien dong ho; khong chay ca nghiep vu bang owner.
        self.conn.execute("UPDATE loi.hang_viec SET giu_den=clock_timestamp()-interval '1 second' WHERE id=%s", (g.viec_id,))

    def _xac(self, g, conn=None):
        return phien.xac_minh_phien(conn or self.core, ma=g.ma, module=g.module,
            phap_nhan_id=g.phap_nhan_id, hanh_dong=g.hanh_dong, viec_id=g.viec_id, the_he=g.the_he)

    def test_ap_chuoi_theo_so_chay_lai_va_login_that(self):
        chuoi = dc._doc_chuoi(self.tep_sql)
        self.assertEqual(dc.ap_doi_cau_truc(self.conn, self.tep_sql), max(chuoi))
        self.assertEqual(self.conn.execute("SELECT so_phien_ban,ma_bam FROM loi.lich_su_doi_cau_truc WHERE ma_goi='core' ORDER BY so_phien_ban").fetchall(),
                         [(so, bam) for so, (_, bam) in chuoi.items()])
        for conn in (self.core, self.module):
            self.assertEqual(conn.execute('SELECT current_user,session_user').fetchone(), (conn.info.user,)*2)

    def test_hai_worker_tranh_mot_viec_chi_mot_nhan_duoc(self):
        def tranh(_):
            with psycopg.connect(**self.cac_thong_tin['core'], autocommit=True) as conn:
                with conn.transaction():
                    return viec.nhan(conn, uuid4(), dang_nhap_csdl=conn.info.user, **self._ctx())
        with ThreadPoolExecutor(max_workers=2) as pool:
            kq = list(pool.map(tranh, range(2)))
        self.assertEqual(sum(g is not None for g in kq), 1)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.lan_thu WHERE viec_id=%s', (self.viec_id,)).fetchone()[0], 1)

    def test_dedupe_giu_nguyen_hop_dong_va_khong_tao_buoc_lap(self):
        khoa = uuid4().hex
        dau = self._moi(khoa_dedupe=khoa)
        self.assertEqual(self._moi(khoa_dedupe=khoa), dau)
        with self.assertRaises(viec.LoiViec) as bat:
            self._moi(khoa_dedupe=khoa, co_tac_dong_ngoai=True)
        self.assertEqual(bat.exception.ma, 'VIEC_KHOA_KHAC_NOI_DUNG')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.buoc_viec WHERE viec_id=%s', (dau,)).fetchone()[0], 1)

    def test_lease_het_han_chan_heartbeat_ket_thuc_va_xac_minh_chung(self):
        g = self._nhan()
        self.assertIsNotNone(self._xac(g))
        self._het_han(g)
        self.assertIsNone(self._xac(g))
        for goi in (lambda: viec.gia_han(self.core, g), lambda: viec.ket_thuc(self.core, g)):
            with self.assertRaises(viec.LoiViec) as bat, self.core.transaction():
                goi()
            self.assertEqual(bat.exception.ma, 'VIEC_MAT_LEASE')

    def test_lease_het_han_sau_khi_transaction_da_bat_dau(self):
        g = self._nhan(module=True)
        with self.assertRaises(viec.LoiViec), self.module.transaction():
            self.module.execute('SELECT transaction_timestamp()')
            self._het_han(g)
            viec.gia_han(self.module, g)

    def test_cas_sai_the_he_instance_va_token(self):
        g = self._nhan()
        for sai in (replace(g, the_he=g.the_he+1), replace(g, instance_id=uuid4()),
                    replace(g, ma=phien.MaBiMat('GIA'*24))):
            with self.assertRaises(viec.LoiViec), self.core.transaction():
                viec.ket_thuc(self.core, sai)
        self.assertEqual(self._trang()[0], 'DANG_CHAY')
        with self.core.transaction():
            self.assertTrue(viec.ket_thuc(self.core, g))

    def test_heartbeat_giu_the_he_va_gia_han_ma_cung_tx(self):
        g = self._nhan()
        with self.core.transaction():
            moi = viec.gia_han(self.core, g, lease_giay=300)
        self.assertEqual(moi.the_he, g.the_he)
        self.assertGreater(moi.giu_den, g.giu_den)
        self.assertEqual(self._xac(g).hieu_luc_den, moi.giu_den)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.lan_thu_trang_thai WHERE viec_id=%s', (g.viec_id,)).fetchone()[0], 2)

    def test_rollback_nghiep_vu_va_trang_thai_viec_cung_tx(self):
        g = self._nhan(module=True)
        kq = uuid4()
        with self.assertRaisesRegex(RuntimeError, 'DEMO_ROLLBACK'):
            with self.module.transaction():
                self.module.execute('INSERT INTO mod_crm.ket_qua_g214 VALUES (%s,%s)', (kq, 'DEMO'))
                viec.ket_thuc(self.module, g, ket_qua_id=kq)
                raise RuntimeError('DEMO_ROLLBACK')
        self.assertEqual(self._trang()[0], 'DANG_CHAY')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM mod_crm.ket_qua_g214 WHERE id=%s', (kq,)).fetchone()[0], 0)
        self.assertIsNotNone(self._xac(g, self.module))
        with self.module.transaction():
            self.module.execute('INSERT INTO mod_crm.ket_qua_g214 VALUES (%s,%s)', (kq, 'DEMO'))
            viec.ket_thuc(self.module, g, ket_qua_id=kq)
        self.assertEqual(self._trang()[0], 'XONG')
        self.assertIsNone(self._xac(g, self.module))

    def test_mat_lease_rollback_phan_ghi_lien_quan(self):
        g = self._nhan(module=True)
        self._het_han(g)
        kq = uuid4()
        with self.assertRaises(viec.LoiViec), self.module.transaction():
            self.module.execute('INSERT INTO mod_crm.ket_qua_g214 VALUES (%s,%s)', (kq, 'DEMO'))
            viec.ket_thuc(self.module, g, ket_qua_id=kq)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM mod_crm.ket_qua_g214 WHERE id=%s', (kq,)).fetchone()[0], 0)

    def test_restart_ghi_gian_doan_va_khong_tu_retry(self):
        g = self._nhan()
        with self.core.transaction():
            self.assertEqual(viec.phuc_hoi(self.core, instance_id=self.instance, **self._ctx()), 1)
        self.assertEqual(self._trang()[0], 'GIAN_DOAN')
        self.assertEqual(self.conn.execute('SELECT trang_thai FROM loi.lan_thu_trang_thai WHERE lan_thu_id=%s ORDER BY phien_ban_dong', (g.lan_thu_id,)).fetchall(),
                         [('DANG_CHAY',), ('GIAN_DOAN',)])
        self.assertIsNone(self._xac(g))
        self.assertIsNone(self._nhan())

    def test_chua_ro_khong_nhan_lai_tu_dong_ke_ca_restart(self):
        self.viec_id = self._moi(co_tac_dong_ngoai=True, thu_lai_an_toan=True)
        # Dong viec mac dinh truoc de nhan dung viec co tac dong ngoai.
        g0 = self._nhan()
        with self.core.transaction():
            viec.ket_thuc(self.core, g0)
        g = self._nhan()
        self._het_han(g)
        self.assertIsNone(self._nhan())
        self.assertEqual(self._trang()[0], 'CHUA_RO')
        with self.assertRaises(ValueError), self.core.transaction():
            viec.xep_lai(self.core, g.viec_id, row_version=self._trang()[1], ma_doi_chieu=None, **self._ctx())
        with self.assertRaises(psycopg.errors.InvalidParameterValue), self.core.transaction():
            self.core.execute('SELECT loi.viec_xep_lai(%s,%s,%s,%s,%s,%s,NULL)',
                (self.ma.lay_de_truyen(), 'crm', self.pn, LAP, g.viec_id, int(self._trang()[1])))
        self.assertIsNone(self._nhan())

    def test_doi_chieu_xep_lai_cap_the_he_va_ma_moi(self):
        # Contract khai thu lai an toan, doi chieu bang chung qua kenh Core.
        self.conn.execute('UPDATE loi.hang_viec SET thu_lai_an_toan=true WHERE id=%s', (self.viec_id,))
        g = self._nhan()
        with self.core.transaction():
            viec.phuc_hoi(self.core, instance_id=self.instance, **self._ctx())
        with self.assertRaises(viec.LoiViec), self.core.transaction():
            viec.xep_lai(self.core, g.viec_id, row_version='1', ma_doi_chieu=uuid4(), **self._ctx())
        with self.core.transaction():
            viec.xep_lai(self.core, g.viec_id, row_version=self._trang()[1], ma_doi_chieu=uuid4(), **self._ctx())
        self.conn.execute("UPDATE loi.hang_viec SET thu_lai_sau=clock_timestamp()-interval '1 second' WHERE id=%s", (g.viec_id,))
        moi = self._nhan()
        self.assertEqual(moi.the_he, g.the_he+1)
        self.assertNotEqual(moi.ma.lay_de_truyen(), g.ma.lay_de_truyen())
        self.assertIsNone(self._xac(g))
        self.assertIsNotNone(self._xac(moi))
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.lan_thu WHERE viec_id=%s', (g.viec_id,)).fetchone()[0], 2)

    def test_huy_hop_tac_khong_mat_dau_chua_ro(self):
        g = self._nhan()
        with self.core.transaction():
            viec.yeu_cau_dung(self.core, g.viec_id, row_version=self._trang()[1], **self._ctx())
        with self.core.transaction():
            self.assertTrue(viec.trang_thai_lease(self.core, g)['yeu_cau_dung'])
            viec.ket_thuc(self.core, g, 'DA_DUNG')
        self.assertEqual(self._trang()[0], 'DA_DUNG')
        self.assertIsNone(self._xac(g))

    def test_runtime_khong_ghi_thang_va_lich_su_khong_sua(self):
        self._nhan()
        for conn in (self.core, self.module):
            for bang in BANG:
                with self.subTest(bang=bang, login=conn.info.user), self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    conn.execute(sql.SQL('INSERT INTO loi.{} DEFAULT VALUES').format(sql.Identifier(bang)))
        # Trigger chan ke ca owner; khong co sua de lich su dang chay.
        for bang in BANG[1:]:
            with self.subTest(bang=bang), self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
                self.conn.execute(sql.SQL('UPDATE loi.{} SET module=module WHERE viec_id=%s').format(sql.Identifier(bang)), (self.viec_id,))

    def test_sai_pn_module_login_thu_hoi_quyen_deu_chan(self):
        g = self._nhan(module=True)
        self.assertIsNone(self._xac(g))  # ma module khong dung duoc tren login Core
        for sai in (replace(g, phap_nhan_id=self.pn_khac), replace(g, module='core')):
            with self.assertRaises(viec.LoiViec), self.module.transaction():
                viec.gia_han(self.module, sai)
        with self.assertRaises(viec.LoiViec), self.core.transaction():
            viec.gia_han(self.core, g)
        phien.thu_hoi_phien_nguoi_dung(self.core, nguoi_dung_id=self.nd)
        with self.assertRaises(viec.LoiViec), self.module.transaction():
            viec.ket_thuc(self.module, g)

    def test_token_chi_luu_hash_khong_luu_ro(self):
        g = self._nhan()
        ma = g.ma.lay_de_truyen()
        bam = self.conn.execute('SELECT ma_bam FROM loi.phien_xac_thuc WHERE viec_id=%s AND the_he=%s', (g.viec_id, g.the_he)).fetchone()[0]
        import hashlib
        self.assertEqual(bytes(bam), hashlib.sha256(ma.encode()).digest())
        for bang in BANG:
            du_lieu = self.conn.execute(sql.SQL('SELECT to_jsonb(t)::text FROM loi.{} t WHERE {}=%s')
                .format(sql.Identifier(bang), sql.Identifier('id' if bang == 'hang_viec' else 'viec_id')), (g.viec_id,)).fetchall()
            self.assertNotIn(ma, str(du_lieu))

    def test_rls_guc_gia_khong_tao_quyen_handle_chi_thay_viec_cua_minh(self):
        g = self._nhan(module=True)
        khac = self._moi()
        self.conn.execute(sql.SQL('GRANT SELECT ON loi.hang_viec TO {}').format(sql.Identifier(self.module_login)))
        try:
            with self.module.transaction():
                for k, v in {'ktt.ma_phien': 'GIA'*24, 'ktt.module': 'crm', 'ktt.phap_nhan_id': str(self.pn),
                             'ktt.hanh_dong': LAP, 'ktt.viec_id': str(g.viec_id), 'ktt.the_he': '1'}.items():
                    self.module.execute('SELECT set_config(%s,%s,true)', (k, v))
                self.assertEqual(self.module.execute('SELECT id FROM loi.hang_viec').fetchall(), [])
                viec.trang_thai_lease(self.module, g)
                self.assertEqual(self.module.execute('SELECT id FROM loi.hang_viec').fetchall(), [(g.viec_id,)])
                self.assertNotEqual(khac, g.viec_id)
        finally:
            self.conn.execute(sql.SQL('REVOKE SELECT ON loi.hang_viec FROM {}').format(sql.Identifier(self.module_login)))


if __name__ == '__main__':
    unittest.main()
