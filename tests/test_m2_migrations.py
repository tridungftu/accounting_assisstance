"""M2 bridge R15 (repair02) — migration M0015_M2_BRIDGE (append-only, candidate) — coder viết, CHƯA CHẠY (CODE_ONLY/UNRUN).

Repair03: R4 tuple tài liệu khai báo (bytes/raw SHA/locator/payload SHA tài liệu khai/căn cứ gắn tài liệu/phạm vi) ở admission + consumer.
Repair02: thứ tự quyền → khóa → biên nhận → CAS (R1); ứng viên literal resolve/đối chiếu trước mọi ghi (R2); guard core M2 bất biến (R3, nhánh
DELETE chỉ kiểm tĩnh); digest canonical đơn vị (R4); CHECK hai trị (S1); ROOT_SEED INVOICE_LINE kiểm đúng mã của chính INSERT + 0 delta.

Tĩnh: prefix 1–12 đúng lineage pin, COMMON13/M5 14 giữ nguyên đối tượng, M0015 là phần tử cuối (PG_SCHEMA_VERSION 15), SQL M0015 không chạm M9/tiền
vay/pool L11, mọi SECURITY DEFINER có search_path + REVOKE PUBLIC, INVOICE_LINE không seed được, core M2 tiền/Nợ/Có NULL.
PostgreSQL (chỉ khi root cấp KHO_PG_DSN_TEST, DB DEMO mới): fresh 0→15; nâng cấp 14→15 giữ nguyên ID/giá trị/owner của hàng cũ (HD_MUA cũ vẫn M1,
dòng cũ no/co giữ), M2 core owner-only + NULL; legacy full-M9 13 bị từ chối trước ghi; catalog mới đúng 7 bảng + view. Không DROP DB/role.
"""

from __future__ import annotations

import json
import os
import re
import unittest
import uuid
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang import postgres as pg
from kho_tri_thuc.ha_tang.pg_migrations import (LEGACY_FULL_M9_M0013_SHA256, M0013_COMMON, M0014_M5, M0015_M2_BRIDGE, PG_MIGRATIONS,
                                                PG_SCHEMA_VERSION)
from kho_tri_thuc.ha_tang.primitives import DataError, sha256

ROOT = Path(__file__).resolve().parents[1]
PINS_PATH = ROOT / "tests" / "fixtures" / "m0_m5" / "lineage-pins.json"
PINS_SHA = "418194019d14cb859f10ed2d545ace0e8c5e1c96b09f534a0a549d2d4f6e5f15"
ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
H = lambda statements: sha256("\n".join(statements).encode())  # noqa: E731
M2_TABLES = {"master.dinh_nghia_don_vi_luong", "master.tai_lieu_khai_bao_don_vi", "master.m2_ung_vien_dong", "kho.hoa_don_danh_tinh", "kho.hoa_don_phien_ban", "kho.hoa_don_quan_sat",
             "kho.hoa_don_dong_danh_tinh", "kho.hoa_don_dong_phien_ban", "kho.mua_dich_dong"}


def _fn(ten: str) -> str:
    return next(s for s in M0015_M2_BRIDGE if f"FUNCTION {ten}(" in s)


class TinhM0015(unittest.TestCase):
    def test_append_only_15(self):
        pins = json.loads(PINS_PATH.read_bytes().decode("utf-8"))
        self.assertEqual(sha256(PINS_PATH.read_bytes()), PINS_SHA)
        for p in pins["prefix_1_12"]:
            m = PG_MIGRATIONS[p["version"] - 1]
            self.assertEqual((len(m), H(m)), (p["statement_count"], p["checksum"]), p["version"])
        self.assertEqual(PG_SCHEMA_VERSION, 15)
        self.assertIs(PG_MIGRATIONS[12], M0013_COMMON)
        self.assertIs(PG_MIGRATIONS[13], M0014_M5)
        self.assertIs(PG_MIGRATIONS[14], M0015_M2_BRIDGE)
        self.assertNotEqual(H(M0013_COMMON), LEGACY_FULL_M9_M0013_SHA256)
        hist = [(i + 1, H(m)) for i, m in enumerate(PG_MIGRATIONS)]
        self.assertEqual(pg.kiem_lich_su(hist), 15)
        self.assertEqual(pg.kiem_lich_su(hist[:14]), 14)  # DB 14 vẫn đúng lineage để nâng cấp
        for xau in (hist[:14] + [(15, "0" * 64)], hist[:12] + [(13, LEGACY_FULL_M9_M0013_SHA256)], hist + [(16, "a" * 64)]):
            with self.assertRaises(DataError):
                pg.kiem_lich_su(xau)

    def test_sql_m0015_pham_vi_va_definer(self):
        sql = "\n".join(M0015_M2_BRIDGE)
        for cam in ("'M9'", "vay_", "lich_tra_no", "lai_suat", "khe_uoc", "lien_ket_phan_bo", "dich_phan_bo_tien", "tien_con_lai", "pool", "l11",
                    "SET DEFAULT 0", "TO PUBLIC", "DROP TABLE", "TRUNCATE", "DELETE FROM"):
            self.assertNotIn(cam, sql, cam)
        for bang in M2_TABLES:
            self.assertIn(f"CREATE TABLE {bang} (", sql, bang)
        self.assertIn("CREATE VIEW kho.mua_dong_hien_hanh WITH (security_invoker = true)", sql)
        for stmt in M0015_M2_BRIDGE:
            if "SECURITY DEFINER" in stmt:
                self.assertIn("SET search_path =", stmt, stmt[:120])
        definer = set(re.findall(r"FUNCTION ((?:master|kho|giao_tiep)\.\w+)\([^)]*\)\s+(?:RETURNS[^$]*?)LANGUAGE \w+(?: STABLE)? SECURITY DEFINER", sql))
        revoked = "\n".join(s for s in M0015_M2_BRIDGE if s.startswith("REVOKE EXECUTE")) + "\n" + "\n".join(
            s for s in M0013_COMMON if s.startswith("REVOKE EXECUTE"))
        for fn in definer:
            self.assertIn(fn + "(", revoked, fn)
        # INVOICE_LINE chỉ do CFO trong workflow; COMMON finalizer M2 tự dẫn xuất; core M2 NULL tiền/Nợ/Có; dòng dẫn xuất không span
        self.assertIn("INVOICE_LINE chỉ do CFO duyệt trong workflow mapping dòng, không seed", sql)
        self.assertIn("kết quả M2 do CSDL dẫn xuất, không nhận refs từ caller", sql)
        self.assertIn("M2_TIEN_CHUA_CAN_CU", sql)
        self.assertIn("NEW.derived_record_sha256 := encode(sha256(convert_to(NEW.row_raw::text, 'UTF8')), 'hex')", sql)
        self.assertRegex(sql, r"so_luong_chuan_hoa'\)::numeric\(38,12\), NULL, NULL,\s+jsonb_build_object\('locator'")  # dòng core M2 no/co NULL tường minh
        grants = "\n".join(s for s in M0015_M2_BRIDGE if "GRANT EXECUTE" in s)
        for noi_bo in ("m2_co_so_noi_bo(", "m2_basis_tuyen_noi_bo(", "nguon_chot_ket_qua("):
            self.assertNotIn(noi_bo, grants, noi_bo)
        # R1: quyền hiện hành → namespace biên nhận → gốc hóa đơn → hàng → tra biên nhận (same-H trả kết quả cũ) → CHỈ yêu cầu mới mới CAS token
        for ten, quyen in (("kho.m2_xem_xet_nguon", "KHONG_CO_QUYEN_M2_SOURCE_REVIEW"), ("kho.m2_mapping_dong", "KHONG_CO_QUYEN_M2_MAP"),
                           ("kho.m2_route", "KHONG_CO_QUYEN_M2_ROUTE")):
            f = _fn(ten)
            with self.subTest(fn=ten):
                self.assertLess(f.index(quyen), f.index("'BIEN_NHAN|'"))
                self.assertLess(f.index("'BIEN_NHAN|'"), f.index("'HOA_DON_ROOT|'"))
                self.assertLess(f.index("'HOA_DON_ROOT|'"), f.index("FOR UPDATE"))
                self.assertLess(f.index("FROM kho.bien_nhan_thao_tac"), f.index("M2_VERSION_CHANGED"))
                self.assertLess(f.index("'lap_lai', true"), f.index("M2_VERSION_CHANGED"))
                self.assertLess(f.index("M2_VERSION_CHANGED"), f.index("INSERT INTO kho.bien_nhan_thao_tac"))
        self.assertIn("ANH_XA_KHONG_CO_QUYEN: replay đổi mapping cần quyền hiện hành trên pháp nhân cũ", _fn("kho.m2_mapping_cong_ty"))

    def test_sql_repair02_r2_r3_r4_s1(self):
        sql = "\n".join(M0015_M2_BRIDGE)
        # R2: ứng viên literal resolve + đối chiếu dòng thực + đúng dòng logic TRƯỚC mọi gốc/mapping/cầu nối/biên nhận/audit; evidence bắt buộc
        f = _fn("kho.m2_mapping_dong")
        for ma in ("M2_UNG_VIEN_KHONG_CO", "kho.m2_ung_vien_khop_noi_bo(fv.id, r.id, o.id)", "M2_UNG_VIEN_SAI_DONG_LOGIC"):
            for ghi in ("INSERT INTO kho.hoa_don_dong_danh_tinh", "INSERT INTO master.anh_xa_nguon", "INSERT INTO kho.hoa_don_dong_phien_ban",
                        "INSERT INTO kho.bien_nhan_thao_tac", "INSERT INTO nhat_ky.su_kien"):
                self.assertLess(f.index(ma), f.index(ghi), (ma, ghi))
        self.assertIn("'evidence_revision', p->'evidence_revision'", f)  # revision nằm trong request H
        self.assertIn("line_ung_vien_id", f)
        khop = _fn("kho.m2_ung_vien_khop_noi_bo")
        for ma in ("M2_UNG_VIEN_SAI_NGUON", "M2_UNG_VIEN_SAI_PHAP_NHAN", "M2_UNG_VIEN_SAI_ARTIFACT", "M2_UNG_VIEN_SAI_DINH_DANH", "M2_UNG_VIEN_SAI_VI_TRI",
                   "l.scope_ref", "v.byte_length", "(r.row_raw->>'byte_length')::bigint", "ARRAY[v_pn_ma, d.chieu, d.mst_ban, d.mau_so, d.ky_hieu, d.so_chuan]"):
            self.assertIn(ma, khop)
        grants = "\n".join(s for s in M0015_M2_BRIDGE if "GRANT EXECUTE" in s)
        self.assertNotIn("m2_ung_vien_khop_noi_bo(", grants)
        self.assertIn("kho.m2_ung_vien_hien_hanh(uuid) TO app_web", grants)
        self.assertIn("ALTER TABLE master.m2_ung_vien_dong ENABLE ROW LEVEL SECURITY", sql)
        self.assertIn("M2_UNG_VIEN_KHONG_KHOP", sql)  # lớp phòng thủ thứ hai ở trigger mapping
        # R3: guard core M2 chặn UPDATE thay đổi + DELETE (kể cả owner), chạy sau cùng; nhánh DELETE chỉ kiểm tĩnh (môi trường cấm xóa)
        core = _fn("kho.m2_core_nguon_bat_bien")
        self.assertIn("IF TG_OP = 'DELETE' THEN\n                RAISE EXCEPTION 'M2_NGUON_BAT_BIEN", core)
        self.assertIn("IF NEW IS DISTINCT FROM OLD THEN", core)
        self.assertNotIn("la_chu_bang", core)  # không có ngoại lệ chủ bảng
        for t in ("kho.chung_tu ", "kho.chung_tu_dong "):
            self.assertIn(f"BEFORE UPDATE OR DELETE ON {t}FOR EACH ROW EXECUTE FUNCTION kho.m2_core_nguon_bat_bien()", sql)
        # R4: digest canonical CSDL (không jsonb::text) + nghĩa + căn cứ nguồn trước khi làm authority
        don_vi = _fn("master.dinh_nghia_don_vi_kiem")
        for ma in ("master.json_chuan(NEW.payload)", "DON_VI_DIGEST_SAI", "DON_VI_NGHIA_THIEU", "master.don_vi_khop_khai_bao(NEW.payload"):
            self.assertIn(ma, don_vi)
        self.assertNotIn("[A-Z0-9_]+:[^:]+:[0-9a-f]{64}", don_vi)  # repair03: không còn regex cú pháp làm authority căn cứ
        chuan = _fn("master.json_chuan")
        self.assertIn("ORDER BY e.key COLLATE \"C\"", chuan)
        self.assertIn("WITH ORDINALITY", chuan)
        self.assertIn("JSON_CHUAN_SO", chuan)

    def test_sql_repair03_r4_tuple_khai_bao(self):
        sql = "\n".join(M0015_M2_BRIDGE)
        # tài liệu khai báo: bytes thô + SHA/độ dài (CHECK) + FK catalog dùng chung + căn cứ UNIQUE; owner-only, chỉ thêm
        tl = next(s for s in M0015_M2_BRIDGE if s.startswith("CREATE TABLE master.tai_lieu_khai_bao_don_vi"))
        for ma in ("noi_dung bytea NOT NULL", "source_basis_ref text NOT NULL UNIQUE", "encode(sha256(noi_dung), 'hex') = raw_sha256",
                   "REFERENCES master.nguon_master_noi_dung (reference_id, raw_sha256, byte_length)"):
            self.assertIn(ma, tl)
        self.assertIn("ADD CONSTRAINT nguon_master_noi_dung_ref_sha_len_m2_uq UNIQUE (reference_id, raw_sha256, byte_length)", sql)
        kiem_tl = _fn("master.tai_lieu_khai_bao_kiem")
        for ma in ("DON_VI_TAI_LIEU_BAT_BIEN", "DON_VI_TAI_LIEU_CHI_CHU", "DON_VI_TAI_LIEU_KHONG_CO_CATALOG", "DON_VI_TAI_LIEU_SAI_HASH",
                   "DON_VI_TAI_LIEU_CAN_CU_DA_DUNG", "DON_VI_TAI_LIEU_CAN_CU_SAI", "DON_VI_TAI_LIEU_KHONG_DOC_DUOC", "la_chu_bang"):
            self.assertIn(ma, kiem_tl)
        self.assertIn("BEFORE INSERT OR UPDATE OR DELETE ON master.tai_lieu_khai_bao_don_vi", sql)
        # hàng đơn vị mang tuple chính xác + FK tài liệu/profile/catalog hỗ trợ
        dv = next(s for s in M0015_M2_BRIDGE if s.startswith("CREATE TABLE master.dinh_nghia_don_vi_luong"))
        for ma in ("declaration_ref text NOT NULL", "declaration_raw_sha256 text NOT NULL", "declaration_locator text NOT NULL",
                   "support_source_instance_id text NOT NULL", "REFERENCES master.tai_lieu_khai_bao_don_vi (reference_id, raw_sha256)",
                   "REFERENCES master.nguon_profile (source_instance_id, profile_ref, profile_sha256)", "UNIQUE (declaration_ref, declaration_locator)"):
            self.assertIn(ma, dv)
        # một quy tắc đối chiếu, kỳ vọng lấy từ BYTES tài liệu (không từ chính hàng): locator, payload SHA tài liệu khai, căn cứ, phạm vi
        k = _fn("master.don_vi_khop_khai_bao")
        for ma in ("convert_from(t.noi_dung, 'UTF8')::jsonb", "doc #> v_path", "cha->>'definition_payload_sha256'", "cha ? 'source_basis_ref'",
                   "p_basis IS DISTINCT FROM t.source_basis_ref", "DON_VI_TAI_LIEU_KHONG_CO", "DON_VI_TAI_LIEU_SAI_HASH", "DON_VI_VI_TRI_KHONG_CO",
                   "DON_VI_KHONG_KHOP_TAI_LIEU", "DON_VI_DIGEST_SAI", "DON_VI_CAN_CU_SAI", "DON_VI_PHAM_VI_SAI", "master.json_chuan(sub)"):
            self.assertIn(ma, k)
        self.assertNotIn("'CAI'", k)
        self.assertNotIn("ROOT_SEED_DEMO", k)  # không hardcode đơn vị/prefix căn cứ làm authority
        # consumer DB độc lập trước MỌI ghi của mapping dòng; ngữ cảnh hỗ trợ = profile snapshot
        f = _fn("kho.m2_mapping_dong")
        for ghi in ("INSERT INTO kho.hoa_don_dong_danh_tinh", "INSERT INTO master.anh_xa_nguon", "INSERT INTO kho.hoa_don_dong_phien_ban",
                    "INSERT INTO kho.bien_nhan_thao_tac"):
            self.assertLess(f.index("master.don_vi_khop_khai_bao(un.payload"), f.index(ghi), ghi)
        self.assertIn("DON_VI_NGOAI_PHAM_VI", f)
        revoked = "\n".join(s for s in M0015_M2_BRIDGE if s.startswith("REVOKE EXECUTE"))
        self.assertIn("master.don_vi_khop_khai_bao(jsonb, text, text, text, text, text, text, text, text, text, text)", revoked)
        self.assertNotIn("don_vi_khop_khai_bao", "\n".join(s for s in M0015_M2_BRIDGE if "GRANT EXECUTE" in s))
        self.assertIn("ALTER TABLE master.tai_lieu_khai_bao_don_vi ENABLE ROW LEVEL SECURITY", sql)
        self.assertIn("'master.tai_lieu_khai_bao_don_vi'", sql)  # REVOKE ALL khỏi role ứng dụng
        # S1: CHECK hai trị (coalesce(..., false) + IS NOT NULL từng cột) cho bộ ZIP quan sát, mapping dòng và ứng viên
        qs = next(s for s in M0015_M2_BRIDGE if s.startswith("CREATE TABLE kho.hoa_don_quan_sat"))
        self.assertIn("CHECK (coalesce((container_sha256 IS NULL AND entry_ordinal IS NULL AND entry_name IS NULL)", qs)
        self.assertIn("container_sha256 IS NOT NULL AND entry_ordinal IS NOT NULL AND entry_name IS NOT NULL", qs)
        mp = next(s for s in M0015_M2_BRIDGE if "anh_xa_nguon_target_m2_check" in s)
        for ma in ("CHECK (coalesce(", "line_native_xml_sha256 IS NOT NULL", "line_identity_binding IS NOT NULL", "array_position(line_identity_binding, NULL) IS NULL",
                   "line_ung_vien_id IS NOT NULL", "line_container_sha256 IS NOT NULL AND line_entry_ordinal IS NOT NULL AND line_entry_name IS NOT NULL",
                   "), false))"):
            self.assertIn(ma, mp)


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test PostgreSQL M2 không chạy (không tính đạt)")
class PgM0015(unittest.TestCase):
    def ket_noi(self, prefix):
        name = prefix + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{name}" ENCODING \'UTF8\' TEMPLATE template0')
        c = psycopg.connect(ADMIN_DSN.rsplit("/", 1)[0] + "/" + name, autocommit=True)
        self.addCleanup(c.close)  # chỉ đóng kết nối; DB giữ làm bằng chứng
        return c

    @staticmethod
    def bang(c):
        return {r[0] for r in c.execute("""SELECT n.nspname || '.' || c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                                           WHERE c.relkind IN ('r','v') AND n.nspname IN ('master','kho','giao_tiep','nhat_ky','bao_mat')""")}

    def test_fresh_0_den_15(self):
        c = self.ket_noi("kho_test_m2mig_moi_")
        self.assertEqual(pg.migrate(c), 15)
        self.assertEqual(pg.migrate(c), 15)
        self.assertTrue(M2_TABLES | {"kho.mua_dong_hien_hanh"} <= self.bang(c))
        self.assertEqual(pg.kiem_lich_su([tuple(r) for r in c.execute("SELECT version, checksum FROM master.schema_migrations ORDER BY 1")]), 15)

    def test_nang_cap_14_den_15_giu_hang_cu(self):
        c = self.ket_noi("kho_test_m2mig_up_")
        self.assertEqual(pg.migrate(c, target=14), 14)
        truoc_bang = self.bang(c)
        pn = c.execute("INSERT INTO master.phap_nhan (ma, ten) VALUES ('M2_UP_PN','PN nâng cấp') RETURNING id").fetchone()[0]
        ct = c.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, hash, so_tien_minor, tien_te)
                          VALUES (%s,'HD_MUA','OLD-HDMUA','2026-08-01',%s,1100,'VND') RETURNING id, module_nghiep_vu""", (pn, "1" * 64)).fetchone()
        self.assertEqual(ct[1], "M1")
        c.execute("INSERT INTO kho.chung_tu_dong (chung_tu_id, stt, mo_ta, no_minor, co_minor) VALUES (%s,1,'cũ',1100,0)", (ct[0],))
        cu = c.execute("SELECT to_jsonb(x)::text FROM kho.chung_tu x WHERE x.id = %s", (ct[0],)).fetchone()[0]
        cu_dong = c.execute("SELECT to_jsonb(x)::text FROM kho.chung_tu_dong x WHERE x.chung_tu_id = %s", (ct[0],)).fetchone()[0]
        # catalog nội dung nguồn dùng chung (M0013) có hàng cũ: M0015 chỉ thêm UNIQUE cho FK tài liệu khai báo, hàng giữ nguyên
        c.execute("INSERT INTO master.nguon_master_noi_dung (reference_id, raw_sha256, byte_length) VALUES ('OLD_MASTER_R14', %s, 7)", ("6" * 64,))
        cu_cat = c.execute("SELECT to_jsonb(x)::text FROM master.nguon_master_noi_dung x WHERE reference_id = 'OLD_MASTER_R14'").fetchone()[0]
        self.assertEqual(pg.migrate(c), 15)
        self.assertEqual(c.execute("SELECT to_jsonb(x)::text FROM master.nguon_master_noi_dung x WHERE reference_id = 'OLD_MASTER_R14'").fetchone()[0], cu_cat)
        self.assertEqual(c.execute("SELECT to_jsonb(x)::text FROM kho.chung_tu x WHERE x.id = %s", (ct[0],)).fetchone()[0], cu)  # ID/giá trị/owner giữ
        self.assertEqual(c.execute("SELECT to_jsonb(x)::text FROM kho.chung_tu_dong x WHERE x.chung_tu_id = %s", (ct[0],)).fetchone()[0], cu_dong)
        self.assertTrue(truoc_bang <= self.bang(c))
        # HD_MUA mới không khai M2 vẫn M1 (caller cũ không đổi hành vi); M2 chỉ khi projector chủ bảng khai, tiền/Nợ/Có phải NULL
        self.assertEqual(c.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, hash) VALUES (%s,'HD_MUA','NEW-M1','2026-08-02',%s)
                                      RETURNING module_nghiep_vu""", (pn, "2" * 64)).fetchone()[0], "M1")
        with self.assertRaises(psycopg.Error):
            c.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, hash, module_nghiep_vu, so_tien_minor)
                         VALUES (%s,'HD_MUA','M2-TIEN','2026-08-03',%s,'M2',100)""", (pn, "3" * 64))
        m2 = c.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, hash, module_nghiep_vu)
                          VALUES (%s,'HD_MUA','M2-OK','2026-08-03',%s,'M2') RETURNING id""", (pn, "4" * 64)).fetchone()[0]
        with self.assertRaises(psycopg.Error):  # bỏ trống no/co → DEFAULT 0 cũ → guard M2 từ chối (phải NULL tường minh)
            c.execute("INSERT INTO kho.chung_tu_dong (chung_tu_id, stt, mo_ta) VALUES (%s,1,'thiếu NULL')", (m2,))
        c.execute("INSERT INTO kho.chung_tu_dong (chung_tu_id, stt, mo_ta, no_minor, co_minor) VALUES (%s,1,'NULL',NULL,NULL)", (m2,))
        with self.assertRaises(psycopg.Error):  # dòng không phải M2/M5 vẫn phải có no/co
            c.execute("INSERT INTO kho.chung_tu_dong (chung_tu_id, stt, no_minor, co_minor) VALUES (%s,2,NULL,NULL)", (ct[0],))
        # INVOICE_LINE không seed bằng ROOT_SEED: setup instance/profile HỢP LỆ ngoài khối assert (lỗi setup phải nổi lên, không giả PASS),
        # rồi kiểm đúng mã của chính INSERT mapping + 0 delta
        c.execute("""INSERT INTO master.nguon_instance (source_instance_id) VALUES ('X_M2_SEED_TEST')""")
        c.execute("""INSERT INTO master.nguon_profile (source_instance_id, profile_ref, profile_sha256, payload) VALUES ('X_M2_SEED_TEST','R',%s,'{"module":"M2"}')""",
                  ("5" * 64,))
        truoc = c.execute("SELECT count(*) FROM master.anh_xa_nguon").fetchone()[0]
        with self.assertRaises(psycopg.Error) as cm:
            c.execute("""INSERT INTO master.anh_xa_nguon (reference_id, revision, source_instance_id, profile_ref, profile_sha256, subject_kind, subject_key,
                         phap_nhan_id, valid_from, nguon_quyet_dinh, duyet_boi) VALUES ('L',1,'X_M2_SEED_TEST','R',%s,'INVOICE_LINE','k',%s,now(),
                         'ROOT_SEED_DEMO','ROOT_SEED_DEMO')""", ("5" * 64, pn))
        self.assertIn("ANH_XA_SEED_SAI", str(cm.exception))
        self.assertEqual(c.execute("SELECT count(*) FROM master.anh_xa_nguon").fetchone()[0], truoc)

    def test_legacy13_tu_choi_truoc_ghi(self):
        c = self.ket_noi("kho_test_m2mig_legacy_")
        pg.migrate(c, target=12)
        c.execute("INSERT INTO master.schema_migrations VALUES (13, %s, '2026-10-19T00:00:00Z')", (LEGACY_FULL_M9_M0013_SHA256,))
        truoc = self.bang(c)
        with self.assertRaises(DataError) as cm:
            pg.migrate(c)
        self.assertEqual(cm.exception.code, "LEGACY_FULL_M9_LINEAGE")
        self.assertEqual(self.bang(c), truoc)


if __name__ == "__main__":
    unittest.main()
