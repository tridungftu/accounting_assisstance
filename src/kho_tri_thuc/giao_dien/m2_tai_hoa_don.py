"""M2-00E — HTTP mỏng cho nút "Tải từ cổng thuế" trong M2 (TL 43 §3), nối giao diện với `m2/tai_hoa_don` (điều phối M2-00B, nhận M2c).

Không viết lại logic: `DieuPhoiTaiHoaDon` giữ phiên + quyền HIỆN HÀNH theo pháp nhân, binding bất biến, nhật ký `nhat_ky.su_kien`, RPC/SSE tới bộ tải #7
sở hữu; `nhan.py` đọc manifest và nhận qua đường K2 sẵn có. Module này chỉ: (1) dựng cấu hình/điều phối từ máy chủ (không nhận gì từ trình duyệt), (2) lọc DTO
trước khi trả (không mật khẩu/capability/nonce/đường dẫn tuyệt đối), (3) đổi lỗi thành mã + câu tiếng Việt + gợi ý.

Route (cùng token X-KTT-Token, cookie phiên HttpOnly do máy chủ cấp như /api/m2):
  GET  /api/m2/tai-hoa-don                                   → trạng thái bộ tải + pháp nhân/profile ĐƯỢC PHÉP (không bí mật). Chưa cấu hình → 200 cau_hinh:false
  POST /api/m2/tai-hoa-don/khoi-dong   {}                    → mở bộ tải ngầm (idempotent); cần ít nhất một pháp nhân được phép
  POST /api/m2/tai-hoa-don/bat-dau     {9 trường, khoa}      → một lựa chọn = một lần tải (Node #7 một job tại một thời điểm)
  GET  /api/m2/tai-hoa-don/trang-thai?run=…                  → trạng thái run (RUNNING / REPLAY + biên nhận / UNKNOWN)
  GET  /api/m2/tai-hoa-don/su-kien?run=…&cursor=n            → SSE đã lọc (log/phase/month/progress/manifest/error/done)
  POST /api/m2/tai-hoa-don/doi-soat    {run}                 → đối soát run chưa rõ
  POST /api/m2/tai-hoa-don/nhan        {run}                 → nhận kết quả (theo manifest) vào M2; trả "mới / đổi trạng thái / không mã / lỗi"
  POST /api/m2/tai-hoa-don/mo-thu-muc  {run, run_rel}        → bộ tải mở thư mục run trên máy
  GET  /api/m2/tai-hoa-don/manifest?run=…&run_rel=…          → tóm tắt manifest (số đếm, nhóm, lỗi; KHÔNG nội dung từng hóa đơn)

Trình duyệt KHÔNG gửi actor/pháp nhân/profile/đường dẫn/cổng/mật khẩu/captcha → 403 M2_CLIENT_AUTHORITY. Cấu hình lấy từ `[tai_hoa_don]` của cấu hình DEMO (vắng →
"Bộ tải chưa cấu hình", không lỗi) hoặc seam `app._tai_hoa_don = {"cau_hinh": CauHinhTaiHoaDon, "tien_trinh": …}` do máy chủ/test tiêm.
Bộ tải #7 thật chưa có trong repo; mã này không bao giờ gọi cổng thuế — chỉ nói chuyện với Node sở hữu qua loopback.
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path

from ..ha_tang.primitives import DataError
from ..m2.tai_hoa_don import CauHinhTaiHoaDon, DieuPhoiTaiHoaDon, TepPin, TienTrinhNode
from ..m2.tai_hoa_don.cau_hinh import kiem_khong_reparse
from ..m2.tai_hoa_don.dieu_phoi import RE_RUN_REL
from ..m2.tai_hoa_don.manifest import doc_manifest
from ..m2.tai_hoa_don.nhan import lap_ke_hoach_nhan, nhan_vao_k2

TIEN_TO = "/api/m2/tai-hoa-don"
PHIEN_BAN = "m2_00e.v1"
CHON_BAT_DAU = frozenset({"source_instance", "scope_ref", "company_key", "mode", "year", "month", "types", "formats", "khoa"})
KHONG_NHAN = frozenset({
    "actor", "nguoi", "dang_nhap", "dang_nhap_thuc_hien", "phap_nhan", "phap_nhan_id", "phap_nhan_ma", "profile", "profile_ref", "profile_revision",
    "tai_khoan", "mat_khau", "password", "username", "token", "captcha", "path", "duong_dan", "url", "dsn", "cong", "port", "node", "argv", "roots",
    "run_id", "nonce", "request_key", "client_key", "context", "capability", "trang_thai", "approved", "quyen", "module", "vai", "vai_tro"})
YEU_CAU_CAU_HINH = ("goc_bo_tai", "node_exe", "node_sha256", "phien_ban_bo_tai", "thu_muc_tai", "thu_muc_trinh_duyet", "thu_muc_profile",
                    "thu_muc_dieu_phoi", "tep_pin")
MA_CHUA_CAU_HINH = frozenset({"TAI_HOA_DON_CHUA_CAU_HINH", "TAI_HOA_DON_CAU_HINH_SAI", "CRM_CHUA_CAU_HINH", "PG_KHONG_KET_NOI", "THAT_UI"})
RE_HANDLE = re.compile(r"[0-9a-f]{64}")
RE_MA = re.compile(r"[A-Z0-9][A-Z0-9_+]{0,79}")
RE_KY = re.compile(r"\d{4}-(?:0[1-9]|1[0-2])")
LOAI_CHIEU = ("purchase", "sold")
TRANG_THAI_RECEIPT = frozenset({"COMPLETE", "PARTIAL", "FAILED", "CONFLICT", "HOAN_TAT", "UNKNOWN"})
TRANG_THAI_RUN = frozenset({"COMPLETE", "PARTIAL", "FAILED", "CONFLICT", "HOAN_TAT", "UNKNOWN", "NOT_FOUND"})
# mã vào kho K2 mà M2c trả để nói "không phải lỗi": bảng kê (HĐ không mã), tiền tệ chờ người duyệt, cảnh báo quan hệ/XML chưa yêu cầu
CANH_BAO_NHAN = frozenset({"XML_CHUA_YEU_CAU", "QUAN_HE_CHUA_RO", "TIEN_TE_CHUA_RO", "TIEN_TE_XUNG_DOT"})
LY_DO_PROFILE = {
    "NODE_CHUA_SAN_SANG": "Bộ tải chưa mở — bấm “Mở bộ tải”.",
    "PROFILE_NOT_FOUND": "Chưa có hồ sơ đăng nhập cổng thuế của pháp nhân này trong thư mục profiles của bộ tải.",
    "PROFILE_UNREADABLE": "Hồ sơ đăng nhập cổng thuế của pháp nhân này đọc không được hoặc thiếu trường.",
}
GOI_Y = {
    "TAI_HOA_DON_CHUA_CAU_HINH": "Bộ tải #7 chưa được cài/cấu hình trên máy này. Báo Claude đặt mục [tai_hoa_don] trong cấu hình; phần mềm vẫn dùng bình thường.",
    "TAI_HOA_DON_CAU_HINH_SAI": "Báo Claude kiểm lại mục [tai_hoa_don] (đường dẫn, bản Node và tệp bộ tải đã ghim).",
    "M2_00B_NODE_CHUA_SAN_SANG": "Bộ tải chưa mở. Bấm “Mở bộ tải” trước khi tải.",
    "M2_00B_JOB_BUSY": "Bộ tải đang chạy một lần tải khác. Đợi lần đó xong rồi tải tiếp.",
    "M2_00B_KHACH_KHONG_KET_NOI": "Mất kết nối tới bộ tải. Bấm “Đối soát” để kiểm tra lần tải; đừng tải lại ngay.",
    "M2_00B_KHACH_QUA_HAN": "Bộ tải trả lời quá chậm. Bấm “Đối soát” để kiểm tra lần tải; đừng tải lại ngay.",
    "M2_00B_CAN_DOI_SOAT": "Lần tải thuộc phiên khác. Kiểm tra bằng cách đối soát từ phiên đã bắt đầu.",
    "M2_00B_NGU_CANH_DOI": "Vai, quyền hoặc hồ sơ nguồn đã đổi sau khi bắt đầu tải — kết quả cũ không còn hiệu lực. Tải lại trang rồi chọn lại.",
    "M2_00B_PN_MAPPING_ABSENT": "Vai hiện tại không thấy mapping công ty → pháp nhân này (chưa duyệt, hoặc ngoài quyền). Chọn pháp nhân trong danh sách; nếu thiếu, nhờ CFO duyệt mapping.",
    "M2_00B_PN_MAPPING_CONFLICT": "Công ty này đang có nhiều hơn một mapping hiện hành. Báo CFO xử lý mapping rồi tải lại.",
    "M2_00B_KHOA_DA_DUNG":"Khóa thao tác này đã dùng cho lựa chọn khác. Bấm “Tải từ cổng thuế” lại để lấy khóa mới.",
    "M2_00B_NHAT_KY_LOI": "Chưa ghi được nhật ký nên chưa tải. Thử lại; nếu lặp lại, báo Claude.",
    "M2_00E_DANG_CHAY": "Bộ tải còn đang chạy. Đợi xong rồi nhận vào M2.",
    "M2_00E_CHUA_CO_KET_QUA": "Lần tải chưa có biên nhận. Bấm “Đối soát” rồi thử lại.",
}
GOI_Y_TIEN_TO = (
    (("KHONG_CO_QUYEN", "NGUON_KHONG_CO_QUYEN"), "Vai hiện tại không được tải hoặc xem pháp nhân này. Đổi vai (nếu đúng) rồi thử lại."),
    (("M2_00B_NODE_", "M2_00B_TEP_PIN_", "M2_00B_BAT_TAY_", "M2_00B_SAN_SANG_", "M2_00B_JOB_KHONG_HO_TRO"),
     "Cài đặt bộ tải chưa đúng bản đã ghim hoặc không khởi động được. Báo Claude kiểm lại bộ tải; chưa gọi cổng thuế."),
)
# Mã lỗi → HTTP. Mặc định M2_00B_* chưa liệt kê (Node từ chối / trả sai hợp đồng) = 502.
HTTP_403 = frozenset({"M2_CLIENT_AUTHORITY", "DANH_TINH", "NGUON_PROFILE", "NGUON_PHAM_VI", "NGUON_PROFILE_DIGEST", "THAT_UI"})
HTTP_404 = frozenset({"M2_00B_RUN_KHONG_CO", "NOT_FOUND"})
HTTP_409 = frozenset({"M2_00B_KHOA_DA_DUNG", "M2_00B_NGU_CANH_DOI", "M2_00B_CAN_DOI_SOAT", "M2_00B_PHIEN_DOI", "M2_00B_JOB_BUSY", "M2_00B_BINDING_HONG",
                      "M2_00B_CONTEXT_MISMATCH", "M2_00B_DANH_TINH_DOI", "M2_00B_PN_KHONG_KHOP", "M2_00B_MA_PN_KHONG_DUNG_DUOC", "M2_00B_PN_MAPPING_ABSENT",
                      "M2_00B_PN_MAPPING_CONFLICT", "M2_00E_DANG_CHAY", "M2_00E_CHUA_CO_KET_QUA"})
HTTP_503 = frozenset({"TAI_HOA_DON_CHUA_CAU_HINH", "TAI_HOA_DON_CAU_HINH_SAI", "M2_00B_CHUA_CAU_HINH", "M2_00B_KET_NOI_KHAC", "M2_00B_NHAT_KY_LOI",
                      "M2_00B_NODE_CHUA_SAN_SANG", "CRM_CHUA_CAU_HINH", "PG_KHONG_KET_NOI"})
HTTP_400 = frozenset({"CRM_PHIEN", "M2_00B_CHON_SAI", "M2_00B_KHOA_SAI", "M2_00B_KY_SAI", "M2_00B_RUN_HANDLE", "M2_00B_RUN_REL_SAI", "M2_00B_HANG_DOI_SAI",
                      "M2_YEU_CAU_SAI", "INVALID_REQUEST"})

_KHOI_TAO = threading.Lock()
_KHOI_DONG = threading.Lock()


# ---------------------------------------------------------------------------------------------- cấu hình + dịch vụ
def dung_cau_hinh(thong_so) -> CauHinhTaiHoaDon:
    """`[tai_hoa_don]` (đã kiểm kiểu bởi Config) → CauHinhTaiHoaDon (kiểm đường dẫn/hash/gốc tách biệt). Thiếu/sai → mã TAI_HOA_DON_* tiếng Việt, không lộ đường dẫn."""
    if not isinstance(thong_so, dict) or not thong_so:
        raise DataError("TAI_HOA_DON_CHUA_CAU_HINH", "Bộ tải chưa cấu hình (cấu hình chưa có mục [tai_hoa_don]).")
    thieu = [k for k in YEU_CAU_CAU_HINH if not thong_so.get(k)]
    if thieu:
        raise DataError("TAI_HOA_DON_CHUA_CAU_HINH", "Bộ tải chưa cấu hình đủ — mục [tai_hoa_don] còn thiếu: " + ", ".join(thieu) + ".")
    try:
        return CauHinhTaiHoaDon(
            node_exe=Path(thong_so["node_exe"]), node_sha256=thong_so["node_sha256"], goc_7=Path(thong_so["goc_bo_tai"]),
            tep_pin=tuple(TepPin(rel, h) for rel, h in sorted(thong_so["tep_pin"].items())), phien_ban_bo_tai=thong_so["phien_ban_bo_tai"],
            goc_tai=Path(thong_so["thu_muc_tai"]), goc_trinh_duyet=Path(thong_so["thu_muc_trinh_duyet"]), goc_profile=Path(thong_so["thu_muc_profile"]),
            goc_dieu_phoi=Path(thong_so["thu_muc_dieu_phoi"]), cong=thong_so.get("cong", 0))
    except DataError as exc:
        raise DataError("TAI_HOA_DON_CAU_HINH_SAI", f"Cấu hình bộ tải chưa dùng được ({exc.code}).") from None


class _KhoaChung:
    """Khóa tái nhập quanh `app.mutation_lock`: mọi đoạn DB của điều phối (đi chung MỘT app connection với CRM/M2) tuần tự cùng các route khác,
    còn IO Node/SSE dài chạy NGOÀI khóa. Chỉ dùng trong DieuPhoiApp."""

    def __init__(self, khoa):
        self._khoa, self._chu, self._dem = khoa, None, 0

    def __enter__(self):
        t = threading.get_ident()
        if self._chu == t:
            self._dem += 1
        else:
            self._khoa.acquire()
            self._chu, self._dem = t, 1
        return self

    def __exit__(self, *_):
        self._dem -= 1
        if self._dem == 0:
            self._chu = None
            self._khoa.release()


class DieuPhoiApp(DieuPhoiTaiHoaDon):
    """Điều phối M2-00B gắn vào LocalApp: dùng khóa của app, thêm vài hàm đọc/kiểm run cho wiring (không đổi lớp m2/tai_hoa_don)."""

    def __init__(self, app, cau_hinh, *, tien_trinh, goc_hoi_cuu_tin_cay=()):
        super().__init__(app, cau_hinh, tien_trinh=tien_trinh)
        self._khoa = _KhoaChung(app.mutation_lock)
        self.tien_trinh = tien_trinh
        # M2d: gốc tin cậy cho manifest HOI_CUU (tệp để tại chỗ). Luôn gồm thư mục tải + gốc dữ liệu cũ ghi trong cấu hình; KHÔNG lấy gốc do manifest tự khai báo.
        self.goc_hoi_cuu_tin_cay = tuple(dict.fromkeys([str(cau_hinh.goc_tai), *(str(x) for x in goc_hoi_cuu_tin_cay)]))

    def khoi_dong_neu_can(self) -> dict:
        with _KHOI_DONG:
            if self.tien_trinh.dang_chay():
                return {"trang_thai": "SAN_SANG"}
            try:
                return self.khoi_dong()
            except DataError as exc:
                if exc.code != "M2_00B_DA_KHOI_DONG":
                    raise
            self.stop()  # tiến trình con cũ đã chết nhưng chưa dọn: dừng đúng cây sở hữu rồi khởi động lại một lần
            return self.khoi_dong()

    def ngu_canh(self, sid, run_handle) -> dict:
        b = self._binding_cua_phien(sid, run_handle)
        return {"source_instance": b["source_instance"], "scope_ref": b["scope_ref"], "company_key": b["company_key"],
                "phap_nhan_ma": b["phap_nhan"]["ma"], "run_id": b["context"]["run"]["run_id"], "yeu_cau": dict(b["request"])}

    def kiem_run(self, sid, run_handle) -> dict:
        """Phiên + quyền hiện hành + bộ tải sẵn sàng, TRƯỚC khi mở luồng SSE (lỗi phải thành JSON thường, không thành luồng hỏng)."""
        b = self._binding_cua_phien(sid, run_handle)
        self._khach()
        with self._kiem_lai(sid, b):
            pass
        return b

    def ghi_nhat_ky(self, sid, run_handle, hanh_dong, them) -> str:
        return self._nhat_ky_sau(sid, self._binding_cua_phien(sid, run_handle), hanh_dong, them)


def dich_vu(app) -> DieuPhoiApp:
    dv = app.__dict__.get("_tai_hoa_don_dv")
    if dv is not None:
        return dv
    with _KHOI_TAO:
        dv = app.__dict__.get("_tai_hoa_don_dv")
        if dv is None:
            seam = app.__dict__.get("_tai_hoa_don")
            seam = seam if isinstance(seam, dict) else {}
            cau_hinh, thong_so = seam.get("cau_hinh"), seam.get("thong_so")
            if cau_hinh is None:
                thong_so = getattr(getattr(app, "demo_config", None), "tai_hoa_don", None)
                cau_hinh = dung_cau_hinh(thong_so)
            goc_cu = seam.get("goc_hoi_cuu_tin_cay") or (thong_so or {}).get("goc_hoi_cuu_tin_cay") or ()
            dv = DieuPhoiApp(app, cau_hinh, tien_trinh=seam.get("tien_trinh") or TienTrinhNode(cau_hinh), goc_hoi_cuu_tin_cay=goc_cu)
            app.__dict__["_tai_hoa_don_dv"] = dv
    return dv


def dung(app):
    """Gọi khi máy chủ dừng: dừng bộ tải sở hữu (nếu đã mở). Không lỗi nếu chưa dùng tính năng này."""
    dv = app.__dict__.get("_tai_hoa_don_dv")
    if dv is not None:
        try:
            dv.stop()
        except Exception:  # noqa: BLE001 — dừng máy chủ không được kẹt vì bộ tải; Windows Job KILL_ON_JOB_CLOSE dọn nốt
            pass


# ---------------------------------------------------------------------------------------------- lỗi → mã + tiếng Việt + gợi ý
def trang_thai_http(code: str) -> int:
    if code in HTTP_404:
        return 404
    if code in HTTP_409:
        return 409
    if code in HTTP_403 or code.startswith(("KHONG_CO_QUYEN", "NGUON_KHONG_CO_QUYEN")):
        return 403
    if code in HTTP_503 or code.startswith(("M2_00B_NODE_", "M2_00B_TEP_PIN_", "M2_00B_BAT_TAY_", "M2_00B_SAN_SANG_", "M2_00B_JOB_KHONG_HO_TRO")):
        return 503
    if code in HTTP_400:
        return 400
    return 502 if code.startswith("M2_00B_") else 400


def goi_y_ma(code: str):
    if code in GOI_Y:
        return GOI_Y[code]
    for tien_to, y in GOI_Y_TIEN_TO:
        if code.startswith(tien_to):
            return y
    return None


def goi_y_cong_thue(http_status, code=None):
    """Gợi ý theo mã HTTP của cổng thuế ghi trong biên nhận/manifest (TL 43 §3 bước 5)."""
    if http_status in (401, 403):
        return "Token cổng thuế đã hết hạn. Bấm “Tải từ cổng thuế” lại và đăng nhập lại (gõ captcha trong cửa sổ Chrome)."
    if http_status in (400, 404):
        return "Cổng thuế có thể đã đổi API. Dừng tải; báo Claude sửa config.js của bộ tải."
    if http_status == 429:
        return "Cổng thuế giới hạn tốc độ. Đợi vài phút rồi tải lại."
    if isinstance(http_status, int) and http_status >= 500:
        return "Cổng thuế đang lỗi. Thử lại sau."
    if code == "LOGIN_TIMEOUT":
        return "Quá hạn chờ đăng nhập (8 phút). Tải lại và gõ captcha trong cửa sổ Chrome kịp hạn."
    return None


def mo_ta_loi(exc: DataError):
    code = str(exc.code)
    body = {"error": code, "message": str(exc)}
    y = goi_y_ma(code)
    if y:
        body["goi_y"] = y
    return trang_thai_http(code), body


# ---------------------------------------------------------------------------------------------- lọc DTO (chỉ whitelist ra trình duyệt)
_KHOA_BI_MAT = (r"mat[_ -]?khau|matkhau|pass[a-z0-9_-]*|pwd|secret|token|nonce|capability|captcha|cookie|authorization|api[_-]?key|username|tai[_-]?khoan|"
                r"request[_-]?key|m2[_-]cap")
_GIA_TRI = r"(?:(?:bearer|basic)\s+)?(?:\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|\S+)"  # giá trị trong nháy kép/đơn (kể cả khoảng trắng, nháy thoát) hoặc đến hết khoảng trắng; có thể mở bằng Bearer/Basic
_BI_MAT = re.compile(
    r"(?i)[\"']?[a-z0-9_.-]*(?:" + _KHOA_BI_MAT + r")[a-z0-9_-]*[\"']?\s*[:=]\s*" + _GIA_TRI   # password=..., "password":"...", TAX_PASSWORD='a b', nonce=..., capability=...
    + r"|bearer\s+" + _GIA_TRI
    + r"|[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"                                    # dạng JWT
    + r"|(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{40,}(?![A-Za-z0-9_-])")                                         # chuỗi dài giống capability/token không kèm khóa
_DUONG_PROFILE = re.compile(r"(?i)(?:[^\s\"'<>|]*[\\/])?profiles[\\/][^\s\"'<>|]*|(?<![A-Za-z0-9_.-])[A-Za-z0-9_.-]+\.env(?![A-Za-z0-9_-])")
_DUONG_TUYET_DOI = re.compile(r"(?i)(?<![A-Za-z0-9])[a-z]:[\\/][^\s\"'<>|]*|\\\\[^\s\"'<>|]+")


def an_toan(msg, toi_da=400) -> str:
    """Dòng log của bộ tải → chuỗi hiển thị. Node đã tự che bí mật; đây là lớp thứ hai — thà che thừa còn hơn lộ:
    đường dẫn tới profiles\\*.env → [profile]; đường dẫn tuyệt đối → [đường dẫn]; `khóa=giá trị` / `"khóa":"giá trị"` (giá trị có nháy đơn/kép hoặc khoảng trắng) với khóa
    mật khẩu/pass*/secret/token/nonce/capability/captcha/cookie/authorization/api_key/username/request_key → [AN]; bearer …; dạng JWT; chuỗi dài ≥ 40 ký tự."""
    s = "".join(c for c in str(msg) if c == "\t" or c >= " ")[:toi_da]
    s = _DUONG_PROFILE.sub("[profile]", s)
    s = _BI_MAT.sub("[AN]", s)
    return _DUONG_TUYET_DOI.sub("[đường dẫn]", s)


def _ma(v):
    return v if isinstance(v, str) and RE_MA.fullmatch(v) else None


def _so(v, nho=0, lon=10**9):
    return v if type(v) is int and nho <= v <= lon else None


def loi_sach(entry):
    """`{code, stage, http_status}` của bộ tải (hoặc mã trần) → dict an toàn + gợi ý theo HTTP cổng thuế."""
    if isinstance(entry, str):
        entry = {"code": entry}
    if not isinstance(entry, dict):
        return {"code": "UNSPECIFIED", "stage": None, "http_status": None, "goi_y": None}
    code, stage, st = _ma(entry.get("code")) or "UNSPECIFIED", _ma(entry.get("stage")), _so(entry.get("http_status"), 0, 999)
    return {"code": code, "stage": stage, "http_status": st, "goi_y": goi_y_cong_thue(st, code)}


def _run_rel(v):
    return v if isinstance(v, str) and RE_RUN_REL.fullmatch(v) else None


def lam_sach_run(d: dict) -> dict:
    """DTO của `DieuPhoiTaiHoaDon` (đã đóng) → chỉ giữ trường biết trước; biên nhận/đối soát do Node trả nên kiểm lại kiểu và dạng."""
    out = {k: d.get(k) for k in ("phien_ban", "run_handle", "trang_thai", "run_id", "phap_nhan_ma", "company_key", "yeu_cau", "nhat_ky", "can_doi_soat", "ma")}
    kq = d.get("ket_qua")
    if isinstance(kq, dict):
        out["ket_qua"] = {"trang_thai": kq.get("trang_thai") if kq.get("trang_thai") in TRANG_THAI_RECEIPT else None, "runs": [
            {"ky": r.get("ky") if isinstance(r.get("ky"), str) and RE_KY.fullmatch(r["ky"]) else None, "chieu": r.get("chieu") if r.get("chieu") in LOAI_CHIEU else None,
             "run_rel": _run_rel(r.get("run_rel")), "trang_thai": r.get("trang_thai") if r.get("trang_thai") in TRANG_THAI_RUN else None,
             "loi": [loi_sach(x) for x in (r.get("loi") if isinstance(r.get("loi"), list) else [])[:50]]}
            for r in (kq.get("runs") or [])[:100] if isinstance(r, dict)]}
    else:
        out["ket_qua"] = None
    rec = d.get("doi_soat")
    out["doi_soat"] = None if not isinstance(rec, dict) else {"co_the_doi_soat": rec.get("co_the_doi_soat") is True, "hanh_dong": _ma(rec.get("hanh_dong")), "runs": [
        {"ky": r.get("ky") if isinstance(r.get("ky"), str) and RE_KY.fullmatch(r["ky"]) else None, "chieu": r.get("chieu") if r.get("chieu") in LOAI_CHIEU else None,
         "run_rel": _run_rel(r.get("run_rel")), "ton_tai": r.get("ton_tai") is True, "manifest": _ma(r.get("manifest")) if isinstance(r.get("manifest"), str) else None,
         "trang_thai_run": r.get("trang_thai_run") if r.get("trang_thai_run") in TRANG_THAI_RUN else None}
        for r in (rec.get("runs") or [])[:100] if isinstance(r, dict)]}
    if isinstance(out.get("ma"), str):  # `ma` của điều phối là mã ngắn của bộ tải (KHACH_*, JOB_BUSY…); gợi ý tra theo dạng M2_00B_<mã>
        out["ma"] = _ma(out["ma"])
        y = goi_y_ma("M2_00B_" + out["ma"]) if out["ma"] else None
        if y:
            out["goi_y"] = y
    return out


def loc_su_kien(ev: dict):
    """Một sự kiện SSE của Node → bản whitelist. Loại lạ / không đúng hình dạng → None (bỏ, không chuyển tiếp)."""
    t, p = ev.get("type"), ev.get("payload")
    seq = _so(ev.get("seq"), 0)
    if seq is None or not isinstance(p, dict):
        return None
    ts = ev.get("ts") if (type(ev.get("ts")) in (int, float) or (isinstance(ev.get("ts"), str) and len(ev["ts"]) <= 40)) else None
    out = {"seq": seq, "type": t, "ts": ts}
    ky = p.get("monthTag") if isinstance(p.get("monthTag"), str) and RE_KY.fullmatch(p["monthTag"]) else None
    chieu = p.get("type") if p.get("type") in LOAI_CHIEU else None
    if t == "log":
        out["payload"] = {"msg": an_toan(p.get("msg", ""))}
    elif t == "phase":
        out["payload"] = {"type": chieu, "label": an_toan(p.get("label", ""), 80), "monthTag": ky}
    elif t == "month":
        out["payload"] = {"monthTag": ky, "index": _so(p.get("index")), "total": _so(p.get("total"))}
    elif t == "progress":
        out["payload"] = {"type": chieu, "monthTag": ky, "index": _so(p.get("index")), "total": _so(p.get("total"))}
    elif t == "manifest":
        out["payload"] = {"run_rel": _run_rel(p.get("run_rel")), "trang_thai": p.get("trang_thai") if p.get("trang_thai") in TRANG_THAI_RUN else None}
    elif t == "error":
        out["payload"] = {"code": _ma(p.get("code")) or "UNSPECIFIED", "goi_y": goi_y_cong_thue(None, _ma(p.get("code")))}
    elif t == "done":
        out["payload"] = {"trang_thai": p.get("trang_thai") if p.get("trang_thai") in TRANG_THAI_RECEIPT else None, "so_run": _so(p.get("so_run"), 0, 1000)}
    else:
        return None
    return out


def ly_do_profile(ly_do):
    if ly_do is None:
        return None
    return LY_DO_PROFILE.get(ly_do) or f"Chưa sẵn sàng ({an_toan(ly_do, 60)})."


def _bo_tai(dv: DieuPhoiApp) -> dict:
    tt = dv.tien_trinh
    ts = getattr(tt, "trang_thai", None)
    out = {"san_sang": bool(tt.dang_chay()), "trang_thai": ts if isinstance(ts, str) and len(ts) <= 80 else None}
    if isinstance(ts, str) and ts.startswith("KHOI_DONG_LOI:"):
        ma = ts.split(":", 1)[1].split("+", 1)[0]
        out["loi_khoi_dong"] = _ma(ma) or "UNSPECIFIED"
        out["goi_y"] = goi_y_ma("M2_00B_NODE_" + out["loi_khoi_dong"])
    return out


# ---------------------------------------------------------------------------------------------- tóm tắt kết quả nhận (TL 43 §3 bước 3)
def tom_tat_nhan(ket_qua_runs: list) -> dict:
    """mới = FIRST_OBSERVATION; đổi trạng thái = revision chờ người kiểm (CHANGED_CONTENT_HOLD / ANCESTOR_REAPPEARANCE_HOLD); không mã = HĐ chỉ có bảng kê;
    lỗi = ngoại lệ tải/đọc + mục giữ chờ vì lý do khác bảng kê/tiền tệ. SAME_CONTENT_REPEAT đếm riêng là 'không đổi'."""
    t = {"moi": 0, "doi_trang_thai": 0, "khong_ma": 0, "loi": 0, "khong_doi": 0, "giu_cho_tien_te": 0}
    for r in ket_qua_runs:
        if r.get("loi") is not None:
            t["loi"] += 1
            continue
        for it in r.get("ket_qua", []):
            if it.get("trang_thai") == "DA_GHI_QUAN_SAT":
                for x in it.get("items", []):
                    c = x.get("classification")
                    c = {c} if isinstance(c, str) else set(c or [])
                    if "FIRST_OBSERVATION" in c:
                        t["moi"] += 1
                    elif c & {"CHANGED_CONTENT_HOLD", "ANCESTOR_REAPPEARANCE_HOLD"}:
                        t["doi_trang_thai"] += 1
                    elif "SAME_CONTENT_REPEAT" in c:
                        t["khong_doi"] += 1
            elif it.get("ly_do") == "K2_CHUA_NHAN_BANG_KE":
                t["khong_ma"] += 1
            elif str(it.get("ly_do", "")).startswith("TIEN_TE_"):
                t["giu_cho_tien_te"] += 1
            else:
                t["loi"] += 1
        t["loi"] += sum(1 for e in r.get("ngoai_le", []) if e["ma"] not in CANH_BAO_NHAN)
    return t


def _ngoai_le_sach(e: dict) -> dict:
    out = {"ma": _ma(e.get("ma")) or "UNSPECIFIED", "item_ordinal": _so(e.get("item_ordinal"), 0)}
    if isinstance(e.get("loi"), (dict, str)):
        out["loi"] = loi_sach(e["loi"])
    if _so(e.get("nhom_thu_tu"), 0) is not None:
        out["nhom_thu_tu"] = e["nhom_thu_tu"]
    return out


def _nhan_mot_run(app, dv, sid, login, ctx, run) -> dict:
    ma, goc = ctx["phap_nhan_ma"], dv.cau_hinh.goc_tai
    rel = run.get("run_rel")
    m = RE_RUN_REL.fullmatch(rel) if isinstance(rel, str) else None
    base = {"run_rel": rel, "ky": run.get("ky"), "chieu": run.get("chieu")}
    if m is None or m.group(1) != ma or m.group(4) != ctx["run_id"]:
        return {**base, "loi": {"ma": "M2_00E_RUN_REL_SAI", "thong_bao": "Thư mục run không thuộc lần tải này."}}
    try:
        thu_muc = kiem_khong_reparse(goc.joinpath(*rel.split("/")), la_thu_muc=True)
        ke_hoach = lap_ke_hoach_nhan(thu_muc, ma_phap_nhan=ma, goc_hoi_cuu_tin_cay=dv.goc_hoi_cuu_tin_cay)  # đọc/băm tệp NGOÀI khóa app
        with app.mutation_lock:
            kq = nhan_vao_k2(ke_hoach, app.m2(), actor=login, source_instance=ctx["source_instance"], scope_ref=ctx["scope_ref"])
    except DataError as exc:
        return {**base, "loi": {"ma": _ma(exc.code) or "UNSPECIFIED", "thong_bao": str(exc)}}
    return {**base, "nguon": ke_hoach["nguon"], "coverage": ke_hoach["coverage"], "so_muc": len(ke_hoach["muc"]),
            "ket_qua": [{"item_ordinal": it.get("item_ordinal"), "trang_thai": it.get("trang_thai"), "ly_do": it.get("ly_do"),
                         "thong_bao": an_toan(it["thong_bao"], 200) if isinstance(it.get("thong_bao"), str) else None,
                         "lap_lai": it.get("lap_lai") is True, "items": [{"classification": x.get("classification"), "phien_ban_moi": x.get("phien_ban_moi") is True}
                                                                         for x in it.get("items", [])]} for it in kq["ket_qua"]],
            "ngoai_le": [_ngoai_le_sach(e) for e in kq["ngoai_le"]], "so_chua_ro_nguon": len(kq["chua_ro_nguon"]),
            "khoang_thieu_k2": [k for k in kq["khoang_thieu_k2"] if _ma(k)]}


def tom_tat_manifest(m: dict, run_rel: str) -> dict:
    """Manifest đã qua `doc_manifest` → số đếm + nhóm + lỗi + đo đăng nhập. KHÔNG trả danh sách hóa đơn, MST, đường dẫn tuyệt đối, hash tệp."""
    dn = m["dang_nhap"]
    return {"phien_ban": PHIEN_BAN, "run_rel": run_rel, "nguon": m["nguon"], "run_id": m["run_id"], "ky": m["ky"], "chieu": m["chieu"], "trang_thai": m["trang_thai"],
            "bat_dau": m["bat_dau"], "ket_thuc": m["ket_thuc"], "phien_ban_bo_tai": an_toan(m["phien_ban_bo_tai"], 80),
            "tong": {k: m["tong"].get(k) for k in ("tong_hd", "xml_ok", "khong_xml_goc", "xml_loi", "xml_khong_yeu_cau", "pdf_ok", "pdf_loi", "bang_ke_trang_thai")},
            "co_bang_ke": isinstance(m["tong"].get("bang_ke"), dict),
            "dang_nhap": {k: dn[k] for k in ("captcha_da_go", "token_tai_su_dung", "thoi_gian_cho_dang_nhap_giay") if isinstance(dn.get(k), dict)},
            "nhom": [{"thu_tu": g.get("thu_tu"), "scope": an_toan(g.get("scope", ""), 40), "ttxly": g.get("ttxly"), "trang_thai": _ma(g.get("trang_thai")),
                      "so_ban_ghi": g.get("so_ban_ghi"), "loi": loi_sach(g["loi"]) if g.get("loi") else None} for g in m["nhom"]],
            "loi_chung": [loi_sach(e) for e in m["loi_chung"]], "ly_do_partial": [x for x in m["ly_do_partial"] if _ma(x)]}


# ---------------------------------------------------------------------------------------------- HTTP
def la_route(post: bool, path: str) -> bool:
    return path == TIEN_TO or path.startswith(TIEN_TO + "/")


def _q(query: dict, cho_phep, bat_buoc=()):
    la = sorted(set(query) - set(cho_phep))
    if la:
        raise DataError("M2_YEU_CAU_SAI", "Tham số không hợp lệ: " + ", ".join(la[:5]))
    out = {}
    for k in cho_phep:
        v = query.get(k)
        if v is None:
            if k in bat_buoc:
                raise DataError("M2_YEU_CAU_SAI", f"Thiếu tham số {k}.")
            continue
        if len(v) != 1 or not v[0]:
            raise DataError("M2_YEU_CAU_SAI", f"Tham số {k} phải có đúng một giá trị.")
        out[k] = v[0]
    return out


def _run(v) -> str:
    if not isinstance(v, str) or not RE_HANDLE.fullmatch(v):
        raise DataError("M2_00B_RUN_HANDLE", "Mã lần tải không hợp lệ.")
    return v


def _than_lenh(body: dict, cho_phep) -> dict:
    cam = sorted(k for k in body if k in KHONG_NHAN)
    if cam:
        raise DataError("M2_CLIENT_AUTHORITY", "Danh tính, pháp nhân, hồ sơ đăng nhập, đường dẫn, cổng, mật khẩu và captcha do máy chủ xác định; không nhận từ trình duyệt.")
    la = sorted(k for k in body if k not in cho_phep)
    if la:
        raise DataError("M2_YEU_CAU_SAI", "Yêu cầu có trường ngoài phạm vi: " + ", ".join(la[:5]))
    return body


def lua_chon_tu_body(body: dict) -> dict:
    """Body bat-dau → đúng 9 khóa của điều phối (`khoa` → client_key). Kiểm hình dạng sâu do `kiem_lua_chon` của điều phối làm."""
    b = _than_lenh(body, CHON_BAT_DAU)
    thieu = sorted(CHON_BAT_DAU - set(b))
    if thieu:
        raise DataError("M2_YEU_CAU_SAI", "Thiếu: " + ", ".join(thieu))
    return {**{k: b[k] for k in CHON_BAT_DAU if k != "khoa"}, "client_key": b["khoa"]}


def _gui(h, status, body, headers=None):
    return h.send_content(status, body, headers=headers)


def _trang_thai(h, app, query):
    _q(query, ())
    with app.mutation_lock:
        sid, _, moi = app.crm_phien(h.crm_sid(), tao=True)
    cookie = {"Set-Cookie": f"{app.CRM_COOKIE}={sid}; Path=/; HttpOnly; SameSite=Strict"} if moi else None
    try:
        dv = dich_vu(app)
        muc = dv.profiles(sid)["muc"]
    except DataError as exc:
        if exc.code not in MA_CHUA_CAU_HINH:
            raise
        return _gui(h, 200, {"phien_ban": PHIEN_BAN, "cau_hinh": False, "ma": exc.code, "ly_do": str(exc), "goi_y": goi_y_ma(exc.code),
                             "bo_tai": {"san_sang": False, "trang_thai": None}, "muc": []}, cookie)
    return _gui(h, 200, {"phien_ban": PHIEN_BAN, "cau_hinh": True, "bo_tai": _bo_tai(dv), "muc": [
        {"source_instance": m["source_instance"], "scope_ref": m["scope_ref"], "company_key": m["company_key"], "phap_nhan_ma": m["phap_nhan_ma"],
         "san_sang": m["san_sang"] is True, "ly_do": m["ly_do"], "ly_do_vi": ly_do_profile(m["ly_do"])} for m in muc]}, cookie)


def _khoi_dong(h, app):
    _than_lenh(h.json_body(4096), ())
    dv = dich_vu(app)
    sid = h.crm_sid()
    if not dv.profiles(sid)["muc"]:  # phiên + quyền hiện hành TRƯỚC khi spawn Node
        raise DataError("KHONG_CO_QUYEN_TAI_CONG_THUE", "Vai hiện tại không có pháp nhân nào được tải từ cổng thuế.")
    dv.khoi_dong_neu_can()
    return _gui(h, 200, {"phien_ban": PHIEN_BAN, "bo_tai": _bo_tai(dv)})


def _bat_dau(h, app):
    sel = lua_chon_tu_body(h.json_body(16 * 1024))
    dv = dich_vu(app)
    return _gui(h, 200, lam_sach_run(dv.start(h.crm_sid(), sel)))


def _nhan(h, app):
    run = _run(_than_lenh(h.json_body(4096), {"run"}).get("run"))
    dv, sid = dich_vu(app), h.crm_sid()
    st = dv.status(sid, run)  # kiểm phiên + quyền hiện hành trước/sau IO Node; đây là nguồn danh sách run của biên nhận
    if st["trang_thai"] == "RUNNING":
        raise DataError("M2_00E_DANG_CHAY", "Bộ tải còn đang chạy — chờ xong rồi nhận vào M2.")
    kq = lam_sach_run(st).get("ket_qua")
    if not kq:
        raise DataError("M2_00E_CHUA_CO_KET_QUA", "Lần tải chưa có biên nhận để nhận vào M2.")
    ctx = dv.ngu_canh(sid, run)
    with app.mutation_lock:
        _, login, _ = app.crm_phien(sid)
    runs = [_nhan_mot_run(app, dv, sid, login, ctx, r) for r in kq["runs"]]
    tt = tom_tat_nhan(runs)
    nk = dv.ghi_nhat_ky(sid, run, "M2_00E_NHAN_KET_QUA", {"so_run": len(runs), "moi": tt["moi"], "doi_trang_thai": tt["doi_trang_thai"], "khong_ma": tt["khong_ma"], "loi": tt["loi"]})
    return _gui(h, 200, {"phien_ban": PHIEN_BAN, "run_handle": run, "trang_thai_tai": kq["trang_thai"], "tom_tat": tt, "runs": runs, "nhat_ky": nk})


def _manifest(h, app, query):
    q = _q(query, ("run", "run_rel"), ("run", "run_rel"))
    run, rel = _run(q["run"]), q["run_rel"]
    dv, sid = dich_vu(app), h.crm_sid()
    ctx = dv.ngu_canh(sid, run)
    m = RE_RUN_REL.fullmatch(rel)
    if m is None or m.group(1) != ctx["phap_nhan_ma"] or m.group(4) != ctx["run_id"]:
        raise DataError("M2_00B_RUN_REL_SAI", "Thư mục run không thuộc lần tải này.")
    dv.kiem_run(sid, run)
    thu_muc = kiem_khong_reparse(dv.cau_hinh.goc_tai.joinpath(*rel.split("/")), la_thu_muc=True)
    return _gui(h, 200, tom_tat_manifest(doc_manifest(thu_muc, goc_hoi_cuu_tin_cay=dv.goc_hoi_cuu_tin_cay), rel))


def _khung(ten, du_lieu, seq=None) -> bytes:
    id_ = f"id: {seq}\n" if seq is not None else ""
    return f"{id_}event: {ten}\ndata: {json.dumps(du_lieu, ensure_ascii=False, separators=(',', ':'))}\n\n".encode("utf-8")


def _su_kien(h, app, query):
    q = _q(query, ("run", "cursor"), ("run",))
    run = _run(q["run"])
    cursor = q.get("cursor", "0")
    if not cursor.isdigit() or len(cursor) > 9:
        raise DataError("M2_YEU_CAU_SAI", "Con trỏ sự kiện không hợp lệ.")
    dv, sid = dich_vu(app), h.crm_sid()
    dv.kiem_run(sid, run)  # lỗi trước khi mở luồng → JSON thường
    h.send_response(200)
    for k, v in {"Content-Type": "text/event-stream; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Connection": "close",
                 "Referrer-Policy": "no-referrer", "Cross-Origin-Resource-Policy": "same-origin",
                 "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'"}.items():
        h.send_header(k, v)
    h.end_headers()
    gen = dv.events(sid, run, int(cursor))
    try:
        h.wfile.write(b": open\n\n")
        h.wfile.flush()
        for ev in gen:
            if "ket_thuc" in ev:
                h.wfile.write(_khung("ket-thuc", {"ly_do": _ma(ev["ket_thuc"]) or "END"}))
                break
            sach = loc_su_kien(ev)
            if sach is not None:
                h.wfile.write(_khung("su-kien", sach, sach["seq"]))
            h.wfile.flush()
        h.wfile.flush()
    except DataError as exc:
        _, body = mo_ta_loi(exc)
        _ghi_cuoi(h, _khung("loi", body))
    except OSError:
        pass  # trình duyệt đóng luồng; Node/binding giữ nguyên, lần sau đọc tiếp từ con trỏ
    finally:
        gen.close()


def _ghi_cuoi(h, data: bytes):
    try:
        h.wfile.write(data)
        h.wfile.flush()
    except OSError:
        pass


def dieu_huong(h, app, post: bool, path: str, query: dict):
    """Một điểm vào cho route /api/m2/tai-hoa-don*. Lỗi → JSON {error, message, goi_y?} với HTTP 400/403/404/409/502/503; không lộ chi tiết nội bộ."""
    try:
        if app.is_that:
            raise DataError("THAT_UI", "Tải từ cổng thuế hiện chỉ có trong bản DEMO; kho thật chưa mở.")
        ten = path[len(TIEN_TO):].strip("/")
        if not post:
            if ten == "":
                return _trang_thai(h, app, query)
            if ten == "trang-thai":
                run = _run(_q(query, ("run",), ("run",))["run"])
                return _gui(h, 200, lam_sach_run(dich_vu(app).status(h.crm_sid(), run)))
            if ten == "su-kien":
                return _su_kien(h, app, query)
            if ten == "manifest":
                return _manifest(h, app, query)
        else:
            if ten == "khoi-dong":
                return _khoi_dong(h, app)
            if ten == "bat-dau":
                return _bat_dau(h, app)
            if ten == "nhan":
                return _nhan(h, app)
            if ten in ("doi-soat", "mo-thu-muc"):
                body = _than_lenh(h.json_body(4096), {"run"} if ten == "doi-soat" else {"run", "run_rel"})
                run, dv, sid = _run(body.get("run")), dich_vu(app), h.crm_sid()
                if ten == "doi-soat":
                    return _gui(h, 200, lam_sach_run(dv.reconcile(sid, run)))
                dv.mo_thu_muc(sid, run, body.get("run_rel"))
                return _gui(h, 200, {"phien_ban": PHIEN_BAN, "da_mo": True})
        return _gui(h, 404, {"error": "NOT_FOUND", "message": "Không tìm thấy chức năng này."})
    except DataError as exc:
        status, body = mo_ta_loi(exc)
        return _gui(h, status, body)
    except (ValueError, TypeError, KeyError, RecursionError):
        return _gui(h, 400, {"error": "INVALID_REQUEST", "message": "Thông tin gửi lên không hợp lệ; chưa xử lý."})
    except OSError:
        return _gui(h, 500, {"error": "LOCAL_STORAGE_ERROR", "message": "Không đọc được thư mục tải trên máy. Dữ liệu đã tải vẫn được giữ."})
