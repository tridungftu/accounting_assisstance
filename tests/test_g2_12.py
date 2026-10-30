"""G2-12: thuần/mock và PG opt-in trên kho_test_*; nghiệp vụ bằng login thật.

Không khởi động/dừng dịch vụ, không DROP/cleanup CSDL/role. Fixture admin
chỉ provisioning quyền/resolver và dữ liệu giả, không chạy ca nghiệp vụ.
"""

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
import traceback
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import danh_muc as dm, doi_cau_truc as dc, phien

try:
    from . import test_g2_09 as g209
except ImportError:
    import test_g2_09 as g209

psycopg = g209.psycopg
if psycopg is not None:
    from psycopg import sql

SQL_PATH = dc.THU_MUC_SQL / '012_danh_muc.sql'
SQL = SQL_PATH.read_text(encoding='utf-8')
LAP, SUA, XEM, DUYET = g209.LAP, g209.SUA, g209.XEM, g209.DUYET
KHOA = 'demo-g2-12-000001'
CT = dict(loai='KHAC', khoa_nguon='DEMO', ngay_nghiep_vu='2026-10-30', ma_bam='a'*64,
          so_tien_minor='900719925474099312345', tien_te='VND', thang_tien=0)
BANG = ('doi_tac', 'du_an', 'tai_khoan', 'tai_khoan_ngan_hang', 'hop_dong', 'chung_tu',
        'hoa_don_danh_tinh', 'khoa_ky', 'lien_ket_chung_tu', 'lien_ket_phan_bo')
CK_GHI = 'ghi_v2(text,text,uuid,text,text,uuid,text,jsonb,text,uuid,bigint)'
CK_KIEM = 'kiem_khoa_ky_v2(text,text,uuid,text,uuid,text,uuid,bigint)'


class DanhMucThuanTest(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.conn.info.transaction_status = 2
        self.ctx = dict(ma=phien.MaBiMat('CANARY_PHIEN'), module='crm',
                        phap_nhan_id=uuid4(), hanh_dong=LAP)
        self.ts = dict(doi_tuong_id=uuid4(), khoa=KHOA, du_lieu=dict(CT), **self.ctx)

    def test_bind_tien_chinh_xac_va_giu_transaction_caller(self):
        dm.ghi_chung_tu(self.conn, **self.ts)
        cau, ts = self.conn.execute.call_args.args
        self.assertNotIn('CANARY', cau)
        self.assertIn('danh_muc.ghi_v2', cau)
        self.assertEqual(ts[:4], ('CANARY_PHIEN', 'crm', self.ctx['phap_nhan_id'], LAP))
        self.assertEqual(json.loads(ts[7])['so_tien_minor'], CT['so_tien_minor'])
        for ten in ('connect', 'commit', 'rollback', 'transaction'):
            getattr(self.conn, ten).assert_not_called()

    def test_bat_buoc_transaction(self):
        for trang_thai in (0, 1, 3, 4):
            self.conn.info.transaction_status = trang_thai
            with self.subTest(trang_thai=trang_thai), self.assertRaises(ValueError):
                dm.ghi_chung_tu(self.conn, **self.ts)
        self.conn.execute.assert_not_called()

    def test_tien_thieu_khong_thanh_0_va_chan_float(self):
        for doi in ({'so_tien_minor': 1.1}, {'so_tien_minor': True}, {'so_tien_minor': '1.2'},
                    {'so_tien_minor': '-1'}, {'so_tien_minor': '9'*39}, {'thang_tien': True},
                    {'thang_tien': 13}, {'tien_te': None}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                dm.ghi_chung_tu(self.conn, **{**self.ts, 'du_lieu': {**CT, **doi}})
        thieu = {k: v for k, v in CT.items() if k not in {'so_tien_minor', 'tien_te', 'thang_tien'}}
        dm.ghi_chung_tu(self.conn, **{**self.ts, 'du_lieu': thieu})
        self.assertNotIn('so_tien_minor', json.loads(self.conn.execute.call_args.args[1][7]))

    def test_khong_nhan_trang_thai_rieng_actor_hoac_ky_tu_khai(self):
        for ten in ('trang_thai', 'module_nghiep_vu', 'tao_boi', 'ky', 'du_lieu', 'chung_tu_dong'):
            with self.subTest(ten=ten), self.assertRaises(ValueError):
                dm.ghi_chung_tu(self.conn, **{**self.ts, 'du_lieu': {**CT, ten: 'GIA'}})
        with self.assertRaises(TypeError):
            dm.ghi_chung_tu(self.conn, actor=uuid4(), **self.ts)
        with self.assertRaises(ValueError):
            dm.ghi(self.conn, loai='lien_ket_chung_tu', **self.ts)
        self.conn.execute.assert_not_called()

    def test_ngay_khoa_phien_hanh_dong_khong_hop_le(self):
        for doi in ({'ma': 'GIA'}, {'khoa': 'ngan'}, {'hanh_dong': XEM},
                    {'du_lieu': {**CT, 'ngay_nghiep_vu': '2026-02-30'}},
                    {'du_lieu': {**CT, 'ngay_nghiep_vu': '2026-10-30T00:00:00'}}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                dm.ghi_chung_tu(self.conn, **{**self.ts, **doi})
        self.conn.execute.assert_not_called()

    def test_cac_cua_ghi_va_het_hieu_luc_cas(self):
        ca = [(dm.ghi_doi_tac, dict(ten_phap_ly='DEMO', ten_chuan_hoa='demo', loai='TC'), 'doi_tac'),
              (dm.ghi_du_an, dict(ma_junsky='DEMO', ten='DEMO'), 'du_an'),
              (dm.ghi_hop_dong, dict(loai='KHAC', ma_noi_bo='DEMO', so_hop_dong='DEMO'), 'hop_dong'),
              (dm.ghi_hoa_don_danh_tinh, dict(chieu='MUA_VAO', mst_ban='DEMO', mau_so='1',
                    ky_hieu='DEMO', so_chuan='1', nguon_cai_dat_id='DEMO'), 'hoa_don_danh_tinh')]
        for ham, data, loai in ca:
            ham(self.conn, **{**self.ts, 'du_lieu': data})
            self.assertEqual(self.conn.execute.call_args.args[1][4], loai)
        ts = {k: v for k, v in self.ts.items() if k != 'du_lieu'}
        dm.het_hieu_luc(self.conn, loai='chung_tu', row_version='1', **{**ts, 'hanh_dong': SUA})
        self.assertEqual(json.loads(self.conn.execute.call_args.args[1][7]), {'row_version': '1'})
        with self.assertRaises(ValueError):
            dm.het_hieu_luc(self.conn, loai='chung_tu', row_version=1, **{**ts, 'hanh_dong': SUA})

    def test_nhom_a_khong_duoc_ghi_ban_ro(self):
        for doi in ({'loai': 'CN', 'mst': 'DEMO'}, {'cccd_mh': 'DEMO'}, {'stk': 'DEMO'}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                dm.ghi_doi_tac(self.conn, **{**self.ts, 'du_lieu':
                    {**dict(ten_phap_ly='DEMO', ten_chuan_hoa='demo', loai='TC'), **doi}})

    def test_khoa_ky_va_adapter_dung_cua(self):
        ts = {k: v for k, v in self.ts.items() if k != 'du_lieu'}
        dm.khoa_ky(self.conn, ky='2026-10', **{**ts, 'hanh_dong': DUYET})
        self.assertEqual(self.conn.execute.call_args.args[1][4], 'khoa_ky')
        dm.kiem_khoa_ky(self.conn, chung_tu_id=self.ts['doi_tuong_id'], **self.ctx)
        self.assertIn('kiem_khoa_ky_v2', self.conn.execute.call_args.args[0])
        with self.assertRaises(ValueError):
            dm.khoa_ky(self.conn, ky='2026-13', **{**ts, 'hanh_dong': DUYET})

    def test_loi_khong_lo_token_dsn_hoac_stack_driver(self):
        for ma, status in (('KY_DA_KHOA', 409), ('BIEN_NHAN_KHONG_THAY', 404), ('TAI_LIEU_MTQ', 403)):
            loi = RuntimeError('CANARY_PHIEN postgresql://CANARY:BI_MAT@localhost')
            loi.diag = MagicMock(message_primary=ma)
            self.conn.execute.side_effect = loi
            with self.assertRaises(dm.LoiDanhMuc) as bat:
                dm.ghi_chung_tu(self.conn, **self.ts)
            self.assertEqual(bat.exception.http_status, status)
            self.assertIsNone(bat.exception.__context__)
            self.assertNotIn('CANARY', ''.join(traceback.format_exception(bat.exception)))

    def test_ddl_khong_phu_thuoc_module_va_dollar_quote(self):
        moc = re.findall(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', SQL)
        self.assertEqual((moc[0], moc[-1]), ('$$', '$$'))
        self.assertTrue(all(a == b for a, b in zip(moc[1:-1:2], moc[2:-1:2])))
        self.assertEqual(len(moc) % 2, 0)
        self.assertNotRegex(SQL, r'(?i)(?:REFERENCES|FROM|JOIN)\s+(?:mod_|master\.|kho\.)')
        self.assertNotRegex(SQL, r'(?i)\bDROP\s+(?:TABLE|FUNCTION|DATABASE|ROLE)')
        self.assertFalse(SQL_PATH.read_bytes().startswith(b'\xef\xbb\xbf'))


@unittest.skipUnless(psycopg is not None and os.environ.get('KHO_PG_DSN_TEST'),
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class DanhMucPostgresTest(unittest.TestCase):
    _ghi = g209.TaiLieuPostgresTest._ghi
    _contract = g209.TaiLieuPostgresTest._contract
    _trang_thai = g209.TaiLieuPostgresTest._trang_thai
    _resolver = g209.TaiLieuPostgresTest._resolver
    _cap = g209.TaiLieuPostgresTest._cap
    _ctx = g209.TaiLieuPostgresTest._ctx
    _tao = g209.TaiLieuPostgresTest._tao

    @classmethod
    def setUpClass(cls):
        g209.TaiLieuPostgresTest.setUpClass.__func__(cls)
        cls.tep_sql = sorted(dc.THU_MUC_SQL.glob('[0-9][0-9][0-9]_*.sql'),
                             key=lambda tep: int(tep.name.split('_', 1)[0]))
        dc.ap_doi_cau_truc(cls.conn, cls.tep_sql)
        cls.vai_module = cls.tien_to + 'vai_chay_mod_crm'
        cls.conn.execute(sql.SQL('GRANT USAGE ON SCHEMA danh_muc TO {}').format(sql.Identifier(cls.vai_module)))
        for ck in (CK_GHI, CK_KIEM):
            cls.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION danh_muc.'+ck+' TO {}').format(sql.Identifier(cls.vai_module)))

    def setUp(self):
        g209.TaiLieuPostgresTest.setUp(self)
        self.uy = phien.cap_phien(self.core, nguoi_dung_id=self.nd, module='crm', phap_nhan_id=self.pn,
            dang_nhap_csdl=self.module_login, pham_vi_hanh_dong=[LAP, SUA, XEM, DUYET], loai='UY_NHIEM_PHIEN',
            ma_goc=self.ma, hieu_luc_den=datetime.now(timezone.utc)+timedelta(minutes=4)).ma
        self.ts = dict(doi_tuong_id=self.obj, khoa=KHOA, du_lieu=dict(CT), **self._ctx(ma=self.uy))

    def _chung_tu(self, conn=None, **doi):
        conn = conn or self.module
        with conn.transaction():
            return dm.ghi_chung_tu(conn, **{**self.ts, **doi})

    def _khoa(self, conn=None, **doi):
        conn = conn or self.module
        with conn.transaction():
            return dm.khoa_ky(conn, ky='2026-10', doi_tuong_id=self.obj, khoa='demo-g2-12-khoa01',
                **self._ctx(DUYET, **{'ma': self.uy, **doi}))

    def test_ap_day_du_chuoi_sql_theo_thu_tu_so(self):
        chuoi = dc._doc_chuoi(self.tep_sql)
        self.assertEqual(self.conn.execute('''SELECT so_phien_ban, ma_bam
            FROM loi.lich_su_doi_cau_truc WHERE ma_goi='core'
            ORDER BY so_phien_ban''').fetchall(),
            [(so, bam) for so, (_, bam) in chuoi.items()])
        self.assertEqual(dc.ap_doi_cau_truc(self.conn, self.tep_sql), max(chuoi))

    def test_ghi_module_login_that_va_replay_khac_noi_dung(self):
        self.assertEqual(self.module.execute('SELECT current_user,session_user').fetchone(), (self.module_login,)*2)
        dau, lap = self._chung_tu(), self._chung_tu()
        self.assertFalse(dau['lap_lai'])
        self.assertTrue(lap['lap_lai'])
        self.assertEqual(dau['ket_qua'], lap['ket_qua'])
        with self.assertRaises(dm.LoiDanhMuc) as bat:
            self._chung_tu(du_lieu={**CT, 'so_tien_minor': '1'})
        self.assertEqual(bat.exception.ma, 'KHOA_CHONG_TRUNG_KHAC_NOI_DUNG')
        self.assertEqual(self.conn.execute('SELECT so_tien_minor FROM danh_muc.chung_tu WHERE id=%s', (self.obj,)).fetchone()[0], int(CT['so_tien_minor']))

    def test_ghi_core_dung_bien_nhan_core_cung_commit(self):
        self._chung_tu(self.core, ma=self.ma)
        self.assertTrue(self._chung_tu(self.core, ma=self.ma)['lap_lai'])
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi_tai_lieu.bien_nhan_core WHERE phap_nhan_id=%s', (self.pn,)).fetchone()[0], 1)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi_tai_lieu.bien_nhan_thao_tac WHERE phap_nhan_id=%s', (self.pn,)).fetchone()[0], 0)

    def test_khoa_ky_chan_them_het_hieu_luc_va_adapter(self):
        self._chung_tu()
        self._khoa()
        # Phát lại tác động cũ sau khóa không tạo ghi mới.
        self.assertTrue(self._chung_tu()['lap_lai'])
        with self.assertRaises(dm.LoiDanhMuc) as bat:
            self._chung_tu(khoa='demo-g2-12-them01')
        self.assertEqual(bat.exception.ma, 'KY_DA_KHOA')
        with self.assertRaises(dm.LoiDanhMuc) as bat, self.module.transaction():
            dm.het_hieu_luc(self.module, loai='chung_tu', doi_tuong_id=self.obj,
                khoa='demo-g2-12-het001', row_version='1', **self._ctx(SUA, ma=self.uy))
        self.assertEqual(bat.exception.ma, 'KY_DA_KHOA')
        with self.assertRaises(dm.LoiDanhMuc) as bat, self.module.transaction():
            dm.kiem_khoa_ky(self.module, chung_tu_id=self.obj, **self._ctx(DUYET, ma=self.uy))
        self.assertEqual(bat.exception.ma, 'KY_DA_KHOA')

    def test_sai_phap_nhan_va_thieu_quyen_hien_hanh_bi_chan(self):
        self._chung_tu()
        with self.assertRaises(dm.LoiDanhMuc):
            self._chung_tu(phap_nhan_id=self.pn_khac)
        # Fixture resolver trả TU_CHOI; không giả định owner có quyền nghiệp vụ.
        self.conn.execute('UPDATE mod_crm.doi_tuong SET tap=%s::jsonb WHERE id=%s',
            (json.dumps([dict(pn=str(self.pn), hop_le=False, loai='TIEP_NHAN', so_tien_vnd='0')]), self.obj))
        with self.assertRaises(dm.LoiDanhMuc):
            self._chung_tu()

    def test_runtime_khong_dml_bang_va_khong_goi_ham_noi_bo(self):
        for conn in (self.core, self.module):
            for bang in BANG:
                with self.subTest(bang=bang, login=conn.info.user), self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    conn.execute(sql.SQL('INSERT INTO danh_muc.{} DEFAULT VALUES').format(sql.Identifier(bang)))
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute('SELECT danh_muc.kiem_khoa_ky(%s,%s)', (self.pn, '2026-10'))

    def test_cac_dinh_danh_va_het_hieu_luc_khong_xoa(self):
        ts = {k: v for k, v in self.ts.items() if k != 'du_lieu'}
        with self.module.transaction():
            dm.ghi_doi_tac(self.module, du_lieu=dict(ten_phap_ly='DEMO', ten_chuan_hoa='demo', loai='TC'), **ts)
            dm.ghi_du_an(self.module, du_lieu=dict(ma_junsky='DEMO', ten='DEMO'), **ts)
            dm.ghi_hop_dong(self.module, du_lieu=dict(loai='KHAC', ma_noi_bo='DEMO', so_hop_dong='DEMO',
                doi_tac_id=str(self.obj), du_an_id=str(self.obj)), **ts)
        self.conn.execute("INSERT INTO loi.nguon_cai_dat(id) VALUES (%s)", ('DEMO_'+self.obj.hex,))
        with self.module.transaction():
            dm.ghi_hoa_don_danh_tinh(self.module, du_lieu=dict(chieu='MUA_VAO', mst_ban='DEMO', mau_so='1',
                ky_hieu='DEMO', so_chuan='1', nguon_cai_dat_id='DEMO_'+self.obj.hex), **ts)
        with self.module.transaction():
            kq = dm.het_hieu_luc(self.module, loai='doi_tac', doi_tuong_id=self.obj,
                khoa='demo-g2-12-het001', row_version='1', **self._ctx(SUA, ma=self.uy))
        self.assertEqual(kq['ket_qua']['row_version'], '2')
        self.assertIsNotNone(self.conn.execute('SELECT hieu_luc_den FROM danh_muc.doi_tac WHERE id=%s', (self.obj,)).fetchone()[0])
        with self.assertRaises(dm.LoiDanhMuc) as bat, self.module.transaction():
            dm.het_hieu_luc(self.module, loai='doi_tac', doi_tuong_id=self.obj,
                khoa='demo-g2-12-het002', row_version='1', **self._ctx(SUA, ma=self.uy))
        self.assertEqual(bat.exception.ma, 'DANH_MUC_XUNG_DOT')

    def test_fk_cung_pn_va_catalog_khong_fk_module_force_rls(self):
        self.assertEqual(self.conn.execute('''SELECT count(*) FROM pg_constraint c
            JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace
            JOIN pg_class d ON d.oid=c.confrelid JOIN pg_namespace dn ON dn.oid=d.relnamespace
            WHERE n.nspname='danh_muc' AND c.contype='f' AND dn.nspname NOT IN ('loi','loi_tai_lieu','danh_muc')''').fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM pg_class WHERE relnamespace='danh_muc'::regnamespace AND relkind='r' AND relrowsecurity AND relforcerowsecurity").fetchone()[0], len(BANG))
        # Cha dự án pháp nhân khác chỉ là fixture; nghiệp vụ vẫn qua runtime V2.
        cha = uuid4()
        self.conn.execute("INSERT INTO danh_muc.du_an(id,phap_nhan_id,ma_junsky,ten,tao_boi) VALUES (%s,%s,'DEMO','DEMO',%s)", (cha, self.pn_khac, self.nd))
        with self.assertRaises(dm.LoiDanhMuc), self.module.transaction():
            dm.ghi_du_an(self.module, **{**self.ts, 'du_lieu': dict(ma_junsky='DEMO', ten='DEMO', cha_id=str(cha))})

    def test_rollback_ca_nghiep_vu_va_bien_nhan(self):
        with self.assertRaisesRegex(RuntimeError, 'DEMO_ROLLBACK'), self.module.transaction():
            dm.ghi_chung_tu(self.module, **self.ts)
            raise RuntimeError('DEMO_ROLLBACK')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM danh_muc.chung_tu WHERE id=%s', (self.obj,)).fetchone()[0], 0)
        self.assertFalse(self._chung_tu()['lap_lai'])

    def test_khoa_ky_doi_ghi_dang_mo_va_nguoc_lai(self):
        # Hai kết nối login Core thật; lock_timeout kiểm đang chờ khóa xact.
        with psycopg.connect(**self.cac_thong_tin['core'], autocommit=True) as khac:
            with self.core.transaction():
                dm.ghi_chung_tu(self.core, **{**self.ts, 'ma': self.ma})
                with self.assertRaises(psycopg.errors.LockNotAvailable), khac.transaction():
                    khac.execute("SET LOCAL lock_timeout='150ms'")
                    khac.execute('SELECT danh_muc.ghi_v2(%s,%s,%s,%s,%s,%s,%s,%s::jsonb)',
                        (self.ma.lay_de_truyen(), 'crm', self.pn, DUYET, 'khoa_ky', self.obj,
                         'demo-g2-12-khoa01', json.dumps({'ky': '2026-10'})))
            with self.core.transaction():
                self._khoa(self.core, ma=self.ma)
                with self.assertRaises(psycopg.errors.LockNotAvailable), khac.transaction():
                    khac.execute("SET LOCAL lock_timeout='150ms'")
                    khac.execute('SELECT danh_muc.ghi_v2(%s,%s,%s,%s,%s,%s,%s,%s::jsonb)',
                        (self.ma.lay_de_truyen(), 'crm', self.pn, LAP, 'chung_tu', self.obj,
                         'demo-g2-12-them02', json.dumps(CT)))
            with self.assertRaises(dm.LoiDanhMuc) as bat:
                self._chung_tu(khac, ma=self.ma, khoa='demo-g2-12-them02')
            self.assertEqual(bat.exception.ma, 'KY_DA_KHOA')


if __name__ == '__main__':
    unittest.main()
