"""CRM_BG1C_M30_REGISTRATION — BG-1c: bước kiểm khi Ký tính lịch theo Tổng VND (QD-20261025-02) thành migration 30.

CHỈ thuần (không CSDL, không driver/kết nối PG, không bootstrap/seed/SET ROLE/M9/mạng):
  - toàn bộ 976.492 byte đầu ``pg_migrations.py`` = baseline 29 (SHA ghim ở đây và ở ``test_m4_03b_m29_integration.py``, không lấy từ code);
  - đoạn M30 = từ mốc 976.492 đến hết dòng ``PG_SCHEMA_VERSION = len(PG_MIGRATIONS)`` ĐẦU TIÊN sau mốc; chỉ import + alias + MỘT tuple đăng ký +
    version; không bản sao SQL. Phần sau đoạn này (31+) KHÔNG thuộc test này;
  - registry baseline 1–29 dựng lại TỪ CHÍNH prefix gốc (exec độc lập) khớp từng câu/checksum; M25 (``CRM_G6A_SQL``) giữ nguyên object/checksum;
  - M30 = ĐÚNG MỘT câu ``CREATE OR REPLACE FUNCTION master.crm_kiem_lich_ky(p_ky uuid)`` cùng khai báo với M0025; thân giữ mọi dòng/mã lỗi của
    M0025 (trừ 3 dòng thay có chủ đích), không bảng/trigger/quyền/dữ liệu mới;
  - module hằng SQL nguyên byte (SHA ghim), không import registry/ha_tang, không tự author ordinal.

Bằng chứng áp dụng thật (migrate 29 → 30 trên CSDL DEMO riêng, gọi hàm trên dữ liệu v2) là bước riêng của lát (báo cáo BG-1c).
"""

from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2 import crm_giao_ket as GK
from kho_tri_thuc.k2 import sql_crm_bg1c as B
from kho_tri_thuc.k2 import sql_crm_kiem_hd as K
from kho_tri_thuc.k2 import sql_ghi_nhan_chung as SG

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
PG_PY = SRC / "ha_tang" / "pg_migrations.py"
SQL_PY = SRC / "k2" / "sql_crm_bg1c.py"

# ghim (không tính lại từ code đang chạy)
PREFIX_BYTES, PREFIX_SHA256 = 976_492, "7817b70da2b3457ac16add058fc894b7484aae12fc7c399e67b24ac0ef99fc07"  # toàn pg_migrations.py baseline 29
M30_END, M30_PREFIX_SHA256 = 977_387, "59d8178346925f1f8cb492a88ce243324c35ca81e29205bc9dd961b4557230c5"  # toàn pg_migrations.py baseline 30
SQL_SHA256 = "f824b966ae6bf3cfb51b5821e6c917a7baabb1f07e75e3a77a6ce5526c77ff83"  # k2/sql_crm_bg1c.py, xuống dòng chuẩn hóa LF
M30_JOINED_SHA256 = "0a717d27a58d0d3cce42b3bf45ec119e27b74c8ce42b267c4248e305a55e8034"  # _hash(câu 30) = sha256("\n".join)
VERSION_DONG = b"PG_SCHEMA_VERSION = len(PG_MIGRATIONS)\n"
DONG_NOI = ("from ..k2.sql_crm_bg1c import CRM_BG1C_SQL  # noqa: E402 — module chỉ hằng SQL, không import ha_tang",
            "M0030_CRM_BG1C = CRM_BG1C_SQL",
            "PG_MIGRATIONS = (*PG_MIGRATIONS, M0030_CRM_BG1C)",
            "PG_SCHEMA_VERSION = len(PG_MIGRATIONS)")
DAU_HAM = "CREATE OR REPLACE FUNCTION master.crm_kiem_lich_ky(p_ky uuid) RETURNS jsonb"
# 3 dòng M0025 được THAY có chủ đích (đã strip): tiền chính theo dữ liệu v2, ghi đè trước gia.tong, ghi đè sai không rơi về tích
DONG_THAY = {"v_tt := v_bg -> 'gia' ->> 'tien_te';",
             "IF coalesce((v_bg -> 'gia' ->> 'tong') ~ '^[0-9]{1,24}(\\.[0-9]{1,12})?$', false) THEN",
             "IF v_tong IS NULL AND v_tich IS NOT NULL THEN"}


def _doan_m30(raw: bytes) -> bytes:
    cuoi = raw.find(VERSION_DONG, PREFIX_BYTES)
    if cuoi < 0:
        raise AssertionError("không thấy dòng version kết thúc khối đăng ký M30 sau mốc 29")
    return raw[PREFIX_BYTES:cuoi + len(VERSION_DONG)]


def _baseline29() -> dict:
    raw = PG_PY.read_bytes()[:PREFIX_BYTES]
    ns = {"__name__": "kho_tri_thuc.ha_tang._pg_baseline29", "__package__": "kho_tri_thuc.ha_tang", "__file__": str(PG_PY)}
    exec(compile(raw, str(PG_PY) + ":baseline29", "exec"), ns)  # noqa: S102 — mã nguồn của chính repo, không nhận đầu vào ngoài
    return ns


def _ham_m25() -> str:
    cau = [s for s in K.CRM_G6A_SQL if "FUNCTION master.crm_kiem_lich_ky(" in s]
    assert len(cau) == 1
    return cau[0]


def _ma_loi(sql: str) -> set:
    return set(re.findall(r"'ma', '([A-Z0-9_]+)'", sql)) | set(re.findall(r"'([A-Z][A-Z0-9_]{3,})'::text", sql))


class M30Prefix(unittest.TestCase):
    def test_prefix_baseline29_nguyen_byte(self):
        raw = PG_PY.read_bytes()
        self.assertGreater(len(raw), PREFIX_BYTES)
        self.assertEqual(hashlib.sha256(raw[:PREFIX_BYTES]).hexdigest(), PREFIX_SHA256, "prefix baseline 29 bị sửa — chỉ được APPEND")
        truoc = raw[:PREFIX_BYTES].decode("utf-8")
        self.assertTrue(truoc.endswith("M0029_M4_GHI_NHAN_CHUNG = M4_03B_COMMON_SQL\nPG_MIGRATIONS = (*PG_MIGRATIONS, M0029_M4_GHI_NHAN_CHUNG)\n"
                                       "PG_SCHEMA_VERSION = len(PG_MIGRATIONS)\n"), "prefix phải dừng đúng sau khối đăng ký M29")
        for x in ("CRM_BG1C_SQL", "sql_crm_bg1c", "M0030"):
            self.assertNotIn(x, truoc)

    def test_doan_m30_chi_import_alias_mot_dang_ky(self):
        raw = PG_PY.read_bytes()
        self.assertGreaterEqual(len(raw), M30_END)
        self.assertEqual(hashlib.sha256(raw[:M30_END]).hexdigest(), M30_PREFIX_SHA256, "đoạn M30 bị sửa — chỉ được APPEND sau mốc 30")
        doan = _doan_m30(raw)
        self.assertEqual(PREFIX_BYTES + len(doan), M30_END)
        doan = doan.decode("utf-8")
        ma = tuple(x.rstrip() for x in doan.splitlines() if x.strip() and not x.lstrip().startswith("#"))
        self.assertEqual(ma, DONG_NOI, "đoạn M30 chỉ được import + alias + một tuple đăng ký + version")
        self.assertNotRegex("\n".join(ma), r"(?i)\b(CREATE|ALTER|DROP|GRANT|REVOKE|INSERT|UPDATE|DELETE)\s")  # không bản sao SQL
        self.assertNotRegex(doan, r"psycopg|connect\(|bootstrap|FULL_M9|TUONG_THICH")
        txt = PG_PY.read_text(encoding="utf-8")
        self.assertEqual(txt.count("import CRM_BG1C_SQL"), 1)
        self.assertEqual(len(re.findall(r"^M0030_CRM_BG1C = ", txt, re.M)), 1)
        self.assertEqual(len(re.findall(r"^PG_MIGRATIONS = \(\*PG_MIGRATIONS, M0030_CRM_BG1C\)$", txt, re.M)), 1)

    def test_module_sql_nguyen_byte_khong_import_registry(self):
        raw = SQL_PY.read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), SQL_SHA256, "module hằng SQL BG-1c bị sửa")
        src = raw.decode("utf-8")
        self.assertIsNone(re.search(r"^\s*(from|import)\s", src, re.M))  # không import gì (kể cả module SQL khác): thân hàm ghim nguyên byte
        self.assertNotIn("M0030", src)
        self.assertNotIn("PG_MIGRATIONS", src)


class M30Registry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.B = _baseline29()

    def test_baseline_dung_lai_la_29(self):
        b = self.B["PG_MIGRATIONS"]
        self.assertEqual((len(b), self.B["PG_SCHEMA_VERSION"]), (29, 29))
        self.assertIs(b[28], SG.M4_03B_COMMON_SQL)
        self.assertFalse(any(m is B.CRM_BG1C_SQL for m in b))

    def test_prefix_1_29_tung_cau_va_checksum(self):
        b = self.B["PG_MIGRATIONS"]
        for i in range(29):
            self.assertEqual(tuple(PM.PG_MIGRATIONS[i]), tuple(b[i]), f"migration {i + 1} đổi câu lệnh")
            self.assertEqual(PM._hash(PM.PG_MIGRATIONS[i]), self.B["_hash"](b[i]), f"migration {i + 1} đổi checksum")
        self.assertIs(PM.PG_MIGRATIONS[24], K.CRM_G6A_SQL)  # M0025 nguyên object (không sửa)
        self.assertIs(PM.PG_MIGRATIONS[24], PM.M0025_CRM_G6A)
        self.assertEqual(PM.PG_MIGRATION_TUONG_THICH, self.B["PG_MIGRATION_TUONG_THICH"])
        self.assertNotIn(30, set(PM.PG_MIGRATION_TUONG_THICH))
        self.assertEqual(PM.PG_MIGRATIONS_LICH_SU_FULL_M9, self.B["PG_MIGRATIONS_LICH_SU_FULL_M9"])
        self.assertEqual(PM.LEGACY_FULL_M9_M0013_SHA256, self.B["LEGACY_FULL_M9_M0013_SHA256"])

    def test_m30_dung_mot_lan_cung_object(self):
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        self.assertGreaterEqual(PM.PG_SCHEMA_VERSION, 30)
        self.assertIs(PM.PG_MIGRATIONS[29], B.CRM_BG1C_SQL)
        self.assertIs(PM.M0030_CRM_BG1C, B.CRM_BG1C_SQL)
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS) if m is B.CRM_BG1C_SQL], [29])
        h30 = PM._hash(PM.PG_MIGRATIONS[29])
        self.assertEqual(h30, M30_JOINED_SHA256, "checksum joined câu 30 lệch pin")
        self.assertNotIn(h30, [PM._hash(m) for m in PM.PG_MIGRATIONS[:29]])
        self.assertFalse(any(m is B.CRM_BG1C_SQL for m in PM.PG_MIGRATIONS_LICH_SU_FULL_M9))

    def test_ham_duy_nhat_dinh_nghia_o_m25_truoc_m30(self):
        co = [i for i, m in enumerate(PM.PG_MIGRATIONS) if any("FUNCTION master.crm_kiem_lich_ky(" in s for s in m)]
        self.assertEqual(co, [24, 29])  # M0025 tạo, M0030 thay thân; không migration nào khác chạm


class M30NoiDung(unittest.TestCase):
    def test_chi_mot_cau_thay_than_ham_cung_khai_bao(self):
        self.assertIsInstance(B.CRM_BG1C_SQL, tuple)
        self.assertEqual(len(B.CRM_BG1C_SQL), 1)
        moi, cu = B.CRM_BG1C_SQL[0], _ham_m25()
        self.assertTrue(moi.startswith(DAU_HAM))
        self.assertEqual(moi.splitlines()[:2], cu.splitlines()[:2])  # cùng chữ ký, kiểu trả, LANGUAGE/STABLE/search_path
        self.assertEqual(moi.count("CREATE OR REPLACE FUNCTION"), 1)
        than = moi.split("AS $$", 1)[1]
        self.assertNotRegex(than, r"(?i)\b(CREATE|ALTER|DROP|GRANT|REVOKE|INSERT|UPDATE|DELETE|TRIGGER|POLICY|SECURITY DEFINER)\b")
        self.assertTrue(moi.rstrip().endswith("END $$"))

    def test_giu_moi_dong_va_ma_loi_cua_m25(self):
        cu = [x.strip() for x in _ham_m25().splitlines() if x.strip()]
        moi = [x.strip() for x in B.CRM_BG1C_SQL[0].splitlines() if x.strip()]
        it = iter(moi)
        mat = [x for x in cu if x not in DONG_THAY and not any(x == y for y in it)]
        self.assertEqual(mat, [], "thân M0025 phải là dãy con của thân M0030 (trừ 3 dòng thay có chủ đích)")
        self.assertTrue(DONG_THAY <= set(cu))  # 3 dòng thay thực sự có trong M0025
        self.assertFalse(DONG_THAY & set(moi))
        self.assertTrue(_ma_loi(_ham_m25()) <= _ma_loi(B.CRM_BG1C_SQL[0]))  # không bỏ kiểm nào (QD-20261024-02)
        self.assertEqual(_ma_loi(B.CRM_BG1C_SQL[0]) - _ma_loi(_ham_m25()), {"VND_TY_GIA_KHAC_1", "USD_THIEU_FX", "TONG_GIA_TRI_GHI_DE_SAI"})

    def test_cung_cong_thuc_voi_may_chu(self):
        sql = B.CRM_BG1C_SQL[0]
        self.assertEqual(GK.TIEN_CHINH, "VND")
        self.assertIn("coalesce(v_bg ->> 'tien_chinh', '') = 'VND'", sql)  # cùng dấu dữ liệu v2 với chuan_hoa_bao_gia
        self.assertIn("round((v_bg -> 'gia' ->> 'don_gia')::numeric * v_fx * (v_bg -> 'gia' ->> 'dien_tich')::numeric, 0)", sql)
        self.assertIn("v_bg -> 'tong_gia_tri_ghi_de'", sql)
        # cùng miền chuỗi số kiểu Việt với ô ghi đè của máy chủ (_gia_tri_nhap)
        mau_vn = re.search(r"!~ '(\^\(\[0-9\]\+\|[^']+)'", sql).group(1).replace("\\\\", "\\")
        for v, ok in (("39.000.000.000", True), ("1.400.000,50", True), ("1500", True), ("1,40", True), ("1.40", False), ("1,400.00", False),
                      ("100%", False), ("-1", False), ("1 000", False)):
            with self.subTest(v=v):
                self.assertEqual(bool(re.fullmatch(mau_vn.strip("^$"), v)), ok)
                self.assertEqual(GK._gia_tri_nhap(v)[2] is None and "%" not in v, ok)
        # làm tròn nửa lên của Python trùng round(numeric, 0) của PostgreSQL với số ≥ 0
        from decimal import ROUND_HALF_UP, Decimal
        from fractions import Fraction
        for x in ("0.5", "1.5", "2.5", "31250.625", "38999250000.0", "0.49999999999"):
            self.assertEqual(GK.lam_tron_nua_len(Fraction(Decimal(x))), int(Decimal(x).quantize(Decimal(1), rounding=ROUND_HALF_UP)), x)


if __name__ == "__main__":
    unittest.main()
