"""Explicit synthetic exchange contract. This is NOT a bank/XML/Base/Junsky parser."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Protocol

from ..ha_tang.config import Config
from ..ha_tang.primitives import (
    DataError, canonical_json, date_iso, instant_utc, money_minor, natural_key,
    normalize_text, text_id, valid_interval,
)

SOURCES = ("sao_ke", "hoa_don_xml", "hoa_don_bang_ke", "base", "junsky_xuat")
JUNSKY_KINDS = {"OPEN_ITEM", "COUNTERPARTY", "ACCOUNT", "EXPENSE", "PROJECT", "COST_CENTER", "LOCK_PERIOD", "JOURNAL"}
CATALOG = {
    source: {"real_adapter": "WAITING_FOR_SAMPLE", "fixture_adapter": "fixture-json-v1"}
    for source in SOURCES
}


@dataclass
class Issue:
    code: str
    message: str
    locator: str = "$"
    severity: str = "ERROR"


@dataclass
class Record:
    ordinal: int
    kind: str
    key: str
    business_date: str
    currency: str | None
    amount_minor: int | None
    core: dict
    lines: list[dict] = field(default_factory=list)


@dataclass
class Batch:
    source: str
    manifest: dict
    raw_records: list
    records: list[Record]
    totals: dict[str, int]
    issues: list[Issue]
    controls: dict[str, Any] = field(default_factory=dict)
    allow_record_errors: bool = False

    @property
    def valid(self) -> bool:
        return not any(issue.severity == "ERROR" and not (self.allow_record_errors and issue.locator.startswith("$.records[")) for issue in self.issues)


class Adapter(Protocol):
    version: str

    def read(self, content: bytes, config: Config) -> Batch: ...


def _unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise DataError("DUPLICATE_JSON_KEY", "JSON chứa khóa lặp; không chọn giá trị cuối.")
        result[key] = value
    return result


def read_json(content: bytes) -> Any:
    try:
        return json.loads(content.decode("utf-8-sig"), object_pairs_hook=_unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(DataError("INVALID_JSON", "JSON chứa NaN/Infinity.")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DataError("INVALID_JSON", "Không đọc được JSON UTF-8 hợp lệ.") from exc


def required(obj: dict, key: str) -> str:
    if key not in obj:
        raise DataError("MISSING_FIELD", f"Thiếu trường {key}.")
    return text_id(obj[key], key)


def optional_text(raw: dict, name: str, core: dict, allowed: set[str]) -> None:
    allowed.add(name)
    if raw.get(name) is not None:
        core[name] = text_id(raw[name], name)


def optional_money(raw: dict, name: str, core: dict, allowed: set[str], config: Config) -> None:
    allowed.add(name)
    if raw.get(name) is not None:
        core[name.replace("amount", "minor")] = money_minor(raw[name], config.scale)


def normalized_invoice_number(value: str) -> str:
    """The source contract identifies invoices without insignificant leading zeroes."""
    number = text_id(value, "số hóa đơn")
    return number.lstrip("0") or "0" if number.isdigit() else number


def invoice_natural_key(seller_tax_id: str, series: str, number: str, invoice_type: str) -> str:
    return natural_key(text_id(seller_tax_id, "seller_tax_id"), text_id(series, "series"), normalized_invoice_number(number), text_id(invoice_type, "invoice_type"))


def _manifest(raw: Any, config: Config) -> tuple[dict, list[Issue]]:
    if not isinstance(raw, dict):
        raise DataError("INVALID_MANIFEST", "Manifest phải là object.")
    result = dict(raw)
    if required(raw, "entity_id") != config.entity_id:
        raise DataError("WRONG_ENTITY", "Pháp nhân không khớp cấu hình.")
    required(raw, "source_system")
    result["as_of"] = date_iso(raw.get("as_of"))
    start, end = valid_interval(raw.get("coverage_from"), raw.get("coverage_to_exclusive"))
    if end is None:
        raise DataError("INCOMPLETE_COVERAGE", "Phạm vi file phải có ngày kết thúc loại trừ.")
    if date.fromisoformat(end) - timedelta(days=1) > date.fromisoformat(result["as_of"]):
        raise DataError("STALE_AS_OF", "As-of chưa bao phủ ngày cuối dữ liệu.")
    result["coverage_from"], result["coverage_to_exclusive"] = start, end
    result["exported_at"] = instant_utc(raw.get("exported_at"))
    # Preserve raw timezone, precision and claims in the immutable manifest/raw file.
    result["exported_at_raw"] = raw["exported_at"]
    if raw["exported_at"][:10] < result["as_of"]:
        raise DataError("INVALID_EXPORT_TIME", "Ngày xuất nguồn trước as-of.")
    issues = []
    if raw.get("known_at") is None:
        result["known_at"] = None
        result["known_at_basis"] = None
        issues.append(Issue("UNKNOWN_KNOWN_AT", "Thiếu bằng chứng thời điểm biết; loại khỏi truy vấn cutoff nghiêm ngặt.", "$.manifest.known_at", "WARNING"))
    else:
        result["known_at"] = instant_utc(raw["known_at"])
        required(raw, "known_at_basis")
    required(raw, "scope")
    return result, issues


def _record(raw: Any, ordinal: int, source: str, manifest: dict, config: Config) -> Record:
    if not isinstance(raw, dict):
        raise DataError("INVALID_RECORD", "Bản ghi phải là object.")
    kind = {"sao_ke": "BANK", "hoa_don_xml": "INVOICE", "hoa_don_bang_ke": "INVOICE", "base": "BASE"}.get(source)
    if kind is None:
        kind = required(raw, "kind")
        if kind not in JUNSKY_KINDS:
            raise DataError("UNSUPPORTED_KIND", "Loại dữ liệu Junsky giả lập chưa hỗ trợ.")
    elif "kind" in raw and raw["kind"] != kind:
        raise DataError("WRONG_RECORD_KIND", "Loại bản ghi không phù hợp nhóm nguồn.")
    business_date = date_iso(raw.get("business_date"))
    if not manifest["coverage_from"] <= business_date < manifest["coverage_to_exclusive"]:
        raise DataError("OUTSIDE_COVERAGE", "Ngày bản ghi nằm ngoài phạm vi khai báo.")
    amount, currency = None, None
    if kind in {"BANK", "INVOICE", "BASE", "OPEN_ITEM", "JOURNAL"}:
        currency = required(raw, "currency")
        if currency != config.currency:
            raise DataError("WRONG_CURRENCY", "Tiền tệ ngoài phạm vi được cấu hình; không tự quy đổi.")
        if "amount" not in raw:
            raise DataError("MISSING_FIELD", "Thiếu trường amount.")
        source_amount = raw["amount"]
        if kind == "BASE" and isinstance(source_amount, str) and source_amount.strip().casefold().endswith(" vnd"):
            source_amount = source_amount.strip()[:-4].strip()
        amount = money_minor(source_amount, config.scale)
    core: dict = {"kind": kind, "business_date": business_date, "currency": currency, "amount_minor": amount}
    # Every mapped field comes from this synthetic format, never inferred source columns.
    allowed = {"business_date", "kind"}
    if currency is not None:
        allowed.update({"currency", "amount"})
    def fields(*names: str) -> list[str]:
        allowed.update(names)
        values = [required(raw, name) for name in names]
        core.update(zip(names, values))
        return values
    lines: list[dict] = []
    if kind == "BANK":
        bank, account, scope = fields("bank", "account", "id_scope")
        allowed.add("reference")
        reference = text_id(raw["reference"], "reference") if raw.get("reference") is not None else None
        if reference is not None:
            core["reference"] = reference
        allowed.update({"identity_verified", "description"})
        if raw.get("identity_verified") is not True:
            raise DataError("AMBIGUOUS_IDENTITY", "Chưa có bằng chứng ID ngân hàng ổn định; giữ chờ xác minh.")
        description = required(raw, "description")
        core.update(description=description, normalized_description=normalize_text(description))
        allowed.update({"counterparty_account", "counterparty_tax_id", "invoice_references", "mtid", "citad", "mtid_citad", "beneficiary_id", "counterparty_name", "occurred_at", "balance_after", "fallback_key_confidence"})
        for name in ("counterparty_account", "counterparty_tax_id", "mtid", "citad", "mtid_citad", "beneficiary_id", "counterparty_name", "occurred_at", "fallback_key_confidence"):
            if raw.get(name) is not None:
                core[name] = text_id(raw[name], name)
        if raw.get("balance_after") is not None:
            core["balance_after_minor"] = money_minor(raw["balance_after"], config.scale)
        if "invoice_references" in raw:
            if not isinstance(raw["invoice_references"], list) or any(not isinstance(v, str) or not v for v in raw["invoice_references"]):
                raise DataError("INVALID_INVOICE_REFERENCES", "Tham chiếu hóa đơn phải là danh sách chuỗi.")
            core["invoice_references"] = raw["invoice_references"]
        if reference:
            key = natural_key(bank, account, scope, reference)
            core["identity_key_level"] = "STABLE_REFERENCE"
        else:
            if not raw.get("occurred_at") or raw.get("balance_after") is None:
                raise DataError("MISSING_BANK_FALLBACK_KEY", "Thiếu số giao dịch thì cần ngày giờ và số dư sau giao dịch cho khóa dự phòng.")
            key = natural_key(bank, account, raw["occurred_at"], str(amount), str(core["balance_after_minor"]))
            core["identity_key_level"] = "FALLBACK_ACCOUNT_TIME_AMOUNT_BALANCE"
    elif kind == "INVOICE":
        seller, series, number, invoice_type = fields("seller_tax_id", "series", "number", "invoice_type")
        allowed.add("buyer_tax_id")
        if raw.get("buyer_tax_id") is not None:
            core["buyer_tax_id"] = str(raw["buyer_tax_id"]).strip()
        fields("source_status")
        allowed.update({"related_invoice_key", "related_invoice", "lines", "net_amount", "tax_amount", "total_amount", "tax_currency", "rounding_tolerance", "invoice_relation", "ttxly", "ttxly_meaning", "model", "tax_status", "direction", "other_amount", "non_taxable_amount", "total_mismatch_warning", "detail_total_warning"})
        if raw.get("related_invoice_key") is not None:
            related = raw["related_invoice_key"]
            if not isinstance(related, list) or len(related) != 4:
                raise DataError("INVALID_INVOICE_RELATION", "Quan hệ HĐ phải có bốn phần khóa giả lập.")
            core["related_invoice_key"] = natural_key(*related)
        key = invoice_natural_key(seller, series, number, invoice_type)
        total = money_minor(raw.get("total_amount", raw.get("amount")), config.scale)
        net = money_minor(raw.get("net_amount", raw.get("amount")), config.scale)
        tax = money_minor(raw.get("tax_amount", "0"), config.scale)
        other = money_minor(raw.get("other_amount", "0"), config.scale)
        non_taxable = money_minor(raw.get("non_taxable_amount", "0"), config.scale)
        tolerance = money_minor(raw.get("rounding_tolerance", "1"), config.scale)
        expected_total = net + tax + other + (0 if config.invoice_non_taxable_in_taxable_total else non_taxable)
        if tolerance < 0 or expected_total != total and abs(expected_total - total) > tolerance and raw.get("total_mismatch_warning") is not True:
            raise DataError("INVOICE_TOTAL_MISMATCH", "Tiền chưa thuế + tiền thuế không khớp tổng thanh toán trong dung sai.")
        core.update(net_minor=net, tax_minor=tax, total_minor=total, other_minor=other, non_taxable_minor=non_taxable,
                    tax_currency=raw.get("tax_currency", currency), tolerance_minor=tolerance,
                    number=normalized_invoice_number(number))
        for name in ("model", "tax_status", "direction"):
            if raw.get(name) is not None:
                core[name] = text_id(raw[name], name)
        if raw.get("related_invoice") is not None:
            related = raw["related_invoice"]
            if not isinstance(related, dict) or set(related) - {"relation_type", "model", "series", "number", "date"}:
                raise DataError("INVALID_INVOICE_RELATION", "Hóa đơn liên quan sai cấu trúc hợp đồng.")
            core["related_invoice"] = {key: text_id(value, "related_invoice." + key) for key, value in related.items() if value not in (None, "")}
        if raw.get("invoice_relation") is not None:
            relation = required(raw, "invoice_relation")
            if relation not in {"ORIGINAL", "ADJUSTMENT", "REPLACEMENT", "CANCELLED"}:
                raise DataError("INVALID_INVOICE_RELATION", "Quan hệ hóa đơn chỉ nhận ORIGINAL/ADJUSTMENT/REPLACEMENT/CANCELLED.")
            core["invoice_relation"] = relation
        if raw.get("ttxly") is not None:
            ttxly = required(raw, "ttxly")
            if ttxly not in {"1", "2", "3", "4", "5", "6"}:
                raise DataError("INVALID_TTXLY", "ttxly của bảng kê chỉ nhận 1–6.")
            core["ttxly"] = ttxly
        if raw.get("ttxly_meaning") is not None:
            core["ttxly_meaning"] = text_id(raw["ttxly_meaning"], "ttxly_meaning")
        if "lines" in raw:
            if source != "hoa_don_xml":
                raise DataError("HEADER_ONLY", "Fixture bảng kê chỉ chứa header, không dựng dòng hàng.")
            if not isinstance(raw["lines"], list) or not raw["lines"]:
                raise DataError("INVALID_LINES", "Lines phải là danh sách không rỗng.")
            for line in raw["lines"]:
                if not isinstance(line, dict) or not {"line_id", "description"}.issubset(line):
                    raise DataError("INVALID_LINE", "Dòng HĐ fixture cần line_id và description.")
                permitted = {"line_id", "description", "amount", "net_amount", "tax_amount", "total_amount", "tax_rate", "line_nature"}
                if set(line) - permitted or not ("amount" in line or "net_amount" in line):
                    raise DataError("INVALID_LINE", "Dòng HĐ có trường ngoài contract hoặc thiếu tiền chưa thuế.")
                line_net = money_minor(line.get("net_amount", line.get("amount")), config.scale)
                line_tax = money_minor(line.get("tax_amount", "0"), config.scale)
                line_total = money_minor(line.get("total_amount", str(line_net + line_tax)), config.scale)
                nature = line.get("line_nature", "GOODS")
                if nature not in {"GOODS", "PROMOTION", "DISCOUNT", "NOTE"}:
                    raise DataError("INVALID_LINE_NATURE", "Tính chất dòng HĐ không hợp lệ.")
                if abs(line_net + line_tax - line_total) > tolerance:
                    raise DataError("LINE_TOTAL_MISMATCH", "Tổng tiền từng dòng không khớp trong dung sai.")
                lines.append({"line_key": required(line, "line_id"), "description": required(line, "description"), "amount_minor": line_net,
                              "net_minor": line_net, "tax_minor": line_tax, "total_minor": line_total,
                              "tax_rate": line.get("tax_rate"), "line_nature": nature})
            if abs(sum(line["net_minor"] for line in lines) - net) > tolerance * len(lines) and raw.get("detail_total_warning") is not True:
                raise DataError("DETAIL_TOTAL_MISMATCH", "Tổng tiền chưa thuế theo dòng không khớp header trong dung sai khai báo.")
    elif kind == "BASE":
        tenant, request_id = fields("tenant", "request_id")
        fields("source_status")
        allowed.update({"project_raw", "expense_raw", "request_name", "proposal_group", "approval_status", "approved_date", "beneficiary_account", "beneficiary_headers", "beneficiary_rows", "fetched_at", "source_state", "attachments"})
        for optional in ("project_raw", "expense_raw", "request_name", "proposal_group", "approval_status", "approved_date", "beneficiary_account", "fetched_at", "source_state"):
            optional_text(raw, optional, core, allowed)
        for optional in ("beneficiary_headers", "beneficiary_rows"):
            if raw.get(optional) is not None:
                if not isinstance(raw[optional], list):
                    raise DataError("INVALID_BASE_TABLE", "Bảng Base cần là danh sách để giữ cấu trúc nguồn.")
                core[optional] = raw[optional]
        if raw.get("attachments") is not None:
            if not isinstance(raw["attachments"], list) or any(not isinstance(v, (str, dict)) for v in raw["attachments"]):
                raise DataError("INVALID_BASE_ATTACHMENTS", "Danh sách file đính kèm Base phải là danh sách chuỗi.")
            core["attachments"] = list(raw["attachments"])
        key = natural_key(tenant, request_id)
    elif kind == "OPEN_ITEM":
        account, party, item, item_type = fields("account", "counterparty", "item_id", "item_type")
        allowed.update({"invoice_reference", "project", "invoice_series", "invoice_number", "invoice_date", "document_date", "description", "loan_contract", "unit_code", "transaction_code", "invoice_model"})
        if item_type not in {"INVOICE", "ADVANCE", "UNBILLED"}:
            raise DataError("UNKNOWN_ITEM_TYPE", "Loại công nợ chưa xác nhận.")
        if item_type == "INVOICE":
            core["invoice_reference"] = required(raw, "invoice_reference")
        core["snapshot_id"] = required(manifest, "snapshot_id")
        for optional in ("project", "invoice_series", "invoice_number", "invoice_date", "document_date", "description", "loan_contract", "unit_code", "transaction_code", "invoice_model"):
            optional_text(raw, optional, core, allowed)
        key = natural_key(manifest["source_system"], core["snapshot_id"], account, party, currency, item)
    elif kind == "LOCK_PERIOD":
        start, end, scope = fields("valid_from", "valid_to", "scope")
        valid_interval(start, end)
        fields("source_status")
        key = natural_key(manifest["source_system"], start, end, scope, required(manifest, "snapshot_id"))
    elif kind == "JOURNAL":
        book, year, voucher_type, number = fields("book", "fiscal_year", "voucher_type", "voucher_number")
        fields("source_status")
        allowed.update({"lines", "complete_voucher"})
        raw_lines = raw.get("lines")
        if not isinstance(raw_lines, list) or not raw_lines or type(raw.get("complete_voucher")) is not bool:
            raise DataError("INVALID_JOURNAL", "Cần dòng sổ và cờ phạm vi complete_voucher rõ ràng.")
        for line in raw_lines:
            if not isinstance(line, dict) or set(line) != {"line_id", "account", "debit", "credit"}:
                raise DataError("INVALID_JOURNAL_LINE", "Dòng sổ fixture sai cấu trúc.")
            debit, credit = money_minor(line["debit"], config.scale), money_minor(line["credit"], config.scale)
            if debit < 0 or credit < 0 or (debit > 0 and credit > 0):
                raise DataError("INVALID_DC", "Dòng sổ phải có Nợ/Có không âm, không cùng dương.")
            lines.append({"line_key": required(line, "line_id"), "account": required(line, "account"), "debit_minor": debit, "credit_minor": credit, "amount_minor": debit - credit})
        total = sum(line["amount_minor"] for line in lines)
        if total != amount or (raw["complete_voucher"] and total != 0):
            raise DataError("JOURNAL_TOTAL_MISMATCH", "Tổng Nợ/Có không khớp phạm vi chứng từ.")
        core["complete_voucher"] = raw["complete_voucher"]
        allowed.update({"bank_reference", "bank_account", "counterparty", "project", "expense", "export_item_id", "batch_id", "invoice_key", "invoice_allocations", "bank_transaction_number", "invoice_reference", "cost_center", "posting_status", "unit_code", "transaction_code", "description"})
        for name in ("bank_reference", "bank_account", "counterparty", "project", "expense", "export_item_id", "batch_id", "invoice_key", "bank_transaction_number", "invoice_reference", "cost_center", "posting_status", "unit_code", "transaction_code", "description"):
            if raw.get(name) is not None:
                core[name] = text_id(raw[name], name)
        if "invoice_allocations" in raw:
            values = raw["invoice_allocations"]
            if not isinstance(values, list) or any(not isinstance(v, dict) or set(v) != {"invoice_reference", "amount_minor"} for v in values):
                raise DataError("INVALID_INVOICE_ALLOCATIONS", "Phân bổ HĐ trên chứng từ fixture sai cấu trúc.")
            core["invoice_allocations"] = [{"invoice_reference": text_id(v["invoice_reference"]), "amount_minor": money_minor(v["amount_minor"])} for v in values]
        key = natural_key(manifest["source_system"], book, year, voucher_type, number)
    else:
        code, version = fields("code", "version")
        fields("name", "source_status", "valid_from")
        allowed.add("valid_to")
        valid_interval(core["valid_from"], raw.get("valid_to"))
        core["valid_to"] = raw.get("valid_to")
        allowed.update({"tax_id", "bank_account", "parent_code", "account_nature"})
        for optional in ("tax_id", "bank_account", "parent_code", "account_nature"):
            if raw.get(optional) is not None:
                core[optional] = text_id(raw[optional], optional)
        key = natural_key(manifest["source_system"], kind, code, version)
    if set(raw) - allowed:
        raise DataError("UNMAPPED_FIELD", "Fixture có trường ngoài contract; không bỏ trường âm thầm.")
    if len({line["line_key"] for line in lines}) != len(lines):
        raise DataError("DUPLICATE_LINE_ID", "ID dòng trùng trong chứng từ.")
    return Record(ordinal, kind, key, business_date, currency, amount, core, lines)


class FixtureAdapter:
    version = "fixture-json-v1"

    def read(self, content: bytes, config: Config) -> Batch:
        obj = read_json(content)
        if not isinstance(obj, dict) or obj.get("format") != "ktt-fixture-v1" or obj.get("synthetic") is not True:
            raise DataError("FIXTURE_ONLY", "Chỉ nhận ktt-fixture-v1 với synthetic=true; không phải adapter dữ liệu thật.")
        source = required(obj, "source")
        if source not in SOURCES:
            raise DataError("UNSUPPORTED_SOURCE", "Nguồn chưa hỗ trợ.")
        manifest, issues = _manifest(obj.get("manifest"), config)
        rows = obj.get("records")
        if not isinstance(rows, list) or not rows:
            raise DataError("EMPTY_SOURCE", "Fixture phải có danh sách records không rỗng.")
        records, totals = [], defaultdict(int)
        keys = set()
        for ordinal, raw in enumerate(rows):
            try:
                record = _record(raw, ordinal, source, manifest, config)
                identity = (record.kind, record.key)
                if identity in keys:
                    raise DataError("DUPLICATE_SOURCE_KEY", "Khóa nghiệp vụ lặp trong cùng file; không tự gộp.")
                keys.add(identity)
                records.append(record)
                if record.amount_minor is not None:
                    totals[f"{record.kind}/{record.currency}"] += record.amount_minor
            except DataError as exc:
                issues.append(Issue(exc.code, str(exc), f"$.records[{ordinal}]"))
        controls = obj.get("controls")
        try:
            if not isinstance(controls, dict) or type(controls.get("count")) is not int or controls["count"] != len(rows):
                raise DataError("COUNT_MISMATCH", "Số bản ghi không khớp tổng kiểm soát.")
            expected = controls.get("totals")
            if not isinstance(expected, dict):
                raise DataError("MISSING_TOTALS", "Thiếu tổng kiểm soát theo loại/tiền tệ.")
            parsed_totals = {key: money_minor(value, config.scale) for key, value in expected.items()}
            if parsed_totals != dict(totals):
                raise DataError("CONTROL_TOTAL_MISMATCH", "Tổng tiền hoặc nhóm loại/tiền tệ không khớp.")
            if source == "sao_ke":
                opening = money_minor(controls.get("opening_balance"), config.scale)
                closing = money_minor(controls.get("closing_balance"), config.scale)
                if opening + totals.get("BANK/VND", 0) != closing:
                    raise DataError("BANK_BALANCE_MISMATCH", "Số đầu + thu - chi không bằng số cuối.")
        except DataError as exc:
            issues.append(Issue(exc.code, str(exc), "$.controls"))
        return Batch(source, manifest, rows, records, dict(totals), issues)


def check_junsky_bundle(batches: list[Batch]) -> dict:
    """Validate conceptual coverage only; not the M3 session gate or posting confirmation."""
    issues = []
    if not batches or any(batch.source != "junsky_xuat" or not batch.valid for batch in batches):
        return {"valid": False, "fixture_only": True, "issues": ["INVALID_COMPONENT"]}
    for field_name in ("entity_id", "as_of", "coverage_from", "coverage_to_exclusive", "snapshot_id", "source_system"):
        if len({batch.manifest.get(field_name) for batch in batches}) != 1:
            issues.append(f"INCOMPATIBLE_{field_name.upper()}")
    present = {record.kind for batch in batches for record in batch.records}
    missing = JUNSKY_KINDS - present
    if missing:
        issues.append("MISSING_ROLES:" + ",".join(sorted(missing)))
    return {"valid": not issues, "fixture_only": True, "roles": sorted(present), "issues": issues}
