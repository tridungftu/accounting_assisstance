"""M4-02A — kiểm HTTP thật route Review L1/L2 trên LocalApp/LocalServer + PostgreSQL DEMO mới. CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN_CODE_ONLY).

Cùng khung M4-01C: KHO_PG_DSN_TEST qua env lúc chạy (không .env/var, không hardcode credentials); DB mới `kho_test_m4rh_*` migrate 1–19, seed CRM + M4
DEMO; login ứng dụng tạm IN ROLE app_web + admin DSN cho factory đường tin cậy; HTTP loopback cổng ngẫu nhiên, cùng token/cookie như trình duyệt.
Không DROP/DELETE/TRUNCATE/cleanup. Thiếu driver/DSN → skip = NOT_RUN; ca chạy worker cần lõi nguồn + openpyxl, skip riêng.
Không chứng minh trình duyệt/hiển thị 1280–1440 (Root kiểm GUI riêng).

H01 tài sản: /m4/review.js đúng một route, no-store, không HTML chuỗi; /m4.js mount tab Review.
H02 phiên/token/tham số: GET list thiếu token → 403 SESSION_TOKEN; tham số lạ/lặp → 400 M4_YEU_CAU_SAI; body có trường authority → 403; o_dich xấu → 400.
H03 SOAN L1 qua HTTP: list (basis) → chạy → chi tiết → tải báo cáo đúng hash + Content-Disposition; replay cùng khóa/body → cùng run; đổi body → 409;
    expected basis cũ → 409 M4_REVIEW_CO_SO_DOI.
H04 phạm vi: actor khác PN → 404 chi tiết/tải; chạy KHÔNG đợt trên kết nối thao tác mới: B1 → đúng 403/M4_KHONG_CO_QUYEN_DU_AN, reviewer →
    đúng 403/M4_REVIEW_PHAM_VI (FIX04 M20; không chấp nhận 400/CSDL_TU_CHOI); reviewer không thấy lần chạy L1 không đợt (404); lỗi không lộ dữ liệu.
H01 (FIX04) kiểm VIỆC DÙNG innerHTML/outerHTML/insertAdjacentHTML/document.write thật (có đối chứng), không cấm chữ trong chú thích.
H05 (FIX01 R3) trong lúc worker Review đang tính (giữ có kiểm soát bằng Event, sau đó chạy worker thật): GET /api/m4, GET danh sách Review và đổi vai
    CÙNG phiên trả ngay (không chờ CPU); lần chạy giữ danh tính lúc gửi (A1).
H06 (FIX01 R7, phần quan sát được qua HTTP) tài sản có API tat() và shell gọi tatReview(); fence DOM thật cần GUI do Root kiểm.
    FIX02 F5/F6: bản /m4.js do máy chủ phục vụ mount Review SAU khi khung gắn vào document; /m4/review.js mang thế hệ form vào lenh.
    Luồng DOM thật (mount positive có form/GET, A muộn sau nháp B, tab/blob) vẫn NOT_VERIFIED cho tới khi Root chạy shell thật.
    FIX03 F2/F3: tài sản thật mang fence thế hệ form trong napDs và nút báo cáo flatMap. H07: lần chạy L1 thật có artifact đăng ký không rỗng →
    mỗi REPORT có id/hash/độ dài → tải theo đúng route quyền hiện hành ra bytes không rỗng khớp hash (dữ liệu nền cho nút thật trên UI).
"""

from __future__ import annotations

import hashlib
import http.client
import io
import json
import os
import re
import secrets
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote, urlencode

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None
try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None

from kho_tri_thuc.kiem_chung import fixtures_m4 as F
from kho_tri_thuc.m4 import nguon_review as NR

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
A1, B1, REVIEW = "MO_PHONG_DU_AN_A1", "MO_PHONG_DU_AN_B1", "MO_PHONG_REVIEW_M4"
XLSX = F.MEDIA_XLSX
CAU_HINH_FIXTURE = """[app]
entity_id = "PLHN_FIXTURE"
environment = "fixture"
data_dir = "data"

[money]
currency = "VND"
scale = 0

[operation]
junsky_export_enabled = false
junsky_import_enabled = false

[storage]
engine = "sqlite"
"""


def _nguon_da_nap() -> bool:
    return NR.GOC.is_dir() and all((NR.GOC / rel).is_file() for rel in NR.PIN)


def _ho_so_xlsx() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TH"
    for i, (nhan, v) in enumerate((("Giá trị thực hiện kỳ này", 9_500_000), ("Đề nghị thanh toán kỳ này", 8_550_000)), 1):
        ws.cell(i, 1, nhan)
        ws.cell(i, 3, v)
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test HTTP M4-02A không chạy (NOT_RUN, không tính đạt)")
class M4ReviewHttp(unittest.TestCase):
    """Các ca chạy theo thứ tự tên h01…h04 trên MỘT DB/một máy chủ; trạng thái qua cls.s."""

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.k2 import crm_demo, m4_demo
        cls.db = "kho_test_m4rh_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)
        cls.version = pg.migrate(cls.admin)
        crm_demo.khoi_tao(cls.admin)
        cls.seed = m4_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_m4rh_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE IN ROLE app_web")
        app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        cls.env = patch.dict(os.environ, {LocalApp.CRM_ENV: app_dsn, LocalApp.CRM_ENV_ADMIN: cls.dsn, LocalApp.CRM_ENV_DB_KIEM_THU: "1"})
        cls.env.start()
        tam = Path(tempfile.mkdtemp(prefix="ktt_m4r_http_"))  # giữ lại
        (tam / "cau_hinh_fixture.toml").write_text(CAU_HINH_FIXTURE, encoding="utf-8")
        cls.app = LocalApp(tam / "cau_hinh_fixture.toml", tam / "web")
        cls.server = LocalServer(cls.app, 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.run_id = uuid.uuid4().hex[:8]
        cls.s = {}

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)
        cls.env.stop()
        cls.admin.close()  # giữ DB/role/thư mục làm bằng chứng

    # ------------------------------------------------------------------ helpers (cùng khung test_m4_01c_http)
    def goi(self, path, body=None, cookie=None, token=True, raw=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=1200)
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
        c.close()
        return r.status, (json.loads(out or b"{}") if ct.startswith("application/json") else out), cd, cc

    def phien(self, login):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=60)
        c.request("GET", "/api/m4", headers={"X-KTT-Token": self.app.token})
        r = c.getresponse()
        r.read()
        sid = r.getheader("Set-Cookie").split(";", 1)[0].split("=", 1)[1]
        c.close()
        st, b, _, _ = self.goi("/api/m4/danh-tinh", {"dang_nhap": login}, sid)
        self.assertEqual((st, b), (200, {"dang_nhap": login}))
        return sid

    def K(self, ten):
        return f"m4rh-{self.run_id}-{ten}"

    def du_an(self, ma):
        return str(self.admin.execute("SELECT id FROM master.du_an WHERE ma_junsky = %s", (ma,)).fetchone()[0])

    def ds(self, sid, **q):
        st, r, _, _ = self.goi("/api/m4/review?" + urlencode(q), cookie=sid)
        return st, r

    def can_worker(self):
        if not (_nguon_da_nap() and openpyxl is not None):
            self.skipTest("Lõi nguồn Review chưa nạp hoặc thiếu openpyxl — NOT_RUN")

    # ------------------------------------------------------------------ H01
    def test_h01_tai_san(self):
        st, js, _, cc = self.goi("/m4/review.js", token=False)
        self.assertEqual((st, cc), (200, "no-store"))
        self.assertIn(b'dangKyVai("m4_review"', js)
        # FIX04: kiểm VIỆC DÙNG thuộc tính/hàm chèn HTML (truy cập thuộc tính `.innerHTML`/`.outerHTML`, kể cả dạng ["innerHTML"], hay gọi
        # insertAdjacentHTML/document.write) — chú thích mô tả "không innerHTML" không phải việc dùng. Vẫn bảo vệ DOM như trước.
        dung_html = re.compile(rb"""\.\s*(?:innerHTML|outerHTML)\b|\[\s*["'](?:innerHTML|outerHTML)["']\s*\]|insertAdjacentHTML\s*\(|document\s*\.\s*write\s*\(""")
        self.assertIsNone(dung_html.search(js), dung_html.search(js))
        self.assertIsNotNone(dung_html.search(b"x.innerHTML = s"))  # đối chứng: biểu thức dùng thật bị bắt
        self.assertIsNotNone(dung_html.search(b'x["innerHTML"] = s'))
        self.assertIsNone(dung_html.search(b"// ch\xc3\xba th\xc3\xadch: kh\xc3\xb4ng innerHTML"))  # chú thích không phải việc dùng
        self.assertIn(b"textContent", js)  # dựng DOM bằng textContent
        self.assertEqual(js, (Path(NR.__file__).parent / "giao_dien" / "review.js").read_bytes())
        for xau in ("/m4/review.css", "/m4/checks.js", "/m4/review_goc/may_chu/giao_dien/checks.js", "/m4/../m4.py"):
            st, _, _, _ = self.goi(xau, token=False)
            self.assertNotEqual(st, 200, xau)  # không có static server tổng quát
        st, m4, _, _ = self.goi("/m4.js", token=False)
        self.assertIn(b"/m4/review.js", m4)
        self.assertEqual(self.version, 20)  # FIX04: 1–19 + M20 corrective cuối

    # ------------------------------------------------------------------ H02
    def test_h02_phien_token_tham_so(self):
        sid = self.phien(A1)
        st, r, _, _ = self.goi("/api/m4/review", cookie=sid, token=False)
        self.assertEqual((st, r.get("error")), (403, "SESSION_TOKEN"))
        st, r = self.ds(sid, actor=A1)
        self.assertEqual((st, r.get("error")), (400, "M4_YEU_CAU_SAI"))
        st, r, _, _ = self.goi("/api/m4/review?dot_id=a&dot_id=b", cookie=sid)
        self.assertEqual((st, r.get("error")), (400, "M4_YEU_CAU_SAI"))
        st, r = self.ds(sid, o_dich="[x.xlsx]TH!A1")
        self.assertEqual((st, r.get("error")), (400, "M4_REVIEW_O_DICH_SAI"))
        st, r = self.ds(sid, che_do="L3")
        self.assertEqual((st, r.get("error")), (400, "M4_REVIEW_CHE_DO_SAI"))
        st, r, _, _ = self.goi("/api/m4/review/chay", {"du_an_id": self.du_an("DA_XD_A1"), "tep_id": str(uuid.uuid4()), "che_do": "L1",
                                                       "expected_basis": "0" * 64, "khoa": self.K("auth"), "actor": "x"}, sid)
        self.assertEqual((st, r.get("error")), (403, "M4_CLIENT_AUTHORITY"))
        st, r, _, _ = self.goi("/api/m4/review/chay", {"du_an_id": self.du_an("DA_XD_A1"), "tep_id": str(uuid.uuid4()), "che_do": "L1_L2",
                                                       "expected_basis": "0" * 64, "khoa": self.K("can-dot")}, sid)
        self.assertEqual((st, r.get("error")), (400, "M4_REVIEW_CAN_DOT"))
        st, r, _, _ = self.goi(f"/api/m4/review/{uuid.uuid4()}", cookie=sid)
        self.assertEqual((st, r.get("error")), (404, "M4_REVIEW_KHONG_THAY"))
        self.s["sid_a1"] = sid

    # ------------------------------------------------------------------ H03
    def test_h03_soan_l1_qua_http(self):
        self.can_worker()
        sid, du_an = self.s["sid_a1"], self.du_an("DA_XD_A1")
        raw = _ho_so_xlsx()
        info = quote(json.dumps({"du_an_id": du_an, "vai_tro": "HO_SO_DOT", "ten": "ho_so.xlsx", "media_type": XLSX, "khoa": self.K("tep")}))
        st, t, _, _ = self.goi("/api/m4/tep", cookie=sid, raw=raw, headers={"X-M4-Info": info, "Content-Type": "application/octet-stream"})
        self.assertEqual(st, 200, t)
        tep = t["tep_id"]
        st, d = self.ds(sid, tep_id=tep, che_do="L1")
        self.assertEqual(st, 200, d)
        cs = d["co_so"]
        self.assertTrue(cs["san_sang"], cs)
        self.assertEqual((cs["quyen"], cs["che_do"], cs["du_an_id"]), ("SOAN", "L1", du_an))
        than = {"du_an_id": du_an, "tep_id": tep, "che_do": "L1", "dot_id": None, "o_dich": None, "expected_basis": cs["basis_sha256"], "khoa": self.K("l1")}
        st, r, _, _ = self.goi("/api/m4/review/chay", than, sid)
        self.assertEqual(st, 200, r)
        self.assertIn(r["trang_thai"], ("SUCCEEDED", "PARTIAL"), r)
        st, lai, _, _ = self.goi("/api/m4/review/chay", than, sid)  # bấm lặp/timeout: gửi lại đúng body + khóa
        self.assertEqual((st, lai["run_id"], lai["lap_lai"]), (200, r["run_id"], True))
        st, x, _, _ = self.goi("/api/m4/review/chay", {**than, "o_dich": "TH!C2"}, sid)
        self.assertEqual((st, x.get("error")), (409, "M4_IDEMPOTENCY_KHAC"))
        st, ct, _, _ = self.goi("/api/m4/review/" + r["run_id"], cookie=sid)
        self.assertEqual(st, 200, ct)
        self.assertEqual(ct["run"]["raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(set(ct["ket_qua"]["coverage"]), {"K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8"})
        rep = next(a for a in ct["artifact"] if a["loai"] == "REPORT_L1")
        st, b, cd, cc = self.goi(f"/api/m4/review/{r['run_id']}/tep/{rep['id']}", cookie=sid)
        self.assertEqual((st, hashlib.sha256(b).hexdigest(), len(b), cc), (200, rep["raw_sha256"], rep["byte_length"], "no-store"))
        self.assertIn("attachment", cd or "")
        st, _, _, _ = self.goi(f"/api/m4/review/{r['run_id']}/tep/{rep['id']}", cookie=sid, token=False)
        self.assertEqual(st, 403)
        st, _, _, _ = self.goi(f"/api/m4/review/{r['run_id']}/tep/{uuid.uuid4()}", cookie=sid)
        self.assertEqual(st, 404)
        # basis đổi (đã có lần chạy mới không làm đổi basis L1; dùng token giả hợp lệ dạng hex) → 409 trước khi tính
        st, x, _, _ = self.goi("/api/m4/review/chay", {**than, "expected_basis": "f" * 64, "khoa": self.K("l1-cu")}, sid)
        self.assertEqual((st, x.get("error")), (409, "M4_REVIEW_CO_SO_DOI"))
        st, x, _, _ = self.goi("/api/m4/review/chay-lai", {"run_id": r["run_id"], "expected_basis": cs["basis_sha256"], "khoa": self.K("lai")}, sid)
        self.assertEqual(st, 200, x)
        self.assertNotEqual(x["run_id"], r["run_id"])
        st, ds, _, _ = self.goi("/api/m4/review?" + urlencode({"tep_id": tep}), cookie=sid)
        self.assertEqual(st, 200)
        self.s.update(tep=tep, run=r["run_id"], rep=rep["id"], basis=cs["basis_sha256"])

    # ------------------------------------------------------------------ H04
    def test_h04_ngoai_pham_vi(self):
        if "run" not in self.s:
            self.skipTest("H03 chưa có lần chạy — NOT_RUN")
        for login in (B1, REVIEW):
            sid = self.phien(login)
            for path in (f"/api/m4/review/{self.s['run']}", f"/api/m4/review/{self.s['run']}/tep/{self.s['rep']}"):
                st, r, _, _ = self.goi(path, cookie=sid)
                self.assertEqual(st, 404, (login, path, r))
                self.assertNotIn(b"ho_so.xlsx", json.dumps(r, ensure_ascii=False).encode("utf-8"))
            st, r, _, _ = self.goi("/api/m4/review/chay", {"du_an_id": self.du_an("DA_XD_A1"), "tep_id": self.s["tep"], "che_do": "L1", "dot_id": None,
                                                           "o_dich": None, "expected_basis": self.s["basis"], "khoa": self.K("ngoai-" + login)}, sid)
            # FIX04: mã domain CHÍNH XÁC theo actor (không chấp nhận 400/CSDL_TU_CHOI hay lẫn mã giữa hai ca)
            mong = (403, "M4_KHONG_CO_QUYEN_DU_AN") if login == B1 else (403, "M4_REVIEW_PHAM_VI")
            self.assertEqual((st, r.get("error")), mong, (login, r))
            st, r, _, _ = self.goi("/api/m4/review/chay-lai", {"run_id": self.s["run"], "expected_basis": self.s["basis"], "khoa": self.K("lai-" + login)}, sid)
            self.assertEqual((st, r.get("error")), (404, "M4_REVIEW_KHONG_THAY"), (login, r))
        self.assertEqual(self.admin.execute("SELECT count(*) FROM m4.review_run WHERE khoa LIKE %s", (self.K("ngoai-") + "%",)).fetchone()[0], 0)

    # ------------------------------------------------------------------ H05 FIX01 R3: GET/đổi vai không chờ CPU; thao tác giữ danh tính lúc gửi
    def test_h05_get_doi_vai_song_song_luc_tinh(self):
        self.can_worker()
        if "tep" not in self.s:
            self.skipTest("H03 chưa có tệp — NOT_RUN")
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        vao, tha = threading.Event(), threading.Event()
        goc = XayDungK2._chay_worker

        def cho(svc, thu_muc):  # giữ tiến trình tính "đang chạy" có kiểm soát; vẫn chạy worker thật sau khi thả
            vao.set()
            tha.wait(600)
            return goc(svc, thu_muc)
        sid = self.phien(A1)
        st, d = self.ds(sid, tep_id=self.s["tep"], che_do="L1", o_dich="TH!C1")
        self.assertEqual(st, 200, d)
        than = {"du_an_id": self.du_an("DA_XD_A1"), "tep_id": self.s["tep"], "che_do": "L1", "dot_id": None, "o_dich": "TH!C1",
                "expected_basis": d["co_so"]["basis_sha256"], "khoa": self.K("song-song")}
        kq = {}
        with patch.object(XayDungK2, "_chay_worker", cho):
            t = threading.Thread(target=lambda: kq.update(r=self.goi("/api/m4/review/chay", than, sid)))
            t.start()
            try:
                self.assertTrue(vao.wait(600), "worker chưa bắt đầu")
                t0 = time.monotonic()
                st, s, _, _ = self.goi("/api/m4", cookie=sid)  # GET thường của module trong lúc tính
                self.assertEqual(st, 200, s)
                st, r = self.ds(sid)
                self.assertEqual(st, 200, r)
                st, r, _, _ = self.goi("/api/m4/danh-tinh", {"dang_nhap": REVIEW}, sid)  # đổi vai CÙNG phiên trong lúc tính
                self.assertEqual((st, r), (200, {"dang_nhap": REVIEW}))
                self.assertLess(time.monotonic() - t0, 60, "GET/đổi vai bị chặn bởi thao tác Review đang tính")
            finally:
                tha.set()
                t.join(1200)
        st, r = kq["r"][0], kq["r"][1]
        self.assertEqual(st, 200, r)
        self.assertIn(r["trang_thai"], ("SUCCEEDED", "PARTIAL"), r)
        # danh tính của thao tác là danh tính lúc gửi (A1), không đổi theo vai mới của phiên
        self.assertEqual(self.admin.execute("SELECT tao_boi FROM m4.review_run WHERE id = %s", (r["run_id"],)).fetchone()[0], A1)

    def test_h06_tai_san_co_api_tat_vung(self):
        st, js, _, _ = self.goi("/m4/review.js", token=False)
        self.assertEqual(st, 200)
        self.assertIn(b"tat,", js)  # shell gọi tat() ngay lúc đổi tab/HĐ/đợt (R7)
        st, m4, _, _ = self.goi("/m4.js", token=False)
        self.assertIn(b"tatReview()", m4)
        # FIX02 F5: tài sản THẬT do máy chủ phục vụ mount Review sau khi khung đã gắn vào document; F6: lệnh mang thế hệ form của ý định gốc
        ve = m4[m4.index(b"function veHd()"):]
        self.assertLess(ve.index(b"box.replaceChildren(card);"), ve.index(b'if (tab === "review") veReview(noi);'))
        self.assertIn(b"async function lenh(path, body, ok, f, gf = genForm)", js)
        self.assertIn(b"const ui = () => f() && gf === genForm;", js)
        # FIX03 F2/F3 trên tài sản thật do máy chủ phục vụ: làm mới GET mang thế hệ form trong fence chung; nút báo cáo là mảng phẳng các nút thật
        self.assertIn(b"const dung = () => e === ep && vungSong() && g === genDs && key === selKey() && fs();", js)
        self.assertIn(b'"LOG"].flatMap(l => art.filter(a => a.loai === l).map(a =>', js)

    def test_h07_artifact_dang_ky_tai_that(self):
        """FIX03 F3 (dữ liệu nền cho nút): lần chạy L1 thật có danh sách artifact không rỗng; MỖI artifact báo cáo tải qua route quyền hiện hành
        ra bytes không rỗng đúng hash/độ dài đã đăng ký. Không tự tạo tệp/artifact; nút DOM thật vẫn cần GUI của Root."""
        self.can_worker()
        if "run" not in self.s:
            self.skipTest("H03 chưa có lần chạy — NOT_RUN")
        sid = self.phien(A1)
        st, ct, _, _ = self.goi("/api/m4/review/" + self.s["run"], cookie=sid)
        self.assertEqual(st, 200, ct)
        bao_cao = [a for a in ct["artifact"] if a["loai"].startswith("REPORT_")]
        self.assertTrue({"REPORT_L1", "REPORT_L1_NGUON"} <= {a["loai"] for a in bao_cao}, ct["artifact"])
        for a in bao_cao:
            st, b, cd, _ = self.goi(f"/api/m4/review/{self.s['run']}/tep/{a['id']}", cookie=sid)
            self.assertEqual(st, 200, a)
            self.assertTrue(len(b) > 0)
            self.assertEqual((hashlib.sha256(b).hexdigest(), len(b)), (a["raw_sha256"], a["byte_length"]), a)
            self.assertIn("attachment", cd or "")


if __name__ == "__main__":
    unittest.main()
