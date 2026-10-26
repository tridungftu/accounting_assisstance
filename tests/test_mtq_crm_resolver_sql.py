"""MTQ-4b1a: resolver bảng riêng CRM, không mở H/S1 hoặc G5/G6.

PG chỉ dùng KHO_PG_DSN_TEST để tạo kho_test_*; không mở server, không xóa DB.
Fixture tổng hợp đi qua CHECK/FK/trigger thật, không gọi dịch vụ hay Word.
"""

from __future__ import annotations

import ast
from datetime import date
import json
import os
from pathlib import Path
import re
import unittest
import uuid

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_ma_tran_tham_quyen import _CATALOG
from kho_tri_thuc.k2.sql_mtq_cong import MTQ_CONG_C_SQL, MTQ_CONG_D_SQL, MTQ_CONG_E_SQL
from tests import test_mtq_sql as nen

ROOT = Path(__file__).resolve().parents[1]
DSN = os.environ.get("KHO_PG_DSN_TEST")
psycopg = nen.psycopg
SIGNATURES = (
    "master.mtq_quyet_dinh_phien(text,jsonb,numeric)",
    "master.mtq_ghi_tu_choi_phien(uuid,text,jsonb,numeric)",
)
# Khóa fixture = bảng, riêng X có hai loại xuất với whitelist khác nhau.
ALLOWED = {
    "master.loai_hinh_doanh_thu": (
        "CRM:G1_MAU:XEM", "CRM:G1_MAU:LAP", "CRM:G2_BAO_GIA:XEM", "CRM:G2_BAO_GIA:LAP"),
    "master.crm_mau_phien_ban": (
        "CRM:G1_MAU:XEM", "CRM:G1_MAU:SUA", "CRM:G1_MAU:KIEM", "CRM:G1_MAU:DUYET"),
    "master.crm_bo_chuan_phien_ban": ("CRM:G7_CHUAN:XEM", "CRM:G7_CHUAN:SUA", "CRM:G7_CHUAN:DUYET"),
    "master.crm_bao_gia": (
        "CRM:G2_BAO_GIA:XEM", "CRM:G2_BAO_GIA:SUA", "CRM:G2_BAO_GIA:HUY", "CRM:G3_G4_SOAN_KY:LAP"),
    "master.crm_hd_soan": (
        "CRM:G3_G4_SOAN_KY:XEM", "CRM:G3_G4_SOAN_KY:LAP", "CRM:G3_G4_SOAN_KY:SUA", "CRM:BAN_KY:XEM"),
    "master.crm_hd_ky": ("CRM:BAN_KY:XEM",),
    "x_bao_gia": ("CRM:G2_BAO_GIA:XEM",),
    "x_hop_dong": ("CRM:G3_G4_SOAN_KY:XEM",),
    "master.du_an": (
        "CRM:DU_AN_BAN:XEM", "CRM:DU_AN_BAN:LAP", "CRM:DU_AN_BAN:SUA",
        "CRM:G7_CHUAN:XEM", "CRM:G7_CHUAN:LAP", "CRM:G7_CHUAN:SUA", "CRM:G7_CHUAN:DUYET",
        "M4:HO_SO:XEM", "M4:HO_SO:LAP", "M4:HO_SO:SUA"),
    "master.crm_da_ban": ("CRM:DU_AN_BAN:XEM", "CRM:DU_AN_BAN:LAP", "CRM:DU_AN_BAN:SUA"),
    "master.crm_da_ban_lo": ("CRM:DU_AN_BAN:XEM", "CRM:DU_AN_BAN:SUA"),
    "master.crm_da_moc": ("CRM:DU_AN_BAN:XEM", "CRM:DU_AN_BAN:SUA"),
}
ACTIONS = sorted({a for actions in ALLOWED.values() for a in actions})


class MtqCrmResolverTinh(unittest.TestCase):
    def test_registry_append_khong_ghim_migration_cuoi(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# MTQ-4b1a — CD-012:"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, "exec"), old)
        previous = old["PG_MIGRATIONS"]
        self.assertEqual(PM.PG_MIGRATIONS[:len(previous)], previous)
        self.assertIs(PM.PG_MIGRATIONS[len(previous)], MTQ_CONG_D_SQL)
        self.assertEqual(sum(m is MTQ_CONG_D_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_chu_ky_acl_search_path_khong_doi(self):
        for new, old in zip(MTQ_CONG_D_SQL[:2], MTQ_CONG_C_SQL[:2]):
            self.assertEqual(new.split("DECLARE", 1)[0], old.split("DECLARE", 1)[0])
            self.assertIn("CREATE OR REPLACE FUNCTION", new)
            self.assertIn("SECURITY DEFINER", new)
            self.assertIn("SET search_path = pg_catalog, master, nhat_ky, pg_temp", new)
        self.assertEqual(MTQ_CONG_D_SQL[2:], MTQ_CONG_C_SQL[2:])
        self.assertNotIn("EXECUTE ", MTQ_CONG_D_SQL[0])
        self.assertNotRegex("\n".join(MTQ_CONG_D_SQL), r"\b(?:CREATE TABLE|ALTER TABLE|DROP )")

    def test_hop_dong_va_audit_idempotency_giu_nguyen(self):
        for new, old in zip(MTQ_CONG_D_SQL[:2], MTQ_CONG_C_SQL[:2]):
            start = "IF p_doi_tuong->>'bang' = 'master.hop_dong' THEN"
            end = "ELSIF p_doi_tuong->>'bang' = 'master.du_an' THEN"
            self.assertEqual(new.split(start, 1)[1].split(end, 1)[0],
                             old.split(start, 1)[1].split(end, 1)[0])
        pattern = r"\(p_doi_tuong->>'bang' = 'master.hop_dong' AND \([\s\S]+?(?=\s+\(p_doi_tuong->>'bang' = 'master.du_an')"
        sections = [re.search(pattern, sql).group() for sql in (MTQ_CONG_D_SQL[0], MTQ_CONG_C_SQL[0])]
        self.assertEqual(*(" ".join(re.sub(r"--[^\n]*", "", s).split()) for s in sections))
        start = "            IF p_doi_tuong->>'bang' = 'master.hop_dong' THEN"
        end = "            SELECT g.phong_id, g.vai INTO phong, vai_hd"
        self.assertEqual(MTQ_CONG_D_SQL[1].split(start)[0], MTQ_CONG_C_SQL[1].split(start)[0])
        self.assertEqual(MTQ_CONG_D_SQL[1].split(end)[1], MTQ_CONG_C_SQL[1].split(end)[1])

    def test_bat_tat_va_pham_vi_giu_cung_loi(self):
        new, old = MTQ_CONG_D_SQL[0], MTQ_CONG_C_SQL[0]
        start = "                    IF NOT EXISTS (SELECT 1 FROM master.mtq_kich_hoat"
        end = "                        SELECT c.loai_doi_tuong"
        self.assertEqual(new.split(start)[1].split(end)[0], old.split(start)[1].split(end)[0])
        start = "                            SELECT count(*), (array_agg(g.phong_id))[1]"
        self.assertEqual(new.split(start)[1], old.split(start)[1])

    def test_resolver_va_audit_du_bang_khoa_deu_co_trong_catalog(self):
        catalog = {f"{m}:{s}:{a}" for m, s, actions, _ in _CATALOG for a in actions.split()}
        for key, actions in ALLOWED.items():
            table = "master.crm_gk_xuat" if key.startswith("x_") else key
            for sql in MTQ_CONG_D_SQL[:2]:
                self.assertIn(f"p_doi_tuong->>'bang' = '{table}'", sql)
                self.assertIn(f"FROM {table}", sql)
            for action in actions:
                self.assertIn(action, catalog)
                sql = MTQ_CONG_E_SQL[0] if action.startswith("M4:") else MTQ_CONG_D_SQL[0]
                self.assertIn(f"'{action}'", sql)
        for ref in ("r.revision = b.revision_hien_hanh", "r.revision = x.revision",
                    "s.hop_dong_id = k.hop_dong_id", "xuat_loai = 'BAO_GIA'", "xuat_loai = 'HOP_DONG'"):
            self.assertIn(ref, MTQ_CONG_D_SQL[0])

    def test_utf8_khong_bom_lf_va_hang_literal(self):
        paths = (Path(PM.__file__), ROOT / "src/kho_tri_thuc/k2/sql_mtq_cong.py", Path(__file__))
        for path in paths:
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn("\ufffd", raw.decode("utf-8"))
        self.assertNotIn(b"\r", paths[0].read_bytes())
        tree = ast.parse(paths[1].read_text(encoding="utf-8"))
        values = {a.targets[0].id: ast.literal_eval(a.value) for a in tree.body}
        self.assertEqual(values["MTQ_CONG_D_SQL"], MTQ_CONG_D_SQL)


@unittest.skipUnless(DSN and psycopg is not None, "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class MtqCrmResolverPostgres(unittest.TestCase):
    nguoi = nen.MtqPostgres.nguoi
    actor = nen.MtqPostgres.actor
    ghi = nen.MtqPostgres.ghi
    nhap = nen.MtqPostgres.nhap
    sua_nhap = nen.MtqPostgres.sua_nhap
    san_sang = nen.MtqPostgres.san_sang

    @classmethod
    def acl(cls):
        return cls.c.execute(
            "SELECT oid::regprocedure::text,proacl::text,proowner,prosecdef,proconfig "
            "FROM pg_proc WHERE oid=ANY(%s::regprocedure[]) ORDER BY oid", (list(SIGNATURES),)).fetchall()

    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = "kho_test_mtq_crm_resolver_" + uuid.uuid4().hex[:12]
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_web') "
                          "THEN CREATE ROLE app_web NOLOGIN; END IF; END $$")
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.c = psycopg.connect(make_conninfo(DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        position = next(i for i, m in enumerate(PM.PG_MIGRATIONS) if m is MTQ_CONG_D_SQL)
        postgres.migrate(cls.c, target=position)
        cls.acl_before = cls.acl()
        postgres.migrate(cls.c, target=position + 1)
        cls.acl_after = cls.acl()
        postgres.migrate(cls.c)

    def setUp(self):
        nen.MtqPostgres.setUp(self)
        self.objects, self.refs = self.fixture(self.pn)

    def insert(self, table, **data):
        from psycopg import sql
        return self.c.execute(sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
            sql.Identifier(*table.split(".")), sql.SQL(",").join(map(sql.Identifier, data)),
            sql.SQL(",").join(sql.Placeholder() for _ in data)), tuple(data.values())).fetchone()[0]

    @staticmethod
    def obj(table, key):
        return {"bang": table, "id": str(key)}

    def fixture(self, pn):
        from psycopg.types.json import Jsonb

        sha, login = uuid.uuid4().hex * 2, self.admin[1]
        lh = self.insert("master.loai_hinh_doanh_thu", phap_nhan_id=pn, ma=uuid.uuid4().hex, ten="Loại hình MTQ tổng hợp")
        da = self.insert("master.du_an", phap_nhan_id=pn, ma_junsky=uuid.uuid4().hex, ten="Dự án MTQ tổng hợp")
        kh = self.insert("master.doi_tac", phap_nhan_id=pn, ten_phap_ly="Khách MTQ tổng hợp", ten_chuan_hoa=uuid.uuid4().hex)
        # hop_dong_kiem yêu cầu mapping đang mở đúng đối tác + pháp nhân,
        # không chỉ doi_tac.phap_nhan_id; giữ mapping này suốt vòng đời G2/G3/G4.
        self.insert("master.doi_tac_ma_junsky", doi_tac_id=kh, phap_nhan_id=pn,
                    object_id_junsky="MTQ_TEST_" + uuid.uuid4().hex, ten_junsky="Khách MTQ tổng hợp")
        mau = self.insert("master.crm_mau", phap_nhan_id=pn, loai_hinh_id=lh, ma_mau=uuid.uuid4().hex, tao_boi=login)
        tep = self.insert("master.crm_mau_tep", phap_nhan_id=pn, raw_sha256=sha, byte_length=1,
                          object_key="crm-mau/" + sha, bo_doc="MTQ_TEST", facts=Jsonb({}),
                          facts_sha256=sha, trang_thai_doc="DU", tao_boi=login)
        mv = self.insert("master.crm_mau_phien_ban", phap_nhan_id=pn, mau_id=mau, loai_hinh_id=lh,
                         phien_ban=1, tep_id=tep, ten_tep="mtq.docx", danh_muc_ref="MTQ_TEST", danh_muc_rev=1,
                         danh_muc_digest=sha, trang_thai="DRAFT", tai_boi=login)
        ax = self.insert("master.crm_mau_anh_xa", phien_ban_id=mv, phap_nhan_id=pn, revision=1,
                         ban_do=Jsonb([]), ban_do_sha256=sha, danh_muc_digest=sha, canh_bao=Jsonb([]),
                         so_chua_anh_xa=0, so_sai_kieu=0, tao_boi=login)
        kiem = self.insert("master.crm_mau_kiem_tra", phien_ban_id=mv, phap_nhan_id=pn, anh_xa_id=ax,
                           raw_sha256=sha, facts_sha256=sha, danh_muc_digest=sha, ban_do_sha256=sha,
                           ket_qua="DAT", kiem_boi=login)
        chuan = self.insert("master.crm_bo_chuan", phap_nhan_id=pn, du_an_id=da, giai_doan="MTQ_TEST", tao_boi=login)
        cv = self.insert("master.crm_bo_chuan_phien_ban", phap_nhan_id=pn, bo_chuan_id=chuan,
                         phien_ban=1, trang_thai="DRAFT", so_dong=1, dong_sha256=sha, lap_boi=login)
        bg = self.insert("master.crm_bao_gia", phap_nhan_id=pn, loai_hinh_id=lh, so_bao_gia="BG-2026-00001",
                         ngay=date(2026, 10, 26), tao_boi=login, trang_thai="NHAP", revision_hien_hanh=1)
        self.insert("master.crm_bao_gia_rev", phap_nhan_id=pn, bao_gia_id=bg, revision=1, du_an_id=da,
                    doi_tac_id=kh, du_lieu=Jsonb({}), du_lieu_sha256=sha, tinh=Jsonb({}), tao_boi=login)
        hd = self.insert("master.hop_dong", phap_nhan_id=pn, du_an_id=da, loai_hinh_dt_id=lh,
                         doi_tac_id=kh, loai="THUE_DAT", ma_noi_bo=uuid.uuid4().hex, so_hop_dong=uuid.uuid4().hex,
                         trang_thai="SOAN_THAO", crm_giao_ket="SOAN_THAO")
        soan = self.insert("master.crm_hd_soan", phap_nhan_id=pn, hop_dong_id=hd, bao_gia_id=bg,
                           bao_gia_revision=1, loai_hinh_id=lh, revision_hien_hanh=1,
                           trang_thai="SOAN_THAO", tao_boi=login)
        pinned = dict(mau_phien_ban_id=mv, anh_xa_id=ax, kiem_id=kiem, raw_sha256=sha, ban_do_sha256=sha,
                      danh_muc_ref="MTQ_TEST", danh_muc_rev=1, danh_muc_digest=sha, profile_phien_ban=1,
                      profile_sha256=sha, du_lieu_sha256=sha)
        rev = self.insert("master.crm_hd_soan_rev", phap_nhan_id=pn, soan_id=soan, revision=1,
                          nguon="MAU", byte_length=1, facts_sha256=sha, renderer="MTQ_TEST", du_lieu=Jsonb({}),
                          tao_boi=login, **pinned)
        self.c.execute("UPDATE master.crm_bao_gia SET trang_thai='DA_CHUYEN',hop_dong_id=%s WHERE id=%s", (hd, bg))
        self.c.execute("UPDATE master.hop_dong SET trang_thai='CHO_KY',crm_giao_ket='CHO_KY' WHERE id=%s", (hd,))
        self.c.execute("UPDATE master.crm_hd_soan SET trang_thai='CHO_KY' WHERE id=%s", (soan,))
        export = dict(phap_nhan_id=pn, revision=1, input_sha256=sha, docx_sha256=sha, docx_len=1,
                      pdf_sha256=sha, pdf_len=1, trang_thai="PDF_DAT", engine="MTQ_TEST", kiem_pdf=Jsonb({}), tao_boi=login)
        xb = self.insert("master.crm_gk_xuat", loai="BAO_GIA", bao_gia_id=bg, **export)
        xs = self.insert("master.crm_gk_xuat", loai="HOP_DONG", soan_id=soan, **export)
        ky = self.insert("master.crm_hd_ky", phap_nhan_id=pn, hop_dong_id=hd, soan_id=soan, revision=1,
                         soan_rev_id=rev, xuat_id=xs, g3_input_sha256=sha, g3_docx_sha256=sha, g3_docx_len=1,
                         g3_pdf_sha256=sha, g3_pdf_len=1, g3_engine="MTQ_TEST", tom_tat=Jsonb({}),
                         ky_pdf_sha256=sha, ky_pdf_len=1, ky_so_trang=1, ten_tep="mtq.pdf",
                         ngay_ky=date(2026, 10, 26), co_sua=False, tao_boi=login, **pinned)
        self.c.execute("UPDATE master.crm_hd_soan SET trang_thai='DA_KY' WHERE id=%s", (soan,))
        self.c.execute("UPDATE master.hop_dong SET trang_thai='DA_KY',crm_giao_ket='DA_KY' WHERE id=%s", (hd,))
        ban = self.insert("master.crm_da_ban", phap_nhan_id=pn, du_an_id=da, tao_boi=login)
        lo = self.insert("master.crm_da_ban_lo", phap_nhan_id=pn, da_ban_id=ban, ma="LO_MTQ", tao_boi=login)
        moc_id = uuid.uuid4()
        moc = self.insert("master.crm_da_moc", id=moc_id, phap_nhan_id=pn, da_ban_id=ban,
                          ma="DAM-" + str(moc_id), tao_boi=login)
        ids = (lh, mv, cv, bg, soan, ky, xb, xs, da, ban, lo, moc)
        objects = {key: self.obj("master.crm_gk_xuat" if key.startswith("x_") else key, obj_id)
                   for key, obj_id in zip(ALLOWED, ids)}
        return objects, {"HOP_DONG": hd, "DU_AN": da, "LOAI_HINH": lh, "KHACH": kh}

    def cau_hinh(self, scope="PHAP_NHAN", key=None, tick=True):
        self.actor(self.admin)
        v = self.nhap()
        for phong in (self.phong, self.phong2):
            for vai in nen.VAI:
                d = self.sua_nhap(v, "DONG", {"phong_id": phong, "vai": vai, "gioi_han_vnd": 0})
                if phong == self.phong and vai == "TRUONG_PHONG" and tick:
                    for action in ACTIONS:
                        module, man, hanh = action.split(":")
                        self.sua_nhap(v, "O", {"dong_id": d["id"], "module": module, "man": man,
                                              "hanh_dong": hanh, "cho_phep": True})
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

    def pairs(self, objects=None):
        return ((action, (objects or self.objects)[key]) for key, actions in ALLOWED.items() for action in actions)

    def denied(self, result, code):
        self.assertEqual(result["nguon"], "MA_TRAN")
        self.assertTrue(result["can_thiep"])
        self.assertIs(result["cho_phep"], False)
        self.assertEqual(result["ma"], code)

    def test_tung_cap_bat_dung_pham_vi_app_web(self):
        self.cau_hinh()
        self.c.execute("SET LOCAL ROLE app_web")
        for action, obj in self.pairs():
            with self.subTest(action=action, obj=obj):
                result = self.cong(action, obj)
                self.assertEqual(result["nguon"], "MA_TRAN")
                self.assertIs(result["cho_phep"], True)
                self.assertIsNone(result["so_tien_vnd"])

    def test_tung_cap_sai_phong(self):
        self.cau_hinh()
        for action, obj in self.pairs():
            with self.subTest(action=action, obj=obj):
                self.denied(self.cong(action, {**obj, "phong_id": self.phong2}), "MTQ_GAN_VAI")

    def test_tung_cap_khong_pham_vi_va_audit_dung_pn(self):
        self.cau_hinh(scope=None)
        before = self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0]
        for action, obj in self.pairs():
            self.denied(self.cong(action, obj), "MTQ_PHAM_VI")
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0], before)
        self.c.execute("SET LOCAL ROLE app_web")
        written = []
        for action, obj in self.pairs():
            key = self.c.execute("SELECT master.mtq_ghi_tu_choi_phien(%s,%s,%s::jsonb,NULL)",
                                 (uuid.uuid4(), action, json.dumps(obj))).fetchone()[0]
            written.append(key)
        self.c.execute("RESET ROLE")
        for key in written:
            self.assertEqual(self.c.execute("SELECT phap_nhan_id,ma FROM nhat_ky.mtq_tu_choi WHERE id=%s",
                                            (key,)).fetchone(), (self.pn, "MTQ_PHAM_VI"))

    def test_tung_cap_tick_tat_khong_fallback_vai_cfo_cu(self):
        self.cau_hinh(tick=False)
        for action, obj in self.pairs():
            with self.subTest(action=action, obj=obj):
                self.denied(self.cong(action, obj), "MTQ_CHUA_TICK")

    def test_tung_cap_sai_pham_vi_cung_pn(self):
        other = self.insert("master.du_an", phap_nhan_id=self.pn, ma_junsky=uuid.uuid4().hex,
                            ten="Dự án ngoài phạm vi MTQ tổng hợp")
        self.cau_hinh("DU_AN", other)
        for action, obj in self.pairs():
            with self.subTest(action=action, obj=obj):
                self.denied(self.cong(action, obj), "MTQ_PHAM_VI")

    def test_pn_tat_ke_ca_khi_pn_khac_bat_va_cap_sai(self):
        other, _ = self.fixture(self.pn2)
        self.actor(self.user)
        for action, obj in self.pairs():
            self.assertEqual(self.cong(action, obj)["nguon"], "CU")
        self.cau_hinh()
        for action, obj in self.pairs(other):
            with self.subTest(action=action, obj=obj):
                result = self.cong(action, obj)
                self.assertEqual(result["nguon"], "CU")
                self.assertFalse(result["can_thiep"])
                self.assertIsNone(result["cho_phep"])
                self.assertEqual(self.cong("CRM:TY_GIA:SUA", obj)["nguon"], "CU")

    def test_toan_bo_cap_ngoai_whitelist_catalog_bi_chan(self):
        self.cau_hinh()
        catalog = [f"{m}:{s}:{a}" for m, s, actions, _ in _CATALOG for a in actions.split()]
        for key, obj in self.objects.items():
            for action in catalog:
                if action not in ALLOWED[key]:
                    with self.subTest(action=action, obj=obj):
                        self.denied(self.cong(action, obj), "MTQ_CAN_RESOLVER_MTQ4")

    def test_id_khong_ton_tai_moi_bang_chan_khi_co_pn_bat(self):
        missing = [(action, {**obj, "id": str(uuid.uuid4())}) for action, obj in self.pairs()]
        self.actor(self.user)
        for action, obj in missing:
            self.assertEqual(self.cong(action, obj)["nguon"], "CU")
        self.cau_hinh()
        for action, obj in missing:
            with self.subTest(action=action, obj=obj):
                self.denied(self.cong(action, obj), "MTQ_CAN_RESOLVER_MTQ4")

    def test_h_ty_gia_va_g5_g6_van_cho_resolver(self):
        self.cau_hinh()
        h = self.obj("master.hop_dong", self.refs["HOP_DONG"])
        pn = self.obj("master.phap_nhan", self.pn)
        pairs = [(action, h) for action in (
            "CRM:G3_G4_SOAN_KY:XEM", "CRM:G5_G6_KIEM_KY:XEM", "M1:XEM_TIEN:XEM")]
        pairs += [(a, pn) for a in ("CRM:TY_GIA:XEM", "CRM:TY_GIA:SUA")]
        pairs += [(f"CRM:G5_G6_KIEM_KY:{a}", self.objects["master.crm_hd_ky"])
                  for a in ("XEM", "SUA", "KIEM", "DUYET")]
        for action, obj in pairs:
            with self.subTest(action=action, obj=obj):
                self.denied(self.cong(action, obj), "MTQ_CAN_RESOLVER_MTQ4")

    def test_pham_vi_hep_tu_fk_khong_buoc_cap_pn(self):
        for scope, ref in self.refs.items():
            with self.subTest(scope=scope), self.c.transaction(force_rollback=True):
                self.cau_hinh(scope, ref)
                targets = {"master.crm_bao_gia", "master.crm_hd_soan", "master.crm_hd_ky", "x_bao_gia", "x_hop_dong"}
                if scope == "LOAI_HINH":
                    targets.update(("master.loai_hinh_doanh_thu", "master.crm_mau_phien_ban"))
                if scope == "DU_AN":
                    targets.update(("master.du_an", "master.crm_bo_chuan_phien_ban", "master.crm_da_ban",
                                    "master.crm_da_ban_lo", "master.crm_da_moc"))
                for key in targets:
                    for action in ALLOWED[key]:
                        self.assertIs(self.cong(action, self.objects[key])["cho_phep"], True)

    def test_bao_gia_revision_hien_hanh_khac_ban_xuat_ghim(self):
        from psycopg.types.json import Jsonb

        sha, login = uuid.uuid4().hex * 2, self.admin[1]
        da2 = self.insert("master.du_an", phap_nhan_id=self.pn, ma_junsky=uuid.uuid4().hex, ten="Dự án revision mới")
        bg = self.insert("master.crm_bao_gia", phap_nhan_id=self.pn, loai_hinh_id=self.refs["LOAI_HINH"],
                         so_bao_gia="BG-2026-00002", ngay=date(2026, 10, 26), tao_boi=login,
                         trang_thai="NHAP", revision_hien_hanh=1)
        for rev, da in ((1, self.refs["DU_AN"]), (2, da2)):
            self.insert("master.crm_bao_gia_rev", phap_nhan_id=self.pn, bao_gia_id=bg, revision=rev, du_an_id=da,
                        doi_tac_id=self.refs["KHACH"], du_lieu=Jsonb({}), du_lieu_sha256=sha, tinh=Jsonb({}), tao_boi=login)
        self.c.execute("UPDATE master.crm_bao_gia SET revision_hien_hanh=2 WHERE id=%s", (bg,))
        xb = self.insert("master.crm_gk_xuat", phap_nhan_id=self.pn, loai="BAO_GIA", bao_gia_id=bg,
                         revision=1, input_sha256=sha, docx_sha256=sha, docx_len=1, pdf_sha256=sha, pdf_len=1,
                         trang_thai="PDF_DAT", engine="MTQ_TEST", kiem_pdf=Jsonb({}), tao_boi=login)
        for da, bg_allowed in ((self.refs["DU_AN"], False), (da2, True)):
            with self.subTest(du_an=da), self.c.transaction(force_rollback=True):
                self.cau_hinh("DU_AN", da)
                result = self.cong("CRM:G2_BAO_GIA:XEM", self.obj("master.crm_bao_gia", bg))
                exported = self.cong("CRM:G2_BAO_GIA:XEM", self.obj("master.crm_gk_xuat", xb))
                self.assertIs(result["cho_phep"], bg_allowed)
                self.assertIs(exported["cho_phep"], not bg_allowed)
                self.denied(exported if bg_allowed else result, "MTQ_PHAM_VI")

    def test_acl_khong_doi_public_cam_app_web_duoc(self):
        self.assertEqual(self.acl_before, self.acl_after)
        for signature in SIGNATURES:
            self.assertFalse(self.c.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_proc p, "
                "LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a "
                "WHERE p.oid=%s::regprocedure AND a.grantee=0 AND a.privilege_type='EXECUTE')", (signature,)).fetchone()[0])
            self.assertTrue(self.c.execute("SELECT has_function_privilege('app_web',%s,'EXECUTE')", (signature,)).fetchone()[0])


if __name__ == "__main__":
    unittest.main()
