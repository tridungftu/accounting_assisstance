"""MTQ-4a3a: resolver CRM/M1; PG tạo kho_test_* từ DSN quản trị.

Không mở server, không dùng DSN DEMO, không xóa CSDL/vai. Lead chạy PG.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import unittest
import uuid

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_mtq_cong import MTQ_CONG_B_SQL, MTQ_CONG_C_SQL, MTQ_CONG_SQL
from tests import test_mtq_sql as nen

ROOT = Path(__file__).resolve().parents[1]
DSN = os.environ.get("KHO_PG_DSN_TEST")
psycopg = nen.psycopg
CASES = (
    ("trich_tu_docx", "CRM:TIEP_NHAN:LAP", "master.phap_nhan"),
    ("nhan_ket_qua_6", "CRM:TIEP_NHAN:LAP", "master.phap_nhan"),
    ("bo_sung_ho_so", "CRM:TIEP_NHAN:SUA", "kho.chung_tu"),
    ("_trich_lai", "CRM:TIEP_NHAN:KIEM", "kho.chung_tu"),
    ("kiem_nhan_tien", "M1:TIEN:LAP", "master.phap_nhan"),
    ("lien_ket", "M1:TIEN:SUA", "master.hop_dong"),
    ("go_lien_ket", "M1:TIEN:HUY", "kho.lien_ket_chung_tu"),
    ("xuat_file_soat", "CRM:FILE_SOAT:XEM", "master.hop_dong"),
    ("tep_file_soat", "CRM:FILE_SOAT:XEM", "kho.lo_xuat"),
)
SIGNATURES = (
    "master.mtq_quyet_dinh_phien(text,jsonb,numeric)",
    "master.mtq_ghi_tu_choi_phien(uuid,text,jsonb,numeric)",
)


class MtqCongCTinh(unittest.TestCase):
    def test_registry_chi_append_khong_ghim_migration_cuoi(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# MTQ-4a3a — CD-012:"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, "exec"), old)
        previous = old["PG_MIGRATIONS"]
        self.assertEqual(PM.PG_MIGRATIONS[:len(previous)], previous)
        self.assertIs(PM.PG_MIGRATIONS[len(previous)], MTQ_CONG_C_SQL)
        self.assertEqual(sum(m is MTQ_CONG_C_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_giu_chu_ky_security_definer_va_acl(self):
        for current, previous in zip(MTQ_CONG_C_SQL[:2], (MTQ_CONG_SQL[0], MTQ_CONG_B_SQL[1])):
            self.assertEqual(current.split("DECLARE", 1)[0], previous.split("DECLARE", 1)[0].replace(
                "CREATE FUNCTION ", "CREATE OR REPLACE FUNCTION ", 1))
            self.assertIn("SECURITY DEFINER", current)
            self.assertIn("SET search_path = pg_catalog, master, nhat_ky, pg_temp", current)
        self.assertEqual(MTQ_CONG_C_SQL[2:], MTQ_CONG_SQL[2:])
        self.assertNotIn("EXECUTE ", MTQ_CONG_C_SQL[0])
        self.assertNotRegex("\n".join(MTQ_CONG_C_SQL), r"\b(?:CREATE TABLE|ALTER TABLE|DROP|INSERT INTO master\.)")

    def test_audit_giu_khoa_request_va_doi_chieu_idempotency(self):
        old = MTQ_CONG_B_SQL[1]
        new = MTQ_CONG_C_SQL[1]
        before_resolver = "            IF p_doi_tuong->>'bang' = 'master.hop_dong' THEN"
        after_resolver = "            SELECT g.phong_id, g.vai INTO phong, vai_hd"
        self.assertEqual(new.split(before_resolver)[0], old.split(before_resolver)[0])
        self.assertEqual(new.split(after_resolver)[1], old.split(after_resolver)[1])

    def test_utf8_khong_bom_va_migration_lf(self):
        for path in (Path(PM.__file__), ROOT / "src/kho_tri_thuc/k2/sql_mtq_cong.py", Path(__file__)):
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn("\ufffd", raw.decode("utf-8"))
        self.assertNotIn(b"\r", Path(PM.__file__).read_bytes())
        tree = ast.parse((ROOT / "src/kho_tri_thuc/k2/sql_mtq_cong.py").read_text(encoding="utf-8"))
        values = {a.targets[0].id: ast.literal_eval(a.value) for a in tree.body}
        self.assertEqual(values["MTQ_CONG_C_SQL"], MTQ_CONG_C_SQL)


@unittest.skipUnless(DSN and psycopg is not None, "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class MtqCongCPostgres(unittest.TestCase):
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

        cls.db = "kho_test_mtq_cong_c_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_web') THEN CREATE ROLE app_web NOLOGIN; END IF; END $$")
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.c = psycopg.connect(make_conninfo(DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        postgres.migrate(cls.c)

    def setUp(self):
        nen.MtqPostgres.setUp(self)
        self.objects = self.tao_doi_tuong(self.pn)

    @staticmethod
    def obj(table, key):
        return {"bang": table, "id": str(key)}

    def chung_tu(self, pn, kind="HOP_DONG_TEP"):
        return self.c.execute(
            "INSERT INTO kho.chung_tu (phap_nhan_id,loai,khoa_nguon,ngay_nghiep_vu,hash) "
            "VALUES (%s,%s,%s,current_date,%s) RETURNING id",
            (pn, kind, uuid.uuid4().hex, uuid.uuid4().hex * 2)).fetchone()[0]

    def hop_dong(self, pn, da=None, loai="DICH_VU", module=None):
        return self.c.execute(
            "INSERT INTO master.hop_dong (phap_nhan_id,du_an_id,loai,ma_noi_bo,so_hop_dong,module_chu) "
            "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (pn, da, loai, uuid.uuid4().hex, "HD-DEMO-" + uuid.uuid4().hex, module)).fetchone()[0]

    def gan_phien_ban(self, hd, ct, version=1):
        return self.c.execute(
            "INSERT INTO master.hop_dong_phien_ban (hop_dong_id,phien_ban,nguon,chung_tu_id) "
            "VALUES (%s,%s,'TRICH_6',%s) RETURNING id", (hd, version, ct)).fetchone()[0]

    def lo_xuat(self, pn, module="CRM", loai="FILE_SOAT"):
        return self.c.execute(
            "INSERT INTO kho.lo_xuat (phap_nhan_id,ky,ma_lo,loai,nguoi,du_lieu) "
            "VALUES (%s,'2026-10',%s,%s,%s,%s::jsonb) RETURNING id",
            (pn, uuid.uuid4().hex, loai, self.admin[1], json.dumps({"module": module}))).fetchone()[0]

    def lien_ket(self, pn, ct_a, ct_b, hd=None):
        # Liên kết không có lịch thu là dữ liệu hợp lệ; không giả lập tiền/duyệt.
        return self.c.execute(
            "INSERT INTO kho.lien_ket_chung_tu (phap_nhan_id,chung_tu_a_id,chung_tu_b_id,loai,hop_dong_id) "
            "VALUES (%s,%s,%s,'KHAC',%s) RETURNING id", (pn, ct_a, ct_b, hd)).fetchone()[0]

    def tao_doi_tuong(self, pn):
        da = self.c.execute(
            "INSERT INTO master.du_an (phap_nhan_id,ma_junsky,ten) VALUES (%s,%s,'Dự án MTQ DEMO') RETURNING id",
            (pn, uuid.uuid4().hex)).fetchone()[0]
        hd = self.hop_dong(pn, da)
        ct = self.chung_tu(pn)
        linked_ct = self.chung_tu(pn)
        self.gan_phien_ban(hd, linked_ct)
        lk = self.lien_ket(pn, ct, linked_ct, hd)
        return {
            "master.phap_nhan": self.obj("master.phap_nhan", pn),
            "master.hop_dong": self.obj("master.hop_dong", hd),
            "kho.chung_tu": self.obj("kho.chung_tu", ct),
            "kho.lien_ket_chung_tu": self.obj("kho.lien_ket_chung_tu", lk),
            "kho.lo_xuat": self.obj("kho.lo_xuat", self.lo_xuat(pn)),
            "ct_da_gan": self.obj("kho.chung_tu", linked_ct),
            "du_an": self.obj("master.du_an", da),
        }

    def cau_hinh(self, scope="PHAP_NHAN", key=None, tick=True):
        self.actor(self.admin)
        v = self.nhap()
        for phong in (self.phong, self.phong2):
            for vai in nen.VAI:
                d = self.sua_nhap(v, "DONG", {"phong_id": phong, "vai": vai, "gioi_han_vnd": 0})
                if phong == self.phong and vai == "TRUONG_PHONG" and tick:
                    for action in sorted({action for _, action, _ in CASES}):
                        module, man, hanh_dong = action.split(":")
                        self.sua_nhap(v, "O", {"dong_id": d["id"], "module": module,
                                               "man": man, "hanh_dong": hanh_dong, "cho_phep": True})
        self.sua_nhap(v, "CONG_BO", {})
        g = self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]), "phap_nhan_id": str(self.pn),
                                 "phong_id": self.phong, "vai": "TRUONG_PHONG"})
        if scope:
            self.ghi("PHAM_VI", {"gan_vai_id": g["id"], "phap_nhan_id": str(self.pn),
                                 "loai": scope, "khoa": str(key or self.pn)})
        self.san_sang()
        self.ghi("KICH_HOAT", {"phap_nhan_id": str(self.pn), "phien_ban_id": v["id"], "bat": True})
        self.actor(self.user)

    def cong(self, action, obj):
        return self.c.execute("SELECT master.mtq_quyet_dinh_phien(%s,%s::jsonb,NULL)",
                              (action, json.dumps(obj))).fetchone()[0]

    def assert_tu_choi(self, kq, code=None):
        self.assertEqual(kq["nguon"], "MA_TRAN")
        self.assertTrue(kq["can_thiep"])
        self.assertIs(kq["cho_phep"], False)
        self.assertTrue(kq["ma"].startswith("MTQ_"))
        if code:
            self.assertEqual(kq["ma"], code)

    def test_chin_diem_dung_pham_vi_khong_can_tien_va_app_web(self):
        self.cau_hinh()
        actions = sorted({action for _, action, _ in CASES})
        rows = self.c.execute("SELECT lenh_ky_thuat,loai_tien FROM master.mtq_danh_muc_hanh_dong "
                              "WHERE catalog_version=1 AND lenh_ky_thuat=ANY(%s)", (actions,)).fetchall()
        self.assertEqual(dict(rows), {a: "PHI_TIEN" for a in actions})
        self.c.execute("SET LOCAL ROLE app_web")
        for point, action, table in CASES:
            with self.subTest(diem=point):
                kq = self.cong(action, self.objects[table])
                self.assertEqual(kq["nguon"], "MA_TRAN")
                self.assertIs(kq["cho_phep"], True)
                self.assertIsNone(kq["so_tien_vnd"])

    def test_chin_diem_sai_phong_khong_fallback(self):
        self.cau_hinh()
        self.c.execute("SET LOCAL ROLE app_web")
        for point, action, table in CASES:
            with self.subTest(diem=point):
                self.assert_tu_choi(self.cong(action, {**self.objects[table], "phong_id": self.phong2}), "MTQ_GAN_VAI")

    def test_chin_diem_thieu_pham_vi_khong_fallback(self):
        self.cau_hinh(scope=None)
        for point, action, table in CASES:
            with self.subTest(diem=point):
                self.assert_tu_choi(self.cong(action, self.objects[table]), "MTQ_PHAM_VI")

    def test_chin_diem_tick_tat_cfo_cu_khong_bypass(self):
        self.cau_hinh(tick=False)
        for point, action, table in CASES:
            with self.subTest(diem=point):
                self.assert_tu_choi(self.cong(action, self.objects[table]), "MTQ_CHUA_TICK")

    def test_pn_chua_bat_tra_cu_ke_ca_khi_pn_khac_da_bat(self):
        other = self.tao_doi_tuong(self.pn2)
        self.actor(self.user)
        for objects in (self.objects, other):
            for point, action, table in CASES:
                with self.subTest(diem=point, obj=objects[table]):
                    self.assertEqual(self.cong(action, objects[table])["nguon"], "CU")
        self.cau_hinh()
        for point, action, table in CASES:
            with self.subTest(diem=point):
                kq = self.cong(action, other[table])
                self.assertEqual(kq["nguon"], "CU")
                self.assertFalse(kq["can_thiep"])
                self.assertIsNone(kq["cho_phep"])

    def test_toan_bo_cap_bang_lenh_ngoai_whitelist_bi_chan(self):
        self.cau_hinh()
        allowed = {(table, action) for _, action, table in CASES}
        # HĐ TIEP_NHAN được giữ từ cổng cũ.
        allowed.update(("master.hop_dong", a) for _, a, _ in CASES if a.startswith("CRM:TIEP_NHAN:"))
        for table in {t for _, _, t in CASES}:
            for action in {a for _, a, _ in CASES}:
                if (table, action) not in allowed:
                    with self.subTest(bang=table, lenh=action):
                        self.assert_tu_choi(self.cong(action, self.objects[table]), "MTQ_CAN_RESOLVER_MTQ4")

    def test_sai_loai_ho_so_lo_xuat_va_module_bi_chan_nhung_pn_tat_giu_cu(self):
        pairs = []
        for pn in (self.pn, self.pn2):
            pairs.extend((pn, a, o) for a, o in (
                ("CRM:TIEP_NHAN:SUA", self.obj("kho.chung_tu", self.chung_tu(pn, "KHAC"))),
                ("CRM:TIEP_NHAN:KIEM", self.obj("kho.chung_tu", self.chung_tu(pn, "KHAC"))),
                ("CRM:FILE_SOAT:XEM", self.obj("kho.lo_xuat", self.lo_xuat(pn, "M5"))),
                ("CRM:FILE_SOAT:XEM", self.obj("kho.lo_xuat", self.lo_xuat(pn, "CRM", "JUNSKY"))),
                ("CRM:FILE_SOAT:XEM", self.obj("kho.lo_xuat", self.lo_xuat(pn, None))),
            ))
        self.cau_hinh()
        for pn, action, obj in pairs:
            with self.subTest(pn=pn, lenh=action, obj=obj):
                kq = self.cong(action, obj)
                if pn == self.pn:
                    self.assert_tu_choi(kq, "MTQ_CAN_RESOLVER_MTQ4")
                else:
                    self.assertEqual(kq["nguon"], "CU")

    def test_pham_vi_hd_qua_phien_ban_va_lien_ket_khong_mo_rong_pn(self):
        hd = self.objects["master.hop_dong"]["id"]
        ct = self.objects["kho.chung_tu"]["id"]
        linked_ct = self.objects["ct_da_gan"]["id"]
        null_link = self.obj("kho.lien_ket_chung_tu", self.lien_ket(self.pn, linked_ct, ct))
        self.cau_hinh("HOP_DONG", hd)
        for action, obj in (
            ("CRM:TIEP_NHAN:SUA", self.objects["ct_da_gan"]),
            ("CRM:TIEP_NHAN:KIEM", self.objects["ct_da_gan"]),
            ("M1:TIEN:HUY", self.objects["kho.lien_ket_chung_tu"]),
        ):
            with self.subTest(lenh=action, obj=obj):
                self.assertIs(self.cong(action, obj)["cho_phep"], True)
        for action, obj in (
            ("CRM:TIEP_NHAN:SUA", self.objects["kho.chung_tu"]),
            ("M1:TIEN:HUY", null_link),
            ("M1:TIEN:LAP", self.objects["master.phap_nhan"]),
            ("CRM:TIEP_NHAN:LAP", self.objects["master.phap_nhan"]),
            ("CRM:FILE_SOAT:XEM", self.objects["kho.lo_xuat"]),
        ):
            with self.subTest(lenh=action, obj=obj):
                self.assert_tu_choi(self.cong(action, obj), "MTQ_PHAM_VI")

    def test_lien_ket_hd_null_chi_can_pham_vi_pn(self):
        lk = self.lien_ket(self.pn, self.objects["ct_da_gan"]["id"], self.objects["kho.chung_tu"]["id"])
        self.cau_hinh()
        self.assertIs(self.cong("M1:TIEN:HUY", self.obj("kho.lien_ket_chung_tu", lk))["cho_phep"], True)

    def test_pham_vi_du_an_qua_hd_ho_so_va_lien_ket(self):
        self.cau_hinh("DU_AN", self.objects["du_an"]["id"])
        for action, obj in (
            ("M1:TIEN:SUA", self.objects["master.hop_dong"]),
            ("CRM:FILE_SOAT:XEM", self.objects["master.hop_dong"]),
            ("CRM:TIEP_NHAN:KIEM", self.objects["ct_da_gan"]),
            ("M1:TIEN:HUY", self.objects["kho.lien_ket_chung_tu"]),
        ):
            with self.subTest(lenh=action):
                self.assertIs(self.cong(action, obj)["cho_phep"], True)

    def test_ho_so_gan_nhieu_hd_chan_khong_tu_chon_scope(self):
        ct = self.objects["ct_da_gan"]["id"]
        self.gan_phien_ban(self.hop_dong(self.pn), ct)
        self.cau_hinh()
        self.assert_tu_choi(self.cong("CRM:TIEP_NHAN:KIEM", self.objects["ct_da_gan"]), "MTQ_CAN_RESOLVER_MTQ4")

    def test_hd_m4_vay_mua_khong_thanh_hd_crm(self):
        da = self.objects["du_an"]["id"]
        objects = [self.obj("master.hop_dong", self.hop_dong(self.pn, da, loai, module))
                   for loai, module in (("XAY_DUNG", "M4"), ("VAY", None), ("MUA", None))]
        self.cau_hinh()
        for obj in objects:
            for action in ("M1:TIEN:SUA", "CRM:FILE_SOAT:XEM"):
                with self.subTest(obj=obj, lenh=action):
                    self.assert_tu_choi(self.cong(action, obj), "MTQ_CAN_RESOLVER_MTQ4")

    def test_ghi_tu_choi_dung_pn_va_khong_ghi_khi_chi_hoi(self):
        self.cau_hinh(scope=None)
        before = self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0]
        for _, action, table in CASES:
            self.assert_tu_choi(self.cong(action, self.objects[table]))
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0], before)
        self.c.execute("SET LOCAL ROLE app_web")
        written = []
        for point, action, table in CASES:
            with self.subTest(diem=point):
                request = uuid.uuid4()
                args = (request, action, json.dumps(self.objects[table]))
                query = "SELECT master.mtq_ghi_tu_choi_phien(%s,%s,%s::jsonb,NULL)"
                key = self.c.execute(query, args).fetchone()[0]
                self.assertEqual(self.c.execute(query, args).fetchone()[0], key)
                written.append((key, action, self.objects[table]["id"]))
        self.c.execute("RESET ROLE")
        for key, action, obj_id in written:
            row = self.c.execute("SELECT phap_nhan_id,actor_id,lenh_ky_thuat,doi_tuong,ma FROM nhat_ky.mtq_tu_choi WHERE id=%s", (key,)).fetchone()
            self.assertEqual(row, (self.pn, self.user[0], action, obj_id, "MTQ_PHAM_VI"))

    def test_acl_public_khong_execute_app_web_co_execute(self):
        for signature in SIGNATURES:
            with self.subTest(ham=signature):
                self.assertFalse(self.c.execute(
                    "SELECT EXISTS (SELECT 1 FROM pg_proc p, "
                    "LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a "
                    "WHERE p.oid=%s::regprocedure AND a.grantee=0 AND a.privilege_type='EXECUTE')",
                    (signature,)).fetchone()[0])
                self.assertTrue(self.c.execute("SELECT has_function_privilege('app_web',%s,'EXECUTE')", (signature,)).fetchone()[0])


if __name__ == "__main__":
    unittest.main()
