"""G2-05: mock + PG16 với LOGIN cài đặt/Core thật, không DROP/dịch vụ.

PG tự tạo kho_test_* và role có tiền tố; lead giữ tài nguyên để đối soát.
Admin chỉ provisioning DDL/fixture, mọi ca registry chạy bằng LOGIN thật.
Không cài thư viện, không đọc cấu hình/bí mật ngoài KHO_PG_DSN_TEST.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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
from kho_tri_thuc.core import dang_ky as dk, doi_cau_truc as dc, phien

try:
    from .test_g2_01 import _kiem_dich_test, psycopg
except ImportError:
    from test_g2_01 import _kiem_dich_test, psycopg

if psycopg is not None:
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict

ADMIN_DSN = os.environ.get('KHO_PG_DSN_TEST')
SQL_PATH = dc.THU_MUC_SQL / '005_dang_ky.sql'
SQL_DANG_KY = SQL_PATH.read_text(encoding='utf-8')
CAC_TEP = sorted(dc.THU_MUC_SQL.glob('[0-9][0-9][0-9]_*.sql'))[:5]
CAC_BANG = ('module_danh_muc', 'phien_ban_module', 'engine_dinh_nghia',
            'dang_ky_contract', 'module_dung_contract', 'dang_ky_ham_module')
BAM = 'a' * 64


class DangKyThuanTest(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.conn.execute.return_value.fetchone.return_value = (uuid4(),)

    def test_ghi_bind_json_khong_noi_sql_va_khong_commit(self):
        du_lieu = dict(ma="demo'); SELECT 1; --", ten='DEMO tiếng Việt')
        dk.ghi_dang_ky(self.conn, loai='module', du_lieu=du_lieu)
        cau_sql, tham_so = self.conn.execute.call_args.args
        self.assertNotIn(du_lieu['ma'], cau_sql)
        self.assertEqual(tham_so[0], 'module')
        self.assertEqual(json.loads(tham_so[1]), du_lieu)
        for ten in ('commit', 'rollback', 'transaction'):
            getattr(self.conn, ten).assert_not_called()

    def test_tu_choi_loai_va_actor_sql(self):
        for loai in (None, [], 'loi.module_danh_muc', 'DROP'):
            with self.subTest(loai=loai), self.assertRaises(ValueError):
                dk.ghi_dang_ky(self.conn, loai=loai, du_lieu={})
        for khoa in ('actor', 'nguoi_dung_id', 'dang_nhap_csdl', 'sql'):
            with self.subTest(khoa=khoa), self.assertRaises(ValueError):
                dk.ghi_dang_ky(self.conn, loai='module', du_lieu={khoa: 'GIA'})
        self.conn.execute.assert_not_called()

    def test_tu_choi_json_khong_hop_le(self):
        for du_lieu in ([], None, {'so': float('nan')}):
            with self.subTest(du_lieu=du_lieu), self.assertRaises((ValueError, TypeError)):
                dk.ghi_dang_ky(self.conn, loai='module', du_lieu=du_lieu)
        self.conn.execute.assert_not_called()

    def test_doc_chi_qua_ham(self):
        self.conn.execute.return_value.fetchone.return_value = ([],)
        self.assertEqual(dk.doc_dang_ky(self.conn, loai='module'), [])
        self.conn.execute.assert_called_once_with('SELECT loi.doc_dang_ky(%s, %s)', ('module', None))
        for loai, ma in (('sql', None), ('module', ''), ('module', 1)):
            with self.subTest(loai=loai, ma=ma), self.assertRaises(ValueError):
                dk.doc_dang_ky(self.conn, loai=loai, ma=ma)

    def test_chuyen_trang_thai_khong_tu_them_bang_chung(self):
        dk.chuyen_trang_thai_contract(self.conn, ma='demo', phien_ban='1', trang_thai='dang_dung')
        loai, noi_dung = self.conn.execute.call_args.args[1]
        self.assertEqual(loai, 'trang_thai_contract')
        self.assertNotIn('bang_chung_duyet', json.loads(noi_dung))
        with self.assertRaises(ValueError):
            dk.chuyen_trang_thai_contract(self.conn, ma='demo', phien_ban='1', trang_thai='duyet_admin')

    def _phan_giai(self, **doi):
        tham_so = dict(module='demo', loai_ham='resolver_mtq', phien_ban_contract='1',
                       ma=phien.MaBiMat('CANARY_PHIEN'), phap_nhan_id=uuid4(), hanh_dong='DOC')
        tham_so.update(doi)
        return dk.phan_giai_ham_module(self.conn, **tham_so)

    def test_phan_giai_cho_va_bind_phien_khong_actor(self):
        self.conn.execute.return_value.fetchone.return_value = ({'ket_luan': 'CHO'},)
        self.assertEqual(self._phan_giai(), {'ket_luan': 'CHO'})
        cau_sql, tham_so = self.conn.execute.call_args.args
        self.assertNotIn('CANARY_PHIEN', cau_sql)
        self.assertEqual(tham_so[:4], ('demo', 'resolver_mtq', '1', 'CANARY_PHIEN'))
        self.assertEqual(tham_so[-2:], (None, None))

    def test_phan_giai_khong_nhan_ten_ham_tuy_y_va_cap_the_he_sai(self):
        for doi in ({'module': 'mod_demo.foo'}, {'loai_ham': 'demo()'}, {'ma': 'MA_THO'},
                    {'viec_id': uuid4()}, {'the_he': 1}, {'viec_id': uuid4(), 'the_he': True}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                self._phan_giai(**doi)
        self.conn.execute.assert_not_called()

    def test_loi_driver_khong_lo_ma_phien_va_dsn(self):
        bi_mat = 'CANARY_PHIEN postgresql://CANARY:BI_MAT@localhost/kho_test_demo'
        self.conn.execute.side_effect = RuntimeError(bi_mat)
        with self.assertRaises(dk.LoiDangKy) as bat:
            self._phan_giai()
        self.assertEqual(bat.exception.ma, 'DANG_KY_THAT_BAI')
        self.assertIsNone(bat.exception.__context__)
        self.assertIsNone(bat.exception.__cause__)
        self.assertNotIn(bi_mat, ''.join(traceback.format_exception(bat.exception)))

    def test_giu_sqlstate_khong_giu_chi_tiet_driver(self):
        loi = RuntimeError('CANARY')
        loi.sqlstate = '42501'
        self.conn.execute.side_effect = loi
        with self.assertRaises(dk.LoiDangKy) as bat:
            dk.doc_dang_ky(self.conn, loai='contract')
        self.assertEqual(bat.exception.ma, '42501')
        self.assertIsNone(bat.exception.__context__)

    def test_sql_delimiter_va_khong_phu_thuoc_module_cu(self):
        # Kiem PL/pgSQL dollar quote; khong kiem kieu xuong dong.
        cac_moc = re.findall(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', SQL_DANG_KY)
        self.assertEqual(len(cac_moc) % 2, 0)
        self.assertEqual((cac_moc[0], cac_moc[-1]), ('$$', '$$'))
        ben_trong = cac_moc[1:-1]
        self.assertTrue(all(a == b for a, b in zip(ben_trong[::2], ben_trong[1::2])))
        self.assertIn('DO $$', SQL_DANG_KY)
        self.assertIn('AS $ham$', SQL_DANG_KY)
        self.assertNotRegex(SQL_DANG_KY, r'(?i)\bDROP\s+(TABLE|FUNCTION|ROLE|DATABASE)\b')
        self.assertNotRegex(SQL_DANG_KY, r'(?i)\bDELETE\s+FROM\b|\bTRUNCATE\s+(?:TABLE\s+)?loi\.')
        self.assertNotRegex(SQL_DANG_KY, r'(?i)REFERENCES\s+(mod_|crm\.|master\.)')
        self.assertNotIn('current_user', SQL_DANG_KY)


@unittest.skipUnless(psycopg is not None and ADMIN_DSN,
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class DangKyPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.thong_tin = _kiem_dich_test(conninfo_to_dict(ADMIN_DSN))
        cls.admin = psycopg.connect(**cls.thong_tin, autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        if cls.admin.info.server_version < 160000 or not cls.admin.execute(
            'SELECT rolsuper FROM pg_roles WHERE rolname=current_user').fetchone()[0]:
            raise RuntimeError('Cần lead provisioning admin PG16+')
        ma = uuid4().hex[:8]
        cls.db = 'kho_test_g2_05_' + ma
        cls.tien_to = 'ktt_g205_' + ma + '_'
        cls.admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(cls.db)))
        cls.conn = psycopg.connect(**{**cls.thong_tin, 'dbname': cls.db}, autocommit=True)
        cls.addClassCleanup(cls.conn.close)
        cls.conn.execute('SELECT set_config(%s,%s,false)', ('kho_tri_thuc.tien_to_vai', cls.tien_to))
        dc.ap_doi_cau_truc(cls.conn, CAC_TEP)
        cls.cac_thong_tin = {}
        for loai, hau_to in (('core', 'dang_nhap_loi'), ('cai_dat', 'dang_nhap_cai_dat')):
            login = cls.tien_to + hau_to
            mat_khau = secrets.token_urlsafe(32)
            cls.conn.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(
                sql.Identifier(login), sql.Literal(mat_khau)))
            for ten in ('log_parameter_max_length', 'log_parameter_max_length_on_error'):
                cls.conn.execute(sql.SQL('ALTER ROLE {} SET {}=0').format(
                    sql.Identifier(login), sql.Identifier(ten)))
            tt = {**cls.thong_tin, 'dbname': cls.db, 'user': login, 'password': mat_khau}
            cls.cac_thong_tin[loai] = tt
            ket_noi = psycopg.connect(**tt, autocommit=True)
            cls.addClassCleanup(ket_noi.close)
            setattr(cls, loai, ket_noi)

    def _ghi(self, loai, **du_lieu):
        # Go truc tiep de cac ca PG kiem SQLSTATE goc, khong qua lop che loi Python.
        return self.cai_dat.execute('SELECT loi.ghi_dang_ky(%s,%s::jsonb)',
                                    (loai, json.dumps(du_lieu))).fetchone()[0]

    def _module(self):
        ma = 'demo_' + uuid4().hex[:8]
        self._ghi('module', ma=ma, ten='DEMO')
        self._ghi('phien_ban_module', module=ma, so_phien_ban='1.0.0', ma_bam_goi=BAM,
                  tuong_thich={'core': '>=1.0.0 <2.0.0'})
        return ma

    def _contract(self, module, *, ma=None, phien_ban='1', kich_hoat=False):
        ma = ma or 'ct_' + uuid4().hex[:10]
        self._ghi('contract', ma=ma, phien_ban=phien_ban, module_so_huu=module,
                  lop='nghiep_vu', muc_dich='DEMO resolver', sieu_du_lieu={'truong': []},
                  luoc_do={'type': 'object'}, ma_bam=BAM)
        if kich_hoat:
            self._trang_thai(ma, phien_ban, 'anh_duyet', bang_chung_duyet='CD-DEMO-Anh-duyet')
            self._trang_thai(ma, phien_ban, 'dang_dung')
        return ma

    def _trang_thai(self, ma, phien_ban, trang_thai, **them):
        return self._ghi('trang_thai_contract', ma=ma, phien_ban=phien_ban,
                         trang_thai=trang_thai, **them)

    def _phien(self, module):
        nd, pn = uuid4(), uuid4()
        self.conn.execute("INSERT INTO loi.nguoi_dung(id,dang_nhap,ten,vai_tro) VALUES (%s,%s,'DEMO','XEM')",
                          (nd, 'demo_' + nd.hex))
        self.conn.execute("INSERT INTO loi.phap_nhan(id,ma,ten) VALUES (%s,%s,'DEMO')", (pn, pn.hex))
        self.conn.execute('INSERT INTO loi.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,%s)',
                          (nd, pn, [module]))
        p = phien.cap_phien(self.core, nguoi_dung_id=nd, module=module, phap_nhan_id=pn,
                            dang_nhap_csdl=self.cac_thong_tin['core']['user'], pham_vi_hanh_dong=['DOC'],
                            hieu_luc_den=datetime.now(timezone.utc) + timedelta(minutes=5))
        return p.ma.lay_de_truyen(), pn

    def _phan_giai(self, module, ma, pn, loai='resolver_mtq'):
        return self.core.execute('SELECT loi.phan_giai_ham_module(%s,%s,%s,%s,%s,%s)',
                                 (module, loai, '1', ma, pn, 'DOC')).fetchone()[0]

    def _ham(self, module, ma_contract):
        chu = self.tien_to + 'vai_doi_cau_truc_mod_' + module
        schema = 'mod_' + module
        # Provisioning fixture theo owner; khong phai ca nghiep vu SET ROLE.
        self.conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOSUPERUSER NOBYPASSRLS').format(sql.Identifier(chu)))
        self.conn.execute(sql.SQL('CREATE SCHEMA {} AUTHORIZATION {}').format(sql.Identifier(schema), sql.Identifier(chu)))
        with self.conn.transaction():
            self.conn.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(chu)))
            self.conn.execute(sql.SQL('''CREATE FUNCTION {}.resolver_demo(text,uuid)
                RETURNS jsonb LANGUAGE sql SECURITY DEFINER
                SET search_path = pg_catalog, pg_temp AS $$
                SELECT jsonb_build_object('dang_nhap',session_user::text) $$''').format(sql.Identifier(schema)))
            self.conn.execute(sql.SQL('REVOKE ALL ON FUNCTION {}.resolver_demo(text,uuid) FROM PUBLIC').format(sql.Identifier(schema)))
            for vai in (self.tien_to + 'vai_doi_cau_truc_loi', self.cac_thong_tin['core']['user']):
                self.conn.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema), sql.Identifier(vai)))
                self.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION {}.resolver_demo(text,uuid) TO {}').format(
                    sql.Identifier(schema), sql.Identifier(vai)))
        du_lieu = dict(module=module, loai_ham='resolver_mtq', phien_ban_contract='1',
                       ma_contract=ma_contract, phien_ban_module='1.0.0', ten_ham='resolver_demo',
                       chu_ky=schema + '.resolver_demo(text,uuid)', vai_so_huu=chu, ma_bam_goi=BAM)
        self._ghi('ham_module', **du_lieu)
        return du_lieu

    def test_dang_ky_doc_khi_chua_co_schema_module(self):
        module = self._module()
        self.assertIsNone(self.conn.execute('SELECT to_regnamespace(%s)', ('mod_' + module,)).fetchone()[0])
        self.assertEqual(self.cai_dat.execute('SELECT current_user,session_user').fetchone(),
                         (self.cac_thong_tin['cai_dat']['user'],) * 2)
        dong = dk.doc_dang_ky(self.core, loai='module', ma=module)
        self.assertEqual(dong[0]['ma'], module)
        self.assertEqual(dk.doc_dang_ky(self.core, loai='phien_ban_module', ma=module)[0]['trang_thai'], 'chua_cai')

    def test_engine_adapter_capability(self):
        ma = 'e_demo_' + uuid4().hex[:8]
        nang_luc = [dict(ma='demo.doc@1', dau_vao='tham_chieu_tep.v1', dau_ra='demo.v1',
                         mime=['application/pdf'], tep_toi_da_mib=20, trang_toi_da=60, thoi_han_giay=900)]
        self._ghi('engine', ma=ma, ten='Engine DEMO', so_phien_ban='0.1.0-demo.1', ma_bam_goi=BAM,
                  adapter={'ma': 'adapter_demo', 'phien_ban': '1'}, capability=nang_luc,
                  gioi_han={'so_viec_dong_thoi': 1})
        dong = dk.doc_dang_ky(self.core, loai='engine', ma=ma)[0]
        self.assertEqual(dong['nang_luc'], nang_luc)
        self.assertEqual((dong['ma_adapter'], dong['phien_ban_adapter']), ('adapter_demo', '1'))
        with self.assertRaises(psycopg.errors.CheckViolation):
            self._ghi('engine', ma=ma, ten='Engine DEMO', so_phien_ban='0.2.0-demo.1', ma_bam_goi=BAM,
                      adapter={'ma': 'adapter_demo', 'phien_ban': '1'}, capability=[{'ma': 'thieu_contract'}],
                      gioi_han={})

    def test_runtime_khong_ghi_bang_hoac_binding(self):
        for bang in CAC_BANG:
            for lenh in (f'INSERT INTO loi.{bang} DEFAULT VALUES', f'DELETE FROM loi.{bang}',
                         f'UPDATE loi.{bang} SET id=id', f'TRUNCATE loi.{bang}'):
                with self.subTest(lenh=lenh), self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    self.core.execute(lenh)
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.core.execute("SELECT loi.ghi_dang_ky('module','{}')")
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.cai_dat.execute("INSERT INTO loi.module_danh_muc(ma,ten,loai) VALUES ('gia','GIA','MODULE')")

    def test_cho_khi_module_chua_cai_hoac_thieu_ham(self):
        module = self._module()
        ma, pn = self._phien(module)
        self.assertEqual(self._phan_giai(module, ma, pn), {'ket_luan': 'CHO'})
        self._ghi('trang_thai_module', module=module, so_phien_ban='1.0.0', trang_thai='da_cai')
        self.assertEqual(self._phan_giai(module, ma, pn), {'ket_luan': 'CHO'})
        # Ma module khong co trong registry van phai co phien hop le truoc khi tra CHO.
        module_khac = 'vang_' + uuid4().hex[:8]
        ma, pn = self._phien(module_khac)
        self.assertEqual(self._phan_giai(module_khac, ma, pn), {'ket_luan': 'CHO'})

    def test_sai_phien_khong_danh_dong_voi_cho(self):
        module = self._module()
        ma, pn = self._phien(module)
        self.core.execute("SELECT set_config('ktt.nguoi_dung_id',%s,false)", (str(uuid4()),))
        for ma_sai, pn_sai in (('GIA', pn), (ma, uuid4())):
            with self.subTest(pn=pn_sai), self.assertRaises(psycopg.errors.InsufficientPrivilege):
                self._phan_giai(module, ma_sai, pn_sai)
        self.core.execute('SELECT loi.thu_hoi_phien(%s)', (ma,))
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self._phan_giai(module, ma, pn)

    def test_contract_chuyen_sai_bi_chan_va_phai_co_bang_chung(self):
        module = self._module()
        ma = self._contract(module)
        for trang_thai, them in (('dang_dung', {}), ('ngung', {}), ('anh_duyet', {})):
            with self.subTest(trang_thai=trang_thai), self.assertRaises(psycopg.errors.CheckViolation):
                self._trang_thai(ma, '1', trang_thai, **them)
        self._trang_thai(ma, '1', 'anh_duyet', bang_chung_duyet='CD-DEMO')
        self._trang_thai(ma, '1', 'dang_dung')
        with self.assertRaises(psycopg.errors.CheckViolation):
            self._trang_thai(ma, '1', 'nhap')

    def test_giu_ban_cu_con_module_dung_va_khong_tu_nang_binding(self):
        module = self._module()
        ma = self._contract(module, kich_hoat=True)
        self._ghi('dung_contract', ma_contract=ma, phien_ban_contract='1', module=module, phien_ban_module='1.0.0')
        self._contract(module, ma=ma, phien_ban='2')
        with self.assertRaises(psycopg.errors.CheckViolation):
            self._trang_thai(ma, '2', 'dang_dung')
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            self._trang_thai(ma, '1', 'ngung')
        # Ca xoa bang LOGIN cai dat phai bi tu choi, khong co cua xoa lich su.
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.cai_dat.execute('DELETE FROM loi.dang_ky_contract WHERE ma=%s', (ma,))
        dong = dk.doc_dang_ky(self.core, loai='contract', ma=ma)
        self.assertEqual([(d['phien_ban'], d['trang_thai']) for d in dong], [('1', 'dang_dung'), ('2', 'nhap')])
        self.assertEqual(dong[0]['module_dang_dung'], [{'module': module, 'phien_ban_module': '1.0.0'}])
        self.assertEqual(dong[1]['module_dang_dung'], [])

    def test_binding_chua_duyet_va_ban_module_khong_ton_tai(self):
        module = self._module()
        ma = self._contract(module)
        with self.assertRaises(psycopg.errors.CheckViolation):
            self._ghi('dung_contract', ma_contract=ma, phien_ban_contract='1', module=module, phien_ban_module='1.0.0')
        self._trang_thai(ma, '1', 'anh_duyet', bang_chung_duyet='CD-DEMO')
        self._trang_thai(ma, '1', 'dang_dung')
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            self._ghi('dung_contract', ma_contract=ma, phien_ban_contract='1', module=module, phien_ban_module='khong_co')

    def test_binding_ham_kiem_catalog_va_cho_truoc_cai(self):
        module = self._module()
        ma_contract = self._contract(module, kich_hoat=True)
        du_lieu = self._ham(module, ma_contract)
        ma, pn = self._phien(module)
        self.assertEqual(self._phan_giai(module, ma, pn), {'ket_luan': 'CHO'})
        self._ghi('trang_thai_module', module=module, so_phien_ban='1.0.0', trang_thai='da_cai')
        ket_qua = self._phan_giai(module, ma, pn)
        self.assertEqual(ket_qua['ket_luan'], 'DAT')
        self.assertEqual(ket_qua['binding']['chu_ky'], du_lieu['chu_ky'])
        self.assertNotIn(ma, json.dumps(ket_qua))
        # Core goi ham cua module theo chu ky contract, giu session_user goc.
        dong = self.core.execute(sql.SQL('SELECT {}.resolver_demo(%s,%s)').format(
            sql.Identifier('mod_' + module)), (ma, pn)).fetchone()[0]
        self.assertEqual(dong['dang_nhap'], self.cac_thong_tin['core']['user'])
        # Thay owner/hash/chu ky khong duoc dang ky.
        for thay in ({'vai_so_huu': self.tien_to + 'vai_doi_cau_truc_loi'},
                     {'ma_bam_goi': 'b' * 64}, {'chu_ky': 'pg_catalog.now()'}):
            with self.subTest(thay=thay), self.assertRaises((psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation)):
                self._ghi('ham_module', **{**du_lieu, **thay})

    def test_binding_quyen_lech_khong_tra_cho(self):
        module = self._module()
        ma_contract = self._contract(module, kich_hoat=True)
        self._ham(module, ma_contract)
        self._ghi('trang_thai_module', module=module, so_phien_ban='1.0.0', trang_thai='da_cai')
        ma, pn = self._phien(module)
        self.conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION {}.resolver_demo(text,uuid) TO PUBLIC').format(
            sql.Identifier('mod_' + module)))
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self._phan_giai(module, ma, pn)

    def test_cho_khi_ham_da_dang_ky_khong_con_ton_tai(self):
        module = self._module()
        ma_contract = self._contract(module, kich_hoat=True)
        self._ham(module, ma_contract)
        self._ghi('trang_thai_module', module=module, so_phien_ban='1.0.0', trang_thai='da_cai')
        ma, pn = self._phien(module)
        self.conn.execute(sql.SQL('ALTER FUNCTION {}.resolver_demo(text,uuid) RENAME TO resolver_cu').format(
            sql.Identifier('mod_' + module)))
        self.assertEqual(self._phan_giai(module, ma, pn), {'ket_luan': 'CHO'})

    def test_ngung_sau_khi_het_binding_khong_xoa_ban_cu(self):
        module = self._module()
        ma = self._contract(module, kich_hoat=True)
        du_lieu = dict(ma_contract=ma, phien_ban_contract='1', module=module, phien_ban_module='1.0.0')
        id_binding = self._ghi('dung_contract', **du_lieu)
        def doc_binding():
            return self.conn.execute('SELECT to_jsonb(b) FROM loi.module_dung_contract b WHERE id=%s',
                                     (id_binding,)).fetchone()[0]
        truoc = doc_binding()
        self.assertIsNone(truoc['ket_thuc_luc'])
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            self._trang_thai(ma, '1', 'ngung')
        self.assertEqual(self._ghi('thoi_dung_contract', **du_lieu), id_binding)
        sau = doc_binding()
        self.assertIsNotNone(sau['ket_thuc_luc'])
        self.assertEqual({k: v for k, v in sau.items() if k != 'ket_thuc_luc'},
                         {k: v for k, v in truoc.items() if k != 'ket_thuc_luc'})
        self.assertEqual(dk.doc_dang_ky(self.core, loai='contract', ma=ma)[0]['module_dang_dung'], [])
        audit = self.conn.execute('''SELECT hanh_dong,dang_nhap_csdl FROM loi.nhat_ky_kiem_toan
            WHERE doi_tuong='module_dung_contract' AND doi_tuong_id=%s''', (id_binding,)).fetchall()
        self.assertCountEqual(audit, [('DANG_KY_' + hd, self.cac_thong_tin['cai_dat']['user'])
                                      for hd in ('INSERT', 'UPDATE')])
        with self.assertRaises(psycopg.errors.InvalidParameterValue):
            self._ghi('thoi_dung_contract', **du_lieu)
        self.assertEqual(doc_binding(), sau)
        self._trang_thai(ma, '1', 'ngung')
        dong = dk.doc_dang_ky(self.core, loai='contract', ma=ma)[0]
        self.assertEqual(dong['trang_thai'], 'ngung')
        self.assertEqual(dong['module_dang_dung'], [])
        with self.assertRaises(psycopg.errors.CheckViolation):
            self._ghi('dung_contract', **du_lieu)

    def test_chi_ngung_khi_binding_cuoi_cung_het_hieu_luc(self):
        module = self._module()
        ma = self._contract(module, kich_hoat=True)
        self._ghi('phien_ban_module', module=module, so_phien_ban='2.0.0', ma_bam_goi=BAM,
                  tuong_thich={'core': '>=1.0.0 <2.0.0'})
        du_lieu = dict(ma_contract=ma, phien_ban_contract='1', module=module)
        for ban in ('1.0.0', '2.0.0'):
            self._ghi('dung_contract', **du_lieu, phien_ban_module=ban)
        self._ghi('thoi_dung_contract', **du_lieu, phien_ban_module='1.0.0')
        self.assertEqual(dk.doc_dang_ky(self.core, loai='contract', ma=ma)[0]['module_dang_dung'],
                         [{'module': module, 'phien_ban_module': '2.0.0'}])
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            self._trang_thai(ma, '1', 'ngung')
        self._ghi('thoi_dung_contract', **du_lieu, phien_ban_module='2.0.0')
        self._trang_thai(ma, '1', 'ngung')
        self.assertEqual(self.conn.execute('''SELECT count(*),count(ket_thuc_luc)
            FROM loi.module_dung_contract WHERE ma_contract=%s''', (ma,)).fetchone(), (2, 2))

    def test_owner_khong_delete_truncate_ke_ca_khong_trung_dong(self):
        module = self._module()
        ma = self._contract(module, kich_hoat=True)
        id_binding = self._ghi('dung_contract', ma_contract=ma, phien_ban_contract='1',
                               module=module, phien_ban_module='1.0.0')
        chu = self.tien_to + 'vai_doi_cau_truc_loi'
        for bang in CAC_BANG:
            for lenh in (f'DELETE FROM loi.{bang} WHERE false', f'DELETE FROM loi.{bang}',
                         f'TRUNCATE loi.{bang} CASCADE'):
                with self.subTest(lenh=lenh), self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
                    with self.conn.transaction():
                        self.conn.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(chu)))
                        self.conn.execute(lenh)
        self.assertEqual(self.conn.execute('SELECT id FROM loi.module_dung_contract WHERE id=%s',
                                           (id_binding,)).fetchone(), (id_binding,))

    def test_ket_thuc_binding_rollback_va_khong_sua_lich_su(self):
        module = self._module()
        ma = self._contract(module, kich_hoat=True)
        du_lieu = dict(ma_contract=ma, phien_ban_contract='1', module=module, phien_ban_module='1.0.0')
        id_binding = self._ghi('dung_contract', **du_lieu)
        with self.cai_dat.transaction(force_rollback=True):
            self._ghi('thoi_dung_contract', **du_lieu)
        self.assertIsNone(self.conn.execute('SELECT ket_thuc_luc FROM loi.module_dung_contract WHERE id=%s',
                                            (id_binding,)).fetchone()[0])
        self.assertEqual(self.conn.execute('''SELECT count(*) FROM loi.nhat_ky_kiem_toan
            WHERE doi_tuong_id=%s AND hanh_dong='DANG_KY_UPDATE' ''', (id_binding,)).fetchone()[0], 0)
        self._ghi('thoi_dung_contract', **du_lieu)
        for thay in ('ket_thuc_luc=NULL', "ket_thuc_luc=ket_thuc_luc + interval '1 second'",
                     "phien_ban_module='khac'"):
            with self.subTest(thay=thay), self.assertRaises(psycopg.errors.CheckViolation):
                with self.conn.transaction():
                    self.conn.execute(sql.SQL('SET LOCAL ROLE {}').format(
                        sql.Identifier(self.tien_to + 'vai_doi_cau_truc_loi')))
                    self.conn.execute('UPDATE loi.module_dung_contract SET ' + thay + ' WHERE id=%s',
                                      (id_binding,))

    def test_audit_cung_transaction_va_login_cai_dat_that(self):
        ten = 'demo_' + uuid4().hex[:8]
        with self.cai_dat.transaction(force_rollback=True):
            id_dong = self._ghi('module', ma=ten, ten='DEMO')
        self.assertEqual(dk.doc_dang_ky(self.core, loai='module', ma=ten), [])
        self.assertEqual(self.conn.execute('SELECT count(*) FROM loi.nhat_ky_kiem_toan WHERE doi_tuong_id=%s',
                                           (id_dong,)).fetchone()[0], 0)
        id_dong = self._ghi('module', ma=ten, ten='DEMO')
        dong = self.conn.execute('''SELECT hanh_dong,doi_tuong,dang_nhap_csdl,nguoi_dung_id
            FROM loi.nhat_ky_kiem_toan WHERE doi_tuong_id=%s''', (id_dong,)).fetchone()
        self.assertEqual(dong, ('DANG_KY_INSERT', 'module_danh_muc', self.cac_thong_tin['cai_dat']['user'], None))

    def test_chuyen_ngung_dong_thoi_binding_khong_cung_thanh_cong(self):
        module = self._module()
        ma = self._contract(module, kich_hoat=True)
        # Khoa dong contract bang ca binding, sau do thu ngung o ket noi LOGIN khac.
        with self.cai_dat.transaction():
            self._ghi('dung_contract', ma_contract=ma, phien_ban_contract='1', module=module, phien_ban_module='1.0.0')
            def ngung():
                with psycopg.connect(**self.cac_thong_tin['cai_dat'], autocommit=True) as khac:
                    khac.execute("SET lock_timeout='250ms'")
                    with self.assertRaises(psycopg.errors.LockNotAvailable):
                        khac.execute('SELECT loi.ghi_dang_ky(%s,%s::jsonb)', ('trang_thai_contract', json.dumps(
                            dict(ma=ma, phien_ban='1', trang_thai='ngung'))))
            with ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(ngung).result(timeout=10)
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            self._trang_thai(ma, '1', 'ngung')

    def test_owner_rls_ham_dac_quyen_va_chay_lai(self):
        chu = self.tien_to + 'vai_doi_cau_truc_loi'
        dong = self.conn.execute('''SELECT relname,pg_get_userbyid(relowner),relrowsecurity,relforcerowsecurity
            FROM pg_class WHERE relnamespace='loi'::regnamespace AND relname=ANY(%s)''', (list(CAC_BANG),)).fetchall()
        self.assertEqual(len(dong), len(CAC_BANG))
        self.assertTrue(all(d[1:] == (chu, True, True) for d in dong))
        self.assertEqual(dc.ap_doi_cau_truc(self.conn, CAC_TEP), 5)
        self.conn.execute(SQL_DANG_KY)
        self.test_runtime_khong_ghi_bang_hoac_binding()


if __name__ == '__main__':
    unittest.main()
