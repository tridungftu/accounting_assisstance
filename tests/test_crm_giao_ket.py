"""CRM-41-03 — G2/G3: kiểm tĩnh + thuần + renderer + (có điều kiện) Word COM thật. CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN_CODE_ONLY).

Phân loại:
- `PrefixMigration`, `M21Tinh`, `RouteTinh`: TĨNH trên mã nguồn/hằng SQL (không PostgreSQL).
- `TinhChinhXac`: THUẦN — chuẩn hóa/tính báo giá bằng số nguyên đơn vị nhỏ nhất + Fraction (không float/rounding), kiểm In/Xuất.
- `RenderDocx`: THẬT trên python-docx (bytes DOCX tổng hợp CRM-only tạo trong test): tách run/bảng lồng/header-footer được tham chiếu, tên ô ≠ mã
  trường, giữ định dạng run đầu ô; lệch facts/thiếu ánh xạ/kênh chưa hỗ trợ → lỗi có mã (không xuất giả). Thiếu python-docx → skip (KHÔNG PASS).
- `NhaCungCapPdf`: THUẦN với nhà cung cấp vắng (không spawn) → DOCX GIỮ, PDF_CHUA_SAN_SANG, không CHO_KY.
- `WordThat`: THẬT Word COM + PDFium/pdfplumber — chỉ Windows có đúng WINWORD đã ghim + pywin32 + guard A517; thiếu → skip (KHÔNG PASS).
  FIX02: test chính KHÔNG gọi COM; "Word người dùng" control chạy trong native child do test sở hữu (Job trước stdin, hạn, dừng có bằng chứng),
  child tự tạo/sở hữu/chứng minh Word như worker; không sở hữu được → skip (NOT_VERIFIED, KHÔNG PASS).
- FIX02 (`VongDoiParent`, `DungWordSoHuu`): THUẦN — tiêm lỗi mọi nhánh vòng đời parent/Word (gán Job/stdin/EOF/quá hạn/treo/Job không rỗng/
  truy vấn lỗi/dừng false-chưa rõ/PDF có sẵn); đồng hồ/Job/tiến trình GIẢ — không phải bằng chứng Word native.
- FIX01 (`KetLuanWorker`, `KiemPdfDem`, `DatChoRender`, `TongCanonical`, `MocTrong`): THUẦN — tiêm lỗi kết luận worker, đếm số lần nội dung PDF,
  đối soát lần render đã đặt chỗ, ngữ nghĩa trường tổng canonical, mốc trống.
Dữ liệu tổng hợp; không M9, không seed/bootstrap chung, không dữ liệu/cấu hình thật, không xóa tệp.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import tempfile
import time
import types
import unicodedata
import unittest
import uuid
import zipfile
from pathlib import Path
from unittest import mock

from kho_tri_thuc.giao_dien import crm_g as G
from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import crm_giao_ket as GK
from kho_tri_thuc.nguon import crm_docx as R

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
LOAI = "11111111-1111-4111-8111-111111111111"
try:
    import docx as _docx  # noqa: F401
    CO_DOCX = True
except ImportError:  # pragma: no cover
    CO_DOCX = False

# ---------------------------------------------------------------------- DOCX tổng hợp CRM-only
W_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
REL_NS, REL_T = "http://schemas.openxmlformats.org/package/2006/relationships", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"


def r(t, dam=False):
    return f'<w:r>{"<w:rPr><w:b/></w:rPr>" if dam else ""}<w:t xml:space="preserve">{t}</w:t></w:r>'


def _bang(o_xml: str, rong: int) -> str:
    """FIX04: một bảng 1×1 HỢP LỆ với Microsoft Word — w:tblPr + w:tblGrid bắt buộc theo schema WordprocessingML, w:tcPr/w:tcW; nội dung ô giữ nguyên.
    Ô PHẢI kết thúc bằng w:p: nếu nội dung ô kết thúc bằng bảng lồng thì thêm một đoạn trống (không văn bản → không đổi ô/facts văn bản)."""
    ket = "" if o_xml.endswith("</w:p>") else "<w:p/>"
    return (f'<w:tbl><w:tblPr><w:tblW w:w="{rong}" w:type="dxa"/></w:tblPr><w:tblGrid><w:gridCol w:w="{rong}"/></w:tblGrid>'
            f'<w:tr><w:tc><w:tcPr><w:tcW w:w="{rong}" w:type="dxa"/></w:tcPr>{o_xml}{ket}</w:tc></w:tr></w:tbl>')


def mau_docx(than_them: str = "") -> bytes:
    """Thân: ô tách run (run đầu IN ĐẬM) + bảng lồng + đoạn; header + footer được tham chiếu.
    FIX04: gói/markup hợp lệ để Microsoft Word mở được (trước đây ô ngoài kết thúc bằng bảng lồng và bảng thiếu tblPr/tblGrid → Word báo
    "The file appears to be corrupted"). Văn bản, tên ô, tách run/in đậm, bảng lồng, header/footer, `than_them` giữ nguyên."""
    bang_long = _bang("<w:p>" + r("Giá trị: {{gia_tri}}") + "</w:p>", 7000)
    than = ("<w:p>" + r("Hợp đồng số ") + r("{{so_", dam=True) + r("hop_dong}}") + r(" ký ngày {{ngay_ky}}") + "</w:p>"
            + _bang("<w:p>" + r("Bên mua: {{ho_ten}}") + "</w:p>" + bang_long, 9000)
            + "<w:p/>"  # FIX04: như Word tự ghi — bảng không là khối cuối của thân trước sectPr; đoạn trống, không văn bản/ô
            + than_them
            + '<w:sectPr><w:headerReference w:type="default" r:id="rIdH"/><w:footerReference w:type="default" r:id="rIdF"/></w:sectPr>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                   '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
                   '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')
        z.writestr("_rels/.rels", XML + f'<Relationships xmlns="{REL_NS}"><Relationship Id="rId1" Type="{REL_T}officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", XML + f"<w:document {W_NS}><w:body>{than}</w:body></w:document>")
        z.writestr("word/_rels/document.xml.rels", XML + f'<Relationships xmlns="{REL_NS}"><Relationship Id="rIdH" Type="{REL_T}header" Target="header1.xml"/>'
                   f'<Relationship Id="rIdF" Type="{REL_T}footer" Target="footer1.xml"/></Relationships>')
        z.writestr("word/header1.xml", XML + f"<w:hdr {W_NS}><w:p>{r('Số HĐ: {{so_hop_dong}}')}</w:p></w:hdr>")
        z.writestr("word/footer1.xml", XML + f"<w:ftr {W_NS}><w:p>{r('Trang cuối — {{ngay_ky}}')}</w:p></w:ftr>")
    return buf.getvalue()


BAN_DO_TEN = {"so_hop_dong": "so_hop_dong", "ngay_ky": "ngay_ky", "ho_ten": "ten_hien_thi_demo", "gia_tri": "gia_tri_hop_dong"}  # tên ô ≠ mã trường


def ban_do_tu_facts(facts, map_=BAN_DO_TEN):
    """Như hàm SQL crm_g_mau_anh_xa: thứ tự = ordinal của lần xuất hiện trong facts."""
    return [{"thu_tu": i, "ten": o["ten"], "phan": o["phan"], "vi_tri": o["vi_tri"], "truong": map_.get(o["ten"])}
            for i, o in enumerate(facts["occurrences"], start=1)]


def bao_gia(**sua):
    d = {"loai_hinh_id": LOAI, "nguon_lich": "KHACH", "don_vi": {"ma": "LO-A01"}, "khach": {"du_thao": {"ten": "KHÁCH DEMO"}},
         "gia": {"tien_te": "VND", "tong": "1000000000", "co_so_thue": "NET"},
         "lich": [{"lan": "1", "loai": "PERCENT", "ty_le": "30", "moc_loai": "SU_KIEN", "moc_su_kien": "KY_HD"},
                  {"lan": "2", "loai": "PERCENT", "ty_le": "70", "moc_loai": "NGAY", "moc_ngay": "2026-12-31"}]}
    d.update(sua)
    return d


class PrefixMigration(unittest.TestCase):
    def test_870225_byte_dau_giu_nguyen_chi_append_m0021(self):
        raw = (SRC / "ha_tang" / "pg_migrations.py").read_bytes()
        self.assertEqual(hashlib.sha256(raw[:870225]).hexdigest(), "7082f25843f12ced5c71ccbe8b23991ce458d9836d2e9448f29a598d0eeac5f2")
        duoi = raw[870225:].decode("utf-8")
        self.assertIn("M0021_CRM_G2G3 = (", duoi)
        self.assertTrue(duoi.rstrip().endswith("PG_MIGRATIONS = (*PG_MIGRATIONS, M0021_CRM_G2G3)\nPG_SCHEMA_VERSION = len(PG_MIGRATIONS)"), duoi[-200:])
        self.assertEqual((PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS)), (21, 21))
        self.assertIs(PM.PG_MIGRATIONS[20], PM.M0021_CRM_G2G3)
        for f in ("sql_review.py", "sql_m17.py"):  # protected: không nằm trong phạm vi ghi; chỉ được import như cũ
            self.assertIn(f"from ..m4.{f[:-3]} import", raw[:870225].decode("utf-8"))


class M21Tinh(unittest.TestCase):
    S = PM.M0021_CRM_G2G3

    def test_khong_xoa_khong_doi_enum_cu(self):
        for s in self.S:
            self.assertIsNone(re.search(r"\bDROP\b|\bTRUNCATE\b|DELETE\s+FROM", s), s[:120])
            self.assertNotIn("_tao_phien_ban", s)
            self.assertNotIn("ALTER TABLE kho.viec_can_duyet", s)
            self.assertNotIn("lich_thu", s)  # không sinh nghĩa vụ/lịch thu
        noi = "\n".join(self.S)
        self.assertIn("ALTER TABLE master.hop_dong ADD COLUMN crm_giao_ket text", noi)
        self.assertNotIn("hop_dong_trang_thai_check", noi)
        self.assertNotIn("'HIEU_LUC', 'HIEU_LUC'", noi)

    def test_ham_lenh_invoker_quyen_truoc_bien_nhan(self):
        lenh = [s for s in self.S if re.search(r"FUNCTION master\.crm_gk_(bao_gia_luu|bao_gia_huy|chuyen|soan_luu|xuat_ghi|dat_lan)\(", s)]
        self.assertEqual(len(lenh), 6)
        for s in lenh:
            self.assertNotIn("SECURITY DEFINER", s)
            self.assertIn("CRM_G_CHI_MAY_CHU", s)
            # FIX01 #6: ghim quyền (FOR SHARE) TRONG CÙNG giao dịch, TRƯỚC kiểm đích và TRƯỚC chờ khóa namespace của biên nhận
            self.assertIn("master.crm_g_ghim_quyen(master.crm_gk_pn(", s, s[:80])
            self.assertLess(s.index("master.crm_g_ghim_quyen(master.crm_gk_pn("), s.index("master.crm_gk_dich("), s[:80])
            self.assertLess(s.index("master.crm_gk_dich("), s.index("master.crm_g_bn_tra("))
        tra = next(s for s in self.S if "FUNCTION master.crm_gk_tra(" in s)
        self.assertLess(tra.index("master.crm_g_ghim_quyen("), tra.index("master.crm_gk_dich("))

    def test_lan_dat_cho_ben_va_cong_bo_dung_lan(self):  # FIX01 #5
        noi = "\n".join(self.S)
        self.assertIn("UNIQUE (phap_nhan_id, nguoi_dung_id, hanh_dong, khoa)", noi)
        self.assertIn("CHECK ((trang_thai = 'DA_CONG_BO') = (xuat_id IS NOT NULL))", noi)
        k = next(s for s in self.S if "FUNCTION master.crm_gk_lan_kiem(" in s)
        for x in ("TG_OP = 'DELETE'", "NEW.trang_thai <> 'DANG_RENDER'", "OLD.trang_thai <> 'DANG_RENDER' OR NEW.trang_thai <> 'DA_CONG_BO'", "la_chu_bang"):
            self.assertIn(x, k)
        d = next(s for s in self.S if "FUNCTION master.crm_gk_dat_lan(" in s)
        self.assertLess(d.index("master.crm_g_bn_tra("), d.index("FROM master.crm_gk_lan"))  # FINAL trước, rồi lần đã đặt
        self.assertLess(d.index("CRM_G_IDEMPOTENCY_KHAC"), d.index("INSERT INTO master.crm_gk_lan"))  # cùng khóa khác H → 409, không chỗ mới
        self.assertLess(d.index("CRM_GK_REVISION_CU"), d.index("INSERT INTO master.crm_gk_lan"))
        x = next(s for s in self.S if "FUNCTION master.crm_gk_xuat_ghi(" in s)
        self.assertLess(x.index("CRM_GK_LAN_KHONG_KHOP"), x.index("INSERT INTO master.crm_gk_xuat"))
        self.assertLess(x.index("INSERT INTO master.crm_gk_xuat"), x.index("UPDATE master.crm_gk_lan SET trang_thai = 'DA_CONG_BO'"))

    def test_chuyen_mot_hop_dong_soan_thao_va_xuat_cas(self):
        ch = next(s for s in self.S if "FUNCTION master.crm_gk_chuyen(" in s)
        self.assertEqual(ch.count("INSERT INTO master.hop_dong "), 1)
        self.assertIn("'SOAN_THAO', 'SOAN_THAO'", ch)
        self.assertIn("CRM_GK_DA_CHUYEN", ch)
        x = next(s for s in self.S if "FUNCTION master.crm_gk_xuat_ghi(" in s)
        self.assertIn("revision_hien_hanh <> p_revision", x)
        self.assertIn("'DA_CU'", x)
        self.assertIn("IF tt = 'PDF_DAT' THEN", x)
        self.assertNotIn("DA_KY", x)
        g = next(s for s in self.S if "FUNCTION master.crm_gk_mau_ghim(" in s)
        self.assertIn("crm_hd_soan_rev", g)  # đọc mẫu đã ghim gắn đúng bản soạn, không theo picker

    def test_bang_moi_revoke_rls(self):
        noi = "\n".join(self.S)
        for t in PM._GK_BANG_MOI:
            self.assertIn(f"ALTER TABLE master.{t} ENABLE ROW LEVEL SECURITY", noi)
        self.assertIn("'app_web','app_ke_toan','app_doc','app_cong_ai'", noi)


class RouteTinh(unittest.TestCase):
    def test_route_va_render_ngoai_khoa(self):
        for p in ("/api/crm/bao-gia", "/api/crm/bao-gia/luu", "/api/crm/soan/xuat", "/api/crm/giao-ket/tep/x/pdf"):
            self.assertTrue(G.la_route(True, p) or G.la_route(False, p), p)
        self.assertFalse(G.la_route(True, "/api/crm/mau"))  # handler #6 cũ giữ nguyên
        src = (SRC / "giao_dien" / "crm_g.py").read_text(encoding="utf-8")
        than = src[src.index("def _dai_gk("):src.index("def _than(")]
        dong = than.splitlines()
        i = next(n for n, d in enumerate(dong) if "gk.render(kh)" in d)
        self.assertEqual(len(dong[i]) - len(dong[i].lstrip()), 4)  # cùng mức hàm, NGOÀI `with app.mutation_lock:`
        self.assertEqual(than.count("with app.mutation_lock:"), 2)
        self.assertIn('"soan/xuat"', src)
        self.assertNotIn("soan/xuat", src[src.index("TRUONG = {"):src.index("TRUONG_TAI")])  # không đi qua nhánh lệnh chung
        for k in G.TRUONG_GK.values():
            self.assertFalse(k & G.KHONG_NHAN)
        self.assertEqual(G.TRUONG_GK["bao-gia/xem-truoc"], {"du_lieu"})  # FIX01 #4: tính thử chỉ nhận dữ liệu form, không khóa/actor
        self.assertTrue(G.la_route(True, "/api/crm/bao-gia/xem-truoc") or G.la_route(False, "/api/crm/bao-gia/xem-truoc"))
        self.assertTrue({"CRM_GK_DANG_XU_LY", "CRM_GK_LAN_KHONG_KHOP"} <= G.MA_409_GK)


class TinhChinhXac(unittest.TestCase):
    def tinh(self, **sua):
        d = GK.chuan_hoa_bao_gia(bao_gia(**sua))
        return d, GK.tinh_bao_gia(d, None)

    def test_vnd_100_phan_tram_duong_tinh(self):
        d, t = self.tinh()
        self.assertEqual(t["tong_minor"], "1000000000")
        self.assertEqual([x["so_tien_minor"] for x in t["dong"]], ["300000000", "700000000"])
        self.assertEqual(t["tong_ty_le"], "100")
        self.assertEqual(t["chan_in"], [])

    def test_bg1_lich_typed_cu_co_phan_hien_thi_moi(self):
        _, t = self.tinh()
        self.assertEqual(t["dong"][0]["so_tien"], t["dong"][0]["so_tien_minor"])
        self.assertEqual(t["dong"][0]["hien_thi_mo"], "= 300.000.000 VND")
        self.assertEqual(t["dong"][0]["moc_hien_thi"], "Ký")
        self.assertTrue(t["tong_ty_le_khop"])
        self.assertEqual(t["ly_do_chan_in"], "")

    def test_bg1_moc_tham_so_khong_doi_ma_luu(self):
        d, t = self.tinh(lich=[{"gia_tri_nhap": "100%", "moc_loai": "SU_KIEN", "moc_su_kien": "SAU_KY_30"}])
        self.assertEqual(d["lich"][0]["moc_su_kien"], "SAU_KY_30")
        self.assertEqual(t["dong"][0]["moc_hien_thi"], "Sau ký + 30 ngày")

    def test_tong_khac_100_usd_thieu_fx_chan_in_nhung_luu_duoc(self):
        _, t = self.tinh(lich=[{"lan": "1", "loai": "PERCENT", "ty_le": "30"}, {"lan": "2", "loai": "PERCENT", "ty_le": "60"}])
        self.assertIn("TONG_TY_LE_KHAC_100", [x["ma"] for x in t["chan_in"]])
        self.assertIn("MOC_TRONG", [x["ma"] for x in t["canh_bao"]])  # mốc trống chỉ cảnh báo
        _, t = self.tinh(gia={"tien_te": "USD", "tong": "1000.00", "co_so_thue": "GROSS"})
        self.assertIn("USD_THIEU_FX", [x["ma"] for x in t["chan_in"]])

    def test_usd_fx_doi_chi_doi_vnd_tham_chieu(self):
        g = {"tien_te": "USD", "tong": "1234.56", "co_so_thue": "NET"}
        _, a = self.tinh(gia=g, fx={"cap": "USD/VND", "ty_gia": "25000", "ngay": "2026-10-21"})
        _, b = self.tinh(gia=g, fx={"cap": "USD/VND", "ty_gia": "25100.5", "ngay": "2026-10-22"})
        self.assertEqual((a["tong_minor"], b["tong_minor"]), ("123456", "123456"))  # USD gốc giữ nguyên
        self.assertEqual(a["vnd_tham_chieu"]["tong"], "30864000")
        self.assertEqual(b["vnd_tham_chieu"]["tong"], "30988073.28")  # 1234.56 × 25100.5 chính xác, không làm tròn

    def test_scale_null_zero_sai_dang_tran(self):
        _, t = self.tinh(gia={"tien_te": "VND", "tong": "1000.5", "co_so_thue": "NET"})
        self.assertIn("TONG_KHONG_DUNG_SCALE", [x["ma"] for x in t["chan_in"]])
        self.assertIsNone(t["tong_minor"])  # không làm tròn/không thành 0
        _, t = self.tinh(gia={"tien_te": "VND", "tong": None, "co_so_thue": "NET"})
        self.assertIsNone(t["tong_minor"])
        self.assertIn("THIEU_TONG_GIA_TRI", [x["ma"] for x in t["thieu"]])
        _, t = self.tinh(gia={"tien_te": "VND", "tong": "0", "co_so_thue": "NET"})
        self.assertEqual(t["tong_minor"], "0")  # 0 khai báo ≠ NULL
        _, t = self.tinh(gia={"tien_te": "VND", "tong": "1000", "co_so_thue": "NET"},
                         lich=[{"lan": "1", "loai": "PERCENT", "ty_le": "33.33"}, {"lan": "2", "loai": "PERCENT", "ty_le": "66.67"}])  # 333,3 VND
        self.assertIn("KHONG_BIEU_DIEN_DUNG_SCALE", t["dong"][0]["loi"])
        for xau in ("1,5", "-3", "1e5", "1" * 25, 12.5, True):
            with self.assertRaises(DataError, msg=xau) as cm:
                GK.chuan_hoa_bao_gia(bao_gia(gia={"tien_te": "VND", "tong": xau}))
            self.assertEqual(cm.exception.code, "CRM_GK_SO_SAI", xau)

    def test_phi_bao_tri_giu_rieng_khong_gop_lich(self):
        d, t = self.tinh(phi_bao_tri={"gia_tri": "20000000", "tien_te": "VND", "co_so": "2% giá trị căn hộ (DEMO)"})
        self.assertEqual(d["phi_bao_tri"]["gia_tri"], "20000000")
        self.assertEqual(t["tong_dong_minor"], "1000000000")
        self.assertEqual(t["chan_in"], [])

    def test_g7_lech_va_thieu_g7(self):
        g7 = {"trang_thai": "HIEU_LUC", "rows": [{"gia_tri_loai": "PERCENT", "gia_tri_thap_phan": "40", "moc_loai": "SU_KIEN", "moc_su_kien": "KY_HD",
                                                    "moc_ngay": None}, {"gia_tri_loai": "PERCENT", "gia_tri_thap_phan": "60", "moc_loai": "NGAY",
                                                                       "moc_ngay": "2026-12-31", "moc_su_kien": None}]}
        d = GK.chuan_hoa_bao_gia(bao_gia(nguon_lich="DU_AN"))
        t = GK.tinh_bao_gia(d, g7)
        self.assertEqual([x["ma"] for x in t["g7_lech"]], ["LECH_G7_TY_LE", "LECH_G7_TY_LE"])
        self.assertTrue(all(x["thong_bao"] for x in t["g7_lech"]))
        t = GK.tinh_bao_gia(d, {"trang_thai": "CHUA_CO", "rows": []})
        self.assertIn("THIEU_G7", [x["ma"] for x in t["canh_bao"]])
        self.assertEqual(t["g7_lech"], [])  # không fake khớp/lệch

    def test_client_khong_cap_ket_qua_tinh_hay_actor(self):
        for la in ({"tinh": {}}, {"trang_thai": "NHAP"}, {"nguoi_lap": "X"}):
            with self.assertRaises(DataError):
                GK.chuan_hoa_bao_gia({**bao_gia(), **la})
        with self.assertRaises(DataError):
            GK.chuan_hoa_bao_gia(bao_gia(fx={"cap": "USD/VND", "ty_gia": "25000", "ngay": "2026-10-21", "nguoi_nhap": "X"}))


class DinhDang(unittest.TestCase):
    def test_tien_ngay_bang_chu_chinh_xac(self):
        self.assertEqual(R.tien_hien_thi(123456789, "VND"), "123.456.789 VND")
        self.assertEqual(R.tien_hien_thi(123450, "USD"), "1.234,50 USD")
        self.assertEqual(R.bang_chu(1500000000000, "VND"), "Một nghìn năm trăm tỷ đồng")
        self.assertEqual(R.bang_chu(1000050, "VND"), "Một triệu không trăm năm mươi đồng")
        self.assertEqual(R.ngay_hien_thi("2026-10-21", "dd/MM/yyyy"), "21/10/2026")
        with self.assertRaises(R.LoiRender):
            R.so_hien_thi(__import__("fractions").Fraction(1, 3), 2)  # không cắt/làm tròn
        with self.assertRaises(R.LoiRender):
            R.ngay_hien_thi("2026-10-21", "MM-dd")


@unittest.skipUnless(CO_DOCX, "python-docx chưa cài — renderer DOCX không chạy (skip, KHÔNG PASS)")
class RenderDocx(unittest.TestCase):
    GT = {"so_hop_dong": "HĐ-DEMO-0001", "ngay_ky": "21/10/2026", "ten_hien_thi_demo": "NGƯỜI MUA DEMO", "gia_tri_hop_dong": "1.000.000.000 VND"}

    def test_dien_tach_run_bang_long_header_footer_giu_dinh_dang(self):
        from kho_tri_thuc.nguon.mau_docx import doc_mau_docx
        raw = mau_docx()
        f = doc_mau_docx(raw)
        self.assertEqual(f["trang_thai"], "DU")
        out, bc = R.dien_mau(raw, f, ban_do_tu_facts(f), self.GT)
        g = doc_mau_docx(out)
        self.assertEqual((g["trang_thai"], g["placeholders"]), ("DU", []))
        with zipfile.ZipFile(io.BytesIO(out)) as z:
            body, hdr, ftr = (z.read(p).decode("utf-8") for p in ("word/document.xml", "word/header1.xml", "word/footer1.xml"))
        self.assertIn("NGƯỜI MUA DEMO", body)  # ô bảng, tên ô ho_ten ≠ mã trường
        self.assertIn("1.000.000.000 VND", body)  # bảng lồng
        self.assertIn("HĐ-DEMO-0001", hdr)
        self.assertIn("21/10/2026", ftr)
        self.assertRegex(body, r"<w:b/></w:rPr><w:t xml:space=\"preserve\">HĐ-DEMO-0001</w:t>")  # định dạng run đầu ô (đậm) giữ cho giá trị
        self.assertEqual(bc["truong_trong"], [])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), f["raw_sha256"])  # bytes mẫu gốc không đổi

    def test_loi_co_ma_khong_xuat_gia(self):
        from kho_tri_thuc.nguon.mau_docx import doc_mau_docx
        raw = mau_docx()
        f = doc_mau_docx(raw)
        bd = ban_do_tu_facts(f, {**BAN_DO_TEN, "gia_tri": None})
        with self.assertRaises(R.LoiRender) as cm:
            R.dien_mau(raw, f, bd, self.GT)
        self.assertEqual(cm.exception.code, "CRM_GK_O_CHUA_ANH_XA")
        khac = mau_docx('<w:p><w:r><w:t xml:space="preserve">Đoạn thêm</w:t></w:r></w:p>')  # thêm một đoạn thân → chỉ số đoạn header lệch
        with self.assertRaises(R.LoiRender) as cm:  # bytes khác facts đã ghim → không thay mù
            R.dien_mau(khac, f, ban_do_tu_facts(f), self.GT)
        self.assertEqual(cm.exception.code, "CRM_GK_MAU_LECH_FACTS")
        f_inc = {**f, "trang_thai": "INCOMPLETE"}
        with self.assertRaises(R.LoiRender) as cm:
            R.dien_mau(raw, f_inc, ban_do_tu_facts(f), self.GT)
        self.assertEqual(cm.exception.code, "CRM_GK_MAU_CHUA_DU")

    def test_docx_bao_gia_khong_ma_noi_bo(self):
        nd = {"so_bao_gia": "BG-2026-00001", "ngay": "21/10/2026", "nguoi_lap": "MO_PHONG_CRM_G_BH_A", "het_han": None, "khach": "KHÁCH DEMO",
              "thong_tin": [("Tổng giá trị", "1.000.000.000 VND")], "lich": [("1", "30% — 300.000.000 VND", "Sự kiện: KY_HD", "")],
              "fx_cau": None, "phi_bao_tri": None, "dieu_khoan": ["Điều khoản DEMO."]}
        b = R.tao_docx_bao_gia(nd)
        R.kiem_docx_chuan_bi(b)
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            body = z.read("word/document.xml").decode("utf-8")
        for x in ("BG-2026-00001", "21/10/2026", "300.000.000 VND", "Điều khoản DEMO."):
            self.assertIn(x, body)
        self.assertIsNone(re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", body))  # không UUID/mã nội bộ


class NhaCungCapPdf(unittest.TestCase):
    def test_thieu_word_khong_spawn_giu_docx(self):
        tam = Path(tempfile.mkdtemp(prefix="ktt_gk_pdf_"))  # giữ lại
        (tam / "x.docx").write_bytes(b"PK")
        with mock.patch.object(R, "_winword_ok", lambda w: "WORD_KHONG_CO"), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("không được spawn khi thiếu nhà cung cấp")):
            kq = R.chuyen_pdf(tam, tam / "x.docx")
        self.assertEqual((kq["trang_thai"], kq["ly_do"]), ("PDF_CHUA_SAN_SANG", "WORD_KHONG_CO"))
        self.assertTrue((tam / "x.docx").is_file())

    @unittest.skipUnless(CO_DOCX, "python-docx chưa cài — skip (KHÔNG PASS)")
    def test_render_giu_docx_bat_bien_truoc_pdf(self):
        class MauGia:
            root = Path(tempfile.mkdtemp(prefix="ktt_gk_render_"))
        gk = GK.CrmGiaoKetK2(MauGia())
        nd = {"so_bao_gia": "BG-2026-00002", "ngay": "21/10/2026", "nguoi_lap": "X", "het_han": None, "khach": "K", "thong_tin": [], "lich": [],
              "fx_cau": None, "phi_bao_tri": None, "dieu_khoan": ["DK"]}
        with mock.patch.object(R, "chuyen_pdf", lambda lan, p, han=0: {"trang_thai": "PDF_CHUA_SAN_SANG", "ly_do": "WORD_KHONG_CO", "pha": "X"}):
            kq = gk.render({"loai": "BAO_GIA", "nd": nd, "mong_doi": [], "ten": "BG-2026-00002", "lan_id": str(uuid.uuid4())})
        self.assertEqual((kq["trang_thai"], kq["pdf_sha"]), ("PDF_CHUA_SAN_SANG", None))
        p = gk.kho / "tep" / kq["docx_sha"]
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), kq["docx_sha"])


# ====================================================================== FIX01 — thuần, không PostgreSQL/Word
class MocTrong(unittest.TestCase):  # FIX01 #8
    def test_moc_trong_luon_canh_bao_va_in_khong_typeerror(self):
        lich = [{"lan": "1", "loai": "PERCENT", "ty_le": "30", "moc_loai": "NGAY"},  # NGAY nhưng NULL
                {"lan": "2", "loai": "PERCENT", "ty_le": "30", "moc_loai": "SU_KIEN"},  # SU_KIEN nhưng NULL
                {"lan": "3", "loai": "PERCENT", "ty_le": "40"}]  # chưa chọn loại mốc
        d = GK.chuan_hoa_bao_gia(bao_gia(lich=lich))
        t = GK.tinh_bao_gia(d, None)
        self.assertEqual(sorted(x["dong"] for x in t["canh_bao"] if x["ma"] == "MOC_TRONG"), [1, 2, 3])
        self.assertNotIn("MOC_TRONG", [x["ma"] for x in t["chan_in"]])  # chỉ cảnh báo, không chặn In
        self.assertEqual(t["chan_in"], [])
        self.assertEqual([GK._moc(r) for r in d["lich"]], ["Ngày: chưa xác định", "Sự kiện: chưa xác định", "Chưa xác định"])
        self.assertEqual([d["lich"][0]["moc_ngay"], d["lich"][1]["moc_su_kien"]], [None, None])  # giữ NULL, không tự tạo ngày/sự kiện
        self.assertEqual(GK._moc({"moc_loai": "NGAY", "moc_ngay": "2026-12-31"}), "Ngày 31/12/2026")


class TongCanonical(unittest.TestCase):  # FIX01 #7
    CH_THUE = {"kiem_tong": {"truong": "gia_tri_hop_dong", "co_so": "TIEN_THUE_DAT_CHUA_VAT"}}
    CH_BAN = {"kiem_tong": {"truong": "gia_tri_hop_dong", "co_so": "GIA_BAN_CHUA_VAT"}}

    def kiem(self, gia_tri, co_so_thue="NET", rb=None, dung=("gia_tri_hop_dong",)):
        d = GK.chuan_hoa_bao_gia(bao_gia(gia={"tien_te": "VND", "tong": "1000000000", "co_so_thue": co_so_thue}))
        t = GK.tinh_bao_gia(d, None)
        rb = GK.rang_buoc_tong(self.CH_THUE) if rb is None else rb
        return GK.kiem_tong_canonical(rb, {"gia_tri_hop_dong": gia_tri} if gia_tri else {}, d, t, set(dung))

    def test_rang_buoc_tu_profile(self):
        self.assertEqual(GK.rang_buoc_tong(self.CH_THUE), {"truong": "gia_tri_hop_dong", "co_so": "TIEN_THUE_DAT_CHUA_VAT", "co_so_thue": "NET"})
        self.assertEqual(GK.rang_buoc_tong(self.CH_BAN)["co_so_thue"], "NET")
        self.assertIsNone(GK.rang_buoc_tong({"kiem_tong": {"truong": "x", "co_so": "GIA_GOM_VAT"}})["co_so_thue"])  # không suy NET/GROSS
        for ch in (None, {}, {"kiem_tong": {"truong": "x"}}, {"kiem_tong": "x"}, "không phải dict"):
            self.assertIsNone(GK.rang_buoc_tong(ch), ch)

    def test_net_khop_qua_khong_chan(self):
        self.assertEqual(self.kiem({"so_tien": "1000000000", "tien_te": "VND"}), ([], []))

    def test_tong_khac_lich_hoac_tien_te_khac_chan(self):
        for v in ({"so_tien": "999999999", "tien_te": "VND"}, {"so_tien": "1000000000", "tien_te": "USD"}):
            chan, _ = self.kiem(v)
            self.assertEqual([x["ma"] for x in chan], ["TONG_TRUONG_KHAC_TONG_LICH"], v)

    def test_co_so_khac_chan_khong_tu_quy_doi(self):
        chan, _ = self.kiem({"so_tien": "1000000000", "tien_te": "VND"}, co_so_thue="GROSS")
        self.assertEqual([x["ma"] for x in chan], ["CO_SO_TONG_KHONG_KHOP"])
        chan, _ = self.kiem({"so_tien": "1000000000", "tien_te": "VND"}, rb={"truong": "gia_tri_hop_dong", "co_so": "LA", "co_so_thue": None})
        self.assertEqual([x["ma"] for x in chan], ["CO_SO_TONG_KHONG_KHOP"])

    def test_thieu_rang_buoc_bao_khong_doan(self):
        d = GK.chuan_hoa_bao_gia(bao_gia())
        chan, cb = GK.kiem_tong_canonical(None, {"gia_tri_hop_dong": {"so_tien": "1", "tien_te": "VND"}}, d, GK.tinh_bao_gia(d, None), {"gia_tri_hop_dong"})
        self.assertEqual((chan, [x["ma"] for x in cb]), ([], ["CHUA_CO_RANG_BUOC_TONG"]))
        self.assertEqual(self.kiem({"so_tien": "1", "tien_te": "VND"}, dung=()), ([], []))  # mẫu không có ô tổng → không kiểm

    def test_kiem_soan_profile_doi_chan_xuat(self):
        ghim = {"danh_muc": [], "ban_do": [], "facts": {}}
        k = GK.CrmGiaoKetK2.kiem_soan({"gia_tri_truong": {}, "bao_gia": {}}, ghim, {"chan_in": [], "canh_bao": []}, None, False)
        self.assertIn("PROFILE_DA_DOI", [x["ma"] for x in k["chan_xuat"]])
        self.assertIn("CHUA_CO_RANG_BUOC_TONG", [x["ma"] for x in k["canh_bao"]])


class KetLuanWorker(unittest.TestCase):  # FIX01 #9/#11 — tiêm lỗi kết luận của parent
    def setUp(self):
        self.tam = Path(tempfile.mkdtemp(prefix="ktt_gk_kl_"))  # giữ lại
        self.pdf = self.tam / "hd.pdf"
        self.pdf.write_bytes(b"%PDF-1.7 tiem loi")
        self.pid = {"pid": 4242, "gan_job": True}
        self.ok = {"kieu": "x", "trang_thai": "PDF_DA_TAO", "pha": "XUAT", "word": {"pid": 4242, "da_dung": True}}

    def test_duong_tinh_duy_nhat(self):
        kq = R._ket_luan(self.ok, self.pid, 0, True, self.pdf, "CHO_WORKER")
        self.assertEqual((kq["trang_thai"], kq["pdf"]), ("PDF_DA_TAO", str(self.pdf)))

    def test_moi_loi_khong_thanh_cong_va_giu_bang_chung(self):
        ca = {
            "báo thành công nhưng dừng = False": ({**self.ok, "word": {"pid": 4242, "da_dung": False}}, self.pid, 0, True),
            "báo thành công nhưng dừng = chưa rõ": ({**self.ok, "word": {"pid": 4242, "da_dung": None}}, self.pid, 0, True),
            "báo thành công nhưng thiếu da_dung": ({**self.ok, "word": {"pid": 4242}}, self.pid, 0, True),
            "mã thoát lỗi": (self.ok, self.pid, 5, True),
            "không có mã thoát": (self.ok, self.pid, None, True),
            "EOF/quá hạn (không báo xong)": (None, self.pid, 0, True),
            "Job chưa rỗng": (self.ok, self.pid, 0, False),
            "PID báo cáo khác PID đã chứng minh": ({**self.ok, "word": {"pid": 9999, "da_dung": True}}, self.pid, 0, True),
            "PID chưa gán Job": (self.ok, {"pid": 4242, "gan_job": False}, 0, True),
            "không chứng minh PID": (self.ok, {}, 0, True),
        }
        for ten, (xong, wp, ma, job) in ca.items():
            kq = R._ket_luan(xong, wp, ma, job, self.pdf, "CHO_WORKER")
            self.assertNotEqual(kq["trang_thai"], "PDF_DA_TAO", ten)
            self.assertEqual(kq["trang_thai"], "PDF_LOI", ten)
            self.assertTrue(self.pdf.is_file(), ten)  # PDF có sẵn vẫn GIỮ làm bằng chứng, không xóa
        kq = R._ket_luan({**self.ok, "word": {"pid": 4242, "da_dung": None}}, self.pid, 0, True, self.pdf, "X")
        self.assertEqual((kq["ly_do"], kq["pdf_giu"]), ("WORD_CHUA_XAC_NHAN_DUNG", str(self.pdf)))
        self.assertEqual(R._ket_luan(None, self.pid, 0, True, self.pdf, "X")["ly_do"], "WORKER_QUA_HAN_HOAC_EOF")
        self.assertEqual(R._ket_luan(self.ok, self.pid, 0, False, self.pdf, "X")["ly_do"], "WORKER_CHUA_DUNG")

    def test_pdf_khong_ton_tai_khong_thanh_cong(self):
        kq = R._ket_luan(self.ok, self.pid, 0, True, self.tam / "khong_co.pdf", "X")
        self.assertEqual((kq["trang_thai"], kq["pdf_giu"]), ("PDF_LOI", None))

    def test_khong_so_huu_la_chua_san_sang(self):
        kq = R._ket_luan({"trang_thai": "LOI", "ly_do": "KHONG_SO_HUU:CHUA_CHUNG_MINH_DOI_TUONG_COM", "pha": "CHUNG_MINH_SO_HUU",
                          "word": {"pid_quan_sat": 77, "da_dung": None}}, {}, 5, True, self.tam / "khong_co.pdf", "X")
        self.assertEqual(kq["trang_thai"], "PDF_CHUA_SAN_SANG")

    def test_so_huu_word_theo_binding_fix02(self):  # FIX02 — tĩnh trên mã nguồn (không chạy Word)
        src = (SRC / "nguon" / "crm_docx.py").read_text(encoding="utf-8")
        # không đường kích hoạt/attach thay thế, không marker tiêu đề/FindWindow, không đặt Hwnd
        self.assertIsNone(re.search(r"DispatchEx\(|GetObject\(|GetActiveObject\(|\.Caption\b|FindWindow\w*\(|Hwnd\s*=|NtResumeProcess|BREAKAWAY", src))
        self.assertEqual(R.LENH_WORD, '"{ww}" /w')  # đúng binary + MỘT switch /w
        self.assertNotRegex(src, r"(?m)^(import|from)\s+(pythoncom|win32com)")  # import module/server không kích hoạt COM
        tao = src[src.index("    def tao(self"):src.index("    def con_song(")]
        thu_tu = ["CreateProcessW(", "self.job.gan(", "IsProcessInJob(", "_anh_cua_handle(", "ResumeThread("]
        self.assertEqual([tao.index(x) for x in thu_tu], sorted(tao.index(x) for x in thu_tu))  # Job + danh tính TRƯỚC ResumeThread
        self.assertIn("0x00000004", tao)  # CREATE_SUSPENDED
        self.assertIn("si.dwFlags, si.wShowWindow = 0x00000001, 0", tao)  # STARTF_USESHOWWINDOW + SW_HIDE
        self.assertNotIn("pythoncom", tao)
        cm = src[src.index("    def chung_minh(self"):src.index("    def dung(self")]
        for x in ("import pythoncom", "_native_window(", "_pid_cua_hwnd(int(w.Hwnd)) != self.pid", "IsProcessInJob(", "self.app = w.Application"):
            self.assertIn(x, cm)
        than = src[src.index("class WordSoHuu"):src.index("if __name__")]
        self.assertNotIn("_pids_winword(", than)  # không so PID trước-sau làm bằng chứng
        wk = src[src.index("def _worker("):src.index("KIEU_CONTROL = ")]
        idx = [wk.index(x) for x in ("w.tao(", "w.cho_cua_so(", "w.chung_minh(", "Documents.Open(", "w.dung()")]
        self.assertEqual(idx, sorted(idx))
        self.assertIn("if w.app is not None:", wk)  # Close/Quit CHỈ trên đối tượng đã chứng minh
        self.assertNotIn("setattr", cm)
        self.assertNotIn(".Visible", cm)

    @unittest.skipUnless(CO_DOCX, "python-docx chưa cài — skip (KHÔNG PASS)")
    def test_render_pdf_co_nhung_word_chua_dung_khong_pdf_dat(self):
        class MauGia:
            root = Path(tempfile.mkdtemp(prefix="ktt_gk_kl_render_"))
        gk = GK.CrmGiaoKetK2(MauGia())
        nd = {"so_bao_gia": "BG-2026-00003", "ngay": "21/10/2026", "nguoi_lap": "X", "het_han": None, "khach": "K", "thong_tin": [], "lich": [],
              "fx_cau": None, "phi_bao_tri": None, "dieu_khoan": ["DK"]}
        goi_kiem = []
        with mock.patch.object(R, "chuyen_pdf", lambda lan, p, han=0: {"trang_thai": "PDF_DA_TAO", "pdf": str(self.pdf), "pha": "XUAT",
                                                                     "word": {"pid": 1, "da_dung": None}}), \
                mock.patch.object(R, "kiem_pdf", lambda *a, **k: goi_kiem.append(a) or {"ok": True}):
            kq = gk.render({"loai": "BAO_GIA", "nd": nd, "mong_doi": [], "ten": "BG-2026-00003", "lan_id": str(uuid.uuid4())})
        self.assertEqual((kq["trang_thai"], kq["pdf_sha"], kq["ly_do"]), ("PDF_LOI", None, "WORD_CHUA_XAC_NHAN_DUNG"))
        self.assertEqual(goi_kiem, [])  # không kiểm/công bố PDF khi Word chưa xác nhận dừng
        self.assertTrue((gk.kho / "tep" / kq["docx_sha"]).is_file())  # DOCX giữ


class _DongHo:
    """Đồng hồ giả cho vòng chờ hữu hạn (tiến 1 s mỗi lần đọc; sleep không chờ thật) — chỉ dùng trong test thuần."""
    def __init__(self):
        self.t = 0.0

    def monotonic(self):
        self.t += 1.0
        return self.t

    def sleep(self, _s):
        pass

    def time(self):
        return 1_800_000_000.0


class _JobGia:
    def __init__(self, gan_loi=False, con=(0,), truy_van_loi=False, truy_van_bat_ngo=False):
        self.gan_loi, self.con, self.truy_van_loi, self.truy_van_bat_ngo = gan_loi, list(con), truy_van_loi, truy_van_bat_ngo
        self.da_ket_thuc = self.da_dong = 0
        self.da_gan = False

    def gan(self, proc):
        from kho_tri_thuc.nguon.trich6_host import LoiHost
        if self.gan_loi:
            raise LoiHost("JOB_GAN_LOI", "gán lỗi (tiêm)")
        self.da_gan = True

    def ket_thuc(self):
        self.da_ket_thuc += 1

    def so_tien_trinh(self):
        from kho_tri_thuc.nguon.trich6_host import LoiHost
        if self.truy_van_loi:
            raise LoiHost("JOB_TRUY_VAN_LOI", "truy vấn lỗi (tiêm)")
        if self.truy_van_bat_ngo:
            raise RuntimeError("truy vấn bất ngờ (tiêm)")
        return self.con.pop(0) if len(self.con) > 1 else self.con[0]

    def dong(self):
        self.da_dong += 1


class _LuongGia:
    def __init__(self, loi_ghi=False):
        self.loi_ghi, self.da_ghi = loi_ghi, []

    def write(self, b):
        if self.loi_ghi:
            raise BrokenPipeError("stdin đóng (tiêm)")
        self.da_ghi.append(b)

    def flush(self):
        pass

    def close(self):
        pass


class _ProcGia:
    def __init__(self, ma=0, treo=False, loi_ghi=False, loi_wait=None):
        self.stdin, self.stdout, self._handle = _LuongGia(loi_ghi), _LuongGia(), 99
        self.returncode, self.treo, self.da_kill, self.loi_wait, self.so_wait = ma, treo, 0, loi_wait, 0

    def wait(self, t=None):
        import subprocess
        self.so_wait += 1
        if self.loi_wait is not None:
            raise self.loi_wait
        if self.treo:
            raise subprocess.TimeoutExpired("worker", t)
        return self.returncode

    def kill(self):
        self.da_kill += 1


class VongDoiParent(unittest.TestCase):  # FIX02 — tiêm lỗi MỌI nhánh parent: luôn dừng cây đã sở hữu + bằng chứng hữu hạn hoặc UNKNOWN
    def chay(self, job, proc, dong=(), pdf_co=False, pdf_sau=False, pdf_som=False, loi_doc=None):
        """pdf_co: PDF có TRƯỚC khi spawn (đường dẫn lần chạy không mới); pdf_sau: "worker" tạo PDF ngay trước khi báo xong; pdf_som: PDF xuất hiện
        ngay lần đọc đầu (FIX03 R4: file tồn tại KHÔNG được biến kết quả sai giao thức thành thành công); loi_doc: ngoại lệ ném khi đọc dòng."""
        from kho_tri_thuc.nguon import trich6_host as H
        lan = Path(tempfile.mkdtemp(prefix="ktt_gk_vd_"))  # giữ lại
        (lan / "hd.docx").write_bytes(b"PK docx tiem")
        if pdf_co:
            (lan / "hd.pdf").write_bytes(b"%PDF-1.7 worker da tao")
        it = iter(dong)

        def doc(_s, _han):
            if pdf_som and not (lan / "hd.pdf").exists():
                (lan / "hd.pdf").write_bytes(b"%PDF-1.7 co som")
            if loi_doc is not None:
                raise loi_doc
            v = next(it, None)
            if v is not None and pdf_sau and R.KIEU_WORKER_XONG.encode() in v:
                (lan / "hd.pdf").write_bytes(b"%PDF-1.7 worker da tao")
            return v
        popen = mock.Mock(return_value=proc)
        with mock.patch.object(R, "_winword_ok", lambda w: None), mock.patch.object(R, "time", _DongHo()), \
                mock.patch.object(H, "chung_cu_guard", lambda *a, **k: {}), mock.patch.object(H, "guard_hop_le", lambda *a, **k: None), \
                mock.patch.object(H, "_JobWindows", lambda: job), mock.patch.object(H, "_doc_dong", doc), \
                mock.patch("subprocess.Popen", popen):
            return R._chuyen_pdf_mot(lan, lan / "hd.docx", 180, R.WINWORD_GHIM), popen, lan

    @staticmethod
    def dong(**v):
        return json.dumps(v).encode("utf-8")

    def test_gan_job_loi_khong_ghi_stdin_dung_dung_handle(self):
        job, proc = _JobGia(gan_loi=True), _ProcGia(ma=1)
        kq, _, _ = self.chay(job, proc)
        self.assertEqual((kq["trang_thai"], kq["ly_do"], kq["dung"]), ("PDF_LOI", "JOB_GAN_LOI", "DA_DUNG"))
        self.assertEqual((proc.stdin.da_ghi, proc.da_kill, job.da_ket_thuc), ([], 1, 0))  # chưa gán Job → không cấu hình; dừng đúng handle
        self.assertEqual(job.da_dong, 1)

    def test_eof_va_qua_han_dung_job_va_xac_nhan_rong(self):
        pid = self.dong(kieu=R.KIEU_WORKER_PID, pid=4242, gan_job=True)
        for dong in ((), (pid,)):  # EOF ngay / có PID rồi EOF-quá hạn
            job, proc = _JobGia(con=(1, 0)), _ProcGia(ma=1)
            kq, _, _ = self.chay(job, proc, dong)
            self.assertEqual((kq["trang_thai"], kq["ly_do"]), ("PDF_LOI", "WORKER_QUA_HAN_HOAC_EOF"), dong)
            self.assertEqual(job.da_ket_thuc, 1)
            self.assertEqual(len(proc.stdin.da_ghi), 1)  # cấu hình chỉ ghi SAU khi gán Job
            if dong:
                self.assertIs(kq["word"]["da_dung"], True)  # Job rỗng ⇒ Word (con không breakaway) đã dừng

    def test_job_khong_rong_hoac_truy_van_loi_hoac_worker_treo_la_unknown(self):
        xong = self.dong(kieu=R.KIEU_WORKER_XONG, trang_thai="PDF_DA_TAO", pha="XUAT", word={"pid": 4242, "da_dung": True})
        pid = self.dong(kieu=R.KIEU_WORKER_PID, pid=4242, gan_job=True)
        for ten, job, proc in (("job còn tiến trình", _JobGia(con=(1,)), _ProcGia()), ("truy vấn Job lỗi", _JobGia(truy_van_loi=True), _ProcGia()),
                               ("worker treo", _JobGia(), _ProcGia(treo=True))):
            kq, _, _ = self.chay(job, proc, (pid, xong), pdf_sau=True)
            self.assertEqual((kq["trang_thai"], kq.get("dung")), ("PDF_LOI", "UNKNOWN"), ten)
            self.assertTrue(kq["ly_do"], ten)

    def test_stdin_loi_van_dung_cay(self):
        job, proc = _JobGia(), _ProcGia(ma=1, loi_ghi=True)
        kq, _, _ = self.chay(job, proc)
        self.assertEqual((kq["trang_thai"], kq["dung"]), ("PDF_LOI", "DA_DUNG"))
        self.assertTrue(kq["ly_do"].startswith("CAU_HINH:"), kq)
        self.assertEqual(job.da_ket_thuc, 1)

    def test_pdf_ton_tai_truoc_khong_spawn(self):
        job, proc = _JobGia(), _ProcGia()
        kq, popen, lan = self.chay(job, proc, pdf_co=True)
        self.assertEqual((kq["trang_thai"], kq["ly_do"]), ("PDF_LOI", "DUONG_DAN_LAN_KHONG_MOI"))
        popen.assert_not_called()
        self.assertEqual((lan / "hd.pdf").read_bytes(), b"%PDF-1.7 worker da tao")  # không ghi đè/xóa

    def test_bao_dung_false_hoac_chua_ro_khong_thanh_cong(self):
        pid = self.dong(kieu=R.KIEU_WORKER_PID, pid=4242, gan_job=True)
        for dd in (False, None):
            xong = self.dong(kieu=R.KIEU_WORKER_XONG, trang_thai="PDF_DA_TAO", pha="XUAT", word={"pid": 4242, "da_dung": dd})
            kq, _, lan = self.chay(_JobGia(), _ProcGia(), (pid, xong), pdf_sau=True)
            self.assertEqual((kq["trang_thai"], kq["ly_do"]), ("PDF_LOI", "WORD_CHUA_XAC_NHAN_DUNG"), dd)
            self.assertTrue((lan / "hd.pdf").is_file())  # PDF giữ làm bằng chứng

    def test_duong_tinh_day_du(self):
        pid = self.dong(kieu=R.KIEU_WORKER_PID, pid=4242, gan_job=True)
        xong = self.dong(kieu=R.KIEU_WORKER_XONG, trang_thai="PDF_DA_TAO", pha="XUAT", word={"pid": 4242, "da_dung": True})
        job = _JobGia()
        kq, _, _ = self.chay(job, _ProcGia(), (pid, xong), pdf_sau=True)
        self.assertEqual(kq["trang_thai"], "PDF_DA_TAO", kq)
        self.assertEqual(job.da_ket_thuc, 0)  # worker tự thoát; Job xác nhận rỗng, không cần kết thúc cưỡng bức

    def test_giao_thuc_sai_hinh_dang_dung_cay_va_khong_thanh_cong(self):  # FIX03 R4
        pid = self.dong(kieu=R.KIEU_WORKER_PID, pid=4242, gan_job=True)
        xong_ok = dict(kieu=R.KIEU_WORKER_XONG, trang_thai="PDF_DA_TAO", pha="XUAT", word={"pid": 4242, "da_dung": True})
        ca = {
            "JSON list": (b"[]",), "JSON số": (b"5",), "JSON null": (b"null",), "JSON chuỗi": (b'"x"',), "không phải JSON": (b"xyz{",),
            "không phải UTF-8": (b"\xff\xfe",), "kiểu lạ": (self.dong(kieu="la", pid=1),),
            "PID chuỗi": (self.dong(kieu=R.KIEU_WORKER_PID, pid="4242", gan_job=True),),
            "PID bool": (self.dong(kieu=R.KIEU_WORKER_PID, pid=True, gan_job=True),),
            "PID 0": (self.dong(kieu=R.KIEU_WORKER_PID, pid=0, gan_job=True),),
            "PID chưa gán Job": (self.dong(kieu=R.KIEU_WORKER_PID, pid=4242, gan_job=False),),
            "PID gan_job không bool": (self.dong(kieu=R.KIEU_WORKER_PID, pid=4242, gan_job=1),),
            "PID hai lần": (pid, pid),
            "XONG trạng thái lạ": (pid, self.dong(**{**xong_ok, "trang_thai": "OK"})),
            "XONG word list": (pid, self.dong(**{**xong_ok, "word": []})),
            "XONG word.pid chuỗi": (pid, self.dong(**{**xong_ok, "word": {"pid": "4242", "da_dung": True}})),
            "XONG da_dung lạ": (pid, self.dong(**{**xong_ok, "word": {"pid": 4242, "da_dung": "yes"}})),
            "XONG ly_do số": (pid, self.dong(**{**xong_ok, "ly_do": 5})),
        }
        for ten, dong in ca.items():
            job, proc = _JobGia(), _ProcGia()
            kq, _, lan = self.chay(job, proc, dong, pdf_som=True)  # PDF CÓ trên đĩa — không được thành thành công
            self.assertEqual((kq["trang_thai"], kq["dung"]), ("PDF_LOI", "DA_DUNG"), ten)
            self.assertTrue(kq["ly_do"].startswith("GIAO_THUC_"), (ten, kq))
            self.assertEqual(kq["pha"], "CHO_WORKER", ten)
            self.assertEqual(job.da_ket_thuc, 1, ten)  # dừng cây đã sở hữu, không chỉ CloseHandle
            self.assertTrue((lan / "hd.pdf").is_file(), ten)  # PDF giữ làm bằng chứng
        # dừng chưa xác nhận trên đường giao thức sai → UNKNOWN (không che)
        kq, _, _ = self.chay(_JobGia(con=(1,)), _ProcGia(), (b"[]",), pdf_som=True)
        self.assertEqual((kq["trang_thai"], kq["ly_do"], kq["dung"]), ("PDF_LOI", "GIAO_THUC_SAI_KIEU", "UNKNOWN"))

    def test_ngoai_le_bat_ngo_doc_wait_truy_van(self):  # FIX03 R4
        pid = self.dong(kieu=R.KIEU_WORKER_PID, pid=4242, gan_job=True)
        xong = self.dong(kieu=R.KIEU_WORKER_XONG, trang_thai="PDF_DA_TAO", pha="XUAT", word={"pid": 4242, "da_dung": True})
        job = _JobGia()
        kq, _, _ = self.chay(job, _ProcGia(), loi_doc=RuntimeError("đọc bất ngờ"), pdf_som=True)
        self.assertEqual((kq["trang_thai"], kq["dung"]), ("PDF_LOI", "DA_DUNG"))
        self.assertEqual(kq["ly_do"], "CHO_WORKER:NGOAI_LE_BAT_NGO:RuntimeError")
        self.assertEqual(job.da_ket_thuc, 1)
        for ten, job, proc in (("wait bất ngờ", _JobGia(), _ProcGia(loi_wait=RuntimeError("wait"))),
                               ("truy vấn Job bất ngờ", _JobGia(truy_van_bat_ngo=True), _ProcGia())):
            kq, _, lan = self.chay(job, proc, (pid, xong), pdf_sau=True)
            self.assertEqual((kq["trang_thai"], kq["dung"]), ("PDF_LOI", "UNKNOWN"), ten)  # file có nhưng dừng không xác nhận → không thành công
            self.assertTrue((lan / "hd.pdf").is_file(), ten)
        kq, _, _ = self.chay(_JobGia(), _ProcGia(loi_wait=RuntimeError("wait")), loi_doc=RuntimeError("đọc"))
        self.assertEqual((kq["ly_do"], kq["dung"]), ("CHO_WORKER:NGOAI_LE_BAT_NGO:RuntimeError", "UNKNOWN"))  # giữ lỗi gốc + UNKNOWN

    def test_doc_giao_thuc_duong_tinh(self):  # FIX03 R4 — hợp đồng gốc vẫn nhận
        k, v = R._doc_giao_thuc(self.dong(kieu=R.KIEU_WORKER_PID, pid=7, gan_job=True), da_co_pid=False)
        self.assertEqual((k, v["pid"]), (R.KIEU_WORKER_PID, 7))
        for w in ({"pid": 7, "da_dung": True}, {"pid": 7, "gan_job": True, "da_dung": None}, {"pid_quan_sat": 7}, None):
            k, v = R._doc_giao_thuc(self.dong(kieu=R.KIEU_WORKER_XONG, trang_thai="LOI", ly_do="KHONG_SO_HUU:X", pha="CHO_CUA_SO", word=w), da_co_pid=True)
            self.assertEqual(k, R.KIEU_WORKER_XONG, w)
        k, _ = R._doc_giao_thuc(self.dong(kieu=R.KIEU_WORKER_XONG, trang_thai="LOI", ly_do="CAU_HINH_SAI", pha="CAU_HINH"), da_co_pid=False)
        self.assertEqual(k, R.KIEU_WORKER_XONG)


class _K32Gia:
    def __init__(self, signal=(True,)):
        self.signal, self.da_terminate, self.da_dong = list(signal), [], []

    def WaitForSingleObject(self, h, ms):
        s = self.signal.pop(0) if len(self.signal) > 1 else self.signal[0]
        return 0 if s else 0x102

    def TerminateProcess(self, h, ma):
        self.da_terminate.append(h)
        return True

    def CloseHandle(self, h):
        self.da_dong.append(h)


class DungWordSoHuu(unittest.TestCase):  # FIX02 — dừng Word đã sở hữu: chỉ handle/Job của chính nó, có hạn, bằng chứng hoặc UNKNOWN
    def w(self, k, job, gan=True, quit_da_goi=True, hp=11):
        w = R.WordSoHuu(Path("WINWORD.EXE"), Path("."))
        w.k, w.job, w.hp, w.ht, w.pid, w.gan, w.quit_da_goi = k, job, hp, 12 if hp else None, 4242 if hp else None, gan, quit_da_goi
        return w

    def test_cac_nhanh(self):
        with mock.patch.object(R, "time", _DongHo()):
            k, job = _K32Gia(), _JobGia()
            self.assertIs(self.w(k, job).dung(), True)  # Quit → handle signaled + Job rỗng
            self.assertEqual((job.da_ket_thuc, sorted(k.da_dong), job.da_dong), (0, [11, 12], 1))
            k, job = _K32Gia(signal=(False, True)), _JobGia()
            self.assertIs(self.w(k, job).dung(), True)  # Quit không dừng trong hạn → kết thúc ĐÚNG Job → signaled
            self.assertEqual(job.da_ket_thuc, 1)
            k, job = _K32Gia(signal=(True,)), _JobGia()
            self.assertIs(self.w(k, job, quit_da_goi=False).dung(), True)  # chưa chứng minh → không Quit, dừng bằng Job
            self.assertEqual(job.da_ket_thuc, 1)
            self.assertIsNone(self.w(_K32Gia(signal=(False,)), _JobGia()).dung())  # không signaled → UNKNOWN
            self.assertIsNone(self.w(_K32Gia(), _JobGia(con=(1,))).dung())  # Job không rỗng trong hạn → UNKNOWN
            self.assertIsNone(self.w(_K32Gia(), _JobGia(truy_van_loi=True)).dung())  # truy vấn lỗi → UNKNOWN
            k, job = _K32Gia(signal=(True,)), _JobGia()
            self.assertIs(self.w(k, job, gan=False, quit_da_goi=False).dung(), True)  # chưa gán Job → TerminateProcess đúng handle
            self.assertEqual((k.da_terminate, job.da_ket_thuc), ([11], 0))
            job = _JobGia()
            self.assertIs(self.w(_K32Gia(), job, hp=None).dung(), True)  # CreateProcessW chưa tạo được → không có Word
            self.assertEqual(job.da_dong, 1)


class _Tp:
    def __init__(self, t):
        self.t = t

    def get_text_range(self, errors="strict"):
        return self.t

    def close(self):
        pass


class _Bm:
    width = height = 1

    def close(self):
        pass


class _Pg:
    def __init__(self, t):
        self.t, self.chars = t, [{"fontname": "ArialMT"}]

    def get_textpage(self):
        return _Tp(self.t)

    def render(self):
        return _Bm()

    def extract_text(self):
        return self.t

    def close(self):
        pass


def _pdf_gia(trang: list[str], trang2: list[str] | None = None):
    """Mô-đun pypdfium2/pdfplumber GIẢ (chỉ trong test thuần) trả đúng văn bản trang đã cho — kiểm logic đếm/so khớp, không phải PDF thật.
    `trang2` (FIX03 R3): trang của pdfplumber nếu khác PDFium (giả lập lệch số trang giữa hai bộ đọc)."""
    trang2 = trang if trang2 is None else trang2
    class Doc:
        def __init__(self, _p):
            pass

        def __len__(self):
            return len(trang)

        def get_page(self, i):
            return _Pg(trang[i])

        def close(self):
            pass

    class P2:
        pages = [_Pg(t) for t in trang2]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    return {"pypdfium2": types.SimpleNamespace(PdfDocument=Doc), "pdfplumber": types.SimpleNamespace(open=lambda p, unicode_norm=None: P2())}


class KiemPdfDem(unittest.TestCase):  # FIX01 #12
    def kiem(self, trang, mong, trang2=None):
        p = Path(tempfile.mkdtemp(prefix="ktt_gk_pdfdem_")) / "x.pdf"
        p.write_bytes(b"%PDF-1.7 gia")
        with mock.patch.dict(sys.modules, _pdf_gia(trang, trang2)):
            return R.kiem_pdf(p, mong)

    def test_so_trang_tach_khoi_so_lan(self):  # FIX03 R3: số trang trả về là số trang THẬT, không bị số lần kỳ vọng cuối cùng ghi đè
        # 1 trang, mục cuối cần 2 lần (≠ số trang)
        k = self.kiem(["Phí 0 VND, giảm 0 VND"], [("VND", 1), ("0", 2)])
        self.assertTrue(k["ok"], k)
        self.assertEqual((k["so_trang"], k["so_trang_pdfplumber"]), (1, 1))
        # 3 trang, mục cuối cần 1 lần
        k = self.kiem(["Trang một HĐ-9", "Trang hai", "Trang ba HĐ-9"], [("HĐ-9", 2), ("Trang ba", 1)])
        self.assertTrue(k["ok"], k)
        self.assertEqual((k["so_trang"], k["so_trang_pdfplumber"]), (3, 3))
        # 2 trang, mục cuối cần 5 lần → thiếu → không đạt, số trang vẫn đúng
        k = self.kiem(["A 1 1", "B 1 1"], [("1", 5)])
        self.assertEqual((k["ok"], k["so_trang"], k["so_trang_pdfplumber"], k["thieu_pdfium"]), (False, 2, 2, ["1"]))
        # lệch số trang giữa hai bộ đọc → không đạt dù đủ nội dung
        k = self.kiem(["HĐ-9", "HĐ-9"], [("HĐ-9", 1)], trang2=["HĐ-9 HĐ-9"])
        self.assertEqual((k["ok"], k["so_trang"], k["so_trang_pdfplumber"]), (False, 2, 1))
        self.assertEqual(k["muc_kiem"], "VAN_BAN_CO_BAN")
        # trang PDFium rỗng → không đạt
        self.assertFalse(self.kiem(["HĐ-9", "   "], [("HĐ-9", 1)])["ok"])

    def test_dem_so_lan_va_gia_tri_ngan(self):
        trang = ["Hợp đồng số HĐ-1 ký 21/10/2026 — giá 7 VND", "Số HĐ: HĐ-1 · Trang cuối 21/10/2026"]
        k = self.kiem(trang, [("HĐ-1", 2), ("21/10/2026", 2), ("7", 1), "VND"])
        self.assertTrue(k["ok"], k)
        self.assertEqual(k["muc_kiem"], "VAN_BAN_CO_BAN")  # chỉ kiểm văn bản cơ bản — không fidelity bố cục/glyph
        k = self.kiem(trang, [("HĐ-1", 3)])  # header thiếu một lần xuất hiện → không đạt
        self.assertFalse(k["ok"])
        self.assertEqual(k["thieu_pdfium"], ["HĐ-1"])
        k = self.kiem(trang, [("Q", 1)])  # giá trị 1 ký tự vắng → không đạt (không bỏ giá trị ngắn)
        self.assertEqual((k["ok"], k["thieu_pdfplumber"]), (False, ["Q"]))

    def test_cong_so_lan_cua_muc_trung_van_ban(self):  # FIX02: cộng, không max/không khử trùng
        mong = [("0", 1), ("0", 1)]  # hai trường khác nhau cùng hiển thị "0", mỗi trường một ô
        k = self.kiem(["Phí: 0 VND", "Giảm: VND"], mong)  # chỉ MỘT "0"
        self.assertEqual((k["ok"], k["thieu_pdfium"], k["thieu_pdfplumber"]), (False, ["0"], ["0"]))
        self.assertTrue(self.kiem(["Phí: 0 VND", "Giảm: 0 VND"], mong)["ok"])  # hai "0" → đạt
        mong = [("HĐ-1", 1), ("HĐ - 1", 1)]  # trùng SAU chuẩn hóa khoảng trắng → cộng = 2
        self.assertFalse(self.kiem(["Số HĐ-1"], mong)["ok"])
        self.assertTrue(self.kiem(["Số HĐ-1", "Đầu trang HĐ-1"], mong)["ok"])
        mong = [("Ứng", 1), ("Ứng", 1)]  # trùng SAU NFC (Ứ dạng tổ hợp) → cộng = 2
        to_hop = "U" + chr(0x31B) + chr(0x301) + "ng"  # Ứ dạng TỔ HỢP (NFD), dựng tường minh để không phụ thuộc mã hóa tệp nguồn
        mong = [(unicodedata.normalize("NFC", to_hop), 1), (to_hop, 1)]
        self.assertNotEqual(mong[0][0], mong[1][0])
        self.assertFalse(self.kiem(["Ứng trước"], mong)["ok"])
        self.assertTrue(self.kiem(["Ứng trước", "Ứng sau"], mong)["ok"])

    def test_cau_fx_day_du(self):
        cau = "Tỷ giá tham chiếu USD/VND = 25100.5 (ngày 20/10/2026), do MO_PHONG_CRM_G_BH_A nhập ngày 21/10/2026; giá trị VND tương đương 30988073.28 VND"
        self.assertTrue(self.kiem([cau[:60], cau[60:]], [(cau, 1)])["ok"])  # ngắt dòng/trang trong câu vẫn đối chiếu sau chuẩn hóa khoảng trắng
        self.assertFalse(self.kiem([cau.replace("25100.5", "25100")], [(cau, 1)])["ok"])


class DatChoRender(unittest.TestCase):  # FIX01 #5 — phần pha B của đặt chỗ bền (phần SQL kiểm ở HTTP g08)
    ND = {"so_bao_gia": "BG-2026-00004", "ngay": "21/10/2026", "nguoi_lap": "X", "het_han": None, "khach": "K", "thong_tin": [], "lich": [],
          "fx_cau": None, "phi_bao_tri": None, "dieu_khoan": ["DK"]}

    def gk(self):
        class MauGia:
            root = Path(tempfile.mkdtemp(prefix="ktt_gk_lan_"))
        return GK.CrmGiaoKetK2(MauGia())

    @unittest.skipUnless(CO_DOCX, "python-docx chưa cài — skip (KHÔNG PASS)")
    def test_mot_lan_mot_thu_muc_khong_render_chong_va_doi_soat(self):
        gk, lan_id, goi = self.gk(), str(uuid.uuid4()), []

        def pdf(lan, p, han=0):
            goi.append(str(lan))
            return {"trang_thai": "PDF_CHUA_SAN_SANG", "ly_do": "WORD_KHONG_CO", "pha": "X"}
        kh = {"loai": "BAO_GIA", "nd": self.ND, "mong_doi": [], "ten": "BG-2026-00004", "lan_id": lan_id}
        with mock.patch.object(R, "chuyen_pdf", pdf):
            kq = gk.render(kh)
            self.assertEqual(goi, [str(gk.kho / "lan" / lan_id)])  # thư mục = định danh lần đã đặt chỗ (không UUID mới)
            luu = json.loads((gk.kho / "lan" / lan_id / "ket_qua.json").read_text(encoding="utf-8"))
            self.assertEqual((luu["docx_sha"], luu["trang_thai"], luu["kiem"]["lan_id"]), (kq["docx_sha"], kq["trang_thai"], lan_id))
            with self.assertRaises(FileExistsError):  # cùng lần chạy lại không đối soát → không render chồng
                gk.render(kh)
            lai = gk.render({**kh, "doi_soat": luu})  # đối soát: trả kết quả đã giữ, không render/Word lần hai
        self.assertEqual((lai, len(goi)), (luu, 1))
        self.assertEqual(sorted(x.name for x in (gk.kho / "lan").iterdir()), [lan_id])

    def test_doi_soat_loi_da_ghi_tra_dung_loi(self):
        with self.assertRaises(DataError) as cm:
            self.gk().render({"lan_id": str(uuid.uuid4()), "doi_soat": {"loi_ma": "CRM_GK_O_CHUA_ANH_XA", "loi": "x"}})
        self.assertEqual(cm.exception.code, "CRM_GK_O_CHUA_ANH_XA")

    @unittest.skipUnless(CO_DOCX, "python-docx chưa cài — skip (KHÔNG PASS)")
    def test_loi_render_xac_dinh_ghi_ben_de_doi_soat(self):
        from kho_tri_thuc.nguon.mau_docx import doc_mau_docx
        raw = mau_docx()
        f = doc_mau_docx(raw)
        gk, lan_id = self.gk(), str(uuid.uuid4())
        kh = {"loai": "HOP_DONG", "raw": raw, "facts": f, "ban_do": ban_do_tu_facts(f, {**BAN_DO_TEN, "gia_tri": None}), "gia_tri": RenderDocx.GT,
              "mong_doi": [], "ten": "HD", "lan_id": lan_id}
        with mock.patch.object(R, "chuyen_pdf", side_effect=AssertionError("không được gọi Word khi DOCX lỗi")):
            with self.assertRaises(DataError) as cm:
                gk.render(kh)
        self.assertEqual(cm.exception.code, "CRM_GK_O_CHUA_ANH_XA")
        luu = json.loads((gk.kho / "lan" / lan_id / "ket_qua.json").read_text(encoding="utf-8"))
        self.assertEqual(luu["loi_ma"], "CRM_GK_O_CHUA_ANH_XA")


def _co_word():
    """CHỈ METADATA (FIX02): binary ghim (hash) + module có mặt (find_spec, KHÔNG import pythoncom/win32com — import có thể khởi tạo COM ở tiến
    trình test chính) + guard. Không kích hoạt Word/COM."""
    import importlib.util
    if os.name != "nt" or not CO_DOCX or R._winword_ok(R.WINWORD_GHIM) is not None:
        return False
    if any(importlib.util.find_spec(m) is None for m in ("pdfplumber", "pypdfium2", "win32com", "pythoncom")):
        return False
    from kho_tri_thuc.nguon.trich6_host import chung_cu_guard, guard_hop_le
    return guard_hop_le(chung_cu_guard()) is None


class _ConSoHuu:
    """Native child DO TEST SỞ HỮU (FIX02): Job gán TRƯỚC khi ghi stdin, đọc có hạn, dừng cây có bằng chứng qua `crm_docx._dung_cay`.
    Test chính không gọi COM nào (không activation/Open/Quit đồng bộ có thể treo)."""

    def __init__(self, che_do: str, cfg: dict):
        import subprocess

        from kho_tri_thuc.nguon.trich6_host import _JobWindows, env_con
        self.job, self.proc, self.gan = _JobWindows(), None, False
        try:
            self.proc = subprocess.Popen([sys.executable, "-X", "utf8", "-m", "kho_tri_thuc.nguon.crm_docx", che_do], stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=cfg["goc"], env=env_con(), close_fds=True,
                                         creationflags=0x08000000)
            self.job.gan(self.proc)
            self.gan = True
            self.gui(json.dumps(cfg, ensure_ascii=False))
        except BaseException:
            self.dung(ket_thuc=True)
            raise

    def gui(self, dong: str):
        self.proc.stdin.write((dong + "\n").encode("utf-8"))
        self.proc.stdin.flush()

    def doc(self, han: float):
        from kho_tri_thuc.nguon.trich6_host import _doc_dong
        d = _doc_dong(self.proc.stdout, han)
        return json.loads(d.decode("utf-8")) if d else None

    def dung(self, *, ket_thuc: bool):
        try:
            return R._dung_cay(self.job, self.proc, self.gan, ket_thuc=ket_thuc)
        finally:
            if self.proc is not None:
                for s in (self.proc.stdin, self.proc.stdout):
                    try:
                        s.close()
                    except OSError:
                        pass
            self.job.dong()


@unittest.skipUnless(_co_word(), "Thiếu Word đã ghim/pywin32/PDFium/pdfplumber/guard A517 — Word thật không chạy (skip, KHÔNG PASS)")
class WordThat(unittest.TestCase):
    """THẬT: Word COM sở hữu → PDF; Word của người dùng mở sẵn vẫn sống, tài liệu không đổi; quá hạn → không báo thành công, không dư tiến trình."""

    def chuan_bi(self):
        from kho_tri_thuc.nguon.mau_docx import doc_mau_docx
        raw = mau_docx()
        f = doc_mau_docx(raw)
        out, _ = R.dien_mau(raw, f, ban_do_tu_facts(f), RenderDocx.GT)
        lan = Path(tempfile.mkdtemp(prefix="ktt_gk_word_"))
        (lan / "hd.docx").write_bytes(out)
        return lan

    def test_docx_sang_pdf_that_kiem_noi_dung(self):
        # FIX02 #11/binding: "Word người dùng" CONTROL tổng hợp của test chạy trong native child do test sở hữu (Job trước stdin, hạn cứng, dừng có
        # bằng chứng); child tự tạo/sở hữu/chứng minh Word y như worker TRƯỚC Open. Test chính KHÔNG gọi COM. Word có sẵn của người dùng chỉ xem
        # metadata PID (không đọc/không chạm). Không sở hữu được control → skip NOT_VERIFIED (KHÔNG PASS).
        goc = Path(tempfile.mkdtemp(prefix="ktt_gk_control_"))  # giữ lại
        tep = goc / "cua_nguoi_dung.docx"
        tep.write_bytes(mau_docx())
        truoc, pids_co_san = tep.read_bytes(), R._pids_winword()
        con = _ConSoHuu("--word-control", {"goc": str(goc), "vao": str(tep), "winword": str(R.WINWORD_GHIM), "han_cua_so": 60})
        san_sang = xong = lan = None
        dung = None
        try:
            het = time.monotonic() + 120
            while time.monotonic() < het:
                v = con.doc(max(0.1, het - time.monotonic()))
                if v is None or v.get("buoc") in ("SAN_SANG", "XONG"):
                    san_sang = v
                    break
            if not san_sang or san_sang.get("buoc") != "SAN_SANG":
                self.skipTest(f"Control Word của test chưa sở hữu/chứng minh được (NOT_VERIFIED, không PASS): {san_sang}")
            lan = self.chuan_bi()
            kq = R.chuyen_pdf(lan, lan / "hd.docx", han=180)
            self.assertEqual(kq["trang_thai"], "PDF_DA_TAO", kq)
            self.assertIs(kq["word"].get("da_dung"), True, kq)
            self.assertNotEqual(kq["word"]["pid"], san_sang["pid"])  # worker chỉ chạm Word của chính nó
            k = R.kiem_pdf(Path(kq["pdf"]), [("HĐ-DEMO-0001", 2), ("NGƯỜI MUA DEMO", 1), ("1.000.000.000 VND", 1), ("21/10/2026", 2)])
            self.assertTrue(k["ok"], k)
            self.assertEqual(k["muc_kiem"], "VAN_BAN_CO_BAN")
            self.assertGreater(k["so_trang"], 0)
            con.gui("KIEM")
            kiem = con.doc(60)
            self.assertEqual((kiem or {}).get("buoc"), "KIEM", kiem)
            self.assertEqual((kiem["so_tai_lieu"], kiem["ten"], kiem["song"]), (san_sang["so_tai_lieu"], "cua_nguoi_dung.docx", True))  # control nguyên vẹn
            con.gui("DUNG")
            xong = con.doc(60)
            self.assertEqual(((xong or {}).get("buoc"), (xong or {}).get("loi"), (xong or {}).get("da_dung")), ("XONG", None, True), xong)
        finally:
            dung = con.dung(ket_thuc=xong is None)
            if dung is not True:
                raise AssertionError(f"Native child/Word control chưa xác nhận dừng (UNKNOWN): {dung}")
        self.assertTrue(pids_co_san <= R._pids_winword(), "Word có sẵn của người dùng bị ảnh hưởng")  # metadata PID, không chạm
        self.assertEqual(tep.read_bytes(), truoc)
        self.assertTrue((lan / "hd.docx").is_file())  # DOCX giữ, không cleanup

    def test_qua_han_trung_thuc(self):
        lan = self.chuan_bi()
        kq = R.chuyen_pdf(lan, lan / "hd.docx", han=0.5)
        self.assertNotEqual(kq["trang_thai"], "PDF_DA_TAO")
        self.assertIn(kq["ly_do"], ("WORKER_QUA_HAN_HOAC_EOF", "WORKER_CHUA_DUNG"))
        if "dung" in kq:
            self.assertIn(kq["dung"], ("DA_DUNG", "UNKNOWN"))
        w = kq.get("word") or {}
        if w.get("pid"):
            self.assertIn(w.get("da_dung"), (True, None))  # True = Job rỗng đã xác nhận; None = UNKNOWN (không kill PID suy đoán)
        self.assertTrue((lan / "hd.docx").is_file())


if __name__ == "__main__":
    unittest.main()
