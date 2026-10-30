"""G2-07: hợp nhất NGUON/B3; PG chỉ kho_test_*, LOGIN thật + phiên.

Resolver/contract DEMO bên dưới là seam thử, không phải gói nghiệp vụ được
kích hoạt ngoài test. Không DROP, không khởi động dịch vụ, không đọc cấu hình.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
import unittest
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import doi_cau_truc as dc, mtq, phien

try:
    from . import test_g2_06 as g206
except ImportError:
    import test_g2_06 as g206

psycopg = g206.psycopg
if psycopg is not None:
    from psycopg import sql

ADMIN_DSN = os.environ.get('KHO_PG_DSN_TEST')
SQL_PATH = dc.THU_MUC_SQL / '007_pham_vi.sql'
SQL = SQL_PATH.read_text(encoding='utf-8')
CAP = 'CRM:MTQ:CAP_PHAM_VI'
XEM = 'CRM:TIEP_NHAN:XEM'
KY = 'CRM:G3_G4_SOAN_KY:XEM'


def than_quyet_dinh(cau):
    return cau.split('    CREATE OR REPLACE FUNCTION loi.mtq_quyet_dinh_phien(', 1)[1].split('    $ham$;', 1)[0]


class PhamViThuanTest(unittest.TestCase):
    def test_mot_validator_chua_dong_thoi_hai_nhanh(self):
        self.assertEqual(SQL.count('CREATE OR REPLACE FUNCTION loi.mtq_kiem_pham_vi('), 1)
        than = SQL.split('CREATE OR REPLACE FUNCTION loi.mtq_kiem_pham_vi(', 1)[1].split('$ham$;', 1)[0]
        for moc in ("p_loai = 'NGUON'", "p_loai = 'DU_AN'", "('HOP_DONG','DU_AN')",
                    "n <> 1", "so_anh_xa <> 1", "IS DISTINCT FROM p_pn::text",
                    "regexp_replace(parts[i]", "p_quan_he IS DISTINCT FROM ghim"):
            self.assertIn(moc, than)
        for cam in ('loi.mtq_o', 'loi.mtq_dong', 'loi.mtq_kich_hoat'):
            self.assertNotIn(cam, than)

    def test_bao_toan_than_quyet_dinh_g206_ngoai_guard_moi(self):
        cu = than_quyet_dinh(g206.SQL_MTQ)
        moi = than_quyet_dinh(SQL)
        moi = moi.replace('\n        pham_vi loi.mtq_pham_vi; kiem jsonb; ma_pn text;', '')
        dau = moi.index('                    -- G2-07: kiem scope DA CHON')
        cuoi = moi.index("                    tien := (giai->>'so_tien_vnd')::numeric;", dau)
        self.assertEqual(moi[:dau] + moi[cuoi:], cu)

    def test_guard_dung_scope_da_chon_va_ma_tung_pn(self):
        guard = than_quyet_dinh(SQL).split('-- G2-07: kiem scope DA CHON', 1)[1].split('tien :=', 1)[0]
        self.assertIn('WHERE id=scope_id', guard)
        self.assertIn('loi.xac_minh_phien(m,p_module,pn,p_hanh_dong', guard)
        self.assertIn('loi.mtq_kiem_pham_vi(ma_pn,p_module,pn', guard)
        self.assertIn('RETURN kiem ||', guard)
        self.assertNotIn('ORDER BY', guard)

    def test_khong_phu_thuoc_bang_module_hoac_tu_kich_hoat_contract(self):
        self.assertNotRegex(SQL, r'(?i)(FROM|JOIN|REFERENCES|INSERT INTO)\s+(mod_|master\.|nhat_ky\.)')
        self.assertNotRegex(SQL, r'(?i)\b(CREATE TABLE|DROP|COMMIT|ALTER ROLE)\b')
        self.assertIn("p_module,'resolver_pham_vi'", SQL)
        self.assertIn('provolatile = \'v\'', SQL)
        self.assertIn("'ket_luan','CHO'", SQL)
        self.assertNotIn('INSERT INTO loi.dang_ky_contract', SQL)

    def test_audit_truoc_trigger_thu_hoi_va_khong_tin_actor(self):
        cap = SQL.split('CREATE OR REPLACE FUNCTION loi.mtq_cap_pham_vi_phien(', 1)[1].split('$ham$;', 1)[0]
        self.assertLess(cap.index('loi.ghi_kiem_toan('), cap.index('INSERT INTO loi.mtq_pham_vi('))
        self.assertLess(cap.index('pg_advisory_xact_lock(742601, 1)'), cap.index('loi.xac_minh_phien('))
        self.assertIn('loi.mtq_admin WHERE nguoi_dung_id=ai AND thu_hoi_luc IS NULL', cap)
        self.assertNotIn('p_actor', cap)
        self.assertIn('INSERT INTO loi.mtq_thay_doi', cap)

    def test_utf8_va_dollar_quote(self):
        self.assertFalse(SQL_PATH.read_bytes().startswith(b'\xef\xbb\xbf'))
        SQL.encode('utf-8').decode('utf-8')
        moc = re.findall(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', SQL)
        self.assertEqual((moc[0], moc[-1]), ('$$', '$$'))
        self.assertEqual(len(moc) % 2, 0)
        self.assertTrue(all(a == b for a, b in zip(moc[1:-1:2], moc[2:-1:2])))
        self.assertNotIn('placeholder', SQL)


@unittest.skipUnless(psycopg is not None and ADMIN_DSN,
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class PhamViPostgresTest(unittest.TestCase):
    _ghi = g206.MTQPostgresTest._ghi
    _contract = g206.MTQPostgresTest._contract
    _trang_thai = g206.MTQPostgresTest._trang_thai
    _resolver = g206.MTQPostgresTest._resolver

    @classmethod
    def setUpClass(cls):
        # Hàm nền tự tạo database/role có UUID và login có mật khẩu ngẫu nhiên.
        # Không chạy test nghiệp vụ với kết nối provisioning này.
        g206.MTQPostgresTest.setUpClass.__func__(cls)
        dc.ap_doi_cau_truc(cls.conn, [*g206.TEP_SQL, SQL_PATH])

    def _resolver_pham_vi(self):
        if self.conn.execute("SELECT to_regclass('mod_crm.quan_he_demo')").fetchone()[0]:
            return
        chu = self.tien_to + 'vai_doi_cau_truc_mod_crm'
        # Provisioning bằng admin; module owner không được tự GRANT hàm Core.
        self.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION loi.xac_minh_phien(text,text,uuid,text,uuid,bigint) TO {}').format(sql.Identifier(chu)))
        self.conn.execute(sql.SQL('GRANT USAGE ON SCHEMA loi TO {}').format(sql.Identifier(chu)))
        with self.conn.transaction():
            self.conn.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(chu)))
            self.conn.execute('''CREATE TABLE mod_crm.quan_he_demo(
                id uuid PRIMARY KEY, phap_nhan_id uuid, loai text, khoa text, quan_he jsonb)''')
            self.conn.execute('CREATE TABLE mod_crm.khach_demo(id uuid PRIMARY KEY,phap_nhan_id uuid)')
            self.conn.execute('CREATE TABLE mod_crm.nguon_demo(ma text PRIMARY KEY,trang_thai text)')
            self.conn.execute('''CREATE TABLE mod_crm.ho_so_demo(ho_so_id uuid PRIMARY KEY,
                nguon_cai_dat text,tham_chieu text,ma_bam text,trang_thai text)''')
            self.conn.execute('''CREATE TABLE mod_crm.anh_xa_demo(id uuid PRIMARY KEY,nguon_cai_dat text,
                tham_chieu text,ma_bam text,loai_chu_the text,khoa_chu_the text,phap_nhan_id uuid,
                trang_thai text,hieu_luc_tu timestamptz,hieu_luc_den timestamptz)''')
            self.conn.execute('''CREATE FUNCTION mod_crm.pham_vi_demo(text,uuid,text,jsonb,uuid,bigint)
                RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
                SET search_path = pg_catalog, pg_temp AS $$
                DECLARE q record; v jsonb; u jsonb := '[]'; a jsonb := '[]'; r record;
                BEGIN
                    IF NOT EXISTS (SELECT FROM loi.xac_minh_phien($1,'crm',$2,$3,$5,$6)) THEN
                        RAISE EXCEPTION 'Phiên resolver sai' USING ERRCODE='42501';
                    END IF;
                    IF $4->>'loai' = 'NGUON' THEN
                        -- Cả hai tập không lọc PN; khóa mọi ứng viên/ánh xạ.
                        FOR r IN SELECT h.ho_so_id,h.nguon_cai_dat,h.tham_chieu,h.ma_bam,i.trang_thai
                            FROM mod_crm.ho_so_demo h JOIN mod_crm.nguon_demo i ON i.ma=h.nguon_cai_dat
                            WHERE (upper(h.ho_so_id::text)=split_part($4->>'khoa','|',2)
                                OR upper(h.nguon_cai_dat)=split_part($4->>'khoa','|',2))
                            ORDER BY h.ho_so_id FOR SHARE OF h,i LOOP
                            u := u || jsonb_build_array(to_jsonb(r));
                        END LOOP;
                        FOR r IN SELECT m.* FROM mod_crm.anh_xa_demo m
                            WHERE upper(m.khoa_chu_the)=split_part($4->>'khoa','|',3)
                            ORDER BY m.id FOR SHARE LOOP
                            a := a || jsonb_build_array(to_jsonb(r));
                        END LOOP;
                        RETURN jsonb_build_object('ket_luan','DAT','ung_vien',u,'anh_xa',a);
                    END IF;
                    IF $4->'doi_tuong' <> 'null'::jsonb THEN
                        SELECT * INTO q FROM mod_crm.quan_he_demo
                            WHERE id=($4->'doi_tuong'->>'id')::uuid FOR SHARE;
                    ELSE
                        SELECT * INTO q FROM mod_crm.quan_he_demo
                            WHERE loai=$4->>'loai' AND khoa=$4->>'khoa' FOR SHARE;
                    END IF;
                    IF NOT FOUND OR q.phap_nhan_id IS DISTINCT FROM $2 THEN
                        RETURN jsonb_build_object('ket_luan','TU_CHOI');
                    END IF;
                    v := q.quan_he;
                    IF $4->>'loai'='DU_AN' AND $4->'doi_tuong'='null'::jsonb THEN
                        v := $4->'quan_he';
                        IF v ? 'doi_tac_id' AND NOT EXISTS (SELECT FROM mod_crm.khach_demo
                            WHERE id=(v->>'doi_tac_id')::uuid AND phap_nhan_id=$2) THEN
                            RETURN jsonb_build_object('ket_luan','TU_CHOI');
                        END IF;
                    END IF;
                    RETURN jsonb_build_object('ket_luan','DAT','phap_nhan_id',q.phap_nhan_id,'quan_he',v);
                END $$''')
            self.conn.execute('REVOKE ALL ON FUNCTION mod_crm.pham_vi_demo(text,uuid,text,jsonb,uuid,bigint) FROM PUBLIC')
            self.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION mod_crm.pham_vi_demo(text,uuid,text,jsonb,uuid,bigint) TO {}').format(
                sql.Identifier(self.tien_to + 'vai_doi_cau_truc_loi')))
        ct = self._contract('crm', kich_hoat=True)
        self._ghi('ham_module',module='crm',loai_ham='resolver_pham_vi',phien_ban_contract='1',ma_contract=ct,
                  phien_ban_module='1',ten_ham='pham_vi_demo',chu_ky='mod_crm.pham_vi_demo(text,uuid,text,jsonb,uuid,bigint)',
                  vai_so_huu=chu,ma_bam_goi='a'*64)

    def setUp(self):
        self._resolver()
        self._resolver_pham_vi()
        self.nd, self.pn, self.pn_khac, self.phong, self.gan = (uuid4() for _ in range(5))
        self.conn.execute("INSERT INTO loi.nguoi_dung(id,dang_nhap,ten,vai_tro) VALUES (%s,%s,'DEMO','XEM')",(self.nd,self.nd.hex))
        for pn in (self.pn,self.pn_khac):
            self.conn.execute("INSERT INTO loi.phap_nhan(id,ma,ten) VALUES (%s,%s,'DEMO')",(pn,pn.hex))
            self.conn.execute('INSERT INTO loi.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,%s)',(self.nd,pn,['crm']))
        self.conn.execute("INSERT INTO loi.mtq_admin(nguoi_dung_id,cap_boi,ly_do) VALUES (%s,%s,'DEMO')",(self.nd,self.nd))
        self.conn.execute("INSERT INTO loi.mtq_phong(id,phap_nhan_id,ma,ten) VALUES (%s,%s,'DEMO','DEMO')",(self.phong,self.pn))
        self.conn.execute("INSERT INTO loi.mtq_gan_vai(id,nguoi_dung_id,phap_nhan_id,phong_id,vai,cap_boi,ly_do) VALUES (%s,%s,%s,%s,'CFO',%s,'DEMO')",
                          (self.gan,self.nd,self.pn,self.phong,self.nd))
        self.hd, self.da, self.obj, self.khach = (uuid4() for _ in range(4))
        self.quan_he = dict(soan_id=str(uuid4()),du_an_id=str(self.da),doi_tac_id=str(self.khach),khach_du_thao_sha256=None)
        self.conn.execute('INSERT INTO mod_crm.khach_demo VALUES (%s,%s)',(self.khach,self.pn))
        for id,loai,khoa,q in ((self.hd,'HOP_DONG',self.hd,self.quan_he),(self.da,'DU_AN',self.da,{}),
                               (self.obj,'DOI_TUONG',self.obj,self.quan_he)):
            self.conn.execute('INSERT INTO mod_crm.quan_he_demo VALUES (%s,%s,%s,%s,%s::jsonb)',(id,self.pn,loai,str(khoa),json.dumps(q)))
        self.ho_so = uuid4()
        self.nguon = 'DEMO_' + uuid4().hex
        self.chu_the = 'CONG TY ' + uuid4().hex.upper()
        self.conn.execute("INSERT INTO mod_crm.nguon_demo VALUES (%s,'HOAT_DONG')",(self.nguon,))
        self.conn.execute("INSERT INTO mod_crm.ho_so_demo VALUES (%s,%s,'HO_SO',%s,'HOAT_DONG')",(self.ho_so,self.nguon,'a'*64))
        self.anh_xa = self._anh_xa(self.pn)

    def _ma(self, pn=None):
        return phien.cap_phien(self.core,nguoi_dung_id=self.nd,module='crm',phap_nhan_id=pn or self.pn,
            dang_nhap_csdl=self.cac_thong_tin['core']['user'],pham_vi_hanh_dong=[CAP,XEM,KY],
            hieu_luc_den=datetime.now(timezone.utc)+timedelta(minutes=5)).ma.lay_de_truyen()

    def _cap(self, loai='HOP_DONG', khoa=None, quan_he=None, **doi):
        ts = dict(ma=self._ma(),module='crm',pn=self.pn,gan=self.gan,loai=loai,
                  khoa=str(khoa or self.hd),quan_he=json.dumps(quan_he or {}),ly_do='DEMO',phien_ban='1')
        ts.update(doi)
        return self.core.execute('''SELECT loi.mtq_cap_pham_vi_phien(
            %(ma)s,%(module)s,%(pn)s,%(gan)s,%(loai)s,%(khoa)s,%(quan_he)s::jsonb,%(ly_do)s,%(phien_ban)s)''',ts).fetchone()[0]

    def _anh_xa(self, pn, **doi):
        id = uuid4()
        ts = dict(id=id,nguon=self.nguon,tham_chieu='HO_SO',bam='a'*64,loai='COMPANY',
                  khoa=self.chu_the,pn=pn,trang_thai='DA_DUYET',tu=datetime.now(timezone.utc)-timedelta(days=1),den=None)
        ts.update(doi)
        self.conn.execute('''INSERT INTO mod_crm.anh_xa_demo VALUES
            (%(id)s,%(nguon)s,%(tham_chieu)s,%(bam)s,%(loai)s,%(khoa)s,%(pn)s,%(trang_thai)s,%(tu)s,%(den)s)''',ts)
        return id

    def _kich_hoat(self, *, hd=None, da=None, nguon=None):
        pb = uuid4()
        self.conn.execute("INSERT INTO loi.mtq_phien_ban(id,phap_nhan_id,so_phien_ban,tao_boi,ly_do) VALUES (%s,%s,1,%s,'DEMO')",(pb,self.pn,self.nd))
        for vai in ('THUC_HIEN_1','THUC_HIEN_2','TRUONG_PHONG','CFO','NGUOI_XEM'):
            d = self.conn.execute('INSERT INTO loi.mtq_dong(phien_ban_id,phap_nhan_id,phong_id,vai) VALUES (%s,%s,%s,%s) RETURNING id',(pb,self.pn,self.phong,vai)).fetchone()[0]
            if vai == 'CFO':
                for man in ('TIEP_NHAN','G3_G4_SOAN_KY'):
                    self.conn.execute("INSERT INTO loi.mtq_o(dong_id,module,man,hanh_dong,cho_phep) VALUES (%s,'CRM',%s,'XEM',true)",(d,man))
        self.conn.execute("UPDATE loi.mtq_phien_ban SET trang_thai='DA_CONG_BO',cong_bo_boi=%s,cong_bo_luc=now(),phien_ban_dong=2 WHERE id=%s",(self.nd,pb))
        self.conn.execute('INSERT INTO loi.mtq_kich_hoat(phap_nhan_id,bat,phien_ban_id,bat_boi,bat_luc) VALUES (%s,true,%s,%s,now())',(self.pn,pb,self.nd))
        tap = [dict(pn=str(self.pn),hop_le=True,loai='TIEP_NHAN',hd=str(hd) if hd else None,
                    da=str(da) if da else None,nguon_khoa=nguon)]
        self.conn.execute('INSERT INTO mod_crm.doi_tuong(id,tap) VALUES (%s,%s::jsonb)',(self.obj,json.dumps(tap)))

    def _quyet(self, **doi):
        ts = dict(ma=phien.MaBiMat(self._ma()),module='crm',phap_nhan_id=self.pn,
                  hanh_dong=XEM,doi_tuong={'bang':'doi_tuong','id':self.obj})
        return mtq.quyet_dinh_phien(self.core,**{**ts,**doi})

    def test_login_that_va_khong_mo_quyen_noi_bo(self):
        login = self.cac_thong_tin['core']['user']
        self.assertEqual(self.core.execute('SELECT current_user,session_user').fetchone(),(login,login))
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.core.execute('SELECT * FROM loi.mtq_pham_vi')
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.core.execute("SELECT loi.mtq_kiem_pham_vi(NULL,'crm',NULL,'XEM','NGUON','x','{}')")
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self._cap(ma='GIA_'*20)

    def test_phien_dung_nhung_khong_con_admin_hoac_gan_vai_sai_pn(self):
        self.assertEqual(self._cap(pn=self.pn_khac,ma=self._ma(self.pn_khac))['ket_luan'],'TU_CHOI')
        self.conn.execute('''UPDATE loi.mtq_admin SET thu_hoi_luc=now(),thu_hoi_boi=%s,
            phien_ban_dong=phien_ban_dong+1 WHERE nguoi_dung_id=%s''',(self.nd,self.nd))
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self._cap()

    def test_cap_chua_tick_ghim_hd_va_audit_cung_transaction(self):
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.mtq_o o JOIN loi.mtq_dong d ON d.id=o.dong_id WHERE d.phap_nhan_id=%s',(self.pn,)).fetchone()[0],0)
        self.assertEqual(self._cap()['pham_vi']['quan_he'],self.quan_he)
        row = self.conn.execute('SELECT nguoi_dung_id,module,ket_luan FROM loi.nhat_ky_kiem_toan WHERE phap_nhan_id=%s AND hanh_dong=%s',(self.pn,CAP)).fetchall()
        self.assertEqual(row,[(self.nd,'crm','DAT')])
        n = self.conn.execute('SELECT count(*) FROM loi.nhat_ky_kiem_toan').fetchone()[0]
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self._cap()
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.nhat_ky_kiem_toan').fetchone()[0],n)

    def test_sai_quan_he_hd_da_va_khac_pn_bi_chan_chua_tick(self):
        self.assertEqual(self._cap(quan_he={'doi_tac_id':str(uuid4())})['ma'],'MTQ_PHAM_VI_LECH')
        khac = uuid4()
        self.conn.execute('INSERT INTO mod_crm.khach_demo VALUES (%s,%s)',(khac,self.pn_khac))
        for q in ({'doi_tac_id':str(khac)}, {'doi_tac_id':str(uuid4())}, {'khach_du_thao_sha256':'x'*64},
                  {'doi_tac_id':str(self.khach),'them':True}, {'khach_du_thao_sha256':None}):
            with self.subTest(q=q):
                self.assertEqual(self._cap('DU_AN',self.da,q)['ket_luan'],'TU_CHOI')
        self.conn.execute('UPDATE mod_crm.quan_he_demo SET phap_nhan_id=%s WHERE id=%s',(self.pn_khac,self.hd))
        self.assertEqual(self._cap()['ket_luan'],'TU_CHOI')

    def test_du_an_khong_tu_suy_khach_nhung_chap_nhan_khach_tuong_minh(self):
        self.assertEqual(self._cap('DU_AN',self.da)['pham_vi']['quan_he'],{})
        self.conn.execute("UPDATE loi.mtq_pham_vi SET thu_hoi_luc=now(),thu_hoi_boi=%s,phien_ban_dong=2 WHERE gan_vai_id=%s",(self.nd,self.gan))
        q = {'doi_tac_id':str(self.khach)}
        self.assertEqual(self._cap('DU_AN',self.da,q)['pham_vi']['quan_he'],q)

    def test_nguon_chuan_hoa_mo_ho_sai_pn_va_anh_xa_trung(self):
        khoa = ' invoice_set | ' + self.nguon.lower() + ' | ' + self.chu_the.lower().replace(' ','   ') + ' '
        self.assertEqual(self._cap('NGUON',khoa)['pham_vi']['khoa'],f'INVOICE_SET|{self.nguon.upper()}|{self.chu_the}')
        self.conn.execute("INSERT INTO mod_crm.ho_so_demo VALUES (%s,%s,'KHAC',%s,'HOAT_DONG')",(uuid4(),self.nguon,'b'*64))
        self.assertEqual(self._cap('NGUON',khoa)['ma'],'MTQ_NGUON_PROFILE')
        # UUID ho so ro rang van phai kiem TOAN BO anh xa, ke ca PN khac.
        khoa = f'INVOICE_SET|{self.ho_so}|{self.chu_the}'
        self._anh_xa(self.pn_khac)
        self.assertEqual(self._cap('NGUON',khoa)['ma'],'MTQ_NGUON_ANH_XA')

    def test_nguon_anh_xa_trung_het_han_hash_sai_va_loai_cam(self):
        khoa = f'INVOICE_SET|{self.ho_so}|{self.chu_the}'
        self.conn.execute('UPDATE mod_crm.anh_xa_demo SET ma_bam=%s WHERE id=%s',('b'*64,self.anh_xa))
        try:
            self.assertEqual(self._cap('NGUON',khoa)['ma'],'MTQ_NGUON_ANH_XA')
        finally:
            self.conn.execute('UPDATE mod_crm.anh_xa_demo SET ma_bam=%s WHERE id=%s',('a'*64,self.anh_xa))
        self.conn.execute("UPDATE mod_crm.anh_xa_demo SET hieu_luc_tu=now()+interval '1 day' WHERE id=%s",(self.anh_xa,))
        try:
            self.assertEqual(self._cap('NGUON',khoa)['ma'],'MTQ_NGUON_ANH_XA')
        finally:
            self.conn.execute("UPDATE mod_crm.anh_xa_demo SET hieu_luc_tu=now()-interval '1 day' WHERE id=%s",(self.anh_xa,))
        self._anh_xa(self.pn)
        self.assertEqual(self._cap('NGUON',khoa)['ma'],'MTQ_NGUON_ANH_XA')
        self.conn.execute('UPDATE mod_crm.anh_xa_demo SET hieu_luc_den=now() WHERE nguon_cai_dat=%s',(self.nguon,))
        self.assertEqual(self._cap('NGUON',khoa)['ma'],'MTQ_NGUON_ANH_XA')
        for khoa in ('x',f'L11_EVIDENCE_SET|{self.ho_so}|x', 'INVOICE_SET||x'):
            self.assertEqual(self._cap('NGUON',khoa)['ket_luan'],'TU_CHOI')

    def test_kho10_chi_nhan_anh_xa_warehouse_hien_hanh(self):
        khoa = f'KHO10_PHIEU|{self.ho_so}|{self.chu_the}'
        self.assertEqual(self._cap('NGUON',khoa)['ma'],'MTQ_NGUON_ANH_XA')
        self.conn.execute("UPDATE mod_crm.anh_xa_demo SET loai_chu_the='WAREHOUSE' WHERE id=%s",(self.anh_xa,))
        self.assertEqual(self._cap('NGUON',khoa)['ket_luan'],'DAT')

    def test_thieu_resolver_tra_cho_khong_ghi_audit_hay_scope(self):
        n = self.conn.execute('SELECT count(*) FROM loi.nhat_ky_kiem_toan').fetchone()[0]
        for loai,khoa in (('HOP_DONG',self.hd),('DU_AN',self.da),('NGUON',f'INVOICE_SET|{self.ho_so}|{self.chu_the}')):
            self.assertEqual(self._cap(loai,khoa,phien_ban='999')['ket_luan'],'CHO')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.mtq_pham_vi WHERE gan_vai_id=%s',(self.gan,)).fetchone()[0],0)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.nhat_ky_kiem_toan').fetchone()[0],n)

    def test_quan_he_doi_sau_ghim_chan_khong_fallback_pn(self):
        self._cap()
        self._cap('PHAP_NHAN',self.pn)
        self._kich_hoat(hd=self.hd)
        self.assertTrue(self._quyet()['cho_phep'])
        self.conn.execute("UPDATE mod_crm.quan_he_demo SET quan_he=jsonb_set(quan_he,'{doi_tac_id}',to_jsonb(%s::text)) WHERE id=%s",(str(uuid4()),self.obj))
        self.assertEqual(self._quyet()['ma'],'MTQ_PHAM_VI_LECH')
        self.assertFalse(mtq.duoc_doc(self.core,ma=phien.MaBiMat(self._ma()),module='crm',phap_nhan_id=self.pn,
                                     hanh_dong=XEM,doi_tuong={'bang':'doi_tuong','id':self.obj}))

    def test_du_an_doi_khach_sau_ghim_bi_chan(self):
        q = {'doi_tac_id':str(self.khach)}
        self._cap('DU_AN',self.da,q)
        self.conn.execute('UPDATE mod_crm.quan_he_demo SET quan_he=%s::jsonb WHERE id=%s',(json.dumps(q),self.obj))
        self._kich_hoat(da=self.da)
        self.assertTrue(self._quyet()['cho_phep'])
        self.conn.execute('UPDATE mod_crm.quan_he_demo SET quan_he=%s::jsonb WHERE id=%s',
                          (json.dumps({'doi_tac_id':str(uuid4())}),self.obj))
        self.assertEqual(self._quyet()['ma'],'MTQ_PHAM_VI_LECH')

    def test_mat_resolver_pham_vi_khi_dung_tra_cho(self):
        self._cap()
        self._kich_hoat(hd=self.hd)
        # Giữ resolver đối tượng G2-06, chỉ làm binding phạm vi không tồn tại.
        # Commit provisioning để login Core thấy thay đổi, phục hồi ở finally.
        self.conn.execute('ALTER FUNCTION mod_crm.pham_vi_demo(text,uuid,text,jsonb,uuid,bigint) RENAME TO pham_vi_demo_cho')
        try:
            self.assertEqual(self._quyet()['ket_luan'],'CHO')
        finally:
            self.conn.execute('ALTER FUNCTION mod_crm.pham_vi_demo_cho(text,uuid,text,jsonb,uuid,bigint) RENAME TO pham_vi_demo')

    def test_du_an_quan_he_rong_khong_du_quyen_ky(self):
        self._cap('DU_AN',self.da)
        self._kich_hoat(da=self.da)
        self.conn.execute("UPDATE mod_crm.quan_he_demo SET quan_he='{}'::jsonb WHERE id=%s",(self.obj,))
        self.assertEqual(self._quyet(hanh_dong=KY)['ma'],'MTQ_PHAM_VI_LECH')

    def test_nguon_doi_anh_xa_sau_cap_bi_chan(self):
        khoa = f'INVOICE_SET|{self.ho_so}|{self.chu_the}'
        khoa = self._cap('NGUON',khoa)['pham_vi']['khoa']
        self._kich_hoat(nguon=khoa)
        self.assertTrue(self._quyet()['cho_phep'])
        self.conn.execute('UPDATE mod_crm.anh_xa_demo SET phap_nhan_id=%s WHERE id=%s',(self.pn_khac,self.anh_xa))
        self.assertEqual(self._quyet()['ma'],'MTQ_NGUON_ANH_XA')

    def test_resolver_giu_khoa_hang_den_het_transaction(self):
        # Kết nối thứ hai thử đổi nguồn/ánh xạ/CRM khi cửa Core đang giữ khóa.
        tt = g206._kiem_dich_test(g206.conninfo_to_dict(ADMIN_DSN))
        khac = psycopg.connect(**{**tt,'dbname':self.db},autocommit=True)
        self.addCleanup(khac.close)
        khac.execute("SET lock_timeout='150ms'")
        with self.core.transaction():
            self.assertEqual(self._cap('NGUON',f'INVOICE_SET|{self.ho_so}|{self.chu_the}')['ket_luan'],'DAT')
            for cau,ts in (('UPDATE mod_crm.ho_so_demo SET ma_bam=%s WHERE ho_so_id=%s',('b'*64,self.ho_so)),
                           ('UPDATE mod_crm.nguon_demo SET trang_thai=%s WHERE ma=%s',('TAT',self.nguon)),
                           ('UPDATE mod_crm.anh_xa_demo SET phap_nhan_id=%s WHERE id=%s',(self.pn_khac,self.anh_xa))):
                with self.assertRaises(psycopg.errors.LockNotAvailable):
                    khac.execute(cau,ts)
        with self.core.transaction():
            self.assertEqual(self._cap()['ket_luan'],'DAT')
            with self.assertRaises(psycopg.errors.LockNotAvailable):
                khac.execute('UPDATE mod_crm.quan_he_demo SET quan_he=%s::jsonb WHERE id=%s',('{}',self.hd))


if __name__ == '__main__':
    unittest.main()
