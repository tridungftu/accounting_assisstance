"""CRM-41-02 — HTTP mỏng cho G1 mẫu DOCX + G7 bộ chuẩn dự án trên LocalApp hiện có (cùng token X-KTT-Token, phiên cookie HttpOnly do máy chủ cấp,
mutation lock, kết nối login ứng dụng của CRM + kết nối chủ bảng `_m5_ket_noi_chu`). Không nhận actor/PN/facts/đường dẫn/duyệt từ trình duyệt.

Route (đều dưới /api/crm; route đặc biệt khớp CHÍNH XÁC trước UUID và trước catch-all cũ `/api/crm/`):
  GET  /api/crm/mau · /api/crm/mau/so-sanh?a=&b= · /api/crm/mau/tep/{version_id} · /api/crm/mau/{version_id}
  POST /api/crm/mau/{tai (bytes + X-CRM-G-Info), anh-xa, gui-kiem, kiem, tra-lai, duyet, tu-choi, xem-thu}
  GET  /api/crm/bo-chuan[?du_an_id=&giai_doan=&as_of=] · POST /api/crm/bo-chuan/{lap, gui-duyet, duyet}
  (tài sản /crm_g.js: static allowlist của server.py)
POST /api/crm/mau (đúng chuỗi, không hậu tố) vẫn thuộc handler cũ nhận mẫu #6 DEMO.

CRM-41-03 (G2 Báo giá → G3 Soạn; cùng phiên/token/factory, không router thứ hai):
  GET  /api/crm/bao-gia · /api/crm/bao-gia/moc-chuan · /api/crm/bao-gia/{id} · /api/crm/soan/{id} · /api/crm/giao-ket/tep/{xuat_id}/{docx|pdf}
  POST /api/crm/bao-gia/{luu, huy, chuyen} · /api/crm/soan/luu   (lệnh ngắn dưới mutation lock)
  POST /api/crm/bao-gia/in · /api/crm/soan/xuat   (ba pha: chụp dưới khóa → render NGOÀI khóa/giao dịch → công bố dưới khóa + CAS)
  BG-1c: GET /api/crm/bao-gia/ty-gia-mac-dinh · POST /api/crm/bao-gia/ty-gia-mac-dinh {ty_gia, ly_do} (kế toán; master.cau_hinh + nhật ký)

CRM-41-04A (G4 ký lần đầu; cùng prefix giao-ket đã route, cùng phiên/token/factory):
  GET  /api/crm/giao-ket/ky/{soan_id}   (điều kiện + căn cứ dialog + bản ký/lịch sử theo quyền hiện hành)
  GET  /api/crm/giao-ket/ban-ky/{ky_id}/tep   (PDF bản ký; quyền + nhật ký truy cập trước tra kho)
  POST /api/crm/giao-ket/ky-ket   (raw PDF + X-CRM-G-Info: quyền dưới khóa → parse PDF NGOÀI khóa → lệnh ký dưới khóa)

CRM-41-06A (G6A KT kiểm + kích hoạt HIEU_LUC; cùng prefix giao-ket, cùng phiên/token/factory; không nhận query; G5 luôn VAN_HANH qua HTTP):
  GET  /api/crm/giao-ket/kiem · /api/crm/giao-ket/kiem/{ky_id} · /api/crm/giao-ket/kiem/{ky_id}/tep/{ban-ky|g3}
  POST /api/crm/giao-ket/kiem/{luu, check, xu-ly-lech, bo-sung, hieu-luc, tra-lai}   (lệnh ngắn dưới mutation lock)
  POST /api/crm/giao-ket/kiem/tim-junsky   (tra mã Junsky CÓ SẴN cho khách dự thảo; quyền lệnh + phạm vi trước tra cứu; không ghi nghiệp vụ)

CRM G5-B (đối chiếu bản ký ↔ bản sinh; cùng prefix giao-ket, cùng phiên/token/factory; không nhận query; một engine Source6 qua app.trich6_client):
  GET  /api/crm/giao-ket/doi-chieu/{ky_id}   (CRM_G5_VIEW_V1: quyền + phạm vi hiện hành trước tra cứu; context_sha256 để CAS)
  POST /api/crm/giao-ket/doi-chieu/{chay, doi-soat}   (CHỈ {ky_id, expected_context_sha256, khoa} → CRM_G5_ACK_V1; engine chạy ở worker nền
       NGOÀI mutation lock/giao dịch; hàng đợi bền ở CSDL, worker khởi tạo một lần theo factory và được đánh thức sau ký G4/lệnh)
  FIX01-C: khởi tạo service G thường (`dich_vu`) cũng khởi tạo + đánh thức đúng MỘT worker G5 cho app (drain/recover việc đã ghi trước restart);
       check+create mọi factory đồng bộ bằng `_KHOI_TAO` (reentrant, KHÔNG lấy mutation_lock bên trong, không gọi engine/mạng). Giới hạn: đây
       không phải hook khởi động toàn máy chủ — worker chỉ có từ lần đầu factory G được dùng trong tiến trình.
  FIX02: factory Gk/Ky/Kiem/G5 lấy service cha TRƯỚC rồi đọc lại cache dưới `_KHOI_TAO` — khởi tạo G (qua G5) có thể đã dựng chính đối tượng
       đó; constructor ngoài không bao giờ ghi đè → một chuỗi G→Gk→Ky→Kiem→G5 duy nhất bất kể factory nào được gọi đầu tiên.

DA-1 CRM · Dự án đang bán (QD-20261025-05…09; M0031; khối riêng cuối tệp `_dieu_huong_da`, cùng phiên/token/factory G, không router thứ hai):
  GET  /api/crm/du-an-ban[?dang_ban=1] · /api/crm/du-an-ban/anh-chup?du_an_id=&ngay= · /api/crm/du-an-ban/{da_ban_id}[?phien_ban=&ngay=]
       · /api/crm/du-an-ban/{da_ban_id}/lich-su
  POST /api/crm/du-an-ban/{bat-ban, cap-nhat, phi, lo, ngung-ban, mo-ban-lai, tien-do}   (lệnh ngắn dưới mutation lock; tham số truy vấn lạ → 400)
"""

from __future__ import annotations

import json
import re
import threading
from urllib.parse import quote, unquote, urlsplit

from ..ha_tang.primitives import DataError

KHONG_NHAN = frozenset({"actor", "nguoi", "dang_nhap", "dang_nhap_thuc_hien", "phap_nhan_id", "phap_nhan", "trang_thai", "approved", "duyet_boi",
                        "kiem_boi", "nguoi_duyet", "quyen", "vai", "vai_tro", "module", "path", "duong_dan", "url", "dsn", "facts", "facts_sha256",
                        "raw_sha256", "sha256", "object_key", "receipt", "bien_nhan", "ket_qua", "viec_id", "proven", "PROVEN"})
TRUONG = {
    "mau/anh-xa": {"version_id", "map", "expected_graph", "khoa"},
    "mau/gui-kiem": {"version_id", "expected_graph", "khoa"},
    "mau/kiem": {"version_id", "expected_graph", "khoa"},
    "mau/tra-lai": {"version_id", "ly_do", "expected_graph", "khoa"},
    "mau/duyet": {"version_id", "valid_from", "expected_graph", "khoa"},
    "mau/tu-choi": {"version_id", "ly_do", "expected_graph", "khoa"},
    "mau/xem-thu": {"version_id"},
    "bo-chuan/lap": {"du_an_id", "giai_doan", "dong", "khoa"},
    "bo-chuan/gui-duyet": {"version_id", "expected_graph", "khoa"},
    "bo-chuan/duyet": {"version_id", "valid_from", "expected_graph", "khoa"},
}
TRUONG_TAI = {"loai_hinh_id", "ma_mau", "ten_tep", "khoa"}
# CRM-41-03: lệnh ngắn (dưới mutation lock) và lệnh dài ba pha (render ngoài khóa)
TRUONG_GK = {
    "bao-gia/luu": {"bao_gia_id", "expected_revision", "du_lieu", "khoa"},
    "bao-gia/huy": {"bao_gia_id", "expected_revision", "ly_do", "khoa"},
    "bao-gia/chuyen": {"bao_gia_id", "expected_revision", "mau_phien_ban_id", "khoa"},
    "soan/luu": {"soan_id", "expected_revision", "gia_tri_truong", "bao_gia", "doi_mau_phien_ban_id", "ly_do", "khoa"},
    "bao-gia/xem-truoc": {"du_lieu"},  # FIX01 #4: tính thử chỉ đọc (không khóa, không ghi)
    "bao-gia/ty-gia-mac-dinh": {"ty_gia", "ly_do"},  # BG-1c: kế toán sửa tỷ giá USD/VND mặc định chung (cấu hình + nhật ký)
}
TRUONG_GK_DAI = {"bao-gia/in": {"bao_gia_id", "expected_revision", "khoa"}, "soan/xuat": {"soan_id", "expected_revision", "khoa"}}
MA_409_GK = frozenset({"CRM_GK_DANG_XU_LY", "CRM_GK_LAN_KHONG_KHOP", "CRM_GK_REVISION_CU", "CRM_GK_TRANG_THAI", "CRM_GK_DA_CHUYEN", "CRM_GK_G7_DOI", "CRM_GK_CHAN_IN", "CRM_GK_CHAN_XUAT", "CRM_GK_CHAN_CHUYEN",
                       "CRM_GK_MAU_KHONG_HIEU_LUC", "CRM_GK_MAU_KHONG_HOP_LE", "CRM_GK_MAU_LECH_GHIM", "CRM_GK_LOAI_HD_CHUA_KHAI", "ARTIFACT_CHANGED"})
MA_403_GK = frozenset({"CRM_GK_PHAM_VI"})
MA_403 = frozenset({"CRM_G_KHONG_CO_QUYEN", "CRM_G_CLIENT_AUTHORITY", "CRM_G_DANH_TINH", "CRM_G_CHI_MAY_CHU", "CRM_G_CHI_CHU", "CRM_G_VIEC_CHI_CHU",
                    "CRM_G_PHAN_CONG_CHI_QUAN_TRI", "CRM_G_CUNG_NGUOI", "DANH_TINH", "DANH_TINH_MO_PHONG", "KHONG_CO_QUYEN_MODULE",
                    "KHONG_CO_QUYEN_PHAP_NHAN", "LOCAL_HOST_ONLY", "CROSS_ORIGIN", "SESSION_TOKEN"})
MA_404 = frozenset({"NOT_FOUND", "CRM_G_KHONG_THAY", "CRM_G_TEP_KHONG_CO"})
MA_409 = frozenset({"CRM_G_TOKEN_CU", "CRM_G_IDEMPOTENCY_KHAC", "CRM_G_TRANG_THAI", "CRM_G_HIEU_LUC_CHONG", "CRM_G_CHUA_DU_DIEU_KIEN",
                    "CRM_G_KIEM_HET_HIEU_LUC", "CRM_G_CHUA_ANH_XA", "CRM_G_VIEC_SAI", "CRM_G_MAU_KHAC_LOAI", "CRM_G_TEP_XUNG_DOT", "CRM_G_BAT_BIEN",
                    "CRM_G_VIEC_BAT_BIEN", "CRM_G_VIEC_DA_DONG", "CRM_G_VIEC_DOI_DICH", "CRM_G_GIAO_DICH_NGOAI", "CRM_G_TEP_HONG"})
MA_413 = frozenset({"CRM_G_TEP_QUA_LON", "CRM_MAU_TEP_QUA_LON", "CRM_MAU_BOM_NEN", "FILE_TOO_LARGE"})
MA_503 = frozenset({"CRM_G_CHUA_SAN_SANG", "PG_KHONG_KET_NOI", "CRM_CHUA_CAU_HINH", "CRM_SCHEMA_KHONG_KHOP"})
# CRM-41-04A G4 ký lần đầu
TRUONG_KY = {"soan_id", "expected_revision", "expected_xuat_id", "ten_tep", "ngay_ky", "co_sua", "mo_ta", "nguoi_ky_khach", "khoa"}
MIME_KY = ("application/pdf", "application/octet-stream")
MA_409_KY = frozenset({"CRM_GK_DA_KY", "CRM_KY_DA_KY", "CRM_KY_XUAT_CU", "CRM_KY_XUAT_CHUA_DAT", "CRM_KY_TRANG_THAI", "CRM_KY_G3_LECH"})
MA_403_KY = frozenset({"CRM_KY_CHUA_CO_PHAM_VI"})
MA_413_KY = frozenset({"CRM_KY_TEP_QUA_LON"})
MA_503_KY = frozenset({"CRM_KY_PDF_CHUA_KIEM_DUOC"})
# CRM-41-06A G6A kế toán kiểm + kích hoạt
TRUONG_KIEM = {
    "giao-ket/kiem/luu": {"ky_id", "expected_revision", "checklist", "doi_tac_id", "ma_junsky_id", "ngay_hieu_luc", "can_cu_ngay", "trich_dan_ngay",
                          "ghi_chu", "khoa"},
    "giao-ket/kiem/check": {"ky_id", "expected_revision", "khoa"},
    "giao-ket/kiem/xu-ly-lech": {"ky_id", "expected_revision", "loai", "muc_tieu_id", "ma_lech", "ly_do", "khoa"},
    "giao-ket/kiem/bo-sung": {"ky_id", "expected_revision", "ly_do", "khoa"},
    "giao-ket/kiem/hieu-luc": {"ky_id", "expected_revision", "check_id", "do_thi_sha256", "khoa"},
    "giao-ket/kiem/tra-lai": {"ky_id", "expected_revision", "ly_do", "khoa"},
    "giao-ket/kiem/tim-junsky": {"ky_id", "tu_khoa"},  # P1-B tra cứu (không ghi nghiệp vụ; có nhật ký truy cập) — POST để không đưa từ khóa vào URL
}
KHONG_NHAN_KIEM = frozenset({"g5_che_do", "che_do", "synthetic", "ket_luan", "chan", "do_thi", "hop_dong_id", "phien_ban_id", "chung_tu_id",
                             "quyet_dinh_id", "g5", "g7"})
MA_403_KIEM = frozenset({"CRM_KIEM_CHUA_CO_PHAM_VI"})
MA_409_KIEM = frozenset({"CRM_KIEM_TRANG_THAI", "CRM_KIEM_REVISION_CU", "CRM_KIEM_CHECK_CU", "CRM_KIEM_CHUA_DU_DIEU_KIEN", "CRM_KIEM_DA_HIEU_LUC",
                         "CRM_KIEM_DA_XU_LY", "CRM_KIEM_LECH_KHONG_CON", "CRM_KIEM_HO_SO_SAI", "CRM_KIEM_REV_SAI", "CRM_KIEM_CHECK_SAI",
                         "CRM_KIEM_QUYET_DINH_SAI", "CRM_KIEM_HOAN_TAT_SAI", "CRM_KIEM_BAT_BIEN", "CRM_KIEM_HD_BAT_BIEN", "CRM_KIEM_HD_KICH_HOAT_SAI",
                         "CRM_KIEM_PB_BAT_BIEN", "CRM_KIEM_PB_DUYET_SAI", "CRM_KIEM_PB_SAI", "CRM_KIEM_PB_CHI_MAU", "CRM_KIEM_THAM_SO_SAI",
                         "CRM_KIEM_THAM_SO_BAT_BIEN", "CRM_KIEM_LICH_SAI", "CRM_KIEM_VIEC_SAI", "CRM_KIEM_VIEC_TRANG_THAI", "CRM_KIEM_VIEC_BAT_BIEN",
                         "CRM_KIEM_KHACH_DA_DINH"})
# CRM G5-B đối chiếu: trình duyệt chỉ gửi đích + ngữ cảnh CAS + khóa; expected/catalog/principal/kết quả/chế độ do máy chủ xác định
TRUONG_DC = {
    "giao-ket/doi-chieu/chay": {"ky_id", "expected_context_sha256", "khoa"},
    "giao-ket/doi-chieu/doi-soat": {"ky_id", "expected_context_sha256", "khoa"},
}
KHONG_NHAN_DC = frozenset({"expected", "expected_sha256", "catalog", "catalog_id", "catalog_binding", "catalog_binding_sha256", "mapping",
                           "dang_ky_id", "principal", "nguoi_chay", "tac_nhan", "request_id", "job_id", "result_id", "mode", "engine", "tham_so",
                           "trusted", "lineage", "soan_rev_id"})
MA_409_DC = frozenset({"CRM_G5_NGU_CANH_CU", "CRM_G5_CHUA_CO_VIEC", "CRM_G5_LEASE_MAT", "CRM_G5_Y_DINH_KHAC", "CRM_G5_VIEC_SAI", "CRM_G5_VIEC_BAT_BIEN",
                       "CRM_G5_DANG_KY_DOI", "CRM_G5_NGUOI_CHAY_DOI", "CRM_G5_KET_QUA_SAI", "CRM_G5_Y_DINH_SAI"})
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
# check+create factory CRM: đồng bộ thực (hai luồng init/refresh → một service/worker). Reentrant cho chuỗi G→Gk→Ky→Kiem→G5.
# Thứ tự khóa: mutation_lock (route) → _KHOI_TAO; worker chỉ lấy mutation_lock và không bao giờ vào factory → không deadlock.
_KHOI_TAO = threading.RLock()


def la_route(post: bool, path: str) -> bool:
    """Route thuộc module này? POST /api/crm/mau (không hậu tố) KHÔNG thuộc — giữ handler #6 cũ. Tài sản /crm_g.js nằm ở static allowlist của server."""
    if path == "/api/crm/mau":
        return not post
    if path == "/api/crm/bao-gia" or path.startswith(("/api/crm/bao-gia/", "/api/crm/soan/", "/api/crm/giao-ket/")):  # CRM-41-03 G2/G3
        return True
    if _la_route_da(path):  # DA-1 dự án đang bán
        return True
    return path.startswith(("/api/crm/mau/", "/api/crm/bo-chuan/")) or path == "/api/crm/bo-chuan"


def dich_vu(app):
    """Factory máy chủ: service G dùng login ứng dụng của CRM (nạp danh tính) + kết nối CHỦ BẢNG `_m5_ket_noi_chu` (đã kiểm đích/chủ bảng).
    Không có admin DSN hoặc không kết nối được → conn_tin_cay=None: mọi thao tác G báo CRM_G_CHUA_SAN_SANG (503), không fallback.
    FIX01-C: lần khởi tạo service G (đồng bộ `_KHOI_TAO`) cũng khởi tạo + đánh thức worker G5 duy nhất của app (`_khoi_dong_g5`)."""
    svc = app.__dict__.get("_crm_g")
    if svc is not None:
        return svc
    with _KHOI_TAO:
        svc = app.__dict__.get("_crm_g")
        if svc is None:
            from ..k2.crm_mau import CrmMauK2
            crm = app.crm()
            try:
                tin_cay, ly_do = app._m5_ket_noi_chu(crm.conn), None
            except DataError as exc:
                tin_cay, ly_do = None, exc.code
            if tin_cay is None and ly_do is None:
                ly_do = "CHUA_CAU_HINH_ADMIN_DSN"
            svc = CrmMauK2(crm.conn, app.root / "crm-g", conn_tin_cay=tin_cay, hom_nay=crm.hom_nay)
            svc.ly_do_chua_san_sang = ly_do
            app.__dict__["_crm_g"] = svc  # công bố TRƯỚC khi dựng G5 → chuỗi Gk/Ky/Kiem gọi lại dich_vu nhận chính svc này (không đệ quy)
            _khoi_dong_g5(app)
    return svc


def dich_vu_gk(app):
    """CRM-41-03: service G2/G3 trên CHÍNH service G (cùng factory/kết nối chủ bảng đã kiểm, cùng kho crm-g) — không factory/IAM thứ hai."""
    gk = app.__dict__.get("_crm_gk")
    if gk is not None:
        return gk
    with _KHOI_TAO:
        gk = app.__dict__.get("_crm_gk")
        if gk is None:
            from ..k2.crm_giao_ket import CrmGiaoKetK2
            cha = dich_vu(app)  # FIX02: lấy cha TRƯỚC — khởi tạo G có thể đã dựng chuỗi G5 (gồm _crm_gk) bên trong
            gk = app.__dict__.get("_crm_gk")
            if gk is None:
                gk = CrmGiaoKetK2(cha)
                app.__dict__["_crm_gk"] = gk
    return gk


def dich_vu_ky(app):
    """CRM-41-04A: service G4 trên CHÍNH service G2/G3 (cùng kết nối chủ bảng/kho giao-ket) — không factory/IAM thứ hai."""
    ky = app.__dict__.get("_crm_ky")
    if ky is not None:
        return ky
    with _KHOI_TAO:
        ky = app.__dict__.get("_crm_ky")
        if ky is None:
            from ..k2.crm_ky_ket import CrmKyKetK2
            cha = dich_vu_gk(app)  # FIX02: cha trước, rồi đọc lại cache (không ghi đè đối tượng chuỗi G5 đã dựng)
            ky = app.__dict__.get("_crm_ky")
            if ky is None:
                ky = CrmKyKetK2(cha)
                app.__dict__["_crm_ky"] = ky
    return ky


def dich_vu_kiem(app):
    """CRM-41-06A: service G6A trên CHÍNH service G4 (cùng kết nối chủ bảng/kho giao-ket). G5 luôn VAN_HANH (HOLD tới khi có bằng chứng đăng ký);
    chế độ SYNTHETIC chỉ fixture kiểm thử dựng trực tiếp — HTTP không có đường chọn."""
    kiem = app.__dict__.get("_crm_kiem")
    if kiem is not None:
        return kiem
    with _KHOI_TAO:
        kiem = app.__dict__.get("_crm_kiem")
        if kiem is None:
            from ..k2.crm_kiem_hd import CrmKiemHdK2
            cha = dich_vu_ky(app)  # FIX02: cha trước, rồi đọc lại cache
            kiem = app.__dict__.get("_crm_kiem")
            if kiem is None:
                kiem = CrmKiemHdK2(cha)
                app.__dict__["_crm_kiem"] = kiem
    return kiem


def dich_vu_doi_chieu(app):
    """CRM G5-B: service đối chiếu trên CHÍNH service G6A (cùng kết nối chủ bảng/kho giao-ket) + client Source6 của app (``app.trich6_client``).
    Worker nền khởi tạo đúng MỘT lần cho app (check+create service VÀ worker trong cùng `_KHOI_TAO`) và được đánh thức ngay để drain/recover
    hàng đợi bền. Không gọi engine/mạng, không lấy mutation_lock: worker tự lấy mutation_lock khi chạy (sau khi caller nhả)."""
    dv, hd = app.__dict__.get("_crm_g5"), app.__dict__.get("_crm_g5_hang_doi")
    if dv is not None and hd is not None:
        return dv
    with _KHOI_TAO:
        if app.__dict__.get("_crm_g5_dang_tao"):  # tái nhập từ chuỗi kiem→…→dich_vu: lần gọi ngoài đang dựng, không dựng lần hai
            return app.__dict__.get("_crm_g5")
        app.__dict__["_crm_g5_dang_tao"] = True
        try:
            dv = app.__dict__.get("_crm_g5")
            if dv is None:
                from ..k2.crm_doi_chieu import CrmDoiChieuK2
                cha = dich_vu_kiem(app)  # FIX02: cha trước, rồi đọc lại cache (cờ _crm_g5_dang_tao đã chặn dựng lồng; đọc lại để rõ ràng)
                dv = app.__dict__.get("_crm_g5")
                if dv is None:
                    dv = CrmDoiChieuK2(cha, client_fn=getattr(app, "trich6_client", None))
                    app.__dict__["_crm_g5"] = dv
            if app.__dict__.get("_crm_g5_hang_doi") is None:
                from ..k2.crm_doi_chieu import HangDoiG5
                hd = HangDoiG5(dv, app.mutation_lock, db=app._crm_db)
                app.__dict__["_crm_g5_hang_doi"] = hd
                hd.bat_dau()
                hd.danh_thuc()
        finally:
            app.__dict__["_crm_g5_dang_tao"] = False
    return dv


def _khoi_dong_g5(app) -> None:
    """Gọi từ khởi tạo service G: dựng/đánh thức worker G5 duy nhất. Lỗi (thiếu cấu hình/thuộc tính) KHÔNG làm hỏng service G — giữ mã lỗi thật
    ở `_crm_g5_loi_khoi_tao`; việc bắt buộc vẫn bền trong CSDL. Chưa cài schema G5 → worker ghi `loi_cuoi` thật ở chu kỳ, không mất việc."""
    try:
        dich_vu_doi_chieu(app)
        app.__dict__["_crm_g5_loi_khoi_tao"] = None
    except Exception as exc:  # noqa: BLE001 — không chặn G; lỗi giữ nguyên mã để chẩn đoán
        app.__dict__["_crm_g5_loi_khoi_tao"] = getattr(exc, "code", None) or type(exc).__name__


def _danh_thuc_g5(app) -> None:
    """Đánh thức worker sau commit (ký G4/lệnh G5). CHỈ đánh thức worker đã có (worker được dựng trong factory, đồng bộ `_KHOI_TAO`);
    không dựng mới ở đây. Lỗi không đổi ACK đã commit — việc bắt buộc đã nằm trong CSDL từ giao dịch ký."""
    try:
        hd = app.__dict__.get("_crm_g5_hang_doi")
        if hd is not None:
            hd.danh_thuc()
    except Exception:  # noqa: BLE001 — hàng đợi bền; worker sẽ drain ở chu kỳ sau
        pass


def _lenh_dc(dv, me, ten: str, p: dict):
    g = p.get
    if ten == "giao-ket/doi-chieu/chay":
        return dv.chay(me, ky_id=g("ky_id"), expected_context_sha256=g("expected_context_sha256"), khoa=g("khoa"))
    if ten == "giao-ket/doi-chieu/doi-soat":
        return dv.doi_soat(me, ky_id=g("ky_id"), expected_context_sha256=g("expected_context_sha256"), khoa=g("khoa"))
    raise DataError("NOT_FOUND", "Không có thao tác đối chiếu này.")


def _lenh_kiem(kiem, me, ten: str, p: dict):
    g = p.get
    if ten == "giao-ket/kiem/luu":
        return kiem.luu(me, ky_id=g("ky_id"), expected_revision=g("expected_revision"), checklist=g("checklist"), doi_tac_id=g("doi_tac_id"),
                        ma_junsky_id=g("ma_junsky_id"), ngay_hieu_luc=g("ngay_hieu_luc"), can_cu_ngay=g("can_cu_ngay"),
                        trich_dan_ngay=g("trich_dan_ngay"), ghi_chu=g("ghi_chu"), khoa=g("khoa"))
    if ten == "giao-ket/kiem/check":
        return kiem.check(me, ky_id=g("ky_id"), expected_revision=g("expected_revision"), khoa=g("khoa"))
    if ten == "giao-ket/kiem/xu-ly-lech":
        return kiem.xu_ly_lech(me, ky_id=g("ky_id"), expected_revision=g("expected_revision"), loai=g("loai"), muc_tieu_id=g("muc_tieu_id"),
                               ma_lech=g("ma_lech"), ly_do=g("ly_do"), khoa=g("khoa"))
    if ten == "giao-ket/kiem/bo-sung":
        return kiem.bo_sung(me, ky_id=g("ky_id"), expected_revision=g("expected_revision"), ly_do=g("ly_do"), khoa=g("khoa"))
    if ten == "giao-ket/kiem/hieu-luc":
        return kiem.hieu_luc(me, ky_id=g("ky_id"), expected_revision=g("expected_revision"), check_id=g("check_id"),
                             do_thi_sha256=g("do_thi_sha256"), khoa=g("khoa"))
    if ten == "giao-ket/kiem/tra-lai":
        return kiem.tra_lai(me, ky_id=g("ky_id"), expected_revision=g("expected_revision"), ly_do=g("ly_do"), khoa=g("khoa"))
    if ten == "giao-ket/kiem/tim-junsky":
        return kiem.tim_junsky(me, g("ky_id"), g("tu_khoa"))
    raise DataError("NOT_FOUND", "Không có thao tác kiểm hợp đồng này.")


def _khong_query(h, query) -> None:
    """Route G4 không nhận tham số truy vấn: cả query đã parse lẫn chuỗi thô (parse_qs bỏ `?x`/`?x=` rỗng) → 400, không xử lý."""
    if query or urlsplit(str(getattr(h, "path", "") or "")).query:
        raise DataError("CRM_G_YEU_CAU_SAI", "Không nhận tham số truy vấn.")


def _ky_ket(h, app, query=None):
    """G4 ký: query/header/khóa/kích thước kiểm trước; (1) dưới mutation lock — danh tính phiên + quyền/phạm vi hiện hành (không đọc bytes);
    (2) NGOÀI khóa — parse PDF (PDFium); (3) dưới khóa — lệnh ký một giao dịch (quyền lại → biên nhận → căn cứ → ghi bất biến → DA_KY).
    Mọi thẩm quyền/thông tin ký chỉ qua X-CRM-G-Info + body; query ngoài hợp đồng bị từ chối (không âm thầm bỏ qua)."""
    from ..k2 import crm_ky_ket as KY
    from .intake import MAX_FILE_SIZE
    _khong_query(h, query)
    encoded = h.headers.get("X-CRM-G-Info", "")
    if len(encoded) > 24000:  # mô tả sửa tối đa 2000 ký tự (UTF-8 percent-encoded)
        raise DataError("CRM_G_YEU_CAU_SAI", "Thông tin bản ký quá dài.")
    try:
        info = json.loads(unquote(encoded) or "{}")
    except ValueError:
        raise DataError("CRM_G_YEU_CAU_SAI", "Thông tin bản ký phải là JSON.") from None
    if not isinstance(info, dict):
        raise DataError("CRM_G_YEU_CAU_SAI", "Thông tin bản ký phải là object.")
    _than(info, TRUONG_KY)
    if (h.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower() not in MIME_KY:
        raise DataError("CRM_KY_PDF_HONG", "Bản ký phải gửi dạng PDF.")
    g = info.get
    KY.chuan_hoa(soan_id=g("soan_id"), expected_revision=g("expected_revision"), expected_xuat_id=g("expected_xuat_id"), ten_tep=g("ten_tep"),
                 ngay_ky=g("ngay_ky"), co_sua=g("co_sua"), mo_ta=g("mo_ta"), nguoi_ky_khach=g("nguoi_ky_khach"), khoa=g("khoa"))
    try:
        raw = h.body(MAX_FILE_SIZE)
    except DataError as exc:
        if exc.code == "FILE_TOO_LARGE":
            raise DataError("CRM_KY_TEP_QUA_LON", f"PDF bản ký tối đa {MAX_FILE_SIZE // (1024 * 1024)} MB.") from None
        raise
    with app.mutation_lock:
        _, me, _ = app.crm_phien(h.crm_sid())
        ky = dich_vu_ky(app)
        app._crm_db(ky.kiem_quyen, me, g("soan_id"))  # quyền + phạm vi TRƯỚC khi parse bytes PDF
    so_trang = KY.kiem_pdf_ky(raw)  # NGOÀI mutation lock/giao dịch
    with app.mutation_lock:
        _, me2, _ = app.crm_phien(h.crm_sid())
        if me2 != me:  # vai phiên đổi trong lúc kiểm PDF: không ký dưới danh tính khác
            raise DataError("CRM_G_DANH_TINH", "Vai phiên đã đổi trong lúc kiểm PDF — chưa ký. Gửi lại y nguyên để đối soát.")
        return app._crm_db(lambda: ky.ky(me, raw, soan_id=g("soan_id"), expected_revision=g("expected_revision"), expected_xuat_id=g("expected_xuat_id"),
                                         ten_tep=g("ten_tep"), ngay_ky=g("ngay_ky"), co_sua=g("co_sua"), mo_ta=g("mo_ta"),
                                         nguoi_ky_khach=g("nguoi_ky_khach"), khoa=g("khoa"), so_trang=so_trang))


def _lenh_gk(gk, me, ten: str, p: dict):
    g = p.get
    if ten == "bao-gia/luu":
        return gk.luu(me, bao_gia_id=g("bao_gia_id"), expected_revision=g("expected_revision"), du_lieu=g("du_lieu"), khoa=g("khoa"))
    if ten == "bao-gia/huy":
        return gk.huy(me, bao_gia_id=g("bao_gia_id"), expected_revision=g("expected_revision"), ly_do=g("ly_do"), khoa=g("khoa"))
    if ten == "bao-gia/chuyen":
        return gk.chuyen(me, bao_gia_id=g("bao_gia_id"), expected_revision=g("expected_revision"), mau_phien_ban_id=g("mau_phien_ban_id"), khoa=g("khoa"))
    if ten == "bao-gia/xem-truoc":
        return gk.xem_truoc(me, du_lieu=g("du_lieu"))
    if ten == "bao-gia/ty-gia-mac-dinh":
        return gk.sua_ty_gia_mac_dinh(me, ty_gia=g("ty_gia"), ly_do=g("ly_do"))
    if ten == "soan/luu":
        return gk.luu_soan(me, soan_id=g("soan_id"), expected_revision=g("expected_revision"), gia_tri_truong=g("gia_tri_truong"), bao_gia=g("bao_gia"),
                           doi_mau_phien_ban_id=g("doi_mau_phien_ban_id"), ly_do=g("ly_do"), khoa=g("khoa"))
    raise DataError("NOT_FOUND", "Không có thao tác báo giá/soạn này.")


def _dai_gk(h, app, ten: str, p: dict):
    """In báo giá / Xuất hợp đồng: (A) dưới mutation lock — danh tính phiên + quyền + biên nhận + chụp nhất quán trên kết nối chủ bảng đã kiểm;
    (B) NGOÀI mutation lock và mọi giao dịch — render/Word/PDF không có thông tin xác thực; (C) dưới mutation lock — quyền hiện hành + CAS
    revision + công bố. Kết nối chủ bảng đệm KHÔNG dùng ngoài khóa."""
    with app.mutation_lock:
        _, me, _ = app.crm_phien(h.crm_sid())
        gk = dich_vu_gk(app)
        if ten == "bao-gia/in":
            kh = app._crm_db(lambda: gk.chuan_bi_in(me, bao_gia_id=p.get("bao_gia_id"), expected_revision=p.get("expected_revision"), khoa=p.get("khoa")))
        else:
            kh = app._crm_db(lambda: gk.chuan_bi_xuat(me, soan_id=p.get("soan_id"), expected_revision=p.get("expected_revision"), khoa=p.get("khoa")))
    if "lap_lai" in kh:
        return kh["lap_lai"]
    kq = gk.render(kh)  # không khóa, không giao dịch, không DSN/token
    with app.mutation_lock:
        _, me2, _ = app.crm_phien(h.crm_sid())
        if me2 != me:  # vai phiên đổi trong lúc render: không công bố dưới danh tính khác; tệp đã giữ làm bằng chứng
            raise DataError("CRM_G_DANH_TINH", "Vai phiên đã đổi trong lúc xuất — tệp đã render được giữ, chưa công bố. Gửi lại y nguyên để đối soát.")
        return app._crm_db(gk.cong_bo, me, kh, kq)


def _than(payload: dict, cho_phep: set) -> dict:
    cam = sorted(k for k in payload if k in KHONG_NHAN)
    if cam:
        raise DataError("CRM_G_CLIENT_AUTHORITY", "Danh tính, pháp nhân, quyền, facts, trạng thái/duyệt và đường dẫn do máy chủ xác định; không nhận từ trình duyệt.")
    la = sorted(k for k in payload if k not in cho_phep)
    if la:
        raise DataError("CRM_G_YEU_CAU_SAI", "Yêu cầu có trường ngoài phạm vi: " + ", ".join(la[:5]))
    return payload


def _q(query: dict, ten: str):
    v = query.get(ten) or [None]
    if len(v) != 1:
        raise DataError("CRM_G_YEU_CAU_SAI", f"Tham số {ten} lặp.")
    return v[0] or None


def _lenh(svc, me, ten: str, p: dict):
    g = p.get
    if ten == "mau/anh-xa":
        return svc.luu_anh_xa(me, version_id=g("version_id"), map=g("map"), expected_graph=g("expected_graph"), khoa=g("khoa"))
    if ten == "mau/gui-kiem":
        return svc.gui_kiem(me, version_id=g("version_id"), expected_graph=g("expected_graph"), khoa=g("khoa"))
    if ten == "mau/kiem":
        return svc.kiem_mau(me, version_id=g("version_id"), expected_graph=g("expected_graph"), khoa=g("khoa"))
    if ten == "mau/tra-lai":
        return svc.tra_lai_mau(me, version_id=g("version_id"), ly_do=g("ly_do"), expected_graph=g("expected_graph"), khoa=g("khoa"))
    if ten == "mau/duyet":
        return svc.duyet_mau(me, version_id=g("version_id"), valid_from=g("valid_from"), expected_graph=g("expected_graph"), khoa=g("khoa"))
    if ten == "mau/tu-choi":
        return svc.tu_choi_mau(me, version_id=g("version_id"), ly_do=g("ly_do"), expected_graph=g("expected_graph"), khoa=g("khoa"))
    if ten == "mau/xem-thu":
        return svc.xem_thu(me, g("version_id"))
    if ten == "bo-chuan/lap":
        return svc.lap_bo_chuan(me, du_an_id=g("du_an_id"), giai_doan=g("giai_doan"), dong=g("dong"), khoa=g("khoa"))
    if ten == "bo-chuan/gui-duyet":
        return svc.gui_duyet_bo_chuan(me, version_id=g("version_id"), expected_graph=g("expected_graph"), khoa=g("khoa"))
    if ten == "bo-chuan/duyet":
        return svc.duyet_bo_chuan(me, version_id=g("version_id"), valid_from=g("valid_from"), expected_graph=g("expected_graph"), khoa=g("khoa"))
    raise DataError("NOT_FOUND", "Không có thao tác mẫu/bộ chuẩn này.")


def dieu_huong(h, app, post: bool, path: str, query: dict):
    """Một điểm vào cho route G (la_route). Tự trả lỗi có mã: 403 quyền / 404 đích ẩn / 409 CAS-idempotency-trạng thái / 413 / 400 / 503 cấu hình."""
    if _la_route_da(path):  # DA-1: khối riêng (cùng phiên/token/factory), lỗi map cùng quy tắc
        return _dieu_huong_da(h, app, post, path, query)
    try:
        if not post:
            if path == "/api/crm/mau":
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    data = app._crm_db(svc.danh_sach, me, _q(query, "as_of"))
                    return h.send_content(200, {**data, "ghi_nguon": {"san_sang": svc.conn_tin_cay is not None,
                                                                      "ly_do": getattr(svc, "ly_do_chua_san_sang", None)}})
            if path == "/api/crm/mau/so-sanh":
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    return h.send_content(200, app._crm_db(svc.so_sanh, me, _q(query, "a"), _q(query, "b")))
            m = re.fullmatch(r"/api/crm/mau/tep/(" + _UUID + ")", path)
            if m:
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    ten, raw = app._crm_db(dich_vu(app).tep_mau, me, m.group(1))  # quyền hiện hành TRƯỚC tra đường dẫn/hash
                return h.send_content(200, raw, _DOCX, {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(ten, safe=""),
                                                        "Cache-Control": "no-store"})
            m = re.fullmatch(r"/api/crm/mau/(" + _UUID + ")", path)
            if m:
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    return h.send_content(200, app._crm_db(dich_vu(app).chi_tiet, me, m.group(1)))
            # --- CRM-41-03 G2/G3 (đọc: quyền hiện hành trong cùng giao dịch RR trên kết nối chủ bảng)
            if path == "/api/crm/bao-gia/moc-chuan":
                _khong_query(h, query)
                with app.mutation_lock:
                    app.crm_phien(h.crm_sid())
                    from ..k2.crm_giao_ket import danh_muc_moc_chuan
                    return h.send_content(200, danh_muc_moc_chuan())
            if path == "/api/crm/bao-gia/ty-gia-mac-dinh":  # BG-1c: tỷ giá USD/VND mặc định chung (đọc; quyền hiện hành trong giao dịch)
                _khong_query(h, query)
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    return h.send_content(200, app._crm_db(dich_vu_gk(app).ty_gia_mac_dinh, me))
            if path == "/api/crm/bao-gia":
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    gk = dich_vu_gk(app)
                    return h.send_content(200, {**app._crm_db(gk.danh_sach, me), "ly_do_chua_san_sang": getattr(gk.mau, "ly_do_chua_san_sang", None)})
            m = re.fullmatch(r"/api/crm/bao-gia/(" + _UUID + ")", path)
            if m:
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    return h.send_content(200, app._crm_db(dich_vu_gk(app).chi_tiet, me, m.group(1)))
            m = re.fullmatch(r"/api/crm/soan/(" + _UUID + ")", path)
            if m:
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    return h.send_content(200, app._crm_db(dich_vu_gk(app).doc_soan, me, m.group(1)))
            m = re.fullmatch(r"/api/crm/giao-ket/tep/(" + _UUID + ")/(docx|pdf)", path)
            if m:
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    ten, raw, mime = app._crm_db(dich_vu_gk(app).tep, me, m.group(1), m.group(2))  # quyền hiện hành TRƯỚC tra kho
                return h.send_content(200, raw, mime, {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(ten, safe=""),
                                                       "Cache-Control": "no-store"})
            # --- CRM-41-04A G4 (đọc: không nhận query; quyền hiện hành trước căn cứ/hash/kho)
            m = re.fullmatch(r"/api/crm/giao-ket/ky/(" + _UUID + ")", path)
            if m:
                _khong_query(h, query)
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    return h.send_content(200, app._crm_db(dich_vu_ky(app).doc, me, m.group(1)))
            m = re.fullmatch(r"/api/crm/giao-ket/ban-ky/(" + _UUID + ")/tep", path)
            if m:
                _khong_query(h, query)
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    ten, raw, mime = app._crm_db(dich_vu_ky(app).tep, me, m.group(1))  # quyền + nhật ký truy cập TRƯỚC tra kho
                return h.send_content(200, raw, mime, {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(ten, safe=""),
                                                       "Cache-Control": "no-store"})
            # --- CRM-41-06A G6A (đọc: không nhận query; quyền + phạm vi hiện hành + nhật ký truy cập trước căn cứ/hash/kho)
            if path == "/api/crm/giao-ket/kiem":
                _khong_query(h, query)
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    return h.send_content(200, {"ds": app._crm_db(dich_vu_kiem(app).ds, me), "nguoi": {"dang_nhap": me}})  # actor do máy chủ trả (fence UI)
            m = re.fullmatch(r"/api/crm/giao-ket/kiem/(" + _UUID + ")", path)
            if m:
                _khong_query(h, query)
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    return h.send_content(200, app._crm_db(dich_vu_kiem(app).doc, me, m.group(1)))
            m = re.fullmatch(r"/api/crm/giao-ket/kiem/(" + _UUID + ")/tep/(ban-ky|g3)", path)
            if m:
                _khong_query(h, query)
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    ten, raw, mime = app._crm_db(dich_vu_kiem(app).tep, me, m.group(1), m.group(2))  # quyền + nhật ký TRƯỚC tra kho
                return h.send_content(200, raw, mime, {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(ten, safe=""),
                                                       "Cache-Control": "no-store"})
            # --- CRM G5-B đối chiếu (đọc: không nhận query; quyền + phạm vi hiện hành + nhật ký truy cập trước tra cứu)
            m = re.fullmatch(r"/api/crm/giao-ket/doi-chieu/(" + _UUID + ")", path)
            if m:
                _khong_query(h, query)
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    return h.send_content(200, app._crm_db(dich_vu_doi_chieu(app).doc, me, m.group(1)))
            if path == "/api/crm/bo-chuan":
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    if _q(query, "du_an_id") is not None:
                        return h.send_content(200, app._crm_db(svc.doc_bo_chuan, me, _q(query, "du_an_id"), _q(query, "giai_doan"), _q(query, "as_of")))
                    return h.send_content(200, app._crm_db(svc.danh_sach_bo_chuan, me))
        else:
            if path == "/api/crm/mau/tai":
                encoded = h.headers.get("X-CRM-G-Info", "")
                if len(encoded) > 4000:
                    raise DataError("CRM_G_YEU_CAU_SAI", "Thông tin tệp quá dài.")
                try:
                    info = json.loads(unquote(encoded) or "{}")
                except ValueError:
                    raise DataError("CRM_G_YEU_CAU_SAI", "Thông tin tệp phải là JSON.") from None
                if not isinstance(info, dict):
                    raise DataError("CRM_G_YEU_CAU_SAI", "Thông tin tệp phải là object.")
                _than(info, TRUONG_TAI)
                from ..nguon.mau_docx import GIOI_HAN
                try:
                    raw = h.body(GIOI_HAN["tep"])
                except DataError as exc:
                    if exc.code == "FILE_TOO_LARGE":
                        raise DataError("CRM_G_TEP_QUA_LON", f"Tệp mẫu tối đa {GIOI_HAN['tep'] // (1024 * 1024)} MB.") from None
                    raise
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    return h.send_content(200, app._crm_db(lambda: svc.tai_mau(me, raw, loai_hinh_id=info.get("loai_hinh_id"), ma_mau=info.get("ma_mau"),
                                                                               ten_tep=info.get("ten_tep"), khoa=info.get("khoa"))))
            if path == "/api/crm/giao-ket/ky-ket":  # CRM-41-04A G4
                kq = _ky_ket(h, app, query)
                _danh_thuc_g5(app)  # G5-B: việc bắt buộc đã ghi trong CHÍNH giao dịch ký; chỉ đánh thức worker, ACK G4 giữ nguyên
                return h.send_content(200, kq)
            ten = path[len("/api/crm/"):]
            if ten in TRUONG_DC:  # CRM G5-B lệnh ngắn (không query; chỉ ky_id + ngữ cảnh CAS + khóa)
                _khong_query(h, query)
                body = h.json_body()
                if not isinstance(body, dict):
                    raise DataError("CRM_G_YEU_CAU_SAI", "Thân yêu cầu phải là object.")
                if any(k in KHONG_NHAN_KIEM or k in KHONG_NHAN_DC for k in body):
                    raise DataError("CRM_G_CLIENT_AUTHORITY", "Expected, catalog, người chạy, kết quả và chế độ đối chiếu do máy chủ xác định; không nhận từ trình duyệt.")
                payload = _than(body, TRUONG_DC[ten])
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    kq = app._crm_db(_lenh_dc, dich_vu_doi_chieu(app), me, ten, payload)
                _danh_thuc_g5(app)
                return h.send_content(200, kq)
            if ten in TRUONG_KIEM:  # CRM-41-06A G6A lệnh ngắn (không query; chế độ G5/kết quả check không nhận từ trình duyệt)
                _khong_query(h, query)
                body = h.json_body()
                if not isinstance(body, dict):
                    raise DataError("CRM_G_YEU_CAU_SAI", "Thân yêu cầu phải là object.")
                if any(k in KHONG_NHAN_KIEM for k in body):
                    raise DataError("CRM_G_CLIENT_AUTHORITY", "Chế độ G5, kết quả check và hồ sơ pháp lý do máy chủ xác định; không nhận từ trình duyệt.")
                payload = _than(body, TRUONG_KIEM[ten])
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    return h.send_content(200, app._crm_db(_lenh_kiem, dich_vu_kiem(app), me, ten, payload))
            if ten in TRUONG_GK:  # CRM-41-03 lệnh ngắn
                payload = _than(h.json_body(), TRUONG_GK[ten])
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    return h.send_content(200, app._crm_db(_lenh_gk, dich_vu_gk(app), me, ten, payload))
            if ten in TRUONG_GK_DAI:  # CRM-41-03 lệnh dài: render NGOÀI mutation lock/giao dịch (tách khỏi nhánh lệnh chung)
                payload = _than(h.json_body(), TRUONG_GK_DAI[ten])
                return h.send_content(200, _dai_gk(h, app, ten, payload))
            if ten in TRUONG:
                payload = _than(h.json_body(), TRUONG[ten])
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    return h.send_content(200, app._crm_db(_lenh, svc, me, ten, payload))
        return h.send_content(404, {"error": "NOT_FOUND", "message": "Không tìm thấy chức năng này."})
    except DataError as exc:
        code = exc.code
        if code.startswith("CRM_MAU_") and code not in MA_413:  # parser fail-closed (tệp sai/nguy hiểm) → 400 với mã riêng
            status = 400
        else:
            status = (403 if code in MA_403 or code in MA_403_GK or code in MA_403_KY or code in MA_403_KIEM else 404 if code in MA_404
                      else 409 if code in MA_409 or code in MA_409_GK or code in MA_409_KY or code in MA_409_KIEM or code in MA_409_DC else 413 if code in MA_413 or code in MA_413_KY
                      else 503 if code in MA_503 or code in MA_503_KY else 400)
        loi = {"error": code, "message": str(exc)}
        if getattr(exc, "locator", "$") not in (None, "", "$"):  # BG-1c: lỗi theo trường (vd fx.ty_gia, gia.don_gia) để màn hình chỉ đúng ô
            loi["truong"] = exc.locator
        return h.send_content(status, loi)
    except (ValueError, TypeError, KeyError, RecursionError):
        return h.send_content(400, {"error": "INVALID_REQUEST", "message": "Thông tin gửi lên không hợp lệ; chưa xử lý."})
    except OSError:
        return h.send_content(500, {"error": "LOCAL_STORAGE_ERROR", "message": "Không đọc/ghi được kho trên máy. Tệp đã lưu vẫn được giữ."})


# ================================================================================================== DA-1 CRM · Dự án đang bán (QD-20261025-05…09)
# Khối riêng (lát C3 thêm route hợp đồng ở chỗ khác của tệp): cùng phiên cookie/token/mutation lock/factory G (`dich_vu`), không router thứ hai.
# Trình duyệt không gửi actor/pháp nhân/trạng thái/kết quả (KHONG_NHAN); ghi chỉ bán hàng/kế toán có module CRM — cổng thật ở CSDL (M0031).
TRUONG_DA = {
    "du-an-ban/bat-ban": {"du_an_id", "thong_tin", "phi", "ly_do", "khoa"},
    "du-an-ban/cap-nhat": {"da_ban_id", "expected_phien_ban", "thong_tin", "phi", "ly_do", "khoa"},
    "du-an-ban/phi": {"da_ban_id", "expected_phien_ban", "phi", "ly_do", "khoa"},
    "du-an-ban/lo": {"da_ban_id", "lo", "ly_do", "khoa"},
    "du-an-ban/ngung-ban": {"da_ban_id", "expected_phien_ban", "ly_do", "khoa"},
    "du-an-ban/mo-ban-lai": {"da_ban_id", "expected_phien_ban", "ly_do", "khoa"},
    "du-an-ban/tien-do": {"du_an_id", "expected_version", "giai_doan", "dong", "khoa"},  # G7 áp dụng ngay (bỏ CFO, QD-20261025-07)
}
MA_409_DA = frozenset({"CRM_DA_DA_CO", "CRM_DA_PHIEN_BAN_CU", "CRM_DA_LO_LAN_CU", "CRM_DA_TRANG_THAI", "CRM_DA_CHUA_BAT_BAN", "CRM_DA_NGAY_LUI",
                       "CRM_DA_DU_AN_DONG"})


def _la_route_da(path: str) -> bool:
    return path == "/api/crm/du-an-ban" or path.startswith("/api/crm/du-an-ban/")


def dich_vu_da(app):
    """DA-1: service dự án đang bán trên CHÍNH service G (cùng kết nối chủ bảng đã kiểm) — không factory/IAM thứ hai."""
    da = app.__dict__.get("_crm_da")
    if da is not None:
        return da
    with _KHOI_TAO:
        da = app.__dict__.get("_crm_da")
        if da is None:
            from ..k2.crm_du_an_ban import CrmDuAnBanK2
            cha = dich_vu(app)  # FIX02: cha trước, rồi đọc lại cache
            da = app.__dict__.get("_crm_da")
            if da is None:
                da = CrmDuAnBanK2(cha)
                app.__dict__["_crm_da"] = da
    return da


def _chi_query(h, query, cho_phep: set) -> None:
    """Kiểm cả query thô giữ giá trị rỗng: đúng khóa, tối đa một giá trị/khóa, đúng định dạng và độ dài trước khi chuyển kiểu."""
    from urllib.parse import parse_qs
    tho = urlsplit(str(getattr(h, "path", "") or "")).query
    du_lieu_tho = parse_qs(tho, keep_blank_values=True)
    la = (set(query or {}) | set(du_lieu_tho)) - set(cho_phep)
    if la:
        raise DataError("CRM_G_YEU_CAU_SAI", "Không nhận tham số truy vấn: " + ", ".join(sorted(la)[:5]))
    mau = {"dang_ban": r"[01]", "phien_ban": r"[0-9]{1,9}", "du_an_id": "(?i:" + _UUID + ")", "ngay": r"[0-9]{4}-[0-9]{2}-[0-9]{2}"}
    for nguon in (du_lieu_tho, query or {}):
        for ten, ds in nguon.items():
            if (not isinstance(ds, list) or len(ds) != 1 or not isinstance(ds[0], str)
                    or not re.fullmatch(mau[ten], ds[0]) or (ten == "phien_ban" and int(ds[0]) == 0)):
                raise DataError("CRM_G_YEU_CAU_SAI", "Tham số truy vấn không hợp lệ hoặc bị lặp: " + ten)


def _lenh_da(da, me, ten: str, p: dict):
    g = p.get
    if ten == "du-an-ban/bat-ban":
        return da.bat_ban(me, du_an_id=g("du_an_id"), thong_tin=g("thong_tin"), phi=g("phi"), ly_do=g("ly_do"), khoa=g("khoa"))
    if ten == "du-an-ban/cap-nhat":
        return da.cap_nhat(me, da_ban_id=g("da_ban_id"), expected_phien_ban=g("expected_phien_ban"), thong_tin=g("thong_tin"), phi=g("phi"),
                           ly_do=g("ly_do"), khoa=g("khoa"))
    if ten == "du-an-ban/phi":
        return da.sua_phi(me, da_ban_id=g("da_ban_id"), expected_phien_ban=g("expected_phien_ban"), phi=g("phi"), ly_do=g("ly_do"), khoa=g("khoa"))
    if ten == "du-an-ban/lo":
        return da.ghi_lo(me, da_ban_id=g("da_ban_id"), lo=g("lo"), ly_do=g("ly_do"), khoa=g("khoa"))
    if ten == "du-an-ban/ngung-ban":
        return da.ngung_ban(me, da_ban_id=g("da_ban_id"), expected_phien_ban=g("expected_phien_ban"), ly_do=g("ly_do"), khoa=g("khoa"))
    if ten == "du-an-ban/mo-ban-lai":
        return da.mo_ban_lai(me, da_ban_id=g("da_ban_id"), expected_phien_ban=g("expected_phien_ban"), ly_do=g("ly_do"), khoa=g("khoa"))
    if ten == "du-an-ban/tien-do":
        return da.ap_dung_tien_do(me, du_an_id=g("du_an_id"), expected_version=g("expected_version"), giai_doan=g("giai_doan"), dong=g("dong"), khoa=g("khoa"))
    raise DataError("NOT_FOUND", "Không có thao tác dự án đang bán này.")


def _ma_http_da(code: str) -> int:
    if code.startswith("CRM_MAU_") and code not in MA_413:
        return 400
    return (403 if code in MA_403 or code in MA_403_GK else 404 if code in MA_404
            else 409 if code in MA_409 or code in MA_409_GK or code in MA_409_DA else 413 if code in MA_413 else 503 if code in MA_503 else 400)


def _dieu_huong_da(h, app, post: bool, path: str, query: dict):
    """Route dự án đang bán. Lỗi có mã: 403 quyền / 404 không thấy / 409 phiên bản cũ-trạng thái-idempotency / 503 cấu hình / 400 nhập (kèm `truong`)."""
    try:
        if not post:
            if path == "/api/crm/du-an-ban":
                _chi_query(h, query, {"dang_ban"})
                dang_ban = _q(query, "dang_ban")
                if dang_ban not in (None, "0", "1"):
                    raise DataError("CRM_G_YEU_CAU_SAI", "Tham số dang_ban chỉ nhận 0 hoặc 1.")
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    da = dich_vu_da(app)
                    return h.send_content(200, {**app._crm_db(lambda: da.danh_sach(me, dang_ban=dang_ban == "1")),
                                                "ly_do_chua_san_sang": getattr(da.mau, "ly_do_chua_san_sang", None)})
            if path == "/api/crm/du-an-ban/anh-chup":
                _chi_query(h, query, {"du_an_id", "ngay"})
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    return h.send_content(200, app._crm_db(dich_vu_da(app).anh_chup_mac_dinh, me, _q(query, "du_an_id"), _q(query, "ngay")))
            m = re.fullmatch(r"/api/crm/du-an-ban/(" + _UUID + ")", path)
            if m:
                _chi_query(h, query, {"phien_ban", "ngay"})
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    return h.send_content(200, app._crm_db(lambda: dich_vu_da(app).chi_tiet(me, m.group(1), phien_ban=_q(query, "phien_ban"),
                                                                                             ngay=_q(query, "ngay"))))
            m = re.fullmatch(r"/api/crm/du-an-ban/(" + _UUID + ")/lich-su", path)
            if m:
                _chi_query(h, query, set())
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    return h.send_content(200, app._crm_db(dich_vu_da(app).lich_su, me, m.group(1)))
        else:
            ten = path[len("/api/crm/"):]
            if ten in TRUONG_DA:
                _chi_query(h, query, set())
                body = h.json_body()
                if not isinstance(body, dict):
                    raise DataError("CRM_G_YEU_CAU_SAI", "Thân yêu cầu phải là object.")
                payload = _than(body, TRUONG_DA[ten])
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    return h.send_content(200, app._crm_db(_lenh_da, dich_vu_da(app), me, ten, payload))
        return h.send_content(404, {"error": "NOT_FOUND", "message": "Không tìm thấy chức năng này."})
    except DataError as exc:
        loi = {"error": exc.code, "message": str(exc)}
        if getattr(exc, "locator", "$") not in (None, "", "$"):  # lỗi theo trường (vd thong_tin.don_gia_niem_yet, phi.0.muc, lo.2.dien_tich)
            loi["truong"] = exc.locator
        return h.send_content(_ma_http_da(exc.code), loi)
    except (ValueError, TypeError, KeyError, RecursionError):
        return h.send_content(400, {"error": "INVALID_REQUEST", "message": "Thông tin gửi lên không hợp lệ; chưa xử lý."})
    except OSError:
        return h.send_content(500, {"error": "LOCAL_STORAGE_ERROR", "message": "Không đọc/ghi được kho trên máy."})
