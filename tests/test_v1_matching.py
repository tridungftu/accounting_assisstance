from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from test_modules import FeatureCase
from kho_tri_thuc.de_xuat.engine import Engine
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.ha_tang.runtime import document, source_bundle
from kho_tri_thuc.kiem_chung.fixtures import CUTOFF, KNOWN, REVIEW_AT, FIELD_VALUES, knowledge_fixture, knowledge_item
from kho_tri_thuc.tri_thuc.matching import compile_pattern, description_hash, expiry_exclusive, literal_pattern, choose


def policy(key="P", tier=2, order=1, trigger=None, **changes):
    p = {"contract_version": 2, "template_id": key, "partition": "TEST:OUT", "direction": "OUT",
         "tier": tier, "order": order, "trigger": trigger or {"mode": "KEY", "key_type": "BANK_ACCOUNT", "key_value": "00009999"},
         "fields": dict(FIELD_VALUES), "needs_open_item": False, "required_fields": list(FIELD_VALUES)}
    p.update(changes)
    return knowledge_item("POLICY", key, p)


class MatchingTests(FeatureCase):
    def prepare(self, items=None, approve=True):
        attempt, banks, _ = self.seed(knowledge=knowledge_fixture()[:-1])
        ids = self.kb.stage_many(items or [policy()], "TEST", KNOWN)
        if approve:
            for identifier in ids:
                self.kb.approve(identifier, "TEST", KNOWN)
        self.bank = document(self.store, banks[0])
        self.bundle = source_bundle(self.store, attempt, CUTOFF)
        return ids

    def predict(self, bank=None, cutoff=CUTOFF):
        return Engine(self.store).preview(bank or self.bank, self.bundle, cutoff)

    def test_key_uses_exact_text_and_preserves_verified_identity(self):
        self.prepare()
        self.assertEqual(self.predict()["completeness"], "FULL")
        self.assertEqual(self.predict()["confidence"]["counterparty"]["level"], "VERIFIED_IDENTIFIER")
        bank = {**self.bank, "counterparty_account": "9999"}
        self.assertEqual(self.predict(bank)["completeness"], "NONE")

    def test_keyword_and_combined_trigger(self):
        self.prepare([policy(trigger={"mode": "KEY_REGEX", "key_type": "BANK_ACCOUNT", "key_value": "00009999", "regex": r"\bTHANH TOAN\b"})])
        self.assertEqual(self.predict()["completeness"], "FULL")
        self.assertEqual(self.predict({**self.bank, "description": "khác"})["completeness"], "NONE")

    def test_regex_can_fill_accounts_with_identity_from_catalog(self):
        p = policy(tier=5, trigger={"mode": "REGEX", "regex": r"\bTHANH TOAN\b"})
        del p["payload"]["fields"]["counterparty"]
        self.prepare([p])
        self.assertEqual(self.predict()["fields"], FIELD_VALUES)

    def test_counterparty_key_and_tax_key(self):
        for kind, value in (("COUNTERPARTY", "0001"), ("TAX_ID", "0000123")):
            p = policy(kind, trigger={"mode": "KEY", "key_type": kind, "key_value": value}, order=2 if kind == "TAX_ID" else 1)
            if kind == "COUNTERPARTY":
                ids = self.prepare([p])
                self.assertEqual(self.predict()["template_id"], ids[0])
            else:
                self.kb.revoke(ids[0], "TEST", REVIEW_AT, "replace test")
                pid = self.kb.stage_many([p], "TEST", REVIEW_AT)[0]
                self.kb.approve(pid, "TEST", REVIEW_AT)
                result = self.predict({**self.bank, "counterparty_tax_id": value}, REVIEW_AT)
                self.assertEqual(result["template_id"], pid)

    def test_first_match_tier_then_source_order(self):
        ids = self.prepare([policy("later", tier=2, order=1), policy("first", tier=1, order=9), policy("last", tier=1, order=10)])
        self.assertEqual(self.predict()["template_id"], ids[1])

    def test_order_collision_rolls_back_entire_import_even_pending(self):
        with self.assertRaises(DataError) as exc:
            self.kb.stage_many([policy("A"), policy("B")], "TEST", KNOWN)
        self.assertEqual(exc.exception.code, "POLICY_ORDER_COLLISION")
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM knowledge_versions").fetchone()[0], 0)

    def test_nonoverlapping_order_is_allowed_and_idempotent(self):
        first, second = policy("A"), policy("B")
        first["valid_to"] = "2026-09-15"
        second["valid_from"] = "2026-09-15"
        ids = self.kb.stage_many([first, second], "TEST", KNOWN)
        self.assertEqual(self.kb.stage_many([first, second], "TEST", KNOWN), ids)

    def test_runtime_collision_defense(self):
        rows = [{"id": "1", "payload": policy("A")["payload"]}, {"id": "2", "payload": policy("B")["payload"]}]
        self.assertEqual(choose(rows), (None, "POLICY_ORDER_COLLISION"))

    def test_conflicting_partitions_block(self):
        p = policy("B", partition="TEST:OTHER")
        self.prepare([policy("A"), p])
        self.assertIn("POLICY_PARTITION_CONFLICT", self.predict()["constraints"])

    def test_name_is_condition_not_verified_identity(self):
        p = policy(tier=4, trigger={"mode": "KEY", "key_type": "COUNTERPARTY_NAME", "key_value": "DOI TAC"})
        self.prepare([p])
        bank = {**self.bank, "counterparty_account": None, "counterparty_name": "Đối tác"}
        r = self.predict(bank)
        self.assertEqual(r["completeness"], "FULL")
        self.assertEqual(r["confidence"]["counterparty"]["level"], "APPROVED_TEMPLATE")
        self.assertEqual(self.predict()["completeness"], "NONE")

    def test_template_conflict_with_verified_identity_blocks(self):
        p = policy()
        p["payload"]["fields"]["counterparty"] = "OTHER"
        self.prepare([p])
        r = self.predict()
        self.assertEqual(r["completeness"], "NONE")
        self.assertIn("TEMPLATE_IDENTIFIER_CONFLICT", r["constraints"])
        self.assertEqual(r["fields"]["counterparty"], "0001")

    def test_pending_is_not_used_and_known_at_is_not_backdated(self):
        ids = self.prepare(approve=False)
        self.assertEqual(self.predict()["completeness"], "NONE")
        self.kb.approve(ids[0], "TEST", REVIEW_AT)
        self.assertEqual(self.predict()["completeness"], "NONE")
        self.assertEqual(self.predict(cutoff=REVIEW_AT)["completeness"], "FULL")

    def test_expiry_last_day_and_expired_evidence(self):
        p = policy(expiry_raw="2026-09-15")
        p["valid_to"] = expiry_exclusive(p["payload"]["expiry_raw"])
        ids = self.prepare([p])
        self.assertEqual(self.predict()["completeness"], "FULL")
        r = self.predict({**self.bank, "business_date": "2026-09-16"})
        self.assertEqual(r["completeness"], "NONE")
        self.assertEqual(r["matching_evidence"]["expired_policy_ids"], ids)
        self.kb.revoke(ids[0], "TEST", REVIEW_AT, "invalid")
        self.assertEqual(self.predict({**self.bank, "business_date": "2026-09-16"}, REVIEW_AT)["matching_evidence"]["expired_policy_ids"], [])

    def test_expiry_mapping_rejects_off_by_one(self):
        with self.assertRaises(DataError) as exc:
            self.kb.stage_many([policy(expiry_raw="2026-09-15")], "TEST", KNOWN)
        self.assertEqual(exc.exception.code, "EXPIRY_MAPPING")

    def case(self, key="C", kind="BANK_REFERENCE", value=None):
        p = policy()["payload"]
        p.pop("trigger")
        p.update(selector={"type": kind, "value": value or self.bank["reference"], "entity_id": self.store.config.entity_id, "bank_account": self.bank["account"]}, normalization="normalize_text-v1")
        return knowledge_item("CASE", key, p)

    def test_case_wins_before_policy_but_does_not_bypass_data_gate(self):
        self.prepare()
        c = self.case()
        cid = self.kb.stage_many([c], "TEST", KNOWN)[0]
        self.kb.approve(cid, "TEST", KNOWN)
        self.assertEqual(self.predict()["template_id"], cid)
        self.bundle["documents"].append({"kind": "LOCK_PERIOD", "source_status": "LOCKED", "valid_from": "2026-09-01", "valid_to": "2026-10-01"})
        r = self.predict()
        self.assertEqual(r["completeness"], "NONE")
        self.assertIn("LOCKED_PERIOD", r["constraints"])

    def test_two_cases_block_without_choosing_arbitrarily(self):
        self.prepare()
        ids = self.kb.stage_many([self.case("C1"), self.case("C2")], "TEST", KNOWN)
        for cid in ids:
            self.kb.approve(cid, "TEST", KNOWN)
        self.assertIn("CASE_CONFLICT", self.predict()["constraints"])

    def test_case_hash_normalization_scope_and_known_at(self):
        self.prepare()
        c = self.case(kind="DESCRIPTION_HASH", value=description_hash(self.bank["description"]))
        cid = self.kb.stage_many([c], "TEST", REVIEW_AT)[0]
        self.kb.approve(cid, "TEST", REVIEW_AT)
        self.assertNotEqual(self.predict().get("template_id"), cid)
        self.assertEqual(self.predict(cutoff=REVIEW_AT)["template_id"], cid)
        self.assertNotEqual(self.predict({**self.bank, "account": "OTHER"}, REVIEW_AT).get("template_id"), cid)

    def test_case_identifier_conflict_is_blocked(self):
        self.prepare()
        c = self.case()
        c["payload"]["fields"]["counterparty"] = "OTHER"
        cid = self.kb.stage_many([c], "TEST", KNOWN)[0]
        self.kb.approve(cid, "TEST", KNOWN)
        self.assertIn("TEMPLATE_IDENTIFIER_CONFLICT", self.predict()["constraints"])

    def test_regex_five_regressions_and_positive_cases(self):
        patterns = json.loads((Path(__file__).parent / 'fixtures/regex_patterns.json').read_text('utf-8'))
        for keyword, negative in (("UNG HO", "TAM UNG HOP DONG"), ("MUA HOA", "MUA HOA CHAT"), ("DAU", "DAU TU"), ("HOA CHAT", "HOA CHAT NHUA"), ("PHI", "PHIEU")):
            with self.subTest(keyword=keyword):
                regex = compile_pattern(patterns.get(keyword, literal_pattern(keyword)))
                self.assertIsNone(regex.search(negative))
                self.assertIsNotNone(regex.search("ABC " + keyword + " XYZ"))

    def test_invalid_regex_and_multiline_rejected(self):
        for expr in ("[", ".*", "", None):
            with self.subTest(expr=expr), self.assertRaises(DataError):
                self.kb.stage_many([policy(trigger={"mode": "REGEX", "regex": expr})], "TEST", KNOWN)
        p = policy()
        p["payload"]["fields"]["debit_account"] = "1331|6427"
        with self.assertRaises(DataError) as exc:
            self.kb.stage_many([p], "TEST", KNOWN)
        self.assertEqual(exc.exception.code, "MULTILINE_NOT_SUPPORTED")

    def test_conflict_cannot_be_approved_via_manual_fields(self):
        p = policy()
        p["payload"]["fields"]["counterparty"] = "OTHER"
        attempt, bank_ids, _ = self.seed(knowledge=knowledge_fixture()[:-1] + [p])
        session = self.sessions.open(attempt, bank_ids, CUTOFF, "TEST")
        props = self.sessions.propose(session["id"])
        proposal = self.store.conn.execute("SELECT * FROM proposals WHERE id=?", (props[0]["id"],)).fetchone()
        with self.assertRaises(DataError) as exc:
            self.sessions.validate_decision(proposal, dict(FIELD_VALUES), [], REVIEW_AT)
        self.assertEqual(exc.exception.code, "HARD_CONSTRAINT")

    def test_multiline_marker_keeps_source_but_blocks_full(self):
        self.prepare([policy(requires_multiline_review=True)])
        r = self.predict()
        self.assertEqual(r["completeness"], "NONE")
        self.assertIn("MULTILINE_TEMPLATE_REQUIRES_REVIEW", r["constraints"])

    def test_case_voucher_key_and_source_known_time(self):
        self.prepare()
        c = self.case(kind="VOUCHER_NUMBER", value="000007")
        c["known_at"] = REVIEW_AT
        cid = self.kb.stage_many([c], "TEST", REVIEW_AT)[0]
        self.kb.approve(cid, "TEST", REVIEW_AT)
        bank = {**self.bank, "voucher_number": "000007"}
        self.assertNotEqual(self.predict(bank).get("template_id"), cid)
        self.assertEqual(self.predict(bank, REVIEW_AT)["template_id"], cid)

    def test_versioned_legacy_name_normalization_is_not_verified_identity(self):
        p = policy(tier=4, trigger={"mode": "KEY", "key_type": "COUNTERPARTY_NAME", "key_value": "CTY CP DOI TAC VN", "name_normalization": "legacy-chung-v1"})
        self.prepare([p])
        r = self.predict({**self.bank, "counterparty_account": None, "counterparty_name": "Công ty cổ phần Đối Tác Việt Nam"})
        self.assertEqual(r["completeness"], "FULL")
        self.assertEqual(r["confidence"]["counterparty"]["level"], "APPROVED_TEMPLATE")

    def test_name_cannot_be_promoted_to_hard_key_tier(self):
        for tier in (1, 2, 5):
            p = policy(tier=tier, trigger={"mode": "KEY", "key_type": "COUNTERPARTY_NAME", "key_value": "DOI TAC"})
            with self.subTest(tier=tier), self.assertRaises(DataError) as exc:
                self.kb.stage_many([p], "TEST", KNOWN)
            self.assertEqual(exc.exception.code, "NAME_POLICY_TIER")

    def test_malformed_trigger_types_are_validation_errors(self):
        for trigger in ({"mode": []}, {"mode": "KEY", "key_type": [], "key_value": "0001"}):
            with self.subTest(trigger=trigger), self.assertRaises(DataError) as exc:
                self.kb.stage_many([policy(trigger=trigger)], "TEST", KNOWN)
            self.assertEqual(exc.exception.code, "POLICY_TRIGGER")

    def test_empty_keyword_signature_requires_absence_not_wildcard(self):
        p = policy(tier=1, trigger={"mode": "KEY_REGEX", "key_type": "BANK_ACCOUNT", "key_value": "00009999", "regex": r"^(?!.*\b(?:THANH TOAN|PHI)\b).+$"})
        self.prepare([p])
        self.assertEqual(self.predict()["completeness"], "NONE")
        self.assertEqual(self.predict({**self.bank, "description": "giao dich khac"})["completeness"], "FULL")


if __name__ == "__main__":
    unittest.main()
