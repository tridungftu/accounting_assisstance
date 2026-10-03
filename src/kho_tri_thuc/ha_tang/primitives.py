"""Canonical values: reject ambiguity instead of silently repairing evidence."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any

MIN_INT64 = -(2**63)
MAX_INT64 = 2**63 - 1


class DataError(ValueError):
    def __init__(self, code: str, message: str, locator: str = "$"):
        super().__init__(message)
        self.code = code
        self.locator = locator


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def local_business_date(instant: str) -> str:
    """PLHN pilot business calendar: Vietnam UTC+07; event instants stay UTC."""
    return datetime.fromisoformat(instant_utc(instant).replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=7))).date().isoformat()


def text_id(value: Any, field: str = "id") -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise DataError("INVALID_TEXT_ID", f"{field} phải là chuỗi không rỗng, không có khoảng trắng ở hai đầu.")
    return value


def normalize_text(value: str) -> str:
    if not isinstance(value, str):
        raise DataError("INVALID_TEXT", "Văn bản phải là chuỗi.")
    replaced = value.replace("Đ", "D").replace("đ", "d")
    plain = "".join(c for c in unicodedata.normalize("NFD", replaced) if not unicodedata.combining(c))
    return " ".join(plain.upper().split())


def date_iso(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise DataError("AMBIGUOUS_DATE", "Ngày phải dùng YYYY-MM-DD; không đoán ngày/tháng.")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise DataError("INVALID_DATE", "Ngày không tồn tại.") from exc
    return value


def instant_utc(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value
    ):
        raise DataError("AMBIGUOUS_TIME", "Thời điểm phải có giờ, phút, giây và offset hoặc Z.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    except ValueError as exc:
        raise DataError("INVALID_TIME", "Thời điểm hoặc offset không hợp lệ.") from exc


def money_minor(value: Any, scale: int = 0, *, decimal_sep: str = ".", group_sep: str | None = None) -> int:
    """Parse only a declared numeric format; floats/bools and implicit rounding are forbidden."""
    if type(scale) is not int or not 0 <= scale <= 6:
        raise DataError("INVALID_SCALE", "Scale phải là số nguyên từ 0 đến 6.")
    if type(value) is int:
        raw = str(value)
    elif isinstance(value, (str, Decimal)):
        raw = str(value)
    else:
        raise DataError("INEXACT_MONEY", "Tiền phải là chuỗi thập phân/Decimal/số nguyên; không nhận float hoặc bool.")
    if len(raw) > 100:
        raise DataError("MONEY_OVERFLOW", "Tiền vượt miền hỗ trợ.")
    if decimal_sep not in (".", ",") or (group_sep is not None and group_sep not in (".", ",", " ")) or group_sep == decimal_sep:
        raise DataError("MONEY_FORMAT", "Ký hiệu phân cách tiền không hợp lệ.")
    integer = r"\d+"
    if group_sep:
        integer = rf"(?:\d+|\d{{1,3}}(?:{re.escape(group_sep)}\d{{3}})+)"
    if not re.fullmatch(rf"[+-]?{integer}(?:{re.escape(decimal_sep)}\d+)?", raw):
        raise DataError("MONEY_FORMAT", "Tiền không khớp định dạng đã khai báo.")
    normalized = raw.replace(group_sep, "") if group_sep else raw
    normalized = normalized.replace(decimal_sep, ".")
    try:
        with localcontext() as ctx:
            ctx.prec = max(40, len(normalized) + scale + 4)
            scaled = Decimal(normalized) * (Decimal(10) ** scale)
            if scaled != scaled.to_integral_value():
                raise DataError("FRACTIONAL_MONEY", "Tiền có số lẻ vượt scale; không tự làm tròn.")
            result = int(scaled)
    except InvalidOperation as exc:
        raise DataError("MONEY_FORMAT", "Tiền không hợp lệ.") from exc
    if not MIN_INT64 <= result <= MAX_INT64:
        raise DataError("MONEY_OVERFLOW", "Tiền vượt INTEGER 64-bit.")
    return result


def natural_key(*parts: str) -> str:
    return canonical_json(["v1", *(text_id(part, "khóa nguồn") for part in parts)])


def valid_interval(start: str, end: str | None) -> tuple[str, str | None]:
    start = date_iso(start)
    if end is not None and date_iso(end) <= start:
        raise DataError("INVALID_INTERVAL", "Khoảng [từ, đến) phải có đến > từ.")
    return start, end


def intervals_overlap(a: tuple[str, str | None], b: tuple[str, str | None]) -> bool:
    a, b = valid_interval(*a), valid_interval(*b)
    return (b[1] is None or a[0] < b[1]) and (a[1] is None or b[0] < a[1])
