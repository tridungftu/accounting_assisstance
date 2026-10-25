"""CRM_G6A_M25_REGISTRATION — tích hợp G6A thành migration 25 (CODE_ONLY: coder viết, CHƯA CHẠY — WRITTEN_NOT_RUN).

Hai tầng:
  1. Thuần (không CSDL): toàn bộ 972.163 byte đầu ``pg_migrations.py`` = baseline 24 Root đã chốt (SHA trong handoff
     GIAO-CODE-CRM-G6A-M25-REGISTRATION §2, không lấy từ code); đoạn M0025 chỉ gồm import + alias + MỘT tuple đăng ký, cho phép append sau đó; registry baseline 1–24
     dựng lại TỪ CHÍNH prefix gốc (exec độc lập) khớp từng câu/checksum với registry mới; M24 ở index 23 nguyên object/checksum; G6A ở index 24
     đúng MỘT lần, cùng object ``CRM_G6A_SQL``; module SQL nguyên byte, không import registry; không bản sao SQL; thân ``kho.viec_chu_so_huu``
     của G6A = thân hiện hành 1–24 + đúng MỘT nhánh typed G6A (giữ legacy/CRM-G/M4); G5 VAN_HANH vẫn HOLD, registry không có producer.
  2. PG thật CHỈ trên bản sao DEMO SỞ HỮU schema tối thiểu 25 do Root cấp, qua cổng ``test_crm_kiem_hd.cong_clone`` (owner DSN + DSN login ứng dụng
     thường, provenance OWNED_DEMO_CLONE, lịch sử registry hiện hành + checksum, marker DEMO, quyền hiện hành). Thiếu/thiếu một phần → FAIL ``NOT_VERIFIED``
     (không skip, không coi là đạt). Không tạo DB/vai/mã/đối tác, không SET ROLE, không seed/bootstrap/M9. Ca K5 dương cần hàng G6A typed
     ĐÃ CÓ do luồng domain thật tạo (tests/test_crm_kiem_hd_http.py n00–n06) — không có → NOT_VERIFIED, không đếm 0 rồi gọi dương.
     Ghi duy nhất được commit: thu hồi + cấp lại phạm vi kiểm (vai quản trị, như n05 của test HTTP) khi ``KTT_G6A_CLONE_CHO_GHI=1``; các lệnh
     lưu kiểm đều trong giao dịch hoàn tác.

Không có gì ở đây là nghiệm thu CRM đầy đủ: G5 vận hành (chưa có producer) / Word / G3 PDF / GUI vẫn OPEN; SYNTHETIC_FIXTURE chỉ là fixture.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import unittest
import uuid
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

import test_crm_kiem_hd as TK  # chỉ mượn cổng/hằng (không đưa lớp TestCase của file đó vào module này)

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.k2 import crm_kiem_hd as KH
from kho_tri_thuc.k2 import sql_crm_kiem_hd as SK
from kho_tri_thuc.k2.crm_mau import _h
from kho_tri_thuc.m4 import sql_duyet as SD

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "src" / "kho_tri_thuc"
PG_PY = SRC / "ha_tang" / "pg_migrations.py"
SQL_PY = SRC / "k2" / "sql_crm_kiem_hd.py"

# handoff GIAO-CODE-CRM-G6A-M25-REGISTRATION §2 (Root pin — không tính lại từ code)
PREFIX_BYTES, PREFIX_SHA256 = 972_163, "3290720ce48f716977030e757060b0c7859456a26899f3aab44dc0854fc0d49b"  # toàn pg_migrations.py baseline 24
SQL_BYTES, SQL_SHA256 = 137_971, "119cd881ea1238bd942537701b513497dd20c666e5f914248f6b6304712f33d1"  # k2/sql_crm_kiem_hd.py
DONG_NOI = ("from ..k2.sql_crm_kiem_hd import CRM_G6A_SQL  # noqa: E402 — module chỉ hằng SQL, không import ha_tang",
            "M0025_CRM_G6A = CRM_G6A_SQL",
            "PG_MIGRATIONS = (*PG_MIGRATIONS, M0025_CRM_G6A)",
            "PG_SCHEMA_VERSION = len(PG_MIGRATIONS)")
VIEC_FN = "FUNCTION kho.viec_chu_so_huu()"
KT, CFO, TAI, CFO_B = "MO_PHONG_CRM_G_KT_A", "MO_PHONG_CRM_G_CFO_A", "MO_PHONG_CRM_G_TAI_A", "MO_PHONG_CRM_G_CFO_B"
CAP_BOI = "TEST:CRM-G6A-M25"


def _baseline24() -> dict:
    """Registry baseline dựng lại từ CHÍNH 972.163 byte gốc (exec trong namespace riêng) — không dùng giá trị của registry mới."""
    raw = PG_PY.read_bytes()[:PREFIX_BYTES]
    ns = {"__name__": "kho_tri_thuc.ha_tang._pg_baseline24", "__package__": "kho_tri_thuc.ha_tang", "__file__": str(PG_PY)}
    exec(compile(raw, str(PG_PY) + ":baseline24", "exec"), ns)  # noqa: S102 — mã nguồn của chính repo, không nhận đầu vào ngoài
    return ns


def _ham(stmts, ten: str) -> str:
    ds = [s for s in stmts if re.search(r"CREATE OR REPLACE FUNCTION " + re.escape(ten) + r"\(", s)]
    assert len(ds) == 1, ten
    return ds[0]


# ================================================================================================== 1. thuần
class M25Prefix(unittest.TestCase):
    def test_prefix_baseline24_nguyen_byte(self):
        raw = PG_PY.read_bytes()
        self.assertGreater(len(raw), PREFIX_BYTES)
        self.assertEqual(hashlib.sha256(raw[:PREFIX_BYTES]).hexdigest(), PREFIX_SHA256, "prefix baseline 24 bị sửa — chỉ được APPEND")
        truoc = raw[:PREFIX_BYTES].decode("utf-8")
        self.assertTrue(truoc.rstrip().endswith("PG_MIGRATIONS = (*PG_MIGRATIONS, M0024_M4_DUYET)\nPG_SCHEMA_VERSION = len(PG_MIGRATIONS)"))
        self.assertNotIn("CRM_G6A_SQL", truoc)
        self.assertNotIn("M0025", truoc)

    def test_phan_noi_chi_import_alias_mot_dang_ky(self):
        duoi = PG_PY.read_bytes()[PREFIX_BYTES:].decode("utf-8")
        ma = tuple(x.rstrip() for x in duoi.splitlines() if x.strip() and not x.lstrip().startswith("#"))
        self.assertEqual(ma[:len(DONG_NOI)], DONG_NOI, "đoạn M0025 chỉ được import + alias + một tuple đăng ký")
        for dong in DONG_NOI[:3]:
            self.assertEqual(ma.count(dong), 1, dong)
        self.assertTrue(duoi.endswith("\n"))
        # Owner có thể append migration sau M0025; oracle SQL chỉ xét đoạn G6A.
        duoi = "\n".join(ma[:len(DONG_NOI)]) + "\n"
        self.assertNotRegex(duoi, r"(?i)\b(CREATE|ALTER|DROP|GRANT|REVOKE|INSERT|UPDATE)\s")  # không bản sao SQL
        self.assertNotRegex(duoi, r"(master|kho)\.crm_kiem_")  # không tên đối tượng SQL G6A nào ngoài hằng của module domain
        self.assertEqual(PG_PY.read_text(encoding="utf-8").count("import CRM_G6A_SQL"), 1)

    def test_module_sql_nguyen_byte_khong_import_registry(self):
        raw = SQL_PY.read_bytes()
        self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), (SQL_BYTES, SQL_SHA256), "module SQL G6A bị sửa")
        src = raw.decode("utf-8")
        self.assertIsNone(re.search(r"^\s*(from|import)\s[^\n]*(pg_migrations|ha_tang)", src, re.M))


class M25Registry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.B = _baseline24()

    def test_baseline_dung_lai_la_24(self):
        b = self.B["PG_MIGRATIONS"]
        self.assertEqual((len(b), self.B["PG_SCHEMA_VERSION"]), (24, 24))
        self.assertIs(b[23], SD.M0024_M4_DUYET)  # module hằng đã nạp: cùng object
        self.assertFalse(any("crm_kiem_" in s for m in b for s in m), "baseline 1–24 không được chứa đối tượng G6A")

    def test_prefix_1_24_tung_cau_va_checksum(self):
        b = self.B["PG_MIGRATIONS"]
        self.assertEqual(len(PM.PG_MIGRATIONS[:24]), 24)
        for i in range(24):
            self.assertEqual(tuple(PM.PG_MIGRATIONS[i]), tuple(b[i]), f"migration {i + 1} đổi câu lệnh")
            self.assertEqual(PM._hash(PM.PG_MIGRATIONS[i]), self.B["_hash"](b[i]), f"migration {i + 1} đổi checksum")
        self.assertEqual({v: x for v, x in PM.PG_MIGRATION_TUONG_THICH.items() if v <= 25},
                         self.B["PG_MIGRATION_TUONG_THICH"])  # không compatibility checksum mới trong prefix
        self.assertFalse({24, 25} & set(PM.PG_MIGRATION_TUONG_THICH))
        self.assertEqual(PM.PG_MIGRATIONS_LICH_SU_FULL_M9, self.B["PG_MIGRATIONS_LICH_SU_FULL_M9"])
        self.assertEqual(PM.LEGACY_FULL_M9_M0013_SHA256, self.B["LEGACY_FULL_M9_M0013_SHA256"])

    def test_m24_index23_nguyen(self):
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS) if tuple(m) == tuple(SD.M0024_M4_DUYET)], [23])
        self.assertIs(PM.PG_MIGRATIONS[23], SD.M0024_M4_DUYET)
        self.assertIs(PM.PG_MIGRATIONS[23], PM.M0024_M4_DUYET)
        self.assertEqual(PM._hash(PM.PG_MIGRATIONS[23]), self.B["_hash"](self.B["PG_MIGRATIONS"][23]))
        self.assertIs(PM.PG_MIGRATIONS[22], PM.M0023_CRM_KY)

    def test_version25_g6a_dung_mot_lan_cung_object(self):
        self.assertGreaterEqual(PM.PG_SCHEMA_VERSION, 25)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        self.assertEqual(TK.SCHEMA_DU_KIEN, 25)
        self.assertIs(PM.PG_MIGRATIONS[24], SK.CRM_G6A_SQL)
        self.assertIs(PM.M0025_CRM_G6A, SK.CRM_G6A_SQL)
        self.assertIs(PM.CRM_G6A_SQL, SK.CRM_G6A_SQL)
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS) if m is SK.CRM_G6A_SQL], [24])
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS) if tuple(m) == tuple(SK.CRM_G6A_SQL)], [24])
        self.assertEqual(SK.CRM_G6A_SQL[0], "SET LOCAL check_function_bodies = off")
        self.assertFalse(any("crm_kiem_" in s for m in PM.PG_MIGRATIONS[:24] for s in m))
        self.assertNotIn(PM.M0013, PM.PG_MIGRATIONS)  # full-M9 lịch sử vẫn ngoài chuỗi active

    def test_viec_chu_so_huu_giu_moi_nhanh(self):
        """Thân G6A = thân hiện hành cuối cùng trong 1–24 + đúng MỘT nhánh typed G6A (không ghi đè mù nhánh legacy/CRM-G/M4)."""
        cu = [s for m in self.B["PG_MIGRATIONS"] for s in m if VIEC_FN in s and "CREATE OR REPLACE" in s]
        self.assertTrue(cu)
        self.assertFalse(any(VIEC_FN in s for s in SD.M0024_M4_DUYET), "M24 định nghĩa lại viec_chu_so_huu — phải hợp nhất trước")
        moi = [s for s in SK.CRM_G6A_SQL if VIEC_FN in s and "CREATE OR REPLACE" in s]
        self.assertEqual(len(moi), 1)
        g = moi[0]
        i = g.index("            IF NEW.tham_chieu_bang IN " + SK._KIEM_TYPED + " THEN")
        j = g.index("            IF NEW.tham_chieu_bang NOT IN (", i)
        self.assertEqual(g[:i] + g[j:], cu[-1], "ngoài nhánh G6A, thân viec_chu_so_huu phải nguyên văn bản hiện hành 1–24")
        self.assertIn("kho.crm_kiem_chu_the(NEW.tham_chieu_bang, NEW.tham_chieu_id)", g[i:j])
        for nhanh in ("IF TG_OP = 'UPDATE' THEN", "IF NEW.tham_chieu_bang IN " + SK._G_TYPED + " THEN", "kho.crm_g_chu_the(",
                      "IF coalesce(NEW.module, 'M1') IN ('CRM','M9') THEN", "kho.kiem_chu_so_huu_noi_bo("):
            self.assertIn(nhanh, g)  # UPDATE bất biến / CRM-G typed / M4 & module khác qua nhánh ngoài allowlist / legacy resolver
        self.assertFalse(any(VIEC_FN in s and "TRIGGER" in s for s in SK.CRM_G6A_SQL))  # trigger cũ giữ nguyên, không gắn lại

    def test_g5_hold_va_quyen_hep(self):
        g5 = _ham(SK.CRM_G6A_SQL, "master.crm_kiem_g5_xet")
        self.assertIn("'UNREGISTERED_G5_PROOF'", g5)
        self.assertIn("'trang_thai', 'HOLD'", g5)
        txt = "\n".join(s for m in PM.PG_MIGRATIONS for s in m)
        self.assertNotRegex(txt, r"INSERT INTO master\.crm_kiem_g5_(nguon|ket_qua|chinh_sach)\b")  # registry không có producer G5
        self.assertNotIn("set_config('ktt.crm_kiem_g5'", txt)
        grants = re.findall(r"GRANT\s[^']*", "\n".join(SK.CRM_G6A_SQL))
        self.assertEqual(grants, ["GRANT EXECUTE ON FUNCTION master.crm_kiem_viec_doc_duoc(text, uuid, uuid) TO %I"])
        i_revoke = max(i for i, s in enumerate(SK.CRM_G6A_SQL) if "REVOKE EXECUTE ON FUNCTION" in s)
        self.assertEqual(i_revoke, len(SK.CRM_G6A_SQL) - 2)
        self.assertNotRegex("\n".join(SK.CRM_G6A_SQL), r"GRANT[^;']*PUBLIC")
        self.assertNotRegex("\n".join(SK.CRM_G6A_SQL), r"(?i)\bSET\s+ROLE\b|BYPASSRLS")


# ================================================================================================== 2. PG thật — bản sao DEMO sở hữu schema 25
class _HoanTac(Exception):
    """Ném trong giao dịch để hoàn tác ca dương lưu kiểm (không để lại hàng)."""


def _than_doc(stmt: str) -> str:
    """Thân $$…$$ của một CREATE FUNCTION trong hằng SQL — để so với prosrc đã triển khai."""
    return stmt.split("$$")[1]


class CrmG6aM25BanSao(unittest.TestCase):
    """Thứ tự n01…n07 trên MỘT bản sao. Bước thiếu cổng/dữ liệu → FAIL NOT_VERIFIED."""

    @classmethod
    def setUpClass(cls):
        cls.ctx, cls.ly_do = TK.cong_clone(can_ghi=True)
        if cls.ctx:
            cls.addClassCleanup(TK._dong, cls.ctx["owner"], cls.ctx["app"])

    def setUp(self):
        if not self.ctx:
            self.fail("NOT_VERIFIED: " + self.ly_do)
        self.o, self.a = self.ctx["owner"], self.ctx["app"]

    def nv(self, ly_do: str):
        self.fail("NOT_VERIFIED: " + ly_do)

    # ------------------------------------------------------------------ helpers
    def nguoi(self, login):
        r = self.o.execute("SELECT id::text FROM master.nguoi_dung WHERE dang_nhap = %s AND mo_phong AND trang_thai = 'HOAT_DONG'", (login,)).fetchone()
        return None if r is None else r[0]

    def dat_phien(self, conn, login):
        """GUC danh tính phiên giống CrmMau._tx (trong giao dịch đang mở). login None → không danh tính."""
        if login is None:
            return
        nid = self.nguoi(login)
        if nid is None:
            self.nv(f"thiếu người dùng DEMO {login}")
        conn.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true), "
                     "set_config('ktt.ngay_hieu_luc', %s, true)", (nid, login, _dt.date.today().isoformat()))

    def viec_thay(self, login, viec_id) -> int:
        with self.a.transaction():
            self.dat_phien(self.a, login)
            return self.a.execute("SELECT count(*) AS n FROM kho.viec_can_duyet WHERE id = %s", (viec_id,)).fetchone()["n"]

    def sql_loi(self, ma, sql, params, login=KT):
        with self.assertRaises(psycopg.Error) as cm:
            with self.o.transaction():
                self.dat_phien(self.o, login)
                self.o.execute(sql, params)
        self.assertIn(ma, str(cm.exception))

    def viec_g6a(self):
        """Việc K5 typed G6A ĐÃ CÓ (luồng domain thật) của KT với đúng MỘT phạm vi kiểm hiện hành trên bản ký đó."""
        r = self.o.execute("""SELECT v.id::text, v.phap_nhan_id::text, h.id::text, h.ky_id::text, pv.id::text, pv.phan_cong_id::text
                              FROM kho.viec_can_duyet v
                              JOIN master.crm_kiem_ho_so h ON v.tham_chieu_bang = 'master.crm_kiem_ho_so' AND v.tham_chieu_id = h.id
                              JOIN master.crm_kiem_pham_vi pv ON pv.ky_id = h.ky_id AND pv.thu_hoi_luc IS NULL
                              JOIN master.phan_cong_hanh_dong a ON a.id = pv.phan_cong_id AND a.thu_hoi_luc IS NULL
                              JOIN master.nguoi_dung n ON n.id = a.nguoi_dung_id AND n.dang_nhap = %s
                              WHERE (SELECT count(*) FROM master.crm_kiem_pham_vi x WHERE x.ky_id = h.ky_id AND x.thu_hoi_luc IS NULL) = 1
                              ORDER BY h.tao_luc, h.id LIMIT 1""", (KT,)).fetchone()
        if r is None:
            self.nv("bản sao chưa có việc K5 typed G6A (master.crm_kiem_ho_so) có phạm vi hiện hành của KT — chạy luồng domain thật "
                    "tests/test_crm_kiem_hd_http.py n00–n06 trước; không seed/forge hàng, không gọi đếm 0 là dương")
        return dict(zip(("viec", "pn", "ho_so", "ky", "pv", "pc"), r))

    def ma(self, pn, *, ngoai_pn=False, dieu_kien="j.valid_to IS NULL AND NOT j.dong", tru=()):
        """Mã Junsky CÓ SẴN của seed DEMO (chỉ đọc; không tạo)."""
        r = self.o.execute(f"""SELECT j.id::text, j.doi_tac_id::text FROM master.doi_tac_ma_junsky j
                               WHERE (CASE WHEN %s THEN j.phap_nhan_id <> %s::uuid ELSE j.phap_nhan_id = %s::uuid END) AND ({dieu_kien})
                                 AND NOT (j.doi_tac_id::text = ANY(%s::text[]))
                               ORDER BY j.object_id_junsky, j.id LIMIT 1""", (ngoai_pn, pn, pn, list(tru))).fetchone()
        return None if r is None else {"id": r[0], "doi_tac_id": r[1]}

    def lineage_g4(self, ky):
        """Bản ký G4 + revision đã ký + khách HĐ master — phải bất biến qua mọi lệnh kiểm."""
        return self.o.execute("""SELECT to_jsonb(k), to_jsonb(r), h.doi_tac_id::text, h.crm_giao_ket, r.du_lieu -> 'bao_gia' -> 'khach' ->> 'doi_tac_id'
                                 FROM master.crm_hd_ky k JOIN master.crm_hd_soan_rev r ON r.id = k.soan_rev_id
                                 JOIN master.hop_dong h ON h.id = k.hop_dong_id WHERE k.id = %s""", (ky,)).fetchone()

    def luu_sql(self, ky, rev, dt, mj):
        y = KH.chuan_hoa_luu(ky_id=ky, expected_revision=rev, checklist={k: "XAC_NHAN" for k in KH.CHECKLIST}, doi_tac_id=dt, ma_junsky_id=mj,
                             khoa="m25-" + uuid.uuid4().hex[:12])
        h = _h("CRM_KIEM_LUU", {k: v for k, v in y.items() if k != "khoa"})
        return ("SELECT master.crm_kiem_luu(%s, %s, %s::uuid, %s, %s::jsonb, %s::uuid, %s::uuid, %s::date, %s, %s, %s) AS r",
                (y["khoa"], h, y["ky_id"], y["expected_revision"], json.dumps(y["checklist"]), y["doi_tac_id"], y["ma_junsky_id"],
                 y["ngay_hieu_luc"], y["can_cu_ngay"], y["trich_dan_ngay"], y["ghi_chu"]))

    # ------------------------------------------------------------------ n01: provenance + lịch sử registry hiện hành + M24/G6A checksum, không compat
    def test_n01_lich_su_exact25(self):
        self.assertTrue(self.ctx["db"].startswith("kho_"), self.ctx["db"])
        self.assertTrue(self.ctx["bien_nhan"])
        ls = self.o.execute("SELECT version, checksum FROM master.schema_migrations ORDER BY version").fetchall()
        self.assertEqual([tuple(x) for x in ls], [(i + 1, PM._hash(m)) for i, m in enumerate(PM.PG_MIGRATIONS)])  # exact, không tiền thân
        self.assertEqual(ls[23][1], PM._hash(SD.M0024_M4_DUYET))
        self.assertEqual(ls[24][1], PM._hash(SK.CRM_G6A_SQL))
        mk = {k for (k,) in self.o.execute("SELECT key FROM master.he_thong WHERE key = ANY(%s)", (list(TK.MARKER_DEMO),)).fetchall()}
        self.assertEqual(mk, set(TK.MARKER_DEMO))

    # ------------------------------------------------------------------ n02: login ứng dụng thường (SCRAM, NOSUPER/NOBYPASS, không SET ROLE)
    def test_n02_vai_ung_dung_thuong(self):
        r = self.a.execute("""SELECT current_user AS u, session_user = current_user AS khong_set_role, r.rolsuper, r.rolbypassrls, r.rolcanlogin
                              FROM pg_roles r WHERE r.rolname = current_user""").fetchone()
        self.assertEqual((r["khong_set_role"], r["rolsuper"], r["rolbypassrls"], r["rolcanlogin"]), (True, False, False, True))
        chu = self.o.execute("SELECT current_user").fetchone()[0]
        self.assertNotIn(r["u"], (chu, "postgres"), "DSN ứng dụng không được là chủ bảng/login mặc định")
        self.assertNotIn(r["u"], TK.VAI_UNG_DUNG, "dùng login thành viên của vai ứng dụng, không đăng nhập thẳng bằng vai nhóm")
        try:
            with self.o.transaction():
                p = self.o.execute("SELECT rolpassword LIKE 'SCRAM-SHA-256$%%' FROM pg_authid WHERE rolname = %s", (r["u"],)).fetchone()
        except psycopg.errors.InsufficientPrivilege:
            self.nv("DSN chủ không đọc được pg_authid — chưa xác minh SCRAM của login ứng dụng (Root xác minh độc lập)")
        self.assertTrue(p and p[0], "login ứng dụng phải dùng mật khẩu SCRAM-SHA-256")

    # ------------------------------------------------------------------ n03: sau REVOKE toàn bộ: chỉ helper boolean được EXECUTE; không grant rộng
    def test_n03_quyen_hep_sau_revoke(self):
        h = self.a.execute("""SELECT p.prorettype = 'boolean'::regtype AS bool, p.prosecdef,
                                     has_function_privilege(current_user, p.oid, 'EXECUTE') AS duoc
                              FROM pg_proc p WHERE p.oid = 'master.crm_kiem_viec_doc_duoc(text, uuid, uuid)'::regprocedure""").fetchone()
        self.assertEqual((h["bool"], h["prosecdef"], h["duoc"]), (True, True, True))
        cong = self.o.execute("""SELECT p.oid::regprocedure::text FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                                 WHERE n.nspname IN ('master','kho') AND p.proname LIKE 'crm\\_kiem\\_%'
                                   AND EXISTS (SELECT 1 FROM aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a
                                               WHERE a.grantee = 0 AND a.privilege_type = 'EXECUTE')""").fetchall()
        self.assertEqual(cong, [], "hàm crm_kiem_* còn EXECUTE cho PUBLIC")
        nhan = {x for (x,) in self.o.execute("""SELECT g.rolname FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) a JOIN pg_roles g ON g.oid = a.grantee
                                                WHERE p.oid = 'master.crm_kiem_viec_doc_duoc(text, uuid, uuid)'::regprocedure
                                                  AND a.grantee <> p.proowner""").fetchall()}
        self.assertTrue(nhan and nhan <= set(TK.VAI_UNG_DUNG), nhan)  # chỉ vai ứng dụng CÓ SẴN
        for t in SK._KIEM_BANG_MOI:
            g = self.o.execute("""SELECT count(*) FROM pg_class c, aclexplode(coalesce(c.relacl, acldefault('r', c.relowner))) a
                                  WHERE c.oid = %s::regclass AND a.grantee <> c.relowner""", (f"master.{t}",)).fetchone()[0]
            self.assertEqual(g, 0, f"bảng {t} có grant ngoài chủ bảng")
            rls = self.o.execute("SELECT relrowsecurity FROM pg_class WHERE oid = %s::regclass", (f"master.{t}",)).fetchone()[0]
            self.assertTrue(rls, t)
        with self.assertRaises(psycopg.Error) as cm:
            with self.a.transaction():
                self.a.execute("SELECT master.crm_kiem_g5_xet(%s::uuid, 'VAN_HANH')", (str(uuid.uuid4()),))
        self.assertIn("permission denied", str(cm.exception))

    # ------------------------------------------------------------------ n04: thân viec_chu_so_huu triển khai = bản G6A (giữ legacy/CRM/M4)
    def test_n04_viec_chu_so_huu_trien_khai(self):
        src = self.o.execute("SELECT prosrc FROM pg_proc WHERE oid = 'kho.viec_chu_so_huu()'::regprocedure").fetchone()[0]
        g6a = [s for s in SK.CRM_G6A_SQL if VIEC_FN in s and "CREATE OR REPLACE" in s][0]
        self.assertEqual(src, _than_doc(g6a))
        tg = self.o.execute("""SELECT count(*) FROM pg_trigger WHERE tgrelid = 'kho.viec_can_duyet'::regclass AND tgname = 'viec_chu_so_huu'
                               AND NOT tgisinternal""").fetchone()[0]
        self.assertEqual(tg, 1)

    # ------------------------------------------------------------------ n05: K5 dương trên hàng typed CÓ DỮ LIỆU + wrongPN/không danh tính/thu hồi
    def test_n05_k5_doc_hang_g6a(self):
        v = self.viec_g6a()
        goc = self.o.execute("SELECT tham_chieu_bang, tham_chieu_id::text, phap_nhan_id::text FROM kho.viec_can_duyet WHERE id = %s",
                             (v["viec"],)).fetchone()
        self.assertEqual(tuple(goc), ("master.crm_kiem_ho_so", v["ho_so"], v["pn"]))
        with self.a.transaction():  # ca dương: login thường + danh tính KT có phân công + phạm vi hiện hành → thấy ĐÚNG hàng typed
            self.dat_phien(self.a, KT)
            r = self.a.execute("SELECT tham_chieu_bang, tham_chieu_id::text AS id, phap_nhan_id::text AS pn FROM kho.viec_can_duyet WHERE id = %s",
                               (v["viec"],)).fetchall()
            self.assertEqual([(x["tham_chieu_bang"], x["id"], x["pn"]) for x in r], [tuple(goc)])
            self.assertTrue(self.a.execute("SELECT master.crm_kiem_viec_doc_duoc('master.crm_kiem_ho_so', %s::uuid, %s::uuid) AS ok",
                                           (v["ho_so"], v["pn"])).fetchone()["ok"])
            pn_khac = self.a.execute("SELECT id::text AS id FROM master.phap_nhan WHERE id <> %s::uuid ORDER BY ma LIMIT 1", (v["pn"],)).fetchone()
            if pn_khac is None:
                self.nv("bản sao chỉ có một pháp nhân — không đo được wrongPN")
            self.assertFalse(self.a.execute("SELECT master.crm_kiem_viec_doc_duoc('master.crm_kiem_ho_so', %s::uuid, %s::uuid) AS ok",
                                            (v["ho_so"], pn_khac["id"])).fetchone()["ok"], "wrongPN phải bị chặn")
        self.assertEqual(self.viec_thay(None, v["viec"]), 0, "không danh tính phiên → không thấy")
        for login in (CFO_B, TAI, CFO):  # ngoài PN / cùng PN không phạm vi → không thấy
            if self.nguoi(login) is None:
                self.nv(f"thiếu người dùng DEMO {login}")
            self.assertEqual(self.viec_thay(login, v["viec"]), 0, login)
        # thu hồi phạm vi (vai quản trị, commit) → chặn; cấp lại hàng mới → thấy lại. Hàng cũ giữ dấu thu hồi làm bằng chứng.
        self.o.execute("UPDATE master.crm_kiem_pham_vi SET thu_hoi_luc = now(), thu_hoi_boi = %s, thu_hoi_ly_do = 'TEST M25 thu hồi' WHERE id = %s",
                       (CAP_BOI, v["pv"]))
        try:
            self.assertEqual(self.viec_thay(KT, v["viec"]), 0, "phạm vi đã thu hồi phải bị chặn")
        finally:
            self.o.execute("""INSERT INTO master.crm_kiem_pham_vi (phan_cong_id, phap_nhan_id, hop_dong_id, ky_id, du_an_id, cap_boi)
                              SELECT %s, k.phap_nhan_id, k.hop_dong_id, k.id, h.du_an_id, %s
                              FROM master.crm_hd_ky k JOIN master.hop_dong h ON h.id = k.hop_dong_id WHERE k.id = %s""", (v["pc"], CAP_BOI, v["ky"]))
        self.assertEqual(self.viec_thay(KT, v["viec"]), 1)

    # ------------------------------------------------------------------ n06: NULL-draft → mã CÓ SẴN đúng PN; sai PN/đóng/hết hiệu lực bị chặn; G4 bất biến
    def test_n06_anh_xa_khach_du_thao(self):
        r = self.o.execute("""SELECT h.ky_id::text, h.phap_nhan_id::text, h.revision, h.trang_thai
                              FROM master.crm_kiem_ho_so h JOIN master.crm_hd_ky k ON k.id = h.ky_id
                              JOIN master.crm_hd_soan_rev s ON s.id = k.soan_rev_id
                              JOIN master.crm_kiem_pham_vi pv ON pv.ky_id = h.ky_id AND pv.thu_hoi_luc IS NULL
                              JOIN master.phan_cong_hanh_dong a ON a.id = pv.phan_cong_id AND a.thu_hoi_luc IS NULL
                              JOIN master.nguoi_dung n ON n.id = a.nguoi_dung_id AND n.dang_nhap = %s
                              WHERE s.du_lieu -> 'bao_gia' -> 'khach' ->> 'doi_tac_id' IS NULL AND h.trang_thai IN ('DANG_KIEM','CHO_BO_SUNG')
                              ORDER BY h.tao_luc, h.id LIMIT 1""", (KT,)).fetchone()
        if r is None:
            self.nv("không có hồ sơ kiểm khách dự thảo (NULL) đang DANG_KIEM/CHO_BO_SUNG với phạm vi hiện hành của KT — chạy luồng domain thật "
                    "tests/test_crm_kiem_hd_http.py n00–n04 trên bản sao mới (trước n07); không seed/forge")
        ky, pn, rev, _ = r
        dung = self.ma(pn)
        sai_pn = self.ma(pn, ngoai_pn=True)
        dong = self.ma(pn, dieu_kien="j.dong")
        het = self.ma(pn, dieu_kien="j.valid_to IS NOT NULL AND NOT j.dong")
        if not (dung and sai_pn and (dong or het)):
            self.nv("seed DEMO thiếu mã Junsky cần cho ánh xạ (mã hiệu lực đúng PN, mã PN khác, mã đóng/hết hiệu lực) — không tự tạo mã")
        g4 = self.lineage_g4(ky)
        self.assertIsNone(g4[4], "bản ký G4 phải là khách dự thảo NULL")
        dem = self.o.execute("SELECT count(*) FROM master.crm_kiem_rev WHERE ky_id = %s", (ky,)).fetchone()[0]
        for ten, m in (("sai PN", sai_pn), ("đóng", dong), ("hết hiệu lực/thu hồi", het)):
            if m is None:
                continue
            with self.subTest(ma=ten):
                self.sql_loi("CRM_KIEM_JUNSKY_SAI", *self.luu_sql(ky, rev, m["doi_tac_id"], m["id"]))
        khac = self.ma(pn, tru=(dung["doi_tac_id"],))
        if khac:  # lệch cặp đối tác/mã cùng PN
            self.sql_loi("CRM_KIEM_JUNSKY_SAI", *self.luu_sql(ky, rev, khac["doi_tac_id"], dung["id"]))
        self.sql_loi("CRM_KIEM_JUNSKY_SAI", *self.luu_sql(ky, rev, dung["doi_tac_id"], str(uuid.uuid4())))  # UUID bịa không lách được
        with self.assertRaises(_HoanTac):  # ca dương: chọn mã CÓ SẴN đúng PN → revision mới đúng cặp; hoàn tác để không để lại hàng
            with self.o.transaction():
                self.dat_phien(self.o, KT)
                sql, p = self.luu_sql(ky, rev, dung["doi_tac_id"], dung["id"])
                kq = self.o.execute(sql, p).fetchone()[0]
                self.assertEqual((kq["lap_lai"], kq["ket_qua"]["revision"]), (False, rev + 1))
                x = self.o.execute("""SELECT de_xuat_doi_tac_id::text, de_xuat_ma_junsky_id::text, phap_nhan_id::text FROM master.crm_kiem_rev
                                      WHERE ky_id = %s AND revision = %s""", (ky, rev + 1)).fetchone()
                self.assertEqual(tuple(x), (dung["doi_tac_id"], dung["id"], pn))
                self.assertEqual(self.lineage_g4(ky), g4, "lưu kiểm không được ghi đè bản ký/HĐ G4")
                raise _HoanTac
        self.assertEqual(self.lineage_g4(ky), g4, "G4 signed lineage phải bất biến")
        self.assertEqual(self.o.execute("SELECT count(*) FROM master.crm_kiem_rev WHERE ky_id = %s", (ky,)).fetchone()[0], dem)

    # ------------------------------------------------------------------ n07: G5 VAN_HANH vẫn HOLD; HIEU_LUC hiện có chỉ là SYNTHETIC_FIXTURE
    def test_n07_g5_hold(self):
        v = self.viec_g6a()
        g = self.o.execute("SELECT master.crm_kiem_g5_xet(%s::uuid, 'VAN_HANH')", (v["ky"],)).fetchone()[0]
        self.assertEqual((g["trang_thai"], g["chan"]), ("HOLD", [{"ma": "UNREGISTERED_G5_PROOF"}]))
        nguon = self.o.execute("SELECT count(*) FROM master.crm_kiem_g5_nguon WHERE loai <> 'SYNTHETIC_FIXTURE' OR NOT phi_van_hanh").fetchone()[0]
        self.assertEqual(nguon, 0, "có nguồn G5 không phải fixture — producer vận hành chưa được đăng ký")
        hl = [x for (x,) in self.o.execute("SELECT DISTINCT g5_che_do FROM master.crm_kiem_hieu_luc").fetchall()]
        self.assertLessEqual(set(hl), {"SYNTHETIC_FIXTURE"}, "HIEU_LUC qua VAN_HANH khi G5 chưa có producer")


if __name__ == "__main__":
    unittest.main()
