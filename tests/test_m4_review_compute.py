"""M4-02A — kiểm tĩnh/thuần Review L1/L2 (không cần PostgreSQL). CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN_CODE_ONLY); Root chạy sau terminal.

Ca:
- Migration: TOÀN BỘ 868.867 byte `pg_migrations.py` (H d95a14dd…, handoff GIAO-VIEC-M4-02A §5/§11) giữ nguyên; M19 chỉ nối sau EOF; 1–18 identity;
  SQL M19 không DELETE/DROP/TRUNCATE, lệnh ghi không cấp PUBLIC/app_web, map SELECT theo quyền đọc lần chạy gốc (correction).
- Companion coverage §10 trên đầu vào TỰ DỰNG (expected viết tay trước, không lấy từ engine/formatter):
  RC02 K2 theo SỐ ĐẾM (không theo tỷ lệ đã làm tròn); K7 thiếu đích → INCOMPLETE, K6 LIMITED, Đạt nguồn không thành nhãn Đạt; K8 không bảng → INCOMPLETE;
  RC01 RAW_NULL/MISSING ≠ OBSERVED_ZERO (thiếu không được tốt hơn 0 vật lý), explicit KHONG_AP_DUNG có căn cứ; TRUOC luôn INCOMPLETE (đợt 1 không
  chứng minh gì); TT-10 CHUA_CO → B8 INCOMPLETE; K7 rỗng → B7 INCOMPLETE, K7 LIMITED giữ B7 LIMITED; L2 lỗi → ERROR (không PASS).
- trang_thai_tho trên workbook openpyxl dựng trong bộ nhớ với bảng nhãn GIẢ (không dùng master_hd thật) — đúng phạm vi quét 80×12, ≤6 ô phải nhãn.
- review.js tĩnh: DOM (không innerHTML), participant `m4_review`, không nút “Nạp đợt đã duyệt”, chỉ route /api/m4/review.
- Ca cần lõi nguồn ghim (phu_thuoc/projection_l2/tinh) skip riêng khi chưa nạp = NOT_RUN.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import unicodedata
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.m4 import nguon_review as NR
from kho_tri_thuc.m4 import review_compute as RC
from kho_tri_thuc.m4 import sql_review as SR

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "kho_tri_thuc"
PREFIX_BYTES = 868_867  # handoff GIAO-VIEC-M4-02A §5/§11: toàn bộ pg_migrations.py trước M19
PREFIX_SHA256 = "d95a14dd962d866c64915c18fded7871c6b3610d1f6e2f7c57f0583f820c0244"
# FIX04 (GIAO-SUA-M4-02A-04 §3): M19 đã áp dụng ở DB DEMO — toàn bộ hai tệp dưới đây tại thời điểm đó là prefix bất biến; M20 chỉ nối sau EOF
PREFIX19_BYTES, PREFIX19_SHA256 = 869_545, "73975e09a4b1a1f8e7229a684919ee9db34f525ee8e1731239c48ea3b87dd30e"            # pg_migrations.py
SQL19_BYTES, SQL19_SHA256 = 37_415, "64bd3f9d1a96bec27e7abece2b5cf5688f1d2b12c58a8f5f157ff8181ac348f0"                # m4/sql_review.py
try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None


def _nguon_da_nap() -> bool:
    return NR.GOC.is_dir() and all((NR.GOC / rel).is_file() for rel in NR.PIN)


# ================================================================================================== migration
class MigrationM19(unittest.TestCase):
    sql = "\n".join(SR.M0019_M4_REVIEW)

    def test_prefix_868867_byte_giu_nguyen_chi_noi_m19(self):
        raw = (SRC / "ha_tang" / "pg_migrations.py").read_bytes()
        self.assertEqual(hashlib.sha256(raw[:PREFIX_BYTES]).hexdigest(), PREFIX_SHA256)
        duoi = raw[PREFIX_BYTES:].decode("utf-8")
        self.assertIn("from ..m4.sql_review import M0019_M4_REVIEW", duoi)
        self.assertIn("PG_MIGRATIONS = (*PG_MIGRATIONS, M0019_M4_REVIEW)\nPG_SCHEMA_VERSION = len(PG_MIGRATIONS)", duoi)

    def test_fix04_prefix_1_19_da_ap_dung_bat_bien_m20_noi_cuoi(self):
        raw = (SRC / "ha_tang" / "pg_migrations.py").read_bytes()
        self.assertEqual(hashlib.sha256(raw[:PREFIX19_BYTES]).hexdigest(), PREFIX19_SHA256)  # toàn bộ tệp lúc M19 áp dụng
        duoi = raw[PREFIX19_BYTES:].decode("utf-8")
        self.assertNotIn("M0019", duoi)  # không đụng lại đăng ký M19
        self.assertIn("from ..m4.sql_review import M0020_M4_REVIEW_QUYEN", duoi)
        # CRM-41-03 và các gói sau nối thêm sau M20; pin 1–19 không đổi.
        cuoi = "PG_MIGRATIONS = (*PG_MIGRATIONS, M0020_M4_REVIEW_QUYEN)\nPG_SCHEMA_VERSION = len(PG_MIGRATIONS)"
        self.assertEqual(duoi.count(cuoi), 1)
        duoi = duoi.split("\n# ---------------------------------------------------------------------------\n# 0021", 1)[0]
        self.assertTrue(duoi.rstrip().endswith("PG_MIGRATIONS = (*PG_MIGRATIONS, M0020_M4_REVIEW_QUYEN)\nPG_SCHEMA_VERSION = len(PG_MIGRATIONS)"),
                        duoi[-200:])
        sq = (SRC / "m4" / "sql_review.py").read_bytes()
        self.assertEqual(hashlib.sha256(sq[:SQL19_BYTES]).hexdigest(), SQL19_SHA256)  # SQL M19 + mọi helper dùng chung giữ nguyên byte
        sq_duoi = sq[SQL19_BYTES:].decode("utf-8")
        self.assertIn("M0020_M4_REVIEW_QUYEN = (", sq_duoi)
        self.assertNotIn("M0019_M4_REVIEW =", sq_duoi)
        for helper in ("_LOI =", "_HEX =", "_XLSX =", "_TIN_CAY =", "_KB =", "HAM_LENH =", "HAM_DOC ="):  # không định nghĩa lại helper sau EOF
            self.assertNotIn(helper, sq_duoi, helper)

    def test_1_18_identity_m19_m20_cuoi(self):
        self.assertGreaterEqual(len(PM.PG_MIGRATIONS), 20)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        self.assertIs(PM.PG_MIGRATIONS[17], PM.M0018_CRM_G)
        self.assertIs(PM.PG_MIGRATIONS[18], SR.M0019_M4_REVIEW)
        self.assertIs(PM.PG_MIGRATIONS[19], SR.M0020_M4_REVIEW_QUYEN)
        self.assertEqual(sum(m is SR.M0020_M4_REVIEW_QUYEN for m in PM.PG_MIGRATIONS), 1)
        from kho_tri_thuc.m4.sql_m17 import M0017_M4
        self.assertIs(PM.PG_MIGRATIONS[16], M0017_M4)

    def test_fix04_m20_chi_sua_dung_ham_pham_vi(self):
        m20 = SR.M0020_M4_REVIEW_QUYEN
        self.assertEqual(len(m20), 1)  # một câu lệnh
        s = m20[0]
        self.assertTrue(s.startswith("CREATE OR REPLACE FUNCTION m4.review_quyen(p_du_an uuid, p_dot uuid, p_tep uuid) RETURNS text"))
        for cam in (r"\bGRANT\b", r"\bREVOKE\b", r"\bCREATE\s+TABLE\b", r"\bALTER\b", r"\bDROP\b", r"\bDELETE\b", r"\bTRUNCATE\b", r"\bINSERT\b",
                    r"\bUPDATE\b", r"\bPOLICY\b"):
            self.assertIsNone(re.search(cam, s), cam)
        self.assertEqual(len(re.findall(r"CREATE OR REPLACE FUNCTION", s)), 1)
        # giữ chữ ký/STABLE/SECURITY DEFINER/search_path của M19
        m19 = next(x for x in SR.M0019_M4_REVIEW if "FUNCTION m4.review_quyen(" in x)
        dau19, dau20 = m19.split("$$", 1)[0], s.split("$$", 1)[0]
        self.assertEqual(" ".join(dau19.split()), " ".join(dau20.split()))
        # không còn record đợt chưa gán: biến kiểu xác định; nhánh không đợt không tham chiếu dữ liệu đợt
        self.assertNotRegex(s, r"\bd\s+record\b")
        self.assertNotRegex(s, r"\bd\.")
        self.assertIn("t m4.tep%ROWTYPE", s)
        than = s[s.index("IF master.m4_duoc(p_du_an, 'SOAN')"):]
        self.assertLess(than.index("IF p_dot IS NULL THEN"), than.index("d_trang_thai = 'DA_NOP'"))
        # giữ đúng điều kiện phạm vi: tệp HO_SO_DOT .xlsx đúng dự án; đợt đúng dự án + tệp gắn đợt; REVIEW chỉ DA_NOP
        for can in ("t.vai_tro_tai_lieu <> 'HO_SO_DOT'", "t.du_an_id IS DISTINCT FROM p_du_an", "d_du_an IS DISTINCT FROM p_du_an",
                    "k.dot_id = p_dot AND k.tep_id = p_tep", "master.m4_duoc(p_du_an, 'SOAN')", "master.m4_duoc(p_du_an, 'REVIEW')"):
            self.assertIn(can, s, can)
        self.assertNotIn(SR.M0020_M4_REVIEW_QUYEN, SR.M0019_M4_REVIEW)  # M19 không bị thay

    def test_khong_xoa_khong_drop(self):
        for mau in (r"\bDELETE\s+FROM\b", r"\bDROP\s+(TABLE|FUNCTION|POLICY|TRIGGER|SCHEMA|INDEX)\b", r"\bTRUNCATE\b", r"\bALTER\s+TABLE\s+m4\.(?!review_)"):
            self.assertIsNone(re.search(mau, self.sql, re.I), mau)
        # bảng kết quả/artifact/map chỉ ghi thêm (trigger M17), lần chạy chặn DELETE + chỉ chủ bảng
        for t in ("review_result", "review_artifact", "review_manual_map"):
            self.assertIn(f"CREATE TRIGGER {t}_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON m4.{t}", self.sql)
        self.assertIn("M4_BAT_BIEN: không xóa lần chạy Review", self.sql)

    def test_lenh_ghi_khong_cap_cho_web(self):
        self.assertIn("REVOKE EXECUTE ON FUNCTION " + ", ".join(SR.HAM_LENH) + " FROM PUBLIC", self.sql)
        self.assertNotRegex(self.sql, r"GRANT\s+EXECUTE")
        self.assertNotRegex(self.sql, r"GRANT\s+(INSERT|UPDATE|DELETE|ALL)")
        # chỉ hai hàm đọc quyền là SECURITY DEFINER (dùng trong RLS); hàm ghi chạy trên kết nối chủ bảng
        definer = re.findall(r"CREATE OR REPLACE FUNCTION (m4\.\w+)\([^)]*\)[^$]*?SECURITY DEFINER", self.sql)
        self.assertEqual(sorted(definer), ["m4.review_doc_duoc", "m4.review_quyen"])

    def test_map_thay_theo_quyen_doc_lan_chay_goc(self):
        self.assertIn("CREATE POLICY review_manual_map_web ON m4.review_manual_map FOR SELECT TO app_web USING (m4.review_doc_duoc(run_id))", self.sql)
        for t, cot in (("review_run", "id"), ("review_result", "run_id"), ("review_artifact", "run_id")):
            self.assertIn(f"ON m4.{t} FOR SELECT TO app_web USING (m4.review_doc_duoc({cot}))", self.sql)
        # reviewer chỉ đọc khi đợt DA_NOP + tệp gắn đúng đợt; người soạn/xem qua XEM
        self.assertIn("d.trang_thai = 'DA_NOP'", self.sql)
        self.assertIn("k.tep_id = r.tep_id", self.sql)

    def _ham(self, ten, ke):
        return self.sql[self.sql.index(f"FUNCTION m4.{ten}("):self.sql.index(f"FUNCTION m4.{ke}(")]

    def test_fix01_r5_xung_dot_khoa_truoc_hieu_luc(self):
        tra = self._ham("review_tra", "review_giu")
        self.assertLess(tra.index("m4.review_kiem("), tra.index("FROM m4.review_giu_khoa g"))
        self.assertLess(tra.index("FROM m4.review_giu_khoa g"), tra.index("m4._bn_tra("))
        self.assertIn("CREATE TRIGGER bien_nhan_review_khoa BEFORE INSERT ON m4.bien_nhan FOR EACH ROW EXECUTE FUNCTION m4.review_bn_khoa()", self.sql)
        bn = self._ham("review_bn_khoa", "review_tao_run")
        self.assertIn("M4_IDEMPOTENCY_KHAC", bn)
        self.assertIn("FROM m4.review_giu_khoa g", bn)  # FIX02 F4: kiểm hàng GIỮ CHỖ đã commit, không phải review_run tạo trong RR
        # ghép: HĐ FOR UPDATE TRƯỚC khóa biên nhận (thứ tự M17), khóa đã giữ chỗ cho Review chạy → xung đột trước _bn_tra
        gm = self.sql[self.sql.index("FUNCTION m4.review_ghi_map("):]
        self.assertLess(gm.index("FROM m4.ho_so_hop_dong WHERE hop_dong_id = r.hop_dong_id FOR UPDATE"), gm.index("m4._bn_tra("))
        self.assertLess(gm.index("FROM m4.review_giu_khoa g WHERE g.nguoi_dung_id = aid AND g.khoa = p_khoa"), gm.index("m4._bn_tra("))
        # không còn namespace biên nhận M17 cho khóa phiên Review
        xd = (SRC / "k2" / "xay_dung.py").read_text(encoding="utf-8")
        self.assertIn('k = f"m4:review:{dt[\'id\']}:{khoa}"', xd)
        self.assertNotIn('f"m4:bien_nhan:{dt', xd)

    def test_fix02_f4_giu_cho_truoc_snapshot_rr(self):
        giu = self._ham("review_giu", "review_bn_khoa")
        # quyền hiện hành → khóa giao dịch biên nhận (trong _bn_tra) → FINAL/xung đột → giữ chỗ; mọi xung đột trước khi ghi giữ chỗ
        self.assertLess(giu.index("m4.review_kiem("), giu.index("m4._bn_tra("))
        self.assertLess(giu.index("m4._bn_tra("), giu.index("INSERT INTO m4.review_giu_khoa"))
        self.assertLess(giu.index("M4_IDEMPOTENCY_KHAC"), giu.index("INSERT INTO m4.review_giu_khoa"))
        self.assertIn("m4.review_giu(text, text, uuid, uuid, uuid, jsonb)", SR.HAM_LENH)
        self.assertIn("CREATE TABLE m4.review_giu_khoa", self.sql)
        self.assertIn("PRIMARY KEY (nguoi_dung_id, khoa)", self.sql)
        self.assertIn("review_giu_khoa_chi_ghi_them", self.sql)
        # dịch vụ: giữ chỗ trong giao dịch READ COMMITTED riêng, đóng (commit) TRƯỚC giao dịch RR chụp basis/tạo lần chạy
        xd = (SRC / "k2" / "xay_dung.py").read_text(encoding="utf-8")
        khoi = xd[xd.index("def _review_khoi("):xd.index("def review_chay(")]
        self.assertLess(khoi.index("SELECT m4.review_giu("), khoi.index("self._tx_review(dt, rr=True)"))
        self.assertLess(khoi.index("self._tx_review(dt, rr=True)"), khoi.index("SELECT m4.review_tao_run("))
        self.assertNotIn("SELECT m4.review_tra(", khoi)
        self.assertIn("with self._khoa_phien(dt, khoa):", khoi)  # khóa phiên namespace m4:review giữ nguyên (R5)

    def test_fix01_r6_dich_ghep_hieu_luc(self):
        gm = self.sql[self.sql.index("FUNCTION m4.review_ghi_map("):]
        self.assertIn("p_boq_dong integer", gm)
        self.assertIn("m4.review_ghi_map(text, jsonb, uuid, text, uuid, integer, text, text, integer, text, text)", SR.HAM_LENH)
        for can in ("bd.dong <> p_boq_dong", "pb.trang_thai <> 'DA_KY'", "pb.ngay_hieu_luc > d.ngay_nghiem_thu",
                    "zd.thao_tac IN ('THEM','THAY')", "(p.ngay_hieu_luc, p.ngay_ky, p.so_pl) > (pb_hl, pb_ky, pb_so)"):
            self.assertIn(can, gm, can)
        # mọi từ chối nằm TRƯỚC ghi map/nhật ký/biên nhận
        self.assertLess(gm.index("M4_REVIEW_DICH_KHONG_HIEU_LUC: mã %"), gm.index("INSERT INTO m4.review_manual_map"))
        self.assertLess(gm.index("INSERT INTO m4.review_manual_map"), gm.index("m4._bn_ghi("))

    def test_tra_bien_nhan_kiem_quyen_truoc(self):
        tra = self.sql[self.sql.index("FUNCTION m4.review_tra("):self.sql.index("FUNCTION m4.review_tao_run(")]
        self.assertLess(tra.index("m4.review_kiem("), tra.index("m4._bn_tra("))
        tao = self.sql[self.sql.index("FUNCTION m4.review_tao_run("):self.sql.index("FUNCTION m4.review_cong_bo(")]
        self.assertLess(tao.index("m4.review_kiem("), tao.index("m4._bn_tra("))
        cb = self.sql[self.sql.index("FUNCTION m4.review_cong_bo("):self.sql.index("FUNCTION m4.review_huy(")]
        self.assertIn("'STALE'", cb)  # basis đổi → STALE, không gắn hiện hành
        self.assertLess(cb.index("m4.review_kiem("), cb.index("INSERT INTO m4.review_result"))
        # quyền reviewer KHÔNG mở cho đợt nháp
        self.assertIn("master.m4_duoc(p_du_an, 'REVIEW') AND p_dot IS NOT NULL AND d.trang_thai = 'DA_NOP'", self.sql)


# ================================================================================================== L1 coverage (K1–K8) — dữ liệu giả, expected viết tay
def _kt(*, sheets=((None, None, None, None, 30, None, None, None, 0),), cot=(), ct=None, an=(), chu=(), dich="TH!D38", cay=None, nhung=(),
        bang_sh="ChiTiet", nguon=("x",), ph=()):
    kq = {"sheet": list(sheets), "cot": list(cot), "an": list(an), "chu": list(chu), "dich": dich,
          "cay": list(cay if cay is not None else [{"cap": 0, 1: "TH!D38"}]), "nhung": list(nhung)}
    if bang_sh is not None:
        kq["bang_sh"] = bang_sh
        kq["nguon"] = list(nguon)
    kt = SimpleNamespace(kq=kq, ph=list(ph))
    kt._ct = dict(ct or {})
    return kt


def _nut(mo_ta):
    return ("TH!D38", mo_ta)


TV_GIA = SimpleNamespace(tach_tham_chieu=lambda f, sh: [])


class CoverageL1(unittest.TestCase):
    def test_k2_theo_so_dem_khong_theo_ty_le_lam_tron(self):
        # 6999/10000 = 0.6999 < 0.7 (nguồn: n<10 or ty<0.7 với ty chưa làm tròn) dù cột hiển thị round(…,3) = 0.7
        cot_bay = [("TH", "E", None, None, 10000, 6999, 0.7)]
        cov = RC.coverage_l1(_kt(cot=cot_bay, cay=[_nut("ô")]), TV_GIA, None)
        self.assertEqual(cov["K2"]["trang_thai"], "NOT_ELIGIBLE")
        # 14/20 = 0.7 đúng ngưỡng, n ≥ 10 → CHECKED
        cov = RC.coverage_l1(_kt(cot=[("TH", "E", None, None, 20, 14, 0.7)], cay=[_nut("ô")]), TV_GIA, None)
        self.assertEqual((cov["K2"]["trang_thai"], cov["K2"]["cot_du"]), ("CHECKED", 1))
        # 9/9 = 100% nhưng < 10 công thức → không đủ điều kiện xét
        cov = RC.coverage_l1(_kt(cot=[("TH", "E", None, None, 9, 9, 1.0)], cay=[_nut("ô")]), TV_GIA, None)
        self.assertEqual(cov["K2"]["trang_thai"], "NOT_ELIGIBLE")

    def test_k7_thieu_dich_incomplete_k6_limited_k8_khong_bang(self):
        cov = RC.coverage_l1(_kt(dich=None, cay=[], bang_sh=None), TV_GIA, None)
        self.assertEqual(cov["K7"]["trang_thai"], "INCOMPLETE")
        self.assertIsNone(cov["K7"]["nguon_dich"])
        self.assertEqual(cov["K6"]["trang_thai"], "LIMITED")
        self.assertEqual(cov["K8"]["trang_thai"], "INCOMPLETE")
        self.assertEqual(list(cov), list(RC.MA_L1))

    def test_k7_nguoi_chon_vs_tu_dong_va_cat_do_sau(self):
        self.assertEqual(RC.coverage_l1(_kt(cay=[_nut("ô")]), TV_GIA, "TH!D38")["K7"]["nguon_dich"], "NGUOI_CHON")
        self.assertEqual(RC.coverage_l1(_kt(cay=[_nut("ô")]), TV_GIA, None)["K7"]["nguon_dich"], "TU_DONG")
        cov = RC.coverage_l1(_kt(cay=[_nut("ô"), _nut("… dừng vì quá sâu")]), TV_GIA, None)
        self.assertEqual(cov["K7"]["trang_thai"], "LIMITED")

    def test_k1_cache(self):
        het = RC.coverage_l1(_kt(sheets=[(None,) * 4 + (5, None, None, None, 5)], cay=[_nut("ô")]), TV_GIA, None)
        self.assertEqual(het["K1"]["trang_thai"], "NOT_AVAILABLE")
        mot = RC.coverage_l1(_kt(sheets=[(None,) * 4 + (5, None, None, None, 2)], cay=[_nut("ô")]), TV_GIA, None)
        self.assertEqual(mot["K1"]["trang_thai"], "LIMITED")

    def test_loi_nguon_thanh_error_va_k3_duoi_nguong(self):
        cov = RC.coverage_l1(_kt(ph=[{"kt": "K5", "mo_ta": "Kiểm tra lỗi: ValueError"}], cay=[_nut("ô")]), TV_GIA, None)
        self.assertEqual(cov["K5"]["trang_thai"], "ERROR")
        self.assertIn("Kiểm tra lỗi", cov["K5"]["ly_do"])
        self.assertEqual(cov["K3"]["trang_thai"], "NOT_ELIGIBLE")  # không có liên kết cặp sheet nào ≥ 20

    def test_dat_nguon_khong_thanh_nhan_dat_khi_chua_kiem(self):
        cov = RC.coverage_l1(_kt(dich=None, cay=[]), TV_GIA, None)
        bang = RC._gan_bang_k([{"code": "K7", "ket_qua": "Đạt"}, {"code": "K4", "ket_qua": "Đạt"}], cov)
        self.assertEqual(bang[0]["ket_qua_nguon"], "Đạt")  # kết quả nguồn giữ nguyên
        self.assertEqual(bang[0]["ket_qua_hien_thi"], RC.NHAN["INCOMPLETE"])
        self.assertEqual(bang[1]["ket_qua_hien_thi"], "Đạt")


# ================================================================================================== L2 coverage — RC01/TRUOC/B7/B8
def _pt(**sua):
    ok = {"ok": True, "ly_do": "có"}
    pt = {k: dict(ok) for k in ("NGAY", "XAC_NHAN", "GT", "GOM_VAT", "VAT", "VAT_NEU_CHUA_GOM", "TT-11", "PL_KHAI", "PL_GT", "PL_THAM_SO", "BOQ", "PL_BOQ")}
    for ma in ("TT-20", "TT-21", "TT-10"):
        pt[ma] = {"ok": True, "ly_do": f"{ma} CO_GIA_TRI", "trang_thai_tham_so": "CO_GIA_TRI", "tuong_minh_khong_ap_dung": False}
    pt["TRUOC"] = {"ok": False, "ly_do": "chưa có nguồn đợt trước đã duyệt", "so_dot_khai": 1}
    for k, v in sua.items():
        pt[k.replace("_", "-") if k.startswith("TT") else k] = v
    return pt


def _knd(**tt):
    return {k: ({"trang_thai": v, "o": "TH!E9", "gia_tri_tho": 0 if v == "OBSERVED_ZERO" else None} if isinstance(v, str) else v) for k, v in tt.items()}


GIU_LAI = "Giữ lại = tỷ lệ giữ lại HĐ (TT-21)"
DE_NGHI_TT20 = "Đề nghị thanh toán kỳ này = tỷ lệ thanh toán HĐ (TT-20)"
B7 = "Hằng số và ô tham số gõ tay trên đường tính số đề nghị"
B5 = "KL kỳ trước = KL lũy kế đợt trước"
K7_OK = {"K7": {"trang_thai": "CHECKED"}}


class CoverageL2(unittest.TestCase):
    def _mot(self, ten, ket_qua, pt, knd, cov_l1=K7_OK):
        bang, tong = RC.coverage_l2([{"ten": ten, "ket_qua": ket_qua, "nhom": "Thanh toán"}], pt, cov_l1, knd)
        return bang[0], tong

    def test_rc01_thieu_khong_tot_hon_khong_vat_ly(self):
        null, _ = self._mot(GIU_LAI, "Lệch", _pt(), _knd(giu_lai="RAW_NULL", gt_kn="RECOGNIZED"))
        vang, _ = self._mot(GIU_LAI, "Lệch", _pt(), _knd(gt_kn="RECOGNIZED"))  # giu_lai MISSING
        khong, _ = self._mot(GIU_LAI, "Lệch", _pt(), _knd(giu_lai="OBSERVED_ZERO", gt_kn="RECOGNIZED"))
        nho, _ = self._mot(GIU_LAI, "Lệch", _pt(), _knd(giu_lai="NOT_RECOGNIZED", gt_kn="RECOGNIZED"))
        self.assertEqual((null["trang_thai_kiem"], vang["trang_thai_kiem"]), ("INCOMPLETE", "INCOMPLETE"))
        self.assertEqual((khong["trang_thai_kiem"], nho["trang_thai_kiem"]), ("LIMITED", "LIMITED"))
        self.assertLess(RC.THU_TU[null["trang_thai_kiem"]], RC.THU_TU[khong["trang_thai_kiem"]])
        self.assertIn("không thay bằng 0", null["ly_do_kiem"])
        self.assertEqual(null["ket_qua_nguon"], "Lệch")  # kết quả nguồn giữ nguyên

    def test_khong_ap_dung_tuong_minh_co_can_cu(self):
        tt21 = {"ok": True, "ly_do": "TT-21 KHONG_AP_DUNG", "trang_thai_tham_so": "KHONG_AP_DUNG", "tuong_minh_khong_ap_dung": True}
        r, tong = self._mot(GIU_LAI, "Không áp dụng", _pt(TT_21=tt21), _knd(giu_lai="RAW_NULL", gt_kn="RECOGNIZED"))
        self.assertEqual(r["trang_thai_kiem"], "KHONG_AP_DUNG")
        self.assertEqual(tong["B8"]["trang_thai"], "KHONG_AP_DUNG")
        self.assertIn("KHONG_AP_DUNG", RC.DAT_DU)
        # cùng dòng vắng nhưng TT-21 CHUA_CO → không suy không áp dụng
        tt21_chua = {"ok": False, "ly_do": "TT-21 CHUA_CO", "trang_thai_tham_so": "CHUA_CO", "tuong_minh_khong_ap_dung": False}
        r, _ = self._mot(GIU_LAI, "Không áp dụng", _pt(TT_21=tt21_chua), _knd(giu_lai="RAW_NULL", gt_kn="RECOGNIZED"))
        self.assertEqual(r["trang_thai_kiem"], "INCOMPLETE")

    def test_fix01_r1_khong_quy_dinh_null_la_incomplete(self):
        # ca độc lập Root: KHONG_QUY_DINH + giữ lại RAW_NULL phải INCOMPLETE (không phải KHONG_AP_DUNG/đạt); cùng dòng với KHONG_AP_DUNG tường minh
        # (đối chứng dương) mới là KHONG_AP_DUNG; 0 vật lý vẫn LIMITED
        kqd = {"ok": True, "ly_do": "TT-21 KHONG_QUY_DINH", "trang_thai_tham_so": "KHONG_QUY_DINH", "tuong_minh_khong_ap_dung": False}
        kad = {"ok": True, "ly_do": "TT-21 KHONG_AP_DUNG", "trang_thai_tham_so": "KHONG_AP_DUNG", "tuong_minh_khong_ap_dung": True}
        duong, _ = self._mot(GIU_LAI, "Không áp dụng", _pt(TT_21=kad), _knd(giu_lai="RAW_NULL", gt_kn="RECOGNIZED"))
        self.assertEqual(duong["trang_thai_kiem"], "KHONG_AP_DUNG")
        for tho in ("RAW_NULL", "MISSING"):
            knd = _knd(giu_lai=tho, gt_kn="RECOGNIZED") if tho != "MISSING" else _knd(gt_kn="RECOGNIZED")
            r, tong = self._mot(GIU_LAI, "Không áp dụng", _pt(TT_21=kqd), knd)
            self.assertEqual(r["trang_thai_kiem"], "INCOMPLETE", tho)
            self.assertEqual(tong["B8"]["trang_thai"], "INCOMPLETE", tho)
            self.assertNotIn(r["trang_thai_kiem"], RC.DAT_DU)
        r, _ = self._mot(GIU_LAI, "Không áp dụng", _pt(TT_21=kqd), _knd(giu_lai="OBSERVED_ZERO", gt_kn="RECOGNIZED"))
        self.assertEqual(r["trang_thai_kiem"], "LIMITED")

    def test_tt10_chua_co_b8_incomplete(self):
        tt10 = {"ok": False, "ly_do": "TT-10 CHUA_CO", "trang_thai_tham_so": "CHUA_CO", "tuong_minh_khong_ap_dung": False}
        r, tong = self._mot(DE_NGHI_TT20, "Đạt", _pt(TT_10=tt10), _knd(tt_ky_nay="RECOGNIZED", gt_kn="RECOGNIZED", thu_hoi_tu="RECOGNIZED"))
        self.assertEqual(r["trang_thai_kiem"], "INCOMPLETE")
        self.assertIn("TT-10 CHUA_CO", r["ly_do_kiem"])
        self.assertNotEqual(r["ket_qua_hien_thi"], "Đạt")
        self.assertEqual(tong["B8"]["trang_thai"], "INCOMPLETE")

    def test_truoc_luon_incomplete_ke_ca_dot_1(self):
        r, tong = self._mot(B5, "Đạt", _pt(), {})
        self.assertEqual((r["ma_kiem"], r["trang_thai_kiem"]), ("B5", "INCOMPLETE"))
        self.assertEqual(tong["B5"]["trang_thai"], "INCOMPLETE")

    def test_b7_theo_cay_k7(self):
        r, _ = self._mot(B7, "Không áp dụng", _pt(), {}, cov_l1={"K7": {"trang_thai": "INCOMPLETE"}})
        self.assertEqual(r["trang_thai_kiem"], "INCOMPLETE")
        r, _ = self._mot(B7, "Đạt", _pt(), {}, cov_l1={"K7": {"trang_thai": "LIMITED"}})
        self.assertEqual(r["trang_thai_kiem"], "LIMITED")
        r, _ = self._mot(B7, "Đạt", _pt(), {}, cov_l1=K7_OK)
        self.assertEqual(r["trang_thai_kiem"], "CHECKED")

    def test_khong_co_so_lieu(self):
        r, _ = self._mot(GIU_LAI, "Không có số liệu", _pt(), _knd(giu_lai="RAW_NULL", gt_kn="RECOGNIZED"))
        self.assertEqual(r["trang_thai_kiem"], "INCOMPLETE")
        r, _ = self._mot(GIU_LAI, "Không có số liệu", _pt(), _knd(giu_lai="RECOGNIZED", gt_kn="RECOGNIZED"))
        self.assertEqual(r["trang_thai_kiem"], "NOT_AVAILABLE")

    def test_ma_khong_co_dong_va_l2_loi(self):
        _, tong = RC.coverage_l2([], _pt(), K7_OK, {})
        self.assertEqual({v["trang_thai"] for v in tong.values()}, {"INCOMPLETE"})
        self.assertEqual(list(tong), list(RC.MA_L2))
        _, tong = RC.coverage_l2([], _pt(), K7_OK, [], l2_loi="ERROR")
        self.assertEqual({v["trang_thai"] for v in tong.values()}, {"ERROR"})
        self.assertNotIn("ERROR", RC.DAT_DU)
        self.assertNotIn("INCOMPLETE", RC.DAT_DU)


# ================================================================================================== trạng thái thô số tổng hợp (§10.4)
def _bo_dau(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower().replace("đ", "d")) if unicodedata.category(c) != "Mn")


MH_GIA = SimpleNamespace(bo_dau=_bo_dau, LABELS={"gt_kn": r"gia tri thuc hien ky nay", "giu_lai": r"giu lai", "thu_hoi_tu": r"thu hoi tam ung",
                                                  "tt_ky_nay": r"de nghi thanh toan ky nay", "gt_lk_kt": r"luy ke het ky truoc"})


@unittest.skipUnless(openpyxl, "Không có openpyxl — NOT_RUN")
class TrangThaiTho(unittest.TestCase):
    def test_bon_trang_thai_va_sheet_an(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "TH"
        ws["A1"], ws["C1"] = "Giá trị thực hiện kỳ này", 0         # 0 vật lý
        ws["A2"] = "Giữ lại"                                         # nhãn có, bên phải trống
        ws["A3"], ws["B3"] = "Thu hồi tạm ứng", 0.5                  # 0<|v|≤1
        ws["A4"], ws["B4"] = "Đề nghị thanh toán kỳ này", 1_000_000
        ws["A90"], ws["B90"] = "Lũy kế hết kỳ trước", 0              # ngoài 80 dòng quét
        an = wb.create_sheet("AN")
        an["A1"], an["B1"] = "Lũy kế hết kỳ trước", 0
        an.sheet_state = "hidden"
        tong = {"tt_ky_nay": {"o": "TH!B4", "gia_tri": 1_000_000}}   # parser nguồn đã nhận
        out = RC.trang_thai_tho(wb, tong, MH_GIA)
        self.assertEqual(out["gt_kn"]["trang_thai"], "OBSERVED_ZERO")
        self.assertEqual((out["gt_kn"]["o"], out["gt_kn"]["gia_tri_tho"]), ("TH!C1", 0))
        self.assertEqual(out["giu_lai"]["trang_thai"], "RAW_NULL")
        self.assertIsNone(out["giu_lai"]["gia_tri_tho"])
        self.assertEqual(out["thu_hoi_tu"]["trang_thai"], "NOT_RECOGNIZED")
        self.assertEqual(out["tt_ky_nay"]["trang_thai"], "RECOGNIZED")
        self.assertEqual(out["gt_lk_kt"]["trang_thai"], "MISSING")  # ngoài phạm vi quét + sheet ẩn không tính
        self.assertEqual(set(out), set(MH_GIA.LABELS))


# ================================================================================================== thuần khác
class ThuanKhac(unittest.TestCase):
    def test_o_dich(self):
        self.assertIsNone(NR.kiem_o_dich(None))
        self.assertEqual(NR.kiem_o_dich("'2. TH'!D38"), "'2. TH'!D38")
        self.assertEqual(NR.kiem_o_dich("TH!$D$38"), "TH!$D$38")
        for xau in ("[a.xlsx]TH!D1", "D38", "TH!D0", "=SUM(A1)", "C:\\x!A1", 5):
            with self.assertRaises(Exception) as cm:
                NR.kiem_o_dich(xau)
            self.assertIn("M4_REVIEW_O_DICH_SAI", str(getattr(cm.exception, "code", cm.exception)))

    def test_ma_hd_va_engine(self):
        self.assertEqual(NR.ma_hd_projection("0a1b2c3d-0000-4000-8000-00000000abcd"), "M40A1B2C3D000040008000" + "00000000ABCD")
        self.assertEqual(set(NR.REVIEW_PIN), {"toan_ven.py", "master_hd.py", "csdl_hop_dong.py", "may_chu/nghiep_vu.py"})
        self.assertRegex(NR.ENGINE_REVIEW_SHA, r"^[0-9a-f]{64}$")
        self.assertIn(NR.REVIEW_PHIEN_BAN, NR.ENGINE_REVIEW)

    def test_json_khong_huu_han_thanh_null(self):
        b = RC._bytes_json({"a": float("nan"), "b": [float("inf"), 1.5]})
        self.assertEqual(json.loads(b), {"a": None, "b": [None, 1.5]})

    def test_worker_luon_ghi_ket_qua_khi_loi(self):
        thu_muc = Path(tempfile.mkdtemp(prefix="ktt_m4_02a_worker_"))  # giữ lại làm bằng chứng
        (thu_muc / "vao.json").write_text("{khong phai json", encoding="utf-8")
        # không gỡ cờ giữ tệp của môi trường chạy: nếu cờ bật thì hook giữ tệp THẬT phải đang cài (FIX02 F1: không đòi sitecustomize) → main trả 3
        self.assertEqual(RC.main([str(thu_muc)]), 3)
        kq = json.loads((thu_muc / "ket_qua.json").read_text(encoding="utf-8"))  # FIX02 F2: đúng thư mục của chính test này
        self.assertEqual(kq["trang_thai"], "FAILED")
        self.assertEqual(kq["bao_cao"], [])

    # --- FIX02 F1: bằng chứng là hook xóa/ghi đè THẬT đang cài, không phải module sitecustomize/marker
    @staticmethod
    def _tuyet_doi(*phan):  # đường dẫn TUYỆT ĐỐI thật trên nền tảng đang chạy (chỉ là chuỗi provenance; không tạo/đọc tệp)
        return RC._chuan_duong(os.path.join(tempfile.gettempdir(), *phan))

    @classmethod
    def _dau(cls, hook: bool, khoi_dong=None, tep=None):
        ham = {f"{m}.{t}": {"goc": True, "module": m, "qualname": t, "tep": None} for m, t in RC.HAM_XOA}
        if hook:
            ham["os.remove"] = {"goc": False, "module": "guard_goc", "qualname": "remove_chan", "tep": tep or cls._tuyet_doi("guard", "goc", "hook.py")}
        return {"ham": ham, "khoi_dong": khoi_dong or {}}

    def test_fix02_f1_guard_that_dang_cai_duoc_nhan(self):
        """Dương tính THẬT: chạy dưới guard giữ tệp gốc của Root (cờ bật) → dấu vân của chính tiến trình này phải có hook đang cài và được nhận,
        kể cả khi không có module sitecustomize. Không chạy dưới guard → NOT_RUN (không giả lập hook, không gỡ/vá guard)."""
        if str(os.environ.get("CODEX_NO_DELETE_FILES") or "").strip().lower() not in ("1", "true", "yes", "on"):
            self.skipTest("Không chạy dưới guard giữ tệp thật — NOT_RUN")
        dau = RC.dau_van_guard()
        self.assertTrue(RC.hook_hoat_dong(dau), dau)
        self.assertTrue(RC.guard_dang_nap({"CODEX_NO_DELETE_FILES": "1", RC.ENV_GUARD_DAU: json.dumps(dau)}, dau)[0])
        self.assertTrue(RC.guard_dang_nap({"CODEX_NO_DELETE_FILES": "1", RC.ENV_GUARD_DAU: json.dumps(dau)})[0])  # dấu vân tự tính lại

    def test_fix02_f1_quyet_dinh_guard(self):
        self.assertTrue(RC.guard_dang_nap({}, self._dau(False))[0])  # không yêu cầu giữ tệp
        # hook thật đang cài, KHÔNG có sitecustomize → nhận (ca Root FAIL trước đây)
        self.assertTrue(RC.guard_dang_nap({"CODEX_NO_DELETE_FILES": "1"}, self._dau(True))[0])
        # chỉ có marker/module sitecustomize nhưng hook không cài → từ chối
        marker = self._dau(False, {"sitecustomize": self._tuyet_doi("guard", "goc", "sitecustomize.py")})
        self.assertFalse(RC.guard_dang_nap({"CODEX_NO_DELETE_FILES": "1"}, marker)[0])
        self.assertFalse(RC.guard_dang_nap({RC.ENV_GUARD_DAU: json.dumps(marker)}, marker)[0])
        # thiếu hoàn toàn → từ chối
        self.assertFalse(RC.guard_dang_nap({"CODEX_NO_DELETE_FILES": "1"}, self._dau(False))[0])
        # hook có nhưng khác provenance hook của tiến trình máy chủ (sai ràng buộc) → từ chối
        cha = self._dau(True)
        self.assertFalse(RC.guard_dang_nap({RC.ENV_GUARD_DAU: json.dumps(cha)}, self._dau(True, tep=self._tuyet_doi("khac", "hook_gia.py")))[0])
        self.assertTrue(RC.guard_dang_nap({RC.ENV_GUARD_DAU: json.dumps(cha)}, self._dau(True))[0])
        self.assertFalse(RC.guard_dang_nap({RC.ENV_GUARD_DAU: "{khong-json"}, cha)[0])
        # FIX03 F1: "hook" chỉ có sentinel (<string>, <frozen os> không khớp) hoặc đường dẫn tương đối KHÔNG phải bằng chứng guard
        for gia in ("<string>", "<frozen os>", "hook.py"):
            self.assertFalse(RC.hook_hoat_dong(self._dau(True, tep=gia)), gia)
            self.assertFalse(RC.guard_dang_nap({"CODEX_NO_DELETE_FILES": "1"}, self._dau(True, tep=gia))[0], gia)

    def test_fix03_f1_frozen_stdlib_on_dinh_va_khong_phai_hook(self):
        """Hàm stdlib frozen (vd os.removedirs/os.renames với co_filename '<frozen os>') được nhận là BẢN GỐC, tep None — không phụ thuộc CWD,
        không bị đếm là hook. Đọc đối tượng THẬT đang cài; đổi CWD rồi tính lại phải cho cùng dấu vân."""
        import types
        dau = RC.dau_van_guard()
        for ten in ("os.removedirs", "os.renames"):
            v = dau["ham"][ten]
            obj = getattr(os, ten.split(".")[1])
            code = getattr(obj, "__code__", None)
            if code is not None and code.co_filename == "<frozen os>":  # chưa bị guard thay
                self.assertEqual((v["goc"], v["tep"]), (True, None), ten)
        cu = os.getcwd()
        moi = tempfile.mkdtemp(prefix="ktt_m4_02a_cwd_")  # giữ lại
        try:
            os.chdir(moi)
            dau2 = RC.dau_van_guard()
        finally:
            os.chdir(cu)
        self.assertEqual(dau2["ham"], dau["ham"])  # cùng provenance dù khác CWD
        # sentinel <frozen x> KHÔNG khớp module định nghĩa hàm → không được coi là stdlib (và cũng không phải bằng chứng hook)
        gia = types.FunctionType(compile("def f(p):\n    return p\n", "<frozen os>", "exec").co_consts[0], {})
        gia.__module__ = "hook_gia"
        self.assertEqual(RC._nguon_ma(gia.__code__, gia), ("sentinel", "<frozen os>"))
        code = getattr(os.removedirs, "__code__", None)
        if code is not None and code.co_filename == "<frozen os>":  # đối chứng dương: hàm stdlib frozen thật → "frozen"
            self.assertEqual(RC._nguon_ma(code, os.removedirs), ("frozen", "<frozen os>"))

    def test_fix03_f1_cha_con_khac_cwd_cung_dau_van(self):
        """Tiến trình con THẬT (cùng Python, môi trường worker do máy chủ dựng, cwd = thư mục riêng khác cha) phải tính ra cùng dấu vân hook và
        chấp nhận guard khi cha yêu cầu. Chỉ đọc thuộc tính hàm; không thử xóa tệp."""
        import subprocess
        import sys as _sys
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        cha = RC.dau_van_guard()
        env = XayDungK2._env_worker()
        con_cwd = tempfile.mkdtemp(prefix="ktt_m4_02a_child_cwd_")  # giữ lại
        ma = ("import json; from kho_tri_thuc.m4 import review_compute as RC; "
              "print(json.dumps({'dau': RC.dau_van_guard(), 'guard': RC.guard_dang_nap()}))")
        p = subprocess.run([_sys.executable, "-c", ma], cwd=con_cwd, env=env, capture_output=True, timeout=300, check=False)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        out = json.loads(p.stdout.decode("utf-8").strip().splitlines()[-1])
        self.assertEqual(out["dau"]["ham"], cha["ham"])
        self.assertTrue(out["guard"][0], out["guard"])  # cờ bật + hook thật → nhận; cờ tắt và không hook → không yêu cầu → nhận

    def test_fix02_f1_dau_van_doc_doi_tuong_dang_cai(self):
        dau = RC.dau_van_guard()  # đọc đối tượng THẬT đang cài trong tiến trình này (không mock)
        self.assertEqual(set(dau["ham"]), {f"{m}.{t}" for m, t in RC.HAM_XOA})
        for ten, v in dau["ham"].items():
            if v is not None:
                self.assertIsInstance(v["goc"], bool, ten)
                self.assertTrue(v["goc"] or v["tep"] or v["module"], ten)  # hook phải có provenance
        self.assertIsInstance(dau["khoi_dong"], dict)
        src = (SRC / "m4" / "review_compute.py").read_text(encoding="utf-8")
        g = src[src.index("def guard_dang_nap("):src.index("def main(")]
        self.assertNotIn("sitecustomize", g.split('"""', 2)[2])  # quyết định không dựa vào module sitecustomize
        m = src[src.index("def main("):]
        self.assertLess(m.index("guard_dang_nap()"), m.index("from ..ha_tang.store import write_immutable"))  # trước mọi I/O

    # --- FIX02 F3: chỉ exit 0 + đúng phạm vi/raw/basis/hình dạng mới được nhận thành công
    @staticmethod
    def _kq(che_do="L1", trang_thai="PARTIAL", o_dich=None, **sua):
        cov = {m: {"trang_thai": "CHECKED", "ly_do": ""} for m in RC.MA_L1}
        cov["K7"] = {"trang_thai": "INCOMPLETE", "ly_do": "thiếu ô đích"}
        if che_do == "L1_L2":
            cov.update({m: {"trang_thai": "INCOMPLETE", "ly_do": ""} for m in RC.MA_L2})
        return {"che_do": che_do, "o_dich": o_dich, "coverage": cov, "trang_thai": trang_thai, "lop1": {"bang_k": []},
                "lop2": {"chay": True} if che_do == "L1_L2" else None, **sua}

    def test_fix02_f3_hinh_dang_ket_qua(self):
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        ok = XayDungK2._hinh_dang_ok
        self.assertTrue(ok(self._kq(), "L1", None))  # đối chứng dương: kết quả thật không rỗng, PARTIAL khớp coverage
        self.assertTrue(ok(self._kq("L1_L2"), "L1_L2", None))
        self.assertFalse(ok(self._kq(), "L1_L2", None))                       # sai chế độ
        self.assertFalse(ok(self._kq(o_dich="TH!C1"), "L1", None))            # sai ô đích đã yêu cầu
        self.assertFalse(ok(self._kq(trang_thai="SUCCEEDED"), "L1", None))    # tự xưng SUCCEEDED dù coverage chưa đủ
        thieu = self._kq()
        del thieu["coverage"]["K8"]
        self.assertFalse(ok(thieu, "L1", None))                               # thiếu mã coverage
        self.assertFalse(ok(self._kq(lop1=None), "L1", None))
        self.assertFalse(ok(self._kq("L1_L2", lop2=None), "L1_L2", None))
        la = self._kq()
        la["coverage"]["K1"] = {"trang_thai": "PASS"}
        self.assertFalse(ok(la, "L1", None))                                   # trạng thái ngoài danh mục

    def test_fix02_f3_exit_khac_0_khong_nhan_thanh_cong(self):
        xd = (SRC / "k2" / "xay_dung.py").read_text(encoding="utf-8")
        t = xd[xd.index("def _review_tinh("):xd.index("def _hinh_dang_ok(")]
        self.assertIn("elif p.returncode != 0:", t)
        # kết quả chỉ được đọc làm kết quả khi chưa có lý do lỗi (exit 0); vẫn GIỮ ket_qua.json làm bằng chứng RESULT
        self.assertIn("if ly_do is None and kq_b is not None:", t)
        self.assertIn('luu(kq_b, "RESULT"', t)
        self.assertLess(t.index("elif p.returncode != 0:"), t.index("if ly_do is None and kq_b is not None:"))
        self.assertIn("self._hinh_dang_ok(kq, che_do, o_dich)", t)

    def test_fix01_r2_main_dung_truoc_moi_io_khi_guard_khong_nap(self):
        thu_muc = Path(tempfile.mkdtemp(prefix="ktt_m4_02a_guard_main_"))  # giữ lại
        (thu_muc / "vao.json").write_text("{}", encoding="utf-8")
        with patch.object(RC, "guard_dang_nap", return_value=(False, "giả lập guard không nạp")):
            self.assertEqual(RC.main([str(thu_muc)]), RC.MA_GUARD_KHONG_NAP)
        self.assertFalse((thu_muc / "ket_qua.json").exists())  # không ghi gì

    def test_fix01_r2_env_worker_giu_khoi_dong_khong_credential(self):
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        g = Path(tempfile.mkdtemp(prefix="ktt_m4_02a_envg_"))
        dep = Path(tempfile.mkdtemp(prefix="ktt_m4_02a_envdep_"))
        environ = {"PATH": "p", "SYSTEMROOT": "s", "PYTHONUSERBASE": r"C:\ub", "CODEX_NO_DELETE_FILES": "1", "PYTHONUTF8": "1",
                   "PYTHONPATH": os.pathsep.join([str(dep), str(g)]), "KHO_PG_DSN_CRM_DEMO": "postgresql://u:p@h/db",
                   "KHO_PG_DSN_CRM_DEMO_ADMIN": "postgresql://a:b@h/db", "PGPASSWORD": "x", "KHAC": "1"}
        dau_cha = self._dau(True)
        env = XayDungK2._env_worker(environ, {"sitecustomize": SimpleNamespace(__file__=str(g / "sitecustomize.py"))}, dau_cha)
        self.assertEqual((env["PYTHONUSERBASE"], env["CODEX_NO_DELETE_FILES"], env["PYTHONDONTWRITEBYTECODE"]), (r"C:\ub", "1", "1"))
        self.assertEqual(json.loads(env[RC.ENV_GUARD_DAU]), dau_cha)  # FIX02 F1: dấu vân hook thật của cha, không phải thư mục sitecustomize
        duong = env["PYTHONPATH"].split(os.pathsep)
        self.assertEqual(duong[0], str(SRC.parent.resolve()))
        self.assertTrue({str(dep), str(g)} <= set(duong) or {str(dep), str(g.resolve())} <= set(duong), duong)
        for cam in ("KHO_PG_DSN_CRM_DEMO", "KHO_PG_DSN_CRM_DEMO_ADMIN", "PGPASSWORD", "KHAC"):
            self.assertNotIn(cam, env)
        self.assertNotIn("postgresql://", json.dumps(env))
        # cờ tắt và cha không có hook → không yêu cầu con chứng minh guard
        tat = XayDungK2._env_worker({"PATH": "p"}, {}, self._dau(False))
        self.assertNotIn(RC.ENV_GUARD_DAU, tat)


# ================================================================================================== cần lõi nguồn ghim
@unittest.skipUnless(_nguon_da_nap(), "Lõi nguồn Review chưa nạp — NOT_RUN")
class CanNguon(unittest.TestCase):
    def _co_so(self, **sua):
        ts = [{"ma": "TT-02", "trang_thai": "CO_GIA_TRI", "gia_tri": "1.000.000.000 đồng"}, {"ma": "TT-03", "trang_thai": "CO_GIA_TRI", "gia_tri": "Đã gồm VAT"},
              {"ma": "TT-04", "trang_thai": "CO_GIA_TRI", "gia_tri": "8%"}, {"ma": "TT-20", "trang_thai": "CO_GIA_TRI", "gia_tri": "90%"},
              {"ma": "TT-21", "trang_thai": "KHONG_AP_DUNG", "gia_tri": None}, {"ma": "TT-10", "trang_thai": "CHUA_CO", "gia_tri": None}]
        co = {"che_do": "L1_L2", "hop_dong": {"id": "0a1b2c3d-0000-4000-8000-00000000abcd", "so_hop_dong": "HD-1", "trang_thai_pl": "KHONG_CO"},
              "dot": {"so_dot": 1, "ngay_nghiem_thu": "2026-03-01"}, "xac_nhan": {"con_hieu_luc": True}, "tham_so": ts, "phu_luc": [],
              "boq": [{"id": "b0", "phu_luc_id": None, "trang_thai": "DA_MAP", "sheet": "BOQ",
                       "dong": [{"dong": 2, "ma_hm": "HM-01", "thao_tac": "GOC", "stt": "1", "nhom": None, "ten": "Đào đất", "dvt": "m3", "kl": "100",
                                 "don_gia": None, "thanh_tien": "0", "ma_rieng": "HM-01"}]}],
              "manual_map": []}
        co.update(sua)
        return co

    def test_phu_thuoc_typed(self):
        pt = RC.phu_thuoc(self._co_so())
        self.assertTrue(pt["NGAY"]["ok"] and pt["BOQ"]["ok"] and pt["PL_GT"]["ok"] and pt["PL_BOQ"]["ok"])
        self.assertFalse(pt["TT-10"]["ok"])
        self.assertTrue(pt["TT-21"]["tuong_minh_khong_ap_dung"])
        self.assertFalse(pt["TRUOC"]["ok"])  # đợt 1 không chứng minh không có đợt trước
        self.assertEqual(pt["TRUOC"]["so_dot_khai"], 1)
        # FIX01 R1 (đầu-cuối phu_thuoc → coverage): KHONG_QUY_DINH không phải căn cứ không áp dụng; KHONG_AP_DUNG cần bộ tham số còn hiệu lực
        ts = [t for t in self._co_so()["tham_so"] if t["ma"] != "TT-21"] + [{"ma": "TT-21", "trang_thai": "KHONG_QUY_DINH", "gia_tri": None}]
        pt_qd = RC.phu_thuoc(self._co_so(tham_so=ts))
        self.assertFalse(pt_qd["TT-21"]["tuong_minh_khong_ap_dung"])
        r, _ = RC.coverage_l2([{"ten": GIU_LAI, "ket_qua": "Không áp dụng", "nhom": "Thanh toán"}], pt_qd, K7_OK,
                              _knd(giu_lai="RAW_NULL", gt_kn="RECOGNIZED"))
        self.assertEqual(r[0]["trang_thai_kiem"], "INCOMPLETE")
        self.assertFalse(RC.phu_thuoc(self._co_so(xac_nhan={"con_hieu_luc": False}))["TT-21"]["tuong_minh_khong_ap_dung"])
        pl = [{"id": "p1", "so_pl": "PL-01", "trang_thai": "DA_KY", "ngay_hieu_luc": "2026-02-01", "doi_boq": True}]
        pt = RC.phu_thuoc(self._co_so(phu_luc=pl, hop_dong={"id": "x", "so_hop_dong": "HD-1", "trang_thai_pl": "CO_DU"}))
        self.assertFalse(pt["PL_GT"]["ok"] or pt["PL_THAM_SO"]["ok"] or pt["PL_BOQ"]["ok"])

    def test_projection_chi_doc_null_khong_thanh_0(self):
        con, bd = NR.projection_l2(self._co_so())
        try:
            r = con.execute("SELECT kl, don_gia, thanh_tien_ghi FROM boq_dong").fetchone()
            self.assertEqual((r[0], r[1], r[2]), (100.0, None, 0.0))  # NULL giữ NULL; 0 tường minh giữ 0
            self.assertEqual(con.execute("SELECT count(*) FROM tham_so").fetchone()[0], 4)  # chỉ CO_GIA_TRI
            self.assertEqual(con.execute("SELECT count(*) FROM dot_thanh_toan").fetchone()[0], 0)
            with self.assertRaises(Exception):
                con.execute("INSERT INTO khop_hang_muc (ma_hd, khoa_hstt, ma_hm) VALUES ('x','y','z')")
            self.assertEqual(bd["nguon_boq"]["HM-01"][0]["boq_id"], "b0")
        finally:
            con.close()


# ================================================================================================== review.js tĩnh
class ReviewJsTinh(unittest.TestCase):
    js = (SRC / "m4" / "giao_dien" / "review.js").read_text(encoding="utf-8")
    ma = "\n".join(d for d in js.splitlines() if not d.lstrip().startswith("//"))

    def test_dom_khong_html_chuoi(self):
        for cam in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
            self.assertNotIn(cam, self.ma, cam)

    def test_participant_va_rao(self):
        self.assertIn('K.dangKyVai("m4_review"', self.ma)
        self.assertGreaterEqual(self.ma.count('K.vaiDangChan("m4_review")'), 2)
        self.assertIn("window.kttM4Review = Object.freeze(", self.ma)
        self.assertIn("khoaMap.clear()", self.ma)  # đổi HĐ/vai: bỏ khóa đang giữ của ngữ cảnh cũ

    def test_khong_nut_nap_dot_da_duyet_va_chi_route_m4(self):
        self.assertNotIn("Nạp đợt đã duyệt", self.ma)
        self.assertIsNone(re.search(r"[\"'`]/api/(?!m4/)", self.ma))
        self.assertEqual(set(re.findall(r"lenh\(\s*\"([a-z/-]+)\"", self.ma)) - {"review/chay", "review/chay-lai", "review/ghep"}, set())
        self.assertNotIn("X-HD", self.ma)
        self.assertNotIn("/api/kiem_tra", self.ma)

    def test_fix01_r7_fence_va_tat(self):
        ma = self.js  # cắt theo các dòng chú thích mốc của tệp (bản đầy đủ)
        self.assertIn("tat,", ma)  # API tắt vùng cho shell
        tat = ma[ma.index("function tat()"):ma.index("window.kttM4Review")]
        for can in ("ep += 1", "genDs += 1", "genCt += 1", "genForm += 1", "hoatDong = false"):
            self.assertIn(can, tat)
        self.assertNotIn("khoaMap.clear()", tat)  # khóa của lệnh chưa rõ được giữ để bấm lại đúng body → FINAL
        fence = ma[ma.index("function fence("):ma.index("const formCon")]
        self.assertIn("vungSong()", fence)
        mo = ma[ma.index("async function moRun("):ma.index("async function tai(")]
        self.assertLess(mo.index("gf = genForm"), mo.index("await"))  # chụp thế hệ form lúc VÀO
        self.assertLess(mo.index("if (!conNhap()) { runChon = null; return; }"), mo.index("kq = r;"))  # A muộn sau nháp B: bỏ, không đặt kết quả
        self.assertLess(mo.index("kq = r;"), mo.index("ui.formMo = false"))
        gh = ma[ma.index("async function ghep("):ma.index("// ------------------------------------------------------------------ khối giao diện")]
        self.assertLess(gh.index("gf !== genForm) return;"), gh.index("delete ui.ghep[k]"))
        self.assertIn("if (ui.ghep[k] === ma) delete ui.ghep[k];", gh)
        tai = ma[ma.index("async function tai("):ma.index("// ------------------------------------------------------------------ hành động")]
        self.assertGreaterEqual(tai.count("if (!f()) return;"), 3)  # trước request, sau headers, sau blob
        m4 = (SRC / "m4" / "giao_dien" / "m4.js").read_text(encoding="utf-8")
        self.assertGreaterEqual(m4.count("tatReview()"), 5)
        bo = m4[m4.index("function boChon()"):m4.index("function huyYDinhTai()")]
        self.assertIn("tatReview();", bo)  # đổi HĐ/vai: tắt NGAY

    def test_fix02_f6_lenh_chan_moi_callback_theo_the_he_form(self):
        js = self.js
        le = js[js.index("async function lenh("):js.index("// ------------------------------------------------------------------ nạp")]
        self.assertIn("async function lenh(path, body, ok, f, gf = genForm)", le)
        self.assertIn("const ui = () => f() && gf === genForm;", le)
        than = le[le.index("try {"):]
        # mọi toast/trạng thái/làm mới/nút gửi lại nằm SAU kiểm ui() của nhánh tương ứng
        ok_, loi = than[:than.index("} catch (e) {")], than[than.index("} catch (e) {"):]
        self.assertLess(ok_.index("if (!ui()) return null;"), ok_.index("K.toast("))
        self.assertLess(loi.index("if (!ui()) return null;"), loi.index("K.toast("))
        self.assertLess(loi.index("if (!ui()) return null;"), loi.index("napDs()"))
        self.assertLess(loi.index("if (!ui()) return null;"), loi.index("guiLai = {path, body, ok, f}"))
        self.assertIn("traBanGhi(k, rec, ve, xong)", le)  # khóa chưa rõ giữ trong khoaMap (không xóa ý định)
        # mọi nơi gọi lệnh truyền thế hệ form của Ý ĐỊNH GỐC
        self.assertEqual(len(re.findall(r"await lenh\([^;]*?, f, gf\)", js)) + len(re.findall(r"lenh\(g\.path, g\.body, g\.ok, g\.f, gf\)", js)), 4)
        ms = js[js.index("function moSauLenh("):js.index("async function tai(")]
        self.assertNotIn("trangThai(", ms)  # không báo trạng thái A vào nháp B

    def test_fix03_f2_lam_moi_muon_khong_cham_nhap_b(self):
        js = self.js
        nd = js[js.index("async function napDs("):js.index("async function moRun(")]
        self.assertIn("fs = formCon()", nd)
        self.assertIn("const dung = () => e === ep && vungSong() && g === genDs && key === selKey() && fs();", nd)
        than = nd[nd.index("try {"):]
        ok_, loi = than[:than.index("} catch (err) {")], than[than.index("} catch (err) {"):]
        # nhánh thành công: fence (gồm thế hệ form) sau headers và sau body, TRƯỚC mọi gán dữ liệu/lựa chọn/vẽ
        self.assertEqual(ok_.count("if (!dung()) return;"), 2)
        self.assertLess(ok_.rindex("if (!dung()) return;"), ok_.index("ds = r;"))
        self.assertLess(ok_.rindex("if (!dung()) return;"), ok_.index("sel.tep = null"))
        # nhánh lỗi: fence TRƯỚC xóa ds/kq/runChon, lỗi, trạng thái, vẽ
        dau = loi.index("if (!dung()) return;")
        for hieu_ung in ("ds = null", "dsLoi = err.message", "trangThai(", "ve_()"):
            self.assertLess(dau, loi.index(hieu_ung), hieu_ung)
        self.assertNotIn("Dữ liệu mới đã về trong lúc bạn đang nhập", nd)  # không ghi trạng thái A vào nháp B
        self.assertNotIn("if (fs())", nd)  # thế hệ form nằm trong fence chung, không chỉ chặn ve_() cuối

    def test_fix03_f3_nut_bao_cao_that(self):
        js = self.js
        eb = js[js.index("function exportButtons("):js.index("function historyPanel(")]
        self.assertIn('"LOG"].flatMap(l => art.filter(a => a.loai === l).map(a =>', eb)  # mảng phẳng các nút
        self.assertNotIn('"LOG"].map(l =>', eb)
        self.assertIn("onclick: () => tai(a)", eb)  # đúng artifact đã đăng ký → route tải theo quyền hiện hành
        # el() chỉ làm phẳng MỘT mức: mọi nơi khác truyền con ở tối đa một mức mảng
        self.assertIn("for (const c of con.flat())", js)

    def test_fix02_f5_mount_sau_khi_gan_vao_document(self):
        m4 = (SRC / "m4" / "giao_dien" / "m4.js").read_text(encoding="utf-8")
        ve = m4[m4.index("function veHd()"):m4.index("veDsHd(); veDsDot();", m4.index("function veHd()"))]
        self.assertLess(ve.index("box.replaceChildren(card);"), ve.index('if (tab === "review") veReview(noi);'))
        self.assertNotIn('else if (tab === "review") veReview(noi);', ve)
        vr = m4[m4.index("function veReview(box)"):m4.index("function veLoTrinh(")]
        self.assertLess(vr.index("if (!vung.isConnected) return;"), vr.index("R.ve(vung"))
        self.assertIn('if (tab === "review" && hd && hdChon) veHd();', vr)  # script nạp xong: vẽ theo ngữ cảnh HIỆN HÀNH
        rv = self.js
        self.assertIn("if (!ctx || !vungSong() || K.vaiDangChan(\"m4_review\")) return;", rv)  # fence isConnected giữ nguyên

    def test_fix01_r3_review_khong_giu_lock_toan_cuc(self):
        src = (SRC / "giao_dien" / "m4.py").read_text(encoding="utf-8")
        dong = src.splitlines()
        i = next(n for n, d in enumerate(dong) if "return h.send_content(200, _review_lenh(app, svc, me, ten, payload))" in d)
        j = max(n for n in range(i) if "with app.mutation_lock:" in dong[n])
        thut = lambda d: len(d) - len(d.lstrip())  # noqa: E731
        self.assertEqual(thut(dong[i]), thut(dong[j]))  # gọi lệnh Review NGOÀI khối lock (cùng mức thụt với `with`)
        self.assertIn("kiem_role_ung_dung(web)", src)
        self.assertIn("kiem_ket_noi_chu(chu, web)", src)
        lenh = src[src.index("def _review_lenh("):src.index("def _q(")]
        self.assertIn("finally:", lenh)
        self.assertLess(lenh.index("finally:"), lenh.index("chu.close()"))

    def test_m4_js_mount_mot_tai_san(self):
        m4 = (SRC / "m4" / "giao_dien" / "m4.js").read_text(encoding="utf-8")
        self.assertIn("/m4/review.js", m4)
        self.assertIn('["review", "Review L1/L2"]', m4)
        css = (SRC / "m4" / "giao_dien" / "m4.css").read_text(encoding="utf-8")
        for dong in css[css.index("/* M4-02A"):].splitlines()[1:]:
            if dong.strip() and not dong.lstrip().startswith(("@media", "}", "font-variant", "/*")):
                self.assertTrue(".m4 .m4-rv" in dong or dong.startswith(" "), dong)


# ================================================================================================== M4-DL5a · DEMO
def _dl5_data():
    from test_m4_review_phu_luc_pg import _pl, _dong
    data = {"trang_thai": "HIEN_HANH", "nguon_id": "DEMO-DL5",
            "phu_luc": [_pl(11, "2026-02-01", gt_sau_vat=108, gt_hd_sau_pl=324),
                        _pl(22, "2026-03-01", gt_sau_vat=-108, gt_hd_sau_pl=216)],
            "thay_doi_tham_so": [dict(pl_id=11, ma_ts="TT-20", gia_tri_cu="90%", gia_tri_moi="95%", trich_dan="DEMO Điều 1"),
                                 dict(pl_id=22, ma_ts="TT-20", gia_tri_cu="95%", gia_tri_moi="", trich_dan=None)],
            "boq_dong": [_dong(1, "DEMO-A", kl=1, don_gia=100), _dong(2, "DEMO-B", kl=1, don_gia=100),
                         _dong(3, "DEMO-A", "THAY", 11, kl=2, don_gia=None, ten=""),
                         _dong(4, "DEMO-C", "THEM", 11, kl=0, don_gia=100),
                         _dong(5, "DEMO-B", "BO", 22)]}
    for row in data["boq_dong"]:
        row["ma_rieng"] = row["ma_hm"]
    return data


def _dl5_basis(identity="00000000-0000-0000-0000-000000000001"):
    return {"hop_dong": {"id": str(identity), "so_hop_dong": "DEMO/HĐ/DL5", "trang_thai_pl": "CO_DU"},
            "dot": {"ngay_nghiem_thu": "2026-03-01", "so_dot": 1},
            "tham_so": [{"ma": ma, "gia_tri": value, "trang_thai": "CO_GIA_TRI"} for ma, value in
                        (("TT-02", "200"), ("TT-03", "Chưa gồm VAT"), ("TT-04", "8%"), ("TT-20", "90%"))],
            "phu_luc": [], "boq": [], "manual_map": []}


def _dl5_mock_owner(session, data=None, state=None):
    from unittest.mock import MagicMock, Mock
    from kho_tri_thuc.m4.review_phu_luc_pg import _COT
    data = _dl5_data() if data is None else data
    owner = MagicMock()
    session.execute.return_value.fetchone.return_value = {"duoc": True}
    responses = [[state or dict(nguon_id=data["nguon_id"], co_nguon=True, co_hd=True)]]
    responses += [[{c: r.get(c) for c in _COT[table]} for r in data[table]] for table in _COT]

    def execute(query, params=()):
        session.execute.assert_called_once()  # quyền phải được kiểm trước mọi đọc owner
        cursor = Mock(description=[])
        cursor.fetchall.return_value = responses.pop(0)
        return cursor
    owner.execute.side_effect = execute
    return owner


class DL5SnapshotTinh(unittest.TestCase):
    def test_khong_phien_khong_doc_khong_nap(self):
        from unittest.mock import Mock
        co, owner = _dl5_basis(), Mock()
        self.assertIs(NR.chup_review_l2(co, owner, conn_phien=None), co)
        owner.execute.assert_not_called()
        owner.transaction.assert_not_called()

    def test_khong_quyen_khong_doc_owner(self):
        from unittest.mock import Mock
        from kho_tri_thuc.ha_tang.primitives import DataError
        owner, session = Mock(), Mock()
        session.execute.return_value.fetchone.return_value = {"duoc": False}
        with self.assertRaises(DataError) as caught:
            NR.chup_review_l2(_dl5_basis(), owner, conn_phien=session)
        self.assertEqual(caught.exception.code, "M4_REVIEW_KHONG_THAY")
        owner.execute.assert_not_called()

    def test_ba_null_giu_nguyen_basis_va_hash(self):
        from unittest.mock import Mock
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        for co_nguon, co_hd in ((False, False), (True, False), (True, True)):
            with self.subTest(co_nguon=co_nguon, co_hd=co_hd):
                co, session = _dl5_basis(), Mock()
                before = XayDungK2._sha_co_so(co)
                owner = _dl5_mock_owner(session, state=dict(nguon_id=None, co_nguon=co_nguon, co_hd=co_hd))
                actual = NR.chup_review_l2(co, owner, conn_phien=session)
                self.assertIs(actual, co)
                self.assertEqual(XayDungK2._sha_co_so(actual), before)
                owner.execute.assert_called_once()

    def test_chup_du_ba_bang_khong_limit_dung_mot_nguon(self):
        from unittest.mock import Mock
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        session = Mock()
        owner = _dl5_mock_owner(session)
        co = _dl5_basis()
        before = XayDungK2._sha_co_so(co)
        result = NR.chup_review_l2(co, owner, conn_phien=session)
        self.assertEqual([len(result["review_chep"][t]) for t in ("phu_luc", "thay_doi_tham_so", "boq_dong")], [2, 2, 5])
        self.assertEqual(len(co["phu_luc"]), 0)  # không sửa basis caller
        self.assertNotEqual(before, XayDungK2._sha_co_so(result))
        import copy
        changed = copy.deepcopy(result)
        changed["review_chep"]["thay_doi_tham_so"][0]["gia_tri_moi"] = "96%"
        self.assertNotEqual(XayDungK2._sha_co_so(changed), XayDungK2._sha_co_so(result))
        for call in owner.execute.call_args_list[1:]:
            self.assertEqual(call.args[1], ("DEMO-DL5", co["hop_dong"]["id"]))
            self.assertNotIn("LIMIT", call.args[0])

    def test_trung_pl_va_boq_khong_chon_nguon(self):
        from kho_tri_thuc.ha_tang.primitives import DataError
        for conflict in ("pl", "boq"):
            co = _dl5_basis()
            if conflict == "pl":
                co["phu_luc"] = [dict(id="DEMO-op", so_pl="demo-pl-11", ngay_ky="2026-01-01",
                                      ngay_hieu_luc="2026-02-01", trang_thai="DA_KY", doi_boq=True)]
            else:
                co["boq"] = [dict(id="DEMO-op", phu_luc_id=None, trang_thai="DA_MAP", dong=[])]
            result = NR._basis_review_l2(co, _dl5_data())
            self.assertTrue(result["review_chep"]["can_xem_lai"])
            with patch.object(NR, "_m") as vendor, self.assertRaises(DataError) as caught:
                NR.projection_l2(result)
            vendor.assert_not_called()
            self.assertEqual(caught.exception.code, "M4_REVIEW_CAN_XEM_LAI")
            self.assertIn("Cần xem lại", str(caught.exception))

    def test_xung_dot_cong_bo_failed_co_co_can_xem_lai_khong_chay_worker(self):
        from unittest.mock import Mock
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        svc = object.__new__(XayDungK2)
        svc.root = Path(tempfile.mkdtemp(prefix="DEMO-DL5-"))
        svc._raw = Mock(side_effect=AssertionError("Không đọc tệp khi xung đột"))
        svc._chay_worker = Mock(side_effect=AssertionError("Không tính khi xung đột"))
        svc._luu_artifact = Mock(return_value={"loai": "DEMO"})
        co = _dl5_basis()
        co["boq"] = [dict(phu_luc_id=None)]
        co = NR._basis_review_l2(co, _dl5_data())
        co["tep"] = {"raw_sha256": "a" * 64, "byte_length": 1}
        result, artifacts, reason = svc._review_tinh("DEMO-run", co, "b" * 64, "L1_L2", None)
        self.assertEqual(result["trang_thai"], "FAILED")
        self.assertIn("Cần xem lại", result["loi"])
        self.assertIn("Cần Anh/lead", reason)
        self.assertTrue(artifacts)
        svc._raw.assert_not_called()
        svc._chay_worker.assert_not_called()

    def test_k2_truyen_phien_vao_chup_trong_basis(self):
        from unittest.mock import Mock
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        svc = object.__new__(XayDungK2)
        owner, session = Mock(), Mock()
        hd = _dl5_basis()["hop_dong"]
        svc._r1 = Mock(side_effect=[{}, dict(id="DEMO-dot", hop_dong_id=hd["id"]), hd, None, None, {"d": "DEMO"}])
        svc._rn = Mock(return_value=[])
        with patch("kho_tri_thuc.k2.xay_dung.DD.lich_su_da_duyet", return_value=None), patch.object(NR, "chup_review_l2", return_value={"DEMO": True}) as capture:
            result = svc._co_so(owner, conn_phien=session, du_an="DEMO", tep="DEMO", dot="DEMO", che_do="L1_L2", o_dich=None)
        self.assertEqual(result, {"DEMO": True})
        self.assertIs(capture.call_args.args[1], owner)
        self.assertIs(capture.call_args.kwargs["conn_phien"], session)
        self.assertEqual(capture.call_args.args[0]["hop_dong"], hd)

    def test_projection_du_cot_lich_su_null_zero_chi_doc(self):
        # Thuần SQLite: dùng đúng DDL ghim, không cần openpyxl để kiểm biên nạp.
        import ast
        import sqlite3
        tree = ast.parse((NR.GOC / "csdl_hop_dong.py").read_text(encoding="utf-8"))
        schema = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "SCHEMA" for t in n.targets))
        # Chạy nguyên AST các hàm SQL thuần nguồn (không import phần Excel).
        # Kiểm SHA trước compile, không viết lại thuật toán hay bỏ điều kiện ngày.
        source = (NR.GOC / "csdl_hop_dong.py").read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(), NR.PIN["csdl_hop_dong.py"])
        namespace = {}
        pure = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in
                               ("phu_luc_ap_dung", "boq_hieu_luc", "_f", "tham_so_hieu_luc")], type_ignores=[])
        exec(compile(pure, str(NR.GOC / "csdl_hop_dong.py"), "exec"), namespace)
        cs = SimpleNamespace(SCHEMA=schema, tien=lambda v: float(v), ty_le=lambda v: float(v.rstrip("%")) / 100)
        data = _dl5_data()
        from test_m4_review_phu_luc_pg import _pl, _dong
        data["phu_luc"].append(_pl(33, "2026-02-01", so_pl="DEMO-PL-11", trang_thai="Đã hủy", ly_do_huy="DEMO hủy"))
        data["boq_dong"].append(_dong(6, "DEMO-A", "BO", 33))
        base = _dl5_basis()
        base["phu_luc"] = [dict(id="11", so_pl="DEMO-OP", ngay_ky="2026-01-01", ngay_hieu_luc="2026-02-01", doi_boq=False, trang_thai="DU_THAO")]
        co = NR._basis_review_l2(base, data)
        with patch.object(NR, "_m", side_effect=lambda name: cs if name == "csdl_hop_dong" else SimpleNamespace(khoa=lambda r: "DEMO")):
            con, mapping = NR.projection_l2(co)
        try:
            self.assertEqual(con.execute("SELECT count(*) FROM phu_luc").fetchone()[0], 4)
            self.assertEqual(con.execute("SELECT count(*) FROM boq_dong").fetchone()[0], 6)
            self.assertEqual(tuple(con.execute("SELECT kl,don_gia,ten FROM boq_dong WHERE thao_tac='THAY'").fetchone()), (2, None, ""))
            self.assertEqual(con.execute("SELECT kl FROM boq_dong WHERE thao_tac='THEM'").fetchone()[0], 0)
            self.assertEqual([r[0] for r in con.execute("SELECT gia_tri_moi FROM thay_doi_tham_so ORDER BY pl_id")], ["95%", ""])
            self.assertEqual(tuple(con.execute("SELECT gt_sau_vat,gt_hd_sau_pl FROM phu_luc WHERE trang_thai='Đã ký' ORDER BY id").fetchone()), (108, 324))
            self.assertEqual(len(mapping["phu_luc"]), 4)
            direct, ma = _dl5_direct(cs)
            try:
                for day, expected in (("2026-02-15", {"DEMO-A", "DEMO-B", "DEMO-C"}), ("2026-03-15", {"DEMO-A", "DEMO-C"})):
                    actual = namespace["boq_hieu_luc"](con, mapping["ma_hd"], day)
                    self.assertEqual(actual, namespace["boq_hieu_luc"](direct, ma, day))
                    self.assertEqual(set(actual[0]), expected)
                    self.assertEqual(namespace["tham_so_hieu_luc"](con, mapping["ma_hd"], "TT-20", day),
                                     namespace["tham_so_hieu_luc"](direct, ma, "TT-20", day))
            finally:
                direct.close()
            with self.assertRaises(sqlite3.OperationalError):
                con.execute("INSERT INTO che_do VALUES (2,0)")
        finally:
            con.close()


def _dl5_direct(cs=None):
    """CSDL SQLite DEMO độc lập; không dùng projection làm expected."""
    import sqlite3
    from kho_tri_thuc.m4.review_phu_luc_pg import _COT
    cs = cs or NR._m("csdl_hop_dong")
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(cs.SCHEMA)
    ma = NR.ma_hd_projection(_dl5_basis()["hop_dong"]["id"])
    con.execute("INSERT INTO hop_dong (ma_hd,so_hd,gia_tri_hd,gom_vat,vat) VALUES (?,?,?,?,?)", (ma, "DEMO/HĐ/DL5", 200, "Chưa gồm VAT", .08))
    for t in _dl5_basis()["tham_so"]:
        con.execute("INSERT INTO tham_so (ma_hd,ma_ts,gia_tri,trang_thai) VALUES (?,?,?,'CO_GIA_TRI')", (ma, t["ma"], t["gia_tri"]))
    data = _dl5_data()
    for table, columns in _COT.items():
        for r in data[table]:
            values = [ma if c == "ma_hd" else r.get(c) for c in columns]
            con.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", values)
    con.commit()
    return con, ma


def _dl5_parity(test, basis):
    import copy
    cs, nv = NR._m("csdl_hop_dong"), NR._m("may_chu.nghiep_vu")
    direct, ma = _dl5_direct()
    projected, mapping = NR.projection_l2(basis)
    test.addCleanup(direct.close)
    test.addCleanup(projected.close)
    for day, codes in (("2026-02-15", {"DEMO-A", "DEMO-B", "DEMO-C"}), ("2026-03-15", {"DEMO-A", "DEMO-C"})):
        with test.subTest(ngay=day):
            test.assertEqual(cs.boq_hieu_luc(direct, ma, day), cs.boq_hieu_luc(projected, mapping["ma_hd"], day))
            test.assertEqual(set(cs.boq_hieu_luc(projected, mapping["ma_hd"], day)[0]), codes)
            test.assertEqual(cs.tham_so_hieu_luc(direct, ma, "TT-20", day), cs.tham_so_hieu_luc(projected, mapping["ma_hd"], "TT-20", day))
            info = dict(so_pl="DEMO-PL-33", ngay_ky=day, ngay_hieu_luc=day, trang_thai="Đã ký", doi_boq="Không", nguoi_nhap="DEMO")
            a_rows = [dict(dong=1, ma_ts="TT-20", cu="95%", moi="97%", trich="DEMO Điều 2")]
            p_results, b_results = [], []
            for con, code in ((direct, ma), (projected, mapping["ma_hd"])):
                hd = dict(con.execute("SELECT * FROM hop_dong WHERE ma_hd=?", (code,)).fetchone())
                p_results.append(cs.kiem_tra_phu_luc(con, hd, info, copy.deepcopy(a_rows), [], [])[0])
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "DEMO"
                ws.append(["STT", "Mã hạng mục", "Tên công việc", "Đơn vị", "KL hợp đồng", "KL kỳ này", "KL lũy kế hết kỳ này", "Đơn giá", "GT kỳ này"])
                for i, item in enumerate(("DEMO-A", "DEMO-B", "DEMO-C"), 1):
                    ws.append([i, item, "DEMO hạng mục", "DEMO m2", 1, 1, 1, 100, 100])
                ws.append([None, None, "Cộng", None, None, None, None, None, 300])
                k = cs.tinh_doi_chieu_dot(con, code, "DEMO.xlsx", day, 1, wv=wb)
                test.assertTrue(k["rows"], "Fixture phải có dòng thực sự đi qua thuật toán B")
                ph = nv._lop2(k)
                checklist = nv.bang_kiem_lop2(k, ph[0], cs, con)
                b_results.append((ph, checklist, nv._lop2b(SimpleNamespace(kq={"cay": [], "nhung": []}), k, cs, con, bang=checklist[1])))
                wb.close()
            test.assertEqual(p_results[0], p_results[1])
            test.assertTrue(p_results[0])
            test.assertEqual(b_results[0], b_results[1])


@unittest.skipUnless(openpyxl is not None and _nguon_da_nap(), "Thiếu openpyxl/lõi ghim — parity cần lead chạy")
class DL5ParityTinh(unittest.TestCase):
    def test_parity_p_b_boq_hai_ngay(self):
        _dl5_parity(self, NR._basis_review_l2(_dl5_basis(), _dl5_data()))

    def test_ba_null_ket_qua_cu_khong_doi(self):
        from unittest.mock import Mock
        cs = NR._m("csdl_hop_dong")
        co = CanNguon()._co_so()
        before, bd = NR.projection_l2(co)
        self.addCleanup(before.close)
        expected = cs.boq_hieu_luc(before, bd["ma_hd"], "2026-03-01")
        for has_source, has_hd in ((False, False), (True, False), (True, True)):
            session = Mock()
            owner = _dl5_mock_owner(session, state=dict(nguon_id=None, co_nguon=has_source, co_hd=has_hd))
            result = NR.chup_review_l2(co, owner, conn_phien=session)
            con, mapping = NR.projection_l2(result)
            try:
                self.assertEqual(cs.boq_hieu_luc(con, mapping["ma_hd"], "2026-03-01"), expected)
            finally:
                con.close()


@unittest.skipUnless(os.environ.get("KHO_PG_DSN_TEST") and openpyxl is not None and _nguon_da_nap(), "Thiếu KHO_PG_DSN_TEST/openpyxl/lõi ghim")
class DL5ParityPG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Dùng hạ tầng DEMO DL3: CREATE kho_test_* riêng, migrate và phiên app_web
        # có quyền XEM. Không kế thừa lớp test để tránh chạy lặp các test DL3.
        from test_m4_review_phu_luc_pg import ReviewPhuLucPGTests
        ReviewPhuLucPGTests.setUpClass.__func__(cls)

    def test_parity_p_b_boq_tu_ban_chup_pg(self):
        from test_m4_review_phu_luc_pg import ReviewPhuLucPGTests, CHUP
        ReviewPhuLucPGTests.setUp(self)
        data = _dl5_data()
        raw = {t: data[t] for t in ("phu_luc", "thay_doi_tham_so", "boq_dong")}
        self.repo.ghi_lan_chup(raw, du_lieu_dl2=dict(che_do=[], hop_dong=[dict(ma_hd="DEMO-HD", so_hd="DEMO/HĐ/DL5")], tham_so=[], tham_so_nguon=[]),
                              nguon_id=self.source, chup_luc=CHUP, nhap_boi="MO_PHONG_DEMO", anh_xa={"DEMO-HD": (self.hd, self.da)})
        basis = NR.chup_review_l2(_dl5_basis(self.hd), self.con, conn_phien=self.web)
        # Chuẩn hóa duy nhất khóa cục bộ HĐ của expected, không đổi dữ liệu tính.
        basis["hop_dong"]["id"] = _dl5_basis()["hop_dong"]["id"]
        _dl5_parity(self, basis)


if __name__ == "__main__":
    unittest.main()
