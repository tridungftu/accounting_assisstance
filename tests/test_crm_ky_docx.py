"""KY-DOCX (QD-20261025-27, M0036) — cho ký trên bản DOCX: kiểm TĨNH hằng SQL M0036 + (có điều kiện) PostgreSQL THẬT "áp sạch".

Phân loại (không lẫn bằng chứng):
- `M36Tinh`: TĨNH trên byte mã nguồn/hằng SQL — M0036 append đúng thứ tự 36, M0001–M0035 nguyên byte (ghim tiền tố tệp), mỗi hàm tạo lại từ
  định nghĩa HIỆN HÀNH (M0023/M0032) chỉ khác đúng các dòng chủ đích; G5 bản sinh chỉ DOCX → HOLD/cần kiểm tay, không bao giờ tự KHOP.
- `M36CsdlThat`: PostgreSQL THẬT (KHO_PG_DSN_TEST) — DB mới `kho_test_kydocx_*` migrate tới bản hiện hành: hàng 36 + checksum, cột PDF G3 cho NULL,
  CHECK cặp, thân hàm đã triển khai đúng định nghĩa cuối trong chuỗi migration. Thiếu DSN/psycopg → skip (NOT_RUN, không tính đạt). Ca luồng thật (soạn → xuất DOCX →
  Chờ ký → ký trên DOCX; ký sai/DA_CU/PDF lệch bị chặn; G5 đánh dấu kiểm tay) ở tests/test_crm_ky_ket_http.py (k01, k05, k09).
Dữ liệu tổng hợp; không dữ liệu thật, không M9, không xóa tệp/CSDL (runner dọn `kho_test_*`).
"""

from __future__ import annotations

import difflib
import hashlib
import os
import re
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2 import crm_ky_ket as KY
from kho_tri_thuc.k2.sql_crm_doi_chieu import CRM_G5_SQL

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
PREFIX_M34_BYTES = 982_239  # toàn pg_migrations.py tới hết M0034 (hop-nhat 6e571f4), giữ ghim cũ
PREFIX_M35_BYTES = 982_757  # toàn tệp tới hết M0035 (mốc dự án), trước khối KY-DOCX
PREFIX_M35_SHA256 = "aa6dbe40a5749e2a796069c2b0158c86d82f7c926a770b18665a26d0dc81092c"
PREFIX_M34_SHA256 = "bab8ad3706dac269f2523831b2b2d7203ac61f439f9278d0388152dee21d2ce0"
TT_DOCX = "('PDF_DAT','PDF_CHUA_SAN_SANG','PDF_LOI')"
M36 = "\n".join(PM.M0036_KY_DOCX)


def _ham(goc, ten, schema="master"):
    ds = [s for s in goc if s.lstrip().startswith(f"CREATE OR REPLACE FUNCTION {schema}.{ten}(")]
    assert len(ds) == 1, (ten, len(ds))
    return ds[0]


def _khac(goc, ten):
    """(dòng bỏ, dòng thêm) giữa định nghĩa hiện hành trước M0036 và định nghĩa M0036."""
    a, b = _ham(goc, ten).splitlines(), _ham(PM.M0036_KY_DOCX, ten).splitlines()
    bo = [x[1:] for x in difflib.unified_diff(a, b, lineterm="", n=0) if x.startswith("-") and not x.startswith("---")]
    them = [x[1:] for x in difflib.unified_diff(a, b, lineterm="", n=0) if x.startswith("+") and not x.startswith("+++")]
    return bo, them


def _ham_hien_hanh(ten, schema="master"):
    """Migration chạy sau ghi đè định nghĩa cùng hàm; giữ kiểm M0036 tĩnh riêng."""
    return next(s for migration in reversed(PM.PG_MIGRATIONS) for s in reversed(migration)
                if s.lstrip().startswith(f"CREATE OR REPLACE FUNCTION {schema}.{ten}("))


class M36Tinh(unittest.TestCase):
    def test_tra_ham_hien_hanh_theo_thu_tu_migration(self):
        ten = "crm_kiem_g5_xet"
        self.assertEqual(_ham_hien_hanh(ten), _ham(PM.M0037_CRM_G5_TAY, ten))
        self.assertEqual(_ham_hien_hanh("crm_ky_ket"), _ham(PM.M0065_MTQ_CRM_C, "crm_ky_ket"))
        for schema, guard in (("kho", "crm_kiem_viec_kiem"), ("master", "crm_kiem_ho_so_kiem")):
            self.assertEqual(_ham_hien_hanh(guard, schema), _ham(PM.M0037_CRM_G5_TAY, guard, schema))
        moi = "CREATE OR REPLACE FUNCTION master.crm_kiem_g5_xet(p_ky uuid, p_che_do text) RETURNS jsonb AS $$ SELECT '{}'::jsonb $$"
        with patch.object(PM, "PG_MIGRATIONS", (*PM.PG_MIGRATIONS, (moi,))):
            self.assertEqual(_ham_hien_hanh(ten), moi)
        moi_kho = "CREATE OR REPLACE FUNCTION kho.crm_kiem_viec_kiem() RETURNS trigger AS $$ BEGIN RETURN NEW; END $$"
        with patch.object(PM, "PG_MIGRATIONS", (*PM.PG_MIGRATIONS, (moi_kho,))):
            self.assertEqual(_ham_hien_hanh("crm_kiem_viec_kiem", "kho"), moi_kho)

    def test_dang_ky_thu_tu_36_va_tien_to_nguyen_byte(self):
        self.assertIs(PM.PG_MIGRATIONS[35], PM.M0036_KY_DOCX)
        self.assertIs(PM.PG_MIGRATIONS[34], PM.M0035_CRM_DU_AN_MOC)
        self.assertIs(PM.PG_MIGRATIONS[33], PM.M0034_CONG_AI_NHAT_KY)
        self.assertGreaterEqual(PM.PG_SCHEMA_VERSION, 36)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        self.assertEqual(sum(m is PM.M0036_KY_DOCX for m in PM.PG_MIGRATIONS), 1)
        self.assertNotIn(PM._hash(PM.M0036_KY_DOCX), [PM._hash(m) for m in PM.PG_MIGRATIONS[:35]])
        self.assertFalse(any(m is PM.M0036_KY_DOCX for m in PM.PG_MIGRATIONS_LICH_SU_FULL_M9))
        raw = (SRC / "ha_tang" / "pg_migrations.py").read_bytes()
        self.assertEqual(hashlib.sha256(raw[:PREFIX_M34_BYTES]).hexdigest(), PREFIX_M34_SHA256)  # M0001–M0034 nguyên byte
        self.assertEqual(hashlib.sha256(raw[:PREFIX_M35_BYTES]).hexdigest(), PREFIX_M35_SHA256)  # M0001–M0035 nguyên byte
        duoi = raw[PREFIX_M35_BYTES:].decode("utf-8")
        self.assertTrue(duoi.startswith("\n# ---------------------------------------------------------------------------\n# 0036 — KY-DOCX"), duoi[:120])
        self.assertEqual(duoi.count("PG_MIGRATIONS = (*PG_MIGRATIONS, M0036_KY_DOCX)\nPG_SCHEMA_VERSION = len(PG_MIGRATIONS)"), 1)

    def test_bang_ky_pdf_g3_tuy_chon_cap_cung_null(self):
        self.assertEqual(PM.M0036_KY_DOCX[0],
                         "ALTER TABLE master.crm_hd_ky ALTER COLUMN g3_pdf_sha256 DROP NOT NULL, ALTER COLUMN g3_pdf_len DROP NOT NULL")
        self.assertEqual(PM.M0036_KY_DOCX[1],
                         "ALTER TABLE master.crm_hd_ky ADD CONSTRAINT crm_hd_ky_g3_pdf_cap CHECK ((g3_pdf_sha256 IS NULL) = (g3_pdf_len IS NULL))")
        # chỉ HAI câu DDL bảng, đều trên crm_hd_ky: DOCX của bản ký vẫn bắt buộc; bảng G5/G6A giữ PDF G3 NOT NULL (bản sinh chỉ DOCX không tới đó)
        ddl = [s for s in PM.M0036_KY_DOCX if not s.lstrip().startswith("CREATE OR REPLACE FUNCTION master.")]
        self.assertEqual(ddl, list(PM.M0036_KY_DOCX[:2]))
        for cam in ("g3_docx_sha256 DROP NOT NULL", "g3_docx_len DROP NOT NULL", "DROP CONSTRAINT", "DROP TABLE", "DROP FUNCTION", "DROP TRIGGER",
                    "CREATE TRIGGER", "CREATE TABLE", "ALTER TABLE master.crm_g5", "ALTER TABLE master.crm_kiem"):
            self.assertNotIn(cam, M36, cam)

    def test_xuat_ghi_cho_ky_khi_co_docx_dung_revision(self):
        bo, them = _khac(PM.M0023_CRM_KY, "crm_gk_xuat_ghi")
        self.assertEqual(bo, ["                IF tt = 'PDF_DAT' THEN"])
        self.assertEqual(len(them), 1)
        self.assertTrue(them[0].startswith(f"                IF tt IN {TT_DOCX} THEN"), them)
        moi = _ham(PM.M0036_KY_DOCX, "crm_gk_xuat_ghi")
        # giữ: CAS revision + đã ký → DA_CU (không CHO_KY); lần đặt chỗ phải khớp; PDF chỉ lưu khi PDF_DAT
        for can in ("cu_rev := s.revision_hien_hanh <> p_revision OR s.trang_thai = 'DA_KY';", "IF cu_rev THEN tt := 'DA_CU'; END IF;",
                    "CRM_GK_LAN_KHONG_KHOP", "CASE WHEN tt = 'PDF_DAT' THEN p_pdf_sha END",
                    "UPDATE master.crm_hd_soan SET trang_thai = 'CHO_KY'", "UPDATE master.hop_dong SET trang_thai = 'CHO_KY', crm_giao_ket = 'CHO_KY'"):
            self.assertIn(can, moi, can)
        self.assertLess(moi.index("IF cu_rev THEN tt := 'DA_CU'; END IF;\n                INSERT INTO master.crm_gk_xuat (phap_nhan_id, loai, soan_id"),
                        moi.index(f"IF tt IN {TT_DOCX} THEN"))
        self.assertNotIn("'DA_CU'", them[0])

    def test_trigger_ban_ky_gan_docx_pdf_khop_khi_co(self):
        bo, them = _khac(PM.M0023_CRM_KY, "crm_hd_ky_kiem")
        self.assertEqual(len(bo), 2, bo)
        self.assertIn("x.trang_thai IS DISTINCT FROM 'PDF_DAT'", bo[0])
        self.assertEqual([x.strip() for x in them[:2]],
                         [f"OR x.trang_thai IS NULL OR x.trang_thai NOT IN {TT_DOCX}",
                          "OR x.pdf_sha256 IS DISTINCT FROM NEW.g3_pdf_sha256 OR x.pdf_len IS DISTINCT FROM NEW.g3_pdf_len"])
        self.assertIn("DOCX của revision hiện hành, PDF khớp khi có", them[2])
        moi = _ham(PM.M0036_KY_DOCX, "crm_hd_ky_kiem")
        for can in ("s.trang_thai IS DISTINCT FROM 'CHO_KY'", "s.revision_hien_hanh IS DISTINCT FROM NEW.revision", "x.loai IS DISTINCT FROM 'HOP_DONG'",
                    "x.revision IS DISTINCT FROM NEW.revision", "x.docx_sha256 IS DISTINCT FROM NEW.g3_docx_sha256",
                    "x.docx_len IS DISTINCT FROM NEW.g3_docx_len", "x.input_sha256 IS DISTINCT FROM NEW.g3_input_sha256",
                    "x.engine IS DISTINCT FROM NEW.g3_engine", "r.du_lieu_sha256 IS DISTINCT FROM NEW.du_lieu_sha256", "CRM_KY_G3_LECH"):
            self.assertIn(can, moi, can)
        self.assertNotIn("DA_CU", TT_DOCX)

    def test_lenh_ky_can_cu_docx_thu_tu_giu_nguyen(self):
        bo, them = _khac(PM.M0023_CRM_KY, "crm_ky_ket")
        self.assertEqual(len(bo), 4, bo)
        self.assertEqual(len(them), 4, them)
        f = _ham(PM.M0036_KY_DOCX, "crm_ky_ket")
        thu_tu = ["crm_g_ghim_quyen", "crm_ky_pham_vi b", "crm_ky_dich(p_soan)", "crm_g_bn_tra", "CRM_KY_KHAI_SAI", "CRM_KY_NGAY_SAI", "CRM_G_YEU_CAU_SAI",
                  "FOR UPDATE", "CRM_KY_DA_KY", "CRM_KY_TRANG_THAI", "CRM_GK_REVISION_CU", "ORDER BY tao_luc DESC, id DESC LIMIT 1", "CRM_KY_XUAT_CU",
                  "CRM_KY_XUAT_CHUA_DAT", "CRM_KY_G3_LECH", "CRM_GK_MAU_LECH_GHIM", "INSERT INTO master.crm_hd_ky ", "INSERT INTO master.crm_hd_ky_g5",
                  "UPDATE master.crm_hd_soan SET trang_thai = 'DA_KY'", "crm_g_bn_ghi"]
        vt = [f.index(x) for x in thu_tu]
        self.assertEqual(vt, sorted(vt), list(zip(thu_tu, vt)))
        for can in ("(p_g3_pdf_sha IS NULL) <> (p_g3_pdf_len IS NULL)", f"IF xm.trang_thai NOT IN {TT_DOCX} OR xm.docx_sha256 IS NULL",
                    "xm.pdf_sha256 IS DISTINCT FROM p_g3_pdf_sha OR xm.pdf_len IS DISTINCT FROM p_g3_pdf_len", "xm.input_sha256 <> p_g3_input_sha",
                    "xm.id IS NULL OR xm.id <> p_xuat", "xm.docx_sha256, xm.docx_len, xm.pdf_sha256, xm.pdf_len"):
            self.assertIn(can, f, can)
        for cam in ("xm.trang_thai <> 'PDF_DAT'", "p_g3_pdf_sha IS NULL OR p_g3_pdf_len IS NULL", "xm.pdf_sha256 <> p_g3_pdf_sha"):
            self.assertNotIn(cam, f, cam)
        self.assertEqual(KY.XUAT_KY_DUOC, frozenset({"PDF_DAT", "PDF_CHUA_SAN_SANG", "PDF_LOI"}))  # service đồng bộ điều kiện CSDL

    def test_g5_ban_sinh_chi_docx_khong_tu_ket_luan_khop(self):
        """Hàm G5 chỉ THÊM khối (không bỏ dòng nào của M0032); bản sinh chỉ DOCX → HOLD/CHO_CAU_HINH 'G5_BAN_SINH_CHI_DOCX' trước mọi đường kết quả."""
        for ten in ("crm_kiem_g5_xet", "crm_g5_hang_doi", "crm_g5_nhan", "crm_g5_doc", "crm_g5_chay"):
            bo, them = _khac(CRM_G5_SQL, ten)
            self.assertEqual(bo, [], ten)
            self.assertTrue(any("g3_pdf_sha256 IS NULL" in x for x in them), ten)
        xet = _ham(PM.M0036_KY_DOCX, "crm_kiem_g5_xet")
        i = xet.index("k0.g3_pdf_sha256 IS NULL")
        self.assertLess(i, xet.index("IF p_che_do IS DISTINCT FROM 'SYNTHETIC_FIXTURE' THEN"))  # mọi chế độ
        khoi = xet[i:xet.index("END IF;", i)]
        self.assertIn("'trang_thai', 'HOLD'", khoi)
        self.assertIn("'chan', jsonb_build_array(jsonb_build_object('ma', 'G5_BAN_SINH_CHI_DOCX'))", khoi)
        self.assertNotIn("KHOP", khoi)
        hd = _ham(PM.M0036_KY_DOCX, "crm_g5_hang_doi")
        j = hd.index("k0.g3_pdf_sha256 IS NULL")
        self.assertLess(j, hd.index("crm_g5_nguoi_chay_hien_hanh"))
        self.assertLess(j, hd.index("kq := kq || jsonb_build_array"))  # không giao worker
        self.assertIn("CONTINUE;", hd[j:hd.index("kq := kq || jsonb_build_array")])
        nh = _ham(PM.M0036_KY_DOCX, "crm_g5_nhan")
        k = nh.index("k0.g3_pdf_sha256 IS NULL")
        self.assertLess(nh.index("'KHONG_DEN_HAN'"), k)
        for sau in ("SET trang_thai = 'DANG_CHAY'", "SELECT * INTO y FROM master.crm_g5_y_dinh", "'nhan', true"):
            self.assertLess(k, nh.index(sau), sau)  # trước khi giữ lease/đọc ý định/trả lineage
        for f, ly in ((hd, "'G5_BAN_SINH_CHI_DOCX'"), (nh, "'G5_BAN_SINH_CHI_DOCX'")):
            self.assertIn("trang_thai = 'CHO_CAU_HINH', ly_do = " + ly, f)  # việc vẫn MỞ (nghĩa vụ không đóng)
            self.assertNotIn("'XONG', ly_do = 'G5_BAN_SINH", f)
        doc = _ham(PM.M0036_KY_DOCX, "crm_g5_doc")
        self.assertIn("v_ly := v_ly || jsonb_build_array('G5_BAN_SINH_CHI_DOCX');\n                v_chay := false;", doc)
        self.assertLess(doc.index("v_chay := false;\n            END IF;\n"), doc.index("'quyen', jsonb_build_object('chay', v_chay"))
        chay = _ham(PM.M0036_KY_DOCX, "crm_g5_chay")
        self.assertLess(chay.index("CRM_G5_NGU_CANH_CU"), chay.index("CRM_G5_CAN_KIEM_TAY"))
        self.assertLess(chay.index("CRM_G5_CAN_KIEM_TAY"), chay.index("INSERT INTO master.crm_g5_viec"))
        # mã lý do hợp CHECK crm_g5_viec.ly_do / crm_g5_su_kien.loai
        self.assertRegex("G5_BAN_SINH_CHI_DOCX", r"^[A-Z0-9_]{1,80}$")
        self.assertRegex("CHO_CAU_HINH", r"^[A-Z0-9_]{1,40}$")

    def test_khong_producer_g5_khong_quyen_moi_khong_m4_m9(self):
        """M0036 = đúng 2 ALTER + 8 hàm tạo lại; phần THÊM (so với định nghĩa hiện hành) không có producer/kết quả G5, quyền mới, M4/M9."""
        ham = [(PM.M0023_CRM_KY, t) for t in ("crm_gk_xuat_ghi", "crm_hd_ky_kiem", "crm_ky_ket")] + \
              [(CRM_G5_SQL, t) for t in ("crm_kiem_g5_xet", "crm_g5_hang_doi", "crm_g5_nhan", "crm_g5_doc", "crm_g5_chay")]
        self.assertEqual(len(PM.M0036_KY_DOCX), 2 + len(ham))
        them = list(PM.M0036_KY_DOCX[:2])
        for goc, ten in ham:
            them += _khac(goc, ten)[1]
        moi = "\n".join(them)
        for cam in ("INSERT INTO", "crm_kiem_g5_", "set_config(", "GRANT ", "CREATE ROLE", "SECURITY DEFINER", "m4.", "khoan_vay",
                    "hop_dong_phien_ban", "lich_thu", "crm_g5_ket_qua", "crm_g5_y_dinh", "'KHOP'", "'XONG'", "HIEU_LUC"):
            self.assertNotIn(cam, moi, cam)


# ====================================================================== PostgreSQL THẬT (áp sạch; không dữ liệu)
try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None
ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")


def _than(stmt: str) -> str:
    """Thân $$…$$ của một CREATE FUNCTION trong hằng SQL — so với prosrc đã triển khai."""
    m = re.search(r"AS \$\$(.*)\$\$\s*$", stmt, re.S)
    assert m, stmt[:80]
    return m.group(1)


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "PostgreSQL thật chưa cấu hình (KHO_PG_DSN_TEST) — NOT_RUN, không tính đạt")
class M36CsdlThat(unittest.TestCase):
    """DB test MỚI (kho_test_kydocx_*), migrate tới bản hiện hành; chỉ đọc catalog. DB giữ lại (runner dọn kho_test_*)."""

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.ha_tang import postgres as pg
        cls.db = "kho_test_kydocx_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.c = psycopg.connect(ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db, autocommit=True)
        cls.addClassCleanup(cls.c.close)
        cls.version = pg.migrate(cls.c)

    def q(self, sql, *p):
        return self.c.execute(sql, p).fetchall()

    def test_m36_ap_sach_checksum(self):
        self.assertEqual(self.version, PM.PG_SCHEMA_VERSION)
        rows = [tuple(r) for r in self.q("SELECT version, checksum FROM master.schema_migrations ORDER BY version")]
        self.assertEqual(rows, [(i + 1, PM._hash(m)) for i, m in enumerate(PM.PG_MIGRATIONS)])
        self.assertEqual(rows[35], (36, PM._hash(PM.M0036_KY_DOCX)))

    def test_cot_pdf_g3_null_duoc_cap_check(self):
        cot = dict(self.q("""SELECT column_name, is_nullable FROM information_schema.columns WHERE table_schema = 'master' AND table_name = 'crm_hd_ky'
                             AND column_name IN ('g3_pdf_sha256', 'g3_pdf_len', 'g3_docx_sha256', 'g3_docx_len', 'g3_input_sha256')"""))
        self.assertEqual(cot, {"g3_pdf_sha256": "YES", "g3_pdf_len": "YES", "g3_docx_sha256": "NO", "g3_docx_len": "NO", "g3_input_sha256": "NO"})
        defs = [r[0] for r in self.q("""SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'master.crm_hd_ky'::regclass
                                        AND conname = 'crm_hd_ky_g3_pdf_cap'""")]
        self.assertEqual(len(defs), 1)
        self.assertIn("g3_pdf_sha256 IS NULL", defs[0])
        self.assertIn("g3_pdf_len IS NULL", defs[0])
        # bảng G5 vẫn đòi PDF G3 (bản sinh chỉ DOCX không tạo ý định/kết quả)
        for t in ("crm_g5_y_dinh", "crm_g5_ket_qua"):
            self.assertEqual(self.q("""SELECT is_nullable FROM information_schema.columns WHERE table_schema = 'master' AND table_name = %s
                                       AND column_name = 'g3_pdf_sha256'""", t), [("NO",)], t)

    def test_than_ham_trien_khai_dung_dinh_nghia_hien_hanh(self):
        for schema, ten, sig in (("master", "crm_gk_xuat_ghi", "(text, text, text, uuid, integer, text, text, bigint, text, bigint, text, text, text, jsonb)"),
                                ("master", "crm_hd_ky_kiem", "()"),
                                ("master", "crm_ky_ket", "(text, text, uuid, integer, uuid, text, text, bigint, text, bigint, integer, text, date, boolean, text, text, jsonb)"),
                                ("master", "crm_kiem_g5_xet", "(uuid, text)"), ("master", "crm_g5_hang_doi", "(integer)"),
                                ("master", "crm_g5_nhan", "(uuid, text, integer)"), ("master", "crm_g5_doc", "(uuid)"),
                                ("master", "crm_g5_chay", "(text, text, uuid, text)"),
                                ("kho", "crm_kiem_viec_kiem", "()"), ("master", "crm_kiem_ho_so_kiem", "()")):
            src = self.q(f"SELECT prosrc FROM pg_proc WHERE oid = '{schema}.{ten}{sig}'::regprocedure")[0][0]
            self.assertEqual(src, _than(_ham_hien_hanh(ten, schema)), f"{schema}.{ten}")
        # quyền giữ nguyên: hàm lệnh không cấp PUBLIC/vai ứng dụng
        for vai in ("app_web", "app_ke_toan", "app_doc", "app_cong_ai"):
            if not self.q("SELECT 1 FROM pg_roles WHERE rolname = %s", vai):
                continue
            for f in ("master.crm_ky_ket(text, text, uuid, integer, uuid, text, text, bigint, text, bigint, integer, text, date, boolean, text, text, jsonb)",
                      "master.crm_g5_chay(text, text, uuid, text)", "master.crm_g5_nhan(uuid, text, integer)"):
                self.assertFalse(self.q("SELECT has_function_privilege(%s, %s, 'EXECUTE')", vai, f)[0][0], (vai, f))


if __name__ == "__main__":
    unittest.main()
