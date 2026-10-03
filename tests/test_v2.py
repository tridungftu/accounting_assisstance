"""V2 contracts use synthetic records only; no operational PLHN data belongs here."""

from __future__ import annotations

import json

from test_modules import FeatureCase
from kho_tri_thuc.ha_tang.config import Config
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.kiem_chung.fixtures import (
    CUTOFF, EXPORT_AT, FIELD_VALUES, KNOWN, REVIEW_AT, envelope, knowledge_fixture,
    knowledge_item, write_json,
)


def invoice(*, source="hoa_don_xml", amount="100", net="90", tax="10", lines=True):
    row = {"kind": "INVOICE", "business_date": "2026-09-15", "currency": "VND", "amount": amount,
           "net_amount": net, "tax_amount": tax, "total_amount": amount,
           "seller_tax_id": "SELLER_FIXTURE", "buyer_tax_id": "PLHN_FIXTURE",
           "series": "1C26FIXTURE", "number": "HD_FIXTURE_001", "invoice_type": "FIXTURE",
           "source_status": "ACTIVE", "ttxly": "1"}
    if lines:
        row["lines"] = [
            {"line_id": "net", "description": "dịch vụ giả lập", "net_amount": net, "tax_amount": tax,
             "total_amount": amount, "tax_rate": "10", "line_nature": "GOODS"}
        ]
    return envelope(source, [row])


def multiline_policy(*, with_rate=True):
    line_tax = {"line_id": "VAT", "account": "1331_FIXTURE", "side": "DEBIT", "amount_source": "INVOICE_TAX"}
    line_net = {"line_id": "COST", "account": "6427_FIXTURE", "side": "DEBIT", "amount_source": "INVOICE_NET"}
    if with_rate:
        line_tax["tax_rate"] = "10"; line_net["tax_rate"] = "10"
    return knowledge_item("POLICY", "MULTILINE_FIXTURE", {
        "contract_version": 2, "template_id": "MULTILINE_FIXTURE", "direction": "OUT",
        "partition": "PLHN_FIXTURE:PAYMENT", "tier": 1, "order": 1,
        "trigger": {"mode": "KEY", "key_type": "BANK_ACCOUNT", "key_value": "00009999"},
        "needs_open_item": False, "required_fields": list(FIELD_VALUES), "fields": {**FIELD_VALUES, "debit_account": "6427_FIXTURE"},
        "journal_lines": [line_net, line_tax, {"line_id": "BANK", "account": "112_FIXTURE", "side": "CREDIT", "amount_source": "BANK_TOTAL"}],
    })


class V2InvoiceAndLineTests(FeatureCase):
    def test_invoice_sources_merge_with_observations_and_money_warning(self):
        self.assertEqual(self.ingest(invoice()) is not None, True)
        self.assertEqual(self.ingest(invoice(source="hoa_don_bang_ke", lines=False)) is not None, True)
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM documents WHERE kind='INVOICE'").fetchone()[0], 1)
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM document_observations").fetchone()[0], 2)
        core = json.loads(self.store.conn.execute("SELECT core_json FROM documents WHERE kind='INVOICE'").fetchone()[0])
        self.assertEqual((core["net_minor"], core["tax_minor"], core["total_minor"]), (90, 10, 100))
        conflict = invoice(source="hoa_don_bang_ke", amount="110", net="100", tax="10", lines=False)
        self.ingest(conflict)
        self.assertEqual(self.store.conn.execute("SELECT status FROM document_observations ORDER BY rowid DESC LIMIT 1").fetchone()[0], "WARNING_MONEY_CONFLICT")

    def test_invoice_rounding_and_invoice_line_contract(self):
        valid = invoice(amount="111", net="100", tax="10")
        valid["records"][0]["rounding_tolerance"] = "1"
        self.assertEqual(self.ingest(valid) is not None, True)
        invalid = invoice(amount="113", net="100", tax="10")
        invalid["records"][0]["rounding_tolerance"] = "1"
        with self.assertRaises(AssertionError):
            self.ingest(invalid)

    def test_multiline_proposal_decision_and_export_lines_use_checksum(self):
        self.ingest(invoice())
        catalog = knowledge_item("CATALOG", "ACCOUNT:6427_FIXTURE", {"kind": "ACCOUNT", "code": "6427_FIXTURE", "name": "Synthetic cost account"})
        _, bank_ids, _ = self.seed(knowledge=knowledge_fixture()[:-1] + [catalog, multiline_policy()])
        attempt = self.store.conn.execute("SELECT id FROM attempts WHERE source='junsky_xuat' ORDER BY rowid DESC LIMIT 1").fetchone()[0]
        session = self.sessions.open(attempt, [bank_ids[0]], CUTOFF, "TEST_OPERATOR")
        proposal = self.sessions.propose(session["id"])[0]
        self.assertEqual(proposal["completeness"], "FULL", proposal)
        self.assertEqual([(x["account"], x["debit_minor"], x["credit_minor"]) for x in proposal["lines"]], [("6427_FIXTURE", 90, 0), ("1331_FIXTURE", 10, 0), ("112_FIXTURE", 0, 100)])
        path, result = self.approve(session)
        self.assertEqual(result["applied"], 1)
        batch = self.review.export(session["id"], "TEST_OPERATOR", EXPORT_AT)
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM export_item_lines WHERE export_item_id IN (SELECT id FROM export_items WHERE batch_id=?)", (batch["batch_id"],)).fetchone()[0], 3)
        self.assertTrue(self.store.conn.execute("SELECT line_checksum FROM export_items WHERE batch_id=?", (batch["batch_id"],)).fetchone()[0])

    def test_multiline_without_tax_evidence_stays_waiting(self):
        catalog = knowledge_item("CATALOG", "ACCOUNT:6427_FIXTURE", {"kind": "ACCOUNT", "code": "6427_FIXTURE", "name": "Synthetic cost account"})
        _, bank_ids, _ = self.seed(knowledge=knowledge_fixture()[:-1] + [catalog, multiline_policy(with_rate=False)])
        attempt = self.store.conn.execute("SELECT id FROM attempts WHERE source='junsky_xuat' ORDER BY rowid DESC LIMIT 1").fetchone()[0]
        session = self.sessions.open(attempt, [bank_ids[0]], CUTOFF, "TEST_OPERATOR")
        proposal = self.sessions.propose(session["id"])[0]
        self.assertIn("MULTILINE_TAX_EVIDENCE_WAIT", proposal["constraints"])
        self.assertEqual(proposal["lines"], [])


class V2EnvironmentTests(FeatureCase):
    def test_that_is_separate_and_cannot_enable_junsky_operations(self):
        path = self.root / "that.toml"
        path.write_text("""[app]\nenvironment = 'that'\nentity_id = 'PLHN'\ndata_dir = 'that-data'\n[money]\ncurrency = 'VND'\nscale = 0\n[operation]\njunsky_export_enabled = false\njunsky_import_enabled = false\n""", encoding="utf-8")
        config = Config.load(path)
        self.assertEqual(config.environment, "that")
        self.assertFalse(config.junsky_export_enabled)
        path.write_text(path.read_text(encoding="utf-8").replace("junsky_export_enabled = false", "junsky_export_enabled = true"), encoding="utf-8")
        with self.assertRaises(DataError) as error:
            Config.load(path)
        self.assertEqual(error.exception.code, "JUNSKY_OPERATION_BLOCKED")
