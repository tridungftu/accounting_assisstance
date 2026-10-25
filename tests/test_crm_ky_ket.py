"""CRM-41-04A — G4 ký lần đầu: kiểm tĩnh + thuần + service MOCK + (có điều kiện) guard CSDL THẬT. CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN_CODE_ONLY).

Phân loại (ghi rõ để không lẫn bằng chứng):
- `PrefixVaPhamVi`: TĨNH trên byte mã nguồn — prefix 1–22 (928356 B) nguyên, khối append M0023 riêng; crm_giao_ket.py nguyên byte.
- `M23Tinh`: TĨNH trên hằng SQL M0023 — thứ tự quyền → biên nhận → căn cứ; guard sau ký; G5 chỉ PENDING|NOT_SELECTED; không nghĩa vụ/hiệu lực/M1;
  đọc KT/KTT/CFO cần phân công hẹp CRM_KY_DOC + phạm vi tường minh (không còn nhánh PN+module+vai); không buộc signed_sha ≠ g3_sha.
- `RouteTinh`: TĨNH + handler GIẢ (thuần) — route/mã lỗi; POST ký từ chối query trước body/phiên/khóa.
- `ChuanHoa`, `KiemPdf`: THUẦN — dạng yêu cầu (co_sua bool thật; False hợp lệ) và parser PDF (bytes PDF tổng hợp; thiếu pypdfium2 → skip, KHÔNG PASS).
- `ServiceMock`: MOCK — CSDL/khóa giả ghi lại thứ tự lệnh; KHÔNG phải bằng chứng PostgreSQL. Kiểm quyền trước parse bytes, replay không đọc căn cứ/kho,
  kho G3 sai hash → không ghi, PDF bản ký ghi bất biến TRƯỚC hàm lệnh, digest yêu cầu không gồm khóa, tải kiểm quyền trước kho; bản ký trùng byte
  bản xuất là lần ký đầu riêng (mock). Fixture báo giá ở dạng producer đã chuẩn hóa (chuan_hoa_bao_gia), kỳ vọng tóm tắt độc lập.
- `GuardCsdlThat`: PostgreSQL THẬT (KHO_PG_DSN_TEST) — CHỈ âm/catalog (trigger/hàm/ràng buộc M0023) trên DB test mới; KHÔNG chứng minh dương phạm vi
  thực tế/đồng thời/producer. Thiếu DSN/psycopg → skip (NOT_RUN, KHÔNG PASS).
  Không tạo PDF_DAT giả qua chủ bảng (gate Word/G3 thật vẫn mở) — chỉ kiểm guard âm/ràng buộc không cần bản xuất đạt.
Dữ liệu tổng hợp; không M9, không dữ liệu/cấu hình thật, không xóa tệp.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.ha_tang.primitives import DataError, canonical_json
from kho_tri_thuc.k2 import crm_ky_ket as KY
from kho_tri_thuc.k2.crm_giao_ket import chuan_hoa_bao_gia, tinh_bao_gia
from test_crm_giao_ket import bao_gia

# Snapshot kỳ vọng ĐỘC LẬP của fixture G2 tổng hợp (tong 1.000.000.000 VND, scale 0; lịch 30%/70% = 2 dòng) — không lấy từ hàm đang kiểm.
TOM_TAT_KY_VONG = {"so_dong": 2, "tong_minor": "1000000000", "tien_te": "VND"}

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
PREFIX_BYTES = 928_356  # handoff CRM-41-04A §1: toàn pg_migrations.py migration 1–22
PREFIX_SHA256 = "225cc40f14670e8428bf8afcc58318c04c15707bdddffa31242067f20199cce2"
GK_SHA256 = "7704a96cc84d21ef60850394a37decc869295b5728eaa8d6720d1116add2f1e5"  # k2/crm_giao_ket.py sau BG-1c (25/10/2026, QD-20261025-01…04 — VND tiền chính, sửa có chủ đích); trước đó BG-1a vòng 2 53dae579…, chốt cũ của G4 là c155c533…
M23 = "\n".join(PM.M0023_CRM_KY)
M23_MOI = "\n".join(s for s in PM.M0023_CRM_KY if s is not PM._KY_XG)  # phần mới của M0023 (bỏ định nghĩa M0021 tạo lại một dòng)
SO, XU = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def pdf_tong_hop(so_trang: int = 1, chu: str = "BAN KY DEMO") -> bytes:
    """PDF tối thiểu hợp lệ (xref đúng offset) — dữ liệu tổng hợp, không phải tài liệu thật."""
    objs = ["<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [" + " ".join(f"{3 + i} 0 R" for i in range(so_trang)) + f"] /Count {so_trang} >>"]
    for _ in range(so_trang):
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents {3 + so_trang} 0 R >>")
    luong = f"BT /F1 12 Tf 20 100 Td ({chu}) Tj ET".encode("latin-1")
    out, off = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, start=1):
        off.append(len(out)); out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    off.append(len(out)); n = len(objs) + 1
    out += f"{n} 0 obj\n<< /Length {len(luong)} >>\nstream\n".encode("latin-1") + luong + b"\nendstream\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {n + 1}\n0000000000 65535 f \n".encode("latin-1") + "".join(f"{o:010d} 00000 n \n" for o in off).encode("latin-1")
    out += f"trailer\n<< /Size {n + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("latin-1")
    return bytes(out)


def yc(**sua):
    d = {"soan_id": SO, "expected_revision": 2, "expected_xuat_id": XU, "ten_tep": "ban-ky.pdf", "ngay_ky": "2026-10-20", "co_sua": False,
         "mo_ta": None, "nguoi_ky_khach": None, "khoa": "crmgk-ky-1"}
    d.update(sua)
    return d


# ====================================================================== TĨNH
class PrefixVaPhamVi(unittest.TestCase):
    def test_928356_byte_dau_nguyen_chi_append_m0023(self):
        raw = (SRC / "ha_tang" / "pg_migrations.py").read_bytes()
        self.assertEqual(hashlib.sha256(raw[:PREFIX_BYTES]).hexdigest(), PREFIX_SHA256)
        duoi = raw[PREFIX_BYTES:].decode("utf-8")
        self.assertIn("M0023_CRM_KY = (", duoi)
        # M4-02C và các gói sau nối thêm sau M23; kiểm riêng khối M23, giữ pin 1–22.
        cuoi = "PG_MIGRATIONS = (*PG_MIGRATIONS, M0023_CRM_KY)\nPG_SCHEMA_VERSION = len(PG_MIGRATIONS)"
        self.assertEqual(duoi.count(cuoi), 1)
        duoi = duoi.split("\n# ---------------------------------------------------------------------------\n# 0024", 1)[0]
        self.assertTrue(duoi.rstrip().endswith("PG_MIGRATIONS = (*PG_MIGRATIONS, M0023_CRM_KY)\nPG_SCHEMA_VERSION = len(PG_MIGRATIONS)"), duoi[-200:])
        self.assertNotIn("M0024", duoi)
        self.assertGreaterEqual(len(PM.PG_MIGRATIONS), 23)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        self.assertIs(PM.PG_MIGRATIONS[22], PM.M0023_CRM_KY)
        self.assertIs(PM.PG_MIGRATIONS[21], PM.M0022_M4_CHUNG_TU)
        self.assertIs(PM.PG_MIGRATIONS[20], PM.M0021_CRM_G2G3)

    def test_crm_giao_ket_nguyen_byte(self):
        raw = (SRC / "k2" / "crm_giao_ket.py").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), GK_SHA256)

    def test_crm_gk_xuat_ghi_tao_lai_dung_mot_thay_doi(self):
        goc = next(s for s in PM.M0021_CRM_G2G3 if "FUNCTION master.crm_gk_xuat_ghi(" in s)
        moi = next(s for s in PM.M0023_CRM_KY if "FUNCTION master.crm_gk_xuat_ghi(" in s)
        a, b = goc.splitlines(), moi.splitlines()
        self.assertEqual(len(a), len(b))
        khac = [(x, y) for x, y in zip(a, b) if x != y]
        self.assertEqual(len(khac), 1, khac)
        self.assertIn("OR s.trang_thai = 'DA_KY'", khac[0][1])

    def test_m4_m9_khong_bi_cham(self):
        self.assertIn(PM._KY_XG, PM.M0023_CRM_KY)
        for cam in ("m4.", "sql_review", "M0019", "M0020", "khoan_vay", "hop_dong_phien_ban", "lich_thu", "nghia_vu", "junsky"):
            self.assertNotIn(cam, M23_MOI.lower(), cam)


class M23Tinh(unittest.TestCase):
    def _ham(self, ten):
        return next(s for s in PM.M0023_CRM_KY if f"FUNCTION master.{ten}(" in s)

    def test_ky_ket_thu_tu_quyen_bien_nhan_can_cu(self):
        f = self._ham("crm_ky_ket")
        thu_tu = ["crm_g_ghim_quyen", "crm_ky_pham_vi b", "crm_ky_dich(p_soan)", "crm_g_bn_tra", "CRM_KY_KHAI_SAI", "CRM_KY_NGAY_SAI",
                  "FOR UPDATE", "CRM_KY_DA_KY", "CRM_KY_TRANG_THAI", "CRM_GK_REVISION_CU", "CRM_KY_XUAT_CU", "CRM_KY_XUAT_CHUA_DAT", "CRM_KY_G3_LECH",
                  "CRM_GK_MAU_LECH_GHIM", "INSERT INTO master.crm_hd_ky ", "INSERT INTO master.crm_hd_ky_g5",
                  "UPDATE master.crm_hd_soan SET trang_thai = 'DA_KY'", "crm_g_bn_ghi"]
        vt = [f.index(x) for x in thu_tu]
        self.assertEqual(vt, sorted(vt), list(zip(thu_tu, vt)))
        self.assertIn("ORDER BY tao_luc DESC, id DESC LIMIT 1", f)  # bản xuất MỚI NHẤT của revision; không chọn ngầm bản khác

    def test_hai_bang_chung_doc_lap_khong_buoc_digest_khac(self):
        """Bỏ ràng buộc phổ quát signed_sha ≠ g3_sha (lệnh + CHECK bảng); GIỮ kiểm hash/độ dài, CAS bản xuất mới nhất, một bản ký/HĐ,
        cùng PDF + cùng căn cứ/khai báo → cùng bản ký; khác → CRM_KY_DA_KY (Q-RETURN)."""
        f = self._ham("crm_ky_ket")
        bang = next(s for s in PM.M0023_CRM_KY if "CREATE TABLE master.crm_hd_ky (" in s)
        for cam in ("CRM_KY_PDF_LA_BAN_XUAT", "p_ky_sha = xm.pdf_sha256", "ky_pdf_sha256 <> g3_pdf_sha256"):
            self.assertNotIn(cam, f + bang, cam)
        self.assertNotIn("CRM_KY_PDF_LA_BAN_XUAT", M23)
        for can in ("ky_pdf_sha256 text NOT NULL CHECK (ky_pdf_sha256 ~ '^[0-9a-f]{64}$')", "ky_pdf_len bigint NOT NULL CHECK (ky_pdf_len > 0)",
                    "g3_pdf_sha256 text NOT NULL CHECK (g3_pdf_sha256 ~ '^[0-9a-f]{64}$')", "g3_pdf_len bigint NOT NULL CHECK (g3_pdf_len > 0)",
                    "UNIQUE (hop_dong_id),", "UNIQUE (hop_dong_id, ky_pdf_sha256),"):
            self.assertIn(can, bang, can)
        for can in ("p_ky_sha !~ '^[0-9a-f]{64}$'", "p_ky_len <= 0", "xm.id <> p_xuat", "xm.pdf_sha256 <> p_g3_pdf_sha", "xm.pdf_len <> p_g3_pdf_len",
                    "k.ky_pdf_sha256 = p_ky_sha AND k.ky_pdf_len = p_ky_len AND k.xuat_id = p_xuat"):
            self.assertIn(can, f, can)
        # cùng PDF/khóa mới → đúng bản ký đã có (k.id), không hàng mới; mọi khác biệt sau ký → CRM_KY_DA_KY
        self.assertLess(f.index("master.crm_ky_kq(k.id)"), f.index("CRM_KY_DA_KY"))
        self.assertLess(f.index("CRM_KY_DA_KY"), f.index("INSERT INTO master.crm_hd_ky "))

    def test_tra_va_doc_tep_quyen_truoc(self):
        tra = self._ham("crm_ky_tra")
        self.assertLess(tra.index("crm_ky_dich(p_soan)"), tra.index("crm_g_bn_tra"))
        tep = self._ham("crm_ky_tep")
        self.assertLess(tep.index("crm_ky_doc_duoc"), tep.index("INSERT INTO nhat_ky.su_kien"))
        self.assertLess(tep.index("INSERT INTO nhat_ky.su_kien"), tep.index("'sha256', k.ky_pdf_sha256"))
        doc = self._ham("crm_ky_doc")
        self.assertLess(doc.index("IF NOT doc THEN"), doc.index("'can_cu'"))
        self.assertLess(doc.index("IF NOT doc THEN"), doc.index("'ban_ky'"))

    def test_pham_vi_khong_suy_tu_nguoi_tao(self):
        hd = self._ham("crm_ky_pham_vi_hd")  # predicate dùng chung: phân công hiện hành + phạm vi tường minh + vai + dự án/khách hiện hành
        for can in ("crm_ky_pham_vi b", "b.thu_hoi_luc IS NULL", "a.thu_hoi_luc IS NULL", "master.phan_cong_hanh_dong a", "a.hanh_dong = p_hanh",
                    "p_hanh IN ('CRM_KY_KET', 'CRM_KY_DOC')", "ktt_co_vai(s.phap_nhan_id, p_vai, NULL)", "ktt.nguoi_dung_id", "HOAT_DONG",
                    "ktt_duoc(s.phap_nhan_id, 'CRM')", "b.du_an_id IS NOT DISTINCT FROM h.du_an_id", "b.doi_tac_id = h.doi_tac_id",
                    "khach_du_thao_sha256", "b.soan_id = s.id AND b.hop_dong_id = h.id AND b.phap_nhan_id = s.phap_nhan_id"):
            self.assertIn(can, hd, can)
        for cam in ("tao_boi", "cap_boi ="):
            self.assertNotIn(cam, hd)
        pv = self._ham("crm_ky_pham_vi_duoc")  # quyền KÝ: chỉ BAN_HANG + CRM_KY_KET
        self.assertIn("master.crm_ky_pham_vi_hd(p_soan, 'CRM_KY_KET', ARRAY['BAN_HANG'])", pv)
        self.assertNotIn("CRM_KY_DOC", pv)
        self.assertNotIn("KE_TOAN", pv)
        kiem = self._ham("crm_ky_pham_vi_kiem")
        self.assertIn("la_chu_bang", kiem)
        self.assertIn("CRM_KY_PHAM_VI_SAI", kiem)
        self.assertIn("a.hanh_dong NOT IN ('CRM_KY_KET', 'CRM_KY_DOC')", kiem)  # phạm vi chỉ gắn phân công ký hoặc đọc hẹp; không action khác

    def test_doc_kt_cfo_can_phan_cong_hep_va_pham_vi(self):
        """P1: KT/KTT/CFO đọc bản ký/căn cứ/hash/tệp KHÔNG còn chỉ nhờ PN + module + vai; cần phân công hẹp CRM_KY_DOC + phạm vi tường minh."""
        doc = self._ham("crm_ky_doc_duoc")
        self.assertIn("master.crm_ky_pham_vi_hd(s.id, 'CRM_KY_DOC', ARRAY['KE_TOAN','KE_TOAN_TRUONG','CFO'])", doc)
        self.assertIn("master.crm_ky_pham_vi_duoc(s.id)", doc)
        self.assertNotIn("ktt_co_vai", doc)  # không còn nhánh vai rộng không phạm vi
        self.assertNotIn("ktt_hanh_dong_duoc", doc)  # phân công không phạm vi chủ thể KHÔNG đủ
        # mọi lối đọc chi tiết/tệp đều qua crm_ky_doc_duoc (fail closed trước căn cứ/hash/bản ký/tệp)
        ky_doc, tep = self._ham("crm_ky_doc"), self._ham("crm_ky_tep")
        self.assertIn("doc := master.crm_ky_doc_duoc(s.id);", ky_doc)
        self.assertIn("NOT master.crm_ky_doc_duoc(k.soan_id)", tep)
        self.assertLess(tep.index("crm_g_ghim_quyen(k.phap_nhan_id)"), tep.index("NOT master.crm_ky_doc_duoc(k.soan_id)"))
        self.assertLess(tep.index("FOR SHARE"), tep.index("NOT master.crm_ky_doc_duoc(k.soan_id)"))
        # không vai/master/IAM song song, không tự cấp DEMO
        for cam in ("CREATE TABLE master.vai", "CREATE ROLE", "INSERT INTO master.phan_cong_hanh_dong", "INSERT INTO master.crm_ky_pham_vi",
                    "INSERT INTO master.phan_quyen", "GRANT "):
            self.assertNotIn(cam, M23_MOI, cam)
        self.assertEqual(KY.HANH_DOC, "CRM_KY_DOC")

    def test_guard_sau_ky_backend(self):
        for ten in ("crm_hd_soan_ky_khoa", "hop_dong_gk_ky_khoa", "crm_hd_soan_rev_ky_khoa", "crm_gk_lan_ky_khoa", "crm_gk_xuat_ky_khoa"):
            self.assertIn("CRM_GK_DA_KY", self._ham(ten))
        for trig in ("BEFORE UPDATE ON master.crm_hd_soan ", "BEFORE UPDATE ON master.hop_dong ", "BEFORE INSERT ON master.crm_hd_soan_rev ",
                     "BEFORE INSERT ON master.crm_gk_lan ", "BEFORE INSERT ON master.crm_gk_xuat ",
                     "crm_hd_ky_bat_bien BEFORE INSERT OR UPDATE OR DELETE", "crm_hd_ky_g5_bat_bien BEFORE INSERT OR UPDATE OR DELETE"):
            self.assertIn(trig, M23)

    def test_g5_chi_khoi_tao_trung_thuc(self):
        self.assertIn("CHECK (trang_thai IN ('PENDING','NOT_SELECTED'))", M23)
        self.assertIn("CASE WHEN p_co_sua THEN 'PENDING' ELSE 'NOT_SELECTED' END", M23)
        for cam in ("'MATCH'", "MISMATCH", "random()", "worker", "Đã chuyển kế toán kiểm"):
            self.assertNotIn(cam, M23_MOI)

    def test_ngay_ky_khong_la_hieu_luc(self):
        f = self._ham("crm_ky_ket")
        self.assertIn("UPDATE master.hop_dong SET trang_thai = 'DA_KY', crm_giao_ket = 'DA_KY' WHERE id = s.hop_dong_id;", f)
        self.assertEqual(f.count("UPDATE master.hop_dong "), 1)  # HĐ: chỉ trạng thái; ngày ký nằm ở bản ký, không thành ngày/phiên bản hiệu lực
        for cam in ("HIEU_LUC", "ngay_hieu_luc", "phien_ban_hien_hanh", "hop_dong_phien_ban", "lich_thu"):
            self.assertNotIn(cam, f)

    def test_quyen_bang_ham(self):
        self.assertIn("REVOKE ALL ON master.crm_ky_pham_vi, master.crm_hd_ky, master.crm_hd_ky_g5 FROM PUBLIC", M23)
        for t in KY_BANG:
            self.assertIn(f"ALTER TABLE master.{t} ENABLE ROW LEVEL SECURITY", M23)
        self.assertIn("master.crm_ky_ket(text, text, uuid, integer, uuid, text, text, bigint, text, bigint, integer, text, date, boolean, text, text, jsonb)", M23)


KY_BANG = ("crm_ky_pham_vi", "crm_hd_ky", "crm_hd_ky_g5")


class RouteTinh(unittest.TestCase):
    def test_route_trong_prefix_giao_ket_va_ma_loi(self):
        from kho_tri_thuc.giao_dien import crm_g as G
        for p in ("/api/crm/giao-ket/ky/" + SO, "/api/crm/giao-ket/ban-ky/" + SO + "/tep", "/api/crm/giao-ket/ky-ket"):
            self.assertTrue(G.la_route(True, p) and G.la_route(False, p))
        self.assertEqual(G.TRUONG_KY, {"soan_id", "expected_revision", "expected_xuat_id", "ten_tep", "ngay_ky", "co_sua", "mo_ta", "nguoi_ky_khach", "khoa"})
        self.assertFalse(G.TRUONG_KY & G.KHONG_NHAN)
        for m in ("CRM_KY_XUAT_CU", "CRM_KY_DA_KY", "CRM_GK_DA_KY", "CRM_KY_XUAT_CHUA_DAT", "CRM_KY_G3_LECH", "CRM_KY_TRANG_THAI"):
            self.assertIn(m, G.MA_409_KY)
        self.assertNotIn("CRM_KY_PDF_LA_BAN_XUAT", G.MA_409_KY)  # không còn ràng buộc phổ quát signed ≠ G3
        self.assertIn("CRM_KY_CHUA_CO_PHAM_VI", G.MA_403_KY)
        self.assertIn("CRM_KY_TEP_QUA_LON", G.MA_413_KY)
        src = (SRC / "giao_dien" / "crm_g.py").read_text(encoding="utf-8")
        ky = src[src.index("def _ky_ket("):src.index("def _lenh_gk(")]
        self.assertLess(ky.index("_khong_query(h, query)"), ky.index("h.headers.get(\"X-CRM-G-Info\""))
        self.assertLess(ky.index("_khong_query(h, query)"), ky.index("h.body(MAX_FILE_SIZE)"))
        self.assertLess(ky.index("_than(info, TRUONG_KY)"), ky.index("h.body(MAX_FILE_SIZE)"))
        self.assertLess(ky.index("ky.kiem_quyen"), ky.index("KY.kiem_pdf_ky(raw)"))
        self.assertLess(ky.index("KY.kiem_pdf_ky(raw)"), ky.index("ky.ky(me, raw"))
        # parse PDF NGOÀI mutation lock: dòng parse không thụt trong khối with
        dong = next(x for x in ky.splitlines() if "KY.kiem_pdf_ky(raw)" in x)
        self.assertTrue(dong.startswith("    so_trang"), dong)

    def test_post_ky_ket_tu_choi_query_truoc_doc_body(self):
        """THUẦN (handler giả, không máy chủ/CSDL): POST ký có query ngoài hợp đồng → 400 CRM_G_YEU_CAU_SAI, không đọc body, không mutation lock."""
        from kho_tri_thuc.giao_dien import crm_g as G

        class _H:
            def __init__(self, path):
                self.path, self.gui = path, []
                self.headers = {"X-CRM-G-Info": "", "Content-Type": "application/pdf"}

            def body(self, n):
                raise AssertionError("đọc body trước khi từ chối query")

            def crm_sid(self):
                raise AssertionError("tra phiên trước khi từ chối query")

            def send_content(self, st, payload, *a):
                self.gui.append((st, payload))

        app = mock.Mock()
        app.mutation_lock.__enter__ = mock.Mock(side_effect=AssertionError("mutation lock trước khi từ chối query"))
        for path, query in (("/api/crm/giao-ket/ky-ket?soan_id=" + SO, {"soan_id": [SO]}), ("/api/crm/giao-ket/ky-ket?actor=x", {"actor": ["x"]}),
                            ("/api/crm/giao-ket/ky-ket?x", {}), ("/api/crm/giao-ket/ky-ket?x=", {})):
            h = _H(path)
            G.dieu_huong(h, app, True, "/api/crm/giao-ket/ky-ket", query)
            self.assertEqual(len(h.gui), 1, path)
            self.assertEqual((h.gui[0][0], h.gui[0][1]["error"]), (400, "CRM_G_YEU_CAU_SAI"), path)
        for path in ("/api/crm/giao-ket/ky/" + SO + "?x", "/api/crm/giao-ket/ban-ky/" + SO + "/tep?x="):
            h = _H(path)
            G.dieu_huong(h, app, False, path.split("?", 1)[0], {})
            self.assertEqual((h.gui[0][0], h.gui[0][1]["error"]), (400, "CRM_G_YEU_CAU_SAI"), path)

    def test_ui_khong_noi_gia(self):
        js = (SRC / "giao_dien" / "assets" / "crm_g.js").read_text(encoding="utf-8")
        self.assertNotIn("Ký kết (G4) chưa nối", js)
        self.assertNotIn("Đã chuyển kế toán kiểm", js)
        for can in ("/api/crm/giao-ket/ky-ket", "/api/crm/giao-ket/ky/", "/api/crm/giao-ket/ban-ky/", "Đã ký — chờ kế toán kiểm", '"X-CRM-G-Info": y.enc'):
            self.assertIn(can, js)
        for cam in ("innerHTML", "outerHTML", "insertAdjacentHTML", "eval(", "new Function", "document.write"):
            self.assertNotIn(cam, js)
        yd = js[js.index("function kyYDinh("):js.index("async function guiKy(")]
        ma_yd = "\n".join(x.split("//", 1)[0] for x in yd.splitlines())  # bỏ chú thích
        self.assertNotIn("await", ma_yd)  # giữ chỗ ý định đồng bộ
        self.assertIn("kyYD.set(k, y)", yd)
        gk = js[js.index("async function guiKy("):js.index("function veKyChuaRo(")]
        self.assertNotIn("taoKhoa(", gk)  # gửi lại dùng ĐÚNG khóa/header gốc
        self.assertLess(gk.index("y.dangGui = true"), gk.index("await"))


# ====================================================================== THUẦN
class ChuanHoa(unittest.TestCase):
    def _loi(self, ma, **sua):
        with self.assertRaises(DataError) as cm:
            KY.chuan_hoa(**yc(**sua))
        self.assertEqual(cm.exception.code, ma)

    def test_false_la_khai_khong_hop_le(self):
        y = KY.chuan_hoa(**yc())
        self.assertIs(y["co_sua"], False)
        self.assertIsNone(y["mo_ta"])

    def test_co_kem_mo_ta(self):
        y = KY.chuan_hoa(**yc(co_sua=True, mo_ta="Sửa điều 5 bằng tay"))
        self.assertIs(y["co_sua"], True)

    def test_co_sua_thieu_null_chuoi_so(self):
        for v in (None, "true", "false", "", 0, 1, "Có"):
            self._loi("CRM_KY_KHAI_SAI", co_sua=v)

    def test_mo_ta_theo_khai_bao(self):
        self._loi("CRM_KY_KHAI_SAI", co_sua=True, mo_ta=None)
        self._loi("CRM_KY_KHAI_SAI", co_sua=True, mo_ta="   ")
        self._loi("CRM_KY_KHAI_SAI", co_sua=False, mo_ta="có mô tả")
        self._loi("CRM_G_YEU_CAU_SAI", co_sua=True, mo_ta="x" * 2001)

    def test_ngay_ten_revision_uuid_khoa(self):
        for v in (None, "", "20-10-2026", "2026-02-30", 20261020):
            self._loi("CRM_G_YEU_CAU_SAI", ngay_ky=v)
        for v in ("a/b.pdf", "..\\x.pdf", "ban.docx", "ban.pdf ", "x:y.pdf", ".pdf", None):
            self._loi("CRM_G_YEU_CAU_SAI", ten_tep=v)
        for v in (0, -1, "2", True, 2.0, None):
            self._loi("CRM_G_YEU_CAU_SAI", expected_revision=v)
        self._loi("CRM_G_YEU_CAU_SAI", soan_id="khong-uuid")
        self._loi("CRM_G_YEU_CAU_SAI", expected_xuat_id=None)
        self._loi("CRM_G_KHOA", khoa="khóa có dấu")
        self._loi("CRM_G_YEU_CAU_SAI", nguoi_ky_khach="dòng\nhai")


class KiemPdf(unittest.TestCase):
    def test_rong_qua_lon_khong_phai_pdf(self):
        for raw, ma in ((b"", "CRM_KY_PDF_RONG"), (None, "CRM_KY_PDF_RONG"), (b"PK\x03\x04docx", "CRM_KY_PDF_HONG"),
                        (b"x" * (KY.TEP_KY_TOI_DA + 1), "CRM_KY_TEP_QUA_LON")):
            with self.assertRaises(DataError) as cm:
                KY.kiem_pdf_ky(raw)
            self.assertEqual(cm.exception.code, ma)

    def test_thieu_parser_fail_closed(self):
        with mock.patch.dict("sys.modules", {"pypdfium2": None}):
            with self.assertRaises(DataError) as cm:
                KY.kiem_pdf_ky(pdf_tong_hop())
        self.assertEqual(cm.exception.code, "CRM_KY_PDF_CHUA_KIEM_DUOC")

    def test_pdf_that_va_hong(self):
        try:
            import pypdfium2  # noqa: F401
        except ImportError:
            self.skipTest("thiếu pypdfium2 — NOT_RUN, không tính đạt")
        self.assertEqual(KY.kiem_pdf_ky(pdf_tong_hop(2)), 2)
        for hong in (b"%PDF-1.4\n%%EOF\n", pdf_tong_hop()[:60], b"%PDF-1.7\n" + os.urandom(512)):
            with self.assertRaises(DataError) as cm:
                KY.kiem_pdf_ky(hong)
            self.assertEqual(cm.exception.code, "CRM_KY_PDF_HONG")


# ====================================================================== MOCK service (KHÔNG phải PostgreSQL)
class _Cur:
    def __init__(self, mau):
        self.mau = mau

    def execute(self, sql, params=()):
        self.mau.nhat.append(("SQL", " ".join(sql.split())[:60], params))
        tra = self.mau.tra_loi(sql, params)
        return mock.Mock(fetchone=lambda: tra)


class _MauGia:
    """CrmMauK2 giả: danh tính + giao dịch + _mot + mau_ghim_trong — ghi lại thứ tự. MOCK."""

    def __init__(self, kho: Path):
        self.root = kho
        self.nhat: list = []
        self.tra_ky = None          # crm_ky_tra(khoa,...) → None | {lap_lai, ket_qua}
        self.loi_quyen = None       # DataError khi preflight quyền
        self.xuat = None            # hàng crm_gk_xuat ⨝ rev
        self.loi_ghim = None

    def danh_tinh(self, dn):
        return {"dang_nhap": dn}

    @contextmanager
    def _tx(self, dt, rr=False):
        self.nhat.append(("TX", rr))
        yield _Cur(self)
        self.nhat.append(("END",))

    def tra_loi(self, sql, params):
        if "crm_ky_tra(NULL" in sql:
            if self.loi_quyen:
                raise self.loi_quyen
            return {"r": None}
        if "crm_ky_tra(" in sql:
            return {"r": self.tra_ky}
        if "crm_ky_ket(" in sql:
            return {"r": {"lap_lai": False, "ket_qua": {"ky_id": "k-1", "trang_thai": "DA_KY", "g5": {"trang_thai": "NOT_SELECTED"}}}}
        if "crm_ky_tep(" in sql:
            if self.loi_quyen:
                raise self.loi_quyen
            return {"r": self.tep}
        raise AssertionError("SQL ngoài dự kiến: " + sql[:80])

    def _mot(self, c, sql, params):
        self.nhat.append(("MOT", "crm_gk_xuat"))
        return self.xuat

    def mau_ghim_trong(self, c, soan, rev):
        self.nhat.append(("GHIM", soan, rev))
        if self.loi_ghim:
            raise self.loi_ghim


class ServiceMock(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="crm-ky-mock-"))  # giữ lại (không xóa tệp)
        self.mau = _MauGia(self.tmp)
        gk = mock.Mock(mau=self.mau, kho=self.tmp / "giao-ket")
        self.svc = KY.CrmKyKetK2(gk)
        self.docx, self.pdf_g3 = b"PK-docx-tong-hop", pdf_tong_hop(1, "BAN XUAT G3")
        for b in (self.docx, self.pdf_g3):
            p = self.tmp / "giao-ket" / "tep" / hashlib.sha256(b).hexdigest()
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.write_bytes(b)
        # cùng fixture tổng hợp G2 (2 dòng 30/70 VND) ở ĐÚNG dạng producer lưu vào revision: producer G2/G3 chuẩn hóa qua chuan_hoa_bao_gia trước
        # khi ghi du_lieu.bao_gia (raw bao_gia() thiếu khóa canonical như gia.don_gia → KeyError ở tinh_bao_gia — lỗi fixture, không phải production)
        bg = chuan_hoa_bao_gia(bao_gia())
        x ={"id": XU, "revision": 2, "trang_thai": "PDF_DAT", "docx_sha256": hashlib.sha256(self.docx).hexdigest(), "docx_len": len(self.docx),
             "pdf_sha256": hashlib.sha256(self.pdf_g3).hexdigest(), "pdf_len": len(self.pdf_g3), "engine": "WORD_DEMO",
             "du_lieu": {"bao_gia": bg}, "du_lieu_sha256": "1" * 64, "raw_sha256": "2" * 64, "ban_do_sha256": "3" * 64, "danh_muc_digest": "4" * 64,
             "profile_sha256": "5" * 64}
        x["input_sha256"] = hashlib.sha256(canonical_json({"soan_id": SO, "revision": 2, "du_lieu_sha256": x["du_lieu_sha256"], "raw_sha256": x["raw_sha256"],
                                                           "ban_do_sha256": x["ban_do_sha256"], "danh_muc_digest": x["danh_muc_digest"],
                                                           "profile_sha256": x["profile_sha256"], "renderer": "WORD_DEMO"}).encode("utf-8")).hexdigest()
        self.mau.xuat = x
        self.raw = pdf_tong_hop(1, "BAN DA KY")

    def _ky(self, raw=None, **sua):
        b = yc(**sua)
        return self.svc.ky("MO_PHONG_CRM_G_BH_A", self.raw if raw is None else raw, so_trang=b.pop("so_trang", 1), **b)

    def _kho_ky(self):
        d = self.tmp / "giao-ket" / "ky"
        return sorted(p.name for p in d.iterdir() if p.is_file()) if d.exists() else []

    def test_quyen_truoc_parse_bytes_khi_goi_truc_tiep(self):
        thu_tu = []
        self.mau.loi_quyen = DataError("CRM_KY_CHUA_CO_PHAM_VI", "x")
        with mock.patch.object(KY, "kiem_pdf_ky", side_effect=lambda r: thu_tu.append("parse") or 1):
            with self.assertRaises(DataError) as cm:
                self.svc.ky("MO_PHONG_CRM_G_BH_A", self.raw, so_trang=None, **yc())
        self.assertEqual(cm.exception.code, "CRM_KY_CHUA_CO_PHAM_VI")
        self.assertEqual(thu_tu, [])  # không parse bytes khi chưa có quyền
        self.assertEqual(self._kho_ky(), [])

    def test_duong_duong_mock_ghi_kho_truoc_ham_lenh(self):
        r = self._ky()
        self.assertEqual(r["trang_thai"], "DA_KY")
        self.assertFalse(r["lap_lai"])
        sha = hashlib.sha256(self.raw).hexdigest()
        self.assertEqual(self._kho_ky(), [sha])
        sqls = [n[1] for n in self.mau.nhat if n[0] == "SQL"]
        self.assertTrue(sqls[0].startswith("SELECT master.crm_ky_tra("))
        self.assertTrue(sqls[-1].startswith("SELECT master.crm_ky_ket("))
        p = next(n[2] for n in self.mau.nhat if n[0] == "SQL" and n[1].startswith("SELECT master.crm_ky_ket("))
        self.assertEqual((p[0], p[2], p[3], p[4]), ("crmgk-ky-1", SO, 2, XU))
        self.assertEqual((p[5], p[6], p[7]), (self.mau.xuat["input_sha256"], self.mau.xuat["pdf_sha256"], self.mau.xuat["pdf_len"]))
        self.assertEqual((p[8], p[9], p[10], p[13]), (sha, len(self.raw), 1, False))
        self.assertEqual(json.loads(p[16]), TOM_TAT_KY_VONG)  # kỳ vọng độc lập (không lấy từ hàm đang kiểm)
        t = tinh_bao_gia(self.mau.xuat["du_lieu"]["bao_gia"], None)  # đối chiếu thêm: cùng phép tính G2/G3
        self.assertEqual((len(t["dong"]), t["tong_minor"], t["tien_te"]), (2, "1000000000", "VND"))
        self.assertIn(("GHIM", SO, 2), self.mau.nhat)

    def test_ban_ky_trung_byte_ban_xuat_la_lan_ky_dau_rieng(self):
        """MOCK (không PG): lần ký ĐẦU với bytes trùng PDF G3 được nhận — hai vai trò bằng chứng riêng (G3 ở `tep/`, bản ký ở `ky/`), hai hash/độ dài
        truyền riêng cho hàm lệnh. Không ký A rồi gửi B (đó là ca Q-RETURN riêng). Hash/bytes KHÔNG chứng minh chữ ký xác thực."""
        sha_g3 = hashlib.sha256(self.pdf_g3).hexdigest()
        tep_g3 = self.tmp / "giao-ket" / "tep" / sha_g3
        truoc = tep_g3.read_bytes()
        r = self._ky(raw=self.pdf_g3)
        self.assertEqual((r["trang_thai"], r["lap_lai"]), ("DA_KY", False))
        p = next(n[2] for n in self.mau.nhat if n[0] == "SQL" and n[1].startswith("SELECT master.crm_ky_ket("))
        self.assertEqual((p[6], p[7]), (sha_g3, len(self.pdf_g3)))  # G3: do máy chủ resolve từ bản xuất
        self.assertEqual((p[8], p[9]), (sha_g3, len(self.pdf_g3)))  # bản ký: hash/độ dài của bytes tải lên (tính riêng)
        self.assertEqual(self._kho_ky(), [sha_g3])  # ghi vào kho bản ký riêng
        self.assertEqual(tep_g3.read_bytes(), truoc)  # artifact G3 nguyên
        self.assertEqual(json.loads(p[16]), TOM_TAT_KY_VONG)

    def test_digest_khong_gom_khoa_va_doi_than_doi_digest(self):
        self._ky(khoa="k-a")
        self._ky(khoa="k-b")
        self._ky(khoa="k-c", ngay_ky="2026-10-19")
        # native33 fixture fix: tham số thật của crm_ky_tra(p_khoa, p_soan, p_h) là (khoa, SO, h) → digest ở chỉ số [2] (không phải [1] = soan UUID)
        ps = [n[2] for n in self.mau.nhat if n[0] == "SQL" and n[1].startswith("SELECT master.crm_ky_tra(")]
        self.assertEqual(len(ps), 3)
        for p in ps:
            self.assertEqual(len(p), 3)
            self.assertEqual(p[1], SO)
        hs = [p[2] for p in ps]
        for h in hs:
            self.assertIsInstance(h, str)
            self.assertTrue(len(h) == 64 and all(ch in "0123456789abcdef" for ch in h), h)
        self.assertEqual(hs[0], hs[1])
        self.assertNotEqual(hs[0], hs[2])

    def test_replay_khong_doc_can_cu_khong_ghi_kho(self):
        self.mau.tra_ky = {"lap_lai": True, "ket_qua": {"ky_id": "k-0", "trang_thai": "DA_KY"}}
        r = self._ky()
        self.assertEqual((r["ky_id"], r["lap_lai"]), ("k-0", True))
        self.assertNotIn(("MOT", "crm_gk_xuat"), self.mau.nhat)
        self.assertEqual(self._kho_ky(), [])

    def test_xuat_khong_thay_chua_dat(self):
        self.mau.xuat = None
        with self.assertRaises(DataError) as cm:
            self._ky()
        self.assertEqual(cm.exception.code, "CRM_KY_XUAT_CU")
        self.setUp()
        self.mau.xuat["trang_thai"] = "PDF_LOI"
        with self.assertRaises(DataError) as cm:
            self._ky()
        self.assertEqual(cm.exception.code, "CRM_KY_XUAT_CHUA_DAT")
        self.assertEqual(self._kho_ky(), [])

    def test_kho_g3_sai_hash_do_dai_hoac_lineage(self):
        for sua in ({"pdf_len": 1}, {"docx_sha256": "f" * 64}, {"input_sha256": "e" * 64}, {"engine": "KHAC"}):
            self.setUp()
            self.mau.xuat.update(sua)
            with self.assertRaises(DataError) as cm:
                self._ky()
            self.assertEqual(cm.exception.code, "CRM_KY_G3_LECH", sua)
            self.assertEqual(self._kho_ky(), [], sua)
            self.assertFalse(any(n[0] == "SQL" and n[1].startswith("SELECT master.crm_ky_ket(") for n in self.mau.nhat))

    def test_ghim_mau_lech_khong_ky(self):
        self.mau.loi_ghim = DataError("CRM_GK_MAU_LECH_GHIM", "x")
        with self.assertRaises(DataError) as cm:
            self._ky()
        self.assertEqual(cm.exception.code, "CRM_GK_MAU_LECH_GHIM")
        self.assertEqual(self._kho_ky(), [])

    def test_tai_quyen_truoc_kho_va_kiem_hash(self):
        self.mau.loi_quyen = DataError("CRM_G_KHONG_THAY", "x")
        with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("đọc kho trước quyền")):
            with self.assertRaises(DataError) as cm:
                self.svc.tep("MO_PHONG_CRM_G_KT_B", str(uuid.uuid4()))
        self.assertEqual(cm.exception.code, "CRM_G_KHONG_THAY")
        self.mau.loi_quyen = None
        self._ky()
        sha = hashlib.sha256(self.raw).hexdigest()
        self.mau.tep = {"ky_id": "k-1", "sha256": sha, "len": len(self.raw), "revision": 2, "ten": "HD-NB/1"}
        ten, raw, mime = self.svc.tep("MO_PHONG_CRM_G_KT_A", str(uuid.uuid4()))
        self.assertEqual((raw, mime), (self.raw, "application/pdf"))
        self.assertEqual(ten, "HD-NB_1-r2-ban-ky.pdf")
        self.mau.tep = {**self.mau.tep, "len": len(self.raw) + 1}
        with self.assertRaises(DataError) as cm:
            self.svc.tep("MO_PHONG_CRM_G_KT_A", str(uuid.uuid4()))
        self.assertEqual(cm.exception.code, "CRM_G_TEP_HONG")
        self.mau.tep = {**self.mau.tep, "sha256": "../" + sha[3:]}
        with self.assertRaises(DataError) as cm:
            self.svc.tep("MO_PHONG_CRM_G_KT_A", str(uuid.uuid4()))
        self.assertEqual(cm.exception.code, "CRM_G_TEP_KHONG_CO")


# ====================================================================== PostgreSQL THẬT (guard âm; không tạo PDF_DAT giả)
try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None
ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "PostgreSQL thật chưa cấu hình (KHO_PG_DSN_TEST) — NOT_RUN, không tính đạt")
class GuardCsdlThat(unittest.TestCase):
    """DB test MỚI (kho_test_*), migrate 1–23 + DEMO CRM/G hiện có. Không dữ liệu thật, không M9 seed, DB giữ lại (không DROP)."""

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.k2 import crm_demo, crm_g_demo
        cls.db = "kho_test_crmky_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.c = psycopg.connect(cls.dsn, autocommit=True)
        cls.addClassCleanup(cls.c.close)
        cls.version = pg.migrate(cls.c)
        crm_demo.khoi_tao(cls.c)
        crm_g_demo.khoi_tao(cls.c)

    def q(self, sql, *p):
        return self.c.execute(sql, p).fetchall()

    def loi(self, ma, sql, *p):
        with self.assertRaises(psycopg.Error) as cm:
            with self.c.transaction():
                self.c.execute(sql, p)
        self.assertIn(ma, str(cm.exception))

    def test_version_23_va_bang(self):
        self.assertEqual(self.version, 23)
        for t in KY_BANG:
            self.assertEqual(self.q("SELECT count(*) FROM pg_class WHERE oid = %s::regclass", f"master.{t}")[0][0], 1)
            self.assertTrue(self.q("SELECT relrowsecurity FROM pg_class WHERE oid = %s::regclass", f"master.{t}")[0][0])

    def test_vai_ung_dung_khong_co_quyen_bang_ham(self):
        for vai in ("app_web", "app_ke_toan", "app_doc", "app_cong_ai"):
            if not self.q("SELECT 1 FROM pg_roles WHERE rolname = %s", vai):
                continue
            for t in KY_BANG:
                for p in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                    self.assertFalse(self.q("SELECT has_table_privilege(%s, %s, %s)", vai, f"master.{t}", p)[0][0], (vai, t, p))
            for f in ("master.crm_ky_tra(text, uuid, text)", "master.crm_ky_doc(uuid)", "master.crm_ky_tep(uuid, text)",
                      "master.crm_ky_pham_vi_hd(uuid, text, text[])", "master.crm_ky_pham_vi_duoc(uuid)", "master.crm_ky_doc_duoc(uuid)",
                      "master.crm_ky_ket(text, text, uuid, integer, uuid, text, text, bigint, text, bigint, integer, text, date, boolean, text, text, jsonb)"):
                self.assertFalse(self.q("SELECT has_function_privilege(%s, %s, 'EXECUTE')", vai, f)[0][0], (vai, f))

    def test_pham_vi_sai_khong_chen(self):
        # chủ bảng chèn phạm vi trỏ phân công/HĐ không tồn tại → trigger CRM_KY_PHAM_VI_SAI (trước FK); không tự cấp
        self.loi("CRM_KY_PHAM_VI_SAI", """INSERT INTO master.crm_ky_pham_vi (phan_cong_id, phap_nhan_id, hop_dong_id, soan_id, khach_du_thao_sha256, cap_boi)
                                          VALUES (gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), %s, 'owner')""", "0" * 64)
        self.assertEqual(self.q("SELECT count(*) FROM master.crm_ky_pham_vi")[0][0], 0)

    def test_ban_ky_va_g5_khong_chen_khi_sai_lineage(self):
        z = "0" * 64
        self.loi("CRM_KY_G3_LECH", """INSERT INTO master.crm_hd_ky (phap_nhan_id, hop_dong_id, soan_id, revision, soan_rev_id, xuat_id, g3_input_sha256,
            g3_docx_sha256, g3_docx_len, g3_pdf_sha256, g3_pdf_len, g3_engine, mau_phien_ban_id, anh_xa_id, kiem_id, raw_sha256, ban_do_sha256, danh_muc_ref,
            danh_muc_rev, danh_muc_digest, profile_phien_ban, profile_sha256, du_lieu_sha256, tom_tat, ky_pdf_sha256, ky_pdf_len, ky_so_trang, ten_tep, ngay_ky,
            co_sua, tao_boi)
            VALUES (gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), 1, gen_random_uuid(), gen_random_uuid(), %s, %s, 1, %s, 1, 'X',
                    gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), %s, %s, 'ref', 1, %s, 1, %s, %s, '{}'::jsonb, %s, 1, 1, 'a.pdf',
                    current_date, false, 'owner')""", z, z, z, z, z, z, z, z, "1" * 64)
        self.loi("CRM_KY_G5_SAI", "INSERT INTO master.crm_hd_ky_g5 (ky_id, phap_nhan_id, trang_thai, ly_do) VALUES (gen_random_uuid(), gen_random_uuid(), "
                                  "'NOT_SELECTED', 'CHUA_AP_DUNG_CHON_MAU')")
        self.assertEqual(self.q("SELECT count(*) FROM master.crm_hd_ky")[0][0], 0)

    def test_catalog_khong_buoc_digest_khac_va_doc_khong_rong(self):
        """CATALOG/ÂM trên PG thật (không phải bằng chứng dương phạm vi/đồng thời/producer): bảng bản ký KHÔNG có CHECK ky ≠ g3; vẫn có UNIQUE HĐ;
        phiên không danh tính không đọc được bản ký nào (crm_ky_doc_duoc fail closed)."""
        defs = [r[0] for r in self.c.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'master.crm_hd_ky'::regclass").fetchall()]
        self.assertFalse([d for d in defs if "ky_pdf_sha256" in d and "g3_pdf_sha256" in d and "<>" in d], defs)
        self.assertIn("UNIQUE (hop_dong_id)", defs)
        trig = self.q("SELECT prosrc FROM pg_proc WHERE oid = 'master.crm_ky_pham_vi_kiem'::regproc")[0][0]
        self.assertIn("'CRM_KY_DOC'", trig)
        for (sid,) in self.q("SELECT id FROM master.crm_hd_soan"):
            self.assertFalse(self.q("SELECT master.crm_ky_doc_duoc(%s)", sid)[0][0], sid)

    def test_trang_thai_da_ky_khong_vao_khi_chua_co_ban_ky(self):
        rows = self.q("SELECT id FROM master.crm_hd_soan LIMIT 1")
        if not rows:
            self.skipTest("DEMO chưa có bản soạn — NOT_RUN (không tạo bản soạn/PDF_DAT giả); kiểm qua HTTP khi có Word")
        self.loi("CRM_KY_TRANG_THAI", "UPDATE master.crm_hd_soan SET trang_thai = 'DA_KY' WHERE id = %s", rows[0][0])


if __name__ == "__main__":
    unittest.main()
