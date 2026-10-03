"""V10 screen contracts (Claude Design handoff) with generated records only.

No PLHN data appears here.  The tests cover what the new screen relies on:
complete entry lines, edited multi-line decisions, Undo/Mở lại, the debt
account rule, level-1 export (review workbook only), the learning cut-off,
re-proposal and the faster identifier lookup.
"""
from __future__ import annotations

import json
import threading
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from openpyxl import load_workbook

from test_modules import FeatureCase
from kho_tri_thuc.de_xuat.engine import Engine, FIELDS
from kho_tri_thuc.giao_dien.operations import Operations
from kho_tri_thuc.giao_dien.quick import QuickPosting, explain_errors
from kho_tri_thuc.giao_dien.v9b import journal_suggestion, offset_account_ranking, similar_at_least, text_similarity
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.kiem_chung.fixtures import envelope, knowledge_item

CUT = "2099-01-01T00:00:00Z"
ACTOR = "CFO_NTD"


class V10Base(FeatureCase):
    def _stage(self, items, *, approve=True):
        identifiers = self.kb.stage_many(items, "V10_SYNTHETIC", CUT)
        if approve:
            for identifier in identifiers:
                self.kb.approve(identifier, "V10_SYNTHETIC", CUT)
        return identifiers

    def _setup(self, *, accounts=("1121", "6427", "1331", "331", "13881"), parties=("CP_SYN", "CP_OTHER"), policy_fields=None):
        items = []
        for party in parties:
            items.append(knowledge_item("CATALOG", "COUNTERPARTY:" + party, {"kind": "COUNTERPARTY", "code": party, "name": "Synthetic " + party}))
        for account in accounts:
            items.append(knowledge_item("CATALOG", "ACCOUNT:" + account, {"kind": "ACCOUNT", "code": account, "name": "Synthetic " + account}))
        items.append(knowledge_item("CATALOG", "COST_CENTER:TT_SYN", {"kind": "COST_CENTER", "code": "TT_SYN", "name": "Synthetic centre"}))
        items.append(knowledge_item("POLICY", "V10_POLICY", {
            "contract_version": 2, "template_id": "V10_POLICY", "partition": "V10_POLICY", "direction": "OUT", "tier": 1, "order": 1,
            "needs_open_item": False, "required_fields": ["debit_account", "credit_account"], "trigger": {"mode": "REGEX", "regex": "SYNTHETIC"},
            "fields": dict(policy_fields or {"debit_account": "6427"})}))
        self._stage(items)
        QuickPosting(self.store).set_cash_mapping("00001234", "1121", ACTOR, source="MANUAL", evidence=["V10_SYNTHETIC"])

    @staticmethod
    def _bank(reference, *, amount=-1000, day="2026-09-15", counterpart_account="", description="SYNTHETIC PAYMENT"):
        record = {"business_date": day, "currency": "VND", "amount": str(amount), "bank": "BANK_SYN", "account": "00001234",
                  "id_scope": "v10-synthetic", "reference": reference, "description": description, "identity_verified": True}
        if counterpart_account:
            record["counterparty_account"] = counterpart_account
        return record

    def _run(self, *records):
        attempt = self.ingest(envelope("sao_ke", list(records)))
        return QuickPosting(self.store).propose(attempt, "sao_ke", "V10_SYNTHETIC", cutoff=CUT, source_name="synthetic.xlsx", source_hash="HASH_" + attempt)

    def _journal_unit(self):
        journal = {"kind": "JOURNAL", "business_date": "2026-09-01", "currency": "VND", "amount": "0", "book": "NKC_SYN", "fiscal_year": "2026",
                   "voucher_type": "BP", "voucher_number": "UNIT_SYNBP2609-0001", "source_status": "POSTED_SOURCE_FIXTURE", "complete_voucher": True,
                   "unit_code": "UNIT_SYN", "description": "OTHER HISTORY",
                   "lines": [{"line_id": "1", "account": "6427", "debit": "5", "credit": "0"}, {"line_id": "2", "account": "1121", "debit": "0", "credit": "5"}]}
        self.ingest(envelope("junsky_xuat", [journal], as_of="2026-09-01", exported="2026-09-02T00:00:00Z"))



class V10ScreenTests(V10Base):
    # -- entry lines and level ------------------------------------------------
    def test_rows_expose_complete_balanced_entry_lines_and_stable_proposal_level(self):
        self._setup()
        run = self._run(self._bank("V10-LINES"))
        row = run["rows"][0]
        self.assertEqual([("N", "6427", 1000), ("C", "1121", 1000)], [(l["side"], l["account"], l["amount"]) for l in row["entry_lines"]])
        self.assertEqual("OUT", row["direction"])
        self.assertEqual("1121", row["cash_account"])
        quick = QuickPosting(self.store)
        after = quick.decide(run["run_id"], [{"id": row["id"], "action": "APPROVE"}], ACTOR, CUT)["rows"][0]
        self.assertEqual("APPROVE", after["state"])
        self.assertEqual(row["proposal_level"], after["proposal_level"])
        self.assertEqual("synthetic.xlsx", after and quick.rows(run["run_id"])["run"]["source_name"])

    def test_cash_leg_is_shown_even_when_no_rule_fits(self):
        self._setup()
        run = self._run(self._bank("V10-NORULE", description="UNMATCHED TEXT"))
        row = run["rows"][0]
        self.assertEqual("Đỏ", row["proposal_level"])
        self.assertIn(("C", "1121"), [(l["side"], l["account"]) for l in row["entry_lines"]])
        self.assertIn(("N", ""), [(l["side"], l["account"]) for l in row["entry_lines"]])
        self.assertTrue(row["suggest_accounts"] is not None)

    # -- edited multi-line decision -------------------------------------------
    def test_edited_multiline_decision_is_validated_exported_and_learned(self):
        self._setup()
        run = self._run(self._bank("V10-SPLIT-1", amount=-1000, counterpart_account="009999"))
        row = run["rows"][0]
        lines = [{"side": "N", "account": "6427", "amount": 900, "counterparty": "CP_SYN", "project": "", "expense": "", "cost_center": "TT_SYN"},
                 {"side": "N", "account": "1331", "amount": 100, "counterparty": "CP_SYN", "project": "", "expense": "", "cost_center": ""},
                 {"side": "C", "account": "1121", "amount": 1000, "counterparty": "CP_SYN", "project": "", "expense": "", "cost_center": ""}]
        quick = QuickPosting(self.store)
        decided = quick.decide(run["run_id"], [{"id": row["id"], "action": "APPROVE", "lines": lines}], ACTOR, CUT)["rows"][0]
        self.assertEqual("APPROVE", decided["state"])
        self.assertEqual(lines, decided["decision_lines"])
        self.assertEqual("6427", decided["fields"]["debit_account"])
        self.assertEqual("CP_SYN", decided["fields"]["counterparty"])
        self.assertEqual("TT_SYN", decided["cost_center"])
        # The same STK at a new amount reuses the split (scaled, integers).
        second = self._run(self._bank("V10-SPLIT-2", amount=-2000, day="2026-09-16", counterpart_account="009999"))["rows"][0]
        self.assertEqual([("N", "6427", 1800), ("N", "1331", 200), ("C", "1121", 2000)], [(l["side"], l["account"], l["amount"]) for l in second["entry_lines"]])
        self.assertEqual("Xanh", second["proposal_level"])
        # Level 2 (Junsky files) writes exactly the decided lines.
        self._journal_unit()
        result = quick.export(run["run_id"], self.root)
        book = load_workbook(result["files"][0], read_only=True)
        try:
            entry2 = list(book["CB_tmpEntry2"].iter_rows(min_row=2, values_only=True))
            headers = [cell.value for cell in next(book["CB_tmpEntry2"].iter_rows(min_row=1, max_row=1))]
        finally:
            book.close()
        account, center = headers.index("AcctID"), headers.index("CenterID")
        self.assertEqual(["6427", "1331", "1121"], [values[account] for values in entry2])
        self.assertEqual("TT_SYN", entry2[0][center])

    def test_edited_lines_must_balance_hit_the_bank_amount_and_name_debt_counterparty(self):
        self._setup()
        run = self._run(self._bank("V10-BAD"))
        row = run["rows"][0]
        quick = QuickPosting(self.store)
        cases = {
            "LINES_UNBALANCED": [{"side": "N", "account": "6427", "amount": 900}, {"side": "C", "account": "1121", "amount": 1000}],
            "LINES_CASH_AMOUNT": [{"side": "N", "account": "6427", "amount": 500}, {"side": "C", "account": "1121", "amount": 500}],
            "MISSING_COUNTERPARTY_FOR_331": [{"side": "N", "account": "331", "amount": 1000}, {"side": "C", "account": "1121", "amount": 1000}],
            "MISSING_COUNTERPARTY_FOR_13881": [{"side": "N", "account": "13881", "amount": 1000}, {"side": "C", "account": "1121", "amount": 1000}],
            "INVALID_DEBIT_ACCOUNT": [{"side": "N", "account": "9999", "amount": 1000}, {"side": "C", "account": "1121", "amount": 1000}],
        }
        for code, lines in cases.items():
            with self.subTest(code=code), self.assertRaises(DataError) as caught:
                quick.decide(run["run_id"], [{"id": row["id"], "action": "APPROVE", "lines": lines}], ACTOR, CUT)
            self.assertIn(code, str(caught.exception))
        self.assertEqual("WAIT", quick.rows(run["run_id"])["rows"][0]["state"])
        self.assertIn("cần đối tượng", explain_errors(["MISSING_COUNTERPARTY_FOR_331"]))
        with self.assertRaises(DataError):
            quick.decide(run["run_id"], [{"id": row["id"], "action": "APPROVE", "lines": [{"side": "X", "account": "6427", "amount": 1}]}], ACTOR, CUT)

    def test_debt_account_without_counterparty_is_not_green_and_cannot_be_approved(self):
        self._setup(policy_fields={"debit_account": "331"})
        run = self._run(self._bank("V10-DEBT"))
        row = run["rows"][0]
        self.assertNotEqual("Xanh", row["proposal_level"])
        with self.assertRaises(DataError) as caught:
            QuickPosting(self.store).decide(run["run_id"], [{"id": row["id"], "action": "APPROVE"}], ACTOR, CUT)
        self.assertIn("MISSING_COUNTERPARTY_FOR_331", str(caught.exception))

    # -- Undo / Mở lại ---------------------------------------------------------
    def test_reopen_returns_to_waiting_and_stops_the_learned_condition(self):
        self._setup()
        run = self._run(self._bank("V10-UNDO-1", counterpart_account="008888"))
        row = run["rows"][0]
        quick = QuickPosting(self.store)
        fields = {**row["fields"], "counterparty": "CP_SYN"}
        quick.decide(run["run_id"], [{"id": row["id"], "action": "APPROVE", "fields": fields}], ACTOR, CUT)
        self.assertEqual(1, self.store.conn.execute("SELECT COUNT(*) FROM quick_condition_learning WHERE active=1").fetchone()[0])
        reopened = quick.decide(run["run_id"], [{"id": row["id"], "action": "REOPEN"}], ACTOR, CUT)["rows"][0]
        self.assertEqual("WAIT", reopened["state"])
        self.assertIsNone(reopened["decision_lines"])
        self.assertEqual(0, self.store.conn.execute("SELECT COUNT(*) FROM quick_condition_learning WHERE active=1").fetchone()[0])
        skipped = quick.decide(run["run_id"], [{"id": row["id"], "action": "SKIP", "reason": "cho hop dong"}], ACTOR, CUT)["rows"][0]
        self.assertEqual(("SKIP", "cho hop dong"), (skipped["state"], skipped["reason"]))
        self.assertEqual("WAIT", quick.decide(run["run_id"], [{"id": row["id"], "action": "REOPEN"}], ACTOR, CUT)["rows"][0]["state"])

    def test_remember_false_approves_without_learning(self):
        self._setup()
        run = self._run(self._bank("V10-NOREMEMBER", counterpart_account="007777"))
        row = run["rows"][0]
        QuickPosting(self.store).decide(run["run_id"], [{"id": row["id"], "action": "APPROVE", "remember": False}], ACTOR, CUT)
        self.assertEqual(0, self.store.conn.execute("SELECT COUNT(*) FROM quick_condition_learning").fetchone()[0])

    # -- export level 1 ----------------------------------------------------------
    def test_level_one_export_writes_only_the_review_workbook_of_approved_rows(self):
        self._setup()
        run = self._run(self._bank("V10-EX-1"), self._bank("V10-EX-2", amount=-500), self._bank("V10-EX-3", amount=-700))
        quick = QuickPosting(self.store)
        by_reference = {row["source_reference"]: row for row in run["rows"]}
        first, second, third = by_reference["V10-EX-1"], by_reference["V10-EX-2"], by_reference["V10-EX-3"]
        quick.decide(run["run_id"], [{"id": first["id"], "action": "APPROVE"}, {"id": second["id"], "action": "SKIP"}], ACTOR, CUT)
        result = quick.export(run["run_id"], self.root, junsky_files=False)
        self.assertEqual([], result["files"])
        self.assertEqual(1, result["reviewed"])
        self.assertTrue(result["no_auto_import"])
        review = Path(result["review"])
        self.assertTrue(review.name.startswith("SOAT-DINH-KHOAN-2026-09-lan1-"))
        book = load_workbook(review, read_only=True)
        try:
            rows = list(book["BUT TOAN"].iter_rows(min_row=2, values_only=True))
            self.assertEqual(["BUT TOAN", "TONG HOP"], book.sheetnames)
        finally:
            book.close()
        self.assertEqual(2, len(rows))  # Nợ 6427 / Có 1121 of the single approved row
        states = {row["id"]: row["state"] for row in quick.rows(run["run_id"])["rows"]}
        self.assertEqual({"EXPORTED", "SKIP", "WAIT"}, set(states.values()))
        history = quick.history()
        self.assertEqual(1, len(history))
        self.assertEqual((1, 1000), (history[0]["count"], history[0]["total_minor"]))
        with self.assertRaises(DataError):
            quick.decide(run["run_id"], [{"id": first["id"], "action": "REOPEN"}], ACTOR, CUT)
        with self.assertRaises(DataError):
            quick.export(run["run_id"], self.root, junsky_files=False)
        quick.decide(run["run_id"], [{"id": third["id"], "action": "APPROVE"}], ACTOR, CUT)
        again = quick.export(run["run_id"], self.root, junsky_files=False)
        self.assertIn("-lan2-", Path(again["review"]).name)
        self.assertEqual(1, again["reviewed"])

    # -- learning cut-off and re-proposal --------------------------------------
    def test_learning_cutoff_hides_rules_first_seen_after_it(self):
        self._setup(policy_fields={"debit_account": "6427"})
        late = knowledge_item("POLICY", "V10_LATE", {
            "contract_version": 2, "template_id": "V10_LATE", "partition": "V10_LATE", "direction": "OUT", "tier": 1, "order": 1,
            "needs_open_item": False, "required_fields": ["debit_account", "credit_account"], "trigger": {"mode": "REGEX", "regex": "LATE ONLY"},
            "fields": {"debit_account": "1331"}, "source_row": {"lan_dau": "2026-08-15", "so_lan_gap": 3, "so_lan_dung": 3}})
        self._stage([late])
        run = self._run(self._bank("V10-LATE", description="LATE ONLY TEXT"))
        self.assertIn("1331", [l["account"] for l in run["rows"][0]["entry_lines"]])
        self.store.conn.execute("INSERT INTO workspace_meta(key,value) VALUES ('v9b_runtime_settings',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                                (json.dumps({"learning_cutoff": "2026-06-30"}),))
        self.store.conn.commit()
        replay = QuickPosting(self.store).repropose(run["run_id"], "V10_SYNTHETIC", CUT)["rows"][0]
        self.assertNotIn("1331", [l["account"] for l in replay["entry_lines"]])

    def test_journal_learning_respects_cutoff_day_and_lists_alternative_structures(self):
        bank = {"business_date": "2026-08-10", "amount_minor": -100, "counterparty_account": "", "description": "SYNTHETIC SERVICE FEE"}
        def journal(identifier, day, account):
            return {"id": identifier, "business_date": day, "voucher_type": "BP", "voucher_number": "BP_" + identifier, "description": "SYNTHETIC SERVICE FEE",
                    "lines": [{"account": account, "debit_minor": 100, "credit_minor": 0}, {"account": "1121", "debit_minor": 0, "credit_minor": 100}]}
        history = [journal("A1", "2026-06-01", "6427"), journal("A2", "2026-06-02", "6427"), journal("B1", "2026-06-03", "331"), journal("LATE", "2026-07-05", "811")]
        learned = journal_suggestion(bank, history, cutoff_day="2026-07-01", own_codes=set(), object_learning_from="2026-07-01")
        self.assertEqual(["A1", "A2", "B1"], learned["source_ids"])
        self.assertEqual([2, 1], [item["count"] for item in learned["signatures"]])
        self.assertEqual(["6427", "331"], [item["lines"][0]["account"] for item in learned["signatures"]])
        self.assertEqual(["6427", "331"], offset_account_ranking(history, "OUT", "2026-07-01"))

    def test_repropose_touches_only_waiting_rows(self):
        self._setup()
        run = self._run(self._bank("V10-RP-1"), self._bank("V10-RP-2", amount=-300))
        quick = QuickPosting(self.store)
        by_reference = {row["source_reference"]: row for row in run["rows"]}
        first, second = by_reference["V10-RP-1"], by_reference["V10-RP-2"]
        quick.decide(run["run_id"], [{"id": first["id"], "action": "SKIP"}], ACTOR, CUT)
        before = self.store.conn.execute("SELECT proposal_json FROM quick_items WHERE id=?", (first["id"],)).fetchone()[0]
        progress = []
        quick.repropose(run["run_id"], "V10_SYNTHETIC", CUT, progress=lambda done, total: progress.append((done, total)))
        self.assertEqual(before, self.store.conn.execute("SELECT proposal_json FROM quick_items WHERE id=?", (first["id"],)).fetchone()[0])
        self.assertEqual([(1, 1)], progress)

    def test_similar_waiting_finds_rows_with_the_same_counterpart_account(self):
        self._setup()
        run = self._run(self._bank("V10-SIM-1", counterpart_account="006666"), self._bank("V10-SIM-2", amount=-50, counterpart_account="006666"),
                        self._bank("V10-SIM-3", amount=-60, counterpart_account="005555"))
        quick = QuickPosting(self.store)
        rows = {row["source_reference"]: row for row in run["rows"]}
        found = quick.similar_waiting(run["run_id"], rows["V10-SIM-1"]["document_id"], CUT)
        self.assertEqual([rows["V10-SIM-2"]["document_id"]], found)

    def test_same_file_hash_reopens_its_run(self):
        self._setup()
        run = self._run(self._bank("V10-HASH"))
        attempt = self.store.conn.execute("SELECT source_attempt_id FROM quick_runs WHERE id=?", (run["run_id"],)).fetchone()[0]
        self.assertEqual(run["run_id"], QuickPosting(self.store).run_for_hash("HASH_" + attempt))
        self.assertIsNone(QuickPosting(self.store).run_for_hash("NOT_SEEN"))

    # -- speed-ups keep their exact meaning -----------------------------------
    def test_batch_identifier_lookup_equals_single_lookups(self):
        items = [knowledge_item("CATALOG", "COUNTERPARTY:" + code, {"kind": "COUNTERPARTY", "code": code, "name": code}) for code in ("P1", "P2")]
        items += [knowledge_item("CATALOG", "ID:A", {"kind": "IDENTIFIER", "code": "ID_A", "identifier_type": "BANK_ACCOUNT", "value": "001111", "counterparty": "P1", "verified": True}),
                  knowledge_item("CATALOG", "ID:B", {"kind": "IDENTIFIER", "code": "ID_B", "identifier_type": "BANK_ACCOUNT", "value": "001111", "counterparty": "P2", "verified": True}),
                  knowledge_item("CATALOG", "ID:C", {"kind": "IDENTIFIER", "code": "ID_C", "identifier_type": "COUNTERPARTY_NAME", "value": "NAME C", "counterparty": "P1", "verified": False})]
        self._stage(items)
        pairs = [("BANK_ACCOUNT", "001111"), ("COUNTERPARTY_NAME", "NAME C"), ("TAX_ID", "0101")]
        for pending in (False, True):
            batch = self.kb.resolve_identifiers(pairs, "2026-09-15", CUT, include_pending=pending)
            for kind, value in pairs:
                with self.subTest(kind=kind, pending=pending):
                    self.assertEqual(self.kb.resolve_identifier(kind, value, "2026-09-15", CUT, include_pending=pending), batch[(kind, value)])

    def test_threshold_similarity_matches_full_similarity(self):
        samples = ["THANH TOAN TIEN DIEN T8", "Thanh toán tiền điện tháng 8", "PHI SMS BDSD", "phi quan ly", "", "CHUYEN TIEN 0123456 NGUYEN VAN A"]
        for left in samples:
            for right in samples:
                for threshold in (0.5, 0.8, 0.95):
                    self.assertEqual(text_similarity(left, right) >= threshold, similar_at_least(left, right, threshold), (left, right, threshold))

    def test_knowledge_query_returns_independent_payload_copies(self):
        self._stage([knowledge_item("CATALOG", "ACCOUNT:7000", {"kind": "ACCOUNT", "code": "7000", "name": "A"})])
        first = self.kb.query("2026-09-15", CUT, "CATALOG")
        first[0]["payload"]["name"] = "CHANGED"
        self.assertEqual("A", self.kb.query("2026-09-15", CUT, "CATALOG")[0]["payload"]["name"])


class V10SettingsTests(FeatureCase):
    def _operations(self):
        operation = object.__new__(Operations)
        operation.config = self.config
        operation.root = self.root
        operation._mutation_lock = threading.RLock()
        return operation

    def test_learning_cutoff_and_debt_accounts_are_validated_settings(self):
        operation = self._operations()
        paths = {key: str(self.root / key) for key in ("junsky_catalog", "junsky_dgblist", "junsky_ledger", "bank", "invoice", "base")}
        saved = operation.save_source_settings({"paths": paths, "settings": {"learning_cutoff": "2026-06-30", "debt_accounts": ["331", "131", "331"]}})
        self.assertEqual("2026-06-30", saved["settings"]["learning_cutoff"])
        self.assertEqual(["131", "331"], saved["settings"]["debt_accounts"])
        self.assertEqual("2026-06-30", Engine(self.store)._learning_cutoff())
        for bad in ({"learning_cutoff": "30/06/2026"}, {"debt_accounts": ["33A"]}):
            with self.subTest(bad=bad), self.assertRaises(DataError):
                operation.save_source_settings({"paths": paths, "settings": bad})
        cleared = operation.save_source_settings({"paths": paths, "settings": {"learning_cutoff": ""}})
        self.assertEqual("", cleared["settings"]["learning_cutoff"])

    def test_cash_accounts_in_settings_file_become_manual_mappings_once(self):
        operation = self._operations()
        (self.root / "source-settings.json").write_text(json.dumps({"paths": {}, "settings": {"cash_accounts": [{"bank_account": "0000 5555 66", "cash_account": "1121"}]}}), encoding="utf-8")
        self.assertEqual(1, operation._apply_file_cash_accounts())
        row = self.store.conn.execute("SELECT cash_account,source FROM cash_account_mappings WHERE bank_account='0000555566'").fetchone()
        self.assertEqual(("1121", "MANUAL"), tuple(row))
        self.assertEqual(0, operation._apply_file_cash_accounts())


if __name__ == "__main__":
    import unittest
    unittest.main()


class V10ReviewFixTests(V10Base):
    """Regression tests for the independent review of the V10 change."""

    def _existing_run(self, reference, day="2026-09-15"):
        journal = {"kind": "JOURNAL", "business_date": day, "currency": "VND", "amount": "0", "book": "NKC_SYN", "fiscal_year": "2026",
                   "voucher_type": "BP", "voucher_number": "UNIT_SYNBP2609-0099", "source_status": "POSTED_SOURCE_FIXTURE", "complete_voucher": True,
                   "unit_code": "UNIT_SYN", "description": "SYNTHETIC PAYMENT",
                   "lines": [{"line_id": "1", "account": "6427", "debit": "1000", "credit": "0"}, {"line_id": "2", "account": "1121", "debit": "0", "credit": "1000"}]}
        exported = (date.fromisoformat(day) + timedelta(days=1)).isoformat() + "T00:00:00Z"
        self.ingest(envelope("junsky_xuat", [journal], as_of=day, exported=exported))
        return self._run(self._bank(reference, day=day))

    def test_clear_existing_never_approves_a_skipped_row_and_never_reopens_an_export(self):
        self._setup()
        run = self._existing_run("V10-FIX-SKIP")
        row = run["rows"][0]
        self.assertEqual("EXISTING", row["state"])
        quick = QuickPosting(self.store)
        with self.assertRaises(DataError):
            quick.decide(run["run_id"], [{"id": row["id"], "action": "SKIP"}], ACTOR, CUT)
        cleared = quick.decide(run["run_id"], [{"id": row["id"], "action": "CLEAR_EXISTING"}], ACTOR, CUT)["rows"][0]
        self.assertEqual("WAIT", cleared["state"])
        quick.decide(run["run_id"], [{"id": row["id"], "action": "SKIP"}], ACTOR, CUT)
        self.assertEqual("SKIP", quick.decide(run["run_id"], [{"id": row["id"], "action": "CLEAR_EXISTING"}], ACTOR, CUT)["rows"][0]["state"])
        quick.decide(run["run_id"], [{"id": row["id"], "action": "REOPEN"}], ACTOR, CUT)
        quick.decide(run["run_id"], [{"id": row["id"], "action": "APPROVE"}], ACTOR, CUT)
        quick.export(run["run_id"], self.root, junsky_files=False)
        with self.assertRaises(DataError):
            quick.decide(run["run_id"], [{"id": row["id"], "action": "CLEAR_EXISTING"}], ACTOR, CUT)
        with self.assertRaises(DataError):
            quick.export(run["run_id"], self.root, junsky_files=False)

    def test_repropose_keeps_the_operator_clearance(self):
        self._setup()
        run = self._existing_run("V10-FIX-RP")
        row = run["rows"][0]
        quick = QuickPosting(self.store)
        quick.decide(run["run_id"], [{"id": row["id"], "action": "CLEAR_EXISTING"}], ACTOR, CUT)
        again = quick.repropose(run["run_id"], "V10_SYNTHETIC", CUT)["rows"][0]
        self.assertEqual("WAIT", again["state"])
        self.assertFalse(again["potential_existing"])

    def test_approved_but_possibly_existing_row_is_never_written_or_marked(self):
        self._setup()
        run = self._existing_run("V10-FIX-EX")
        row = run["rows"][0]
        quick = QuickPosting(self.store)
        quick.decide(run["run_id"], [{"id": row["id"], "action": "APPROVE"}], ACTOR, CUT)
        first = quick.export(run["run_id"], self.root)
        self.assertEqual(0, first["reviewed"])
        self.assertEqual("APPROVE", quick.rows(run["run_id"])["rows"][0]["state"])

    def test_reopen_revokes_the_learned_bank_account_identifier(self):
        self._setup()
        run = self._run(self._bank("V10-FIX-ID-1", counterpart_account="004444"))
        row = run["rows"][0]
        quick = QuickPosting(self.store)
        quick.decide(run["run_id"], [{"id": row["id"], "action": "APPROVE", "fields": {**row["fields"], "counterparty": "CP_SYN"}}], ACTOR, CUT)
        self.assertEqual("UNIQUE", self.kb.resolve_identifier("BANK_ACCOUNT", "004444", "2026-09-20", CUT)["status"])
        quick.decide(run["run_id"], [{"id": row["id"], "action": "REOPEN"}], ACTOR, CUT)
        self.assertEqual("UNKNOWN", self.kb.resolve_identifier("BANK_ACCOUNT", "004444", "2026-09-20", "2099-12-31T00:00:00Z")["status"])

    def test_fields_path_rejects_a_reversed_or_missing_bank_leg(self):
        self._setup()
        run = self._run(self._bank("V10-FIX-CASH"))
        row = run["rows"][0]
        quick = QuickPosting(self.store)
        for fields in ({"counterparty": None, "debit_account": "1121", "credit_account": "6427", "project": None, "expense": None},
                       {"counterparty": "CP_SYN", "debit_account": "6427", "credit_account": "331", "project": None, "expense": None}):
            with self.subTest(fields=fields), self.assertRaises(DataError):
                quick.decide(run["run_id"], [{"id": row["id"], "action": "APPROVE", "fields": fields}], ACTOR, CUT)
        self.assertEqual("WAIT", quick.rows(run["run_id"])["rows"][0]["state"])

    def test_level_two_export_is_locked_by_configuration(self):
        operation = object.__new__(Operations)
        operation.config = self.config
        operation.root = self.root
        operation._mutation_lock = threading.RLock()
        if not self.config.junsky_export_enabled:
            with self.assertRaises(DataError) as caught:
                operation.quick_export("RUN_SYNTHETIC", junsky_files=True)
            self.assertEqual("JUNSKY_EXPORT_LOCKED", caught.exception.code)

    def test_first_seen_parses_workbook_date_shapes(self):
        self.assertEqual("2026-08-01", Engine._first_seen("08/2026"))
        self.assertEqual("2026-08-15", Engine._first_seen("15/08/2026"))
        self.assertEqual("2026-08-15", Engine._first_seen("2026-08-15 00:00:00"))
        self.assertEqual("", Engine._first_seen(None))
