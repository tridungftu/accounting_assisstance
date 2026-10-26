"""XS-3b: bọc cổng dùng chung; không đọc/ghi bảng của module.

Chỉ dùng CongOCR/CongAI được tiêm, không tạo cổng, thư mục, sổ trang,
thư viện, kết nối hoặc mô hình thứ hai. Cổng AI tự quyết Local/Cloud và
Mask v2; engine không định tuyến lại. Không ghi log nội dung hay ngoại lệ.
Các bảng công khai chỉ ánh xạ lỗi đã biết; lỗi ngoài bảng được ném lại.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from types import MappingProxyType

from kho_tri_thuc.ha_tang.cong_ocr import CongOCR
from kho_tri_thuc.ha_tang.danh_ba_engine import DanhBaEngine
from kho_tri_thuc.ha_tang.engine import (
    Engine, KhaiBaoEngine, KetQuaXuLy, TrangThaiEngine,
)
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.tri_thuc.ai_cuc_bo import LocalAIUnavailable
from kho_tri_thuc.tri_thuc.cong_ai import (
    CloudLoi, CongAI, KetQuaAI, MaskKhongGui, YeuCauAI,
)


@dataclass(frozen=True)
class DauVaoOCR:
    """Bytes và đuôi nguyên vẹn; cổng kiểm định dạng, chuẩn hóa đuôi tệp."""

    raw: bytes
    duoi: str


# OCR dùng chung một lớp DataError, nên khóa phải gồm cả lớp và code.
# Không bắt DataError mã lạ hoặc lớp con chưa được khai báo trong bảng.
BANG_ANH_XA_LOI_OCR = MappingProxyType({
    (DataError, "OCR_HET_HAN_MUC"): (
        TrangThaiEngine.CHO, "OCR_HET_HAN_MUC", "Chờ hạn mức trang nhận dạng."),
    (DataError, "OCR_HUY"): (
        TrangThaiEngine.CHO, "OCR_DA_HUY", "Yêu cầu nhận dạng đã được hủy."),
    (DataError, "OCR_QUA_GIO"): (
        TrangThaiEngine.CHO, "OCR_QUA_GIO", "Chưa nhận được kết quả trong thời gian chờ."),
    (DataError, "OCR_KHONG_NHAN"): (
        TrangThaiEngine.CHO, "OCR_KHONG_NHAN", "Cổng nhận dạng chưa nhận tài liệu."),
    (DataError, "OCR_DINH_DANG"): (
        TrangThaiEngine.LOI, "OCR_DINH_DANG", "Định dạng tài liệu chưa được hỗ trợ."),
    (DataError, "OCR_LOI_ABBYY"): (
        TrangThaiEngine.LOI, "OCR_LOI_ABBYY", "Cổng nhận dạng không hoàn tất xử lý."),
})


# CongAI hiện chuyển các lỗi này thành KetQuaAI. Bảng vẫn giữ phân biệt
# lớp nếu cổng được tiêm trả ngoại lệ công khai, không bắt ValueError chung.
BANG_ANH_XA_NGOAI_LE_AI = MappingProxyType({
    LocalAIUnavailable: (
        TrangThaiEngine.CHO, "AI_LOCAL_CHUA_SAN", "Local AI chưa sẵn sàng xử lý."),
    MaskKhongGui: (
        TrangThaiEngine.CHO, "AI_MASK_KHONG_GUI", "Cổng Mask chưa cho phép gửi yêu cầu."),
    CloudLoi: (
        TrangThaiEngine.LOI, "AI_CLOUD_LOI", "Cổng AI không hoàn tất xử lý Cloud."),
})


# Chỉ dùng khi không có trường kết quả. Có kết quả Local/Cloud dùng được
# vẫn là XONG, kể cả khi một đường khác bị lỗi. Giữ nguyên toàn bộ DTO.
# Ưu tiên LOI trước CHO, rồi thứ tự bảng; không phụ thuộc thứ tự mã cổng.
# Không coi các mã đánh giá chất lượng/trích dẫn là lỗi vận hành của cổng.
BANG_ANH_XA_LY_DO_AI = MappingProxyType({
    "LOCAL_LOI": (
        TrangThaiEngine.LOI, "AI_LOCAL_LOI", "Local AI không hoàn tất xử lý."),
    "LOCAL_KHONG_CHAY": (
        TrangThaiEngine.CHO, "AI_LOCAL_CHUA_SAN", "Local AI chưa sẵn sàng xử lý."),
    "LOCAL_TAT": (
        TrangThaiEngine.CHO, "AI_LOCAL_TAT", "Local AI chưa được bật để xử lý."),
    "CLOUD_TAT": (
        TrangThaiEngine.CHO, "AI_CLOUD_TAT", "Đường Cloud chưa được bật để xử lý."),
    "LOAI_VIEC_KHONG_DUNG_CLOUD": (
        TrangThaiEngine.CHO, "AI_LOAI_VIEC_KHONG_DUNG_CLOUD", "Loại việc này chỉ được xử lý bằng Local AI."),
    "CAI_DAT_CLOUD_LOI": (
        TrangThaiEngine.LOI, "AI_CAI_DAT_CLOUD_LOI", "Cài đặt Cloud chưa hợp lệ."),
    "CHUA_CO_KHOA_API": (
        TrangThaiEngine.CHO, "AI_CHUA_CO_KHOA_API", "Chờ cấu hình khóa truy cập Cloud."),
    "CHUA_CO_KHOA_MASK": (
        TrangThaiEngine.CHO, "AI_CHUA_CO_KHOA_MASK", "Chờ cấu hình khóa truy cập Mask."),
    "XML_HOA_DON_THO": (
        TrangThaiEngine.LOI, "AI_XML_HOA_DON_THO", "Cổng AI không gửi XML hóa đơn thô ra Cloud."),
    "QUA_NHIEU_DINH_DANH": (
        TrangThaiEngine.LOI, "AI_QUA_NHIEU_DINH_DANH", "Số định danh vượt giới hạn của cổng AI."),
    "MASK_KHONG_CHAY": (
        TrangThaiEngine.CHO, "AI_MASK_KHONG_CHAY", "Mask chưa sẵn sàng xử lý."),
    "MASK_DANH_MUC_KHOA": (
        TrangThaiEngine.CHO, "AI_MASK_DANH_MUC_KHOA", "Chờ mở danh mục của Mask."),
    "MASK_DANH_MUC_CHUA_CO": (
        TrangThaiEngine.CHO, "AI_MASK_DANH_MUC_CHUA_CO", "Chờ danh mục bí danh của Mask."),
    "MASK_CON_SOT": (
        TrangThaiEngine.LOI, "AI_MASK_CON_SOT", "Mask chưa che hết định danh của yêu cầu."),
    "MASK_KHONG_CHO_GUI": (
        TrangThaiEngine.CHO, "AI_MASK_KHONG_CHO_GUI", "Mask chưa cho phép gửi yêu cầu."),
    "MASK_PHAN_HOI_LOI": (
        TrangThaiEngine.LOI, "AI_MASK_PHAN_HOI_LOI", "Mask trả kết quả chưa hợp lệ."),
    "MASK_API_CHUA_BAT": (
        TrangThaiEngine.CHO, "AI_MASK_API_CHUA_BAT", "Chờ bật chế độ API của Mask."),
    "MASK_SAI_KHOA": (
        TrangThaiEngine.LOI, "AI_MASK_SAI_KHOA", "Khóa truy cập Mask chưa hợp lệ."),
    "CON_SOT_DINH_DANH": (
        TrangThaiEngine.LOI, "AI_CON_SOT_DINH_DANH", "Cổng AI phát hiện định danh chưa được che."),
    "CLOUD_KHONG_KET_NOI": (
        TrangThaiEngine.CHO, "AI_CLOUD_KHONG_KET_NOI", "Chưa kết nối được Cloud qua cổng AI."),
    "CLOUD_TU_CHOI": (
        TrangThaiEngine.LOI, "AI_CLOUD_TU_CHOI", "Cloud từ chối xử lý yêu cầu."),
    "CLOUD_LOI": (
        TrangThaiEngine.LOI, "AI_CLOUD_LOI", "Cổng AI không hoàn tất xử lý Cloud."),
    "MASK_MO_CHE_LOI": (
        TrangThaiEngine.LOI, "AI_MASK_MO_CHE_LOI", "Mask không mở che được kết quả Cloud."),
})


# Cổng giữ mã HTTP trong DTO thay vì ném CloudLoi/MaskKhongGui ra ngoài.
# Chỉ nhận đúng mẫu mã do cổng tạo, không bắt mọi tiền tố CLOUD_/MASK_.
BANG_ANH_XA_MAU_LY_DO_AI = MappingProxyType({
    r"CLOUD_HTTP_[1-5][0-9]{2}": BANG_ANH_XA_NGOAI_LE_AI[CloudLoi],
    r"MASK_HTTP_[1-5][0-9]{2}": BANG_ANH_XA_NGOAI_LE_AI[MaskKhongGui],
})


class EngineOCR(Engine):
    """E-OCR/v1: dùng đúng cổng/sổ trang đã cấp; không truy cập bảng module."""

    def __init__(self, cong_ocr: CongOCR) -> None:
        super().__init__(KhaiBaoEngine("E-OCR", "v1", DauVaoOCR, bytes))
        self._cong = cong_ocr

    def xu_ly(self, dau_vao: DauVaoOCR) -> KetQuaXuLy:
        try:
            docx = self._cong.ocr(dau_vao.raw, dau_vao.duoi)
        except DataError as exc:
            anh_xa = BANG_ANH_XA_LOI_OCR.get((type(exc), exc.code))
            if anh_xa is None:
                raise
            return KetQuaXuLy(*anh_xa)
        return KetQuaXuLy(TrangThaiEngine.XONG, "OCR_XONG",
                          "Đã nhận kết quả nhận dạng.", docx)


class EngineAI(Engine):
    """E-AI/v1: giữ YeuCauAI/KetQuaAI, không chọn đường hay truy cập bảng.

    KetQuaAI là dataclass chứa dữ liệu thuần được hash_du_lieu hỗ trợ,
    kể cả dict TruongAI. Hash bao gồm mã yêu cầu do cổng cấp; hai lượt gọi
    cổng có mã yêu cầu khác nhau có thể cho hash đầu ra khác nhau.
    """

    def __init__(self, cong_ai: CongAI) -> None:
        super().__init__(KhaiBaoEngine("E-AI", "v1", YeuCauAI, KetQuaAI))
        self._cong = cong_ai

    def xu_ly(self, dau_vao: YeuCauAI) -> KetQuaXuLy:
        try:
            ket_qua = self._cong.goi(dau_vao)
        except (LocalAIUnavailable, MaskKhongGui, CloudLoi) as exc:
            anh_xa = BANG_ANH_XA_NGOAI_LE_AI.get(type(exc))
            if anh_xa is None:
                raise
            return KetQuaXuLy(*anh_xa)
        # Sai hợp đồng cổng là lỗi lập trình, không chuyển thành LOI.
        if not isinstance(ket_qua, KetQuaAI):
            raise ValueError("Cổng AI phải trả KetQuaAI.")
        if not ket_qua.co_ket_qua:
            cac_anh_xa = [anh_xa for ma, anh_xa in BANG_ANH_XA_LY_DO_AI.items()
                          if ma in ket_qua.ly_do]
            cac_anh_xa.extend(
                anh_xa for mau, anh_xa in BANG_ANH_XA_MAU_LY_DO_AI.items()
                if any(re.fullmatch(mau, ma) for ma in ket_qua.ly_do)
            )
            for trang_thai in (TrangThaiEngine.LOI, TrangThaiEngine.CHO):
                for anh_xa in cac_anh_xa:
                    if anh_xa[0] == trang_thai:
                        return KetQuaXuLy(*anh_xa, du_lieu=ket_qua)
        return KetQuaXuLy(TrangThaiEngine.XONG, "AI_XONG",
                          "Đã nhận kết quả từ cổng AI.", ket_qua)


def dang_ky_engine_cong(danh_ba: DanhBaEngine, *,
                      cong_ocr: CongOCR | None = None,
                      cong_ai: CongAI | None = None) -> None:
    """Chỉ đăng ký cổng đã cấp; danh bạ hiện có tự từ chối mã/version trùng."""
    if cong_ocr is not None:
        danh_ba.dang_ky(EngineOCR(cong_ocr))
    if cong_ai is not None:
        danh_ba.dang_ky(EngineAI(cong_ai))
