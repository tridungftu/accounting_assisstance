"""CRM-41-02 — kiểm HTTP thật G1/G7/S6 trên LocalApp/LocalServer + PostgreSQL DEMO mới (CODE_ONLY: coder viết, CHƯA CHẠY — NOT_RUN_CODE_ONLY).

Chạy khi Root cấp KHO_PG_DSN_TEST qua env lúc chạy (DSN chủ CSDL; không đọc .env/var, không hardcode credentials). DB MỚI `kho_test_crmg_*` migrate
mặc định (tối thiểu M0018), seed CRM DEMO + crm_g_demo (actor MO_PHONG_CRM_G_*, danh mục, phân công — KHÔNG seed duyệt); login ứng dụng tạm (NOSUPERUSER
NOBYPASSRLS IN ROLE app_web) + admin DSN cho factory kết nối chủ bảng hiện hành của máy chủ. HTTP loopback cổng ngẫu nhiên, cùng token/cookie như
trình duyệt; vai đổi qua đúng route phiên CRM hiện có. Không mock quyền/dịch vụ sản phẩm (chỉ bọc bộ đọc DOCX THẬT để giữ request ở bước parse
trong ca đồng thời). Không DROP/DELETE/TRUNCATE/cleanup — DB/role/thư mục giữ làm bằng chứng. Thiếu driver/DSN → skip = NOT_RUN (không tính đạt).

Ánh xạ: A02 g02–g06 · A03 g05/g08/g09 · A04 g07 · A05 g03/g10/g11 · A06 g12 · A07 toàn bộ (HTTP/phiên/token/tải về hash). Không chứng minh GUI.
"""

from __future__ import annotations

import hashlib
import http.client
import io
import json
import os
import secrets
import tempfile
import threading
import time
import unittest
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
TAI, KT, CFO, BH = "MO_PHONG_CRM_G_TAI_A", "MO_PHONG_CRM_G_KT_A", "MO_PHONG_CRM_G_CFO_A", "MO_PHONG_CRM_G_BH_A"
CFO_NO_V4, KT_NO_CRM, TAI_REVOKED, CFO_B = "MO_PHONG_CRM_G_CFO_NO_V4_A", "MO_PHONG_CRM_G_KT_NO_CRM_A", "MO_PHONG_CRM_G_TAI_REVOKED_A", "MO_PHONG_CRM_G_CFO_B"
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

# ---------------------------------------------------------------------- DOCX tổng hợp DEMO (3 ô: tách run, ô bảng, header) — tạo trong test
W_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
REL_NS, REL_T = "http://schemas.openxmlformats.org/package/2006/relationships", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"


def _p(*runs):
    return "<w:p>" + "".join(f'<w:r><w:t xml:space="preserve">{t}</w:t></w:r>' for t in runs) + "</w:p>"


def mau_docx(ghi_chu: str = "DEMO") -> bytes:
    than = (_p("Hợp đồng số ", "{{so_", "hop_dong}}", f" — {ghi_chu}")
            + f"<w:tbl><w:tr><w:tc>{_p('Bên thuê: {{ho_ten}}')}</w:tc></w:tr></w:tbl>"
            + '<w:sectPr><w:headerReference w:type="default" r:id="rIdH"/></w:sectPr>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/></Types>')
        z.writestr("_rels/.rels", XML + f'<Relationships xmlns="{REL_NS}"><Relationship Id="rId1" Type="{REL_T}officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", XML + f"<w:document {W_NS}><w:body>{than}</w:body></w:document>")
        z.writestr("word/_rels/document.xml.rels", XML + f'<Relationships xmlns="{REL_NS}"><Relationship Id="rIdH" Type="{REL_T}header" Target="header1.xml"/></Relationships>')
        z.writestr("word/header1.xml", XML + f"<w:hdr {W_NS}>{_p('Ngày ký: {{ngay_ky}}')}</w:hdr>")
    return buf.getvalue()


BAN_DO_DEMO = {"so_hop_dong": "so_hop_dong", "ho_ten": "ten_hien_thi_demo", "ngay_ky": "ngay_ky"}  # ho_ten → trường khác tên


def hom_nay():
    return datetime.now(timezone(timedelta(hours=7))).date()


def _dong(conn) -> None:
    """Đóng kết nối do test sở hữu; idempotent (None/đã đóng → bỏ qua)."""
    if conn is not None and not conn.closed:
        conn.close()


def ma_loi(exc) -> str:
    return ((getattr(getattr(exc, "diag", None), "message_primary", "") or str(exc)).split(":", 1)[0]).strip()


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test HTTP CRM-41-02 không chạy (NOT_RUN, không tính đạt)")
class CrmGHttp(unittest.TestCase):
    """Các ca chạy theo thứ tự tên g01…g13 trên MỘT DB/một máy chủ; trạng thái qua cls.s."""

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.k2 import crm_demo, crm_g_demo
        cls.db = "kho_test_crmg_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        # T02: mỗi tài nguyên do test sở hữu được đăng ký dọn NGAY khi tạo (addClassCleanup chạy cả khi setUpClass lỗi giữa chừng, LIFO,
        # idempotent). Chỉ đóng kết nối/socket/thread/env của chính test — GIỮ DB/role/thư mục/artifact làm bằng chứng.
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)
        cls.addClassCleanup(_dong, cls.admin)
        cls.version = pg.migrate(cls.admin)
        crm_demo.khoi_tao(cls.admin)
        cls.seed = crm_g_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_crmg_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE IN ROLE app_web")
        cls.app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        cls.env = patch.dict(os.environ, {LocalApp.CRM_ENV: cls.app_dsn, LocalApp.CRM_ENV_ADMIN: cls.dsn, LocalApp.CRM_ENV_DB_KIEM_THU: "1"})
        cls.env.start()
        cls.addClassCleanup(cls.env.stop)
        cls.tam = Path(tempfile.mkdtemp(prefix="ktt_crmg_http_"))  # giữ lại
        (cls.tam / "cau_hinh_fixture.toml").write_text(CAU_HINH_FIXTURE, encoding="utf-8")
        cls.app = LocalApp(cls.tam / "cau_hinh_fixture.toml", cls.tam / "web")
        cls.addClassCleanup(cls._dong_ket_noi_app)  # kết nối do app tạo trong lúc test (CRM thường + chủ bảng của service G)
        cls.server = LocalServer(cls.app, 0)
        cls.addClassCleanup(cls.server.server_close)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls._dung_server)
        cls.run_id = uuid.uuid4().hex[:8]
        cls.kho = cls.app.root / "crm-g" / "crm-mau"
        cls.s = {}

    @classmethod
    def _dung_server(cls):
        cls.server.shutdown()
        cls.thread.join(10)

    @classmethod
    def _dong_ket_noi_app(cls):
        crm = getattr(cls.app, "_crm", None)
        g = cls.app.__dict__.get("_crm_g")
        _dong(getattr(g, "conn_tin_cay", None))
        _dong(getattr(crm, "conn", None))

    def cho_bi_chan(self, pid: int, boi: int, han: float = 30.0):
        """T03: chờ đến khi backend `pid` THỰC SỰ bị `boi` chặn (pg_blocking_pids) — quan sát bằng kết nối observer trên chính DB DEMO mới.
        Trả (wait_event_type, wait_event, [locktype chưa cấp], query). Hết hạn → FAIL (không coi timeout/sleep là bằng chứng)."""
        het = time.monotonic() + han
        while time.monotonic() < het:
            chan = self.q("SELECT pg_blocking_pids(%s)", (pid,)) or []
            if boi in chan:
                hd = self.admin.execute("SELECT wait_event_type, wait_event, query FROM pg_stat_activity WHERE pid = %s", (pid,)).fetchone()
                khoa = sorted(r[0] for r in self.admin.execute("SELECT locktype FROM pg_locks WHERE pid = %s AND NOT granted", (pid,)).fetchall())
                return hd[0], hd[1], khoa, hd[2]
            time.sleep(0.05)
        self.fail(f"backend {pid} không bị {boi} chặn trong {han}s — không có bằng chứng chờ đúng khóa")

    # ------------------------------------------------------------------ helpers
    def goi(self, path, body=None, cookie=None, token=True, raw=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=180)
        h = {"X-KTT-Token": self.app.token} if token else {}
        if cookie:
            h["Cookie"] = f"{self.app.CRM_COOKIE}={cookie}"
        h.update(headers or {})
        data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
        if body is not None and raw is None:
            h["Content-Type"] = "application/json"
        c.request("POST" if data is not None else "GET", path, body=data, headers=h)
        r = c.getresponse()
        out, ct, ck = r.read(), r.getheader("Content-Type") or "", r.getheader("Set-Cookie")
        c.close()
        return r.status, (json.loads(out or b"{}") if ct.startswith("application/json") else out), ck

    def phien(self, login):
        """Phiên thật: cookie do GET /api/crm cấp, vai đổi qua route phiên CRM hiện có (không actor trong body lệnh)."""
        st, s, ck = self.goi("/api/crm")
        self.assertEqual(st, 200, s)
        sid = ck.split(";", 1)[0].split("=", 1)[1]
        st, r, _ = self.goi("/api/crm/danh-tinh", {"dang_nhap": login}, sid)
        self.assertEqual((st, r), (200, {"dang_nhap": login}))
        return sid

    def sid(self, login):
        if login not in self.s.setdefault("sid", {}):
            self.s["sid"][login] = self.phien(login)
        return self.s["sid"][login]

    def K(self, ten):
        return f"g-{self.run_id}-{ten}"

    def ok(self, login, path, body):
        st, r, _ = self.goi("/api/crm/" + path, body, self.sid(login))
        self.assertEqual(st, 200, (login, path, r))
        return r

    def loi(self, login, path, body, status, ma):
        st, r, _ = self.goi("/api/crm/" + path, body, self.sid(login))
        self.assertEqual((st, r.get("error") if isinstance(r, dict) else r), (status, ma), (login, path, r))
        return r

    def tai(self, login, raw, loai, ma_mau, khoa, ten="mau_hd.docx", them=None):
        info = {"loai_hinh_id": loai, "ma_mau": ma_mau, "ten_tep": ten, "khoa": self.K(khoa), **(them or {})}
        return self.goi("/api/crm/mau/tai", cookie=self.sid(login), raw=raw,
                        headers={"X-CRM-G-Info": quote(json.dumps(info)), "Content-Type": "application/octet-stream"})[:2]

    def ct(self, login, pb, status=200):
        st, r, _ = self.goi("/api/crm/mau/" + pb, cookie=self.sid(login))
        self.assertEqual(st, status, r)
        return r

    def q(self, sql, params=()):
        return self.admin.execute(sql, params).fetchone()[0]

    def loai_a(self):
        return str(self.q("""SELECT l.id FROM master.loai_hinh_doanh_thu l JOIN master.phap_nhan p ON p.id = l.phap_nhan_id
                             WHERE p.ma = 'PN_DEMO_A' AND l.ma = 'DT-KCN-THUE-DAT-DEMO' AND l.phien_ban = 2"""))

    def du_an(self, ma):
        return str(self.q("SELECT id FROM master.du_an WHERE ma_junsky = %s", (ma,)))

    def dem(self, kho=None):
        """Quan sát: hàng/biên nhận/nhật ký/sequence/K5/tệp — dùng chứng minh replay và từ chối 0 delta."""
        kho = kho or self.kho
        return {"pb": self.q("SELECT count(*) FROM master.crm_mau_phien_ban"), "tep": self.q("SELECT count(*) FROM master.crm_mau_tep"),
                "goc": self.q("SELECT count(*) FROM master.crm_mau"), "ax": self.q("SELECT count(*) FROM master.crm_mau_anh_xa"),
                "kt": self.q("SELECT count(*) FROM master.crm_mau_kiem_tra"), "bn": self.q("SELECT count(*) FROM master.crm_g_bien_nhan"),
                "nk": self.q("SELECT count(*) FROM nhat_ky.su_kien"), "seq": self.q("SELECT last_value FROM nhat_ky.su_kien_id_seq"),
                "viec": self.q("SELECT count(*) FROM kho.viec_can_duyet"), "dm": self.q("SELECT count(*) FROM master.crm_danh_muc_truong"),
                "tep_kho": sorted(p.name for p in kho.iterdir() if p.is_file()) if kho.is_dir() else []}

    # ------------------------------------------------------------------ g01 tài sản, phiên, seed, CRM cũ giữ nguyên
    def test_g01_tai_san_phien_seed(self):
        from kho_tri_thuc.ha_tang import pg_migrations as PM
        self.assertGreaterEqual(self.version, 18)
        self.assertEqual([i + 1 for i, m in enumerate(PM.PG_MIGRATIONS) if tuple(m) == tuple(PM.M0018_CRM_G)], [18])
        ls = self.admin.execute("SELECT version, checksum FROM master.schema_migrations WHERE version <= %s ORDER BY version", (18,)).fetchall()
        self.assertEqual([tuple(x) for x in ls], [(i + 1, PM._hash(m)) for i, m in enumerate(PM.PG_MIGRATIONS[:18])])
        self.assertEqual(self.seed["trang_thai"], "DU", self.seed)
        self.assertEqual(self.seed["danh_muc"], {"TYPE_A_V2": "DA_TAO", "TYPE_B_V2": "DA_TAO"})
        self.assertEqual(self.q("SELECT count(*) FROM master.crm_mau_phien_ban"), 0)  # không seed mẫu/duyệt
        self.assertEqual(self.q("SELECT count(*) FROM master.crm_bo_chuan_phien_ban"), 0)
        st, js, _ = self.goi("/crm_g.js", token=False)
        self.assertEqual(st, 200)
        self.assertIn(b'K.dangKyVai("crm_g"', js)
        st, html, _ = self.goi("/", token=False)
        self.assertIn(b'id="crm-g"', html)
        self.assertIn(b'<script src="/crm_g.js" defer>', html)
        sid = self.sid(TAI)
        st, r, _ = self.goi("/api/crm/mau", token=False, cookie=sid)
        self.assertEqual((st, r.get("error")), (403, "SESSION_TOKEN"))
        st, r, _ = self.goi("/api/crm/mau")  # không cookie phiên
        self.assertEqual((st, r.get("error")), (400, "CRM_PHIEN"))
        st, s, _ = self.goi("/api/crm", cookie=sid)  # CRM-B cũ vẫn chạy (cùng phiên)
        self.assertEqual(st, 200)
        self.assertIn(TAI, {d["dang_nhap"] for d in s["danh_tinh_demo"]})
        st, r, _ = self.goi("/api/crm/mau", {"mau": "KHONG_CO_MAU_NAY"}, sid)  # POST /api/crm/mau = handler #6 cũ, không thuộc G
        self.assertEqual((st, r.get("error")), (400, "CRM_MAU"))
        st, ds, _ = self.goi("/api/crm/mau", cookie=sid)
        self.assertEqual(st, 200, ds)
        self.assertTrue(ds["ghi_nguon"]["san_sang"], ds["ghi_nguon"])
        self.assertEqual([l["id"] for l in ds["loai_hinh"] if l["duoc_tai"]], [self.loai_a()])

    # ------------------------------------------------------------------ g02 tải lên thật + từ chối quyền/authority/hazard
    def test_g02_tai_len(self):
        raw, loai = mau_docx(), self.loai_a()
        truoc = self.dem()
        for login, status, ma in ((BH, 403, "CRM_G_KHONG_CO_QUYEN"), (TAI_REVOKED, 403, "CRM_G_KHONG_CO_QUYEN"),
                                  (KT_NO_CRM, 404, "CRM_G_KHONG_THAY"), (CFO_B, 404, "CRM_G_KHONG_THAY"), (KT, 403, "CRM_G_KHONG_CO_QUYEN")):
            st, r = self.tai(login, raw, loai, "MAU_HD_A", "tai-tu-choi-" + login)
            self.assertEqual((st, r.get("error")), (status, ma), login)
        st, r = self.tai(TAI, raw, loai, "MAU_HD_A", "tai-authority", them={"phap_nhan_id": str(uuid.uuid4())})
        self.assertEqual((st, r.get("error")), (403, "CRM_G_CLIENT_AUTHORITY"))
        st, r = self.tai(TAI, b"khong phai docx", loai, "MAU_HD_A", "tai-sai")
        self.assertEqual((st, r.get("error")), (400, "CRM_MAU_TEP_SAI"))
        self.assertEqual(self.dem(), truoc)  # mọi từ chối: 0 hàng/biên nhận/nhật ký/tệp
        st, r = self.tai(TAI, raw, loai, "MAU_HD_A", "tai-1")
        self.assertEqual(st, 200, r)
        self.assertEqual((r["phien_ban"], r["trang_thai"], r["trang_thai_doc"], r["lap_lai"]), (1, "DRAFT", "DU", False))
        self.assertEqual(r["raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual((self.kho / r["raw_sha256"]).read_bytes(), raw)
        ct = self.ct(TAI, r["phien_ban_id"])
        self.assertEqual({p["ten"]: p["so_lan"] for p in ct["phat_hien"]["placeholders"]}, {"so_hop_dong": 1, "ho_ten": 1, "ngay_ky": 1})
        self.assertEqual([o["loai_phan"] for o in ct["phat_hien"]["occurrences"]], ["THAN", "THAN", "HEADER"])
        self.assertTrue(ct["phat_hien"]["occurrences"][0]["tach_run"])
        st, tep, _ = self.goi("/api/crm/mau/tep/" + r["phien_ban_id"], cookie=self.sid(TAI))
        self.assertEqual((st, hashlib.sha256(tep).hexdigest()), (200, r["raw_sha256"]))  # tải về đúng bytes gốc
        self.ct(BH, r["phien_ban_id"], 404)  # nháp ẩn với bán hàng
        st, _, _ = self.goi("/api/crm/mau/tep/" + r["phien_ban_id"], cookie=self.sid(BH))
        self.assertEqual(st, 404)
        self.s["pb1"], self.s["raw"] = r["phien_ban_id"], raw

    # ------------------------------------------------------------------ g03 replay / đổi H cùng khóa
    def test_g03_replay_va_doi_h(self):
        raw, loai, pb1 = self.s["raw"], self.loai_a(), self.s["pb1"]
        truoc = self.dem()
        st, r = self.tai(TAI, raw, loai, "MAU_HD_A", "tai-1")
        self.assertEqual((st, r["lap_lai"], r["phien_ban_id"]), (200, True, pb1))
        self.assertEqual(self.dem(), truoc)
        st, r = self.tai(TAI, raw, loai, "MAU_HD_KHAC", "tai-1")  # cùng khóa, body khác
        self.assertEqual((st, r.get("error")), (409, "CRM_G_IDEMPOTENCY_KHAC"))
        khac = mau_docx("BYTES KHAC")
        st, r = self.tai(TAI, khac, loai, "MAU_HD_A", "tai-1")
        self.assertEqual((st, r.get("error")), (409, "CRM_G_IDEMPOTENCY_KHAC"))
        self.assertFalse((self.kho / hashlib.sha256(khac).hexdigest()).exists())  # 409 trước parse/blob
        self.assertEqual(self.dem(), truoc)

    # ------------------------------------------------------------------ g04 ánh xạ khác tên + cảnh báo bắt buộc vắng
    def test_g04_anh_xa(self):
        pb = self.s["pb1"]
        tok = self.ct(TAI, pb)["token"]
        self.loi(TAI, "mau/anh-xa", {"version_id": pb, "map": BAN_DO_DEMO, "expected_graph": "0" * 64, "khoa": self.K("map-cu")}, 409, "CRM_G_TOKEN_CU")
        self.loi(TAI, "mau/anh-xa", {"version_id": pb, "map": {**BAN_DO_DEMO, "o_la": None}, "expected_graph": tok, "khoa": self.K("map-thua")}, 400, "CRM_G_ANH_XA_THUA")
        self.loi(TAI, "mau/anh-xa", {"version_id": pb, "map": {**BAN_DO_DEMO, "ho_ten": "khong_co"}, "expected_graph": tok, "khoa": self.K("map-sai")}, 400,
                 "CRM_G_TRUONG_KHONG_CO")
        self.loi(TAI, "mau/anh-xa", {"version_id": pb, "map": BAN_DO_DEMO, "expected_graph": tok, "khoa": self.K("map-a"), "trang_thai": "HIEU_LUC"}, 403,
                 "CRM_G_CLIENT_AUTHORITY")
        self.loi(BH, "mau/anh-xa", {"version_id": pb, "map": BAN_DO_DEMO, "expected_graph": tok, "khoa": self.K("map-bh")}, 404, "CRM_G_KHONG_THAY")
        r = self.ok(TAI, "mau/anh-xa", {"version_id": pb, "map": BAN_DO_DEMO, "expected_graph": tok, "khoa": self.K("map-1")})
        self.assertEqual((r["revision"], r["so_chua_anh_xa"], r["so_sai_kieu"]), (1, 0, 0))
        self.assertEqual([c["truong"] for c in r["canh_bao"]], ["gia_tri_hop_dong"])  # bắt buộc vắng: chỉ cảnh báo
        ax = self.ct(KT, pb)["anh_xa"]
        self.assertEqual({o["ten"]: o["truong"] for o in ax["ban_do"]}, BAN_DO_DEMO)

    # ------------------------------------------------------------------ g05 gửi kiểm → KT trả lại (cùng K5) → gửi lại → KT kiểm
    def test_g05_tra_lai_cung_k5(self):
        pb = self.s["pb1"]
        r = self.ok(TAI, "mau/gui-kiem", {"version_id": pb, "expected_graph": self.ct(TAI, pb)["token"], "khoa": self.K("gui-1")})
        w = r["viec_id"]
        self.assertEqual((r["trang_thai"], self.q("SELECT trang_thai FROM kho.viec_can_duyet WHERE id = %s", (w,))), ("CHO_KIEM", "CHO_DUYET"))
        tok = self.ct(KT, pb)["token"]
        self.loi(KT, "mau/tra-lai", {"version_id": pb, "ly_do": "", "expected_graph": tok, "khoa": self.K("tl-rong")}, 400, "CRM_G_YEU_CAU_SAI")
        self.loi(KT, "mau/tra-lai", {"version_id": pb, "ly_do": "  ", "expected_graph": tok, "khoa": self.K("tl-trang")}, 400, "CRM_G_THIEU_LY_DO")
        self.loi(BH, "mau/tra-lai", {"version_id": pb, "ly_do": "x", "expected_graph": tok, "khoa": self.K("tl-bh")}, 404, "CRM_G_KHONG_THAY")
        self.loi(CFO, "mau/tra-lai", {"version_id": pb, "ly_do": "x", "expected_graph": tok, "khoa": self.K("tl-cfo")}, 403, "CRM_G_KHONG_CO_QUYEN")
        self.loi(TAI, "mau/tra-lai", {"version_id": pb, "ly_do": "x", "expected_graph": tok, "khoa": self.K("tl-tai")}, 403, "CRM_G_KHONG_CO_QUYEN")
        self.loi(CFO, "mau/kiem", {"version_id": pb, "expected_graph": tok, "khoa": self.K("kiem-cfo")}, 403, "CRM_G_KHONG_CO_QUYEN")
        r = self.ok(KT, "mau/tra-lai", {"version_id": pb, "ly_do": "Thiếu ghi chú điều khoản", "expected_graph": tok, "khoa": self.K("tl-1")})
        self.assertEqual((r["trang_thai"], r["viec_id"]), ("DRAFT", w))
        self.assertEqual(self.q("SELECT trang_thai FROM kho.viec_can_duyet WHERE id = %s", (w,)), "CHO_BO_SUNG")
        r = self.ok(TAI, "mau/gui-kiem", {"version_id": pb, "expected_graph": self.ct(TAI, pb)["token"], "khoa": self.K("gui-2")})
        self.assertEqual((r["viec_id"], self.q("SELECT trang_thai FROM kho.viec_can_duyet WHERE id = %s", (w,))), (w, "CHO_DUYET"))  # MỘT K5 xuyên pha
        self.assertEqual(self.q("SELECT count(*) FROM kho.viec_can_duyet WHERE tham_chieu_id = %s", (pb,)), 1)
        r = self.ok(KT, "mau/kiem", {"version_id": pb, "expected_graph": self.ct(KT, pb)["token"], "khoa": self.K("kiem-1")})
        self.assertEqual(r["trang_thai"], "CHO_CFO")
        ls = self.ct(KT, pb)["lich_su"]
        self.assertIn("CRM_MAU_TRA_LAI", [e["hanh_dong"] for e in ls["su_kien"]])
        self.s["w1"] = w

    # ------------------------------------------------------------------ g06 CFO+CRM+V4 duyệt → hiệu lực; BH chỉ thấy hiệu lực
    def test_g06_cfo_duyet(self):
        pb, w, ngay = self.s["pb1"], self.s["w1"], hom_nay().isoformat()
        tok = self.ct(CFO, pb)["token"]
        self.loi(CFO_NO_V4, "mau/duyet", {"version_id": pb, "valid_from": ngay, "expected_graph": tok, "khoa": self.K("d-nov4")}, 403, "CRM_G_KHONG_CO_QUYEN")
        self.loi(KT, "mau/duyet", {"version_id": pb, "valid_from": ngay, "expected_graph": tok, "khoa": self.K("d-kt")}, 403, "CRM_G_KHONG_CO_QUYEN")
        self.loi(CFO_B, "mau/duyet", {"version_id": pb, "valid_from": ngay, "expected_graph": tok, "khoa": self.K("d-b")}, 404, "CRM_G_KHONG_THAY")
        r = self.ok(CFO, "mau/duyet", {"version_id": pb, "valid_from": ngay, "expected_graph": tok, "khoa": self.K("d-1")})
        self.assertEqual((r["trang_thai"], r["valid_from"]), ("HIEU_LUC", ngay))
        self.assertEqual(self.q("SELECT trang_thai FROM kho.viec_can_duyet WHERE id = %s", (w,)), "DA_DUYET")
        st, ds, _ = self.goi("/api/crm/mau", cookie=self.sid(BH))
        self.assertEqual([v["phien_ban_id"] for v in ds["phien_ban"]], [pb])
        ct = self.ct(BH, pb)
        self.assertEqual((ct["quyen_doc"], ct["phat_hien"], ct["lich_su"]), ("HIEU_LUC", None, {}))
        self.assertFalse(any(ct["kha_nang"].values()))
        st, tep, _ = self.goi("/api/crm/mau/tep/" + pb, cookie=self.sid(BH))
        self.assertEqual((st, tep), (200, self.s["raw"]))
        self.s["truoc_v2"] = {k: self.q(f"SELECT md5(row_to_json(x)::text) FROM master.{k} x WHERE {c} = %s", (pb,))
                              for k, c in (("crm_mau_phien_ban", "id"), ("crm_mau_anh_xa", "phien_ban_id"), ("crm_mau_kiem_tra", "phien_ban_id"))}

    # ------------------------------------------------------------------ g07 v2 cùng raw, ánh xạ khác; đổi ánh xạ vô hiệu lần kiểm; hiệu lực không chồng
    def test_g07_v2_doi_anh_xa_va_hieu_luc(self):
        pb1, raw, loai = self.s["pb1"], self.s["raw"], self.loai_a()
        st, r = self.tai(TAI, raw, loai, "MAU_HD_A", "tai-v2")
        self.assertEqual((st, r["phien_ban"], r["lap_lai"]), (200, 2, False), r)
        pb2 = r["phien_ban_id"]
        self.assertEqual(self.q("SELECT count(DISTINCT tep_id) FROM master.crm_mau_phien_ban WHERE id IN (%s, %s)", (pb1, pb2)), 1)  # cùng raw → cùng tệp
        r = self.ok(TAI, "mau/anh-xa", {"version_id": pb2, "map": {**BAN_DO_DEMO, "ho_ten": None}, "expected_graph": self.ct(TAI, pb2)["token"], "khoa": self.K("v2-map-1")})
        self.assertEqual(r["so_chua_anh_xa"], 1)
        self.ok(TAI, "mau/gui-kiem", {"version_id": pb2, "expected_graph": self.ct(TAI, pb2)["token"], "khoa": self.K("v2-gui")})
        self.loi(KT, "mau/kiem", {"version_id": pb2, "expected_graph": self.ct(KT, pb2)["token"], "khoa": self.K("v2-kiem-thieu")}, 409, "CRM_G_CHUA_DU_DIEU_KIEN")
        ban_do_2 = {**BAN_DO_DEMO, "ho_ten": "so_hop_dong"}  # ánh xạ khác v1
        self.ok(KT, "mau/anh-xa", {"version_id": pb2, "map": ban_do_2, "expected_graph": self.ct(KT, pb2)["token"], "khoa": self.K("v2-map-2")})
        self.ok(KT, "mau/kiem", {"version_id": pb2, "expected_graph": self.ct(KT, pb2)["token"], "khoa": self.K("v2-kiem-1")})
        r = self.ok(TAI, "mau/anh-xa", {"version_id": pb2, "map": ban_do_2, "expected_graph": self.ct(TAI, pb2)["token"], "khoa": self.K("v2-map-3")})
        self.assertEqual(r["trang_thai"], "CHO_KIEM")  # đổi ánh xạ sau kiểm → lần kiểm hết hiệu lực
        self.assertIsNone(self.q("SELECT kiem_hien_hanh FROM master.crm_mau_phien_ban WHERE id = %s", (pb2,)))
        self.loi(CFO, "mau/duyet", {"version_id": pb2, "valid_from": hom_nay().isoformat(), "expected_graph": self.ct(CFO, pb2)["token"],
                                    "khoa": self.K("v2-d-stale")}, 409, "CRM_G_TRANG_THAI")
        self.ok(KT, "mau/kiem", {"version_id": pb2, "expected_graph": self.ct(KT, pb2)["token"], "khoa": self.K("v2-kiem-2")})
        self.loi(CFO, "mau/duyet", {"version_id": pb2, "valid_from": hom_nay().isoformat(), "expected_graph": self.ct(CFO, pb2)["token"],
                                    "khoa": self.K("v2-d-chong")}, 409, "CRM_G_HIEU_LUC_CHONG")
        tuong_lai = (hom_nay() + timedelta(days=30)).isoformat()
        self.ok(CFO, "mau/duyet", {"version_id": pb2, "valid_from": tuong_lai, "expected_graph": self.ct(CFO, pb2)["token"], "khoa": self.K("v2-d-1")})
        self.assertEqual(self.q("SELECT valid_to FROM master.crm_mau_phien_ban WHERE id = %s", (pb1,)).isoformat(), tuong_lai)
        st, ds, _ = self.goi("/api/crm/mau", cookie=self.sid(BH))
        self.assertEqual([v["phien_ban_id"] for v in ds["phien_ban"]], [pb1])  # bản tương lai không che bản hiện hành
        st, ds, _ = self.goi("/api/crm/mau?as_of=" + tuong_lai, cookie=self.sid(BH))
        self.assertEqual([v["phien_ban_id"] for v in ds["phien_ban"]], [pb2])
        self.ct(BH, pb2, 404)
        sau = {k: self.q(f"SELECT md5(row_to_json(x)::text) FROM master.{k} x WHERE {c} = %s", (pb1,))
               for k, c in (("crm_mau_anh_xa", "phien_ban_id"), ("crm_mau_kiem_tra", "phien_ban_id"))}
        self.assertEqual(sau, {k: self.s["truoc_v2"][k] for k in sau})  # ánh xạ/lần kiểm cũ nguyên vẹn
        self.assertEqual((self.kho / hashlib.sha256(raw).hexdigest()).read_bytes(), raw)

    # ------------------------------------------------------------------ g08 K5 typed: DML trực tiếp, retarget, mở lại, đọc qua vai kế thừa
    def test_g08_k5_typed_va_dml_truc_tiep(self):
        w, pb = self.s["w1"], self.s["pb1"]
        pn = str(self.q("SELECT phap_nhan_id FROM master.crm_mau_phien_ban WHERE id = %s", (pb,)))
        # T01: chỉ thăm dò UPDATE (retarget / mở lại) — KHÔNG gửi lệnh xóa nào, kể cả lệnh được kỳ vọng bị từ chối
        for sql, ma in (("UPDATE kho.viec_can_duyet SET tham_chieu_id = gen_random_uuid() WHERE id = %s", "CRM_G_VIEC_DOI_DICH"),
                        ("UPDATE kho.viec_can_duyet SET trang_thai = 'CHO_DUYET' WHERE id = %s", "CRM_G_VIEC_DA_DONG"),
                        ("UPDATE kho.viec_can_duyet SET trang_thai = 'DONG' WHERE id = %s", "CRM_G_VIEC_DA_DONG")):
            with self.assertRaises(psycopg.Error) as c:
                self.admin.execute(sql, (w,))  # kể cả chủ bảng: lệnh trực tiếp bị guard typed chặn (lỗi → không ghi)
            self.assertEqual(ma_loi(c.exception), ma)
        self.assertEqual(self.q("SELECT trang_thai FROM kho.viec_can_duyet WHERE id = %s", (w,)), "DA_DUYET")
        with psycopg.connect(self.app_dsn, autocommit=True) as app:
            with self.assertRaises(psycopg.Error) as c:
                app.execute("""INSERT INTO kho.viec_can_duyet (phap_nhan_id, loai, chu_trinh, module, tham_chieu_bang, tham_chieu_id)
                               VALUES (%s, 'V4', 'CRM_MAU', 'CRM', 'master.crm_mau_phien_ban', %s)""", (pn, pb))
            self.assertEqual(ma_loi(c.exception), "CRM_G_VIEC_CHI_CHU")
            for sql in ("SELECT count(*) FROM master.crm_mau_phien_ban", "SELECT count(*) FROM master.crm_g_bien_nhan",
                        "SELECT count(*) FROM master.phan_cong_hanh_dong"):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    app.execute(sql)
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                app.execute("SELECT master.crm_g_mau_kiem('k', %s, %s::uuid, 't')", ("0" * 64, pb))
            bh = str(self.q("SELECT id FROM master.nguoi_dung WHERE dang_nhap = %s", (BH,)))
            app.execute("SELECT set_config('ktt.nguoi_dung_id', %s, false), set_config('ktt.nguoi_dung_dang_nhap', %s, false)", (bh, BH))
            self.assertEqual(app.execute("SELECT count(*) FROM kho.viec_can_duyet WHERE tham_chieu_bang = 'master.crm_mau_phien_ban'").fetchone()[0], 0)
        self.assertEqual(self.q("SELECT count(*) FROM kho.viec_can_duyet WHERE tham_chieu_id = %s", (pb,)), 1)

    # ------------------------------------------------------------------ g09 CFO từ chối là hành động riêng từ CHO_CFO
    def test_g09_cfo_tu_choi(self):
        loai = self.loai_a()
        st, r = self.tai(TAI, mau_docx("TU CHOI"), loai, "MAU_TU_CHOI", "tc-tai")
        self.assertEqual(st, 200, r)
        pb = r["phien_ban_id"]
        self.ok(TAI, "mau/anh-xa", {"version_id": pb, "map": BAN_DO_DEMO, "expected_graph": self.ct(TAI, pb)["token"], "khoa": self.K("tc-map")})
        w = self.ok(TAI, "mau/gui-kiem", {"version_id": pb, "expected_graph": self.ct(TAI, pb)["token"], "khoa": self.K("tc-gui")})["viec_id"]
        self.loi(CFO, "mau/tu-choi", {"version_id": pb, "ly_do": "x", "expected_graph": self.ct(CFO, pb)["token"], "khoa": self.K("tc-som")}, 409, "CRM_G_TRANG_THAI")
        self.ok(KT, "mau/kiem", {"version_id": pb, "expected_graph": self.ct(KT, pb)["token"], "khoa": self.K("tc-kiem")})
        self.loi(KT, "mau/tra-lai", {"version_id": pb, "ly_do": "x", "expected_graph": self.ct(KT, pb)["token"], "khoa": self.K("tc-tl")}, 409, "CRM_G_TRANG_THAI")
        self.loi(CFO, "mau/tu-choi", {"version_id": pb, "ly_do": "", "expected_graph": self.ct(CFO, pb)["token"], "khoa": self.K("tc-rong")}, 400, "CRM_G_YEU_CAU_SAI")
        r = self.ok(CFO, "mau/tu-choi", {"version_id": pb, "ly_do": "Không dùng mẫu này", "expected_graph": self.ct(CFO, pb)["token"], "khoa": self.K("tc-1")})
        self.assertEqual(r["trang_thai"], "TU_CHOI")
        self.assertEqual(self.q("SELECT trang_thai FROM kho.viec_can_duyet WHERE id = %s", (w,)), "DONG")
        self.loi(TAI, "mau/anh-xa", {"version_id": pb, "map": BAN_DO_DEMO, "expected_graph": self.ct(TAI, pb)["token"], "khoa": self.K("tc-map2")}, 409,
                 "CRM_G_TRANG_THAI")

    # ------------------------------------------------------------------ g10 S01: hai service/kết nối chủ bảng thật, cùng khóa, khác H
    def test_g10_dong_thoi_cung_khoa(self):
        from kho_tri_thuc.k2 import crm_mau as M
        loai, kho2 = self.loai_a(), Path(tempfile.mkdtemp(prefix="ktt_crmg_dong_thoi_"))  # giữ lại
        that, goi, vao, tha = M.doc_mau_docx, [], threading.Event(), threading.Event()
        ket_noi, luong = [], []

        def don():  # T02: chạy cả khi assertion/worker lỗi — nhả Event, join hữu hạn, rồi đóng đúng kết nối test tạo
            tha.set()
            for t in luong:
                t.join(60)
            con_song = [t.name for t in luong if t.is_alive()]
            for c in ket_noi:
                _dong(c)
            if con_song:
                raise AssertionError(f"worker không kết thúc trong hạn: {con_song}")
        self.addCleanup(don)

        def dich_vu():
            app = psycopg.connect(self.app_dsn, autocommit=True, row_factory=dict_row)
            ket_noi.append(app)
            chu = psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)
            ket_noi.append(chu)
            return M.CrmMauK2(app, kho2, conn_tin_cay=chu)
        sa, sb = dich_vu(), dich_vu()
        pid_a, pid_b = sa.conn_tin_cay.info.backend_pid, sb.conn_tin_cay.info.backend_pid
        self.assertNotEqual(pid_a, pid_b)  # hai kết nối chủ bảng thật, khác backend
        x, y, khoa = mau_docx("DONG THOI X"), mau_docx("DONG THOI Y"), self.K("dong-thoi")

        def boc(raw, **kw):  # bọc bộ đọc THẬT: chỉ giữ request đầu ở bước parse
            goi.append(hashlib.sha256(raw).hexdigest())
            if len(goi) == 1:
                vao.set()
                tha.wait(60)
            return that(raw, **kw)
        kq = {}

        def chay(ten, svc, raw):
            try:
                kq[ten] = svc.tai_mau(TAI, raw, loai_hinh_id=loai, ma_mau="MAU_DONG_THOI", ten_tep="dong_thoi.docx", khoa=khoa)
            except Exception as exc:  # noqa: BLE001 — ghi nhận để kiểm mã
                kq[ten] = exc
        with patch.object(M, "doc_mau_docx", boc):
            ta = threading.Thread(target=chay, args=("a", sa, x), name="g10-A")
            luong.append(ta)
            ta.start()
            self.assertTrue(vao.wait(60), "A không tới bước parse trong hạn")
            # A đang ở parse, TRONG giao dịch: đang giữ khóa namespace advisory
            self.assertGreaterEqual(self.q("SELECT count(*) FROM pg_locks WHERE pid = %s AND locktype = 'advisory' AND granted", (pid_a,)), 1)
            truoc_b = self.dem(kho2 / "crm-mau")
            tb = threading.Thread(target=chay, args=("b", sb, y), name="g10-B")
            luong.append(tb)
            tb.start()
            # T03: bằng chứng THỰC — backend của B bị chính backend của A chặn, đợi khóa advisory, tại preflight crm_g_tra
            loai_cho, su_kien, khoa_cho, cau = self.cho_bi_chan(pid_b, pid_a)
            self.assertEqual((loai_cho, su_kien, khoa_cho), ("Lock", "advisory", ["advisory"]))
            self.assertIn("crm_g_tra", cau)
            self.assertTrue(tb.is_alive())
            self.assertEqual(len(goi), 1)
            tha.set()
            ta.join(60)
            tb.join(60)
            self.assertFalse(ta.is_alive() or tb.is_alive(), "worker không kết thúc")
            self.assertIsInstance(kq["a"], dict, kq)
            self.assertEqual((kq["a"]["trang_thai"], kq["a"]["lap_lai"]), ("DRAFT", False))
            self.assertIsInstance(kq["b"], psycopg.Error, kq)
            self.assertEqual(ma_loi(kq["b"]), "CRM_G_IDEMPOTENCY_KHAC")
            self.assertEqual(goi, [hashlib.sha256(x).hexdigest()])  # B không parse
            self.assertFalse((kho2 / "crm-mau" / hashlib.sha256(y).hexdigest()).exists())  # B không ghi tệp
            sau_a = self.dem(kho2 / "crm-mau")
            r = sb.tai_mau(TAI, x, loai_hinh_id=loai, ma_mau="MAU_DONG_THOI", ten_tep="dong_thoi.docx", khoa=khoa)  # cùng body: FINAL cũ
            self.assertEqual((r["lap_lai"], r["phien_ban_id"]), (True, kq["a"]["phien_ban_id"]))
            self.assertEqual(len(goi), 1)  # replay không parse lại
            self.assertEqual(self.dem(kho2 / "crm-mau"), sau_a)
        self.assertEqual(truoc_b["bn"] + 1, sau_a["bn"])
        self.assertEqual(truoc_b["tep_kho"], [])
        self.assertEqual(sau_a["tep_kho"], [hashlib.sha256(x).hexdigest()])  # tên tệp cấp đầu thư mục (không phải hash đệ quy)

    # ------------------------------------------------------------------ g11 thu hồi thắng preflight (đồng thời), replay/tải về bị từ chối, seed không cấp lại
    def test_g11_thu_hoi(self):
        from kho_tri_thuc.k2 import crm_g_demo
        loai, pb1 = self.loai_a(), self.s["pb1"]
        moi = mau_docx("SAU THU HOI")
        truoc = self.dem()
        sid = self.sid(TAI)
        chu_may_chu = self.app.__dict__["_crm_g"].conn_tin_cay  # kết nối chủ bảng của service G trên máy chủ (request chạy trên backend này)
        pid_req = chu_may_chu.info.backend_pid
        kq, luong = {}, []
        a2 = psycopg.connect(self.dsn)  # giao dịch thu hồi (không autocommit) do test sở hữu

        def don():  # T02: mọi đường lỗi — không để worker kẹt sau lock; join hữu hạn; đóng đúng kết nối test tạo
            if not a2.closed and a2.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
                a2.rollback()  # chỉ bỏ giao dịch thu hồi CHƯA commit của chính test khi ca đã hỏng; không xóa dữ liệu
            for t_ in luong:
                t_.join(60)
            con_song = [t_.name for t_ in luong if t_.is_alive()]
            _dong(a2)
            if con_song:
                raise AssertionError(f"worker không kết thúc trong hạn: {con_song}")
        self.addCleanup(don)

        def gui():
            try:
                kq["r"] = self.tai(TAI, moi, loai, "MAU_HD_A", "sau-thu-hoi")
            except Exception as exc:  # noqa: BLE001 — worker lỗi được báo, không nuốt
                kq["loi"] = exc
        self.assertEqual(sid, self.s["sid"][TAI])
        a2.execute("""UPDATE master.phan_cong_hanh_dong SET thu_hoi_luc = now(), thu_hoi_boi = 'TEST_CRM_41_02', thu_hoi_ly_do = 'Ca thu hồi đồng thời'
                      WHERE nguoi_dung_id = (SELECT id FROM master.nguoi_dung WHERE dang_nhap = %s) AND thu_hoi_luc IS NULL""", (TAI,))
        pid_thu_hoi = a2.info.backend_pid
        t = threading.Thread(target=gui, name="g11-upload")
        luong.append(t)
        t.start()
        # T03: bằng chứng THỰC — backend của chính request bị backend giao dịch thu hồi chặn, đợi khóa dòng/xid ở preflight crm_g_tra
        loai_cho, _, khoa_cho, cau = self.cho_bi_chan(pid_req, pid_thu_hoi)
        self.assertEqual(loai_cho, "Lock")
        self.assertTrue(khoa_cho and set(khoa_cho) <= {"transactionid", "tuple"}, khoa_cho)
        self.assertIn("crm_g_tra", cau)
        self.assertTrue(t.is_alive())
        a2.commit()
        t.join(60)
        self.assertFalse(t.is_alive(), "request không kết thúc sau khi thu hồi commit")
        self.assertNotIn("loi", kq, kq.get("loi"))
        st, r = kq["r"]
        self.assertEqual((st, r.get("error")), (403, "CRM_G_KHONG_CO_QUYEN"))
        self.assertFalse((self.kho / hashlib.sha256(moi).hexdigest()).exists())
        self.assertEqual(self.dem(), truoc)
        st, r = self.tai(TAI, self.s["raw"], loai, "MAU_HD_A", "tai-1")  # đúng khóa/body cũ: quyền hiện hành trước biên nhận
        self.assertEqual((st, r.get("error")), (403, "CRM_G_KHONG_CO_QUYEN"))
        pb_tc = self.q("SELECT id FROM master.crm_mau_phien_ban WHERE trang_thai = 'TU_CHOI' LIMIT 1")
        st, _, _ = self.goi(f"/api/crm/mau/tep/{pb_tc}", cookie=self.sid(TAI))
        self.assertEqual(st, 404)  # không còn quyền đọc nháp/lịch sử
        st, tep, _ = self.goi(f"/api/crm/mau/tep/{pb1}", cookie=self.sid(TAI))
        self.assertEqual((st, tep), (200, self.s["raw"]))  # bản đang hiệu lực vẫn đọc được bằng quyền CRM thường
        self.assertEqual(self.dem(), truoc)
        lai = crm_g_demo.khoi_tao(self.admin)
        self.assertEqual(next(a for a in lai["actor"] if a["dang_nhap"] == TAI)["trang_thai"], "DA_THU_HOI")
        self.assertEqual(lai["dem"], {"actor": 0, "phan_quyen": 0, "danh_muc": 0, "phan_cong": 0})
        self.assertEqual(self.q("""SELECT count(*) FROM master.phan_cong_hanh_dong a JOIN master.nguoi_dung n ON n.id = a.nguoi_dung_id
                                   WHERE n.dang_nhap = %s AND a.thu_hoi_luc IS NULL""", (TAI,)), 0)

    # ------------------------------------------------------------------ g12 G7: KT lập/gửi → CFO duyệt → đọc 4 cột/as_of/CHUA_CO
    def test_g12_bo_chuan(self):
        da, da_b, gd, ngay = self.du_an("DA_KCN_DEMO"), self.du_an("DA_NHA_DEMO"), "DEMO_G7_STAGE_1", hom_nay()
        tien_truoc = (self.q("SELECT count(*) FROM master.lich_thu"), self.q("SELECT count(*) FROM kho.chung_tu"))
        st, r, _ = self.goi(f"/api/crm/bo-chuan?du_an_id={da}&giai_doan={gd}", cookie=self.sid(KT))
        self.assertEqual((st, r["trang_thai"], r["version"], r["rows"]), (200, "CHUA_CO", None, []))
        self.assertEqual(r["cot"], ["Lần", "Giá trị", "Mốc thời gian", "Ghi chú"])
        dong = [{"lan": "1", "gia_tri_loai": "PERCENT", "gia_tri_thap_phan": "40", "so_tien_minor": None, "tien_te": None, "moc_loai": "NGAY",
                 "moc_ngay": "2026-11-01", "moc_su_kien": None, "ghi_chu": "DEMO ngày tường minh"},
                {"lan": "2", "gia_tri_loai": "PERCENT", "gia_tri_thap_phan": "60", "so_tien_minor": None, "tien_te": None, "moc_loai": "SU_KIEN",
                 "moc_ngay": None, "moc_su_kien": "DEMO_BAN_GIAO", "ghi_chu": "DEMO sự kiện, không tự gán ngày"}]
        body = {"du_an_id": da, "giai_doan": gd, "dong": dong}
        self.loi(BH, "bo-chuan/lap", {**body, "khoa": self.K("bc-bh")}, 403, "CRM_G_KHONG_CO_QUYEN")
        self.loi(CFO, "bo-chuan/lap", {**body, "khoa": self.K("bc-cfo")}, 403, "CRM_G_KHONG_CO_QUYEN")
        self.loi(CFO_B, "bo-chuan/lap", {**body, "khoa": self.K("bc-b")}, 404, "CRM_G_KHONG_THAY")
        self.loi(KT, "bo-chuan/lap", {**body, "dong": [{**dong[0], "gia_tri_loai": "AMOUNT"}], "khoa": self.K("bc-sai")}, 400, "CRM_G_CHUAN_SAI")
        r = self.ok(KT, "bo-chuan/lap", {**body, "khoa": self.K("bc-1")})
        self.assertEqual((r["trang_thai"], r["so_dong"], r["phien_ban"]), ("DRAFT", 2, 1))
        v1 = r["phien_ban_id"]
        tong = self.goi("/api/crm/bo-chuan", cookie=self.sid(KT))[1]
        ban = next(v for v in tong["phien_ban"] if v["id"] == v1)
        self.assertEqual([(d["lan"], d["gia_tri_thap_phan"], d["moc_loai"]) for d in ban["dong"]], [("1", "40", "NGAY"), ("2", "60", "SU_KIEN")])
        r = self.ok(KT, "bo-chuan/gui-duyet", {"version_id": v1, "expected_graph": ban["token"], "khoa": self.K("bc-gui")})
        self.assertEqual(r["trang_thai"], "CHO_CFO")
        tok = next(v for v in self.goi("/api/crm/bo-chuan", cookie=self.sid(CFO))[1]["phien_ban"] if v["id"] == v1)["token"]
        self.loi(KT, "bo-chuan/duyet", {"version_id": v1, "valid_from": ngay.isoformat(), "expected_graph": tok, "khoa": self.K("bc-d-kt")}, 403, "CRM_G_KHONG_CO_QUYEN")
        self.loi(CFO_NO_V4, "bo-chuan/duyet", {"version_id": v1, "valid_from": ngay.isoformat(), "expected_graph": tok, "khoa": self.K("bc-d-nov4")}, 403,
                 "CRM_G_KHONG_CO_QUYEN")
        self.ok(CFO, "bo-chuan/duyet", {"version_id": v1, "valid_from": ngay.isoformat(), "expected_graph": tok, "khoa": self.K("bc-d-1")})
        st, r, _ = self.goi(f"/api/crm/bo-chuan?du_an_id={da}&giai_doan={gd}&as_of={ngay.isoformat()}", cookie=self.sid(BH))
        self.assertEqual((st, r["trang_thai"], r["version"]["id"]), (200, "HIEU_LUC", v1))
        self.assertEqual([(x["lan"], x["gia_tri_loai"], x["gia_tri_thap_phan"], x["moc_loai"], x["moc_ngay"], x["moc_su_kien"]) for x in r["rows"]],
                         [("1", "PERCENT", "40", "NGAY", "2026-11-01", None), ("2", "PERCENT", "60", "SU_KIEN", None, "DEMO_BAN_GIAO")])
        st, r, _ = self.goi(f"/api/crm/bo-chuan?du_an_id={da}&giai_doan={gd}&as_of={(ngay - timedelta(days=1)).isoformat()}", cookie=self.sid(KT))
        self.assertEqual(r["trang_thai"], "CHUA_CO")
        st, r, _ = self.goi(f"/api/crm/bo-chuan?du_an_id={da}&giai_doan=GIAI_DOAN_KHAC", cookie=self.sid(KT))
        self.assertEqual(r["trang_thai"], "CHUA_CO")
        st, r, _ = self.goi(f"/api/crm/bo-chuan?du_an_id={da_b}&giai_doan={gd}", cookie=self.sid(KT))
        self.assertEqual((st, r.get("error")), (404, "CRM_G_KHONG_THAY"))  # dự án PN khác
        # kiểu: NULL ≠ 0, số tiền minor + tiền tệ, không mốc
        kieu = [{"lan": "1", "gia_tri_loai": "AMOUNT", "gia_tri_thap_phan": None, "so_tien_minor": "0", "tien_te": "VND", "moc_loai": None,
                 "moc_ngay": None, "moc_su_kien": None, "ghi_chu": None},
                {"lan": "2", "gia_tri_loai": None, "gia_tri_thap_phan": None, "so_tien_minor": None, "tien_te": None, "moc_loai": None,
                 "moc_ngay": None, "moc_su_kien": None, "ghi_chu": "chưa có giá trị"}]
        r = self.ok(KT, "bo-chuan/lap", {"du_an_id": da, "giai_doan": "DEMO_G7_KIEU", "dong": kieu, "khoa": self.K("bc-kieu")})
        rows = self.admin.execute("SELECT gia_tri_loai, so_tien_minor, tien_te, gia_tri_thap_phan FROM master.crm_bo_chuan_dong WHERE phien_ban_id = %s ORDER BY thu_tu",
                                  (r["phien_ban_id"],)).fetchall()
        self.assertEqual(rows, [("AMOUNT", "0", "VND", None), (None, None, None, None)])
        # phiên bản tương lai không che bản hiện hành
        r = self.ok(KT, "bo-chuan/lap", {**body, "khoa": self.K("bc-2")})
        v2 = r["phien_ban_id"]
        t2 = next(v for v in self.goi("/api/crm/bo-chuan", cookie=self.sid(KT))[1]["phien_ban"] if v["id"] == v2)["token"]
        self.ok(KT, "bo-chuan/gui-duyet", {"version_id": v2, "expected_graph": t2, "khoa": self.K("bc-gui-2")})
        t2 = next(v for v in self.goi("/api/crm/bo-chuan", cookie=self.sid(CFO))[1]["phien_ban"] if v["id"] == v2)["token"]
        sau10 = (ngay + timedelta(days=10)).isoformat()
        self.ok(CFO, "bo-chuan/duyet", {"version_id": v2, "valid_from": sau10, "expected_graph": t2, "khoa": self.K("bc-d-2")})
        self.assertEqual(self.goi(f"/api/crm/bo-chuan?du_an_id={da}&giai_doan={gd}", cookie=self.sid(KT))[1]["version"]["id"], v1)
        self.assertEqual(self.goi(f"/api/crm/bo-chuan?du_an_id={da}&giai_doan={gd}&as_of={sau10}", cookie=self.sid(KT))[1]["version"]["id"], v2)
        st, r, _ = self.goi("/api/crm/bo-chuan/tra-lai", {"version_id": v2, "khoa": self.K("bc-tl")}, self.sid(KT))
        self.assertEqual(st, 404)  # không có vòng đời trả lại G7
        self.assertEqual((self.q("SELECT count(*) FROM master.lich_thu"), self.q("SELECT count(*) FROM kho.chung_tu")), tien_truoc)  # 0 nghĩa vụ tiền

    # ------------------------------------------------------------------ g13 CRM cũ vẫn chạy sau G
    def test_g13_crm_cu_giu_nguyen(self):
        st, s, _ = self.goi("/api/crm", cookie=self.sid(KT))
        self.assertEqual(st, 200, s)
        self.assertTrue(s["cau_hinh"])


if __name__ == "__main__":
    unittest.main()
