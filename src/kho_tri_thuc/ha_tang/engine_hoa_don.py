"""XS-3d: E-HOADON/v1 bọc riêng nhánh đọc XML/ZIP có sẵn.

Không đọc/ghi bảng M2 hay module nào; không filesystem, mạng, cổng thuế,
thư viện hoặc kết nối mới. Chưa nối M2/M3, chưa bọc nhánh tải M2-00.
Caller cấp bytes/context đã được phép đọc. Tên tệp chỉ là metadata;
``dinh_dang`` tường minh, không đoán định dạng hay sửa dữ liệu nguồn.
Đầu ra là asdict của TOÀN BỘ DTO reader: giữ bytes, Decimal, tuple, mọi
trường hóa đơn, coverage, issues, locator và hash; không dùng ra_json vì
hàm đó bỏ raw bytes. Các kiểu thuần này được hash_du_lieu hỗ trợ sẵn.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from lzma import LZMAError
from types import MappingProxyType

from kho_tri_thuc.ha_tang.danh_ba_engine import DanhBaEngine
from kho_tri_thuc.ha_tang.engine import Engine, KhaiBaoEngine, KetQuaXuLy, TrangThaiEngine
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.nguon.hoa_don_xml import (
    InvoiceReadContext, InvoiceReadResult, InvoiceZipReadResult,
    doc_goi_hoa_don_zip, doc_hoa_don_xml,
)


@dataclass(frozen=True)
class DauVaoHoaDon:
    """XML nhận một context/None; ZIP nhận tuple contexts/None (= tuple rỗng).

    Thiếu context được reader đánh giá; wrapper không tự dựng context.
    Chỉ nhận bytes theo hợp đồng engine, không đường dẫn hay file object.
    """

    raw: bytes
    context: InvoiceReadContext | tuple[InvoiceReadContext, ...] | None = None
    ten_tep: str | None = None
    dinh_dang: str = "XML"


# Chỉ các lý do reader dùng để chặn định danh vì THIẾU context. Không biến
# RAW_REF_NOT_BOUND (không gate content), lỗi dòng hay context mâu thuẫn thành CHO.
_THIEU_CONTEXT = frozenset({
    "CONTEXT_ABSENT", "PROFILE_DOCUMENT_NOT_BOUND", "IDENTITY_PROFILE_ABSENT", "COMPANY_ABSENT",
})
_LOI_GOI = frozenset({"ZIP_MALFORMED", "ZIP_TOO_LARGE", "ZIP_TOO_MANY_ENTRIES"})
_DA_DOC = "Đã đọc hóa đơn bằng bộ đọc hiện có."
_CHO_CONTEXT = "Chờ ngữ cảnh đọc hóa đơn còn thiếu theo bộ đọc."
_KHONG_DOC_DUOC = "Bộ đọc không đọc được tệp hóa đơn trong phạm vi hỗ trợ."


# None ở cột mã: DataError đã có mã ổn định, giữ nguyên exc.code.
# XML parse, ZIP hỏng/CRC, giải mã tên ZIP đã thành issues trong reader.
# ZIP dùng LZMA có thể để lọt LZMAError khi dữ liệu nén hỏng.
ANH_XA_NGOAI_LE_HOA_DON = MappingProxyType({
    DataError: (TrangThaiEngine.LOI, None, "Đầu vào bộ đọc hóa đơn chưa hợp lệ."),
    LZMAError: (TrangThaiEngine.LOI, "HOADON_ZIP_LZMA_HONG",
                "Dữ liệu nén trong gói hóa đơn không hợp lệ."),
})


def _trang_thai_xml(result: InvoiceReadResult) -> tuple[TrangThaiEngine, str, str]:
    # shape phản ánh khả năng đọc cấu trúc; issues của dòng/tiền vẫn thuộc XONG.
    if result.shape != "SUPPORTED_SUBSET":
        ma = result.issues[0].code if result.issues else "XML_UNREADABLE"
        return TrangThaiEngine.LOI, ma, _KHONG_DOC_DUOC
    for ma in result.candidate_reasons:
        if ma in _THIEU_CONTEXT:
            return TrangThaiEngine.CHO, ma, _CHO_CONTEXT
    return TrangThaiEngine.XONG, "DA_DOC_HOA_DON", _DA_DOC


def _trang_thai_zip(result: InvoiceZipReadResult) -> tuple[TrangThaiEngine, str, str]:
    for issue in result.issues:
        if issue.code in _LOI_GOI:
            return TrangThaiEngine.LOI, issue.code, _KHONG_DOC_DUOC
    cho = None
    for entry in result.entries:
        if entry.state == "READ_ERROR":
            ma = entry.issues[0].code if entry.issues else "ZIP_MEMBER_READ_ERROR"
            return TrangThaiEngine.LOI, ma, _KHONG_DOC_DUOC
        if entry.result is not None:
            trang_thai = _trang_thai_xml(entry.result)
            if trang_thai[0] == TrangThaiEngine.LOI:
                return trang_thai
            if trang_thai[0] == TrangThaiEngine.CHO and cho is None:
                cho = trang_thai
    return cho or (TrangThaiEngine.XONG, "DA_DOC_HOA_DON", _DA_DOC)


class EngineHoaDon(Engine):
    """Một wrapper dùng chung, thuần; không đọc/ghi bảng hay nối module."""

    def __init__(self) -> None:
        super().__init__(KhaiBaoEngine("E-HOADON", "v1", DauVaoHoaDon, dict))

    def xu_ly(self, dau_vao: DauVaoHoaDon) -> KetQuaXuLy:
        if dau_vao.dinh_dang not in ("XML", "ZIP"):
            return KetQuaXuLy(TrangThaiEngine.LOI, "DINH_DANG_KHONG_HO_TRO",
                              "Định dạng đầu vào phải là XML hoặc ZIP.")
        try:
            if dau_vao.dinh_dang == "XML":
                result = doc_hoa_don_xml(dau_vao.raw, dau_vao.context, artifact_name=dau_vao.ten_tep)
            else:
                contexts = () if dau_vao.context is None else dau_vao.context
                result = doc_goi_hoa_don_zip(dau_vao.raw, contexts, archive_name=dau_vao.ten_tep)
        except tuple(ANH_XA_NGOAI_LE_HOA_DON) as exc:
            # Chỉ ánh xạ đúng lớp đã công bố; lớp con chưa biết cũng nổi lên.
            if type(exc) not in ANH_XA_NGOAI_LE_HOA_DON:
                raise
            trang_thai, ma, ly_do = ANH_XA_NGOAI_LE_HOA_DON[type(exc)]
            return KetQuaXuLy(trang_thai, exc.code if ma is None else ma, ly_do)
        trang_thai, ma, ly_do = (_trang_thai_xml(result) if dau_vao.dinh_dang == "XML"
                                else _trang_thai_zip(result))
        return KetQuaXuLy(trang_thai, ma, ly_do, asdict(result))


def dang_ky_engine_hoa_don(danh_ba: DanhBaEngine) -> EngineHoaDon:
    """Đăng ký riêng lát XS-3d; danh bạ hiện có chịu trách nhiệm từ chối trùng."""
    engine = EngineHoaDon()
    danh_ba.dang_ky(engine)
    return engine
