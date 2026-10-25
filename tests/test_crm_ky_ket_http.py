"""CRM-41-04A — kiểm HTTP thật G4 ký lần đầu trên LocalApp/LocalServer + PostgreSQL DEMO mới (CODE_ONLY: coder viết, CHƯA CHẠY — NOT_RUN_CODE_ONLY).

Chạy khi Root cấp KHO_PG_DSN_TEST lúc chạy (DSN chủ CSDL; không đọc .env/var, không hardcode credentials). DB MỚI `kho_test_crmky_*` migrate mặc định
(tối thiểu M0023), seed CRM DEMO + crm_g_demo (không M9, không bootstrap chung). Mẫu/báo giá/bản soạn/xuất dựng bằng LUỒNG DỊCH VỤ THẬT qua HTTP (mượn helper
của tests/test_crm_giao_ket_http.py — không sửa file đó). Phân công CRM_KY_KET + phạm vi ký do CHỦ CSDL khai (đúng vai trò quản trị của handoff —
không tự cấp qua HTTP, không suy từ người tạo). KHÔNG owner-forge PDF_DAT: `_co_word()` CHỈ là metadata probe (Word/guard có mặt), KHÔNG chứng
minh PDF_DAT. Nhánh ký dương chỉ chạy khi RUNTIME có bản xuất G3 thật PDF_DAT (hàng crm_gk_xuat PDF_DAT + bản soạn CHO_KY + tải bytes G3 qua HTTP
đúng hash/độ dài/chữ ký %PDF-); runtime PDF_LOI/PDF_CHUA_SAN_SANG/chưa có G3 thật → ghi rõ trạng thái thực đã chạy, ca dương skip = NOT_RUN.
Quyền đọc KT/KTT/CFO: vai + PN + module KHÔNG đủ — cần phân công hẹp CRM_KY_DOC + phạm vi tường minh do CHỦ CSDL khai (k03b: âm sai HĐ/khách/
dự án/thu hồi + đối chứng đúng phạm vi). Đây là kiểm PG THẬT + HTTP thật khi Root chạy; chưa chạy thì không có bằng chứng dương nào.
Ánh xạ tiêu chí handoff §7: 1 → k02 · 2 → k03/k05 · 3/4 → k05/k08 · 5 → k06 · 6 → k05 · 7 → k02/k03b/k04/k07 · 8 → k06/k07 · 9 → tests/crm_ky_ket_async.cjs ·
10 → test_crm_ky_ket.PrefixVaPhamVi. Không DROP/DELETE/cleanup — DB/role/thư mục giữ làm bằng chứng. Không chứng minh GUI/trình duyệt thật.
KY-DOCX (QD-20261025-27, M0035): lần xuất đúng revision có DOCX (PDF xuất tay/lỗi/đạt) → Chờ ký; ca dương k05/k06/k07 chạy trên bản xuất THẬT của
runtime (mặc định chỉ DOCX — PDF G3 NULL), không owner-forge. k08 (bản ký trùng byte PDF G3) vẫn chỉ chạy khi có PDF_DAT thật. k09: G5 bản sinh chỉ
DOCX → HOLD/việc giữ mở "cần kiểm tay" (không ý định/engine); trigger bản ký chặn sai DOCX/revision/PDF/DA_CU — bản xuất DA_CU/PDF_DAT giả chỉ chèn
trong giao dịch bị hoàn tác để kiểm guard ÂM (không phải bằng chứng PDF_DAT, không để lại hàng).
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


class _HoanTac(Exception):
    """Ném trong giao dịch để hoàn tác ca dương của trigger (không để lại hàng bản ký/bản xuất giả)."""


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

    def can_cho_ky(self):
        """QD-20261025-27 (M0035): ký trên DOCX — ca dương chạy khi k01 đã đưa bản soạn sang Chờ ký bằng lần xuất THẬT có DOCX (PDF có hay không)."""
        if not self.s.get("cho_ky"):
            self.skipTest(f"NOT_RUN: bản soạn chưa Chờ ký sau lần xuất ở k01 (trạng thái thực: {self.s.get('g3_trang_thai', 'chưa xuất')})")

    def can_word(self):
        """Chỉ cho ca cần PDF G3 thật (k08: bản ký trùng byte PDF G3)."""
        if not (self.co_word and self.s.get("pdf_dat")):
            self.skipTest("NOT_RUN: chưa có bản xuất G3 PDF_DAT THẬT ở runtime (trạng thái thực: "
                          f"{self.s.get('g3_trang_thai', 'chưa xuất')}; probe Word={self.co_word}) — không owner-forge PDF_DAT; ca dương G4 không tính đạt")

    def g3_dat_that(self, x, soan):
        """Bằng chứng RUNTIME (không phải probe metadata): bản xuất trả PDF_DAT + hàng crm_gk_xuat PDF_DAT có hash/độ dài + bản soạn CHO_KY +
        tải bytes G3 qua HTTP đúng hash/độ dài/chữ ký %PDF-. Trả bytes G3, hoặc None khi runtime PDF_LOI/PDF_CHUA_SAN_SANG/chưa có G3 thật.
        Hàng nói PDF_DAT mà bytes lệch → FAIL (lỗi thật), không skip."""
        row = self.admin.execute("SELECT trang_thai, pdf_sha256, pdf_len FROM master.crm_gk_xuat WHERE id = %s", (x["xuat_id"],)).fetchone()
        if x.get("trang_thai") != "PDF_DAT" or row is None or row[0] != "PDF_DAT" or not row[1] or not row[2]:
            return None
        if self.q("SELECT trang_thai FROM master.crm_hd_soan WHERE id = %s", (soan,)) != "CHO_KY":
            return None
        st, raw, _ = self.goi(f"/api/crm/giao-ket/tep/{x['xuat_id']}/pdf", cookie=self.sid(BH))
        self.assertEqual(st, 200, "bản xuất PDF_DAT nhưng không tải được PDF G3")
        self.assertIsInstance(raw, bytes)
        self.assertEqual((hashlib.sha256(raw).hexdigest(), len(raw)), (row[1], row[2]))
        self.assertTrue(raw.startswith(b"%PDF-"))
        return raw

    def tao_soan(self, tag):
        """Thêm một HĐ CRM CÙNG PN qua LUỒNG DỊCH VỤ THẬT (báo giá → chuyển soạn, cùng mẫu hiệu lực của k01). Không owner INSERT."""
        r = self.ok(BH, "bao-gia/luu", {"bao_gia_id": None, "expected_revision": None,
                                        "du_lieu": self.bao_gia(don_vi={"ma": f"LO-{tag}-{self.run_id}"}), "khoa": self.K("bg-" + tag)})
        return self.ok(BH, "bao-gia/chuyen", {"bao_gia_id": r["bao_gia_id"], "expected_revision": 1, "mau_phien_ban_id": self.s["pb"],
                                              "khoa": self.K("cv-" + tag)})

    def cap_phan_cong(self, login, hanh="CRM_KY_KET"):
        """Chủ CSDL khai phân công (CRM_KY_KET ký | CRM_KY_DOC đọc hẹp; cùng bảng/kỷ luật M0018) — không qua HTTP, không tự cấp."""
        return str(self.q("""INSERT INTO master.phan_cong_hanh_dong (nguoi_dung_id, phap_nhan_id, module, hanh_dong, loai_hinh_id, cap_boi)
                             SELECT n.id, s.phap_nhan_id, 'CRM', %s, s.loai_hinh_id, 'TEST:CRM-41-04A'
                             FROM master.nguoi_dung n, master.crm_hd_soan s WHERE n.dang_nhap = %s AND s.id = %s RETURNING id""",
                          (hanh, login, self.s["soan"])))

    def cap_pham_vi(self, pc, soan=None, khach_sha=None):
        """Chủ CSDL khai phạm vi: đúng HĐ/bản soạn + dự án của HĐ + digest khách dự thảo của revision hiện hành (HĐ chưa có mã đối tác).
        `khach_sha` chỉ dùng cho ca ÂM (digest khách không khớp revision)."""
        return str(self.q("""INSERT INTO master.crm_ky_pham_vi (phan_cong_id, phap_nhan_id, hop_dong_id, soan_id, du_an_id, khach_du_thao_sha256, cap_boi)
                             SELECT %s, s.phap_nhan_id, s.hop_dong_id, s.id, h.du_an_id,
                                    coalesce(%s::text, encode(sha256(convert_to((r.du_lieu -> 'bao_gia' -> 'khach' -> 'du_thao')::text, 'UTF8')), 'hex')),
                                    'TEST:CRM-41-04A'
                             FROM master.crm_hd_soan s JOIN master.hop_dong h ON h.id = s.hop_dong_id
                             JOIN master.crm_hd_soan_rev r ON r.soan_id = s.id AND r.revision = s.revision_hien_hanh
                             WHERE s.id = %s RETURNING id""", (pc, khach_sha, soan or self.s["soan"])))

    def thu_hoi(self, bang, id_):
        """Chủ CSDL thu hồi bằng dấu một lần (không xóa)."""
        self.admin.execute(f"UPDATE master.{bang} SET thu_hoi_luc = now(), thu_hoi_boi = 'TEST', thu_hoi_ly_do = 'TEST thu hồi' WHERE id = %s", (id_,))

    def sql_loi(self, ma, sql, params):
        with self.assertRaises(psycopg.Error) as cm:
            with self.admin.transaction():
                self.admin.execute(sql, params)
        self.assertIn(ma, str(cm.exception))

    def khong_doc(self, login):
        """Âm đọc: không chi tiết bản ký/căn cứ/hash cho phiên ngoài phạm vi đọc (200 chỉ trạng thái/quyền, hoặc 404 ẩn)."""
        st, d, _ = self.goi("/api/crm/giao-ket/ky/" + self.s["soan"], cookie=self.sid(login))
        self.assertIn(st, (200, 404), (login, d))
        if st == 200:
            self.assertFalse(d["quyen"]["doc"], login)
            for k in ("can_cu", "ban_ky", "lich_su"):
                self.assertNotIn(k, d, (login, k))
        self.assertNotIn("sha256", json.dumps(d))
        return st

    # ------------------------------------------------------------------ k01: dựng HĐ CRM qua luồng thật tới bản xuất G3
    def test_k01_dung_ban_soan_va_xuat_that(self):
        from kho_tri_thuc.ha_tang import pg_migrations as PM
        self.assertGreaterEqual(self.version, 23)
        self.assertEqual([i + 1 for i, m in enumerate(PM.PG_MIGRATIONS) if tuple(m) == tuple(PM.M0023_CRM_KY)], [23])
        ls = self.admin.execute("SELECT version, checksum FROM master.schema_migrations WHERE version <= %s ORDER BY version", (23,)).fetchall()
        self.assertEqual([tuple(x) for x in ls], [(i + 1, PM._hash(m)) for i, m in enumerate(PM.PG_MIGRATIONS[:23])])
        pb, _ = self.mau_hieu_luc("HD_KY_" + self.run_id, ngay(-2), "MAU V1")
        self.s["pb"] = pb
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
        self.s["g3_trang_thai"] = x["trang_thai"]  # ghi rõ trạng thái THỰC đã chạy (probe Word chỉ là metadata, không phải PDF_DAT)
        if not self.co_word:
            self.assertEqual(x["trang_thai"], "PDF_CHUA_SAN_SANG")
        else:
            self.assertIn(x["trang_thai"], {"PDF_DAT", "PDF_LOI", "PDF_CHUA_SAN_SANG"})
        # KY-DOCX (QD-20261025-27, M0035): lần xuất đúng revision có DOCX → Chờ ký, KHÔNG phụ thuộc PDF (PDF xuất tay/lỗi chỉ là tham khảo)
        self.assertEqual([i + 1 for i, m in enumerate(PM.PG_MIGRATIONS) if m is PM.M0035_KY_DOCX], [35])
        self.assertEqual(self.q("SELECT checksum FROM master.schema_migrations WHERE version = 35"), PM._hash(PM.M0035_KY_DOCX))
        self.assertTrue(x["docx_sha256"] and x["docx_len"] > 0, x)
        if x["trang_thai"] != "PDF_DAT":
            self.assertEqual((x["pdf_sha256"], x["pdf_len"]), (None, None), x)
        self.assertEqual(self.q("SELECT trang_thai FROM master.crm_hd_soan WHERE id = %s", (a["soan_id"],)), "CHO_KY")
        hd = self.admin.execute("SELECT trang_thai, crm_giao_ket FROM master.hop_dong WHERE id = %s", (a["hop_dong_id"],)).fetchone()
        self.assertEqual(tuple(hd), ("CHO_KY", "CHO_KY"))
        docx = self.goi(f"/api/crm/giao-ket/tep/{x['xuat_id']}/docx", cookie=self.sid(BH))[1]
        self.assertEqual((hashlib.sha256(docx).hexdigest(), len(docx)), (x["docx_sha256"], x["docx_len"]))  # bản DOCX để ký tải được, đúng hash
        self.s["cho_ky"] = True
        g3 = self.g3_dat_that(x, a["soan_id"])  # PDF G3 thật chỉ cho k08 (bản ký trùng byte PDF G3)
        self.s["pdf_dat"], self.s["g3_pdf"] = g3 is not None, g3

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
        # P1: KT/CFO cùng PN có module CRM + vai hiện hành nhưng CHƯA có phân công CRM_KY_DOC + phạm vi → KHÔNG đọc căn cứ/hash (fail closed),
        # không ký; không tự cấp (đối chứng đúng phạm vi ở k03b)
        d = self.get(KT, "giao-ket/ky/" + self.s["soan"])
        self.assertEqual((d["quyen"]["ky"], d["quyen"]["doc"]), (False, False))
        self.khong_doc(KT)
        self.assertEqual(self.khong_doc(CFO), 404)  # CFO không có nhóm CRM_SOAN và chưa có phạm vi đọc → ẩn
        st, r = self.ky(KT, self.info(khoa=self.K("ky-kt")), raw)
        self.assertIn((st, r.get("error")), {(403, "CRM_G_KHONG_CO_QUYEN"), (404, "CRM_G_KHONG_THAY")})
        self.get(BH, "giao-ket/ky/" + self.s["soan"] + "?x=1", status=400)  # query lạ bị từ chối
        # POST ký có query ngoài hợp đồng → 400 trước đọc body/phiên (không âm thầm bỏ qua)
        st, r, _ = self.goi("/api/crm/giao-ket/ky-ket?soan_id=" + self.s["soan"], cookie=self.sid(BH), raw=raw,
                            headers={"X-CRM-G-Info": quote(json.dumps(self.info(khoa=self.K("ky-q")))), "Content-Type": "application/pdf"})
        self.assertEqual((st, r.get("error")), (400, "CRM_G_YEU_CAU_SAI"))
        self.assertEqual((self.dem_ky(), self.kho_ky()), (trc, kho))  # không hàng/tệp nào sinh ra

    # ------------------------------------------------------------------ k03 (§7.2): phạm vi đủ nhưng căn cứ chưa đạt → 409, không ghi
    def test_k03_pham_vi_va_can_cu_chua_dat(self):
        self.s["pv"] = self.cap_pham_vi(self.s["pc"])
        d = self.get(BH, "giao-ket/ky/" + self.s["soan"])
        self.assertEqual(d["quyen"]["doc"], True)
        self.assertEqual(d["quyen"]["ky"], bool(self.s.get("cho_ky")))  # QD-27: Chờ ký trên DOCX + phạm vi → ký được (không cần PDF đạt)
        self.assertEqual(d["can_cu"]["xuat_id"], self.s["xuat"])
        self.assertEqual((d["can_cu"]["docx_sha256"], d["can_cu"]["pdf_sha256"], d["can_cu"]["trang_thai"]),
                         (self.s["x"]["docx_sha256"], self.s["x"]["pdf_sha256"], self.s["x"]["trang_thai"]))
        self.assertNotIn("_bao_gia", d["can_cu"])
        self.assertEqual(d["can_cu"]["tom_tat"], {"so_dong": 2, "tong_minor": "1000000000", "tien_te": "VND"})
        self.can_pdf()
        trc, kho = self.dem_ky(), self.kho_ky()
        raw = pdf_tong_hop(1, "BAN KY DEMO K03")
        st, r = self.ky(BH, self.info(expected_xuat_id=str(uuid.uuid4()), khoa=self.K("ky-xu")), raw)
        self.assertEqual((st, r.get("error")), (409, "CRM_KY_XUAT_CU"))
        # (QD-27: bản chỉ DOCX KHÔNG còn bị CRM_KY_XUAT_CHUA_DAT — ký dương ở k05; guard DA_CU/PDF lệch ở k09)
        self.assertEqual((self.dem_ky(), self.kho_ky()), (trc, kho))
        # phạm vi: chỉ thu hồi một lần, không xóa/sửa
        for sql in ("DELETE FROM master.crm_ky_pham_vi WHERE id = %s", "UPDATE master.crm_ky_pham_vi SET du_an_id = NULL WHERE id = %s"):
            with self.assertRaises(psycopg.Error) as cm:
                with self.admin.transaction():
                    self.admin.execute(sql, (self.s["pv"],))
            self.assertIn("CRM_KY_PHAM_VI_BAT_BIEN", str(cm.exception))

    # ------------------------------------------------------------------ k03b (§7.7, P1): đọc KT/CFO cần phân công hẹp CRM_KY_DOC + phạm vi
    def test_k03b_doc_kt_cfo_can_phan_cong_hep_va_pham_vi(self):
        """PG THẬT + HTTP thật. Âm: chỉ vai/PN/module; có phân công nhưng thiếu phạm vi; phạm vi sai HĐ cùng PN; sai khách; sai dự án/khách bị
        trigger chặn; thu hồi phân công. Đối chứng: đúng phân công + phạm vi tường minh → đọc được (vẫn KHÔNG ký)."""
        sid = self.s["soan"]
        trc, kho = self.dem_ky(), self.kho_ky()
        # (1) có phân công CRM_KY_DOC nhưng CHƯA có phạm vi chủ thể → không đọc
        pc_kt = self.cap_phan_cong(KT, "CRM_KY_DOC")
        self.khong_doc(KT)
        # (2) phạm vi gắn HĐ KHÁC cùng PN (sai chủ thể) → không đọc HĐ này
        a2 = self.tao_soan("khac")
        self.s["soan2"] = a2["soan_id"]
        self.cap_pham_vi(pc_kt, soan=a2["soan_id"])
        self.khong_doc(KT)
        # (3) phạm vi đúng HĐ nhưng khách (digest khách dự thảo) không khớp revision hiện hành → không đọc; thu hồi bằng dấu
        pv_sai = self.cap_pham_vi(pc_kt, khach_sha="0" * 64)
        self.khong_doc(KT)
        self.thu_hoi("crm_ky_pham_vi", pv_sai)
        # (4) sai dự án (dự án PN khác) / khách có mã khác / phân công không phải ký-đọc → trigger từ chối, không chèn
        chen = """INSERT INTO master.crm_ky_pham_vi (phan_cong_id, phap_nhan_id, hop_dong_id, soan_id, du_an_id, doi_tac_id, khach_du_thao_sha256, cap_boi)
                  SELECT %s, s.phap_nhan_id, s.hop_dong_id, s.id, %s::uuid, %s::uuid, %s::text, 'TEST:CRM-41-04A' FROM master.crm_hd_soan s WHERE s.id = %s"""
        du_an_hd = self.q("SELECT h.du_an_id FROM master.crm_hd_soan s JOIN master.hop_dong h ON h.id = s.hop_dong_id WHERE s.id = %s", (sid,))
        du_an_hd = None if du_an_hd is None else str(du_an_hd)
        self.sql_loi("CRM_KY_PHAM_VI_SAI", chen, (pc_kt, self.du_an("DA_NHA_DEMO"), None, "0" * 64, sid))  # dự án của PN khác
        if du_an_hd is not None:
            self.sql_loi("CRM_KY_PHAM_VI_SAI", chen, (pc_kt, None, None, "0" * 64, sid))  # thiếu dự án trong khi HĐ có dự án
        self.sql_loi("CRM_KY_PHAM_VI_SAI", chen, (pc_kt, du_an_hd, str(uuid.uuid4()), None, sid))  # mã khách khác (HĐ chưa có mã đối tác)
        pc_tai = str(self.q("""SELECT a.id FROM master.phan_cong_hanh_dong a JOIN master.nguoi_dung n ON n.id = a.nguoi_dung_id
                               WHERE n.dang_nhap = %s AND a.hanh_dong = 'CRM_MAU_TAI' AND a.thu_hoi_luc IS NULL""", (TAI,)))
        self.sql_loi("CRM_KY_PHAM_VI_SAI", chen, (pc_tai, du_an_hd, None, "0" * 64, sid))
        self.khong_doc(KT)
        # (5) ĐỐI CHỨNG: đúng phân công hẹp + phạm vi tường minh hiện hành → đọc được căn cứ; vẫn không ký (quyền ký tách riêng)
        self.s["pc_kt"], self.s["pv_kt"] = pc_kt, self.cap_pham_vi(pc_kt)
        d = self.get(KT, "giao-ket/ky/" + sid)
        self.assertEqual((d["quyen"]["doc"], d["quyen"]["ky"]), (True, False))
        self.assertEqual(d["can_cu"]["xuat_id"], self.s["xuat"])
        st, r = self.ky(KT, self.info(khoa=self.K("ky-kt-pv")), pdf_tong_hop(1, "BAN KY KT"))
        self.assertEqual((st, r.get("error")), (403, "CRM_G_KHONG_CO_QUYEN"))
        self.khong_doc(TAI)  # vai XEM có module CRM nhưng không phân công/phạm vi đọc → không chi tiết
        # (6) CFO: đúng phân công + phạm vi → đọc; THU HỒI PHÂN CÔNG (phạm vi còn) → fail closed ngay
        pc_cfo = self.cap_phan_cong(CFO, "CRM_KY_DOC")
        self.cap_pham_vi(pc_cfo)
        d = self.get(CFO, "giao-ket/ky/" + sid)
        self.assertEqual((d["quyen"]["doc"], d["quyen"]["ky"], d["can_cu"]["xuat_id"]), (True, False, self.s["xuat"]))
        self.thu_hoi("phan_cong_hanh_dong", pc_cfo)
        self.assertEqual(self.khong_doc(CFO), 404)
        self.assertEqual((self.dem_ky(), self.kho_ky()), (trc, kho))  # đọc/âm không sinh bản ký/tệp

    # ------------------------------------------------------------------ k04 (§7.2/§7.7): PDF hỏng/rỗng sau quyền; replay không lộ cho vai khác
    def test_k04_pdf_hong_va_rong(self):
        for raw, ma, st_ in ((b"", "CRM_KY_PDF_RONG", 400), (b"%PDF-1.4\n%%EOF\n", "CRM_KY_PDF_HONG", 400), (b"PK\x03\x04", "CRM_KY_PDF_HONG", 400)):
            st, r = self.ky(BH, self.info(khoa=self.K("ky-hong")), raw)
            self.assertIn((st, r.get("error")), {(st_, ma), (503, "CRM_KY_PDF_CHUA_KIEM_DUOC")}, raw[:10])  # thiếu parser: fail closed, không nhận

    # ------------------------------------------------------------------ k05 (§7.3/§7.4/§7.6): ký lần đầu trên bản xuất THẬT (QD-27: DOCX; PDF nếu có)
    def test_k05_ky_lan_dau_replay_va_g5(self):
        self.can_cho_ky()
        self.can_pdf()
        raw = pdf_tong_hop(2, "BAN KY DEMO K05")
        # (bản ký trùng byte PDF G3 là lần ký ĐẦU hợp lệ với vai trò bằng chứng riêng — kiểm ở k08 trên HĐ riêng, không ký A rồi gửi B ở đây)
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
        # QD-27 (M0035): bản ký gắn ĐÚNG bản xuất theo DOCX + input + engine + revision; PDF G3 = PDF bản xuất (NULL khi bản xuất chỉ DOCX)
        x = self.s["x"]
        row = self.admin.execute("""SELECT k.g3_docx_sha256, k.g3_docx_len, k.g3_pdf_sha256, k.g3_pdf_len, k.xuat_id, k.revision, k.g3_input_sha256 = g.input_sha256,
                                         k.g3_engine = g.engine FROM master.crm_hd_ky k JOIN master.crm_gk_xuat g ON g.id = k.xuat_id WHERE k.id = %s""",
                                 (r["ky_id"],)).fetchone()
        self.assertEqual((row[0], row[1], row[2], row[3], str(row[4]), row[5], row[6], row[7]),
                         (x["docx_sha256"], x["docx_len"], x["pdf_sha256"], x["pdf_len"], self.s["xuat"], self.s["rev"], True, True))
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
        self.can_cho_ky()
        if not self.s.get("ky_id"):
            self.skipTest("NOT_RUN: k05 chưa ký (thiếu bộ đọc PDF hoặc k05 lỗi) — không có bản ký để kiểm bất biến")
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
        # KT: thu hồi PHẠM VI đọc (phân công còn) → không còn căn cứ/bản ký/hash/tệp (fail closed, không cần ký dương)
        self.assertIn("pv_kt", self.s, "k03b chưa tạo phạm vi đọc KT — không có đối chứng")
        self.thu_hoi("crm_ky_pham_vi", self.s["pv_kt"])
        self.khong_doc(KT)
        if self.s.get("ky_id"):
            st, out, _ = self.tai(KT, self.s["ky_id"])
            self.assertEqual(st, 404)
            self.assertNotIn(b"sha256", out)
        self.can_cho_ky()
        if not self.s.get("ky_id"):
            self.skipTest("NOT_RUN: k05 chưa ký — không có bản ký để kiểm thu hồi trước replay")
        self.admin.execute("UPDATE master.crm_ky_pham_vi SET thu_hoi_luc = now(), thu_hoi_boi = 'TEST', thu_hoi_ly_do = 'TEST thu hồi' WHERE id = %s",
                           (self.s["pv"],))
        st, r = self.ky(BH, self.info(), self.s["raw"])  # cùng khóa đã FINAL: quyền hiện hành TRƯỚC biên nhận → 403, không trả kết quả cũ
        self.assertEqual((st, r.get("error")), (403, "CRM_KY_CHUA_CO_PHAM_VI"))
        self.assertNotIn("ky_id", r)
        d = self.get(BH, "giao-ket/ky/" + self.s["soan"])
        self.assertEqual((d["quyen"]["doc"], "ban_ky" in d, "can_cu" in d), (False, False, False))
        st, _, _ = self.tai(BH, self.s["ky_id"])
        self.assertEqual(st, 404)

    # ------------------------------------------------------------------ k08 (§7.3/§7.4): bản ký TRÙNG BYTE PDF G3 = lần ký ĐẦU riêng trên HĐ riêng
    def test_k08_ban_ky_trung_byte_g3_la_lan_ky_dau_rieng(self):
        """Hai bằng chứng (G3 bản sinh / bản ký) có vai trò/ID/hash/độ dài riêng; không buộc digest khác nhau. Chỉ chạy khi runtime có G3 PDF_DAT
        thật cho HĐ riêng này. Hash/bytes KHÔNG chứng minh chữ ký xác thực (G4 không OCR/so nội dung)."""
        self.can_word()
        a = self.tao_soan("trung")
        bg = dict(self.get(BH, "soan/" + a["soan_id"])["du_lieu"]["bao_gia"])
        bg["fx"] = None
        gt = {"so_hop_dong": "HĐ-DEMO-KY-0002", "ngay_ky": ngay(0), "ten_hien_thi_demo": "NGƯỜI MUA DEMO",
              "gia_tri_hop_dong": {"so_tien": "1000000000", "tien_te": "VND"}}
        self.ok(BH, "soan/luu", {"soan_id": a["soan_id"], "expected_revision": 1, "gia_tri_truong": gt, "bao_gia": bg, "khoa": self.K("so-trung")})
        x = self.ok(BH, "soan/xuat", {"soan_id": a["soan_id"], "expected_revision": 2, "khoa": self.K("x-trung")})
        g3 = self.g3_dat_that(x, a["soan_id"])
        if g3 is None:
            self.skipTest(f"NOT_RUN: HĐ thứ hai chưa có G3 PDF_DAT thật ở runtime (trạng thái thực {x.get('trang_thai')}) — không owner-forge")
        self.cap_pham_vi(self.s["pc"], soan=a["soan_id"])  # BH: phân công CRM_KY_KET sẵn có + phạm vi tường minh cho HĐ này
        info = {"soan_id": a["soan_id"], "expected_revision": 2, "expected_xuat_id": x["xuat_id"], "ten_tep": "ban-ky-trung.pdf", "ngay_ky": ngay(0),
                "co_sua": False, "khoa": self.K("ky-trung-1")}
        trc, sha = self.dem_ky(), hashlib.sha256(g3).hexdigest()
        st, r = self.ky(BH, info, g3)
        self.assertEqual(st, 200, r)
        self.assertEqual((r["trang_thai"], r["lap_lai"], r["xuat_id"]), ("DA_KY", False, x["xuat_id"]))
        self.assertEqual((r["ky_pdf_sha256"], r["ky_pdf_len"], r["g3_pdf_sha256"]), (sha, len(g3), sha))
        self.assertNotEqual(r["ky_id"], x["xuat_id"])  # ID bằng chứng ký riêng
        self.assertEqual(tuple(x_ - y for x_, y in zip(self.dem_ky(), trc)), (1, 1, 1))
        self.assertIn(sha, self.kho_ky())  # lưu ở kho bản ký riêng (giao-ket/ky), artifact G3 giữ nguyên ở giao-ket/tep
        row = self.admin.execute("SELECT ky_pdf_sha256, ky_pdf_len, g3_pdf_sha256, g3_pdf_len, xuat_id FROM master.crm_hd_ky WHERE id = %s",
                                 (r["ky_id"],)).fetchone()
        self.assertEqual((row[0], row[1], row[2], row[3], str(row[4])), (sha, len(g3), sha, len(g3), x["xuat_id"]))
        # khóa mới + cùng PDF/căn cứ/khai báo → ĐÚNG bản ký đã có (dedup chuẩn), 0 hàng mới; khác khai báo sau ký → Q-RETURN
        st, r2 = self.ky(BH, {**info, "khoa": self.K("ky-trung-2")}, g3)
        self.assertEqual((st, r2["ky_id"], r2["lap_lai"]), (200, r["ky_id"], True))
        st, e = self.ky(BH, {**info, "ngay_ky": ngay(-1), "khoa": self.K("ky-trung-3")}, g3)
        self.assertEqual((st, e.get("error")), (409, "CRM_KY_DA_KY"))
        self.assertEqual(tuple(x_ - y for x_, y in zip(self.dem_ky(), trc)), (1, 1, 1))
    # ------------------------------------------------------------------ KY-DOCX (QD-20261025-27, M0035): helper k09/k10
    _CHEN_KY_THO = """INSERT INTO master.crm_hd_ky (phap_nhan_id, hop_dong_id, soan_id, revision, soan_rev_id, xuat_id, g3_input_sha256, g3_docx_sha256,
            g3_docx_len, g3_pdf_sha256, g3_pdf_len, g3_engine, mau_phien_ban_id, anh_xa_id, kiem_id, raw_sha256, ban_do_sha256, danh_muc_ref, danh_muc_rev,
            danh_muc_digest, profile_phien_ban, profile_sha256, du_lieu_sha256, tom_tat, ky_pdf_sha256, ky_pdf_len, ky_so_trang, ten_tep, ngay_ky, co_sua,
            tao_boi)
        SELECT s.phap_nhan_id, s.hop_dong_id, s.id, coalesce(%(rev)s::integer, s.revision_hien_hanh), r.id, x.id, x.input_sha256,
               coalesce(%(docx)s::text, x.docx_sha256), x.docx_len,
               CASE WHEN %(pdf_xuat)s::boolean THEN x.pdf_sha256 ELSE %(pdf_sha)s::text END,
               CASE WHEN %(pdf_xuat)s::boolean THEN x.pdf_len ELSE %(pdf_len)s::bigint END,
               x.engine, r.mau_phien_ban_id, r.anh_xa_id, r.kiem_id, r.raw_sha256, r.ban_do_sha256, r.danh_muc_ref, r.danh_muc_rev, r.danh_muc_digest,
               r.profile_phien_ban, r.profile_sha256, r.du_lieu_sha256, '{}'::jsonb, %(ky)s::text, 1, 1, 'ban-ky-tho.pdf', current_date, false, 'TEST:KY-DOCX'
        FROM master.crm_hd_soan s JOIN master.crm_hd_soan_rev r ON r.soan_id = s.id AND r.revision = s.revision_hien_hanh
        JOIN master.crm_gk_xuat x ON x.id = %(xuat)s::uuid WHERE s.id = %(soan)s::uuid"""
    _XUAT_GIA = """INSERT INTO master.crm_gk_xuat (phap_nhan_id, loai, soan_id, revision, input_sha256, docx_sha256, docx_len, pdf_sha256, pdf_len, trang_thai,
                                                  engine, ly_do, kiem_pdf, tao_boi)
        SELECT phap_nhan_id, loai, soan_id, revision, input_sha256, docx_sha256, docx_len, %s::text, %s::bigint, %s::text, engine, 'TEST_KY_DOCX', '{}'::jsonb,
               'TEST:KY-DOCX' FROM master.crm_gk_xuat WHERE id = %s::uuid RETURNING id"""

    def xuat_soan(self, tag, so_hd):
        """HĐ CRM mới cùng PN qua LUỒNG THẬT (báo giá → chuyển → lưu revision 2 → xuất). Trả (soan_id, kết quả xuất, giá trị trường)."""
        a = self.tao_soan(tag)
        bg = dict(self.get(BH, "soan/" + a["soan_id"])["du_lieu"]["bao_gia"])
        bg["fx"] = None
        gt = {"so_hop_dong": so_hd, "ngay_ky": ngay(0), "ten_hien_thi_demo": "NGƯỜI MUA DEMO",
              "gia_tri_hop_dong": {"so_tien": "1000000000", "tien_te": "VND"}}
        self.ok(BH, "soan/luu", {"soan_id": a["soan_id"], "expected_revision": 1, "gia_tri_truong": gt, "bao_gia": bg, "khoa": self.K("so-" + tag)})
        x = self.ok(BH, "soan/xuat", {"soan_id": a["soan_id"], "expected_revision": 2, "khoa": self.K("x-" + tag)})
        return a["soan_id"], x, gt

    def chen_ky_tho(self, soan, xuat, *, rev=None, docx=None, pdf=None, xuat_gia=None):
        """CHỦ BẢNG chèn THẲNG crm_hd_ky (bỏ qua hàm lệnh) với căn cứ chép từ bản soạn/revision hiện hành/bản xuất; `pdf` = (sha, len) thay PDF
        của bản xuất; `xuat_gia` = (pdf_sha, pdf_len, trang_thai) → chèn TRƯỚC một bản xuất giả cùng revision (chỉ trong giao dịch này)."""
        if xuat_gia is not None:
            xuat = str(self.admin.execute(self._XUAT_GIA, (*xuat_gia, xuat)).fetchone()[0])
        self.admin.execute(self._CHEN_KY_THO, {"soan": soan, "xuat": xuat, "rev": rev, "docx": docx, "pdf_xuat": pdf is None,
                                                "pdf_sha": (pdf or (None, None))[0], "pdf_len": (pdf or (None, None))[1], "ky": "a" * 64})

    def ky_tho_bi_chan(self, soan, xuat, **sua):
        with self.assertRaises(psycopg.Error) as cm:
            with self.admin.transaction():
                self.chen_ky_tho(soan, xuat, **sua)
        self.assertIn("CRM_KY_G3_LECH", str(cm.exception), sua)

    def ky_tho_nhan(self, soan, xuat, **sua):
        """Đối chứng dương của trigger: chèn được rồi HOÀN TÁC (không để lại bản ký/bản xuất giả)."""
        with self.assertRaises(_HoanTac):
            with self.admin.transaction():
                self.chen_ky_tho(soan, xuat, **sua)
                self.assertEqual(self.q("SELECT count(*) FROM master.crm_hd_ky WHERE soan_id = %s", (soan,)), 1)
                raise _HoanTac

    # ------------------------------------------------------------------ k09 (QD-27): trigger bản ký gắn DOCX; PDF khớp khi có; DA_CU/sai bị chặn
    def test_k09_trigger_ban_ky_gan_docx_va_chan_sai(self):
        """PG THẬT. HĐ Chờ ký MỚI qua luồng thật (bản xuất thật của runtime). Guard crm_hd_ky_kiem khi chủ bảng chèn thẳng: đúng bản xuất (DOCX +
        input + engine + revision; PDF như bản xuất) → nhận (hoàn tác); sai DOCX / revision / PDF (có mà bản xuất không có, hoặc ngược lại, hoặc
        lệch) / bản xuất DA_CU → CRM_KY_G3_LECH. Bản xuất DA_CU/PDF_DAT giả chỉ sống trong giao dịch bị hoàn tác (guard ÂM, không phải bằng chứng
        PDF_DAT). Sau đó lưu revision mới → bản soạn về Đang soạn → ký trên bản xuất cũ bị 409."""
        self.can_cho_ky()
        sid, x, gt = self.xuat_soan("tho", "HĐ-DEMO-KY-0003")
        xid, co_pdf = x["xuat_id"], x["pdf_sha256"] is not None
        self.assertEqual(self.q("SELECT trang_thai FROM master.crm_hd_soan WHERE id = %s", (sid,)), "CHO_KY")
        self.ky_tho_nhan(sid, xid)  # đúng bản xuất thật (chỉ DOCX → PDF NULL)
        self.ky_tho_bi_chan(sid, xid, docx="f" * 64)
        self.ky_tho_bi_chan(sid, xid, rev=1)
        self.ky_tho_bi_chan(sid, xid, pdf=("c" * 64, 100) if not co_pdf else (None, None))
        self.ky_tho_bi_chan(sid, xid, xuat_gia=(None, None, "DA_CU"))
        self.ky_tho_bi_chan(sid, xid, xuat_gia=("c" * 64, 100, "PDF_DAT"), pdf=(None, None))  # bản xuất có PDF → bản ký phải có đúng PDF
        self.ky_tho_bi_chan(sid, xid, xuat_gia=("c" * 64, 100, "PDF_DAT"), pdf=("d" * 64, 100))
        self.ky_tho_nhan(sid, xid, xuat_gia=("c" * 64, 100, "PDF_DAT"), pdf=("c" * 64, 100))
        self.assertEqual(self.q("SELECT count(*) FROM master.crm_hd_ky WHERE soan_id = %s", (sid,)), 0)
        self.assertEqual(self.q("SELECT count(*) FROM master.crm_gk_xuat WHERE soan_id = %s", (sid,)), 1)  # bản xuất giả đã hoàn tác
        # lưu revision mới → Đang soạn; ký trên bản xuất của revision cũ bị chặn (không ký bản DOCX cũ)
        self.ok(BH, "soan/luu", {"soan_id": sid, "expected_revision": 2, "gia_tri_truong": gt, "khoa": self.K("so-tho-3")})
        self.assertEqual(self.q("SELECT trang_thai FROM master.crm_hd_soan WHERE id = %s", (sid,)), "SOAN_THAO")
        self.ky_tho_bi_chan(sid, xid)  # trigger: bản soạn không Chờ ký / revision đã đổi
        self.can_pdf()
        self.cap_pham_vi(self.s["pc"], soan=sid)
        trc = self.dem_ky()
        st, r = self.ky(BH, {"soan_id": sid, "expected_revision": 2, "expected_xuat_id": xid, "ten_tep": "ban-ky-cu.pdf", "ngay_ky": ngay(0),
                             "co_sua": False, "khoa": self.K("ky-tho-cu")}, pdf_tong_hop(1, "BAN KY DEMO CU"))
        self.assertEqual((st, r.get("error")), (409, "CRM_KY_TRANG_THAI"))
        self.assertEqual(self.dem_ky(), trc)

    # ------------------------------------------------------------------ k10 (QD-27): G5 bản sinh chỉ DOCX → cần kiểm tay, không tự kết luận khớp
    def test_k10_g5_ban_sinh_chi_docx_can_kiem_tay(self):
        """PG THẬT + HTTP thật. Ký khai Có trên bản xuất chỉ DOCX → việc G5 bắt buộc tạo trong giao dịch ký; xét G5 cho G6 = HOLD +
        G5_BAN_SINH_CHI_DOCX ở mọi chế độ (cả bản ký khai Không của k05); nhận việc / hàng đợi KHÔNG giữ lease, KHÔNG ý định/kết quả/engine;
        việc vẫn MỞ ở CHO_CAU_HINH với lý do cần kiểm tay (nghĩa vụ không đóng)."""
        self.can_cho_ky()
        self.can_pdf()
        sid, x, _ = self.xuat_soan("g5", "HĐ-DEMO-KY-0004")
        if x["pdf_sha256"] is not None:
            self.skipTest(f"NOT_RUN: runtime xuất có PDF ({x['trang_thai']}) — ca bản sinh chỉ DOCX không áp dụng")
        self.cap_pham_vi(self.s["pc"], soan=sid)
        st, r = self.ky(BH, {"soan_id": sid, "expected_revision": 2, "expected_xuat_id": x["xuat_id"], "ten_tep": "ban-ky-g5.pdf", "ngay_ky": ngay(0),
                             "co_sua": True, "mo_ta": "Sửa tay điều khoản DEMO", "khoa": self.K("ky-g5")}, pdf_tong_hop(1, "BAN KY DEMO G5"))
        self.assertEqual(st, 200, r)
        self.assertEqual((r["trang_thai"], r["g3_pdf_sha256"], r["g5"]), ("DA_KY", None, {"trang_thai": "PENDING", "ly_do": "BAT_BUOC_KHAI_CO"}))
        ky = r["ky_id"]
        cac_ky = [ky] + ([self.s["ky_id"]] if self.s.get("ky_id") and self.s["x"]["pdf_sha256"] is None else [])
        for k in cac_ky:
            for che_do in ("VAN_HANH", "SYNTHETIC_FIXTURE"):
                g = self.q("SELECT master.crm_kiem_g5_xet(%s::uuid, %s)", (k, che_do))
                self.assertEqual((g["che_do"], g["trang_thai"], g["chan"], g["lech"]), (che_do, "HOLD", [{"ma": "G5_BAN_SINH_CHI_DOCX"}], []), (k, che_do))
        viec = str(self.q("SELECT id FROM master.crm_g5_viec WHERE ky_id = %s AND loai = 'BAT_BUOC'", (ky,)))

        def dong():
            return tuple(self.admin.execute("SELECT trang_thai, ly_do, lease_boi, ket_qua_id FROM master.crm_g5_viec WHERE id = %s", (viec,)).fetchone())

        def su_kien():
            return self.q("""SELECT count(*) FROM master.crm_g5_su_kien WHERE viec_id = %s AND loai = 'CHO_CAU_HINH'
                             AND chi_tiet ->> 'ly_do' = 'G5_BAN_SINH_CHI_DOCX'""", (viec,))
        self.assertEqual(dong()[0], "CHO")
        self.assertEqual(self.q("SELECT master.crm_g5_nhan(%s::uuid, %s, %s)", (viec, "test-kydocx", 60)),
                         {"nhan": False, "ly_do": "G5_BAN_SINH_CHI_DOCX", "trang_thai": "CHO_CAU_HINH"})
        self.assertEqual(dong(), ("CHO_CAU_HINH", "G5_BAN_SINH_CHI_DOCX", None, None))
        self.assertEqual(su_kien(), 1)
        self.admin.execute("UPDATE master.crm_g5_viec SET thu_lai_sau = now() - interval '1 minute' WHERE id = %s", (viec,))  # đến hạn lại
        self.assertNotIn(viec, [str(m["viec_id"]) for m in self.q("SELECT master.crm_g5_hang_doi(50)")])  # không giao worker
        self.assertEqual(dong(), ("CHO_CAU_HINH", "G5_BAN_SINH_CHI_DOCX", None, None))
        self.assertEqual(su_kien(), 1)  # cùng lý do → không ghi sự kiện trùng
        for bang in ("crm_g5_y_dinh", "crm_g5_ket_qua"):
            self.assertEqual(self.q(f"SELECT count(*) FROM master.{bang} WHERE ky_id = %s", (ky,)), 0, bang)


if __name__ == "__main__":
    unittest.main()
