"""Lịch sử hóa đơn ↔ chứng từ Junsky (V12).

Hóa đơn điện tử không mang tài khoản kế toán.  Muốn đề xuất bút toán cho một
hóa đơn mới, phần mềm nhìn lại các hóa đơn TRƯỚC ĐÓ của cùng người bán / người
mua và tìm chứng từ Junsky đã hạch toán chúng.  Sổ Junsky phần lớn không ghi
số hóa đơn, nên việc ghép dựa trên số tiền:

* hóa đơn mua vào ↔ chứng từ có dòng Nợ (không phải 1331/111/112) bằng tiền
  chưa thuế và dòng Nợ 1331 bằng tiền thuế;
* hóa đơn bán ra ↔ chứng từ có dòng Có (không phải 333x) bằng tiền chưa thuế
  và dòng Có 3331x bằng tiền thuế;

trong khoảng 20 ngày trước đến 75 ngày sau ngày hóa đơn, ưu tiên chứng từ cùng
đối tượng rồi gần ngày nhất.  Mỗi cặp ghép là một "liên kết" mang tài khoản,
tài khoản công nợ, dự án, khoản mục.  Không có gì ở đây được duyệt; đây chỉ là
căn cứ đo được (n/n hóa đơn trước) cho màn hình.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Iterable

import re

from ..giao_dien.v9b import fingerprint_similar
from ..ha_tang.primitives import normalize_text

WINDOW_BEFORE, WINDOW_AFTER = 20, 75
TOLERANCE = 2  # VND


def _amount(line: dict, side: str) -> int:
    value = line.get(side + "_minor")
    if value is None:
        value = line.get(side, 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _close(left: int, right: int) -> bool:
    return abs(int(left) - int(right)) <= TOLERANCE


def _invoice_amounts(invoice: dict) -> tuple[int, int, int]:
    net = invoice.get("net_minor", invoice.get("net_amount"))
    tax = invoice.get("tax_minor", invoice.get("tax_amount", 0))
    total = invoice.get("total_minor", invoice.get("total_amount", invoice.get("amount_minor", invoice.get("amount"))))
    return int(net or 0), int(tax or 0), int(total or 0)


def invoice_text(invoice: dict, limit: int = 4) -> str:
    return " ".join(str(line.get("description") or "") for line in (invoice.get("lines") or [])[:limit])


_REFERENCE = re.compile(r"\b(THEO|HOP DONG|HD SO|HD|SO HD|CAN CU|DINH KEM|KEM THEO)\b")


def item_core(invoice_or_text) -> str:
    """The item names without contract/request references.

    "Phí quản lý năm 2026 … theo hợp đồng số 1304/2026/KCN/…" and "Phí sử dụng
    hạ tầng … theo hợp đồng số 1304/2026/KCN/…" are different services of the
    same contract; only the part before the reference tells them apart.
    """
    lines = [str(line.get("description") or "") for line in (invoice_or_text.get("lines") or [])[:4]] if isinstance(invoice_or_text, dict) else [str(invoice_or_text or "")]
    parts = []
    for line in lines:
        text = normalize_text(line)
        found = _REFERENCE.search(text)
        parts.append(text[:found.start()] if found and found.start() > 0 else text)
    return " ".join(parts)


def party_tax_id(invoice: dict) -> str:
    return str((invoice.get("seller_tax_id") if invoice.get("direction") == "MUA_VAO" else invoice.get("buyer_tax_id")) or "").strip()


class JournalIndex:
    """Posted vouchers indexed by the amounts an invoice can be matched on."""

    def __init__(self, journals: Iterable[dict]):
        self.purchase: dict[int, list[tuple[dict, dict]]] = {}
        self.sale: dict[int, list[tuple[dict, dict]]] = {}
        for journal in journals:
            for line in journal.get("lines") or []:
                account = str(line.get("account") or "")
                debit, credit = _amount(line, "debit"), _amount(line, "credit")
                # A debit to a payable (33x) is a payment, a credit to a
                # receivable (13x) is a collection: neither posts an invoice.
                if debit and not account.startswith(("1331", "1332", "111", "112", "113", "33")):
                    self.purchase.setdefault(debit, []).append((journal, line))
                if credit and not account.startswith(("333", "111", "112", "113", "13")):
                    self.sale.setdefault(credit, []).append((journal, line))

    def _near(self, table: dict, amount: int):
        for key in range(amount - TOLERANCE, amount + TOLERANCE + 1):
            yield from table.get(key, ())

    def link(self, invoice: dict, party_code: str = "", *, last_day: str = "") -> dict | None:
        """The voucher that posted this invoice, or None (see module notes)."""
        purchase = invoice.get("direction") == "MUA_VAO"
        net, tax, total = _invoice_amounts(invoice)
        if net <= 0:
            return None
        try:
            day = date.fromisoformat(str(invoice.get("business_date"))[:10])
        except ValueError:
            return None
        low, high = (day - timedelta(days=WINDOW_BEFORE)).isoformat(), (day + timedelta(days=WINDOW_AFTER)).isoformat()
        if last_day:
            high = min(high, last_day)
        best = None
        for journal, line in self._near(self.purchase if purchase else self.sale, net):
            journal_day = str(journal.get("business_date") or "")[:10]
            if not low <= journal_day <= high:
                continue
            lines = journal.get("lines") or []
            if not purchase and any(str(item.get("account") or "").startswith(("111", "112", "113")) and _amount(item, "debit") for item in lines):
                continue  # money received: a collection, not the sale itself
            if tax:
                if purchase and not any(str(item.get("account") or "").startswith("1331") and _close(_amount(item, "debit"), tax) for item in lines):
                    continue
                if not purchase and not any(str(item.get("account") or "").startswith("3331") and _close(_amount(item, "credit"), tax) for item in lines):
                    continue
            same_party = bool(party_code) and str(journal.get("counterparty") or "") == party_code
            rank = (0 if same_party else 1, abs((date.fromisoformat(journal_day) - day).days))
            if best is None or rank < best[0]:
                best = (rank, journal, line)
        if best is None:
            return None
        _, journal, line = best
        lines = journal.get("lines") or []
        if purchase:
            partner = next((str(item.get("account") or "") for item in lines if _amount(item, "credit") and (_close(_amount(item, "credit"), net) or _close(_amount(item, "credit"), total))), "")
            partner = partner or next((str(item.get("account") or "") for item in lines if _amount(item, "credit")), "")
        else:
            partner = next((str(item.get("account") or "") for item in lines if _amount(item, "debit") and (_close(_amount(item, "debit"), net) or _close(_amount(item, "debit"), total))), "")
            partner = partner or next((str(item.get("account") or "") for item in lines if _amount(item, "debit")), "")
        return {"journal_id": journal.get("id"), "voucher": journal.get("voucher_number") or "", "voucher_type": journal.get("voucher_type") or "",
                "journal_date": str(journal.get("business_date") or "")[:10], "journal_party": str(journal.get("counterparty") or ""),
                "account": str(line.get("account") or ""), "partner_account": partner, "project": str(journal.get("project") or ""),
                "expense": str(journal.get("expense") or ""), "cost_center": str(journal.get("cost_center") or ""),
                "description": str(journal.get("description") or "")}


def build_history(invoices: Iterable[dict], journals: list[dict], *, party_of: Callable[[str], str] | None = None,
                  first_day: str = "", last_day: str = "", journal_last_day: str = "") -> list[dict]:
    """Links between earlier invoices (``first_day``–``last_day``) and the
    vouchers that posted them (vouchers dated up to ``journal_last_day``)."""
    index = JournalIndex(journals)
    links = []
    for invoice in invoices:
        day = str(invoice.get("business_date") or "")[:10]
        if (first_day and day < first_day) or (last_day and day > last_day):
            continue
        tax_id = party_tax_id(invoice)
        code = party_of(tax_id) if (party_of and tax_id) else ""
        link = index.link(invoice, code or "", last_day=journal_last_day)
        if link:
            links.append({**link, "direction": invoice.get("direction"), "tax_id": tax_id, "party_code": code or "",
                          "date": day, "text": invoice_text(invoice), "core": item_core(invoice)})
    links.sort(key=lambda item: item["date"])
    return links


def _month(day: str) -> str:
    return day[5:7] + "/" + day[:4] if len(day) >= 7 else day


MAJORITY = 0.75  # measured on T7–T8 2026 (learning cut 30/06): 0.6 adds wrong proposals


def _evaluate(candidates: list[dict], basis: str, window: int) -> dict:
    candidates = candidates[-window:]
    signatures = Counter((link["account"], link["partner_account"]) for link in candidates)
    (account, partner), count = signatures.most_common(1)[0]
    total = len(candidates)
    unanimous = count == total
    majority = count >= 2 and count / total >= MAJORITY
    if basis in ("PARTY_ITEM", "PARTY"):
        strength = "STRONG" if unanimous and total >= 3 else "WEAK" if (unanimous or majority) else None
    elif basis == "ITEM":
        strength = "STRONG" if unanimous and total >= 4 else "WEAK" if ((unanimous and total >= 2) or majority) else None
    else:
        strength = "WEAK" if (unanimous or majority) else None
    return {"candidates": candidates, "signatures": signatures, "account": account, "partner": partner,
            "count": count, "total": total, "strength": strength, "basis": basis}


def suggest(invoice: dict, history: list[dict], *, ignore_words: frozenset = frozenset(), window: int = 12) -> dict | None:
    """Measured proposal for one invoice from earlier, already posted invoices.

    Evidence is tried in order and the first conclusive one wins: the same
    party with similar item text; any party with similar item text (a
    customer buying a new kind of service is booked like the other customers
    of that service); the party's history whatever the items — the last one
    is never more than "weak" when the items differ.  With nothing
    conclusive, the first one is returned without strength so the screen can
    show the options.
    """
    direction, tax_id, text = invoice.get("direction"), party_tax_id(invoice), item_core(invoice)
    same_direction = [link for link in history if link["direction"] == direction and link["date"] < str(invoice.get("business_date") or "9999")[:10]]
    party = [link for link in same_direction if tax_id and link["tax_id"] == tax_id]
    similar = (lambda link: fingerprint_similar(text, link.get("core") or link["text"], 0.75, ignore_words)) if text.strip() else (lambda link: False)
    party_item = [link for link in party if similar(link)]
    item_all = [link for link in same_direction if similar(link)]
    tiers = []
    if party_item:
        tiers.append((party_item, "PARTY_ITEM"))
    if item_all:
        tiers.append((item_all, "ITEM"))
    if party:
        tiers.append((party, "PARTY" if not text.strip() else "PARTY_OTHER_ITEMS"))
    if not tiers:
        return None
    chosen = None
    for candidates, basis in tiers:
        found = _evaluate(candidates, basis, window)
        if found["strength"]:
            chosen = found
            break
    chosen = chosen or _evaluate(*tiers[0], window)
    candidates, basis, account, partner = chosen["candidates"], chosen["basis"], chosen["account"], chosen["partner"]
    count, total, strength, signatures = chosen["count"], chosen["total"], chosen["strength"], chosen["signatures"]
    winners = [link for link in candidates if (link["account"], link["partner_account"]) == (account, partner)]
    first, last = _month(candidates[0]["date"]), _month(candidates[-1]["date"])
    span = first if first == last else f"{first}–{last}"
    stats = {"window": total, "consistent": count, "total": total, "from": first, "to": last, "share": round(count / total, 3)}
    role = "người bán" if direction == "MUA_VAO" else "người mua"
    who = {"PARTY": f"của {role} này", "PARTY_ITEM": f"của {role} này có tên hàng tương tự",
           "ITEM": "có tên hàng tương tự (các đối tác)", "PARTY_OTHER_ITEMS": f"của {role} này (tên hàng khác — cần xem)"}[basis]
    purchase = direction == "MUA_VAO"
    words = (f"Nợ {account} / Có {partner}" if purchase else f"Nợ {partner} / Có {account}")
    why = f"{count}/{total} hóa đơn trước {who} ({span}) hạch toán {words}."
    dimensions = {}
    for name in ("project", "expense", "cost_center"):
        # The project of the matching invoices; the engine weighs it against
        # the project the party's own vouchers carry.
        values = Counter(link[name] for link in winners if link[name])
        if values:
            value, hits = values.most_common(1)[0]
            dimensions[name] = {"value": value, "count": hits, "total": len(winners), "unanimous": hits == len(winners)}
    # Small purchases bought by an employee are booked in Junsky against the
    # employee (Có 331 · NV.x), not the seller.
    recent = party[-window:]
    employees = Counter(link["journal_party"] for link in recent if str(link.get("journal_party") or "").startswith("NV."))
    payer = {"count": sum(employees.values()), "total": len(recent), "codes": [code for code, _ in employees.most_common(5)]} if employees else None
    alternatives = [{"account": acc, "partner_account": part, "count": n} for (acc, part), n in signatures.most_common(3)]
    return {"account": account, "partner_account": partner, "strength": strength, "basis": basis, "stats": stats, "why": why,
            "dimensions": dimensions, "alternatives": alternatives, "employee_payer": payer,
            "source_ids": [link["journal_id"] for link in winners if link.get("journal_id")][-10:],
            "source_vouchers": [link["voucher"] for link in winners][-10:],
            "paid_directly": partner.startswith(("111", "112")) if purchase else False}


def month_bounds(day: str, months_back: int) -> str:
    """First day of the month ``months_back`` months before ``day`` (yyyy-mm-dd)."""
    year, month = int(day[:4]), int(day[5:7])
    month -= months_back
    while month <= 0:
        month += 12; year -= 1
    return f"{year:04d}-{month:02d}-01"


def history_files(root: Path, first_day: str, last_day: str) -> list[Path]:
    """XML files of the month folders that may hold invoices between the two days."""
    files = []
    if not root.is_dir():
        return files
    for folder in sorted(root.iterdir()):
        name = folder.name
        if not folder.is_dir() or len(name) != 7 or name[4] != "-":
            continue
        if name < first_day[:7] or name > last_day[:7]:
            continue
        for side in ("mua_vao", "ban_ra"):
            if (folder / side).is_dir():
                files.extend(sorted((folder / side).glob("*.xml")))
    return files
