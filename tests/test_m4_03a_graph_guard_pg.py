"""M4-03A graph guard — kiểm PostgreSQL THẬT: L3 chạy lại + công bố sau seal ⇒ nguồn KT HOLD. CODE_ONLY: WRITTEN_NOT_RUN.

Cùng cổng/env/ràng buộc với tests/test_m4_03a_pg.py (KHO_M4_03A_*; không env → SkipTest NOT_VERIFIED, không phải PASS; clone/registry/quyền không
chứng minh được → LoiThietLap TRƯỚC mọi ghi). Dùng lại hàm module + helper của bộ gốc (mượn thuộc tính lớp, KHÔNG import lớp TestCase vào namespace
này → 13 test gốc không chạy lại ở đây). Chỉ dùng login KT1; cổng đọc vẫn đòi KT2 còn vai KE_TOAN → chạy trên clone mới hoặc TRƯỚC P99 của bộ gốc.

Producer THẬT, không INSERT giả duyệt/seal/đồ thị, không monkeypatch readiness/SQL/engine:
G01 hồ sơ F (nhánh riêng, không chạy lại L3): seal → KT lưu NA đủ → xác nhận thành công (baseline dương, chống always-HOLD).
G02 hồ sơ E: seal A → KT lưu NA đủ → quyen.xac_nhan=true (dương TRƯỚC) → chung_tu_chay_lai THẬT công bố B cùng phiên bản → producer M24 chọn B
    (run_id/basis khác A), hàng seal/phong bì/PDF/kết luận A bất biến → KT HOLD (đọc/danh sách/lịch sử), lưu/xác nhận/khóa mới/replay/SQL trực tiếp
    bị chặn, delta 0 toàn bảng; GET lịch sử + PDF A giữ đúng ngữ cảnh/bytes; hồ sơ F vẫn hiện hành.
G03 hồ sơ E tiếp: phiên bản kế tiếp chưa seal vẫn HOLD; kết luận/duyệt/PDF trên đồ thị B ⇒ phong bì mới hiện hành lại, lưu được; phong bì A chỉ lịch sử.
Chưa phủ (NOT_VERIFIED, ghi ở báo cáo): lần chạy L3 chưa công bố/FAILED sau seal (không có lệnh public tạo ổn định mà không INSERT giả).
"""

from __future__ import annotations

import json
import unittest

from tests import test_m4_03a_pg as P
from tests.test_m4_02c_pg import A1, chay_l3

from kho_tri_thuc.m4 import ke_toan_nghiem_thu as KT
from kho_tri_thuc.m4 import sql_ke_toan_nghiem_thu as SK

_G = vars(P.M4KeToanPG)  # descriptor gốc (hàm / staticmethod / classmethod) — không phải lớp TestCase
BANG_M24 = ("duyet_phien_ban", "duyet_ket_luan", "duyet_quyet_dinh", "duyet_pdf", "duyet_seal", "duyet_kt_cho", "duyet_kt_phong_bi", "kt_xac_nhan")
QUYEN_HOLD = {"xem": True, "luu": False, "xac_nhan": False, "tai_pdf": True}


@unittest.skipUnless(P.CO_ENV, P.LY_DO_SKIP)
class M4GraphGuardPG(unittest.TestCase):
    """Chạy theo thứ tự g01 → g03 trên MỘT clone; trạng thái qua cls.s."""

    setUpClass = _G["setUpClass"]
    _svc_moi = _G["_svc_moi"]
    K, q, ma, loi, can = _G["K"], _G["q"], _G["ma"], _G["loi"], _G["can"]
    dem_tat_ca, doi, ghi_mot = _G["dem_tat_ca"], _G["doi"], _G["ghi_mot"]
    chap_thuan, ket_luan, pdf, ho_so_seal = _G["chap_thuan"], _G["ket_luan"], _G["pdf"], _G["ho_so_seal"]
    phong_bi, kt_db, xem, kiem_ack, kiem_xem = _G["phong_bi"], _G["kt_db"], _G["xem"], _G["kiem_ack"], _G["kiem_xem"]
    than_luu, than_xn, du_day = _G["than_luu"], _G["than_xn"], _G["du_day"]

    # ------------------------------------------------------------------ helpers riêng
    def anh(self, dot) -> dict:
        """Ảnh CHÍNH XÁC mọi hàng M24/KT của đợt (owner) — bằng chứng seal/phong bì/PDF/kết luận/lịch sử không bị sửa."""
        return {b: self.q(f"SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY x.id), '[]'::jsonb) FROM m4.{b} x WHERE x.dot_id = %s", (dot,))
                for b in BANG_M24}

    def l3_seal(self, ket_luan_id) -> str:
        return str(self.q("SELECT l3_run_id FROM m4.duyet_ket_luan WHERE id = %s", (ket_luan_id,)))

    def m24(self, dot, version_id=None) -> dict:
        return self.svc.duyet_xem(A1, dot_id=dot, version_id=version_id)

    def luu_sql(self, than):
        yc = {k: v for k, v in than.items() if k != "khoa"}
        return self.kt._goi(self.svc.danh_tinh(self.KT1), "SELECT m4.kt_luu(%s, %s::jsonb, %s::uuid, %s::uuid, %s, %s::integer, %s::jsonb) AS r",
                            (than["khoa"], json.dumps(yc, ensure_ascii=False), than["kt_pending_id"], than["phong_bi_id"],
                             than["expected_phong_bi_sha256"], than["expected_revision"],
                             json.dumps({k: than[k] for k in KT.DU_LIEU}, ensure_ascii=False)), than["khoa"])

    def dong(self, cho) -> dict:
        return next(r for r in self.kt.danh_sach(self.KT1)["items"] if r["kt_pending_id"] == cho)

    # ------------------------------------------------------------------ G01 baseline dương (không chạy lại L3)
    def test_g01_baseline_khong_chay_lai_van_xac_nhan(self):
        h = self.ho_so_seal("GF")
        m = self.m24(h["dot"])
        self.assertEqual(str(m["do_thi"]["l3"]["run_id"]), self.l3_seal(m["seal"]["ket_luan_id"]))  # đồ thị hiện hành = L3 đã seal
        x = self.xem(h["cho"])
        self.assertEqual((x["can_cu_hien_hanh"], x["quyen"]["luu"]), (True, True))
        truoc = self.dem_tat_ca()
        than = self.than_luu(x, self.K("GF-luu"), **self.du_day("KHONG_AP_DUNG", ly_do=P.LY_DO_NA))
        a = self.kt.luu(self.KT1, than)
        self.kiem_ack(a, khoa=than["khoa"], revision=1, trang_thai=KT.TT_CHO_XAC_NHAN, lap_lai=False, hanh_dong="LUU")
        self.ghi_mot(truoc)
        x = self.xem(h["cho"])
        self.assertEqual(x["quyen"], {"xem": True, "luu": True, "xac_nhan": True, "tai_pdf": True})
        truoc = self.dem_tat_ca()
        bx = self.than_xn(x, self.K("GF-xn"))
        xn = self.kt.xac_nhan(self.KT1, bx)
        self.kiem_ack(xn, khoa=bx["khoa"], revision=2, trang_thai=SK.TT_DA_XAC_NHAN, lap_lai=False, hanh_dong="XAC_NHAN")
        self.ghi_mot(truoc)
        self.assertEqual(self.xem(h["cho"])["can_cu_hien_hanh"], True)
        self.s["F"] = h

    # ------------------------------------------------------------------ G02 L3 chạy lại + công bố B sau seal A ⇒ HOLD
    def test_g02_l3_cong_bo_lai_sau_seal_hold(self):
        h = self.ho_so_seal("GE")
        dot, cho = h["dot"], h["cho"]
        pb1 = self.phong_bi(cho)[0]
        m_a = self.m24(dot)
        l3_a = self.l3_seal(m_a["seal"]["ket_luan_id"])
        self.assertEqual((str(m_a["do_thi"]["l3"]["run_id"]), l3_a), (str(h["run"]), str(h["run"])))
        # dương TRƯỚC chạy lại: hiện hành, lưu NA đủ, quyền xác nhận true
        x = self.xem(cho)
        self.kiem_xem(x, h, pb1)
        self.assertTrue(x["can_cu_hien_hanh"])
        truoc = self.dem_tat_ca()
        than1 = self.than_luu(x, self.K("GE-luu-1"), **self.du_day("KHONG_AP_DUNG", ly_do=P.LY_DO_NA))
        a1 = self.kt.luu(self.KT1, than1)
        self.kiem_ack(a1, khoa=than1["khoa"], revision=1, trang_thai=KT.TT_CHO_XAC_NHAN, lap_lai=False, hanh_dong="LUU")
        self.ghi_mot(truoc)
        x_a = self.xem(cho)
        self.assertEqual((x_a["can_cu_hien_hanh"], x_a["quyen"]), (True, {"xem": True, "luu": True, "xac_nhan": True, "tai_pdf": True}))
        self.assertEqual(self.dong(cho)["trang_thai"], KT.TT_CHO_XAC_NHAN)
        bx = self.than_xn(x_a, self.K("GE-xn-1"))
        anh_a, db_a = self.anh(dot), self.kt_db(cho)

        # chạy lại L3 THẬT (SOAN, lệnh public) trên CÙNG phiên bản — công bố B
        run_b = str(chay_l3(self.svc, dot, self.K("GE-l3-b"), cha=h["run"]))
        self.assertNotEqual(run_b, l3_a)
        self.assertIs(self.q("SELECT x.cong_bo FROM m4.chung_tu_result x WHERE x.run_id = %s", (run_b,)), True)
        m_b = self.m24(dot)
        self.assertEqual(str(m_b["do_thi"]["l3"]["run_id"]), run_b)  # producer M24 chọn B
        self.assertNotEqual(m_b["context"]["basis_sha256"], m_a["context"]["basis_sha256"])  # đồ thị B ≠ A
        self.assertEqual((m_b["context"]["version_id"], m_b["seal"], m_b["trang_thai"]), (m_a["context"]["version_id"], m_a["seal"], "DA_SEAL"))
        self.assertEqual(self.anh(dot), anh_a)  # seal/phong bì/PDF/kết luận/phiên bản/KT A không đổi
        self.assertEqual(self.l3_seal(m_a["seal"]["ket_luan_id"]), l3_a)

        # đọc: HOLD, giữ ngữ cảnh/nguồn/lịch sử A
        x_b = self.xem(cho)
        self.kiem_xem(x_b, h, pb1)
        self.assertEqual((x_b["can_cu_hien_hanh"], x_b["quyen"]), (False, QUYEN_HOLD))
        self.assertEqual((x_b["context"], x_b["nguon"], x_b["kt"]), (x_a["context"], x_a["nguon"], x_a["kt"]))
        self.assertEqual([(r["thu_tu"], r["can_cu_hien_hanh"], r["context"]) for r in x_b["lich_su"]["phong_bi"]], [(1, False, x_a["context"])])
        self.assertEqual([(r["kt"]["revision"], r["context"]) for r in x_b["lich_su"]["kt"]], [(1, x_a["context"])])
        self.assertEqual(self.xem(cho, pb=pb1["id"])["context"], x_a["context"])  # GET lịch sử tường minh
        self.assertEqual(self.kt.tep_pdf(self.KT1, cho, pb1["id"]), (h["ten_pdf"], "application/pdf", h["raw"]))
        row = self.dong(cho)
        self.assertEqual((row["phong_bi_id"], row["revision"], row["trang_thai"]), (pb1["id"], 1, KT.TT_CAN_KIEM_LAI))

        # ghi: lệnh mới / xác nhận / replay cùng khóa / SQL trực tiếp — chặn dưới khóa, delta 0
        truoc = self.dem_tat_ca()
        self.assertEqual(self.loi(self.kt.luu, self.KT1, self.than_luu(x_a, self.K("GE-luu-2"), **self.du_day("KHONG_AP_DUNG", ly_do=P.LY_DO_NA))),
                         "M4_KT_CAN_KIEM_LAI")
        self.assertEqual(self.loi(self.kt.xac_nhan, self.KT1, bx), "M4_KT_CAN_KIEM_LAI")
        self.assertEqual(self.loi(self.kt.luu, self.KT1, than1), "M4_KT_NGUON_CU")  # replay đúng khóa+body cũ không trả kết quả nguồn cũ
        self.assertEqual(self.loi(self.luu_sql, self.than_luu(x_a, self.K("GE-luu-sql"), **self.du_day("KHONG_AP_DUNG", ly_do=P.LY_DO_NA))),
                         "M4_KT_CAN_KIEM_LAI")
        self.doi(truoc)
        self.assertEqual((self.kt_db(cho), self.anh(dot)), (db_a, anh_a))
        if "F" in self.s:  # chạy lại L3 của đợt E không làm hồ sơ khác stale
            self.assertTrue(self.xem(self.s["F"]["cho"])["can_cu_hien_hanh"])
        self.s["E"] = {**h, "pb1": pb1, "run_b": run_b, "x_a": x_a, "than1": than1}

    # ------------------------------------------------------------------ G03 phiên bản đính chính seal trên đồ thị B ⇒ hiện hành lại
    def test_g03_dinh_chinh_seal_tren_do_thi_b(self):
        self.can("E")
        e = self.s["E"]
        dot, cho, pb1 = e["dot"], e["cho"], e["pb1"]
        c = self.m24(dot)["context"]
        v2 = self.svc.duyet_phien_ban(A1, dot_id=dot, parent_version_id=e["v1"], revision=c["revision"], expected_basis=c["basis_sha256"],
                                      ly_do="Đính chính sau khi Chứng từ L3 công bố lại (DEMO)", khoa=self.K("GE-pb2"))["phien_ban_id"]
        c = self.m24(dot, v2)["context"]
        self.svc.duyet_phien_ban_nop(A1, dot_id=dot, version_id=v2, revision=0, expected_basis=c["basis_sha256"], khoa=self.K("GE-nop2"))
        x = self.xem(cho)  # kế tiếp chưa seal: vẫn HOLD, không phong bì giả
        self.assertEqual((x["can_cu_hien_hanh"], x["quyen"], len(self.phong_bi(cho))), (False, QUYEN_HOLD, 1))
        self.ket_luan(dot, "GE-kl-v2")
        self.assertEqual(self.chap_thuan(dot, "GE-ct-v2")["trang_thai"], "CHO_PDF")
        raw2 = P.F.ho_so_dot_duyet_pdf(f"KT-{self.run_id}-GE-dinh-chinh")
        p2 = self.pdf(dot, raw2, "GE-pdf-v2", "ho_so_da_duyet_GE_v2.pdf")
        self.assertEqual((p2["trang_thai"], str(p2["kt_pending_id"])), ("DA_SEAL", cho))
        m = self.m24(dot)
        self.assertEqual((self.l3_seal(m["seal"]["ket_luan_id"]), str(m["do_thi"]["l3"]["run_id"])), (e["run_b"], e["run_b"]))
        pbs = self.phong_bi(cho)
        self.assertEqual([(p["thu_tu"], p["truoc_id"]) for p in pbs], [(1, None), (2, pb1["id"])])
        x = self.xem(cho)
        self.kiem_xem(x, e, pbs[1])
        self.assertIsNone(x["kt"])
        self.assertEqual((x["can_cu_hien_hanh"], x["quyen"]), (True, {"xem": True, "luu": True, "xac_nhan": False, "tai_pdf": True}))
        self.assertEqual([(r["thu_tu"], r["can_cu_hien_hanh"]) for r in x["lich_su"]["phong_bi"]], [(1, False), (2, True)])
        xa = self.xem(cho, pb=pb1["id"])
        self.assertEqual((xa["context"], xa["can_cu_hien_hanh"], xa["quyen"]), (e["x_a"]["context"], False, QUYEN_HOLD))
        self.assertEqual(self.kt.tep_pdf(self.KT1, cho, pb1["id"])[2], e["raw"])
        truoc = self.dem_tat_ca()
        self.assertEqual(self.loi(self.kt.luu, self.KT1, e["than1"]), "M4_KT_NGUON_CU")  # replay nguồn A vẫn bị chặn
        self.doi(truoc)
        than = self.than_luu(x, self.K("GE-luu-v2"), **self.du_day("KHONG_AP_DUNG", ly_do=P.LY_DO_NA))
        self.assertEqual(than["expected_revision"], 0)
        a = self.kt.luu(self.KT1, than)
        self.kiem_ack(a, khoa=than["khoa"], revision=2, trang_thai=KT.TT_CHO_XAC_NHAN, lap_lai=False, hanh_dong="LUU")  # đơn điệu theo gốc
        self.ghi_mot(truoc)
        self.assertEqual(a["context"]["phong_bi_id"], pbs[1]["id"])
        row = self.dong(cho)
        self.assertEqual((row["phong_bi_id"], row["revision"], row["trang_thai"]), (pbs[1]["id"], 2, KT.TT_CHO_XAC_NHAN))
        self.assertEqual(self.xem(cho)["quyen"]["xac_nhan"], True)


if __name__ == "__main__":
    unittest.main()
