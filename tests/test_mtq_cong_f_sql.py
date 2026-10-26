"""MTQ-NEN-0: resolver chỉ đọc; đối chiếu cổng với toàn thân M0048.

Kế thừa toàn bộ ca PG của C/CRM/M4, dùng fixture/trigger thật đã có.
Chỉ KHO_PG_DSN_TEST quản trị tạo kho_test_*; không mở server hoặc xóa DB.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import unittest
import uuid

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_mtq_cong import MTQ_CONG_E_SQL, MTQ_CONG_F_SQL
from tests import test_mtq_cong_c_sql as cong
from tests import test_mtq_crm_resolver_sql as crm
from tests import test_mtq_m4_resolver as m4

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = "master.mtq_giai_doi_tuong(text,jsonb)"
OLD_DECISION = "master.mtq_quyet_dinh_phien_nen0_m0048"
OLD_AUDIT = "master.mtq_ghi_tu_choi_phien_nen0_m0048"
KEYS = {"pn", "hd", "da", "lh", "khach", "phong", "hop_le", "ma", "ly_do", "loai", "man", "module"}
RESOLVER_START = "                    -- Không SQL động, không để client chọn bảng tùy ý."
ACTIVATION = "                    IF NOT EXISTS (SELECT 1 FROM master.mtq_kich_hoat"
CATALOG_START = "                        SELECT c.loai_doi_tuong, c.man, c.module"
SCOPE_START = "                            SELECT count(*), (array_agg(g.phong_id))[1]"
AUDIT_START = "            IF p_doi_tuong->>'bang' = 'master.hop_dong' THEN"
AUDIT_END = "            SELECT g.phong_id, g.vai INTO phong, vai_hd"


def section(source, start, end):
    return source.split(start, 1)[1].split(end, 1)[0]


class MtqCongFTinh(unittest.TestCase):
    def test_registry_chi_append_khong_ghim_migration_cuoi(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# MTQ-NEN-0 — CD-012:"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, "exec"), old)
        previous = old["PG_MIGRATIONS"]
        self.assertEqual(PM.PG_MIGRATIONS[:len(previous)], previous)
        self.assertIs(PM.PG_MIGRATIONS[len(previous)], MTQ_CONG_F_SQL)
        self.assertEqual(sum(m is MTQ_CONG_F_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        self.assertIs(PM.M00xx_MTQ_CONG_F, MTQ_CONG_F_SQL)

    def test_resolver_stable_khong_ghi_khong_sql_dong(self):
        helper = MTQ_CONG_F_SQL[0]
        self.assertIn("p_hanh_dong text, p_doi_tuong jsonb) RETURNS jsonb", helper)
        self.assertIn("LANGUAGE plpgsql STABLE SECURITY DEFINER", helper)
        self.assertIn("SET search_path = pg_catalog, master, nhat_ky, pg_temp", helper)
        sql = re.sub(r"--[^\n]*", "", helper)
        self.assertNotRegex(sql, r"\b(?:INSERT|UPDATE|DELETE|MERGE|EXECUTE|CALL|PERFORM|LOCK|CREATE TABLE|ALTER|DROP)\b")
        self.assertNotIn("master.mtq_quyet_dinh(", sql)
        self.assertNotIn("master.mtq_kich_hoat", sql)
        self.assertNotIn("master.mtq_gan_vai", sql)
        self.assertNotIn("master.ktt_danh_tinh", sql)
        self.assertNotIn("nhat_ky.", sql)
        returned = helper.split("RETURN jsonb_build_object(", 1)[1]
        self.assertEqual(set(re.findall(r"'([a-z_]+)'", returned)), KEYS)

    def test_nguyen_khoi_resolver_va_whitelist_m0048(self):
        helper, old = MTQ_CONG_F_SQL[0], MTQ_CONG_E_SQL[0]
        self.assertEqual(section(old, RESOLVER_START, ACTIVATION),
                         section(helper, RESOLVER_START, "                    IF pn IS NULL THEN"))
        # Whitelist giữ từng byte, chỉ bỏ ELSE dẫn sang phần tìm phòng/phạm vi.
        whitelist = CATALOG_START + section(old, CATALOG_START, SCOPE_START)
        self.assertIn(whitelist.removesuffix("                        ELSE\n"), helper)
        validation = section(old, "            ELSIF jsonb_typeof", "                    PERFORM pg_advisory")
        self.assertIn("            IF jsonb_typeof" + validation, helper)

    def test_cong_giu_danh_tinh_cu_pham_vi_loi_va_khoa(self):
        old, new = MTQ_CONG_E_SQL[0], MTQ_CONG_F_SQL[1]
        self.assertEqual(section(old, "        BEGIN\n", RESOLVER_START),
                         section(new, "        BEGIN\n", "                    giai :="))
        self.assertEqual(section(old, ACTIVATION, CATALOG_START),
                         section(new, ACTIVATION, "                        IF NOT (giai->>'hop_le')"))
        self.assertEqual(old.split(SCOPE_START, 1)[1], new.split(SCOPE_START, 1)[1])
        self.assertIn("giai := master.mtq_giai_doi_tuong(p_hanh_dong, p_doi_tuong)", new)
        for key in ("pn", "hd", "da", "lh", "khach", "phong", "loai", "hop_le", "ma", "ly_do"):
            self.assertIn(f"giai->>'{key}'", new)

    def test_audit_giu_request_insert_va_id_trong_quyet_dinh(self):
        old, new = MTQ_CONG_E_SQL[1], MTQ_CONG_F_SQL[2]
        marker = "            -- Giữ đúng ID chuẩn hóa trong quyết định M0048"
        self.assertEqual(old.split(AUDIT_START, 1)[0], new.split(marker, 1)[0])
        self.assertEqual(old.split(AUDIT_END, 1)[1], new.split(AUDIT_END, 1)[1])
        self.assertIn("master.mtq_giai_doi_tuong(p_hanh_dong,", new)
        self.assertIn("jsonb_build_object('bang',p_doi_tuong->>'bang','id',kq->>'doi_tuong')", new)

    def test_chu_ky_acl_hai_cong_giu_nguyen_va_acl_resolver(self):
        for new, old in zip(MTQ_CONG_F_SQL[1:3], MTQ_CONG_E_SQL[:2]):
            self.assertEqual(new.split("DECLARE", 1)[0], old.split("DECLARE", 1)[0])
        self.assertEqual(MTQ_CONG_F_SQL[3:5], MTQ_CONG_E_SQL[2:])
        self.assertEqual(MTQ_CONG_F_SQL[5:], (f"REVOKE ALL ON FUNCTION {RESOLVER} FROM PUBLIC",))
        self.assertNotRegex("\n".join(MTQ_CONG_F_SQL),
                            r"(?is)\bGRANT\b[^;]*\bmtq_giai_doi_tuong\b")
        for sql in MTQ_CONG_F_SQL[:3]:
            self.assertNotIn("EXECUTE ", sql)

    def test_utf8_khong_bom_migration_lf_hang_literal(self):
        paths = (Path(PM.__file__), ROOT / "src/kho_tri_thuc/k2/sql_mtq_cong.py", Path(__file__))
        for path in paths:
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn("\ufffd", raw.decode("utf-8"))
        self.assertNotIn(b"\r", paths[0].read_bytes())
        tree = ast.parse(paths[1].read_text(encoding="utf-8"))
        values = {a.targets[0].id: ast.literal_eval(a.value) for a in tree.body}
        self.assertEqual(values["MTQ_CONG_F_SQL"], MTQ_CONG_F_SQL)


class _SoM0048:
    """Oracle mang toàn thân cũ, chỉ đổi tên trong CSDL test; không mock lõi."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for sql in MTQ_CONG_E_SQL:
            cls.c.execute(sql.replace("master.mtq_quyet_dinh_phien", OLD_DECISION)
                          .replace("master.mtq_ghi_tu_choi_phien", OLD_AUDIT))

    def cong(self, action, obj, money=None):
        args = (action, json.dumps(obj), money)
        old = self.c.execute(f"SELECT {OLD_DECISION}(%s,%s::jsonb,%s)", args).fetchone()[0]
        new = self.c.execute("SELECT master.mtq_quyet_dinh_phien(%s,%s::jsonb,%s)", args).fetchone()[0]
        self.assertEqual(new, old, (action, obj, money))
        return new

    def audit_row(self, function, request, action, obj, repeat=True):
        # SAVEPOINT rollback cả dòng audit, giữ nguyên cùng fixture/request cho oracle.
        with self.c.transaction(force_rollback=True):
            args = (request, action, json.dumps(obj))
            query = f"SELECT {function}(%s,%s,%s::jsonb,NULL)"
            key = self.c.execute(query, args).fetchone()[0]
            if repeat:
                self.assertEqual(self.c.execute(query, args).fetchone()[0], key)
            return self.c.execute(
                "SELECT to_jsonb(t) - 'id' - 'luc' FROM nhat_ky.mtq_tu_choi t WHERE id=%s", (key,)
            ).fetchone()[0]

    def test_audit_so_m0048_tung_cap_cung_du_lieu_va_request(self):
        self.cau_hinh(scope=None)
        for action, obj in self.reference_pairs():
            with self.subTest(action=action, obj=obj):
                request = uuid.uuid4()
                self.assertEqual(self.audit_row("master.mtq_ghi_tu_choi_phien", request, action, obj),
                                 self.audit_row(OLD_AUDIT, request, action, obj))

    def test_loi_dau_vao_thu_tu_danh_tinh_va_audit_so_m0048(self):
        self.cau_hinh(scope=None)
        action, obj = next(iter(self.reference_pairs()))
        invalid = [None, [], "gia", {}, {"bang": obj["bang"]},
                   {**obj, "actor_id": str(self.user[0])},
                   {**obj, "id": "sai-uuid"}, {**obj, "phong_id": "sai-uuid"},
                   {**obj, "id": str(uuid.uuid4())},
                   {**obj, "id": "{" + obj["id"].upper() + "}"},
                   {**obj, "bang": "pg_catalog.pg_authid"}]
        for bad in invalid:
            with self.subTest(obj=bad):
                self.cong(action, bad)
                request = uuid.uuid4()
                # M0048 so request với chuỗi caller, nên ID không chuẩn hóa hoặc
                # đầu vào lỗi có thể không replay được; chỉ so lần ghi đầu ở đây.
                self.assertEqual(self.audit_row("master.mtq_ghi_tu_choi_phien", request, action, bad, False),
                                 self.audit_row(OLD_AUDIT, request, action, bad, False))
        self.actor((self.admin[0], self.user[1]))
        self.assertEqual(self.cong(action, obj)["ma"], "MTQ_DANH_TINH")
        self.assertEqual(self.cong(action, None)["ma"], "MTQ_DANH_TINH")


class MtqCongFCRM_BPostgres(_SoM0048, cong.MtqCongCPostgres):
    def reference_pairs(self):
        return [(action, self.objects[table]) for _, action, table in cong.CASES]


class MtqCongFCRM_GPostgres(_SoM0048, crm.MtqCrmResolverPostgres):
    def reference_pairs(self):
        return [(action, self.objects[key]) for key, actions in crm.ALLOWED.items() for action in actions]


class MtqCongFM4Postgres(_SoM0048, m4.MtqM4ResolverPostgres):
    def reference_pairs(self):
        return [*self.pairs(), ("M4:02C_DUYET:DUYET", self.objects["m4.duyet_ket_luan"])]


@unittest.skipUnless(cong.DSN and cong.psycopg is not None,
                     "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class MtqCongFReadOnlyPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Một CSDL test riêng, migrate thật; không dùng CSDL/DSN của ứng dụng.
        cong.MtqCongCPostgres.setUpClass.__func__(cls)

    def test_read_only_owner_du_crm_m4_app_web_bi_chan_va_acl(self):
        base = cong.MtqCongCPostgres(methodName="runTest")
        base.c = self.c
        self.addCleanup(base.doCleanups)
        base.setUp()
        fixtures = [base]
        for fixture_class in (crm.MtqCrmResolverPostgres, m4.MtqM4ResolverPostgres):
            fixture = fixture_class(methodName="runTest")
            # Chung PN/danh tính đã bootstrap một lần; chỉ tái dùng đồ thị
            # fixture của CRM/M4, không gọi lại bootstrap hoặc tắt trigger.
            for name in ("c", "pn", "pn2", "admin", "user", "phong", "phong2"):
                setattr(fixture, name, getattr(base, name))
            fixture.objects, fixture.refs = fixture.fixture(base.pn)
            fixtures.append(fixture)
        base.cau_hinh()
        other_objects = [base.obj("master.phap_nhan", base.pn2),
                         base.obj("master.hop_dong", base.hop_dong(base.pn2))]
        # CSDL riêng của đúng một test này; commit dữ liệu giả để mở một
        # giao dịch READ ONLY mới trước mọi SELECT/SET ROLE.
        self.c.execute("COMMIT")

        def audit_counts():
            return self.c.execute("SELECT (SELECT count(*) FROM nhat_ky.mtq_tu_choi), "
                                  "(SELECT count(*) FROM nhat_ky.mtq_thay_doi)").fetchone()

        before = audit_counts()
        self.c.execute("BEGIN")
        self.addCleanup(self.c.execute, "ROLLBACK")
        self.c.execute("SET TRANSACTION READ ONLY")
        self.assertEqual(self.c.execute("SHOW transaction_read_only").fetchone()[0], "on")
        pairs = [(action, fixtures[0].objects[table]) for _, action, table in cong.CASES]
        pairs += [(action, fixtures[1].objects[key]) for key, actions in crm.ALLOWED.items() for action in actions]
        pairs += list(fixtures[2].pairs())
        for action, obj in pairs:
            with self.subTest(action=action, obj=obj):
                resolved = self.c.execute("SELECT master.mtq_giai_doi_tuong(%s,%s::jsonb)",
                                          (action, json.dumps(obj))).fetchone()[0]
                self.assertEqual(set(resolved), KEYS)
                self.assertIs(resolved["hop_le"], True)
                self.assertIsNone(resolved["ma"])
                self.assertIsNone(resolved["ly_do"])
                self.assertIsNotNone(resolved["pn"])
                self.assertEqual(resolved["module"], action.split(":")[0])
                for bad in ({**obj, "id": str(uuid.uuid4())}, {**obj, "phong_id": "sai-uuid"}, None):
                    result = self.c.execute("SELECT master.mtq_giai_doi_tuong(%s,%s::jsonb)",
                                            (action, json.dumps(bad))).fetchone()[0]
                    self.assertIs(result["hop_le"], False)
        self.c.execute("SET LOCAL ROLE app_web")
        blocked_pairs = pairs + [("M1:TIEN:LAP", other_objects[0]),
                                 ("M1:TIEN:SUA", other_objects[1])]
        for action, obj in blocked_pairs:
            with self.subTest(app_web=action, obj=obj):
                with self.assertRaises(cong.psycopg.errors.InsufficientPrivilege) as error:
                    # SAVEPOINT phục hồi giao dịch sau lỗi quyền của từng lần gọi.
                    with self.c.transaction():
                        self.c.execute("SELECT master.mtq_giai_doi_tuong(%s,%s::jsonb)",
                                       (action, json.dumps(obj)))
                self.assertEqual(error.exception.sqlstate, "42501")
                self.assertIn("mtq_giai_doi_tuong", error.exception.diag.message_primary)
        self.c.execute("RESET ROLE")
        self.assertEqual(audit_counts(), before)
        for signature in (*crm.SIGNATURES, RESOLVER):
            self.assertFalse(self.c.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_proc p, "
                "LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a "
                "WHERE p.oid=%s::regprocedure AND a.grantee=0 AND a.privilege_type='EXECUTE')",
                (signature,)).fetchone()[0])
            self.assertEqual(self.c.execute("SELECT has_function_privilege('app_web',%s,'EXECUTE')",
                                            (signature,)).fetchone()[0], signature != RESOLVER)
        self.assertEqual(self.c.execute(
            "SELECT count(DISTINCT proowner) FROM pg_proc WHERE oid=ANY(%s::regprocedure[])",
            ([*crm.SIGNATURES, RESOLVER],)).fetchone()[0], 1)
        self.assertEqual(self.c.execute(
            "SELECT provolatile,prosecdef,proconfig FROM pg_proc WHERE oid=%s::regprocedure",
            (RESOLVER,)).fetchone(), ("s", True, ["search_path=pg_catalog, master, nhat_ky, pg_temp"]))

    def test_acl_owner_hai_cong_truoc_sau_migration_khong_doi(self):
        def snapshot():
            return self.c.execute(
                "SELECT oid,proacl::text,proowner,prosecdef,proconfig "
                "FROM pg_proc WHERE oid=ANY(%s::regprocedure[]) ORDER BY oid",
                (list(crm.SIGNATURES),)).fetchall()

        with self.c.transaction(force_rollback=True):
            for sql in MTQ_CONG_E_SQL:
                self.c.execute(sql)
            before = snapshot()
            for sql in MTQ_CONG_F_SQL:
                self.c.execute(sql)
            self.assertEqual(snapshot(), before)


def load_tests(loader, tests, pattern):
    # Các subclass trên kế thừa MỌI ca PG cũ và so JSON với oracle M0048
    # ngay trong từng lần gọi cong(). Chạy lại cả các ca tĩnh của ba module.
    for test_class in (cong.MtqCongCTinh, crm.MtqCrmResolverTinh, m4.MtqM4ResolverTinh):
        tests.addTests(loader.loadTestsFromTestCase(test_class))
    return tests


if __name__ == "__main__":
    unittest.main()
