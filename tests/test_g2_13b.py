"""G2-13b: resolver duy nhất và mã lỗi danh mục; PG dùng login thật.

Kế thừa fixture DEMO G2-13, tự áp toàn bộ chuỗi SQL theo số, không DROP.
"""
import os
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kho_tri_thuc.core import danh_muc as dm, doi_cau_truc as dc, lien_ket as lk
try:
    from tests import test_g2_13 as g213
except ImportError:
    import test_g2_13 as g213

psycopg = g213.psycopg


class MaLoiDanhMucTest(unittest.TestCase):
    def test_giu_ma_loi_g2_13_khong_tra_loi_chung(self):
        sql = (dc.THU_MUC_SQL / '013_lien_ket.sql').read_text(encoding='utf-8')
        cac_ma = set(re.findall(r"RAISE EXCEPTION '(LIEN_KET_[A-Z_]+)'", sql))
        self.assertIn('LIEN_KET_CAN_READ_COMMITTED', cac_ma)
        for ma in cac_ma:
            with self.subTest(ma=ma):
                conn = MagicMock()
                exc = RuntimeError('CANARY_DRIVER')
                exc.diag = MagicMock(message_primary=ma)
                conn.execute.side_effect = exc
                with self.assertRaises(dm.LoiDanhMuc) as bat:
                    dm._goi(conn, 'SELECT demo()', ())
                self.assertEqual(bat.exception.ma, ma)
                self.assertIsNone(bat.exception.__context__)
                self.assertNotIn('CANARY', str(bat.exception))


@unittest.skipUnless(psycopg is not None and os.environ.get('KHO_PG_DSN_TEST'),
                     'CHUA_KIEM PG: thiếu psycopg hoặc KHO_PG_DSN_TEST')
class LienKetBPostgresTest(unittest.TestCase):
    # Tái sử dụng fixture, không nhập các test cũ có đích migration cố định 013.
    _ghi = g213.LienKetPostgresTest._ghi
    _contract = g213.LienKetPostgresTest._contract
    _trang_thai = g213.LienKetPostgresTest._trang_thai
    _cap = g213.LienKetPostgresTest._cap
    _ctx = g213.LienKetPostgresTest._ctx
    _tao = g213.LienKetPostgresTest._tao
    _resolver = g213.LienKetPostgresTest._resolver
    _quyen_huy = g213.LienKetPostgresTest._quyen_huy
    _demo_module = g213.LienKetPostgresTest._demo_module
    _chung_tu = g213.LienKetPostgresTest._chung_tu
    _quyen = g213.LienKetPostgresTest._quyen
    _lap = g213.LienKetPostgresTest._lap
    setUp = g213.LienKetPostgresTest.setUp

    @classmethod
    def setUpClass(cls):
        g213.LienKetPostgresTest.setUpClass.__func__(cls)
        cls.tep_sql = sorted(dc.THU_MUC_SQL.glob('[0-9][0-9][0-9]_*.sql'),
                             key=lambda tep: int(tep.name.split('_', 1)[0]))
        dc.ap_doi_cau_truc(cls.conn, cls.tep_sql)

    def _so_dong(self, bang):
        return self.conn.execute('SELECT count(*) FROM '+bang+' WHERE phap_nhan_id=%s',
                                 (self.pn,)).fetchone()[0]

    def _het_hieu_luc(self):
        with self.module.transaction():
            return dm.het_hieu_luc(self.module, loai='chung_tu', doi_tuong_id=self.obj,
                khoa='demo-g2-13b-het-'+self.obj.hex, row_version='1',
                **self._ctx(g213.SUA, ma=self.uy))

    def test_chuoi_sql_theo_so_va_ap_lai(self):
        chuoi = dc._doc_chuoi(self.tep_sql)
        self.assertIn(17, chuoi)
        self.assertEqual(self.conn.execute('''SELECT so_phien_ban,ma_bam
            FROM loi.lich_su_doi_cau_truc WHERE ma_goi='core' ORDER BY so_phien_ban''').fetchall(),
            [(so, bam) for so, (_, bam) in chuoi.items()])
        self.assertEqual(dc.ap_doi_cau_truc(self.conn, self.tep_sql), max(chuoi))

    def test_hai_contract_dang_dung_bao_resolver_va_khong_ghi(self):
        h = self.conn.execute('''SELECT ma_contract,phien_ban_module,vai_so_huu,ma_bam_goi
            FROM loi.dang_ky_ham_module WHERE module='demo_nv' AND loai_ham='resolver_nghia_vu'
              AND phien_ban_contract='2' ''').fetchone()
        ct = self._contract('demo_nv', ma=h[0], phien_ban='3', kich_hoat=True)
        try:
            self._ghi('ham_module', module='demo_nv', loai_ham='resolver_nghia_vu',
                phien_ban_contract='3', ma_contract=ct, phien_ban_module=h[1],
                ten_ham='resolver', chu_ky='mod_demo_nv.'+g213.CK_NV,
                vai_so_huu=h[2], ma_bam_goi=h[3])
            self.assertEqual(self.module.execute('SELECT current_user,session_user').fetchone(),
                             (self.module_login,)*2)
            self.assertEqual(self.conn.execute('''SELECT count(*) FROM loi.dang_ky_contract
                WHERE ma=%s AND trang_thai='dang_dung' ''', (ct,)).fetchone()[0], 2)
            with self.assertRaises(lk.LoiLienKet) as bat:
                self._lap()
            self.assertEqual(bat.exception.ma, 'LIEN_KET_RESOLVER')
            for bang in ('danh_muc.lien_ket_chung_tu', 'danh_muc.lien_ket_phan_bo'):
                self.assertEqual(self._so_dong(bang), 0)
        finally:
            self._trang_thai(ct, '3', 'ngung')

    def test_mot_contract_dang_dung_ghi_nhu_cu(self):
        self.assertEqual(self.module.execute('SELECT current_user,session_user').fetchone(),
                         (self.module_login,)*2)
        self.assertEqual(self._lap()['ket_luan'], 'DAT')
        self.assertEqual(self._so_dong('danh_muc.lien_ket_chung_tu'), 1)

    def test_khong_co_resolver_cho_va_khong_ghi(self):
        kq = self._lap(data={**self.data, 'module_nghia_vu': 'chua_cai'})
        self.assertEqual(kq['ket_luan'], 'CHO')
        self.assertEqual(self._so_dong('danh_muc.lien_ket_chung_tu'), 0)

    def test_repeatable_read_het_hieu_luc_tra_dung_ma(self):
        with self.module.transaction():
            dm.ghi_chung_tu(self.module, doi_tuong_id=self.obj,
                khoa='demo-g2-13b-lap-'+self.obj.hex, du_lieu=dict(g213.g212.CT),
                **self._ctx(ma=self.uy))
        with self.assertRaises(dm.LoiDanhMuc) as bat, self.module.transaction():
            self.module.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            self._het_hieu_luc()
        self.assertEqual(bat.exception.ma, 'LIEN_KET_CAN_READ_COMMITTED')
        self.assertEqual(self.conn.execute('''SELECT hieu_luc_den,phien_ban_dong
            FROM danh_muc.chung_tu WHERE id=%s''', (self.obj,)).fetchone(), (None, 1))
        self.assertEqual(self._het_hieu_luc()['ket_qua']['row_version'], '2')


if __name__ == '__main__':
    unittest.main()
