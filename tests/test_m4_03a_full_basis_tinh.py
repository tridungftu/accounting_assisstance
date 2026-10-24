"""M4-03A full basis — kiểm TĨNH + THUẦN: hiện hành toàn căn cứ qua producer M24 + chứng thực SET LOCAL. CODE_ONLY: WRITTEN_NOT_RUN.

Phân loại (nhãn trung thực):
- `CauNoiSql` / `HienHanhSql`: chuỗi hằng `M4_03A_SQL` (không registry/ordinal): phiên chủ bảng theo session_user, mẫu chứng thực gắn backend/
  giao dịch/actor/ngữ cảnh/SHA, bên ghi kiểm phiên → actor đã khôi phục → quyền KT → SET LOCAL, bên đọc so đúng chuỗi với đồ thị ĐÃ SEAL; hàm nội bộ
  không GRANT; `_kt_hien_hanh` + trigger thêm điều kiện căn cứ. Chỉ chứng minh văn bản SQL, KHÔNG phải bằng chứng PostgreSQL.
- `TaiSuDungProducer`: nguồn thật của helper ghim gọi ĐÚNG DuyetDot._dot/_phien_ban + duyet_dot.do_thi (không tự dựng đồ thị/căn cứ ở KT).
- `ThuTuChu`: `KeToanNghiemThuK2` với FAKE_XD_CHU (đối tượng giả có nhãn; do_thi/_dot/_phien_ban là code producer THẬT chạy trên fake) — chỉ kiểm
  thứ tự biên: quyền app → giao dịch chủ bảng → quyền/khóa → producer (đổi danh tính người công bố + khôi phục KT kể cả lỗi) → chứng thực → SQL.
  Hiện hành thật/HOLD/spoof GUC/phát lại: tests/test_m4_03a_full_basis_pg.py (PostgreSQL thật, env-gated).
"""

from __future__ import annotations

import inspect
import re
import unittest
import uuid
from contextlib import contextmanager

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m4 import duyet_dot as DD
from kho_tri_thuc.m4 import ke_toan_nghiem_thu as KT
from kho_tri_thuc.m4 import sql_ke_toan_nghiem_thu as SK

NOI = "\n".join(SK.M4_03A_SQL)
HAM_MOI = ("m4._kt_phien_chu", "m4._kt_chung_thuc_mau", "m4._kt_chung_thuc_ghi", "m4._kt_co_so_hien_hanh", "m4._kt_khoa_doc")


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


def _dau(ten: str) -> str:
    """Phần khai báo (trước thân AS $$) — nơi có LANGUAGE/SECURITY/SET."""
    h = _ham(ten)
    return h[:h.index("$$")]


def _id(n: int) -> str:
    return str(uuid.UUID(int=n))


H = {k: c * 64 for k, c in (("pb", "a"), ("graph", "b"), ("pdf", "c"), ("tep", "d"), ("pb2", "e"))}


# ================================================================================================== SQL cầu nối
class CauNoiSql(unittest.TestCase):
    def test_phien_chu_theo_session_user(self):
        h = _ham("m4._kt_phien_chu")
        self.assertIn("rolname = session_user", h)
        self.assertIn("c.relowner", h)
        self.assertIn("'m4.kt_xac_nhan'::regclass", h)
        self.assertNotIn("current_user", h)  # bên trong hàm SECURITY DEFINER current_user = chủ hàm — không phải bằng chứng phiên
        self.assertNotIn("pg_has_role", h)  # đúng chủ, không chấp nhận thành viên/SET ROLE

    def test_mau_gan_phien_giao_dich_actor_ngu_canh(self):
        h = _ham("m4._kt_chung_thuc_mau")
        for k in ("'pid', pg_catalog.pg_backend_pid()", "'txid', pg_catalog.txid_current()",
                  "'actor', nullif(current_setting('ktt.nguoi_dung_id', true), '')", "'kt_pending_id', c.id", "'dot_id', c.dot_id",
                  "'hop_dong_id', c.hop_dong_id", "'phap_nhan_id', c.phap_nhan_id", "'du_an_id', c.du_an_id", "'version_id', p_version",
                  "'phong_bi_id', b.id", "'seal_id', s.id", "'ket_luan_id', s.ket_luan_id", "'graph_sha256', p_graph_sha",
                  "'co_so_l3_sha256', p_co_so_sha"):
            self.assertIn(k, h)
        self.assertIn("JOIN m4.duyet_kt_cho c ON c.id = b.cho_id", h)  # ngữ cảnh do máy chủ resolve từ phong bì, không từ tham số

    def test_ghi_phien_chu_actor_quyen_roi_set_local(self):
        h = _ham("m4._kt_chung_thuc_ghi")
        vt = [h.index("m4._kt_phien_chu()"), h.index("M4_CHI_MAY_CHU_NGUON"), h.index("p_actor::text IS DISTINCT FROM"),
              h.index("M4_KT_DANH_TINH"), h.index("PERFORM m4.kt_kiem(p_cho, 'XEM')"), h.index("M4_THAM_SO_SAI"),
              h.index("ORDER BY x.thu_tu DESC LIMIT 1"), h.index("m4._kt_chung_thuc_mau(moi,"), h.index("M4_KT_KHONG_THAY"),
              h.index(f"pg_catalog.set_config('{SK.GUC_CHUNG_THUC}', a::text, true)")]
        self.assertEqual(vt, sorted(vt))
        d = _dau("m4._kt_chung_thuc_ghi")
        self.assertNotIn("SECURITY DEFINER", d)
        self.assertNotIn(" SET ", d)  # SET clause của hàm sẽ hoàn GUC khi thoát — chứng thực phải sống tới hết giao dịch
        self.assertEqual(NOI.count(f"set_config('{SK.GUC_CHUNG_THUC}'"), 1)  # chỉ MỘT nơi ghi chứng thực

    def test_doc_so_dung_chuoi_voi_do_thi_da_seal(self):
        h = _ham("m4._kt_co_so_hien_hanh")
        self.assertIn(f"nullif(current_setting('{SK.GUC_CHUNG_THUC}', true), '')", h)
        self.assertLess(h.index("IF a IS NULL OR NOT m4._kt_phien_chu() THEN"), h.index("RETURN false"))
        self.assertLess(h.index("RETURN false"), h.index("m4._kt_chung_thuc_mau(b.id, b.phien_ban_id, s.graph_sha256, k.graph->>'co_so_l3_sha256')"))
        self.assertIn("JOIN m4.duyet_ket_luan k ON k.id = s.ket_luan_id", h)
        self.assertIn("k.graph_sha256 = s.graph_sha256", h)
        self.assertIn("RETURN mau IS NOT NULL AND a = mau::text", h)
        self.assertNotIn("set_config", h)
        self.assertNotIn("SECURITY DEFINER", _dau("m4._kt_co_so_hien_hanh"))
        for k in ("run_id", "ket_qua_sha256", "basis_sha256"):  # không thay toàn căn cứ bằng run/hash L3
            self.assertNotIn(k, h)

    def test_ham_noi_bo_khong_cap(self):
        noi_bo = " ".join(SK.HAM_NOI_BO)
        cap = " ".join(re.findall(r"GRANT EXECUTE ON FUNCTION (.*?) TO ", NOI, re.S) + list(SK.HAM_DOC) + list(SK.HAM_LENH))
        revoke = next(s for s in SK.M4_03A_SQL if s.startswith("REVOKE EXECUTE ON FUNCTION"))
        for ten in HAM_MOI:
            self.assertIn(ten + "(", noi_bo)
            self.assertIn(ten + "(", revoke)
            self.assertNotIn(ten + "(", cap)
            self.assertNotIn("SECURITY DEFINER", _dau(ten))

    def test_khoa_doc_quyen_truoc_khoa_hd(self):
        h = _ham("m4._kt_khoa_doc")
        vt = [h.index("master.la_chu_bang('m4.kt_xac_nhan'::regclass)"), h.index("q := m4.kt_kiem(p_cho, 'XEM')"),
              h.index("FROM m4.ho_so_hop_dong WHERE hop_dong_id = c.hop_dong_id FOR SHARE")]
        self.assertEqual(vt, sorted(vt))
        self.assertNotIn("FOR UPDATE", h)

    def test_khong_bang_bi_mat_vai_cau_hinh_toan_cuc(self):
        for k in ("ALTER SYSTEM", "ALTER DATABASE", "ALTER ROLE", "SET ROLE", "CREATE ROLE", "pgcrypto", "hmac(", "gen_random_bytes",
                  "kt_chung_thuc TEXT", "CREATE TABLE m4.kt_chung_thuc"):
            self.assertNotIn(k, NOI)
        self.assertEqual(SK.GUC_CHUNG_THUC, "ktt.kt_chung_thuc")


class HienHanhSql(unittest.TestCase):
    def test_hien_hanh_them_can_cu(self):
        h = _ham("m4._kt_hien_hanh")
        self.assertIn("cs := b.id IS NOT NULL AND m4._kt_co_so_hien_hanh(b.id);", h)
        self.assertIn("'co_so_hien_hanh', cs", h)
        self.assertIn("v_moi IS NOT DISTINCT FROM b.phien_ban_id AND dt AND cs", h)
        self.assertIn(f"WHEN NOT cs THEN '{SK.LY_DO_CO_SO}'", h)
        self.assertLess(h.index("WHEN NOT dt THEN"), h.index("WHEN NOT cs THEN"))
        self.assertEqual(SK.LY_DO_CO_SO, "CAN_CU_DOI_SAU_SEAL")
        self.assertEqual(len(SK.LY_DO_HOLD), 2)  # bộ cũ giữ nguyên; bộ đầy đủ là bộ mới tách riêng
        self.assertEqual(SK.LY_DO_HOLD_DAY_DU, (*SK.LY_DO_HOLD, SK.LY_DO_CO_SO))
        self.assertIs(KT.LY_DO_KHONG_HIEN_HANH, SK.LY_DO_HOLD)

    def test_trigger_kiem_can_cu_truoc_revision(self):
        h = _ham("m4.kt_xac_nhan_kiem")
        vt = [h.index("v_moi IS DISTINCT FROM b.phien_ban_id"), h.index("m4._kt_do_thi_hien_hanh(b.id)"),
              h.index("IF NOT m4._kt_co_so_hien_hanh(b.id) THEN"), h.index("M4_KT_REVISION_CU")]
        self.assertEqual(vt, sorted(vt))
        seg = h[vt[2]:vt[3]]
        self.assertIn("M4_KT_CAN_KIEM_LAI", seg)

    def test_lenh_doc_dung_hien_hanh_chung(self):
        for ten in ("m4.kt_chi_tiet", "m4.kt_danh_sach", "m4.kt_luu", "m4.kt_xac_nhan_lenh"):
            h = _ham(ten)
            self.assertIn("m4._kt_hien_hanh(", h)  # hiện hành (gồm căn cứ) do một hàm SQL quyết cho đọc/lệnh/phát lại
            self.assertNotIn("_kt_chung_thuc_ghi", h)  # hàm đọc/lệnh không tự ghim — chỉ service dựng producer rồi ghim
            self.assertNotIn("set_config", h)
        self.assertIn("căn cứ đổi sau seal", SK._PHONG_BI)  # lệnh mới trên nguồn không hiện hành: M4_KT_CAN_KIEM_LAI nêu cả lý do căn cứ
        self.assertIn("M4_KT_CAN_KIEM_LAI", SK._PHONG_BI)
        self.assertIn("(h->>'hien_hanh')::boolean", SK._LAP_LAI)  # phát lại cùng khóa cũng phụ thuộc hiện hành toàn căn cứ


# ================================================================================================== tái sử dụng producer
class TaiSuDungProducer(unittest.TestCase):
    def test_ghim_goi_dung_producer(self):
        s = inspect.getsource(KT._ghim_do_thi)
        for k in ("DD.DuyetDot._dot(xd, c,", "DD.DuyetDot._phien_ban(xd, c,", "DD.do_thi(xd, c, dt, d, vs[-1])",
                  "m4._kt_chung_thuc_ghi(%s::uuid, %s::uuid, %s::uuid, %s, %s)", 'g["co_so_l3_sha256"]', 'dt["id"]'):
            self.assertIn(k, s)
        for k in ("_chung_tu_co_so", "_sha_co_so", "canonical_json", "hashlib", "._xem(", "._thay(", "set_config"):
            self.assertNotIn(k, s)  # không tự dựng/rút gọn đồ thị/căn cứ, không gọi đường REVIEW, không tự đổi danh tính

    def test_producer_khoi_phuc_trong_finally(self):
        s = inspect.getsource(DD.do_thi)  # tệp producer KHÔNG sửa — chỉ đọc lại để ràng buộc giả định
        i = s.index("finally:")
        self.assertLess(s.index('_dat_danh_tinh(c, r["tao_boi_id"], r["tao_dang_nhap"])'), i)
        self.assertGreater(s.index('_dat_danh_tinh(c, dt["id"], dt["dang_nhap"])'), i)
        self.assertIn('"co_so_l3_sha256": sha_l3', s)

    def test_lop_dich_vu_khong_tu_suy(self):
        s = inspect.getsource(KT.KeToanNghiemThuK2)
        for k in ("chung_tu", "can_cu_hien_hanh", "DD.do_thi", "co_so_l3", "graph_sha256"):
            self.assertNotIn(k, s)
        self.assertIsNone(re.search(r"^\s*(from|import)\s+\S*xay_dung", inspect.getsource(KT), re.M))  # không import engine nguồn
        self.assertEqual(KT.LENH_HANH, (("m4.kt_luu(", "LUU"), ("m4.kt_xac_nhan_lenh(", "XAC_NHAN")))


# ================================================================================================== thứ tự biên (FAKE_XD_CHU, có nhãn)
NHAN = ("m4.kt_doc_cho(", "m4._kt_khoa_doc(", "m4.kt_khoa(", "FROM m4.duyet_kt_cho", "FROM m4.dot d", "FROM m4.duyet_phien_ban v",
        "FROM m4.chung_tu_run r", "m4._kt_chung_thuc_ghi(", "m4._kt_hien_hanh(", "m4.kt_chi_tiet(", "m4.kt_luu(", "m4.kt_xac_nhan_lenh(",
        "m4.kt_kiem(", "m4.kt_danh_sach(", "m4.kt_pdf(")
PDF = {"id": _id(51), "ten": "ho-so-dot.pdf", "media_type": "application/pdf", "raw_sha256": H["pdf"], "byte_length": 2048}


def _nhan(sql: str) -> str:
    n = next((k for k in NHAN if k in sql), None)
    if n is None:
        raise AssertionError("FAKE_XD_CHU: SQL ngoài kịch bản — " + sql[:80])
    return n


def _ctx(pb=11) -> dict:
    return {"phap_nhan_id": _id(1), "du_an_id": _id(2), "hop_dong_id": _id(3), "dot_id": _id(4), "kt_pending_id": _id(5), "phong_bi_id": _id(pb),
            "seal_id": _id(21), "version_id": _id(31), "ket_luan_id": _id(41), "pdf_id": _id(51), "phong_bi_sha256": H["pb"],
            "graph_sha256": H["graph"], "pdf_sha256": H["pdf"]}


def _nd() -> dict:
    return {"tien_te": "VND", "gia_tri_nt": "1000000", "so_xin_thanh_toan": "900000", "tam_ung": "0", "thu_hoi": "100000", "giu_lai": "50000",
            "dong": [], "pdf": {"id": _id(51), "raw_sha256": H["pdf"], "byte_length": 2048}}


def _kt_nhap() -> dict:
    r = {"kt_revision_id": _id(101), "revision": 1, "loai": "NHAP", "nhap_id": None, "phong_bi_id": _id(11), "tien_te": "VND",
         "gia_tri_nt_xac_nhan": "1000000", "tam_ung_xac_nhan": None, "thu_hoi_xac_nhan": None, "giu_lai_xac_nhan": None,
         "co_so_gia_tri": "TRUOC_VAT", "vat_trang_thai": "KHONG_AP_DUNG", "vat_can_cu_tep_id": None, "vat_can_cu_sha256": None,
         "vat_trich_dan": None, "ly_do": "Hóa đơn chưa phát sinh VAT"}
    r["thieu"] = KT.thieu(r, _nd())
    return r


def _ct(kt=None, hien=True) -> dict:
    """Khung biên viết tay (hình dạng m4.kt_chi_tiet) — không phải producer."""
    c = _ctx()
    return {"context": c, "can_cu_hien_hanh": hien, "nguon": _nd(), "pdf": dict(PDF), "tep_can_cu": [], "kt": kt, "da_xac_nhan": False,
            "lich_su_phong_bi": [{"context": c, "thu_tu": 1, "truoc_id": None, "phien_ban_so": 1, "can_cu_hien_hanh": hien}],
            "lich_su_kt": [] if kt is None else [{"context": c, "kt": kt, "nguon": {k: v for k, v in _nd().items() if k != "dong"}}]}


def _body_luu(**kw) -> dict:
    b = {"kt_pending_id": _id(5), "phong_bi_id": _id(11), "expected_phong_bi_sha256": H["pb"], "expected_revision": 0,
         "gia_tri_nt_xac_nhan": None, "tien_te": None, "co_so_gia_tri": "CHUA_RO", "tam_ung_xac_nhan": None, "thu_hoi_xac_nhan": None,
         "giu_lai_xac_nhan": None, "vat_trang_thai": "CHUA_DU", "vat_can_cu_tep_id": None, "vat_trich_dan": None, "ly_do": None, "khoa": "fb-luu-1"}
    b.update(kw)
    return b


def _ack(hanh="LUU") -> dict:
    xn = hanh == "XAC_NHAN"
    kq = {"hanh_dong": hanh, "context": _ctx(), "kt_revision_id": _id(102 if xn else 101), "revision": 2 if xn else 1,
          "loai": "XAC_NHAN" if xn else "NHAP", "nhap_id": _id(101) if xn else None, "trang_thai": SK.TT_DA_XAC_NHAN if xn else KT.TT_CHO_XAC_NHAN,
          "thieu": [], "trung_xac_nhan": False, "ap": dict(KT.AP), "request": dict(KT.REQUEST)}
    return {"lap_lai": False, "ket_qua": kq, "receipt_id": _id(900)}


class FakeXdChu:
    """FAKE_XD_CHU — đối tượng giả CHỈ để kiểm thứ tự gọi; không phải PostgreSQL. Hàm producer thật (DuyetDot._dot/_phien_ban, do_thi) chạy trên
    fake này: đợt/phiên bản/L3 công bố (người công bố MO_PHONG_SOAN ≠ KT) là khung viết tay; _chung_tu_co_so/_sha_co_so giả (có thể ép lỗi)."""

    def __init__(self, ct=None, kq=None, *, ds=(), doc=None, hh=None, loi_khoa=None, loi_co_so=None, khong_dot=False):
        self.goi, self.ct, self.kq, self.ds, self.doc, self.hh = [], ct, kq, list(ds), doc, dict(hh or {})
        self.loi_khoa, self.loi_co_so, self.khong_dot, self.conn_tin_cay = loi_khoa, loi_co_so, khong_dot, object()

    def danh_tinh(self, dang_nhap):
        self.goi.append(("danh_tinh", dang_nhap))
        return {"id": _id(800), "dang_nhap": dang_nhap}

    @contextmanager
    def _tx(self, dt):
        self.goi.append(("tx_app",))
        yield

    def _mot(self, sql, params=()):
        n = _nhan(sql)
        self.goi.append(("app", n, params))
        return {"m4.kt_chi_tiet(": {"ct": self.ct}, "m4.kt_danh_sach(": {"ds": self.ds}, "m4.kt_pdf(": {"p": dict(PDF)},
                "m4.kt_kiem(": {"q": "KE_TOAN"}}[n]

    def _raw(self, sha, dai=None):
        self.goi.append(("raw", sha))
        return b"%PDF-"

    @contextmanager
    def _chua_ro(self):
        yield

    @contextmanager
    def _tx_review(self, dt, rr=False):
        self.goi.append(("tx_chu",))
        yield FakeConnChu(self.goi)

    def _r1(self, c, sql, params=()):
        n = _nhan(sql)
        self.goi.append(("chu", n, params))
        if n == "m4.kt_doc_cho(":
            return {"ok": self.doc is None or params[0] in self.doc}
        if n == "m4.kt_khoa(" and self.loi_khoa:
            raise DataError(self.loi_khoa, "FAKE: quyền KT đã thu hồi")
        if n in ("m4.kt_khoa(", "m4._kt_khoa_doc("):
            return {"q": "KE_TOAN"}
        if n == "FROM m4.duyet_kt_cho":
            return None if self.khong_dot else {"dot_id": _id(4)}
        if n == "FROM m4.dot d":
            return {"id": _id(4), "hop_dong_id": _id(3), "du_an_id": _id(2), "phap_nhan_id": _id(1), "so_dot": 1, "ngay_nghiem_thu": "2026-10-01",
                    "trang_thai": "DA_NOP", "revision": 1, "so_hop_dong": "HD-1", "revision_ho_so_hien_hanh": 2}
        if n == "FROM m4.chung_tu_run r":
            return {"run_id": _id(600), "revision": 1, "trang_thai": "SUCCEEDED", "basis_sha256": H["graph"], "tao_boi_id": _id(700),
                    "tao_dang_nhap": "MO_PHONG_SOAN", "ket_qua": {}, "ket_qua_sha256": H["pb2"], "basis_cong_bo_sha256": H["graph"]}
        if n == "m4._kt_chung_thuc_ghi(":
            return {"a": {"kt_pending_id": params[0]}}
        if n == "m4._kt_hien_hanh(":
            return {"h": self.hh.get(params[0])}
        if n == "m4.kt_chi_tiet(":
            return {"ct": self.ct}
        return {"r": self.kq}

    def _rn(self, c, sql, params=()):
        self.goi.append(("chu", _nhan(sql), params))
        return [{"id": _id(31), "so": 1, "parent_id": None, "nop_id": _id(32), "trang_thai": "DA_NOP", "ly_do": None, "digest": H["pb"],
                 "revision_ho_so": 2, "ket_luan_revision": 1, "quyet_dinh_id": _id(61), "seal_id": _id(21)}]

    def _chung_tu_co_so(self, c, dot):
        self.goi.append(("co_so", dot))
        if self.loi_co_so:
            raise DataError(self.loi_co_so, "FAKE: producer lỗi giữa chừng")
        return {"l2": {}}

    @staticmethod
    def _sha_co_so(co):
        return H["graph"]


class FakeConnChu:
    """FAKE_CONN — chỉ ghi lại set_config danh tính mà producer do_thi gọi."""

    def __init__(self, goi):
        self.goi = goi

    def execute(self, sql, params=()):
        self.goi.append(("guc", tuple(params)))


def _vet(goi) -> list:
    return [g[1] if g[0] in ("app", "chu") else g[0] for g in goi]


GHIM = ["FROM m4.duyet_kt_cho", "FROM m4.dot d", "FROM m4.duyet_phien_ban v", "FROM m4.chung_tu_run r", "guc", "co_so", "guc",
        "m4._kt_chung_thuc_ghi("]
GUC = [(_id(700), "MO_PHONG_SOAN"), (_id(800), "MO_PHONG_KT")]


class ThuTuChu(unittest.TestCase):
    def test_xem_quyen_app_truoc_chu_roi_producer(self):
        xd = FakeXdChu(_ct())
        x = KT.KeToanNghiemThuK2(xd).xem("MO_PHONG_KT", kt_pending_id=_id(5))
        self.assertEqual(_vet(xd.goi), ["danh_tinh", "tx_app", "m4.kt_kiem(", "tx_chu", "m4._kt_khoa_doc(", *GHIM, "m4.kt_chi_tiet("])
        self.assertEqual([g[1] for g in xd.goi if g[0] == "guc"], GUC)
        at = next(g for g in xd.goi if g[0] == "chu" and g[1] == "m4._kt_chung_thuc_ghi(")[2]
        self.assertEqual(at[:3], (_id(5), _id(800), _id(31)))  # gốc, actor KT đã khôi phục, phiên bản MỚI NHẤT
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", at[3]))  # SHA do do_thi trả (không phải hằng của service)
        self.assertEqual(at[4], H["graph"])  # co_so_l3_sha256 của producer
        self.assertEqual(x["context"], _ctx())

    def test_danh_sach_moi_goc_mot_giao_dich(self):
        def dong(n):
            return {"kt_pending_id": _id(n), "dot_id": _id(4), "phong_bi_id": _id(11), "phong_bi_sha256": H["pb"], "toan_ven": True, "kt": None,
                    "hien_hanh": True}  # cờ app bị BỎ QUA: phiên ứng dụng không bao giờ thấy hiện hành
        hh = {_id(5): {"hien_hanh": True, "phong_bi_id": _id(11)}, _id(7): {"hien_hanh": True, "phong_bi_id": _id(12)},
              _id(8): {"hien_hanh": False, "phong_bi_id": _id(11), "ly_do": SK.LY_DO_CO_SO}}
        xd = FakeXdChu(ds=[dong(5), dong(6), dong(7), dong(8)], doc={_id(5), _id(7), _id(8)}, hh=hh)
        out = KT.KeToanNghiemThuK2(xd).danh_sach("MO_PHONG_KT")
        self.assertEqual([(r["kt_pending_id"], r["trang_thai"]) for r in out["items"]],
                         [(_id(5), KT.TT_CHO_XAC_NHAN), (_id(7), KT.TT_CAN_KIEM_LAI), (_id(8), KT.TT_CAN_KIEM_LAI)])
        v = _vet(xd.goi)
        self.assertEqual(v[:3], ["danh_tinh", "tx_app", "m4.kt_danh_sach("])
        dau = [i for i, x in enumerate(v) if x == "tx_chu"] + [len(v)]
        doan = [v[a:b] for a, b in zip(dau, dau[1:])]
        du = ["tx_chu", "m4.kt_doc_cho(", "m4._kt_khoa_doc(", *GHIM, "m4._kt_hien_hanh("]
        self.assertEqual(doan, [du, ["tx_chu", "m4.kt_doc_cho("], du, du])  # gốc mất quyền: không khóa, không producer
        self.assertEqual([g[2][0] for g in xd.goi if g[0] == "chu" and g[1] == "m4._kt_chung_thuc_ghi("], [_id(5), _id(7), _id(8)])

    def test_goi_lenh_ngoai_hop_dong_tu_choi_truoc_ket_noi(self):
        xd = FakeXdChu()
        svc = KT.KeToanNghiemThuK2(xd)
        self.assertEqual(_ma(svc._goi, {"id": _id(800), "dang_nhap": "K"}, "SELECT m4.kt_khac(%s, %s, %s) AS r", ("k", "{}", _id(5)), "k"),
                         "M4_THAM_SO_SAI")
        self.assertEqual(xd.goi, [])
        self.assertEqual((KT._hanh_lenh("SELECT m4.kt_luu(%s) AS r"), KT._hanh_lenh("SELECT m4.kt_xac_nhan_lenh(%s) AS r")), ("LUU", "XAC_NHAN"))

    def test_thu_hoi_quyen_chan_truoc_can_cu(self):
        xd = FakeXdChu(_ct(), _ack(), loi_khoa="M4_KT_PHAM_VI")
        self.assertEqual(_ma(KT.KeToanNghiemThuK2(xd).luu, "MO_PHONG_KT", _body_luu()), "M4_KT_PHAM_VI")
        v = _vet(xd.goi)
        self.assertEqual(v[v.index("tx_chu"):], ["tx_chu", "m4.kt_khoa("])  # không đọc căn cứ, không đổi danh tính, không ghim, không ghi
        self.assertNotIn("co_so", v)

    def test_loi_producer_van_khoi_phuc_kt_khong_ghim(self):
        xd = FakeXdChu(_ct(), _ack(), loi_co_so="M4_LOI_GIA_PRODUCER")
        self.assertEqual(_ma(KT.KeToanNghiemThuK2(xd).luu, "MO_PHONG_KT", _body_luu()), "M4_LOI_GIA_PRODUCER")
        v = _vet(xd.goi)
        self.assertEqual(v[v.index("tx_chu"):], ["tx_chu", "m4.kt_khoa(", *GHIM[:-1]])
        self.assertEqual([g[1] for g in xd.goi if g[0] == "guc"], GUC)  # finally: người công bố → KT dù lỗi
        self.assertNotIn("m4.kt_luu(", v)

    def test_luu_va_xac_nhan_quyen_khoa_can_cu_truoc_lenh(self):
        for hanh, ten, ct, goi in (("LUU", "m4.kt_luu(", _ct(), lambda s: s.luu("MO_PHONG_KT", _body_luu())),
                                   ("XAC_NHAN", "m4.kt_xac_nhan_lenh(", _ct(_kt_nhap()),
                                    lambda s: s.xac_nhan("MO_PHONG_KT", {"kt_pending_id": _id(5), "phong_bi_id": _id(11), "kt_revision_id": _id(101),
                                                                         "expected_revision": 1, "expected_phong_bi_sha256": H["pb"], "khoa": "fb-xn-1"}))):
            with self.subTest(hanh=hanh):
                xd = FakeXdChu(ct, _ack(hanh))
                a = goi(KT.KeToanNghiemThuK2(xd))
                v = _vet(xd.goi)
                self.assertEqual(v[v.index("tx_chu"):], ["tx_chu", "m4.kt_khoa(", *GHIM, ten])
                self.assertEqual(v.count("tx_chu"), 1)
                self.assertLess(v.index("raw"), v.index("tx_chu"))  # kiểm sớm login thường vẫn trước giao dịch chủ bảng
                self.assertEqual(next(g for g in xd.goi if g[0] == "chu" and g[1] == "m4.kt_khoa(")[2], (_id(5), hanh))
                self.assertEqual([g[1] for g in xd.goi if g[0] == "guc"], GUC)
                self.assertEqual((a["hanh_dong"], a["ap"]["da_ghi_cong_no"]), (hanh, False))

    def test_khong_thay_dot_khong_producer(self):
        xd = FakeXdChu(_ct(), khong_dot=True)
        self.assertEqual(_ma(KT.KeToanNghiemThuK2(xd).xem, "MO_PHONG_KT", kt_pending_id=_id(5)), "M4_KT_KHONG_THAY")
        v = _vet(xd.goi)
        self.assertEqual(v[v.index("tx_chu"):], ["tx_chu", "m4._kt_khoa_doc(", "FROM m4.duyet_kt_cho"])

    def test_pdf_van_login_thuong(self):
        xd = FakeXdChu()
        self.assertEqual(KT.KeToanNghiemThuK2(xd).tep_pdf("MO_PHONG_KT", _id(5), _id(11)), ("ho-so-dot.pdf", "application/pdf", b"%PDF-"))
        self.assertEqual(_vet(xd.goi), ["danh_tinh", "tx_app", "m4.kt_pdf(", "raw", "tx_app", "m4.kt_pdf("])

    def test_chu_ky_cong_khai_khong_doi(self):
        C = KT.KeToanNghiemThuK2
        sig = {t: list(inspect.signature(getattr(C, t)).parameters) for t in ("luu", "xac_nhan", "xem", "danh_sach", "tep_pdf", "_goi")}
        self.assertEqual(sig, {"luu": ["self", "dang_nhap", "body", "kw"], "xac_nhan": ["self", "dang_nhap", "body", "kw"],
                               "xem": ["self", "dang_nhap", "kt_pending_id", "phong_bi_id"], "danh_sach": ["self", "dang_nhap"],
                               "tep_pdf": ["self", "dang_nhap", "kt_pending_id", "phong_bi_id"], "_goi": ["self", "dt", "sql", "params", "khoa"]})
        self.assertEqual((KT.ACK_KEYS, KT.XEM_KEYS, KT.DONG_DS_KEYS, KT.TRUONG_LUU[-1], KT.TRUONG_XAC_NHAN[-1]),
                         (("schema", "context", "kt_revision_id", "revision", "trang_thai", "lap_lai", "receipt_id", "ap", "request"),
                          ("schema", "context", "quyen", "can_cu_hien_hanh", "nguon", "kt", "lich_su", "ap", "request"),
                          ("kt_pending_id", "dot_id", "phong_bi_id", "phong_bi_sha256", "revision", "trang_thai", "ap"), "khoa", "khoa"))


if __name__ == "__main__":
    unittest.main()
