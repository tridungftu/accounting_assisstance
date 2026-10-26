"""MTQ-4a0: kiểm tĩnh và PG tùy chọn; không mở server, không xóa CSDL/vai."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import unittest
import uuid

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_mtq_cong import MTQ_CONG_B_SQL, MTQ_CONG_SQL
from tests import test_mtq_sql as nen

ROOT = Path(__file__).resolve().parents[1]
SQL = "\n".join(MTQ_CONG_SQL)
DSN = os.environ.get("KHO_PG_DSN_TEST")
psycopg = nen.psycopg


class MtqCongTinh(unittest.TestCase):
    def test_module_chi_chua_hang_sql(self):
        path = ROOT / "src/kho_tri_thuc/k2/sql_mtq_cong.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        # Lát sau chỉ được nối thêm hằng SQL; hai hằng đã phát hành giữ đầu tệp.
        self.assertGreaterEqual(len(tree.body), 2)
        for assignment, name, value in zip(
                tree.body, ("MTQ_CONG_SQL", "MTQ_CONG_B_SQL"),
                (MTQ_CONG_SQL, MTQ_CONG_B_SQL)):
            self.assertEqual([t.id for t in assignment.targets], [name])
            self.assertEqual(ast.literal_eval(assignment.value), value)
        for assignment in tree.body:
            self.assertIsInstance(assignment, ast.Assign)
            self.assertRegex(assignment.targets[0].id, r"^MTQ_CONG_[A-Z_]*SQL$")
            value = ast.literal_eval(assignment.value)
            self.assertTrue(all(isinstance(s, str) and s.strip() for s in value))

    def test_m0041_da_phat_hanh_khong_doi_noi_dung_sql(self):
        # Python chuẩn hóa newline khi nạp hằng: checkout LF/CRLF cùng nội dung.
        self.assertEqual(hashlib.sha256("\x00".join(MTQ_CONG_SQL).encode("utf-8")).hexdigest(),
                         "d4f8f8993a232fb00c647dd3431e756c64e6dc3dd3734e1c7947e0460fafb628")

    def test_noi_dung_hang_sql_khong_phu_thuoc_checkout_lf_crlf(self):
        source = (ROOT / "src/kho_tri_thuc/k2/sql_mtq_cong.py").read_text(encoding="utf-8")
        for newline in ("\n", "\r\n"):
            tree = ast.parse(source.replace("\n", newline))
            self.assertEqual([ast.literal_eval(a.value) for a in tree.body][:2],
                             [MTQ_CONG_SQL, MTQ_CONG_B_SQL])

    def test_definer_search_path_chu_ky_khong_nhan_danh_tinh(self):
        functions = (*MTQ_CONG_SQL[:2], MTQ_CONG_B_SQL[1])
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
        self.assertEqual(PM.PG_MIGRATIONS[:len(previous)], previous)
        self.assertIs(PM.PG_MIGRATIONS[len(previous)], MTQ_CONG_SQL)
        self.assertEqual(sum(m is MTQ_CONG_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_registry_b_chi_append_sau_cac_migration_da_phat_hanh(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# MTQ-4a0b — CD-012:"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, "exec"), old)
        i = next(k for k, m in enumerate(PM.PG_MIGRATIONS) if m is MTQ_CONG_B_SQL)
        self.assertEqual(PM.PG_MIGRATIONS[:i], old["PG_MIGRATIONS"])
        self.assertIs(PM.M0043_MTQ_CONG_B, MTQ_CONG_B_SQL)
        self.assertEqual(sum(m is MTQ_CONG_B_SQL for m in PM.PG_MIGRATIONS), 1)

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
        for f in (MTQ_CONG_SQL[1], MTQ_CONG_B_SQL[1]):
            self.assertIn("kq := master.mtq_quyet_dinh_phien(", f)
            self.assertIn("kq->'cho_phep' IS DISTINCT FROM 'false'::jsonb", f)
            self.assertIn("kq->>'nguon' IS DISTINCT FROM 'MA_TRAN'", f)
            self.assertIn("INSERT INTO nhat_ky.mtq_tu_choi", f)
            self.assertNotIn("EXCEPTION WHEN", f)
            self.assertNotRegex(f, r"\bp_(ma|ly_do|quyet_dinh|gioi_han)\b")

    def test_b_giu_chu_ky_acl_va_khoa_request_truoc_doi_chieu(self):
        self.assertEqual(len(MTQ_CONG_B_SQL), 2)
        self.assertEqual(MTQ_CONG_B_SQL[0],
                         "CREATE INDEX IF NOT EXISTS mtq_tu_choi_request_id_idx\n"
                         "        ON nhat_ky.mtq_tu_choi (request_id)")
        f = MTQ_CONG_B_SQL[1]
        self.assertEqual(f.split("DECLARE", 1)[0],
                         MTQ_CONG_SQL[1].split("DECLARE", 1)[0].replace(
                             "CREATE FUNCTION ", "CREATE OR REPLACE FUNCTION ", 1))
        lock = f.index("pg_advisory_xact_lock(hashtextextended(p_request::text, 0))")
        read = f.index("SELECT * INTO cu FROM nhat_ky.mtq_tu_choi")
        reject = f.index("RAISE EXCEPTION 'MTQ_REQUEST_TRUNG:")
        reuse = f.index("RETURN cu.id;")
        insert = f.index("INSERT INTO nhat_ky.mtq_tu_choi")
        self.assertLess(lock, read)
        self.assertLess(read, reject)
        self.assertLess(reject, reuse)
        self.assertLess(reuse, insert)
        for check in ("cu.actor_id IS DISTINCT FROM ai", "cu.actor_login IS DISTINCT FROM login",
                      "cu.lenh_ky_thuat IS DISTINCT FROM p_hanh_dong",
                      "cu.doi_tuong IS DISTINCT FROM (p_doi_tuong->>'id')"):
            self.assertIn(check, f[read:reject])
        self.assertIn("IF FOUND THEN", f[read:reject])
        self.assertEqual(f[f.index("kq :="):],
                         MTQ_CONG_SQL[1][MTQ_CONG_SQL[1].index("kq :="):])
        self.assertNotRegex("\n".join(MTQ_CONG_B_SQL), r"\b(GRANT|REVOKE|DROP)\b")

    def test_utf8_khong_bom_va_migration_lf(self):
        data = Path(PM.__file__).read_bytes()
        self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn("\ufffd", data.decode("utf-8"))
        self.assertNotIn(b"\r", data)


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

    def test_vai_khac_khong_co_execute_hai_ham_cong(self):
        roles = self.c.execute("SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)",
                               (["app_ke_toan", "app_doc", "app_cong_ai"],)).fetchall()
        # PUBLIC là grantee 0 trong ACL, luôn kiểm kể cả khi không có vai app khác.
        for signature in ("master.mtq_quyet_dinh_phien(text,jsonb,numeric)",
                          "master.mtq_ghi_tu_choi_phien(uuid,text,jsonb,numeric)"):
            with self.subTest(vai="PUBLIC", ham=signature):
                self.assertFalse(self.c.execute(
                    "SELECT EXISTS (SELECT 1 FROM pg_proc p, "
                    "LATERAL aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a "
                    "WHERE p.oid = %s::regprocedure AND a.grantee = 0 "
                    "AND a.privilege_type = 'EXECUTE')", (signature,)).fetchone()[0])
        for (role,) in roles:
            for signature in ("master.mtq_quyet_dinh_phien(text,jsonb,numeric)",
                              "master.mtq_ghi_tu_choi_phien(uuid,text,jsonb,numeric)"):
                with self.subTest(vai=role, ham=signature):
                    self.assertFalse(self.c.execute("SELECT has_function_privilege(%s,%s,'EXECUTE')",
                                                    (role, signature)).fetchone()[0])

    def test_phap_nhan_chua_bat_hd_m4_ban_soan_va_hanh_dong_chua_ho_tro_tra_cu(self):
        objects = []
        for pn in (self.pn, self.pn2):
            da = self.c.execute("INSERT INTO master.du_an (phap_nhan_id,ma_junsky,ten) VALUES (%s,%s,'Resolver DEMO') RETURNING id",
                                (pn, uuid.uuid4().hex)).fetchone()[0]
            for module, giao_ket, loai, trang_thai in (("M4", None, "XAY_DUNG", "SOAN_THAO"),
                                                       (None, "SOAN_THAO", "DICH_VU", "SOAN_THAO")):
                hd = self.c.execute("INSERT INTO master.hop_dong (phap_nhan_id,du_an_id,loai,ma_noi_bo,so_hop_dong,module_chu,crm_giao_ket,trang_thai) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                                     (pn, da, loai, uuid.uuid4().hex, "HD-DEMO-" + uuid.uuid4().hex,
                                      module, giao_ket, trang_thai)).fetchone()[0]
                objects.append((pn, {"bang": "master.hop_dong", "id": str(hd)}, "CRM:TIEP_NHAN:XEM"))
            objects.append((pn, {"bang": "master.du_an", "id": str(da)}, "CRM:G3_G4_SOAN_KY:XEM"))
        self.actor(self.user)
        self.web()
        for pn, obj, action in objects:
            with self.subTest(phap_nhan=pn, obj=obj, bat=False):
                kq = self.cong(action, obj)
                self.assertEqual(kq["nguon"], "CU")
                self.assertIsNone(kq["cho_phep"])
                self.assertFalse(kq["can_thiep"])
        self.c.execute("RESET ROLE")
        self.cau_hinh()
        self.web()
        for pn, obj, action in objects:
            with self.subTest(phap_nhan=pn, obj=obj, bat=pn == self.pn):
                kq = self.cong(action, obj)
                if pn == self.pn:
                    self.assertEqual(kq["ma"], "MTQ_CAN_RESOLVER_MTQ4")
                    self.assertFalse(kq["cho_phep"])
                else:
                    self.assertEqual(kq["nguon"], "CU")

    def test_bang_chua_co_resolver_chi_chan_khi_co_phap_nhan_bat(self):
        objects = ({"bang": "master.nguoi_dung", "id": str(self.user[0])},
                   {"bang": "master.du_an", "id": str(uuid.uuid4())}, {})
        self.actor(self.user)
        self.web()
        for obj in objects:
            self.assertEqual(self.cong(obj=obj)["nguon"], "CU")
        self.c.execute("RESET ROLE")
        self.cau_hinh()
        self.web()
        for obj in objects:
            self.assertEqual(self.cong(obj=obj)["ma"], "MTQ_CAN_RESOLVER_MTQ4")

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
        before = self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0]
        self.web()
        kq = self.cong()
        self.assertEqual(kq["ma"], "MTQ_CHUA_TICK")
        self.c.execute("RESET ROLE")
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0], before)
        self.web()
        req = uuid.uuid4()
        key = self.audit(req)
        self.c.execute("RESET ROLE")
        row = self.c.execute("SELECT request_id,actor_id,actor_login,ma,doi_tuong,gioi_han_vnd,so_tien_vnd FROM nhat_ky.mtq_tu_choi WHERE id=%s", (key,)).fetchone()
        self.assertEqual(row, (req, self.user[0], self.user[1], kq["ma"], str(self.da), 100, None))
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0], before + 1)

    def test_logger_trung_request_tra_cung_id_khong_them_dong(self):
        self.cau_hinh(tick=False)
        before = self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0]
        self.web()
        req = uuid.uuid4()
        key = self.audit(req)
        self.c.execute("RESET ROLE")
        after_first = self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0]
        self.assertEqual(after_first, before + 1)
        self.web()
        self.assertEqual(self.audit(req), key)
        self.c.execute("RESET ROLE")
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0], after_first)
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi WHERE request_id=%s", (req,)).fetchone()[0], 1)

    def test_logger_trung_request_khac_nguoi_hanh_dong_doi_tuong_bao_loi(self):
        self.cau_hinh(tick=False)
        before = self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0]
        self.web()
        req = uuid.uuid4()
        key = self.audit(req)
        for actor, action, obj in (
                (self.admin, "CRM:DU_AN_BAN:XEM", self.obj),
                (self.user, "CRM:TIEP_NHAN:XEM", self.obj),
                (self.user, "CRM:DU_AN_BAN:XEM", {**self.obj, "id": str(uuid.uuid4())}),
                (self.user, "CRM:DU_AN_BAN:XEM", {**self.obj, "id": None})):
            with self.subTest(actor=actor[1], action=action, obj=obj):
                self.actor(actor)
                with self.assertRaisesRegex(psycopg.Error, "MTQ_REQUEST_TRUNG"):
                    with self.c.transaction():
                        self.audit(req, obj=obj, action=action)
        self.actor(self.user)
        self.assertEqual(self.audit(req), key)
        self.c.execute("RESET ROLE")
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0], before + 1)
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi WHERE request_id=%s",
                                       (req,)).fetchone()[0], 1)

    def test_logger_hanh_dong_la_bi_tu_choi_khong_ghi(self):
        self.cau_hinh(tick=False)
        before = self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0]
        self.web()
        for action in ("CRM:DU_AN_BAN:LA", "", None):
            with self.subTest(hanh_dong=action):
                with self.assertRaisesRegex(psycopg.Error, "MTQ_HANH_DONG"):
                    with self.c.transaction():
                        self.audit(action=action)
        self.c.execute("RESET ROLE")
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0], before)

    def test_logger_khong_danh_tinh_khong_ghi(self):
        self.cau_hinh(tick=False)
        before = self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0]
        self.web()
        for actor in (("", ""), (str(uuid.uuid4()), self.user[1]),
                      (str(self.user[0]), self.admin[1])):
            self.actor(actor)
            with self.assertRaisesRegex(psycopg.Error, "MTQ_DANH_TINH"):
                with self.c.transaction():
                    self.audit()
        self.c.execute("RESET ROLE")
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0], before)

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
            self.assertEqual(self.cong(obj={"actor_id": "GIA_DEMO"})["ma"], "MTQ_DOI_TUONG")
            self.c.execute("ROLLBACK")
            req = uuid.uuid4()
            with audit_c.transaction():
                audit_c.execute("SET LOCAL ROLE app_web")
                audit_c.execute("SELECT set_config('ktt.nguoi_dung_id',%s,true),set_config('ktt.nguoi_dung_dang_nhap',%s,true)", (str(actor_id), login))
                key = audit_c.execute("SELECT master.mtq_ghi_tu_choi_phien(%s,'CRM:DU_AN_BAN:XEM',%s::jsonb,NULL)",
                                       (req, json.dumps({"actor_id": "GIA_DEMO"}))).fetchone()[0]
            self.c.execute("BEGIN")
            self.c.execute("UPDATE master.nguoi_dung SET ten='Giao dịch khác DEMO' WHERE id=%s", (actor_id,))
            self.c.execute("ROLLBACK")
            self.assertEqual(audit_c.execute("SELECT request_id,actor_id,actor_login,ma FROM nhat_ky.mtq_tu_choi WHERE id=%s", (key,)).fetchone(),
                             (req, actor_id, login, "MTQ_DOI_TUONG"))
            self.assertEqual(audit_c.execute("SELECT ten FROM master.nguoi_dung WHERE id=%s", (actor_id,)).fetchone()[0], "Audit DEMO")


if __name__ == "__main__":
    unittest.main()
