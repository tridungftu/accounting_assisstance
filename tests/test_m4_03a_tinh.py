"""M4-03A — kiểm TĨNH + THUẦN cho inbox kế toán / xác nhận nguồn nghiệm thu (không PostgreSQL, không mạng). CODE_ONLY: WRITTEN_NOT_RUN.

Phân loại (nhãn trung thực):
- `SqlTinh`: chuỗi `M4_03A_SQL` (hằng, KHÔNG đăng ký registry, không ordinal): giữ vai cũ + thêm KE_TOAN; bảng ghi thêm + FK tổ hợp; không UPDATE/
  DELETE hàng M24; lệnh không GRANT; app_web chỉ EXECUTE hàm đọc; REVOKE PUBLIC; RLS; không AP/sổ cái/Request.
- `KiemDauVao`: validator thật `kiem_luu` / `kiem_xac_nhan_body` (allowlist, khóa thẩm quyền, NULL ≠ "0", tiền tệ/độ chính xác/bool/float,
  VAT ba trạng thái, trường CAS).
- `MienThuan`: `thieu` / `trang_thai_kt` / `trang_thai_dong` (gương m4._kt_thieu).
- `DtoBien`: builder DTO thật (`xem_dto`, `kt_dto`, `nguon_dto`, `dong_ds_dto`, `ack_dto`, `kiem_ngu_canh`) trên KHUNG BIÊN VIẾT TAY theo đúng
  hình dạng hàm SQL — chỉ chứng minh serializer/kiểm hợp đồng, KHÔNG phải bằng chứng producer/PG/GUI (đó là tests/test_m4_03a_pg.py).
- `ThuTuDichVu`: `KeToanNghiemThuK2` với FAKE_XD (đối tượng giả có nhãn) — chỉ kiểm thứ tự biên: validate trước danh tính, đọc qua login thường,
  lệnh qua kết nối chủ bảng, ACK lệch hợp đồng không thành công.
"""

from __future__ import annotations

import copy
import json
import re
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m4 import ke_toan_nghiem_thu as KT
from kho_tri_thuc.m4 import sql_duyet as SD
from kho_tri_thuc.m4 import sql_ke_toan_nghiem_thu as SK

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
NOI = "\n".join(SK.M4_03A_SQL)


def _ma(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except DataError as exc:
        return exc.code
    return None


def _ham(ten: str) -> str:
    """Đầu + thân một hàm SQL trong M4_03A_SQL (từ CREATE OR REPLACE FUNCTION <ten>( tới dấu $$ đóng thân)."""
    i = NOI.index(f"CREATE OR REPLACE FUNCTION {ten}(")
    a = NOI.index("$$", i)
    return NOI[i:NOI.index("$$", a + 2)]


def _id(n: int) -> str:
    return str(uuid.UUID(int=n))


H = {k: c * 64 for k, c in (("pb", "a"), ("graph", "b"), ("pdf", "c"), ("tep", "d"), ("pb2", "e"))}


# ================================================================================================== khung biên viết tay (hình dạng hàm SQL)
def ctx(pb=11, sha=None, seal=21, ver=31) -> dict:
    return {"phap_nhan_id": _id(1), "du_an_id": _id(2), "hop_dong_id": _id(3), "dot_id": _id(4), "kt_pending_id": _id(5), "phong_bi_id": _id(pb),
            "seal_id": _id(seal), "version_id": _id(ver), "ket_luan_id": _id(41), "pdf_id": _id(51), "phong_bi_sha256": sha or H["pb"],
            "graph_sha256": H["graph"], "pdf_sha256": H["pdf"]}


def nd(**kw) -> dict:
    """noi_dung phong bì M24 (sql_duyet.py:478–498) — số nguồn là chuỗi thập phân chuẩn."""
    x = {"tien_te": "VND", "gia_tri_nt": "1000000", "so_xin_thanh_toan": "900000", "tam_ung": "0", "thu_hoi": "100000", "giu_lai": "50000",
         "ket_luan_id": _id(41), "ket_luan_revision": 1, "dong": [{"row_id": "R1", "ma_hm": "HM1", "dvt": "m3", "khoi_luong_chap_nhan": "10"}],
         "xu_ly_phat_hien": [], "thue": "CHO_GOI_M4_03", "nguon": "M4", "seal_id": _id(21), "phien_ban_id": _id(31), "phien_ban_so": 1,
         "quyet_dinh_id": _id(61), "pdf": {"id": _id(51), "raw_sha256": H["pdf"], "byte_length": 2048}, "ap": "CHUA_NOI_GOI_M4_03",
         "request": "CHUA_NOI_GOI_M4_04"}
    x.update(kw)
    return x


def kt_row(rev=1, loai="NHAP", pb=11, **kw) -> dict:
    """Dòng m4._kt_dong (máy chủ) — thiếu được tính bằng gương thuần rồi ghi vào như CSDL làm."""
    r = {"kt_revision_id": _id(100 + rev), "revision": rev, "loai": loai, "nhap_id": _id(100 + rev - 1) if loai == "XAC_NHAN" else None,
         "phong_bi_id": _id(pb), "tien_te": "VND", "gia_tri_nt_xac_nhan": "1000000", "tam_ung_xac_nhan": None, "thu_hoi_xac_nhan": None,
         "giu_lai_xac_nhan": None, "co_so_gia_tri": "TRUOC_VAT", "vat_trang_thai": "KHONG_AP_DUNG", "vat_can_cu_tep_id": None,
         "vat_can_cu_sha256": None, "vat_trich_dan": None, "ly_do": "Hóa đơn chưa phát sinh VAT", "tao_boi": "MO_PHONG_KT", "tao_luc": "2026-10-23"}
    r.update(kw)
    r["thieu"] = KT.thieu(r, nd())
    return r


TEP = {"id": _id(71), "ten": "hoa-don.pdf", "raw_sha256": H["tep"], "media_type": "application/pdf", "byte_length": 999}


def chi_tiet(kt=None, *, hien=True, da_xn=False, lich_kt=None, tep=None) -> dict:
    c = ctx()
    return {"context": c, "can_cu_hien_hanh": hien, "phong_bi_moi_nhat": True, "ly_do_hold": None, "nguon": nd(),
            "pdf": {"id": _id(51), "ten": "ho-so-dot.pdf", "media_type": "application/pdf", "raw_sha256": H["pdf"], "byte_length": 2048},
            "tep_can_cu": [TEP] if tep is None else tep, "kt": kt, "da_xac_nhan": da_xn,
            "lich_su_phong_bi": [{"context": c, "thu_tu": 1, "truoc_id": None, "phien_ban_so": 1, "can_cu_hien_hanh": hien}],
            "lich_su_kt": [{"context": c, "kt": r, "nguon": {k: v for k, v in nd().items() if k != "dong"}} for r in (lich_kt or ([kt] if kt else []))]}


def body_luu(**kw) -> dict:
    b = {"kt_pending_id": _id(5), "phong_bi_id": _id(11), "expected_phong_bi_sha256": H["pb"], "expected_revision": 0,
         "gia_tri_nt_xac_nhan": None, "tien_te": None, "co_so_gia_tri": "CHUA_RO", "tam_ung_xac_nhan": None, "thu_hoi_xac_nhan": None,
         "giu_lai_xac_nhan": None, "vat_trang_thai": "CHUA_DU", "vat_can_cu_tep_id": None, "vat_trich_dan": None, "ly_do": None, "khoa": "kt-luu-1"}
    b.update(kw)
    return b


def body_xn(**kw) -> dict:
    b = {"kt_pending_id": _id(5), "phong_bi_id": _id(11), "kt_revision_id": _id(101), "expected_revision": 1,
         "expected_phong_bi_sha256": H["pb"], "khoa": "kt-xn-1"}
    b.update(kw)
    return b


# ================================================================================================== tĩnh: SQL hằng
class SqlTinh(unittest.TestCase):
    def test_chi_hang_khong_dang_ky(self):
        self.assertIsInstance(SK.M4_03A_SQL, tuple)
        self.assertTrue(all(isinstance(s, str) and s.strip() for s in SK.M4_03A_SQL))
        self.assertEqual(SK.M4_03A_SQL[0], "SET LOCAL check_function_bodies = off")
        nguon = (SRC / "m4" / "sql_ke_toan_nghiem_thu.py").read_text(encoding="utf-8")
        self.assertNotIn("pg_migrations", nguon)
        self.assertNotIn("PG_MIGRATIONS", nguon)
        self.assertNotRegex(nguon, r"M00\d\d")
        pgm = (SRC / "ha_tang" / "pg_migrations.py").read_text(encoding="utf-8")
        self.assertNotIn("sql_ke_toan_nghiem_thu", pgm)
        self.assertNotIn("M4_03A_SQL", pgm)

    def test_vai_cu_giu_nguyen_them_ke_toan(self):
        self.assertIn("CHECK (vai IN ('PHU_TRACH','XEM','REVIEW','DUYET','KE_TOAN'))", NOI)
        self.assertIn("LIKE '%DUYET%'", NOI)
        self.assertIn("CHECK (vai IN ('PHU_TRACH','XEM','REVIEW','DUYET'))", "\n".join(SD.M0024_M4_DUYET))  # M24 không đổi
        f = _ham("master.m4_kt_duoc")
        self.assertIn("q.vai = 'KE_TOAN'", f)
        self.assertIn("n.vai_tro IN ('KE_TOAN','KE_TOAN_TRUONG')", f)
        self.assertIn("q.thu_hoi_luc IS NULL", f)
        self.assertIn("master.ktt_duoc(q.phap_nhan_id, 'M4')", f)
        self.assertNotIn("INSERT INTO m4.quyen_du_an", NOI)  # không seed/auto-grant
        for cu in ("master.m4_duoc(", "master.m4_duyet_duoc(", "m4.duyet_doc_dot(", "m4.duyet_kiem("):
            self.assertNotIn("CREATE OR REPLACE FUNCTION " + cu, NOI)

    def test_khong_sua_hang_m24(self):
        for bang in ("duyet_kt_cho", "duyet_kt_phong_bi", "duyet_seal", "duyet_pdf", "duyet_quyet_dinh", "duyet_phien_ban", "bien_nhan", "tep"):
            self.assertNotRegex(NOI, rf"(UPDATE|DELETE FROM)\s+m4\.{bang}\b")
            self.assertNotRegex(NOI, rf"INSERT INTO m4\.{bang}\b")
        self.assertNotRegex(NOI, r"DROP (TABLE|FUNCTION)")
        self.assertIn("ALTER TABLE m4.duyet_kt_phong_bi ADD CONSTRAINT duyet_kt_phong_bi_id_cho_uq UNIQUE (id, cho_id)", NOI)

    def test_bang_ghi_them_fk_to_hop(self):
        t = next(s for s in SK.M4_03A_SQL if s.startswith("CREATE TABLE m4.kt_xac_nhan"))
        for fk in ("FOREIGN KEY (cho_id, dot_id) REFERENCES m4.duyet_kt_cho (id, dot_id)",
                   "FOREIGN KEY (phong_bi_id, cho_id) REFERENCES m4.duyet_kt_phong_bi (id, cho_id)",
                   "FOREIGN KEY (seal_id, dot_id) REFERENCES m4.duyet_seal (id, dot_id)",
                   "FOREIGN KEY (phien_ban_id, dot_id) REFERENCES m4.duyet_phien_ban (id, dot_id)",
                   "FOREIGN KEY (vat_can_cu_tep_id, du_an_id, vat_can_cu_sha256) REFERENCES m4.tep (id, du_an_id, raw_sha256)",
                   "UNIQUE (cho_id, revision)", "CHECK ((revision = 1) = (truoc_id IS NULL))"):
            self.assertIn(fk, t)
        for k in SK.TIEN_KT:
            self.assertIn(f"{k} text CHECK ({k} IS NULL OR {k} ", t)  # nullable — thiếu ≠ 0
            self.assertNotIn(f"{k} text NOT NULL", t)
        self.assertNotRegex(t, r"\b(numeric|float|double|real)\b")
        self.assertIn("kt_xac_nhan_truoc_fk FOREIGN KEY (truoc_id, cho_id)", NOI)
        self.assertIn("CREATE UNIQUE INDEX kt_xac_nhan_mot_xac_nhan_uq ON m4.kt_xac_nhan (phong_bi_id) WHERE loai = 'XAC_NHAN'", NOI)
        self.assertIn("kt_xac_nhan_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE ON m4.kt_xac_nhan FOR EACH ROW EXECUTE FUNCTION m4.chi_ghi_them()", NOI)
        trg = _ham("m4.kt_xac_nhan_kiem")
        for ma in ("M4_BAT_BIEN", "M4_KT_NGUON_SAI", "M4_KT_NGUON_CU", "M4_KT_CAN_KIEM_LAI", "M4_KT_REVISION_CU", "M4_KT_DA_XAC_NHAN",
                   "M4_KT_TIEN_TE_KHAC", "M4_KT_SO_SAI", "M4_KT_CAN_CU_VAT_SAI", "M4_KT_XAC_NHAN_KHAC_NHAP", "M4_KT_CHO_BO_SUNG"):
            self.assertIn(ma, trg)

    def test_quyen_thuc_thi(self):
        rv = next(s for s in SK.M4_03A_SQL if s.startswith("REVOKE EXECUTE ON FUNCTION"))
        for f in (*SK.HAM_LENH, *SK.HAM_NOI_BO, *SK.HAM_DOC):
            self.assertIn(f, rv)
        grant = [s for s in SK.M4_03A_SQL if "GRANT EXECUTE" in s]
        self.assertEqual(len(grant), 1)
        g = grant[0][grant[0].index("GRANT EXECUTE"):]
        for f in SK.HAM_DOC:
            self.assertIn(f, g)
        for f in (*SK.HAM_LENH, *SK.HAM_NOI_BO):
            self.assertNotIn(f, g)
        self.assertNotRegex(NOI, r"GRANT (INSERT|UPDATE|DELETE|ALL)")
        self.assertIn("ALTER TABLE m4.kt_xac_nhan ENABLE ROW LEVEL SECURITY", NOI)
        self.assertIn("FOR SELECT TO app_web USING (m4.kt_doc_cho(cho_id))", NOI)
        for f in ("m4.kt_doc_cho", "m4.kt_kiem", "m4.kt_danh_sach", "m4.kt_chi_tiet", "m4.kt_pdf"):
            self.assertIn("SECURITY DEFINER", _ham(f)[:400])
        for f in ("m4.kt_khoa", "m4.kt_luu", "m4.kt_xac_nhan_lenh"):
            h = _ham(f)
            self.assertNotIn("SECURITY DEFINER", h[:500])
            self.assertIn("master.la_chu_bang('m4.kt_xac_nhan'::regclass)", h)

    def test_thu_tu_lenh(self):
        k = _ham("m4.kt_khoa")
        vt = [k.index(s) for s in ("m4.kt_kiem(p_cho, p_hanh)", "FROM m4.ho_so_hop_dong", "FROM m4.dot", "FROM m4.duyet_phien_ban",
                                   "FROM m4.duyet_kt_cho WHERE id = c.id FOR UPDATE", "FROM m4.kt_xac_nhan")]
        self.assertEqual(vt, sorted(vt))
        for f, hd in (("m4.kt_luu", "KT_LUU"), ("m4.kt_xac_nhan_lenh", "KT_XAC_NHAN")):
            h = _ham(f)
            vt = [h.index(s) for s in ("m4.kt_khoa(", f"m4._bn_tra(aid, p_khoa, '{hd}'", "M4_KT_NGUON_CU", "M4_KT_KHONG_THAY", "M4_KT_NGUON_HONG",
                                       "M4_KT_CAN_KIEM_LAI", "M4_KT_NGUON_DOI", "INSERT INTO m4.kt_xac_nhan", f"m4._bn_ghi(aid, p_khoa, '{hd}'")]
            self.assertEqual(vt, sorted(vt), f)

    def test_khong_ap_request_so_cai(self):
        for x in ("ke_toan.", "but_toan", "so_cai", "cong_no_mo", "giao_tiep.", "request_", "kho.bien_nhan", "m4.tra_bien_nhan"):
            self.assertNotIn(x, NOI)
        self.assertIn("'CHUA_TRIEN_KHAI_M4_03B', 'da_ghi_cong_no', false", NOI)
        self.assertIn("'CHUA_NOI_M4_04'", NOI)

    def test_chi_tiet_khong_lo_object_key(self):
        for f in ("m4.kt_chi_tiet", "m4.kt_pdf", "m4._kt_tep_can_cu"):
            self.assertNotIn("object_key", _ham(f))


# ================================================================================================== validator thật
class KiemDauVao(unittest.TestCase):
    def test_luu_null_khac_0(self):
        _, yc = KT.kiem_luu(body_luu(gia_tri_nt_xac_nhan="0", tam_ung_xac_nhan=None, tien_te="VND"))
        self.assertEqual(yc["gia_tri_nt_xac_nhan"], "0")
        self.assertIsNone(yc["tam_ung_xac_nhan"])
        self.assertNotEqual(KT.thieu(yc, nd()), KT.thieu({**yc, "gia_tri_nt_xac_nhan": None}, nd()))

    def test_luu_moi_khoa_bat_buoc_va_allowlist(self):
        for k in KT.TRUONG_LUU:
            b = body_luu()
            del b[k]
            self.assertEqual(_ma(KT.kiem_luu, b), "M4_YEU_CAU_SAI", k)
        self.assertEqual(_ma(KT.kiem_luu, {**body_luu(), "abc": 1}), "M4_YEU_CAU_SAI")
        self.assertEqual(_ma(KT.kiem_luu, {**body_luu(), "kt_revision_id": _id(9)}), "M4_YEU_CAU_SAI")
        self.assertEqual(_ma(KT.kiem_luu, [body_luu()]), "M4_YEU_CAU_SAI")

    def test_luu_khoa_tham_quyen(self):
        for k in ("actor", "nguoi_dung_id", "phap_nhan_id", "du_an_id", "owner", "trang_thai", "pass", "ap", "request", "da_ghi_cong_no",
                  "gia_tri_nt", "so_xin_thanh_toan", "phong_bi_sha256", "receipt_id", "vat_can_cu_sha256", "tai_khoan", "ty_gia"):
            self.assertEqual(_ma(KT.kiem_luu, {**body_luu(), k: None}), "M4_CLIENT_AUTHORITY", k)

    def test_luu_tien(self):
        for v in (1000, 1000.0, True, "1,000", "01", "1.", "-1", "1e3", " 1", "1.000", "NaN"):
            self.assertEqual(_ma(KT.kiem_luu, body_luu(gia_tri_nt_xac_nhan=v, tien_te="USD")), "M4_KT_SO_SAI", repr(v))
        self.assertEqual(_ma(KT.kiem_luu, body_luu(gia_tri_nt_xac_nhan="12.5", tien_te="VND")), "M4_KT_SO_SAI")
        self.assertIsNone(_ma(KT.kiem_luu, body_luu(gia_tri_nt_xac_nhan="12.5", tien_te="USD")))
        for tt in ("vnd", "VN", 704, True):
            self.assertEqual(_ma(KT.kiem_luu, body_luu(tien_te=tt)), "M4_KT_SO_SAI", repr(tt))

    def test_luu_vat_ba_trang_thai(self):
        self.assertIsNone(_ma(KT.kiem_luu, body_luu(vat_trang_thai="CHUA_DU")))
        self.assertIsNone(_ma(KT.kiem_luu, body_luu(vat_trang_thai="KHONG_AP_DUNG", ly_do="Không chịu VAT")))
        self.assertIsNone(_ma(KT.kiem_luu, body_luu(vat_trang_thai="CO_CAN_CU", vat_can_cu_tep_id=_id(71), vat_trich_dan="Điều 3")))
        self.assertIsNone(_ma(KT.kiem_luu, body_luu(vat_trang_thai="CO_CAN_CU")))  # nháp được thiếu
        self.assertEqual(_ma(KT.kiem_luu, body_luu(vat_trang_thai="KHONG_AP_DUNG", vat_can_cu_tep_id=_id(71))), "M4_KT_VAT_SAI")
        self.assertEqual(_ma(KT.kiem_luu, body_luu(vat_trang_thai="CHUA_DU", vat_trich_dan="x")), "M4_KT_VAT_SAI")
        self.assertEqual(_ma(KT.kiem_luu, body_luu(vat_trang_thai="CO")), "M4_KT_TRUONG_SAI")
        self.assertEqual(_ma(KT.kiem_luu, body_luu(vat_trang_thai="CO_CAN_CU", vat_can_cu_tep_id="71")), "M4_THAM_SO_SAI")
        self.assertEqual(_ma(KT.kiem_luu, body_luu(co_so_gia_tri="SAU_VAT")), "M4_KT_TRUONG_SAI")
        self.assertEqual(_ma(KT.kiem_luu, body_luu(ly_do="a\x00b")), "M4_KT_TRUONG_SAI")
        self.assertEqual(_ma(KT.kiem_luu, body_luu(ly_do="x" * 2001)), "M4_KT_TRUONG_SAI")
        _, yc = KT.kiem_luu(body_luu(ly_do="   "))
        self.assertIsNone(yc["ly_do"])

    def test_luu_cas(self):
        for v in (-1, True, "0", 0.0, None, 10 ** 6 + 1):
            self.assertEqual(_ma(KT.kiem_luu, body_luu(expected_revision=v)), "M4_THAM_SO_SAI", repr(v))
        for v in ("A" * 64, "a" * 63, None, 1):
            self.assertEqual(_ma(KT.kiem_luu, body_luu(expected_phong_bi_sha256=v)), "M4_KT_CO_SO_SAI", repr(v))
        for k in ("kt_pending_id", "phong_bi_id"):
            self.assertEqual(_ma(KT.kiem_luu, body_luu(**{k: "x"})), "M4_THAM_SO_SAI")
        for v in ("", "a b", None, "x" * 201):
            self.assertEqual(_ma(KT.kiem_luu, body_luu(khoa=v)), "M4_KHOA_THAO_TAC")
        khoa, yc = KT.kiem_luu(body_luu())
        self.assertEqual(khoa, "kt-luu-1")
        self.assertNotIn("khoa", yc)
        self.assertEqual(set(yc), set(KT.TRUONG_LUU) - {"khoa"})

    def test_xac_nhan(self):
        khoa, yc = KT.kiem_xac_nhan_body(body_xn())
        self.assertEqual((khoa, yc["expected_revision"]), ("kt-xn-1", 1))
        self.assertEqual(_ma(KT.kiem_xac_nhan_body, body_xn(expected_revision=0)), "M4_THAM_SO_SAI")  # không xác nhận từ null
        for k in KT.DU_LIEU:
            self.assertEqual(_ma(KT.kiem_xac_nhan_body, {**body_xn(), k: None}), "M4_CLIENT_AUTHORITY", k)  # không gửi lại số/VAT
        for k in KT.TRUONG_XAC_NHAN:
            b = body_xn()
            del b[k]
            self.assertEqual(_ma(KT.kiem_xac_nhan_body, b), "M4_YEU_CAU_SAI", k)
        self.assertEqual(_ma(KT.kiem_xac_nhan_body, {**body_xn(), "kt": {}}), "M4_YEU_CAU_SAI")


# ================================================================================================== miền thuần
class MienThuan(unittest.TestCase):
    def test_thieu(self):
        du = kt_row()
        self.assertEqual(du["thieu"], [])
        self.assertEqual(KT.thieu({**du, "gia_tri_nt_xac_nhan": None}, nd()), ["GIA_TRI_NT_THIEU"])
        self.assertEqual(KT.thieu({**du, "tien_te": None}, nd()), ["TIEN_TE_THIEU"])
        self.assertEqual(KT.thieu({**du, "co_so_gia_tri": "CHUA_RO"}, nd()), ["CO_SO_CHUA_XAC_DINH"])
        self.assertEqual(KT.thieu({**du, "vat_trang_thai": "CHUA_DU"}, nd()), ["VAT_CHUA_DU"])
        self.assertEqual(KT.thieu({**du, "ly_do": None}, nd()), ["VAT_LY_DO_THIEU"])
        co = {**du, "vat_trang_thai": "CO_CAN_CU", "ly_do": None}
        self.assertEqual(KT.thieu(co, nd()), ["VAT_CAN_CU_THIEU"])
        self.assertEqual(KT.thieu({**co, "vat_can_cu_tep_id": _id(71), "vat_trich_dan": "Điều 3"}, nd()), [])
        # khác số nguồn cần lý do; null không phải "khác" (chưa xác nhận), "0" là số thật
        khac = {**co, "vat_can_cu_tep_id": _id(71), "vat_trich_dan": "Điều 3", "gia_tri_nt_xac_nhan": "990000"}
        self.assertEqual(KT.thieu(khac, nd()), ["LY_DO_KHAC_NGUON"])
        self.assertEqual(KT.thieu({**khac, "ly_do": "Trừ phạt"}, nd()), [])
        self.assertEqual(KT.thieu({**khac, "gia_tri_nt_xac_nhan": "1000000", "tam_ung_xac_nhan": None}, nd()), [])
        self.assertEqual(KT.thieu({**khac, "gia_tri_nt_xac_nhan": "1000000", "tam_ung_xac_nhan": "0"}, nd()), [])  # nguồn tam_ung = "0"
        self.assertEqual(KT.thieu({**khac, "gia_tri_nt_xac_nhan": "1000000", "giu_lai_xac_nhan": "0"}, nd()), ["LY_DO_KHAC_NGUON"])
        tat = KT.thieu({k: None for k in KT.DU_LIEU}, nd())
        self.assertEqual(tat, sorted(tat))
        self.assertEqual(set(tat) | {"LY_DO_KHAC_NGUON", "VAT_CAN_CU_THIEU", "VAT_LY_DO_THIEU"}, set(SK.THIEU))

    def test_trang_thai(self):
        self.assertEqual(KT.trang_thai_kt("NHAP", []), "CHO_XAC_NHAN")
        self.assertEqual(KT.trang_thai_kt("NHAP", ["VAT_CHUA_DU"]), "CHO_BO_SUNG")
        self.assertEqual(KT.trang_thai_kt("XAC_NHAN", []), "KT_DA_XAC_NHAN_CHO_GHI_CONG_NO")
        self.assertEqual(_ma(KT.trang_thai_kt, "KHAC", []), "M4_KT_SAI_DTO")
        self.assertEqual(KT.trang_thai_dong(False, True, None), "CAN_KIEM_LAI")
        self.assertEqual(KT.trang_thai_dong(True, False, None), "CAN_KIEM_LAI")
        self.assertEqual(KT.trang_thai_dong(True, True, None), "CHO_XAC_NHAN")
        self.assertEqual(KT.trang_thai_dong(True, True, {"loai": "NHAP", "thieu": ["X"]}), "CHO_BO_SUNG")
        self.assertEqual(KT.AP, {"trang_thai": "CHUA_TRIEN_KHAI_M4_03B", "da_ghi_cong_no": False})
        self.assertEqual(KT.REQUEST, {"trang_thai": "CHUA_NOI_M4_04"})
        self.assertNotIn("DA_GHI_CONG_NO", KT.TRANG_THAI_KT)


# ================================================================================================== DTO trên khung biên viết tay
class DtoBien(unittest.TestCase):
    def test_kt_null_tuong_minh(self):
        x = KT.xem_dto(chi_tiet())
        self.assertEqual(tuple(x), KT.XEM_KEYS)
        self.assertIn("kt", x)
        self.assertIsNone(x["kt"])
        self.assertEqual(x["lich_su"], {"phong_bi": x["lich_su"]["phong_bi"], "kt": []})
        self.assertEqual(x["quyen"], {"xem": True, "luu": True, "xac_nhan": False, "tai_pdf": True})
        self.assertEqual(set(x["nguon"]), set(KT.NGUON_KEYS))
        self.assertEqual(x["nguon"]["tep_can_cu"], [TEP])
        self.assertNotIn("object_key", json.dumps(x))
        self.assertEqual(x["nguon"]["gia_tri_nt"], "1000000")  # số nguồn giữ nguyên, không copy thành KT

    def test_kt_revision_chuan(self):
        r = kt_row(gia_tri_nt_xac_nhan="0", ly_do="Chưa nghiệm thu giá trị")  # "0" thật, khác nguồn → có lý do
        x = KT.xem_dto(chi_tiet(r))
        self.assertEqual(tuple(x["kt"]), KT.KT_KEYS)
        self.assertEqual((x["kt"]["kt_revision_id"], x["kt"]["revision"]), (_id(101), 1))
        self.assertEqual(x["kt"]["gia_tri_nt_xac_nhan"], "0")
        self.assertIsNone(x["kt"]["tam_ung_xac_nhan"])
        self.assertEqual(x["kt"]["trang_thai"], "CHO_XAC_NHAN")
        self.assertTrue(x["quyen"]["xac_nhan"])
        self.assertEqual(x["lich_su"]["kt"][0]["kt"], x["kt"])
        for xau in ({"revision": 0}, {"revision": True}, {"revision": "1"}, {"kt_revision_id": "abc"}, {"loai": "X"}):
            self.assertEqual(_ma(KT.kt_dto, {**r, **xau}, nd()), "M4_KT_SAI_DTO", xau)
        self.assertEqual(_ma(KT.kt_dto, {**r, "thieu": ["VAT_CHUA_DU"]}, nd()), "M4_KT_SAI_DTO")  # CSDL ≠ miền → không đoán

    def test_lich_hold_va_da_xac_nhan(self):
        x = KT.xem_dto(chi_tiet(kt_row(), hien=False))
        self.assertFalse(x["can_cu_hien_hanh"])
        self.assertEqual((x["quyen"]["luu"], x["quyen"]["xac_nhan"]), (False, False))
        n, c = kt_row(1), kt_row(2, "XAC_NHAN")
        x = KT.xem_dto(chi_tiet(c, da_xn=True, lich_kt=[n, c]))
        self.assertEqual(x["kt"]["trang_thai"], "KT_DA_XAC_NHAN_CHO_GHI_CONG_NO")
        self.assertEqual((x["quyen"]["luu"], x["quyen"]["xac_nhan"]), (False, False))
        self.assertEqual([r["kt"]["revision"] for r in x["lich_su"]["kt"]], [1, 2])
        self.assertEqual(_ma(KT.xem_dto, chi_tiet(c, da_xn=False, lich_kt=[n, c])), "M4_KT_SAI_DTO")
        self.assertEqual(_ma(KT.xem_dto, chi_tiet(c, da_xn=True, lich_kt=[c, n])), "M4_KT_SAI_DTO")  # không tăng dần

    def test_hai_phong_bi(self):
        ct = chi_tiet()
        a = ctx(pb=12, sha=H["pb2"], seal=22, ver=32)
        ct["lich_su_phong_bi"] = [{"context": a, "thu_tu": 1, "truoc_id": None, "phien_ban_so": 1, "can_cu_hien_hanh": False},
                                  {**ct["lich_su_phong_bi"][0], "thu_tu": 2, "truoc_id": _id(12), "phien_ban_so": 2}]
        ra = kt_row(1, pb=12)
        ct["lich_su_kt"] = [{"context": a, "kt": ra, "nguon": nd()}]
        x = KT.xem_dto(ct)
        self.assertIsNone(x["kt"])  # KT của A không mượn sang B
        self.assertEqual([r["context"]["phong_bi_id"] for r in x["lich_su"]["phong_bi"]], [_id(12), _id(11)])
        self.assertEqual(x["lich_su"]["kt"][0]["context"], a)
        xau = copy.deepcopy(ct)
        xau["lich_su_kt"][0]["kt"]["phong_bi_id"] = _id(11)
        self.assertEqual(_ma(KT.xem_dto, xau), "M4_KT_SAI_DTO")
        xau = copy.deepcopy(ct)
        xau["lich_su_kt"][0]["context"] = {**a, "kt_pending_id": _id(99)}
        self.assertEqual(_ma(KT.xem_dto, xau), "M4_KT_SAI_DTO")

    def test_ngu_canh_va_nguon(self):
        self.assertEqual(KT.kiem_ngu_canh(ctx()), ctx())
        for xau in ({**ctx(), "them": 1}, {k: v for k, v in ctx().items() if k != "pdf_id"}, {**ctx(), "dot_id": "1"},
                    {**ctx(), "pdf_sha256": "C" * 64}, {**ctx(), "version_id": _id(31).upper()}):
            self.assertEqual(_ma(KT.kiem_ngu_canh, xau), "M4_KT_SAI_DTO")
        ct = chi_tiet()
        for k, v in (("tep_can_cu", None), ("tep_can_cu", [{**TEP, "object_key": "m4-raw/x"}]), ("tep_can_cu", [{**TEP, "byte_length": 0}]),
                     ("pdf", {**ct["pdf"], "raw_sha256": H["tep"]}), ("pdf", {**ct["pdf"], "media_type": "text/html"})):
            self.assertEqual(_ma(KT.xem_dto, {**ct, k: v}), "M4_KT_SAI_DTO", k)
        self.assertEqual(KT.xem_dto({**ct, "tep_can_cu": []})["nguon"]["tep_can_cu"], [])

    def test_danh_sach_va_ack(self):
        d = KT.dong_ds_dto({"kt_pending_id": _id(5), "dot_id": _id(4), "phong_bi_id": _id(11), "phong_bi_sha256": H["pb"], "hien_hanh": True,
                            "toan_ven": True, "kt": None})
        self.assertEqual(tuple(d), KT.DONG_DS_KEYS)
        self.assertIsNone(d["revision"])
        kq = {"hanh_dong": "LUU", "context": ctx(), "kt_revision_id": _id(101), "revision": 1, "loai": "NHAP", "nhap_id": None,
              "trang_thai": "CHO_BO_SUNG", "thieu": ["VAT_CHUA_DU"], "trung_xac_nhan": False, "ap": dict(KT.AP), "request": dict(KT.REQUEST)}
        a = KT.ack_dto({"lap_lai": False, "ket_qua": kq, "receipt_id": _id(900)}, "k1")
        self.assertTrue(set(KT.ACK_KEYS) <= set(a))
        self.assertEqual((a["revision"], a["lap_lai"], a["receipt_id"]), (1, False, _id(900)))
        self.assertTrue(KT.ack_dto({"lap_lai": True, "ket_qua": kq, "receipt_id": _id(900)}, "k1")["lap_lai"])
        for xau in ({"ap": {"trang_thai": "DA_GHI"}}, {"revision": 0}, {"trang_thai": "KT_DA_XAC_NHAN_CHO_GHI_CONG_NO"}, {"context": {}}):
            self.assertEqual(_ma(KT.ack_dto, {"lap_lai": False, "ket_qua": {**kq, **xau}, "receipt_id": _id(900)}, "k1"), "M4_KT_SAI_DTO", xau)
        self.assertEqual(_ma(KT.ack_dto, {"lap_lai": False, "ket_qua": kq, "receipt_id": None}, "k1"), "M4_KT_SAI_DTO")
        xn = {**kq, "hanh_dong": "XAC_NHAN", "loai": "XAC_NHAN", "trang_thai": "KT_DA_XAC_NHAN_CHO_GHI_CONG_NO", "thieu": [], "trung_xac_nhan": True}
        self.assertTrue(KT.ack_dto({"lap_lai": False, "ket_qua": xn, "receipt_id": _id(901)}, "k2")["lap_lai"])


# ================================================================================================== thứ tự biên dịch vụ (FAKE_XD, có nhãn)
class FakeXd:
    """FAKE_XD — đối tượng giả CHỈ để kiểm thứ tự gọi của service; không phải PostgreSQL/producer."""

    def __init__(self, ct=None, kq=None):
        self.goi, self.ct, self.kq, self.conn_tin_cay = [], ct, kq, object()

    def danh_tinh(self, dang_nhap):
        self.goi.append(("danh_tinh", dang_nhap))
        return {"id": _id(800), "dang_nhap": dang_nhap}

    @contextmanager
    def _tx(self, dt):
        self.goi.append(("tx_app",))
        yield

    def _mot(self, sql, params=()):
        self.goi.append(("app", sql.split("(")[0]))
        if "kt_chi_tiet" in sql:
            return {"ct": self.ct}
        return {"ds": []}

    def _raw(self, sha, dai=None):
        self.goi.append(("raw", sha))
        return b"%PDF-"

    @contextmanager
    def _chua_ro(self):
        yield

    @contextmanager
    def _tx_review(self, dt, rr=False):
        self.goi.append(("tx_chu",))
        yield FakeConn(self.goi)

    def _r1(self, c, sql, params=()):
        """Đường chủ bảng (khung viết tay có nhãn): quyền+khóa m4.kt_khoa → seam producer THẬT DuyetDot._dot / do_thi (đợt, L3 công bố có người công
        bố riêng) → chứng thực → lệnh ghi trả kq."""
        self.goi.append(("chu", sql.split("(")[0], params))
        if "m4.kt_khoa(" in sql:
            return {"q": "KE_TOAN"}
        if "FROM m4.duyet_kt_cho" in sql:
            return {"dot_id": _id(4)}
        if "FROM m4.dot d" in sql:
            return {"id": _id(4), "hop_dong_id": _id(3), "du_an_id": _id(2), "phap_nhan_id": _id(1), "so_dot": 1, "ngay_nghiem_thu": "2026-10-01",
                    "trang_thai": "DA_NOP", "revision": 1, "so_hop_dong": "HD-1", "revision_ho_so_hien_hanh": 2}
        if "FROM m4.chung_tu_run r" in sql:
            return {"run_id": _id(600), "revision": 1, "trang_thai": "SUCCEEDED", "basis_sha256": H["graph"], "tao_boi_id": _id(700),
                    "tao_dang_nhap": "MO_PHONG_SOAN", "ket_qua": {}, "ket_qua_sha256": H["pb2"], "basis_cong_bo_sha256": H["graph"]}
        if "m4._kt_chung_thuc_ghi(" in sql:
            return {"a": {"kt_pending_id": params[0]}}
        return {"r": self.kq}

    def _rn(self, c, sql, params=()):
        self.goi.append(("chu_n", sql.split("(")[0], params))
        return [{"id": _id(31), "so": 1, "parent_id": None, "nop_id": _id(32), "trang_thai": "DA_NOP", "ly_do": None, "digest": H["pb"],
                 "revision_ho_so": 2, "ket_luan_revision": 1, "quyet_dinh_id": _id(61), "seal_id": _id(21)}]

    def _chung_tu_co_so(self, c, dot):
        self.goi.append(("co_so", dot))
        return {"l2": {}}

    @staticmethod
    def _sha_co_so(co):
        return H["graph"]


class FakeConn:
    """FAKE_CONN — kết nối chủ bảng giả: chỉ ghi lại set_config danh tính mà producer do_thi gọi (đổi sang người công bố L3 rồi khôi phục)."""

    def __init__(self, goi):
        self.goi = goi

    def execute(self, sql, params=()):
        self.goi.append(("guc", tuple(params)))


class ThuTuDichVu(unittest.TestCase):
    def test_validate_truoc_danh_tinh(self):
        xd = FakeXd()
        svc = KT.KeToanNghiemThuK2(xd)
        self.assertEqual(_ma(svc.luu, "MO_PHONG_KT", {**body_luu(), "actor": "x"}), "M4_CLIENT_AUTHORITY")
        self.assertEqual(_ma(svc.xac_nhan, "MO_PHONG_KT", body_xn(expected_revision=0)), "M4_THAM_SO_SAI")
        self.assertEqual(_ma(svc.luu, "MO_PHONG_KT", body_luu(), khoa="x"), "M4_YEU_CAU_SAI")
        self.assertEqual(xd.goi, [])

    def test_luu_doc_truoc_roi_lenh_chu_bang(self):
        kq = {"hanh_dong": "LUU", "context": ctx(), "kt_revision_id": _id(101), "revision": 1, "loai": "NHAP", "nhap_id": None,
              "trang_thai": "CHO_XAC_NHAN", "thieu": [], "trung_xac_nhan": False, "ap": dict(KT.AP), "request": dict(KT.REQUEST)}
        xd = FakeXd(chi_tiet(), {"lap_lai": False, "ket_qua": kq, "receipt_id": _id(900)})
        a = KT.KeToanNghiemThuK2(xd).luu("MO_PHONG_KT", body_luu(tien_te="VND", gia_tri_nt_xac_nhan="1000000", co_so_gia_tri="TRUOC_VAT",
                                                               vat_trang_thai="CO_CAN_CU", vat_can_cu_tep_id=_id(71), vat_trich_dan="Điều 3"))
        loai = [g[0] for g in xd.goi]
        self.assertEqual(loai[:3], ["danh_tinh", "tx_app", "app"])
        self.assertLess(loai.index("raw"), loai.index("tx_chu"))
        self.assertEqual([g[1] for g in xd.goi if g[0] == "raw"], [H["pdf"], H["tep"]])  # PDF đã duyệt + tệp căn cứ VAT
        chu = next(g for g in xd.goi if g[0] == "chu" and g[1] == "SELECT m4.kt_luu")
        self.assertEqual(chu[1], "SELECT m4.kt_luu")
        # quyền KT + khóa (m4.kt_khoa) → căn cứ producer → chứng thực → lệnh ghi, cùng MỘT giao dịch chủ bảng
        vt = [next(n for n, g in enumerate(xd.goi) if g[0] == "chu" and g[1] == "SELECT m4.kt_khoa"),
              next(n for n, g in enumerate(xd.goi) if g[0] == "co_so"),
              next(n for n, g in enumerate(xd.goi) if g[0] == "chu" and g[1] == "SELECT m4._kt_chung_thuc_ghi"),
              xd.goi.index(chu)]
        self.assertEqual(vt, sorted(set(vt)))
        self.assertEqual(loai.count("tx_chu"), 1)
        self.assertEqual(xd.goi[vt[0]][2], (_id(5), "LUU"))
        self.assertEqual([g[1] for g in xd.goi if g[0] == "guc"], [(_id(700), "MO_PHONG_SOAN"), (_id(800), "MO_PHONG_KT")])  # khôi phục KT
        self.assertEqual(xd.goi[vt[2]][2][:3], (_id(5), _id(800), _id(31)))
        self.assertEqual(xd.goi[vt[2]][2][4], H["graph"])
        self.assertEqual(json.loads(chu[2][6]), {k: body_luu(tien_te="VND", gia_tri_nt_xac_nhan="1000000", co_so_gia_tri="TRUOC_VAT",
                                                                 vat_trang_thai="CO_CAN_CU", vat_can_cu_tep_id=_id(71),
                                                                 vat_trich_dan="Điều 3")[k] for k in KT.DU_LIEU})
        self.assertEqual((a["revision"], a["trang_thai"], a["ap"]["da_ghi_cong_no"]), (1, "CHO_XAC_NHAN", False))

    def test_luu_chan_som(self):
        xd = FakeXd(chi_tiet(tep=[]))
        svc = KT.KeToanNghiemThuK2(xd)
        self.assertEqual(_ma(svc.luu, "K", body_luu(vat_trang_thai="CO_CAN_CU", vat_can_cu_tep_id=_id(71))), "M4_KT_CAN_CU_VAT_SAI")
        self.assertEqual(_ma(svc.luu, "K", body_luu(tien_te="USD")), "M4_KT_TIEN_TE_KHAC")
        self.assertNotIn(("tx_chu",), xd.goi)

    def test_ack_lech_khong_thanh_cong(self):
        kq = {"hanh_dong": "LUU", "context": ctx(), "kt_revision_id": _id(101), "revision": 1, "loai": "XAC_NHAN", "nhap_id": None,
              "trang_thai": "KT_DA_XAC_NHAN_CHO_GHI_CONG_NO", "thieu": [], "trung_xac_nhan": False, "ap": dict(KT.AP), "request": dict(KT.REQUEST)}
        xd = FakeXd(chi_tiet(), {"lap_lai": False, "ket_qua": kq, "receipt_id": _id(900)})
        self.assertEqual(_ma(KT.KeToanNghiemThuK2(xd).luu, "K", body_luu()), "M4_KT_SAI_DTO")  # lưu không bao giờ tự xác nhận


if __name__ == "__main__":
    unittest.main()
