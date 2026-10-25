"""MASTER-REUSE-02 — kiểm PostgreSQL THẬT cho nhận master dùng chung / gắn đối tác / căn cứ master-mapping (m4/sql_master_dung_chung.py).
CODE_ONLY: coder viết, CHƯA CHẠY (WRITTEN_NOT_RUN).

KHÔNG tạo CSDL/role, KHÔNG migrate/bootstrap/M9, KHÔNG SET ROLE, KHÔNG apply SQL: chạy DUY NHẤT trên một CLONE DEMO SỞ HỮU Root đã dựng (schema =
PG_SCHEMA_VERSION hiện hành của registry — không hardcode số) VÀ đã tự apply `M4_MASTER_DUNG_CHUNG_SQL` (từ M4-4/7 gói là M0028 trong registry: clone migrate bằng registry hiện hành đã có SQL này; ghim SHA/marker của Root bên dưới vẫn được đòi như trước). Env (không .env/var,
không hardcode/in DSN):
  KHO_M4_MC_CLONE_DSN         DSN chủ bảng (owner) — đường tin cậy của máy chủ
  KHO_M4_MC_CLONE_APP_DSN     login ứng dụng có sẵn (SCRAM, IN ROLE app_web, NOSUPERUSER, NOBYPASSRLS)
  KHO_M4_MC_CLONE_DB          tên CSDL clone mong đợi (bắt đầu 'kho_test_')
  KHO_M4_MC_CLONE_PROVENANCE  = master.he_thong['m4_mc_clone_provenance']
  KHO_M4_MC_SQL_SHA256        SHA-256 Root ghim của '\\n'.join(M4_MASTER_DUNG_CHUNG_SQL) (= master.he_thong['m4_mc_sql_sha256'] = định nghĩa hiện tại)
  KHO_M4_MC_CRM_G6A           (tùy chọn, chỉ G09) JSON {dang_nhap, ky_id, expected_revision, check_id, do_thi_sha256, hop_dong_id} của một lần kích hoạt
                              G6A Root chuẩn bị sẵn trên clone; vắng → G09 SkipTest NOT_READY.
Không env nào → SkipTest NOT_VERIFIED (KHÔNG phải PASS). Env dở / clone không chứng minh được → LoiThietLap TRƯỚC mọi ghi.

Nhãn đường ghi (không phải đường người dùng):
  FIXTURE_MASTER_SEED_OWNER   đối tác/mapping DEMO của lượt: owner INSERT-only đúng giao thức crm_demo (ghi_chu 'TEST_ONLY:M4_MC:<run>').
  NGUON_MASTER_ADMIN_OWNER    đóng mapping (UPDATE valid_to) bằng owner = đường quản trị master tin cậy; M4 không có lệnh này.
  SEAM_GIAO_DICH_GIU          giữ giao dịch lệnh gắn mở (svc._tx + gọi hàm lệnh) để dựng đúng thứ tự thắng khóa — cùng hàm/GUC như service.
Không DROP/DELETE/TRUNCATE, không dọn dẹp, không thu hồi quyền. Ca đồng thời chờ khóa thật qua pg_stat_activity (không sleep đoán).
Master CRM (XAY_DUNG có crm_giao_ket) lấy từ clone: DEMO có thể không có → từng trạng thái thiếu là subTest NOT_READY (không tự tạo master CRM).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path

try:
    import psycopg
    from psycopg import sql as S
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang.primitives import DataError
from tests.test_m4_02c_pg import A1, B1, XEM, LoiThietLap, _q1, chuan_bi_duyet_vien, dung_ho_so

ENV_CHU, ENV_APP, ENV_DB, ENV_NGUON, ENV_SQL = ("KHO_M4_MC_CLONE_DSN", "KHO_M4_MC_CLONE_APP_DSN", "KHO_M4_MC_CLONE_DB",
                                                "KHO_M4_MC_CLONE_PROVENANCE", "KHO_M4_MC_SQL_SHA256")
ENV = (ENV_CHU, ENV_APP, ENV_DB, ENV_NGUON, ENV_SQL)
ENV_G6A = "KHO_M4_MC_CRM_G6A"
KHOA_NGUON, KHOA_SQL = "m4_mc_clone_provenance", "m4_mc_sql_sha256"
TIEN_TO_DB = "kho_test_"
CO_ENV = any(os.environ.get(k) for k in ENV)
LY_DO_SKIP = "NOT_VERIFIED: chưa cấp clone DEMO sở hữu đã apply M4_MASTER_DUNG_CHUNG_SQL (KHO_M4_MC_CLONE_*) — test PG/HTTP không chạy, KHÔNG tính đạt"
CHO_KHOA_GIAY = 20


# ================================================================================================== cổng clone (dùng chung với test_m4_master_dung_chung_http)
def cau_hinh_clone() -> dict:
    gia_tri = {k: os.environ.get(k) or "" for k in ENV}
    thieu = [k for k, v in gia_tri.items() if not v]
    if thieu:
        raise LoiThietLap("SETUP_FAILURE: cấu hình clone dở dang — thiếu " + ", ".join(thieu))
    if psycopg is None:
        raise LoiThietLap("SETUP_FAILURE: thiếu driver psycopg")
    if not re.fullmatch(r"[0-9a-f]{64}", gia_tri[ENV_SQL]):
        raise LoiThietLap(f"SETUP_FAILURE: {ENV_SQL} phải là SHA-256 hex thường")
    return gia_tri


def sql_sha256() -> str:
    from kho_tri_thuc.m4.sql_master_dung_chung import M4_MASTER_DUNG_CHUNG_SQL
    return hashlib.sha256("\n".join(M4_MASTER_DUNG_CHUNG_SQL).encode("utf-8")).hexdigest()


def kiem_clone_mc(chu, web, cfg: dict) -> dict:
    """Cổng CHỈ ĐỌC trước mọi ghi (khung kiem_clone_request M4-04A). Sai → LoiThietLap (không chứa DSN)."""
    from kho_tri_thuc.ha_tang import pg_migrations as PGM
    from kho_tri_thuc.ha_tang import postgres as pg
    from kho_tri_thuc.k2 import crm_demo, m4_demo
    from kho_tri_thuc.m4 import sql_master_dung_chung as MC

    def sai(ly_do):
        raise LoiThietLap("SETUP_FAILURE: " + ly_do + " — không ghi gì; Root cấp clone DEMO sở hữu đúng lineage + SQL master dùng chung đã ghim")
    db = _q1(chu, "SELECT current_database()")
    if db != cfg[ENV_DB] or not str(db).startswith(TIEN_TO_DB):
        sai(f"CSDL owner không phải clone mong đợi (phải = {ENV_DB}, bắt đầu '{TIEN_TO_DB}')")
    if _q1(web, "SELECT current_database()") != db:
        sai("login ứng dụng không trỏ cùng CSDL clone")
    r = web.execute("""SELECT r.rolname, r.rolsuper, r.rolbypassrls, pg_has_role(current_user, 'app_web', 'MEMBER')
                       FROM pg_roles r WHERE r.rolname = current_user""").fetchone()
    vals = tuple(r.values()) if isinstance(r, dict) else tuple(r or ())
    if len(vals) != 4 or vals[1:] != (False, False, True):
        sai("login ứng dụng phải IN ROLE app_web, NOSUPERUSER, NOBYPASSRLS")
    if getattr(web.pgconn, "used_password", None) is not True:
        sai("login ứng dụng không xác thực bằng mật khẩu")
    try:
        scram = _q1(chu, "SELECT rolpassword LIKE 'SCRAM-SHA-256$%%' FROM pg_authid WHERE rolname = %s", (vals[0],))
    except psycopg.Error:
        raise LoiThietLap("NOT_VERIFIED: owner không đọc được pg_authid — không chứng minh được login ứng dụng dùng SCRAM; không ghi gì") from None
    if scram is not True:
        sai("mật khẩu login ứng dụng không phải SCRAM-SHA-256")
    try:
        version = pg.kiem_lineage_ung_dung(chu)
    except DataError as exc:
        sai(f"lineage không khớp ({exc.code})")
    if version != PGM.PG_SCHEMA_VERSION:
        sai("schema clone ≠ PG_SCHEMA_VERSION của registry hiện hành")
    for t in MC.BANG:
        if _q1(chu, f"SELECT to_regclass('m4.{t}') IS NOT NULL") is not True:
            sai(f"clone chưa có m4.{t} (Root chưa apply M4_MASTER_DUNG_CHUNG_SQL)")
    for f in MC.HAM_LENH + MC.HAM_DOC:
        if _q1(chu, "SELECT to_regprocedure(%s) IS NOT NULL", (f,)) is not True:
            sai(f"clone thiếu hàm {f}")
    if _q1(chu, "SELECT pg_has_role(current_user, c.relowner, 'MEMBER') FROM pg_class c WHERE c.oid = 'm4.master_can_cu'::regclass") is not True:
        sai("kết nối owner không sở hữu bảng căn cứ master (không phải đường tin cậy của máy chủ)")
    he = dict(chu.execute("SELECT key, value FROM master.he_thong WHERE key = ANY(%s)",
                          ([pg.APP_MARKER_KEY, crm_demo.MARKER, m4_demo.MARKER, KHOA_NGUON, KHOA_SQL],)).fetchall())
    ck = sql_sha256()
    if not (he.get(KHOA_SQL) == ck == cfg[ENV_SQL]):
        sai("SHA SQL master dùng chung trong clone ≠ định nghĩa hiện tại ≠ giá trị Root ghim")
    if he.get(pg.APP_MARKER_KEY) != pg.APP_MARKER_VALUE:
        sai("thiếu marker ứng dụng")
    if crm_demo.MARKER not in he or m4_demo.MARKER not in he:
        sai("thiếu marker seed CRM/M4 DEMO (clone phải dựng từ DEMO, test không seed)")
    if he.get(KHOA_NGUON) != cfg[ENV_NGUON]:
        sai(f"provenance clone ({KHOA_NGUON}) không khớp {ENV_NGUON}")
    if _q1(chu, r"SELECT count(*) FROM master.phap_nhan WHERE ma NOT LIKE 'PN\_DEMO\_%'") != 0:
        sai("có pháp nhân ngoài DEMO — có thể là CSDL thật")
    if _q1(chu, "SELECT count(*) FROM master.nguoi_dung WHERE NOT mo_phong") != 0:
        sai("có người dùng không mô phỏng — có thể là CSDL thật")
    return {"trang_thai": "CLONE_DEMO_DA_KIEM", "schema": version, "mc_sql_sha256": ck, "scram": True}


# ================================================================================================== fixture + tiện ích (dùng chung với HTTP)
def seed_doi_tac(chu, run_id: str, nhan: str, pn: str, *, so_mapping: int = 1, khoa: bool = False) -> dict:
    """FIXTURE_MASTER_SEED_OWNER: đối tác + mapping DEMO của lượt, INSERT-only cùng giao thức crm_demo (không sửa hàng có sẵn)."""
    ten = f"Đối tác DEMO M4-MC {run_id} {nhan}"
    dt = chu.execute("""INSERT INTO master.doi_tac (ten_phap_ly, ten_chuan_hoa, loai, vai_tro, ghi_chu)
                        VALUES (%s, master.chuan_hoa_ten(%s), 'TC', '{KH}', %s) RETURNING id""",
                     (ten, ten, f"TEST_ONLY:M4_MC:{run_id}:{nhan}")).fetchone()[0]
    mp = [chu.execute("""INSERT INTO master.doi_tac_ma_junsky (doi_tac_id, phap_nhan_id, object_id_junsky, ten_junsky, khoa)
                         VALUES (%s, %s, %s, %s, %s) RETURNING id""", (dt, pn, f"MC{run_id}{nhan}{i}".upper(), ten, khoa)).fetchone()[0]
          for i in range(so_mapping)]
    return {"doi_tac_id": str(dt), "mapping": [str(m) for m in mp], "ten": ten}


def dong_mapping(chu, mapping_id: str) -> None:
    """NGUON_MASTER_ADMIN_OWNER: đóng mapping (valid_to) — nguồn master đổi; observer M4 chạy trong chính giao dịch này."""
    chu.execute("UPDATE master.doi_tac_ma_junsky SET valid_to = now() WHERE id = %s", (mapping_id,))


def ma_loi(exc: BaseException) -> str:
    if isinstance(exc, DataError):
        return exc.code
    if psycopg is not None and isinstance(exc, psycopg.Error):
        p = (getattr(exc.diag, "message_primary", "") or "").split(":", 1)[0]
        return p if re.fullmatch(r"[A-Z][A-Z0-9_]*", p) else type(exc).__name__
    return type(exc).__name__


def chay_nen(fn) -> tuple[threading.Thread, dict]:
    out: dict = {}

    def chay():
        try:
            out["kq"] = fn()
        except BaseException as exc:  # noqa: BLE001 — chuyển về luồng test
            out["loi"] = exc
    t = threading.Thread(target=chay, daemon=True)
    t.start()
    return t, out


def cho_khoa(chu, conn) -> bool:
    """Chờ tới khi backend của `conn` thật sự chờ khóa hàng/giao dịch (pg_stat_activity), tối đa CHO_KHOA_GIAY."""
    pid = conn.info.backend_pid
    het = time.monotonic() + CHO_KHOA_GIAY
    while time.monotonic() < het:
        if _q1(chu, "SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s", (pid,)) == "Lock":
            return True
        time.sleep(0.05)
    return False


class _ChuaNop(Exception):
    pass


class _DungKhongNop:
    """Bọc service cho dung_ho_so (02C): sau tao_hop_dong gọi `sau_tao(hd)` (vd. gắn đối tác lúc nháp); `nop` bị chặn trước CSDL nếu chan_nop
    → hồ sơ ĐỦ căn cứ nhưng CHƯA nộp. Mọi lệnh khác đi thẳng service thật."""

    def __init__(self, svc, sau_tao=None, chan_nop=True):
        self._svc, self._sau_tao, self._chan = svc, sau_tao, chan_nop
        self.hd = self.dot = None

    def __getattr__(self, ten):
        return getattr(self._svc, ten)

    def tao_hop_dong(self, *a, **k):
        r = self._svc.tao_hop_dong(*a, **k)
        self.hd = r["hop_dong_id"]
        if self._sau_tao is not None:
            self._sau_tao(self.hd)
        return r

    def nop(self, *a, **k):
        self.dot = k.get("dot_id")
        if self._chan:
            raise _ChuaNop()
        return self._svc.nop(*a, **k)


@unittest.skipUnless(CO_ENV, LY_DO_SKIP)
class M4MasterDungChungPG(unittest.TestCase):
    """Chạy theo thứ tự g01…g13 trên MỘT clone; trạng thái qua cls.s."""

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        cfg = cau_hinh_clone()
        cls.cfg = cfg
        cls.admin = psycopg.connect(cfg[ENV_CHU], autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        web_raw = psycopg.connect(cfg[ENV_APP], autocommit=True)
        cls.addClassCleanup(web_raw.close)
        cls.gate = kiem_clone_mc(cls.admin, web_raw, cfg)  # CHỈ ĐỌC
        cls.goc = Path(tempfile.mkdtemp(prefix="ktt_m4_mc_pg_"))  # DataRoot DEMO của lượt — giữ lại
        cls.run_id = uuid.uuid4().hex[:8]
        cls.XayDungK2 = XayDungK2
        cls.trich6 = None
        cls.svc = cls._svc_moi()
        cls.du_an = str(_q1(cls.admin, "SELECT id FROM master.du_an WHERE ma_junsky = 'DA_XD_A1'"))
        cls.pn = str(_q1(cls.admin, "SELECT phap_nhan_id FROM master.du_an WHERE id = %s", (cls.du_an,)))
        cls.s = {}

    @classmethod
    def _svc_moi(cls):
        web = psycopg.connect(cls.cfg[ENV_APP], autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(web.close)
        chu = psycopg.connect(cls.cfg[ENV_CHU], autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(chu.close)
        return cls.XayDungK2(web, cls.goc / "m4-k2", conn_tin_cay=chu, trich6=cls.trich6)

    @classmethod
    def _chu_moi(cls):
        c = psycopg.connect(cls.cfg[ENV_CHU], autocommit=True)
        cls.addClassCleanup(c.close)
        return c

    # ------------------------------------------------------------------ helpers
    def K(self, ten):
        return f"m4mc-{self.run_id}-{ten}"

    def q(self, sql, params=()):
        return _q1(self.admin, sql, params)

    def loi(self, fn, *a, **k) -> str:
        try:
            fn(*a, **k)
        except (DataError, psycopg.Error) as exc:
            return ma_loi(exc)
        self.fail("thao tác không bị chặn")

    def can_cu(self, hd) -> list:
        return [dict(zip(("so", "nguon", "sha256", "revision_ho_so", "boi", "thieu_nguoi", "mapping_id", "ly_do", "meta"), r)) for r in self.admin.execute(
            """SELECT so, nguon, sha256, revision_ho_so, boi, thieu_nguoi, mapping_id::text, ly_do, meta FROM m4.master_can_cu
               WHERE hop_dong_id = %s ORDER BY so""", (hd,)).fetchall()]

    def rev(self, hd) -> tuple:
        return tuple(self.admin.execute("SELECT revision, rev_tham_so FROM m4.ho_so_hop_dong WHERE hop_dong_id = %s", (hd,)).fetchone())

    def doi_tac_master(self, hd):
        v = self.q("SELECT doi_tac_id FROM master.hop_dong WHERE id = %s", (hd,))
        return None if v is None else str(v)

    def dem(self, hd=None) -> dict:
        w, p = ("WHERE hop_dong_id = %s", (hd,)) if hd else ("", ())
        return {"ho_so": self.q(f"SELECT count(*) FROM m4.ho_so_hop_dong {w}", p), "can_cu": self.q(f"SELECT count(*) FROM m4.master_can_cu {w}", p),
                "lien_ket": self.q(f"SELECT count(*) FROM m4.master_can_cu_phien_ban {w}", p),
                "bien_nhan": self.q("SELECT count(*) FROM m4.bien_nhan"), "nhat_ky": self.q(f"SELECT count(*) FROM m4.nhat_ky {w}", p)}

    def dau_van_tay(self, hd) -> dict:
        """Hàng master + mọi hàng bảng NGOÀI m4 trỏ FK tới master.hop_dong(id) của HĐ — nhận master không được đổi gì ngoài m4."""
        out = {"master": self.q("SELECT md5(h::text) FROM master.hop_dong h WHERE h.id = %s", (hd,))}
        fks = self.admin.execute("""
            SELECT c.conrelid::regclass::text, a.attname
              FROM pg_constraint c JOIN pg_class r ON r.oid = c.conrelid JOIN pg_namespace n ON n.oid = r.relnamespace
             CROSS JOIN LATERAL unnest(c.conkey, c.confkey) AS k(col, fcol)
              JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.col
              JOIN pg_attribute fa ON fa.attrelid = c.confrelid AND fa.attnum = k.fcol
             WHERE c.contype = 'f' AND c.confrelid = 'master.hop_dong'::regclass AND fa.attname = 'id' AND n.nspname <> 'm4'
             ORDER BY 1, 2""").fetchall()
        for bang, cot in fks:
            q = S.SQL("SELECT md5(coalesce(string_agg(t::text, '|' ORDER BY t::text), '')) FROM {} t WHERE t.{} = %s").format(
                S.SQL(bang), S.Identifier(cot))  # bang = regclass::text (đã quote bởi PG)
            out[f"{bang}.{cot}"] = self.q(q, (hd,))
        return out

    def mc(self, hd, login=A1) -> dict:
        return self.svc.chi_tiet(login, hd)["master_can_cu"]

    def ho_so_moi(self, nhan) -> str:
        return self.svc.tao_hop_dong(A1, du_an_id=self.du_an, so_hop_dong=f"MC-{self.run_id}-{nhan}", ten=f"Hồ sơ MC DEMO {nhan}",
                                     khoa=self.K(f"{nhan}-hd"))["hop_dong_id"]

    def muc_doi_tac(self, d, login=A1, svc=None) -> dict:
        ds = (svc or self.svc).master_doi_tac(login, du_an_id=self.du_an, q=d["ten"][-30:], limit=50)["items"]
        return next(x for x in ds if str(x["doi_tac_id"]) == d["doi_tac_id"])

    def than_gan(self, hd, d, *, ly_do="Gắn đối tác theo hợp đồng ký (DEMO)", svc=None) -> dict:
        m = self.mc(hd) if svc is None else svc.chi_tiet(A1, hd)["master_can_cu"]
        x = self.muc_doi_tac(d, svc=svc)
        return dict(hop_dong_id=hd, doi_tac_id=d["doi_tac_id"], mapping_id=x["mapping_id"], revision=m["revision"],
                    expected_master=m["expected_master"], expected_mapping=x["expected_mapping"], ly_do=ly_do)

    def gan(self, hd, d, khoa, login=A1, svc=None, **thay) -> dict:
        return (svc or self.svc).gan_doi_tac_hop_dong(login, **{**self.than_gan(hd, d, svc=svc), **thay}, khoa=self.K(khoa))

    def dung_san_sang(self, nhan, *, gan_doi_tac=True, nop=False) -> dict:
        """Hồ sơ DEMO đủ căn cứ (dung_ho_so 02C); nếu gan_doi_tac: gắn đối tác fixture NGAY sau tạo (nháp, trước trích) → nộp không bị bump sau
        xác nhận. nop=False: chặn trước m4.nop → hồ sơ sẵn sàng nhưng chưa nộp."""
        if self.trich6 is None:
            import tests.test_m4_02b_k2 as K2B
            from tests.test_m4_02b_pure import _docx, openpyxl
            if not (K2B._nguon_da_nap() and openpyxl is not None and _docx is not None):
                self.skipTest("NOT_READY: lõi nguồn Review chưa nạp hoặc thiếu openpyxl/python-docx — không dựng được hồ sơ đủ căn cứ")
            type(self).trich6, type(self).gate6 = K2B.M4ChungTuPG._gate_trich6.__func__(type(self))
            type(self).svc = self._svc_moi()
            if "seed" not in self.s:
                self.s["seed"] = chuan_bi_duyet_vien(self.admin)
        d = seed_doi_tac(self.admin, self.run_id, nhan, self.pn) if gan_doi_tac else None
        px = _DungKhongNop(self.svc, (lambda hd: self.gan(hd, d, f"{nhan}-gan-dau")) if d else None, chan_nop=not nop)
        try:
            h = dung_ho_so(px, self.admin, self.K, nhan, self.run_id)
        except _ChuaNop:
            h = {"hd": px.hd, "dot": px.dot}
        return {**h, "hd": px.hd, "dot": h.get("dot") or px.dot, "doi_tac": d}

    def ung_vien_crm(self, trang_thai) -> str | None:
        """Master XAY_DUNG có sẵn trong clone (CRM/nguồn khác), đúng dự án, trạng thái cho trước, CHƯA có hồ sơ M4. Không có → None (NOT_READY)."""
        v = self.q("""SELECT h.id FROM master.hop_dong h WHERE h.du_an_id = %s AND h.loai = 'XAY_DUNG' AND h.trang_thai = %s
                         AND (h.crm_giao_ket IS NULL OR h.crm_giao_ket = h.trang_thai)
                         AND NOT EXISTS (SELECT 1 FROM m4.ho_so_hop_dong s WHERE s.hop_dong_id = h.id)
                       ORDER BY h.id LIMIT 1""", (self.du_an, trang_thai))
        return None if v is None else str(v)

    def expected_master(self, hd, login=A1) -> str:
        so = self.q("SELECT so_hop_dong FROM master.hop_dong WHERE id = %s", (hd,))
        ds = self.svc.master_hop_dong(login, du_an_id=self.du_an, q=so[:100], limit=50)["items"]
        return next(x for x in ds if str(x["hop_dong_id"]) == hd)["expected_master"]

    # ------------------------------------------------------------------ G01 nhận master 4 trạng thái, không đổi master/ngoài m4
    def test_g01_nhan_master_bon_trang_thai_giu_fingerprint(self):
        from kho_tri_thuc.m4.sql_master_dung_chung import TRANG_THAI_NHAN
        self.s["crm"] = {}
        for tt in TRANG_THAI_NHAN:
            with self.subTest(trang_thai=tt):
                hd = self.ung_vien_crm(tt)
                if hd is None:
                    self.skipTest(f"NOT_READY: clone không có master XAY_DUNG '{tt}' chưa nhận trong DA_XD_A1 (DEMO không seed master CRM)")
                fp, truoc = self.dau_van_tay(hd), self.dem()
                exp = self.expected_master(hd)
                r = self.svc.nhan_master_hop_dong(A1, du_an_id=self.du_an, hop_dong_id=hd, ten=f"Nhận {tt}", expected_master=exp,
                                                  khoa=self.K(f"g01-{tt}"))
                self.assertEqual((r["hop_dong_id"], r["da_co_san"], r["lap_lai"], r["revision"]), (hd, False, False, 1))
                self.assertEqual(self.dau_van_tay(hd), fp, "nhận master không được ghi master/bảng ngoài m4")
                cc = self.can_cu(hd)
                self.assertEqual([(c["so"], c["nguon"], c["revision_ho_so"]) for c in cc], [(1, "NHAN_MASTER_CO_SAN", 1)])
                self.assertEqual(cc[0]["sha256"], exp)
                sau = self.dem()
                self.assertEqual((sau["ho_so"] - truoc["ho_so"], sau["can_cu"] - truoc["can_cu"], sau["bien_nhan"] - truoc["bien_nhan"]), (1, 1, 1))
                lai = self.svc.nhan_master_hop_dong(A1, du_an_id=self.du_an, hop_dong_id=hd, ten=f"Nhận {tt}", expected_master=exp,
                                                    khoa=self.K(f"g01-{tt}"))
                self.assertEqual((lai["lap_lai"], lai["hop_dong_id"]), (True, hd))
                lan2 = self.svc.nhan_master_hop_dong(A1, du_an_id=self.du_an, hop_dong_id=hd, ten="Khác", expected_master=self.expected_master(hd),
                                                     khoa=self.K(f"g01-{tt}-2"))
                self.assertTrue(lan2["da_co_san"])
                self.assertEqual(self.dem()["can_cu"], sau["can_cu"], "nhận lần hai không thêm căn cứ")
                self.assertEqual(self.dau_van_tay(hd), fp)
                self.s["crm"][tt] = hd
        # HĐ M4 (tao_hop_dong) đã có hồ sơ: nhận lại → da_co_san, 0 hàng nghiệp vụ mới
        hd = self.ho_so_moi("g01-m4")
        truoc = self.dem(hd)
        r = self.svc.nhan_master_hop_dong(A1, du_an_id=self.du_an, hop_dong_id=hd, ten="Lại", expected_master=self.expected_master(hd),
                                          khoa=self.K("g01-m4-nhan"))
        self.assertTrue(r["da_co_san"])
        self.assertEqual({k: v for k, v in self.dem(hd).items() if k != "bien_nhan"}, {k: v for k, v in truoc.items() if k != "bien_nhan"})

    # ------------------------------------------------------------------ G02 từ chối HUY/loại/PN-dự án/quyền — 0 ghi
    def test_g02_tu_choi_huy_loai_pn_du_an_quyen_khong_ghi(self):
        hd_m4 = self.ho_so_moi("g02")
        exp = self.expected_master(hd_m4)
        ca = []
        huy = self.q("""SELECT h.id FROM master.hop_dong h WHERE h.du_an_id = %s AND h.loai = 'XAY_DUNG' AND h.trang_thai = 'HUY'
                          AND NOT EXISTS (SELECT 1 FROM m4.ho_so_hop_dong s WHERE s.hop_dong_id = h.id) LIMIT 1""", (self.du_an,))
        ca.append(("HUY", A1, self.du_an, huy and str(huy), "M4_MASTER_TRANG_THAI_KHONG_NHAN"))
        loai = self.q("SELECT h.id FROM master.hop_dong h WHERE h.du_an_id = %s AND h.loai <> 'XAY_DUNG' LIMIT 1", (self.du_an,))
        ca.append(("LOAI_KHAC", A1, self.du_an, loai and str(loai), "M4_MASTER_KHONG_THAY"))
        khac = self.q("SELECT h.id FROM master.hop_dong h WHERE h.du_an_id <> %s AND h.loai = 'XAY_DUNG' ORDER BY h.id LIMIT 1", (self.du_an,))
        ca.append(("DU_AN_KHAC", A1, self.du_an, khac and str(khac), "M4_MASTER_KHONG_THAY"))
        du_an_khac = self.q("SELECT h.du_an_id FROM master.hop_dong h WHERE h.id = %s", (khac,)) if khac else None
        ca.append(("KHONG_SOAN_DU_AN", A1, du_an_khac and str(du_an_khac), khac and str(khac), "M4_KHONG_CO_QUYEN_DU_AN"))
        ca.append(("XEM", XEM, self.du_an, hd_m4, "M4_KHONG_CO_QUYEN_DU_AN"))
        ca.append(("PN_KHAC", B1, self.du_an, hd_m4, "M4_KHONG_CO_QUYEN_DU_AN"))
        for nhan, login, du_an, hd, ma in ca:
            with self.subTest(ca=nhan):
                if hd is None or du_an is None:
                    self.skipTest(f"NOT_READY: clone không có master cho ca {nhan}")
                truoc, fp = self.dem(), self.dau_van_tay(hd)
                self.assertEqual(self.loi(self.svc.nhan_master_hop_dong, login, du_an_id=du_an, hop_dong_id=hd, ten="x", expected_master=exp,
                                          khoa=self.K(f"g02-{nhan}")), ma)
                self.assertEqual((self.dem(), self.dau_van_tay(hd)), (truoc, fp))
        with self.subTest(ca="EXPECTED_CU"):
            self.assertEqual(self.loi(self.svc.nhan_master_hop_dong, A1, du_an_id=self.du_an, hop_dong_id=hd_m4, ten="x", expected_master="0" * 64,
                                      khoa=self.K("g02-exp")), "M4_MASTER_DA_DOI")
        with self.subTest(ca="DTO"):
            for sai in ({"expected_master": "ABC"}, {"ten": ""}, {"hop_dong_id": "x"}):
                kw = dict(du_an_id=self.du_an, hop_dong_id=hd_m4, ten="x", expected_master=exp, khoa=self.K("g02-dto"), **sai)
                self.assertIn(self.loi(self.svc.nhan_master_hop_dong, A1, **kw), ("M4_THAM_SO_SAI", "M4_THIEU_THONG_TIN"))

    # ------------------------------------------------------------------ G03 người chỉ có M4 đọc được HĐ đã nhận, không mở rộng select master
    def test_g03_m4_only_doc_ho_so_da_nhan_khong_select_rong(self):
        hd = self.ho_so_moi("g03")
        x = self.mc(hd, XEM)
        self.assertIsNotNone(x)
        self.assertEqual(x["gan_doi_tac"], {"duoc": False, "ma": "M4_KHONG_CO_QUYEN_DU_AN"})
        dt = self.svc.danh_tinh(XEM)
        with self.svc._tx(dt):
            self.assertEqual(self.svc._mot("SELECT count(*) AS n FROM master.hop_dong WHERE id = %s::uuid", (hd,))["n"], 1)
            khong = self.svc._mot("""SELECT count(*) AS n FROM master.hop_dong h
                                     WHERE h.du_an_id = %s::uuid AND m4.mc_co_ho_so(h.id, h.du_an_id)
                                       AND NOT EXISTS (SELECT 1 FROM m4.ho_so_hop_dong s WHERE s.hop_dong_id = h.id)""", (self.du_an,))["n"]
            self.assertEqual(khong, 0, "policy mới không được cho thấy master không có hồ sơ M4")
        cho = self.q("""SELECT h.id FROM master.hop_dong h WHERE NOT EXISTS (SELECT 1 FROM m4.ho_so_hop_dong s WHERE s.hop_dong_id = h.id)
                        ORDER BY h.id LIMIT 1""")
        if cho is not None:
            du = self.q("SELECT du_an_id FROM master.hop_dong WHERE id = %s", (cho,))
            with self.svc._tx(dt):
                self.assertFalse(self.svc._mot("SELECT m4.mc_co_ho_so(%s::uuid, %s::uuid) AS r", (cho, du))["r"])
        self.assertEqual(self.loi(self.svc.master_hop_dong, XEM, du_an_id=self.du_an), "M4_KHONG_CO_QUYEN_DU_AN")
        self.assertEqual(self.loi(self.svc.master_doi_tac, XEM, du_an_id=self.du_an), "M4_KHONG_CO_QUYEN_DU_AN")
        self.assertIsNone(self._mc_hoac_none(hd, B1), "ngoài phạm vi: không thấy hồ sơ, không lộ căn cứ")

    def _mc_hoac_none(self, hd, login):
        try:
            return self.mc(hd, login)
        except DataError as exc:
            self.assertEqual(exc.code, "M4_KHONG_THAY_HOP_DONG")
            return None

    # ------------------------------------------------------------------ G04 tạo mới thiếu đối tác vẫn là nháp, HOLD hiển thị
    def test_g04_tao_moi_thieu_doi_tac_van_nhap(self):
        hd = self.ho_so_moi("g04")
        cc = self.can_cu(hd)
        self.assertEqual([(c["so"], c["nguon"], c["revision_ho_so"], c["mapping_id"]) for c in cc], [(1, "TAO_HO_SO_M4", 1, None)])
        self.assertEqual(cc[0]["boi"], A1)
        x = self.mc(hd)
        self.assertEqual((x["revision"], x["dong_bo"], x["gan_doi_tac"]["duoc"], x["master"]["mapping_trang_thai"]), (1, True, True, "KHONG_DOI_TAC"))
        self.assertIn("MAPPING_KHONG_DOI_TAC", x["hold"])
        self.assertEqual(x["expected_master"], cc[0]["sha256"])
        self.assertIsNone(self.doi_tac_master(hd))
        self.s["g04"] = hd

    # ------------------------------------------------------------------ G05 gắn đối tác: CAS, lý do, replay, quyền, HOLD mapping
    def test_g05_gan_doi_tac_cas_replay_quyen(self):
        hd = self.s.get("g04") or self.ho_so_moi("g05")
        d1, d2 = seed_doi_tac(self.admin, self.run_id, "g05a", self.pn), seed_doi_tac(self.admin, self.run_id, "g05b", self.pn)
        r0 = self.rev(hd)
        than = self.than_gan(hd, d1)
        self.assertIn(self.loi(self.svc.gan_doi_tac_hop_dong, A1, **{**than, "ly_do": "   "}, khoa=self.K("g05-ld")),
                      ("M4_LY_DO_BAT_BUOC", "M4_THIEU_THONG_TIN"))
        self.assertEqual(self.loi(self.svc.gan_doi_tac_hop_dong, XEM, **than, khoa=self.K("g05-xem")), "M4_KHONG_CO_QUYEN_DU_AN")
        self.assertEqual(self.loi(self.svc.gan_doi_tac_hop_dong, A1, **{**than, "revision": r0[0] + 5}, khoa=self.K("g05-rev")), "M4_REVISION_CU")
        self.assertEqual(self.loi(self.svc.gan_doi_tac_hop_dong, A1, **{**than, "expected_master": "f" * 64}, khoa=self.K("g05-em")), "M4_MASTER_DA_DOI")
        self.assertEqual(self.loi(self.svc.gan_doi_tac_hop_dong, A1, **{**than, "expected_mapping": "f" * 64}, khoa=self.K("g05-ep")), "M4_MAPPING_DA_DOI")
        self.assertEqual(self.loi(self.svc.gan_doi_tac_hop_dong, A1, **{**than, "mapping_id": d2["mapping"][0]}, khoa=self.K("g05-mk")),
                         "M4_MAPPING_KHONG_THAY")
        self.assertEqual((self.rev(hd), len(self.can_cu(hd)), self.doi_tac_master(hd)), (r0, 1, None), "từ chối không ghi")
        r = self.svc.gan_doi_tac_hop_dong(A1, **than, khoa=self.K("g05-ok"))
        self.assertEqual((r["revision"], r["lap_lai"]), (r0[0] + 1, False))
        self.assertEqual(self.rev(hd), (r0[0] + 1, r0[1] + 1))
        self.assertEqual(self.doi_tac_master(hd), d1["doi_tac_id"])
        cc = self.can_cu(hd)
        self.assertEqual([(c["nguon"], c["boi"], c["mapping_id"]) for c in cc[1:]], [("GAN_DOI_TAC", A1, than["mapping_id"])])
        self.assertEqual((cc[-1]["sha256"], cc[-1]["ly_do"]), (r["expected_master"], than["ly_do"]))
        x = self.mc(hd)
        self.assertEqual((x["dong_bo"], x["master"]["mapping_trang_thai"], str(x["master"]["doi_tac_id"])), (True, "OK", d1["doi_tac_id"]))
        truoc = self.dem(hd)
        lai = self.svc.gan_doi_tac_hop_dong(A1, **than, khoa=self.K("g05-ok"))
        self.assertEqual((lai["lap_lai"], lai["revision"]), (True, r["revision"]))
        self.assertEqual(self.dem(hd), truoc, "replay không thêm hàng")
        self.assertEqual(self.loi(self.svc.gan_doi_tac_hop_dong, A1, **{**than, "ly_do": "Lý do khác"}, khoa=self.K("g05-ok")), "M4_IDEMPOTENCY_KHAC")
        self.assertEqual(self.loi(self.svc.gan_doi_tac_hop_dong, A1, **than, khoa=self.K("g05-cu")), "M4_REVISION_CU")  # revision đã đổi
        self.assertEqual(self.loi(self.gan, hd, d1, "g05-same"), "M4_KHONG_DOI")
        # HOLD mapping: hai mapping mở → MO_HO (không có mapping_id để chọn); mapping khóa → KHOA_DONG
        mo_ho = seed_doi_tac(self.admin, self.run_id, "g05mh", self.pn, so_mapping=2)
        khoa = seed_doi_tac(self.admin, self.run_id, "g05kh", self.pn, khoa=True)
        self.assertEqual((self.muc_doi_tac(mo_ho)["ma_hold"], self.muc_doi_tac(mo_ho)["mapping_id"]), ("M4_MAPPING_MO_HO", None))
        self.assertEqual((self.muc_doi_tac(khoa)["ma_hold"], self.muc_doi_tac(khoa)["mapping_id"]), ("M4_MAPPING_KHOA_DONG", None))
        m = self.mc(hd)
        than_mh = dict(hop_dong_id=hd, doi_tac_id=mo_ho["doi_tac_id"], mapping_id=mo_ho["mapping"][0], revision=m["revision"],
                       expected_master=m["expected_master"], expected_mapping=self.q("SELECT m4._mc_mapping_sha(%s)", (mo_ho["mapping"][0],)),
                       ly_do="Thử mơ hồ")
        self.assertEqual(self.loi(self.svc.gan_doi_tac_hop_dong, A1, **than_mh, khoa=self.K("g05-mh")), "M4_MAPPING_MO_HO")
        than_kh = {**than_mh, "doi_tac_id": khoa["doi_tac_id"], "mapping_id": khoa["mapping"][0],
                   "expected_mapping": self.q("SELECT m4._mc_mapping_sha(%s)", (khoa["mapping"][0],))}
        self.assertEqual(self.loi(self.svc.gan_doi_tac_hop_dong, A1, **than_kh, khoa=self.K("g05-kh")), "M4_MAPPING_KHONG_HIEN_HANH")
        self.assertEqual(self.dem(hd)["can_cu"], truoc["can_cu"])
        self.s["g05"] = (hd, d1)

    # ------------------------------------------------------------------ G06 hai lệnh gắn đồng thời, hai khóa khác → đúng một thắng
    def test_g06_gan_dong_thoi_hai_khoa(self):
        hd = self.ho_so_moi("g06")
        d1, d2 = seed_doi_tac(self.admin, self.run_id, "g06a", self.pn), seed_doi_tac(self.admin, self.run_id, "g06b", self.pn)
        t1, t2 = self.than_gan(hd, d1), self.than_gan(hd, d2)
        svc2, svc3 = self._svc_moi(), self._svc_moi()
        dt = svc2.danh_tinh(A1)
        cm = svc2._tx(dt)  # SEAM_GIAO_DICH_GIU
        cm.__enter__()
        try:
            svc2.conn.execute("SELECT m4.gan_doi_tac_hop_dong(%s, %s::uuid, %s::uuid, %s::uuid, %s, %s, %s, %s)",
                              (self.K("g06-1"), hd, t1["doi_tac_id"], t1["mapping_id"], t1["revision"], t1["expected_master"],
                               t1["expected_mapping"], t1["ly_do"])).fetchone()
            th, out = chay_nen(lambda: svc3.gan_doi_tac_hop_dong(A1, **t2, khoa=self.K("g06-2")))
            self.assertTrue(cho_khoa(self.admin, svc3.conn), "lệnh thứ hai phải chờ khóa master")
        finally:
            cm.__exit__(None, None, None)
        th.join(60)
        self.assertEqual(ma_loi(out.get("loi")) if "loi" in out else None, "M4_REVISION_CU")
        self.assertEqual(self.doi_tac_master(hd), d1["doi_tac_id"])
        self.assertEqual([c["nguon"] for c in self.can_cu(hd)].count("GAN_DOI_TAC"), 1)
        self.assertEqual(self.rev(hd)[0], t1["revision"] + 1)

    # ------------------------------------------------------------------ G07 nguồn khác quản lý / đã nộp → từ chối, 0 thay đổi
    def test_g07_crm_khoa_va_sau_nop_tu_choi_khong_doi(self):
        d = seed_doi_tac(self.admin, self.run_id, "g07", self.pn)
        with self.subTest(ca="CRM"):
            hd = next(iter(self.s.get("crm", {}).values()), None)
            if hd is None:
                self.skipTest("NOT_READY: chưa nhận được master CRM nào ở G01 (clone DEMO thiếu master CRM)")
            x = self.mc(hd)
            self.assertEqual(x["gan_doi_tac"], {"duoc": False, "ma": "M4_MASTER_CAN_SUA_TAI_NGUON"})
            truoc, fp = self.dem(hd), self.dau_van_tay(hd)
            than = dict(hop_dong_id=hd, doi_tac_id=d["doi_tac_id"], mapping_id=d["mapping"][0], revision=x["revision"],
                        expected_master=x["expected_master"], expected_mapping=self.muc_doi_tac(d)["expected_mapping"], ly_do="Thử CRM")
            self.assertEqual(self.loi(self.svc.gan_doi_tac_hop_dong, A1, **than, khoa=self.K("g07-crm")), "M4_MASTER_CAN_SUA_TAI_NGUON")
            self.assertEqual((self.dem(hd), self.dau_van_tay(hd)), (truoc, fp))
        with self.subTest(ca="SAU_NOP"):
            h = self.dung_san_sang("g07n", gan_doi_tac=False, nop=True)
            self.s["g07n"] = h
            x = self.mc(h["hd"])
            self.assertEqual(x["gan_doi_tac"], {"duoc": False, "ma": "M4_MASTER_CAN_PHIEN_BAN_DIEU_CHINH"})
            truoc = (self.dem(h["hd"]), self.rev(h["hd"]), self.doi_tac_master(h["hd"]))
            self.assertEqual(self.loi(self.gan, h["hd"], d, "g07-nop"), "M4_MASTER_CAN_PHIEN_BAN_DIEU_CHINH")
            self.assertEqual((self.dem(h["hd"]), self.rev(h["hd"]), self.doi_tac_master(h["hd"])), truoc)

    # ------------------------------------------------------------------ G08 liên kết phiên bản bất biến; nguồn đổi → +1 revision, xác nhận hết hiệu lực
    def test_g08_lien_ket_bat_bien_va_nguon_doi_tang_mot(self):
        h = self.dung_san_sang("g08", nop=True)
        hd = h["hd"]
        lk = self.admin.execute("SELECT id, can_cu_id, can_cu_sha256 FROM m4.master_can_cu_phien_ban WHERE hop_dong_id = %s", (hd,)).fetchall()
        self.assertEqual(len(lk), 1, "bản nộp đầu phải có đúng một liên kết căn cứ")
        cc = self.can_cu(hd)
        self.assertEqual(lk[0][2], cc[-1]["sha256"])
        for cau in ("UPDATE m4.master_can_cu_phien_ban SET can_cu_sha256 = can_cu_sha256 WHERE hop_dong_id = %s",
                    "DELETE FROM m4.master_can_cu_phien_ban WHERE hop_dong_id = %s",
                    "UPDATE m4.master_can_cu SET ly_do = 'x' WHERE hop_dong_id = %s"):
            with self.subTest(owner=cau):
                self.assertRaises(psycopg.Error, self.admin.execute, cau, (hd,))
        r0 = self.rev(hd)
        self.assertTrue(self.svc.chi_tiet(A1, hd)["xac_nhan"]["con_hieu_luc"])
        dong_mapping(self.admin, h["doi_tac"]["mapping"][0])
        self.assertEqual(self.rev(hd), (r0[0] + 1, r0[1] + 1), "nguồn đổi → revision + rev_tham_so tăng ĐÚNG 1")
        cc2 = self.can_cu(hd)
        self.assertEqual((len(cc2), cc2[-1]["nguon"], cc2[-1]["meta"]["mapping_trang_thai"]), (len(cc) + 1, "QUAN_SAT_NGUON_MAPPING", "THIEU"))
        self.assertEqual((cc2[-1]["boi"], cc2[-1]["thieu_nguoi"]), (None, "NGUON_KHONG_CO_DANH_TINH_PHIEN"))
        ct = self.svc.chi_tiet(A1, hd)
        self.assertFalse(ct["xac_nhan"]["con_hieu_luc"])
        self.assertTrue(ct["dot"][0]["can_cu_doi_sau_nop"])
        self.assertEqual(self.admin.execute("SELECT can_cu_sha256 FROM m4.master_can_cu_phien_ban WHERE hop_dong_id = %s", (hd,)).fetchall(),
                         [(lk[0][2],)], "liên kết cũ giữ nguyên")
        self.assertIn("MAPPING_THIEU", ct["master_can_cu"]["hold"])
        self.s["g08"] = h

    # ------------------------------------------------------------------ G09 CRM G6A (người chỉ có CRM) → observer M4 ghi căn cứ + tăng 1
    def test_g09_crm_g6a_nguoi_chi_crm_quan_sat(self):
        raw = os.environ.get(ENV_G6A)
        if not raw:
            self.skipTest(f"NOT_READY: chưa cấp {ENV_G6A} (lần kích hoạt G6A Root chuẩn bị trên clone) — không tự dựng chuỗi CRM G1–G6A")
        g = json.loads(raw)
        for k in ("dang_nhap", "ky_id", "expected_revision", "check_id", "do_thi_sha256", "hop_dong_id"):
            if k not in g:
                raise LoiThietLap(f"SETUP_FAILURE: {ENV_G6A} thiếu '{k}'")
        hd = str(g["hop_dong_id"])
        if self.q("SELECT 1 FROM m4.ho_so_hop_dong WHERE hop_dong_id = %s", (hd,)) is None:
            self.svc.nhan_master_hop_dong(A1, du_an_id=self.du_an, hop_dong_id=hd, ten="Nhận để quan sát G6A", expected_master=self.expected_master(hd),
                                          khoa=self.K("g09-nhan"))
        r0, n0 = self.rev(hd), len(self.can_cu(hd))
        from unittest.mock import patch
        from kho_tri_thuc.giao_dien.crm_g import dich_vu_kiem
        from kho_tri_thuc.giao_dien.server import LocalApp
        from tests.test_m4_review_http import CAU_HINH_FIXTURE
        tam = Path(tempfile.mkdtemp(prefix="ktt_m4_mc_g6a_"))
        (tam / "cau_hinh_fixture.toml").write_text(CAU_HINH_FIXTURE, encoding="utf-8")
        with patch.dict(os.environ, {LocalApp.CRM_ENV: self.cfg[ENV_APP], LocalApp.CRM_ENV_ADMIN: self.cfg[ENV_CHU], LocalApp.CRM_ENV_DB_KIEM_THU: "1"}):
            app = LocalApp(tam / "cau_hinh_fixture.toml", tam / "web")
            dich_vu_kiem(app).hieu_luc(g["dang_nhap"], ky_id=g["ky_id"], expected_revision=g["expected_revision"], check_id=g["check_id"],
                                       do_thi_sha256=g["do_thi_sha256"], khoa=self.K("g09-g6a"))
        cc = self.can_cu(hd)
        self.assertEqual((len(cc), cc[-1]["nguon"]), (n0 + 1, "QUAN_SAT_NGUON_HOP_DONG"))
        self.assertEqual(self.rev(hd), (r0[0] + 1, r0[1] + 1))
        self.assertTrue(cc[-1]["boi"] == g["dang_nhap"] or (cc[-1]["boi"] is None and cc[-1]["thieu_nguoi"] == "NGUON_KHONG_CO_DANH_TINH_PHIEN"))
        self.assertTrue(self.mc(hd)["dong_bo"])

    # ------------------------------------------------------------------ G10 nguồn đổi không thực chất → không tăng; không backfill lịch sử
    def test_g10_no_op_khong_tang_va_khong_backfill(self):
        hd, d1 = self.s.get("g05") or (None, None)
        if hd is None:
            self.skipTest("NOT_RUN: G05 chưa dựng hồ sơ có đối tác")
        r0, n0 = self.rev(hd), len(self.can_cu(hd))
        self.admin.execute("UPDATE master.doi_tac_ma_junsky SET ten_junsky = ten_junsky WHERE id = %s", (d1["mapping"][0],))
        khac = seed_doi_tac(self.admin, self.run_id, "g10", self.pn)  # INSERT mapping đối tác khác → observer chạy, hash HĐ không đổi
        self.admin.execute("UPDATE master.doi_tac_ma_junsky SET valid_to = now() WHERE id = %s", (khac["mapping"][0],))
        self.assertEqual((self.rev(hd), len(self.can_cu(hd))), (r0, n0))
        lich_su = self.q("""SELECT v.hop_dong_id FROM m4.duyet_phien_ban v
                            WHERE v.trang_thai = 'DA_NOP' AND NOT EXISTS (SELECT 1 FROM m4.master_can_cu_phien_ban l WHERE l.phien_ban_id = v.id)
                            ORDER BY v.hop_dong_id LIMIT 1""")
        if lich_su is None:
            self.skipTest("NOT_READY: clone không có bản DA_NOP trước khi apply gói (không chứng minh được nhánh không backfill)")
        cc = self.can_cu(str(lich_su))
        self.assertEqual((cc[0]["nguon"], cc[0]["boi"], cc[0]["thieu_nguoi"]), ("BASELINE_BIET_TAI_NHAN", None, "NGUON_KHONG_CO_DANH_TINH_PHIEN"))
        x = self._mc_hoac_none(str(lich_su), A1)
        if x is not None:
            self.assertIn("LICH_SU_NOP_CHUA_CHUNG_MINH", x["hold"])
            self.assertGreater(x["phien_ban_chua_chung_minh"], 0)

    # ------------------------------------------------------------------ G11 login ứng dụng không gọi nội bộ / không ghi trực tiếp
    def test_g11_app_web_khong_goi_noi_bo_khong_update_ho_so(self):
        hd = self.s.get("g04") or self.ho_so_moi("g11")
        dt = self.svc.danh_tinh(A1)
        truoc = (self.rev(hd), len(self.can_cu(hd)), self.doi_tac_master(hd))
        cau = ("SELECT m4._mc_sha('{}'::jsonb)", "SELECT m4._mc_meta(%s::uuid, NULL, false)", "SELECT m4._mc_mapping_sha(%s::uuid)",
               "SELECT m4._mc_ghi(%s::uuid, '{}'::jsonb, 'GAN_DOI_TAC', 'x', NULL, true)",
               "SELECT m4._mc_quan_sat_mapping()", "SELECT m4._mc_chup_phien_ban()",
               "UPDATE m4.ho_so_hop_dong SET revision = revision + 1 WHERE hop_dong_id = %s::uuid",
               "INSERT INTO m4.master_can_cu (phap_nhan_id, du_an_id, hop_dong_id, so, revision_ho_so, meta, sha256, nguon) "
               "SELECT phap_nhan_id, du_an_id, hop_dong_id, 99, 1, '{}'::jsonb, repeat('0', 64), 'GAN_DOI_TAC' FROM m4.ho_so_hop_dong WHERE hop_dong_id = %s::uuid",
               "UPDATE master.hop_dong SET doi_tac_id = NULL WHERE id = %s::uuid RETURNING id",
               "UPDATE m4.master_can_cu SET ly_do = 'x' WHERE hop_dong_id = %s::uuid RETURNING id")
        for c in cau:
            with self.subTest(sql=c[:60]):
                try:
                    with self.svc._tx(dt):
                        cur = self.svc.conn.execute(c, (hd,) if "%s" in c else None)
                        bi_chan = not c.startswith("SELECT") and cur.rowcount == 0  # ghi bị RLS lọc hết (0 hàng) cũng là chặn; SELECT phải lỗi quyền
                except psycopg.Error:
                    bi_chan = True
                self.assertTrue(bi_chan, c)
        self.assertEqual((self.rev(hd), len(self.can_cu(hd)), self.doi_tac_master(hd)), truoc)

    # ------------------------------------------------------------------ G12 gắn đối tác ↔ đóng mapping: hai thứ tự thắng khóa
    def test_g12_attach_vs_dong_mapping_hai_thu_tu(self):
        chu2 = self._chu_moi()
        with self.subTest(thu_tu="1_attach_thang"):
            hd = self.ho_so_moi("g12a")
            d = seed_doi_tac(self.admin, self.run_id, "g12a", self.pn)
            t = self.than_gan(hd, d)
            svc2 = self._svc_moi()
            cm = svc2._tx(svc2.danh_tinh(A1))  # SEAM_GIAO_DICH_GIU: attach giữ khóa master + hồ sơ
            cm.__enter__()
            try:
                svc2.conn.execute("SELECT m4.gan_doi_tac_hop_dong(%s, %s::uuid, %s::uuid, %s::uuid, %s, %s, %s, %s)",
                                  (self.K("g12a"), hd, t["doi_tac_id"], t["mapping_id"], t["revision"], t["expected_master"], t["expected_mapping"],
                                   t["ly_do"])).fetchone()
                th, out = chay_nen(lambda: dong_mapping(chu2, t["mapping_id"]))
                self.assertTrue(cho_khoa(self.admin, chu2), "đóng mapping phải chờ khóa master của attach")
            finally:
                cm.__exit__(None, None, None)
            th.join(60)
            self.assertNotIn("loi", out)
            self.assertEqual(self.doi_tac_master(hd), d["doi_tac_id"])
            self.assertEqual(self.rev(hd)[0], t["revision"] + 2, "attach +1, observer đóng mapping +1 (HĐ vừa gắn bị vô hiệu)")
            cc = self.can_cu(hd)
            self.assertEqual([c["nguon"] for c in cc[-2:]], ["GAN_DOI_TAC", "QUAN_SAT_NGUON_MAPPING"])
            self.assertEqual(cc[-1]["meta"]["mapping_trang_thai"], "THIEU")
            x = self.mc(hd)
            self.assertTrue(x["dong_bo"])
            self.assertIn("MAPPING_THIEU", x["hold"])
        with self.subTest(thu_tu="2_dong_thang"):
            hd = self.ho_so_moi("g12b")
            d = seed_doi_tac(self.admin, self.run_id, "g12b", self.pn)
            t = self.than_gan(hd, d)
            svc2 = self._svc_moi()
            truoc = (self.rev(hd), len(self.can_cu(hd)), self.q("SELECT count(*) FROM m4.bien_nhan WHERE khoa = %s", (self.K("g12b"),)))
            with chu2.transaction():  # đóng mapping giữ khóa mapping + (observer) master FOR SHARE + hồ sơ
                dong_mapping(chu2, t["mapping_id"])
                th, out = chay_nen(lambda: svc2.gan_doi_tac_hop_dong(A1, **t, khoa=self.K("g12b")))
                self.assertTrue(cho_khoa(self.admin, svc2.conn), "attach phải chờ khóa master của giao dịch nguồn")
            th.join(60)
            self.assertEqual(ma_loi(out["loi"]) if "loi" in out else None, "M4_MAPPING_DA_DOI")
            self.assertEqual((self.rev(hd), len(self.can_cu(hd)), self.q("SELECT count(*) FROM m4.bien_nhan WHERE khoa = %s", (self.K("g12b"),))),
                             truoc, "0 thay đổi")
            self.assertIsNone(self.doi_tac_master(hd))

    # ------------------------------------------------------------------ G13 nguồn đổi ↔ nộp: hai thứ tự thắng khóa
    def test_g13_nguon_doi_vs_nop_hai_thu_tu(self):
        chu2, chu3 = self._chu_moi(), self._chu_moi()
        with self.subTest(thu_tu="A_nguon_thang"):
            h = self.dung_san_sang("g13a")
            hd, dot = h["hd"], h["dot"]
            r0 = self.rev(hd)[0]
            rd = self.q("SELECT revision FROM m4.dot WHERE id = %s", (dot,))
            with chu2.transaction():  # nguồn giữ khóa hồ sơ (observer) tới commit
                dong_mapping(chu2, h["doi_tac"]["mapping"][0])
                th, out = chay_nen(lambda: self.svc.nop(A1, dot_id=dot, revision_ho_so=r0, revision_dot=rd, khoa=self.K("g13a-nop")))
                self.assertTrue(cho_khoa(self.admin, self.svc.conn), "nộp phải chờ khóa hồ sơ của nguồn")
            th.join(120)
            self.assertEqual(ma_loi(out["loi"]) if "loi" in out else None, "M4_REVISION_CU")
            self.assertEqual(self.q("SELECT count(*) FROM m4.nop WHERE dot_id = %s", (dot,)), 0)
            self.assertEqual(self.q("SELECT count(*) FROM m4.master_can_cu_phien_ban WHERE hop_dong_id = %s", (hd,)), 0)
            self.assertEqual(self.rev(hd)[0], r0 + 1)
        with self.subTest(thu_tu="B_nop_thang"):
            h = self.dung_san_sang("g13b")
            hd, dot = h["hd"], h["dot"]
            r0 = self.rev(hd)[0]
            rd = self.q("SELECT revision FROM m4.dot WHERE id = %s", (dot,))
            sha_truoc = self.can_cu(hd)[-1]["sha256"]
            with chu3.transaction():  # owner giữ đợt → nộp đã khóa hồ sơ rồi chờ đợt
                chu3.execute("SELECT 1 FROM m4.dot WHERE id = %s FOR UPDATE", (dot,)).fetchone()
                tn, on = chay_nen(lambda: self.svc.nop(A1, dot_id=dot, revision_ho_so=r0, revision_dot=rd, khoa=self.K("g13b-nop")))
                self.assertTrue(cho_khoa(self.admin, self.svc.conn), "nộp phải chờ khóa đợt")
                tm, om = chay_nen(lambda: dong_mapping(chu2, h["doi_tac"]["mapping"][0]))
                self.assertTrue(cho_khoa(self.admin, chu2), "đóng mapping phải chờ khóa hồ sơ của lệnh nộp")
            tn.join(120)
            tm.join(120)
            self.assertNotIn("loi", on)
            self.assertNotIn("loi", om)
            lk = self.admin.execute("SELECT can_cu_sha256 FROM m4.master_can_cu_phien_ban WHERE hop_dong_id = %s", (hd,)).fetchall()
            self.assertEqual(lk, [(sha_truoc,)], "bản nộp liên kết căn cứ ĐÚNG lúc nộp")
            cc = self.can_cu(hd)
            self.assertEqual((cc[-1]["nguon"], cc[-2]["sha256"]), ("QUAN_SAT_NGUON_MAPPING", sha_truoc))
            self.assertEqual(self.rev(hd)[0], r0 + 1, "nguồn đổi sau nộp → +1 → bản đã nộp CAN_KIEM_LAI qua cổng revision")
            self.assertTrue(self.svc.chi_tiet(A1, hd)["dot"][0]["can_cu_doi_sau_nop"])


if __name__ == "__main__":
    unittest.main()
