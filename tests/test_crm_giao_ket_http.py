"""CRM-41-03 — kiểm HTTP thật G2 Báo giá → G3 Soạn trên LocalApp/LocalServer + PostgreSQL DEMO mới (CODE_ONLY: coder viết, CHƯA CHẠY —
NOT_RUN_CODE_ONLY).

Chạy khi Root cấp KHO_PG_DSN_TEST lúc chạy (DSN chủ CSDL; không đọc .env/var, không hardcode credentials). DB MỚI `kho_test_crmgk_*` migrate mặc
định (tối thiểu M0021), seed CRM DEMO + crm_g_demo (actor/danh mục/phân công + điều khoản tham chiếu DEMO — KHÔNG seed M9, KHÔNG bootstrap chung kéo theo
module vay). Mẫu hợp đồng và bộ chuẩn G7 được dựng bằng LUỒNG DỊCH VỤ THẬT qua HTTP (tải → ánh xạ → gửi kiểm → KT kiểm → CFO duyệt; KT lập/gửi →
CFO duyệt) — không owner INSERT đối tượng đã duyệt. Word/PDF: metadata Word/guard không chứng minh worker được phép chạy COM; PDF_DAT cần
bằng chứng Word sở hữu đã dừng. Guard/PermissionError → PDF_CHUA_SAN_SANG có lý do cụ thể, DOCX vẫn giữ, KHÔNG CHO_KY giả.
Không DROP/DELETE/cleanup — DB/role/thư mục giữ làm bằng chứng.
Thiếu driver/DSN → skip = NOT_RUN (không tính đạt). Không chứng minh GUI/1440 click (Root chạy riêng).
Ánh xạ ca nghiệm thu §8: c1 → g02/g03 · c2 → g04 · c3 → g05 · c4 → g01 · c5 → g06 · c6 → g02/g07 · c7 (async) → tests/crm_giao_ket_async.cjs.
FIX01: g07 fixture (PDF lỗi sau CHO_KY không hạ trạng thái) · #5 → g08 (đặt chỗ bền, đếm render/chỗ đặt/thư mục, 409 đang xử lý/khác body) ·
#6 → g09 (thu hồi khi lệnh chờ khóa namespace) · #4/#7/#8 → g10 (tính thử chỉ đọc, mốc trống in được, tổng canonical NET/GROSS/khác tổng).
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
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

from test_crm_giao_ket import BAN_DO_TEN, _co_word, mau_docx

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
TAI, KT, CFO, BH = "MO_PHONG_CRM_G_TAI_A", "MO_PHONG_CRM_G_KT_A", "MO_PHONG_CRM_G_CFO_A", "MO_PHONG_CRM_G_BH_A"
KT_NO_CRM, CFO_B = "MO_PHONG_CRM_G_KT_NO_CRM_A", "MO_PHONG_CRM_G_CFO_B"
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
RE_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def ngay(d=0):
    return (datetime.now(timezone(timedelta(hours=7))).date() + timedelta(days=d)).isoformat()


def _dong(c):
    if c is not None and not c.closed:
        c.close()


def kiem_ket_qua_pdf(ca, x, ly_do, kiem, word_san_sang):
    """Chỉ nhận PDF đạt có bằng chứng; không coi mọi lỗi chuyển PDF là do chính sách/guard."""
    if x["trang_thai"] == "PDF_DAT":
        ca.assertTrue(word_san_sang, x)
        ca.assertIsNone(ly_do)
        word = kiem.get("word") or {}
        ca.assertIs(word.get("gan_job"), True, kiem)
        ca.assertIs(word.get("da_dung"), True, kiem)
        ca.assertIs(type(word.get("pid")), int, kiem)
        ca.assertGreater(word["pid"], 0, kiem)
        ca.assertTrue(x["pdf_sha256"], x)
        ca.assertGreater(x["pdf_len"], 0, x)
        return True
    ca.assertEqual(x["trang_thai"], "PDF_CHUA_SAN_SANG", x)
    # crm_docx: kiểm nhà cung cấp/guard trước spawn, hoặc worker bị chặn quyền tại một pha COM.
    ca.assertTrue(ly_do in {
        "KHONG_PHAI_WINDOWS", "WORD_KHONG_CO", "WORD_KHAC_BAN_GHIM",
        "GUARD_KHONG_NAP", "GUARD_SHA_SAI", "GUARD_CO_TAT", "GUARD_KHONG_HOOK", "GUARD_BYTECODE_BAT",
    } or re.fullmatch(r"COM_(?:TAO_WORD|CHUNG_MINH_SO_HUU|TUY_CHON|MO|XUAT):PermissionError", ly_do or ""),
                  (ly_do, kiem, x))
    ca.assertIsNone(x["pdf_sha256"], x)
    ca.assertIsNone(x["pdf_len"], x)
    ca.assertTrue(x["docx_sha256"], x)
    ca.assertGreater(x["docx_len"], 0, x)
    return False


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — HTTP CRM-41-03 không chạy (NOT_RUN, không tính đạt)")
class CrmGiaoKetHttp(unittest.TestCase):
    """Chạy theo thứ tự tên g01…g08 trên MỘT DB/một máy chủ; trạng thái qua cls.s."""

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.k2 import crm_demo, crm_g_demo
        cls.db = "kho_test_crmgk_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)
        cls.addClassCleanup(_dong, cls.admin)
        cls.version = pg.migrate(cls.admin)
        crm_demo.khoi_tao(cls.admin)
        cls.seed = crm_g_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_crmgk_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE IN ROLE app_web")
        cls.app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        cls.env = patch.dict(os.environ, {LocalApp.CRM_ENV: cls.app_dsn, LocalApp.CRM_ENV_ADMIN: cls.dsn, LocalApp.CRM_ENV_DB_KIEM_THU: "1"})
        cls.env.start()
        cls.addClassCleanup(cls.env.stop)
        cls.tam = Path(tempfile.mkdtemp(prefix="ktt_crmgk_http_"))  # giữ lại
        (cls.tam / "cau_hinh_fixture.toml").write_text(CAU_HINH_FIXTURE, encoding="utf-8")
        cls.app = LocalApp(cls.tam / "cau_hinh_fixture.toml", cls.tam / "web")
        cls.addClassCleanup(cls._dong_ket_noi_app)
        cls.server = LocalServer(cls.app, 0)
        cls.addClassCleanup(cls.server.server_close)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls._dung)
        cls.run_id = uuid.uuid4().hex[:8]
        cls.co_word = _co_word()
        cls.s = {}

    @classmethod
    def _dung(cls):
        cls.server.shutdown()
        cls.thread.join(10)

    @classmethod
    def _dong_ket_noi_app(cls):
        g = cls.app.__dict__.get("_crm_g")
        _dong(getattr(g, "conn_tin_cay", None))
        _dong(getattr(getattr(cls.app, "_crm", None), "conn", None))

    # ------------------------------------------------------------------ helpers
    def goi(self, path, body=None, cookie=None, raw=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=600)
        h = {"X-KTT-Token": self.app.token}
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

    def sid(self, login):
        if login not in self.s.setdefault("sid", {}):
            st, _, ck = self.goi("/api/crm")
            sid = ck.split(";", 1)[0].split("=", 1)[1]
            st, r, _ = self.goi("/api/crm/danh-tinh", {"dang_nhap": login}, sid)
            self.assertEqual((st, r), (200, {"dang_nhap": login}))
            self.s["sid"][login] = sid
        return self.s["sid"][login]

    def K(self, ten):
        return f"gk-{self.run_id}-{ten}"

    def ok(self, login, path, body):
        st, r, _ = self.goi("/api/crm/" + path, body, self.sid(login))
        self.assertEqual(st, 200, (login, path, r))
        return r

    def loi(self, login, path, body, status, ma):
        st, r, _ = self.goi("/api/crm/" + path, body, self.sid(login))
        self.assertEqual((st, r.get("error") if isinstance(r, dict) else r), (status, ma), (login, path, r))
        return r

    def get(self, login, path, status=200):
        st, r, _ = self.goi("/api/crm/" + path, cookie=self.sid(login))
        self.assertEqual(st, status, r)
        return r

    def q(self, sql, params=()):
        return self.admin.execute(sql, params).fetchone()[0]

    def pdf_dat(self, x):
        ly_do, kiem = self.admin.execute("SELECT ly_do, kiem_pdf FROM master.crm_gk_xuat WHERE id = %s", (x["xuat_id"],)).fetchone()
        return kiem_ket_qua_pdf(self, x, ly_do, kiem, self.co_word)

    def loai_a(self):
        return str(self.q("""SELECT l.id FROM master.loai_hinh_doanh_thu l JOIN master.phap_nhan p ON p.id = l.phap_nhan_id
                             WHERE p.ma = 'PN_DEMO_A' AND l.ma = 'DT-KCN-THUE-DAT-DEMO' AND l.phien_ban = 2"""))

    def du_an(self, ma):
        return str(self.q("SELECT id FROM master.du_an WHERE ma_junsky = %s", (ma,)))

    def dem(self):
        return {k: self.q(f"SELECT count(*) FROM {t}") for k, t in (("hd", "master.hop_dong"), ("soan", "master.crm_hd_soan"), ("rev", "master.crm_hd_soan_rev"),
                                                                     ("xuat", "master.crm_gk_xuat"), ("lich_thu", "master.lich_thu"), ("bg", "master.crm_bao_gia"),
                                                                     ("bn", "master.crm_g_bien_nhan"))}

    @staticmethod
    def khoa_may(nhan):
        """FIX02: khóa máy DETERMINISTIC theo cùng ý định, tách khỏi nhãn hiển thị (vd "MAU V1" → "mau-v1"); chỉ ký tự hợp lệ của KHOA_RE G1."""
        k = re.sub(r"[^a-z0-9]+", "-", nhan.lower()).strip("-")
        assert re.fullmatch(r"[a-z0-9-]{1,40}", k), nhan
        return k

    def mau_hieu_luc(self, ma_mau, valid_from, ghi_chu):
        """Mẫu qua LUỒNG THẬT: tải (TAI) → ánh xạ tên ô ≠ mã trường (KT) → gửi kiểm → KT kiểm → CFO duyệt (V4). `ghi_chu` = nội dung hiển thị
        trong DOCX (giữ nguyên "MAU V1"/"MAU V2"); khóa thao tác dùng khóa máy riêng (FIX02 — không đưa nhãn có khoảng trắng vào khóa)."""
        km = self.khoa_may(ghi_chu)
        info = {"loai_hinh_id": self.loai_a(), "ma_mau": ma_mau, "ten_tep": "mau_hd.docx", "khoa": self.K("tai-" + km)}
        raw = mau_docx(f'<w:p><w:r><w:t xml:space="preserve">{ghi_chu}</w:t></w:r></w:p>')
        st, r, _ = self.goi("/api/crm/mau/tai", cookie=self.sid(TAI), raw=raw,
                            headers={"X-CRM-G-Info": quote(json.dumps(info)), "Content-Type": "application/octet-stream"})
        self.assertEqual(st, 200, r)
        pb = r["phien_ban_id"]
        tok = lambda: self.get(KT, "mau/" + pb)["token"]  # noqa: E731
        self.ok(KT, "mau/anh-xa", {"version_id": pb, "map": BAN_DO_TEN, "expected_graph": tok(), "khoa": self.K("map-" + km)})
        self.ok(KT, "mau/gui-kiem", {"version_id": pb, "expected_graph": tok(), "khoa": self.K("gui-" + km)})
        self.ok(KT, "mau/kiem", {"version_id": pb, "expected_graph": tok(), "khoa": self.K("kiem-" + km)})
        self.ok(CFO, "mau/duyet", {"version_id": pb, "valid_from": valid_from, "expected_graph": self.get(CFO, "mau/" + pb)["token"],
                                   "khoa": self.K("duyet-" + km)})
        return pb, hashlib.sha256(raw).hexdigest()

    def test_g00_khoa_fixture_hop_le(self):
        """FIX02: mọi khóa fixture sinh ra phải hợp lệ với khóa thao tác G1 (không nới regex sản phẩm); nhãn hiển thị vẫn giữ trong DOCX."""
        from kho_tri_thuc.k2 import crm_mau
        re_khoa = getattr(crm_mau, "KHOA_RE", None) or re.compile(r"^[A-Za-z0-9_.:-]{1,200}$")
        for nhan in ("MAU V1", "MAU V2"):
            km = self.khoa_may(nhan)
            self.assertEqual(km, self.khoa_may(nhan))  # deterministic
            for tien_to in ("tai-", "map-", "gui-", "kiem-", "duyet-"):
                self.assertTrue(re_khoa.fullmatch(self.K(tien_to + km)), self.K(tien_to + km))
        self.assertNotEqual(self.khoa_may("MAU V1"), self.khoa_may("MAU V2"))

    def bao_gia(self, **sua):
        d = {"loai_hinh_id": self.loai_a(), "du_an_id": self.du_an("DA_KCN_DEMO"), "nguon_lich": "KHACH", "don_vi": {"ma": f"LO-{self.run_id}"},
             "khach": {"du_thao": {"ten": "KHÁCH DỰ THẢO DEMO"}}, "gia": {"tien_te": "VND", "tong": "1000000000", "co_so_thue": "NET"},
             "phi_bao_tri": {"gia_tri": "20000000", "tien_te": "VND", "co_so": "khai riêng DEMO"},
             "lich": [{"lan": "1", "loai": "PERCENT", "ty_le": "40", "moc_loai": "SU_KIEN", "moc_su_kien": "KY_HD"},
                      {"lan": "2", "loai": "PERCENT", "ty_le": "60"}]}  # mốc dòng 2 TRỐNG: chỉ cảnh báo
        d.update(sua)
        return d

    # ------------------------------------------------------------------ g01 (c4): mẫu + G7 qua luồng dịch vụ thật
    def test_g01_mau_va_bo_chuan_qua_luong_that(self):
        from kho_tri_thuc.ha_tang import pg_migrations as PM
        self.assertGreaterEqual(self.version, 21)
        self.assertEqual([i + 1 for i, m in enumerate(PM.PG_MIGRATIONS) if tuple(m) == tuple(PM.M0021_CRM_G2G3)], [21])
        ls = self.admin.execute("SELECT version, checksum FROM master.schema_migrations WHERE version <= %s ORDER BY version", (21,)).fetchall()
        self.assertEqual([tuple(x) for x in ls], [(i + 1, PM._hash(m)) for i, m in enumerate(PM.PG_MIGRATIONS[:21])])
        self.assertEqual(self.seed["g2g3_dieu_khoan"], "DA_TAO", self.seed)
        self.s["v1"], self.s["v1_sha"] = self.mau_hieu_luc("HD_GK_" + self.run_id, ngay(-2), "MAU V1")
        ct = self.get(KT, "mau/" + self.s["v1"])
        self.assertEqual((ct["phien_ban"]["trang_thai"], ct["tep"]["trang_thai_doc"], ct["anh_xa"]["so_chua_anh_xa"]), ("HIEU_LUC", "DU", 0))
        self.assertEqual(len(ct["phat_hien"]["occurrences"]), 6)  # tách run + bảng lồng + header + footer
        r = self.ok(KT, "bo-chuan/lap", {"du_an_id": self.du_an("DA_KCN_DEMO"), "giai_doan": "GK_STAGE", "khoa": self.K("g7-lap"),
                                         "dong": [{"lan": "1", "gia_tri_loai": "PERCENT", "gia_tri_thap_phan": "40", "moc_loai": "SU_KIEN", "moc_su_kien": "KY_HD"},
                                                  {"lan": "2", "gia_tri_loai": "PERCENT", "gia_tri_thap_phan": "60"}]})
        tok = next(v["token"] for v in self.get(KT, "bo-chuan")["phien_ban"] if v["id"] == r["phien_ban_id"])
        self.ok(KT, "bo-chuan/gui-duyet", {"version_id": r["phien_ban_id"], "expected_graph": tok, "khoa": self.K("g7-gui")})
        tok = next(v["token"] for v in self.get(CFO, "bo-chuan")["phien_ban"] if v["id"] == r["phien_ban_id"])
        self.ok(CFO, "bo-chuan/duyet", {"version_id": r["phien_ban_id"], "valid_from": ngay(-2), "expected_graph": tok, "khoa": self.K("g7-duyet")})

    # ------------------------------------------------------------------ g02 (c1/c6): VND dương → in PDF thật (hoặc PDF chưa sẵn sàng trung thực)
    def test_g02_bao_gia_vnd_luu_in(self):
        r = self.ok(BH, "bao-gia/luu", {"bao_gia_id": None, "expected_revision": None, "du_lieu": self.bao_gia(), "khoa": self.K("bg1")})
        self.s["bg1"] = r["bao_gia_id"]
        ct = self.get(BH, "bao-gia/" + r["bao_gia_id"])
        t = ct["tinh"]
        self.assertEqual((t["tong_minor"], [x["so_tien_minor"] for x in t["dong"]], t["tong_ty_le"], t["chan_in"]),
                         ("1000000000", ["400000000", "600000000"], "100", []))
        self.assertIn("MOC_TRONG", [x["ma"] for x in t["canh_bao"]])  # mốc trống chỉ cảnh báo
        self.assertEqual(ct["du_lieu"]["phi_bao_tri"]["gia_tri"], "20000000")  # phí bảo trì giữ riêng
        trc = self.dem()
        x = self.ok(BH, "bao-gia/in", {"bao_gia_id": r["bao_gia_id"], "expected_revision": 1, "khoa": self.K("in1")})
        sau = self.dem()
        self.assertEqual((sau["xuat"] - trc["xuat"], sau["lich_thu"] - trc["lich_thu"], sau["hd"] - trc["hd"]), (1, 0, 0))
        pdf_dat = self.pdf_dat(x)
        st, docx_b, _ = self.goi(f"/api/crm/giao-ket/tep/{x['xuat_id']}/docx", cookie=self.sid(BH))
        self.assertEqual((st, hashlib.sha256(docx_b).hexdigest(), len(docx_b)), (200, x["docx_sha256"], x["docx_len"]))
        if pdf_dat:
            import pdfplumber
            st, pdf_b, _ = self.goi(f"/api/crm/giao-ket/tep/{x['xuat_id']}/pdf", cookie=self.sid(BH))
            self.assertTrue(pdf_b.startswith(b"%PDF-"))
            with pdfplumber.open(io.BytesIO(pdf_b), unicode_norm="NFC") as p:
                chu = "".join(pg.extract_text() or "" for pg in p.pages)
            so = self.q("SELECT so_bao_gia FROM master.crm_bao_gia WHERE id = %s", (r["bao_gia_id"],))
            for mong in (so, "1.000.000.000 VND", "400.000.000 VND", BH, "Báo giá DEMO chỉ để tham khảo"):
                self.assertIn(mong.replace(" ", ""), chu.replace(" ", "").replace("\n", ""), mong)
            self.assertIsNone(RE_UUID.search(chu))  # không mã nội bộ/định danh hệ thống
        else:
            st, r2, _ = self.goi(f"/api/crm/giao-ket/tep/{x['xuat_id']}/pdf", cookie=self.sid(BH))
            self.assertEqual((st, r2["error"]), (404, "CRM_G_TEP_KHONG_CO"))
        lai = self.ok(BH, "bao-gia/in", {"bao_gia_id": r["bao_gia_id"], "expected_revision": 1, "khoa": self.K("in1")})
        self.assertEqual((lai["lap_lai"], lai["xuat_id"], self.dem()["xuat"]), (True, x["xuat_id"], sau["xuat"]))  # cùng khóa: 0 render/0 ghi
        # tổng sai: chặn In nhưng Lưu được; Chuyển không bị cổng In chặn (kiểm ở g05)
        bad = self.bao_gia(lich=[{"lan": "1", "loai": "PERCENT", "ty_le": "40"}, {"lan": "2", "loai": "PERCENT", "ty_le": "50"}])
        r = self.ok(BH, "bao-gia/luu", {"bao_gia_id": r["bao_gia_id"], "expected_revision": 1, "du_lieu": bad, "khoa": self.K("bg1-r2")})
        self.assertEqual(r["revision"], 2)
        self.loi(BH, "bao-gia/in", {"bao_gia_id": r["bao_gia_id"], "expected_revision": 2, "khoa": self.K("in-bad")}, 409, "CRM_GK_CHAN_IN")
        self.loi(BH, "bao-gia/luu", {"bao_gia_id": r["bao_gia_id"], "expected_revision": 1, "du_lieu": bad, "khoa": self.K("bg1-cu")}, 409, "CRM_GK_REVISION_CU")

    # ------------------------------------------------------------------ g03 (c1): DTO/actor từ trình duyệt bị chặn; sai dạng số không làm tròn
    def test_g03_khong_nhan_authority_va_so_sai(self):
        self.loi(BH, "bao-gia/luu", {"du_lieu": self.bao_gia(), "khoa": self.K("x1"), "trang_thai": "NHAP"}, 403, "CRM_G_CLIENT_AUTHORITY")
        for xau in ("1,000", "-5", "1" * 25):
            self.loi(BH, "bao-gia/luu", {"bao_gia_id": None, "expected_revision": None, "du_lieu": self.bao_gia(gia={"tien_te": "VND", "tong": xau}),
                                         "khoa": self.K("so-" + str(len(xau)))}, 400, "CRM_GK_SO_SAI")

    # ------------------------------------------------------------------ g04 (c2): BG-1c — USD tham chiếu, FX mặc định/tay đổi tổng VND; G7 lệch/thiếu
    def test_g04_usd_fx_g7(self):
        # QD-20261025-01…04: Tổng VND = đơn giá USD × tỷ giá × diện tích, làm tròn đến đồng.
        g = {"tien_te": "USD", "don_gia": "1234.56", "dien_tich": "1", "co_so_thue": "GROSS"}
        r = self.ok(BH, "bao-gia/luu", {"bao_gia_id": None, "expected_revision": None, "du_lieu": self.bao_gia(gia=g), "khoa": self.K("usd")})
        mac_dinh = self.get(BH, "bao-gia/" + r["bao_gia_id"])
        self.assertEqual((mac_dinh["du_lieu"]["fx"]["ty_gia"], mac_dinh["du_lieu"]["fx"]["nguon"],
                          mac_dinh["tinh"]["tien_te"], mac_dinh["tinh"]["tong_minor"], mac_dinh["tinh"]["chan_in"]),
                         ("26000", "MAC_DINH", "VND", "32098560", []))
        fx1 = {"cap": "USD/VND", "ty_gia": "25000", "ngay": ngay(-1)}
        r = self.ok(BH, "bao-gia/luu", {"bao_gia_id": r["bao_gia_id"], "expected_revision": 1, "du_lieu": self.bao_gia(gia=g, fx=fx1), "khoa": self.K("usd2")})
        a = self.get(BH, "bao-gia/" + r["bao_gia_id"])
        self.assertEqual((a["tinh"]["tien_te"], a["tinh"]["tong_minor"], a["tinh"]["usd_tham_chieu"]["tong_minor"],
                          a["du_lieu"]["fx"]["nguoi_nhap"]), ("VND", "30864000", "123456", BH))
        self.assertIsNone(a["tinh"]["vnd_tham_chieu"])
        self.assertEqual([x["so_tien_minor"] for x in a["tinh"]["dong"]], ["12345600", "18518400"])
        r = self.ok(BH, "bao-gia/luu", {"bao_gia_id": r["bao_gia_id"], "expected_revision": 2,
                                        "du_lieu": self.bao_gia(gia=g, fx={**fx1, "ty_gia": "25100.5"}), "khoa": self.K("usd3")})
        b = self.get(BH, "bao-gia/" + r["bao_gia_id"])
        self.assertEqual((b["tinh"]["tien_te"], b["tinh"]["tong_minor"], b["tinh"]["usd_tham_chieu"]["tong_minor"],
                          b["tinh"]["tong_lam_tron"], b["du_lieu"]["fx"]["nguoi_nhap"]), ("VND", "30988073", "123456", True, BH))
        r = self.ok(BH, "bao-gia/luu", {"bao_gia_id": None, "expected_revision": None, "khoa": self.K("g7"),
                                        "du_lieu": self.bao_gia(nguon_lich="DU_AN", giai_doan_g7="GK_STAGE",
                                                                lich=[{"lan": "1", "loai": "PERCENT", "ty_le": "30", "moc_loai": "SU_KIEN", "moc_su_kien": "KY_HD"},
                                                                      {"lan": "2", "loai": "PERCENT", "ty_le": "70"}])})
        c = self.get(BH, "bao-gia/" + r["bao_gia_id"])
        self.assertEqual(c["g7"]["trang_thai"], "HIEU_LUC")
        self.assertEqual([x["ma"] for x in c["tinh"]["g7_lech"]], ["LECH_G7_TY_LE", "LECH_G7_TY_LE"])
        r = self.ok(BH, "bao-gia/luu", {"bao_gia_id": None, "expected_revision": None, "khoa": self.K("g7-khong"),
                                        "du_lieu": self.bao_gia(nguon_lich="DU_AN", giai_doan_g7="KHONG_CO_GD")})
        d = self.get(BH, "bao-gia/" + r["bao_gia_id"])
        self.assertIn("THIEU_G7", [x["ma"] for x in d["tinh"]["canh_bao"]])
        self.assertEqual(d["tinh"]["g7_lech"], [])

    # ------------------------------------------------------------------ g05 (c3): chuyển hai lần cùng khóa → một HĐ; quyền/PN trước tra cứu
    def test_g05_chuyen_mot_hop_dong_va_quyen(self):
        # TL 45 BG-02 (Anh chốt 23/10, mới hơn handoff 41-03): Σ% ≠ 100 → máy chủ chặn cả In lẫn Chuyển.
        r40 = self.ok(BH, "bao-gia/luu", {"bao_gia_id": None, "expected_revision": None, "khoa": self.K("cv40"),
                                          "du_lieu": self.bao_gia(lich=[{"lan": "1", "loai": "PERCENT", "ty_le": "40"}])})
        self.loi(BH, "bao-gia/chuyen", {"bao_gia_id": r40["bao_gia_id"], "expected_revision": 1, "mau_phien_ban_id": self.s["v1"],
                                        "khoa": self.K("cv40-1")}, 409, "CRM_GK_CHAN_CHUYEN")
        r = self.ok(BH, "bao-gia/luu", {"bao_gia_id": None, "expected_revision": None, "khoa": self.K("cv"),
                                        "du_lieu": self.bao_gia(lich=[{"lan": "1", "loai": "PERCENT", "ty_le": "100"}])})  # tổng 100% — Chuyển được
        bg = r["bao_gia_id"]
        lich_bg = self.get(BH, "bao-gia/" + bg)["du_lieu"]["lich"]
        self.loi(KT_NO_CRM, "bao-gia/chuyen", {"bao_gia_id": bg, "expected_revision": 1, "mau_phien_ban_id": self.s["v1"], "khoa": self.K("cv-x")}, 404,
                 "CRM_G_KHONG_THAY")  # không module CRM: từ chối TRƯỚC tra biên nhận/hiệu ứng
        self.loi(CFO_B, "bao-gia/" + "chuyen", {"bao_gia_id": bg, "expected_revision": 1, "mau_phien_ban_id": self.s["v1"], "khoa": self.K("cv-b")}, 404,
                 "CRM_G_KHONG_THAY")  # khác PN
        self.get(CFO_B, "bao-gia/" + bg, status=404)
        trc = self.dem()
        body = {"bao_gia_id": bg, "expected_revision": 1, "mau_phien_ban_id": self.s["v1"], "khoa": self.K("cv-1")}
        a = self.ok(BH, "bao-gia/chuyen", body)
        b = self.ok(BH, "bao-gia/chuyen", body)
        sau = self.dem()
        self.assertEqual((a["hop_dong_id"], a["soan_id"], b["lap_lai"]), (b["hop_dong_id"], b["soan_id"], True))
        self.assertEqual((sau["hd"] - trc["hd"], sau["soan"] - trc["soan"], sau["lich_thu"] - trc["lich_thu"]), (1, 1, 0))
        self.loi(BH, "bao-gia/chuyen", {**body, "khoa": self.K("cv-2")}, 409, "CRM_GK_DA_CHUYEN")  # khóa khác: không HĐ thứ hai
        hd = self.admin.execute("SELECT trang_thai, crm_giao_ket, phien_ban_hien_hanh FROM master.hop_dong WHERE id = %s", (a["hop_dong_id"],)).fetchone()
        self.assertEqual(tuple(hd), ("SOAN_THAO", "SOAN_THAO", None))  # không hiệu lực mặc định
        so = self.get(BH, "soan/" + a["soan_id"])
        self.assertEqual([x["dong_id"] for x in so["du_lieu"]["bao_gia"]["lich"]], [x["dong_id"] for x in lich_bg])  # cùng row ID/thứ tự
        self.assertEqual(so["du_lieu"]["gia_tri_truong"]["gia_tri_hop_dong"], {"so_tien": "1000000000", "tien_te": "VND"})
        self.s["soan"], self.s["hd"] = a["soan_id"], a["hop_dong_id"]
        # FIX03 R5 (TEST ONLY): discriminator chỉ hàm lệnh chủ bảng ghi; login ứng dụng (non-owner, NOBYPASSRLS) không sửa được.
        sua = "UPDATE master.hop_dong SET crm_giao_ket = 'CHO_KY', trang_thai = 'CHO_KY' WHERE id = %s"  # UPDATE GỐC, không đổi
        dem_thay = "SELECT count(*) FROM master.hop_dong WHERE id = %s"
        anh = lambda: self.admin.execute("SELECT md5(row_to_json(h)::text) FROM master.hop_dong h WHERE id = %s",  # noqa: E731 — owner quan sát TOÀN dòng
                                         (a["hop_dong_id"],)).fetchone()[0]
        truoc = anh()
        self.assertIsNotNone(truoc)
        # (a) đối chứng KHÔNG context trên kết nối thường mới: RLS lọc → thấy 0 dòng, UPDATE gốc tác động 0 dòng, không lỗi. Đây là bằng chứng lọc RLS,
        # KHÔNG phải bằng chứng guard đã chạy.
        with psycopg.connect(self.app_dsn, autocommit=True) as c:
            self.assertEqual(c.execute(dem_thay, (a["hop_dong_id"],)).fetchone()[0], 0)
            self.assertEqual(c.execute(sua, (a["hop_dong_id"],)).rowcount, 0)
        self.assertEqual(anh(), truoc)
        # (b) ĐÚNG ordinary context của actor BH (cùng hợp đồng danh tính/giao dịch hiện có `crm_mau._tx`: LOCAL ktt.nguoi_dung_id + ktt.nguoi_dung_dang_nhap
        # trong giao dịch tường minh) trên kết nối thường mới KHÁC: thấy đúng 1 dòng → UPDATE gốc bị guard chặn P0001/CRM_G_CHI_CHU.
        aid = str(self.q("SELECT id FROM master.nguoi_dung WHERE dang_nhap = %s", (BH,)))
        with self.assertRaises(psycopg.Error) as cm:
            with psycopg.connect(self.app_dsn) as c:  # autocommit=False
                with c.transaction():
                    c.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true)", (aid, BH))
                    self.assertEqual(c.execute(dem_thay, (a["hop_dong_id"],)).fetchone()[0], 1)  # AssertionError ≠ psycopg.Error → không lọt qua
                    c.execute(sua, (a["hop_dong_id"],))
        self.assertEqual(cm.exception.sqlstate, "P0001", cm.exception)
        self.assertTrue(str(cm.exception.diag.message_primary or "").startswith("CRM_G_CHI_CHU"), cm.exception.diag.message_primary)
        self.assertEqual(anh(), truoc)  # sau khi giao dịch đóng: toàn dòng nguyên vẹn
        self.assertEqual(tuple(self.admin.execute("SELECT trang_thai, crm_giao_ket FROM master.hop_dong WHERE id = %s", (a["hop_dong_id"],)).fetchone()),
                         ("SOAN_THAO", "SOAN_THAO"))

    # ------------------------------------------------------------------ g06 (c5): xuất v1 → CFO làm v2 → v1 vẫn mở/render đúng; đổi mẫu tường minh
    def test_g06_mau_ghim_lich_su_va_doi_mau(self):
        sid = self.s["soan"]
        so = self.get(BH, "soan/" + sid)
        self.assertIn("THIEU_GIA_TRI_BAT_BUOC", [x["ma"] for x in so["kiem"]["chan_xuat"]])  # required value thiếu → chặn Xuất
        self.assertIn("TONG_TY_LE_KHAC_100", [x["ma"] for x in so["kiem"]["chan_xuat"]])
        self.loi(BH, "soan/xuat", {"soan_id": sid, "expected_revision": 1, "khoa": self.K("x0")}, 409, "CRM_GK_CHAN_XUAT")
        bg = dict(so["du_lieu"]["bao_gia"])
        bg["lich"] = so["du_lieu"]["bao_gia"]["lich"] + [{"lan": "2", "loai": "PERCENT", "ty_le": "60"}]
        bg["fx"] = None
        gt = {"so_hop_dong": "HĐ-DEMO-GK-0001", "ngay_ky": ngay(0), "ten_hien_thi_demo": "NGƯỜI MUA DEMO",
              "gia_tri_hop_dong": {"so_tien": "1000000000", "tien_te": "VND"}}
        r = self.ok(BH, "soan/luu", {"soan_id": sid, "expected_revision": 1, "gia_tri_truong": gt, "bao_gia": bg, "khoa": self.K("so-2")})
        self.assertEqual(r["revision"], 2)
        x = self.ok(BH, "soan/xuat", {"soan_id": sid, "expected_revision": 2, "khoa": self.K("x1")})
        self.s["soan_pdf_dat"] = self.pdf_dat(x)
        tt = self.q("SELECT trang_thai FROM master.crm_hd_soan WHERE id = %s", (sid,))
        self.assertEqual(tt, "CHO_KY" if self.s["soan_pdf_dat"] else "SOAN_THAO")  # PDF chưa sẵn sàng → KHÔNG CHO_KY
        docx1 = self.goi(f"/api/crm/giao-ket/tep/{x['xuat_id']}/docx", cookie=self.sid(BH))[1]
        self.assertEqual(hashlib.sha256(docx1).hexdigest(), x["docx_sha256"])
        v2, v2_sha = self.mau_hieu_luc("HD_GK_" + self.run_id, ngay(-1), "MAU V2")  # cùng mã mẫu → v2; đóng v1
        so = self.get(BH, "soan/" + sid)
        self.assertEqual((so["mau"]["mau_phien_ban_id"], so["mau"]["raw_sha256"]), (self.s["v1"], self.s["v1_sha"]))  # vẫn ghim v1
        self.assertEqual([m["mau_phien_ban_id"] for m in so["mau_hieu_luc"]], [v2])  # picker chỉ mẫu hiệu lực
        r = self.ok(BH, "soan/luu", {"soan_id": sid, "expected_revision": 2, "gia_tri_truong": gt, "khoa": self.K("so-3")})  # sửa → rev mới vẫn v1
        x2 = self.ok(BH, "soan/xuat", {"soan_id": sid, "expected_revision": 3, "khoa": self.K("x2")})
        self.s["soan_pdf_dat"] = self.pdf_dat(x2)  # lưu revision mới đã đưa bản soạn về SOAN_THAO
        doc_xml = lambda b: zipfile.ZipFile(io.BytesIO(b)).read("word/document.xml")  # noqa: E731 — zip có dấu thời gian; so nội dung phần
        docx2 = self.goi(f"/api/crm/giao-ket/tep/{x2['xuat_id']}/docx", cookie=self.sid(BH))[1]
        self.assertEqual(doc_xml(docx2), doc_xml(docx1))  # vẫn render từ mẫu v1 đã ghim
        self.assertIn("MAU V1".encode(), doc_xml(docx2))
        self.loi(BH, "soan/luu", {"soan_id": sid, "expected_revision": 3, "gia_tri_truong": gt, "doi_mau_phien_ban_id": v2, "khoa": self.K("so-4x")},
                 400, "CRM_GK_THIEU_LY_DO")
        r = self.ok(BH, "soan/luu", {"soan_id": sid, "expected_revision": 3, "gia_tri_truong": gt, "doi_mau_phien_ban_id": v2, "ly_do": "Đổi sang mẫu v2",
                                     "khoa": self.K("so-4")})
        so = self.get(BH, "soan/" + sid)
        self.assertEqual((so["mau"]["mau_phien_ban_id"], so["mau"]["raw_sha256"], so["soan"]["revision_hien_hanh"]), (v2, v2_sha, 4))
        x3 = self.ok(BH, "soan/xuat", {"soan_id": sid, "expected_revision": 4, "khoa": self.K("x3")})
        self.s["soan_pdf_dat"] = self.pdf_dat(x3)
        docx3 = self.goi(f"/api/crm/giao-ket/tep/{x3['xuat_id']}/docx", cookie=self.sid(BH))[1]
        self.assertIn("MAU V2".encode(), doc_xml(docx3))  # mẫu mới → tệp mới
        self.assertNotEqual(x3["docx_sha256"], x["docx_sha256"])
        self.assertEqual(hashlib.sha256(self.goi(f"/api/crm/giao-ket/tep/{x['xuat_id']}/docx", cookie=self.sid(BH))[1]).hexdigest(), x["docx_sha256"])
        self.get(CFO_B, "soan/" + sid, status=404)  # bản soạn mượn ID khác PN
        self.loi(BH, "soan/luu", {"soan_id": sid, "expected_revision": 4, "gia_tri_truong": gt, "doi_mau_phien_ban_id": str(uuid.uuid4()),
                                  "ly_do": "x", "khoa": self.K("so-mau-la")}, 404, "CRM_G_KHONG_THAY")

    # ------------------------------------------------------------------ g07 (c6): PDF lỗi giữ DOCX; revision đổi khi render → DA_CU; quyền đổi khi render
    def test_g07_pdf_loi_va_doi_trong_luc_render(self):
        from kho_tri_thuc.k2 import crm_giao_ket as GK
        from kho_tri_thuc.nguon import crm_docx as R
        sid = self.s["soan"]
        rev = self.q("SELECT revision_hien_hanh FROM master.crm_hd_soan WHERE id = %s", (sid,))
        # FIX01 (fixture g07): g06 có thể đã đưa bản soạn sang CHO_KY (PDF_DAT thật). PDF lỗi của lần SAU không được đổi trạng thái theo bất kỳ
        # hướng nào: không CHO_KY giả, cũng không hạ về SOAN_THAO — trạng thái/discriminator trước đó giữ nguyên.
        truoc = tuple(self.admin.execute("""SELECT s.trang_thai, h.trang_thai, h.crm_giao_ket FROM master.crm_hd_soan s JOIN master.hop_dong h
                                             ON h.id = s.hop_dong_id WHERE s.id = %s""", (sid,)).fetchone())
        self.assertEqual(truoc[0], "CHO_KY" if self.s["soan_pdf_dat"] else "SOAN_THAO", truoc)  # kết quả xuất thực tế ở g06
        with patch.object(R, "chuyen_pdf", lambda lan, p, han=0: {"trang_thai": "PDF_LOI", "ly_do": "GIA_LAP_LOI", "pha": "XUAT"}):
            x = self.ok(BH, "soan/xuat", {"soan_id": sid, "expected_revision": rev, "khoa": self.K("pdfloi")})
        self.assertEqual((x["trang_thai"], x["pdf_sha256"]), ("PDF_LOI", None))
        sau = tuple(self.admin.execute("""SELECT s.trang_thai, h.trang_thai, h.crm_giao_ket FROM master.crm_hd_soan s JOIN master.hop_dong h
                                           ON h.id = s.hop_dong_id WHERE s.id = %s""", (sid,)).fetchone())
        self.assertEqual(sau, truoc)
        self.assertEqual(self.goi(f"/api/crm/giao-ket/tep/{x['xuat_id']}/docx", cookie=self.sid(BH))[0], 200)  # DOCX giữ
        goc_render = GK.CrmGiaoKetK2.render
        gt = self.get(BH, "soan/" + sid)["du_lieu"]["gia_tri_truong"]

        def render_roi_sua(self_, kh):  # trong lúc render (NGOÀI khóa) một người khác lưu revision mới
            st, r, _ = CrmGiaoKetHttp.goi(t, "/api/crm/soan/luu", {"soan_id": sid, "expected_revision": rev, "gia_tri_truong": gt,
                                                                   "khoa": t.K("chen")}, t.sid(KT))
            assert st == 200, r
            return goc_render(self_, kh)
        t = self
        with patch.object(GK.CrmGiaoKetK2, "render", render_roi_sua):
            x = self.ok(BH, "soan/xuat", {"soan_id": sid, "expected_revision": rev, "khoa": self.K("stale")})
        self.assertEqual((x["trang_thai"], x["da_cu"]), ("DA_CU", True))  # không gắn tệp như hiện hành
        rev2 = rev + 1

        def render_roi_thu_hoi(self_, kh):
            t.admin.execute("""UPDATE master.phan_quyen SET module = array_remove(module, 'CRM') WHERE nguoi_dung_id =
                               (SELECT id FROM master.nguoi_dung WHERE dang_nhap = %s)""", (BH,))
            return goc_render(self_, kh)
        trc = self.dem()
        try:
            with patch.object(GK.CrmGiaoKetK2, "render", render_roi_thu_hoi):
                st, r, _ = self.goi("/api/crm/soan/xuat", {"soan_id": sid, "expected_revision": rev2, "khoa": self.K("revoke")}, self.sid(BH))
            self.assertIn(st, (403, 404), r)  # quyền hiện hành kiểm lại trước công bố
            self.assertEqual(self.dem()["xuat"], trc["xuat"])
        finally:
            self.admin.execute("""UPDATE master.phan_quyen SET module = array_append(module, 'CRM') WHERE nguoi_dung_id =
                                  (SELECT id FROM master.nguoi_dung WHERE dang_nhap = %s) AND NOT ('CRM' = ANY(module))""", (BH,))

    def tao_soan(self, ten, gia=None, lich=None, gt=None):
        """FIX01: một bản soạn MỚI qua luồng thật (lưu báo giá → chuyển với mẫu hiệu lực hiện tại → [lưu trường]) — trả (bao_gia_id, soan_id, rev)."""
        d = self.bao_gia(**({"gia": gia} if gia else {}), **({"lich": lich} if lich else {}))
        r = self.ok(BH, "bao-gia/luu", {"bao_gia_id": None, "expected_revision": None, "du_lieu": d, "khoa": self.K(ten + "-bg")})
        mau = self.get(BH, "bao-gia/" + r["bao_gia_id"])["mau_hieu_luc"][0]["mau_phien_ban_id"]
        cv = self.ok(BH, "bao-gia/chuyen", {"bao_gia_id": r["bao_gia_id"], "expected_revision": 1, "mau_phien_ban_id": mau, "khoa": self.K(ten + "-cv")})
        if gt is None:
            return r["bao_gia_id"], cv["soan_id"], 1
        s = self.ok(BH, "soan/luu", {"soan_id": cv["soan_id"], "expected_revision": 1, "gia_tri_truong": gt, "khoa": self.K(ten + "-so")})
        return r["bao_gia_id"], cv["soan_id"], s["revision"]

    @staticmethod
    def gt_du(gia_tri=None):
        return {"so_hop_dong": "HĐ-DEMO-GK-0009", "ngay_ky": ngay(0), "ten_hien_thi_demo": "NGƯỜI MUA DEMO",
                "gia_tri_hop_dong": gia_tri or {"so_tien": "1000000000", "tien_te": "VND"}}

    # ------------------------------------------------------------------ g08 (c3) + FIX01 #5: cùng khóa khi lần đầu đang render → đối soát, không
    # render mù/UUID mới/Word mới; khác body cùng khóa → 409; replay sau FINAL → biên nhận cũ. Đếm render, lần đặt chỗ, thư mục lần chạy.
    def test_g08_dong_thoi_cung_khoa(self):
        from kho_tri_thuc.giao_dien.crm_g import dich_vu_gk
        from kho_tri_thuc.k2 import crm_giao_ket as GK
        lich = [{"lan": "1", "loai": "PERCENT", "ty_le": "40", "moc_loai": "SU_KIEN", "moc_su_kien": "KY_HD"}, {"lan": "2", "loai": "PERCENT", "ty_le": "60"}]
        _, sid, rev = self.tao_soan("g8a", lich=lich, gt=self.gt_du())
        _, sid2, rev2 = self.tao_soan("g8b", lich=lich, gt=self.gt_du())
        kho_lan = dich_vu_gk(self.app).kho / "lan"
        lan0 = {p.name for p in kho_lan.iterdir()} if kho_lan.is_dir() else set()
        n_lan0, trc = self.q("SELECT count(*) FROM master.crm_gk_lan"), self.dem()
        goc, dang, tha, renders = GK.CrmGiaoKetK2._render_trong, threading.Event(), threading.Event(), []

        def render_cho(self_, kh, lan):  # lần 1 dừng giữa pha B (đã đặt chỗ, chưa có kết quả) cho tới khi ca cho phép
            renders.append(kh["lan_id"])
            dang.set()
            tha.wait(300)
            return goc(self_, kh, lan)
        body = {"soan_id": sid, "expected_revision": rev, "khoa": self.K("dt")}
        kq, loi = [], []

        def mot():
            try:
                kq.append(self.goi("/api/crm/soan/xuat", body, self.sid(BH))[:2])
            except BaseException as e:  # noqa: BLE001
                loi.append(e)
        t1 = threading.Thread(target=mot)
        try:
            with patch.object(GK.CrmGiaoKetK2, "_render_trong", render_cho):
                t1.start()
                self.assertTrue(dang.wait(300), "lần 1 không tới pha render")
                self.loi(BH, "soan/xuat", body, 409, "CRM_GK_DANG_XU_LY")  # cùng khóa/body: đối soát → chưa có kết quả → không render lần hai
                self.loi(BH, "soan/xuat", {"soan_id": sid2, "expected_revision": rev2, "khoa": self.K("dt")}, 409, "CRM_G_IDEMPOTENCY_KHAC")
                self.assertEqual(len(renders), 1)
        finally:
            tha.set()
            t1.join(900)
        self.assertEqual((t1.is_alive(), loi, len(kq)), (False, [], 1))
        st, r1 = kq[0]
        self.assertEqual(st, 200, r1)
        lai = self.ok(BH, "soan/xuat", body)  # replay sau FINAL: biên nhận cũ, 0 render
        self.assertEqual((lai["lap_lai"], lai["xuat_id"]), (True, r1["xuat_id"]))
        self.loi(BH, "soan/xuat", {**body, "expected_revision": rev + 1}, 409, "CRM_G_IDEMPOTENCY_KHAC")  # khác body sau FINAL
        self.assertEqual(len(renders), 1)  # đúng MỘT lần render/Word cho khóa này
        self.assertEqual(self.dem()["xuat"] - trc["xuat"], 1)
        self.assertEqual(self.q("SELECT count(*) FROM master.crm_gk_lan") - n_lan0, 1)  # một chỗ đặt
        self.assertEqual(self.q("SELECT trang_thai FROM master.crm_gk_lan WHERE id = %s", (renders[0],)), "DA_CONG_BO")
        self.assertEqual({p.name for p in kho_lan.iterdir()} - lan0, {renders[0]})  # một thư mục lần chạy = định danh chỗ đặt
        self.assertTrue((kho_lan / renders[0] / "ket_qua.json").is_file())

    # ------------------------------------------------------------------ g09 FIX01 #6: thu hồi quyền khi lệnh đang chờ khóa namespace
    def test_g09_thu_hoi_khi_cho_khoa_namespace(self):
        r = self.ok(BH, "bao-gia/luu", {"bao_gia_id": None, "expected_revision": None, "du_lieu": self.bao_gia(), "khoa": self.K("g9")})
        bg = r["bao_gia_id"]
        pn = str(self.q("SELECT phap_nhan_id FROM master.crm_bao_gia WHERE id = %s", (bg,)))
        aid = str(self.q("SELECT id FROM master.nguoi_dung WHERE dang_nhap = %s", (BH,)))
        body = {"bao_gia_id": bg, "expected_revision": 1, "ly_do": "thử thu hồi khi chờ", "khoa": self.K("g9-huy")}
        bo = """UPDATE master.phan_quyen SET module = array_remove(module, 'CRM') WHERE nguoi_dung_id = %s"""
        tra = """UPDATE master.phan_quyen SET module = array_append(module, 'CRM') WHERE nguoi_dung_id = %s AND NOT ('CRM' = ANY(module))"""
        giu = psycopg.connect(self.dsn)  # giao dịch mở giữ ĐÚNG khóa namespace của (PN, actor, CRM_BAO_GIA_HUY, khóa)
        self.addCleanup(_dong, giu)
        giu.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"crm_g|{pn}|{aid}|CRM_BAO_GIA_HUY|{body['khoa']}",))
        kq = []
        t = threading.Thread(target=lambda: kq.append(self.goi("/api/crm/bao-gia/huy", body, self.sid(BH))[:2]))
        t.start()
        try:
            het = time.monotonic() + 60
            while self.q("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND NOT granted") == 0:  # lệnh đã TỚI chờ khóa namespace
                self.assertLess(time.monotonic(), het, "lệnh hủy không tới chờ khóa namespace")
                time.sleep(0.05)
            with psycopg.connect(self.dsn, autocommit=True) as rv:  # quyền đã ghim FOR SHARE TRƯỚC khi chờ → thu hồi bị chặn, không lọt giữa chừng
                rv.execute("SET lock_timeout = '1s'")
                with self.assertRaises(psycopg.errors.LockNotAvailable):
                    rv.execute(bo, (aid,))
        finally:
            giu.commit()  # nhả khóa namespace
            t.join(300)
        self.assertEqual(kq[0][0], 200, kq)
        self.assertEqual(self.q("SELECT trang_thai FROM master.crm_bao_gia WHERE id = %s", (bg,)), "HUY")
        try:
            self.admin.execute(bo, (aid,))  # thu hồi SAU khi lệnh xong
            st, r2, _ = self.goi("/api/crm/bao-gia/huy", body, self.sid(BH))
            self.assertIn(st, (403, 404), r2)  # replay đúng khóa/body: quyền hiện hành kiểm TRƯỚC biên nhận → từ chối, không trả FINAL cũ
        finally:
            self.admin.execute(tra, (aid,))

    # ------------------------------------------------------------------ g10 FIX01 #4/#7/#8: tính thử chỉ đọc; mốc trống in được; tổng canonical
    def test_g10_tinh_thu_moc_trong_tong_canonical(self):
        g = {"tien_te": "USD", "tong": "1000.00", "co_so_thue": "NET"}
        lich = [{"lan": "1", "loai": "AMOUNT", "so_tien": "123.45", "tien_te": "USD", "moc_loai": "NGAY"},  # NGAY nhưng chưa có ngày
                {"lan": "2", "loai": "PERCENT", "ty_le": "87.655", "moc_loai": "SU_KIEN"}]  # SU_KIEN nhưng chưa có sự kiện
        d = self.bao_gia(gia=g, lich=lich, fx={"cap": "USD/VND", "ty_gia": "25000", "ngay": ngay(-1)})
        trc = self.dem()
        x = self.ok(BH, "bao-gia/xem-truoc", {"du_lieu": d})
        self.assertEqual([(r["so_tien_minor"], r["ty_le"]) for r in x["tinh"]["dong"]], [("12345", "12.345"), ("87655", "87.655")])
        self.assertEqual((x["tinh"]["tong_ty_le"], x["tinh"]["vnd_tham_chieu"]["dong"]), ("100", ["3086250", "21913750"]))
        self.assertEqual(sorted(c["dong"] for c in x["tinh"]["canh_bao"] if c["ma"] == "MOC_TRONG"), [1, 2])
        self.assertEqual(x["tinh"]["chan_in"], [])
        self.assertEqual(self.dem(), trc)  # tính thử không ghi gì
        self.loi(BH, "bao-gia/xem-truoc", {"du_lieu": d, "khoa": self.K("x")}, 400, "CRM_G_YEU_CAU_SAI")
        r = self.ok(BH, "bao-gia/luu", {"bao_gia_id": None, "expected_revision": None, "du_lieu": d, "khoa": self.K("g10-bg")})
        cot = lambda t: [(z["so_tien_minor"], z["ty_le"], z["loi"]) for z in t["dong"]]  # noqa: E731 — dong_id do máy chủ cấp khi lưu
        self.assertEqual(cot(self.get(BH, "bao-gia/" + r["bao_gia_id"])["tinh"]), cot(x["tinh"]))  # cùng phép tính của dịch vụ
        p = self.ok(BH, "bao-gia/in", {"bao_gia_id": r["bao_gia_id"], "expected_revision": 1, "khoa": self.K("g10-in")})  # mốc trống: in được
        self.assertEqual(p["trang_thai"], "PDF_DAT" if self.co_word else "PDF_CHUA_SAN_SANG", p)
        xml = zipfile.ZipFile(io.BytesIO(self.goi(f"/api/crm/giao-ket/tep/{p['xuat_id']}/docx", cookie=self.sid(BH))[1])).read("word/document.xml")
        chu = re.sub(r"<[^>]+>", "", xml.decode("utf-8"))
        for m in ("Ngày: chưa xác định", "Sự kiện: chưa xác định", "Tỷ giá tham chiếu USD/VND = 25000", BH, "KHÁCH DỰ THẢO DEMO"):
            self.assertIn(m, chu, m)
        # tổng canonical: NET → chuyển điền sẵn ĐÚNG trường profile.kiem_tong; GROSS → không điền; khác tổng/khác cơ sở → chặn Xuất
        mau = self.get(BH, "bao-gia/" + r["bao_gia_id"])["mau_hieu_luc"][0]["mau_phien_ban_id"]
        cv = self.ok(BH, "bao-gia/chuyen", {"bao_gia_id": r["bao_gia_id"], "expected_revision": 1, "mau_phien_ban_id": mau, "khoa": self.K("g10-cv")})
        self.assertEqual(self.get(BH, "soan/" + cv["soan_id"])["du_lieu"]["gia_tri_truong"], {"gia_tri_hop_dong": {"so_tien": "1000", "tien_te": "USD"}})
        _, sid, rv = self.tao_soan("g10-lech", gt=self.gt_du({"so_tien": "999999999", "tien_te": "VND"}))
        so = self.get(BH, "soan/" + sid)
        self.assertIn("TONG_TRUONG_KHAC_TONG_LICH", [c["ma"] for c in so["kiem"]["chan_xuat"]])
        self.loi(BH, "soan/xuat", {"soan_id": sid, "expected_revision": rv, "khoa": self.K("g10-x1")}, 409, "CRM_GK_CHAN_XUAT")
        _, sid, _ = self.tao_soan("g10-gross", gia={"tien_te": "VND", "tong": "1000000000", "co_so_thue": "GROSS"})
        self.assertEqual(self.get(BH, "soan/" + sid)["du_lieu"]["gia_tri_truong"], {})  # không suy NET/GROSS, không điền mù
        s = self.ok(BH, "soan/luu", {"soan_id": sid, "expected_revision": 1, "gia_tri_truong": self.gt_du(), "khoa": self.K("g10-gross-so")})
        so = self.get(BH, "soan/" + sid)
        self.assertIn("CO_SO_TONG_KHONG_KHOP", [c["ma"] for c in so["kiem"]["chan_xuat"]])
        self.loi(BH, "soan/xuat", {"soan_id": sid, "expected_revision": s["revision"], "khoa": self.K("g10-x2")}, 409, "CRM_GK_CHAN_XUAT")


class PdfGuard(unittest.TestCase):
    """Hồi quy thuần: không PostgreSQL/server/Word; guard và lỗi quyền phải giữ DOCX thật."""

    def test_guard_chan_truoc_spawn_giu_docx(self):
        from kho_tri_thuc.k2 import crm_giao_ket as GK
        from kho_tri_thuc.nguon import crm_docx as R, trich6_host as H
        root = Path(tempfile.mkdtemp(prefix="ktt_t_pdf_"))  # giữ bằng chứng, không cleanup
        mau = type("MauGia", (), {"root": root})()
        gk = GK.CrmGiaoKetK2(mau)
        nd = {"so_bao_gia": "BG-DEMO", "ngay": "25/10/2026", "nguoi_lap": BH, "khach": "KHÁCH DEMO"}
        with patch.object(R, "_winword_ok", return_value=None), \
                patch.object(H, "chung_cu_guard", return_value={"module": False}), \
                patch.object(H, "_JobWindows") as job, patch.object(R.subprocess, "Popen") as popen:
            kq = gk.render({"loai": "BAO_GIA", "nd": nd, "mong_doi": [], "ten": "BG-DEMO", "lan_id": str(uuid.uuid4())})
        job.assert_not_called()
        popen.assert_not_called()
        self.assertEqual((kq["ly_do"], kq["kiem"]["pha"]), ("GUARD_KHONG_NAP", "KIEM_GUARD"))
        x = {**kq, "docx_sha256": kq["docx_sha"], "pdf_sha256": kq["pdf_sha"]}
        self.assertFalse(kiem_ket_qua_pdf(self, x, kq["ly_do"], kq["kiem"], True))  # metadata Word đủ vẫn bị guard chặn
        docx_b = (gk.kho / "tep" / kq["docx_sha"]).read_bytes()
        self.assertEqual((hashlib.sha256(docx_b).hexdigest(), len(docx_b)), (kq["docx_sha"], kq["docx_len"]))
        with zipfile.ZipFile(io.BytesIO(docx_b)) as z:
            self.assertIn("BÁO GIÁ", z.read("word/document.xml").decode("utf-8"))

    def test_worker_bi_chan_quyen_khong_thanh_pdf_dat(self):
        from kho_tri_thuc.nguon import crm_docx as R, trich6_host as H
        lan = Path(tempfile.mkdtemp(prefix="ktt_t_pdf_worker_"))
        vao = lan / "bao-gia.docx"
        raw = mau_docx()
        vao.write_bytes(raw)
        cfg = {"goc": str(lan), "vao": str(vao), "ra": str(lan / "bao-gia.pdf"),
               "vao_sha256": hashlib.sha256(raw).hexdigest(), "winword": str(R.WINWORD_GHIM)}
        kenh = io.StringIO()
        with patch.object(H, "guard_hop_le", return_value=None), patch.object(R, "_winword_ok", return_value=None), \
                patch.object(R.WordSoHuu, "tao", side_effect=PermissionError("guard")), \
                patch.object(R, "_k32") as native:
            self.assertEqual(R._worker(io.BytesIO(json.dumps(cfg).encode("utf-8") + b"\n"), kenh), 5)
        native.assert_not_called()  # không CreateProcessW/Word
        xong = json.loads(kenh.getvalue())
        kq = R._ket_luan(xong, {}, 5, True, lan / "bao-gia.pdf", "CHO_WORKER")
        self.assertEqual(kq["ly_do"], "COM_TAO_WORD:PermissionError")
        x = {**kq, "pdf_sha256": None, "pdf_len": None, "docx_sha256": cfg["vao_sha256"], "docx_len": len(raw)}
        self.assertFalse(kiem_ket_qua_pdf(self, x, kq["ly_do"], {"word": kq["word"]}, True))
        self.assertEqual(vao.read_bytes(), raw)
        for ly_do in ("COM_XUAT:ValueError", "WORD_CHUA_XAC_NHAN_DUNG", "LOI_KHONG_RO"):
            with self.subTest(ly_do=ly_do), self.assertRaises(AssertionError):
                kiem_ket_qua_pdf(self, x, ly_do, {}, True)  # không nuốt lỗi sản phẩm thành policy
        with self.assertRaises(AssertionError):
            kiem_ket_qua_pdf(self, {**x, "trang_thai": "PDF_DAT"}, None, {"word": {"pid": 1, "gan_job": True, "da_dung": None}}, True)
        dat = {**x, "trang_thai": "PDF_DAT", "pdf_sha256": "a" * 64, "pdf_len": 100}
        chung_cu = {"word": {"pid": 1, "gan_job": True, "da_dung": True}}  # fixture, không phải Word thật
        self.assertTrue(kiem_ket_qua_pdf(self, dat, None, chung_cu, True))
        with self.assertRaises(AssertionError):
            kiem_ket_qua_pdf(self, dat, None, chung_cu, False)  # có kết quả nhưng metadata/guard không đủ → không nhận


if __name__ == "__main__":
    unittest.main()
