"""M2 — bộ đọc STRICT, thuần (pure), opt-in cho hóa đơn XML/ZIP DEMO (profile `DEMO_M2_XML_QD1271_FIELDS_V1`).

Đầu bài: docs/GIAO-CODE-M2-XML-PURE-01.md; DTO: docs/M2-XML-PURE-DTO-01.json; profile: docs/M2-PROFILE-XML-DEMO-01.md.

- Chỉ nhận BYTES thực (bytearray được snapshot thành bytes ngay biên). Không đọc filesystem/env/DB/network, không ghi file, không lấy giờ hiện
  tại, không sinh UUID. Tên artifact/archive chỉ là metadata, không dùng để mở/giải nén ra đĩa.
- Cùng họ adapter với `that.py` (stdlib ElementTree/ZipFile), nhưng KHÔNG gọi `parse_invoice_xml`/`_xml_rows` (legacy flatten namespace,
  descendant search, strip, float, default tiền tệ/tính chất/STT) — strict output viết riêng, `that.py` không đổi.
- Reuse đúng primitives: `DataError`, `canonical_json`, `sha256`, `date_iso`; ngữ nghĩa Issue của `fixture.Issue` (code/message/locator/severity)
  qua snapshot bất biến `InvoiceIssue` (`as_issue()` trả Issue MỚI). Không dùng normalize_text/text_id/money_minor.
- Field = các occurrence có thứ tự: thiếu → (ABSENT,), rỗng → (EMPTY,""), text → (TEXT, nguyên văn đã decode, KHÔNG trim). Trùng scalar giữ mọi
  occurrence + issue, không chọn đầu/cuối. Lexeme = XML_DECODED_CHARACTER_DATA_NO_TRIM, không phải byte span; row_raw_sha256 luôn NULL.
- Decimal exact (không float/round/default 0); số lượng/đơn giá 21 chữ số/6 thập phân; tiền giữ exact + PRECISION_UNDECLARED.
- PURE02: chuẩn hóa số lượng CHỈ cho CAI→CAI 1/1 (đơn vị khác fail-closed); fact của context mâu thuẫn raw/profile không được dùng.
- Định danh `DEMO_M2_ID_DIGITS_V1` dẫn xuất từ header native + công ty cấu hình (không nhận tuple canonical làm authority); nội dung
  `M2_XML_CONTENT_V1` = sha256(canonical_json(envelope)); hash raw/container/content/registry payload tách riêng.
- Crosswalk dòng chỉ theo fact tường minh (artifact SHA + locator + ordinal + identity tự dẫn xuất); không suy từ MaHang/STT.
- Không DB/seed/route/actor/API/UI/L11/ghi nhận nghiệp vụ; `native_fiscal_status` UNKNOWN, `business_promotion` NOT_PERFORMED.
"""

from __future__ import annotations

import io
import re
import zipfile
import zlib
from dataclasses import dataclass, fields as _dc_fields, is_dataclass
from decimal import Decimal
from typing import Any
from xml.etree import ElementTree as ET

from ..ha_tang.primitives import DataError, canonical_json, date_iso, sha256

# ---------------------------------------------------------------------------------------------------------------- profile / hằng số
PROFILE_REF = "DEMO_M2_XML_QD1271_FIELDS_V1"
PROFILE_DOCUMENT_SHA256 = "37d57c38138e7b76f916cb20ef72d92306967d1cce572820b15b135246c32fcf"
IDENTITY_PROFILE_REF = "DEMO_M2_ID_DIGITS_V1"
CONTENT_CONTRACT = "M2_XML_CONTENT_V1"
LEXEME_BASIS = "XML_DECODED_CHARACTER_DATA_NO_TRIM"
MEDIA_XML = "application/xml"

HEADER_TAGS = ("PBan", "KHMSHDon", "KHHDon", "SHDon", "NLap", "DVTTe")
HEADER_FIELDS = HEADER_TAGS + ("NBan/MST", "NMua/MST")
LINE_TAGS = ("STT", "TChat", "MHHDVu", "THHDVu", "DVTinh", "SLuong", "DGia", "ThTien", "TSuat")
_HEADER_CODE = {"KHMSHDon": "MODEL", "KHHDon": "SERIES", "SHDon": "NUMBER", "NLap": "DATE", "DVTTe": "CURRENCY",
                "NBan/MST": "SELLER_TAX_ID", "NMua/MST": "BUYER_TAX_ID"}
_NATURE = {"1": "GOODS", "2": "PROMOTION", "3": "DISCOUNT", "4": "NOTE", "5": "SPECIAL_GOODS"}

# PURE02/R1: đơn vị DUY NHẤT được chuẩn hóa ở pure phase của profile này (CAI, tỉ lệ 1/1). Đơn vị khác (vd THUNG) dù fact tự khai cùng
# raw/canonical 1/1 vẫn fail-closed: giữ raw/Decimal, normalized NULL. Quy đổi khác cần proof riêng ở gói L11 sau.
SUPPORTED_UNIT = "CAI"
QUANTITY_MAX_DIGITS = 21
QUANTITY_MAX_SCALE = 6
_DECIMAL = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_DIGITS = re.compile(r"[0-9]+")
_ENCODING_DECL = re.compile(rb"^(?:\xef\xbb\xbf)?\s*<\?xml[^>]*?encoding\s*=\s*[\"']([A-Za-z0-9._-]+)[\"']")

# giới hạn DEMO hữu hạn (chống input quá lớn/zip bomb); vượt → lỗi rõ, giữ container/raw
MAX_XML_BYTES = 16 * 1024 * 1024
MAX_ZIP_BYTES = 64 * 1024 * 1024
MAX_ZIP_ENTRIES = 1000

_PATH_DLHDON = "/HDon/DLHDon"
_PATH_TTCHUNG = "/HDon/DLHDon/TTChung"
_PATH_NDHDON = "/HDon/DLHDon/NDHDon"
_PATH_LINE = "/HDon/DLHDon/NDHDon/DSHHDVu/HHDVu"

_ALLOWED_CHILDREN = {"HDon": {"DLHDon"}, "DLHDon": {"TTChung", "NDHDon"}, "TTChung": set(HEADER_TAGS),
                     "NDHDon": {"NBan", "NMua", "DSHHDVu", "TToan"}, "NBan": {"MST"}, "NMua": {"MST"}, "DSHHDVu": {"HHDVu"},
                     "HHDVu": set(LINE_TAGS)}

# BR4: phần đọc bổ sung có allowlist riêng; envelope V1 vẫn được kiểm bằng
# allowlist cũ để không đổi bất kỳ field/issue/digest đã phát hành nào.
_LEGACY_ALLOWED_CHILDREN = _ALLOWED_CHILDREN
MONEY_TAGS = ("TgTCThue", "TgTThue", "TgTTTBSo", "TGTKCThue")
TAX_TAGS = ("TSuat", "ThTien", "TThue")
RELATION_TAGS = ("TCHDon", "LHDCLQuan", "KHMSHDCLQuan", "KHHDCLQuan", "SHDCLQuan", "NLHDCLQuan")
_ALLOWED_CHILDREN = {**_ALLOWED_CHILDREN,
                     "TTChung": set(HEADER_TAGS) | {"TTHDLQuan"},
                     "TToan": set(MONEY_TAGS) | {"THTTLTSuat"},
                     "THTTLTSuat": {"LTSuat"}, "LTSuat": set(TAX_TAGS),
                     "TTHDLQuan": set(RELATION_TAGS)}

_WARNING = {"PBAN_ABSENT", "MODEL_ABSENT", "MODEL_EMPTY", "SERIES_ABSENT", "SERIES_EMPTY", "NUMBER_ABSENT", "NUMBER_EMPTY", "DATE_ABSENT",
            "DATE_EMPTY", "CURRENCY_ABSENT", "CURRENCY_EMPTY", "SELLER_TAX_ID_ABSENT", "SELLER_TAX_ID_EMPTY", "BUYER_TAX_ID_ABSENT",
            "BUYER_TAX_ID_EMPTY", "STT_ABSENT", "STT_EMPTY", "STT_DUPLICATE", "STT_AMBIGUOUS", "LINE_IDENTITY_UNRESOLVED", "NATURE_ABSENT",
            "NATURE_EMPTY", "NATURE_UNKNOWN", "SPECIAL_GOODS_HOLD", "QUANTITY_ABSENT", "QUANTITY_EMPTY", "UNIT_ABSENT", "UNIT_EMPTY",
            "UNIT_UNPROVEN", "XML_LITERAL_LEXEME_NOT_PROVEN", "ZIP_DUPLICATE_ENTRY_NAME", "ZIP_ENTRY_IGNORED_NON_XML",
            "CROSSWALK_NOT_APPLIED"}

_MESSAGES = {
    "XML_MALFORMED": "XML không phân tích được; giữ nguyên bytes làm bằng chứng.",
    "XML_TOO_LARGE": "XML vượt giới hạn DEMO; không phân tích.",
    "XML_DOCTYPE_UNSUPPORTED": "XML có DOCTYPE — ngoài profile strict; không phân tích.",
    "XML_ENCODING_UNSUPPORTED": "Mã hóa XML ngoài UTF-8 của profile DEMO; không phân tích.",
    "XML_LITERAL_LEXEME_NOT_PROVEN": "XML có entity/CDATA/comment/PI/CR — text đã decode có thể khác chính tả byte; không cấp content digest.",
    "UNSUPPORTED_NAMESPACE": "Namespace ngoài profile (không namespace); không strip namespace để ghép field.",
    "UNSUPPORTED_PATH": "Không đúng path wrapped HDon/DLHDon/{TTChung,NDHDon}; không descendant search.",
    "STRUCTURE_DUPLICATE": "Phần tử cấu trúc xuất hiện nhiều lần; không chọn một bản.",
    "UNSUPPORTED_ELEMENT": "Phần tử ngoài profile DEMO (vd DChat) — giữ bằng chứng, không làm alias, không cấp content digest.",
    "UNSUPPORTED_ATTRIBUTE": "Thuộc tính XML ngoài profile; không cấp content digest.",
    "UNSUPPORTED_TEXT": "Text không phải khoảng trắng trong phần tử cấu trúc; không cấp content digest.",
    "TOTAL_SECTION_UNSUPPORTED": "Có mục tổng TToan — ngoài envelope DEMO hiện hỗ trợ.",
    "LINES_SECTION_ABSENT": "Thiếu DSHHDVu.",
    "FIELD_DUPLICATE": "Field scalar xuất hiện nhiều lần — giữ mọi occurrence, không chọn.",
    "FIELD_MIXED_CONTENT": "Field scalar có phần tử con — không ghép itertext.",
    "DATE_INVALID": "NLap không phải ngày YYYY-MM-DD hợp lệ.",
    "NUMBER_INVALID": "SHDon không phải chuỗi chữ số ASCII.",
    "IDENTITY_FIELD_INVALID": "Field định danh không phải ASCII in được, không rỗng.",
    "STT_ABSENT": "Dòng thiếu STT.", "STT_EMPTY": "STT rỗng.", "STT_DUPLICATE": "STT trùng giữa các dòng.",
    "STT_AMBIGUOUS": "STT nhiều occurrence trong một dòng.",
    "LINE_IDENTITY_UNRESOLVED": "Không có khóa dòng logic tự động (STT chỉ là thứ tự nguồn).",
    "NATURE_ABSENT": "Thiếu TChat — UNKNOWN, không mặc định GOODS.", "NATURE_EMPTY": "TChat rỗng.",
    "NATURE_UNKNOWN": "TChat ngoài 1..5.", "NATURE_AMBIGUOUS": "TChat nhiều occurrence.",
    "SPECIAL_GOODS_HOLD": "TChat=5 — giữ chờ trong corpus DEMO.",
    "QUANTITY_ABSENT": "Thiếu SLuong — không phải 0.", "QUANTITY_EMPTY": "SLuong rỗng — không phải 0.",
    "QUANTITY_LEXEME_INVALID": "SLuong không theo ^-?[0-9]+(\\.[0-9]+)?$ (không khoảng trắng/dấu +/exponent/dấu phẩy).",
    "QUANTITY_DIGITS_EXCEEDED": "SLuong vượt 21 chữ số.", "QUANTITY_SCALE_EXCEEDED": "SLuong vượt 6 chữ số thập phân.",
    "QUANTITY_AMBIGUOUS": "SLuong nhiều occurrence/mixed.",
    "QUANTITY_FACT_DOMAIN_EXCEEDED": "Số lượng vượt miền của fact đo lường — không chuẩn hóa.",
    "UNIT_PRICE_LEXEME_INVALID": "DGia sai ngữ pháp decimal.", "UNIT_PRICE_DIGITS_EXCEEDED": "DGia vượt 21 chữ số.",
    "UNIT_PRICE_SCALE_EXCEEDED": "DGia vượt 6 chữ số thập phân.", "UNIT_PRICE_AMBIGUOUS": "DGia nhiều occurrence/mixed.",
    "AMOUNT_LEXEME_INVALID": "ThTien sai ngữ pháp decimal.", "AMOUNT_AMBIGUOUS": "ThTien nhiều occurrence/mixed.",
    "UNIT_ABSENT": "Thiếu DVTinh — không chuẩn hóa số lượng.", "UNIT_EMPTY": "DVTinh rỗng.",
    "UNIT_AMBIGUOUS": "DVTinh nhiều occurrence/mixed.", "UNIT_UNPROVEN": "Không có fact đơn vị khớp DVTinh — số lượng chuẩn hóa NULL (HOLD).",
    "MEASUREMENT_FACTS_UNSUPPORTED": "Fact đo lường ngoài quy tắc hỗ trợ (CAI 1/1, 21/6, profile document đúng) — bỏ qua.",
    "RAW_REF_MISMATCH": "Raw ref kỳ vọng của context không khớp bytes thực — HOLD, không ghi đè native.",
    "PROFILE_REF_MISMATCH": "Context profile ref khác profile strict.", "PROFILE_DOCUMENT_MISMATCH": "Context profile document SHA khác profile strict.",
    "PROFILE_PAYLOAD_CONFUSED": "Profile payload SHA trùng document SHA — hai hash phải tách.",
    "IDENTITY_PROFILE_UNSUPPORTED": "Identity profile không được hỗ trợ.",
    "COMPANY_BOTH_SIDES": "Công ty cấu hình là cả người bán lẫn người mua — giữ ứng viên.",
    "CROSSWALK_ARTIFACT_MISMATCH": "Crosswalk bind artifact SHA khác bytes thực — không áp.",
    "CROSSWALK_IDENTITY_MISMATCH": "Crosswalk bind định danh khác định danh tự dẫn xuất — không áp.",
    "CROSSWALK_LOCATOR_MISMATCH": "Crosswalk locator/ordinal không khớp dòng nguồn — không áp.",
    "CROSSWALK_DUPLICATE_LINE": "Nhiều crosswalk cho cùng dòng — không áp dòng đó.",
    "CROSSWALK_NOT_APPLIED": "Chưa có content digest/định danh — crosswalk không áp.",
    "ZIP_MALFORMED": "ZIP không mở được; giữ container bytes.", "ZIP_TOO_LARGE": "ZIP vượt giới hạn DEMO.",
    "ZIP_TOO_MANY_ENTRIES": "ZIP quá nhiều entry.", "ZIP_DUPLICATE_ENTRY_NAME": "Tên entry trùng — giữ từng entry theo ordinal, không gộp.",
    "ZIP_MEMBER_READ_ERROR": "Entry ZIP không đọc được — raw NULL.", "ZIP_MEMBER_TOO_LARGE": "Entry ZIP vượt giới hạn DEMO.",
    "ZIP_ENTRY_IGNORED_NON_XML": "Entry không phải .xml — bỏ qua, không đọc.",
    "CONTEXT_UNMATCHED": "Context không khớp đúng container SHA + ordinal + tên entry nào — không dùng.",
    "CONTEXT_AMBIGUOUS": "Nhiều context cho cùng entry — không dùng context nào.",
}

# key context bị cấm (authority không thuộc pure reader)
FORBIDDEN_CONTEXT_KEYS = frozenset({"case_id", "expected_output", "expected_semantic_digest", "semantic_sha256", "canonical_invoice_tuple",
                                    "canonical_identity", "identity_alias", "content_alias", "observation_alias", "observation_ref", "actor",
                                    "route", "L11_proven", "l11_proven", "direction"})


def _loi(code: str, message: str, locator: str = "$"):
    raise DataError(code, message, locator)


def _str(v, f, *, none_ok=False, empty_ok=False) -> str | None:
    if v is None and none_ok:
        return None
    if not isinstance(v, str) or (not empty_ok and v == ""):
        _loi("CONTEXT_FIELD_TYPE", f"{f} phải là chuỗi{' không rỗng' if not empty_ok else ''}.", f)
    return v


def _int(v, f, minimum: int) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v < minimum:
        _loi("CONTEXT_FIELD_TYPE", f"{f} phải là số nguyên ≥ {minimum} (bool không phải int).", f)
    return v


def _hex(v, f, *, none_ok=False) -> str | None:
    if v is None and none_ok:
        return None
    if not isinstance(v, str) or not _HEX64.fullmatch(v):
        _loi("CONTEXT_FIELD_TYPE", f"{f} phải là SHA-256 hex thường.", f)
    return v


def _tuple(v, typ, f) -> tuple:
    if not isinstance(v, (tuple, list)):
        _loi("CONTEXT_FIELD_TYPE", f"{f} phải là tuple/list.", f)
    out = tuple(v)
    for i, x in enumerate(out):
        if not isinstance(x, typ):
            _loi("CONTEXT_FIELD_TYPE", f"{f}[{i}] sai kiểu.", f"{f}[{i}]")
    return out


def _keys(d, allowed: set, f: str) -> dict:
    if not isinstance(d, dict):
        _loi("CONTEXT_FIELD_TYPE", f"{f} phải là object.", f)
    cam = sorted(k for k in d if k in FORBIDDEN_CONTEXT_KEYS)
    if cam:
        _loi("CONTEXT_FORBIDDEN_FIELD", f"{f} chứa key bị cấm: {', '.join(map(str, cam))}.", f)
    la = sorted(str(k) for k in d if k not in allowed)
    if la:
        _loi("CONTEXT_UNKNOWN_FIELD", f"{f} có key lạ: {', '.join(la)}.", f)
    return d


# ---------------------------------------------------------------------------------------------------------------- DTO (frozen, sâu)
@dataclass(frozen=True)
class InvoiceIssue:
    code: str
    message: str
    locator: str
    severity: str

    def __post_init__(self):
        for f in ("code", "message", "locator"):
            _str(getattr(self, f), f"InvoiceIssue.{f}")
        if self.severity not in ("ERROR", "WARNING"):
            _loi("ISSUE_SEVERITY", "severity phải là ERROR hoặc WARNING.", "InvoiceIssue.severity")

    def as_issue(self):
        """Interop: trả fixture.Issue MỚI mỗi lần (Issue mutable — không chia sẻ object bên trong DTO)."""
        from .fixture import Issue
        return Issue(code=self.code, message=self.message, locator=self.locator, severity=self.severity)


@dataclass(frozen=True)
class FieldValue:
    state: str
    lexeme: str | None
    lexeme_basis: str = LEXEME_BASIS

    def __post_init__(self):
        ok = ((self.state == "ABSENT" and self.lexeme is None) or (self.state == "EMPTY" and self.lexeme == "")
              or (self.state == "TEXT" and isinstance(self.lexeme, str) and self.lexeme != ""))
        if not ok or self.lexeme_basis != LEXEME_BASIS:
            _loi("FIELD_VALUE_INVARIANT", "FieldValue: ABSENT⇒None, EMPTY⇒'', TEXT⇒chuỗi không rỗng; basis decoded-no-trim.", "FieldValue")

    def ra_dict(self) -> dict:
        return {"state": self.state, "lexeme": self.lexeme}


_ABSENT = FieldValue("ABSENT", None)


@dataclass(frozen=True)
class InvoiceField:
    name: str
    locator: str
    occurrences: tuple
    mixed_content: bool = False

    def __post_init__(self):
        object.__setattr__(self, "occurrences", _tuple(self.occurrences, FieldValue, f"InvoiceField({self.name}).occurrences"))
        if not self.occurrences:
            _loi("FIELD_VALUE_INVARIANT", "InvoiceField phải có ≥1 occurrence (thiếu = (ABSENT,)).", self.locator)

    @property
    def duy_nhat(self) -> FieldValue | None:
        """Occurrence duy nhất rõ ràng; None nếu trùng hoặc mixed content (không chọn đầu/cuối)."""
        return self.occurrences[0] if len(self.occurrences) == 1 and not self.mixed_content else None


@dataclass(frozen=True)
class XmlRawRef:
    native_sha256: str
    byte_length: int
    media_type: str = MEDIA_XML
    container_sha256: str | None = None
    entry_ordinal: int | None = None
    entry_name: str | None = None

    def __post_init__(self):
        _hex(self.native_sha256, "raw_ref.native_sha256")
        _int(self.byte_length, "raw_ref.byte_length", 0)
        if self.media_type != MEDIA_XML:
            _loi("CONTEXT_FIELD_TYPE", "raw_ref.media_type phải là application/xml.", "raw_ref.media_type")
        zip_parts = (self.container_sha256, self.entry_ordinal, self.entry_name)
        if any(x is not None for x in zip_parts):
            if any(x is None for x in zip_parts):
                _loi("CONTEXT_FIELD_TYPE", "raw_ref ZIP cần đủ container_sha256 + entry_ordinal + entry_name.", "raw_ref")
            _hex(self.container_sha256, "raw_ref.container_sha256")
            _int(self.entry_ordinal, "raw_ref.entry_ordinal", 1)
            _str(self.entry_name, "raw_ref.entry_name")

    @classmethod
    def tu_dict(cls, d) -> "XmlRawRef":
        _keys(d, {"native_sha256", "byte_length", "media_type", "container_sha256", "entry_ordinal", "entry_name"}, "raw_ref")
        return cls(d.get("native_sha256"), d.get("byte_length"), d.get("media_type", MEDIA_XML), d.get("container_sha256"),
                   d.get("entry_ordinal"), d.get("entry_name"))


@dataclass(frozen=True)
class CompanyFact:
    source_company_key: str
    pn_alias: str
    mapping_ref: str
    mapping_revision: int
    scope_ref: str
    authority: str = "DECLARED_DEMO"

    def __post_init__(self):
        for f in ("source_company_key", "pn_alias", "mapping_ref", "scope_ref", "authority"):
            _str(getattr(self, f), f"company.{f}")
        _int(self.mapping_revision, "company.mapping_revision", 1)

    @classmethod
    def tu_dict(cls, d) -> "CompanyFact":
        _keys(d, {"source_company_key", "pn_alias", "mapping_ref", "mapping_revision", "scope_ref", "authority"}, "company")
        return cls(d.get("source_company_key"), d.get("pn_alias"), d.get("mapping_ref"), d.get("mapping_revision"), d.get("scope_ref"),
                   d.get("authority", "DECLARED_DEMO"))


@dataclass(frozen=True)
class LineCrosswalkFact:
    mapping_ref: str
    revision: int
    invoice_identity_binding: tuple
    content_artifact_sha256: str
    source_locator: str
    source_ordinal: int
    logical_line_ref: str
    continuity_ref: str
    row_raw_sha256: None = None

    def __post_init__(self):
        for f in ("mapping_ref", "source_locator", "logical_line_ref", "continuity_ref"):
            _str(getattr(self, f), f"crosswalk.{f}")
        _int(self.revision, "crosswalk.revision", 1)
        _int(self.source_ordinal, "crosswalk.source_ordinal", 1)
        _hex(self.content_artifact_sha256, "crosswalk.content_artifact_sha256")
        b = _tuple(self.invoice_identity_binding, str, "crosswalk.invoice_identity_binding")
        if len(b) != 6 or any(x == "" for x in b):
            _loi("CONTEXT_FIELD_TYPE", "invoice_identity_binding phải là 6 chuỗi (PN, chiều, mst_ban, mẫu, ký hiệu, số chuẩn).",
                 "crosswalk.invoice_identity_binding")
        object.__setattr__(self, "invoice_identity_binding", b)
        if self.row_raw_sha256 is not None:
            _loi("CONTEXT_FIELD_TYPE", "row_raw_sha256 phải NULL (chưa có span thật).", "crosswalk.row_raw_sha256")

    @classmethod
    def tu_dict(cls, d) -> "LineCrosswalkFact":
        _keys(d, {"mapping_ref", "revision", "invoice_identity_binding", "content_artifact_sha256", "source_locator", "source_ordinal",
                  "logical_line_ref", "continuity_ref", "row_raw_sha256"}, "crosswalk")
        return cls(d.get("mapping_ref"), d.get("revision"), d.get("invoice_identity_binding"), d.get("content_artifact_sha256"),
                   d.get("source_locator"), d.get("source_ordinal"), d.get("logical_line_ref"), d.get("continuity_ref"),
                   d.get("row_raw_sha256"))


@dataclass(frozen=True)
class InvoiceMeasurementFacts:
    encoding_ref: str
    unit_definition_ref: str
    profile_document_sha256: str
    raw_unit: str
    canonical_unit: str
    numerator_text: str
    denominator_text: str
    max_lexical_digits: int
    max_scale: int
    declared_encoding_kind: str = "EXACT_TEXT_DECIMAL"
    authority: str = "DECLARED_DEMO"

    def __post_init__(self):
        for f in ("encoding_ref", "unit_definition_ref", "raw_unit", "canonical_unit", "numerator_text", "denominator_text",
                  "declared_encoding_kind", "authority"):
            _str(getattr(self, f), f"measurement.{f}")
        _hex(self.profile_document_sha256, "measurement.profile_document_sha256")
        _int(self.max_lexical_digits, "measurement.max_lexical_digits", 0)
        _int(self.max_scale, "measurement.max_scale", 0)

    @property
    def ho_tro(self) -> bool:
        """Quy tắc DEMO duy nhất được hỗ trợ: CAI→CAI (không đơn vị tùy ý), tỉ lệ 1/1, EXACT_TEXT_DECIMAL, ≤21/≤6, đúng profile document."""
        return (self.declared_encoding_kind == "EXACT_TEXT_DECIMAL" and self.raw_unit == SUPPORTED_UNIT and self.canonical_unit == SUPPORTED_UNIT
                and self.numerator_text == "1" and self.denominator_text == "1" and self.profile_document_sha256 == PROFILE_DOCUMENT_SHA256
                and self.max_lexical_digits <= QUANTITY_MAX_DIGITS and self.max_scale <= QUANTITY_MAX_SCALE)

    @classmethod
    def tu_dict(cls, d) -> "InvoiceMeasurementFacts":
        _keys(d, {"encoding_ref", "unit_definition_ref", "profile_document_sha256", "raw_unit", "canonical_unit", "numerator_text",
                  "denominator_text", "max_lexical_digits", "max_scale", "declared_encoding_kind", "authority"}, "measurement")
        return cls(d.get("encoding_ref"), d.get("unit_definition_ref"), d.get("profile_document_sha256"), d.get("raw_unit"),
                   d.get("canonical_unit"), d.get("numerator_text"), d.get("denominator_text"), d.get("max_lexical_digits"),
                   d.get("max_scale"), d.get("declared_encoding_kind", "EXACT_TEXT_DECIMAL"), d.get("authority", "DECLARED_DEMO"))


@dataclass(frozen=True)
class InvoiceReadContext:
    """Context do caller tin cậy đã resolve (không phải trình duyệt). Không có case_id/expected/alias/route/actor/L11."""
    source_instance: str | None = None
    source_profile_ref: str | None = None
    profile_document_sha256: str | None = None
    profile_payload_sha256: str | None = None
    profile_payload_binding: str = "NOT_BOUND"
    company: CompanyFact | None = None
    identity_profile_ref: str | None = None
    expected_raw_ref: XmlRawRef | None = None
    line_crosswalk: tuple = ()
    resolved_invoice_measurement_facts: InvoiceMeasurementFacts | None = None

    def __post_init__(self):
        _str(self.source_instance, "context.source_instance", none_ok=True)
        _str(self.source_profile_ref, "context.source_profile_ref", none_ok=True)
        _hex(self.profile_document_sha256, "context.profile_document_sha256", none_ok=True)
        _hex(self.profile_payload_sha256, "context.profile_payload_sha256", none_ok=True)
        _str(self.profile_payload_binding, "context.profile_payload_binding")
        _str(self.identity_profile_ref, "context.identity_profile_ref", none_ok=True)
        if self.company is not None and not isinstance(self.company, CompanyFact):
            _loi("CONTEXT_FIELD_TYPE", "company phải là CompanyFact.", "context.company")
        if self.expected_raw_ref is not None and not isinstance(self.expected_raw_ref, XmlRawRef):
            _loi("CONTEXT_FIELD_TYPE", "expected_raw_ref phải là XmlRawRef.", "context.expected_raw_ref")
        if (self.resolved_invoice_measurement_facts is not None
                and not isinstance(self.resolved_invoice_measurement_facts, InvoiceMeasurementFacts)):
            _loi("CONTEXT_FIELD_TYPE", "resolved_invoice_measurement_facts sai kiểu.", "context.resolved_invoice_measurement_facts")
        object.__setattr__(self, "line_crosswalk", _tuple(self.line_crosswalk, LineCrosswalkFact, "context.line_crosswalk"))

    @classmethod
    def tu_dict(cls, d) -> "InvoiceReadContext":
        """Snapshot sâu từ mapping JSON-like: list → tuple, object con → DTO frozen; key cấm/lạ → DataError (không I/O)."""
        _keys(d, {"source_instance", "source_profile_ref", "profile_document_sha256", "profile_payload_sha256", "profile_payload_binding",
                  "company", "identity_profile_ref", "expected_raw_ref", "line_crosswalk", "resolved_invoice_measurement_facts"}, "context")
        cw = d.get("line_crosswalk", ())
        if not isinstance(cw, (list, tuple)):
            _loi("CONTEXT_FIELD_TYPE", "line_crosswalk phải là list/tuple.", "context.line_crosswalk")
        return cls(source_instance=d.get("source_instance"), source_profile_ref=d.get("source_profile_ref"),
                   profile_document_sha256=d.get("profile_document_sha256"), profile_payload_sha256=d.get("profile_payload_sha256"),
                   profile_payload_binding=d.get("profile_payload_binding", "NOT_BOUND"),
                   company=None if d.get("company") is None else CompanyFact.tu_dict(d["company"]),
                   identity_profile_ref=d.get("identity_profile_ref"),
                   expected_raw_ref=None if d.get("expected_raw_ref") is None else XmlRawRef.tu_dict(d["expected_raw_ref"]),
                   line_crosswalk=tuple(LineCrosswalkFact.tu_dict(x) for x in cw),
                   resolved_invoice_measurement_facts=(None if d.get("resolved_invoice_measurement_facts") is None
                                                       else InvoiceMeasurementFacts.tu_dict(d["resolved_invoice_measurement_facts"])))


@dataclass(frozen=True)
class DecimalFact:
    state: str
    exact_value: Decimal | None = None
    exact_text: str | None = None
    lexical_digits: int | None = None
    scale: int | None = None

    def __post_init__(self):
        if self.state not in ("EXACT", "ABSENT", "EMPTY", "INVALID", "OVER_DOMAIN", "PRECISION_UNDECLARED"):
            _loi("DECIMAL_INVARIANT", "DecimalFact.state lạ.", "DecimalFact")
        co_gia_tri = self.state in ("EXACT", "PRECISION_UNDECLARED")
        if co_gia_tri != (isinstance(self.exact_value, Decimal) and isinstance(self.exact_text, str)):
            _loi("DECIMAL_INVARIANT", "Chỉ EXACT/PRECISION_UNDECLARED mang giá trị exact.", "DecimalFact")


@dataclass(frozen=True)
class InvoiceTaxComponent:
    source_locator: str
    fields: tuple
    rate: str | None
    net_amount: DecimalFact
    tax_amount: DecimalFact


@dataclass(frozen=True)
class InvoiceMoney:
    """Chỉ số nguồn, chưa phải minor/cơ sở thuế đã duyệt; không cộng/trừ/suy số thiếu."""
    state: str = "HOLD"
    fields: tuple = ()
    currency: str | None = None
    net_amount: DecimalFact = DecimalFact("ABSENT")
    tax_amount: DecimalFact = DecimalFact("ABSENT")
    non_taxable_amount: DecimalFact = DecimalFact("ABSENT")
    total_amount: DecimalFact = DecimalFact("ABSENT")
    tax_components: tuple = ()
    issues: tuple = ()
    reasons: tuple = ("INPUT_NOT_READ",)


@dataclass(frozen=True)
class InvoiceRelation:
    state: str
    source_locator: str
    fields: tuple
    relation_type: str | None
    original_model: str | None
    original_series: str | None
    original_number: str | None
    original_date: str | None
    issues: tuple


@dataclass(frozen=True)
class InvoiceRelations:
    # ABSENT chỉ nghĩa là không có thẻ, không khẳng định hóa đơn không có quan hệ.
    state: str = "HOLD"
    items: tuple = ()
    issues: tuple = ()
    reasons: tuple = ("INPUT_NOT_READ",)


@dataclass(frozen=True)
class InvoiceLine:
    source_ordinal: int
    source_locator: str
    fields: tuple
    nature: str
    quantity: DecimalFact
    unit_price: DecimalFact
    source_amount: DecimalFact
    normalized_quantity_text: str | None
    unit_definition_ref: str | None
    logical_line_ref: str | None
    crosswalk_ref: str | None
    continuity_ref: str | None
    issues: tuple
    row_raw_sha256: None = None

    def __post_init__(self):
        object.__setattr__(self, "fields", _tuple(self.fields, InvoiceField, "InvoiceLine.fields"))
        object.__setattr__(self, "issues", _tuple(self.issues, InvoiceIssue, "InvoiceLine.issues"))

    def field(self, name: str) -> InvoiceField:
        return next(f for f in self.fields if f.name == name)


@dataclass(frozen=True)
class InvoiceContentEnvelope:
    contract: str
    canonical_invoice_tuple: tuple
    header: tuple
    lines: tuple
    header_total_section: FieldValue

    def ra_dict(self) -> dict:
        """Envelope chính xác của golden M2_XML_CONTENT_V1 (dict/list MỚI mỗi lần gọi)."""
        return {"contract": self.contract, "canonical_invoice_tuple": list(self.canonical_invoice_tuple),
                "header": {f.name: f.occurrences[0].ra_dict() for f in self.header},
                "lines": [{"source_ordinal": o, "fields": {f.name: f.occurrences[0].ra_dict() for f in fs}} for o, fs in self.lines],
                "header_total_section": self.header_total_section.ra_dict()}

    @property
    def digest(self) -> str:
        return sha256(canonical_json(self.ra_dict()).encode("utf-8"))


@dataclass(frozen=True)
class InvoiceReadResult:
    raw_xml: bytes
    raw_ref: XmlRawRef
    artifact_name: str | None
    shape: str
    source_instance: str | None
    source_profile_ref: str | None
    profile_document_sha256: str | None
    profile_payload_sha256: str | None
    header_fields: tuple
    header_total_section: FieldValue
    lines: tuple
    canonical_identity: tuple | None
    semantic_envelope: InvoiceContentEnvelope | None
    semantic_digest: str | None
    issues: tuple
    candidate_reasons: tuple
    native_fiscal_status: str = "UNKNOWN"
    business_promotion: str = "NOT_PERFORMED"
    current_DB_basis_sha256: None = None
    L11_eligibility: str = "NOT_EVALUATED"
    request_digest: str = "NOT_DEFINED_IN_THIS_SLICE"
    profile_payload_binding: str = "NOT_BOUND"

    # BR4 bổ sung độc lập: không dùng cho semantic V1 hoặc quyết định promote.
    money: InvoiceMoney = InvoiceMoney()
    relations: InvoiceRelations = InvoiceRelations()

    def __post_init__(self):
        for f, typ in (("header_fields", InvoiceField), ("lines", InvoiceLine), ("issues", InvoiceIssue), ("candidate_reasons", str)):
            object.__setattr__(self, f, _tuple(getattr(self, f), typ, f"InvoiceReadResult.{f}"))
        if self.canonical_identity is not None:
            object.__setattr__(self, "canonical_identity", _tuple(self.canonical_identity, str, "canonical_identity"))
        if not isinstance(self.raw_xml, bytes):
            _loi("RESULT_INVARIANT", "raw_xml phải là bytes.", "InvoiceReadResult.raw_xml")

    def header(self, name: str) -> InvoiceField:
        return next(f for f in self.header_fields if f.name == name)


@dataclass(frozen=True)
class ZipEntryResult:
    entry_ordinal: int
    entry_name: str
    byte_length: int | None
    raw_sha256: str | None
    result: InvoiceReadResult | None
    issues: tuple
    state: str

    def __post_init__(self):
        object.__setattr__(self, "issues", _tuple(self.issues, InvoiceIssue, "ZipEntryResult.issues"))
        if self.state not in ("PARSED", "CANDIDATE", "READ_ERROR", "IGNORED_NON_XML"):
            _loi("RESULT_INVARIANT", "ZipEntryResult.state lạ.", "ZipEntryResult.state")


@dataclass(frozen=True)
class InvoiceZipReadResult:
    raw_zip: bytes
    container_sha256: str
    byte_length: int
    archive_name: str | None
    entries: tuple
    artifact_coverage: str
    issues: tuple
    period_completeness: str = "UNKNOWN"
    source_revocation: str = "NOT_INFERRED"

    def __post_init__(self):
        object.__setattr__(self, "entries", _tuple(self.entries, ZipEntryResult, "InvoiceZipReadResult.entries"))
        object.__setattr__(self, "issues", _tuple(self.issues, InvoiceIssue, "InvoiceZipReadResult.issues"))
        if self.artifact_coverage not in ("COMPLETE", "PARTIAL"):
            _loi("RESULT_INVARIANT", "artifact_coverage phải COMPLETE/PARTIAL.", "artifact_coverage")


# ---------------------------------------------------------------------------------------------------------------- JSON copy
def ra_json(value: Any) -> Any:
    """Bản sao JSON-compatible MỚI: dataclass → dict, tuple → list, Decimal → text exact (format 'f', không float).
    Trường bytes (raw_xml/raw_zip) không đưa vào bản JSON — dùng raw_ref/container_sha256 làm tham chiếu."""
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: ra_json(getattr(value, f.name)) for f in _dc_fields(value) if not isinstance(getattr(value, f.name), bytes)}
    if isinstance(value, (tuple, list)):
        return [ra_json(x) for x in value]
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {k: ra_json(v) for k, v in value.items()}
    if isinstance(value, bytes):
        return None
    return value


# ---------------------------------------------------------------------------------------------------------------- input boundary
def _bytes(raw, f: str) -> bytes:
    if isinstance(raw, bytearray):
        return bytes(raw)
    if not isinstance(raw, bytes):
        _loi("INPUT_NOT_BYTES", f"{f} phải là bytes thực (không str/path/file object).", f)
    return raw


def _ten(v, f) -> str | None:
    if v is not None and not isinstance(v, str):
        _loi("INPUT_NAME_TYPE", f"{f} chỉ là metadata chuỗi hoặc None.", f)
    return v


def _context(ctx) -> InvoiceReadContext | None:
    if ctx is not None and not isinstance(ctx, InvoiceReadContext):
        _loi("CONTEXT_FIELD_TYPE", "context phải là InvoiceReadContext hoặc None.", "context")
    return ctx


class _Ghi:
    """Bộ gom issue với locator phân biệt artifact/container-entry + path nguồn."""

    def __init__(self, prefix: str):
        self.prefix = prefix

    def issue(self, code: str, path: str, message: str | None = None) -> InvoiceIssue:
        return InvoiceIssue(code, message or _MESSAGES.get(code, code), f"{self.prefix}#{path}", "WARNING" if code in _WARNING else "ERROR")


def _prefix(ref: XmlRawRef) -> str:
    if ref.container_sha256 is not None:
        return f"zip:{ref.container_sha256}!{ref.entry_ordinal}:{ref.entry_name}"
    return f"xml:{ref.native_sha256}"


# ---------------------------------------------------------------------------------------------------------------- XML strict
def _children(el, tag) -> list:
    return [c for c in el if c.tag == tag]


def _field(parents: list, tag: str, name: str, locator: str) -> InvoiceField:
    occ, mixed = [], False
    for p in parents:
        for c in _children(p, tag):
            if len(c):
                mixed = True
            occ.append(FieldValue("EMPTY", "") if c.text is None or c.text == "" else FieldValue("TEXT", c.text))
    return InvoiceField(name, locator, tuple(occ) or (_ABSENT,), mixed)


def _so(field: InvoiceField, ma: str, gioi_han: bool, bao_vang: bool) -> tuple[DecimalFact, list[str]]:
    if len(field.occurrences) > 1 or field.mixed_content:
        return DecimalFact("INVALID"), [f"{ma}_AMBIGUOUS"]
    fv = field.occurrences[0]
    if fv.state == "ABSENT":
        return DecimalFact("ABSENT"), [f"{ma}_ABSENT"] if bao_vang else []
    if fv.state == "EMPTY":
        return DecimalFact("EMPTY"), [f"{ma}_EMPTY"] if bao_vang else []
    s = fv.lexeme
    if not _DECIMAL.fullmatch(s):
        return DecimalFact("INVALID"), [f"{ma}_LEXEME_INVALID"]
    digits = sum(ch.isdigit() for ch in s)
    scale = len(s.split(".", 1)[1]) if "." in s else 0
    if gioi_han:
        codes = ([f"{ma}_DIGITS_EXCEEDED"] if digits > QUANTITY_MAX_DIGITS else []) + ([f"{ma}_SCALE_EXCEEDED"] if scale > QUANTITY_MAX_SCALE else [])
        if codes:
            return DecimalFact("OVER_DOMAIN", None, None, digits, scale), codes
    d = Decimal(s)  # exact từ lexeme đã kiểm ngữ pháp; không float/round
    return DecimalFact("EXACT" if gioi_han else "PRECISION_UNDECLARED", d, format(d, "f"), digits, scale), []


def _literal_not_proven(raw: bytes) -> bool:
    prolog = 1 if raw.lstrip(b"\xef\xbb\xbf").lstrip().startswith(b"<?xml") else 0
    return (b"&" in raw or b"<![CDATA[" in raw or b"\r" in raw or b"<!--" in raw or raw.count(b"<?") > prolog)


def _component_structure(el, path, g, issues):
    """Kiểm cả scalar, thuộc tính và tail trong phần mở rộng; không bỏ qua thẻ lạ."""
    if el.attrib:
        issues.append(g.issue("UNSUPPORTED_ATTRIBUTE", path))
    allowed = _ALLOWED_CHILDREN.get(el.tag, set())
    if allowed and el.text and el.text.strip():
        issues.append(g.issue("UNSUPPORTED_TEXT", path))
    counts = {}
    for child in el:
        counts[child.tag] = counts.get(child.tag, 0) + 1
        loc = f"{path}/{child.tag}[{counts[child.tag]}]"
        if child.tag not in allowed:
            issues.append(g.issue("UNSUPPORTED_ELEMENT", loc))
        else:
            _component_structure(child, loc, g, issues)
        if child.tail and child.tail.strip():
            issues.append(g.issue("UNSUPPORTED_TEXT", loc))


def _component_text(field, g, issues, *, required=True):
    fv = field.duy_nhat
    if fv is None:
        code = "FIELD_AMBIGUOUS"
    elif fv.state in ("ABSENT", "EMPTY"):
        if not required and fv.state == "ABSENT":
            return None
        code = "FIELD_" + fv.state
    elif fv.lexeme != fv.lexeme.strip():
        code = "FIELD_LEXEME_INVALID"
    else:
        return fv.lexeme
    issues.append(g.issue(code, field.locator, f"{field.name}: thiếu, rỗng hoặc mơ hồ; HOLD."))
    return None


def _component_number(field, g, issues):
    fact, codes = _so(field, "MONEY", False, True)
    issues.extend(g.issue(code, field.locator, f"{field.name}: {code}; HOLD, không thay bằng 0.") for code in codes)
    return fact


def _read_money(tt, nd, raw, g):
    path = _PATH_NDHDON + "/TToan"
    sections = _children(nd, "TToan")
    issues = []
    if len(sections) != 1:
        issues.append(g.issue("MONEY_SECTION_ABSENT" if not sections else "MONEY_SECTION_AMBIGUOUS", path,
                              "Cần đúng một TToan; HOLD."))
    for section in sections:
        _component_structure(section, path, g, issues)
    fields = tuple(_field(sections, tag, tag, path + "/" + tag) for tag in MONEY_TAGS)
    fd = {f.name: f for f in fields}
    currency_field = _field(tt, "DVTTe", "DVTTe", _PATH_TTCHUNG + "/DVTTe")
    currency = _component_text(currency_field, g, issues)
    if currency is not None and not re.fullmatch(r"[A-Z]{3}", currency):
        issues.append(g.issue("MONEY_CURRENCY_INVALID", currency_field.locator, "DVTTe không phải mã 3 chữ hoa; HOLD."))
        currency = None
    for el in _children(tt[0], "DVTTe"):
        _component_structure(el, currency_field.locator, g, issues)
    net, tax, total = (_component_number(fd[tag], g, issues) for tag in MONEY_TAGS[:3])
    groups = [el for section in sections for el in _children(section, "THTTLTSuat")]
    if len(groups) != 1:
        issues.append(g.issue("MONEY_TAX_GROUP_AMBIGUOUS" if groups else "MONEY_TAX_GROUP_ABSENT", path + "/THTTLTSuat",
                              "Cần đúng một bảng tổng hợp thuế suất; HOLD."))
    components, rates, non_taxable = [], set(), []
    rows = [el for group in groups for el in _children(group, "LTSuat")]
    if not rows:
        issues.append(g.issue("MONEY_TAX_ROWS_ABSENT", path + "/THTTLTSuat", "Thiếu LTSuat; HOLD."))
    for i, el in enumerate(rows, 1):
        loc = f"{path}/THTTLTSuat/LTSuat[{i}]"
        fs = tuple(_field([el], tag, tag, loc + "/" + tag) for tag in TAX_TAGS)
        rate = _component_text(fs[0], g, issues)
        if rate is not None:
            # Chỉ phân loại mã nguồn, không tính tiền/thuế từ thuế suất.
            if rate not in ("0", "5", "8", "10", "0%", "5%", "8%", "10%", "KCT", "KKKNT"):
                issues.append(g.issue("MONEY_TAX_RATE_UNSUPPORTED", fs[0].locator, "Thuế suất ngoài profile; HOLD."))
                rate = None
            elif rate.rstrip("%") in rates:
                issues.append(g.issue("MONEY_TAX_RATE_AMBIGUOUS", loc, "Nhiều dòng cùng thuế suất; không cộng hoặc chọn; HOLD."))
            else:
                rates.add(rate.rstrip("%"))
        base = _component_number(fs[1], g, issues)
        vat = _component_number(fs[2], g, issues)
        components.append(InvoiceTaxComponent(loc, fs, rate, base, vat))
        if rate == "KCT":
            non_taxable.append(base)
    # TGTKCThue hoặc đúng một dòng KCT là số nguồn tường minh, không suy từ tổng.
    explicit = fd["TGTKCThue"].occurrences[0].state != "ABSENT"
    if explicit:
        non = _component_number(fd["TGTKCThue"], g, issues)
        if non_taxable and (len(non_taxable) != 1 or non_taxable[0].exact_value is None
                            or non.exact_value != non_taxable[0].exact_value):
            non = DecimalFact("INVALID")
            issues.append(g.issue("MONEY_NON_TAXABLE_CONFLICT", path, "TGTKCThue và dòng KCT mâu thuẫn; HOLD."))
    elif len(non_taxable) == 1:
        non = non_taxable[0]
    else:
        non = DecimalFact("ABSENT" if not non_taxable else "INVALID")
        issues.append(g.issue("MONEY_NON_TAXABLE_UNPROVEN", path, "Phần không chịu thuế thiếu hoặc mơ hồ; HOLD."))
    if _literal_not_proven(raw):
        issues.append(g.issue("XML_LITERAL_LEXEME_NOT_PROVEN", path))
    return InvoiceMoney("HOLD" if issues else "EXACT", fields + (currency_field,), currency, net, tax, non, total,
                        tuple(components), tuple(issues), tuple(dict.fromkeys(i.code for i in issues)))


def _read_relations(tt, raw, g):
    items, all_issues = [], []
    for i, el in enumerate(_children(tt[0], "TTHDLQuan"), 1):
        loc = f"{_PATH_TTCHUNG}/TTHDLQuan[{i}]"
        issues = []
        _component_structure(el, loc, g, issues)
        fs = tuple(_field([el], tag, tag, loc + "/" + tag) for tag in RELATION_TAGS)
        vals = {f.name: _component_text(f, g, issues, required=f.name != "LHDCLQuan") for f in fs}
        kind = {"1": "THAY_THE", "2": "DIEU_CHINH"}.get(vals["TCHDon"])
        if kind is None:
            issues.append(g.issue("RELATION_TYPE_UNSUPPORTED", loc + "/TCHDon", "TCHDon phải là 1 (thay thế) hoặc 2 (điều chỉnh); HOLD."))
        number, day = vals["SHDCLQuan"], vals["NLHDCLQuan"]
        if number is not None and not _DIGITS.fullmatch(number):
            issues.append(g.issue("RELATION_NUMBER_INVALID", loc + "/SHDCLQuan", "Số hóa đơn gốc không phải chữ số ASCII; HOLD."))
            number = None
        if day is not None:
            try:
                date_iso(day)
            except DataError:
                issues.append(g.issue("RELATION_DATE_INVALID", loc + "/NLHDCLQuan", "Ngày hóa đơn gốc không hợp lệ; HOLD."))
                day = None
        if _literal_not_proven(raw):
            issues.append(g.issue("XML_LITERAL_LEXEME_NOT_PROVEN", loc))
        items.append(InvoiceRelation("HOLD" if issues else "EXACT", loc, fs, kind, vals["KHMSHDCLQuan"],
                                     vals["KHHDCLQuan"], number, day, tuple(issues)))
        all_issues.extend(issues)
    return InvoiceRelations("HOLD" if all_issues else "EXACT" if items else "ABSENT", tuple(items), tuple(all_issues),
                            tuple(dict.fromkeys(i.code for i in all_issues)))


def _identity_text(fv: FieldValue | None) -> str | None:
    if fv is None or fv.state != "TEXT":
        return None
    s = fv.lexeme
    return s if s.isascii() and all(0x20 <= ord(c) < 0x7F for c in s) else None


def _doc(raw: bytes, ctx: InvoiceReadContext | None, ref: XmlRawRef, artifact_name: str | None) -> InvoiceReadResult:
    g = _Ghi(_prefix(ref))
    issues: list[InvoiceIssue] = []
    ly_do: list[str] = []  # candidate_reasons (thứ tự ổn định, không trùng)
    money, relations = InvoiceMoney(), InvoiceRelations()

    def ld(code: str):
        if code not in ly_do:
            ly_do.append(code)

    # ---- context: chỉ so sánh; không ghi đè native
    facts = None
    if ctx is None:
        ld("CONTEXT_ABSENT")
    else:
        if ctx.source_profile_ref != PROFILE_REF:
            issues.append(g.issue("PROFILE_REF_MISMATCH", "/context/source_profile_ref")); ld("PROFILE_REF_MISMATCH")
        if ctx.profile_document_sha256 is None:
            ld("PROFILE_DOCUMENT_NOT_BOUND")
        elif ctx.profile_document_sha256 != PROFILE_DOCUMENT_SHA256:
            issues.append(g.issue("PROFILE_DOCUMENT_MISMATCH", "/context/profile_document_sha256")); ld("PROFILE_DOCUMENT_MISMATCH")
        if ctx.profile_payload_sha256 is not None and ctx.profile_payload_sha256 == ctx.profile_document_sha256:
            issues.append(g.issue("PROFILE_PAYLOAD_CONFUSED", "/context/profile_payload_sha256")); ld("PROFILE_PAYLOAD_CONFUSED")
        if ctx.identity_profile_ref is None:
            ld("IDENTITY_PROFILE_ABSENT")
        elif ctx.identity_profile_ref != IDENTITY_PROFILE_REF:
            issues.append(g.issue("IDENTITY_PROFILE_UNSUPPORTED", "/context/identity_profile_ref")); ld("IDENTITY_PROFILE_UNSUPPORTED")
        if ctx.company is None:
            ld("COMPANY_ABSENT")
        if ctx.expected_raw_ref is None:
            ld("RAW_REF_NOT_BOUND")  # không gate content; chỉ ghi nhận chưa bind
        elif ctx.expected_raw_ref != ref:
            issues.append(g.issue("RAW_REF_MISMATCH", "/context/expected_raw_ref")); ld("RAW_REF_MISMATCH")
        f0 = ctx.resolved_invoice_measurement_facts
        if f0 is not None:
            if f0.ho_tro:
                facts = f0
            else:
                issues.append(g.issue("MEASUREMENT_FACTS_UNSUPPORTED", "/context/resolved_invoice_measurement_facts"))
    # PURE02/R2: context mâu thuẫn tường minh (raw binding / profile ref / profile document / payload nhầm document) → KHÔNG dùng fact
    # đo lường của chính context đó để cấp normalized quantity. expected_raw_ref=None chỉ là NOT_BOUND, không phải mâu thuẫn.
    if facts is not None and {"RAW_REF_MISMATCH", "PROFILE_REF_MISMATCH", "PROFILE_DOCUMENT_MISMATCH", "PROFILE_PAYLOAD_CONFUSED"} & set(ly_do):
        facts = None
        ld("MEASUREMENT_FACTS_NOT_APPLIED_CONTEXT_CONTRADICTION")
    ctx_ok = ctx is not None and not ({"PROFILE_REF_MISMATCH", "PROFILE_DOCUMENT_MISMATCH", "PROFILE_DOCUMENT_NOT_BOUND",
                                       "PROFILE_PAYLOAD_CONFUSED", "IDENTITY_PROFILE_ABSENT", "IDENTITY_PROFILE_UNSUPPORTED",
                                       "COMPANY_ABSENT", "RAW_REF_MISMATCH"} & set(ly_do))

    def ket_qua(shape, header=(), total=_ABSENT, lines=(), identity=None, env=None):
        return InvoiceReadResult(
            raw_xml=raw, raw_ref=ref, artifact_name=artifact_name, shape=shape,
            source_instance=None if ctx is None else ctx.source_instance, source_profile_ref=None if ctx is None else ctx.source_profile_ref,
            profile_document_sha256=None if ctx is None else ctx.profile_document_sha256,
            profile_payload_sha256=None if ctx is None else ctx.profile_payload_sha256,
            header_fields=tuple(header), header_total_section=total, lines=tuple(lines), canonical_identity=identity,
            semantic_envelope=env, semantic_digest=None if env is None else env.digest, issues=tuple(issues),
            candidate_reasons=tuple(ly_do), profile_payload_binding="NOT_BOUND" if ctx is None else ctx.profile_payload_binding,
            money=money, relations=relations)

    # ---- tiền kiểm bytes (không parse khi ngoài profile)
    if len(raw) > MAX_XML_BYTES:
        issues.append(g.issue("XML_TOO_LARGE", "/")); ld("INPUT_UNSUPPORTED")
        return ket_qua("UNSUPPORTED_INPUT")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in raw:
        issues.append(g.issue("XML_ENCODING_UNSUPPORTED", "/")); ld("INPUT_UNSUPPORTED")
        return ket_qua("UNSUPPORTED_INPUT")
    m = _ENCODING_DECL.match(raw)
    if m and m.group(1).decode("ascii").lower() not in ("utf-8", "utf8"):
        issues.append(g.issue("XML_ENCODING_UNSUPPORTED", "/")); ld("INPUT_UNSUPPORTED")
        return ket_qua("UNSUPPORTED_INPUT")
    if b"<!DOCTYPE" in raw:
        issues.append(g.issue("XML_DOCTYPE_UNSUPPORTED", "/")); ld("INPUT_UNSUPPORTED")
        return ket_qua("UNSUPPORTED_INPUT")
    try:
        parser = ET.XMLParser()
        parser.feed(raw)
        root = parser.close()
    except (ET.ParseError, ValueError, LookupError):
        issues.append(g.issue("XML_MALFORMED", "/")); ld("XML_MALFORMED")
        return ket_qua("XML_MALFORMED")
    if any(isinstance(el.tag, str) and el.tag.startswith("{") for el in root.iter()):
        issues.append(g.issue("UNSUPPORTED_NAMESPACE", "/")); ld("STRUCTURE_UNSUPPORTED")
        return ket_qua("UNSUPPORTED_NAMESPACE")
    if root.tag != "HDon":
        issues.append(g.issue("UNSUPPORTED_PATH", "/")); ld("STRUCTURE_UNSUPPORTED")
        return ket_qua("UNSUPPORTED_PATH")
    dl = _children(root, "DLHDon")
    if len(dl) != 1:
        issues.append(g.issue("UNSUPPORTED_PATH" if not dl else "STRUCTURE_DUPLICATE", _PATH_DLHDON)); ld("STRUCTURE_UNSUPPORTED")
        return ket_qua("UNSUPPORTED_PATH" if not dl else "STRUCTURE_DUPLICATE")
    tt, nd = _children(dl[0], "TTChung"), _children(dl[0], "NDHDon")
    if len(tt) != 1 or len(nd) != 1:
        thieu = not tt or not nd
        issues.append(g.issue("UNSUPPORTED_PATH" if thieu else "STRUCTURE_DUPLICATE", _PATH_DLHDON)); ld("STRUCTURE_UNSUPPORTED")
        return ket_qua("UNSUPPORTED_PATH" if thieu else "STRUCTURE_DUPLICATE")
    ds = _children(nd[0], "DSHHDVu")
    if len(ds) > 1:
        issues.append(g.issue("STRUCTURE_DUPLICATE", _PATH_NDHDON + "/DSHHDVu")); ld("STRUCTURE_UNSUPPORTED")
        return ket_qua("STRUCTURE_DUPLICATE")

    money = _read_money(tt, nd[0], raw, g)
    relations = _read_relations(tt, raw, g)

    # ---- phần tử/thuộc tính/text ngoài profile: giữ bằng chứng, không alias, chặn content digest
    ngoai = False

    def quet(el, path):
        nonlocal ngoai
        if el.attrib:
            issues.append(g.issue("UNSUPPORTED_ATTRIBUTE", path)); ngoai = True
        allowed = _LEGACY_ALLOWED_CHILDREN.get(el.tag)
        if allowed is None:  # leaf scalar: kiểm mixed riêng ở _field
            return
        if el.text is not None and el.text.strip():
            issues.append(g.issue("UNSUPPORTED_TEXT", path)); ngoai = True
        dem = {}
        for c in el:
            dem[c.tag] = dem.get(c.tag, 0) + 1
            cpath = f"{path}/{c.tag}" + (f"[{dem[c.tag]}]" if c.tag == "HHDVu" else "")
            if c.tail is not None and c.tail.strip():
                issues.append(g.issue("UNSUPPORTED_TEXT", path)); ngoai = True
            if c.tag not in allowed:
                issues.append(g.issue("UNSUPPORTED_ELEMENT", f"{path}/{c.tag}")); ngoai = True
                continue
            quet(c, cpath)
    quet(root, "/HDon")

    # ---- header
    header = [_field(tt, t, t, f"{_PATH_TTCHUNG}/{t}") for t in HEADER_TAGS]
    nban, nmua = _children(nd[0], "NBan"), _children(nd[0], "NMua")
    header.append(_field(nban, "MST", "NBan/MST", f"{_PATH_NDHDON}/NBan/MST"))
    header.append(_field(nmua, "MST", "NMua/MST", f"{_PATH_NDHDON}/NMua/MST"))
    mo_ho = False
    for f in header:
        if len(f.occurrences) > 1:
            issues.append(g.issue("FIELD_DUPLICATE", f.locator)); mo_ho = True
        if f.mixed_content:
            issues.append(g.issue("FIELD_MIXED_CONTENT", f.locator)); mo_ho = True
    for parent, ten in ((nban, "NBan"), (nmua, "NMua")):
        if len(parent) > 1:
            issues.append(g.issue("STRUCTURE_DUPLICATE", f"{_PATH_NDHDON}/{ten}")); mo_ho = True
    hd = {f.name: f for f in header}
    for name, ma in _HEADER_CODE.items():
        fv = hd[name].duy_nhat
        if fv is not None and fv.state in ("ABSENT", "EMPTY"):
            issues.append(g.issue(f"{ma}_{fv.state}", hd[name].locator))
    ngay = hd["NLap"].duy_nhat
    if ngay is not None and ngay.state == "TEXT":
        try:
            date_iso(ngay.lexeme)
        except DataError:
            issues.append(g.issue("DATE_INVALID", hd["NLap"].locator))
    ttoan = _children(nd[0], "TToan")
    total = _ABSENT
    if ttoan:
        total = FieldValue("EMPTY", "") if not ttoan[0].text else FieldValue("TEXT", ttoan[0].text)
        issues.append(g.issue("TOTAL_SECTION_UNSUPPORTED", f"{_PATH_NDHDON}/TToan")); ngoai = True
    if not ds:
        issues.append(g.issue("LINES_SECTION_ABSENT", f"{_PATH_NDHDON}/DSHHDVu")); ngoai = True

    # ---- dòng: trích field theo ordinal nguồn (1-based), STT chỉ là thứ tự nguồn
    rows = []
    for i, el in enumerate(_children(ds[0], "HHDVu") if ds else [], 1):
        loc = f"{_PATH_LINE}[{i}]"
        rows.append((i, loc, [_field([el], t, t, f"{loc}/{t}") for t in LINE_TAGS]))
    stt_text = {}
    for _, _, fs in rows:
        fv = fs[0].duy_nhat
        if fv is not None and fv.state == "TEXT":
            stt_text[fv.lexeme] = stt_text.get(fv.lexeme, 0) + 1

    # ---- định danh DEMO_M2_ID_DIGITS_V1 (dẫn xuất từ native + công ty cấu hình)
    identity = None
    if ctx_ok:
        mst_ban, mst_mua = _identity_text(hd["NBan/MST"].duy_nhat), _identity_text(hd["NMua/MST"].duy_nhat)
        mau, ky = _identity_text(hd["KHMSHDon"].duy_nhat), _identity_text(hd["KHHDon"].duy_nhat)
        so = hd["SHDon"].duy_nhat
        for name in ("NBan/MST", "NMua/MST", "KHMSHDon", "KHHDon"):
            fv = hd[name].duy_nhat
            if fv is not None and fv.state == "TEXT" and _identity_text(fv) is None:
                issues.append(g.issue("IDENTITY_FIELD_INVALID", hd[name].locator))
        so_chuan = None
        if so is not None and so.state == "TEXT":
            if so.lexeme.isascii() and _DIGITS.fullmatch(so.lexeme):
                so_chuan = so.lexeme.lstrip("0") or "0"  # strip bằng chuỗi; toàn 0 → "0"
            else:
                issues.append(g.issue("NUMBER_INVALID", hd["SHDon"].locator))
        key = ctx.company.source_company_key
        mua, ban = mst_mua == key, mst_ban == key
        if mua and ban:
            issues.append(g.issue("COMPANY_BOTH_SIDES", f"{_PATH_NDHDON}")); ld("COMPANY_BOTH_SIDES")
        elif not mua and not ban:
            ld("COMPANY_UNMATCHED")
        if None in (mst_ban, mau, ky, so_chuan):
            ld("IDENTITY_FIELDS_UNRESOLVED")
        if (mua != ban) and None not in (mst_ban, mau, ky, so_chuan):
            identity = (ctx.company.pn_alias, "MUA_VAO" if mua else "BAN_RA", mst_ban, mau, ky, so_chuan)

    # ---- content M2_XML_CONTENT_V1 (chỉ khi rõ ràng, trong envelope hỗ trợ, literal không nghi ngờ)
    line_mo_ho = any(len(f.occurrences) > 1 or f.mixed_content for _, _, fs in rows for f in fs)
    literal = _literal_not_proven(raw)
    if literal:
        issues.append(g.issue("XML_LITERAL_LEXEME_NOT_PROVEN", "/")); ld("XML_LITERAL_LEXEME_NOT_PROVEN")
    if mo_ho or line_mo_ho:
        ld("CONTENT_AMBIGUOUS")
    if ngoai:
        ld("CONTENT_OUTSIDE_SUPPORTED_ENVELOPE")
    env = None
    if identity is not None and not (mo_ho or line_mo_ho or ngoai or literal):
        env = InvoiceContentEnvelope(CONTENT_CONTRACT, identity, tuple(header), tuple((o, tuple(fs)) for o, _, fs in rows), total)
    elif identity is None:
        ld("IDENTITY_UNRESOLVED")

    # ---- crosswalk tường minh (chỉ khi identity + content đã dẫn xuất)
    cw_line: dict[int, LineCrosswalkFact] = {}
    if ctx is not None and ctx.line_crosswalk:
        theo_loc = {loc: o for o, loc, _ in rows}
        hop: dict[int, list] = {}
        for k, fct in enumerate(ctx.line_crosswalk):
            p = f"/context/line_crosswalk[{k}]"
            if env is None:
                issues.append(g.issue("CROSSWALK_NOT_APPLIED", p)); continue
            if fct.content_artifact_sha256 != ref.native_sha256:
                issues.append(g.issue("CROSSWALK_ARTIFACT_MISMATCH", p)); continue
            if fct.invoice_identity_binding != identity:
                issues.append(g.issue("CROSSWALK_IDENTITY_MISMATCH", p)); continue
            if theo_loc.get(fct.source_locator) != fct.source_ordinal:
                issues.append(g.issue("CROSSWALK_LOCATOR_MISMATCH", p)); continue
            hop.setdefault(fct.source_ordinal, []).append(fct)
        for o, ds_f in hop.items():
            if len(ds_f) > 1:
                issues.append(g.issue("CROSSWALK_DUPLICATE_LINE", f"{_PATH_LINE}[{o}]"))
            else:
                cw_line[o] = ds_f[0]

    # ---- dựng dòng bất biến
    lines = []
    for o, loc, fs in rows:
        fd = {f.name: f for f in fs}
        codes: list[tuple[str, str]] = []
        stt = fd["STT"]
        if len(stt.occurrences) > 1 or stt.mixed_content:
            codes.append(("STT_AMBIGUOUS", stt.locator))
        else:
            fv = stt.occurrences[0]
            if fv.state in ("ABSENT", "EMPTY"):
                codes.append((f"STT_{fv.state}", stt.locator))
            elif stt_text.get(fv.lexeme, 0) > 1:
                codes.append(("STT_DUPLICATE", stt.locator))
        if codes:
            codes.append(("LINE_IDENTITY_UNRESOLVED", loc))
        for f in fs:
            if f.name in ("STT", "TChat", "SLuong", "DGia", "ThTien", "DVTinh"):
                continue  # đã có mã riêng
            if len(f.occurrences) > 1:
                codes.append(("FIELD_DUPLICATE", f.locator))
            if f.mixed_content:
                codes.append(("FIELD_MIXED_CONTENT", f.locator))
        tc = fd["TChat"]
        if len(tc.occurrences) > 1 or tc.mixed_content:
            nature = "UNKNOWN"; codes.append(("NATURE_AMBIGUOUS", tc.locator))
        else:
            fv = tc.occurrences[0]
            if fv.state == "ABSENT":
                nature = "UNKNOWN"; codes.append(("NATURE_ABSENT", tc.locator))
            elif fv.state == "EMPTY":
                nature = "UNKNOWN"; codes.append(("NATURE_EMPTY", tc.locator))
            else:
                nature = _NATURE.get(fv.lexeme, "UNKNOWN")
                if nature == "UNKNOWN":
                    codes.append(("NATURE_UNKNOWN", tc.locator))
                elif nature == "SPECIAL_GOODS":
                    codes.append(("SPECIAL_GOODS_HOLD", tc.locator))
        qty, qc = _so(fd["SLuong"], "QUANTITY", True, True)
        codes.extend((c, fd["SLuong"].locator) for c in qc)
        dv = fd["DVTinh"]
        unit_ref = None
        if len(dv.occurrences) > 1 or dv.mixed_content:
            codes.append(("UNIT_AMBIGUOUS", dv.locator))
        else:
            fv = dv.occurrences[0]
            if fv.state in ("ABSENT", "EMPTY"):
                codes.append((f"UNIT_{fv.state}", dv.locator))
            elif facts is not None and fv.lexeme == facts.raw_unit:
                unit_ref = facts.unit_definition_ref
            else:
                codes.append(("UNIT_UNPROVEN", dv.locator))
        normalized = None
        if qty.state == "EXACT" and unit_ref is not None:
            if qty.lexical_digits <= facts.max_lexical_digits and qty.scale <= facts.max_scale:
                normalized = qty.exact_text
            else:
                codes.append(("QUANTITY_FACT_DOMAIN_EXCEEDED", fd["SLuong"].locator))
        price, pc = _so(fd["DGia"], "UNIT_PRICE", True, False)
        codes.extend((c, fd["DGia"].locator) for c in pc)
        amount, ac = _so(fd["ThTien"], "AMOUNT", False, False)
        codes.extend((c, fd["ThTien"].locator) for c in ac)
        line_issues = tuple(g.issue(c, p) for c, p in codes)
        issues.extend(line_issues)
        fct = cw_line.get(o)
        lines.append(InvoiceLine(o, loc, tuple(fs), nature, qty, price, amount, normalized, unit_ref,
                                 None if fct is None else fct.logical_line_ref, None if fct is None else fct.mapping_ref,
                                 None if fct is None else fct.continuity_ref, line_issues))

    return ket_qua("SUPPORTED_SUBSET", header, total, lines, identity, env)


# ---------------------------------------------------------------------------------------------------------------- public API
def doc_hoa_don_xml(raw: bytes, context: InvoiceReadContext | None = None, *, artifact_name: str | None = None) -> InvoiceReadResult:
    """Đọc MỘT XML (bytes thực). Lỗi nguồn → giữ raw + issues/candidate; chỉ input sai kiểu của caller mới raise DataError."""
    raw = _bytes(raw, "raw")
    ctx = _context(context)
    ref = XmlRawRef(sha256(raw), len(raw), MEDIA_XML)
    return _doc(raw, ctx, ref, _ten(artifact_name, "artifact_name"))


def doc_goi_hoa_don_zip(raw_zip: bytes, contexts: tuple = (), *, archive_name: str | None = None) -> InvoiceZipReadResult:
    """Đọc ZIP qua infolist()+open(ZipInfo) — mỗi entry giữ ordinal 1-based + tên + SHA/độ dài thực; tên trùng KHÔNG gộp. Context chỉ áp
    khi khớp đúng (container SHA, ordinal, tên entry); raw ref đầy đủ (SHA entry) được reader so lại. Coverage chỉ nói về bundle này."""
    raw = _bytes(raw_zip, "raw_zip")
    ctxs = _tuple(contexts, InvoiceReadContext, "contexts")
    name = _ten(archive_name, "archive_name")
    csha = sha256(raw)
    g = _Ghi(f"zip:{csha}")
    issues: list[InvoiceIssue] = []

    def ket_qua(entries, coverage):
        return InvoiceZipReadResult(raw, csha, len(raw), name, tuple(entries), coverage, tuple(issues))

    if len(raw) > MAX_ZIP_BYTES:
        issues.append(g.issue("ZIP_TOO_LARGE", "/"))
        return ket_qua((), "PARTIAL")
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except (zipfile.BadZipFile, zipfile.LargeZipFile, ValueError, OSError, EOFError, NotImplementedError):
        issues.append(g.issue("ZIP_MALFORMED", "/"))
        return ket_qua((), "PARTIAL")
    with zf:
        try:
            infos = zf.infolist()
        except Exception:  # noqa: BLE001 — central directory hỏng: giữ container
            issues.append(g.issue("ZIP_MALFORMED", "/"))
            return ket_qua((), "PARTIAL")
        if len(infos) > MAX_ZIP_ENTRIES:
            issues.append(g.issue("ZIP_TOO_MANY_ENTRIES", "/"))
            return ket_qua((), "PARTIAL")
        dem: dict[str, int] = {}
        for info in infos:
            dem[info.filename] = dem.get(info.filename, 0) + 1
        for ten_trung in sorted(n for n, c in dem.items() if c > 1):
            issues.append(g.issue("ZIP_DUPLICATE_ENTRY_NAME", f"/{ten_trung}"))
        # gán context theo khe (container, ordinal, tên) — không wildcard, không theo tên một mình
        khe: dict[tuple[int, str], list[InvoiceReadContext]] = {}
        for k, c in enumerate(ctxs):
            r = c.expected_raw_ref
            if (r is None or r.container_sha256 != csha or r.entry_ordinal is None or r.entry_ordinal > len(infos)
                    or infos[r.entry_ordinal - 1].filename != r.entry_name):
                issues.append(g.issue("CONTEXT_UNMATCHED", f"/contexts[{k}]")); continue
            khe.setdefault((r.entry_ordinal, r.entry_name), []).append(c)
        entries, du = [], True
        for ordinal, info in enumerate(infos, 1):
            ten = info.filename
            eg = _Ghi(f"zip:{csha}!{ordinal}:{ten}")
            if info.is_dir() or not ten.casefold().endswith(".xml"):
                entries.append(ZipEntryResult(ordinal, ten, None, None, None, (eg.issue("ZIP_ENTRY_IGNORED_NON_XML", "/"),), "IGNORED_NON_XML"))
                continue
            if info.file_size > MAX_XML_BYTES:
                du = False
                entries.append(ZipEntryResult(ordinal, ten, None, None, None, (eg.issue("ZIP_MEMBER_TOO_LARGE", "/"),), "READ_ERROR"))
                continue
            try:
                with zf.open(info) as fh:
                    data = fh.read(MAX_XML_BYTES + 1)
            except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError, EOFError, zlib.error, ValueError):
                du = False
                entries.append(ZipEntryResult(ordinal, ten, None, None, None, (eg.issue("ZIP_MEMBER_READ_ERROR", "/"),), "READ_ERROR"))
                continue
            if len(data) > MAX_XML_BYTES:
                du = False
                entries.append(ZipEntryResult(ordinal, ten, None, None, None, (eg.issue("ZIP_MEMBER_TOO_LARGE", "/"),), "READ_ERROR"))
                continue
            ref = XmlRawRef(sha256(data), len(data), MEDIA_XML, csha, ordinal, ten)
            cs = khe.get((ordinal, ten), [])
            ctx = None
            if len(cs) > 1:
                issues.append(g.issue("CONTEXT_AMBIGUOUS", f"/entry[{ordinal}]"))
            elif cs:
                ctx = cs[0]
            res = _doc(data, ctx, ref, ten)
            state = "PARSED" if res.shape == "SUPPORTED_SUBSET" else "CANDIDATE"
            if state != "PARSED":
                du = False
            entries.append(ZipEntryResult(ordinal, ten, len(data), ref.native_sha256, res, (), state))
    return ket_qua(entries, "COMPLETE" if du else "PARTIAL")
