"""G2-06: mock và PG16, ca nghiệp vụ chạy dưới LOGIN Core thật + phiên G2-03.

Chỉ KHO_PG_DSN_TEST, tự tạo kho_test_* / role có tiền tố; không DROP, không
khởi động dịch vụ. Admin chỉ provisioning SQL/fixture, không đóng giả runtime.
Contract/resolver trong bài PG là fixture DEMO, không kích hoạt nghiệp vụ thật.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import secrets
import sys
import traceback
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import doi_cau_truc as dc, mtq, phien

try:
    from .test_g2_01 import _kiem_dich_test, psycopg
    from . import test_g2_05 as g205
except ImportError:
    from test_g2_01 import _kiem_dich_test, psycopg
    import test_g2_05 as g205

if psycopg is not None:
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict

ADMIN_DSN = os.environ.get('KHO_PG_DSN_TEST')
SQL_PATH = dc.THU_MUC_SQL / '006_mtq.sql'
SQL_MTQ = SQL_PATH.read_text(encoding='utf-8')
TEP_SQL = sorted(dc.THU_MUC_SQL.glob('[0-9][0-9][0-9]_*.sql'))[:6]
XEM = 'CRM:TIEP_NHAN:XEM'
DUYET = 'CRM:TIEP_NHAN:DUYET'
LAP = 'CORE:DANH_TINH:LAP'
CAC_BANG = ('mtq_phong','mtq_admin','mtq_danh_muc_hanh_dong','mtq_phien_ban',
            'mtq_dong','mtq_o','mtq_gan_vai','mtq_pham_vi','mtq_kich_hoat','mtq_thay_doi','mtq_tu_choi')


class MTQThuanTest(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.conn.execute.return_value.fetchone.return_value = ({'ket_luan': 'CHO', 'cho_phep': False},)
        self.ts = dict(ma=phien.MaBiMat('CANARY_PHIEN'), module='crm', phap_nhan_id=uuid4(),
                       hanh_dong=XEM, doi_tuong={'bang': 'doi_tuong', 'id': uuid4()})

    def test_bind_phien_tham_chieu_va_khong_commit(self):
        self.assertEqual(mtq.quyet_dinh_phien(self.conn, **self.ts)['ket_luan'], 'CHO')
        cau, ts = self.conn.execute.call_args.args
        self.assertNotIn('CANARY_PHIEN', cau)
        self.assertEqual(ts[0], 'CANARY_PHIEN')
        self.assertEqual(json.loads(ts[4])['id'], str(self.ts['doi_tuong']['id']))
        self.assertEqual(ts[6:], ([], None, None))
        for ten in ('commit','rollback','transaction'):
            getattr(self.conn, ten).assert_not_called()

    def test_khong_nhan_actor_tien_phap_nhan_va_ten_ham(self):
        for khoa in ('actor','nguoi_dung_id','phap_nhan_id','so_tien_vnd','cho_phep','ten_ham'):
            with self.subTest(khoa=khoa), self.assertRaises(ValueError):
                mtq.quyet_dinh_phien(self.conn, **{**self.ts, 'doi_tuong': {**self.ts['doi_tuong'], khoa: 'GIA'}})
        self.conn.execute.assert_not_called()

    def test_module_hanh_dong_ma_va_the_he_sai(self):
        for doi in ({'ma': 'THO'}, {'module': 'crm.foo'}, {'hanh_dong': 'M2:HOA_DON:XEM'},
                    {'viec_id': uuid4()}, {'the_he': 1}, {'viec_id': uuid4(), 'the_he': True},
                    {'cac_ma': ['THO']}, {'phien_ban_contract': ''}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                mtq.quyet_dinh_phien(self.conn, **{**self.ts, **doi})
        self.conn.execute.assert_not_called()

    def test_doc_va_ghi_tu_choi_dung_cua(self):
        self.conn.execute.return_value.fetchone.return_value = (False,)
        self.assertFalse(mtq.duoc_doc(self.conn, **self.ts))
        self.assertIn('loi.mtq_duoc_doc', self.conn.execute.call_args.args[0])
        req = uuid4()
        mtq.ghi_tu_choi_phien(self.conn, request_id=req, **self.ts)
        self.assertEqual(self.conn.execute.call_args.args[1][0], req)

    def test_nhieu_phap_nhan_bind_tung_ma(self):
        mtq.quyet_dinh_phien(self.conn, **self.ts, cac_ma=[phien.MaBiMat('CANARY_B')])
        self.assertEqual(self.conn.execute.call_args.args[1][6], ['CANARY_B'])

    def test_ngu_canh_xac_minh_truoc_set_local_va_xoa_viec_cu(self):
        mtq.dat_ngu_canh(self.conn, **{k: v for k, v in self.ts.items() if k != 'doi_tuong'})
        self.assertEqual(self.conn.execute.call_count, 2)
        self.assertIn('loi.xac_minh_phien', self.conn.execute.call_args_list[0].args[0])
        cau, ts = self.conn.execute.call_args.args
        self.assertEqual(cau.count('true'), 6)
        self.assertNotIn('CANARY_PHIEN', cau)
        self.assertEqual(ts[-2:], ('',''))

    def test_ngu_canh_sai_khong_dat(self):
        self.conn.execute.return_value.fetchone.return_value = (False,)
        with self.assertRaises(mtq.LoiMTQ):
            mtq.dat_ngu_canh(self.conn, **{k: v for k, v in self.ts.items() if k != 'doi_tuong'})
        self.assertEqual(self.conn.execute.call_count, 1)

    def test_loi_driver_khong_lo_bi_mat(self):
        loi = RuntimeError('CANARY_PHIEN postgresql://CANARY:BI_MAT@localhost/kho_test_demo')
        loi.sqlstate = '42501'
        self.conn.execute.side_effect = loi
        with self.assertRaises(mtq.LoiMTQ) as bat:
            mtq.quyet_dinh_phien(self.conn, **self.ts)
        self.assertEqual(bat.exception.ma, '42501')
        self.assertIsNone(bat.exception.__context__)
        self.assertIsNone(bat.exception.__cause__)
        self.assertNotIn('CANARY', ''.join(traceback.format_exception(bat.exception)))

    def test_ghi_danh_tinh_chi_qua_ham_va_khong_nhan_actor(self):
        nd = uuid4()
        mtq.tao_danh_tinh(self.conn, ma=self.ts['ma'], phap_nhan_id=self.ts['phap_nhan_id'],
                         loai='thanh_vien', du_lieu={'nguoi_dung_id': nd, 'module': ['crm']})
        cau, ts = self.conn.execute.call_args.args
        self.assertIn('loi.mtq_tao_danh_tinh', cau)
        self.assertEqual(json.loads(ts[3])['nguoi_dung_id'], str(nd))
        for du_lieu in ({'actor': nd}, {'phap_nhan_id': nd}, {'sql': 'SELECT 1'}, {'module': [None]}):
            with self.subTest(du_lieu=du_lieu), self.assertRaises(ValueError):
                mtq.tao_danh_tinh(self.conn, ma=self.ts['ma'], phap_nhan_id=self.ts['phap_nhan_id'],
                                 loai='thanh_vien', du_lieu=du_lieu)

    def test_sql_khong_phu_thuoc_bang_module_va_dollar_quote_dung(self):
        self.assertNotRegex(SQL_MTQ, r'(?i)(?:FROM|JOIN|REFERENCES|INSERT INTO)\s+(?:mod_|master\.|nhat_ky\.)')
        self.assertNotIn('ktt_duoc', SQL_MTQ)
        self.assertNotIn('current_user', SQL_MTQ)
        self.assertNotRegex(SQL_MTQ, r'(?i)\bDROP\s+(TABLE|FUNCTION|DATABASE|ROLE|POLICY)\b')
        self.assertEqual(SQL_MTQ.count('CREATE TABLE IF NOT EXISTS'), 11)
        moc = re.findall(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', SQL_MTQ)
        self.assertEqual((moc[0],moc[-1]), ('$$','$$'))
        self.assertEqual(len(moc) % 2, 0)
        self.assertTrue(all(a == b for a,b in zip(moc[1:-1:2],moc[2:-1:2])))


@unittest.skipUnless(psycopg is not None and ADMIN_DSN,
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class MTQPostgresTest(unittest.TestCase):
    _ghi = g205.DangKyPostgresTest._ghi
    _contract = g205.DangKyPostgresTest._contract
    _trang_thai = g205.DangKyPostgresTest._trang_thai

    @classmethod
    def setUpClass(cls):
        tt = _kiem_dich_test(conninfo_to_dict(ADMIN_DSN))
        cls.admin = psycopg.connect(**tt, autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        if cls.admin.info.server_version < 160000 or not cls.admin.execute(
            'SELECT rolsuper FROM pg_roles WHERE rolname=current_user').fetchone()[0]:
            raise RuntimeError('Cần lead provisioning admin PG16+')
        ma = uuid4().hex[:8]
        cls.db = 'kho_test_g2_06_' + ma
        cls.tien_to = 'ktt_g206_' + ma + '_'
        cls.admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(cls.db)))
        cls.conn = psycopg.connect(**{**tt, 'dbname': cls.db}, autocommit=True)
        cls.addClassCleanup(cls.conn.close)
        cls.conn.execute('SELECT set_config(%s,%s,false)', ('kho_tri_thuc.tien_to_vai',cls.tien_to))
        dc.ap_doi_cau_truc(cls.conn, TEP_SQL)
        cls.cac_thong_tin = {}
        for ten in ('core','cai_dat'):
            login = cls.tien_to + ('dang_nhap_loi' if ten == 'core' else 'dang_nhap_cai_dat')
            mat_khau = secrets.token_urlsafe(32)
            cls.conn.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(sql.Identifier(login),sql.Literal(mat_khau)))
            for khoa in ('log_parameter_max_length','log_parameter_max_length_on_error'):
                cls.conn.execute(sql.SQL('ALTER ROLE {} SET {}=0').format(sql.Identifier(login),sql.Identifier(khoa)))
            cls.cac_thong_tin[ten] = {**tt,'dbname':cls.db,'user':login,'password':mat_khau}
            kn = psycopg.connect(**cls.cac_thong_tin[ten],autocommit=True)
            cls.addClassCleanup(kn.close)
            setattr(cls,ten,kn)

    def _resolver(self):
        # Moi CSDL chi tao mot resolver. Toan bo doan nay la provisioning fixture.
        if self.conn.execute("SELECT to_regclass('mod_crm.doi_tuong')").fetchone()[0]:
            return
        self._ghi('module', ma='crm', ten='CRM DEMO')
        self._ghi('phien_ban_module', module='crm', so_phien_ban='1', ma_bam_goi='a'*64, tuong_thich={})
        self._ghi('trang_thai_module', module='crm', so_phien_ban='1', trang_thai='da_cai')
        ct = self._contract('crm', kich_hoat=True)
        chu = self.tien_to + 'vai_doi_cau_truc_mod_crm'
        self.conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOSUPERUSER NOBYPASSRLS').format(sql.Identifier(chu)))
        self.conn.execute(sql.SQL('CREATE SCHEMA mod_crm AUTHORIZATION {}').format(sql.Identifier(chu)))
        with self.conn.transaction():
            self.conn.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(chu)))
            self.conn.execute('CREATE TABLE mod_crm.doi_tuong(id uuid PRIMARY KEY,tap jsonb NOT NULL)')
            self.conn.execute('''CREATE FUNCTION mod_crm.resolver_demo(text,uuid,text,jsonb,uuid,bigint)
                RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER
                SET search_path = pg_catalog, pg_temp AS $$
                SELECT tap FROM mod_crm.doi_tuong WHERE id = ($4->>'id')::uuid $$''')
            self.conn.execute('REVOKE ALL ON FUNCTION mod_crm.resolver_demo(text,uuid,text,jsonb,uuid,bigint) FROM PUBLIC')
            for vai in (self.tien_to+'vai_doi_cau_truc_loi',self.cac_thong_tin['core']['user']):
                self.conn.execute(sql.SQL('GRANT USAGE ON SCHEMA mod_crm TO {}').format(sql.Identifier(vai)))
                self.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION mod_crm.resolver_demo(text,uuid,text,jsonb,uuid,bigint) TO {}').format(sql.Identifier(vai)))
        self._ghi('ham_module',module='crm',loai_ham='resolver_mtq',phien_ban_contract='1',ma_contract=ct,
                  phien_ban_module='1',ten_ham='resolver_demo',chu_ky='mod_crm.resolver_demo(text,uuid,text,jsonb,uuid,bigint)',
                  vai_so_huu=chu,ma_bam_goi='a'*64)

    def setUp(self):
        self._resolver()
        self.nd = uuid4()
        self.pn = [uuid4(),uuid4()]
        self.conn.execute("INSERT INTO loi.nguoi_dung(id,dang_nhap,ten,vai_tro) VALUES (%s,%s,'DEMO','XEM')",
                          (self.nd,'demo_'+self.nd.hex))
        self.dong = []
        self.gan = []
        for pn in self.pn:
            self.conn.execute("INSERT INTO loi.phap_nhan(id,ma,ten) VALUES (%s,%s,'DEMO')",(pn,pn.hex))
            self.conn.execute('INSERT INTO loi.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,%s)',
                              (self.nd,pn,['crm','core']))
            phong,pb,dong,gan = (uuid4() for _ in range(4))
            self.conn.execute("INSERT INTO loi.mtq_phong(id,phap_nhan_id,ma,ten) VALUES (%s,%s,'DEMO','DEMO')",(phong,pn))
            self.conn.execute('''INSERT INTO loi.mtq_phien_ban(id,phap_nhan_id,so_phien_ban,tao_boi,ly_do)
                VALUES (%s,%s,1,%s,'DEMO')''',(pb,pn,self.nd))
            self.conn.execute("INSERT INTO loi.mtq_dong(id,phien_ban_id,phap_nhan_id,phong_id,vai,gioi_han_vnd) VALUES (%s,%s,%s,%s,'CFO',100)",
                              (dong,pb,pn,phong))
            for vai in ('THUC_HIEN_1','THUC_HIEN_2','TRUONG_PHONG','NGUOI_XEM'):
                self.conn.execute('INSERT INTO loi.mtq_dong(phien_ban_id,phap_nhan_id,phong_id,vai) VALUES (%s,%s,%s,%s)',
                                  (pb,pn,phong,vai))
            self.dong.append(dong)
            for module,hd,man in (('CRM','XEM','TIEP_NHAN'),('CRM','DUYET','TIEP_NHAN'),('CORE','LAP','DANH_TINH')):
                self.conn.execute('INSERT INTO loi.mtq_o(dong_id,module,man,hanh_dong,cho_phep) VALUES (%s,%s,%s,%s,true)',(dong,module,man,hd))
            self.conn.execute("UPDATE loi.mtq_phien_ban SET trang_thai='DA_CONG_BO',cong_bo_boi=%s,cong_bo_luc=now(),phien_ban_dong=phien_ban_dong+1 WHERE id=%s",
                              (self.nd,pb))
            self.conn.execute("INSERT INTO loi.mtq_gan_vai(id,nguoi_dung_id,phap_nhan_id,phong_id,vai,cap_boi,ly_do) VALUES (%s,%s,%s,%s,'CFO',%s,'DEMO')",
                              (gan,self.nd,pn,phong,self.nd))
            self.gan.append(gan)
            self.conn.execute("INSERT INTO loi.mtq_pham_vi(gan_vai_id,phap_nhan_id,loai,khoa,cap_boi,ly_do) VALUES (%s,%s,'PHAP_NHAN',%s,%s,'DEMO')",
                              (gan,pn,str(pn),self.nd))
            self.conn.execute('INSERT INTO loi.mtq_kich_hoat(phap_nhan_id,bat,phien_ban_id,bat_boi,bat_luc) VALUES (%s,true,%s,%s,now())',(pn,pb,self.nd))
        self.obj = uuid4()
        self._doi_tuong(self.pn)
        self._cap_lai()

    def _doi_tuong(self, pns, *, tien='50', loai='TIEP_NHAN'):
        tap = [{'pn':str(pn),'hop_le':True,'loai':loai,'so_tien_vnd':tien} for pn in pns]
        self.conn.execute('INSERT INTO mod_crm.doi_tuong(id,tap) VALUES (%s,%s::jsonb) ON CONFLICT(id) DO UPDATE SET tap=EXCLUDED.tap',
                          (self.obj,json.dumps(tap)))

    def _cap(self,pn,module='crm',nguoi=None):
        return phien.cap_phien(self.core,nguoi_dung_id=nguoi or self.nd,module=module,phap_nhan_id=pn,
            dang_nhap_csdl=self.cac_thong_tin['core']['user'],pham_vi_hanh_dong=[XEM,DUYET] if module=='crm' else [LAP],
            hieu_luc_den=datetime.now(timezone.utc)+timedelta(minutes=10)).ma

    def _cap_lai(self):
        self.mas = [self._cap(pn) for pn in self.pn]
        self.ma_core = self._cap(self.pn[0],'core')

    def _ts(self, **doi):
        return {**dict(ma=self.mas[0],module='crm',phap_nhan_id=self.pn[0],hanh_dong=XEM,
                       doi_tuong={'bang':'doi_tuong','id':self.obj},cac_ma=[self.mas[1]]),**doi}

    def _quyet(self, **doi):
        return mtq.quyet_dinh_phien(self.core,**self._ts(**doi))

    def _context(self, pn=None, ma=None):
        mtq.dat_ngu_canh(self.core,ma=ma or self.mas[0],module='crm',phap_nhan_id=pn or self.pn[0],hanh_dong=XEM)

    def test_dung_login_that_va_force_rls_acl(self):
        login=self.cac_thong_tin['core']['user']
        self.assertEqual(self.core.execute('SELECT current_user,session_user').fetchone(),(login,login))
        for bang in CAC_BANG:
            with self.subTest(bang=bang),self.assertRaises(psycopg.errors.InsufficientPrivilege):
                self.core.execute(sql.SQL('SELECT * FROM loi.{}').format(sql.Identifier(bang)))
        self.assertEqual(self.conn.execute('''SELECT count(*) FROM pg_class WHERE relnamespace='loi'::regnamespace
            AND relname=ANY(%s) AND relrowsecurity AND relforcerowsecurity''',(list(CAC_BANG)+['nguoi_dung','phap_nhan','phan_quyen'],)).fetchone()[0],14)

    def test_dung_pn_thay_sai_pn_chan_gia_guc_vo_hieu(self):
        with self.core.transaction():
            self._context()
            self.assertEqual(self.core.execute('SELECT id FROM loi.phap_nhan').fetchall(),[(self.pn[0],)])
            self.assertEqual(self.core.execute('SELECT id FROM loi.nguoi_dung').fetchall(),[(self.nd,)])
            for ten,gia in (('ktt.nguoi_dung_id',str(uuid4())),('ktt.nguoi_dung_dang_nhap','CFO')):
                self.core.execute('SELECT set_config(%s,%s,true)',(ten,gia))
            self.assertEqual(self.core.execute('SELECT id FROM loi.phap_nhan').fetchall(),[(self.pn[0],)])
            self.core.execute("SELECT set_config('ktt.phap_nhan_id',%s,true)",(str(self.pn[1]),))
            self.assertEqual(self.core.execute('SELECT id FROM loi.phap_nhan').fetchall(),[])
            self.core.execute("SELECT set_config('ktt.ma_phien',%s,true)",('GIA_'*15,))
            self.assertEqual(self.core.execute('SELECT * FROM loi.phan_quyen').fetchall(),[])
        self.assertEqual(self.core.execute('SELECT id FROM loi.phap_nhan').fetchall(),[])

    def test_du_quyen_moi_pn_dat_va_doc_khong_ghi_audit(self):
        n=self.conn.execute('SELECT count(*) FROM loi.nhat_ky_kiem_toan').fetchone()[0]
        self.assertTrue(self._quyet()['cho_phep'])
        self.assertTrue(mtq.duoc_doc(self.core,**self._ts()))
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.nhat_ky_kiem_toan').fetchone()[0],n)

    def test_thieu_phien_mot_pn_tu_choi(self):
        self.assertEqual(self._quyet(cac_ma=[])['ma'],'MTQ_PHAP_NHAN')

    def test_ma_cua_nguoi_khac_khong_ghep_quyen_hai_pn(self):
        nguoi=uuid4()
        self.conn.execute("INSERT INTO loi.nguoi_dung(id,dang_nhap,ten,vai_tro) VALUES (%s,%s,'DEMO','XEM')",
                          (nguoi,'demo_'+nguoi.hex))
        self.conn.execute('INSERT INTO loi.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,%s)',
                          (nguoi,self.pn[1],['crm']))
        ma_khac=self._cap(self.pn[1],nguoi=nguoi)
        self.assertEqual(self._quyet(cac_ma=[ma_khac])['ma'],'MTQ_PHAP_NHAN')

    def test_thieu_quyen_mot_pn_tu_choi(self):
        self.conn.execute('UPDATE loi.mtq_gan_vai SET thu_hoi_luc=now(),thu_hoi_boi=%s,phien_ban_dong=phien_ban_dong+1 WHERE id=%s',
                          (self.nd,self.gan[1]))
        self._cap_lai()
        self.assertEqual(self._quyet()['ma'],'MTQ_GAN_VAI')
        self.assertFalse(mtq.duoc_doc(self.core,**self._ts()))

    def test_hon_hop_bat_tat_tu_choi(self):
        self.conn.execute('UPDATE loi.mtq_kich_hoat SET bat=false,phien_ban_dong=phien_ban_dong+1 WHERE phap_nhan_id=%s',(self.pn[1],))
        self._cap_lai()
        self.assertEqual(self._quyet()['ma'],'MTQ_PN_HON_HOP')

    def test_thieu_resolver_ke_ca_mtq_tat_tra_cho(self):
        self.assertEqual(self._quyet(phien_ban_contract='999')['ket_luan'],'CHO')
        self.conn.execute('UPDATE loi.mtq_kich_hoat SET bat=false,phien_ban_dong=phien_ban_dong+1 WHERE phap_nhan_id=ANY(%s)',(self.pn,))
        self._cap_lai()
        kq=self._quyet(phien_ban_contract='999')
        self.assertEqual(kq['ket_luan'],'CHO')
        self.assertFalse(kq['cho_phep'])

    def test_tien_chi_tu_resolver_va_han_muc(self):
        self._doi_tuong(self.pn,tien='101')
        self.assertEqual(self._quyet(hanh_dong=DUYET)['ma'],'MTQ_VUOT_HAN_MUC')
        self._doi_tuong(self.pn,tien=None)
        self.assertEqual(self._quyet(hanh_dong=DUYET)['ma'],'MTQ_THIEU_TIEN')

    def test_phien_thu_hoi_guc_cu_khong_con_quyen(self):
        with self.core.transaction():
            self._context()
            phien.thu_hoi_phien(self.core,ma=self.mas[0])
            self.assertEqual(self.core.execute('SELECT id FROM loi.phap_nhan').fetchall(),[])
            with self.assertRaises(mtq.LoiMTQ),self.core.transaction():
                self._quyet()

    def test_runtime_khong_ghi_truc_tiep_hay_chuyen_pn(self):
        with self.core.transaction():
            self._context()
            for cau,ts in (("INSERT INTO loi.phap_nhan(ma,ten) VALUES ('GIA','GIA')",()),
                           ('UPDATE loi.phan_quyen SET phap_nhan_id=%s WHERE nguoi_dung_id=%s',(self.pn[1],self.nd)),
                           ("INSERT INTO loi.nguoi_dung(dang_nhap,ten,vai_tro) VALUES ('GIA','GIA','XEM')",())):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege),self.core.transaction():
                    self.core.execute(cau,ts)
        # Trigger van chan neu ve sau co ham Core bi lap trinh sai/owner duoc UPDATE.
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.conn.execute('UPDATE loi.phan_quyen SET phap_nhan_id=%s WHERE nguoi_dung_id=%s AND phap_nhan_id=%s',
                              (uuid4(),self.nd,self.pn[0]))

    def test_audit_tu_choi_idempotent_khong_luu_ma(self):
        self.conn.execute('UPDATE loi.mtq_gan_vai SET thu_hoi_luc=now(),thu_hoi_boi=%s,phien_ban_dong=phien_ban_dong+1 WHERE id=%s',
                          (self.nd,self.gan[1]))
        self._cap_lai()
        req=uuid4()
        with self.core.transaction():
            ket=mtq.ghi_tu_choi_phien(self.core,request_id=req,**self._ts())
        self.assertEqual(mtq.ghi_tu_choi_phien(self.core,request_id=req,**self._ts()),ket)
        row=self.conn.execute('SELECT to_jsonb(t)::text FROM loi.mtq_tu_choi t WHERE id=%s',(ket,)).fetchone()[0]
        for ma in self.mas:
            self.assertNotIn(ma.lay_de_truyen(),row)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.nhat_ky_kiem_toan WHERE request_id=%s',(req,)).fetchone()[0],1)
        self.assertEqual(self.conn.execute('SELECT phap_nhan_id FROM loi.nhat_ky_kiem_toan WHERE request_id=%s',(req,)).fetchone()[0],self.pn[1])

    def test_ban_cong_bo_bat_bien(self):
        # Dong/o thuoc snapshot phien_ban_id; khong co phien_ban_dong rieng.
        for cau in ('UPDATE loi.mtq_o SET cho_phep=false WHERE dong_id=%s',
                    'UPDATE loi.mtq_dong SET gioi_han_vnd=999 WHERE id=%s'):
            with self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
                self.conn.execute(cau,(self.dong[0],))

    def test_g2_02b_tao_tra_trung_qua_cua_core(self):
        # Tuong duong ca skip G2-02, khong sua tep ngoai whitelist.
        ten='demo_'+uuid4().hex
        nd=mtq.tao_danh_tinh(self.core,ma=self.ma_core,phap_nhan_id=self.pn[0],loai='nguoi_dung',
                             du_lieu={'dang_nhap':ten,'ten':'DEMO','vai_tro':'XEM'})
        tv=mtq.tao_danh_tinh(self.core,ma=self.ma_core,phap_nhan_id=self.pn[0],loai='thanh_vien',
                             du_lieu={'nguoi_dung_id':nd,'module':['crm']})
        with self.assertRaises(mtq.LoiMTQ) as bat:
            mtq.tao_danh_tinh(self.core,ma=self.ma_core,phap_nhan_id=self.pn[0],loai='thanh_vien',
                              du_lieu={'nguoi_dung_id':nd,'module':['crm']})
        self.assertEqual(bat.exception.ma,'23505')
        ma=self._cap(self.pn[0],nguoi=nd)
        with self.core.transaction():
            self._context(ma=ma)
            self.assertEqual(self.core.execute('SELECT id,dang_nhap FROM loi.nguoi_dung').fetchall(),[(nd,ten)])
            self.assertEqual(self.core.execute('SELECT id FROM loi.phan_quyen WHERE nguoi_dung_id=%s',(nd,)).fetchall(),[(tv,)])
        with self.assertRaises(mtq.LoiMTQ) as bat:
            mtq.tao_danh_tinh(self.core,ma=self.ma_core,phap_nhan_id=self.pn[0],loai='nguoi_dung',
                              du_lieu={'dang_nhap':ten,'ten':'DEMO'})
        self.assertEqual(bat.exception.ma,'23505')
        pn=mtq.tao_danh_tinh(self.core,ma=self.ma_core,phap_nhan_id=self.pn[0],loai='phap_nhan',
                             du_lieu={'ma':ten,'ten':'DEMO','mst':'0012345678'})
        moi=self._cap(pn,'core')
        with self.core.transaction():
            mtq.dat_ngu_canh(self.core,ma=moi,module='core',phap_nhan_id=pn,hanh_dong=LAP)
            self.assertEqual(self.core.execute('SELECT id,mst FROM loi.phap_nhan').fetchall(),[(pn,'0012345678')])
        moi_goc=self._cap(self.pn[0],'core')
        with self.assertRaises(mtq.LoiMTQ) as bat:
            mtq.tao_danh_tinh(self.core,ma=moi_goc,phap_nhan_id=self.pn[0],loai='phap_nhan',
                              du_lieu={'ma':ten,'ten':'DEMO'})
        self.assertEqual(bat.exception.ma,'23505')


if __name__ == '__main__':
    unittest.main()
