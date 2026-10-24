"""M4-02B — kiểm TĨNH + THUẦN cho Chứng từ L3 (không PostgreSQL). CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN_CODE_ONLY).

Phân loại:
- `M22Tinh`: migration 22 append-only (prefix 927604 byte của pg_migrations giữ nguyên; sql_review.py nguyên byte), hằng SQL M22 (bảng, trigger, quyền,
  RLS, thứ tự khóa HĐ → biên nhận, kiểm quyền TRƯỚC biên nhận).
- `SeamTinh`: PIN lõi nguồn L3, nhánh L3 của worker, route/allowlist HTTP (query nghiêm cho chi tiết/tải), tài sản UI (không innerHTML, mount sau khi
  gắn DOM, ngữ cảnh PN/dự án).
- `DichVuThuan` (FIX01 §6/§3): kiểm JSON hữu hạn TOÀN cây của kết quả worker, hình dạng kết quả L3 sâu, phần căn cứ L2 phụ thuộc (không gồm tệp gắn
  đợt/nộp), authority lồng trong mục sửa → 403 — gọi hàm thật của service, không PG.
- `AdapterThat`: THẬT trên lõi nguồn đã ghim (`review_goc/may_chu/chung_tu.py` …) + openpyxl/python-docx — bộ chứng từ TỔNG HỢP viết tay trong test.
  Kỳ vọng là SỐ/CHUỖI VIẾT TAY từ đầu vào + quy tắc nguồn đã đọc (không lấy từ output của sản phẩm). FIX01 §4: mỗi tệp tạo bytes MỘT lần; row_id kỳ
  vọng tính từ CHÍNH raw đã đưa vào lần chạy (không serialize workbook lần hai). Căn cứ BOQ/PL hiệu lực dùng projection SQLite :memory: của seam Review
  hiện hữu (`nguon_review.projection_l2`) — khác tích hợp PostgreSQL (test_m4_02b_k2). Thiếu lõi nguồn/openpyxl/python-docx → skip = NOT_RUN.
Không mạng, không PG, không Office, không OCR/AI; thư mục tạm giữ lại, không xóa.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

from kho_tri_thuc.giao_dien import m4 as GM4
from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m4 import nguon_review as NR
from kho_tri_thuc.m4 import sql_chung_tu as SC

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None
try:
    import docx as _docx
except ImportError:  # pragma: no cover
    _docx = None


def _nguon_da_nap() -> bool:
    return NR.GOC.is_dir() and all((NR.GOC / rel).is_file() for rel in NR.PIN)


# ================================================================================================== tĩnh: migration
class M22Tinh(unittest.TestCase):
    S = SC.M0022_M4_CHUNG_TU

    def test_prefix_927604_byte_va_append_m22(self):
        raw = (SRC / "ha_tang" / "pg_migrations.py").read_bytes()
        self.assertEqual(hashlib.sha256(raw[:927604]).hexdigest(), "0e87d8e1a39aef582d79ffd7cef30b7dcdf523d151009729e6cb1d5b64452dce")
        duoi = raw[927604:].decode("utf-8")
        self.assertIn("from ..m4.sql_chung_tu import M0022_M4_CHUNG_TU", duoi)
        self.assertTrue(duoi.rstrip().endswith("PG_MIGRATIONS = (*PG_MIGRATIONS, M0022_M4_CHUNG_TU)\nPG_SCHEMA_VERSION = len(PG_MIGRATIONS)"), duoi[-200:])
        self.assertEqual((PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS)), (22, 22))  # M22 candidate; KHÔNG có M23
        self.assertIs(PM.PG_MIGRATIONS[21], SC.M0022_M4_CHUNG_TU)
        self.assertIs(PM.PG_MIGRATIONS[20], PM.M0021_CRM_G2G3)

    def test_sql_review_nguyen_byte(self):
        raw = (SRC / "m4" / "sql_review.py").read_bytes()
        self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), (40029, "273cb440b22f3d646cf2145e8bbcf9b56c9944fe607860e37c9cea05a161881f"))

    def test_khong_xoa_khong_sua_doi_tuong_cu(self):
        for s in self.S:
            self.assertIsNone(re.search(r"\bDROP\b|\bTRUNCATE\b|DELETE\s+FROM|ALTER\s+TABLE\s+m4\.(review|bien_nhan|dot|tep|nop)", s), s[:120])
            self.assertNotIn("CREATE OR REPLACE FUNCTION m4.review_", s)  # không thay hàm M19/M20
            self.assertNotIn("CREATE OR REPLACE FUNCTION m4._bn_", s)
            self.assertNotIn("CREATE ROLE", s)
        noi = "\n".join(self.S)
        for t in SC.BANG:
            self.assertIn(f"CREATE TABLE m4.{t} (", noi)
            self.assertIn(f"ALTER TABLE m4.{t} ENABLE ROW LEVEL SECURITY", noi)
        self.assertNotIn("m4.review_artifact (run_id, du_an_id, loai", noi)  # REPORT_L3 không nhét vào review_artifact
        self.assertIn("CHECK (object_key = 'm4-chung-tu/' || raw_sha256)", noi)
        self.assertIn("'REPORT_L3'", noi)
        self.assertNotIn("chung_tu_giu_khoa TO app_web", noi)  # giữ chỗ khóa không cấp đọc cho login ứng dụng
        self.assertNotIn("GRANT INSERT", noi)
        self.assertNotIn("GRANT UPDATE", noi)

    def _ham(self, ten):
        return next(s for s in self.S if f"FUNCTION m4.{ten}(" in s and "CREATE OR REPLACE" in s)

    def test_ham_lenh_owner_invoker_quyen_truoc_bien_nhan(self):
        for ten in ("chung_tu_tra", "chung_tu_giu", "chung_tu_tao_run", "chung_tu_cong_bo", "chung_tu_huy", "chung_tu_ghi_revision", "chung_tu_ghi_map"):
            s = self._ham(ten)
            self.assertNotIn("SECURITY DEFINER", s, ten)
            self.assertIn("M4_CHI_MAY_CHU_NGUON", s, ten)
            if ten != "chung_tu_huy":  # hủy dùng ĐÚNG khi người chạy đã mất quyền: chỉ chủ lần chạy (tao_boi_id), không biên nhận/FINAL nghiệp vụ
                self.assertIn("m4.chung_tu_kiem(", s, ten)
            else:
                self.assertIn("r.tao_boi_id <> aid", s)
                self.assertNotIn("_bn_ghi", s)
            if "m4._bn_tra(" in s:
                self.assertLess(s.index("m4.chung_tu_kiem("), s.index("m4._bn_tra("), ten)
        for ten in ("chung_tu_ghi_revision", "chung_tu_ghi_map"):  # khóa HĐ TRƯỚC khóa biên nhận (thứ tự M17/M19)
            s = self._ham(ten)
            self.assertLess(s.index("FROM m4.ho_so_hop_dong WHERE hop_dong_id = r.hop_dong_id FOR UPDATE"), s.index("pg_advisory_xact_lock("), ten)
            self.assertIn("M4_REVISION_CU", s)
            self.assertIn("m4.review_giu_khoa", s)  # khóa đã giữ chỗ cho Review → xung đột
        tao = self._ham("chung_tu_tao_run")
        self.assertLess(tao.index("m4._bn_tra("), tao.index("M4_REVISION_CU"))  # FINAL cũ trước kiểm revision
        cb = self._ham("chung_tu_cong_bo")
        self.assertIn("THEN 'STALE'", cb)
        self.assertIn("m4._bn_ghi(", cb)
        gm = self._ham("chung_tu_ghi_map")  # đích ghép tay lưu ĐÚNG boq_id + dòng vật lý (worker so lại với đích hiện hành trước khi áp)
        self.assertIn("boq_id, boq_dong, ma_hm, run_id, tep_id,", gm)
        self.assertIn("M4_REVIEW_DICH_KHONG_HIEU_LUC", gm)

    def test_quyen_doc_va_kiem(self):
        q = self._ham("chung_tu_quyen")
        self.assertIn("%TYPE", q)
        self.assertNotIn(" record;", q)  # không record chưa gán (bài học M20)
        self.assertIn("d_tt = 'DA_NOP' AND master.m4_duoc(d_du_an, 'REVIEW')", q)
        k = self._ham("chung_tu_kiem")
        self.assertIn("M4_CHUNG_TU_KHONG_THAY", k)
        self.assertIn("M4_CHUNG_TU_PHAM_VI", k)
        dd = self._ham("chung_tu_doc_dot")
        self.assertIn("'XEM'", dd)
        self.assertIn("d.trang_thai = 'DA_NOP'", dd)
        noi = "\n".join(self.S)
        self.assertIn("REVOKE EXECUTE ON FUNCTION " + ", ".join(SC.HAM_LENH) + " FROM PUBLIC", noi)
        for p in ("chung_tu_run_web", "chung_tu_result_web", "chung_tu_artifact_web", "chung_tu_revision_web", "chung_tu_manual_map_web"):
            self.assertIn(f"CREATE POLICY {p}", noi)

    def test_trigger_xung_dot_khoa_l3_review_m17(self):
        noi = "\n".join(self.S)
        self.assertIn("CREATE TRIGGER bien_nhan_chung_tu_khoa BEFORE INSERT ON m4.bien_nhan", noi)
        self.assertIn("CREATE TRIGGER review_giu_khoa_chung_tu BEFORE INSERT ON m4.review_giu_khoa", noi)
        self.assertIn("CREATE TRIGGER chung_tu_run_kiem BEFORE INSERT OR UPDATE OR DELETE ON m4.chung_tu_run", noi)
        for t in ("chung_tu_result", "chung_tu_artifact", "chung_tu_revision", "chung_tu_manual_map", "chung_tu_giu_khoa"):
            self.assertIn(f"CREATE TRIGGER {t}_chi_ghi_them", noi)
        g = self._ham("chung_tu_giu")
        self.assertLess(g.index("m4._bn_tra("), g.index("INSERT INTO m4.chung_tu_giu_khoa"))


# ================================================================================================== tĩnh: seam
class SeamTinh(unittest.TestCase):
    def test_pin_l3_va_engine(self):
        self.assertEqual(NR.PIN["may_chu/chung_tu.py"], "31a4d04a5af84e65d2bc3c9a44463ccf871a96f9aa053d0c79aaf5246e034cd0")
        self.assertEqual(NR.PIN["may_chu/phu_luc_ai.py"], "743168a158bebeb6e3cda25fb4b0b31e1f9d1fc78c495a4adc5aff3b98321caf")
        self.assertTrue(all(k in NR.PIN for k in NR.L3_PIN))
        self.assertIn(NR.PIN["may_chu/chung_tu.py"][:12], NR.ENGINE_L3)
        self.assertRegex(NR.ENGINE_L3_SHA, r"^[0-9a-f]{64}$")
        self.assertNotIn("may_chu.chung_tu", NR.MODULE_CAN)  # không nạp eager khi khởi động
        for p in NR.L3_PROVIDER.values():
            self.assertEqual(p["trang_thai"], "NOT_CONFIGURED")

    def test_worker_nhanh_l3_mot_tien_trinh(self):
        src = (SRC / "m4" / "review_compute.py").read_text(encoding="utf-8")
        main = src[src.index("def main("):]
        self.assertLess(main.index("guard_dang_nap()"), main.index('vao.get("che_do") == "L3"'))  # guard trước mọi I/O/nạp vendor
        self.assertIn("chung_tu_adapter.tinh(vao, thu_muc)", main)
        ad = (SRC / "m4" / "chung_tu_adapter.py").read_text(encoding="utf-8")
        for cam in ("tao_bo(", "hang_muc_tu_dot(", "hang_muc_tu_boq(", ".luu(", ".xoa(", "dich_vu", "ocr_docx(", "chuan_bi_pdf(", "chuyen_docx(",
                    "doc_dong_ai(", "setattr(", "ct.ghep_hang_muc =", "ct._cot =", "ct.dong_hang =", "psycopg", "subprocess"):
            self.assertNotIn(cam, ad, cam)
        self.assertIn('g["doc_mot_tai_lieu"](str(path), ai=None)', ad)  # reader nguồn NGUYÊN mã, ai=None, trong namespace cục bộ
        self.assertIn("ct.doi_chieu(copy.deepcopy(kq_goc))", ad)
        self.assertIn("types.FunctionType(ct.doi_chieu.__code__", ad)

    def test_route_allowlist_va_lenh_rieng(self):
        self.assertEqual(GM4.TRUONG["chung-tu/chay"], {"dot_id", "revision", "expected_basis", "khoa"})
        self.assertEqual(GM4.TRUONG["chung-tu/sua"], {"run_id", "revision", "tai_lieu", "expected_basis", "ly_do", "khoa"})
        self.assertEqual(GM4.TRUONG["chung-tu/ghep"], {"run_id", "row_id", "boq_id", "boq_dong", "ma_hm", "revision", "expected_basis", "ly_do", "khoa"})
        self.assertEqual(GM4.TRUONG["chung-tu/chay-lai"], {"run_id", "revision", "expected_basis", "khoa"})
        self.assertTrue(GM4.CHUNG_TU_LENH <= GM4.LENH_RIENG)
        self.assertEqual(GM4.CHUNG_TU_GET, {"dot_id"})
        for t in GM4.TRUONG.values():
            self.assertFalse(t & GM4.KHONG_NHAN)
        self.assertIn("M4_CHUNG_TU_KHONG_THAY", GM4.MA_404)
        self.assertIn("M4_CHUNG_TU_PHAM_VI", GM4.MA_403)
        self.assertIn("M4_KET_QUA_CHUA_RO", GM4.MA_503)  # commit chưa rõ → 503: trình duyệt giữ khóa/body để đối soát
        src = (SRC / "giao_dien" / "m4.py").read_text(encoding="utf-8")
        self.assertIn('if path == "/m4/chung-tu.js":', src)
        self.assertIn('(ASSETS / "chung_tu.js")', src)
        nhanh = src[src.index('m = re.fullmatch(r"/api/m4/chung-tu/('):]
        self.assertLess(nhanh.index("_q(query, set())"), nhanh.index("app.crm_phien("))  # query lạ/lặp bị từ chối TRƯỚC phiên/dữ liệu

    def test_tai_san_ui(self):
        js = (SRC / "m4" / "giao_dien" / "chung_tu.js").read_text(encoding="utf-8")
        code = re.sub(r"//[^\n]*", "", js)
        self.assertIsNone(re.search(r"\.innerHTML\s*=|\.outerHTML\s*=|insertAdjacentHTML\(|document\.write\(", code))
        self.assertIn("window.kttM4ChungTu = Object.freeze(", js)
        self.assertIn('K.dangKyVai("m4_chung_tu"', js)
        self.assertNotIn('"DELETE"', code)
        self.assertNotIn("/api/chung_tu", code)
        m4 = (SRC / "m4" / "giao_dien" / "m4.js").read_text(encoding="utf-8")
        self.assertIn('["chung_tu", "Chứng từ L3"]', m4)
        self.assertIn('s.src = "/m4/chung-tu.js";', m4)
        ve = m4[m4.index("function veHd()"):]
        self.assertLess(ve.index("box.replaceChildren(card);"), ve.index('if (tab === "chung_tu") veChungTu(noi);'))  # mount SAU khi gắn DOM
        self.assertIn("C.huy()", m4)
        self.assertIn("duAnId: hd.ho_so.du_an_id", m4)  # ngữ cảnh fence có dự án + PN
        self.assertIn("phapNhan: hd.ho_so.phap_nhan", m4)


# ================================================================================================== dịch vụ thuần (không PG)
class DichVuThuan(unittest.TestCase):
    def setUp(self):
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        self.X = XayDungK2

    def test_json_huu_han_toan_cay(self):
        for xau in (b'{"a": NaN}', b'{"a": [1, {"b": Infinity}]}', b'{"a": -Infinity}', b'{"a": {"b": [1e999]}}'):
            with self.assertRaises(ValueError, msg=xau):
                self.X._json_l3(xau)
        sau = b'{"a":' * 70 + b"1" + b"}" * 70
        with self.assertRaises(ValueError):
            self.X._json_l3(sau)
        self.assertEqual(self.X._json_l3(b'{"a": [0, 0.5, null, "x", true]}'), {"a": [0, 0.5, None, "x", True]})

    def test_hinh_dang_sau(self):
        from kho_tri_thuc.m4 import chung_tu_adapter as CA
        svc = self.X.__new__(self.X)
        cov = {m: {"trang_thai": "INCOMPLETE", "ly_do": "x"} for m in (*CA.MA_L3, *CA.MA_PHU)}
        tep = {"tep_id": "t1", "raw_sha256": "a" * 64}
        kq = {"che_do": "L3", "basis_sha256": "b" * 64, "engine_sha256": NR.ENGINE_L3_SHA, "coverage": cov, "trang_thai": "PARTIAL",
              "tai_lieu": [{"tep_id": "t1", "trang_thai_doc": "CHECKED", "raw_sha256": "a" * 64, "dong": [{"row_id": "c" * 64, "vi_tri_vat_ly": {}}]}],
              "hang_muc": [{"khoa": "HM-01"}], "phat_hien": [], "ma_tran": [],
              "so_sanh": {"HM-01": {"C01": {"trang_thai": "CHUA_SO_DUOC"}, "C03": {"trang_thai": "KHONG_AP_DUNG"}}},
              "c06_cap": [], "chu_thich_phat_hien": [], "provenance": {"auto": {}, "ghep_tay": []}, "bao_cao": []}
        co = {"tai_lieu": [tep]}
        self.assertTrue(svc._chung_tu_hinh_dang_ok(kq, co, "b" * 64))
        for sua in ({"trang_thai": "SUCCEEDED"}, {"engine_sha256": "0" * 64}, {"so_sanh": {"HM-01": {"C01": {"trang_thai": "DAT"}, "C03": {"trang_thai": "SO_DUOC"}}}},
                    {"tai_lieu": [{**kq["tai_lieu"][0], "raw_sha256": "d" * 64}]}, {"tai_lieu": [{**kq["tai_lieu"][0], "dong": [{"row_id": "x"}]}]},
                    {"phat_hien": [{"id": "C10-01", "code": "C10", "level": "Cao"}]}, {"c06_cap": [{"gn_row_id": "a"}]}, {"so_sanh": {}}):
            self.assertFalse(svc._chung_tu_hinh_dang_ok({**kq, **sua}, co, "b" * 64), sua)

    def test_l2_phan_phu_thuoc_khong_gom_tep_dot_va_nop(self):
        co = {k: {"v": k} for k in self.X.L2_PHU_THUOC}
        co.update(dot={"id": "d", "hop_dong_id": "h", "ngay_nghiem_thu": "2026-03-01", "trang_thai": "NHAP", "revision": 3, "nop_id": None},
                  dot_tep=[{"tep_id": "x"}])
        a = self.X._l2_phan_phu_thuoc(co)
        b = self.X._l2_phan_phu_thuoc({**co, "dot_tep": [{"tep_id": "x"}, {"tep_id": "co-moi"}],
                                       "dot": {**co["dot"], "trang_thai": "DA_NOP", "revision": 4, "nop_id": "n"}})
        self.assertEqual(a, b)  # gắn thêm chứng từ L3 / nộp đợt không làm L2 cũ đi
        c = self.X._l2_phan_phu_thuoc({**co, "dot": {**co["dot"], "ngay_nghiem_thu": "2026-03-05"}})
        self.assertNotEqual(a, c)  # đổi ngày NT → căn cứ L2 khác
        self.assertNotEqual(a, self.X._l2_phan_phu_thuoc({**co, "boq": {"v": "boq moi"}}))

    def test_authority_long_trong_muc_sua(self):
        svc = self.X.__new__(self.X)
        for k in ("raw_sha256", "path", "actor", "trang_thai", "row_id"):
            with self.assertRaises(DataError) as cm:
                svc._chung_tu_chuan_sua([{"tep_id": "11111111-1111-4111-8111-111111111111", "so": "1", k: "x"}])
            self.assertEqual(cm.exception.code, "M4_CLIENT_AUTHORITY", k)
        with self.assertRaises(DataError) as cm:
            svc._chung_tu_chuan_sua([{"tep_id": "11111111-1111-4111-8111-111111111111", "ghi_chu": "x"}])
        self.assertEqual(cm.exception.code, "M4_THAM_SO_SAI")  # trường lạ không phải authority → 400


# ================================================================================================== thuần THẬT trên lõi nguồn
def _docx_bytes(dong_dau: list, bang: list | None, *, ins: bool = False) -> bytes:
    d = _docx.Document()
    for t in dong_dau:
        d.add_paragraph(t)
    if bang:
        tb = d.add_table(rows=len(bang), cols=len(bang[0]))
        for i, r in enumerate(bang):
            for j, v in enumerate(r):
                tb.cell(i, j).text = v
    b = io.BytesIO()
    d.save(b)
    raw = b.getvalue()
    if not ins:
        return raw
    src, out = zipfile.ZipFile(io.BytesIO(raw)), io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for i in src.infolist():
            data = src.read(i.filename)
            if i.filename == "word/document.xml":
                s = data.decode("utf-8")
                k = s.index("</w:p>")
                s = s[:k] + '<w:ins w:id="91" w:author="DEMO" w:date="2026-03-01T00:00:00Z"><w:r><w:t>sửa chưa chốt</w:t></w:r></w:ins>' + s[k:]
                data = s.encode("utf-8")
            z.writestr(i, data)
    return out.getvalue()


def _xlsx_bytes(sheets: list) -> bytes:
    """sheets: [(tên, {(dòng, cột): giá trị}[, [vùng gộp 'D4:E4', ...]])] — ô không khai là trống thật (None); gộp SAU khi ghi giá trị."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for s in sheets:
        ten, o = s[0], s[1]
        ws = wb.create_sheet(ten)
        for (r, c), v in o.items():
            ws.cell(r, c, v)
        for rg in (s[2] if len(s) > 2 else ()):
            ws.merge_cells(rg)
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def _docx_bang_gop(dong_dau: list, bangs: list) -> bytes:
    """bangs: [(dòng ô chữ, [((r1, c1), (r2, c2)) ô gộp])] — ghi chữ TRƯỚC rồi gộp bằng python-docx (ngang → gridSpan, dọc → vMerge)."""
    d = _docx.Document()
    for t in dong_dau:
        d.add_paragraph(t)
    for rows, gop in bangs:
        tb = d.add_table(rows=len(rows), cols=len(rows[0]))
        for i, r in enumerate(rows):
            for j, v in enumerate(r):
                if v:
                    tb.cell(i, j).text = v
        for (r1, c1), (r2, c2) in gop:
            tb.cell(r1, c1).merge(tb.cell(r2, c2))
        d.add_paragraph("")
    b = io.BytesIO()
    d.save(b)
    return b.getvalue()


def _hang(r0: int, rows: list) -> dict:
    return {(r0 + i, j + 1): v for i, row in enumerate(rows) if row is not None for j, v in enumerate(row) if v is not None}


NT_DAU = ["BIÊN BẢN NGHIỆM THU KHỐI LƯỢNG", "Số: 01/BBNT-2026", "Hà Nội, ngày 01 tháng 03 năm 2026", "Căn cứ Hợp đồng số 123/2025"]
NT_BANG = [["STT", "Tên công việc", "ĐVT", "Khối lượng kỳ này"], ["1", "Ống HDPE D110", "m", "100"], ["2", "Van cổng DN100", "cái", "5"]]
GN_TIEU_DE = {(1, 1): "BIÊN BẢN GIAO NHẬN VẬT TƯ — Hợp đồng số 123/2025", (2, 1): "Số: 05/BBGN-2026", (3, 1): "Ngày 25/02/2026"}
GN_COT = ["STT", "Tên vật tư", "Model", "ĐVT", "Số lượng", "Số lô"]
# hạng mục căn cứ = dòng L2 đã công bố (giá trị viết tay): HM-01 KL kỳ này 120 / lũy kế 150; HM-02 5 / 5
L2_DONG = [{"dong": 10, "ma_hm": "HM-01", "ten": "Ống HDPE D110", "dvt": "m", "kl_kn": 120, "kl_lk": 150, "dg_hd": 100000, "dg_hs": 100000, "kl_hd_hs": 500},
           {"dong": 11, "ma_hm": "HM-02", "ten": "Van cổng DN100", "dvt": "cái", "kl_kn": 5, "kl_lk": 5, "dg_hd": 2000000, "dg_hs": 2000000, "kl_hd_hs": 10}]
HD_ID = "00000000-0000-4000-8000-000000000001"
BOQ_ID, BOQ_MOI_ID, BOQ_PL_ID, PL_ID = ("b0000000-0000-4000-8000-000000000001", "b0000000-0000-4000-8000-000000000002",
                                        "b0000000-0000-4000-8000-000000000003", "c0000000-0000-4000-8000-000000000001")


def _boq_dong(dong, ma, ten, dvt, kl, thao_tac="GOC"):
    return {"dong": dong, "ma_hm": ma, "thao_tac": thao_tac, "stt": str(dong - 1), "nhom": "", "ten": ten, "dvt": dvt, "kl": kl, "don_gia": "100000",
            "thanh_tien": None, "ma_rieng": None}


BOQ_GOC = {"id": BOQ_ID, "lan": 1, "phu_luc_id": None, "trang_thai": "DA_MAP", "sheet": "BOQ",
           "dong": [_boq_dong(2, "HM-01", "Ống HDPE D110", "m", "500"), _boq_dong(3, "HM-02", "Van cổng DN100", "cái", "10")]}


def _basis(*, l2=True, revision=None, manual=None, ngay_nt="2026-03-01", boq=True, l2_dong=None, phu_luc=None, boq_them=None):
    if l2 == "CU":
        l2v = {"trang_thai": "CU", "run_id": "l2-cu", "basis_sha256": "e" * 64, "ket_qua_sha256": "f" * 64, "khac": ["boq"],
               "ly_do": "Căn cứ L2 đã đổi so với lần chạy L2 đã công bố (boq)"}
    elif l2:
        l2v = {"trang_thai": "CO", "run_id": "l2", "doi_chieu_hm": l2_dong if l2_dong is not None else L2_DONG}
    else:
        l2v = {"trang_thai": "CHUA_CO", "ly_do": "chưa có"}
    return {"phien_ban": "m4.chung_tu.basis/1", "che_do": "L3", "dot": {"id": "dot", "ngay_nghiem_thu": ngay_nt, "so_dot": 1},
            "hop_dong": {"id": HD_ID, "so_hop_dong": "123/2025"},
            "tham_so": [{"ma": "TC-02", "trang_thai": "CO_GIA_TRI", "gia_tri": "01/01/2025"}, {"ma": "TT-04", "trang_thai": "CO_GIA_TRI", "gia_tri": "10%"}],
            "phu_luc": phu_luc or [], "boq": ([BOQ_GOC] if boq else []) + (boq_them or []), "manual_map_l2": [], "l2": l2v,
            "revision": revision or {"revision": 0, "tai_lieu": {}}, "revision_lich_su": [], "manual_map_l3": manual or [], "provider": NR.L3_PROVIDER}


@unittest.skipUnless(_nguon_da_nap() and openpyxl is not None and _docx is not None,
                     "Thiếu lõi nguồn Review đã nạp/openpyxl/python-docx — adapter L3 thật không chạy (skip = NOT_RUN, không tính đạt)")
class AdapterThat(unittest.TestCase):
    def chay(self, tep: list, basis: dict) -> tuple[dict, Path]:
        from kho_tri_thuc.m4 import chung_tu_adapter as CA
        tm = Path(tempfile.mkdtemp(prefix="ktt_m4ct_pure_"))  # giữ lại
        vao_tl = []
        for i, (tep_id, ten, media, raw) in enumerate(tep, 1):
            ref = f"tai_lieu/{i:03d}/{ten}"
            (tm / ref).parent.mkdir(parents=True)
            (tm / ref).write_bytes(raw)
            vao_tl.append({"tep_id": tep_id, "work_ref": ref, "raw_sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw), "media_type": media,
                           "ten_goc": ten, "muc": f"C{i:02d}"})
        kq = CA.tinh({"che_do": "L3", "run_id": "t", "basis": basis, "basis_sha256": "a" * 64, "tai_lieu": vao_tl, "revision": basis["revision"]["revision"]}, tm)
        json.dumps(kq, allow_nan=False)  # kết quả là JSON hữu hạn
        return kq, tm

    # mỗi helper tạo bytes MỘT lần và trả tuple (id, tên, media, raw) — test dùng LẠI đúng tuple đó cho kỳ vọng
    def nt(self, bang=NT_BANG, ins=False):
        return ("11111111-1111-4111-8111-111111111111", "bb_nghiem_thu.docx", NR.MEDIA_DOCX, _docx_bytes(NT_DAU, bang, ins=ins))

    def gn(self, dong, sheet2=None, them=None, cot=GN_COT, tep_id="22222222-2222-4222-8222-222222222222"):
        o = {**GN_TIEU_DE, **_hang(5, [cot]), **_hang(6, dong), **(them or {})}
        sheets = [("GiaoNhan", o)] + ([("Ghi chu", sheet2)] if sheet2 else [])
        return (tep_id, "bb_giao_nhan.xlsx", NR.MEDIA_XLSX, _xlsx_bytes(sheets))

    def chung_nhan(self, loai, tieu_de, so, ngay, dong, tep_id):  # CO/CQ/PL dạng bảng XLSX (tiêu đề tiếng Anh nguồn nhận)
        o = {(1, 1): tieu_de, (2, 1): f"No.: {so}", (3, 1): f"Date: {ngay}", **_hang(4, [["Description", "Model", "Unit", "Quantity", "Lot No."]]), **_hang(5, dong)}
        return (tep_id, f"{loai.lower()}.xlsx", NR.MEDIA_XLSX, _xlsx_bytes([(loai, o)]))

    def form_docx(self, dong_dau, tep_id, ten):  # chứng từ dạng form: chỉ đoạn văn, không bảng
        return (tep_id, ten, NR.MEDIA_DOCX, _docx_bytes(dong_dau, None))

    @staticmethod
    def theo_ten(kq):
        return {x["ten"]: x for x in kq["tai_lieu"]}

    # dòng 6 Ống, dòng 7 TRỐNG, dòng 8 Van — locator vật lý phải là 6 và 8 (nguồn nén dòng trống thành "bảng 1 dòng 5/6")
    GN_CO_BAN = [[1, "Ống HDPE D110", "HDPE110", "m", 150, "LOT-A1"], None, [2, "Van cổng DN100", "VC100", "cái", 5, "LOT-B2"]]

    def test_bo_co_ban_metadata_locator_c01_coverage(self):
        from kho_tri_thuc.m4 import chung_tu_adapter as CA
        gn = self.gn(self.GN_CO_BAN, sheet2={(1, 1): "ghi chú"})  # bytes tạo MỘT lần
        kq, tm = self.chay([self.nt(), gn], _basis())
        d = self.theo_ten(kq)
        nt_d, gn_d = d["bb_nghiem_thu.docx"], d["bb_giao_nhan.xlsx"]
        self.assertEqual((nt_d["loai"], nt_d["so"], nt_d["ngay"], nt_d["trang_thai_doc"], nt_d["trang_thai_dong"]),
                         ("BB_NT", "01/BBNT-2026", "2026-03-01", "CHECKED", "CHECKED"))
        self.assertEqual((gn_d["loai"], gn_d["so"], gn_d["ngay"], gn_d["trang_thai_doc"]), ("BB_GN", "05/BBGN-2026", "2026-02-25", "CHECKED"))
        self.assertEqual([list(x) for x in nt_d["hd_ref"]], [["123", "2025"]])
        self.assertEqual([(ln["ten"], ln["so_luong"], ln["vi_tri_vat_ly"]["sheet"], ln["vi_tri_vat_ly"]["dong"]) for ln in gn_d["dong"]],
                         [("Ống HDPE D110", 150.0, "GiaoNhan", 6), ("Van cổng DN100", 5.0, "GiaoNhan", 8)])
        self.assertEqual([(ln["vi_tri_vat_ly"]["bang"], ln["vi_tri_vat_ly"]["dong"]) for ln in nt_d["dong"]], [(1, 2), (1, 3)])
        # FIX01 §4: row_id kỳ vọng từ CHÍNH raw đã cấp cho lần chạy (gn[3]) — không tạo workbook lần hai
        self.assertEqual(gn_d["dong"][0]["row_id"], CA.row_id(hashlib.sha256(gn[3]).hexdigest(), "XLSX|GiaoNhan|6"))
        self.assertEqual(gn_d["raw_sha256"], hashlib.sha256(gn[3]).hexdigest())
        self.assertEqual([(ln["khoa"]) for ln in nt_d["dong"]], ["HM-01", "HM-02"])
        c01 = [f for f in kq["phat_hien"] if f["code"] == "C01"]
        self.assertEqual(len(c01), 1)  # HM-01 KL kỳ này 120 > NT 100; HM-02 5 = 5 không phát hiện
        self.assertIn("120", c01[0]["title"])
        self.assertIn("100", c01[0]["title"])
        self.assertEqual(c01[0]["level"], "Cao")
        self.assertEqual(c01[0]["amount"], round(20 * 100000 * 1.1))  # ước tính nguồn: (120−100)×ĐG×(1+VAT 10%)
        self.assertTrue(any(f["code"] == "C05" for f in kq["phat_hien"]))  # chưa có CO/CQ cho hàng đã giao (nhánh nguồn)
        ss = kq["so_sanh"]
        self.assertEqual((ss["HM-01"]["C01"]["trang_thai"], ss["HM-01"]["C01"]["kl_kn"], ss["HM-01"]["C01"]["nt"]), ("SO_DUOC", 120, 100.0))
        self.assertEqual((ss["HM-01"]["C03"]["trang_thai"], ss["HM-01"]["C03"]["gn"]), ("SO_DUOC", 150.0))
        cov = kq["coverage"]
        self.assertEqual(set(cov), set(CA.MA_L3) | set(CA.MA_PHU))
        self.assertEqual({k: cov[k]["trang_thai"] for k in ("C01", "C03", "C05", "C06", "CAN_CU", "DONG_HANG")},
                         {"C01": "CHECKED", "C03": "CHECKED", "C05": "CHECKED", "C06": "NOT_AVAILABLE", "CAN_CU": "CHECKED", "DONG_HANG": "CHECKED"})
        self.assertEqual(kq["trang_thai"], "PARTIAL")  # có mục chưa đủ phạm vi → không SUCCEEDED
        self.assertTrue((tm / "chung_tu_l3.xlsx").is_file())
        wb = openpyxl.load_workbook(tm / "chung_tu_l3.xlsx", read_only=True)
        self.assertEqual(wb.sheetnames, ["Tóm tắt", "Ma trận", "Phát hiện C01-C09", "Phạm vi kiểm", "Chứng từ", "Dòng hàng", "Đối chiếu chéo C06",
                                         "Ghép tay & lịch sử", "Giới hạn"])
        wb.close()
        self.assertEqual(kq["bao_cao"], [{"loai": "REPORT_L3", "tep": "chung_tu_l3.xlsx"}])

    def test_null_va_don_vi_khac_cua_dong_chung_tu(self):
        nt_m2 = [NT_BANG[0], ["1", "Ống HDPE D110", "m2", "100"], NT_BANG[2]]  # ĐVT khác hạng mục (m) → không so lượng
        gn = [[1, "Ống HDPE D110", "HDPE110", "m", 150, "LOT-A1"], [2, "Van cổng DN100", "VC100", "cái", None, "LOT-B2"]]  # Van: số lượng TRỐNG
        kq, _ = self.chay([self.nt(nt_m2), self.gn(gn)], _basis())
        g = next(x for x in kq["tai_lieu"] if x["loai"] == "BB_GN")
        self.assertEqual([ln["so_luong"] for ln in g["dong"]], [150.0, None])  # không biến trống thành 0
        ss = kq["so_sanh"]
        self.assertEqual(ss["HM-01"]["C01"]["trang_thai"], "CHUA_SO_DUOC")
        self.assertIn("ĐVT", ss["HM-01"]["C01"]["ly_do"])
        self.assertEqual(ss["HM-02"]["C03"]["trang_thai"], "CHUA_SO_DUOC")
        self.assertIn("NULL", ss["HM-02"]["C03"]["ly_do"])
        self.assertEqual(kq["coverage"]["C01"]["trang_thai"], "INCOMPLETE")
        self.assertIn("ĐVT", kq["coverage"]["C01"]["ly_do"])
        self.assertEqual(kq["coverage"]["C03"]["trang_thai"], "INCOMPLETE")
        self.assertIn("NULL", kq["coverage"]["C03"]["ly_do"])
        # finding nguồn GIỮ NGUYÊN (Van: giao 0 < 5 vì nguồn cộng NULL như 0) + ghi chú L3 riêng "chưa so được"
        c03 = [f for f in kq["phat_hien"] if f["code"] == "C03"]
        self.assertTrue(any("Van cổng DN100" in f["title"] for f in c03))
        self.assertTrue(any(x["code"] == "C03" and x["so_sanh"] == "CHUA_SO_DUOC" for x in kq["chu_thich_phat_hien"]))

    def test_so_0_tuong_minh_khac_null(self):
        gn = [[1, "Ống HDPE D110", "HDPE110", "m", 150, "LOT-A1"], [2, "Van cổng DN100", "VC100", "cái", 0, "LOT-B2"]]  # Van: 0 TƯỜNG MINH
        kq, _ = self.chay([self.nt(), self.gn(gn)], _basis())
        g = next(x for x in kq["tai_lieu"] if x["loai"] == "BB_GN")
        self.assertEqual([ln["so_luong"] for ln in g["dong"]], [150.0, 0.0])
        self.assertEqual((kq["so_sanh"]["HM-02"]["C03"]["trang_thai"], kq["so_sanh"]["HM-02"]["C03"]["gn"]), ("SO_DUOC", 0.0))  # 0 so được (≠ NULL)
        self.assertTrue(any(f["code"] == "C03" and "Van cổng DN100" in f["title"] for f in kq["phat_hien"]))  # giao 0 < 5: finding thật
        self.assertEqual(kq["coverage"]["C03"]["trang_thai"], "CHECKED")

    def test_l2_kl_null_va_0_tuong_minh(self):
        l2 = [{**L2_DONG[0], "kl_kn": None, "kl_lk": None}, {**L2_DONG[1], "kl_kn": 0, "kl_lk": 5}]
        kq, _ = self.chay([self.nt(), self.gn(self.GN_CO_BAN)], _basis(l2_dong=l2))
        ss = kq["so_sanh"]
        self.assertEqual((ss["HM-01"]["C01"]["trang_thai"], ss["HM-02"]["C01"]["trang_thai"]), ("CHUA_SO_DUOC", "NGUON_KHONG_SO"))
        self.assertEqual((ss["HM-01"]["C03"]["trang_thai"], ss["HM-02"]["C03"]["trang_thai"]), ("CHUA_SO_DUOC", "SO_DUOC"))
        self.assertIn("NULL", ss["HM-01"]["C01"]["ly_do"])
        self.assertFalse(any(f["code"] == "C01" for f in kq["phat_hien"]))  # nguồn bỏ qua KL kỳ này NULL/0 — ít phát hiện KHÔNG phải Đạt
        self.assertEqual((kq["coverage"]["C01"]["trang_thai"], kq["coverage"]["C03"]["trang_thai"]), ("INCOMPLETE", "INCOMPLETE"))
        mt = {r["khoa"]: r for r in kq["ma_tran"]}
        self.assertEqual(mt["HM-02"]["kl_kn"], 0)  # 0 tường minh giữ là 0 trong ma trận
        self.assertIsNone(mt["HM-01"]["kl_kn"])
        self.assertEqual(mt["HM-01"]["so_sanh"]["C03"]["trang_thai"], "CHUA_SO_DUOC")

    def test_bb_nt_gn_khong_co_dong_hang(self):
        nt = self.form_docx(NT_DAU + ["Hai bên thống nhất nghiệm thu khối lượng theo phụ lục đính kèm."], "33333333-3333-4333-8333-333333333331", "bb_nt_form.docx")
        gn = ("22222222-2222-4222-8222-222222222229", "bb_gn_trong.xlsx", NR.MEDIA_XLSX,
              _xlsx_bytes([("GiaoNhan", {**GN_TIEU_DE, (5, 1): "Đã giao đủ vật tư theo danh sách kèm theo."})]))
        kq, _ = self.chay([nt, gn], _basis())
        d = self.theo_ten(kq)
        self.assertEqual((d["bb_nt_form.docx"]["loai"], d["bb_nt_form.docx"]["trang_thai_doc"], d["bb_nt_form.docx"]["trang_thai_dong"]),
                         ("BB_NT", "CHECKED", "NOT_CONFIGURED"))  # metadata đọc thật; dòng hàng cần Local AI (chưa cấu hình)
        self.assertEqual((d["bb_gn_trong.xlsx"]["loai"], d["bb_gn_trong.xlsx"]["trang_thai_dong"]), ("BB_GN", "NOT_CONFIGURED"))
        self.assertEqual(d["bb_nt_form.docx"]["dong"], [])  # không tạo dòng giả
        cov = kq["coverage"]
        self.assertEqual({k: cov[k]["trang_thai"] for k in ("C01", "C03", "C05", "TAI_LIEU")},
                         {"C01": "INCOMPLETE", "C03": "INCOMPLETE", "C05": "INCOMPLETE", "TAI_LIEU": "LIMITED"})
        self.assertIn("chưa đọc được dòng hàng", cov["C01"]["ly_do"])
        self.assertTrue(any(f["code"] == "C09" and "không đọc được dòng hàng" in f["title"] for f in kq["phat_hien"]))  # C09 nguồn giữ nguyên

    def test_co_dang_form_khong_bang_khong_thanh_thieu_chac_chan(self):
        co = self.form_docx(["CERTIFICATE OF ORIGIN", "No.: CO-01/2026", "Date: 20/02/2026", "Goods: HDPE pipe HDPE110, 150 m, Lot LOT-A1"],
                            "44444444-4444-4444-8444-444444444441", "co_form.docx")
        kq, _ = self.chay([self.nt(), self.gn(self.GN_CO_BAN), co], _basis())
        d = self.theo_ten(kq)["co_form.docx"]
        self.assertEqual((d["loai"], d["trang_thai_dong"]), ("CO", "NOT_CONFIGURED"))
        cov = kq["coverage"]
        self.assertEqual((cov["C05"]["trang_thai"], cov["C06"]["trang_thai"]), ("INCOMPLETE", "INCOMPLETE"))
        self.assertIn("chưa chắc chắn", cov["C05"]["ly_do"])
        c05 = [f for f in kq["phat_hien"] if f["code"] == "C05"]
        self.assertTrue(c05)  # finding 'thiếu CO' của nguồn giữ nguyên ...
        ghi = {x["id"] for x in kq["chu_thich_phat_hien"] if x["code"] == "C05"}
        self.assertEqual(ghi, {f["id"] for f in c05})  # ... nhưng có ghi chú L3: chưa chắc chắn (có chứng từ chưa đọc dòng)

    def test_c06_don_vi_cheo_va_lo_ngay_theo_cap(self):
        gn = self.gn([[1, "Ống HDPE D110", "HDPE110", "m", 150, "LOT-A1"]])
        co = self.chung_nhan("CO", "CERTIFICATE OF ORIGIN", "CO-01/2026", "20/02/2026", [["HDPE pipe", "HDPE110", "kg", 140, "LOT-A1"]],
                             "55555555-5555-4555-8555-555555555551")
        cq = self.chung_nhan("CQ", "CERTIFICATE OF QUALITY", "CQ-01/2026", "21/02/2026", [["HDPE pipe", "HDPE110", None, 150, "LOT-A1"]],
                             "55555555-5555-4555-8555-555555555552")
        pl = self.chung_nhan("PL", "PACKING LIST", "PL-01/2026", "22/02/2026", [["HDPE pipe", "HDPE110", "m", 150, None]],
                             "55555555-5555-4555-8555-555555555553")
        kq, _ = self.chay([self.nt(), gn, co, cq, pl], _basis())
        caps = {c["loai"]: c for c in kq["c06_cap"]}
        self.assertEqual(set(caps), {"CO", "CQ", "PL"})  # nguồn coi là cùng hàng theo model HDPE110
        self.assertEqual((caps["CO"]["dvt"], caps["CO"]["so_luong"]["trang_thai"], caps["CO"]["lo"]["trang_thai"], caps["CO"]["ngay"]["trang_thai"]),
                         ("KHAC", "CHUA_SO_DUOC", "SO_DUOC", "SO_DUOC"))  # m ↔ kg: không so lượng; lô/ngày vẫn kiểm
        self.assertEqual((caps["CQ"]["dvt"], caps["CQ"]["so_luong"]["trang_thai"]), ("KHONG_RO", "CHUA_SO_DUOC"))
        self.assertEqual((caps["PL"]["dvt"], caps["PL"]["so_luong"]["trang_thai"], caps["PL"]["lo"]["trang_thai"]), ("CUNG", "SO_DUOC", "KHONG_AP_DUNG"))
        self.assertEqual(kq["coverage"]["C06"]["trang_thai"], "LIMITED")
        self.assertIn("ĐVT", kq["coverage"]["C06"]["ly_do"])
        c06 = [f for f in kq["phat_hien"] if f["code"] == "C06" and "trên CO" in f["title"]]
        self.assertTrue(c06)  # finding số lượng của nguồn (140 < 150, không theo ĐVT) giữ nguyên ...
        self.assertTrue({f["id"] for f in c06} <= {x["id"] for x in kq["chu_thich_phat_hien"] if x["code"] == "C06"})  # ... kèm ghi chú chưa so được

    def test_header_ten_hang_khong_trao_cot(self):
        ct = NR._m("may_chu.chung_tu")
        cot_goc = ct._cot
        cot = ["STT", "Tên hàng", "Model", "Hãng", "ĐVT", "Số lượng", "Số lô"]
        gn = self.gn([[1, "Ống HDPE D110", "HDPE110", "Tiền Phong", "m", 150, "LOT-A1"]], cot=cot)
        kq, _ = self.chay([self.nt(), gn], _basis())
        self.assertIs(ct._cot, cot_goc)  # module nguồn không bị sửa
        g = self.theo_ten(kq)["bb_giao_nhan.xlsx"]
        ln = g["dong"][0]
        self.assertEqual((ln["ten"], ln["model"], ln["nsx"], ln["dvt"], ln["so_luong"], ln["lo"]), ("Ống HDPE D110", "HDPE110", "Tiền Phong", "m", 150.0, "LOT-A1"))
        self.assertEqual([(x["tieu_de"], x["alias"], x["ap"]) for x in g["thich_nghi_cot"]], [("Tên hàng", "Tên vật tư", "ten")])
        # tiêu đề KHÔNG dấu mơ hồ ("Ten hang" có thể là hãng) → không alias: giữ đúng quyết định nguồn (tên lấy theo model)
        gn2 = self.gn([[1, "Ống HDPE D110", "HDPE110", "Tiền Phong", "m", 150, "LOT-A1"]], cot=["STT", "Ten hang", "Model", "Hãng", "ĐVT", "Số lượng", "Số lô"],
                      tep_id="22222222-2222-4222-8222-222222222228")
        kq2, _ = self.chay([self.nt(), gn2], _basis())
        g2 = self.theo_ten(kq2)["bb_giao_nhan.xlsx"]
        self.assertEqual(g2["thich_nghi_cot"], [])
        self.assertEqual(g2["dong"][0]["ten"], "HDPE110")

    # ---------------------------------------------------------------------------------------------- L3 A1/A2 (GIAO-SUA-M4-L3-BACKEND6) — NOT_RUN_CODE_ONLY
    # Kỳ vọng viết tay từ ô đầu vào + quy tắc `_cot`/`_tieu_de`/`dong_hang` nguồn đã đọc; bytes mỗi tệp tạo MỘT lần, hash tính từ chính bytes đó.
    GN_HANG_COT = ["STT", "Tên hàng", "Model", "Hãng", "ĐVT", "Số lượng", "Số lô"]

    def test_l3a_alias_chi_tieu_de_ten_hang_ro_nghia(self):
        from kho_tri_thuc.m4 import chung_tu_adapter as CA
        ct = NR._m("may_chu.chung_tu")
        cot_goc = ct._cot
        cho = []
        cot = CA._cot_tuong_thich(ct._cot, cho)
        for t, k, a in (("Tên hàng", "ten", ["Tên hàng"]), ("TÊN  HÀNG", "ten", ["TÊN  HÀNG"]),
                        ("Tên hàng / Nhà sản xuất", "nsx", []), ("Tên hàng (Hãng sản xuất)", "nsx", []),  # gộp tên/NSX: KHÔNG alias
                        ("Tên hãng", "nsx", []), ("Ten hang", "nsx", []), ("Hãng", "nsx", []), ("Nhà sản xuất", "nsx", []),  # hãng/không dấu mơ hồ
                        ("Ten vat tu", "ten", []), ("Tên hàng hóa", "ten", [])):  # nguồn tự nhận → quyết định native, không ghi alias
            cho.clear()
            self.assertEqual((cot(t), cho), (k, a), t)
        self.assertIs(ct._cot, cot_goc)

    def test_l3a_alias_hai_sheet_offset_gop_va_ban_truoc_alias(self):
        from kho_tri_thuc.m4 import chung_tu_adapter as CA
        s1 = {**GN_TIEU_DE, **_hang(5, [self.GN_HANG_COT]),
              **_hang(6, [[1, "Ống HDPE D110", "HDPE110", "Tiền Phong", "m", 150, "LOT-A1"], None, [2, "Van cổng DN100", "VC100", "Shinyi", "cái", 5, "LOT-B2"]])}
        # sheet 2: lệch 2 cột (bắt đầu C), tiêu đề dòng 4, dòng 5 trống, "Tên hàng" là ô gộp D4:E4
        s2 = {(4, 3): "STT", (4, 4): "Tên hàng", (4, 6): "Model", (4, 7): "Hãng", (4, 8): "ĐVT", (4, 9): "Số lượng",
              (6, 3): 1, (6, 4): "Van bi DN50", (6, 6): "VB50", (6, 7): "Shinyi", (6, 8): "cái", (6, 9): 3}
        raw = _xlsx_bytes([("GiaoNhan", s1), ("Dot2", s2, ["D4:E4"])])  # bytes MỘT lần
        gn = ("22222222-2222-4222-8222-222222222231", "bb_giao_nhan.xlsx", NR.MEDIA_XLSX, raw)
        sha = hashlib.sha256(raw).hexdigest()
        nt = self.nt()
        kq, tm = self.chay([nt, gn], _basis())
        self.assertEqual((tm / "tai_lieu/002/bb_giao_nhan.xlsx").read_bytes(), raw)  # raw không đổi
        g = self.theo_ten(kq)["bb_giao_nhan.xlsx"]
        rid = [CA.row_id(sha, "XLSX|GiaoNhan|6"), CA.row_id(sha, "XLSX|GiaoNhan|8"), CA.row_id(sha, "XLSX|Dot2|6")]
        # lớp HIỆU LỰC (sau alias): tên/model/NSX tách đúng; vị trí vật lý + dòng tiêu đề vật lý; row_id ổn định theo vị trí
        self.assertEqual([(ln["ten"], ln["model"], ln["nsx"], ln["dvt"], ln["so_luong"]) for ln in g["dong"]],
                         [("Ống HDPE D110", "HDPE110", "Tiền Phong", "m", 150.0), ("Van cổng DN100", "VC100", "Shinyi", "cái", 5.0),
                          ("Van bi DN50", "VB50", "Shinyi", "cái", 3.0)])
        self.assertEqual([(ln["vi_tri_vat_ly"]["trang_thai"], ln["vi_tri_vat_ly"]["sheet"], ln["vi_tri_vat_ly"]["dong"], ln["vi_tri_vat_ly"]["dong_tieu_de"])
                          for ln in g["dong"]], [("CHECKED", "GiaoNhan", 6, 5), ("CHECKED", "GiaoNhan", 8, 5), ("CHECKED", "Dot2", 6, 4)])
        self.assertEqual([ln["row_id"] for ln in g["dong"]], rid)
        self.assertEqual(g["trang_thai_dong"], "CHECKED")
        # bằng chứng alias: HAI bản ghi cho cùng chuỗi tiêu đề ở hai sheet (không gộp), mỗi bản đúng raw/tệp/bảng/dòng/cột/ô
        tn = g["thich_nghi_cot"]
        self.assertEqual([(x["tieu_de"], x["alias"], x["ap"], x["bang_nguon"], x["dong_tieu_de_nguon"], x["cot_nguon"], x["hieu_luc"], x["raw_sha256"], x["tep_id"])
                          for x in tn], [("Tên hàng", "Tên vật tư", "ten", 1, 4, 2, True, sha, gn[0]), ("Tên hàng", "Tên vật tư", "ten", 2, 1, 4, True, sha, gn[0])])
        v1, v2 = tn[0]["vi_tri_vat_ly"], tn[1]["vi_tri_vat_ly"]
        self.assertEqual((v1["trang_thai"], v1["sheet"], v1["dong"], v1["cot"], v1["o"], v1.get("o_gop")), ("CHECKED", "GiaoNhan", 5, 2, "B5", None))
        self.assertEqual((v2["trang_thai"], v2["sheet"], v2["dong"], v2["cot"], v2["o"], v2["o_gop"]), ("CHECKED", "Dot2", 4, 4, "D4", "D4:E4"))
        self.assertEqual(tn[0]["o_tieu_de"][:7], self.GN_HANG_COT)
        self.assertEqual(tn[1]["o_tieu_de"][:9], ["", "", "STT", "Tên hàng", "", "Model", "Hãng", "ĐVT", "Số lượng"])
        self.assertEqual([x["tep_id"] for x in kq["provenance"]["thich_nghi_cot"]], [gn[0], gn[0]])
        td = g["tieu_de_bang"]
        self.assertEqual([(x["bang_nguon"], {k: x["cot"].get(k) for k in ("ten", "model", "nsx", "sl")}, x["cot_vat_ly"]["sl"]["o"], x["alias"]) for x in td],
                         [(1, {"ten": 2, "model": 3, "nsx": 4, "sl": 6}, "F5", ["Tên hàng"]), (2, {"ten": 4, "model": 6, "nsx": 7, "sl": 9}, "I4", ["Tên hàng"])])
        # lớp nguồn TRƯỚC alias (`_cot` nguyên): "Tên hàng" là NSX, tên lấy theo model — giữ riêng, truy về đúng bytes, không qua ghép
        tr = g["nguon_truoc_alias"]
        self.assertEqual((tr["raw_sha256"], tr["tep_id"], tr["trang_thai"], tr["giong_hieu_luc"], tr["so_dong"]), (sha, gn[0], "CHECKED", False, 3))
        self.assertEqual([(ln["ten"], ln["model"], ln["nsx"], ln["so_luong"]) for ln in tr["dong"]],
                         [("HDPE110", "HDPE110", "Ống HDPE D110", 150.0), ("VC100", "VC100", "Van cổng DN100", 5.0), ("VB50", "VB50", "Van bi DN50", 3.0)])
        self.assertEqual([ln["row_id"] for ln in tr["dong"]], rid)
        self.assertEqual([(ln["vi_tri_vat_ly"]["sheet"], ln["vi_tri_vat_ly"]["dong"]) for ln in tr["dong"]], [("GiaoNhan", 6), ("GiaoNhan", 8), ("Dot2", 6)])
        self.assertEqual(tr["dong"][0]["o_nguon"][:7], ["1", "Ống HDPE D110", "HDPE110", "Tiền Phong", "m", "150", "LOT-A1"])
        self.assertTrue(all(x == "" for x in tr["dong"][0]["o_nguon"][7:]))
        self.assertTrue(all("khoa" not in ln and "ghep_tay" not in ln for ln in tr["dong"]))
        self.assertEqual([(x["bang_nguon"], {k: x["cot"].get(k) for k in ("ten", "model", "nsx", "sl")}, x["alias"]) for x in tr["tieu_de_bang"]],
                         [(1, {"ten": None, "model": 3, "nsx": 2, "sl": 6}, []), (2, {"ten": None, "model": 6, "nsx": 4, "sl": 9}, [])])
        self.assertEqual({x["tep_id"]: x["giong_hieu_luc"] for x in kq["provenance"]["truoc_alias"]}, {nt[0]: True, gn[0]: False})

    def test_l3a_tieu_de_gop_va_khong_dau_giu_quyet_dinh_nguon(self):
        s1 = {**GN_TIEU_DE, **_hang(5, [["STT", "Tên hàng / Nhà sản xuất", "Model", "ĐVT", "Số lượng", "Số lô"],
                                        [1, "Ống HDPE D110 / Tiền Phong", "HDPE110", "m", 150, "LOT-A1"]])}
        s2 = _hang(1, [["STT", "Tên hàng (Hãng sản xuất)", "Model", "ĐVT", "Số lượng"], [1, "Van cổng DN100 (Shinyi)", "VC100", "cái", 5]])
        s3 = _hang(2, [["STT", "Ten vat tu", "Model", "ĐVT", "Số lượng"], None, [1, "Van bi DN50", "VB50", "cai", 3]])
        raw = _xlsx_bytes([("GiaoNhan", s1), ("Gop2", s2), ("KhongDau", s3)])
        gn = ("22222222-2222-4222-8222-222222222232", "bb_giao_nhan.xlsx", NR.MEDIA_XLSX, raw)
        kq, _ = self.chay([self.nt(), gn], _basis())
        g = self.theo_ten(kq)["bb_giao_nhan.xlsx"]
        self.assertEqual(g["thich_nghi_cot"], [])  # tiêu đề gộp tên/NSX không bị tự alias; "Ten vat tu" nguồn đã nhận
        self.assertEqual([(ln["ten"], ln["model"], ln["nsx"], ln["vi_tri_vat_ly"]["sheet"], ln["vi_tri_vat_ly"]["dong"]) for ln in g["dong"]],
                         [("HDPE110", "HDPE110", "Ống HDPE D110 / Tiền Phong", "GiaoNhan", 6), ("VC100", "VC100", "Van cổng DN100 (Shinyi)", "Gop2", 2),
                          ("Van bi DN50", "VB50", "", "KhongDau", 4)])
        self.assertEqual([x["alias"] for x in g["tieu_de_bang"]], [[], [], []])
        tr = g["nguon_truoc_alias"]
        self.assertEqual((tr["raw_sha256"], tr["giong_hieu_luc"], tr["so_dong"], tr["dong"]), (hashlib.sha256(raw).hexdigest(), True, 3, None))

    def test_l3a_docx_hai_bang_gridspan_vmerge_dong_trong(self):
        from kho_tri_thuc.m4 import chung_tu_adapter as CA
        dau = ["BIÊN BẢN GIAO NHẬN VẬT TƯ", "Số: 06/BBGN-2026", "Ngày 26/02/2026", "Căn cứ Hợp đồng số 123/2025"]
        b1 = [["STT", "Tên hàng", "Model", "Hãng", "ĐVT", "Số lượng"], ["1", "Ống HDPE D110", "HDPE110", "Tiền Phong", "m", "150"],
              ["", "", "", "", "", ""], ["2", "Van cổng DN100", "VC100", "Shinyi", "cái", "5"]]  # w:tr 3 trống (ĐVT tiếp vMerge)
        b2 = [["STT", "", "Tên hàng", "Model", "Hãng", "ĐVT", "Số lượng"], ["1", "", "Van bi DN50", "VB50", "Shinyi", "cái", "3"]]  # STT gridSpan 2
        raw = _docx_bang_gop(dau, [(b1, [((1, 4), (2, 4))]), (b2, [((0, 0), (0, 1))])])
        gd = ("22222222-2222-4222-8222-222222222233", "bb_gn.docx", NR.MEDIA_DOCX, raw)
        sha = hashlib.sha256(raw).hexdigest()
        kq, tm = self.chay([self.nt(), gd], _basis())
        g = self.theo_ten(kq)["bb_gn.docx"]
        self.assertEqual([(ln["ten"], ln["model"], ln["nsx"], ln["dvt"], ln["so_luong"]) for ln in g["dong"]],
                         [("Ống HDPE D110", "HDPE110", "Tiền Phong", "m", 150.0), ("Van cổng DN100", "VC100", "Shinyi", "cái", 5.0),
                          ("Van bi DN50", "VB50", "Shinyi", "cái", 3.0)])
        self.assertEqual([(ln["vi_tri_vat_ly"]["bang"], ln["vi_tri_vat_ly"]["dong"], ln["vi_tri_vat_ly"]["dong_tieu_de"]) for ln in g["dong"]],
                         [(1, 2, 1), (1, 4, 1), (2, 2, 1)])
        self.assertEqual(g["dong"][1]["row_id"], CA.row_id(sha, "DOCX|1|4"))
        tn = g["thich_nghi_cot"]
        self.assertEqual([(x["bang_nguon"], x["dong_tieu_de_nguon"], x["cot_nguon"], x["hieu_luc"], x["vi_tri_vat_ly"]["trang_thai"], x["vi_tri_vat_ly"]["bang"],
                           x["vi_tri_vat_ly"]["dong"], x["vi_tri_vat_ly"]["tc"], x["vi_tri_vat_ly"]["grid_span"], x["vi_tri_vat_ly"]["logic_khac_vat_ly"]) for x in tn],
                         [(1, 1, 2, True, "CHECKED", 1, 1, 2, 1, False), (2, 1, 3, True, "CHECKED", 2, 1, 2, 1, True)])  # bảng 2: cột logic 3 = w:tc 2
        stt = g["tieu_de_bang"][1]["cot_vat_ly"]["stt"]
        self.assertEqual((stt["trang_thai"], stt["tc"], stt["grid_span"]), ("CHECKED", 1, 2))
        bd = NR.l3_vi_tri_docx(tm / "tai_lieu/002/bb_gn.docx")
        self.assertEqual([(b["bang_vat_ly"], b["dong"]) for b in bd["bang"]], [(1, [1, 2, 4]), (2, [1, 2])])
        self.assertEqual(bd["bang"][0]["o"][1][4], [5, 0, "restart"])
        self.assertEqual(bd["bang"][1]["o"][0][:3], [[1, 0, None], [1, 1, None], [2, 0, None]])
        loc = CA.vi_tri_o(NR.MEDIA_DOCX, bd, 2, 0, 1)  # cột logic 2 của tiêu đề bảng 2 = phần trải gridSpan, không phải ô vật lý
        self.assertEqual((loc["trang_thai"], loc["tc"]), ("LIMITED", 1))
        tr = g["nguon_truoc_alias"]
        self.assertEqual((tr["raw_sha256"], tr["giong_hieu_luc"]), (sha, False))
        self.assertEqual([(ln["ten"], ln["nsx"], ln["vi_tri_vat_ly"]["bang"], ln["vi_tri_vat_ly"]["dong"]) for ln in tr["dong"]],
                         [("HDPE110", "Ống HDPE D110", 1, 2), ("VC100", "Van cổng DN100", 1, 4), ("VB50", "Van bi DN50", 2, 2)])

    def test_pdf_track_changes_va_gioi_han_400(self):
        pdf = ("33333333-3333-4333-8333-333333333333", "co_scan.pdf", NR.MEDIA_PDF, b"%PDF-1.4\n%DEMO scan\n")
        tc = self.nt(ins=True)
        tc = ("44444444-4444-4444-8444-444444444444", "bb_nt_con_sua.docx", tc[2], tc[3])
        gn = self.gn(self.GN_CO_BAN, them={(405, 2): "dữ liệu ngoài vùng đọc của nguồn"})
        kq, _ = self.chay([self.nt(), gn, pdf, tc], _basis())
        d = self.theo_ten(kq)
        self.assertEqual(d["co_scan.pdf"]["trang_thai_doc"], "NOT_CONFIGURED")
        self.assertEqual(d["co_scan.pdf"]["dong"], [])
        self.assertEqual((d["bb_nt_con_sua.docx"]["trang_thai_doc"], d["bb_nt_con_sua.docx"]["track_changes"]), ("KHONG_HO_TRO", 1))
        self.assertEqual(d["bb_giao_nhan.xlsx"]["trang_thai_doc"], "LIMITED")
        self.assertIn("400", d["bb_giao_nhan.xlsx"]["ly_do_doc"])
        cov = kq["coverage"]
        self.assertEqual((cov["TAI_LIEU"]["trang_thai"], cov["C05"]["trang_thai"], cov["C09"]["trang_thai"]), ("INCOMPLETE", "INCOMPLETE", "LIMITED"))
        self.assertNotEqual(cov["C01"]["trang_thai"], "CHECKED")
        self.assertEqual(kq["trang_thai"], "PARTIAL")

    def _ghep_case(self, manual_boq_id, *, phu_luc=None, boq_them=None):  # đích lưu hợp lệ = BOQ gốc dòng 2 (fixture BOQ thật, có ID + dòng vật lý)
        from kho_tri_thuc.m4 import chung_tu_adapter as CA
        gn_rows = self.GN_CO_BAN + [[3, "Phụ kiện đặc biệt XYZ", "PKX9", "m", 7, ""]]  # dòng 9: máy không ghép được
        gn = self.gn(gn_rows)
        rid = CA.row_id(hashlib.sha256(gn[3]).hexdigest(), "XLSX|GiaoNhan|9")  # từ CHÍNH raw đã cấp
        nt = self.nt()
        rev = {"revision": 1, "tai_lieu": {nt[0]: {"ngay": "2026-03-05"}}}  # người dùng sửa ngày BB NT (revision 1)
        manual = [{"id": "m1", "row_id": rid, "ma_hm": "HM-01", "revision": 1, "boq_id": manual_boq_id, "boq_dong": 2, "raw_sha256": hashlib.sha256(gn[3]).hexdigest(),
                   "revision_chung_tu": 0}]
        kq, _ = self.chay([nt, gn], _basis(revision=rev, manual=manual, phu_luc=phu_luc, boq_them=boq_them))
        return kq, rid

    def test_ghep_tay_dich_hien_hanh_va_revision_metadata(self):
        ct = NR._m("may_chu.chung_tu")
        goc_ghep, goc_glob = ct.ghep_hang_muc, ct.doi_chieu.__globals__["ghep_hang_muc"]
        kq, rid = self._ghep_case(BOQ_ID)  # đích đã lưu = BOQ gốc dòng 2 = đích hiệu lực hiện hành của HM-01
        self.assertIs(ct.ghep_hang_muc, goc_ghep)  # module nguồn KHÔNG bị monkeypatch
        self.assertIs(ct.doi_chieu.__globals__["ghep_hang_muc"], goc_glob)
        hm = {h["khoa"]: h for h in kq["hang_muc"]}
        self.assertEqual([(str(x["boq_id"]), x["dong"]) for x in hm["HM-01"]["nguon_boq"]], [(BOQ_ID, 2)])  # projection seam: đích hiệu lực có ID/dòng
        g = next(x for x in kq["tai_lieu"] if x["loai"] == "BB_GN")
        ln = next(x for x in g["dong"] if x["row_id"] == rid)
        self.assertEqual((ln["khoa"], ln["khop"], ln["ghep_tay"]), ("HM-01", 1.0, True))
        auto = {x["row_id"]: x["khoa"] for d in kq["provenance"]["auto"]["tai_lieu"] for x in d["dong"]}
        self.assertIsNone(auto[rid])  # kết quả tự động của nguồn giữ riêng
        nk = kq["provenance"]["ghep_tay"]
        self.assertEqual([x["trang_thai"] for x in nk], ["DA_AP"])
        self.assertEqual((nk[0]["dich_luu"], nk[0]["dich_hien_hanh"]["boq_id"], nk[0]["dich_hien_hanh"]["dong"]), ({"boq_id": BOQ_ID, "dong": 2}, BOQ_ID, 2))
        self.assertTrue(any(f["code"] == "C04" for f in kq["provenance"]["auto"]["phat_hien"]))
        nt = next(x for x in kq["tai_lieu"] if x["loai"] == "BB_NT")
        self.assertEqual((nt["ngay"], nt["trich"]["ngay"]), ("2026-03-05", "2026-03-01"))  # hiệu lực ≠ bản trích bất biến
        self.assertTrue(any(f["code"] == "C02" for f in kq["phat_hien"]))  # ngày NT hiệu lực ≠ ngày nghiệm thu của đợt

    def test_ghep_tay_dich_cu_cung_ma_khong_tu_ap(self):
        # (a) BOQ nhập lại: cùng mã HM-01, cùng số dòng 2, nhưng boq_id hiện hành khác đích đã lưu
        from kho_tri_thuc.m4 import chung_tu_adapter as CA
        moi = {**BOQ_GOC, "id": BOQ_MOI_ID}
        gn = self.gn(self.GN_CO_BAN + [[3, "Phụ kiện đặc biệt XYZ", "PKX9", "m", 7, ""]])
        rid = CA.row_id(hashlib.sha256(gn[3]).hexdigest(), "XLSX|GiaoNhan|9")
        manual = [{"id": "m1", "row_id": rid, "ma_hm": "HM-01", "revision": 1, "boq_id": BOQ_ID, "boq_dong": 2}]
        b = _basis(manual=manual, boq=False, boq_them=[moi])
        kq, _ = self.chay([self.nt(), gn], b)
        ln = next(x for d in kq["tai_lieu"] for x in d["dong"] if x["row_id"] == rid)
        self.assertEqual((ln["khoa"], ln["ghep_tay"]), (None, False))  # không âm thầm áp chỉ vì cùng ma_hm
        nk = kq["provenance"]["ghep_tay"]
        self.assertEqual([x["trang_thai"] for x in nk], ["CAN_XAC_NHAN_LAI"])
        self.assertEqual((nk[0]["dich_luu"]["boq_id"], nk[0]["dich_hien_hanh"]["boq_id"]), (BOQ_ID, BOQ_MOI_ID))
        auto = {x["row_id"]: x["khoa"] for d in kq["provenance"]["auto"]["tai_lieu"] for x in d["dong"]}
        self.assertIsNone(auto[rid])
        # (b) phụ lục ĐÃ KÝ hiệu lực trước ngày NT THAY HM-01 → đích hiệu lực là dòng BOQ phụ lục; map cũ trỏ BOQ gốc → cần xác nhận lại
        pl = [{"id": PL_ID, "so_pl": "PL-01", "ngay_ky": "2026-01-10", "ngay_hieu_luc": "2026-01-15", "trang_thai": "DA_KY", "doi_boq": True, "tep_id": None}]
        bpl = {"id": BOQ_PL_ID, "lan": 1, "phu_luc_id": PL_ID, "trang_thai": "DA_MAP", "sheet": "BOQ", "dong": [_boq_dong(2, "HM-01", "Ống HDPE D110", "m", "600", "THAY")]}
        kq2, _ = self.chay([self.nt(), gn], _basis(manual=manual, phu_luc=pl, boq_them=[bpl]))
        nk2 = kq2["provenance"]["ghep_tay"]
        self.assertEqual([x["trang_thai"] for x in nk2], ["CAN_XAC_NHAN_LAI"])
        self.assertEqual(nk2[0]["dich_hien_hanh"]["boq_id"], BOQ_PL_ID)
        self.assertFalse(next(x for d in kq2["tai_lieu"] for x in d["dong"] if x["row_id"] == rid)["ghep_tay"])

    def test_khong_l2_khong_boq_chua_du_can_cu(self):
        kq, _ = self.chay([self.nt(), self.gn(self.GN_CO_BAN)], _basis(l2=False, boq=False))
        cov = kq["coverage"]
        self.assertEqual({k: cov[k]["trang_thai"] for k in ("C01", "C03", "C04", "CAN_CU")},
                         {"C01": "INCOMPLETE", "C03": "INCOMPLETE", "C04": "INCOMPLETE", "CAN_CU": "INCOMPLETE"})
        self.assertEqual(kq["hang_muc"], [])
        self.assertEqual(kq["so_sanh"], {})
        self.assertFalse(any(f["code"] in ("C01", "C03") for f in kq["phat_hien"]))  # ít phát hiện KHÔNG phải Đạt
        self.assertEqual(kq["trang_thai"], "PARTIAL")
        kq2, _ = self.chay([self.nt(), self.gn(self.GN_CO_BAN)], _basis(l2=False, ngay_nt=None))
        self.assertEqual(kq2["coverage"]["CAN_CU"]["trang_thai"], "INCOMPLETE")
        self.assertIn("ngày nghiệm thu", kq2["coverage"]["CAN_CU"]["ly_do"])

    def test_boq_only_va_l2_cu(self):
        kq, _ = self.chay([self.nt(), self.gn(self.GN_CO_BAN)], _basis(l2=False))
        self.assertEqual(sorted((h["khoa"], h["kl_kn"], h["kl_lk"]) for h in kq["hang_muc"]), [("HM-01", None, None), ("HM-02", None, None)])
        self.assertEqual(kq["coverage"]["CAN_CU"]["trang_thai"], "LIMITED")
        self.assertEqual({v["C01"]["trang_thai"] for v in kq["so_sanh"].values()}, {"CHUA_SO_DUOC"})
        kq2, _ = self.chay([self.nt(), self.gn(self.GN_CO_BAN)], _basis(l2="CU"))  # L2 đã công bố nhưng căn cứ đổi
        self.assertEqual(kq2["coverage"]["CAN_CU"]["trang_thai"], "INCOMPLETE")
        self.assertEqual(kq2["provenance"]["l2_cu"]["run_id"], "l2-cu")
        self.assertTrue(all(h["kl_kn"] is None for h in kq2["hang_muc"]))  # không dùng lượng L2 cũ
        self.assertIn("chạy lại Review L1+L2", kq2["coverage"]["CAN_CU"]["ly_do"])

    def test_bo_khoi_bo_va_work_ref_an_toan(self):
        from kho_tri_thuc.m4 import chung_tu_adapter as CA
        gn = self.gn(self.GN_CO_BAN)
        kq, tm = self.chay([self.nt(), gn], _basis(revision={"revision": 1, "tai_lieu": {gn[0]: {"bo": True}}}))
        self.assertTrue(next(x for x in kq["tai_lieu"] if x["tep_id"] == gn[0])["bo"])
        self.assertEqual(kq["coverage"]["C03"]["trang_thai"], "INCOMPLETE")  # BB giao nhận bị bỏ khỏi lần kiểm này
        for xau in ("/etc/x", "..\\x", "a/../../x", "C:/x", ""):
            with self.assertRaises(RuntimeError, msg=xau):
                CA.duong_lam_viec(tm, xau)


# ================================================================================================== L3 A1/A2 thuần (không lõi nguồn) — NOT_RUN_CODE_ONLY
class L3ViTriThuan(unittest.TestCase):
    """Locator ô/tiêu đề trên bản đồ viết tay: vị trí không xác định → NOT_AVAILABLE/LIMITED có lý do, không bao giờ CHECKED giả; regex alias fullmatch."""

    def test_re_ten_hang_khong_hau_to_tuy_y(self):
        from kho_tri_thuc.m4 import chung_tu_adapter as CA
        for s in ("tên hàng", "tên hàng hóa", "tên hàng hoá"):
            self.assertIsNotNone(CA.RE_TEN_HANG.fullmatch(s), s)
        for s in ("tên hàng / nhà sản xuất", "tên hàng (hãng sản xuất)", "tên hàng/nsx", "tên hãng", "ten hang", "tên hàng model", "hãng"):
            self.assertIsNone(CA.RE_TEN_HANG.fullmatch(s), s)

    def test_vi_tri_o_xlsx(self):
        from kho_tri_thuc.m4 import chung_tu_adapter as CA
        x = CA.vi_tri_o(NR.MEDIA_XLSX, None, 1, 0, 0, "Seam vị trí lỗi (OSError) — vị trí vật lý không xác định")
        self.assertEqual((x["trang_thai"], x["ly_do"]), ("NOT_AVAILABLE", "Seam vị trí lỗi (OSError) — vị trí vật lý không xác định"))
        bd = {"bang": [{"sheet": "S", "dong": [2, 5], "cot_dau": 1, "o_gop": ["B5:C5"]}]}
        for bi, h0, j in ((2, 0, 0), (1, 2, 0), (None, None, 1), (1, None, 0), (0, 0, 0)):
            r = CA.vi_tri_o(NR.MEDIA_XLSX, bd, bi, h0, j)
            self.assertEqual(r["trang_thai"], "NOT_AVAILABLE", (bi, h0, j))
            self.assertTrue(r["ly_do"])
        a = CA.vi_tri_o(NR.MEDIA_XLSX, bd, 1, 1, 1)
        self.assertEqual((a["trang_thai"], a["sheet"], a["dong"], a["cot"], a["o"], a["o_gop"], a["bang_nguon"], a["dong_nguon"], a["cot_nguon"]),
                         ("CHECKED", "S", 5, 2, "B5", "B5:C5", 1, 2, 2))
        b = CA.vi_tri_o(NR.MEDIA_XLSX, bd, 1, 1, 2)  # C5 trong vùng gộp, không phải ô trên-trái
        self.assertEqual((b["trang_thai"], b["o"], b["o_gop"]), ("LIMITED", "C5", "B5:C5"))
        c = CA.vi_tri_o(NR.MEDIA_XLSX, bd, 1, 0, 27)
        self.assertEqual((c["trang_thai"], c["o"], c.get("o_gop")), ("CHECKED", "AB2", None))
        bd2 = {"bang": [{"sheet": "S", "dong": [2], "cot_dau": 1, "o_gop": None}], "o_gop_ly_do": "Không đọc được danh sách ô gộp (X)"}
        d = CA.vi_tri_o(NR.MEDIA_XLSX, bd2, 1, 0, 0)
        self.assertEqual((d["trang_thai"], d["ly_do"], d["o"]), ("LIMITED", "Không đọc được danh sách ô gộp (X)", "A2"))
        e = CA.vi_tri_o(NR.MEDIA_XLSX, {"bang": [{"sheet": "S", "dong": [2]}]}, 1, 0, 0)  # bản đồ cũ không có cột đầu
        self.assertEqual((e["trang_thai"], e["dong"], "cot" in e), ("LIMITED", 2, False))

    def test_vi_tri_o_docx(self):
        from kho_tri_thuc.m4 import chung_tu_adapter as CA
        dx = {"bang": [{"bang_vat_ly": 3, "dong": [1, 4],
                        "o": [[[1, 0, None], [1, 1, None], [2, 0, None]], [[1, 0, None], [2, 0, "continue"], [3, 0, "restart"]]]}]}
        d0 = CA.vi_tri_o(NR.MEDIA_DOCX, dx, 1, 0, 1)
        self.assertEqual((d0["trang_thai"], d0["tc"], d0["grid_span"]), ("LIMITED", 1, 2))
        self.assertIn("gridSpan", d0["ly_do"])
        d1 = CA.vi_tri_o(NR.MEDIA_DOCX, dx, 1, 0, 2)
        self.assertEqual((d1["trang_thai"], d1["bang"], d1["dong"], d1["tc"], d1["logic_khac_vat_ly"]), ("CHECKED", 3, 1, 2, True))
        d2 = CA.vi_tri_o(NR.MEDIA_DOCX, dx, 1, 1, 1)
        self.assertEqual((d2["trang_thai"], d2["dong"], d2["v_merge"]), ("LIMITED", 4, "continue"))
        d3 = CA.vi_tri_o(NR.MEDIA_DOCX, dx, 1, 1, 2)
        self.assertEqual((d3["trang_thai"], d3["tc"], d3["v_merge"], d3["logic_khac_vat_ly"]), ("CHECKED", 3, "restart", False))
        self.assertEqual(CA.vi_tri_o(NR.MEDIA_DOCX, dx, 1, 1, 5)["trang_thai"], "LIMITED")  # cột logic ngoài dòng
        self.assertEqual(CA.vi_tri_o(NR.MEDIA_DOCX, {"bang": [{"bang_vat_ly": 1, "dong": [1]}]}, 1, 0, 0)["trang_thai"], "LIMITED")  # không có map ô

    def test_gan_vi_tri_dong_tieu_de_khong_doi_row_id(self):
        from kho_tri_thuc.m4 import chung_tu_adapter as CA
        sha = "ab" * 32
        dong = [{"vi_tri": "bảng 1 dòng 2"}, {"vi_tri": "bảng 2 dòng 1"}]
        CA.gan_vi_tri(dong, NR.MEDIA_XLSX, {"bang": [{"sheet": "S", "dong": [3, 7]}]}, sha, "t", None, tieu_de={1: 0})
        self.assertEqual(dong[0]["vi_tri_vat_ly"], {"trang_thai": "CHECKED", "loai": "XLSX", "sheet": "S", "dong": 7, "nguon": "bảng 1 dòng 2", "dong_tieu_de": 3})
        self.assertEqual(dong[0]["row_id"], hashlib.sha256(f"m4.chung_tu.row/1|{sha}|XLSX|S|7".encode("utf-8")).hexdigest())
        self.assertEqual(dong[1]["vi_tri_vat_ly"]["trang_thai"], "NOT_AVAILABLE")
        self.assertEqual(dong[1]["row_id"], hashlib.sha256(f"m4.chung_tu.row/1|{sha}|NGUON|bảng 2 dòng 1|1".encode("utf-8")).hexdigest())


if __name__ == "__main__":
    unittest.main()
