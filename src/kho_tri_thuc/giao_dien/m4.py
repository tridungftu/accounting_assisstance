"""M4-01 — HTTP mỏng cho Cổng hồ sơ xây dựng trên LocalApp hiện có (cùng token X-KTT-Token, phiên cookie HttpOnly do máy chủ cấp, mutation lock,
cùng kết nối login ứng dụng + cổng lineage của CRM). Không webserver/iframe nguồn, không X-HD, không nhận đường dẫn/URL/actor/PN/cờ duyệt từ
trình duyệt. Route contract: docs/BAO-CAO-M4-01C.md.
M4-01C: thêm GET /api/m4/mau (danh sách) và /api/m4/mau/{tên cố định} (bytes tệp mẫu DEMO) cho phiên có quyền soạn M4 hiện hành.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

from ..ha_tang.primitives import DataError

ASSETS = Path(__file__).resolve().parents[1] / "m4" / "giao_dien"  # tài sản UI riêng của package M4 (m4.js, m4.css)
KHONG_NHAN = frozenset({"actor", "nguoi", "dang_nhap_thuc_hien", "phap_nhan_id", "phap_nhan", "trang_thai", "da_trich", "da_xac_nhan", "xac_nhan_boi",
                        "approved", "duyet", "nguoi_duyet", "proven", "PROVEN", "module", "quyen", "vai", "vai_tro_nguoi_dung", "path", "duong_dan", "url",
                        "dsn", "snapshot", "digest", "raw_sha256", "sha256", "object_key", "receipt", "bien_nhan"})
TRUONG = {
    "danh-tinh": {"dang_nhap"},
    "hop-dong/tao": {"du_an_id", "so_hop_dong", "ten", "khoa"},
    # MASTER-REUSE-02: nhận master có sẵn / gắn đối tác — chỉ ID/CAS token/lý do/khóa; PN/module/owner/trạng thái/actor do CSDL suy ra
    "hop-dong/nhan-master": {"du_an_id", "hop_dong_id", "ten", "expected_master", "khoa"},
    "hop-dong/gan-doi-tac": {"hop_dong_id", "doi_tac_id", "mapping_id", "revision", "expected_master", "expected_mapping", "ly_do", "khoa"},
    "hop-dong/gan-tep": {"hop_dong_id", "revision", "tep_id", "khoa"},
    "hop-dong/trich": {"hop_dong_id", "revision", "khoa"},
    "tham-so/sua": {"hop_dong_id", "revision", "ma", "trang_thai_tham_so", "gia_tri", "don_vi", "dieu_khoan", "trich_dan", "ly_do", "khoa"},
    "tham-so/xac-nhan": {"hop_dong_id", "revision", "ly_do", "khoa"},
    "phu-luc/khai": {"hop_dong_id", "revision", "khai", "khoa"},
    "phu-luc/them": {"hop_dong_id", "revision", "so_pl", "ngay_ky", "ngay_hieu_luc", "trang_thai_phu_luc", "doi_boq", "noi_dung", "tep_id", "khoa"},
    "phu-luc/huy": {"phu_luc_id", "revision", "ly_do", "khoa"},
    "boq/xem": {"tep_id", "sheet"},
    "boq/nhap": {"hop_dong_id", "revision", "tep_id", "phu_luc_id", "sheet", "hang_tieu_de", "cot", "khoa"},
    "dot/tao": {"hop_dong_id", "so_dot", "ngay_nghiem_thu", "khoa"},
    "dot/sua": {"dot_id", "revision", "ngay_nghiem_thu", "khoa"},
    "dot/gan-tep": {"dot_id", "revision", "tep_id", "muc", "khoa"},
    "dot/nop": {"dot_id", "revision_ho_so", "revision_dot", "khoa"},
    # M4-02A Review L1/L2: chỉ ID/lựa chọn/expected basis/khóa — không facts máy, đường dẫn, actor hay cờ duyệt
    "review/chay": {"du_an_id", "tep_id", "che_do", "dot_id", "o_dich", "expected_basis", "khoa"},
    "review/chay-lai": {"run_id", "expected_basis", "khoa"},
    "review/ghep": {"run_id", "khoa_dong", "boq_id", "ma_hm", "expected_basis", "ly_do", "khoa"},
    # M4-02B Chứng từ L3: bộ tệp lấy từ liên kết đợt trong PG (không danh sách đường dẫn/bytes/hash từ trình duyệt); row_id do máy chủ cấp
    "chung-tu/chay": {"dot_id", "revision", "expected_basis", "khoa"},
    "chung-tu/chay-lai": {"run_id", "revision", "expected_basis", "khoa"},
    "chung-tu/sua": {"run_id", "revision", "tai_lieu", "expected_basis", "ly_do", "khoa"},
    "chung-tu/ghep": {"run_id", "row_id", "boq_id", "boq_dong", "ma_hm", "revision", "expected_basis", "ly_do", "khoa"},
    # M4-02C Duyệt & PDF (docs/M4-02C-UI-CONTRACT.md): chỉ ID/revision/expected basis/số chấp nhận (chuỗi thập phân|null)/lý do/khóa — không actor,
    # cờ duyệt, hash, trạng thái hay số đề xuất từ trình duyệt
    "duyet/ket-luan": {"dot_id", "version_id", "revision", "expected_basis", "gia_tri_nt", "so_xin_thanh_toan", "tam_ung", "thu_hoi", "giu_lai",
                       "tien_te", "dong_nt", "xu_ly_phat_hien", "ly_do", "khoa"},
    "duyet/chap-thuan": {"dot_id", "version_id", "revision", "expected_basis", "ket_luan_id", "ly_do", "khoa"},
    "duyet/phien-ban": {"dot_id", "parent_version_id", "revision", "expected_basis", "ly_do", "khoa"},
    "duyet/phien-ban/nop": {"dot_id", "version_id", "revision", "expected_basis", "khoa"},
}
REVIEW_GET = {"hop_dong_id", "dot_id", "tep_id", "che_do", "o_dich"}
CHUNG_TU_GET = {"dot_id"}
DUYET_GET = {"dot_id", "version_id"}
MASTER_GET = {"du_an_id", "q", "limit"}  # MASTER-REUSE-02: bộ chọn master/đối tác (mỗi khóa một giá trị; q ≤100, limit 1–50 kiểm ở service + CSDL)
TRUONG_TEP = {"du_an_id", "vai_tro", "ten", "media_type", "khoa"}
TRUONG_DUYET_PDF = {"dot_id", "version_id", "revision", "expected_basis", "ten", "media_type", "khoa"}
# M4-03A Kế toán nghiệm thu (docs/GIAO-CODE-M4-03A-GUI.md §2, API-CONTRACT + ADDENDUM-01): đúng allowlist backend handoff §4 — không amount/pass/actor/PN/
# owner/approval/ledger ở lệnh xác nhận; danh tính lấy từ phiên hiện hành
KT_GET = {"phong_bi_id"}
TRUONG_KT = {
    "ke-toan/luu": {"kt_pending_id", "phong_bi_id", "expected_phong_bi_sha256", "expected_revision", "gia_tri_nt_xac_nhan", "tien_te", "co_so_gia_tri",
                    "tam_ung_xac_nhan", "thu_hoi_xac_nhan", "giu_lai_xac_nhan", "vat_trang_thai", "vat_can_cu_tep_id", "vat_trich_dan", "ly_do", "khoa"},
    "ke-toan/xac-nhan": {"kt_pending_id", "phong_bi_id", "kt_revision_id", "expected_revision", "expected_phong_bi_sha256", "khoa"},
}
MA_422_KT = frozenset({"M4_YEU_CAU_SAI", "M4_THAM_SO_SAI", "M4_THIEU_THONG_TIN", "M4_KHOA_THAO_TAC", "INVALID_REQUEST"})  # chỉ route /api/m4/ke-toan*
# M4-03A FIX01: mã miền KT của backend (docs/M4-03A-GUI-FIX01-BACKEND-REFERENCE.py:68–76) — CHỈ áp trên route /api/m4/ke-toan*, tra ĐÚNG mã (không suy
# theo tiền tố). Mã chung giữ bảng toàn cục (M4_CLIENT_AUTHORITY/M4_CHI_MAY_CHU_NGUON 403, M4_IDEMPOTENCY_KHAC 409, 503 có sẵn); mã lạ giữ 400.
MA_KT = {"M4_KT_PHAM_VI": 403, "M4_KT_KHONG_THAY": 404,
         **dict.fromkeys(("M4_KT_NGUON_CU", "M4_KT_NGUON_DOI", "M4_KT_CAN_KIEM_LAI", "M4_KT_REVISION_CU", "M4_KT_DA_XAC_NHAN", "M4_KT_CHO_BO_SUNG",
                          "M4_KT_XAC_NHAN_KHAC_NHAP", "M4_KT_NGUON_HONG"), 409),
         **dict.fromkeys(("M4_KT_SO_SAI", "M4_KT_TRUONG_SAI", "M4_KT_VAT_SAI", "M4_KT_CO_SO_SAI", "M4_KT_TIEN_TE_KHAC", "M4_KT_CAN_CU_VAT_SAI"), 422),
         "M4_KT_SAI_DTO": 500}
KT_SAI_DTO_MSG = "Dữ liệu máy chủ kế toán nghiệm thu không đúng hợp đồng M4_03A_KT_V1 — chưa trả cho trình duyệt."  # 500: không lộ chi tiết nội bộ
MA_403 = frozenset({"M4_KHONG_CO_QUYEN_DU_AN", "M4_CLIENT_AUTHORITY", "DANH_TINH_M4", "DANH_TINH", "DANH_TINH_MO_PHONG", "M4_CHI_CHU",
                    "M4_HOP_DONG_CHI_CHU", "M4_DANH_TINH", "M4_CHI_MAY_CHU_NGUON", "M4_QUYEN_CHI_QUAN_TRI", "LOCAL_HOST_ONLY", "CROSS_ORIGIN", "SESSION_TOKEN",
                    "M4_REVIEW_PHAM_VI", "M4_CHUNG_TU_PHAM_VI", "M4_DUYET_PHAM_VI"})
MA_404 = frozenset({"NOT_FOUND", "M4_KHONG_THAY_HOP_DONG", "M4_KHONG_THAY_DOT", "M4_KHONG_THAY_TEP", "M4_KHONG_THAY_PHU_LUC", "M4_REVIEW_KHONG_THAY",
                    "M4_TEP_KHONG_CO_TRONG_KHO", "M4_CHUNG_TU_KHONG_THAY", "M4_DUYET_KHONG_THAY",
                    "M4_MASTER_KHONG_THAY", "M4_MAPPING_KHONG_THAY"})
# M4-02C: căn cứ/phiên bản/kết luận cũ, đã chấp thuận/seal, thiếu số liệu bắt buộc, ID không thuộc đồ thị, blob khác nội dung → tải lại/xem lại, giữ nháp
MA_409_DUYET = frozenset({"M4_DUYET_CO_SO_DOI", "M4_DUYET_PHIEN_BAN_CU", "M4_DUYET_PHIEN_BAN_NHAP", "M4_DUYET_DA_CHAP_THUAN", "M4_DUYET_DA_SEAL",
                          "M4_DUYET_KET_LUAN_CU", "M4_DUYET_THIEU_CAN_CU", "M4_DUYET_CHUA_CO_REVIEW", "M4_DUYET_DA_CO_NHAP", "M4_DUYET_DONG_KHONG_THUOC",
                          "M4_DUYET_PHAT_HIEN_KHONG_THUOC", "M4_DUYET_CAN_PHIEN_BAN_MOI", "M4_DUYET_CHUA_KET_LUAN", "ARTIFACT_CHANGED"})
MA_409_REVIEW = frozenset({"M4_REVIEW_CO_SO_DOI", "M4_REVIEW_CHA_SAI", "M4_REVIEW_DONG_KHONG_CO", "M4_REVIEW_BOQ_KHONG_HIEN_HANH", "M4_REVIEW_DICH_MO_HO",
                           "M4_REVIEW_DICH_KHONG_HIEU_LUC",
                           "M4_REVIEW_DA_CHOT", "M4_REVIEW_TEP_DOI", "M4_TEP_HONG_LUU_TRU",
                           # M4-02B
                           "M4_CHUNG_TU_CO_SO_DOI", "M4_CHUNG_TU_CHA_SAI", "M4_CHUNG_TU_DONG_KHONG_CO", "M4_CHUNG_TU_TEP_KHONG_THUOC", "M4_CHUNG_TU_DA_CHOT"})
MA_409 = frozenset({"M4_REVISION_CU", "M4_IDEMPOTENCY_KHAC", "M4_DANG_XU_LY", "M4_HOP_DONG_DA_CO", "M4_HOP_DONG_DA_CO_NOI_KHAC", "M4_DOT_DA_CO",
                    "M4_DOT_DA_NOP", "M4_DA_XAC_NHAN", "M4_PHU_LUC_DA_CO", "M4_KHONG_DOI", "M4_CHUA_DU_CAN_CU", "M4_KHAI_PHU_LUC_MAU_THUAN",
                    "M4_TRICH_KHAC_TEP", "M4_TRICH_HASH_KHAC", "M4_CHUA_TRICH", "M4_CHUA_TRICH_DUNG_NGUON", "M4_THAM_SO_CON_TRONG",
                    "M4_THAM_SO_KHONG_DU_DANH_MUC", "M4_DANH_MUC_DOI", "M4_DOCX_CON_SUA_DOI", "M4_TEP_XUNG_DOT", "M4_QUYEN_BAT_BIEN",
                    # MASTER-REUSE-02: CAS master/mapping cũ, nguồn khác quản lý, đã nộp (cần phiên bản điều chỉnh), căn cứ nguồn đổi lúc nộp
                    "M4_MASTER_DA_DOI", "M4_MAPPING_DA_DOI", "M4_MASTER_CAN_SUA_TAI_NGUON", "M4_MASTER_CAN_PHIEN_BAN_DIEU_CHINH",
                    "M4_MASTER_CAN_CU_DOI"})
# MASTER-REUSE-02: dữ kiện nguồn không cho phép (mapping đóng/mơ hồ, trạng thái master, đối tác, thiếu lý do) → 422; mã chỉ phát sinh từ gói này
MA_422_MASTER = frozenset({"M4_MAPPING_KHONG_HIEN_HANH", "M4_MAPPING_MO_HO", "M4_MASTER_TRANG_THAI_KHONG_NHAN", "M4_DOI_TAC_KHONG_HOP_LE",
                           "M4_LY_DO_BAT_BUOC"})
MA_413 = frozenset({"M4_TEP_QUA_LON", "FILE_TOO_LARGE"})
MA_503 = frozenset({"M4_NGUON_REVIEW_CHUA_NAP", "M4_NGUON_REVIEW_SAI_PIN", "M4_NGUON_REVIEW_XUNG_DOT", "M4_NGUON_REVIEW_CHUA_GHIM",
                    "M4_TRICH6_CHUA_SAN_SANG", "M4_TRICH6_CHUA_RO", "TRICH6_URL_SAI", "TRICH6_CHUA_SAN_SANG",
                    "M4_CHUA_SAN_SANG_GHI_NGUON", "CRM_SCHEMA_KHONG_KHOP", "PG_KHONG_KET_NOI",
                    "M4_KET_QUA_CHUA_RO",  # M4-02B FIX01: commit chưa rõ — trình duyệt giữ khóa/body, gửi lại để đối soát
                    "M4_KT_CHUA_NOI"})  # M4-03A: backend kế toán nghiệm thu chưa compose (wrapper XayDungK2._kt)
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


def dich_vu(app):
    """Factory máy chủ (B1): service M4 dùng kết nối login ứng dụng + cổng lineage của CRM cho đọc/lệnh thường, và kết nối CHỦ BẢNG của máy chủ
    (cùng đường `_m5_ket_noi_chu` đã kiểm đích/chủ bảng của M5/M2) làm đường ghi nguồn tin cậy. Không nhận DSN/đường dẫn từ request; không cấp vai
    worker cho app_web. Chưa có admin DSN hoặc không kết nối được → conn_tin_cay=None: tải tệp/trích/BOQ/sửa tham số báo M4_CHUA_SAN_SANG_GHI_NGUON
    (không fallback sang quyền người dùng thường); route đọc vẫn chạy."""
    svc = app.__dict__.get("_m4")
    if svc is None:
        from ..k2.xay_dung import XayDungK2
        crm = app.crm()
        try:
            tin_cay, ly_do = app._m5_ket_noi_chu(crm.conn), None
        except DataError as exc:
            tin_cay, ly_do = None, exc.code
        if tin_cay is None and ly_do is None:
            ly_do = "CHUA_CAU_HINH_ADMIN_DSN"
        svc = XayDungK2(crm.conn, app.root / "m4-k2", conn_tin_cay=tin_cay, hom_nay=crm.hom_nay)
        svc.ly_do_chua_san_sang = ly_do
        app.__dict__["_m4"] = svc
    return svc


def _mau_tao(ten_bang: str, **kw):
    def tao():
        from ..kiem_chung import fixtures_m4 as F
        return F.boq_xlsx(getattr(F, ten_bang), **kw)
    return tao


def _mau_docx(track_changes: bool):
    def tao():
        from ..kiem_chung import fixtures_m4 as F
        return F.hop_dong_docx(track_changes=track_changes)
    return tao


def _mau_pdf(nhan: str):
    def tao():
        from ..kiem_chung import fixtures_m4 as F
        return F.pdf_demo(nhan)
    return tao


_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# M4-01C: tệp mẫu DEMO cố định (tên cố định → builder có sẵn trong kiem_chung/fixtures_m4.py). Chỉ trả BYTES nguồn để người dùng chọn rồi tải lên
# qua đúng POST /api/m4/tep như tệp thật — không ghi gì, không seed trích XONG/BOQ DA_MAP/xác nhận/nộp/biên nhận. Không nhận đường dẫn từ trình duyệt.
MAU = {  # tên tệp → (vai tài liệu gợi ý, media, builder, mô tả)
    "hop_dong.docx": ("HOP_DONG", _DOCX, _mau_docx(False), "Hợp đồng thi công DEMO (Word, đã chốt sửa đổi)"),
    "hop_dong_con_sua_doi.docx": ("HOP_DONG", _DOCX, _mau_docx(True), "Hợp đồng DEMO còn Track Changes — ca phải bị chặn"),
    "hop_dong.pdf": ("HOP_DONG", "application/pdf", _mau_pdf("HOP_DONG"), "Hợp đồng PDF — trích chưa hỗ trợ (OCR chưa bật)"),
    "boq_goc.xlsx": ("BOQ", _XLSX, _mau_tao("BOQ_GOC"), "BOQ gốc DEMO, không phát hiện"),
    "boq_lech_so_hoc.xlsx": ("BOQ", _XLSX, _mau_tao("BOQ_LOI_SO_HOC"), "BOQ có thành tiền 999 lệch KL×ĐG — phát hiện, không chặn"),
    "boq_trong_va_0.xlsx": ("BOQ", _XLSX, _mau_tao("BOQ_TRONG_VA_0"), "BOQ có ô khối lượng trống và ô 0 tường minh"),
    "boq_so_khong_doc.xlsx": ("BOQ", _XLSX, _mau_tao("BOQ_SO_KHONG_DOC"), "BOQ có khối lượng là chữ — lỗi chặn"),
    "boq_ten_gia_loi.xlsx": ("BOQ", _XLSX, _mau_tao("BOQ_TEN_GIA_LOI"), "BOQ tên giống thông điệp số học + KL 'abc' — lỗi chặn"),
    "boq_phu_luc.xlsx": ("BOQ", _XLSX, _mau_tao("BOQ_PHU_LUC"), "BOQ phụ lục DEMO (thay HM-02, thêm HM-04)"),
    "phu_luc_01.pdf": ("PHU_LUC", "application/pdf", _mau_pdf("PHU_LUC_01"), "Phụ lục 01 DEMO (PDF)"),
    "ho_so_dot_ky1.pdf": ("HO_SO_DOT", "application/pdf", _mau_pdf("HO_SO_KY1"), "Tài liệu hồ sơ đợt kỳ 1 DEMO"),
    "ho_so_dot_ky2.pdf": ("HO_SO_DOT", "application/pdf", _mau_pdf("HO_SO_KY2"), "Tài liệu hồ sơ đợt kỳ 2 DEMO"),
}


def _kiem_mau(svc, me):
    """Tệp mẫu chỉ cho phiên hiện hành có quyền soạn M4 (PHU_TRACH + DU_AN, module M4 hiện hành) ở ít nhất một dự án — quyền đọc từ CSDL."""
    if not any(p.get("soan") for p in svc.tong_quan(me)["pham_vi"]):
        raise DataError("M4_KHONG_CO_QUYEN_DU_AN", "Tệp mẫu DEMO chỉ dành cho phòng dự án đang có quyền soạn hồ sơ M4.")


def _than(payload: dict, cho_phep: set) -> dict:
    cam = sorted(k for k in payload if k in KHONG_NHAN)
    if cam:
        raise DataError("M4_CLIENT_AUTHORITY", "Danh tính, pháp nhân, quyền, trạng thái xác nhận/duyệt và đường dẫn do máy chủ xác định; không nhận từ trình duyệt.")
    la = sorted(k for k in payload if k not in cho_phep)
    if la:
        raise DataError("M4_YEU_CAU_SAI", "Yêu cầu có trường ngoài phạm vi: " + ", ".join(la[:5]))
    return payload


def trang_thai(app, me) -> dict:
    try:
        svc = dich_vu(app)
    except DataError as exc:
        if exc.code == "CRM_CHUA_CAU_HINH":
            return {"cau_hinh": False, "ly_do": str(exc)}
        raise
    from ..k2.m4_demo import dang_nhap_m4
    demo = [dict(r) for r in svc.conn.execute("""SELECT dang_nhap, vai_tro FROM master.nguoi_dung WHERE mo_phong AND trang_thai = 'HOAT_DONG'
                                                 AND dang_nhap = ANY(%s) ORDER BY dang_nhap""", (dang_nhap_m4(),))]
    return {"cau_hinh": True, **app._crm_db(svc.tong_quan, me), "danh_tinh_demo": demo,
            "ghi_nguon": {"san_sang": svc.conn_tin_cay is not None, "ly_do": getattr(svc, "ly_do_chua_san_sang", None)}}


def _lenh(app, svc, me, path: str, p: dict):
    g = p.get
    if path == "hop-dong/tao":
        return svc.tao_hop_dong(me, du_an_id=g("du_an_id"), so_hop_dong=g("so_hop_dong"), ten=g("ten"), khoa=g("khoa"))
    if path == "hop-dong/nhan-master":
        return svc.nhan_master_hop_dong(me, du_an_id=g("du_an_id"), hop_dong_id=g("hop_dong_id"), ten=g("ten"), expected_master=g("expected_master"),
                                        khoa=g("khoa"))
    if path == "hop-dong/gan-doi-tac":
        return svc.gan_doi_tac_hop_dong(me, hop_dong_id=g("hop_dong_id"), doi_tac_id=g("doi_tac_id"), mapping_id=g("mapping_id"), revision=g("revision"),
                                        expected_master=g("expected_master"), expected_mapping=g("expected_mapping"), ly_do=g("ly_do"), khoa=g("khoa"))
    if path == "hop-dong/gan-tep":
        return svc.gan_tep_hop_dong(me, hop_dong_id=g("hop_dong_id"), revision=g("revision"), tep_id=g("tep_id"), khoa=g("khoa"))
    if path == "hop-dong/trich":
        return svc.trich(me, hop_dong_id=g("hop_dong_id"), revision=g("revision"), khoa=g("khoa"))
    if path == "tham-so/sua":
        return svc.sua_tham_so(me, hop_dong_id=g("hop_dong_id"), revision=g("revision"), ma=g("ma"), trang_thai_tham_so=g("trang_thai_tham_so"),
                               gia_tri=g("gia_tri"), don_vi=g("don_vi"), dieu_khoan=g("dieu_khoan"), trich_dan=g("trich_dan"), ly_do=g("ly_do"), khoa=g("khoa"))
    if path == "tham-so/xac-nhan":
        return svc.xac_nhan(me, hop_dong_id=g("hop_dong_id"), revision=g("revision"), ly_do=g("ly_do"), khoa=g("khoa"))
    if path == "phu-luc/khai":
        return svc.khai_phu_luc(me, hop_dong_id=g("hop_dong_id"), revision=g("revision"), khai=g("khai"), khoa=g("khoa"))
    if path == "phu-luc/them":
        return svc.them_phu_luc(me, hop_dong_id=g("hop_dong_id"), revision=g("revision"), so_pl=g("so_pl"), ngay_ky=g("ngay_ky"),
                                ngay_hieu_luc=g("ngay_hieu_luc"), trang_thai_phu_luc=g("trang_thai_phu_luc"), doi_boq=g("doi_boq"),
                                noi_dung=g("noi_dung"), tep_id=g("tep_id"), khoa=g("khoa"))
    if path == "phu-luc/huy":
        return svc.huy_phu_luc(me, phu_luc_id=g("phu_luc_id"), revision=g("revision"), ly_do=g("ly_do"), khoa=g("khoa"))
    if path == "boq/xem":
        return svc.boq_xem(me, tep_id=g("tep_id"), sheet=g("sheet"))
    if path == "boq/nhap":
        return svc.boq_nhap(me, hop_dong_id=g("hop_dong_id"), revision=g("revision"), tep_id=g("tep_id"), phu_luc_id=g("phu_luc_id"),
                            sheet=g("sheet"), hang_tieu_de=g("hang_tieu_de"), cot=g("cot"), khoa=g("khoa"))
    if path == "dot/tao":
        return svc.tao_dot(me, hop_dong_id=g("hop_dong_id"), so_dot=g("so_dot"), ngay_nghiem_thu=g("ngay_nghiem_thu"), khoa=g("khoa"))
    if path == "dot/sua":
        return svc.sua_dot(me, dot_id=g("dot_id"), revision=g("revision"), ngay_nghiem_thu=g("ngay_nghiem_thu"), khoa=g("khoa"))
    if path == "dot/gan-tep":
        return svc.gan_tep_dot(me, dot_id=g("dot_id"), revision=g("revision"), tep_id=g("tep_id"), muc=g("muc"), khoa=g("khoa"))
    if path == "dot/nop":
        return svc.nop(me, dot_id=g("dot_id"), revision_ho_so=g("revision_ho_so"), revision_dot=g("revision_dot"), khoa=g("khoa"))
    if path == "review/chay":
        return svc.review_chay(me, du_an_id=g("du_an_id"), tep_id=g("tep_id"), mode=g("che_do"), dot_id=g("dot_id"), o_dich=g("o_dich"),
                               expected_basis=g("expected_basis"), khoa=g("khoa"))
    if path == "review/chay-lai":
        return svc.review_chay_lai(me, run_id=g("run_id"), expected_basis=g("expected_basis"), khoa=g("khoa"))
    if path == "review/ghep":
        return svc.review_ghep(me, run_id=g("run_id"), khoa_dong=g("khoa_dong"), boq_id=g("boq_id"), ma_hm=g("ma_hm"), expected_basis=g("expected_basis"),
                               ly_do=g("ly_do"), khoa=g("khoa"))
    if path == "chung-tu/chay":
        return svc.chung_tu_chay(me, dot_id=g("dot_id"), revision=g("revision"), expected_basis=g("expected_basis"), khoa=g("khoa"))
    if path == "chung-tu/chay-lai":
        return svc.chung_tu_chay_lai(me, run_id=g("run_id"), revision=g("revision"), expected_basis=g("expected_basis"), khoa=g("khoa"))
    if path == "chung-tu/sua":
        return svc.chung_tu_sua(me, run_id=g("run_id"), revision=g("revision"), tai_lieu=g("tai_lieu"), expected_basis=g("expected_basis"),
                                ly_do=g("ly_do"), khoa=g("khoa"))
    if path == "chung-tu/ghep":
        return svc.chung_tu_ghep(me, run_id=g("run_id"), row_id=g("row_id"), boq_id=g("boq_id"), boq_dong=g("boq_dong"), ma_hm=g("ma_hm"),
                                 revision=g("revision"), expected_basis=g("expected_basis"), ly_do=g("ly_do"), khoa=g("khoa"))
    if path == "duyet/ket-luan":
        return svc.duyet_ket_luan(me, dot_id=g("dot_id"), version_id=g("version_id"), revision=g("revision"), expected_basis=g("expected_basis"),
                                  gia_tri_nt=g("gia_tri_nt"), so_xin_thanh_toan=g("so_xin_thanh_toan"), tam_ung=g("tam_ung"), thu_hoi=g("thu_hoi"),
                                  giu_lai=g("giu_lai"), tien_te=g("tien_te"), dong_nt=g("dong_nt"), xu_ly_phat_hien=g("xu_ly_phat_hien"),
                                  ly_do=g("ly_do"), khoa=g("khoa"))
    if path == "duyet/chap-thuan":
        return svc.duyet_chap_thuan(me, dot_id=g("dot_id"), version_id=g("version_id"), revision=g("revision"), expected_basis=g("expected_basis"),
                                    ket_luan_id=g("ket_luan_id"), ly_do=g("ly_do"), khoa=g("khoa"))
    if path == "duyet/phien-ban":
        return svc.duyet_phien_ban(me, dot_id=g("dot_id"), parent_version_id=g("parent_version_id"), revision=g("revision"),
                                   expected_basis=g("expected_basis"), ly_do=g("ly_do"), khoa=g("khoa"))
    if path == "duyet/phien-ban/nop":
        return svc.duyet_phien_ban_nop(me, dot_id=g("dot_id"), version_id=g("version_id"), revision=g("revision"), expected_basis=g("expected_basis"),
                                       khoa=g("khoa"))
    raise DataError("NOT_FOUND", "Không có thao tác M4 này.")


REVIEW_LENH = frozenset({"review/chay", "review/chay-lai", "review/ghep"})
CHUNG_TU_LENH = frozenset({"chung-tu/chay", "chung-tu/chay-lai", "chung-tu/sua", "chung-tu/ghep"})  # M4-02B: khóa phiên + CPU/worker → kết nối riêng
# M4-02C: lệnh duyệt giữ khóa HĐ → đợt → phiên bản trong giao dịch chủ bảng (có thể chờ khóa của lệnh khác) → kết nối riêng, ngoài mutation lock
DUYET_LENH = frozenset({"duyet/ket-luan", "duyet/chap-thuan", "duyet/phien-ban", "duyet/phien-ban/nop"})
# CRM-41-01: lệnh trích tham số gọi engine #6 dùng chung (mạng + tính lâu) → cùng seam kết nối riêng, ngoài mutation lock toàn cục
LENH_RIENG = REVIEW_LENH | CHUNG_TU_LENH | DUYET_LENH | {"hop-dong/trich"}


def _ket_noi_review(app):
    """FIX01 R3 — cặp kết nối RIÊNG của MỘT thao tác Review: login ứng dụng thường (kiem_role_ung_dung) + kết nối chủ bảng đã kiểm cùng máy chủ/DB
    (kiem_ket_noi_chu), từ đúng DSN đã chuẩn hóa/kiểm của máy chủ (không nhận DSN/actor từ request). Không dùng chung kết nối/GUC/giao dịch với
    service đệm của app; người gọi đóng ở MỌI nhánh."""
    from ..k2.crm_khoi_dong import kiem_ket_noi_chu, kiem_role_ung_dung, nap_driver
    psycopg = nap_driver()
    from psycopg.rows import dict_row
    dsn, admin = app._crm_ket_noi()
    if not dsn:
        raise DataError("CRM_CHUA_CAU_HINH", "CRM/M4 DEMO chưa được cấu hình kết nối PostgreSQL cục bộ.")
    if not admin:
        raise DataError("M4_CHUA_SAN_SANG_GHI_NGUON", "Review cần đường tin cậy của máy chủ (kết nối chủ bảng) — chưa cấu hình.")
    web = chu = None
    try:
        web = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
        kiem_role_ung_dung(web)
        chu = psycopg.connect(admin, autocommit=True, row_factory=dict_row)
        kiem_ket_noi_chu(chu, web)
        return web, chu
    except BaseException as exc:
        for c in (chu, web):
            if c is not None:
                c.close()
        if isinstance(exc, psycopg.Error):
            raise DataError("PG_KHONG_KET_NOI", "Không mở được kết nối riêng cho thao tác Review.") from None
        raise


def _review_lenh(app, svc, me: str, ten: str, payload: dict):
    """FIX01 R3 — chạy lệnh Review NGOÀI mutation lock toàn cục: danh tính phiên (`me`) đã chụp dưới lock ngắn; dịch vụ riêng trên cặp kết nối riêng
    (cùng thư mục kho/đồng hồ của service hiện hành); tính toán CPU trong tiến trình con không chặn GET/đổi vai/module khác. Đổi vai sau đó không đổi
    danh tính của thao tác đang chạy; quyền HIỆN HÀNH vẫn kiểm lại trong CSDL trước tra biên nhận và trước công bố (CAS toàn basis)."""
    from ..k2.xay_dung import XayDungK2
    # CRM-41-01-06: factory client theo app (engine DEMO sở hữu hoặc seam host cấp) — không nhận URL/token từ trình duyệt
    trich6 = app.trich6_client(svc.root) if ten == "hop-dong/trich" else None
    web, chu = _ket_noi_review(app)
    try:
        rieng = XayDungK2(web, svc.root, conn_tin_cay=chu, chi_mo_phong=svc.chi_mo_phong, hom_nay=svc.hom_nay, trich6=trich6)
        return app._crm_db(_lenh, app, rieng, me, ten, payload)
    finally:
        chu.close()
        web.close()


def _rieng(app, svc, fn):
    """M4-02C — cùng seam kết nối riêng của `_review_lenh` cho lệnh không qua bảng TRUONG (POST PDF hồ sơ đã duyệt: bytes thô + X-M4-Info)."""
    from ..k2.xay_dung import XayDungK2
    web, chu = _ket_noi_review(app)
    try:
        return app._crm_db(fn, XayDungK2(web, svc.root, conn_tin_cay=chu, chi_mo_phong=svc.chi_mo_phong, hom_nay=svc.hom_nay))
    finally:
        chu.close()
        web.close()


def _info(h, cho_phep: set) -> dict:
    """Header X-M4-Info (JSON đã URL-encode, ≤4000 ký tự): đúng tập trường cho phép, không authority từ trình duyệt."""
    encoded = h.headers.get("X-M4-Info", "")
    if len(encoded) > 4000:
        raise DataError("M4_YEU_CAU_SAI", "Thông tin tệp quá dài.")
    try:
        info = json.loads(unquote(encoded) or "{}")
    except ValueError:
        raise DataError("M4_YEU_CAU_SAI", "Thông tin tệp phải là JSON.") from None
    if not isinstance(info, dict):
        raise DataError("M4_YEU_CAU_SAI", "Thông tin tệp phải là object.")
    return _than(info, cho_phep)


def _q(query: dict, cho_phep: set) -> dict:
    """Tham số GET Review: chỉ khóa cho phép, mỗi khóa một giá trị (không nhận actor/đường dẫn/facts qua query)."""
    la = sorted(k for k in query if k not in cho_phep)
    if la:
        raise DataError("M4_YEU_CAU_SAI", "Truy vấn có tham số ngoài phạm vi: " + ", ".join(la[:5]))
    out = {}
    for k, v in query.items():
        if len(v) != 1:
            raise DataError("M4_YEU_CAU_SAI", f"Tham số {k} lặp.")
        out[k] = v[0] or None
    return out


def _dc_doc(svc, me, pending):
    """03B: chỉ ghép các dịch vụ có sẵn; nguồn NT lấy từ chi tiết 03A của phiên."""
    from ..m4.ghi_nhan_nghiem_thu import dich_vu as dc, ref_tu_kt
    from ..k2.ghi_nhan_chung import SCHEMA
    ct = svc.kt_xem(me, kt_pending_id=pending, phong_bi_id=None)
    if ct.get("quyen", {}).get("xem") is not True:
        raise DataError("DC_PHAM_VI", "Không có quyền xem căn cứ của đợt này.")
    gn = dc(svc)
    ref = ref_tu_kt(ct)
    return {"schema": SCHEMA, "nguon_nt": ref,
            "can_cu": gn.xem_doi_chieu(me, {"nguon": [ref]}),
            "goi_y": gn.goi_y_hoa_don(me, ct["context"]["dot_id"])}


def dieu_huong(h, app, post: bool, path: str, query: dict):
    """Một điểm vào cho mọi route /api/m4* và tài sản /m4*. Tự trả lỗi có mã (403 phạm vi / 404 / 409 xung đột / 413 / 503 chưa cấu hình)."""
    try:
        if path.startswith("/api/m4/doi-chieu/") and hasattr(h, "path"):
            # Dispatcher chung bỏ tham số rỗng; 03B phải chặn cả ?actor= / ?la=.
            query = parse_qs(urlsplit(h.path).query, keep_blank_values=True)
        if not post:
            m = re.fullmatch(r"/api/m4/doi-chieu/(dot|lich-su|con-thieu)/(" + _UUID + r")", path)
            if m:
                _q(query, set())
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    if m.group(1) == "lich-su":
                        from ..m4.ghi_nhan_nghiem_thu import dich_vu as dc
                        result = app._crm_db(lambda: dc(svc).lich_su(me, m.group(2)))
                    else:  # con-thieu dùng cùng căn cứ/quyền; UI đọc kt.thieu và hóa đơn chưa gắn
                        result = app._crm_db(_dc_doc, svc, me, m.group(2))
                return h.send_content(200, result, headers={"Cache-Control": "no-store"})
            if path in ("/m4.js", "/m4.css"):
                mime = "text/javascript; charset=utf-8" if path.endswith(".js") else "text/css; charset=utf-8"
                return h.send_content(200, (ASSETS / path[1:]).read_bytes(), mime)
            if path == "/m4/review.js":  # M4-02A: đúng MỘT tài sản Review (bố cục checks.js nguồn đã thích nghi) — không static server tổng quát
                return h.send_content(200, (ASSETS / "review.js").read_bytes(), "text/javascript; charset=utf-8", {"Cache-Control": "no-store"})
            if path == "/m4/chung-tu.js":  # M4-02B: đúng MỘT tài sản Chứng từ L3 (bố cục chung_tu.js nguồn đã thích nghi)
                return h.send_content(200, (ASSETS / "chung_tu.js").read_bytes(), "text/javascript; charset=utf-8", {"Cache-Control": "no-store"})
            if path == "/m4/m4_duyet_pdf.js":  # M4-02C: đúng MỘT tài sản do UI head giao; vắng → 404 (không stub, không static tổng quát)
                p = ASSETS / "m4_duyet_pdf.js"
                if not p.is_file():
                    raise DataError("NOT_FOUND", "Tài sản Duyệt & PDF chưa được giao.")
                return h.send_content(200, p.read_bytes(), "text/javascript; charset=utf-8", {"Cache-Control": "no-store"})
            if path == "/m4/m4_ke_toan.js":  # M4-03A: đúng MỘT tài sản Kế toán nghiệm thu; vắng → 404 (không stub, không static tổng quát)
                p = ASSETS / "m4_ke_toan.js"
                if not p.is_file():
                    raise DataError("NOT_FOUND", "Tài sản Kế toán nghiệm thu chưa được giao.")
                return h.send_content(200, p.read_bytes(), "text/javascript; charset=utf-8", {"Cache-Control": "no-store"})
            if path == "/m4/m4_request_nhap.js":  # M4-04B: đúng MỘT tài sản widget Request nháp; vắng → 404 (không stub, không static tổng quát)
                p = ASSETS / "m4_request_nhap.js"
                if not p.is_file():
                    raise DataError("NOT_FOUND", "Tài sản Request nháp chưa được giao.")
                return h.send_content(200, p.read_bytes(), "text/javascript; charset=utf-8", {"Cache-Control": "no-store"})
            if path == "/api/m4/ke-toan":  # M4-03A: inbox KT của chính phiên hiện hành (không suy từ danh sách HĐ/portal)
                _q(query, set())
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    return h.send_content(200, app._crm_db(svc.kt_danh_sach, me), headers={"Cache-Control": "no-store"})
            m = re.fullmatch(r"/api/m4/ke-toan/(" + _UUID + r")(?:/phong-bi/(" + _UUID + r")/pdf)?", path)
            if m:
                q = _q(query, KT_GET if m.group(2) is None else set())  # tải PDF: không tham số nào; xem: chỉ phong_bi_id (một giá trị)
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    if m.group(2) is None:
                        return h.send_content(200, app._crm_db(lambda: svc.kt_xem(me, kt_pending_id=m.group(1), phong_bi_id=q.get("phong_bi_id"))),
                                              headers={"Cache-Control": "no-store"})
                    ten, media, raw = app._crm_db(svc.kt_tep_pdf, me, m.group(1), m.group(2))  # quyền KT hiện hành + hash/độ dài kiểm ở backend
                return h.send_content(200, raw, media, {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(ten, safe=""), "Cache-Control": "no-store"})
            if path == "/api/m4/duyet":
                q = _q(query, DUYET_GET)
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    return h.send_content(200, app._crm_db(lambda: svc.duyet_xem(me, dot_id=q.get("dot_id"), version_id=q.get("version_id"))),
                                          headers={"Cache-Control": "no-store"})
            m = re.fullmatch(r"/api/m4/duyet/(" + _UUID + r")/pdf/(" + _UUID + ")", path)
            if m:
                _q(query, set())
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    ten, media, raw = app._crm_db(svc.duyet_pdf_tai, me, m.group(1), m.group(2))  # quyền hiện hành TRƯỚC và SAU khi đọc kho
                return h.send_content(200, raw, media, {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(ten, safe=""), "Cache-Control": "no-store"})
            if path in ("/api/m4/master-hop-dong", "/api/m4/master-doi-tac"):  # MASTER-REUSE-02: bộ chọn có giới hạn, SOAN hiện hành trong CSDL
                q = _q(query, MASTER_GET)
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    fn = svc.master_hop_dong if path.endswith("hop-dong") else svc.master_doi_tac
                    return h.send_content(200, app._crm_db(lambda: fn(me, du_an_id=q.get("du_an_id"), q=q.get("q") or "", limit=q.get("limit"))),
                                          headers={"Cache-Control": "no-store"})
            if path == "/api/m4/chung-tu":
                q = _q(query, CHUNG_TU_GET)
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    return h.send_content(200, app._crm_db(lambda: svc.chung_tu_ds(me, dot_id=q.get("dot_id"))))
            m = re.fullmatch(r"/api/m4/chung-tu/(" + _UUID + r")(?:/tep/(" + _UUID + "))?", path)
            if m:
                _q(query, set())  # FIX01: chi tiết/tải L3 không nhận tham số truy vấn nào (lạ/lặp → 400), không cấp authority qua query
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    if m.group(2) is None:
                        return h.send_content(200, app._crm_db(svc.chung_tu_chi_tiet, me, m.group(1)))
                    ten, media, raw = app._crm_db(svc.chung_tu_tai, me, m.group(1), m.group(2))  # quyền hiện hành TRƯỚC registry/kho
                return h.send_content(200, raw, media, {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(ten, safe=""), "Cache-Control": "no-store"})
            if path == "/api/m4/review":
                q = _q(query, REVIEW_GET)
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    return h.send_content(200, app._crm_db(lambda: svc.review_ds(me, hop_dong_id=q.get("hop_dong_id"), dot_id=q.get("dot_id"),
                                                                                 tep_id=q.get("tep_id"), che_do=q.get("che_do"), o_dich=q.get("o_dich"))))
            m = re.fullmatch(r"/api/m4/review/(" + _UUID + r")(?:/tep/(" + _UUID + "))?", path)
            if m:
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    if m.group(2) is None:
                        return h.send_content(200, app._crm_db(svc.review_chi_tiet, me, m.group(1)))
                    ten, media, raw = app._crm_db(svc.review_tai, me, m.group(1), m.group(2))  # quyền hiện hành TRƯỚC registry/kho
                return h.send_content(200, raw, media, {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(ten, safe=""), "Cache-Control": "no-store"})
            if path.startswith("/m4/fonts/"):
                from ..m4.nguon_review import tai_san_font
                ten = path[len("/m4/fonts/"):]
                mime = "font/woff2" if ten.endswith(".woff2") else "text/css; charset=utf-8" if ten.endswith(".css") else "text/plain; charset=utf-8"
                return h.send_content(200, tai_san_font(ten), mime, {"Cache-Control": "no-store"})
            if path == "/api/m4":
                with app.mutation_lock:
                    sid, me, moi = app.crm_phien(h.crm_sid(), tao=True)
                    headers = {"Set-Cookie": f"{app.CRM_COOKIE}={sid}; Path=/; HttpOnly; SameSite=Strict"} if moi else None
                    return h.send_content(200, trang_thai(app, me), headers=headers)
            if path == "/api/m4/mau" or path.startswith("/api/m4/mau/"):
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    app._crm_db(_kiem_mau, svc, me)  # phiên hiện hành phải có quyền soạn M4 hiện hành ở ít nhất một dự án
                if path == "/api/m4/mau":
                    return h.send_content(200, {"mau": [{"ma": ma, "vai_tro": v[0], "media_type": v[1], "mo_ta": v[3]} for ma, v in MAU.items()]})
                ma = path[len("/api/m4/mau/"):]
                if ma not in MAU:
                    raise DataError("NOT_FOUND", "Không có tệp mẫu DEMO này.")
                vai, media, tao, _ = MAU[ma]
                return h.send_content(200, tao(), media, {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(ma, safe=""),
                                                          "Cache-Control": "no-store"})
            m = re.fullmatch(r"/api/m4/(hop-dong|dot|tep)/(" + _UUID + ")", path)
            if m:
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    if m.group(1) == "hop-dong":
                        return h.send_content(200, app._crm_db(svc.chi_tiet, me, m.group(2)))
                    if m.group(1) == "dot":
                        return h.send_content(200, app._crm_db(svc.chi_tiet_dot, me, m.group(2)))
                    ten, _media, raw = app._crm_db(svc.tai_ve, me, m.group(2))
                return h.send_content(200, raw, "application/octet-stream", {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(ten, safe="")})
        else:
            if path in ("/api/m4/doi-chieu/xem", "/api/m4/doi-chieu/luu", "/api/m4/doi-chieu/xac-nhan"):
                from ..k2 import ghi_nhan_chung as GN
                from ..m4.ghi_nhan_nghiem_thu import dich_vu as dc
                _q(query, set())
                ten = path.rsplit("/", 1)[1]
                payload = h.json_body()
                # Dùng validator hiện có, kể cả khóa lồng; tham số lạ 400, authority 403.
                {"xem": GN.yeu_cau_xem, "luu": GN.yeu_cau_luu, "xac-nhan": GN.yeu_cau_xac_nhan}[ten](payload)
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                def goi(s):
                    gn = dc(s)
                    return {"xem": gn.xem_doi_chieu, "luu": gn.luu_doi_chieu, "xac-nhan": gn.xac_nhan_doi_chieu}[ten](me, payload)
                return h.send_content(200, _rieng(app, svc, goi), headers={"Cache-Control": "no-store"})
            if path == "/api/m4/tep":
                encoded = h.headers.get("X-M4-Info", "")
                if len(encoded) > 4000:
                    raise DataError("M4_YEU_CAU_SAI", "Thông tin tệp quá dài.")
                try:
                    info = json.loads(unquote(encoded) or "{}")
                except ValueError:
                    raise DataError("M4_YEU_CAU_SAI", "Thông tin tệp phải là JSON.") from None
                if not isinstance(info, dict):
                    raise DataError("M4_YEU_CAU_SAI", "Thông tin tệp phải là object.")
                _than(info, TRUONG_TEP)
                raw = h.body()
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    return h.send_content(200, app._crm_db(lambda: svc.tai_tep(me, raw, du_an_id=info.get("du_an_id"), vai_tro=info.get("vai_tro"),
                                                                               ten=info.get("ten"), media_type=info.get("media_type"), khoa=info.get("khoa"))))
            if path == "/api/m4/duyet/pdf":  # M4-02C: PDF hồ sơ thanh toán ĐÃ DUYỆT — bytes thô, không qua /api/m4/tep (không vòng vai tài liệu)
                info = _info(h, TRUONG_DUYET_PDF)
                raw = h.body()
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                return h.send_content(200, _rieng(app, svc, lambda s: s.duyet_pdf(
                    me, raw, dot_id=info.get("dot_id"), version_id=info.get("version_id"), revision=info.get("revision"),
                    expected_basis=info.get("expected_basis"), ten=info.get("ten"), media_type=info.get("media_type"), khoa=info.get("khoa"))),
                    headers={"Cache-Control": "no-store"})
            if path in ("/api/m4/ke-toan/luu", "/api/m4/ke-toan/xac-nhan"):  # M4-03A: allowlist chặt; kết nối riêng như M4-02C, ngoài mutation lock
                ten = path[len("/api/m4/"):]
                payload = _than(h.json_body(), TRUONG_KT[ten])
                with app.mutation_lock:
                    _, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                if ten == "ke-toan/luu":
                    return h.send_content(200, _rieng(app, svc, lambda s: s.kt_luu(me, **payload)), headers={"Cache-Control": "no-store"})
                return h.send_content(200, _rieng(app, svc, lambda s: s.kt_xac_nhan(me, **payload)), headers={"Cache-Control": "no-store"})
            if path.startswith("/api/m4/"):
                ten = path[len("/api/m4/"):]
                if ten not in TRUONG:
                    raise DataError("NOT_FOUND", "Không có thao tác M4 này.")
                payload = _than(h.json_body(), TRUONG[ten])
                if ten in LENH_RIENG:  # FIX01 R3 + CRM-41-01: lock toàn cục chỉ bao bước chụp danh tính phiên + service; lệnh chạy trên kết nối riêng
                    with app.mutation_lock:
                        _, me, _ = app.crm_phien(h.crm_sid())
                        svc = dich_vu(app)
                    return h.send_content(200, _review_lenh(app, svc, me, ten, payload))
                with app.mutation_lock:
                    sid, me, _ = app.crm_phien(h.crm_sid())
                    svc = dich_vu(app)
                    if ten == "danh-tinh":
                        from ..k2.m4_demo import dang_nhap_m4
                        if payload.get("dang_nhap") not in dang_nhap_m4():
                            raise DataError("DANH_TINH_M4", "Vai mô phỏng không thuộc danh sách vai M4 DEMO.")
                        app._crm_db(svc.danh_tinh, payload["dang_nhap"])  # chỉ danh tính mô phỏng hoạt động; chỉ đổi phiên của trình duyệt này
                        app._crm_phien[sid] = payload["dang_nhap"]
                        return h.send_content(200, {"dang_nhap": payload["dang_nhap"]})
                    return h.send_content(200, app._crm_db(_lenh, app, svc, me, ten, payload))
        return h.send_content(404, {"error": "NOT_FOUND", "message": "Không tìm thấy chức năng này."})
    except DataError as exc:
        if path.startswith("/api/m4/doi-chieu/"):
            from ..k2.ghi_nhan_chung import MA_HTTP
            status = {"DC_YEU_CAU_SAI": 400, "DC_CLIENT_AUTHORITY": 403, "M4_YEU_CAU_SAI": 400}.get(
                exc.code, MA_HTTP.get(exc.code, 403 if exc.code in MA_403 else 404 if exc.code in MA_404 else 503 if exc.code in MA_503 else 400))
            labels = {"so_tien_khai": "số tiền một phần", "tien_te": "đơn vị tiền", "thanh_phan": "nguồn đã chọn", "nguon": "căn cứ",
                      "expected_graph": "căn cứ đang xem", "expected_revision": "phiên bản đang xem", "doi_chieu_id": "đối chiếu",
                      "phien_ban_id": "phiên bản", "can_cu_tep": "tệp căn cứ", "ly_do": "lý do", "khoa": "khóa thao tác"}
            message = str(exc)
            for field, label in labels.items():
                message = re.sub(r"\b" + field + r"\b", label, message)
            return h.send_content(status, {"error": exc.code, "message": message, "field": exc.locator},
                                  headers={"Cache-Control": "no-store"})
        if path.startswith("/api/m4/ke-toan") and exc.code in MA_KT:  # FIX01: chỉ route KT, đúng mã
            st = MA_KT[exc.code]
            return h.send_content(st, {"error": exc.code, "message": KT_SAI_DTO_MSG if st == 500 else str(exc)})
        status = (403 if exc.code in MA_403 else 404 if exc.code in MA_404
                  else 409 if (exc.code in MA_409 or exc.code in MA_409_REVIEW or exc.code in MA_409_DUYET) else 413 if exc.code in MA_413
                  else 503 if exc.code in MA_503 else 422 if (path.startswith("/api/m4/ke-toan") and exc.code in MA_422_KT)
                  else 422 if exc.code in MA_422_MASTER else 400)
        return h.send_content(status, {"error": exc.code, "message": str(exc)})
    except (ValueError, TypeError, KeyError, RecursionError):  # M4-03A: hợp đồng KT invalid → 422; route khác giữ 400
        return h.send_content(422 if path.startswith("/api/m4/ke-toan") else 400, {"error": "INVALID_REQUEST", "message": "Thông tin gửi lên không hợp lệ; chưa xử lý."})
    except OSError:
        return h.send_content(500, {"error": "LOCAL_STORAGE_ERROR", "message": "Không đọc/ghi được kho trên máy. Tệp đã lưu vẫn được giữ."})
