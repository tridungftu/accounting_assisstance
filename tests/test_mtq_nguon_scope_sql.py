"""MTQ-4i-a: validator NGUON; PG chỉ tạo kho_test_* từ DSN quản trị.

Không mở server, không dùng DSN DEMO, không tắt trigger hoặc xóa CSDL/vai.
Lead chạy PG bằng KHO_PG_DSN_TEST. Caller kiểm đủ mọi PN ở lát 4i-c.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_ma_tran_tham_quyen import MA_TRAN_THAM_QUYEN_SQL
from kho_tri_thuc.k2.sql_mtq_lien_module import (
    MTQ_LMOD_A_SQL, MTQ_LMOD_B_SQL, _M0049_PROFILE_CU, _M0049_PROFILE_MOI,
    _NGUON_CU, _NGUON_MOI,
)
from tests import test_mtq_sql as nen

SQL = MTQ_LMOD_A_SQL[0]
DSN = os.environ.get("KHO_PG_DSN_TEST")
psycopg = nen.psycopg


class MtqNguonTinh(unittest.TestCase):
    def test_registry_append_khong_ghim_migration_cuoi(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# MTQ-4i-a — CD-012:"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, "exec"), old)
        previous = old["PG_MIGRATIONS"]
        self.assertEqual(PM.PG_MIGRATIONS[:len(previous)], previous)
        self.assertIs(PM.PG_MIGRATIONS[len(previous)], MTQ_LMOD_A_SQL)
        self.assertEqual(sum(m is MTQ_LMOD_A_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_chi_thay_nhanh_nguon_giu_toan_bo_guard_va_acl(self):
        old = next(s for s in MA_TRAN_THAM_QUYEN_SQL
                   if s.startswith("CREATE FUNCTION master.mtq_kiem_ghi("))
        self.assertEqual(len(MTQ_LMOD_A_SQL), 1)
        self.assertEqual(SQL.count(_NGUON_MOI), 1)
        self.assertEqual(SQL.replace(_NGUON_MOI, _NGUON_CU, 1).replace(
            "CREATE OR REPLACE FUNCTION ", "CREATE FUNCTION ", 1), old)
        self.assertNotIn("SECURITY DEFINER", SQL)
        self.assertNotIn("GRANT ", SQL)
        self.assertNotIn("REVOKE ", SQL)
        self.assertNotIn("EXECUTE ", SQL)

    def test_utf8_khong_bom_va_migrations_lf(self):
        for path in (Path(PM.__file__), Path(__file__),
                     ROOT / "src/kho_tri_thuc/k2/sql_mtq_lien_module.py"):
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), str(path))
            self.assertNotIn("\ufffd", raw.decode("utf-8"))
        self.assertNotIn(b"\r", Path(PM.__file__).read_bytes())

    def test_helper_registry_sau_cong_h_khong_doi_migration_cu(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# MTQ-4i-b1 — CD-012: helper NGUON"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, "exec"), old)
        previous = old["PG_MIGRATIONS"]
        self.assertEqual(PM.PG_MIGRATIONS[:len(previous)], previous)
        self.assertIs(previous[-1], PM.M0066_MTQ_CONG_H)
        self.assertIs(PM.PG_MIGRATIONS[len(previous)], MTQ_LMOD_B_SQL)
        self.assertIs(PM.M0067_MTQ_LMOD_B, MTQ_LMOD_B_SQL)
        self.assertEqual(sum(m is MTQ_LMOD_B_SQL for m in PM.PG_MIGRATIONS), 1)

    def test_validator_chung_chi_thay_truy_van_profile_m0049(self):
        new = MTQ_LMOD_B_SQL[-1]
        self.assertEqual(new.count(_M0049_PROFILE_MOI), 1)
        self.assertEqual(new.replace(_M0049_PROFILE_MOI, _M0049_PROFILE_CU, 1), SQL)
        self.assertIn("ORDER BY p.id FOR SHARE OF p, i", new)
        self.assertNotIn("SECURITY DEFINER", new)
        self.assertNotIn("GRANT ", new)
        for statement in (MTQ_LMOD_B_SQL[0], new):
            self.assertEqual(statement.count("AS $$"), 1)
            self.assertEqual(statement.count("$$"), 2)
            self.assertTrue(statement.endswith("END $$"))

    def test_helper_stable_definer_search_path_va_khong_cap_app_web(self):
        helper = MTQ_LMOD_B_SQL[0]
        self.assertIn("LANGUAGE plpgsql STABLE SECURITY DEFINER", helper)
        self.assertIn("SET search_path = pg_catalog, master, pg_temp AS $$", helper)
        self.assertIn("FROM PUBLIC", MTQ_LMOD_B_SQL[1])
        self.assertIn("FROM app_web", MTQ_LMOD_B_SQL[2])
        self.assertNotIn("GRANT ", "\n".join(MTQ_LMOD_B_SQL))
        self.assertNotIn("FOR SHARE", helper)
        self.assertNotIn("anh_xa_nguon", helper)


@unittest.skipUnless(DSN and psycopg is not None,
                     "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class MtqNguonPostgres(unittest.TestCase):
    nguoi = nen.MtqPostgres.nguoi
    actor = nen.MtqPostgres.actor
    ghi = nen.MtqPostgres.ghi
    loi = nen.MtqPostgres.loi

    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = "kho_test_mtq_nguon_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as c:
            c.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(
                sql.Identifier(cls.db)))
        cls.c = psycopg.connect(make_conninfo(DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        before = next(i for i, m in enumerate(PM.PG_MIGRATIONS) if m is MTQ_LMOD_A_SQL)
        postgres.migrate(cls.c, target=before)
        cls.acl_before = cls.function_acl()
        postgres.migrate(cls.c)

    @classmethod
    def function_acl(cls):
        return cls.c.execute("""SELECT oid, proowner, proacl, prosecdef, proconfig
            FROM pg_proc WHERE oid = 'master.mtq_kiem_ghi()'::regprocedure""").fetchone()

    def setUp(self):
        self.c.execute("BEGIN")
        self.addCleanup(self.c.execute, "ROLLBACK")
        self.pn = self.c.execute("""INSERT INTO master.phap_nhan (ma,ten)
            VALUES (%s,'PN nguồn tổng hợp') RETURNING id""", (uuid.uuid4().hex,)).fetchone()[0]
        self.pn2 = self.c.execute("""INSERT INTO master.phap_nhan (ma,ten)
            VALUES (%s,'PN khác tổng hợp') RETURNING id""", (uuid.uuid4().hex,)).fetchone()[0]
        self.admin = self.nguoi("XEM")
        self.user = self.nguoi("CFO")
        self.c.execute("SELECT master.mtq_bootstrap_admin(%s,%s,'Bootstrap test nguồn')",
                       (self.admin[0], uuid.uuid4()))
        self.actor(self.admin)
        self.phong = self.ghi("PHONG", {"phap_nhan_id": str(self.pn), "ma": "KT", "ten": "KT tổng hợp"})["id"]
        self.gan = self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]),
            "phap_nhan_id": str(self.pn), "phong_id": self.phong, "vai": "NGUOI_XEM"})["id"]
        self.inst = "TEST_NGUON_" + uuid.uuid4().hex
        self.c.execute("INSERT INTO master.nguon_instance (source_instance_id) VALUES (%s)", (self.inst,))
        self.profile = self.them_profile("PROFILE_TEST")

    def them_profile(self, ref):
        # Registry chỉ có FK/append-only, không có payload trigger; dữ liệu giả.
        return self.c.execute("""INSERT INTO master.nguon_profile
            (source_instance_id,profile_ref,profile_sha256,payload)
            VALUES (%s,%s,%s,'{}'::jsonb) RETURNING id,profile_ref,profile_sha256""",
            (self.inst, ref, "a" * 64)).fetchone()

    def mapping(self, kind="COMPANY", key="CTY A", pn=None, profile=None, future=False):
        pr = profile or self.profile
        # Đúng trigger mapping hiện hành: chủ bảng, ROOT_SEED_DEMO, revision 1,
        # DA_DUYET, valid_to NULL; không dùng INVOICE_LINE làm seed.
        return self.c.execute("""INSERT INTO master.anh_xa_nguon
            (reference_id,revision,source_instance_id,profile_ref,profile_sha256,
             subject_kind,subject_key,phap_nhan_id,valid_from,nguon_quyet_dinh,duyet_boi)
            VALUES (%s,1,%s,%s,%s,%s,%s,%s,
                now() + CASE WHEN %s THEN interval '1 day' ELSE interval '-1 day' END,
                'ROOT_SEED_DEMO','ROOT_SEED_DEMO') RETURNING id""",
            ("TEST_MAP_" + uuid.uuid4().hex, self.inst, pr[1], pr[2], kind, key,
             pn or self.pn, future)).fetchone()[0]

    def cap(self, key=None, pn=None, gan=None, loai="NGUON"):
        return self.ghi("PHAM_VI", {"gan_vai_id": gan or self.gan,
            "phap_nhan_id": str(pn or self.pn), "loai": loai,
            "khoa": key if key is not None else "INVOICE_SET|" + self.inst + "|CTY A"})

    def ung_vien_m0049(self, loai, source, subject):
        # Oracle lấy nguyên truy vấn M0049, gồm cả FOR SHARE và upper tên
        # registry; chỉ thay biến PL/pgSQL bằng tham số đã chuẩn hóa như M0049.
        parts = [self.c.execute("""SELECT upper(btrim(regexp_replace(
            %s::text, '[[:space:]]+', ' ', 'g')))""", (part,)).fetchone()[0]
                 for part in (loai, source, subject)]
        old = _M0049_PROFILE_CU.replace("SELECT p.*", "SELECT p.id").replace("parts[2]", "%s")
        expected = self.c.execute(old, (parts[1], parts[1])).fetchall()
        actual = self.c.execute("SELECT profile_id,nguon_khoa FROM "
                                "master.mtq_nguon_ung_vien(%s,%s,%s) ORDER BY profile_id",
                                (loai, source, subject)).fetchall()
        self.assertEqual(actual, [(row[0], "|".join(parts)) for row in expected])
        return [row[0] for row in actual]

    def oracle_validator(self, key, *, pn=None, loai="NGUON", revoke=False):
        # Hai thân chạy cùng fixture, ID/request/thời điểm cấp cố định; mỗi
        # lần rollback savepoint nên không làm mất fixture hay đổi trigger.
        # Audit bỏ đúng ID/lúc ghi ngẫu nhiên; nội dung NEW so nguyên JSON.
        row_id, request = uuid.uuid4(), uuid.uuid4()
        results = []
        for validator in (SQL, MTQ_LMOD_B_SQL[-1]):
            try:
                with self.c.transaction(force_rollback=True):
                    self.c.execute(validator)
                    self.c.execute("SELECT set_config('ktt.mtq_request',%s,true),"
                                   "set_config('ktt.mtq_ly_do','Oracle M0049',true),"
                                   "set_config('ktt.mtq_lenh','PHAM_VI',true)", (str(request),))
                    row = self.c.execute("""INSERT INTO master.mtq_pham_vi
                        (id,gan_vai_id,phap_nhan_id,loai,khoa,cap_boi,cap_luc,ly_do)
                        VALUES (%s,%s,%s,%s,%s,%s,'2000-01-01 UTC','Oracle M0049')
                        RETURNING to_jsonb(mtq_pham_vi.*)""",
                        (row_id, self.gan, pn or self.pn, loai, key, self.admin[0])).fetchone()[0]
                    if revoke:
                        row = self.c.execute("""UPDATE master.mtq_pham_vi
                            SET thu_hoi_luc='2000-01-02 UTC',thu_hoi_boi=%s,revision=revision+1
                            WHERE id=%s RETURNING to_jsonb(mtq_pham_vi.*)""",
                            (self.admin[0], row_id)).fetchone()[0]
                    audit = self.c.execute("""SELECT to_jsonb(t)-'id'-'luc'
                        FROM nhat_ky.mtq_thay_doi t WHERE request_id=%s ORDER BY revision""",
                        (request,)).fetchall()
                    results.append(("OK", row, audit))
            except psycopg.Error as exc:
                results.append(("ERROR", exc.sqlstate, exc.diag.message_primary))
        self.assertEqual(results[0], results[1])
        return results[1]

    def test_oracle_validator_m0049_nguyen_ket_qua_va_loi(self):
        key = "INVOICE_SET|" + self.inst + "|CTY A"
        self.assertEqual(self.oracle_validator(key)[0], "ERROR")
        self.mapping()
        self.mapping("WAREHOUSE", "KHO 01")
        for source in (self.inst, str(self.profile[0])):
            for kind, subject in (("INVOICE_SET", "CTY A"), ("KHO10_PHIEU", "KHO 01")):
                raw = " \t" + kind.lower() + " | " + source.lower() + " | " + subject.lower().replace(" ", "  ") + "\n"
                with self.subTest(key=raw):
                    self.assertEqual(self.ung_vien_m0049(kind, source, subject), [self.profile[0]])
                    self.assertEqual(self.oracle_validator(raw, revoke=True)[0], "OK")
        for raw in ("", "INVOICE_SET|x", "INVOICE_SET|x|y|z", "INVOICE_SET| |CTY A",
                    "INVOICE_SET|x| \t", "L11_EVIDENCE_SET|x|y", "KHAC|x|y",
                    "INVOICE_SET|KHONG_CO|CTY A", "INVOICE_SET|" + self.inst + "|CHUA MAP"):
            with self.subTest(key=raw):
                self.assertEqual(self.oracle_validator(raw)[0], "ERROR")
        self.assertEqual(self.oracle_validator(str(self.pn), loai="PHAP_NHAN")[0], "OK")
        self.assertEqual(self.oracle_validator(key, pn=self.pn2)[0], "ERROR")

    def test_oracle_validator_m0049_nhieu_profile_trung_uuid_va_instance_dung(self):
        self.mapping()
        key = "INVOICE_SET|" + str(self.profile[0]) + "|CTY A"
        second = self.them_profile("PROFILE_THU_HAI")
        self.assertEqual(set(self.ung_vien_m0049("INVOICE_SET", self.inst, "CTY A")),
                         {self.profile[0], second[0]})
        self.assertEqual(self.oracle_validator("INVOICE_SET|" + self.inst + "|CTY A")[0], "ERROR")
        self.assertEqual(self.oracle_validator(key)[0], "OK")
        old_inst = self.inst
        self.inst = str(self.profile[0])
        self.c.execute("INSERT INTO master.nguon_instance(source_instance_id) VALUES (%s)", (self.inst,))
        collision = self.them_profile("PROFILE_TRUNG_UUID")
        self.mapping(profile=collision)
        self.assertEqual(set(self.ung_vien_m0049("INVOICE_SET", self.inst, "CTY A")),
                         {self.profile[0], collision[0]})
        self.assertEqual(self.oracle_validator(key)[0], "ERROR")
        self.c.execute("UPDATE master.nguon_instance SET trang_thai='DUNG' WHERE source_instance_id=%s",
                       (self.inst,))
        self.assertEqual(self.oracle_validator(key)[0], "OK")
        self.c.execute("UPDATE master.nguon_instance SET trang_thai='DUNG' WHERE source_instance_id=%s",
                       (old_inst,))
        self.assertEqual(self.ung_vien_m0049("INVOICE_SET", str(self.profile[0]), "CTY A"), [])
        self.assertEqual(self.oracle_validator(key)[0], "ERROR")

    def test_oracle_validator_m0049_mapping_tuong_lai_trung_va_khac_pn(self):
        key = "INVOICE_SET|" + self.inst + "|CTY A"
        for options in ({"future": True}, {"pn": self.pn2}, {}):
            with self.subTest(options=options), self.c.transaction(force_rollback=True):
                self.mapping(**options)
                self.assertEqual(self.oracle_validator(key)[0], "OK" if not options else "ERROR")
                self.mapping(key="cty   a")
                self.assertEqual(self.oracle_validator(key)[0], "ERROR" if not options or "pn" in options else "OK")

    def test_helper_ung_vien_chuan_hoa_va_ten_registry_khac_hoa_thuong(self):
        for source in (self.inst.lower(), " \t" + self.inst.lower() + "\n", str(self.profile[0]), "KHONG_CO"):
            self.ung_vien_m0049(" invoice_set ", source, " cty\t  a ")
        # Registry phân biệt hoa/thường ở PK, nhưng M0049 xét upper cả hai:
        # hai tên hợp lệ khác hoa/thường vẫn phải trả đủ hai ứng viên.
        self.inst = self.inst.lower()
        self.c.execute("INSERT INTO master.nguon_instance(source_instance_id) VALUES (%s)", (self.inst,))
        pr = self.them_profile("PROFILE_KHAC_HOA_THUONG")
        self.assertEqual(set(self.ung_vien_m0049("INVOICE_SET", self.inst, "CTY A")),
                         {self.profile[0], pr[0]})
        self.assertEqual(self.ung_vien_m0049("INVOICE_SET", str(pr[0]), "CTY A"), [pr[0]])

    def test_helper_read_only_va_khong_cap_app_web_public(self):
        signature = "master.mtq_nguon_ung_vien(text,text,text)"
        self.assertEqual(self.c.execute("SELECT provolatile,prosecdef,proconfig FROM pg_proc "
                                       "WHERE oid=%s::regprocedure", (signature,)).fetchone(),
                         ("s", True, ["search_path=pg_catalog, master, pg_temp"]))
        self.assertFalse(self.c.execute("SELECT has_function_privilege('app_web',%s,'EXECUTE')",
                                        (signature,)).fetchone()[0])
        self.assertFalse(self.c.execute("SELECT EXISTS (SELECT 1 FROM pg_proc p, "
            "LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a "
            "WHERE p.oid=%s::regprocedure AND a.grantee=0 AND a.privilege_type='EXECUTE')",
            (signature,)).fetchone()[0])
        self.c.execute("ROLLBACK")
        self.c.execute("BEGIN READ ONLY")
        self.assertEqual(self.c.execute("SELECT * FROM master.mtq_nguon_ung_vien(%s,%s,%s)",
                                        ("INVOICE_SET", "KHONG_CO", "CTY A")).fetchall(), [])
        self.c.execute("SET LOCAL ROLE app_web")
        with self.assertRaises(psycopg.errors.InsufficientPrivilege), self.c.transaction():
            self.c.execute("SELECT * FROM master.mtq_nguon_ung_vien(%s,%s,%s)",
                           ("INVOICE_SET", "KHONG_CO", "CTY A"))

    def dong_mapping(self, mapping_id, expired=False):
        # Đi qua guard CFO V4 + module + SOURCE_MAP thật; fixture chưa có child
        # L11 nên closure rỗng, không cần/tắt bất kỳ trigger nào.
        self.c.execute("""INSERT INTO master.phan_quyen
            (nguoi_dung_id,phap_nhan_id,module,duyet_loai_viec)
            VALUES (%s,%s,ARRAY['M2','M5'],ARRAY['V4'])""", (self.user[0], self.pn))
        self.c.execute("""INSERT INTO master.nang_luc_nguon
            (nguoi_dung_id,source_instance_id,profile_ref,profile_sha256,hanh_dong,target_phap_nhan_id)
            VALUES (%s,%s,%s,%s,'SOURCE_MAP',%s)""",
            (self.user[0], self.inst, self.profile[1], self.profile[2], self.pn))
        self.actor(self.user)
        self.c.execute("""UPDATE master.anh_xa_nguon SET state='DONG',
            valid_to = now() + CASE WHEN %s THEN interval '-1 hour' ELSE interval '1 hour' END
            WHERE id=%s""", (expired, mapping_id))
        self.actor(self.admin)

    def test_nang_cap_giu_oid_owner_acl_va_invoker(self):
        self.assertEqual(self.function_acl(), self.acl_before)
        for role in ("app_web", "app_ke_toan", "app_doc", "app_cong_ai"):
            exists = self.c.execute("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=%s)", (role,)).fetchone()[0]
            if exists:
                self.assertFalse(self.c.execute("SELECT has_function_privilege(%s,'master.mtq_kiem_ghi()','EXECUTE')",
                                                (role,)).fetchone()[0])

    def test_cap_invoice_va_kho_chuan_hoa_va_audit(self):
        self.mapping()
        self.mapping("WAREHOUSE", "KHO 01")
        for loai, subject in (("INVOICE_SET", "CTY A"), ("KHO10_PHIEU", "KHO 01")):
            with self.subTest(loai=loai):
                raw = " \t" + loai.lower() + " | " + self.inst.lower() + " | " + subject.lower().replace(" ", "  ") + "\n"
                row = self.cap(raw)
                self.assertEqual(row["khoa"], loai + "|" + self.inst.upper() + "|" + subject)
                audit = self.c.execute("""SELECT actor_id,loai_su_kien,truoc,sau FROM nhat_ky.mtq_thay_doi
                    WHERE doi_tuong_bang='master.mtq_pham_vi' AND doi_tuong->>'id'=%s""", (row["id"],)).fetchone()
                self.assertEqual(audit[:3], (self.admin[0], "PHAM_VI", None))
                self.assertEqual(audit[3]["khoa"], row["khoa"])
                self.assertEqual(audit[3]["phap_nhan_id"], str(self.pn))

    def test_uuid_profile_chon_tuong_minh_instance_nhieu_profile_bi_chan(self):
        self.mapping()
        self.them_profile("PROFILE_KHAC")
        self.loi("MTQ_NGUON_PROFILE", self.cap)
        row = self.cap("INVOICE_SET|" + str(self.profile[0]) + "|CTY A")
        self.assertEqual(row["khoa"], "INVOICE_SET|" + str(self.profile[0]).upper() + "|CTY A")

    def test_khong_map_sai_pn_sai_loai_va_gia_quan_he_deu_chan(self):
        self.loi("MTQ_NGUON_ANH_XA", self.cap)
        self.mapping(pn=self.pn2)
        self.loi("MTQ_NGUON_ANH_XA", self.cap)
        self.loi("MTQ_NGUON_ANH_XA", lambda: self.cap("KHO10_PHIEU|" + self.inst + "|CTY A"))
        self.loi("MTQ_NGUON_ANH_XA", lambda: self.ghi("PHAM_VI", {
            "gan_vai_id": self.gan, "phap_nhan_id": str(self.pn), "loai": "NGUON",
            "khoa": "INVOICE_SET|" + self.inst + "|CTY A",
            "quan_he": {"phap_nhan_id": str(self.pn), "da_xac_minh": True}}))

    def test_profile_khong_map_instance_dung_va_id_khong_ton_tai_chan(self):
        self.mapping()
        pr2 = self.them_profile("KHONG_MAP")
        self.loi("MTQ_NGUON_ANH_XA", lambda: self.cap("INVOICE_SET|" + str(pr2[0]) + "|CTY A"))
        self.loi("MTQ_NGUON_PROFILE", lambda: self.cap("INVOICE_SET|KHONG_CO|CTY A"))
        self.c.execute("UPDATE master.nguon_instance SET trang_thai='DUNG' WHERE source_instance_id=%s", (self.inst,))
        self.loi("MTQ_NGUON_PROFILE", lambda: self.cap("INVOICE_SET|" + str(self.profile[0]) + "|CTY A"))

    def test_mapping_tuong_lai_bi_chan(self):
        self.mapping(future=True)
        self.loi("MTQ_NGUON_ANH_XA", self.cap)

    def test_mapping_dong_het_han_bi_chan_nhung_van_thu_hoi_duoc(self):
        m = self.mapping()
        row = self.cap()
        self.dong_mapping(m, expired=True)
        self.loi("MTQ_NGUON_ANH_XA", self.cap)
        revoked = self.ghi("THU_HOI_PHAM_VI", {"id": row["id"]}, 1)
        self.assertIsNotNone(revoked["thu_hoi_luc"])

    def test_mapping_dong_du_valid_to_tuong_lai_van_chan(self):
        m = self.mapping()
        self.dong_mapping(m)
        self.loi("MTQ_NGUON_ANH_XA", self.cap)

    def test_anh_xa_trung_sau_chuan_hoa_bi_chan_ke_ca_cung_pn(self):
        self.mapping()
        self.mapping(key="cty   a")
        self.loi("MTQ_NGUON_ANH_XA", self.cap)

    def test_khoa_sai_va_l11_khong_cap_nguon(self):
        self.mapping()
        for key in ("", "INVOICE_SET|x", "INVOICE_SET|x|y|z", "INVOICE_SET| |CTY A", "INVOICE_SET|x| \t"):
            with self.subTest(key=key):
                self.loi("MTQ_NGUON_KHOA", lambda: self.cap(key))
        for loai in ("L11_EVIDENCE_SET", "KHAC"):
            self.loi("MTQ_NGUON_LOAI", lambda: self.cap(loai + "|" + self.inst + "|CTY A"))

    def test_khac_pn_phong_va_gan_vai_da_thu_hoi_chan(self):
        self.mapping()
        self.mapping(key="CTY B", pn=self.pn2)
        self.loi("MTQ_PHAM_VI", lambda: self.cap("INVOICE_SET|" + self.inst + "|CTY B", pn=self.pn2))
        self.loi("foreign key", lambda: self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]),
            "phap_nhan_id": str(self.pn2), "phong_id": self.phong, "vai": "NGUOI_XEM"}))
        self.ghi("THU_HOI_VAI", {"id": self.gan}, 1)
        self.loi("MTQ_PHAM_VI", self.cap)

    def test_nguon_gop_cap_tung_dong_rieng_khong_tu_cap_pn_khac(self):
        self.mapping()
        self.mapping(key="CTY B", pn=self.pn2)
        self.cap()
        self.assertEqual(self.c.execute("SELECT count(*) FROM master.mtq_pham_vi WHERE phap_nhan_id=%s", (self.pn2,)).fetchone()[0], 0)
        p2 = self.ghi("PHONG", {"phap_nhan_id": str(self.pn2), "ma": "KT", "ten": "KT PN khác"})
        g2 = self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]), "phap_nhan_id": str(self.pn2),
            "phong_id": p2["id"], "vai": "NGUOI_XEM"})
        row = self.cap("INVOICE_SET|" + self.inst + "|CTY B", pn=self.pn2, gan=g2["id"])
        self.assertEqual(row["phap_nhan_id"], str(self.pn2))

    def test_admin_thu_hoi_co_audit_sau_dung_nguon_va_thu_hoi_vai(self):
        self.mapping()
        row = self.cap()
        self.ghi("THU_HOI_VAI", {"id": self.gan}, 1)
        self.c.execute("UPDATE master.nguon_instance SET trang_thai='DUNG' WHERE source_instance_id=%s", (self.inst,))
        self.loi("MTQ_REVISION", lambda: self.ghi("THU_HOI_PHAM_VI", {"id": row["id"]}, 9))
        revoked = self.ghi("THU_HOI_PHAM_VI", {"id": row["id"]}, 1)
        self.assertEqual(revoked["revision"], 2)
        audit = self.c.execute("""SELECT actor_id,truoc,sau FROM nhat_ky.mtq_thay_doi
            WHERE doi_tuong->>'id'=%s AND loai_su_kien='THU_HOI_PHAM_VI'""", (row["id"],)).fetchone()
        self.assertEqual(audit[0], self.admin[0])
        self.assertIsNone(audit[1]["thu_hoi_luc"])
        self.assertIsNotNone(audit[2]["thu_hoi_luc"])
        self.loi("MTQ_REVISION", lambda: self.ghi("THU_HOI_PHAM_VI", {"id": row["id"]}, 2))

    def test_nonadmin_khong_cap_khong_thu_hoi_va_khong_sua_khoa(self):
        self.mapping()
        row = self.cap()
        self.actor(self.user)
        self.loi("MTQ_CHI_ADMIN", self.cap)
        self.loi("MTQ_CHI_ADMIN", lambda: self.ghi("THU_HOI_PHAM_VI", {"id": row["id"]}, 1))
        self.loi("MTQ_CHI_ADMIN", lambda: self.c.execute("""INSERT INTO master.mtq_pham_vi
            (gan_vai_id,phap_nhan_id,loai,khoa,cap_boi,ly_do)
            VALUES (%s,%s,'NGUON',%s,%s,'Giả cấp trực tiếp')""",
            (self.gan, self.pn, row["khoa"], self.user[0])))
        self.actor(self.admin)
        self.loi("MTQ_BAT_BIEN", lambda: self.c.execute("""UPDATE master.mtq_pham_vi
            SET khoa=khoa || '_KHAC',revision=revision+1 WHERE id=%s""", (row["id"],)))
        self.loi("duplicate key", lambda: self.cap(" invoice_set | " + self.inst.lower() + " | cty   a "))

    def test_pham_vi_pn_cu_giu_nguyen_khong_can_mapping(self):
        row = self.cap(str(self.pn), loai="PHAP_NHAN")
        self.assertEqual(row["khoa"], str(self.pn))
        self.loi("MTQ_PHAM_VI", lambda: self.cap(str(self.pn2), loai="PHAP_NHAN"))
        self.assertFalse(self.c.execute("SELECT master.mtq_san_sang(%s)", (self.pn,)).fetchone()[0])


if __name__ == "__main__":
    unittest.main()
