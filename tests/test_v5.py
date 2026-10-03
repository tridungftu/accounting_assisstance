"""V5 keeps review workbooks compact and scores abstentions separately."""

from __future__ import annotations

from pathlib import Path

from test_modules import FeatureCase
from kho_tri_thuc.kiem_chung.fixtures import CUTOFF, REVIEW_AT, bundle_fixture
from kho_tri_thuc.kiem_chung.service import score
from kho_tri_thuc.xuat import excel


class V5ReviewAndScoreTests(FeatureCase):
    def test_other_open_item_can_be_selected_by_code_without_widening_shortlist(self):
        bundle = bundle_fixture()
        bundle["records"].insert(1, {"kind": "OPEN_ITEM", "business_date": "2026-09-16", "currency": "VND", "amount": "-100",
                                     "account": "331_FIXTURE", "counterparty": "0001", "item_id": "DEBT_FIXTURE_OTHER",
                                     "item_type": "INVOICE", "invoice_reference": "HD_FIXTURE_OTHER"})
        bundle["controls"]["count"] = len(bundle["records"])
        bundle["controls"]["totals"]["OPEN_ITEM/VND"] = "-300"
        attempt, bank_ids, _ = self.seed(bundle=bundle)
        session = self.sessions.open(attempt, [bank_ids[0]], CUTOFF, "TEST_OPERATOR")
        self.sessions.propose(session["id"])
        review = self.review.review_workbook(session["id"], "TEST_OPERATOR", REVIEW_AT)
        self.assertEqual(review["candidate_limit"], 10)
        raw = excel.load(Path(review["path"]).read_bytes())
        try:
            self.assertEqual(set(raw.sheetnames), {"META", "DUYET", "PHAN_BO", "CONG_NO_KHAC"})
            headers = {cell.value: cell.column for cell in raw["DUYET"][1]}
            proposal_id = raw["DUYET"].cell(2, headers["proposal_id"]).value
            raw["DUYET"].cell(2, headers["quyet_dinh"], "APPROVE")
            raw["DUYET"].cell(2, headers["ly_do"], "Chọn công nợ khác trong kiểm thử")
            allocation_headers = {cell.value: cell.column for cell in raw["PHAN_BO"][1]}
            raw["PHAN_BO"].cell(2, allocation_headers["tien_duyet"], "0")
            other = raw["CONG_NO_KHAC"]
            other.append([proposal_id, self.store.conn.execute("SELECT id FROM documents WHERE kind='OPEN_ITEM' AND json_extract(core_json,'$.item_id')='DEBT_FIXTURE_OTHER'").fetchone()[0], "100"])
            content = excel.to_bytes(raw)
        finally:
            raw.close()
        path = self.root / "other-allocation.xlsx"; path.write_bytes(content)
        result = self.review.import_review(path, "TEST_KTT_FIXTURE", REVIEW_AT)
        self.assertEqual(result["applied"], 1)
        allocation = self.store.conn.execute("SELECT open_item_id,amount_minor FROM allocations WHERE state='APPROVED'").fetchone()
        self.assertEqual(allocation["amount_minor"], 100)

    def test_none_is_coverage_gap_not_wrong_proposal_and_codes_stay_text(self):
        predictions = [
            {"completeness": "NONE", "fields": {}, "allocations": [], "amount_minor": -100, "direction": "OUT"},
            {"completeness": "PARTIAL", "fields": {"counterparty": "00379227"}, "allocations": [], "amount_minor": 200, "direction": "IN"},
        ]
        records = [{"truth": {"fields": {"counterparty": "X"}}}, {"truth": {"fields": {"counterparty": "00379227"}}}]
        report = score(predictions, records)
        self.assertEqual(report["proposal"]["not_proposed_count"], 1)
        self.assertEqual(report["proposal"]["not_proposed_minor"], 100)
        self.assertEqual(report["amount"]["assessed_minor"], 200)
        self.assertEqual(report["amount"]["wrong_minor"], 0)
        self.assertEqual(report["per_field"]["counterparty"]["assessed"], 1)
