"""V9 quick posting tests use generated fixture records only."""
from __future__ import annotations

from test_modules import FeatureCase
from openpyxl import load_workbook
from kho_tri_thuc.giao_dien.quick import QuickPosting
from kho_tri_thuc.giao_dien.operations import Operations
from kho_tri_thuc.kiem_chung.fixtures import KNOWN, bank_fixture, envelope, knowledge_fixture


class V9QuickTests(FeatureCase):
    def test_pending_knowledge_can_propose_then_approval_learns_exact_document(self):
        attempt = self.ingest(bank_fixture())
        self.kb.stage_many(knowledge_fixture(), "HE_THONG_JUNSKY", KNOWN)
        quick = QuickPosting(self.store)
        first = quick.propose(attempt, "sao_ke", "TEST")
        self.assertEqual(2, len(first["rows"]))
        item = first["rows"][0]
        # Keep the decision inside the synthetic catalog.  V9b validates a
        # manual decision before it can become reusable knowledge.
        fields = dict(item["fields"])
        quick.decide(first["run_id"], [{"id": item["id"], "action": "APPROVE", "fields": fields}], "CFO_NTD", "2026-09-26T00:00:00Z")
        self.assertEqual("APPROVE", quick.rows(first["run_id"])["rows"][0]["state"])
        # The next proposed copy uses the explicit decision and is therefore Green.
        replay = quick.propose(attempt, "sao_ke", "TEST")
        self.assertEqual("Xanh", replay["rows"][0]["level"])

    def test_export_only_contains_explicitly_approved_items(self):
        # S9 obtains the branch/unit exclusively from an already-read Junsky
        # journal.  This synthetic BP also creates the S7 warning, which the
        # operator must explicitly clear before the otherwise approved item is
        # exported.
        self.ingest(envelope("junsky_xuat", [{
            "kind": "JOURNAL", "business_date": "2026-09-15", "currency": "VND", "amount": "0",
            "book": "NKC_FIXTURE", "fiscal_year": "2026", "voucher_type": "BP",
            "voucher_number": "UNIT_SYNBP2609-0001", "source_status": "POSTED_SOURCE_FIXTURE",
            "complete_voucher": True, "unit_code": "UNIT_SYN", "description": "Thanh toán hóa đơn giả lập",
            "lines": [
                {"line_id": "1", "account": "331_FIXTURE", "debit": "100", "credit": "0"},
                {"line_id": "2", "account": "112_FIXTURE", "debit": "0", "credit": "100"},
            ],
        }]))
        # A quick decision is accepted only when its selected accounts are
        # present in the synthetic catalog, just as in the real workflow.
        catalog = [item for item in knowledge_fixture()
                   if item["category"] == "CATALOG" and item["payload"].get("kind") != "IDENTIFIER"]
        identifiers = self.kb.stage_many(catalog, "TEST", KNOWN)
        for identifier in identifiers:
            self.kb.approve(identifier, "TEST", KNOWN)
        attempt = self.ingest(bank_fixture())
        quick = QuickPosting(self.store)
        quick.set_cash_mapping("00001234", "112_FIXTURE", "CFO_NTD", "MANUAL", ["V9_SYNTHETIC"])
        run = quick.propose(attempt, "sao_ke", "TEST")
        item = run["rows"][0]
        self.assertTrue(item["potential_existing"])
        quick.clear_existing(run["run_id"], item["id"], "CFO_NTD", "2026-09-26T00:00:00Z")
        fields = {"counterparty": None, "debit_account": "331_FIXTURE", "credit_account": "112_FIXTURE", "project": None, "expense": None}
        quick.decide(run["run_id"], [{"id": item["id"], "action": "APPROVE", "fields": fields}], "CFO_NTD", "2026-09-26T00:00:00Z")
        result = quick.export(run["run_id"], self.root)
        self.assertEqual(1, result["approved"])
        self.assertTrue(result["no_auto_import"])
        self.assertEqual(1, len(result["files"]))
        for path in result["files"]:
            book = load_workbook(path, read_only=True, data_only=False, keep_links=False)
            self.assertEqual(17, book["CB_tmpEntry1"].max_column)
            self.assertEqual(37, book["CB_tmpEntry2"].max_column)
            book.close()

    def test_bank_account_normalization_preserves_longest_identifier_only(self):
        self.assertEqual("0123456789", Operations._bank_account("NH 0123456789 — mã 123"))
        self.assertEqual("", Operations._bank_account("không có số tài khoản"))
