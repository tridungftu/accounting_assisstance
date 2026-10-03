"""Versioned, explicit matching contracts; never infer approval from source status."""
from __future__ import annotations

import re
from datetime import date, timedelta
from functools import lru_cache

from ..ha_tang.primitives import DataError, date_iso, normalize_text, sha256, text_id

FIELDS = {"counterparty", "debit_account", "credit_account", "project", "expense"}
KEY_FIELDS = {"BANK_ACCOUNT": "counterparty_account", "TAX_ID": "counterparty_tax_id",
              "COUNTERPARTY": "counterparty", "COUNTERPARTY_NAME": "counterparty_name"}


@lru_cache(maxsize=2048)
def compile_pattern(pattern):
    if not isinstance(pattern, str) or not pattern.strip() or len(pattern) > 512:
        raise DataError("INVALID_REGEX", "Regex phải là chuỗi không rỗng, tối đa 512 ký tự.")
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise DataError("INVALID_REGEX", "Regex sai cú pháp; kiểm tra hàng tri thức nguồn.") from exc
    if compiled.search("") is not None:
        raise DataError("EMPTY_REGEX_MATCH", "Regex không được khớp văn bản rỗng.")
    return compiled


def literal_pattern(value):
    """Explicit conversion of a literal keyword, preserving regex syntax elsewhere."""
    term = normalize_text(text_id(value, "keyword"))
    return r"(?<!\w)" + re.escape(term) + r"(?!\w)"


def expiry_exclusive(raw):
    if raw is None or raw == "":
        return None
    try:
        return (date.fromisoformat(date_iso(raw)) + timedelta(days=1)).isoformat()
    except OverflowError as exc:
        raise DataError("INVALID_EXPIRY", "Ngày hết hạn vượt miền ngày hỗ trợ.") from exc


def description_hash(value):
    return sha256(normalize_text(value).encode("utf-8"))


def normalized_name(value, version=None):
    value = normalize_text(value)
    if version == "legacy-chung-v1":
        value = " ".join(re.sub(r"[^A-Z0-9 ]", " ", value).split())
        for long, short in (("VIET NAM", "VN"), ("CONG TY", "CTY"), ("CO PHAN", "CP"), ("TRACH NHIEM HUU HAN", "TNHH"), ("DICH VU", "DV")):
            value = value.replace(long, short)
    return value


def validate_payload(category, payload):
    version = payload.get("contract_version", 1)
    if type(version) is not int or version not in (1, 2):
        raise DataError("KNOWLEDGE_CONTRACT_VERSION", "Phiên bản payload chưa hỗ trợ.")
    if version == 1:
        return
    if category not in {"POLICY", "CASE", "RULE"}:
        raise DataError("KNOWLEDGE_CONTRACT_VERSION", "Version 2 áp dụng POLICY/CASE/RULE.")
    fields = payload.get("fields")
    if not isinstance(fields, dict) or not set(fields) <= FIELDS:
        raise DataError("MATCH_FIELDS", "Các trường kết quả không hợp lệ.")
    for name, value in fields.items():
        if value is not None:
            text_id(value, name)
            if name in {"debit_account", "credit_account"} and "|" in value:
                raise DataError("MULTILINE_NOT_SUPPORTED", "Mẫu nhiều tài khoản cần thiết kế nhiều dòng riêng.")
    journal_lines = payload.get("journal_lines")
    if journal_lines is not None:
        if category not in {"POLICY", "CASE"} or not isinstance(journal_lines, list) or len(journal_lines) < 2:
            raise DataError("MULTILINE_CONTRACT", "Mẫu nhiều dòng cần ít nhất hai dòng trong POLICY/CASE.")
        ids = set()
        for line in journal_lines:
            if not isinstance(line, dict) or set(line) - {"line_id", "account", "side", "amount_source", "tax_rate", "dimensions"}:
                raise DataError("MULTILINE_CONTRACT", "Dòng mẫu có trường ngoài hợp đồng.")
            identifier, account, side, source = line.get("line_id"), line.get("account"), line.get("side"), line.get("amount_source")
            text_id(identifier, "line_id"); text_id(account, "account")
            if identifier in ids or side not in {"DEBIT", "CREDIT"} or source not in {"BANK_TOTAL", "INVOICE_NET", "INVOICE_TAX"}:
                raise DataError("MULTILINE_CONTRACT", "line_id/side/amount_source của mẫu nhiều dòng không hợp lệ.")
            ids.add(identifier)
            if line.get("tax_rate") is not None:
                text_id(line["tax_rate"], "tax_rate")
            if line.get("dimensions") is not None and (not isinstance(line["dimensions"], dict) or not set(line["dimensions"]) <= FIELDS):
                raise DataError("MULTILINE_CONTRACT", "dimensions dòng chỉ nhận các trường định khoản.")
    if category in {"POLICY", "CASE"}:
        for name in ("template_id", "partition", "direction"):
            text_id(payload.get(name), name)
        if payload["direction"] not in {"IN", "OUT"} or type(payload.get("needs_open_item")) is not bool:
            raise DataError("MATCH_CONTRACT", "Thiếu chiều hoặc quy tắc công nợ.")
        required = payload.get("required_fields")
        if not isinstance(required, list) or not all(isinstance(x, str) for x in required) or not set(required) <= FIELDS:
            raise DataError("MATCH_CONTRACT", "Danh sách trường bắt buộc sai.")
    if category == "CASE":
        selector = payload.get("selector", {})
        if not isinstance(selector, dict) or set(selector) != {"type", "value", "entity_id", "bank_account"}:
            raise DataError("CASE_SCOPE", "CASE cần phạm vi pháp nhân/tài khoản và khóa chính xác.")
        for name, value in selector.items():
            text_id(value, name)
        if selector["type"] not in {"BANK_REFERENCE", "VOUCHER_NUMBER", "DESCRIPTION_HASH"}:
            raise DataError("CASE_KEY", "Loại khóa CASE không hỗ trợ.")
        if selector["type"] == "DESCRIPTION_HASH" and (payload.get("normalization") != "normalize_text-v1" or not re.fullmatch(r"[0-9a-f]{64}", selector["value"])):
            raise DataError("CASE_HASH", "Hash CASE cần SHA-256 và phiên bản chuẩn hóa.")
        return
    if category == "POLICY":
        if type(payload.get("tier")) is not int or payload["tier"] not in range(1, 6) or type(payload.get("order")) is not int or payload["order"] < 1:
            raise DataError("POLICY_ORDER", "Mẫu cần bậc 1–5 và thứ tự dương.")
    trigger = payload.get("trigger")
    if not isinstance(trigger, dict) or not set(trigger) <= {"mode", "key_type", "key_value", "regex", "name_normalization"}:
        raise DataError("POLICY_TRIGGER", "Trigger không hợp lệ.")
    mode = trigger.get("mode")
    if not isinstance(mode, str) or mode not in {"KEY", "REGEX", "KEY_REGEX"}:
        raise DataError("POLICY_TRIGGER", "Trigger cần KEY, REGEX hoặc KEY_REGEX.")
    if mode != "REGEX":
        if not isinstance(trigger.get("key_type"), str) or trigger["key_type"] not in KEY_FIELDS:
            raise DataError("POLICY_TRIGGER", "Loại định danh không hỗ trợ.")
        text_id(trigger.get("key_value"), "key_value")
        if category == "POLICY" and trigger["key_type"] == "COUNTERPARTY_NAME" and payload["tier"] not in (3, 4):
            raise DataError("NAME_POLICY_TIER", "Điều kiện tên đối ứng chỉ được dùng ở bậc 3 hoặc 4.")
    elif "key_type" in trigger or "key_value" in trigger:
        raise DataError("POLICY_TRIGGER", "REGEX không được có khóa bị bỏ qua.")
    if "name_normalization" in trigger and (trigger.get("key_type") != "COUNTERPARTY_NAME" or trigger["name_normalization"] != "legacy-chung-v1"):
        raise DataError("NAME_NORMALIZATION", "Chuẩn hóa tên nguồn không hợp lệ.")
    if mode != "KEY":
        compile_pattern(trigger.get("regex"))
    elif "regex" in trigger:
        raise DataError("POLICY_TRIGGER", "KEY không được có regex bị bỏ qua.")


def matches(payload, bank, fields):
    if payload.get("direction") and payload["direction"] != ("IN" if bank["amount_minor"] > 0 else "OUT"):
        return False
    if payload.get("contract_version", 1) == 1:
        return all(normalize_text(term) in normalize_text(bank.get("description", "")) for term in payload.get("keywords", []))
    trigger = payload["trigger"]
    if trigger["mode"] != "REGEX":
        kind = trigger["key_type"]
        value = fields.get("counterparty") if kind == "COUNTERPARTY" else bank.get(KEY_FIELDS[kind])
        if not value:
            return False
        expected = trigger["key_value"]
        if kind == "COUNTERPARTY_NAME":
            value, expected = normalized_name(value, trigger.get("name_normalization")), normalized_name(expected, trigger.get("name_normalization"))
        if value != expected:
            return False
    return trigger["mode"] == "KEY" or compile_pattern(trigger["regex"]).search(normalize_text(bank.get("description", ""))) is not None


def case_matches(payload, bank, entity):
    selector = payload.get("selector", {})
    if selector.get("entity_id") != entity or selector.get("bank_account") != bank.get("account"):
        return False
    if payload.get("direction") != ("IN" if bank["amount_minor"] > 0 else "OUT"):
        return False
    value = {"BANK_REFERENCE": bank.get("reference"), "VOUCHER_NUMBER": bank.get("voucher_number"),
             "DESCRIPTION_HASH": description_hash(bank.get("description", ""))}.get(selector.get("type"))
    return value is not None and value == selector.get("value")


def choose(policies):
    """First match per partition. Ambiguous partitions or ties never pick silently."""
    modern = [r for r in policies if r["payload"].get("contract_version", 1) == 2]
    if not modern:
        ordered = sorted(policies, key=lambda r: int(r["payload"].get("priority", 0)), reverse=True)
        if not ordered or (len(ordered) > 1 and ordered[0]["payload"].get("priority", 0) == ordered[1]["payload"].get("priority", 0)):
            return None, "NO_UNIQUE_APPROVED_TEMPLATE"
        return ordered[0], None
    if len(modern) != len(policies):
        return None, "MIXED_POLICY_CONTRACTS"
    groups = {}
    for row in modern:
        p = row["payload"]
        groups.setdefault(p["partition"], []).append(row)
    winners = []
    for rows in groups.values():
        rows.sort(key=lambda r: (r["payload"]["tier"], r["payload"]["order"]))
        ranks = [(r["payload"]["tier"], r["payload"]["order"]) for r in rows]
        if len(ranks) != len(set(ranks)):
            return None, "POLICY_ORDER_COLLISION"
        winners.append(rows[0])
    if len(winners) != 1:
        return None, "POLICY_PARTITION_CONFLICT"
    return winners[0], None
