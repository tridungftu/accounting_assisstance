"""M5 phiếu kho — HTTP trong cùng shell (token, cookie phiên HttpOnly, khóa thao tác) trên PostgreSQL thật, bản sửa 02.

Chỉ chạy khi root cấp KHO_PG_DSN_TEST (DB fixture kho_test_*): login ứng dụng thường (app_web) cho route đọc + kết nối chủ bảng (admin DSN cục bộ,
cùng validator loopback/endpoint) cho intake/FILE_SOAT; server 127.0.0.1 cổng ngẫu nhiên, không mạng ngoài. Kiểm: 403 thiếu token; bộ chọn
vai M5 đúng 8 login registry; trình duyệt không gửi actor/PN/facts/PROVEN; reported_errors sai container → 400 trước ghi; nhận bytes thật
(base64 nguyên văn, kể cả Number lớn/NULL) — server tự hash; cùng khóa khác nội dung → 409 với 0 delta; raw chỉ READ_SOURCE; review/mapping/file
qua hàm guarded (file cùng khóa = cùng lô/bytes; expected cũ → 409); L11 501; tồn/kiểm kê chưa có producer. Không chạy JS/browser: phần epoch UI
(I1) cần kiểm tương tác trình duyệt riêng — ở đây chỉ kiểm phía API. Không DROP DB/role, không xóa thư mục: giữ làm bằng chứng.
"""

from __future__ import annotations

import base64
import http.client
import json
import os
import secrets
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang.primitives import sha256
from kho_tri_thuc.k2 import m5_demo

ROOT = Path(__file__).resolve().parents[1]
ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
M0A, KTA, KTB, CFOA, M1A = "MO_PHONG_M0_KHO_A", "MO_PHONG_KT_KHO_A", "MO_PHONG_KT_KHO_B", "MO_PHONG_CFO_KHO_A", "MO_PHONG_M1_ONLY_KHO_A"
FULL = "FULL_FOR_SINGLE_DETAIL_AND_REFERENCED_MASTER_ONLY"


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test HTTP M5 không chạy (không tính đạt)")
class M5Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        from kho_tri_thuc.k2 import crm_demo
        cls.db = "kho_test_m5http_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.admin = psycopg.connect(dsn, autocommit=True)
        crm_demo.khoi_tao(cls.admin)
        m5_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_m5h_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOCREATEDB NOCREATEROLE IN ROLE app_web")
        app_dsn = f"postgresql://{cls.role}:{pw}@{dsn.split('@', 1)[1]}"
        cls.env = patch.dict(os.environ, {LocalApp.CRM_ENV: app_dsn, LocalApp.CRM_ENV_ADMIN: dsn, LocalApp.CRM_ENV_DB_KIEM_THU: "1"})
        cls.env.start()
        cls.app = LocalApp(ROOT / "cau_hinh.toml", Path(tempfile.mkdtemp(prefix="ktt_m5_http_")) / "web")
        cls.server = LocalServer(cls.app, 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.cookie_name = LocalApp.CRM_COOKIE

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)
        cls.env.stop()
        cls.admin.close()  # giữ DB/role/thư mục làm bằng chứng

    def call(self, path, body=None, cookie=None, token=True):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=60)
        headers = {"X-KTT-Token": self.app.token} if token else {}
        if cookie:
            headers["Cookie"] = f"{self.cookie_name}={cookie}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        c.request("POST" if body is not None else "GET", path, body=None if body is None else json.dumps(body), headers=headers)
        r = c.getresponse()
        raw, ck = r.read(), r.getheader("Set-Cookie")
        c.close()
        is_json = (r.getheader("Content-Type") or "").startswith("application/json")
        return r.status, (json.loads(raw or b"{}") if is_json else raw), ck

    def phien(self, login):
        status, _, ck = self.call("/api/m5")
        self.assertEqual(status, 200)
        self.assertIn("HttpOnly", ck)
        sid = ck.split(";", 1)[0].split("=", 1)[1]
        self.assertEqual(self.call("/api/m5/danh-tinh", {"dang_nhap": login}, sid)[0], 200)
        return sid

    def dem(self):
        q = lambda s: self.admin.execute(s).fetchone()[0]  # noqa: E731
        return tuple(q(f"SELECT count(*) FROM {t}") for t in ("giao_tiep.stage_tin_cay", "giao_tiep.lan_tiep_nhan_nguon", "giao_tiep.tep_tiep_nhan",
                                                              "kho.phieu_kho_quan_sat", "kho.lo_xuat", "kho.bien_nhan_thao_tac"))

    def test_luong_http_m5(self):
        self.assertEqual(self.call("/api/m5", token=False)[0], 403)
        self.assertEqual(self.call("/api/m5/nhan", {"mau": "K01", "khoa": "h1"})[1]["error"], "CRM_PHIEN")

        m0 = self.phien(M0A)
        s = self.call("/api/m5", cookie=m0)[1]
        self.assertEqual(sorted(d["dang_nhap"] for d in s["danh_tinh_demo"]), sorted(m5_demo.dang_nhap_m5()))  # đúng 8 vai, không CRM/M1 khác
        self.assertEqual(self.call("/api/m5/danh-tinh", {"dang_nhap": "MO_PHONG_KT_A"}, m0)[1]["error"], "DANH_TINH_M5")
        self.assertTrue(s["khong_quyen"])
        self.assertEqual({c["hanh_dong"] for c in s["nang_luc_nguon"]}, {"INTAKE", "READ_SOURCE"})
        self.assertEqual({p["source_instance_id"] for p in s["pham_vi_nguon"]}, {"DEMO_KHO_A"})
        self.assertTrue(s["may_chu_nhan"])
        for key in ("actor", "resolved_measurement_facts", "PROVEN", "phap_nhan_id"):
            with self.subTest(key=key):
                status, err, _ = self.call("/api/m5/nhan", {"mau": "K01", "khoa": "h-x", key: "x"}, m0)
                self.assertEqual((status, err["error"]), (403, "M5_CLIENT_AUTHORITY"))
        mm = m5_demo.mau("K08")  # Number lớn + NULL: bytes phải giữ nguyên qua base64
        than = {"source_instance": "DEMO_KHO_A", "scope_ref": s["pham_vi_nguon"][0]["scope_ref"], "coverage": FULL, "khoa": "h-tep",
                "native_b64": base64.b64encode(mm["native"]).decode(), "master_b64": base64.b64encode(mm["master"]).decode()}
        truoc = self.dem()
        for xau in (None, "AB", {"A": 1}, 0, False, [1]):
            with self.subTest(errors=repr(xau)):
                status, err, _ = self.call("/api/m5/nhan", {**than, "reported_errors": xau}, m0)
                self.assertEqual((status, err["error"]), (400, "NGUON_MA_LOI"))
        self.assertEqual(self.dem(), truoc)
        status, r, _ = self.call("/api/m5/nhan", than, m0)  # reported_errors vắng = []
        self.assertEqual((status, r["lap_lai"], r["raw_sha256"]), (200, False, sha256(mm["native"])))
        status, raw, _ = self.call(f"/api/m5/nguon/{r['lan_tiep_nhan_id']}/raw/NATIVE_DETAIL", cookie=m0)
        self.assertEqual((status, raw), (200, mm["native"]))
        self.assertTrue(self.call("/api/m5/nhan", {**than, "reported_errors": []}, m0)[1]["lap_lai"])
        truoc = self.dem()
        status, err, _ = self.call("/api/m5/nhan", {**than, "reported_errors": ["LOI_MOI"]}, m0)
        self.assertEqual((status, err["error"]), (409, "CAPTURE_KHAC_NOI_DUNG"))
        status, err, _ = self.call("/api/m5/nhan", {**than, "master_b64": base64.b64encode(m5_demo.mau("K09")["master"]).decode()}, m0)
        self.assertEqual((status, err["error"]), (409, "CAPTURE_KHAC_NOI_DUNG"))
        self.assertEqual(self.dem(), truoc)
        status, r1, _ = self.call("/api/m5/nhan", {"mau": "K01", "khoa": "h1"}, m0)
        self.assertEqual((status, r1["promote"]["trang_thai"]), (200, "DA_GHI_QUAN_SAT"))
        truoc = self.dem()
        status, r1b, _ = self.call("/api/m5/nhan", {"mau": "K01", "khoa": "h1"}, m0)  # SR02-1: replay qua HTTP trả đúng kết quả cuối đã chốt
        self.assertEqual((status, r1b["lap_lai"], r1b["promote"], r1b["stage_id"], r1b["snapshot_moi"]),
                         (200, True, r1["promote"], r1["stage_id"], r1["snapshot_moi"]))
        self.assertEqual(self.dem(), truoc)

        kt = self.phien(KTA)
        status, err, _ = self.call(f"/api/m5/nguon/{r1['lan_tiep_nhan_id']}/raw/NATIVE_DETAIL", cookie=kt)
        self.assertEqual((status, err["error"]), (403, "NGUON_KHONG_CO_QUYEN"))
        status, err, _ = self.call("/api/m5/nhan", {"mau": "K01", "khoa": "h1"}, kt)
        self.assertEqual((status, err["error"]), (403, "NGUON_KHONG_CO_QUYEN"))
        self.assertEqual(self.call("/api/m5", cookie=kt)[1]["pham_vi_nguon"], [])  # metadata nguồn chỉ theo năng lực nguồn
        [p] = self.call("/api/m5", cookie=kt)[1]["phieu"]
        status, ct, _ = self.call(f"/api/m5/phieu/{p['id']}", cookie=kt)
        self.assertEqual((status, ct["phap_nhan"], ct["duoc"]["M5_SOURCE_REVIEW_V8"]), (200, "PN_DEMO_A", False))
        ptr = ct["con_tro"]
        self.assertRegex(ct["co_so_file"]["co_so_sha256"], r"^[0-9a-f]{64}$")  # token basis do máy chủ dẫn xuất, UI gửi lại làm expected
        file_body = {"phieu_id": p["id"], "khoa": "file-h", "latest_truoc": ptr["latest_observation_id"], "accepted_truoc": ptr["accepted_source_observation_id"],
                     "eligible_truoc": ptr["eligible_content_id"], "co_so_truoc": ct["co_so_file"]["co_so_sha256"]}
        truoc = self.dem()
        for sai, ma, code in (({"duong_dan": "m0-raw/x"}, 400, "M5_YEU_CAU_SAI"), ({"co_so_truoc": None}, 400, "M5_CO_SO_FILE"),
                              ({"co_so_truoc": "0" * 64, "khoa": "file-h-stale"}, 409, "KHO_VERSION_CHANGED")):
            with self.subTest(sai=list(sai)):
                status, err, _ = self.call("/api/m5/xuat-file-soat", {**file_body, **sai}, kt)
                self.assertEqual((status, err["error"]), (ma, code))
        self.assertEqual(self.dem(), truoc)
        status, lo, _ = self.call("/api/m5/xuat-file-soat", file_body, kt)
        self.assertEqual((status, lo["lap_lai"], lo["co_so_sha256"]), (200, False, file_body["co_so_truoc"]))
        status, lai, _ = self.call("/api/m5/xuat-file-soat", file_body, kt)
        self.assertEqual((status, lai["lap_lai"], lai["id"]), (200, True, lo["id"]))
        status, err, _ = self.call("/api/m5/xuat-file-soat", {**file_body, "khoa": "file-cu", "latest_truoc": None}, kt)
        self.assertEqual((status, err["error"]), (409, "KHO_VERSION_CHANGED"))
        status, raw, _ = self.call(f"/api/m5/file-soat/{lo['id']}", cookie=kt)
        self.assertEqual((status, raw[:2], sha256(raw)), (200, b"PK", lo["sha256"]))
        status, err, _ = self.call("/api/m5/lien-ket/preview", {"phieu_id": p["id"]}, kt)
        self.assertEqual((status, err["error"]), (501, "M5_L11_CHUA_PHAT_HANH"))
        status, ton, _ = self.call("/api/m5/ton-nguon", cookie=kt)
        self.assertEqual((status, ton["trang_thai"], ton["du_lieu"]), (200, "CHUA_CO_SNAPSHOT_PRODUCER", []))
        review = {"phieu_id": p["id"], "observation_id": ptr["latest_observation_id"], "quyet_dinh": "CHAP_NHAN_NGUON", "accepted_truoc": None,
                  "eligible_truoc": None, "latest_truoc": ptr["latest_observation_id"], "ly_do": "DEMO HTTP", "khoa": "rv-h"}
        status, err, _ = self.call("/api/m5/nguon/kiem-lai", review, kt)
        self.assertEqual((status, err["error"]), (403, "KHONG_CO_QUYEN_HANH_DONG"))

        cfo = self.phien(CFOA)
        status, err, _ = self.call("/api/m5/nguon/kiem-lai", {**review, "latest_truoc": None, "khoa": "rv-cu"}, cfo)
        self.assertEqual((status, err["error"]), (409, "KHO_VERSION_CHANGED"))
        status, r, _ = self.call("/api/m5/nguon/kiem-lai", review, cfo)
        self.assertEqual((status, r["quyet_dinh"], r["lap_lai"]), (200, "CHAP_NHAN_NGUON", False))
        self.assertTrue(self.call("/api/m5/nguon/kiem-lai", review, cfo)[1]["lap_lai"])
        status, m, _ = self.call("/api/m5/mapping", {"source_instance": "DEMO_KHO_A", "ma_kho": "KHO_HTTP", "phap_nhan": "PN_DEMO_A", "revision_hien_tai": 0,
                                                     "ly_do": "DEMO", "khoa": "map-h"}, cfo)
        self.assertEqual((status, m["revision"]), (200, 1))

        ktb = self.phien(KTB)
        self.assertEqual(self.call("/api/m5", cookie=ktb)[1]["phieu"], [])
        self.assertEqual(self.call(f"/api/m5/phieu/{p['id']}", cookie=ktb)[1]["error"], "PHIEU_KHO")
        self.assertEqual(self.call(f"/api/m5/file-soat/{lo['id']}", cookie=ktb)[1]["error"], "FILE_SOAT")
        m1 = self.phien(M1A)
        s = self.call("/api/m5", cookie=m1)[1]
        self.assertEqual((s["phieu"], bool(s["khong_quyen"])), ([], True))
        self.assertEqual(self.call("/api/m5/danh-tinh", {"dang_nhap": "NGUOI_THAT_DEMO"}, m1)[1]["error"], "DANH_TINH_M5")

    def test_shell_co_trang_va_form_nhan_tep(self):
        """Chỉ kiểm tài nguyên được phục vụ (không thay kiểm tương tác trình duyệt cho epoch/picker)."""
        _, raw_html, _ = self.call("/")
        for chuoi in (b"page-phieukho", b"m5-tl-native", b"m5-tl-master", b"m5-tl-khoa", b"m5-tl-loi"):
            self.assertIn(chuoi, raw_html)
        _, js, _ = self.call("/app.js")
        for chuoi in (b"m5Epoch", b"readAsArrayBuffer", b"m5XoaTrangThai", b"m5FormEpoch", b"m5KhoaFile", b"co_so_truoc", b"conHieuLuc"):
            self.assertIn(chuoi, js)  # chỉ có mặt giao diện — không thay kiểm trình duyệt (R1/R2/R3 cần root chạy GUI)
        self.assertNotIn(b"JSON.parse(r.result", js)


if __name__ == "__main__":
    unittest.main()
