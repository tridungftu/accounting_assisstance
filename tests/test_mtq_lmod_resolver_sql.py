"""MTQ-4i-b1: rS/rA, NGUON và oracle nguyên thân hai cổng M0057.

PG chỉ tạo kho_test_* từ KHO_PG_DSN_TEST quản trị, không mở server/xóa DB.
Fixture dùng trigger thật; đọc M0039/M0049 và schema/trigger nguồn M0014–16.
Không nối caller; retarget cần hai lần gọi, bên ghi thuộc lát 4i-d.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import unittest
import uuid

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2.sql_mtq_cong import MTQ_CONG_G_SQL, MTQ_CONG_H_SQL
from tests import test_mtq_cong_c_sql as cong
from tests import test_mtq_sql as nen
from tests import test_mtq_nguon_scope_sql as nguon

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = "master.mtq_giai_doi_tuong_tap(text,jsonb)"
OLD_TAP = "master.mtq_giai_doi_tuong_tap_4ib1_m0057"
OLD_DECISION = "master.mtq_quyet_dinh_phien_4ib1_m0057"
OLD_AUDIT = "master.mtq_ghi_tu_choi_phien_4ib1_m0057"
ACTION = "M2:HOA_DON:DUYET"
SOURCE_ACTIONS = (
    "M2:HOA_DON:XEM", "M2:HOA_DON:LAP", ACTION, "M2:HOA_DON:HUY", "M2:NGUON_THO:XEM",
    "M5:KHO:XEM", "M5:KHO:LAP", "M5:KHO:DUYET", "M5:NGUON_THO:XEM",
)


class MtqLmodResolverTinh(unittest.TestCase):
    def test_registry_append_khong_ghim_cuoi(self):
        source = Path(PM.__file__).read_text(encoding="utf-8")
        marker = "# MTQ-4i-b1 — CD-012: resolver"
        self.assertEqual(source.count(marker), 1)
        old = {"__name__": PM.__name__, "__package__": PM.__package__}
        exec(compile(source.split(marker, 1)[0], PM.__file__, "exec"), old)
        previous = old["PG_MIGRATIONS"]
        self.assertEqual(PM.PG_MIGRATIONS[:len(previous)], previous)
        self.assertIs(PM.PG_MIGRATIONS[len(previous)], MTQ_CONG_H_SQL)
        self.assertEqual(sum(m is MTQ_CONG_H_SQL for m in PM.PG_MIGRATIONS), 1)
        self.assertIs(PM.M00xx_MTQ_CONG_H, MTQ_CONG_H_SQL)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))

    def test_hai_cong_chi_them_tieu_thu_nguon_con_lai_nguyen_byte_m0057(self):
        for new, old in zip(MTQ_CONG_H_SQL[1:], MTQ_CONG_G_SQL[1:3]):
            audit = "DECLARE login" in old
            indent = "                    " if audit else "                            "
            scope_indent = "                                        " if audit else "                                                "
            edits = (
                ("scope_loai text;", "scope_loai text; nguon_khoa text;"),
                ("loai := giai->>'loai';", "loai := giai->>'loai';\n" + indent + "nguon_khoa := giai->>'nguon_khoa';"),
                ("OR (s.loai = 'KHACH' AND s.khoa = khach::text))",
                 "OR (s.loai = 'KHACH' AND s.khoa = khach::text)\n" + scope_indent
                 + "OR (s.loai = 'NGUON' AND s.khoa = nguon_khoa))"),
                ("WHEN 'LOAI_HINH' THEN 3 WHEN 'KHACH' THEN 4 ELSE 5 END",
                 "WHEN 'LOAI_HINH' THEN 3 WHEN 'KHACH' THEN 4 WHEN 'NGUON' THEN 5 ELSE 6 END"),
            )
            restored = new
            for before, after in edits:
                self.assertEqual(restored.count(after), 1)
                restored = restored.replace(after, before, 1)
            self.assertEqual(restored, old)

    def test_resolver_stable_read_only_va_giu_acl(self):
        helper = MTQ_CONG_H_SQL[0]
        self.assertIn("LANGUAGE plpgsql STABLE SECURITY DEFINER", helper)
        self.assertIn("SET search_path = pg_catalog, master, nhat_ky, pg_temp AS $$", helper)
        self.assertIn("cu := master.mtq_giai_doi_tuong(p_hanh_dong, p_doi_tuong)", helper)
        sql = re.sub(r"--[^\n]*", "", helper)
        self.assertNotRegex(sql, r"\b(?:INSERT|UPDATE|DELETE|MERGE|EXECUTE|CALL|PERFORM|LOCK|ALTER|DROP)\b")
        self.assertNotIn("master.mtq_quyet_dinh(", sql)
        self.assertNotIn("master.mtq_kich_hoat", sql)
        self.assertNotRegex("\n".join(MTQ_CONG_H_SQL), r"\b(?:GRANT|REVOKE|CREATE TABLE|ALTER TABLE)\b")
        self.assertEqual(len(MTQ_CONG_H_SQL), 3)
        for current in MTQ_CONG_H_SQL:
            self.assertEqual(current.count("AS $$"), 1)
            self.assertEqual(current.count("$$"), 2)
            self.assertTrue(current.endswith("END $$"))

    def test_whitelist_nguon_khong_mo_crm_l11_va_pn_chi_duyet_mapping(self):
        sql = MTQ_CONG_H_SQL[0]
        whitelist = sql.split("IF NOT coalesce((", 1)[1].split("RETURN jsonb_build_array(cu)", 1)[0]
        self.assertEqual(set(re.findall(r"'(M[25]:[^']+)'", whitelist)), set(SOURCE_ACTIONS))
        for table in ("master.nguon_pham_vi", "master.nguon_profile", "master.anh_xa_nguon", "master.phap_nhan"):
            self.assertIn("'" + table + "'", whitelist)
        self.assertNotIn("CRM:", whitelist)
        self.assertNotIn(":L11:", whitelist)
        self.assertNotIn("master.hop_dong", whitelist)
        narrow = whitelist.split("'master.anh_xa_nguon','master.phap_nhan'", 1)[1]
        self.assertEqual(set(re.findall(r"'(M[25]:[^']+)'", narrow)), {ACTION, "M5:KHO:DUYET"})

    def test_dung_helper_m0049_cho_ca_uuid_va_instance_khong_dem_rieng(self):
        sql = MTQ_CONG_H_SQL[0]
        self.assertIn("master.mtq_nguon_ung_vien(r.scope_kind, token.nguon, r.subject_key)", sql)
        self.assertIn("(true, r.profile_id::text), (false, r.source_instance_id)", sql)
        self.assertIn("HAVING count(*) = 1 AND (array_agg(c.profile_id))[1] = r.profile_id", sql)
        self.assertNotIn("WHERE p.source_instance_id = r.source_instance_id) = 1", sql)
        self.assertIn("count(t.value->>'nguon_khoa') = count(*)", sql)
        self.assertNotIn("đúng module từ CSDL", sql)

    def test_utf8_khong_bom_migration_lf_va_hang_literal(self):
        paths = (Path(PM.__file__), ROOT / "src/kho_tri_thuc/k2/sql_mtq_cong.py", Path(__file__))
        for path in paths:
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn("\ufffd", raw.decode("utf-8"))
        self.assertNotIn(b"\r", paths[0].read_bytes())
        tree = ast.parse(paths[1].read_text(encoding="utf-8"))
        values = {a.targets[0].id: ast.literal_eval(a.value) for a in tree.body}
        self.assertEqual(values["MTQ_CONG_H_SQL"], MTQ_CONG_H_SQL)


@unittest.skipUnless(cong.DSN and cong.psycopg is not None,
                     "NOT_RUN: cần KHO_PG_DSN_TEST + psycopg; lead chạy PG")
class MtqLmodResolverPostgres(unittest.TestCase):
    nguoi = nen.MtqPostgres.nguoi
    actor = nen.MtqPostgres.actor
    ghi = nen.MtqPostgres.ghi
    sua_nhap = nen.MtqPostgres.sua_nhap
    san_sang = nen.MtqPostgres.san_sang
    mapping = nguon.MtqNguonPostgres.mapping
    them_profile = nguon.MtqNguonPostgres.them_profile
    ung_vien_m0049 = nguon.MtqNguonPostgres.ung_vien_m0049
    dong_mapping = nguon.MtqNguonPostgres.dong_mapping
    hop_dong = cong.MtqCongCPostgres.hop_dong

    @classmethod
    def setUpClass(cls):
        cong.MtqCongCPostgres.setUpClass.__func__(cls)
        # Oracle nguyên M0057, gồm cả helper một PN; không gọi resolver H.
        for sql in MTQ_CONG_G_SQL[:3]:
            cls.c.execute(sql.replace("master.mtq_giai_doi_tuong_tap", OLD_TAP)
                          .replace("master.mtq_quyet_dinh_phien", OLD_DECISION)
                          .replace("master.mtq_ghi_tu_choi_phien", OLD_AUDIT))

    def setUp(self):
        nen.MtqPostgres.setUp(self)
        self.rooms = {self.pn: (self.phong, self.phong2)}
        self.rooms[self.pn2] = (self.ghi("PHONG", {
            "phap_nhan_id": str(self.pn2), "ma": "KT", "ten": "KT nguồn giả"})["id"],)
        self.gans = {}
        self.inst = "MTQ_4IB1_" + uuid.uuid4().hex
        self.c.execute("INSERT INTO master.nguon_instance (source_instance_id) VALUES (%s)", (self.inst,))
        self.profile = self.them_profile("PROFILE_GIA")
        self.map_a = self.mapping()
        self.scope_a = self.scope(["CTY A"])
        self.obj = self.ref("master.nguon_pham_vi", self.scope_a)

    @staticmethod
    def ref(table, key):
        return {"bang": table, "id": str(key)}

    def key(self, subject="CTY A", kind="INVOICE_SET", instance=False):
        return kind + "|" + (self.inst if instance else str(self.profile[0])).upper() + "|" + subject

    def scope(self, subjects=None, kind="INVOICE_SET", warehouse="KHO 01"):
        # nguon_pham_vi append-only, FK triple profile, CHECK kiểu M0016:
        # hóa đơn không giả kho/phiếu/PN; kho không giả company/PN.
        return self.c.execute("""INSERT INTO master.nguon_pham_vi
            (source_instance_id,profile_ref,profile_sha256,scope_ref,scope_kind,
             company_keys,ma_kho,so_phieu,sections,coverage_binding)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,ARRAY['HEADER'],'GIA_MTQ_4IB1') RETURNING id""",
            (self.inst, self.profile[1], self.profile[2], uuid.uuid4().hex, kind,
             subjects if kind == "INVOICE_SET" else None,
             warehouse if kind == "KHO10_PHIEU" else None,
             "PHIEU_GIA" if kind == "KHO10_PHIEU" else None)).fetchone()[0]

    def configure(self, pn=None, *, scope="NGUON", key=None, tick=True, enable=True):
        pn = pn or self.pn
        self.actor(self.admin)
        v = self.ghi("NHAP", {"phap_nhan_id": str(pn)})
        for room in self.rooms[pn]:
            for vai in nen.VAI:
                row = self.sua_nhap(v, "DONG", {"phong_id": room, "vai": vai, "gioi_han_vnd": 0})
                if tick and room == self.rooms[pn][0] and vai == "TRUONG_PHONG":
                    for action in (*SOURCE_ACTIONS, "CRM:TIEP_NHAN:DUYET", "M1:TIEN:LAP"):
                        module, man, verb = action.split(":")
                        self.sua_nhap(v, "O", {"dong_id": row["id"], "module": module, "man": man,
                                              "hanh_dong": verb, "cho_phep": True})
        self.sua_nhap(v, "CONG_BO", {})
        g = self.ghi("GAN_VAI", {"nguoi_dung_id": str(self.user[0]), "phap_nhan_id": str(pn),
                                 "phong_id": self.rooms[pn][0], "vai": "TRUONG_PHONG"})
        self.gans[pn] = g
        if scope:
            self.ghi("PHAM_VI", {"gan_vai_id": g["id"], "phap_nhan_id": str(pn), "loai": scope,
                                  "khoa": key or (str(pn) if scope == "PHAP_NHAN" else self.key())})
        self.san_sang()
        self.ghi("KICH_HOAT", {"phap_nhan_id": str(pn), "phien_ban_id": v["id"], "bat": enable})
        self.actor(self.user)

    def resolve(self, obj=None, action=ACTION):
        return self.c.execute("SELECT master.mtq_giai_doi_tuong_tap(%s,%s::jsonb)",
                              (action, json.dumps(self.obj if obj is None else obj))).fetchone()[0]

    def decision(self, obj=None, action=ACTION, money=None, function="master.mtq_quyet_dinh_phien"):
        self.assertIn(function, ("master.mtq_quyet_dinh_phien", OLD_DECISION))
        return self.c.execute(f"SELECT {function}(%s,%s::jsonb,%s)",
                              (action, json.dumps(self.obj if obj is None else obj), money)).fetchone()[0]

    def audit(self, obj=None, action=ACTION, function="master.mtq_ghi_tu_choi_phien", request=None):
        self.assertIn(function, ("master.mtq_ghi_tu_choi_phien", OLD_AUDIT))
        return self.c.execute(f"SELECT {function}(%s,%s,%s::jsonb,NULL)",
                              (request or uuid.uuid4(), action, json.dumps(self.obj if obj is None else obj))).fetchone()[0]

    def test_mot_pn_nguon_dung_khoa_cho_sai_khoa_chan(self):
        self.mapping(key="CTY B")
        for key, expected in ((self.key(), True), (self.key("CTY B"), False)):
            with self.subTest(key=key), self.c.transaction(force_rollback=True):
                self.configure(key=key)
                context = self.resolve()[0]
                self.assertEqual(context["pn"], str(self.pn))
                self.assertEqual(context["nguon_khoa"], self.key())
                self.assertIs(context["hop_le"], True)
                self.assertIs(self.decision()["cho_phep"], expected)
                if not expected:
                    self.assertEqual(self.decision()["ma"], "MTQ_PHAM_VI")

    def test_alias_instance_m0049_cung_duoc_tieu_thu(self):
        self.configure(key=self.key(instance=True))
        self.assertEqual(self.resolve()[0]["nguon_khoa"], self.key(instance=True))
        self.assertIs(self.decision()["cho_phep"], True)
        self.them_profile("PROFILE_THU_HAI")
        self.assertIsNone(self.resolve()[0]["nguon_khoa"])
        self.assertEqual(self.decision()["ma"], "MTQ_PHAM_VI")

    def test_review_uuid_profile_trung_ten_instance_khong_dung_quyen_nguon_cu(self):
        self.configure()
        old_obj = self.obj
        old_profile = self.profile
        old_alias = self.key(instance=True)
        self.assertEqual(self.ung_vien_m0049("INVOICE_SET", str(old_profile[0]), "CTY A"), [old_profile[0]])
        self.assertEqual(self.resolve()[0]["nguon_khoa"], self.key())
        self.assertIs(self.decision()["cho_phep"], True)
        # Cấp U trước, sau đó thêm instance tên U với profile/mapping khác.
        self.inst = str(old_profile[0])
        self.c.execute("INSERT INTO master.nguon_instance(source_instance_id) VALUES (%s)", (self.inst,))
        self.profile = self.them_profile("PROFILE_TRUNG_UUID")
        self.mapping()
        new_obj = self.ref("master.nguon_pham_vi", self.scope(["CTY A"]))
        self.assertEqual(set(self.ung_vien_m0049("INVOICE_SET", self.inst, "CTY A")),
                         {old_profile[0], self.profile[0]})
        for obj in (old_obj, new_obj):
            with self.subTest(obj=obj):
                self.assertIsNone(self.resolve(obj)[0]["nguon_khoa"])
                self.assertEqual(self.decision(obj)["ma"], "MTQ_PHAM_VI")
                self.assertIs(self.decision(obj)["cho_phep"], False)
        self.actor(self.admin)
        # UUID mới/alias cũ riêng lẻ vẫn hợp lệ với M0049, nhưng không được
        # dùng chúng làm đường vòng cho đối tượng có một định danh mơ hồ.
        for key in (old_alias, self.key()):
            self.ghi("PHAM_VI", {"gan_vai_id": self.gans[self.pn]["id"], "phap_nhan_id": str(self.pn),
                                  "loai": "NGUON", "khoa": key})
        self.actor(self.user)
        for obj in (old_obj, new_obj):
            self.assertIsNone(self.resolve(obj)[0]["nguon_khoa"])
            self.assertIs(self.decision(obj)["cho_phep"], False)
        self.actor(self.admin)
        self.ghi("PHAM_VI", {"gan_vai_id": self.gans[self.pn]["id"], "phap_nhan_id": str(self.pn),
                              "loai": "PHAP_NHAN", "khoa": str(self.pn)})
        self.actor(self.user)
        for obj in (old_obj, new_obj):
            self.assertIsNone(self.resolve(obj)[0]["nguon_khoa"])
            self.assertIs(self.decision(obj)["cho_phep"], True)

    def test_uuid_trung_instance_sau_chuan_hoa_ca_hai_chi_dung_phap_nhan(self):
        self.configure()
        old_obj = self.obj
        # Registry cấm whitespace; UUID chữ hoa vẫn va chạm với UUID chữ thường.
        self.inst = str(self.profile[0]).upper()
        self.c.execute("INSERT INTO master.nguon_instance(source_instance_id) VALUES (%s)", (self.inst,))
        self.profile = self.them_profile("PROFILE_UUID_CHUAN_HOA")
        self.mapping()
        new_obj = self.ref("master.nguon_pham_vi", self.scope(["CTY A"]))
        for obj in (old_obj, new_obj):
            with self.subTest(obj=obj):
                self.assertIs(self.resolve(obj)[0]["hop_le"], True)
                self.assertIsNone(self.resolve(obj)[0]["nguon_khoa"])
                self.assertEqual(self.decision(obj)["ma"], "MTQ_PHAM_VI")
                self.assertIs(self.decision(obj)["cho_phep"], False)
        self.actor(self.admin)
        self.ghi("PHAM_VI", {"gan_vai_id": self.gans[self.pn]["id"], "phap_nhan_id": str(self.pn),
                              "loai": "PHAP_NHAN", "khoa": str(self.pn)})
        self.actor(self.user)
        for obj in (old_obj, new_obj):
            self.assertIsNone(self.resolve(obj)[0]["nguon_khoa"])
            self.assertIs(self.decision(obj)["cho_phep"], True)

    def test_mot_ung_vien_uuid_va_alias_doi_chieu_m0049_cho(self):
        for instance in (False, True):
            with self.subTest(instance=instance), self.c.transaction(force_rollback=True):
                self.configure(key=self.key(instance=instance))
                token = self.inst if instance else str(self.profile[0])
                self.assertEqual(self.ung_vien_m0049(" invoice_set ", " \t" + token.lower(), "cty  a\n"),
                                 [self.profile[0]])
                self.assertEqual(self.resolve()[0]["nguon_khoa"], self.key(instance=instance))
                self.assertIs(self.decision()["cho_phep"], True)

    def test_subject_mo_ho_cung_pn_khong_mat_khi_gop_voi_subject_ro(self):
        self.mapping(key="CTY B")
        self.obj = self.ref("master.nguon_pham_vi", self.scope(["CTY A", "CTY B"]))
        # Chỉ CTY A có alias instance đã cấp; CTY B phải giữ khóa NULL khi
        # UUID trở nên mơ hồ, không được mất khỏi phép gộp do count bỏ NULL.
        self.configure(key=self.key(instance=True))
        old_inst = self.inst
        self.inst = str(self.profile[0])
        self.c.execute("INSERT INTO master.nguon_instance(source_instance_id) VALUES (%s)", (self.inst,))
        self.them_profile("PROFILE_TRUNG_UUID_KHONG_MAP")
        # Subject UUID mơ hồ vẫn tính dù profile trùng tên chưa có mapping.
        self.assertEqual(len(self.ung_vien_m0049("INVOICE_SET", self.inst, "CTY B")), 2)
        self.assertEqual(self.ung_vien_m0049("INVOICE_SET", old_inst, "CTY A"), [self.profile[0]])
        self.assertIsNone(self.resolve()[0]["nguon_khoa"])
        self.assertEqual(self.decision()["ma"], "MTQ_PHAM_VI")

    def test_nguon_uu_tien_truoc_phap_nhan_va_thu_hoi(self):
        self.configure()
        self.actor(self.admin)
        broad = self.ghi("PHAM_VI", {"gan_vai_id": self.gans[self.pn]["id"], "phap_nhan_id": str(self.pn),
                                    "loai": "PHAP_NHAN", "khoa": str(self.pn)})
        self.actor(self.user)
        narrow = self.decision()
        self.assertNotEqual(narrow["pham_vi_id"], broad["id"])
        self.actor(self.admin)
        self.ghi("THU_HOI_PHAM_VI", {"id": narrow["pham_vi_id"]}, 1)
        self.actor(self.user)
        self.assertEqual(self.decision()["pham_vi_id"], broad["id"])

    def test_nguon_gop_hai_pn_cung_bat_du_hoac_thieu_mot_pn(self):
        self.mapping(key="CTY B", pn=self.pn2)
        self.obj = self.ref("master.nguon_pham_vi", self.scope(["CTY B", "CTY A", "CTY A"]))
        for fail in (None, self.pn, self.pn2):
            with self.subTest(fail=fail), self.c.transaction(force_rollback=True):
                self.configure(self.pn, tick=fail != self.pn)
                self.configure(self.pn2, key=self.key("CTY B"), tick=fail != self.pn2)
                contexts = self.resolve()
                self.assertEqual([c["pn"] for c in contexts], sorted(map(str, (self.pn, self.pn2))))
                self.assertEqual(len(contexts), 2)
                before = self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0]
                self.c.execute("SET LOCAL ROLE app_web")
                result = self.decision()
                self.assertIs(result["cho_phep"], fail is None)
                if fail is not None:
                    self.assertEqual(result["ma"], "MTQ_CHUA_TICK")
                    request = uuid.uuid4()
                    audit_id = self.audit(request=request)
                    self.assertEqual(self.audit(request=request), audit_id)
                self.c.execute("RESET ROLE")
                self.assertEqual(self.c.execute("SELECT count(*) FROM nhat_ky.mtq_tu_choi").fetchone()[0],
                                 before + (fail is not None))
                if fail is not None:
                    self.assertEqual(self.c.execute("SELECT phap_nhan_id,ma FROM nhat_ky.mtq_tu_choi WHERE id=%s",
                                                    (audit_id,)).fetchone(), (fail, "MTQ_CHUA_TICK"))

    def test_nguon_gop_hai_pn_thieu_pham_vi_pn_sau(self):
        self.mapping(key="CTY B", pn=self.pn2)
        self.obj = self.ref("master.nguon_pham_vi", self.scope(["CTY A", "CTY B"]))
        self.configure()
        self.configure(self.pn2, scope=None)
        self.assertEqual(self.decision()["ma"], "MTQ_PHAM_VI")
        key = self.audit()
        self.assertEqual(self.c.execute("SELECT phap_nhan_id FROM nhat_ky.mtq_tu_choi WHERE id=%s",
                                        (key,)).fetchone()[0], self.pn2)

    def test_hon_hop_chan_ca_hai_huong_tat_giu_cu(self):
        self.mapping(key="CTY B", pn=self.pn2)
        self.obj = self.ref("master.nguon_pham_vi", self.scope(["CTY A", "CTY B"]))
        for enabled in (None, self.pn, self.pn2):
            with self.subTest(enabled=enabled), self.c.transaction(force_rollback=True):
                self.configure(enable=enabled == self.pn)
                self.configure(self.pn2, key=self.key("CTY B"), enable=enabled == self.pn2)
                result = self.decision()
                self.assertEqual(result["ma"], "MTQ_TAT" if enabled is None else "MTQ_PN_HON_HOP")
                if enabled is not None:
                    self.assertIs(result["cho_phep"], False)

    def test_profile_hop_tat_ca_scope_khong_lay_mot_pn(self):
        self.mapping(key="CTY B", pn=self.pn2)
        self.scope(["CTY B"])
        self.obj = self.ref("master.nguon_profile", self.profile[0])
        self.configure()
        self.configure(self.pn2, key=self.key("CTY B"))
        self.assertEqual([r["pn"] for r in self.resolve()], sorted(map(str, (self.pn, self.pn2))))
        self.assertIs(self.decision()["cho_phep"], True)
        obj = {**self.obj, "phong_id": self.phong}
        self.assertEqual(self.decision(obj)["ma"], "MTQ_PHONG_MO_HO")

    def test_nhieu_subject_cung_pn_khong_lay_mot_khoa_dai_dien(self):
        self.mapping(key="CTY B")
        self.obj = self.ref("master.nguon_pham_vi", self.scope(["CTY A", "CTY B"]))
        self.configure()
        contexts = self.resolve()
        self.assertEqual(len(contexts), 1)
        self.assertIsNone(contexts[0]["nguon_khoa"])
        self.assertEqual(self.decision()["ma"], "MTQ_PHAM_VI")
        self.actor(self.admin)
        self.ghi("PHAM_VI", {"gan_vai_id": self.gans[self.pn]["id"], "phap_nhan_id": str(self.pn),
                              "loai": "PHAP_NHAN", "khoa": str(self.pn)})
        self.actor(self.user)
        self.assertIs(self.decision()["cho_phep"], True)

    def test_kho_chi_dung_mapping_warehouse_va_khoa_kho(self):
        self.mapping("WAREHOUSE", "KHO 01", pn=self.pn2)
        self.obj = self.ref("master.nguon_pham_vi", self.scope(kind="KHO10_PHIEU"))
        self.configure(self.pn2, key=self.key("KHO 01", "KHO10_PHIEU"))
        context = self.resolve(action="M5:KHO:DUYET")[0]
        self.assertEqual(context["pn"], str(self.pn2))
        self.assertIs(self.decision(action="M5:KHO:DUYET")["cho_phep"], True)
        self.assertEqual(self.decision(action=ACTION)["ma"], "MTQ_CAN_RESOLVER_MTQ4")

    def test_retarget_kiem_pn_cu_va_pn_dich_bang_hai_doi_tuong(self):
        self.configure()
        old = self.ref("master.anh_xa_nguon", self.map_a)
        target = self.ref("master.phap_nhan", self.pn2)
        self.assertEqual([r["pn"] for r in self.resolve(old)], [str(self.pn)])
        self.assertEqual([r["pn"] for r in self.resolve(target)], [str(self.pn2)])
        for tick in (False, True):
            with self.subTest(tick=tick), self.c.transaction(force_rollback=True):
                self.configure(self.pn2, scope="PHAP_NHAN", tick=tick)
                self.assertIs(self.decision(old)["cho_phep"], True)
                self.assertIs(self.decision(target)["cho_phep"], tick)
                if not tick:
                    self.assertEqual(self.decision(target)["ma"], "MTQ_CHUA_TICK")
        for extra in ({"pn": str(self.pn2)}, {"phap_nhan_id": str(self.pn2)}, {"nguon_khoa": self.key()}):
            self.assertEqual(self.decision({**old, **extra})["ma"], "MTQ_DOI_TUONG")

    def test_master_pn_dich_chi_hai_khoa_duyet_anh_xa(self):
        self.configure(scope="PHAP_NHAN")
        obj = self.ref("master.phap_nhan", self.pn)
        for action in (ACTION, "M5:KHO:DUYET"):
            self.assertIs(self.decision(obj, action)["cho_phep"], True)
        for action in ("M2:HOA_DON:LAP", "M5:KHO:XEM", "M2:L11:DUYET", "CRM:G1_MAU:DUYET"):
            self.assertEqual(self.decision(obj, action)["ma"], "MTQ_CAN_RESOLVER_MTQ4")
        mapping = self.ref("master.anh_xa_nguon", self.map_a)
        self.assertEqual(self.decision(mapping, "M5:KHO:DUYET")["ma"], "MTQ_CAN_RESOLVER_MTQ4")

    def test_whitelist_tung_cap_bang_khoa_khong_bac_cau_module(self):
        warehouse_map = self.mapping("WAREHOUSE", "KHO 01", pn=self.pn2)
        warehouse_scope = self.scope(kind="KHO10_PHIEU")
        self.configure(scope="PHAP_NHAN")
        self.configure(self.pn2, scope="PHAP_NHAN")
        invoice_actions = {a for a in SOURCE_ACTIONS if a.startswith("M2:")}
        warehouse_actions = {a for a in SOURCE_ACTIONS if a.startswith("M5:")}
        matrix = (
            (self.obj, invoice_actions),
            (self.ref("master.nguon_pham_vi", warehouse_scope), warehouse_actions),
            (self.ref("master.nguon_profile", self.profile[0]), set(SOURCE_ACTIONS)),
            (self.ref("master.anh_xa_nguon", self.map_a), {ACTION}),
            (self.ref("master.anh_xa_nguon", warehouse_map), {"M5:KHO:DUYET"}),
            (self.ref("master.phap_nhan", self.pn), {ACTION, "M5:KHO:DUYET"}),
        )
        for obj, allowed in matrix:
            for action in (*SOURCE_ACTIONS, "M2:L11:DUYET", "M5:L11:XEM"):
                with self.subTest(obj=obj, action=action):
                    result = self.decision(obj, action)
                    self.assertIs(result["cho_phep"], action in allowed)
                    if action not in allowed:
                        self.assertEqual(result["ma"], "MTQ_CAN_RESOLVER_MTQ4")

    def test_thieu_trung_hoac_het_hieu_luc_mapping_khong_bo_qua_subject(self):
        self.configure()
        self.obj = self.ref("master.nguon_pham_vi", self.scope(["CTY A", "CHUA MAP"]))
        self.assertEqual(self.decision()["ma"], "MTQ_CAN_RESOLVER_MTQ4")
        self.mapping(key="CHUA MAP", future=True)
        self.assertEqual(self.decision()["ma"], "MTQ_CAN_RESOLVER_MTQ4")
        self.obj = self.ref("master.nguon_pham_vi", self.scope_a)
        with self.c.transaction(force_rollback=True):
            self.mapping(key="cty   a")
            self.assertEqual(self.decision()["ma"], "MTQ_CAN_RESOLVER_MTQ4")
        self.dong_mapping(self.map_a)
        self.assertEqual(self.decision()["ma"], "MTQ_CAN_RESOLVER_MTQ4")
        historical = self.ref("master.anh_xa_nguon", self.map_a)
        self.assertEqual(self.resolve(historical)[0]["pn"], str(self.pn))
        self.assertEqual(self.decision(historical)["ma"], "MTQ_CAN_RESOLVER_MTQ4")

    def test_instance_dung_va_id_thieu_chan_khong_tin_body(self):
        self.configure()
        for table in ("master.nguon_pham_vi", "master.nguon_profile", "master.anh_xa_nguon", "master.phap_nhan"):
            self.assertEqual(self.decision(self.ref(table, uuid.uuid4()))["ma"], "MTQ_CAN_RESOLVER_MTQ4")
        self.c.execute("UPDATE master.nguon_instance SET trang_thai='DUNG' WHERE source_instance_id=%s", (self.inst,))
        self.assertEqual(self.decision()["ma"], "MTQ_CAN_RESOLVER_MTQ4")

    def test_oracle_nguyen_json_m0057_doi_tuong_cu_ca_bat_tat(self):
        hd = self.hop_dong(self.pn)
        obj_hd = self.ref("master.hop_dong", hd)
        obj_pn = self.ref("master.phap_nhan", self.pn)
        for enabled in (False, True):
            with self.subTest(enabled=enabled), self.c.transaction(force_rollback=True):
                self.configure(scope="PHAP_NHAN", enable=enabled)
                for action, obj in (
                    ("CRM:TIEP_NHAN:DUYET", obj_hd), ("M1:TIEN:LAP", obj_pn),
                    ("CRM:TIEP_NHAN:DUYET", {**obj_hd, "phong_id": self.phong}),
                    ("CRM:TIEP_NHAN:DUYET", {**obj_hd, "id": str(uuid.uuid4())}),
                    ("CRM:TIEP_NHAN:DUYET", {**obj_hd, "pn": str(self.pn2)}),
                    ("CRM:TIEP_NHAN:DUYET", {"bang": "master.hop_dong", "id": "sai-uuid"}),
                    ("CRM:TIEP_NHAN:DUYET", []),
                ):
                    for money in (None, -1, 0, 1):
                        self.assertEqual(self.decision(obj, action, money),
                                         self.decision(obj, action, money, OLD_DECISION))
                    self.assertEqual(self.resolve(obj, action), self.c.execute(
                        f"SELECT {OLD_TAP}(%s,%s::jsonb)", (action, json.dumps(obj))).fetchone()[0])
                if enabled:
                    new = self.audit(obj_hd, "CRM:TIEP_NHAN:DUYET")
                    old = self.audit(obj_hd, "CRM:TIEP_NHAN:DUYET", OLD_AUDIT)
                    rows = self.c.execute("SELECT to_jsonb(t)-'id'-'request_id'-'luc' "
                                          "FROM nhat_ky.mtq_tu_choi t WHERE id=ANY(%s) ORDER BY id",
                                          ([new, old],)).fetchall()
                    self.assertEqual(rows[0], rows[1])

    def test_qd03_hd_crm_khong_mo_qua_khoa_m2_m5(self):
        self.configure(scope="PHAP_NHAN")
        hd = self.ref("master.hop_dong", self.hop_dong(self.pn))
        for action in SOURCE_ACTIONS:
            self.assertEqual(self.decision(hd, action)["ma"], "MTQ_CAN_RESOLVER_MTQ4")

    def test_resolver_read_only_app_khong_execute_oid_acl_khong_doi(self):
        names = (RESOLVER, "master.mtq_giai_doi_tuong(text,jsonb)", *cong.SIGNATURES)

        def snapshot():
            return self.c.execute("SELECT oid,proowner,proacl::text,prosecdef,proconfig "
                                  "FROM pg_proc WHERE oid=ANY(%s::regprocedure[]) ORDER BY oid",
                                  (list(names),)).fetchall()

        for sql in MTQ_CONG_G_SQL[:3]:
            self.c.execute(sql.replace("CREATE FUNCTION ", "CREATE OR REPLACE FUNCTION ", 1))
        before = snapshot()
        for sql in MTQ_CONG_H_SQL:
            self.c.execute(sql)
        self.assertEqual(snapshot(), before)
        for name in names[:2]:
            self.assertFalse(self.c.execute("SELECT has_function_privilege('app_web',%s,'EXECUTE')",
                                            (name,)).fetchone()[0])
            self.assertFalse(self.c.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_proc p, "
                "LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a "
                "WHERE p.oid=%s::regprocedure AND a.grantee=0 AND a.privilege_type='EXECUTE')",
                (name,)).fetchone()[0])
        # PG không cho chuyển TX đã ghi fixture thành READ ONLY.
        # Rollback trước; cleanup setUp vẫn rollback TX đọc mới này.
        self.c.execute("ROLLBACK")
        self.c.execute("BEGIN READ ONLY")
        self.assertEqual(self.c.execute("SELECT provolatile,prosecdef FROM pg_proc WHERE oid=%s::regprocedure",
                                        (RESOLVER,)).fetchone(), ("s", True))
        obj = self.ref("master.nguon_pham_vi", uuid.uuid4())
        self.resolve(obj)
        self.c.execute("SET LOCAL ROLE app_web")
        with self.assertRaises(cong.psycopg.errors.InsufficientPrivilege), self.c.transaction():
            self.resolve(obj)


if __name__ == "__main__":
    unittest.main()
