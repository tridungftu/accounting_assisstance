"""M5 · reader THUẦN nguồn kho #10 (gói 01) — DTO ``kho10-pure-dto/v3``, contract ``kho10-content/v1`` + ``kho10-request/v1``.

Đọc native ``{phieu, lines}`` (bytes thực truyền vào) + context/history do caller tin cậy dựng (``KhoReadContext.tu_dict`` /
``KhoHistorySummary.tu_dict`` — chỉ repository/root DEMO, không native/browser). Trả candidate bất biến sâu; KHÔNG Store/K2/DB/
file/API/UI, không tính tồn/giá/sổ, không capacity/pool/budget, không duyệt/chọn current, không cache/history toàn cục.

- Raw SHA = sha256 đúng bytes truyền vào. JSON đọc strict bằng ``doc_json_chinh_xac`` (khóa lặp/NaN/Infinity bị chặn); token số
  native được bắt LẠI nguyên văn bằng parser stdlib (``parse_int``/``parse_float`` nhận chuỗi token) → ``quantity_text`` của NUMBER
  là token lexical (``1e+03`` ≠ ``str(Decimal)``), không serialize lại.
- Fingerprint: ``H(x) = sha256(canonical_json(chuan_hoa_so(x)))`` CHỈ trên envelope đã qua kiểm shape; Decimal chỉ được chuẩn hóa
  trong cây fingerprint. Graph lỗi → semantic/request NULL. Request NULL khi thiếu ref bắt buộc hoặc facts mâu thuẫn; measurement/
  proof tùy chọn chưa biết vẫn hash được (NULL tường minh) — request identity tách khỏi eligibility (precision/UOM/proof).
- Số lượng chuẩn hóa chỉ khi resolved_measurement_facts tin cậy khớp nguồn/profile/đơn vị/encoding/miền 38,12/tỉ lệ 1/1 tường minh;
  không suy 1/1, không dùng DVT_QuyDoi, không tin nhãn.
- ``phan_loai_quan_sat`` là bộ phân loại thuần: missing/mismatch/unbound/replay/conflict/fresh/reversed/reappearance; giữ đồng thời
  issue partial/precision/UOM/continuity; không đổi candidate/summary.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from ..ha_tang.primitives import DataError, canonical_json, date_iso, sha256, text_id
from .fixture import Issue, _unique_object
from .review_xay_dung import chuan_hoa_so, doc_json_chinh_xac

SEMANTIC_CONTRACT = "kho10-content/v1"
REQUEST_CONTRACT = "kho10-request/v1"
HEADER_KEYS = ("SoPhieu", "LoaiPhieu", "NgayChungTu", "MaKho", "MaDoiTac", "DienGiai", "TrangThai", "NguoiLap", "NguoiDuyet",
               "ThoiDiemDuyet", "SoPhieu_Goc")
LINE_KEYS = ("ID_Dong", "SoPhieu", "MaHang", "SoLuong", "GhiChu")
MASTER_KEYS = {"DM_HangHoa": ("MaHang", ("MaHang", "DVT_Goc", "DVT_QuyDoi")), "DM_Kho": ("MaKho", ("MaKho", "TrangThai")),
               "DM_DoiTac": ("MaDoiTac", ("MaDoiTac", "MaDoiTuong_KT"))}
REQUIRED_HEADER_TEXT = ("SoPhieu", "LoaiPhieu", "MaKho", "TrangThai")  # NgayChungTu bắt buộc, kiểm riêng bằng mã ngày
SOURCE_STATE = {"Nháp": "NHAP", "Đã duyệt": "DA_DUYET", "Đã đảo": "DA_DAO"}
SAME_UNIT = "SAME_VERIFIED_UNIT_ONLY"
DOMAIN = (38, 12)
_DIGEST = re.compile(r"[0-9a-f]{64}")
_DEC = re.compile(r"-?(\d+)(?:\.(\d+))?")
_FINITE_DEC = re.compile(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")


def la_digest(value) -> bool:
    """Digest = đúng 64 hex thường, fullmatch (không chấp nhận newline cuối, không strip/lowercase)."""
    return isinstance(value, str) and _DIGEST.fullmatch(value) is not None

GRAPH_CODES = frozenset({"INVALID_JSON", "DUPLICATE_JSON_KEY", "INVALID_TEXT_ID", "INVALID_DATE", "KHO_SHAPE", "KHO_FIELD_TYPE",
                         "KHO_LINE_ID_CONFLICT", "KHO_ORPHAN_LINE", "KHO_MASTER_GRAPH_CONFLICT", "KHO_MASTER_MISSING", "KHO_DATE_MISSING"})
REQUEST_CODES = frozenset({"KHO_CONTEXT_UNRESOLVED", "KHO_CONTEXT_SCOPE_MISMATCH", "KHO_CONTEXT_PROOF_MISMATCH"})
MEASUREMENT_CODES = frozenset({"KHO_MEASUREMENT_UNRESOLVED", "KHO_UOM_UNKNOWN", "KHO_PRECISION_UNVERIFIED", "KHO_MEASUREMENT_NOT_EXACT",
                               "KHO_CONVERSION_PROOF_MISSING"})
_INFO = frozenset({"FIRST_OBSERVATION_CANDIDATE", "REPLAY", "SAME_CONTENT_FRESH_OBSERVATION"})


# ---------------------------------------------------------------- giá trị bất biến có tag
@dataclass(frozen=True)
class FrozenObject:
    """JSON object bất biến: cặp (khóa, giá trị) theo thứ tự nguồn, khóa duy nhất. ``{}`` khác ``[]``."""
    entries: tuple

    def get(self, key, default=None):
        for k, v in self.entries:
            if k == key:
                return v
        return default

    def keys(self) -> tuple:
        return tuple(k for k, _ in self.entries)

    def __contains__(self, key) -> bool:
        return key in self.keys()


@dataclass(frozen=True)
class FrozenArray:
    """JSON array bất biến."""
    items: tuple


def dong_bang(value: Any):
    """Đóng băng sâu cây JSON (dict→FrozenObject, list→FrozenArray). Chỉ nhận scalar JSON str/int/Decimal/bool/None — float bị từ chối."""
    if isinstance(value, (FrozenObject, FrozenArray)):
        return value
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise DataError("KHO_FIELD_TYPE", "Khóa object phải là chuỗi.")
        return FrozenObject(tuple((k, dong_bang(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return FrozenArray(tuple(dong_bang(v) for v in value))
    if value is None or isinstance(value, (str, bool, int, Decimal)):
        return value
    raise DataError("KHO_FIELD_TYPE", "Giá trị không phải JSON hợp lệ (không nhận float/kiểu khác).")


def ra_json(value: Any):
    """Rã băng chỉ để dựng envelope fingerprint."""
    if isinstance(value, FrozenObject):
        return {k: ra_json(v) for k, v in value.entries}
    if isinstance(value, FrozenArray):
        return [ra_json(v) for v in value.items]
    return value


@dataclass(frozen=True)
class KhoIssue:
    """Ảnh chụp bất biến của ngữ nghĩa ``fixture.Issue`` (Issue dùng chung là mutable, không giữ lại)."""
    code: str
    message: str
    locator: str = "$"
    severity: str = "ERROR"

    @classmethod
    def tu_issue(cls, issue: Issue) -> "KhoIssue":
        return cls(str(issue.code), str(issue.message), str(issue.locator), str(issue.severity))


# ---------------------------------------------------------------- kiểm kiểu ở biên tin cậy
def _dict(value, ten) -> dict:
    if not isinstance(value, dict):
        raise DataError("KHO_SHAPE", f"{ten} phải là object.")
    return value


def _keys(d: dict, allowed, ten) -> None:
    la = sorted(set(d) - set(allowed))
    if la:
        raise DataError("KHO_SHAPE", f"{ten} có khóa ngoài DTO: {','.join(la)}.")


def _tid(value, ten):
    return None if value is None else text_id(value, ten)


def _str(value, ten):
    if value is not None and not isinstance(value, str):
        raise DataError("KHO_FIELD_TYPE", f"{ten} phải là chuỗi hoặc null.")
    return value


def _digest(value, ten):
    if value is not None and not la_digest(value):
        raise DataError("KHO_FIELD_TYPE", f"{ten} phải là SHA-256 64 hex thường hoặc null.")
    return value


def _hist_digest(value, ten):
    """Digest trong history: chuỗi hoặc null; chuỗi không phải 64 hex (vd NOT_BOUND) được giữ để classifier báo HISTORY_UNBOUND."""
    return _str(value, ten)


def _version(value, ten):
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 1):
        raise DataError("KHO_FIELD_TYPE", f"{ten} phải là số nguyên dương.")
    return value


def _get(d: dict | None, key):
    return None if d is None else d.get(key)


# ---------------------------------------------------------------- DTO context
@dataclass(frozen=True)
class LogicalSource:
    source_instance: str | None
    SoPhieu: str | None

    @classmethod
    def tu_dict(cls, d):
        if d is None:
            return None
        d = _dict(d, "logical_source_identity")
        _keys(d, ("source_instance", "SoPhieu"), "logical_source_identity")
        return cls(_tid(d.get("source_instance"), "source_instance"), _tid(d.get("SoPhieu"), "SoPhieu"))

    def ra_json(self) -> dict:
        return {"source_instance": self.source_instance, "SoPhieu": self.SoPhieu}


@dataclass(frozen=True)
class Scope:
    source_instance_id: str | None
    SoPhieu: str | None
    MaKho: str | None
    sections: tuple | None
    coverage: str | None

    @classmethod
    def tu_dict(cls, d):
        if d is None:
            return None
        d = _dict(d, "scope")
        _keys(d, ("source_instance_id", "SoPhieu", "MaKho", "sections", "coverage"), "scope")
        sec = d.get("sections")
        if sec is not None:
            if not isinstance(sec, list):
                raise DataError("KHO_FIELD_TYPE", "scope.sections phải là mảng.")
            sec = tuple(text_id(s, "scope.sections") for s in sec)
        cov = _str(d.get("coverage"), "scope.coverage")
        if cov is not None and cov not in ("FULL_FOR_SINGLE_DETAIL_AND_REFERENCED_MASTER_ONLY", "PARTIAL"):
            raise DataError("KHO_FIELD_TYPE", "scope.coverage ngoài miền DTO.")
        return cls(_tid(d.get("source_instance_id"), "scope.source_instance_id"), _tid(d.get("SoPhieu"), "scope.SoPhieu"),
                   _tid(d.get("MaKho"), "scope.MaKho"), sec, cov)


@dataclass(frozen=True)
class MappingRevision:
    reference_id: str | None
    version: int | None
    source_instance: str | None
    MaKho: str | None
    phap_nhan: str | None
    authority_origin: str | None
    actual_mapping_verification: str | None

    @classmethod
    def tu_dict(cls, d):
        if d is None:
            return None
        d = _dict(d, "mapping_revision")
        _keys(d, ("reference_id", "version", "source_instance", "MaKho", "phap_nhan", "authority_origin", "actual_mapping_verification"),
              "mapping_revision")
        return cls(_tid(d.get("reference_id"), "mapping.reference_id"), _version(d.get("version"), "mapping.version"),
                   _tid(d.get("source_instance"), "mapping.source_instance"), _tid(d.get("MaKho"), "mapping.MaKho"),
                   _tid(d.get("phap_nhan"), "mapping.phap_nhan"), _str(d.get("authority_origin"), "mapping.authority_origin"),
                   _str(d.get("actual_mapping_verification"), "mapping.actual_mapping_verification"))


@dataclass(frozen=True)
class MasterRows:
    DM_HangHoa: tuple
    DM_Kho: tuple
    DM_DoiTac: tuple

    @classmethod
    def tu_dict(cls, d):
        if d is None:
            return None
        d = _dict(d, "whitelist_rows")
        _keys(d, tuple(MASTER_KEYS), "whitelist_rows")
        out = {}
        for section, (khoa, cot) in MASTER_KEYS.items():
            rows = d.get(section, [])
            if not isinstance(rows, list):
                raise DataError("KHO_FIELD_TYPE", f"{section} phải là mảng.")
            frozen = []
            for i, r in enumerate(rows):
                r = _dict(r, f"{section}[{i}]")
                _keys(r, cot, f"{section}[{i}]")
                text_id(r.get(khoa), f"{section}.{khoa}")
                for c in cot[1:]:
                    v = r.get(c)
                    if c == "DVT_QuyDoi":
                        if v is not None and (isinstance(v, bool) or not isinstance(v, (str, int, Decimal))):
                            raise DataError("KHO_FIELD_TYPE", "DVT_QuyDoi phải là chuỗi/số/null.")
                    else:
                        _str(v, f"{section}.{c}")
                frozen.append(dong_bang(r))
            out[section] = tuple(frozen)
        return cls(**out)


@dataclass(frozen=True)
class MasterSnapshot:
    reference_id: str | None
    raw_subtree_sha256: str | None
    whitelist_rows: MasterRows | None
    actual_master_history_verification: str | None

    @classmethod
    def tu_dict(cls, d):
        if d is None:
            return None
        d = _dict(d, "master_snapshot")
        _keys(d, ("reference_id", "raw_subtree_sha256", "whitelist_rows", "actual_master_history_verification"), "master_snapshot")
        return cls(_tid(d.get("reference_id"), "master.reference_id"), _digest(d.get("raw_subtree_sha256"), "master.raw_subtree_sha256"),
                   MasterRows.tu_dict(d.get("whitelist_rows")), _str(d.get("actual_master_history_verification"), "master.verification"))


_MREF = ("profile_ref", "native_encoding_kind", "conversion_kind", "unit_definition_ref", "approved_conversion_proof_ref",
         "prior_unit_definition_ref", "master_revision_ref", "ratio_numerator_text", "ratio_denominator_text")


@dataclass(frozen=True)
class MeasurementRefs:
    profile_ref: str | None
    native_encoding_kind: str | None
    conversion_kind: str | None
    unit_definition_ref: str | None
    approved_conversion_proof_ref: str | None
    prior_unit_definition_ref: str | None
    master_revision_ref: str | None
    ratio_numerator_text: str | None
    ratio_denominator_text: str | None
    authority_origin: str | None

    @classmethod
    def tu_dict(cls, d):
        if d is None:
            return None
        d = _dict(d, "quantity_evidence")
        _keys(d, _MREF + ("authority_origin",), "quantity_evidence")
        tid = ("profile_ref", "unit_definition_ref", "approved_conversion_proof_ref", "prior_unit_definition_ref", "master_revision_ref")
        vals = {k: (_tid(d.get(k), k) if k in tid else _str(d.get(k), k)) for k in _MREF}
        return cls(**vals, authority_origin=_str(d.get("authority_origin"), "authority_origin"))

    def ra_json(self) -> dict:
        return {k: getattr(self, k) for k in _MREF}


@dataclass(frozen=True)
class ResolvedMeasurementFacts:
    declaration_ref: str | None
    source_instance: str | None
    source_profile_ref: str | None
    measurement_profile_ref: str | None
    declared_encoding_kind: str | None
    quantity_domain: tuple | None
    unit_reference_id: str | None
    unit_native_code: str | None
    ratio_measurement_profile_ref: str | None
    ratio_unit_definition_ref: str | None
    ratio_numerator_text: str | None
    ratio_denominator_text: str | None
    authority_origin: str | None

    @classmethod
    def tu_dict(cls, d):
        if d is None:
            return None
        d = _dict(d, "resolved_measurement_facts")
        _keys(d, ("declaration_ref", "source_instance", "source_profile_ref", "measurement_profile_ref", "declared_encoding_kind",
                  "quantity_domain", "unit_definition", "same_unit_ratio_evidence", "authority_origin"), "resolved_measurement_facts")
        dom = d.get("quantity_domain")
        if dom is not None:
            dom = _dict(dom, "quantity_domain")
            _keys(dom, ("precision", "scale"), "quantity_domain")
            dom = (_version(dom.get("precision"), "precision"), _version(dom.get("scale"), "scale"))
        unit = d.get("unit_definition")
        if unit is not None:
            unit = _dict(unit, "unit_definition")
            _keys(unit, ("reference_id", "native_unit_code"), "unit_definition")
        ratio = d.get("same_unit_ratio_evidence")
        if ratio is not None:
            ratio = _dict(ratio, "same_unit_ratio_evidence")
            _keys(ratio, ("measurement_profile_ref", "unit_definition_ref", "numerator_text", "denominator_text"), "same_unit_ratio_evidence")
        return cls(_tid(d.get("declaration_ref"), "declaration_ref"), _tid(d.get("source_instance"), "source_instance"),
                   _tid(d.get("source_profile_ref"), "source_profile_ref"), _tid(d.get("measurement_profile_ref"), "measurement_profile_ref"),
                   _str(d.get("declared_encoding_kind"), "declared_encoding_kind"), dom,
                   _tid(_get(unit, "reference_id"), "unit.reference_id"), _tid(_get(unit, "native_unit_code"), "unit.native_unit_code"),
                   _tid(_get(ratio, "measurement_profile_ref"), "ratio.measurement_profile_ref"),
                   _tid(_get(ratio, "unit_definition_ref"), "ratio.unit_definition_ref"),
                   _str(_get(ratio, "numerator_text"), "ratio.numerator_text"), _str(_get(ratio, "denominator_text"), "ratio.denominator_text"),
                   _str(d.get("authority_origin"), "authority_origin"))


_CTX_KEYS = ("authority_ref", "authority_origin", "actual_source_verification", "logical_source_identity", "receipt_id", "profile_ref",
             "source_code_sha256", "scope_ref", "scope", "capture_consistency_claim", "mapping_revision", "master_snapshot",
             "quantity_evidence", "resolved_measurement_facts", "actual_profile_proof_deployment", "capture_ref", "source_revision_token",
             "source_as_of", "server_known_at", "reported_capture_errors", "request_digest", "request_binding_state")


@dataclass(frozen=True)
class KhoReadContext:
    authority_ref: str | None
    authority_origin: str | None
    actual_source_verification: str | None
    logical_source_identity: LogicalSource | None
    receipt_id: str | None
    profile_ref: str | None
    source_code_sha256: str | None
    scope_ref: str | None
    scope: Scope | None
    capture_consistency_claim: str | None
    mapping_revision: MappingRevision | None
    master_snapshot: MasterSnapshot | None
    quantity_evidence: MeasurementRefs | None
    resolved_measurement_facts: ResolvedMeasurementFacts | None
    actual_profile_proof_deployment: str | None
    capture_ref: str | None
    source_revision_token: str | None
    source_as_of: str | None
    server_known_at: str | None
    reported_capture_errors: tuple
    request_binding_state: str | None

    @classmethod
    def tu_dict(cls, d: dict) -> "KhoReadContext":
        """CHỈ cho caller tin cậy (repository/root DEMO). Container/kiểu sai hoặc khóa lạ → DataError; ref nghiệp vụ thiếu/null giữ NULL."""
        d = _dict(d, "context")
        _keys(d, _CTX_KEYS, "context")
        if d.get("request_digest") is not None:
            raise DataError("KHO_FIELD_TYPE", "request_digest chỉ là placeholder null; digest do reader tính, không nhận từ caller.")
        errs = d.get("reported_capture_errors", [])  # chỉ VẮNG mới mặc định rỗng; null hiện diện là container sai
        if not isinstance(errs, list):
            raise DataError("KHO_FIELD_TYPE", "reported_capture_errors phải là mảng (null tường minh không được coi là rỗng).")
        return cls(
            _tid(d.get("authority_ref"), "authority_ref"), _str(d.get("authority_origin"), "authority_origin"),
            _str(d.get("actual_source_verification"), "actual_source_verification"), LogicalSource.tu_dict(d.get("logical_source_identity")),
            _tid(d.get("receipt_id"), "receipt_id"), _tid(d.get("profile_ref"), "profile_ref"),
            _digest(d.get("source_code_sha256"), "source_code_sha256"), _tid(d.get("scope_ref"), "scope_ref"), Scope.tu_dict(d.get("scope")),
            _str(d.get("capture_consistency_claim"), "capture_consistency_claim"), MappingRevision.tu_dict(d.get("mapping_revision")),
            MasterSnapshot.tu_dict(d.get("master_snapshot")), MeasurementRefs.tu_dict(d.get("quantity_evidence")),
            ResolvedMeasurementFacts.tu_dict(d.get("resolved_measurement_facts")),
            _str(d.get("actual_profile_proof_deployment"), "actual_profile_proof_deployment"), _tid(d.get("capture_ref"), "capture_ref"),
            _str(d.get("source_revision_token"), "source_revision_token"), _str(d.get("source_as_of"), "source_as_of"),
            _str(d.get("server_known_at"), "server_known_at"), tuple(text_id(e, "reported_capture_errors") for e in errs),
            _str(d.get("request_binding_state"), "request_binding_state"))


# ---------------------------------------------------------------- DTO history
@dataclass(frozen=True)
class ReceiptSeen:
    receipt_id: str
    request_digest: str | None
    content_digest: str | None
    content_reference_id: str | None
    request_reference_id: str | None
    binding_state: str | None


@dataclass(frozen=True)
class AcceptedSource:
    content_digest: str | None
    observation_ref: str
    source_state: str
    content_reference_id: str | None
    actual_event_history_verification: str | None


@dataclass(frozen=True)
class ContentReference:
    reference_id: str
    logical_source_identity: LogicalSource
    native_raw_sha256: str | None
    master_raw_subtree_sha256: str | None
    semantic_digest: str | None
    binding_state: str | None


@dataclass(frozen=True)
class OldLineBasis:
    native_line_id: str
    unit_definition_ref: str
    basis_ref: str
    proof_ref: str
    proof_authority: str | None
    actual_source_proof_verification: str | None


_HIST_KEYS = ("summary_kind", "authority_ref", "logical_source_identity", "scope_ref", "profile_ref", "receipts_seen", "seen_content_references",
              "seen_content_digests", "accepted_source", "old_line_unit_basis_refs", "digest_binding_state", "actual_repository_state")


def _mang(d, key) -> list:
    v = d.get(key)
    if not isinstance(v, list):
        raise DataError("KHO_FIELD_TYPE", f"{key} phải là mảng.")
    return v


@dataclass(frozen=True)
class KhoHistorySummary:
    summary_kind: str
    authority_ref: str
    logical_source_identity: LogicalSource
    scope_ref: str
    profile_ref: str
    receipts_seen: tuple
    seen_content_references: tuple
    seen_content_digests: tuple
    accepted_source: AcceptedSource | None
    old_line_unit_basis_refs: tuple
    digest_binding_state: str
    actual_repository_state: str

    @classmethod
    def tu_dict(cls, d: dict) -> "KhoHistorySummary":
        """CHỈ cho caller tin cậy. Mọi khóa bắt buộc có mặt; ``None`` (không có summary) do caller truyền riêng, khác EXPLICIT_EMPTY."""
        d = _dict(d, "history")
        _keys(d, _HIST_KEYS, "history")
        thieu = [k for k in _HIST_KEYS if k not in d]
        if thieu:
            raise DataError("KHO_SHAPE", "history thiếu khóa: " + ",".join(thieu))
        kind = d["summary_kind"]
        if kind not in ("EXPLICIT_EMPTY", "SYNTHETIC_PRIOR_STATE", "REPOSITORY_PRIOR_STATE"):
            raise DataError("KHO_FIELD_TYPE", "summary_kind ngoài miền DTO.")
        logical = LogicalSource.tu_dict(_dict(d["logical_source_identity"], "logical_source_identity"))
        receipts = []
        for r in _mang(d, "receipts_seen"):
            r = _dict(r, "receipts_seen[]")
            _keys(r, ("receipt_id", "request_digest", "content_digest", "content_reference_id", "request_reference_id", "binding_state"), "receipt")
            receipts.append(ReceiptSeen(text_id(r.get("receipt_id"), "receipt_id"), _hist_digest(r.get("request_digest"), "request_digest"),
                                        _hist_digest(r.get("content_digest"), "content_digest"), _tid(r.get("content_reference_id"), "content_reference_id"),
                                        _tid(r.get("request_reference_id"), "request_reference_id"), _str(r.get("binding_state"), "binding_state")))
        refs = []
        for r in _mang(d, "seen_content_references"):
            r = _dict(r, "seen_content_references[]")
            _keys(r, ("reference_id", "logical_source_identity", "native_raw_sha256", "master_raw_subtree_sha256", "semantic_digest", "binding_state"),
                  "content_reference")
            refs.append(ContentReference(text_id(r.get("reference_id"), "reference_id"),
                                         LogicalSource.tu_dict(_dict(r.get("logical_source_identity"), "logical_source_identity")),
                                         _hist_digest(r.get("native_raw_sha256"), "native_raw_sha256"),
                                         _hist_digest(r.get("master_raw_subtree_sha256"), "master_raw_subtree_sha256"),
                                         _hist_digest(r.get("semantic_digest"), "semantic_digest"), _str(r.get("binding_state"), "binding_state")))
        seen = tuple(_hist_digest(x, "seen_content_digests") for x in _mang(d, "seen_content_digests"))
        acc = d.get("accepted_source")
        if acc is not None:
            acc = _dict(acc, "accepted_source")
            _keys(acc, ("content_digest", "observation_ref", "source_state", "content_reference_id", "actual_event_history_verification"), "accepted_source")
            if acc.get("source_state") not in ("NHAP", "DA_DUYET", "DA_DAO", "CHUA_MAP"):
                raise DataError("KHO_FIELD_TYPE", "accepted_source.source_state ngoài miền DTO.")
            acc = AcceptedSource(_hist_digest(acc.get("content_digest"), "content_digest"), text_id(acc.get("observation_ref"), "observation_ref"),
                                 acc["source_state"], _tid(acc.get("content_reference_id"), "content_reference_id"),
                                 _str(acc.get("actual_event_history_verification"), "verification"))
        basis = []
        for r in _mang(d, "old_line_unit_basis_refs"):
            r = _dict(r, "old_line_unit_basis_refs[]")
            _keys(r, ("native_line_id", "unit_definition_ref", "basis_ref", "proof_ref", "proof_authority", "actual_source_proof_verification"), "basis")
            basis.append(OldLineBasis(text_id(r.get("native_line_id"), "native_line_id"), text_id(r.get("unit_definition_ref"), "unit_definition_ref"),
                                      text_id(r.get("basis_ref"), "basis_ref"), text_id(r.get("proof_ref"), "proof_ref"),
                                      _str(r.get("proof_authority"), "proof_authority"), _str(r.get("actual_source_proof_verification"), "verification")))
        return cls(kind, text_id(d["authority_ref"], "authority_ref"), logical, text_id(d["scope_ref"], "scope_ref"),
                   text_id(d["profile_ref"], "profile_ref"), tuple(receipts), tuple(refs), seen, acc, tuple(basis),
                   _str(d["digest_binding_state"], "digest_binding_state") or "", _str(d["actual_repository_state"], "actual_repository_state") or "")


# ---------------------------------------------------------------- kết quả reader
@dataclass(frozen=True)
class NativeLine:
    logical_key: tuple | None
    source_ordinal: int
    native_values: Any
    quantity_json_kind: str
    quantity_text: str | None
    normalized_quantity_text: str | None
    precision_state: str
    unit_definition_ref: str | None


@dataclass(frozen=True)
class KhoReadResult:
    raw_sha256: str
    semantic_contract: str
    request_contract: str
    receipt_id: str | None
    source_profile_ref: str | None
    scope_ref: str | None
    logical_source_identity: LogicalSource | None
    semantic_digest: str | None
    request_digest: str | None
    native_header: FrozenObject | None
    business_date: str | None
    lines: tuple
    scope: Scope | None
    master_snapshot_ref: str | None
    measurement_refs: MeasurementRefs | None
    issues: tuple
    semantic_envelope: FrozenObject | None
    request_envelope: FrozenObject | None
    master_raw_subtree_sha256: str | None
    source_state: str | None
    candidate_only: bool = True

    def ma_loi(self) -> tuple:
        return tuple(dict.fromkeys(i.code for i in self.issues))


@dataclass(frozen=True)
class KhoClassification:
    reason_codes: tuple
    needs_review: bool
    history_state: str


def H(envelope) -> str:
    """Fingerprint contract: sha256(canonical_json(chuan_hoa_so(envelope)).encode('utf-8'))."""
    return sha256(canonical_json(chuan_hoa_so(envelope)).encode("utf-8"))


# ---------------------------------------------------------------- token số nguyên văn (stdlib)
@dataclass(frozen=True)
class _So:
    text: str


def _token_so(content: bytes):
    """Parse lại để giữ token số nguyên văn (parser stdlib đưa chuỗi token cho parse_int/parse_float). Gọi SAU doc_json_chinh_xac."""
    return json.loads(content.decode("utf-8-sig"), object_pairs_hook=_unique_object, parse_int=_So, parse_float=_So,
                      parse_constant=lambda _: (_ for _ in ()).throw(DataError("INVALID_JSON", "JSON chứa NaN/Infinity.")))


# ---------------------------------------------------------------- reader
def doc_phieu_kho(content: bytes, context: KhoReadContext) -> KhoReadResult:
    if not isinstance(content, (bytes, bytearray)) or not isinstance(context, KhoReadContext):
        raise DataError("KHO_SHAPE", "Reader nhận bytes native và KhoReadContext tin cậy.")
    content = bytes(content)
    raw_sha = sha256(content)
    issues: list[KhoIssue] = []

    def add(code, msg, loc="$", sev="ERROR"):
        issues.append(KhoIssue(code, msg, loc, sev))

    ctx = context
    rong = dict(raw_sha256=raw_sha, semantic_contract=SEMANTIC_CONTRACT, request_contract=REQUEST_CONTRACT, receipt_id=ctx.receipt_id,
                source_profile_ref=ctx.profile_ref, scope_ref=ctx.scope_ref, logical_source_identity=ctx.logical_source_identity,
                scope=ctx.scope, master_snapshot_ref=ctx.master_snapshot.reference_id if ctx.master_snapshot else None,
                measurement_refs=ctx.quantity_evidence,
                master_raw_subtree_sha256=ctx.master_snapshot.raw_subtree_sha256 if ctx.master_snapshot else None)
    try:
        value = doc_json_chinh_xac(content)
        tokens = _token_so(content)
    except DataError as exc:
        add(exc.code if exc.code in GRAPH_CODES else "INVALID_JSON", "JSON native không đọc được strict.", "$")
        return KhoReadResult(**rong, semantic_digest=None, request_digest=None, native_header=None, business_date=None, lines=(),
                             issues=tuple(issues), semantic_envelope=None, request_envelope=None, source_state=None)

    graph_ok = True
    if not isinstance(value, dict) or set(value) != {"phieu", "lines"}:
        add("KHO_SHAPE", "Native phải là object đúng hai khóa {phieu, lines} (không wrapper/metadata).", "$")
        graph_ok = False
    phieu = value.get("phieu") if isinstance(value, dict) else None
    lines_raw = value.get("lines") if isinstance(value, dict) else None

    # header
    header, business_date, so_phieu, ma_kho, ma_dt, source_state = None, None, None, None, None, None
    if isinstance(phieu, dict):
        header = dong_bang(phieu)
        for k in phieu:
            if k not in HEADER_KEYS:
                add("KHO_SHAPE", "Header có khóa ngoài whitelist (giữ raw, cần review profile).", f"/phieu/{k}")
                graph_ok = False
        bat_buoc = {}
        for k in REQUIRED_HEADER_TEXT:  # kiểm TRƯỚC lookup/hash; object/array/null/rỗng không bao giờ tới SOURCE_STATE
            if k not in phieu:
                add("KHO_SHAPE", f"Header thiếu trường bắt buộc {k}.", f"/phieu/{k}")
                graph_ok = False
                continue
            try:
                bat_buoc[k] = text_id(phieu[k], k)
            except DataError:
                add("INVALID_TEXT_ID", f"{k} phải là chuỗi không rỗng nguyên văn.", f"/phieu/{k}")
                graph_ok = False
        so_phieu, ma_kho = bat_buoc.get("SoPhieu"), bat_buoc.get("MaKho")
        trang_thai = bat_buoc.get("TrangThai")
        if trang_thai is not None:
            source_state = SOURCE_STATE.get(trang_thai)
            if source_state is None:
                source_state = "CHUA_MAP"
                add("KHO_FIELD_TYPE", "TrangThai nguồn chưa map — giữ nguyên giá trị, không suy duyệt/đủ điều kiện.", "/phieu/TrangThai", "HOLD")
        dt = phieu.get("MaDoiTac")
        if dt not in (None, ""):
            try:
                ma_dt = text_id(dt, "MaDoiTac")
            except DataError:
                add("INVALID_TEXT_ID", "MaDoiTac không hợp lệ.", "/phieu/MaDoiTac")
                graph_ok = False
        ngay = phieu.get("NgayChungTu")
        if ngay in (None, ""):
            add("KHO_DATE_MISSING", "Thiếu NgayChungTu — không suy ngày.", "/phieu/NgayChungTu")
            graph_ok = False
        else:
            try:
                business_date = date_iso(ngay)
            except DataError:
                add("INVALID_DATE", "NgayChungTu không hợp lệ — không tạo ngày giả.", "/phieu/NgayChungTu")
                graph_ok = False
        for k in HEADER_KEYS:
            if k in phieu and k not in REQUIRED_HEADER_TEXT + ("MaDoiTac", "NgayChungTu") and not (phieu[k] is None or isinstance(phieu[k], str)):
                add("KHO_FIELD_TYPE", "Trường header phải là chuỗi/null.", f"/phieu/{k}")
                graph_ok = False
    elif isinstance(value, dict) and "phieu" in value:
        add("KHO_SHAPE", "phieu phải là object.", "/phieu")
        graph_ok = False

    logical = ctx.logical_source_identity
    si = logical.source_instance if logical else None
    logical_ok = bool(logical and logical.source_instance and logical.SoPhieu)
    if not logical_ok:
        add("KHO_CONTEXT_UNRESOLVED", "Thiếu logical source identity tin cậy.", "/context/logical_source_identity", "HOLD")
    elif so_phieu is not None and logical.SoPhieu != so_phieu:
        add("KHO_CONTEXT_SCOPE_MISMATCH", "Logical SoPhieu khác SoPhieu native.", "/context/logical_source_identity", "HOLD")
        logical_ok = False

    # lines
    lines: list[NativeLine] = []
    raw_lines_ok: list[dict] = []
    if isinstance(lines_raw, list):
        tok_lines = tokens.get("lines") if isinstance(tokens, dict) else None
        ids = [ln.get("ID_Dong") for ln in lines_raw if isinstance(ln, dict)]
        dup = {x for x in ids if isinstance(x, str) and ids.count(x) > 1}
        for i, ln in enumerate(lines_raw):
            loc = f"/lines/{i}"
            if not isinstance(ln, dict):
                add("KHO_SHAPE", "Dòng phải là object.", loc)
                graph_ok = False
                lines.append(NativeLine(None, i, dong_bang(ln), "INVALID", None, None, "UNKNOWN", None))
                continue
            for k in ln:
                if k not in LINE_KEYS:
                    add("KHO_SHAPE", "Dòng có khóa ngoài whitelist.", f"{loc}/{k}")
                    graph_ok = False
            line_id = None
            try:
                line_id = text_id(ln.get("ID_Dong"), "ID_Dong")
            except DataError:
                add("INVALID_TEXT_ID", "ID_Dong không hợp lệ.", f"{loc}/ID_Dong")
                graph_ok = False
            if line_id in dup:
                add("KHO_LINE_ID_CONFLICT", "ID_Dong lặp — không chọn dòng cuối, không thay bằng STT.", f"{loc}/ID_Dong")
                graph_ok = False
            try:
                sp = text_id(ln.get("SoPhieu"), "SoPhieu")
                if so_phieu is not None and sp != so_phieu:
                    add("KHO_ORPHAN_LINE", "Dòng thuộc SoPhieu khác header.", f"{loc}/SoPhieu")
                    graph_ok = False
            except DataError:
                add("INVALID_TEXT_ID", "SoPhieu dòng không hợp lệ.", f"{loc}/SoPhieu")
                graph_ok = False
            try:
                text_id(ln.get("MaHang"), "MaHang")
            except DataError:
                add("INVALID_TEXT_ID", "MaHang không hợp lệ.", f"{loc}/MaHang")
                graph_ok = False
            if "GhiChu" in ln and not (ln["GhiChu"] is None or isinstance(ln["GhiChu"], str)):
                add("KHO_FIELD_TYPE", "GhiChu phải là chuỗi/null.", f"{loc}/GhiChu")
                graph_ok = False
            q = ln.get("SoLuong")
            if "SoLuong" not in ln:
                kind, qtext = "NULL", None
                add("KHO_SHAPE", "Thiếu khóa SoLuong (khác null tường minh).", f"{loc}/SoLuong")
                graph_ok = False
            elif q is None:
                kind, qtext = "NULL", None
            elif isinstance(q, bool):
                kind, qtext = "INVALID", None
            elif isinstance(q, str):
                kind, qtext = "STRING", q
                if not _FINITE_DEC.fullmatch(q):  # graph: kiểm cú pháp thập phân hữu hạn TRƯỚC envelope/H, giữ nguyên text
                    add("KHO_FIELD_TYPE", "SoLuong dạng chuỗi không phải số thập phân hữu hạn (giữ nguyên văn bản).", f"{loc}/SoLuong")
                    graph_ok = False
            elif isinstance(q, (int, Decimal)):
                kind = "NUMBER"
                tk = tok_lines[i].get("SoLuong") if isinstance(tok_lines, list) and isinstance(tok_lines[i], dict) else None
                qtext = tk.text if isinstance(tk, _So) else None
            else:
                kind, qtext = "INVALID", None
            if kind == "INVALID":
                add("KHO_FIELD_TYPE", "SoLuong không phải chuỗi/số/null (giữ nguyên giá trị, không ép null).", f"{loc}/SoLuong")
                graph_ok = False
            key = (si, so_phieu, line_id) if logical_ok and so_phieu and line_id else None
            lines.append(NativeLine(key, i, dong_bang(ln), kind, qtext, None, "UNKNOWN", None))
            raw_lines_ok.append(ln)
    elif isinstance(value, dict) and "lines" in value:
        add("KHO_SHAPE", "lines phải là mảng.", "/lines")
        graph_ok = False

    # master facts (chỉ khóa được tham chiếu)
    master = ctx.master_snapshot
    rows = master.whitelist_rows if master else None
    related = None
    master_ok = rows is not None
    if not master_ok:
        add("KHO_CONTEXT_UNRESOLVED", "Thiếu master snapshot tin cậy.", "/context/master_snapshot", "HOLD")
    elif graph_ok:
        can = {"DM_HangHoa": sorted({ln.get("MaHang") for ln in raw_lines_ok if isinstance(ln.get("MaHang"), str)}),
               "DM_Kho": [ma_kho] if ma_kho else [], "DM_DoiTac": [ma_dt] if ma_dt else []}
        related = {}
        for section, (khoa, _) in MASTER_KEYS.items():
            out = []
            for ma in sorted(can[section]):
                hit = [r for r in getattr(rows, section) if r.get(khoa) == ma]
                if not hit:
                    add("KHO_MASTER_MISSING", f"Thiếu dòng master {section} được tham chiếu.", f"/context/master_snapshot/{section}")
                    master_ok = False
                elif len(hit) > 1:
                    add("KHO_MASTER_GRAPH_CONFLICT", f"Master {section} lặp khóa được tham chiếu (kể cả giống hệt).", f"/context/master_snapshot/{section}")
                    master_ok = False
                else:
                    out.append(ra_json(hit[0]))
            related[section] = out

    semantic_env = semantic = None
    if graph_ok and logical_ok and master_ok and related is not None:
        semantic_env = {"contract": SEMANTIC_CONTRACT, "logical_source": {"source_instance": si, "SoPhieu": so_phieu},
                        "native_header": {k: phieu[k] for k in HEADER_KEYS if k in phieu},
                        "ordered_native_lines": [{k: ln[k] for k in LINE_KEYS if k in ln} for ln in raw_lines_ok],
                        "related_master_facts": related}
        semantic = H(semantic_env)
        if master.raw_subtree_sha256 == semantic:
            add("KHO_CONTEXT_PROOF_MISMATCH", "Master raw SHA không được là alias semantic SHA.", "/context/master_snapshot", "HOLD")

    # measurement + request
    qe, facts = ctx.quantity_evidence, ctx.resolved_measurement_facts
    kinds = tuple(ln.quantity_json_kind for ln in lines)
    proof_mismatch = _facts_mau_thuan(ctx, si, rows, raw_lines_ok, kinds) if facts is not None else False
    if proof_mismatch:
        add("KHO_CONTEXT_PROOF_MISMATCH", "Resolved measurement facts mâu thuẫn nguồn/profile/đơn vị/encoding/tỉ lệ.", "/context/resolved_measurement_facts", "HOLD")
    request_env = request = None
    if semantic is not None:
        thieu, lech = _kiem_request(ctx, si, so_phieu, ma_kho)
        for loc in thieu:
            add("KHO_CONTEXT_UNRESOLVED", "Thiếu ref bắt buộc cho request.", loc, "HOLD")
        for loc in lech:
            add("KHO_CONTEXT_SCOPE_MISMATCH", "Ref context không khớp logical/scope/header.", loc, "HOLD")
        if not thieu and not lech and not proof_mismatch and not any(i.code == "KHO_CONTEXT_PROOF_MISMATCH" for i in issues):
            sc, mp = ctx.scope, ctx.mapping_revision
            request_env = {
                "contract": REQUEST_CONTRACT, "logical_source": semantic_env["logical_source"], "native_raw_sha256": raw_sha,
                "semantic_digest": semantic, "source_profile_ref": ctx.profile_ref,
                "source_scope": {"source_instance": sc.source_instance_id, "SoPhieu": sc.SoPhieu, "MaKho": sc.MaKho,
                                 "sections": sorted(set(sc.sections)), "coverage": sc.coverage},
                "capture_consistency": {"claim": ctx.capture_consistency_claim, "reported_errors": sorted(set(ctx.reported_capture_errors))},
                "mapping_revision": {"reference_id": mp.reference_id, "version": mp.version, "source_instance": mp.source_instance,
                                     "MaKho": mp.MaKho, "phap_nhan": mp.phap_nhan},
                "master_snapshot": {"reference_id": master.reference_id, "raw_subtree_sha256": master.raw_subtree_sha256},
                "measurement_refs": qe.ra_json() if qe else {k: None for k in _MREF}}
            request = H(request_env)

    # đo lường từng dòng (không ảnh hưởng request identity)
    lines = _do_luong(lines, ctx, facts, proof_mismatch, rows, add)
    if ctx.scope and ctx.scope.coverage == "PARTIAL" or ctx.reported_capture_errors:
        add("KHO_SOURCE_PARTIAL", "Snapshot nguồn một phần — thiếu dòng không chứng minh xóa/hủy.", "/context/scope/coverage", "HOLD")
    if source_state == "DA_DAO":
        add("KHO_SOURCE_REVERSED", "Phiếu nguồn ở trạng thái Đã đảo — không đủ điều kiện, không sinh phiếu âm.", "/phieu/TrangThai", "HOLD")

    return KhoReadResult(**rong, semantic_digest=semantic, request_digest=request, native_header=header, business_date=business_date,
                         lines=tuple(lines), issues=tuple(issues), semantic_envelope=dong_bang(semantic_env) if semantic_env else None,
                         request_envelope=dong_bang(request_env) if request_env else None, source_state=source_state)


def _kiem_request(ctx: KhoReadContext, si, so_phieu, ma_kho) -> tuple[list, list]:
    thieu, lech = [], []
    if ctx.profile_ref is None:
        thieu.append("/context/profile_ref")
    if ctx.scope_ref is None:
        thieu.append("/context/scope_ref")
    sc = ctx.scope
    if sc is None or None in (sc.source_instance_id, sc.SoPhieu, sc.MaKho, sc.sections, sc.coverage):
        thieu.append("/context/scope")
    elif (sc.source_instance_id, sc.SoPhieu, sc.MaKho) != (si, so_phieu, ma_kho):
        lech.append("/context/scope")
    mp = ctx.mapping_revision
    if mp is None or None in (mp.reference_id, mp.version, mp.source_instance, mp.MaKho, mp.phap_nhan):
        thieu.append("/context/mapping_revision")
    elif (mp.source_instance, mp.MaKho) != (si, ma_kho):
        lech.append("/context/mapping_revision")
    ms = ctx.master_snapshot
    if ms is None or ms.reference_id is None or ms.raw_subtree_sha256 is None:
        thieu.append("/context/master_snapshot")
    return thieu, lech


def _facts_mau_thuan(ctx: KhoReadContext, si, rows, raw_lines, kinds) -> bool:
    """True nếu payload resolved hiện diện nhưng KHÔNG khớp nguồn/profile/đơn vị/encoding/miền/tỉ lệ (không tin nhãn/spelling).

    Encoding khai báo phải khớp loại token THỰC: exact-text mà có dòng Number thực là mâu thuẫn → cả candidate không chuẩn hóa."""
    f, qe = ctx.resolved_measurement_facts, ctx.quantity_evidence
    if f.declared_encoding_kind == "EXACT_TEXT_SYNTHETIC_ONLY" and "NUMBER" in kinds:
        return True
    if qe is None or None in (f.declaration_ref, f.source_instance, f.source_profile_ref, f.measurement_profile_ref, f.declared_encoding_kind,
                              f.quantity_domain, f.unit_reference_id, f.unit_native_code, f.ratio_measurement_profile_ref,
                              f.ratio_unit_definition_ref, f.ratio_numerator_text, f.ratio_denominator_text):
        return True
    if f.source_instance != si or f.source_profile_ref != ctx.profile_ref or f.measurement_profile_ref != qe.profile_ref:
        return True
    if f.declared_encoding_kind != qe.native_encoding_kind or f.quantity_domain != DOMAIN:
        return True
    if f.unit_reference_id != qe.unit_definition_ref or f.ratio_unit_definition_ref != f.unit_reference_id:
        return True
    if f.ratio_measurement_profile_ref != f.measurement_profile_ref:
        return True
    if qe.conversion_kind == SAME_UNIT and ((f.ratio_numerator_text, f.ratio_denominator_text) != ("1", "1")
                                            or (qe.ratio_numerator_text, qe.ratio_denominator_text) != ("1", "1")):
        return True
    if rows is not None:  # đơn vị gốc của MỌI hàng được tham chiếu phải đúng native unit của định nghĩa
        for ma in {ln.get("MaHang") for ln in raw_lines if isinstance(ln.get("MaHang"), str)}:
            hit = [r for r in rows.DM_HangHoa if r.get("MaHang") == ma]
            if len(hit) == 1 and hit[0].get("DVT_Goc") != f.unit_native_code:
                return True
    return False


def _do_luong(lines, ctx, facts, proof_mismatch, rows, add) -> list:
    qe = ctx.quantity_evidence
    coherent = facts is not None and not proof_mismatch and qe is not None and qe.conversion_kind == SAME_UNIT
    if facts is None:
        add("KHO_MEASUREMENT_UNRESOLVED", "Chưa có resolved measurement facts tin cậy — số lượng chuẩn hóa NULL/HOLD.",
            "/context/resolved_measurement_facts", "HOLD")
    elif not proof_mismatch and qe is not None and qe.conversion_kind != SAME_UNIT and qe.approved_conversion_proof_ref is None:
        add("KHO_CONVERSION_PROOF_MISSING", "Khác đơn vị cần proof chuyển đổi đã duyệt — chưa có.", "/context/quantity_evidence", "HOLD")
    don_vi = {}
    if rows is not None:
        for r in rows.DM_HangHoa:
            don_vi.setdefault(r.get("MaHang"), []).append(r.get("DVT_Goc"))
    out = []
    for ln in lines:
        nv = ln.native_values
        loc = f"/lines/{ln.source_ordinal}"
        ma = nv.get("MaHang") if isinstance(nv, FrozenObject) else None
        dvt = don_vi.get(ma, [])
        if isinstance(nv, FrozenObject) and len(dvt) == 1 and dvt[0] in (None, ""):
            add("KHO_UOM_UNKNOWN", "Đơn vị gốc rỗng/thiếu — không mặc định đơn vị/tỉ lệ.", loc, "HOLD")
            coherent_line = False
        else:
            coherent_line = coherent
        norm, state = None, "UNKNOWN"
        if ln.quantity_json_kind == "NUMBER":
            state = "UNPROVEN"
            add("KHO_PRECISION_UNVERIFIED", "Số JSON Number: độ chính xác nguồn chưa chứng minh (Decimal không phục hồi).", f"{loc}/SoLuong", "HOLD")
            if coherent_line:
                add("KHO_MEASUREMENT_NOT_EXACT", "Encoding khai báo không khớp loại token thực.", f"{loc}/SoLuong", "HOLD")
        elif ln.quantity_json_kind == "STRING" and coherent_line and facts.declared_encoding_kind == "EXACT_TEXT_SYNTHETIC_ONLY":
            m = _DEC.fullmatch(ln.quantity_text)
            if not m:
                add("KHO_MEASUREMENT_NOT_EXACT", "Chuỗi số lượng không phải thập phân chính xác.", f"{loc}/SoLuong", "HOLD")
            elif len(m.group(1).lstrip("0") or "0") > DOMAIN[0] - DOMAIN[1] or len(m.group(2) or "") > DOMAIN[1]:
                state = "OUT_OF_DOMAIN"
                add("KHO_MEASUREMENT_NOT_EXACT", "Số lượng ngoài miền 38,12 — không làm tròn/cắt.", f"{loc}/SoLuong", "HOLD")
            else:
                norm, state = ln.quantity_text, "EXACT_SYNTHETIC_DEMO"
        elif ln.quantity_json_kind in ("NULL", "INVALID") and coherent_line:
            add("KHO_MEASUREMENT_NOT_EXACT", "Số lượng null/không hợp lệ — không phải 0.", f"{loc}/SoLuong", "HOLD")
        unit = facts.unit_reference_id if coherent_line else None
        out.append(NativeLine(ln.logical_key, ln.source_ordinal, ln.native_values, ln.quantity_json_kind, ln.quantity_text, norm, state, unit))
    return out


# ---------------------------------------------------------------- bộ phân loại thuần
def _kiem_history(s: KhoHistorySummary) -> tuple[bool, bool]:
    """(unbound, mismatch). Không sửa/rebind history; không coi raw SHA là semantic SHA.

    unbound: bất kỳ digest nào được cung cấp (receipt request/content, seen, accepted, raw/master/semantic của content ref)
    là null/NOT_BOUND/không đúng 64 hex. mismatch: id lặp, ref lặp/không resolve/lệch digest hoặc logical, digest ngoài seen,
    EXPLICIT_EMPTY có dữ liệu. ``content_reference_id`` vắng/null thì không tra, không bịa ref."""
    refs = s.seen_content_references
    digests = ([r.request_digest for r in s.receipts_seen] + [r.content_digest for r in s.receipts_seen] + list(s.seen_content_digests)
               + [x for c in refs for x in (c.native_raw_sha256, c.master_raw_subtree_sha256, c.semantic_digest)])
    if s.accepted_source is not None:
        digests.append(s.accepted_source.content_digest)
    unbound = any(not la_digest(d) for d in digests)

    ids = [r.receipt_id for r in s.receipts_seen]
    ref_ids = [c.reference_id for c in refs]
    seen = set(s.seen_content_digests)
    theo_ref = {c.reference_id: c for c in refs}

    def ref_lech(ref_id, digest) -> bool:
        if ref_id is None:
            return False
        if ref_ids.count(ref_id) != 1:
            return True
        return theo_ref[ref_id].semantic_digest != digest

    acc = s.accepted_source
    mismatch = (
        len(ids) != len(set(ids)) or len(ref_ids) != len(set(ref_ids))
        or len(s.seen_content_digests) != len(seen)
        or any(r.content_digest not in seen for r in s.receipts_seen)
        or (acc is not None and acc.content_digest not in seen)
        or any(c.logical_source_identity != s.logical_source_identity for c in refs)
        or any(c.semantic_digest not in seen for c in refs)
        or any(ref_lech(r.content_reference_id, r.content_digest) for r in s.receipts_seen)
        or (acc is not None and ref_lech(acc.content_reference_id, acc.content_digest))
        or (s.summary_kind == "EXPLICIT_EMPTY" and bool(ids or seen or acc or s.old_line_unit_basis_refs or refs)))
    return unbound, mismatch


def phan_loai_quan_sat(candidate: KhoReadResult, summary: KhoHistorySummary | None) -> KhoClassification:
    """Phân loại quan sát so với summary lịch sử tin cậy. Không đổi candidate/summary, không chọn current/duyệt/cấp capacity."""
    if not isinstance(candidate, KhoReadResult) or (summary is not None and not isinstance(summary, KhoHistorySummary)):
        raise DataError("KHO_SHAPE", "Classifier nhận KhoReadResult và KhoHistorySummary|None.")
    reasons = list(candidate.ma_loi())
    hold = any(i.severity in ("ERROR", "HOLD") for i in candidate.issues)

    def them(code):
        if code not in reasons:
            reasons.append(code)

    if candidate.source_state == "DA_DAO":
        them("REVERSED")
    if summary is None:
        them("HISTORY_UNAVAILABLE")
        return KhoClassification(tuple(reasons), True, "MISSING")
    state = "KNOWN"
    if (summary.logical_source_identity != candidate.logical_source_identity or summary.scope_ref != candidate.scope_ref
            or summary.profile_ref != candidate.source_profile_ref):
        them("HISTORY_MISMATCH")
        state = "UNKNOWN"
    unbound, mismatch = _kiem_history(summary)
    if unbound:
        them("HISTORY_UNBOUND")
        state = "UNKNOWN"
    if mismatch:
        them("HISTORY_MISMATCH")
        state = "UNKNOWN"
    seen = set(summary.seen_content_digests)
    if state == "KNOWN":
        acc = summary.accepted_source
        sem, req = candidate.semantic_digest, candidate.request_digest
        cu = next((r for r in summary.receipts_seen if r.receipt_id == candidate.receipt_id), None) if candidate.receipt_id else None
        if cu is not None:
            if sem is not None and req is not None and cu.request_digest == req and cu.content_digest == sem:
                them("REPLAY")
            else:
                them("KHO_RECEIPT_CONFLICT")
        elif sem is not None:
            if acc is not None and acc.content_digest == sem:
                them("SAME_CONTENT_FRESH_OBSERVATION")
            elif sem in seen:
                them("REAPPEARANCE_HOLD")
            else:
                them("FIRST_OBSERVATION_CANDIDATE")
        # liên tục đơn vị so với basis cũ của cùng dòng native (không cấp hệ số/basis mới)
        theo_dong = {ln.native_values.get("ID_Dong"): ln for ln in candidate.lines if isinstance(ln.native_values, FrozenObject)}
        for b in summary.old_line_unit_basis_refs:
            ln = theo_dong.get(b.native_line_id)
            if ln is not None and ln.unit_definition_ref != b.unit_definition_ref:
                them("KHO_POOL_CONTINUITY_UNPROVEN")
                mr = candidate.measurement_refs
                if mr is None or mr.approved_conversion_proof_ref is None:
                    them("KHO_CONVERSION_PROOF_MISSING")
    needs = hold or state != "KNOWN" or any(r not in _INFO for r in reasons)
    return KhoClassification(tuple(reasons), needs, state)
