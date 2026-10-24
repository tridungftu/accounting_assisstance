"""M2 bridge R15 — HTTP trong cùng shell (token, cookie phiên HttpOnly, khóa thao tác) trên PostgreSQL thật — coder viết, CHƯA CHẠY (CODE_ONLY).

Chỉ chạy khi root cấp KHO_PG_DSN_TEST (DB fixture kho_test_*): login ứng dụng thường (app_web) cho route đọc/thao tác CFO + kết nối chủ bảng (admin
DSN cục bộ, cùng validator loopback/endpoint) cho capture; server 127.0.0.1 cổng ngẫu nhiên, không mạng ngoài. Kiểm: 403 thiếu token; bộ chọn vai
M2 đúng 8 login declarations; trình duyệt không gửi actor/PN/identity/proof/line facts; nhận mẫu + bytes thật (base64); cùng khóa khác nội dung → 409
0 delta; raw chỉ READ_SOURCE; CFO map dòng + tuyến qua HTTP với token đồ thị (cũ → 409); viewer/M1-only; L11 501. Không chạy JS/browser.
Không DROP DB/role, không xóa thư mục: giữ làm bằng chứng.
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
from kho_tri_thuc.k2 import m2_demo

ROOT = Path(__file__).resolve().parents[1]
ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
INST, SCOPE, G01, G03 = "DEMO_M2_XML_INSTANCE_A", "DEMO_M2_SCOPE_BOTH_COMPANIES_V1", "inputs/G01-wrapped-positive.xml", "inputs/G03-identical-members.zip"
INTAKE, KTA, KTB, CFOA, VIEWA, M1A = ("MO_PHONG_M0_HD_INTAKE", "MO_PHONG_KT_MUA_A", "MO_PHONG_KT_MUA_B", "MO_PHONG_CFO_MUA_A", "MO_PHONG_VIEW_MUA_A",
                                      "MO_PHONG_M1_ONLY_MUA_A")


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test HTTP M2 không chạy (không tính đạt)")
class M2Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        from kho_tri_thuc.k2 import crm_demo, m5_demo
        cls.db = "kho_test_m2http_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.admin = psycopg.connect(dsn, autocommit=True)
        crm_demo.khoi_tao(cls.admin)
        m5_demo.khoi_tao(cls.admin)
        m2_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_m2h_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOCREATEDB NOCREATEROLE IN ROLE app_web")
        app_dsn = f"postgresql://{cls.role}:{pw}@{dsn.split('@', 1)[1]}"
        cls.env = patch.dict(os.environ, {LocalApp.CRM_ENV: app_dsn, LocalApp.CRM_ENV_ADMIN: dsn, LocalApp.CRM_ENV_DB_KIEM_THU: "1"})
        cls.env.start()
        cls.app = LocalApp(ROOT / "cau_hinh.toml", Path(tempfile.mkdtemp(prefix="ktt_m2_http_")) / "web")
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
        status, _, ck = self.call("/api/m2")
        self.assertEqual(status, 200)
        self.assertIn("HttpOnly", ck)
        sid = ck.split(";", 1)[0].split("=", 1)[1]
        self.assertEqual(self.call("/api/m2/danh-tinh", {"dang_nhap": login}, sid)[0], 200)
        return sid

    def dem(self):
        q = lambda s: self.admin.execute(s).fetchone()[0]  # noqa: E731
        return tuple(q(f"SELECT count(*) FROM {t}") for t in ("giao_tiep.stage_tin_cay", "giao_tiep.lan_tiep_nhan_nguon", "giao_tiep.tep_tiep_nhan",
                                                              "kho.hoa_don_quan_sat", "kho.hoa_don_dong_phien_ban", "kho.mua_dich_dong",
                                                              "master.anh_xa_nguon", "kho.bien_nhan_thao_tac"))

    def test_luong_http_m2(self):
        self.assertEqual(self.call("/api/m2", token=False)[0], 403)
        self.assertEqual(self.call("/api/m2/nhan", {"mau": G01, "khoa": "h1"})[1]["error"], "CRM_PHIEN")

        m0 = self.phien(INTAKE)
        s = self.call("/api/m2", cookie=m0)[1]
        self.assertEqual(sorted(d["dang_nhap"] for d in s["danh_tinh_demo"]), sorted(m2_demo.dang_nhap_m2()))  # đúng 8 vai M2
        self.assertEqual(self.call("/api/m2/danh-tinh", {"dang_nhap": "MO_PHONG_M0_KHO_A"}, m0)[1]["error"], "DANH_TINH_M2")  # vai M5 không vào bộ chọn M2
        self.assertTrue(s["may_chu_nhan"])
        self.assertIn(G01, s["mau"])
        self.assertEqual({p["source_instance_id"] for p in s["pham_vi_nguon"]}, {INST})
        for key in ("actor", "phap_nhan_id", "identity", "line_facts", "mapping_id", "proof", "PROVEN"):
            with self.subTest(key=key):
                status, err, _ = self.call("/api/m2/nhan", {"mau": G01, "khoa": "h-x", key: "x"}, m0)
                self.assertEqual((status, err["error"]), (403, "M2_CLIENT_AUTHORITY"))
        status, err, _ = self.call("/api/m2/nhan", {"mau": G01, "khoa": "h-x", "duong_dan_tep": "C:/x"}, m0)
        self.assertEqual((status, err["error"]), (400, "M2_YEU_CAU_SAI"))
        base = {"source_instance": INST, "scope_ref": SCOPE, "coverage": "COMPLETE_INPUT"}
        ten, raw = m2_demo.mau(G01)
        than = {**base, "khoa": "h-tep", "native_b64": base64.b64encode(raw).decode(), "artifact_name": ten}
        truoc = self.dem()
        status, err, _ = self.call("/api/m2/nhan", {**than, "native_b64": "khong-phai-base64!"}, m0)
        self.assertEqual((status, err["error"]), (400, "M2_ARTIFACT"))
        self.assertEqual(self.dem(), truoc)
        status, r, _ = self.call("/api/m2/nhan", than, m0)
        self.assertEqual((status, r["lap_lai"], r["artifact_sha256"], r["promote"]["module"]), (200, False, sha256(raw), "M2"))
        hd = r["promote"]["items"][0]["hoa_don_id"]
        status, back, _ = self.call(f"/api/m2/nguon/{r['lan_tiep_nhan_id']}/raw/NATIVE", cookie=m0)
        self.assertEqual((status, back), (200, raw))
        truoc = self.dem()
        self.assertTrue(self.call("/api/m2/nhan", than, m0)[1]["lap_lai"])
        status, err, _ = self.call("/api/m2/nhan", {**than, "coverage": "PARTIAL_INPUT"}, m0)
        self.assertEqual((status, err["error"]), (409, "CAPTURE_KHAC_NOI_DUNG"))
        # giới hạn tải lên hữu hạn, công bố trong state; vượt → 413 mã M2 rõ ràng trước mọi ghi (thân JSON vẫn < 1 MiB)
        self.assertEqual(s["gioi_han_tai_len_byte"], 700_000)
        lon = {**than, "khoa": "h-lon", "native_b64": base64.b64encode(b"<" + b"x" * 700_000).decode()}
        status, err, _ = self.call("/api/m2/nhan", lon, m0)
        self.assertEqual((status, err["error"]), (413, "M2_TEP_QUA_LON"))
        self.assertEqual(self.dem(), truoc)

        kt = self.phien(KTA)
        status, err, _ = self.call(f"/api/m2/nguon/{r['lan_tiep_nhan_id']}/raw/NATIVE", cookie=kt)
        self.assertEqual((status, err["error"]), (403, "NGUON_KHONG_CO_QUYEN"))
        status, err, _ = self.call("/api/m2/nhan", {**base, "mau": G03, "khoa": "h-kt"}, kt)
        self.assertEqual((status, err["error"]), (403, "NGUON_KHONG_CO_QUYEN"))
        status, ct, _ = self.call(f"/api/m2/hoa-don/{hd}", cookie=kt)
        self.assertEqual((status, ct["duoc"]["M2_MAP"], ct["cau_noi"], ct["chieu"]), (200, False, [], "MUA_VAO"))
        row = ct["dong_nguon_hien_hanh"][0]["source_row_id"]
        # đúng cách GUI làm: chọn trong ứng viên literal máy chủ đã lọc cho chính dòng này (ref + revision + dòng logic đích)
        uv = [u for u in ct["ung_vien_dong"] if u["source_row_id"] == row]
        self.assertEqual({u["logical_line_key"] for u in uv}, {"DEMO_LINE_G01_A"})
        u = uv[0]
        ml = {"hoa_don_id": hd, "expected_graph": ct["expected_graph"], "source_row_id": row, "logical_line_key": u["logical_line_key"],
              "evidence_ref": u["evidence_ref"], "evidence_revision": u["evidence_revision"], "ly_do": "DEMO HTTP", "khoa": "ml-h"}
        status, err, _ = self.call("/api/m2/mapping-line", ml, kt)
        self.assertEqual((status, err["error"]), (403, "KHONG_CO_QUYEN_HANH_DONG"))

        cfo = self.phien(CFOA)
        truoc = self.dem()
        for sai, ma, code in (({"expected_graph": "0" * 64, "khoa": "ml-cu"}, 409, "M2_VERSION_CHANGED"),  # F3: mã SQL có chữ số giữ nguyên → 409
                              ({"approved": True}, 403, "M2_CLIENT_AUTHORITY"), ({"duong_dan": "x"}, 403, "M2_CLIENT_AUTHORITY"),
                              ({"stt": 1}, 400, "M2_YEU_CAU_SAI"),
                              ({"evidence_ref": "DEMO_M2_LITERAL_LINE_FACT_99_V1", "khoa": "ml-uv"}, 400, "M2_UNG_VIEN_KHONG_CO"),
                              ({"evidence_ref": "DEMO_M2_LITERAL_LINE_FACT_05_V1", "khoa": "ml-uv5"}, 400, "M2_UNG_VIEN_SAI_ARTIFACT"),
                              ({"logical_line_key": "DEMO_LINE_TUY_Y", "khoa": "ml-lg"}, 400, "M2_UNG_VIEN_SAI_DONG_LOGIC")):
            with self.subTest(sai=list(sai)):
                status, err, _ = self.call("/api/m2/mapping-line", {**ml, **sai}, cfo)
                self.assertEqual((status, err["error"]), (ma, code))
                self.assertNotIn("CONTEXT", err.get("message", ""))  # không lộ chi tiết SQL
        self.assertEqual(self.dem(), truoc)
        status, m, _ = self.call("/api/m2/mapping-line", ml, cfo)
        self.assertEqual((status, m["lap_lai"], m["evidence_ref_authority"]), (200, False, "EVIDENCE_ONLY_NOT_APPROVAL"))
        sau = self.dem()
        status, lai, _ = self.call("/api/m2/mapping-line", ml, cfo)  # R1: nguyên body/token A sau khi đồ thị đã đổi
        self.assertEqual((status, lai["lap_lai"]), (200, True))
        self.assertEqual({k: v for k, v in lai.items() if k != "lap_lai"}, {k: v for k, v in m.items() if k != "lap_lai"})
        status, err, _ = self.call("/api/m2/mapping-line", {**ml, "ly_do": "khác"}, cfo)
        self.assertEqual((status, err["error"]), (409, "IDEMPOTENCY_KHAC"))
        self.assertEqual(self.dem(), sau)
        ct = self.call(f"/api/m2/hoa-don/{hd}", cookie=cfo)[1]
        rt = {"hoa_don_id": hd, "cau_noi_id": ct["cau_noi"][0]["id"], "dich": "KHO", "expected_route_id": None, "expected_graph": ct["expected_graph"],
              "ly_do": "DEMO HTTP KHO", "khoa": "rt-h"}
        status, err, _ = self.call("/api/m2/route", {**rt, "dich": "NGAN_HANG"}, cfo)
        self.assertEqual((status, err["error"]), (400, "M2_YEU_CAU_SAI"))
        status, t, _ = self.call("/api/m2/route", rt, cfo)
        self.assertEqual((status, t["dich"], t["phien_ban"], t["financial_or_inventory_approval"]), (200, "KHO", 1, False))
        status, lai, _ = self.call("/api/m2/route", rt, cfo)
        self.assertEqual((status, lai["lap_lai"], lai["route_id"]), (200, True, t["route_id"]))
        # hai negative TÁCH RIÊNG (repair03): CAS đồ thị chạy trước kiểm tuyến mong đợi — mỗi ca một nguyên nhân, một mã chính xác, 0 delta
        nen = self.dem()
        self.assertGreater(nen[5], 0)  # nền không rỗng: đã có tuyến KHO thật
        status, err, _ = self.call("/api/m2/route", {**rt, "khoa": "rt-h-cu", "dich": "CHI_PHI"}, cfo)  # (1) khóa mới + đồ thị CŨ (trước route đầu)
        self.assertEqual((status, err["error"]), (409, "M2_VERSION_CHANGED"))
        self.assertEqual(self.dem(), nen)
        ct_moi = self.call(f"/api/m2/hoa-don/{hd}", cookie=cfo)[1]  # (2) đồ thị HIỆN HÀNH từ chi tiết thật sau route đầu
        self.assertNotEqual(ct_moi["expected_graph"], rt["expected_graph"])
        self.assertEqual([x["id"] for x in ct_moi["tuyen"] if x["hien_hanh"]], [t["route_id"]])
        status, err, _ = self.call("/api/m2/route", {**rt, "khoa": "rt-h-stale", "dich": "CHI_PHI", "expected_graph": ct_moi["expected_graph"],
                                                     "expected_route_id": None}, cfo)  # tuyến mong đợi sai (NULL trong khi đã có tuyến KHO)
        self.assertEqual((status, err["error"]), (409, "M2_ROUTE_STALE"))
        self.assertEqual(self.dem(), nen)
        status, lai2, _ = self.call("/api/m2/route", rt, cfo)  # retry nguyên body/token A vẫn trả kết quả gốc sau các negative
        self.assertEqual((status, lai2["lap_lai"], lai2["route_id"]), (200, True, t["route_id"]))
        status, err, _ = self.call("/api/m2/lien-ket/preview", {"hoa_don_id": hd}, cfo)
        self.assertEqual((status, err["error"]), (501, "M2_L11_CHUA_PHAT_HANH"))

        view = self.phien(VIEWA)
        s = self.call("/api/m2", cookie=view)[1]
        self.assertEqual([h["id"] for h in s["hoa_don"]], [hd])
        status, err, _ = self.call("/api/m2/route", {**rt, "khoa": "rt-v", "expected_route_id": t["route_id"], "dich": "CHI_PHI"}, view)
        self.assertEqual((status, err["error"]), (403, "KHONG_CO_QUYEN_HANH_DONG"))
        ktb = self.phien(KTB)
        self.assertEqual(self.call("/api/m2", cookie=ktb)[1]["hoa_don"], [])
        self.assertEqual(self.call(f"/api/m2/hoa-don/{hd}", cookie=ktb)[1]["error"], "HOA_DON")
        m1 = self.phien(M1A)
        s = self.call("/api/m2", cookie=m1)[1]
        self.assertEqual((s["hoa_don"], bool(s["khong_quyen"])), ([], True))
        self.assertEqual(self.call("/api/m2/danh-tinh", {"dang_nhap": "NGUOI_THAT_DEMO"}, m1)[1]["error"], "DANH_TINH_M2")

    def test_shell_co_trang_va_form_nhan_tep(self):
        """Chỉ kiểm tài nguyên được phục vụ (không thay kiểm tương tác trình duyệt cho epoch/form)."""
        _, raw_html, _ = self.call("/")
        for chuoi in (b"page-hoadonmua", b"m2-tl-native", b"m2-tl-crosswalk", b"m2-tl-khoa", b"m2-tl-loi", b"m2-chi-tiet"):
            self.assertIn(chuoi, raw_html)
        _, js, _ = self.call("/app.js")
        for chuoi in (b"m2Epoch", b"m2FormEpoch", b"m2XoaTrangThai", b"expected_graph", b'm2Act("mapping-line"', b'm2Act("route"', b"readAsArrayBuffer",
                      b"m2Tai(", b"m2DocGen", b"m2CtGen", b"evidence_revision", b"gioi_han_tai_len_byte", b"m2-tl-gioi-han"):
            self.assertIn(chuoi, js + raw_html)
        self.assertNotIn(b"m5Tai(`/api/m2/", js)  # F1: tải raw M2 không còn đi qua epoch M5


class PhanLoaiMaCsdl(unittest.TestCase):
    """F3: phân loại mã SQL không cần DB — mã ASCII HOA neo hai đầu (có chữ số) giữ nguyên; text khác → CSDL_TU_CHOI, không lộ chi tiết."""

    @unittest.skipUnless(psycopg is not None, "Không có psycopg")
    def test_ma_csdl(self):
        from kho_tri_thuc.giao_dien.server import M2_MA_403, M2_MA_409, LocalApp
        from kho_tri_thuc.ha_tang.primitives import DataError

        class Diag:
            def __init__(self, m):
                self.message_primary = m

        class Loi(psycopg.Error):
            def __init__(self, m):
                super().__init__(m)
                self._d = Diag(m)

            @property
            def diag(self):
                return self._d

        def ma(msg):
            def boom():
                raise Loi(msg)
            with self.assertRaises(DataError) as cm:
                LocalApp._crm_db(boom)
            self.assertNotIn("bí mật", str(cm.exception))
            return cm.exception.code

        self.assertEqual(ma("M2_VERSION_CHANGED: đồ thị đã đổi"), "M2_VERSION_CHANGED")
        self.assertIn("M2_VERSION_CHANGED", M2_MA_409)
        self.assertEqual(ma("KHONG_CO_QUYEN_M2_MAP: cần CFO"), "KHONG_CO_QUYEN_M2_MAP")
        self.assertIn("KHONG_CO_QUYEN_M2_MAP", M2_MA_403)
        self.assertEqual(ma("KHO_VERSION_CHANGED: cũ"), "KHO_VERSION_CHANGED")  # mã M5/legacy giữ nguyên
        self.assertEqual(ma("BIEN_NHAN_M5_CHI_CHU: x"), "BIEN_NHAN_M5_CHI_CHU")
        for xau in ("duplicate key value violates unique constraint \"bí mật\"", "m2_lower: x", "2M_SAI: x", "Ma Co Dau Cach: x", "MÃ_ĐỎ: x", "",
                    "A" * 81 + ": dài"):
            with self.subTest(xau=xau):
                self.assertEqual(ma(xau), "CSDL_TU_CHOI")


if __name__ == "__main__":
    unittest.main()
