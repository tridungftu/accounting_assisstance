"""G2-13: login thật, module nghĩa vụ DEMO chỉ tồn tại trong fixture.

Không tự bật PostgreSQL; KHO_PG_DSN_TEST phải trỏ cụm test/DEMO PG16+.
Fixture nền tự tạo kho_test_*; không xóa CSDL/role sau test.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
import threading
import traceback
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import cong_tac, doi_cau_truc as dc, lien_ket as lk, phien
try:
    from tests import test_g2_12 as g212
except ImportError:
    import test_g2_12 as g212

psycopg = g212.psycopg
if psycopg is not None:
    from psycopg import sql

SQL_PATH = dc.THU_MUC_SQL / '013_lien_ket.sql'
SQL = SQL_PATH.read_text(encoding='utf-8')
CK = 'lien_ket_v2(text,text,uuid,text,text,uuid,jsonb,text,uuid,bigint)'
CK_NV = 'resolver(text,text,uuid,text,jsonb,uuid,bigint)'
LAP, SUA, XEM = g212.LAP, g212.SUA, g212.XEM
HUY = 'CRM:TIEP_NHAN:HUY'


def du_lieu(a=None, nv=None, **doi):
    return dict(chung_tu_a_id=str(a or uuid4()), loai='DEMO_TIEN', mo_hinh_phan_bo='DIRECT',
                module_nghia_vu='demo_nv', loai_nghia_vu='DOT', nghia_vu_id=str(nv or uuid4()),
                phien_ban_can_cu_id=str(uuid4()), ma_bam_phien_ban_can_cu='b'*64,
                so_tien_khop_minor='60', tien_te='VND', thang_tien=0, **doi)


class LienKetThuanTest(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.conn.info.transaction_status = 2
        self.ctx = dict(ma=phien.MaBiMat('CANARY_PHIEN'), module='crm', phap_nhan_id=uuid4(), hanh_dong=LAP)
        self.data = du_lieu()
        self.id = uuid4()

    def _tao(self, **doi):
        return lk.tao(self.conn, **{**dict(lien_ket_id=self.id, du_lieu=self.data), **self.ctx, **doi})

    def test_bind_mot_ket_noi_va_khong_tu_commit(self):
        self.data['so_tien_khop_minor'] = '900719925474099312345'
        truoc = dict(self.data)
        self._tao()
        cau, ts = self.conn.execute.call_args.args
        self.assertIn('danh_muc.lien_ket_v2', cau)
        self.assertNotIn('CANARY', cau)
        self.assertEqual(ts[:4], ('CANARY_PHIEN', 'crm', self.ctx['phap_nhan_id'], LAP))
        self.assertEqual(json.loads(ts[6]), truoc)
        self.assertEqual(self.data, truoc)
        for ten in ('connect', 'commit', 'rollback', 'transaction'):
            getattr(self.conn, ten).assert_not_called()

    def test_bat_buoc_transaction(self):
        for st in (0, 1, 3, 4):
            self.conn.info.transaction_status = st
            with self.subTest(st=st), self.assertRaises(ValueError):
                self._tao()
        self.conn.execute.assert_not_called()

    def test_khong_nhan_tien_float_actor_trang_thai_hoac_thieu_can_cu(self):
        for doi in ({'so_tien_khop_minor': 60}, {'so_tien_khop_minor': 1.1}, {'so_tien_khop_minor': '0'},
                    {'so_tien_khop_minor': '1.0'}, {'so_tien_khop_minor': '9'*39}, {'tao_boi': str(uuid4())},
                    {'trang_thai': 'DA_KHOP'}, {'thang_tien': True}, {'tien_te': 'vnd'},
                    {'ma_bam_phien_ban_can_cu': 'sai'}, {'nghia_vu_id': None}):
            with self.subTest(doi=doi), self.assertRaises((ValueError, TypeError)):
                lk.tao(self.conn, lien_ket_id=self.id, du_lieu={**self.data, **doi}, **self.ctx)
        self.conn.execute.assert_not_called()

    def test_child_khong_dem_tien_parent_va_trung_dich_logic(self):
        con = {k: v for k, v in self.data.items() if k in lk._DICH}
        con.update(dich_logic_id=str(uuid4()), cau_phan='GOC', so_tien_minor='60')
        data = {k: v for k, v in self.data.items() if k not in lk._DICH | {'so_tien_khop_minor'}}
        data.update(mo_hinh_phan_bo='CHILD', phan_bo=[con])
        lk.tao(self.conn, lien_ket_id=self.id, du_lieu=data, **self.ctx)
        self.assertNotIn('so_tien_khop_minor', json.loads(self.conn.execute.call_args.args[1][6]))
        for con_sai in ([], [con, con], [{**con, 'so_tien_minor': 60}]):
            with self.subTest(con=con_sai), self.assertRaises(ValueError):
                lk.tao(self.conn, lien_ket_id=self.id, du_lieu={**data, 'phan_bo': con_sai}, **self.ctx)

    def test_sua_huy_can_dung_hanh_dong_va_ly_do(self):
        moi = uuid4()
        lk.sua(self.conn, lien_ket_id=self.id, id_moi=moi, ly_do='DEMO', du_lieu=self.data,
               **{**self.ctx, 'hanh_dong': SUA})
        self.assertEqual(json.loads(self.conn.execute.call_args.args[1][6])['id_moi'], str(moi))
        lk.huy(self.conn, lien_ket_id=self.id, ly_do='DEMO', **{**self.ctx, 'hanh_dong': HUY})
        self.assertEqual(json.loads(self.conn.execute.call_args.args[1][6]), {'ly_do_huy': 'DEMO'})
        with self.assertRaises(ValueError):
            lk.huy(self.conn, lien_ket_id=self.id, ly_do='DEMO', **self.ctx)
        with self.assertRaises(ValueError):
            lk.huy(self.conn, lien_ket_id=self.id, ly_do=' ', **{**self.ctx, 'hanh_dong': HUY})

    def test_loi_khong_lo_tong_token_hay_driver(self):
        for ma in ('LIEN_KET_VUOT_CHUNG_TU', 'LIEN_KET_VUOT_NGHIA_VU', 'TAI_LIEU_MTQ', 'LIEN_KET_CAN_CU'):
            exc = RuntimeError('CANARY_PHIEN postgresql://CANARY 80+30>100')
            exc.diag = MagicMock(message_primary=ma)
            self.conn.execute.side_effect = exc
            with self.assertRaises(lk.LoiLienKet) as bat:
                self._tao()
            self.assertEqual(bat.exception.ma, ma)
            self.assertIsNone(bat.exception.__context__)
            self.assertNotIn('CANARY', ''.join(traceback.format_exception(bat.exception)))
            self.assertNotIn('80', str(bat.exception))

    def test_cho_giu_nguyen_ket_luan_va_khong_commit(self):
        cho = dict(ket_luan='CHO', ly_do='THIEU_CAN_CU')
        self.conn.execute.return_value.fetchone.return_value = (cho,)
        self.assertEqual(self._tao(), cho)
        self.conn.commit.assert_not_called()

    def test_sql_can_bang_nhan_dollar_va_ham_tinh_ngoai_do(self):
        moc = re.findall(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', SQL)
        self.assertTrue(moc)
        self.assertEqual(len(moc) % 2, 0)
        for i in range(0, len(moc), 2):
            self.assertEqual(moc[i], moc[i + 1], f'Nhan dollar sai cap {i // 2 + 1}')
        for nhan in set(moc):
            self.assertEqual(moc.count(nhan) % 2, 0, nhan)
        khoi_do = re.findall(r'DO\s+(\$[A-Za-z_0-9]*\$)(.*?)\1\s*;', SQL, re.S)
        self.assertTrue(khoi_do)
        for _, than in khoi_do:
            self.assertNotRegex(than, r'(?i)CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION')
        self.assertIn('IF n<>(CASE WHEN b IS NULL THEN 1 ELSE 2 END) THEN', SQL)

    def test_sql_khong_drop_fk_module_hay_bom(self):
        self.assertNotRegex(SQL, r'(?i)\bDROP\s+(TABLE|FUNCTION|TRIGGER|ROLE|DATABASE)')
        self.assertNotRegex(SQL, r'(?i)(REFERENCES|FROM|JOIN)\s+mod_')
        self.assertFalse(SQL_PATH.read_bytes().startswith(b'\xef\xbb\xbf'))


@unittest.skipUnless(psycopg is not None and os.environ.get('KHO_PG_DSN_TEST'),
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class LienKetPostgresTest(unittest.TestCase):
    _ghi = g212.DanhMucPostgresTest._ghi
    _contract = g212.DanhMucPostgresTest._contract
    _trang_thai = g212.DanhMucPostgresTest._trang_thai
    _cap = g212.DanhMucPostgresTest._cap
    _ctx = g212.DanhMucPostgresTest._ctx
    _tao = g212.DanhMucPostgresTest._tao

    def _resolver(self):
        g212.DanhMucPostgresTest._resolver(self)
        self.conn.execute('''CREATE OR REPLACE FUNCTION mod_crm.resolver_demo(text,uuid,text,jsonb,uuid,bigint)
            RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
            SELECT tap FROM mod_crm.doi_tuong WHERE id=($4->>'id')::uuid $$''')

    @classmethod
    def setUpClass(cls):
        g212.DanhMucPostgresTest.setUpClass.__func__(cls)
        cls.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION danh_muc.'+CK+' TO {}').format(sql.Identifier(cls.vai_module)))
        cls.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION loi.mtq_phien_rls() TO {}').format(sql.Identifier(cls.vai_module)))
        # Catalog HUY của module DEMO chỉ nằm trong fixture, không sửa catalog Core.
        cls.conn.execute("""INSERT INTO loi.mtq_danh_muc_hanh_dong VALUES
            (1,'CRM','TIEP_NHAN','HUY','CRM:TIEP_NHAN:HUY','TIEP_NHAN','MAY_CHU_MTQ4','PHI_TIEN')
            ON CONFLICT DO NOTHING""")

    def setUp(self):
        g212.DanhMucPostgresTest.setUp(self)
        self._quyen_huy()
        self._demo_module()
        self.a, self.nv, self.pb = uuid4(), uuid4(), uuid4()
        self._chung_tu(self.a, 1000)
        self.conn.execute('''INSERT INTO mod_demo_nv.nghia_vu(id,phap_nhan_id,loai,pb,bam,so_tien_minor)
            VALUES (%s,%s,'DOT',%s,%s,1000)''', (self.nv, self.pn, self.pb, 'b'*64))
        self._quyen(self.nv)
        self.data = du_lieu(self.a, self.nv)
        self.data['phien_ban_can_cu_id'] = str(self.pb)
        self.ma = self._cap(hd=[LAP, SUA, XEM, g212.DUYET, HUY])
        self.uy = phien.cap_phien(self.core, nguoi_dung_id=self.nd, module='crm', phap_nhan_id=self.pn,
            dang_nhap_csdl=self.module_login, pham_vi_hanh_dong=[LAP, SUA, XEM, HUY], loai='UY_NHIEM_PHIEN',
            ma_goc=self.ma, hieu_luc_den=datetime.now(timezone.utc)+timedelta(minutes=4)).ma
        ma_ct = self._cap(module='core', hd=['CORE:MODULE:SUA'])
        cong_tac.doi_che_do(self.core, ma=ma_ct, module='demo_nv', phap_nhan_id=self.pn,
            payload=dict(row_version='1', che_do='VAN_HANH', nguoi_thu_ids=[]), request_id=uuid4())

    def _quyen_huy(self):
        # Tạo snapshot mới đúng guard MTQ, không sửa bản đã công bố.
        phong, cu, gan = self.conn.execute('''SELECT g.phong_id,k.phien_ban_id,g.id FROM loi.mtq_gan_vai g
            JOIN loi.mtq_kich_hoat k USING(phap_nhan_id) WHERE g.nguoi_dung_id=%s AND g.phap_nhan_id=%s''',
            (self.nd, self.pn)).fetchone()
        pb = uuid4()
        self.conn.execute("INSERT INTO loi.mtq_phien_ban(id,phap_nhan_id,so_phien_ban,tao_boi,ly_do) VALUES (%s,%s,2,%s,'DEMO')", (pb,self.pn,self.nd))
        cac_dong = self.conn.execute('SELECT id,vai FROM loi.mtq_dong WHERE phien_ban_id=%s', (cu,)).fetchall()
        for dong_cu, vai in cac_dong:
            dong = uuid4()
            self.conn.execute('INSERT INTO loi.mtq_dong(id,phien_ban_id,phap_nhan_id,phong_id,vai) VALUES (%s,%s,%s,%s,%s)', (dong,pb,self.pn,phong,vai))
            if vai == 'CFO':
                for hd in ('XEM','LAP','SUA','DUYET','HUY'):
                    self.conn.execute("INSERT INTO loi.mtq_o(dong_id,module,man,hanh_dong,cho_phep) VALUES (%s,'CRM','TIEP_NHAN',%s,true)", (dong,hd))
        self.conn.execute("UPDATE loi.mtq_phien_ban SET trang_thai='DA_CONG_BO',cong_bo_boi=%s,cong_bo_luc=now(),phien_ban_dong=2 WHERE id=%s", (self.nd,pb))
        self.conn.execute('UPDATE loi.mtq_kich_hoat SET phien_ban_id=%s,phien_ban_dong=phien_ban_dong+1 WHERE phap_nhan_id=%s', (pb,self.pn))

    def _demo_module(self):
        if self.conn.execute("SELECT to_regclass('mod_demo_nv.nghia_vu')").fetchone()[0]:
            return
        self._ghi('module', ma='m1', ten='M1 DEMO chỉ định danh đầu chứng từ')
        self._ghi('module', ma='demo_nv', ten='Nghĩa vụ DEMO')
        self._ghi('phien_ban_module', module='demo_nv', so_phien_ban='1', ma_bam_goi='b'*64, tuong_thich={})
        self._ghi('trang_thai_module', module='demo_nv', so_phien_ban='1', trang_thai='da_cai')
        ct = self._contract('demo_nv', kich_hoat=True)
        chu = self.tien_to+'vai_doi_cau_truc_mod_demo_nv'
        kiem = self.tien_to+'vai_kiem_toan_ven_mod_demo_nv'
        core_chu = self.tien_to+'vai_doi_cau_truc_loi'
        for role in (chu, kiem):
            self.conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB').format(sql.Identifier(role)))
        self.conn.execute(sql.SQL('CREATE SCHEMA mod_demo_nv AUTHORIZATION {}').format(sql.Identifier(chu)))
        self.conn.execute('''CREATE TABLE mod_demo_nv.nghia_vu(id uuid PRIMARY KEY, phap_nhan_id uuid NOT NULL,
            loai text NOT NULL,pb uuid NOT NULL,bam text NOT NULL,so_tien_minor numeric(38,0) NOT NULL,
            tien_te text NOT NULL DEFAULT 'VND',thang_tien smallint NOT NULL DEFAULT 0,
            khoa integer NOT NULL DEFAULT 0,cho_cuoi boolean NOT NULL DEFAULT false)''')
        self.conn.execute(sql.SQL('ALTER TABLE mod_demo_nv.nghia_vu OWNER TO {}').format(sql.Identifier(chu)))
        self.conn.execute('ALTER TABLE mod_demo_nv.nghia_vu ENABLE ROW LEVEL SECURITY')
        self.conn.execute('ALTER TABLE mod_demo_nv.nghia_vu FORCE ROW LEVEL SECURITY')
        self.conn.execute(sql.SQL('''CREATE POLICY pn ON mod_demo_nv.nghia_vu TO {},{}
            USING(phap_nhan_id IN (SELECT phap_nhan_id FROM loi.mtq_phien_rls()))
            WITH CHECK(phap_nhan_id IN (SELECT phap_nhan_id FROM loi.mtq_phien_rls()))''').format(sql.Identifier(chu),sql.Identifier(kiem)))
        self.conn.execute(sql.SQL('GRANT USAGE ON SCHEMA mod_demo_nv TO {},{}').format(sql.Identifier(kiem),sql.Identifier(core_chu)))
        self.conn.execute(sql.SQL('GRANT SELECT,UPDATE(khoa) ON mod_demo_nv.nghia_vu TO {}').format(sql.Identifier(kiem)))
        for role in (chu, kiem):
            self.conn.execute(sql.SQL('GRANT USAGE ON SCHEMA loi,loi_tai_lieu,danh_muc TO {}').format(sql.Identifier(role)))
            for ck in ('loi.mtq_phien_rls()', 'loi_tai_lieu.ngu_canh(text,text,uuid,text,uuid,bigint)'):
                self.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION '+ck+' TO {}').format(sql.Identifier(role)))
        self.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION loi_tai_lieu.kiem_quyen(text,text,uuid,text,jsonb,text,text,uuid,bigint) TO {}').format(sql.Identifier(chu)))
        for ck in ('khoa_lien_ket_noi_bo(uuid,uuid[])','tong_nghia_vu_noi_bo(uuid,text,text,uuid)'):
            self.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION danh_muc.'+ck+' TO {}').format(sql.Identifier(kiem)))
        self.conn.execute('''CREATE FUNCTION mod_demo_nv.resolver(text,text,uuid,text,jsonb,uuid,bigint)
            RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
            DECLARE n mod_demo_nv.nghia_vu; d jsonb := $5;
            BEGIN
                PERFORM loi_tai_lieu.ngu_canh($1,$2,$3,$4,$6,$7);
                SELECT * INTO n FROM mod_demo_nv.nghia_vu WHERE id=(d->>'nghia_vu_id')::uuid AND phap_nhan_id=$3 FOR UPDATE;
                IF NOT FOUND THEN RETURN jsonb_build_object('ket_luan','CHO'); END IF;
                IF d->>'module_nghia_vu'<>'demo_nv' OR d->>'loai_nghia_vu'<>n.loai
                   OR d->>'phien_ban_can_cu_id'<>n.pb::text OR d->>'ma_bam_phien_ban_can_cu'<>n.bam
                   OR d->>'tien_te'<>n.tien_te OR (d->>'thang_tien')::int<>n.thang_tien THEN
                    RAISE EXCEPTION 'LIEN_KET_CAN_CU' USING ERRCODE='P0001';
                END IF;
                IF d->>'giai_doan'='KIEM' AND danh_muc.tong_nghia_vu_noi_bo($3,'demo_nv',n.loai,n.id)>n.so_tien_minor THEN
                    RAISE EXCEPTION 'LIEN_KET_VUOT_NGHIA_VU' USING ERRCODE='P0001';
                END IF;
                IF d->>'giai_doan'='KIEM' AND n.cho_cuoi THEN
                    RETURN jsonb_build_object('ket_luan','CHO');
                END IF;
                RETURN d || '{"ket_luan":"DAT"}';
            END $$''')
        self.conn.execute(sql.SQL('ALTER FUNCTION mod_demo_nv.'+CK_NV+' OWNER TO {}').format(sql.Identifier(kiem)))
        self.conn.execute('REVOKE ALL ON FUNCTION mod_demo_nv.'+CK_NV+' FROM PUBLIC')
        self.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION mod_demo_nv.'+CK_NV+' TO {}').format(sql.Identifier(core_chu)))
        # Giảm sức chứa gọi cùng khóa PN/chứng từ trước khóa nghĩa vụ.
        self.conn.execute('''CREATE FUNCTION mod_demo_nv.kiem_giam(uuid,uuid,numeric) RETURNS boolean
            LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
            DECLARE n mod_demo_nv.nghia_vu;
            BEGIN
                PERFORM danh_muc.khoa_lien_ket_noi_bo($1);
                SELECT * INTO n FROM mod_demo_nv.nghia_vu WHERE phap_nhan_id=$1 AND id=$2 FOR UPDATE;
                RETURN FOUND AND $3>=0 AND danh_muc.tong_nghia_vu_noi_bo($1,'demo_nv',n.loai,n.id)<=$3;
            END $$''')
        self.conn.execute(sql.SQL('ALTER FUNCTION mod_demo_nv.kiem_giam(uuid,uuid,numeric) OWNER TO {}').format(sql.Identifier(kiem)))
        self.conn.execute('REVOKE ALL ON FUNCTION mod_demo_nv.kiem_giam(uuid,uuid,numeric) FROM PUBLIC')
        self.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION mod_demo_nv.kiem_giam(uuid,uuid,numeric) TO {}').format(sql.Identifier(chu)))
        self.conn.execute('''CREATE FUNCTION mod_demo_nv.giam(text,text,uuid,text,uuid,numeric) RETURNS void
            LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
            BEGIN
                PERFORM loi_tai_lieu.ngu_canh($1,$2,$3,$4,NULL,NULL);
                PERFORM loi_tai_lieu.kiem_quyen($1,$2,$3,$4,jsonb_build_object('bang','mod_demo_nv.nghia_vu','id',$5),
                    '1','cho_ghi',NULL,NULL);
                IF split_part($4,':',3)<>'SUA' OR NOT mod_demo_nv.kiem_giam($3,$5,$6) THEN
                    RAISE EXCEPTION 'LIEN_KET_VUOT_NGHIA_VU' USING ERRCODE='P0001';
                END IF;
                UPDATE mod_demo_nv.nghia_vu SET so_tien_minor=$6 WHERE phap_nhan_id=$3 AND id=$5;
            END $$''')
        self.conn.execute(sql.SQL('ALTER FUNCTION mod_demo_nv.giam(text,text,uuid,text,uuid,numeric) OWNER TO {}').format(sql.Identifier(chu)))
        self.conn.execute('REVOKE ALL ON FUNCTION mod_demo_nv.giam(text,text,uuid,text,uuid,numeric) FROM PUBLIC')
        self.conn.execute(sql.SQL('GRANT USAGE ON SCHEMA mod_demo_nv TO {}').format(sql.Identifier(self.module_login)))
        self.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION mod_demo_nv.giam(text,text,uuid,text,uuid,numeric) TO {}').format(sql.Identifier(self.module_login)))
        self._ghi('ham_module', module='demo_nv', loai_ham='resolver_nghia_vu', phien_ban_contract='1',
            ma_contract=ct, phien_ban_module='1', ten_ham='resolver', chu_ky='mod_demo_nv.'+CK_NV,
            vai_so_huu=kiem, ma_bam_goi='b'*64)
        # Quyền đọc nội dung module cố ý che mọi liên kết, không lọc role kiểm.
        for bang in ('lien_ket_chung_tu','lien_ket_phan_bo'):
            self.conn.execute(sql.SQL('GRANT SELECT ON danh_muc.{} TO {}').format(sql.Identifier(bang),sql.Identifier(self.vai_module)))
            self.conn.execute(sql.SQL('CREATE POLICY noi_dung_bi_che ON danh_muc.{} FOR SELECT TO {} USING(false)').format(sql.Identifier(bang),sql.Identifier(self.vai_module)))

    def _chung_tu(self, id, tien):
        self.conn.execute('''INSERT INTO danh_muc.chung_tu(id,phap_nhan_id,module_nghiep_vu,loai,khoa_nguon,
            ngay_nghiep_vu,ky,so_tien_minor,tien_te,thang_tien,ma_bam,tao_boi)
            VALUES (%s,%s,'m1','SAO_KE',%s,'2026-10-30','2026-10',%s,'VND',0,%s,%s)''',
            (id,self.pn,id.hex,tien,'a'*64,self.nd))

    def _quyen(self, id):
        self.conn.execute('INSERT INTO mod_crm.doi_tuong(id,tap) VALUES (%s,%s::jsonb) ON CONFLICT DO NOTHING',
            (id,json.dumps([dict(pn=str(self.pn),hop_le=True,loai='TIEP_NHAN',so_tien_vnd='0')])))

    def _lap(self, tien='60', conn=None, id=None, data=None, **ctx):
        id = id or uuid4()
        self._quyen(id)
        kn = conn or self.module
        with kn.transaction():
            return lk.tao(kn,lien_ket_id=id,du_lieu={**(data or self.data),'so_tien_khop_minor':tien},
                          **self._ctx(**{'ma':self.uy,**ctx}))

    def _sua(self, id, tien, conn=None):
        kn = conn or self.module
        with kn.transaction():
            return lk.sua(kn,lien_ket_id=id,id_moi=uuid4(),ly_do='DEMO',du_lieu={**self.data,'so_tien_khop_minor':tien},
                          **self._ctx(SUA,ma=self.uy))

    def _huy(self, id, conn=None):
        kn = conn or self.module
        with kn.transaction():
            return lk.huy(kn,lien_ket_id=id,ly_do='DEMO',**self._ctx(HUY,ma=self.uy))

    def _giam(self, tien, conn=None):
        kn = conn or self.module
        with kn.transaction():
            kn.execute('SELECT mod_demo_nv.giam(%s,%s,%s,%s,%s,%s)',
                (self.uy.lay_de_truyen(),'crm',self.pn,SUA,self.nv,tien))

    def _tong(self):
        return self.conn.execute("SELECT coalesce(sum(so_tien_khop_minor),0) FROM danh_muc.lien_ket_chung_tu WHERE phap_nhan_id=%s AND trang_thai<>'HUY'", (self.pn,)).fetchone()[0]

    def _ket_noi_module(self):
        return psycopg.connect(**{**self.cac_thong_tin['core'],'user':self.module_login,
            'password':self.module.info.password},autocommit=True)

    def _bi_che(self, bang='lien_ket_chung_tu'):
        with self.module.transaction():
            self.module.execute("""SELECT set_config('ktt.ma_phien',%s,true),set_config('ktt.module','crm',true),
                set_config('ktt.phap_nhan_id',%s,true),set_config('ktt.hanh_dong',%s,true)""",
                (self.uy.lay_de_truyen(),str(self.pn),LAP))
            self.assertEqual(self.module.execute('SELECT phap_nhan_id FROM loi.mtq_phien_rls()').fetchall(),[(self.pn,)])
            self.assertEqual(self.module.execute('SELECT * FROM danh_muc.'+bang).fetchall(),[])

    def test_a_80_bi_che_them_30_vuot_chung_tu(self):
        a = uuid4()
        self._chung_tu(a,100)
        self.data['chung_tu_a_id'] = str(a)
        self.assertNotIn('m1',self.conn.execute('SELECT module FROM loi.phan_quyen WHERE nguoi_dung_id=%s AND phap_nhan_id=%s',(self.nd,self.pn)).fetchone()[0])
        self._lap('80')
        self._bi_che()
        with self.assertRaises(lk.LoiLienKet) as bat:
            self._lap('30')
        self.assertEqual(bat.exception.ma,'LIEN_KET_VUOT_CHUNG_TU')
        self.assertNotIn('80',str(bat.exception))
        self.assertEqual(self._tong(),80)

    def test_b_80_bi_che_them_30_vuot_nghia_vu(self):
        self._giam(100)
        self._lap('80')
        self._bi_che()
        with self.assertRaises(lk.LoiLienKet) as bat:
            self._lap('30')
        self.assertEqual(bat.exception.ma,'LIEN_KET_VUOT_NGHIA_VU')
        self.assertEqual(self._tong(),80)

    def test_c_60_cong_60_hai_ket_noi_chi_mot_commit(self):
        self._giam(100)
        ids = [uuid4(),uuid4()]
        for id in ids:
            self._quyen(id)
        barrier = threading.Barrier(2)
        def ghi(id):
            # Hai connection thực sự; cùng mã ủy nhiệm gắn đúng login.
            with self._ket_noi_module() as kn:
                kn.execute("SET statement_timeout='10s'")
                barrier.wait(timeout=10)
                try:
                    return self._lap('60',conn=kn,id=id)['ket_luan']
                except lk.LoiLienKet as exc:
                    return exc.ma
        with ThreadPoolExecutor(max_workers=2) as pool:
            kq = list(pool.map(ghi,ids))
        self.assertCountEqual(kq,['DAT','LIEN_KET_VUOT_NGHIA_VU'])
        self.assertEqual(self._tong(),60)

    def test_sua_huy_va_giam_khong_bo_qua_lien_ket(self):
        self._giam(100)
        id = uuid4()
        self._lap('80',id=id)
        with self.assertRaises(psycopg.Error):
            self._giam(70)
        with self.assertRaises(lk.LoiLienKet):
            self._sua(id,'110')
        self.assertEqual(self._tong(),80)
        moi = self._sua(id,'60')['id']
        self.assertEqual(self._tong(),60)
        self._giam(60)
        self._quyen(moi)
        self._huy(moi)
        self._giam(0)
        self.assertEqual(self._tong(),0)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM danh_muc.lien_ket_chung_tu WHERE phap_nhan_id=%s AND trang_thai=\'HUY\'',(self.pn,)).fetchone()[0],2)

    def test_sua_huy_giam_va_tao_dong_thoi_giu_cung_thu_tu_khoa(self):
        self._giam(100)
        id = uuid4()
        self._lap('80',id=id)
        with self._ket_noi_module() as kn:
            # SUA giu khoa den commit ngoai, giam phai doi dung khoa nay.
            with self.module.transaction():
                moi = self._sua(id,'60')['id']
                with self.assertRaises(psycopg.errors.LockNotAvailable),kn.transaction():
                    kn.execute("SET LOCAL lock_timeout='150ms'")
                    self._giam(50,conn=kn)
            with self.assertRaises(psycopg.Error):
                self._giam(50,conn=kn)
            self.assertEqual(self._tong(),60)
            # HUY va LAP cung chung giao thuc; khong co khoa nguoc nghia vu -> chung tu.
            self._quyen(moi)
            them = uuid4()
            self._quyen(them)
            with self.module.transaction():
                self._huy(moi)
                with self.assertRaises(psycopg.errors.LockNotAvailable),kn.transaction():
                    kn.execute("SET LOCAL lock_timeout='150ms'")
                    kn.execute('SELECT danh_muc.lien_ket_v2(%s,%s,%s,%s,%s,%s,%s::jsonb)',
                        (self.uy.lay_de_truyen(),'crm',self.pn,LAP,'LAP',them,json.dumps(self.data)))
            self._lap('60',conn=kn,id=them)
            # Giam lay khoa truoc, tao cung phai doi va doc suc chua moi sau commit.
            with kn.transaction():
                self._giam(60,conn=kn)
                with self.assertRaises(lk.LoiLienKet),self.module.transaction():
                    self.module.execute("SET LOCAL lock_timeout='150ms'")
                    self._lap('10')
            with self.assertRaises(lk.LoiLienKet):
                self._lap('10')
        self.assertEqual(self._tong(),60)

    def test_child_cong_direct_khong_dem_parent_hai_lan(self):
        self._giam(100)
        con = {k:v for k,v in self.data.items() if k in lk._DICH}
        con.update(dich_logic_id=str(uuid4()),cau_phan='GOC',so_tien_minor='80')
        child = {k:v for k,v in self.data.items() if k not in lk._DICH|{'so_tien_khop_minor'}}
        child.update(mo_hinh_phan_bo='CHILD',phan_bo=[con])
        id = uuid4()
        self._quyen(id)
        with self.module.transaction():
            self.assertEqual(lk.tao(self.module,lien_ket_id=id,du_lieu=child,**self._ctx(ma=self.uy))['ket_luan'],'DAT')
        self._bi_che('lien_ket_phan_bo')
        self._lap('20')
        with self.assertRaises(lk.LoiLienKet) as bat:
            self._lap('1')
        self.assertEqual(bat.exception.ma,'LIEN_KET_VUOT_NGHIA_VU')
        self._huy(id)
        self._giam(20)
        self.assertEqual(self.conn.execute("SELECT trang_thai FROM danh_muc.lien_ket_phan_bo WHERE lien_ket_id=%s",(id,)).fetchone()[0],'HUY')

    def test_cho_o_kiem_cuoi_rollback_ca_huy_cu_va_them_moi(self):
        id = uuid4()
        self._lap('80',id=id)
        self.conn.execute('UPDATE mod_demo_nv.nghia_vu SET cho_cuoi=true WHERE id=%s',(self.nv,))
        kq = self._sua(id,'60')
        self.assertEqual(kq['ket_luan'],'CHO')
        self.assertEqual(self._tong(),80)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM danh_muc.lien_ket_chung_tu WHERE phap_nhan_id=%s',(self.pn,)).fetchone()[0],1)
        self.assertEqual(self.conn.execute('SELECT trang_thai FROM danh_muc.lien_ket_chung_tu WHERE id=%s',(id,)).fetchone()[0],'DA_KHOP')

    def test_resolver_mat_va_module_tat_cho_khong_ghi(self):
        self.conn.execute('ALTER FUNCTION mod_demo_nv.'+CK_NV+' RENAME TO resolver_tam_ngung')
        try:
            kq = self._lap()
            self.assertEqual(kq['ket_luan'],'CHO')
        finally:
            self.conn.execute('ALTER FUNCTION mod_demo_nv.resolver_tam_ngung(text,text,uuid,text,jsonb,uuid,bigint) RENAME TO resolver')
        cong_tac.doi_che_do(self.core,ma=self._cap(module='core',hd=['CORE:MODULE:SUA']),
            module='demo_nv',phap_nhan_id=self.pn,payload=dict(row_version='2',che_do='TAT',nguoi_thu_ids=[]),request_id=uuid4())
        self.assertEqual(self._lap()['ket_luan'],'CHO')
        self.assertEqual(self._tong(),0)

    def test_rollback_transaction_ngoai_va_tu_choi_snapshot_cu(self):
        id = uuid4()
        with self.assertRaisesRegex(RuntimeError,'DEMO_ROLLBACK'),self.module.transaction():
            self._lap('60',id=id)
            raise RuntimeError('DEMO_ROLLBACK')
        self.assertEqual(self._tong(),0)
        with self.assertRaises(lk.LoiLienKet) as bat,self.module.transaction():
            self.module.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            self._lap('60',id=id)
        self.assertEqual(bat.exception.ma,'LIEN_KET_CAN_READ_COMMITTED')

    def test_chuoi_sql_tang_va_ap_lai_khong_noi_quyen(self):
        tep = sorted(dc.THU_MUC_SQL.glob('[0-9][0-9][0-9]_*.sql'),key=lambda p:int(p.name.split('_')[0]))
        self.assertEqual(dc.ap_doi_cau_truc(self.conn,tep),13)
        self.conn.execute(SQL)
        self.assertEqual(self.conn.execute("SELECT max(so_phien_ban) FROM loi.lich_su_doi_cau_truc WHERE ma_goi='core'").fetchone()[0],13)

    def test_b_la_chung_tu_can_cu_khong_tru_tien_hai_lan(self):
        b = uuid4()
        self.conn.execute('''INSERT INTO danh_muc.chung_tu(id,phap_nhan_id,module_nghiep_vu,loai,khoa_nguon,
            ngay_nghiep_vu,ky,ma_bam,tao_boi) VALUES (%s,%s,'crm','HOP_DONG_TEP',%s,'2026-10-30','2026-10',%s,%s)''',
            (b,self.pn,b.hex,'a'*64,self.nd))
        self.assertEqual(self._lap('80',data={**self.data,'chung_tu_b_id':str(b)})['ket_luan'],'DAT')
        self.assertEqual(self._tong(),80)

    def test_module_resolver_can_cu_thieu_cho_khong_ghi(self):
        for doi in ({'module_nghia_vu':'chua_cai'}, {'nghia_vu_id':str(uuid4())}):
            kq = self._lap(data={**self.data,**doi})
            self.assertEqual(kq['ket_luan'],'CHO')
            self.assertTrue(kq['ly_do'])
        self.assertEqual(self._tong(),0)
        with self.assertRaises(lk.LoiLienKet) as bat:
            self._lap(data={**self.data,'ma_bam_phien_ban_can_cu':'c'*64})
        self.assertEqual(bat.exception.ma,'LIEN_KET_CAN_CU')
        self.assertEqual(self._tong(),0)

    def test_sai_phien_pn_quyen_va_don_vi_khong_ghi(self):
        for ctx in ({'ma':phien.MaBiMat('GIA'*24)}, {'phap_nhan_id':self.pn_khac}):
            with self.subTest(ctx=ctx), self.assertRaises(lk.LoiLienKet):
                self._lap(**ctx)
        khong_quyen = self._cap(hd=[XEM])
        with self.assertRaises(lk.LoiLienKet):
            self._lap(conn=self.core,ma=khong_quyen)
        with self.assertRaises(lk.LoiLienKet):
            self._lap(data={**self.data,'tien_te':'USD'})
        self.assertEqual(self._tong(),0)

    def test_phien_hop_le_nhung_mtq_khong_cap_hanh_dong(self):
        nd = uuid4()
        self.conn.execute("INSERT INTO loi.nguoi_dung(id,dang_nhap,ten,vai_tro) VALUES (%s,%s,'DEMO','XEM')",(nd,'demo_'+nd.hex))
        self.conn.execute('INSERT INTO loi.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,%s)',(nd,self.pn,['crm']))
        ma = phien.cap_phien(self.core,nguoi_dung_id=nd,module='crm',phap_nhan_id=self.pn,
            dang_nhap_csdl=self.cac_thong_tin['core']['user'],pham_vi_hanh_dong=[LAP],
            hieu_luc_den=datetime.now(timezone.utc)+timedelta(minutes=4)).ma
        with self.assertRaises(lk.LoiLienKet) as bat:
            self._lap(conn=self.core,ma=ma)
        self.assertEqual(bat.exception.ma,'TAI_LIEU_MTQ')
        self.assertEqual(self._tong(),0)

    def test_runtime_khong_dml_tong_noi_bo_fk_va_vai_kiem(self):
        self.assertEqual(self.module.execute('SELECT current_user,session_user').fetchone(),(self.module_login,)*2)
        for kn in (self.core,self.module):
            for bang in ('lien_ket_chung_tu','lien_ket_phan_bo'):
                with self.subTest(bang=bang),self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    kn.execute('INSERT INTO danh_muc.'+bang+' DEFAULT VALUES')
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                kn.execute('SELECT danh_muc.tong_nghia_vu_noi_bo(%s,%s,%s,%s)',(self.pn,'demo_nv','DOT',self.nv))
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                kn.execute('SELECT danh_muc.khoa_lien_ket_noi_bo(%s)',(self.pn,))
        kiem = self.tien_to+'vai_kiem_toan_ven_danh_muc'
        self.assertEqual(self.conn.execute('SELECT rolcanlogin,rolbypassrls,rolsuper FROM pg_roles WHERE rolname=%s',(kiem,)).fetchone(),(False,False,False))
        self.assertEqual(self.conn.execute('SELECT count(*) FROM pg_auth_members WHERE roleid=(SELECT oid FROM pg_roles WHERE rolname=%s)',(kiem,)).fetchone()[0],0)
        self.assertFalse(self.conn.execute("SELECT has_table_privilege(%s,'danh_muc.chung_tu','INSERT,UPDATE,DELETE')",(kiem,)).fetchone()[0])
        self.assertEqual(self.conn.execute("""SELECT count(*) FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
            JOIN pg_namespace n ON n.oid=t.relnamespace JOIN pg_class d ON d.oid=c.confrelid
            JOIN pg_namespace nd ON nd.oid=d.relnamespace WHERE n.nspname='danh_muc' AND c.contype='f'
              AND nd.nspname LIKE 'mod_%'""").fetchone()[0],0)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM pg_class WHERE oid=ANY(ARRAY['danh_muc.chung_tu'::regclass,'danh_muc.lien_ket_chung_tu'::regclass,'danh_muc.lien_ket_phan_bo'::regclass]) AND relrowsecurity AND relforcerowsecurity").fetchone()[0],3)


if __name__ == '__main__':
    unittest.main()
