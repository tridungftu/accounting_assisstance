"""MTQ-4f1b: oracle CU, từng ô M17, ghi tin cậy và thu hồi trước replay.

PG chỉ tạo kho_test_* từ KHO_PG_DSN_TEST; giữ DB, không mở dịch vụ,
không đọc cấu hình DEMO, không tắt trigger. Thiếu runtime/DSN = NOT_RUN.
"""

from __future__ import annotations

import ast
from datetime import date
import os
from pathlib import Path
import re
import unittest
import uuid

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.m4.sql_m17 import HAM_LENH, HAM_TIN_CAY, _SOAN
from kho_tri_thuc.m4.sql_mtq import MTQ_M4_A_SQL
from tests import test_mtq_sql as nen

ROOT = Path(__file__).resolve().parents[1]
DSN = os.environ.get("KHO_PG_DSN_TEST")
psycopg = nen.psycopg
POSITION = next(i for i, m in enumerate(PM.PG_MIGRATIONS) if m[:len(MTQ_M4_A_SQL)] == MTQ_M4_A_SQL)
MIGRATION = PM.PG_MIGRATIONS[POSITION]
# Oracle ánh xạ độc lập từ KK-MTQ4-M4, không suy từ implementation.
COMMANDS = {
    "tao_hop_dong": ("TAO_HOP_DONG", "LAP", "master.du_an", "p_du_an", "p_du_an"),
    "ghi_tep": ("TAI_TEP", "LAP", "master.du_an", "p_du_an", "p_du_an"),
    "gan_tep_hop_dong": ("GAN_TEP_HOP_DONG", "SUA", "master.hop_dong", "h.du_an_id", "p_hd"),
    "ghi_trich_xuat": ("TRICH", "SUA", "master.hop_dong", "h.du_an_id", "p_hd"),
    "sua_tham_so": ("SUA_THAM_SO", "SUA", "master.hop_dong", "h.du_an_id", "p_hd"),
    "xac_nhan_tham_so": ("XAC_NHAN_THAM_SO", "KIEM", "master.hop_dong", "h.du_an_id", "p_hd"),
    "khai_phu_luc": ("KHAI_PHU_LUC", "SUA", "master.hop_dong", "h.du_an_id", "p_hd"),
    "them_phu_luc": ("THEM_PHU_LUC", "LAP", "master.hop_dong", "h.du_an_id", "p_hd"),
    "huy_phu_luc": ("HUY_PHU_LUC", "HUY", "master.hop_dong", "h.du_an_id", "p_pl"),
    "ghi_boq": ("NHAP_BOQ", "LAP", "master.hop_dong", "h.du_an_id", "p_hd"),
    "tao_dot": ("TAO_DOT", "LAP", "master.hop_dong", "h.du_an_id", "p_hd"),
    "sua_dot": ("SUA_DOT", "SUA", "m4.dot", "d.du_an_id", "p_dot"),
    "gan_tep_dot": ("GAN_TEP_DOT", "SUA", "m4.dot", "d.du_an_id", "p_dot"),
    "nop": ("NOP", "SUA", "m4.dot", "d.du_an_id", "p_dot"),
}
TRUSTED = {"ghi_tep", "ghi_trich_xuat", "sua_tham_so", "ghi_boq"}
INTERNAL = (
    "m4._mtq_ho_so_quyen(text,uuid)", "m4._mtq_ho_so_replay(text,jsonb,uuid)",
    "m4._mtq_ho_so_digest(uuid)", "m4._mtq_ho_so_thieu(uuid)", "m4._mtq_ho_so_khoa_dot(uuid,text)",
)
SIGNATURES = (*HAM_LENH, *HAM_TIN_CAY[:4], "m4.tra_bien_nhan(text)")


def definitions(migrations):
    result = {}
    for migration in migrations:
        for stmt in migration:
            m = re.match(r"CREATE(?: OR REPLACE)? FUNCTION ([\w.]+)\(", stmt)
            if m:
                result[m[1]] = stmt
    return result


BEFORE = definitions(PM.PG_MIGRATIONS[:POSITION])
AFTER = definitions((MIGRATION,))


class MtqM4HoSoTinh(unittest.TestCase):
    def test_chi_append_khong_ghim_migration_cuoi(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# MTQ-4f1b — CD-012:"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, "exec"), old)
        self.assertEqual(PM.PG_MIGRATIONS[:POSITION], old["PG_MIGRATIONS"])
        self.assertEqual(sum(m is MIGRATION for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_pham_vi_chi_m17_khong_sua_rls_master_hay_cong(self):
        self.assertEqual(set(AFTER), {"m4." + n for n in COMMANDS} | {"m4.tra_bien_nhan"}
                         | {s.split("(")[0] for s in INTERNAL})
        sql = "\n".join(MIGRATION)
        self.assertNotRegex(sql, r"\b(?:ALTER TABLE|CREATE POLICY|ALTER POLICY|DROP |GRANT )")
        self.assertNotIn("CREATE OR REPLACE FUNCTION master.", sql)
        self.assertNotIn("M4:02C_DUYET:DUYET", sql)
        self.assertNotIn("EXCEPTION WHEN", sql)

    def test_giu_toan_than_lenh_cu_ngoai_nguon_quyen(self):
        for name, (hanh, _, _, da, obj) in COMMANDS.items():
            with self.subTest(lenh=name):
                old, new = BEFORE["m4." + name], AFTER["m4." + name]
                if da == "d.du_an_id":
                    new = new.replace(f"m4._mtq_ho_so_khoa_dot(p_dot, '{hanh}')", "m4._khoa_dot(p_dot)", 1)
                else:
                    guard = _SOAN.format(d=da)
                    new = new.replace(f"\n            IF NOT m4._mtq_ho_so_quyen('{hanh}', {obj}) THEN"
                                      + guard + "\n            END IF;", guard, 1)
                if name == "xac_nhan_tham_so":
                    new = new.replace("CASE WHEN m4._mtq_ho_so_quyen('XAC_NHAN_THAM_SO', p_hd) "
                                      "THEN m4._mtq_ho_so_digest(h.hop_dong_id) ELSE m4.digest_tham_so(h.hop_dong_id) END",
                                      "m4.digest_tham_so(h.hop_dong_id)", 1)
                if name == "nop":
                    new = new.replace("con := CASE WHEN m4._mtq_ho_so_quyen('NOP', p_dot) "
                                      "THEN m4._mtq_ho_so_thieu(p_dot) ELSE m4.thieu(p_dot) END;",
                                      "con := m4.thieu(p_dot);", 1)
                self.assertEqual(new, old)

    def test_guard_truoc_replay_cas_va_giu_guard_nguon(self):
        for name, (hanh, _, _, _, _) in COMMANDS.items():
            stmt = AFTER["m4." + name]
            guard = "m4._mtq_ho_so_khoa_dot(" if name in ("sua_dot", "gan_tep_dot", "nop") else "m4._mtq_ho_so_quyen("
            self.assertLess(stmt.index(guard), stmt.index("m4._bn_tra("), name)
            self.assertLess(stmt.index(guard), stmt.index("m4._bn_ghi("), name)
            if "IF p_rev" in stmt:
                self.assertLess(stmt.index(guard), stmt.index("IF p_rev"), name)
            if name in TRUSTED:
                self.assertIn("master.la_chu_bang('m4.tep'::regclass)", stmt)
                self.assertLess(stmt.index("master.la_chu_bang("), stmt.index(guard))
                self.assertNotIn("SECURITY DEFINER", stmt)

    def test_chu_ky_acl_va_soan_chi_trong_nhanh_cu(self):
        for name, stmt in AFTER.items():
            if name in BEFORE:
                self.assertEqual(stmt.split("\n", 1)[0], BEFORE[name].split("\n", 1)[0])
                self.assertEqual("SECURITY DEFINER" in stmt, "SECURITY DEFINER" in BEFORE[name])
        for sig in INTERNAL:
            self.assertIn("REVOKE ALL ON FUNCTION " + sig.replace(",", ", ") + " FROM PUBLIC", MIGRATION)
        f = AFTER["m4._mtq_ho_so_quyen"]
        self.assertIn("pg_advisory_xact_lock_shared(742601, 1)", f)
        self.assertIn("m4.ai_id() FOR SHARE", f)
        self.assertIn("pn IS NULL OR phap_nhan_id = pn", f)
        self.assertIn("q->>'nguon' IS DISTINCT FROM 'MA_TRAN'", f)
        self.assertNotIn("master.m4_duoc", f)
        self.assertNotIn("ktt_co_vai", f)
        self.assertIn("master.mtq_giai_doi_tuong", f)

    def test_whitelist_dung_tung_lenh_va_doi_tuong(self):
        f = AFTER["m4._mtq_ho_so_quyen"].split("            -- M0051", 1)[0]
        actual = {}
        for choices, body in re.findall(r"WHEN (.*?) THEN(.*?)(?=\n                WHEN|\n                ELSE)", f, re.S):
            bang = re.search(r"bang := '([^']+)'", body).group(1)
            action = re.search(r"lenh := 'M4:HO_SO:([^']+)'", body).group(1)
            for hanh in re.findall(r"'([A-Z_]+)'", choices):
                actual[hanh] = (action, bang)
        self.assertEqual(actual, {hanh: (action, bang) for hanh, action, bang, _, _ in COMMANDS.values()})
        self.assertIn("SELECT p.hop_dong_id INTO obj FROM m4.phu_luc p WHERE p.id = p_id", f)

    def test_cac_helper_doc_noi_bo_giu_dieu_kien_nghiep_vu(self):
        digest = BEFORE["m4.digest_tham_so"].replace(
            "CREATE OR REPLACE FUNCTION m4.digest_tham_so", "CREATE FUNCTION m4._mtq_ho_so_digest", 1).replace(
            "LANGUAGE sql STABLE SECURITY DEFINER", "LANGUAGE sql STABLE", 1).replace(
            "\n          AND EXISTS (SELECT 1 FROM m4.ho_so_hop_dong h WHERE h.hop_dong_id = p_hd\n"
            "                      AND (master.m4_duoc(h.du_an_id, 'XEM') OR master.m4_duoc(h.du_an_id, 'REVIEW')))", "", 1)
        self.assertEqual(AFTER["m4._mtq_ho_so_digest"], digest)
        thieu = BEFORE["m4.thieu"].replace("CREATE OR REPLACE FUNCTION m4.thieu", "CREATE FUNCTION m4._mtq_ho_so_thieu", 1).replace(
            "LANGUAGE plpgsql STABLE SECURITY DEFINER", "LANGUAGE plpgsql STABLE", 1).replace(
            "IF NOT FOUND OR NOT (master.m4_duoc(d.du_an_id, 'XEM') OR (master.m4_duoc(d.du_an_id, 'REVIEW') AND d.trang_thai = 'DA_NOP')) THEN",
            "IF NOT FOUND THEN", 1).replace("m4.digest_tham_so(h.hop_dong_id)", "m4._mtq_ho_so_digest(h.hop_dong_id)", 1)
        self.assertEqual(AFTER["m4._mtq_ho_so_thieu"], thieu)
        khoa = AFTER["m4._mtq_ho_so_khoa_dot"].replace(
            "CREATE FUNCTION m4._mtq_ho_so_khoa_dot(p_dot uuid, p_hanh_dong text)",
            "CREATE OR REPLACE FUNCTION m4._khoa_dot(p_dot uuid)", 1)
        guard = _SOAN.format(d="d.du_an_id")
        khoa = khoa.replace("\n            IF NOT m4._mtq_ho_so_quyen(p_hanh_dong, p_dot) THEN" + guard + "\n            END IF;", guard, 1)
        self.assertEqual(khoa, BEFORE["m4._khoa_dot"])

    def test_replay_dung_actor_lenh_goc_va_khong_mo_lenh_khac(self):
        f = AFTER["m4.tra_bien_nhan"]
        self.assertIn("WHERE nguoi_dung_id = aid AND khoa = p_khoa", f)
        self.assertLess(f.index("m4._mtq_ho_so_replay("), f.index("RETURN jsonb_build_object("))
        self.assertNotIn("STABLE", f)
        f = AFTER["m4._mtq_ho_so_replay"]
        for hanh, _, _, _, _ in COMMANDS.values():
            self.assertIn("'" + hanh + "'", f)
        self.assertIn("ELSE\n                    -- Receipt", f)
        self.assertIn("MTQ_CAN_RESOLVER_MTQ4", f)

    def test_raise_giu_ma_loi_cau_nghiep_vu_khong_noi_khoa_ky_thuat(self):
        raises = re.findall(r"RAISE EXCEPTION '([^']+)'(.*?) USING ERRCODE = 'P0001';",
                            "\n".join(MTQ_M4_A_SQL))
        self.assertEqual(len(raises), 4)
        for template, args in raises:
            with self.subTest(thong_bao=template):
                code, separator, sentence = template.partition(": ")
                self.assertEqual(separator, ": ")
                self.assertNotRegex(sentence, r"[:%]|\b(?:master|m4)\.|\b(?:receipt|replay|PN)\b")
                if code == "%":
                    self.assertEqual(args, ", coalesce(q->>'ma', 'MTQ_TU_CHOI')")
                else:
                    self.assertEqual(code, "MTQ_CAN_RESOLVER_MTQ4")
                    self.assertEqual(args, "")

    def test_utf8_khong_bom_va_registry_lf(self):
        for path in (Path(PM.__file__), ROOT / "src/kho_tri_thuc/m4/sql_mtq.py", Path(__file__)):
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn("\ufffd", raw.decode("utf-8"))
        self.assertNotIn(b"\r", Path(PM.__file__).read_bytes())
        tree = ast.parse((ROOT / "src/kho_tri_thuc/m4/sql_mtq.py").read_text(encoding="utf-8"))
        self.assertEqual(ast.literal_eval(tree.body[1].value), MTQ_M4_A_SQL)


@unittest.skipUnless(DSN and psycopg is not None, "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class MtqM4HoSoPostgres(unittest.TestCase):
    nguoi = nen.MtqPostgres.nguoi
    actor = nen.MtqPostgres.actor
    ghi = nen.MtqPostgres.ghi
    nhap = nen.MtqPostgres.nhap
    sua_nhap = nen.MtqPostgres.sua_nhap
    san_sang = nen.MtqPostgres.san_sang

    @classmethod
    def metadata(cls):
        return cls.c.execute("SELECT oid::regprocedure::text,proowner,proacl::text,prosecdef,proconfig "
                             "FROM pg_proc WHERE oid=ANY(%s::regprocedure[]) ORDER BY oid", (list(SIGNATURES),)).fetchall()

    @classmethod
    def policies(cls):
        return cls.c.execute("SELECT polrelid,polname,polcmd,polpermissive,pg_get_expr(polqual,polrelid),"
                             "pg_get_expr(polwithcheck,polrelid) FROM pg_policy ORDER BY polrelid,polname").fetchall()

    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = "kho_test_mtq_m4_ho_so_" + uuid.uuid4().hex[:12]
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
        self.f = self.fixture(self.pn)
        self.actor(self.user)  # CFO cũ, không assignment/module M4.

    def insert(self, table, **values):
        from psycopg import sql
        stmt = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
            sql.Identifier(*table.split(".")), sql.SQL(",").join(map(sql.Identifier, values)),
            sql.SQL(",").join(sql.Placeholder() for _ in values))
        return self.c.execute(stmt, tuple(values.values())).fetchone()[0]

    def fixture(self, pn, da=None, module="M4"):
        from psycopg.types.json import Jsonb

        # Đã đọc hop_dong_kiem, _mc_ho_so_moi, nop_duyet_phien_ban và
        # trigger chủ bảng/append-only M17. Đối tác gắn mapping cùng PN.
        j = Jsonb
        login = self.admin[1]
        da = da or self.insert("master.du_an", phap_nhan_id=pn, ma_junsky=uuid.uuid4().hex, ten="Dự án giả MTQ")
        kh = self.insert("master.doi_tac", phap_nhan_id=pn, ten_phap_ly="Đối tác giả", ten_chuan_hoa=uuid.uuid4().hex)
        self.insert("master.doi_tac_ma_junsky", phap_nhan_id=pn, doi_tac_id=kh, object_id_junsky=uuid.uuid4().hex)
        hd = self.insert("master.hop_dong", phap_nhan_id=pn, du_an_id=da, doi_tac_id=kh, loai="XAY_DUNG",
                         module_chu=module, ma_noi_bo=uuid.uuid4().hex, so_hop_dong=uuid.uuid4().hex)
        f = dict(pn=pn, da=da, hd=hd)
        for key, role in (("t_hd", "HOP_DONG"), ("t_hd2", "HOP_DONG"), ("t_pl", "PHU_LUC"), ("t_boq", "BOQ"), ("t_dot", "HO_SO_DOT")):
            sha = uuid.uuid4().hex * 2
            media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if role == "BOQ" else "application/pdf"
            filename = "gia.xlsx" if role == "BOQ" else "gia.pdf"
            f[key] = self.insert("m4.tep", phap_nhan_id=pn, du_an_id=da, vai_tro_tai_lieu=role, raw_sha256=sha,
                                 byte_length=1, media_type=media, ten_goc=filename, object_key="m4-raw/" + sha, tao_boi=login)
            f[key + "_sha"] = sha
        self.c.execute("INSERT INTO m4.ho_so_hop_dong(hop_dong_id,phap_nhan_id,du_an_id,ten,tao_boi,tep_hop_dong_id,trang_thai_pl) "
                       "VALUES (%s,%s,%s,'Hồ sơ giả',%s,%s,'CO_DU')", (hd, pn, da, login, f["t_hd"]))
        extracted = [{"ma": row[0], "trang_thai": "KHONG_QUY_DINH", "gia_tri": None,
                      "ly_do": "Dữ liệu giả không quy định", "nguon": "QUY_TAC"}
                     for row in self.c.execute("SELECT ma FROM m4.danh_muc_tham_so ORDER BY ma")]
        f["tx"] = self.insert("m4.trich_xuat", hop_dong_id=hd, du_an_id=da, lan=1, tep_id=f["t_hd"], raw_sha256=f["t_hd_sha"],
                              catalog_sha256="a" * 64, engine="MTQ_TEST", che_do="QUY_TAC_KHONG_AI", trang_thai="XONG",
                              phieu=j({}), ket_qua=j(extracted), tao_boi=login)
        self.c.execute("INSERT INTO m4.tham_so(hop_dong_id,ma,du_an_id,trang_thai,ly_do,nguon,trich_xuat_id,cap_nhat_boi) "
                       "SELECT %s,ma,%s,'KHONG_QUY_DINH','Dữ liệu giả không quy định','QUY_TAC',%s,%s FROM m4.danh_muc_tham_so",
                       (hd, da, f["tx"], login))
        self.insert("m4.xac_nhan_tham_so", hop_dong_id=hd, du_an_id=da, rev_tham_so=1, tep_id=f["t_hd"],
                    raw_sha256=f["t_hd_sha"], trich_xuat_id=f["tx"], catalog_sha256="a" * 64,
                    tham_so_digest=self.c.execute("SELECT m4._mtq_ho_so_digest(%s)", (hd,)).fetchone()[0],
                    xac_nhan_boi=login, xac_nhan_boi_id=self.admin[0])
        f["pl"] = self.insert("m4.phu_luc", hop_dong_id=hd, du_an_id=da, so_pl="PL-GIA", ngay_ky=date(2026, 1, 1),
                              ngay_hieu_luc=date(2026, 1, 1), trang_thai="DA_KY", doi_boq=False, tep_id=f["t_pl"], tao_boi=login)
        b = self.insert("m4.boq", hop_dong_id=hd, du_an_id=da, lan=1, tep_id=f["t_boq"], raw_sha256=f["t_boq_sha"],
                        sheet="Gia", hang_tieu_de=1, cot=j({}), so_dong=1, loi_chan=j([]), phat_hien=j([]), trang_thai="DA_MAP",
                        bo_doc="MTQ_TEST", tao_boi=login)
        self.c.execute("INSERT INTO m4.boq_dong(boq_id,du_an_id,dong,ma_hm,thao_tac,ten,dvt,o_goc) "
                       "VALUES (%s,%s,1,'GIA','GOC','Hạng mục giả','m','{}')", (b, da))
        f["dot"] = self.insert("m4.dot", hop_dong_id=hd, du_an_id=da, so_dot=1, ngay_nghiem_thu=date(2026, 2, 1), tao_boi=login)
        self.c.execute("INSERT INTO m4.dot_tep(dot_id,du_an_id,tep_id,muc,tao_boi) "
                       "SELECT %s,%s,%s,ma,%s FROM m4.danh_muc_ho_so_dot WHERE bat_buoc_dot_dau", (f["dot"], da, f["t_dot"], login))
        return f

    def legacy(self, *fixtures):
        self.c.execute("UPDATE master.nguoi_dung SET vai_tro='DU_AN' WHERE id=%s", (self.user[0],))
        for pn in {f["pn"] for f in fixtures}:
            self.c.execute("INSERT INTO master.phan_quyen(nguoi_dung_id,phap_nhan_id,module) VALUES (%s,%s,ARRAY['M4']) "
                           "ON CONFLICT (nguoi_dung_id,phap_nhan_id) DO UPDATE SET module=EXCLUDED.module", (self.user[0], pn))
        for f in fixtures:
            self.insert("m4.quyen_du_an", nguoi_dung_id=self.user[0], phap_nhan_id=f["pn"], du_an_id=f["da"], vai="PHU_TRACH")

    def configure(self, actions=("LAP", "SUA", "KIEM", "HUY"), scope="PHAP_NHAN", key=None):
        self.actor(self.admin)
        v = self.nhap()
        for phong in (self.phong, self.phong2):
            for vai in nen.VAI:
                row = self.sua_nhap(v, "DONG", {"phong_id": phong, "vai": vai, "gioi_han_vnd": 0})
                if phong == self.phong and vai == "TRUONG_PHONG":
                    for a in actions:
                        self.sua_nhap(v, "O", {"dong_id": row["id"], "module": "M4", "man": "HO_SO", "hanh_dong": a, "cho_phep": True})
        self.sua_nhap(v, "CONG_BO", {})
        g = self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]), "phap_nhan_id": str(self.pn), "phong_id": self.phong, "vai": "TRUONG_PHONG"})
        s = self.ghi("PHAM_VI", {"gan_vai_id": g["id"], "phap_nhan_id": str(self.pn), "loai": scope, "khoa": str(key or self.pn)})
        self.san_sang()
        self.ghi("KICH_HOAT", {"phap_nhan_id": str(self.pn), "phien_ban_id": v["id"], "bat": True})
        self.actor(self.user)
        return s

    def call(self, name, f=None, key=None, stale=False):
        from psycopg.types.json import Jsonb

        f = f or self.f
        k, h, d, rev = key or uuid.uuid4().hex, f["hd"], f["dot"], 0 if stale else 1
        j = Jsonb
        args = {
            "tao_hop_dong": (k, f["da"], "HD-" + k, "Hợp đồng giả"),
            "ghi_tep": (k, f["da"], "HOP_DONG", "f" * 64, 1, "application/pdf", "gia.pdf"),
            "gan_tep_hop_dong": (k, h, rev, f["t_hd2"]),
            "ghi_trich_xuat": (k, h, rev, f["t_hd"], f["t_hd_sha"], "a" * 64, "MTQ_TEST", "QUY_TAC_KHONG_AI", "LOI", "Lỗi giả", j({}), j([])),
            "sua_tham_so": (k, h, rev, "TC-01", "KHONG_QUY_DINH", None, None, None, None, "Lý do giả", None),
            "xac_nhan_tham_so": (k, h, rev, "a" * 64, "Xác nhận giả"),
            "khai_phu_luc": (k, h, rev, "CO_CHUA_DU"),
            "them_phu_luc": (k, h, rev, "PL-MOI", date(2026, 2, 1), date(2026, 2, 1), "DU_THAO", False, "Giả", f["t_pl"]),
            "huy_phu_luc": (k, f["pl"], rev, "Hủy giả"),
            "ghi_boq": (k, h, rev, f["t_boq"], f["t_boq_sha"], None, "Gia", 1, j({}), "MTQ_TEST", j([]), j(["Lỗi giả"]), j([])),
            "tao_dot": (k, h, 2, date(2026, 2, 1)),
            "sua_dot": (k, d, rev, date(2026, 2, 2)),
            "gan_tep_dot": (k, d, rev, f["t_dot"], "A04"),
            "nop": (k, d, rev, rev),
        }[name]
        return "SELECT m4." + name + "(" + ",".join("%s" for _ in args) + ")", args

    def prepare(self, name, f=None):
        if name == "xac_nhan_tham_so":
            self.c.execute("UPDATE m4.ho_so_hop_dong SET rev_tham_so=2 WHERE hop_dong_id=%s", ((f or self.f)["hd"],))

    def probe(self, name, f=None, oracle=False, stale=False, web=None, query=None, full_message=False):
        self.c.execute("SAVEPOINT mtq_m4_probe")
        try:
            if oracle:
                self.c.execute(BEFORE["m4." + name])
            self.prepare(name, f)
            if (web if web is not None else name not in TRUSTED):
                self.c.execute("SET LOCAL ROLE app_web")
            stmt, args = query or self.call(name, f, stale=stale)
            try:
                self.c.execute(stmt, args).fetchone()
                return ("OK",)
            except psycopg.Error as exc:
                message = exc.diag.message_primary
                return ("ERR", exc.sqlstate, message if full_message else message.split(":", 1)[0])
        finally:
            self.c.execute("ROLLBACK TO SAVEPOINT mtq_m4_probe")
            self.c.execute("RELEASE SAVEPOINT mtq_m4_probe")

    def test_acl_rls_va_helper_khong_cap_app(self):
        self.assertEqual(self.acl_before, self.acl_after)
        self.assertEqual(self.rls_before, self.rls_after)
        for sig in INTERNAL:
            self.assertFalse(self.c.execute("SELECT has_function_privilege('app_web',%s,'EXECUTE')", (sig,)).fetchone()[0])
        for name in TRUSTED:
            self.assertEqual(self.probe(name, web=True)[:2], ("ERR", "42501"))

    def test_cu_so_oracle_cho_chan_va_ma_loi_moi_lenh(self):
        for grant in (False, True):
            if grant:
                self.legacy(self.f)
            for name in COMMANDS:
                for stale in (False, True):
                    with self.subTest(lenh=name, legacy=grant, stale=stale):
                        old = self.probe(name, oracle=True, stale=stale)
                        self.assertEqual(self.probe(name, stale=stale), old)
                        if grant and not stale:
                            self.assertEqual(old, ("OK",))
                        elif not grant:
                            self.assertEqual(old, ("ERR", "P0001", "M4_KHONG_CO_QUYEN_DU_AN"))

    def test_tick_bat_vai_cu_cam_van_ghi_du_14_lenh(self):
        self.configure()
        self.assertFalse(self.c.execute("SELECT master.m4_duoc(%s,'SOAN')", (self.f["da"],)).fetchone()[0])
        for name in COMMANDS:
            with self.subTest(lenh=name):
                self.assertEqual(self.probe(name), ("OK",))

    def test_tick_tat_vai_cu_cho_van_chan_truoc_cas(self):
        self.legacy(self.f)
        self.configure(actions=())
        for name in COMMANDS:
            with self.subTest(lenh=name):
                self.assertEqual(self.probe(name, stale=True), ("ERR", "P0001", "MTQ_CHUA_TICK"))

    def assert_thong_bao_nghiep_vu(self, result, code):
        self.assertEqual(result[:2], ("ERR", "P0001"))
        prefix, separator, sentence = result[2].partition(": ")
        self.assertEqual((prefix, separator), (code, ": "))
        self.assertTrue(sentence.strip())
        self.assertNotRegex(sentence, r":|\b(?:master|m4)\.|\b[A-Z][A-Z0-9_]+\b|[0-9a-f]{8}-[0-9a-f-]{27,}")

    def test_tu_choi_lenh_va_replay_khong_lo_khoa_catalog(self):
        from psycopg.types.json import Jsonb

        self.configure(actions=())
        request = Jsonb({key: str(self.f[value]) for key, value in
                        (("du_an_id", "da"), ("hop_dong_id", "hd"), ("phu_luc_id", "pl"), ("dot_id", "dot"))})
        for name, (action, _, _, _, _) in COMMANDS.items():
            with self.subTest(lenh=name):
                self.assert_thong_bao_nghiep_vu(self.probe(name, full_message=True), "MTQ_CHUA_TICK")
                query = ("SELECT m4._mtq_ho_so_replay(%s,%s,%s)", (action, request, self.f["da"]))
                self.assert_thong_bao_nghiep_vu(
                    self.probe(name, query=query, web=False, full_message=True), "MTQ_CHUA_TICK")

    def test_raise_khong_ho_tro_va_replay_khong_lo_du_lieu_ky_thuat(self):
        from psycopg.types.json import Jsonb

        self.configure()
        unsupported = "M4:HO_SO:SUA"
        other = self.fixture(self.pn2)
        queries = (
            ("SELECT m4._mtq_ho_so_quyen(%s,%s)", (unsupported, self.f["hd"])),
            ("SELECT m4._mtq_ho_so_replay(%s,%s,%s)", (unsupported, Jsonb({}), self.f["da"])),
            ("SELECT m4._mtq_ho_so_replay(%s,%s,%s)",
             ("SUA_THAM_SO", Jsonb({"hop_dong_id": str(other["hd"])}), self.f["da"])),
        )
        for query in queries:
            with self.subTest(query=query[0], action=query[1][0]):
                self.assert_thong_bao_nghiep_vu(
                    self.probe("replay", query=query, web=False, full_message=True), "MTQ_CAN_RESOLVER_MTQ4")

    def test_tick_bat_van_giu_cas_revision(self):
        self.configure()
        for name in set(COMMANDS) - {"tao_hop_dong", "ghi_tep", "tao_dot"}:
            with self.subTest(lenh=name):
                self.assertEqual(self.probe(name, stale=True), ("ERR", "P0001", "M4_REVISION_CU"))

    def test_tung_o_doc_lap_khong_doi_them_soan_sua_xem(self):
        for action in ("LAP", "SUA", "KIEM", "HUY"):
            self.c.execute("SAVEPOINT mtq_m4_cell")
            try:
                self.configure(actions=(action,))
                for name, (_, expected, _, _, _) in COMMANDS.items():
                    with self.subTest(o=action, lenh=name):
                        outcome = ("OK",) if expected == action else ("ERR", "P0001", "MTQ_CHUA_TICK")
                        self.assertEqual(self.probe(name), outcome)
            finally:
                self.c.execute("ROLLBACK TO SAVEPOINT mtq_m4_cell")
                self.c.execute("RELEASE SAVEPOINT mtq_m4_cell")

    def test_scope_hd_khong_mo_hd_khac_cung_du_an_hay_du_an_cha(self):
        other = self.fixture(self.pn, da=self.f["da"])
        self.configure(scope="HOP_DONG", key=self.f["hd"])
        self.assertEqual(self.probe("sua_dot"), ("OK",))
        for name in ("khai_phu_luc", "sua_dot", "huy_phu_luc"):
            self.assertEqual(self.probe(name, other), ("ERR", "P0001", "MTQ_PHAM_VI"))
        for name in ("tao_hop_dong", "ghi_tep"):
            self.assertEqual(self.probe(name), ("ERR", "P0001", "MTQ_PHAM_VI"))

    def test_scope_du_an_va_pn_b_tat_khong_doi_khi_a_bat(self):
        other = self.fixture(self.pn)
        off = self.fixture(self.pn2)
        self.legacy(off)
        before = {name: self.probe(name, off) for name in COMMANDS}
        self.configure(scope="DU_AN", key=self.f["da"])
        for name in COMMANDS:
            with self.subTest(lenh=name):
                self.assertEqual(self.probe(name, other), ("ERR", "P0001", "MTQ_PHAM_VI"))
                self.assertEqual(self.probe(name, off), before[name])
                self.assertEqual(before[name], ("OK",))

    def test_hd_crm_va_id_khong_giai_duoc_bi_chan(self):
        crm = self.fixture(self.pn, module=None)
        self.configure()
        for name in ("gan_tep_hop_dong", "xac_nhan_tham_so", "sua_dot", "nop", "huy_phu_luc"):
            self.assertEqual(self.probe(name, crm), ("ERR", "P0001", "MTQ_CAN_RESOLVER_MTQ4"))
        missing = {**self.f, "da": uuid.uuid4()}
        for name in ("tao_hop_dong", "ghi_tep"):
            self.assertEqual(self.probe(name, missing), ("ERR", "P0001", "MTQ_CAN_RESOLVER_MTQ4"))

    def test_thu_hoi_truoc_replay_lenh_va_tra_bien_nhan(self):
        scope = self.configure()
        for name in COMMANDS:
            self.c.execute("SAVEPOINT mtq_m4_replay")
            try:
                self.prepare(name)
                key = uuid.uuid4().hex
                stmt, args = self.call(name, key=key)
                if name not in TRUSTED:
                    self.c.execute("SET LOCAL ROLE app_web")
                first = self.c.execute(stmt, args).fetchone()[0]
                again = self.c.execute(stmt, args).fetchone()[0]
                self.assertFalse(first["lap_lai"])
                self.assertTrue(again["lap_lai"])
                self.assertEqual(first["ket_qua"], again["ket_qua"])
                receipt = self.c.execute("SELECT m4.tra_bien_nhan(%s)", (key,)).fetchone()[0]
                self.assertEqual(receipt["hanh_dong"], COMMANDS[name][0])
                self.c.execute("RESET ROLE")
                self.actor(self.admin)
                self.ghi("THU_HOI_PHAM_VI", {"id": scope["id"]}, scope["revision"])
                self.actor(self.user)
                for query in ((stmt, args), ("SELECT m4.tra_bien_nhan(%s)", (key,))):
                    with self.subTest(lenh=name, query=query[0]):
                        web = query[0].startswith("SELECT m4.tra_bien_nhan") or name not in TRUSTED
                        self.assertEqual(self.probe(name, query=query, web=web), ("ERR", "P0001", "MTQ_PHAM_VI"))
            finally:
                self.c.execute("ROLLBACK TO SAVEPOINT mtq_m4_replay")
                self.c.execute("RELEASE SAVEPOINT mtq_m4_replay")

    def test_receipt_dung_actor_va_cu_so_oracle(self):
        self.legacy(self.f)
        stmt, args = self.call("tao_dot")
        self.c.execute(stmt, args)
        query = ("SELECT m4.tra_bien_nhan(%s)", (args[0],))
        self.assertEqual(self.probe("tra_bien_nhan", oracle=True, web=True, query=query), ("OK",))
        self.assertEqual(self.probe("tra_bien_nhan", web=True, query=query), ("OK",))
        self.actor(self.admin)
        self.assertIsNone(self.c.execute(*query).fetchone()[0])
        self.actor(self.user)
        qid = self.c.execute("SELECT id FROM m4.quyen_du_an WHERE nguoi_dung_id=%s AND du_an_id=%s",
                             (self.user[0], self.f["da"])).fetchone()[0]
        self.c.execute("SELECT m4.thu_hoi_quyen_du_an(%s,%s,'Thu hồi giả')", (qid, self.admin[1]))
        old = self.probe("tra_bien_nhan", oracle=True, web=True, query=query)
        self.assertEqual(old, ("ERR", "P0001", "M4_KHONG_CO_QUYEN_DU_AN"))
        self.assertEqual(self.probe("tra_bien_nhan", web=True, query=query), old)

    def test_receipt_ngoai_m17_cu_giu_nguyen_bat_thi_chan(self):
        from psycopg.types.json import Jsonb

        self.legacy(self.f)
        key = uuid.uuid4().hex
        self.c.execute("SELECT m4._bn_ghi(%s,%s,'REVIEW_CHAY',%s,%s,%s)",
                       (self.user[0], key, self.f["da"], Jsonb({}), Jsonb({"gia": True})))
        query = ("SELECT m4.tra_bien_nhan(%s)", (key,))
        self.assertEqual(self.probe("tra_bien_nhan", web=True, query=query),
                         self.probe("tra_bien_nhan", oracle=True, web=True, query=query))
        self.configure()
        self.assertEqual(self.probe("tra_bien_nhan", web=True, query=query), ("ERR", "P0001", "MTQ_CAN_RESOLVER_MTQ4"))

    def test_nhieu_phong_khong_tu_hop_quyen_cu_va_moi(self):
        self.legacy(self.f)
        self.configure()
        self.actor(self.admin)
        g = self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]), "phap_nhan_id": str(self.pn),
                                  "phong_id": self.phong2, "vai": "TRUONG_PHONG"})
        self.ghi("PHAM_VI", {"gan_vai_id": g["id"], "phap_nhan_id": str(self.pn), "loai": "PHAP_NHAN", "khoa": str(self.pn)})
        self.actor(self.user)
        for name in COMMANDS:
            self.assertEqual(self.probe(name), ("ERR", "P0001", "MTQ_PHONG_MO_HO"))


if __name__ == "__main__":
    unittest.main()
