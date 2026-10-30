"""HD-1: lớp bọc thuần cho profile XML DEMO, không phải bộ kiểm hợp lệ thuế.

CD-036 — dùng lại nguyên: nguon/hoa_don_xml.py (parser, DTO, Decimal, hash,
context, coverage); bọc: ha_tang/engine_hoa_don.py (_trang_thai_xml và bảng
ngoại lệ); viết mới: phép chiếu hoa_don.v1 theo CONTRACT-DU-LIEU.md §10.
Không sửa/chép lõi parser, không SDK, I/O, CSDL, COM, OCR hay mạng.

Core cấp ID tệp XML và ID tệp JSON chi tiết riêng, rồi lưu chi tiết bằng
hoa_don_xml.ra_json(chi_tiet_nguon). DTO Python vẫn giữ raw bytes/Decimal;
context đầu vào được giữ riêng, không dùng làm field nguồn thay XML.
ZIP trả NGUYÊN DTO thư viện; chưa có schema báo cáo gói, không tạo vỏ JSON
hay công bố capability đã chuẩn hóa. chieu_hoa_don dùng được cho từng entry.
Không phát hoa_don_da_nhan.v1: sự kiện thuộc tiếp nhận nghiệp vụ, còn chờ
chính sách theo CONTRACT-NGHIEP-VU.md, không thuộc bộ đọc kỹ thuật này.
"""

from __future__ import annotations

from dataclasses import dataclass
from lzma import LZMAError
import re
from uuid import UUID

from kho_tri_thuc.ha_tang.engine import TrangThaiEngine
from kho_tri_thuc.ha_tang.engine_hoa_don import (
    ANH_XA_NGOAI_LE_HOA_DON, _trang_thai_xml,
)
from kho_tri_thuc.ha_tang.primitives import DataError, date_iso
from kho_tri_thuc.nguon.hoa_don_xml import (
    DecimalFact, InvoiceField, InvoiceIssue, InvoiceReadContext,
    InvoiceReadResult, InvoiceZipReadResult, _identity_text,
    doc_goi_hoa_don_zip, doc_hoa_don_xml,
)


MAX_ZIP_BYTES_CORE = 20 * 1024 * 1024
_TIEN = re.compile(r"-?(0|[1-9][0-9]{0,17})(\.[0-9]{1,6})?")
_DAU = {
    "mau_so": "KHMSHDon", "ky_hieu": "KHHDon", "so_hoa_don": "SHDon",
    "ngay_lap": "NLap", "don_vi_tien": "DVTTe",
    "ma_so_thue_ban": "NBan/MST", "ma_so_thue_mua": "NMua/MST",
}


@dataclass(frozen=True)
class KetQuaDocHoaDon:
    """Kết quả trong RAM; chỉ hoa_don là payload hoa_don.v1 để trao đổi."""

    hoa_don: dict
    chi_tiet_nguon: InvoiceReadResult
    context: InvoiceReadContext | None
    trang_thai: TrangThaiEngine
    ma: str
    ly_do: str


def _id(value: str, name: str) -> None:
    # Kiểm ID nhưng không chuẩn hóa/chuyển sang UUID làm mất chuỗi Core cấp.
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value,
    ):
        raise DataError("HOADON_ID_INVALID", "ID tệp phải là UUID do Core cấp.", name)
    UUID(value)


def _text(field: InvoiceField | None) -> str | None:
    value = None if field is None else field.duy_nhat
    return value.lexeme if value is not None and value.state == "TEXT" else None


def _decimal(fact: DecimalFact) -> dict:
    return {"trang_thai": fact.state, "gia_tri": fact.exact_text}


def chieu_hoa_don(
    result: InvoiceReadResult, *, tep_xml_id: str,
    chi_tiet_nguon_tep_id: str, revision: int = 1,
) -> dict:
    """Chiếu một DTO (kể cả entry ZIP) sang contract, không tính lại hash/tổng.

    Mọi occurrence, quan hệ, thành phần thuế và crosswalk còn nguyên trong
    result; caller lưu chúng vào chi_tiet_nguon_tep_id trước khi công bố.
    """
    _id(tep_xml_id, "tep_xml_id")
    _id(chi_tiet_nguon_tep_id, "chi_tiet_nguon_tep_id")
    if tep_xml_id.lower() == chi_tiet_nguon_tep_id.lower():
        raise DataError("HOADON_FILE_REF_CONFLICT", "XML và chi tiết nguồn cần hai tệp riêng.")
    if type(revision) is not int or revision < 1:
        raise DataError("HOADON_REVISION_INVALID", "Revision phải là số nguyên dương.")

    issues = list(dict.fromkeys((*result.issues, *result.money.issues, *result.relations.issues)))

    def issue(code, message, locator):
        value = InvoiceIssue(code, message, locator, "ERROR")
        if value not in issues:
            issues.append(value)

    header = {f.name: f for f in result.header_fields}
    dau = {}
    for name, tag in _DAU.items():
        field = header.get(tag)
        text = _text(field)
        if field is not None and any(
            # Dấu # cuối ngăn path XML; tên entry ZIP có thể chứa #.
            i.code == "STRUCTURE_DUPLICATE" and field.locator.startswith(i.locator.rsplit("#", 1)[-1] + "/")
            for i in result.issues
        ):
            text = None
        if text is not None:
            valid = True
            if name == "ngay_lap":
                try:
                    date_iso(text)
                except DataError:
                    valid = False
            elif name == "don_vi_tien":
                valid = re.fullmatch(r"[A-Z]{3}", text) is not None
            elif name == "so_hoa_don":
                valid = re.fullmatch(r"[0-9]+", text) is not None
            else:
                valid = _identity_text(field.duy_nhat) is not None
            if not valid:
                issue("HOADON_HEADER_INVALID", "Field đầu hóa đơn không hợp lệ; giữ chi tiết nguồn.", field.locator)
                text = None
        dau[name] = text

    def tien(fact, locator):
        if fact.exact_value is None:
            return None
        # format Decimal không làm tròn và không phụ thuộc precision hiện hành.
        text = format(fact.exact_value, "f")
        if not _TIEN.fullmatch(text):
            issue("HOADON_MONEY_OVER_DOMAIN", "Tiền nguồn vượt miền 18/6; không làm tròn.", locator)
            return None
        currency = dau["don_vi_tien"]
        return None if currency is None else {"gia_tri": text, "don_vi_tien": currency}

    dong = []
    for line in result.lines:
        field = line.field("TSuat")
        value = field.duy_nhat
        if value is None:
            tax = {"trang_thai": "KHONG_HOP_LE", "gia_tri_nguon": None}
            issue("HOADON_TAX_RATE_AMBIGUOUS", "Thuế suất không có occurrence duy nhất rõ ràng.", field.locator)
        else:
            tax = {"trang_thai": value.state,
                   "gia_tri_nguon": value.lexeme if value.state == "TEXT" else None}
        dong.append({
            "thu_tu_nguon": line.source_ordinal, "dinh_vi": line.source_locator,
            "tinh_chat": line.nature, "don_vi": _text(line.field("DVTinh")),
            "so_luong": _decimal(line.quantity), "don_gia": _decimal(line.unit_price),
            "thanh_tien": _decimal(line.source_amount),
            "tien_chuan": tien(line.source_amount, line.field("ThTien").locator),
            "thue_suat": tax,
        })

    totals = []
    money_fields = {f.name: f for f in result.money.fields}
    for name, tag, fact in (
        ("truoc_thue", "TgTCThue", result.money.net_amount),
        ("thue", "TgTThue", result.money.tax_amount),
        ("khong_chiu_thue", "TGTKCThue", result.money.non_taxable_amount),
        ("thanh_toan", "TgTTTBSo", result.money.total_amount),
    ):
        if fact.state == "ABSENT":
            continue
        field = money_fields[tag]
        locator = field.locator
        if name == "khong_chiu_thue" and field.duy_nhat is not None and field.duy_nhat.state == "ABSENT":
            # Reader chỉ dùng đúng một dòng KCT tường minh, không cộng để bù.
            components = [c for c in result.money.tax_components if c.rate == "KCT"]
            if len(components) == 1:
                locator = next(f.locator for f in components[0].fields if f.name == "ThTien")
        totals.append({"ma": name, "dinh_vi": locator,
                       "gia_tri_nguon": _decimal(fact), "tien_chuan": tien(fact, locator)})

    return {
        "contract": "hoa_don.v1", "phien_ban": "1.0.0", "revision": revision,
        "nguon_tep_ids": [tep_xml_id], "tep_xml_id": tep_xml_id,
        "chi_tiet_nguon_tep_id": chi_tiet_nguon_tep_id,
        "profile_ref": result.source_profile_ref,
        "profile_document_sha256": result.profile_document_sha256,
        "profile_payload_sha256": result.profile_payload_sha256,
        "dang_cau_truc": result.shape,
        "dinh_danh_nguon": None if result.canonical_identity is None else list(result.canonical_identity),
        "ma_bam_noi_dung": result.semantic_digest, "dau_hoa_don": dau,
        "dong": dong, "tong_tien": totals,
        "van_de": [{"ma": i.code, "thong_diep": i.message, "dinh_vi": i.locator, "muc": i.severity}
                   for i in issues],
        "ly_do_ung_vien": list(result.candidate_reasons),
        "trang_thai_thue": result.native_fiscal_status,
        "ghi_nhan_nghiep_vu": result.business_promotion,
    }


def doc_xml(
    raw: bytes, context: InvoiceReadContext | None = None, *, tep_xml_id: str,
    chi_tiet_nguon_tep_id: str, revision: int = 1, artifact_name: str | None = None,
) -> KetQuaDocHoaDon:
    """Đọc bytes do Core cấp; lỗi nguồn giữ DTO/mã, lỗi tham số raise DataError."""
    result = doc_hoa_don_xml(raw, context, artifact_name=artifact_name)
    payload = chieu_hoa_don(result, tep_xml_id=tep_xml_id,
                           chi_tiet_nguon_tep_id=chi_tiet_nguon_tep_id, revision=revision)
    state, code, reason = _trang_thai_xml(result)
    # Context mâu thuẫn là lỗi kể cả khi đồng thời thiếu context (CHO).
    # Giữ ưu tiên lỗi không đọc được cấu trúc từ wrapper cũ.
    if state in (TrangThaiEngine.XONG, TrangThaiEngine.CHO):
        for invalid in ("PROFILE_REF_MISMATCH", "PROFILE_DOCUMENT_MISMATCH",
                        "PROFILE_PAYLOAD_CONFUSED", "IDENTITY_PROFILE_UNSUPPORTED", "RAW_REF_MISMATCH"):
            if invalid in result.candidate_reasons:
                state, code, reason = (TrangThaiEngine.LOI, invalid,
                                       "Context không khớp profile hoặc tệp nguồn; giữ kết quả để kiểm tra.")
                break
    return KetQuaDocHoaDon(payload, result, context, state, code, reason)


def doc_zip(
    raw: bytes, contexts: tuple[InvoiceReadContext, ...] = (), *, archive_name: str | None = None,
) -> InvoiceZipReadResult:
    """Giữ DTO ZIP, entry/CRC/partial/issues; báo cáo contract gói còn CHỜ.

    Từng entry.result có thể đưa vào chieu_hoa_don với ID riêng do Core cấp.
    Không gọi trạng thái XONG từ wrapper cũ để suy gói đã đủ/chuẩn hóa.
    """
    if isinstance(raw, (bytes, bytearray)) and len(raw) > MAX_ZIP_BYTES_CORE:
        raise DataError("ZIP_TOO_LARGE", "ZIP vượt giới hạn tiếp nhận Core 20 MiB.")
    try:
        return doc_goi_hoa_don_zip(raw, contexts, archive_name=archive_name)
    except LZMAError as exc:
        if type(exc) is not LZMAError:
            raise
        _, code, reason = ANH_XA_NGOAI_LE_HOA_DON[LZMAError]
        raise DataError(code, reason) from exc
