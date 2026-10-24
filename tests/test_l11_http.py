"""L11 QUANTITY R16 — HTTP trong cùng shell (token, cookie HttpOnly, bộ chọn 2 vai L11) trên PostgreSQL thật — coder viết, CHƯA CHẠY (CODE_ONLY/UNRUN).

Repair02 (UNRUN): khóa duyệt theo toàn tham chiếu (frozen01 `ref[-8:]` trùng khóa GOODS/CAI → nghi là nguyên nhân KeyError `trang_thai`, cần đối chứng
độc lập), đối chứng trùng khóa cố ý → 409; GET /api/m5/l11/proof thật (CFO thấy H/độ dài/facts trước duyệt, LINK không thấy raw); mã lỗi chính xác.

Chỉ chạy khi root cấp KHO_PG_DSN_TEST (DB DEMO mới kho_test_*): app_web login cho route đọc + kết nối chủ bảng cho intake/FILE; server 127.0.0.1
cổng ngẫu nhiên. Nguồn M2 G01 / M5 K01 được dựng bằng service K2 thật (đường đã có test riêng); phần HTTP kiểm: 403 thiếu token, selector L11
đúng 2 login, client authority 403, nhận bằng chứng qua mẫu whitelisted, CFO xác nhận + 409 token cũ, mã hóa, preview 0 ghi / xác nhận / replay /
409 khác body / undo, FILE L11_QUANTITY + tải lại theo quyền BOTH READ + FILE (M5-only bị 403), tài nguyên trang. Không chạy JS/browser.
Không DROP/DELETE/cleanup: DB/role/thư mục giữ làm bằng chứng.
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

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang.primitives import sha256
from kho_tri_thuc.k2 import l11_demo, m5_demo

ROOT = Path(__file__).resolve().parents[1]
ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
LINK, PCFO, M5_KT, M5_INTAKE, M5_CFO = ("MO_PHONG_L11_LINK_A", "MO_PHONG_L11_PROOF_CFO_A", "MO_PHONG_KT_KHO_A", "MO_PHONG_M0_KHO_A",
                                         "MO_PHONG_CFO_KHO_A")
M2_INTAKE, M2_CFO = "MO_PHONG_M0_HD_INTAKE", "MO_PHONG_CFO_MUA_A"


def g01_va_fact01() -> tuple[bytes, dict]:
    """G01 + ứng viên literal 01 R15 theo đúng pin của tests/test_m2_k2.py (manifest XML + line-facts); không đọc expected."""
    def pin(path: Path, sha: str) -> bytes:
        raw = path.read_bytes()
        assert sha256(raw) == sha, f"{path.name} khác pin"
        return raw
    xmlfix, bridge = ROOT / "tests" / "fixtures" / "m2_invoice_xml", ROOT / "tests" / "fixtures" / "m2_bridge"
    man = {f["path"]: f for f in json.loads(pin(xmlfix / "manifest.json", "43ad28257ca646b9d43f45ed34a8c441131328cca1b576cf247b378224e2b177")
                                             .decode("utf-8"))["files"]}
    rel = "inputs/G01-wrapped-positive.xml"
    facts = json.loads(pin(bridge / "line-facts.json", "2195792bef97a1c94773f7fbe3391192e0ed24e872dfd904ac90ed54ba3b41fd").decode("utf-8"))["rows"]
    return pin(xmlfix / rel, man[rel]["sha256"]), facts[0]


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test HTTP L11 không chạy (không tính đạt)")
class L11Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        from kho_tri_thuc.k2 import crm_demo, m2_demo
        cls.db = "kho_test_l11http_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)
        crm_demo.khoi_tao(cls.admin)
        m5_demo.khoi_tao(cls.admin)
        m2_demo.khoi_tao(cls.admin)
        l11_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_l11h_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOCREATEDB NOCREATEROLE IN ROLE app_web")
        cls.app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        cls.env = patch.dict(os.environ, {LocalApp.CRM_ENV: cls.app_dsn, LocalApp.CRM_ENV_ADMIN: cls.dsn, LocalApp.CRM_ENV_DB_KIEM_THU: "1"})
        cls.env.start()
        cls.web = Path(tempfile.mkdtemp(prefix="ktt_l11_http_")) / "web"
        cls.app = LocalApp(ROOT / "cau_hinh.toml", cls.web)
        cls.server = LocalServer(cls.app, 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.cookie_name = LocalApp.CRM_COOKIE
        cls.dung_nguon()

    @classmethod
    def dung_nguon(cls):
        """G01 (M2: nhận → CFO map → tuyến KHO) + K01 (M5: nhận → CFO chấp nhận) bằng service K2 thật trên kết nối riêng (không seed approval)."""
        from kho_tri_thuc.k2.hoa_don import HoaDonK2
        from kho_tri_thuc.k2.kho_so_luong import KhoSoLuongK2
        opts = "-c lock_timeout=20000 -c statement_timeout=60000"
        cls.k_app = psycopg.connect(cls.app_dsn, autocommit=True, row_factory=dict_row, options=opts)
        cls.k_chu = psycopg.connect(cls.dsn, autocommit=True, row_factory=dict_row, options=opts)
        root = Path(tempfile.mkdtemp(prefix="ktt_l11_http_k2_"))
        m2, m5 = HoaDonK2(cls.k_app, root, conn_chu=cls.k_chu), KhoSoLuongK2(cls.k_app, root, conn_chu=cls.k_chu)
        g01, f01 = g01_va_fact01()
        m2.nhan(M2_INTAKE, source_instance="DEMO_M2_XML_INSTANCE_A", scope_ref="DEMO_M2_SCOPE_BOTH_COMPANIES_V1", coverage="COMPLETE_INPUT",
                client_key="h-g01", native=g01)
        hd = cls.admin.execute("SELECT id::text FROM kho.hoa_don_danh_tinh WHERE ky_hieu = 'DEMO_SERIES_A' AND so_chuan = '1'").fetchone()[0]
        ct = m2.chi_tiet(M2_CFO, hd)
        m2.mapping_line(M2_CFO, client_key="h-ml", hoa_don_id=hd, expected_graph=ct["expected_graph"], source_row_id=ct["dong_nguon_hien_hanh"][0]["source_row_id"],
                        logical_line_key=f01["logical_line_key"], reason="DEMO", evidence_ref=f01["mapping_ref"], evidence_revision=f01["revision"])
        ct = m2.chi_tiet(M2_CFO, hd)
        m2.route(M2_CFO, {"hoa_don_id": hd, "cau_noi_id": ct["cau_noi"][0]["id"], "dich": "KHO", "expected_route_id": None,
                          "expected_graph": ct["expected_graph"], "ly_do": "DEMO", "khoa": "h-rt"})
        mm = m5_demo.mau("K01")
        scope = next(c for c in m5_demo.doc_registry()["configured_scopes"] if c["source_instance"] == mm["source_instance"])["scope_ref"]
        m5.nhan(M5_INTAKE, source_instance=mm["source_instance"], scope_ref=scope, coverage=mm["coverage"], reported_errors=mm["reported_errors"],
                client_key="h-k01", native=mm["native"], master=mm["master"])
        pid = cls.admin.execute("SELECT id::text FROM kho.phieu_kho_danh_tinh WHERE so_phieu_key = 'NK20260814001'").fetchone()[0]
        p = m5.chi_tiet(M5_CFO, pid)["con_tro"]
        m5.kiem_lai_nguon(M5_CFO, {"phieu_id": pid, "observation_id": p["latest_observation_id"], "quyet_dinh": "CHAP_NHAN_NGUON",
                                   "accepted_truoc": p["accepted_source_observation_id"], "eligible_truoc": p["eligible_content_id"],
                                   "latest_truoc": p["latest_observation_id"], "ly_do": "DEMO", "khoa": "h-rv"})
        cls.hd, cls.pid = hd, pid

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)
        cls.env.stop()
        for c in (cls.k_app, cls.k_chu, cls.admin):
            c.close()  # giữ DB/role/thư mục làm bằng chứng

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

    def phien_l11(self, login):
        status, _, ck = self.call("/api/m5/l11")
        self.assertEqual(status, 200)
        self.assertIn("HttpOnly", ck)
        sid = ck.split(";", 1)[0].split("=", 1)[1]
        self.assertEqual(self.call("/api/m5/l11/danh-tinh", {"dang_nhap": login}, sid)[0], 200)
        return sid

    def phien_m5(self, login):
        _, _, ck = self.call("/api/m5")
        sid = ck.split(";", 1)[0].split("=", 1)[1]
        self.assertEqual(self.call("/api/m5/danh-tinh", {"dang_nhap": login}, sid)[0], 200)
        return sid

    def dem(self):
        q = lambda s: self.admin.execute(s).fetchone()[0]  # noqa: E731
        return tuple(q(f"SELECT count(*) FROM {t}") for t in ("giao_tiep.stage_tin_cay", "kho.bang_chung_ung_vien", "kho.bang_chung_quy_doi_luong",
                                                              "kho.dich_so_luong", "kho.ma_hoa_luong_nguon", "kho.lien_ket_dong", "kho.lo_xuat",
                                                              "kho.bien_nhan_thao_tac", "kho.lien_ket_chung_tu"))

    def test_luong_http_l11(self):
        self.assertEqual(self.call("/api/m5/l11", token=False)[0], 403)
        cfo = self.phien_l11(PCFO)
        s = self.call("/api/m5/l11", cookie=cfo)[1]
        self.assertEqual(sorted(d["dang_nhap"] for d in s["danh_tinh_demo"]), sorted(l11_demo.dang_nhap_l11()))
        self.assertEqual(self.call("/api/m5/l11/danh-tinh", {"dang_nhap": M5_KT}, cfo)[1]["error"], "DANH_TINH_L11")
        self.assertEqual(sorted(s["mau_bang_chung"]), sorted(l11_demo.PROOF_FILES))
        pv = s["pham_vi_bang_chung"][0]
        than = {"source_instance": pv["source_instance_id"], "scope_ref": pv["scope_ref"], "coverage": "COMPLETE_INPUT"}
        truoc = self.dem()
        for key in ("PROVEN", "phap_nhan_id", "actor"):
            with self.subTest(key=key):
                status, err, _ = self.call("/api/m5/l11/proof/nhan", {**than, "fixture_ref": "GOODS_EQ_A", "khoa": "hp-x", key: "x"}, cfo)
                self.assertEqual((status, err["error"]), (403, "M5_CLIENT_AUTHORITY"))
        status, err, _ = self.call("/api/m5/l11/proof/nhan", {**than, "fixture_ref": "GOODS_EQ_A", "khoa": "hp-x", "duong_dan": "tests/x"}, cfo)
        self.assertEqual((status, err["error"]), (400, "L11_YEU_CAU_SAI"))  # trường đường dẫn ngoài whitelist body nhận bằng chứng
        self.assertEqual(self.dem(), truoc)
        for ma in ("GOODS_EQ_A", "CAI_EQ_A"):
            status, r, _ = self.call("/api/m5/l11/proof/nhan", {**than, "fixture_ref": ma, "khoa": f"hp-{ma.lower()}"}, cfo)
            self.assertEqual((status, r["promote"]["trang_thai_ung_vien"], r["lap_lai"]), (200, "UNG_VIEN", False))
        status, r, _ = self.call("/api/m5/l11/proof/nhan", {**than, "fixture_ref": "CAI_EQ_A", "khoa": "hp-goods_eq_a"}, cfo)
        self.assertEqual((status, r["error"]), (409, "CAPTURE_KHAC_NOI_DUNG"))
        # GET bằng chứng thật (R4): CFO có READ_SOURCE thấy ứng viên + H/độ dài/facts TRƯỚC khi duyệt; thiếu token → 403
        self.assertEqual(self.call("/api/m5/l11/proof", cookie=cfo, token=False)[0], 403)
        status, pf, _ = self.call("/api/m5/l11/proof", cookie=cfo)
        self.assertEqual((status, sorted(pf)), (200, ["bang_chung", "pham_vi_nguon", "ung_vien"]))
        goods = next(x for x in pf["ung_vien"] if x["reference_id"] == "DEMO_M2_M5_GOODS_EQ_A_V1")
        self.assertEqual((goods["raw_sha256"], goods["byte_length"], goods["coverage"], goods["reported_errors"]),
                         ("aef5de224e04fd64ef67a272689f72a041097ae93c5160393ef2297640d2bb4f", 3927, "COMPLETE_INPUT", []))
        self.assertEqual((goods["facts"]["domain"]["invoice"]["item_code"], goods["facts"]["domain"]["warehouse"]["MaKho"]), ("DEMO_ITEM_A", "KHO_DEMO"))
        cai = next(x for x in pf["ung_vien"] if x["reference_id"] == "DEMO_M2_M5_CAI_EQ_A_V1")
        self.assertEqual((cai["facts"]["from_definition_ref"], cai["facts"]["to_definition_ref"], cai["facts"]["numerator_text"], cai["facts"]["denominator_text"]),
                         ("DEMO_M2_UNIT_CAI_V1", "DEMO_UNIT_CAI_A", "1", "1"))
        ids = {}
        for ref in ("DEMO_M2_M5_GOODS_EQ_A_V1", "DEMO_M2_M5_CAI_EQ_A_V1"):
            u = next(x for x in self.call("/api/m5/l11", cookie=cfo)[1]["ung_vien"] if x["reference_id"] == ref and x["trang_thai"] == "UNG_VIEN")
            # repair02 (root-cause test setup): khóa duyệt theo TOÀN BỘ tham chiếu + thao tác — frozen01 dùng ref[-8:] nên GOODS/CAI trùng khóa
            body = {"candidate_id": u["id"], "expected_graph": u["expected_graph"], "khoa": f"hc-approve-{ref}", "ly_do": "DEMO HTTP"}
            status, err, _ = self.call("/api/m5/l11/proof/xac-nhan", {**body, "expected_graph": "0" * 64, "khoa": f"hc-cu-{ref}"}, cfo)
            self.assertEqual((status, err["error"]), (409, "L11_VERSION_CHANGED"))
            status, err, _ = self.call("/api/m5/l11/proof/xac-nhan", {**body, "tu_so": "1"}, cfo)
            self.assertEqual((status, err["error"]), (403, "L11_CLIENT_AUTHORITY"))
            status, r, _ = self.call("/api/m5/l11/proof/xac-nhan", body, cfo)
            self.assertEqual((status, r.get("error"), r.get("trang_thai")), (200, None, "DA_XAC_NHAN"))
            ids[ref] = r["bang_chung_id"]
            status, lai, _ = self.call("/api/m5/l11/proof/xac-nhan", body, cfo)  # cùng khóa + cùng body → replay, cùng bằng chứng
            self.assertEqual((status, lai["bang_chung_id"], lai["lap_lai"]), (200, r["bang_chung_id"], True))
        # cố ý dùng LẠI khóa của GOODS cho body khác (CAI) → 409 đúng mã, 0 delta (đối chứng riêng cho giả thuyết trùng khóa)
        u_cai = next(x for x in self.call("/api/m5/l11", cookie=cfo)[1]["ung_vien"] if x["reference_id"] == "DEMO_M2_M5_CAI_EQ_A_V1")
        truoc = self.dem()
        status, err, _ = self.call("/api/m5/l11/proof/xac-nhan", {"candidate_id": u_cai["id"], "expected_graph": u_cai["expected_graph"],
                                                                   "khoa": "hc-approve-DEMO_M2_M5_GOODS_EQ_A_V1", "ly_do": "DEMO HTTP"}, cfo)
        self.assertEqual((status, err["error"]), (409, "IDEMPOTENCY_KHAC"))
        self.assertEqual(self.dem(), truoc)
        # mã hóa hai phía bằng token đồ thị do máy chủ trả
        s = self.call("/api/m5/l11", cookie=cfo)[1]
        dh = next(d for d in s["dong_hoa_don"] if d["hoa_don_id"] == self.hd)
        dp = next(d for d in s["dong_phieu"] if d["phieu_id"] == self.pid and d["stt"] == 1)
        enc = {}
        for side, line, mh in (("M2", dh["cau_noi_id"], dh["ma_hoa"]), ("M5", dp["dong_phien_ban_id"], dp["ma_hoa"])):
            status, r, _ = self.call("/api/m5/l11/ma-hoa", {"side": side, "line_id": line, "expected_graph": mh["expected_graph"], "khoa": f"he-{side}",
                                                            "ly_do": "DEMO"}, cfo)
            self.assertEqual(status, 200, r)
            enc[side] = r["ma_hoa_id"]
        link = self.phien_l11(LINK)
        status, pl, _ = self.call("/api/m5/l11/proof", cookie=link)  # LINK: BOTH READ thấy bằng chứng đã duyệt, KHÔNG thấy raw candidate
        self.assertEqual((status, pl["ung_vien"], pl["pham_vi_nguon"]), (200, [], []))
        self.assertEqual(sorted(b["reference_id"] for b in pl["bang_chung"]), ["DEMO_M2_M5_CAI_EQ_A_V1", "DEMO_M2_M5_GOODS_EQ_A_V1"])
        status, err, _ = self.call("/api/m5/l11/ma-hoa", {"side": "M2", "line_id": dh["cau_noi_id"], "expected_graph": "0" * 64, "khoa": "he-l", "ly_do": "x"},
                                   link)
        self.assertEqual((status, err["error"]), (403, "KHONG_CO_QUYEN_L11_MA_HOA"))
        cap = {"cau_noi_id": dh["cau_noi_id"], "dong_phien_ban_id": dp["dong_phien_ban_id"], "ma_hoa_hoa_don_id": enc["M2"], "ma_hoa_phieu_id": enc["M5"],
               "bang_chung_hang_id": ids["DEMO_M2_M5_GOODS_EQ_A_V1"], "bang_chung_ty_le_id": ids["DEMO_M2_M5_CAI_EQ_A_V1"],
               "so_luong_hoa_don": "8", "so_luong_phieu": "8"}
        truoc = self.dem()
        status, xt, _ = self.call("/api/m5/lien-ket/preview", cap, link)
        self.assertEqual((status, xt["blockers"], xt["ghi"]), (200, [], 0))
        self.assertEqual(self.dem(), truoc)
        for sai, code in (({"so_luong_phieu": 8}, (400, "L11_SO_LUONG_SAI")), ({"so_luong_phieu": "8.5e0"}, (400, "L11_SO_LUONG_SAI")),
                          ({"tu_so": "1"}, (403, "L11_CLIENT_AUTHORITY")), ({"pool_id": str(uuid.uuid4())}, (403, "L11_CLIENT_AUTHORITY"))):
            with self.subTest(sai=sai):
                status, err, _ = self.call("/api/m5/lien-ket/preview", {**cap, **sai}, link)
                self.assertEqual((status, err["error"]), code)
        xn = {**cap, "expected_graph": xt["expected_graph"], "khoa": "hl-1", "ly_do": "DEMO HTTP 8/8"}
        status, r, _ = self.call("/api/m5/lien-ket/xac-nhan", xn, link)
        self.assertEqual((status, r["trang_thai"], r["so_luong"]["pool_phieu"]), (200, "DA_KHOP", "8"))
        status, lai, _ = self.call("/api/m5/lien-ket/xac-nhan", xn, link)
        self.assertEqual((status, lai["child_id"], lai["lap_lai"]), (200, r["child_id"], True))
        status, err, _ = self.call("/api/m5/lien-ket/xac-nhan", {**xn, "ly_do": "khác"}, link)
        self.assertEqual((status, err["error"]), (409, "IDEMPOTENCY_KHAC"))
        status, err, _ = self.call("/api/m5/lien-ket/xac-nhan", {**xn, "khoa": "hl-cu"}, link)
        self.assertEqual((status, err["error"]), (409, "L11_VERSION_CHANGED"))
        # quyền: M5-only (selector M5) không xem/xác nhận/tải file chéo
        kt = self.phien_m5(M5_KT)
        status, err, _ = self.call("/api/m5/lien-ket/preview", cap, kt)
        self.assertEqual((status, err["error"]), (403, "KHONG_CO_QUYEN_L11_XEM"))
        # FILE L11_QUANTITY: token đồ thị từ trang, tải lại theo quyền hiện hành
        s = self.call("/api/m5/l11", cookie=link)[1]
        lk = next(x for x in s["lien_ket"] if x["id"] == r["lien_ket_id"])
        fb = {"lien_ket_id": lk["id"], "co_so_truoc": lk["co_so"]["co_so_sha256"], "khoa": "hf-1", "ly_do": "DEMO file"}
        status, lo, _ = self.call("/api/m5/l11/file-soat", fb, link)
        self.assertEqual((status, lo["che_do"], lo["lap_lai"]), (200, "L11_QUANTITY", False))
        self.assertTrue(self.call("/api/m5/l11/file-soat", fb, link)[1]["lap_lai"])
        status, raw, _ = self.call(f"/api/m5/file-soat/{lo['id']}", cookie=link)
        self.assertEqual((status, raw[:2], sha256(raw)), (200, b"PK", lo["sha256"]))
        status, err, _ = self.call(f"/api/m5/file-soat/{lo['id']}", cookie=kt)  # M5 FILE không M2_READ: RLS lô chéo ẩn → cùng từ chối ngoài quyền
        self.assertEqual((status, err["error"]), (400, "FILE_SOAT"))
        # undo bằng token trạng thái child do máy chủ trả
        tok = lk["co_so"]["token_dong"][r["child_id"]]
        status, err, _ = self.call("/api/m5/lien-ket/huy", {"child_id": r["child_id"], "expected_graph": tok, "khoa": "hu-1", "ly_do": "x"}, cfo)
        self.assertEqual((status, err["error"]), (403, "KHONG_CO_QUYEN_L11_LIEN_KET"))
        status, h, _ = self.call("/api/m5/lien-ket/huy", {"child_id": r["child_id"], "expected_graph": tok, "khoa": "hu-1", "ly_do": "DEMO undo"}, link)
        self.assertEqual((status, h["trang_thai"]), (200, "HUY"))
        status, lai, _ = self.call("/api/m5/lien-ket/xac-nhan", xn, link)
        self.assertEqual((status, lai["trang_thai"], lai["lap_lai"]), (200, "HUY", True))

    def test_tai_nguyen_trang(self):
        """Chỉ kiểm tài nguyên được phục vụ — không thay kiểm tương tác trình duyệt (epoch/picker/fence cần root chạy GUI)."""
        _, html, _ = self.call("/")
        for chuoi in (b"page-lienketsoluong", b"l11-tl-gui", b"l11-xem-truoc", b"l11-lien-ket", b"l11-dong-hoa-don", b"l11-dong-phieu"):
            self.assertIn(chuoi, html)
        _, js, _ = self.call("/app.js")
        for chuoi in (b"l11Epoch", b"l11Gen", b"l11Tai", b"l11FormEpoch", b'"lien-ket/preview"', b'"lien-ket/xac-nhan"', b'"lien-ket/huy"',
                      b'"l11/proof/nhan"', b"expected_graph", b"l11Facts", b"kq.fence()", b"gen !== l11Gen", b"ve === l11Gen", b"fe === l11FormEpoch && (l11 && l11.lien_ket",
                      b"native_byte_length"):
            self.assertIn(chuoi, js)
        self.assertNotIn(b"parseFloat", js)  # lượng giữ dạng chuỗi exact


if __name__ == "__main__":
    unittest.main()
