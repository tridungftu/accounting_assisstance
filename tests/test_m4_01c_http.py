"""M4-01C — kiểm HTTP thật Cổng hồ sơ trên LocalApp/LocalServer + PostgreSQL DEMO mới (CODE_ONLY: coder viết, CHƯA CHẠY — NOT_RUN).

Chạy khi Root cấp KHO_PG_DSN_TEST qua env lúc chạy (không đọc .env/var, không hardcode credentials). DB mới `kho_test_m4c_*` migrate mặc định (1–17),
seed CRM DEMO + M4 DEMO; login ứng dụng tạm (NOSUPERUSER NOBYPASSRLS IN ROLE app_web) + admin DSN cho factory đường ghi nguồn tin cậy hiện hành.
HTTP loopback cổng ngẫu nhiên, cùng token/cookie như trình duyệt. Không DROP/DELETE/TRUNCATE/cleanup — DB/role/thư mục giữ làm bằng chứng.
Thiếu driver/DSN → skip = NOT_RUN. Ca cần lõi nguồn đã nạp (trích/BOQ) skip riêng khi chưa nạp. Không chứng minh trình duyệt/hiển thị (Root kiểm 18 ca GUI).

Ánh xạ ca GUI (phần quan sát được qua HTTP): C01 tài sản/trạng thái; C02 thiếu căn cứ + Nộp bị chặn trực tiếp; C03/C04 nguồn→trích→sửa có căn cứ→xác nhận
(KT/reviewer không xác nhận thay); C05 Track Changes; C06 PL; C07 BOQ phát hiện 999 không chặn; C08 tệp rỗng/media/đường dẫn; C09 Nộp + reviewer
đọc/tải; C10 đợt 2 phải có ngày/bộ tài liệu riêng; C11 revision cũ; C12 replay cùng khóa/đổi body; C13 ngoài phạm vi; C15 phiên chung CRM↔M4;
C16 thu hồi; C17 bytes tải về khớp nguồn.
"""

from __future__ import annotations

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
from urllib.parse import quote

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.kiem_chung import fixtures_m4 as F
from kho_tri_thuc.m4 import nguon_review as NR

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
A1, A2, B1 = "MO_PHONG_DU_AN_A1", "MO_PHONG_DU_AN_A2", "MO_PHONG_DU_AN_B1"
REVIEW, KT, XEM = "MO_PHONG_REVIEW_M4", "MO_PHONG_KT_M4", "MO_PHONG_XEM_M4"
DOCX, XLSX, PDF = F.MEDIA_DOCX, F.MEDIA_XLSX, "application/pdf"
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


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test HTTP M4-01C không chạy (NOT_RUN, không tính đạt)")
class M4CongHttp(unittest.TestCase):
    """Các ca chạy theo thứ tự tên h01…h12 trên MỘT DB/một máy chủ; trạng thái qua cls.s."""

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.k2 import crm_demo, m4_demo
        cls.db = "kho_test_m4c_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)
        cls.version = pg.migrate(cls.admin)
        crm_demo.khoi_tao(cls.admin)
        cls.seed = m4_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_m4c_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE IN ROLE app_web")
        app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        cls.env = patch.dict(os.environ, {LocalApp.CRM_ENV: app_dsn, LocalApp.CRM_ENV_ADMIN: cls.dsn, LocalApp.CRM_ENV_DB_KIEM_THU: "1"})
        cls.env.start()
        tam = Path(tempfile.mkdtemp(prefix="ktt_m4c_http_"))  # giữ lại
        (tam / "cau_hinh_fixture.toml").write_text(CAU_HINH_FIXTURE, encoding="utf-8")
        cls.app = LocalApp(tam / "cau_hinh_fixture.toml", tam / "web")
        cls.server = LocalServer(cls.app, 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.run_id = uuid.uuid4().hex[:8]  # không đặt tên `run` (che unittest.TestCase.run)
        cls.s = {}

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)
        cls.env.stop()
        cls.admin.close()  # giữ DB/role/thư mục làm bằng chứng

    # ------------------------------------------------------------------ helpers
    def goi(self, path, body=None, cookie=None, token=True, raw=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=180)
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
        out, ct, ck, cd = r.read(), r.getheader("Content-Type") or "", r.getheader("Set-Cookie"), r.getheader("Content-Disposition")
        c.close()
        return r.status, (json.loads(out or b"{}") if ct.startswith("application/json") else out), ck, cd

    def phien(self, login):
        st, s, ck, _ = self.goi("/api/m4")
        self.assertEqual(st, 200, s)
        sid = ck.split(";", 1)[0].split("=", 1)[1]
        st, r, _, _ = self.goi("/api/m4/danh-tinh", {"dang_nhap": login}, sid)
        self.assertEqual((st, r), (200, {"dang_nhap": login}))
        return sid

    def ok(self, sid, path, body):
        st, r, _, _ = self.goi("/api/m4/" + path, body, sid)
        self.assertEqual(st, 200, (path, r))
        return r

    def loi(self, sid, path, body, status, ma):
        st, r, _, _ = self.goi("/api/m4/" + path, body, sid)
        self.assertEqual((st, r.get("error")), (status, ma), (path, r))

    def K(self, ten):
        return f"m4c-{self.run_id}-{ten}"

    def tep(self, sid, du_an, raw, ten, media, vai, khoa, expect=200):
        info = quote(json.dumps({"du_an_id": du_an, "vai_tro": vai, "ten": ten, "media_type": media, "khoa": self.K(khoa)}))
        st, r, _, _ = self.goi("/api/m4/tep", cookie=sid, raw=raw, headers={"X-M4-Info": info, "Content-Type": "application/octet-stream"})
        self.assertEqual(st, expect, r)
        return r

    def mau(self, sid, ma):
        st, raw, _, cd = self.goi("/api/m4/mau/" + ma, cookie=sid)
        self.assertEqual(st, 200, raw)
        self.assertIn(ma, cd or "")
        return raw

    def du_an(self, ma):
        return str(self.admin.execute("SELECT id FROM master.du_an WHERE ma_junsky = %s", (ma,)).fetchone()[0])

    def hd(self, sid, hd_id):
        st, r, _, _ = self.goi("/api/m4/hop-dong/" + hd_id, cookie=sid)
        self.assertEqual(st, 200, r)
        return r

    def dot(self, sid, dot_id):
        st, r, _, _ = self.goi("/api/m4/dot/" + dot_id, cookie=sid)
        self.assertEqual(st, 200, r)
        return r

    def can_nguon(self):
        if not _nguon_da_nap():
            self.skipTest("Lõi nguồn chưa nạp (Root chạy tools/nap_nguon_review_m4.py) — NOT_RUN")

    # ------------------------------------------------------------------ C01
    def test_h01_tai_san_va_trang_thai(self):
        self.assertEqual(self.seed["trang_thai"], "DU", self.seed)
        st, js, _, _ = self.goi("/m4.js", token=False)
        self.assertEqual(st, 200)
        self.assertIn(b"kttChung", js)
        st, css, _, _ = self.goi("/m4.css", token=False)
        self.assertEqual(st, 200)
        self.assertIn(b".m4", css)
        st, html, _, _ = self.goi("/", token=False)
        self.assertEqual(st, 200)
        self.assertIn(b'id="page-m4"', html)
        sid = self.phien(A1)
        st, s, _, _ = self.goi("/api/m4", cookie=sid)
        self.assertEqual(st, 200)
        self.assertTrue(s["cau_hinh"])
        self.assertEqual(s["nguoi"]["dang_nhap"], A1)
        self.assertTrue(s["ghi_nguon"]["san_sang"], s["ghi_nguon"])
        self.assertEqual({p["du_an_id"] for p in s["pham_vi"] if p["soan"]}, {self.du_an("DA_XD_A1")})
        self.assertEqual(len(s["danh_muc_ho_so"]), 28)
        st, r, _, _ = self.goi("/api/m4", token=False, cookie=sid)
        self.assertEqual((st, r.get("error")), (403, "SESSION_TOKEN"))
        self.s["sid_a1"] = sid

    # ------------------------------------------------------------------ tệp mẫu + C08
    def test_h02_tep_mau_va_tep_xau(self):
        sid = self.s["sid_a1"]
        st, ds, _, _ = self.goi("/api/m4/mau", cookie=sid)
        self.assertEqual(st, 200)
        self.assertIn("hop_dong.docx", {m["ma"] for m in ds["mau"]})
        self.assertEqual(self.mau(sid, "hop_dong.docx"), F.hop_dong_docx())
        st, r, _, _ = self.goi("/api/m4/mau/../../pyproject.toml", cookie=sid)
        self.assertIn(st, (400, 404))
        sid_kt = self.phien(KT)  # KE_TOAN chỉ XEM: không có quyền soạn → không lấy tệp mẫu
        st, r, _, _ = self.goi("/api/m4/mau", cookie=sid_kt)
        self.assertEqual((st, r.get("error")), (403, "M4_KHONG_CO_QUYEN_DU_AN"))
        st, r, _, _ = self.goi("/api/m4/mau/hop_dong.docx", cookie=None)
        self.assertNotEqual(st, 200)
        du_an = self.du_an("DA_XD_A1")
        self.assertEqual(self.tep(sid, du_an, b"", "rong.pdf", PDF, "HO_SO_DOT", "rong", 400)["error"], "M4_TEP_RONG")
        self.assertEqual(self.tep(sid, du_an, F.hop_dong_docx(), "hd.pdf", PDF, "HOP_DONG", "gia-media", 400)["error"], "M4_TEP_MEDIA_KHONG_KHOP")
        self.assertEqual(self.tep(sid, du_an, F.pdf_demo(), "../x.pdf", PDF, "HO_SO_DOT", "duong-dan", 400)["error"], "M4_TEN_TEP_SAI")
        info = quote(json.dumps({"du_an_id": du_an, "vai_tro": "HOP_DONG", "ten": "a.pdf", "media_type": PDF, "khoa": self.K("auth"), "sha256": "0" * 64}))
        st, r, _, _ = self.goi("/api/m4/tep", cookie=sid, raw=F.pdf_demo(), headers={"X-M4-Info": info})
        self.assertEqual((st, r.get("error")), (403, "M4_CLIENT_AUTHORITY"))

    # ------------------------------------------------------------------ C02 + C12 + C15 + C17
    def test_h03_hd_dot_thieu_replay_tai_ve(self):
        sid, du_an = self.s["sid_a1"], self.du_an("DA_XD_A1")
        than = {"du_an_id": du_an, "so_hop_dong": f"HDXD-C-{self.run_id}", "ten": "Cổng hồ sơ C", "khoa": self.K("hd")}
        r1 = self.ok(sid, "hop-dong/tao", than)
        r2 = self.ok(sid, "hop-dong/tao", than)  # C12: bấm lặp/timeout gửi lại đúng body + khóa
        self.assertEqual((r2["hop_dong_id"], r2["lap_lai"]), (r1["hop_dong_id"], True))
        self.loi(sid, "hop-dong/tao", {**than, "ten": "Khác"}, 409, "M4_IDEMPOTENCY_KHAC")
        self.loi(sid, "hop-dong/tao", {**than, "khoa": self.K("hd-2")}, 409, "M4_HOP_DONG_DA_CO")  # không tạo master song song
        hd = r1["hop_dong_id"]
        raw = self.mau(sid, "hop_dong.docx")
        t = self.tep(sid, du_an, raw, "hop_dong.docx", DOCX, "HOP_DONG", "tep-hd")
        st, b, _, cd = self.goi("/api/m4/tep/" + t["tep_id"], cookie=sid)  # C17: bytes tải về = bytes nguồn đã nhận
        self.assertEqual((st, b, len(b)), (200, raw, t["byte_length"]))
        self.assertIn("hop_dong.docx", cd)
        st, _, _, _ = self.goi("/api/m4/tep/" + t["tep_id"], cookie=sid, token=False)
        self.assertEqual(st, 403)
        d = self.ok(sid, "dot/tao", {"hop_dong_id": hd, "so_dot": 1, "ngay_nghiem_thu": None, "khoa": self.K("dot1")})
        ct = self.dot(sid, d["dot_id"])
        ma = {x["ma"] for x in ct["thieu"]}
        self.assertTrue({"HD_CHUA_CO_TEP", "PL_CHUA_KHAI", "BOQ_CHUA_NHAP", "DOT_CHUA_NGAY"} <= ma, ma)
        self.assertFalse(ct["du_can_cu"])
        self.loi(sid, "dot/nop", {"dot_id": d["dot_id"], "revision_ho_so": ct["dot"]["revision_ho_so"], "revision_dot": ct["dot"]["revision"],
                                  "khoa": self.K("nop-thieu")}, 409, "M4_CHUA_DU_CAN_CU")
        st, crm, _, _ = self.goi("/api/crm", cookie=sid)  # C15: một phiên cookie chung — CRM thấy đúng vai vừa đổi ở M4
        self.assertEqual(st, 200)
        self.assertEqual(crm.get("nguoi", {}).get("dang_nhap"), A1, crm)
        self.s.update(hd=hd, tep_hd=t["tep_id"], dot1=d["dot_id"])

    # ------------------------------------------------------------------ C13
    def test_h04_ngoai_pham_vi(self):
        sid_b = self.phien(B1)
        for path in (f"/api/m4/hop-dong/{self.s['hd']}", f"/api/m4/tep/{self.s['tep_hd']}", f"/api/m4/dot/{self.s['dot1']}", f"/api/m4/hop-dong/{uuid.uuid4()}"):
            st, r, _, _ = self.goi(path, cookie=sid_b)
            self.assertEqual(st, 404, (path, r))
            self.assertNotIn(b"HDXD-C-", json.dumps(r, ensure_ascii=False).encode("utf-8"))
        st, s, _, _ = self.goi("/api/m4", cookie=sid_b)
        self.assertNotIn(self.s["hd"], {h["id"] for h in s["hop_dong"]})
        # lệnh ghi trên HĐ ngoài phạm vi: CSDL chặn ở quyền soạn hiện hành (403), không đổi gì
        self.loi(sid_b, "phu-luc/khai", {"hop_dong_id": self.s["hd"], "revision": 1, "khai": "KHONG_CO", "khoa": self.K("b1-khai")}, 403, "M4_KHONG_CO_QUYEN_DU_AN")

    # ------------------------------------------------------------------ C05 Track Changes qua đường sửa tham số (không cần lõi nguồn)
    def test_h05_track_changes(self):
        sid, du_an = self.s["sid_a1"], self.du_an("DA_XD_A1")
        hd = self.ok(sid, "hop-dong/tao", {"du_an_id": du_an, "so_hop_dong": f"HDXD-TC-{self.run_id}", "ten": "Track Changes", "khoa": self.K("hd-tc")})["hop_dong_id"]
        raw = self.mau(sid, "hop_dong_con_sua_doi.docx")
        t = self.tep(sid, du_an, raw, "hop_dong_con_sua_doi.docx", DOCX, "HOP_DONG", "tep-tc")
        self.ok(sid, "hop-dong/gan-tep", {"hop_dong_id": hd, "revision": 1, "tep_id": t["tep_id"], "khoa": self.K("gan-tc")})
        self.loi(sid, "tham-so/sua", {"hop_dong_id": hd, "revision": 2, "ma": "TT-32", "trang_thai_tham_so": "CO_GIA_TRI", "gia_tri": "12 tháng",
                                      "trich_dan": "Thời hạn bảo hành là 12 tháng", "khoa": self.K("sua-tc")}, 409, "M4_DOCX_CON_SUA_DOI")
        self.assertEqual(self.hd(sid, hd)["ho_so"]["revision"], 2)
        st, b, _, _ = self.goi("/api/m4/tep/" + t["tep_id"], cookie=sid)
        self.assertEqual(b, raw)  # nguồn giữ nguyên
        if _nguon_da_nap():
            r = self.ok(sid, "hop-dong/trich", {"hop_dong_id": hd, "revision": 2, "khoa": self.K("trich-tc")})
            self.assertEqual(r["trang_thai"], "KHONG_HO_TRO", r)  # entrypoint thứ hai: không đánh dấu đã trích

    # ------------------------------------------------------------------ C03/C04/C06/C07/C09/C10/C11 (cần lõi nguồn)
    def test_h06_luong_day_du_den_nop_va_reviewer(self):
        self.can_nguon()
        from tests.test_m4_01b_pg import PHIEU_THAM_SO, VANG  # oracle thủ công từ DOCX nguồn + danh mục (không lấy từ parser)
        sid, du_an, hd = self.s["sid_a1"], self.du_an("DA_XD_A1"), self.s["hd"]
        rev = lambda: self.hd(sid, hd)["ho_so"]["revision"]  # noqa: E731
        self.ok(sid, "hop-dong/gan-tep", {"hop_dong_id": hd, "revision": rev(), "tep_id": self.s["tep_hd"], "khoa": self.K("gan")})
        tr = self.ok(sid, "hop-dong/trich", {"hop_dong_id": hd, "revision": rev(), "khoa": self.K("trich")})
        self.assertEqual((tr["trang_thai"], tr["che_do"]), ("XONG", "QUY_TAC_KHONG_AI"), tr)
        ct = self.hd(sid, hd)
        self.assertEqual([t["ma"] for t in ct["tham_so"]][:9], [f"TC-0{i}" for i in range(1, 10)])
        self.assertEqual(len(ct["tham_so"]), 37)
        r_cu = ct["ho_so"]["revision"]
        self.loi(sid, "tham-so/sua", {"hop_dong_id": hd, "revision": r_cu, "ma": "TT-32", "trang_thai_tham_so": "CO_GIA_TRI", "gia_tri": "18 tháng",
                                      "trich_dan": "Thời hạn bảo hành là 18 tháng", "khoa": self.K("sua-gia")}, 400, "M4_TRICH_DAN_KHONG_KHOP")
        for ma, (tt, gt, dv, dk, td) in PHIEU_THAM_SO.items():
            r = self.ok(sid, "tham-so/sua", {"hop_dong_id": hd, "revision": rev(), "ma": ma, "trang_thai_tham_so": tt, "gia_tri": gt, "don_vi": dv,
                                             "dieu_khoan": dk, "trich_dan": td, "ly_do": None if tt == "CO_GIA_TRI" else "HĐ Điều 3.1 ghi: Tạm ứng: Không áp dụng",
                                             "khoa": self.K("sua-" + ma)})
            self.assertTrue(str(r["kiem_tra"]).startswith("OK"), (ma, r))
        for ma in VANG:
            self.ok(sid, "tham-so/sua", {"hop_dong_id": hd, "revision": rev(), "ma": ma, "trang_thai_tham_so": "KHONG_QUY_DINH",
                                         "ly_do": "HĐ DEMO không có điều khoản này", "khoa": self.K("sua-" + ma)})
        self.loi(sid, "phu-luc/khai", {"hop_dong_id": hd, "revision": r_cu, "khai": "KHONG_CO", "khoa": self.K("khai-cu")}, 409, "M4_REVISION_CU")  # C11
        for login in (KT, REVIEW):  # C04: KT/reviewer không xác nhận thay phòng dự án
            s2 = self.phien(login)
            st, r, _, _ = self.goi("/api/m4/tham-so/xac-nhan", {"hop_dong_id": hd, "revision": rev(), "khoa": self.K("xn-" + login)}, s2)
            self.assertIn((st, r.get("error")), ((403, "M4_KHONG_CO_QUYEN_DU_AN"), (404, "M4_KHONG_THAY_HOP_DONG")), (login, r))
        # mỗi phien() là một cookie/phiên riêng — phiên A1 ban đầu vẫn là A1
        xn =self.ok(sid, "tham-so/xac-nhan", {"hop_dong_id": hd, "revision": rev(), "ly_do": "Phòng dự án đã soát", "khoa": self.K("xn")})
        self.assertTrue(self.hd(sid, hd)["xac_nhan"]["con_hieu_luc"])
        # C06: khai có-chưa-đủ → thêm PL dự thảo có tệp → hủy (giữ lịch sử) → khai không có
        self.ok(sid, "phu-luc/khai", {"hop_dong_id": hd, "revision": rev(), "khai": "CO_CHUA_DU", "khoa": self.K("khai1")})
        tpl = self.tep(sid, du_an, self.mau(sid, "phu_luc_01.pdf"), "phu_luc_01.pdf", PDF, "PHU_LUC", "tep-pl")
        pl = self.ok(sid, "phu-luc/them", {"hop_dong_id": hd, "revision": rev(), "so_pl": "PL-01", "ngay_ky": "2026-02-01", "ngay_hieu_luc": "2026-02-01",
                                           "trang_thai_phu_luc": "DU_THAO", "doi_boq": False, "noi_dung": "Dự thảo", "tep_id": tpl["tep_id"], "khoa": self.K("pl")})
        self.ok(sid, "phu-luc/huy", {"phu_luc_id": pl["phu_luc_id"], "revision": rev(), "ly_do": "Không ký", "khoa": self.K("huy")})
        self.ok(sid, "phu-luc/khai", {"hop_dong_id": hd, "revision": rev(), "khai": "KHONG_CO", "khoa": self.K("khai2")})
        self.assertEqual([p["trang_thai"] for p in self.hd(sid, hd)["phu_luc"]], ["DA_HUY"])
        # C07: BOQ thật — xem sheet → nhập; thành tiền 999 lệch là phát hiện, giữ nguyên, không chặn
        tb = self.tep(sid, du_an, self.mau(sid, "boq_lech_so_hoc.xlsx"), "boq_lech_so_hoc.xlsx", XLSX, "BOQ", "tep-boq")
        xem = self.ok(sid, "boq/xem", {"tep_id": tb["tep_id"]})
        self.assertEqual([s["ten"] for s in xem["sheets"]], ["BOQ"])
        xs = self.ok(sid, "boq/xem", {"tep_id": tb["tep_id"], "sheet": "BOQ"})
        self.assertEqual(xs["sheet"], "BOQ")
        boq = self.ok(sid, "boq/nhap", {"hop_dong_id": hd, "revision": rev(), "tep_id": tb["tep_id"], "phu_luc_id": None, "sheet": "BOQ", "hang_tieu_de": 1,
                                        "cot": dict(F.BOQ_COT), "khoa": self.K("boq")})
        self.assertEqual((boq["trang_thai"], boq["loi_chan"], [p["dong"] for p in boq["phat_hien"]]), ("DA_MAP", [], [4]), boq)
        dong = {r["ma_rieng"]: r for r in self.hd(sid, hd)["boq_goc_dong"]}
        self.assertEqual(dong["HM-03"]["o_goc"]["thanh_tien"], {"tho": "999", "kieu": "SO", "o": "G4"})
        # đợt 1: ngày + bộ tài liệu bắt buộc → đủ căn cứ → Nộp thật (C09)
        d1 = self.s["dot1"]
        ct = self.dot(sid, d1)
        r = self.ok(sid, "dot/sua", {"dot_id": d1, "revision": ct["dot"]["revision"], "ngay_nghiem_thu": "2026-03-01", "khoa": self.K("ngay1")})
        rv = r["revision"]
        ths = self.tep(sid, du_an, self.mau(sid, "ho_so_dot_ky1.pdf"), "ho_so_dot_ky1.pdf", PDF, "HO_SO_DOT", "hs1")
        for c in self.dot(sid, d1)["checklist"]:
            if c["bat_buoc"]:
                rv = self.ok(sid, "dot/gan-tep", {"dot_id": d1, "revision": rv, "tep_id": ths["tep_id"], "muc": c["ma"], "khoa": self.K("gan1-" + c["ma"])})["revision"]
        ct = self.dot(sid, d1)
        self.assertEqual(ct["thieu"], [])
        self.assertTrue(ct["du_can_cu"])
        nop = self.ok(sid, "dot/nop", {"dot_id": d1, "revision_ho_so": ct["dot"]["revision_ho_so"], "revision_dot": ct["dot"]["revision"], "khoa": self.K("nop1")})
        sau = self.dot(sid, d1)
        self.assertEqual((sau["nop"]["id"], sau["nop"]["digest"]), (nop["nop_id"], nop["digest"]))
        self.assertEqual(sau["nop"]["snapshot"]["xac_nhan_id"], xn["xac_nhan_id"])
        self.assertEqual([b["so_phat_hien"] for b in sau["nop"]["snapshot"]["boq"]], [1])
        self.assertTrue(all(x["trang_thai"] == "CHUA_NOI" for x in sau["nhanh_sau"]))
        # reviewer đọc đợt đã nộp và tải đúng tệp nguồn; không có hành động soạn/duyệt
        sr = self.phien(REVIEW)
        st, s, _, _ = self.goi("/api/m4", cookie=sr)
        self.assertIn(d1, {d["id"] for d in s["dot"]})
        cr = self.dot(sr, d1)
        self.assertFalse(cr["dot"]["soan"])
        st, b, _, _ = self.goi("/api/m4/tep/" + ths["tep_id"], cookie=sr)
        self.assertEqual((st, b), (200, F.pdf_demo("HO_SO_KY1")))
        self.loi(sr, "dot/sua", {"dot_id": d1, "revision": sau["dot"]["revision"], "ngay_nghiem_thu": "2026-03-05", "khoa": self.K("rv-sua")}, 403, "M4_KHONG_CO_QUYEN_DU_AN")
        # C10: đợt 2 dùng lại HĐ/PL/BOQ nhưng phải có ngày + tài liệu kỳ 2 riêng
        d2 = self.ok(sid, "dot/tao", {"hop_dong_id": hd, "so_dot": 2, "ngay_nghiem_thu": None, "khoa": self.K("dot2")})["dot_id"]
        th2 = {x["ma"] for x in self.dot(sid, d2)["thieu"]}
        self.assertIn("DOT_CHUA_NGAY", th2)
        self.assertFalse({m for m in th2 if m.startswith(("HD_", "PL_", "BOQ_"))}, th2)
        self.s.update(tep_hs1=ths["tep_id"], dot2=d2)

    # ------------------------------------------------------------------ C16
    def test_h07_thu_hoi_du_an(self):
        sid = self.phien(A2)
        du_an = self.du_an("DA_XD_A2")
        than = {"du_an_id": du_an, "so_hop_dong": f"HDXD-A2C-{self.run_id}", "ten": "A2", "khoa": self.K("hd-a2")}
        hd = self.ok(sid, "hop-dong/tao", than)["hop_dong_id"]
        t = self.tep(sid, du_an, F.pdf_demo("A2C"), "a2.pdf", PDF, "HOP_DONG", "tep-a2")
        q = self.admin.execute("""SELECT q.id FROM m4.quyen_du_an q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                                  WHERE n.dang_nhap = %s AND q.du_an_id = %s AND q.vai = 'PHU_TRACH' AND q.thu_hoi_luc IS NULL""", (A2, du_an)).fetchone()[0]
        self.admin.execute("SELECT m4.thu_hoi_quyen_du_an(%s, 'MO_PHONG_QUAN_TRI_TEST', 'Kiểm thu hồi M4-01C')", (q,))
        self.loi(sid, "hop-dong/tao", than, 403, "M4_KHONG_CO_QUYEN_DU_AN")  # replay đúng body bị chặn theo quyền hiện hành
        for path in (f"/api/m4/hop-dong/{hd}", f"/api/m4/tep/{t['tep_id']}"):
            st, r, _, _ = self.goi(path, cookie=sid)
            self.assertEqual(st, 404, (path, r))
        st, s, _, _ = self.goi("/api/m4", cookie=sid)
        self.assertEqual((st, s["pham_vi"], s["hop_dong"]), (200, [], []))
        self.assertEqual(self.admin.execute("SELECT trang_thai FROM master.nguoi_dung WHERE dang_nhap = %s", (A2,)).fetchone()[0], "HOAT_DONG")

    def test_h08_role_khong_thuoc_m4_bi_tu_choi(self):
        st, s, ck, _ = self.goi("/api/m4")
        sid = ck.split(";", 1)[0].split("=", 1)[1]
        st, r, _, _ = self.goi("/api/m4/danh-tinh", {"dang_nhap": "MO_PHONG_KT_A"}, sid)  # actor CRM, không thuộc danh sách M4
        self.assertEqual((st, r.get("error")), (403, "DANH_TINH_M4"))
        st, r, _, _ = self.goi("/api/m4/danh-tinh", {"dang_nhap": A1, "actor": "x"}, sid)
        self.assertEqual((st, r.get("error")), (403, "M4_CLIENT_AUTHORITY"))


if __name__ == "__main__":
    unittest.main()
