"""Khởi tạo DEMO CRM-41-02 G1/G7 (chủ CSDL, sau migrate 18 + seed CRM DEMO) theo literal readonly `docs/CRM-41-02-DEMO-INPUTS.json`:
8 actor MO_PHONG_CRM_G_* mới + grant PN/module/V4, danh mục trường DEMO_CRM_G1_FIELDS_V1@1 cho TYPE_A_V2/TYPE_B_V2, 2 phân công CRM_MAU_TAI
(một hiện hành, một đã thu hồi — giữ hàng). Chỉ là khai báo kỹ thuật tổng hợp, không phải policy production.

- Phân giải master có sẵn theo khóa nghiệp vụ (PN_DEMO_A/B, DT-KCN-THUE-DAT-DEMO@2, DT-NHA-O-DEMO@2, DA_KCN_DEMO, DA_NHA_DEMO); thiếu/mơ hồ →
  CHUA_SAN_SANG, không bịa UUID, không chèn master để "cho đủ".
- Lần đầu (chưa marker, chưa actor khai báo nào): tạo actor/grant/phân công trong MỘT giao dịch. Mở lại (marker HOẶC bất kỳ actor khai báo nào
  đã có) → chỉ kiểm, không cấp bù/cấp lại grant/phân công thiếu hoặc đã thu hồi. Không đổi actor/grant cũ.
- Danh mục: định danh ref+revision+loại hình+khóa; vắng hẳn → chèn; có mà khác nội dung bất biến → XUNG_DOT (không ghi đè).
- KHÔNG seed mẫu/phiên bản/ánh xạ/lần kiểm/duyệt CFO, không bộ chuẩn G7, không việc K5 hoàn tất, không grant production.
Trạng thái: DU / THIEU / DA_THU_HOI / XUNG_DOT / CHUA_SAN_SANG.
"""

from __future__ import annotations

import json

MARKER = "demo_seed_crm_g1_g7_v1"
TIEN_TO = "MO_PHONG_"
CAP_BOI = "SEED:" + MARKER
PHAP_NHAN = {"PN_A": "PN_DEMO_A", "PN_B": "PN_DEMO_B"}
LOAI_HINH = {"TYPE_A_V2": ("PN_A", "DT-KCN-THUE-DAT-DEMO", 2), "TYPE_B_V2": ("PN_B", "DT-NHA-O-DEMO", 2)}
DU_AN = {"PROJECT_A": ("PN_A", "DA_KCN_DEMO"), "PROJECT_B": ("PN_B", "DA_NHA_DEMO")}
DANH_MUC_REF, DANH_MUC_REV = "DEMO_CRM_G1_FIELDS_V1", 1
DANH_MUC_LOAI = ("TYPE_A_V2", "TYPE_B_V2")
TRUONG = (  # khoa, nhan, nhom, kieu, dinh_dang, nguon, pii, bat_buoc, xem_thu (dữ liệu giả)
    ("so_hop_dong", "Số hợp đồng", "HOP_DONG", "text", "TEXT", "HOP_DONG", False, True, "HD-DEMO-G1-0001"),
    ("ten_hien_thi_demo", "Họ tên hiển thị — DEMO", "DOI_TUONG", "text", "TEXT_ESCAPED", "KHAC", True, False, "NGUOI DEMO <KHONG PHAI NGUOI THAT>"),
    ("ngay_ky", "Ngày ký", "HOP_DONG", "ngay", "dd/MM/yyyy", "HOP_DONG", False, True, "2026-10-21"),
    ("gia_tri_hop_dong", "Giá trị hợp đồng — DEMO, không tính nghĩa vụ", "GIA", "tien", "EXPLICIT_MINOR_AND_CURRENCY", "GIA", False, True,
     {"amount_minor": "100000000", "currency": "VND"}),
)
NGUOI_DUNG = (  # đăng nhập, vai trò, {PN ref: (module, loại việc duyệt)}
    ("MO_PHONG_CRM_G_TAI_A", "XEM", {"PN_A": (["CRM"], [])}),
    ("MO_PHONG_CRM_G_KT_A", "KE_TOAN", {"PN_A": (["CRM"], [])}),
    ("MO_PHONG_CRM_G_CFO_A", "CFO", {"PN_A": (["CRM"], ["V4"])}),
    ("MO_PHONG_CRM_G_BH_A", "BAN_HANG", {"PN_A": (["CRM"], [])}),
    ("MO_PHONG_CRM_G_CFO_NO_V4_A", "CFO", {"PN_A": (["CRM"], [])}),
    ("MO_PHONG_CRM_G_KT_NO_CRM_A", "KE_TOAN", {"PN_A": (["M1"], [])}),
    ("MO_PHONG_CRM_G_TAI_REVOKED_A", "XEM", {"PN_A": (["CRM"], [])}),
    ("MO_PHONG_CRM_G_CFO_B", "CFO", {"PN_B": (["CRM"], ["V4"])}),
)
PHAN_CONG = (  # actor, PN ref, module, hành động, loại hình ref, trạng thái khai báo
    ("MO_PHONG_CRM_G_TAI_A", "PN_A", "CRM", "CRM_MAU_TAI", "TYPE_A_V2", "ACTIVE"),
    ("MO_PHONG_CRM_G_TAI_REVOKED_A", "PN_A", "CRM", "CRM_MAU_TAI", "TYPE_A_V2", "REVOKED"),
)
LY_DO_THU_HOI = "DEMO CRM-41-02: phân công khai báo ở trạng thái đã thu hồi (ca âm); không phải quyết định lịch sử"
assert all(n[0].startswith(TIEN_TO) for n in NGUOI_DUNG)


def dang_nhap_crm_g() -> list[str]:
    return [n[0] for n in NGUOI_DUNG]


def _mot(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return None if row is None else row[0]


def _duy_nhat(conn, sql, params):
    rows = conn.execute(sql, params).fetchall()
    return rows[0][0] if len(rows) == 1 else None


def _phan_giai(conn) -> tuple[dict, list]:
    ref, thieu = {}, []
    for r, ma in PHAP_NHAN.items():
        ref[r] = _duy_nhat(conn, "SELECT id FROM master.phap_nhan WHERE ma = %s", (ma,))
    for r, (pn, ma, pb) in LOAI_HINH.items():
        ref[r] = None if ref[pn] is None else _duy_nhat(conn, """SELECT id FROM master.loai_hinh_doanh_thu WHERE phap_nhan_id = %s AND ma = %s
                                                                 AND phien_ban = %s""", (ref[pn], ma, pb))
    for r, (pn, ma) in DU_AN.items():
        ref[r] = None if ref[pn] is None else _duy_nhat(conn, "SELECT id FROM master.du_an WHERE phap_nhan_id = %s AND ma_junsky = %s", (ref[pn], ma))
    thieu = [r for r, v in ref.items() if v is None]
    return ref, thieu


def _danh_muc(conn, loai_id) -> str:
    """Chèn danh mục nếu vắng hẳn; có đủ đúng → DU; có mà khác/thiếu một phần → XUNG_DOT (không ghi đè)."""
    cu = {r[0]: tuple(r[1:]) for r in conn.execute("""SELECT khoa, nhan, nhom, kieu, dinh_dang, nguon, pii, bat_buoc, xem_thu
                                                       FROM master.crm_danh_muc_truong WHERE loai_hinh_id = %s AND danh_muc_ref = %s AND revision = %s""",
                                                    (loai_id, DANH_MUC_REF, DANH_MUC_REV))}
    muon = {t[0]: tuple(t[1:]) for t in TRUONG}
    if not cu:
        pn = _mot(conn, "SELECT phap_nhan_id FROM master.loai_hinh_doanh_thu WHERE id = %s", (loai_id,))
        for khoa, nhan, nhom, kieu, dd, nguon, pii, bb, xem in TRUONG:
            conn.execute("""INSERT INTO master.crm_danh_muc_truong (phap_nhan_id, loai_hinh_id, danh_muc_ref, revision, khoa, nhan, nhom, kieu, dinh_dang,
                                                                     nguon, pii, bat_buoc, xem_thu)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
                         (pn, loai_id, DANH_MUC_REF, DANH_MUC_REV, khoa, nhan, nhom, kieu, dd, nguon, pii, bb, json.dumps(xem, ensure_ascii=False)))
        return "DA_TAO"
    return "DU" if cu == muon else "XUNG_DOT"


def _trang_thai_actor(conn, ref: dict, dang_nhap, vai_tro, grants) -> dict:
    """Đối chiếu khai báo với CSDL hiện hành, không ghi gì."""
    thieu, thu_hoi, sai = [], [], []
    nd = conn.execute("SELECT id, vai_tro, mo_phong, trang_thai FROM master.nguoi_dung WHERE dang_nhap = %s", (dang_nhap,)).fetchone()
    if nd is None:
        return {"dang_nhap": dang_nhap, "trang_thai": "THIEU", "thieu": ["nguoi_dung"], "da_thu_hoi": [], "sai": []}
    if (nd[1], nd[2], nd[3]) != (vai_tro, True, "HOAT_DONG"):
        sai.append(f"nguoi_dung khác khai báo ({nd[1]}, mo_phong={nd[2]}, {nd[3]})")
    for pn_ref, (mod, duyet) in grants.items():
        r = conn.execute("SELECT module, duyet_loai_viec FROM master.phan_quyen WHERE nguoi_dung_id = %s AND phap_nhan_id = %s",
                         (nd[0], ref[pn_ref])).fetchone()
        if r is None:
            thieu.append(f"phan_quyen {pn_ref}")
        elif (sorted(r[0] or []), sorted(r[1] or [])) != (sorted(mod), sorted(duyet)):
            sai.append(f"phan_quyen {pn_ref} khác khai báo")
    for a, pn_ref, module, hd, loai_ref, muon in PHAN_CONG:
        if a != dang_nhap:
            continue
        rows = conn.execute("""SELECT thu_hoi_luc IS NULL FROM master.phan_cong_hanh_dong WHERE nguoi_dung_id = %s AND phap_nhan_id = %s AND module = %s
                               AND hanh_dong = %s AND loai_hinh_id IS NOT DISTINCT FROM %s""", (nd[0], ref[pn_ref], module, hd, ref[loai_ref])).fetchall()
        hien_hanh = any(x[0] for x in rows)
        if muon == "ACTIVE" and not hien_hanh:
            (thu_hoi if rows else thieu).append(f"{hd}:{loai_ref}")
        elif muon == "REVOKED":
            if hien_hanh:
                sai.append(f"{hd}:{loai_ref} đang hiện hành nhưng khai báo đã thu hồi")
            elif not rows:
                thieu.append(f"{hd}:{loai_ref} (hàng đã thu hồi)")
    tt = "XUNG_DOT" if sai else "DA_THU_HOI" if thu_hoi else "THIEU" if thieu else "DU"
    return {"dang_nhap": dang_nhap, "trang_thai": tt, "thieu": thieu, "da_thu_hoi": thu_hoi, "sai": sai}


# CRM-41-03 (bổ sung, chỉ thêm): điều khoản tham chiếu DEMO cho bản in báo giá theo loại hình DEMO — nội dung tổng hợp, ghi rõ DEMO, không phải
# chính sách giá/thanh toán production. Không seed báo giá/bản soạn/mẫu/duyệt/FX/phí.
DIEU_KHOAN_G2 = (("TYPE_A_V2", "THAM_CHIEU_DEMO", "Báo giá DEMO chỉ để tham khảo; giá, lịch và điều kiện thanh toán chỉ ràng buộc khi hai bên ký "
                                                  "hợp đồng chính thức theo mẫu đã duyệt."),
                 ("TYPE_B_V2", "THAM_CHIEU_DEMO", "Báo giá DEMO chỉ để tham khảo; giá, lịch, phí bảo trì và điều kiện thanh toán chỉ ràng buộc khi "
                                                  "hai bên ký hợp đồng chính thức theo mẫu đã duyệt."))


def _g2g3(conn, ref: dict) -> str:
    """Chèn điều khoản DEMO nếu vắng; có mà khác → XUNG_DOT (không ghi đè). Schema 21 chưa có → CHUA_SAN_SANG."""
    if _mot(conn, "SELECT to_regclass('master.crm_bao_gia_dieu_khoan') IS NOT NULL") is not True:
        return "CHUA_SAN_SANG"
    kq = []
    for loai_ref, ma, noi_dung in DIEU_KHOAN_G2:
        cu = _mot(conn, "SELECT noi_dung FROM master.crm_bao_gia_dieu_khoan WHERE loai_hinh_id = %s AND ma = %s", (ref[loai_ref], ma))
        if cu is None:
            pn = _mot(conn, "SELECT phap_nhan_id FROM master.loai_hinh_doanh_thu WHERE id = %s", (ref[loai_ref],))
            conn.execute("INSERT INTO master.crm_bao_gia_dieu_khoan (phap_nhan_id, loai_hinh_id, ma, noi_dung) VALUES (%s,%s,%s,%s)",
                         (pn, ref[loai_ref], ma, noi_dung))
            kq.append("DA_TAO")
        else:
            kq.append("DU" if cu == noi_dung else "XUNG_DOT")
    return "XUNG_DOT" if "XUNG_DOT" in kq else "DA_TAO" if "DA_TAO" in kq else "DU"


def khoi_tao(admin_conn) -> dict:
    """admin_conn: psycopg autocommit, chủ CSDL (tuple row). Chỉ thêm, một lần; KHÔNG raise khi chưa sẵn sàng — trả trạng thái trung thực."""
    dem = {"actor": 0, "phan_quyen": 0, "danh_muc": 0, "phan_cong": 0}
    with admin_conn.transaction():
        if _mot(admin_conn, "SELECT to_regclass('master.crm_mau_phien_ban') IS NOT NULL") is not True:
            return {"trang_thai": "CHUA_SAN_SANG", "ly_do": "Schema CRM-G chưa có — migrate 18 trước khi seed G1/G7 DEMO.", "dem": dem, "actor": []}
        ref, thieu = _phan_giai(admin_conn)
        if thieu:
            return {"trang_thai": "CHUA_SAN_SANG", "ly_do": "Thiếu hoặc mơ hồ master DEMO: " + ", ".join(thieu) + " — không tạo master mới.",
                    "dem": dem, "actor": []}
        danh_muc = {}
        for r in DANH_MUC_LOAI:
            danh_muc[r] = _danh_muc(admin_conn, ref[r])
            if danh_muc[r] == "DA_TAO":
                dem["danh_muc"] += len(TRUONG)
        da_co = _mot(admin_conn, "SELECT 1 FROM master.he_thong WHERE key = %s", (MARKER,)) is not None or \
            _mot(admin_conn, "SELECT EXISTS (SELECT 1 FROM master.nguoi_dung WHERE dang_nhap = ANY(%s))", (dang_nhap_crm_g(),))
        if not da_co:
            ids = {}
            for dang_nhap, vai_tro, grants in NGUOI_DUNG:
                ids[dang_nhap] = _mot(admin_conn, """INSERT INTO master.nguoi_dung (ten, dang_nhap, vai_tro, mo_phong) VALUES (%s,%s,%s,true)
                                                     RETURNING id""", (dang_nhap, dang_nhap, vai_tro))
                dem["actor"] += 1
                for pn_ref, (mod, duyet) in grants.items():
                    dem["phan_quyen"] += admin_conn.execute("""INSERT INTO master.phan_quyen (nguoi_dung_id, phap_nhan_id, duyet_loai_viec, module)
                                                               VALUES (%s,%s,%s,%s)""", (ids[dang_nhap], ref[pn_ref], duyet, mod)).rowcount
            for a, pn_ref, module, hd, loai_ref, muon in PHAN_CONG:
                pc = _mot(admin_conn, """INSERT INTO master.phan_cong_hanh_dong (nguoi_dung_id, phap_nhan_id, module, hanh_dong, loai_hinh_id, cap_boi)
                                         VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""", (ids[a], ref[pn_ref], module, hd, ref[loai_ref], CAP_BOI))
                dem["phan_cong"] += 1
                if muon == "REVOKED":  # giữ hàng; dấu thu hồi một lần theo thời điểm giao dịch máy chủ
                    admin_conn.execute("""UPDATE master.phan_cong_hanh_dong SET thu_hoi_luc = now(), thu_hoi_boi = %s, thu_hoi_ly_do = %s
                                          WHERE id = %s""", (CAP_BOI, LY_DO_THU_HOI, pc))
            admin_conn.execute("INSERT INTO master.he_thong (key, value) VALUES (%s, 'v1') ON CONFLICT (key) DO NOTHING", (MARKER,))
        actor = [_trang_thai_actor(admin_conn, ref, *n) for n in NGUOI_DUNG]
        marker = _mot(admin_conn, "SELECT 1 FROM master.he_thong WHERE key = %s", (MARKER,)) is not None
        g2g3 = _g2g3(admin_conn, ref)  # CRM-41-03: chỉ thêm điều khoản tham chiếu DEMO; không đổi trạng thái tổng G1/G7
    trang = [a["trang_thai"] for a in actor] + [("XUNG_DOT" if v == "XUNG_DOT" else "DU") for v in danh_muc.values()]
    tong = next((t for t in ("XUNG_DOT", "DA_THU_HOI", "THIEU") if t in trang), "DU")
    return {"trang_thai": tong, "ly_do": None if tong == "DU" else "Có actor/grant/phân công/danh mục thiếu, đã thu hồi hoặc xung đột — seed không tự bù/cấp lại/ghi đè.",
            "dem": dem, "mo_lai_khong_them": bool(da_co), "marker": marker, "danh_muc": danh_muc, "actor": actor, "g2g3_dieu_khoan": g2g3,
            "khong_seed": ["mau/phien_ban/anh_xa/kiem/duyet CFO", "bo_chuan G7", "viec K5 hoan tat", "grant production"]}
