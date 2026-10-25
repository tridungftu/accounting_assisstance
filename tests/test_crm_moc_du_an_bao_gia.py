"""MDA-3s — kiểm mốc riêng khi lưu và nhãn bản in; không cần CSDL/Word. PG do lead chạy."""

from __future__ import annotations

import io
import json
import os
import unittest
import uuid
import zipfile
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest.mock import patch

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import crm_giao_ket as G
from kho_tri_thuc.k2.crm_mau import CrmMauK2
from tests.test_crm_giao_ket import bao_gia

DA, KHAC, BG, MID = (str(uuid.UUID(int=n)) for n in (1, 2, 3, 4))
MA = "DAM-" + MID
TEN = "Xong chứng nhận đầu tư"
ME = "MO_PHONG_BAN_HANG"
LOI = "Dòng {}: mốc không thuộc dự án đã chọn hoặc đã ngừng dùng — chọn lại mốc."


def du_lieu(ma=MA, du_an=DA):
    d = bao_gia(du_an_id=du_an)
    d["lich"][0]["moc_su_kien"] = ma
    return d


class _Mau(CrmMauK2):
    """Kết nối giả chặn lệnh ngoài dự kiến và mọi SQL ngoài giao dịch."""

    def __init__(self):
        self.root = Path(__file__).parent
        self.hom_nay = lambda: date(2026, 10, 25)
        self.lenh, self.dang_tx, self.da_luu = [], False, []
        self.moc = {DA: [{"ma": MA, "ten": TEN}], KHAC: []}
        self.cu = G.chuan_hoa_bao_gia(du_lieu(MA + "_30"))

    def danh_tinh(self, dang_nhap):
        return {"id": MID, "dang_nhap": dang_nhap, "vai_tro": "BAN_HANG"}

    @contextmanager
    def _tx(self, dt, *, rr=False):
        assert rr and not self.dang_tx
        self.dang_tx = True
        try:
            yield self
        finally:
            self.dang_tx = False

    def execute(self, sql, params=()):
        assert self.dang_tx, "SQL phải cùng giao dịch"
        self.lenh.append((sql, params))
        if "master.crm_gk_tra(" in sql:
            row = {"r": None}
        elif "master.crm_da_moc_doc(" in sql:
            assert params[1] == "2026-10-25", "Ngày đọc phải là ngày máy chủ"
            row = {"r": self.moc[params[0]]}
        elif "master.crm_gk_bao_gia_luu(" in sql:
            self.da_luu.append(json.loads(params[7]))
            row = {"r": {"ket_qua": {"id": BG, "revision": len(self.da_luu)}, "lap_lai": False}}
        elif "SELECT phap_nhan_id, cau_hinh" in sql:
            row = {"phap_nhan_id": DA, "cau_hinh": {}}
        elif "FROM master.crm_bao_gia b JOIN" in sql:
            row = {"id": BG, "du_an_id": self.cu["du_an_id"], "du_lieu": self.cu, "g7": None,
                   "revision_hien_hanh": 1, "trang_thai": "NHAP", "loai_hinh_id": self.cu["loai_hinh_id"],
                   "khach_ten": None, "so_bao_gia": "BG-DEMO", "ngay": "2026-10-25", "tao_boi": ME,
                   "du_lieu_sha256": "0" * 64}
        elif "FROM master.crm_bao_gia_dieu_khoan" in sql:
            return [{"noi_dung": "Điều khoản DEMO"}]
        elif "SELECT ten FROM master.du_an" in sql:
            row = {"ten": "Dự án DEMO"}
        else:
            raise AssertionError("SQL ngoài phạm vi: " + sql)
        return type("R", (), {"fetchone": lambda _: row})()


class LuuMocDuAn(unittest.TestCase):
    def setUp(self):
        self.m = _Mau()
        self.s = G.CrmGiaoKetK2(self.m)
        # Các seam dự án/lô và trùng đơn vị đã có test riêng; giữ nguyên luồng SQL lưu thật của service.
        for ten, kw in (("_gan_tieu_chuan", {"return_value": None}), ("_trung_don_vi", {"return_value": []})):
            p = patch.object(self.s, ten, **kw)
            p.start()
            self.addCleanup(p.stop)

    def luu(self, d, sua=False):
        return self.s.luu(ME, bao_gia_id=BG if sua else None, expected_revision=1 if sua else None,
                          du_lieu=d, khoa="mda3s-demo")

    def so_doc_moc(self):
        return sum("master.crm_da_moc_doc(" in sql for sql, _ in self.m.lenh)

    def test_luu_moc_thuoc_du_an_va_bien_ngay_ca_nhap_sua(self):
        for sua in (False, True):
            for ma in (MA, MA + "_1", MA + "_30", MA + "_3650"):
                with self.subTest(sua=sua, ma=ma):
                    truoc = self.so_doc_moc()
                    self.assertFalse(self.luu(du_lieu(ma), sua)["lap_lai"])
                    self.assertEqual(self.so_doc_moc(), truoc + 1)
                    self.assertEqual(self.m.da_luu[-1]["lich"][0]["moc_su_kien"], ma)

    def test_khac_du_an_khong_du_an_va_ngung_dung_loi_dung_truong(self):
        for sua in (False, True):
            for da, rows in ((KHAC, []), (None, []), (DA, [])):
                with self.subTest(sua=sua, du_an=da):
                    self.m.moc[DA] = rows
                    d = du_lieu(MA + "_30", da)
                    # Giữ nguyên mã khi sửa bản đã lưu vẫn phải kiểm lại.
                    self.m.cu = G.chuan_hoa_bao_gia(d)
                    with self.assertRaises(DataError) as cm:
                        self.luu(d, sua)
                    self.assertEqual((cm.exception.code, cm.exception.locator, str(cm.exception)),
                                     ("CRM_GK_LICH_SAI", "lich.0.moc_su_kien", LOI.format(1)))
        self.assertEqual(self.m.da_luu, [])

    def test_dong_thu_hai_loi_va_nhieu_dong_chi_doc_mot_lan(self):
        d = du_lieu()
        d["lich"][1].update(moc_loai="SU_KIEN", moc_ngay=None, moc_su_kien="DAM-" + KHAC)
        with self.assertRaises(DataError) as cm:
            self.luu(d)
        self.assertEqual((cm.exception.locator, str(cm.exception)), ("lich.1.moc_su_kien", LOI.format(2)))
        self.assertEqual(self.so_doc_moc(), 1)
        self.assertEqual(self.m.da_luu, [])
        d["lich"][1]["moc_su_kien"] = MA + "_30"
        self.luu(d)
        self.assertEqual(self.so_doc_moc(), 2)

    def test_ma_chuan_va_ma_cu_khong_doc_moc_du_an(self):
        for ma in ("KY_HD", "BAN_GIAO", "SO", "SAU_KY_30", "XONG_TANG_2", "MA_CU_DEMO"):
            self.luu(du_lieu(ma))
        self.assertEqual(self.so_doc_moc(), 0)

    def test_ma_dam_sai_va_tham_so_ngoai_mien_khong_luu(self):
        for ma in ("DAM-x", MA + "_0", MA + "_3651", MA + "_-1", MA + "_30x", MA + "_99999"):
            with self.subTest(ma=ma), self.assertRaises(DataError) as cm:
                self.luu(du_lieu(ma))
            self.assertEqual((cm.exception.locator, str(cm.exception)), ("lich.0.moc_su_kien", LOI.format(1)))
        self.assertEqual(self.m.da_luu, [])


class NhanVaBanIn(unittest.TestCase):
    def test_nhan_moc_rieng_tham_so_thieu_bang_va_ma_la(self):
        bang = {"DAM-x": TEN}
        for ma, nhan in (("DAM-x", TEN), ("DAM-x_30", TEN + " + 30 ngày"),
                         ("DAM-y", "Mốc riêng của dự án (đã ngừng dùng)"),
                         ("DAM-x_3651", "Mốc riêng của dự án (đã ngừng dùng)"),
                         ("MA_LA", "Sự kiện khác (chưa có nhãn)"), ("KY_HD", "Ký"),
                         ("SAU_KY_30", "Sau ký + 30 ngày"), (None, "Sự kiện: chưa xác định")):
            with self.subTest(ma=ma):
                self.assertEqual(G.nhan_moc_su_kien(ma, bang), nhan)
        self.assertEqual(G.nhan_moc_su_kien("DAM-x"), "Mốc riêng của dự án (đã ngừng dùng)")

    def test_ban_cu_in_duoc_nhan_hien_hanh_hoac_ngung_dung_khong_in_ma(self):
        for rows, nhan in (([{"ma": MA, "ten": TEN}], TEN + " + 30 ngày"),
                           ([], "Mốc riêng của dự án (đã ngừng dùng)")):
            with self.subTest(rows=rows):
                m = _Mau()
                m.moc[DA] = rows
                m.cu["lich"][1].update(moc_loai="SU_KIEN", moc_ngay=None, moc_su_kien=MA)
                s = G.CrmGiaoKetK2(m)
                # Kế hoạch in và renderer DOCX thật; không đặt chỗ/ghi tệp/chuyển PDF/Word.
                with patch.object(s, "_dat_lan", side_effect=lambda dt, kh: kh):
                    kh = s.chuan_bi_in(ME, bao_gia_id=BG, expected_revision=1, khoa="in-mda3s-demo")
                self.assertEqual(kh["nd"]["lich"][0][2], nhan)
                self.assertEqual(kh["nd"]["lich"][1][2], TEN if rows else "Mốc riêng của dự án (đã ngừng dùng)")
                self.assertEqual(sum("master.crm_da_moc_doc(" in sql for sql, _ in m.lenh), 1)
                self.assertNotIn("DAM-", json.dumps(kh["nd"], ensure_ascii=False))
                self.assertIn((nhan, 1), kh["mong_doi"])
                with zipfile.ZipFile(io.BytesIO(G.R.tao_docx_bao_gia(kh["nd"]))) as z:
                    xml = z.read("word/document.xml").decode("utf-8")
                self.assertIn(nhan, xml)
                self.assertNotIn("DAM-", xml)


try:
    import psycopg
except ImportError:
    psycopg = None


@unittest.skipUnless(os.environ.get("KHO_PG_DSN_TEST") and psycopg is not None,
                     "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PostgreSQL")
class BaoGiaMocPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from psycopg.rows import dict_row
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.k2 import crm_demo, crm_du_an_ban as D
        dsn = os.environ["KHO_PG_DSN_TEST"]
        cls.db = "kho_test_mda3s_" + uuid.uuid4().hex[:12]
        with psycopg.connect(dsn, autocommit=True) as c:
            c.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        db_dsn = make_conninfo(dsn, dbname=cls.db)
        cls.c = psycopg.connect(db_dsn, autocommit=True)
        cls.addClassCleanup(cls.c.close)
        pg.migrate(cls.c)
        crm_demo.khoi_tao(cls.c)
        cls.today = D._hom_nay_vn()
        D.khoi_tao_demo(cls.c, hom_nay=cls.today)
        cls.cd = psycopg.connect(db_dsn, autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(cls.cd.close)
        cls.m = CrmMauK2(cls.cd, Path(__file__).parent, conn_tin_cay=cls.cd, hom_nay=lambda: cls.today)
        cls.s = G.CrmGiaoKetK2(cls.m)

    def test_seed_kcn_moc_cong_30_luu_duoc_doi_sang_nha_bi_chan(self):
        from kho_tri_thuc.k2.crm_du_an_ban import CrmDuAnBanK2
        da = {r["ma_junsky"]: r for r in self.cd.execute(
            "SELECT a.id::text, a.ma_junsky, v.loai_hinh_id::text FROM master.du_an a "
            "JOIN master.crm_da_ban d ON d.du_an_id = a.id "
            "JOIN master.crm_da_ban_phien_ban v ON v.da_ban_id = d.id AND v.hieu_luc_den IS NULL "
            "WHERE a.ma_junsky IN ('DA_KCN_DEMO', 'DA_NHA_DEMO')")}
        kcn, nha = da["DA_KCN_DEMO"], da["DA_NHA_DEMO"]
        rows = CrmDuAnBanK2(self.m).moc_ds(ME, kcn["id"])["moc"]
        ma = next(r["ma"] for r in rows if r["ten"] == TEN) + "_30"
        d = du_lieu(ma, kcn["id"])
        d["loai_hinh_id"] = kcn["loai_hinh_id"]
        kq = self.s.luu(ME, bao_gia_id=None, expected_revision=None, du_lieu=d, khoa="mda3s-kcn-demo")
        bg = kq["bao_gia_id"]
        chi_tiet = self.s.chi_tiet(ME, bg)
        self.assertEqual(chi_tiet["du_lieu"]["lich"][0]["moc_su_kien"], ma)
        d["du_an_id"] = nha["id"]
        with self.assertRaises(DataError) as cm:
            self.s.luu(ME, bao_gia_id=bg, expected_revision=kq["revision"], du_lieu=d, khoa="mda3s-nha-demo")
        self.assertEqual((cm.exception.locator, str(cm.exception)), ("lich.0.moc_su_kien", LOI.format(1)))
        self.assertEqual(self.s.chi_tiet(ME, bg)["bao_gia"]["revision_hien_hanh"], kq["revision"])


if __name__ == "__main__":
    unittest.main()
