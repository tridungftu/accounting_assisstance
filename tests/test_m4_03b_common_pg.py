"""M4-03B-01 (+FIX01) — kiểm PostgreSQL THẬT identity nguồn dùng chung + đối chiếu căn cứ NT ↔ hóa đơn do KT xác nhận. WRITTEN_NOT_RUN.

Ba cổng (thiếu cổng nào → SkipTest NOT_VERIFIED, KHÔNG phải PASS):
1. Cổng 03A (tests/test_m4_03a_pg.py: KHO_M4_03A_* + kiem_clone/registry/quyền) — mượn thuộc tính lớp gốc như test_m4_03a_full_basis_pg
   (không import lớp TestCase → test gốc không chạy lại); DSN chủ bảng phải là ĐÚNG chủ m4.kt_xac_nhan theo session_user.
2. Cổng 03B: env KHO_M4_03B_DA_AP_DUNG=1 (từ M4-4/7 `M4_03B_COMMON_SQL` là M0029 trong registry: clone migrate bằng registry hiện hành; cờ env vẫn là xác nhận của Root) + kiểm CHỈ ĐỌC:
   mọi bảng/hàm mới tồn tại và thân kho.dc_luu / kho.dc_xac_nhan / kho._dc_do_thi / ... trên clone BẰNG BYTE hằng trong file nguồn. Sai → LoiThietLap.
3. Cổng hóa đơn (chỉ ca cross-source): KHO_M4_03B_HOA_DON_ID = hóa đơn M2 CÓ SẴN trên clone, cùng PN với hồ sơ DEMO, KT1 có module M2 trên PN đó.
   Dương thật cần thêm mst_ban = MST master của đối tác HĐ DEMO (máy chủ resolve, không seed). Lệch MST → ca dương SKIP NOT_VERIFIED kèm
   phụ thuộc chính xác, ca âm BEN_BAN_KHAC vẫn chạy. Tùy chọn: KHO_M4_03B_CFO / KHO_M4_03B_XEM (login M2_READ không phải KT) cho ca từ chối ghi;
   KHO_M4_03B_DONG_ID = dòng logic CÓ SẴN của chính hóa đơn đó cho ca đổi phần toàn bộ ↔ dòng.

Producer THẬT: hồ sơ NT seal + 03A lưu/xác nhận qua service 03A; không INSERT giả nguồn/duyệt/hóa đơn, không monkeypatch SQL/service.
FIX01: đổi tập nguồn/phần = revision mới (lý do + expected_revision + CAS) của CÙNG gốc; alias tập → gốc; namespace biên nhận = module gốc lúc tạo.
C01 NT-only (không cần M2): xem → lưu NHAP đúng delta (gốc + alias tập) → phát lại / khác nội dung / gốc trùng → xác nhận bị chặn (thiếu) delta 0.
C02 03A xác nhận làm đồ thị đổi: revision cũ dẫn xuất CAN_KIEM_LAI, xác nhận cũ bị chặn; lưu revision mới cùng tập (alias 0).
C03 cross-source (cổng 3): gốc NT-only của C01 → CÙNG gốc thêm hóa đơn (body hóa đơn trước) → xác nhận → KT_XAC_NHAN_CAN_CU; trung_xac_nhan;
    lịch sử/thành phần/biên nhận cũ nguyên; nhiều đợt trong CÙNG gốc OK, hóa đơn ở gốc khác bị từ chối; 0 hàng tài chính/AP.
C04 đổi tập cùng gốc + CAS (setup seal TRƯỚC snapshot): stale nguồn/đồ thị/revision → 0 delta; thêm NT (thứ tự ngược) → revision cùng gốc;
    xem thứ tự ngược cùng identity; bớt NT (ABA về tập cũ, alias 0); phát lại khóa cũ sau đổi thành viên = cùng ID; khóa cũ khác body 409;
    khóa mới body cũ/ABA không trùng.
C05 từ chối: KT_KHAC (ngoài dự án) xem/lưu/lịch sử/xác nhận; CFO/XEM ghi hóa đơn (cổng 3); delta 0.
C06 bỏ qua DB: app DML/EXECUTE lệnh/helper/alias; app giả biên nhận M4/DC_*; owner gọi lệnh không ghim / GUC giả → DC_CAN_KIEM_LAI;
    owner ghi alias ngoài lệnh → DC_BAT_BIEN; delta 0.
C07 đồng thời (hai kết nối): hai lệnh tạo cùng tập khác khóa → đúng một gốc, còn lại DC_DA_CO_GOC; sửa gốc khác sang tập đó → 409.
C08 hóa đơn trước (cổng 3): gốc invoice-only (namespace M2) → thêm NT thuộc tập gốc khác 409 → thêm NT mới cùng gốc (vẫn M2) → bớt hóa đơn →
    ABA; phát lại/409/khóa mới; tùy chọn toàn bộ ↔ dòng logic.
C09 đồng thời đổi tập (hai kết nối): cùng expected_revision → đúng một revision commit, bên kia DC_REVISION_CU; thứ tự thắng ngược bằng CAS đã commit.
C10 xác nhận vs revision (cổng 3 dương): đua hai kết nối + cả hai thứ tự thắng bằng CAS đã commit; đúng +1 revision mỗi vòng.
Nghi vấn GUC exact-tuple KHÔNG được sửa/kiểm ở đây (cần bằng chứng native riêng).
"""

from __future__ import annotations

import json
import os
import unittest
import uuid

from tests import test_m4_03a_pg as P
from tests.test_m4_02c_pg import _q1

from kho_tri_thuc.k2 import ghi_nhan_chung as GN
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import sql_ghi_nhan_chung as SG
from kho_tri_thuc.k2 import sql_ghi_nhan_so_tien as ST
from kho_tri_thuc.m4 import ghi_nhan_nghiem_thu as AD

_G = vars(P.M4KeToanPG)
ENV_DA_AP_DUNG = "KHO_M4_03B_DA_AP_DUNG"
ENV_HOA_DON = "KHO_M4_03B_HOA_DON_ID"
ENV_DONG = "KHO_M4_03B_DONG_ID"
ENV_CFO, ENV_XEM = "KHO_M4_03B_CFO", "KHO_M4_03B_XEM"
CO_ENV_03B = P.CO_ENV and os.environ.get(ENV_DA_AP_DUNG) == "1"
LY_DO_SKIP_03B = ("NOT_VERIFIED: chưa có clone 03A + M4_03B_COMMON_SQL (M0029) do Root migrate (KHO_M4_03A_* + KHO_M4_03B_DA_AP_DUNG=1) — "
                  "test M4-03B PG không chạy, KHÔNG tính đạt")
NOI = "\n".join((*SG.M4_03B_COMMON_SQL, *ST.M4_03B_SO_TIEN_SQL))
BANG_DC = tuple(f"kho.{t}" for t in SG.BANG)
# bảng được phép đổi bởi lệnh đối chiếu (mọi bảng khác — tài chính/M24/AP/Request/M2 — phải 0 delta)
GHI_DC = (*BANG_DC, "kho.bien_nhan_thao_tac")


def _than_ham(ten: str) -> str:
    i = NOI.rindex(f"CREATE OR REPLACE FUNCTION {ten}(")  # định nghĩa hiện hành sau M0033; M0029 vẫn nguyên byte
    a = NOI.index("$$", i)
    return NOI[a + 2:NOI.index("$$", a + 2)]


@unittest.skipUnless(CO_ENV_03B, LY_DO_SKIP_03B)
class M4DoiChieuCanCuPG(unittest.TestCase):
    """Chạy theo thứ tự c01 → c10 trên MỘT clone; trạng thái qua cls.s."""

    @classmethod
    def setUpClass(cls):
        _G["setUpClass"].__func__(cls)
        if _q1(cls.admin, "SELECT m4._kt_phien_chu()") is not True:
            raise P.LoiThietLap("SETUP_FAILURE: DSN chủ bảng không phải ĐÚNG chủ m4.kt_xac_nhan theo session_user — không ghim được chứng thực")
        for t in BANG_DC:
            if _q1(cls.admin, "SELECT to_regclass(%s) IS NOT NULL", (t,)) is not True:
                raise P.LoiThietLap(f"SETUP_FAILURE: clone chưa có {t} — M4_03B_COMMON_SQL (M0029) chưa được migrate vào clone")
        for h in (*SG.HAM_LENH, *SG.HAM_NOI_BO, *SG.HAM_DOC, *SG.HAM_TRIGGER):
            if _q1(cls.admin, "SELECT to_regprocedure(%s) IS NOT NULL", (h,)) is not True:
                raise P.LoiThietLap(f"SETUP_FAILURE: clone thiếu hàm {h}")
        for h in ("kho._dc_so_tien_hop_le(text,text)", "kho._dc_kiem_tien_tp(jsonb)", "kho._dc_dot_goi_y(uuid)", "kho._dc_goi_y_hoa_don(uuid)",
                  "kho._dc_hd_da_gan(uuid,uuid)", "kho._dc_kiem_hd_da_gan(jsonb,uuid)"):
            if _q1(cls.admin, "SELECT to_regprocedure(%s) IS NOT NULL", (h,)) is not True:
                raise P.LoiThietLap(f"SETUP_FAILURE: clone thiếu M0033: {h}")
        for h in ("kho.dc_luu", "kho.dc_xac_nhan", "kho._dc_do_thi", "kho._dc_quyen", "kho._dc_phien_ban_hoan_tat", "kho._dc_hop",
                  "kho._dc_tap_kiem", "kho.bien_nhan_dc_chi_chu", "kho._dc_thieu", "kho._dc_goi_y_hoa_don", "kho._dc_kiem_tien_tp",
                  "kho._dc_hd_da_gan", "kho._dc_kiem_hd_da_gan"):
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
        """Tạo gốc mới: gốc + revision 1 + alias tập tạo + nhật ký + biên nhận; identity nguồn chỉ cho nguồn chưa có."""
        self.doi_dc(truoc, kho__mua_nguon_kinh_te=n_nguon_moi, kho__mua_nguon_kinh_te_phien_ban=n_nguon_moi, kho__mua_nguon_phan=n_nguon_moi,
                    kho__mua_doi_chieu_can_cu=1, kho__mua_doi_chieu_can_cu_phien_ban=1, kho__mua_doi_chieu_can_cu_thanh_phan=n_tp,
                    kho__mua_doi_chieu_can_cu_nhat_ky=1, kho__mua_doi_chieu_can_cu_tap=1, kho__bien_nhan_thao_tac=1)

    def luu_rev(self, truoc, n_tp: int, *, tap: int, nguon: int = 0, nguon_pb: int | None = None, phan: int | None = None):
        """Revision mới của gốc CÓ SẴN: KHÔNG gốc mới; alias chỉ khi tập chưa từng thuộc gốc (tap=1)."""
        self.doi_dc(truoc, kho__mua_nguon_kinh_te=nguon, kho__mua_nguon_kinh_te_phien_ban=nguon if nguon_pb is None else nguon_pb,
                    kho__mua_nguon_phan=nguon if phan is None else phan, kho__mua_doi_chieu_can_cu_phien_ban=1,
                    kho__mua_doi_chieu_can_cu_thanh_phan=n_tp, kho__mua_doi_chieu_can_cu_nhat_ky=1, kho__mua_doi_chieu_can_cu_tap=tap,
                    kho__bien_nhan_thao_tac=1)

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

    def xn_cua(self, a, khoa) -> dict:
        d = a["doi_chieu"]
        return {"doi_chieu_id": d["doi_chieu_id"], "phien_ban_id": d["phien_ban_id"], "expected_revision": d["revision"],
                "expected_graph": d["graph_sha256"], "khoa": khoa}

    def cuoi(self, goc) -> dict:
        return self.dc.lich_su(self.KT1, goc)["doi_chieu"]["phien_ban"][-1]

    def tap_hien(self, goc) -> list:
        return [t["nguon"] for t in self.cuoi(goc)["noi_dung"]["thanh_phan"]]

    def anh_goc(self, goc) -> dict:
        """Ảnh CSDL của một gốc: gốc + mọi revision/thành phần/alias/biên nhận (để chứng minh lịch sử cũ nguyên vẹn)."""
        return self.q("""SELECT jsonb_build_object(
                'goc', (SELECT to_jsonb(g) FROM kho.mua_doi_chieu_can_cu g WHERE g.id = %s::uuid),
                'pb', (SELECT coalesce(jsonb_agg(to_jsonb(v) ORDER BY v.revision), '[]') FROM kho.mua_doi_chieu_can_cu_phien_ban v WHERE v.doi_chieu_id = %s::uuid),
                'tp', (SELECT coalesce(jsonb_agg(to_jsonb(m) ORDER BY m.id), '[]') FROM kho.mua_doi_chieu_can_cu_thanh_phan m WHERE m.doi_chieu_id = %s::uuid),
                'tap', (SELECT coalesce(jsonb_agg(to_jsonb(a) ORDER BY a.id), '[]') FROM kho.mua_doi_chieu_can_cu_tap a WHERE a.doi_chieu_id = %s::uuid),
                'bn', (SELECT coalesce(jsonb_agg(to_jsonb(b) ORDER BY b.id), '[]') FROM kho.bien_nhan_thao_tac b
                       WHERE b.result_json->>'doi_chieu_id' = %s::text))""", (goc,) * 5)

    def giu_lich_su(self, cu: dict, moi: dict):
        self.assertEqual(moi["goc"], cu["goc"], "gốc (khoa_goc_sha256 tạo, module_bien_nhan) bất biến")
        for k in ("pb", "tp", "tap", "bn"):
            for x in cu[k]:
                self.assertIn(x, moi[k], f"{k}: hàng lịch sử cũ phải còn nguyên byte")
        self.assertEqual([p["revision"] for p in moi["pb"]], list(range(1, len(moi["pb"]) + 1)))

    def module_goc(self, goc) -> tuple:
        return (self.q("SELECT module_bien_nhan FROM kho.mua_doi_chieu_can_cu WHERE id = %s", (goc,)),
                self.q("SELECT coalesce(array_agg(DISTINCT module ORDER BY module), '{}') FROM kho.bien_nhan_thao_tac WHERE result_json->>'doi_chieu_id' = %s",
                       (str(goc),)))

    def co_nguon(self, occ) -> int:
        return self.q("SELECT count(*) FROM kho.mua_nguon_kinh_te WHERE occurrence_id = %s", (occ,))

    def dich_vu_rieng(self, n=2) -> list:
        """Mỗi dịch vụ một cặp kết nối riêng (app + chủ bảng) — đồng thời thật, không chia kết nối."""
        return [AD.dich_vu(self._svc_moi()) for _ in range(n)]

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
        self.assertIsNone(x["doi_chieu"]["goc_cua_tap"])
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
        self.assertEqual(a["doi_chieu"]["tap_sha256"], x["doi_chieu"]["khoa_goc_sha256"])
        self.luu_moi(truoc, 1, 1)
        goc = a["doi_chieu"]["doi_chieu_id"]
        bn = self.q("SELECT to_jsonb(b) FROM kho.bien_nhan_thao_tac b WHERE b.id = %s", (a["receipt_id"],))
        self.assertEqual((bn["module"], bn["operation"], bn["actor"]), ("M4", SG.OP_LUU, self.KT1))
        self.assertEqual(self.module_goc(goc), ("M4", ["M4"]))
        self.assertEqual(self.q("SELECT khoa_goc_sha256 FROM kho.mua_doi_chieu_can_cu WHERE id = %s", (goc,)), a["doi_chieu"]["tap_sha256"])
        pb = self.q("SELECT to_jsonb(v) FROM kho.mua_doi_chieu_can_cu_phien_ban v WHERE v.id = %s", (a["doi_chieu"]["phien_ban_id"],))
        self.assertEqual((str(pb["hop_dong_id"]), pb["financial_owner"], pb["ghi_nhan"]),
                         (x03["context"]["hop_dong_id"], None, SG.GHI_NHAN_TT))
        # phát lại đúng khóa đúng nội dung → biên nhận cũ, 0 delta
        truoc = self.dem_tat_ca()
        a2 = self.dc.luu_doi_chieu(self.KT1, b)
        self.assertEqual((a2["lap_lai"], a2["receipt_id"], a2["doi_chieu"]["phien_ban_id"]), (True, a["receipt_id"], a["doi_chieu"]["phien_ban_id"]))
        self.doi_dc(truoc)
        # cùng khóa khác nội dung → 409; khóa mới cùng tập → DC_DA_CO_GOC (alias giải về gốc đã có)
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, {**b, "ly_do": "khác"}), "DC_IDEMPOTENCY_KHAC")
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, {**b, "khoa": self.K("c01-trung")}), "DC_DA_CO_GOC")
        self.assertEqual(self.xem_dc([r])["doi_chieu"]["goc_cua_tap"], goc)
        # xác nhận khi còn thiếu → chặn, 0 delta
        self.assertEqual(self.loi(self.dc.xac_nhan_doi_chieu, self.KT1, self.xn_cua(a, self.K("c01-xn"))), "DC_CHO_BO_SUNG")
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
        self.assertEqual(self.loi(self.dc.xac_nhan_doi_chieu, self.KT1, self.xn_cua(a, self.K("c02-xn-cu"))), "DC_CAN_KIEM_LAI")
        self.doi_dc(truoc)
        # revision mới của CÙNG gốc, cùng tập (alias 0) với ref ghim phiên bản hiện hành → NHAP rev 2 (nguồn NT có phiên bản identity mới)
        x = self.xem_dc([self.s["r1"]])
        b = self.than([self.s["r1"]], x, self.K("c02-luu2"), goc=a["doi_chieu"]["doi_chieu_id"], rev=1)
        a2 = self.dc.luu_doi_chieu(self.KT1, b)
        self.assertEqual((a2["doi_chieu"]["revision"], a2["kt"]["thieu"]), (2, ["THIEU_HOA_DON"]))
        self.assertEqual(a2["doi_chieu"]["tap_sha256"], a["doi_chieu"]["tap_sha256"])
        self.luu_rev(truoc, 1, tap=0, nguon_pb=1)
        self.s.update(a1b=a2)

    # ------------------------------------------------------------------ C03 cross-source dương (cổng hóa đơn): NT-only → CÙNG gốc thêm hóa đơn → xác nhận
    def test_c03_cross_source_kt_xac_nhan(self):
        self.can("h1", "a1b")
        self.can_hoa_don()
        try:
            rh, it = self.ref_hd()
        except Exception as exc:  # noqa: BLE001
            self.skipTest(f"NOT_VERIFIED: KT1 không đọc được hóa đơn {ENV_HOA_DON} ({self.ma(exc)}) — cần module M2 cho KT1 trên PN hóa đơn")
        rn = self.s["r1"]
        goc = self.s["a1b"]["doi_chieu"]["doi_chieu_id"]
        x = self.xem_dc([rn, rh])
        nt = next(i for i in x["nguon"] if i["kind"] == "NT")
        if it["phap_nhan_id"] != nt["phap_nhan_id"]:
            self.skipTest("NOT_VERIFIED: hóa đơn khác PN của hồ sơ DEMO — phụ thuộc clone của Root")
        self.assertIsNone(x["doi_chieu"]["goc_cua_tap"])
        cu = self.cuoi(goc)
        anh = self.anh_goc(goc)
        n_hd = 0 if self.co_nguon(rh["occurrence_id"]) else 1
        truoc = self.dem_tat_ca()
        b = self.than([rh, rn], x, self.K("c03-them-hd"), goc=goc, rev=cu["revision"],
                      ly_do="Bổ sung hóa đơn mua vào đối chiếu nghiệm thu")  # thứ tự body: hóa đơn trước — máy chủ sắp lại
        a = self.dc.luu_doi_chieu(self.KT1, b)
        self.assertEqual((a["doi_chieu"]["doi_chieu_id"], a["doi_chieu"]["revision"]), (goc, cu["revision"] + 1), "cùng gốc, revision nối tiếp")
        self.assertEqual(a["doi_chieu"]["tap_sha256"], x["doi_chieu"]["khoa_goc_sha256"])
        self.assertNotEqual(a["doi_chieu"]["tap_sha256"], cu["tap_sha256"])
        self.luu_rev(truoc, 2, tap=1, nguon=n_hd)
        self.giu_lich_su(anh, self.anh_goc(goc))
        self.assertEqual(self.module_goc(goc), ("M4", ["M4"]), "namespace biên nhận theo gốc, không đổi khi thêm hóa đơn")
        if a["kt"]["thieu"] == ["BEN_BAN_KHAC"]:
            # âm thật: không khớp tên/ngày/tiền — MST master HĐ ≠ mst_ban → NHAP lưu được nhưng không xác nhận (vẫn chờ)
            truoc = self.dem_tat_ca()
            self.assertEqual(self.loi(self.dc.xac_nhan_doi_chieu, self.KT1, self.xn_cua(a, self.K("c03-khac-xn"))), "DC_CHO_BO_SUNG")
            self.doi_dc(truoc)
            self.skipTest("NOT_VERIFIED (dương): mst_ban hóa đơn ≠ MST đối tác HĐ DEMO — cần hóa đơn M2 có sẵn của đúng bên bán (phụ thuộc Root)")
        self.assertEqual(a["kt"]["thieu"], [], "căn cứ đủ: NT hiện hành + KT 03A đã xác nhận + cùng PN + MST master = mst_ban")
        self.assertEqual(it["money_basis_state"], "UNPROVEN_NO_MINOR")
        # xác nhận: sao y nháp, KT_XAC_NHAN_CAN_CU, 0 tài chính, alias 0
        truoc = self.dem_tat_ca()
        c = self.dc.xac_nhan_doi_chieu(self.KT1, self.xn_cua(a, self.K("c03-xn")))
        self.assertEqual((c["doi_chieu"]["trang_thai"], c["doi_chieu"]["revision"], c["doi_chieu"]["nhap_id"], c["ghi_nhan"]),
                         (SG.TT_XAC_NHAN, a["doi_chieu"]["revision"] + 1, a["doi_chieu"]["phien_ban_id"], GN.GHI_NHAN))
        self.assertEqual(c["doi_chieu"]["tap_sha256"], a["doi_chieu"]["tap_sha256"])
        self.doi_dc(truoc, kho__mua_doi_chieu_can_cu_phien_ban=1, kho__mua_doi_chieu_can_cu_thanh_phan=2, kho__mua_doi_chieu_can_cu_nhat_ky=1,
                    kho__bien_nhan_thao_tac=1)
        self.assertEqual(self.q("SELECT module FROM kho.bien_nhan_thao_tac WHERE id = %s", (c["receipt_id"],)), "M4")
        # khóa mới sau xác nhận → cùng xác nhận (trung_xac_nhan), không revision mới
        truoc = self.dem_tat_ca()
        c2 = self.dc.xac_nhan_doi_chieu(self.KT1, self.xn_cua(a, self.K("c03-xn2")))
        self.assertEqual((c2["doi_chieu"]["phien_ban_id"], c2["doi_chieu"]["trung_xac_nhan"]), (c["doi_chieu"]["phien_ban_id"], True))
        self.doi_dc(truoc, kho__bien_nhan_thao_tac=1)
        ls = self.dc.lich_su(self.KT1, goc)
        pbs = ls["doi_chieu"]["phien_ban"]
        self.assertEqual([p["phien_ban_id"] for p in pbs[:2]], [self.s["a1"]["doi_chieu"]["phien_ban_id"], self.s["a1b"]["doi_chieu"]["phien_ban_id"]])
        self.assertEqual([len(p["noi_dung"]["thanh_phan"]) for p in pbs], [1] * (len(pbs) - 2) + [2, 2])
        self.assertEqual(pbs[-1]["trang_thai"], SG.TT_XAC_NHAN)
        self.assertEqual({t["tap_sha256"] for t in ls["doi_chieu"]["bo_tap"]}, {cu["tap_sha256"], a["doi_chieu"]["tap_sha256"]})
        self.assertEqual(ls["module_bien_nhan"], "M4")
        # Checklist 7: cùng hóa đơn ở gốc khác phải bị chặn, có nhãn và trường.
        h2 = self.ho_so_seal("DC3")
        r2 = self.ref_nt(self.xem(h2["cho"]))
        x2 = self.xem_dc([r2, rh])
        truoc = self.dem_tat_ca()
        with self.assertRaises(DataError) as cm:
            self.dc.luu_doi_chieu(self.KT1, self.than([r2, rh], x2, self.K("c03-trung")))
        self.assertEqual(cm.exception.code, "DC_HOA_DON_DA_GAN")
        self.assertIn("đã gắn ở", str(cm.exception))
        self.assertIn(goc, str(cm.exception))
        self.assertTrue(cm.exception.locator.startswith("thanh_phan."))
        self.doi_dc(truoc)
        # Cùng một đối chiếu: một hóa đơn ↔ nhiều đợt vẫn hợp lệ, phiên bản
        # mới giữ hóa đơn rồi bớt đợt cũng không xung đột với chính gốc A.
        a3 = self.dc.luu_doi_chieu(self.KT1, self.than([rn, r2, rh], self.xem_dc([rn, r2, rh]), self.K("c03-nn"),
                                                                    goc=goc, rev=c["doi_chieu"]["revision"]))
        self.assertEqual(a3["doi_chieu"]["doi_chieu_id"], goc)
        self.assertIn("NT_CHUA_KT_XAC_NHAN", a3["kt"]["thieu"])
        a4 = self.dc.luu_doi_chieu(self.KT1, self.than([rn, rh], self.xem_dc([rn, rh]), self.K("c03-giu-hd"),
                                                                    goc=goc, rev=a3["doi_chieu"]["revision"]))
        self.assertEqual(a4["doi_chieu"]["doi_chieu_id"], goc)
        self.s.update(rh=rh, a3x=c, r2=r2)

    # ------------------------------------------------------------------ C04 đổi tập cùng gốc + stale / CAS
    def test_c04_doi_tap_cung_goc_va_cas(self):
        self.can("h1", "a1b", "r1")
        r1 = self.s["r1"]
        goc = self.s["a1b"]["doi_chieu"]["doi_chieu_id"]
        # setup nguồn (producer thật) TRƯỚC ảnh đếm — oracle 0 delta chỉ đo lệnh đối chiếu
        h3 = self.ho_so_seal("DC4")
        r3 = self.ref_nt(self.xem(h3["cho"]))
        cu = self.cuoi(goc)
        rev = cu["revision"]
        base = self.tap_hien(goc)
        them = base + [r3]
        x_base, x_them = self.xem_dc(base), self.xem_dc(them)
        self.assertIsNone(x_them["doi_chieu"]["goc_cua_tap"])
        self.assertEqual(x_base["doi_chieu"]["goc_cua_tap"], goc)
        truoc = self.dem_tat_ca()
        # stale: phiên bản nguồn cũ / đồ thị cũ / revision cũ (cùng tập và đổi tập) → 0 delta
        cu_nguon = [{**r, "source_version_id": str(uuid.uuid4())} if r["occurrence_id"] == r1["occurrence_id"] else r for r in base]
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, self.than(cu_nguon, x_base, self.K("c04-nguon"), goc=goc, rev=rev)), "DC_NGUON_CU")
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, {**self.than(base, x_base, self.K("c04-graph"), goc=goc, rev=rev),
                                                                     "expected_graph": "0" * 64}), "DC_DO_THI_DOI")
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, self.than(base, x_base, self.K("c04-rev"), goc=goc, rev=rev - 1)), "DC_REVISION_CU")
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, self.than(them, x_them, self.K("c04-tap-cu"), goc=goc, rev=rev - 1)),
                         "DC_REVISION_CU")
        self.doi_dc(truoc)
        # dương: thêm NT (body thứ tự ngược) → revision CÙNG gốc, tập mới, alias +1; thiếu thật vẫn chờ (NT mới chưa KT xác nhận)
        anh = self.anh_goc(goc)
        b_them = self.than(list(reversed(them)), x_them, self.K("c04-them"), goc=goc, rev=rev, ly_do="Thêm nghiệm thu đợt bổ sung")
        a = self.dc.luu_doi_chieu(self.KT1, b_them)
        self.assertEqual((a["lap_lai"], a["doi_chieu"]["doi_chieu_id"], a["doi_chieu"]["revision"]), (False, goc, rev + 1))
        self.assertEqual(a["doi_chieu"]["tap_sha256"], x_them["doi_chieu"]["khoa_goc_sha256"])
        self.assertIn("NT_CHUA_KT_XAC_NHAN", a["kt"]["thieu"])
        self.luu_rev(truoc, len(them), tap=1, nguon=1)
        self.giu_lich_su(anh, self.anh_goc(goc))
        self.assertEqual(self.module_goc(goc)[0], "M4")
        self.s.update(h3=h3, r3=r3)
        # thứ tự ref ngược khi xem → cùng identity (đồ thị, digest tập, gốc của tập)
        xr = self.xem_dc(list(reversed(them)))
        self.assertEqual((xr["doi_chieu"]["graph_sha256"], xr["doi_chieu"]["khoa_goc_sha256"], xr["doi_chieu"]["goc_cua_tap"]),
                         (x_them["doi_chieu"]["graph_sha256"], a["doi_chieu"]["tap_sha256"], goc))
        # bớt NT: ABA về tập cũ → cùng gốc, alias 0
        truoc = self.dem_tat_ca()
        a2 = self.dc.luu_doi_chieu(self.KT1, self.than(base, x_base, self.K("c04-bot"), goc=goc, rev=rev + 1, ly_do="Bỏ nghiệm thu bổ sung"))
        self.assertEqual((a2["doi_chieu"]["doi_chieu_id"], a2["doi_chieu"]["revision"], a2["doi_chieu"]["tap_sha256"]), (goc, rev + 2, cu["tap_sha256"]))
        self.luu_rev(truoc, len(base), tap=0)
        # phát lại khóa cũ sau đổi thành viên → đúng ID cũ; khóa cũ khác body → 409; khóa mới body cũ → CAS; tạo gốc mới tập đã thuộc gốc → chặn
        truoc = self.dem_tat_ca()
        a3 = self.dc.luu_doi_chieu(self.KT1, b_them)
        self.assertEqual((a3["lap_lai"], a3["receipt_id"], a3["doi_chieu"]["phien_ban_id"], a3["doi_chieu"]["doi_chieu_id"]),
                         (True, a["receipt_id"], a["doi_chieu"]["phien_ban_id"], goc))
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, {**b_them, "ly_do": "khác"}), "DC_IDEMPOTENCY_KHAC")
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, {**b_them, "khoa": self.K("c04-them-moi")}), "DC_REVISION_CU")
        ma_trung = "DC_HOA_DON_DA_GAN" if any(r["kind"] == "HOA_DON" for r in base) else "DC_DA_CO_GOC"
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, self.than(them, x_them, self.K("c04-goc-moi"))), ma_trung)
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, self.than(base, x_base, self.K("c04-goc-cu"))), ma_trung)
        self.doi_dc(truoc)
        ls = self.dc.lich_su(self.KT1, goc)
        self.assertEqual(ls["doi_chieu_id"], goc)
        self.assertEqual(ls["khoa_goc_sha256"], anh["goc"]["khoa_goc_sha256"], "digest tạo bất biến")
        self.assertTrue({cu["tap_sha256"], a["doi_chieu"]["tap_sha256"]} <= {t["tap_sha256"] for t in ls["doi_chieu"]["bo_tap"]})

    # ------------------------------------------------------------------ C05 từ chối quyền
    def test_c05_tu_choi(self):
        self.can("a1b", "r1")
        a = self.s["a1b"]
        goc = a["doi_chieu"]["doi_chieu_id"]
        truoc = self.dem_tat_ca()
        self.assertIn(self.loi(self.xem_dc, [self.s["r1"]], self.KT_KHAC), ("M4_KT_PHAM_VI", "M4_KT_KHONG_THAY"))
        x = self.xem_dc([self.s["r1"]])
        self.assertIn(self.loi(self.dc.luu_doi_chieu, self.KT_KHAC, self.than([self.s["r1"]], x, self.K("c05-khac"), goc=goc, rev=2)),
                      ("M4_KT_PHAM_VI", "M4_KT_KHONG_THAY"))
        self.assertIn(self.loi(self.dc.lich_su, self.KT_KHAC, goc), ("DC_KHONG_THAY",))
        self.assertEqual(self.loi(self.dc.xac_nhan_doi_chieu, self.KT_KHAC, self.xn_cua(a, self.K("c05-xn"))), "DC_KHONG_THAY")
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
        goc, pb = a["doi_chieu"]["doi_chieu_id"], a["doi_chieu"]["phien_ban_id"]
        truoc = self.dem_tat_ca()
        pn = self.q("SELECT phap_nhan_id FROM kho.mua_doi_chieu_can_cu WHERE id = %s", (goc,))
        aid = self.q("SELECT tao_boi_id FROM kho.mua_doi_chieu_can_cu WHERE id = %s", (goc,))
        for sql, p in (("INSERT INTO kho.mua_doi_chieu_can_cu (phap_nhan_id, khoa_goc_sha256, module_bien_nhan, tao_boi, tao_boi_id) "
                        "VALUES (%s, %s, 'M4', 'x', %s)", (pn, "1" * 64, str(uuid.uuid4()))),
                       ("INSERT INTO kho.mua_doi_chieu_can_cu_tap (phap_nhan_id, tap_sha256, doi_chieu_id, phien_ban_id, tao_boi, tao_boi_id) "
                        "VALUES (%s, %s, %s, %s, 'x', %s)", (pn, "4" * 64, goc, pb, aid)),
                       ("UPDATE kho.mua_doi_chieu_can_cu_phien_ban SET ly_do = 'x'", ()),
                       ("UPDATE kho.mua_doi_chieu_can_cu SET module_bien_nhan = 'M2'", ()),
                       ("DELETE FROM kho.mua_doi_chieu_can_cu_tap", ()),
                       ("DELETE FROM kho.mua_nguon_kinh_te", ()),
                       ("SELECT kho.dc_luu('x', '{}'::jsonb)", ()),
                       ("SELECT kho._dc_nt_ghi(%s::uuid)", (self.s["h1"]["cho"],)),
                       ("SELECT kho._dc_do_thi('[]'::jsonb)", ()),
                       ("SELECT kho._dc_hop('[]'::jsonb, '[]'::jsonb)", ()),
                       ("INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor) "
                        "VALUES (%s, 'M4', 'DC_CAN_CU_LUU', 'gia', %s, '{}'::jsonb, %s)", (pn, "2" * 64, self.KT1)),
                       ("INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor) "
                        "VALUES (%s, 'M2', 'DC_CAN_CU_XAC_NHAN', 'gia2', %s, '{}'::jsonb, %s)", (pn, "3" * 64, self.KT1))):
            self.assertIsNotNone(self.app_loi(sql, p), sql)
        # Đủ 6 hàm trong REVOKE M0033: phải lỗi quyền, không nhận lỗi nghiệp vụ thay thế.
        for sql, p in (("SELECT kho._dc_hd_da_gan(%s::uuid, NULL::uuid)", (str(uuid.uuid4()),)),
                       ("SELECT kho._dc_kiem_hd_da_gan('[]'::jsonb, NULL::uuid)", ()),
                       ("SELECT kho._dc_so_tien_hop_le('1'::text, 'VND'::text)", ()),
                       ("SELECT kho._dc_kiem_tien_tp('[]'::jsonb)", ()),
                       ("SELECT kho._dc_dot_goi_y(%s::uuid)", (self.s["h1"]["dot"],)),
                       ("SELECT kho._dc_goi_y_hoa_don(%s::uuid)", (self.s["h1"]["dot"],))):
            with self.subTest(sql=sql):
                self.assertEqual(self.app_loi(sql, p), "InsufficientPrivilege", sql)
        self.doi_dc(truoc)
        # owner: lệnh không ghim producer / GUC giả → không hiện hành
        x = self.xem_dc([self.s["r1"]])
        b = self.than([self.s["r1"]], x, self.K("c06-khong-ghim"), goc=goc, rev=self.cuoi(goc)["revision"])
        y = GN.yeu_cau_luu(b)
        y.pop("khoa")
        yc = json.dumps(y, ensure_ascii=False)
        self.assertEqual(self.chu_loi(("SELECT kho.dc_luu(%s, %s::jsonb) AS r", (b["khoa"], yc))), "DC_CAN_KIEM_LAI")
        gia = json.dumps({"pid": "0", "txid": "0", "actor": "x", "cho": {self.s["h1"]["cho"]: {"hien_hanh": True, "toan_ven": True}}})
        self.assertEqual(self.chu_loi(("SELECT set_config(%s, %s, true) AS r", (SG.GUC_NT, gia)),
                                      ("SELECT kho.dc_luu(%s, %s::jsonb) AS r", (b["khoa"] + "g", yc))), "DC_CAN_KIEM_LAI")
        # owner sửa lịch sử / gắn alias ngoài lệnh (trỏ revision cũ) / đổi namespace gốc → chặn
        self.assertEqual(self.chu_loi(("UPDATE kho.mua_doi_chieu_can_cu_phien_ban SET ly_do = 'x' WHERE id = %s RETURNING id AS r", (pb,))),
                         "DC_BAT_BIEN")
        self.assertEqual(self.chu_loi(("UPDATE kho.mua_doi_chieu_can_cu SET module_bien_nhan = 'M2' WHERE id = %s RETURNING id AS r", (goc,))),
                         "DC_BAT_BIEN")
        self.assertEqual(self.chu_loi(("INSERT INTO kho.mua_doi_chieu_can_cu_tap (phap_nhan_id, tap_sha256, doi_chieu_id, phien_ban_id, tao_boi, "
                                       "tao_boi_id) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id AS r", (pn, "4" * 64, goc, pb, self.KT1, aid))),
                         "DC_BAT_BIEN")
        self.doi_dc(truoc)

    # ------------------------------------------------------------------ C07 đồng thời tạo gốc + xung đột alias
    def test_c07_dong_thoi_mot_goc(self):
        self.can("r3", "a1b")
        r3 = self.s["r3"]
        x = self.xem_dc([r3])
        self.assertIsNone(x["doi_chieu"]["goc_cua_tap"])
        dcs = self.dich_vu_rieng(3)
        truoc = self.dem_tat_ca()
        kq, loi = self.song_song([lambda d=d, i=i: d.luu_doi_chieu(self.KT1, self.than([r3], x, self.K(f"c07-{i}"))) for i, d in enumerate(dcs)])
        self.assertEqual(len(kq), 1, (kq, loi))
        self.assertEqual(sorted(loi), ["DC_DA_CO_GOC", "DC_DA_CO_GOC"])
        self.luu_moi(truoc, 0, 1)  # identity r3 đã có từ C04
        goc_d = kq[0]["doi_chieu"]["doi_chieu_id"]
        self.assertEqual(self.xem_dc([r3])["doi_chieu"]["goc_cua_tap"], goc_d)
        # sửa gốc khác sang tập đã thuộc gốc này → 409, không gộp/dời lịch sử, 0 delta
        goc = self.s["a1b"]["doi_chieu"]["doi_chieu_id"]
        anh = self.anh_goc(goc)
        truoc = self.dem_tat_ca()
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, self.than([r3], x, self.K("c07-xung"), goc=goc, rev=self.cuoi(goc)["revision"])),
                         "DC_TAP_THUOC_GOC_KHAC")
        self.doi_dc(truoc)
        self.assertEqual(self.anh_goc(goc), anh)
        self.s.update(goc_d=goc_d)

    # ------------------------------------------------------------------ C08 hóa đơn trước → CÙNG gốc thêm NT (cổng hóa đơn)
    def test_c08_hoa_don_truoc_cung_goc(self):
        self.can("rh", "r2", "r1", "a1b")
        rh, r2 = self.s["rh"], self.s["r2"]
        goc_a = self.s["a1b"]["doi_chieu"]["doi_chieu_id"]
        # A đang giữ hóa đơn: invoice-only cũng bị chặn. Revision mới bỏ hóa
        # đơn giải phóng liên kết hiện hành, lịch sử của A vẫn nguyên byte.
        truoc = self.dem_tat_ca()
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, self.than([rh], self.xem_dc([rh]), self.K("c08-trung"))),
                         "DC_HOA_DON_DA_GAN")
        self.doi_dc(truoc)
        giu_nt = [r for r in self.tap_hien(goc_a) if r["kind"] != "HOA_DON"]
        anh_a = self.anh_goc(goc_a)
        self.dc.luu_doi_chieu(self.KT1, self.than(giu_nt, self.xem_dc(giu_nt), self.K("c08-a-bo-hd"),
                                               goc=goc_a, rev=self.cuoi(goc_a)["revision"]))
        self.giu_lich_su(anh_a, self.anh_goc(goc_a))
        xh = self.xem_dc([rh])
        self.assertIsNone(xh["doi_chieu"]["goc_cua_tap"])
        truoc = self.dem_tat_ca()
        a = self.dc.luu_doi_chieu(self.KT1, self.than([rh], xh, self.K("c08-tao")))
        goc = a["doi_chieu"]["doi_chieu_id"]
        self.assertIn("THIEU_NT", a["kt"]["thieu"])
        self.luu_moi(truoc, 0, 1)  # identity hóa đơn đã có từ C03
        self.assertEqual(self.module_goc(goc), ("M2", ["M2"]), "gốc tạo chỉ hóa đơn → namespace M2")
        # Tập lịch sử {r1, hóa đơn} vẫn có alias của A, không chuyển lịch sử.
        x2 = self.xem_dc([rh, self.s["r1"]])
        self.assertEqual(x2["doi_chieu"]["goc_cua_tap"], goc_a)
        truoc = self.dem_tat_ca()
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, self.than([rh, self.s["r1"]], x2, self.K("c08-xung"), goc=goc, rev=1)), "DC_TAP_THUOC_GOC_KHAC")
        self.doi_dc(truoc)
        # thêm NT mới → revision CÙNG gốc, namespace vẫn M2; thiếu thật (NT chưa KT xác nhận) vẫn chờ
        h5 = self.ho_so_seal("DC8")
        r5 = self.ref_nt(self.xem(h5["cho"]))
        x5 = self.xem_dc([r5, rh])
        anh = self.anh_goc(goc)
        truoc = self.dem_tat_ca()
        b_them = self.than([r5, rh], x5, self.K("c08-them"), goc=goc, rev=1, ly_do="Bổ sung nghiệm thu cho hóa đơn")
        a2 = self.dc.luu_doi_chieu(self.KT1, b_them)
        self.assertEqual((a2["lap_lai"], a2["doi_chieu"]["doi_chieu_id"], a2["doi_chieu"]["revision"]), (False, goc, 2))
        self.assertIn("NT_CHUA_KT_XAC_NHAN", a2["kt"]["thieu"])
        self.luu_rev(truoc, 2, tap=1, nguon=1)
        self.giu_lich_su(anh, self.anh_goc(goc))
        self.assertEqual(self.module_goc(goc), ("M2", ["M2"]), "thêm NT không đổi namespace biên nhận")
        truoc = self.dem_tat_ca()
        self.assertEqual(self.loi(self.dc.xac_nhan_doi_chieu, self.KT1, self.xn_cua(a2, self.K("c08-xn"))), "DC_CHO_BO_SUNG")
        self.doi_dc(truoc)
        # bớt hóa đơn (chỉ còn NT) → tập mới cùng gốc; ABA về {hóa đơn} → alias 0
        a3 = self.dc.luu_doi_chieu(self.KT1, self.than([r5], self.xem_dc([r5]), self.K("c08-bo-hd"), goc=goc, rev=2))
        self.luu_rev(truoc, 1, tap=1)
        self.assertEqual((a3["doi_chieu"]["doi_chieu_id"], a3["doi_chieu"]["revision"]), (goc, 3))
        truoc = self.dem_tat_ca()
        a4 = self.dc.luu_doi_chieu(self.KT1, self.than([rh], self.xem_dc([rh]), self.K("c08-aba"), goc=goc, rev=3))
        self.assertEqual((a4["doi_chieu"]["revision"], a4["doi_chieu"]["tap_sha256"]), (4, a["doi_chieu"]["tap_sha256"]))
        self.luu_rev(truoc, 1, tap=0)
        # phát lại sau đổi thành viên; khóa cũ khác body; khóa mới body cũ; gốc mới cho tập đã thuộc gốc
        truoc = self.dem_tat_ca()
        a2b = self.dc.luu_doi_chieu(self.KT1, b_them)
        self.assertEqual((a2b["lap_lai"], a2b["receipt_id"], a2b["doi_chieu"]["phien_ban_id"]), (True, a2["receipt_id"], a2["doi_chieu"]["phien_ban_id"]))
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, {**b_them, "ly_do": "khác"}), "DC_IDEMPOTENCY_KHAC")
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, {**b_them, "khoa": self.K("c08-them-moi")}), "DC_REVISION_CU")
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, self.than([rh], self.xem_dc([rh]), self.K("c08-goc-moi"))), "DC_HOA_DON_DA_GAN")
        self.assertEqual(self.loi(self.dc.luu_doi_chieu, self.KT1, self.than([r5, rh], x5, self.K("c08-goc-moi2"))), "DC_HOA_DON_DA_GAN")
        self.doi_dc(truoc)
        self.assertEqual(self.module_goc(goc), ("M2", ["M2"]))
        self.s.update(goc_c=goc, r5=r5)
        def bo_hd():
            self.dc.luu_doi_chieu(self.KT1, self.than([r5], self.xem_dc([r5]), self.K("c08-c-bo-hd"),
                                                   goc=goc, rev=self.cuoi(goc)["revision"]))
        # đổi phần: toàn bộ hóa đơn ↔ dòng logic có thật (tùy chọn)
        dong = os.environ.get(ENV_DONG)
        if not dong:
            bo_hd()
            return  # phần tùy chọn chưa chạy; ca gốc invoice-only phía trên đã kiểm thật
        rl, itl = self.ref_hd(part=dong)
        xl = self.xem_dc([rl])
        n_phan = 0 if self.q("SELECT count(*) FROM kho.mua_nguon_phan WHERE dong_danh_tinh_id = %s", (dong,)) else 1
        truoc = self.dem_tat_ca()
        a5 = self.dc.luu_doi_chieu(self.KT1, self.than([rl], xl, self.K("c08-dong"), goc=goc, rev=4, ly_do="Chỉ đối chiếu một dòng hóa đơn"))
        self.assertEqual((a5["doi_chieu"]["doi_chieu_id"], a5["doi_chieu"]["revision"]), (goc, 5))
        if not itl["cau_noi"]:
            self.assertIn("CHO_MAPPING_M2", a5["kt"]["thieu"], "dòng chưa có mapping M2 → vẫn chờ, không suy")
        self.luu_rev(truoc, 1, tap=1, phan=n_phan)
        truoc = self.dem_tat_ca()
        a6 = self.dc.luu_doi_chieu(self.KT1, self.than([rh], self.xem_dc([rh]), self.K("c08-toan"), goc=goc, rev=5))
        self.assertEqual((a6["doi_chieu"]["revision"], a6["doi_chieu"]["tap_sha256"]), (6, a["doi_chieu"]["tap_sha256"]))
        self.luu_rev(truoc, 1, tap=0)
        bo_hd()

    # ------------------------------------------------------------------ C09 hai kết nối cạnh tranh đổi tập của cùng gốc
    def test_c09_dong_thoi_doi_tap(self):
        self.can("a1b", "r1", "r3")
        r1, r3 = self.s["r1"], self.s["r3"]
        goc = self.s["a1b"]["doi_chieu"]["doi_chieu_id"]
        h6 = self.ho_so_seal("DC9")
        r6 = self.ref_nt(self.xem(h6["cho"]))
        cu = self.cuoi(goc)
        rev = cu["revision"]
        taps = ([r1, r6], [r1, r3, r6])
        xs = [self.xem_dc(t) for t in taps]
        dcs = self.dich_vu_rieng(2)
        bodies = [self.than(t, x, self.K(f"c09-{i}"), goc=goc, rev=rev) for i, (t, x) in enumerate(zip(taps, xs))]
        truoc = self.dem_tat_ca()
        kq, loi = self.song_song([lambda d=d, b=b: d.luu_doi_chieu(self.KT1, b) for d, b in zip(dcs, bodies)])
        self.assertEqual((len(kq), loi), (1, ["DC_REVISION_CU"]), (kq, loi))
        w = kq[0]["doi_chieu"]
        thang = next(i for i, x in enumerate(xs) if x["doi_chieu"]["khoa_goc_sha256"] == w["tap_sha256"])
        thua = 1 - thang
        # bằng chứng CAS đã commit (không dựa thời gian): đúng +1 revision nối tiếp revision đã đọc; alias chỉ của bên thắng
        pbs = self.q("SELECT jsonb_agg(jsonb_build_object('id', v.id, 'revision', v.revision, 'truoc_id', v.truoc_id) ORDER BY v.revision) "
                     "FROM kho.mua_doi_chieu_can_cu_phien_ban v WHERE v.doi_chieu_id = %s", (goc,))
        self.assertEqual((pbs[-1]["revision"], pbs[-1]["id"], pbs[-1]["truoc_id"]), (rev + 1, w["phien_ban_id"], cu["phien_ban_id"]))
        self.assertEqual(self.q("SELECT count(*) FROM kho.mua_doi_chieu_can_cu_tap WHERE tap_sha256 = %s",
                                (xs[thua]["doi_chieu"]["khoa_goc_sha256"],)), 0)
        self.luu_rev(truoc, len(taps[thang]), tap=1, nguon=1)
        # thứ tự thắng ngược: bên thua trước (CAS rev+1) rồi bên thắng cũ với cùng revision → DC_REVISION_CU
        truoc = self.dem_tat_ca()
        b_thua = self.than(taps[thua], self.xem_dc(taps[thua]), self.K("c09-nguoc-thua"), goc=goc, rev=rev + 1)
        b_thang = self.than(taps[thang], self.xem_dc(taps[thang]), self.K("c09-nguoc-thang"), goc=goc, rev=rev + 1)
        n = dcs[thua].luu_doi_chieu(self.KT1, b_thua)
        self.assertEqual((n["doi_chieu"]["doi_chieu_id"], n["doi_chieu"]["revision"]), (goc, rev + 2))
        self.assertEqual(self.loi(dcs[thang].luu_doi_chieu, self.KT1, b_thang), "DC_REVISION_CU")
        self.luu_rev(truoc, len(taps[thua]), tap=1)

    # ------------------------------------------------------------------ C10 xác nhận vs revision (cổng hóa đơn dương)
    def test_c10_xac_nhan_vs_revision(self):
        self.can("a3x", "rh", "r1")
        r1, rh = self.s["r1"], self.s["rh"]
        goc = self.s["a1b"]["doi_chieu"]["doi_chieu_id"]
        du = [r1, rh]
        xf = self.xem_dc(du)
        self.assertEqual((xf["kt"]["thieu"], xf["doi_chieu"]["goc_cua_tap"]), ([], goc))
        x1 = self.xem_dc([r1])
        dcs = self.dich_vu_rieng(2)

        def nhap(nhan):
            return self.dc.luu_doi_chieu(self.KT1, self.than(du, xf, self.K(f"c10-nhap-{nhan}"), goc=goc, rev=self.cuoi(goc)["revision"]))

        def kiem_ket_thuc(truoc, d, xac_nhan_thang: bool):
            pbs = self.q("SELECT jsonb_agg(to_jsonb(v) ORDER BY v.revision) FROM kho.mua_doi_chieu_can_cu_phien_ban v WHERE v.doi_chieu_id = %s",
                         (goc,))
            cuoi = pbs[-1]
            self.assertEqual((cuoi["revision"], cuoi["truoc_id"]), (d["doi_chieu"]["revision"] + 1, d["doi_chieu"]["phien_ban_id"]))
            if xac_nhan_thang:
                self.assertEqual((cuoi["loai"], cuoi["nhap_id"]), ("XAC_NHAN", d["doi_chieu"]["phien_ban_id"]))
                self.doi_dc(truoc, kho__mua_doi_chieu_can_cu_phien_ban=1, kho__mua_doi_chieu_can_cu_thanh_phan=2,
                            kho__mua_doi_chieu_can_cu_nhat_ky=1, kho__bien_nhan_thao_tac=1)
            else:
                self.assertEqual((cuoi["loai"], cuoi["tap_sha256"]), ("NHAP", x1["doi_chieu"]["khoa_goc_sha256"]))
                self.luu_rev(truoc, 1, tap=0)

        # đua thật hai kết nối: đúng một thành công, bên kia DC_REVISION_CU; trạng thái commit quyết định bên thắng
        d = nhap("dua")
        xn = self.xn_cua(d, self.K("c10-xn-dua"))
        rv = self.than([r1], x1, self.K("c10-rv-dua"), goc=goc, rev=d["doi_chieu"]["revision"])
        truoc = self.dem_tat_ca()
        kq, loi = self.song_song([lambda: dcs[0].xac_nhan_doi_chieu(self.KT1, xn), lambda: dcs[1].luu_doi_chieu(self.KT1, rv)])
        self.assertEqual((len(kq), loi), (1, ["DC_REVISION_CU"]), (kq, loi))
        kiem_ket_thuc(truoc, d, kq[0]["doi_chieu"]["trang_thai"] == SG.TT_XAC_NHAN)
        # cả hai thứ tự thắng, xác định bằng CAS đã commit
        for xn_truoc in (True, False):
            nhan = "xn" if xn_truoc else "rv"
            d = nhap(f"thu-tu-{nhan}")
            xn = self.xn_cua(d, self.K(f"c10-xn-{nhan}"))
            rv = self.than([r1], x1, self.K(f"c10-rv-{nhan}"), goc=goc, rev=d["doi_chieu"]["revision"])
            truoc = self.dem_tat_ca()
            if xn_truoc:
                dcs[0].xac_nhan_doi_chieu(self.KT1, xn)
                self.assertEqual(self.loi(dcs[1].luu_doi_chieu, self.KT1, rv), "DC_REVISION_CU")
            else:
                dcs[1].luu_doi_chieu(self.KT1, rv)
                self.assertEqual(self.loi(dcs[0].xac_nhan_doi_chieu, self.KT1, xn), "DC_REVISION_CU")
            kiem_ket_thuc(truoc, d, xn_truoc)

    # ------------------------------------------------------------------ M4-5a: chạy trên clone đã migrate M0033, không tự migrate/server
    def test_c11_so_tien_nhap_phat_lai_revision_va_thieu(self):
        h = self.ho_so_seal("DC33A")
        r = self.ref_nt(self.nt_xac_nhan_03a(h))
        x = self.xem_dc([r])
        b = self.than([r], x, self.K("c33-nhap"))
        b["thanh_phan"] = [{"nguon": r, "phan": "MOT_PHAN", "so_tien_khai": "1", "tien_te": "VND"}]
        truoc = self.dem_tat_ca()
        a = self.dc.luu_doi_chieu(self.KT1, b)
        self.luu_moi(truoc, 1, 1)
        self.assertEqual(a["kt"]["thieu"], ["THIEU_HOA_DON"])
        pb = a["doi_chieu"]["phien_ban_id"]
        self.assertEqual(self.q("SELECT jsonb_build_array(so_tien_khai::text,tien_te,ty_le_khai,ty_le_trang_thai) "
                               "FROM kho.mua_doi_chieu_can_cu_thanh_phan WHERE phien_ban_id = %s", (pb,)),
                         ["1", "VND", None, "KHAI_SO_TIEN"])
        truoc = self.dem_tat_ca()
        self.assertTrue(self.dc.luu_doi_chieu(self.KT1, b)["lap_lai"])
        self.doi_dc(truoc)
        goc = a["doi_chieu"]["doi_chieu_id"]
        cu = self.anh_goc(goc)
        b2 = {**b, "doi_chieu_id": goc, "expected_revision": 1, "khoa": self.K("c33-thieu"),
              "thanh_phan": [{"nguon": r, "phan": "MOT_PHAN", "so_tien_khai": None, "tien_te": "VND"}]}
        a2 = self.dc.luu_doi_chieu(self.KT1, b2)
        self.assertIn("PHAN_KHAI_THIEU", a2["kt"]["thieu"])
        self.giu_lich_su(cu, self.anh_goc(goc))
        ls = self.dc.lich_su(self.KT1, goc)
        self.assertEqual(ls["kt"]["phan_khai_con_thieu"][0]["ly_do"], "PHAN_KHAI_THIEU")

    def test_c12_so_tien_xac_nhan_sao_y_deferred(self):
        self.can("rh", "r1", "a1b", "a3x")
        r, rh = self.s["r1"], self.s["rh"]
        goc = self.s["a1b"]["doi_chieu"]["doi_chieu_id"]
        x = self.xem_dc([r, rh])
        b = self.than([r, rh], x, self.K("c33-du"), goc=goc, rev=self.cuoi(goc)["revision"])
        b["thanh_phan"] = [{"nguon": r, "phan": "MOT_PHAN", "so_tien_khai": "1", "tien_te": "VND"},
                           {"nguon": rh, "phan": "TOAN_PHAN", "so_tien_khai": None, "tien_te": None}]
        a = self.dc.luu_doi_chieu(self.KT1, b)
        truoc = self.dem_tat_ca()
        xn = self.dc.xac_nhan_doi_chieu(self.KT1, self.xn_cua(a, self.K("c33-xn")))
        self.doi_dc(truoc, kho__mua_doi_chieu_can_cu_phien_ban=1, kho__mua_doi_chieu_can_cu_thanh_phan=2,
                    kho__mua_doi_chieu_can_cu_nhat_ky=1, kho__bien_nhan_thao_tac=1)
        for pb in (a["doi_chieu"]["phien_ban_id"], xn["doi_chieu"]["phien_ban_id"]):
            self.assertEqual(self.q("SELECT jsonb_build_array(m.so_tien_khai::text,m.tien_te,m.ty_le_trang_thai) "
                                   "FROM kho.mua_doi_chieu_can_cu_thanh_phan m JOIN kho.mua_nguon_kinh_te n ON n.id = m.nguon_id "
                                   "WHERE m.phien_ban_id = %s AND n.loai = 'NT'", (pb,)), ["1", "VND", "KHAI_SO_TIEN"])

    def test_c13_mien_sql_truc_tiep_khong_qua_python(self):
        truoc = self.dem_tat_ca()
        for so, tt, ok in (("1", "VND", True), ("0.01", "USD", True), ("999999999999999999.99", "USD", True),
                           ("0", "USD", False), ("-1", "VND", False), ("1.00", "VND", False), ("١", "USD", False),
                           ("1e2", "USD", False), ("NaN", "USD", False), ("1.234", "USD", False),
                           ("1000000000000000000", "USD", False)):
            with self.subTest(so=so, tt=tt):
                self.assertEqual(self.q("SELECT kho._dc_so_tien_hop_le(%s,%s)", (so, tt)), ok)
        for t in ({"phan": "MOT_PHAN", "ty_le_khai": "50%"}, {"phan": "MOT_PHAN", "ty_le_khai": None},
                  {"phan": "MOT_PHAN", "so_tien_khai": 1, "tien_te": "VND"},
                  {"phan": "TOAN_PHAN", "so_tien_khai": "1", "tien_te": "VND"}):
            self.assertEqual(self.chu_loi(("SELECT kho._dc_kiem_tien_tp(%s::jsonb) AS r", (json.dumps([t]),))), "DC_PHAN_SAI")
        self.doi_dc(truoc)

    def test_c14_goi_y_loc_quyen_va_da_gan(self):
        self.can("rh", "h1", "r2")
        truoc = self.dem_tat_ca()
        dot_id = self.q("SELECT dot_id FROM m4.duyet_kt_cho WHERE id = %s", (self.s["h1"]["cho"],))
        out = self.dc.goi_y_hoa_don(self.KT1, str(dot_id))
        self.assertFalse(out["khong_quyen"])
        for h in out["hoa_don"]:
            self.assertEqual(h["mst_ban"], self.q("SELECT t.mst FROM master.doi_tac t JOIN master.hop_dong hd ON hd.doi_tac_id=t.id "
                                                "JOIN m4.duyet_kt_cho c ON c.hop_dong_id=hd.id WHERE c.dot_id=%s", (dot_id,)))
            self.assertNotIn("score", h)
        target = next((h for h in out["hoa_don"] if h["nguon"]["occurrence_id"] == self.hd_id), None)
        if target:
            self.assertFalse(target["da_gan"], "hóa đơn của chính gốc A không bị gợi ý là gắn trùng")
            self.assertEqual(target["da_gan_o"], [])
        dot_khac = self.q("SELECT dot_id FROM m4.duyet_kt_cho WHERE id=%s", (self.s["r2"]["occurrence_id"],))
        out_khac = self.dc.goi_y_hoa_don(self.KT1, str(dot_khac))
        target_khac = next((h for h in out_khac["hoa_don"] if h["nguon"]["occurrence_id"] == self.hd_id), None)
        if target_khac:
            self.assertTrue(target_khac["da_gan"])
            self.assertIn("đã gắn ở", target_khac["da_gan_o"][0]["nhan"])
        self.doi_dc(truoc)

    def test_c15_goi_y_khong_quyen_m2(self):
        self.can("h1")
        dot_id = self.q("SELECT dot_id FROM m4.duyet_kt_cho WHERE id = %s", (self.s["h1"]["cho"],))
        pn = self.q("SELECT phap_nhan_id FROM m4.duyet_kt_cho WHERE dot_id=%s", (dot_id,))
        # Không cấp/thu hồi quyền trong test; clone cần sẵn KT dự án thiếu M2.
        for login in (self.KT1, self.KT2):
            xd = self.svc
            dt = xd.danh_tinh(login)
            with xd._tx_review(dt) as c:
                co = xd._r1(c, "SELECT kho._dc_m2_doc(%s) AS r", (pn,))["r"]
            if not co:
                truoc = self.dem_tat_ca()
                self.assertEqual(self.dc.goi_y_hoa_don(login, str(dot_id)), {"khong_quyen": True, "hoa_don": []})
                self.doi_dc(truoc)
                return
        self.skipTest("NOT_VERIFIED: clone chưa có KT dự án không có M2 (không tự thu hồi/cấp quyền)")

    def test_c16_ty_le_cu_van_doc_nguyen_nghia(self):
        cu = self.q("SELECT jsonb_build_object('ty_le_khai',m.ty_le_khai,'trang_thai',m.ty_le_trang_thai, "
                    "'so_tien_khai',m.so_tien_khai,'tien_te',m.tien_te,'noi_dung',p.noi_dung) "
                    "FROM kho.mua_doi_chieu_can_cu_thanh_phan m JOIN kho.mua_doi_chieu_can_cu_phien_ban p ON p.id=m.phien_ban_id "
                    "WHERE m.ty_le_khai IS NOT NULL ORDER BY m.id LIMIT 1")
        if cu is None:
            self.skipTest("NOT_VERIFIED: clone không có thành phần tỷ lệ được tạo trước M0033; không chèn giả lịch sử")
        self.assertEqual(cu["trang_thai"], "KHAI_BAO_THO_CHUA_SCALE")
        self.assertIsNone(cu["so_tien_khai"])
        self.assertIsNone(cu["tien_te"])
        self.assertTrue(any(t.get("ty_le_khai") == cu["ty_le_khai"] for t in cu["noi_dung"]["thanh_phan"]))

    def test_c17_hai_goc_canh_tranh_cung_hoa_don(self):
        self.can("rh", "a1b", "r1", "a3x")
        rh = self.s["rh"]
        goc_a = self.s["a1b"]["doi_chieu"]["doi_chieu_id"]
        giu = [r for r in self.tap_hien(goc_a) if r["kind"] != "HOA_DON"]
        self.dc.luu_doi_chieu(self.KT1, self.than(giu, self.xem_dc(giu), self.K("c17-a-bo-hd"),
                                               goc=goc_a, rev=self.cuoi(goc_a)["revision"]))
        refs, gocs = [], []
        for i in range(2):
            h = self.ho_so_seal(f"DC17{i}")
            r = self.ref_nt(self.nt_xac_nhan_03a(h))
            a = self.dc.luu_doi_chieu(self.KT1, self.than([r], self.xem_dc([r]), self.K(f"c17-goc-{i}")))
            refs.append([r, rh])
            gocs.append(a["doi_chieu"]["doi_chieu_id"])
        bodies = [self.than(rs, self.xem_dc(rs), self.K(f"c17-them-{i}"), goc=gocs[i], rev=1) for i, rs in enumerate(refs)]
        dcs = self.dich_vu_rieng(2)
        truoc = self.dem_tat_ca()
        kq, loi = self.song_song([lambda d=d, b=b: d.luu_doi_chieu(self.KT1, b) for d, b in zip(dcs, bodies)])
        self.assertEqual((len(kq), loi), (1, ["DC_HOA_DON_DA_GAN"]), (kq, loi))
        self.luu_rev(truoc, 2, tap=1)
        thang = kq[0]["doi_chieu"]["doi_chieu_id"]
        thua = next(g for g in gocs if g != thang)
        self.assertEqual((self.cuoi(thang)["revision"], self.cuoi(thua)["revision"]), (2, 1))
        # Gọi CSDL trực tiếp vẫn bị chặn; cùng gốc thì không. Không dựa guard Python.
        truoc = self.dem_tat_ca()
        self.assertEqual(self.chu_loi(("SELECT kho._dc_kiem_hd_da_gan(%s::jsonb,%s::uuid) AS r",
                                      (json.dumps([rh]), thua))), "DC_HOA_DON_DA_GAN")
        with self.svc._tx_review(self.svc.danh_tinh(self.KT1)) as c:
            self.svc._r1(c, "SELECT kho._dc_kiem_hd_da_gan(%s::jsonb,%s::uuid) AS r", (json.dumps([rh]), thang))
        self.doi_dc(truoc)

    def test_c18_snapshot_cu_khong_duoc_gan_hoa_don(self):
        self.can("rh")
        truoc = self.dem_tat_ca()
        with self.assertRaises(Exception) as cm:
            with self.svc._tx_review(self.svc.danh_tinh(self.KT1), rr=True) as c:
                self.svc._r1(c, "SELECT kho._dc_kiem_hd_da_gan(%s::jsonb,NULL::uuid) AS r", (json.dumps([self.s["rh"]]),))
        self.assertEqual(self.ma(cm.exception), "DC_GIAO_DICH_SAI")
        self.doi_dc(truoc)


if __name__ == "__main__":
    unittest.main()
