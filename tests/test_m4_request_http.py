"""M4-04A — kiểm HTTP thật route /api/m4-request trên LocalApp + máy chủ loopback RIÊNG của test + clone DEMO sở hữu. CODE_ONLY: CHƯA CHẠY.

Route này CHƯA nối vào `server.Handler.handle_route` (gói đăng ký/wire sau). Test dựng `HandlerThu`/`MayChuThu` (lớp con TEST_ONLY): CHỈ đường dẫn
`/api/m4-request*` đi vào `giao_dien.m4_request.dieu_huong` sau cùng `authorize(private=True)`; mọi đường khác (cấp cookie GET /api/m4, chọn danh tính
POST /api/m4/danh-tinh) đi qua Handler gốc — phiên dùng chung THẬT (cookie HttpOnly + X-KTT-Token). Request là `FakeRequest` tiêm qua seam máy chủ
`app._m4_request` (không mạng). Cùng cổng clone với tests/test_m4_request_pg.py (env KHO_M4_04A_CLONE_*; không env → SkipTest NOT_VERIFIED; dở dang /
không chứng minh được → lỗi thiết lập trước mọi ghi). Cổng đòi clone CHƯA có mapping/intent → chạy trên clone riêng (hoặc trước test PG).
KHÔNG tạo CSDL/role, KHÔNG migrate/bootstrap/M9/SET ROLE, KHÔNG DROP/DELETE/TRUNCATE, không dọn dẹp. Không chứng minh GUI/trình duyệt.

H01 cổng/tham số: thiếu token → 403; thiếu phiên → 400 CRM_PHIEN; query lạ → 400; authority (nguoiTao/so_tien/endpoint/pdf…) → 403; trường lạ → 400;
    id sai dạng → 400; thân quá lớn → 413; route lạ (gửi/duyệt/xóa) → 404.
H02 luồng: chưa cấu hình → 503 CHUA_CAU_HINH có cấu trúc, 0 hàng; mapping + seam → mất ACK tạo → 200 CHUA_RO_TAO (quan sát được); đối soát mà trình
    duyệt timeout (fake POST chậm) → TimeoutError phía client, máy chủ vẫn hoàn tất; GET xem thấy dang_xu_ly rồi CHO_QUET; phát lại đúng khóa → 200
    lap_lai, 0 POST mới; clean → DA_DOI_SOAT; một Request, một tệp; DTO không lộ canonical/người đứng tên/khóa.
H03 phạm vi: XEM → 403 M4_REQUEST_PHAM_VI; B1 → 404 xem/lệnh; lệnh đang chạy → 409 M4_REQUEST_DANG_XU_LY.
"""

from __future__ import annotations

import http.client
import json
import os
import tempfile
import threading
import time
import unittest
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang.primitives import DataError
from tests.test_m4_02c_pg import A1, B1, XEM, _q1, chuan_bi_duyet_vien
from tests.test_m4_request_pg import (BANG, CO_ENV, ENV_APP, ENV_CHU, LY_DO_SKIP, cau_hinh_clone, cau_hinh_pg, dat_anh_xa, dung_seal,
                                      kiem_clone_request)
from tests.test_m4_request_tinh import DongHo, FakeRequest
from tests.test_m4_review_http import CAU_HINH_FIXTURE

TIEN_TO = "/api/m4-request"


def _lop_may_chu():
    """Lớp con TEST_ONLY của Handler/LocalServer: chỉ thêm định tuyến /api/m4-request* (KHÔNG sửa server.py)."""
    from kho_tri_thuc.giao_dien import m4_request as W
    from kho_tri_thuc.giao_dien.server import Handler, LocalServer

    class HandlerThu(Handler):
        def handle_route(self, post):
            path = urlsplit(self.path).path
            if path != TIEN_TO and not path.startswith(TIEN_TO + "/"):
                return super().handle_route(post)
            try:
                self.authorize(private=True)
            except DataError as exc:
                return self.send_content(403, {"error": exc.code, "message": str(exc)})
            return W.dieu_huong(self, self.server.app, post, path, parse_qs(urlsplit(self.path).query, keep_blank_values=True))

    class MayChuThu(LocalServer):
        def __init__(self, app, port=0):
            self.app = app
            ThreadingHTTPServer.__init__(self, ("127.0.0.1", port), HandlerThu)

    return MayChuThu


@unittest.skipUnless(CO_ENV, LY_DO_SKIP)
class M4RequestHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tests.test_m4_02b_k2 as K2B
        from kho_tri_thuc.giao_dien.server import LocalApp
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        cfg = cau_hinh_clone()
        cls.cfg = cfg
        cls.admin = psycopg.connect(cfg[ENV_CHU], autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        web0 = psycopg.connect(cfg[ENV_APP], autocommit=True)
        cls.addClassCleanup(web0.close)
        cls.gate = kiem_clone_request(cls.admin, web0, cfg)  # CHỈ ĐỌC
        cls.run_id = uuid.uuid4().hex[:8]
        cls.s = {}
        cls.env = patch.dict(os.environ, {LocalApp.CRM_ENV: cfg[ENV_APP], LocalApp.CRM_ENV_ADMIN: cfg[ENV_CHU], LocalApp.CRM_ENV_DB_KIEM_THU: "1"})
        cls.env.start()
        cls.addClassCleanup(cls.env.stop)
        tam = Path(tempfile.mkdtemp(prefix="ktt_m4_04a_http_"))  # giữ lại
        (tam / "cau_hinh_fixture.toml").write_text(CAU_HINH_FIXTURE, encoding="utf-8")
        cls.app = LocalApp(tam / "cau_hinh_fixture.toml", tam / "web")
        cls.server = _lop_may_chu()(cls.app, 0)
        cls.addClassCleanup(cls.server.server_close)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls._dung_server)
        cls.seed = chuan_bi_duyet_vien(cls.admin)  # ghi đầu tiên — sau cổng
        from tests.test_m4_02b_pure import _docx, openpyxl
        cls.co_worker = K2B._nguon_da_nap() and openpyxl is not None and _docx is not None
        cls.K2B, cls.XayDungK2 = K2B, XayDungK2

    @classmethod
    def _dung_server(cls):
        cls.server.shutdown()
        cls.thread.join(5)

    @classmethod
    def _builder(cls):
        if "svc" not in cls.s:
            if not cls.co_worker:
                raise unittest.SkipTest("NOT_RUN: lõi nguồn Review chưa nạp hoặc thiếu openpyxl/python-docx — không dựng được hồ sơ")
            cls.goc = cls.app.root
            cls.trich6, cls.gate6 = cls.K2B.M4ChungTuPG._gate_trich6.__func__(cls)
            web = psycopg.connect(cls.cfg[ENV_APP], autocommit=True, row_factory=dict_row)
            cls.addClassCleanup(web.close)
            chu = psycopg.connect(cls.cfg[ENV_CHU], autocommit=True, row_factory=dict_row)
            cls.addClassCleanup(chu.close)
            cls.s["svc"] = cls.XayDungK2(web, cls.app.root / "m4-k2", conn_tin_cay=chu, trich6=cls.trich6)
        return cls.s["svc"]

    # ------------------------------------------------------------------ helpers
    def goi(self, path, body=None, cookie=None, token=True, raw=None, timeout=300):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=timeout)
        try:
            h = {"X-KTT-Token": self.app.token} if token else {}
            if cookie:
                h["Cookie"] = f"{self.app.CRM_COOKIE}={cookie}"
            data = raw
            if raw is None and body is not None:
                data = json.dumps(body).encode("utf-8")
            if data is not None:
                h["Content-Type"] = "application/json"
            c.request("POST" if data is not None else "GET", path, body=data, headers=h)
            r = c.getresponse()
            out, ct, cc = r.read(), r.getheader("Content-Type") or "", r.getheader("Cache-Control")
        finally:
            c.close()
        return r.status, (json.loads(out or b"{}") if ct.startswith("application/json") else out), cc

    def phien(self, login):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=60)
        try:
            c.request("GET", "/api/m4", headers={"X-KTT-Token": self.app.token})
            r = c.getresponse()
            r.read()
            sid = r.getheader("Set-Cookie").split(";", 1)[0].split("=", 1)[1]
        finally:
            c.close()
        st, b, _ = self.goi("/api/m4/danh-tinh", {"dang_nhap": login}, sid)
        self.assertEqual((st, b), (200, {"dang_nhap": login}))
        return sid

    def K(self, ten):
        return f"m4rqh-{self.run_id}-{ten}"

    def q(self, sql, params=()):
        return _q1(self.admin, sql, params)

    def dem(self):
        return {t: self.q(f"SELECT count(*) FROM m4.{t}") for t in BANG}

    def lenh(self, sid, h, khoa, duong="tao", **kw):
        return self.goi(f"{TIEN_TO}/{duong}", {"dot_id": h["dot"], "version_id": h["pb"], "khoa": self.K(khoa)}, sid, **kw)

    def xem(self, sid, dot):
        return self.goi(f"{TIEN_TO}?" + urlencode({"dot_id": dot}), cookie=sid)

    def ho_so(self, nhan):
        if nhan not in self.s:
            self.s[nhan] = dung_seal(self._builder(), self.admin, self.K, nhan, self.run_id)
        return self.s[nhan]

    # ------------------------------------------------------------------ H01
    def test_h01_cong_tham_so(self):
        sid = self.phien(A1)
        dot, pb = str(uuid.uuid4()), str(uuid.uuid4())
        than = {"dot_id": dot, "version_id": pb, "khoa": self.K("h01")}
        st, r, _ = self.goi(f"{TIEN_TO}/tao", than, sid, token=False)
        self.assertEqual((st, r.get("error")), (403, "SESSION_TOKEN"))
        st, r, _ = self.goi(f"{TIEN_TO}/tao", than)
        self.assertEqual((st, r.get("error")), (400, "CRM_PHIEN"))
        truoc = self.dem()
        for k in ("nguoiTao", "so_tien", "amount", "currency", "endpoint", "origin", "api_key", "pdf", "actor", "phap_nhan_id", "remote_id", "idem_key"):
            with self.subTest(k=k):
                st, r, _ = self.goi(f"{TIEN_TO}/tao", {**than, k: "x"}, sid)
                self.assertEqual((st, r.get("error")), (403, "M4_CLIENT_AUTHORITY"))
        st, r, _ = self.goi(f"{TIEN_TO}/tao", {**than, "la": "x"}, sid)
        self.assertEqual((st, r.get("error")), (400, "M4_YEU_CAU_SAI"))
        st, _, _ = self.goi(f"{TIEN_TO}/tao?x=1", than, sid)
        self.assertEqual(st, 400)
        st, _, _ = self.goi(f"{TIEN_TO}?dot_id={dot}&x=1", cookie=sid)
        self.assertEqual(st, 400)
        st, _, _ = self.goi(f"{TIEN_TO}/tao", {**than, "dot_id": "khong-phai-uuid"}, sid)
        self.assertEqual(st, 400)
        st, r, _ = self.goi(f"{TIEN_TO}/tao", raw=json.dumps({**than, "khoa": "k" * 20000}).encode(), cookie=sid)
        self.assertEqual(st, 413)
        for duong in ("gui", "duyet", "xoa", "tra-lai"):
            st, r, _ = self.goi(f"{TIEN_TO}/{duong}", than, sid)
            self.assertEqual((st, r.get("error")), (404, "NOT_FOUND"))
        st, r, _ = self.goi(f"{TIEN_TO}/tao", than, sid)
        self.assertEqual((st, r.get("error")), (404, "M4_REQUEST_KHONG_THAY"))
        self.assertEqual(self.dem(), truoc)

    # ------------------------------------------------------------------ H02
    def test_h02_luong_mat_phan_hoi_timeout(self):
        h = self.ho_so("A")
        sid = self.phien(A1)
        truoc = self.dem()
        self.app.__dict__.pop("_m4_request", None)
        st, r, cc = self.lenh(sid, h, "chua-cau-hinh")
        self.assertEqual((st, r["trang_thai"], r["y_dinh"], cc), (503, "CHUA_CAU_HINH", None, "no-store"))
        self.assertTrue({"khoa_api", "anh_xa_nhan_vien", "origin", "luu_giu_tep_nhiem"} <= set(r["thieu"]), r["thieu"])
        self.assertEqual(self.dem(), truoc)
        dat_anh_xa(self._builder(), A1, h["pn"], "nv.request.a1")
        fake = FakeRequest(DongHo())
        self.app._m4_request = {"cau_hinh": cau_hinh_pg(h["pn"]), "transport": fake}
        # (1) mất ACK tạo → UNKNOWN quan sát được, không giả thành công
        fake.tiem("POST_DE_XUAT", "MAT_ACK")
        st, r, _ = self.lenh(sid, h, "tao-1")
        self.assertEqual((st, r["trang_thai"], r["loi"][0]["ma"], r["loi"][0]["khong_ro"]), (200, "CHUA_RO_TAO", "REQUEST_KHONG_RO", True))
        self.assertEqual(len(fake.de_xuat), 1)
        # (2) đối soát: fake POST chậm 4 giây, trình duyệt timeout 1 giây → client thấy TimeoutError; máy chủ vẫn hoàn tất
        fake.tiem("POST_DE_XUAT", lambda _f: time.sleep(4))
        with self.assertRaises(TimeoutError):
            self.lenh(sid, h, "ds-1", duong="doi-soat", timeout=1)
        st, x, cc = self.xem(sid, h["dot"])
        self.assertEqual((st, cc, len(x["y_dinh"])), (200, "no-store", 1))
        self.assertTrue(x["y_dinh"][0]["dang_xu_ly"])
        st, r, _ = self.lenh(sid, h, "ds-dong-thoi", duong="doi-soat")
        self.assertEqual((st, r.get("error")), (409, "M4_REQUEST_DANG_XU_LY"))
        han = time.monotonic() + 60
        while time.monotonic() < han:
            st, x, _ = self.xem(sid, h["dot"])
            if not x["y_dinh"][0]["dang_xu_ly"]:
                break
            time.sleep(0.5)
        self.assertEqual((x["y_dinh"][0]["dang_xu_ly"], x["y_dinh"][0]["trang_thai"]), (False, "CHO_QUET"))
        n_post = fake.dem("POST", r"/api/v1/.*")
        st, r, _ = self.lenh(sid, h, "ds-1", duong="doi-soat")  # phát lại đúng khóa mà trình duyệt đã mất phản hồi
        self.assertEqual((st, r["lap_lai"], r["trang_thai"], fake.dem("POST", r"/api/v1/.*")), (200, True, "CHO_QUET", n_post))
        self.assertEqual((len(fake.de_xuat), len(fake.tep)), (1, 1))
        # (3) quét clean → đối soát bytes
        fake.quet(next(iter(fake.tep)), "clean")
        st, r, _ = self.lenh(sid, h, "ds-2", duong="doi-soat")
        self.assertEqual((st, r["trang_thai"]), (200, "DA_DOI_SOAT"))
        st, x, _ = self.xem(sid, h["dot"])
        y = x["y_dinh"][0]
        self.assertEqual((y["trang_thai"], y["so_tien"], y["tien_te"], y["remote_id"]), ("DA_DOI_SOAT", "31500000", "VND", next(iter(fake.de_xuat))))
        for cam in ("canonical", "nguoi_tao", "idem_key", "khoa_ref", "actor"):
            self.assertNotIn(cam, y)
        self.assertEqual({s["den_trang_thai"] for s in y["su_kien"]} >= {"CHUA_RO_TAO", "DA_TAO", "DA_TAO_NHAP", "CHO_QUET", "DA_DOI_SOAT"}, True)
        self.assertNotIn("Bearer", json.dumps(x, ensure_ascii=False))
        self.s["A_xong"] = True

    # ------------------------------------------------------------------ H03
    def test_h03_pham_vi(self):
        if "A_xong" not in self.s:
            self.skipTest("H02 chưa dựng hồ sơ — NOT_RUN")
        h = self.s["A"]
        st, r, _ = self.lenh(self.phien(XEM), h, "xem-tao")
        self.assertEqual((st, r.get("error")), (403, "M4_REQUEST_PHAM_VI"))
        sb = self.phien(B1)
        st, r, _ = self.lenh(sb, h, "b1-tao")
        self.assertEqual((st, r.get("error")), (404, "M4_REQUEST_KHONG_THAY"))
        st, r, _ = self.xem(sb, h["dot"])
        self.assertEqual((st, r.get("error")), (404, "M4_REQUEST_KHONG_THAY"))


if __name__ == "__main__":
    unittest.main()
