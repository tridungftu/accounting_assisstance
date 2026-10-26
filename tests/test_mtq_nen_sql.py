"""MTQ-NEN-1: quyết định STABLE không ghi; PG do lead chạy trên kho_test_*.

Chỉ DSN quản trị KHO_PG_DSN_TEST, không mở server, không xóa CSDL/vai.
Fixture dùng API cấu hình/trigger thật; readiness chỉ giả lập trong CSDL test.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import unittest
import uuid

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_ma_tran_tham_quyen import MA_TRAN_THAM_QUYEN_SQL
from kho_tri_thuc.k2.sql_mtq_cong import MTQ_CONG_F_SQL
from kho_tri_thuc.k2.sql_mtq_nen import MTQ_NEN_A_SQL
from tests import test_mtq_cong_sql as cong
from tests import test_mtq_cong_c_sql as cong_c
from tests import test_mtq_sql as nen

ROOT = Path(__file__).resolve().parents[1]
READ = "master.mtq_duoc_doc(text,jsonb,numeric)"
PURE = "master.mtq_tinh_doc(uuid,uuid,text,text,text,text,text,numeric,uuid)"
RESOLVER = "master.mtq_giai_doi_tuong(text,jsonb)"
ACTION = "CRM:DU_AN_BAN:XEM"
_OMITTED = object()


def normalized(sql):
    return " ".join(re.sub(r"--[^\n]*", "", sql).split())


class MtqNenTinh(unittest.TestCase):
    def test_registry_chi_append_khong_ghim_migration_cuoi(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# MTQ-NEN-1 — CD-012:"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, "exec"), old)
        previous = old["PG_MIGRATIONS"]
        self.assertEqual(PM.PG_MIGRATIONS[:len(previous)], previous)
        self.assertIs(PM.PG_MIGRATIONS[len(previous)], MTQ_NEN_A_SQL)
        self.assertIs(PM.M00xx_MTQ_NEN_A, MTQ_NEN_A_SQL)
        self.assertEqual(sum(m is MTQ_NEN_A_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_hai_ham_stable_chi_doc_khong_khoa_khong_rollback(self):
        for function in MTQ_NEN_A_SQL[:2]:
            code = re.sub(r"--[^\n]*", "", function)
            self.assertIn("LANGUAGE plpgsql STABLE", code)
            self.assertIn("SET search_path = pg_catalog, master, nhat_ky, pg_temp", code)
            body = code.split("AS $$", 1)[1]
            self.assertNotRegex(body, r"\b(?:INSERT|UPDATE|DELETE|MERGE|EXECUTE|CALL|PERFORM|LOCK|EXCEPTION|RAISE)\b")
            self.assertNotIn("master.mtq_quyet_dinh(", body)
            self.assertNotIn("master.mtq_quyet_dinh_phien(", body)
            self.assertNotIn("nhat_ky.", body)
        wrapper = MTQ_NEN_A_SQL[1]
        self.assertIn("STABLE SECURITY DEFINER", wrapper)
        self.assertIn("p_hanh_dong text, p_doi_tuong jsonb, p_so_tien numeric DEFAULT NULL) RETURNS boolean",
                      normalized(wrapper))
        self.assertEqual(sum(s.startswith("CREATE FUNCTION master.mtq_duoc_doc(")
                             for s in MTQ_NEN_A_SQL), 1)
        self.assertIn("master.ktt_danh_tinh()", wrapper)
        self.assertIn("master.mtq_giai_doi_tuong(p_hanh_dong, p_doi_tuong)", wrapper)
        self.assertNotRegex(wrapper, r"master\.(?:ktt_duoc|ktt_co_vai|ktt_pn_cho_phep)\(")

    def test_loi_thuan_giu_cac_select_va_dieu_kien_m0039(self):
        old = next(s for s in MA_TRAN_THAM_QUYEN_SQL
                   if s.startswith("CREATE FUNCTION master.mtq_quyet_dinh("))
        new = MTQ_NEN_A_SQL[0]
        # So toàn bộ truy vấn và predicate, chỉ bỏ mã/lý do/audit của lõi cũ.
        start, end = "SELECT * INTO v FROM", "            kq :="
        core = old.split(start, 1)[1].split(end, 1)[0]
        core = re.sub(r"ma := '[^']+'; ly_do := '[^']+';", "RETURN false;", core)
        core = core.replace("ELSE RETURN false; END IF;", "ELSE RETURN true; END IF;")
        pure = new.split(start, 1)[1].split("        END $$", 1)[0]
        self.assertEqual(normalized(pure), normalized(core))

    def test_chon_phong_pham_vi_giong_cong_m0051(self):
        old, new = MTQ_CONG_F_SQL[1], MTQ_NEN_A_SQL[1]
        start = "SELECT count(*), (array_agg(g.phong_id))[1]"
        end = "IF n > 1 THEN"
        self.assertEqual(normalized(old.split(start, 1)[1].split(end, 1)[0]),
                         normalized(new.split(start, 1)[1].split(end, 1)[0]))
        start, end = "SELECT s.id, s.khoa, s.loai", "s.id LIMIT 1;"
        self.assertEqual(normalized(old.split(start, 1)[1].split(end, 1)[0]),
                         normalized(new.split(start, 1)[1].split(end, 1)[0]))
        self.assertLess(new.index("IS DISTINCT FROM true"), new.index("RETURN NULL"))
        self.assertIn("khoa, scope_loai, p_so_tien, scope_id)", new)

    def test_acl_chi_mo_boolean_khong_mo_resolver_va_loi(self):
        acl = "\n".join(MTQ_NEN_A_SQL[2:])
        self.assertIn("REVOKE ALL ON FUNCTION " + PURE, acl)
        self.assertIn(READ + " FROM PUBLIC", acl)
        grants = re.findall(r"GRANT EXECUTE ON FUNCTION ([^;]+)", acl)
        self.assertEqual(grants, [READ + " TO app_web"])
        self.assertNotIn("mtq_giai_doi_tuong", acl)

    def test_utf8_khong_bom_lf_va_hang_literal(self):
        module = ROOT / "src/kho_tri_thuc/k2/sql_mtq_nen.py"
        for path in (module, Path(PM.__file__), Path(__file__)):
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn("\ufffd", raw.decode("utf-8"))
        self.assertNotIn(b"\r", Path(PM.__file__).read_bytes())
        tree = ast.parse(module.read_text(encoding="utf-8"))
        self.assertEqual(len(tree.body), 2)
        self.assertIn("quyết định đọc/đếm/hiển thị", ast.get_docstring(tree))
        self.assertIn("Thực hiện hành động vẫn phải qua cổng phiên", ast.get_docstring(tree))
        self.assertEqual(ast.literal_eval(tree.body[1].value), MTQ_NEN_A_SQL)


@unittest.skipUnless(nen.DSN and nen.psycopg is not None,
                     "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class _MtqNenFixture(unittest.TestCase):
    nguoi = nen.MtqPostgres.nguoi
    actor = nen.MtqPostgres.actor
    ghi = nen.MtqPostgres.ghi
    nhap = nen.MtqPostgres.nhap
    sua_nhap = nen.MtqPostgres.sua_nhap
    san_sang = nen.MtqPostgres.san_sang
    hop_dong = cong_c.MtqCongCPostgres.hop_dong

    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = "kho_test_mtq_nen_" + uuid.uuid4().hex[:12]
        with nen.psycopg.connect(nen.DSN, autocommit=True) as admin:
            admin.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_web') THEN CREATE ROLE app_web NOLOGIN; END IF; END $$")
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.c = nen.psycopg.connect(make_conninfo(nen.DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c)

    def setUp(self):
        cong.MtqCongPostgres.setUp(self)
        self.other_da = self.new_da(self.pn)
        self.other_pn_obj = {"bang": "master.du_an", "id": str(self.new_da(self.pn2))}

    def new_da(self, pn):
        return self.c.execute("INSERT INTO master.du_an (phap_nhan_id,ma_junsky,ten) "
                              "VALUES (%s,%s,'Dự án MTQ NỀN giả') RETURNING id",
                              (pn, uuid.uuid4().hex)).fetchone()[0]

    def cau_hinh(self, tick=True, limit=100):
        self.actor(self.admin)
        self.version = self.nhap()
        for phong in (self.phong, self.phong2):
            for vai in nen.VAI:
                d = self.sua_nhap(self.version, "DONG", {
                    "phong_id": phong, "vai": vai, "gioi_han_vnd": limit})
                if phong == self.phong and vai == "TRUONG_PHONG" and tick:
                    for man, action in (("DU_AN_BAN", "XEM"), ("G7_CHUAN", "DUYET"),
                                        ("TIEP_NHAN", "DUYET")):
                        self.sua_nhap(self.version, "O", {"dong_id": d["id"], "module": "CRM",
                            "man": man, "hanh_dong": action, "cho_phep": True})
        self.sua_nhap(self.version, "CONG_BO", {})
        self.assignment = self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]),
            "phap_nhan_id": str(self.pn), "phong_id": self.phong, "vai": "TRUONG_PHONG"})
        self.scope = self.ghi("PHAM_VI", {"gan_vai_id": self.assignment["id"],
            "phap_nhan_id": str(self.pn), "loai": "DU_AN", "khoa": str(self.da)})
        self.san_sang()
        self.ghi("KICH_HOAT", {"phap_nhan_id": str(self.pn),
            "phien_ban_id": self.version["id"], "bat": True})
        self.actor(self.user)

    def audit_counts(self):
        return self.c.execute("SELECT (SELECT count(*) FROM nhat_ky.mtq_tu_choi), "
                              "(SELECT count(*) FROM nhat_ky.mtq_thay_doi)").fetchone()

    def doc(self, action=ACTION, obj=None, money=_OMITTED):
        params = (action, json.dumps(self.obj if obj is None else obj))
        if money is _OMITTED:
            return self.c.execute("SELECT master.mtq_duoc_doc(%s,%s::jsonb)", params).fetchone()[0]
        return self.c.execute("SELECT master.mtq_duoc_doc(%s,%s::jsonb,%s::numeric)",
                              (*params, money)).fetchone()[0]

    def so_cong(self, expected, action=ACTION, obj=None, money=_OMITTED):
        before = self.audit_counts()
        actual = self.doc(action, obj, money)
        self.assertIs(actual, expected)
        self.assertEqual(self.audit_counts(), before)
        result = self.c.execute("SELECT master.mtq_quyet_dinh_phien(%s,%s::jsonb,%s::numeric)",
            (action, json.dumps(self.obj if obj is None else obj),
             None if money is _OMITTED else money)).fetchone()[0]
        self.assertIs(actual, result["cho_phep"])
        self.assertEqual(self.audit_counts(), before)


class MtqNenPostgres(_MtqNenFixture):
    def test_chua_bat_va_tat_tuong_minh_tra_null_so_cong(self):
        self.actor(self.user)
        self.so_cong(None)
        self.cau_hinh()
        self.actor(self.admin)
        self.ghi("KICH_HOAT", {"phap_nhan_id": str(self.pn),
            "phien_ban_id": self.version["id"], "bat": False}, 1)
        self.actor(self.user)
        self.so_cong(None)

    def test_bat_dung_sai_pham_vi_khac_module_so_cong(self):
        self.cau_hinh()
        self.so_cong(True)
        self.so_cong(True, obj={**self.obj, "id": "{" + self.obj["id"].upper() + "}"})
        self.so_cong(False, obj={**self.obj, "id": str(self.other_da)})
        self.so_cong(False, obj={**self.obj, "id": str(uuid.uuid4())})
        # Cùng đối tượng/dự án, tick CRM không cấp ô M4.
        self.so_cong(False, action="M4:HO_SO:XEM")
        self.so_cong(True, action="CRM:G7_CHUAN:DUYET")

    def test_thieu_tick_khong_co_duong_vuot_cfo_admin(self):
        self.cau_hinh(tick=False)
        self.so_cong(False)  # Vai cũ của user là CFO.
        self.actor(self.admin)
        self.so_cong(False)

    def test_khac_pn_tat_null_bat_khong_muon_quyen_pn_dau(self):
        self.cau_hinh()
        self.so_cong(None, obj=self.other_pn_obj)
        self.actor(self.admin)
        phong = self.ghi("PHONG", {"phap_nhan_id": str(self.pn2), "ma": "KT", "ten": "PN khác giả"})["id"]
        v = self.ghi("NHAP", {"phap_nhan_id": str(self.pn2)})
        for vai in nen.VAI:
            self.sua_nhap(v, "DONG", {"phong_id": phong, "vai": vai})
        self.sua_nhap(v, "CONG_BO", {})
        self.ghi("KICH_HOAT", {"phap_nhan_id": str(self.pn2), "phien_ban_id": v["id"], "bat": True})
        self.actor(self.user)
        self.so_cong(False, obj=self.other_pn_obj)

    def test_thu_hoi_pham_vi_va_vai_co_hieu_luc_ngay(self):
        self.cau_hinh()
        self.so_cong(True)
        self.actor(self.admin)
        self.ghi("THU_HOI_PHAM_VI", {"id": self.scope["id"]}, 1)
        self.actor(self.user)
        self.so_cong(False)
        self.actor(self.admin)
        self.ghi("PHAM_VI", {"gan_vai_id": self.assignment["id"], "phap_nhan_id": str(self.pn),
                              "loai": "DU_AN", "khoa": str(self.da)})
        self.actor(self.user)
        self.so_cong(True)
        self.actor(self.admin)
        self.ghi("THU_HOI_VAI", {"id": self.assignment["id"]}, 1)
        self.actor(self.user)
        self.so_cong(False)

    def test_phong_mo_ho_khong_tron_quyen_va_phong_dung_sai(self):
        self.cau_hinh()
        self.actor(self.admin)
        g = self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]), "phap_nhan_id": str(self.pn),
                                  "phong_id": self.phong2, "vai": "TRUONG_PHONG"})
        self.ghi("PHAM_VI", {"gan_vai_id": g["id"], "phap_nhan_id": str(self.pn),
                             "loai": "DU_AN", "khoa": str(self.da)})
        self.actor(self.user)
        self.so_cong(False)
        self.so_cong(True, obj={**self.obj, "phong_id": self.phong})
        self.so_cong(False, obj={**self.obj, "phong_id": self.phong2})

    def test_danh_tinh_guc_sai_thieu_khoa_so_cong(self):
        self.cau_hinh()
        self.c.execute("UPDATE master.nguoi_dung SET trang_thai='KHOA' WHERE id=%s", (self.admin[0],))
        for actor in (("", ""), (uuid.uuid4(), self.user[1]), (self.admin[0], self.user[1]),
                      (self.admin[0], self.admin[1]), ("sai-uuid", self.user[1])):
            with self.subTest(actor=actor):
                self.actor(actor)
                self.so_cong(False)

    def test_dau_vao_khong_hop_le_khong_ton_tai_false_ke_ca_tat(self):
        self.actor(self.user)
        for bat in (False, True):
            if bat:
                self.cau_hinh()
            for obj in (None, [], "gia", {}, {"bang": "master.du_an"},
                        {**self.obj, "id": str(uuid.uuid4())}, {**self.obj, "id": "sai-uuid"},
                        {**self.obj, "phong_id": "sai-uuid"}, {**self.obj, "pn": str(self.pn)},
                        {**self.obj, "bang": "pg_catalog.pg_authid"}):
                with self.subTest(bat=bat, obj=obj):
                    before = self.audit_counts()
                    result = self.c.execute("SELECT master.mtq_duoc_doc(%s,%s::jsonb)",
                                            (ACTION, json.dumps(obj))).fetchone()[0]
                    self.assertIs(result, False)
                    self.assertEqual(self.audit_counts(), before)
            for action in (None, "", "KHONG:CO:XEM", "CRM:G3_G4_SOAN_KY:XEM"):
                self.assertIs(self.doc(action), False)

    def test_loi_thuan_so_m0039_du_bien_tien_va_han_muc(self):
        # Mọi fixture vẫn qua trigger; oracle INSERT audit chỉ ở SAVEPOINT rollback.
        for limit in (0, 100, None):
            with self.subTest(limit=limit), self.c.transaction(force_rollback=True):
                self.cau_hinh(limit=limit)
                for money in (None, -1, "NaN", "Infinity", "-Infinity", "1.5", 0, 99, 100, 101, 10**19):
                    with self.subTest(money=money):
                        args = (self.pn, self.phong, "CRM:TIEP_NHAN:DUYET", "TIEP_NHAN",
                                "HO-SO-GIA", str(self.da), "DU_AN", money, self.scope["id"])
                        before = self.audit_counts()
                        pure = self.c.execute("SELECT master.mtq_tinh_doc(%s,%s,%s,%s,%s,%s,%s,%s::numeric,%s)",
                                              args).fetchone()[0]
                        self.assertEqual(self.audit_counts(), before)
                        with self.c.transaction(force_rollback=True):
                            old = self.c.execute("SELECT master.mtq_quyet_dinh(%s,%s,%s,%s,%s,%s,%s,%s::numeric,%s,NULL)",
                                                 args).fetchone()[0]
                        expected = money in (0, 99, 100, 101, 10**19) and (limit is None or money <= limit)
                        self.assertIs(pure, expected)
                        self.assertIs(pure, old["cho_phep"])
                        self.assertEqual(self.audit_counts(), before)

    def test_duyet_co_tien_thieu_co_so_khong_suy_tien_client(self):
        self.cau_hinh(limit=None)
        obj = {"bang": "master.hop_dong", "id": str(self.hop_dong(self.pn, self.da))}
        self.so_cong(False, action="CRM:TIEP_NHAN:DUYET", obj=obj)
        self.assertIs(self.doc("CRM:TIEP_NHAN:DUYET", {**obj, "so_tien": 0}), False)

    def test_duyet_cung_so_tien_so_cong_han_muc_va_mac_dinh_null(self):
        for limit in (100, None):
            with self.subTest(limit=limit), self.c.transaction(force_rollback=True):
                self.cau_hinh(limit=limit)
                obj = {"bang": "master.hop_dong", "id": str(self.hop_dong(self.pn, self.da))}
                self.so_cong(False, action="CRM:TIEP_NHAN:DUYET", obj=obj)
                for money in (99, 100, 101, 10**19, None):
                    with self.subTest(money=money):
                        expected = money is not None and (limit is None or money <= limit)
                        self.so_cong(expected, action="CRM:TIEP_NHAN:DUYET", obj=obj, money=money)
                self.so_cong(True)  # Hai tham số dùng DEFAULT NULL cho đọc không có tiền.
                self.so_cong(True, money=None)

    def test_acl_app_chi_boolean_khong_goi_resolver_loi(self):
        self.cau_hinh()
        obj = {"bang": "master.hop_dong", "id": str(self.hop_dong(self.pn, self.da))}
        self.assertIsNone(self.c.execute(
            "SELECT to_regprocedure('master.mtq_duoc_doc(text,jsonb)')").fetchone()[0])
        self.assertEqual(self.c.execute(
            "SELECT pronargs,pronargdefaults FROM pg_proc WHERE oid=%s::regprocedure",
            (READ,)).fetchone(), (3, 1))
        for signature, allowed in ((READ, True), (RESOLVER, False), (PURE, False)):
            self.assertIs(self.c.execute("SELECT has_function_privilege('app_web',%s,'EXECUTE')",
                                         (signature,)).fetchone()[0], allowed)
            self.assertFalse(self.c.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_proc p, "
                "LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a "
                "WHERE p.oid=%s::regprocedure AND a.grantee=0 AND a.privilege_type='EXECUTE')",
                (signature,)).fetchone()[0])
        self.assertEqual(self.c.execute(
            "SELECT provolatile,prosecdef,prorettype::regtype::text,proconfig FROM pg_proc WHERE oid=%s::regprocedure",
            (READ,)).fetchone(), ("s", True, "boolean", ["search_path=pg_catalog, master, nhat_ky, pg_temp"]))
        before = self.audit_counts()
        self.c.execute("SET LOCAL ROLE app_web")
        self.assertIs(self.doc(), True)
        self.assertIs(self.doc("CRM:TIEP_NHAN:DUYET", obj, money=99), True)
        self.assertIs(self.doc("CRM:TIEP_NHAN:DUYET", obj, money=101), False)
        self.assertIs(self.doc(obj={**self.obj, "id": str(self.other_da)}), False)
        for query, params in (
            ("SELECT master.mtq_giai_doi_tuong(%s,%s::jsonb)", (ACTION, json.dumps(self.obj))),
            ("SELECT master.mtq_tinh_doc(NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL)", ())):
            with self.assertRaises(nen.psycopg.errors.InsufficientPrivilege):
                with self.c.transaction():
                    self.c.execute(query, params)
        self.c.execute("RESET ROLE")
        self.assertEqual(self.audit_counts(), before)


class MtqNenReadOnlyPostgres(_MtqNenFixture):
    # CSDL riêng: ca READ ONLY cần commit fixture; không để bootstrap đã commit
    # ảnh hưởng các ca dùng fixture rollback ở MtqNenPostgres.
    def test_read_only_stable_rls_app_khong_them_nhat_ky(self):
        self.cau_hinh()
        money_obj = {"bang": "master.hop_dong", "id": str(self.hop_dong(self.pn, self.da))}
        # Bảng/policy chỉ trong CSDL kho_test_*; không sửa RLS nền của phần mềm.
        self.c.execute("CREATE TABLE master.mtq_nen1_rls_test (ref jsonb)")
        for obj in (self.obj, {**self.obj, "id": str(self.other_da)}):
            self.c.execute("INSERT INTO master.mtq_nen1_rls_test VALUES (%s::jsonb)", (json.dumps(obj),))
        self.c.execute("ALTER TABLE master.mtq_nen1_rls_test ENABLE ROW LEVEL SECURITY")
        self.c.execute("GRANT SELECT ON master.mtq_nen1_rls_test TO app_web")
        self.c.execute("CREATE POLICY doc ON master.mtq_nen1_rls_test FOR SELECT TO app_web "
                       "USING (master.mtq_duoc_doc('CRM:DU_AN_BAN:XEM',ref) IS TRUE)")
        self.c.execute("CREATE FUNCTION master.mtq_nen1_stable_test(text,jsonb,numeric DEFAULT NULL) RETURNS boolean "
                       "LANGUAGE sql STABLE AS $$ SELECT master.mtq_duoc_doc($1,$2,$3) $$")
        # Commit fixture giả trước READ ONLY; actor GUC local phải đặt lại.
        self.c.execute("COMMIT")
        before = self.audit_counts()
        self.c.execute("BEGIN")
        self.c.execute("SET TRANSACTION READ ONLY")
        self.actor(self.user)
        self.c.execute("SET LOCAL ROLE app_web")
        self.assertEqual(self.c.execute("SHOW transaction_read_only").fetchone()[0], "on")
        for action, obj, expected in ((ACTION, self.obj, True),
                (ACTION, {**self.obj, "id": str(self.other_da)}, False),
                (ACTION, self.other_pn_obj, None), ("M4:HO_SO:XEM", self.obj, False)):
            with self.subTest(action=action, obj=obj):
                self.assertIs(self.doc(action, obj), expected)
                self.assertIs(self.c.execute("SELECT master.mtq_nen1_stable_test(%s,%s::jsonb)",
                    (action, json.dumps(obj))).fetchone()[0], expected)
        self.assertIs(self.doc("CRM:TIEP_NHAN:DUYET", money_obj), False)
        for money, expected in ((99, True), (100, True), (101, False), (None, False)):
            with self.subTest(money=money):
                self.assertIs(self.doc("CRM:TIEP_NHAN:DUYET", money_obj, money), expected)
                self.assertIs(self.c.execute(
                    "SELECT master.mtq_nen1_stable_test(%s,%s::jsonb,%s::numeric)",
                    ("CRM:TIEP_NHAN:DUYET", json.dumps(money_obj), money)).fetchone()[0], expected)
        self.assertEqual(self.c.execute("SELECT ref FROM master.mtq_nen1_rls_test").fetchall(), [(self.obj,)])
        self.c.execute("RESET ROLE")
        self.assertEqual(self.audit_counts(), before)


if __name__ == "__main__":
    unittest.main()
