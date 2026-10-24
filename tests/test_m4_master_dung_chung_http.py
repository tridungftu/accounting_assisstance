"""MASTER-REUSE-02 — kiểm HTTP thật route bộ chọn master/đối tác + lệnh nhận master/gắn đối tác trên LocalApp/LocalServer + clone DEMO sở hữu.
CODE_ONLY: coder viết, CHƯA CHẠY (WRITTEN_NOT_RUN).

Cùng cổng clone với tests/test_m4_master_dung_chung_pg.py (env KHO_M4_MC_CLONE_*; không env → SkipTest NOT_VERIFIED; cấu hình dở/clone không chứng minh
được → lỗi thiết lập TRƯỚC mọi ghi). KHÔNG tạo CSDL/role, KHÔNG migrate, KHÔNG apply SQL. Đối tác/mapping DEMO của lượt: FIXTURE_MASTER_SEED_OWNER
(owner INSERT-only). Mọi thao tác người dùng đi qua HTTP loopback cổng ngẫu nhiên, cùng token/cookie như trình duyệt. Không DROP/DELETE/TRUNCATE.

M01 phiên/tham số: thiếu token → 403; query lạ/lặp → 400; limit/q sai → 400; GET đúng → 200 no-store; XEM → 403 bộ chọn.
M02 thân lệnh: trường authority (actor/phap_nhan_id/trang_thai/sha256/digest) → 403; trường lạ (module_chu/doi_tac_ten/mapping_trang_thai) → 400;
    id sai dạng → 400; HĐ lạ → 404.
M03 luồng: tạo hồ sơ → GET hồ sơ có master_can_cu (HOLD thiếu đối tác) → GET master-doi-tac → POST gan-doi-tac → replay lap_lai → CAS cũ 409 →
    nhận master đã có hồ sơ → da_co_san; XEM → 403 lệnh, 200 xem (gan_doi_tac.duoc false).
"""

from __future__ import annotations

import http.client
import json
import os
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

from tests.test_m4_02c_pg import A1, XEM, _q1
from tests.test_m4_master_dung_chung_pg import CO_ENV, ENV_APP, ENV_CHU, LY_DO_SKIP, cau_hinh_clone, kiem_clone_mc, seed_doi_tac
from tests.test_m4_review_http import CAU_HINH_FIXTURE


@unittest.skipUnless(CO_ENV, LY_DO_SKIP)
class M4MasterDungChungHttp(unittest.TestCase):
    """Các ca chạy theo thứ tự m01…m03 trên MỘT clone/một máy chủ; trạng thái qua cls.s."""

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        cfg = cau_hinh_clone()
        cls.admin = psycopg.connect(cfg[ENV_CHU], autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        web0 = psycopg.connect(cfg[ENV_APP], autocommit=True)
        cls.addClassCleanup(web0.close)
        cls.gate = kiem_clone_mc(cls.admin, web0, cfg)  # CHỈ ĐỌC — sai → lỗi thiết lập, chưa ghi gì
        cls.run_id = uuid.uuid4().hex[:8]
        cls.s = {}
        cls.env = patch.dict(os.environ, {LocalApp.CRM_ENV: cfg[ENV_APP], LocalApp.CRM_ENV_ADMIN: cfg[ENV_CHU], LocalApp.CRM_ENV_DB_KIEM_THU: "1"})
        cls.env.start()
        cls.addClassCleanup(cls.env.stop)
        tam = Path(tempfile.mkdtemp(prefix="ktt_m4_mc_http_"))  # giữ lại
        (tam / "cau_hinh_fixture.toml").write_text(CAU_HINH_FIXTURE, encoding="utf-8")
        cls.app = LocalApp(tam / "cau_hinh_fixture.toml", tam / "web")
        cls.server = LocalServer(cls.app, 0)
        cls.addClassCleanup(cls.server.server_close)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls._dung_server)  # chạy TRƯỚC server_close (LIFO)
        cls.du_an = str(_q1(cls.admin, "SELECT id FROM master.du_an WHERE ma_junsky = 'DA_XD_A1'"))
        cls.pn = str(_q1(cls.admin, "SELECT phap_nhan_id FROM master.du_an WHERE id = %s", (cls.du_an,)))

    @classmethod
    def _dung_server(cls):
        cls.server.shutdown()
        cls.thread.join(5)

    # ------------------------------------------------------------------ helpers (cùng khung test_m4_02c_http)
    def goi(self, path, body=None, cookie=None, token=True):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=300)
        try:
            h = {"X-KTT-Token": self.app.token} if token else {}
            if cookie:
                h["Cookie"] = f"{self.app.CRM_COOKIE}={cookie}"
            data = None
            if body is not None:
                h["Content-Type"] = "application/json"
                data = json.dumps(body).encode("utf-8")
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
        return f"m4mch-{self.run_id}-{ten}"

    def q(self, sql, params=()):
        return _q1(self.admin, sql, params)

    def ok(self, path, body, sid):
        st, r, _ = self.goi(path, body, sid)
        self.assertEqual(st, 200, (path, r))
        return r

    def get_ok(self, path, sid, **qs):
        st, r, cc = self.goi(path + ("?" + urlencode(qs) if qs else ""), cookie=sid)
        self.assertEqual((st, cc), (200, "no-store"), (path, r))
        return r

    def ho_so(self, sid, nhan) -> str:
        return self.ok("/api/m4/hop-dong/tao", {"du_an_id": self.du_an, "so_hop_dong": f"MCH-{self.run_id}-{nhan}", "ten": f"Hồ sơ MC HTTP {nhan}",
                                                "khoa": self.K(f"{nhan}-hd")}, sid)["hop_dong_id"]

    # ------------------------------------------------------------------ M01
    def test_m01_phien_tham_so(self):
        sid = self.phien(A1)
        st, r, _ = self.goi(f"/api/m4/master-hop-dong?du_an_id={self.du_an}", cookie=sid, token=False)
        self.assertEqual((st, r.get("error")), (403, "SESSION_TOKEN"))
        for duong in ("/api/m4/master-hop-dong", "/api/m4/master-doi-tac"):
            for qs in (f"du_an_id={self.du_an}&actor={A1}", f"du_an_id={self.du_an}&du_an_id={self.du_an}", f"du_an_id={self.du_an}&phap_nhan_id=x",
                       f"du_an_id={self.du_an}&q=a&q=b"):
                st, r, _ = self.goi(f"{duong}?{qs}", cookie=sid)
                self.assertEqual((st, r.get("error")), (400, "M4_YEU_CAU_SAI"), (duong, qs))
            for qs in ("du_an_id=khong-uuid", f"du_an_id={self.du_an}&limit=0", f"du_an_id={self.du_an}&limit=51", f"du_an_id={self.du_an}&limit=abc",
                       f"du_an_id={self.du_an}&q=" + "x" * 101):
                st, r, _ = self.goi(f"{duong}?{qs}", cookie=sid)
                self.assertEqual((st, r.get("error")), (400, "M4_THAM_SO_SAI"), (duong, qs))
            r = self.get_ok(duong, sid, du_an_id=self.du_an, limit="5")
            self.assertEqual((r["du_an_id"], r["limit"]), (self.du_an, 5))
            self.assertLessEqual(len(r["items"]), 5)
        sx = self.phien(XEM)
        for duong in ("/api/m4/master-hop-dong", "/api/m4/master-doi-tac"):
            st, r, _ = self.goi(f"{duong}?du_an_id={self.du_an}", cookie=sx)
            self.assertEqual((st, r.get("error")), (403, "M4_KHONG_CO_QUYEN_DU_AN"), duong)

    # ------------------------------------------------------------------ M02
    def test_m02_than_lenh(self):
        sid = self.phien(A1)
        hd, dt, mp = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        nhan = {"du_an_id": self.du_an, "hop_dong_id": hd, "ten": "x", "expected_master": "0" * 64, "khoa": self.K("m02-n")}
        gan = {"hop_dong_id": hd, "doi_tac_id": dt, "mapping_id": mp, "revision": 1, "expected_master": "0" * 64, "expected_mapping": "0" * 64,
               "ly_do": "x", "khoa": self.K("m02-g")}
        for duong, than in (("/api/m4/hop-dong/nhan-master", nhan), ("/api/m4/hop-dong/gan-doi-tac", gan)):
            for them in ({"actor": A1}, {"phap_nhan_id": self.pn}, {"trang_thai": "HIEU_LUC"}, {"sha256": "a" * 64}, {"digest": "a" * 64}):
                st, r, _ = self.goi(duong, {**than, **them}, sid)
                self.assertEqual((st, r.get("error")), (403, "M4_CLIENT_AUTHORITY"), (duong, them))
            for them in ({"module_chu": "M4"}, {"doi_tac_ten": "X"}, {"mapping_trang_thai": "OK"}):
                st, r, _ = self.goi(duong, {**than, **them}, sid)
                self.assertEqual((st, r.get("error")), (400, "M4_YEU_CAU_SAI"), (duong, them))
            st, r, _ = self.goi(duong, {**than, "hop_dong_id": "khong-uuid"}, sid)
            self.assertEqual((st, r.get("error")), (400, "M4_THAM_SO_SAI"), duong)
        st, r, _ = self.goi("/api/m4/hop-dong/nhan-master", nhan, sid)
        self.assertEqual((st, r.get("error")), (404, "M4_MASTER_KHONG_THAY"))
        st, r, _ = self.goi("/api/m4/hop-dong/gan-doi-tac", gan, sid)
        self.assertEqual((st, r.get("error")), (404, "M4_KHONG_THAY_HOP_DONG"))
        st, r, _ = self.goi("/api/m4/hop-dong/gan-doi-tac", {**gan, "ly_do": None}, sid)
        self.assertEqual(st, 400)

    # ------------------------------------------------------------------ M03
    def test_m03_luong(self):
        sid = self.phien(A1)
        hd = self.ho_so(sid, "m03")
        st, ct, _ = self.goi(f"/api/m4/hop-dong/{hd}", cookie=sid)
        self.assertEqual(st, 200)
        mc = ct["master_can_cu"]
        self.assertIsNotNone(mc, "gói SQL đã apply → chi tiết phải có master_can_cu")
        self.assertEqual((mc["revision"], mc["gan_doi_tac"]["duoc"], mc["dong_bo"]), (1, True, True))
        self.assertIn("MAPPING_KHONG_DOI_TAC", mc["hold"])
        # bộ chọn master thấy HĐ vừa tạo (đã có hồ sơ) → nhận lại = da_co_san, không hàng mới
        so = f"MCH-{self.run_id}-m03"
        ds = self.get_ok("/api/m4/master-hop-dong", sid, du_an_id=self.du_an, q=so)["items"]
        it = next(x for x in ds if str(x["hop_dong_id"]) == hd)
        self.assertEqual((it["da_co_ho_so_m4"], it["module_chu"]), (True, "M4"))
        n0 = self.q("SELECT count(*) FROM m4.master_can_cu WHERE hop_dong_id = %s", (hd,))
        r = self.ok("/api/m4/hop-dong/nhan-master", {"du_an_id": self.du_an, "hop_dong_id": hd, "ten": "Lại", "expected_master": it["expected_master"],
                                                     "khoa": self.K("m03-nhan")}, sid)
        self.assertEqual((r["da_co_san"], r["lap_lai"]), (True, False))
        self.assertEqual(self.q("SELECT count(*) FROM m4.master_can_cu WHERE hop_dong_id = %s", (hd,)), n0)
        # gắn đối tác qua DTO bộ chọn
        d = seed_doi_tac(self.admin, self.run_id, "m03", self.pn)  # FIXTURE_MASTER_SEED_OWNER
        x = next(i for i in self.get_ok("/api/m4/master-doi-tac", sid, du_an_id=self.du_an, q=d["ten"][-30:])["items"]
                 if str(i["doi_tac_id"]) == d["doi_tac_id"])
        self.assertIsNone(x["ma_hold"])
        than = {"hop_dong_id": hd, "doi_tac_id": d["doi_tac_id"], "mapping_id": x["mapping_id"], "revision": mc["revision"],
                "expected_master": mc["expected_master"], "expected_mapping": x["expected_mapping"], "ly_do": "Gắn theo HĐ ký (DEMO HTTP)",
                "khoa": self.K("m03-gan")}
        sx = self.phien(XEM)
        st, rx, _ = self.goi("/api/m4/hop-dong/gan-doi-tac", than, sx)
        self.assertEqual((st, rx.get("error")), (403, "M4_KHONG_CO_QUYEN_DU_AN"))
        g = self.ok("/api/m4/hop-dong/gan-doi-tac", than, sid)
        self.assertEqual((g["revision"], g["lap_lai"], g["hop_dong_id"]), (2, False, hd))
        lai = self.ok("/api/m4/hop-dong/gan-doi-tac", than, sid)
        self.assertEqual((lai["lap_lai"], lai["revision"]), (True, 2))
        st, r, _ = self.goi("/api/m4/hop-dong/gan-doi-tac", {**than, "ly_do": "khác"}, sid)
        self.assertEqual((st, r.get("error")), (409, "M4_IDEMPOTENCY_KHAC"))
        st, r, _ = self.goi("/api/m4/hop-dong/gan-doi-tac", {**than, "khoa": self.K("m03-cu")}, sid)
        self.assertEqual((st, r.get("error")), (409, "M4_REVISION_CU"))
        st, r, _ = self.goi("/api/m4/hop-dong/gan-doi-tac", {**than, "revision": 2, "khoa": self.K("m03-em")}, sid)
        self.assertEqual((st, r.get("error")), (409, "M4_MASTER_DA_DOI"))
        mc2 = self.goi(f"/api/m4/hop-dong/{hd}", cookie=sid)[1]["master_can_cu"]
        self.assertEqual((mc2["revision"], mc2["dong_bo"], mc2["master"]["mapping_trang_thai"], mc2["can_cu"]["nguon"]), (2, True, "OK", "GAN_DOI_TAC"))
        self.assertEqual(mc2["expected_master"], g["expected_master"])
        st, r, _ = self.goi("/api/m4/hop-dong/gan-doi-tac", {**than, "revision": 2, "expected_master": mc2["expected_master"],
                                                             "khoa": self.K("m03-same")}, sid)
        self.assertEqual((st, r.get("error")), (409, "M4_KHONG_DOI"))
        # XEM đọc được hồ sơ, không có nút gắn
        st, cx, _ = self.goi(f"/api/m4/hop-dong/{hd}", cookie=sx)
        self.assertEqual(st, 200)
        self.assertEqual(cx["master_can_cu"]["gan_doi_tac"], {"duoc": False, "ma": "M4_KHONG_CO_QUYEN_DU_AN"})


if __name__ == "__main__":
    unittest.main()
