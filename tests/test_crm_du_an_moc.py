"""MDA-1b — service/HTTP giả lập; PostgreSQL chỉ chạy khi lead cấp DSN test."""

from __future__ import annotations

import json
import os
import unittest
import uuid
from contextlib import nullcontext
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from kho_tri_thuc.giao_dien import crm_g as CG
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import crm_du_an_ban as D
from kho_tri_thuc.k2.crm_giao_ket import danh_muc_moc_chuan
from kho_tri_thuc.k2.crm_mau import CrmMauK2, _h
from tests import test_crm_du_an_ban as T

DA, DB, MID, ME = T.DA, T.DB, T.LH, T.ME


def moc(**kw):
    return {"ten": "Xong chứng nhận đầu tư DEMO", "ten_tat": "CNĐT", "ngay_du_kien": "24/11/2026", **kw}


def dong(tt="QUA_DU_KIEN", **kw):
    return {"moc_id": MID, "ma": "DAM-" + MID, "lan": 1, "ten": "Xong chứng nhận đầu tư DEMO", "ten_tat": "CNĐT",
            "ngay_du_kien": "2026-10-20", "ngay_thuc_te": None, "trang_thai": tt, **kw}


class Service(unittest.TestCase):
    def setUp(self):
        self.m = T._Mau()
        self.s = D.CrmDuAnBanK2(self.m)

    def ghi(self, nd, **kw):
        return self.s.moc_ghi(ME, da_ban_id=DB, moc=nd, khoa="moc-demo", **kw)

    def test_ngay_viet_sang_iso_va_hash_khong_gom_khoa(self):
        self.ghi(moc(ten="  Mốc DEMO  ", ngay_thuc_te="25/10/2026"), ly_do="  Lý do DEMO  ")
        self.s.moc_ghi(ME, da_ban_id=DB, moc=moc(ten="Mốc DEMO", ngay_du_kien="2026-11-24", ngay_thuc_te="2026-10-25"),
                       khoa="moc-demo-khac", ly_do="Lý do DEMO")
        (sql, p), (_, p2) = self.m.lenh
        self.assertIn("master.crm_da_moc_ghi(%s, %s, %s::uuid, %s::jsonb, %s)", sql)
        nd = json.loads(p[3])
        self.assertEqual((p[0], p[2], p[4]), ("moc-demo", DB, "Lý do DEMO"))
        self.assertEqual((nd["ten"], nd["ngay_du_kien"], nd["ngay_thuc_te"]), ("Mốc DEMO", "2026-11-24", "2026-10-25"))
        self.assertEqual(p[1], p2[1])
        self.assertEqual(p[1], _h("CRM_DA_MOC", {"da_ban_id": DB, "moc": nd, "ly_do": p[4]}))

    def test_loi_theo_truong_truoc_sql(self):
        cases = [(None, "moc"), (moc(actor="DEMO"), "moc.actor"), (moc(ten="x" * 121), "moc.ten"),
                 (moc(ten_tat="x" * 21), "moc.ten_tat"), (moc(ten=" "), "moc.ten"),
                 (moc(ngay_du_kien=None), "moc.ngay_du_kien"), (moc(ngay_du_kien="31/02/2026"), "moc.ngay_du_kien"),
                 (moc(ngay_du_kien="20261025"), "moc.ngay_du_kien"), (moc(ngay_thuc_te=20261025), "moc.ngay_thuc_te"),
                 (moc(ngay_thuc_te="26/10/2026"), "moc.ngay_thuc_te"),
                 (moc(moc_id="sai"), "moc.moc_id"), (moc(dang_dung="true"), "moc.dang_dung")]
        for n in (None, True, False, "1", 0, -1, 1.5, 1_000_000_000):
            cases.append(({"moc_id": MID, "expected_lan": n, "ten": "Mốc DEMO"}, "moc.expected_lan"))
        for nd, truong in cases:
            with self.subTest(nd=nd), self.assertRaises(DataError) as cm:
                self.ghi(nd)
            self.assertEqual(cm.exception.locator, truong)
        for ly in (True, "x" * 1001):
            with self.assertRaises(DataError) as cm:
                self.ghi(moc(), ly_do=ly)
            self.assertEqual(cm.exception.locator, "ly_do")
        self.assertEqual(self.m.lenh, [])

    def test_sua_giu_truong_vang_va_null_tuong_minh(self):
        self.ghi({"moc_id": MID, "expected_lan": 2, "ngay_thuc_te": None, "ten_tat": "", "dang_dung": False}, ly_do="Bỏ ghi nhầm DEMO")
        nd = json.loads(self.m.lenh[0][1][3])
        self.assertEqual(nd, {"moc_id": MID, "expected_lan": 2, "ngay_thuc_te": None, "ten_tat": None, "dang_dung": False})

    def test_ds_trang_thai_ngay_va_viec_cho(self):
        self.m.c = T._C([dong(), dong("CHUA_DEN", ngay_du_kien="2026-10-25"), dong("DA_XONG", ngay_thuc_te="2026-10-24")])
        r = self.s.moc_ds(ME, DA)
        self.assertEqual(self.m.c.goi, [("SELECT master.crm_da_moc_doc(%s::uuid, %s::date) AS r", (DA, "2026-10-25"))])
        self.assertEqual(r["so_viec_cho"], 1)
        self.assertEqual([x["viec_cho"] for x in r["moc"]], [True, False, False])
        self.assertEqual([x["trang_thai_hien_thi"] for x in r["moc"]],
                         ["Quá ngày dự kiến — cần chỉnh ngày", "Chưa đến ngày dự kiến", "Đã xong"])
        self.assertEqual(r["moc"][0]["ngay_du_kien_hien_thi"], "20/10/2026")
        self.assertIsNone(r["moc"][0]["ngay_thuc_te_hien_thi"])
        self.assertEqual(r["moc"][2]["ngay_thuc_te_hien_thi"], "24/10/2026")
        self.m.c = T._C([])
        self.assertEqual(self.s.moc_ds(ME, DA)["so_viec_cho"], 0)

    def test_lich_su_nhan_va_cu_moi(self):
        cu, moi = {"ngay_du_kien": "2026-10-20", "ngay_thuc_te": None}, {"ngay_du_kien": "2026-11-24", "ngay_thuc_te": "2026-10-25"}
        labels = {"CRM_DA_MOC_KHAI": "Khai mốc", "CRM_DA_MOC_CHINH_DU_KIEN": "Chỉnh ngày dự kiến",
                  "CRM_DA_MOC_THUC_TE": "Ghi ngày thực tế", "CRM_DA_MOC_SUA": "Sửa mốc"}
        original = {"moc_id": MID, "lich_su": [{**moi, "lan": 2, "hieu_luc_tu": "2026-10-25", "hieu_luc_den": None}],
                    "nhat_ky": [{"hanh_dong": k, "truoc": cu, "sau": moi, "luc": "2026-10-25T08:30:00+07:00"} for k in labels]}
        self.m.c = T._C(original)
        r = self.s.moc_lich_su(ME, MID)
        self.assertEqual(self.m.c.goi[0][1], (MID,))
        self.assertIn("master.crm_da_moc_ls_doc", self.m.c.goi[0][0])
        self.assertEqual([x["hanh_dong_hien_thi"] for x in r["nhat_ky"]], list(labels.values()))
        self.assertEqual(r["lich_su"][0]["hieu_luc_tu_hien_thi"], "25/10/2026")
        k = r["nhat_ky"][0]
        self.assertEqual((k["truoc_hien_thi"]["ngay_du_kien_hien_thi"], k["sau_hien_thi"]["ngay_du_kien_hien_thi"]), ("20/10/2026", "24/11/2026"))
        self.assertEqual(k["sau_hien_thi"]["ngay_thuc_te_hien_thi"], "25/10/2026")
        self.assertEqual(k["luc_hien_thi"], "25/10/2026")
        self.assertNotIn("ngay_du_kien_hien_thi", original["nhat_ky"][0]["sau"])

    def test_danh_muc_co_ban_khong_csdl(self):
        with patch.object(self.m, "danh_tinh", side_effect=AssertionError("Không được gọi CSDL")):
            self.assertEqual(self.s.danh_muc_moc(ME), danh_muc_moc_chuan())
        self.assertEqual(self.m.c.goi, [])

    def test_danh_muc_gop_rieng_va_tham_so(self):
        self.m.c = T._C([dong()])
        r, base = self.s.danh_muc_moc(ME, DA), danh_muc_moc_chuan()
        self.assertEqual(r["moc"][:-1], base["moc"])
        self.assertEqual(r["moc_tham_so"][:-1], base["moc_tham_so"])
        self.assertEqual(r["moc"][-1], {"ma": "DAM-" + MID, "nhan": dong()["ten"], "ten_tat": "CNĐT",
                                         "du_kien": "2026-10-20", "thuc_te": None, "rieng": True})
        self.assertEqual(r["moc_tham_so"][-1], {"mau_ma": "DAM-" + MID + "_<n>", "nhan": dong()["ten"] + " + n ngày", "tham_so": "n", "toi_thieu": 1})
        self.assertEqual(self.s.danh_muc_moc(ME), base)  # không tích lũy giữa các lần gọi


class Http(unittest.TestCase):
    def goi(self, post, url, body=None, da=None):
        da = da if da is not None else T._Da()
        h, app = T._H(url, body), T._App(da)
        path = urlsplit(url)
        CG.dieu_huong(h, app, post, path.path, parse_qs(path.query))
        return h, da

    def test_ba_route_va_danh_muc_theo_du_an(self):
        body = {"da_ban_id": DB, "moc": moc(), "ly_do": "DEMO", "khoa": "http-moc"}
        for post, url, nd, ham, args, kw in (
            (False, f"/api/crm/du-an-ban/moc?du_an_id={DA}", None, "moc_ds", (ME, DA), {}),
            (False, f"/api/crm/du-an-ban/moc/{MID}/lich-su", None, "moc_lich_su", (ME, MID), {}),
            (True, "/api/crm/du-an-ban/moc", body, "moc_ghi", (ME,), body),
            (False, f"/api/crm/bao-gia/moc-chuan?du_an_id={DA}", None, "danh_muc_moc", (ME, DA), {})):
            with self.subTest(url=url):
                self.assertTrue(CG.la_route(post, urlsplit(url).path))
                h, da = self.goi(post, url, nd)
                self.assertEqual((h.st, da.goi), (200, [(ham, args, kw)]))

    def test_danh_muc_khong_du_an_giu_nguyen(self):
        with patch.object(CG, "dich_vu_da", side_effect=AssertionError("Không khởi tạo kết nối")):
            h, _ = self.goi(False, "/api/crm/bao-gia/moc-chuan")
        self.assertEqual((h.st, h.data), (200, danh_muc_moc_chuan()))

    def test_query_sai_la_lap_va_rong(self):
        for base in ("/api/crm/du-an-ban/moc", "/api/crm/bao-gia/moc-chuan"):
            for q in ("du_an_id=sai", "du_an_id=", f"du_an_id={DA}&du_an_id={DB}", "actor=DEMO", "la="):
                h, da = self.goi(False, base + "?" + q)
                self.assertEqual((h.st, da.goi), (400, []))
        for url, post in ((f"/api/crm/du-an-ban/moc/{MID}/lich-su?x=1", False), ("/api/crm/du-an-ban/moc?x=1", True)):
            h, da = self.goi(post, url, {})
            self.assertEqual((h.st, da.goi), (400, []))

    def test_loi_csdl_409_va_400_theo_truong(self):
        for ma, status, truong in (("CRM_DA_MOC_LAN_CU", 409, "moc.expected_lan"), ("CRM_DA_MOC_CAN_LY_DO", 400, "ly_do"),
                                  ("CRM_DA_MOC_TRUNG", 400, "moc.ten"), ("CRM_DA_MOC_NGAY_SAI", 400, "moc.ngay_thuc_te"),
                                  ("CRM_DA_MOC_SAI", 400, "moc")):
            h, _ = self.goi(True, "/api/crm/du-an-ban/moc", {"da_ban_id": DB, "moc": moc(), "khoa": "k"}, T._Da(DataError(ma, "Lỗi DEMO")))
            self.assertEqual((h.st, h.data["error"], h.data["truong"]), (status, ma, truong))
        h, _ = self.goi(True, "/api/crm/du-an-ban/moc", {}, T._Da(DataError("CRM_DA_MOC_NGAY_SAI", "Ngày sai", "moc.ngay_du_kien")))
        self.assertEqual(h.data["truong"], "moc.ngay_du_kien")

    def test_khong_nhan_tham_quyen_va_lock(self):
        for k in ("actor", "phap_nhan_id", "nguoi", "trang_thai", "la"):
            h, da = self.goi(True, "/api/crm/du-an-ban/moc", {"da_ban_id": DB, "moc": moc(), "khoa": "k", k: "DEMO"})
            self.assertEqual(h.st, 403 if k in CG.KHONG_NHAN else 400)
            self.assertEqual(da.goi, [])
        app = T._App(T._Da())
        def ghi(me, **kw):
            self.assertTrue(app.mutation_lock.locked())
            return {"ok": True}
        app.__dict__["_crm_da"].moc_ghi = ghi
        h = T._H("/api/crm/du-an-ban/moc", {"da_ban_id": DB, "moc": moc(), "khoa": "k"})
        CG.dieu_huong(h, app, True, h.path, {})
        self.assertEqual(h.st, 200)


class SeedGiaLap(unittest.TestCase):
    def test_bo_sung_moc_cho_demo_cu_khong_de_du_an_tu_khai(self):
        class C:
            def __init__(self):
                self.bn, self.rows = set(), []
            @staticmethod
            def transaction():
                return nullcontext()
            def execute(self, sql, args=()):
                if "to_regclass" in sql:
                    r = (True,)
                elif "FROM master.nguoi_dung" in sql:
                    r = (MID,)
                elif "set_config" in sql:
                    r = (None,)
                elif "FROM master.du_an a" in sql:
                    r = [(DA, T.LH)]
                elif "FROM master.crm_da_ban WHERE" in sql:
                    r = (DB,)
                elif "hanh_dong = 'CRM_DA_BAT_BAN'" in sql:
                    r = (1,) if "DA_KCN_DEMO" in args[1] else None
                elif "FROM master.crm_g_bien_nhan" in sql:
                    r = (1,) if args[1] in self.bn else None
                elif "SELECT master.crm_da_moc_ghi(" in sql:
                    self.rows.append(json.loads(args[3]))
                    self.bn.add(args[0])
                    r = ({"ket_qua": {}, "lap_lai": False},)
                else:
                    raise AssertionError("Lệnh ngoài phạm vi bổ sung mốc: " + sql)
                return type("R", (), {"fetchone": lambda _: r, "fetchall": lambda _: r})()
        c = C()
        first = D.khoi_tao_demo(c, hom_nay=date(2026, 10, 25))
        self.assertEqual([r["trang_thai"] for r in first["du_an"]], ["DA_TAO", "BO_QUA_DA_CO"])
        self.assertEqual(len(c.rows), 2)
        again = D.khoi_tao_demo(c, hom_nay=date(2026, 10, 26))
        self.assertEqual([r["trang_thai"] for r in again["du_an"]], ["DU", "BO_QUA_DA_CO"])
        self.assertEqual(len(c.rows), 2)

    def test_seed_khoa_rieng_idempotent_qua_ngay(self):
        class C:
            def __init__(self):
                self.bn, self.rows = set(), []
            def execute(self, sql, args=()):
                if "to_regclass" in sql:
                    r = (True,)
                elif "FROM master.crm_g_bien_nhan" in sql:
                    r = (1,) if args[1] in self.bn else None
                else:
                    self.assert_sql(sql)
                    self.rows.append((sql, args))
                    self.bn.add(args[0])
                    r = ({"ket_qua": {}, "lap_lai": False},)
                return type("R", (), {"fetchone": lambda _: r})()
            @staticmethod
            def assert_sql(sql):
                assert sql.startswith("SELECT master.crm_da_moc_ghi(")
        c = C()
        self.assertTrue(D._seed_moc_demo(c, "nd-demo", DB, "DA_KCN_DEMO", "2026-10-25"))
        self.assertEqual(len(c.rows), 2)
        ds = [json.loads(p[3]) for _, p in c.rows]
        self.assertEqual([(r["ten"], r["ten_tat"], r["ngay_du_kien"]) for r in ds],
                         [("Xong chứng nhận đầu tư", "CNĐT", "2026-11-24"), ("Bàn giao hạ tầng giai đoạn 1 — DEMO", None, "2026-10-20")])
        self.assertTrue(all(p[0].startswith(D.SEED_MOC_KHOA) and p[2] == DB for _, p in c.rows))
        self.assertFalse(D._seed_moc_demo(c, "nd-demo", DB, "DA_KCN_DEMO", "2026-10-26"))
        self.assertFalse(D._seed_moc_demo(c, "nd-demo", DB, "DA_NHA_DEMO", "2026-10-25"))
        self.assertEqual(len(c.rows), 2)


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
        from psycopg.conninfo import make_conninfo
        from psycopg.rows import dict_row
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.k2 import crm_demo
        dsn = os.environ["KHO_PG_DSN_TEST"]
        cls.db = "kho_test_mda1b_" + uuid.uuid4().hex[:12]
        with psycopg.connect(dsn, autocommit=True) as c:
            c.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        db_dsn = make_conninfo(dsn, dbname=cls.db)
        cls.c = psycopg.connect(db_dsn, autocommit=True)
        cls.addClassCleanup(cls.c.close)
        pg.migrate(cls.c)
        crm_demo.khoi_tao(cls.c)
        cls.cd = psycopg.connect(db_dsn, autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(cls.cd.close)
        cls.today = D._hom_nay_vn()
        cls.s = D.CrmDuAnBanK2(CrmMauK2(cls.cd, Path(__file__).parent, conn_tin_cay=cls.cd, hom_nay=lambda: cls.today))

    def test_seed_hai_moc_lap_lai_va_ghi_thuc_te_het_viec_cho(self):
        r = D.khoi_tao_demo(self.c, hom_nay=self.today)
        self.assertEqual(r["trang_thai"], "DA_TAO", r)
        da = self.c.execute("SELECT a.id::text, d.id::text FROM master.du_an a JOIN master.crm_da_ban d ON d.du_an_id = a.id WHERE a.ma_junsky = 'DA_KCN_DEMO'").fetchone()
        rows = self.s.moc_ds(ME, da[0])
        self.assertEqual((len(rows["moc"]), rows["so_viec_cho"]), (2, 1))
        self.assertEqual({m["ten"] for m in rows["moc"]}, {"Xong chứng nhận đầu tư", "Bàn giao hạ tầng giai đoạn 1 — DEMO"})
        self.assertEqual({m["ngay_du_kien"] for m in rows["moc"]},
                         {(self.today + timedelta(days=30)).isoformat(), (self.today - timedelta(days=5)).isoformat()})
        truoc = self.c.execute("SELECT (SELECT count(*) FROM master.crm_da_moc), (SELECT count(*) FROM master.crm_da_moc_ls)").fetchone()
        for ngay in (self.today, self.today + timedelta(days=1)):
            again = D.khoi_tao_demo(self.c, hom_nay=ngay)
            self.assertEqual(again["trang_thai"], "DU", again)
            self.assertEqual(self.c.execute("SELECT (SELECT count(*) FROM master.crm_da_moc), (SELECT count(*) FROM master.crm_da_moc_ls)").fetchone(), truoc)
        self.assertEqual(self.s.moc_ds(ME, da[0]), rows)
        qua = next(m for m in rows["moc"] if m["viec_cho"])
        result = self.s.moc_ghi(ME, da_ban_id=da[1], moc={"moc_id": qua["moc_id"], "expected_lan": qua["lan"],
                             "ngay_thuc_te": self.today.strftime("%d/%m/%Y")}, khoa="mda1b-thuc-te-demo")
        self.assertEqual(result["lan"], 2)
        self.assertEqual(self.s.moc_ds(ME, da[0])["so_viec_cho"], 0)
        self.assertEqual(self.s.moc_lich_su(ME, qua["moc_id"])["nhat_ky"][-1]["hanh_dong_hien_thi"], "Ghi ngày thực tế")


if __name__ == "__main__":
    unittest.main()
