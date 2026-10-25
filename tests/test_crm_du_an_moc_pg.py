"""MDA-1a: test tĩnh + PostgreSQL thật trên CSDL kho_test_* mới, chỉ DEMO.

Thiếu KHO_PG_DSN_TEST/psycopg thì SKIP PG (không tính đạt). Không khởi động
server, không DROP CSDL/vai; lead chạy phần PG và quản lý CSDL test.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unicodedata
import unittest
import uuid
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_crm_du_an_ban import CRM_DU_AN_BAN_SQL
from kho_tri_thuc.k2.sql_crm_du_an_moc import CRM_DU_AN_MOC_SQL, _HAM

SQL = "\n".join(CRM_DU_AN_MOC_SQL)
BH, XEM = "MO_PHONG_BAN_HANG", "MO_PHONG_XEM_A"


class MocTinh(unittest.TestCase):
    def test_migration_append_sau_34_giu_nguyen_chuoi_cu(self):
        self.assertGreaterEqual(len(PM.PG_MIGRATIONS), 35)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        self.assertIs(PM.PG_MIGRATIONS[30], CRM_DU_AN_BAN_SQL)
        self.assertEqual(sum(m is CRM_DU_AN_MOC_SQL for m in PM.PG_MIGRATIONS), 1)
        moc_index = PM.PG_MIGRATIONS.index(CRM_DU_AN_MOC_SQL)
        self.assertGreater(moc_index, PM.PG_MIGRATIONS.index(PM.M0034_CONG_AI_NHAT_KY))
        # So toàn bộ registry trước mốc; không phụ thuộc số lead cấp khi gộp.
        source = (ROOT / "src/kho_tri_thuc/ha_tang/pg_migrations.py").read_text(encoding="utf-8")
        prefix = source[:source.index("from ..k2.sql_crm_du_an_moc import ")]
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(prefix, PM.__file__, "exec"), old)
        self.assertEqual(PM.PG_MIGRATIONS[:moc_index], old["PG_MIGRATIONS"])

    def test_bang_ham_bat_bien_va_quyen(self):
        for t in ("crm_da_moc", "crm_da_moc_ls"):
            self.assertIn(f"CREATE TABLE master.{t} (", SQL)
            self.assertIn(f"ALTER TABLE master.{t} ENABLE ROW LEVEL SECURITY", SQL)
        for f in _HAM:
            self.assertIn(f, SQL[SQL.index("REVOKE EXECUTE ON FUNCTION"):])
        for s in ("master.crm_g_bat_bien()", "master.crm_da_dong_mot_lan()", "PRIMARY KEY (moc_id, lan)",
                  "WHERE hieu_luc_den IS NULL", "ma = 'DAM-' || id::text", "UNIQUE (id, phap_nhan_id)",
                  "REFERENCES master.crm_da_ban (id, phap_nhan_id)",
                  "REVOKE ALL ON master.crm_da_moc, master.crm_da_moc_ls FROM PUBLIC",
                  "ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai']", "FROM %I"):
            self.assertIn(s, SQL)
        self.assertNotIn("SECURITY DEFINER", SQL)

    def test_preflight_replay_va_ghi_mot_su_kien(self):
        f = next(s for s in CRM_DU_AN_MOC_SQL if "CREATE FUNCTION master.crm_da_moc_ghi(" in s)
        self.assertLess(f.index("master.crm_da_vao('CRM_DA_MOC'"), f.index("IF cu IS NOT NULL"))
        self.assertLess(f.index("IF cu IS NOT NULL"), f.index("jsonb_typeof(p_moc)"))
        self.assertEqual(f.count("INSERT INTO nhat_ky.su_kien"), 1)
        for s in ("CRM_DA_MOC_LAN_CU", "CRM_DA_MOC_CAN_LY_DO", "CRM_DA_MOC_NGAY_SAI", "CRM_DA_MOC_KHAI",
                  "CRM_DA_MOC_THUC_TE", "CRM_DA_MOC_CHINH_DU_KIEN", "CRM_DA_MOC_SUA", "truoc, sau, ld",
                  "master.crm_g_bn_ghi", "FOR UPDATE"):
            self.assertIn(s, f)
        self.assertIn("CRM_DA_MOC_TRUNG", SQL)
        self.assertIn(
            "IF v ->> 'ngay_du_kien' IS NULL THEN\n"
            "                IF o.id IS NOT NULL THEN\n"
            "                    RAISE EXCEPTION 'CRM_DA_MOC_SAI: Ngày dự kiến không được để trống'",
            f,
        )
        self.assertEqual(SQL.count("LANGUAGE plpgsql STABLE"), 2)
        self.assertNotIn("CREATE EXTENSION", SQL)

    def test_anh_xa_dau_tieng_viet_va_utf8_khong_bom(self):
        f = next(s for s in CRM_DU_AN_MOC_SQL if "CREATE FUNCTION master.crm_da_moc_ten_chuan(" in s)
        self.assertIn("LANGUAGE sql IMMUTABLE STRICT", f)
        src, dst = re.search(r"U&'([^']+)',\s*'([^']+)'", f).groups()
        self.assertEqual(len(src), len(dst), "Nguồn/đích translate phải đủ cặp ký tự")
        self.assertEqual(len(src), len(set(src)))
        mapping = str.maketrans(src, dst)
        # Độc lập với bảng SQL: đủ 12 nguyên âm × 6 thanh, cả hoa/thường + đ/Đ.
        for base, expected in zip("aăâeêioôơuưy", "aaaeeiooouuy"):
            for tone in ("", "\u0300", "\u0301", "\u0303", "\u0309", "\u0323"):
                viet = unicodedata.normalize("NFC", base + tone)
                for c in (viet, viet.upper()):
                    with self.subTest(c=c):
                        self.assertIn(c, src)
                        self.assertEqual(c.translate(mapping), expected.upper())
        self.assertEqual("đĐ".translate(mapping), "DD")
        self.assertTrue(dst.isascii())
        self.assertTrue(dst.isupper())
        self.assertIn("btrim(regexp_replace(upper(regexp_replace(translate(p_ten,", f)
        marks = re.search(r"U&'\[([^']+)\]', '', 'g'", f)[1]
        marks = re.sub(r"\\([0-9A-Fa-f]{4})", lambda m: chr(int(m[1], 16)), marks)
        self.assertEqual(set(marks), set("\u0300\u0301\u0303\u0309\u0323\u0306\u0302\u031b"))
        self.assertIn("'[[:space:]]+', ' ', 'g'", f)
        remove_marks = dict.fromkeys(map(ord, marks))
        ascii_upper = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        for ten in ("Xong chứng nhận đầu tư", "XONG CHỨNG NHẬN ĐẦU TƯ", "xong chung nhan dau tu",
                    unicodedata.normalize("NFD", "Xong chứng nhận đầu tư"),
                    unicodedata.normalize("NFD", "XONG CHỨNG NHẬN ĐẦU TƯ"),
                    "  Xong  chứng\t nhận đầu tư  "):
            with self.subTest(ten=ten):
                # Locale C upper chỉ đổi ASCII: không dùng ten.upper().
                key = ten.translate(mapping).translate(remove_marks).translate(ascii_upper)
                key = re.sub(r"[ \t\n\r\f\v]+", " ", key).strip(" ")
                self.assertEqual(key, "XONG CHUNG NHAN DAU TU")
        for p in ("src/kho_tri_thuc/k2/sql_crm_du_an_moc.py", "src/kho_tri_thuc/ha_tang/pg_migrations.py", "tests/test_crm_du_an_moc_pg.py"):
            raw = (ROOT / p).read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), p)
            self.assertNotIn("\ufffd", raw.decode("utf-8"), p)


try:
    import psycopg
except ImportError:
    psycopg = None

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")


@unittest.skipUnless(ADMIN_DSN and psycopg is not None, "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PostgreSQL")
class MocPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.k2 import crm_demo

        cls.db = "kho_test_mda1a_" + uuid.uuid4().hex[:12]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.c = psycopg.connect(make_conninfo(ADMIN_DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        cls.version = pg.migrate(cls.c)
        crm_demo.khoi_tao(cls.c)
        cls.pn = cls.c.execute("SELECT id FROM master.phap_nhan WHERE ma = 'PN_DEMO_A'").fetchone()[0]
        cls.lh = str(cls.c.execute("SELECT id FROM master.loai_hinh_doanh_thu WHERE phap_nhan_id = %s AND valid_to IS NULL AND ma = 'DT-KCN-THUE-DAT-DEMO'", (cls.pn,)).fetchone()[0])

    def setUp(self):
        self.today = self.c.execute("SELECT master.ktt_ngay()").fetchone()[0]
        self.du_an = self.project()
        tt = json.dumps({"loai_hinh_id": self.lh, "tien_te": "VND"})
        r = self.call("SELECT master.crm_da_bat_ban(%s, %s, %s, %s::jsonb, '[]'::jsonb, NULL)",
                      (uuid.uuid4().hex, "a" * 64, self.du_an, tt))
        self.da = r["ket_qua"]["da_ban_id"]

    def project(self):
        return self.c.execute("INSERT INTO master.du_an (phap_nhan_id, ma_junsky, ten) VALUES (%s, %s, 'Dự án mốc DEMO') RETURNING id",
                              (self.pn, "DA_MOC_DEMO_" + uuid.uuid4().hex[:12])).fetchone()[0]

    def call(self, sql, args=(), actor=BH):
        with self.c.transaction():
            nd = self.c.execute("SELECT id::text FROM master.nguoi_dung WHERE dang_nhap = %s", (actor,)).fetchone()[0]
            self.c.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true)", (nd, actor))
            return self.c.execute(sql, args).fetchone()[0]

    def ghi(self, moc, ly_do=None, khoa=None, actor=BH, da=None):
        da = da or self.da
        body = json.dumps([str(da), moc, ly_do], sort_keys=True, ensure_ascii=False)
        h = hashlib.sha256(body.encode("utf-8")).hexdigest()
        return self.call("SELECT master.crm_da_moc_ghi(%s, %s, %s, %s::jsonb, %s)",
                         (khoa or uuid.uuid4().hex, h, da, json.dumps(moc, ensure_ascii=False), ly_do), actor)

    def khai(self, ten="Xong chứng nhận đầu tư DEMO", **fields):
        return self.ghi({"ten": ten, "ngay_du_kien": (self.today + timedelta(days=30)).isoformat(), **fields})["ket_qua"]

    def sua(self, r, ly_do=None, **fields):
        return self.ghi({"moc_id": r["moc_id"], "expected_lan": r["lan"], **fields}, ly_do)["ket_qua"]

    def history(self, r, actor=BH):
        return self.call("SELECT master.crm_da_moc_ls_doc(%s)", (r["moc_id"],), actor)

    def doc(self, ngay=None, actor=BH, du_an=None):
        return self.call("SELECT master.crm_da_moc_doc(%s, %s)", (du_an or self.du_an, ngay or self.today), actor)

    def loi(self, ma, fn):
        with self.assertRaises(psycopg.Error) as cm:
            fn()
        self.assertIn(ma, str(cm.exception))

    def test_khai_lan_1_nhat_ky_va_ma(self):
        r = self.khai(ten_tat="CNĐT")
        self.assertEqual((r["lan"], r["doi"], r["da_ban_id"], r["du_an_id"]), (1, True, self.da, str(self.du_an)))
        self.assertEqual(r["ma"], "DAM-" + r["moc_id"])
        h = self.history(r)
        self.assertEqual(len(h["lich_su"]), 1)
        self.assertEqual(len(h["nhat_ky"]), 1)
        k = h["nhat_ky"][0]
        self.assertEqual((k["hanh_dong"], k["truoc"], k["nguoi"]), ("CRM_DA_MOC_KHAI", None, BH))
        self.assertEqual(k["sau"]["ten_tat"], "CNĐT")
        self.assertEqual(k["sau"]["ngay_du_kien"], (self.today + timedelta(days=30)).isoformat())

    def test_chinh_du_kien_ly_do_cas_va_nhat_ky_cu_moi(self):
        r = self.khai()
        ngay_moi = (self.today + timedelta(days=60)).isoformat()
        for ld in (None, "", "   "):
            self.loi("CRM_DA_MOC_CAN_LY_DO", lambda: self.sua(r, ld, ngay_du_kien=ngay_moi))
        r2 = self.sua(r, "Dời tiến độ DEMO", ngay_du_kien=ngay_moi)
        self.assertEqual((r2["lan"], r2["doi"]), (2, True))
        h = self.history(r)
        self.assertEqual([(s["lan"], s["hieu_luc_den"]) for s in h["lich_su"]], [(1, self.today.isoformat()), (2, None)])
        k = h["nhat_ky"][-1]
        self.assertEqual(len(h["nhat_ky"]), 2)
        self.assertEqual(k["hanh_dong"], "CRM_DA_MOC_CHINH_DU_KIEN")
        self.assertEqual(k["truoc"], h["nhat_ky"][0]["sau"])
        self.assertEqual(k["sau"], {**k["truoc"], "ngay_du_kien": ngay_moi})
        self.assertEqual(k["ly_do"], "Dời tiến độ DEMO")
        self.assertEqual(h["lich_su"][-1]["ly_do"], k["ly_do"])
        self.loi("CRM_DA_MOC_LAN_CU", lambda: self.sua(r, ten="Tên mới DEMO"))
        self.loi("CRM_DA_MOC_LAN_CU", lambda: self.ghi({"moc_id": r["moc_id"], "ten": "Tên mới DEMO"}))
        self.assertEqual(self.history(r), h)

    def test_thuc_te_lan_dau_sua_va_bo_can_ly_do(self):
        r = self.khai()
        r2 = self.sua(r, ngay_thuc_te=self.today.isoformat())
        self.assertEqual(r2["lan"], 2)
        self.assertEqual(self.history(r)["nhat_ky"][-1]["hanh_dong"], "CRM_DA_MOC_THUC_TE")
        for value in (None, (self.today - timedelta(days=1)).isoformat()):
            self.loi("CRM_DA_MOC_CAN_LY_DO", lambda: self.sua(r2, ngay_thuc_te=value))
        r3 = self.sua(r2, "Sửa ngày DEMO", ngay_thuc_te=(self.today - timedelta(days=1)).isoformat())
        r4 = self.sua(r3, "Bỏ ghi nhận nhầm DEMO", ngay_thuc_te=None)
        h = self.history(r)
        self.assertEqual(r4["lan"], 4)
        self.assertEqual(h["nhat_ky"][-1]["truoc"]["ngay_thuc_te"], (self.today - timedelta(days=1)).isoformat())
        self.assertIsNone(h["nhat_ky"][-1]["sau"]["ngay_thuc_te"])
        self.assertEqual(len(h["nhat_ky"]), 4)

    def test_ngay_thuc_te_tuong_lai_khong_ghi(self):
        future = (self.today + timedelta(days=1)).isoformat()
        self.loi("CRM_DA_MOC_NGAY_SAI", lambda: self.khai(ngay_thuc_te=future))
        self.assertEqual(self.doc(), [])
        r = self.khai()
        h = self.history(r)
        self.loi("CRM_DA_MOC_NGAY_SAI", lambda: self.sua(r, ngay_thuc_te=future))
        self.assertEqual(self.history(r), h)

    def test_khong_doi_giu_lan_khong_nhat_ky_va_patch_giu_truong_cu(self):
        r = self.khai(ten_tat="CNĐT", ngay_thuc_te=self.today.isoformat())
        h = self.history(r)
        same = self.sua(r)
        self.assertEqual((same["lan"], same["doi"]), (1, False))
        self.assertEqual(self.history(r), h)
        r2 = self.sua(r, ten="Xong thủ tục DEMO")
        k = self.history(r2)["nhat_ky"][-1]
        self.assertEqual(k["hanh_dong"], "CRM_DA_MOC_SUA")
        self.assertEqual(k["sau"], {**k["truoc"], "ten": "Xong thủ tục DEMO"})
        r3 = self.sua(r2, ten_tat=None)
        self.assertIsNone(self.history(r3)["lich_su"][-1]["ten_tat"])

    def test_uu_tien_hanh_dong_thuc_te_truoc_du_kien(self):
        r = self.khai()
        r2 = self.sua(r, "Chỉnh tiến độ DEMO", ngay_du_kien=self.today.isoformat(), ngay_thuc_te=self.today.isoformat(), ten="Mốc đã xong DEMO")
        h = self.history(r2)
        self.assertEqual((r2["lan"], len(h["nhat_ky"])), (2, 2))
        self.assertEqual(h["nhat_ky"][-1]["hanh_dong"], "CRM_DA_MOC_THUC_TE")

    def test_trung_ten_khong_dau_hoa_thuong_va_mo_lai(self):
        r = self.khai()
        for ten in ("XONG CHỨNG NHẬN ĐẦU TƯ DEMO", "xong chung nhan dau tu demo", unicodedata.normalize("NFD", "Xong chứng nhận đầu tư DEMO")):
            self.loi("CRM_DA_MOC_TRUNG", lambda: self.khai(ten))
        r2 = self.khai("Mốc khác DEMO")
        self.loi("CRM_DA_MOC_TRUNG", lambda: self.sua(r2, ten="Xong chung nhan dau tu DEMO"))
        self.assertEqual(self.history(r2)["lich_su"][-1]["lan"], 1)
        off = self.sua(r, dang_dung=False)
        moi = self.khai("xong chung nhan dau tu demo")
        self.loi("CRM_DA_MOC_TRUNG", lambda: self.sua(off, dang_dung=True))
        self.assertFalse(self.history(r)["lich_su"][-1]["dang_dung"])
        self.assertEqual({m["moc_id"] for m in self.doc()}, {r2["moc_id"], moi["moc_id"]})

    def test_ten_chuan_immutable_khong_extension(self):
        viet = "ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬ ÈÉẺẼẸÊỀẾỂỄỆ ÌÍỈĨỊ ÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢ ÙÚỦŨỤƯỪỨỬỮỰ ỲÝỶỸỴ Đ"
        expected = "A" * 17 + " " + "E" * 11 + " " + "I" * 5 + " " + "O" * 17 + " " + "U" * 11 + " " + "Y" * 5 + " D"
        for ten in (viet, viet.lower(), unicodedata.normalize("NFD", viet)):
            self.assertEqual(self.c.execute("SELECT master.crm_da_moc_ten_chuan(%s)", (ten,)).fetchone()[0], expected)

    def test_ten_chuan_cac_dang_cung_khoa(self):
        for ten in ("Xong chứng nhận đầu tư", "XONG CHỨNG NHẬN ĐẦU TƯ", "xong chung nhan dau tu",
                    unicodedata.normalize("NFD", "Xong chứng nhận đầu tư"),
                    "  Xong  chứng\t nhận đầu tư  "):
            with self.subTest(ten=ten):
                self.assertEqual(self.c.execute("SELECT master.crm_da_moc_ten_chuan(%s)", (ten,)).fetchone()[0],
                                 "XONG CHUNG NHAN DAU TU")

    def test_sua_ngay_du_kien_null_bao_rieng_khong_ghi(self):
        r = self.khai()
        h = self.history(r)
        self.loi("CRM_DA_MOC_SAI: Ngày dự kiến không được để trống", lambda: self.sua(r, ngay_du_kien=None))
        self.assertEqual(self.history(r), h)

    def test_doc_ba_trang_thai_theo_ngay_sap_xep_va_hieu_luc(self):
        a = self.khai("A DEMO", ngay_du_kien=(self.today - timedelta(days=1)).isoformat())
        b = self.khai("B DEMO", ngay_du_kien=self.today.isoformat())
        c = self.khai("C DEMO", ngay_du_kien=(self.today + timedelta(days=1)).isoformat(), ngay_thuc_te=self.today.isoformat())
        self.khai("Ẩn DEMO", dang_dung=False)
        hom_nay = self.doc()
        self.assertEqual([m["moc_id"] for m in hom_nay], [a["moc_id"], b["moc_id"], c["moc_id"]])
        self.assertEqual([m["trang_thai"] for m in hom_nay], ["QUA_DU_KIEN", "CHUA_DEN", "DA_XONG"])
        rows = self.doc(self.today + timedelta(days=1))
        self.assertEqual([m["trang_thai"] for m in rows], ["QUA_DU_KIEN", "QUA_DU_KIEN", "DA_XONG"])
        self.assertEqual(self.doc(self.today - timedelta(days=1)), [])
        # Cùng ngày chỉ lần cuối có hiệu lực; các lần đã đóng vẫn ở lịch sử.
        a2 = self.sua(a, ten="A đổi tên DEMO")
        self.assertEqual(next(m["lan"] for m in self.doc() if m["moc_id"] == a["moc_id"]), a2["lan"])
        self.assertEqual(self.doc(actor=XEM), self.doc())

    def test_du_an_chua_bat_ban_ngung_ban_va_moc_khac_du_an(self):
        chua_ban = self.project()
        self.assertEqual(self.doc(du_an=chua_ban), [])
        r = self.khai()
        self.loi("CRM_DA_MOC_SAI", lambda: self.sua({**r, "moc_id": str(uuid.uuid4())}, ten="Sai DEMO"))
        ban_khac = self.call("SELECT master.crm_da_bat_ban(%s, %s, %s, %s::jsonb, '[]'::jsonb, NULL)",
                            (uuid.uuid4().hex, "c" * 64, chua_ban, json.dumps({"loai_hinh_id": self.lh, "tien_te": "VND"})))
        da_khac = ban_khac["ket_qua"]["da_ban_id"]
        self.loi("CRM_DA_MOC_SAI", lambda: self.ghi({"moc_id": r["moc_id"], "expected_lan": 1, "ten_tat": "Sai"}, da=da_khac))
        # Cùng tên ở dự án khác được phép, không làm lẫn kết quả đọc.
        khac = self.ghi({"ten": "Xong chứng nhận đầu tư DEMO", "ngay_du_kien": self.today.isoformat()}, da=da_khac)["ket_qua"]
        self.assertEqual([m["moc_id"] for m in self.doc(du_an=chua_ban)], [khac["moc_id"]])
        self.assertEqual([m["moc_id"] for m in self.doc()], [r["moc_id"]])
        self.call("SELECT master.crm_da_doi_trang_thai(%s, %s, %s, 1, false, 'Ngừng bán DEMO')", (uuid.uuid4().hex, "b" * 64, self.da))
        self.assertEqual(self.doc(), [])
        self.assertEqual(len(self.history(r)["lich_su"]), 1)

    def test_replay_khong_them_lan_nhat_ky_va_khac_noi_dung(self):
        moc = {"ten": "Replay DEMO", "ngay_du_kien": self.today.isoformat()}
        key = uuid.uuid4().hex
        a = self.ghi(moc, khoa=key)
        h = self.history(a["ket_qua"])
        b = self.ghi(moc, khoa=key)
        self.assertFalse(a["lap_lai"])
        self.assertTrue(b["lap_lai"])
        self.assertEqual(a["ket_qua"], b["ket_qua"])
        self.assertEqual(self.history(a["ket_qua"]), h)
        self.loi("CRM_G_IDEMPOTENCY_KHAC", lambda: self.ghi({**moc, "ten": "Khác DEMO"}, khoa=key))
        # Replay lệnh sửa phải trả lại kết quả đã chốt dù expected_lan đã cũ.
        patch = {"moc_id": a["ket_qua"]["moc_id"], "expected_lan": 1, "ten_tat": "DEMO"}
        key2 = uuid.uuid4().hex
        x = self.ghi(patch, khoa=key2)
        y = self.ghi(patch, khoa=key2)
        self.assertEqual(x["ket_qua"], y["ket_qua"])
        self.assertTrue(y["lap_lai"])
        self.assertEqual(len(self.history(a["ket_qua"])["nhat_ky"]), 2)

    def test_khong_quyen_ghi_va_doc_ngoai_pham_vi(self):
        r = self.khai()
        self.loi("CRM_G_KHONG_CO_QUYEN", lambda: self.ghi({"ten": "Không quyền DEMO", "ngay_du_kien": self.today.isoformat()}, actor=XEM))
        self.loi("CRM_G_KHONG_CO_QUYEN", lambda: self.ghi({"moc_id": r["moc_id"], "expected_lan": 1, "ten_tat": "X"}, actor="MO_PHONG_CFO"))
        for actor in ("MO_PHONG_KT_B", "MO_PHONG_KT_KHONG_CRM_A"):
            self.loi("CRM_G_KHONG_THAY", lambda: self.doc(actor=actor))
            self.loi("CRM_G_KHONG_THAY", lambda: self.history(r, actor=actor))
        self.assertEqual(self.history(r, actor=XEM), self.history(r))

    def test_update_delete_goc_va_sua_lich_su_bi_chan(self):
        r = self.khai()
        for statement in ("UPDATE master.crm_da_moc SET ma = ma WHERE id = %s", "DELETE FROM master.crm_da_moc WHERE id = %s"):
            self.loi("CRM_G_BAT_BIEN", lambda: self.c.execute(statement, (r["moc_id"],)))
        self.loi("CRM_G_BAT_BIEN", lambda: self.c.execute("UPDATE master.crm_da_moc_ls SET ten = 'Ghi đè DEMO' WHERE moc_id = %s", (r["moc_id"],)))
        self.sua(r, ten_tat="DEMO")
        self.loi("CRM_G_BAT_BIEN", lambda: self.c.execute("UPDATE master.crm_da_moc_ls SET hieu_luc_den = hieu_luc_den WHERE moc_id = %s AND lan = 1", (r["moc_id"],)))

    def test_rls_revoke_va_checksum_migration_cu(self):
        self.assertEqual(self.version, PM.PG_SCHEMA_VERSION)
        rows = self.c.execute("SELECT version, checksum FROM master.schema_migrations ORDER BY version").fetchall()
        self.assertEqual([tuple(r) for r in rows], [(i + 1, PM._hash(m)) for i, m in enumerate(PM.PG_MIGRATIONS)])
        for t in ("crm_da_moc", "crm_da_moc_ls"):
            self.assertTrue(self.c.execute("SELECT relrowsecurity FROM pg_class WHERE oid = %s::regclass", ("master." + t,)).fetchone()[0])
            for vai in ("app_web", "app_ke_toan", "app_doc", "app_cong_ai"):
                if not self.c.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (vai,)).fetchone():
                    continue
                for p in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                    self.assertFalse(self.c.execute("SELECT has_table_privilege(%s, %s, %s)", (vai, "master." + t, p)).fetchone()[0])
                for f in _HAM:
                    self.assertFalse(self.c.execute("SELECT has_function_privilege(%s, %s, 'EXECUTE')", (vai, f)).fetchone()[0])

    def test_khoa_la_kieu_sai_va_ngay_khong_hop_le(self):
        base = {"ten": "Kiểm dữ liệu DEMO", "ngay_du_kien": self.today.isoformat()}
        bad = [None, [], {**base, "la": 1}, {**base, "ten": None}, {**base, "ten": " DEMO"}, {**base, "ten": "DEMO\n"},
               {**base, "ten": "{DEMO}"}, {**base, "ten": "x" * 121}, {**base, "ten_tat": "x" * 21},
               {**base, "dang_dung": "true"}, {**base, "dang_dung": None}, {**base, "ngay_du_kien": None},
               {**base, "ngay_du_kien": 20261025}, {**base, "moc_id": "không phải uuid"}, {**base, "expected_lan": "1"}]
        for moc in bad:
            with self.subTest(moc=moc):
                self.loi("CRM_DA_MOC_SAI", lambda: self.ghi(moc))
        for day in ("25/10/2026", "2026-02-30", "2026-13-01", "2026-2-01", "0000-01-01", "infinity"):
            with self.subTest(day=day):
                self.loi("CRM_DA_MOC_NGAY_SAI", lambda: self.ghi({**base, "ngay_du_kien": day}))
        self.assertEqual(self.doc(), [])


if __name__ == "__main__":
    unittest.main()
