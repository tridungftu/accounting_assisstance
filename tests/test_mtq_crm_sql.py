"""MTQ-4b1b: guard G1/G7; PG chỉ tạo kho_test_* từ DSN quản trị test.

Không mở server, không đọc cấu hình DEMO, không xóa DB, không tắt trigger.
A3/cổng chỉ đọc và RLS nền do MTQ-NEN phụ trách, không chứng nhận ở lát này.
"""

from __future__ import annotations

import ast
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import unittest
import uuid

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_mtq_crm import MTQ_CRM_A_SQL, MTQ_CRM_B_SQL, MTQ_CRM_C_SQL
from tests import test_mtq_sql as nen

ROOT = Path(__file__).resolve().parents[1]
DSN = os.environ.get("KHO_PG_DSN_TEST")
psycopg = nen.psycopg
POSITION = next(i for i, m in enumerate(PM.PG_MIGRATIONS) if m[:len(MTQ_CRM_A_SQL)] == MTQ_CRM_A_SQL)
MIGRATION = PM.PG_MIGRATIONS[POSITION]
# Đích thật theo từng lệnh, không phải PN/phạm vi từ payload.
COMMANDS = {
    "CRM_MAU_TAI": ("lh", "CRM:G1_MAU:LAP"),
    "CRM_MAU_MAP": ("mv", "CRM:G1_MAU:SUA"),
    "CRM_MAU_GUI_KIEM": ("mv", "CRM:G1_MAU:SUA"),
    "CRM_MAU_KIEM": ("mv", "CRM:G1_MAU:KIEM"),
    "CRM_MAU_TRA_LAI": ("mv", "CRM:G1_MAU:KIEM"),
    "CRM_MAU_DUYET_V4": ("mv", "CRM:G1_MAU:DUYET"),
    "CRM_MAU_TU_CHOI": ("mv", "CRM:G1_MAU:DUYET"),
    "CRM_CHUAN_LAP": ("da", "CRM:G7_CHUAN:LAP"),
    "CRM_CHUAN_GUI_DUYET": ("cv", "CRM:G7_CHUAN:SUA"),
    "CRM_CHUAN_DUYET_V4": ("cv", "CRM:G7_CHUAN:DUYET"),
}
WRITE_ACTIONS = {a for _, a in COMMANDS.values()}
READ_ACTIONS = {"CRM:G1_MAU:XEM", "CRM:G7_CHUAN:XEM"}


def definitions(migrations):
    result = {}
    for migration in migrations:
        for stmt in migration:
            match = re.match(r"CREATE(?: OR REPLACE)? FUNCTION ([\w.]+)\(", stmt)
            if match:
                result[match[1]] = stmt
    return result


BEFORE = definitions(PM.PG_MIGRATIONS[:POSITION])
AFTER = definitions((MIGRATION,))


class MtqCrmSqlTinh(unittest.TestCase):
    def test_append_va_khong_doi_cac_migration_truoc(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# MTQ-4b1b — CD-012:"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, "exec"), old)
        self.assertEqual(PM.PG_MIGRATIONS[:POSITION], old["PG_MIGRATIONS"])
        self.assertEqual(MIGRATION[:len(MTQ_CRM_A_SQL)], MTQ_CRM_A_SQL)
        self.assertEqual(sum(m is MIGRATION for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_chi_dung_g1_g7_khong_sua_cong_va_rls_nen(self):
        self.assertEqual(set(AFTER), {
            "master.crm_g_dich", "master.crm_g_tra", "master.crm_g_mau_doc",
            "master.crm_g_chuan_doc_duoc", "master.crm_g_duoc", "master.crm_g_chuan_xem",
            "master.crm_g_viec_doc_duoc", "master.crm_g_chuan_doc", "master.crm_g_chuan_duyet",
        })
        sql = "\n".join(MIGRATION)
        self.assertNotRegex(sql, r"\b(?:ALTER TABLE|CREATE POLICY|ALTER POLICY|DROP |GRANT )")
        self.assertNotRegex(sql, r"CRM:(?:G2_|G3_|G4_|G5_|G6_|TY_GIA)")
        self.assertNotIn("CREATE OR REPLACE FUNCTION master.ktt_", sql)

    def test_cac_lenh_cu_giu_nguyen_tru_hai_diem_g7(self):
        # Các lệnh G1 dùng guard chung mới, không viết lại graph/digest/hiệu lực.
        self.assertNotIn("master.crm_g_mau_duyet", AFTER)
        self.assertIn("IF kt.kiem_boi = ai THEN", BEFORE["master.crm_g_mau_duyet"])
        old = BEFORE["master.crm_g_chuan_duyet"]
        new = AFTER["master.crm_g_chuan_duyet"]
        self.assertEqual(new, old.replace(
            "IF v.gui_boi = ai THEN",
            "IF v.gui_boi = ai OR (v.lap_boi = ai AND EXISTS (SELECT 1 FROM master.mtq_kich_hoat "
            "WHERE phap_nhan_id = v.phap_nhan_id AND bat)) THEN", 1))
        self.assertEqual(AFTER["master.crm_g_chuan_doc"], BEFORE["master.crm_g_chuan_doc"].replace(
            "LANGUAGE plpgsql STABLE SET search_path", "LANGUAGE plpgsql SET search_path", 1).replace(
            "IF pn IS NULL OR NOT master.ktt_duoc(pn, 'CRM') THEN",
            "IF pn IS NULL OR NOT master.crm_g_chuan_xem(p_du_an, false) THEN", 1))

    def test_ghim_mtq_va_kiem_truoc_replay(self):
        dich = AFTER["master.crm_g_dich"]
        tra = AFTER["master.crm_g_tra"]
        self.assertIn("pg_advisory_xact_lock_shared(742601, 1)", dich)
        self.assertIn("master.crm_g_ai_id() FOR SHARE", dich)
        self.assertLess(tra.index("master.crm_g_dich("), tra.index("master.crm_g_bn_tra("))
        for name, stmt in BEFORE.items():
            if re.search(r"master\.crm_g_(?:mau_(?:tai|anh_xa|gui_kiem|kiem|tra_lai|duyet|tu_choi)|chuan_(?:lap|gui|duyet))$", name):
                self.assertLess(stmt.index("master.crm_g_dich("), stmt.index("master.crm_g_bn_tra("), name)
                self.assertIn("master.la_chu_bang(", stmt, name)

    def test_chu_ky_acl_va_security_definer_cu(self):
        for name, stmt in AFTER.items():
            if name not in BEFORE:
                continue
            self.assertEqual(stmt.split("\n", 1)[0], BEFORE[name].split("\n", 1)[0])
            self.assertEqual("SECURITY DEFINER" in stmt, "SECURITY DEFINER" in BEFORE[name], name)
        self.assertIn("REVOKE ALL ON FUNCTION master.crm_g_chuan_xem(uuid, boolean) FROM PUBLIC", MIGRATION)
        self.assertNotIn("EXCEPTION WHEN", "\n".join(MIGRATION))

    def test_cu_giu_noi_dung_bieu_thuc_vai_cu(self):
        for name in ("master.crm_g_mau_doc", "master.crm_g_chuan_doc_duoc", "master.crm_g_duoc"):
            old = BEFORE[name].split("AS $$", 1)[1].split("$$", 1)[0].strip()
            expression = old.removeprefix("SELECT ").strip()
            self.assertIn(" ".join(expression.split()), " ".join(AFTER[name].split()), name)

    def test_utf8_lf_va_module_chi_hang_literal(self):
        paths = (ROOT / "src/kho_tri_thuc/k2/sql_mtq_crm.py", Path(PM.__file__), Path(__file__))
        for path in paths:
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), str(path))
            self.assertNotIn("\ufffd", raw.decode("utf-8"))
        self.assertNotIn(b"\r", paths[1].read_bytes())
        tree = ast.parse(paths[0].read_text(encoding="utf-8"))
        self.assertEqual(len(tree.body), 3)
        self.assertEqual(ast.literal_eval(tree.body[0].value), MTQ_CRM_A_SQL)
        self.assertEqual(ast.literal_eval(tree.body[1].value), MTQ_CRM_B_SQL)
        self.assertEqual(ast.literal_eval(tree.body[2].value), MTQ_CRM_C_SQL)


@unittest.skipUnless(DSN and psycopg is not None, "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class MtqCrmSqlPostgres(unittest.TestCase):
    nguoi = nen.MtqPostgres.nguoi
    actor = nen.MtqPostgres.actor
    ghi = nen.MtqPostgres.ghi
    nhap = nen.MtqPostgres.nhap
    sua_nhap = nen.MtqPostgres.sua_nhap
    san_sang = nen.MtqPostgres.san_sang
    loi = nen.MtqPostgres.loi

    @classmethod
    def metadata(cls):
        return cls.c.execute(
            "SELECT oid::regprocedure::text,proowner,proacl::text,prosecdef,proconfig "
            "FROM pg_proc WHERE oid=ANY(%s::regprocedure[]) ORDER BY oid",
            (["master.crm_g_dich(text,uuid)", "master.crm_g_tra(text,text,uuid,text)",
              "master.crm_g_mau_doc(uuid,uuid)", "master.crm_g_chuan_doc_duoc(uuid)",
              "master.crm_g_duoc(text,uuid,uuid)", "master.crm_g_viec_doc_duoc(text,uuid,uuid)",
              "master.crm_g_chuan_doc(uuid,text,date)", "master.crm_g_chuan_duyet(text,text,uuid,text,date)"],)
        ).fetchall()

    @classmethod
    def policies(cls):
        return cls.c.execute("SELECT polrelid::regclass::text,polname,polcmd,polpermissive,"
                             "pg_get_expr(polqual,polrelid),pg_get_expr(polwithcheck,polrelid) "
                             "FROM pg_policy ORDER BY polrelid,polname").fetchall()

    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = "kho_test_mtq_crm_guard_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as c:
            c.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_web') "
                      "THEN CREATE ROLE app_web NOLOGIN; END IF; END $$")
            c.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.c = psycopg.connect(make_conninfo(DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c, target=POSITION)
        cls.acl_before, cls.rls_before = cls.metadata(), cls.policies()
        postgres.migrate(cls.c, target=POSITION + 1)
        cls.acl_after, cls.rls_after = cls.metadata(), cls.policies()
        postgres.migrate(cls.c)

    def setUp(self):
        nen.MtqPostgres.setUp(self)
        self.user = self.nguoi("XEM")  # Không module/vai nghiệp vụ/phân công cũ.
        self.sender, self.approver = self.nguoi("XEM"), self.nguoi("XEM")
        self.f = self.fixture(self.pn)
        self.digest = "a" * 64

    def insert(self, table, **data):
        from psycopg import sql
        return self.c.execute(sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
            sql.Identifier(*table.split(".")), sql.SQL(",").join(map(sql.Identifier, data)),
            sql.SQL(",").join(sql.Placeholder() for _ in data)), tuple(data.values())).fetchone()[0]

    def fixture(self, pn):
        from psycopg.types.json import Jsonb

        # Chỉ G1/G7: không cần đối tác/HĐ giả hoặc tắt trigger để dựng fixture.
        sha = hashlib.sha256(b"MTQ_G1_G7_SYNTHETIC").hexdigest()
        digest = hashlib.sha256(b"").hexdigest()  # danh mục rỗng, digest thật của hàm SQL
        login = self.admin[1]
        lh = self.insert("master.loai_hinh_doanh_thu", phap_nhan_id=pn, ma=uuid.uuid4().hex, ten="Loại hình G1 tổng hợp")
        da = self.insert("master.du_an", phap_nhan_id=pn, ma_junsky=uuid.uuid4().hex, ten="Dự án G7 tổng hợp")
        m = self.insert("master.crm_mau", phap_nhan_id=pn, loai_hinh_id=lh, ma_mau=uuid.uuid4().hex, tao_boi=login)
        tep = self.insert("master.crm_mau_tep", phap_nhan_id=pn, raw_sha256=sha, byte_length=1,
                          object_key="crm-mau/" + sha, bo_doc="MTQ_TEST", facts=Jsonb({"occurrences": []}),
                          facts_sha256=sha, trang_thai_doc="DU", tao_boi=login)
        mv = self.insert("master.crm_mau_phien_ban", phap_nhan_id=pn, mau_id=m, loai_hinh_id=lh,
                         phien_ban=1, tep_id=tep, ten_tep="mtq.docx", danh_muc_ref="MTQ_TEST", danh_muc_rev=1,
                         danh_muc_digest=digest, trang_thai="DRAFT", tai_boi=login)
        chuan = self.insert("master.crm_bo_chuan", phap_nhan_id=pn, du_an_id=da, giai_doan="MTQ_TEST", tao_boi=login)
        cv = self.insert("master.crm_bo_chuan_phien_ban", phap_nhan_id=pn, bo_chuan_id=chuan, phien_ban=1,
                         trang_thai="DRAFT", so_dong=1, dong_sha256=sha, lap_boi=login)
        self.insert_dong(cv, pn)
        return dict(lh=lh, da=da, mv=mv, cv=cv, sha=sha, digest=digest)

    def insert_dong(self, cv, pn):
        self.c.execute("INSERT INTO master.crm_bo_chuan_dong(phien_ban_id,phap_nhan_id,thu_tu,lan) VALUES (%s,%s,1,'1')", (cv, pn))

    def legacy(self, actor=None, pn=None, fixture=None):
        who, pn, f = actor or self.user, pn or self.pn, fixture or self.f
        self.c.execute("INSERT INTO master.phan_quyen(nguoi_dung_id,phap_nhan_id,module,duyet_loai_viec) "
                       "VALUES (%s,%s,ARRAY['CRM'],ARRAY['V4'])", (who[0], pn))
        self.insert("master.phan_cong_hanh_dong", nguoi_dung_id=who[0], phap_nhan_id=pn, module="CRM",
                    hanh_dong="CRM_MAU_TAI", loai_hinh_id=f["lh"], cap_boi=self.admin[1])

    def cau_hinh(self, actions=WRITE_ACTIONS, scope="PHAP_NHAN", key=None):
        self.actor(self.admin)
        v = self.nhap()
        for phong in (self.phong, self.phong2):
            for vai in nen.VAI:
                d = self.sua_nhap(v, "DONG", {"phong_id": phong, "vai": vai, "gioi_han_vnd": 0})
                if phong == self.phong and vai == "TRUONG_PHONG":
                    for action in sorted(actions):
                        module, man, hanh = action.split(":")
                        self.sua_nhap(v, "O", {"dong_id": d["id"], "module": module, "man": man,
                                               "hanh_dong": hanh, "cho_phep": True})
        self.sua_nhap(v, "CONG_BO", {})
        grants = []
        for who in (self.user, self.sender, self.approver):
            g = self.ghi("GAN_VAI", {"nguoi_dung_id": str(who[0]), "phap_nhan_id": str(self.pn),
                                     "phong_id": self.phong, "vai": "TRUONG_PHONG"})
            grants.append(g)
            if scope:
                self.ghi("PHAM_VI", {"gan_vai_id": g["id"], "phap_nhan_id": str(self.pn),
                                      "loai": scope, "khoa": str(key or self.pn)})
        self.san_sang()
        self.ghi("KICH_HOAT", {"phap_nhan_id": str(self.pn), "phien_ban_id": v["id"], "bat": True})
        self.actor(self.user)
        return grants

    def dich(self, command, fixture=None, target=None):
        f = fixture or self.f
        return self.c.execute("SELECT * FROM master.crm_g_dich(%s,%s)",
                              (command, target or f[COMMANDS[command][0]])).fetchone()

    def tra(self, command, target=None):
        return self.c.execute("SELECT master.crm_g_tra(%s,'MTQ_REPLAY',%s,%s)",
                              (command, target or self.f[COMMANDS[command][0]], self.digest)).fetchone()[0]

    def test_moi_lenh_tick_bat_khong_can_vai_cu_hoac_xem(self):
        self.cau_hinh()
        for command in COMMANDS:
            with self.subTest(command=command):
                self.assertEqual(self.dich(command)[0], self.pn)
        self.assertIsNone(self.c.execute("SELECT master.crm_g_mau_doc(%s,%s)", (self.pn, self.f["lh"])).fetchone()[0])
        self.assertFalse(self.c.execute("SELECT master.crm_g_chuan_xem(%s,false)", (self.f["da"],)).fetchone()[0])

    def test_tick_tat_chan_ke_ca_cfo_v4_va_assignment_cu(self):
        self.user = self.nguoi("CFO")
        self.legacy()
        self.cau_hinh(actions=())
        for command in COMMANDS:
            with self.subTest(command=command):
                self.loi("MTQ_CHUA_TICK", lambda: self.dich(command))

    def test_tung_o_doc_lap_khong_dung_tick_cua_lenh_khac(self):
        for action in sorted(WRITE_ACTIONS):
            with self.subTest(action=action), self.c.transaction(force_rollback=True):
                self.cau_hinh(actions={action})
                for command, (_, expected) in COMMANDS.items():
                    if expected == action:
                        self.assertEqual(self.dich(command)[0], self.pn)
                    else:
                        self.loi("MTQ_CHUA_TICK", lambda: self.dich(command))

    def test_pham_vi_hep_dung_lh_hoac_du_an_khong_doi_cap_ca_pn(self):
        for scope, key, targets in (("LOAI_HINH", self.f["lh"], {"lh", "mv"}),
                                    ("DU_AN", self.f["da"], {"da", "cv"})):
            with self.subTest(scope=scope), self.c.transaction(force_rollback=True):
                self.cau_hinh(scope=scope, key=key)
                for command, (target, _) in COMMANDS.items():
                    if target in targets:
                        self.assertEqual(self.dich(command)[0], self.pn)
                    else:
                        self.loi("MTQ_PHAM_VI", lambda: self.dich(command))

    def test_thieu_pham_vi_va_id_khong_ton_tai(self):
        self.cau_hinh(scope=None)
        for command in COMMANDS:
            self.loi("MTQ_PHAM_VI", lambda: self.dich(command))
            self.loi("CRM_G_KHONG_THAY", lambda: self.dich(command, target=uuid.uuid4()))
        self.loi("CRM_G_HANH_DONG_SAI", lambda: self.c.execute(
            "SELECT * FROM master.crm_g_dich('CRM_BAO_GIA',%s)", (self.f["mv"],)))

    def test_khong_lan_sang_pn_khac_dang_tat(self):
        f2 = self.fixture(self.pn2)
        self.user = self.nguoi("CFO")
        self.legacy(pn=self.pn2, fixture=f2)
        actors = {"co_quyen_cu": self.user, "khong_quyen_cu": self.sender}

        def capture():
            results = {}
            for label, who in actors.items():
                self.actor(who)
                for command in COMMANDS:
                    try:
                        with self.c.transaction():
                            result = ("CHO", self.dich(command, f2))
                    except psycopg.Error as exc:
                        # Chỉ chấp nhận lỗi quyền của đường cũ, không che lỗi SQL.
                        self.assertEqual(exc.sqlstate, "P0001")
                        self.assertRegex(exc.diag.message_primary, r"^CRM_G_(KHONG_THAY|KHONG_CO_QUYEN):")
                        result = ("CHAN", exc.sqlstate, exc.diag.message_primary)
                    results[label, command] = result
            return results

        # Oracle dùng đúng guard và các hàm quyền trước migration, cùng người/đích.
        # Rollback savepoint khôi phục hàm mới kể cả khi capture thất bại.
        with self.c.transaction(force_rollback=True):
            for name in ("master.crm_g_dich", "master.crm_g_mau_doc",
                         "master.crm_g_chuan_doc_duoc", "master.crm_g_duoc"):
                self.c.execute(BEFORE[name])
            oracle = capture()
        self.assertEqual({result[0] for result in oracle.values()}, {"CHO", "CHAN"})
        for command in COMMANDS:
            self.assertEqual(oracle["khong_quyen_cu", command][0], "CHAN")

        for stage in ("truoc_bat_A", "sau_bat_A"):
            if stage == "sau_bat_A":
                self.cau_hinh()  # Cả hai người có tick MTQ tại A, không cấp quyền cũ tại B.
                self.assertTrue(self.c.execute(
                    "SELECT EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id=%s AND bat)",
                    (self.pn,)).fetchone()[0])
            self.assertFalse(self.c.execute(
                "SELECT EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id=%s AND bat)",
                (self.pn2,)).fetchone()[0])
            actual = capture()
            for (label, command), expected in oracle.items():
                with self.subTest(stage=stage, actor=label, command=command):
                    self.assertEqual(actual[label, command], expected)

    def test_preflight_replay_kiem_lai_sau_thu_hoi(self):
        grants = self.cau_hinh()
        for command in COMMANDS:
            self.c.execute("SELECT master.crm_g_bn_ghi(%s,%s,'MTQ_REPLAY',%s,%s::jsonb)",
                           (self.pn, command, self.digest, json.dumps({"synthetic": command})))
            self.assertTrue(self.tra(command)["lap_lai"])
        self.actor(self.admin)
        self.ghi("THU_HOI_VAI", {"id": grants[0]["id"]}, grants[0]["revision"])
        self.actor(self.user)
        for command in COMMANDS:
            self.loi("MTQ_GAN_VAI", lambda: self.tra(command))
        self.assertEqual(self.c.execute("SELECT count(*) FROM master.crm_g_bien_nhan").fetchone()[0], len(COMMANDS))

    def test_lenh_sql_truc_tiep_khong_tra_bien_nhan_khi_tick_tat(self):
        self.cau_hinh(actions=())
        self.c.execute("SELECT master.crm_g_bn_ghi(%s,'CRM_CHUAN_LAP','MTQ_REPLAY',%s,'{}'::jsonb)", (self.pn, self.digest))
        self.loi("MTQ_CHUA_TICK", lambda: self.c.execute(
            "SELECT master.crm_g_chuan_lap('MTQ_REPLAY',%s,%s,'MTQ_TEST','[]'::jsonb)", (self.digest, self.f["da"])))

    def test_g7_lap_gui_duyet_khac_ca_nguoi_lap_va_gui(self):
        self.cau_hinh()
        made = self.c.execute("SELECT master.crm_g_chuan_lap('LAP',%s,%s,'NEW','[{\"lan\":\"1\"}]'::jsonb)",
                              (self.digest, self.f["da"])).fetchone()[0]["ket_qua"]
        cv = made["phien_ban_id"]
        token = self.c.execute("SELECT master.crm_g_chuan_token(%s)", (cv,)).fetchone()[0]
        self.actor(self.sender)
        self.c.execute("SELECT master.crm_g_chuan_gui('GUI',%s,%s,%s)", (self.digest, cv, token))
        token = self.c.execute("SELECT master.crm_g_chuan_token(%s)", (cv,)).fetchone()[0]
        for who in (self.user, self.sender):
            self.actor(who)
            self.loi("CRM_G_CUNG_NGUOI", lambda: self.c.execute(
                "SELECT master.crm_g_chuan_duyet('DUYET',%s,%s,%s,%s)", (self.digest, cv, token, date(2026, 10, 26))))
        self.actor(self.approver)
        self.loi("CRM_G_TOKEN_CU", lambda: self.c.execute(
            "SELECT master.crm_g_chuan_duyet('DUYET',%s,%s,'sai',%s)", (self.digest, cv, date(2026, 10, 26))))
        result = self.c.execute("SELECT master.crm_g_chuan_duyet('DUYET',%s,%s,%s,%s)",
                                (self.digest, cv, token, date(2026, 10, 26))).fetchone()[0]
        self.assertEqual(result["ket_qua"]["trang_thai"], "HIEU_LUC")

    def test_g1_duyet_khac_nguoi_kiem_va_giu_bat_bien(self):
        from psycopg.types.json import Jsonb

        self.cau_hinh()
        ax = self.insert("master.crm_mau_anh_xa", phien_ban_id=self.f["mv"], phap_nhan_id=self.pn,
                         revision=1, ban_do=Jsonb([]), ban_do_sha256=self.f["sha"], danh_muc_digest=self.f["digest"],
                         canh_bao=Jsonb([]), so_chua_anh_xa=0, so_sai_kieu=0, tao_boi=self.user[1])
        kiem = self.insert("master.crm_mau_kiem_tra", phien_ban_id=self.f["mv"], phap_nhan_id=self.pn, anh_xa_id=ax,
                           raw_sha256=self.f["sha"], facts_sha256=self.f["sha"], danh_muc_digest=self.f["digest"],
                           ban_do_sha256=self.f["sha"], ket_qua="DAT", kiem_boi=self.user[1])
        self.c.execute("UPDATE master.crm_mau_phien_ban SET trang_thai='CHO_CFO',anh_xa_hien_hanh=%s,kiem_hien_hanh=%s WHERE id=%s",
                       (ax, kiem, self.f["mv"]))
        token = self.c.execute("SELECT master.crm_g_mau_token(%s)", (self.f["mv"],)).fetchone()[0]
        self.loi("CRM_G_CUNG_NGUOI", lambda: self.c.execute(
            "SELECT master.crm_g_mau_duyet('DUYET',%s,%s,%s,%s)", (self.digest, self.f["mv"], token, date(2026, 10, 26))))
        self.loi("CRM_G_BAT_BIEN", lambda: self.c.execute("UPDATE master.crm_mau_anh_xa SET ban_do='[]'::jsonb WHERE id=%s", (ax,)))
        self.actor(self.approver)
        result = self.c.execute("SELECT master.crm_g_mau_duyet('DUYET',%s,%s,%s,%s)",
                                (self.digest, self.f["mv"], token, date(2026, 10, 26))).fetchone()[0]
        self.assertEqual(result["ket_qua"]["trang_thai"], "HIEU_LUC")

    def test_typed_doc_chan_muc_day_du_chua_chot_khi_bat(self):
        for actions in (WRITE_ACTIONS, READ_ACTIONS):
            with self.subTest(actions=actions), self.c.transaction(force_rollback=True):
                self.cau_hinh(actions=actions)
                if actions == READ_ACTIONS:
                    for command in COMMANDS:
                        self.loi("MTQ_CHUA_TICK", lambda: self.dich(command))
                for table, key in (("master.crm_mau_phien_ban", "mv"), ("master.crm_bo_chuan_phien_ban", "cv")):
                    for state in ("DRAFT", "HIEU_LUC"):
                        # Giữ CHECK hiệu lực; không vô hiệu trigger.
                        self.c.execute("UPDATE " + table + " SET trang_thai=%s,valid_from=%s WHERE id=%s",
                                       (state, date(2026, 10, 26) if state == "HIEU_LUC" else None, self.f[key]))
                        self.assertEqual(self.c.execute("SELECT master.crm_g_viec_doc_duoc(%s,%s,%s)",
                                                        (table, self.f[key], self.pn)).fetchone()[0], False)
                    self.assertFalse(self.c.execute("SELECT master.crm_g_viec_doc_duoc(%s,%s,%s)",
                                                    (table, self.f[key], self.pn2)).fetchone()[0])
                    self.assertFalse(self.c.execute("SELECT master.crm_g_viec_doc_duoc(%s,%s,%s)",
                                                    (table, uuid.uuid4(), self.pn)).fetchone()[0])

    def test_g7_doc_hieu_luc_dung_du_an_va_khong_dua_vao_vai_cu(self):
        self.cau_hinh(actions=READ_ACTIONS, scope="DU_AN", key=self.f["da"])
        self.c.execute("UPDATE master.crm_bo_chuan_phien_ban SET trang_thai='HIEU_LUC',valid_from=%s WHERE id=%s",
                       (date(2026, 10, 26), self.f["cv"]))
        result = self.c.execute("SELECT master.crm_g_chuan_doc(%s,'MTQ_TEST',%s)", (self.f["da"], date(2026, 10, 26))).fetchone()[0]
        self.assertEqual(result["version"]["id"], str(self.f["cv"]))
        other = self.insert("master.du_an", phap_nhan_id=self.pn, ma_junsky=uuid.uuid4().hex, ten="Ngoài phạm vi G7")
        self.loi("CRM_G_KHONG_THAY", lambda: self.c.execute("SELECT master.crm_g_chuan_doc(%s,'MTQ_TEST',%s)", (other, date(2026, 10, 26))))
        self.assertFalse(self.c.execute("SELECT master.crm_g_chuan_doc_duoc(%s)", (self.pn,)).fetchone()[0])

    def test_chu_ky_cu_thieu_locator_chan_khi_bat(self):
        self.cau_hinh(actions=WRITE_ACTIONS | READ_ACTIONS)
        self.assertEqual(self.c.execute("SELECT master.crm_g_mau_doc(%s,%s)",
                                        (self.pn, self.f["lh"])).fetchone()[0], "HIEU_LUC")
        self.assertFalse(self.c.execute("SELECT master.crm_g_chuan_xem(%s,true)", (self.f["da"],)).fetchone()[0])
        for command in COMMANDS:
            value = self.c.execute("SELECT master.crm_g_duoc(%s,%s,%s)", (command, self.pn, self.f["lh"])).fetchone()[0]
            self.assertEqual(value, command == "CRM_MAU_TAI")
        self.assertIsNone(self.c.execute("SELECT master.crm_g_mau_doc(%s,%s)", (self.pn2, self.f["lh"])).fetchone()[0])
        self.assertIsNone(self.c.execute("SELECT master.crm_g_mau_doc(%s,%s)", (self.pn, uuid.uuid4())).fetchone()[0])

    def test_cu_truoc_sau_giong_nhau_tren_cac_vai(self):
        actors = [self.nguoi(v) for v in ("XEM", "BAN_HANG", "KE_TOAN", "KE_TOAN_TRUONG", "CFO")]
        for who in actors:
            self.legacy(who)

        def capture():
            results = []
            for who in actors:
                self.actor(who)
                results.append(self.c.execute("SELECT master.crm_g_mau_doc(%s,%s),master.crm_g_chuan_doc_duoc(%s)",
                                              (self.pn, self.f["lh"], self.pn)).fetchone())
                for command in COMMANDS:
                    try:
                        with self.c.transaction():
                            results.append(self.dich(command))
                    except psycopg.Error as exc:
                        results.append((exc.sqlstate, exc.diag.message_primary))
                    try:
                        with self.c.transaction():
                            self.dich(command, target=uuid.UUID(int=0))
                    except psycopg.Error as exc:
                        results.append((exc.sqlstate, exc.diag.message_primary))
            return results

        for name in AFTER.keys() & BEFORE.keys():
            self.c.execute(BEFORE[name])
        before = capture()
        for name in AFTER.keys() & BEFORE.keys():
            self.c.execute(AFTER[name])
        self.assertEqual(capture(), before)

    def test_acl_rls_khong_doi_va_app_khong_goi_lenh_chu_bang(self):
        self.assertEqual(self.acl_before, self.acl_after)
        self.assertEqual(self.rls_before, self.rls_after)
        self.actor(self.user)
        self.c.execute("SET LOCAL ROLE app_web")
        self.loi("permission denied", lambda: self.c.execute(
            "SELECT master.crm_g_chuan_lap('LAP',%s,%s,'TEST','[]'::jsonb)", (self.digest, self.f["da"])))
        self.loi("permission denied", lambda: self.c.execute("SELECT master.crm_g_chuan_xem(%s,false)", (self.f["da"],)))
        self.c.execute("RESET ROLE")


B_POSITION = next(i for i, m in enumerate(PM.PG_MIGRATIONS) if m[:len(MTQ_CRM_B_SQL)] == MTQ_CRM_B_SQL)
B_MIGRATION = PM.PG_MIGRATIONS[B_POSITION]
B_BEFORE = definitions(PM.PG_MIGRATIONS[:B_POSITION])
B_AFTER = definitions((B_MIGRATION,))
B_COMMANDS = {
    "CRM_BAO_GIA_TAO": ("lh", "CRM:G2_BAO_GIA:LAP"),
    "CRM_BAO_GIA_LUU": ("bg", "CRM:G2_BAO_GIA:SUA"),
    "CRM_BAO_GIA_HUY": ("bg", "CRM:G2_BAO_GIA:HUY"),
    "CRM_BAO_GIA_IN": ("bg", "CRM:G2_BAO_GIA:XEM"),
    "CRM_BAO_GIA_CHUYEN": ("sbg", "CRM:G3_G4_SOAN_KY:LAP"),
    "CRM_SOAN_LUU": ("s", "CRM:G3_G4_SOAN_KY:SUA"),
    "CRM_SOAN_XUAT": ("s", "CRM:G3_G4_SOAN_KY:XEM"),
}
B_ACTIONS = {action for _, action in B_COMMANDS.values()} | {"CRM:G1_MAU:XEM"}
B_COMMAND_FUNCTIONS = {
    "master.crm_gk_tra", "master.crm_gk_dat_lan", "master.crm_gk_bao_gia_luu",
    "master.crm_gk_bao_gia_huy", "master.crm_gk_chuyen", "master.crm_gk_soan_luu",
    "master.crm_gk_xuat_ghi",
}
B_READ_FUNCTIONS = {
    "master.crm_gk_ghim_mau", "master.crm_gk_mau_ghim",
    "master.crm_gk_mau_hieu_luc", "master.crm_gk_tep",
}


class MtqCrmBGSqlTinh(unittest.TestCase):
    def test_append_khong_doi_migration_truoc(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# MTQ-4b2a — CD-012:"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, "exec"), old)
        self.assertEqual(PM.PG_MIGRATIONS[:B_POSITION], old["PG_MIGRATIONS"])
        self.assertEqual(B_MIGRATION[:len(MTQ_CRM_B_SQL)], MTQ_CRM_B_SQL)
        self.assertEqual(sum(m is B_MIGRATION for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_pham_vi_chi_g2_g3_khong_doi_helper_dung_chung_g4_ty_gia(self):
        self.assertEqual(set(B_AFTER), B_COMMAND_FUNCTIONS | B_READ_FUNCTIONS | {
            "master.crm_gk_dich", "master.crm_gk_ghim_quyen", "master.crm_gk_xem"})
        sql = "\n".join(B_MIGRATION)
        self.assertNotRegex(sql, r"\b(?:ALTER TABLE|CREATE POLICY|ALTER POLICY|DROP |GRANT )")
        self.assertNotRegex(sql, r"CREATE(?: OR REPLACE)? FUNCTION master\.(?:ktt_|crm_ky_|crm_kiem_|crm_g5_)")
        self.assertNotIn("CRM:TY_GIA", sql)
        self.assertNotIn("CRM:BAN_KY", sql)
        self.assertNotIn("EXCEPTION WHEN", sql)

    def test_giu_than_lenh_cas_hash_bat_bien_va_guard_chu_bang(self):
        for name in B_COMMAND_FUNCTIONS:
            old, new = B_BEFORE[name], B_AFTER[name]
            self.assertEqual(old.count("PERFORM master.crm_g_ghim_quyen("), 1, name)
            self.assertEqual(new, old.replace("PERFORM master.crm_g_ghim_quyen(",
                                              "PERFORM master.crm_gk_ghim_quyen(", 1), name)
            self.assertIn("master.la_chu_bang(", new, name)
            self.assertLess(new.index("master.crm_gk_dich("), new.index("master.crm_g_bn_tra("), name)

    def test_cu_guard_giu_nguyen_kiem_quyen_va_ma_loi(self):
        old = B_BEFORE["master.crm_gk_dich"]
        # Từ kiểm quyền cũ đến cuối hàm phải nguyên văn, có cả kiểm kép lúc chuyển.
        start = "            IF pn IS NULL OR NOT master.ktt_duoc(pn, 'CRM') THEN"
        self.assertEqual(B_AFTER["master.crm_gk_dich"].split(start, 1)[1], old.split(start, 1)[1])
        self.assertIn("RETURN;", B_AFTER["master.crm_gk_dich"].split(start, 1)[0])

    def test_chu_ky_security_definer_acl_va_volatility(self):
        for name in B_AFTER.keys() & B_BEFORE.keys():
            old, new = B_BEFORE[name], B_AFTER[name]
            self.assertEqual(new.split("\n", 1)[0], old.split("\n", 1)[0], name)
            self.assertEqual("SECURITY DEFINER" in new, "SECURITY DEFINER" in old, name)
            self.assertEqual(re.search(r"SET search_path = ([^\n]+)", new).group(1),
                             re.search(r"SET search_path = ([^\n]+)", old).group(1), name)
        for name in B_READ_FUNCTIONS | {"master.crm_gk_dich", "master.crm_gk_xem"}:
            self.assertNotIn("LANGUAGE plpgsql STABLE", B_AFTER[name], name)
            self.assertIn("pg_advisory_xact_lock_shared(742601, 1)", B_AFTER[name], name)
        self.assertIn("REVOKE ALL ON FUNCTION master.crm_gk_xem(text, uuid, uuid) FROM PUBLIC", B_MIGRATION)
        self.assertIn("REVOKE ALL ON FUNCTION master.crm_gk_ghim_quyen(uuid) FROM PUBLIC", B_MIGRATION)


@unittest.skipUnless(DSN and psycopg is not None, "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class MtqCrmBGSqlPostgres(unittest.TestCase):
    nguoi = nen.MtqPostgres.nguoi
    actor = nen.MtqPostgres.actor
    ghi = nen.MtqPostgres.ghi
    nhap = nen.MtqPostgres.nhap
    sua_nhap = nen.MtqPostgres.sua_nhap
    san_sang = nen.MtqPostgres.san_sang
    loi = nen.MtqPostgres.loi
    insert = MtqCrmSqlPostgres.insert
    insert_dong = MtqCrmSqlPostgres.insert_dong
    setUp = MtqCrmSqlPostgres.setUp
    policies = classmethod(MtqCrmSqlPostgres.policies.__func__)

    @classmethod
    def metadata(cls):
        return cls.c.execute(
            "SELECT oid::regprocedure::text,proowner,proacl::text,prosecdef,proconfig "
            "FROM pg_proc WHERE pronamespace='master'::regnamespace "
            "AND proname LIKE 'crm_gk_%' AND proname NOT IN ('crm_gk_xem','crm_gk_ghim_quyen') ORDER BY oid"
        ).fetchall()

    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = "kho_test_mtq_crm_g2g3_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as c:
            c.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_web') "
                      "THEN CREATE ROLE app_web NOLOGIN; END IF; END $$")
            c.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.c = psycopg.connect(make_conninfo(DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c, target=B_POSITION)
        cls.acl_before, cls.rls_before = cls.metadata(), cls.policies()
        postgres.migrate(cls.c, target=B_POSITION + 1)
        cls.acl_after, cls.rls_after = cls.metadata(), cls.policies()
        postgres.migrate(cls.c)

    def fixture(self, pn):
        from psycopg.types.json import Jsonb

        f = MtqCrmSqlPostgres.fixture(self, pn)
        sha, login = f["sha"], self.admin[1]
        # Đã đối chiếu hop_dong_kiem, crm_*_kiem/bat_bien/ky_khoa và FK thật.
        # Đối tác gắn PN và mapping hiện hành; không tắt bất kỳ trigger nào.
        kh = self.insert("master.doi_tac", phap_nhan_id=pn, ten_phap_ly="Khách G2/G3 tổng hợp", ten_chuan_hoa=uuid.uuid4().hex)
        self.insert("master.doi_tac_ma_junsky", phap_nhan_id=pn, doi_tac_id=kh,
                    object_id_junsky="MTQ_TEST_" + uuid.uuid4().hex, ten_junsky="Khách G2/G3 tổng hợp")
        ax = self.insert("master.crm_mau_anh_xa", phap_nhan_id=pn, phien_ban_id=f["mv"], revision=1,
                         ban_do=Jsonb([]), ban_do_sha256=sha, danh_muc_digest=f["digest"], canh_bao=Jsonb([]),
                         so_chua_anh_xa=0, so_sai_kieu=0, tao_boi=login)
        kt = self.insert("master.crm_mau_kiem_tra", phap_nhan_id=pn, phien_ban_id=f["mv"], anh_xa_id=ax,
                         raw_sha256=sha, facts_sha256=sha, danh_muc_digest=f["digest"], ban_do_sha256=sha,
                         ket_qua="DAT", kiem_boi=login)
        self.c.execute("UPDATE master.crm_mau_phien_ban SET trang_thai='HIEU_LUC',valid_from=%s,"
                       "anh_xa_hien_hanh=%s,kiem_hien_hanh=%s WHERE id=%s", (date(2026, 1, 1), ax, kt, f["mv"]))
        self.c.execute("UPDATE master.loai_hinh_doanh_thu SET cau_hinh=%s WHERE id=%s",
                       (Jsonb({"loai_hop_dong": "THUE_DAT"}), f["lh"]))
        # Hai báo giá: một NHAP để test lệnh ghi, một nguồn đã chuyển của bản soạn.
        for key, number in (("bg", "00001"), ("sbg", "00002")):
            f[key] = self.insert("master.crm_bao_gia", phap_nhan_id=pn, loai_hinh_id=f["lh"],
                                 so_bao_gia="BG-2026-" + number, ngay=date(2026, 10, 26), tao_boi=login,
                                 trang_thai="NHAP", revision_hien_hanh=1)
            self.insert("master.crm_bao_gia_rev", phap_nhan_id=pn, bao_gia_id=f[key], revision=1,
                        du_an_id=f["da"], doi_tac_id=kh, du_lieu=Jsonb({}), du_lieu_sha256=sha,
                        tinh=Jsonb({}), tao_boi=login)
        hd = self.insert("master.hop_dong", phap_nhan_id=pn, du_an_id=f["da"], loai_hinh_dt_id=f["lh"],
                         doi_tac_id=kh, loai="THUE_DAT", ma_noi_bo=uuid.uuid4().hex, so_hop_dong=uuid.uuid4().hex,
                         trang_thai="SOAN_THAO", crm_giao_ket="SOAN_THAO")
        f["s"] = self.insert("master.crm_hd_soan", phap_nhan_id=pn, hop_dong_id=hd, bao_gia_id=f["sbg"],
                             bao_gia_revision=1, loai_hinh_id=f["lh"], revision_hien_hanh=1,
                             trang_thai="SOAN_THAO", tao_boi=login)
        self.insert("master.crm_hd_soan_rev", phap_nhan_id=pn, soan_id=f["s"], revision=1, nguon="MAU",
                    mau_phien_ban_id=f["mv"], anh_xa_id=ax, kiem_id=kt, raw_sha256=sha, byte_length=1,
                    facts_sha256=sha, ban_do_sha256=sha, danh_muc_ref="MTQ_TEST", danh_muc_rev=1,
                    danh_muc_digest=f["digest"], profile_phien_ban=1, profile_sha256=sha,
                    renderer="MTQ_TEST", du_lieu=Jsonb({"bao_gia": {"du_an_id": str(f["da"]),
                        "khach": {"doi_tac_id": str(kh)}}}), du_lieu_sha256=sha, tao_boi=login)
        self.c.execute("UPDATE master.crm_bao_gia SET trang_thai='DA_CHUYEN',hop_dong_id=%s WHERE id=%s", (hd, f["sbg"]))
        for key, kind, target in (("xb", "BAO_GIA", "bao_gia_id"), ("xs", "HOP_DONG", "soan_id")):
            f[key] = self.insert("master.crm_gk_xuat", phap_nhan_id=pn, loai=kind,
                                 **{target: f["bg" if key == "xb" else "s"]}, revision=1,
                                 input_sha256=sha, docx_sha256=sha, docx_len=1, trang_thai="PDF_CHUA_SAN_SANG",
                                 engine="MTQ_TEST", kiem_pdf=Jsonb({}), tao_boi=login)
        f.update(kh=kh, hd=hd)
        return f

    def cau_hinh(self, actions=B_ACTIONS, scope="PHAP_NHAN", key=None):
        grants = MtqCrmSqlPostgres.cau_hinh(self, actions, scope, key)
        if scope == "PHAP_NHAN" and any(":G3_G4_SOAN_KY:" in action for action in actions):
            self.actor(self.admin)
            for grant in grants:
                self.ghi("PHAM_VI", {"gan_vai_id": grant["id"], "phap_nhan_id": str(self.pn),
                    "loai": "DU_AN", "khoa": str(self.f["da"]), "quan_he": {"doi_tac_id": str(self.f["kh"])}})
            self.actor(self.user)
        return grants

    def legacy(self, who=None, pn=None):
        self.c.execute("INSERT INTO master.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,ARRAY['CRM'])",
                       ((who or self.user)[0], pn or self.pn))

    def dich(self, command, fixture=None, target=None):
        f = fixture or self.f
        return self.c.execute("SELECT * FROM master.crm_gk_dich(%s,%s)",
                              (command, target or f[B_COMMANDS[command][0]])).fetchone()

    def tra(self, command, fixture=None):
        f = fixture or self.f
        return self.c.execute("SELECT master.crm_gk_tra(%s,'MTQ_REPLAY',%s,%s)",
                              (command, f[B_COMMANDS[command][0]], self.digest)).fetchone()[0]

    def test_tung_lenh_tick_bat_khong_can_vai_cu_hoac_tick_xem_kem(self):
        for action in sorted({a for _, a in B_COMMANDS.values()}):
            with self.subTest(action=action), self.c.transaction(force_rollback=True):
                self.cau_hinh(actions={action})
                for command, (_, expected) in B_COMMANDS.items():
                    if action == expected:
                        self.assertEqual(self.dich(command)[0], self.pn)
                    else:
                        self.loi("MTQ_CHUA_TICK", lambda: self.dich(command))

    def test_tick_tat_chan_vai_cu_va_assignment_cu(self):
        self.user = self.nguoi("BAN_HANG")
        self.legacy()
        for group in ("CRM_BAO_GIA", "CRM_SOAN"):
            self.insert("master.phan_cong_hanh_dong", nguoi_dung_id=self.user[0], phap_nhan_id=self.pn,
                        module="CRM", hanh_dong=group, cap_boi=self.admin[1])
        self.cau_hinh(actions=())
        for command in B_COMMANDS:
            self.loi("MTQ_CHUA_TICK", lambda: self.dich(command))
        self.loi("CRM_G_KHONG_THAY", lambda: self.c.execute("SELECT master.crm_gk_tep(%s)", (self.f["xb"],)))

    def test_scope_sai_thieu_id_va_helper_khong_nhan_pn_gia(self):
        other = self.insert("master.du_an", phap_nhan_id=self.pn, ma_junsky=uuid.uuid4().hex, ten="Ngoài scope G2/G3")
        # B3 không cấp phạm vi dự án ký khi chưa có bản soạn/khách để ghim.
        # Giữ ca scope ngoài đích cho mọi lệnh; scope này chỉ có các ô G1/G2.
        self.cau_hinh(actions={a for a in B_ACTIONS if ':G3_G4_' not in a}, scope="DU_AN", key=other)
        for command in B_COMMANDS:
            self.loi("MTQ_PHAM_VI", lambda: self.dich(command))
            self.loi("CRM_G_KHONG_THAY", lambda: self.dich(command, target=uuid.uuid4()))
        for table, key in (("master.crm_bao_gia", "bg"), ("master.crm_hd_soan", "s"),
                           ("master.crm_gk_xuat", "xb"), ("master.crm_mau_phien_ban", "mv")):
            self.assertFalse(self.c.execute("SELECT master.crm_gk_xem(%s,%s,%s)", (table, self.f[key], self.pn)).fetchone()[0])
            self.assertFalse(self.c.execute("SELECT master.crm_gk_xem(%s,%s,%s)", (table, self.f[key], self.pn2)).fetchone()[0])
        self.assertFalse(self.c.execute("SELECT master.crm_gk_xem('master.doi_tac',%s,%s)", (self.f["kh"], self.pn)).fetchone()[0])

    def test_thieu_scope_chan_tat_ca_lenh_ke_ca_nguoi_co_tick(self):
        self.cau_hinh(scope=None)
        for command in B_COMMANDS:
            self.loi("MTQ_PHAM_VI", lambda: self.dich(command))

    def test_xem_tach_bao_gia_soan_mau_va_ban_xuat(self):
        for action in ("CRM:G2_BAO_GIA:XEM", "CRM:G3_G4_SOAN_KY:XEM", "CRM:G1_MAU:XEM"):
            with self.subTest(action=action), self.c.transaction(force_rollback=True):
                self.cau_hinh(actions={action})
                for table, key, allowed in (
                    ("master.crm_bao_gia", "bg", action == "CRM:G2_BAO_GIA:XEM"),
                    ("master.crm_hd_soan", "s", action == "CRM:G3_G4_SOAN_KY:XEM"),
                    ("master.crm_gk_xuat", "xb", action == "CRM:G2_BAO_GIA:XEM"),
                    ("master.crm_gk_xuat", "xs", action == "CRM:G3_G4_SOAN_KY:XEM"),
                    ("master.crm_mau_phien_ban", "mv", action == "CRM:G1_MAU:XEM")):
                    self.assertEqual(self.c.execute("SELECT master.crm_gk_xem(%s,%s,%s)",
                                                    (table, self.f[key], self.pn)).fetchone()[0], allowed)
                picker = self.c.execute("SELECT master.crm_gk_mau_hieu_luc(%s)", (self.f["lh"],)).fetchone()[0]
                self.assertEqual(bool(picker), action == "CRM:G1_MAU:XEM")
                for key, expected in (("xb", "CRM:G2_BAO_GIA:XEM"), ("xs", "CRM:G3_G4_SOAN_KY:XEM")):
                    if action == expected:
                        self.assertEqual(self.c.execute("SELECT master.crm_gk_tep(%s)", (self.f[key],)).fetchone()[0]["docx_sha256"], self.f["sha"])
                    else:
                        self.loi("CRM_G_KHONG_THAY", lambda: self.c.execute("SELECT master.crm_gk_tep(%s)", (self.f[key],)))

    def test_mau_lich_su_ghim_theo_soan_khong_mo_picker(self):
        self.c.execute("UPDATE master.crm_mau_phien_ban SET valid_to=%s WHERE id=%s", (date(2026, 2, 1), self.f["mv"]))
        self.cau_hinh(actions={"CRM:G3_G4_SOAN_KY:XEM"})
        pin = self.c.execute("SELECT master.crm_gk_mau_ghim(%s,1)", (self.f["s"],)).fetchone()[0]
        self.assertEqual(pin["mau_phien_ban_id"], str(self.f["mv"]))
        self.assertEqual(self.c.execute("SELECT master.crm_gk_mau_hieu_luc(%s)", (self.f["lh"],)).fetchone()[0], [])
        self.loi("CRM_G_KHONG_THAY", lambda: self.c.execute("SELECT master.crm_gk_ghim_mau(%s,%s,%s)",
                                                           (self.pn, self.f["lh"], self.f["mv"])))
        self.loi("CRM_G_KHONG_THAY", lambda: self.c.execute("SELECT master.crm_gk_mau_ghim(%s,99)", (self.f["s"],)))

    def test_chon_mau_moi_can_g1_xem_va_giu_hieu_luc_pn_loai(self):
        self.cau_hinh(actions={"CRM:G1_MAU:XEM"})
        pin = self.c.execute("SELECT master.crm_gk_ghim_mau(%s,%s,%s)", (self.pn, self.f["lh"], self.f["mv"])).fetchone()[0]
        self.assertEqual(pin["mau_phien_ban_id"], str(self.f["mv"]))
        self.loi("CRM_G_KHONG_THAY", lambda: self.c.execute("SELECT master.crm_gk_ghim_mau(%s,%s,%s)",
                                                           (self.pn2, self.f["lh"], self.f["mv"])))
        self.loi("CRM_G_KHONG_THAY", lambda: self.c.execute("SELECT master.crm_gk_ghim_mau(NULL,%s,%s)",
                                                           (self.f["lh"], self.f["mv"])))
        self.loi("CRM_GK_MAU_KHONG_HIEU_LUC", lambda: self.c.execute("SELECT master.crm_gk_ghim_mau(%s,NULL,%s)",
                                                                 (self.pn, self.f["mv"])))
        self.c.execute("UPDATE master.crm_mau_phien_ban SET valid_to=%s WHERE id=%s", (date(2026, 2, 1), self.f["mv"]))
        self.loi("CRM_GK_MAU_KHONG_HIEU_LUC", lambda: self.c.execute("SELECT master.crm_gk_ghim_mau(%s,%s,%s)",
                                                                 (self.pn, self.f["lh"], self.f["mv"])))

    def test_thu_hoi_truoc_replay_dat_lan_cong_bo_va_tra_hash(self):
        grants = self.cau_hinh()
        for command, key in (("CRM_BAO_GIA_IN", "bg"), ("CRM_SOAN_XUAT", "s")):
            self.assertTrue(self.c.execute("SELECT master.crm_gk_dat_lan(%s,'PHA_A',%s,%s,1,%s)",
                                           (command, self.f[key], self.digest, self.f["sha"])).fetchone()[0]["moi"])
        for command, (key, _) in B_COMMANDS.items():
            self.c.execute("SELECT master.crm_g_bn_ghi(%s,%s,'MTQ_REPLAY',%s,'{}'::jsonb)", (self.pn, command, self.digest))
            self.assertTrue(self.tra(command)["lap_lai"])
        self.actor(self.admin)
        self.ghi("THU_HOI_VAI", {"id": grants[0]["id"]}, grants[0]["revision"])
        self.actor(self.user)
        for command in B_COMMANDS:
            self.loi("MTQ_GAN_VAI", lambda: self.tra(command))
        for command, key in (("CRM_BAO_GIA_IN", "bg"), ("CRM_SOAN_XUAT", "s")):
            self.loi("MTQ_GAN_VAI", lambda: self.c.execute("SELECT master.crm_gk_dat_lan(%s,'MTQ_REPLAY',%s,%s,1,%s)",
                                                          (command, self.f[key], self.digest, self.f["sha"])))
            self.loi("MTQ_GAN_VAI", lambda: self.c.execute(
                "SELECT master.crm_gk_xuat_ghi('PHA_A',%s,%s,%s,1,%s,%s,1,NULL,NULL,'PDF_CHUA_SAN_SANG','MTQ_TEST',NULL,'{}'::jsonb)",
                (self.digest, command, self.f[key], self.f["sha"], self.f["sha"])))
        for key in ("xb", "xs"):
            self.loi("CRM_G_KHONG_THAY", lambda: self.c.execute("SELECT master.crm_gk_tep(%s)", (self.f[key],)))
        self.assertEqual(self.c.execute("SELECT count(*) FROM master.crm_gk_lan WHERE trang_thai='DANG_RENDER'").fetchone()[0], 2)
        self.assertEqual(self.c.execute("SELECT count(*) FROM master.crm_gk_xuat").fetchone()[0], 2)

    def test_chuyen_chi_can_g3_lap_va_g1_xem_khong_them_g2_sua(self):
        self.cau_hinh(actions={"CRM:G3_G4_SOAN_KY:LAP", "CRM:G1_MAU:XEM"})
        result = self.c.execute("SELECT master.crm_gk_chuyen('CHUYEN',%s,%s,1,%s,'{}'::jsonb,'MTQ_TEST')",
                                (self.digest, self.f["bg"], self.f["mv"])).fetchone()[0]["ket_qua"]
        self.assertEqual(result["trang_thai"], "SOAN_THAO")
        self.loi("MTQ_CHUA_TICK", lambda: self.dich("CRM_BAO_GIA_LUU"))

    def test_lenh_ghi_truc_tiep_cas_va_bat_bien_khong_can_xem(self):
        self.cau_hinh(actions={"CRM:G2_BAO_GIA:SUA", "CRM:G2_BAO_GIA:HUY", "CRM:G3_G4_SOAN_KY:SUA"})
        args = (self.digest, self.f["bg"], self.f["lh"], self.f["da"], self.f["kh"])
        result = self.c.execute("SELECT master.crm_gk_bao_gia_luu('LUU',%s,%s,%s,1,%s,%s,'{}'::jsonb,'{}'::jsonb,NULL,NULL,NULL,NULL)", args).fetchone()[0]
        self.assertEqual(result["ket_qua"]["revision"], 2)
        self.loi("CRM_GK_REVISION_CU", lambda: self.c.execute("SELECT master.crm_gk_bao_gia_huy('HUY_CU',%s,%s,1,'Test CAS')", (self.digest, self.f["bg"])))
        self.loi("CRM_GK_REVISION_CU", lambda: self.c.execute("SELECT master.crm_gk_soan_luu('SOAN_CU',%s,%s,99,'{}'::jsonb,NULL,NULL,'MTQ_TEST')", (self.digest, self.f["s"])))
        self.loi("CRM_G_BAT_BIEN", lambda: self.c.execute("UPDATE master.crm_bao_gia_rev SET tinh='{}'::jsonb WHERE bao_gia_id=%s", (self.f["bg"],)))
        result = self.c.execute("SELECT master.crm_gk_soan_luu('SOAN',%s,%s,1,'{}'::jsonb,NULL,NULL,'MTQ_TEST')", (self.digest, self.f["s"])).fetchone()[0]
        self.assertEqual(result["ket_qua"]["revision"], 2)

    def test_dat_lan_cong_bo_dung_tick_xem_giu_revision_va_hash(self):
        self.cau_hinh(actions={"CRM:G2_BAO_GIA:XEM", "CRM:G3_G4_SOAN_KY:XEM"})
        for command, key in (("CRM_BAO_GIA_IN", "bg"), ("CRM_SOAN_XUAT", "s")):
            with self.subTest(command=command):
                self.loi("CRM_GK_REVISION_CU", lambda: self.c.execute("SELECT master.crm_gk_dat_lan(%s,'CU',%s,%s,99,%s)",
                                                                    (command, self.f[key], self.digest, self.f["sha"])))
                made = self.c.execute("SELECT master.crm_gk_dat_lan(%s,'XUAT',%s,%s,1,%s)",
                                      (command, self.f[key], self.digest, self.f["sha"])).fetchone()[0]
                self.assertTrue(made["moi"])
                result = self.c.execute(
                    "SELECT master.crm_gk_xuat_ghi('XUAT',%s,%s,%s,1,%s,%s,1,NULL,NULL,'PDF_CHUA_SAN_SANG','MTQ_TEST',NULL,'{}'::jsonb)",
                    (self.digest, command, self.f[key], self.f["sha"], self.f["sha"])).fetchone()[0]["ket_qua"]
                self.assertEqual(result["docx_sha256"], self.f["sha"])
                self.assertEqual(self.c.execute("SELECT master.crm_gk_tep(%s)", (result["xuat_id"],)).fetchone()[0]["docx_len"], 1)

    def test_cu_oracle_bat_a_khong_doi_pn_b_tat_ca_cho_chan_va_ma(self):
        f2 = self.fixture(self.pn2)
        allowed = self.nguoi("BAN_HANG")
        self.legacy(allowed, self.pn2)
        actors = (allowed, self.user, self.nguoi("CFO"))
        self.legacy(actors[2], self.pn2)

        def capture():
            result = {}
            for who in actors:
                self.actor(who)
                calls = {command: ("SELECT * FROM master.crm_gk_dich(%s,%s)", (command, f2[key]))
                         for command, (key, _) in B_COMMANDS.items()}
                calls.update({
                    "picker": ("SELECT master.crm_gk_mau_hieu_luc(%s)", (f2["lh"],)),
                    "pin": ("SELECT master.crm_gk_ghim_mau(%s,%s,%s)", (self.pn2, f2["lh"], f2["mv"])),
                    "ghim": ("SELECT master.crm_gk_mau_ghim(%s,1)", (f2["s"],)),
                    "xb": ("SELECT master.crm_gk_tep(%s)", (f2["xb"],)),
                    "xs": ("SELECT master.crm_gk_tep(%s)", (f2["xs"],)),
                    "missing": ("SELECT * FROM master.crm_gk_dich('CRM_SOAN_LUU',%s)", (uuid.UUID(int=0),)),
                })
                for name, (sql, args) in calls.items():
                    try:
                        with self.c.transaction():
                            row = ("CHO", self.c.execute(sql, args).fetchone())
                    except psycopg.Error as exc:
                        self.assertEqual(exc.sqlstate, "P0001")
                        self.assertRegex(exc.diag.message_primary, r"^CRM_G_(?:KHONG_THAY|KHONG_CO_QUYEN):")
                        row = ("CHAN", exc.sqlstate, exc.diag.message_primary)
                    result[who[0], name] = row
            return result

        with self.c.transaction(force_rollback=True):
            for name in B_AFTER.keys() & B_BEFORE.keys():
                self.c.execute(B_BEFORE[name])
            oracle = capture()
        self.assertEqual({r[0] for r in oracle.values()}, {"CHO", "CHAN"})
        self.assertEqual(capture(), oracle)
        self.cau_hinh()
        self.assertFalse(self.c.execute("SELECT EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id=%s AND bat)", (self.pn2,)).fetchone()[0])
        self.assertEqual(capture(), oracle)

    def test_acl_rls_chu_bang_giu_nguyen(self):
        self.assertEqual(self.acl_before, self.acl_after)
        self.assertEqual(self.rls_before, self.rls_after)
        self.cau_hinh()
        self.c.execute("SET LOCAL ROLE app_web")
        for sql, args in (
            ("SELECT master.crm_gk_dich('CRM_SOAN_LUU',%s)", (self.f["s"],)),
            ("SELECT master.crm_gk_xem('master.crm_hd_soan',%s,%s)", (self.f["s"], self.pn)),
            ("SELECT master.crm_gk_ghim_quyen(%s)", (self.pn,)),
            ("SELECT master.crm_gk_tep(%s)", (self.f["xs"],))):
            self.loi("permission denied", lambda: self.c.execute(sql, args))
        self.c.execute("RESET ROLE")


C_POSITION = next(i for i, m in enumerate(PM.PG_MIGRATIONS) if m[:len(MTQ_CRM_C_SQL)] == MTQ_CRM_C_SQL)
C_MIGRATION = PM.PG_MIGRATIONS[C_POSITION]
C_BEFORE = definitions(PM.PG_MIGRATIONS[:C_POSITION])
C_AFTER = definitions((C_MIGRATION,))
C_LAP = "CRM:G3_G4_SOAN_KY:LAP"
C_XEM = "CRM:G3_G4_SOAN_KY:XEM"
C_BAN = "CRM:BAN_KY:XEM"
C_ACTIONS = {C_LAP, C_XEM, C_BAN}


class MtqCrmKySqlTinh(unittest.TestCase):
    def test_append_khong_doi_migration_cu(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# MTQ-4b2b — CD-012:"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, "exec"), old)
        self.assertEqual(PM.PG_MIGRATIONS[:C_POSITION], old["PG_MIGRATIONS"])
        self.assertEqual(C_MIGRATION[:len(MTQ_CRM_C_SQL)], MTQ_CRM_C_SQL)
        self.assertEqual(sum(m is C_MIGRATION for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_validator_dua_tren_than_moi_nhat_giu_nguyen_nguon(self):
        old, new = C_BEFORE["master.mtq_kiem_ghi"], C_AFTER["master.mtq_kiem_ghi"]
        start = "                IF TG_OP = 'INSERT' AND NEW.loai IN ('HOP_DONG','DU_AN') THEN"
        end = "            ELSIF TG_TABLE_NAME = 'mtq_admin' AND TG_OP = 'UPDATE' THEN"
        self.assertEqual(new.split(start)[0] + end + new.split(end)[1], old)
        block = new.split(start, 1)[1].split(end, 1)[0]
        self.assertNotIn("master.mtq_dong", block)
        self.assertNotIn("master.mtq_o", block)
        self.assertIn("master.crm_ky_cap_quan_he(NEW.loai, NEW.khoa, NEW.phap_nhan_id)", block)
        self.assertIn("ELSIF NEW.loai = 'NGUON' THEN", new)
        self.assertIn("NEW.quan_he := ghim", new)
        self.assertIn("NEW.quan_he <> '{}'::jsonb AND NEW.quan_he IS DISTINCT FROM ghim", new)
        self.assertNotIn("UPDATE master.crm_ky_pham_vi", "\n".join(C_MIGRATION))
        self.assertNotIn("INSERT INTO master.mtq_pham_vi", "\n".join(C_MIGRATION))

    def test_cu_giu_bieu_thuc_va_ma_loi(self):
        old, new = C_BEFORE["master.crm_ky_dich"], C_AFTER["master.crm_ky_dich"]
        start = "            IF s.id IS NULL OR NOT master.ktt_duoc"
        self.assertEqual(new.split(start)[1], old.split(start)[1])
        for name in ("master.crm_ky_pham_vi_hd", "master.crm_ky_doc_duoc"):
            expression = C_BEFORE[name].split("AS $$", 1)[1].split("$$", 1)[0].strip().removeprefix("SELECT ")
            self.assertIn(" ".join(expression.split()), " ".join(C_AFTER[name].split()))
        for name in ("master.crm_g_dich", "master.crm_gk_dich"):
            old, new = C_BEFORE[name], C_AFTER[name]
            expected = old.replace(
                "RAISE EXCEPTION '%: không có quyền hiện hành cho %', coalesce(q->>'ma', 'MTQ_TU_CHOI'), lenh",
                "RAISE EXCEPTION '%: không có quyền thực hiện thao tác này', coalesce(q->>'ma', 'MTQ_TU_CHOI')", 1)
            if name == "master.crm_gk_dich":
                expected = expected.replace(
                    "q := master.mtq_quyet_dinh_phien(lenh, jsonb_build_object('bang', bang, 'id', p_dich), NULL);",
                    "q := CASE WHEN split_part(lenh, ':', 2) = 'G3_G4_SOAN_KY'\n"
                    "                    THEN master.crm_ky_mtq(lenh, bang, p_dich)\n"
                    "                    ELSE master.mtq_quyet_dinh_phien(lenh, jsonb_build_object('bang', bang, 'id', p_dich), NULL) END;", 1)
            self.assertEqual(new, expected)

    def test_ghim_cu_khong_doc_record_chua_gan(self):
        for name in ("master.crm_ky_tra", "master.crm_ky_ket"):
            stmt = C_AFTER[name]
            guard = stmt.split("IF NOT EXISTS (", 1)[1].split("END IF;", 1)[0]
            self.assertNotRegex(guard, r"\bs\.")
            self.assertIn("master.crm_hd_soan s0", guard)
            self.assertIn("s0.id = p_soan", guard)
            self.assertLess(stmt.index("IF NOT EXISTS ("), stmt.index("SELECT * INTO d"))

    def test_cap_quan_he_khong_buoc_co_soan_va_du_an_khong_tu_chon_khach(self):
        stmt = C_AFTER["master.crm_ky_cap_quan_he"]
        self.assertIn("IF p_loai IS DISTINCT FROM 'HOP_DONG' THEN RETURN '{}'::jsonb", stmt)
        self.assertIn("IF NOT FOUND THEN RETURN '{}'::jsonb", stmt)
        self.assertNotIn("RAISE EXCEPTION", stmt)
        self.assertIn("h.module_chu IS NULL", stmt)
        self.assertIn("h.loai NOT IN ('VAY','MUA')", stmt)
        self.assertIn("r.revision = v.revision_hien_hanh", stmt)
        validator = C_AFTER["master.mtq_kiem_ghi"]
        self.assertIn("NEW.loai = 'DU_AN' AND NEW.quan_he <> '{}'::jsonb", validator)
        self.assertIn("dt.phap_nhan_id = NEW.phap_nhan_id", validator)
        self.assertIn("~ '^[0-9a-f]{64}$'", validator)

    def test_giu_than_ky_revision_digest_va_trigger_lineage(self):
        for name in ("master.crm_ky_tra", "master.crm_ky_ket"):
            old, new = C_BEFORE[name], C_AFTER[name]
            start = "            SELECT * INTO d FROM master.crm_ky_dich(p_soan);"
            self.assertEqual(new.split(start)[1], old.split(start)[1])
            self.assertLess(new.index(start), new.index("master.crm_g_bn_tra("))
            self.assertIn("master.la_chu_bang(", new)
        old, new = C_BEFORE["master.crm_hd_ky_kiem"], C_AFTER["master.crm_hd_ky_kiem"]
        start = "            SELECT * INTO x FROM master.crm_gk_xuat"
        self.assertEqual(new.split(start)[1], old.split(start)[1])
        self.assertIn("master.crm_ky_dich(NEW.soan_id)", new)

    def test_chon_dung_scope_cua_cong_khong_tu_mo_rong(self):
        stmt = C_AFTER["master.crm_ky_mtq"]
        self.assertIn("master.mtq_quyet_dinh_phien(", stmt)
        self.assertIn("id = (q->>'pham_vi_id')::uuid", stmt)
        self.assertIn("pv.loai NOT IN ('HOP_DONG','DU_AN')", stmt)
        self.assertIn("pv.quan_he IS DISTINCT FROM ghim", stmt)
        self.assertIn("pv.quan_he = '{}'::jsonb", stmt)
        self.assertIn("MTQ_PHAM_VI_LECH", stmt)
        self.assertNotIn("ORDER BY", stmt)
        self.assertNotIn("phan_cong_hanh_dong", stmt)
        self.assertNotIn("crm_ky_pham_vi", stmt)
        relation = C_AFTER["master.crm_ky_quan_he"]
        self.assertIn("r.revision = s.revision_hien_hanh", relation)
        self.assertIn("encode(sha256(convert_to(", relation)
        for field in ("soan_id", "du_an_id", "doi_tac_id", "khach_du_thao_sha256"):
            self.assertIn("'" + field + "'", relation)

    def test_doc_metadata_ban_ky_tach_quyen_va_log_truoc_hash(self):
        doc, tep = C_AFTER["master.crm_ky_doc"], C_AFTER["master.crm_ky_tep"]
        self.assertIn("master.crm_ky_mtq('CRM:G3_G4_SOAN_KY:XEM'", doc)
        self.assertIn("master.crm_ky_mtq('CRM:BAN_KY:XEM', 'master.crm_hd_ky'", tep)
        self.assertLess(doc.index("IF NOT doc THEN"), doc.index("INSERT INTO nhat_ky.su_kien"))
        self.assertLess(doc.index("INSERT INTO nhat_ky.su_kien"), doc.index("'pdf_sha256'"))
        self.assertLess(tep.index("master.crm_ky_mtq("), tep.index("INSERT INTO nhat_ky.su_kien"))
        self.assertLess(tep.index("INSERT INTO nhat_ky.su_kien"), tep.index("RETURN jsonb_build_object"))
        current = C_AFTER["master.crm_ky_doc_duoc"].split("RETURN EXISTS", 1)[0]
        self.assertNotIn("crm_ky_pham_vi_duoc", current)

    def test_chu_ky_acl_search_path_va_dollar_quotes(self):
        for name in C_AFTER.keys() & C_BEFORE.keys():
            old, new = C_BEFORE[name], C_AFTER[name]
            header = old.split("\n", 1)[0]
            if name == "master.crm_gk_xem":
                header = header.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)
            self.assertEqual(new.split("\n", 1)[0], header, name)
            self.assertEqual("SECURITY DEFINER" in new, "SECURITY DEFINER" in old, name)
            self.assertEqual(re.search(r"SET search_path = ([^\n]+?) AS \$\$", new).group(1),
                             re.search(r"SET search_path = ([^\n]+?) AS \$\$", old).group(1), name)
        for name, stmt in C_AFTER.items():
            self.assertEqual(stmt.count("$$"), 2, name)
            self.assertIn("AS $$", stmt, name)
            self.assertTrue(stmt.rstrip().endswith("$$"), name)
        sql = "\n".join(C_MIGRATION)
        self.assertNotRegex(sql, r"\b(?:ALTER TABLE|CREATE POLICY|ALTER POLICY|DROP |GRANT )")
        self.assertNotRegex(sql, r"CREATE(?: OR REPLACE)? FUNCTION master\.(?:ktt_|crm_kiem_|crm_g5_|mtq_quyet|mtq_giai|mtq_duoc_doc)")
        for name in ("master.crm_ky_quan_he(uuid)", "master.crm_ky_cap_quan_he(text,text,uuid)", "master.crm_ky_mtq(text,text,uuid)"):
            self.assertIn(name, sql.split("REVOKE ALL ON FUNCTION", 1)[1])

    def test_g3_ghi_va_doc_noi_cung_kiem_quan_he_g4(self):
        for name in ("master.crm_gk_dich", "master.crm_gk_xem"):
            stmt = C_AFTER[name]
            self.assertIn("CASE WHEN split_part(lenh, ':', 2) = 'G3_G4_SOAN_KY'", stmt)
            self.assertIn("THEN master.crm_ky_mtq(", stmt)
            self.assertIn("ELSE master.mtq_quyet_dinh_phien(", stmt)
        stmt = C_AFTER["master.crm_ky_mtq"]
        self.assertIn("p_bang = 'master.crm_bao_gia' AND pv.loai = 'DU_AN'", stmt)
        self.assertIn("r.revision = b.revision_hien_hanh", stmt)
        self.assertIn("p_bang = 'master.crm_gk_xuat'", stmt)

    def test_thong_bao_mtq_khong_lo_khoa_catalog(self):
        for name in ("master.crm_g_dich", "master.crm_gk_dich", "master.crm_ky_dich", "master.crm_ky_doc", "master.crm_ky_tep"):
            lines = [line for line in C_AFTER[name].splitlines() if "RAISE EXCEPTION" in line and "q->>'ma'" in line]
            self.assertEqual(len(lines), 1, name)
            self.assertNotIn(", lenh", lines[0])
            self.assertNotIn("CRM:", lines[0])
            self.assertNotIn("master.", lines[0])


@unittest.skipUnless(DSN and psycopg is not None, "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class MtqCrmKySqlPostgres(unittest.TestCase):
    nguoi = nen.MtqPostgres.nguoi
    actor = nen.MtqPostgres.actor
    ghi = nen.MtqPostgres.ghi
    nhap = nen.MtqPostgres.nhap
    sua_nhap = nen.MtqPostgres.sua_nhap
    san_sang = nen.MtqPostgres.san_sang
    loi = nen.MtqPostgres.loi
    insert = MtqCrmSqlPostgres.insert
    insert_dong = MtqCrmSqlPostgres.insert_dong
    policies = classmethod(MtqCrmSqlPostgres.policies.__func__)

    @classmethod
    def metadata(cls):
        names = sorted(C_AFTER.keys() & C_BEFORE.keys())
        return cls.c.execute(
            "SELECT oid,proowner,proacl::text,prosecdef,proconfig FROM pg_proc "
            "WHERE pronamespace='master'::regnamespace AND proname=ANY(%s) ORDER BY oid",
            ([n.split('.')[1] for n in names],)).fetchall()

    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = "kho_test_mtq_crm_ky_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as c:
            c.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_web') "
                      "THEN CREATE ROLE app_web NOLOGIN; END IF; END $$")
            c.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.c = psycopg.connect(make_conninfo(DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c, target=C_POSITION)
        cls.acl_before, cls.rls_before = cls.metadata(), cls.policies()
        postgres.migrate(cls.c, target=C_POSITION + 1)
        cls.acl_after, cls.rls_after = cls.metadata(), cls.policies()
        postgres.migrate(cls.c)

    def setUp(self):
        nen.MtqPostgres.setUp(self)
        self.user = self.nguoi("XEM")
        self.sender, self.approver = self.nguoi("XEM"), self.nguoi("XEM")
        self.f = self.fixture(self.pn)
        self.digest = "b" * 64

    def revision(self, f, khach=None):
        from psycopg.types.json import Jsonb

        old = self.c.execute("SELECT to_jsonb(r) FROM master.crm_hd_soan_rev r WHERE soan_id=%s ORDER BY revision DESC LIMIT 1",
                             (f["s"],)).fetchone()[0]
        for key in ("id", "tao_luc"):
            old.pop(key)
        old["revision"] += 1
        data = {"bao_gia": {"du_an_id": str(f["da"]), "khach": khach or {"doi_tac_id": str(f["kh"])}}}
        old["du_lieu"] = Jsonb(data)
        # Digest là giá trị do PostgreSQL tính như producer, không hash JSON Python.
        old["du_lieu_sha256"] = self.c.execute(
            "SELECT encode(sha256(convert_to(%s::jsonb::text,'UTF8')),'hex')", (Jsonb(data),)).fetchone()[0]
        rid = self.insert("master.crm_hd_soan_rev", **old)
        self.c.execute("UPDATE master.crm_hd_soan SET revision_hien_hanh=%s WHERE id=%s", (old["revision"], f["s"]))
        f["rev"], f["rid"] = old["revision"], rid
        return data

    def fixture(self, pn):
        # Tái dùng fixture đã kiểm FK/trigger G1/G2/G3. Thêm revision giả đủ
        # HĐ–dự án–khách; không sửa revision bất biến, không tắt trigger.
        f = MtqCrmBGSqlPostgres.fixture(self, pn)
        self.revision(f)
        from psycopg.types.json import Jsonb
        f["xs"] = self.insert("master.crm_gk_xuat", phap_nhan_id=pn, loai="HOP_DONG", soan_id=f["s"], revision=f["rev"],
                              input_sha256=f["sha"], docx_sha256=f["sha"], docx_len=1, trang_thai="PDF_CHUA_SAN_SANG",
                              engine="MTQ_TEST", kiem_pdf=Jsonb({}), tao_boi=self.admin[1])
        self.c.execute("UPDATE master.crm_hd_soan SET trang_thai='CHO_KY' WHERE id=%s", (f["s"],))
        self.c.execute("UPDATE master.hop_dong SET trang_thai='CHO_KY',crm_giao_ket='CHO_KY' WHERE id=%s", (f["hd"],))
        return f

    def cau_hinh(self, actions=C_ACTIONS, scope="HOP_DONG", key=None):
        return MtqCrmSqlPostgres.cau_hinh(self, actions, scope, key or self.f["hd"])

    def scope(self, grant, loai="HOP_DONG", key=None, relation=None):
        return self.ghi("PHAM_VI", {"gan_vai_id": grant["id"], "phap_nhan_id": str(self.pn),
                                  "loai": loai, "khoa": str(key or self.f["hd"]), "quan_he": relation or {}})

    def decision(self, action=C_LAP, f=None):
        return self.c.execute("SELECT master.crm_ky_mtq(%s,'master.crm_hd_soan',%s)",
                              (action, (f or self.f)["s"])).fetchone()[0]

    def doc(self, f=None):
        return self.c.execute("SELECT master.crm_ky_doc(%s)", ((f or self.f)["s"],)).fetchone()[0]

    def ky(self, f=None, expected=None, input_sha=None, khoa="KY", ngay=date(2026, 1, 1)):
        from psycopg.types.json import Jsonb
        f = f or self.f
        return self.c.execute(
            "SELECT master.crm_ky_ket(%s,%s,%s,%s,%s,%s,NULL,NULL,%s,1,1,'ban-ky.pdf',%s,false,NULL,NULL,%s)",
            (khoa, self.digest, f["s"], expected if expected is not None else f["rev"], f["xs"], input_sha or f["sha"],
             "c" * 64, ngay, Jsonb({}))).fetchone()[0]

    def legacy(self, who=None, pn=None, f=None):
        who, pn, f = who or self.user, pn or self.pn, f or self.f
        self.c.execute("INSERT INTO master.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,ARRAY['CRM'])", (who[0], pn))
        assignment = self.insert("master.phan_cong_hanh_dong", nguoi_dung_id=who[0], phap_nhan_id=pn, module="CRM",
                                 hanh_dong="CRM_KY_KET", cap_boi=self.admin[1])
        self.insert("master.crm_ky_pham_vi", phan_cong_id=assignment, phap_nhan_id=pn, hop_dong_id=f["hd"],
                    soan_id=f["s"], du_an_id=f["da"], doi_tac_id=f["kh"], cap_boi=self.admin[1])

    def test_tick_lap_ky_khong_can_xem_vai_hoac_assignment_cu(self):
        self.cau_hinh(actions={C_LAP})
        self.assertEqual(self.c.execute("SELECT * FROM master.crm_ky_dich(%s)", (self.f["s"],)).fetchone()[0], self.pn)
        signed = self.ky()["ket_qua"]
        self.assertEqual(signed["trang_thai"], "DA_KY")
        self.assertIsNone(signed["g3_pdf_sha256"])
        self.loi("MTQ_CHUA_TICK", self.doc)
        self.loi("MTQ_CHUA_TICK", lambda: self.c.execute("SELECT master.crm_ky_tep(%s,'TAI_BAN_KY')", (signed["ky_id"],)))

    def test_tick_tat_chan_ca_vai_va_assignment_cu(self):
        self.user = self.nguoi("BAN_HANG")
        self.legacy()
        self.cau_hinh(actions={C_XEM})
        self.loi("MTQ_CHUA_TICK", self.ky)
        self.assertFalse(self.doc()["quyen"]["doc"])
        self.assertEqual(self.c.execute("SELECT count(*) FROM master.crm_hd_ky").fetchone()[0], 0)

    def test_metadata_khong_tu_cap_ban_ky_hoac_can_cu(self):
        self.cau_hinh(actions={C_XEM})
        data = self.doc()
        self.assertFalse(data["quyen"]["doc"])
        self.assertNotIn("can_cu", data)
        self.assertNotIn("ban_ky", data)
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.su_kien WHERE hanh_dong='CRM_KY_DOC'").fetchone()[0], 0)

    def test_ban_ky_doc_lap_xem_va_ghi_log_truoc_tra_hash(self):
        self.cau_hinh()
        signed = self.ky()["ket_qua"]
        data = self.doc()
        self.assertEqual(data["ban_ky"]["ky_pdf_sha256"], "c" * 64)
        got = self.c.execute("SELECT master.crm_ky_tep(%s,'TAI_BAN_KY')", (signed["ky_id"],)).fetchone()[0]
        self.assertEqual(got["sha256"], "c" * 64)
        logs = self.c.execute("SELECT hanh_dong,sau FROM nhat_ky.su_kien WHERE hanh_dong IN ('CRM_KY_DOC','CRM_KY_TAI') ORDER BY id").fetchall()
        self.assertEqual([r[0] for r in logs], ["CRM_KY_DOC", "CRM_KY_TAI"])
        self.assertNotIn("nguoi_ky_khach", json.dumps(logs, default=str))
        self.loi("CRM_G_YEU_CAU_SAI", lambda: self.c.execute("SELECT master.crm_ky_tep(%s,'SAI')", (signed["ky_id"],)))

    def test_chi_tick_ban_ky_tai_duoc_nhung_khong_mo_metadata_hoac_ky(self):
        self.user = self.nguoi("BAN_HANG")
        self.legacy()
        self.actor(self.user)
        signed = self.ky()["ket_qua"]
        self.user = self.nguoi("XEM")
        self.cau_hinh(actions={C_BAN})
        self.loi("MTQ_CHUA_TICK", self.doc)
        self.loi("MTQ_CHUA_TICK", self.ky)
        got = self.c.execute("SELECT master.crm_ky_tep(%s,'TAI_BAN_KY')", (signed["ky_id"],)).fetchone()[0]
        self.assertEqual(got["sha256"], "c" * 64)

    def test_pham_vi_pn_loai_hinh_khach_khong_du_ky(self):
        for scope, key in (("PHAP_NHAN", self.pn), ("LOAI_HINH", self.f["lh"]), ("KHACH", self.f["kh"])):
            with self.subTest(scope=scope), self.c.transaction(force_rollback=True):
                self.cau_hinh(scope=scope, key=key)
                self.loi("MTQ_PHAM_VI:", self.ky)
                self.loi("MTQ_PHAM_VI:", self.doc)
                self.loi("MTQ_PHAM_VI:", lambda: self.c.execute(
                    "SELECT master.crm_gk_dich('CRM_SOAN_XUAT',%s)", (self.f["s"],)))

    def test_server_ghim_hd_crm_co_ban_soan_hien_hanh(self):
        self.cau_hinh()
        pv = self.c.execute("SELECT quan_he FROM master.mtq_pham_vi ORDER BY id LIMIT 1").fetchone()[0]
        self.assertEqual(pv, {"doi_tac_id": str(self.f["kh"]), "soan_id": str(self.f["s"]),
                              "du_an_id": str(self.f["da"]), "khach_du_thao_sha256": None})
        self.assertTrue(self.decision()["cho_phep"])

    def test_cap_hd_truoc_tick_sau_cong_bo_va_bat_pn_ky_duoc(self):
        self.actor(self.admin)
        v = self.nhap()
        for phong in (self.phong, self.phong2):
            for vai in nen.VAI:
                d = self.sua_nhap(v, "DONG", {"phong_id": phong, "vai": vai, "gioi_han_vnd": 0})
                if phong == self.phong and vai == "TRUONG_PHONG":
                    dong = d["id"]
        self.assertEqual(self.c.execute("SELECT count(*) FROM master.mtq_o").fetchone()[0], 0)
        self.assertFalse(self.c.execute(
            "SELECT EXISTS (SELECT 1 FROM master.mtq_kich_hoat WHERE phap_nhan_id=%s AND bat)",
            (self.pn,)).fetchone()[0])
        grant = self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]), "phap_nhan_id": str(self.pn),
                                     "phong_id": self.phong, "vai": "TRUONG_PHONG"})
        # Không gửi quan_he: server phải ghim ngay khi vai chưa có bất kỳ tick nào.
        pv = self.ghi("PHAM_VI", {"gan_vai_id": grant["id"], "phap_nhan_id": str(self.pn),
                                  "loai": "HOP_DONG", "khoa": str(self.f["hd"])})
        self.assertEqual(pv["quan_he"], {"doi_tac_id": str(self.f["kh"]), "soan_id": str(self.f["s"]),
                                        "du_an_id": str(self.f["da"]), "khach_du_thao_sha256": None})
        for action in sorted(C_ACTIONS):
            module, man, hanh = action.split(":")
            self.sua_nhap(v, "O", {"dong_id": dong, "module": module, "man": man,
                                    "hanh_dong": hanh, "cho_phep": True})
        self.sua_nhap(v, "CONG_BO", {})
        self.san_sang()
        self.ghi("KICH_HOAT", {"phap_nhan_id": str(self.pn), "phien_ban_id": v["id"], "bat": True})
        self.actor(self.user)
        for action in C_ACTIONS:
            self.assertTrue(self.decision(action)["cho_phep"])
        self.assertEqual(self.ky()["ket_qua"]["trang_thai"], "DA_KY")
        self.assertEqual(self.c.execute("SELECT quan_he FROM master.mtq_pham_vi WHERE id=%s",
                                        (pv["id"],)).fetchone()[0], pv["quan_he"])

    def test_quan_he_sai_khac_rong_bi_tu_choi_voi_moi_vai_chua_tick(self):
        self.actor(self.admin)
        self.assertEqual(self.c.execute("SELECT count(*) FROM master.mtq_o").fetchone()[0], 0)
        for vai in nen.VAI:
            with self.subTest(vai=vai):
                who = self.nguoi("XEM")
                grant = self.ghi("GAN_VAI", {"nguoi_dung_id": str(who[0]), "phap_nhan_id": str(self.pn),
                                             "phong_id": self.phong, "vai": vai})
                self.loi("MTQ_PHAM_VI_LECH", lambda: self.scope(
                    grant, relation={"doi_tac_id": str(uuid.uuid4())}))
                self.loi("MTQ_PHAM_VI_LECH", lambda: self.scope(
                    grant, "DU_AN", self.f["da"], {"doi_tac_id": str(uuid.uuid4())}))
                self.assertEqual(self.scope(grant)["quan_he"]["soan_id"], str(self.f["s"]))
        self.assertEqual(self.c.execute("SELECT count(*) FROM master.mtq_pham_vi").fetchone()[0], len(nen.VAI))

    def test_cap_hd_m4_vay_mua_va_crm_chua_soan_giu_quan_he_rong(self):
        grants = self.cau_hinh(scope=None)
        self.actor(self.admin)
        for module, kind in (("M4", "XAY_DUNG"), (None, "VAY"), (None, "MUA"), (None, "THUE_DAT")):
            with self.subTest(module=module, loai=kind):
                hd = self.insert("master.hop_dong", phap_nhan_id=self.pn, du_an_id=self.f["da"],
                                 loai_hinh_dt_id=self.f["lh"], loai=kind, module_chu=module,
                                 ma_noi_bo=uuid.uuid4().hex, so_hop_dong=uuid.uuid4().hex, trang_thai="SOAN_THAO")
                pv = self.scope(grants[0], key=hd)
                self.assertEqual(pv["quan_he"], {})
                self.loi("MTQ_PHAM_VI_LECH", lambda: self.scope(
                    grants[1], key=hd, relation={"doi_tac_id": str(self.f["kh"])}))

    def test_du_an_khong_gui_quan_he_duoc_cap_nhung_chan_khoa_ky(self):
        self.cau_hinh(actions=C_ACTIONS | {"CRM:G3_G4_SOAN_KY:SUA", "CRM:G2_BAO_GIA:SUA"},
                      scope="DU_AN", key=self.f["da"])
        self.assertEqual(self.c.execute("SELECT quan_he FROM master.mtq_pham_vi LIMIT 1").fetchone()[0], {})
        for action in (C_LAP, C_XEM, C_BAN, "CRM:G3_G4_SOAN_KY:SUA"):
            self.assertEqual(self.decision(action)["ma"], "MTQ_PHAM_VI_LECH")
        self.loi("MTQ_PHAM_VI_LECH", self.ky)
        self.loi("MTQ_PHAM_VI_LECH", self.doc)
        for command in ("CRM_SOAN_LUU", "CRM_SOAN_XUAT"):
            self.loi("MTQ_PHAM_VI_LECH", lambda: self.c.execute(
                "SELECT master.crm_gk_dich(%s,%s)", (command, self.f["s"])))
        for table, key in (("master.crm_hd_soan", "s"), ("master.crm_gk_xuat", "xs")):
            self.assertFalse(self.c.execute("SELECT master.crm_gk_xem(%s,%s,%s)",
                                            (table, self.f[key], self.pn)).fetchone()[0])
        self.assertEqual(self.c.execute("SELECT * FROM master.crm_gk_dich('CRM_BAO_GIA_LUU',%s)",
                                        (self.f["bg"],)).fetchone()[0], self.pn)

    def test_hd_quan_he_rong_da_cap_truoc_khi_co_tick_khong_du_ky(self):
        grants = self.cau_hinh(scope=None)
        self.actor(self.admin)
        # Scope cũ được cấp trước khi vai có tick CRM ký: không sửa dữ liệu
        # bất biến và không tắt trigger; dùng đúng validator trước migration C.
        self.c.execute(C_BEFORE["master.mtq_kiem_ghi"])
        pv = self.scope(grants[0])
        self.c.execute(C_AFTER["master.mtq_kiem_ghi"])
        self.assertEqual(pv["quan_he"], {})
        self.actor(self.user)
        for action in C_ACTIONS:
            self.assertEqual(self.decision(action)["ma"], "MTQ_PHAM_VI_LECH")
        self.loi("MTQ_PHAM_VI_LECH", self.ky)

    def test_du_an_admin_chon_khach_cung_pn_va_tu_choi_quan_he_sai(self):
        grants = self.cau_hinh(scope=None)
        self.actor(self.admin)
        other = self.insert("master.doi_tac", phap_nhan_id=self.pn2,
                            ten_phap_ly="Khách PN khác tổng hợp", ten_chuan_hoa=uuid.uuid4().hex)
        for relation in ({"doi_tac_id": str(other)}, {"doi_tac_id": str(uuid.uuid4())},
                         {"doi_tac_id": "uuid-sai"}, {"khach_du_thao_sha256": "x" * 64},
                         {"khach_du_thao_sha256": None}, {"doi_tac_id": str(self.f["kh"]), "them": True},
                         {"doi_tac_id": str(self.f["kh"]), "khach_du_thao_sha256": "a" * 64}):
            with self.subTest(relation=relation):
                self.loi("MTQ_PHAM_VI_LECH", lambda: self.scope(grants[0], "DU_AN", self.f["da"], relation))
        relation = {"doi_tac_id": str(self.f["kh"])}
        with self.c.transaction(force_rollback=True):
            # Định dạng hash hợp lệ được cấp; khách thực tế khác thì vẫn chặn
            # lúc kiểm quyền, không tự lấy khách từ một bản soạn trong dự án.
            self.scope(grants[0], "DU_AN", self.f["da"], {"khach_du_thao_sha256": "a" * 64})
            self.actor(self.user)
            self.assertEqual(self.decision()["ma"], "MTQ_PHAM_VI_LECH")
        pv = self.scope(grants[0], "DU_AN", self.f["da"], relation)
        self.assertEqual(pv["quan_he"], relation)
        self.actor(self.user)
        self.assertTrue(self.decision()["cho_phep"])
        self.assertEqual(self.c.execute("SELECT * FROM master.crm_gk_dich('CRM_BAO_GIA_CHUYEN',%s)",
                                        (self.f["bg"],)).fetchone()[0], self.pn)

    def test_admin_quan_he_gia_bi_tu_choi_va_thu_hoi_cap_lai(self):
        grants = self.cau_hinh(scope=None)
        self.actor(self.admin)
        self.loi("MTQ_PHAM_VI_LECH", lambda: self.scope(grants[0], relation={"doi_tac_id": str(uuid.uuid4())}))
        p = self.scope(grants[0])
        self.ghi("THU_HOI_PHAM_VI", {"id": p["id"]}, p["revision"])
        self.scope(grants[0], relation=p["quan_he"])
        self.actor(self.user)
        self.assertTrue(self.decision()["cho_phep"])

    def test_khach_du_thao_bam_dung_va_doi_hash_chan_khong_fallback(self):
        draft = {"ten": "KHACH GIA LAP A"}
        self.c.execute("UPDATE master.hop_dong SET doi_tac_id=NULL WHERE id=%s", (self.f["hd"],))
        self.revision(self.f, {"du_thao": draft})
        grants = self.cau_hinh(scope=None)
        self.actor(self.admin)
        sha = self.c.execute("SELECT encode(sha256(convert_to(%s::jsonb::text,'UTF8')),'hex')", (json.dumps(draft),)).fetchone()[0]
        pv = self.scope(grants[0], "DU_AN", self.f["da"], {"khach_du_thao_sha256": sha})
        self.assertEqual(pv["quan_he"], {"khach_du_thao_sha256": sha})
        self.actor(self.user)
        self.assertTrue(self.decision()["cho_phep"])
        self.revision(self.f, {"du_thao": {"ten": "KHACH GIA LAP B"}})
        self.assertEqual(self.decision()["ma"], "MTQ_PHAM_VI_LECH")
        self.loi("MTQ_PHAM_VI_LECH", self.doc)

    def test_doi_khach_du_an_va_soan_chan_bang_ma_lech(self):
        for kind in ("khach", "du_an"):
            with self.subTest(kind=kind), self.c.transaction(force_rollback=True):
                self.cau_hinh()
                f = dict(self.f)
                if kind == "khach":
                    self.c.execute("UPDATE master.hop_dong SET doi_tac_id=NULL WHERE id=%s", (f["hd"],))
                    self.revision(f, {"du_thao": {"ten": "KHACH DOI TONG HOP"}})
                else:
                    f["da"] = self.insert("master.du_an", phap_nhan_id=self.pn, ma_junsky=uuid.uuid4().hex, ten="Dự án thay tổng hợp")
                    self.c.execute("UPDATE master.hop_dong SET du_an_id=%s WHERE id=%s", (f["da"], f["hd"]))
                    self.revision(f)
                self.loi("MTQ_PHAM_VI_LECH", self.ky)
                self.loi("MTQ_PHAM_VI_LECH", self.doc)

    def test_du_an_nhieu_khach_khong_tu_chon_va_id_thieu_chan(self):
        grants = self.cau_hinh(scope=None)
        self.loi("MTQ_PHAM_VI", self.ky)
        self.loi("CRM_G_KHONG_THAY", lambda: self.c.execute("SELECT master.crm_ky_dich(%s)", (uuid.uuid4(),)))
        self.loi("CRM_G_KHONG_THAY", lambda: self.c.execute("SELECT master.crm_ky_tep(%s,'TAI_BAN_KY')", (uuid.uuid4(),)))
        # Dự án có nhiều khách vẫn cấp được {}; Admin chọn khách tường minh.
        # Chỉ dùng các bảng/FK thật, không tạo fixture PN trùng số báo giá.
        self.actor(self.admin)
        other = self.insert("master.hop_dong", phap_nhan_id=self.pn, du_an_id=self.f["da"], loai_hinh_dt_id=self.f["lh"],
                            loai="THUE_DAT", ma_noi_bo=uuid.uuid4().hex, so_hop_dong=uuid.uuid4().hex,
                            trang_thai="SOAN_THAO", crm_giao_ket="SOAN_THAO")
        sid = self.insert("master.crm_hd_soan", phap_nhan_id=self.pn, hop_dong_id=other,
                          bao_gia_id=self.f["bg"], bao_gia_revision=1, loai_hinh_id=self.f["lh"], revision_hien_hanh=1,
                          trang_thai="SOAN_THAO", tao_boi=self.admin[1])
        from psycopg.types.json import Jsonb
        row = self.c.execute("SELECT to_jsonb(r) FROM master.crm_hd_soan_rev r WHERE id=%s", (self.f["rid"],)).fetchone()[0]
        for key in ("id", "tao_luc"):
            row.pop(key)
        row.update(soan_id=sid, revision=1, du_lieu=Jsonb({"bao_gia": {"du_an_id": str(self.f["da"]),
                   "khach": {"du_thao": {"ten": "KHACH KHAC TONG HOP"}}}}))
        self.insert("master.crm_hd_soan_rev", **row)
        pv = self.scope(grants[0], "DU_AN", self.f["da"])
        self.assertEqual(pv["quan_he"], {})
        self.ghi("THU_HOI_PHAM_VI", {"id": pv["id"]}, pv["revision"])
        self.scope(grants[0], "DU_AN", self.f["da"], {"doi_tac_id": str(self.f["kh"])})
        self.actor(self.user)
        self.assertTrue(self.decision()["cho_phep"])
        self.assertEqual(self.decision(f={"s": sid})["ma"], "MTQ_PHAM_VI_LECH")
        self.actor(self.admin)
        self.loi("MTQ_PHAM_VI", lambda: self.scope(grants[0], "HOP_DONG", uuid.uuid4()))

    def test_scope_hd_lech_khong_roi_xuong_du_an_hoac_pn(self):
        grants = self.cau_hinh(scope=None)
        self.actor(self.admin)
        self.scope(grants[0], "DU_AN", self.f["da"], {"doi_tac_id": str(self.f["kh"])})
        pv = self.scope(grants[0])
        self.scope(grants[0], "PHAP_NHAN", self.pn)
        # Mô phỏng scope đã cấp trước B3 bằng cách tạo trước khi migration C;
        # validator hiện hành không cho sửa quan_he của scope bất biến.
        with self.c.transaction(force_rollback=True):
            self.c.execute(C_BEFORE["master.mtq_kiem_ghi"])
            self.ghi("THU_HOI_PHAM_VI", {"id": pv["id"]}, pv["revision"])
            self.scope(grants[0], relation={"soan_id": str(uuid.uuid4())})
            self.c.execute(C_AFTER["master.mtq_kiem_ghi"])
            self.actor(self.user)
            self.assertEqual(self.decision()["ma"], "MTQ_PHAM_VI_LECH")

    def test_thu_hoi_scope_va_vai_chan_truoc_replay_metadata_tep(self):
        for kind in ("PHAM_VI", "VAI"):
            with self.subTest(kind=kind), self.c.transaction(force_rollback=True):
                grants = self.cau_hinh()
                signed = self.ky()["ket_qua"]
                self.assertTrue(self.ky()["lap_lai"])
                self.actor(self.admin)
                row = grants[0] if kind == "VAI" else self.c.execute(
                    "SELECT jsonb_build_object('id',id,'revision',revision) FROM master.mtq_pham_vi WHERE gan_vai_id=%s", (grants[0]["id"],)).fetchone()[0]
                self.ghi("THU_HOI_" + kind, {"id": row["id"]}, row["revision"])
                self.actor(self.user)
                code = "MTQ_GAN_VAI" if kind == "VAI" else "MTQ_PHAM_VI"
                self.loi(code, self.ky)
                self.loi(code, lambda: self.c.execute("SELECT master.crm_ky_tra('KY',%s,%s)", (self.f["s"], self.digest)))
                self.loi(code, self.doc)
                self.loi(code, lambda: self.c.execute("SELECT master.crm_ky_tep(%s,'TAI_BAN_KY')", (signed["ky_id"],)))

    def test_revision_digest_sai_va_sql_truc_tiep_van_chan(self):
        self.cau_hinh(actions={C_LAP})
        self.loi("CRM_GK_REVISION_CU", lambda: self.ky(expected=99))
        self.loi("CRM_KY_G3_LECH", lambda: self.ky(input_sha="d" * 64))
        signed = self.ky()["ket_qua"]
        self.loi("CRM_G_BAT_BIEN", lambda: self.c.execute("UPDATE master.crm_hd_ky SET ky_pdf_len=2 WHERE id=%s", (signed["ky_id"],)))
        self.loi("CRM_GK_DA_KY", lambda: self.revision(self.f))

    def test_trigger_insert_ban_ky_truc_tiep_khong_ne_tick(self):
        from psycopg.types.json import Jsonb
        with self.c.transaction(force_rollback=True):
            self.cau_hinh(actions={C_LAP})
            signed = self.ky()["ket_qua"]
            row = self.c.execute("SELECT to_jsonb(k) FROM master.crm_hd_ky k WHERE id=%s", (signed["ky_id"],)).fetchone()[0]
        self.cau_hinh(actions={C_XEM})
        for key in ("id", "tao_luc"):
            row.pop(key)
        row["tom_tat"] = Jsonb(row["tom_tat"])
        self.loi("MTQ_CHUA_TICK", lambda: self.insert("master.crm_hd_ky", **row))

    def test_thong_bao_tu_choi_g1_g2_g4_khong_lo_khoa_bang_uuid(self):
        self.cau_hinh(actions=())
        for fn in (self.ky, self.doc,
                   lambda: self.c.execute("SELECT master.crm_g_dich('CRM_MAU_MAP',%s)", (self.f["mv"],)),
                   lambda: self.c.execute("SELECT master.crm_gk_dich('CRM_BAO_GIA_LUU',%s)", (self.f["bg"],))):
            with self.assertRaises(psycopg.Error) as cm:
                with self.c.transaction():
                    fn()
            message = cm.exception.diag.message_primary
            self.assertRegex(message, r"^MTQ_(CHUA_TICK|PHAM_VI): ")  # G4: PN scope không đủ (B3) → MTQ_PHAM_VI
            self.assertNotIn("CRM:", message)
            self.assertNotIn("master.", message)
            self.assertNotRegex(message, r"[0-9a-f]{8}-[0-9a-f-]{27,}")

    def test_cu_oracle_pn_b_tat_khong_doi_khi_bat_pn_a(self):
        f = self.fixture(self.pn2)
        allowed = self.nguoi("BAN_HANG")
        self.legacy(allowed, self.pn2, f)
        self.actor(allowed)
        signed = self.ky(f)["ket_qua"]

        def capture():
            result = {}
            for who in (allowed, self.user, self.nguoi_cu):
                self.actor(who)
                calls = {
                    "dich": ("SELECT master.crm_ky_dich(%s)", (f["s"],)),
                    "tra": ("SELECT master.crm_ky_tra('KY',%s,%s)", (f["s"], self.digest)),
                    "doc": ("SELECT master.crm_ky_doc(%s)", (f["s"],)),
                    "tep": ("SELECT master.crm_ky_tep(%s,'TAI_BAN_KY')", (signed["ky_id"],)),
                    "missing": ("SELECT master.crm_ky_dich(%s)", (uuid.UUID(int=0),)),
                }
                for name, (query, args) in calls.items():
                    try:
                        with self.c.transaction(force_rollback=True):
                            row = ("CHO", self.c.execute(query, args).fetchone())
                    except psycopg.Error as exc:
                        self.assertEqual(exc.sqlstate, "P0001")
                        self.assertRegex(exc.diag.message_primary, r"^CRM_(?:G_|KY_)")
                        row = ("CHAN", exc.sqlstate, exc.diag.message_primary)
                    result[who[0], name] = row
            return result

        self.nguoi_cu = self.nguoi("CFO")
        with self.c.transaction(force_rollback=True):
            for name in C_AFTER.keys() & C_BEFORE.keys():
                self.c.execute(C_BEFORE[name].replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1))
            oracle = capture()
        self.assertEqual({v[0] for v in oracle.values()}, {"CHO", "CHAN"})
        self.assertEqual(capture(), oracle)
        self.cau_hinh()
        self.assertEqual(capture(), oracle)

    def test_pn_tat_ky_giu_ma_ngay_trang_thai_va_ket_qua_oracle(self):
        self.user = self.nguoi("BAN_HANG")
        self.legacy()
        self.actor(self.user)

        def capture():
            errors = []
            for ngay in (None, date(2099, 1, 1)):
                with self.assertRaises(psycopg.Error) as cm:
                    with self.c.transaction():
                        self.ky(ngay=ngay)
                self.assertEqual(cm.exception.sqlstate, "P0001")
                self.assertTrue(cm.exception.diag.message_primary.startswith("CRM_KY_NGAY_SAI:"))
                errors.append(cm.exception.diag.message_primary)
            with self.c.transaction(force_rollback=True):
                self.c.execute("UPDATE master.crm_hd_soan SET trang_thai='SOAN_THAO' WHERE id=%s", (self.f["s"],))
                with self.assertRaises(psycopg.Error) as cm:
                    with self.c.transaction():
                        self.ky()
                self.assertEqual(cm.exception.sqlstate, "P0001")
                self.assertTrue(cm.exception.diag.message_primary.startswith("CRM_KY_TRANG_THAI:"))
                errors.append(cm.exception.diag.message_primary)
            with self.c.transaction(force_rollback=True):
                result = self.ky()
                self.assertFalse(result["lap_lai"])
                self.assertTrue(self.ky()["lap_lai"])
                signed = result["ket_qua"]
                self.assertEqual(signed["trang_thai"], "DA_KY")
                # UUID và thời điểm của lần ký mới do CSDL sinh, các giá trị
                # nghiệp vụ vẫn phải trùng oracle cũ trên cùng fixture.
                return errors, {k: signed[k] for k in ("trang_thai", "ky_pdf_sha256", "g3_pdf_sha256")}

        with self.c.transaction(force_rollback=True):
            for name in C_AFTER.keys() & C_BEFORE.keys():
                self.c.execute(C_BEFORE[name].replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1))
            oracle = capture()
        self.assertEqual(capture(), oracle)

    def test_acl_rls_va_ham_noi_bo_khong_cap_app(self):
        self.assertEqual(self.acl_before, self.acl_after)
        self.assertEqual(self.rls_before, self.rls_after)
        for signature in ("master.crm_ky_quan_he(uuid)", "master.crm_ky_cap_quan_he(text,text,uuid)", "master.crm_ky_mtq(text,text,uuid)"):
            self.assertFalse(self.c.execute("SELECT has_function_privilege('app_web',%s,'EXECUTE')", (signature,)).fetchone()[0])
        self.cau_hinh()
        self.c.execute("SET LOCAL ROLE app_web")
        self.loi("permission denied", lambda: self.c.execute("SELECT master.crm_ky_dich(%s)", (self.f["s"],)))
        self.c.execute("RESET ROLE")


if __name__ == "__main__":
    unittest.main()
