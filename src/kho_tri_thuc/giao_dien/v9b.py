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


def journal_bank_leg(journal: dict, direction: str, amount_minor: int) -> dict | None:
    """Find the single cash leg that balances a bank row of the stated direction."""
    expected = "DEBIT" if direction == "IN" else "CREDIT"
    legs = [leg for leg in cash_legs(journal) if leg["side"] == expected and leg["amount_minor"] == abs(amount_minor)]
    return legs[0] if len(legs) == 1 else None


def match_bank_to_journal(bank: dict, journals: Iterable[dict], threshold: float = 0.8) -> dict:
    """Match one bank row only when date, 112 amount and description are unique."""
    direction = "IN" if int(bank.get("amount_minor", 0) or 0) > 0 else "OUT"
    amount = abs(int(bank.get("amount_minor", 0) or 0))
    candidates = []
    for journal in journals:
        if not _is_bank_journal(journal) or journal.get("business_date") != bank.get("business_date"):
            continue
        leg = journal_bank_leg(journal, direction, amount)
        if not leg:
            continue
        similarity = text_similarity(bank.get("description"), journal.get("description"))
        if similarity >= threshold:
            candidates.append({"journal_id": journal["id"], "voucher_number": journal.get("voucher_number") or "", "unit_code": journal.get("unit_code") or "", "cash_account": leg["account"], "similarity": similarity})
    if len(candidates) == 1:
        return {"status": "UNIQUE", **candidates[0], "candidate_count": 1}
    return {"status": "AMBIGUOUS" if candidates else "UNMATCHED", "candidate_count": len(candidates)}


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
    legs = [leg for leg in cash_legs(journal) if leg["side"] == expected]
    if len(legs) != 1 or legs[0]["amount_minor"] <= 0:
        return None, []
    cash = legs[0]
    opposite_side = "CREDIT" if direction == "IN" else "DEBIT"
    lines = []
    for line in journal.get("lines", []):
        account = str(line.get("account") or "")
        debit, credit = int(line.get("debit_minor", 0) or 0), int(line.get("credit_minor", 0) or 0)
        if account.startswith("112"):
            continue
        value = credit if opposite_side == "CREDIT" else debit
        if value:
            lines.append({"account": account, "side": opposite_side, "amount_minor": value})
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


def journal_suggestion(bank: dict, journals: Iterable[dict], *, cutoff_day: str, own_codes: set[str], object_learning_from: str, threshold: float = 0.8) -> dict | None:
    """Learn a pending pattern from BR/BP vouchers known before the cutoff.

    Account/project/expense evidence may use all history.  Counterparty evidence
    begins only at ``object_learning_from`` and filters codes of the own entity.
    """
    direction = "IN" if int(bank.get("amount_minor", 0) or 0) > 0 else "OUT"
    amount = abs(int(bank.get("amount_minor", 0) or 0))
    target_account = bank_account(bank.get("counterparty_account"))
    same_account, similar = [], []
    for journal in journals:
        if not _is_bank_journal(journal) or str(journal.get("business_date") or "") >= cutoff_day:
            continue
        counterpart, lines = _opposite_accounts(journal, direction)
        if not counterpart:
            continue
        account_hit = bool(target_account and target_account in _description_accounts(journal.get("description")))
        entry = {"journal": journal, "counterpart": counterpart, "lines": lines, "account_hit": account_hit}
        if account_hit:
            same_account.append(entry)
        elif similar_at_least(bank.get("description"), journal.get("description"), threshold):
            similar.append(entry)
    candidates = same_account or similar
    if not candidates:
        return None
    # A pattern is strong only if every selected sample has the same complete
    # opposite-account structure.  This is stricter than merely agreeing on a
    # primary account, and keeps VAT split (for example 6427 + 1331) intact.
    signatures = [tuple((line["account"], line["side"]) for line in entry["lines"]) for entry in candidates]
    signature, signature_count = Counter(signatures).most_common(1)[0]
    matching = [entry for entry, item_signature in zip(candidates, signatures) if item_signature == signature]
    values: dict[str, list[str]] = {"debit_account": [], "credit_account": [], "counterparty": [], "project": [], "expense": [], "cost_center": []}
    for entry in candidates:
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
        if count == len(candidates):
            fields[field] = winner
            field_counts[field] = count
    # Do not claim a full learned line structure if only a subset agrees.  The
    # header fields may still be a useful weak proposal, but it must wait.
    strong = len(candidates) >= 3 and signature_count == len(candidates) and bool(fields.get("debit_account") or fields.get("credit_account"))
    sample_ids = [entry["journal"]["id"] for entry in candidates]
    sample_vouchers = [entry["journal"].get("voucher_number") or "" for entry in candidates]
    account_words = "; ".join(f"{'Nợ' if side == 'DEBIT' else 'Có'} {account}" for account, side in signature)
    reason = (f"{len(candidates)}/{len(candidates)} lần trước cùng STK hạch toán {account_words}."
              if same_account else f"{len(candidates)} mẫu có diễn giải tương tự trước thời điểm chấm.")
    # V10: every distinct structure found among the samples, most frequent
    # first.  The screen offers them as "phương án" when samples disagree;
    # nothing here is approved or used for export by itself.
    grouped_signatures: dict[tuple, list[dict]] = {}
    for entry, item_signature in zip(candidates, signatures):
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
            "strength": "PENDING_PATTERN_STRONG" if strong else "PENDING_PATTERN_WEAK", "count": len(candidates),
            "source_ids": sample_ids, "source_vouchers": sample_vouchers, "why": reason,
            "match_basis": "COUNTERPARTY_BANK_ACCOUNT" if same_account else "DESCRIPTION_SIMILARITY"}


def offset_account_ranking(journals: Iterable[dict], direction: str, cutoff_day: str, limit: int = 5) -> list[str]:
    """Most frequent non-cash accounts of earlier BR/BP vouchers for one direction.

    Used only as clickable hints for a row that lacks its offset account.
    """
    counts: Counter = Counter()
    for journal in journals:
        if not _is_bank_journal(journal) or str(journal.get("business_date") or "") >= cutoff_day:
            continue
        primary, lines = _opposite_accounts(journal, direction)
        if primary:
            counts.update({line["account"] for line in lines})
    return [account for account, _ in counts.most_common(limit)]
