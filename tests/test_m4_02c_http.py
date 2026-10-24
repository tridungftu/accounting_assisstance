"""M4-02C — kiểm HTTP thật route Duyệt & PDF trên LocalApp/LocalServer + clone DEMO sở hữu. CODE_ONLY: coder viết, CHƯA CHẠY (WRITTEN_NOT_RUN).

Cùng cổng clone với tests/test_m4_02c_pg.py (env KHO_M4_02C_CLONE_*; không env → SkipTest NOT_VERIFIED; cấu hình dở/clone không chứng minh được →
lỗi thiết lập TRƯỚC mọi ghi). KHÔNG tạo CSDL/role, KHÔNG migrate, KHÔNG seed CRM/M9: dùng login ứng dụng Root cấp (IN app_web) + DSN owner làm đường
tin cậy của factory máy chủ. Hồ sơ DEMO dựng bằng service (cùng DataRoot m4-k2 với máy chủ, engine #6 qua gate 02B) rồi MỌI thao tác duyệt đi qua HTTP
loopback cổng ngẫu nhiên, cùng token/cookie như trình duyệt. Không DROP/DELETE/TRUNCATE. Không thu hồi quyền (ca thu hồi ở test PG, chạy SAU tệp này
hoặc trên clone riêng). Không chứng minh trình duyệt/hiển thị (Root kiểm GUI riêng).

H01 tài sản: /m4/m4_duyet_pdf.js đúng MỘT route — có tệp UI head giao → 200 no-store đúng bytes; vắng → 404 (backend không tạo stub); biến thể đường dẫn
    không 200 (không static tổng quát).
H02 phiên/tham số: thiếu token → 403; query lạ/lặp → 400; id sai dạng → 400; đợt lạ → 404; trường authority (actor/trang_thai/duyet/sha256/vai) → 403;
    trường lạ → 400; tải PDF có query → 400.
H03 luồng: GET hồ sơ (no-store, DTO typed) → kết luận REVIEW (ACK typed, replay) → căn cứ cũ 409 → REVIEW/SOAN chấp thuận 403 → DUYET chấp thuận
    CHO_PDF (0 KT) → PDF hỏng/không phải PDF/sai media 400 (0 hàng) → PDF đúng → DA_SEAL + KT → tải đúng bytes (attachment, no-store) → kết luận lại 409.
H04 phạm vi: A2/B1 → 404 xem/tải/lệnh; XEM → 200 xem (quyền false), 403 lệnh + tải.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote, urlencode

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.kiem_chung import fixtures_m4 as F
from tests.test_m4_02c_pg import (A1, A2, B1, CO_ENV, DUYET, ENV_APP, ENV_CHU, LY_DO_SKIP, REVIEW, XEM, _q1, cau_hinh_clone, chuan_bi_duyet_vien,
                                  dung_ho_so, kiem_clone, than_ket_luan)
from tests.test_m4_review_http import CAU_HINH_FIXTURE


@unittest.skipUnless(CO_ENV, LY_DO_SKIP)
class M4DuyetHttp(unittest.TestCase):
    """Các ca chạy theo thứ tự tên h01…h04 trên MỘT clone/một máy chủ; trạng thái qua cls.s."""

    @classmethod
    def setUpClass(cls):
        import tests.test_m4_02b_k2 as K2B  # module (không import lớp TestCase của 02B)
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        cfg = cau_hinh_clone()
        cls.admin = psycopg.connect(cfg[ENV_CHU], autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        web0 = psycopg.connect(cfg[ENV_APP], autocommit=True)
        cls.addClassCleanup(web0.close)
        cls.gate = kiem_clone(cls.admin, web0, cfg)  # CHỈ ĐỌC — sai → lỗi thiết lập, chưa ghi gì
        cls.run_id = uuid.uuid4().hex[:8]
        cls.s = {}
        cls.env = patch.dict(os.environ, {LocalApp.CRM_ENV: cfg[ENV_APP], LocalApp.CRM_ENV_ADMIN: cfg[ENV_CHU], LocalApp.CRM_ENV_DB_KIEM_THU: "1"})
        cls.env.start()
        cls.addClassCleanup(cls.env.stop)
        tam = Path(tempfile.mkdtemp(prefix="ktt_m4_02c_http_"))  # giữ lại
        (tam / "cau_hinh_fixture.toml").write_text(CAU_HINH_FIXTURE, encoding="utf-8")
        cls.app = LocalApp(tam / "cau_hinh_fixture.toml", tam / "web")
        cls.server = LocalServer(cls.app, 0)
        cls.addClassCleanup(cls.server.server_close)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls._dung_server)  # chạy TRƯỚC server_close (LIFO)
        cls.seed = chuan_bi_duyet_vien(cls.admin)  # ghi đầu tiên — sau cổng
        # dựng hồ sơ (H03) cần engine #6 + lõi nguồn: chuẩn bị lười trong H03, ở đây chỉ ghi nhận khả năng
        from tests.test_m4_02b_pure import _docx, openpyxl
        cls.co_worker = K2B._nguon_da_nap() and openpyxl is not None and _docx is not None
        cls.cfg, cls.K2B, cls.XayDungK2 = cfg, K2B, XayDungK2

    @classmethod
    def _dung_server(cls):
        cls.server.shutdown()
        cls.thread.join(5)

    @classmethod
    def _builder(cls):
        """Service dựng hồ sơ: CÙNG DataRoot m4-k2 với máy chủ (app.root), engine #6 qua gate 02B (SkipTest NOT_READY nếu chưa sẵn sàng)."""
        if "svc" not in cls.s:
            cls.goc = cls.app.root
            cls.trich6, cls.gate6 = cls.K2B.M4ChungTuPG._gate_trich6.__func__(cls)
            web = psycopg.connect(cls.cfg[ENV_APP], autocommit=True, row_factory=dict_row)
            cls.addClassCleanup(web.close)
            chu = psycopg.connect(cls.cfg[ENV_CHU], autocommit=True, row_factory=dict_row)
            cls.addClassCleanup(chu.close)
            cls.s["svc"] = cls.XayDungK2(web, cls.app.root / "m4-k2", conn_tin_cay=chu, trich6=cls.trich6)
        return cls.s["svc"]

    # ------------------------------------------------------------------ helpers (cùng khung test_m4_02b_http)
    def goi(self, path, body=None, cookie=None, token=True, raw=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=1200)
        try:
            h = {"X-KTT-Token": self.app.token} if token else {}
            if cookie:
                h["Cookie"] = f"{self.app.CRM_COOKIE}={cookie}"
            h.update(headers or {})
            data = None
            if raw is not None:
                data = raw
            elif body is not None:
                h["Content-Type"] = "application/json"
                data = json.dumps(body).encode("utf-8")
            c.request("POST" if data is not None else "GET", path, body=data, headers=h)
            r = c.getresponse()
            out, ct, cd, cc = r.read(), r.getheader("Content-Type") or "", r.getheader("Content-Disposition"), r.getheader("Cache-Control")
        finally:
            c.close()
        return r.status, (json.loads(out or b"{}") if ct.startswith("application/json") else out), cd, cc

    def phien(self, login):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=60)
        try:
            c.request("GET", "/api/m4", headers={"X-KTT-Token": self.app.token})
            r = c.getresponse()
            r.read()
            sid = r.getheader("Set-Cookie").split(";", 1)[0].split("=", 1)[1]
        finally:
            c.close()
        st, b, _, _ = self.goi("/api/m4/danh-tinh", {"dang_nhap": login}, sid)
        self.assertEqual((st, b), (200, {"dang_nhap": login}))
        return sid

    def K(self, ten):
        return f"m4dyh-{self.run_id}-{ten}"

    def q(self, sql, params=()):
        return _q1(self.admin, sql, params)

    def xem(self, sid, **q):
        st, r, _, cc = self.goi("/api/m4/duyet?" + urlencode(q), cookie=sid)
        return st, r, cc

    def ok(self, path, body, sid):
        st, r, _, _ = self.goi(path, body, sid)
        self.assertEqual(st, 200, (path, r))
        return r

    def pdf(self, sid, raw, than, khoa, media="application/pdf"):
        info = quote(json.dumps({**than, "media_type": media, "khoa": self.K(khoa)}))
        st, r, _, cc = self.goi("/api/m4/duyet/pdf", cookie=sid, raw=raw, headers={"X-M4-Info": info, "Content-Type": "application/octet-stream"})
        return st, r, cc

    def dem_dot(self, dot):
        return {t: self.q(f"SELECT count(*) FROM m4.{t} WHERE dot_id = %s", (dot,))
                for t in ("duyet_ket_luan", "duyet_quyet_dinh", "duyet_pdf", "duyet_seal", "duyet_kt_cho", "duyet_kt_phong_bi")}

    # ------------------------------------------------------------------ H01
    def test_h01_tai_san(self):
        from kho_tri_thuc.giao_dien import m4 as M
        tep = M.ASSETS / "m4_duyet_pdf.js"
        st, js, _, cc = self.goi("/m4/m4_duyet_pdf.js", token=False)
        if tep.is_file():  # UI head đã giao — backend chỉ phục vụ đúng bytes
            self.assertEqual((st, cc, js), (200, "no-store", tep.read_bytes()))
        else:  # chưa giao — 404 có mã, không stub
            self.assertEqual((st, js.get("error")), (404, "NOT_FOUND"))
            self.assertFalse(tep.exists())
        for xau in ("/m4/m4-duyet-pdf.js", "/m4/m4_duyet_pdf.js/x", "/m4/../m4_duyet_pdf.js", "/m4/giao_dien/m4_duyet_pdf.js", "/m4/m4_duyet_pdf.css"):
            st, _, _, _ = self.goi(xau, token=False)
            self.assertNotEqual(st, 200, xau)

    # ------------------------------------------------------------------ H02
    def test_h02_phien_tham_so(self):
        sid = self.phien(A1)
        d, v, p = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        st, r, _, _ = self.goi("/api/m4/duyet?dot_id=" + d, cookie=sid, token=False)
        self.assertEqual((st, r.get("error")), (403, "SESSION_TOKEN"))
        for qs in (f"dot_id={d}&actor={A1}", f"dot_id={d}&dot_id={d}", f"dot_id={d}&trang_thai=DA_SEAL"):
            st, r, _, _ = self.goi("/api/m4/duyet?" + qs, cookie=sid)
            self.assertEqual((st, r.get("error")), (400, "M4_YEU_CAU_SAI"), qs)
        st, r, _ = self.xem(sid, dot_id="khong-phai-uuid")
        self.assertEqual((st, r.get("error")), (400, "M4_THAM_SO_SAI"))
        st, r, _ = self.xem(sid, dot_id=d)
        self.assertEqual((st, r.get("error")), (404, "M4_DUYET_KHONG_THAY"))
        st, r, _, _ = self.goi(f"/api/m4/duyet/{v}/pdf/{p}?raw_sha256=a", cookie=sid)
        self.assertEqual((st, r.get("error")), (400, "M4_YEU_CAU_SAI"))
        st, r, _, _ = self.goi(f"/api/m4/duyet/{v}/pdf/{p}", cookie=sid)
        self.assertEqual((st, r.get("error")), (404, "M4_DUYET_KHONG_THAY"))
        kl = {"dot_id": d, "version_id": v, "revision": 0, "expected_basis": "0" * 64, **F.KET_LUAN_VND, "dong_nt": [], "xu_ly_phat_hien": [],
              "ly_do": None, "khoa": self.K("auth")}
        for them in ({"actor": DUYET}, {"trang_thai": "DA_SEAL"}, {"duyet": True}, {"sha256": "a" * 64}, {"quyen": "DUYET"}):
            st, r, _, _ = self.goi("/api/m4/duyet/ket-luan", {**kl, **them}, sid)
            self.assertEqual((st, r.get("error")), (403, "M4_CLIENT_AUTHORITY"), them)
        st, r, _, _ = self.goi("/api/m4/duyet/ket-luan", {**kl, "de_xuat": "1"}, sid)
        self.assertEqual((st, r.get("error")), (400, "M4_YEU_CAU_SAI"))
        st, r, _, _ = self.goi("/api/m4/duyet/ket-luan", kl, sid)
        self.assertEqual((st, r.get("error")), (404, "M4_DUYET_KHONG_THAY"))
        st, r, _, _ = self.goi("/api/m4/duyet/ket-luan", {**kl, "gia_tri_nt": 35000000}, sid)  # số JS → từ chối, không đoán
        self.assertEqual((st, r.get("error")), (400, "M4_DUYET_SO_SAI"))
        than_pdf = {"dot_id": d, "version_id": v, "revision": 0, "expected_basis": "0" * 64, "ten": "x.pdf"}
        for them in ({"sha256": "a" * 64}, {"vai": "HO_SO_DOT_DA_DUYET"}, {"actor": A1}):
            info = quote(json.dumps({**than_pdf, "media_type": "application/pdf", "khoa": self.K("pdf-auth"), **them}))
            st, r, _, _ = self.goi("/api/m4/duyet/pdf", cookie=sid, raw=F.ho_so_dot_duyet_pdf(), headers={"X-M4-Info": info})
            self.assertEqual((st, r.get("error")), (403, "M4_CLIENT_AUTHORITY"), them)

    # ------------------------------------------------------------------ H03
    def test_h03_luong_duyet_pdf(self):
        if not self.co_worker:
            self.skipTest("NOT_RUN: lõi nguồn Review chưa nạp hoặc thiếu openpyxl/python-docx — không dựng được hồ sơ")
        h = dung_ho_so(self._builder(), self.admin, self.K, "H", self.run_id)
        dot = h["dot"]
        rv, du, a1 = self.phien(REVIEW), self.phien(DUYET), self.phien(A1)
        st, x, cc = self.xem(rv, dot_id=dot)
        self.assertEqual((st, cc, x["schema"], x["trang_thai"], x["chua_nop"]), (200, "no-store", "M4_DUYET_PDF_V1", "CHO_KET_LUAN", False))
        for k in ("can_cu", "review_refs", "phat_hien", "dong_nt", "lich_su", "phien_ban", "pdf_lich_su"):
            self.assertIsInstance(x[k], list, k)
        self.assertEqual(set(x["phien_ban"][0]) >= {"version_id", "so", "trang_thai", "moi_nhat"}, True)
        self.assertEqual(x["quyen"], {"xem": True, "ket_luan": True, "duyet": False, "tai_pdf": False, "phien_ban": False})
        than = {**than_ket_luan(x), "khoa": self.K("kl")}
        kl = self.ok("/api/m4/duyet/ket-luan", than, rv)
        self.assertEqual((kl["schema"], kl["hanh_dong"], kl["trang_thai"], kl["lap_lai"], kl["pdf_id"], kl["kt_pending_id"]),
                         ("M4_DUYET_PDF_V1", "KET_LUAN", "CHO_DUYET", False, None, None))
        self.assertTrue(isinstance(kl["receipt_id"], str) and isinstance(kl["ket_luan_id"], str) and isinstance(kl["ho_so"], dict))
        lai = self.ok("/api/m4/duyet/ket-luan", than, rv)
        self.assertEqual((lai["lap_lai"], lai["ket_luan_id"], lai["receipt_id"]), (True, kl["ket_luan_id"], kl["receipt_id"]))
        st, r, _, _ = self.goi("/api/m4/duyet/ket-luan", {**than, "revision": 1, "expected_basis": "e" * 64, "khoa": self.K("kl-cu")}, rv)
        self.assertEqual((st, r.get("error")), (409, "M4_DUYET_CO_SO_DOI"))
        st, x, _ = self.xem(du, dot_id=dot)
        c = x["context"]
        ct = {"dot_id": dot, "version_id": c["version_id"], "revision": c["revision"], "expected_basis": c["basis_sha256"],
              "ket_luan_id": kl["ket_luan_id"], "ly_do": "Chấp thuận DEMO"}
        for sid, ten in ((rv, "rv"), (a1, "a1")):
            st, r, _, _ = self.goi("/api/m4/duyet/chap-thuan", {**ct, "khoa": self.K("ct-" + ten)}, sid)
            self.assertEqual((st, r.get("error")), (403, "M4_DUYET_PHAM_VI"), ten)
        ack = self.ok("/api/m4/duyet/chap-thuan", {**ct, "khoa": self.K("ct")}, du)
        self.assertEqual((ack["trang_thai"], ack["seal_id"], ack["kt_pending_id"]), ("CHO_PDF", None, None))
        self.assertEqual(self.dem_dot(dot)["duyet_kt_cho"], 0)
        st, x, _ = self.xem(a1, dot_id=dot)
        c = x["context"]
        than_pdf = {"dot_id": dot, "version_id": c["version_id"], "revision": c["revision"], "expected_basis": c["basis_sha256"], "ten": "ho_so_da_duyet.pdf"}
        truoc = self.dem_dot(dot)
        for raw, media, ten in ((F.PDF_BI_CAT, "application/pdf", "cat"), (F.KHONG_PHAI_PDF, "application/pdf", "zip"),
                                (F.ho_so_dot_duyet_pdf(), "application/octet-stream", "media")):
            st, r, _ = self.pdf(a1, raw, than_pdf, "pdf-" + ten, media)
            self.assertEqual(st, 400, (ten, r))
        self.assertEqual(self.dem_dot(dot), truoc)
        raw = F.ho_so_dot_duyet_pdf("HTTP-1")
        st, p, cc = self.pdf(a1, raw, than_pdf, "pdf")
        self.assertEqual((st, cc), (200, "no-store"), p)
        self.assertEqual(p["trang_thai"], "DA_SEAL", p)
        self.assertTrue(isinstance(p["seal_id"], str) and isinstance(p["kt_pending_id"], str) and isinstance(p["pdf_id"], str))
        self.assertEqual({k: v for k, v in self.dem_dot(dot).items() if k in ("duyet_seal", "duyet_kt_cho", "duyet_kt_phong_bi")},
                         {"duyet_seal": 1, "duyet_kt_cho": 1, "duyet_kt_phong_bi": 1})
        url = f"/api/m4/duyet/{c['version_id']}/pdf/{p['pdf_id']}"
        for sid in (du, a1):
            st, b, cd, cc = self.goi(url, cookie=sid)
            self.assertEqual((st, hashlib.sha256(b).hexdigest(), cc), (200, hashlib.sha256(raw).hexdigest(), "no-store"))
            self.assertIn("attachment", cd or "")
        st, _, _, _ = self.goi(url, cookie=du, token=False)
        self.assertEqual(st, 403)
        st, x, _ = self.xem(du, dot_id=dot)
        self.assertEqual((x["trang_thai"], x["kt"]["trang_thai"], x["pdf"]["id"], x["pdf"]["name"]), ("DA_SEAL", "CHO_XAC_NHAN", p["pdf_id"], "ho_so_da_duyet.pdf"))
        st, r, _, _ = self.goi("/api/m4/duyet/ket-luan", {**than_ket_luan(x), "khoa": self.K("kl-sau")}, rv)
        self.assertEqual((st, r.get("error")), (409, "M4_DUYET_DA_CHAP_THUAN"))
        self.s.update(dot=dot, url=url, kl_than=than)

    # ------------------------------------------------------------------ H04
    def test_h04_pham_vi(self):
        if "dot" not in self.s:
            self.skipTest("H03 chưa dựng hồ sơ — NOT_RUN")
        dot, url = self.s["dot"], self.s["url"]
        truoc = self.dem_dot(dot)
        for login in (A2, B1):
            sid = self.phien(login)
            st, r, _ = self.xem(sid, dot_id=dot)
            self.assertEqual((st, r.get("error")), (404, "M4_DUYET_KHONG_THAY"), login)
            st, r, _, _ = self.goi(url, cookie=sid)
            self.assertEqual(st, 404, login)
            st, r, _, _ = self.goi("/api/m4/duyet/ket-luan", {**self.s["kl_than"], "khoa": self.K("ngoai-" + login)}, sid)
            self.assertEqual((st, r.get("error")), (404, "M4_DUYET_KHONG_THAY"), login)
        sid = self.phien(XEM)
        st, x, _ = self.xem(sid, dot_id=dot)
        self.assertEqual((st, x["quyen"]), (200, {"xem": True, "ket_luan": False, "duyet": False, "tai_pdf": False, "phien_ban": False}))
        st, r, _, _ = self.goi("/api/m4/duyet/ket-luan", {**self.s["kl_than"], "khoa": self.K("xem-kl")}, sid)
        self.assertEqual((st, r.get("error")), (403, "M4_DUYET_PHAM_VI"))
        st, r, _, _ = self.goi(url, cookie=sid)
        self.assertEqual((st, r.get("error")), (403, "M4_DUYET_PHAM_VI"))
        self.assertEqual(self.dem_dot(dot), truoc)


if __name__ == "__main__":
    unittest.main()
