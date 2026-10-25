"""M4-02C — kiểm PostgreSQL THẬT cho duyệt hồ sơ đợt (XayDungK2.duyet_*). CODE_ONLY: coder viết, CHƯA CHẠY (WRITTEN_NOT_RUN).

KHÔNG tạo CSDL, KHÔNG migrate, KHÔNG seed CRM/M9/full bootstrap. Chạy DUY NHẤT trên một CLONE DEMO SỞ HỮU do Root chuẩn bị (đã ở schema 24), cấp qua env
lúc chạy (không .env/var, không hardcode DSN/credentials, không in DSN ra thông điệp):
  KHO_M4_02C_CLONE_DSN         DSN chủ bảng (owner) của clone — đường tin cậy của máy chủ
  KHO_M4_02C_CLONE_APP_DSN     DSN login ứng dụng có sẵn (IN ROLE app_web, NOSUPERUSER, NOBYPASSRLS) — test KHÔNG tạo role
  KHO_M4_02C_CLONE_DB          tên CSDL clone mong đợi (bắt đầu 'kho_test_')
  KHO_M4_02C_CLONE_PROVENANCE  giá trị master.he_thong['m4_02c_clone_provenance'] Root ghi khi dựng clone (ràng clone ↔ nguồn/lineage)
  KHO_M4_02C_M24_SHA256        checksum M0024 Root đã ghim (phải = master.schema_migrations[24] = sha256 định nghĩa hiện tại)
Không env nào → SkipTest 'NOT_VERIFIED' (không phải PASS). Thiếu một phần / clone không chứng minh được → LỖI THIẾT LẬP (setUpClass raise) TRƯỚC mọi ghi.
Cổng clone (chỉ đọc, trước mọi ghi): đúng tên CSDL; login app đúng CSDL + IN app_web + không superuser/bypassrls; owner sở hữu bảng M24; lineage ứng dụng
= 24 (checksum 1–24 khớp chuỗi phần mềm) + checksum 24 = ghim; marker ứng dụng KTT1 + marker seed CRM/M4 DEMO + provenance khớp; phạm vi DEMO (mọi PN
'PN_DEMO_*', mọi người dùng mo_phong). Sau cổng: chỉ `m4_demo.khoi_tao_duyet` (thêm duyệt viên DEMO riêng, không hồi sinh quyền đã thu hồi) — DUYET đã
thu hồi (clone đã dùng cho ca P10) → lỗi thiết lập, cần clone mới. Mọi dữ liệu nghiệp vụ là HĐ/đợt DEMO MỚI với số HĐ/khóa riêng của lượt (run_id).
Không DROP/DELETE/TRUNCATE; P03 thử INSERT seal sai bằng giao dịch force_rollback (luôn hủy). Thu hồi (P10) chỉ trên duyệt viên DEMO, không cấp lại.
Ca dương cần engine #6 (gate dùng chung của test_m4_02b_k2) + lõi nguồn Review + openpyxl/python-docx; thiếu → SkipTest NOT_READY/NOT_RUN.

P01 thứ tự duyệt→PDF: PDF trước kết luận → M4_DUYET_CHUA_KET_LUAN (0 hàng); kết luận (REVIEW) → CHO_DUYET; SOAN/REVIEW chấp thuận → PHAM_VI; DUYET
    chấp thuận → CHO_PDF, 0 seal, 0 KT (DTO kt CHUA_CHUYEN); PDF → DA_SEAL + MỘT gốc KT + MỘT phong bì; tải PDF đúng bytes.
P02 thứ tự PDF→duyệt: PDF gắn kết luận → CHO_DUYET (0 seal/KT) → chấp thuận → DA_SEAL; seal/gốc/phong bì cùng hình dạng + cùng số liệu với P01.
P03 PDF ở đồ thị A → L3 chạy lại (đồ thị B) → kết luận B → chấp thuận: KHÔNG seal PDF của A, 0 KT; INSERT seal dùng PDF A bị FK chặn; tải lại
    CÙNG bytes → ứng viên MỚI gắn B → seal dùng ứng viên mới (bytes trùng không vượt ràng buộc).
P04 vật liệu đổi sau nộp (nhập lại BOQ): kết luận/chấp thuận/PDF trên v1 → M4_DUYET_CAN_PHIEN_BAN_MOI, v1 không đổi, 0 hàng mới; DTO CAN_KIEM_LAI +
    VAT_LIEU DOI_SAU_NOP; phiên bản kế tiếp + L3 lại + nộp → v2 kết luận được.
P05 replay/đồng thời: replay → cùng ID, 0 delta; khác body cùng khóa → IDEMPOTENCY_KHAC; hai kết nối chấp thuận đồng thời → MỘT quyết định; hai PDF
    đồng thời → MỘT seal/gốc/phong bì.
P06 đính chính: phiên bản kế tiếp của bản đã seal → seal 2 dùng LẠI gốc KT + phong bì 2 (truoc_id = phong bì 1); seal 1 nguyên.
P07 DTO trung thực (lịch sử v1 vs hiện hành v2): mảng/khóa theo UI contract; XEM chỉ đọc; A2/B1 → KHONG_THAY.
P08 bypass SQL: login app gọi hàm lệnh/ghi bảng M24 → bị từ chối quyền.
P09 (cuối) thu hồi DUYET: replay đúng body cũ, xem, tải PDF → KHONG_THAY; 0 delta; SOAN vẫn tải được.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import unittest
import uuid
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.kiem_chung import fixtures_m4 as F

ENV_CHU, ENV_APP, ENV_DB, ENV_NGUON, ENV_M24 = ("KHO_M4_02C_CLONE_DSN", "KHO_M4_02C_CLONE_APP_DSN", "KHO_M4_02C_CLONE_DB",
                                                "KHO_M4_02C_CLONE_PROVENANCE", "KHO_M4_02C_M24_SHA256")
ENV = (ENV_CHU, ENV_APP, ENV_DB, ENV_NGUON, ENV_M24)
KHOA_NGUON = "m4_02c_clone_provenance"
TIEN_TO_DB = "kho_test_"
CO_ENV = any(os.environ.get(k) for k in ENV)
A1, A2, B1, REVIEW, XEM = "MO_PHONG_DU_AN_A1", "MO_PHONG_DU_AN_A2", "MO_PHONG_DU_AN_B1", "MO_PHONG_REVIEW_M4", "MO_PHONG_XEM_M4"
DUYET = "MO_PHONG_DUYET_M4"
BANG_DUYET = ("duyet_phien_ban", "duyet_ket_luan", "duyet_ket_luan_dong", "duyet_quyet_dinh", "duyet_pdf", "duyet_seal", "duyet_kt_cho",
              "duyet_kt_phong_bi")
LY_DO_SKIP = "NOT_VERIFIED: chưa cấp clone DEMO sở hữu (KHO_M4_02C_CLONE_*) — test M4-02C PG/HTTP không chạy, KHÔNG tính đạt"


# ================================================================================================== cổng clone (dùng chung với test_m4_02c_http)
class LoiThietLap(Exception):
    """SETUP_FAILURE / NOT_VERIFIED: clone không chứng minh được là clone DEMO sở hữu đúng lineage — dừng TRƯỚC mọi ghi. Thông điệp không chứa DSN."""


def cau_hinh_clone() -> dict:
    """Đọc env clone. Thiếu MỘT PHẦN → lỗi thiết lập (không lặng lẽ bỏ qua). Gọi khi CO_ENV."""
    gia_tri = {k: os.environ.get(k) or "" for k in ENV}
    thieu = [k for k, v in gia_tri.items() if not v]
    if thieu:
        raise LoiThietLap("SETUP_FAILURE: cấu hình clone dở dang — thiếu " + ", ".join(thieu))
    if psycopg is None:
        raise LoiThietLap("SETUP_FAILURE: thiếu driver psycopg")
    if not re.fullmatch(r"[0-9a-f]{64}", gia_tri[ENV_M24]):
        raise LoiThietLap(f"SETUP_FAILURE: {ENV_M24} phải là SHA-256 hex thường")
    return gia_tri


def _q1(conn, sql, params=None):  # không bind → None: psycopg không parse placeholder, '%' literal (LIKE 'PN\_DEMO\_%') giữ nguyên
    row = conn.execute(sql, params).fetchone()
    return None if row is None else (next(iter(row.values())) if isinstance(row, dict) else row[0])


def kiem_clone(chu, web, cfg: dict) -> dict:
    """Cổng CHỈ ĐỌC trước mọi ghi. chu = kết nối owner (autocommit), web = login ứng dụng. Trả bằng chứng không bí mật; sai → LoiThietLap."""
    from kho_tri_thuc.ha_tang import pg_migrations as PGM
    from kho_tri_thuc.ha_tang import postgres as pg
    from kho_tri_thuc.k2 import crm_demo, m4_demo
    from kho_tri_thuc.m4.sql_duyet import M0024_M4_DUYET

    def sai(ly_do):
        raise LoiThietLap("SETUP_FAILURE: " + ly_do + " — không ghi gì; Root cấp clone DEMO sở hữu đúng lineage")
    db = _q1(chu, "SELECT current_database()")
    if db != cfg[ENV_DB] or not str(db).startswith(TIEN_TO_DB):
        sai(f"CSDL kết nối owner không phải clone mong đợi (phải = {ENV_DB} và bắt đầu '{TIEN_TO_DB}')")
    if _q1(web, "SELECT current_database()") != db:
        sai("login ứng dụng không trỏ cùng CSDL clone")
    r = web.execute("""SELECT r.rolsuper, r.rolbypassrls, pg_has_role(current_user, 'app_web', 'MEMBER')
                       FROM pg_roles r WHERE r.rolname = current_user""").fetchone()
    vals = tuple(r.values()) if isinstance(r, dict) else tuple(r or ())
    if vals != (False, False, True):
        sai("login ứng dụng phải IN ROLE app_web, NOSUPERUSER, NOBYPASSRLS")
    if _q1(chu, "SELECT to_regclass('m4.duyet_phien_ban') IS NOT NULL") is not True:
        sai("clone chưa có bảng M24")
    if _q1(chu, """SELECT pg_has_role(current_user, c.relowner, 'MEMBER') FROM pg_class c WHERE c.oid = 'm4.duyet_phien_ban'::regclass""") is not True:
        sai("kết nối owner không sở hữu bảng M24 (không phải đường tin cậy của máy chủ)")
    try:
        version = pg.kiem_lineage_ung_dung(chu)  # checksum 1..N khớp chuỗi phần mềm + N = PG_SCHEMA_VERSION
    except DataError as exc:
        sai(f"lineage không khớp ({exc.code})")
    ck24 = hashlib.sha256("\n".join(M0024_M4_DUYET).encode()).hexdigest()
    if (version, PGM.PG_SCHEMA_VERSION, len(PGM.PG_MIGRATIONS)) != (24, 24, 24) or PGM.PG_MIGRATIONS[-1] is not M0024_M4_DUYET:
        sai("schema/registry không phải 24 với M0024 cuối")
    if not (_q1(chu, "SELECT checksum FROM master.schema_migrations WHERE version = 24") == ck24 == cfg[ENV_M24]):
        sai("checksum M0024 trong clone ≠ định nghĩa hiện tại ≠ giá trị Root ghim")
    he = dict(chu.execute("SELECT key, value FROM master.he_thong WHERE key = ANY(%s)",  # chu: hàng tuple (kết nối mặc định)
                          ([pg.APP_MARKER_KEY, crm_demo.MARKER, m4_demo.MARKER, KHOA_NGUON],)).fetchall())
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
    return {"trang_thai": "CLONE_DEMO_DA_KIEM", "schema": version, "m0024_sha256": ck24}


def chuan_bi_duyet_vien(chu) -> dict:
    """Ghi DUY NHẤT sau cổng: duyệt viên DEMO riêng (insert-only, không hồi sinh quyền đã thu hồi). Không DU → lỗi thiết lập (clone đã dùng/sai)."""
    from kho_tri_thuc.k2 import m4_demo
    kq = m4_demo.khoi_tao_duyet(chu)
    if kq["trang_thai"] != "DU":
        raise LoiThietLap(f"SETUP_FAILURE: duyệt viên DEMO không đủ ({kq['trang_thai']}: {kq.get('ly_do')}; actor gốc có DUYET: "
                          f"{kq.get('actor_goc_co_duyet')}) — clone đã dùng hoặc sai ma trận; cần clone mới, test không tự cấp/khôi phục quyền")
    return kq


# ================================================================================================== dựng hồ sơ DEMO (dùng chung với test_m4_02c_http)
def dung_ho_so(svc, admin, K, nhan: str, run_id: str, *, gan_doi_tac: str | None = None) -> dict:
    """HĐ DEMO MỚI (số riêng của lượt) → trích #6 → tham số/xác nhận/khai PL → BOQ → đợt 1 + hồ sơ + chứng từ → NỘP (bản 1) → L3 công bố (SOAN).
    Bytes mỗi hồ sơ khác nhau (nhãn) để không dùng chung tệp giữa các HĐ. Trả định danh. Mẫu bước theo tests/test_m4_02b_k2.py K01/K02.
    gan_doi_tac tùy chọn là UUID đối tác DEMO: gắn bằng lệnh M4 thật khi còn nháp; None giữ nguyên luồng cũ."""
    from tests.test_m4_01b_pg import PHIEU_THAM_SO, VANG
    from tests.test_m4_02b_k2 import GN, NT_BANG, NT_DAU
    from tests.test_m4_02b_pure import _docx_bytes, _xlsx_bytes
    from tests.test_m4_review_k2 import ho_so_xlsx
    du_an = str(_q1(admin, "SELECT id FROM master.du_an WHERE ma_junsky = 'DA_XD_A1'"))
    s = {"nhan": nhan}

    def rev():
        return _q1(admin, "SELECT revision FROM m4.ho_so_hop_dong WHERE hop_dong_id = %s", (s["hd"],))

    def rev_dot():
        return _q1(admin, "SELECT revision FROM m4.dot WHERE id = %s", (s["dot"],))

    def tai(raw, ten, media, vai, khoa):
        return svc.tai_tep(A1, raw, du_an_id=du_an, vai_tro=vai, ten=ten, media_type=media, khoa=K(f"{nhan}-{khoa}"))["tep_id"]
    s["hd"] = svc.tao_hop_dong(A1, du_an_id=du_an, so_hop_dong=f"123/2025-{run_id}-{nhan}", ten=f"Gói duyệt DEMO {nhan}",
                               khoa=K(f"{nhan}-hd"))["hop_dong_id"]
    if gan_doi_tac is not None:
        # Đọc đúng mapping của đối tác trong PN dự án, không đoán UUID/mapping từ hóa đơn.
        ma = _q1(admin, """SELECT m.object_id_junsky FROM master.doi_tac_ma_junsky m
                           JOIN master.du_an d ON d.phap_nhan_id = m.phap_nhan_id
                           WHERE d.id = %s AND m.doi_tac_id = %s AND m.valid_to IS NULL
                             AND NOT m.khoa AND NOT m.dong AND m.valid_from <= now()
                           ORDER BY m.id LIMIT 1""", (du_an, gan_doi_tac))
        ds = svc.master_doi_tac(A1, du_an_id=du_an, q=ma, limit=50)["items"] if ma else []
        dt = next((x for x in ds if str(x["doi_tac_id"]) == gan_doi_tac), None)
        if dt is None or not dt.get("mapping_id") or not dt.get("expected_mapping"):
            raise AssertionError("Đối tác DEMO được cấp thiếu mapping M4 hiện hành duy nhất trong PN dự án")
        mc = svc.chi_tiet(A1, s["hd"])["master_can_cu"]
        svc.gan_doi_tac_hop_dong(A1, hop_dong_id=s["hd"], doi_tac_id=gan_doi_tac, mapping_id=dt["mapping_id"],
                                 revision=mc["revision"], expected_master=mc["expected_master"], expected_mapping=dt["expected_mapping"],
                                 ly_do="Gắn đối tác DEMO của bản sao trước khi nộp hồ sơ test 03B", khoa=K(f"{nhan}-gan-doi-tac"))
    dong_hd = tuple(f"Căn cứ Luật Xây dựng (văn bản DEMO {nhan});" if x.startswith("Căn cứ Luật") else x for x in F.DONG_HOP_DONG)
    tep_hd = tai(F.hop_dong_docx(dong_hd), f"Hợp đồng DEMO {nhan}.docx", F.MEDIA_DOCX, "HOP_DONG", "tep-hd")
    svc.gan_tep_hop_dong(A1, hop_dong_id=s["hd"], revision=rev(), tep_id=tep_hd, khoa=K(f"{nhan}-gan-hd"))
    tr = svc.trich(A1, hop_dong_id=s["hd"], revision=rev(), khoa=K(f"{nhan}-trich"))
    if tr.get("trang_thai") != "XONG":
        raise unittest.SkipTest(f"NOT_READY: trích #6 không XONG cho hồ sơ {nhan} ({tr.get('trang_thai')})")
    for ma, (tt, gia_tri, don_vi, dieu, trich) in PHIEU_THAM_SO.items():
        svc.sua_tham_so(A1, hop_dong_id=s["hd"], revision=rev(), ma=ma, trang_thai_tham_so=tt, gia_tri=gia_tri, don_vi=don_vi, dieu_khoan=dieu,
                        trich_dan=trich, ly_do=None if tt == "CO_GIA_TRI" else "HĐ Điều 3.1 ghi: Tạm ứng: Không áp dụng", khoa=K(f"{nhan}-sua-{ma}"))
    for ma in VANG:
        svc.sua_tham_so(A1, hop_dong_id=s["hd"], revision=rev(), ma=ma, trang_thai_tham_so="KHONG_QUY_DINH", ly_do="HĐ DEMO không có điều khoản này",
                        khoa=K(f"{nhan}-sua-{ma}"))
    svc.xac_nhan(A1, hop_dong_id=s["hd"], revision=rev(), ly_do="Phòng dự án đã soát", khoa=K(f"{nhan}-xn"))
    svc.khai_phu_luc(A1, hop_dong_id=s["hd"], revision=rev(), khai="KHONG_CO", khoa=K(f"{nhan}-khai"))
    boq_goc = tuple((r[0], r[1], f"{r[2]} {nhan}" if r[0] == "A" else r[2], *r[3:]) for r in F.BOQ_GOC)  # nhóm 'Phần móng <nhãn>': bytes riêng
    tep_boq = tai(F.boq_xlsx(boq_goc), f"BOQ-{nhan}.xlsx", F.MEDIA_XLSX, "BOQ", "boq-tep")
    b = svc.boq_nhap(A1, hop_dong_id=s["hd"], revision=rev(), tep_id=tep_boq, sheet="BOQ", hang_tieu_de=1, cot=dict(F.BOQ_COT), khoa=K(f"{nhan}-boq"))
    if b.get("trang_thai") != "DA_MAP":
        raise AssertionError(f"BOQ hồ sơ {nhan} không DA_MAP: {b.get('trang_thai')}")
    s["dot"] = svc.tao_dot(A1, hop_dong_id=s["hd"], so_dot=1, ngay_nghiem_thu="2026-03-01", khoa=K(f"{nhan}-dot"))["dot_id"]
    bb = [r[0] for r in admin.execute("SELECT ma FROM m4.danh_muc_ho_so_dot WHERE bat_buoc_dot_dau ORDER BY ma").fetchall()]
    muc = [r[0] for r in admin.execute("SELECT ma FROM m4.danh_muc_ho_so_dot ORDER BY ma").fetchall()]
    x1 = tai(ho_so_xlsx(f"KY1-{nhan}"), f"ho_so_ky1_{nhan}.xlsx", F.MEDIA_XLSX, "HO_SO_DOT", "x1")
    svc.gan_tep_dot(A1, dot_id=s["dot"], revision=rev_dot(), tep_id=x1, muc=bb[0], khoa=K(f"{nhan}-gan-x1"))
    for i, m in enumerate(bb):
        t = tai(F.pdf_demo(f"{nhan}-CT{i}"), f"hs-{nhan}-{i}.pdf", "application/pdf", "HO_SO_DOT", f"hs-{i}")
        svc.gan_tep_dot(A1, dot_id=s["dot"], revision=rev_dot(), tep_id=t, muc=m, khoa=K(f"{nhan}-gan-hs-{i}"))
    s["nt"] = tai(_docx_bytes([*NT_DAU, f"Ghi chú DEMO {nhan}"], NT_BANG), f"bb_nt_{nhan}.docx", F.MEDIA_DOCX, "HO_SO_DOT", "nt")
    gn = tai(_xlsx_bytes([("GiaoNhan", {**GN, (2, 3): f"DEMO {nhan}"})]), f"bb_gn_{nhan}.xlsx", F.MEDIA_XLSX, "HO_SO_DOT", "gn")
    for i, t in enumerate((s["nt"], gn)):
        svc.gan_tep_dot(A1, dot_id=s["dot"], revision=rev_dot(), tep_id=t, muc=muc[i], khoa=K(f"{nhan}-gan-ct-{i}"))
    if svc.chi_tiet_dot(A1, s["dot"])["thieu"]:
        raise AssertionError(f"Hồ sơ {nhan} còn thiếu mục nộp")
    svc.nop(A1, dot_id=s["dot"], revision_ho_so=rev(), revision_dot=rev_dot(), khoa=K(f"{nhan}-nop"))
    s["run"] = chay_l3(svc, s["dot"], K(f"{nhan}-l3"))
    s.update(du_an=du_an, rev=rev, tep_boq=tep_boq)
    return s


def chay_l3(svc, dot, khoa, *, cha=None) -> str:
    """Chạy (hoặc chạy lại từ run cha) Chứng từ L3 bằng SOAN trên căn cứ hiện hành; phải công bố (SUCCEEDED/PARTIAL)."""
    cs = svc.chung_tu_ds(A1, dot_id=dot)["co_so"]
    if cha is None:
        r = svc.chung_tu_chay(A1, dot_id=dot, revision=cs["revision"], expected_basis=cs["basis_sha256"], khoa=khoa)
    else:
        r = svc.chung_tu_chay_lai(A1, run_id=cha, revision=cs["revision"], expected_basis=cs["basis_sha256"], khoa=khoa)
    if r.get("trang_thai") not in ("SUCCEEDED", "PARTIAL"):
        raise AssertionError(f"L3 không công bố: {r.get('trang_thai')}")
    return r["run_id"]


def than_ket_luan(x: dict, *, so: dict = F.KET_LUAN_VND) -> dict:
    """Thân kết luận ĐỦ từ DTO (máy chủ cấp row_id/finding_id): KL chấp nhận literal theo mã HM (HM-01/HM-02 → F.KL_CHAP_NHAN, khác → '1') cho mọi
    dòng + lý do cho mọi phát hiện. Gán theo mã HM (không theo thứ tự row_id) để hai hồ sơ cùng BOQ chốt cùng số liệu."""
    ctx = x["context"]
    theo_ma = dict(zip(("HM-01", "HM-02"), F.KL_CHAP_NHAN))
    dong = [{"row_id": r["row_id"], "khoi_luong_chap_nhan": theo_ma.get(r.get("ma_hm"), "1")} for r in x["dong_nt"]]
    xl = [{"finding_id": f["finding_id"], "ly_do": "Đã soát chứng từ DEMO"} for f in x["phat_hien"]]
    return dict(dot_id=ctx["dot_id"], version_id=ctx["version_id"], revision=ctx["revision"], expected_basis=ctx["basis_sha256"], **so, dong_nt=dong,
                xu_ly_phat_hien=xl, ly_do=None)


@unittest.skipUnless(CO_ENV, LY_DO_SKIP)
class M4DuyetPG(unittest.TestCase):
    """Chạy theo thứ tự tên p01…p09 trên MỘT clone; trạng thái qua cls.s. P09 thu hồi DUYET (không đảo ngược) — clone sau đó không dùng lại."""

    @classmethod
    def setUpClass(cls):
        import tests.test_m4_02b_k2 as K2B  # import module (không import tên lớp TestCase — tránh chạy lại bộ 02B ở đây)
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        cfg = cau_hinh_clone()
        cls.cfg = cfg
        cls.admin = psycopg.connect(cfg[ENV_CHU], autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        web0 = psycopg.connect(cfg[ENV_APP], autocommit=True)
        cls.addClassCleanup(web0.close)
        cls.web_raw = web0
        cls.gate = kiem_clone(cls.admin, web0, cfg)  # CHỈ ĐỌC — sai → LoiThietLap, chưa ghi gì
        from tests.test_m4_02b_pure import _docx, openpyxl
        if not (K2B._nguon_da_nap() and openpyxl is not None and _docx is not None):
            raise unittest.SkipTest("NOT_RUN: lõi nguồn Review chưa nạp hoặc thiếu openpyxl/python-docx — không dựng được hồ sơ")
        cls.goc = Path(tempfile.mkdtemp(prefix="ktt_m4_02c_pg_"))  # DataRoot DEMO của lượt — giữ lại
        cls.run_id = uuid.uuid4().hex[:8]
        cls.trich6, cls.gate6 = K2B.M4ChungTuPG._gate_trich6.__func__(cls)  # cùng gate #6 của 02B (SkipTest NOT_READY/NOT_VERIFIED)
        cls.seed = chuan_bi_duyet_vien(cls.admin)  # ghi đầu tiên — sau cổng
        cls.XayDungK2 = XayDungK2
        cls.svc = cls._svc_moi()
        cls.s = {}

    @classmethod
    def _svc_moi(cls):
        web = psycopg.connect(cls.cfg[ENV_APP], autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(web.close)
        chu = psycopg.connect(cls.cfg[ENV_CHU], autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(chu.close)
        return cls.XayDungK2(web, cls.goc / "m4-k2", conn_tin_cay=chu, trich6=cls.trich6)

    # ------------------------------------------------------------------ helpers
    def K(self, ten):
        return f"m4dy-{self.run_id}-{ten}"

    def q(self, sql, params=()):
        return _q1(self.admin, sql, params)

    @staticmethod
    def ma(exc) -> str:
        if isinstance(exc, DataError):
            return exc.code
        if psycopg is not None and isinstance(exc, psycopg.Error):
            p = (getattr(exc.diag, "message_primary", "") or "").split(":", 1)[0]
            return p if re.fullmatch(r"[A-Z][A-Z0-9_]*", p) else type(exc).__name__
        return type(exc).__name__

    def loi(self, fn, *a, **k) -> str:
        try:
            fn(*a, **k)
        except (DataError, psycopg.Error) as exc:
            return self.ma(exc)
        self.fail("thao tác không bị chặn")

    def song_song(self, viec) -> tuple[list, list]:
        """Chạy các hàm không đối số trên luồng riêng cùng lúc; join có hạn + assert không còn sống. Trả (kết quả, mã lỗi)."""
        kq, loi = [], []

        def mot(fn):
            try:
                kq.append(fn())
            except BaseException as exc:  # noqa: BLE001
                loi.append(self.ma(exc))
        ts = [threading.Thread(target=mot, args=(fn,), daemon=True) for fn in viec]
        try:
            for t in ts:
                t.start()
        finally:
            for t in ts:
                t.join(600)
        self.assertEqual([t.is_alive() for t in ts], [False] * len(ts), "luồng đồng thời không kết thúc trong hạn")
        return kq, loi

    def dem(self, dot=None) -> dict:
        if dot is None:
            return {t: self.q(f"SELECT count(*) FROM m4.{t}") for t in BANG_DUYET if t != "duyet_ket_luan_dong"}
        return {t: self.q(f"SELECT count(*) FROM m4.{t} WHERE dot_id = %s", (dot,)) for t in BANG_DUYET if t != "duyet_ket_luan_dong"}

    def ho_so(self, nhan) -> dict:
        return dung_ho_so(self.svc, self.admin, self.K, nhan, self.run_id)

    def xem(self, dot, login=A1, version_id=None):
        return self.svc.duyet_xem(login, dot_id=dot, version_id=version_id)

    def ket_luan(self, dot, khoa, login=REVIEW, **thay):
        return self.svc.duyet_ket_luan(login, **{**than_ket_luan(self.xem(dot, login)), **thay}, khoa=self.K(khoa))

    def than_chap_thuan(self, dot, login=DUYET):
        x = self.xem(dot, login)
        c = x["context"]
        return dict(dot_id=dot, version_id=c["version_id"], revision=c["revision"], expected_basis=c["basis_sha256"], ket_luan_id=x["ket_luan"]["id"],
                    ly_do="Chấp thuận hồ sơ đợt DEMO")

    def chap_thuan(self, dot, khoa, login=DUYET, svc=None):
        return (svc or self.svc).duyet_chap_thuan(login, **self.than_chap_thuan(dot, login), khoa=self.K(khoa))

    def than_pdf(self, dot, ten, login=A1):
        c = self.xem(dot, login)["context"]
        return dict(dot_id=dot, version_id=c["version_id"], revision=c["revision"], expected_basis=c["basis_sha256"], ten=ten, media_type="application/pdf")

    def pdf(self, dot, raw, khoa, login=A1, svc=None, ten="ho_so_da_duyet.pdf"):
        return (svc or self.svc).duyet_pdf(login, raw, **self.than_pdf(dot, ten, login), khoa=self.K(khoa))

    def seal_dot(self, dot):
        r = self.admin.execute("""SELECT s.id, s.pdf_id, s.ket_luan_id, s.graph_sha256, s.so_lieu, s.so_lieu_sha256, b.id, b.thu_tu, b.truoc_id, b.noi_dung,
                                         c.id, c.seal_dau_id
                                  FROM m4.duyet_seal s JOIN m4.duyet_kt_phong_bi b ON b.seal_id = s.id JOIN m4.duyet_kt_cho c ON c.id = b.cho_id
                                  WHERE s.dot_id = %s ORDER BY b.thu_tu""", (dot,)).fetchall()
        return [dict(zip(("id", "pdf_id", "ket_luan_id", "graph", "so_lieu", "so_lieu_sha", "pb_id", "thu_tu", "truoc_id", "noi_dung", "goc_id",
                          "seal_dau_id"), x)) for x in r]

    def can(self, *khoa):
        for k in khoa:
            if k not in self.s:
                self.skipTest(f"ca trước chưa dựng '{k}' — NOT_RUN")

    # ------------------------------------------------------------------ P01
    def test_p01_duyet_roi_pdf(self):
        self.assertEqual(self.gate["schema"], 24)
        h = self.ho_so("A")
        dot = h["dot"]
        x = self.xem(dot)
        self.assertEqual((x["trang_thai"], x["chua_nop"], len(x["phien_ban"]), x["phien_ban"][0]["so"]), ("CHO_KET_LUAN", False, 1, 1))
        self.assertTrue(x["dong_nt"], "L3 không có hàng mục — không kết luận được (NOT_VERIFIED)")
        truoc = self.dem(dot)
        self.assertEqual(self.loi(self.pdf, dot, F.ho_so_dot_duyet_pdf("A-0"), "A-pdf-som"), "M4_DUYET_CHUA_KET_LUAN")
        self.assertEqual(self.dem(dot), truoc)
        self.assertEqual(self.loi(self.ket_luan, dot, "A-kl-xem", login=XEM), "M4_DUYET_PHAM_VI")
        kl = self.ket_luan(dot, "A-kl")
        self.assertEqual((kl["trang_thai"], kl["lap_lai"], kl["ket_luan_revision"], kl["pdf_id"], kl["kt_pending_id"]), ("CHO_DUYET", False, 1, None, None))
        for ai in (A1, REVIEW):
            self.assertEqual(self.loi(self.chap_thuan, dot, "A-ct-" + ai, login=ai), "M4_DUYET_PHAM_VI")
        ct = self.chap_thuan(dot, "A-ct")
        self.assertEqual((ct["trang_thai"], ct["seal_id"], ct["kt_pending_id"]), ("CHO_PDF", None, None))
        self.assertEqual((self.q("SELECT count(*) FROM m4.duyet_seal WHERE dot_id = %s", (dot,)),
                          self.q("SELECT count(*) FROM m4.duyet_kt_cho WHERE dot_id = %s", (dot,))), (0, 0))  # không PDF → 0 KT
        x = self.xem(dot, DUYET)
        self.assertEqual((x["trang_thai"], x["kt"]["trang_thai"], x["kt"]["pending_id"], x["pdf"]), ("CHO_PDF", "CHUA_CHUYEN", None, None))
        raw = F.ho_so_dot_duyet_pdf("A-1")
        p = self.pdf(dot, raw, "A-pdf")
        self.assertEqual(p["trang_thai"], "DA_SEAL", p)
        self.assertTrue(p["seal_id"] and p["kt_pending_id"] and p["pdf_id"])
        rows = self.seal_dot(dot)
        self.assertEqual([(r["thu_tu"], r["truoc_id"]) for r in rows], [(1, None)])
        self.assertEqual((str(rows[0]["id"]), str(rows[0]["pdf_id"]), str(rows[0]["goc_id"]), str(rows[0]["seal_dau_id"])),
                         (p["seal_id"], p["pdf_id"], p["kt_pending_id"], p["seal_id"]))
        x = self.xem(dot, DUYET)
        self.assertEqual((x["trang_thai"], x["kt"]["trang_thai"], x["kt"]["pending_id"], x["kt"]["phong_bi_hien_hanh"]),
                         ("DA_SEAL", "CHO_XAC_NHAN", p["kt_pending_id"], True))
        self.assertEqual((x["pdf"]["id"], x["pdf"]["name"], x["pdf"]["sha256"]), (p["pdf_id"], "ho_so_da_duyet.pdf", hashlib.sha256(raw).hexdigest()))
        for ai in (A1, DUYET):
            ten, media, b = self.svc.duyet_pdf_tai(ai, x["context"]["version_id"], p["pdf_id"])
            self.assertEqual((ten, media, b), ("ho_so_da_duyet.pdf", "application/pdf", raw))
        self.assertEqual(self.loi(self.pdf, dot, F.ho_so_dot_duyet_pdf("A-2"), "A-pdf-2"), "M4_DUYET_DA_SEAL")
        self.s["A"] = {**h, "seal": rows[0], "pdf": p["pdf_id"], "raw": raw, "v1": x["context"]["version_id"]}

    # ------------------------------------------------------------------ P02
    def test_p02_pdf_roi_duyet_cung_ket_qua(self):
        self.can("A")
        h = self.ho_so("B")
        dot = h["dot"]
        self.ket_luan(dot, "B-kl")
        raw = F.ho_so_dot_duyet_pdf("B-1")
        p = self.pdf(dot, raw, "B-pdf")
        self.assertEqual((p["trang_thai"], p["seal_id"], p["kt_pending_id"], p["quyet_dinh_id"]), ("CHO_DUYET", None, None, None))
        self.assertEqual(self.dem(dot)["duyet_kt_cho"], 0)
        x = self.xem(dot, DUYET)
        self.assertEqual((x["trang_thai"], x["pdf"]["id"], x["pdf"]["gan_hien_hanh"], x["kt"]["trang_thai"]), ("CHO_DUYET", p["pdf_id"], True, "CHUA_CHUYEN"))
        ct = self.chap_thuan(dot, "B-ct")
        self.assertEqual(ct["trang_thai"], "DA_SEAL", ct)
        self.assertEqual(ct["pdf_id"], p["pdf_id"])
        a, b = self.s["A"]["seal"], self.seal_dot(dot)
        self.assertEqual([(r["thu_tu"], r["truoc_id"]) for r in b], [(1, None)])
        b = b[0]
        self.assertEqual(str(b["seal_dau_id"]), str(b["id"]))
        self.assertEqual(set(a["so_lieu"]), set(b["so_lieu"]))
        self.assertEqual(set(a["noi_dung"]), set(b["noi_dung"]))
        chot = lambda s: ({k: s[k] for k in ("tien_te", "gia_tri_nt", "so_xin_thanh_toan", "tam_ung", "thu_hoi", "giu_lai", "thue")},  # noqa: E731
                          [(d["ma_hm"], d["khoi_luong_chap_nhan"]) for d in s["dong"]], len(s["xu_ly_phat_hien"]))
        self.assertEqual(chot(a["so_lieu"]), chot(b["so_lieu"]))  # hai thứ tự → cùng số liệu chốt
        self.assertEqual((a["noi_dung"]["ap"], a["noi_dung"]["request"]), (b["noi_dung"]["ap"], b["noi_dung"]["request"]))
        self.assertEqual(self.dem(dot), {"duyet_phien_ban": 1, "duyet_ket_luan": 1, "duyet_quyet_dinh": 1, "duyet_pdf": 1, "duyet_seal": 1,
                                         "duyet_kt_cho": 1, "duyet_kt_phong_bi": 1})
        self.assertEqual(self.dem(self.s["A"]["dot"]), self.dem(dot))

    # ------------------------------------------------------------------ P03
    def test_p03_pdf_do_thi_cu_khong_seal(self):
        h = self.ho_so("C")
        dot = h["dot"]
        kl_a = self.ket_luan(dot, "C-kl-a")
        raw = F.ho_so_dot_duyet_pdf("C-1")
        pa = self.pdf(dot, raw, "C-pdf-a")
        self.assertEqual(pa["trang_thai"], "CHO_DUYET")
        g_a = self.xem(dot)["context"]["basis_sha256"]
        # đồ thị B: sửa metadata L3 rồi chạy lại (không đổi vật liệu HĐ) — kết quả L3 công bố mới
        cs = self.svc.chung_tu_ds(A1, dot_id=dot)["co_so"]
        self.svc.chung_tu_sua(A1, run_id=h["run"], revision=cs["revision"], tai_lieu=[{"tep_id": h["nt"], "ngay": "2026-03-05"}],
                              expected_basis=cs["basis_sha256"], ly_do="BB nghiệm thu ký 05/03 theo bản gốc", khoa=self.K("C-sua"))
        chay_l3(self.svc, dot, self.K("C-l3-b"), cha=h["run"])
        x = self.xem(dot, DUYET)
        self.assertNotEqual(x["context"]["basis_sha256"], g_a)
        self.assertEqual(x["trang_thai"], "CAN_KIEM_LAI")
        self.assertIsNone(x["pdf"])  # ứng viên A chỉ còn lịch sử
        self.assertEqual([(p["id"], p["gan_hien_hanh"]) for p in x["pdf_lich_su"]], [(pa["pdf_id"], False)])
        than = self.than_chap_thuan(dot)
        self.assertEqual(self.loi(self.svc.duyet_chap_thuan, DUYET, **{**than, "ket_luan_id": kl_a["ket_luan_id"]}, khoa=self.K("C-ct-a")),
                         "M4_DUYET_KET_LUAN_CU")
        kl_b = self.ket_luan(dot, "C-kl-b")
        self.assertEqual(kl_b["ket_luan_revision"], 2)
        ct = self.chap_thuan(dot, "C-ct-b")
        self.assertEqual((ct["trang_thai"], ct["seal_id"], ct["kt_pending_id"]), ("CHO_PDF", None, None))  # KHÔNG seal PDF của đồ thị A
        self.assertEqual((self.dem(dot)["duyet_seal"], self.dem(dot)["duyet_kt_cho"], self.dem(dot)["duyet_kt_phong_bi"]), (0, 0, 0))
        x = self.xem(dot, DUYET)
        self.assertEqual((x["trang_thai"], x["kt"]["trang_thai"], x["pdf"]), ("CHO_PDF", "CHUA_CHUYEN", None))
        # CSDL: seal dùng PDF gắn kết luận A cho quyết định trên kết luận B bị FK chặn (giao dịch luôn hủy)
        chan = True
        try:
            with self.admin.transaction(force_rollback=True):
                self.admin.execute("""INSERT INTO m4.duyet_seal (phap_nhan_id, du_an_id, hop_dong_id, dot_id, phien_ban_id, quyet_dinh_id, ket_luan_id,
                                          pdf_id, graph_sha256, pdf_sha256, so_lieu, so_lieu_sha256, tao_boi, tao_boi_id)
                                      SELECT q.phap_nhan_id, q.du_an_id, q.hop_dong_id, q.dot_id, q.phien_ban_id, q.id, q.ket_luan_id, p.id, q.graph_sha256,
                                             p.raw_sha256, '{}'::jsonb, repeat('0', 64), 'KIEM_FK', q.duyet_boi_id
                                      FROM m4.duyet_quyet_dinh q JOIN m4.duyet_pdf p ON p.phien_ban_id = q.phien_ban_id
                                      WHERE q.dot_id = %s AND p.id = %s""", (dot, pa["pdf_id"]))
                chan = False
        except psycopg.errors.ForeignKeyViolation:
            chan = True
        self.assertTrue(chan, "seal dùng PDF gắn kết luận khác không bị CSDL chặn")
        self.assertEqual(self.dem(dot)["duyet_seal"], 0)
        # tải lại CÙNG bytes: ứng viên MỚI gắn kết luận B (không thừa kế gắn cũ) → seal dùng ứng viên mới
        pb = self.pdf(dot, raw, "C-pdf-b")
        self.assertEqual(pb["trang_thai"], "DA_SEAL", pb)
        self.assertNotEqual(pb["pdf_id"], pa["pdf_id"])
        r = self.seal_dot(dot)
        self.assertEqual((len(r), str(r[0]["pdf_id"]), str(r[0]["ket_luan_id"])), (1, pb["pdf_id"], kl_b["ket_luan_id"]))
        self.assertEqual(self.q("SELECT count(*) FROM m4.duyet_pdf WHERE dot_id = %s AND raw_sha256 = %s", (dot, hashlib.sha256(raw).hexdigest())), 2)

    # ------------------------------------------------------------------ P04
    def test_p04_vat_lieu_doi_sau_nop(self):
        h = self.ho_so("D")
        dot = h["dot"]
        kl = self.ket_luan(dot, "D-kl")
        v1 = kl["phien_ban_id"]
        anh = lambda: self.admin.execute("SELECT to_jsonb(v) FROM m4.duyet_phien_ban v WHERE id = %s", (v1,)).fetchone()[0]  # noqa: E731
        v1_truoc, rev0 = anh(), h["rev"]()
        tep = self.svc.tai_tep(A1, F.boq_xlsx(F.BOQ_DOI_SAU_NOP), du_an_id=h["du_an"], vai_tro="BOQ", ten="BOQ-doi-D.xlsx", media_type=F.MEDIA_XLSX,
                               khoa=self.K("D-boq2-tep"))["tep_id"]
        b2 = self.svc.boq_nhap(A1, hop_dong_id=h["hd"], revision=rev0, tep_id=tep, sheet="BOQ", hang_tieu_de=1, cot=dict(F.BOQ_COT), khoa=self.K("D-boq2"))
        self.assertEqual(b2["trang_thai"], "DA_MAP", b2)
        self.assertGreater(h["rev"](), rev0)
        x = self.xem(dot, DUYET)
        vl = next(c for c in x["can_cu"] if c["loai"] == "VAT_LIEU")
        self.assertEqual((x["trang_thai"], vl["trang_thai"], x["do_thi"]["vat_lieu"]["khop"]), ("CAN_KIEM_LAI", "DOI_SAU_NOP", False))
        truoc = self.dem(dot)
        self.assertEqual(self.loi(self.ket_luan, dot, "D-kl-2"), "M4_DUYET_CAN_PHIEN_BAN_MOI")
        self.assertEqual(self.loi(self.chap_thuan, dot, "D-ct"), "M4_DUYET_CAN_PHIEN_BAN_MOI")
        self.assertEqual(self.loi(self.pdf, dot, F.ho_so_dot_duyet_pdf("D-1"), "D-pdf"), "M4_DUYET_CAN_PHIEN_BAN_MOI")
        self.assertEqual(self.dem(dot), truoc)
        self.assertEqual(anh(), v1_truoc)  # v1 không bị sửa
        # phiên bản kế tiếp (SOAN) → L3 lại trên căn cứ mới → nộp/kiểm lại → v2 kết luận được
        c = self.xem(dot)["context"]
        pb = self.svc.duyet_phien_ban(A1, dot_id=dot, parent_version_id=v1, revision=c["revision"], expected_basis=c["basis_sha256"],
                                      ly_do="BOQ đổi sau nộp", khoa=self.K("D-pb"))
        v2 = pb["phien_ban_id"]
        self.assertEqual((pb["trang_thai"], pb["phien_ban_so"], pb["parent_id"]), ("CAN_KIEM_LAI", 2, v1))
        chay_l3(self.svc, dot, self.K("D-l3-2"), cha=h["run"])
        c = self.xem(dot, version_id=v2)["context"]
        nop = self.svc.duyet_phien_ban_nop(A1, dot_id=dot, version_id=v2, revision=0, expected_basis=c["basis_sha256"], khoa=self.K("D-nop2"))
        self.assertEqual(nop["trang_thai"], "CHO_KET_LUAN", nop)
        self.assertEqual(self.q("SELECT revision_ho_so FROM m4.duyet_phien_ban WHERE id = %s", (v2,)), h["rev"]())
        kl2 = self.ket_luan(dot, "D-kl-v2")
        self.assertEqual((kl2["phien_ban_id"], kl2["trang_thai"]), (v2, "CHO_DUYET"))
        x1 = self.xem(dot, DUYET, version_id=v1)
        self.assertEqual((x1["trang_thai"], x1["phien_ban_hien_hanh"]), ("CAN_KIEM_LAI", False))
        self.assertEqual(anh(), v1_truoc)

    # ------------------------------------------------------------------ P05
    def test_p05_replay_dong_thoi(self):
        h = self.ho_so("E")
        dot = h["dot"]
        than = than_ket_luan(self.xem(dot, REVIEW))
        k1 = self.svc.duyet_ket_luan(REVIEW, **than, khoa=self.K("E-kl"))
        truoc = self.dem(dot)
        k2 = self.svc.duyet_ket_luan(REVIEW, **than, khoa=self.K("E-kl"))
        self.assertEqual((k2["lap_lai"], k2["ket_luan_id"], k2["receipt_id"]), (True, k1["ket_luan_id"], k1["receipt_id"]))
        self.assertEqual(self.dem(dot), truoc)
        self.assertEqual(self.loi(self.svc.duyet_ket_luan, REVIEW, **{**than, "ly_do": "khác"}, khoa=self.K("E-kl")), "M4_IDEMPOTENCY_KHAC")
        than_ct = self.than_chap_thuan(dot)
        svcs = [self._svc_moi() for _ in range(2)]  # hai kết nối riêng; đăng ký cleanup ngay khi tạo
        kq, loi = self.song_song([lambda sv=sv, i=i: sv.duyet_chap_thuan(DUYET, **than_ct, khoa=self.K(f"E-ct-{i}")) for i, sv in enumerate(svcs)])
        self.assertEqual((len(kq), loi), (1, ["M4_DUYET_DA_CHAP_THUAN"]))
        self.assertEqual(self.dem(dot)["duyet_quyet_dinh"], 1)
        khoa_ct = next(self.K(f"E-ct-{i}") for i in (0, 1) if self._receipt(f"E-ct-{i}") == kq[0]["receipt_id"])  # bên thua không có biên nhận
        self.s["E_ct"] = (than_ct, khoa_ct)
        raw = F.ho_so_dot_duyet_pdf("E-1")
        than_p = self.than_pdf(dot, "ho_so_E.pdf")
        kq, loi = self.song_song([lambda sv=sv, i=i: sv.duyet_pdf(A1, raw, **than_p, khoa=self.K(f"E-pdf-{i}")) for i, sv in enumerate(svcs)])
        self.assertEqual((len(kq), loi), (1, ["M4_DUYET_DA_SEAL"]))
        self.assertEqual(kq[0]["trang_thai"], "DA_SEAL")
        d = self.dem(dot)
        self.assertEqual((d["duyet_pdf"], d["duyet_seal"], d["duyet_kt_cho"], d["duyet_kt_phong_bi"]), (1, 1, 1, 1))
        khoa_pdf = next(self.K(f"E-pdf-{i}") for i in (0, 1) if self._receipt(f"E-pdf-{i}") == kq[0]["receipt_id"])
        lai = self.svc.duyet_pdf(A1, raw, **than_p, khoa=khoa_pdf)
        self.assertEqual((lai["lap_lai"], lai["seal_id"], lai["pdf_id"]), (True, kq[0]["seal_id"], kq[0]["pdf_id"]))
        self.assertEqual(self.dem(dot), d)
        self.s["E"] = {**h, "pdf": kq[0]["pdf_id"], "v1": than_p["version_id"], "than_pdf": than_p, "khoa_pdf": khoa_pdf, "raw": raw}

    def _receipt(self, ten):
        r = self.admin.execute("SELECT id FROM m4.bien_nhan WHERE khoa = %s", (self.K(ten),)).fetchone()
        return None if r is None else str(r[0])

    # ------------------------------------------------------------------ P06
    def test_p06_dinh_chinh_cung_goc_kt(self):
        self.can("A")
        a = self.s["A"]
        dot, v1 = a["dot"], a["v1"]
        seal1 = self.admin.execute("SELECT to_jsonb(s) FROM m4.duyet_seal s WHERE dot_id = %s", (dot,)).fetchone()[0]
        c = self.xem(dot)["context"]
        pb = self.svc.duyet_phien_ban(A1, dot_id=dot, parent_version_id=v1, revision=c["revision"], expected_basis=c["basis_sha256"],
                                      ly_do="Đính chính hồ sơ đã duyệt", khoa=self.K("A-pb"))
        v2 = pb["phien_ban_id"]
        c = self.xem(dot, version_id=v2)["context"]
        self.svc.duyet_phien_ban_nop(A1, dot_id=dot, version_id=v2, revision=0, expected_basis=c["basis_sha256"], khoa=self.K("A-nop2"))
        self.ket_luan(dot, "A-kl-v2")
        self.assertEqual(self.chap_thuan(dot, "A-ct-v2")["trang_thai"], "CHO_PDF")
        p2 = self.pdf(dot, F.ho_so_dot_duyet_pdf("A-dinh-chinh"), "A-pdf-v2")
        self.assertEqual(p2["trang_thai"], "DA_SEAL", p2)
        rows = self.seal_dot(dot)
        self.assertEqual([r["thu_tu"] for r in rows], [1, 2])
        self.assertEqual((rows[1]["goc_id"], rows[1]["truoc_id"]), (rows[0]["goc_id"], rows[0]["pb_id"]))  # cùng gốc KT, phong bì con
        self.assertEqual(str(rows[1]["goc_id"]), p2["kt_pending_id"])
        self.assertEqual(self.q("SELECT count(*) FROM m4.duyet_kt_cho WHERE dot_id = %s", (dot,)), 1)
        self.assertEqual(self.admin.execute("SELECT to_jsonb(s) FROM m4.duyet_seal s WHERE id = %s", (seal1["id"],)).fetchone()[0], seal1)
        self.s["A"].update(v2=v2, pdf2=p2["pdf_id"])

    # ------------------------------------------------------------------ P07
    def test_p07_dto_trung_thuc(self):
        self.can("A")
        a = self.s["A"]
        if "v2" not in a:
            self.skipTest("P06 chưa có phiên bản đính chính — NOT_RUN")
        dot = a["dot"]
        x1, x2 = self.xem(dot, DUYET, version_id=a["v1"]), self.xem(dot, DUYET)
        json.dumps(x2, ensure_ascii=False)  # DTO tuần tự hóa được
        for x in (x1, x2):
            for k in ("can_cu", "review_refs", "phat_hien", "dong_nt", "lich_su", "phien_ban", "pdf_lich_su", "ket_luan_lich_su"):
                self.assertIsInstance(x[k], list, k)
            self.assertTrue(all({"version_id", "so", "parent_version_id", "trang_thai", "moi_nhat"} <= set(v) for v in x["phien_ban"]))
            self.assertTrue(all(set(e) == {"hanh_dong", "actor", "luc", "chi_tiet"} for e in x["lich_su"]))
            self.assertTrue({"actor", "luc", "dong_nt", "khop_co_so"} <= set(x["ket_luan"]))
            self.assertTrue({"actor", "luc", "khop_co_so"} <= set(x["quyet_dinh"]))
            self.assertTrue({"name", "sha256", "byte_length", "ket_luan_id", "graph_sha256", "actor", "luc"} <= set(x["pdf"]))
            self.assertNotIn("ten", x["pdf"])
            self.assertEqual([c["loai"] for c in x["can_cu"]], ["PHIEN_BAN", "VAT_LIEU", "REVIEW_L3", "REVIEW_L2", "TRUOC_DA_DUYET", "THUE", "DO_THI"])
            self.assertEqual(x["trang_thai"], "DA_SEAL")
        self.assertEqual((x1["phien_ban_hien_hanh"], x1["kt"]["phong_bi_hien_hanh"], x1["pdf"]["id"]), (False, False, a["pdf"]))
        self.assertIsNotNone(x1["kt"]["ly_do"])
        self.assertEqual((x2["phien_ban_hien_hanh"], x2["kt"]["phong_bi_hien_hanh"], x2["pdf"]["id"]), (True, True, a["pdf2"]))
        self.assertEqual(x1["kt"]["pending_id"], x2["kt"]["pending_id"])
        self.assertEqual([v["version_id"] for v in x2["phien_ban"]], [a["v1"], a["v2"]])
        self.assertEqual(x2["quyen"], {"xem": True, "ket_luan": True, "duyet": True, "tai_pdf": True, "phien_ban": False})
        self.assertEqual(self.xem(dot, XEM)["quyen"], {"xem": True, "ket_luan": False, "duyet": False, "tai_pdf": False, "phien_ban": False})
        self.assertEqual(self.xem(dot, A1)["quyen"]["duyet"], False)
        for ai in (XEM, REVIEW):  # thấy đợt nhưng cờ tai_pdf=false → tải bị chặn đúng như DTO
            self.assertEqual(self.loi(self.svc.duyet_pdf_tai, ai, a["v1"], a["pdf"]), "M4_DUYET_PHAM_VI")
        for ai in (A2, B1):
            self.assertEqual(self.loi(self.xem, dot, ai), "M4_DUYET_KHONG_THAY")
            self.assertEqual(self.loi(self.svc.duyet_pdf_tai, ai, a["v1"], a["pdf"]), "M4_DUYET_KHONG_THAY")

    # ------------------------------------------------------------------ P08
    def test_p08_bypass_sql_login_ung_dung(self):
        self.can("E")
        e = self.s["E"]
        web = self.web_raw  # login ứng dụng (IN app_web), autocommit — lệnh lỗi không giữ giao dịch hỏng
        truoc = self.dem()
        lenh = (("SELECT m4.duyet_chap_thuan('k', '{}'::jsonb, %s::uuid, %s::uuid, 1, repeat('0',64), repeat('0',64), %s::uuid, 'x')",
                 (e["dot"], e["v1"], e["pdf"])),
                ("SELECT m4._duyet_seal(%s::uuid, repeat('0',64), %s::uuid)", (e["v1"], e["pdf"])),
                ("SELECT m4.duyet_khoa(%s::uuid, %s::uuid, 'CHAP_THUAN')", (e["dot"], e["v1"])))
        for sql, p in lenh:  # EXECUTE thu hồi khỏi PUBLIC; nếu môi trường cấp lại thì cổng chủ bảng trong hàm vẫn chặn
            self.assertIn(self.loi(web.execute, sql, p), ("InsufficientPrivilege", "M4_CHI_MAY_CHU_NGUON"), sql)
        for sql in ("INSERT INTO m4.duyet_quyet_dinh (phien_ban_id) VALUES (%s::uuid)", "UPDATE m4.duyet_seal SET tao_boi = 'x' WHERE phien_ban_id = %s::uuid",
                    "DELETE FROM m4.duyet_kt_phong_bi WHERE phien_ban_id = %s::uuid"):
            self.assertEqual(self.loi(web.execute, sql, (e["v1"],)), "InsufficientPrivilege", sql)
        self.assertEqual(self.dem(), truoc)

    # ------------------------------------------------------------------ P09 (cuối: thu hồi không đảo ngược)
    def test_p09_thu_hoi_chan_replay_va_tai(self):
        self.can("E", "E_ct")
        e = self.s["E"]
        dot = e["dot"]
        self.assertEqual(self.svc.duyet_pdf_tai(DUYET, e["v1"], e["pdf"])[2], e["raw"])  # trước thu hồi: tải được
        qid = self.q("""SELECT q.id FROM m4.quyen_du_an q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                        WHERE n.dang_nhap = %s AND q.vai = 'DUYET' AND q.thu_hoi_luc IS NULL""", (DUYET,))
        self.assertIsNotNone(qid)
        self.admin.execute("SELECT m4.thu_hoi_quyen_du_an(%s, 'MO_PHONG_QUAN_TRI_TEST', 'Kiểm thu hồi M4-02C')", (qid,))
        truoc = self.dem()
        than_ct, khoa_ct = self.s["E_ct"]
        self.assertEqual(self.loi(self.svc.duyet_chap_thuan, DUYET, **than_ct, khoa=khoa_ct), "M4_DUYET_KHONG_THAY")  # replay đúng body cũ
        self.assertEqual(self.loi(self.xem, dot, DUYET), "M4_DUYET_KHONG_THAY")
        self.assertEqual(self.loi(self.svc.duyet_pdf_tai, DUYET, e["v1"], e["pdf"]), "M4_DUYET_KHONG_THAY")
        self.assertEqual(self.dem(), truoc)
        self.assertEqual(self.svc.duyet_pdf_tai(A1, e["v1"], e["pdf"])[2], e["raw"])  # SOAN vẫn tải được
        self.assertEqual(self.q("SELECT trang_thai FROM master.nguoi_dung WHERE dang_nhap = %s", (DUYET,)), "HOAT_DONG")


class DungHoSoDoiTacThuanTests(unittest.TestCase):
    """Chỉ kiểm bước nháp mới của helper; chặn tại trích, không nối PG/engine #6."""

    def dung_den_trich(self, doi_tac=None, *, mapping=True):
        from unittest.mock import Mock, patch
        svc, admin = Mock(), Mock()
        svc.tao_hop_dong.return_value = {"hop_dong_id": "hd-demo"}
        svc.tai_tep.return_value = {"tep_id": "tep-demo"}
        svc.master_doi_tac.return_value = {"items": [{"doi_tac_id": "dt-demo", "mapping_id": "map-demo" if mapping else None,
                                                    "expected_mapping": "a" * 64}]}
        svc.chi_tiet.return_value = {"master_can_cu": {"revision": 1, "expected_master": "b" * 64}}
        svc.trich.side_effect = unittest.SkipTest("CHAN_TRICH_THUAN")
        q = ["du-an-demo", "331.DEMO_M2_SUPPLIER", 2, 2] if doi_tac is not None else ["du-an-demo", 1, 1]
        with patch(__name__ + "._q1", side_effect=q), patch.object(F, "hop_dong_docx", return_value=b"demo"):
            with self.assertRaisesRegex(unittest.SkipTest if mapping else AssertionError,
                                        "CHAN_TRICH_THUAN" if mapping else "thiếu mapping"):
                dung_ho_so(svc, admin, lambda x: x, "DC1", "luot-demo", gan_doi_tac=doi_tac)
        return svc

    def test_mac_dinh_none_khong_doc_hay_gan_doi_tac(self):
        svc = self.dung_den_trich()
        svc.master_doi_tac.assert_not_called()
        svc.chi_tiet.assert_not_called()
        svc.gan_doi_tac_hop_dong.assert_not_called()

    def test_gan_bang_actor_demo_va_cas_truoc_trich_nop(self):
        svc = self.dung_den_trich("dt-demo")
        svc.gan_doi_tac_hop_dong.assert_called_once_with(
            A1, hop_dong_id="hd-demo", doi_tac_id="dt-demo", mapping_id="map-demo", revision=1,
            expected_master="b" * 64, expected_mapping="a" * 64,
            ly_do="Gắn đối tác DEMO của bản sao trước khi nộp hồ sơ test 03B", khoa="DC1-gan-doi-tac")
        ten = [c[0] for c in svc.mock_calls]
        self.assertLess(ten.index("gan_doi_tac_hop_dong"), ten.index("trich"))
        self.assertEqual(svc.gan_tep_hop_dong.call_args.kwargs["revision"], 2)
        svc.nop.assert_not_called()

    def test_mapping_mo_ho_khong_tu_chon_de_gan(self):
        svc = self.dung_den_trich("dt-demo", mapping=False)
        svc.gan_doi_tac_hop_dong.assert_not_called()
        svc.trich.assert_not_called()
        svc.nop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
