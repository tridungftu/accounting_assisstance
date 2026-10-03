"""V8 is tested only with generated workbooks and explicit synthetic records."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from test_modules import FeatureCase
from test_v2 import invoice

from kho_tri_thuc.giao_dien.operations import Operations
from kho_tri_thuc.ha_tang.config import Config
from kho_tri_thuc.nguon.that import SourceMetadata, ThatAdapter
from kho_tri_thuc.tri_thuc.human_workbook import HumanKnowledgeWorkbook
from kho_tri_thuc.xuat.service import ReviewExport
from kho_tri_thuc.kiem_chung.fixtures import CUTOFF, KNOWN, knowledge_item


class V8ProposalTests(FeatureCase):
    def _approve(self, items):
        identifiers = self.kb.stage_many(items, "TEST_V8", KNOWN)
        for identifier in identifiers:
            self.kb.approve(identifier, "TEST_V8", CUTOFF)

    def test_purchase_invoice_uses_approved_vocabulary_and_builds_tax_lines(self):
        source = invoice(); source["records"][0]["direction"] = "MUA_VAO"; source["records"][0]["buyer_tax_id"] = self.store.config.entity_tax_id
        attempt = self.ingest(source)
        invoice_id = self.store.conn.execute("SELECT id FROM documents WHERE kind='INVOICE'").fetchone()[0]
        self._approve([
            knowledge_item("CATALOG", "CP", {"kind": "COUNTERPARTY", "code": "CP_SYN", "name": "Synthetic supplier"}),
            knowledge_item("CATALOG", "ID", {"kind": "IDENTIFIER", "code": "TAX_ID:SELLER_FIXTURE", "identifier_type": "TAX_ID", "value": "SELLER_FIXTURE", "counterparty": "CP_SYN", "verified": True}),
            knowledge_item("CATALOG", "A6427", {"kind": "ACCOUNT", "code": "6427", "name": "Synthetic expense"}),
            knowledge_item("CATALOG", "A331", {"kind": "ACCOUNT", "code": "33111", "name": "Synthetic payable"}),
            knowledge_item("CATALOG", "P", {"kind": "PROJECT", "code": "P_SYN", "name": "Synthetic project"}),
            knowledge_item("CATALOG", "E", {"kind": "EXPENSE", "code": "E_SYN", "name": "Synthetic expense item"}),
            knowledge_item("INVOICE_KEYWORD", "KW", {"keywords": ["dịch vụ giả lập"], "direction": "MUA_VAO", "fields": {"expense": "E_SYN"}}),
            knowledge_item("INVOICE_POLICY", "POL", {"direction": "MUA_VAO", "expense": "E_SYN", "fields": {"debit_account": "6427", "project": "P_SYN"}}),
        ])
        session = self.sessions.open(attempt, [invoice_id], CUTOFF, "TEST_V8", "fixture")
        proposal = self.sessions.propose(session["id"])[0]
        self.assertEqual("FULL", proposal["completeness"], proposal)
        self.assertEqual([("6427", 90, 0), ("1331", 10, 0), ("33111", 0, 100)], [(line["account"], line["debit_minor"], line["credit_minor"]) for line in proposal["lines"]])
        self.assertEqual(0, self.store.conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0])
        rows = ReviewExport(self.store).ui_rows(session["id"], CUTOFF)
        result = ReviewExport(self.store).decide_from_ui(session["id"], [{"proposal_id": rows[0]["proposal_id"], "action": "APPROVE", "fields": proposal["fields"], "reason": ""}], "TEST_V8", CUTOFF)
        self.assertEqual(1, result["applied"])


class V8ReaderAndUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ktt-v8-synthetic-")
        self.root = Path(self.temp.name)
        self.config_path = self.root / "that.toml"
        self.config_path.write_text("""[app]\nenvironment='that'\nentity_id='PLHN_SYN'\ndata_dir='that'\n[money]\ncurrency='VND'\nscale=0\n[operation]\njunsky_export_enabled=false\njunsky_import_enabled=false\ncatalog_valid_from='1900-01-01'\nknowledge_approval_actor='CFO_NTD'\n""", encoding="utf-8")
        self.config = Config.load(self.config_path)

    def tearDown(self):
        self.temp.cleanup()

    def test_catalog_import_uses_configured_effective_date_without_changing_rule_date(self):
        source = self.root / "BO-QUY-TAC.xlsx"; wb = Workbook(); ws = wb.active; ws.title = "Quy tắc"
        ws.append(["ma_quy_tac", "bac", "loai_khoa", "chieu", "stk_doi_ung", "ten_doi_ung", "tu_khoa", "tk_doi_ung", "ma_doi_tuong", "ma_du_an", "lan_dau", "han_dung", "trang_thai"])
        ws.append(["R_SYN", "2", "STK", "CHI", "00001234", "", "", "6427", "", "", "2026-08-01", "", "DE_CU"])
        for name, headers, row in (("Ánh xạ STK", ["stk_doi_ung", "ma_doi_tuong", "trang_thai"], ["00001234", "CP_SYN", "CHỜ"]), ("DM Đối tượng", ["ma", "ten"], ["CP_SYN", "Synthetic"]), ("DM Tài khoản", ["ma", "ten"], ["6427", "Synthetic"]), ("DM Khoản mục CP", ["ma", "ten"], ["E_SYN", "Synthetic"]), ("DM Dự án", ["ma", "ten"], ["P_SYN", "Synthetic"]), ("DM Trung tâm CP", ["ma", "ten"], ["C_SYN", "Synthetic"])):
            sheet = wb.create_sheet(name); sheet.append(headers); sheet.append(row)
        wb.save(source); wb.close()
        from kho_tri_thuc.ha_tang.store import Store
        with Store(self.config) as store:
            HumanKnowledgeWorkbook(store).import_sources([source], "IMPORTER", "2026-09-10T00:00:00Z")
            catalog_dates = {row[0] for row in store.conn.execute("SELECT valid_from FROM knowledge_versions WHERE category='CATALOG'")}
            rule_date = store.conn.execute("SELECT valid_from FROM knowledge_versions WHERE category='POLICY'").fetchone()[0]
        self.assertEqual({"1900-01-01"}, catalog_dates)
        self.assertEqual("2026-08-01", rule_date)

    def test_efast_accepts_iso_period_and_operations_remain_that_only(self):
        data = [["Số tài khoản/ Account No.", "0000123456"], ["Chu kỳ yêu cầu/From date- to date", "2026-08-01 - 2026-08-31"],
                ["STT", "Ngày hạch toán", "Mô tả giao dịch", "Nợ", "Có", "Số dư TK", "Số giao dịch"], [1, "01-08-2026", "Synthetic", 0, 100, 100, "SYN-1"]]
        meta = SourceMetadata("2026-08-31", "2026-09-01T00:00:00Z", "synthetic", "2026-08-01", "2026-09-01")
        rows, issues, _ = ThatAdapter("sao_ke", self.root / "unused.xlsx", meta)._bank_table(data)
        self.assertEqual(1, len(rows))
        self.assertNotIn("BANK_PERIOD_UNPARSEABLE", [issue.code for issue in issues])
        app = Operations(self.config_path, self.root / "web")
        receipt = app.receive_source(b"synthetic source bytes", {"source": "sao_ke", "name": "synthetic.xlsx", "relative_path": "synthetic.xlsx"})
        self.assertEqual("sao_ke", receipt["source"])
        self.assertTrue(app.state()["status"]["integrity"]["ok"])


if __name__ == "__main__":
    unittest.main()
