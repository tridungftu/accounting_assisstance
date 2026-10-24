"""Small, deterministic V9b helpers for local bank posting.

The helpers deliberately operate on already-ingested records.  They never read
source workbooks themselves, never approve knowledge and expose no transaction
text in logs or reports.  That keeps matching repeatable in the real store and
in the copy-only F replay.
"""
from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Iterable

from ..ha_tang.primitives import normalize_text


@lru_cache(maxsize=131072)
def _normalized(value: str) -> str:
    """normalize_text() is pure; the same ledger texts are compared for every bank row."""
    return normalize_text(value)


def bank_account(value: object) -> str:
    """Return the longest plausible account number, or an empty string."""
    raw = str(value or "").strip()
    # An operator may write an account with spaces or familiar separators in
    # source settings.  When the entire value is plainly an account number,
    # join its digit groups; do not join unrelated numbers embedded in a
    # narrative description.
    if re.fullmatch(r"[\d\s._()\-]+", raw):
        compact = "".join(re.findall(r"\d+", raw))
        return compact if len(compact) >= 6 else ""
    values = re.findall(r"\d+", raw)
    selected = max(values, key=len, default="")
    return selected if len(selected) >= 6 else ""


def is_cash_detail(value: object) -> bool:
    """Accept only a detailed 112 account, never the root 112 bucket."""
    # A detail account may be numeric in production (for example ``1121``)
    # or carry a sub-ledger suffix in an isolated fixture.  The invariant is
    # that the root bucket ``112`` itself is never accepted.
    return bool(re.fullmatch(r"112(?:[._-]?[A-Za-z0-9]+)", str(value or "").strip()))


def text_similarity(left: object, right: object) -> float:
    """Conservative description similarity used only after date and money match."""
    a, b = _normalized(str(left or "")), _normalized(str(right or ""))
    if not a or not b:
        return 0.0
    words_a, words_b = set(a.split()), set(b.split())
    contained = len(words_a & words_b) / max(1, min(len(words_a), len(words_b)))
    return max(contained, SequenceMatcher(None, a, b).ratio())


def similar_at_least(left: object, right: object, threshold: float) -> bool:
    """text_similarity(left, right) >= threshold, without computing ratio() when bounds decide."""
    a, b = _normalized(str(left or "")), _normalized(str(right or ""))
    if not a or not b:
        return 0.0 >= threshold
    words_a, words_b = set(a.split()), set(b.split())
    if len(words_a & words_b) / max(1, min(len(words_a), len(words_b))) >= threshold:
        return True
    matcher = SequenceMatcher(None, a, b)
    return matcher.real_quick_ratio() >= threshold and matcher.quick_ratio() >= threshold and matcher.ratio() >= threshold



# ---------------------------------------------------------------------------
# V11 — "vân tay diễn giải": the stable words of a bank/ledger description.
# Numbers (loan or account numbers, amounts, dates, phone fragments) and the
# bank's filler words are dropped, so "Tra no TK vay 8080…, so tien … VND"
# and the accountant's "Tra no goc vay" share one fingerprint core.
# ---------------------------------------------------------------------------
_FINGERPRINT_STOP = frozenset({
    "VND", "THANG", "SO", "TK", "STK", "SDT", "NGAY", "QUA", "CUA", "CHO", "VA", "TAI", "DEN", "TU", "VE",
    "GD", "CK", "MA", "LA", "CAC", "KHOAN", "TIEN", "NO", "CO", "THEO", "VAO", "TREN", "DO", "BOI", "VOI",
    # Generic narrative words: every payment is "thanh toan"/"chuyen tien" something.
    "THANH", "TOAN", "TT", "TTOAN", "CHUYEN", "CHUYENKHOAN", "UNC", "CTY", "CONG", "TY", "CP", "TNHH",
})
# Words that carry the business meaning even when short ("NO" in "TRA NO").
_FINGERPRINT_KEEP = frozenset({"NO"})


@lru_cache(maxsize=131072)
def fingerprint(value: str) -> tuple:
    """Ordered, de-duplicated words of a description with its variable parts removed."""
    text = _normalized(str(value or ""))
    seen, result = set(), []
    for token in re.findall(r"[A-Z0-9]+", text):
        digits = sum(ch.isdigit() for ch in token)
        if token.isdigit() or digits >= 2 or (digits and len(token) <= 3):
            continue                      # amounts, account/loan numbers, dates, "T7", "Q3"
        if len(token) == 1:
            continue
        if token in _FINGERPRINT_STOP and token not in _FINGERPRINT_KEEP:
            continue
        if token not in seen:
            seen.add(token); result.append(token)
    return tuple(result)


def fingerprint_score(left: object, right: object) -> float:
    """Share of the shorter fingerprint found in the longer one (0..1)."""
    a, b = set(fingerprint(str(left or ""))), set(fingerprint(str(right or "")))
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def fingerprint_similar(left: object, right: object, threshold: float = 0.8, ignore: frozenset = frozenset()) -> bool:
    """Fingerprint match with a relaxed rule for very short ledger wordings.

    A four-word voucher text ("TRA NO GOC VAY") against a long bank narrative
    is accepted when all but one of its words are present.  ``ignore`` holds
    words that identify nobody here, such as the own company's name
    ("PLASCHEM HA NAM" appears in half of all vouchers).
    """
    a, b = set(fingerprint(str(left or ""))) - ignore, set(fingerprint(str(right or ""))) - ignore
    if not a or not b:
        return False
    shared, smallest = len(a & b), min(len(a), len(b))
    if shared / smallest >= threshold:
        return True
    return smallest <= 4 and shared >= max(3, smallest - 1)


_BANK_JOURNAL_MEMO: dict[tuple, bool] = {}


def _is_bank_journal(journal: dict) -> bool:
    key = (journal.get("voucher_type"), journal.get("transaction_code"), journal.get("voucher_number"))
    known = _BANK_JOURNAL_MEMO.get(key)
    if known is None:
        if len(_BANK_JOURNAL_MEMO) > 200000:
            _BANK_JOURNAL_MEMO.clear()
        known = _BANK_JOURNAL_MEMO[key] = _is_bank_journal_uncached(journal)
    return known


def _is_bank_journal_uncached(journal: dict) -> bool:
    values = " ".join(str(journal.get(name) or "") for name in ("voucher_type", "transaction_code", "voucher_number"))
    normalized = _normalized(values)
    # Source ledgers often place BR/BP in a dedicated type column.  A Junsky
    # export can instead carry it inside `<unit>BRYYMM-####`; accept that
    # tightly constrained suffix too so its next read is eligible for S7.
    return bool(re.search(r"(^|[^A-Z0-9])(BR|BP)([^A-Z0-9]|$)|(?:BR|BP)\d{4}-\d{4,}$", normalized))


def cash_legs(journal: dict) -> list[dict]:
    """Return the actual 112 legs of one balanced journal, preserving side."""
    result = []
    for line in journal.get("lines", []):
        account = str(line.get("account") or "")
        if not is_cash_detail(account):
            continue
        debit, credit = int(line.get("debit_minor", 0) or 0), int(line.get("credit_minor", 0) or 0)
        if debit:
            result.append({"account": account, "side": "DEBIT", "amount_minor": debit})
        if credit:
            result.append({"account": account, "side": "CREDIT", "amount_minor": credit})
    return result


def merged_cash_legs(journal: dict) -> list[dict]:
    """112 legs summed per (account, side).

    "Sổ NKC có đối ứng" writes one 112 line per opposite line (for example a
    fee line against 6427 and a VAT line against 1331).  The bank sees one
    payment, so matching and learning compare against the merged leg.
    """
    totals: dict[tuple, int] = {}
    order: list[tuple] = []
    for leg in cash_legs(journal):
        key = (leg["account"], leg["side"])
        if key not in totals:
            order.append(key)
        totals[key] = totals.get(key, 0) + leg["amount_minor"]
    return [{"account": account, "side": side, "amount_minor": totals[(account, side)]} for account, side in order]


def journal_bank_leg(journal: dict, direction: str, amount_minor: int) -> dict | None:
    """Find the single cash leg that balances a bank row of the stated direction."""
    expected = "DEBIT" if direction == "IN" else "CREDIT"
    legs = [leg for leg in merged_cash_legs(journal) if leg["side"] == expected and leg["amount_minor"] == abs(amount_minor)]
    return legs[0] if len(legs) == 1 else None


def match_bank_to_journal(bank: dict, journals: Iterable[dict], threshold: float = 0.8, *, require_description: bool = True) -> dict:
    """Match one bank row only when date, 112 amount and description are unique.

    ``require_description=False`` (scoring replay) accepts a sole date+amount
    candidate even when the accountant's wording differs from the bank's; the
    description then only breaks ties.
    """
    direction = "IN" if int(bank.get("amount_minor", 0) or 0) > 0 else "OUT"
    amount = abs(int(bank.get("amount_minor", 0) or 0))
    candidates, loose = [], []
    for journal in journals:
        if not _is_bank_journal(journal) or journal.get("business_date") != bank.get("business_date"):
            continue
        leg = journal_bank_leg(journal, direction, amount)
        if not leg:
            continue
        similarity = text_similarity(bank.get("description"), journal.get("description"))
        entry = {"journal_id": journal["id"], "voucher_number": journal.get("voucher_number") or "", "unit_code": journal.get("unit_code") or "", "cash_account": leg["account"], "similarity": similarity}
        loose.append(entry)
        if similarity >= threshold:
            candidates.append(entry)
    if len(candidates) == 1:
        return {"status": "UNIQUE", **candidates[0], "candidate_count": 1}
    if not require_description and not candidates and len(loose) == 1:
        return {"status": "UNIQUE", **loose[0], "candidate_count": 1}
    return {"status": "AMBIGUOUS" if (candidates or (not require_description and loose)) else "UNMATCHED", "candidate_count": len(candidates or loose)}


def infer_cash_mappings(banks: Iterable[dict], journals: Iterable[dict], threshold: float = 0.8) -> dict[str, dict]:
    """Infer a source account → detailed 112 mapping without looking ahead.

    First prefer documentary S7 matches.  In a cut replay there is no August
    posting yet, so a sole source STK may instead use the sole detailed 112
    found across historical BR/BP vouchers.  That fallback is intentionally
    unavailable when several statement accounts or several cash GLs exist.
    """
    bank_rows = list(banks)
    journal_rows = list(journals)
    grouped: dict[str, list[dict]] = {}
    source_accounts = {bank_account(bank.get("account")) for bank in bank_rows if bank_account(bank.get("account"))}
    for bank in bank_rows:
        account = bank_account(bank.get("account"))
        matched = match_bank_to_journal(bank, journal_rows, threshold)
        if account and matched["status"] == "UNIQUE":
            grouped.setdefault(account, []).append(matched)
    result = {}
    for account, entries in grouped.items():
        cash_accounts = {entry["cash_account"] for entry in entries}
        if len(cash_accounts) == 1:
            result[account] = {"cash_account": next(iter(cash_accounts)), "matches": entries, "evidence_ids": [entry["journal_id"] for entry in entries], "status": "UNIQUE", "basis": "DATE_AMOUNT_DESCRIPTION"}
        else:
            result[account] = {"cash_account": None, "matches": entries, "evidence_ids": [entry["journal_id"] for entry in entries], "status": "CONFLICT", "basis": "DATE_AMOUNT_DESCRIPTION"}
    if len(source_accounts) == 1:
        source_account = next(iter(source_accounts))
        history = [(journal["id"], leg["account"]) for journal in journal_rows if _is_bank_journal(journal) for leg in cash_legs(journal)]
        cash_accounts = {account for _, account in history}
        if source_account not in result and len(cash_accounts) == 1:
            result[source_account] = {"cash_account": next(iter(cash_accounts)), "matches": [], "evidence_ids": [identifier for identifier, _ in history],
                                      "status": "UNIQUE", "basis": "SINGLE_HISTORICAL_CASH_GL"}
    return result


def _description_accounts(value: object) -> set[str]:
    return {candidate for candidate in re.findall(r"\d+", str(value or "")) if len(candidate) >= 6}


def _opposite_accounts(journal: dict, direction: str) -> tuple[str | None, list[dict]]:
    """Return a reusable BR/BP pattern without requiring the same amount.

    Historical vouchers are training examples, not duplicate candidates.  The
    old implementation accidentally required their amount to equal the new
    bank row, which prevented learning from the usual case: the same type of
    payment at another amount.  A usable pattern has exactly one 112 leg on
    the expected side and its non-cash legs on the balancing side.  The
    original amounts are retained as integer numerators so Engine can scale a
    multi-line pattern (including 1331) safely for a new transaction.
    """
    expected = "DEBIT" if direction == "IN" else "CREDIT"
    legs = [leg for leg in merged_cash_legs(journal) if leg["side"] == expected]
    if len(legs) != 1 or legs[0]["amount_minor"] <= 0:
        return None, []
    cash = legs[0]
    opposite_side = "CREDIT" if direction == "IN" else "DEBIT"
    totals: dict[str, int] = {}
    order: list[str] = []
    for line in journal.get("lines", []):
        account = str(line.get("account") or "")
        debit, credit = int(line.get("debit_minor", 0) or 0), int(line.get("credit_minor", 0) or 0)
        if account.startswith("112"):
            continue
        value = credit if opposite_side == "CREDIT" else debit
        if value:
            if account not in totals:
                order.append(account)
            totals[account] = totals.get(account, 0) + value
    lines = [{"account": account, "side": opposite_side, "amount_minor": totals[account]} for account in sorted(order)]
    if not lines or sum(line["amount_minor"] for line in lines) != cash["amount_minor"]:
        return None, []
    # The header field remains useful to the existing screen.  For an actual
    # multi-line voucher it is the highest-value non-cash account; `lines`
    # remains the complete accounting structure and is what export uses.
    primary = max(lines, key=lambda item: (item["amount_minor"], item["account"]))["account"]
    return primary, lines


def materialize_journal_pattern(pattern_lines: list[dict], *, direction: str, cash_account: str,
                                amount_minor: int, currency: str, dimensions: dict | None = None) -> list[dict]:
    """Scale a balanced learned pattern to one bank amount without float math."""
    if not pattern_lines or amount_minor <= 0 or not cash_account:
        return []
    denominator = sum(int(item.get("amount_minor", 0) or 0) for item in pattern_lines)
    if denominator <= 0:
        return []
    dimensions = dimensions or {}
    result, allocated = [], 0
    for index, item in enumerate(pattern_lines, 1):
        original = int(item.get("amount_minor", 0) or 0)
        value = amount_minor - allocated if index == len(pattern_lines) else amount_minor * original // denominator
        allocated += value
        if not value:
            continue
        result.append({"line_id": f"LEARN-{index:03d}", "account": item["account"], "currency": currency,
                       "debit_minor": value if item["side"] == "DEBIT" else 0,
                       "credit_minor": value if item["side"] == "CREDIT" else 0,
                       "tax_basis": "JOURNAL_PATTERN", "state": "READY",
                       "dimensions": {key: dimensions.get(key) for key in ("project", "expense", "cost_center") if dimensions.get(key)}})
    cash_side = "DEBIT" if direction == "IN" else "CREDIT"
    result.append({"line_id": "LEARN-CASH", "account": cash_account, "currency": currency,
                   "debit_minor": amount_minor if cash_side == "DEBIT" else 0,
                   "credit_minor": amount_minor if cash_side == "CREDIT" else 0,
                   "tax_basis": "BANK_AMOUNT", "state": "READY", "dimensions": {}})
    debit = sum(item["debit_minor"] for item in result)
    credit = sum(item["credit_minor"] for item in result)
    return result if debit == credit == amount_minor else []


def _month(value: str) -> str:
    text = str(value or "")[:7]
    return (text[5:7] + "/" + text[:4]) if len(text) == 7 else text


def journal_suggestion(bank: dict, journals: Iterable[dict], *, cutoff_day: str, own_codes: set[str], object_learning_from: str,
                       threshold: float = 0.8, cash_account: str = "", window_days: int = 365, counterparty_code: str = "",
                       ignore_words: frozenset = frozenset()) -> dict | None:
    """Learn a pending pattern from BR/BP vouchers known before the cutoff.

    V11: samples are found by description *fingerprint* (numbers and filler
    words removed), vouchers with VAT split lines count (merged 112 legs), and
    the consensus is measured on the most recent window so an old practice
    (for example capitalising fees in 2024) does not dilute the current one.
    The returned ``stats`` are what the screen shows as the measured odds.

    Account/project/expense evidence may use all history.  Counterparty evidence
    begins only at ``object_learning_from`` and filters codes of the own entity.
    """
    direction = "IN" if int(bank.get("amount_minor", 0) or 0) > 0 else "OUT"
    target_account = bank_account(bank.get("counterparty_account"))
    same_account, similar, same_party = [], [], []
    for journal in journals:
        if not _is_bank_journal(journal) or str(journal.get("business_date") or "") >= cutoff_day:
            continue
        counterpart, lines = _opposite_accounts(journal, direction)
        if not counterpart:
            continue
        account_hit = bool(target_account and target_account in _description_accounts(journal.get("description")))
        entry = {"journal": journal, "counterpart": counterpart, "lines": lines, "account_hit": account_hit,
                 "cash": next((leg["account"] for leg in merged_cash_legs(journal) if leg["side"] == ("DEBIT" if direction == "IN" else "CREDIT")), "")}
        if account_hit:
            same_account.append(entry)
        elif fingerprint_similar(bank.get("description"), journal.get("description"), threshold, ignore_words):
            similar.append(entry)
        elif counterparty_code and str(journal.get("counterparty") or "") == counterparty_code:
            # V11: the identified counterparty's own earlier receipts/payments.
            same_party.append(entry)
    basis = "COUNTERPARTY_BANK_ACCOUNT" if same_account else "DESCRIPTION_SIMILARITY" if similar else "COUNTERPARTY_HISTORY"
    candidates = same_account or similar or same_party
    if not candidates:
        return None
    total_found = len(candidates)
    # Prefer vouchers on the same detailed 112 account when that is known and
    # leaves enough samples: another bank account may follow another practice.
    if cash_account:
        same_cash = [entry for entry in candidates if entry["cash"] == cash_account]
        if len(same_cash) >= 3 or (same_cash and len(same_cash) == len(candidates)):
            candidates = same_cash
    # Keep ledger order for ids/evidence; use dates only to pick the window.
    latest = max(str(entry["journal"].get("business_date") or "") for entry in candidates)
    window = candidates
    if latest and window_days:
        from datetime import date as _date, timedelta as _timedelta
        try:
            floor = (_date.fromisoformat(latest[:10]) - _timedelta(days=window_days)).isoformat()
            recent = [entry for entry in candidates if str(entry["journal"].get("business_date") or "") >= floor]
            if len(recent) >= 3:
                window = recent
        except ValueError:
            pass
    # A pattern is strong only if every selected sample has the same complete
    # opposite-account structure.  This is stricter than merely agreeing on a
    # primary account, and keeps VAT split (for example 6427 + 1331) intact.
    signatures = [tuple((line["account"], line["side"]) for line in entry["lines"]) for entry in window]
    signature, signature_count = Counter(signatures).most_common(1)[0]
    matching = [entry for entry, item_signature in zip(window, signatures) if item_signature == signature]
    values: dict[str, list[str]] = {"debit_account": [], "credit_account": [], "counterparty": [], "project": [], "expense": [], "cost_center": []}
    for entry in window:
        journal = entry["journal"]
        if direction == "IN":
            values["credit_account"].append(entry["counterpart"])
        else:
            values["debit_account"].append(entry["counterpart"])
        party = str(journal.get("counterparty") or "")
        if str(journal.get("business_date") or "") >= object_learning_from and party and party not in own_codes:
            values["counterparty"].append(party)
        for field, name in (("project", "project"), ("expense", "expense"), ("cost_center", "cost_center")):
            value = str(journal.get(name) or "")
            if value:
                values[field].append(value)
    fields, field_counts = {}, {}
    for field, options in values.items():
        if not options:
            continue
        winner, count = Counter(options).most_common(1)[0]
        # V11: a clear majority (≥ 80 % of the window, at least 2) is proposed
        # as a weak value; only unanimity can make the pattern strong below.
        if count == len(window) or (count >= 2 and count / len(window) >= 0.8):
            fields[field] = winner
            field_counts[field] = count
    # Do not claim a full learned line structure if only a subset agrees.  The
    # header fields may still be a useful weak proposal, but it must wait.
    unanimous = all(field_counts.get(field, 0) == len(window) for field in ("debit_account", "credit_account") if field in fields)
    strong = len(window) >= 3 and signature_count == len(window) and unanimous and bool(fields.get("debit_account") or fields.get("credit_account"))
    sample_ids = [entry["journal"]["id"] for entry in window]
    sample_vouchers = [entry["journal"].get("voucher_number") or "" for entry in window]
    account_words = "; ".join(f"{'Nợ' if side == 'DEBIT' else 'Có'} {account}" for account, side in signature)
    dates = sorted(str(entry["journal"].get("business_date") or "") for entry in window)
    first_month, last_month = _month(dates[0]), _month(dates[-1])
    span = first_month if first_month == last_month else f"{first_month}–{last_month}"
    stats = {"window": len(window), "consistent": signature_count, "total": total_found, "from": first_month, "to": last_month,
             "share": round(signature_count / len(window), 3) if window else 0.0}
    if basis == "COUNTERPARTY_BANK_ACCOUNT":
        reason = f"{signature_count}/{len(window)} lần trước cùng STK ({span}) hạch toán {account_words}."
    elif basis == "DESCRIPTION_SIMILARITY":
        reason = f"{signature_count}/{len(window)} chứng từ có diễn giải cùng dạng ({span}) hạch toán {account_words}."
    else:
        reason = f"{signature_count}/{len(window)} chứng từ trước của đối tượng này ({span}) hạch toán {account_words}."
    if total_found > len(window):
        reason = reason.rstrip(".") + f"; xét {len(window)} chứng từ gần nhất trong {total_found} chứng từ tương tự."
    # V10: every distinct structure found among the samples, most frequent
    # first.  The screen offers them as "phương án" when samples disagree;
    # nothing here is approved or used for export by itself.
    grouped_signatures: dict[tuple, list[dict]] = {}
    for entry, item_signature in zip(window, signatures):
        grouped_signatures.setdefault(item_signature, []).append(entry)
    alternatives = []
    for item_signature, entries in sorted(grouped_signatures.items(), key=lambda pair: (-len(pair[1]), pair[0]))[:3]:
        alternatives.append({"lines": [dict(item) for item in entries[0]["lines"]], "count": len(entries),
                             "source_ids": [entry["journal"]["id"] for entry in entries],
                             "source_vouchers": [entry["journal"].get("voucher_number") or "" for entry in entries]})
    return {"fields": {key: value for key, value in fields.items() if key != "cost_center"},
            "dimensions": {"cost_center": fields.get("cost_center")},
            "signatures": alternatives,
            "pattern_lines": [dict(item) for item in matching[0]["lines"]] if strong and matching else [],
            "strength": "PENDING_PATTERN_STRONG" if strong else "PENDING_PATTERN_WEAK", "count": len(window),
            "stats": stats,
            "source_ids": sample_ids, "source_vouchers": sample_vouchers, "why": reason,
            "match_basis": basis}


def offset_account_ranking(journals: Iterable[dict], direction: str, cutoff_day: str, limit: int = 5, description: object = None,
                           ignore_words: frozenset = frozenset()) -> list[str]:
    """Most frequent non-cash accounts of earlier BR/BP vouchers for one direction.

    Used only as clickable hints for a row that lacks its offset account.
    V11: when a description is given, vouchers sharing at least two
    fingerprint words with it are counted first ("tra no vay" → 341x), and
    the overall ranking is only the fallback.
    """
    counts: Counter = Counter()
    context: Counter = Counter()
    words = (set(fingerprint(str(description or ""))) - ignore_words) if description else set()
    for journal in journals:
        if not _is_bank_journal(journal) or str(journal.get("business_date") or "") >= cutoff_day:
            continue
        primary, lines = _opposite_accounts(journal, direction)
        if not primary:
            continue
        # V13: duyệt theo thứ tự sắp xếp để thứ tự gợi ý khi đồng hạng không phụ thuộc hash của tiến trình Python
        accounts = sorted({line["account"] for line in lines})
        counts.update(accounts)
        if words:
            shared = len(words & (set(fingerprint(str(journal.get("description") or ""))) - ignore_words))
            if shared >= 2 or (shared == 1 and len(words) == 1):
                context.update(accounts)
    if context:
        ranked = [account for account, _ in context.most_common(limit)]
        for account, _ in counts.most_common():
            if len(ranked) >= limit:
                break
            if account not in ranked:
                ranked.append(account)
        return ranked
    return [account for account, _ in counts.most_common(limit)]


def match_bank_groups_to_journal(banks: Iterable[dict], journals: Iterable[dict], threshold: float = 0.8) -> dict[str, dict]:
    """Several bank rows of one day and one counterparty ↔ one voucher.

    A customer often splits a payment into transfers below a limit while the
    accountant books one receipt per day.  Rows are grouped by day, direction
    and counterparty (account number, else name); a group of two or more rows
    whose total equals exactly one voucher's merged 112 leg is reported for
    every member.  Rows that already match on their own are left alone.
    """
    rows = [bank for bank in banks if bank.get("kind", "BANK") == "BANK"]
    journal_rows = [journal for journal in journals if _is_bank_journal(journal)]
    # Vouchers already explained by one row on its own are never shared.
    singles = {bank["id"]: match_bank_to_journal(bank, journal_rows, threshold) for bank in rows}
    claimed = {match["journal_id"] for match in singles.values() if match["status"] == "UNIQUE"}
    groups: dict[tuple, list[dict]] = {}
    for bank in rows:
        if singles[bank["id"]]["status"] == "UNIQUE":
            continue
        key_value = bank_account(bank.get("counterparty_account")) or _normalized(str(bank.get("counterparty_name") or ""))
        if not key_value:
            continue
        direction = "IN" if int(bank.get("amount_minor", 0) or 0) > 0 else "OUT"
        groups.setdefault((str(bank.get("business_date") or ""), direction, key_value), []).append(bank)
    proposals: dict[str, list[tuple]] = {}
    for (day, direction, _key), members in groups.items():
        if len(members) < 2:
            continue
        total = sum(abs(int(bank.get("amount_minor", 0) or 0)) for bank in members)
        hits = []
        for journal in journal_rows:
            if journal.get("business_date") != day or journal["id"] in claimed:
                continue
            leg = journal_bank_leg(journal, direction, total)
            if leg:
                hits.append({"journal_id": journal["id"], "voucher_number": journal.get("voucher_number") or "", "unit_code": journal.get("unit_code") or "", "cash_account": leg["account"]})
        if len(hits) == 1:
            proposals.setdefault(hits[0]["journal_id"], []).append((members, hits[0], total))
    result: dict[str, dict] = {}
    for journal_id, claims in proposals.items():
        if len(claims) != 1:
            continue  # two groups add up to the same voucher: nobody is marked
        members, hit, total = claims[0]
        for bank in members:
            result[bank["id"]] = {"status": "UNIQUE", **hit, "similarity": 1.0, "candidate_count": 1,
                                  "group": {"size": len(members), "total_minor": total, "bank_ids": [member["id"] for member in members]}}
    return result
