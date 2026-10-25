"""BG-1c vòng 2 — đối chiếu hai tầng: phép tính báo giá của máy chủ (Python, In/Chuyển) ↔ bước kiểm khi Ký (M0030, SQL).

- `MienTien` (THUẦN): hằng giới hạn rút từ M0030; các ca biên (tổng/tiền đợt ngoài miền, tổng ≤ 0, tích làm tròn về 0, đúng biên) — Python chặn
  In/Chuyển bằng ĐÚNG mã SQL trả ở Ký, lỗi theo trường.
- `DoiChieuPostgres` (PostgreSQL THẬT, chỉ đọc): dựng hàm tạm pg_temp từ `pg_get_functiondef` của `master.crm_kiem_lich_ky` ĐÃ CÀI (chỉ thay nguồn
  v_bg = tham số jsonb), chạy cùng các ca trong MỘT giao dịch rồi ROLLBACK; so mã chặn, tổng, tiền từng đợt với Python.
  Cần biến môi trường KTT_BG1C_KET_NOI = tệp ket-noi.local.json của CSDL DEMO (kho_crm_demo*) đã ở schema ≥ 30; thiếu → skip (NOT_VERIFIED).
Dữ liệu tổng hợp DEMO; không ghi CSDL, không mạng ngoài máy.
"""

from __future__ import annotations

import json
import os
import re
import unittest
from pathlib import Path

from kho_tri_thuc.ha_tang import primitives as P
from kho_tri_thuc.k2 import crm_giao_ket as GK
from kho_tri_thuc.k2 import sql_crm_bg1c as B

LOAI = "11111111-1111-4111-8111-111111111111"
MAX = int(re.search(r"v_max constant numeric := ([0-9]+);", B.CRM_BG1C_SQL[0]).group(1))  # hằng của M0030, không tự đặt
MAC_DINH = {"ty_gia": "26000", "ngay": None}


def bao_gia(gia, lich=("100%",), **sua):
    return {"loai_hinh_id": LOAI, "don_vi": {"ma": "LO-DEMO"}, "khach": {"du_thao": {"ten": "KHÁCH DEMO"}},
            "gia": {"co_so_thue": "NET", **gia}, "lich": [{"gia_tri_nhap": v} for v in lich], **sua}


def vnd(**g):
    return {"tien_te": "VND", **g}


def usd(**g):
    return {"tien_te": "USD", **g}


def _vn(n: int) -> str:
    return f"{n:,}".replace(",", ".")


# (tên, dữ liệu, dữ liệu cũ?, mã SQL kỳ vọng ở Ký: tổng (loi), từng đợt (dong[i].loi chứa SO_TIEN_KHONG_DUONG))
CA_BIEN = (
    ("v2_vi_du_39_ty", bao_gia(usd(don_gia="100", dien_tich="15000"), ("30%", "70%")), False, set(), [False, False]),
    ("usd_1e15_x26000_x1", bao_gia(usd(don_gia="1" + "0" * 15, dien_tich="1")), False, {"TONG_NGOAI_MIEN"}, [False]),
    ("usd_1e15_x26000_x100_bang_chu_khong_doc", bao_gia(usd(don_gia="1" + "0" * 15, dien_tich="100")), False, {"TONG_NGOAI_MIEN"}, [False]),
    ("vnd_don_gia_0", bao_gia(vnd(don_gia="0", dien_tich="100")), False, {"TONG_NGOAI_MIEN"}, [False]),
    ("vnd_tich_lam_tron_ve_0", bao_gia(vnd(don_gia="0.0001", dien_tich="1")), False, {"TONG_NGOAI_MIEN"}, [False]),
    ("vnd_tich_lam_tron_len_1", bao_gia(vnd(don_gia="0.5", dien_tich="1")), False, set(), [False]),
    ("vnd_tong_dung_bien", bao_gia(vnd(tong=str(MAX))), False, set(), [False]),
    ("vnd_tong_bien_cong_1", bao_gia(vnd(tong=str(MAX + 1))), False, {"TONG_NGOAI_MIEN"}, [False]),
    ("ghi_de_0", bao_gia(usd(don_gia="100", dien_tich="15000"), tong_gia_tri_ghi_de="0"), False, {"TONG_NGOAI_MIEN"}, [False]),
    ("ghi_de_vuot_bien", bao_gia(vnd(), tong_gia_tri_ghi_de=_vn(MAX + 1)), False, {"TONG_NGOAI_MIEN"}, [False]),
    ("ghi_de_dung_bien", bao_gia(vnd(), tong_gia_tri_ghi_de=_vn(MAX)), False, set(), [False]),
    ("dot_tien_0", bao_gia(vnd(tong="1000"), ("0", "1.000")), False, set(), [True, False]),
    ("dot_phan_tram_0", bao_gia(vnd(tong="1000"), ("0%", "100%")), False, set(), [True, False]),
    ("dot_tien_vuot_bien", bao_gia(vnd(tong="1000"), (_vn(MAX + 1),)), False, set(), [True]),
    ("cu_usd_tong_dung_bien", bao_gia(usd(tong=f"{MAX // 100}.{MAX % 100:02d}"), fx={"cap": "USD/VND", "ty_gia": "25500", "ngay": "2026-10-24"}),
     True, set(), [False]),
    ("cu_usd_tong_bien_cong_1_cent", bao_gia(usd(tong=f"{(MAX + 1) // 100}.{(MAX + 1) % 100:02d}"),
                                             fx={"cap": "USD/VND", "ty_gia": "25500", "ngay": "2026-10-24"}), True, {"TONG_NGOAI_MIEN"}, [False]),
    ("cu_vnd_tong_0", bao_gia(vnd(tong="0")), True, {"TONG_NGOAI_MIEN"}, [False]),
)


def _python(du, cu):
    d = GK.chuan_hoa_bao_gia(du, fx_mac_dinh=MAC_DINH, hom_nay="2026-10-25")
    if cu:
        d.pop("tien_chinh")
    return d, GK.tinh_bao_gia(d, None)


class MienTien(unittest.TestCase):
    def test_hang_gioi_han_rut_tu_m0030(self):
        self.assertEqual(GK.TIEN_TOI_DA_MINOR, MAX)
        self.assertEqual(MAX, 2 ** 63 - 1)  # bigint của PostgreSQL
        self.assertEqual(MAX, P.MAX_INT64)  # cùng biên vượt-INTEGER-64-bit của money_minor
        sql = B.CRM_BG1C_SQL[0]
        self.assertIn("ELSIF v_tong <= 0 OR v_tong > v_max THEN", sql)
        self.assertIn("IF v_mi IS NOT NULL AND (v_mi <= 0 OR v_mi > v_max) THEN", sql)

    def test_ca_bien_python_chan_dung_ma_cua_ky(self):
        for ten, du, cu, ma_tong, dot in CA_BIEN:
            with self.subTest(ten=ten):
                d, t = _python(du, cu)
                ma = {e["ma"] for e in t["chan_in"]}
                self.assertTrue(ma_tong <= ma, (ma_tong, ma))
                self.assertEqual(["SO_TIEN_KHONG_DUONG" in x["loi"] for x in t["dong"]], dot)
                chan = bool(ma_tong) or any(dot)
                self.assertEqual(bool(t["chan_in"]), chan)  # ngoài miền chặn In …
                self.assertTrue(set(e["ma"] for e in t["chan_in"]) <= set(e["ma"] for e in t["chan_chuyen"]))  # … và Chuyển
                if "TONG_NGOAI_MIEN" in ma:
                    e = next(e for e in t["chan_in"] if e["ma"] == "TONG_NGOAI_MIEN")
                    self.assertIn(e["truong"], ("gia.don_gia", "gia.tong", "tong_gia_tri_ghi_de"))
                    self.assertIn("không quá " + GK.R.tien_hien_thi(MAX, t["tien_te"]), e["thong_bao"])
                    self.assertIsNone(t["tong_bang_chu"])  # không đọc chữ cho tổng bị chặn
                    self.assertTrue(all(x["so_tien_minor"] is None for x in t["dong"]))  # như SQL: tổng ngoài miền → đợt chưa có tổng
                if not chan:
                    self.assertIsNotNone(t["tong_bang_chu"])

    def test_truong_cua_loi_mien(self):
        _, t = _python(bao_gia(usd(don_gia="1" + "0" * 15, dien_tich="1")), False)
        self.assertEqual(next(e["truong"] for e in t["chan_in"] if e["ma"] == "TONG_NGOAI_MIEN"), "gia.don_gia")
        _, t = _python(bao_gia(vnd(tong=str(MAX + 1))), False)
        self.assertEqual(next(e["truong"] for e in t["chan_in"] if e["ma"] == "TONG_NGOAI_MIEN"), "gia.tong")
        _, t = _python(bao_gia(vnd(), tong_gia_tri_ghi_de="0"), False)
        self.assertEqual(next(e["truong"] for e in t["chan_in"] if e["ma"] == "TONG_NGOAI_MIEN"), "tong_gia_tri_ghi_de")
        _, t = _python(bao_gia(vnd(tong="1000"), ("0", "1.000")), False)
        e = t["dong"][0]["loi_chi_tiet"][0]
        self.assertEqual((e["ma"], e["truong"]), ("SO_TIEN_KHONG_DUONG", "lich.0"))
        self.assertIn("lớn hơn 0", e["thong_bao"])

    def test_bang_chu_khong_doc_duoc_la_loi_chan(self):
        from unittest import mock
        with mock.patch.object(GK.R, "bang_chu", side_effect=GK.R.LoiRender("CRM_GK_BANG_CHU", "x")):
            _, t = _python(bao_gia(vnd(tong="1000")), False)
        e = next(e for e in t["chan_in"] if e["ma"] == "TONG_BANG_CHU_KHONG_DOC_DUOC")
        self.assertEqual(e["truong"], "gia.tong")
        self.assertIsNone(t["tong_bang_chu"])
        self.assertIn("TONG_BANG_CHU_KHONG_DOC_DUOC", [x["ma"] for x in t["chan_chuyen"]])


def _ket_noi():
    tep = os.environ.get("KTT_BG1C_KET_NOI")
    if not tep:
        raise unittest.SkipTest("NOT_VERIFIED: thiếu KTT_BG1C_KET_NOI (tệp ket-noi.local.json của CSDL DEMO schema ≥ 30)")
    from kho_tri_thuc.k2.crm_khoi_dong import doc_ket_noi, nap_driver
    kn = doc_ket_noi(Path(tep))  # chỉ CSDL DEMO kho_crm_demo*; không in DSN
    return nap_driver(), kn


@unittest.skipUnless(os.environ.get("KTT_BG1C_KET_NOI"), "NOT_VERIFIED: thiếu KTT_BG1C_KET_NOI — đối chiếu PostgreSQL thật không chạy (skip, KHÔNG PASS)")
class DoiChieuPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        psycopg, kn = _ket_noi()
        cls.conn = psycopg.connect(kn["admin_dsn"] or kn["app_dsn"])  # không autocommit: mọi câu trong MỘT giao dịch, cuối cùng ROLLBACK
        cur = cls.conn.cursor()
        cur.execute("SELECT max(version) FROM master.schema_migrations")
        cls.schema = cur.fetchone()[0]
        cur.execute("SELECT pg_get_functiondef('master.crm_kiem_lich_ky(uuid)'::regprocedure)")
        dn = cur.fetchone()[0]
        than = dn[dn.index("DECLARE"):].rsplit("$function$", 1)[0]
        nguon = ("SELECT r.du_lieu -> 'bao_gia' INTO v_bg FROM master.crm_hd_ky k JOIN master.crm_hd_soan_rev r ON r.id = k.soan_rev_id "
                 "WHERE k.id = p_ky;")
        assert than.count(nguon) == 1
        cur.execute("CREATE FUNCTION pg_temp.bg1c_lich(p_bg jsonb) RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path = master, pg_temp "
                    "AS $bg1c$ " + than.replace(nguon, "v_bg := p_bg;") + " $bg1c$")
        cls.cur = cur

    @classmethod
    def tearDownClass(cls):
        cls.conn.rollback()  # hàm tạm pg_temp không để lại gì
        cls.conn.close()

    def test_csdl_da_co_m0030(self):
        self.assertGreaterEqual(self.schema, 30)

    def test_ca_bien_hai_tang_cung_ket_luan(self):
        for ten, du, cu, ma_tong, dot in CA_BIEN:
            with self.subTest(ten=ten):
                d, t = _python(du, cu)
                self.cur.execute("SELECT pg_temp.bg1c_lich(%s::jsonb)", (json.dumps(d, ensure_ascii=False),))
                s = self.cur.fetchone()[0]
                ma_sql = {e["ma"] for e in s["loi"]}
                self.assertEqual(ma_tong, ma_sql & {"TONG_NGOAI_MIEN"}, ma_sql)
                self.assertEqual(["SO_TIEN_KHONG_DUONG" in x["loi"] for x in s["dong"]], dot)
                self.assertEqual(bool(s["loi"]), bool(t["chan_in"]), (ma_sql, [e["ma"] for e in t["chan_in"]]))  # cùng chặn / cùng qua
                self.assertEqual(s["tien_te"], t["tien_te"])
                if not s["loi"]:
                    self.assertEqual((s["tong_minor"], [x["so_tien_minor"] for x in s["dong"]]),
                                     (t["tong_minor"], [x["so_tien_minor"] for x in t["dong"]]))
                    self.assertIsNotNone(t["tong_bang_chu"])


if __name__ == "__main__":
    unittest.main()
