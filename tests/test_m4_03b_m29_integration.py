"""M4_03B_M29_REGISTRATION — đăng ký M4-03B ghi nhận chung (identity nguồn kinh tế M2–M4 + đối chiếu căn cứ NT ↔ hóa đơn, gồm FIX01–FIX04) thành migration 29.

CHỈ thuần (không CSDL, không driver/kết nối PG, không bootstrap sản phẩm, không SQL/migrate/seed/SET ROLE/M9/mạng/Request ngoài):
  - toàn bộ 975.546 byte đầu ``pg_migrations.py`` = baseline 28 (gồm M0028 master dùng chung; SHA ghim ở đây, không lấy từ code), trong đó
    974.607 byte đầu = baseline 27 (checkpoint M27/M28 của ``test_m4_04c_m27_integration.py`` / ``test_m4_master_m28_integration.py``);
  - đoạn M29 = từ mốc 975.546 đến hết dòng ``PG_SCHEMA_VERSION = len(PG_MIGRATIONS)`` ĐẦU TIÊN sau mốc; chỉ import + alias + MỘT tuple
    đăng ký + version; không bản sao SQL. Phần sau đoạn này (30+) KHÔNG thuộc test này — biên tương lai rõ, không khẳng định schema mãi là 29;
  - registry baseline 1–28 dựng lại TỪ CHÍNH prefix gốc (exec độc lập) khớp từng câu/checksum với registry hiện hành;
    03B ở index 28 đúng MỘT lần, CHÍNH object ``M4_03B_COMMON_SQL``, SAU M26 (``m4.kt_xac_nhan``) và sau biên nhận chung/khóa dòng nguồn;
  - module hằng SQL nguyên byte (SHA ghim), không import registry/ha_tang, không tự author ordinal.

Không có gì ở đây là nghiệm thu PG/native/HTTP/GUI: bằng chứng áp dụng thật (migrate 0→N và 27→N trên CSDL riêng) là bước riêng của lát M4-4/7,
còn kiểm PG nhiều phiên là ``tests/test_m4_03b_common_pg.py`` (cần clone riêng + ba cổng env, thiếu thì SkipTest NOT_VERIFIED).
"""

from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2 import sql_ghi_nhan_chung as SG
from kho_tri_thuc.m4 import sql_master_dung_chung as MC

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
PG_PY = SRC / "ha_tang" / "pg_migrations.py"
SQL_PY = SRC / "k2" / "sql_ghi_nhan_chung.py"

# ghim (không tính lại từ code đang chạy)
M27_END, M27_PREFIX_SHA256 = 974_607, "9ceb58b21f73d553bc9cf317e6e720ebed6448358fab65195c1fd2a42ac2d491"  # toàn pg_migrations.py baseline 27
PREFIX_BYTES, PREFIX_SHA256 = 975_546, "f724ea0f6a25bed446949a1e029fcd57808a557ed7218984957b24d82c419795"  # toàn pg_migrations.py baseline 28
M29_END, M29_PREFIX_SHA256 = 976_492, "7817b70da2b3457ac16add058fc894b7484aae12fc7c399e67b24ac0ef99fc07"  # toàn pg_migrations.py baseline 29
SQL_SHA256 = "b67ef795467dec1958267195e9e14f9601e705b61bc52495b5598b2609e75b12"  # k2/sql_ghi_nhan_chung.py, xuống dòng chuẩn hóa LF (gitattributes chưa ép eol cho file này)
M29_JOINED_SHA256 = "4544ab374806a52729b1602fbf3d95eae3401ada006da54a97312cd1bc8ae5eb"  # _hash(câu 29) = sha256("\n".join)
VERSION_DONG = b"PG_SCHEMA_VERSION = len(PG_MIGRATIONS)\n"
DONG_NOI = ("from ..k2.sql_ghi_nhan_chung import M4_03B_COMMON_SQL  # noqa: E402 — module chỉ hằng SQL, không import ha_tang",
            "M0029_M4_GHI_NHAN_CHUNG = M4_03B_COMMON_SQL",
            "PG_MIGRATIONS = (*PG_MIGRATIONS, M0029_M4_GHI_NHAN_CHUNG)",
            "PG_SCHEMA_VERSION = len(PG_MIGRATIONS)")
BANG_03B = "kho.mua_nguon_kinh_te"  # bảng đầu tiên của 03B — dấu hiệu không được có trong 1–28


def _doan_m29(raw: bytes) -> bytes:
    """Đoạn M29: [mốc 28, hết dòng version ĐẦU TIÊN sau mốc]. Migration 30+ nối sau đoạn này và nằm ngoài phạm vi test."""
    cuoi = raw.find(VERSION_DONG, PREFIX_BYTES)
    if cuoi < 0:
        raise AssertionError("không thấy dòng version kết thúc khối đăng ký M29 sau mốc 28")
    return raw[PREFIX_BYTES:cuoi + len(VERSION_DONG)]


def _baseline28() -> dict:
    """Registry baseline dựng lại từ CHÍNH 975.546 byte gốc (exec trong namespace riêng) — không dùng giá trị của registry hiện hành."""
    raw = PG_PY.read_bytes()[:PREFIX_BYTES]
    ns = {"__name__": "kho_tri_thuc.ha_tang._pg_baseline28", "__package__": "kho_tri_thuc.ha_tang", "__file__": str(PG_PY)}
    exec(compile(raw, str(PG_PY) + ":baseline28", "exec"), ns)  # noqa: S102 — mã nguồn của chính repo, không nhận đầu vào ngoài
    return ns


def _cho_tao(mau: str, den: int | None = None) -> list[int]:
    """Chỉ số (0-based) các migration (trong PG_MIGRATIONS[:den]) có câu khớp regex ``mau``."""
    return [i for i, m in enumerate(PM.PG_MIGRATIONS[:den]) if any(re.search(mau, s) for s in m)]


class M29Prefix(unittest.TestCase):
    def test_prefix_baseline28_nguyen_byte(self):
        raw = PG_PY.read_bytes()
        self.assertGreater(len(raw), PREFIX_BYTES)
        self.assertEqual(hashlib.sha256(raw[:M27_END]).hexdigest(), M27_PREFIX_SHA256, "prefix baseline 27 bị sửa — chỉ được APPEND")
        self.assertEqual(hashlib.sha256(raw[:PREFIX_BYTES]).hexdigest(), PREFIX_SHA256, "prefix baseline 28 bị sửa — chỉ được APPEND")
        truoc = raw[:PREFIX_BYTES].decode("utf-8")
        self.assertTrue(truoc.endswith("M0028_M4_MASTER_DUNG_CHUNG = M4_MASTER_DUNG_CHUNG_SQL\nPG_MIGRATIONS = (*PG_MIGRATIONS, M0028_M4_MASTER_DUNG_CHUNG)\n"
                                       "PG_SCHEMA_VERSION = len(PG_MIGRATIONS)\n"), "prefix phải dừng đúng sau khối đăng ký M28")
        self.assertNotIn("M4_03B_COMMON_SQL", truoc)
        self.assertNotIn("sql_ghi_nhan_chung", truoc)
        self.assertNotIn("M0029", truoc)

    def test_doan_m29_chi_import_alias_mot_dang_ky(self):
        raw = PG_PY.read_bytes()
        self.assertGreaterEqual(len(raw), M29_END)
        self.assertEqual(hashlib.sha256(raw[:M29_END]).hexdigest(), M29_PREFIX_SHA256, "đoạn M29 bị sửa — chỉ được APPEND sau mốc 29")
        doan = _doan_m29(raw)
        self.assertEqual(PREFIX_BYTES + len(doan), M29_END)
        doan = doan.decode("utf-8")
        ma = tuple(x.rstrip() for x in doan.splitlines() if x.strip() and not x.lstrip().startswith("#"))
        self.assertEqual(ma, DONG_NOI, "đoạn M29 chỉ được import + alias + một tuple đăng ký + version")
        self.assertTrue(doan.endswith("\n"))
        self.assertNotRegex("\n".join(ma), r"(?i)\b(CREATE|ALTER|DROP|GRANT|REVOKE|INSERT|UPDATE|DELETE)\s")  # không bản sao SQL
        self.assertNotRegex("\n".join(ma), r"kho\.mua_|kho\.dc_|kho\._dc_|bien_nhan_thao_tac")  # không tên đối tượng SQL nào ngoài hằng của module domain
        self.assertNotRegex(doan, r"psycopg|connect\(|bootstrap|FULL_M9|TUONG_THICH")  # không driver/bootstrap/lịch sử/compat mới
        txt = PG_PY.read_text(encoding="utf-8")
        self.assertEqual(txt.count("import M4_03B_COMMON_SQL"), 1)
        self.assertEqual(len(re.findall(r"^M0029_M4_GHI_NHAN_CHUNG = ", txt, re.M)), 1)
        self.assertEqual(len(re.findall(r"^PG_MIGRATIONS = \(\*PG_MIGRATIONS, M0029_M4_GHI_NHAN_CHUNG\)$", txt, re.M)), 1)

    def test_module_sql_03b_nguyen_byte_khong_import_registry(self):
        raw = SQL_PY.read_bytes().replace(b"\r\n", b"\n")  # checkout autocrlf cho CRLF; checksum migration không phụ thuộc (Python chuẩn hóa xuống dòng trong chuỗi)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), SQL_SHA256, "module hằng SQL 03B bị sửa")
        src = raw.decode("utf-8")
        self.assertIsNone(re.search(r"^\s*(from|import)\s[^\n]*(pg_migrations|ha_tang|psycopg)", src, re.M))
        self.assertNotIn("M0029", src)  # ordinal do integration owner cấp, không author trong domain constant
        self.assertNotIn("PG_MIGRATIONS", src)


class M29Registry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.B = _baseline28()

    def test_baseline_dung_lai_la_28(self):
        b = self.B["PG_MIGRATIONS"]
        self.assertEqual((len(b), self.B["PG_SCHEMA_VERSION"]), (28, 28))
        self.assertIs(b[27], MC.M4_MASTER_DUNG_CHUNG_SQL)  # module hằng đã nạp: cùng object
        self.assertFalse(any(m is SG.M4_03B_COMMON_SQL for m in b))
        self.assertFalse(any(BANG_03B in s for m in b for s in m), "baseline 1–28 không được chứa đối tượng 03B")

    def test_prefix_1_28_tung_cau_va_checksum(self):
        b = self.B["PG_MIGRATIONS"]
        self.assertEqual(len(PM.PG_MIGRATIONS[:28]), 28)
        for i in range(28):
            # không assertIs với b[i]: tuple literal của hai lần compile/exec riêng là object khác nhau dù cùng byte — so câu + checksum
            self.assertEqual(tuple(PM.PG_MIGRATIONS[i]), tuple(b[i]), f"migration {i + 1} đổi câu lệnh")
            self.assertEqual(PM._hash(PM.PG_MIGRATIONS[i]), self.B["_hash"](b[i]), f"migration {i + 1} đổi checksum")
        self.assertIs(PM.PG_MIGRATIONS[27], MC.M4_MASTER_DUNG_CHUNG_SQL)
        self.assertIs(PM.PG_MIGRATIONS[27], PM.M0028_M4_MASTER_DUNG_CHUNG)
        self.assertEqual(PM.PG_MIGRATION_TUONG_THICH, self.B["PG_MIGRATION_TUONG_THICH"])  # không compatibility checksum mới
        self.assertNotIn(29, set(PM.PG_MIGRATION_TUONG_THICH))
        self.assertEqual(PM.PG_MIGRATIONS_LICH_SU_FULL_M9, self.B["PG_MIGRATIONS_LICH_SU_FULL_M9"])
        self.assertEqual(PM.LEGACY_FULL_M9_M0013_SHA256, self.B["LEGACY_FULL_M9_M0013_SHA256"])

    def test_m29_03b_dung_mot_lan_cung_object(self):
        # biên tương lai: version = len và >= 29; 03B ở index 28 (ngay sau M28 master), không đòi mãi là phần tử cuối
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        self.assertGreaterEqual(PM.PG_SCHEMA_VERSION, 29)
        self.assertIs(PM.PG_MIGRATIONS[28], SG.M4_03B_COMMON_SQL)
        self.assertIs(PM.PG_MIGRATIONS[:29][-1], SG.M4_03B_COMMON_SQL)  # hậu tố duy nhất của 1–29, ngay sau M28
        self.assertIs(PM.M0029_M4_GHI_NHAN_CHUNG, SG.M4_03B_COMMON_SQL)
        self.assertIs(PM.M4_03B_COMMON_SQL, SG.M4_03B_COMMON_SQL)
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS) if m is SG.M4_03B_COMMON_SQL], [28])
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS) if tuple(m) == tuple(SG.M4_03B_COMMON_SQL)], [28])
        # mọi bảng của 03B (kể cả khóa chứng thực nội bộ) được tạo đúng ở index 28 và không ở 1–28; migration sau 29 được phép tham chiếu
        for bang in SG.BANG + SG.BANG_NOI_BO:
            self.assertEqual(_cho_tao(r"CREATE TABLE kho\." + re.escape(bang) + r" \(", 29), [28], bang)
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS[:29]) if any(BANG_03B in s for s in m)], [28])
        self.assertIsInstance(SG.M4_03B_COMMON_SQL, tuple)
        self.assertTrue(SG.M4_03B_COMMON_SQL and all(isinstance(s, str) and s.strip() for s in SG.M4_03B_COMMON_SQL))
        self.assertEqual(SG.M4_03B_COMMON_SQL[0], "SET LOCAL check_function_bodies = off")
        h29 = PM._hash(PM.PG_MIGRATIONS[28])
        self.assertEqual(h29, PM._hash(SG.M4_03B_COMMON_SQL))
        self.assertEqual(h29, M29_JOINED_SHA256, "checksum joined câu 29 lệch pin")
        self.assertNotIn(h29, [PM._hash(m) for m in PM.PG_MIGRATIONS[:28]], "checksum 29 trùng một migration cũ")
        self.assertFalse(any(m is SG.M4_03B_COMMON_SQL for m in PM.PG_MIGRATIONS_LICH_SU_FULL_M9))  # không chạm lịch sử full-M9
        self.assertNotIn(PM.M0013, PM.PG_MIGRATIONS)  # full-M9 lịch sử vẫn ngoài chuỗi active

    def test_thu_tu_sau_m26_va_nguon_hien_huu(self):
        # 03B chạy SAU M26 (m4.kt_xac_nhan, kt_kiem, _kt_hien_hanh), SAU biên nhận chung và khóa dòng nguồn L11; các đối tượng đó đã có ở migration trước
        self.assertEqual(_cho_tao(r"CREATE TABLE m4\.kt_xac_nhan\b", 28), [25])  # M26
        self.assertEqual(_cho_tao(r"FUNCTION m4\.kt_kiem\(", 28), [25])
        self.assertEqual(_cho_tao(r"FUNCTION m4\._kt_hien_hanh\(", 28), [25])
        self.assertEqual(_cho_tao(r"FUNCTION m4\.kt_khoa\(", 28), [25])
        self.assertEqual(_cho_tao(r"CREATE TABLE (IF NOT EXISTS )?kho\.bien_nhan_thao_tac\b", 28), [12])  # bảng biên nhận chung mà 03B nới CHECK module
        self.assertEqual(_cho_tao(r"FUNCTION kho\.l11_khoa_dong_nguon_noi_bo\(", 28), [15])
        self.assertIs(PM.PG_MIGRATIONS[25], PM.M0026_M4_KT)
        # 03B không phụ thuộc master dùng chung (M28) ở mức đối tượng; thứ tự M28 → M29 là thứ tự cấp, không phải phụ thuộc SQL
        self.assertNotIn("m4.master_can_cu", "\n".join(SG.M4_03B_COMMON_SQL))


if __name__ == "__main__":
    unittest.main()
