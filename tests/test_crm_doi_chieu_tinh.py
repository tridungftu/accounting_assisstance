"""CRM G5-B — kiểm thuần (không CSDL/engine/mạng) trên CHÍNH module ``k2/crm_doi_chieu.py`` + hằng ``CRM_G5_SQL`` (CODE_ONLY: coder viết,
CHƯA CHẠY — WRITTEN_NOT_RUN).

Tầng:
  1. Hàm thuần: bảng lịch typed (0 ≠ null, thứ tự dòng, tiền tệ từng dòng), expected từ revision ĐÃ KÝ, binding, body E5 đúng 13 khóa + SHA
     canonical, kiểm g5 (KHOP/LECH/CHUA, mức, locator, phủ), kiểm envelope niêm phong (raw/yêu cầu/implementation).
  2. Service với kết nối/khóa/client GIẢ: lệnh người dùng chỉ gửi đích + ngữ cảnh + khóa; người chạy không mượn danh tính khác; chuỗi
     A (dưới khóa) → B (engine NGOÀI khóa) → C (dưới khóa); E5 chưa ghép/chưa sẵn sàng → CHO_CAU_HINH; mất ACK → CHUA_RO giữ request_id.
  3. Hợp đồng tĩnh của ``CRM_G5_SQL`` (chuỗi hằng — không chạy SQL): không đụng registry/ordinal, trigger bắt buộc trong giao dịch ký,
     nhánh SYNTHETIC và G7 giữ NGUYÊN VĂN so với G6A.

NHÃN: mọi DTO/đăng ký/client/envelope ở đây là DỮ LIỆU GIẢ DỰNG CHO KIỂM THỬ (DEMO) — KHÔNG phải bằng chứng vận hành, không phải producer E5
thật, không phải nghiệm thu. Producer E5 thật / đăng ký vận hành / PG native / Word G3 / GUI vẫn OPEN tới khi Root kiểm độc lập.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import tempfile
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path

from kho_tri_thuc.ha_tang.primitives import DataError, canonical_json, sha256
from kho_tri_thuc.k2 import crm_doi_chieu as DC
from kho_tri_thuc.k2.crm_mau import _h
from kho_tri_thuc.k2.sql_crm_doi_chieu import _G5_BANG_MOI, CRM_G5_SQL
from kho_tri_thuc.k2.sql_crm_kiem_hd import CRM_G6A_SQL
from kho_tri_thuc.nguon.trich_chung_6 import ChuaRo, LoiNguon

ROOT = Path(__file__).resolve().parents[1]
SQL_TXT = "\n".join(CRM_G5_SQL)
SQL_G6A = "\n".join(CRM_G6A_SQL)

KY = "11111111-1111-4111-8111-111111111111"
VIEC = "22222222-2222-4222-8222-222222222222"
DK = "33333333-3333-4333-8333-333333333333"
CTX = "c" * 64
IMPL = "e" * 64
RAW_PDF = b"%PDF-1.7\n% DEMO BAN KY G5-B (fixture kiem thu, khong phai hop dong that)\n%%EOF\n"
G3_PDF_SHA = "a" * 64  # vai PDF G3 riêng (expected.lineage) — khác PDF bản ký

DANH_MUC = [{"khoa": "gia_tri_hop_dong", "kieu": "tien"}, {"khoa": "so_hop_dong", "kieu": "text"}, {"khoa": "ngay_ky", "kieu": "ngay"},
            {"khoa": "dien_tich", "kieu": "so"}, {"khoa": "phu_luc", "kieu": "bang"}]
MAPPING = [{"ma": "GIA_TRI_HD", "crm_truong": "gia_tri_hop_dong", "muc": 3}, {"ma": "SO_HD", "crm_truong": "so_hop_dong", "muc": 1},
           {"ma": "NGAY_KY", "crm_truong": "ngay_ky", "muc": 2}, {"ma": "DIEN_TICH", "crm_truong": "dien_tich", "muc": 0},
           {"ma": "LICH_TT", "crm_truong": "crm.lich", "muc": 2}]
LICH = [{"dong_id": "d1", "lan": "1", "loai": "PERCENT", "ty_le": "40", "so_tien": "0", "tien_te": "VND", "moc_loai": "SU_KIEN",
         "moc_su_kien": "KY_HD"},
        {"dong_id": "d2", "lan": "2", "loai": "AMOUNT", "so_tien": "600000000", "tien_te": "USD", "moc_loai": "NGAY", "moc_ngay": "2026-12-31"}]
# r.du_lieu của revision ĐÃ KÝ (soan_rev_id ghim ở bản ký) — bản nháp hiện hành khác (DU_LIEU_NHAP) không được dùng
DU_LIEU_KY = {"gia_tri_truong": {"gia_tri_hop_dong": {"so_tien": "1000", "tien_te": "VND"}, "so_hop_dong": "HĐ-DEMO-G5-01", "ngay_ky": "2026-10-20",
                                 "dien_tich": "0"},
              "bao_gia": {"lich": LICH}}
DU_LIEU_NHAP = {"gia_tri_truong": {"gia_tri_hop_dong": {"so_tien": "100", "tien_te": "VND"}, "so_hop_dong": "HĐ-NHAP", "ngay_ky": "2026-10-21",
                                   "dien_tich": None},
                "bao_gia": {"lich": LICH[:1]}}


def _ky_row(**sua):
    k = {"ky_id": KY, "hop_dong_id": "44444444-4444-4444-8444-444444444444", "soan_id": "55555555-5555-4555-8555-555555555555",
         "soan_rev_id": "66666666-6666-4666-8666-666666666666", "xuat_id": "77777777-7777-4777-8777-777777777777",
         "mau_phien_ban_id": "88888888-8888-4888-8888-888888888888", "anh_xa_id": "99999999-9999-4999-8999-999999999999", "revision": 2,
         "g3_input_sha256": "1" * 64, "g3_docx_sha256": "2" * 64, "g3_pdf_sha256": G3_PDF_SHA, "ban_do_sha256": "3" * 64,
         "danh_muc_ref": "DM_DEMO_G5", "danh_muc_rev": 1, "danh_muc_digest": "4" * 64, "profile_sha256": "5" * 64, "du_lieu_sha256": "6" * 64,
         "ky_pdf_sha256": sha256(RAW_PDF), "ky_pdf_len": len(RAW_PDF), "ten_tep": "ban-da-ky.pdf"}
    k.update(sua)
    return k


DANG_KY = {"id": DK, "nhan": "DEMO_KIEM_THU", "loai_hop_dong": "XD_DEMO", "catalog_id": "catalog.demo.g5", "catalog_sha256": "7" * 64,
           "implementation_sha256": IMPL, "capability": "doi_chieu_ban_ky", "mapping": MAPPING}


def _loi(test, ma, fn, *a, **kw):
    with test.assertRaises(DataError) as cm:
        fn(*a, **kw)
    test.assertEqual(cm.exception.code, ma, str(cm.exception))
    return cm.exception


def _body(ky=None, du_lieu=None, request_id=None):
    ky = ky or _ky_row()
    exp = DC.dung_expected(ky, du_lieu or DU_LIEU_KY, DANH_MUC, MAPPING)
    bd = DC.dung_binding(ky, DANG_KY)
    return DC.body_e5(ky, DANG_KY, request_id or f"crm-g5-{VIEC}-1", exp, bd)


def _y(body, ky=None):
    ky = ky or _ky_row()
    return {"expected": body["expected"], "binding": body["catalog_binding"], "expected_sha256": body["expected_sha256"],
            "binding_sha256": body["catalog_binding_sha256"], "ky_pdf_sha256": ky["ky_pdf_sha256"], "g3_pdf_sha256": ky["g3_pdf_sha256"]}


def _g5(y, trang_thai="KHOP", coverage=None, lech=(), thieu=()):
    ma = [t["ma"] for t in y["expected"]["tham_so"]]
    return {"kieu": DC.KIEU_G5, "signed_pdf_sha256": y["ky_pdf_sha256"], "source_sha256": y["ky_pdf_sha256"], "expected_sha256": y["expected_sha256"],
            "catalog_binding_sha256": y["binding_sha256"], "g3_pdf_sha256": y["g3_pdf_sha256"],
            "coverage": list(ma if coverage is None else coverage), "trang_thai": trang_thai, "lech": [dict(e) for e in lech], "thieu": list(thieu)}


def _lech(y, ma, ban_ky, *, trich="Điều 3: giá trị hợp đồng 100 VND", vi_tri=None, **sua):
    t = {x["ma"]: x for x in y["expected"]["tham_so"]}[ma]
    muc = {m["ma"]: m["muc"] for m in y["binding"]["mapping"]}[ma]
    e = {"ma": ma, "muc": muc, "kieu": t["kieu"], "gia_tri_ky_vong": t["gia_tri"], "gia_tri_ban_ky": ban_ky, "trich_dan": trich,
         "vi_tri_do_duoc": vi_tri if vi_tri is not None else {"trang": 1, "dong": 12}}
    e.update(sua)
    return e


def _env(body, g5, impl=IMPL, luot="luot-demo-1", **sua):
    kq = {"trang_thai": "XONG", "g5": g5}
    raw = canonical_json(kq).encode("utf-8")
    e = {"luot": luot, "raw_ket_qua": raw, "raw_sha256": sha256(raw), "ket_qua": kq, "common": {"implementation_sha256": impl},
         "yeu_cau": body, "g5": g5}
    e.update(sua)
    return e


# ---------------------------------------------------------------------------------------------------------------- 1. hàm thuần
class BangLich(unittest.TestCase):
    def test_khong_khac_null_va_thu_tu(self):
        b = DC.bang_lich([{"lan": "1", "so_tien": "0"}, {"lan": "2"}, {"lan": "3", "so_tien": 0}])
        self.assertEqual(b["cot"], list(DC.COT_LICH))
        i = DC.COT_LICH.index("so_tien")
        self.assertEqual([d[i] for d in b["dong"]], ["0", None, 0])  # "0" và 0 giữ nguyên, thiếu = None — không mặc định 0
        self.assertEqual([d[DC.COT_LICH.index("lan")] for d in b["dong"]], ["1", "2", "3"])
        self.assertEqual(DC.bang_lich(None), {"cot": list(DC.COT_LICH), "dong": []})

    def test_tien_te_tung_dong_khong_quy_doi(self):
        b = DC.bang_lich(LICH)
        i, j = DC.COT_LICH.index("tien_te"), DC.COT_LICH.index("ty_le")
        self.assertEqual([d[i] for d in b["dong"]], ["VND", "USD"])
        self.assertEqual([d[j] for d in b["dong"]], ["40", None])  # không suy % từ số tiền

    def test_o_sai_kieu(self):
        for x in (1.5, True, {"a": 1}, ["x"]):
            _loi(self, "CRM_G5_EXPECTED_SAI", DC.bang_lich, [{"lan": "1", "so_tien": x}])
        _loi(self, "CRM_G5_EXPECTED_SAI", DC.bang_lich, {"lan": "1"})
        _loi(self, "CRM_G5_EXPECTED_SAI", DC.bang_lich, ["dong"])


class Expected(unittest.TestCase):
    def test_tu_revision_da_ky(self):
        ky = _ky_row()
        e = DC.dung_expected(ky, DU_LIEU_KY, DANH_MUC, MAPPING)
        self.assertEqual(set(e), {"kieu", "lineage", "tham_so"})
        self.assertEqual(e["kieu"], "CRM_G5_EXPECTED_V1")
        self.assertEqual(list(e["lineage"]), list(DC.LINEAGE_KHOA))
        self.assertEqual(e["lineage"]["soan_rev_id"], ky["soan_rev_id"])
        self.assertNotIn("ky_pdf_sha256", e["lineage"])  # PDF bản ký không nằm trong lineage expected (vai riêng)
        self.assertEqual([t["ma"] for t in e["tham_so"]], [m["ma"] for m in MAPPING])  # đúng thứ tự mapping đăng ký
        ts = {t["ma"]: t for t in e["tham_so"]}
        self.assertEqual(ts["GIA_TRI_HD"], {"ma": "GIA_TRI_HD", "kieu": "tien", "gia_tri": {"so_tien": "1000", "tien_te": "VND"}})
        self.assertEqual(ts["DIEN_TICH"]["gia_tri"], "0")
        self.assertEqual((ts["SO_HD"]["kieu"], ts["NGAY_KY"]["gia_tri"]), ("text", "2026-10-20"))
        self.assertEqual(ts["LICH_TT"], {"ma": "LICH_TT", "kieu": "bang", "gia_tri": DC.bang_lich(LICH)})

    def test_ban_nhap_khac_ban_ky(self):
        """Expected chỉ phụ thuộc du_lieu ĐÃ KÝ được truyền vào (do SQL lấy theo k.soan_rev_id) — bản nháp cho expected KHÁC."""
        ky = _ky_row()
        e_ky = DC.dung_expected(ky, DU_LIEU_KY, DANH_MUC, MAPPING)
        e_nhap = DC.dung_expected(ky, DU_LIEU_NHAP, DANH_MUC, MAPPING)
        self.assertNotEqual(DC.sha_obj(e_ky), DC.sha_obj(e_nhap))
        ts = {t["ma"]: t["gia_tri"] for t in e_nhap["tham_so"]}
        self.assertEqual((ts["GIA_TRI_HD"]["so_tien"], ts["DIEN_TICH"]), ("100", None))  # 100 ≠ 1000; null ≠ "0"

    def test_100_khac_1000_va_tien_te(self):
        ky = _ky_row()
        a = DC.dung_expected(ky, {"gia_tri_truong": {"gia_tri_hop_dong": {"so_tien": "100", "tien_te": "VND"}}}, DANH_MUC, MAPPING[:1])
        b = DC.dung_expected(ky, {"gia_tri_truong": {"gia_tri_hop_dong": {"so_tien": "1000", "tien_te": "VND"}}}, DANH_MUC, MAPPING[:1])
        c = DC.dung_expected(ky, {"gia_tri_truong": {"gia_tri_hop_dong": {"so_tien": "1000", "tien_te": "USD"}}}, DANH_MUC, MAPPING[:1])
        self.assertEqual(len({DC.sha_obj(a), DC.sha_obj(b), DC.sha_obj(c)}), 3)
        _loi(self, "CRM_GK_YEU_CAU_SAI", DC.dung_expected, ky, {"gia_tri_truong": {"gia_tri_hop_dong": {"so_tien": "1000"}}}, DANH_MUC, MAPPING[:1])
        _loi(self, "CRM_GK_SO_SAI", DC.dung_expected, ky, {"gia_tri_truong": {"gia_tri_hop_dong": {"so_tien": "1000.5", "tien_te": "VND"}}},
             DANH_MUC, MAPPING[:1])  # không làm tròn scale tiền tệ

    def test_mapping_sai(self):
        ky = _ky_row()
        _loi(self, "CRM_G5_MAPPING_SAI", DC.dung_expected, ky, DU_LIEU_KY, DANH_MUC, [{"ma": "X", "crm_truong": "khong_co", "muc": 1}])
        _loi(self, "CRM_G5_MAPPING_SAI", DC.dung_expected, ky, DU_LIEU_KY, DANH_MUC, [{"ma": "X", "crm_truong": "phu_luc", "muc": 1}])
        _loi(self, "CRM_G5_EXPECTED_SAI", DC.dung_expected, ky, DU_LIEU_KY, DANH_MUC, [])
        _loi(self, "CRM_G5_EXPECTED_SAI", DC.dung_expected, ky, None, DANH_MUC, MAPPING)


class BodyE5(unittest.TestCase):
    def test_13_khoa_va_vai_pdf(self):
        b = _body()
        self.assertEqual(set(b), DC.E5_KHOA)
        self.assertEqual(len(b), 13)
        self.assertEqual((b["contract"], b["mode"]), ("trich-tham-so-common/v1", "doi_chieu_ban_ky"))
        self.assertEqual(b["source_sha256"], sha256(RAW_PDF))
        self.assertEqual(b["signed_pdf_sha256"], b["source_sha256"])
        self.assertEqual(b["expected"]["lineage"]["g3_pdf_sha256"], G3_PDF_SHA)
        self.assertNotEqual(b["source_sha256"], G3_PDF_SHA)
        self.assertEqual(b["tham_so"], [m["ma"] for m in MAPPING])
        self.assertEqual(b["catalog_binding"]["kieu"], "CRM_G5_CATALOG_BINDING_V1")
        self.assertEqual(b["catalog_binding"]["mapping"], MAPPING)
        self.assertEqual((b["catalog_binding"]["danh_muc_ref"], b["catalog_binding"]["danh_muc_rev"]), ("DM_DEMO_G5", 1))

    def test_sha_canonical(self):
        self.assertEqual(DC.sha_obj({"b": 1, "a": "Đ"}), hashlib.sha256('{"a":"Đ","b":1}'.encode("utf-8")).hexdigest())
        b = _body()
        self.assertEqual(b["expected_sha256"], DC.sha_obj(b["expected"]))
        self.assertEqual(b["catalog_binding_sha256"], DC.sha_obj(b["catalog_binding"]))
        self.assertEqual(DC.sha_body(b), DC.sha_obj(b))
        self.assertNotEqual(DC.sha_body(_body(request_id=f"crm-g5-{VIEC}-2")), DC.sha_body(b))  # thế hệ khác → body khác

    def test_body_thieu_thua_khoa(self):
        b = _body()
        _loi(self, "CRM_G5_Y_DINH_SAI", DC.sha_body, {**b, "trusted": True})
        b2 = dict(b)
        b2.pop("catalog_binding_sha256")
        _loi(self, "CRM_G5_Y_DINH_SAI", DC.sha_body, b2)


class KiemG5(unittest.TestCase):
    def setUp(self):
        self.b = _body()
        self.y = _y(self.b)

    def test_khop_du(self):
        g = _g5(self.y)
        self.assertIs(DC.kiem_g5(g, self.y), g)

    def test_lech_co_trich_dan_va_vi_tri(self):
        g = _g5(self.y, "LECH", lech=[_lech(self.y, "GIA_TRI_HD", {"so_tien": "100", "tien_te": "VND"})])
        self.assertIs(DC.kiem_g5(g, self.y), g)
        g = _g5(self.y, "LECH", lech=[_lech(self.y, "LICH_TT", {"cot": list(DC.COT_LICH), "dong": []}, trich="Điều 5 bảng thanh toán dòng 2",
                                             vi_tri="trang 2/bảng 1/dòng 2")])
        self.assertIs(DC.kiem_g5(g, self.y), g)

    def test_chua_doi_chieu_duoc_giu_lech_mot_phan(self):
        g = _g5(self.y, "CHUA_DOI_CHIEU_DUOC", coverage=["GIA_TRI_HD"], thieu=["LICH_TT"],
                lech=[_lech(self.y, "GIA_TRI_HD", {"so_tien": "100", "tien_te": "VND"}, trich="", vi_tri="")])
        self.assertIs(DC.kiem_g5(g, self.y), g)

    def test_khop_gia_bi_tu_choi(self):
        y = self.y
        for g in (_g5(y, coverage=["GIA_TRI_HD"]),  # thiếu phủ
                  _g5(y, coverage=["GIA_TRI_HD", "SO_HD", "NGAY_KY", "DIEN_TICH"], thieu=["LICH_TT"]),
                  _g5(y, lech=[_lech(y, "SO_HD", "HĐ-KHAC")]),  # KHOP kèm lệch
                  _g5(y, "LECH"),  # LECH 0 lệch
                  _g5(y, "LECH", coverage=["GIA_TRI_HD"], lech=[_lech(y, "GIA_TRI_HD", {"so_tien": "100", "tien_te": "VND"})]),
                  _g5(y, "MATCH")):
            _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_g5, g, y)

    def test_lech_sai(self):
        y = self.y
        ban = {"so_tien": "100", "tien_te": "VND"}
        for e in (_lech(y, "GIA_TRI_HD", ban, trich=""), _lech(y, "GIA_TRI_HD", ban, trich="   "), _lech(y, "GIA_TRI_HD", ban, vi_tri=""),
                  _lech(y, "GIA_TRI_HD", ban, vi_tri={}), _lech(y, "GIA_TRI_HD", ban, vi_tri=[]), _lech(y, "GIA_TRI_HD", ban, vi_tri=7),
                  _lech(y, "GIA_TRI_HD", ban, muc=2),  # mức khác catalog đã ghim (3) — không mặc định 2
                  _lech(y, "GIA_TRI_HD", ban, muc=True),
                  _lech(y, "GIA_TRI_HD", ban, gia_tri_ky_vong={"so_tien": "100", "tien_te": "VND"}),  # 100 ≠ 1000 kỳ vọng
                  _lech(y, "GIA_TRI_HD", ban, kieu="so"),
                  {**_lech(y, "GIA_TRI_HD", ban), "khac": 1}):
            _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_g5, _g5(y, "LECH", lech=[e]), y)
        e = _lech(y, "GIA_TRI_HD", ban)
        _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_g5, _g5(y, "LECH", lech=[e, e]), y)  # trùng mã

    def test_ma_phu_va_sha(self):
        y = self.y
        for g in (_g5(y, coverage=["GIA_TRI_HD", "GIA_TRI_HD"]), _g5(y, coverage=["KHONG_YEU_CAU"]),
                  _g5(y, "CHUA_DOI_CHIEU_DUOC", coverage=["SO_HD"], thieu=["SO_HD"]), _g5(y, coverage="GIA_TRI_HD")):
            _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_g5, g, y)
        for k, v in (("signed_pdf_sha256", G3_PDF_SHA), ("source_sha256", "0" * 64), ("expected_sha256", "0" * 64),
                     ("catalog_binding_sha256", "0" * 64), ("g3_pdf_sha256", sha256(RAW_PDF)), ("kieu", "CRM_G5_COMPARE_RESULT_V2")):
            _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_g5, {**_g5(y), k: v}, y)
        _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_g5, {**_g5(y), "trusted": True}, y)
        _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_g5, [], y)


class KiemEnvelope(unittest.TestCase):
    def setUp(self):
        self.b = _body()
        self.y = _y(self.b)

    def test_hop_le(self):
        g = _g5(self.y)
        env = _env(self.b, g)
        g2, raw, h, luot = DC.kiem_envelope(env, self.b, self.y, IMPL)
        self.assertEqual((g2, raw, h, luot), (g, env["raw_ket_qua"], sha256(env["raw_ket_qua"]), "luot-demo-1"))

    def test_gia_mao(self):
        g = _g5(self.y)
        env = _env(self.b, g)
        for sua in ({"raw_sha256": "0" * 64}, {"raw_ket_qua": env["raw_ket_qua"] + b" "}, {"raw_ket_qua": b""}, {"raw_ket_qua": "chuoi"},
                    {"ket_qua": {"trang_thai": "XONG", "g5": {**g, "trang_thai": "LECH"}}},
                    {"g5": {**g, "coverage": []}},  # g5 ngoài khác g5 trong raw đã niêm phong
                    {"yeu_cau": {**self.b, "request_id": f"crm-g5-{VIEC}-9"}},  # body trôi
                    {"yeu_cau": {**self.b, "expected_sha256": "0" * 64}},
                    {"luot": "../x"}, {"luot": ""}):
            _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_envelope, {**env, **sua}, self.b, self.y, IMPL)
        _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_envelope, {**env, "trusted": True}, self.b, self.y, IMPL)
        raw = b"khong-phai-json"
        _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_envelope, {**env, "raw_ket_qua": raw, "raw_sha256": sha256(raw)}, self.b, self.y, IMPL)

    def test_implementation_khac_la_chua_san_sang(self):
        env = _env(self.b, _g5(self.y), impl="f" * 64)
        _loi(self, "E5_IMPLEMENTATION_KHAC", DC.kiem_envelope, env, self.b, self.y, IMPL)
        self.assertIn("E5_IMPLEMENTATION_KHAC", DC.MA_CHUA_SAN_SANG)
        _loi(self, "E5_IMPLEMENTATION_KHAC", DC.kiem_envelope, {**env, "common": None}, self.b, self.y, IMPL)

    # FIX01-A (bổ sung): raw niêm phong là nguồn duy nhất của g5 — không suy từ envelope ngoài
    def _niem(self, kq, g5_ngoai):
        raw = canonical_json(kq).encode("utf-8")  # raw hợp lệ, hash khớp
        return {"luot": "luot-demo-1", "raw_ket_qua": raw, "raw_sha256": sha256(raw), "ket_qua": kq, "common": {"implementation_sha256": IMPL},
                "yeu_cau": self.b, "g5": g5_ngoai}

    def test_raw_thieu_g5_bi_tu_choi(self):
        g = _g5(self.y)  # g5 ngoài hợp lệ KHOP (đủ phủ, 0 lệch)
        self.assertEqual(DC.kiem_g5(g, self.y)["trang_thai"], "KHOP")
        env = self._niem({"trang_thai": "XONG"}, g)  # raw + ket_qua nhất quán, SHA khớp, nhưng KHÔNG có g5
        e = _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_envelope, env, self.b, self.y, IMPL)
        self.assertIn("thiếu g5", str(e))
        for kq in ([{"g5": g}], "chuoi", 1, None):  # raw JSON không phải object
            _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_envelope, self._niem(kq, g), self.b, self.y, IMPL)

    def test_g5_trong_raw_la_g5_duoc_kiem(self):
        g = _g5(self.y)
        g_raw = {**g, "lech": [], "trang_thai": "CHUA_DOI_CHIEU_DUOC", "coverage": [], "thieu": [t["ma"] for t in self.y["expected"]["tham_so"]]}
        # ket_qua khớp raw nhưng g5 ngoài (KHOP) khác g5 trong raw (CHUA) → từ chối; không lấy KHOP ngoài
        _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_envelope, self._niem({"trang_thai": "XONG", "g5": g_raw}, g), self.b, self.y, IMPL)
        g2, *_ = DC.kiem_envelope(self._niem({"trang_thai": "XONG", "g5": g_raw}, g_raw), self.b, self.y, IMPL)
        self.assertEqual(g2["trang_thai"], "CHUA_DOI_CHIEU_DUOC")  # đúng giá trị niêm phong, không mặc định KHOP

    def test_so_sanh_canonical_1_khac_1_0_va_true(self):
        g = _g5(self.y, "LECH", lech=[_lech(self.y, "GIA_TRI_HD", {"so_tien": "100", "tien_te": "VND"})])
        g_raw = json.loads(canonical_json(g))
        g_raw["lech"][0]["vi_tri_do_duoc"] = {"trang": 1.0, "dong": 12}  # raw: 1.0; ngoài: 1 (Python == coi bằng nhau)
        kq = {"trang_thai": "XONG", "g5": g_raw}
        self.assertEqual(g_raw, g)  # Python == không phân biệt 1 / 1.0 — đúng lỗ hổng mà so canonical phải chặn
        _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_envelope, self._niem(kq, g), self.b, self.y, IMPL)
        g_bool = json.loads(canonical_json(g))
        g_bool["lech"][0]["vi_tri_do_duoc"] = {"trang": True, "dong": 12}
        _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_envelope, self._niem({"trang_thai": "XONG", "g5": g}, g_bool), self.b, self.y, IMPL)
        raw = b'{"g5": NaN}'
        _loi(self, "CRM_G5_KET_QUA_SAI", DC.kiem_envelope, {**self._niem({"g5": None}, g), "raw_ket_qua": raw, "raw_sha256": sha256(raw)},
             self.b, self.y, IMPL)

    def test_duong_duong_tinh_qua_giao_dien_e5(self):
        e5 = _E5()  # client E5 GIẢ: raw = canonical {"trang_thai","g5"} — giao diện thật `.doi_chieu_ban_ky` (DEMO, không phải producer)
        dv, _ = _dv(client=e5)
        b = _body()
        loai, (g5, raw, h, _) = dv.goi_engine({**_p(), "body": b, "body_sha256": DC.sha_body(b), "expected": b["expected"],
                                              "binding": b["catalog_binding"]})
        self.assertEqual((loai, g5["trang_thai"], h), ("KET_QUA", "KHOP", sha256(raw)))
        self.assertEqual(canonical_json(json.loads(raw.decode("utf-8"))["g5"]), canonical_json(g5))


# ---------------------------------------------------------------------------------------------------------------- 2. service với giả
class _Cur:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class _Conn:
    """Kết nối giả: trả theo tên hàm master.crm_g5_*; ghi lại (hàm, tham số, danh tính giao dịch)."""

    def __init__(self, tra=None):
        self.tra = {k: list(v) for k, v in (tra or {}).items()}
        self.goi = []
        self.dt = None

    def execute(self, sql, params=None):
        ham = re.search(r"master\.(crm_g5_\w+)\(", sql).group(1)
        self.goi.append((ham, params, self.dt))
        x = self.tra[ham].pop(0)
        if isinstance(x, Exception):
            raise x
        return _Cur({"r": x})

    @contextmanager
    def transaction(self):
        yield


class _Mau:
    def __init__(self, conn, nguoi=("MO_PHONG_KT_A",)):
        self.conn, self.nguoi = conn, set(nguoi)

    def danh_tinh(self, dang_nhap):
        if dang_nhap not in self.nguoi:
            raise DataError("DANH_TINH", "không nạp được danh tính")
        return {"id": "00000000-0000-4000-8000-000000000001", "dang_nhap": dang_nhap}

    @contextmanager
    def _tx(self, dt, *, rr=False):
        self.conn.dt = dt["dang_nhap"]
        try:
            yield self.conn
        finally:
            self.conn.dt = None

    def _c(self):
        self.conn.dt = None  # kết nối chủ bảng KHÔNG danh tính (SQL ghi CHO_CAU_HINH) — không mượn người khác
        return self.conn


class _Kiem:
    def __init__(self, conn, nguoi=("MO_PHONG_KT_A",)):
        tam = Path(tempfile.mkdtemp(prefix="ktt_g5b_tinh_"))  # giữ lại (không xóa)
        self.mau = _Mau(conn, nguoi)
        self.ky = type("Ky", (), {})()
        self.ky.mau = self.mau
        self.ky.kho_ky = tam / "ky"
        self.ky.kho_ky.mkdir()
        self.ky.gk = type("GK", (), {"kho": tam / "giao-ket"})()
        (self.ky.kho_ky / sha256(RAW_PDF)).write_bytes(RAW_PDF)


class _Khoa:
    """mutation lock giả: ghi lại sự kiện để chứng minh engine chạy NGOÀI khóa."""

    def __init__(self):
        self.giu, self.su_kien = False, []

    def __enter__(self):
        assert not self.giu, "khóa không tái nhập"
        self.giu = True
        self.su_kien.append("vao")

    def __exit__(self, *a):
        self.giu = False
        self.su_kien.append("ra")


class _E5:
    """Client E5 GIẢ (DEMO, không phải producer thật): kiểm khóa không bị giữ khi gọi; trả envelope dựng từ đúng body."""
    san_sang = True

    def __init__(self, khoa=None, tao=None, loi=None):
        self.khoa, self.tao, self.loi, self.goi = khoa, tao, loi, []

    def doi_chieu_ban_ky(self, raw, *, ten_tep, loai_hop_dong, tham_so, request_id, expected, expected_sha256, catalog_binding,
                         catalog_binding_sha256):
        self.goi.append({"raw": raw, "ten_tep": ten_tep, "request_id": request_id, "tham_so": tham_so, "expected_sha256": expected_sha256,
                         "khoa_dang_giu": bool(self.khoa and self.khoa.giu)})
        if self.loi is not None:
            raise self.loi
        body = {"contract": DC.CONTRACT, "mode": DC.MODE_E5, "loai_hop_dong": loai_hop_dong, "catalog_id": catalog_binding["catalog_id"],
                "catalog_sha256": catalog_binding["catalog_sha256"], "source_sha256": sha256(raw), "request_id": request_id, "tham_so": tham_so,
                "signed_pdf_sha256": sha256(raw), "expected": expected, "expected_sha256": expected_sha256, "catalog_binding": catalog_binding,
                "catalog_binding_sha256": catalog_binding_sha256}
        y = {"expected": expected, "binding": catalog_binding, "expected_sha256": expected_sha256, "binding_sha256": catalog_binding_sha256,
             "ky_pdf_sha256": sha256(raw), "g3_pdf_sha256": expected["lineage"]["g3_pdf_sha256"]}
        return _env(body, self.tao(y) if self.tao else _g5(y))


class _Trich6Goc:
    """Hình dạng client baseline (chỉ .trich, chưa ghép E5-A) — không có doi_chieu_ban_ky."""
    san_sang = True

    def trich(self, *a, **kw):  # pragma: no cover - không được gọi
        raise AssertionError("không được rơi về .trich legacy")


def _p(**sua):
    p = {"nhan": True, "viec_id": VIEC, "loai": "THU_CONG", "the_he": 1, "request_id": f"crm-g5-{VIEC}-1", "tac_nhan_loai": "NGUOI_DUNG",
         "tac_nhan": "MO_PHONG_KT_A", "ky": _ky_row(), "du_lieu": DU_LIEU_KY, "danh_muc": DANH_MUC, "dang_ky": DANG_KY, "y_dinh": None,
         "nguoi_chay": "MO_PHONG_KT_A"}
    p.update(sua)
    return p


def _dv(tra=None, client=None, nguoi=("MO_PHONG_KT_A",)):
    c = _Conn(tra)
    dv = DC.CrmDoiChieuK2(_Kiem(c, nguoi), (lambda goc: client) if client is not None else None)
    return dv, c


class LenhNguoiDung(unittest.TestCase):
    def test_chay_chi_dich_ngu_canh_khoa(self):
        ack = {"kieu": "CRM_G5_ACK_V1", "ky_id": KY, "context_sha256": CTX, "job_id": VIEC, "request_id": f"crm-g5-{VIEC}-1", "state": "CHO",
               "current_result_id": None, "tao_moi": True}
        dv, c = _dv({"crm_g5_chay": [{"lap_lai": False, "ket_qua": ack}]})
        r = dv.chay("MO_PHONG_KT_A", ky_id=KY.upper(), expected_context_sha256=CTX, khoa="g5-k1")
        self.assertEqual(r, {**ack, "replay": False})
        self.assertEqual(set(r), {"kieu", "ky_id", "context_sha256", "job_id", "request_id", "state", "current_result_id", "tao_moi", "replay"})
        (ham, params, dt), = c.goi
        self.assertEqual((ham, dt), ("crm_g5_chay", "MO_PHONG_KT_A"))
        self.assertEqual(params, ("g5-k1", _h("CRM_G5_CHAY", {"ky_id": KY, "expected_context_sha256": CTX}), KY, CTX))

    def test_doi_soat_replay_va_digest(self):
        ack = {"kieu": "CRM_G5_ACK_V1", "ky_id": KY, "context_sha256": CTX, "job_id": VIEC, "request_id": f"crm-g5-{VIEC}-1", "state": "CHO",
               "current_result_id": None, "tao_moi": False}
        dv, c = _dv({"crm_g5_doi_soat": [{"lap_lai": True, "ket_qua": ack}]})
        r = dv.doi_soat("MO_PHONG_KT_A", ky_id=KY, expected_context_sha256=CTX, khoa="g5-k2")
        self.assertEqual((r["replay"], r["tao_moi"]), (True, False))
        h_ds = c.goi[0][1][1]
        self.assertEqual(h_ds, _h("CRM_G5_DOI_SOAT", {"ky_id": KY, "expected_context_sha256": CTX}))
        self.assertNotEqual(h_ds, _h("CRM_G5_CHAY", {"ky_id": KY, "expected_context_sha256": CTX}))

    def test_tu_choi_truoc_sql(self):
        dv, c = _dv()
        for ctx in (None, "", "C" * 64, "c" * 63, 5):
            _loi(self, "CRM_G_YEU_CAU_SAI", dv.chay, "MO_PHONG_KT_A", ky_id=KY, expected_context_sha256=ctx, khoa="k")
        _loi(self, "CRM_G_YEU_CAU_SAI", dv.chay, "MO_PHONG_KT_A", ky_id="khong-uuid", expected_context_sha256=CTX, khoa="k")
        _loi(self, "CRM_G_KHOA", dv.doi_soat, "MO_PHONG_KT_A", ky_id=KY, expected_context_sha256=CTX, khoa="k k")
        _loi(self, "DANH_TINH", dv.chay, "NGUOI_LA", ky_id=KY, expected_context_sha256=CTX, khoa="k")
        self.assertEqual(c.goi, [])


class Worker(unittest.TestCase):
    def test_hang_doi_tren_ket_noi_chu(self):
        muc = [{"viec_id": VIEC, "ky_id": KY, "loai": "BAT_BUOC", "nguoi_chay": "MO_PHONG_KT_A", "tac_nhan_loai": "SYSTEM_JOB"}]
        dv, c = _dv({"crm_g5_hang_doi": [muc]})
        self.assertEqual(dv.hang_doi(5), muc)
        self.assertEqual(c.goi, [("crm_g5_hang_doi", (5,), None)])

    def test_nhan_duoi_nguoi_chay_khong_muon_danh_tinh(self):
        dv, c = _dv({"crm_g5_nhan": [{"nhan": True, "viec_id": VIEC}, {"nhan": False, "ly_do": "THIEU_NGUOI_CHAY"}]})
        p = dv.nhan({"viec_id": VIEC, "nguoi_chay": "MO_PHONG_KT_A"})
        self.assertEqual((p["nguoi_chay"], c.goi[0][2]), ("MO_PHONG_KT_A", "MO_PHONG_KT_A"))
        self.assertEqual(c.goi[0][1], (VIEC, dv.lease_boi, dv.lease_giay))
        p = dv.nhan({"viec_id": VIEC, "nguoi_chay": "NGUOI_DA_THU_HOI"})  # không nạp được → giao dịch KHÔNG danh tính, không fallback
        self.assertEqual((p["nhan"], c.goi[1][2]), (False, None))
        self.assertTrue(re.fullmatch(r"g5w-[0-9a-f]{16}", dv.lease_boi))
        self.assertNotEqual(dv.lease_boi, DC.CrmDoiChieuK2(dv.kiem).lease_boi)  # khởi động lại = định danh worker mới

    def test_chuan_bi_ghi_y_dinh_truoc_engine(self):
        dv, c = _dv({"crm_g5_ghi_y_dinh": [{"y_dinh_id": "yd-1", "request_id": f"crm-g5-{VIEC}-1", "lap_lai": False}]})
        q = dv.chuan_bi(_p())
        b = _body()
        self.assertEqual((q["body"], q["body_sha256"], q["y_dinh_id"]), (b, DC.sha_body(b), "yd-1"))
        (ham, params, dt), = c.goi
        self.assertEqual((ham, dt), ("crm_g5_ghi_y_dinh", "MO_PHONG_KT_A"))
        self.assertEqual(params[:3], (VIEC, 1, dv.lease_boi))
        self.assertEqual((json.loads(params[3]), params[4], json.loads(params[5]), params[6], json.loads(params[7]), params[8]),
                         (b["expected"], b["expected_sha256"], b["catalog_binding"], b["catalog_binding_sha256"], b, DC.sha_body(b)))

    def test_chuan_bi_y_dinh_khac_khong_dung_lai_khoa(self):
        dv, c = _dv()
        b = _body()
        _loi(self, "CRM_G5_Y_DINH_KHAC", dv.chuan_bi, _p(y_dinh={"id": "yd", "expected_sha256": "0" * 64, "binding_sha256": b["catalog_binding_sha256"],
                                                               "body_sha256": DC.sha_body(b)}))
        _loi(self, "CRM_G5_Y_DINH_KHAC", dv.chuan_bi, _p(du_lieu=DU_LIEU_NHAP, y_dinh={"id": "yd", "expected_sha256": b["expected_sha256"],
                                                                                      "binding_sha256": b["catalog_binding_sha256"],
                                                                                      "body_sha256": DC.sha_body(b)}))
        self.assertEqual(c.goi, [])


class GoiEngine(unittest.TestCase):
    def q(self, dv):
        p = _p()
        b = _body()
        return {**p, "body": b, "body_sha256": DC.sha_body(b), "expected": b["expected"], "binding": b["catalog_binding"]}

    def test_chua_ghep_e5(self):
        for client in (None, _Trich6Goc()):
            dv, _ = _dv(client=client)
            self.assertEqual(dv.goi_engine(self.q(dv)), ("CHO_CAU_HINH", "E5_CHUA_GHEP"))

    def test_chua_san_sang(self):
        e5 = _E5()
        e5.san_sang = False
        dv, _ = _dv(client=e5)
        self.assertEqual(dv.goi_engine(self.q(dv)), ("CHO_CAU_HINH", "TRICH6_CHUA_SAN_SANG"))
        self.assertEqual(e5.goi, [])

    def test_ban_ky_thieu_hoac_hong(self):
        e5 = _E5()
        dv, _ = _dv(client=e5)
        q = self.q(dv)
        self.assertEqual(dv.goi_engine({**q, "ky": {**q["ky"], "ky_pdf_sha256": "b" * 64}}), ("CHO_CAU_HINH", "CRM_G5_BAN_KY_KHONG_CO"))
        self.assertEqual(dv.goi_engine({**q, "ky": {**q["ky"], "ky_pdf_sha256": "../x"}}), ("CHO_CAU_HINH", "CRM_G5_BAN_KY_KHONG_CO"))
        hong = b"%PDF-1.7 hong"
        (dv.ky.kho_ky / ("d" * 64)).write_bytes(hong)  # tên = SHA khác nội dung
        self.assertEqual(dv.goi_engine({**q, "ky": {**q["ky"], "ky_pdf_sha256": "d" * 64, "ky_pdf_len": len(hong)}}), ("LOI", "CRM_G_TEP_HONG"))
        self.assertEqual(dv.goi_engine({**q, "ky": {**q["ky"], "ky_pdf_len": len(RAW_PDF) + 1}}), ("LOI", "CRM_G_TEP_HONG"))
        self.assertEqual(e5.goi, [])

    def test_khop_tu_client_e5_gia(self):
        e5 = _E5()
        dv, _ = _dv(client=e5)
        loai, kq = dv.goi_engine(self.q(dv))
        self.assertEqual(loai, "KET_QUA")
        g5, raw, h, luot = kq
        self.assertEqual((g5["trang_thai"], h, luot), ("KHOP", sha256(raw), "luot-demo-1"))
        (g,) = e5.goi
        self.assertEqual((g["raw"], g["ten_tep"], g["request_id"], g["tham_so"]), (RAW_PDF, "ban-da-ky.pdf", f"crm-g5-{VIEC}-1", [m["ma"] for m in MAPPING]))

    def test_lech_tu_client_e5_gia(self):
        e5 = _E5(tao=lambda y: _g5(y, "LECH", lech=[_lech(y, "GIA_TRI_HD", {"so_tien": "100", "tien_te": "VND"})]))
        dv, _ = _dv(client=e5)
        loai, (g5, _, _, _) = dv.goi_engine(self.q(dv))
        self.assertEqual((loai, g5["trang_thai"], g5["lech"][0]["muc"]), ("KET_QUA", "LECH", 3))

    def test_ket_qua_sai_va_implementation(self):
        dv, _ = _dv(client=_E5(tao=lambda y: _g5(y, "KHOP", coverage=["SO_HD"])))
        self.assertEqual(dv.goi_engine(self.q(dv)), ("LOI", "CRM_G5_KET_QUA_SAI"))
        dv, _ = _dv(client=_E5())
        q = self.q(dv)
        self.assertEqual(dv.goi_engine({**q, "dang_ky": {**DANG_KY, "implementation_sha256": "f" * 64}}), ("CHO_CAU_HINH", "E5_IMPLEMENTATION_KHAC"))

    def test_chua_ro_va_loi_nguon(self):
        dv, _ = _dv(client=_E5(loi=ChuaRo("TRICH6_CHUA_RO", "mất phản hồi")))
        self.assertEqual(dv.goi_engine(self.q(dv)), ("CHUA_RO", "TRICH6_CHUA_RO"))
        dv, _ = _dv(client=_E5(loi=TimeoutError("het han")))
        self.assertEqual(dv.goi_engine(self.q(dv)), ("CHUA_RO", "LOI_KHONG_PHAN_LOAI_TIMEOUTERROR"))
        dv, _ = _dv(client=_E5(loi=LoiNguon(409, "TRICH6_XUNG_DOT", "x")))
        self.assertEqual(dv.goi_engine(self.q(dv)), ("LOI", "TRICH6_XUNG_DOT"))
        dv, _ = _dv(client=_E5(loi=LoiNguon(409, "TRICH6_LOAI_CHUA_CO_DANH_MUC", "KCN/NHAO chưa đăng ký")))
        self.assertEqual(dv.goi_engine(self.q(dv)), ("CHO_CAU_HINH", "TRICH6_LOAI_CHUA_CO_DANH_MUC"))


class ChuoiABC(unittest.TestCase):
    NHAN = {"nhan": True}

    def chay(self, client, tra, muc=None):
        khoa = _Khoa()
        if isinstance(client, _E5):
            client.khoa = khoa
        nhan = {**_p(), "nguoi_chay": None}
        nhan.pop("nguoi_chay")
        base = {"crm_g5_nhan": [nhan], "crm_g5_ghi_y_dinh": [{"y_dinh_id": "yd-1", "request_id": f"crm-g5-{VIEC}-1", "lap_lai": False}]}
        base.update(tra)
        dv, c = _dv(base, client=client)
        db_goi = []

        def db(fn, *a):
            db_goi.append((fn.__name__, khoa.giu))
            return fn(*a)
        self.dv = dv
        r = dv.chay_mot(muc or {"viec_id": VIEC, "nguoi_chay": "MO_PHONG_KT_A"}, khoa, db)
        return r, c, db_goi, khoa

    def test_khop_cong_bo_ngoai_khoa(self):
        e5 = _E5()
        r, c, db_goi, khoa = self.chay(e5, {"crm_g5_cong_bo": [{"ket_qua_id": "kq-1", "trang_thai": "KHOP"}]})
        self.assertEqual(r, {"ket_qua_id": "kq-1", "trang_thai": "KHOP"})
        self.assertEqual(db_goi, [("nhan", True), ("chuan_bi", True), ("cong_bo", True)])
        self.assertEqual([g["khoa_dang_giu"] for g in e5.goi], [False])  # engine NGOÀI mutation lock
        self.assertEqual([h for h, _, _ in c.goi], ["crm_g5_nhan", "crm_g5_ghi_y_dinh", "crm_g5_cong_bo"])
        p = c.goi[2][1]
        self.assertEqual((p[0], p[1], p[2], p[3]), (VIEC, 1, self.dv.lease_boi, "KHOP"))
        raw_sha, raw_len = p[8], p[9]
        tep = self.dv.kho / "ket-qua" / f"{raw_sha}.json"  # raw bất biến theo SHA trong kho doi-chieu (không chép vào master)
        self.assertEqual((sha256(tep.read_bytes()), len(tep.read_bytes())), (raw_sha, raw_len))
        self.assertEqual(khoa.su_kien, ["vao", "ra"] * 3)

    def test_khong_nhan_duoc(self):
        dv_tra = {"crm_g5_nhan": [{"nhan": False, "ly_do": "THIEU_DANG_KY", "trang_thai": "CHO_CAU_HINH"}]}
        e5 = _E5()
        r, c, db_goi, _ = self.chay(e5, dv_tra)
        self.assertEqual(r["ly_do"], "THIEU_DANG_KY")
        self.assertEqual((e5.goi, [h for h, _, _ in c.goi]), ([], ["crm_g5_nhan"]))

    def test_e5_chua_ghep_cho_cau_hinh_giu_viec(self):
        r, c, _, _ = self.chay(_Trich6Goc(), {"crm_g5_ket_thuc": [{"ap_dung": True, "trang_thai": "CHO_CAU_HINH"}]})
        self.assertEqual(r["trang_thai"], "CHO_CAU_HINH")
        (ham, p, _), = [x for x in c.goi if x[0] == "crm_g5_ket_thuc"]
        self.assertEqual(p, (VIEC, 1, c.goi[0][1][1], "CHO_CAU_HINH", "E5_CHUA_GHEP", DC.CHO_CAU_HINH))
        self.assertNotIn("crm_g5_cong_bo", [h for h, _, _ in c.goi])  # không MATCH giả

    def test_chua_ro_giu_request(self):
        r, c, _, _ = self.chay(_E5(loi=ChuaRo("TRICH6_CHUA_RO", "x")), {"crm_g5_ket_thuc": [{"ap_dung": True, "trang_thai": "CHUA_RO"}]})
        p = [x for x in c.goi if x[0] == "crm_g5_ket_thuc"][0][1]
        self.assertEqual((p[3], p[4], p[5]), ("CHUA_RO", "TRICH6_CHUA_RO", DC.CHO_CHUA_RO))

    def test_lease_mat_khi_y_dinh_hoac_cong_bo(self):
        r, c, _, _ = self.chay(_E5(), {"crm_g5_ghi_y_dinh": [DataError("CRM_G5_LEASE_MAT", "x")]})
        self.assertEqual(r, {"nhan": True, "ket_thuc": "LEASE_MAT"})
        self.assertNotIn("crm_g5_ket_thuc", [h for h, _, _ in c.goi])
        e5 = _E5()
        r, c, _, _ = self.chay(e5, {"crm_g5_cong_bo": [DataError("CRM_G5_LEASE_MAT", "x")]})
        self.assertEqual((r, len(e5.goi)), ({"nhan": True, "ket_thuc": "LEASE_MAT"}, 1))
        self.assertNotIn("crm_g5_ket_thuc", [h for h, _, _ in c.goi])

    def test_quyen_hoac_dang_ky_doi_truoc_cong_bo(self):
        for ma in ("CRM_G5_DANG_KY_DOI", "CRM_G5_NGUOI_CHAY_DOI", "CRM_KIEM_CHUA_CO_PHAM_VI", "CRM_G5_KET_QUA_SAI"):
            r, c, _, _ = self.chay(_E5(), {"crm_g5_cong_bo": [DataError(ma, "x")],
                                           "crm_g5_ket_thuc": [{"ap_dung": True, "trang_thai": "CHO_CAU_HINH"}]})
            p = [x for x in c.goi if x[0] == "crm_g5_ket_thuc"][0][1]
            self.assertEqual((p[3], p[4]), ("CHO_CAU_HINH", ma), ma)

    def test_mapping_sai_ket_thuc_loi(self):
        dk_sai = {**DANG_KY, "mapping": [{"ma": "X", "crm_truong": "khong_co", "muc": 1}]}
        nhan = {**_p(dang_ky=dk_sai)}
        nhan.pop("nguoi_chay")
        e5 = _E5()
        r, c, _, _ = self.chay(e5, {"crm_g5_nhan": [nhan], "crm_g5_ket_thuc": [{"ap_dung": True, "trang_thai": "LOI"}]})
        p = [x for x in c.goi if x[0] == "crm_g5_ket_thuc"][0][1]
        self.assertEqual((p[3], p[4], e5.goi), ("LOI", "CRM_G5_MAPPING_SAI", []))  # SQL đổi LOI → CHO_CAU_HINH cho việc bắt buộc

    def test_bat_buoc_duoi_nguoi_chay_cau_hinh(self):
        nhan = {**_p(loai="BAT_BUOC", tac_nhan_loai="SYSTEM_JOB", tac_nhan="MO_PHONG_KT_CHAY")}
        nhan.pop("nguoi_chay")
        e5 = _E5()
        khoa = _Khoa()
        e5.khoa = khoa
        dv, c = _dv({"crm_g5_nhan": [nhan], "crm_g5_ghi_y_dinh": [{"y_dinh_id": "yd", "request_id": "r", "lap_lai": False}],
                     "crm_g5_cong_bo": [{"ket_qua_id": "kq", "trang_thai": "KHOP"}]}, client=e5, nguoi=("MO_PHONG_KT_CHAY",))
        dv.chay_mot({"viec_id": VIEC, "nguoi_chay": "MO_PHONG_KT_CHAY", "tac_nhan_loai": "SYSTEM_JOB"}, khoa)
        self.assertEqual([dt for _, _, dt in c.goi], ["MO_PHONG_KT_CHAY"] * 3)  # cả A và C dưới đúng người chạy cấu hình

    def test_chua_doi_chieu_duoc_cong_bo_nghia_vu_van_mo(self):  # FIX01-D (bổ sung)
        thieu = [m["ma"] for m in MAPPING]
        e5 = _E5(tao=lambda y: _g5(y, "CHUA_DOI_CHIEU_DUOC", coverage=[], thieu=thieu))
        nhan = {**_p(loai="BAT_BUOC", tac_nhan_loai="SYSTEM_JOB")}
        nhan.pop("nguoi_chay")
        cb = {"ket_qua_id": "kq-chua", "trang_thai": "CHUA_DOI_CHIEU_DUOC", "viec_trang_thai": "CHO_CAU_HINH"}
        r, c, db_goi, _ = self.chay(e5, {"crm_g5_nhan": [nhan], "crm_g5_cong_bo": [cb]})
        self.assertEqual(r, cb)  # SQL giữ việc bắt buộc mở (CHO_CAU_HINH); service không tự đóng/ghi đè
        p = [x for x in c.goi if x[0] == "crm_g5_cong_bo"][0][1]
        self.assertEqual((p[3], json.loads(p[4]), json.loads(p[6])), ("CHUA_DOI_CHIEU_DUOC", [], thieu))  # công bố CHUA nguyên văn
        self.assertEqual(json.loads(p[7])["trang_thai"], "CHUA_DOI_CHIEU_DUOC")
        self.assertNotIn("crm_g5_ket_thuc", [h for h, _, _ in c.goi])
        self.assertEqual(len(e5.goi), 1)
        # lần nhận sau, cùng đăng ký: SQL trả chờ có lý do → KHÔNG ghi ý định, KHÔNG gọi engine (không POST trùng request_id)
        e5b = _E5()
        r, c, _, _ = self.chay(e5b, {"crm_g5_nhan": [{"nhan": False, "ly_do": "G5_CHUA_DOI_CHIEU_DUOC", "trang_thai": "CHO_CAU_HINH"}]})
        self.assertEqual((r["ly_do"], e5b.goi, [h for h, _, _ in c.goi]), ("G5_CHUA_DOI_CHIEU_DUOC", [], ["crm_g5_nhan"]))
        # đăng ký mới → SQL cấp thế hệ mới (request_id mới) → chạy tiếp và có thể hoàn tất KHOP
        nhan2 = {**_p(loai="BAT_BUOC", tac_nhan_loai="SYSTEM_JOB", the_he=2, request_id=f"crm-g5-{VIEC}-2")}
        nhan2.pop("nguoi_chay")
        e5c = _E5()
        r, c, _, _ = self.chay(e5c, {"crm_g5_nhan": [nhan2],
                                     "crm_g5_ghi_y_dinh": [{"y_dinh_id": "yd-2", "request_id": f"crm-g5-{VIEC}-2", "lap_lai": False}],
                                     "crm_g5_cong_bo": [{"ket_qua_id": "kq-2", "trang_thai": "KHOP", "viec_trang_thai": "XONG"}]})
        self.assertEqual((r["viec_trang_thai"], [g["request_id"] for g in e5c.goi]), ("XONG", [f"crm-g5-{VIEC}-2"]))


class HangDoi(unittest.TestCase):
    def test_mot_luot_va_dung(self):
        class _Dv:
            def __init__(self):
                self.da = []

            def hang_doi(self, n):
                return [{"viec_id": "a"}, {"viec_id": "b"}]

            def chay_mot(self, muc, lock, db):
                self.da.append(muc["viec_id"])
                hd._dung.set()
        dv = _Dv()
        hd = DC.HangDoiG5(dv, threading.Lock(), lo=5)
        self.assertEqual(hd.mot_luot(), 2)
        self.assertEqual(dv.da, ["a"])  # dừng: không nhận việc kế tiếp; việc còn lại nằm bền ở CSDL

    def test_mot_worker_va_loi_chu_ky(self):
        class _Dv:
            n = 0

            def hang_doi(self, n):
                _Dv.n += 1
                hd._dung.set()
                hd._ev.set()
                raise DataError("PG_KHONG_KET_NOI", "x")
        hd = DC.HangDoiG5(_Dv(), threading.Lock(), chu_ky=3600)
        hd._vong()
        self.assertEqual((hd.loi_cuoi, _Dv.n), ("PG_KHONG_KET_NOI", 1))
        hd2 = DC.HangDoiG5(_Dv(), threading.Lock(), chu_ky=3600)
        hd2._dung.set()
        hd2.bat_dau()
        t = hd2._t
        hd2.bat_dau()
        self.assertIs(hd2._t, t)
        self.assertTrue(t.daemon)
        hd2.dung(5)


# ---------------------------------------------------------------------------------------------------------------- 3. hợp đồng tĩnh CRM_G5_SQL
def _doan(txt: str, dau: str, cuoi: str) -> str:
    i = txt.index(dau)
    return txt[i:txt.index(cuoi, i)]


def _import_that(src: str) -> list[str]:
    """FIX01-B: import THẬT của module = nút AST Import/ImportFrom (chữ 'import' trong docstring/chuỗi SQL không phải import)."""
    return [ast.dump(n) for n in ast.walk(ast.parse(src)) if isinstance(n, (ast.Import, ast.ImportFrom))]


class HopDongSqlTinh(unittest.TestCase):
    def test_khong_registry_ordinal(self):
        src = (ROOT / "src/kho_tri_thuc/k2/sql_crm_doi_chieu.py").read_text(encoding="utf-8")
        self.assertEqual(_import_that(src), [], "module SQL chỉ hằng — không import registry")
        from kho_tri_thuc.ha_tang import pg_migrations as PM
        self.assertGreaterEqual(PM.PG_SCHEMA_VERSION, 32)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        self.assertEqual([i for i, x in enumerate(PM.PG_MIGRATIONS) if tuple(x) == tuple(CRM_G5_SQL)], [31],
                         "owner đăng ký G5 đúng một lần tại M0032")
        self.assertIs(PM.PG_MIGRATIONS[31], CRM_G5_SQL)
        self.assertNotIn("schema_migrations", SQL_TXT)
        self.assertNotIn("ktt.crm_kiem_g5', 'SYNTHETIC", SQL_TXT)  # không tự đặt GUC fixture

    def test_trigger_bat_buoc_cung_giao_dich(self):
        self.assertIn("AFTER INSERT ON master.crm_hd_ky FOR EACH ROW WHEN (NEW.co_sua)", SQL_TXT)
        self.assertNotIn("UPDATE master.crm_hd_ky_g5", SQL_TXT)  # G4 PENDING/NOT_SELECTED không bị ghi đè
        self.assertNotIn("UPDATE master.crm_hd_ky ", SQL_TXT)
        self.assertIn("ON CONFLICT DO NOTHING", _doan(SQL_TXT, "WITH moi AS", "FROM moi"))  # backfill idempotent

    def test_khong_fallback_nguoi_chay(self):
        hd = _doan(SQL_TXT, "FUNCTION master.crm_g5_hang_doi", "END $$")
        self.assertIn("THIEU_NGUOI_CHAY", hd)
        for x in ("k.tao_boi", "crm_hd_ky", "CFO", "vai_tro", "ORDER BY n."):  # không suy người chạy từ người ký/vai/người đầu tiên
            self.assertNotIn(x, hd)
        self.assertIn("'nguoi_chay', v.khoi_tao_boi", hd)  # thủ công: chính người khởi tạo
        self.assertNotIn("INSERT INTO master.phan_cong_hanh_dong", SQL_TXT)
        self.assertNotIn("GRANT ", SQL_TXT.replace("REVOKE", ""))

    def test_he_thong_khong_duyet(self):
        for f in ("crm_g5_nhan", "crm_g5_cong_bo", "crm_g5_ket_thuc"):
            t = _doan(SQL_TXT, "FUNCTION master." + f, "END $$")
            for x in ("crm_kiem_ho_so", "crm_kiem_hieu_luc", "hop_dong_phien_ban", "but_toan", "viec_can_duyet", "crm_kiem_quyet_dinh"):
                self.assertNotIn(x, t, (f, x))

    def test_g6_nhanh_synthetic_va_g7_nguyen_van(self):
        dau = "IF current_setting('ktt.crm_kiem_g5', true) IS DISTINCT FROM 'SYNTHETIC_FIXTURE' THEN"
        cu = _doan(SQL_G6A, "FUNCTION master.crm_kiem_g5_xet", "END $$")
        moi = _doan(SQL_TXT, "FUNCTION master.crm_kiem_g5_xet", "END $$")
        self.assertEqual(moi[moi.index(dau):], cu[cu.index(dau):])
        self.assertIn("UNREGISTERED_G5_PROOF", moi)
        g7 = "IF NEW.loai = 'G7_LECH' THEN"
        cu = _doan(SQL_G6A, "FUNCTION master.crm_kiem_xu_ly_lech_kiem", "END $$")
        moi = _doan(SQL_TXT, "FUNCTION master.crm_kiem_xu_ly_lech_kiem", "END $$")
        self.assertEqual(_doan(moi, g7, "            ELSE"), _doan(cu, g7, "            ELSE"))
        self.assertEqual(moi[:moi.index(g7)], cu[:cu.index(g7)])

    def test_rls_revoke_bang_moi(self):
        for t in _G5_BANG_MOI:
            self.assertIn(f"ALTER TABLE master.{t} ENABLE ROW LEVEL SECURITY", SQL_TXT)
        self.assertIn("REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC", SQL_TXT)

    def test_ma_409_dc_khop_sql(self):
        from kho_tri_thuc.giao_dien import crm_g as CG
        ma_sql = set(re.findall(r"'(CRM_G5_[A-Z_]+):", SQL_TXT))
        self.assertTrue({"CRM_G5_NGU_CANH_CU", "CRM_G5_CHUA_CO_VIEC", "CRM_G5_LEASE_MAT", "CRM_G5_DANG_KY_DOI"} <= ma_sql)
        self.assertTrue(ma_sql - {"CRM_G5_DANG_KY_SAI", "CRM_G5_NGUOI_CHAY_SAI", "CRM_G5_THU_HOI_SAI"} <= CG.MA_409_DC, ma_sql - CG.MA_409_DC)

    # ------------------------------------------------------------------ FIX01 (bổ sung; ID cũ giữ nguyên)
    def test_oracle_ast_phan_biet_docstring_va_import_that(self):  # FIX01-B counterexample
        chi_doc = '"""Docstring:\n  import ``CRM_G5_SQL`` và APPEND\nfrom registry import x\n"""\nX = ("import y",)\n'
        self.assertIsNotNone(re.search(r"^\s*(from|import)\s", chi_doc, re.M))  # regex cũ báo nhầm (dương tính giả trên docstring)
        self.assertEqual(_import_that(chi_doc), [])
        for that in ("import kho_tri_thuc.ha_tang.pg_migrations\nX = 1\n", "from ..ha_tang import pg_migrations\n",
                     "def f():\n    from kho_tri_thuc.ha_tang import pg_migrations as PM\n    return PM\n"):
            self.assertEqual(len(_import_that(that)), 1, that)  # import thật (kể cả lồng trong hàm) vẫn bị bắt
        src = (ROOT / "src/kho_tri_thuc/k2/sql_crm_doi_chieu.py").read_text(encoding="utf-8")
        self.assertIn("import ``CRM_G5_SQL``", src)  # docstring nguyên văn (không sửa để né oracle)

    def test_nhan_chi_dong_bat_buoc_khi_ket_qua_hoan_tat(self):  # FIX01-D
        nhan = _doan(SQL_TXT, "FUNCTION master.crm_g5_nhan", "END $$")
        self.assertNotIn("IF x.id IS NOT NULL AND NOT EXISTS", nhan)  # shortcut cũ: đóng chỉ vì có x.id
        i_sc = nhan.index("IF x.id IS NOT NULL AND x.trang_thai IN ('KHOP','LECH') THEN")
        i_cho = nhan.index("IF v_y_xong AND y.dang_ky_id = dk.id THEN")
        # FIX02: nhánh CHUA kết thúc TRƯỚC nhánh đăng ký đổi — slice cũ [i_cho:'THE_HE_MOI'] vô tình gồm UPDATE tăng thế hệ của nhánh đổi
        i_doi = nhan.index("IF y.id IS NOT NULL AND y.dang_ky_id <> dk.id THEN")
        i_th = nhan.index("'THE_HE_MOI'")
        i_chay = nhan.index("SET trang_thai = 'DANG_CHAY'")
        self.assertTrue(i_sc < i_cho < i_doi < i_th < i_chay)
        self.assertIn("q.y_dinh_id = y.id", nhan[:i_sc])  # ý định của thế hệ đã có kết quả → không POST lại cùng request_id
        cho = nhan[i_cho:i_doi]
        self.assertIn("RETURN jsonb_build_object('nhan', false, 'ly_do', 'G5_CHUA_DOI_CHIEU_DUOC', 'trang_thai', 'CHO_CAU_HINH')", cho)
        self.assertTrue(cho.rstrip().endswith("END IF;"), cho[-80:])  # nhánh CHUA đóng (RETURN wait) trước khi nhánh đổi bắt đầu
        self.assertLess(cho.index("RETURN jsonb_build_object('nhan', false"), cho.rindex("END IF;"))
        self.assertIn("lease_den = NULL", cho)
        for x in ("so_lan", "the_he + 1", "the_he = the_he", "crm_g5_y_dinh (", "'XONG'", "'THE_HE_MOI'", "'DANG_CHAY'"):  # không lượt/ý định/thế hệ/đóng
            self.assertNotIn(x, cho, x)
        # đăng ký đổi (implementation/catalog/mapping mới = dòng đăng ký mới) → thế hệ mới, request_id mới → chạy tiếp được (có kiểm soát)
        doi = nhan[i_doi:i_chay]
        for x in ("SET the_he = the_he + 1", "'THE_HE_MOI'"):
            self.assertIn(x, doi, x)
        for x in ("RETURN jsonb_build_object", "'XONG'", "'G5_CHUA_DOI_CHIEU_DUOC'"):  # ("RETURNING * INTO v" hợp lệ — không phải lệnh trả)
            self.assertNotIn(x, doi, x)

    def test_oracle_slice_cho_dung_truoc_nhanh_doi(self):  # FIX02: counterexample — slice cũ gồm nhánh đổi, slice mới thì không
        nhan = _doan(SQL_TXT, "FUNCTION master.crm_g5_nhan", "END $$")
        i_cho = nhan.index("IF v_y_xong AND y.dang_ky_id = dk.id THEN")
        i_doi = nhan.index("IF y.id IS NOT NULL AND y.dang_ky_id <> dk.id THEN")
        cu, moi = nhan[i_cho:nhan.index("'THE_HE_MOI'")], nhan[i_cho:i_doi]
        self.assertIn("the_he = the_he + 1", cu)  # nguyên nhân FAIL độc lập: UPDATE tăng thế hệ thuộc nhánh ĐỔI, không thuộc nhánh CHUA
        self.assertNotIn("the_he = the_he + 1", moi)
        self.assertEqual(nhan.count("IF y.id IS NOT NULL AND y.dang_ky_id <> dk.id THEN"), 1)
        self.assertEqual(nhan.count("the_he = the_he + 1"), 1)  # đúng một chỗ tăng thế hệ trong crm_g5_nhan — nằm trong nhánh đổi
        self.assertLess(i_doi, nhan.index("the_he = the_he + 1"))

    def test_cong_bo_chua_giu_nghia_vu_bat_buoc(self):  # FIX01-D
        cb = _doan(SQL_TXT, "FUNCTION master.crm_g5_cong_bo", "END $$")
        i_ins = cb.index("INSERT INTO master.crm_g5_ket_qua")
        i_chua = cb.index("IF x.trang_thai = 'CHUA_DOI_CHIEU_DUOC' AND v.loai = 'BAT_BUOC' THEN")
        i_xong = cb.index("SET trang_thai = 'XONG'")
        self.assertTrue(i_ins < cb.index("'KET_QUA'") < i_chua < i_xong)  # kết quả CHUA vẫn công bố (raw/ID/lịch sử) trước nhánh
        nhanh = cb[i_chua:i_xong]
        for x in ("trang_thai = 'CHO_CAU_HINH'", "ly_do = 'G5_CHUA_DOI_CHIEU_DUOC'", "ket_qua_id = NULL", "lease_boi = NULL",
                  "'viec_trang_thai', 'CHO_CAU_HINH'"):
            self.assertIn(x, nhanh, x)
        self.assertIn("'viec_trang_thai', 'XONG'", cb[i_xong:])  # KHOP/LECH (và việc thủ công) đóng như trước

    def test_lease_het_han_khong_ghi(self):  # FIX01-E
        bien = "v.lease_den IS NULL OR v.lease_den <= now()"
        for f, moc in (("crm_g5_ghi_y_dinh", "CRM_G5_LEASE_MAT"), ("crm_g5_cong_bo", "CRM_G5_LEASE_MAT"), ("crm_g5_ket_thuc", "'ap_dung', false")):
            t = _doan(SQL_TXT, "FUNCTION master." + f, "END $$")
            self.assertIn(bien, t[:t.index(moc)], f)
        kt = _doan(SQL_TXT, "FUNCTION master.crm_g5_ket_thuc", "END $$")
        self.assertLess(kt.index("'ap_dung', false"), kt.index("UPDATE master.crm_g5_viec"))  # không áp dụng → không đổi trạng thái
        self.assertLess(kt.index("'ap_dung', false"), kt.index("crm_g5_ghi_su_kien"))  # … và không ghi lịch sử
        self.assertNotIn("lease_den < now()", SQL_TXT)  # claim/đối soát/fencing cùng biên <= — không khe hở tại đúng thời điểm hết hạn
        for f in ("crm_g5_hang_doi", "crm_g5_nhan", "crm_g5_doi_soat"):
            self.assertIn("lease_den <= now()", _doan(SQL_TXT, "FUNCTION master." + f, "END $$"), f)


if __name__ == "__main__":
    unittest.main()
