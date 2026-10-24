"""M0–M5 gói 01 — registry migration: prefix 1–12 nguyên, COMMON13 → M5 14 mặc định, M0013 full-M9 chỉ là định nghĩa lịch sử.

Sửa 02: S05 (master có bảng nhưng thiếu lịch sử/marker → từ chối trước ghi), S06 (chuỗi tùy chỉnh chỉ đúng tiền tố lịch sử đã review),
stage đóng/không writer free-JSON, discriminator core (backfill trước guard, PHIEU_KHO cũ = M1, no/co DEFAULT 0 giữ cho caller cũ).
Phần tĩnh (không DB): checksum prefix/legacy theo root pin `tests/fixtures/m0_m5/lineage-pins.json`, thành phần chuỗi mặc định, cổng lineage
thuần (`kiem_lich_su`) với lịch sử trống/đủ/legacy/trùng/hụt/lạ/tương lai/sai hình dạng, chặn chuỗi tùy chỉnh > M0012, quét SQL COMMON/M5
không chứa đối tượng loan/money/M9 và mọi hàm SECURITY DEFINER có search_path cố định + REVOKE PUBLIC.
Phần PostgreSQL (chỉ khi root cấp KHO_PG_DSN_TEST): DB mới 0→14, CRM12 có dữ liệu → 14, lịch sử legacy13 (kể cả có 14) và lineage lạ bị từ chối
TRƯỚC mọi ghi (catalog/lịch sử không đổi), cổng mở ứng dụng, catalog mới chỉ trong allowlist COMMON/M5. Không DROP DB/role: giữ làm bằng chứng.
Sửa 03: I-S02 — enum/sequence/routine/view/domain không phải bảng (public, master, schema lạ) bị từ chối trước ghi; DB mới/schema rỗng/extension
dương. Tĩnh: thứ tự namespace→mapping→phiếu→hàng, guard kỳ/con trỏ/basis trước tra biên nhận FILE, cổng eligible, getter SOURCE_MAP hiện hành.
"""

from __future__ import annotations

import json
import os
import re
import unittest
import uuid
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang import postgres as pg
from kho_tri_thuc.ha_tang.pg_migrations import (LEGACY_FULL_M9_M0013_SHA256, M0010_V1_BAN_GIAO_DAU, M0013, M0013_COMMON, M0014_M5, PG_MIGRATIONS,
                                                PG_MIGRATIONS_LICH_SU_FULL_M9, PG_SCHEMA_VERSION)
from kho_tri_thuc.ha_tang.primitives import DataError, sha256

ROOT = Path(__file__).resolve().parents[1]
PINS_PATH = ROOT / "tests" / "fixtures" / "m0_m5" / "lineage-pins.json"
PINS_SHA = "418194019d14cb859f10ed2d545ace0e8c5e1c96b09f534a0a549d2d4f6e5f15"
ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
H = lambda statements: sha256("\n".join(statements).encode())  # noqa: E731


def lich_su(n=None):
    chain = PG_MIGRATIONS if n is None else PG_MIGRATIONS[:n]
    return [(i + 1, H(m)) for i, m in enumerate(chain)]


class TinhLineage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = PINS_PATH.read_bytes()
        assert sha256(raw) == PINS_SHA, "lineage-pins.json khác root pin"
        cls.pins = json.loads(raw.decode("utf-8"))

    def test_prefix_1_12_nguyen_checksum_va_so_cau(self):
        for p in self.pins["prefix_1_12"]:
            m = PG_MIGRATIONS[p["version"] - 1]
            self.assertEqual((len(m), H(m)), (p["statement_count"], p["checksum"]), p["version"])

    def test_m0013_full_m9_chi_la_dinh_nghia_lich_su(self):
        legacy = self.pins["legacy_full_m9_m13"]
        self.assertEqual((len(M0013), H(M0013)), (legacy["statement_count"], legacy["checksum"]))
        self.assertEqual(LEGACY_FULL_M9_M0013_SHA256, legacy["checksum"])
        self.assertEqual(PG_MIGRATIONS_LICH_SU_FULL_M9[12], M0013)
        self.assertNotIn(M0013, PG_MIGRATIONS)
        self.assertEqual(PG_MIGRATIONS[:12], PG_MIGRATIONS_LICH_SU_FULL_M9[:12])
        self.assertIs(PG_MIGRATIONS[12], M0013_COMMON)
        self.assertIs(PG_MIGRATIONS[13], M0014_M5)
        self.assertGreaterEqual(len(PG_MIGRATIONS), 14)
        self.assertEqual(PG_SCHEMA_VERSION, len(PG_MIGRATIONS))
        self.assertNotEqual(H(M0013_COMMON), LEGACY_FULL_M9_M0013_SHA256)

    def test_kiem_lich_su_duong_va_am(self):
        self.assertEqual(pg.kiem_lich_su([]), 0)
        self.assertEqual(pg.kiem_lich_su(lich_su(12)), 12)
        self.assertEqual(pg.kiem_lich_su(lich_su(13)), 13)
        self.assertEqual(pg.kiem_lich_su(lich_su(14)), 14)
        self.assertEqual(pg.kiem_lich_su(lich_su()), PG_SCHEMA_VERSION)
        compat = lich_su(12)
        compat[9] = (10, H(M0010_V1_BAN_GIAO_DAU))  # tiền thân M0010 liệt kê chính xác
        self.assertEqual(pg.kiem_lich_su(compat), 12)
        cases = {
            "LEGACY_FULL_M9_LINEAGE": [lich_su(12) + [(13, LEGACY_FULL_M9_M0013_SHA256)],
                                       lich_su(12) + [(13, LEGACY_FULL_M9_M0013_SHA256), (14, H(M0014_M5))]],
            "MIGRATION_HISTORY": [lich_su(12)[:5] + lich_su(12)[6:], lich_su(3) + [(3, H(PG_MIGRATIONS[2]))], [(1, H(PG_MIGRATIONS[0]), "x")],
                                  [("1", H(PG_MIGRATIONS[0]))], "khong-phai-list", [(True, H(PG_MIGRATIONS[0]))]],
            "MIGRATION_CHANGED": [lich_su(12) + [(13, "0" * 64)], lich_su(2)[:1] + [(2, "f" * 64)]],
            "FUTURE_SCHEMA": [lich_su() + [(PG_SCHEMA_VERSION + 1, "a" * 64)]],
        }
        for code, histories in cases.items():
            for i, h in enumerate(histories):
                with self.subTest(code=code, i=i):
                    with self.assertRaises(DataError) as cm:
                        pg.kiem_lich_su(h)
                    self.assertEqual(cm.exception.code, code)

    def test_chuoi_tuy_chinh_chi_dung_tien_to_lich_su(self):
        class KhongDung:
            def __getattr__(self, _):
                raise AssertionError("không được chạm CSDL")
        gop_m13 = PG_MIGRATIONS[:11] + (M0013,)  # 12 phần tử nhưng phần tử 12 là SQL full-M9 → S06 phải chặn (không chỉ đếm độ dài)
        gop_sql = PG_MIGRATIONS[:9] + (M0010_V1_BAN_GIAO_DAU + ("SELECT 1",),)
        for chain in (PG_MIGRATIONS_LICH_SU_FULL_M9, PG_MIGRATIONS[:12] + (M0013_COMMON,), PG_MIGRATIONS[:13] + (M0014_M5,), gop_m13, gop_sql, ()):
            with self.subTest(n=len(chain)):
                with self.assertRaises(DataError) as cm:
                    pg.migrate(KhongDung(), migrations=chain)
                self.assertEqual(cm.exception.code, "MIGRATION_TUY_CHINH")
        pg.kiem_chuoi_lich_su(PG_MIGRATIONS[:9] + (M0010_V1_BAN_GIAO_DAU,))  # tiền thân M0010 đã liệt kê: hợp lệ
        pg.kiem_chuoi_lich_su(PG_MIGRATIONS[:12])

    def test_sql_stage_dong_va_core_owner(self):
        sql = "\n".join(M0013_COMMON + M0014_M5)
        for cu in ("nguon_ghi_lan_nhan", "m5_ghi_quan_sat", "(p jsonb) RETURNS TABLE (receipt_id"):
            self.assertNotIn(cu, sql)  # không còn writer free-JSON cho capture/typed
        for can in ("CREATE TABLE giao_tiep.stage_tin_cay", "master.la_chu_bang(TG_RELID::regclass)", "nguon_tieu_thu_capture(p_stage uuid, p_h text)",
                    "m5_tieu_thu_quan_sat(p_stage uuid, p_h text)", "m5_file_tieu_thu(p_stage uuid, p_h text)", "BIEN_NHAN_M5_CHI_CHU", "LO_M5_CHI_CHU",
                    "CHUNG_TU_M5_CHI_CHU", "M5_CHI_SO_LUONG", "chung_tu_id uuid NOT NULL UNIQUE", "chung_tu_dong_id uuid NOT NULL UNIQUE",
                    "o.id IS DISTINCT FROM d.latest_observation_id", "ktt_nguon_co_nang_luc", "REVOKE ALL ON %s FROM %I"):
            self.assertIn(can, sql, can)
        stmts = list(M0013_COMMON)
        i_add = stmts.index("ALTER TABLE kho.chung_tu ADD COLUMN module_nghiep_vu text")
        i_upd = stmts.index("UPDATE kho.chung_tu SET module_nghiep_vu = CASE WHEN loai = 'HOP_DONG_TEP' THEN 'CRM' ELSE 'M1' END")
        i_nn = stmts.index("ALTER TABLE kho.chung_tu ALTER COLUMN module_nghiep_vu SET NOT NULL")
        i_trg = next(i for i, s in enumerate(stmts) if s.startswith("CREATE TRIGGER chung_tu_chu_so_huu_common"))
        self.assertLess(i_add, i_upd)
        self.assertLess(i_upd, i_nn)
        self.assertLess(i_nn, i_trg)  # backfill (mọi hàng cũ khác → M1, kể cả PHIEU_KHO cũ) TRƯỚC guard mới
        self.assertNotIn("SET DEFAULT", "\n".join(s for s in stmts if "no_minor" in s or "co_minor" in s))  # giữ DEFAULT 0 cũ
        # review: khóa advisory logic TRƯỚC khóa hàng (cùng thứ tự với intake/file)
        review = next(s for s in M0014_M5 if "FUNCTION kho.m5_xem_xet_nguon" in s)
        self.assertLess(review.index("pg_advisory_xact_lock"), review.index("FOR UPDATE"))
        # app_web không còn INSERT/UPDATE mapping (S07: chỉ qua hàm định nghĩa của chủ bảng)
        self.assertNotIn("GRANT SELECT, INSERT, UPDATE ON master.anh_xa_nguon", sql)

    def test_sql_repair03_thu_tu_khoa_guard_va_cong(self):
        """Tĩnh (không thay runtime): namespace biên nhận khóa TRƯỚC tra biên nhận/khóa phiếu; guard kỳ/con trỏ/basis TRƯỚC cached FILE;
        eligible qua cổng số lượng; getter SOURCE_MAP dùng predicate nguồn hiện hành; chốt kết quả cuối không cấp app_web."""
        fn = lambda ten: next(s for s in M0013_COMMON + M0014_M5 if f"FUNCTION {ten}(" in s)  # noqa: E731
        lookup = "FROM kho.bien_nhan_thao_tac b"
        mp = fn("kho.m5_anh_xa_v4")
        self.assertLess(mp.index("'BIEN_NHAN|'"), mp.index("'ANH_XA|'"))
        self.assertLess(mp.index("'ANH_XA|'"), mp.index(lookup))  # tra biên nhận SAU namespace + subject
        self.assertLess(mp.index(lookup), mp.index("FOR UPDATE"))
        rv = fn("kho.m5_xem_xet_nguon")
        self.assertLess(rv.index("'BIEN_NHAN|'"), rv.index("'PHIEU_KHO|'"))
        self.assertIn("kho.m5_quan_sat_du_dieu_kien(o.id)", rv)
        self.assertNotIn("v_eligible := CASE WHEN o.trang_thai_nguon = 'DA_DUYET' THEN o.content_id END", rv)
        for ten in ("kho.m5_file_bat_dau", "kho.m5_file_tieu_thu"):
            f = fn(ten)
            with self.subTest(fn=ten):
                self.assertLess(f.index("'BIEN_NHAN|'"), f.index("FOR SHARE"))
                self.assertLess(f.index("FOR SHARE"), f.index("'PHIEU_KHO|'"))
                self.assertLess(f.index("'PHIEU_KHO|'"), f.index("FOR UPDATE"))
                for guard in ("KY_DA_KHOA", "KHO_VERSION_CHANGED: con trỏ", "kho.m5_co_so_file_noi_bo(d.id)"):
                    self.assertLess(f.index(guard), f.index(lookup), guard)  # guard hiện hành trước cached result
        self.assertIn("'co_so_truoc', p->'co_so_truoc'", fn("kho.m5_file_bat_dau"))  # token basis thuộc request H
        getter = fn("giao_tiep.nguon_anh_xa_hien_hanh")
        self.assertNotIn("WHERE n.dang_nhap = master.ktt_danh_tinh() AND c.source_instance_id = p_instance", getter)
        self.assertIn("master.ktt_nguon_duoc(p_instance, p_ref, p_sha, 'SOURCE_MAP', m.phap_nhan_id)", getter)
        grants = "\n".join(s for s in M0013_COMMON + M0014_M5 if "GRANT EXECUTE" in s)
        for noi_bo in ("nguon_chot_ket_qua(", "m5_quan_sat_du_dieu_kien(", "m5_co_so_file_noi_bo("):
            self.assertNotIn(noi_bo, grants.split("-- KHÔNG cấp app_web")[0], noi_bo)
        con_tro = fn("kho.phieu_kho_con_tro_kiem")
        self.assertIn("kho.m5_quan_sat_du_dieu_kien(NEW.accepted_source_observation_id)", con_tro)
        self.assertIn("CREATE TABLE giao_tiep.ket_qua_cuoi_tiep_nhan", "\n".join(M0013_COMMON))

    def test_sql_common_m5_trung_tinh_va_definer_an_toan(self):
        sql = "\n".join(M0013_COMMON + M0014_M5)
        for cam in ("vay_", "lich_tra_no", "su_kien_vay", "lien_ket_phan_bo", "dich_phan_bo_tien", "tien_con_lai", "khe_uoc", "lai_suat", "'M9'", "_rls_v13",
                    "m9_", "chung_tu_tien_encoding", "dinh_danh_cong_ty_nguon"):
            self.assertNotIn(cam, sql, cam)
        for stmt in M0013_COMMON + M0014_M5:
            if "SECURITY DEFINER" in stmt:
                self.assertIn("SET search_path =", stmt, stmt[:120])
        definer = set(re.findall(r"FUNCTION ((?:master|kho|giao_tiep)\.\w+)\([^)]*\)\s+(?:RETURNS[^$]*?)LANGUAGE \w+(?: STABLE)? SECURITY DEFINER", sql))
        revoked = "\n".join(s for s in M0013_COMMON + M0014_M5 if s.startswith("REVOKE EXECUTE"))
        for fn in definer - {"kho.bien_nhan_kiem", "kho.phieu_kho_con_tro_kiem"}:  # hàm trigger không gọi trực tiếp được
            self.assertIn(fn + "(", revoked, fn)
        self.assertNotIn("TO PUBLIC", sql)
        self.assertNotIn("UNIQUE (source_instance_id, profile_sha256, raw_sha256)", sql)  # không UNIQUE raw/profile nuốt lần fetch


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test PostgreSQL M0–M5 không chạy (không tính đạt)")
class PgLineage(unittest.TestCase):
    @classmethod
    def _db(cls, prefix):
        name = prefix + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{name}" ENCODING \'UTF8\' TEMPLATE template0')
        return name, ADMIN_DSN.rsplit("/", 1)[0] + "/" + name

    def ket_noi(self, prefix):
        _, dsn = self._db(prefix)
        c = psycopg.connect(dsn, autocommit=True)
        self.addCleanup(c.close)  # chỉ đóng kết nối; DB giữ lại làm bằng chứng
        return c

    @staticmethod
    def lich_su_db(c):
        return [tuple(r) for r in c.execute("SELECT version, checksum FROM master.schema_migrations ORDER BY version")]

    @staticmethod
    def catalog(c):
        return {"rel": sorted(r[0] for r in c.execute("""SELECT n.nspname || '.' || c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                                                         WHERE n.nspname IN ('master','kho','nhat_ky','bao_mat','giao_tiep')""")),
                "fn": sorted(r[0] for r in c.execute("""SELECT n.nspname || '.' || p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                                                        WHERE n.nspname IN ('master','kho','nhat_ky','bao_mat','giao_tiep')"""))}

    def test_db_moi_0_den_14_va_lap_lai(self):
        c = self.ket_noi("kho_test_m0m5_moi_")
        self.assertEqual(pg.migrate(c), 14)
        self.assertEqual(pg.migrate(c), 14)
        self.assertEqual(self.lich_su_db(c), lich_su())

    def test_crm12_co_du_lieu_len_14_catalog_trong_allowlist(self):
        c = self.ket_noi("kho_test_m0m5_crm12_")
        self.assertEqual(pg.migrate(c, target=12), 12)
        pn = c.execute("INSERT INTO master.phap_nhan (ma, ten) VALUES ('LEGACY_M0M5','PN DEMO cũ') RETURNING id").fetchone()[0]
        c.execute("INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, hash) VALUES (%s,'SAO_KE','M0M5-1','2026-08-01',%s)", (pn, "0" * 64))
        truoc = self.catalog(c)
        self.assertEqual(pg.migrate(c), 14)
        sau = self.catalog(c)
        moi_rel = set(sau["rel"]) - set(truoc["rel"])
        moi_fn = set(sau["fn"]) - set(truoc["fn"])
        allow_tbl = {"master.nguon_instance", "master.nguon_profile", "master.nguon_pham_vi", "master.nang_luc_nguon", "master.nguon_master_noi_dung",
                     "master.nguon_su_kien_do_luong", "giao_tiep.stage_tin_cay", "giao_tiep.tep_tiep_nhan", "kho.anh_chup_nguon", "kho.anh_chup_nguon_vai_tro",
                     "giao_tiep.lan_tiep_nhan_nguon",
                     "kho.ban_ghi_nguon", "master.anh_xa_nguon", "giao_tiep.tep_tach_phap_nhan", "kho.bien_nhan_thao_tac", "kho.phieu_kho_danh_tinh",
                     "kho.phieu_kho_phien_ban", "kho.phieu_kho_quan_sat", "kho.phieu_kho_dong_danh_tinh", "kho.phieu_kho_dong_phien_ban"}
        self.assertTrue(allow_tbl <= moi_rel)
        self.assertTrue(all(r.split(".")[0] in {"master", "kho", "giao_tiep"} for r in moi_rel))
        self.assertFalse({r for r in moi_rel if re.search(r"vay|lich_tra_no|phan_bo|khe_uoc|lai_suat|don_vi_tien", r)})
        self.assertFalse({f for f in moi_fn if re.search(r"m9|vay|tien_con_lai|phan_bo", f)})
        self.assertEqual(c.execute("SELECT count(*) FROM kho.chung_tu WHERE khoa_nguon = 'M0M5-1'").fetchone()[0], 1)
        self.assertEqual(self.lich_su_db(c), lich_su())

    def test_legacy13_va_lineage_la_tu_choi_truoc_moi_ghi(self):
        for label, extra in (("legacy13", [(13, LEGACY_FULL_M9_M0013_SHA256)]), ("legacy13_14", [(13, LEGACY_FULL_M9_M0013_SHA256), (14, H(M0014_M5))]),
                             ("la13", [(13, "1" * 64)])):
            with self.subTest(label=label):
                c = self.ket_noi("kho_test_m0m5_tu_choi_")
                pg.migrate(c, target=12)
                for v, chk in extra:  # chỉ GHI HÀNG lịch sử mô phỏng; không execute SQL M0013 full-M9
                    c.execute("INSERT INTO master.schema_migrations VALUES (%s,%s,'2026-10-19T00:00:00Z')", (v, chk))
                truoc, hist = self.catalog(c), self.lich_su_db(c)
                with self.assertRaises(DataError) as cm:
                    pg.migrate(c)
                self.assertEqual(cm.exception.code, "LEGACY_FULL_M9_LINEAGE" if label.startswith("legacy") else "MIGRATION_CHANGED")
                with self.assertRaises(DataError):
                    pg.kiem_lineage_ung_dung(c)
                self.assertEqual((self.catalog(c), self.lich_su_db(c)), (truoc, hist))

    def test_s05_master_co_bang_thieu_lich_su_tu_choi(self):
        for label, setup in (("bang_trong_master", ["CREATE SCHEMA master", "CREATE TABLE master.la (x int)"]),
                             ("lich_su_khong_marker", ["CREATE SCHEMA master", "CREATE TABLE master.schema_migrations (version integer PRIMARY KEY, checksum text NOT NULL, applied_at text NOT NULL)"]),
                             ("bang_ngoai", ["CREATE TABLE public.ngoai (x int)"])):
            with self.subTest(label=label):
                c = self.ket_noi("kho_test_m0m5_s05_")
                for s in setup:
                    c.execute(s)
                truoc = self.catalog(c)
                with self.assertRaises(DataError) as cm:
                    pg.migrate(c)
                self.assertIn(cm.exception.code, {"MIGRATION_HISTORY", "FOREIGN_DATABASE"})
                self.assertEqual(self.catalog(c), truoc)

    @staticmethod
    def catalog_rong(c):
        """Toàn bộ đối tượng người dùng (mọi schema không hệ thống) — để chứng minh từ chối xảy ra TRƯỚC mọi DDL/marker/seed."""
        return {"n": pg._dem_doi_tuong_nguoi_dung(c.cursor()),
                "ns": sorted(r[0] for r in c.execute("""SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg\\_%' AND nspname <> 'information_schema'"""))}

    def test_i_s02_doi_tuong_khong_phai_bang_tu_choi_truoc_ghi(self):
        """I-S02: DB không có bảng nhưng có routine/enum/sequence/view/domain ngoại lai (có hoặc không có schema master) ⇒ từ chối, catalog nguyên."""
        cases = (("enum_public", ["CREATE TYPE public.ngoai_enum AS ENUM ('A')"]),
                 ("sequence_public", ["CREATE SEQUENCE public.ngoai_seq"]),
                 ("ham_public", ["CREATE FUNCTION public.ngoai_fn() RETURNS int LANGUAGE sql AS 'SELECT 1'"]),
                 ("view_public", ["CREATE VIEW public.ngoai_view AS SELECT 1 AS x"]),
                 ("domain_public", ["CREATE DOMAIN public.ngoai_dom AS int"]),
                 ("master_enum", ["CREATE SCHEMA master", "CREATE TYPE master.ngoai_enum AS ENUM ('A')"]),
                 ("master_seq", ["CREATE SCHEMA master", "CREATE SEQUENCE master.ngoai_seq"]),
                 ("schema_ngoai_chi_ham", ["CREATE SCHEMA ngoai", "CREATE FUNCTION ngoai.f() RETURNS int LANGUAGE sql AS 'SELECT 1'"]))
        for label, setup in cases:
            with self.subTest(label=label):
                c = self.ket_noi("kho_test_m0m5_is02_")
                for s in setup:
                    c.execute(s)
                truoc = self.catalog_rong(c)
                self.assertGreater(truoc["n"], 0)
                with self.assertRaises(DataError) as cm:
                    pg.migrate(c)
                self.assertIn(cm.exception.code, {"MIGRATION_HISTORY", "FOREIGN_DATABASE"})
                self.assertEqual(self.catalog_rong(c), truoc)

    @staticmethod
    def catalog_doc_lap(c):
        """Oracle ĐỘC LẬP với hàm sản phẩm: text-search config/mapping ngoài pg_catalog, quan hệ/hàm/kiểu ngoài schema hệ thống, namespace, lịch sử."""
        q = lambda s: c.execute(s).fetchone()[0]  # noqa: E731
        return {"ts_cfg": q("SELECT count(*) FROM pg_ts_config t JOIN pg_namespace n ON n.oid = t.cfgnamespace WHERE n.nspname <> 'pg_catalog'"),
                "ts_map": q("""SELECT count(*) FROM pg_ts_config_map m JOIN pg_ts_config t ON t.oid = m.mapcfg JOIN pg_namespace n ON n.oid = t.cfgnamespace
                               WHERE n.nspname <> 'pg_catalog'"""),
                "rel": q("""SELECT count(*) FROM pg_class r JOIN pg_namespace n ON n.oid = r.relnamespace
                            WHERE n.nspname NOT IN ('pg_catalog','information_schema','pg_toast') AND n.nspname NOT LIKE 'pg\\_t%'"""),
                "fn": q("""SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                           WHERE n.nspname NOT IN ('pg_catalog','information_schema')"""),
                "ns": sorted(r[0] for r in c.execute("SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg\\_%' AND nspname <> 'information_schema'")),
                "lich_su": q("SELECT to_regclass('master.schema_migrations') IS NOT NULL"),
                "he_thong": q("SELECT to_regclass('master.he_thong') IS NOT NULL")}

    def test_repair04_text_search_config_ngoai_lai_tu_choi_truoc_ghi(self):
        """Repair04 mục3: một TEXT SEARCH CONFIGURATION độc lập (không thuộc extension, mapping không rỗng) ở public — có và không có master rỗng —
        bị từ chối ở admission (đọc, READ ONLY) và ở migrate TRƯỚC mọi DDL/lịch sử/marker/seed; catalog độc lập trước/sau 0 delta."""
        for label, setup, ma in (("khong_master", [], "FOREIGN_DATABASE"), ("master_rong", ["CREATE SCHEMA master"], "MIGRATION_HISTORY")):
            with self.subTest(label=label):
                c = self.ket_noi("kho_test_m0m5_tscfg_")
                for s in setup + ["CREATE TEXT SEARCH CONFIGURATION public.ngoai_ts (COPY = pg_catalog.simple)"]:
                    c.execute(s)
                truoc = self.catalog_doc_lap(c)
                self.assertEqual(truoc["ts_cfg"], 1)
                self.assertGreater(truoc["ts_map"], 0)
                self.assertEqual(c.execute("""SELECT count(*) FROM pg_depend d JOIN pg_ts_config t ON t.oid = d.objid
                                              WHERE d.classid = 'pg_ts_config'::regclass AND d.deptype = 'e'""").fetchone()[0], 0)  # không thuộc extension
                with c.transaction():
                    c.execute("SET TRANSACTION READ ONLY")
                    with self.assertRaises(DataError) as cm:
                        pg._current_state(c)
                self.assertEqual(cm.exception.code, ma)
                with self.assertRaises(DataError) as cm2:
                    pg.migrate(c)
                self.assertEqual(cm2.exception.code, ma)
                self.assertEqual(self.catalog_doc_lap(c), truoc)

    def test_i_s02_db_moi_va_schema_rong_van_duong(self):
        c = self.ket_noi("kho_test_m0m5_is02_ok_")
        self.assertEqual(pg._dem_doi_tuong_nguoi_dung(c.cursor()), 0)  # DB mới từ template0
        c.execute("CREATE SCHEMA trong_khong_doi_tuong")
        self.assertEqual(pg.migrate(c), 14)
        c2 = self.ket_noi("kho_test_m0m5_is02_master_rong_")
        c2.execute("CREATE SCHEMA master")  # master rỗng, chưa lịch sử: vẫn là DB trống đã kiểm
        self.assertEqual(pg.migrate(c2), 14)

    def test_i_s02_extension_da_cai_khong_tinh_la_ngoai_lai(self):
        c = self.ket_noi("kho_test_m0m5_is02_ext_")
        try:
            c.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        except psycopg.Error:
            self.skipTest("pgcrypto không có trên máy chủ test — không tính đạt")
        self.assertGreater(c.execute("SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'public'").fetchone()[0], 0)
        self.assertEqual(pg._dem_doi_tuong_nguoi_dung(c.cursor()), 0)  # hàm thuộc extension (pg_depend 'e') không tính
        self.assertEqual(pg.migrate(c), 14)

    def test_core_owner_backfill_va_quantity_only(self):
        c = self.ket_noi("kho_test_m0m5_core_")
        pg.migrate(c, target=12)
        pn = c.execute("INSERT INTO master.phap_nhan (ma, ten) VALUES ('CORE_M0M5','PN core') RETURNING id").fetchone()[0]
        for loai, khoa in (("PHIEU_KHO", "OLD-PK"), ("HOP_DONG_TEP", "OLD-HD"), ("SAO_KE", "OLD-SK")):
            c.execute("INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, hash) VALUES (%s,%s,%s,'2026-08-01',%s)", (pn, loai, khoa, "0" * 64))
        old_pk = c.execute("SELECT id FROM kho.chung_tu WHERE khoa_nguon = 'OLD-PK'").fetchone()[0]
        c.execute("INSERT INTO kho.chung_tu_dong (chung_tu_id, stt) VALUES (%s, 1)", (old_pk,))
        pg.migrate(c)
        self.assertEqual(dict(c.execute("SELECT khoa_nguon, module_nghiep_vu FROM kho.chung_tu WHERE phap_nhan_id = %s", (pn,)).fetchall()),
                         {"OLD-PK": "M1", "OLD-HD": "CRM", "OLD-SK": "M1"})  # PHIEU_KHO cũ giữ M1, không retag M5
        self.assertEqual(tuple(c.execute("SELECT no_minor, co_minor FROM kho.chung_tu_dong WHERE chung_tu_id = %s", (old_pk,)).fetchone()), (0, 0))
        c.execute("INSERT INTO kho.chung_tu_dong (chung_tu_id, stt) VALUES (%s, 2)", (old_pk,))  # caller cũ: DEFAULT 0 vẫn chạy
        with self.assertRaises(psycopg.Error):
            c.execute("INSERT INTO kho.chung_tu_dong (chung_tu_id, stt, no_minor, co_minor) VALUES (%s, 3, NULL, NULL)", (old_pk,))
        with self.assertRaises(psycopg.Error):
            c.execute("UPDATE kho.chung_tu SET module_nghiep_vu = 'M5' WHERE id = %s", (old_pk,))
        with self.assertRaises(psycopg.Error):  # module do caller khai sai bị từ chối
            c.execute("INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, hash, module_nghiep_vu) VALUES (%s,'SAO_KE','X','2026-08-01',%s,'M5')",
                      (pn, "0" * 64))

    def test_cong_mo_ung_dung_doi_ban_moi_nhat(self):
        c = self.ket_noi("kho_test_m0m5_cong_")
        pg.migrate(c, target=12)
        with self.assertRaises(DataError) as cm:
            pg.kiem_lineage_ung_dung(c)
        self.assertEqual(cm.exception.code, "SCHEMA_CHUA_NANG_CAP")
        pg.migrate(c)
        self.assertEqual(pg.kiem_lineage_ung_dung(c), 14)


if __name__ == "__main__":
    unittest.main()
