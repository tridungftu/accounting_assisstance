"""MDA-4a: S1 mốc riêng dự án; mock thuần và PG DEMO mới do lead chạy.

Fixture PG tạo lịch trong giao dịch duyệt, giữ nguyên trigger/quyền; không
mở server, không DROP/DELETE. Thiếu KHO_PG_DSN_TEST hoặc psycopg thì skip.
"""

import copy
import json
import os
import unittest
import uuid
from datetime import date, timedelta
from pathlib import Path

from kho_tri_thuc.k2.crm_s1 import CrmDanhSachK2, _dong

NGAY = date(2026, 10, 25)
MA = "SU_KIEN:DAM-11111111-2222-4333-8444-555555555555"


def dot(**kw):
    return {"dot": 1, "han": None, "moc": MA + "_3", "so_tien_minor": "100",
            "da_thu_minor": "0", "tien_te": "VND", "moc_ngay_du_kien": "2026-10-20",
            "moc_ngay_thuc_te": None, **kw}


def dong(*lich, **kw):
    return {"id": "HD-MDA-4A-DEMO", "trang_thai": "HIEU_LUC", "xem_tien": True,
            "gia_tri_minor": "100", "tien_te": "VND", "lich": list(lich), **kw}


class MocGiaLap(unittest.TestCase):
    def test_du_kien_da_qua_cong_n_khong_qua_han_khong_w5(self):
        for moc, han in ((MA, "2026-10-20"), (MA + "_3", "2026-10-23")):
            with self.subTest(moc=moc):
                raw = dong(dot(moc=moc))
                truoc = copy.deepcopy(raw)
                r = _dong(raw, NGAY)
                self.assertEqual(r["dot_ke_tiep"], {"dot": 1, "han": None, "moc": moc,
                                 "han_du_kien": han, "trang_thai": "MOC_DU_KIEN"})
                self.assertNotIn("QUA_HAN", r["co"])
                self.assertEqual(r["viec"]["W5"], 0)
                self.assertEqual(raw, truoc)

    def test_du_kien_trong_bay_ngay_cung_khong_w5(self):
        for ngay in (NGAY, NGAY + timedelta(days=7)):
            r = _dong(dong(dot(moc=MA, moc_ngay_du_kien=ngay)), NGAY)
            self.assertEqual(r["dot_ke_tiep"]["han_du_kien"], ngay.isoformat())
            self.assertEqual(r["viec"]["W5"], 0)
            self.assertNotIn("QUA_HAN", r["co"])

    def test_thuc_te_cong_n_qua_han(self):
        for moc, han in ((MA, "2026-10-20"), (MA + "_3", "2026-10-23")):
            with self.subTest(moc=moc):
                r = _dong(dong(dot(moc=moc, moc_ngay_thuc_te="2026-10-20")), NGAY)
                self.assertEqual(r["dot_ke_tiep"]["han"], han)
                self.assertIsNone(r["dot_ke_tiep"]["han_du_kien"])
                self.assertEqual(r["dot_ke_tiep"]["trang_thai"], "CO_NGAY")
                self.assertEqual(r["co"].count("QUA_HAN"), 1)
                self.assertEqual(r["viec"]["W5"], 0)

    def test_thuc_te_w5_bien_va_da_thu(self):
        for han, thu, w5, qua in ((-1, "0", 0, True), (0, "0", 1, False),
                                  (7, "0", 1, False), (8, "0", 0, False), (-1, "100", 0, False)):
            with self.subTest(han=han, thu=thu):
                r = _dong(dong(dot(moc_ngay_thuc_te=NGAY + timedelta(days=han - 3), da_thu_minor=thu)), NGAY)
                self.assertEqual(r["viec"]["W5"], w5)
                self.assertEqual("QUA_HAN" in r["co"], qua)
                if thu == "100":
                    self.assertIsNone(r["dot_ke_tiep"])

    def test_sap_xep_han_thuc_te_nhu_han_co_dinh(self):
        r = _dong(dong(dot(dot=1, moc_ngay_du_kien="2026-01-01"),
                       dot(dot=2, han="2026-10-24"), dot(dot=3, moc_ngay_thuc_te="2026-10-20")), NGAY)
        self.assertEqual((r["dot_ke_tiep"]["dot"], r["dot_ke_tiep"]["han"]), (3, "2026-10-23"))

    def test_moc_chuan_khong_doi_du_co_du_lieu_moc_rieng(self):
        for han in (None, "2026-10-24"):
            r = _dong(dong(dot(moc="SU_KIEN:KY_HD", han=han, moc_ngay_thuc_te="2026-10-20")), NGAY)
            self.assertEqual(r["dot_ke_tiep"]["han"], han)
            self.assertIsNone(r["dot_ke_tiep"]["han_du_kien"])
            self.assertEqual(r["dot_ke_tiep"]["trang_thai"], "CO_NGAY" if han else "MOC_CHUA_CO_NGAY")
            self.assertEqual("QUA_HAN" in r["co"], bool(han))

    def test_han_co_dinh_uu_tien_truoc_moc(self):
        r = _dong(dong(dot(han="2026-10-25", moc_ngay_thuc_te="2026-10-20")), NGAY)
        self.assertEqual(r["dot_ke_tiep"]["han"], "2026-10-25")
        self.assertIsNone(r["dot_ke_tiep"]["han_du_kien"])
        self.assertEqual(r["viec"]["W5"], 1)
        self.assertNotIn("QUA_HAN", r["co"])

    def test_moc_ngung_hoac_khong_tim_thay_khong_co_ngay(self):
        # LEFT JOIN không trả ngày của mốc ngừng/không tồn tại/ngoài dự án.
        r = _dong(dong(dot(moc_ngay_du_kien=None)), NGAY)
        self.assertEqual(r["dot_ke_tiep"]["trang_thai"], "MOC_CHUA_CO_NGAY")
        self.assertIsNone(r["dot_ke_tiep"]["han"])
        self.assertIsNone(r["dot_ke_tiep"]["han_du_kien"])
        self.assertNotIn("QUA_HAN", r["co"])
        self.assertEqual(r["viec"]["W5"], 0)

    def test_khong_quyen_xem_tien_khong_lo_ngay_moc(self):
        r = _dong(dong(dot(moc_ngay_thuc_te="2026-10-20"), xem_tien=False), NGAY)
        self.assertIsNone(r["dot_ke_tiep"])
        self.assertIsNone(r["viec"]["W5"])
        self.assertNotIn("QUA_HAN", r["co"])
        self.assertNotIn("moc_ngay_", json.dumps(r))


try:
    import psycopg
except ImportError:
    psycopg = None


@unittest.skipUnless(os.environ.get("KHO_PG_DSN_TEST") and psycopg is not None,
                     "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PostgreSQL")
class MocPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict, make_conninfo
        from psycopg.rows import dict_row
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.k2 import crm_demo, crm_du_an_ban as D
        from kho_tri_thuc.k2.crm_mau import CrmMauK2

        cfg = conninfo_to_dict(os.environ["KHO_PG_DSN_TEST"])
        if cfg.get("host") not in ("localhost", "127.0.0.1", "::1"):
            raise unittest.SkipTest("S1 chỉ chạy PostgreSQL cục bộ DEMO")
        cls.db = "kho_test_mda4a_" + uuid.uuid4().hex[:12]
        with psycopg.connect(make_conninfo(**cfg), autocommit=True) as c:
            c.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cfg["dbname"] = cls.db
        cls.c = psycopg.connect(make_conninfo(**cfg), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        pg.migrate(cls.c)
        crm_demo.khoi_tao(cls.c)
        seed = D.khoi_tao_demo(cls.c, hom_nay=NGAY)
        if seed["trang_thai"] != "DA_TAO":
            raise AssertionError(seed)
        cls.c.row_factory = dict_row
        cls.m = CrmMauK2(cls.c, Path(__file__).parent, conn_tin_cay=cls.c, hom_nay=lambda: NGAY)
        cls.da = D.CrmDuAnBanK2(cls.m)
        cls.s1 = CrmDanhSachK2(cls.m)

    def test_du_kien_khong_qua_han_ghi_thuc_te_vao_dung_mot_hop_dong(self):
        c, m = self.c, self.m
        da = c.execute("""SELECT d.id::text AS da_ban_id, d.du_an_id, d.phap_nhan_id
            FROM master.crm_da_ban d JOIN master.du_an a ON a.id = d.du_an_id
            WHERE a.ma_junsky = 'DA_KCN_DEMO'""").fetchone()
        moc = self.da.moc_ghi("MO_PHONG_BAN_HANG", da_ban_id=da["da_ban_id"],
                             moc={"ten": "Mốc S1 MDA-4a DEMO", "ngay_du_kien": "2026-10-20"}, khoa="mda4a-khai")
        ma = "SU_KIEN:" + moc["ma"] + "_3"
        # Fixture projection: kiểm KT rồi duyệt CFO, sinh một lịch cùng giao dịch
        # duyệt theo trigger hiện hành; không mock bất kỳ truy vấn đọc S1 nào.
        with m._tx(m.danh_tinh("MO_PHONG_KT_A")):
            hd = c.execute("""INSERT INTO master.hop_dong
                (phap_nhan_id, du_an_id, loai, ma_noi_bo, so_hop_dong, gia_tri_minor, tien_te)
                VALUES (%s, %s, 'THUE_DAT', 'HD-MDA-4A-DEMO', 'HD-MDA-4A-DEMO', 100, 'VND') RETURNING id""",
                           (da["phap_nhan_id"], da["du_an_id"])).fetchone()["id"]
            pb = c.execute("""INSERT INTO master.hop_dong_phien_ban
                (hop_dong_id, phien_ban, nguon, tao_boi, ngay_hieu_luc, valid_from)
                VALUES (%s, 1, 'TAY', 'MO_PHONG_KT_A', %s, %s::date::timestamp AT TIME ZONE 'UTC') RETURNING id""",
                           (hd, NGAY, NGAY)).fetchone()["id"]
            c.execute("""UPDATE master.hop_dong_phien_ban SET kiem_boi = 'MO_PHONG_KT_A',
                kiem_luc = now(), kiem_van_tay = master.van_tay_phien_ban(id) WHERE id = %s""", (pb,))
        with m._tx(m.danh_tinh("MO_PHONG_CFO")):
            c.execute("""UPDATE master.hop_dong_phien_ban SET trang_thai = 'DA_DUYET',
                nguoi_duyet = 'MO_PHONG_CFO', duyet_luc = now() WHERE id = %s""", (pb,))
            c.execute("""INSERT INTO master.lich_thu
                (phien_ban_id, phap_nhan_id, dot, moc, so_tien_minor, tien_te, khoa_nghia_vu)
                VALUES (%s, %s, 1, %s, 100, 'VND', 'MDA-4A-DEMO-DOT-1')""", (pb, da["phap_nhan_id"], ma))
            c.execute("""UPDATE master.hop_dong SET phien_ban_hien_hanh = %s,
                trang_thai = 'HIEU_LUC' WHERE id = %s""", (pb, hd))

        loc = {"tim": "HD-MDA-4A-DEMO"}
        r = self.s1.danh_sach("MO_PHONG_KT_A", loc)
        self.assertEqual(r["tong"], 1)
        self.assertEqual(r["hop_dong"][0]["dot_ke_tiep"],
                         {"dot": 1, "han": None, "moc": ma, "han_du_kien": "2026-10-23", "trang_thai": "MOC_DU_KIEN"})
        self.assertNotIn("QUA_HAN", r["hop_dong"][0]["co"])
        self.assertEqual(r["the_so"]["W5"]["so_luong"], 0)
        self.assertEqual(self.s1.danh_sach("MO_PHONG_KT_A", {**loc, "co": "QUA_HAN"})["tong"], 0)
        self.assertEqual(self.s1.danh_sach("MO_PHONG_KT_A", {**loc, "the": "W5"})["tong"], 0)

        moc = self.da.moc_ghi("MO_PHONG_BAN_HANG", da_ban_id=da["da_ban_id"],
                             moc={"moc_id": moc["moc_id"], "expected_lan": moc["lan"],
                                  "ngay_thuc_te": "2026-10-20"}, khoa="mda4a-thuc-te")
        r = self.s1.danh_sach("MO_PHONG_KT_A", {**loc, "co": "QUA_HAN"})
        self.assertEqual((r["tong"], len(r["hop_dong"])), (1, 1))
        h = r["hop_dong"][0]
        self.assertEqual(h["id"], str(hd))
        self.assertEqual(h["co"].count("QUA_HAN"), 1)
        self.assertEqual((h["dot_ke_tiep"]["han"], h["dot_ke_tiep"]["trang_thai"]), ("2026-10-23", "CO_NGAY"))
        self.assertIsNone(h["dot_ke_tiep"]["han_du_kien"])

        moc = self.da.moc_ghi("MO_PHONG_BAN_HANG", da_ban_id=da["da_ban_id"],
                             moc={"moc_id": moc["moc_id"], "expected_lan": moc["lan"], "ngay_thuc_te": "2026-10-22"},
                             ly_do="Chỉnh ngày DEMO để kiểm W5", khoa="mda4a-den-han")
        r = self.s1.danh_sach("MO_PHONG_KT_A", {**loc, "the": "W5"})
        self.assertEqual((r["tong"], r["the_so"]["W5"]["so_luong"]), (1, 1))
        self.assertEqual(r["hop_dong"][0]["dot_ke_tiep"]["han"], NGAY.isoformat())
        self.assertNotIn("QUA_HAN", r["hop_dong"][0]["co"])

        self.da.moc_ghi("MO_PHONG_BAN_HANG", da_ban_id=da["da_ban_id"],
                       moc={"moc_id": moc["moc_id"], "expected_lan": moc["lan"], "dang_dung": False}, khoa="mda4a-ngung")
        r = self.s1.danh_sach("MO_PHONG_KT_A", loc)
        self.assertEqual(r["hop_dong"][0]["dot_ke_tiep"]["trang_thai"], "MOC_CHUA_CO_NGAY")
        self.assertEqual(r["the_so"]["W5"]["so_luong"], 0)


if __name__ == "__main__":
    unittest.main()
