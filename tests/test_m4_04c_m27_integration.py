"""M4_REQUEST_M27_REGISTRATION — đăng ký M4-04A/04C (Request nháp) thành migration 27 (CODE_ONLY: coder viết, CHƯA CHẠY — WRITTEN_NOT_RUN).

CHỈ thuần (không CSDL, không driver/kết nối PG, không bootstrap sản phẩm, không SQL/migrate/seed/SET ROLE/M9/mạng/Request ngoài):
  - toàn bộ 973.783 byte đầu ``pg_migrations.py`` = baseline 26 Root đã chốt (SHA trong handoff GIAO-CODE-M4-04C-M27, không lấy từ code);
  - đoạn M27 = từ mốc 973.783 đến hết dòng ``PG_SCHEMA_VERSION = len(PG_MIGRATIONS)`` ĐẦU TIÊN sau mốc; chỉ import + alias + MỘT tuple
    đăng ký + version; không bản sao SQL. Phần sau đoạn này (28+) KHÔNG thuộc test này — biên tương lai rõ, không khẳng định schema mãi là 27;
  - registry baseline 1–26 dựng lại TỪ CHÍNH prefix gốc (exec độc lập) khớp từng câu/checksum với registry hiện hành;
    Request ở index 26 đúng MỘT lần, CHÍNH object ``M4_REQUEST_NHAP``;
  - module hằng SQL Request nguyên byte (SHA Root ghim), không import registry/ha_tang, không tự author ordinal; helper ``test_m4_02c_pg.py`` nguyên byte.

Không có gì ở đây là nghiệm thu PG/native/HTTP/GUI/toàn M4: apply 27 trên clone riêng, Request6/HTTP3 native, compose 04B và GUI do Root lượt riêng.
Backend Request vận hành thật vẫn OFF.
"""

from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.m4 import sql_ke_toan_nghiem_thu as SK
from kho_tri_thuc.m4 import sql_request_nhap as SR

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
PG_PY = SRC / "ha_tang" / "pg_migrations.py"
SQL_PY = SRC / "m4" / "sql_request_nhap.py"
HELPER_PY = GOC / "tests" / "test_m4_02c_pg.py"

# handoff GIAO-CODE-M4-04C-M27 (Root pin — không tính lại từ code)
PREFIX_BYTES, PREFIX_SHA256 = 973_783, "682131e655ff7b15470ecac3c47e2b9a666645321ac558eca8d692718af51f89"  # toàn pg_migrations.py baseline 26
SQL_SHA256 = "453ed0831839099852d9f4bdf1f168a3e9fb5d229ca568ceb814501c9f3d1ce2"  # m4/sql_request_nhap.py
M27_JOINED_SHA256 = "eb0e23f47bcbfdc6f0df8277265d024a51408e833f81ce18da007415429bebc7"  # _hash(câu 27) = sha256("\n".join)
HELPER_SHA256 = "6bed282d8d37947fa947b737e31f074546a291e5707d45df740268c21eabcde7"  # tests/test_m4_02c_pg.py
VERSION_DONG = b"PG_SCHEMA_VERSION = len(PG_MIGRATIONS)\n"
DONG_NOI = ("from ..m4.sql_request_nhap import M4_REQUEST_NHAP  # noqa: E402 — module chỉ hằng SQL, không import ha_tang",
            "M0027_M4_REQUEST = M4_REQUEST_NHAP",
            "PG_MIGRATIONS = (*PG_MIGRATIONS, M0027_M4_REQUEST)",
            "PG_SCHEMA_VERSION = len(PG_MIGRATIONS)")
BANG_REQUEST = "m4.request_y_dinh"  # bảng intent Request — dấu hiệu không được có trong 1–26


def _doan_m27(raw: bytes) -> bytes:
    """Đoạn M27: [mốc 26, hết dòng version ĐẦU TIÊN sau mốc]. Migration 28+ nối sau đoạn này và nằm ngoài phạm vi test."""
    cuoi = raw.find(VERSION_DONG, PREFIX_BYTES)
    if cuoi < 0:
        raise AssertionError("không thấy dòng version kết thúc khối đăng ký M27 sau mốc 26")
    return raw[PREFIX_BYTES:cuoi + len(VERSION_DONG)]


def _baseline26() -> dict:
    """Registry baseline dựng lại từ CHÍNH 973.783 byte gốc (exec trong namespace riêng) — không dùng giá trị của registry hiện hành."""
    raw = PG_PY.read_bytes()[:PREFIX_BYTES]
    ns = {"__name__": "kho_tri_thuc.ha_tang._pg_baseline26", "__package__": "kho_tri_thuc.ha_tang", "__file__": str(PG_PY)}
    exec(compile(raw, str(PG_PY) + ":baseline26", "exec"), ns)  # noqa: S102 — mã nguồn của chính repo, không nhận đầu vào ngoài
    return ns


class M27Prefix(unittest.TestCase):
    def test_prefix_baseline26_nguyen_byte(self):
        raw = PG_PY.read_bytes()
        self.assertGreater(len(raw), PREFIX_BYTES)
        self.assertEqual(hashlib.sha256(raw[:PREFIX_BYTES]).hexdigest(), PREFIX_SHA256, "prefix baseline 26 bị sửa — chỉ được APPEND")
        truoc = raw[:PREFIX_BYTES].decode("utf-8")
        self.assertTrue(truoc.endswith("M0026_M4_KT = M4_03A_SQL\nPG_MIGRATIONS = (*PG_MIGRATIONS, M0026_M4_KT)\n"
                                       "PG_SCHEMA_VERSION = len(PG_MIGRATIONS)\n"), "prefix phải dừng đúng sau khối đăng ký M26")
        self.assertNotIn("M4_REQUEST_NHAP", truoc)
        self.assertNotIn("sql_request_nhap", truoc)
        self.assertNotIn("M0027", truoc)

    def test_doan_m27_chi_import_alias_mot_dang_ky(self):
        raw = PG_PY.read_bytes()
        doan = _doan_m27(raw).decode("utf-8")
        ma = tuple(x.rstrip() for x in doan.splitlines() if x.strip() and not x.lstrip().startswith("#"))
        self.assertEqual(ma, DONG_NOI, "đoạn M27 chỉ được import + alias + một tuple đăng ký + version")
        self.assertTrue(doan.endswith("\n"))
        self.assertNotRegex(doan, r"(?i)\b(CREATE|ALTER|DROP|GRANT|REVOKE|INSERT|UPDATE|DELETE)\s")  # không bản sao SQL
        self.assertNotRegex(doan, r"m4\.request_|m4\._request_")  # không tên đối tượng SQL Request nào ngoài hằng của module domain
        self.assertNotRegex(doan, r"psycopg|connect\(|bootstrap|FULL_M9|TUONG_THICH")  # không driver/bootstrap/lịch sử/compat mới
        txt = PG_PY.read_text(encoding="utf-8")
        self.assertEqual(txt.count("import M4_REQUEST_NHAP"), 1)
        self.assertEqual(len(re.findall(r"^M0027_M4_REQUEST = ", txt, re.M)), 1)
        self.assertEqual(len(re.findall(r"^PG_MIGRATIONS = \(\*PG_MIGRATIONS, M0027_M4_REQUEST\)$", txt, re.M)), 1)

    def test_module_sql_request_nguyen_byte_khong_import_registry(self):
        raw = SQL_PY.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), SQL_SHA256, "module hằng SQL Request bị sửa")
        src = raw.decode("utf-8")
        self.assertIsNone(re.search(r"^\s*(from|import)\s[^\n]*(pg_migrations|ha_tang|psycopg)", src, re.M))
        self.assertNotIn("M0027", src)  # ordinal do integration owner cấp, không author trong domain constant
        self.assertNotIn("PG_MIGRATIONS", src)

    def test_helper_m4_02c_pg_nguyen_byte(self):
        self.assertEqual(hashlib.sha256(HELPER_PY.read_bytes()).hexdigest(), HELPER_SHA256, "helper tests/test_m4_02c_pg.py bị sửa")


class M27Registry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.B = _baseline26()

    def test_baseline_dung_lai_la_26(self):
        b = self.B["PG_MIGRATIONS"]
        self.assertEqual((len(b), self.B["PG_SCHEMA_VERSION"]), (26, 26))
        self.assertIs(b[25], SK.M4_03A_SQL)  # module hằng đã nạp: cùng object
        self.assertFalse(any(m is SR.M4_REQUEST_NHAP for m in b))
        self.assertFalse(any(BANG_REQUEST in s for m in b for s in m), "baseline 1–26 không được chứa đối tượng Request")

    def test_prefix_1_26_tung_cau_va_checksum(self):
        b = self.B["PG_MIGRATIONS"]
        self.assertEqual(len(PM.PG_MIGRATIONS[:26]), 26)
        for i in range(26):
            # không assertIs với b[i]: tuple literal của hai lần compile/exec riêng là object khác nhau dù cùng byte — so câu + checksum
            self.assertEqual(tuple(PM.PG_MIGRATIONS[i]), tuple(b[i]), f"migration {i + 1} đổi câu lệnh")
            self.assertEqual(PM._hash(PM.PG_MIGRATIONS[i]), self.B["_hash"](b[i]), f"migration {i + 1} đổi checksum")
        self.assertIs(PM.PG_MIGRATIONS[25], SK.M4_03A_SQL)
        self.assertIs(PM.PG_MIGRATIONS[25], PM.M0026_M4_KT)
        self.assertEqual(PM.PG_MIGRATION_TUONG_THICH, self.B["PG_MIGRATION_TUONG_THICH"])  # không compatibility checksum mới
        self.assertNotIn(27, set(PM.PG_MIGRATION_TUONG_THICH))
        self.assertEqual(PM.PG_MIGRATIONS_LICH_SU_FULL_M9, self.B["PG_MIGRATIONS_LICH_SU_FULL_M9"])
        self.assertEqual(PM.LEGACY_FULL_M9_M0013_SHA256, self.B["LEGACY_FULL_M9_M0013_SHA256"])

    def test_m27_request_dung_mot_lan_cung_object(self):
        # biên tương lai: version = len và >= 27; Request cố định ở index 26 (ngay sau M26), không đòi mãi là phần tử cuối
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        self.assertGreaterEqual(PM.PG_SCHEMA_VERSION, 27)
        self.assertIs(PM.PG_MIGRATIONS[26], SR.M4_REQUEST_NHAP)
        self.assertIs(PM.PG_MIGRATIONS[:27][-1], SR.M4_REQUEST_NHAP)  # hậu tố duy nhất của 1–27, ngay sau M26
        self.assertIs(PM.M0027_M4_REQUEST, SR.M4_REQUEST_NHAP)
        self.assertIs(PM.M4_REQUEST_NHAP, SR.M4_REQUEST_NHAP)
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS) if m is SR.M4_REQUEST_NHAP], [26])
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS) if tuple(m) == tuple(SR.M4_REQUEST_NHAP)], [26])
        # dấu bảng intent Request duy nhất trong 1–27; migration sau 27 được phép FK/tham chiếu
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS[:27]) if any(BANG_REQUEST in s for s in m)], [26])
        self.assertIsInstance(SR.M4_REQUEST_NHAP, tuple)
        self.assertTrue(SR.M4_REQUEST_NHAP and all(isinstance(s, str) and s.strip() for s in SR.M4_REQUEST_NHAP))
        self.assertEqual(SR.M4_REQUEST_NHAP[0], "SET LOCAL check_function_bodies = off")
        h27 = PM._hash(PM.PG_MIGRATIONS[26])
        self.assertEqual(h27, PM._hash(SR.M4_REQUEST_NHAP))
        self.assertEqual(h27, M27_JOINED_SHA256, "checksum joined câu 27 lệch pin Root")
        self.assertNotIn(h27, [PM._hash(m) for m in PM.PG_MIGRATIONS[:26]], "checksum 27 trùng một migration cũ")
        self.assertFalse(any(m is SR.M4_REQUEST_NHAP for m in PM.PG_MIGRATIONS_LICH_SU_FULL_M9))  # không chạm lịch sử full-M9
        self.assertNotIn(PM.M0013, PM.PG_MIGRATIONS)  # full-M9 lịch sử vẫn ngoài chuỗi active


if __name__ == "__main__":
    unittest.main()
