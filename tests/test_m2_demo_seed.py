"""M2s: seed thuần/mock, không kết nối PostgreSQL."""

from contextlib import nullcontext
import unittest
from unittest.mock import patch

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import m2_demo, quyen


class KetNoiGia:
    def __init__(self):
        self.marker = False
        self.actor = None
        self.pn = ("pn-a",)
        self.ghi = []
        self.row = None

    def transaction(self):
        return nullcontext()

    def fetchone(self):
        return self.row

    def execute(self, sql, params=()):
        sql = " ".join(sql.split())
        self.row = None
        if sql.startswith("INSERT"):
            self.ghi.append((sql, params))
            if "master.nguoi_dung" in sql:
                self.actor = ("nd-m2", "KE_TOAN", True, "HOAT_DONG")
            elif "master.he_thong" in sql:
                self.marker = True
        elif "FROM master.he_thong" in sql:
            self.row = (1,) if self.marker else None
        elif "FROM master.nguoi_dung" in sql:
            assert params == (m2_demo.M2_00_LOGIN,)
            self.row = self.actor
        elif "FROM master.phap_nhan" in sql:
            assert params == ("PN_DEMO_A",)
            self.row = self.pn
        elif not sql.startswith("SELECT pg_advisory_xact_lock"):
            raise AssertionError(sql)
        return self


class SeedM2Tests(unittest.TestCase):
    def setUp(self):
        self.conn = KetNoiGia()
        self.d = {"source_instance": "DEMO_M2_XML_INSTANCE_A", "profile_ref": "DEMO_PROFILE"}

    def seed(self):
        return m2_demo.bo_sung_ke_toan_m2(self.conn, self.d)

    def test_cap_dung_quyen_chi_mot_actor_tren_pn_a(self):
        self.assertEqual(self.seed(), {"da_them": True})
        self.assertEqual(len(self.conn.ghi), 5)
        actor, business, intake, read, marker = self.conn.ghi
        self.assertEqual(actor[1], ("Kế toán M2 (mô phỏng)", "MO_PHONG_KT_M2_A"))
        self.assertIn("'KE_TOAN',true", actor[0])
        self.assertEqual(business[1], ("nd-m2", "pn-a", ["M2"]))
        self.assertIn("'{}'", business[0])
        for call, action in ((intake, "INTAKE"), (read, "READ_SOURCE")):
            self.assertEqual(call[1], ("nd-m2", self.d["source_instance"], self.d["profile_ref"],
                                       m2_demo.PROFILE_PAYLOAD_SHA256, action))
            self.assertIn("%s,NULL)", call[0])
        self.assertEqual(marker[1], (m2_demo.M2_00_MARKER,))
        quyen.kiem({"vai_tro": "KE_TOAN", "quyen": {"pn-a": {"module": ["M2"], "duyet": []}}}, "M2_READ", "pn-a")

    def test_chay_lai_khong_ghi_them(self):
        self.seed()
        truoc = list(self.conn.ghi)
        self.assertEqual(self.seed(), {"da_them": False})
        self.assertEqual(self.conn.ghi, truoc)

    def test_marker_giu_quyen_da_thu_hoi_khong_tao_lai_actor(self):
        self.conn.marker = True
        self.assertEqual(self.seed(), {"da_them": False})
        self.assertEqual(self.conn.ghi, [])

    def test_actor_co_san_khong_cap_bu_ke_ca_khong_con_marker(self):
        self.conn.actor = ("co-san", "CFO", False, "NGUNG")
        self.assertEqual(self.seed(), {"da_them": False})
        self.assertEqual(self.conn.ghi, [])

    def test_thieu_phap_nhan_khong_ghi(self):
        self.conn.pn = None
        with self.assertRaises(DataError):
            self.seed()
        self.assertEqual(self.conn.ghi, [])

    def test_bo_chon_vai_giu_login_cu_va_them_dung_mot(self):
        actors = [{"login": "MO_PHONG_CU_A"}, {"login": "MO_PHONG_CU_B"}]
        with patch.object(m2_demo, "doc_khai_bao", return_value={"actors": actors}):
            self.assertEqual(m2_demo.dang_nhap_m2(), ["MO_PHONG_CU_A", "MO_PHONG_CU_B", "MO_PHONG_KT_M2_A"])


if __name__ == "__main__":
    unittest.main()
