"""Khởi tạo DEMO M4 (chạy bằng tài khoản chủ CSDL, sau migrate 17 + seed CRM DEMO): dự án xây dựng DEMO và vai mô phỏng MO_PHONG_* RIÊNG
của M4 với phạm vi dự án. Không cấp M4 cho actor CRM/M1/M2/M5/L11 hiện có, không dữ liệu thật, không cấp quyền duyệt CRM/CFO.

Ma trận (DEMO do Root chốt ở handoff M4-01, không phải policy production; phạm vi review theo ASSIGNMENT dự án, không suy từ vai trò/chủ sở hữu):
- MO_PHONG_DU_AN_A1 / _A2: DU_AN, PN_DEMO_A module M4, PHU_TRACH đúng một dự án (cùng PN, khác dự án → ca âm).
- MO_PHONG_DU_AN_B1: DU_AN, PN_DEMO_B module M4, PHU_TRACH dự án B1 (khác PN).
- MO_PHONG_REVIEW_M4: CFO, PN_DEMO_A module M4, assignment REVIEW dự án A1 + A2 (chỉ xem hồ sơ đã nộp; KHÔNG soạn/xác nhận tham số —
  SOAN cần PHU_TRACH + vai trò DU_AN; chưa có quyền duyệt ở gói này).
- MO_PHONG_KT_M4: KE_TOAN, PN_DEMO_A module M4, XEM dự án A1 (kế toán chỉ đọc; xác nhận kế toán là gói M4-03).
- MO_PHONG_XEM_M4: XEM, PN_DEMO_A module M4, XEM dự án A1.
- MO_PHONG_KT_PHU_TRACH_M4: KE_TOAN có PHU_TRACH A1 — ca âm: soạn hồ sơ cần vai trò DU_AN.
- MO_PHONG_DU_AN_KHONG_M4: DU_AN, PHU_TRACH A1 nhưng PN không cấp module M4 — ca âm.

M4-01B (B6):
- Khởi tạo vai/quyền MỘT LẦN, chỉ thêm (như crm_demo/m5_demo SR5). Đã có marker hoặc đã có bất kỳ actor M4 → không thêm gì nữa.
- Quyền dự án chỉ chèn khi CHƯA từng có hàng nào (kể cả hàng đã thu hồi) cho (người, dự án, vai): KHÔNG cấp lại quyền đã thu hồi.
- Báo cáo trung thực từng actor: DU / THIEU (kèm danh sách thiếu) / DA_THU_HOI (kèm assignment đã thu hồi); toàn bộ: DU / THIEU / CHUA_SAN_SANG.
  Không coi seed "xong" khi còn thiếu; không sửa/xóa hàng có sẵn để "cho đủ".

M4-02C (duyệt hồ sơ đợt, cần schema M24): `khoi_tao_duyet` RIÊNG, gọi tường minh sau `khoi_tao` (không nằm trong seed gốc/bootstrap):
- MO_PHONG_DUYET_M4: CFO, PN_DEMO_A module M4, assignment DUYET dự án A1 — CHỈ chấp thuận/kết luận/PDF trên đợt đã nộp; không SOAN/REVIEW/XEM.
- KHÔNG nâng MO_PHONG_REVIEW_M4 (review-only vẫn là ca âm của chấp thuận), không cấp DUYET cho actor nào khác, không cấp lại hàng đã thu hồi,
  không sửa người dùng/phân quyền có sẵn khác ma trận (báo xung đột). Marker riêng; chạy lại không thêm gì.
"""

from __future__ import annotations

MARKER = "demo_seed_m4_actor"
TIEN_TO = "MO_PHONG_"
DU_AN = (("PN_DEMO_A", "DA_XD_A1", "Dự án xây dựng DEMO A1"), ("PN_DEMO_A", "DA_XD_A2", "Dự án xây dựng DEMO A2"),
         ("PN_DEMO_B", "DA_XD_B1", "Dự án xây dựng DEMO B1"))
NGUOI_DUNG = (  # đăng nhập, vai trò, {PN: module}, [(dự án, vai dự án)]
    ("MO_PHONG_DU_AN_A1", "DU_AN", {"PN_DEMO_A": ["M4"]}, [("DA_XD_A1", "PHU_TRACH")]),
    ("MO_PHONG_DU_AN_A2", "DU_AN", {"PN_DEMO_A": ["M4"]}, [("DA_XD_A2", "PHU_TRACH")]),
    ("MO_PHONG_DU_AN_B1", "DU_AN", {"PN_DEMO_B": ["M4"]}, [("DA_XD_B1", "PHU_TRACH")]),
    ("MO_PHONG_REVIEW_M4", "CFO", {"PN_DEMO_A": ["M4"]}, [("DA_XD_A1", "REVIEW"), ("DA_XD_A2", "REVIEW")]),
    ("MO_PHONG_KT_M4", "KE_TOAN", {"PN_DEMO_A": ["M4"]}, [("DA_XD_A1", "XEM")]),
    ("MO_PHONG_XEM_M4", "XEM", {"PN_DEMO_A": ["M4"]}, [("DA_XD_A1", "XEM")]),
    ("MO_PHONG_KT_PHU_TRACH_M4", "KE_TOAN", {"PN_DEMO_A": ["M4"]}, [("DA_XD_A1", "PHU_TRACH")]),
    ("MO_PHONG_DU_AN_KHONG_M4", "DU_AN", {"PN_DEMO_A": []}, [("DA_XD_A1", "PHU_TRACH")]),
)
assert all(n[0].startswith(TIEN_TO) for n in NGUOI_DUNG)
MARKER_DUYET = "demo_seed_m4_duyet"
NGUOI_DUNG_DUYET = (  # M4-02C: duyệt viên DEMO riêng (vai dự án DUYET); cùng hình dạng NGUOI_DUNG
    ("MO_PHONG_DUYET_M4", "CFO", {"PN_DEMO_A": ["M4"]}, [("DA_XD_A1", "DUYET")]),
)
assert all(n[0].startswith(TIEN_TO) for n in NGUOI_DUNG_DUYET)
assert not {n[0] for n in NGUOI_DUNG} & {n[0] for n in NGUOI_DUNG_DUYET}


def _dang_nhap_goc() -> list[str]:
    return [n[0] for n in NGUOI_DUNG]


def dang_nhap_m4() -> list[str]:
    """Vai mô phỏng M4 chọn được trên giao diện DEMO (gốc + duyệt viên M4-02C). Danh tính vẫn phải tồn tại/hoạt động trong CSDL."""
    return _dang_nhap_goc() + dang_nhap_m4_duyet()


def dang_nhap_m4_duyet() -> list[str]:
    return [n[0] for n in NGUOI_DUNG_DUYET]


def _mot(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return None if row is None else row[0]


def _trang_thai_actor(conn, pn: dict, du_an: dict, dang_nhap, vai_tro, modules, du_an_vai) -> dict:
    """Đối chiếu ma trận với CSDL hiện hành, không ghi gì."""
    thieu, thu_hoi, sai = [], [], []
    nd = conn.execute("SELECT id, vai_tro, mo_phong, trang_thai FROM master.nguoi_dung WHERE dang_nhap = %s", (dang_nhap,)).fetchone()
    if nd is None:
        return {"dang_nhap": dang_nhap, "trang_thai": "THIEU", "thieu": ["nguoi_dung"], "da_thu_hoi": [], "sai": []}
    if (nd[1], nd[2]) != (vai_tro, True):
        sai.append(f"nguoi_dung vai_tro/mo_phong khác ma trận ({nd[1]}, mo_phong={nd[2]})")
    if nd[3] != "HOAT_DONG":
        sai.append(f"nguoi_dung trang_thai {nd[3]}")
    for pn_ma, mod in modules.items():
        r = conn.execute("SELECT module FROM master.phan_quyen WHERE nguoi_dung_id = %s AND phap_nhan_id = %s", (nd[0], pn[pn_ma])).fetchone()
        if r is None:
            thieu.append(f"phan_quyen {pn_ma}")
        elif ("M4" in mod) != ("M4" in list(r[0] or [])):
            sai.append(f"phan_quyen {pn_ma} module M4 khác ma trận")
    for ma, vai in du_an_vai:
        rows = conn.execute("""SELECT thu_hoi_luc IS NULL FROM m4.quyen_du_an WHERE nguoi_dung_id = %s AND du_an_id = %s AND vai = %s""",
                            (nd[0], du_an[ma][0], vai)).fetchall()
        if any(r[0] for r in rows):
            continue
        (thu_hoi if rows else thieu).append(f"{ma}:{vai}")
    tt = "DA_THU_HOI" if thu_hoi else "THIEU" if (thieu or sai) else "DU"
    return {"dang_nhap": dang_nhap, "trang_thai": tt, "thieu": thieu, "da_thu_hoi": thu_hoi, "sai": sai}


def khoi_tao(admin_conn) -> dict:
    """admin_conn: psycopg autocommit, chủ CSDL. Chỉ thêm, một lần; KHÔNG raise khi chưa sẵn sàng — trả trạng thái trung thực:
    {"trang_thai": DU|THIEU|CHUA_SAN_SANG, "ly_do", "dem", "actor": [...]}."""
    dem = {"du_an": 0, "actor": 0, "phan_quyen": 0, "quyen_du_an": 0}
    with admin_conn.transaction():
        if _mot(admin_conn, "SELECT to_regclass('m4.quyen_du_an') IS NOT NULL") is not True:
            return {"trang_thai": "CHUA_SAN_SANG", "ly_do": "Schema M4 chưa có — migrate 17 trước khi seed M4 DEMO.", "dem": dem, "actor": []}
        pn, thieu_pn = {}, []
        for ma in sorted({d[0] for d in DU_AN}):
            i = _mot(admin_conn, "SELECT id FROM master.phap_nhan WHERE ma = %s", (ma,))
            if i is None:
                thieu_pn.append(ma)
            pn[ma] = i
        if thieu_pn:
            return {"trang_thai": "CHUA_SAN_SANG", "ly_do": "Thiếu pháp nhân " + ", ".join(thieu_pn) + " — chạy seed CRM DEMO trước, không tạo PN mới.",
                    "dem": dem, "actor": []}
        du_an = {}
        for pn_ma, ma, ten in DU_AN:
            dem["du_an"] += admin_conn.execute("""INSERT INTO master.du_an (phap_nhan_id, ma_junsky, ten) VALUES (%s,%s,%s)
                                                  ON CONFLICT (phap_nhan_id, ma_junsky) DO NOTHING""", (pn[pn_ma], ma, ten)).rowcount
            du_an[ma] = (_mot(admin_conn, "SELECT id FROM master.du_an WHERE phap_nhan_id = %s AND ma_junsky = %s", (pn[pn_ma], ma)), pn[pn_ma])
        da_co = _mot(admin_conn, "SELECT 1 FROM master.he_thong WHERE key = %s", (MARKER,)) is not None or \
            _mot(admin_conn, "SELECT EXISTS (SELECT 1 FROM master.nguoi_dung WHERE dang_nhap = ANY(%s))", (_dang_nhap_goc(),))
        xung_dot = []
        for dang_nhap, vai_tro, modules, du_an_vai in ([] if da_co else NGUOI_DUNG):
            dem["actor"] += admin_conn.execute("""INSERT INTO master.nguoi_dung (ten, dang_nhap, vai_tro, mo_phong) VALUES (%s,%s,%s,true)
                                                  ON CONFLICT (dang_nhap) DO NOTHING""", (dang_nhap, dang_nhap, vai_tro)).rowcount
            row = admin_conn.execute("SELECT id, vai_tro, mo_phong FROM master.nguoi_dung WHERE dang_nhap = %s", (dang_nhap,)).fetchone()
            if (row[1], row[2]) != (vai_tro, True):
                xung_dot.append(dang_nhap)  # không ghi đè, không cấp gì thêm cho người này
                continue
            for pn_ma, mod in modules.items():
                dem["phan_quyen"] += admin_conn.execute("""INSERT INTO master.phan_quyen (nguoi_dung_id, phap_nhan_id, duyet_loai_viec, module)
                                                           VALUES (%s,%s,'{}',%s) ON CONFLICT (nguoi_dung_id, phap_nhan_id) DO NOTHING""",
                                                        (row[0], pn[pn_ma], mod)).rowcount
            for ma, vai in du_an_vai:  # chỉ khi chưa từng có hàng (kể cả đã thu hồi) — không cấp lại quyền đã thu hồi
                dem["quyen_du_an"] += admin_conn.execute("""INSERT INTO m4.quyen_du_an (nguoi_dung_id, phap_nhan_id, du_an_id, vai)
                                                            SELECT %s,%s,%s,%s WHERE NOT EXISTS (SELECT 1 FROM m4.quyen_du_an
                                                                WHERE nguoi_dung_id = %s AND du_an_id = %s AND vai = %s)""",
                                                         (row[0], du_an[ma][1], du_an[ma][0], vai, row[0], du_an[ma][0], vai)).rowcount
        admin_conn.execute("INSERT INTO master.he_thong (key, value) VALUES (%s, 'v1') ON CONFLICT (key) DO NOTHING", (MARKER,))
        actor = [_trang_thai_actor(admin_conn, pn, du_an, *n) for n in NGUOI_DUNG]
    tong = "DU" if all(a["trang_thai"] == "DU" for a in actor) else "THIEU"
    return {"trang_thai": tong, "ly_do": None if tong == "DU" else "Có actor thiếu/đã thu hồi/khác ma trận — xem danh sách; seed không tự bù/cấp lại.",
            "dem": dem, "mo_lai_khong_them": bool(da_co), "xung_dot_khong_ghi_de": xung_dot, "actor": actor}


def khoi_tao_duyet(admin_conn) -> dict:
    """M4-02C — thêm duyệt viên DEMO riêng (vai dự án DUYET) MỘT LẦN, chỉ thêm. admin_conn: psycopg autocommit, chủ CSDL, schema đã có M24.
    Không raise khi chưa sẵn sàng; không đụng actor gốc (review-only giữ nguyên), không cấp lại quyền đã thu hồi, không sửa hàng có sẵn khác ma trận.
    Trả {"trang_thai": DU|THIEU|CHUA_SAN_SANG, "ly_do", "dem", "actor", "review_khong_duyet"}."""
    dem = {"actor": 0, "phan_quyen": 0, "quyen_du_an": 0}
    with admin_conn.transaction():
        if _mot(admin_conn, "SELECT to_regclass('m4.duyet_phien_ban') IS NOT NULL") is not True:
            return {"trang_thai": "CHUA_SAN_SANG", "ly_do": "Schema M24 (duyệt hồ sơ đợt) chưa có — Root áp migration trước; helper không migrate.",
                    "dem": dem, "actor": []}
        pn, du_an, thieu = {}, {}, []
        for pn_ma, ma, _ten in DU_AN:
            pn[pn_ma] = _mot(admin_conn, "SELECT id FROM master.phap_nhan WHERE ma = %s", (pn_ma,))
            i = None if pn[pn_ma] is None else _mot(admin_conn, "SELECT id FROM master.du_an WHERE phap_nhan_id = %s AND ma_junsky = %s", (pn[pn_ma], ma))
            if i is None:
                thieu.append(ma)
            du_an[ma] = (i, pn[pn_ma])
        can = sorted({ma for n in NGUOI_DUNG_DUYET for ma, _ in n[3]} & set(thieu))
        if can:
            return {"trang_thai": "CHUA_SAN_SANG", "ly_do": "Thiếu PN/dự án DEMO " + ", ".join(can) + " — chạy khoi_tao M4 DEMO trước.",
                    "dem": dem, "actor": []}
        da_co = _mot(admin_conn, "SELECT 1 FROM master.he_thong WHERE key = %s", (MARKER_DUYET,)) is not None
        xung_dot = []
        for dang_nhap, vai_tro, modules, du_an_vai in ([] if da_co else NGUOI_DUNG_DUYET):
            dem["actor"] += admin_conn.execute("""INSERT INTO master.nguoi_dung (ten, dang_nhap, vai_tro, mo_phong) VALUES (%s,%s,%s,true)
                                                  ON CONFLICT (dang_nhap) DO NOTHING""", (dang_nhap, dang_nhap, vai_tro)).rowcount
            row = admin_conn.execute("SELECT id, vai_tro, mo_phong FROM master.nguoi_dung WHERE dang_nhap = %s", (dang_nhap,)).fetchone()
            if (row[1], row[2]) != (vai_tro, True):
                xung_dot.append(dang_nhap)
                continue
            for pn_ma, mod in modules.items():  # phân quyền có sẵn (kể cả đã gỡ module) giữ nguyên — không ghi đè
                dem["phan_quyen"] += admin_conn.execute("""INSERT INTO master.phan_quyen (nguoi_dung_id, phap_nhan_id, duyet_loai_viec, module)
                                                           VALUES (%s,%s,'{}',%s) ON CONFLICT (nguoi_dung_id, phap_nhan_id) DO NOTHING""",
                                                        (row[0], pn[pn_ma], mod)).rowcount
            for ma, vai in du_an_vai:  # chỉ khi CHƯA TỪNG có hàng (kể cả đã thu hồi) — không hồi sinh quyền đã thu hồi
                dem["quyen_du_an"] += admin_conn.execute("""INSERT INTO m4.quyen_du_an (nguoi_dung_id, phap_nhan_id, du_an_id, vai)
                                                            SELECT %s,%s,%s,%s WHERE NOT EXISTS (SELECT 1 FROM m4.quyen_du_an
                                                                WHERE nguoi_dung_id = %s AND du_an_id = %s AND vai = %s)""",
                                                         (row[0], du_an[ma][1], du_an[ma][0], vai, row[0], du_an[ma][0], vai)).rowcount
        admin_conn.execute("INSERT INTO master.he_thong (key, value) VALUES (%s, 'v1') ON CONFLICT (key) DO NOTHING", (MARKER_DUYET,))
        actor = [_trang_thai_actor(admin_conn, pn, du_an, *n) for n in NGUOI_DUNG_DUYET]
        # ca âm bắt buộc: actor review-only gốc KHÔNG có DUYET hiện hành (helper không cấp; nếu ai đó đã cấp ngoài seed → báo, không tự gỡ)
        review_duyet = [r[0] for r in admin_conn.execute(
            """SELECT n.dang_nhap FROM m4.quyen_du_an q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
               WHERE q.vai = 'DUYET' AND q.thu_hoi_luc IS NULL AND n.dang_nhap = ANY(%s) ORDER BY n.dang_nhap""", (_dang_nhap_goc(),)).fetchall()]
    tong = "DU" if all(a["trang_thai"] == "DU" for a in actor) and not review_duyet else "THIEU"
    return {"trang_thai": tong,
            "ly_do": None if tong == "DU" else "Duyệt viên thiếu/đã thu hồi/khác ma trận, hoặc actor gốc đang có DUYET — xem chi tiết; helper không tự bù/gỡ.",
            "dem": dem, "mo_lai_khong_them": da_co, "xung_dot_khong_ghi_de": xung_dot, "actor": actor, "actor_goc_co_duyet": review_duyet}
