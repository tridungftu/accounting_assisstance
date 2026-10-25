"""DA-3a — mặc định dự án / nguồn chuẩn / lô / nhật ký trong cùng giao dịch.

Thuần/mock không CSDL. Ca PG chỉ chạy khi lead đặt KTT_DA3A_KET_NOI trỏ tệp
ket-noi.local.json của DEMO schema >= 31, theo mẫu test_crm_du_an_ban_pg.
Thiếu cấu hình -> NOT_VERIFIED/skip. Chỉ dữ liệu tổng hợp DEMO, không xóa.
"""
from __future__ import annotations

import copy
import json
import os
import threading
import unittest
import uuid
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from kho_tri_thuc.giao_dien import crm_g as HTTP
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import crm_giao_ket as G
from kho_tri_thuc.k2.crm_du_an_ban import CrmDuAnBanK2

LH, DA, LO, BG, KHAC = [str(uuid.UUID(int=i)) for i in range(1, 6)]
ME, NGAY = "MO_PHONG_BAN_HANG", "2026-10-25"
PHI = [{"ten": "Phí bảo trì DEMO", "loai": "BAO_TRI", "muc": "0.5", "don_vi_tinh": "M2_NAM", "tien_te": "USD", "co_so_tinh": "Diện tích"}]


def anh_chup():
    return {"trang_thai": "DANG_BAN", "du_an_id": DA, "phap_nhan_id": KHAC, "ngay": NGAY,
            "phien_ban": {"id": KHAC, "so": 3, "hieu_luc_tu": NGAY}, "anh_chup_sha256": "a" * 64,
            "don_gia": "120", "tien_te": "USD", "loai_hinh": {"id": LH, "ten": "Loại hình DEMO"},
            "thue": {"thue_suat": "10", "nhan": "Thuế suất 10%", "gia_chua_gom_vat": True}, "gia_dat_tru": "24",
            "giai_doan_g7": "GD1", "phi": [{**PHI[0], "thu_tu": 1}],
            "lo": [{"id": LO, "ma": "L-DEMO", "dien_tich": "100", "trang_thai": "CON_TRONG"},
                   {"id": KHAC, "ma": "GIU-DEMO", "dien_tich": "200", "trang_thai": "GIU_CHO"},
                   {"id": BG, "ma": "BAN-DEMO", "dien_tich": "300", "trang_thai": "DA_BAN"},
                   {"id": LH, "ma": "KHOA-DEMO", "dien_tich": "400", "trang_thai": "KHONG_BAN"}],
            "bo_chuan": {"trang_thai": "HIEU_LUC", "rows": [
                {"lan": "1", "gia_tri_loai": "PERCENT", "gia_tri_thap_phan": "30", "moc_loai": "SU_KIEN", "moc_su_kien": "KY_HD"},
                {"lan": "2", "gia_tri_loai": "PERCENT", "gia_tri_thap_phan": "70", "moc_loai": "SU_KIEN", "moc_su_kien": "BAN_GIAO"}]}}


def bao_gia():
    return {"loai_hinh_id": LH, "du_an_id": DA, "lo_id": LO, "don_vi": {"ma": "L-DEMO"},
            "gia": {"don_gia": "120", "tien_te": "USD", "dien_tich": "100", "co_so_thue": "NET"},
            "fx": {"ty_gia": "26000", "ngay": NGAY}, "giai_doan_g7": "GD1", "nguon_lich": "KHACH",
            "lich": G._lich_tieu_chuan(anh_chup()), "phi": copy.deepcopy(PHI)}


class MauGia:
    """Giao dịch giả khôi phục revision + nhật ký khi lệnh sau bị lỗi."""
    root = "."
    conn_tin_cay = object()

    def __init__(self):
        self.s = anh_chup()
        self.lenh, self.luu, self.nk = [], [], []
        self.quyen = True
        self.dang_tx = False
        self.loi_nk = False
        self.sql_replay = False
        self.kq = {"bao_gia_id": BG, "revision": 1, "trang_thai": "NHAP"}

    def hom_nay(self):
        return date.fromisoformat(NGAY)

    def danh_tinh(self, me):
        return {"dang_nhap": me, "vai_tro": "BAN_HANG"}

    @contextmanager
    def _tx(self, dt, *, rr=False):
        assert rr and dt["dang_nhap"] == ME
        truoc = (copy.deepcopy(self.luu), copy.deepcopy(self.nk))
        self.dang_tx = True
        try:
            yield self
        except Exception:
            self.luu, self.nk = truoc
            raise
        finally:
            self.dang_tx = False

    def _mot(self, c, sql, params=()):
        assert c is self and self.dang_tx
        if "master.du_an" in sql:
            assert "crm_gk_duoc('CRM_BAO_GIA'" in sql
            return {"id": DA} if self.quyen else None
        return {"phap_nhan_id": KHAC, "cau_hinh": {}}

    def execute(self, sql, params=()):
        assert self.dang_tx
        self.lenh.append((sql, params))
        if "crm_da_anh_chup(" in sql:
            return SimpleNamespace(fetchone=lambda: {"r": copy.deepcopy(self.s)})
        if "crm_gk_bao_gia_luu(" in sql:
            if not self.sql_replay:
                self.luu.append((json.loads(params[7]), json.loads(params[8])))
            return SimpleNamespace(fetchone=lambda: {"r": {"ket_qua": self.kq, "lap_lai": self.sql_replay}})
        if "INSERT INTO nhat_ky.su_kien" in sql:
            if self.loi_nk:
                raise RuntimeError("Nhật ký DEMO bị lỗi")
            self.nk.append((sql, params))
            return SimpleNamespace(fetchone=lambda: None)
        raise AssertionError(sql)


class MacDinh(unittest.TestCase):
    def setUp(self):
        self.m = MauGia()
        self.g = G.CrmGiaoKetK2(self.m)
        self.g._tra = Mock(return_value=None)
        self.g._trung_don_vi = Mock(return_value=[])

    def luu(self, d=None):
        return self.g.luu(ME, bao_gia_id=None, expected_revision=None, du_lieu=d or bao_gia(), khoa="da3a-demo")

    def route(self, query=None):
        query = {"du_an_id": [DA]} if query is None else query
        h = SimpleNamespace(crm_sid=lambda: "sid", send_content=Mock(), path="/api/crm/bao-gia/mac-dinh")
        app = SimpleNamespace(mutation_lock=threading.RLock(), crm_phien=lambda sid: (None, ME, None),
                              _crm_db=lambda f, *a, **kw: f(*a, **kw))
        with patch.object(HTTP, "dich_vu_gk", return_value=self.g):
            HTTP.dieu_huong(h, app, False, h.path, query)
        return h.send_content.call_args.args

    def test_route_du_truong_va_an_lo_khong_trong(self):
        status, r = self.route({"du_an_id": [DA], "ngay": [NGAY]})
        self.assertEqual(status, 200)
        self.assertEqual(set(r), {"du_an_id", "ngay", "don_gia", "tien_te", "don_vi_don_gia", "loai_hinh", "thue", "thue_chi_hien_thi",
                                  "gia_dat_tru", "lo", "giai_doan_g7", "bo_chuan", "lich", "phi", "anh_chup_sha256", "phien_ban"})
        self.assertEqual((r["don_gia"], r["tien_te"], r["don_vi_don_gia"]), ("120", "USD", "m²"))
        self.assertEqual(r["lo"], [{"id": LO, "ma": "L-DEMO", "dien_tich": "100"}])
        self.assertEqual(r["thue"], self.m.s["thue"])
        self.assertTrue(r["thue_chi_hien_thi"])
        self.assertEqual((r["gia_dat_tru"], r["phi"], len(r["lich"]), r["phien_ban"]["so"]), ("24", PHI, 2, 3))
        self.assertEqual(self.m.luu, [])
        self.assertEqual(self.m.lenh[0][1], (DA, NGAY))

    def test_route_ngung_ban_chua_bat_ban_va_khong_co_phien_ban(self):
        for tt, status in (("NGUNG_BAN", 409), ("CHUA_BAT_BAN", 404), ("CHUA_CO_PHIEN_BAN", 404)):
            with self.subTest(tt=tt):
                self.m.s["trang_thai"] = tt
                code, r = self.route()
                self.assertEqual(code, status)
                self.assertTrue(any(x in r["message"] for x in ("ngừng bán", "danh mục đang bán")))

    def test_route_quyen_doc_bao_gia_va_phien(self):
        self.m.quyen = False
        self.assertEqual(self.route()[0], 404)
        self.assertEqual(self.m.lenh, [])  # chưa đọc ảnh chụp

    def test_route_query_sai_va_ngay_khong_ton_tai(self):
        for query in ({}, {"du_an_id": [DA, DA]}, {"du_an_id": ["sai"]}, {"du_an_id": [DA], "ngay": ["2026-02-30"]},
                      {"du_an_id": [DA], "actor": [ME]}, {"du_an_id": [DA], "ngay": [""]}):
            with self.subTest(query=query):
                self.assertEqual(self.route(query)[0], 400)

    def test_route_chuan_dien_vao_bao_gia_khong_lech(self):
        _, mac_dinh = self.route()
        d = bao_gia()
        d.update({"lich": mac_dinh["lich"], "phi": mac_dinh["phi"]})
        self.luu(d)
        self.assertEqual(self.m.luu[-1][0]["khac_tieu_chuan"], [])
        self.assertEqual(self.m.nk, [])

    def test_luu_nguon_may_chu_bo_metadata_gia_va_khong_doi_thue(self):
        d = bao_gia()
        d.update({"nguon_tieu_chuan": {"anh_chup_sha256": "gia", "phien_ban": 999, "ngay": "2099-01-01"}, "khac_tieu_chuan": ["giả"]})
        self.luu(d)
        dl, t = self.m.luu[-1]
        self.assertEqual(dl["nguon_tieu_chuan"], {"anh_chup_sha256": "a" * 64, "phien_ban": self.m.s["phien_ban"], "ngay": NGAY})
        self.assertEqual(dl["khac_tieu_chuan"], [])
        self.assertEqual(t["tong_minor"], "312000000")
        self.m.s["thue"]["thue_suat"], self.m.s["gia_dat_tru"] = "KCT", "99"
        self.luu(d)
        self.assertEqual({k: v for k, v in self.m.luu[-1][1].items() if k != "dong"}, {k: v for k, v in t.items() if k != "dong"})
        self.assertEqual([r["so_tien_minor"] for r in self.m.luu[-1][1]["dong"]], [r["so_tien_minor"] for r in t["dong"]])

    def test_so_tung_truong_va_nhat_ky_co_ai_chuan_bao_gia(self):
        for truong, nhan in (("gia.don_gia", "Đơn giá"), ("gia.tien_te", "Tiền tệ"), ("loai_hinh_id", "Loại hình"),
                             ("don_vi.ma", "Lô/căn"), ("gia.dien_tich", "Diện tích"), ("lich", "Tiến độ thanh toán"), ("phi", "Phí")):
            with self.subTest(truong=truong):
                d = bao_gia()
                if truong.startswith("gia."):
                    d["gia"][truong.split(".")[1]] = "VND" if truong == "gia.tien_te" else "101"
                    if truong == "gia.tien_te":
                        d.pop("fx")
                elif truong == "loai_hinh_id":
                    d[truong] = KHAC
                elif truong == "don_vi.ma":
                    d["don_vi"]["ma"] = "TU-NHAP-DEMO"
                elif truong == "lich":
                    d["lich"][0]["ty_le"] = "31"
                else:
                    d["phi"][0]["muc"] = "0.6"
                self.luu(d)
                lech = self.m.luu[-1][0]["khac_tieu_chuan"]
                self.assertEqual([(x["truong"], x["nhan"]) for x in lech], [(truong, nhan)])
                sql, p = self.m.nk[-1]
                self.assertIn("CRM_BAO_GIA_KHAC_TIEU_CHUAN", sql)
                self.assertEqual(p[0], ME)
                self.assertEqual(json.loads(p[1]), {truong: lech[0]["tieu_chuan"]})
                self.assertEqual(json.loads(p[2])["khac_tieu_chuan"], lech)
                self.assertEqual(p[3], BG)

    def test_so_lich_so_dong_gia_tri_moc_thu_tu_ke_ca_nguon_khach(self):
        for sua in (lambda d: d["lich"].pop(), lambda d: d["lich"].reverse(),
                    lambda d: d["lich"][0].update(moc_su_kien="SO"),
                    lambda d: d["lich"][0].update(loai="AMOUNT", ty_le=None, so_tien="100")):
            d = bao_gia()
            sua(d)
            self.luu(d)
            self.assertIn("lich", [x["truong"] for x in self.m.luu[-1][0]["khac_tieu_chuan"]])

    def test_lich_o_thong_minh_va_so_khac_scale_van_khop(self):
        d = bao_gia()
        d["gia"].update(don_gia="120.00", dien_tich="100.000")
        d["phi"][0]["muc"] = "0.500"
        for r in d["lich"]:
            r["gia_tri_nhap"] = r["ty_le"] + ",00%"
            r["dong_id"] = str(uuid.uuid4())
            r["ghi_chu"] = "Ghi chú riêng DEMO"
        self.luu(d)
        self.assertEqual(self.m.luu[-1][0]["khac_tieu_chuan"], [])

    def test_lich_tien_typed_chuan_hoa_don_vi_nho_nhat(self):
        self.m.s["bo_chuan"]["rows"] = [{"lan": "1", "gia_tri_loai": "AMOUNT", "so_tien_minor": "12345", "tien_te": "USD",
                                          "moc_loai": "SU_KIEN", "moc_su_kien": "KY_HD"}]
        r = self.g.mac_dinh_bao_gia(ME, DA)
        self.assertEqual(r["lich"][0]["so_tien"], "123.45")
        d = bao_gia()
        d["lich"] = r["lich"]
        self.luu(d)
        self.assertNotIn("lich", [x["truong"] for x in self.m.luu[-1][0]["khac_tieu_chuan"]])

    def test_lo_id_lay_dien_tich_may_chu_truoc_tinh_va_ghi_nhan_nhap_khac(self):
        d = bao_gia()
        d["gia"]["dien_tich"], d["don_vi"]["ma"] = "999", "MA-GIA"
        self.luu(d)
        dl, t = self.m.luu[-1]
        self.assertEqual((dl["gia"]["dien_tich"], dl["don_vi"]["ma"], t["tong_minor"]), ("100", "L-DEMO", "312000000"))
        self.assertEqual(dl["don_vi"]["can_cu"], {"lo_id": LO, "anh_chup_sha256": "a" * 64})
        lech = next(x for x in dl["khac_tieu_chuan"] if x["truong"] == "gia.dien_tich")
        self.assertEqual((lech["tieu_chuan"], lech["bao_gia"], lech["gia_tri_luu"]), ("100", "999", "100"))

    def test_lo_id_khong_can_gui_ma_dien_tich(self):
        d = bao_gia()
        d.pop("don_vi")
        d["gia"].pop("dien_tich")
        self.luu(d)
        self.assertEqual(self.m.luu[-1][0]["khac_tieu_chuan"], [])

    def test_ma_lo_va_nhan_dot_la_chuoi_khong_phai_so(self):
        self.m.s["lo"][0]["ma"] = "001"
        d = bao_gia()
        d["don_vi"]["ma"] = "1"
        d["lich"][0]["lan"] = "01"
        self.luu(d)
        self.assertEqual([x["truong"] for x in self.m.luu[-1][0]["khac_tieu_chuan"]], ["don_vi.ma", "lich"])

    def test_tinh_thu_co_lo_id_cung_dien_tich_voi_luu_va_khong_ghi(self):
        d = bao_gia()
        d["gia"]["dien_tich"] = "999"
        self.m._mot = Mock(side_effect=[{"ok": True, "phap_nhan_id": KHAC, "phap_nhan": "PN_DEMO", "phap_nhan_ten": "DEMO",
                                        "loai_hinh": "LH_DEMO", "loai_hinh_ten": "Loại hình DEMO"}, {"ma": "DA_DEMO", "ten": "Dự án DEMO"}])
        r = self.g.xem_truoc(ME, du_lieu=d)
        self.assertEqual(r["tinh"]["tong_minor"], "312000000")
        self.assertEqual(r["khac_tieu_chuan"][0]["truong"], "gia.dien_tich")
        self.assertEqual((self.m.luu, self.m.nk), ([], []))

    def test_lo_sai_du_an_khong_trong_thieu_du_an_bi_tu_choi(self):
        for lo, da, code in ((str(uuid.UUID(int=99)), DA, "CRM_GK_YEU_CAU_SAI"), (KHAC, DA, "CRM_GK_TRANG_THAI"),
                             (BG, DA, "CRM_GK_TRANG_THAI"), (LH, DA, "CRM_GK_TRANG_THAI"), (LO, None, "CRM_GK_YEU_CAU_SAI")):
            with self.subTest(lo=lo, da=da):
                d = bao_gia()
                d.update(lo_id=lo, du_an_id=da)
                with self.assertRaises(DataError) as cm:
                    self.luu(d)
                self.assertEqual((cm.exception.code, cm.exception.locator), (code, "lo_id"))
                self.assertEqual((self.m.luu, self.m.nk), ([], []))

    def test_luu_du_an_ngung_ban_bi_tu_choi(self):
        self.m.s["trang_thai"] = "NGUNG_BAN"
        with self.assertRaisesRegex(DataError, "ngừng bán"):
            self.luu()
        self.assertEqual(self.m.luu, [])

    def test_nhap_cu_cung_du_an_ngung_ban_khong_lo_giu_tien_va_ghi_khac_chuan(self):
        d = bao_gia()
        d.pop("lo_id")
        d["gia"].update(don_gia="135", dien_tich="99")
        d["phi"][0]["muc"] = "0.6"
        self.luu(d)
        truoc, tinh_truoc = copy.deepcopy(self.m.luu[-1])
        self.g._bao_gia = Mock(return_value={"du_lieu": truoc, "trang_thai": "NHAP"})
        self.m.s.update(trang_thai="NGUNG_BAN", don_gia="999")
        self.m.s["phi"][0]["muc"] = "9"
        self.m.luu.clear()
        self.m.nk.clear()
        d["lich"] = copy.deepcopy(truoc["lich"])
        d["nguon_tieu_chuan"] = truoc["nguon_tieu_chuan"]

        r = self.g.luu(ME, bao_gia_id=BG, expected_revision=1, du_lieu=d, khoa="da3a-nhap-cu")

        self.assertEqual(r["bao_gia_id"], BG)
        dl, tinh = self.m.luu[-1]
        for truong in ("gia", "fx", "phi", "phi_bao_tri", "lich"):
            self.assertEqual(dl[truong], truoc[truong])
        self.assertEqual(tinh, tinh_truoc)
        self.assertIsNone(dl["nguon_tieu_chuan"])
        self.assertEqual(dl["khac_tieu_chuan"], [{"truong": "du_an_id", "nhan": "Dự án không có tiêu chuẩn đang bán",
                                                "tieu_chuan": None, "bao_gia": DA}])
        self.assertEqual(len(self.m.nk), 1)
        self.assertEqual(json.loads(self.m.nk[0][1][2])["khac_tieu_chuan"], dl["khac_tieu_chuan"])

    def test_tao_moi_du_an_ngung_ban_khong_lo_bi_tu_choi(self):
        self.m.s["trang_thai"] = "NGUNG_BAN"
        d = bao_gia()
        d.pop("lo_id")
        with self.assertRaisesRegex(DataError, "ngừng bán") as cm:
            self.luu(d)
        self.assertEqual((cm.exception.code, cm.exception.locator), ("CRM_GK_TRANG_THAI", "du_an_id"))
        self.assertEqual((self.m.luu, self.m.nk), ([], []))

    def test_nhap_cu_doi_sang_du_an_ngung_ban_bi_tu_choi(self):
        self.m.s["trang_thai"] = "NGUNG_BAN"
        d = bao_gia()
        d.pop("lo_id")
        truoc = {**d, "du_an_id": KHAC}
        self.g._bao_gia = Mock(return_value={"du_lieu": truoc, "trang_thai": "NHAP"})
        with self.assertRaisesRegex(DataError, "ngừng bán") as cm:
            self.g.luu(ME, bao_gia_id=BG, expected_revision=1, du_lieu=d, khoa="da3a-doi-du-an")
        self.assertEqual((cm.exception.code, cm.exception.locator), ("CRM_GK_TRANG_THAI", "du_an_id"))
        self.assertEqual((self.m.luu, self.m.nk), ([], []))

    def test_nhap_cu_cung_du_an_ngung_ban_co_lo_bi_tu_choi(self):
        self.m.s["trang_thai"] = "NGUNG_BAN"
        d = bao_gia()
        self.g._bao_gia = Mock(return_value={"du_lieu": copy.deepcopy(d), "trang_thai": "NHAP"})
        with self.assertRaisesRegex(DataError, "ngừng bán") as cm:
            self.g.luu(ME, bao_gia_id=BG, expected_revision=1, du_lieu=d, khoa="da3a-nhap-co-lo")
        self.assertEqual((cm.exception.code, cm.exception.locator), ("CRM_GK_TRANG_THAI", "du_an_id"))
        self.assertEqual((self.m.luu, self.m.nk), ([], []))

    def test_ma_go_tay_va_dien_tich_so_voi_danh_muc(self):
        d = bao_gia()
        d.pop("lo_id")
        d["gia"]["dien_tich"] = "99"
        self.luu(d)
        self.assertEqual([x["truong"] for x in self.m.luu[-1][0]["khac_tieu_chuan"]], ["gia.dien_tich"])
        d["don_vi"]["ma"] = "NGOAI-DANH-MUC"
        self.luu(d)
        self.assertEqual([x["truong"] for x in self.m.luu[-1][0]["khac_tieu_chuan"]], ["don_vi.ma"])

    def test_phi_thieu_them_va_phi_bao_tri_cu(self):
        d = bao_gia()
        d.pop("phi")
        d["phi_bao_tri"] = {"gia_tri": "99", "tien_te": "VND", "co_so": "Riêng DEMO"}
        self.luu(d)
        self.assertEqual([x["truong"] for x in self.m.luu[-1][0]["khac_tieu_chuan"]], ["phi", "phi_bao_tri"])

    def test_khong_nhan_phi_sai_dang(self):
        for phi in ({}, [{"ten": "DEMO"}], [{**PHI[0], "muc": "-1"}], [{**PHI[0], "actor": ME}]):
            d = bao_gia()
            d["phi"] = phi
            with self.assertRaises(DataError):
                self.luu(d)
        self.assertEqual(self.m.lenh, [])

    def test_nhat_ky_loi_rollback_revision(self):
        d = bao_gia()
        d["gia"]["don_gia"] = "121"
        self.m.loi_nk = True
        with self.assertRaisesRegex(RuntimeError, "Nhật ký"):
            self.luu(d)
        self.assertEqual((self.m.luu, self.m.nk), ([], []))

    def test_replay_khong_doc_lai_chuan_khong_ghi_nhat_ky(self):
        self.g._tra.return_value = {**self.m.kq, "lap_lai": True}
        r = self.luu()
        self.assertTrue(r["lap_lai"])
        self.assertEqual(self.m.lenh, [])
        self.g._tra.return_value = None
        self.m.sql_replay = True
        d = bao_gia()
        d["gia"]["don_gia"] = "121"
        self.assertTrue(self.luu(d)["lap_lai"])
        self.assertEqual(self.m.nk, [])

    def test_hash_yeu_cau_khong_tin_metadata_khach_va_khong_phu_thuoc_chuan(self):
        d = bao_gia()
        self.luu(d)
        h1 = self.g._tra.call_args.args[-1]
        d.update(nguon_tieu_chuan={"ngay": "1900-01-01"}, khac_tieu_chuan=[])
        self.m.s["don_gia"], self.m.s["anh_chup_sha256"] = "121", "b" * 64
        self.luu(d)
        self.assertEqual(h1, self.g._tra.call_args.args[-1])
        self.assertEqual(self.m.luu[-1][0]["nguon_tieu_chuan"]["anh_chup_sha256"], "b" * 64)

    def test_bao_gia_cu_khong_co_nguon_doc_nguyen(self):
        cu = G.chuan_hoa_bao_gia(bao_gia())
        cu.pop("tien_chinh")
        b = dict.fromkeys(("so_bao_gia", "ngay", "trang_thai", "tao_boi", "tao_luc", "revision_hien_hanh", "hop_dong_id", "huy_ly_do", "huy_boi",
                           "tinh", "g7", "khach_ten"))
        b.update(id=BG, loai_hinh_id=LH, du_lieu=cu)
        self.g._bao_gia = Mock(return_value=b)
        self.m._nhieu = Mock(return_value=[])
        self.m._mot = Mock(side_effect=[{"r": None}, None])
        r = self.g.chi_tiet(ME, BG)
        self.assertEqual(r["du_lieu"], cu)
        self.assertNotIn("nguon_tieu_chuan", r["du_lieu"])
        self.assertEqual(self.m.lenh, [])

    def test_bao_gia_du_an_chua_bat_ban_giu_hop_dong_cu(self):
        self.m.s["trang_thai"] = "CHUA_BAT_BAN"
        d = bao_gia()
        d.pop("lo_id")
        self.luu(d)
        self.assertNotIn("nguon_tieu_chuan", self.m.luu[-1][0])


@unittest.skipUnless(os.environ.get("KTT_DA3A_KET_NOI"), "NOT_VERIFIED: thiếu KTT_DA3A_KET_NOI — PostgreSQL thật chưa chạy")
class MacDinhPostgres(unittest.TestCase):
    """Lead chạy riêng trên DEMO đã chuẩn bị; cùng chủ bảng/app, không migration, không xóa."""

    @classmethod
    def setUpClass(cls):
        from psycopg.rows import dict_row
        from kho_tri_thuc.giao_dien.server import LocalApp
        from kho_tri_thuc.k2.crm_khoi_dong import chuan_hoa_dsn, doc_ket_noi, nap_driver
        from kho_tri_thuc.k2.crm_mau import CrmMauK2
        kn = doc_ket_noi(Path(os.environ["KTT_DA3A_KET_NOI"]))
        pg = nap_driver()
        cls.admin = pg.connect(chuan_hoa_dsn(kn["admin_dsn"])["conninfo"], autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(cls.admin.close)
        cls.app = pg.connect(chuan_hoa_dsn(kn["app_dsn"])["conninfo"], autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(cls.app.close)
        if cls.admin.execute("SELECT max(version) AS v FROM master.schema_migrations").fetchone()["v"] < 31:
            raise AssertionError("NOT_VERIFIED: cần DEMO schema >= 31")
        cls.db = staticmethod(LocalApp._crm_db)
        cls.m = CrmMauK2(cls.app, Path("."), conn_tin_cay=cls.admin)
        cls.g, cls.da = G.CrmGiaoKetK2(cls.m), CrmDuAnBanK2(cls.m)

    def test_pg_luu_nguon_lo_so_chuan_nhat_ky_replay_va_tu_choi(self):
        q, run = self.admin.execute, uuid.uuid4().hex[:10].upper()
        pn = q("SELECT id FROM master.phap_nhan WHERE ma = 'PN_DEMO_A'").fetchone()["id"]
        lh = q("SELECT id::text AS id FROM master.loai_hinh_doanh_thu WHERE phap_nhan_id = %s AND valid_to IS NULL ORDER BY ma LIMIT 1", (pn,)).fetchone()["id"]
        ids = [q("INSERT INTO master.du_an (phap_nhan_id, ma_junsky, ten) VALUES (%s, %s, %s) RETURNING id::text AS id",
                 (pn, f"DA3A_DEMO_{run}_{i}", "Dự án kiểm thử DA-3a DEMO")).fetchone()["id"] for i in range(2)]
        for i, da_id in enumerate(ids):
            r = self.db(lambda: self.da.bat_ban(ME, du_an_id=da_id,
                       thong_tin={"don_gia_niem_yet": "120", "tien_te": "USD", "loai_hinh_id": lh, "giai_doan_g7": "GD1"}, phi=PHI, khoa=f"da3a-{run}-bat-{i}"))
            self.db(lambda: self.da.ghi_lo(ME, da_ban_id=r["da_ban_id"], lo=[{"ma": "L-DEMO", "dien_tich": "100"},
                          {"ma": "GIU-DEMO", "dien_tich": "200", "trang_thai": "GIU_CHO"}], khoa=f"da3a-{run}-lo-{i}"))
        ac = self.db(lambda: self.da.anh_chup_mac_dinh(ME, ids[0]))
        lot = next(x for x in ac["lo"] if x["trang_thai"] == "CON_TRONG")
        mac_dinh = self.db(lambda: self.g.mac_dinh_bao_gia(ME, ids[0]))
        self.assertEqual(len(mac_dinh["lo"]), 1)
        d = bao_gia()
        d.update(loai_hinh_id=lh, du_an_id=ids[0], lo_id=lot["id"], nguon_tieu_chuan={"anh_chup_sha256": "giả"})
        d["gia"]["dien_tich"], d["gia"]["don_gia"] = "999", "121"
        key = f"da3a-{run}-bg"
        r = self.db(lambda: self.g.luu(ME, bao_gia_id=None, expected_revision=None, du_lieu=d, khoa=key))
        saved = self.db(lambda: self.g.chi_tiet(ME, r["bao_gia_id"]))["du_lieu"]
        self.assertEqual(saved["nguon_tieu_chuan"]["anh_chup_sha256"], ac["anh_chup_sha256"])
        self.assertEqual(saved["gia"]["dien_tich"], "100")
        self.assertIn("gia.don_gia", [x["truong"] for x in saved["khac_tieu_chuan"]])
        nk = q("SELECT nguoi, truoc, sau FROM nhat_ky.su_kien WHERE doi_tuong_id = %s::uuid AND hanh_dong = 'CRM_BAO_GIA_KHAC_TIEU_CHUAN'", (r["bao_gia_id"],)).fetchall()
        self.assertEqual((len(nk), nk[0]["nguoi"], nk[0]["truoc"]["gia.don_gia"]), (1, ME, "120"))
        self.assertTrue(self.db(lambda: self.g.luu(ME, bao_gia_id=None, expected_revision=None, du_lieu=d, khoa=key))["lap_lai"])
        self.assertEqual(q("SELECT count(*) AS n FROM nhat_ky.su_kien WHERE doi_tuong_id = %s::uuid AND hanh_dong = 'CRM_BAO_GIA_KHAC_TIEU_CHUAN'", (r["bao_gia_id"],)).fetchone()["n"], 1)
        other = self.db(lambda: self.da.anh_chup_mac_dinh(ME, ids[1]))
        for lo_id in (other["lo"][0]["id"], next(x["id"] for x in ac["lo"] if x["trang_thai"] == "GIU_CHO")):
            d["lo_id"] = lo_id
            with self.assertRaises(DataError):
                self.db(lambda: self.g.luu(ME, bao_gia_id=r["bao_gia_id"], expected_revision=1, du_lieu=d, khoa=f"da3a-{run}-sai-{lo_id}"))
        self.assertEqual(self.db(lambda: self.g.chi_tiet(ME, r["bao_gia_id"]))["bao_gia"]["revision_hien_hanh"], 1)


if __name__ == "__main__":
    unittest.main()
