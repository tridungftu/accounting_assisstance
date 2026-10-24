"""M4_KT_M26_REGISTRATION — đăng ký M4-03A (KT xác nhận nguồn nghiệm thu) thành migration 26 (CODE_ONLY: coder viết, CHƯA CHẠY — WRITTEN_NOT_RUN).

CHỈ thuần (không CSDL, không driver/kết nối PG, không bootstrap sản phẩm, không SQL/migrate/seed/SET ROLE/M9):
  - toàn bộ 973.003 byte đầu ``pg_migrations.py`` = baseline 25 Root đã chốt (SHA trong handoff GIAO-CODE-M4-KT-M26-REGISTRATION, không lấy
    từ code); phần nối chỉ gồm import + alias + MỘT tuple đăng ký + version; không bản sao SQL;
  - registry baseline 1–25 dựng lại TỪ CHÍNH prefix gốc (exec độc lập) khớp từng câu/checksum với registry mới; M24 ở index 23 và G6A ở index 24
    nguyên object/checksum; M4-03A ở index 25 đúng MỘT lần, CHÍNH object ``M4_03A_SQL``;
  - module hằng SQL KT nguyên byte (SHA Root ghim), không import registry/ha_tang, không tự author ordinal; helper ``test_m4_02c_pg.py`` nguyên byte.

Không có gì ở đây là nghiệm thu PG/native/GUI/toàn M4: apply 26 trên bản sao DEMO SỞ HỮU, checksum joinedSQL, native13/graph3/fullbasis/
concurrency/producer→GUI do Root lượt riêng (tests/test_m4_03a_pg.py …). AP03B/Request/sổ cái ngoài phạm vi.
"""

from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2 import sql_crm_kiem_hd as SG
from kho_tri_thuc.m4 import sql_duyet as SD
from kho_tri_thuc.m4 import sql_ke_toan_nghiem_thu as SK

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
PG_PY = SRC / "ha_tang" / "pg_migrations.py"
SQL_PY = SRC / "m4" / "sql_ke_toan_nghiem_thu.py"
HELPER_PY = GOC / "tests" / "test_m4_02c_pg.py"

# handoff GIAO-CODE-M4-KT-M26-REGISTRATION (Root pin — không tính lại từ code)
PREFIX_BYTES, PREFIX_SHA256 = 973_003, "1f91fafc029b62bbc6d4edba126301b5a0962e176f2bdc10619cb55d0e3ec3a9"  # toàn pg_migrations.py baseline 25
# checkpoint M26 = đoạn byte [973.003:973.783] (handoff GIAO-CODE-M4-04C-M27, Root pin); registry được tiến hóa APPEND sau mốc này (27+)
M26_END, M26_PREFIX_SHA256 = 973_783, "682131e655ff7b15470ecac3c47e2b9a666645321ac558eca8d692718af51f89"  # toàn pg_migrations.py baseline 26
SQL_SHA256 = "ad36b72993defa3f9cb5c951716a141bd77843a0dcf7f354226d9ad7da3992db"  # m4/sql_ke_toan_nghiem_thu.py
HELPER_SHA256 = "6bed282d8d37947fa947b737e31f074546a291e5707d45df740268c21eabcde7"  # tests/test_m4_02c_pg.py
DONG_NOI = ("from ..m4.sql_ke_toan_nghiem_thu import M4_03A_SQL  # noqa: E402 — module chỉ hằng SQL, không import ha_tang",
            "M0026_M4_KT = M4_03A_SQL",
            "PG_MIGRATIONS = (*PG_MIGRATIONS, M0026_M4_KT)",
            "PG_SCHEMA_VERSION = len(PG_MIGRATIONS)")
BANG_KT = "m4.kt_xac_nhan"  # bảng mới của M4-03A — dấu hiệu không được có trong 1–25


def _baseline25() -> dict:
    """Registry baseline dựng lại từ CHÍNH 973.003 byte gốc (exec trong namespace riêng) — không dùng giá trị của registry mới."""
    raw = PG_PY.read_bytes()[:PREFIX_BYTES]
    ns = {"__name__": "kho_tri_thuc.ha_tang._pg_baseline25", "__package__": "kho_tri_thuc.ha_tang", "__file__": str(PG_PY)}
    exec(compile(raw, str(PG_PY) + ":baseline25", "exec"), ns)  # noqa: S102 — mã nguồn của chính repo, không nhận đầu vào ngoài
    return ns


class M26Prefix(unittest.TestCase):
    def test_prefix_baseline25_nguyen_byte(self):
        raw = PG_PY.read_bytes()
        self.assertGreater(len(raw), PREFIX_BYTES)
        self.assertEqual(hashlib.sha256(raw[:PREFIX_BYTES]).hexdigest(), PREFIX_SHA256, "prefix baseline 25 bị sửa — chỉ được APPEND")
        truoc = raw[:PREFIX_BYTES].decode("utf-8")
        self.assertTrue(truoc.endswith("M0025_CRM_G6A = CRM_G6A_SQL\nPG_MIGRATIONS = (*PG_MIGRATIONS, M0025_CRM_G6A)\n"
                                       "PG_SCHEMA_VERSION = len(PG_MIGRATIONS)\n"), "prefix phải dừng đúng sau khối đăng ký M25")
        self.assertNotIn("M4_03A_SQL", truoc)
        self.assertNotIn("sql_ke_toan_nghiem_thu", truoc)
        self.assertNotIn("M0026", truoc)

    def test_phan_noi_chi_import_alias_mot_dang_ky(self):
        raw = PG_PY.read_bytes()
        self.assertGreaterEqual(len(raw), M26_END)
        self.assertEqual(hashlib.sha256(raw[:M26_END]).hexdigest(), M26_PREFIX_SHA256, "đoạn M26 bị sửa — chỉ được APPEND sau mốc 26")
        duoi = raw[PREFIX_BYTES:M26_END].decode("utf-8")  # chỉ đoạn M26; migration sau 26 nằm ngoài checkpoint này
        ma = tuple(x.rstrip() for x in duoi.splitlines() if x.strip() and not x.lstrip().startswith("#"))
        self.assertEqual(ma, DONG_NOI, "phần nối chỉ được import + alias + một tuple đăng ký + version")
        self.assertTrue(duoi.endswith("\n"))
        self.assertNotRegex(duoi, r"(?i)\b(CREATE|ALTER|DROP|GRANT|REVOKE|INSERT|UPDATE|DELETE)\s")  # không bản sao SQL
        self.assertNotRegex(duoi, r"m4\.kt_|master\.m4_kt")  # không tên đối tượng SQL KT nào ngoài hằng của module domain
        self.assertNotRegex(duoi, r"psycopg|connect\(|bootstrap")  # không driver/kết nối/bootstrap
        txt = PG_PY.read_text(encoding="utf-8")
        self.assertEqual(txt.count("import M4_03A_SQL"), 1)
        self.assertEqual(len(re.findall(r"^PG_MIGRATIONS = \(\*PG_MIGRATIONS, M0026_M4_KT\)$", txt, re.M)), 1)

    def test_module_sql_kt_nguyen_byte_khong_import_registry(self):
        raw = SQL_PY.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), SQL_SHA256, "module hằng SQL KT bị sửa")
        src = raw.decode("utf-8")
        self.assertIsNone(re.search(r"^\s*(from|import)\s[^\n]*(pg_migrations|ha_tang|psycopg)", src, re.M))
        self.assertNotIn("M0026", src)  # ordinal do integration owner cấp, không author trong domain constant
        self.assertNotIn("PG_MIGRATIONS", src)

    def test_helper_m4_02c_pg_nguyen_byte(self):
        self.assertEqual(hashlib.sha256(HELPER_PY.read_bytes()).hexdigest(), HELPER_SHA256, "helper tests/test_m4_02c_pg.py bị sửa")


class M26Registry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.B = _baseline25()

    def test_baseline_dung_lai_la_25(self):
        b = self.B["PG_MIGRATIONS"]
        self.assertEqual((len(b), self.B["PG_SCHEMA_VERSION"]), (25, 25))
        self.assertIs(b[23], SD.M0024_M4_DUYET)  # module hằng đã nạp: cùng object
        self.assertIs(b[24], SG.CRM_G6A_SQL)
        self.assertFalse(any(m is SK.M4_03A_SQL for m in b))
        self.assertFalse(any(BANG_KT in s for m in b for s in m), "baseline 1–25 không được chứa đối tượng KT M4-03A")

    def test_prefix_1_25_tung_cau_va_checksum(self):
        b = self.B["PG_MIGRATIONS"]
        self.assertEqual(len(PM.PG_MIGRATIONS[:25]), 25)
        for i in range(25):
            # không assertIs với b[i]: tuple literal của hai lần compile/exec riêng là object khác nhau dù cùng byte — so câu + checksum
            self.assertEqual(tuple(PM.PG_MIGRATIONS[i]), tuple(b[i]), f"migration {i + 1} đổi câu lệnh")
            self.assertEqual(PM._hash(PM.PG_MIGRATIONS[i]), self.B["_hash"](b[i]), f"migration {i + 1} đổi checksum")
        self.assertEqual(PM.PG_MIGRATION_TUONG_THICH, self.B["PG_MIGRATION_TUONG_THICH"])  # không compatibility checksum mới
        self.assertNotIn(26, set(PM.PG_MIGRATION_TUONG_THICH))
        self.assertEqual(PM.PG_MIGRATIONS_LICH_SU_FULL_M9, self.B["PG_MIGRATIONS_LICH_SU_FULL_M9"])
        self.assertEqual(PM.LEGACY_FULL_M9_M0013_SHA256, self.B["LEGACY_FULL_M9_M0013_SHA256"])

    def test_m24_m25_giu_nguyen_object(self):
        self.assertIs(PM.PG_MIGRATIONS[23], SD.M0024_M4_DUYET)
        self.assertIs(PM.PG_MIGRATIONS[23], PM.M0024_M4_DUYET)
        self.assertIs(PM.PG_MIGRATIONS[24], SG.CRM_G6A_SQL)
        self.assertIs(PM.PG_MIGRATIONS[24], PM.M0025_CRM_G6A)
        self.assertEqual(PM._hash(PM.PG_MIGRATIONS[23]), self.B["_hash"](self.B["PG_MIGRATIONS"][23]))
        self.assertEqual(PM._hash(PM.PG_MIGRATIONS[24]), self.B["_hash"](self.B["PG_MIGRATIONS"][24]))

    def test_version26_kt_dung_mot_lan_cung_object(self):
        # registry tiến hóa: version = len và >= 26; M26 cố định ở index 25 (ngay sau M25), không đòi mãi là phần tử cuối
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        self.assertGreaterEqual(PM.PG_SCHEMA_VERSION, 26)
        self.assertIs(PM.PG_MIGRATIONS[25], SK.M4_03A_SQL)
        self.assertIs(PM.PG_MIGRATIONS[:26][-1], SK.M4_03A_SQL)  # hậu tố duy nhất của 1–26, ngay sau M25
        self.assertIs(PM.M0026_M4_KT, SK.M4_03A_SQL)
        self.assertIs(PM.M4_03A_SQL, SK.M4_03A_SQL)
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS) if m is SK.M4_03A_SQL], [25])
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS) if tuple(m) == tuple(SK.M4_03A_SQL)], [25])
        # dấu bảng KT duy nhất trong 1–26; migration sau 26 được phép FK/tham chiếu m4.kt_xac_nhan
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS[:26]) if any(BANG_KT in s for s in m)], [25])
        self.assertIsInstance(SK.M4_03A_SQL, tuple)
        self.assertTrue(SK.M4_03A_SQL and all(isinstance(s, str) and s.strip() for s in SK.M4_03A_SQL))
        self.assertEqual(SK.M4_03A_SQL[0], "SET LOCAL check_function_bodies = off")
        h26 = PM._hash(PM.PG_MIGRATIONS[25])
        self.assertEqual(h26, PM._hash(SK.M4_03A_SQL))
        self.assertNotIn(h26, [PM._hash(m) for m in PM.PG_MIGRATIONS[:25]], "checksum 26 trùng một migration cũ")
        self.assertNotIn(PM.M0013, PM.PG_MIGRATIONS)  # full-M9 lịch sử vẫn ngoài chuỗi active


if __name__ == "__main__":
    unittest.main()
