"""MTQ-NEN-2a: cổng tập PN; oracle nguyên thân M0051 và fixture thật.

PG chỉ tạo kho_test_* từ KHO_PG_DSN_TEST quản trị, không mở server/xóa DB.
Resolver hai PN chỉ được thay trong giao dịch test và rollback sau mỗi ca.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import unittest
import uuid

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_mtq_cong import MTQ_CONG_F_SQL, MTQ_CONG_G_SQL
from tests import test_mtq_cong_f_sql as f
from tests import test_mtq_cong_c_sql as cong
from tests import test_mtq_cong_sql as legacy
from tests import test_mtq_sql as nen

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = "master.mtq_giai_doi_tuong_tap(text,jsonb)"
OLD_DECISION = "master.mtq_quyet_dinh_phien_nen2_m0051"
OLD_AUDIT = "master.mtq_ghi_tu_choi_phien_nen2_m0051"
ACTION = "CRM:TIEP_NHAN:DUYET"


class MtqCongGTinh(unittest.TestCase):
    def test_migration_append_khong_ghim_cuoi(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# MTQ-NEN-2a — CD-012:"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, "exec"), old)
        previous = old["PG_MIGRATIONS"]
        self.assertEqual(PM.PG_MIGRATIONS[:len(previous)], previous)
        self.assertIs(PM.PG_MIGRATIONS[len(previous)], MTQ_CONG_G_SQL)
        self.assertEqual(sum(m is MTQ_CONG_G_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_ham_tap_chi_goi_resolver_cu_khong_cap_app(self):
        helper = MTQ_CONG_G_SQL[0]
        self.assertIn("LANGUAGE sql STABLE SECURITY DEFINER", helper)
        self.assertIn("SELECT jsonb_build_array(master.mtq_giai_doi_tuong(p_hanh_dong, p_doi_tuong))", helper)
        self.assertNotRegex(re.sub(r"--[^\n]*", "", helper),
                            r"\b(?:INSERT|UPDATE|DELETE|EXECUTE|PERFORM|LOCK)\b")
        self.assertEqual(MTQ_CONG_G_SQL[3:], (f"REVOKE ALL ON FUNCTION {RESOLVER} FROM PUBLIC",))
        self.assertNotRegex("\n".join(MTQ_CONG_G_SQL), r"\b(?:GRANT|ALTER TABLE|CREATE TABLE|DROP)\b")
        for new, old in zip(MTQ_CONG_G_SQL[1:3], MTQ_CONG_F_SQL[1:3]):
            self.assertEqual(new.split("DECLARE", 1)[0], old.split("DECLARE", 1)[0])

    def test_giu_validation_scope_core_request_va_insert_m0051(self):
        old, new, audit = MTQ_CONG_F_SQL[1], MTQ_CONG_G_SQL[1], MTQ_CONG_G_SQL[2]
        start = "            -- JSON là tham chiếu đối tượng"
        end = "                    PERFORM pg_advisory_xact_lock_shared(742601, 1);"
        self.assertEqual(f.section(old, start, end), f.section(new, start, end))
        start = "SELECT count(*), (array_agg(g.phong_id))[1]"
        end = "s.id LIMIT 1;"
        normalize = lambda text: " ".join(text.split())
        expected = normalize(f.section(old, start, end))
        for current in (new, audit):
            self.assertEqual(normalize(f.section(current, start, end)), expected)
            self.assertIn("khoa, scope_loai, p_so_tien, scope_id, NULL)", current)
            self.assertIn("scope_id := NULL; khoa := NULL; scope_loai := NULL;", current)
            self.assertIn("ORDER BY (value->>'pn')::uuid LOOP", current)
            self.assertIn("RAISE SQLSTATE 'ZMT01'", current)
        start = "            -- Caller rollback nghiệp vụ"
        end = "            -- Giữ đúng ID chuẩn hóa"
        self.assertEqual(f.section(MTQ_CONG_F_SQL[2], start, end), f.section(audit, start, end))
        start = "            SELECT g.phong_id, g.vai INTO phong, vai_hd"
        self.assertEqual(MTQ_CONG_F_SQL[2].split(start, 1)[1], audit.split(start, 1)[1])

    def test_utf8_khong_bom_migration_lf_hang_literal(self):
        paths = (Path(PM.__file__), ROOT / "src/kho_tri_thuc/k2/sql_mtq_cong.py", Path(__file__))
        for path in paths:
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn("\ufffd", raw.decode("utf-8"))
        self.assertNotIn(b"\r", paths[0].read_bytes())
        tree = ast.parse(paths[1].read_text(encoding="utf-8"))
        values = {a.targets[0].id: ast.literal_eval(a.value) for a in tree.body}
        self.assertEqual(values["MTQ_CONG_G_SQL"], MTQ_CONG_G_SQL)


class _SoM0051:
    """Kế thừa mọi ca cổng cũ, so nguyên JSON trên cùng dữ liệu với M0051."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for sql in MTQ_CONG_F_SQL[1:3]:
            cls.c.execute(sql.replace("master.mtq_quyet_dinh_phien", OLD_DECISION)
                          .replace("master.mtq_ghi_tu_choi_phien", OLD_AUDIT))

    def cong(self, action, obj, money=None):
        args = (action, json.dumps(obj), money)
        old = self.c.execute(f"SELECT {OLD_DECISION}(%s,%s::jsonb,%s)", args).fetchone()[0]
        new = self.c.execute("SELECT master.mtq_quyet_dinh_phien(%s,%s::jsonb,%s)", args).fetchone()[0]
        self.assertEqual(new, old, (action, obj, money))
        return new

    def audit_row(self, function, request, action, obj, repeat=True):
        # Các ca kế thừa gọi tên oracle của F; đổi sang toàn thân M0051.
        if function == f.OLD_AUDIT:
            function = OLD_AUDIT
        return super().audit_row(function, request, action, obj, repeat)

    def test_tap_mot_pn_dung_nguyen_json_resolver_cu(self):
        for action, obj in self.reference_pairs():
            for ref in (obj, {**obj, "id": str(uuid.uuid4())}, None):
                with self.subTest(action=action, obj=ref):
                    single, contexts = self.c.execute(
                        "SELECT master.mtq_giai_doi_tuong(%s,%s::jsonb), "
                        "master.mtq_giai_doi_tuong_tap(%s,%s::jsonb)",
                        (action, json.dumps(ref), action, json.dumps(ref))).fetchone()
                    self.assertEqual(contexts, [single])


class MtqCongGCRM_BPostgres(_SoM0051, f.MtqCongFCRM_BPostgres):
    pass


class MtqCongGCRM_GPostgres(_SoM0051, f.MtqCongFCRM_GPostgres):
    pass


class MtqCongGM4Postgres(_SoM0051, f.MtqCongFM4Postgres):
    pass


class MtqCongGCuPostgres(_SoM0051, legacy.MtqCongPostgres):
    def cong(self, action="CRM:DU_AN_BAN:XEM", obj=None, money=None):
        return super().cong(action, self.obj if obj is None else obj, money)

    def reference_pairs(self):
        return [("CRM:DU_AN_BAN:XEM", self.obj)]


@unittest.skipUnless(cong.DSN and cong.psycopg is not None,
                     "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class MtqCongGTapPostgres(unittest.TestCase):
    nguoi = nen.MtqPostgres.nguoi
    actor = nen.MtqPostgres.actor
    ghi = nen.MtqPostgres.ghi
    sua_nhap = nen.MtqPostgres.sua_nhap
    san_sang = nen.MtqPostgres.san_sang
    hop_dong = cong.MtqCongCPostgres.hop_dong

    @classmethod
    def setUpClass(cls):
        cong.MtqCongCPostgres.setUpClass.__func__(cls)
        for sql in MTQ_CONG_F_SQL[1:3]:
            cls.c.execute(sql.replace("master.mtq_quyet_dinh_phien", OLD_DECISION)
                          .replace("master.mtq_ghi_tu_choi_phien", OLD_AUDIT))

    def setUp(self):
        # Đã đọc mtq_kiem_ghi, mtq_ghi_vet, mtq_bat_bien (M0039): mọi phòng
        # đủ năm dòng khi công bố, scope PHAP_NHAN khớp PN, chỉ ghi qua cổng Admin.
        nen.MtqPostgres.setUp(self)
        self.rooms = {self.pn: (self.phong, self.phong2)}
        self.rooms[self.pn2] = tuple(self.ghi("PHONG", {
            "phap_nhan_id": str(self.pn2), "ma": ma, "ten": "Phòng giả NEN-2"})["id"]
            for ma in ("KT", "DA"))
        self.ordered = sorted((self.pn, self.pn2), key=str)
        # hop_dong_kiem cho phép HĐ không đối tác; không dựng đối tác thiếu mapping.
        self.contracts = {pn: self.hop_dong(pn) for pn in self.ordered}
        self.obj = self.ref(self.pn)
        self.resolver_tap(list(reversed(self.ordered)))

    def ref(self, pn):
        return {"bang": "master.hop_dong", "id": str(self.contracts[pn])}

    def resolver_tap(self, pns):
        from psycopg import sql

        # Test-only: quan hệ hai PN được mô phỏng bằng hai kết quả resolver thật;
        # không thêm bảng/nhánh giả vào migration, không tắt bất kỳ trigger nào.
        contexts = [sql.SQL("master.mtq_giai_doi_tuong(p_hanh_dong,{}::jsonb)").format(
            sql.Literal(json.dumps(self.ref(pn)))) for pn in pns]
        self.c.execute(sql.SQL(
            "CREATE OR REPLACE FUNCTION master.mtq_giai_doi_tuong_tap("
            "p_hanh_dong text,p_doi_tuong jsonb) RETURNS jsonb "
            "LANGUAGE sql STABLE SECURITY DEFINER "
            "SET search_path = pg_catalog, master, nhat_ky, pg_temp AS "
            "$$ SELECT jsonb_build_array({}) $$").format(sql.SQL(",").join(contexts)))

    def configure(self, pn, *, tick=True, limit=100, scope=True, role=True, enable=True):
        self.actor(self.admin)
        v = self.ghi("NHAP", {"phap_nhan_id": str(pn)})
        for room in self.rooms[pn]:
            for vai in nen.VAI:
                row = self.sua_nhap(v, "DONG", {"phong_id": room, "vai": vai,
                                                "gioi_han_vnd": limit})
                if room == self.rooms[pn][0] and vai == "TRUONG_PHONG" and tick:
                    self.sua_nhap(v, "O", {"dong_id": row["id"], "module": "CRM",
                                           "man": "TIEP_NHAN", "hanh_dong": "DUYET", "cho_phep": True})
        self.sua_nhap(v, "CONG_BO", {})
        if role:
            g = self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]), "phap_nhan_id": str(pn),
                                     "phong_id": self.rooms[pn][0], "vai": "TRUONG_PHONG"})
            if scope:
                self.ghi("PHAM_VI", {"gan_vai_id": g["id"], "phap_nhan_id": str(pn),
                                      "loai": "PHAP_NHAN", "khoa": str(pn)})
        self.san_sang()
        self.ghi("KICH_HOAT", {"phap_nhan_id": str(pn), "phien_ban_id": v["id"], "bat": enable})
        self.actor(self.user)

    def decision(self, money=100, obj=None):
        return self.c.execute("SELECT master.mtq_quyet_dinh_phien(%s,%s::jsonb,%s)",
                              (ACTION, json.dumps(self.obj if obj is None else obj), money)).fetchone()[0]

    def scalar(self, pn, money=100):
        # Cùng ID đối tượng gộp trong kết quả để so nguyên JSON, không thêm khóa PN.
        result = self.c.execute(f"SELECT {OLD_DECISION}(%s,%s::jsonb,%s)",
                                (ACTION, json.dumps(self.ref(pn)), money)).fetchone()[0]
        result["doi_tuong"] = self.obj["id"]
        return result

    def audit(self, request, money=100, obj=None):
        return self.c.execute("SELECT master.mtq_ghi_tu_choi_phien(%s,%s,%s::jsonb,%s)",
                              (request, ACTION, json.dumps(self.obj if obj is None else obj), money)).fetchone()[0]

    def test_hai_pn_bat_cung_dat_app_web_va_hoi_khong_ghi(self):
        for pn in self.ordered:
            self.configure(pn)
        before = self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0]
        expected = self.scalar(self.ordered[0])
        self.c.execute("SET LOCAL ROLE app_web")
        self.assertEqual(self.decision(), expected)
        self.assertIs(self.decision()["cho_phep"], True)
        self.c.execute("RESET ROLE")
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0], before)

    def test_moi_pn_thieu_tick_tra_nguyen_quyet_dinh_dung_pn(self):
        for failed in self.ordered:
            with self.subTest(pn=failed), self.c.transaction(force_rollback=True):
                for pn in self.ordered:
                    self.configure(pn, tick=pn != failed)
                self.assertEqual(self.decision(), self.scalar(failed))
                self.assertEqual(self.decision()["ma"], "MTQ_CHUA_TICK")

    def test_han_muc_rieng_cung_tien_khong_cong_hay_chia(self):
        for failed in self.ordered:
            with self.subTest(pn=failed), self.c.transaction(force_rollback=True):
                for pn in self.ordered:
                    self.configure(pn, limit=100 if pn == failed else 1000)
                for money, code in ((100, "MTQ_CHO_PHEP"), (101, "MTQ_VUOT_HAN_MUC"),
                                    (None, "MTQ_THIEU_TIEN"), (-1, "MTQ_THIEU_TIEN")):
                    result = self.decision(money)
                    self.assertEqual(result["ma"], code)
                    self.assertEqual(result["so_tien_vnd"], money)
                    if money == 101:
                        self.assertEqual(result, self.scalar(failed, money))
                        key = self.audit(uuid.uuid4(), money)
                        self.assertEqual(self.c.execute(
                            "SELECT phap_nhan_id,ma,so_tien_vnd FROM nhat_ky.mtq_tu_choi WHERE id=%s",
                            (key,)).fetchone(), (failed, code, money))

    def test_pn_sau_thieu_vai_pham_vi_khong_dung_lai_bien_pn_truoc(self):
        first, second = self.ordered
        for option, code in (({"scope": False}, "MTQ_PHAM_VI"), ({"role": False}, "MTQ_GAN_VAI")):
            with self.subTest(option=option), self.c.transaction(force_rollback=True):
                self.configure(first)
                self.configure(second, **option)
                self.assertEqual(self.decision(), self.scalar(second))
                self.assertEqual(self.decision()["ma"], code)
                request = uuid.uuid4()
                key = self.audit(request)
                self.assertEqual(self.c.execute("SELECT phap_nhan_id,ma FROM nhat_ky.mtq_tu_choi WHERE id=%s",
                                                (key,)).fetchone(), (second, code))

    def test_hon_hop_bat_tat_chan_ca_hai_thu_tu(self):
        for enabled in self.ordered:
            with self.subTest(pn=enabled), self.c.transaction(force_rollback=True):
                for pn in self.ordered:
                    self.configure(pn, enable=pn == enabled)
                result = self.decision()
                self.assertIs(result["cho_phep"], False)
                self.assertEqual(result["ma"], "MTQ_PN_HON_HOP")
                self.assertEqual(result["ly_do"], "Đối tượng thuộc nhiều pháp nhân, có pháp nhân chưa bật ma trận")
                request = uuid.uuid4()
                key = self.audit(request)
                self.assertEqual(self.c.execute("SELECT phap_nhan_id FROM nhat_ky.mtq_tu_choi WHERE id=%s",
                                                (key,)).fetchone()[0], self.ordered[0])

    def test_ca_hai_tat_tra_dung_cu_ke_ca_co_phong(self):
        expected = {"nguon": "CU", "can_thiep": False, "cho_phep": None,
                    "ma": "MTQ_TAT", "ly_do": "Giữ đường kiểm quyền cũ"}
        self.actor(self.user)
        self.assertEqual(self.decision(), expected)
        for pn in self.ordered:
            self.configure(pn, enable=False)
        self.assertEqual(self.decision(), expected)
        self.assertEqual(self.decision(obj={**self.obj, "phong_id": self.phong}), expected)

    def test_khong_giai_duoc_pn_giu_cu_khi_tat_chan_khi_co_pn_bat(self):
        missing = uuid.uuid4()
        self.contracts[missing] = uuid.uuid4()  # ID không tồn tại, không tạo dòng giả sai FK.
        self.resolver_tap([missing])
        self.actor(self.user)
        self.assertEqual(self.decision()["ma"], "MTQ_TAT")
        self.configure(self.ordered[0])
        self.assertEqual(self.decision()["ma"], "MTQ_CAN_RESOLVER_MTQ4")
        key = self.audit(uuid.uuid4())
        self.assertEqual(self.c.execute("SELECT phap_nhan_id FROM nhat_ky.mtq_tu_choi WHERE id=%s",
                                        (key,)).fetchone(), (None,))
        # Một ngữ cảnh thiếu PN cũng không được bỏ qua để dùng PN giải được.
        self.resolver_tap([self.ordered[0], missing])
        self.assertEqual(self.decision()["ma"], "MTQ_CAN_RESOLVER_MTQ4")

    def test_nhieu_pn_co_phong_caller_chan_va_audit_pn_dau(self):
        for pn in self.ordered:
            self.configure(pn)
        obj = {**self.obj, "phong_id": self.phong}
        self.assertEqual(self.decision(obj=obj)["ma"], "MTQ_PHONG_MO_HO")
        request = uuid.uuid4()
        key = self.audit(request, obj=obj)
        self.assertEqual(self.c.execute("SELECT phap_nhan_id,ma FROM nhat_ky.mtq_tu_choi WHERE id=%s",
                                        (key,)).fetchone(), (self.ordered[0], "MTQ_PHONG_MO_HO"))

    def test_nhieu_phong_cua_pn_sau_khong_hop_quyen_audit_dung_pn(self):
        for pn in self.ordered:
            self.configure(pn)
        second = self.ordered[1]
        self.actor(self.admin)
        self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]), "phap_nhan_id": str(second),
                              "phong_id": self.rooms[second][1], "vai": "TRUONG_PHONG"})
        self.actor(self.user)
        self.assertEqual(self.decision(), self.scalar(second))
        self.assertEqual(self.decision()["ma"], "MTQ_PHONG_MO_HO")
        key = self.audit(uuid.uuid4())
        self.assertEqual(self.c.execute("SELECT phap_nhan_id FROM nhat_ky.mtq_tu_choi WHERE id=%s",
                                        (key,)).fetchone()[0], second)

    def test_nhat_ky_hai_pn_truot_chi_mot_dong_request_va_idempotent(self):
        for pn in self.ordered:
            self.configure(pn, tick=False)
        self.assertEqual(self.decision(), self.scalar(self.ordered[0]))
        request = uuid.uuid4()
        self.c.execute("SET LOCAL ROLE app_web")
        key = self.audit(request)
        self.assertEqual(self.audit(request), key)
        with self.assertRaisesRegex(cong.psycopg.Error, "MTQ_REQUEST_TRUNG"), self.c.transaction():
            self.audit(request, obj={**self.obj, "id": str(self.pn2)})
        self.c.execute("RESET ROLE")
        rows = self.c.execute("SELECT phap_nhan_id,ma FROM nhat_ky.mtq_tu_choi WHERE request_id=%s",
                              (request,)).fetchall()
        self.assertEqual(rows, [(self.ordered[0], "MTQ_CHUA_TICK")])


@unittest.skipUnless(cong.DSN and cong.psycopg is not None,
                     "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class MtqCongGACLPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cong.MtqCongCPostgres.setUpClass.__func__(cls)

    def test_ham_tap_read_only_app_web_khong_goi_duoc(self):
        self.c.execute("BEGIN READ ONLY")
        self.addCleanup(self.c.execute, "ROLLBACK")
        args = ("CRM:TIEP_NHAN:LAP", json.dumps({"bang": "master.phap_nhan", "id": str(uuid.uuid4())}))
        single = self.c.execute("SELECT master.mtq_giai_doi_tuong(%s,%s::jsonb)", args).fetchone()[0]
        self.assertEqual(self.c.execute("SELECT master.mtq_giai_doi_tuong_tap(%s,%s::jsonb)",
                                        args).fetchone()[0], [single])
        self.assertEqual(self.c.execute(
            "SELECT provolatile,prosecdef,proconfig FROM pg_proc WHERE oid=%s::regprocedure",
            (RESOLVER,)).fetchone(), ("s", True, ["search_path=pg_catalog, master, nhat_ky, pg_temp"]))
        self.assertFalse(self.c.execute(
            "SELECT has_function_privilege('app_web',%s,'EXECUTE')", (RESOLVER,)).fetchone()[0])
        self.assertFalse(self.c.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_proc p, "
            "LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a "
            "WHERE p.oid=%s::regprocedure AND a.grantee=0 AND a.privilege_type='EXECUTE')",
            (RESOLVER,)).fetchone()[0])
        self.c.execute("SET LOCAL ROLE app_web")
        with self.assertRaises(cong.psycopg.errors.InsufficientPrivilege), self.c.transaction():
            self.c.execute("SELECT master.mtq_giai_doi_tuong_tap(%s,%s::jsonb)", args)

    def test_acl_oid_owner_hai_cong_truoc_sau_khong_doi(self):
        def snapshot():
            return self.c.execute(
                "SELECT oid,proacl::text,proowner,prosecdef,proconfig FROM pg_proc "
                "WHERE oid=ANY(%s::regprocedure[]) ORDER BY oid", (list(cong.SIGNATURES),)).fetchall()

        with self.c.transaction(force_rollback=True):
            for sql in MTQ_CONG_F_SQL[1:3]:
                self.c.execute(sql)
            before = snapshot()
            for sql in MTQ_CONG_G_SQL[1:3]:
                self.c.execute(sql)
            self.assertEqual(snapshot(), before)
            self.assertEqual(self.c.execute(
                "SELECT count(DISTINCT proowner) FROM pg_proc WHERE oid=ANY(%s::regprocedure[])",
                ([*cong.SIGNATURES, RESOLVER],)).fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
