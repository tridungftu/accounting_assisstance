"""M4-03A — inbox kế toán + xác nhận nguồn nghiệm thu trên gốc/phong bì M24 đã seal (schema DTO `M4_03A_KT_V1`).

Service `KeToanNghiemThuK2(xd)` nhận XayDungK2 hiện hữu qua tham số (KHÔNG import xay_dung, không engine nguồn). Root integration owner nối
registry (`sql_ke_toan_nghiem_thu.M4_03A_SQL`), route và UI sau — module này không tự đăng ký gì.

Nguyên tắc:
- Quyền KE_TOAN hiện hành kiểm qua login ứng dụng thường (hàm SECURITY DEFINER m4.kt_*) TRƯỚC mọi đọc chủ bảng/nguồn/lịch sử/blob. PDF đọc trên login
  thường. Chi tiết/danh sách: sau đó trên giao dịch chủ bảng (`xd._tx_review`) kiểm lại quyền + HĐ FOR SHARE (m4._kt_khoa_doc) → dựng đồ thị căn cứ
  bằng ĐÚNG producer M24 (duyet_dot.DuyetDot._dot/_phien_ban + do_thi) → ghim chứng thực SET LOCAL (m4._kt_chung_thuc_ghi) → hàm đọc SQL quyết hiện
  hành toàn căn cứ. Lệnh ghi: một giao dịch chủ bảng m4.kt_khoa (quyền → khóa HĐ→đợt→phiên bản→gốc→revision KT) → ghim đồ thị producer → m4.kt_luu /
  m4.kt_xac_nhan_lenh (biên nhận m4.bien_nhan dùng chung → phát lại/CAS nguồn + revision → ghi thêm; trigger kiểm lại). Không dùng chứng thực của
  giao dịch khác. Không actor/PN/dự án/trạng thái/pass/AP từ body.
- Số nguồn (phong bì M24) và số KT xác nhận tách riêng; NULL ≠ 0; chuỗi thập phân chuẩn, không float/FX/VAT suy diễn/tài khoản/sổ cái.
- Trạng thái trung thực: CHO_XAC_NHAN / CHO_BO_SUNG / KT_DA_XAC_NHAN_CHO_GHI_CONG_NO; AP luôn CHUA_TRIEN_KHAI_M4_03B (chưa ghi công nợ), Request
  luôn CHUA_NOI_M4_04.
"""

from __future__ import annotations

import json
import re
import uuid

from ..ha_tang.primitives import DataError
from . import duyet_dot as DD
from . import nguon_review as NR
from .sql_ke_toan_nghiem_thu import CO_SO, LOAI, LY_DO_HOLD, TIEN_KT, TIEN_NGUON, TT_DA_XAC_NHAN, VAT
from .sql_duyet import TIEN

SCHEMA = "M4_03A_KT_V1"
TT_CHO_XAC_NHAN = "CHO_XAC_NHAN"
TT_CHO_BO_SUNG = "CHO_BO_SUNG"
# chỉ dòng danh sách: phong bì mới nhất không hiện hành (phiên bản kế tiếp chưa seal / L3 công bố lại sau seal — LY_DO_HOLD; căn cứ đầy đủ đổi sau
# seal — LY_DO_CO_SO) hoặc nguồn hỏng. Hiện hành do SQL quyết định (m4._kt_hien_hanh, gọi lại dưới khóa trong lệnh/phát lại + trigger); service chỉ
# dựng đồ thị bằng producer M24 và ghim chứng thực, KHÔNG tự so/suy và không chặn sớm bằng Python.
TT_CAN_KIEM_LAI = "CAN_KIEM_LAI"
LY_DO_KHONG_HIEN_HANH = LY_DO_HOLD
TRANG_THAI_KT = (TT_CHO_XAC_NHAN, TT_CHO_BO_SUNG, TT_DA_XAC_NHAN)
AP = {"trang_thai": "CHUA_TRIEN_KHAI_M4_03B", "da_ghi_cong_no": False}
REQUEST = {"trang_thai": "CHUA_NOI_M4_04"}

CONTEXT_UUID = ("phap_nhan_id", "du_an_id", "hop_dong_id", "dot_id", "kt_pending_id", "phong_bi_id", "seal_id", "version_id", "ket_luan_id", "pdf_id")
CONTEXT_SHA = ("phong_bi_sha256", "graph_sha256", "pdf_sha256")
CONTEXT_KEYS = CONTEXT_UUID + CONTEXT_SHA
DU_LIEU = ("gia_tri_nt_xac_nhan", "tien_te", "co_so_gia_tri", "tam_ung_xac_nhan", "thu_hoi_xac_nhan", "giu_lai_xac_nhan", "vat_trang_thai",
           "vat_can_cu_tep_id", "vat_trich_dan", "ly_do")
KT_KEYS = ("kt_revision_id", "revision", "trang_thai") + DU_LIEU
NGUON_KEYS = (*TIEN, "tien_te", "dong", "pdf", "tep_can_cu")
PDF_KEYS = ("id", "ten", "media_type", "raw_sha256", "byte_length")
TEP_KEYS = ("id", "ten", "raw_sha256", "media_type", "byte_length")
QUYEN_KEYS = ("xem", "luu", "xac_nhan", "tai_pdf")
XEM_KEYS = ("schema", "context", "quyen", "can_cu_hien_hanh", "nguon", "kt", "lich_su", "ap", "request")
LICH_SU_PB_KEYS = ("context", "thu_tu", "truoc_id", "phien_ban_so", "can_cu_hien_hanh")
DONG_DS_KEYS = ("kt_pending_id", "dot_id", "phong_bi_id", "phong_bi_sha256", "revision", "trang_thai", "ap")
ACK_KEYS = ("schema", "context", "kt_revision_id", "revision", "trang_thai", "lap_lai", "receipt_id", "ap", "request")

TRUONG_LUU = ("kt_pending_id", "phong_bi_id", "expected_phong_bi_sha256", "expected_revision") + DU_LIEU + ("khoa",)
TRUONG_XAC_NHAN = ("kt_pending_id", "phong_bi_id", "kt_revision_id", "expected_revision", "expected_phong_bi_sha256", "khoa")
# khóa mang thẩm quyền/định danh/trạng thái/số nguồn do MÁY CHỦ quyết — trình duyệt gửi là sai vai trò (không bỏ qua im lặng)
KHONG_NHAN = frozenset({
    "actor", "nguoi_dung_id", "dang_nhap", "tao_boi", "tao_boi_id", "owner", "chu", "chu_bang", "vai", "vai_tro", "quyen", "role",
    "phap_nhan_id", "du_an_id", "hop_dong_id", "dot_id", "seal_id", "version_id", "phien_ban_id", "ket_luan_id", "pdf_id", "quyet_dinh_id",
    "context", "phong_bi_sha256", "graph_sha256", "pdf_sha256", "vat_can_cu_sha256", "raw_sha256", "object_key",
    "trang_thai", "loai", "nhap_id", "pass", "dat", "da_duyet", "approved", "da_xac_nhan", "receipt_id", "lap_lai",
    "ap", "request", "da_ghi_cong_no", "cong_no", "so_cai", "but_toan", "ledger", "journal", "tai_khoan", "account", "thue_suat", "tien_thue",
    "vat_tinh", "ty_gia", "fx",
    *TIEN, "dong", "nguon"})
KHONG_NHAN_XAC_NHAN = KHONG_NHAN | frozenset(DU_LIEU)  # xác nhận KHÔNG gửi lại số/VAT/lý do — máy chủ sao y bản nháp đã lưu

KHOA_RE = re.compile(r"[A-Za-z0-9_.:-]{1,200}")
HEX_RE = re.compile(r"[0-9a-f]{64}")
VAN_BAN_TOI_DA = 2000
REVISION_TOI_DA = 10 ** 6

# gợi ý HTTP cho integration owner (bổ sung vào bảng mã của giao_dien/m4.py khi nối route; module này không sửa bảng đó)
MA_HTTP = {
    "M4_YEU_CAU_SAI": 422, "M4_CLIENT_AUTHORITY": 422, "M4_THAM_SO_SAI": 422, "M4_KHOA_THAO_TAC": 422, "M4_KT_SO_SAI": 422,
    "M4_KT_TRUONG_SAI": 422, "M4_KT_VAT_SAI": 422, "M4_KT_CO_SO_SAI": 422, "M4_KT_TIEN_TE_KHAC": 422, "M4_KT_CAN_CU_VAT_SAI": 422,
    "M4_KT_PHAM_VI": 403, "M4_KT_KHONG_THAY": 404,
    "M4_KT_NGUON_CU": 409, "M4_KT_NGUON_DOI": 409, "M4_KT_CAN_KIEM_LAI": 409, "M4_KT_REVISION_CU": 409, "M4_KT_DA_XAC_NHAN": 409,
    "M4_KT_CHO_BO_SUNG": 409, "M4_KT_XAC_NHAN_KHAC_NHAP": 409, "M4_KT_NGUON_HONG": 409, "M4_IDEMPOTENCY_KHAC": 409,
    "M4_CHUA_SAN_SANG_GHI_NGUON": 503, "M4_KET_QUA_CHUA_RO": 503,
    "M4_KT_SAI_DTO": 500, "M4_CHI_MAY_CHU_NGUON": 500,
}


# ================================================================================================== kiểm đầu vào (chặt, không đoán)
def _yc_sai(msg: str):
    raise DataError("M4_YEU_CAU_SAI", msg)


def _dto_sai(msg: str):
    raise DataError("M4_KT_SAI_DTO", f"Dữ liệu máy chủ không đúng hợp đồng M4_03A_KT_V1: {msg}")


def _la_uuid(v) -> bool:
    if not isinstance(v, str):
        return False
    try:
        return str(uuid.UUID(v)) == v
    except ValueError:
        return False


def _la_sha(v) -> bool:
    return isinstance(v, str) and HEX_RE.fullmatch(v) is not None


def _la_int(v, *, toi_thieu: int) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= toi_thieu


def _khoa_body(body, cho_phep: tuple, cam: frozenset) -> dict:
    """Body phải là object có ĐÚNG các khóa cho phép (mọi khóa bắt buộc hiện diện; null ≠ thiếu). Khóa thẩm quyền → M4_CLIENT_AUTHORITY."""
    if not isinstance(body, dict):
        _yc_sai("Yêu cầu phải là object JSON.")
    kh = set(body)
    xau = sorted(k for k in kh if k in cam and k not in cho_phep)
    if xau:
        raise DataError("M4_CLIENT_AUTHORITY", "Trình duyệt không được gửi trường do máy chủ quyết định: " + ", ".join(xau[:10]))
    la = sorted(k for k in kh if k not in cho_phep)
    if la:
        _yc_sai("Trường không thuộc hợp đồng: " + ", ".join(str(k)[:60] for k in la[:10]))
    thieu = [k for k in cho_phep if k not in kh]
    if thieu:
        _yc_sai("Thiếu trường bắt buộc (gửi null nếu chưa có): " + ", ".join(thieu))
    return body


def _khoa(v) -> str:
    if not isinstance(v, str) or not KHOA_RE.fullmatch(v):
        raise DataError("M4_KHOA_THAO_TAC", "Thiếu hoặc sai khóa thao tác (chống bấm lặp).")
    return v


def _sha(v, ten: str) -> str:
    if not _la_sha(v):
        raise DataError("M4_KT_CO_SO_SAI", f"{ten} phải là SHA-256 của phong bì nguồn đang xem (64 ký tự hex thường).")
    return v


def _rev(v, *, toi_thieu: int) -> int:
    if not _la_int(v, toi_thieu=toi_thieu) or v > REVISION_TOI_DA:
        raise DataError("M4_THAM_SO_SAI", f"expected_revision phải là số nguyên {toi_thieu}..{REVISION_TOI_DA} (không nhận bool/chuỗi/số thực).")
    return v


def _tien(v, ten: str, *, vnd: bool):
    try:
        return DD.tien(v, ten, vnd=vnd)
    except DataError as e:
        raise DataError("M4_KT_SO_SAI", str(e)) from None


def _tien_te(v):
    try:
        return DD.kiem_tien_te(v)
    except DataError:
        raise DataError("M4_KT_SO_SAI", "tien_te phải là mã ISO 4217 ba chữ in hoa (vd VND) hoặc null.") from None


def _enum(v, ten: str, gia_tri: tuple) -> str:
    if not isinstance(v, str) or v not in gia_tri:
        raise DataError("M4_KT_TRUONG_SAI", f"{ten} phải thuộc {', '.join(gia_tri)}.")
    return v


def _van_ban(v, ten: str):
    """Văn bản tự do (lý do/trích dẫn): null hoặc chuỗi 1..2000 ký tự, không ký tự điều khiển ngoài xuống dòng/tab. Chuỗi trắng = null (thiếu)."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if not isinstance(v, str) or len(v) > VAN_BAN_TOI_DA or any(ord(c) < 32 and c not in "\n\t" for c in v):
        raise DataError("M4_KT_TRUONG_SAI", f"{ten} phải là chuỗi ≤{VAN_BAN_TOI_DA} ký tự (không ký tự điều khiển) hoặc null.")
    return v


def kiem_luu(body) -> tuple[str, dict]:
    """Lệnh LƯU NHÁP: allowlist đủ 15 khóa. Trả (khoa, yc) — yc là yêu cầu chuẩn hóa (không gồm khoa) dùng cho biên nhận + lệnh SQL."""
    b = _khoa_body(body, TRUONG_LUU, KHONG_NHAN)
    khoa = _khoa(b["khoa"])
    tt = _tien_te(b["tien_te"])
    vnd = tt == "VND"
    vat = _enum(b["vat_trang_thai"], "vat_trang_thai", VAT)
    tep = b["vat_can_cu_tep_id"]
    if tep is not None:
        tep = DD._uuid(tep, "vat_can_cu_tep_id")
    trich = _van_ban(b["vat_trich_dan"], "vat_trich_dan")
    if vat != "CO_CAN_CU" and (tep is not None or trich is not None):
        raise DataError("M4_KT_VAT_SAI", "Chỉ trạng thái VAT CO_CAN_CU mới gắn tệp căn cứ/trích dẫn — bỏ tệp/trích dẫn hoặc chọn CO_CAN_CU.")
    yc = {"kt_pending_id": DD._uuid(b["kt_pending_id"], "kt_pending_id"), "phong_bi_id": DD._uuid(b["phong_bi_id"], "phong_bi_id"),
          "expected_phong_bi_sha256": _sha(b["expected_phong_bi_sha256"], "expected_phong_bi_sha256"),
          "expected_revision": _rev(b["expected_revision"], toi_thieu=0),
          "tien_te": tt, **{k: _tien(b[k], k, vnd=vnd) for k in TIEN_KT},
          "co_so_gia_tri": _enum(b["co_so_gia_tri"], "co_so_gia_tri", CO_SO), "vat_trang_thai": vat, "vat_can_cu_tep_id": tep,
          "vat_trich_dan": trich, "ly_do": _van_ban(b["ly_do"], "ly_do")}
    return khoa, yc


def kiem_xac_nhan_body(body) -> tuple[str, dict]:
    """Lệnh XÁC NHẬN: đúng 6 khóa; chọn ĐÚNG revision nháp đã lưu (kt_revision_id + expected_revision ≥1) + SHA phong bì. Không nhận lại số/VAT."""
    b = _khoa_body(body, TRUONG_XAC_NHAN, KHONG_NHAN_XAC_NHAN)
    khoa = _khoa(b["khoa"])
    yc = {"kt_pending_id": DD._uuid(b["kt_pending_id"], "kt_pending_id"), "phong_bi_id": DD._uuid(b["phong_bi_id"], "phong_bi_id"),
          "kt_revision_id": DD._uuid(b["kt_revision_id"], "kt_revision_id"), "expected_revision": _rev(b["expected_revision"], toi_thieu=1),
          "expected_phong_bi_sha256": _sha(b["expected_phong_bi_sha256"], "expected_phong_bi_sha256")}
    return khoa, yc


# ================================================================================================== miền: thiếu / trạng thái (gương của m4._kt_thieu)
def thieu(kt: dict, nguon: dict) -> list:
    """Điều kiện xác nhận còn thiếu (sắp ASCII = collation "C" của SQL). Không bao giờ coi null là 0; số KT khác số nguồn đã seal cần lý do."""
    x = []
    if kt.get("gia_tri_nt_xac_nhan") is None:
        x.append("GIA_TRI_NT_THIEU")
    if kt.get("tien_te") is None:
        x.append("TIEN_TE_THIEU")
    if kt.get("co_so_gia_tri") not in ("TRUOC_VAT", "GOM_VAT"):
        x.append("CO_SO_CHUA_XAC_DINH")
    vat = kt.get("vat_trang_thai")
    if vat == "CO_CAN_CU":
        if kt.get("vat_can_cu_tep_id") is None or kt.get("vat_trich_dan") is None:
            x.append("VAT_CAN_CU_THIEU")
    elif vat == "KHONG_AP_DUNG":
        if kt.get("ly_do") is None:
            x.append("VAT_LY_DO_THIEU")
    else:
        x.append("VAT_CHUA_DU")
    if kt.get("ly_do") is None and any(kt.get(k) is not None and kt.get(k) != nguon.get(n) for k, n in TIEN_NGUON.items()):
        x.append("LY_DO_KHAC_NGUON")
    return sorted(x)


def trang_thai_kt(loai: str, ds_thieu: list) -> str:
    if loai == "XAC_NHAN":
        return TT_DA_XAC_NHAN
    if loai != "NHAP":
        _dto_sai("loai revision KT lạ")
    return TT_CHO_XAC_NHAN if not ds_thieu else TT_CHO_BO_SUNG


def trang_thai_dong(hien_hanh: bool, toan_ven: bool, kt: dict | None) -> str:
    """Trạng thái dòng inbox (chỉ hiển thị): phong bì mới nhất không hiện hành/không toàn vẹn → CAN_KIEM_LAI; chưa có KT → CHO_XAC_NHAN."""
    if not hien_hanh or not toan_ven:
        return TT_CAN_KIEM_LAI
    if kt is None:
        return TT_CHO_XAC_NHAN
    return trang_thai_kt(kt.get("loai"), kt.get("thieu") or [])


# ================================================================================================== DTO typed (kiểm chặt dữ liệu máy chủ trước khi trả)
def kiem_ngu_canh(ctx) -> dict:
    if not isinstance(ctx, dict) or set(ctx) != set(CONTEXT_KEYS):
        _dto_sai("context phải có đúng 13 khóa định danh")
    for k in CONTEXT_UUID:
        if not _la_uuid(ctx[k]):
            _dto_sai(f"context.{k} phải là UUID chuẩn")
    for k in CONTEXT_SHA:
        if not _la_sha(ctx[k]):
            _dto_sai(f"context.{k} phải là SHA-256")
    return {k: ctx[k] for k in CONTEXT_KEYS}


def _tien_dto(v, ten: str):
    if v is None:
        return None
    if not isinstance(v, str) or not DD.TIEN_RE.fullmatch(v):
        _dto_sai(f"{ten} phải là chuỗi thập phân chuẩn hoặc null")
    return v


def _chuoi_hoac_null(v, ten: str):
    if v is not None and not isinstance(v, str):
        _dto_sai(f"{ten} phải là chuỗi hoặc null")
    return v


def kt_dto(row: dict, nguon_nd: dict) -> dict:
    """Một revision KT đã lưu (máy chủ, m4._kt_dong) → đúng 13 khóa. Đối chiếu danh sách thiếu SQL với gương Python (lệch → SAI_DTO, không đoán)."""
    if not isinstance(row, dict):
        _dto_sai("revision KT phải là object")
    if not _la_uuid(row.get("kt_revision_id")) or not _la_int(row.get("revision"), toi_thieu=1) or row.get("loai") not in LOAI:
        _dto_sai("kt_revision_id/revision/loai")
    th = thieu(row, nguon_nd)
    if list(row.get("thieu") or []) != th:
        _dto_sai("danh sách thiếu của CSDL khác kiểm tra miền")
    out = {"kt_revision_id": row["kt_revision_id"], "revision": row["revision"], "trang_thai": trang_thai_kt(row["loai"], th),
           "gia_tri_nt_xac_nhan": _tien_dto(row.get("gia_tri_nt_xac_nhan"), "gia_tri_nt_xac_nhan"),
           "tien_te": _chuoi_hoac_null(row.get("tien_te"), "tien_te"),
           "co_so_gia_tri": row.get("co_so_gia_tri"),
           **{k: _tien_dto(row.get(k), k) for k in ("tam_ung_xac_nhan", "thu_hoi_xac_nhan", "giu_lai_xac_nhan")},
           "vat_trang_thai": row.get("vat_trang_thai"),
           "vat_can_cu_tep_id": row.get("vat_can_cu_tep_id"),
           "vat_trich_dan": _chuoi_hoac_null(row.get("vat_trich_dan"), "vat_trich_dan"),
           "ly_do": _chuoi_hoac_null(row.get("ly_do"), "ly_do")}
    if out["co_so_gia_tri"] not in CO_SO or out["vat_trang_thai"] not in VAT:
        _dto_sai("co_so_gia_tri/vat_trang_thai")
    if out["vat_can_cu_tep_id"] is not None and not _la_uuid(out["vat_can_cu_tep_id"]):
        _dto_sai("vat_can_cu_tep_id")
    return {k: out[k] for k in KT_KEYS}


def _tep_dto(t, ten: str) -> dict:
    if not isinstance(t, dict) or set(t) != set(TEP_KEYS):
        _dto_sai(f"{ten} phải có đúng khóa {TEP_KEYS}")
    if (not _la_uuid(t["id"]) or not isinstance(t["ten"], str) or not t["ten"] or not _la_sha(t["raw_sha256"])
            or not isinstance(t["media_type"], str) or not t["media_type"] or not _la_int(t["byte_length"], toi_thieu=1)):
        _dto_sai(f"{ten}: id/ten/raw_sha256/media_type/byte_length")
    return {k: t[k] for k in TEP_KEYS}


def nguon_dto(nd: dict, pdf: dict, tep_can_cu, ctx: dict) -> dict:
    """Nguồn đã seal (CHỈ ĐỌC, đúng giá trị phong bì M24 — không copy thành số KT) + PDF hồ sơ đã duyệt (metadata, không object_key/URL) + ứng
    viên căn cứ VAT (mảng bắt buộc, rỗng hợp lệ)."""
    if not isinstance(nd, dict):
        _dto_sai("nguồn phải là object")
    p = _tep_dto({k: (pdf or {}).get(k) for k in TEP_KEYS} if isinstance(pdf, dict) and set(pdf) == set(PDF_KEYS) else None, "nguon.pdf")
    npdf = nd.get("pdf") or {}
    if (p["id"] != ctx["pdf_id"] or p["raw_sha256"] != ctx["pdf_sha256"] or p["media_type"] != NR.MEDIA_PDF
            or npdf.get("id") != p["id"] or npdf.get("raw_sha256") != p["raw_sha256"] or npdf.get("byte_length") != p["byte_length"]):
        _dto_sai("PDF hồ sơ đã duyệt không khớp phong bì/ngữ cảnh")
    if not isinstance(nd.get("dong"), list):
        _dto_sai("nguon.dong phải là mảng")
    if not isinstance(tep_can_cu, list):
        _dto_sai("nguon.tep_can_cu phải là mảng")
    return {**{k: _tien_dto(nd.get(k), k) for k in TIEN}, "tien_te": _chuoi_hoac_null(nd.get("tien_te"), "tien_te"), "dong": nd["dong"],
            "pdf": {k: p[k] for k in PDF_KEYS}, "tep_can_cu": [_tep_dto(t, "nguon.tep_can_cu[]") for t in tep_can_cu]}


def xem_dto(ct: dict) -> dict:
    """Chi tiết từ m4.kt_chi_tiet → DTO đúng 9 khóa top-level (kt explicit null khi phong bì chưa có revision KT)."""
    ctx = kiem_ngu_canh(ct.get("context"))
    nd = ct.get("nguon") or {}
    hien = ct.get("can_cu_hien_hanh") is True
    da_xn = ct.get("da_xac_nhan") is True
    k = ct.get("kt")
    kt = None if k is None else kt_dto(k, nd)
    if kt is not None and k.get("phong_bi_id") != ctx["phong_bi_id"]:
        _dto_sai("revision KT không thuộc phong bì đang xem")
    if da_xn != (kt is not None and kt["trang_thai"] == TT_DA_XAC_NHAN):
        _dto_sai("cờ đã xác nhận lệch revision mới nhất")
    pbs = []
    for r in ct.get("lich_su_phong_bi") or []:
        c = kiem_ngu_canh(r.get("context"))
        if (c["kt_pending_id"] != ctx["kt_pending_id"] or not _la_int(r.get("thu_tu"), toi_thieu=1) or not _la_int(r.get("phien_ban_so"), toi_thieu=1)
                or not (r.get("truoc_id") is None or _la_uuid(r.get("truoc_id"))) or not isinstance(r.get("can_cu_hien_hanh"), bool)):
            _dto_sai("lich_su.phong_bi")
        pbs.append({"context": c, "thu_tu": r["thu_tu"], "truoc_id": r["truoc_id"], "phien_ban_so": r["phien_ban_so"],
                    "can_cu_hien_hanh": r["can_cu_hien_hanh"]})
    if [x["thu_tu"] for x in pbs] != sorted({x["thu_tu"] for x in pbs}) or not any(x["context"] == ctx for x in pbs):
        _dto_sai("lich_su.phong_bi phải tăng dần theo thu_tu và chứa phong bì đang xem")
    kts = []
    for r in ct.get("lich_su_kt") or []:
        c = kiem_ngu_canh(r.get("context"))
        if c["kt_pending_id"] != ctx["kt_pending_id"] or not any(x["context"] == c for x in pbs) or not isinstance(r.get("nguon"), dict):
            _dto_sai("lich_su.kt thuộc phong bì ngoài gốc / thiếu số nguồn của phong bì")
        if (r.get("kt") or {}).get("phong_bi_id") != c["phong_bi_id"]:
            _dto_sai("lich_su.kt: revision không thuộc phong bì của ngữ cảnh")
        kts.append({"context": c, "kt": kt_dto(r["kt"], r["nguon"])})  # thiếu/khác nguồn tính theo ĐÚNG phong bì của revision đó
    if [x["kt"]["revision"] for x in kts] != sorted({x["kt"]["revision"] for x in kts}):
        _dto_sai("lich_su.kt phải tăng dần theo revision")
    xac_nhan = hien and not da_xn and kt is not None and kt["trang_thai"] == TT_CHO_XAC_NHAN
    return {"schema": SCHEMA, "context": ctx,
            "quyen": {"xem": True, "luu": hien and not da_xn, "xac_nhan": xac_nhan, "tai_pdf": True},
            "can_cu_hien_hanh": hien, "nguon": nguon_dto(nd, ct.get("pdf"), ct.get("tep_can_cu"), ctx), "kt": kt,
            "lich_su": {"phong_bi": pbs, "kt": kts}, "ap": dict(AP), "request": dict(REQUEST)}


def dong_ds_dto(r: dict) -> dict:
    if not _la_uuid(r.get("kt_pending_id")) or not _la_uuid(r.get("dot_id")) or not _la_uuid(r.get("phong_bi_id")) or not _la_sha(r.get("phong_bi_sha256")):
        _dto_sai("dòng danh sách: định danh/SHA phong bì")
    k = r.get("kt")
    if k is not None and (not _la_int(k.get("revision"), toi_thieu=1) or k.get("loai") not in LOAI):
        _dto_sai("dòng danh sách: revision KT")
    return {"kt_pending_id": r["kt_pending_id"], "dot_id": r["dot_id"], "phong_bi_id": r["phong_bi_id"], "phong_bi_sha256": r["phong_bi_sha256"],
            "revision": None if k is None else k["revision"],
            "trang_thai": trang_thai_dong(r.get("hien_hanh") is True, r.get("toan_ven") is True, k), "ap": dict(AP)}


def ack_dto(r: dict, khoa: str) -> dict:
    """Kết quả lệnh (mới / phát lại cùng khóa / xác nhận trùng khóa mới) → ACK typed. ACK lệch hợp đồng KHÔNG được coi là thành công."""
    if not isinstance(r, dict) or not isinstance(r.get("ket_qua"), dict):
        _dto_sai("kết quả lệnh")
    kq = r["ket_qua"]
    if kq.get("ap") != AP or kq.get("request") != REQUEST:
        _dto_sai("AP/Request phải giữ CHUA_TRIEN_KHAI_M4_03B / CHUA_NOI_M4_04")
    if (not _la_uuid(kq.get("kt_revision_id")) or not _la_int(kq.get("revision"), toi_thieu=1) or kq.get("trang_thai") not in TRANG_THAI_KT
            or not _la_uuid(None if r.get("receipt_id") is None else str(r["receipt_id"])) or not isinstance(r.get("lap_lai"), bool)):
        _dto_sai("ACK: kt_revision_id/revision/trang_thai/receipt_id/lap_lai")
    if kq.get("hanh_dong") == "XAC_NHAN" and (kq["trang_thai"] != TT_DA_XAC_NHAN or kq.get("loai") != "XAC_NHAN"):
        _dto_sai("ACK xác nhận phải là revision XAC_NHAN")
    if kq.get("hanh_dong") == "LUU" and (kq.get("loai") != "NHAP" or kq["trang_thai"] == TT_DA_XAC_NHAN):
        _dto_sai("ACK lưu phải là revision NHAP — lưu không tự xác nhận")
    return {"schema": SCHEMA, "context": kiem_ngu_canh(kq.get("context")), "kt_revision_id": kq["kt_revision_id"], "revision": kq["revision"],
            "trang_thai": kq["trang_thai"], "lap_lai": r["lap_lai"] or kq.get("trung_xac_nhan") is True, "receipt_id": str(r["receipt_id"]),
            "ap": dict(AP), "request": dict(REQUEST), "hanh_dong": kq.get("hanh_dong"), "khoa": khoa, "thieu": list(kq.get("thieu") or [])}


# ================================================================================================== ghim đồ thị producer M24 (giao dịch chủ bảng)
# lệnh ghi đi qua `_goi` → hành động KT mà m4.kt_khoa kiểm lại quyền + khóa TRƯỚC khi dựng căn cứ (lệnh khác → từ chối, không đoán)
LENH_HANH = (("m4.kt_luu(", "LUU"), ("m4.kt_xac_nhan_lenh(", "XAC_NHAN"))


def _hanh_lenh(sql: str) -> str:
    for ten, hanh in LENH_HANH:
        if ten in sql:
            return hanh
    raise DataError("M4_THAM_SO_SAI", "Lệnh kế toán không thuộc hợp đồng M4-03A.")


def _ghim_do_thi(xd, c, dt, cho: str):
    """Trong giao dịch chủ bảng ĐÃ kiểm lại quyền KT + giữ khóa HĐ: dựng đồ thị căn cứ của phiên bản MỚI NHẤT bằng ĐÚNG producer M24
    (DuyetDot._dot / _phien_ban + do_thi — tạm đổi sang danh tính người công bố L3, khôi phục danh tính KT trong finally) rồi ghim SHA đồ thị +
    co_so_l3_sha256 bằng chứng thực SET LOCAL của chính giao dịch này (m4._kt_chung_thuc_ghi kiểm phiên chủ bảng thật, danh tính đã khôi phục, quyền
    KT). Không tự dựng/rút gọn đồ thị, không so ở Python: SQL so với đồ thị đã seal."""
    r = xd._r1(c, "SELECT dot_id FROM m4.duyet_kt_cho WHERE id = %s::uuid", (cho,))
    d = None if r is None else DD.DuyetDot._dot(xd, c, str(r["dot_id"]))
    vs = [] if d is None else DD.DuyetDot._phien_ban(xd, c, str(d["id"]))
    if not vs:
        raise DataError("M4_KT_KHONG_THAY", "Không thấy hồ sơ chờ kế toán (hoặc ngoài phạm vi hiện hành).")
    g, gsha, _ = DD.do_thi(xd, c, dt, d, vs[-1])
    return xd._r1(c, "SELECT m4._kt_chung_thuc_ghi(%s::uuid, %s::uuid, %s::uuid, %s, %s) AS a",
                  (cho, dt["id"], vs[-1]["id"], gsha, g["co_so_l3_sha256"]))["a"]


# ================================================================================================== dịch vụ
class KeToanNghiemThuK2:
    def __init__(self, xd):
        self.xd = xd

    # ------------------------------------------------------------------ đọc (quyền KT qua login thường TRƯỚC; hiện hành trên giao dịch chủ bảng)
    def danh_sach(self, dang_nhap: str) -> dict:
        """Gốc trong phạm vi KT (login thường) → mỗi gốc MỘT giao dịch chủ bảng riêng hữu hạn: quyền → khóa đọc → ghim đồ thị → m4._kt_hien_hanh.
        Gốc mất quyền giữa hai bước → bỏ dòng; phong bì mới nhất khác dòng đã đọc → không hiện hành (CAN_KIEM_LAI)."""
        xd = self.xd
        dt = xd.danh_tinh(dang_nhap)
        with xd._tx(dt):
            r = xd._mot("SELECT m4.kt_danh_sach() AS ds")
        items = []
        for x in (r or {}).get("ds") or []:
            h = self._hien_hanh(dt, x.get("kt_pending_id"))
            if h is None:
                continue
            items.append(dong_ds_dto({**x, "hien_hanh": h.get("hien_hanh") is True and h.get("phong_bi_id") == x.get("phong_bi_id")}))
        return {"schema": SCHEMA, "items": items}

    def _hien_hanh(self, dt, cho: str) -> dict | None:
        xd = self.xd
        with xd._tx_review(dt) as c:
            if not (xd._r1(c, "SELECT m4.kt_doc_cho(%s::uuid) AS ok", (cho,)) or {}).get("ok"):
                return None
            xd._r1(c, "SELECT m4._kt_khoa_doc(%s::uuid) AS q", (cho,))
            _ghim_do_thi(xd, c, dt, cho)
            return (xd._r1(c, "SELECT m4._kt_hien_hanh(%s::uuid) AS h", (cho,)) or {}).get("h") or {}

    def _chi_tiet(self, dt, cho: str, pb: str | None) -> dict:
        """Chi tiết trên login thường (kiểm sớm trước lệnh: phong bì/nguồn/PDF/căn cứ VAT). Phiên ứng dụng không có chứng thực producer nên KHÔNG bao
        giờ thấy hiện hành — lệnh SQL quyết lại dưới khóa."""
        xd = self.xd
        with xd._tx(dt):  # một câu lệnh = một snapshot: quyền + nguồn + KT + lịch sử
            r = xd._mot("SELECT m4.kt_chi_tiet(%s::uuid, %s::uuid) AS ct", (cho, pb))
        if not r or not isinstance(r.get("ct"), dict):
            raise DataError("M4_KT_KHONG_THAY", "Không thấy hồ sơ chờ kế toán (hoặc ngoài phạm vi hiện hành).")
        return r["ct"]

    def _chi_tiet_chu(self, dt, cho: str, pb: str | None) -> dict:
        """Chi tiết cho người xem: quyền KT qua login thường TRƯỚC; rồi MỘT giao dịch chủ bảng: kiểm lại quyền + HĐ FOR SHARE → ghim đồ thị producer →
        m4.kt_chi_tiet (hiện hành toàn căn cứ do SQL quyết trong cùng giao dịch)."""
        xd = self.xd
        with xd._tx(dt):
            xd._mot("SELECT m4.kt_kiem(%s::uuid, 'XEM') AS q", (cho,))
        with xd._tx_review(dt) as c:
            xd._r1(c, "SELECT m4._kt_khoa_doc(%s::uuid) AS q", (cho,))
            _ghim_do_thi(xd, c, dt, cho)
            r = xd._r1(c, "SELECT m4.kt_chi_tiet(%s::uuid, %s::uuid) AS ct", (cho, pb))
        if not r or not isinstance(r.get("ct"), dict):
            raise DataError("M4_KT_KHONG_THAY", "Không thấy hồ sơ chờ kế toán (hoặc ngoài phạm vi hiện hành).")
        return r["ct"]

    def xem(self, dang_nhap: str, *, kt_pending_id, phong_bi_id=None) -> dict:
        cho = DD._uuid(kt_pending_id, "kt_pending_id")
        pb = None if phong_bi_id in (None, "") else DD._uuid(phong_bi_id, "phong_bi_id")
        dt = self.xd.danh_tinh(dang_nhap)
        return xem_dto(self._chi_tiet_chu(dt, cho, pb))

    def tep_pdf(self, dang_nhap: str, kt_pending_id, phong_bi_id) -> tuple[str, str, bytes]:
        """PDF hồ sơ đã duyệt của ĐÚNG seal phong bì (gồm phong bì lịch sử cùng gốc): quyền KT hiện hành TRƯỚC tra cứu/kho; hash + độ dài kiểm lại;
        quyền + metadata kiểm lại SAU khi đọc blob (thu hồi giữa chừng → không trả bytes)."""
        xd = self.xd
        cho, pb = DD._uuid(kt_pending_id, "kt_pending_id"), DD._uuid(phong_bi_id, "phong_bi_id")
        dt = xd.danh_tinh(dang_nhap)

        def meta():
            with xd._tx(dt):
                r = xd._mot("SELECT m4.kt_pdf(%s::uuid, %s::uuid) AS p", (cho, pb))
            p = (r or {}).get("p")
            if not isinstance(p, dict) or p.get("media_type") != NR.MEDIA_PDF or not _la_sha(p.get("raw_sha256")) \
                    or not _la_int(p.get("byte_length"), toi_thieu=1) or not isinstance(p.get("ten"), str):
                raise DataError("M4_KT_KHONG_THAY", "Không thấy PDF hồ sơ đã duyệt của phong bì (hoặc ngoài phạm vi hiện hành).")
            return p
        p = meta()
        raw = xd._raw(p["raw_sha256"], p["byte_length"])
        if meta() != p:
            raise DataError("M4_KT_NGUON_DOI", "PDF hồ sơ đã duyệt đổi trong lúc tải — tải lại.")
        return p["ten"], NR.MEDIA_PDF, raw

    # ------------------------------------------------------------------ lệnh (kết nối chủ bảng; quyền → khóa → biên nhận → CAS trong SQL)
    def _truoc_lenh(self, dt, yc: dict) -> dict:
        """Kiểm sớm trên login thường (SQL kiểm lại toàn bộ dưới khóa): quyền KT hiện hành + phong bì thuộc gốc + toàn vẹn bytes PDF đã duyệt."""
        ct = self._chi_tiet(dt, yc["kt_pending_id"], yc["phong_bi_id"])
        x = xem_dto(ct)
        p = x["nguon"]["pdf"]
        self.xd._raw(p["raw_sha256"], p["byte_length"])
        return x

    def _can_cu_vat(self, x: dict, tep_id: str | None):
        if tep_id is None:
            return
        t = next((t for t in x["nguon"]["tep_can_cu"] if t["id"] == tep_id), None)
        if t is None:
            raise DataError("M4_KT_CAN_CU_VAT_SAI", "Tệp căn cứ VAT không thuộc hồ sơ/HĐ của nguồn trong phạm vi kế toán hiện hành.")
        self.xd._raw(t["raw_sha256"], t["byte_length"])

    def _goi(self, dt, sql: str, params: tuple, khoa: str) -> dict:
        """MỘT giao dịch chủ bảng: m4.kt_khoa (quyền KT hiện hành → khóa HĐ→đợt→phiên bản→gốc→revision) → ghim đồ thị producer → lệnh SQL (biên nhận
        → phát lại/CAS → INSERT; trigger kiểm lại hiện hành toàn căn cứ). Mỗi lệnh/phát lại dựng lại chứng thực, không mượn của giao dịch khác."""
        xd = self.xd
        hanh, cho = _hanh_lenh(sql), params[2]
        with xd._chua_ro():
            with xd._tx_review(dt) as c:
                xd._r1(c, "SELECT m4.kt_khoa(%s::uuid, %s) AS q", (cho, hanh))
                _ghim_do_thi(xd, c, dt, cho)
                r = xd._r1(c, sql, params)["r"]
        return ack_dto(r, khoa)

    @staticmethod
    def _body(body, kw) -> dict:
        if body is not None and kw:
            _yc_sai("Gửi body một lần (object hoặc tham số tên), không trộn.")
        return kw if body is None else body

    def luu(self, dang_nhap: str, body: dict | None = None, **kw) -> dict:
        """Lưu NHÁP KT (được thiếu; không tự xác nhận): revision mới trên phong bì hiện hành. expected_revision = kt.revision đang xem, hoặc 0 CHỈ
        khi kt === null (lệnh tạo nháp đầu của phong bì)."""
        khoa, yc = kiem_luu(self._body(body, kw))
        dt = self.xd.danh_tinh(dang_nhap)
        x = self._truoc_lenh(dt, yc)
        tt_nguon = x["nguon"]["tien_te"]
        if yc["tien_te"] is not None and yc["tien_te"] != tt_nguon:
            raise DataError("M4_KT_TIEN_TE_KHAC", "Tiền tệ KT phải đúng tiền tệ nguồn đã seal (không quy đổi).")
        if tt_nguon == "VND":
            for k in TIEN_KT:
                _tien(yc[k], k, vnd=True)
        self._can_cu_vat(x, yc["vat_can_cu_tep_id"])
        nd = {k: yc[k] for k in DU_LIEU}
        return self._goi(dt, "SELECT m4.kt_luu(%s, %s::jsonb, %s::uuid, %s::uuid, %s, %s::integer, %s::jsonb) AS r",
                         (khoa, json.dumps(yc, ensure_ascii=False), yc["kt_pending_id"], yc["phong_bi_id"], yc["expected_phong_bi_sha256"],
                          yc["expected_revision"], json.dumps(nd, ensure_ascii=False)), khoa)

    def xac_nhan(self, dang_nhap: str, body: dict | None = None, **kw) -> dict:
        """Xác nhận ĐÚNG bản nháp mới nhất đã lưu của phong bì hiện hành (máy chủ sao y dữ liệu đã lưu). Kết quả: KT_DA_XAC_NHAN_CHO_GHI_CONG_NO —
        CHƯA ghi công nợ (AP thuộc M4-03B), không Request (M4-04)."""
        khoa, yc = kiem_xac_nhan_body(self._body(body, kw))
        dt = self.xd.danh_tinh(dang_nhap)
        x = self._truoc_lenh(dt, yc)
        nhap = next((r["kt"] for r in x["lich_su"]["kt"] if r["kt"]["kt_revision_id"] == yc["kt_revision_id"]), None)
        if nhap is not None and nhap["vat_trang_thai"] == "CO_CAN_CU":
            self._can_cu_vat(x, nhap["vat_can_cu_tep_id"])
        return self._goi(dt, "SELECT m4.kt_xac_nhan_lenh(%s, %s::jsonb, %s::uuid, %s::uuid, %s, %s::uuid, %s::integer) AS r",
                         (khoa, json.dumps(yc, ensure_ascii=False), yc["kt_pending_id"], yc["phong_bi_id"], yc["expected_phong_bi_sha256"],
                          yc["kt_revision_id"], yc["expected_revision"]), khoa)
