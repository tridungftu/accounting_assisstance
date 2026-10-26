"""MTQ-4f1a: resolver phạm vi M4; không mở Duyệt có tiền.

PG dùng DSN quản trị KHO_PG_DSN_TEST, tự tạo kho_test_* và giữ DB cho lead.
Fixture giả đi qua trigger/FK thật, không tắt trigger hoặc gọi dịch vụ ngoài.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import re
import unittest
import uuid

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_ma_tran_tham_quyen import _CATALOG
from kho_tri_thuc.k2.sql_mtq_cong import MTQ_CONG_D_SQL, MTQ_CONG_E_SQL
from tests import test_mtq_sql as nen
from tests import test_mtq_crm_resolver_sql as crm

SIGNATURES = crm.SIGNATURES

ROOT = Path(__file__).resolve().parents[1]
DSN = os.environ.get("KHO_PG_DSN_TEST")
ALLOWED = {
    "master.du_an": ("M4:HO_SO:XEM", "M4:HO_SO:LAP", "M4:HO_SO:SUA"),
    "master.hop_dong": tuple("M4:HO_SO:" + a for a in ("XEM", "LAP", "SUA", "KIEM", "HUY")),
    "m4.tep": ("M4:HO_SO:XEM", "M4:02A_REVIEW:XEM", "M4:02A_REVIEW:KIEM"),
    "m4.dot": (
        "M4:HO_SO:XEM", "M4:HO_SO:SUA", "M4:02A_REVIEW:XEM", "M4:02A_REVIEW:KIEM",
        "M4:02B_CHUNG_TU:XEM", "M4:02B_CHUNG_TU:SUA", "M4:02B_CHUNG_TU:KIEM",
        "M4:02C_DUYET:XEM", "M4:02C_DUYET:KIEM",
        "M4:04_REQUEST_NHAP:XEM", "M4:04_REQUEST_NHAP:LAP", "M4:04_REQUEST_NHAP:KIEM"),
    "m4.review_run": tuple("M4:02A_REVIEW:" + a for a in ("XEM", "SUA", "KIEM")),
    "m4.chung_tu_run": tuple("M4:02B_CHUNG_TU:" + a for a in ("XEM", "SUA", "KIEM")),
    "m4.duyet_phien_ban": (
        "M4:02C_DUYET:XEM", "M4:02C_DUYET:LAP", "M4:02C_DUYET:SUA", "M4:02C_DUYET:KIEM",
        "M4:04_REQUEST_NHAP:XEM", "M4:04_REQUEST_NHAP:LAP", "M4:04_REQUEST_NHAP:KIEM"),
    # K chỉ có nhánh giải phạm vi, không whitelist DUYET trước MTQ-4f3a.
    "m4.duyet_ket_luan": (),
    "m4.duyet_pdf": ("M4:PDF_DA_DUYET:XEM",),
    "m4.duyet_kt_cho": (
        "M4:03A_KE_TOAN:XEM", "M4:03A_KE_TOAN:SUA", "M4:03A_KE_TOAN:KIEM", "M4:PDF_DA_DUYET:XEM"),
    "m4.request_y_dinh": tuple("M4:04_REQUEST_NHAP:" + a for a in ("XEM", "LAP", "KIEM")),
}
ACTIONS = sorted({a for actions in ALLOWED.values() for a in actions})


class MtqM4ResolverTinh(unittest.TestCase):
    def test_registry_chi_append_khong_ghim_cuoi(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# MTQ-4f1a — CD-012:"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker)[0], PM.__file__, "exec"), old)
        previous = old["PG_MIGRATIONS"]
        self.assertEqual(PM.PG_MIGRATIONS[:len(previous)], previous)
        self.assertIs(PM.PG_MIGRATIONS[len(previous)], MTQ_CONG_E_SQL)
        self.assertEqual(sum(m is MTQ_CONG_E_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_so_toan_than_ham_quyet_dinh_m0047(self):
        # Bỏ đúng ba phần thêm của E rồi so TOÀN thân hàm với M0047.
        new = MTQ_CONG_E_SQL[0].replace(
            "hd_text text; xuat_loai text; m4_ho_tro boolean := false;", "hd_text text; xuat_loai text;")
        start = new.index("                    -- MTQ-4f1a: phạm vi")
        end = new.index("                    IF NOT EXISTS (SELECT 1 FROM master.mtq_kich_hoat", start)
        new = new[:start] + "                    END IF;\n" + new[end:]
        start = new.index(" OR\n                            -- MTQ-4f1a:")
        end = new.index("), false) THEN", start)
        new = new[:start] + new[end:]
        self.assertEqual(new, MTQ_CONG_D_SQL[0])

    def test_so_toan_than_ham_audit_m0047(self):
        new = MTQ_CONG_E_SQL[1]
        start = new.index("            ELSIF p_doi_tuong->>'bang' = 'm4.dot' THEN")
        end = new.index("            END IF;\n            SELECT g.phong_id", start)
        self.assertEqual(new[:start] + new[end:], MTQ_CONG_D_SQL[1])

    def test_chu_ky_acl_search_path_khong_doi(self):
        for new, old in zip(MTQ_CONG_E_SQL[:2], MTQ_CONG_D_SQL[:2]):
            self.assertEqual(new.split("DECLARE")[0], old.split("DECLARE")[0])
            self.assertIn("CREATE OR REPLACE FUNCTION", new)
            self.assertIn("SECURITY DEFINER", new)
            self.assertIn("SET search_path = pg_catalog, master, nhat_ky, pg_temp", new)
        self.assertEqual(MTQ_CONG_E_SQL[2:], MTQ_CONG_D_SQL[2:])
        self.assertNotRegex(
            "\n".join(MTQ_CONG_E_SQL),
            r"(?im)(?:^\s*EXECUTE\b(?!\s+ON\s+FUNCTION\b)|\bEXECUTE\s+(?:format\s*\(|'|\()|\b(?:ALTER TABLE|CREATE TABLE|DROP ))")

    def test_whitelist_chinh_xac_tung_cap_va_catalog(self):
        catalog = {f"{m}:{s}:{a}" for m, s, actions, _ in _CATALOG for a in actions.split()}
        section = MTQ_CONG_E_SQL[0].split("-- MTQ-4f1a: chỉ cặp", 1)[1].split("), false) THEN", 1)[0]
        groups = re.findall(r"\(p_doi_tuong->>'bang' = '([^']+)' AND p_hanh_dong (.*?)(?= OR\n|-- K)", section, re.S)
        actual = {t: tuple(re.findall(r"'(M4:[^']+)'", clause)) for t, clause in groups}
        self.assertEqual(actual, {t: actions for t, actions in ALLOWED.items() if actions})
        self.assertTrue(set(ACTIONS) <= catalog)
        self.assertNotIn("M4:02C_DUYET:DUYET", section)
        self.assertNotIn("03B_DOI_CHIEU", section)
        self.assertIn("module_hd = 'M4' AND m4_ho_tro", MTQ_CONG_E_SQL[0])

    def test_resolver_audit_du_11_doi_tuong_va_fk(self):
        for table in ALLOWED:
            for sql in MTQ_CONG_E_SQL[:2]:
                self.assertIn(f"p_doi_tuong->>'bang' = '{table}'", sql)
                self.assertIn(f"FROM {table}", sql)
        for ref in ("h.module_chu = 'M4'", "v.dot_id = x.dot_id", "v.hop_dong_id = x.hop_dong_id",
                    "d.hop_dong_id = x.hop_dong_id", "a.phap_nhan_id = x.phap_nhan_id",
                    "t.raw_sha256 = r.raw_sha256", "r.hop_dong_id IS NULL OR h.id IS NOT NULL",
                    "r.dot_id IS NULL OR d.id IS NOT NULL", "k.revision = x.ket_luan_revision"):
            self.assertIn(ref, MTQ_CONG_E_SQL[0])
        self.assertIn("JOIN master.du_an a ON a.id = d.du_an_id", MTQ_CONG_E_SQL[1])

    def test_b6_chi_du_an_lap_khong_pn_tep_hay_chon_tuy_y(self):
        self.assertIn("M4:HO_SO:LAP", ALLOWED["master.du_an"])
        self.assertNotIn("M4:HO_SO:LAP", ALLOWED["m4.tep"])
        self.assertNotIn("'M4:", MTQ_CONG_E_SQL[0].split(
            "p_doi_tuong->>'bang' = 'master.phap_nhan' AND doi_tuong_ho_tro", 1)[1].split(" OR", 1)[0])
        branch = MTQ_CONG_E_SQL[0].split("ELSIF p_doi_tuong->>'bang' = 'm4.tep' THEN")[1].split("ELSIF", 1)[0]
        self.assertNotIn("hop_dong", branch)
        self.assertNotIn("LIMIT", branch)

    def test_utf8_khong_bom_lf_va_hang_literal(self):
        paths = (Path(PM.__file__), ROOT / "src/kho_tri_thuc/k2/sql_mtq_cong.py", Path(__file__))
        for path in paths:
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn("\ufffd", raw.decode("utf-8"))
        self.assertNotIn(b"\r", paths[0].read_bytes())
        tree = ast.parse(paths[1].read_text(encoding="utf-8"))
        values = {a.targets[0].id: ast.literal_eval(a.value) for a in tree.body}
        self.assertEqual(values["MTQ_CONG_E_SQL"], MTQ_CONG_E_SQL)


@unittest.skipUnless(DSN and nen.psycopg is not None, "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class MtqM4ResolverPostgres(unittest.TestCase):
    nguoi = nen.MtqPostgres.nguoi
    actor = nen.MtqPostgres.actor
    ghi = nen.MtqPostgres.ghi
    nhap = nen.MtqPostgres.nhap
    sua_nhap = nen.MtqPostgres.sua_nhap
    san_sang = nen.MtqPostgres.san_sang
    insert = crm.MtqCrmResolverPostgres.insert
    obj = staticmethod(crm.MtqCrmResolverPostgres.obj)
    acl = classmethod(crm.MtqCrmResolverPostgres.acl.__func__)

    @classmethod
    def setUpClass(cls):
        from psycopg import sql
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.ha_tang import postgres

        cls.db = "kho_test_mtq_m4_resolver_" + uuid.uuid4().hex[:12]
        with nen.psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_web') "
                          "THEN CREATE ROLE app_web NOLOGIN; END IF; END $$")
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(cls.db)))
        cls.c = nen.psycopg.connect(make_conninfo(DSN, dbname=cls.db), autocommit=True)
        cls.addClassCleanup(cls.c.close)
        position = next(i for i, m in enumerate(PM.PG_MIGRATIONS) if m is MTQ_CONG_E_SQL)
        postgres.migrate(cls.c, target=position)
        cls.acl_before = cls.acl()
        postgres.migrate(cls.c, target=position + 1)
        cls.acl_after = cls.acl()
        postgres.migrate(cls.c)

    def setUp(self):
        nen.MtqPostgres.setUp(self)
        self.objects, self.refs = self.fixture(self.pn)

    def fixture(self, pn):
        from psycopg.types.json import Jsonb

        sha, login, aid = uuid.uuid4().hex * 2, self.admin[1], self.admin[0]
        data = dict(phap_nhan_id=pn)
        da = self.insert("master.du_an", **data, ma_junsky=uuid.uuid4().hex, ten="Dự án M4 tổng hợp")
        lh = self.insert("master.loai_hinh_doanh_thu", **data, ma=uuid.uuid4().hex, ten="Loại hình M4 giả")
        kh = self.insert("master.doi_tac", **data, ten_phap_ly="Đối tác M4 giả", ten_chuan_hoa=uuid.uuid4().hex)
        # hop_dong_kiem đòi mapping mở đúng PN, không chỉ FK tới doi_tac.
        self.insert("master.doi_tac_ma_junsky", **data, doi_tac_id=kh, object_id_junsky=uuid.uuid4().hex)
        hd = self.insert("master.hop_dong", **data, du_an_id=da, loai_hinh_dt_id=lh, doi_tac_id=kh,
                         loai="XAY_DUNG", module_chu="M4", ma_noi_bo=uuid.uuid4().hex, so_hop_dong=uuid.uuid4().hex)
        self.c.execute("INSERT INTO m4.ho_so_hop_dong (hop_dong_id,phap_nhan_id,du_an_id,ten,tao_boi) "
                       "VALUES (%s,%s,%s,'Hồ sơ M4 giả',%s)", (hd, pn, da, login))
        d = self.insert("m4.dot", hop_dong_id=hd, du_an_id=da, so_dot=1, tao_boi=login)
        t = self.insert("m4.tep", **data, du_an_id=da, vai_tro_tai_lieu="HO_SO_DOT", raw_sha256=sha,
                        byte_length=1, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        ten_goc="gia.xlsx", object_key="m4-raw/" + sha, tao_boi=login)
        context = dict(phap_nhan_id=pn, du_an_id=da, hop_dong_id=hd, dot_id=d)
        run = dict(**context, basis=Jsonb({}), basis_sha256=sha, engine="MTQ_TEST", engine_sha256=sha,
                   yeu_cau=Jsonb({}), yeu_cau_sha256=sha, quyen="SOAN", tao_boi=login, tao_boi_id=aid)
        r = self.insert("m4.review_run", **run, tep_id=t, raw_sha256=sha, che_do="L1_L2",
                        hanh_dong="REVIEW_CHAY", khoa=uuid.uuid4().hex)
        c = self.insert("m4.chung_tu_run", **run, revision=0, hanh_dong="CHUNG_TU_CHAY", khoa=uuid.uuid4().hex)
        # nop_duyet_phien_ban sinh bản 1 qua trigger thật; không chèn bản 1 thủ công.
        self.insert("m4.nop", hop_dong_id=hd, du_an_id=da, dot_id=d, revision_ho_so=1, revision_dot=1,
                    snapshot=Jsonb({}), digest=sha, nop_boi=login, nop_boi_id=aid)
        v = self.c.execute("SELECT id FROM m4.duyet_phien_ban WHERE dot_id=%s", (d,)).fetchone()[0]
        k = self.insert("m4.duyet_ket_luan", **context, phien_ban_id=v, revision=1, graph=Jsonb({}),
                        graph_sha256=sha, l3_run_id=c, l2_run_id=r, tien_te="VND", so_xin_thanh_toan="999",
                        xu_ly_phat_hien=Jsonb([]), de_xuat_nguon=Jsonb({}), thieu=Jsonb([]),
                        canh_bao=Jsonb([]), quyen="REVIEW", tao_boi=login, tao_boi_id=aid)
        p = self.insert("m4.duyet_pdf", **context, phien_ban_id=v, ket_luan_id=k, ket_luan_revision=1,
                        graph_sha256=sha, vai="HO_SO_DOT_DA_DUYET", ten="gia.pdf", media_type="application/pdf",
                        raw_sha256=sha, byte_length=1, object_key="m4-raw/" + sha, tai_boi=login, tai_boi_id=aid)
        qd = self.insert("m4.duyet_quyet_dinh", **context, phien_ban_id=v, ket_luan_id=k, graph_sha256=sha,
                         ly_do="Quyết định giả cho fixture phạm vi", duyet_boi=login, duyet_boi_id=aid)
        seal = self.insert("m4.duyet_seal", **context, phien_ban_id=v, quyet_dinh_id=qd, ket_luan_id=k,
                           pdf_id=p, graph_sha256=sha, pdf_sha256=sha, so_lieu=Jsonb({}),
                           so_lieu_sha256=sha, tao_boi=login, tao_boi_id=aid)
        a = self.insert("m4.duyet_kt_cho", **context, nguon="M4", trang_thai="CHO_XAC_NHAN", seal_dau_id=seal)
        ax = self.insert("m4.request_anh_xa", **data, nguoi_dung_id=aid, request_dang_nhap=login,
                         can_cu="Mapping giả cho test", revision=1, tao_boi=login, tao_boi_id=aid)
        yid = uuid.uuid4()
        q = self.insert("m4.request_y_dinh", **context, id=yid, phien_ban_id=v, seal_id=seal, nhanh="GOC",
                        actor_id=aid, actor=login, anh_xa_id=ax, anh_xa_revision=1, nguoi_tao=login,
                        canonical=Jsonb({}), canonical_sha256=sha, idem_key="m4-request:" + str(yid),
                        cau_hinh_sha256=sha, khoa_ref="MTQ_TEST", nhom="MTQ_TEST", nhom_phien_ban=1,
                        so_tien="999", tien_te="VND", pdf_id=p, pdf_sha256=sha, pdf_byte_length=1,
                        trang_thai="MOI")
        ids = (da, hd, t, d, r, c, v, k, p, a, q)
        return {table: self.obj(table, key) for table, key in zip(ALLOWED, ids)}, {
            "DU_AN": da, "HOP_DONG": hd, "LOAI_HINH": lh, "KHACH": kh}

    def cau_hinh(self, scope="PHAP_NHAN", key=None, tick=True):
        self.actor(self.admin)
        v = self.nhap()
        for phong in (self.phong, self.phong2):
            for vai in nen.VAI:
                row = self.sua_nhap(v, "DONG", {"phong_id": phong, "vai": vai, "gioi_han_vnd": 0})
                if phong == self.phong and vai == "TRUONG_PHONG" and tick:
                    # Cả DUYET được tick để chứng minh caller không thể giả tiền mở K.
                    for action in [*ACTIONS, "M4:02C_DUYET:DUYET"]:
                        module, man, hanh = action.split(":")
                        self.sua_nhap(v, "O", {"dong_id": row["id"], "module": module, "man": man,
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

    def pairs(self, objects=None):
        return ((action, (objects or self.objects)[table]) for table, actions in ALLOWED.items() for action in actions)

    def cong(self, action, obj, money=None):
        return self.c.execute("SELECT master.mtq_quyet_dinh_phien(%s,%s::jsonb,%s)",
                              (action, json.dumps(obj), money)).fetchone()[0]

    def denied(self, result, code="MTQ_CAN_RESOLVER_MTQ4"):
        self.assertEqual(result["nguon"], "MA_TRAN")
        self.assertIs(result["cho_phep"], False)
        self.assertEqual(result["ma"], code)

    def test_tung_cap_dung_app_web_khong_can_assignment_cu(self):
        self.cau_hinh()
        self.c.execute("SET LOCAL ROLE app_web")
        for action, obj in self.pairs():
            with self.subTest(action=action, obj=obj):
                self.assertIs(self.cong(action, obj)["cho_phep"], True)

    def test_tick_tat_chan_du_vai_cu_cfo(self):
        self.cau_hinh(tick=False)
        for action, obj in self.pairs():
            self.denied(self.cong(action, obj), "MTQ_CHUA_TICK")

    def test_pn_tat_cu_ke_ca_pn_khac_bat_va_cap_sai(self):
        other, _ = self.fixture(self.pn2)
        self.actor(self.user)
        for action, obj in self.pairs():
            self.assertEqual(self.cong(action, obj)["nguon"], "CU")
        self.cau_hinh()
        for action, obj in self.pairs(other):
            self.assertEqual(self.cong(action, obj)["nguon"], "CU")
            self.assertEqual(self.cong("M4:02C_DUYET:DUYET", obj, 0)["nguon"], "CU")

    def test_sai_phong_va_phong_mo_ho(self):
        self.cau_hinh()
        for action, obj in self.pairs():
            self.denied(self.cong(action, {**obj, "phong_id": self.phong2}), "MTQ_GAN_VAI")
        self.actor(self.admin)
        self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]), "phap_nhan_id": str(self.pn),
                            "phong_id": self.phong2, "vai": "NGUOI_XEM"})
        self.actor(self.user)
        self.denied(self.cong("M4:HO_SO:LAP", self.objects["master.du_an"]), "MTQ_PHONG_MO_HO")

    def test_sai_du_an_cung_pn(self):
        da = self.insert("master.du_an", phap_nhan_id=self.pn, ma_junsky=uuid.uuid4().hex, ten="Ngoài phạm vi giả")
        self.cau_hinh("DU_AN", da)
        for action, obj in self.pairs():
            self.denied(self.cong(action, obj), "MTQ_PHAM_VI")

    def test_pham_vi_hep_tu_fk_khong_mo_sang_hd_cung_du_an(self):
        for scope, ref in self.refs.items():
            with self.subTest(scope=scope), self.c.transaction(force_rollback=True):
                self.cau_hinh(scope, ref)
                for action, obj in self.pairs():
                    project_only = obj["bang"] in ("master.du_an", "m4.tep")
                    if scope != "DU_AN" and project_only:
                        self.denied(self.cong(action, obj), "MTQ_PHAM_VI")
                    else:
                        self.assertIs(self.cong(action, obj)["cho_phep"], True)
                if scope == "HOP_DONG":
                    hd2 = self.insert("master.hop_dong", phap_nhan_id=self.pn, du_an_id=self.refs["DU_AN"],
                                      loai="XAY_DUNG", module_chu="M4",
                                      ma_noi_bo=uuid.uuid4().hex, so_hop_dong=uuid.uuid4().hex)
                    self.denied(self.cong("M4:HO_SO:XEM", self.obj("master.hop_dong", hd2)), "MTQ_PHAM_VI")

    def test_tat_ca_cap_m4_ngoai_whitelist_va_cheo_module(self):
        self.cau_hinh()
        catalog = [f"{m}:{s}:{a}" for m, s, actions, _ in _CATALOG for a in actions.split()]
        for table, obj in self.objects.items():
            for action in catalog:
                # DA giữ whitelist CRM cũ; H M4 không thuộc CRM.
                if action in ALLOWED[table] or (table == "master.du_an" and action.startswith("CRM:")):
                    continue
                with self.subTest(action=action, table=table):
                    self.denied(self.cong(action, obj))

    def test_hd_crm_master_muon_khong_mo_cap_m4(self):
        self.cau_hinh()
        for loai in ("XAY_DUNG", "THUE_DAT", "VAY", "MUA"):
            hd = self.insert("master.hop_dong", phap_nhan_id=self.pn, du_an_id=self.refs["DU_AN"],
                             loai=loai, ma_noi_bo=uuid.uuid4().hex, so_hop_dong=uuid.uuid4().hex)
            for action in ALLOWED["master.hop_dong"]:
                self.denied(self.cong(action, self.obj("master.hop_dong", hd)))
        for action in ("CRM:TIEP_NHAN:XEM", "CRM:FILE_SOAT:XEM", "M1:TIEN:SUA"):
            self.denied(self.cong(action, self.objects["master.hop_dong"]))

    def test_id_thieu_va_b6_khong_du_an(self):
        self.cau_hinh()
        for table in ALLOWED:
            self.denied(self.cong((ALLOWED[table] or ("M4:02C_DUYET:DUYET",))[0], self.obj(table, uuid.uuid4())))
        for obj in ({}, {"bang": "master.du_an"}, self.obj("master.phap_nhan", self.pn)):
            self.denied(self.cong("M4:HO_SO:LAP", obj))
        self.assertIs(self.cong("M4:HO_SO:LAP", self.objects["master.du_an"])["cho_phep"], True)

    def test_k_chua_nhan_tien_caller_ke_ca_tick_duyet(self):
        self.cau_hinh()
        for money in (None, 0, 1, 999, 999999999):
            self.denied(self.cong("M4:02C_DUYET:DUYET", self.objects["m4.duyet_ket_luan"], money))

    def clone_run(self, table, source, **changes):
        from psycopg import sql

        changes.update(id=str(uuid.uuid4()), khoa=uuid.uuid4().hex)
        return self.c.execute(sql.SQL(
            "INSERT INTO {table} SELECT (jsonb_populate_record(NULL::{table}, "
            "to_jsonb(r) || %s::jsonb)).* FROM {table} r WHERE id=%s RETURNING id"
        ).format(table=sql.Identifier(*table.split("."))), (json.dumps(changes), source)).fetchone()[0]

    def test_l1_khong_hd_chi_co_pham_vi_du_an_tu_tep(self):
        table = "m4.review_run"
        r = self.clone_run(table, self.objects[table]["id"], hop_dong_id=None, dot_id=None, che_do="L1")
        for scope in ("DU_AN", "HOP_DONG"):
            with self.subTest(scope=scope), self.c.transaction(force_rollback=True):
                self.cau_hinh(scope, self.refs[scope])
                for action in ALLOWED[table]:
                    result = self.cong(action, self.obj(table, r))
                    if scope == "DU_AN":
                        self.assertIs(result["cho_phep"], True)
                    else:
                        self.denied(result, "MTQ_PHAM_VI")

    def test_fk_tung_cot_hop_le_nhung_khac_hd_dot_van_chan(self):
        # FK dot_id độc lập vẫn nhận đợt của HĐ khác cùng dự án; resolver phải chặn.
        hd = self.insert("master.hop_dong", phap_nhan_id=self.pn, du_an_id=self.refs["DU_AN"],
                         loai="XAY_DUNG", module_chu="M4",
                         ma_noi_bo=uuid.uuid4().hex, so_hop_dong=uuid.uuid4().hex)
        self.c.execute("INSERT INTO m4.ho_so_hop_dong (hop_dong_id,phap_nhan_id,du_an_id,ten,tao_boi) "
                       "VALUES (%s,%s,%s,'Hồ sơ khác giả',%s)",
                       (hd, self.pn, self.refs["DU_AN"], self.admin[1]))
        dot = self.insert("m4.dot", hop_dong_id=hd, du_an_id=self.refs["DU_AN"], so_dot=1, tao_boi=self.admin[1])
        bad = {table: self.obj(table, self.clone_run(table, self.objects[table]["id"], dot_id=str(dot)))
               for table in ("m4.review_run", "m4.chung_tu_run")}
        self.cau_hinh()
        for table, obj in bad.items():
            for action in ALLOWED[table]:
                self.denied(self.cong(action, obj))

    def test_thu_hoi_kiem_lai_va_audit_sau_rollback(self):
        self.cau_hinh()
        obj, action = self.objects["m4.dot"], "M4:HO_SO:SUA"
        self.assertIs(self.cong(action, obj)["cho_phep"], True)
        self.actor(self.admin)
        g = self.c.execute("SELECT id,revision FROM master.mtq_gan_vai WHERE nguoi_dung_id=%s "
                           "AND phap_nhan_id=%s AND thu_hoi_luc IS NULL", (self.user[0], self.pn)).fetchone()
        self.ghi("THU_HOI_VAI", {"id": str(g[0])}, g[1])
        self.actor(self.user)
        with self.c.transaction(force_rollback=True):
            self.denied(self.cong(action, obj), "MTQ_GAN_VAI")
        request = uuid.uuid4()
        with self.c.transaction():
            key = self.c.execute("SELECT master.mtq_ghi_tu_choi_phien(%s,%s,%s::jsonb,NULL)",
                                 (request, action, json.dumps(obj))).fetchone()[0]
        self.assertEqual(self.c.execute("SELECT phap_nhan_id,ma FROM nhat_ky.mtq_tu_choi WHERE id=%s",
                                        (key,)).fetchone(), (self.pn, "MTQ_GAN_VAI"))

    def test_tu_choi_khong_ghi_khi_hoi_audit_dung_pn_va_idempotent(self):
        self.cau_hinh(scope=None)
        before = self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0]
        pairs = [*self.pairs(), ("M4:02C_DUYET:DUYET", self.objects["m4.duyet_ket_luan"])]
        for action, obj in pairs:
            self.denied(self.cong(action, obj),
                        "MTQ_CAN_RESOLVER_MTQ4" if obj["bang"] == "m4.duyet_ket_luan" else "MTQ_PHAM_VI")
        self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0], before)
        self.c.execute("SET LOCAL ROLE app_web")
        keys = []
        for action, obj in pairs:
            request = uuid.uuid4()
            args = (request, action, json.dumps(obj))
            key = self.c.execute("SELECT master.mtq_ghi_tu_choi_phien(%s,%s,%s::jsonb,NULL)", args).fetchone()[0]
            self.assertEqual(self.c.execute("SELECT master.mtq_ghi_tu_choi_phien(%s,%s,%s::jsonb,NULL)",
                                            args).fetchone()[0], key)
            keys.append(key)
        self.c.execute("RESET ROLE")
        for key in keys:
            self.assertEqual(self.c.execute("SELECT phap_nhan_id FROM nhat_ky.mtq_tu_choi WHERE id=%s",
                                            (key,)).fetchone()[0], self.pn)

    def test_acl_owner_public_app_web_khong_doi(self):
        self.assertEqual(self.acl_before, self.acl_after)
        for signature in SIGNATURES:
            self.assertFalse(self.c.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_proc p, "
                "LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a "
                "WHERE p.oid=%s::regprocedure AND a.grantee=0 AND a.privilege_type='EXECUTE')",
                (signature,)).fetchone()[0])
            self.assertTrue(self.c.execute("SELECT has_function_privilege('app_web',%s,'EXECUTE')",
                                           (signature,)).fetchone()[0])


if __name__ == "__main__":
    unittest.main()
