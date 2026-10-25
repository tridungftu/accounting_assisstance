"""DA-1 — CRM · Dự án đang bán (QD-20261025-05…09): kiểm THUẦN (không CSDL/driver/mạng; service/handler/app GIẢ).

- Registry: pg_migrations.py chỉ APPEND M0031 sau baseline 30 (prefix nguyên byte, SHA ghim), 1–30 nguyên câu/checksum, M0031 đúng MỘT lần.
- SQL tĩnh M0031: bảng mới có trigger bất biến + RLS + REVOKE vai ứng dụng/PUBLIC; mọi hàm REVOKE PUBLIC; lệnh ghi qua preflight chủ bảng + quyền
  TRƯỚC biên nhận; không DELETE/TRUNCATE/DROP TABLE/GRANT; không định nghĩa lại hàm đọc G7 (crm_g_chuan_doc, crm_kiem_g7…); căn cứ QD-07.
- Chuẩn hóa nhập (quy tắc tiền BG-1c: chuỗi chính xác, CHỈ chữ số ASCII, miền khớp SQL) + lỗi theo trường; service gọi đúng hàm SQL với H
  không gồm khóa; HTTP: route, tham số truy vấn, trường thẩm quyền, mã lỗi → 400/403/404/409/503 + `truong`.
- Seed DEMO: tên có DEMO, ≥ 2 phí khác đơn vị, ≥ 2 lô; bước seed của tool không chạy khi chuẩn bị chưa migrate, không bao giờ ném lỗi.
Luồng PostgreSQL thật: tests/test_crm_du_an_ban_pg.py.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from kho_tri_thuc.giao_dien import crm_g as CG
from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import crm_du_an_ban as D
from kho_tri_thuc.k2 import crm_giao_ket as GK
from kho_tri_thuc.k2 import sql_crm_bg1c as B
from kho_tri_thuc.k2 import sql_crm_du_an_ban as S
from kho_tri_thuc.k2 import sql_crm_kiem_hd as SK
from kho_tri_thuc.k2.crm_mau import CrmMauK2, _h

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
PG_PY = SRC / "ha_tang" / "pg_migrations.py"
SQL_PY = SRC / "k2" / "sql_crm_du_an_ban.py"
PREFIX30_BYTES, PREFIX30_SHA256 = 977_387, "59d8178346925f1f8cb492a88ce243324c35ca81e29205bc9dd961b4557230c5"  # baseline 30 (pin của BG-1c)
VERSION_DONG = b"PG_SCHEMA_VERSION = len(PG_MIGRATIONS)\n"
DONG_NOI = ("from ..k2.sql_crm_du_an_ban import CRM_DU_AN_BAN_SQL  # noqa: E402 — module chỉ hằng SQL, không import ha_tang",
            "M0031_CRM_DU_AN_BAN = CRM_DU_AN_BAN_SQL",
            "PG_MIGRATIONS = (*PG_MIGRATIONS, M0031_CRM_DU_AN_BAN)",
            "PG_SCHEMA_VERSION = len(PG_MIGRATIONS)")
SQL_TXT = "\n".join(S.CRM_DU_AN_BAN_SQL)
LH, DA, DB = "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", "33333333-3333-4333-8333-333333333333"
ME = "MO_PHONG_BAN_HANG"


def tt(**sua):
    return {"vi_tri": "KCN DEMO", "mo_ta": "Mô tả DEMO", "don_gia_niem_yet": "120", "tien_te": "USD", "loai_hinh_id": LH, "thue_suat": "10",
            "gia_dat_tru": "0", "giai_doan_g7": "GD1", **sua}


PHI = [{"ten": "Phí bảo trì DEMO", "loai": "BAO_TRI", "muc": "0.5", "don_vi_tinh": "M2_NAM", "tien_te": "USD", "co_so_tinh": "Diện tích"},
       {"ten": "Phí sử dụng DEMO", "loai": "SU_DUNG", "muc": "15000", "don_vi_tinh": "M2_THANG", "tien_te": "VND"}]


def _ham(ten: str) -> str:
    ds = [s for s in S.CRM_DU_AN_BAN_SQL if f"CREATE OR REPLACE FUNCTION master.{ten}(" in s]
    assert len(ds) == 1, ten
    return ds[0]


def _ma(fn, *a, **kw) -> tuple:
    try:
        fn(*a, **kw)
    except DataError as exc:
        return exc.code, exc.locator
    raise AssertionError("không ném DataError")


# ================================================================================================== 1. registry + SQL tĩnh
class M31Registry(unittest.TestCase):
    def test_prefix_baseline30_nguyen_byte_chi_append(self):
        raw = PG_PY.read_bytes()
        self.assertGreater(len(raw), PREFIX30_BYTES)
        self.assertEqual(hashlib.sha256(raw[:PREFIX30_BYTES]).hexdigest(), PREFIX30_SHA256, "prefix baseline 30 bị sửa — chỉ được APPEND")
        self.assertTrue(raw[:PREFIX30_BYTES].endswith(b"PG_MIGRATIONS = (*PG_MIGRATIONS, M0030_CRM_BG1C)\n" + VERSION_DONG))
        cuoi = raw.find(VERSION_DONG, PREFIX30_BYTES)
        doan = raw[PREFIX30_BYTES:cuoi + len(VERSION_DONG)].decode("utf-8")
        ma = tuple(x.rstrip() for x in doan.splitlines() if x.strip() and not x.lstrip().startswith("#"))
        self.assertEqual(ma, DONG_NOI, "đoạn M31 chỉ được import + alias + một tuple đăng ký + version")
        self.assertNotRegex("\n".join(ma), r"(?i)\b(CREATE|ALTER|DROP|GRANT|REVOKE|INSERT|UPDATE|DELETE)\s")

    def test_1_30_nguyen_cau_checksum_va_m31_mot_lan(self):
        raw = PG_PY.read_bytes()[:PREFIX30_BYTES]
        ns = {"__name__": "kho_tri_thuc.ha_tang._pg_baseline30", "__package__": "kho_tri_thuc.ha_tang", "__file__": str(PG_PY)}
        exec(compile(raw, str(PG_PY) + ":baseline30", "exec"), ns)  # noqa: S102 — mã nguồn của chính repo
        b = ns["PG_MIGRATIONS"]
        self.assertEqual((len(b), ns["PG_SCHEMA_VERSION"]), (30, 30))
        for i in range(30):
            self.assertEqual(tuple(PM.PG_MIGRATIONS[i]), tuple(b[i]), f"migration {i + 1} đổi câu lệnh")
            self.assertEqual(PM._hash(PM.PG_MIGRATIONS[i]), ns["_hash"](b[i]), f"migration {i + 1} đổi checksum")
        self.assertIs(PM.PG_MIGRATIONS[30], S.CRM_DU_AN_BAN_SQL)
        self.assertIs(PM.M0031_CRM_DU_AN_BAN, S.CRM_DU_AN_BAN_SQL)
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS) if m is S.CRM_DU_AN_BAN_SQL], [30])
        self.assertGreaterEqual(PM.PG_SCHEMA_VERSION, 31)
        self.assertNotIn(31, set(PM.PG_MIGRATION_TUONG_THICH))

    def test_module_sql_chi_import_mau_so_m0030(self):
        src = SQL_PY.read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
        nhap = [x.strip() for x in re.findall(r"^[ \t]*(?:from|import)\s.*$", src, re.M)]
        self.assertEqual(len(nhap), 1)
        self.assertTrue(nhap[0].startswith("from .sql_crm_bg1c import _RE_SO  #"), nhap)  # chỉ hằng mẫu số của M0030, không import registry
        for x in ("PG_MIGRATIONS", "M0031", "ha_tang"):
            self.assertNotIn(x, src.split('"""', 2)[2])  # ngoài docstring: không tự đăng ký/đoán ordinal
        self.assertIs(S._RE_SO, B._RE_SO)
        self.assertEqual(GK.RE_SO.pattern, S._RE_SO.strip("'")[1:-1])  # Python (báo giá + dự án đang bán) = literal SQL
        self.assertIs(D.RE_SO, GK.RE_SO)


class M31SqlTinh(unittest.TestCase):
    def test_bang_moi_bat_bien_rls_revoke(self):
        for t in S._BANG:
            self.assertIn(f"CREATE TABLE master.{t} (", SQL_TXT)
            self.assertRegex(SQL_TXT, rf"CREATE TRIGGER \w+ BEFORE INSERT OR UPDATE OR DELETE ON master\.{t} FOR EACH ROW EXECUTE FUNCTION "
                                      r"master\.(crm_g_bat_bien|crm_da_dong_mot_lan)\(\)")
            self.assertIn(f"ALTER TABLE master.{t} ENABLE ROW LEVEL SECURITY", SQL_TXT)
        self.assertIn("REVOKE ALL ON " + S._BANG_DS + " FROM PUBLIC", S.CRM_DU_AN_BAN_SQL)
        self.assertIn("EXECUTE format('REVOKE ALL ON " + S._BANG_DS + " FROM %I', r)", SQL_TXT)
        # phiên bản/lịch sử lô: đóng hiệu lực MỘT lần, mọi cột khác bất biến; phí/gốc/lô/bằng chứng G7: chỉ ghi thêm
        dong = _ham("crm_da_dong_mot_lan")
        self.assertIn("(to_jsonb(NEW) - 'hieu_luc_den') IS DISTINCT FROM (to_jsonb(OLD) - 'hieu_luc_den')", dong)
        self.assertIn("IF TG_OP = 'DELETE' THEN", dong)
        self.assertIn("CREATE UNIQUE INDEX crm_da_ban_phien_ban_mo_uq ON master.crm_da_ban_phien_ban (da_ban_id) WHERE hieu_luc_den IS NULL", SQL_TXT)
        self.assertIn("CREATE UNIQUE INDEX crm_da_ban_lo_ls_mo_uq ON master.crm_da_ban_lo_ls (lo_id) WHERE hieu_luc_den IS NULL", SQL_TXT)

    def test_moi_ham_revoke_public(self):
        ten = set(re.findall(r"CREATE OR REPLACE FUNCTION (master\.\w+)\(", SQL_TXT))
        revoke = S.CRM_DU_AN_BAN_SQL[-1]
        self.assertTrue(revoke.startswith("REVOKE EXECUTE ON FUNCTION ") and revoke.endswith(" FROM PUBLIC"))
        self.assertEqual(ten, set(re.findall(r"(master\.\w+)\(", revoke)))
        self.assertNotRegex(SQL_TXT, r"\bGRANT\b")
        for cam in ("DELETE FROM", "TRUNCATE", "DROP TABLE", "DROP FUNCTION", "SET ROLE", "BYPASSRLS", "DISABLE TRIGGER"):
            self.assertNotIn(cam, SQL_TXT)

    def test_khong_dinh_nghia_lai_ham_doc_g7_va_ham_cu(self):
        for cu in ("crm_g_chuan_doc", "crm_kiem_g7", "crm_kiem_lich_ky", "crm_g_chuan_lap", "crm_g_chuan_gui", "crm_g_chuan_duyet", "crm_g_duoc",
                   "crm_g_dich", "crm_g_bat_bien", "crm_bo_chuan_phien_ban_kiem", "crm_gk_bao_gia_luu"):
            self.assertNotIn(f"CREATE OR REPLACE FUNCTION master.{cu}(", SQL_TXT)
        # thay đổi DUY NHẤT trên bảng cũ: nới đúng một CHECK valid_to của crm_bo_chuan_phien_ban (> → >=), fail-closed nếu không thấy đúng 1
        alter = [s for s in S.CRM_DU_AN_BAN_SQL if "ALTER TABLE master." in s and "ENABLE ROW LEVEL SECURITY" not in s]
        self.assertEqual(len(alter), 2)
        self.assertIn("LIKE '%valid_to > valid_from%'", alter[0])
        self.assertIn("IF n <> 1 THEN", alter[0])
        self.assertIn("CHECK (valid_to IS NULL OR (valid_from IS NOT NULL AND valid_to >= valid_from))", alter[1])
        # các chỗ đọc "bộ chuẩn hiệu lực" giữ nguyên điều kiện trạng thái + khoảng ngày → đọc được phiên bản áp dụng ngay (khoảng rỗng không bao giờ khớp)
        g7 = next(s for s in SK.CRM_G6A_SQL if "FUNCTION master.crm_kiem_g7(" in s)
        self.assertIn("v.trang_thai = 'HIEU_LUC' AND v.valid_from <= k.ngay_ky AND (v.valid_to IS NULL OR v.valid_to > k.ngay_ky)", g7)
        doc = next(s for s in PM.M0018_CRM_G if "FUNCTION master.crm_g_chuan_doc(" in s)
        self.assertIn("p.trang_thai = 'HIEU_LUC'\n                  AND p.valid_from <= p_as_of AND (p.valid_to IS NULL OR p_as_of < p.valid_to)", doc)

    def test_lenh_ghi_preflight_truoc_bien_nhan(self):
        vao = _ham("crm_da_vao")
        self.assertLess(vao.index("master.la_chu_bang('master.crm_da_ban'::regclass)"), vao.index("master.crm_g_ghim_quyen(p_pn)"))
        self.assertLess(vao.index("master.crm_g_ghim_quyen(p_pn)"), vao.index("master.crm_da_duoc_doc(p_pn)"))
        self.assertLess(vao.index("master.crm_da_duoc_ghi(p_pn)"), vao.index("master.crm_g_bn_tra("))
        ghi = _ham("crm_da_duoc_ghi")
        self.assertIn("ARRAY['BAN_HANG','KE_TOAN','KE_TOAN_TRUONG']", ghi)
        self.assertIn("master.ktt_duoc(p_pn, 'CRM')", ghi)
        self.assertNotIn("CFO", ghi)
        for ten, hanh in (("crm_da_bat_ban", "'CRM_DA_BAT_BAN'"), ("crm_da_cap_nhat", "p_hanh"), ("crm_da_doi_trang_thai", "hanh"),
                          ("crm_da_lo_ghi", "'CRM_DA_LO'"), ("crm_g_chuan_ap_dung", "'CRM_CHUAN_AP_DUNG'")):
            f = _ham(ten)
            self.assertIn(f"cu := master.crm_da_vao({hanh},", f)
            i = f.index("cu := master.crm_da_vao(")
            self.assertNotRegex(f[:i], r"\b(INSERT|UPDATE)\s", ten)  # không ghi gì trước preflight
            self.assertIn("PERFORM master.crm_g_bn_ghi(", f)
        for ten in ("crm_da_anh_chup", "crm_da_anh_chup_pb"):
            self.assertIn("master.crm_da_duoc_doc(", _ham(ten))
            self.assertIn("master.la_chu_bang('master.crm_da_ban'::regclass)", _ham(ten))

    def test_xem_co_phan_cong_van_khong_duoc_ghi(self):
        import sqlite3

        # Chạy chính biểu thức quyền SQL với các hàm IAM giả; phân công luôn được cấp, không thay thế điều kiện vai/module/pháp nhân.
        sql = re.search(r"SELECT (.*?)\$\$", _ham("crm_da_duoc_ghi"), re.S).group(1)
        sql = sql.replace("master.", "").replace("p_pn", ":pn")
        sql = sql.replace("ARRAY['BAN_HANG','KE_TOAN','KE_TOAN_TRUONG']", "'BAN_HANG,KE_TOAN,KE_TOAN_TRUONG'")
        ctx = {"vai": "XEM", "crm": True}
        with sqlite3.connect(":memory:") as c:
            c.create_function("ktt_duoc", 2, lambda pn, module: pn == DA and module == "CRM" and ctx["crm"])
            c.create_function("ktt_co_vai", 3, lambda pn, vai, loai: pn == DA and ctx["vai"] in vai.split(","))
            c.create_function("ktt_hanh_dong_duoc", 4, lambda *a: True)
            self.assertEqual(c.execute("SELECT " + sql, {"pn": DA}).fetchone()[0], 0)
            for vai in ("BAN_HANG", "KE_TOAN", "KE_TOAN_TRUONG"):
                ctx["vai"] = vai
                self.assertEqual(c.execute("SELECT " + sql, {"pn": DA}).fetchone()[0], 1)
                self.assertEqual(c.execute("SELECT " + sql, {"pn": DB}).fetchone()[0], 0)
                ctx["crm"] = False
                self.assertEqual(c.execute("SELECT " + sql, {"pn": DA}).fetchone()[0], 0)
                ctx["crm"] = True

    def test_g7_cas_sau_khoa_truoc_khong_doi_va_ghi(self):
        f = _ham("crm_g_chuan_ap_dung")
        khoa = f.index("FROM master.crm_bo_chuan WHERE")
        doc = f.index("SELECT * INTO mo FROM master.crm_bo_chuan_phien_ban")
        cas = f.index("IF p_expected_version IS DISTINCT FROM coalesce(mo.phien_ban, 0) THEN")
        self.assertLess(f.index("pg_advisory_xact_lock("), khoa)
        self.assertIn("FOR UPDATE;", f[khoa:doc])
        self.assertIn("FOR UPDATE;", f[doc:cas])
        self.assertLess(cas, f.index("IF mo.id IS NOT NULL AND mo.dong_sha256 = sha THEN"))
        self.assertLess(cas, f.index("INSERT INTO master.crm_bo_chuan_phien_ban"))
        self.assertIn("RAISE EXCEPTION 'CRM_DA_PHIEN_BAN_CU:", f)
        self.assertIn("p_expected_version IS NULL OR p_expected_version < 0", f)

    def test_g7_ap_dung_ngay_can_cu_qd07(self):
        f = _ham("crm_g_chuan_ap_dung")
        self.assertEqual(S.CAN_CU_G7, "QD-20261025-07")
        self.assertEqual(f.count("'QD-20261025-07'"), 4)  # bằng chứng + nhật ký can_cu + kq (2 nhánh)
        self.assertIn("bỏ bước CFO duyệt (QD-20261025-07)", f)
        self.assertIn("'CRM_DA_CHUA_BAT_BAN:", f)
        self.assertIn("RAISE EXCEPTION 'CRM_G_HIEU_LUC_CHONG:", f)  # không chồng lên phiên bản CFO duyệt hiệu lực tương lai
        self.assertIn("VALUES (b.id, a.phap_nhan_id, n, 'DRAFT', so, sha, ai)", f)  # trigger cũ: phiên bản mới phải DRAFT
        self.assertLess(f.index("SET valid_to = ngay"), f.index("SET trang_thai = 'HIEU_LUC', valid_from = ngay"))
        self.assertIn("CHECK (can_cu = 'QD-20261025-07')", SQL_TXT)
        self.assertNotIn("viec_can_duyet", f)  # không tạo việc CFO
        self.assertNotIn("duyet_boi", f)  # không giả là CFO đã duyệt

    def test_mien_so_sql_khop_python(self):
        for cot in ("don_gia_niem_yet ~ ", "muc ~ ", "gia_dat_tru::text ~ ", "dien_tich ~ "):
            self.assertIn(cot + B._RE_SO, SQL_TXT)
        self.assertIn("thue_suat text NOT NULL DEFAULT '10' CHECK (thue_suat IN ('10','8','5','0','KCT','KKKNT'))", SQL_TXT)
        self.assertIn("gia_dat_tru numeric NOT NULL DEFAULT 0 CHECK (gia_dat_tru >= 0", SQL_TXT)
        self.assertIn("gia_dat_tru <= don_gia_niem_yet::numeric", SQL_TXT)
        self.assertNotIn("co_so_thue", SQL_TXT)
        self.assertNotIn("vat_phan_tram", SQL_TXT)
        self.assertIn("dien_tich::numeric > 0", SQL_TXT)
        self.assertIn("tien_te IN ('VND','USD')", SQL_TXT)
        self.assertIn("don_vi_tinh IN ('M2_THANG','M2_NAM','LAN')", SQL_TXT)
        self.assertIn("loai IN ('BAO_TRI','SU_DUNG','KHAC')", SQL_TXT)
        self.assertIn("trang_thai IN ('CON_TRONG','GIU_CHO','DA_BAN','KHONG_BAN')", SQL_TXT)
        self.assertEqual(set(D.TIEN_TE), {"VND", "USD"})
        self.assertEqual(set(D.DON_VI_TINH), {"M2_THANG", "M2_NAM", "LAN"})
        self.assertEqual(set(D.LOAI_PHI), {"BAO_TRI", "SU_DUNG", "KHAC"})
        self.assertEqual(set(D.TRANG_THAI_LO), {"CON_TRONG", "GIU_CHO", "DA_BAN", "KHONG_BAN"})
        self.assertEqual(tuple(re.findall(r"'(\w+)'", S._TT_KHOA)), D.TRUONG_TT)
        self.assertEqual(tuple(re.findall(r"'(\w+)'", S._PHI_KHOA)), D.TRUONG_PHI)
        self.assertEqual(tuple(re.findall(r"'(\w+)'", S._LO_KHOA)), D.TRUONG_LO)


# ================================================================================================== 2. chuẩn hóa nhập
class ChuanHoa(unittest.TestCase):
    def test_thong_tin_hop_le_va_gon(self):
        x = D.chuan_hoa_thong_tin(tt(don_gia_niem_yet="0120.50", vi_tri="  KCN DEMO  ", mo_ta="", giai_doan_g7=""))
        self.assertEqual(x, {"vi_tri": "KCN DEMO", "mo_ta": None, "don_gia_niem_yet": "120.5", "tien_te": "USD", "loai_hinh_id": LH,
                             "thue_suat": "10", "gia_dat_tru": "0", "giai_doan_g7": None})
        self.assertEqual(tuple(x), D.TRUONG_TT)
        self.assertEqual(D.chuan_hoa_thong_tin({"tien_te": "VND", "loai_hinh_id": LH.upper()})["loai_hinh_id"], LH)

    def test_thong_tin_loi_theo_truong(self):
        ca = ((tt(la="x"), ("CRM_DA_YEU_CAU_SAI", "thong_tin.la")),
              (tt(don_gia_niem_yet="٢٥٩٩٩.٥"), ("CRM_DA_SO_SAI", "thong_tin.don_gia_niem_yet")),
              (tt(don_gia_niem_yet="１２０"), ("CRM_DA_SO_SAI", "thong_tin.don_gia_niem_yet")),
              (tt(don_gia_niem_yet="1,5"), ("CRM_DA_SO_SAI", "thong_tin.don_gia_niem_yet")),
              (tt(don_gia_niem_yet="-1"), ("CRM_DA_SO_SAI", "thong_tin.don_gia_niem_yet")),
              (tt(don_gia_niem_yet=120), ("CRM_DA_SO_SAI", "thong_tin.don_gia_niem_yet")),
              (tt(don_gia_niem_yet="1" * 25), ("CRM_DA_SO_SAI", "thong_tin.don_gia_niem_yet")),
              (tt(vat_phan_tram="100.5"), ("CRM_DA_YEU_CAU_SAI", "thong_tin.vat_phan_tram")),
              (tt(tien_te="EUR"), ("CRM_DA_YEU_CAU_SAI", "thong_tin.tien_te")),
              (tt(tien_te=None), ("CRM_DA_TIEN_TE_SAI", "thong_tin.tien_te")),
              (tt(loai_hinh_id=None), ("CRM_DA_THIEU_LOAI_HINH", "thong_tin.loai_hinh_id")),
              (tt(loai_hinh_id="x"), ("CRM_DA_YEU_CAU_SAI", "thong_tin.loai_hinh_id")),
              (tt(co_so_thue="VAT"), ("CRM_DA_YEU_CAU_SAI", "thong_tin.co_so_thue")),
              (tt(giai_doan_g7="GĐ 1"), ("CRM_DA_YEU_CAU_SAI", "thong_tin.giai_doan_g7")),
              (tt(vi_tri="a\x01b"), ("CRM_DA_YEU_CAU_SAI", "thong_tin.vi_tri")),
              (tt(vi_tri="{{x}}"), ("CRM_DA_YEU_CAU_SAI", "thong_tin.vi_tri")),
              (tt(vi_tri="x" * 501), ("CRM_DA_YEU_CAU_SAI", "thong_tin.vi_tri")),
              ([], ("CRM_DA_YEU_CAU_SAI", "thong_tin")))
        for v, mong in ca:
            with self.subTest(v=v):
                self.assertEqual(_ma(D.chuan_hoa_thong_tin, v), mong)
        self.assertEqual(D.chuan_hoa_thong_tin(tt(mo_ta="dòng 1\ndòng 2"))["mo_ta"], "dòng 1\ndòng 2")  # mô tả nhiều dòng

    def test_thue_danh_muc_va_gia_dat_tru(self):
        x = D.chuan_hoa_thong_tin({"tien_te": "USD", "loai_hinh_id": LH})
        self.assertEqual((x["thue_suat"], x["gia_dat_tru"]), ("10", "0"))
        for ma in ("10", "8", "5", "0", "KCT", "KKKNT"):
            self.assertEqual(D.chuan_hoa_thong_tin(tt(thue_suat=ma))["thue_suat"], ma)
        for v in ("7", "100", "10.0", "１０", "kct", " 8", "", None, 10, True, [], {}):
            with self.subTest(thue=v):
                self.assertEqual(_ma(D.chuan_hoa_thong_tin, tt(thue_suat=v)), ("CRM_DA_YEU_CAU_SAI", "thong_tin.thue_suat"))
        for v in ("120.000000000001", "-1", "1e1", "1,5", "٢٤", "２４", " 24", "1" * 25, "0." + "1" * 13, "", None, 24, True):
            with self.subTest(dat=v):
                self.assertEqual(_ma(D.chuan_hoa_thong_tin, tt(gia_dat_tru=v)), ("CRM_DA_SO_SAI", "thong_tin.gia_dat_tru"))
        for v in ("0", "24.50", "120"):
            self.assertEqual(D.chuan_hoa_thong_tin(tt(gia_dat_tru=v))["gia_dat_tru"], {"24.50": "24.5"}.get(v, v))
        self.assertEqual(_ma(D.chuan_hoa_thong_tin, tt(don_gia_niem_yet=None, gia_dat_tru="1")), ("CRM_DA_SO_SAI", "thong_tin.gia_dat_tru"))

    def test_phi(self):
        x = D.chuan_hoa_phi(PHI)
        self.assertEqual([(p["don_vi_tinh"], p["muc"], p["co_so_tinh"]) for p in x], [("M2_NAM", "0.5", "Diện tích"), ("M2_THANG", "15000", None)])
        self.assertEqual(D.chuan_hoa_phi(None), [])
        self.assertEqual(D.chuan_hoa_phi([]), [])
        ca = (([dict(PHI[0], muc=None)], ("CRM_DA_PHI_SAI", "phi.0.muc")),
              ([PHI[0], dict(PHI[1], muc="1e3")], ("CRM_DA_SO_SAI", "phi.1.muc")),
              ([PHI[0], dict(PHI[0], ten="PHÍ BẢO TRÌ DEMO")], ("CRM_DA_PHI_SAI", "phi.1.ten")),
              ([dict(PHI[0], don_vi_tinh="M2")], ("CRM_DA_YEU_CAU_SAI", "phi.0.don_vi_tinh")),
              ([dict(PHI[0], tien_te=None)], ("CRM_DA_PHI_SAI", "phi.0.tien_te")),
              ([dict(PHI[0], loai="PHI")], ("CRM_DA_YEU_CAU_SAI", "phi.0.loai")),
              ([dict(PHI[0], them=1)], ("CRM_DA_PHI_SAI", "phi.0")),
              ([PHI[0]] * 51, ("CRM_DA_PHI_SAI", "phi")),
              ({"ten": "x"}, ("CRM_DA_PHI_SAI", "phi")))
        for v, mong in ca:
            with self.subTest(v=str(v)[:60]):
                self.assertEqual(_ma(D.chuan_hoa_phi, v), mong)

    def test_lo(self):
        x = D.chuan_hoa_lo([{"ma": " CN-A01 ", "dien_tich": "15000.50"}, {"ma": "CN-A02", "dien_tich": "1", "trang_thai": "GIU_CHO", "expected_lan": 2}])
        self.assertEqual([(r["ma"], r["dien_tich"], r["trang_thai"], r["expected_lan"]) for r in x],
                         [("CN-A01", "15000.5", None, None), ("CN-A02", "1", "GIU_CHO", 2)])
        ca = (([{"ma": "A", "dien_tich": "1"}, {"ma": "a", "dien_tich": "2"}], ("CRM_DA_LO_SAI", "lo.1.ma")),
              ([{"ma": "A", "dien_tich": "0"}], ("CRM_DA_SO_SAI", "lo.0.dien_tich")),
              ([{"ma": "A"}], ("CRM_DA_LO_SAI", "lo.0.dien_tich")),
              ([{"dien_tich": "1"}], ("CRM_DA_LO_SAI", "lo.0.ma")),
              ([{"ma": "A", "dien_tich": "1", "expected_lan": True}], ("CRM_DA_YEU_CAU_SAI", "lo.0.expected_lan")),
              ([{"ma": "A", "dien_tich": "1", "expected_lan": "1"}], ("CRM_DA_YEU_CAU_SAI", "lo.0.expected_lan")),
              ([{"ma": "A", "dien_tich": "1", "trang_thai": "BAN"}], ("CRM_DA_YEU_CAU_SAI", "lo.0.trang_thai")),
              ([{"ma": "A", "dien_tich": "٣"}], ("CRM_DA_SO_SAI", "lo.0.dien_tich")),
              ([], ("CRM_DA_LO_SAI", "lo")),
              ([{"ma": "A", "dien_tich": "1"}] * 501, ("CRM_DA_LO_SAI", "lo")))
        for v, mong in ca:
            with self.subTest(v=str(v)[:60]):
                self.assertEqual(_ma(D.chuan_hoa_lo, v), mong)


# ================================================================================================== 3. service (CrmMauK2 GIẢ)
class _C:
    """Kết nối giả: trả ảnh chụp cho crm_da_anh_chup."""

    def __init__(self, anh=None):
        self.anh, self.goi = anh, []

    def execute(self, sql, params=()):
        self.goi.append((sql, params))
        anh = self.anh

        class _R:
            def fetchone(self_):
                return {"r": anh}
        return _R()


class _Mau(CrmMauK2):
    """CrmMauK2 không kết nối: ghi lại lệnh SQL (kiểm tham số, H, thứ tự kiểm TRƯỚC SQL)."""

    def __init__(self, conn=None):  # noqa: D107 — không gọi __init__ thật (psycopg)
        self.conn_tin_cay, self.lenh, self.c = object(), [], conn or _C()
        self.hom_nay = lambda: __import__("datetime").date(2026, 10, 25)

    def danh_tinh(self, dang_nhap):
        return {"id": "nd-1", "dang_nhap": dang_nhap, "vai_tro": "BAN_HANG"}

    def _lenh(self, dt, sql, params):
        self.lenh.append((sql, params))
        return {"ok": True, "lap_lai": False}

    @contextmanager
    def _tx(self, dt, *, rr=False):
        yield self.c


class Service(unittest.TestCase):
    def setUp(self):
        self.m = _Mau()
        self.s = D.CrmDuAnBanK2(self.m)

    def test_bat_ban_tham_so_va_h_khong_gom_khoa(self):
        self.s.bat_ban(ME, du_an_id=DA, thong_tin=tt(don_gia_niem_yet="120.50"), phi=PHI, khoa="k-1")
        self.s.bat_ban(ME, du_an_id=DA, thong_tin=tt(don_gia_niem_yet="120.5"), phi=PHI, khoa="k-2")
        (sql1, p1), (_, p2) = self.m.lenh
        self.assertIn("master.crm_da_bat_ban(%s, %s, %s::uuid, %s::jsonb, %s::jsonb, %s)", sql1)
        self.assertEqual((p1[0], p1[2], p1[5]), ("k-1", DA, None))
        self.assertEqual(p1[1], p2[1])  # H theo yêu cầu đã chuẩn hóa, không gồm khóa
        self.assertEqual(p1[1], _h("CRM_DA_BAT_BAN", {"du_an_id": DA, "thong_tin": D.chuan_hoa_thong_tin(tt(don_gia_niem_yet="120.5")), "phi": D.chuan_hoa_phi(PHI),
                                                     "ly_do": None}))
        self.assertEqual(json.loads(p1[3])["don_gia_niem_yet"], "120.5")
        self.assertEqual(len(json.loads(p1[4])), 2)

    def test_kiem_truoc_sql(self):
        for kw, ma in ((dict(du_an_id=DA, thong_tin=tt(), khoa="khóa có dấu"), "CRM_G_KHOA"),
                       (dict(du_an_id="x", thong_tin=tt(), khoa="k"), "CRM_G_YEU_CAU_SAI"),
                       (dict(du_an_id=DA, thong_tin=tt(tien_te="JPY"), khoa="k"), "CRM_DA_YEU_CAU_SAI"),
                       (dict(du_an_id=DA, thong_tin=tt(), phi=[{"ten": "x"}], khoa="k"), "CRM_DA_PHI_SAI")):
            with self.subTest(ma=ma):
                self.assertEqual(_ma(self.s.bat_ban, ME, **kw)[0], ma)
        for n in (None, True, "1", 0, 1.0):
            self.assertEqual(_ma(self.s.cap_nhat, ME, da_ban_id=DB, expected_phien_ban=n, thong_tin=tt(), khoa="k")[0], "CRM_DA_YEU_CAU_SAI")
        self.assertEqual(_ma(self.s.sua_phi, ME, da_ban_id=DB, expected_phien_ban=1, phi=None, khoa="k"), ("CRM_DA_PHI_SAI", "phi"))
        self.assertEqual(_ma(self.s.ngung_ban, ME, da_ban_id=DB, expected_phien_ban=1, ly_do="  ", khoa="k"), ("CRM_DA_THIEU_LY_DO", "ly_do"))
        self.assertEqual(self.m.lenh, [])  # mọi lỗi nhập dừng TRƯỚC giao dịch/SQL

    def test_cac_lenh_goi_dung_ham(self):
        self.s.cap_nhat(ME, da_ban_id=DB, expected_phien_ban=3, thong_tin=tt(), khoa="a")
        self.s.cap_nhat(ME, da_ban_id=DB, expected_phien_ban=3, thong_tin=tt(), phi=[], khoa="b")
        self.s.sua_phi(ME, da_ban_id=DB, expected_phien_ban=4, phi=PHI, ly_do="đổi phí", khoa="c")
        self.s.ghi_lo(ME, da_ban_id=DB, lo=[{"ma": "A", "dien_tich": "1"}, {"ma": "B", "dien_tich": "2", "expected_lan": 1}], khoa="d")
        self.s.ngung_ban(ME, da_ban_id=DB, expected_phien_ban=5, ly_do="tạm dừng", khoa="e")
        self.s.mo_ban_lai(ME, da_ban_id=DB, expected_phien_ban=6, khoa="f")
        l = self.m.lenh
        self.assertIn("'CRM_DA_CAP_NHAT'", l[0][0])
        self.assertIsNone(l[0][1][5])  # phí không gửi → NULL (giữ phí hiện hành)
        self.assertEqual(json.loads(l[1][1][5]), [])
        self.assertIn("'CRM_DA_PHI', %s::uuid, %s, NULL, %s::jsonb", l[2][0])
        self.assertEqual(json.loads(l[3][1][3]), [{"ma": "A", "dien_tich": "1"}, {"ma": "B", "dien_tich": "2", "expected_lan": 1}])  # bỏ trường null
        self.assertEqual(l[4][1][3:], (5, False, "tạm dừng"))
        self.assertEqual(l[5][1][3:], (6, True, None))
        self.assertNotEqual(l[0][1][1], l[1][1][1])  # cùng thông tin nhưng có/không phí → yêu cầu khác (H khác)

    def test_tien_do_cas_tham_so_va_hash(self):
        dong = [{"lan": "1", "gia_tri_loai": "PERCENT", "gia_tri_thap_phan": "100", "moc_loai": "SU_KIEN", "moc_su_kien": "KY_HD"}]
        self.s.ap_dung_tien_do(ME, du_an_id=DA, expected_version=0, giai_doan="", dong=dong, khoa="g")
        self.s.ap_dung_tien_do(ME, du_an_id=DA, expected_version=1, giai_doan="GD1", dong=dong, khoa="h")
        (sql, p), (_, p2) = self.m.lenh
        self.assertIn("master.crm_g_chuan_ap_dung(%s, %s, %s::uuid, %s, %s::jsonb, %s)", sql)
        self.assertEqual((p[0], p[2], p[3], p2[3]), ("g", DA, None, "GD1"))
        self.assertEqual((p[5], p2[5]), (0, 1))
        self.assertEqual(p[1], _h("CRM_CHUAN_AP_DUNG", {"du_an_id": DA, "giai_doan": None, "dong": json.loads(p[4]), "expected_version": 0}))
        self.s.ap_dung_tien_do(ME, du_an_id=DA, expected_version=1, dong=dong, khoa="j")
        self.assertNotEqual(p[1], self.m.lenh[-1][1][1])  # đổi phiên bản mong đợi → đổi H
        self.s.ap_dung_tien_do(ME, du_an_id=DA, expected_version=0, dong=dong, khoa="k")
        self.assertEqual(p[1], self.m.lenh[-1][1][1])  # đổi khóa → giữ H
        self.assertEqual(len(json.loads(p[4])), 1)
        self.assertEqual(json.loads(p[4])[0]["moc_ngay"], None)  # dòng đủ 9 cột typed như G7
        self.assertEqual(_ma(self.s.ap_dung_tien_do, ME, du_an_id=DA, expected_version=0, giai_doan="GĐ", dong=dong, khoa="i")[0], "CRM_G_YEU_CAU_SAI")
        self.assertEqual(_ma(self.s.ap_dung_tien_do, ME, du_an_id=DA, expected_version=0, dong=[], khoa="i")[0], "CRM_G_CHUAN_SAI")
        self.assertEqual(_ma(self.s.ap_dung_tien_do, ME, du_an_id=DA, expected_version=0, dong=[{"lan": "1", "gia_tri_loai": "PERCENT", "gia_tri_thap_phan": 30}],
                             khoa="i")[0], "CRM_G_CHUAN_SAI")
        for n in (None, True, False, "1", -1, 1.0, 1_000_000_000):
            self.assertEqual(_ma(self.s.ap_dung_tien_do, ME, du_an_id=DA, expected_version=n, dong=dong, khoa="i"),
                             ("CRM_DA_YEU_CAU_SAI", "expected_version"))
        self.assertEqual(len(self.m.lenh), 4)

    def test_anh_chup_mac_dinh_va_trong(self):
        anh = {"kieu": D.KIEU_ANH_CHUP, "trang_thai": "DANG_BAN", "ngay": "2026-10-25",
               "phien_ban": {"so": 2, "hieu_luc_tu": "2026-10-25", "hieu_luc_den": None}, "don_gia": "120.5", "tien_te": "USD",
               "loai_hinh": {"ten": "KCN DEMO", "con_hieu_luc": False}, "thue": {"thue_suat": "10", "nhan": "Thuế suất 10%", "gia_chua_gom_vat": True},
               "gia_dat_tru": "24",
               "phi": [{"ten": "Phí bảo trì DEMO", "loai": "BAO_TRI", "muc": "0.5", "don_vi_tinh": "M2_NAM", "tien_te": "USD", "co_so_tinh": None}],
               "lo": [{"ma": "CN-A01", "dien_tich": "15000.5", "trang_thai": "GIU_CHO"}],
               "bo_chuan": {"trang_thai": "HIEU_LUC", "giai_doan": "GD1", "nguon": "AP_DUNG_NGAY", "version": {"phien_ban": 3, "valid_from": "2026-10-25"}}}
        m = _Mau(_C(anh))
        r = D.CrmDuAnBanK2(m).anh_chup_mac_dinh(ME, DA)
        self.assertEqual(m.c.goi[0], ("SELECT master.crm_da_anh_chup(%s::uuid, %s::date) AS r", (DA, "2026-10-25")))  # mặc định hôm nay
        ht = r["hien_thi"]
        self.assertEqual((ht["don_gia"], ht["phi"][0]["muc"], ht["lo"][0]["dien_tich"], ht["lo"][0]["trang_thai"], ht["ngay"]),
                         ("120,5 USD/m²", "0,5 USD/m²/năm", "15.000,5 m²", "Đang giữ chỗ", "25/10/2026"))
        self.assertIn("cần chọn lại", ht["loai_hinh"])
        self.assertIn("QD-20261025-07", ht["bo_chuan"])
        self.assertEqual(ht["thue"], "Giá chưa gồm VAT · Thuế suất 10%")
        self.assertEqual((r["thue"], r["gia_dat_tru"], ht["gia_dat_tru"]), (anh["thue"], "24", "24 USD/m²"))
        D.CrmDuAnBanK2(m).anh_chup_mac_dinh(ME, DA, "2026-09-30")
        self.assertEqual(m.c.goi[-1][1], (DA, "2026-09-30"))
        self.assertEqual(_ma(D.CrmDuAnBanK2(m).anh_chup_mac_dinh, ME, DA, "30/09/2026")[0], "CRM_G_YEU_CAU_SAI")
        self.assertEqual(D.hien_thi_anh_chup({"trang_thai": "CHUA_BAT_BAN", "ngay": "2026-10-25", "phien_ban": None}),
                         {"trang_thai": "Chưa có trong danh mục đang bán", "ngay": "25/10/2026"})

    def test_danh_muc_nhan_viet(self):
        dm = D.danh_muc()
        self.assertEqual(dm["thue_suat"], [{"ma": k, "nhan": v} for k, v in D.THUE_SUAT.items()])
        self.assertEqual([x["ma"] for x in dm["thue_suat"]], ["10", "8", "5", "0", "KCT", "KKKNT"])
        self.assertNotIn("co_so_thue", dm)
        self.assertEqual([x["nhan"] for x in dm["don_vi_tinh"]], ["m²/tháng", "m²/năm", "lần"])
        for k, ds in dm.items():
            for x in ds:
                if k != "tien_te":  # mã tiền tệ (VND/USD) là đơn vị nghiệp vụ
                    self.assertNotRegex(x["nhan"], r"^[A-Z0-9_]+$")  # không đưa mã kỹ thuật làm nhãn


# ================================================================================================== 4. HTTP (handler/app GIẢ)
class _H:
    def __init__(self, path, body=None):
        self.path, self.body, self.headers = path, body, {}
        self.st = self.data = None

    def json_body(self):
        return self.body

    def crm_sid(self):
        return "sid-gia"

    def send_content(self, status, data, mime=None, headers=None):
        self.st, self.data = status, data


class _Da:
    def __init__(self, loi=None):
        self.goi, self.loi, self.mau = [], loi, type("M", (), {"ly_do_chua_san_sang": None})()

    def __getattr__(self, ten):
        if ten.startswith("_"):
            raise AttributeError(ten)

        def f(*a, **kw):
            self.goi.append((ten, a, kw))
            if self.loi is not None:
                raise self.loi
            return {"ham": ten}
        return f


class _App:
    def __init__(self, da):
        self.mutation_lock = threading.Lock()
        self.__dict__["_crm_da"] = da

    def crm_phien(self, sid, *, tao=False):
        return sid, ME, False

    @staticmethod
    def _crm_db(fn, *a):
        return fn(*a)


class Http(unittest.TestCase):
    def goi(self, post, path, body=None, query=None, raw=None, da=None):
        da = _Da() if da is None else da
        h = _H(raw or path, body)
        CG.dieu_huong(h, _App(da), post, path, query or {})
        return h, da

    def test_la_route(self):
        for post, p in ((False, "/api/crm/du-an-ban"), (False, "/api/crm/du-an-ban/anh-chup"), (False, f"/api/crm/du-an-ban/{DB}"),
                        (False, f"/api/crm/du-an-ban/{DB}/lich-su"), *((True, "/api/crm/" + k) for k in CG.TRUONG_DA)):
            self.assertTrue(CG.la_route(post, p), p)
        self.assertFalse(CG.la_route(True, "/api/crm/mau"))  # handler #6 cũ giữ nguyên
        self.assertFalse(CG._la_route_da("/api/crm/du-an-ban-x"))
        for k in CG.TRUONG_DA.values():
            self.assertFalse(k & CG.KHONG_NHAN)

    def test_get(self):
        h, da = self.goi(False, "/api/crm/du-an-ban", query={"dang_ban": ["1"]}, raw="/api/crm/du-an-ban?dang_ban=1")
        self.assertEqual((h.st, da.goi[0][0], da.goi[0][2]), (200, "danh_sach", {"dang_ban": True}))
        h, da = self.goi(False, "/api/crm/du-an-ban")
        self.assertEqual(da.goi[0][2], {"dang_ban": False})
        h, da = self.goi(False, "/api/crm/du-an-ban/anh-chup", query={"du_an_id": [DA], "ngay": ["2026-10-25"]},
                         raw=f"/api/crm/du-an-ban/anh-chup?du_an_id={DA}&ngay=2026-10-25")
        self.assertEqual((h.st, da.goi[0][0], da.goi[0][1]), (200, "anh_chup_mac_dinh", (ME, DA, "2026-10-25")))
        h, da = self.goi(False, f"/api/crm/du-an-ban/{DB}", query={"phien_ban": ["2"]}, raw=f"/api/crm/du-an-ban/{DB}?phien_ban=2")
        self.assertEqual((da.goi[0][0], da.goi[0][1], da.goi[0][2]), ("chi_tiet", (ME, DB), {"phien_ban": "2", "ngay": None}))
        h, da = self.goi(False, f"/api/crm/du-an-ban/{DB}/lich-su")
        self.assertEqual((h.st, da.goi[0][0]), (200, "lich_su"))

    def test_query_la_va_sai(self):
        for path, q, raw in (("/api/crm/du-an-ban", {"x": ["1"]}, "/api/crm/du-an-ban?x=1"),
                             ("/api/crm/du-an-ban", {}, "/api/crm/du-an-ban?phap_nhan_id"),
                             ("/api/crm/du-an-ban", {"dang_ban": ["2"]}, "/api/crm/du-an-ban?dang_ban=2"),
                             (f"/api/crm/du-an-ban/{DB}/lich-su", {"ngay": ["2026-10-25"]}, f"/api/crm/du-an-ban/{DB}/lich-su?ngay=2026-10-25")):
            h, da = self.goi(False, path, query=q, raw=raw)
            self.assertEqual((h.st, h.data["error"], da.goi), (400, "CRM_G_YEU_CAU_SAI", []), raw)
        h, da = self.goi(True, "/api/crm/du-an-ban/bat-ban", {"du_an_id": DA, "khoa": "k"}, raw="/api/crm/du-an-ban/bat-ban?x=1")
        self.assertEqual((h.st, da.goi), (400, []))

    def test_post_than(self):
        h, da = self.goi(True, "/api/crm/du-an-ban/bat-ban", {"du_an_id": DA, "thong_tin": tt(), "phi": PHI, "khoa": "k"})
        self.assertEqual((h.st, da.goi[0][0], da.goi[0][2]["du_an_id"], da.goi[0][2]["khoa"]), (200, "bat_ban", DA, "k"))
        for body, st, ma in (({"du_an_id": DA, "phap_nhan_id": "x", "khoa": "k"}, 403, "CRM_G_CLIENT_AUTHORITY"),
                             ({"du_an_id": DA, "trang_thai": "DANG_BAN", "khoa": "k"}, 403, "CRM_G_CLIENT_AUTHORITY"),
                             ({"du_an_id": DA, "phien_ban_id": "x", "khoa": "k"}, 400, "CRM_G_YEU_CAU_SAI"),
                             ([1, 2], 400, "CRM_G_YEU_CAU_SAI")):
            h, da = self.goi(True, "/api/crm/du-an-ban/bat-ban", body)
            self.assertEqual((h.st, h.data["error"], da.goi), (st, ma, []), body)
        h, da = self.goi(True, "/api/crm/du-an-ban/tien-do", {"du_an_id": DA, "expected_version": 3, "giai_doan": "GD1", "dong": [], "khoa": "k"})
        self.assertEqual((da.goi[0][0], da.goi[0][2]["giai_doan"], da.goi[0][2]["expected_version"]), ("ap_dung_tien_do", "GD1", 3))
        for ten, ham in (("cap-nhat", "cap_nhat"), ("phi", "sua_phi"), ("lo", "ghi_lo"), ("ngung-ban", "ngung_ban"), ("mo-ban-lai", "mo_ban_lai")):
            body = {k: None for k in CG.TRUONG_DA["du-an-ban/" + ten]}
            h, da = self.goi(True, "/api/crm/du-an-ban/" + ten, body)
            self.assertEqual((h.st, da.goi[0][0]), (200, ham))
        h, _ = self.goi(True, "/api/crm/du-an-ban/xoa", {"da_ban_id": DB})
        self.assertEqual(h.st, 404)

    def test_thue_va_dat_loi_400_theo_truong(self):
        for endpoint, id_ in (("bat-ban", {"du_an_id": DA}), ("cap-nhat", {"da_ban_id": DB, "expected_phien_ban": 1})):
            for sua, truong in (({"thue_suat": "7"}, "thue_suat"), ({"thue_suat": 10}, "thue_suat"),
                                ({"gia_dat_tru": "121"}, "gia_dat_tru"), ({"gia_dat_tru": "٢٤"}, "gia_dat_tru"),
                                ({"co_so_thue": "NET"}, "co_so_thue"), ({"vat_phan_tram": "10"}, "vat_phan_tram")):
                with self.subTest(endpoint=endpoint, sua=sua):
                    h, da = self.goi(True, "/api/crm/du-an-ban/" + endpoint, {**id_, "thong_tin": tt(**sua), "khoa": "k"})
                    self.assertEqual((h.st, h.data["truong"], da.goi), (400, "thong_tin." + truong, []))
        h, da = self.goi(True, "/api/crm/du-an-ban/bat-ban", {"du_an_id": DA, "thong_tin": {"loai_hinh_id": LH, "tien_te": "USD"}, "khoa": "k"})
        self.assertEqual((h.st, da.goi[0][2]["thong_tin"]["thue_suat"], da.goi[0][2]["thong_tin"]["gia_dat_tru"]), (200, "10", "0"))

    def test_query_tho_lap_rong_va_gioi_han(self):
        from urllib.parse import parse_qs

        ds = (("/api/crm/du-an-ban", "dang_ban=1&dang_ban="),
              ("/api/crm/du-an-ban", "dang_ban=&dang_ban=1"),
              ("/api/crm/du-an-ban", "dang_ban=1&dang_ban=1"),
              ("/api/crm/du-an-ban", "dang_ban="),
              ("/api/crm/du-an-ban", "dang_ban"),
              (f"/api/crm/du-an-ban/{DB}", "phien_ban=" + "0" * 1000 + "1"),
              (f"/api/crm/du-an-ban/{DB}", "phien_ban=0000000001"),
              (f"/api/crm/du-an-ban/{DB}", "phien_ban=0"),
              (f"/api/crm/du-an-ban/{DB}", "phien_ban=١"),
              (f"/api/crm/du-an-ban/{DB}", "phien_ban="),
              (f"/api/crm/du-an-ban/{DB}", "phien_ban=1&phien_ban="),
              (f"/api/crm/du-an-ban/{DB}", "ngay="),
              (f"/api/crm/du-an-ban/{DB}", "ngay=2026-10-25&ngay="),
              (f"/api/crm/du-an-ban/{DB}", "ngay=02026-10-25"),
              ("/api/crm/du-an-ban/anh-chup", "du_an_id="),
              ("/api/crm/du-an-ban/anh-chup", "du_an_id=" + DA.replace("-", "")),
              ("/api/crm/du-an-ban/anh-chup", "du_an_id=" + DA + "0"),
              ("/api/crm/du-an-ban/anh-chup", "du_an_id=" + DA + "&du_an_id="))
        for path, tho in ds:
            with self.subTest(query=tho[:80]):
                # Parser ngoài bỏ giá trị rỗng như server thật; route vẫn phải từ chối dựa trên query thô.
                h, da = self.goi(False, path, query=parse_qs(tho), raw=path + "?" + tho)
                self.assertEqual((h.st, h.data["error"], da.goi), (400, "CRM_G_YEU_CAU_SAI", []))
        for value in ("1", "000000001", "999999999"):
            h, _ = self.goi(False, f"/api/crm/du-an-ban/{DB}", query={"phien_ban": [value]}, raw=f"/api/crm/du-an-ban/{DB}?phien_ban={value}")
            self.assertEqual(h.st, 200)

    def test_tien_do_hai_nguoi_cung_ban_cu_tra_409(self):
        m = _Mau()
        da = D.CrmDuAnBanK2(m)
        hien_tai, actors = [1], []

        def lenh(dt, sql, p):
            actors.append(dt["dang_nhap"])
            if p[5] != hien_tai[0]:
                raise DataError("CRM_DA_PHIEN_BAN_CU", "Tiến độ đã đổi.")
            hien_tai[0] += 1
            return {"phien_ban": hien_tai[0]}

        body = {"du_an_id": DA, "expected_version": 1, "giai_doan": "GD1", "khoa": "bh",
                "dong": [{"lan": "1", "gia_tri_loai": "PERCENT", "gia_tri_thap_phan": "100", "moc_loai": "SU_KIEN", "moc_su_kien": "KY_HD"}]}
        with patch.object(m, "_lenh", side_effect=lenh), patch.object(_App, "crm_phien", side_effect=[("sid", ME, False), ("sid", "MO_PHONG_KT_A", False)]):
            h1, _ = self.goi(True, "/api/crm/du-an-ban/tien-do", body, da=da)
            h2, _ = self.goi(True, "/api/crm/du-an-ban/tien-do", {**body, "khoa": "kt"}, da=da)
        self.assertEqual((h1.st, h1.data["phien_ban"], h2.st, h2.data["error"], hien_tai[0]), (200, 2, 409, "CRM_DA_PHIEN_BAN_CU", 2))
        self.assertEqual(actors, [ME, "MO_PHONG_KT_A"])
        for expected in (None, True, -1, "1"):
            h, _ = self.goi(True, "/api/crm/du-an-ban/tien-do", {**body, "expected_version": expected}, da=da)
            self.assertEqual((h.st, h.data["truong"]), (400, "expected_version"))

    def test_ma_loi(self):
        for ma, st in (("CRM_DA_PHIEN_BAN_CU", 409), ("CRM_DA_DA_CO", 409), ("CRM_DA_LO_LAN_CU", 409), ("CRM_DA_TRANG_THAI", 409),
                       ("CRM_DA_CHUA_BAT_BAN", 409), ("CRM_G_IDEMPOTENCY_KHAC", 409), ("CRM_G_HIEU_LUC_CHONG", 409), ("CRM_G_KHONG_THAY", 404),
                       ("CRM_G_KHONG_CO_QUYEN", 403), ("CRM_G_CHI_MAY_CHU", 403), ("CRM_G_CHUA_SAN_SANG", 503), ("CRM_DA_SO_SAI", 400),
                       ("CRM_DA_LOAI_HINH_SAI", 400), ("CRM_G_CHUAN_SAI", 400), ("CSDL_TU_CHOI", 400)):
            h, _ = self.goi(True, "/api/crm/du-an-ban/ngung-ban", {"da_ban_id": DB, "khoa": "k"}, da=_Da(DataError(ma, "x")))
            self.assertEqual((h.st, h.data["error"]), (st, ma))
            self.assertNotIn("truong", h.data)
        h, _ = self.goi(True, "/api/crm/du-an-ban/phi", {"da_ban_id": DB, "khoa": "k"}, da=_Da(DataError("CRM_DA_SO_SAI", "x", "phi.0.muc")))
        self.assertEqual((h.st, h.data["truong"]), (400, "phi.0.muc"))
        h, _ = self.goi(False, "/api/crm/du-an-ban", da=_Da(TypeError("x")))
        self.assertEqual((h.st, h.data["error"]), (400, "INVALID_REQUEST"))

    def test_route_g_cu_khong_doi(self):
        self.assertTrue(CG.la_route(True, "/api/crm/bo-chuan/lap"))
        self.assertEqual(set(CG.TRUONG), {"mau/anh-xa", "mau/gui-kiem", "mau/kiem", "mau/tra-lai", "mau/duyet", "mau/tu-choi", "mau/xem-thu",
                                          "bo-chuan/lap", "bo-chuan/gui-duyet", "bo-chuan/duyet"})
        src = (SRC / "giao_dien" / "crm_g.py").read_text(encoding="utf-8")
        dh = src[src.index("def dieu_huong("):src.index("    try:", src.index("def dieu_huong("))]
        self.assertIn("return _dieu_huong_da(h, app, post, path, query)", dh)  # nhánh DA chỉ khi _la_route_da (khớp tiền tố riêng)

    def test_factory_dung_service_g(self):
        class _AppF:
            def __init__(self):
                self.mutation_lock = threading.Lock()
        app, g = _AppF(), object()
        app.__dict__["_crm_g"] = g
        with patch.object(CG, "dich_vu", lambda a: a.__dict__["_crm_g"]):
            a, b = CG.dich_vu_da(app), CG.dich_vu_da(app)
        self.assertIs(a, b)
        self.assertIs(a.mau, g)


# ================================================================================================== 5. seed DEMO + tool chuẩn bị
class SeedDemo(unittest.TestCase):
    def test_literal_seed(self):
        self.assertTrue(D.SEED_NGUOI.startswith("MO_PHONG_"))
        self.assertEqual(len(D.SEED_DU_AN), 2)
        for x in D.SEED_DU_AN:
            with self.subTest(du_an=x["du_an"]):
                self.assertIn("DEMO", x["du_an"])
                self.assertIn("DEMO", x["thong_tin"]["mo_ta"])
                tt_ = D.chuan_hoa_thong_tin({**x["thong_tin"], "loai_hinh_id": LH})
                self.assertIsNotNone(tt_["don_gia_niem_yet"])
                self.assertEqual(tt_["thue_suat"], "10")
                self.assertEqual(tt_["gia_dat_tru"], "24" if x["du_an"] == "DA_KCN_DEMO" else "0")
                ph = D.chuan_hoa_phi(x["phi"])
                self.assertGreaterEqual(len(ph), 2)
                self.assertGreaterEqual(len({p["don_vi_tinh"] for p in ph}), 2)  # ≥ 2 phí khác đơn vị tính
                self.assertTrue(all("DEMO" in p["ten"] for p in ph))
                lo = D.chuan_hoa_lo(x["lo"])
                self.assertGreaterEqual(len(lo), 2)
                self.assertTrue(all("DEMO" in z["ma"] for z in lo))
                dong = D._dong_g7_demo(x["g7"])
                self.assertEqual(sum(int(r["gia_tri_thap_phan"]) for r in dong), 100)
                for r in dong:
                    self.assertEqual(GK.nhan_moc_su_kien(r["moc_su_kien"]) != "Sự kiện khác (chưa có nhãn)", True)
        self.assertEqual({p["tien_te"] for x in D.SEED_DU_AN for p in x["phi"]}, {"USD", "VND"})

    def test_khoi_tao_demo_chua_san_sang_khong_raise(self):
        class _Tx:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        class _A:
            def transaction(self):
                return _Tx()

            def execute(self, sql, params=()):
                class _R:
                    def fetchone(self_):
                        return (False,)
                return _R()
        kq = D.khoi_tao_demo(_A())
        self.assertEqual(kq["trang_thai"], "CHUA_SAN_SANG")

    def _tool(self):
        spec = importlib.util.spec_from_file_location("chuan_bi_crm_demo_da1", GOC / "tools" / "chuan_bi_crm_demo.py")
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        return tool

    def test_tool_chi_seed_sau_khi_migrate_va_khong_nem_loi(self):
        tool = self._tool()
        goi = []
        with patch.object(tool, "chuan_bi", lambda kn: {"trang_thai": "SAN_SANG"}), patch.object(tool, "bo_sung_duyet_vien_m4", lambda kn: {}), \
                patch.object(tool, "bo_sung_du_an_ban", lambda kn: goi.append(1) or {"trang_thai": "DU"}):
            self.assertEqual(tool.chuan_bi_day_du({})["du_an_ban_seed"]["trang_thai"], "BO_QUA")
            self.assertEqual(goi, [])
        with patch.object(tool, "chuan_bi", lambda kn: {"trang_thai": "SAN_SANG", "schema_sau": PM.PG_SCHEMA_VERSION}), \
                patch.object(tool, "bo_sung_duyet_vien_m4", lambda kn: {}), patch.object(tool, "bo_sung_du_an_ban", lambda kn: goi.append(1) or {"trang_thai": "DU"}):
            self.assertEqual(tool.chuan_bi_day_du({})["du_an_ban_seed"], {"trang_thai": "DU"})
            self.assertEqual(goi, [1])
        self.assertEqual(tool.bo_sung_du_an_ban({"admin_dsn": None})["trang_thai"], "BO_QUA")
        kq = tool.bo_sung_du_an_ban({"admin_dsn": "host=10.0.0.1 port=5432 dbname=khac user=x"})  # không loopback/không DEMO → từ chối, không kết nối
        self.assertEqual(kq["trang_thai"], "LOI")
        self.assertNotIn("10.0.0.1", json.dumps(kq, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
