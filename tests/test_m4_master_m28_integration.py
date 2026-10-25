"""M4_MASTER_M28_REGISTRATION — đăng ký M4 master dùng chung (nhận HĐ master, gắn đối tác, căn cứ master/mapping) thành migration 28.

CHỈ thuần (không CSDL, không driver/kết nối PG, không bootstrap sản phẩm, không SQL/migrate/seed/SET ROLE/M9/mạng/Request ngoài):
  - toàn bộ 974.607 byte đầu ``pg_migrations.py`` = baseline 27 (hop-nhat sau M0027 Request nháp; SHA ghim ở đây, không lấy từ code);
  - đoạn M28 = từ mốc 974.607 đến hết dòng ``PG_SCHEMA_VERSION = len(PG_MIGRATIONS)`` ĐẦU TIÊN sau mốc; chỉ import + alias + MỘT tuple
    đăng ký + version; không bản sao SQL. Phần sau đoạn này (29+) KHÔNG thuộc test này — biên tương lai rõ, không khẳng định schema mãi là 28;
  - registry baseline 1–27 dựng lại TỪ CHÍNH prefix gốc (exec độc lập) khớp từng câu/checksum với registry hiện hành;
    master dùng chung ở index 27 đúng MỘT lần, CHÍNH object ``M4_MASTER_DUNG_CHUNG_SQL``, sau M17 (m4 lõi) và M24 (duyệt phiên bản);
  - module hằng SQL nguyên byte (SHA ghim), không import registry/ha_tang, không tự author ordinal.

Không có gì ở đây là nghiệm thu PG/native/HTTP/GUI: bằng chứng áp dụng thật (migrate 0→N trên CSDL riêng) là bước riêng của lát M4-4/7,
còn kiểm PG nhiều phiên là ``tests/test_m4_master_dung_chung_pg.py`` (cần clone riêng, thiếu env thì SkipTest NOT_VERIFIED).
"""

from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.m4 import sql_master_dung_chung as MC
from kho_tri_thuc.m4 import sql_request_nhap as SR

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
PG_PY = SRC / "ha_tang" / "pg_migrations.py"
SQL_PY = SRC / "m4" / "sql_master_dung_chung.py"

# ghim (không tính lại từ code đang chạy)
PREFIX_BYTES, PREFIX_SHA256 = 974_607, "9ceb58b21f73d553bc9cf317e6e720ebed6448358fab65195c1fd2a42ac2d491"  # toàn pg_migrations.py baseline 27
M28_END, M28_PREFIX_SHA256 = 975_546, "f724ea0f6a25bed446949a1e029fcd57808a557ed7218984957b24d82c419795"  # toàn pg_migrations.py baseline 28
SQL_SHA256 = "98d2b711193cfca2946dd041262d808c461059aac063cb347fbcdc03280c233c"  # m4/sql_master_dung_chung.py
M28_JOINED_SHA256 = "f7d6df6763db487c11794fb63fa5b020212ff784e45ac30262a26dfc8c8a4800"  # _hash(câu 28) = sha256("\n".join)
VERSION_DONG = b"PG_SCHEMA_VERSION = len(PG_MIGRATIONS)\n"
DONG_NOI = ("from ..m4.sql_master_dung_chung import M4_MASTER_DUNG_CHUNG_SQL  # noqa: E402 — module chỉ hằng SQL, không import ha_tang",
            "M0028_M4_MASTER_DUNG_CHUNG = M4_MASTER_DUNG_CHUNG_SQL",
            "PG_MIGRATIONS = (*PG_MIGRATIONS, M0028_M4_MASTER_DUNG_CHUNG)",
            "PG_SCHEMA_VERSION = len(PG_MIGRATIONS)")
BANG_MASTER = ("m4.master_can_cu", "m4.master_can_cu_phien_ban")  # bảng mới của gói — không được có trong 1–27


def _doan_m28(raw: bytes) -> bytes:
    """Đoạn M28: [mốc 27, hết dòng version ĐẦU TIÊN sau mốc]. Migration 29+ nối sau đoạn này và nằm ngoài phạm vi test."""
    cuoi = raw.find(VERSION_DONG, PREFIX_BYTES)
    if cuoi < 0:
        raise AssertionError("không thấy dòng version kết thúc khối đăng ký M28 sau mốc 27")
    return raw[PREFIX_BYTES:cuoi + len(VERSION_DONG)]


def _baseline27() -> dict:
    """Registry baseline dựng lại từ CHÍNH 974.607 byte gốc (exec trong namespace riêng) — không dùng giá trị của registry hiện hành."""
    raw = PG_PY.read_bytes()[:PREFIX_BYTES]
    ns = {"__name__": "kho_tri_thuc.ha_tang._pg_baseline27", "__package__": "kho_tri_thuc.ha_tang", "__file__": str(PG_PY)}
    exec(compile(raw, str(PG_PY) + ":baseline27", "exec"), ns)  # noqa: S102 — mã nguồn của chính repo, không nhận đầu vào ngoài
    return ns


def _cho_tao(mau: str, den: int | None = None) -> list[int]:
    """Chỉ số (0-based) các migration (trong PG_MIGRATIONS[:den]) có câu khớp regex ``mau``."""
    return [i for i, m in enumerate(PM.PG_MIGRATIONS[:den]) if any(re.search(mau, s) for s in m)]


class M28Prefix(unittest.TestCase):
    def test_prefix_baseline27_nguyen_byte(self):
        raw = PG_PY.read_bytes()
        self.assertGreater(len(raw), PREFIX_BYTES)
        self.assertEqual(hashlib.sha256(raw[:PREFIX_BYTES]).hexdigest(), PREFIX_SHA256, "prefix baseline 27 bị sửa — chỉ được APPEND")
        truoc = raw[:PREFIX_BYTES].decode("utf-8")
        self.assertTrue(truoc.endswith("M0027_M4_REQUEST = M4_REQUEST_NHAP\nPG_MIGRATIONS = (*PG_MIGRATIONS, M0027_M4_REQUEST)\n"
                                       "PG_SCHEMA_VERSION = len(PG_MIGRATIONS)\n"), "prefix phải dừng đúng sau khối đăng ký M27")
        self.assertNotIn("M4_MASTER_DUNG_CHUNG_SQL", truoc)
        self.assertNotIn("sql_master_dung_chung", truoc)
        self.assertNotIn("M0028", truoc)

    def test_doan_m28_chi_import_alias_mot_dang_ky(self):
        raw = PG_PY.read_bytes()
        self.assertGreaterEqual(len(raw), M28_END)
        self.assertEqual(hashlib.sha256(raw[:M28_END]).hexdigest(), M28_PREFIX_SHA256, "đoạn M28 bị sửa — chỉ được APPEND sau mốc 28")
        doan = _doan_m28(raw)
        self.assertEqual(PREFIX_BYTES + len(doan), M28_END)
        doan = doan.decode("utf-8")
        ma = tuple(x.rstrip() for x in doan.splitlines() if x.strip() and not x.lstrip().startswith("#"))
        self.assertEqual(ma, DONG_NOI, "đoạn M28 chỉ được import + alias + một tuple đăng ký + version")
        self.assertTrue(doan.endswith("\n"))
        self.assertNotRegex("\n".join(ma), r"(?i)\b(CREATE|ALTER|DROP|GRANT|REVOKE|INSERT|UPDATE|DELETE)\s")  # không bản sao SQL
        self.assertNotRegex("\n".join(ma), r"m4\.master_|m4\.nhan_master|m4\.gan_doi_tac")  # không tên đối tượng SQL nào ngoài hằng của module domain
        self.assertNotRegex(doan, r"psycopg|connect\(|bootstrap|FULL_M9|TUONG_THICH")  # không driver/bootstrap/lịch sử/compat mới
        txt = PG_PY.read_text(encoding="utf-8")
        self.assertEqual(txt.count("import M4_MASTER_DUNG_CHUNG_SQL"), 1)
        self.assertEqual(len(re.findall(r"^M0028_M4_MASTER_DUNG_CHUNG = ", txt, re.M)), 1)
        self.assertEqual(len(re.findall(r"^PG_MIGRATIONS = \(\*PG_MIGRATIONS, M0028_M4_MASTER_DUNG_CHUNG\)$", txt, re.M)), 1)

    def test_module_sql_master_nguyen_byte_khong_import_registry(self):
        raw = SQL_PY.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), SQL_SHA256, "module hằng SQL master dùng chung bị sửa")
        src = raw.decode("utf-8")
        self.assertIsNone(re.search(r"^\s*(from|import)\s[^\n]*(pg_migrations|ha_tang|psycopg)", src, re.M))
        self.assertNotIn("M0028", src)  # ordinal do integration owner cấp, không author trong domain constant
        self.assertNotIn("PG_MIGRATIONS", src)


class M28Registry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.B = _baseline27()

    def test_baseline_dung_lai_la_27(self):
        b = self.B["PG_MIGRATIONS"]
        self.assertEqual((len(b), self.B["PG_SCHEMA_VERSION"]), (27, 27))
        self.assertIs(b[26], SR.M4_REQUEST_NHAP)  # module hằng đã nạp: cùng object
        self.assertFalse(any(m is MC.M4_MASTER_DUNG_CHUNG_SQL for m in b))
        for bang in BANG_MASTER:
            self.assertFalse(any(bang in s for m in b for s in m), f"baseline 1–27 không được chứa {bang}")

    def test_prefix_1_27_tung_cau_va_checksum(self):
        b = self.B["PG_MIGRATIONS"]
        self.assertEqual(len(PM.PG_MIGRATIONS[:27]), 27)
        for i in range(27):
            # không assertIs với b[i]: tuple literal của hai lần compile/exec riêng là object khác nhau dù cùng byte — so câu + checksum
            self.assertEqual(tuple(PM.PG_MIGRATIONS[i]), tuple(b[i]), f"migration {i + 1} đổi câu lệnh")
            self.assertEqual(PM._hash(PM.PG_MIGRATIONS[i]), self.B["_hash"](b[i]), f"migration {i + 1} đổi checksum")
        self.assertIs(PM.PG_MIGRATIONS[26], SR.M4_REQUEST_NHAP)
        self.assertIs(PM.PG_MIGRATIONS[26], PM.M0027_M4_REQUEST)
        self.assertEqual(PM.PG_MIGRATION_TUONG_THICH, self.B["PG_MIGRATION_TUONG_THICH"])  # không compatibility checksum mới
        self.assertNotIn(28, set(PM.PG_MIGRATION_TUONG_THICH))
        self.assertEqual(PM.PG_MIGRATIONS_LICH_SU_FULL_M9, self.B["PG_MIGRATIONS_LICH_SU_FULL_M9"])
        self.assertEqual(PM.LEGACY_FULL_M9_M0013_SHA256, self.B["LEGACY_FULL_M9_M0013_SHA256"])

    def test_m28_master_dung_mot_lan_cung_object(self):
        # biên tương lai: version = len và >= 28; master ở index 27 (ngay sau M27 Request), không đòi mãi là phần tử cuối
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        self.assertGreaterEqual(PM.PG_SCHEMA_VERSION, 28)
        self.assertIs(PM.PG_MIGRATIONS[27], MC.M4_MASTER_DUNG_CHUNG_SQL)
        self.assertIs(PM.PG_MIGRATIONS[:28][-1], MC.M4_MASTER_DUNG_CHUNG_SQL)  # hậu tố duy nhất của 1–28, ngay sau M27
        self.assertIs(PM.M0028_M4_MASTER_DUNG_CHUNG, MC.M4_MASTER_DUNG_CHUNG_SQL)
        self.assertIs(PM.M4_MASTER_DUNG_CHUNG_SQL, MC.M4_MASTER_DUNG_CHUNG_SQL)
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS) if m is MC.M4_MASTER_DUNG_CHUNG_SQL], [27])
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS) if tuple(m) == tuple(MC.M4_MASTER_DUNG_CHUNG_SQL)], [27])
        # dấu bảng master dùng chung duy nhất trong 1–28; migration sau 28 được phép FK/tham chiếu
        for bang in BANG_MASTER:
            self.assertEqual(_cho_tao(r"CREATE TABLE " + re.escape(bang) + r"\b", 28), [27], bang)
            self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS[:28]) if any(bang in s for s in m)], [27], bang)
        self.assertIsInstance(MC.M4_MASTER_DUNG_CHUNG_SQL, tuple)
        self.assertTrue(MC.M4_MASTER_DUNG_CHUNG_SQL and all(isinstance(s, str) and s.strip() for s in MC.M4_MASTER_DUNG_CHUNG_SQL))
        self.assertEqual(MC.M4_MASTER_DUNG_CHUNG_SQL[0], "SET LOCAL check_function_bodies = off")
        h28 = PM._hash(PM.PG_MIGRATIONS[27])
        self.assertEqual(h28, PM._hash(MC.M4_MASTER_DUNG_CHUNG_SQL))
        self.assertEqual(h28, M28_JOINED_SHA256, "checksum joined câu 28 lệch pin")
        self.assertNotIn(h28, [PM._hash(m) for m in PM.PG_MIGRATIONS[:27]], "checksum 28 trùng một migration cũ")
        self.assertFalse(any(m is MC.M4_MASTER_DUNG_CHUNG_SQL for m in PM.PG_MIGRATIONS_LICH_SU_FULL_M9))  # không chạm lịch sử full-M9
        self.assertNotIn(PM.M0013, PM.PG_MIGRATIONS)  # full-M9 lịch sử vẫn ngoài chuỗi active

    def test_thu_tu_sau_m17_m24_va_nguon_hien_huu(self):
        # master dùng chung chạy SAU M17 (m4 lõi), SAU M24 (m4.duyet_phien_ban) và M27; các đối tượng nó dựa vào đã có ở migration trước
        self.assertEqual(_cho_tao(r"FUNCTION m4\.ai_id\(", 27), [16])  # M17 m4 lõi
        self.assertEqual(_cho_tao(r"CREATE TABLE m4\.duyet_phien_ban\b", 27), [23])  # M24
        self.assertIs(PM.PG_MIGRATIONS[23], PM.M0024_M4_DUYET)
        self.assertEqual(_cho_tao(r"FUNCTION master\.ktt_danh_tinh\(", 27), [10])
        self.assertTrue(_cho_tao(r"CREATE TABLE master\.hop_dong\b", 27), "master.hop_dong phải có trước M28")
        self.assertTrue(_cho_tao(r"CREATE TABLE master\.doi_tac_ma_junsky\b", 27), "master.doi_tac_ma_junsky phải có trước M28")
        self.assertTrue(_cho_tao(r"CREATE TABLE m4\.ho_so_hop_dong\b", 27), "m4.ho_so_hop_dong phải có trước M28")


if __name__ == "__main__":
    unittest.main()
