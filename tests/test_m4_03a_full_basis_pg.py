"""M4-03A full basis — kiểm PostgreSQL THẬT: sửa metadata chứng từ sau seal, KHÔNG chạy lại L3 ⇒ producer M24 đánh L3 CU ⇒ nguồn KT HOLD.
CODE_ONLY: WRITTEN_NOT_RUN.

Cùng cổng/env/ràng buộc với tests/test_m4_03a_pg.py (KHO_M4_03A_*; không env → SkipTest NOT_VERIFIED, không phải PASS; clone/registry/quyền không
chứng minh được → LoiThietLap TRƯỚC mọi ghi). Thêm cổng CHỈ ĐỌC: đăng nhập DSN chủ bảng phải là ĐÚNG chủ m4.kt_xac_nhan theo session_user
(m4._kt_phien_chu) — không SET ROLE/thành viên; sai → SETUP_FAILURE (phụ thuộc triển khai, không nới). Mượn thuộc tính lớp gốc như graph3 (không import
lớp TestCase → 13 test gốc không chạy lại). Chỉ dùng KT1 (+ KT_KHAC chỉ đọc quyền); chạy trên clone mới hoặc TRƯỚC P99 của bộ gốc.

Producer THẬT, không INSERT giả duyệt/seal/đồ thị/revision, không monkeypatch readiness/SQL/engine/service:
FB01 hồ sơ F: seal → xem hiện hành → lưu NA đủ → xác nhận (baseline dương, chống always-HOLD).
FB02 hồ sơ E: seal A → lưu NA (quyen.xac_nhan=true) → chung_tu_sua THẬT đổi ngày một tệp của chính run A, CAS đúng, KHÔNG chạy lại → producer M24:
     L3 CU, run_id vẫn A, đồ thị ≠ đồ thị đã seal → KT HOLD (chi tiết/danh sách/lịch sử; owner: do_thi_hien_hanh=true nhưng co_so_hien_hanh=false
     ⇒ guard run/hash-only không đủ) → lưu/xác nhận khóa mới, phát lại đúng khóa, SQL qua _goi bị chặn; delta 0; hàng M24/KT + PDF A bất biến.
FB03 cầu nối: owner sau ghim — mẫu = chuỗi tính độc lập, danh tính đã khôi phục về KT; sửa từng trường/khoảng trắng → false; giao dịch cũ (kể cả
     chép lại chuỗi) → false; lệnh ghi không ghim / chép chứng thực cũ → CAN_KIEM_LAI; actor sai / danh tính người công bố / hình dạng sai → lỗi;
     login ứng dụng tự SET GUC đúng mẫu của chính phiên nó → vẫn không hiện hành, helper nội bộ → InsufficientPrivilege; login không vai KE_TOAN qua
     _goi → chặn ở kt_khoa, delta 0.
FB04 hồ sơ E tiếp: chạy lại L3 trên căn cứ mới (B) → vẫn HOLD; phiên bản kế tiếp chưa seal → HOLD; kết luận/duyệt/PDF ⇒ phong bì 2 hiện hành,
     lưu + xác nhận được; phong bì A chỉ lịch sử, PDF A giữ bytes, phát lại A vẫn bị chặn.
Chưa phủ (NOT_VERIFIED, ghi ở báo cáo): đồng thời sửa metadata ↔ lệnh KT (thứ tự khóa có kiểm soát), các đột biến căn cứ public khác (L2/ghép tay/HĐ/BOQ).
"""

from __future__ import annotations

import json
import unittest
import uuid

from tests import test_m4_03a_pg as P
from tests.test_m4_02c_pg import A1, _q1, chay_l3

from kho_tri_thuc.m4 import ke_toan_nghiem_thu as KT
from kho_tri_thuc.m4 import sql_ke_toan_nghiem_thu as SK

_G = vars(P.M4KeToanPG)  # descriptor gốc (hàm / staticmethod / classmethod) — không phải lớp TestCase
BANG_M24 = ("duyet_phien_ban", "duyet_ket_luan", "duyet_quyet_dinh", "duyet_pdf", "duyet_seal", "duyet_kt_cho", "duyet_kt_phong_bi", "kt_xac_nhan")
QUYEN_HOLD = {"xem": True, "luu": False, "xac_nhan": False, "tai_pdf": True}
LUU_SQL = "SELECT m4.kt_luu(%s, %s::jsonb, %s::uuid, %s::uuid, %s, %s::integer, %s::jsonb) AS r"
GHIM_SQL = "SELECT m4._kt_chung_thuc_ghi(%s::uuid, %s::uuid, %s::uuid, %s, %s) AS a"


@unittest.skipUnless(P.CO_ENV, P.LY_DO_SKIP)
class M4FullBasisPG(unittest.TestCase):
    """Chạy theo thứ tự fb01 → fb04 trên MỘT clone; trạng thái qua cls.s."""

    @classmethod
    def setUpClass(cls):
        _G["setUpClass"].__func__(cls)
        if _q1(cls.admin, "SELECT m4._kt_phien_chu()") is not True:
            raise P.LoiThietLap("SETUP_FAILURE: đăng nhập DSN chủ bảng không phải ĐÚNG chủ m4.kt_xac_nhan theo session_user (thành viên/SET ROLE không "
                                "được tính) — đường tin cậy không ghim được chứng thực; phụ thuộc triển khai, không nới")

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

    def m24(self, dot, version_id=None) -> dict:
        return self.svc.duyet_xem(A1, dot_id=dot, version_id=version_id)

    def l3_seal(self, ket_luan_id) -> str:
        return str(self.q("SELECT l3_run_id FROM m4.duyet_ket_luan WHERE id = %s", (ket_luan_id,)))

    def dt(self, login=None) -> dict:
        return self.svc.danh_tinh(login or self.KT1)

    @staticmethod
    def tham_luu(than) -> tuple:
        yc = {k: v for k, v in than.items() if k != "khoa"}
        return (than["khoa"], json.dumps(yc, ensure_ascii=False), than["kt_pending_id"], than["phong_bi_id"], than["expected_phong_bi_sha256"],
                than["expected_revision"], json.dumps({k: than[k] for k in KT.DU_LIEU}, ensure_ascii=False))

    def luu_sql(self, than, login=None):
        return self.kt._goi(self.dt(login), LUU_SQL, self.tham_luu(than), than["khoa"])

    def dong(self, cho) -> dict:
        return next(r for r in self.kt.danh_sach(self.KT1)["items"] if r["kt_pending_id"] == cho)

    def gia_mau(self, pid, txid, actor, pb) -> str:
        """Chuỗi chứng thực tính ĐỘC LẬP (owner, ngoài giao dịch đang xét) từ seal/kết luận của phong bì + pid/txid/actor cho trước — dùng làm oracle
        dương và làm bản giả mạo đúng hình dạng cho phiên ứng dụng."""
        return self.q("""SELECT jsonb_build_object('pid', %s::integer, 'txid', %s::bigint, 'actor', %s::text, 'kt_pending_id', c.id,
                                                   'dot_id', c.dot_id, 'hop_dong_id', c.hop_dong_id, 'phap_nhan_id', c.phap_nhan_id,
                                                   'du_an_id', c.du_an_id, 'version_id', b.phien_ban_id, 'phong_bi_id', b.id, 'seal_id', s.id,
                                                   'ket_luan_id', s.ket_luan_id, 'graph_sha256', s.graph_sha256,
                                                   'co_so_l3_sha256', k.graph->>'co_so_l3_sha256')::text
                         FROM m4.duyet_kt_phong_bi b JOIN m4.duyet_kt_cho c ON c.id = b.cho_id JOIN m4.duyet_seal s ON s.id = b.seal_id
                              JOIN m4.duyet_ket_luan k ON k.id = s.ket_luan_id
                         WHERE b.id = %s""", (pid, txid, actor, pb))

    def chu_hien_hanh(self, cho) -> dict:
        """Một giao dịch chủ bảng của KT1: khóa đọc → ghim producer (đường service thật) → m4._kt_hien_hanh."""
        d = self.dt()
        with self.svc._tx_review(d) as c:
            self.svc._r1(c, "SELECT m4._kt_khoa_doc(%s::uuid) AS q", (cho,))
            KT._ghim_do_thi(self.svc, c, d, cho)
            return self.svc._r1(c, "SELECT m4._kt_hien_hanh(%s::uuid) AS h", (cho,))["h"]

    def chu_loi(self, login, *cau):
        """Chạy các câu (sql, params) trong MỘT giao dịch chủ bảng của login — mong lỗi; giao dịch hủy."""
        def chay():
            with self.svc._tx_review(self.dt(login)) as c:
                for sql, p in cau:
                    self.svc._r1(c, sql, p)
        return self.loi(chay)

    def app_loi(self, sql, params=()):
        def chay():
            with self.svc._tx(self.dt()):
                self.svc._mot(sql, params)
        return self.loi(chay)

    # ------------------------------------------------------------------ FB01 baseline dương
    def test_fb01_baseline_seal_hien_hanh_xac_nhan(self):
        h = self.ho_so_seal("FBF")
        m = self.m24(h["dot"])
        self.assertEqual((m["do_thi"]["l3"]["trang_thai"], m["context"]["basis_sha256"]), ("CO", m["seal"]["graph_sha256"]))
        x = self.xem(h["cho"])
        self.assertEqual((x["can_cu_hien_hanh"], x["quyen"]["luu"]), (True, True))
        hh = self.chu_hien_hanh(h["cho"])
        self.assertEqual((hh["hien_hanh"], hh["do_thi_hien_hanh"], hh["co_so_hien_hanh"], hh["ly_do"]), (True, True, True, None))
        truoc = self.dem_tat_ca()
        than = self.than_luu(x, self.K("FBF-luu"), **self.du_day("KHONG_AP_DUNG", ly_do=P.LY_DO_NA))
        a = self.kt.luu(self.KT1, than)
        self.kiem_ack(a, khoa=than["khoa"], revision=1, trang_thai=KT.TT_CHO_XAC_NHAN, lap_lai=False, hanh_dong="LUU")
        self.ghi_mot(truoc)
        x = self.xem(h["cho"])
        self.assertEqual(x["quyen"], {"xem": True, "luu": True, "xac_nhan": True, "tai_pdf": True})
        self.assertEqual(self.dong(h["cho"])["trang_thai"], KT.TT_CHO_XAC_NHAN)
        truoc = self.dem_tat_ca()
        bx = self.than_xn(x, self.K("FBF-xn"))
        xn = self.kt.xac_nhan(self.KT1, bx)
        self.kiem_ack(xn, khoa=bx["khoa"], revision=2, trang_thai=SK.TT_DA_XAC_NHAN, lap_lai=False, hanh_dong="XAC_NHAN")
        self.ghi_mot(truoc)
        self.assertTrue(self.xem(h["cho"])["can_cu_hien_hanh"])
        self.s["F"] = {**h, "pb1": self.phong_bi(h["cho"])[0]}

    # ------------------------------------------------------------------ FB02 sửa metadata sau seal, không chạy lại ⇒ HOLD
    def test_fb02_sua_metadata_khong_chay_lai_hold(self):
        h = self.ho_so_seal("FBE")
        dot, cho = h["dot"], h["cho"]
        pb1 = self.phong_bi(cho)[0]
        m_a = self.m24(dot)
        l3_a = self.l3_seal(m_a["seal"]["ket_luan_id"])
        self.assertEqual((str(m_a["do_thi"]["l3"]["run_id"]), l3_a, m_a["do_thi"]["l3"]["trang_thai"]), (str(h["run"]), str(h["run"]), "CO"))
        self.assertEqual(m_a["context"]["basis_sha256"], m_a["seal"]["graph_sha256"])
        # dương TRƯỚC: hiện hành, lưu NA đủ, quyền xác nhận true
        x = self.xem(cho)
        self.kiem_xem(x, h, pb1)
        self.assertTrue(x["can_cu_hien_hanh"])
        truoc = self.dem_tat_ca()
        than1 = self.than_luu(x, self.K("FBE-luu-1"), **self.du_day("KHONG_AP_DUNG", ly_do=P.LY_DO_NA))
        a1 = self.kt.luu(self.KT1, than1)
        self.kiem_ack(a1, khoa=than1["khoa"], revision=1, trang_thai=KT.TT_CHO_XAC_NHAN, lap_lai=False, hanh_dong="LUU")
        self.ghi_mot(truoc)
        x_a = self.xem(cho)
        self.assertEqual((x_a["can_cu_hien_hanh"], x_a["quyen"]), (True, {"xem": True, "luu": True, "xac_nhan": True, "tai_pdf": True}))
        bx = self.than_xn(x_a, self.K("FBE-xn-1"))
        anh_a, db_a = self.anh(dot), self.kt_db(cho)
        n_run = self.q("SELECT count(*) FROM m4.chung_tu_run WHERE dot_id = %s", (dot,))

        # sửa metadata THẬT (lệnh public, SOAN, CAS đúng) trên CHÍNH run A — KHÔNG chạy lại L3
        cs = self.svc.chung_tu_ds(A1, dot_id=dot)["co_so"]
        self.svc.chung_tu_sua(A1, run_id=h["run"], revision=cs["revision"], tai_lieu=[{"tep_id": h["nt"], "ngay": "2026-03-07"}],
                              expected_basis=cs["basis_sha256"], ly_do="BB nghiệm thu ký 07/03 theo bản gốc (DEMO sau seal)", khoa=self.K("FBE-sua"))
        self.assertEqual(self.q("SELECT count(*) FROM m4.chung_tu_run WHERE dot_id = %s", (dot,)), n_run)  # không có lần chạy mới
        m_b = self.m24(dot)
        self.assertEqual(str(m_b["do_thi"]["l3"]["run_id"]), l3_a)  # run/kết quả công bố vẫn là A
        self.assertEqual(m_b["do_thi"]["l3"]["ket_qua_sha256"], m_a["do_thi"]["l3"]["ket_qua_sha256"])
        self.assertEqual(m_b["do_thi"]["l3"]["trang_thai"], "CU")  # producer M24 THẬT: căn cứ đổi sau lần công bố
        self.assertNotEqual(m_b["context"]["basis_sha256"], m_b["seal"]["graph_sha256"])
        self.assertEqual((m_b["context"]["version_id"], m_b["seal"]), (m_a["context"]["version_id"], m_a["seal"]))
        self.assertEqual(self.anh(dot), anh_a)  # seal/phong bì/PDF/kết luận/phiên bản/KT A không đổi

        # owner: guard L3 run/hash vẫn true — CHỈ căn cứ đầy đủ bắt được
        hh = self.chu_hien_hanh(cho)
        self.assertEqual((hh["hien_hanh"], hh["do_thi_hien_hanh"], hh["co_so_hien_hanh"], hh["ly_do"]), (False, True, False, SK.LY_DO_CO_SO))
        # đọc: HOLD, giữ ngữ cảnh/nguồn/lịch sử A
        x_b = self.xem(cho)
        self.kiem_xem(x_b, h, pb1)
        self.assertEqual((x_b["can_cu_hien_hanh"], x_b["quyen"]), (False, QUYEN_HOLD))
        self.assertEqual((x_b["context"], x_b["nguon"], x_b["kt"]), (x_a["context"], x_a["nguon"], x_a["kt"]))
        self.assertEqual([(r["thu_tu"], r["can_cu_hien_hanh"]) for r in x_b["lich_su"]["phong_bi"]], [(1, False)])
        self.assertEqual([(r["kt"]["revision"], r["context"]) for r in x_b["lich_su"]["kt"]], [(1, x_a["context"])])
        self.assertEqual(self.xem(cho, pb=pb1["id"])["context"], x_a["context"])
        self.assertEqual(self.kt.tep_pdf(self.KT1, cho, pb1["id"]), (h["ten_pdf"], "application/pdf", h["raw"]))
        row = self.dong(cho)
        self.assertEqual((row["phong_bi_id"], row["revision"], row["trang_thai"]), (pb1["id"], 1, KT.TT_CAN_KIEM_LAI))

        # ghi: lệnh mới / xác nhận / phát lại đúng khóa+body / SQL qua _goi — chặn dưới khóa, delta 0
        truoc = self.dem_tat_ca()
        self.assertEqual(self.loi(self.kt.luu, self.KT1, self.than_luu(x_a, self.K("FBE-luu-2"), **self.du_day("KHONG_AP_DUNG", ly_do=P.LY_DO_NA))),
                         "M4_KT_CAN_KIEM_LAI")
        self.assertEqual(self.loi(self.kt.xac_nhan, self.KT1, bx), "M4_KT_CAN_KIEM_LAI")
        self.assertEqual(self.loi(self.kt.luu, self.KT1, than1), "M4_KT_NGUON_CU")
        self.assertEqual(self.loi(self.luu_sql, self.than_luu(x_a, self.K("FBE-luu-sql"), **self.du_day("KHONG_AP_DUNG", ly_do=P.LY_DO_NA))),
                         "M4_KT_CAN_KIEM_LAI")
        self.doi(truoc)
        self.assertEqual((self.kt_db(cho), self.anh(dot)), (db_a, anh_a))
        self.assertEqual(self.kt.tep_pdf(self.KT1, cho, pb1["id"])[2], h["raw"])
        if "F" in self.s:  # sửa metadata đợt E không làm hồ sơ khác stale
            self.assertTrue(self.xem(self.s["F"]["cho"])["can_cu_hien_hanh"])
        self.s["E"] = {**h, "pb1": pb1, "x_a": x_a, "than1": than1}

    # ------------------------------------------------------------------ FB03 cầu nối chứng thực
    def test_fb03_cau_noi_chung_thuc(self):
        self.can("F")
        f = self.s["F"]
        cho, pb = f["cho"], f["pb1"]["id"]
        d = self.dt()
        v = str(self.q("SELECT id FROM m4.duyet_phien_ban WHERE dot_id = %s ORDER BY so DESC LIMIT 1", (f["dot"],)))
        cs_hh = "SELECT m4._kt_co_so_hien_hanh(%s::uuid) AS ok"

        # owner: ghim đường service thật → chuỗi = oracle độc lập; danh tính đã về KT; giả mạo từng trường → false; khôi phục → true
        with self.svc._tx_review(d) as c:
            self.svc._r1(c, "SELECT m4._kt_khoa_doc(%s::uuid) AS q", (cho,))
            KT._ghim_do_thi(self.svc, c, d, cho)
            r = self.svc._r1(c, f"""SELECT pg_backend_pid() AS pid, txid_current() AS tx, current_setting('{SK.GUC_CHUNG_THUC}') AS g,
                                           current_setting('ktt.nguoi_dung_id') AS nd, current_setting('ktt.nguoi_dung_dang_nhap') AS dn,
                                           m4._kt_co_so_hien_hanh(%s::uuid) AS ok""", (pb,))
            self.assertEqual((r["nd"], r["dn"], r["ok"]), (str(d["id"]), d["dang_nhap"], True))  # producer đã khôi phục danh tính KT
            self.assertEqual(r["g"], self.gia_mau(r["pid"], r["tx"], str(d["id"]), pb))
            sai = {"pid": r["pid"] + 1, "txid": r["tx"] + 1, "actor": str(uuid.uuid4()), "version_id": str(uuid.uuid4()),
                   "phong_bi_id": str(uuid.uuid4()), "dot_id": str(uuid.uuid4()), "graph_sha256": "0" * 64, "co_so_l3_sha256": "0" * 64}
            for k, gt in sai.items():
                self.svc._r1(c, f"SELECT set_config('{SK.GUC_CHUNG_THUC}', (%s::jsonb || jsonb_build_object(%s::text, %s::jsonb))::text, true) AS x",
                             (r["g"], k, json.dumps(gt)))
                self.assertIs(self.svc._r1(c, cs_hh, (pb,))["ok"], False, k)
            for gt in (" " + r["g"], r["g"].replace('", "', '","'), "{}", "không phải json"):
                self.svc._r1(c, f"SELECT set_config('{SK.GUC_CHUNG_THUC}', %s, true) AS x", (gt,))
                self.assertIs(self.svc._r1(c, cs_hh, (pb,))["ok"], False)
            self.svc._r1(c, f"SELECT set_config('{SK.GUC_CHUNG_THUC}', %s, true) AS x", (r["g"],))
            self.assertIs(self.svc._r1(c, cs_hh, (pb,))["ok"], True)  # đối chứng dương: chỉ đúng chuỗi mới mở
            if "E" in self.s:  # chứng thực của gốc F không mở phong bì gốc khác
                self.assertIs(self.svc._r1(c, cs_hh, (self.s["E"]["pb1"]["id"],))["ok"], False)
        g_cu = r["g"]

        # giao dịch mới: chứng thực cũ không mang sang; chép lại chuỗi cũ vẫn false (txid khác); không ghim → không hiện hành
        with self.svc._tx_review(d) as c:
            self.assertIn(self.svc._r1(c, f"SELECT current_setting('{SK.GUC_CHUNG_THUC}', true) AS g")["g"], (None, ""))
            self.assertIs(self.svc._r1(c, cs_hh, (pb,))["ok"], False)
            hh = self.svc._r1(c, "SELECT m4._kt_hien_hanh(%s::uuid) AS h", (cho,))["h"]
            self.assertEqual((hh["hien_hanh"], hh["do_thi_hien_hanh"], hh["co_so_hien_hanh"], hh["ly_do"]), (False, True, False, SK.LY_DO_CO_SO))
            self.svc._r1(c, f"SELECT set_config('{SK.GUC_CHUNG_THUC}', %s, true) AS x", (g_cu,))
            self.assertIs(self.svc._r1(c, cs_hh, (pb,))["ok"], False)

        # lệnh ghi trên đường chủ bảng KHÔNG ghim / chép chứng thực cũ → chặn; delta 0
        x = self.xem(cho)
        than = self.than_luu(x, self.K("FB03-khong-ghim"), **self.du_day("KHONG_AP_DUNG", ly_do=P.LY_DO_NA))
        khoa = ("SELECT m4.kt_khoa(%s::uuid, 'LUU') AS q", (cho,))
        truoc = self.dem_tat_ca()
        self.assertEqual(self.chu_loi(self.KT1, khoa, (LUU_SQL, self.tham_luu(than))), "M4_KT_CAN_KIEM_LAI")
        self.assertEqual(self.chu_loi(self.KT1, khoa, (f"SELECT set_config('{SK.GUC_CHUNG_THUC}', %s, true) AS x", (g_cu,)),
                                      (LUU_SQL, self.tham_luu(than))), "M4_KT_CAN_KIEM_LAI")
        # bên ghi: actor ≠ danh tính phiên; danh tính người công bố (không vai KE_TOAN); hình dạng sai
        self.assertEqual(self.chu_loi(self.KT1, (GHIM_SQL, (cho, str(uuid.uuid4()), v, "a" * 64, "b" * 64))), "M4_KT_DANH_TINH")
        pub = self.dt(A1)
        self.assertEqual(self.chu_loi(A1, (GHIM_SQL, (cho, str(d["id"]), v, "a" * 64, "b" * 64))), "M4_KT_DANH_TINH")
        self.assertIn(self.chu_loi(A1, (GHIM_SQL, (cho, str(pub["id"]), v, "a" * 64, "b" * 64))), ("M4_KT_PHAM_VI", "M4_KT_KHONG_THAY"))
        self.assertEqual(self.chu_loi(self.KT1, (GHIM_SQL, (cho, str(d["id"]), v, "x", "b" * 64))), "M4_THAM_SO_SAI")
        # login không vai KE_TOAN đi thẳng _goi: chặn ở kt_khoa (trước producer/chứng thực/biên nhận)
        self.assertIn(self.loi(self.luu_sql, {**than, "khoa": self.K("FB03-khac")}, self.KT_KHAC), ("M4_KT_PHAM_VI", "M4_KT_KHONG_THAY"))
        self.doi(truoc)

        # login ứng dụng: tự SET GUC đúng mẫu của CHÍNH phiên nó (pid/txid/actor thật) → vẫn không hiện hành; helper nội bộ không EXECUTE được
        with self.svc._tx(d):
            a = self.svc._mot("SELECT pg_backend_pid() AS pid, txid_current() AS tx")
            gia = self.gia_mau(a["pid"], a["tx"], str(d["id"]), pb)
            self.svc._mot(f"SELECT set_config('{SK.GUC_CHUNG_THUC}', %s, true) AS x", (gia,))
            self.assertEqual(self.svc._mot(f"SELECT current_setting('{SK.GUC_CHUNG_THUC}') AS g")["g"], gia)
            ct = self.svc._mot("SELECT m4.kt_chi_tiet(%s::uuid, NULL::uuid) AS ct", (cho,))["ct"]
            ds = self.svc._mot("SELECT m4.kt_danh_sach() AS ds")["ds"]
        self.assertIs(ct["can_cu_hien_hanh"], False)
        self.assertIs(next(r for r in ds if str(r["kt_pending_id"]) == cho)["hien_hanh"], False)
        for sql, p in (("SELECT m4._kt_phien_chu() AS x", ()), (cs_hh, (pb,)), ("SELECT m4._kt_hien_hanh(%s::uuid) AS x", (cho,)),
                       ("SELECT m4._kt_khoa_doc(%s::uuid) AS x", (cho,)), (GHIM_SQL, (cho, str(d["id"]), v, "a" * 64, "b" * 64)),
                       ("SELECT m4._kt_chung_thuc_mau(%s::uuid, %s::uuid, %s, %s) AS x", (pb, v, "a" * 64, "b" * 64))):
            self.assertEqual(self.app_loi(sql, p), "InsufficientPrivilege", sql)
        self.assertTrue(self.xem(cho)["can_cu_hien_hanh"])  # đường service thật vẫn dương sau mọi thử

    # ------------------------------------------------------------------ FB04 seal hợp lệ đời sau ⇒ hiện hành lại
    def test_fb04_seal_doi_sau_hien_hanh_lai(self):
        self.can("E")
        e = self.s["E"]
        dot, cho, pb1 = e["dot"], e["cho"], e["pb1"]
        run_b = str(chay_l3(self.svc, dot, self.K("FBE-l3-b"), cha=e["run"]))  # công bố L3 trên căn cứ đã sửa
        m = self.m24(dot)
        self.assertEqual((str(m["do_thi"]["l3"]["run_id"]), m["do_thi"]["l3"]["trang_thai"]), (run_b, "CO"))
        self.assertEqual((self.xem(cho)["can_cu_hien_hanh"], self.dong(cho)["trang_thai"]), (False, KT.TT_CAN_KIEM_LAI))  # A vẫn không hiện hành
        c = m["context"]
        v2 = self.svc.duyet_phien_ban(A1, dot_id=dot, parent_version_id=e["v1"], revision=c["revision"], expected_basis=c["basis_sha256"],
                                      ly_do="Đính chính sau khi sửa metadata chứng từ (DEMO)", khoa=self.K("FBE-pb2"))["phien_ban_id"]
        c = self.m24(dot, v2)["context"]
        self.svc.duyet_phien_ban_nop(A1, dot_id=dot, version_id=v2, revision=0, expected_basis=c["basis_sha256"], khoa=self.K("FBE-nop2"))
        x = self.xem(cho)  # kế tiếp chưa seal: vẫn HOLD, không phong bì giả
        self.assertEqual((x["can_cu_hien_hanh"], x["quyen"], len(self.phong_bi(cho))), (False, QUYEN_HOLD, 1))
        self.ket_luan(dot, "FBE-kl-v2")
        self.assertEqual(self.chap_thuan(dot, "FBE-ct-v2")["trang_thai"], "CHO_PDF")
        raw2 = P.F.ho_so_dot_duyet_pdf(f"KT-{self.run_id}-FBE-dinh-chinh")
        p2 = self.pdf(dot, raw2, "FBE-pdf-v2", "ho_so_da_duyet_FBE_v2.pdf")
        self.assertEqual((p2["trang_thai"], str(p2["kt_pending_id"])), ("DA_SEAL", cho))
        m = self.m24(dot)
        self.assertEqual(m["context"]["basis_sha256"], m["seal"]["graph_sha256"])
        pbs = self.phong_bi(cho)
        self.assertEqual([(p["thu_tu"], p["truoc_id"]) for p in pbs], [(1, None), (2, pb1["id"])])
        hh = self.chu_hien_hanh(cho)
        self.assertEqual((hh["hien_hanh"], hh["co_so_hien_hanh"], hh["phong_bi_id"]), (True, True, pbs[1]["id"]))
        x = self.xem(cho)
        self.kiem_xem(x, e, pbs[1])
        self.assertEqual((x["can_cu_hien_hanh"], x["quyen"], x["kt"]), (True, {"xem": True, "luu": True, "xac_nhan": False, "tai_pdf": True}, None))
        self.assertEqual([(r["thu_tu"], r["can_cu_hien_hanh"]) for r in x["lich_su"]["phong_bi"]], [(1, False), (2, True)])
        xa = self.xem(cho, pb=pb1["id"])
        self.assertEqual((xa["context"], xa["can_cu_hien_hanh"], xa["quyen"]), (e["x_a"]["context"], False, QUYEN_HOLD))
        self.assertEqual(self.kt.tep_pdf(self.KT1, cho, pb1["id"])[2], e["raw"])  # PDF lịch sử A giữ bytes
        truoc = self.dem_tat_ca()
        self.assertEqual(self.loi(self.kt.luu, self.KT1, e["than1"]), "M4_KT_NGUON_CU")  # phát lại nguồn A vẫn bị chặn
        self.doi(truoc)
        than = self.than_luu(x, self.K("FBE-luu-v2"), **self.du_day("KHONG_AP_DUNG", ly_do=P.LY_DO_NA))
        self.assertEqual(than["expected_revision"], 0)
        a = self.kt.luu(self.KT1, than)
        self.kiem_ack(a, khoa=than["khoa"], revision=2, trang_thai=KT.TT_CHO_XAC_NHAN, lap_lai=False, hanh_dong="LUU")
        self.ghi_mot(truoc)
        self.assertEqual(a["context"]["phong_bi_id"], pbs[1]["id"])
        x = self.xem(cho)
        self.assertEqual(x["quyen"]["xac_nhan"], True)
        truoc = self.dem_tat_ca()
        bx = self.than_xn(x, self.K("FBE-xn-v2"))
        xn = self.kt.xac_nhan(self.KT1, bx)
        self.kiem_ack(xn, khoa=bx["khoa"], revision=3, trang_thai=SK.TT_DA_XAC_NHAN, lap_lai=False, hanh_dong="XAC_NHAN")
        self.ghi_mot(truoc)
        row = self.dong(cho)
        self.assertEqual((row["phong_bi_id"], row["revision"], row["trang_thai"]), (pbs[1]["id"], 3, SK.TT_DA_XAC_NHAN))


if __name__ == "__main__":
    unittest.main()
