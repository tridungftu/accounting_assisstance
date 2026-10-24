"""M4-02B — kiểm HTTP thật route Chứng từ L3 trên LocalApp/LocalServer + PostgreSQL DEMO mới. CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN_CODE_ONLY).

Cùng khung test_m4_review_http: KHO_PG_DSN_TEST qua env lúc chạy (không .env/var, không hardcode credentials); DB mới `kho_test_m4cth_*` migrate 1–22,
seed CRM + M4 DEMO; login ứng dụng tạm IN ROLE app_web + admin DSN cho factory đường tin cậy; HTTP loopback cổng ngẫu nhiên, cùng token/cookie như
trình duyệt. Mỗi tài nguyên (kết nối, env patch, server, luồng) đăng ký cleanup NGAY sau khi tạo — raise giữa setUpClass vẫn dừng server/đóng kết nối
do test sở hữu. Không DROP/DELETE/TRUNCATE/cleanup dữ liệu. Thiếu driver/DSN → skip = NOT_RUN; ca chạy worker cần lõi nguồn + openpyxl + python-docx.
Không chứng minh trình duyệt/hiển thị (Root kiểm GUI riêng; luồng DOM giả lập ở tests/m4_02b_async.cjs).

H01 tài sản: /m4/chung-tu.js đúng một route, no-store, không dùng chèn HTML, đúng bytes tệp; /m4.js nạp /m4/chung-tu.js và mount sau khi khung gắn DOM.
H02 phiên/token/tham số (đúng validator thật): thiếu token → 403 SESSION_TOKEN; query lạ/lặp ở list, CHI TIẾT và TẢI → 400 M4_YEU_CAU_SAI; body có
    trường authority cấp đỉnh (actor/phap_nhan_id/path/raw_sha256) → 403 M4_CLIENT_AUTHORITY; trường lạ cấp đỉnh (vd tai_lieu ở route chạy) → 400
    M4_YEU_CAU_SAI; authority LỒNG trong mục sửa (route sua) → 403; run lạ → 404.
H03 SOAN qua HTTP: dựng HĐ/BOQ/đợt/tệp qua route M17 → list (basis) → chạy → chi tiết → tải REPORT_L3 đúng hash + attachment + no-store; replay →
    cùng run; đổi body cùng khóa → 409; basis cũ → 409 M4_CHUNG_TU_CO_SO_DOI; sửa → revision 1; Chạy lại revision cũ → 409; Chạy lại → run con.
H04 phạm vi: B1 (khác PN) và A2 (cùng PN khác dự án) → 404 list/chi tiết/tải + chạy/sửa; reviewer trên đợt nháp → 404 list/chi tiết, 403 chạy;
    XEM-only → 200 list (không basis), 403 chạy/sửa; không tạo run; lỗi không lộ tên tệp.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import secrets
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote, urlencode

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.kiem_chung import fixtures_m4 as F
from kho_tri_thuc.m4 import nguon_review as NR
from tests.test_m4_02b_k2 import GN, NT_BANG, NT_DAU
from tests.test_m4_02b_pure import _docx, _docx_bytes, _xlsx_bytes, openpyxl
from tests.test_m4_review_http import CAU_HINH_FIXTURE

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
A1, A2, B1, REVIEW, XEM = "MO_PHONG_DU_AN_A1", "MO_PHONG_DU_AN_A2", "MO_PHONG_DU_AN_B1", "MO_PHONG_REVIEW_M4", "MO_PHONG_XEM_M4"


def _nguon_da_nap() -> bool:
    return NR.GOC.is_dir() and all((NR.GOC / rel).is_file() for rel in NR.PIN)


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test HTTP M4-02B không chạy (NOT_RUN, không tính đạt)")
class M4ChungTuHttp(unittest.TestCase):
    """Các ca chạy theo thứ tự tên h01…h04 trên MỘT DB/một máy chủ; trạng thái qua cls.s."""

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.k2 import crm_demo, m4_demo
        cls.db = "kho_test_m4cth_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        cls.version = pg.migrate(cls.admin)
        crm_demo.khoi_tao(cls.admin)
        cls.seed = m4_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_m4cth_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE IN ROLE app_web")
        app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        cls.env = patch.dict(os.environ, {LocalApp.CRM_ENV: app_dsn, LocalApp.CRM_ENV_ADMIN: cls.dsn, LocalApp.CRM_ENV_DB_KIEM_THU: "1"})
        cls.env.start()
        cls.addClassCleanup(cls.env.stop)
        tam = Path(tempfile.mkdtemp(prefix="ktt_m4ct_http_"))  # giữ lại
        (tam / "cau_hinh_fixture.toml").write_text(CAU_HINH_FIXTURE, encoding="utf-8")
        cls.app = LocalApp(tam / "cau_hinh_fixture.toml", tam / "web")
        cls.server = LocalServer(cls.app, 0)
        cls.addClassCleanup(cls.server.server_close)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls._dung_server)  # chạy TRƯỚC server_close (LIFO): shutdown → join có hạn
        cls.run_id = uuid.uuid4().hex[:8]
        cls.s = {}

    @classmethod
    def _dung_server(cls):
        cls.server.shutdown()
        cls.thread.join(5)

    # ------------------------------------------------------------------ helpers (cùng khung test_m4_review_http)
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
        return f"m4cth-{self.run_id}-{ten}"

    def q(self, sql, params=()):
        return self.admin.execute(sql, params).fetchone()[0]

    def du_an(self, ma="DA_XD_A1"):
        return str(self.q("SELECT id FROM master.du_an WHERE ma_junsky = %s", (ma,)))

    def ok(self, path, body, sid):
        st, r, _, _ = self.goi(path, body, sid)
        self.assertEqual(st, 200, (path, r))
        return r

    def tep(self, sid, raw, ten, media, vai, khoa):
        info = quote(json.dumps({"du_an_id": self.du_an(), "vai_tro": vai, "ten": ten, "media_type": media, "khoa": self.K(khoa)}))
        st, t, _, _ = self.goi("/api/m4/tep", cookie=sid, raw=raw, headers={"X-M4-Info": info, "Content-Type": "application/octet-stream"})
        self.assertEqual(st, 200, t)
        return t["tep_id"]

    def ds(self, sid, **q):
        st, r, _, _ = self.goi("/api/m4/chung-tu?" + urlencode(q), cookie=sid)
        return st, r

    def can_worker(self):
        if not (_nguon_da_nap() and openpyxl is not None and _docx is not None):
            self.skipTest("Lõi nguồn Review chưa nạp hoặc thiếu openpyxl/python-docx — NOT_RUN")

    # ------------------------------------------------------------------ H01
    def test_h01_tai_san(self):
        self.assertEqual(self.version, 22)
        st, js, _, cc = self.goi("/m4/chung-tu.js", token=False)
        self.assertEqual((st, cc), (200, "no-store"))
        self.assertEqual(js, (Path(NR.__file__).parent / "giao_dien" / "chung_tu.js").read_bytes())
        self.assertIn(b'dangKyVai("m4_chung_tu"', js)
        self.assertIn(b"window.kttM4ChungTu", js)
        dung_html = re.compile(rb"""\.\s*(?:innerHTML|outerHTML)\b|\[\s*["'](?:innerHTML|outerHTML)["']\s*\]|insertAdjacentHTML\s*\(|document\s*\.\s*write\s*\(""")
        self.assertIsNone(dung_html.search(js), dung_html.search(js))
        self.assertIsNotNone(dung_html.search(b"x.innerHTML = s"))  # đối chứng
        for xau in ("/m4/chung_tu.js", "/m4/chung-tu.css", "/m4/review_goc/may_chu/giao_dien/chung_tu.js", "/m4/../m4.py", "/m4/chung-tu.js/x"):
            st, _, _, _ = self.goi(xau, token=False)
            self.assertNotEqual(st, 200, xau)  # không static server tổng quát
        st, m4, _, _ = self.goi("/m4.js", token=False)
        self.assertIn(b"/m4/chung-tu.js", m4)
        self.assertIn(b"kttM4ChungTu", m4)
        ve = m4[m4.index(b"function veHd()"):]
        self.assertLess(ve.index(b"box.replaceChildren(card);"), ve.index(b"veChungTu(noi)"))  # mount sau khi khung gắn vào document

    # ------------------------------------------------------------------ H02
    def test_h02_phien_token_tham_so(self):
        sid = self.phien(A1)
        d, r0 = str(uuid.uuid4()), str(uuid.uuid4())
        st, r, _, _ = self.goi("/api/m4/chung-tu?dot_id=" + d, cookie=sid, token=False)
        self.assertEqual((st, r.get("error")), (403, "SESSION_TOKEN"))
        st, r = self.ds(sid, dot_id=d, actor=A1)
        self.assertEqual((st, r.get("error")), (400, "M4_YEU_CAU_SAI"))
        st, r, _, _ = self.goi(f"/api/m4/chung-tu?dot_id={d}&dot_id={d}", cookie=sid)
        self.assertEqual((st, r.get("error")), (400, "M4_YEU_CAU_SAI"))
        st, r = self.ds(sid, dot_id=d)
        self.assertEqual((st, r.get("error")), (404, "M4_CHUNG_TU_KHONG_THAY"))
        # chi tiết / tải: KHÔNG nhận tham số truy vấn nào (lạ hoặc lặp) — 400 trước mọi tra cứu
        for path in (f"/api/m4/chung-tu/{r0}?actor={A1}", f"/api/m4/chung-tu/{r0}?x=1&x=2", f"/api/m4/chung-tu/{r0}/tep/{uuid.uuid4()}?raw_sha256=a"):
            st, r, _, _ = self.goi(path, cookie=sid)
            self.assertEqual((st, r.get("error")), (400, "M4_YEU_CAU_SAI"), path)
        chay = {"dot_id": d, "revision": 0, "expected_basis": "0" * 64, "khoa": self.K("auth")}
        for them in ({"actor": "x"}, {"phap_nhan_id": str(uuid.uuid4())}, {"path": "C:/x.docx"}, {"raw_sha256": "a" * 64}):
            st, r, _, _ = self.goi("/api/m4/chung-tu/chay", {**chay, **them}, sid)
            self.assertEqual((st, r.get("error")), (403, "M4_CLIENT_AUTHORITY"), them)
        st, r, _, _ = self.goi("/api/m4/chung-tu/chay", {**chay, "tai_lieu": [{"tep_id": d}]}, sid)  # trường lạ của route chạy (không phải authority)
        self.assertEqual((st, r.get("error")), (400, "M4_YEU_CAU_SAI"))
        st, r, _, _ = self.goi("/api/m4/chung-tu/sua", {"run_id": r0, "revision": 0, "tai_lieu": [{"tep_id": d, "so": "1", "raw_sha256": "a" * 64}],
                                                         "expected_basis": "0" * 64, "ly_do": "x", "khoa": self.K("long")}, sid)
        self.assertEqual((st, r.get("error")), (403, "M4_CLIENT_AUTHORITY"))  # authority lồng trong mục sửa
        st, r, _, _ = self.goi(f"/api/m4/chung-tu/{uuid.uuid4()}", cookie=sid)
        self.assertEqual((st, r.get("error")), (404, "M4_CHUNG_TU_KHONG_THAY"))
        st, r, _, _ = self.goi(f"/api/m4/chung-tu/{uuid.uuid4()}/tep/{uuid.uuid4()}", cookie=sid)
        self.assertEqual(st, 404)
        st, r, _, _ = self.goi("/api/m4/chung-tu/chay-lai", {"run_id": str(uuid.uuid4()), "revision": 0, "expected_basis": "0" * 64, "khoa": self.K("x")}, sid)
        self.assertEqual((st, r.get("error")), (404, "M4_CHUNG_TU_KHONG_THAY"))
        self.s["sid_a1"] = sid

    # ------------------------------------------------------------------ H03
    def test_h03_soan_qua_http(self):
        self.can_worker()
        sid = self.s.get("sid_a1") or self.phien(A1)
        hd = self.ok("/api/m4/hop-dong/tao", {"du_an_id": self.du_an(), "so_hop_dong": f"123/2025-{self.run_id}", "ten": "Gói chứng từ HTTP DEMO",
                                              "khoa": self.K("hd")}, sid)["hop_dong_id"]
        rev_hd = lambda: self.q("SELECT revision FROM m4.ho_so_hop_dong WHERE hop_dong_id = %s", (hd,))  # noqa: E731
        boq_tep = self.tep(sid, F.boq_xlsx(F.BOQ_GOC), "BOQ.xlsx", F.MEDIA_XLSX, "BOQ", "boq-tep")
        b = self.ok("/api/m4/boq/nhap", {"hop_dong_id": hd, "revision": rev_hd(), "tep_id": boq_tep, "phu_luc_id": None, "sheet": "BOQ", "hang_tieu_de": 1,
                                         "cot": dict(F.BOQ_COT), "khoa": self.K("boq")}, sid)
        self.assertEqual(b["trang_thai"], "DA_MAP", b)
        dot = self.ok("/api/m4/dot/tao", {"hop_dong_id": hd, "so_dot": 1, "ngay_nghiem_thu": "2026-03-01", "khoa": self.K("dot")}, sid)["dot_id"]
        muc = [r[0] for r in self.admin.execute("SELECT ma FROM m4.danh_muc_ho_so_dot ORDER BY ma").fetchall()]
        nt = self.tep(sid, _docx_bytes(NT_DAU, NT_BANG), "bb_nghiem_thu.docx", F.MEDIA_DOCX, "HO_SO_DOT", "nt")
        gn = self.tep(sid, _xlsx_bytes([("GiaoNhan", GN)]), "bb_giao_nhan.xlsx", F.MEDIA_XLSX, "HO_SO_DOT", "gn")
        for i, t in enumerate((nt, gn)):
            self.ok("/api/m4/dot/gan-tep", {"dot_id": dot, "revision": self.q("SELECT revision FROM m4.dot WHERE id = %s", (dot,)), "tep_id": t,
                                            "muc": muc[i], "khoa": self.K(f"gan-{i}")}, sid)
        st, d = self.ds(sid, dot_id=dot)
        self.assertEqual(st, 200, d)
        cs = d["co_so"]
        self.assertTrue(cs["san_sang"], cs)
        self.assertEqual((cs["quyen"], cs["revision"]), ("SOAN", 0))
        self.assertEqual({t["tep_id"] for t in d["tai_lieu"]}, {nt, gn})
        than = {"dot_id": dot, "revision": 0, "expected_basis": cs["basis_sha256"], "khoa": self.K("chay")}
        r = self.ok("/api/m4/chung-tu/chay", than, sid)
        self.assertIn(r["trang_thai"], ("SUCCEEDED", "PARTIAL"), r)
        st, lai, _, _ = self.goi("/api/m4/chung-tu/chay", than, sid)  # bấm lặp/timeout: gửi lại đúng body + khóa
        self.assertEqual((st, lai["run_id"], lai["lap_lai"]), (200, r["run_id"], True))
        st, x, _, _ = self.goi("/api/m4/chung-tu/chay", {**than, "expected_basis": "e" * 64}, sid)
        self.assertEqual((st, x.get("error")), (409, "M4_IDEMPOTENCY_KHAC"))
        st, x, _, _ = self.goi("/api/m4/chung-tu/chay", {**than, "expected_basis": "e" * 64, "khoa": self.K("cu")}, sid)
        self.assertEqual((st, x.get("error")), (409, "M4_CHUNG_TU_CO_SO_DOI"))
        st, ct, _, _ = self.goi("/api/m4/chung-tu/" + r["run_id"], cookie=sid)
        self.assertEqual(st, 200, ct)
        kq = ct["ket_qua"]
        self.assertEqual(set(kq["coverage"]), {"C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "TAI_LIEU", "DONG_HANG", "CAN_CU"})
        self.assertEqual(set(kq["ket_qua"]["so_sanh"]), {h["khoa"] for h in kq["ket_qua"]["hang_muc"]})
        rep = next(a for a in ct["artifact"] if a["loai"] == "REPORT_L3")
        st, raw, cd, cc = self.goi(f"/api/m4/chung-tu/{r['run_id']}/tep/{rep['id']}", cookie=sid)
        self.assertEqual((st, hashlib.sha256(raw).hexdigest(), len(raw), cc), (200, rep["raw_sha256"], rep["byte_length"], "no-store"))
        self.assertIn("attachment", cd or "")
        st, _, _, _ = self.goi(f"/api/m4/chung-tu/{r['run_id']}/tep/{rep['id']}", cookie=sid, token=False)
        self.assertEqual(st, 403)
        # sửa metadata → revision 1 (cha nguyên) → Chạy lại → run con
        sua = self.ok("/api/m4/chung-tu/sua", {"run_id": r["run_id"], "revision": 0, "tai_lieu": [{"tep_id": nt, "so": "01/BBNT-2026/SUA"}],
                                                "expected_basis": cs["basis_sha256"], "ly_do": "Số BB theo bản gốc ký", "khoa": self.K("sua")}, sid)
        self.assertEqual(sua["revision"], 1)
        st, d2 = self.ds(sid, dot_id=dot)
        self.assertEqual((st, d2["co_so"]["revision"]), (200, 1))
        st, x, _, _ = self.goi("/api/m4/chung-tu/chay-lai", {"run_id": r["run_id"], "revision": 0, "expected_basis": d2["co_so"]["basis_sha256"],
                                                              "khoa": self.K("lai-cu")}, sid)
        self.assertEqual((st, x.get("error")), (409, "M4_REVISION_CU"))
        con = self.ok("/api/m4/chung-tu/chay-lai", {"run_id": r["run_id"], "revision": 1, "expected_basis": d2["co_so"]["basis_sha256"],
                                                    "khoa": self.K("lai")}, sid)
        self.assertNotEqual(con["run_id"], r["run_id"])
        st, ct2, _, _ = self.goi("/api/m4/chung-tu/" + con["run_id"], cookie=sid)
        self.assertEqual((st, ct2["run"]["parent_run_id"]), (200, r["run_id"]))
        st, ct1, _, _ = self.goi("/api/m4/chung-tu/" + r["run_id"], cookie=sid)
        self.assertEqual(ct1["ket_qua"]["ket_qua_sha256"], kq["ket_qua_sha256"])  # kết quả cha nguyên
        self.s.update(dot=dot, run=r["run_id"], rep=rep["id"], basis=d2["co_so"]["basis_sha256"], nt=nt)

    # ------------------------------------------------------------------ H04
    def test_h04_ngoai_pham_vi(self):
        if "run" not in self.s:
            self.skipTest("H03 chưa có lần chạy — NOT_RUN")
        truoc = self.q("SELECT count(*) FROM m4.chung_tu_run")
        doc_duoc = (f"/api/m4/chung-tu?dot_id={self.s['dot']}", f"/api/m4/chung-tu/{self.s['run']}", f"/api/m4/chung-tu/{self.s['run']}/tep/{self.s['rep']}")
        sua = {"run_id": self.s["run"], "revision": 1, "tai_lieu": [{"tep_id": self.s["nt"], "bo": True}], "expected_basis": self.s["basis"], "ly_do": "x"}
        chay = {"dot_id": self.s["dot"], "revision": 1, "expected_basis": self.s["basis"]}
        for login in (B1, A2, REVIEW):
            sid = self.phien(login)
            for path in doc_duoc:
                st, r, _, _ = self.goi(path, cookie=sid)
                self.assertEqual(st, 404, (login, path, r))
                self.assertNotIn(b"bb_nghiem_thu", json.dumps(r, ensure_ascii=False).encode("utf-8") if isinstance(r, dict) else r)
            st, r, _, _ = self.goi("/api/m4/chung-tu/chay", {**chay, "khoa": self.K("ngoai-" + login)}, sid)
            mong = (403, "M4_CHUNG_TU_PHAM_VI") if login == REVIEW else (404, "M4_CHUNG_TU_KHONG_THAY")  # reviewer: đợt chưa nộp
            self.assertEqual((st, r.get("error")), mong, (login, r))
            st, r, _, _ = self.goi("/api/m4/chung-tu/sua", {**sua, "khoa": self.K("sua-" + login)}, sid)
            self.assertEqual((st, r.get("error")), (404, "M4_CHUNG_TU_KHONG_THAY"), (login, r))
        sid = self.phien(XEM)  # XEM-only: đọc được, không có basis/nút chạy, mọi lệnh 403
        st, d = self.ds(sid, dot_id=self.s["dot"])
        self.assertEqual((st, d["co_so"]["san_sang"], d["co_so"]["quyen"]), (200, False, None))
        self.assertNotIn("basis_sha256", d["co_so"])
        st, r, _, _ = self.goi("/api/m4/chung-tu/chay", {**chay, "khoa": self.K("xem-chay")}, sid)
        self.assertEqual((st, r.get("error")), (403, "M4_CHUNG_TU_PHAM_VI"))
        st, r, _, _ = self.goi("/api/m4/chung-tu/sua", {**sua, "khoa": self.K("xem-sua")}, sid)
        self.assertEqual((st, r.get("error")), (403, "M4_CHUNG_TU_PHAM_VI"))
        self.assertEqual(self.q("SELECT count(*) FROM m4.chung_tu_run"), truoc)


if __name__ == "__main__":
    unittest.main()
