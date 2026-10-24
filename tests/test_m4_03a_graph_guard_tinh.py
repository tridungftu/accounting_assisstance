"""M4-03A graph guard — kiểm TĨNH + THUẦN bổ sung (không PostgreSQL). CODE_ONLY: WRITTEN_NOT_RUN.

Bổ sung cho tests/test_m4_03a_tinh.py (27 test gốc giữ nguyên). Kiểm:
- `GuardSql`: guard đồ thị nằm trong SQL (m4._kt_do_thi_hien_hanh → m4._kt_hien_hanh → lệnh/phát lại dưới khóa + trigger), không chỉ kiểm sớm Python.
- `SeamProducer`: quy tắc chọn kết quả L3 đã công bố và thành phần L3 của đồ thị đọc từ NGUỒN THẬT của producer M24 (duyet_dot._l3_cong_bo /
  do_thi, sql_duyet kết luận) — không gương tự viết.
- `HopDongGiuNguyen`: chữ ký lệnh/body/ACK/DTO công khai không đổi; docstring module SQL không còn literal M00xx.
- `DtoHold`: builder DTO thật trên KHUNG BIÊN VIẾT TAY (nhãn rõ): phong bì HOLD vì đồ thị → không lưu/xác nhận, lịch sử/PDF giữ; baseline hiện hành
  vẫn mở lệnh (chống always-HOLD). Không phải bằng chứng producer/PG (đó là tests/test_m4_03a_graph_guard_pg.py).
"""

from __future__ import annotations

import inspect
import re
import unittest
import uuid
from pathlib import Path

from kho_tri_thuc.m4 import duyet_dot as DD
from kho_tri_thuc.m4 import ke_toan_nghiem_thu as KT
from kho_tri_thuc.m4 import sql_duyet as SD
from kho_tri_thuc.m4 import sql_ke_toan_nghiem_thu as SK

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
NOI = "\n".join(SK.M4_03A_SQL)
CHON = "r.trang_thai IN ('SUCCEEDED','PARTIAL') AND x.cong_bo"
THU_TU = "ORDER BY r.xong_luc DESC NULLS LAST, r.tao_luc DESC, r.id LIMIT 1"


def _ham(ten: str) -> str:
    i = NOI.index(f"CREATE OR REPLACE FUNCTION {ten}(")
    a = NOI.index("$$", i)
    return NOI[i:NOI.index("$$", a + 2)]


def _gon(s: str) -> str:
    return re.sub(r"\s+", " ", s)


def _id(n: int) -> str:
    return str(uuid.UUID(int=n))


class GuardSql(unittest.TestCase):
    def test_ham_do_thi_so_dung_thanh_phan_l3_cua_seal(self):
        f = _gon(_ham("m4._kt_do_thi_hien_hanh"))
        self.assertIn("RETURNS boolean", f)
        self.assertIn("STABLE", f)
        self.assertNotIn("SECURITY DEFINER", f)
        self.assertIn("JOIN m4.duyet_seal s ON s.id = b.seal_id JOIN m4.duyet_ket_luan k ON k.id = s.ket_luan_id", f)
        self.assertIn("l.run_id = k.l3_run_id", f)
        self.assertIn("l.ket_qua_sha256 IS NOT DISTINCT FROM (k.graph->'l3'->>'ket_qua_sha256')", f)
        self.assertIn(_gon(SK.L3_CONG_BO_MOI_NHAT), f)
        self.assertIn("), false)", f)  # không có kết quả công bố → HOLD, không đoán hiện hành

    def test_hien_hanh_gom_do_thi_va_ly_do(self):
        f = _gon(_ham("m4._kt_hien_hanh"))
        self.assertIn("dt := b.id IS NOT NULL AND m4._kt_do_thi_hien_hanh(b.id)", f)
        self.assertIn("'hien_hanh', b.id IS NOT NULL AND v_moi IS NOT DISTINCT FROM b.phien_ban_id AND dt", f)
        self.assertIn(f"WHEN v_moi IS DISTINCT FROM b.phien_ban_id THEN '{SK.LY_DO_PHIEN_BAN}'", f)
        self.assertIn(f"WHEN NOT dt THEN '{SK.LY_DO_DO_THI}'", f)
        self.assertEqual(SK.LY_DO_HOLD, ("PHIEN_BAN_KE_TIEP_CHUA_SEAL", "L3_CONG_BO_LAI_SAU_SEAL"))
        # chi tiết/danh sách/lịch sử dùng cùng cờ hien_hanh (không suy từ vị trí mảng)
        ct = _gon(_ham("m4.kt_chi_tiet"))
        self.assertIn("h := m4._kt_hien_hanh(p_cho)", ct)
        self.assertIn("'can_cu_hien_hanh', b.id = moi AND hh", ct)
        self.assertIn("'can_cu_hien_hanh', x.id = moi AND hh", ct)
        self.assertIn("'ly_do_hold', CASE WHEN b.id = moi AND NOT hh THEN h->>'ly_do' END", ct)
        self.assertIn("h := m4._kt_hien_hanh(c.id)", _gon(_ham("m4.kt_danh_sach")))

    def test_lenh_kiem_duoi_khoa_truoc_ghi_va_phat_lai(self):
        for f, hd in (("m4.kt_luu", "KT_LUU"), ("m4.kt_xac_nhan_lenh", "KT_XAC_NHAN")):
            h = _ham(f)
            vt = [h.index(s) for s in ("m4.kt_khoa(", f"m4._bn_tra(aid, p_khoa, '{hd}'", "h := m4._kt_hien_hanh(p_cho)",
                                       "coalesce((h->>'hien_hanh')::boolean, false)", "'lap_lai', true",
                                       "M4_KT_CAN_KIEM_LAI", "INSERT INTO m4.kt_xac_nhan", f"m4._bn_ghi(aid, p_khoa, '{hd}'")]
            self.assertEqual(vt, sorted(vt), f)  # phát lại (lap_lai) chỉ sau khi kiểm hiện hành → replay nguồn cũ bị chặn

    def test_khoa_cho_cong_bo_dang_do(self):
        k = _gon(_ham("m4.kt_khoa"))
        self.assertIn("PERFORM 1 FROM m4.chung_tu_run r WHERE r.dot_id = c.dot_id AND r.trang_thai IN ('PENDING','RUNNING') FOR SHARE", k)
        self.assertLess(k.index("FROM m4.kt_xac_nhan"), k.index("FROM m4.chung_tu_run"))  # thứ tự khóa cũ giữ nguyên, khóa run sau cùng
        self.assertNotRegex(k, r"chung_tu_run[^;]*FOR UPDATE")
        # m4.chung_tu_cong_bo (M22, bất biến) khóa run FOR UPDATE — FOR SHARE ở đây chờ giao dịch công bố đang dở rồi mới đọc đồ thị
        from kho_tri_thuc.m4 import sql_chung_tu as SC
        cb = next(s for s in SC.M0022_M4_CHUNG_TU if "FUNCTION m4.chung_tu_cong_bo(" in s)
        self.assertIn("FROM m4.chung_tu_run WHERE id = p_run FOR UPDATE", cb)

    def test_trigger_chan_tai_thoi_diem_insert(self):
        t = _ham("m4.kt_xac_nhan_kiem")
        i_pb, i_dt, i_rev = (t.index("v_moi IS DISTINCT FROM b.phien_ban_id"), t.index("IF NOT m4._kt_do_thi_hien_hanh(b.id) THEN"),
                             t.index("M4_KT_REVISION_CU"))
        self.assertLess(i_pb, i_dt)
        self.assertLess(i_dt, i_rev)
        self.assertIn("M4_KT_CAN_KIEM_LAI: Chứng từ L3 đã công bố lại sau seal", t[i_dt:i_rev])

    def test_quyen_ham_moi_noi_bo(self):
        self.assertIn("m4._kt_do_thi_hien_hanh(uuid)", SK.HAM_NOI_BO)
        rv = next(s for s in SK.M4_03A_SQL if s.startswith("REVOKE EXECUTE ON FUNCTION"))
        self.assertIn("m4._kt_do_thi_hien_hanh(uuid)", rv)
        g = next(s for s in SK.M4_03A_SQL if "GRANT EXECUTE" in s)
        self.assertNotIn("_kt_do_thi_hien_hanh", g)
        self.assertLess(NOI.index("CREATE OR REPLACE FUNCTION m4._kt_do_thi_hien_hanh("), NOI.index("CREATE OR REPLACE FUNCTION m4._kt_hien_hanh("))

    def test_khong_ghi_m24_chung_tu_khong_cap_quyen(self):
        for bang in ("chung_tu_run", "chung_tu_result", "duyet_ket_luan", "duyet_seal", "duyet_kt_phong_bi", "duyet_pdf", "duyet_phien_ban"):
            self.assertNotRegex(NOI, rf"(UPDATE|DELETE FROM|INSERT INTO)\s+m4\.{bang}\b")
        self.assertNotIn("INSERT INTO m4.quyen_du_an", NOI)
        self.assertNotRegex(NOI, r"'(REVIEW|DUYET)'\s*\)?\s*(TO|INTO)")
        self.assertNotIn("m4.chung_tu_kiem(", NOI)  # không mượn quyền SOAN/REVIEW của L3 — quyền KT riêng


class SeamProducer(unittest.TestCase):
    def test_quy_tac_chon_l3_trung_producer(self):
        src = _gon(inspect.getsource(DD._l3_cong_bo))
        for s in (CHON, THU_TU, "FROM m4.chung_tu_run r JOIN m4.chung_tu_result x ON x.run_id = r.id"):
            self.assertIn(s, src)
            self.assertIn(s, _gon(SK.L3_CONG_BO_MOI_NHAT))

    def test_thanh_phan_l3_trong_do_thi_va_ket_luan(self):
        dt = inspect.getsource(DD.do_thi)
        self.assertIn('"run_id": r["run_id"]', dt)
        self.assertIn('"ket_qua_sha256": r["ket_qua_sha256"]', dt)
        self.assertIn('"l3": l3', dt)  # run_id + ket_qua_sha256 của L3 công bố là một phần đồ thị đã băm
        m24 = _gon("\n".join(SD.M0024_M4_DUYET))
        self.assertIn("l3_run_id uuid NOT NULL", m24)
        self.assertIn("p_graph, p_graph_hien_tai, (p_graph->'l3'->>'run_id')::uuid", m24)  # kết luận lưu đúng graph + l3_run_id đã băm
        self.assertIn("(p_graph->'l3'->>'trang_thai') IS DISTINCT FROM 'CO'", m24)


class HopDongGiuNguyen(unittest.TestCase):
    def test_docstring_khong_literal_ordinal(self):
        nguon = (SRC / "m4" / "sql_ke_toan_nghiem_thu.py").read_text(encoding="utf-8")
        self.assertNotRegex(nguon, r"M00\d\d")
        self.assertIn("SAU nguyên prefix M24 và mọi migration đã cấp", nguon.splitlines()[2])

    def test_chu_ky_va_hop_dong_cong_khai(self):
        self.assertEqual(SK.HAM_LENH, ("m4.kt_khoa(uuid, text)", "m4.kt_luu(text, jsonb, uuid, uuid, text, integer, jsonb)",
                                       "m4.kt_xac_nhan_lenh(text, jsonb, uuid, uuid, text, uuid, integer)"))
        self.assertEqual(SK.HAM_DOC[-2:], ("m4.kt_chi_tiet(uuid, uuid)", "m4.kt_pdf(uuid, uuid)"))
        self.assertEqual(KT.XEM_KEYS, ("schema", "context", "quyen", "can_cu_hien_hanh", "nguon", "kt", "lich_su", "ap", "request"))
        self.assertEqual(KT.ACK_KEYS, ("schema", "context", "kt_revision_id", "revision", "trang_thai", "lap_lai", "receipt_id", "ap", "request"))
        self.assertEqual(len(KT.TRUONG_LUU), 15)
        self.assertEqual(len(KT.TRUONG_XAC_NHAN), 6)
        self.assertEqual(KT.LY_DO_KHONG_HIEN_HANH, SK.LY_DO_HOLD)
        for k in ("graph_sha256", "expected_graph_sha256", "l3_run_id"):
            self.assertNotIn(k, KT.TRUONG_LUU + KT.TRUONG_XAC_NHAN)  # trình duyệt không gửi đồ thị — máy chủ tự resolve
        self.assertIn("graph_sha256", KT.KHONG_NHAN)

    def test_service_khong_chan_som_bang_python(self):
        src = inspect.getsource(KT.KeToanNghiemThuK2)
        self.assertNotIn("can_cu_hien_hanh", src)  # hiện hành do SQL quyết dưới khóa; Python không tự suy/chặn (giữ mã lỗi replay/nguồn cũ)
        self.assertNotIn("chung_tu", src)


# ================================================================================================== khung biên viết tay (nhãn: KHÔNG phải producer)
def _ctx(pb=11):
    return {"phap_nhan_id": _id(1), "du_an_id": _id(2), "hop_dong_id": _id(3), "dot_id": _id(4), "kt_pending_id": _id(5), "phong_bi_id": _id(pb),
            "seal_id": _id(21), "version_id": _id(31), "ket_luan_id": _id(41), "pdf_id": _id(51), "phong_bi_sha256": "a" * 64,
            "graph_sha256": "b" * 64, "pdf_sha256": "c" * 64}


def _nd():
    return {"tien_te": "VND", "gia_tri_nt": "1000000", "so_xin_thanh_toan": "900000", "tam_ung": "0", "thu_hoi": "0", "giu_lai": "50000",
            "dong": [], "pdf": {"id": _id(51), "raw_sha256": "c" * 64, "byte_length": 2048}}


def _kt_row():
    r = {"kt_revision_id": _id(101), "revision": 1, "loai": "NHAP", "nhap_id": None, "phong_bi_id": _id(11), "tien_te": "VND",
         "gia_tri_nt_xac_nhan": "1000000", "tam_ung_xac_nhan": "0", "thu_hoi_xac_nhan": "0", "giu_lai_xac_nhan": "50000",
         "co_so_gia_tri": "TRUOC_VAT", "vat_trang_thai": "KHONG_AP_DUNG", "vat_can_cu_tep_id": None, "vat_can_cu_sha256": None,
         "vat_trich_dan": None, "ly_do": "Đợt không phát sinh hóa đơn GTGT"}
    r["thieu"] = KT.thieu(r, _nd())
    return r


def _ct(hien: bool, ly_do):
    c, k = _ctx(), _kt_row()
    return {"context": c, "can_cu_hien_hanh": hien, "phong_bi_moi_nhat": True, "ly_do_hold": ly_do, "nguon": _nd(),
            "pdf": {"id": _id(51), "ten": "ho-so.pdf", "media_type": "application/pdf", "raw_sha256": "c" * 64, "byte_length": 2048},
            "tep_can_cu": [], "kt": k, "da_xac_nhan": False,
            "lich_su_phong_bi": [{"context": c, "thu_tu": 1, "truoc_id": None, "phien_ban_so": 1, "can_cu_hien_hanh": hien}],
            "lich_su_kt": [{"context": c, "kt": k, "nguon": {x: v for x, v in _nd().items() if x != "dong"}}]}


class DtoHold(unittest.TestCase):
    """KHUNG BIÊN VIẾT TAY theo hình dạng m4.kt_chi_tiet — chứng minh builder DTO thật xử lý cờ HOLD; KHÔNG phải bằng chứng producer/PG."""

    def test_baseline_hien_hanh_van_mo_lenh(self):
        x = KT.xem_dto(_ct(True, None))
        self.assertEqual(x["kt"]["trang_thai"], KT.TT_CHO_XAC_NHAN)
        self.assertEqual(x["quyen"], {"xem": True, "luu": True, "xac_nhan": True, "tai_pdf": True})

    def test_do_thi_hold_dong_lenh_giu_lich_su(self):
        x = KT.xem_dto(_ct(False, SK.LY_DO_DO_THI))
        self.assertEqual((x["can_cu_hien_hanh"], x["quyen"]), (False, {"xem": True, "luu": False, "xac_nhan": False, "tai_pdf": True}))
        self.assertEqual((x["kt"]["revision"], x["context"]["pdf_sha256"], x["nguon"]["pdf"]["raw_sha256"]), (1, "c" * 64, "c" * 64))
        self.assertEqual([r["can_cu_hien_hanh"] for r in x["lich_su"]["phong_bi"]], [False])
        self.assertEqual([r["kt"]["revision"] for r in x["lich_su"]["kt"]], [1])
        self.assertNotIn("ly_do_hold", x)  # hợp đồng công khai 9 khóa không đổi
        self.assertEqual(tuple(x), KT.XEM_KEYS)

    def test_dong_danh_sach(self):
        dong = {"kt_pending_id": _id(5), "dot_id": _id(4), "phong_bi_id": _id(11), "phong_bi_sha256": "a" * 64, "toan_ven": True,
                "kt": {"revision": 1, "loai": "NHAP", "thieu": []}}
        self.assertEqual(KT.dong_ds_dto({**dong, "hien_hanh": False})["trang_thai"], KT.TT_CAN_KIEM_LAI)
        self.assertEqual(KT.dong_ds_dto({**dong, "hien_hanh": True})["trang_thai"], KT.TT_CHO_XAC_NHAN)


if __name__ == "__main__":
    unittest.main()
