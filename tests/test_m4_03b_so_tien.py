"""M4-5a: miền tiền/contract/đọc cũ/xếp hạng thuần, fake service có nhãn; không PG/mạng.

Native migration/lưu/xác nhận nằm ở test_m4_03b_common_pg (thiếu clone → skip).
"""

from __future__ import annotations

import copy
import hashlib
import unittest
import uuid
from contextlib import contextmanager
from decimal import Decimal, localcontext
from pathlib import Path

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import ghi_nhan_chung as GN
from kho_tri_thuc.k2 import sql_ghi_nhan_chung as CU
from kho_tri_thuc.k2 import sql_ghi_nhan_so_tien as SQL


def uid(n):
    return str(uuid.UUID(int=n))


def ref(n=1, kind="NT"):
    return {"kind": kind, "occurrence_id": uid(n), "source_version_id": uid(n + 100), "part_id": None}


def tp(so=None, tt=None, **kw):
    return {"nguon": ref(), "phan": "MOT_PHAN", "so_tien_khai": so, "tien_te": tt, **kw}


def dot(**kw):
    return {"dot_id": uid(50), "cho_id": uid(1), "phap_nhan_id": uid(10), "doi_tac_mst": "0101",
            "ngay_nghiem_thu": "2026-10-25", "gia_tri": "100", "tien_te": "USD", **kw}


def hd(n, ngay="2026-10-01", so="90", **kw):
    return {"nguon": ref(n, "HOA_DON"), "phap_nhan_id": uid(10), "mst_ban": "0101", "ngay_lap": ngay,
            "tien_te": "USD", "da_gan_o": [], "raw_header_states": {"TgTTTBSo": {"state": "TEXT", "lexeme": so}}, **kw}


def graph():
    return {"contract": CU.CONTRACT_DO_THI, "nguon": [
        {"kind": "NT", "occurrence_id": uid(1), "hop_dong_id": uid(20), "doi_tac_mst": "0101",
         "hien_hanh": True, "toan_ven": True, "kt_xac_nhan_id": uid(30)},
        {"kind": "HOA_DON", "occurrence_id": uid(2), "mst_ban": "0101", "current": uid(102)}]}


class MienTien(unittest.TestCase):
    def test_bien_hop_le(self):
        for so, tt in (("1", "VND"), ("999999999999999999", "VND"), ("0.01", "USD"),
                       ("1.0", "USD"), ("999999999999999999.99", "USD")):
            with self.subTest(so=so, tt=tt):
                self.assertEqual(GN.parse_so_tien(so, tt), Decimal(so))

    def test_tu_choi_hinh_thuc_va_tran(self):
        for so in (None, True, 1, 1.2, Decimal(1), "", " 1", "1 ", "\n1", "1\n", "+1", "-1", "0", "0.00", "00", "01",
                   "1e2", "NaN", "Infinity", "1,000", "1_000", "1.234", "1.", ".1", "١", "１", "1000000000000000000", "9" * 10000):
            with self.subTest(so=str(so)[:40]):
                with self.assertRaisesRegex(DataError, "so_tien_khai"):
                    GN.parse_so_tien(so, "USD")

    def test_vnd_khong_lam_tron(self):
        for so in ("1.00", "1.01", "0.01"):
            with self.subTest(so=so), self.assertRaises(DataError):
                GN.parse_so_tien(so, "VND")

    def test_tien_te_bat_buoc(self):
        for tt in (None, "EUR", "vnd", "VND ", 1):
            with self.subTest(tt=tt), self.assertRaisesRegex(DataError, "tien_te"):
                GN.parse_so_tien("1", tt)

    def test_decimal_khong_phu_thuoc_context_ngoai(self):
        with localcontext() as c:
            c.prec = 6
            self.assertEqual(GN.parse_so_tien("999999999999999999.99", "USD"), Decimal("999999999999999999.99"))


class ContractMoiVaCu(unittest.TestCase):
    def test_mot_phan_du(self):
        t = GN.kiem_thanh_phan(tp("12.30", "USD"))
        self.assertEqual(t, tp("12.30", "USD"))
        self.assertNotIn("ty_le_khai", t)
        self.assertEqual(GN.thieu(graph(), [t]), [])

    def test_thieu_tien_hoac_tien_te_luu_nhap_duoc(self):
        for t in (tp(), tp("12.30"), tp(tt="USD"), {"nguon": ref(), "phan": "MOT_PHAN"}):
            with self.subTest(t=t):
                self.assertEqual(GN.thieu(graph(), [GN.kiem_thanh_phan(t)]), ["PHAN_KHAI_THIEU"])

    def test_ty_le_moi_tu_choi_theo_truong_ke_ca_null(self):
        for ty in (None, "50%", "1/2", "x" * 101):
            with self.subTest(ty=ty), self.assertRaisesRegex(DataError, "ty_le_khai"):
                GN.kiem_thanh_phan(tp("50", "USD", ty_le_khai=ty))

    def test_toan_phan_khong_kem_tien(self):
        self.assertEqual(GN.kiem_thanh_phan({"nguon": ref(), "phan": "TOAN_PHAN"})["so_tien_khai"], None)
        for t in (tp("1", "USD", phan="TOAN_PHAN"), tp(tt="USD", phan="TOAN_PHAN")):
            with self.assertRaises(DataError):
                GN.kiem_thanh_phan(t)

    def test_toan_phan_client_cu_null_duoc_chuan_hoa(self):
        self.assertNotIn("ty_le_khai", GN.kiem_thanh_phan({"nguon": ref(), "phan": "TOAN_PHAN", "ty_le_khai": None}))

    def test_ty_le_cu_khong_bien_thanh_tien(self):
        cu = {"nguon": ref(), "phan": "MOT_PHAN", "ty_le_khai": "50%"}
        before = copy.deepcopy(cu)
        self.assertEqual(GN.thieu(graph(), [cu]), [])
        self.assertEqual(GN.phan_khai_con_thieu(dot(), [cu])[0]["ly_do"], "TY_LE_CU_CHUA_SCALE")
        self.assertEqual(cu, before)

    def test_lich_su_ty_le_cu_nguyen_nghia(self):
        cu = {"nguon": ref(), "phan": "MOT_PHAN", "ty_le_khai": "1/3 chưa scale"}
        r = {"doi_chieu_id": uid(80), "do_thi": graph(), "graph_sha256": "a" * 64, "phien_ban": [
            {"financial_owner": None, "ghi_nhan": CU.GHI_NHAN_TT, "noi_dung": {"thanh_phan": [cu]}}]}
        out = GN.lich_su_dto(r)
        self.assertEqual(out["doi_chieu"]["phien_ban"][0]["noi_dung"]["thanh_phan"], [cu])

    def test_thieu_truong_nguon_va_truong_la(self):
        t = tp()
        t.pop("nguon")
        for v in (t, tp(truong_la=1)):
            with self.assertRaises(DataError):
                GN.kiem_thanh_phan(v)

    def test_sai_mien_tien_khong_duoc_luu_nhap(self):
        for t in (tp("-1", "USD"), tp("1.1", "VND"), tp("abc"), tp(tt="EUR")):
            with self.assertRaises(DataError):
                GN.kiem_thanh_phan(t)


class PhanConThieu(unittest.TestCase):
    def test_dot_co_gia_tri_khong_khong_phai_thieu_gia_tri(self):
        self.assertEqual(GN.phan_khai_con_thieu(dot(gia_tri="0"), [tp("1", "USD")])[0]["so_tien_con_thieu"], "0")

    def test_chenh_chinh_xac(self):
        self.assertEqual(GN.phan_khai_con_thieu(dot(), [tp("40.01", "USD")])[0]["so_tien_con_thieu"], "59.99")

    def test_khong_am_va_toan_phan(self):
        for t in (tp("101", "USD"), tp(phan="TOAN_PHAN")):
            self.assertEqual(GN.phan_khai_con_thieu(dot(), [t])[0]["so_tien_con_thieu"], "0")

    def test_khong_suy_tien_te_khac_va_thieu_du_lieu(self):
        for d, t, ly in ((dot(), tp("20", "VND"), "TIEN_TE_KHAC"),
                         (dot(), tp(), "PHAN_KHAI_THIEU"),
                         (dot(gia_tri=None), tp("20", "USD"), "GIA_TRI_DOT_CHUA_DOC_DUOC")):
            with self.subTest(ly=ly):
                r = GN.phan_khai_con_thieu(d, [t])[0]
                self.assertIsNone(r["so_tien_con_thieu"])
                self.assertEqual(r["ly_do"], ly)

    def test_khong_cong_hoa_don_hay_nguon_khac(self):
        r = GN.phan_khai_con_thieu(dot(), [tp("40", "USD"), tp("90", "USD", nguon=ref(2, "HOA_DON")), tp("90", "USD", nguon=ref(3))])
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["so_tien_con_thieu"], "60")


class GoiYThuan(unittest.TestCase):
    def test_ky_truoc_tien_sau_tie_uuid(self):
        rows = [hd(3, "2026-09-30", "100"), hd(4, so="99"), hd(2, so="99"), hd(5, so="80")]
        self.assertEqual([r["nguon"]["occurrence_id"] for r in GN.xep_hang_hoa_don(dot(), rows)], [uid(2), uid(4), uid(5), uid(3)])

    def test_loc_pn_doi_tac_khong_ten(self):
        rows = [hd(2), hd(3, phap_nhan_id=uid(11)), hd(4, mst_ban="999")]
        self.assertEqual(len(GN.xep_hang_hoa_don(dot(), rows)), 1)
        self.assertEqual(GN.xep_hang_hoa_don(dot(doi_tac_mst=None), rows), [])

    def test_chenh_thang_qua_nam_va_null_cuoi(self):
        r = GN.xep_hang_hoa_don(dot(ngay_nghiem_thu="2026-01-01"), [hd(3, None), hd(2, "2025-12-31")])
        self.assertEqual(r[0]["tin_hieu"]["chenh_ky_thang"], 1)
        self.assertIsNone(r[1]["tin_hieu"]["chenh_ky_thang"])

    def test_khong_doc_duoc_khong_tu_suy(self):
        for h in (hd(2, so="1,000"), hd(2, so="NaN"), hd(2, raw_header_states={}), hd(2, tien_te="VND"),
                  hd(2, raw_header_states={"TgTTTBSo": "100"}), hd(2, raw_header_states=[]),
                  hd(2, raw_header_states={"TgTTTBSo": {"state": "ABSENT", "lexeme": "100"}})):
            r = GN.xep_hang_hoa_don(dot(), [h])[0]
            self.assertIsNone(r["tin_hieu"]["chenh_so_tien"])

    def test_hoa_don_khong_doc_duoc_khac_so_khong(self):
        r = GN.xep_hang_hoa_don(dot(), [hd(2, so="0")])[0]
        self.assertEqual(r["so_tien_doc_duoc"], "0")
        self.assertEqual(r["tin_hieu"]["chenh_so_tien"], "100")

    def test_tien_chinh_xac_khong_float(self):
        d = dot(gia_tri="999999999999999999.99")
        self.assertEqual(GN.xep_hang_hoa_don(d, [hd(2, so="999999999999999999.98")])[0]["tin_hieu"]["chenh_so_tien"], "0.01")

    def test_da_gan_o_khong_tu_chon_khong_diem(self):
        gan = [{"doi_chieu_id": uid(60), "nhan": "đã gắn ở DEMO"}]
        r = GN.xep_hang_hoa_don(dot(), [hd(2, da_gan_o=gan)])[0]
        self.assertTrue(r["da_gan"])
        self.assertEqual(r["da_gan_o"], gan)
        self.assertTrue(r["tin_hieu"]["cung_doi_tac"])
        for k in ("score", "diem", "khop", "selected", "tu_chon"):
            self.assertNotIn(k, r)


class FakeDoc:
    """Fake ghi log chỉ chứng minh service boundary; không chứng minh quyền PostgreSQL."""
    def __init__(self, r):
        self.r, self.log = r, []

    def danh_tinh(self, dn):
        self.log.append("danh_tinh")
        return {"dang_nhap": dn}

    @contextmanager
    def _tx_review(self, dt):
        self.log.append("tx_review")
        yield None

    def _r1(self, c, sql, params):
        self.log.append((sql, params))
        return {"r": self.r}


class GoiYDichVu(unittest.TestCase):
    def test_khong_quyen_danh_sach_rong(self):
        xd = FakeDoc({"khong_quyen": True, "hoa_don": [hd(2)]})
        self.assertEqual(GN.GhiNhanChungK2(xd).goi_y_hoa_don("kt-demo", uid(50)), {"khong_quyen": True, "hoa_don": []})
        self.assertEqual(len(xd.log), 3)
        self.assertIn("_dc_goi_y_hoa_don", xd.log[-1][0])

    def test_dich_vu_xep_hang_du_lieu_may_chu(self):
        xd = FakeDoc({"khong_quyen": False, "dot": dot(), "hoa_don": [hd(3, so="90"), hd(2, so="99")]})
        r = GN.GhiNhanChungK2(xd).goi_y_hoa_don("kt-demo", uid(50))
        self.assertEqual(r["hoa_don"][0]["nguon"]["occurrence_id"], uid(2))

    def test_dot_phai_uuid_khong_nhan_context_client(self):
        xd = FakeDoc({})
        with self.assertRaises(DataError):
            GN.GhiNhanChungK2(xd).goi_y_hoa_don("kt-demo", dot())
        self.assertEqual(xd.log, [])


class MigrationTinh(unittest.TestCase):
    def test_prefix_m1_den_m32_nguyen_byte(self):
        p = Path(PM.__file__)
        self.assertEqual(hashlib.sha256(p.read_bytes()[:979228]).hexdigest(),
                         "b9b03c67eb32ba729f5bd7933d5ac130ab066d662e14e5cc3a0ec62d82760983")

    def test_dang_ky_dung_mot_lan_sau_m32(self):
        self.assertIs(PM.PG_MIGRATIONS[32], SQL.M4_03B_SO_TIEN_SQL)
        self.assertEqual(sum(s is SQL.M4_03B_SO_TIEN_SQL for s in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_sql_cu_khong_doi(self):
        p = Path(CU.__file__)
        self.assertEqual(hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
                         "b67ef795467dec1958267195e9e14f9601e705b61bc52495b5598b2609e75b12")

    def test_guard_cas_quyen_bien_nhan_giu_nguyen(self):
        # Ngoài những phép thay tiền đã công bố, thân lưu/xác nhận lấy đúng từ M0029.
        for ten, moi in (("kho.dc_luu", SQL._LUU), ("kho.dc_xac_nhan", SQL._XAC_NHAN)):
            cu = SQL._ham(ten)
            for guard in ("PERFORM kho._dc_quyen(hop, true);", "PERFORM kho._dc_khoa_hoa_don(hop);",
                          "kho._dc_bn_tra(", "DC_REVISION_CU", "m4._kt_phien_chu()"):
                self.assertEqual(moi.count(guard), cu.count(guard))

    def test_tien_duoc_sao_y_va_kiem_deferred(self):
        self.assertIn("m.so_tien_khai, m.tien_te", SQL._XAC_NHAN)
        self.assertIn("m.so_tien_khai IS NOT DISTINCT FROM", SQL._HOAN_TAT)
        self.assertIn("m.tien_te IS NOT DISTINCT FROM", SQL._HOAN_TAT)
        self.assertIn("t->>'ty_le_khai' IS NULL AND (t->>'so_tien_khai' IS NULL", SQL._THIEU)

    def test_quyen_truoc_doc_hd_va_revoke(self):
        h = next(s for s in SQL.M4_03B_SO_TIEN_SQL if s.startswith("CREATE OR REPLACE FUNCTION kho._dc_goi_y_hoa_don("))
        self.assertLess(h.index("kho._dc_m2_doc"), h.index("FROM kho.hoa_don_danh_tinh"))
        self.assertIn("d.chieu = 'MUA_VAO'", h)
        self.assertIn("d.mst_ban = dc_dot->>'doi_tac_mst'", h)
        self.assertIn("kho._dc_doc_duoc", h)
        self.assertTrue(SQL.M4_03B_SO_TIEN_SQL[-1].endswith("FROM PUBLIC"))

    def test_khong_doi_du_lieu_cu_khong_drop_ham(self):
        sql = "\n".join(SQL.M4_03B_SO_TIEN_SQL)
        self.assertNotRegex(sql, r"(?i)\b(?:UPDATE|DELETE FROM|DROP FUNCTION|DROP TABLE)\s+kho\.")
        self.assertIn("so_tien_khai > 0", sql)
        self.assertIn("scale(so_tien_khai) = 0", sql)
        self.assertIn("KHAI_BAO_THO_CHUA_SCALE", sql)


if __name__ == "__main__":
    unittest.main()
