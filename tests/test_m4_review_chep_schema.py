"""M4-DL1: oracle từ SCHEMA trong mã vendor, không import/chạy/mở DB nguồn.

PG chỉ chạy khi lead cấp KHO_PG_DSN_TEST; tạo DB kho_test_* riêng, migrate sạch,
giữ DB làm bằng chứng. Không mở/dừng server, không xóa DB/role/tệp.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sqlite3
import unittest
import uuid
from pathlib import Path

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.m4 import sql_review_chep as S

try:
    import psycopg
    from psycopg import conninfo, sql
except ImportError:
    psycopg = None

ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / "src/kho_tri_thuc/m4/sql_review_chep.py"
SQL = S.M4_REVIEW_CHEP_SQL
TOAN = "\n".join(SQL)
DSN = os.environ.get("KHO_PG_DSN_TEST")


def _nguon():
    """Đọc DUY NHẤT literal schema trong mã, tạo SQLite :memory: giả để lấy oracle."""
    path = ROOT / "src/kho_tri_thuc/m4/review_goc/csdl_hop_dong.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    schema = next(ast.literal_eval(n.value) for n in tree.body
                  if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SCHEMA" for t in n.targets))
    with sqlite3.connect(":memory:") as con:
        con.executescript(schema)
        tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return {t: con.execute(f'PRAGMA table_info("{t}")').fetchall() for (t,) in tables}


NGUON = _nguon()
PK = {t: [r[1] for r in sorted(rows, key=lambda r: r[5]) if r[5]] for t, rows in NGUON.items()}


def _bang(t):
    return "m4.ho_so_hop_dong" if t == "hop_dong" else "m4.review_chep_" + t


def _cot(t, c):
    return "review_" + c if t == "hop_dong" else c


def _ddl(t):
    prefix = "ALTER TABLE m4.ho_so_hop_dong\n" if t == "hop_dong" else "CREATE TABLE " + _bang(t) + " ("
    return next(s for s in SQL if s.startswith(prefix))


def _hash(row):
    return hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _demo():
    """Đủ mọi cột gốc; không lấy dữ liệu/file/catalog thực tế, không gọi vendor."""
    return {
        "che_do": dict(id=1, sua=1),
        "hop_dong": dict(ma_hd="DEMO-HD", so_hd="DEMO/HĐ/01", phan_loai="DEMO xây dựng",
                         loai_gia="DEMO đơn giá", ngay_ky="", goi_thau=None, gia_tri_hd=-1234.125,
                         gom_vat="DEMO gồm VAT", vat=0.08, file_nguon="DEMO.docx", ngay_nap="2026-10-26 07:00"),
        "tham_so": dict(ma_hd="DEMO-HD", ma_ts="Y-DEMO", ten=None, gia_tri="", don_vi=None,
                        dieu_khoan="DEMO Điều 1", trich_dan="DEMO " * 1000, trang_thai="DEMO AI chưa xác nhận"),
        "phu_luc": dict(id=7, ma_hd="DEMO-HD", so_pl="DEMO-PL", ngay_ky="2026-10-26", ngay_hieu_luc="2026-01-01",
                        loai="DEMO Kết hợp", doi_boq=1, gt_truoc_vat=-12.5, gt_sau_vat=None, gt_hd_sau_pl=0.0,
                        noi_dung="DEMO " * 500, can_cu="DEMO căn cứ", file_nguon="DEMO-PL.docx", phieu="DEMO.xlsx",
                        trang_thai="Đã hủy", nguoi_nhap=None, ngay_nap="", ly_do_huy=None),
        "thay_doi_tham_so": dict(pl_id=7, ma_ts="Y-DEMO", gia_tri_cu=None, gia_tri_moi="", trich_dan="DEMO PL"),
        "boq_dong": dict(id=11, ma_hd="DEMO-HD", pl_id=7, thao_tac="BO", ma_hm="DEMO-HM", stt="01A",
                         nhom=None, ten=None, dvt=None, kl=-0.125, don_gia=12.5, thanh_tien_ghi=None,
                         khoa="DEMO|hm|", vi_tri_nguon="DEMO!A1", ghi_chu="DEMO bỏ", ma_rieng="DEMO-DA-01"),
        "dot_thanh_toan": dict(ma_hd="DEMO-HD", dot=1001, ngay_nghiem_thu="", ngay_nhan_hs=None,
                               gt_ky=-12.5, gt_luy_ke=123.75, giu_lai=None, thu_hoi_tu=0.0, gt_tt_ky=-10.0,
                               file_nguon="DEMO-dot.xlsx", ngay_nap="2026-10-26"),
        "kl_thanh_toan": dict(ma_hd="DEMO-HD", dot=1001, ma_hm="DEMO-HM", kl_ky=-1.5,
                              kl_luy_ke=None, don_gia_tt=0.0, vi_tri_nguon="DEMO!B2"),
        "khop_hang_muc": dict(ma_hd="DEMO-ORPHAN", khoa_hstt="DEMO|hstt|m3", ma_hm="DEMO-HM",
                              cach_khop=None, nguoi_xac_nhan=None, ngay=""),
        "canh_bao": dict(id=13, ma_hd="DEMO-ORPHAN", pl_id=9999, dot=-2, ma_kt="DEMO-P01",
                         muc_do=None, noi_dung="DEMO cảnh báo cũ", thoi_diem="không có timezone"),
        "nhat_ky": dict(id=17, thoi_diem="", nguoi=None, thao_tac=None, ma_hd=None, chi_tiet="DEMO không phải JSON"),
        "tham_so_nguon": dict(ma_hd="DEMO-HD", ma_ts="Y-DEMO", gia_tri_ai=None, gia_tri="", kiem_tra="DEMO",
                              muc=None, nguon="DEMO Local", da_xac_nhan=1, da_sua_tay=0, nguoi_xac_nhan=None,
                              luc_xac_nhan="", ghi_chu_soat=None, lich_su="DEMO chưa phải JSON", model="DEMO-model",
                              may_ai="DEMO-máy", luot="DEMO-lượt", file_hop_dong="DEMO.docx", sha1_file="a" * 40,
                              luc_trich="2026-10-26 07:00", luc_nap=None),
    }


class ReviewChepThuan(unittest.TestCase):
    def test_du_12_bang_va_tung_cot_kieu_null_default_goc(self):
        self.assertEqual(len(NGUON), 12)
        self.assertEqual(set(S.BANG_NGUON), set(NGUON))
        types = {"TEXT": "text", "REAL": "double precision", "INTEGER": "bigint"}
        for t, rows in NGUON.items():
            ddl = _ddl(t)
            for _, c, typ, notnull, default, pk in rows:
                with self.subTest(bang=t, cot=c):
                    match = re.search(r"\b" + _cot(t, c) + r"\s+(" + types[typ] + r")\b([^,\n]*)", ddl)
                    self.assertIsNotNone(match, f"Thiếu cột/kiểu {t}.{c}")
                    if t != "hop_dong":
                        self.assertEqual("NOT NULL" in match[2], bool(notnull or pk))
                        if default is not None:
                            self.assertIn("DEFAULT " + default, match[2])
            self.assertEqual(set(_demo()[t]), {r[1] for r in rows})

    def test_khoa_nguon_duy_nhat_dung_pk_goc_khong_dung_sha_file(self):
        for t in NGUON:
            with self.subTest(bang=t):
                if t == "hop_dong":
                    self.assertIn("UNIQUE (review_nguon_id, review_ma_hd)", _ddl(t))
                    self.assertIn("UNIQUE (review_nguon_id, review_so_hd)", _ddl(t))
                    self.assertIn("review_dong_sha256 ~ '^[0-9a-f]{64}$'", _ddl(t))
                else:
                    self.assertIn("PRIMARY KEY (" + ", ".join(["nguon_id", *PK[t]]) + ")", _ddl(t))
                    self.assertIn("dong_sha256 text NOT NULL", _ddl(t))
        self.assertIn("coalesce(pl_id, 0)", TOAN)
        self.assertIn("WHERE trang_thai <> 'Đã hủy'", TOAN)
        self.assertIn("'GOC','THAY','THEM','BO'", _ddl("boq_dong"))

    def test_fk_nguon_va_tai_dung_dich_khong_tao_can_cu_gia(self):
        self.assertNotIn("CREATE TABLE master.hop_dong", TOAN)
        self.assertNotIn("CREATE TABLE m4.ho_so_hop_dong", TOAN)
        for target in ("m4.tham_so", "m4.phu_luc", "m4.boq", "m4.boq_dong", "m4.dot", "m4.review_manual_map", "m4.nhat_ky"):
            self.assertIn("REFERENCES " + target + " (", TOAN)
        self.assertIn("REFERENCES m4.review_chep_dot_thanh_toan (nguon_id, ma_hd, dot, du_an_id)", TOAN)
        self.assertIn("REFERENCES m4.review_chep_phu_luc (nguon_id, id, du_an_id)", TOAN)
        self.assertNotIn("trich_xuat_id", _ddl("tham_so"))
        self.assertNotIn("danh_muc_tham_so", _ddl("tham_so"))
        self.assertNotRegex(TOAN, r"(?i)\b(?:INSERT INTO|DROP|DISABLE TRIGGER|DROP NOT NULL)\b")

    def test_acl_rls_bat_bien_va_khong_chuyen_co_sua_thanh_quyen(self):
        for t in S.BANG_BO_SUNG:
            self.assertIn(f"ALTER TABLE m4.{t} ENABLE ROW LEVEL SECURITY", SQL)
            self.assertIn(f"m4.{t}", next(s for s in SQL if s.startswith("REVOKE ALL ON")))
            self.assertIn(f"CREATE TRIGGER {t}_chi_ghi_them BEFORE INSERT OR UPDATE OR DELETE", TOAN)
            self.assertIn(f"CREATE TRIGGER {t}_chan_truncate BEFORE TRUNCATE", TOAN)
        for t in ("review_chep_nguon", "review_chep_che_do"):
            self.assertNotIn(f"GRANT SELECT ON m4.{t} TO app_web", TOAN)
        self.assertNotRegex(TOAN, r"GRANT (?:INSERT|UPDATE|DELETE|ALL)")
        self.assertNotIn("SECURITY DEFINER", TOAN)
        self.assertNotIn("current_setting", TOAN)
        self.assertIn("master.m4_duoc(du_an_id, 'XEM')", TOAN)

    def test_chi_hang_sql_va_registry_append_khong_ghim_ordinal(self):
        tree = ast.parse(SQL_PATH.read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)) for n in ast.walk(tree)))
        self.assertTrue(all(isinstance(s, str) and s.strip() for s in SQL))
        self.assertEqual(sum(m is SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertIs(PM.PG_MIGRATIONS[-1], SQL)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        # Định vị bằng module marker, không ghi cứng số; prefix vẫn nạp độc lập.
        path = ROOT / "src/kho_tri_thuc/ha_tang/pg_migrations.py"
        prefix = path.read_text(encoding="utf-8").split("# M4-DL1 — CD-011:")[0]
        ns = {"__package__": "kho_tri_thuc.ha_tang", "__name__": "kho_tri_thuc.ha_tang._dl1_baseline"}
        exec(compile(prefix, str(path), "exec"), ns)
        self.assertEqual(PM.PG_MIGRATIONS[:-1], ns["PG_MIGRATIONS"])


@unittest.skipUnless(DSN and psycopg is not None, "Thiếu KHO_PG_DSN_TEST/psycopg — PG do lead chạy (NOT_RUN)")
class ReviewChepPG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.ha_tang import postgres as pg
        cls.db = "kho_test_m4_dl1_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.dsn = conninfo.make_conninfo(DSN, dbname=cls.db)
        cls.con = psycopg.connect(cls.dsn, autocommit=True)
        cls.addClassCleanup(cls.con.close)
        cls.version = pg.migrate(cls.con)
        cls.pn = cls.con.execute("INSERT INTO master.phap_nhan (ma,ten) VALUES ('DEMO_DL1','Pháp nhân DEMO DL1') RETURNING id").fetchone()[0]
        cls.da = cls.con.execute("INSERT INTO master.du_an (phap_nhan_id,ma_junsky,ten) VALUES (%s,'DEMO_DL1','Dự án DEMO DL1') RETURNING id", (cls.pn,)).fetchone()[0]

    def _insert(self, table, row, *, replay=False):
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({})" + (" ON CONFLICT DO NOTHING" if replay else ""))
        self.con.execute(query.format(sql.Identifier(*table.split(".")), sql.SQL(",").join(map(sql.Identifier, row)),
                                      sql.SQL(",").join(sql.Placeholder() for _ in row)), list(row.values()))

    def _fixture(self):
        source = "DEMO-DL1-" + uuid.uuid4().hex
        self._insert("m4.review_chep_nguon", dict(id=source, mo_ta="DEMO giả", nhap_boi="MO_PHONG_NHAP"))
        hd = self._master_hd()
        originals = _demo()
        rows = {}
        for t, original in originals.items():
            if t == "hop_dong":
                row = {"review_" + c: v for c, v in original.items()}
                row.update(hop_dong_id=hd, phap_nhan_id=self.pn, du_an_id=self.da, ten="Hồ sơ DEMO DL1",
                           tao_boi="MO_PHONG_NHAP", review_nguon_id=source, review_dong_sha256=_hash(original),
                           review_nhap_boi="MO_PHONG_NHAP", review_nhap_luc="2026-10-26T07:00:00+07:00")
            else:
                row = dict(original, nguon_id=source, dong_sha256=_hash(original), nhap_boi="MO_PHONG_NHAP")
                if t not in ("che_do", "khop_hang_muc", "canh_bao", "nhat_ky"):
                    row["du_an_id"] = self.da
                if t in ("tham_so", "phu_luc", "boq_dong", "dot_thanh_toan", "tham_so_nguon"):
                    row["hop_dong_id"] = hd
            rows[t] = row
            self._insert(_bang(t), row)
        return source, hd, originals, rows

    def _master_hd(self):
        code = "DEMO-HD-" + uuid.uuid4().hex
        return self.con.execute("""INSERT INTO master.hop_dong
            (phap_nhan_id,du_an_id,loai,module_chu,ma_noi_bo,so_hop_dong,trang_thai)
            VALUES (%s,%s,'XAY_DUNG','M4',%s,%s,'SOAN_THAO') RETURNING id""", (self.pn, self.da, code, code)).fetchone()[0]

    def _loi(self, error, table, row):
        with self.assertRaises(error):
            with self.con.transaction():
                self._insert(table, row)

    def test_migrate_sach_va_chay_lai_migration(self):
        from kho_tri_thuc.ha_tang import postgres as pg
        self.assertEqual(self.version, PM.PG_SCHEMA_VERSION)
        self.assertEqual(pg.migrate(self.con), self.version)
        for t, rows in NGUON.items():
            schema, table = _bang(t).split(".")
            cols = dict(self.con.execute("SELECT column_name,data_type FROM information_schema.columns WHERE table_schema=%s AND table_name=%s", (schema, table)).fetchall())
            for _, c, typ, *_ in rows:
                self.assertEqual(cols[_cot(t, c)], {"TEXT": "text", "REAL": "double precision", "INTEGER": "bigint"}[typ])

    def test_ghi_doc_demo_du_12_bang_giu_null_chuoi_so_am(self):
        source, hd, originals, _ = self._fixture()
        for t, original in originals.items():
            with self.subTest(bang=t):
                query = sql.SQL("SELECT {} FROM {} WHERE {}=%s").format(
                    sql.SQL(",").join(sql.Identifier(_cot(t, c)) for c in original), sql.Identifier(*_bang(t).split(".")),
                    sql.Identifier("review_nguon_id" if t == "hop_dong" else "nguon_id"))
                self.assertEqual(self.con.execute(query, (source,)).fetchall(), [tuple(original.values())])
        self.assertIsNone(self.con.execute("SELECT gia_tri_minor FROM master.hop_dong WHERE id=%s", (hd,)).fetchone()[0])
        for table in ("m4.trich_xuat", "m4.review_run", "m4.boq", "m4.dot", "m4.nop"):
            self.assertEqual(self.con.execute(sql.SQL("SELECT count(*) FROM {} WHERE hop_dong_id=%s").format(sql.Identifier(*table.split("."))), (hd,)).fetchone()[0], 0)

    def test_khoa_nguon_ca_12_bang_va_replay_khong_them_dong(self):
        source, _, _, rows = self._fixture()
        for t, row in rows.items():
            with self.subTest(bang=t):
                duplicate = dict(row, hop_dong_id=self._master_hd()) if t == "hop_dong" else row
                self._loi(psycopg.errors.UniqueViolation, _bang(t), duplicate)
                self._insert(_bang(t), row, replay=True)
                column = "review_nguon_id" if t == "hop_dong" else "nguon_id"
                q = sql.SQL("SELECT count(*) FROM {} WHERE {}=%s").format(sql.Identifier(*_bang(t).split(".")), sql.Identifier(column))
                self.assertEqual(self.con.execute(q, (source,)).fetchone()[0], 1)
        # UQ số HĐ nguồn độc lập với PK ma_hd và UUID master.
        self._loi(psycopg.errors.UniqueViolation, _bang("hop_dong"),
                  dict(rows["hop_dong"], hop_dong_id=self._master_hd(), review_ma_hd="DEMO-KHAC"))
        # Cùng PK gốc trong kho khác được phép; SHA DB không tham gia khóa.
        self._fixture()

    def test_fk_dung_nguon_hd_pl_dot_va_pham_vi(self):
        source, hd, _, rows = self._fixture()
        source2, hd2, _, _ = self._fixture()
        self._loi(psycopg.errors.ForeignKeyViolation, _bang("tham_so"), dict(rows["tham_so"], ma_ts="DEMO-MOI", hop_dong_id=hd2))
        self._loi(psycopg.errors.ForeignKeyViolation, _bang("boq_dong"), dict(rows["boq_dong"], id=12, ma_hm="DEMO-MOI", pl_id=999))
        self._loi(psycopg.errors.ForeignKeyViolation, _bang("thay_doi_tham_so"), dict(rows["thay_doi_tham_so"], ma_ts="DEMO-MOI", pl_id=999))
        self._loi(psycopg.errors.ForeignKeyViolation, _bang("kl_thanh_toan"), dict(rows["kl_thanh_toan"], dot=-1))
        self._loi(psycopg.errors.ForeignKeyViolation, _bang("tham_so"), dict(rows["tham_so"], nguon_id=source2, ma_hd="DEMO-KHONG-CO", ma_ts="DEMO-MOI"))
        self._loi(psycopg.errors.ForeignKeyViolation, _bang("khop_hang_muc"),
                  dict(rows["khop_hang_muc"], khoa_hstt="DEMO-KHAC", hop_dong_id=hd, du_an_id=self.da))

    def test_tai_dung_phu_luc_dot_m4_co_san_khong_nhan_nham_hd(self):
        _, hd, _, rows = self._fixture()
        _, _, _, rows2 = self._fixture()
        native_pl = self.con.execute("""INSERT INTO m4.phu_luc
            (hop_dong_id,du_an_id,so_pl,ngay_ky,ngay_hieu_luc,trang_thai,doi_boq,tao_boi)
            VALUES (%s,%s,'DEMO-NATIVE','2026-01-01','2026-01-01','DA_KY',true,'MO_PHONG_NHAP') RETURNING id""",
                                    (hd, self.da)).fetchone()[0]
        self._insert(_bang("phu_luc"), dict(rows["phu_luc"], id=19, so_pl="DEMO-NATIVE", trang_thai="Đã ký", m4_phu_luc_id=native_pl))
        self._loi(psycopg.errors.ForeignKeyViolation, _bang("phu_luc"),
                  dict(rows2["phu_luc"], id=20, m4_phu_luc_id=native_pl))
        native_dot = self.con.execute("""INSERT INTO m4.dot (hop_dong_id,du_an_id,so_dot,tao_boi)
            VALUES (%s,%s,1,'MO_PHONG_NHAP') RETURNING id""", (hd, self.da)).fetchone()[0]
        self._insert(_bang("dot_thanh_toan"), dict(rows["dot_thanh_toan"], dot=1, m4_dot_id=native_dot))
        self.assertEqual(self.con.execute("SELECT trang_thai FROM m4.dot WHERE id=%s", (native_dot,)).fetchone()[0], "NHAP")

    def test_pl_huy_nap_lai_bo_va_unique_boq_null(self):
        _, _, _, rows = self._fixture()
        active = dict(rows["phu_luc"], id=8, trang_thai="Đã ký")
        self._insert(_bang("phu_luc"), active)  # cùng số với PL hủy vẫn được
        self._loi(psycopg.errors.UniqueViolation, _bang("phu_luc"), dict(active, id=9))
        goc = dict(rows["boq_dong"], id=12, pl_id=None, thao_tac="GOC")
        self._insert(_bang("boq_dong"), goc)
        self._loi(psycopg.errors.UniqueViolation, _bang("boq_dong"), dict(goc, id=13))
        self._loi(psycopg.errors.CheckViolation, _bang("boq_dong"), dict(goc, id=14, ma_hm="DEMO-KHAC", thao_tac="SAI"))

    def test_ban_nguon_bat_bien_ke_ca_nhat_ky_va_ho_so(self):
        source, hd, _, _ = self._fixture()
        for table in ("m4.review_chep_nhat_ky", "m4.review_chep_che_do", "m4.review_chep_tham_so"):
            with self.assertRaises(psycopg.errors.RaiseException):
                with self.con.transaction():
                    self.con.execute(sql.SQL("UPDATE {} SET dong_sha256=%s WHERE nguon_id=%s").format(sql.Identifier(*table.split("."))), ("b" * 64, source))
        with self.assertRaises(psycopg.errors.RaiseException):
            with self.con.transaction():
                self.con.execute("UPDATE m4.ho_so_hop_dong SET review_so_hd='DEMO đổi' WHERE hop_dong_id=%s", (hd,))

    def test_acl_rls_khong_co_quyen_khong_doc_ghi(self):
        self._fixture()
        for t in S.BANG_BO_SUNG:
            self.assertTrue(self.con.execute("SELECT relrowsecurity FROM pg_class WHERE oid=%s::regclass", ("m4." + t,)).fetchone()[0])
            for privilege in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                self.assertFalse(self.con.execute("SELECT has_table_privilege('app_web',%s,%s)", ("m4." + t, privilege)).fetchone()[0])
        # SET LOCAL ROLE chỉ trong DB test riêng; không tạo login/danh tính giả.
        with self.con.transaction():
            self.con.execute("SET LOCAL ROLE app_web")
            for t in S.BANG_BO_SUNG:
                if t in ("review_chep_nguon", "review_chep_che_do"):
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        with self.con.transaction():
                            self.con.execute(sql.SQL("SELECT * FROM m4.{}").format(sql.Identifier(t)))
                else:
                    self.assertEqual(self.con.execute(sql.SQL("SELECT count(*) FROM m4.{}").format(sql.Identifier(t))).fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
