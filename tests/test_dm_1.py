"""DM-1: test thuần và PG opt-in; không khởi động/dừng dịch vụ, không DROP.

Provisioning tạo kho_test_* riêng; thao tác dưới login Core thật, FORCE RLS.
Các hàm fixture chỉ thử lớp constraint (kể cả đường ghi bỏ qua V2), không
thay thế hàm Core hay cấp DML bảng cho runtime. Lead chạy PG và review Opus.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import sys
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import danh_muc as dm, doi_cau_truc as dc, lien_ket as lk, mtq, phap_nhan_demo as demo, phien

try:
    from . import test_g2_06 as g206
except ImportError:
    import test_g2_06 as g206

SQL_PATH = dc.THU_MUC_SQL / '023_phap_nhan_demo.sql'
SQL = SQL_PATH.read_text(encoding='utf-8')
HD = 'CORE:DEMO:SUA'


class DemoThuanTest(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.conn.info.transaction_status = 2
        self.ts = dict(ma=phien.MaBiMat('CANARY_'+'x'*32), phap_nhan_id=uuid4(),
                       la_demo=True, row_version='1', request_id=uuid4())
        self.conn.execute.return_value.fetchone.return_value = ({'la_demo': True, 'row_version': '2'},)

    def test_dat_co_bind_cas_va_khong_quan_ly_transaction(self):
        self.assertEqual(demo.dat_demo(self.conn, **self.ts)['row_version'], '2')
        cau, ts = self.conn.execute.call_args.args
        self.assertIn('loi.phap_nhan_dat_demo', cau)
        self.assertNotIn('CANARY', cau)
        self.assertEqual(ts, (self.ts['ma'].lay_de_truyen(), self.ts['phap_nhan_id'], True, 1, self.ts['request_id']))
        for ten in ('commit', 'rollback', 'transaction'):
            getattr(self.conn, ten).assert_not_called()

    def test_mac_dinh_loai_demo_va_nhan_giao_dien(self):
        self.conn.execute.return_value.fetchall.return_value = [(uuid4(), 'D', 'Mẫu', True, '2')]
        self.assertEqual(demo.pham_vi(self.conn)[0].nhan, 'DEMO')
        self.assertEqual(self.conn.execute.call_args.args[1], (False,))
        demo.pham_vi(self.conn, gom_demo=True)
        self.assertEqual(self.conn.execute.call_args.args[1], (True,))
        self.assertEqual(demo.nhan_hien_thi(False), '')

    def test_chan_du_lieu_mo_ho_truoc_sql(self):
        for doi in ({'la_demo': 'false'}, {'la_demo': 1}, {'row_version': '0'},
                    {'row_version': 1}, {'row_version': '01'}, {'row_version': '9223372036854775808'},
                    {'ma': 'CANARY'}, {'phap_nhan_id': 'sai'}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                demo.dat_demo(self.conn, **(self.ts | doi))
        for co in (None, 1, 'true'):
            with self.subTest(co=co), self.assertRaises(ValueError):
                demo.pham_vi(self.conn, gom_demo=co)
        self.conn.execute.assert_not_called()

    def test_bat_buoc_transaction_va_khong_nhan_actor(self):
        self.conn.info.transaction_status = 0
        for goi in (lambda: demo.dat_demo(self.conn, **self.ts), lambda: demo.pham_vi(self.conn)):
            with self.assertRaises(ValueError):
                goi()
        with self.assertRaises(TypeError):
            demo.dat_demo(self.conn, **self.ts, actor=uuid4())
        self.conn.execute.assert_not_called()

    def test_loi_an_driver_token_va_giu_ma_da_biet(self):
        for ma, du_kien in [('DEMO_CAS', 'DEMO_CAS'), ('DEMO_DA_CO_DU_LIEU', 'DEMO_DA_CO_DU_LIEU'),
                            ('CANARY_PASSWORD', 'DEMO_THAT_BAI')]:
            exc = RuntimeError('postgresql://CANARY:SECRET@localhost')
            exc.diag = SimpleNamespace(message_primary=ma)
            self.conn.execute.side_effect = exc
            with self.assertRaises(demo.LoiPhapNhanDemo) as bat:
                demo.dat_demo(self.conn, **self.ts)
            self.assertEqual(bat.exception.ma, du_kien)
            self.assertIsNone(bat.exception.__context__)
            self.assertNotIn('CANARY', ''.join(traceback.format_exception(bat.exception)))

    def test_migration_quote_utf8_va_khong_sua_chuoi_cu(self):
        quotes = re.findall(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', SQL)
        self.assertEqual(len(quotes) % 2, 0)
        self.assertTrue(all(a == b for a, b in zip(quotes[::2], quotes[1::2])))
        self.assertFalse(SQL_PATH.read_bytes().startswith(b'\xef\xbb\xbf'))
        self.assertNotRegex(SQL, r'(?i)\bDROP\s+(?:TABLE|ROLE|FUNCTION|DATABASE|TRIGGER)')

    def test_cua_python_giu_ma_demo_va_guard_lien_ket(self):
        ctx = dict(ma=self.ts['ma'], module='crm', phap_nhan_id=self.ts['phap_nhan_id'],
                   hanh_dong='CRM:TIEP_NHAN:HUY')
        for ma in ('DEMO_LIEN_KET_CHEO', 'DEMO_PHAP_NHAN', 'DEMO_CAN_READ_COMMITTED',
                   'LIEN_KET_CAN_READ_COMMITTED'):
            for loai_loi, goi in (
                (dm.LoiDanhMuc, lambda: dm._goi(self.conn, 'SELECT demo()', ())),
                (lk.LoiLienKet, lambda: lk.huy(self.conn, lien_ket_id=uuid4(), ly_do='DEMO', **ctx)),
            ):
                with self.subTest(ma=ma, cua=loai_loi.__name__):
                    exc = RuntimeError('CANARY_DRIVER_TOKEN')
                    exc.diag = SimpleNamespace(message_primary=ma)
                    self.conn.execute.side_effect = exc
                    with self.assertRaises(loai_loi) as bat:
                        goi()
                    self.assertEqual(bat.exception.ma, ma)
                    self.assertIsNone(bat.exception.__context__)
                    self.assertNotIn('CANARY', ''.join(traceback.format_exception(bat.exception)))


@unittest.skipUnless(g206.psycopg is not None and g206.ADMIN_DSN,
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class DemoPostgresTest(unittest.TestCase):
    _ghi = g206.MTQPostgresTest._ghi
    _contract = g206.MTQPostgresTest._contract
    _trang_thai = g206.MTQPostgresTest._trang_thai
    _resolver = g206.MTQPostgresTest._resolver

    @classmethod
    def setUpClass(cls):
        g206.MTQPostgresTest.setUpClass.__func__(cls)
        cls.tep_sql = sorted(dc.THU_MUC_SQL.glob('[0-9][0-9][0-9]_*.sql'),
                             key=lambda p: int(p.name.split('_', 1)[0]))
        dc.ap_doi_cau_truc(cls.conn, cls.tep_sql)
        cls._fixture_ghi()

    @classmethod
    def _fixture_ghi(cls):
        # Fixture cua constraint: khong GRANT DML, khong sua RLS/Core function.
        # Loi.phien duoc xac minh trong cung ket noi truoc khi dung cac hook nay.
        sql = g206.sql
        owners = [('danh_muc', 'vai_doi_cau_truc_danh_muc'),
                  ('loi_tai_lieu', 'vai_doi_cau_truc_loi_tai_lieu'), ('loi', 'vai_doi_cau_truc_loi')]
        bodies = [
            """INSERT INTO danh_muc.lien_ket_chung_tu(phap_nhan_id,chung_tu_a_id,chung_tu_b_id,
                loai,muc_dich_lien_ket,mo_hinh_phan_bo,module_nghia_vu,loai_nghia_vu,nghia_vu_id,
                phien_ban_can_cu_id,ma_bam_phien_ban_can_cu,so_tien_khop_minor,tien_te,thang_tien,tao_boi)
                VALUES(p_pn,p_a,p_b,'DEMO','MONEY','DIRECT','crm','DEMO',p_a,p_a,repeat('a',64),1,'VND',0,p_ai);""",
            """INSERT INTO loi_tai_lieu.ket_qua_cong_bo(phap_nhan_id,ket_qua_id,tao_boi)
                VALUES(p_pn,p_a,p_ai);""",
            """INSERT INTO loi.mtq_pham_vi(gan_vai_id,phap_nhan_id,loai,khoa,cap_boi,ly_do)
                VALUES(p_a,p_pn,'PHAP_NHAN',p_b::text,p_ai,'DEMO');""",
        ]
        for (schema, owner), body in zip(owners, bodies):
            with cls.conn.transaction():
                cls.conn.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(cls.tien_to+owner)))
                cls.conn.execute(f'''CREATE FUNCTION {schema}.thu_demo_constraint(p_pn uuid,p_a uuid,p_b uuid,p_ai uuid)
                    RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
                    BEGIN {body} END $$''')
                cls.conn.execute(f'REVOKE ALL ON FUNCTION {schema}.thu_demo_constraint(uuid,uuid,uuid,uuid) FROM PUBLIC')
                cls.conn.execute(sql.SQL(f'GRANT EXECUTE ON FUNCTION {schema}.thu_demo_constraint(uuid,uuid,uuid,uuid) TO {{}}')
                                 .format(sql.Identifier(cls.cac_thong_tin['core']['user'])))
                cls.conn.execute(sql.SQL(f'GRANT USAGE ON SCHEMA {schema} TO {{}}')
                                 .format(sql.Identifier(cls.cac_thong_tin['core']['user'])))

    def setUp(self):
        self.nd = uuid4()
        self.pn, self.khac = uuid4(), uuid4()
        self.conn.execute("INSERT INTO loi.nguoi_dung(id,dang_nhap,ten,vai_tro) VALUES(%s,%s,'DEMO','XEM')",
                          (self.nd, 'demo_'+self.nd.hex))
        for pn in (self.pn, self.khac):
            self.conn.execute("INSERT INTO loi.phap_nhan(id,ma,ten) VALUES(%s,%s,'DEMO')", (pn, pn.hex))
            self.conn.execute('INSERT INTO loi.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES(%s,%s,%s)',
                              (self.nd, pn, ['core', 'crm']))
        self.conn.execute("INSERT INTO loi.mtq_admin(nguoi_dung_id,cap_boi,ly_do) VALUES(%s,%s,'DEMO')", (self.nd,self.nd))
        self.ma = self._cap(self.pn)

    def _cap(self, pn, module='core', hd=None):
        return phien.cap_phien(self.core, nguoi_dung_id=self.nd, module=module, phap_nhan_id=pn,
            dang_nhap_csdl=self.cac_thong_tin['core']['user'], pham_vi_hanh_dong=hd or [HD],
            hieu_luc_den=datetime.now(timezone.utc)+timedelta(minutes=10)).ma

    def _dat(self, co=True, version='1'):
        with self.core.transaction():
            return demo.dat_demo(self.core, ma=self.ma, phap_nhan_id=self.pn,
                                 la_demo=co, row_version=version, request_id=uuid4())

    def _context(self, pn=None, ma=None):
        mtq.dat_ngu_canh(self.core, ma=ma or self.ma, module='core', phap_nhan_id=pn or self.pn, hanh_dong=HD)

    def test_admin_cas_audit_va_chuoi_migration_chay_lai(self):
        self.assertEqual(self._dat(), {'id': str(self.pn), 'la_demo': True, 'row_version': '2'})
        with self.assertRaises(demo.LoiPhapNhanDemo) as bat:
            self._dat(False)
        self.assertEqual(bat.exception.ma, 'DEMO_CAS')
        audit = self.conn.execute("""SELECT nguoi_dung_id,phap_nhan_id,hanh_dong,doi_tuong_id
            FROM loi.nhat_ky_kiem_toan WHERE doi_tuong_id=%s""", (self.pn,)).fetchall()
        self.assertEqual(audit, [(self.nd,self.pn,HD,self.pn)])
        self.assertEqual(dc.ap_doi_cau_truc(self.conn,self.tep_sql),23)
        with self.conn.transaction():
            self.conn.execute(SQL)  # DDL 023 tu chay lai duoc, khong chi bo qua checksum.

    def test_sai_quyen_va_phien_gia_khong_doi_co(self):
        self.conn.execute('UPDATE loi.mtq_admin SET thu_hoi_luc=now(),thu_hoi_boi=%s,phien_ban_dong=phien_ban_dong+1 WHERE nguoi_dung_id=%s', (self.nd,self.nd))
        for ma in (self.ma, phien.MaBiMat('gia_'+'x'*32)):
            with self.assertRaises(demo.LoiPhapNhanDemo) as bat, self.core.transaction():
                demo.dat_demo(self.core,ma=ma,phap_nhan_id=self.pn,la_demo=True,row_version='1',request_id=uuid4())
            self.assertEqual(bat.exception.ma,'DEMO_CHI_ADMIN')

    def test_force_rls_login_that_khong_dml_hoac_goi_noi_bo(self):
        self.assertEqual(self.core.execute('SELECT current_user,session_user').fetchone(),
                         (self.cac_thong_tin['core']['user'],)*2)
        self.assertEqual(self.conn.execute("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='loi.phap_nhan'::regclass").fetchone(), (True,True))
        for cau, ts in [('UPDATE loi.phap_nhan SET la_demo=true WHERE id=%s',(self.pn,)),
                        ('SELECT loi.demo_kiem_tap_noi_bo(%s::uuid[])',([self.pn],)),
                        ('INSERT INTO loi.phap_nhan(ma,ten,la_demo) VALUES(%s,%s,true)',('gia','gia'))]:
            with self.assertRaises(g206.psycopg.errors.InsufficientPrivilege),self.core.transaction():
                self.core.execute(cau,ts)

    def test_vai_kiem_chi_doc_dinh_danh_khong_doc_bi_mat(self):
        vai = self.tien_to+'vai_kiem_demo'
        self.assertEqual(self.conn.execute('SELECT rolcanlogin,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb FROM pg_roles WHERE rolname=%s', (vai,)).fetchone(), (False,)*5)
        self.assertTrue(self.conn.execute("SELECT has_column_privilege(%s,'loi.phien_xac_thuc','phap_nhan_id','SELECT')",(vai,)).fetchone()[0])
        self.assertFalse(self.conn.execute("SELECT has_column_privilege(%s,'loi.phien_xac_thuc','ma_bam','SELECT')",(vai,)).fetchone()[0])
        with self.assertRaises(g206.psycopg.errors.InsufficientPrivilege),self.core.transaction():
            self.core.execute(g206.sql.SQL('SET LOCAL ROLE {}').format(g206.sql.Identifier(vai)))

    def test_snapshot_cu_bi_tu_choi_truoc_doi_co(self):
        with self.assertRaises(g206.psycopg.Error) as bat,self.core.transaction():
            self.core.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            self.core.execute('SELECT loi.phap_nhan_dat_demo(%s,%s,true,1,%s)',
                              (self.ma.lay_de_truyen(),self.pn,uuid4()))
        self.assertEqual(bat.exception.diag.message_primary,'DEMO_CAN_READ_COMMITTED')

    def test_pham_vi_mac_dinh_chon_ro_va_khong_lo_phap_nhan_khac(self):
        self._dat()
        with self.core.transaction():
            self._context()
            self.assertEqual(demo.pham_vi(self.core),[])
            rows = demo.pham_vi(self.core,gom_demo=True)
            self.assertEqual([(r.id,r.nhan) for r in rows],[(self.pn,'DEMO')])
        with self.core.transaction():
            self._context(self.khac,self._cap(self.khac))
            self.assertEqual([r.id for r in demo.pham_vi(self.core)],[self.khac])
        with self.core.transaction():
            self.assertEqual(demo.pham_vi(self.core,gom_demo=True),[])

    def test_co_du_lieu_tu_choi_ca_hai_chieu(self):
        for la_demo in (False,True):
            with self.subTest(la_demo=la_demo):
                if la_demo:
                    self.setUp()
                    self._dat()
                self.conn.execute("INSERT INTO loi.phap_nhan_boi_canh(phap_nhan_id,phien_ban,muc) VALUES(%s,1,0)",(self.pn,))
                with self.assertRaises(demo.LoiPhapNhanDemo) as bat:
                    self._dat(not la_demo,'2' if la_demo else '1')
                self.assertEqual(bat.exception.ma,'DEMO_DA_CO_DU_LIEU')

    def test_lien_ket_tien_mtq_va_cong_bo_bi_constraint_chan(self):
        self._dat()
        self._resolver()
        ct = uuid4()
        # Chi fixture du lieu; thao tac LIEN KET ben duoi chay login runtime.
        self.conn.execute("""INSERT INTO danh_muc.chung_tu(id,phap_nhan_id,module_nghiep_vu,loai,khoa_nguon,
            ngay_nghiep_vu,ky,ma_bam,tao_boi) VALUES(%s,%s,'crm','HOP_DONG_TEP',%s,'2026-10-01','2026-10',%s,%s)""",
            (ct,self.khac,ct.hex,'a'*64,self.nd))
        phong, gan = uuid4(),uuid4()
        self.conn.execute("INSERT INTO loi.mtq_phong(id,phap_nhan_id,ma,ten) VALUES(%s,%s,'D','D')",(phong,self.pn))
        self.conn.execute("INSERT INTO loi.mtq_gan_vai(id,nguoi_dung_id,phap_nhan_id,phong_id,vai,cap_boi,ly_do) VALUES(%s,%s,%s,%s,'CFO',%s,'D')",(gan,self.nd,self.pn,phong,self.nd))
        tl, kq = uuid4(), uuid4()
        contract = self.conn.execute("SELECT ma FROM loi.dang_ky_contract WHERE module_so_huu='crm' LIMIT 1").fetchone()[0]
        self.conn.execute("""INSERT INTO loi_tai_lieu.tai_lieu(id,phap_nhan_id,module,loai,ten,
            bang_doi_tuong,doi_tuong_id,phien_ban_contract,tao_boi)
            VALUES(%s,%s,'crm','DEMO','DEMO','doi_tuong',%s,'1',%s)""",(tl,self.khac,uuid4(),self.nd))
        self.conn.execute("""INSERT INTO loi_tai_lieu.ket_qua_xu_ly(id,phap_nhan_id,tai_lieu_id,goc_id,
            revision,bien_the,ma_contract,phien_ban_contract,module,phien_ban_module,ham,phien_ban_ham,
            trang_thai,ly_do,tao_boi) VALUES(%s,%s,%s,%s,1,'noi_dung',%s,'1','crm','1','DEMO','1','thanh_cong','DEMO',%s)""",
            (kq,self.khac,tl,kq,contract,self.nd))
        self.ma = self._cap(self.pn)  # Cap lai sau trigger doi quyen MTQ.
        for schema, a, b in [('danh_muc',ct,None),('loi',gan,self.khac),('loi_tai_lieu',kq,None)]:
            with self.subTest(schema=schema),self.assertRaises(g206.psycopg.Error) as bat,self.core.transaction():
                self._context()
                self.core.execute(f'SELECT {schema}.thu_demo_constraint(%s,%s,%s,%s)',(self.pn,a,b,self.nd))
            self.assertEqual((bat.exception.sqlstate,bat.exception.diag.message_primary),('23514','DEMO_LIEN_KET_CHEO'))
        # Hai dau cung loai van ghi duoc; FK ghep cu tiep tuc rang cung PN.
        with self.core.transaction():
            self._context(self.khac,self._cap(self.khac))
            self.core.execute('SELECT danh_muc.thu_demo_constraint(%s,%s,NULL,%s)',(self.khac,ct,self.nd))
            self.core.execute('SELECT loi_tai_lieu.thu_demo_constraint(%s,%s,NULL,%s)',(self.khac,kq,self.nd))
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi_tai_lieu.ket_qua_cong_bo WHERE ket_qua_id=%s',(kq,)).fetchone()[0],1)

    def test_mtq_resolver_da_phap_nhan_chan_ca_khi_tat(self):
        self._dat()
        self._resolver()
        obj = uuid4()
        import json
        self.conn.execute('INSERT INTO mod_crm.doi_tuong(id,tap) VALUES(%s,%s::jsonb)',
                          (obj,json.dumps([dict(pn=str(p),hop_le=True,loai='TIEP_NHAN') for p in (self.pn,self.khac)])))
        ma = self._cap(self.pn,'crm',['CRM:TIEP_NHAN:XEM'])
        with self.assertRaises(g206.psycopg.Error) as bat,self.core.transaction():
            self.core.execute('SELECT loi.mtq_quyet_dinh_phien(%s,%s,%s,%s,%s::jsonb)',
                              (ma.lay_de_truyen(),'crm',self.pn,'CRM:TIEP_NHAN:XEM',json.dumps(dict(bang='doi_tuong',id=str(obj)))))
        self.assertEqual(bat.exception.diag.message_primary,'DEMO_LIEN_KET_CHEO')

    def test_guard_isolation_lien_ket_chay_truoc_demo_trong_mtq(self):
        import json
        self._dat()
        self._resolver()
        for cheo in (False, True):
            obj = uuid4()
            tap = [dict(pn=str(p), hop_le=True, loai='TIEP_NHAN')
                   for p in ((self.pn, self.khac) if cheo else (self.pn,))]
            self.conn.execute('INSERT INTO mod_crm.doi_tuong(id,tap) VALUES(%s,%s::jsonb)',
                              (obj, json.dumps(tap)))
            for bang, hd, ma_loi in (
                ('danh_muc.lien_ket_chung_tu', 'LAP', 'LIEN_KET_CAN_READ_COMMITTED'),
                ('danh_muc.lien_ket_chung_tu', 'SUA', 'LIEN_KET_CAN_READ_COMMITTED'),
                ('danh_muc.chung_tu', 'SUA', 'LIEN_KET_CAN_READ_COMMITTED'),
                ('danh_muc.chung_tu', 'XEM', 'DEMO_CAN_READ_COMMITTED'),
            ):
                hanh_dong = 'CRM:TIEP_NHAN:'+hd
                ma = self._cap(self.pn, 'crm', [hanh_dong])
                for isolation in ('REPEATABLE READ', 'SERIALIZABLE'):
                    with self.subTest(cheo=cheo, bang=bang, hd=hd, isolation=isolation):
                        with self.assertRaises(dm.LoiDanhMuc) as bat, self.core.transaction():
                            self.core.execute('SET TRANSACTION ISOLATION LEVEL '+isolation)
                            dm._goi(self.core,
                                'SELECT loi.mtq_quyet_dinh_phien(%s,%s,%s,%s,%s::jsonb)',
                                (ma.lay_de_truyen(), 'crm', self.pn, hanh_dong,
                                 json.dumps(dict(bang=bang, id=str(obj)))))
                        self.assertEqual(bat.exception.ma, ma_loi)

    def test_khoa_doi_co_cho_giao_dich_ghi_du_lieu(self):
        # Xac nhan hai duong dung cung khoa, khong can thread/doi vo han.
        with self.conn.transaction():
            self.conn.execute("INSERT INTO loi.phap_nhan_boi_canh(phap_nhan_id,phien_ban,muc) VALUES(%s,1,0)",(self.pn,))
            with self.assertRaises(g206.psycopg.errors.LockNotAvailable),self.core.transaction():
                self.core.execute("SET LOCAL lock_timeout='150ms'")
                self.core.execute('SELECT loi.phap_nhan_dat_demo(%s,%s,true,1,%s)',
                                  (self.ma.lay_de_truyen(),self.pn,uuid4()))
        with self.assertRaises(demo.LoiPhapNhanDemo) as bat:
            self._dat()
        self.assertEqual(bat.exception.ma,'DEMO_DA_CO_DU_LIEU')


if __name__ == '__main__':
    unittest.main()
