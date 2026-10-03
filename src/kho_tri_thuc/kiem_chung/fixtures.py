"""Explicit synthetic examples. These definitions are NOT Junsky mappings."""
from __future__ import annotations

import copy
import json
from datetime import date, timedelta
from pathlib import Path

from ..de_xuat.engine import FIELDS

KNOWN = "2026-09-15T00:00:00Z"
CUTOFF = "2026-09-16T01:00:00Z"
REVIEW_AT = "2026-09-16T01:30:00Z"
EXPORT_AT = "2026-09-16T02:00:00Z"
VERIFY_AT = "2026-09-16T04:00:00Z"
FIELD_VALUES = {"counterparty": "0001", "debit_account": "331_FIXTURE", "credit_account": "112_FIXTURE", "project": "0001", "expense": "0001"}


def envelope(source, records, *, snapshot="SNAP_FIXTURE_0", exported="2026-09-16T00:00:00Z", as_of="2026-09-16"):
    totals = {}
    for record in records:
        kind = record.get("kind", "BANK" if source == "sao_ke" else "")
        if "amount" in record:
            key = kind + "/" + record["currency"]
            totals[key] = str(int(totals.get(key, 0)) + int(record["amount"]))
    controls = {"count": len(records), "totals": totals}
    if source == "sao_ke":
        controls.update(opening_balance="1000000", closing_balance=str(1000000 + int(totals.get("BANK/VND", 0))))
    return {"format": "ktt-fixture-v1", "synthetic": True, "source": source,
            "manifest": {"entity_id": "PLHN_FIXTURE", "source_system": "SYNTHETIC_FULL_PIPELINE", "as_of": as_of,
                         "coverage_from": "2026-09-01", "coverage_to_exclusive": (date.fromisoformat(as_of) + timedelta(days=1)).isoformat(), "exported_at": exported, "known_at": exported,
                         "known_at_basis": "SYNTHETIC CLOCK, NOT HISTORICAL EVIDENCE", "scope": "all synthetic example records",
                         "snapshot_id": snapshot, "posting_evidence_complete": True, "scope_open_items_complete": True},
            "controls": controls, "records": records}


def bank_fixture(count=2):
    records = [{"business_date": "2026-09-15", "currency": "VND", "amount": "-100", "bank": "BANK_FIXTURE", "account": "00001234",
                "id_scope": "stable-fixture-v1", "reference": f"PAY{i:03d}", "identity_verified": True, "description": "Thanh toán hóa đơn giả lập",
                "counterparty_account": "00009999", "invoice_references": ["HD_FIXTURE_001"]} for i in range(1, count + 1)]
    return envelope("sao_ke", records)


def journal_fixture(number="PLACEHOLDER", *, payload=None, item_id=None, batch_id=None):
    fields = payload["fields"] if payload else FIELD_VALUES
    amount = abs(payload["amount_minor"]) if payload else 1
    row = {"kind": "JOURNAL", "business_date": payload["business_date"] if payload else "2026-09-01", "currency": "VND", "amount": "0",
           "book": "NKC_FIXTURE", "fiscal_year": "2026", "voucher_type": "FIXTURE_ONLY", "voucher_number": number,
           "source_status": "POSTED_SOURCE_FIXTURE" if payload else "DRAFT_SOURCE_FIXTURE", "complete_voucher": True,
           "lines": [{"line_id": "1", "account": fields["debit_account"], "debit": str(amount), "credit": "0"},
                     {"line_id": "2", "account": fields["credit_account"], "debit": "0", "credit": str(amount)}]}
    if payload:
        row.update({f: fields[f] for f in ("counterparty", "project", "expense") if fields[f] is not None})
        row.update(bank_reference=payload["bank_reference"], bank_account=payload["bank_account"],
                   invoice_allocations=[{"invoice_reference": a["invoice_reference"], "amount_minor": str(a["amount_minor"])} for a in payload["allocations"]])
    if item_id:
        row["export_item_id"] = item_id
    if batch_id:
        row["batch_id"] = batch_id
    return row


def bundle_fixture(balance=-200, *, snapshot="SNAP_FIXTURE_0", exported="2026-09-16T00:00:00Z", as_of="2026-09-16", journals=None):
    records = [{"kind": "OPEN_ITEM", "business_date": as_of, "currency": "VND", "amount": str(balance), "account": "331_FIXTURE", "counterparty": "0001",
                "item_id": "DEBT_FIXTURE_001", "item_type": "INVOICE", "invoice_reference": "HD_FIXTURE_001"}]
    for kind, code, name in (("COUNTERPARTY", "0001", "Đối tượng giả lập"), ("ACCOUNT", "331_FIXTURE", "TK phải trả giả lập"),
                             ("ACCOUNT", "112_FIXTURE", "TK ngân hàng giả lập"), ("PROJECT", "0001", "Dự án giả lập"), ("EXPENSE", "0001", "Khoản mục giả lập")):
        records.append({"kind": kind, "business_date": "2026-09-01", "code": code, "version": "v1", "name": name, "source_status": "ACTIVE", "valid_from": "2026-09-01", "valid_to": None})
    records.append({"kind": "COST_CENTER", "business_date": "2026-09-01", "code": "0001", "version": "v1", "name": "Trung tâm chi phí giả lập", "source_status": "ACTIVE", "valid_from": "2026-09-01", "valid_to": None})
    records.append({"kind": "LOCK_PERIOD", "business_date": "2026-09-01", "valid_from": "2026-08-01", "valid_to": "2026-09-01", "scope": "all-fixture", "source_status": "LOCKED"})
    records.extend(copy.deepcopy(journals) if journals is not None else [journal_fixture()])
    return envelope("junsky_xuat", records, snapshot=snapshot, exported=exported, as_of=as_of)


def knowledge_item(category, key, payload, *, known=KNOWN, start="2026-09-01", end=None):
    return {"category": category, "logical_key": key, "payload": payload, "known_at": known, "valid_from": start, "valid_to": end, "evidence": ["SYNTHETIC_FIXTURE_DEFINITION_NOT_REAL_APPROVAL"]}


def knowledge_fixture():
    items = []
    for row in bundle_fixture()["records"]:
        if row["kind"] in {"COUNTERPARTY", "ACCOUNT", "PROJECT", "EXPENSE"}:
            items.append(knowledge_item("CATALOG", row["kind"] + ":" + row["code"], {"kind": row["kind"], "code": row["code"], "name": row["name"]}))
    items.append(knowledge_item("CATALOG", "ID:PAYEE", {"kind": "IDENTIFIER", "code": "PAYEE_FIXTURE", "identifier_type": "BANK_ACCOUNT", "value": "00009999", "counterparty": "0001", "verified": True}))
    items.append(knowledge_item("POLICY", "PAY_OUT_FIXTURE", {"template_id": "PAY_OUT_FIXTURE", "direction": "OUT", "partition": "PLHN_FIXTURE:PAYMENT",
        "needs_open_item": True, "required_fields": list(FIELDS), "keywords": ["thanh toan"], "priority": 1,
        "fields": dict(FIELD_VALUES), "statistics": {"min_count": 1, "min_share": "0.75", "half_life_days": "365"}}))
    return items


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def approved_review(source, destination, *, reason="Duyệt giả lập bởi kiểm thử tự động"):
    from ..xuat import excel
    wb = excel.load(Path(source).read_bytes())
    try:
        sheet = wb["DUYET"]
        headers = {cell.value: cell.column for cell in sheet[1]}
        for row in range(2, sheet.max_row + 1):
            sheet.cell(row, headers["quyet_dinh"], "APPROVE")
            sheet.cell(row, headers["ly_do"], reason)
        raw = excel.to_bytes(wb)
    finally:
        wb.close()
    Path(destination).write_bytes(raw)
    return Path(destination)


def postings_for_batch(store, batch_id):
    result = []
    for entry in store.conn.execute("SELECT * FROM export_items WHERE batch_id=? ORDER BY id", (batch_id,)):
        payload = json.loads(entry["payload_json"])
        result.append(journal_fixture("V_" + entry["id"], payload=payload, item_id=entry["id"], batch_id=batch_id))
    return result
