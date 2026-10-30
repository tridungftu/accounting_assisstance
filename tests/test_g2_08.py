"""G2-08: thuần/mock và PG16, login thật + phiên; không chạy dịch vụ.

Chỉ dùng KHO_PG_DSN_TEST localhost, tự tạo kho_test_*, không DROP/cleanup
dữ liệu. Admin chỉ provisioning/đối chiếu lịch sử; nghiệp vụ chạy Core/module.
008 thử độc lập trên nền handoff 001..006, không chứng nhận gộp G2-07.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import re
import secrets
import sys
from threading import Barrier
import traceback
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import cong_tac as ct, doi_cau_truc as dc, phien

try:
    from .test_g2_01 import _kiem_dich_test, psycopg
except ImportError:
    from test_g2_01 import _kiem_dich_test, psycopg

if psycopg is not None:
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict

ADMIN_DSN = os.environ.get('KHO_PG_DSN_TEST')
SQL_PATH = dc.THU_MUC_SQL / '008_cong_tac.sql'
SQL_CONG_TAC = SQL_PATH.read_text(encoding='utf-8')
XEM = 'CORE:MODULE:XEM'
SUA = 'CORE:MODULE:SUA'
DOC_MODULE = 'CRM:TIEP_NHAN:XEM'


class CongTacThuanTest(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.ts = dict(ma=phien.MaBiMat('CANARY_PHIEN'), module='crm', phap_nhan_id=uuid4())
        self.payload = dict(row_version='1', che_do='THU', nguoi_thu_ids=[str(uuid4())])

    def test_bind_patch_va_khong_tu_commit(self):
        ct.doi_che_do(self.conn, **self.ts, payload=self.payload, request_id=uuid4())
        cau, ts = self.conn.execute.call_args.args
        self.assertIn('loi.module_doi_che_do', cau)
        self.assertNotIn('CANARY', cau)
        self.assertEqual(ts[:5], ('CANARY_PHIEN','crm',self.ts['phap_nhan_id'],'THU',1))
        self.assertEqual(str(ts[5][0]), self.payload['nguoi_thu_ids'][0])
        for ten in ('commit','rollback','transaction'):
            getattr(self.conn, ten).assert_not_called()

    def test_payload_cam_actor_va_thieu_truong(self):
        for doi in ({'actor': 'GIA'}, {'phap_nhan_id': str(uuid4())}, {'expected_revision': 1}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                ct.doi_che_do(self.conn, **self.ts, payload={**self.payload, **doi}, request_id=uuid4())
        with self.assertRaises(ValueError):
            ct.doi_che_do(self.conn, **self.ts, payload={'che_do':'TAT'}, request_id=uuid4())
        self.conn.execute.assert_not_called()

    def test_row_version_chuoi_bigint(self):
        for ban in (0,1,True,None,'0','01','-1','1.0',' 1','9223372036854775808'):
            with self.subTest(ban=ban), self.assertRaises(ValueError):
                ct.doi_che_do(self.conn, **self.ts, payload={**self.payload,'row_version':ban}, request_id=uuid4())
        self.conn.execute.assert_not_called()

    def test_danh_sach_nguoi_thu_va_che_do(self):
        n = self.payload['nguoi_thu_ids'][0]
        for doi in ({'nguoi_thu_ids':[n,n]}, {'nguoi_thu_ids':[None]},
                    {'nguoi_thu_ids':[n]*1001}, {'nguoi_thu_ids':()}, {'che_do':'TU_BAT'}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                ct.doi_che_do(self.conn, **self.ts, payload={**self.payload,**doi}, request_id=uuid4())
        self.conn.execute.assert_not_called()

    def test_phien_module_hanh_dong_va_viec_sai(self):
        ts = {**self.ts,'hanh_dong':DOC_MODULE}
        for doi in ({'ma':'THO'}, {'module':'crm.sql'}, {'module':'core'}, {'module_phien':'m2'},
                    {'hanh_dong':XEM}, {'viec_id':uuid4()}, {'the_he':1},
                    {'viec_id':uuid4(),'the_he':True}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                ct.trang_thai(self.conn, **{**ts,**doi})
        self.conn.execute.assert_not_called()

    def test_cua_doc_core_va_module(self):
        ct.che_do(self.conn, **self.ts)
        self.assertIn('loi.module_che_do', self.conn.execute.call_args.args[0])
        ct.trang_thai(self.conn, **self.ts, hanh_dong=XEM, module_phien='core')
        self.assertEqual(self.conn.execute.call_args.args[1][3:], (XEM,'core',None,None))
        viec = uuid4()
        ct.trang_thai(self.conn, **self.ts, hanh_dong=DOC_MODULE, viec_id=viec, the_he=2)
        self.assertEqual(self.conn.execute.call_args.args[1][3:], (DOC_MODULE,'crm',viec,2))
        ct.trang_thai_cho(self.conn, **self.ts, hanh_dong='M2:HOA_DON:XEM', module_phien='m2')
        self.assertEqual(self.conn.execute.call_args.args[1][3:5], ('M2:HOA_DON:XEM','m2'))

    def _co(self, **co):
        self.conn.execute.return_value.fetchone.return_value = (co,)

    def test_tat_giu_xem_lich_su_chan_ghi_va_cho_nguon(self):
        self._co(che_do='TAT',cho_xem=True,cho_ghi=False,cong_bo_chinh_thuc=False)
        ts = {**self.ts,'hanh_dong':DOC_MODULE}
        self.assertTrue(ct.kiem_module(self.conn,can='xem',**ts)['cho_xem'])
        with self.assertRaises(ct.LoiCongTac) as bat:
            ct.kiem_module(self.conn,can='ghi',**ts)
        self.assertEqual(bat.exception.ma,'MODULE_TAT')
        self.assertEqual(ct.trang_thai_cho(self.conn,**ts)['ma'],'CHO_MODULE')

    def test_thu_chi_nguoi_thu_va_cam_xuat_cong_bo(self):
        ts = {**self.ts,'hanh_dong':DOC_MODULE}
        self._co(che_do='THU',cho_xem=False,cho_ghi=False)
        with self.assertRaises(ct.LoiCongTac) as bat:
            ct.kiem_module(self.conn,can='ghi',**ts)
        self.assertEqual(bat.exception.ma,'MODULE_CHI_NGUOI_THU')
        self._co(che_do='THU',cho_xem=True,cho_ghi=True,cho_xuat_ngoai=False,cong_bo_chinh_thuc=False)
        self.assertTrue(ct.kiem_module(self.conn,can='ghi',**ts)['cho_ghi'])
        for can,loi in (('xuat_ngoai','MODULE_THU_KHONG_XUAT'),('cong_bo','MODULE_THU_KHONG_CONG_BO')):
            with self.subTest(can=can), self.assertRaises(ct.LoiCongTac) as bat:
                ct.kiem_module(self.conn,can=can,**ts)
            self.assertEqual(bat.exception.ma,loi)

    def test_van_hanh_cho_cong_bo(self):
        self._co(che_do='VAN_HANH',cho_xem=True,cho_ghi=True,cho_xuat_ngoai=True,cong_bo_chinh_thuc=True)
        ts = {**self.ts,'hanh_dong':DOC_MODULE}
        self.assertIsNone(ct.trang_thai_cho(self.conn,**ts))
        self.assertTrue(ct.kiem_module(self.conn,can='cong_bo',**ts)['cong_bo_chinh_thuc'])

    def test_loi_driver_khong_lo_ma_phien(self):
        loi = RuntimeError('CANARY_PHIEN postgresql://CANARY:MAT_KHAU@localhost')
        loi.diag = MagicMock(message_primary='MODULE_REVISION')
        self.conn.execute.side_effect = loi
        with self.assertRaises(ct.LoiCongTac) as bat:
            ct.che_do(self.conn,**self.ts)
        self.assertEqual(bat.exception.ma,'MODULE_REVISION')
        self.assertIsNone(bat.exception.__context__)
        self.assertIsNone(bat.exception.__cause__)
        self.assertNotIn('CANARY',''.join(traceback.format_exception(bat.exception)))

    def test_dollar_quote_va_bien_gioi_sql(self):
        moc = re.findall(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', SQL_CONG_TAC)
        self.assertEqual((moc[0],moc[-1]),('$$','$$'))
        self.assertTrue(all(a == b for a,b in zip(moc[1:-1:2],moc[2:-1:2])))
        self.assertEqual(len(moc)%2,0)
        self.assertNotRegex(SQL_CONG_TAC,r'(?i)\b(?:UPDATE|DELETE FROM)\s+loi\.module_')
        self.assertNotRegex(SQL_CONG_TAC,r'(?i)\bDROP\s+(?:TABLE|FUNCTION|DATABASE|ROLE)')
        self.assertNotRegex(SQL_CONG_TAC,r'(?i)(?:FROM|JOIN|REFERENCES)\s+(?:mod_|master\.|nhat_ky\.)')


@unittest.skipUnless(psycopg is not None and ADMIN_DSN,
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class CongTacPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tt = _kiem_dich_test(conninfo_to_dict(ADMIN_DSN))
        cls.admin = psycopg.connect(**tt,autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        if cls.admin.info.server_version < 160000 or not cls.admin.execute(
            'SELECT rolsuper FROM pg_roles WHERE rolname=current_user').fetchone()[0]:
            raise RuntimeError('Cần lead provisioning admin PG16+')
        ma = uuid4().hex[:8]
        cls.db = 'kho_test_g2_08_' + ma
        cls.tien_to = 'ktt_g208_' + ma + '_'
        cls.admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(cls.db)))
        cls.conn = psycopg.connect(**{**tt,'dbname':cls.db},autocommit=True)
        cls.addClassCleanup(cls.conn.close)
        cls.conn.execute('SELECT set_config(%s,%s,false)',('kho_tri_thuc.tien_to_vai',cls.tien_to))
        dc.ap_doi_cau_truc(cls.conn,sorted(dc.THU_MUC_SQL.glob('00[1-6]_*.sql')))
        # DDL doc lap tren nen handoff; khong chen migration 007 gia vao so.
        with cls.conn.transaction():
            cls.conn.execute(SQL_CONG_TAC)
        cls.thong_tin = {}
        for loai,hau_to in (('core','dang_nhap_loi'),('cai_dat','dang_nhap_cai_dat'),
                           ('module','dang_nhap_mod_crm'),('module_m2','dang_nhap_mod_m2')):
            login = cls.tien_to + hau_to
            mat_khau = secrets.token_urlsafe(32)
            if loai.startswith('module'):
                vai_chay = cls.tien_to + ('vai_chay_mod_crm' if loai == 'module' else 'vai_chay_mod_m2')
                cls.conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN INHERIT NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB').format(sql.Identifier(vai_chay)))
                cls.conn.execute(sql.SQL('CREATE ROLE {} LOGIN INHERIT NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB').format(sql.Identifier(login)))
                cls.conn.execute(sql.SQL('GRANT {} TO {} WITH INHERIT TRUE, SET FALSE, ADMIN FALSE').format(sql.Identifier(vai_chay),sql.Identifier(login)))
                cls.conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier(cls.db),sql.Identifier(login)))
                cls.conn.execute(sql.SQL('GRANT USAGE ON SCHEMA loi TO {}').format(sql.Identifier(vai_chay)))
                cls.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION loi.module_trang_thai(text,text,uuid,text,text,uuid,bigint) TO {}').format(sql.Identifier(vai_chay)))
            cls.conn.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(sql.Identifier(login),sql.Literal(mat_khau)))
            for khoa in ('log_parameter_max_length','log_parameter_max_length_on_error'):
                cls.conn.execute(sql.SQL('ALTER ROLE {} SET {}=0').format(sql.Identifier(login),sql.Identifier(khoa)))
            cls.thong_tin[loai] = {**tt,'dbname':cls.db,'user':login,'password':mat_khau}
            kn = psycopg.connect(**cls.thong_tin[loai],autocommit=True)
            cls.addClassCleanup(kn.close)
            setattr(cls,loai,kn)
        cls.cai_dat.execute("SELECT loi.ghi_dang_ky('module',%s::jsonb)",('{"ma":"crm","ten":"CRM DEMO"}',))
        cls.cai_dat.execute("SELECT loi.ghi_dang_ky('phien_ban_module',%s::jsonb)",
            ('{"module":"crm","so_phien_ban":"1","ma_bam_goi":"'+'a'*64+'","tuong_thich":{}}',))
        cls.cai_dat.execute("SELECT loi.ghi_dang_ky('trang_thai_module',%s::jsonb)",
            ('{"module":"crm","so_phien_ban":"1","trang_thai":"da_cai"}',))
        cls.cai_dat.execute("SELECT loi.ghi_dang_ky('module',%s::jsonb)",('{"ma":"m2","ten":"M2 DEMO"}',))

    def setUp(self):
        self.pn,self.pn_khac = uuid4(),uuid4()
        self.admin_id,self.thu_id,self.khac_id = uuid4(),uuid4(),uuid4()
        for pn in (self.pn,self.pn_khac):
            self.conn.execute("INSERT INTO loi.phap_nhan(id,ma,ten) VALUES (%s,%s,'DEMO')",(pn,pn.hex))
        for nd in (self.admin_id,self.thu_id,self.khac_id):
            self.conn.execute("INSERT INTO loi.nguoi_dung(id,dang_nhap,ten,vai_tro) VALUES (%s,%s,'DEMO','CFO')",(nd,'demo_'+nd.hex))
            for pn in (self.pn,self.pn_khac):
                self.conn.execute('INSERT INTO loi.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,%s)',(nd,pn,['core','crm','m2']))
        self.conn.execute("INSERT INTO loi.mtq_admin(nguoi_dung_id,cap_boi,ly_do) VALUES (%s,%s,'DEMO')",(self.admin_id,self.admin_id))
        self.ma = self._cap(self.admin_id)
        self.ma_khac = self._cap(self.khac_id)

    def _cap(self, nd, module='core', pn=None, dich='core', hanh_dong=None):
        hd = hanh_dong or ([XEM,SUA] if module == 'core' else [DOC_MODULE])
        goc = phien.cap_phien(self.core,nguoi_dung_id=nd,module=module,phap_nhan_id=pn or self.pn,
            dang_nhap_csdl=self.thong_tin['core']['user'],pham_vi_hanh_dong=hd,
            hieu_luc_den=datetime.now(timezone.utc)+timedelta(minutes=5))
        if dich == 'core':
            return goc.ma
        return phien.cap_phien(self.core,nguoi_dung_id=nd,module=module,phap_nhan_id=pn or self.pn,
            dang_nhap_csdl=self.thong_tin[dich]['user'],pham_vi_hanh_dong=hd,loai='UY_NHIEM_PHIEN',ma_goc=goc.ma,
            hieu_luc_den=datetime.now(timezone.utc)+timedelta(minutes=4)).ma

    def _doi(self, cd='THU', ban='1', ds=None, ma=None, ket_noi=None):
        return ct.doi_che_do(ket_noi or self.core,ma=ma or self.ma,module='crm',phap_nhan_id=self.pn,
            payload=dict(row_version=ban,che_do=cd,nguoi_thu_ids=[] if ds is None else ds),request_id=uuid4())

    def _doc(self, nd=None, ma=None, ket_noi=None, **doi):
        return ct.trang_thai(ket_noi or self.core,ma=ma or self._cap(nd or self.thu_id,module='crm'),
            module='crm',phap_nhan_id=self.pn,hanh_dong=DOC_MODULE,**doi)

    def test_admin_that_duoc_cfo_khong_admin_bi_chan(self):
        self.assertEqual(self.core.execute('SELECT current_user,session_user').fetchone(),(self.thong_tin['core']['user'],)*2)
        self.assertEqual(self._doi()['row_version'],'2')
        with self.assertRaises(ct.LoiCongTac) as bat:
            self._doi(ban='2',ma=self.ma_khac)
        self.assertEqual(bat.exception.ma,'MODULE_CHI_ADMIN')
        with self.assertRaises(ct.LoiCongTac):
            ct.che_do(self.core,ma=self.ma_khac,module='crm',phap_nhan_id=self.pn)

    def test_cas_lech_khong_them_lich_su_hoac_audit(self):
        self._doi()
        n = self.conn.execute('SELECT count(*) FROM loi.nhat_ky_kiem_toan WHERE phap_nhan_id=%s',(self.pn,)).fetchone()[0]
        with self.assertRaises(ct.LoiCongTac) as bat:
            self._doi('VAN_HANH')
        self.assertEqual(bat.exception.ma,'MODULE_REVISION')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.module_cong_tac WHERE phap_nhan_id=%s',(self.pn,)).fetchone()[0],2)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.nhat_ky_kiem_toan WHERE phap_nhan_id=%s',(self.pn,)).fetchone()[0],n)

    def test_thu_chi_danh_sach_ke_ca_admin_khong_tu_duoc_thu(self):
        self._doi(ds=[str(self.thu_id)])
        self.assertTrue(self._doc()['cho_ghi'])
        for nd in (self.khac_id,self.admin_id):
            self.assertFalse(self._doc(nd)['cho_ghi'])
        co = self._doc()
        self.assertFalse(co['cho_xuat_ngoai'])
        self.assertFalse(co['cong_bo_chinh_thuc'])
        self._doi(ban='2',ds=[])
        self.assertFalse(self._doc()['cho_ghi'])
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.module_nguoi_thu WHERE phap_nhan_id=%s',(self.pn,)).fetchone()[0],1)

    def test_tat_giu_lich_su_khong_tu_bat(self):
        self.assertEqual(ct.che_do(self.core,ma=self.ma,module='crm',phap_nhan_id=self.pn)['che_do'],'TAT')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.module_cong_tac WHERE phap_nhan_id=%s',(self.pn,)).fetchone()[0],0)
        self._doi('VAN_HANH')
        self._doi('TAT','2')
        for _ in range(3):
            co = self._doc()
            self.assertEqual((co['che_do'],co['cho_xem'],co['cho_ghi']),('TAT',True,False))
        self.assertEqual(self.conn.execute('SELECT che_do FROM loi.module_cong_tac WHERE phap_nhan_id=%s ORDER BY phien_ban_dong',(self.pn,)).fetchall(),[('TAT',),('VAN_HANH',),('TAT',)])

    def test_audit_va_snapshot_rollback_cung_giao_dich(self):
        with self.assertRaisesRegex(RuntimeError,'DEMO rollback'):
            with self.core.transaction():
                self._doi()
                raise RuntimeError('DEMO rollback')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.module_cong_tac WHERE phap_nhan_id=%s',(self.pn,)).fetchone()[0],0)
        self._doi()
        dong = self.conn.execute('SELECT nguoi_dung_id,module,hanh_dong,ket_luan FROM loi.nhat_ky_kiem_toan WHERE phap_nhan_id=%s',(self.pn,)).fetchall()
        self.assertEqual(dong,[(self.admin_id,'core',SUA,'DAT')])

    def test_runtime_khong_ghi_thang_va_lich_su_bat_bien(self):
        self._doi()
        for kn in (self.core,self.module,self.cai_dat):
            for bang in ('module_cong_tac','module_nguoi_thu'):
                for lenh in (f'INSERT INTO loi.{bang} DEFAULT VALUES',f'UPDATE loi.{bang} SET phap_nhan_id=phap_nhan_id',f'DELETE FROM loi.{bang}',f'TRUNCATE loi.{bang}'):
                    with self.subTest(lenh=lenh), self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        kn.execute(lenh)
        for bang in ('module_cong_tac','module_nguoi_thu'):
            with self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
                self.conn.execute(f'UPDATE loi.{bang} SET phap_nhan_id=phap_nhan_id')
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.module.execute('SELECT loi.module_doi_che_do(%s,%s,%s,%s,%s,%s::uuid[],%s)',
                (self.ma.lay_de_truyen(),'crm',self.pn,'TAT',2,[],uuid4()))

    def test_nguoi_thu_sai_phap_nhan_hoac_ngung_hoat_dong(self):
        nd = uuid4()
        self.conn.execute("INSERT INTO loi.nguoi_dung(id,dang_nhap,ten,vai_tro) VALUES (%s,%s,'DEMO','XEM')",(nd,nd.hex))
        self.conn.execute('INSERT INTO loi.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,%s)',(nd,self.pn_khac,['crm']))
        for nguoi in (nd,uuid4()):
            with self.assertRaises(ct.LoiCongTac) as bat:
                self._doi(ds=[str(nguoi)])
            self.assertEqual(bat.exception.ma,'MODULE_NGUOI_THU')
        self._doi(ds=[str(self.thu_id)])
        ma = self._cap(self.thu_id,module='crm')
        self.conn.execute("UPDATE loi.nguoi_dung SET trang_thai='KHOA' WHERE id=%s",(self.thu_id,))
        with self.assertRaises(ct.LoiCongTac):
            self._doc(ma=ma)

    def test_phien_gia_sai_pn_hanh_dong_login_va_thu_hoi(self):
        for ma in (phien.MaBiMat('GIA'),self._cap(self.admin_id,pn=self.pn_khac),
                   self._cap(self.admin_id,hanh_dong=[XEM])):
            with self.assertRaises(ct.LoiCongTac):
                self._doi(ma=ma)
        self._doi(ds=[str(self.thu_id)])
        ma = self._cap(self.thu_id,module='crm',dich='module')
        self.assertTrue(self._doc(ma=ma,ket_noi=self.module)['cho_ghi'])
        with self.assertRaises(ct.LoiCongTac):
            self._doc(ma=ma)
        phien.thu_hoi_phien(self.core,ma=ma)
        with self.assertRaises(ct.LoiCongTac):
            self._doc(ma=ma,ket_noi=self.module)

    def test_thu_hoi_admin_chan_phien_cu_va_moi(self):
        self.conn.execute('UPDATE loi.mtq_admin SET thu_hoi_boi=%s,thu_hoi_luc=clock_timestamp(),phien_ban_dong=phien_ban_dong+1 WHERE nguoi_dung_id=%s',(self.admin_id,self.admin_id))
        for ma in (self.ma,self._cap(self.admin_id)):
            with self.assertRaises(ct.LoiCongTac):
                self._doi(ma=ma)

    def test_hai_login_that_cas_chi_mot_thanh_cong(self):
        bat_dau = Barrier(2)
        def doi(cd):
            with psycopg.connect(**self.thong_tin['core'],autocommit=True) as kn:
                kn.execute("SET statement_timeout='10s'")
                bat_dau.wait(timeout=10)
                try:
                    return self._doi(cd,ket_noi=kn)['row_version']
                except ct.LoiCongTac as exc:
                    return exc.ma
        with ThreadPoolExecutor(max_workers=2) as pool:
            kq = list(pool.map(doi,['THU','VAN_HANH']))
        self.assertCountEqual(kq,['2','MODULE_REVISION'])

    def test_ben_nhan_doc_nguon_bang_phien_cua_minh(self):
        self._doi('VAN_HANH')
        ma = self._cap(self.khac_id,module='m2',dich='module_m2',hanh_dong=['M2:HOA_DON:XEM'])
        ts = dict(ma=ma,module='crm',phap_nhan_id=self.pn,hanh_dong='M2:HOA_DON:XEM',module_phien='m2')
        self.assertIsNone(ct.trang_thai_cho(self.module_m2,**ts))
        self._doi('TAT','2')
        self.assertEqual(ct.trang_thai_cho(self.module_m2,**ts)['ma'],'CHO_MODULE')
        with self.assertRaises(ct.LoiCongTac):
            ct.trang_thai(self.module_m2,**{**ts,'phap_nhan_id':self.pn_khac})

    def test_van_hanh_khong_cho_module_chi_dang_ky(self):
        with self.assertRaises(ct.LoiCongTac) as bat:
            ct.doi_che_do(self.core,ma=self.ma,module='m2',phap_nhan_id=self.pn,
                payload=dict(row_version='1',che_do='VAN_HANH',nguoi_thu_ids=[]),request_id=uuid4())
        self.assertEqual(bat.exception.ma,'MODULE_CHUA_DU_DIEU_KIEN_GO_LIVE')

    def test_ap_lai_ddl_giu_cong_tac_da_tat(self):
        self._doi('TAT')
        with self.conn.transaction():
            self.conn.execute(SQL_CONG_TAC)
        self.assertEqual(ct.che_do(self.core,ma=self.ma,module='crm',phap_nhan_id=self.pn),
                         dict(row_version='2',che_do='TAT',nguoi_thu_ids=[]))


if __name__ == '__main__':
    unittest.main()
