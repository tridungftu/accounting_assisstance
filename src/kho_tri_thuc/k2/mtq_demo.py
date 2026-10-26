"""MTQ-5a: mẫu DEMO một lần, công bố nhưng KHÔNG kích hoạt.

Chỉ bootstrap tin cậy qua chủ bảng; không dùng dịch vụ MTQ-2. Pháp nhân và
dự án lấy từ seed CRM/M4, không tạo master thay thế. Phòng dùng mtq_phong
duy nhất: tái dùng mã đã có, thiếu mới tạo bằng lệnh PHONG của MTQ-1.
Không cấp quyền legacy cho actor mới, không đổi các actor/ca âm seed cũ.
"""

from __future__ import annotations

import json
import re
import uuid

from . import crm_demo, m4_demo

MARKER = "demo_seed_mtq_v1"
LY_DO = "MTQ-5a: mẫu DEMO, đã công bố, chưa bật; không phải quyền dữ liệu thật"
ADMIN = "MO_PHONG_MTQ_ADMIN"
# Vai cũ chỉ để tương thích CHECK danh tính, không sinh grant legacy.
NGUOI_DUNG = (
    ("MO_PHONG_MTQ_THUC_HIEN_1", "Người thực hiện 1 DEMO", "THUC_HIEN_1", "BAN_HANG"),
    ("MO_PHONG_MTQ_THUC_HIEN_2", "Người thực hiện 2 DEMO", "THUC_HIEN_2", "KE_TOAN"),
    ("MO_PHONG_MTQ_TRUONG_PHONG", "Trưởng phòng DEMO", "TRUONG_PHONG", "KE_TOAN_TRUONG"),
    ("MO_PHONG_MTQ_CFO", "CFO DEMO", "CFO", "CFO"),
    ("MO_PHONG_MTQ_NGUOI_XEM", "Người xem DEMO", "NGUOI_XEM", "XEM"),
)
GIOI_HAN_VND = {"THUC_HIEN_1": None, "THUC_HIEN_2": None,
                "TRUONG_PHONG": 500_000_000, "CFO": None, "NGUOI_XEM": None}
PHONG = (("KINH_DOANH", "Kinh doanh DEMO"), ("KE_TOAN", "Kế toán DEMO"), ("DU_AN", "Dự án DEMO"))
# Whitelist hữu hạn theo màn/phòng. Không tự mở tick khi catalog thêm màn.
O_MAU = {
    "KINH_DOANH": {
        "THUC_HIEN_1": (("CRM", "TIEP_NHAN", "XEM LAP SUA"), ("CRM", "G2_BAO_GIA", "XEM LAP SUA")),
        "THUC_HIEN_2": (("CRM", "TIEP_NHAN", "XEM KIEM"), ("CRM", "G5_G6_KIEM_KY", "XEM KIEM")),
        "TRUONG_PHONG": (("CRM", "TIEP_NHAN", "XEM DUYET"),),
        "CFO": (("CRM", "TIEP_NHAN", "XEM DUYET"), ("CRM", "G5_G6_KIEM_KY", "XEM DUYET")),
        "NGUOI_XEM": (("CRM", "TIEP_NHAN", "XEM"), ("CRM", "G2_BAO_GIA", "XEM")),
    },
    "KE_TOAN": {
        "THUC_HIEN_1": (("M1", "TIEN", "XEM LAP SUA"), ("M2", "HOA_DON", "XEM LAP")),
        "THUC_HIEN_2": (("CRM", "G5_G6_KIEM_KY", "XEM KIEM"),),
        "TRUONG_PHONG": (("CRM", "G5_G6_KIEM_KY", "XEM DUYET"),),
        # Ca âm BOTH M2+M5: chỉ tick phía M2 của L11, không tick M5.
        "CFO": (("M2", "HOA_DON", "XEM DUYET"), ("M2", "L11", "XEM DUYET")),
        "NGUOI_XEM": (("M1", "TIEN", "XEM"), ("M1", "XEM_TIEN", "XEM"), ("M2", "HOA_DON", "XEM")),
    },
    "DU_AN": {
        "THUC_HIEN_1": (("M4", "HO_SO", "XEM LAP SUA"),),
        "THUC_HIEN_2": (("M4", "02A_REVIEW", "XEM KIEM"), ("M4", "02B_CHUNG_TU", "XEM KIEM")),
        "TRUONG_PHONG": (("M4", "02C_DUYET", "XEM DUYET"),),
        "CFO": (("M4", "02C_DUYET", "XEM DUYET"),),
        "NGUOI_XEM": (("M4", "HO_SO", "XEM"), ("M4", "PDF_DA_DUYET", "XEM")),
    },
}
_GUCS = ("ktt.nguoi_dung_id", "ktt.nguoi_dung_dang_nhap", "ktt.mtq_request", "ktt.mtq_lenh", "ktt.mtq_ly_do")


def _mot(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return None if row is None else row[0]


def _ghi(conn, lenh, data, revision=0):
    return _mot(conn, "SELECT master.mtq_cau_hinh_ghi(%s,%s,%s::jsonb,%s,%s)",
                (uuid.uuid4(), lenh, json.dumps(data, ensure_ascii=False), revision, LY_DO))


def _sua_nhap(conn, ban, lenh, data):
    kq = _ghi(conn, lenh, {**data, "phien_ban_id": ban["id"]}, ban["revision"])
    ban.update(kq["phien_ban"])
    return kq["doi_tuong"]


def _phan_giai(conn):
    pn, du_an = {}, {}
    for ma, *_ in crm_demo.PHAP_NHAN:
        k = _mot(conn, "SELECT id FROM master.phap_nhan WHERE ma=%s", (ma,))
        if k is None:
            return None
        pn[ma] = str(k)
    # Hai dự án cùng PN A, một dự án PN B; chỉ dùng master từ seed M4.
    for ma_pn, ma, _ in m4_demo.DU_AN:
        k = _mot(conn, "SELECT id FROM master.du_an WHERE phap_nhan_id=%s AND ma_junsky=%s", (pn[ma_pn], ma))
        if k is None:
            return None
        du_an.setdefault(ma_pn, []).append(str(k))
    return pn, du_an


def khoi_tao(admin_conn, *, demo=False) -> dict:
    """Chỉ gọi từ bootstrap DEMO đã kiểm DSN; mặc định không được phép chạy.

    Cần autocommit/chủ bảng. Mọi ghi (kể cả marker/audit) trong một giao dịch;
    lỗi rollback toàn bộ. Marker HOẶC bất kỳ actor đã có đều chặn cấp lại.
    Không có dòng mtq_kich_hoat tương đương tắt theo MTQ-1.
    """
    if demo is not True:
        return {"trang_thai": "KHONG_PHAI_DEMO"}
    db = _mot(admin_conn, "SELECT current_database()")
    if not isinstance(db, str) or not re.fullmatch(r"(?:kho_crm_demo[a-z0-9_]*|kho_test_[a-z0-9_]+)", db):
        return {"trang_thai": "KHONG_PHAI_DEMO"}
    with admin_conn.transaction():
        if not _mot(admin_conn, "SELECT to_regclass('master.mtq_admin') IS NOT NULL"):
            return {"trang_thai": "CHUA_SAN_SANG", "can_anh": "Cần migrate MTQ-1 trước."}
        # Cùng khóa với toàn bộ lệnh MTQ-1: hai bootstrap không thể cùng seed.
        admin_conn.execute("SELECT pg_advisory_xact_lock(742601, 1)")
        if _mot(admin_conn, "SELECT 1 FROM master.he_thong WHERE key=%s", (MARKER,)):
            return {"trang_thai": "DA_SEED", "marker": True}
        if not _mot(admin_conn, "SELECT 1 FROM master.he_thong WHERE key=%s", (crm_demo.MARKER,)) or _mot(
                admin_conn, "SELECT EXISTS (SELECT 1 FROM master.phap_nhan WHERE NOT (ma=ANY(%s)))",
                ([p[0] for p in crm_demo.PHAP_NHAN],)):
            return {"trang_thai": "KHONG_PHAI_DEMO"}
        if not _mot(admin_conn, """SELECT bool_and(pg_get_userbyid(c.relowner) = current_user
                AND pg_has_role(session_user, c.relowner, 'MEMBER'))
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='master' AND c.relname IN ('mtq_admin','mtq_phong','mtq_phien_ban')"""):
            return {"trang_thai": "CHUA_SAN_SANG", "can_anh": "Cần kết nối đúng chủ bảng MTQ."}
        if _mot(admin_conn, "SELECT EXISTS (SELECT 1 FROM master.nguoi_dung WHERE dang_nhap=ANY(%s))",
                ([ADMIN, *(n[0] for n in NGUOI_DUNG)],)) or _mot(admin_conn, """SELECT
                EXISTS (SELECT 1 FROM master.mtq_admin) OR EXISTS (SELECT 1 FROM master.mtq_phien_ban)
                OR EXISTS (SELECT 1 FROM master.mtq_gan_vai)"""):
            return {"trang_thai": "XUNG_DOT", "can_anh": "Đã có actor/cấu hình MTQ; không ghi đè hoặc cấp bù."}
        ref = _phan_giai(admin_conn)
        if ref is None:
            return {"trang_thai": "CHUA_SAN_SANG", "can_anh": "Thiếu master CRM/M4 DEMO; không tạo master thứ hai."}
        pn, du_an = ref
        phong = {}
        for ma_pn, pn_id in pn.items():
            rows = admin_conn.execute("SELECT ma,id,hoat_dong FROM master.mtq_phong WHERE phap_nhan_id=%s", (pn_id,)).fetchall()
            if any(ma not in dict(PHONG) or not active for ma, _, active in rows):
                return {"trang_thai": "XUNG_DOT", "can_anh": "Phòng hiện có khác mẫu; không sửa phòng đã khai báo."}
            phong[ma_pn] = {ma: str(k) for ma, k, _ in rows}
        cu = {k: _mot(admin_conn, "SELECT current_setting(%s,true)", (k,)) for k in _GUCS}
        admin_id = _mot(admin_conn, """INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro,mo_phong)
                            VALUES ('Admin MTQ DEMO',%s,'XEM',true) RETURNING id""", (ADMIN,))
        # Ghim danh tính chỉ định trước bootstrap để audit không dùng actor phiên cũ.
        for k, v in zip(_GUCS[:2], (str(admin_id), ADMIN)):
            admin_conn.execute("SELECT set_config(%s,%s,true)", (k, v))
        admin_conn.execute("SELECT master.mtq_bootstrap_admin(%s,%s,%s)", (admin_id, uuid.uuid4(), LY_DO))
        actors = {}
        for login, ten, vai, vai_cu in NGUOI_DUNG:
            actors[vai] = str(_mot(admin_conn, """INSERT INTO master.nguoi_dung (ten,dang_nhap,vai_tro,mo_phong)
                                         VALUES (%s,%s,%s,true) RETURNING id""", (ten, login, vai_cu)))
        for ma_pn, pn_id in pn.items():
            for ma, ten in PHONG:
                if ma not in phong[ma_pn]:
                    phong[ma_pn][ma] = _ghi(admin_conn, "PHONG", {"phap_nhan_id": pn_id, "ma": ma, "ten": ten})["id"]
            ban = _ghi(admin_conn, "NHAP", {"phap_nhan_id": pn_id})
            for ma, _ in PHONG:
                phong_id = phong[ma_pn][ma]
                for vai in GIOI_HAN_VND:
                    dong = _sua_nhap(admin_conn, ban, "DONG", {"phong_id": phong_id, "vai": vai, "gioi_han_vnd": GIOI_HAN_VND[vai]})
                    for module, man, actions in O_MAU[ma][vai]:
                        for hd in actions.split():
                            _sua_nhap(admin_conn, ban, "O", {"dong_id": dong["id"], "module": module, "man": man,
                                                           "hanh_dong": hd, "cho_phep": True})
                    gan = _ghi(admin_conn, "GAN_VAI", {"nguoi_dung_id": actors[vai], "phap_nhan_id": pn_id, "phong_id": phong_id, "vai": vai})
                    # Chỉ phòng Dự án được phạm vi dự án; CFO có A1+A2,
                    # các vai còn lại chỉ A1: ca âm khác dự án cùng pháp nhân.
                    scopes = [("PHAP_NHAN", pn_id)] if ma != "DU_AN" else [
                        ("DU_AN", k) for k in (du_an[ma_pn] if vai == "CFO" else du_an[ma_pn][:1])]
                    for loai, khoa in scopes:
                        _ghi(admin_conn, "PHAM_VI", {"gan_vai_id": gan["id"], "phap_nhan_id": pn_id, "loai": loai, "khoa": khoa})
            _sua_nhap(admin_conn, ban, "CONG_BO", {})
        admin_conn.execute("INSERT INTO master.he_thong (key,value) VALUES (%s,'v1')", (MARKER,))
        for k, v in cu.items():
            admin_conn.execute("SELECT set_config(%s,%s,true)", (k, v or ""))
    return {"trang_thai": "DU", "marker": True, "actor": 6, "phien_ban": len(pn), "da_cong_bo": True, "bat": False}
