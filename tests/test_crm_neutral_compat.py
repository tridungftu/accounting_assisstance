"""CRM neutral compatibility 01 — CRM/M1 trên lineage mặc định neutral16 (prefix1–12 + COMMON13 + M5/M2/L11), PostgreSQL DEMO thật.

CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN). Chỉ chạy khi Root cấp KHO_PG_DSN_TEST (không đọc .env/credentials trên đĩa). DB mới `kho_test_crmn_*`
migrate MẶC ĐỊNH (16, không legacy-M9/M13), seed CRM DEMO chính thức; HTTP qua LocalApp/LocalServer loopback cổng ngẫu nhiên với LOGIN app_web thường
(NOSUPERUSER, không BYPASSRLS); admin chỉ dùng cho setup/bộ chiếu M1/observer chỉ-đọc. Không kế thừa class/state test cũ, không mock product/UDF/converter.
Không DROP/DELETE/TRUNCATE/cleanup — DB/role/thư mục giữ làm bằng chứng. Thiếu driver/DSN → skip có khai báo (không tính đạt).

T01 neutral16: object tiền legacy (kho.tien_con_lai / kho.ghi_proof_tien_noi_bo / kho.chung_tu_tien_encoding) VẮNG; GET CRM của KT_A 200, tien=[];
    actor không có CRM bị chặn ở service, HTTP trả khong_quyen + 0 dữ liệu.
T02 HTTP m1-sao-ke PN_DEMO_A:truoc_hop_dong (300m) qua ingest→engine→converter: 200, khóa đỉnh đúng {m1, chieu}, converter ok thật, đúng một BANK
    logic + đề xuất, da_noi="0"; retry không thêm BANK/đề xuất/dòng, PK/business fields giữ nguyên.
T03 #6 kcn_goc → KT kiểm → CFO duyệt (V3+V4); lịch 300m/1.2b/1.5b; nối một phần → da_noi tăng đúng; replay cùng khóa/body cùng ID; đổi body cùng khóa
    → IDEMPOTENCY_KHAC; gỡ → HUY, da_noi giảm đúng; khóa cũ trả HUY hiện hành, không tái tạo.
T04 guard: vượt BANK còn lại (nghĩa vụ đủ) → VUOT_TIEN_KHA_DUNG; vượt nghĩa vụ (BANK đủ) → VUOT_NGHIA_VU; khác PN → LIEN_KET_THAM_CHIEU; CFO không
    quyền nối → KHONG_CO_QUYEN_HANH_DONG — mỗi ca âm 0 delta trên: bảng nghiệp vụ được chọn (toàn hàng), số lượng audit, last_value sequence,
    path+size tệp (không phải toàn byte/toàn audit/mọi trường sequence).
T05 KT_B không thấy tiền/HĐ của A; BANK2 nối 100m DOT-1 + 50m DOT-2 → da_noi 150m = SUM đầy đủ mọi link CRM active của BANK; gỡ 50m → 100m;
    snapshot BANK/đề xuất/PK/hash nguồn giữ qua nối/gỡ/từ chối.
Cấu hình: TOML fixture tối thiểu ghi trong thư mục temp được giữ lại (không đọc cau_hinh.toml/.env/var của repo).
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
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.kiem_chung import fixtures_crm as F

ROOT = Path(__file__).resolve().parents[1]
ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
BH, KTA, KTB, CFO, KT_M1 = "MO_PHONG_BAN_HANG", "MO_PHONG_KT_A", "MO_PHONG_KT_B", "MO_PHONG_CFO", "MO_PHONG_KT_KHONG_CRM_A"
LEGACY_HAM = ("kho.tien_con_lai(uuid)", "kho.ghi_proof_tien_noi_bo(uuid, smallint, text, text, text, text, text, text)")
LEGACY_BANG = ("kho.chung_tu_tien_encoding",)
# 02: môi trường fixture, entity PLHN_FIXTURE, VND scale 0, lưu trữ SQLite, Junsky tắt — ghi vào thư mục temp của test
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


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test CRM neutral16 không chạy (NOT_RUN, không tính đạt)")
class CrmNeutralCompat(unittest.TestCase):
    """Các test chạy theo thứ tự tên (t01…t05) trên MỘT DB neutral16; trạng thái truyền qua cls.state."""

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.ha_tang.pg_migrations import PG_SCHEMA_VERSION
        from kho_tri_thuc.k2 import crm_demo
        cls.db = "kho_test_crmn_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)
        cls.version = pg.migrate(cls.admin)  # MẶC ĐỊNH: neutral16, không legacy full-M13
        cls.schema = PG_SCHEMA_VERSION
        cls.ids = crm_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_crmn_" + uuid.uuid4().hex[:8], secrets.token_hex(16)  # bí mật chỉ trong bộ nhớ
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE IN ROLE app_web")
        app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        cls.env = patch.dict(os.environ, {LocalApp.CRM_ENV: app_dsn, LocalApp.CRM_ENV_ADMIN: cls.dsn, LocalApp.CRM_ENV_DB_KIEM_THU: "1"})
        cls.env.start()
        # 02: cấu hình fixture TỐI THIỂU trong chính thư mục temp được giữ lại (không đọc cau_hinh.toml/.env/var của repo)
        tam = Path(tempfile.mkdtemp(prefix="ktt_crmn_http_"))
        cls.cau_hinh = tam / "cau_hinh_fixture.toml"
        cls.cau_hinh.write_text(CAU_HINH_FIXTURE, encoding="utf-8")
        cls.app = LocalApp(cls.cau_hinh, tam / "web")
        cls.server = LocalServer(cls.app, 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.cookie_name = LocalApp.CRM_COOKIE
        cls.state = {}

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)
        cls.env.stop()
        cls.admin.close()  # chỉ đóng thứ test sở hữu; giữ DB/role/thư mục làm bằng chứng

    # ------------------------------------------------------------------ helpers
    def q(self, sql, params=()):
        return self.admin.execute(sql, params).fetchone()[0]

    def call(self, path, body=None, cookie=None, token=True):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=120)
        headers = {"X-KTT-Token": self.app.token} if token else {}
        if cookie:
            headers["Cookie"] = f"{self.cookie_name}={cookie}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        c.request("POST" if body is not None else "GET", path, body=None if body is None else json.dumps(body), headers=headers)
        r = c.getresponse()
        raw = r.read()
        ck = r.getheader("Set-Cookie")
        c.close()
        is_json = (r.getheader("Content-Type") or "").startswith("application/json")
        return r.status, (json.loads(raw or b"{}") if is_json else raw), ck

    def phien(self, login):
        status, _, ck = self.call("/api/crm")
        self.assertEqual(status, 200)
        self.assertIn("HttpOnly", ck)
        sid = ck.split(";", 1)[0].split("=", 1)[1]
        status, r, _ = self.call("/api/crm/danh-tinh", {"dang_nhap": login}, sid)
        self.assertEqual((status, r), (200, {"dang_nhap": login}))
        return sid

    def trang(self, sid):
        status, s, _ = self.call("/api/crm", cookie=sid)
        self.assertEqual(status, 200)
        return s

    def tu_choi(self, sid, path, body, ma):
        status, r, _ = self.call(path, body, sid)
        self.assertEqual((status, r.get("error")), (400, ma), r)

    def bank_300(self, s):
        _, ngay, so, _ = F.SAO_KE_M1["PN_DEMO_A"]["truoc_hop_dong"][0]
        hit = [t for t in s["tien"] if (t["ngay"], t["so_tien"]) == (ngay, str(so))]
        self.assertEqual(len(hit), 1, s["tien"])
        return hit[0]

    def legacy_vang(self):
        for sig in LEGACY_HAM:
            self.assertIsNone(self.q("SELECT to_regprocedure(%s)::text", (sig,)), sig)
        for t in LEGACY_BANG:
            self.assertIsNone(self.q("SELECT to_regclass(%s)::text", (t,)), t)

    def anh_chup(self):
        """Observer chỉ-đọc, phạm vi trung thực: các bảng nghiệp vụ ĐƯỢC CHỌN (chung_tu, chung_tu_dong, de_xuat, de_xuat_dong, lien_ket_chung_tu,
        lich_thu) so TOÀN HÀNG (to_jsonb); audit nhat_ky.su_kien chỉ so SỐ LƯỢNG; sequence chỉ so last_value; tệp chỉ so đường dẫn + kích thước.
        Không phải so toàn byte tệp, toàn hàng audit hay mọi trường sequence."""
        doc = lambda sql: [r[0] for r in self.admin.execute(sql)]  # noqa: E731
        tep = sorted(str(p.relative_to(self.app.root)) + ":" + str(p.stat().st_size) for p in Path(self.app.root).rglob("*") if p.is_file())
        return {"chung_tu": doc("SELECT to_jsonb(x)::text FROM kho.chung_tu x ORDER BY x.id"),
                "chung_tu_dong": doc("SELECT to_jsonb(x)::text FROM kho.chung_tu_dong x ORDER BY x.id"),
                "de_xuat": doc("SELECT to_jsonb(x)::text FROM kho.de_xuat x ORDER BY x.id"),
                "de_xuat_dong": doc("SELECT to_jsonb(x)::text FROM kho.de_xuat_dong x ORDER BY x.id"),
                "lien_ket": doc("SELECT to_jsonb(x)::text FROM kho.lien_ket_chung_tu x ORDER BY x.id"),
                "lich_thu": doc("SELECT to_jsonb(x)::text FROM master.lich_thu x ORDER BY x.id"),
                "su_kien": [self.q("SELECT count(*) FROM nhat_ky.su_kien")],
                "sequence": doc("SELECT schemaname || '.' || sequencename || '=' || coalesce(last_value, 0)::text FROM pg_sequences ORDER BY 1"),
                "tep": tep}

    def bank_snapshot(self):
        """BANK/đề xuất của A: PK + trường nghiệp vụ + hash nguồn — phải giữ qua nối/gỡ/từ chối."""
        return [tuple(r) for r in self.admin.execute(
            """SELECT c.id::text, c.khoa_nguon, c.so_tien_minor, c.tien_te, c.chieu, c.hash, c.ngay_nghiep_vu::text,
                      (SELECT jsonb_agg(jsonb_build_array(x.id, x.phien_ban) ORDER BY x.id) FROM kho.de_xuat x WHERE x.chung_tu_id = c.id)::text
               FROM kho.chung_tu c WHERE c.loai = 'SAO_KE' AND c.phap_nhan_id = %s ORDER BY c.id""", (self.ids["PN_DEMO_A"],))]

    def sum_doc_lap(self, bank_id):
        """Đáp án độc lập: SUM số tiền mọi link CRM active (≠ HUY) có BANK là chứng từ A — không gọi helper/UDF sản phẩm."""
        return str(self.q("SELECT coalesce(sum(so_tien_khop_minor), 0) FROM kho.lien_ket_chung_tu WHERE chung_tu_a_id = %s AND trang_thai <> 'HUY'",
                          (bank_id,)))

    # ------------------------------------------------------------------ T01
    def test_t01_neutral16_khong_legacy_va_get_crm(self):
        self.assertEqual((self.version, self.schema), (16, 16))
        self.legacy_vang()
        kt = self.phien(KTA)
        s = self.trang(kt)
        self.assertEqual((s["cau_hinh"], s["tien"], s["nguoi"]["dang_nhap"], s["nguoi"]["xem_tien"]), (True, [], KTA, True))
        self.assertNotIn("khong_quyen", s)
        m1 = self.phien(KT_M1)
        s = self.trang(m1)
        self.assertTrue(s.get("khong_quyen"))
        self.assertEqual((s["hop_dong"], s["tien"], s["ho_so"]), ([], [], []))
        self.state["kt"] = kt

    # ------------------------------------------------------------------ T02
    def test_t02_m1_sao_ke_http_tra_m1_chieu(self):
        kt = self.state["kt"]
        truoc = self.anh_chup()
        status, r, _ = self.call("/api/crm/m1-sao-ke", {"mau": "PN_DEMO_A:truoc_hop_dong"}, kt)
        self.assertEqual(status, 200, r)
        self.assertEqual(set(r), {"m1", "chieu"})  # API lịch sử: không proof/PROVEN giả
        self.assertNotIn("sqlite", r["m1"])
        self.assertTrue(r["chieu"]["ok"])
        self.assertEqual((r["chieu"].get("lech_dem"), r["chieu"].get("lech_noi_dung")), ([], []))
        self.assertEqual(r["m1"]["moi"], 1)
        self.assertGreater(r["m1"]["de_xuat"], 0)
        sau = self.anh_chup()
        self.assertEqual(len(sau["chung_tu"]) - len(truoc["chung_tu"]), 1)  # một BANK logic
        self.assertEqual(len(sau["de_xuat"]) - len(truoc["de_xuat"]), r["m1"]["de_xuat"])
        s = self.trang(kt)
        b = self.bank_300(s)
        self.assertEqual((b["da_noi"], b["nguon_m1"], b["so_de_xuat"]), ("0", True, r["m1"]["de_xuat"]))
        self.legacy_vang()
        # retry: không thêm BANK/đề xuất/dòng, PK + trường nghiệp vụ giữ nguyên (khác biệt kỹ thuật chỉ ở nhật ký nhận — khai báo: su_kien có thể tăng)
        snap = self.bank_snapshot()
        status, r2, _ = self.call("/api/crm/m1-sao-ke", {"mau": "PN_DEMO_A:truoc_hop_dong"}, kt)
        self.assertEqual((status, set(r2), r2["chieu"]["ok"], r2["m1"]["moi"]), (200, {"m1", "chieu"}, True, 0))
        lai = self.anh_chup()
        for k in ("chung_tu", "chung_tu_dong", "de_xuat", "de_xuat_dong", "lien_ket"):
            self.assertEqual(lai[k], sau[k], k)
        self.assertEqual(self.bank_snapshot(), snap)
        self.state["bank"] = b["id"]

    # ------------------------------------------------------------------ T03
    def test_t03_hop_dong_noi_mot_phan_replay_go(self):
        kt, bank = self.state["kt"], self.state["bank"]
        bh = self.phien(BH)
        status, r, _ = self.call("/api/crm/mau", {"mau": "kcn_goc"}, bh)
        self.assertEqual((status, r.get("ket_qua"), r.get("chan")), (200, "HOP_DONG_CHO_DUYET", []), r)
        pb = r["phien_ban_id"]
        self.assertEqual(self.call("/api/crm/kiem", {"id": pb}, kt)[0], 200)
        cfo = self.phien(CFO)
        status, r, _ = self.call("/api/crm/duyet", {"id": pb}, cfo)
        self.assertEqual((status, r.get("so_dot")), (200, 3), r)
        hd = next(h for h in self.trang(kt)["hop_dong"] if h["ma_noi_bo"] == "HDC-KCN-DEMO-01")
        lich = {l["khoa"]: l for l in hd["phien_ban"][0]["lich"]}
        self.assertEqual({k: l["so_tien"] for k, l in lich.items()}, {"COC-1": "300000000", "DOT-1": "1200000000", "DOT-2": "1500000000"})
        # nối một phần
        body = {"tien": bank, "lich": lich["COC-1"]["id"], "so_tien": "100000000", "khoa": "crmn-coc-mot-phan"}
        status, lk, _ = self.call("/api/crm/lien-ket", body, kt)
        self.assertEqual((status, lk.get("lap_lai")), (200, False), lk)
        self.assertEqual(self.bank_300(self.trang(kt))["da_noi"], "100000000")
        self.assertEqual(self.sum_doc_lap(bank), "100000000")
        status, lai, _ = self.call("/api/crm/lien-ket", body, kt)
        self.assertEqual((status, lai.get("lien_ket_id"), lai.get("lap_lai")), (200, lk["lien_ket_id"], True))
        self.tu_choi(kt, "/api/crm/lien-ket", {**body, "so_tien": "200000000"}, "IDEMPOTENCY_KHAC")
        self.assertEqual(self.bank_300(self.trang(kt))["da_noi"], "100000000")
        # gỡ → HUY, da_noi giảm đúng; khóa cũ trả HUY hiện hành, không tái tạo
        status, go, _ = self.call("/api/crm/go-lien-ket", {"id": lk["lien_ket_id"], "ly_do": "DEMO gỡ neutral16"}, kt)
        self.assertEqual(status, 200, go)
        self.assertEqual(self.bank_300(self.trang(kt))["da_noi"], "0")
        self.assertEqual(self.sum_doc_lap(bank), "0")
        status, cu, _ = self.call("/api/crm/lien-ket", body, kt)
        self.assertEqual((status, cu), (200, {"lien_ket_id": lk["lien_ket_id"], "lap_lai": True, "trang_thai": "HUY"}))
        self.assertEqual(self.q("SELECT count(*) FROM kho.lien_ket_chung_tu WHERE chung_tu_a_id = %s", (bank,)), 1)
        self.legacy_vang()
        self.state.update(lich={k: l["id"] for k, l in lich.items()}, cfo=cfo)

    # ------------------------------------------------------------------ T04
    def test_t04_guard_ngan_sach_va_quyen(self):
        kt, bank, lich, cfo = self.state["kt"], self.state["bank"], self.state["lich"], self.state["cfo"]
        # dương: nối đủ 300m BANK vào cọc 300m
        status, r, _ = self.call("/api/crm/lien-ket", {"tien": bank, "lich": lich["COC-1"], "so_tien": "300000000", "khoa": "crmn-coc-du"}, kt)
        self.assertEqual((status, r.get("lap_lai")), (200, False), r)
        # BANK thứ hai/ba thật qua M1 (sau hợp đồng) để có BANK còn tiền cho ca vượt nghĩa vụ
        status, r, _ = self.call("/api/crm/m1-sao-ke", {"mau": "PN_DEMO_A:sau_hop_dong"}, kt)
        self.assertEqual((status, set(r), r["chieu"]["ok"]), (200, {"m1", "chieu"}, True))
        s = self.trang(kt)
        con_tien = [t for t in s["tien"] if t["id"] != bank and t["da_noi"] == "0"]
        self.assertTrue(con_tien, s["tien"])
        bank2 = con_tien[0]["id"]
        kb = self.phien(KTB)
        for ten, sid, body, ma in (
                ("vượt BANK còn lại, nghĩa vụ DOT-1 còn đủ", kt, {"tien": bank, "lich": lich["DOT-1"], "so_tien": "1", "khoa": "crmn-het-tien"},
                 "VUOT_TIEN_KHA_DUNG"),
                ("vượt nghĩa vụ COC-1 đã đủ, BANK2 còn tiền", kt, {"tien": bank2, "lich": lich["COC-1"], "so_tien": "1", "khoa": "crmn-vuot-nv"},
                 "VUOT_NGHIA_VU"),
                ("khác pháp nhân: KT_B nối BANK/đợt của A", kb, {"tien": bank2, "lich": lich["DOT-1"], "so_tien": "1", "khoa": "crmn-cheo"},
                 "LIEN_KET_THAM_CHIEU"),
                ("CFO không có quyền nối", cfo, {"tien": bank2, "lich": lich["DOT-1"], "so_tien": "1", "khoa": "crmn-cfo"},
                 "KHONG_CO_QUYEN_HANH_DONG")):
            with self.subTest(ca=ten):
                truoc = self.anh_chup()
                self.tu_choi(sid, "/api/crm/lien-ket", body, ma)
                self.assertEqual(self.anh_chup(), truoc)  # 0 delta: bảng chọn toàn hàng, số audit, last_value sequence, path+size tệp
        self.assertEqual(self.bank_300(self.trang(kt))["da_noi"], "300000000")
        self.state.update(bank2=bank2, kb=kb)

    # ------------------------------------------------------------------ T05
    def test_t05_rieng_tu_bat_bien_va_sum_day_du(self):
        kt, kb, bank, bank2, lich = self.state["kt"], self.state["kb"], self.state["bank"], self.state["bank2"], self.state["lich"]
        sb = self.trang(kb)
        self.assertEqual(({h["phap_nhan"] for h in sb["hop_dong"]} & {"PN_DEMO_A"}, [t for t in sb["tien"] if t["phap_nhan"] == "PN_DEMO_A"]), (set(), []))
        snap = self.bank_snapshot()
        self.assertTrue(snap)
        # dương trước: BANK2 nối 100m vào DOT-1 và 50m vào DOT-2 (hai link active cùng BANK, KHÁC đợt — guard cũ cấm hai link active cùng
        # BANK/đợt, giữ nguyên) → da_noi = SUM đầy đủ mọi đợt, không lọc một hợp đồng/đợt
        for khoa, dot, so in (("crmn-d1-a", "DOT-1", "100000000"), ("crmn-d2-b", "DOT-2", "50000000")):
            status, r, _ = self.call("/api/crm/lien-ket", {"tien": bank2, "lich": lich[dot], "so_tien": so, "khoa": khoa}, kt)
            self.assertEqual((status, r.get("lap_lai")), (200, False), r)
        s = self.trang(kt)
        doc = {t["id"]: t["da_noi"] for t in s["tien"]}
        self.assertEqual((doc[bank2], self.sum_doc_lap(bank2)), ("150000000", "150000000"))
        self.assertEqual((doc[bank], self.sum_doc_lap(bank)), ("300000000", "300000000"))
        for t in s["tien"]:
            self.assertEqual(t["da_noi"], self.sum_doc_lap(t["id"]), t)
        # từ chối giữa chừng không đổi gì; gỡ một link → SUM giảm đúng phần đó
        self.tu_choi(kb, "/api/crm/lien-ket", {"tien": bank2, "lich": lich["DOT-1"], "so_tien": "1", "khoa": "crmn-cheo-2"}, "LIEN_KET_THAM_CHIEU")
        lk_b = self.q("""SELECT id::text FROM kho.lien_ket_chung_tu WHERE chung_tu_a_id = %s AND so_tien_khop_minor = 50000000 AND trang_thai <> 'HUY'""",
                      (bank2,))
        status, _, _ = self.call("/api/crm/go-lien-ket", {"id": lk_b, "ly_do": "DEMO gỡ một link"}, kt)
        self.assertEqual(status, 200)
        self.assertEqual(({t["id"]: t["da_noi"] for t in self.trang(kt)["tien"]}[bank2], self.sum_doc_lap(bank2)), ("100000000", "100000000"))
        # BANK/đề xuất/PK/hash nguồn giữ nguyên qua nối/gỡ/từ chối
        self.assertEqual(self.bank_snapshot(), snap)
        self.assertEqual(self.trang(kt)["nguoi"]["dang_nhap"], KTA)  # positive sau cùng vẫn đọc được
        self.legacy_vang()


if __name__ == "__main__":
    unittest.main()
