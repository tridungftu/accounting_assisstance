"""MTQ-1: test thuần và PG tùy chọn. Không mở server, không xóa CSDL/vai.

Lead chạy PG ngoài sandbox bằng KHO_PG_DSN_TEST; chỉ tạo kho_test_* DEMO.
Trong test, readiness được thay ở giao dịch riêng rồi rollback, không bật thật.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_ma_tran_tham_quyen import (
    MA_TRAN_THAM_QUYEN_SQL, _BANG, _CATALOG, _HAM,
)

SQL = "\n".join(MA_TRAN_THAM_QUYEN_SQL)
VAI = ("THUC_HIEN_1", "THUC_HIEN_2", "TRUONG_PHONG", "CFO", "NGUOI_XEM")


def ham(ten):
    return next(s for s in MA_TRAN_THAM_QUYEN_SQL if s.startswith("CREATE FUNCTION master." + ten + "("))


class MtqTinh(unittest.TestCase):
    def test_append_khong_doi_registry_cu_khong_ghim_so(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        prefix = source[:source.index("from ..k2.sql_ma_tran_tham_quyen import ")]
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(prefix, PM.__file__, "exec"), old)
        old_migrations = old["PG_MIGRATIONS"]
        self.assertEqual(PM.PG_MIGRATIONS[:len(old_migrations)], old_migrations)
        self.assertIs(PM.PG_MIGRATIONS[len(old_migrations)], MA_TRAN_THAM_QUYEN_SQL)
        self.assertEqual(sum(m is MA_TRAN_THAM_QUYEN_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_tat_ca_bang_co_rls_revoke_chan_truncate(self):
        self.assertEqual(len(_BANG), 11)
        for t in _BANG:
            with self.subTest(bang=t):
                self.assertIn("CREATE TABLE " + t + " (", SQL)
                self.assertIn("ALTER TABLE " + t + " ENABLE ROW LEVEL SECURITY", SQL)
                self.assertIn("BEFORE TRUNCATE ON " + t, SQL)
        self.assertIn("REVOKE ALL ON " + ", ".join(_BANG) + " FROM PUBLIC", SQL)
        self.assertIn("ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai']", SQL)
        self.assertNotIn("GRANT ", SQL)
        self.assertNotIn("SECURITY DEFINER", SQL)

    def test_ham_noi_bo_thu_hoi_public_va_app(self):
        revoke = "REVOKE EXECUTE ON FUNCTION " + ", ".join(_HAM)
        self.assertIn(revoke + " FROM PUBLIC", SQL)
        self.assertIn(revoke + " FROM %I", SQL)
        self.assertEqual(len(_HAM), sum(s.startswith("CREATE FUNCTION ") for s in MA_TRAN_THAM_QUYEN_SQL))

    def test_han_muc_chi_mot_noi_va_fk_cheo_phap_nhan(self):
        self.assertIn("gioi_han_vnd numeric(20,0)", SQL)
        table = next(s for s in MA_TRAN_THAM_QUYEN_SQL if s.startswith("CREATE TABLE master.mtq_o"))
        self.assertNotIn("gioi_han_vnd", table)
        for s in ("UNIQUE (phien_ban_id, phong_id, vai)", "UNIQUE (id, phap_nhan_id)",
                  "FOREIGN KEY (phong_id, phap_nhan_id)", "FOREIGN KEY (phien_ban_id, phap_nhan_id)",
                  "FOREIGN KEY (gan_vai_id, phap_nhan_id)", "FOREIGN KEY (catalog_version, module, man, hanh_dong)"):
            self.assertIn(s, SQL)

    def test_catalog_huu_han_khong_wildcard_m9_hay_seed_vai(self):
        self.assertEqual(len({(m, man) for m, man, _, _ in _CATALOG}), len(_CATALOG))
        self.assertTrue(all(m != "M9" for m, _, _, _ in _CATALOG))
        for screen in ("PDF_DA_DUYET", "BAN_KY", "NGUON_THO", "XEM_TIEN"):
            self.assertTrue(any(man == screen for _, man, _, _ in _CATALOG))
        for action in ("XEM", "LAP", "SUA", "KIEM", "DUYET", "HUY"):
            self.assertIn(action, {a for _, _, actions, _ in _CATALOG for a in actions.split()})
        # Chỉ danh mục cấu trúc được seed trong migration.
        inserts = [s for s in MA_TRAN_THAM_QUYEN_SQL if s.startswith("INSERT INTO ")]
        self.assertTrue(inserts)
        self.assertTrue(all(s.startswith("INSERT INTO master.mtq_danh_muc_hanh_dong ") for s in inserts))

    def test_mac_dinh_tat_va_khoa_bat_truoc_mtq4(self):
        self.assertIn("bat boolean NOT NULL DEFAULT false", SQL)
        self.assertIn("SELECT false", ham("mtq_san_sang"))
        self.assertIn("MTQ_CHUA_NOI_MTQ4", ham("mtq_kiem_ghi"))
        self.assertIn("'nguon', 'CU', 'can_thiep', false, 'cho_phep', NULL", ham("mtq_quyet_dinh"))
        self.assertNotIn("CREATE OR REPLACE FUNCTION master.ktt_", SQL)

    def test_identity_truoc_nhanh_tat_va_khong_admin_bypass(self):
        f = ham("mtq_quyet_dinh")
        self.assertIn("master.ktt_danh_tinh()", f)
        self.assertLess(f.index("IF ai IS NULL"), f.index("ELSIF NOT coalesce(kh.bat, false)"))
        self.assertNotIn("mtq_la_admin", f)
        for s in ("MTQ_CON_TRO_SAI", "MTQ_HANH_DONG", "MTQ_GAN_VAI", "MTQ_PHAM_VI", "MTQ_CHUA_TICK"):
            self.assertIn(s, f)

    def test_duyet_tien_huu_han_khong_am_nguyen_va_vuot(self):
        f = ham("mtq_quyet_dinh")
        for s in ("c.hanh_dong = 'DUYET'", "c.loai_tien <> 'PHI_TIEN'", "p_tien_vnd IS NULL", "p_tien_vnd < 0",
                  "p_tien_vnd >= 'Infinity'::numeric", "p_tien_vnd <> trunc(p_tien_vnd)",
                  "p_tien_vnd > d.gioi_han_vnd", "MTQ_VUOT_HAN_MUC", "MTQ_THIEU_TIEN"):
            self.assertIn(s, f)

    def test_cas_audit_va_khoa_cung_giao_dich(self):
        f = ham("mtq_cau_hinh_ghi")
        for s in ("mtq_la_admin()", "pg_advisory_xact_lock(742601, 1)", "FOR UPDATE", "p_expected_revision", "MTQ_REVISION"):
            self.assertIn(s, f)
        self.assertIn("pg_advisory_xact_lock_shared(742601, 1)", ham("mtq_quyet_dinh"))
        for s in ("truoc, sau, actor_id, actor_login, ly_do", "clock_timestamp()", "doi_tuong_bang", "gan_vai_revision", "pham_vi_revision"):
            self.assertIn(s, SQL)
        self.assertNotIn("EXCEPTION WHEN", ham("mtq_ghi_vet"))

    def test_bat_bien_cong_bo_lich_su_admin_cuoi(self):
        f = ham("mtq_kiem_ghi")
        for s in ("MTQ_ADMIN_CUOI", "OLD.trang_thai = 'DA_CONG_BO'", "MTQ_THIEU_DONG", "MTQ_BAT_BIEN"):
            self.assertIn(s, f)
        for t in ("nhat_ky.mtq_thay_doi", "nhat_ky.mtq_tu_choi"):
            self.assertIn("BEFORE UPDATE OR DELETE ON " + t, SQL)

    def test_bootstrap_tin_cay_khong_tu_chon_cfo(self):
        f = ham("mtq_bootstrap_admin")
        for s in ("session_user", "pg_has_role", "EXISTS (SELECT 1 FROM master.mtq_admin)", "p_nguoi", "HOAT_DONG"):
            self.assertIn(s, f)
        self.assertNotIn("CFO", f)

    def test_utf8_khong_bom(self):
        for name in ("src/kho_tri_thuc/k2/sql_ma_tran_tham_quyen.py", "src/kho_tri_thuc/ha_tang/pg_migrations.py", "tests/test_mtq_sql.py"):
            raw = (ROOT / name).read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), name)
            self.assertNotIn("\ufffd", raw.decode("utf-8"))


try:
    import psycopg
except ImportError:
    psycopg = None

DSN = os.environ.get("KHO_PG_DSN_TEST")


@unittest.skipUnless(DSN and psycopg is not None, "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class MtqPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = "kho_test_mtq_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as c:
            c.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.c = psycopg.connect(make_conninfo(DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c)

    def setUp(self):
        self.c.execute("BEGIN")
        self.addCleanup(self.c.execute, "ROLLBACK")
        self.pn = self.c.execute("INSERT INTO master.phap_nhan (ma, ten) VALUES (%s, 'Pháp nhân MTQ DEMO') RETURNING id", (uuid.uuid4().hex,)).fetchone()[0]
        self.pn2 = self.c.execute("INSERT INTO master.phap_nhan (ma, ten) VALUES (%s, 'Pháp nhân khác DEMO') RETURNING id", (uuid.uuid4().hex,)).fetchone()[0]
        self.admin = self.nguoi("XEM")
        self.user = self.nguoi("CFO")  # Vai cũ CFO không mặc nhiên là Admin.
        self.c.execute("SELECT master.mtq_bootstrap_admin(%s,%s,'Bootstrap DEMO tin cậy')", (self.admin[0], uuid.uuid4()))
        self.actor(self.admin)
        self.phong = self.ghi("PHONG", {"phap_nhan_id": str(self.pn), "ma": "KT", "ten": "Kế toán DEMO"})["id"]
        self.phong2 = self.ghi("PHONG", {"phap_nhan_id": str(self.pn), "ma": "DA", "ten": "Dự án DEMO"})["id"]

    def nguoi(self, vai):
        login = "MO_PHONG_MTQ_" + uuid.uuid4().hex
        k = self.c.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro) VALUES ('Người MTQ DEMO',%s,%s) RETURNING id", (login, vai)).fetchone()[0]
        return (k, login)

    def actor(self, actor):
        self.c.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true),set_config('ktt.nguoi_dung_dang_nhap',%s,true)", (str(actor[0]), actor[1]))

    def ghi(self, lenh, data, rev=0):
        return self.c.execute("SELECT master.mtq_cau_hinh_ghi(%s,%s,%s::jsonb,%s,'Cấu hình DEMO')", (uuid.uuid4(), lenh, json.dumps(data), rev)).fetchone()[0]

    def loi(self, code, fn):
        with self.assertRaises(psycopg.Error) as cm:
            with self.c.transaction():  # savepoint; giữ giao dịch DEMO dùng tiếp.
                fn()
        self.assertIn(code, str(cm.exception))

    def nhap(self):
        return self.ghi("NHAP", {"phap_nhan_id": str(self.pn)})

    def sua_nhap(self, v, lenh, data):
        r = self.ghi(lenh, {"phien_ban_id": v["id"], **data}, v["revision"])
        v.update(r["phien_ban"])
        return r["doi_tuong"]

    def cau_hinh(self, limit=100, tick=True, enable=True, actor=None):
        self.actor(self.admin)
        v = self.nhap()
        for phong in (self.phong, self.phong2):
            for vai in VAI:
                r = self.sua_nhap(v, "DONG", {"phong_id": phong, "vai": vai, "gioi_han_vnd": limit})
                if phong == self.phong and vai == "TRUONG_PHONG":
                    dong = r["id"]
        if tick:
            self.sua_nhap(v, "O", {"dong_id": dong, "module": "CRM", "man": "TIEP_NHAN", "hanh_dong": "DUYET", "cho_phep": True})
        self.sua_nhap(v, "CONG_BO", {})
        g = self.ghi("GAN_VAI", {"nguoi_dung_id": str((actor or self.user)[0]), "phap_nhan_id": str(self.pn), "phong_id": self.phong, "vai": "TRUONG_PHONG"})
        s = self.ghi("PHAM_VI", {"gan_vai_id": g["id"], "phap_nhan_id": str(self.pn), "loai": "PHAP_NHAN", "khoa": str(self.pn)})
        if enable:
            self.san_sang()
            self.ghi("KICH_HOAT", {"phap_nhan_id": str(self.pn), "phien_ban_id": v["id"], "bat": True})
        self.actor(actor or self.user)
        return v, g, s, dong

    def san_sang(self):
        # Chỉ mô phỏng readiness trong CSDL kho_test_*; setUp rollback mọi lần.
        self.c.execute("CREATE OR REPLACE FUNCTION master.mtq_san_sang(p_pn uuid) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path = pg_catalog, master, pg_temp AS $$ SELECT true $$")

    def quyet(self, scope=None, tien=100, pn=None, phong=None, lenh="CRM:TIEP_NHAN:DUYET", loai="TIEP_NHAN", khoa=None, scope_loai="PHAP_NHAN"):
        return self.c.execute("SELECT master.mtq_quyet_dinh(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (pn or self.pn, phong or self.phong, lenh, loai, "HO-SO-DEMO", khoa or str(pn or self.pn), scope_loai, tien, scope, uuid.uuid4())).fetchone()[0]

    def test_admin_sua_nonadmin_va_identity_gia_bi_chan(self):
        self.actor(self.user)
        self.loi("MTQ_CHI_ADMIN", self.nhap)
        self.actor((self.admin[0], self.user[1]))
        self.loi("MTQ_CHI_ADMIN", self.nhap)
        self.assertEqual(self.quyet()["ma"], "MTQ_DANH_TINH")
        self.actor(self.admin)
        self.assertEqual(self.nhap()["trang_thai"], "NHAP")

    def test_migrate_lai_khong_doi_du_lieu_mtq_va_lich_su(self):
        from psycopg import sql
        from kho_tri_thuc.ha_tang import postgres

        # Có cấu hình và cả hai loại nhật ký trước khi chạy lại migrate.
        _, _, scope, _ = self.cau_hinh()
        self.assertEqual(self.quyet(scope["id"], tien=101)["ma"], "MTQ_VUOT_HAN_MUC")

        def chup():
            return {
                table: self.c.execute(sql.SQL(
                    "SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text), '[]'::jsonb) FROM {} AS t"
                ).format(sql.Identifier(*table.split(".")))).fetchone()[0]
                for table in (*_BANG, "master.schema_migrations")
            }

        truoc = chup()
        self.assertTrue(all(truoc.values()))
        self.assertEqual(postgres.migrate(self.c), PM.PG_SCHEMA_VERSION)
        self.assertEqual(chup(), truoc)

    def test_bootstrap_chi_mot_lan_admin_cuoi(self):
        self.loi("MTQ_BOOTSTRAP", lambda: self.c.execute("SELECT master.mtq_bootstrap_admin(%s,%s,'DEMO')", (self.user[0], uuid.uuid4())))
        k = self.c.execute("SELECT id FROM master.mtq_admin").fetchone()[0]
        self.loi("MTQ_ADMIN_CUOI", lambda: self.ghi("THU_HOI_ADMIN", {"id": str(k)}, 1))

    def test_tat_khong_can_thiep_va_readiness_chan_bat(self):
        v, _, s, _ = self.cau_hinh(enable=False)
        self.assertEqual(self.quyet(s["id"])["nguon"], "CU")
        self.assertIsNone(self.quyet(s["id"])["cho_phep"])
        self.actor(self.admin)
        self.loi("MTQ_CHUA_NOI_MTQ4", lambda: self.ghi("KICH_HOAT", {"phap_nhan_id": str(self.pn), "phien_ban_id": v["id"], "bat": True}))

    def test_bat_phai_tick_khong_cfo_bypass(self):
        _, _, s, _ = self.cau_hinh(tick=False)
        self.assertEqual(self.quyet(s["id"])["ma"], "MTQ_CHUA_TICK")

    def test_han_muc_thap_bang_vuot_co_ly_do_va_nhat_ky(self):
        _, _, s, _ = self.cau_hinh()
        for money in (0, 99, 100):
            self.assertTrue(self.quyet(s["id"], tien=money)["cho_phep"])
        r = self.quyet(s["id"], tien=101)
        self.assertEqual(r["ma"], "MTQ_VUOT_HAN_MUC")
        self.assertTrue(r["ly_do"])
        audit = self.c.execute("SELECT ma,gioi_han_vnd,so_tien_vnd,gan_vai_revision,pham_vi_revision FROM nhat_ky.mtq_tu_choi").fetchall()
        self.assertEqual(audit, [("MTQ_VUOT_HAN_MUC", 100, 101, 1, 1)])

    def test_null_khong_gioi_han_nhung_tien_phai_hop_le(self):
        _, _, s, _ = self.cau_hinh(limit=None)
        self.assertTrue(self.quyet(s["id"], tien=10**19)["cho_phep"])
        for money in (None, -1, "NaN", "Infinity", "-Infinity", "1.5"):
            self.assertEqual(self.quyet(s["id"], tien=money)["ma"], "MTQ_THIEU_TIEN")

    def test_zero_chi_duyet_zero(self):
        _, _, s, _ = self.cau_hinh(limit=0)
        self.assertTrue(self.quyet(s["id"], tien=0)["cho_phep"])
        self.assertEqual(self.quyet(s["id"], tien=1)["ma"], "MTQ_VUOT_HAN_MUC")

    def test_duyet_phi_tien_khai_tuong_minh_khong_doi_tien_gia(self):
        old, _, s, _ = self.cau_hinh(limit=0)
        self.actor(self.admin)
        v = self.ghi("NHAP", {"phap_nhan_id": str(self.pn), "phien_ban_id": old["id"]})
        dong = str(self.c.execute("SELECT id FROM master.mtq_dong WHERE phien_ban_id=%s AND phong_id=%s AND vai='TRUONG_PHONG'", (v["id"], self.phong)).fetchone()[0])
        self.sua_nhap(v, "O", {"dong_id": dong, "module": "CRM", "man": "G1_MAU", "hanh_dong": "DUYET", "cho_phep": True})
        self.sua_nhap(v, "CONG_BO", {})
        self.ghi("KICH_HOAT", {"phap_nhan_id": str(self.pn), "phien_ban_id": v["id"], "bat": True}, 1)
        self.actor(self.user)
        self.assertTrue(self.quyet(s["id"], tien=None, lenh="CRM:G1_MAU:DUYET", loai="G1_MAU")["cho_phep"])

    def test_admin_khong_bypass_nghiep_vu(self):
        self.cau_hinh()
        self.actor(self.admin)
        self.assertEqual(self.quyet()["ma"], "MTQ_GAN_VAI")

    def test_phong_khac_khong_tron_tick_han_muc_va_scope(self):
        _, _, s, _ = self.cau_hinh()
        self.assertEqual(self.quyet(s["id"], phong=self.phong2)["ma"], "MTQ_GAN_VAI")
        self.assertEqual(self.quyet(str(uuid.uuid4()))["ma"], "MTQ_PHAM_VI")
        self.assertEqual(self.quyet(s["id"], khoa=str(self.pn2))["ma"], "MTQ_PHAM_VI")

    def test_phap_nhan_khac_da_bat_khong_nhan_vai_cua_pn_dau(self):
        _, _, s, _ = self.cau_hinh()
        self.actor(self.admin)
        phong = self.ghi("PHONG", {"phap_nhan_id": str(self.pn2), "ma": "KT", "ten": "Phòng PN khác DEMO"})["id"]
        v = self.ghi("NHAP", {"phap_nhan_id": str(self.pn2)})
        for vai in VAI:
            self.sua_nhap(v, "DONG", {"phong_id": phong, "vai": vai})
        self.sua_nhap(v, "CONG_BO", {})
        self.ghi("KICH_HOAT", {"phap_nhan_id": str(self.pn2), "phien_ban_id": v["id"], "bat": True})
        self.actor(self.user)
        self.assertEqual(self.quyet(s["id"], pn=self.pn2, phong=phong)["ma"], "MTQ_GAN_VAI")

    def test_fk_khong_lan_phap_nhan_va_scope_du_an(self):
        v = self.nhap()
        phong = self.ghi("PHONG", {"phap_nhan_id": str(self.pn2), "ma": "KT", "ten": "Phòng khác DEMO"})["id"]
        self.loi("foreign key", lambda: self.sua_nhap(v, "DONG", {"phong_id": phong, "vai": "CFO"}))
        g = self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]), "phap_nhan_id": str(self.pn), "phong_id": self.phong, "vai": "CFO"})
        da = self.c.execute("INSERT INTO master.du_an (phap_nhan_id,ma_junsky,ten) VALUES (%s,'MTQ-DA','Dự án khác DEMO') RETURNING id", (self.pn2,)).fetchone()[0]
        self.loi("MTQ_PHAM_VI", lambda: self.ghi("PHAM_VI", {"gan_vai_id": g["id"], "phap_nhan_id": str(self.pn), "loai": "DU_AN", "khoa": str(da)}))

    def test_revision_cu_khong_sua_va_audit_atomically(self):
        v = self.nhap()
        self.sua_nhap(v, "DONG", {"phong_id": self.phong, "vai": "CFO", "gioi_han_vnd": 100})
        count = self.c.execute("SELECT count(*) FROM nhat_ky.mtq_thay_doi").fetchone()[0]
        self.loi("MTQ_REVISION", lambda: self.ghi("DONG", {"phien_ban_id": v["id"], "phong_id": self.phong, "vai": "CFO"}, 1))
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_thay_doi").fetchone()[0], count)

    def test_audit_o_cu_moi_ai_luc_nao(self):
        v = self.nhap()
        d = self.sua_nhap(v, "DONG", {"phong_id": self.phong, "vai": "CFO"})
        data = {"dong_id": d["id"], "module": "CRM", "man": "TIEP_NHAN", "hanh_dong": "DUYET", "cho_phep": False}
        self.sua_nhap(v, "O", data)
        self.sua_nhap(v, "O", {**data, "cho_phep": True})
        row = self.c.execute("SELECT doi_tuong,truoc,sau,actor_id,actor_login,luc FROM nhat_ky.mtq_thay_doi WHERE doi_tuong_bang='master.mtq_o' AND truoc IS NOT NULL").fetchone()
        self.assertEqual(row[0]["hanh_dong"], "DUYET")
        self.assertFalse(row[1]["cho_phep"])
        self.assertTrue(row[2]["cho_phep"])
        self.assertEqual(row[3:5], self.admin)
        self.assertIsNotNone(row[5])

    def test_audit_loi_thi_cau_hinh_va_revision_rollback(self):
        v = self.nhap()
        count = self.c.execute("SELECT count(*) FROM nhat_ky.mtq_thay_doi").fetchone()[0]

        def audit_hong():
            self.c.execute("CREATE TRIGGER mtq_test_audit_loi BEFORE INSERT ON nhat_ky.mtq_thay_doi FOR EACH ROW EXECUTE FUNCTION master.mtq_bat_bien()")
            self.sua_nhap(v, "DONG", {"phong_id": self.phong, "vai": "CFO", "gioi_han_vnd": 10})

        self.loi("MTQ_BAT_BIEN", audit_hong)
        self.assertEqual(self.c.execute("SELECT revision FROM master.mtq_phien_ban WHERE id=%s", (v["id"],)).fetchone()[0], 1)
        self.assertEqual(self.c.execute("SELECT count(*) FROM master.mtq_dong WHERE phien_ban_id=%s", (v["id"],)).fetchone()[0], 0)
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_thay_doi").fetchone()[0], count)

    def test_snapshot_va_audit_bat_bien_truncate_bi_chan(self):
        v, _, _, dong = self.cau_hinh()
        self.actor(self.admin)
        self.loi("MTQ_BAT_BIEN", lambda: self.c.execute("UPDATE master.mtq_dong SET gioi_han_vnd=999 WHERE id=%s", (dong,)))
        self.loi("MTQ_BAT_BIEN", lambda: self.c.execute("UPDATE master.mtq_o SET cho_phep=false WHERE dong_id=%s", (dong,)))
        self.loi("MTQ_BAT_BIEN", lambda: self.c.execute("UPDATE master.mtq_phien_ban SET revision=revision+1 WHERE id=%s", (v["id"],)))
        self.loi("MTQ_BAT_BIEN", lambda: self.c.execute("UPDATE nhat_ky.mtq_thay_doi SET ly_do='Sửa'"))
        self.loi("MTQ_BAT_BIEN", lambda: self.c.execute("DELETE FROM nhat_ky.mtq_thay_doi"))
        self.loi("MTQ_BAT_BIEN", lambda: self.c.execute("TRUNCATE nhat_ky.mtq_tu_choi"))

    def test_thu_hoi_vai_hieu_luc_ngay_khong_doi_snapshot(self):
        _, g, s, _ = self.cau_hinh()
        self.assertTrue(self.quyet(s["id"])["cho_phep"])
        self.actor(self.admin)
        self.ghi("THU_HOI_VAI", {"id": g["id"]}, g["revision"])
        self.actor(self.user)
        self.assertEqual(self.quyet(s["id"])["ma"], "MTQ_GAN_VAI")

    def test_thu_hoi_pham_vi_hieu_luc_ngay_va_nguon_chua_resolve_bi_chan(self):
        _, g, s, _ = self.cau_hinh()
        self.actor(self.admin)
        self.loi("MTQ_CAN_RESOLVER_MTQ4", lambda: self.ghi("PHAM_VI", {
            "gan_vai_id": g["id"], "phap_nhan_id": str(self.pn), "loai": "NGUON", "khoa": "NGUON-DEMO"}))
        self.ghi("THU_HOI_PHAM_VI", {"id": s["id"]}, s["revision"])
        self.actor(self.user)
        self.assertEqual(self.quyet(s["id"])["ma"], "MTQ_PHAM_VI")

    def test_cong_bo_thieu_dong_va_khoi_phuc_bang_ban_moi(self):
        v = self.nhap()
        self.loi("MTQ_THIEU_DONG", lambda: self.sua_nhap(v, "CONG_BO", {}))
        published, _, _, _ = self.cau_hinh()
        self.actor(self.admin)
        clone = self.ghi("NHAP", {"phap_nhan_id": str(self.pn), "phien_ban_id": published["id"]})
        self.assertEqual(clone["duoc_tao_tu"], published["id"])
        self.assertGreater(clone["so_phien_ban"], published["so_phien_ban"])
        self.assertEqual(self.c.execute("SELECT count(*) FROM master.mtq_dong WHERE phien_ban_id=%s", (clone["id"],)).fetchone()[0], 10)

    def test_catalog_khong_co_chan_va_quyen_sql_cua_app(self):
        _, _, s, _ = self.cau_hinh()
        self.assertEqual(self.quyet(s["id"], lenh="M9:MO:DUYET")["ma"], "MTQ_HANH_DONG")
        for role, in self.c.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('app_web','app_ke_toan','app_doc','app_cong_ai')"):
            for table in _BANG:
                self.assertFalse(self.c.execute("SELECT has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE')", (role, table)).fetchone()[0])
            for f in _HAM:
                self.assertFalse(self.c.execute("SELECT has_function_privilege(%s,%s,'EXECUTE')", (role, f)).fetchone()[0])


if __name__ == "__main__":
    unittest.main()
