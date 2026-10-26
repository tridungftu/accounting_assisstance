"""MTQ-4a0: kiểm tĩnh và PG tùy chọn; không mở server, không xóa CSDL/vai."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import re
import unittest
import uuid

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_mtq_cong import MTQ_CONG_SQL
from tests import test_mtq_sql as nen

ROOT = Path(__file__).resolve().parents[1]
SQL = "\n".join(MTQ_CONG_SQL)
DSN = os.environ.get("KHO_PG_DSN_TEST")
psycopg = nen.psycopg


class MtqCongTinh(unittest.TestCase):
    def test_module_chi_chua_hang_sql(self):
        path = ROOT / "src/kho_tri_thuc/k2/sql_mtq_cong.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        self.assertEqual(len(tree.body), 1)
        assignment = tree.body[0]
        self.assertIsInstance(assignment, ast.Assign)
        self.assertEqual([t.id for t in assignment.targets], ["MTQ_CONG_SQL"])
        self.assertEqual(ast.literal_eval(assignment.value), MTQ_CONG_SQL)
        self.assertTrue(all(isinstance(s, str) and s.strip() for s in MTQ_CONG_SQL))

    def test_definer_search_path_chu_ky_khong_nhan_danh_tinh(self):
        functions = MTQ_CONG_SQL[:2]
        self.assertEqual(len(re.findall(r"CREATE FUNCTION ", SQL)), 2)
        for f in functions:
            self.assertIn("SECURITY DEFINER", f)
            self.assertIn("SET search_path = pg_catalog, master, nhat_ky, pg_temp", f)
            self.assertIn("master.ktt_danh_tinh()", f)
            signature = f.split("RETURNS", 1)[0]
            self.assertNotRegex(signature, r"\bp_(actor\w*|phap_nhan\w*|pn|vai\w*|login\w*|nguoi\w*)\b")
        self.assertIn("p_hanh_dong text, p_doi_tuong jsonb, p_so_tien numeric", functions[0])

    def test_registry_append_theo_dau_khong_ghim_so(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# MTQ-4a0 — CD-012:"
        self.assertEqual(source.count(marker), 1)
        prefix = source.split(marker, 1)[0]
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(prefix, PM.__file__, "exec"), old)
        previous = old["PG_MIGRATIONS"]
        self.assertEqual(PM.PG_MIGRATIONS[:-1], previous)
        self.assertIs(PM.PG_MIGRATIONS[-1], MTQ_CONG_SQL)
        self.assertIs(PM.M00xx_MTQ_CONG, MTQ_CONG_SQL)
        self.assertEqual(sum(m is MTQ_CONG_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_acl_chi_cap_hai_ham_khong_cap_bang(self):
        for sig in ("master.mtq_quyet_dinh_phien(text,jsonb,numeric)",
                    "master.mtq_ghi_tu_choi_phien(uuid,text,jsonb,numeric)"):
            self.assertIn(sig, MTQ_CONG_SQL[2])
            self.assertIn(sig, MTQ_CONG_SQL[3])
        self.assertIn("REVOKE ALL ON FUNCTION", MTQ_CONG_SQL[2])
        self.assertIn("FROM PUBLIC", MTQ_CONG_SQL[2])
        self.assertIn("IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_web')", MTQ_CONG_SQL[3])
        self.assertIn("GRANT EXECUTE ON FUNCTION", MTQ_CONG_SQL[3])
        self.assertIn("TO app_web", MTQ_CONG_SQL[3])
        self.assertNotRegex(SQL, r"GRANT\s+(SELECT|ALL|INSERT|UPDATE|DELETE)")

    def test_cung_loi_khong_goi_quyen_cu_khong_cache_danh_tinh(self):
        f = MTQ_CONG_SQL[0]
        self.assertIn("master.mtq_quyet_dinh(", f)
        self.assertIn("pg_advisory_xact_lock_shared(742601, 1)", f)
        self.assertIn("EXCEPTION WHEN SQLSTATE 'ZMT01'", f)
        self.assertNotIn("STABLE", f)
        self.assertNotIn("IMMUTABLE", f)
        for forbidden in ("ktt_duoc(", "ktt_co_vai(", "mtq_la_admin(", "EXECUTE "):
            self.assertNotIn(forbidden, f)
        self.assertIn("khoa, scope_loai, p_so_tien, scope_id, NULL", f)

    def test_audit_tinh_lai_chi_tu_choi_khong_nuot_loi_ghi(self):
        f = MTQ_CONG_SQL[1]
        self.assertIn("kq := master.mtq_quyet_dinh_phien(", f)
        self.assertIn("kq->'cho_phep' IS DISTINCT FROM 'false'::jsonb", f)
        self.assertIn("kq->>'nguon' IS DISTINCT FROM 'MA_TRAN'", f)
        self.assertIn("INSERT INTO nhat_ky.mtq_tu_choi", f)
        self.assertNotIn("EXCEPTION WHEN", f)
        self.assertNotRegex(f, r"\bp_(ma|ly_do|quyet_dinh|gioi_han)\b")

    def test_utf8_khong_bom_va_migration_lf(self):
        for name in ("src/kho_tri_thuc/k2/sql_mtq_cong.py",
                     "src/kho_tri_thuc/ha_tang/pg_migrations.py", "tests/test_mtq_cong_sql.py"):
            data = (ROOT / name).read_bytes()
            self.assertFalse(data.startswith(b"\xef\xbb\xbf"), name)
            self.assertNotIn("\ufffd", data.decode("utf-8"))
            self.assertNotIn(b"\r\n", data, name)


@unittest.skipUnless(DSN and psycopg is not None, "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class MtqCongPostgres(unittest.TestCase):
    # Tái dùng fixture DEMO M0039, không thừa kế/chạy lại toàn bộ test của nó.
    nguoi = nen.MtqPostgres.nguoi
    actor = nen.MtqPostgres.actor
    ghi = nen.MtqPostgres.ghi
    nhap = nen.MtqPostgres.nhap
    sua_nhap = nen.MtqPostgres.sua_nhap
    san_sang = nen.MtqPostgres.san_sang

    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = "kho_test_mtq_cong_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as c:
            # Vai dùng chung chỉ tạo khi thiếu; không đổi thuộc tính/quyền vai có sẵn.
            c.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_web') THEN CREATE ROLE app_web NOLOGIN; END IF; END $$")
            c.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.test_dsn = make_conninfo(DSN, dbname=cls.db)
        cls.c = psycopg.connect(cls.test_dsn, autocommit=True)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c)

    def setUp(self):
        nen.MtqPostgres.setUp(self)
        self.da = self.c.execute("INSERT INTO master.du_an (phap_nhan_id,ma_junsky,ten) VALUES (%s,%s,'Dự án MTQ DEMO') RETURNING id",
                                 (self.pn, uuid.uuid4().hex)).fetchone()[0]
        self.obj = {"bang": "master.du_an", "id": str(self.da)}

    def cong(self, action="CRM:DU_AN_BAN:XEM", obj=None, money=None):
        return self.c.execute("SELECT master.mtq_quyet_dinh_phien(%s,%s::jsonb,%s)",
                              (action, json.dumps(self.obj if obj is None else obj), money)).fetchone()[0]

    def audit(self, request=None, obj=None, action="CRM:DU_AN_BAN:XEM", money=None):
        return self.c.execute("SELECT master.mtq_ghi_tu_choi_phien(%s,%s,%s::jsonb,%s)",
                              (request or uuid.uuid4(), action,
                               json.dumps(self.obj if obj is None else obj), money)).fetchone()[0]

    def cau_hinh(self, tick=True):
        self.actor(self.admin)
        v = self.nhap()
        for phong in (self.phong, self.phong2):
            for vai in nen.VAI:
                d = self.sua_nhap(v, "DONG", {"phong_id": phong, "vai": vai, "gioi_han_vnd": 100})
                if phong == self.phong and vai == "TRUONG_PHONG" and tick:
                    self.sua_nhap(v, "O", {"dong_id": d["id"], "module": "CRM", "man": "DU_AN_BAN", "hanh_dong": "XEM", "cho_phep": True})
                    self.sua_nhap(v, "O", {"dong_id": d["id"], "module": "CRM", "man": "TIEP_NHAN", "hanh_dong": "DUYET", "cho_phep": True})
        self.sua_nhap(v, "CONG_BO", {})
        g = self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]), "phap_nhan_id": str(self.pn), "phong_id": self.phong, "vai": "TRUONG_PHONG"})
        self.scope = self.ghi("PHAM_VI", {"gan_vai_id": g["id"], "phap_nhan_id": str(self.pn), "loai": "DU_AN", "khoa": str(self.da)})
        self.san_sang()
        self.ghi("KICH_HOAT", {"phap_nhan_id": str(self.pn), "phien_ban_id": v["id"], "bat": True})
        self.actor(self.user)

    def web(self):
        self.c.execute("SET LOCAL ROLE app_web")

    def permission_denied(self, query):
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with self.c.transaction():
                self.c.execute(query)

    def test_app_goi_duoc_va_chua_bat_tra_cu(self):
        self.actor(self.user)
        self.web()
        kq = self.cong()
        self.assertEqual(kq["nguon"], "CU")
        self.assertIsNone(kq["cho_phep"])
        self.assertFalse(kq["can_thiep"])

    def test_danh_tinh_trong_sai_id_login_va_ngung_hoat_dong(self):
        self.c.execute("UPDATE master.nguoi_dung SET trang_thai='KHOA' WHERE id=%s", (self.admin[0],))
        self.web()
        for actor in (("", ""), (str(uuid.uuid4()), self.user[1]),
                      (str(self.admin[0]), self.user[1]), (str(self.admin[0]), self.admin[1]),
                      ("khong-phai-uuid", self.user[1])):
            self.actor(actor)
            kq = self.cong()
            self.assertFalse(kq["cho_phep"])
            self.assertEqual(kq["ma"], "MTQ_DANH_TINH")

    def test_app_khong_doc_bang_khong_goi_loi_goc(self):
        self.actor(self.user)
        self.web()
        for table in nen._BANG:
            self.permission_denied("SELECT * FROM " + table)
        self.permission_denied("SELECT master.mtq_quyet_dinh(NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL)")
        self.permission_denied("INSERT INTO nhat_ky.mtq_tu_choi (request_id,ma,ly_do) VALUES (gen_random_uuid(),'GIA','DEMO')")

    def test_cung_ket_qua_loi_va_doi_guc_khong_lan_cache(self):
        self.cau_hinh()
        core = self.c.execute("SELECT master.mtq_quyet_dinh(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                              (self.pn, self.phong, "CRM:DU_AN_BAN:XEM", "DU_AN_BAN", str(self.da),
                               str(self.da), "DU_AN", None, self.scope["id"], uuid.uuid4())).fetchone()[0]
        self.web()
        self.assertEqual(self.cong(), core)
        for actor, expected in ((self.admin, False), (self.user, True), (self.admin, False), (self.user, True)):
            self.actor(actor)
            self.assertIs(self.cong()["cho_phep"], expected)

    def test_khong_nhan_actor_phap_nhan_vai_hay_quyet_dinh_gia(self):
        self.cau_hinh()
        self.web()
        for key in ("actor_id", "phap_nhan_id", "vai", "cho_phep", "ma", "gioi_han_vnd"):
            kq = self.cong(obj={**self.obj, key: "GIA_DEMO"})
            self.assertFalse(kq["cho_phep"])
            self.assertEqual(kq["ma"], "MTQ_DOI_TUONG")
        self.assertFalse(self.cong(obj={**self.obj, "id": "sai-uuid"})["cho_phep"])
        self.assertFalse(self.cong(obj={"bang": "master.nguoi_dung", "id": str(self.user[0])})["cho_phep"])
        for value in ([], "DEMO", 1):
            self.assertEqual(self.cong(obj=value)["ma"], "MTQ_DOI_TUONG")

    def test_han_muc_cung_loi_va_audit_khong_nhan_so_lieu_quyet_dinh(self):
        self.cau_hinh()
        self.c.execute("RESET ROLE")
        hd = self.c.execute("INSERT INTO master.hop_dong (phap_nhan_id,du_an_id,loai,ma_noi_bo,so_hop_dong) VALUES (%s,%s,'DICH_VU',%s,%s) RETURNING id",
                             (self.pn, self.da, uuid.uuid4().hex, "HD-DEMO-" + uuid.uuid4().hex)).fetchone()[0]
        obj = {"bang": "master.hop_dong", "id": str(hd)}
        self.web()
        for money in (0, 99, 100):
            self.assertTrue(self.cong("CRM:TIEP_NHAN:DUYET", obj, money)["cho_phep"])
        kq = self.cong("CRM:TIEP_NHAN:DUYET", obj, 101)
        self.assertEqual(kq["ma"], "MTQ_VUOT_HAN_MUC")
        self.assertEqual((kq["gioi_han_vnd"], kq["so_tien_vnd"]), (100, 101))
        self.assertIsNotNone(kq["revision"])
        key = self.audit(obj=obj, action="CRM:TIEP_NHAN:DUYET", money=101)
        for money in (None, -1, "NaN", "Infinity", "1.5"):
            self.assertEqual(self.cong("CRM:TIEP_NHAN:DUYET", obj, money)["ma"], "MTQ_THIEU_TIEN")
        self.c.execute("RESET ROLE")
        row = self.c.execute("SELECT ma,hanh_dong,doi_tuong,gioi_han_vnd,so_tien_vnd,revision FROM nhat_ky.mtq_tu_choi WHERE id=%s", (key,)).fetchone()
        self.assertEqual(row, (kq["ma"], "DUYET", str(hd), 100, 101, kq["revision"]))

    def test_khac_phap_nhan_pham_vi_va_phong_mo_ho_bi_chan(self):
        self.cau_hinh()
        self.actor(self.admin)
        da2 = self.c.execute("INSERT INTO master.du_an (phap_nhan_id,ma_junsky,ten) VALUES (%s,%s,'Ngoài phạm vi DEMO') RETURNING id",
                             (self.pn, uuid.uuid4().hex)).fetchone()[0]
        da_khac_pn = self.c.execute("INSERT INTO master.du_an (phap_nhan_id,ma_junsky,ten) VALUES (%s,%s,'Khác pháp nhân DEMO') RETURNING id",
                                   (self.pn2, uuid.uuid4().hex)).fetchone()[0]
        phong_khac_pn = self.ghi("PHONG", {"phap_nhan_id": str(self.pn2), "ma": "KT", "ten": "Phòng khác PN DEMO"})
        v = self.ghi("NHAP", {"phap_nhan_id": str(self.pn2)})
        for vai in nen.VAI:
            self.sua_nhap(v, "DONG", {"phong_id": phong_khac_pn["id"], "vai": vai})
        self.sua_nhap(v, "CONG_BO", {})
        self.ghi("KICH_HOAT", {"phap_nhan_id": str(self.pn2), "phien_ban_id": v["id"], "bat": True})
        self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]), "phap_nhan_id": str(self.pn), "phong_id": self.phong2, "vai": "CFO"})
        self.actor(self.user)
        self.web()
        self.assertEqual(self.cong()["ma"], "MTQ_PHONG_MO_HO")
        self.assertTrue(self.cong(obj={**self.obj, "phong_id": self.phong})["cho_phep"])
        self.assertEqual(self.cong(obj={**self.obj, "id": str(da2), "phong_id": self.phong})["ma"], "MTQ_PHAM_VI")
        self.assertEqual(self.cong(obj={**self.obj, "phong_id": str(uuid.uuid4())})["ma"], "MTQ_GAN_VAI")
        self.assertEqual(self.cong(obj={**self.obj, "id": str(da_khac_pn)})["ma"], "MTQ_GAN_VAI")

    def test_hoi_khong_ghi_audit_logger_ghi_dung_mot_dong(self):
        self.cau_hinh(tick=False)
        self.web()
        kq = self.cong()
        self.assertEqual(kq["ma"], "MTQ_CHUA_TICK")
        self.c.execute("RESET ROLE")
        before = self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0]
        self.assertEqual(before, 0)
        self.web()
        req = uuid.uuid4()
        key = self.audit(req)
        self.c.execute("RESET ROLE")
        row = self.c.execute("SELECT request_id,actor_id,actor_login,ma,doi_tuong,gioi_han_vnd,so_tien_vnd FROM nhat_ky.mtq_tu_choi WHERE id=%s", (key,)).fetchone()
        self.assertEqual(row, (req, self.user[0], self.user[1], kq["ma"], str(self.da), 100, None))
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0], before + 1)

    def test_logger_khong_ghi_cho_phep_cu_va_loi_audit_khong_bi_nuot(self):
        self.actor(self.user)
        self.web()
        with self.assertRaisesRegex(psycopg.Error, "MTQ_KHONG_PHAI_TU_CHOI"):
            with self.c.transaction():
                self.audit()
        self.c.execute("RESET ROLE")
        self.cau_hinh()
        self.web()
        with self.assertRaisesRegex(psycopg.Error, "MTQ_KHONG_PHAI_TU_CHOI"):
            with self.c.transaction():
                self.audit()
        self.c.execute("RESET ROLE")
        self.c.execute("CREATE TRIGGER mtq_cong_test_loi BEFORE INSERT ON nhat_ky.mtq_tu_choi FOR EACH ROW EXECUTE FUNCTION master.mtq_bat_bien()")
        self.web()
        with self.assertRaisesRegex(psycopg.Error, "MTQ_BAT_BIEN"):
            with self.c.transaction():
                self.audit(obj={**self.obj, "actor_id": "GIA_DEMO"})

    def test_audit_giao_dich_rieng_song_qua_rollback(self):
        # Bỏ fixture chưa commit để nhả khóa cấu hình exclusive trước khi dùng
        # kết nối audit khác. Chỉ danh tính DEMO riêng bên dưới được commit.
        self.c.execute("ROLLBACK")
        login = "MO_PHONG_MTQ_CONG_" + uuid.uuid4().hex
        with psycopg.connect(self.test_dsn, autocommit=True) as audit_c:
            actor_id = audit_c.execute("INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro) VALUES ('Audit DEMO',%s,'XEM') RETURNING id", (login,)).fetchone()[0]
            self.c.execute("BEGIN")
            self.c.execute("UPDATE master.nguoi_dung SET ten='Chưa commit DEMO' WHERE id=%s", (actor_id,))
            self.actor((actor_id, login))
            self.web()
            self.assertEqual(self.cong(obj={})["ma"], "MTQ_CAN_RESOLVER_MTQ4")
            self.c.execute("ROLLBACK")
            req = uuid.uuid4()
            with audit_c.transaction():
                audit_c.execute("SET LOCAL ROLE app_web")
                audit_c.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true),set_config('ktt.nguoi_dung_dang_nhap',%s,true)", (str(actor_id), login))
                key = audit_c.execute("SELECT master.mtq_ghi_tu_choi_phien(%s,'CRM:DU_AN_BAN:XEM','{}'::jsonb,NULL)", (req,)).fetchone()[0]
            self.c.execute("BEGIN")
            self.c.execute("UPDATE master.nguoi_dung SET ten='Giao dịch khác DEMO' WHERE id=%s", (actor_id,))
            self.c.execute("ROLLBACK")
            self.assertEqual(audit_c.execute("SELECT request_id,actor_id,actor_login,ma FROM nhat_ky.mtq_tu_choi WHERE id=%s", (key,)).fetchone(),
                             (req, actor_id, login, "MTQ_CAN_RESOLVER_MTQ4"))
            self.assertEqual(audit_c.execute("SELECT ten FROM master.nguoi_dung WHERE id=%s", (actor_id,)).fetchone()[0], "Audit DEMO")


if __name__ == "__main__":
    unittest.main()
