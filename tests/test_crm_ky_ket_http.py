"""CRM-41-04A — kiểm HTTP thật G4 ký lần đầu trên LocalApp/LocalServer + PostgreSQL DEMO mới (CODE_ONLY: coder viết, CHƯA CHẠY — NOT_RUN_CODE_ONLY).

Chạy khi Root cấp KHO_PG_DSN_TEST lúc chạy (DSN chủ CSDL; không đọc .env/var, không hardcode credentials). DB MỚI `kho_test_crmky_*` migrate mặc định
(1–23), seed CRM DEMO + crm_g_demo (không M9, không bootstrap chung). Mẫu/báo giá/bản soạn/xuất dựng bằng LUỒNG DỊCH VỤ THẬT qua HTTP (mượn helper
của tests/test_crm_giao_ket_http.py — không sửa file đó). Phân công CRM_KY_KET + phạm vi ký do CHỦ CSDL khai (đúng vai trò quản trị của handoff —
không tự cấp qua HTTP, không suy từ người tạo). KHÔNG owner-forge PDF_DAT: nhánh ký dương chỉ chạy khi có Word đã ghim + guard (`_co_word()`)
và bản xuất G3 thật đạt PDF_DAT; không có → ghi rõ nhánh đã chạy (ký bị 409 CRM_KY_XUAT_CHUA_DAT) và các ca dương skip = NOT_RUN (không tính đạt).
Ánh xạ tiêu chí handoff §7: 1 → k02 · 2 → k03/k05 · 3/4 → k05 · 5 → k06 · 6 → k05 · 7 → k02/k04/k07 · 8 → k06/k07 · 9 → tests/crm_ky_ket_async.cjs ·
10 → test_crm_ky_ket.PrefixVaPhamVi. Không DROP/DELETE/cleanup — DB/role/thư mục giữ làm bằng chứng. Không chứng minh GUI/trình duyệt thật.
"""

from __future__ import annotations

import hashlib
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

import test_crm_giao_ket_http as GKH  # chỉ mượn helper (không đưa lớp TestCase của file đó vào module này)
from test_crm_giao_ket import _co_word
from test_crm_ky_ket import pdf_tong_hop

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
TAI, KT, CFO, BH = GKH.TAI, GKH.KT, GKH.CFO, GKH.BH
KT_NO_CRM, CFO_B = GKH.KT_NO_CRM, GKH.CFO_B
ngay = GKH.ngay


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — HTTP CRM-41-04A không chạy (NOT_RUN, không tính đạt)")
class CrmKyKetHttp(unittest.TestCase):
    """Chạy theo thứ tự tên k01…k08 trên MỘT DB/một máy chủ; trạng thái qua cls.s."""

    # helper G2/G3 dùng lại nguyên (cùng cookie/khóa/luồng mẫu thật). Lớp TestCase G2/G3 chỉ tham chiếu trong thân lớp (không gán ở mức module →
    # unittest không nạp/chạy lại bộ G2/G3 trong module này).
    _H = GKH.CrmGiaoKetHttp
    goi, sid, K, ok, loi, get, q, loai_a, du_an, dem = _H.goi, _H.sid, _H.K, _H.ok, _H.loi, _H.get, _H.q, _H.loai_a, _H.du_an, _H.dem
    mau_hieu_luc, bao_gia = _H.mau_hieu_luc, _H.bao_gia
    # staticmethod/classmethod lấy NGUYÊN descriptor (không bind vào lớp G2/G3)
    khoa_may, _dung, _dong_ket_noi_app = _H.__dict__["khoa_may"], _H.__dict__["_dung"], _H.__dict__["_dong_ket_noi_app"]
    del _H

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.k2 import crm_demo, crm_g_demo
        cls.db = "kho_test_crmky_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)
        cls.addClassCleanup(GKH._dong, cls.admin)
        cls.version = pg.migrate(cls.admin)
        crm_demo.khoi_tao(cls.admin)
        cls.seed = crm_g_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_crmky_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE IN ROLE app_web")
        cls.app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        cls.env = patch.dict(os.environ, {LocalApp.CRM_ENV: cls.app_dsn, LocalApp.CRM_ENV_ADMIN: cls.dsn, LocalApp.CRM_ENV_DB_KIEM_THU: "1"})
        cls.env.start()
        cls.addClassCleanup(cls.env.stop)
        cls.tam = Path(tempfile.mkdtemp(prefix="ktt_crmky_http_"))  # giữ lại
        (cls.tam / "cau_hinh_fixture.toml").write_text(GKH.CAU_HINH_FIXTURE, encoding="utf-8")
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

    # ------------------------------------------------------------------ helpers G4
    def ky(self, login, info, raw, ct="application/pdf", headers=None):
        """POST raw PDF + X-CRM-G-Info (JSON percent-encoded) — đúng hợp đồng route UI dùng."""
        h = {"X-CRM-G-Info": quote(json.dumps(info, ensure_ascii=False)), "Content-Type": ct}
        h.update(headers or {})
        return self.goi("/api/crm/giao-ket/ky-ket", cookie=self.sid(login), raw=raw, headers=h)[:2]

    def tai(self, login, ky_id):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=120)
        c.request("GET", f"/api/crm/giao-ket/ban-ky/{ky_id}/tep", headers={"X-KTT-Token": self.app.token, "Cookie": f"{self.app.CRM_COOKIE}={self.sid(login)}"})
        r = c.getresponse()
        out, hd = r.read(), {k.lower(): v for k, v in r.getheaders()}
        c.close()
        return r.status, out, hd

    def info(self, **sua):
        d = {"soan_id": self.s["soan"], "expected_revision": self.s["rev"], "expected_xuat_id": self.s["xuat"], "ten_tep": "ban-da-ky.pdf",
             "ngay_ky": ngay(0), "co_sua": False, "khoa": self.K("ky-1")}
        d.update(sua)
        return d

    def dem_ky(self):
        return (self.q("SELECT count(*) FROM master.crm_hd_ky"), self.q("SELECT count(*) FROM master.crm_hd_ky_g5"),
                self.q("SELECT count(*) FROM nhat_ky.su_kien WHERE hanh_dong = 'CRM_KY_KET'"))

    def kho_ky(self):
        return sorted(p.name for p in self.tam.rglob("*") if p.is_file() and p.parent.name == "ky" and p.parent.parent.name == "giao-ket")

    def can_pdf(self):
        try:
            import pypdfium2  # noqa: F401
        except ImportError:
            self.skipTest("NOT_RUN: máy chủ thiếu pypdfium2 — route trả 503 CRM_KY_PDF_CHUA_KIEM_DUOC (fail closed), ca 409 căn cứ không kiểm được")

    def can_word(self):
        if not (self.co_word and self.s.get("pdf_dat")):
            self.skipTest("NOT_RUN: chưa có bản xuất G3 PDF_DAT thật (Word/PDF chưa sẵn sàng) — không owner-forge PDF_DAT; ca dương G4 không tính đạt")

    def cap_phan_cong(self, login):
        """Chủ CSDL khai phân công CRM_KY_KET (cùng bảng/kỷ luật M0018) — không qua HTTP, không tự cấp."""
        return str(self.q("""INSERT INTO master.phan_cong_hanh_dong (nguoi_dung_id, phap_nhan_id, module, hanh_dong, loai_hinh_id, cap_boi)
                             SELECT n.id, s.phap_nhan_id, 'CRM', 'CRM_KY_KET', s.loai_hinh_id, 'TEST:CRM-41-04A'
                             FROM master.nguoi_dung n, master.crm_hd_soan s WHERE n.dang_nhap = %s AND s.id = %s RETURNING id""", (login, self.s["soan"])))

    def cap_pham_vi(self, pc):
        """Chủ CSDL khai phạm vi ký: đúng HĐ/bản soạn + dự án của HĐ + digest khách dự thảo của revision hiện hành (HĐ chưa có mã đối tác)."""
        return str(self.q("""INSERT INTO master.crm_ky_pham_vi (phan_cong_id, phap_nhan_id, hop_dong_id, soan_id, du_an_id, khach_du_thao_sha256, cap_boi)
                             SELECT %s, s.phap_nhan_id, s.hop_dong_id, s.id, h.du_an_id,
                                    encode(sha256(convert_to((r.du_lieu -> 'bao_gia' -> 'khach' -> 'du_thao')::text, 'UTF8')), 'hex'), 'TEST:CRM-41-04A'
                             FROM master.crm_hd_soan s JOIN master.hop_dong h ON h.id = s.hop_dong_id
                             JOIN master.crm_hd_soan_rev r ON r.soan_id = s.id AND r.revision = s.revision_hien_hanh
                             WHERE s.id = %s RETURNING id""", (pc, self.s["soan"])))

    # ------------------------------------------------------------------ k01: dựng HĐ CRM qua luồng thật tới bản xuất G3
    def test_k01_dung_ban_soan_va_xuat_that(self):
        self.assertEqual(self.version, 23)
        pb, _ = self.mau_hieu_luc("HD_KY_" + self.run_id, ngay(-2), "MAU V1")
        r = self.ok(BH, "bao-gia/luu", {"bao_gia_id": None, "expected_revision": None, "du_lieu": self.bao_gia(), "khoa": self.K("bg")})
        a = self.ok(BH, "bao-gia/chuyen", {"bao_gia_id": r["bao_gia_id"], "expected_revision": 1, "mau_phien_ban_id": pb, "khoa": self.K("cv")})
        self.s["soan"], self.s["hd"] = a["soan_id"], a["hop_dong_id"]
        bg = dict(self.get(BH, "soan/" + a["soan_id"])["du_lieu"]["bao_gia"])
        bg["fx"] = None  # như g06: không gửi lại phần FX do máy chủ ghi
        gt ={"so_hop_dong": "HĐ-DEMO-KY-0001", "ngay_ky": ngay(0), "ten_hien_thi_demo": "NGƯỜI MUA DEMO",
              "gia_tri_hop_dong": {"so_tien": "1000000000", "tien_te": "VND"}}
        self.ok(BH, "soan/luu", {"soan_id": a["soan_id"], "expected_revision": 1, "gia_tri_truong": gt, "bao_gia": bg,
                                 "khoa": self.K("so-2")})
        x = self.ok(BH, "soan/xuat", {"soan_id": a["soan_id"], "expected_revision": 2, "khoa": self.K("x1")})
        self.s["rev"], self.s["xuat"], self.s["x"] = 2, x["xuat_id"], x
        self.s["pdf_dat"] = x["trang_thai"] == "PDF_DAT"
        self.assertEqual(x["trang_thai"], "PDF_DAT" if self.co_word else "PDF_CHUA_SAN_SANG")  # ghi rõ nhánh đã chạy
        self.assertEqual(self.q("SELECT trang_thai FROM master.crm_hd_soan WHERE id = %s", (a["soan_id"],)), "CHO_KY" if self.s["pdf_dat"] else "SOAN_THAO")

    # ------------------------------------------------------------------ k02 (§7.1/§7.7): hợp đồng yêu cầu + quyền trước mọi thứ
    def test_k02_hop_dong_yeu_cau_va_quyen(self):
        raw = pdf_tong_hop(1, "BAN KY DEMO K02")
        trc, kho = self.dem_ky(), self.kho_ky()
        for sua, ma in (({"actor": BH}, "CRM_G_CLIENT_AUTHORITY"), ({"trang_thai": "DA_KY"}, "CRM_G_CLIENT_AUTHORITY"),
                        ({"sha256": "0" * 64}, "CRM_G_CLIENT_AUTHORITY")):
            st, r = self.ky(BH, {**self.info(), **sua}, raw)
            self.assertEqual((st, r.get("error")), (403, ma), sua)
        st, r = self.ky(BH, {**self.info(), "la": 1}, raw)
        self.assertEqual((st, r.get("error")), (400, "CRM_G_YEU_CAU_SAI"))
        for sua, ma in (({"co_sua": None}, "CRM_KY_KHAI_SAI"), ({"co_sua": "false"}, "CRM_KY_KHAI_SAI"), ({"co_sua": True}, "CRM_KY_KHAI_SAI"),
                        ({"co_sua": False, "mo_ta": "x"}, "CRM_KY_KHAI_SAI"), ({"ngay_ky": "21/10/2026"}, "CRM_G_YEU_CAU_SAI"),
                        ({"ten_tep": "../a.pdf"}, "CRM_G_YEU_CAU_SAI"), ({"expected_revision": "2"}, "CRM_G_YEU_CAU_SAI"), ({"khoa": "k k"}, "CRM_G_KHOA")):
            st, r = self.ky(BH, self.info(**sua), raw)
            self.assertEqual((st, r.get("error")), (400, ma), sua)
        st, r = self.ky(BH, self.info(), raw, ct="application/json")
        self.assertEqual((st, r.get("error")), (400, "CRM_KY_PDF_HONG"))
        st, r = self.ky(BH, {}, raw, headers={"X-CRM-G-Info": "x" * 24001})
        self.assertEqual((st, r.get("error")), (400, "CRM_G_YEU_CAU_SAI"))
        # quyền/phạm vi TRƯỚC parse bytes: BH chưa phân công → 403, kể cả khi bytes không phải PDF (không lộ lỗi parser)
        st, r = self.ky(BH, self.info(), b"khong-phai-pdf")
        self.assertEqual((st, r.get("error")), (403, "CRM_G_KHONG_CO_QUYEN"))
        d = self.get(BH, "giao-ket/ky/" + self.s["soan"])
        self.assertEqual((d["quyen"]["ky"], d["quyen"]["doc"], d["quyen"]["ly_do"]), (False, False, "CRM_G_KHONG_CO_QUYEN"))
        self.assertNotIn("can_cu", d)
        self.s["pc"] = self.cap_phan_cong(BH)
        st, r = self.ky(BH, self.info(), b"khong-phai-pdf")
        self.assertEqual((st, r.get("error")), (403, "CRM_KY_CHUA_CO_PHAM_VI"))  # có vai+phân công nhưng chưa có phạm vi: không suy từ người tạo HĐ
        d = self.get(BH, "giao-ket/ky/" + self.s["soan"])
        self.assertEqual((d["quyen"]["ky"], d["quyen"]["ly_do"]), (False, "CRM_KY_CHUA_CO_PHAM_VI"))
        # ngoài PN/module: 404 ẩn; không hash/căn cứ
        for login in (CFO_B, KT_NO_CRM):
            st, r = self.ky(login, self.info(khoa=self.K("ky-ngoai")), raw)
            self.assertEqual((st, r.get("error")), (404, "CRM_G_KHONG_THAY"), login)
            self.get(login, "giao-ket/ky/" + self.s["soan"], status=404)
        # KT đọc được căn cứ (vai sẵn có) nhưng KHÔNG ký
        d = self.get(KT, "giao-ket/ky/" + self.s["soan"])
        self.assertEqual((d["quyen"]["ky"], d["quyen"]["doc"]), (False, True))
        st, r = self.ky(KT, self.info(khoa=self.K("ky-kt")), raw)
        self.assertIn((st, r.get("error")), {(403, "CRM_G_KHONG_CO_QUYEN"), (404, "CRM_G_KHONG_THAY")})
        self.get(BH, "giao-ket/ky/" + self.s["soan"] + "?x=1", status=400)  # query lạ bị từ chối
        self.assertEqual((self.dem_ky(), self.kho_ky()), (trc, kho))  # không hàng/tệp nào sinh ra

    # ------------------------------------------------------------------ k03 (§7.2): phạm vi đủ nhưng căn cứ chưa đạt → 409, không ghi
    def test_k03_pham_vi_va_can_cu_chua_dat(self):
        self.s["pv"] = self.cap_pham_vi(self.s["pc"])
        d = self.get(BH, "giao-ket/ky/" + self.s["soan"])
        self.assertEqual(d["quyen"]["doc"], True)
        self.assertEqual(d["quyen"]["ky"], self.s["pdf_dat"])  # chỉ ký được khi CHO_KY thật
        self.assertEqual(d["can_cu"]["xuat_id"], self.s["xuat"])
        self.assertNotIn("_bao_gia", d["can_cu"])
        self.assertEqual(d["can_cu"]["tom_tat"], {"so_dong": 2, "tong_minor": "1000000000", "tien_te": "VND"})
        self.can_pdf()
        trc, kho = self.dem_ky(), self.kho_ky()
        raw = pdf_tong_hop(1, "BAN KY DEMO K03")
        st, r = self.ky(BH, self.info(expected_xuat_id=str(uuid.uuid4()), khoa=self.K("ky-xu")), raw)
        self.assertEqual((st, r.get("error")), (409, "CRM_KY_XUAT_CU"))
        if not self.s["pdf_dat"]:
            st, r = self.ky(BH, self.info(khoa=self.K("ky-chua-dat")), raw)
            self.assertEqual((st, r.get("error")), (409, "CRM_KY_XUAT_CHUA_DAT"))  # nhánh không Word: không ký trên bản chưa có PDF đạt
        self.assertEqual((self.dem_ky(), self.kho_ky()), (trc, kho))
        # phạm vi: chỉ thu hồi một lần, không xóa/sửa
        for sql in ("DELETE FROM master.crm_ky_pham_vi WHERE id = %s", "UPDATE master.crm_ky_pham_vi SET du_an_id = NULL WHERE id = %s"):
            with self.assertRaises(psycopg.Error) as cm:
                with self.admin.transaction():
                    self.admin.execute(sql, (self.s["pv"],))
            self.assertIn("CRM_KY_PHAM_VI_BAT_BIEN", str(cm.exception))

    # ------------------------------------------------------------------ k04 (§7.2/§7.7): PDF hỏng/rỗng sau quyền; replay không lộ cho vai khác
    def test_k04_pdf_hong_va_rong(self):
        for raw, ma, st_ in ((b"", "CRM_KY_PDF_RONG", 400), (b"%PDF-1.4\n%%EOF\n", "CRM_KY_PDF_HONG", 400), (b"PK\x03\x04", "CRM_KY_PDF_HONG", 400)):
            st, r = self.ky(BH, self.info(khoa=self.K("ky-hong")), raw)
            self.assertIn((st, r.get("error")), {(st_, ma), (503, "CRM_KY_PDF_CHUA_KIEM_DUOC")}, raw[:10])  # thiếu parser: fail closed, không nhận

    # ------------------------------------------------------------------ k05 (§7.3/§7.4/§7.6): ký lần đầu (CHỈ khi có PDF_DAT thật)
    def test_k05_ky_lan_dau_replay_va_g5(self):
        self.can_word()
        raw = pdf_tong_hop(2, "BAN KY DEMO K05")
        g3 = self.goi(f"/api/crm/giao-ket/tep/{self.s['xuat']}/pdf", cookie=self.sid(BH))[1]
        st, r = self.ky(BH, self.info(khoa=self.K("ky-trung")), g3)
        self.assertEqual((st, r.get("error")), (409, "CRM_KY_PDF_LA_BAN_XUAT"))  # tải lại chính PDF bản xuất ≠ bằng chứng ký
        st, r = self.ky(BH, self.info(ngay_ky=ngay(1), khoa=self.K("ky-tuong-lai")), raw)
        self.assertEqual((st, r.get("error")), (400, "CRM_KY_NGAY_SAI"))
        st, r = self.ky(BH, self.info(expected_revision=1, khoa=self.K("ky-rev")), raw)
        self.assertEqual((st, r.get("error")), (409, "CRM_GK_REVISION_CU"))
        trc, lt = self.dem_ky(), self.dem()["lich_thu"]
        st, r = self.ky(BH, self.info(), raw)
        self.assertEqual(st, 200, r)
        self.assertEqual((r["trang_thai"], r["hien_thi"], r["lap_lai"], r["co_sua"]), ("DA_KY", "Đã ký — chờ kế toán kiểm", False, False))
        self.assertEqual(r["g5"], {"trang_thai": "NOT_SELECTED", "ly_do": "CHUA_AP_DUNG_CHON_MAU"})
        self.assertEqual((r["ky_pdf_sha256"], r["ky_pdf_len"], r["g3_pdf_sha256"]), (hashlib.sha256(raw).hexdigest(), len(raw), self.s["x"]["pdf_sha256"]))
        self.s["ky_id"], self.s["raw"] = r["ky_id"], raw
        self.assertEqual(tuple(x - y for x, y in zip(self.dem_ky(), trc)), (1, 1, 1))
        hd = self.admin.execute("SELECT trang_thai, crm_giao_ket, ngay_ky, phien_ban_hien_hanh FROM master.hop_dong WHERE id = %s", (self.s["hd"],)).fetchone()
        self.assertEqual(tuple(hd), ("DA_KY", "DA_KY", None, None))  # ngày ký KHÔNG thành ngày/phiên bản hiệu lực
        self.assertEqual(self.dem()["lich_thu"], lt)  # không lịch thu/nghĩa vụ
        # replay: cùng khóa + cùng body → cùng kết quả, 0 hàng mới; cùng khóa khác body → 409; khóa mới + cùng PDF/căn cứ/khai báo → cùng bản ký
        st, r2 = self.ky(BH, self.info(), raw)
        self.assertEqual((st, r2["ky_id"], r2["lap_lai"]), (200, r["ky_id"], True))
        st, r3 = self.ky(BH, self.info(khoa=self.K("ky-moi")), raw)
        self.assertEqual((st, r3["ky_id"], r3["lap_lai"]), (200, r["ky_id"], True))
        st, e = self.ky(BH, self.info(nguoi_ky_khach="KHÁCH DEMO"), raw)
        self.assertEqual((st, e.get("error")), (409, "CRM_G_IDEMPOTENCY_KHAC"))
        st, e = self.ky(BH, self.info(khoa=self.K("ky-khac")), pdf_tong_hop(1, "BAN KHAC"))
        self.assertEqual((st, e.get("error")), (409, "CRM_KY_DA_KY"))  # không thay bản ký (Q-RETURN ngoài lượt)
        st, e = self.ky(BH, self.info(co_sua=True, mo_ta="sửa điều 5", khoa=self.K("ky-co")), raw)
        self.assertEqual((st, e.get("error")), (409, "CRM_KY_DA_KY"))
        self.assertEqual(tuple(x - y for x, y in zip(self.dem_ky(), trc)), (1, 1, 1))
        nk = self.admin.execute("SELECT sau FROM nhat_ky.su_kien WHERE hanh_dong = 'CRM_KY_KET' AND doi_tuong_id = %s", (r["ky_id"],)).fetchone()[0]
        self.assertNotIn("KHÁCH", json.dumps(nk, ensure_ascii=False))  # nhật ký không PII

    # ------------------------------------------------------------------ k06 (§7.5/§7.8): bất biến sau ký + tải bản ký
    def test_k06_bat_bien_sau_ky_va_tai(self):
        self.can_word()
        sid = self.s["soan"]
        for path, body in (("soan/luu", {"soan_id": sid, "expected_revision": 2, "gia_tri_truong": {"so_hop_dong": "X"}, "khoa": self.K("sau-luu")}),
                           ("soan/xuat", {"soan_id": sid, "expected_revision": 2, "khoa": self.K("sau-xuat")})):
            st, r, _ = self.goi("/api/crm/" + path, body, self.sid(BH))
            self.assertEqual(st, 409, (path, r))
            self.assertIn(r.get("error"), {"CRM_GK_DA_KY", "CRM_GK_TRANG_THAI"}, (path, r))  # backend chặn (không chỉ nút UI)
        for sql in ("UPDATE master.crm_hd_soan SET trang_thai = 'CHO_KY' WHERE id = %s", "UPDATE master.hop_dong SET crm_giao_ket = 'CHO_KY' WHERE id = %s",
                    "UPDATE master.crm_hd_ky SET ngay_ky = ngay_ky - 1 WHERE id = %s", "DELETE FROM master.crm_hd_ky_g5 WHERE ky_id = %s"):
            with self.assertRaises(psycopg.Error) as cm:
                with self.admin.transaction():
                    self.admin.execute(sql, (self.s["hd"] if "hop_dong" in sql else sid if "crm_hd_soan" in sql else self.s["ky_id"],))
            self.assertRegex(str(cm.exception), "CRM_GK_DA_KY|CRM_G_BAT_BIEN", sql)
        d = self.get(KT, "giao-ket/ky/" + sid)
        self.assertEqual((d["trang_thai"], d["hien_thi"], d["ban_ky"]["ky_id"], d["ban_ky"]["g5"]["trang_thai"]),
                         ("DA_KY", "Đã ký — chờ kế toán kiểm", self.s["ky_id"], "NOT_SELECTED"))
        self.assertEqual(d["can_cu"]["xuat_id"], self.s["xuat"])  # căn cứ = snapshot bản xuất đã ký
        for login in (BH, KT):
            trc = self.q("SELECT count(*) FROM nhat_ky.su_kien WHERE hanh_dong = 'CRM_KY_TAI' AND doi_tuong_id = %s", (self.s["ky_id"],))
            st, out, hd = self.tai(login, self.s["ky_id"])
            self.assertEqual(st, 200, login)
            self.assertEqual((hashlib.sha256(out).hexdigest(), len(out)), (hashlib.sha256(self.s["raw"]).hexdigest(), len(self.s["raw"])))
            self.assertTrue(hd["content-type"].startswith("application/pdf"), hd)
            self.assertIn("attachment", hd.get("content-disposition", ""))
            self.assertIn("no-store", hd.get("cache-control", ""))
            self.assertNotIn("ban-da-ky", hd.get("content-disposition", ""))  # tên tải do máy chủ đặt (không tên gốc)
            self.assertEqual(self.q("SELECT count(*) FROM nhat_ky.su_kien WHERE hanh_dong = 'CRM_KY_TAI' AND doi_tuong_id = %s", (self.s["ky_id"],)), trc + 1)

    # ------------------------------------------------------------------ k07 (§7.7/§7.8): không IDOR/alias; thu hồi phạm vi chặn TRƯỚC replay
    def test_k07_idor_va_thu_hoi(self):
        for login in (CFO_B, KT_NO_CRM):
            st, out, _ = self.tai(login, self.s.get("ky_id") or str(uuid.uuid4()))
            self.assertEqual(st, 404, login)
            self.assertNotIn(b"sha256", out)
        st, out, _ = self.tai(BH, str(uuid.uuid4()))
        self.assertEqual(st, 404)
        st, out, _ = self.tai(BH, "../ky")
        self.assertIn(st, (400, 404))
        self.can_word()
        self.admin.execute("UPDATE master.crm_ky_pham_vi SET thu_hoi_luc = now(), thu_hoi_boi = 'TEST', thu_hoi_ly_do = 'TEST thu hồi' WHERE id = %s",
                           (self.s["pv"],))
        st, r = self.ky(BH, self.info(), self.s["raw"])  # cùng khóa đã FINAL: quyền hiện hành TRƯỚC biên nhận → 403, không trả kết quả cũ
        self.assertEqual((st, r.get("error")), (403, "CRM_KY_CHUA_CO_PHAM_VI"))
        self.assertNotIn("ky_id", r)
        d = self.get(BH, "giao-ket/ky/" + self.s["soan"])
        self.assertEqual((d["quyen"]["doc"], "ban_ky" in d, "can_cu" in d), (False, False, False))
        st, _, _ = self.tai(BH, self.s["ky_id"])
        self.assertEqual(st, 404)


if __name__ == "__main__":
    unittest.main()
