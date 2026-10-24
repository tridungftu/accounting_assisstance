"""M4-03A GUI FIX01 — ma trận mã HTTP KT trên `m4.dieu_huong` THẬT. CODE_ONLY: coder viết, CHƯA CHẠY (WRITTEN_NOT_RUN).

Stub backend CHỈ phát DataError (module giả `kho_tri_thuc.m4.ke_toan_nghiem_thu` nạp qua wrapper XayDungK2._kt thật) — bằng chứng map route, KHÔNG phải
backend thật/PG/native browser. Nguồn mã: docs/M4-03A-GUI-FIX01-BACKEND-REFERENCE.py:68–76 (đọc, không import).

X01 mã miền KT (M4_KT_*) → đúng 403/404/409/422/500 trên MỌI route KT (danh sách, chi tiết, chi tiết lịch sử, PDF, lưu, xác nhận).
X02 M4_KT_SAI_DTO 500: thông điệp cố định, không lộ chi tiết nội bộ của backend.
X03 mã chung giữ bảng toàn cục trên route KT (không chép mù gợi ý backend): M4_CLIENT_AUTHORITY/M4_CHI_MAY_CHU_NGUON 403, M4_IDEMPOTENCY_KHAC 409,
    M4_CHUA_SAN_SANG_GHI_NGUON/M4_KET_QUA_CHUA_RO 503, invalid KT 422; mã lạ giữ 400.
X04 mã KT KHÔNG áp ngoài route KT (route duyệt phát M4_KT_PHAM_VI → 400 như mã lạ).
X05 authority query/body/phiên giữ nguyên: trường authority 403, trường lạ 422, query lạ 422, danh tính từ phiên (không từ body).
"""

from __future__ import annotations

import importlib
import sys
import threading
import types
import unittest
from unittest.mock import patch

from kho_tri_thuc.giao_dien import m4 as M
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2.xay_dung import XayDungK2

TEN_MODULE = "kho_tri_thuc.m4.ke_toan_nghiem_thu"
PEND = "2b3c4d5e-0000-4000-8000-000000000001"
PB = "2b3c4d5e-0000-4000-8000-000000000002"
KTR = "2b3c4d5e-0000-4000-8000-000000000003"
SHA = "b" * 64
ACTOR = "kt_fix01"
THAN_LUU = {"kt_pending_id": PEND, "phong_bi_id": PB, "expected_phong_bi_sha256": SHA, "expected_revision": 1, "gia_tri_nt_xac_nhan": "100",
            "tien_te": "VND", "co_so_gia_tri": "TRUOC_VAT", "tam_ung_xac_nhan": None, "thu_hoi_xac_nhan": "0", "giu_lai_xac_nhan": None,
            "vat_trang_thai": "KHONG_AP_DUNG", "vat_can_cu_tep_id": None, "vat_trich_dan": None, "ly_do": "không chịu VAT", "khoa": "m4kt-f1"}
THAN_XN = {"kt_pending_id": PEND, "phong_bi_id": PB, "kt_revision_id": KTR, "expected_revision": 1, "expected_phong_bi_sha256": SHA, "khoa": "m4kt-f2"}
ROUTES = [("GET", "/api/m4/ke-toan", {}, None), ("GET", "/api/m4/ke-toan/" + PEND, {}, None),
          ("GET", "/api/m4/ke-toan/" + PEND, {"phong_bi_id": [PB]}, None), ("GET", "/api/m4/ke-toan/%s/phong-bi/%s/pdf" % (PEND, PB), {}, None),
          ("POST", "/api/m4/ke-toan/luu", {}, THAN_LUU), ("POST", "/api/m4/ke-toan/xac-nhan", {}, THAN_XN)]
MA_KT = {"M4_KT_PHAM_VI": 403, "M4_KT_KHONG_THAY": 404,
         "M4_KT_NGUON_CU": 409, "M4_KT_NGUON_DOI": 409, "M4_KT_CAN_KIEM_LAI": 409, "M4_KT_REVISION_CU": 409, "M4_KT_DA_XAC_NHAN": 409,
         "M4_KT_CHO_BO_SUNG": 409, "M4_KT_XAC_NHAN_KHAC_NHAP": 409, "M4_KT_NGUON_HONG": 409,
         "M4_KT_SO_SAI": 422, "M4_KT_TRUONG_SAI": 422, "M4_KT_VAT_SAI": 422, "M4_KT_CO_SO_SAI": 422, "M4_KT_TIEN_TE_KHAC": 422,
         "M4_KT_CAN_CU_VAT_SAI": 422, "M4_KT_SAI_DTO": 500}
MA_CHUNG = {"M4_CLIENT_AUTHORITY": 403, "M4_CHI_MAY_CHU_NGUON": 403, "M4_IDEMPOTENCY_KHAC": 409, "M4_CHUA_SAN_SANG_GHI_NGUON": 503,
            "M4_KET_QUA_CHUA_RO": 503, "M4_KT_CHUA_NOI": 503, "M4_YEU_CAU_SAI": 422, "M4_THAM_SO_SAI": 422, "M4_KHOA_THAO_TAC": 422,
            "M4_KT_MA_LA_FIX01": 400}
CHI_TIET_NOI_BO = "chi tiết nội bộ backend: relation m4.kt_x / password=SECRET"


class H:
    def __init__(self, body=None):
        self.body, self.headers, self.sent = body, {}, []

    def crm_sid(self):
        return "sid-fix01"

    def json_body(self):
        if not isinstance(self.body, dict):
            raise ValueError("body không phải JSON object")
        return dict(self.body)

    def send_content(self, status, content, mime=None, headers=None):
        self.sent.append((status, content, mime, dict(headers or {})))


class App:
    def __init__(self):
        self.mutation_lock = threading.Lock()
        self.__dict__["_m4"] = object.__new__(XayDungK2)

    def crm_phien(self, sid, tao=False):
        return sid, ACTOR, False

    def _crm_db(self, fn, *a):
        return fn(*a)


class Nen(unittest.TestCase):
    def setUp(self):
        self.goi = []
        self._pkg = importlib.import_module("kho_tri_thuc.m4")
        self._cu_mod = sys.modules.pop(TEN_MODULE, None)
        self._cu_attr = self._pkg.__dict__.pop("ke_toan_nghiem_thu", None)
        p = patch.object(M, "_rieng", lambda app, svc, fn: app._crm_db(fn, svc))  # không mở kết nối PG riêng; vẫn qua đúng seam
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self._khoi_phuc)

    def _khoi_phuc(self):
        sys.modules.pop(TEN_MODULE, None)
        self._pkg.__dict__.pop("ke_toan_nghiem_thu", None)
        if self._cu_mod is not None:
            sys.modules[TEN_MODULE] = self._cu_mod
        if self._cu_attr is not None:
            self._pkg.ke_toan_nghiem_thu = self._cu_attr

    def stub(self, ma=None, msg=CHI_TIET_NOI_BO):
        """Stub CHỈ phát DataError(ma) (hoặc ghi lời gọi khi ma=None) — không dữ liệu/DTO nào."""
        goi, mod = self.goi, types.ModuleType(TEN_MODULE)

        class KeToanNghiemThuK2:
            def __init__(self, k2):
                assert isinstance(k2, XayDungK2)

            def _p(self, ten, dang_nhap, **kw):
                goi.append((ten, dang_nhap, kw))
                if ma:
                    raise DataError(ma, msg)
                return ("x.pdf", "application/pdf", b"%PDF") if ten == "tep_pdf" else {"ok": ten}

            def danh_sach(self, dang_nhap):
                return self._p("danh_sach", dang_nhap)

            def xem(self, dang_nhap, **kw):
                return self._p("xem", dang_nhap, **kw)

            def tep_pdf(self, dang_nhap, **kw):
                return self._p("tep_pdf", dang_nhap, **kw)

            def luu(self, dang_nhap, **kw):
                return self._p("luu", dang_nhap, **kw)

            def xac_nhan(self, dang_nhap, **kw):
                return self._p("xac_nhan", dang_nhap, **kw)

        mod.KeToanNghiemThuK2 = KeToanNghiemThuK2
        sys.modules[TEN_MODULE] = mod
        self._pkg.ke_toan_nghiem_thu = mod

    def route(self, method, path, query=None, body=None):
        h = H(body)
        M.dieu_huong(h, App(), method == "POST", path, query or {})
        self.assertEqual(len(h.sent), 1, h.sent)
        return h.sent[0]


class X01MaKt(Nen):
    def test_ma_tran_moi_route(self):
        for ma, st in MA_KT.items():
            self.stub(ma)
            for method, path, q, body in ROUTES:
                with self.subTest(ma=ma, route=(method, path, tuple(q))):
                    kq = self.route(method, path, q, body)
                    self.assertEqual((kq[0], kq[1].get("error")), (st, ma), kq)

    def test_bang_ma_dung_tham_chieu(self):
        self.assertEqual(M.MA_KT, MA_KT)  # đúng tập mã + status của handoff FIX01 (không thêm/bớt)


class X02SaiDto(Nen):
    def test_500_khong_lo_chi_tiet(self):
        self.stub("M4_KT_SAI_DTO")
        for method, path, q, body in ROUTES:
            with self.subTest(route=(method, path)):
                st, out, _, _ = self.route(method, path, q, body)
                self.assertEqual(st, 500)
                self.assertEqual(out["message"], M.KT_SAI_DTO_MSG)
                self.assertNotIn("SECRET", out["message"])
                self.assertNotIn("relation", out["message"])

    def test_4xx_giu_thong_diep_nghiep_vu(self):
        self.stub("M4_KT_REVISION_CU", "Revision KT đã đổi — tải lại.")
        st, out, _, _ = self.route("POST", "/api/m4/ke-toan/luu", body=THAN_LUU)
        self.assertEqual((st, out["message"]), (409, "Revision KT đã đổi — tải lại."))


class X03MaChung(Nen):
    def test_ma_chung_giu_bang_toan_cuc(self):
        for ma, st in MA_CHUNG.items():
            self.stub(ma)
            for method, path, q, body in ROUTES:
                with self.subTest(ma=ma, route=(method, path, tuple(q))):
                    kq = self.route(method, path, q, body)
                    self.assertEqual((kq[0], kq[1].get("error")), (st, ma), kq)


class X04NgoaiRouteKt(Nen):
    def test_ma_kt_khong_ap_ngoai_route_kt(self):
        def nem(self_, me, **kw):
            raise DataError("M4_KT_PHAM_VI", "x")
        with patch.object(XayDungK2, "duyet_xem", nem, create=True):
            st, out, _, _ = self.route("GET", "/api/m4/duyet", {"dot_id": [PEND]})
        self.assertEqual((st, out["error"]), (400, "M4_KT_PHAM_VI"))


class X05Authority(Nen):
    def test_body_query_phien(self):
        self.stub()
        for path, body in (("/api/m4/ke-toan/luu", THAN_LUU), ("/api/m4/ke-toan/xac-nhan", THAN_XN)):
            for k in ("actor", "phap_nhan_id", "trang_thai", "quyen"):
                with self.subTest(path=path, k=k):
                    kq = self.route("POST", path, body={**body, k: "x"})
                    self.assertEqual((kq[0], kq[1]["error"]), (403, "M4_CLIENT_AUTHORITY"))
            with self.subTest(path=path, k="la"):
                kq = self.route("POST", path, body={**body, "truong_la": 1})
                self.assertEqual((kq[0], kq[1]["error"]), (422, "M4_YEU_CAU_SAI"))
        for path, q in (("/api/m4/ke-toan", {"dang_nhap": ["x"]}), ("/api/m4/ke-toan/" + PEND, {"phong_bi_id": [PB, PB]})):
            with self.subTest(path=path, q=q):
                kq = self.route("GET", path, q)
                self.assertEqual((kq[0], kq[1]["error"]), (422, "M4_YEU_CAU_SAI"))
        self.assertEqual(self.goi, [])
        self.route("POST", "/api/m4/ke-toan/xac-nhan", body=THAN_XN)
        self.assertEqual(self.goi, [("xac_nhan", ACTOR, THAN_XN)])  # danh tính từ phiên; body đi nguyên đúng allowlist


if __name__ == "__main__":
    unittest.main()
