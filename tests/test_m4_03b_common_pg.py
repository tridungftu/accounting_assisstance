"""M4-03B-01 — kiểm PostgreSQL THẬT identity nguồn dùng chung + đối chiếu căn cứ NT ↔ hóa đơn do KT xác nhận. WRITTEN_NOT_RUN.

Ba cổng (thiếu cổng nào → SkipTest NOT_VERIFIED, KHÔNG phải PASS):
1. Cổng 03A (tests/test_m4_03a_pg.py: KHO_M4_03A_* + kiem_clone/registry/quyền) — mượn thuộc tính lớp gốc như test_m4_03a_full_basis_pg
   (không import lớp TestCase → test gốc không chạy lại); DSN chủ bảng phải là ĐÚNG chủ m4.kt_xac_nhan theo session_user.
2. Cổng 03B: env KHO_M4_03B_DA_AP_DUNG=1 (Root đã append `M4_03B_COMMON_SQL` vào registry ở ordinal của Root rồi migrate clone) + kiểm CHỈ ĐỌC:
   mọi bảng/hàm mới tồn tại và thân kho.dc_luu / kho.dc_xac_nhan / kho._dc_do_thi trên clone BẰNG BYTE hằng trong file nguồn. Sai → LoiThietLap.
3. Cổng hóa đơn (chỉ ca cross-source): KHO_M4_03B_HOA_DON_ID = hóa đơn M2 CÓ SẴN trên clone, cùng PN với hồ sơ DEMO, KT1 có module M2 trên PN đó.
   Dương thật cần thêm mst_ban = MST master của đối tác HĐ DEMO (máy chủ resolve, không seed). Lệch MST → ca dương SKIP NOT_VERIFIED kèm
   phụ thuộc chính xác, ca âm BEN_BAN_KHAC vẫn chạy. Tùy chọn: KHO_M4_03B_CFO / KHO_M4_03B_XEM (login M2_READ không phải KT) cho ca từ chối ghi.

Producer THẬT: hồ sơ NT seal + 03A lưu/xác nhận qua service 03A; không INSERT giả nguồn/duyệt/hóa đơn, không monkeypatch SQL/service.
C01 NT-only (không cần M2): xem → lưu NHAP đúng delta → phát lại / khác nội dung / gốc trùng → xác nhận bị chặn (thiếu) delta 0.
C02 03A xác nhận làm đồ thị đổi: revision cũ dẫn xuất CAN_KIEM_LAI, xác nhận cũ bị chặn; lưu revision mới (đúng cùng tập nguồn).
C03 cross-source (cổng 3): xem đủ căn cứ → lưu → xác nhận → KT_XAC_NHAN_CAN_CU; xác nhận lại khóa mới = trung_xac_nhan; thứ tự body ngược
    (hóa đơn trước) = cùng gốc; nhiều-nhiều: cùng hóa đơn với NT khác là gốc khác; 0 hàng tài chính/AP.
C04 stale/CAS: source_version_id cũ → DC_NGUON_CU; expected_graph cũ → DC_DO_THI_DOI; expected_revision cũ → DC_REVISION_CU; đổi tập nguồn → bị chặn.
C05 từ chối: KT_KHAC (ngoài dự án) xem/lưu/lịch sử/xác nhận; CFO/XEM ghi hóa đơn (cổng 3); delta 0.
C06 bỏ qua DB: app DML/EXECUTE lệnh/helper; app giả biên nhận M4/DC_*; owner gọi lệnh không ghim / GUC giả → DC_CAN_KIEM_LAI; delta 0.
C07 đồng thời: hai lệnh tạo cùng tập nguồn khác khóa → đúng một gốc, còn lại DC_DA_CO_GOC.
"""

from __future__ import annotations

import json
import os
import unittest
import uuid

from tests import test_m4_03a_pg as P
from tests.test_m4_02c_pg import _q1

from kho_tri_thuc.k2 import ghi_nhan_chung as GN
from kho_tri_thuc.k2 import sql_ghi_nhan_chung as SG
from kho_tri_thuc.m4 import ghi_nhan_nghiem_thu as AD

_G = vars(P.M4KeToanPG)
ENV_DA_AP_DUNG = "KHO_M4_03B_DA_AP_DUNG"
ENV_HOA_DON = "KHO_M4_03B_HOA_DON_ID"
ENV_CFO, ENV_XEM = "KHO_M4_03B_CFO", "KHO_M4_03B_XEM"
CO_ENV_03B = P.CO_ENV and os.environ.get(ENV_DA_AP_DUNG) == "1"
LY_DO_SKIP_03B = ("NOT_VERIFIED: chưa có clone 03A + M4_03B_COMMON_SQL do Root đăng ký/migrate (KHO_M4_03A_* + KHO_M4_03B_DA_AP_DUNG=1) — "
                  "test M4-03B PG không chạy, KHÔNG tính đạt")
NOI = "\n".join(SG.M4_03B_COMMON_SQL)
BANG_DC = tuple(f"kho.{t}" for t in SG.BANG)
# delta mong của MỘT lần lưu tạo gốc mới với n nguồn mới (identity nguồn chưa có)
GHI_DC = (*BANG_DC, "kho.bien_nhan_thao_tac")


def _than_ham(ten: str) -> str:
    i = NOI.index(f"CREATE OR REPLACE FUNCTION {ten}(")
    a = NOI.index("$$", i)
    return NOI[a + 2:NOI.index("$$", a + 2)]


@unittest.skipUnless(CO_ENV_03B, LY_DO_SKIP_03B)
class M4DoiChieuCanCuPG(unittest.TestCase):
    """Chạy theo thứ tự c01 → c07 trên MỘT clone; trạng thái qua cls.s."""

    @classmethod
    def setUpClass(cls):
        _G["setUpClass"].__func__(cls)
        if _q1(cls.admin, "SELECT m4._kt_phien_chu()") is not True:
            raise P.LoiThietLap("SETUP_FAILURE: DSN chủ bảng không phải ĐÚNG chủ m4.kt_xac_nhan theo session_user — không ghim được chứng thực")
        for t in BANG_DC:
            if _q1(cls.admin, "SELECT to_regclass(%s) IS NOT NULL", (t,)) is not True:
                raise P.LoiThietLap(f"SETUP_FAILURE: clone chưa có {t} — M4_03B_COMMON_SQL chưa được Root đăng ký/migrate")
        for h in (*SG.HAM_LENH, *SG.HAM_NOI_BO, *SG.HAM_DOC, *SG.HAM_TRIGGER):
            if _q1(cls.admin, "SELECT to_regprocedure(%s) IS NOT NULL", (h,)) is not True:
                raise P.LoiThietLap(f"SETUP_FAILURE: clone thiếu hàm {h}")
        for h in ("kho.dc_luu", "kho.dc_xac_nhan", "kho._dc_do_thi", "kho._dc_quyen", "kho._dc_phien_ban_hoan_tat"):
            if _q1(cls.admin, "SELECT p.prosrc FROM pg_proc p WHERE p.oid = to_regproc(%s)", (h,)) != _than_ham(h):
                raise P.LoiThietLap(f"SETUP_FAILURE: thân {h} trên clone khác hằng nguồn — không phải đúng bản đóng băng")
        cls.dc = AD.dich_vu(cls.svc)
        cls.hd_id = os.environ.get(ENV_HOA_DON) or None
        cls.s = {}

    _svc_moi = _G["_svc_moi"]
    K, q, ma, loi, can, song_song = _G["K"], _G["q"], _G["ma"], _G["loi"], _G["can"], _G["song_song"]
    dem_tat_ca = _G["dem_tat_ca"]
    chap_thuan, ket_luan, pdf, ho_so_seal = _G["chap_thuan"], _G["ket_luan"], _G["pdf"], _G["ho_so_seal"]
    xem, than_luu, than_xn, du_day = _G["xem"], _G["than_luu"], _G["than_xn"], _G["du_day"]

    # ------------------------------------------------------------------ helpers riêng
    def doi_dc(self, truoc: dict, **mong):
        """Delta thực tế ĐÚNG bằng mong ('schema__bang' → số hàng); mọi bảng khác (tài chính/M24/AP/Request/M2) 0 delta."""
        sau = self.dem_tat_ca()
        thuc = {t: sau.get(t, 0) - truoc.get(t, 0) for t in set(truoc) | set(sau) if sau.get(t, 0) != truoc.get(t, 0)}
        self.assertEqual(thuc, {k.replace("__", "."): v for k, v in mong.items() if v})
        self.assertTrue(set(thuc) <= set(GHI_DC), thuc)

    def luu_moi(self, truoc, n_nguon_moi: int, n_tp: int):
        self.doi_dc(truoc, kho__mua_nguon_kinh_te=n_nguon_moi, kho__mua_nguon_kinh_te_phien_ban=n_nguon_moi, kho__mua_nguon_phan=n_nguon_moi,
                    kho__mua_doi_chieu_can_cu=1, kho__mua_doi_chieu_can_cu_phien_ban=1, kho__mua_doi_chieu_can_cu_thanh_phan=n_tp,
                    kho__mua_doi_chieu_can_cu_nhat_ky=1, kho__bien_nhan_thao_tac=1)

    def nt_xac_nhan_03a(self, h) -> dict:
        """03A thật: lưu NA đủ + xác nhận (nguồn NT có kt_xac_nhan_id)."""
        x = self.xem(h["cho"])
        self.kt.luu(self.KT1, self.than_luu(x, self.K(f"{h['cho'][:8]}-kt-luu"), **self.du_day("KHONG_AP_DUNG", ly_do=P.LY_DO_NA)))
        x = self.xem(h["cho"])
        self.kt.xac_nhan(self.KT1, self.than_xn(x, self.K(f"{h['cho'][:8]}-kt-xn")))
        return self.xem(h["cho"])

    @staticmethod
    def ref_nt(x03a) -> dict:
        return AD.ref_tu_kt(x03a)

    def ref_hd(self, part=None, login=None) -> dict:
        """Ref hóa đơn với source_version_id = phiên bản hiện hành do MÁY CHỦ trả (xem trước bằng ID tạm, xem không so CAS)."""
        tam = {"kind": "HOA_DON", "occurrence_id": self.hd_id, "source_version_id": self.hd_id, "part_id": part}
        x = self.dc.xem_doi_chieu(login or self.KT1, {"nguon": [tam]})
        it = next(i for i in x["nguon"] if i["kind"] == "HOA_DON")
        return {**tam, "source_version_id": it["current"]}, it

    def than(self, refs, x, khoa, *, goc=None, rev=0, phan=None, tep=(), ly_do="KT đối chiếu căn cứ nguồn") -> dict:
        return {"doi_chieu_id": goc, "thanh_phan": [{"nguon": r, "phan": (phan or {}).get(r["kind"], "TOAN_PHAN"), "ty_le_khai": None} for r in refs],
                "can_cu_tep": list(tep), "expected_graph": x["doi_chieu"]["graph_sha256"], "expected_revision": rev, "ly_do": ly_do, "khoa": khoa}

    def xem_dc(self, refs, login=None):
        return self.dc.xem_doi_chieu(login or self.KT1, {"nguon": refs})

    def can_hoa_don(self):
        if not self.hd_id:
            self.skipTest(f"NOT_VERIFIED: thiếu {ENV_HOA_DON} (hóa đơn M2 có sẵn cùng PN DEMO, KT1 có M2) — phụ thuộc clone của Root")

    # ------------------------------------------------------------------ C01 NT-only dương (không M2)
    def test_c01_nt_only_luu_phat_lai(self):
        h = self.ho_so_seal("DC1")
        x03 = self.xem(h["cho"])
        r = self.ref_nt(x03)
        x = self.xem_dc([r])
        self.assertEqual(x["kt"]["thieu"], ["NT_CHUA_KT_XAC_NHAN", "THIEU_HOA_DON"])
        nt = x["nguon"][0]
        self.assertEqual((nt["hien_hanh"], nt["toan_ven"], nt["current"], nt["hop_dong_id"]),
                         (True, True, x03["context"]["phong_bi_id"], x03["context"]["hop_dong_id"]))
        self.assertIsNotNone(nt["doi_tac_id"], "đối tác resolve từ master.hop_dong — không từ body")
        truoc = self.dem_tat_ca()
        b = self.than([r], x, self.K("c01-luu"))
        a = self.dc.luu_doi_chieu(self.KT1, b)
        self.assertEqual((a["lap_lai"], a["doi_chieu"]["revision"], a["doi_chieu"]["trang_thai"]), (False, 1, SG.TT_NHAP))
        self.assertEqual(a["kt"]["thieu"], ["NT_CHUA_KT_XAC_NHAN", "THIEU_HOA_DON"])
        self.assertEqual(a["ghi_nhan"], GN.GHI_NHAN)
        self.luu_moi(truoc, 1, 1)
        bn = self.q("SELECT to_jsonb(b) FROM kho.bien_nhan_thao_tac b WHERE b.id = %s", (a["receipt_id"],))
        self.assertEqual((bn["module"], bn["operation"], bn["actor"]), ("M4", SG.OP_LUU, self.KT1))
        pb = self.q("SELECT to_jsonb(v) FROM kho.mua_doi_chieu_can_cu_phien_ban v WHERE v.id = %s", (a["doi_chieu"]["phien_ban_id"],))
        self.assertEqual((str(pb["hop_dong_id"]), pb["financial_owner"], pb["ghi_nhan"]),
                         (x03["context"]["hop_dong_id"], None, SG.GHI_NHAN_TT))
        # phát lại đúng khóa đúng nội dung → biên nhận cũ, 0 delta
        truoc = self.dem_tat_ca()
        a2 = self.dc.luu_doi_chieu(self.KT1, b)
        self.assertEqual((a2["lap_lai"], a2["receipt_id"], a2["doi_chieu"]["phien_ban_id"]), (True, a["receipt_id"], a["doi_chieu"]["phien_ban_id"]))
        self.doi_dc(truoc)
        # cùng khóa khác nội dung → 409; khóa mới cùng tập → DC_DA_CO_GOC
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, {**b, "ly_do": "khác"}), "DC_IDEMPOTENCY_KHAC")
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, {**b, "khoa": self.K("c01-trung")}), "DC_DA_CO_GOC")
        # xác nhận khi còn thiếu → chặn, 0 delta
        xn = {"doi_chieu_id": a["doi_chieu"]["doi_chieu_id"], "phien_ban_id": a["doi_chieu"]["phien_ban_id"], "expected_revision": 1,
              "expected_graph": a["doi_chieu"]["graph_sha256"], "khoa": self.K("c01-xn")}
        self.assertEqual(self.loi(self.dc.xac_nhan_doi_chieu, self.KT1, xn), "DC_CHO_BO_SUNG")
        self.doi_dc(truoc)
        self.s.update(h1=h, a1=a, r1=r)

    # ------------------------------------------------------------------ C02 03A xác nhận → đồ thị đổi → CAN_KIEM_LAI dẫn xuất
    def test_c02_nguon_doi_can_kiem_lai(self):
        self.can("h1", "a1")
        h, a = self.s["h1"], self.s["a1"]
        self.nt_xac_nhan_03a(h)
        ls = self.dc.lich_su(self.KT1, a["doi_chieu"]["doi_chieu_id"])
        self.assertEqual(ls["doi_chieu"]["phien_ban"][-1]["trang_thai"], SG.TT_CAN_KIEM_LAI)
        self.assertEqual(ls["kt"]["thieu_hien_tai"], ["THIEU_HOA_DON"])
        truoc = self.dem_tat_ca()
        xn = {"doi_chieu_id": a["doi_chieu"]["doi_chieu_id"], "phien_ban_id": a["doi_chieu"]["phien_ban_id"], "expected_revision": 1,
              "expected_graph": a["doi_chieu"]["graph_sha256"], "khoa": self.K("c02-xn-cu")}
        self.assertEqual(self.loi(self.dc.xac_nhan_doi_chieu, self.KT1, xn), "DC_CAN_KIEM_LAI")
        self.doi_dc(truoc)
        # revision mới của CÙNG gốc với ref ghim phiên bản hiện hành → NHAP rev 2 (nguồn NT có phiên bản identity mới)
        x = self.xem_dc([self.s["r1"]])
        b = self.than([self.s["r1"]], x, self.K("c02-luu2"), goc=a["doi_chieu"]["doi_chieu_id"], rev=1)
        a2 = self.dc.luu_doi_chieu(self.KT1, b)
        self.assertEqual((a2["doi_chieu"]["revision"], a2["kt"]["thieu"]), (2, ["THIEU_HOA_DON"]))
        self.doi_dc(truoc, kho__mua_nguon_kinh_te_phien_ban=1, kho__mua_doi_chieu_can_cu_phien_ban=1, kho__mua_doi_chieu_can_cu_thanh_phan=1,
                    kho__mua_doi_chieu_can_cu_nhat_ky=1, kho__bien_nhan_thao_tac=1)
        self.s.update(a1b=a2)

    # ------------------------------------------------------------------ C03 cross-source dương (cổng hóa đơn)
    def test_c03_cross_source_kt_xac_nhan(self):
        self.can("h1", "a1b")
        self.can_hoa_don()
        try:
            rh, it = self.ref_hd()
        except Exception as exc:  # noqa: BLE001
            self.skipTest(f"NOT_VERIFIED: KT1 không đọc được hóa đơn {ENV_HOA_DON} ({self.ma(exc)}) — cần module M2 cho KT1 trên PN hóa đơn")
        rn = self.s["r1"]
        x = self.xem_dc([rn, rh])
        nt = next(i for i in x["nguon"] if i["kind"] == "NT")
        if it["phap_nhan_id"] != nt["phap_nhan_id"]:
            self.skipTest("NOT_VERIFIED: hóa đơn khác PN của hồ sơ DEMO — phụ thuộc clone của Root")
        if x["kt"]["thieu"] == ["BEN_BAN_KHAC"]:
            # âm thật: không khớp tên/ngày/tiền — MST master HĐ ≠ mst_ban → lưu được NHAP nhưng không xác nhận
            truoc = self.dem_tat_ca()
            a = self.dc.luu_doi_chieu(self.KT1, self.than([rn, rh], x, self.K("c03-khac")))
            self.assertEqual(a["kt"]["thieu"], ["BEN_BAN_KHAC"])
            xn = {"doi_chieu_id": a["doi_chieu"]["doi_chieu_id"], "phien_ban_id": a["doi_chieu"]["phien_ban_id"], "expected_revision": 1,
                  "expected_graph": a["doi_chieu"]["graph_sha256"], "khoa": self.K("c03-khac-xn")}
            self.assertEqual(self.loi(self.dc.xac_nhan_doi_chieu, self.KT1, xn), "DC_CHO_BO_SUNG")
            self.skipTest("NOT_VERIFIED (dương): mst_ban hóa đơn ≠ MST đối tác HĐ DEMO — cần hóa đơn M2 có sẵn của đúng bên bán (phụ thuộc Root)")
        self.assertEqual(x["kt"]["thieu"], [], "căn cứ đủ: NT hiện hành + KT 03A đã xác nhận + cùng PN + MST master = mst_ban")
        self.assertEqual(it["money_basis_state"], "UNPROVEN_NO_MINOR")
        truoc = self.dem_tat_ca()
        b = self.than([rh, rn], x, self.K("c03-luu"))  # thứ tự body: hóa đơn trước — máy chủ sắp lại
        a = self.dc.luu_doi_chieu(self.KT1, b)
        self.assertEqual((a["doi_chieu"]["revision"], a["kt"]["thieu"], a["doi_chieu"]["trang_thai"]), (1, [], SG.TT_NHAP))
        self.assertTrue(a["receipt_id"])
        sau = self.dem_tat_ca()  # identity NT đã có (C01/C02); identity hóa đơn có thể mới — chỉ kiểm gốc/thành phần + phạm vi bảng
        self.assertEqual(sau["kho.mua_doi_chieu_can_cu"] - truoc["kho.mua_doi_chieu_can_cu"], 1)
        self.assertEqual(sau["kho.mua_doi_chieu_can_cu_thanh_phan"] - truoc["kho.mua_doi_chieu_can_cu_thanh_phan"], 2)
        self.assertTrue({t for t in sau if sau[t] != truoc.get(t)} <= set(GHI_DC))
        self.assertEqual(self.q("SELECT module FROM kho.bien_nhan_thao_tac WHERE id = %s", (a["receipt_id"],)), "M4")
        # xác nhận: sao y nháp, KT_XAC_NHAN_CAN_CU, 0 tài chính
        truoc = self.dem_tat_ca()
        xn = {"doi_chieu_id": a["doi_chieu"]["doi_chieu_id"], "phien_ban_id": a["doi_chieu"]["phien_ban_id"], "expected_revision": 1,
              "expected_graph": a["doi_chieu"]["graph_sha256"], "khoa": self.K("c03-xn")}
        c = self.dc.xac_nhan_doi_chieu(self.KT1, xn)
        self.assertEqual((c["doi_chieu"]["trang_thai"], c["doi_chieu"]["revision"], c["doi_chieu"]["nhap_id"], c["ghi_nhan"]),
                         (SG.TT_XAC_NHAN, 2, a["doi_chieu"]["phien_ban_id"], GN.GHI_NHAN))
        self.doi_dc(truoc, kho__mua_doi_chieu_can_cu_phien_ban=1, kho__mua_doi_chieu_can_cu_thanh_phan=2, kho__mua_doi_chieu_can_cu_nhat_ky=1,
                    kho__bien_nhan_thao_tac=1)
        # đồng thời/khóa mới sau xác nhận → cùng xác nhận (trung_xac_nhan), không revision mới
        truoc = self.dem_tat_ca()
        c2 = self.dc.xac_nhan_doi_chieu(self.KT1, {**xn, "khoa": self.K("c03-xn2")})
        self.assertEqual((c2["doi_chieu"]["phien_ban_id"], c2["doi_chieu"]["trung_xac_nhan"]), (c["doi_chieu"]["phien_ban_id"], True))
        self.doi_dc(truoc, kho__bien_nhan_thao_tac=1)
        ls = self.dc.lich_su(self.KT1, a["doi_chieu"]["doi_chieu_id"])
        self.assertEqual([p["trang_thai"] for p in ls["doi_chieu"]["phien_ban"]], [SG.TT_NHAP, SG.TT_XAC_NHAN])
        # nhiều-nhiều: cùng hóa đơn với NT khác (hồ sơ mới cùng HĐ DEMO) là đối chiếu khác; không cần hóa đơn đã nối NT từ trước
        h2 = self.ho_so_seal("DC3")
        r2 = self.ref_nt(self.xem(h2["cho"]))
        x2 = self.xem_dc([r2, rh])
        a3 = self.dc.luu_doi_chieu(self.KT1, self.than([r2, rh], x2, self.K("c03-nn")))
        self.assertNotEqual(a3["doi_chieu"]["doi_chieu_id"], a["doi_chieu"]["doi_chieu_id"])
        self.assertIn("NT_CHUA_KT_XAC_NHAN", a3["kt"]["thieu"])
        self.s.update(rh=rh, a3x=c)

    # ------------------------------------------------------------------ C04 stale / CAS
    def test_c04_stale_cas(self):
        self.can("h1", "a1b", "r1")
        a = self.s["a1b"]
        x = self.xem_dc([self.s["r1"]])
        goc = a["doi_chieu"]["doi_chieu_id"]
        truoc = self.dem_tat_ca()
        cu = {**self.s["r1"], "source_version_id": str(uuid.uuid4())}
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, self.than([cu], x, self.K("c04-nguon"), goc=goc, rev=2)), "DC_NGUON_CU")
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, {**self.than([self.s["r1"]], x, self.K("c04-graph"), goc=goc, rev=2),
                                                                     "expected_graph": "0" * 64}), "DC_DO_THI_DOI")
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, self.than([self.s["r1"]], x, self.K("c04-rev"), goc=goc, rev=1)), "DC_REVISION_CU")
        h3 = self.ho_so_seal("DC4")
        r3 = self.ref_nt(self.xem(h3["cho"]))
        x3 = self.xem_dc([self.s["r1"], r3])
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, self.than([self.s["r1"], r3], x3, self.K("c04-tap"), goc=goc, rev=2)),
                         "DC_THAM_SO_SAI")
        self.doi_dc(truoc)
        self.s.update(h3=h3, r3=r3)

    # ------------------------------------------------------------------ C05 từ chối quyền
    def test_c05_tu_choi(self):
        self.can("a1b", "r1")
        a = self.s["a1b"]
        truoc = self.dem_tat_ca()
        self.assertIn(self.loi(self.xem_dc, [self.s["r1"]], self.KT_KHAC), ("M4_KT_PHAM_VI", "M4_KT_KHONG_THAY"))
        x = self.xem_dc([self.s["r1"]])
        self.assertIn(self.loi(self.dc.luu_doi_chieu, self.KT_KHAC, self.than([self.s["r1"]], x, self.K("c05-khac"), goc=a["doi_chieu"]["doi_chieu_id"],
                                                                                rev=2)), ("M4_KT_PHAM_VI", "M4_KT_KHONG_THAY"))
        self.assertIn(self.loi(self.dc.lich_su, self.KT_KHAC, a["doi_chieu"]["doi_chieu_id"]), ("DC_KHONG_THAY",))
        xn = {"doi_chieu_id": a["doi_chieu"]["doi_chieu_id"], "phien_ban_id": a["doi_chieu"]["phien_ban_id"], "expected_revision": 2,
              "expected_graph": a["doi_chieu"]["graph_sha256"], "khoa": self.K("c05-xn")}
        self.assertEqual(self.loi(self.dc.xac_nhan_doi_chieu, self.KT_KHAC, xn), "DC_KHONG_THAY")
        self.doi_dc(truoc)
        if not self.hd_id:
            return
        for env in (ENV_CFO, ENV_XEM):
            login = os.environ.get(env)
            if not login:
                continue
            try:
                rh, _ = self.ref_hd(login=login)
            except Exception as exc:  # noqa: BLE001
                self.fail(f"{env}: M2_READ hiện hành phải xem được hóa đơn ({self.ma(exc)})")
            xh = self.xem_dc([rh], login)
            self.assertFalse(xh["kt"]["duoc_ghi"])
            self.assertEqual(self.loi(self.dc.luu_doi_chieu, login, self.than([rh], xh, self.K(f"c05-{env[-3:]}"))), "DC_PHAM_VI")
            self.doi_dc(truoc)

    # ------------------------------------------------------------------ C06 bỏ qua DB
    def app_loi(self, sql, params=()):
        def chay():
            with self.svc._tx(self.svc.danh_tinh(self.KT1)):
                self.svc._mot(sql, params)
        return self.loi(chay)

    def chu_loi(self, *cau):
        def chay():
            d = self.svc.danh_tinh(self.KT1)
            with self.svc._tx_review(d) as c:
                for sql, p in cau:
                    self.svc._r1(c, sql, p)
        return self.loi(chay)

    def test_c06_bo_qua_db(self):
        self.can("a1b", "r1", "h1")
        a = self.s["a1b"]
        truoc = self.dem_tat_ca()
        pn = self.q("SELECT phap_nhan_id FROM kho.mua_doi_chieu_can_cu WHERE id = %s", (a["doi_chieu"]["doi_chieu_id"],))
        for sql, p in (("INSERT INTO kho.mua_doi_chieu_can_cu (phap_nhan_id, khoa_goc_sha256, tao_boi, tao_boi_id) VALUES (%s, %s, 'x', %s)",
                        (pn, "1" * 64, str(uuid.uuid4()))),
                       ("UPDATE kho.mua_doi_chieu_can_cu_phien_ban SET ly_do = 'x'", ()),
                       ("DELETE FROM kho.mua_nguon_kinh_te", ()),
                       ("SELECT kho.dc_luu('x', '{}'::jsonb)", ()),
                       ("SELECT kho._dc_nt_ghi(%s::uuid)", (self.s["h1"]["cho"],)),
                       ("SELECT kho._dc_do_thi('[]'::jsonb)", ()),
                       ("INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor) "
                        "VALUES (%s, 'M4', 'DC_CAN_CU_LUU', 'gia', %s, '{}'::jsonb, %s)", (pn, "2" * 64, self.KT1)),
                       ("INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor) "
                        "VALUES (%s, 'M2', 'DC_CAN_CU_XAC_NHAN', 'gia2', %s, '{}'::jsonb, %s)", (pn, "3" * 64, self.KT1))):
            self.assertIsNotNone(self.app_loi(sql, p), sql)
        self.doi_dc(truoc)
        # owner: lệnh không ghim producer / GUC giả → không hiện hành
        x = self.xem_dc([self.s["r1"]])
        b = self.than([self.s["r1"]], x, self.K("c06-khong-ghim"), goc=a["doi_chieu"]["doi_chieu_id"], rev=2)
        y = GN.yeu_cau_luu(b)
        y.pop("khoa")
        yc = json.dumps(y, ensure_ascii=False)
        self.assertEqual(self.chu_loi(("SELECT kho.dc_luu(%s, %s::jsonb) AS r", (b["khoa"], yc))), "DC_CAN_KIEM_LAI")
        gia = json.dumps({"pid": "0", "txid": "0", "actor": "x", "cho": {self.s["h1"]["cho"]: {"hien_hanh": True, "toan_ven": True}}})
        self.assertEqual(self.chu_loi(("SELECT set_config(%s, %s, true) AS r", (SG.GUC_NT, gia)),
                                      ("SELECT kho.dc_luu(%s, %s::jsonb) AS r", (b["khoa"] + "g", yc))), "DC_CAN_KIEM_LAI")
        # thành phần gắn thêm vào phiên bản cũ / sửa lịch sử bởi owner → chặn
        self.assertEqual(self.chu_loi(("UPDATE kho.mua_doi_chieu_can_cu_phien_ban SET ly_do = 'x' WHERE id = %s RETURNING id AS r",
                                       (a["doi_chieu"]["phien_ban_id"],))), "DC_BAT_BIEN")
        self.doi_dc(truoc)

    # ------------------------------------------------------------------ C07 đồng thời
    def test_c07_dong_thoi_mot_goc(self):
        self.can("r3")
        r3 = self.s["r3"]
        x = self.xem_dc([r3])
        truoc = self.dem_tat_ca()
        kq, loi = self.song_song([lambda i=i: self.dc.luu_doi_chieu(self.KT1, self.than([r3], x, self.K(f"c07-{i}"))) for i in range(3)])
        self.assertEqual(len(kq), 1, (kq, loi))
        self.assertEqual(sorted(loi), ["DC_DA_CO_GOC", "DC_DA_CO_GOC"])
        self.luu_moi(truoc, 1, 1)


if __name__ == "__main__":
    unittest.main()
