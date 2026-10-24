"""M4-03A — kiểm route HTTP Kế toán nghiệm thu (giao_dien/m4.py) + wrapper XayDungK2.kt_*. CODE_ONLY: coder viết, CHƯA CHẠY (WRITTEN_NOT_RUN).

Gọi THẬT `m4.dieu_huong` với handler/app giả (không socket, không PG, không server): chứng minh hợp đồng ROUTE — asset đúng một tệp, allowlist query/body,
authority 403, invalid 422, id sai dạng 404, kwargs đi nguyên vào service, header attachment/no-store, map mã DataError backend, backend chưa compose
→ 503 M4_KT_CHUA_NOI. Service backend ở đây là module GIẢ ghi lời gọi: CHỈ là bằng chứng route-contract, KHÔNG chứng minh backend/PG/GUI.

R01 tài sản /m4/m4_ke_toan.js: có tệp → 200 no-store đúng bytes; vắng → 404 NOT_FOUND; biến thể đường dẫn → 404.
R02 chưa compose: module m4.ke_toan_nghiem_thu vắng / thiếu lớp → 503 M4_KT_CHUA_NOI ở MỌI route KT; lỗi import KHÁC đi nguyên (không nuốt thành 503).
R03 query: danh sách không nhận tham số; chi tiết chỉ phong_bi_id một giá trị; PDF không tham số → 422 M4_YEU_CAU_SAI.
R04 đường dẫn: id không phải UUID thường / hoa / thừa đoạn → 404 (không gọi service).
R05 body: trường authority → 403 M4_CLIENT_AUTHORITY; trường lạ → 422 M4_YEU_CAU_SAI; body không phải JSON object → 422 INVALID_REQUEST.
R06 chuyển tiếp: kwargs đúng allowlist đi nguyên vào backend (danh tính từ phiên, không từ body); phản hồi no-store.
R07 PDF: attachment filename* UTF-8 + no-store, đúng bytes/media do backend trả.
R08 map lỗi backend: 403/404/409/503 theo bảng mã hiện có; mã chưa ghim → 400 (báo phụ thuộc trong docs/BAO-CAO-M4-03A-GUI.md).
I01 tích hợp producer THẬT → JS THẬT: chỉ chạy khi có env KHO_M4_03A_PRODUCER_BUNDLE (bundle M4_03A_KT_PRODUCER_BUNDLE_V1 do backend đã compose sinh)
    + node; thiếu → SkipTest NOT_VERIFIED (không tính là nghiệm thu).
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from kho_tri_thuc.giao_dien import m4 as M
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2.xay_dung import XayDungK2

TEN_MODULE = "kho_tri_thuc.m4.ke_toan_nghiem_thu"
PEND = "1a2b3c4d-0000-4000-8000-000000000001"
PB = "1a2b3c4d-0000-4000-8000-000000000002"
KTR = "1a2b3c4d-0000-4000-8000-000000000003"
SHA = "a" * 64
ACTOR = "kt_demo"
THAN_LUU = {"kt_pending_id": PEND, "phong_bi_id": PB, "expected_phong_bi_sha256": SHA, "expected_revision": 0, "gia_tri_nt_xac_nhan": "100",
            "tien_te": "VND", "co_so_gia_tri": "TRUOC_VAT", "tam_ung_xac_nhan": "0", "thu_hoi_xac_nhan": "0", "giu_lai_xac_nhan": "0",
            "vat_trang_thai": "KHONG_AP_DUNG", "vat_can_cu_tep_id": None, "vat_trich_dan": None, "ly_do": "không chịu VAT", "khoa": "m4kt-1"}
THAN_XN = {"kt_pending_id": PEND, "phong_bi_id": PB, "kt_revision_id": KTR, "expected_revision": 1, "expected_phong_bi_sha256": SHA, "khoa": "m4kt-2"}


class H:
    """Handler giả: đúng các thuộc tính dieu_huong dùng (crm_sid, json_body, headers, send_content)."""

    def __init__(self, body=None):
        self.body = body
        self.headers = {}
        self.sent = []

    def crm_sid(self):
        return "sid-kt"

    def json_body(self):
        if not isinstance(self.body, dict):
            raise ValueError("body không phải JSON object")
        return dict(self.body)

    def send_content(self, status, content, mime=None, headers=None):
        self.sent.append((status, content, mime, dict(headers or {})))

    @property
    def kq(self):
        assert len(self.sent) == 1, self.sent
        return self.sent[0]


class App:
    """App giả: mutation lock + phiên cố định + _crm_db gọi thẳng; service là XayDungK2 THẬT (wrapper kt_*) không kết nối."""

    def __init__(self):
        self.mutation_lock = threading.Lock()
        self.__dict__["_m4"] = object.__new__(XayDungK2)

    def crm_phien(self, sid, tao=False):
        return sid, ACTOR, False

    def _crm_db(self, fn, *a):
        return fn(*a)


class _ChanModule:
    """meta_path finder: mô phỏng module backend CHƯA compose (ModuleNotFoundError .name đúng) hoặc lỗi import phụ thuộc khác."""

    def __init__(self, ten_thieu):
        self.ten_thieu = ten_thieu

    def find_spec(self, name, path=None, target=None):
        if name == TEN_MODULE:
            raise ModuleNotFoundError("No module named " + repr(self.ten_thieu), name=self.ten_thieu)
        return None


class Nen(unittest.TestCase):
    def setUp(self):
        self.goi = []
        self._cu_mod = sys.modules.pop(TEN_MODULE, None)
        goi_pkg = importlib.import_module("kho_tri_thuc.m4")
        self._pkg = goi_pkg
        self._cu_attr = goi_pkg.__dict__.pop("ke_toan_nghiem_thu", None)
        self._finder = None
        p = patch.object(M, "_rieng", lambda app, svc, fn: app._crm_db(fn, svc))  # không mở kết nối riêng PG; vẫn qua đúng seam
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self._khoi_phuc)

    def _khoi_phuc(self):
        if self._finder is not None and self._finder in sys.meta_path:
            sys.meta_path.remove(self._finder)
        sys.modules.pop(TEN_MODULE, None)
        self._pkg.__dict__.pop("ke_toan_nghiem_thu", None)
        if self._cu_mod is not None:
            sys.modules[TEN_MODULE] = self._cu_mod
        if self._cu_attr is not None:
            self._pkg.ke_toan_nghiem_thu = self._cu_attr

    def chan(self, ten_thieu=TEN_MODULE):
        self._finder = _ChanModule(ten_thieu)
        sys.meta_path.insert(0, self._finder)

    def cai_backend(self, loi=None, co_lop=True):
        """Module backend GIẢ ghi lời gọi (route-contract only)."""
        goi, mod = self.goi, types.ModuleType(TEN_MODULE)

        class KeToanNghiemThuK2:
            def __init__(self, k2):
                assert isinstance(k2, XayDungK2)

            def _ghi(self, ten, *a, **kw):
                goi.append((ten, a, kw))
                if loi:
                    raise DataError(loi, "lỗi backend giả")
                return {"ten": ten}

            def danh_sach(self, dang_nhap):
                return self._ghi("danh_sach", dang_nhap)

            def xem(self, dang_nhap, **kw):
                return self._ghi("xem", dang_nhap, **kw)

            def tep_pdf(self, dang_nhap, **kw):
                self._ghi("tep_pdf", dang_nhap, **kw)
                return "Hồ sơ đợt 1.pdf", "application/pdf", b"%PDF-1.7 gia"

            def luu(self, dang_nhap, **kw):
                return self._ghi("luu", dang_nhap, **kw)

            def xac_nhan(self, dang_nhap, **kw):
                return self._ghi("xac_nhan", dang_nhap, **kw)

        if co_lop:
            mod.KeToanNghiemThuK2 = KeToanNghiemThuK2
        sys.modules[TEN_MODULE] = mod
        self._pkg.ke_toan_nghiem_thu = mod

    def goi_route(self, path, query=None, body=None, post=False):
        h = H(body)
        M.dieu_huong(h, App(), post, path, query or {})
        return h.kq

    def assertLoi(self, kq, status, ma):
        self.assertEqual((kq[0], kq[1].get("error")), (status, ma), kq)


ROUTE_GET = [("/api/m4/ke-toan", {}), ("/api/m4/ke-toan/" + PEND, {}), ("/api/m4/ke-toan/" + PEND, {"phong_bi_id": [PB]}),
             ("/api/m4/ke-toan/%s/phong-bi/%s/pdf" % (PEND, PB), {})]
ROUTE_POST = [("/api/m4/ke-toan/luu", THAN_LUU), ("/api/m4/ke-toan/xac-nhan", THAN_XN)]


class R01TaiSan(Nen):
    def test_co_tep_dung_bytes_no_store(self):
        st, raw, mime, hd = self.goi_route("/m4/m4_ke_toan.js")
        self.assertEqual(st, 200)
        self.assertEqual(raw, (M.ASSETS / "m4_ke_toan.js").read_bytes())
        self.assertEqual(mime, "text/javascript; charset=utf-8")
        self.assertEqual(hd.get("Cache-Control"), "no-store")

    def test_vang_404(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        with patch.object(M, "ASSETS", Path(d)):
            self.assertLoi(self.goi_route("/m4/m4_ke_toan.js"), 404, "NOT_FOUND")

    def test_bien_the_khong_200(self):
        for p in ("/m4/m4_ke_toan.JS", "/m4/./m4_ke_toan.js", "/m4/m4_ke_toan.js/", "/m4_ke_toan.js", "/m4/ke_toan_nghiem_thu.py"):
            with self.subTest(p=p):
                self.assertEqual(self.goi_route(p)[0], 404)


class R02ChuaCompose(Nen):
    def test_module_vang_503_moi_route(self):
        self.chan()
        for path, q in ROUTE_GET:
            with self.subTest(path=path, q=q):
                self.assertLoi(self.goi_route(path, q), 503, "M4_KT_CHUA_NOI")
        for path, body in ROUTE_POST:
            with self.subTest(path=path):
                self.assertLoi(self.goi_route(path, body=body, post=True), 503, "M4_KT_CHUA_NOI")

    def test_thieu_lop_503(self):
        self.cai_backend(co_lop=False)
        self.assertLoi(self.goi_route("/api/m4/ke-toan"), 503, "M4_KT_CHUA_NOI")
        self.assertEqual(self.goi, [])

    def test_loi_import_khac_khong_nuot(self):
        self.chan("psycopg_phu_thuoc_khac")
        with self.assertRaises(ModuleNotFoundError):
            self.goi_route("/api/m4/ke-toan")


class R03Query(Nen):
    def test_query_ngoai_pham_vi_422(self):
        self.cai_backend()
        ca = [("/api/m4/ke-toan", {"phong_bi_id": [PB]}), ("/api/m4/ke-toan", {"actor": ["x"]}),
              ("/api/m4/ke-toan/" + PEND, {"version_id": [PB]}), ("/api/m4/ke-toan/" + PEND, {"phong_bi_id": [PB, PB]}),
              ("/api/m4/ke-toan/" + PEND, {"kt_pending_id": [PEND]}), ("/api/m4/ke-toan/%s/phong-bi/%s/pdf" % (PEND, PB), {"phong_bi_id": [PB]})]
        for path, q in ca:
            with self.subTest(path=path, q=q):
                self.assertLoi(self.goi_route(path, q), 422, "M4_YEU_CAU_SAI")
        self.assertEqual(self.goi, [])


class R04DuongDan(Nen):
    def test_id_sai_dang_404(self):
        self.cai_backend()
        for p in ("/api/m4/ke-toan/abc", "/api/m4/ke-toan/" + PEND.upper(), "/api/m4/ke-toan/" + PEND + "/",
                  "/api/m4/ke-toan/%s/phong-bi/%s" % (PEND, PB), "/api/m4/ke-toan/%s/phong-bi/abc/pdf" % PEND,
                  "/api/m4/ke-toan/%s/phong-bi/%s/pdf/x" % (PEND, PB)):
            with self.subTest(p=p):
                self.assertEqual(self.goi_route(p)[0], 404)
        for p in ("/api/m4/ke-toan/luu/x", "/api/m4/ke-toan/" + PEND, "/api/m4/ke-toan/xac_nhan"):
            with self.subTest(post=p):
                self.assertLoi(self.goi_route(p, body=THAN_LUU, post=True), 404, "NOT_FOUND")
        self.assertEqual(self.goi, [])


class R05Body(Nen):
    def test_authority_403(self):
        self.cai_backend()
        for path, body in ROUTE_POST:
            for k in ("actor", "phap_nhan_id", "trang_thai", "quyen", "raw_sha256", "duyet"):
                with self.subTest(path=path, k=k):
                    self.assertLoi(self.goi_route(path, body={**body, k: "x"}, post=True), 403, "M4_CLIENT_AUTHORITY")
        self.assertEqual(self.goi, [])

    def test_truong_la_422(self):
        self.cai_backend()
        ca = [("/api/m4/ke-toan/luu", {**THAN_LUU, "kt_revision_id": KTR}), ("/api/m4/ke-toan/luu", {**THAN_LUU, "gia_tri_nt": "1"}),
              ("/api/m4/ke-toan/xac-nhan", {**THAN_XN, "gia_tri_nt_xac_nhan": "1"}), ("/api/m4/ke-toan/xac-nhan", {**THAN_XN, "vat_trang_thai": "CO_CAN_CU"}),
              ("/api/m4/ke-toan/xac-nhan", {**THAN_XN, "da_ghi_cong_no": True})]
        for path, body in ca:
            with self.subTest(path=path, body=sorted(body)):
                self.assertLoi(self.goi_route(path, body=body, post=True), 422, "M4_YEU_CAU_SAI")
        self.assertEqual(self.goi, [])

    def test_body_khong_phai_object_422(self):
        self.cai_backend()
        for path, _ in ROUTE_POST:
            for body in (None, [], "x"):
                with self.subTest(path=path, body=body):
                    self.assertLoi(self.goi_route(path, body=body, post=True), 422, "INVALID_REQUEST")
        self.assertEqual(self.goi, [])


class R06ChuyenTiep(Nen):
    def test_get_kwargs(self):
        self.cai_backend()
        for path, q, mong in [("/api/m4/ke-toan", {}, ("danh_sach", (ACTOR,), {})),
                              ("/api/m4/ke-toan/" + PEND, {}, ("xem", (ACTOR,), {"kt_pending_id": PEND, "phong_bi_id": None})),
                              ("/api/m4/ke-toan/" + PEND, {"phong_bi_id": [PB]}, ("xem", (ACTOR,), {"kt_pending_id": PEND, "phong_bi_id": PB}))]:
            self.goi.clear()
            with self.subTest(path=path, q=q):
                st, body, _, hd = self.goi_route(path, q)
                self.assertEqual((st, hd.get("Cache-Control")), (200, "no-store"))
                self.assertEqual(self.goi, [mong])
                self.assertEqual(body, {"ten": mong[0]})

    def test_post_kwargs_nguyen_ven(self):
        self.cai_backend()
        for (path, body), ten in zip(ROUTE_POST, ("luu", "xac_nhan")):
            self.goi.clear()
            with self.subTest(path=path):
                st, out, _, hd = self.goi_route(path, body=body, post=True)
                self.assertEqual((st, hd.get("Cache-Control"), out), (200, "no-store", {"ten": ten}))
                self.assertEqual(self.goi, [(ten, (ACTOR,), body)])  # null giữ nguyên null; không thêm/bớt khóa


class R07Pdf(Nen):
    def test_attachment_no_store(self):
        self.cai_backend()
        st, raw, mime, hd = self.goi_route("/api/m4/ke-toan/%s/phong-bi/%s/pdf" % (PEND, PB))
        self.assertEqual((st, raw, mime), (200, b"%PDF-1.7 gia", "application/pdf"))
        self.assertEqual(hd.get("Cache-Control"), "no-store")
        self.assertEqual(hd.get("Content-Disposition"), "attachment; filename*=UTF-8''H%E1%BB%93%20s%C6%A1%20%C4%91%E1%BB%A3t%201.pdf")
        self.assertEqual(self.goi, [("tep_pdf", (ACTOR,), {"kt_pending_id": PEND, "phong_bi_id": PB})])


class R08MapLoi(Nen):
    def test_ma_backend(self):
        for ma, st in (("M4_KHONG_CO_QUYEN_DU_AN", 403), ("NOT_FOUND", 404), ("M4_REVISION_CU", 409), ("M4_IDEMPOTENCY_KHAC", 409),
                       ("M4_DANG_XU_LY", 409), ("PG_KHONG_KET_NOI", 503), ("M4_CHUA_SAN_SANG_GHI_NGUON", 503), ("M4_KET_QUA_CHUA_RO", 503),
                       ("M4_THIEU_THONG_TIN", 422), ("M4_THAM_SO_SAI", 422), ("M4_KT_MA_CHUA_GHIM", 400)):
            self.goi.clear()
            self.cai_backend(loi=ma)
            for path, body in ROUTE_POST:
                with self.subTest(ma=ma, path=path):
                    self.assertLoi(self.goi_route(path, body=body, post=True), st, ma)
            with self.subTest(ma=ma, path="xem"):
                self.assertLoi(self.goi_route("/api/m4/ke-toan/" + PEND), st, ma)


ENV_BUNDLE = "KHO_M4_03A_PRODUCER_BUNDLE"


class I01ProducerJs(unittest.TestCase):
    """Producer Python THẬT (backend đã compose) → JS THẬT. Bundle do Root/backend sinh từ service thật sau compose; test này không tự dựng DTO."""

    def test_bundle_producer_qua_js(self):
        bundle = os.environ.get(ENV_BUNDLE)
        node = shutil.which("node")
        if not bundle or not node:
            raise unittest.SkipTest("NOT_VERIFIED: thiếu env %s (bundle M4_03A_KT_PRODUCER_BUNDLE_V1 sau compose) hoặc node — tích hợp producer→JS "
                                    "CHƯA được chứng minh" % ENV_BUNDLE)
        with open(bundle, encoding="utf-8") as f:
            self.assertEqual(json.load(f).get("schema"), "M4_03A_KT_PRODUCER_BUNDLE_V1")
        cjs = Path(__file__).resolve().parent / "m4_03a_async.cjs"
        r = subprocess.run([node, str(cjs), bundle], capture_output=True, text=True, encoding="utf-8", timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout[-4000:] + r.stderr[-2000:])
        self.assertIn("INTEGRATION_BUNDLE_CHECKED", r.stdout)
        self.assertNotIn("NOT_VERIFIED", r.stdout)


if __name__ == "__main__":
    unittest.main()
