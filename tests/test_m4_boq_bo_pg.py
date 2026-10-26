"""BO-1a: chỉ dữ liệu giả; PG tự tạo kho_test_*, không mở server/xóa tệp/DB.

Chạy: python -B -X utf8 -m unittest discover -s tests -p test_m4_boq_bo_pg.py -v
PYTHONPATH=src; thiếu psycopg/KHO_PG_DSN_TEST => NOT_RUN, lead chạy PG.
"""

from __future__ import annotations

import os
from pathlib import Path
import unittest
import uuid

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.m4.sql_boq_bo import M4_BOQ_BO_SQL

try:
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
except ImportError:
    psycopg = None


DSN = os.environ.get("KHO_PG_DSN_TEST")
POSITION = next(i for i, m in enumerate(PM.PG_MIGRATIONS) if m is M4_BOQ_BO_SQL)
ROOT = Path(__file__).resolve().parents[1]


class BoqBoTinh(unittest.TestCase):
    def test_chi_append_khong_ghim_migration_cuoi(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# BO-1a — QD-09:"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, "exec"), old)
        self.assertEqual(PM.PG_MIGRATIONS[:POSITION], old["PG_MIGRATIONS"])
        self.assertEqual(sum(m is M4_BOQ_BO_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        # Writer đã có guard ma trận phải giữ nguyên sau migration mới.
        def writer(migrations):
            return [s for m in migrations for s in m
                    if s.startswith("CREATE OR REPLACE FUNCTION m4.ghi_boq(")][-1]
        self.assertEqual(writer(PM.PG_MIGRATIONS), writer(old["PG_MIGRATIONS"]))

    def test_khong_them_bang_cot_hay_quyen_bang(self):
        statements = "\n".join(M4_BOQ_BO_SQL)
        self.assertNotRegex(statements, r"\b(?:CREATE TABLE|ADD COLUMN|CREATE POLICY|ALTER POLICY|DISABLE)\b")
        self.assertNotRegex(statements, r"\b(?:INSERT INTO|UPDATE m4|DELETE FROM|GRANT SELECT)\b")
        self.assertIn("pg_catalog.pg_constraint", M4_BOQ_BO_SQL[0])
        self.assertIn("INTO STRICT", M4_BOQ_BO_SQL[0])
        self.assertIn("STABLE SECURITY INVOKER", M4_BOQ_BO_SQL[1])
        self.assertIn("RETURNS jsonb", M4_BOQ_BO_SQL[1])
        self.assertNotRegex(M4_BOQ_BO_SQL[1], r"::(?:numeric|decimal|float|real)\b")

    def test_moi_than_ham_sql_dong_dollar_quote(self):
        for statement in M4_BOQ_BO_SQL:
            with self.subTest(statement=statement[:70]):
                if "$$" in statement:
                    self.assertEqual(statement.count("$$"), 2)
                    self.assertTrue(statement.rstrip().endswith("END $$"))
        self.assertEqual(M4_BOQ_BO_SQL[1].count("AS $$"), 1)

    def test_utf8_khong_bom_registry_lf(self):
        for path in (Path(PM.__file__), ROOT / "src/kho_tri_thuc/m4/sql_boq_bo.py", Path(__file__)):
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), str(path))
            self.assertNotIn("\ufffd", raw.decode("utf-8"))
        self.assertNotIn(b"\r", Path(PM.__file__).read_bytes())


@unittest.skipUnless(DSN and psycopg is not None,
                     "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class BoqBoPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.ha_tang import postgres

        cls.db = "kho_test_m4_boq_bo_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_web') "
                          "THEN CREATE ROLE app_web NOLOGIN; END IF; END $$")
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.dsn = make_conninfo(DSN, dbname=cls.db)
        cls.c = psycopg.connect(cls.dsn, autocommit=True)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c, target=POSITION)
        cls.hd_cu, cls.da_cu, cls.pn_cu = cls.hop_dong()
        cls.b_cu = cls.boq(cls.hd_cu, cls.da_cu, 1, [(1, "CU", "GOC", "01,2300")])
        cls.cu_truoc = cls.chup(cls.hd_cu)
        # Đổi tên CHECK để chứng minh migration tra catalog, không đoán tên.
        cls.c.execute("""DO $$ DECLARE ten name; BEGIN
            SELECT c.conname INTO STRICT ten FROM pg_constraint c
            JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attname='thao_tac'
            WHERE c.conrelid='m4.boq_dong'::regclass AND c.contype='c'
              AND c.conkey=ARRAY[a.attnum]::smallint[];
            EXECUTE format('ALTER TABLE m4.boq_dong RENAME CONSTRAINT %I TO bo_test_ten_khac', ten);
        END $$""")
        cls.policy_truoc = cls.policies()
        postgres.migrate(cls.c, target=POSITION + 1)
        cls.cu_sau = cls.chup(cls.hd_cu)
        cls.policy_sau = cls.policies()
        postgres.migrate(cls.c)

    @classmethod
    def insert(cls, table, **values):
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
            sql.Identifier(*table.split(".")),
            sql.SQL(",").join(map(sql.Identifier, values)),
            sql.SQL(",").join(sql.Placeholder() for _ in values))
        return cls.c.execute(query, tuple(values.values())).fetchone()[0]

    @classmethod
    def hop_dong(cls):
        code = uuid.uuid4().hex
        pn = cls.insert("master.phap_nhan", ma=code, ten="Pháp nhân giả BO")
        da = cls.insert("master.du_an", phap_nhan_id=pn, ma_junsky=code, ten="Dự án giả BO")
        dt = cls.insert("master.doi_tac", phap_nhan_id=pn, ten_phap_ly="Đối tác giả BO", ten_chuan_hoa=code)
        cls.insert("master.doi_tac_ma_junsky", phap_nhan_id=pn, doi_tac_id=dt, object_id_junsky=code)
        hd = cls.insert("master.hop_dong", phap_nhan_id=pn, du_an_id=da, doi_tac_id=dt,
                        loai="XAY_DUNG", module_chu="M4", ma_noi_bo=code, so_hop_dong=code)
        cls.c.execute("""INSERT INTO m4.ho_so_hop_dong(hop_dong_id,phap_nhan_id,du_an_id,ten,tao_boi)
            VALUES (%s,%s,%s,'Hồ sơ giả BO','MO_PHONG_BO')""", (hd, pn, da))
        return hd, da, pn

    @classmethod
    def boq(cls, hd, da, lan, rows, pl=None, state="DA_MAP", cells=None):
        from psycopg.types.json import Jsonb

        pn = cls.c.execute("SELECT phap_nhan_id FROM master.du_an WHERE id=%s", (da,)).fetchone()[0]
        sha = uuid.uuid4().hex * 2
        tep = cls.insert("m4.tep", phap_nhan_id=pn, du_an_id=da, vai_tro_tai_lieu="BOQ",
                         raw_sha256=sha, byte_length=1,
                         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         ten_goc="gia.xlsx", object_key="m4-raw/" + sha, tao_boi="MO_PHONG_BO")
        b = cls.insert("m4.boq", hop_dong_id=hd, du_an_id=da, lan=lan, phu_luc_id=pl,
                       tep_id=tep, raw_sha256=sha, sheet="Gia", hang_tieu_de=1,
                       cot=Jsonb({}), so_dong=len(rows), loi_chan=Jsonb([] if state == "DA_MAP" else ["Lỗi giả"]),
                       phat_hien=Jsonb([]), trang_thai=state, bo_doc="BO_TEST", tao_boi="MO_PHONG_BO")
        for dong, ma, op, quantity in rows:
            values = dict(stt="01", nhom="Nhóm giả", ten="Hạng mục giả", dvt="m2",
                          kl=quantity, don_gia="0002,50", thanh_tien=None, ma_rieng="MÃ-GIẢ")
            values.update((cells or {}).get(dong, {}))
            cls.c.execute("""INSERT INTO m4.boq_dong
                (boq_id,du_an_id,dong,ma_hm,thao_tac,stt,nhom,ten,dvt,kl,don_gia,thanh_tien,ma_rieng,o_goc)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                          (b, da, dong, ma, op, *values.values(),
                           Jsonb({"kl": {"loai": "CHU", "gia_tri": values["kl"]}})))
        return b

    @classmethod
    def phu_luc(cls, hd, da, day, state="DA_KY"):
        return cls.insert("m4.phu_luc", hop_dong_id=hd, du_an_id=da, so_pl="GIA-" + uuid.uuid4().hex,
                          ngay_ky="2026-01-01", ngay_hieu_luc=day, trang_thai=state,
                          doi_boq=True, tao_boi="MO_PHONG_BO")

    @classmethod
    def chup(cls, hd):
        return cls.c.execute("SELECT to_jsonb(d) FROM m4.boq_dong d JOIN m4.boq b ON b.id=d.boq_id "
                             "WHERE b.hop_dong_id=%s ORDER BY b.lan,d.dong", (hd,)).fetchall()

    @classmethod
    def policies(cls):
        return cls.c.execute("SELECT polrelid,polname,polcmd,polpermissive,pg_get_expr(polqual,polrelid),"
                             "pg_get_expr(polwithcheck,polrelid) FROM pg_policy ORDER BY polrelid,polname").fetchall()

    def setUp(self):
        self.hd, self.da, self.pn = self.hop_dong()
        # Ghi đảo thứ tự vật lý và mã để oracle kiểm đúng thứ tự nguồn.
        self.b0 = self.boq(self.hd, self.da, 1, [(3, "A", "GOC", None), (2, "Z", "GOC", "01,2300")])
        self.old = self.chup(self.hd)
        self.p1 = self.phu_luc(self.hd, self.da, "2026-02-01")
        self.b1 = self.boq(self.hd, self.da, 2, [(5, "C", "THEM", "-0.100"), (4, "Z", "THAY", "2.5000")], self.p1)
        self.p2 = self.phu_luc(self.hd, self.da, "2026-03-01")
        self.b2 = self.boq(self.hd, self.da, 3, [(7, "A", "BO", None)], self.p2)

    def doc(self, day="2026-03-01", conn=None, hd=None):
        return (conn or self.c).execute("SELECT m4.boq_hieu_luc(%s,%s::date)",
                                       (hd or self.hd, day)).fetchone()[0]

    def rows(self, day="2026-03-01", **kwargs):
        result = self.doc(day, **kwargs)
        self.assertEqual(set(result), {"boq", "can_xem_lai", "ly_do"})
        self.assertFalse(result["can_xem_lai"], result["ly_do"])
        self.assertEqual(result["ly_do"], [])
        return result["boq"]

    def can_xem_lai(self, reason, day="2026-03-01", **kwargs):
        result = self.doc(day, **kwargs)
        self.assertEqual(set(result), {"boq", "can_xem_lai", "ly_do"})
        self.assertIs(result["can_xem_lai"], True)
        self.assertIsNone(result["boq"])
        self.assertIn(reason, result["ly_do"])
        self.assertEqual(len(result["ly_do"]), len(set(result["ly_do"])))
        return result

    def so_pl(self, pl):
        return self.c.execute("SELECT so_pl FROM m4.phu_luc WHERE id=%s", (pl,)).fetchone()[0]

    def sai_thao_tac(self, pl):
        return f"Phụ lục {self.so_pl(pl)}: thao tác BOQ không khớp hạng mục đang hiệu lực."

    def codes(self, day="2026-03-01"):
        return [r["ma_hm"] for r in self.rows(day)]

    def huy(self, pl):
        self.c.execute("UPDATE m4.phu_luc SET trang_thai='DA_HUY',huy_ly_do='Hủy giả',"
                       "huy_boi='MO_PHONG_BO',huy_luc=now() WHERE id=%s", (pl,))

    def test_migration_catalog_du_lieu_cu_va_rls(self):
        self.assertEqual(self.cu_truoc, self.cu_sau)
        self.assertEqual(self.policy_truoc, self.policy_sau)
        self.assertEqual(self.c.execute("SELECT convalidated FROM pg_constraint WHERE "
                                       "conrelid='m4.boq_dong'::regclass AND conname='bo_test_ten_khac'").fetchone(), (True,))
        self.assertEqual(self.c.execute("SELECT provolatile,prosecdef FROM pg_proc "
                                       "WHERE oid='m4.boq_hieu_luc(uuid,date)'::regprocedure").fetchone(), ("s", False))

    def test_ba_moc_ngay_nguon_text_va_thu_tu(self):
        for day, expected in (("2026-01-31", ["Z", "A"]), ("2026-02-01", ["Z", "A", "C"]),
                              ("2026-02-28", ["Z", "A", "C"]), ("2026-03-01", ["Z", "C"])):
            with self.subTest(day=day):
                self.assertEqual(self.codes(day), expected)
                self.assertEqual(self.doc(day), self.doc(day))
        root = self.rows("2026-01-31")[0]
        self.assertEqual((root["boq_id"], root["dong"], root["phu_luc_id"]), (str(self.b0), 2, None))
        self.assertEqual(root["nguon"], "HĐ gốc")
        self.assertEqual((root["kl"], root["don_gia"], root["thanh_tien"]), ("01,2300", "0002,50", None))
        changed = self.rows()[0]
        self.assertEqual((changed["boq_id"], changed["dong"], changed["phu_luc_id"], changed["lan"]),
                         (str(self.b1), 4, str(self.p1), 2))
        self.assertEqual(changed["nguon"], self.so_pl(self.p1))
        self.assertEqual((changed["kl"], changed["don_gia"], changed["thanh_tien"]), ("2.5000", "0002,50", None))
        self.assertEqual(changed["o_goc"], {"kl": {"loai": "CHU", "gia_tri": "2.5000"}})
        self.assertEqual(self.old, [r for r in self.chup(self.hd) if r[0]["boq_id"] == str(self.b0)])

    def test_huy_phu_luc_tra_lai_hang_muc_va_giu_moi_dong_cu(self):
        before = self.chup(self.hd)
        self.assertEqual(self.codes(), ["Z", "C"])
        self.huy(self.p2)
        self.assertEqual(self.doc(), self.doc("2026-02-28"))
        self.assertEqual(self.codes(), ["Z", "A", "C"])
        self.assertEqual(self.chup(self.hd), before)
        with self.assertRaisesRegex(psycopg.Error, "M4_BAT_BIEN"):
            self.c.execute("UPDATE m4.boq_dong SET kl='99' WHERE boq_id=%s", (self.b0,))

    def test_bo_khong_ton_tai_bao_ro_va_chua_den_ngay_khong_ap(self):
        pl = self.phu_luc(self.hd, self.da, "2026-04-01")
        self.boq(self.hd, self.da, 4, [(1, "KHONG_CO", "BO", None)], pl)
        self.assertEqual(self.codes(), ["Z", "C"])
        self.can_xem_lai(self.sai_thao_tac(pl), "2026-04-01")
        self.huy(pl)
        self.assertEqual(self.codes("2026-04-01"), ["Z", "C"])

    def test_bo_khong_phu_luc_bao_ro(self):
        hd, da, _ = self.hop_dong()
        self.boq(hd, da, 1, [(1, "GIA", "BO", None)])
        self.can_xem_lai("BOQ gốc trùng mã hoặc sai thao tác.", hd=hd)

    def test_bo_khong_duoc_dua_vao_them_cung_phu_luc(self):
        pl = self.phu_luc(self.hd, self.da, "2026-04-01")
        self.boq(self.hd, self.da, 4, [(1, "MOI", "THEM", "1"), (2, "MOI", "BO", None)], pl)
        self.can_xem_lai(f"Phụ lục {self.so_pl(pl)}: trùng mã hạng mục.", "2026-04-01")

    def test_bo_lan_hai_va_huy_phu_luc_them_truoc_do(self):
        p3 = self.phu_luc(self.hd, self.da, "2026-04-01")
        self.boq(self.hd, self.da, 4, [(1, "A", "BO", None)], p3)
        self.can_xem_lai(self.sai_thao_tac(p3), "2026-04-01")
        self.huy(p3)
        p4 = self.phu_luc(self.hd, self.da, "2026-05-01")
        self.boq(self.hd, self.da, 5, [(1, "C", "BO", None)], p4)
        self.assertEqual(self.codes("2026-05-01"), ["Z"])
        self.huy(self.p1)
        self.can_xem_lai(self.sai_thao_tac(p4), "2026-05-01")

    def test_them_b_thay_b_roi_huy_phu_luc_them_can_xem_lai(self):
        hd, da, _ = self.hop_dong()
        self.boq(hd, da, 1, [(1, "A", "GOC", "1")])
        p1 = self.phu_luc(hd, da, "2026-02-01")
        self.boq(hd, da, 2, [(1, "B", "THEM", "01,2300")], p1)
        p2 = self.phu_luc(hd, da, "2026-03-01")
        self.boq(hd, da, 3, [(1, "B", "THAY", "2.5000")], p2)
        before = self.chup(hd)
        self.assertEqual([r["ma_hm"] for r in self.rows(hd=hd)], ["A", "B"])
        self.assertEqual(self.rows(hd=hd)[1]["kl"], "2.5000")
        self.huy(p1)
        self.can_xem_lai(self.sai_thao_tac(p2), hd=hd)
        self.assertEqual(self.chup(hd), before)

    def test_thay_chi_ghi_de_truong_co_gia_tri_va_cap_nhat_nguon(self):
        before = self.rows()[0]
        pl = self.phu_luc(self.hd, self.da, "2026-04-01")
        b = self.boq(self.hd, self.da, 4, [(1, "Z", "THAY", None)], pl,
                     cells={1: dict(stt="", nhom=None, ten="", dvt="", don_gia="",
                                    thanh_tien="000,00", ma_rieng="MA-THAY")})
        changed = self.rows("2026-04-01")[0]
        for key in ("ma_hm", "stt", "nhom", "ten", "dvt", "kl", "don_gia", "ma_rieng"):
            with self.subTest(key=key):
                self.assertEqual(changed[key], before[key])
        self.assertEqual(changed["thanh_tien"], "000,00")
        self.assertEqual((changed["boq_id"], changed["dong"], changed["phu_luc_id"],
                          changed["lan"], changed["thao_tac"], changed["nguon"]),
                         (str(b), 1, str(pl), 4, "THAY", self.so_pl(pl)))
        self.assertEqual(changed["o_goc"], {"kl": {"loai": "CHU", "gia_tri": None}})

    def test_them_ma_da_co_va_thay_ma_chua_co_can_xem_lai(self):
        pl = self.phu_luc(self.hd, self.da, "2026-04-01")
        self.boq(self.hd, self.da, 4, [(1, "Z", "THEM", "9"),
                                      (2, "KHONG_CO", "THAY", "8")], pl)
        result = self.can_xem_lai(self.sai_thao_tac(pl), "2026-04-01")
        self.assertEqual(result["ly_do"], [self.sai_thao_tac(pl)])

    def test_trung_ma_cung_phu_luc_ke_ca_khac_lan_boq(self):
        pl = self.phu_luc(self.hd, self.da, "2026-04-01")
        self.boq(self.hd, self.da, 4, [(1, "Z", "THAY", "4"), (2, "Z", "THAY", "5")], pl)
        reason = f"Phụ lục {self.so_pl(pl)}: trùng mã hạng mục."
        self.assertEqual(self.can_xem_lai(reason, "2026-04-01")["ly_do"], [reason])
        # Một mã xuất hiện ở BOQ khác nhưng cùng PL vẫn là trùng mã.
        self.boq(self.hd, self.da, 5, [(1, "A", "THEM", "1")], pl)
        self.boq(self.hd, self.da, 6, [(1, "A", "BO", None)], pl)
        self.assertEqual(self.can_xem_lai(reason, "2026-04-01")["ly_do"], [reason])

    def test_boq_thieu_phu_luc_nguon_can_xem_lai(self):
        # Chỉ tạo nguồn giả hỏng trong transaction test; không sửa/xóa dữ liệu cũ.
        is_super = self.c.execute("SELECT rolsuper FROM pg_roles WHERE rolname=current_user").fetchone()[0]
        if not is_super:
            self.skipTest("NOT_RUN: cần superuser tạo fixture thiếu phụ lục qua session_replication_role")
        with self.c.transaction():
            self.c.execute("SET LOCAL session_replication_role = replica")
            self.boq(self.hd, self.da, 4, [(1, "MAT_NGUON", "THEM", "1")], uuid.uuid4())
            self.c.execute("SET LOCAL session_replication_role = origin")
            self.can_xem_lai("BOQ thiếu phụ lục nguồn.")

    def test_bo_roi_them_lai_noi_cuoi_va_chi_doc_boq_goc_moi_nhat(self):
        hd, da, _ = self.hop_dong()
        self.boq(hd, da, 1, [(1, "CU", "GOC", "1")])
        self.boq(hd, da, 2, [(1, "B", "GOC", "2"), (2, "A", "GOC", "3")])
        p1 = self.phu_luc(hd, da, "2026-02-01")
        self.boq(hd, da, 3, [(1, "B", "BO", None)], p1)
        p2 = self.phu_luc(hd, da, "2026-03-01")
        self.boq(hd, da, 4, [(1, "B", "THEM", "0004,00")], p2)
        rows = self.rows(hd=hd)
        self.assertEqual([r["ma_hm"] for r in rows], ["A", "B"])
        self.assertEqual(rows[1]["kl"], "0004,00")

    def test_ngay_uu_tien_truoc_lan_va_cung_ngay_theo_lan(self):
        # lan=4 nhập sau nhưng hiệu lực trước PL1; PL1 phải thắng.
        early = self.phu_luc(self.hd, self.da, "2026-01-15")
        self.boq(self.hd, self.da, 4, [(1, "Z", "THAY", "4")], early)
        self.assertEqual(self.rows()[0]["kl"], "2.5000")
        same = self.phu_luc(self.hd, self.da, "2026-02-01")
        self.boq(self.hd, self.da, 5, [(1, "Z", "THAY", "5")], same)
        self.assertEqual(self.rows()[0]["kl"], "5")
        # Cùng ngày, lan nhỏ có thể thêm rồi lan lớn bỏ.
        later = self.phu_luc(self.hd, self.da, "2026-02-01")
        self.boq(self.hd, self.da, 6, [(1, "C", "BO", None)], later)
        self.assertEqual(self.codes(), ["Z"])

    def test_du_thao_co_loi_khong_ap_va_doc_read_only(self):
        draft = self.phu_luc(self.hd, self.da, "2026-01-01", "DU_THAO")
        self.boq(self.hd, self.da, 4, [(1, "KHONG_CO", "BO", None)], draft)
        signed = self.phu_luc(self.hd, self.da, "2026-01-01")
        self.boq(self.hd, self.da, 5, [(1, "Z", "BO", None)], signed, state="CO_LOI")
        with psycopg.connect(self.dsn, autocommit=True) as con:
            with con.transaction():
                con.execute("SET TRANSACTION READ ONLY")
                self.assertEqual(self.doc(conn=con), self.doc())

    def test_rls_xem_review_ngoai_pham_vi_thu_hoi_va_acl(self):
        for vai in ("XEM", "REVIEW"):
            login = "MO_PHONG_BO_" + uuid.uuid4().hex
            user = self.insert("master.nguoi_dung", ten="Người giả BO", dang_nhap=login, vai_tro="XEM")
            self.c.execute("INSERT INTO master.phan_quyen(nguoi_dung_id,phap_nhan_id,module) "
                           "VALUES (%s,%s,ARRAY['M4'])", (user, self.pn))
            grant = self.insert("m4.quyen_du_an", nguoi_dung_id=user, phap_nhan_id=self.pn, du_an_id=self.da, vai=vai)
            with self.c.transaction():
                self.c.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true),"
                               "set_config('ktt.nguoi_dung_dang_nhap',%s,true)", (str(user), login))
                self.c.execute("SET LOCAL ROLE app_web")
                self.assertEqual([r["ma_hm"] for r in self.rows()], ["Z", "C"])
                self.assertEqual(self.rows(hd=self.hd_cu), [])
                self.c.execute("SET LOCAL ROLE NONE")
                self.c.execute("UPDATE m4.quyen_du_an SET thu_hoi_luc=now(),thu_hoi_boi='MO_PHONG_BO',"
                               "thu_hoi_ly_do='Thu hồi giả' WHERE id=%s", (grant,))
                self.c.execute("SET LOCAL ROLE app_web")
                self.assertEqual(self.rows(), [])
                self.c.execute("SET LOCAL ROLE NONE")
        self.assertFalse(self.c.execute("SELECT EXISTS (SELECT 1 FROM pg_proc p, "
                                       "LATERAL aclexplode(p.proacl) a WHERE p.oid="
                                       "'m4.boq_hieu_luc(uuid,date)'::regprocedure AND a.grantee=0)").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
