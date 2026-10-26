"""M4-DL5b: fixture DEMO thuần; không DSN, không dịch vụ, không Review thật."""

import copy
import unittest
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from kho_tri_thuc.ha_tang.primitives import canonical_json
from kho_tri_thuc.k2.xay_dung import XayDungK2, _v
from kho_tri_thuc.m4 import duyet_dot as DD
from kho_tri_thuc.m4.review_dot_pg import doc_lich_su_chep
from tests import test_m4_02c_dto_ui as F


def _chep():
    return {"dot": [{"dot": n, "m4_dot_id": None, "m4_so_dot": None} for n in (1, 2)],
            "dong": [{"dot": 1, "ma_hm": "DEMO-A", "kl_ky": Decimal("1.25"), "kl_luy_ke": Decimal("1.25")},
                     {"dot": 2, "ma_hm": "DEMO-A", "kl_ky": Decimal("2.75"), "kl_luy_ke": Decimal("4")}]}


def _seal(n=1, kl="10"):
    return {"id": f"DEMO-M4-{n}", "so_dot": n, "seal_id": f"DEMO-SEAL-{n}",
            "so_lieu": {"dong": [{"row_id": "DEMO-row-cu", "ma_hm": "DEMO-A", "khoi_luong_chap_nhan": kl}]}}


class LichSuReviewThuan(unittest.TestCase):
    def test_seal_thang_legacy_cung_dot_khong_cong_trung(self):
        chep = _chep()
        chep["dot"][0].update(m4_dot_id="DEMO-M4-1", m4_so_dot=1)
        before = copy.deepcopy(chep)
        out = DD.gom_lich_su_review_chep(chep, 3, [_seal()])
        self.assertEqual(out["dot"], [{"so_dot": 1, "nguon": "M4_SEAL"}, {"so_dot": 2, "nguon": "REVIEW_CHEP"}])
        self.assertEqual(out["bo_qua_trung"], 1)
        self.assertEqual(out["luy_ke"]["DEMO-A"]["kl_luy_ke_gom_lich_su"], Decimal("12.75"))
        self.assertEqual(chep, before)

    def test_chi_review_cong_kl_ky_khong_cong_cac_luy_ke(self):
        out = DD.gom_lich_su_review_chep(_chep(), 3, [])
        row = out["luy_ke"]["DEMO-A"]
        self.assertEqual(row["kl_luy_ke_gom_lich_su"], Decimal("4"))
        self.assertIsInstance(row["kl_luy_ke_gom_lich_su"], Decimal)
        self.assertEqual((out["trang_thai"], row["trang_thai"]), ("CO", "CO"))
        self.assertEqual(out["nhan"], "Gồm lịch sử Review đã chép — chưa qua duyệt M4")

    def test_null_ke_ca_legacy_da_bi_thay_khong_thanh_khong(self):
        for col in ("kl_ky", "kl_luy_ke"):
            for seals in ([], [_seal()]):
                with self.subTest(col=col, seal=bool(seals)):
                    chep = _chep()
                    chep["dong"][0][col] = None
                    out = DD.gom_lich_su_review_chep(chep, 3, seals)
                    self.assertIsNone(out["luy_ke"]["DEMO-A"]["kl_luy_ke_gom_lich_su"])
                    self.assertEqual(out["luy_ke"]["DEMO-A"]["trang_thai"], "INCOMPLETE")

    def test_m4_id_lech_so_uu_tien_can_xem_lai_ke_ca_co_seal(self):
        chep = _chep()
        chep["dot"][0].update(m4_dot_id="DEMO-M4-2", m4_so_dot=2)
        out = DD.gom_lich_su_review_chep(chep, 3, [_seal()])
        self.assertEqual(out["dot"][0]["nguon"], "CAN_XEM_LAI")
        self.assertEqual(out["bo_qua_trung"], 0)
        self.assertIsNone(out["luy_ke"]["DEMO-A"]["kl_luy_ke_gom_lich_su"])
        self.assertEqual(out["trang_thai"], "INCOMPLETE")

    def test_cung_dot_m4_chua_seal_khong_cong(self):
        dot = _seal()
        dot["seal_id"] = None
        out = DD.gom_lich_su_review_chep(_chep(), 3, [dot])
        self.assertEqual(out["dot"][0]["nguon"], "CAN_XEM_LAI")
        self.assertIsNone(out["luy_ke"]["DEMO-A"]["kl_luy_ke_gom_lich_su"])

    def test_lech_luy_ke_review_giu_ca_hai_so_khong_chon(self):
        chep = _chep()
        chep["dong"][1]["kl_luy_ke"] = Decimal("9")
        out = DD.gom_lich_su_review_chep(chep, 3, [])
        row = out["luy_ke"]["DEMO-A"]
        self.assertEqual(out["trang_thai"], "LECH_LUY_KE_REVIEW")
        self.assertEqual(row["trang_thai"], "LECH_LUY_KE_REVIEW")
        self.assertIsNone(row["kl_luy_ke_gom_lich_su"])
        self.assertEqual(row["doi_chieu"], {"trang_thai": "LECH_LUY_KE_REVIEW",
                                          "tong_kl_ky_review": Decimal("4"), "kl_luy_ke_review": Decimal("9")})

    def test_gan_theo_ma_hm_khong_theo_row_id_thieu_ma_la_none(self):
        out = DD.gom_lich_su_review_chep(_chep(), 3, [_seal()], ["DEMO-A", "DEMO-B"])
        rows = [{"row_id": "DEMO-row-moi", "ma_hm": "DEMO-A", "truoc_da_duyet": {"trang_thai": "CO"}},
                {"row_id": "DEMO-row-cu", "ma_hm": "DEMO-B"},
                {"row_id": "DEMO-row-thieu", "ma_hm": None}]
        before = copy.deepcopy(rows)
        result = DD._gan_lich_su_review_chep(rows, out)
        self.assertEqual(result[0]["lich_su_review_chep"]["kl_luy_ke_gom_lich_su"], Decimal("12.75"))
        self.assertEqual(result[0]["truoc_da_duyet"], before[0]["truoc_da_duyet"])
        self.assertEqual(result[1]["lich_su_review_chep"]["trang_thai"], "INCOMPLETE")
        self.assertIsNone(result[2]["lich_su_review_chep"])
        self.assertEqual(rows, before)

    def test_lich_su_thieu_ma_trung_ma_hoac_thieu_dong_seal_can_xem_lai(self):
        for kind in ("review_thieu_ma", "seal_thieu_ma", "seal_trung_ma", "seal_thieu_dong"):
            with self.subTest(kind=kind):
                chep, seal = _chep(), _seal()
                if kind == "review_thieu_ma":
                    chep["dong"][0]["ma_hm"] = None
                elif kind == "seal_thieu_ma":
                    seal["so_lieu"]["dong"][0]["ma_hm"] = None
                elif kind == "seal_trung_ma":
                    seal["so_lieu"]["dong"] *= 2
                else:
                    seal["so_lieu"]["dong"] = []
                out = DD.gom_lich_su_review_chep(chep, 3, [seal])
                self.assertEqual(out["trang_thai"], "INCOMPLETE")
                self.assertIsNone(out["luy_ke"]["DEMO-A"]["kl_luy_ke_gom_lich_su"])

    def test_chi_dot_truoc_khong_lay_hien_tai_tuong_lai(self):
        chep = _chep()
        chep["dong"][1]["kl_ky"] = None  # đợt hiện tại không làm bẩn lịch sử
        out = DD.gom_lich_su_review_chep(chep, 2, [_seal(2), _seal(4)])
        self.assertEqual(out["dot"], [{"so_dot": 1, "nguon": "REVIEW_CHEP"}])
        self.assertEqual(out["luy_ke"]["DEMO-A"]["kl_luy_ke_gom_lich_su"], Decimal("1.25"))

    def test_khong_ban_chup_va_khong_dong_khong_bia_khong(self):
        self.assertIsNone(DD.gom_lich_su_review_chep(None, 3, [_seal()]))
        out = DD.gom_lich_su_review_chep({"dot": [], "dong": []}, 3, [], ["DEMO-A"])
        self.assertEqual(out["trang_thai"], "INCOMPLETE")
        self.assertIsNone(out["luy_ke"]["DEMO-A"]["kl_luy_ke_gom_lich_su"])

    def test_decimal_chinh_xac_dieu_chinh_am_va_khong_that(self):
        for a, b, total in (("0.1", "-0.1", "0"),
                            ("123456789012345678901234567890.123456", "0.000001", "123456789012345678901234567890.123457")):
            with self.subTest(a=a), localcontext() as ctx:
                ctx.prec = 8  # không lệ thuộc precision của nơi gọi
                chep = _chep()
                chep["dong"][0].update(kl_ky=Decimal(a), kl_luy_ke=Decimal(a))
                chep["dong"][1].update(kl_ky=Decimal(b), kl_luy_ke=Decimal(total))
                row = DD.gom_lich_su_review_chep(chep, 3, [])["luy_ke"]["DEMO-A"]
                self.assertEqual(row["kl_luy_ke_gom_lich_su"], Decimal(total))
                self.assertEqual(row["trang_thai"], "CO")


class _Cur(F._Cur):
    def __init__(self, rows):
        super().__init__(rows)
        self.description = [SimpleNamespace(name=k) for k in (rows[0] if rows else ())]

    def fetchall(self):
        return self.rows


class _ConnLichSu(F.ConnGia):
    def __init__(self, W, log, chep):
        super().__init__("phien_02c", W, log)
        self.chep = chep

    def execute(self, sql, params=()):
        s = " ".join(sql.split())
        rows = None
        if "FROM master.hop_dong h WHERE h.id=" in s:
            rows = [{"duoc": True}]
        elif "has_table_privilege(" in s:
            rows = [{"duoc": True}]
        elif "m4.review_chep_hien_hanh(" in s:
            rows = [{"nguon_id": "DEMO-chup" if self.chep is not None else None}]
        elif "FROM m4.review_chep_dot_thanh_toan d" in s:
            rows = copy.deepcopy(self.chep["dot"])
        elif "FROM m4.review_chep_kl_thanh_toan k" in s:
            rows = copy.deepcopy(self.chep["dong"])
        elif s.startswith("SELECT d.id,d.so_dot,s.id AS seal_id"):
            rows = []
        if rows is None:
            return super().execute(sql, params)
        self.log.append((self.ten, s))
        return _Cur(rows)


def _xd(W, chep):
    # Bỏ riêng __init__ đăng ký dumper psycopg; giữ nguyên provider, quyền,
    # giao dịch, SQL, đồ thị, SHA và biên DTO thật trên hai connection giả.
    log = []
    xd = object.__new__(XayDungK2)
    xd.conn = F.ConnGia("app", W, log)
    xd.conn_tin_cay = _ConnLichSu(W, log, chep)
    xd.root, xd.chi_mo_phong = Path("var"), True
    xd.hom_nay = lambda: date(2026, 10, 26)
    xd._chung_tu_co_so = lambda c, dot: copy.deepcopy(W["co"])
    return xd, log


class Provider02CHoiQuy(unittest.TestCase):
    def test_dto_cung_giao_dich_json_chuan_va_prior_ket_luan_khong_doi(self):
        W = F.the_gioi()
        W["dot"]["so_dot"] = 3
        W["l3"]["basis_cong_bo_sha256"] = XayDungK2._sha_co_so(W["co"])
        F._gan_ket_luan(W, "a" * 64)
        chep = _chep()
        for row in chep["dong"]:
            row["ma_hm"] = "HM01"
        results = []
        for data in (None, chep):
            xd, log = _xd(W, data)
            dto = xd.duyet_xem(F.LOGIN, dot_id=F.S(F.DOT))
            canonical_json(dto)  # Decimal phải chuyển chuỗi tại biên DTO
            results.append(dto)
            history_sql = [(t, s) for t, s in log if "review_chep_" in s]
            self.assertTrue(history_sql)
            self.assertTrue(all(t == "phien_02c" for t, _ in history_sql))
            self.assertTrue(any("REPEATABLE READ" in s for _, s in log))
        before, after = results
        self.assertIsNone(before["lich_su_review_chep"])
        self.assertEqual(after["dong_nt"][0]["lich_su_review_chep"]["kl_luy_ke_gom_lich_su"], "4")
        for key in ("do_thi", "context", "can_cu", "ket_luan", "seal"):
            self.assertEqual(canonical_json(before[key]).encode("utf-8"), canonical_json(after[key]).encode("utf-8"), key)
        self.assertEqual([r["truoc_da_duyet"] for r in before["dong_nt"]], [r["truoc_da_duyet"] for r in after["dong_nt"]])

    def test_basis_co_so_va_json_gui_ghi_ket_luan_khong_doi_byte(self):
        output = []
        for chep in (None, _chep()):
            W = F.the_gioi()
            W["dot"]["so_dot"] = 3
            xd, _ = _xd(W, chep)
            # Lớp dữ liệu basis tối thiểu, không thay _co_so/provider prior.
            def r1(c, sql, params=()):
                if "to_regclass('m4.duyet_seal')" in sql:
                    return {"co": True}
                if "FROM m4.tep" in sql:
                    return {"phap_nhan_id": F.S(F.PN)}
                if "FROM m4.dot d LEFT JOIN" in sql:
                    return _v(copy.deepcopy(W["dot"]))
                if "FROM m4.ho_so_hop_dong h" in sql:
                    return {"rev_tham_so": 0}
                if "digest_tham_so(" in sql:
                    return {"d": "DEMO-digest"}
                return None
            xd._r1, xd._rn = r1, lambda *a: []
            with patch.object(DD, "doc_lich_su_chep", return_value=chep) as read:
                co = xd._co_so(xd.conn_tin_cay, du_an=F.S(F.DA), tep=F.S(F.TEP_DOT1),
                               dot=F.S(F.DOT), che_do="L1_L2", o_dich=None)
                self.assertEqual(co["truoc_da_duyet"]["trang_thai"], "CHUA_CO_NGUON")
                dd = DD.DuyetDot(xd)
                graph = {"l3": {"trang_thai": "CO"}, "l2": {"trang_thai": "CO"}, "vat_lieu": {"khop": True}}
                capture = []
                def write(c, sql, params=()):
                    capture.append(params[8].encode("utf-8"))
                    return {"r": "DEMO-ack"}
                def lenh(dt, action, key, yc, dot, pb, lam):
                    xd._r1 = write
                    # prior không có đợt M4 trước; không có SQL kết luận giả khác
                    with patch.object(DD, "lich_su_da_duyet", return_value=None):
                        return lam(xd.conn_tin_cay, canonical_json(yc), W["dot"], {}, graph, "a" * 64, W["l3"])
                dd._chung = lambda *a, **kw: ({}, F.S(F.DOT), F.S(F.V1), 0, "a" * 64, "DEMO-khoa")
                dd._lenh = lenh
                dd.ket_luan(F.LOGIN, dot_id=F.S(F.DOT), version_id=F.S(F.V1), revision=0, expected_basis="a" * 64,
                            gia_tri_nt="1", so_xin_thanh_toan="1", tam_ung="0", thu_hoi="0", giu_lai="0", tien_te="VND",
                            dong_nt=[{"row_id": "R-01", "khoi_luong_chap_nhan": "1"}], xu_ly_phat_hien=[], ly_do=None, khoa="DEMO-khoa")
                read.assert_not_called()
            self.assertNotIn("lich_su_review_chep", capture[0].decode("utf-8"))
            output.append((canonical_json(co).encode("utf-8"), capture[0]))
        self.assertEqual(output[0], output[1])

    def test_doc_thieu_quyen_hoac_grant_khong_doc_nguon_va_khong_doi_connection(self):
        for answers in ((False,), (True, False)):
            with self.subTest(answers=answers):
                conn = Mock()
                conn.execute.side_effect = [_Cur([{"duoc": a}]) for a in answers]
                self.assertIsNone(doc_lich_su_chep(conn, F.S(F.HD)))
                self.assertEqual(conn.execute.call_count, len(answers))
                self.assertFalse(any("review_chep_hien_hanh(" in call.args[0] for call in conn.execute.call_args_list))


if __name__ == "__main__":
    unittest.main()
