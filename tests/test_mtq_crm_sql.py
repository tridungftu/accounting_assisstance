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
from kho_tri_thuc.k2.sql_mtq_crm import MTQ_CRM_A_SQL, MTQ_CRM_B_SQL
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
        self.assertEqual(len(tree.body), 2)
        self.assertEqual(ast.literal_eval(tree.body[0].value), MTQ_CRM_A_SQL)
        self.assertEqual(ast.literal_eval(tree.body[1].value), MTQ_CRM_B_SQL)


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
                    renderer="MTQ_TEST", du_lieu=Jsonb({}), du_lieu_sha256=sha, tao_boi=login)
        self.c.execute("UPDATE master.crm_bao_gia SET trang_thai='DA_CHUYEN',hop_dong_id=%s WHERE id=%s", (hd, f["sbg"]))
        for key, kind, target in (("xb", "BAO_GIA", "bao_gia_id"), ("xs", "HOP_DONG", "soan_id")):
            f[key] = self.insert("master.crm_gk_xuat", phap_nhan_id=pn, loai=kind,
                                 **{target: f["bg" if key == "xb" else "s"]}, revision=1,
                                 input_sha256=sha, docx_sha256=sha, docx_len=1, trang_thai="PDF_CHUA_SAN_SANG",
                                 engine="MTQ_TEST", kiem_pdf=Jsonb({}), tao_boi=login)
        f.update(kh=kh, hd=hd)
        return f

    def cau_hinh(self, actions=B_ACTIONS, scope="PHAP_NHAN", key=None):
        return MtqCrmSqlPostgres.cau_hinh(self, actions, scope, key)

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
        self.cau_hinh(scope="DU_AN", key=other)
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


if __name__ == "__main__":
    unittest.main()
