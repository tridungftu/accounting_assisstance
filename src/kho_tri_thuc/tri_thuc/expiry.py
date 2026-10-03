"""Explicit expiry policy; original workbook expiry is retained as evidence."""
from datetime import date, timedelta

from ..ha_tang.primitives import DataError, date_iso
from .matching import expiry_exclusive


def configured_valid_to(payload):
    rule = payload.get('expiry_policy')
    if not isinstance(rule, dict):
        raise DataError('EXPIRY_POLICY', 'Thiếu cấu hình hạn dùng.')
    if rule.get('mode') == 'VERIFIED_IDENTIFIER_NO_EXPIRY':
        if payload.get('kind') != 'IDENTIFIER' or payload.get('verified') is not True:
            raise DataError('EXPIRY_POLICY', 'Chỉ định danh đã xác minh được dùng chế độ không hết hạn này.')
        return None
    if rule.get('mode') != 'LAST_SEEN_DAYS' or type(rule.get('days')) is not int or not 1 <= rule['days'] <= 36500:
        raise DataError('EXPIRY_POLICY', 'Hạn dùng cần số ngày nguyên dương và lần cuối có bằng chứng.')
    try:
        last = date.fromisoformat(date_iso(rule.get('last_seen')))
        return expiry_exclusive((last + timedelta(days=rule['days'])).isoformat())
    except OverflowError as exc:
        raise DataError('EXPIRY_POLICY', 'Hạn dùng vượt miền ngày hỗ trợ.') from exc
