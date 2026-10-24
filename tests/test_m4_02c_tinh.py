"""M4-02C — kiểm TĨNH + THUẦN cho Duyệt & PDF (không PostgreSQL, không mạng, không Office). CODE_ONLY: coder viết, CHƯA CHẠY (WRITTEN_NOT_RUN).

Phân loại:
- `M24Tinh`: registry append (24 mục, [-1] là M0024, [22] là M0023 giữ nguyên), chuỗi SQL M24 (FK tổ hợp PDF/seal, vật liệu trong cả ba lệnh, seal
  dùng chung, CHUA_KET_LUAN trước INSERT PDF, REVOKE EXECUTE mọi hàm lệnh, RLS mọi bảng, không GRANT EXECUTE, không DROP bảng/hàm).
- `HttpTinh`: bảng TRUONG/KHONG_NHAN/mã lỗi khớp chữ ký service; đúng MỘT tài sản /m4/m4_duyet_pdf.js (200 no-store khi có, 404 khi vắng — gọi
  `dieu_huong` với handler giả + ASSETS tạm, không máy chủ).
- `KiemDauVao`: validator tiền/khối lượng/tiền tệ/dòng/xử lý/căn cứ với literal viết tay (fixtures_m4).
- `ThuanDTO`: so_chuan, vat_lieu, _pb_dto, _kt, ma trận _trang_thai, lich_su_da_duyet (không schema → None) bằng đối tượng giả.
- `DemoTinh`: hằng m4_demo + khoi_tao_duyet trên kết nối giả chưa có M24 → CHUA_SAN_SANG (không ghi).
"""

from __future__ import annotations

import inspect
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kho_tri_thuc.giao_dien import m4 as GM4
from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import m4_demo
from kho_tri_thuc.kiem_chung import fixtures_m4 as F
from kho_tri_thuc.m4 import duyet_dot as DD
from kho_tri_thuc.m4 import sql_duyet as SD

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
HEX_A = "a" * 64


def _ma(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except DataError as exc:
        return exc.code
    return None


def _ham(noi: str, ten: str) -> str:
    """Thân một hàm SQL trong M24 (từ CREATE OR REPLACE FUNCTION <ten>( tới END $$ đầu tiên sau đó)."""
    i = noi.index(f"CREATE OR REPLACE FUNCTION {ten}(")
    return noi[i:noi.index("END $$", i)]


# ================================================================================================== tĩnh: migration
class M24Tinh(unittest.TestCase):
    S = SD.M0024_M4_DUYET
    NOI = "\n".join(SD.M0024_M4_DUYET)

    def test_registry_append_24(self):
        self.assertEqual((PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS)), (24, 24))
        self.assertIs(PM.PG_MIGRATIONS[-1], SD.M0024_M4_DUYET)
        self.assertIs(PM.PG_MIGRATIONS[22], PM.M0023_CRM_KY)
        self.assertIs(PM.PG_MIGRATIONS[21], PM.M0022_M4_CHUNG_TU)
        duoi = (SRC / "ha_tang" / "pg_migrations.py").read_text(encoding="utf-8")
        self.assertTrue(duoi.rstrip().endswith("PG_MIGRATIONS = (*PG_MIGRATIONS, M0024_M4_DUYET)\nPG_SCHEMA_VERSION = len(PG_MIGRATIONS)"), duoi[-200:])
        self.assertIn("from ..m4.sql_duyet import M0024_M4_DUYET", duoi)
        # sql_duyet chỉ hằng SQL: không import ha_tang (tránh vòng import với pg_migrations)
        self.assertNotRegex((SRC / "m4" / "sql_duyet.py").read_text(encoding="utf-8"), r"(?m)^\s*(from|import)\s+\.\.ha_tang")

    def test_khong_xoa_khong_role(self):
        for s in self.S:
            self.assertIsNone(re.search(r"DROP\s+(TABLE|FUNCTION|POLICY|TRIGGER|SCHEMA)|\bTRUNCATE\b|DELETE\s+FROM|CREATE\s+ROLE|GRANT\s+EXECUTE", s), s[:120])
            self.assertNotIn("CREATE OR REPLACE FUNCTION master.m4_duoc(", s)  # m4_duoc KHÔNG đổi — DUYET kiểm riêng
            self.assertNotIn("CREATE OR REPLACE FUNCTION m4._bn_", s)
        # DROP duy nhất: ràng buộc CHECK vai cũ của m4.quyen_du_an (nới thêm DUYET)
        self.assertEqual(len(re.findall(r"DROP\s+CONSTRAINT", self.NOI)), 1)
        self.assertIn("CHECK (vai IN ('PHU_TRACH','XEM','REVIEW','DUYET'))", self.NOI)

    def test_bang_rls_quyen(self):
        for t in SD.BANG:
            self.assertIn(f"CREATE TABLE m4.{t} (", self.NOI)
            self.assertIn(f"ALTER TABLE m4.{t} ENABLE ROW LEVEL SECURITY", self.NOI)
            self.assertIn(f"ON m4.{t} FOR SELECT TO app_web", self.NOI)
        for t in SD.BANG_GHI_THEM:
            self.assertIn(f"CREATE TRIGGER {t}_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON m4.{t}", self.NOI)
        revoke = next(s for s in self.S if s.startswith("REVOKE EXECUTE ON FUNCTION"))
        for f in SD.HAM_LENH:
            self.assertIn(f, revoke)
        for f in SD.HAM_LENH:  # mọi hàm lệnh (gồm seal nội bộ) chỉ chạy trên kết nối chủ bảng
            ten = f.split("(", 1)[0]
            self.assertIn("master.la_chu_bang('m4.duyet_phien_ban'::regclass)", _ham(self.NOI, ten), ten)
        for f in ("m4.duyet_doc_dot", "m4.duyet_quyen", "m4.duyet_kiem"):  # đọc: SECURITY DEFINER, không raise lộ tồn tại ngoài mã 404
            self.assertIn("SECURITY DEFINER", _ham(self.NOI, f))

    def test_fk_pdf_seal(self):
        pdf = self.NOI[self.NOI.index("CREATE TABLE m4.duyet_pdf ("):self.NOI.index("CREATE TABLE m4.duyet_seal (")]
        for x in ("FOREIGN KEY (ket_luan_id, phien_ban_id) REFERENCES m4.duyet_ket_luan (id, phien_ban_id)",
                  "FOREIGN KEY (ket_luan_id, graph_sha256) REFERENCES m4.duyet_ket_luan (id, graph_sha256)",
                  "UNIQUE (ket_luan_id, raw_sha256)", "CHECK (object_key = 'm4-raw/' || raw_sha256)", f"CHECK (vai = '{SD.VAI_PDF}')",
                  "CHECK (media_type = 'application/pdf')"):
            self.assertIn(x, pdf)
        seal = self.NOI[self.NOI.index("CREATE TABLE m4.duyet_seal ("):self.NOI.index("CREATE TABLE m4.duyet_kt_cho (")]
        for x in ("phien_ban_id uuid NOT NULL UNIQUE", "quyet_dinh_id uuid NOT NULL UNIQUE",
                  "FOREIGN KEY (pdf_id, ket_luan_id) REFERENCES m4.duyet_pdf (id, ket_luan_id)",
                  "FOREIGN KEY (quyet_dinh_id, ket_luan_id) REFERENCES m4.duyet_quyet_dinh (id, ket_luan_id)",
                  "FOREIGN KEY (ket_luan_id, graph_sha256) REFERENCES m4.duyet_ket_luan (id, graph_sha256)"):
            self.assertIn(x, seal)
        self.assertIn("dot_id uuid NOT NULL UNIQUE REFERENCES m4.dot(id)", self.NOI)  # một gốc KT/đợt
        self.assertIn("CHECK ((thu_tu = 1) = (truoc_id IS NULL))", self.NOI)

    def test_vat_lieu_va_thu_tu_lenh(self):
        for f in ("m4.duyet_ghi_ket_luan", "m4.duyet_chap_thuan", "m4.duyet_ghi_pdf"):
            than = _ham(self.NOI, f)
            self.assertIn("M4_DUYET_CAN_PHIEN_BAN_MOI", than, f)
            self.assertLess(than.index("m4.duyet_khoa("), than.index("m4._bn_tra("), f)  # quyền + khóa TRƯỚC biên nhận
        pdf = _ham(self.NOI, "m4.duyet_ghi_pdf")
        self.assertLess(pdf.index("M4_DUYET_CHUA_KET_LUAN"), pdf.index("INSERT INTO m4.duyet_pdf"))
        self.assertLess(pdf.index("M4_DUYET_DA_SEAL"), pdf.index("INSERT INTO m4.duyet_pdf"))
        self.assertIn("m4._duyet_seal(v.id, p_graph_hien_tai, moi)", pdf)
        self.assertIn("m4._duyet_seal(v.id, p_graph_hien_tai, NULL)", _ham(self.NOI, "m4.duyet_chap_thuan"))
        seal = _ham(self.NOI, "m4._duyet_seal")
        i_kl = seal.index("'CAN_KIEM_LAI'")
        self.assertIn("v.revision_ho_so IS DISTINCT FROM", seal[:i_kl])
        self.assertLess(i_kl, seal.index("'CHO_PDF'"))
        self.assertIn("ket_luan_id = q.ket_luan_id AND graph_sha256 = q.graph_sha256", seal)  # chỉ ứng viên gắn đúng kết luận được duyệt
        self.assertIn("ON CONFLICT (dot_id) DO NOTHING", seal)
        self.assertNotRegex(self.NOI, r"(?i)(CREATE TABLE|INSERT INTO)\s+\w+\.\w*(ap|request|cong_no)\b")  # không AP/Request
        self.assertIn("'ap', 'CHUA_NOI_GOI_M4_03', 'request', 'CHUA_NOI_GOI_M4_04'", seal)
        khoa = _ham(self.NOI, "m4.duyet_khoa")
        self.assertLess(khoa.index("m4.ho_so_hop_dong"), khoa.index("FROM m4.dot WHERE id = p_dot FOR UPDATE"))
        self.assertLess(khoa.index("FROM m4.dot WHERE id = p_dot FOR UPDATE"), khoa.index("FROM m4.duyet_phien_ban"))

    def test_quyen_dto(self):
        q = _ham(self.NOI, "m4.duyet_quyen")
        self.assertIn("'tai_pdf', d_tt = 'DA_NOP' AND (soan OR du)", q)
        self.assertIn("'duyet', d_tt = 'DA_NOP' AND du", q)
        self.assertIn("'ket_luan', d_tt = 'DA_NOP' AND (rv OR du)", q)


# ================================================================================================== tĩnh: HTTP
class _H:
    def __init__(self):
        self.gui = []

    def send_content(self, status, body, mime=None, headers=None):
        self.gui.append((status, body, mime, headers))


class HttpTinh(unittest.TestCase):
    def _kw(self, fn) -> set:
        return {p.name for p in inspect.signature(fn).parameters.values() if p.kind is inspect.Parameter.KEYWORD_ONLY}

    def test_truong_khop_chu_ky(self):
        self.assertEqual(self._kw(DD.DuyetDot.ket_luan), GM4.TRUONG["duyet/ket-luan"])
        self.assertEqual(self._kw(DD.DuyetDot.chap_thuan), GM4.TRUONG["duyet/chap-thuan"])
        self.assertEqual(self._kw(DD.DuyetDot.phien_ban), GM4.TRUONG["duyet/phien-ban"])
        self.assertEqual(self._kw(DD.DuyetDot.phien_ban_nop), GM4.TRUONG["duyet/phien-ban/nop"])
        self.assertEqual(self._kw(DD.DuyetDot.pdf), GM4.TRUONG_DUYET_PDF)
        for k in GM4.DUYET_LENH:
            self.assertFalse(GM4.TRUONG[k] & GM4.KHONG_NHAN, k)
        self.assertFalse(GM4.TRUONG_DUYET_PDF & GM4.KHONG_NHAN)
        self.assertFalse(GM4.DUYET_GET & GM4.KHONG_NHAN)
        self.assertTrue({"actor", "trang_thai", "duyet", "sha256", "vai", "quyen", "raw_sha256"} <= GM4.KHONG_NHAN)
        self.assertTrue(GM4.DUYET_LENH <= GM4.LENH_RIENG)
        self.assertEqual(GM4.DUYET_GET, {"dot_id", "version_id"})

    def test_ma_loi(self):
        self.assertTrue({"M4_DUYET_PHAM_VI", "M4_CLIENT_AUTHORITY"} <= GM4.MA_403)
        self.assertIn("M4_DUYET_KHONG_THAY", GM4.MA_404)
        sql_ma = set(re.findall(r"'(M4_DUYET_[A-Z_]+):", "\n".join(SD.M0024_M4_DUYET)))
        py_ma = set(re.findall(r'"(M4_DUYET_[A-Z_]+)"', (SRC / "m4" / "duyet_dot.py").read_text(encoding="utf-8")))
        bat_dong_bo = {"M4_DUYET_PHAM_VI", "M4_DUYET_KHONG_THAY", "M4_DUYET_SO_SAI", "M4_DUYET_CO_SO_SAI", "M4_DUYET_PDF_SAI_VAI_TRO"}
        for m in (sql_ma | py_ma) - bat_dong_bo:  # mọi xung đột căn cứ/trạng thái → 409 (giữ nháp, tải lại)
            self.assertIn(m, GM4.MA_409_DUYET, m)
        for m in ("M4_DUYET_SO_SAI", "M4_DUYET_CO_SO_SAI", "M4_DUYET_PDF_SAI_VAI_TRO"):  # đầu vào sai → 400
            self.assertFalse(m in GM4.MA_403 or m in GM4.MA_404 or m in GM4.MA_409_DUYET or m in GM4.MA_409, m)

    def test_tai_san_mot_route(self):
        with tempfile.TemporaryDirectory(prefix="ktt_m4_02c_tinh_") as tam:
            tam = Path(tam)
            with patch.object(GM4, "ASSETS", tam):
                h = _H()
                GM4.dieu_huong(h, None, False, "/m4/m4_duyet_pdf.js", {})
                self.assertEqual((h.gui[0][0], h.gui[0][1]["error"]), (404, "NOT_FOUND"))
                self.assertFalse((tam / "m4_duyet_pdf.js").exists())  # không stub
                (tam / "m4_duyet_pdf.js").write_bytes(b"/* UI head */\n")
                h = _H()
                GM4.dieu_huong(h, None, False, "/m4/m4_duyet_pdf.js", {})
                st, body, mime, headers = h.gui[0]
                self.assertEqual((st, body, mime, headers), (200, b"/* UI head */\n", "text/javascript; charset=utf-8", {"Cache-Control": "no-store"}))
                for xau in ("/m4/m4-duyet-pdf.js", "/m4/m4_duyet_pdf.js/x", "/m4/../m4_duyet_pdf.js", "/m4/m4_duyet_pdf.css", "/m4/M4_DUYET_PDF.JS"):
                    h = _H()
                    GM4.dieu_huong(h, None, False, xau, {})
                    self.assertNotEqual(h.gui[0][0], 200, xau)

    def test_query_nghiem(self):
        self.assertEqual(_ma(GM4._q, {"dot_id": ["x"], "actor": ["A"]}, GM4.DUYET_GET), "M4_YEU_CAU_SAI")
        self.assertEqual(_ma(GM4._q, {"dot_id": ["x", "y"]}, GM4.DUYET_GET), "M4_YEU_CAU_SAI")
        self.assertEqual(_ma(GM4._q, {"raw_sha256": ["a"]}, set()), "M4_YEU_CAU_SAI")
        self.assertEqual(GM4._q({"dot_id": ["x"]}, GM4.DUYET_GET), {"dot_id": "x"})
        self.assertEqual(_ma(GM4._than, {"dot_id": "x", "vai": "HO_SO_DOT_DA_DUYET"}, GM4.TRUONG_DUYET_PDF), "M4_CLIENT_AUTHORITY")
        self.assertEqual(_ma(GM4._than, {"dot_id": "x", "la": 1}, GM4.TRUONG_DUYET_PDF), "M4_YEU_CAU_SAI")


# ================================================================================================== thuần: kiểm đầu vào
class KiemDauVao(unittest.TestCase):
    def test_tien(self):
        for v in F.TIEN_HOP_LE:
            self.assertEqual(DD.tien(v, "x", vnd=False), v)
        for v in F.TIEN_SAI:
            self.assertEqual(_ma(DD.tien, v, "x", vnd=False), "M4_DUYET_SO_SAI", repr(v))
        self.assertIsNone(DD.tien(None, "x", vnd=True))  # null = CHƯA CÓ, khác "0"
        self.assertEqual(DD.tien("0", "x", vnd=True), "0")
        for v in ("12.5", "12.05", "999999999999999999.99"):
            self.assertEqual(_ma(DD.tien, v, "x", vnd=True), "M4_DUYET_SO_SAI", v)
        for k in SD.TIEN:
            self.assertIsNone(_ma(DD.tien, F.KET_LUAN_VND[k], k, vnd=True), k)
        self.assertIsNone(F.KET_LUAN_VND_THIEU_TT["so_xin_thanh_toan"])
        self.assertNotEqual(F.KET_LUAN_NT_KHAC_TT["gia_tri_nt"], F.KET_LUAN_NT_KHAC_TT["so_xin_thanh_toan"])

    def test_khoi_luong(self):
        for v in F.KL_HOP_LE + F.KL_CHAP_NHAN:
            self.assertEqual(DD.khoi_luong(v, "x"), v)
        for v in F.KL_SAI:
            self.assertEqual(_ma(DD.khoi_luong, v, "x"), "M4_DUYET_SO_SAI", repr(v))
        self.assertIsNone(DD.khoi_luong(None, "x"))

    def test_tien_te_dong_xu_ly(self):
        self.assertEqual(DD.kiem_tien_te("VND"), "VND")
        self.assertIsNone(DD.kiem_tien_te(None))
        for v in ("vnd", "VN", "VNDD", 704):
            self.assertEqual(_ma(DD.kiem_tien_te, v), "M4_DUYET_SO_SAI", repr(v))
        self.assertEqual(DD.kiem_dong_nt([{"row_id": "b", "khoi_luong_chap_nhan": "1"}, {"row_id": "a", "khoi_luong_chap_nhan": None}]),
                         [{"row_id": "a", "khoi_luong_chap_nhan": None}, {"row_id": "b", "khoi_luong_chap_nhan": "1"}])
        self.assertEqual(_ma(DD.kiem_dong_nt, [{"row_id": "a", "khoi_luong_chap_nhan": "1"}] * 2), "M4_THAM_SO_SAI")
        self.assertEqual(_ma(DD.kiem_dong_nt, [{"row_id": "a", "khoi_luong_chap_nhan": "1", "de_xuat": "9"}]), "M4_THAM_SO_SAI")
        self.assertEqual(_ma(DD.kiem_dong_nt, [{"row_id": "a", "khoi_luong_chap_nhan": 1}]), "M4_DUYET_SO_SAI")
        self.assertEqual(_ma(DD.kiem_dong_nt, {"a": "1"}), "M4_THAM_SO_SAI")
        self.assertEqual(DD.kiem_xu_ly([{"finding_id": "L3:0:X", "ly_do": "Đã soát"}]), [{"finding_id": "L3:0:X", "ly_do": "Đã soát"}])
        self.assertEqual(_ma(DD.kiem_xu_ly, [{"finding_id": "L3:0:X", "ly_do": " "}]), "M4_THIEU_LY_DO")
        self.assertEqual(_ma(DD.kiem_xu_ly, [{"finding_id": "L3:0:X"}]), "M4_THAM_SO_SAI")
        self.assertEqual(_ma(DD.kiem_xu_ly, [{"finding_id": "x", "ly_do": "a"}, {"finding_id": "x", "ly_do": "b"}]), "M4_THAM_SO_SAI")

    def test_can_cu_ly_do(self):
        self.assertEqual(DD._hex(HEX_A), HEX_A)
        for v in (None, "A" * 64, "a" * 63, 1, "g" * 64):
            self.assertEqual(_ma(DD._hex, v), "M4_DUYET_CO_SO_SAI", repr(v))
        self.assertEqual(_ma(DD._ly_do, None, bat_buoc=True), "M4_THIEU_LY_DO")
        self.assertIsNone(DD._ly_do("  ", bat_buoc=False))
        self.assertEqual(_ma(DD._ly_do, "a\x00b", bat_buoc=False), "M4_THAM_SO_SAI")
        self.assertEqual(_ma(DD._ly_do, "x" * (DD.LY_DO_TOI_DA + 1), bat_buoc=False), "M4_THAM_SO_SAI")
        self.assertEqual(_ma(DD._uuid, "khong-uuid", "dot_id"), "M4_THAM_SO_SAI")
        self.assertEqual(_ma(DD._rev, True), "M4_THAM_SO_SAI")
        self.assertEqual(_ma(DD._rev, -1), "M4_THAM_SO_SAI")
        self.assertEqual(DD._rev(0), 0)

    def test_regex_py_khop_sql(self):  # cùng định nghĩa thập phân chuẩn ở máy chủ và CHECK CSDL
        self.assertIn(DD.TIEN_RE.pattern, SD._TIEN)
        self.assertIn(DD.KL_RE.pattern, SD._KL)


# ================================================================================================== thuần: DTO/trạng thái
class ThuanDTO(unittest.TestCase):
    def test_so_chuan(self):
        for x, y in ((None, None), (True, None), (100, "100"), (22.5, "22.5"), ("1.500", "1.5"), ("0.000", "0"), (float("nan"), None),
                     (float("inf"), None), ("", None), ("abc", None), (1e-7, "0.0000001")):
            self.assertEqual(DD.so_chuan(x), y, repr(x))

    def test_vat_lieu(self):
        self.assertEqual(DD.vat_lieu({"revision_ho_so_hien_hanh": 3}, {"revision_ho_so": 3})["khop"], True)
        self.assertEqual(DD.vat_lieu({"revision_ho_so_hien_hanh": 4}, {"revision_ho_so": 3})["khop"], False)
        self.assertEqual(DD.vat_lieu({"revision_ho_so_hien_hanh": None}, {"revision_ho_so": None})["khop"], False)  # NHÁP chưa nộp ≠ khớp

    def test_pb_dto(self):
        v = {k: None for k in ("parent_id", "nop_id", "ly_do", "digest", "revision_ho_so", "tao_boi", "tao_luc", "nop_boi", "nop_luc",
                               "ket_luan_revision", "quyet_dinh_id", "seal_id")}
        v.update(id="v1", so=1, trang_thai="DA_NOP")
        self.assertTrue(DD._pb_dto(v, "v1")["moi_nhat"])
        d = DD._pb_dto(v, "v2")
        self.assertFalse(d["moi_nhat"])
        self.assertNotIn("snapshot", d)
        self.assertEqual((d["version_id"], d["parent_version_id"]), ("v1", None))

    def test_kt(self):
        self.assertEqual(DD._kt(None, None, [])["trang_thai"], "CHUA_CHUYEN")
        pb = [{"id": "b1", "seal_id": "s1"}, {"id": "b2", "seal_id": "s2"}]
        k = DD._kt({"id": "s1"}, {"id": "g"}, pb)
        self.assertEqual((k["trang_thai"], k["pending_id"], k["phong_bi_id"], k["phong_bi_hien_hanh"]), ("CHO_XAC_NHAN", "g", "b1", False))
        k = DD._kt({"id": "s2"}, {"id": "g"}, pb)
        self.assertEqual((k["phong_bi_id"], k["phong_bi_hien_hanh"], k["ly_do"]), ("b2", True, None))
        k = DD._kt(None, {"id": "g"}, pb)  # phiên bản chưa seal: gốc là lịch sử, KHÔNG phải bàn giao của phiên bản này
        self.assertEqual((k["trang_thai"], k["pending_id"], k["goc_id"]), ("CHUA_CHUYEN", None, "g"))

    def test_trang_thai(self):
        tt = DD.DuyetDot._trang_thai
        nop = {"trang_thai": "DA_NOP"}
        g = {"vat_lieu": {"khop": True}, "l3": {"trang_thai": "CO"}}
        g_doi = {"vat_lieu": {"khop": False}, "l3": {"trang_thai": "CO"}}
        g_l3 = {"vat_lieu": {"khop": True}, "l3": {"trang_thai": "CU", "ly_do": "cũ"}}
        kl = {"graph_sha256": "g1", "thieu": []}
        qd = {"graph_sha256": "g1"}
        self.assertEqual(tt(nop, True, g, "g1", None, None, {"id": "s"})[0], "DA_SEAL")
        self.assertEqual(tt({"trang_thai": "NHAP"}, True, g, "g1", None, None, None)[0], "CAN_KIEM_LAI")
        self.assertEqual(tt(nop, False, g, "g1", kl, None, None)[0], "CAN_KIEM_LAI")
        self.assertEqual(tt(nop, True, g_doi, "g1", kl, qd, None)[0], "CAN_KIEM_LAI")  # vật liệu đổi xét TRƯỚC quyết định
        self.assertEqual(tt(nop, True, g, "g1", kl, qd, None)[0], "CHO_PDF")
        self.assertEqual(tt(nop, True, g, "g2", kl, qd, None)[0], "CAN_KIEM_LAI")
        self.assertEqual(tt(nop, True, g_l3, "g1", None, None, None), ("CAN_KIEM_LAI", "cũ"))
        self.assertEqual(tt(nop, True, g, "g1", kl, None, None)[0], "CHO_DUYET")
        self.assertEqual(tt(nop, True, g, "g2", kl, None, None)[0], "CAN_KIEM_LAI")
        self.assertEqual(tt(nop, True, g, "g1", {"graph_sha256": "g1", "thieu": [{"ma": "TIEN_THIEU"}]}, None, None)[0], "CHO_KET_LUAN")
        self.assertEqual(tt(nop, True, g, "g1", None, None, None)[0], "CHO_KET_LUAN")
        for x in ("CHO_KET_LUAN", "CHO_DUYET", "CHO_PDF", "DA_SEAL", "CAN_KIEM_LAI"):
            self.assertIn(x, DD.TRANG_THAI)

    def test_lich_su_khong_schema(self):
        class XD:
            def _r1(self, c, sql, params=()):
                return {"co": False}

            def _rn(self, c, sql, params=()):
                raise AssertionError("không được truy vấn khi chưa có schema M24")
        self.assertIsNone(DD.lich_su_da_duyet(XD(), None, None))
        self.assertIsNone(DD.lich_su_da_duyet(XD(), None, {"hop_dong_id": "h", "so_dot": None}))
        self.assertIsNone(DD.lich_su_da_duyet(XD(), None, {"hop_dong_id": "h", "so_dot": 2, "ngay_nghiem_thu": "2026-03-01"}))


# ================================================================================================== thuần: DEMO + fixture
class _Cur:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class _ConnChuaM24:
    """Kết nối giả: chỉ trả lời to_regclass = false; mọi câu ghi → lỗi (chứng minh helper không ghi khi chưa sẵn sàng)."""

    def transaction(self):
        import contextlib
        return contextlib.nullcontext()

    def execute(self, sql, params=()):
        if "to_regclass" in sql:
            return _Cur((False,))
        raise AssertionError("khoi_tao_duyet không được ghi/truy vấn khác khi chưa có M24: " + sql[:80])


class DemoTinh(unittest.TestCase):
    def test_hang(self):
        self.assertEqual(m4_demo.MARKER_DUYET, "demo_seed_m4_duyet")
        self.assertEqual(m4_demo.dang_nhap_m4_duyet(), ["MO_PHONG_DUYET_M4"])
        self.assertIn("MO_PHONG_DUYET_M4", m4_demo.dang_nhap_m4())
        self.assertEqual(m4_demo.NGUOI_DUNG_DUYET[0][3], [("DA_XD_A1", "DUYET")])
        for n in m4_demo.NGUOI_DUNG:  # không actor gốc nào có DUYET (review-only vẫn là ca âm)
            self.assertNotIn("DUYET", [v for _, v in n[3]], n[0])

    def test_chua_san_sang(self):
        r = m4_demo.khoi_tao_duyet(_ConnChuaM24())
        self.assertEqual((r["trang_thai"], r["actor"], r["dem"]), ("CHUA_SAN_SANG", [], {"actor": 0, "phan_quyen": 0, "quyen_du_an": 0}))

    def test_fixture(self):
        a, b = F.ho_so_dot_duyet_pdf(), F.ho_so_dot_duyet_pdf("KHAC")
        self.assertTrue(a.startswith(b"%PDF-") and b"%%EOF" in a[-1024:])
        self.assertNotEqual(a, b)
        self.assertTrue(F.PDF_BI_CAT.startswith(b"%PDF-") and b"%%EOF" not in F.PDF_BI_CAT)
        self.assertFalse(F.KHONG_PHAI_PDF.startswith(b"%PDF-"))
        self.assertEqual(set(F.KET_LUAN_VND), {"tien_te", *SD.TIEN})
        self.assertEqual(len(F.BOQ_DOI_SAU_NOP), len(F.BOQ_GOC))
        self.assertNotEqual(F.BOQ_DOI_SAU_NOP, F.BOQ_GOC)


if __name__ == "__main__":
    unittest.main()
