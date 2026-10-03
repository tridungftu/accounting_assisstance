"""V9b contracts use generated records only; no PLHN source data appears here.

The tests deliberately exercise the public quick-posting/engine boundary.  They
are a specification for the behaviour that operators see, rather than tests of
SQLite implementation details.
"""
from __future__ import annotations

import json
import threading
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook, load_workbook

from test_modules import FeatureCase
from kho_tri_thuc.de_xuat.engine import Engine, FIELDS
from kho_tri_thuc.giao_dien.operations import Operations
from kho_tri_thuc.giao_dien.quick import QuickPosting
from kho_tri_thuc.giao_dien.v9b import bank_account, journal_suggestion
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.ha_tang.runtime import document
from kho_tri_thuc.kiem_chung.fixtures import CUTOFF, envelope, knowledge_item
from kho_tri_thuc.xuat.shadow import ENTRY1_HEADERS, ENTRY2_HEADERS


# This is intentionally far in the future of all generated source snapshots.
# QuickPosting.set_cash_mapping() may use its own current timestamp, so a fixed
# September-2026 cutoff would make a test depend on the computer clock.
CUT = "2099-01-01T00:00:00Z"
ACTOR = "CFO_NTD"


class V9bQuickPostingTests(FeatureCase):
    def _stage(self, items, *, approve=True):
        identifiers = self.kb.stage_many(items, "V9B_SYNTHETIC", CUT)
        if approve:
            for identifier in identifiers:
                self.kb.approve(identifier, "V9B_SYNTHETIC", CUT)
        return identifiers

    @staticmethod
    def _catalogs(*, parties=("CP_SYN",), accounts=("1121", "6427")):
        items = []
        for party in parties:
            items.append(knowledge_item("CATALOG", "COUNTERPARTY:" + party,
                                        {"kind": "COUNTERPARTY", "code": party, "name": "Synthetic " + party}))
        for account in accounts:
            items.append(knowledge_item("CATALOG", "ACCOUNT:" + account,
                                        {"kind": "ACCOUNT", "code": account, "name": "Synthetic " + account}))
        return items

    @staticmethod
    def _policy(key, *, direction="OUT", fields=None, required=None, tier=1, order=1, partition=None):
        return knowledge_item("POLICY", key, {
            "contract_version": 2,
            "template_id": key,
            "partition": partition or key,
            "direction": direction,
            "tier": tier,
            "order": order,
            "needs_open_item": False,
            "required_fields": list(required if required is not None else ("counterparty", "debit_account", "credit_account")),
            "trigger": {"mode": "REGEX", "regex": "SYNTHETIC"},
            "fields": dict(fields or {}),
        })

    @staticmethod
    def _rule(key, fields, trigger):
        return knowledge_item("RULE", key, {"contract_version": 2, "fields": dict(fields), "trigger": trigger})

    @staticmethod
    def _identifier(key, value, party, source_status):
        return knowledge_item("CATALOG", key, {
            "kind": "IDENTIFIER", "code": key, "identifier_type": "BANK_ACCOUNT", "value": value,
            "counterparty": party, "verified": True, "source_status": source_status,
        })

    @staticmethod
    def _bank(reference, *, amount=-100, day="2026-09-15", counterpart_account="", description="SYNTHETIC PAYMENT"):
        record = {
            "business_date": day, "currency": "VND", "amount": str(amount), "bank": "BANK_SYN",
            "account": "00001234", "id_scope": "v9b-synthetic", "reference": reference,
            "description": description, "identity_verified": True,
        }
        if counterpart_account:
            record["counterparty_account"] = counterpart_account
        return record

    def _bank_document(self, record):
        attempt = self.ingest(envelope("sao_ke", [record]))
        identifier = self.store.conn.execute("SELECT id FROM documents WHERE first_attempt_id=? AND kind='BANK'", (attempt,)).fetchone()[0]
        return attempt, document(self.store, identifier, CUT)

    @staticmethod
    def _bundle(*documents):
        return {"manifest": {"as_of": "9999-12-31", "posting_evidence_complete": True}, "documents": list(documents)}

    def _quick_ready(self, *, policy_fields=None):
        # The generic regex policy deliberately does not fill the counterparty
        # (S4); cash is supplied from the separate source-account mapping.
        fields = policy_fields or {"debit_account": "6427"}
        self._stage(self._catalogs() + [self._policy("POLICY_V9B", fields=fields, required=("debit_account", "credit_account"))])
        QuickPosting(self.store).set_cash_mapping("00001234", "1121", ACTOR, source="MANUAL", evidence=["V9B_SYNTHETIC"])

    def test_s1_cash_leg_uses_configured_112_and_is_strong_for_both_directions(self):
        self._stage(self._catalogs() + [
            self._policy("CASH_OUT", fields={"debit_account": "6427"}, required=("debit_account", "credit_account")),
            self._policy("CASH_IN", direction="IN", fields={"credit_account": "6427"}, required=("debit_account", "credit_account")),
        ])
        quick = QuickPosting(self.store)
        # Public V9b configuration API.  Its mapping is local configuration,
        # not an inferred posting rule.
        quick.set_cash_mapping("00001234", "1121", ACTOR, source="MANUAL", evidence=["V9B_SYNTHETIC"])
        _, outgoing = self._bank_document(self._bank("S1-OUT", amount=-100))
        _, incoming = self._bank_document(self._bank("S1-IN", amount=100))
        engine = Engine(self.store)
        out = engine.preview(outgoing, self._bundle(), CUT)
        inc = engine.preview(incoming, self._bundle(), CUT)
        self.assertEqual("1121", out["cash_leg"]["account"])
        self.assertEqual("CREDIT", out["cash_leg"]["side"])
        self.assertEqual("1121", out["fields"]["credit_account"])
        self.assertEqual("CAU_HINH_TK_TIEN", out["confidence"]["credit_account"]["level"])
        self.assertEqual("1121", inc["cash_leg"]["account"])
        self.assertEqual("DEBIT", inc["cash_leg"]["side"])
        self.assertEqual("1121", inc["fields"]["debit_account"])
        self.assertEqual("CAU_HINH_TK_TIEN", inc["confidence"]["debit_account"]["level"])

    def test_s2_pending_strong_template_can_turn_green_without_being_relabelled_approved(self):
        self._stage(self._catalogs())
        # Pending knowledge is intentionally visible to the proposal mode.  A
        # 3/3 rule is strong enough to be green, but must retain a PENDING
        # evidence label rather than being silently presented as approved.
        pending = self._policy("PENDING_ONLY", fields={"debit_account": "6427"}, required=("debit_account", "credit_account"))
        pending["payload"].update(occurrences=3, correct_occurrences=3)
        self._stage([pending], approve=False)
        QuickPosting(self.store).set_cash_mapping("00001234", "1121", ACTOR, source="MANUAL", evidence=["V9B_SYNTHETIC"])
        attempt, _ = self._bank_document(self._bank("S2-PENDING"))
        result = QuickPosting(self.store).propose(attempt, "sao_ke", "V9B_SYNTHETIC", cutoff=CUT)
        self.assertEqual("Xanh", result["rows"][0]["level"])
        self.assertTrue(any(term in result["rows"][0]["why"].upper() for term in ("PENDING", "CHỜ")))

    def test_s2_pending_one_occurrence_stays_yellow(self):
        self._stage(self._catalogs())
        pending = self._policy("PENDING_ONCE", fields={"debit_account": "6427"}, required=("debit_account", "credit_account"))
        pending["payload"].update(occurrences=1, correct_occurrences=1)
        self._stage([pending], approve=False)
        QuickPosting(self.store).set_cash_mapping("00001234", "1121", ACTOR, source="MANUAL", evidence=["V9B_SYNTHETIC"])
        attempt, _ = self._bank_document(self._bank("S2-PENDING-ONE"))
        result = QuickPosting(self.store).propose(attempt, "sao_ke", "V9B_SYNTHETIC", cutoff=CUT)
        self.assertEqual("Vàng", result["rows"][0]["level"])

    def test_s4_regex_rule_cannot_fill_counterparty_but_bank_account_key_can(self):
        self._stage(self._catalogs(parties=("CP_REGEX", "CP_KEY")) + [
            self._policy("S4_POLICY", fields={"debit_account": "6427", "credit_account": "1121"}, required=("debit_account", "credit_account")),
            self._rule("S4_REGEX", {"counterparty": "CP_REGEX"}, {"mode": "REGEX", "regex": "SYNTHETIC"}),
            self._rule("S4_BANK_KEY", {"counterparty": "CP_KEY"}, {"mode": "KEY", "key_type": "BANK_ACCOUNT", "key_value": "009999"}),
        ])
        QuickPosting(self.store).set_cash_mapping("00001234", "1121", ACTOR, source="MANUAL", evidence=["V9B_SYNTHETIC"])
        _, from_regex = self._bank_document(self._bank("S4-REGEX"))
        _, from_key = self._bank_document(self._bank("S4-KEY", counterpart_account="009999"))
        engine = Engine(self.store)
        self.assertIsNone(engine.preview(from_regex, self._bundle(), CUT)["fields"]["counterparty"])
        self.assertEqual("CP_KEY", engine.preview(from_key, self._bundle(), CUT)["fields"]["counterparty"])

    def test_s5_directory_priority_selects_high_and_same_level_conflict_waits(self):
        self._stage(self._catalogs(parties=("CP_HIGH", "CP_MEDIUM", "CP_CONFLICT_A", "CP_CONFLICT_B")) + [
            self._policy("S5_POLICY", fields={"debit_account": "6427", "credit_account": "1121"}, required=("debit_account", "credit_account")),
            self._identifier("ID-HIGH", "001111", "CP_HIGH", "DIRECTORY_HIGH"),
            self._identifier("ID-MEDIUM", "001111", "CP_MEDIUM", "DIRECTORY_MEDIUM"),
            self._identifier("ID-HIGH-A", "002222", "CP_CONFLICT_A", "DIRECTORY_HIGH"),
            self._identifier("ID-HIGH-B", "002222", "CP_CONFLICT_B", "DIRECTORY_HIGH"),
        ])
        QuickPosting(self.store).set_cash_mapping("00001234", "1121", ACTOR, source="MANUAL", evidence=["V9B_SYNTHETIC"])
        _, higher = self._bank_document(self._bank("S5-HIGH", counterpart_account="001111"))
        _, conflict = self._bank_document(self._bank("S5-CONFLICT", counterpart_account="002222"))
        engine = Engine(self.store)
        selected = engine.preview(higher, self._bundle(), CUT)
        blocked = engine.preview(conflict, self._bundle(), CUT)
        self.assertEqual("CP_HIGH", selected["fields"]["counterparty"])
        self.assertEqual("DIRECTORY_HIGH", selected["confidence"]["counterparty"]["level"])
        self.assertIn("IDENTIFIER_CONFLICT", blocked["constraints"])
        self.assertIsNone(blocked["fields"]["counterparty"])

    def test_s5_every_higher_identifier_rank_wins_over_each_lower_rank(self):
        """Exercise every ordered pair in the S5 priority list."""
        ranks = [
            ("QUICK_DECISION", "CP_1"),
            ("DIRECTORY_CORRECT", "CP_2"),
            ("DIRECTORY_HIGH", "CP_3"),
            ("DIRECTORY_MEDIUM", "CP_4"),
            ("MACHINE_CHAC_CHAN", "CP_5"),
            ("DIRECTORY_LOW", "CP_6"),
            ("MACHINE_NHAP", "CP_7"),
        ]
        items = self._catalogs(parties=tuple(code for _, code in ranks))
        expected: dict[str, str] = {}
        for high, (status, party) in enumerate(ranks):
            for low, (other_status, other_party) in enumerate(ranks[high + 1 :], high + 1):
                value = f"77{high}{low}0000"
                expected[value] = party
                items.extend((
                    self._identifier(f"S5-{high}-{low}-HIGH", value, party, status),
                    self._identifier(f"S5-{high}-{low}-LOW", value, other_party, other_status),
                ))
        self._stage(items)
        engine = Engine(self.store)
        for value, party in expected.items():
            selected, _, failure, _ = engine._identify_counterparty(
                {"business_date": "2026-09-15", "counterparty_account": value}, CUT
            )
            self.assertIsNone(failure)
            self.assertEqual(party, selected)

    def _add_unique_journal(self, *, day, amount, voucher, unit="UNIT_SYN", description="SYNTHETIC PAYMENT"):
        journal = {
            "kind": "JOURNAL", "business_date": day, "currency": "VND", "amount": "0", "book": "NKC_SYN",
            "fiscal_year": "2026", "voucher_type": "BP", "voucher_number": voucher,
            "source_status": "POSTED_SOURCE_FIXTURE", "complete_voucher": True, "unit_code": unit,
            "description": description,
            "lines": [
                {"line_id": "1", "account": "6427", "debit": str(amount), "credit": "0"},
                {"line_id": "2", "account": "1121", "debit": "0", "credit": str(amount)},
            ],
        }
        exported = (date.fromisoformat(day) + timedelta(days=1)).isoformat() + "T00:00:00Z"
        self.ingest(envelope("junsky_xuat", [journal], as_of=day, exported=exported))

    def test_s7_unique_journal_match_marks_existing_and_operator_can_clear_before_export(self):
        self._quick_ready()
        self._add_unique_journal(day="2026-09-15", amount=100, voucher="BP_SYN_S7")
        attempt, _ = self._bank_document(self._bank("S7-BANK"))
        quick = QuickPosting(self.store)
        proposal = quick.propose(attempt, "sao_ke", "V9B_SYNTHETIC", cutoff=CUT)
        item = proposal["rows"][0]
        self.assertTrue(item["potential_existing"])
        self.assertIn("BP_SYN_S7", item["why"])
        decision = {name: item["fields"].get(name) for name in FIELDS}
        quick.decide(proposal["run_id"], [{"id": item["id"], "action": "APPROVE", "fields": decision}], ACTOR, CUT)
        blocked = quick.export(proposal["run_id"], self.root)
        self.assertEqual(0, blocked["approved"])
        quick.clear_existing(proposal["run_id"], item["id"], ACTOR, CUT)
        allowed = quick.export(proposal["run_id"], self.root)
        self.assertEqual(1, allowed["approved"])

    def _approved_clearable_bank(self, reference, *, day, voucher):
        self._add_unique_journal(day=day, amount=100, voucher=voucher)
        attempt, _ = self._bank_document(self._bank(reference, day=day))
        quick = QuickPosting(self.store)
        proposal = quick.propose(attempt, "sao_ke", "V9B_SYNTHETIC", cutoff=CUT)
        item = proposal["rows"][0]
        decision = {name: item["fields"].get(name) for name in FIELDS}
        quick.decide(proposal["run_id"], [{"id": item["id"], "action": "APPROVE", "fields": decision}], ACTOR, CUT)
        quick.clear_existing(proposal["run_id"], item["id"], ACTOR, CUT)
        return quick.export(proposal["run_id"], self.root)

    def test_s9_export_fallback_headers_and_unit_voucher_counter_are_stable(self):
        self._quick_ready()
        first = self._approved_clearable_bank("S9-FIRST", day="2026-09-15", voucher="BP_SYN_S9_1")
        second = self._approved_clearable_bank("S9-SECOND", day="2026-09-16", voucher="BP_SYN_S9_2")
        self.assertEqual(1, len(first["voucher_ids"]))
        self.assertEqual(1, len(second["voucher_ids"]))
        first_id, second_id = first["voucher_ids"][0], second["voucher_ids"][0]
        self.assertTrue(first_id.startswith("UNIT_SYNBP2609-"), first_id)
        self.assertTrue(second_id.startswith("UNIT_SYNBP2609-"), second_id)
        self.assertNotEqual(first_id, second_id)
        self.assertTrue(first_id.endswith("0001"), first_id)
        self.assertTrue(second_id.endswith("0002"), second_id)
        chi = next(Path(path) for path in first["files"] if "CHI" in Path(path).name)
        book = load_workbook(chi, read_only=True, data_only=False, keep_links=False)
        try:
            self.assertEqual(ENTRY1_HEADERS, tuple(book["CB_tmpEntry1"].cell(1, column).value for column in range(1, 18)))
            self.assertEqual(ENTRY2_HEADERS, tuple(book["CB_tmpEntry2"].cell(1, column).value for column in range(1, 38)))
        finally:
            book.close()

    def test_s9_one_export_groups_each_month_and_unit_with_its_own_entry_prefix(self):
        self._quick_ready()
        self._add_unique_journal(day="2026-09-15", amount=100, voucher="UNIT_ABP2609-0001", unit="UNIT_A")
        self._add_unique_journal(day="2026-10-15", amount=100, voucher="UNIT_BBP2610-0001", unit="UNIT_B")
        attempt = self.ingest(envelope("sao_ke", [
            self._bank("S9-MONTH-A", day="2026-09-15"),
            self._bank("S9-MONTH-B", day="2026-10-15"),
        ], as_of="2026-10-15", exported="2026-10-16T00:00:00Z"))
        quick = QuickPosting(self.store)
        proposal = quick.propose(attempt, "sao_ke", "V9B_SYNTHETIC", cutoff=CUT)
        decisions = []
        for row in proposal["rows"]:
            decisions.append({"id": row["id"], "action": "APPROVE", "fields": {name: row["fields"].get(name) for name in FIELDS}})
        quick.decide(proposal["run_id"], decisions, ACTOR, CUT)
        for row in proposal["rows"]:
            quick.clear_existing(proposal["run_id"], row["id"], ACTOR, CUT)
        # This synthetic test intentionally spans two months after the
        # workstation clock.  Export is evaluated at a later replay cutoff,
        # not against today's live operational clock.
        with patch("kho_tri_thuc.giao_dien.quick.now_utc", return_value="2099-01-01T00:00:00Z"):
            result = quick.export(proposal["run_id"], self.root)
        self.assertEqual(2, len(result["files"]))
        self.assertEqual(2, len(result["voucher_ids"]))
        self.assertTrue(any(value.startswith("UNIT_ABP2609-") for value in result["voucher_ids"]))
        self.assertTrue(any(value.startswith("UNIT_BBP2610-") for value in result["voucher_ids"]))

    def test_s10_approval_learns_counterparty_by_account_for_another_date_and_amount(self):
        self._stage(self._catalogs() + [self._policy("S10_POLICY", fields={"debit_account": "6427"})])
        QuickPosting(self.store).set_cash_mapping("00001234", "1121", ACTOR, source="MANUAL", evidence=["V9B_SYNTHETIC"])
        first_attempt, _ = self._bank_document(self._bank("S10-FIRST", day="2026-09-15", amount=-100, counterpart_account="009999"))
        quick = QuickPosting(self.store)
        first = quick.propose(first_attempt, "sao_ke", "V9B_SYNTHETIC", cutoff=CUT)
        item = first["rows"][0]
        fields = {**item["fields"], "counterparty": "CP_SYN"}
        quick.decide(first["run_id"], [{"id": item["id"], "action": "APPROVE", "fields": fields}], ACTOR, CUT)
        second_attempt, _ = self._bank_document(self._bank("S10-SECOND", day="2026-09-16", amount=-999, counterpart_account="009999"))
        second = quick.propose(second_attempt, "sao_ke", "V9B_SYNTHETIC", cutoff=CUT)
        replay = second["rows"][0]
        self.assertEqual("CP_SYN", replay["fields"]["counterparty"])
        self.assertEqual("Xanh", replay["level"])

    def test_s11_bank_account_normalization_keeps_one_long_identifier_across_three_shapes(self):
        self.assertEqual("000012345678", bank_account("NH: 000012345678; mã giao dịch 123"))
        self.assertEqual("9876543210", bank_account("Ref 77 / STK 9876543210 / 05"))
        self.assertEqual("", bank_account("mã 123 và 4567 không phải STK"))

    def test_s11_partner_directory_obeys_dung_bo_sua_blank_and_entered_statuses(self):
        parties = ("CP_DUNG", "CP_BO", "CP_SUA", "CP_TRONG", "CP_NHAP")
        self._stage(self._catalogs(parties=parties))
        source = self.root / "partner-directory-synthetic.xlsx"
        book = Workbook(); sheet = book.active; sheet.title = "DOI TAC"
        sheet.append(["Mã đối tượng", "STK 1", "STK 2", "STK 3", "STK khác", "Độ tin cậy STK (1/2/3)", "Anh xác nhận (Đúng/Sửa/Bỏ)"])
        sheet.append(["CP_DUNG", "0000011111", "", "", "", "1", "Đúng"])
        sheet.append(["CP_BO", "0000022222", "", "", "", "1", "Bỏ"])
        sheet.append(["CP_SUA", "0000033333", "", "", "", "1", "Sửa"])
        sheet.append(["CP_TRONG", "0000044444", "", "", "", "2", ""])
        pending = book.create_sheet("STK CHUA GAN")
        pending.append(["STK", "Anh điền mã đối tượng"])
        pending.append(["0000055555", "CP_NHAP"])
        book.save(source); book.close()
        operations = object.__new__(Operations)
        operations.config = self.config
        self.assertEqual(3, operations._import_partner_directory(self.store, source, CUT))
        knowledge = self.kb
        correct = knowledge.resolve_identifier("BANK_ACCOUNT", "0000011111", "2026-09-15", CUT)["matches"]
        entered = knowledge.resolve_identifier("BANK_ACCOUNT", "0000055555", "2026-09-15", CUT)["matches"]
        blank = knowledge.resolve_identifier("BANK_ACCOUNT", "0000044444", "2026-09-15", CUT, include_pending=True)["matches"]
        self.assertEqual(["DIRECTORY_CORRECT"], [row["source_status"] for row in correct])
        self.assertEqual(["DIRECTORY_ENTERED"], [row["source_status"] for row in entered])
        self.assertEqual(["DIRECTORY_MEDIUM"], [row["source_status"] for row in blank])
        self.assertEqual([], knowledge.resolve_identifier("BANK_ACCOUNT", "0000022222", "2026-09-15", CUT, include_pending=True)["matches"])
        self.assertEqual([], knowledge.resolve_identifier("BANK_ACCOUNT", "0000033333", "2026-09-15", CUT, include_pending=True)["matches"])

    def test_s11_own_counterparty_code_cannot_be_selected_by_identifier_or_rule(self):
        self._stage(self._catalogs(parties=("CP_OWN",)) + [
            self._policy("OWN_POLICY", fields={"debit_account": "6427"}, required=("debit_account", "credit_account")),
            self._identifier("OWN_IDENTIFIER", "008888", "CP_OWN", "DIRECTORY_CORRECT"),
            self._rule("OWN_RULE", {"counterparty": "CP_OWN"}, {"mode": "KEY", "key_type": "BANK_ACCOUNT", "key_value": "008888"}),
        ])
        self.store.conn.execute("INSERT INTO workspace_meta(key,value) VALUES ('v9b_runtime_settings',?)", (json.dumps({"own_counterparty_codes": ["CP_OWN"]}),))
        self.store.conn.commit()
        QuickPosting(self.store).set_cash_mapping("00001234", "1121", ACTOR, source="MANUAL", evidence=["V9B_SYNTHETIC"])
        _, bank = self._bank_document(self._bank("S11-OWN", counterpart_account="008888"))
        proposal = Engine(self.store).preview(bank, self._bundle(), CUT)
        self.assertIsNone(proposal["fields"]["counterparty"])
        self.assertNotIn("IDENTIFIER_CONFLICT", proposal["constraints"])

    def test_s11_ambiguous_journal_warning_does_not_block_a_balanced_export(self):
        self._quick_ready()
        self._add_unique_journal(day="2026-09-15", amount=100, voucher="BP_SYN_WARN_A")
        self._add_unique_journal(day="2026-09-15", amount=100, voucher="BP_SYN_WARN_B")
        attempt, bank = self._bank_document(self._bank("S11-WARN"))
        journals = [document(self.store, row[0], CUT) for row in self.store.conn.execute("SELECT id FROM documents WHERE kind='JOURNAL'")]
        preview = Engine(self.store).preview(bank, self._bundle(*journals), CUT)
        self.assertIn("JOURNAL_MATCH_AMBIGUOUS", preview["warnings"])
        self.assertNotIn("JOURNAL_MATCH_AMBIGUOUS", preview["constraints"])
        self.assertEqual("FULL", preview["completeness"])
        quick = QuickPosting(self.store)
        run = quick.propose(attempt, "sao_ke", "V9B_SYNTHETIC", cutoff=CUT)
        item = run["rows"][0]
        self.assertFalse(item["potential_existing"])
        fields = {name: item["fields"].get(name) for name in FIELDS}
        quick.decide(run["run_id"], [{"id": item["id"], "action": "APPROVE", "fields": fields}], ACTOR, CUT)
        exported = quick.export(run["run_id"], self.root)
        workbook = load_workbook(exported["files"][0], read_only=True, data_only=False, keep_links=False)
        try:
            rows = list(workbook["CB_tmpEntry2"].iter_rows(min_row=2, values_only=True))
            headers = [cell.value for cell in next(workbook["CB_tmpEntry2"].iter_rows(min_row=1, max_row=1))]
            debit, credit = headers.index("OrglDeb"), headers.index("OrglCrd")
            self.assertEqual(sum(int(row[debit] or 0) for row in rows), sum(int(row[credit] or 0) for row in rows))
        finally:
            workbook.close()

    @staticmethod
    def _learning_journal(identifier, day, *, debit="6427", lines=None, counterparty="CP_HISTORY"):
        return {
            "id": identifier, "business_date": day, "voucher_type": "BP", "voucher_number": "BP_" + identifier,
            "description": "009999 SYNTHETIC SERVICE", "counterparty": counterparty, "project": "P_SYN", "expense": "E_SYN",
            "lines": lines or [
                {"account": debit, "debit_minor": 100, "credit_minor": 0},
                {"account": "1121", "debit_minor": 0, "credit_minor": 100},
            ],
        }

    @staticmethod
    def _tax_split_lines(vat_account="1331"):
        return [
            {"account": "6427", "debit_minor": 90, "credit_minor": 0},
            {"account": vat_account, "debit_minor": 10, "credit_minor": 0},
            {"account": "1121", "debit_minor": 0, "credit_minor": 100},
        ]

    def test_s11_journal_learning_uses_only_prior_vouchers_and_requires_one_structure_for_strong(self):
        bank = {"business_date": "2026-08-10", "amount_minor": -100, "counterparty_account": "009999", "description": "SYNTHETIC SERVICE"}
        history = [
            self._learning_journal("J1", "2026-08-01", lines=self._tax_split_lines()),
            self._learning_journal("J2", "2026-08-02", lines=self._tax_split_lines()),
            self._learning_journal("J3", "2026-08-03", lines=self._tax_split_lines()),
            # This contradictory voucher is after the cutoff and must not
            # weaken, strengthen, or otherwise leak into the proposal.
            self._learning_journal("FUTURE", "2026-08-11", debit="6411"),
        ]
        strong = journal_suggestion(bank, history, cutoff_day="2026-08-10", own_codes=set(), object_learning_from="2026-07-01")
        self.assertEqual("PENDING_PATTERN_STRONG", strong["strength"])
        self.assertEqual("6427", strong["fields"]["debit_account"])
        self.assertEqual(["J1", "J2", "J3"], strong["source_ids"])
        self.assertEqual([("6427", 90), ("1331", 10)], [(line["account"], line["amount_minor"]) for line in strong["pattern_lines"]])
        divergent = list(history[:2]) + [self._learning_journal("J_DIFFERENT", "2026-08-03", lines=self._tax_split_lines("1332"))]
        weaker = journal_suggestion(bank, divergent, cutoff_day="2026-08-10", own_codes=set(), object_learning_from="2026-07-01")
        self.assertIsNotNone(weaker)
        self.assertNotEqual("PENDING_PATTERN_STRONG", weaker["strength"])
        self.assertEqual([], weaker["pattern_lines"])

    def test_s3_historical_own_code_is_not_learned_as_counterparty(self):
        bank = {"business_date": "2026-08-10", "amount_minor": -100, "counterparty_account": "009999", "description": "SYNTHETIC SERVICE"}
        history = [
            self._learning_journal(f"OWN-{index}", f"2026-08-0{index}", counterparty="CP_OWN")
            for index in range(1, 4)
        ]
        learned = journal_suggestion(bank, history, cutoff_day="2026-08-10", own_codes={"CP_OWN"}, object_learning_from="2026-07-01")
        self.assertIsNotNone(learned)
        self.assertNotIn("counterparty", learned["fields"])
        self.assertEqual("6427", learned["fields"]["debit_account"])

    def test_s11_journal_learning_proposes_a_scaled_multiline_1331_entry(self):
        """The complete historical split is materialized for a new amount."""
        self._stage(self._catalogs(accounts=("1121", "6427", "1331")))
        QuickPosting(self.store).set_cash_mapping("00001234", "1121", ACTOR, source="MANUAL", evidence=["V9B_SYNTHETIC"])
        for number, day in enumerate(("2026-08-01", "2026-08-02", "2026-08-03"), 1):
            history = envelope("junsky_xuat", [{
                "kind": "JOURNAL", "business_date": day, "currency": "VND", "amount": "0", "book": "NKC_SYN",
                "fiscal_year": "2026", "voucher_type": "BP", "voucher_number": f"BP_SPLIT_{number}",
                "source_status": "POSTED_SOURCE_FIXTURE", "complete_voucher": True,
                "description": "009999 SYNTHETIC SERVICE",
                "lines": [{"line_id": str(index), "account": line["account"], "debit": str(line["debit_minor"]), "credit": str(line["credit_minor"])} for index, line in enumerate(self._tax_split_lines(), 1)],
            }], as_of="2026-08-10")
            history["manifest"]["coverage_from"] = "2026-08-01"
            self.ingest(history)
        attempt, _ = self._bank_document(self._bank("S11-SPLIT", amount=-1_000, day="2026-09-10", counterpart_account="009999"))
        row = QuickPosting(self.store).propose(attempt, "sao_ke", "V9B_SYNTHETIC", cutoff=CUT)["rows"][0]
        self.assertEqual("Xanh", row["level"])
        self.assertEqual({"6427", "1331", "1121"}, {line["account"] for line in row["lines"]})
        self.assertEqual(1_000, sum(line["debit_minor"] for line in row["lines"]))
        self.assertEqual(1_000, sum(line["credit_minor"] for line in row["lines"]))

    def test_s9_quick_download_is_limited_to_its_xlsx_run_directory(self):
        operation = object.__new__(Operations)
        operation.root = self.root
        run_id = "RUN_SYNTHETIC"
        output = self.root / "xuat-junsky" / run_id
        output.mkdir(parents=True)
        expected = b"SYNTHETIC XLSX BYTES"
        (output / "SOAT-RUN_SYNTHETIC.xlsx").write_bytes(expected)
        name, content = operation.quick_file(run_id, "SOAT-RUN_SYNTHETIC.xlsx")
        self.assertEqual("SOAT-RUN_SYNTHETIC.xlsx", name)
        self.assertEqual(expected, content)
        for invalid_run, invalid_name in (("../escape", "SOAT-RUN_SYNTHETIC.xlsx"), (run_id, "../outside.xlsx"), (run_id, "notes.txt")):
            with self.subTest(run=invalid_run, name=invalid_name), self.assertRaises(DataError):
                operation.quick_file(invalid_run, invalid_name)

    def test_s9_bankid_mapping_normalizes_a_formatted_source_account(self):
        operation = object.__new__(Operations)
        operation.config = self.config
        operation.root = self.root
        operation._mutation_lock = threading.RLock()
        paths = {key: str(self.root / key) for key in ("junsky_catalog", "junsky_dgblist", "junsky_ledger", "bank", "invoice", "base")}
        saved = operation.save_source_settings({"paths": paths, "settings": {"bank_ids": {"0123 456 789": "BANK_SYN"}}})
        self.assertEqual({"0123456789": "BANK_SYN"}, saved["settings"]["bank_ids"])
        self.assertEqual("0123456789", bank_account("0123 456 789"))


if __name__ == "__main__":
    import unittest
    unittest.main()
