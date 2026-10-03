from __future__ import annotations

import copy
import json
import tempfile
import unittest
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from kho_tri_thuc.de_xuat.engine import Engine, FIELDS
from kho_tri_thuc.ha_tang.backup import create_backup, restore_backup, verify_backup
from kho_tri_thuc.ha_tang.config import Config
from kho_tri_thuc.ha_tang.primitives import DataError, canonical_json
from kho_tri_thuc.ha_tang.runtime import document, source_bundle
from kho_tri_thuc.ha_tang.store import Store
from kho_tri_thuc.hoc.service import Learning, Reconciliation
from kho_tri_thuc.kiem_chung.fixtures import *
from kho_tri_thuc.kiem_chung.service import Quality, reconstruct_open_items, score
from kho_tri_thuc.tri_thuc.service import Knowledge
from kho_tri_thuc.trang_thai.service import Sessions
from kho_tri_thuc.xuat import excel
from kho_tri_thuc.xuat.service import ReviewExport

ROOT = Path(__file__).resolve().parents[1]


class FeatureCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ktt-modules-")
        self.root = Path(self.tmp.name)
        self.config = Config.load(ROOT / "cau_hinh.toml", self.root / "data")
        self.store = Store(self.config)
        self.kb, self.sessions, self.review = Knowledge(self.store), Sessions(self.store), ReviewExport(self.store)
        self.learning, self.recon, self.quality = Learning(self.store), Reconciliation(self.store), Quality(self.store)

    def tearDown(self):
        self.store.conn.close()
        self.tmp.cleanup()

    def ingest(self, value):
        result = self.store.ingest(write_json(self.root / (str(len(list(self.root.glob('*.json')))) + ".json"), value))
        self.assertEqual(result["state"], "COMMITTED", result)
        return result["attempt_id"]

    def seed(self, banks=None, bundle=None, knowledge=None):
        self.ingest(banks or bank_fixture())
        attempt = self.ingest(bundle or bundle_fixture())
        ids = self.kb.stage_many(knowledge or knowledge_fixture(), "TEST_KTT_FIXTURE", KNOWN)
        for identifier in ids:
            self.kb.approve(identifier, "TEST_KTT_FIXTURE", KNOWN)
        bank_ids = [r[0] for r in self.store.conn.execute("SELECT id FROM documents WHERE kind='BANK' ORDER BY natural_key")]
        return attempt, bank_ids, ids

    def open_propose(self, count=2, **kwargs):
        attempt, bank_ids, ids = self.seed(**kwargs)
        session = self.sessions.open(attempt, bank_ids[:count], CUTOFF, "TEST_OPERATOR")
        proposals = self.sessions.propose(session["id"])
        return session, proposals, bank_ids

    def approve(self, session, at=REVIEW_AT):
        wb = self.review.review_workbook(session["id"], "TEST_OPERATOR", at)
        path = approved_review(wb["path"], self.root / (wb["workbook_id"] + "-approved.xlsx"))
        result = self.review.import_review(path, "TEST_KTT_FIXTURE", at)
        return path, result

    def exported(self, count=2, **kwargs):
        session, proposals, bank_ids = self.open_propose(count, **kwargs)
        self.assertTrue(all(p["completeness"] == "FULL" for p in proposals), proposals)
        path, decision = self.approve(session)
        batch = self.review.export(session["id"], "TEST_OPERATOR", EXPORT_AT)
        return batch, session, bank_ids

    def post(self, batch, balance=0, *, journals=None, snapshot="SNAP_POSTED", exported="2026-09-16T03:00:00Z"):
        if journals is None:
            journals = postings_for_batch(self.store, batch["batch_id"])
        attempt = self.ingest(bundle_fixture(balance, snapshot=snapshot, exported=exported, journals=journals))
        report = self.recon.reconcile(batch["batch_id"], attempt, "TEST_VERIFIER_FIXTURE", VERIFY_AT)
        return attempt, report

    def edit(self, path, action):
        wb = excel.load(Path(path).read_bytes())
        try:
            action(wb)
            raw = excel.to_bytes(wb)
        finally:
            wb.close()
        destination = self.root / "edited.xlsx"
        destination.write_bytes(raw)
        return destination

    def dataset(self, attempt, bank_ids):
        value = {"format": "ktt-evaluation-fixture-v1", "synthetic": True, "id": "EXPLICIT_FIXTURE", "version": "1", "records": []}
        for index, bank_id in enumerate(bank_ids):
            value["records"].append({"bank_id": bank_id, "source_attempt_id": attempt, "cutoff": CUTOFF, "group_id": "PAY_GROUP", "split": "BLIND",
                "truth": {"fields": dict(FIELD_VALUES), "allocations": [{"invoice_reference": "HD_FIXTURE_001", "amount_minor": 100}], "reviewer": "FIXTURE_AUTHOR", "evidence": ["hand-defined expected payment 100 per bank"]}})
        return self.quality.register(write_json(self.root / "dataset.json", value))


class KnowledgeTests(FeatureCase):
    def test_pending_never_used_approve_and_revoke_point_in_time(self):
        item = knowledge_fixture()[0]
        identifier = self.kb.stage_many([item], "TEST", KNOWN)[0]
        self.assertEqual(self.kb.query("2026-09-15", CUTOFF), [])
        self.kb.approve(identifier, "TEST", CUTOFF)
        self.assertEqual(len(self.kb.query("2026-09-15", CUTOFF)), 1)
        self.kb.revoke(identifier, "TEST", REVIEW_AT, "test")
        self.assertEqual(len(self.kb.query("2026-09-15", CUTOFF)), 1)
        self.assertEqual(self.kb.query("2026-09-15", REVIEW_AT), [])

    def test_import_idempotent_and_overlap_requires_explicit_supersession(self):
        item = knowledge_fixture()[0]
        first = self.kb.stage_many([item], "TEST", KNOWN)[0]
        self.assertEqual(self.kb.stage_many([item], "TEST", KNOWN), [first])
        self.kb.approve(first, "TEST", KNOWN)
        item["payload"]["name"] = "new"
        second = self.kb.stage_many([item], "TEST", CUTOFF)[0]
        with self.assertRaises(DataError) as error:
            self.kb.approve(second, "TEST", CUTOFF)
        self.assertEqual(error.exception.code, "KNOWLEDGE_OVERLAP")
        item["supersedes_id"] = first
        third = self.kb.stage_many([item], "TEST", CUTOFF)[0]
        self.kb.approve(third, "TEST", CUTOFF)
        self.assertEqual(self.kb.query("2026-09-15", CUTOFF)[0]["id"], third)
        self.kb.revoke(third, "TEST", REVIEW_AT, "wrong replacement")
        self.assertEqual(self.kb.query("2026-09-15", REVIEW_AT), [])

    def test_half_open_validity_and_future_knowledge(self):
        item = knowledge_item("RULE", "TEST", {"fields": {}}, start="2026-09-01", end="2026-09-15")
        first = self.kb.stage_many([item], "TEST", KNOWN)[0]
        self.kb.approve(first, "TEST", KNOWN)
        self.assertEqual(self.kb.query("2026-09-15", CUTOFF), [])
        item["known_at"] = EXPORT_AT
        with self.assertRaises(DataError):
            self.kb.stage_many([item], "TEST", CUTOFF)

    def test_excel_pending_roundtrip_never_autoapproves_and_keeps_zeroes(self):
        self.kb.stage_many(knowledge_fixture(), "TEST", KNOWN)
        path = self.root / "knowledge.xlsx"
        self.kb.export_pending(path, "TEST", CUTOFF)
        result = self.kb.import_workbook(path, "TEST", CUTOFF)
        self.assertFalse(result["approved"])
        self.assertEqual(self.kb.query("2026-09-15", CUTOFF), [])
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM knowledge_versions").fetchone()[0], 7)

    def test_conflicting_verified_identifiers_block(self):
        knowledge = knowledge_fixture()
        conflict = copy.deepcopy(knowledge[-2])
        conflict["logical_key"] = "CONFLICT"
        conflict["payload"]["counterparty"] = "0002"
        knowledge.append(conflict)
        _, proposals, _ = self.open_propose(knowledge=knowledge)
        self.assertIn("IDENTIFIER_CONFLICT", proposals[0]["constraints"])
        self.assertEqual(proposals[0]["completeness"], "NONE")

    def test_historical_links_do_not_make_labels(self):
        batch, _, _ = self.exported()
        self.post(batch)
        self.store.conn.execute("DELETE FROM label_events")
        self.store.conn.execute("DELETE FROM labels")
        report = self.kb.link_history(VERIFY_AT)
        self.assertTrue(report)
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0], 0)


class ProposalTests(FeatureCase):
    def test_many_payments_one_invoice_reserves_and_propose_idempotent(self):
        session, proposals, _ = self.open_propose()
        self.assertTrue(all(p["completeness"] == "FULL" for p in proposals), proposals)
        self.assertEqual(self.store.conn.execute("SELECT SUM(amount_minor) FROM allocations").fetchone()[0], 200)
        self.assertEqual([p["id"] for p in self.sessions.propose(session["id"])], [p["id"] for p in proposals])
        self.assertEqual(len(proposals[0]["stages"]), 5)

    def test_overpayment_remains_partial_and_cannot_be_approved(self):
        session, proposals, _ = self.open_propose(bundle=bundle_fixture(-150))
        self.assertEqual(proposals[1]["unallocated_minor"], 50)
        with self.assertRaises(DataError):
            self.approve(session)
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)
        self.assertEqual(self.store.conn.execute("SELECT SUM(amount_minor) FROM allocations WHERE state='RESERVED'").fetchone()[0], 150)

    def test_tied_invoices_not_chosen_arbitrarily(self):
        bundle = bundle_fixture(-100)
        extra = copy.deepcopy(bundle["records"][0]); extra.update(item_id="ANOTHER", invoice_reference="HD_2")
        bundle["records"].append(extra)
        bundle = envelope("junsky_xuat", bundle["records"])
        banks = bank_fixture(); [b.update(invoice_references=[]) for b in banks["records"]]
        _, proposals, _ = self.open_propose(banks=banks, bundle=bundle)
        self.assertEqual(proposals[0]["allocations"], [])
        self.assertEqual(proposals[0]["completeness"], "PARTIAL")

    def test_one_payment_multiple_explicit_invoices(self):
        bundle = bundle_fixture(-60)
        extra = copy.deepcopy(bundle["records"][0]); extra.update(amount="-40", item_id="ANOTHER", invoice_reference="HD_2")
        bundle["records"].append(extra)
        bundle = envelope("junsky_xuat", bundle["records"])
        banks = bank_fixture(1); banks["records"][0]["invoice_references"].append("HD_2")
        _, proposals, _ = self.open_propose(1, banks=banks, bundle=bundle)
        self.assertEqual(sorted(a["amount_minor"] for a in proposals[0]["allocations"]), [40, 60])

    def test_active_session_and_mode_are_isolated(self):
        session, _, bank_ids = self.open_propose()
        with self.assertRaises(DataError):
            self.sessions.open(session["source_attempt_id"], bank_ids, CUTOFF, "TEST")
        self.sessions.cancel(session["id"], "TEST", REVIEW_AT, "test")
        with self.assertRaises(DataError) as error:
            self.sessions.open(session["source_attempt_id"], bank_ids, REVIEW_AT, "TEST", "backtest")
        self.assertEqual(error.exception.code, "MODE_ISOLATION")

    def test_locked_period_and_already_posted_block(self):
        bundle = bundle_fixture()
        next(r for r in bundle["records"] if r["kind"] == "LOCK_PERIOD").update(valid_to="2026-10-01")
        session, proposals, _ = self.open_propose(bundle=bundle)
        self.assertIn("LOCKED_PERIOD", proposals[0]["constraints"])
        with self.assertRaises(DataError):
            self.approve(session)

    def test_stale_snapshot_new_catalog_and_knowledge_change_block(self):
        session, _, _ = self.open_propose()
        changed = self.ingest(bundle_fixture(snapshot="NEW", exported="2026-09-16T01:10:00Z"))
        with self.assertRaises(DataError) as error:
            self.review.review_workbook(session["id"], "TEST", REVIEW_AT)
        self.assertEqual(error.exception.code, "SESSION_INPUT_CHANGED")


class ReviewTests(FeatureCase):
    def test_review_is_idempotent_and_export_is_not_posted_or_learned(self):
        session, _, _ = self.open_propose()
        path, result = self.approve(session)
        self.assertEqual(result["applied"], 2)
        self.assertTrue(self.review.import_review(path, "TEST", REVIEW_AT)["replayed"])
        batch = self.review.export(session["id"], "TEST", EXPORT_AT)
        self.assertEqual(batch["state"], "EXPORTED")
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0], 0)
        self.assertEqual(self.review.export(session["id"], "TEST", EXPORT_AT)["batch_id"], batch["batch_id"])
        wb = excel.load(Path(batch["path"]).read_bytes())
        self.assertNotIn("CB_tmpEntry1", wb.sheetnames)
        self.assertEqual(wb["FIXTURE_HEADER"].cell(2, 4).value, "0001")
        wb.close()

    def test_excel_tampering_formula_wrong_code_all_rejected_atomically(self):
        session, _, _ = self.open_propose()
        review = self.review.review_workbook(session["id"], "TEST", REVIEW_AT)
        source = approved_review(review["path"], self.root / "approve.xlsx")
        edits = [lambda w: w["DUYET"].cell(2, 1, "FAKE"), lambda w: w["DUYET"].cell(2, 7, "-999"),
                 lambda w: w["DUYET"].cell(2, 12, '=HYPERLINK("http://x")'), lambda w: w["DUYET"].cell(2, 12, "INVALID"),
                 lambda w: w["DUYET"].cell(2, 9, 1), lambda w: w["DUYET"].delete_rows(2)]
        for action in edits:
            with self.subTest(action=action), self.assertRaises(DataError):
                self.review.import_review(self.edit(source, action), "TEST", REVIEW_AT)
            self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)

    def test_stale_workbook_cannot_overwrite_new_decision(self):
        session, _, _ = self.open_propose()
        stale = self.review.review_workbook(session["id"], "TEST", REVIEW_AT)
        self.approve(session)
        path = approved_review(stale["path"], self.root / "stale.xlsx")
        with self.assertRaises(DataError) as error:
            self.review.import_review(path, "TEST", REVIEW_AT)
        self.assertEqual(error.exception.code, "STALE_WORKBOOK")

    def test_reorder_rows_is_safe(self):
        session, _, _ = self.open_propose()
        wb = self.review.review_workbook(session["id"], "TEST", REVIEW_AT)
        source = approved_review(wb["path"], self.root / "approve.xlsx")
        def reorder(w):
            sheet = w["DUYET"]
            a, b = [c.value for c in sheet[2]], [c.value for c in sheet[3]]
            for col, (av, bv) in enumerate(zip(a, b), 1):
                sheet.cell(2, col, bv); sheet.cell(3, col, av)
        self.assertEqual(self.review.import_review(self.edit(source, reorder), "TEST", REVIEW_AT)["applied"], 2)

    def test_crash_after_prepare_can_recover_exact_same_batch(self):
        session, _, _ = self.open_propose()
        self.approve(session)
        with patch.object(self.review, "_publish", side_effect=OSError("simulated power loss")), self.assertRaises(OSError):
            self.review.export(session["id"], "TEST", EXPORT_AT)
        batch = self.store.conn.execute("SELECT * FROM export_batches").fetchone()
        self.assertEqual(batch["state"], "PREPARING")
        self.assertEqual(self.sessions.get(session["id"])["state"], "PREPARING")
        restored = self.review.recover(batch["id"], "TEST", EXPORT_AT)
        self.assertEqual(restored["state"], "EXPORTED")
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM export_batches").fetchone()[0], 1)

    def test_real_junsky_export_is_blocked(self):
        with self.assertRaises(DataError) as error:
            self.review.export("none", "TEST", EXPORT_AT, "junsky")
        self.assertEqual(error.exception.code, "JUNSKY_MAPPING_MISSING")


class LearningTests(FeatureCase):
    def test_verified_postings_make_labels_and_replay_is_idempotent(self):
        batch, _, _ = self.exported()
        attempt, report = self.post(batch)
        self.assertTrue(report["complete"], report)
        self.assertEqual(len(report["label_ids"]), 2)
        self.assertTrue(self.recon.reconcile(batch["batch_id"], attempt, "TEST", VERIFY_AT)["replayed"])
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0], 2)

    def test_balance_zero_without_journal_never_proves_posting(self):
        batch, _, _ = self.exported()
        _, report = self.post(batch, journals=[journal_fixture()])
        self.assertTrue(all(i["status"] == "RECON_A" for i in report["items"]))
        self.assertEqual(report["label_ids"], [])

    def test_wrong_invoice_same_amount_does_not_learn(self):
        batch, _, _ = self.exported()
        journals = postings_for_batch(self.store, batch["batch_id"])
        for j in journals:
            j["invoice_allocations"][0]["invoice_reference"] = "WRONG_INVOICE"
        _, report = self.post(batch, journals=journals)
        self.assertTrue(all(i["status"] == "RECON_C" for i in report["items"]))
        self.assertEqual(report["label_ids"], [])

    def test_partial_import_only_verified_item_is_labeled(self):
        batch, _, _ = self.exported()
        journals = postings_for_batch(self.store, batch["batch_id"])[:1]
        _, report = self.post(batch, balance=-100, journals=journals)
        self.assertFalse(report["complete"])
        self.assertEqual(report["label_ids"], [])  # shared invoice balance still disputed
        self.assertIn("RECON_A", [i["status"] for i in report["items"]])

    def test_wrong_project_or_ledger_amount_prevents_label(self):
        batch, _, _ = self.exported()
        journals = postings_for_batch(self.store, batch["batch_id"])
        for j in journals:
            j["project"] = "WRONG"
        _, report = self.post(batch, journals=journals)
        self.assertFalse(report["complete"])
        self.assertEqual(report["label_ids"], [])
        self.assertTrue(all(not i["verified_fields"]["project"] for i in report["items"]))

    def test_labels_not_visible_before_verification_and_revoke_rebuilds(self):
        batch, _, _ = self.exported()
        _, report = self.post(batch)
        label = self.store.conn.execute("SELECT * FROM labels LIMIT 1").fetchone()
        context = json.loads(label["context_json"])
        self.assertEqual(self.learning.eligible(context, CUTOFF, "2026-09-16"), [])
        self.assertEqual(len(self.learning.eligible(context, VERIFY_AT, "2026-09-16")), 2)
        settings = {"min_count": 1, "min_share": "0.75"}
        first = self.learning.rebuild(context, VERIFY_AT, "2026-09-16", settings)
        self.assertEqual(self.learning.rebuild(context, VERIFY_AT, "2026-09-16", settings)["id"], first["id"])
        self.learning.revoke(label["id"], "TEST", "2026-09-16T05:00:00Z", "test")
        self.assertEqual(len(self.learning.eligible(context, VERIFY_AT, "2026-09-16")), 2)
        self.assertEqual(len(self.learning.eligible(context, "2026-09-16T05:00:00Z", "2026-09-16")), 1)
        self.assertEqual(self.learning.suggest({**context, "partition": "OTHER"}, VERIFY_AT, "2026-09-16", settings), {})

    def test_two_sessions_use_fresh_snapshot_without_double_counting(self):
        batch, first, banks = self.exported(1)
        attempt, report = self.post(batch, balance=-100)
        self.assertTrue(report["complete"], report)
        with self.assertRaises(DataError):
            self.sessions.open(first["source_attempt_id"], [banks[1]], VERIFY_AT, "TEST")
        second = self.sessions.open(attempt, [banks[1]], VERIFY_AT, "TEST")
        proposal = self.sessions.propose(second["id"])[0]
        self.assertEqual(proposal["completeness"], "FULL", proposal)
        self.assertEqual(proposal["allocations"][0]["amount_minor"], 100)
        self.approve(second, "2026-09-16T04:30:00Z")
        batch2 = self.review.export(second["id"], "TEST", "2026-09-16T05:00:00Z")
        journals = postings_for_batch(self.store, batch["batch_id"]) + postings_for_batch(self.store, batch2["batch_id"])
        attempt2 = self.ingest(bundle_fixture(0, snapshot="FINAL", exported="2026-09-16T06:00:00Z", journals=journals))
        report2 = self.recon.reconcile(batch2["batch_id"], attempt2, "TEST", "2026-09-16T07:00:00Z")
        self.assertTrue(report2["complete"], report2)

    def test_unverified_candidate_cannot_be_autoapproved(self):
        item = knowledge_item("RULE", "LEARNED", {"keywords": ["thanh toan"], "fields": {"project": "0001"}})
        identifier = self.learning.propose_rule(item, "TEST", KNOWN)[0]
        with self.assertRaises(DataError) as error:
            self.kb.approve(identifier, "TEST", KNOWN)
        self.assertEqual(error.exception.code, "CANDIDATE_NOT_EVALUATED")


class QualityTests(FeatureCase):
    def test_frozen_dataset_AB_blind_no_suggestions_and_no_real_go(self):
        attempt, bank_ids, _ = self.seed()
        dataset = self.dataset(attempt, bank_ids)
        report = self.quality.evaluate(dataset, "TEST", CUTOFF)
        self.assertEqual(report["splits"]["BLIND"]["A"]["all_fields"]["accuracy"], "1")
        self.assertEqual(report["splits"]["BLIND"]["A"], report["splits"]["BLIND"]["B"])
        self.assertEqual(report["real_operation_gate"], "NO_GO_REAL_DATA")
        self.assertEqual(self.quality.evaluate(dataset, "TEST", CUTOFF)["run_id"], report["run_id"])
        path = self.root / "blind.xlsx"
        self.quality.blind_workbook(dataset, path, "TEST", CUTOFF)
        wb = excel.load(path.read_bytes())
        self.assertTrue(all(wb["DANH_GIA_MU"].cell(2, col).value is None for col in range(7, 15)))
        wb.close()

    def test_changed_dataset_same_version_and_split_group_leak_rejected(self):
        attempt, bank_ids, _ = self.seed()
        self.dataset(attempt, bank_ids)
        path = self.root / "dataset.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["records"][0]["truth"]["fields"]["project"] = "0002"
        with self.assertRaises(DataError) as error:
            self.quality.register(write_json(path, value))
        self.assertEqual(error.exception.code, "DATASET_FROZEN")
        value["version"] = "2"; value["records"][0]["split"] = "DEV"
        with self.assertRaises(DataError) as error:
            self.quality.register(write_json(path, value))
        self.assertEqual(error.exception.code, "GROUP_LEAKAGE")

    def test_amount_weighted_error_counts_each_bank_once_and_unknown_excluded(self):
        predictions = [{"completeness": "FULL", "fields": dict(FIELD_VALUES), "allocations": [], "amount_minor": -100, "direction": "OUT"},
                       {"completeness": "NONE", "fields": {}, "allocations": [], "amount_minor": 900, "direction": "IN"}]
        records = [{"truth": {"fields": {"project": "WRONG", "expense": "WRONG"}}}, {"truth": {}}]
        report = score(predictions, records)
        self.assertEqual(report["amount"]["wrong_minor"], 100)
        self.assertEqual(report["amount"]["assessed_minor"], 100)
        self.assertEqual(report["unknown_truth_count"], 2)
        self.assertIsNone(report["all_fields"]["accuracy"])

    def test_reconstruction_refuses_future_anchor_and_skips_future_known_movement(self):
        anchors = [{"id": "OPEN", "as_of": "2026-09-01", "known_at": KNOWN, "balances": {"I": -200}},
                   {"id": "FUTURE", "as_of": "2026-09-30", "known_at": KNOWN, "balances": {"I": 0}}]
        movement = {"id": "POST", "business_date": "2026-09-15", "known_at": EXPORT_AT, "item_key": "I", "delta_minor": 100}
        report = reconstruct_open_items(anchors, [movement], "2026-09-16", CUTOFF)
        self.assertEqual(report["balances"]["I"], -200)
        self.assertFalse(report["complete"])
        self.assertEqual(reconstruct_open_items(anchors, [movement, movement], "2026-09-16", VERIFY_AT)["balances"]["I"], -100)
        with self.assertRaises(DataError):
            reconstruct_open_items(anchors[1:], [], "2026-09-16", CUTOFF)

    def test_month_close_requires_final_scope_and_all_banks_reconciled(self):
        batch, _, _ = self.exported()
        attempt, report = self.post(batch)
        with self.assertRaises(DataError):
            self.quality.close_month("2026-09", attempt, "TEST", VERIFY_AT)
        journals = postings_for_batch(self.store, batch["batch_id"])
        final = self.ingest(bundle_fixture(0, snapshot="MONTH_END", exported="2026-10-01T00:00:00Z", as_of="2026-09-30", journals=journals))
        self.recon.reconcile(batch["batch_id"], final, "TEST", "2026-10-01T01:00:00Z")
        closed = self.quality.close_month("2026-09", final, "TEST", "2026-10-01T02:00:00Z")
        self.assertEqual(closed["state"], "CLOSED_FIXTURE")

    def test_full_backup_restore_keeps_labels_workbooks_and_export_identity(self):
        batch, session, _ = self.exported()
        self.post(batch)
        backup = self.root / "backup"
        create_backup(self.store, backup)
        self.assertTrue(verify_backup(backup)["verified"])
        restore_backup(backup, self.root / "restored")
        with Store(Config.load(ROOT / "cau_hinh.toml", self.root / "restored")) as restored:
            self.assertEqual(restored.conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0], 2)
            rebuilt = ReviewExport(restored).recover(batch["batch_id"], "TEST", VERIFY_AT)
            self.assertEqual(Path(rebuilt["path"]).read_bytes(), Path(batch["path"]).read_bytes())


class AdversarialTests(FeatureCase):
    def test_missing_field_or_incomplete_voucher_remains_unresolved(self):
        batch, _, _ = self.exported()
        journals = postings_for_batch(self.store, batch["batch_id"])
        journals[0].pop("project")
        journals[1]["complete_voucher"] = False
        _, result = self.post(batch, journals=journals)
        self.assertTrue(all(item["status"] == "UNRESOLVED" for item in result["items"]))
        self.assertEqual(result["label_ids"], [])

    def test_missing_open_item_is_not_assumed_zero_without_complete_scope(self):
        batch, _, _ = self.exported()
        data = bundle_fixture(0, snapshot="PARTIAL_SCOPE", exported="2026-09-16T03:00:00Z", journals=postings_for_batch(self.store, batch["batch_id"]))
        data["records"][0].update(item_id="UNRELATED", invoice_reference="UNRELATED_INVOICE")
        data["manifest"]["scope_open_items_complete"] = False
        attempt = self.ingest(data)
        result = self.recon.reconcile(batch["batch_id"], attempt, "TEST", VERIFY_AT)
        self.assertIsNone(result["balances"][0]["actual_minor"])
        self.assertTrue(all(item["status"] == "UNRESOLVED" for item in result["items"]))
        self.assertEqual(result["label_ids"], [])

    def test_baseline_B_uses_only_verified_prior_labels_and_never_own_answer(self):
        knowledge = knowledge_fixture()
        knowledge[-1]["payload"]["fields"].pop("project")
        initial, bank_ids, _ = self.seed(knowledge=knowledge)
        bank = document(self.store, bank_ids[0], CUTOFF)
        original = Engine(self.store).preview(bank, source_bundle(self.store, initial, CUTOFF), CUTOFF)
        payload = {"business_date": bank["business_date"], "amount_minor": -100, "fields": dict(FIELD_VALUES), "bank_reference": bank["reference"], "bank_account": bank["account"], "allocations": [{"invoice_reference": "HD_FIXTURE_001", "amount_minor": 100}]}
        posted = self.ingest(bundle_fixture(-100, snapshot="TRAINING", exported="2026-09-16T03:00:00Z", journals=[journal_fixture("HISTORICAL", payload=payload)]))
        journal = self.store.conn.execute("SELECT id FROM documents WHERE kind='JOURNAL' AND core_json LIKE '%HISTORICAL%'").fetchone()[0]
        self.learning.from_journal(bank_ids[0], journal, original["context"], "INDEPENDENT_FIXTURE_CHECKER", VERIFY_AT)
        future = "2026-09-16T05:00:00Z"
        second = document(self.store, bank_ids[1], future)
        bundle = source_bundle(self.store, posted, future)
        engine = Engine(self.store)
        self.assertIsNone(engine.preview(second, bundle, future, "A")["fields"]["project"])
        self.assertEqual(engine.preview(second, bundle, future, "B")["fields"]["project"], "0001")
        self.assertIsNone(engine.preview(second, bundle, future, "B", excluded_label_bank_ids=[bank_ids[0]])["fields"]["project"])
        context = {**original["context"], "policy_version": "NEW_POLICY_VERSION"}
        self.assertEqual(self.learning.suggest(context, future, "2026-09-15", {"min_count": 1, "min_share": "0.75"}), {})
        own_dataset = self.dataset(initial, bank_ids)
        replay = self.quality.evaluate(own_dataset, "TEST", future)
        self.assertEqual(replay["splits"]["BLIND"]["B"]["per_field"]["project"]["correct"], 0)

    def test_rule_impact_requires_approved_gate_holdout_and_later_manual_approval(self):
        knowledge = knowledge_fixture(); knowledge[-1]["payload"]["fields"].pop("project")
        attempt, bank_ids, _ = self.seed(knowledge=knowledge)
        self.dataset(attempt, bank_ids)
        path = self.root / "dataset.json"
        dataset = json.loads(path.read_text(encoding="utf-8")); dataset["version"] = "2"
        for record in dataset["records"]:
            record["split"] = "HOLDOUT"
        dataset_id = self.quality.register(write_json(path, dataset))
        item = knowledge_item("RULE", "RULE_CANDIDATE", {"keywords": ["thanh toan"], "partition": "PLHN_FIXTURE:PAYMENT", "fields": {"project": "0001"}})
        candidate = self.learning.propose_rule(item, "TEST", CUTOFF)[0]
        gate = knowledge_item("STATISTICS", "FIXTURE_GATE", {"kind": "QUALITY_GATE_FIXTURE", "min_assessed": 2, "min_accuracy": "1", "max_wrong_money_share": "0"})
        gate_id = self.kb.stage_many([gate], "TEST", CUTOFF)[0]
        with self.assertRaises(DataError):
            self.quality.evaluate_candidate(candidate, dataset_id, gate_id, "TEST", CUTOFF)
        self.kb.approve(gate_id, "TEST", CUTOFF)
        impact = self.quality.evaluate_candidate(candidate, dataset_id, gate_id, "TEST", CUTOFF)
        self.assertTrue(impact["candidate_gate_passed"], impact)
        self.assertEqual(self.kb.query("2026-09-15", CUTOFF, "RULE"), [])
        self.kb.approve(candidate, "TEST_MANUAL_FIXTURE_APPROVAL", REVIEW_AT)
        self.assertEqual(len(self.kb.query("2026-09-15", REVIEW_AT, "RULE")), 1)

    def test_unbalanced_or_wrong_amount_posting_cannot_confirm_payment(self):
        batch, _, _ = self.exported()
        journals = postings_for_batch(self.store, batch["batch_id"])
        for j in journals:
            j["lines"][0]["debit"] = "99"; j["lines"][1]["credit"] = "99"
        _, result = self.post(batch, journals=journals)
        self.assertFalse(result["complete"])
        self.assertTrue(all(not item["money_verified"] for item in result["items"]))
        self.assertEqual(result["label_ids"], [])

    def test_duplicate_posting_evidence_stays_unresolved(self):
        batch, _, _ = self.exported()
        journals = postings_for_batch(self.store, batch["batch_id"])
        duplicate = copy.deepcopy(journals[0]); duplicate["voucher_number"] = "DUPLICATE"
        journals.append(duplicate)
        _, result = self.post(batch, journals=journals)
        self.assertIn("UNRESOLVED", [item["status"] for item in result["items"]])
        self.assertFalse(result["complete"])

    def test_external_manual_posting_is_candidate_only_and_blocks_month_close(self):
        batch, _, _ = self.exported()
        journals = postings_for_batch(self.store, batch["batch_id"])
        manual = copy.deepcopy(journals[0]); manual.update(voucher_number="MANUAL", bank_reference="OUTSIDE")
        manual.pop("export_item_id"); manual.pop("batch_id")
        journals.append(manual)
        final = self.ingest(bundle_fixture(0, snapshot="END", exported="2026-10-01T00:00:00Z", as_of="2026-09-30", journals=journals))
        result = self.recon.reconcile(batch["batch_id"], final, "TEST", "2026-10-01T01:00:00Z")
        self.assertEqual(result["outside_batch"][0]["status"], "RECON_B")
        self.assertFalse(result["outside_batch"][0]["learning_eligible"])
        with self.assertRaises(DataError) as error:
            self.quality.close_month("2026-09", final, "TEST", "2026-10-01T02:00:00Z")
        self.assertEqual(error.exception.code, "OUTSIDE_BATCH_UNREVIEWED")

    def test_no_unverified_project_guess_and_fee_never_forced_through_payables(self):
        knowledge = knowledge_fixture()
        knowledge[-1]["payload"].update(needs_open_item=False, fields=dict(FIELD_VALUES))
        knowledge[-1]["payload"]["fields"]["debit_account"] = "FEE_FIXTURE"
        knowledge[-1]["payload"]["fields"]["credit_account"] = "112_FIXTURE"
        knowledge.append(knowledge_item("CATALOG", "ACCOUNT:FEE_FIXTURE", {"kind": "ACCOUNT", "code": "FEE_FIXTURE", "name": "Synthetic expense account"}))
        # Synthetic direct template; actual fee accounts remain an accountant decision.
        _, proposals, _ = self.open_propose(knowledge=knowledge)
        self.assertEqual(proposals[0]["allocations"], [])
        self.assertEqual(proposals[0]["unallocated_minor"], 0)

    def test_parallel_session_open_allows_only_one_writer(self):
        attempt, banks, _ = self.seed()
        def enter(_):
            with Store(self.config) as store:
                try:
                    return Sessions(store).open(attempt, banks, CUTOFF, "PARALLEL")["state"]
                except DataError as exc:
                    return exc.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(enter, range(2)))
        self.assertCountEqual(results, ["OPEN", "SESSION_ALREADY_OPEN"])

    def test_process_death_after_prepare_recovers(self):
        session, _, _ = self.open_propose()
        self.approve(session)
        script = """
import os,sys
from pathlib import Path
from kho_tri_thuc.ha_tang.config import Config
from kho_tri_thuc.ha_tang.store import Store
from kho_tri_thuc.xuat.service import ReviewExport
with Store(Config.load(Path(sys.argv[1]),Path(sys.argv[2]))) as s:
    export = ReviewExport(s)
    export._publish = lambda batch: os._exit(17)
    export.export(sys.argv[3], 'PROCESS_DEATH_FIXTURE', '2026-09-16T02:00:00Z')
"""
        result = subprocess.run([sys.executable, "-c", script, str(ROOT / "cau_hinh.toml"), str(self.config.data_dir), session["id"]], env=os.environ.copy(), capture_output=True)
        self.assertEqual(result.returncode, 17, result.stderr)
        batch = self.store.conn.execute("SELECT id FROM export_batches").fetchone()[0]
        self.assertEqual(self.review.recover(batch, "TEST", EXPORT_AT)["state"], "EXPORTED")

    def test_unpublished_prepared_batch_can_cancel_after_source_changes(self):
        session, _, banks = self.open_propose()
        self.approve(session)
        with patch.object(self.review, "_publish", side_effect=OSError("fail")), self.assertRaises(OSError):
            self.review.export(session["id"], "TEST", EXPORT_AT)
        batch = self.store.conn.execute("SELECT id FROM export_batches").fetchone()[0]
        attempt = self.ingest(bundle_fixture(snapshot="CHANGED", exported="2026-09-16T03:00:00Z"))
        with self.assertRaises(DataError):
            self.review.recover(batch, "TEST", VERIFY_AT)
        self.review.cancel_prepared(batch, "TEST", VERIFY_AT, "source changed before publication")
        with self.assertRaises(DataError):
            self.review.recover(batch, "TEST", VERIFY_AT)
        replacement = self.sessions.open(attempt, banks, VERIFY_AT, "TEST")
        self.assertEqual(replacement["state"], "OPEN")

    def test_published_file_is_preserved_when_db_commit_fails_and_source_changes(self):
        session, _, _ = self.open_propose()
        self.approve(session)
        publish = self.review._publish
        def fail_after_publication(batch):
            publish(batch)
            raise OSError("crash after publication before DB commit")
        with patch.object(self.review, "_publish", side_effect=fail_after_publication), self.assertRaises(OSError):
            self.review.export(session["id"], "TEST", EXPORT_AT)
        batch = self.store.conn.execute("SELECT * FROM export_batches").fetchone()
        original = (self.store.root / batch["relative_path"]).read_bytes()
        self.ingest(bundle_fixture(snapshot="CHANGED", exported="2026-09-16T03:00:00Z"))
        with self.assertRaises(DataError):
            self.review.cancel_prepared(batch["id"], "TEST", VERIFY_AT, "cannot drop published identity")
        result = self.review.recover(batch["id"], "TEST", VERIFY_AT)
        self.assertTrue(result["source_changed_after_publication"])
        self.assertEqual(Path(result["path"]).read_bytes(), original)

    def test_local_midnight_cutoff_uses_vietnam_business_date(self):
        data = bundle_fixture(exported="2026-09-16T00:05:00+07:00")
        attempt = self.ingest(data)
        self.assertEqual(source_bundle(self.store, attempt, "2026-09-16T00:10:00+07:00")["manifest"]["as_of"], "2026-09-16")

    def test_knowledge_changes_during_review_require_new_session(self):
        session, _, _ = self.open_propose()
        self.approve(session)
        rule = knowledge_item("RULE", "CHANGED", {"keywords": ["thanh toan"], "fields": {}})
        identifier = self.kb.stage_many([rule], "TEST", REVIEW_AT)[0]
        self.kb.approve(identifier, "TEST", REVIEW_AT)
        with self.assertRaises(DataError) as error:
            self.review.export(session["id"], "TEST", EXPORT_AT)
        self.assertEqual(error.exception.code, "SESSION_INPUT_CHANGED")

    def test_full_cli_demo_and_json_workflow(self):
        from kho_tri_thuc.cli import main
        from contextlib import redirect_stdout
        from io import StringIO
        output = StringIO()
        destination = self.root / "full-demo"
        with redirect_stdout(output):
            status = main(["--config", str(ROOT / "cau_hinh.toml"), "demo-full", str(destination)])
        self.assertEqual(status, 0, output.getvalue())
        report = json.loads(output.getvalue())
        self.assertEqual(report["sessions"], 2)
        self.assertEqual(report["month_close"], "CLOSED_FIXTURE")
        request = write_json(self.root / "query.json", {"business_date": "2026-09-15", "cutoff": CUTOFF})
        with redirect_stdout(StringIO()) as output:
            status = main(["--config", str(ROOT / "cau_hinh.toml"), "--data-dir", str(destination / "data"), "workflow", "knowledge-query", str(request)])
        self.assertEqual(status, 0, output.getvalue())
        self.assertEqual(len(json.loads(output.getvalue())["result"]), 7)


if __name__ == "__main__":
    unittest.main()
