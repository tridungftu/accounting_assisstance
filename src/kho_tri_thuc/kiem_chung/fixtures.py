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


def review_dot_fixture(*, ma="KTD-DEMO-0001", dot="3", luc="2026-09-20T09:15:00+07:00", da_nap=True, anh_huong=1_500_000, ma_hd="HD-DEMO-01"):
    """Một kết quả `kiem_tra_dot` DEMO đúng shape #5 (docs/TAI-SU-DUNG-REVIEW-XAY-DUNG.md §3.1). Mọi giá trị là giả lập."""
    def o(value, cell, label):
        return {"gia_tri": value, "o": cell, "nhan": label}
    return {
        "ma": ma, "loai": "kiem_tra_dot", "luc": luc, "tep": "HSTT_DOT3_DEMO.xlsx",
        "hop_dong": {"ma_hd": ma_hd, "so_hd": "SO-HD-DEMO/2026", "phan_loai": "DON_GIA_CO_DINH"},
        "dot": dot, "dot_truoc": str(int(dot) - 1), "ngay_nghiem_thu": "2026-09-18",
        "gt_hieu_luc": 1_000_000_000, "loai_gia": "DON_GIA_CO_DINH", "vat": 8,
        "phu_luc_ap_dung": [{"so": "PL01-DEMO", "ngay_hieu_luc": "2026-07-01"}],
        "de_nghi": 120_000_000, "o_de_nghi": "Tong!H40",
        "tong_hop": {"gt_hd": o(1_000_000_000, "Tong!H10", "Giá trị hợp đồng"), "gt_lk_kt": o(300_000_000, "Tong!H12", "Lũy kế kỳ trước"),
                     "gt_kn": o(125_000_000, "Tong!H14", "Giá trị kỳ này"), "gt_lk": o(425_000_000, "Tong!H16", "Lũy kế đến kỳ này"),
                     "giu_lai": o(6_250_000, "Tong!H20", "Giữ lại đợt"), "thu_hoi_tu": o(10_000_000, "Tong!H22", "Thu hồi tạm ứng"),
                     "tt_ky_nay": o("không đọc được", "Tong!H40", "Thanh toán kỳ này")},
        "anh_huong": anh_huong, "phat_hien": [{"ma": "B1", "mo_ta": "KL vượt dự toán hạng mục DEMO", "anh_huong": anh_huong}],
        "bang_k": [{"buoc": "K1", "ket_qua": "DAT"}], "cay": {"nut": "DEMO"}, "bang_lop2": [], "doi_chieu_hm": [],
        "da_nap": {"luc": "2026-09-20T10:00:00", "dot": dot, "so_hang_muc": 12, "khong_khop": 1, "ghi_chu": "DEMO", "nap_lai": False} if da_nap else False,
        "tai": {"lop1": "/bao_cao/KTD-DEMO-lop1.html", "lop2": "/bao_cao/KTD-DEMO-lop2.html"},
    }


def nghiem_thu_catalog_fixture():
    """Danh mục DEMO cho mẫu bút toán nghiệm thu công khai (không phải mã Junsky thật)."""
    records = []
    for kind, code, name in (("ACCOUNT", "2412_DEMO", "Chi phí XDCB dở dang — DEMO"), ("ACCOUNT", "331_DEMO", "Phải trả nhà thầu — DEMO"),
                             ("ACCOUNT", "3388_DEMO", "Giữ lại theo đợt — DEMO"), ("PROJECT", "DA_DEMO_01", "Dự án DEMO 01"),
                             ("COUNTERPARTY", "NT_DEMO_01", "Nhà thầu DEMO 01")):
        records.append({"kind": kind, "business_date": "2026-09-01", "code": code, "version": "v1", "name": name, "source_status": "ACTIVE", "valid_from": "2026-01-01", "valid_to": None})
    return envelope("junsky_xuat", records, snapshot="SNAP_NT_DEMO")


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
