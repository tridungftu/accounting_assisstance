"""XS-4c1: mock + PG tùy chọn, không mở server hay xóa tệp/CSDL/vai.

PG chỉ dùng KHO_PG_DSN_TEST để tạo kho_test_* mới; giữ CSDL cho lead.
Không dùng dữ liệu thật, không kiểm CRLF/LF của tệp nguồn.
"""

from contextlib import contextmanager
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2.module import CongTacModuleK2, kiem_module, trang_thai_cho

try:
    import psycopg
except ImportError:
    psycopg = None

DSN = os.environ.get('KHO_PG_DSN_TEST')
PN = str(uuid.uuid4())
CAN = ('xem', 'ghi', 'xuat_ngoai', 'cong_bo')
CAU_LOI = {
    'MODULE_TAT': 'Chức năng này đang tạm tắt ở pháp nhân này.',
    'MODULE_CHI_NGUOI_THU': 'Chức năng đang chạy thử, chỉ người được chọn thử dùng được.',
    'MODULE_THU_KHONG_XUAT': 'Đang chạy thử nên chưa được xuất ra ngoài.',
    'MODULE_THU_KHONG_CONG_BO': 'Đang chạy thử nên chưa được chuyển kết quả chính thức sang chức năng khác.',
}


def lenh(**kw):
    return {'module': 'CRM', 'phap_nhan_id': PN, 'che_do': 'THU',
            'ly_do': 'Thử với dữ liệu giả XS4c1', 'expected_revision': 0, **kw}


class HaTangGia:
    def __init__(self):
        self.conn = MagicMock()
        self.danh_tinh = MagicMock(return_value={'id': str(uuid.uuid4()), 'dang_nhap': 'PHIEN_MAY_CHU'})
        self.events = []

    @contextmanager
    def _tx(self, dt):
        self.events.append(('begin', dt))
        try:
            yield self.conn
        except Exception:
            self.events.append('rollback')
            raise
        else:
            self.events.append('commit')


class DichVuTinh(unittest.TestCase):
    def setUp(self):
        self.ha_tang = HaTangGia()
        self.svc = CongTacModuleK2(self.ha_tang)

    def test_danh_tinh_chi_tu_phien_va_payload_khong_duoc_gia_actor(self):
        self.ha_tang.conn.execute.return_value.fetchone.return_value = {'r': 1}
        self.assertEqual(self.svc.doi_che_do('PHIEN_MAY_CHU', lenh()), {'revision': 1})
        self.ha_tang.danh_tinh.assert_called_once_with('PHIEN_MAY_CHU')
        self.assertEqual(self.ha_tang.events[0], ('begin', self.ha_tang.danh_tinh.return_value))
        for field in ('dang_nhap', 'actor', 'doi_boi', 'pn'):
            with self.subTest(field=field), self.assertRaises(DataError):
                self.svc.doi_che_do('PHIEN_MAY_CHU', lenh(**{field: 'gia_mao'}))
        self.assertEqual(self.ha_tang.conn.execute.call_count, 1)

    def test_dau_vao_sai_khong_toi_sql(self):
        for change in ({'expected_revision': True}, {'expected_revision': -1},
                       {'expected_revision': 2 ** 63}, {'expected_revision': '0'},
                       {'che_do': 'SAI'}, {'ly_do': '  '}, {'phap_nhan_id': None}):
            with self.subTest(change=change), self.assertRaises(DataError):
                self.svc.doi_che_do('PHIEN_MAY_CHU', lenh(**change))
        self.ha_tang.conn.execute.assert_not_called()

    def test_loi_sql_duoc_dich_sau_rollback_khong_lo_chi_tiet(self):
        for code in ('MODULE_CHI_ADMIN', 'MODULE_REVISION', 'MODULE_CHUA_DU_DIEU_KIEN_GO_LIVE'):
            exc = RuntimeError('Chi tiết SQL riêng')
            exc.diag = SimpleNamespace(message_primary=code + ': Chi tiết SQL riêng')
            self.ha_tang.conn.execute.side_effect = exc
            with self.subTest(code=code), self.assertRaises(DataError) as cm:
                self.svc.doi_che_do('PHIEN_MAY_CHU', lenh())
            self.assertEqual(cm.exception.code, code)
            self.assertNotIn(code, str(cm.exception))
            self.assertNotIn('Chi tiết SQL riêng', str(cm.exception))
            self.assertEqual(self.ha_tang.events[-1], 'rollback')
        exc = RuntimeError('Hỏng kết nối')
        self.ha_tang.conn.execute.side_effect = exc
        with self.assertRaises(RuntimeError) as cm:
            self.svc.doi_che_do('PHIEN_MAY_CHU', lenh())
        self.assertIs(cm.exception, exc)

    def test_guard_khong_suy_pn_khong_dat_lai_phien_hay_commit(self):
        c = self.ha_tang.conn
        c.execute.return_value.fetchone.return_value = {'r': {'che_do': 'TAT', 'cho_xem': True}}
        self.assertTrue(kiem_module(c, 'M2', PN, can='xem')['cho_xem'])
        c.execute.assert_called_once_with('SELECT master.module_trang_thai(%s,%s::uuid) AS r', ('M2', PN))
        c.commit.assert_not_called()
        c.rollback.assert_not_called()
        for can in ('lap', None, []):
            with self.assertRaises(DataError):
                kiem_module(c, 'M2', PN, can=can)
        with self.assertRaises(DataError):
            kiem_module(c, 'M2', None, can='xem')
        self.assertEqual(c.execute.call_count, 1)

    def test_khong_du_co_khong_duoc_mo_quyen(self):
        self.ha_tang.conn.execute.return_value.fetchone.return_value = {'r': {'che_do': 'VAN_HANH'}}
        for can in CAN:
            with self.subTest(can=can), self.assertRaises(DataError) as cm:
                kiem_module(self.ha_tang.conn, 'M2', PN, can=can)
            self.assertEqual(cm.exception.code, 'MODULE_KHONG_CHO_PHEP')
        self.assertIsNotNone(trang_thai_cho(self.ha_tang.conn, 'M2', PN))

    def test_ten_cho_tu_khai_bao_va_ten_trung_tinh(self):
        c = self.ha_tang.conn
        c.execute.return_value.fetchone.return_value = {'r': {'che_do': 'TAT', 'cho_xem': True,
                                                            'cong_bo_chinh_thuc': False}}
        with patch('kho_tri_thuc.ha_tang.khai_bao_module.tu_khai_bao_crm',
                   return_value=SimpleNamespace(ten='Hợp đồng bán hàng')):
            self.assertEqual(trang_thai_cho(c, 'CRM', PN),
                             {'ma': 'CHO_MODULE', 'ly_do': 'Chờ Hợp đồng bán hàng'})
        self.assertEqual(trang_thai_cho(c, 'M2', PN),
                         {'ma': 'CHO_MODULE', 'ly_do': 'Chờ dữ liệu từ chức năng nguồn'})


@unittest.skipUnless(DSN and psycopg is not None,
                     'NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG')
class DichVuPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from psycopg.rows import dict_row
        from kho_tri_thuc.ha_tang import postgres

        cls.db = 'kho_test_xs4c1_' + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0")
                          .format(sql.Identifier(cls.db)))
        cls.c = psycopg.connect(make_conninfo(DSN, dbname=cls.db), autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c)
        with cls.c.transaction():
            cls.admin = cls.nguoi('XEM')
            cls.c.execute("SELECT master.mtq_bootstrap_admin(%s::uuid,%s::uuid,'Admin giả XS4c1')",
                          (cls.admin['id'], str(uuid.uuid4())))

    @classmethod
    def nguoi(cls, vai):
        login = 'MO_PHONG_XS4C1_' + uuid.uuid4().hex
        row = cls.c.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro,mo_phong) "
                            "VALUES ('Người giả XS4c1',%s,%s,true) RETURNING id,dang_nhap", (login, vai)).fetchone()
        return {'id': str(row['id']), 'dang_nhap': row['dang_nhap']}

    def setUp(self):
        from kho_tri_thuc.k2.crm_mau import CrmMauK2

        with self.c.transaction():
            self.c.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true),"
                           "set_config('ktt.nguoi_dung_dang_nhap',%s,true)",
                           (self.admin['id'], self.admin['dang_nhap']))
            self.pn, self.pn_b = (str(self.c.execute(
                "INSERT INTO master.phap_nhan (ma,ten) VALUES (%s,'Pháp nhân giả XS4c1') RETURNING id",
                (uuid.uuid4().hex,)).fetchone()['id']) for _ in range(2))
            self.tester = self.nguoi('CFO')
            self.other = self.nguoi('KE_TOAN_TRUONG')
        # Kết nối do bên gọi cấp; không ghi artifact hay dựng phiên HTTP/DEMO.
        self.mau = CrmMauK2(self.c, ROOT, conn_tin_cay=self.c)
        self.svc = CongTacModuleK2(self.mau)

    def doi(self, cd, rev=0, *, actor=None, pn=None, module='CRM'):
        return self.svc.doi_che_do((actor or self.admin)['dang_nhap'],
                                  lenh(module=module, phap_nhan_id=pn or self.pn,
                                       che_do=cd, expected_revision=rev))['revision']

    def nguoi_thu_payload(self, pn=None):
        return {'module': 'CRM', 'phap_nhan_id': pn or self.pn,
                'nguoi_dung_id': self.tester['id'], 'ly_do': 'Lượt thử giả XS4c1'}

    def loi(self, code, fn):
        with self.assertRaises(DataError) as cm:
            fn()
        self.assertEqual(cm.exception.code, code)
        message = str(cm.exception)
        self.assertNotIn(code, message)
        self.assertNotRegex(message, r'\b(?:MODULE_[A-Z_]+|TAT|THU|VAN_HANH)\b')
        if code in CAU_LOI:
            self.assertEqual(message, CAU_LOI[code])

    def test_ba_che_do_ba_danh_tinh_bon_thao_tac(self):
        self.svc.cap_nguoi_thu(self.admin['dang_nhap'], self.nguoi_thu_payload())
        revision = 0
        for cd in ('TAT', 'THU', 'VAN_HANH'):
            revision = self.doi(cd, revision)
            for actor in (self.admin, self.tester, self.other):
                for can in CAN:
                    with self.subTest(cd=cd, actor=actor['dang_nhap'], can=can):
                        code = None
                        if cd == 'TAT' and can != 'xem':
                            code = 'MODULE_TAT'
                        elif cd == 'THU':
                            if actor == self.other:
                                code = 'MODULE_CHI_NGUOI_THU'
                            elif can in ('xuat_ngoai', 'cong_bo'):
                                code = ('MODULE_THU_KHONG_XUAT' if can == 'xuat_ngoai'
                                        else 'MODULE_THU_KHONG_CONG_BO')
                        with self.mau._tx(self.mau.danh_tinh(actor['dang_nhap'])) as conn:
                            fn = lambda: kiem_module(conn, 'CRM', self.pn, can=can)
                            if code:
                                self.loi(code, fn)
                            else:
                                self.assertEqual(fn()['che_do'], cd)

    def test_cho_tat_thu_van_hanh_cho_ca_ba_danh_tinh(self):
        self.svc.cap_nguoi_thu(self.admin['dang_nhap'],
                              {**self.nguoi_thu_payload(), 'module': 'M2'})
        rev = 0
        for cd in ('TAT', 'THU', 'VAN_HANH'):
            rev = self.doi(cd, rev, module='M2')
            for actor in (self.admin, self.tester, self.other):
                with self.subTest(cd=cd, actor=actor['dang_nhap']):
                    with self.mau._tx(self.mau.danh_tinh(actor['dang_nhap'])) as conn:
                        result = trang_thai_cho(conn, 'M2', self.pn)
                    if cd == 'VAN_HANH':
                        self.assertIsNone(result)
                    else:
                        self.assertEqual(result, {'ma': 'CHO_MODULE', 'ly_do': 'Chờ dữ liệu từ chức năng nguồn'})

    def test_admin_doi_cas_va_phap_nhan_b_doc_lap(self):
        before_b = self.svc.trang_thai(self.admin['dang_nhap'], 'CRM', self.pn_b)
        for actor in (self.tester, self.other):
            self.loi('MODULE_CHI_ADMIN', lambda: self.doi('THU', actor=actor))
        self.assertEqual(self.doi('THU'), 1)
        self.loi('MODULE_REVISION', lambda: self.doi('TAT', 0))
        self.assertEqual(self.svc.trang_thai(self.admin['dang_nhap'], 'CRM', self.pn)['revision'], 1)
        self.assertEqual(self.doi('TAT', 1), 2)
        self.assertEqual(self.svc.trang_thai(self.admin['dang_nhap'], 'CRM', self.pn_b), before_b)
        with self.mau._tx(self.mau.danh_tinh(self.other['dang_nhap'])) as conn:
            for can in CAN:
                self.assertEqual(kiem_module(conn, 'CRM', self.pn_b, can=can)['che_do'], 'VAN_HANH')

    def test_cap_thu_hoi_danh_sach_chi_admin_va_dung_pn(self):
        admin = self.admin['dang_nhap']
        p = self.nguoi_thu_payload()
        self.doi('THU')
        self.doi('THU', pn=self.pn_b)
        for actor in (self.tester, self.other):
            login = actor['dang_nhap']
            self.loi('MODULE_CHI_ADMIN', lambda: self.svc.cap_nguoi_thu(login, p))
            self.loi('MODULE_CHI_ADMIN', lambda: self.svc.thu_hoi_nguoi_thu(login, p))
            self.loi('MODULE_CHI_ADMIN', lambda: self.svc.danh_sach_nguoi_thu(login, 'CRM', self.pn))
        key = self.svc.cap_nguoi_thu(admin, p)['id']
        rows = self.svc.danh_sach_nguoi_thu(admin, 'CRM', self.pn)
        self.assertEqual([r['id'] for r in rows], [key])
        self.assertEqual(rows[0]['nguoi_dung_id'], self.tester['id'])
        self.assertEqual(self.svc.danh_sach_nguoi_thu(admin, 'CRM', self.pn_b), [])
        self.assertTrue(self.svc.trang_thai(self.tester['dang_nhap'], 'CRM', self.pn)['cho_ghi'])
        self.assertFalse(self.svc.trang_thai(self.tester['dang_nhap'], 'CRM', self.pn_b)['cho_ghi'])
        self.assertEqual(self.svc.thu_hoi_nguoi_thu(admin, p)['id'], key)
        self.assertFalse(self.svc.trang_thai(self.tester['dang_nhap'], 'CRM', self.pn)['cho_xem'])
        with self.mau._tx(self.mau.danh_tinh(self.tester['dang_nhap'])) as conn:
            self.loi('MODULE_CHI_NGUOI_THU', lambda: kiem_module(conn, 'CRM', self.pn, can='ghi'))
        history = self.svc.danh_sach_nguoi_thu(admin, 'CRM', self.pn)
        self.assertIsNotNone(history[0]['thu_hoi_luc'])

    def test_s5_khong_bat_module_moi_khi_chua_du_dieu_kien(self):
        self.loi('MODULE_CHUA_DU_DIEU_KIEN_GO_LIVE', lambda: self.doi('VAN_HANH', module='M9'))
        self.assertEqual(self.svc.trang_thai(self.admin['dang_nhap'], 'M9', self.pn)['revision'], 0)


if __name__ == '__main__':
    unittest.main()
