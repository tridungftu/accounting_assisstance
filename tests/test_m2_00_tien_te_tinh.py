"""M2-00-06: policy có phiên bản, chỉ thông tin DEMO tự tạo trong RAM/temp."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m2.tai_hoa_don.chinh_sach_tien_te import DUONG_DAN_QUY_TAC, ap_dung, nap_quy_tac


class TienTeTinh(unittest.TestCase):
    def setUp(self):
        self.xml = {"mst_ban": "0000000001", "mst_mua": "0000000002"}

    def chua_ro(self, xml=None, bk=None):
        kq = ap_dung(self.xml if xml is None else xml, bk)
        self.assertEqual(kq.trang_thai, "CHUA_RO")
        self.assertIsNone(kq.de_xuat_tien_te)
        self.assertFalse(kq.co_theo_policy)
        self.assertEqual((kq.ma_policy, kq.phien_ban), ("POLICY-TIENTE-01", "v1"))
        return kq

    def test_du_ba_dieu_kien_de_xuat_vnd_co_co(self):
        for bk in (None, {}, {"dvtte_cong": "VND"}, {"dvtte_cong": None}):
            with self.subTest(bk=bk):
                kq = ap_dung(self.xml, bk)
                self.assertEqual((kq.trang_thai, kq.de_xuat_tien_te, kq.co_theo_policy), ("DE_XUAT", "VND", True))
                self.assertEqual((kq.ma_policy, kq.phien_ban), ("POLICY-TIENTE-01", "v1"))

    def test_mst_13_so_co_va_khong_dau_gach(self):
        for mst_ban in ("0000000001001", "0000000001-001"):
            for mst_mua in ("0000000002002", "0000000002-002"):
                with self.subTest(ban=mst_ban, mua=mst_mua):
                    kq = ap_dung({"mst_ban": mst_ban, "mst_mua": mst_mua}, None)
                    self.assertEqual(kq.de_xuat_tien_te, "VND")
                    self.assertTrue(kq.co_theo_policy)

    def test_tgia_khac_1_la_chua_ro(self):
        for ty_gia in ("25000", 25000, "0.5", 0, -1):
            with self.subTest(ty_gia=ty_gia):
                self.chua_ro({**self.xml, "TGia": ty_gia})

    def test_dvtte_ngoai_te_la_chua_ro(self):
        for tien in ("USD", "EUR", "JPY"):
            with self.subTest(tien=tien):
                self.chua_ro({**self.xml, "DVTTe": tien})

    def test_bang_ke_ngoai_te_la_chua_ro_khong_suy_vnd(self):
        for tien in ("USD", "EUR", "JPY"):
            with self.subTest(tien=tien):
                self.chua_ro(bk={"dvtte_cong": tien})

    def test_moi_ben_mst_khong_hop_le_la_chua_ro(self):
        for ben in ("mst_ban", "mst_mua"):
            for mst in (None, "", "DEMO-US-001", "000000001", "000000000100", "00000000010001",
                        "０００００００００１", "000000000x", " 0000000001", 1):
                with self.subTest(ben=ben, mst=mst):
                    self.chua_ro({**self.xml, ben: mst})
            xml = dict(self.xml)
            xml.pop(ben)
            self.chua_ro(xml)

    def test_mau_thuan_xml_bang_ke_la_xung_dot_uu_tien(self):
        for x, b in (("VND", "USD"), ("USD", "VND"), ("USD", "EUR")):
            with self.subTest(xml=x, bk=b):
                kq = ap_dung({**self.xml, "DVTTe": x, "TGia": "25000"}, {"dvtte_cong": b})
                self.assertEqual(kq.trang_thai, "XUNG_DOT")
                self.assertIsNone(kq.de_xuat_tien_te)
                self.assertFalse(kq.co_theo_policy)

    def test_dong_nhat_ngoai_te_van_chua_ro(self):
        self.chua_ro({**self.xml, "DVTTe": "USD"}, {"dvtte_cong": "USD"})

    def test_dvtte_vnd_lay_tu_xml_khong_co_policy(self):
        for bk in (None, {"dvtte_cong": "VND"}, {"dvtte_cong": " vnd "}):
            with self.subTest(bk=bk):
                kq = ap_dung({**self.xml, "DVTTe": "VND"}, bk)
                self.assertEqual((kq.trang_thai, kq.de_xuat_tien_te, kq.co_theo_policy), ("THEO_XML", "VND", False))
        kq = ap_dung({**self.xml, "DVTTe": "VND", "TGia": "1.00"}, None)
        self.assertEqual(kq.trang_thai, "THEO_XML")

    def test_dvtte_vnd_nhung_co_dau_hieu_ngoai_te_van_chua_ro(self):
        self.chua_ro({**self.xml, "DVTTe": "VND", "TGia": "25000"})
        self.chua_ro({**self.xml, "DVTTe": "VND", "mst_mua": "DEMO-US"})

    def test_tgia_co_mat_bang_1_khong_du_dieu_kien_policy(self):
        for ty_gia in (1, 1.0, "1", "1.00"):
            with self.subTest(ty_gia=ty_gia):
                self.chua_ro({**self.xml, "TGia": ty_gia})

    def test_the_co_mat_nhung_rong_khong_suy_vnd(self):
        for truong in ("DVTTe", "TGia"):
            for gia_tri in (None, "", " ", [], {}, False, "NaN", "Infinity"):
                with self.subTest(truong=truong, gia_tri=gia_tri):
                    self.chua_ro({**self.xml, truong: gia_tri})

    def test_khong_sua_nguon_khong_co_vnd_goc_khi_thieu_dvtte(self):
        bk = {"dvtte_cong": "VND"}
        truoc = copy.deepcopy((self.xml, bk))
        a, b = ap_dung(self.xml, bk), ap_dung(self.xml, bk)
        self.assertEqual(a, b)
        self.assertEqual((self.xml, bk), truoc)
        self.assertNotIn("DVTTe", self.xml)
        self.assertTrue(a.co_theo_policy)
        self.assertNotEqual(a.trang_thai, "THEO_XML")

    def test_doi_phien_ban_file_quy_tac_ket_qua_theo_dung_file(self):
        with tempfile.TemporaryDirectory(prefix="M2b-DEMO-policy-", ignore_cleanup_errors=True) as tam:
            p = Path(tam) / "DEMO-policy.json"
            q = nap_quy_tac(DUONG_DAN_QUY_TAC)
            p.write_text(json.dumps(q), encoding="utf-8")
            a = ap_dung(self.xml, None, duong_dan_quy_tac=p)
            q["phien_ban"] = "v2-DEMO"
            p.write_text(json.dumps(q), encoding="utf-8")
            b = ap_dung(self.xml, None, duong_dan_quy_tac=p)
            self.assertEqual((a.phien_ban, b.phien_ban), ("v1", "v2-DEMO"))
            self.assertTrue(b.co_theo_policy)

    def test_nguong_nap_tu_file_khong_hard_code(self):
        with tempfile.TemporaryDirectory(prefix="M2b-DEMO-policy-", ignore_cleanup_errors=True) as tam:
            p = Path(tam) / "DEMO-policy.json"
            q = nap_quy_tac(DUONG_DAN_QUY_TAC)
            q["mst_vn"]["do_dai"] = [13]
            q["ty_gia_noi_dia"] = "2"
            p.write_text(json.dumps(q), encoding="utf-8")
            self.assertEqual(ap_dung(self.xml, None, duong_dan_quy_tac=p).trang_thai, "CHUA_RO")
            xml = {"mst_ban": "0000000001-001", "mst_mua": "0000000002-002", "DVTTe": "VND", "TGia": 2}
            self.assertEqual(ap_dung(xml, None, duong_dan_quy_tac=p).trang_thai, "THEO_XML")

    def test_quy_tac_hong_khong_am_tham_mac_dinh(self):
        with tempfile.TemporaryDirectory(prefix="M2b-DEMO-policy-", ignore_cleanup_errors=True) as tam:
            p = Path(tam) / "DEMO-policy.json"
            for raw in ('{', '{}', '[]', '{"ma_policy":"DEMO"}'):
                with self.subTest(raw=raw):
                    p.write_text(raw, encoding="utf-8")
                    with self.assertRaises(DataError) as ctx:
                        ap_dung(self.xml, None, duong_dan_quy_tac=p)
                    self.assertEqual(ctx.exception.code, "M2_00_POLICY_SAI")
            with self.assertRaises(DataError):
                ap_dung(self.xml, None, duong_dan_quy_tac=Path(tam) / "DEMO-thieu.json")

    def test_dau_vao_sai_kieu_co_ma_loi(self):
        for x, b in ((None, None), ([], None), (self.xml, [])):
            with self.subTest(xml=x, bk=b):
                with self.assertRaises(DataError) as ctx:
                    ap_dung(x, b)
                self.assertEqual(ctx.exception.code, "M2_00_POLICY_DAU_VAO")


if __name__ == "__main__":
    unittest.main()
