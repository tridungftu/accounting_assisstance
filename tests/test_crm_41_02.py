"""CRM-41-02 — kiểm tĩnh + thuần (CODE_ONLY: coder viết, CHƯA CHẠY — NOT_RUN_CODE_ONLY).

Không cần PostgreSQL/mạng/Office/AI. Không đọc var/.env/oracle riêng; chỉ đọc hai input công khai readonly trong docs/ và mã nguồn sản phẩm.
- Prefix pg_migrations.py: 791902 byte đầu giữ nguyên (SHA 36ed5ad1…), M18 chỉ APPEND; 17 checksum + digest thứ tự khớp input Root.
- M18 tĩnh: không DROP/TRUNCATE/sửa K5 CHECK; hàm lệnh INVOKER; bảng mới REVOKE khỏi vai ứng dụng; guard K5 OLD-or-NEW.
- Bộ đọc DOCX tổng hợp (literal tạo trong test): nhiều phần/tách run/bảng lồng/header-footer được tham chiếu/xuất hiện lặp; không ghép qua
  đoạn/ô/phần; 7 hazard fail-closed; kênh chưa hỗ trợ/Track Changes → INCOMPLETE.
- Seed literal khớp docs/CRM-41-02-DEMO-INPUTS.json; route HTTP/shell/S6 tĩnh; dòng setup C4 đúng một lần.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import unittest
import warnings
import zipfile
from pathlib import Path

from kho_tri_thuc.giao_dien import crm_g as G
from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import crm_g_demo as SEED, quyen
from kho_tri_thuc.nguon.mau_docx import PHIEN_BAN_BO_DOC, doc_mau_docx

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
PREFIX = json.loads((GOC / "docs" / "CRM-41-02-MIGRATION-PREFIX-17.json").read_text(encoding="utf-8"))
DEMO = json.loads((GOC / "docs" / "CRM-41-02-DEMO-INPUTS.json").read_text(encoding="utf-8"))

# ---------------------------------------------------------------------- DOCX tổng hợp (không dùng tệp riêng của Root)
W_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:v="urn:schemas-microsoft-com:vml"')
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
CT = (XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
REL_T = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
ROOT_RELS = XML + f'<Relationships xmlns="{REL_NS}"><Relationship Id="rId1" Type="{REL_T}officeDocument" Target="word/document.xml"/></Relationships>'


def r(text: str) -> str:
    return f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r>'


def p(*runs: str) -> str:
    return "<w:p>" + "".join(r(t) for t in runs) + "</w:p>"


def tbl(*rows) -> str:
    return "<w:tbl>" + "".join("<w:tr>" + "".join(f"<w:tc>{c}</w:tc>" for c in row) + "</w:tr>" for row in rows) + "</w:tbl>"


def document(body: str, sect: str = "") -> str:
    return XML + f"<w:document {W_NS}><w:body>{body}{sect}</w:body></w:document>"


def rels(*items) -> str:  # (Id, loại, đích, ngoài?)
    return XML + f'<Relationships xmlns="{REL_NS}">' + "".join(
        f'<Relationship Id="{i}" Type="{REL_T}{t}" Target="{d}"' + (' TargetMode="External"' if ngoai else "") + "/>" for i, t, d, ngoai in items) + "</Relationships>"


def docx(doc_xml: str, parts: dict | None = None, doc_rels: str | None = None, dup: str | None = None, overrides=()) -> bytes:
    buf = io.BytesIO()
    ct = CT.replace("</Types>", "".join(f'<Override PartName="/{p_}" ContentType="{c_}"/>' for p_, c_ in overrides) + "</Types>")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # tên trùng (ca hazard) — zipfile cảnh báo nhưng vẫn ghi
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", ct)
            z.writestr("_rels/.rels", ROOT_RELS)
            z.writestr("word/document.xml", doc_xml)
            if doc_rels:
                z.writestr("word/_rels/document.xml.rels", doc_rels)
            for k, v in (parts or {}).items():
                z.writestr(k, v)
            if dup:
                z.writestr(dup, "<x/>")
    return buf.getvalue()


SECT_HF = '<w:sectPr><w:headerReference w:type="default" r:id="rIdH"/><w:footerReference w:type="default" r:id="rIdF"/></w:sectPr>'
HF_RELS = rels(("rIdH", "header", "header1.xml", False), ("rIdF", "footer", "footer1.xml", False))


def mau_day_du() -> bytes:
    """Thân: tách run + lặp + bảng lồng; header/footer được tham chiếu; footer2 KHÔNG tham chiếu (không thuộc phát hiện)."""
    than = (p("Hợp đồng số ", "{{so_", "hop_dong}}", " ngày {{ngay_ky}}")
            + tbl([p("Bên thuê: {{ho_ten}}") + tbl([p("Lặp: {{so_hop_dong}}")])])  # một ô: đoạn + bảng lồng
            + p("Kết thúc."))
    return docx(document(than, SECT_HF), {
        "word/header1.xml": XML + f"<w:hdr {W_NS}>{p('Đầu trang {{so_hop_dong}}')}</w:hdr>",
        "word/footer1.xml": XML + f"<w:ftr {W_NS}>{p('Chân trang {{ngay_ky}}')}</w:ftr>",
        "word/footer2.xml": XML + f"<w:ftr {W_NS}>{p('Không dùng {{an}}')}</w:ftr>",
    }, HF_RELS)


class PrefixMigration(unittest.TestCase):
    def test_791902_byte_dau_giu_nguyen_va_chi_append(self):
        raw = (SRC / "ha_tang" / "pg_migrations.py").read_bytes()
        self.assertEqual(hashlib.sha256(raw[:791902]).hexdigest(), "36ed5ad1035f3cf85593cbfdc2e5ca84b3a73ecffd1df010aa4987d6826b3964")
        duoi = raw[791902:].decode("utf-8")
        self.assertIn("M0018_CRM_G = (", duoi)
        # Các gói sau M18 nối thêm; chỉ cắt tới cuối khối đăng ký M18, giữ nguyên pin prefix.
        cuoi = "PG_MIGRATIONS = (*PG_MIGRATIONS, M0018_CRM_G)\nPG_SCHEMA_VERSION = len(PG_MIGRATIONS)"
        self.assertEqual(duoi.count(cuoi), 1)
        duoi = duoi.split("\n# ---------------------------------------------------------------------------\n# 0019", 1)[0]
        self.assertTrue(duoi.rstrip().endswith("PG_MIGRATIONS = (*PG_MIGRATIONS, M0018_CRM_G)\nPG_SCHEMA_VERSION = len(PG_MIGRATIONS)"), duoi[-200:])

    def test_17_checksum_va_digest_thu_tu(self):
        self.assertGreaterEqual(len(PM.PG_MIGRATIONS), 18)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        self.assertIs(PM.PG_MIGRATIONS[17], PM.M0018_CRM_G)
        ds = PREFIX["prefix_1_17"]
        self.assertEqual([x["version"] for x in ds], list(range(1, 18)))
        for x in ds:
            self.assertEqual(PM._hash(PM.PG_MIGRATIONS[x["version"] - 1]), x["checksum"], x["constant"])
        digest = hashlib.sha256("".join(f"{x['version']}:{x['checksum']}\n" for x in ds).encode("ascii")).hexdigest()
        self.assertEqual(digest, PREFIX["ordered_prefix_digest"]["sha256"])

    def test_m17_import_va_tuong_thich_khong_doi(self):
        from kho_tri_thuc.m4.sql_m17 import M0017_M4
        self.assertIs(PM.PG_MIGRATIONS[16], M0017_M4)
        self.assertEqual(set(PM.PG_MIGRATION_TUONG_THICH), {10})


class M18Tinh(unittest.TestCase):
    S = PM.M0018_CRM_G

    def test_khong_xoa_khong_sua_k5_check(self):
        for s in self.S:
            self.assertIsNone(re.search(r"\bDROP\b|\bTRUNCATE\b|DELETE\s+FROM", s), s[:120])
            self.assertNotIn("ALTER TABLE kho.viec_can_duyet", s)
            self.assertIsNone(re.search(r"GRANT\s+(?!.*REVOKE).*\bTO\s+app_web", s), s[:120])

    def test_ham_lenh_invoker_va_chi_chu(self):
        lenh = [s for s in self.S if re.search(r"FUNCTION master\.crm_g_(mau|chuan)_(tai|anh_xa|gui_kiem|kiem|tra_lai|duyet|tu_choi|lap|gui)\(", s)]
        self.assertEqual(len(lenh), 10)
        for s in lenh:
            self.assertNotIn("SECURITY DEFINER", s)
            self.assertIn("CRM_G_CHI_MAY_CHU", s)
            self.assertIn("master.crm_g_dich(", s)  # quyền hiện hành TRƯỚC tra biên nhận
            self.assertLess(s.index("master.crm_g_dich("), s.index("master.crm_g_bn_tra("))

    def test_s01_preflight_ghim_quyen_truoc_dich(self):
        tra = next(s for s in self.S if "FUNCTION master.crm_g_tra(" in s)
        self.assertLess(tra.index("master.crm_g_ghim_quyen("), tra.index("master.crm_g_dich("))
        ghim = next(s for s in self.S if "FUNCTION master.crm_g_ghim_quyen(" in s)
        for bang in ("master.nguoi_dung", "master.phan_quyen", "master.phan_cong_hanh_dong"):
            self.assertRegex(ghim, re.escape(bang) + r"[^;]*FOR SHARE")
        bn = next(s for s in self.S if "FUNCTION master.crm_g_bn_tra(" in s)
        self.assertIn("pg_advisory_xact_lock", bn)  # khóa namespace giữ đến hết giao dịch
        src = (SRC / "k2" / "crm_mau.py").read_text(encoding="utf-8")
        than = src[src.index("    def tai_mau("):src.index("    def luu_anh_xa(")]
        i_tx, i_tra, i_parse, i_blob, i_lenh = (than.index(x) for x in ("with self._tx(dt) as c:", "self._tra_trong(c,", "doc_mau_docx(raw)",
                                                                         "write_immutable(", "master.crm_g_mau_tai("))
        self.assertTrue(i_tx < i_tra < i_parse < i_blob < i_lenh)
        self.assertEqual(than.count("self._tx("), 1)  # một giao dịch duy nhất từ preflight đến FINAL

    def test_guard_k5_typed_dang_active(self):
        """T04: guard K5 typed ĐANG active ở chuỗi mặc định là trigger `crm_g_viec_kiem` do M18 tạo (INSERT/UPDATE/DELETE)."""
        tao = [s for s in self.S if s.startswith("CREATE TRIGGER crm_g_viec_kiem ")]
        self.assertEqual(tao, ["CREATE TRIGGER crm_g_viec_kiem BEFORE INSERT OR UPDATE OR DELETE ON kho.viec_can_duyet FOR EACH ROW "
                               "EXECUTE FUNCTION kho.crm_g_viec_kiem()"])
        self.assertFalse(any("crm_g_viec_kiem" in s for m in PM.PG_MIGRATIONS[:17] for s in m))

    def test_guard_chu_the_k5_chi_them_nhanh_typed(self):
        """T04: `viec_chu_so_huu` chỉ có trong M0013 full-M9 LỊCH SỬ (không thuộc chuỗi mặc định 1–17); M18 thay HÀM nhưng không tạo trigger nào
        gắn hàm đó → ở chuỗi mặc định hàm này KHÔNG active và không được dùng làm bằng chứng chặn typed K5. Vẫn kiểm: bản M18 giữ mọi dòng của
        định nghĩa lịch sử theo thứ tự và chỉ thêm nhánh typed (an toàn nếu một lineage nào đó có gắn trigger)."""
        self.assertNotIn(PM.M0013, PM.PG_MIGRATIONS)  # full-M9 lịch sử không thuộc chuỗi active
        self.assertIn(PM.M0013, PM.PG_MIGRATIONS_LICH_SU_FULL_M9)
        self.assertFalse(any("TRIGGER viec_chu_so_huu" in s for m in PM.PG_MIGRATIONS for s in m))  # 1–18 không gắn trigger này
        cu = next(s for s in PM.M0013 if "FUNCTION kho.viec_chu_so_huu()" in s)
        moi = next(s for s in self.S if "FUNCTION kho.viec_chu_so_huu()" in s)
        dong_cu, dong_moi = [x.strip() for x in cu.splitlines() if x.strip()], [x.strip() for x in moi.splitlines() if x.strip()]
        it = iter(dong_moi)
        self.assertTrue(all(any(d == m for m in it) for d in dong_cu), "mọi dòng guard cũ phải còn nguyên và đúng thứ tự")
        them = [d for d in dong_moi if d not in dong_cu]
        cho_phep = ("IF NEW.tham_chieu_bang IN ('master.crm_mau_phien_ban','master.crm_bo_chuan_phien_ban') THEN",
                    "IF n <> 1 OR chu.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id OR chu.module IS DISTINCT FROM NEW.module THEN")
        self.assertTrue(all("crm_g_chu_the" in d or d in cho_phep for d in them), them)
        self.assertEqual(sum("FUNCTION kho.viec_chu_so_huu()" in s for m in PM.PG_MIGRATIONS[:17] for s in m), 0)

    def test_bang_moi_revoke_va_rls(self):
        noi = "\n".join(self.S)
        for t in PM._G_BANG_MOI:
            self.assertIn(f"ALTER TABLE master.{t} ENABLE ROW LEVEL SECURITY", noi)
            self.assertIn(f"master.{t}", noi.split("REVOKE ALL ON", 1)[1])
        self.assertIn("'app_web','app_ke_toan','app_doc','app_cong_ai'", noi)

    def test_guard_k5_old_or_new_va_doc_moi_trang_thai(self):
        g = next(s for s in self.S if "FUNCTION kho.crm_g_viec_kiem()" in s)
        self.assertIn("cu_typed := OLD.tham_chieu_bang IN", g)
        self.assertIn("moi_typed := NEW.tham_chieu_bang IN", g)
        self.assertIn("CRM_G_VIEC_DOI_DICH", g)
        self.assertIn("CRM_G_VIEC_DA_DONG", g)
        self.assertIn("NEW.loai IS DISTINCT FROM 'V4'", g)
        pol = next(s for s in self.S if "CREATE POLICY viec_can_duyet_crm_g_doc" in s)
        self.assertIn("AS RESTRICTIVE FOR SELECT TO PUBLIC", pol)
        self.assertNotIn("trang_thai", pol)  # áp mọi trạng thái, kể cả đã đóng

    def test_ban_do_khac_ten_va_canh_bao_bat_buoc(self):
        ax = next(s for s in self.S if "FUNCTION master.crm_g_mau_anh_xa(" in s)
        self.assertIn("TRUONG_BAT_BUOC_VANG", ax)
        self.assertIn("kiem_hien_hanh = NULL", ax)  # đổi ánh xạ vô hiệu lần kiểm hiện hành
        kiem = next(s for s in self.S if "FUNCTION master.crm_g_mau_kiem(" in s)
        self.assertNotIn("canh_bao", kiem)  # cảnh báo không chặn kiểm


class BoDocDocx(unittest.TestCase):
    def test_phat_hien_nhieu_phan_tach_run_bang_long_header_footer(self):
        raw = mau_day_du()
        f = doc_mau_docx(raw)
        self.assertEqual(f["bo_doc"], PHIEN_BAN_BO_DOC)
        self.assertEqual(f["raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(f["trang_thai"], "DU", f["ly_do_chua_du"])
        self.assertEqual([x["ten"] for x in f["phan_quet"]], ["word/document.xml", "word/header1.xml", "word/footer1.xml"])
        self.assertEqual([(o["ten"], o["loai_phan"]) for o in f["occurrences"]],
                         [("so_hop_dong", "THAN"), ("ngay_ky", "THAN"), ("ho_ten", "THAN"), ("so_hop_dong", "THAN"),
                          ("so_hop_dong", "HEADER"), ("ngay_ky", "FOOTER")])
        dau = f["occurrences"][0]
        self.assertTrue(dau["tach_run"])
        self.assertEqual(dau["runs"], [2, 3])
        self.assertEqual(dau["vi_tri"], "p[1]")
        self.assertFalse(f["occurrences"][1]["tach_run"])
        self.assertEqual(f["occurrences"][3]["vi_tri"], "tbl[1]/tr[1]/tc[1]/tbl[1]/tr[1]/tc[1]/p[1]")
        self.assertEqual({x["ten"]: x["so_lan"] for x in f["placeholders"]}, {"so_hop_dong": 3, "ngay_ky": 2, "ho_ten": 1})
        self.assertNotIn("an", {x["ten"] for x in f["placeholders"]})  # footer2 không tham chiếu
        self.assertEqual(doc_mau_docx(raw)["facts_sha256"], f["facts_sha256"])  # tất định
        self.assertEqual(len(f["members"]), 7)

    def test_khong_ghep_qua_doan_o_phan(self):
        f = doc_mau_docx(docx(document(p("{{so_") + p("hop_dong}}") + tbl([p("{{a"), p("b}}")]))))
        self.assertEqual(f["occurrences"], [])
        self.assertEqual(f["trang_thai"], "INCOMPLETE")
        self.assertEqual({x["ma"] for x in f["ly_do_chua_du"]}, {"NGOAC_LE"})

    def test_track_changes_va_hop_van_ban_incomplete(self):
        tc = document('<w:p><w:ins w:id="1" w:author="DEMO">' + r("{{so_hop_dong}}") + "</w:ins></w:p>")
        f = doc_mau_docx(docx(tc))
        self.assertEqual(f["trang_thai"], "INCOMPLETE")
        self.assertIn("TRACK_CHANGES", {x["ma"] for x in f["ly_do_chua_du"]})
        hop = document("<w:p>" + r("Trước ") + "<w:r><w:pict><v:textbox><w:txbxContent>" + p("{{trong_hop}}")
                       + "</w:txbxContent></v:textbox></w:pict></w:r></w:p>")
        f = doc_mau_docx(docx(hop))
        self.assertEqual(f["trang_thai"], "INCOMPLETE")
        self.assertIn("KENH_CHUA_HO_TRO", {x["ma"] for x in f["ly_do_chua_du"]})
        self.assertEqual([o["ngu_canh"] for o in f["occurrences"]], ["{{trong_hop}}"])  # không ghép vào đoạn ngoài

    def test_kenh_chua_quet_footnote(self):
        f = doc_mau_docx(docx(document(p("x")), {"word/footnotes.xml": XML + f"<w:footnotes {W_NS}>{p('{{chu_thich}}')}</w:footnotes>"}))
        self.assertEqual(f["trang_thai"], "INCOMPLETE")
        self.assertEqual([x["ma"] for x in f["ly_do_chua_du"]], ["KENH_CHUA_QUET"])

    def test_p03_khoang_run_va_van_ban_doan(self):
        f = doc_mau_docx(mau_day_du())
        self.assertEqual(f["don_vi_khoang"], "UNICODE_CODE_POINT_NUA_MO")
        dau, a = f["occurrences"][0], len("Hợp đồng số ")
        self.assertEqual((dau["bat_dau"], dau["ket_thuc"], dau["van_ban_o"]), (a, a + len("{{so_hop_dong}}"), "{{so_hop_dong}}"))
        self.assertEqual(dau["khoang_run"], [
            {"run": 2, "bat_dau": a, "ket_thuc": a + 5, "bat_dau_trong_run": 0, "ket_thuc_trong_run": 5},
            {"run": 3, "bat_dau": a + 5, "ket_thuc": a + 15, "bat_dau_trong_run": 0, "ket_thuc_trong_run": 10}])
        d1 = next(d for d in f["doan"] if d["chi_so"] == dau["doan"])
        self.assertEqual(d1["van_ban"], "Hợp đồng số {{so_hop_dong}} ngày {{ngay_ky}}")
        self.assertEqual(d1["do_dai"], len(d1["van_ban"]))
        self.assertFalse(d1["cat_bot"])
        self.assertEqual([x["run"] for x in d1["runs"]], [1, 2, 3, 4])
        for o in f["occurrences"]:  # khoảng tái tạo đúng chuỗi ô từ văn bản đoạn đã lưu
            d = next(x for x in f["doan"] if x["chi_so"] == o["doan"])
            self.assertEqual(d["van_ban"][o["bat_dau"]:o["ket_thuc"]], o["van_ban_o"])
        self.assertEqual([d["chi_so"] for d in f["doan"]], [1, 2, 3, 5, 6])  # đoạn 4 "Kết thúc." không có ô → không lưu văn bản
        g = doc_mau_docx(mau_day_du(), limits={"doan_ky_tu": 5})
        self.assertEqual(g["trang_thai"], "INCOMPLETE")
        self.assertIn("DOAN_QUA_DAI", {x["ma"] for x in g["ly_do_chua_du"]})
        self.assertTrue(all(d["cat_bot"] and len(d["van_ban"]) == 5 for d in g["doan"]))

    def test_p01_utf16_dtd_va_ma_khai_bao(self):
        than = f"<w:document {W_NS}><w:body>{p('{{so_hop_dong}}')}</w:body></w:document>"
        ok16 = ("﻿" + '<?xml version="1.0" encoding="UTF-16" standalone="yes"?>' + than).encode("utf-16-le")
        f = doc_mau_docx(docx(ok16))
        self.assertEqual((f["trang_thai"], [o["ten"] for o in f["occurrences"]]), ("DU", ["so_hop_dong"]))  # đối chứng hợp lệ
        self.assertEqual(doc_mau_docx(docx(('<?xml version="1.0" encoding="UTF-16"?>' + than).encode("utf-16-be")))["trang_thai"], "DU")
        dtd16 = ("﻿" + '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE w:document [<!ENTITY e "{{x}}">]>' + than).encode("utf-16-le")
        self.assertNotIn(b"DOCTYPE", dtd16)  # chứng minh regex byte ASCII cũ không thấy
        self._loi(docx(dtd16), "CRM_MAU_DTD")
        self._loi(docx(("<!DOCTYPE w:document [<!ENTITY e 'x'>]>" + than).encode("utf-16-be")), "CRM_MAU_DTD")  # UTF-16 không BOM
        self._loi(docx(('<?xml version="1.0" encoding="ISO-8859-1"?>' + than).encode("utf-8")), "CRM_MAU_XML_HONG")  # khai báo lệch mã
        self._loi(docx(('<?xml version="1.0" encoding="UTF-8"?>' + than).encode("utf-16-le")), "CRM_MAU_XML_HONG")
        self._loi(docx(b"\xff\xfe\x00\x00" + than.encode("utf-32-le")), "CRM_MAU_XML_HONG")  # UTF-32 không nhận
        ct16 = docx(document(p("x")))
        self.assertEqual(doc_mau_docx(ct16)["trang_thai"], "DU")

    def test_p02_kenh_chua_quet_ngoac_tach_run(self):
        def fn(*doan):
            return {"word/footnotes.xml": XML + f"<w:footnotes {W_NS}><w:footnote w:id=\"1\">{''.join(doan)}</w:footnote></w:footnotes>"}
        cases = {
            "tach_run": fn(p("{", "{chu_thich}", "}")),
            "tach_doan": fn(p("Xem {"), p("{chu_thich}}")),
            "ngoac_le": fn(p("giá trị } lẻ")),
        }
        for ten, parts in cases.items():
            raw = docx(document(p("{{so_hop_dong}}")), parts)
            self.assertNotIn(b"{{", zipfile.ZipFile(io.BytesIO(raw)).read("word/footnotes.xml") if ten != "tach_doan" else b"", ten)
            f = doc_mau_docx(raw)
            self.assertEqual((f["trang_thai"], [x["ma"] for x in f["ly_do_chua_du"]]), ("INCOMPLETE", ["KENH_CHUA_QUET"]), ten)
        # kênh được document tham chiếu ở thư mục khác cũng bị xét
        rel = rels(("rIdC", "comments", "extra/comments.xml", False))
        f = doc_mau_docx(docx(document(p("x")), {"word/extra/comments.xml": XML + f"<w:comments {W_NS}>{p('{', '{a}}')}</w:comments>"}, rel))
        self.assertEqual([x["ma"] for x in f["ly_do_chua_du"]], ["KENH_CHUA_QUET"])
        # đối chứng: chú thích không có ngoặc → DU, thân vẫn phát hiện đúng
        f = doc_mau_docx(docx(document(p("{{so_hop_dong}}")), fn(p("Chú thích bình thường"))))
        self.assertEqual((f["trang_thai"], len(f["occurrences"])), ("DU", 1))

    def test_p02_tiep02_phan_loai_theo_quan_he_khong_theo_ten(self):
        ct_fn = "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"
        ct_st = "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"
        fn_ngoac = XML + f'<w:footnotes {W_NS}><w:footnote w:id="1">{p("{", "{ho", "_ten}", "}")}</w:footnote></w:footnotes>'  # token tách 4 run
        fn_sach = XML + f'<w:footnotes {W_NS}><w:footnote w:id="1">{p("Chú thích bình thường")}</w:footnote></w:footnotes>'
        than = document(p("{{so_hop_dong}}") + '<w:p><w:r><w:footnoteReference w:id="1"/></w:r></w:p>')
        # (1) phần footnotes ĐƯỢC tham chiếu nhưng mang tên dễ bị bỏ qua theo basename → vẫn quét, INCOMPLETE (không DU)
        for ten in ("styles.xml", "header1.xml", "theme/theme1.xml", "settings.xml", "fontTable.xml"):
            raw = docx(than, {f"word/{ten}": fn_ngoac}, rels(("rIdF", "footnotes", ten, False)), overrides=[(f"word/{ten}", ct_fn)])
            self.assertNotIn(b"{{", zipfile.ZipFile(io.BytesIO(raw)).read(f"word/{ten}"), ten)
            f = doc_mau_docx(raw)
            self.assertEqual((f["trang_thai"], [x["ma"] for x in f["ly_do_chua_du"]]), ("INCOMPLETE", ["KENH_CHUA_QUET"]), ten)
            self.assertEqual(f["ly_do_chua_du"][0]["quan_he"], ["footnotes"])
            self.assertEqual([o["ten"] for o in f["occurrences"]], ["so_hop_dong"], ten)  # thân vẫn phát hiện đúng
        # (2) đối chứng hợp lệ: styles thật + footnotes sạch (tên lạ nhưng nhất quán) → DU
        styles = XML + f'<w:styles {W_NS}><w:style w:styleId="a"/></w:styles>'
        raw = docx(than, {"word/styles.xml": styles, "word/header1.xml": fn_sach},
                   rels(("rIdS", "styles", "styles.xml", False), ("rIdF", "footnotes", "header1.xml", False)),
                   overrides=[("word/styles.xml", ct_st), ("word/header1.xml", ct_fn)])
        f = doc_mau_docx(raw)
        self.assertEqual((f["trang_thai"], f["ly_do_chua_du"], len(f["occurrences"])), ("DU", [], 1))
        self.assertEqual(f["raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual({m["ten"]: m["sha256"] for m in f["members"]}["word/header1.xml"], hashlib.sha256(fn_sach.encode("utf-8")).hexdigest())
        # (3) siêu dữ liệu mâu thuẫn không suy COMPLETE
        def ma(raw_):
            return sorted({x["ma"] for x in doc_mau_docx(raw_)["ly_do_chua_du"]})
        self.assertEqual(ma(docx(than, {"word/styles.xml": fn_ngoac}, rels(("rIdS", "styles", "styles.xml", False)))),
                         ["KENH_CHUA_QUET", "SIEU_DU_LIEU_MAU_THUAN"])  # quan hệ styles ↔ gốc footnotes
        self.assertEqual(ma(docx(than, {"word/styles.xml": fn_sach}, rels(("rIdS", "styles", "styles.xml", False)))),
                         ["SIEU_DU_LIEU_MAU_THUAN"])  # mâu thuẫn dù không có ngoặc
        self.assertEqual(ma(docx(than, {"word/x.xml": fn_sach}, rels(("rIdF", "footnotes", "x.xml", False)), overrides=[("word/x.xml", ct_st)])),
                         ["SIEU_DU_LIEU_MAU_THUAN"])  # ContentType styles ↔ quan hệ/gốc footnotes
        sect = '<w:sectPr><w:headerReference w:type="default" r:id="rIdH"/></w:sectPr>'
        self.assertEqual(ma(docx(document(p("x"), sect), {"word/header1.xml": fn_sach}, rels(("rIdH", "header", "header1.xml", False)))),
                         ["SIEU_DU_LIEU_MAU_THUAN"])  # sectPr trỏ phần không phải w:hdr
        # (4) phần mồ côi mang tên header nhưng gốc footnotes có ngoặc → không bỏ qua theo tên
        self.assertEqual(ma(docx(document(p("x")), {"word/header2.xml": fn_ngoac})), ["KENH_CHUA_QUET"])
        # (5) header/footer nhất quán nhưng không được sectPr tham chiếu → không hiển thị, giữ DU (đối chứng)
        hdr = XML + f"<w:hdr {W_NS}>{p('{{khong_hien}}')}</w:hdr>"
        f = doc_mau_docx(docx(document(p("x")), {"word/header9.xml": hdr}, rels(("rIdH", "header", "header9.xml", False))))
        self.assertEqual((f["trang_thai"], f["occurrences"]), ("DU", []))

    def _loi(self, raw, ma, **kw):
        with self.assertRaises(DataError) as c:
            doc_mau_docx(raw, **kw)
        self.assertEqual(c.exception.code, ma)

    def test_7_hazard_fail_closed(self):
        than = document(p("{{so_hop_dong}}"))
        self._loi(docx(than, dup="word/document.xml"), "CRM_MAU_TRUNG_PHAN")
        self._loi(docx(than, {"../ngoai.xml": "<x/>"}), "CRM_MAU_DUONG_DAN")
        self._loi(docx(than, {"word/vbaProject.bin": "x"}), "CRM_MAU_MACRO")
        self._loi(docx(than, {"word/activeX/activeX1.xml": "<x/>"}), "CRM_MAU_NOI_DUNG_CHU_DONG")
        self._loi(docx(XML + '<!DOCTYPE w:document [<!ENTITY e "x">]>' + than[len(XML):]), "CRM_MAU_DTD")
        self._loi(docx(than, doc_rels=rels(("rIdX", "hyperlink", "https://example.invalid/", True))), "CRM_MAU_QUAN_HE_NGOAI")
        self._loi(docx(than), "CRM_MAU_BOM_NEN", limits={"member": 64})

    def test_dau_vao_sai(self):
        self._loi(b"", "CRM_MAU_TEP_RONG")
        self._loi(b"not a zip", "CRM_MAU_TEP_SAI")
        self._loi(b"PK\x03\x04hong", "CRM_MAU_TEP_SAI")
        self._loi(docx("<w:document"), "CRM_MAU_XML_HONG")


class SeedLiteral(unittest.TestCase):
    def test_actor_grant_phan_cong_danh_muc_khop_input(self):
        self.assertEqual(SEED.MARKER, DEMO["seed_contract"]["new_marker"])
        muon = {(a["login"], a["role"], a["grants"][0]["pn_ref"], tuple(a["grants"][0]["modules"]), tuple(a["grants"][0]["type_of_work"]))
                for a in DEMO["new_actors"]}
        co = {(n, v, pn, tuple(m), tuple(d)) for n, v, g in SEED.NGUOI_DUNG for pn, (m, d) in g.items()}
        self.assertEqual(co, muon)
        self.assertTrue(all(n.startswith("MO_PHONG_") for n in SEED.dang_nhap_crm_g()))
        self.assertEqual({(x["actor"], x["pn_ref"], x["module"], x["action"], x["scope_type_ref"], x["state"]) for x in DEMO["new_assignments"]},
                         set(SEED.PHAN_CONG))
        cat = DEMO["catalog"]
        self.assertEqual((SEED.DANH_MUC_REF, SEED.DANH_MUC_REV, list(SEED.DANH_MUC_LOAI)), (cat["ref"], cat["revision"], cat["scope_type_refs"]))
        self.assertEqual([(f["key"], f["label"], f["group"], f["type"], f["format"], f["source_kind"], f["pii"], f["required_in_document"], f["synthetic_preview"])
                          for f in cat["fields"]], [tuple(t) for t in SEED.TRUONG])
        self.assertEqual(set(quyen.HANH_DONG_CRM_G), {a["code"] for a in DEMO["actions"]})

    def test_khong_seed_duyet(self):
        src = (SRC / "k2" / "crm_g_demo.py").read_text(encoding="utf-8")
        for bang in ("crm_mau ", "crm_mau_phien_ban", "crm_mau_kiem_tra", "crm_bo_chuan", "viec_can_duyet"):
            self.assertNotIn("INSERT INTO master." + bang.strip(), src)
            self.assertNotIn("INSERT INTO kho." + bang.strip(), src)


class HttpShellTinh(unittest.TestCase):
    def test_route_khong_dung_post_mau_cu(self):
        self.assertFalse(G.la_route(True, "/api/crm/mau"))  # #6 DEMO cũ giữ handler cũ
        self.assertTrue(G.la_route(False, "/api/crm/mau"))
        for path in ("/api/crm/mau/tai", "/api/crm/mau/anh-xa", "/api/crm/bo-chuan/lap"):
            self.assertTrue(G.la_route(True, path))
        for path in ("/api/crm/mau/so-sanh", "/api/crm/bo-chuan", "/api/crm/mau/0b6f6f6e-0000-4000-8000-000000000000"):
            self.assertTrue(G.la_route(False, path))
        for path in ("/api/crm", "/api/crm/danh-tinh", "/api/crm/duyet", "/api/crm/bo-sung"):
            self.assertFalse(G.la_route(True, path))

    def test_than_tu_choi_truong_quyen(self):
        for k in ("actor", "phap_nhan_id", "trang_thai", "facts", "raw_sha256", "dang_nhap", "viec_id"):
            with self.assertRaises(DataError) as c:
                G._than({k: "x", "version_id": "x"}, G.TRUONG["mau/kiem"])
            self.assertEqual(c.exception.code, "CRM_G_CLIENT_AUTHORITY")
        with self.assertRaises(DataError) as c:
            G._than({"la": 1}, G.TRUONG["mau/kiem"])
        self.assertEqual(c.exception.code, "CRM_G_YEU_CAU_SAI")
        self.assertNotIn("tra-lai", " ".join(k for k in G.TRUONG if k.startswith("bo-chuan")))  # G7 không có trả lại

    def test_server_dispatch_va_allowlist(self):
        s = (SRC / "giao_dien" / "server.py").read_text(encoding="utf-8")
        self.assertIn('"/mark.svg", "/crm_g.js"}', s)
        i_g, i_old = s.index("crm_g_http.la_route(post, path)"), s.index('if path.startswith("/api/crm/"):')
        self.assertLess(i_g, i_old)
        self.assertLess(s.index("m4_http.dieu_huong"), i_g)

    def test_shell_mount_va_s6(self):
        h = (SRC / "giao_dien" / "assets" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<article id="crm-g" class="card"', h)
        self.assertLess(h.index('<script src="/app.js" defer>'), h.index('<script src="/crm_g.js" defer>'))
        trang = h[h.index('id="page-hopdong"'):h.index('id="page-khoanvay"')]
        self.assertIn('id="crm-g"', trang)
        js = (SRC / "giao_dien" / "assets" / "crm_g.js").read_text(encoding="utf-8")
        self.assertIn('K.dangKyVai("crm_g"', js)
        self.assertGreaterEqual(js.count('K.vaiDangChan("crm_g")'), 4)
        for cam in ("innerHTML", "outerHTML", "insertAdjacentHTML", "eval(", "new Function", "document.write"):
            self.assertNotIn(cam, js)
        for route in ("/api/crm/mau/tai", "/api/crm/mau/tep/", "/api/crm/mau/so-sanh", "/api/crm/bo-chuan", '"mau/tra-lai"', '"mau/tu-choi"'):
            self.assertIn(route, js)
        # QD-20261025-07: G7 áp dụng ngay qua du-an-ban/tien-do trong Dự án đang bán, bỏ bước CFO duyệt.
        # Giao diện ghép route từ tiền tố và hành động; route máy chủ cũ không thuộc kiểm tra shell này.
        self.assertIn('const path = "du-an-ban/" + f.hanh', js)
        self.assertIn('["Sửa tiến độ tiêu chuẩn", "tien-do"]', js)
        # U01: giữ chỗ ý định ĐỒNG BỘ (không await trong hàm giữ chỗ); một header/khóa gốc tạo lúc giữ chỗ; gửi lại dùng đúng y.enc/y.file
        giu = js[js.index("function giuChoYDinh()"):js.index("async function guiTai(")]
        self.assertNotIn("await", giu)
        self.assertIn("taiDang.set(intent, y)", giu)
        self.assertIn("khoa = taoKhoa()", giu)
        gt_ = js[js.index("async function guiTai("):js.index("// ---", js.index("async function guiTai("))]
        self.assertIn('headers: {"X-CRM-G-Info": y.enc}, body: y.file', gt_)
        self.assertNotIn("taoKhoa(", gt_)
        self.assertLess(gt_.index("y.dangGui = true"), gt_.index("await"))
        self.assertIn("gf === genForm", giu)  # TIEP-02: context ý định gồm thế hệ form chung
        # TIEP-02 U02: tải tệp gốc rào trước request, sau mọi bước chờ (phản hồi/blob/arrayBuffer/digest) và ngay trước URL/click/trạng thái
        tg = js[js.index("async function taiGoc("):js.index("// ---", js.index("async function taiGoc("))]
        self.assertIn('tab === "mau" && gf === genForm', tg)
        self.assertEqual(tg.count("if (!f()) return;"), 6)
        self.assertLess(tg.rindex("if (!f()) return;"), tg.index("URL.createObjectURL"))
        self.assertLess(tg.index("if (!f()) return;"), tg.index("await goi("))
        # TIEP-02 U02: GET lỗi cùng fence với thành công; lỗi tạm không xóa dữ liệu/editor; hẹn giờ thử lại qua fence
        nds = js[js.index("async function napDs()"):js.index("async function napCt()")]
        self.assertIn("if (dung()) napDs()", nds)
        self.assertIn("if (loiAnNinh(err))", nds)
        self.assertEqual(nds.count("if (!dung()) return;"), 2)
        nbc = js[js.index("async function napBc()"):js.index("const truyVanDoc")]
        self.assertIn('dung = () => e === ep && g === genBc && tab === "chuan"', nbc)
        self.assertEqual(nbc.count("if (!dung()) return;"), 2)
        # U02: GET bộ chuẩn rào theo thế hệ + truy vấn + tab + vai
        doc = js[js.index("async function docChuan()"):js.index("function boChon()")]
        for x in ("++genDoc", "g === genDoc", 'tab === "chuan"', "JSON.stringify(truyVanDoc()) === khoaQ", 'K.vaiDangChan("crm_g")'):
            self.assertIn(x, doc)
        for cot in DEMO["G7_demo_input_not_seeded_approval"]["columns"]:
            self.assertIn(cot, (SRC / "k2" / "crm_mau.py").read_text(encoding="utf-8"))

    def test_c4_setup_dung_mot_dong(self):
        """T04: tệp f77 có ĐÚNG 3 câu chọn nguồn mẫu dạng trực tiếp — một câu đã có từ trước (khối mở tab thứ hai) và hai câu bổ sung
        đúng §11 (trước `nutMau` và sau `soGet2`). Kiểm theo TỪNG ngữ cảnh + SHA toàn tệp; không sửa tệp M4 cho vừa test."""
        raw = (GOC / "tests" / "m4_01c_async.cjs").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), "f77bdfe66772a2494d36f40cb1f2119d27af351ae8f101b1a3dc42bd9274a9d2")
        dong = '$("m4f-nguon-mau").value = "hop_dong.docx"; $("m4f-nguon-mau").dispatch("change");'
        text = raw.decode("utf-8")
        self.assertEqual(text.count(dong), 3)
        ngu_canh = {
            "da_co_truoc": ('await moTab("Nguồn HĐ");', 'nutTheoChu($("m4-chi-tiet"), "Dùng tệp mẫu").click(); await chay();'),
            "bo_sung_truoc_nutMau": ('await moTab("Nguồn HĐ");', 'const nutMau = nutTheoChu($("m4-chi-tiet"), "Dùng tệp mẫu");'),
            "bo_sung_sau_soGet2": ('const soGet2 = dem(get("/api/m4/mau/hop_dong.docx"));', 'nutTheoChu($("m4-chi-tiet"), "Dùng tệp mẫu").click(); await chay();'),
        }
        dong_tep = [d.strip() for d in text.splitlines()]
        vi_tri = [i for i, d in enumerate(dong_tep) if d == dong]
        self.assertEqual(len(vi_tri), 3)
        thuc = [(dong_tep[i - 1], dong_tep[i + 1]) for i in vi_tri]
        self.assertEqual(thuc, list(ngu_canh.values()))  # đúng thứ tự xuất hiện: có sẵn, rồi hai bổ sung
        self.assertEqual(text.count('const chonMau = v => { $("m4f-nguon-mau").value = v; $("m4f-nguon-mau").dispatch("change"); };'), 1)


class DigestYeuCau(unittest.TestCase):
    def test_h_khong_gom_khoa_va_tat_dinh(self):
        from kho_tri_thuc.k2.crm_mau import _h
        a = _h("CRM_MAU_KIEM", {"version_id": "v", "expected_graph": "t"})
        self.assertEqual(a, _h("CRM_MAU_KIEM", {"expected_graph": "t", "version_id": "v"}))
        self.assertNotEqual(a, _h("CRM_MAU_TRA_LAI", {"version_id": "v", "expected_graph": "t"}))
        self.assertRegex(a, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
