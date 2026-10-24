"""M5 reader thuần #10 gói 01 — test bộ fixture root DEMO (chỉ đọc) + controls đối kháng trong bộ nhớ.

Native/context/history đọc RIÊNG; observer expected chỉ dùng để assert, không truyền vào reader/classifier.
Không DB/network/process/file write; hash input root được kiểm trước/sau.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kho_tri_thuc.ha_tang.primitives import DataError  # noqa: E402
from kho_tri_thuc.nguon.fixture import Issue  # noqa: E402
from kho_tri_thuc.nguon.kho_10 import (  # noqa: E402
    GRAPH_CODES, REQUEST_CODES, FrozenArray, FrozenObject, KhoHistorySummary, KhoIssue, KhoReadContext, KhoReadResult,
    doc_phieu_kho, phan_loai_quan_sat, ra_json,
)
from kho_tri_thuc.nguon.review_xay_dung import chuan_hoa_so  # noqa: E402

FX = ROOT / "tests" / "fixtures" / "kho_10"
MANIFEST_SHA = "5d680a1cd4a691fba5d6eca7056bdc94f9fbf558b80e2415d97f9808215c8e66"
CASES = [f"K{i:02d}" for i in range(1, 11)]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot() -> dict:
    return {str(p.relative_to(FX)): _sha(p) for p in sorted(FX.rglob("*")) if p.is_file()}


BEFORE = _snapshot()


def native(name: str, control: bool = False) -> bytes:
    return (FX / ("controls/native" if control else "native") / f"{name}.json").read_bytes()


def ctx_dict(name: str, control: bool = False) -> dict:
    return json.loads((FX / ("controls/contexts" if control else "contexts") / f"{name}.json").read_text("utf-8"))


def hist_dict(name: str) -> dict:
    return json.loads((FX / "history" / f"{name}.json").read_text("utf-8"))


def ctx(name: str, control: bool = False) -> KhoReadContext:
    return KhoReadContext.tu_dict(ctx_dict(name, control))


def hist(name: str) -> KhoHistorySummary:
    return KhoHistorySummary.tu_dict(hist_dict(name))


EXPECTED = json.loads((FX / "observer" / "expected-fingerprints.json").read_text("utf-8"))["cases"]


def doc(raw: bytes, c: dict | KhoReadContext) -> KhoReadResult:
    return doc_phieu_kho(raw, c if isinstance(c, KhoReadContext) else KhoReadContext.tu_dict(c))


def codes(r: KhoReadResult) -> set:
    return set(r.ma_loi())


def edit_native(raw: bytes, fn) -> bytes:
    v = json.loads(raw.decode("utf-8"))
    fn(v)
    return json.dumps(v, ensure_ascii=False, indent=2).encode("utf-8")


class A_Golden(unittest.TestCase):
    """K01–K10: raw/semantic/request digest + envelope đúng observer độc lập."""

    def test_digests_and_envelopes(self):
        for k in CASES:
            with self.subTest(case=k):
                exp = EXPECTED[k]
                r = doc(native(k), ctx_dict(k))
                self.assertEqual(r.raw_sha256, exp["raw_sha256"])
                self.assertEqual(r.semantic_digest, exp["semantic_digest"])
                self.assertEqual(r.request_digest, exp["request_digest"])
                if exp.get("semantic_envelope") is not None:
                    self.assertEqual(chuan_hoa_so(ra_json(r.semantic_envelope)), exp["semantic_envelope"])
                if exp.get("request_envelope") is not None:
                    self.assertEqual(chuan_hoa_so(ra_json(r.request_envelope)), exp["request_envelope"])
                self.assertEqual(codes(r) & GRAPH_CODES, set(exp.get("graph_issues") or []))
                if exp.get("request_issues") == []:
                    self.assertFalse(codes(r) & REQUEST_CODES)
                self.assertTrue(set(exp.get("measurement_issues") or []) <= codes(r))
                self.assertTrue(r.candidate_only)

    def test_k01_exact_demo(self):
        r = doc(native("K01"), ctx_dict("K01"))
        self.assertEqual(r.business_date, "2026-08-14")
        self.assertEqual([ln.quantity_json_kind for ln in r.lines], ["STRING", "STRING"])
        self.assertEqual([ln.normalized_quantity_text for ln in r.lines], ["8", "2"])
        self.assertEqual({ln.precision_state for ln in r.lines}, {"EXACT_SYNTHETIC_DEMO"})
        self.assertEqual({ln.unit_definition_ref for ln in r.lines}, {"DEMO_UNIT_CAI_A"})
        self.assertEqual(r.lines[0].logical_key, ("DEMO_KHO_A", "NK20260814001", "ID_1786672800001"))
        self.assertFalse(r.issues)

    def test_k02_instance_b_distinct(self):
        a, b = doc(native("K01"), ctx_dict("K01")), doc(native("K02"), ctx_dict("K02"))
        self.assertEqual(a.raw_sha256, b.raw_sha256)
        self.assertNotEqual(a.semantic_digest, b.semantic_digest)
        self.assertNotEqual(a.request_digest, b.request_digest)
        self.assertNotEqual(a.lines[0].logical_key, b.lines[0].logical_key)

    def test_k06_duplicate_no_last_wins(self):
        r = doc(native("K06"), ctx_dict("K06"))
        self.assertIn("KHO_LINE_ID_CONFLICT", codes(r))
        self.assertIsNone(r.semantic_digest)
        self.assertIsNone(r.request_digest)
        self.assertEqual(len(r.lines), 2)
        self.assertNotEqual(r.lines[0].native_values, r.lines[1].native_values)

    def test_k07_partial_not_deletion(self):
        r = doc(native("K07"), ctx_dict("K07"))
        self.assertEqual(len(r.lines), 1)
        self.assertIn("KHO_SOURCE_PARTIAL", codes(r))
        self.assertIsNotNone(r.request_digest)
        c = phan_loai_quan_sat(r, hist("K07"))
        self.assertIn("KHO_SOURCE_PARTIAL", c.reason_codes)
        self.assertTrue(c.needs_review)
        self.assertFalse(any("DELETE" in x or "CANCEL" in x for x in c.reason_codes))

    def test_k08_null_zero_fraction_number(self):
        r = doc(native("K08"), ctx_dict("K08"))
        self.assertEqual([ln.quantity_json_kind for ln in r.lines], ["NULL", "NUMBER", "NUMBER", "NUMBER"])
        self.assertEqual([ln.quantity_text for ln in r.lines], [None, "0", "2.5", "9007199254740992"])
        self.assertEqual([ln.normalized_quantity_text for ln in r.lines], [None] * 4)
        self.assertEqual([ln.precision_state for ln in r.lines], ["UNKNOWN", "UNPROVEN", "UNPROVEN", "UNPROVEN"])
        self.assertIsNone(r.lines[0].native_values.get("SoLuong"))
        self.assertEqual(r.lines[1].native_values.get("SoLuong"), 0)
        self.assertIn("KHO_PRECISION_UNVERIFIED", codes(r))
        self.assertIn("KHO_MEASUREMENT_UNRESOLVED", codes(r))
        self.assertIsNotNone(r.request_digest)

    def test_k09_k10_request_hashable_but_hold(self):
        for k in ("K09", "K10"):
            with self.subTest(case=k):
                r = doc(native(k), ctx_dict(k))
                self.assertIsNotNone(r.request_digest)
                self.assertEqual({ln.normalized_quantity_text for ln in r.lines}, {None})
                self.assertEqual({ln.unit_definition_ref for ln in r.lines}, {None})
                self.assertEqual(r.lines[0].quantity_text, "8")
        self.assertIn("KHO_UOM_UNKNOWN", codes(doc(native("K10"), ctx_dict("K10"))))


class B_Controls(unittest.TestCase):
    """C01–C19 theo observer controls."""

    def cls(self, raw, c, h):
        r = doc(raw, c)
        return r, phan_loai_quan_sat(r, h)

    def test_c01_fresh_receipt_same_content(self):
        r, c = self.cls(native("K03"), ctx_dict("FRESH_RECEIPT", True), hist("K03"))
        self.assertIn("SAME_CONTENT_FRESH_OBSERVATION", c.reason_codes)
        self.assertNotIn("REPLAY", c.reason_codes)
        self.assertEqual(c.history_state, "KNOWN")

    def test_c02_bom(self):
        a, b = doc(native("K01"), ctx_dict("K01")), doc(native("BOM", True), ctx_dict("K01"))
        self.assertNotEqual(a.raw_sha256, b.raw_sha256)
        self.assertEqual(b.raw_sha256, hashlib.sha256(native("BOM", True)).hexdigest())
        self.assertEqual(a.semantic_digest, b.semantic_digest)
        self.assertNotEqual(a.request_digest, b.request_digest)

    def test_c03_reversed(self):
        r, c = self.cls(native("K04"), ctx_dict("K04"), hist("K04"))
        self.assertIn("REVERSED", c.reason_codes)
        self.assertIn("KHO_SOURCE_REVERSED", c.reason_codes)
        self.assertTrue(c.needs_review)
        self.assertEqual(r.source_state, "DA_DAO")

    def test_c04_instance_b(self):
        r, c = self.cls(native("K02"), ctx_dict("K02"), hist("K02"))
        self.assertEqual(c.reason_codes, ("FIRST_OBSERVATION_CANDIDATE",))
        self.assertFalse(c.needs_review)
        self.assertEqual(r.logical_source_identity.source_instance, "DEMO_KHO_B")

    def test_c05_c18_uom_continuity(self):
        r, c = self.cls(native("K09"), ctx_dict("K09"), hist("K09"))
        self.assertIn("KHO_POOL_CONTINUITY_UNPROVEN", c.reason_codes)
        self.assertIn("KHO_CONVERSION_PROOF_MISSING", c.reason_codes)
        self.assertTrue(c.needs_review)
        self.assertEqual({ln.normalized_quantity_text for ln in r.lines}, {None})
        self.assertNotIn("12", {ln.normalized_quantity_text for ln in r.lines})
        self.assertNotIn("96", {ln.normalized_quantity_text for ln in r.lines})

    def test_c06_k08_classified_hold(self):
        _, c = self.cls(native("K08"), ctx_dict("K08"), hist("K08"))
        self.assertIn("FIRST_OBSERVATION_CANDIDATE", c.reason_codes)
        self.assertIn("KHO_PRECISION_UNVERIFIED", c.reason_codes)
        self.assertTrue(c.needs_review)

    def test_c07_replay(self):
        _, c = self.cls(native("K03"), ctx_dict("K03"), hist("K03"))
        self.assertEqual(c.reason_codes, ("REPLAY",))
        self.assertFalse(c.needs_review)

    def test_c08_reappearance(self):
        _, c = self.cls(native("K05"), ctx_dict("K05"), hist("K05"))
        self.assertIn("REAPPEARANCE_HOLD", c.reason_codes)
        self.assertNotIn("SAME_CONTENT_FRESH_OBSERVATION", c.reason_codes)
        self.assertTrue(c.needs_review)

    def test_c09_history_missing(self):
        _, c = self.cls(native("K01"), ctx_dict("K01"), None)
        self.assertEqual(c.history_state, "MISSING")
        self.assertIn("HISTORY_UNAVAILABLE", c.reason_codes)
        self.assertTrue(c.needs_review)
        _, e = self.cls(native("K01"), ctx_dict("K01"), hist("K01"))
        self.assertEqual((e.history_state, e.reason_codes), ("KNOWN", ("FIRST_OBSERVATION_CANDIDATE",)))

    def test_c10_history_mismatch(self):
        _, c = self.cls(native("K01"), ctx_dict("K01"), hist("K02"))
        self.assertEqual(c.history_state, "UNKNOWN")
        self.assertIn("HISTORY_MISMATCH", c.reason_codes)
        self.assertTrue(c.needs_review)

    def test_c11_to_c15_native_rejects(self):
        for name, code in (("WRAPPER", "KHO_SHAPE"), ("DUPLICATE_KEY", "DUPLICATE_JSON_KEY"), ("NONFINITE", "INVALID_JSON"),
                           ("ORPHAN", "KHO_ORPHAN_LINE"), ("INVALID_DATE", "INVALID_DATE")):
            with self.subTest(control=name):
                raw = native(name, True)
                r, c = self.cls(raw, ctx_dict("K01"), hist("K01"))
                self.assertIn(code, codes(r))
                self.assertIsNone(r.semantic_digest)
                self.assertIsNone(r.request_digest)
                self.assertEqual(r.raw_sha256, hashlib.sha256(raw).hexdigest())
                self.assertTrue(c.needs_review)
        r = doc(native("ORPHAN", True), ctx_dict("K01"))
        self.assertEqual(len(r.lines), 2)
        r = doc(native("INVALID_DATE", True), ctx_dict("K01"))
        self.assertIsNone(r.business_date)
        self.assertEqual(r.native_header.get("NgayChungTu"), "2026-02-30")

    def test_c16_mapping_mismatch(self):
        r = doc(native("K01"), ctx_dict("MAPPING_MISMATCH", True))
        self.assertIn("KHO_CONTEXT_SCOPE_MISMATCH", codes(r))
        self.assertEqual(r.semantic_digest, EXPECTED["K01"]["semantic_digest"])
        self.assertIsNone(r.request_digest)

    def test_c17_unknown_uom_no_default(self):
        r, c = self.cls(native("K10"), ctx_dict("K10"), hist("K10"))
        self.assertIn("KHO_UOM_UNKNOWN", c.reason_codes)
        self.assertEqual({(ln.normalized_quantity_text, ln.unit_definition_ref) for ln in r.lines}, {(None, None)})
        self.assertIsNone(r.measurement_refs.ratio_numerator_text)
        self.assertTrue(c.needs_review)

    def test_c19_inputs_unchanged(self):
        paths = [FX / "native/K05.json", FX / "contexts/K05.json", FX / "history/K05.json"]
        before = [_sha(p) for p in paths]
        raw, cd, hd = native("K05"), ctx_dict("K05"), hist_dict("K05")
        cd0, hd0 = copy.deepcopy(cd), copy.deepcopy(hd)
        phan_loai_quan_sat(doc(raw, cd), KhoHistorySummary.tu_dict(hd))
        self.assertEqual((cd, hd), (cd0, hd0))
        self.assertEqual(raw, native("K05"))
        self.assertEqual(before, [_sha(p) for p in paths])


class C_Adversarial(unittest.TestCase):
    def setUp(self):
        self.raw = native("K01")
        self.base = doc(self.raw, ctx_dict("K01"))

    def test_missing_null_refs_keep_candidate(self):
        for key in ("mapping_revision", "profile_ref", "scope", "scope_ref"):
            with self.subTest(missing=key):
                d = ctx_dict("K01")
                d[key] = None
                r = doc(self.raw, d)
                self.assertEqual(r.semantic_digest, self.base.semantic_digest)
                self.assertIsNone(r.request_digest)
                self.assertIn("KHO_CONTEXT_UNRESOLVED", codes(r))
                self.assertEqual(len(r.lines), 2)
        d = ctx_dict("K01")
        del d["mapping_revision"]["phap_nhan"]
        r = doc(self.raw, d)
        self.assertIsNone(r.request_digest)
        self.assertIsNotNone(r.semantic_digest)
        for key in ("master_snapshot", "logical_source_identity"):
            with self.subTest(graph_missing=key):
                d = ctx_dict("K01")
                d[key] = None
                r = doc(self.raw, d)
                self.assertIsNone(r.semantic_digest)
                self.assertIsNone(r.request_digest)
                self.assertEqual(len(r.lines), 2)

    def test_constructor_rejects_malformed_container(self):
        bad = [lambda d: d.update(extra=1), lambda d: d.update(scope=[]), lambda d: d.update(request_digest="0" * 64),
               lambda d: d["mapping_revision"].update(version="1"), lambda d: d["master_snapshot"].update(raw_subtree_sha256="ABC")]
        for i, fn in enumerate(bad):
            with self.subTest(i=i):
                d = ctx_dict("K01")
                fn(d)
                with self.assertRaises(DataError):
                    KhoReadContext.tu_dict(d)
        with self.assertRaises(DataError):
            KhoReadContext.tu_dict([])
        h = hist_dict("K01")
        del h["receipts_seen"]
        with self.assertRaises(DataError):
            KhoHistorySummary.tu_dict(h)
        with self.assertRaises(DataError):
            doc_phieu_kho("text", ctx("K01"))

    def test_malformed_quantity_kept(self):
        for val, cls_ in ((True, bool), ({}, FrozenObject), ([], FrozenArray)):
            with self.subTest(val=val):
                raw = edit_native(self.raw, lambda v: v["lines"][0].__setitem__("SoLuong", val))
                r = doc(raw, ctx_dict("K01"))
                q = r.lines[0].native_values.get("SoLuong")
                self.assertIsInstance(q, cls_)
                self.assertEqual(r.lines[0].quantity_json_kind, "INVALID")
                self.assertIn("KHO_FIELD_TYPE", codes(r))
                self.assertIsNone(r.semantic_digest)
        a = doc(edit_native(self.raw, lambda v: v["lines"][0].__setitem__("SoLuong", {})), ctx_dict("K01"))
        b = doc(edit_native(self.raw, lambda v: v["lines"][0].__setitem__("SoLuong", [])), ctx_dict("K01"))
        self.assertNotEqual(a.lines[0].native_values, b.lines[0].native_values)

    def test_date_missing_invalid(self):
        for val, code in ((None, "KHO_DATE_MISSING"), ("", "KHO_DATE_MISSING"), ("14/08/2026", "INVALID_DATE")):
            with self.subTest(val=val):
                r = doc(edit_native(self.raw, lambda v: v["phieu"].__setitem__("NgayChungTu", val)), ctx_dict("K01"))
                self.assertIn(code, codes(r))
                self.assertIsNone(r.business_date)
                self.assertIsNone(r.semantic_digest)
        r = doc(edit_native(self.raw, lambda v: v["phieu"].pop("NgayChungTu")), ctx_dict("K01"))
        self.assertIn("KHO_DATE_MISSING", codes(r))

    def test_duplicate_master_even_identical(self):
        d = ctx_dict("K01")
        d["master_snapshot"]["whitelist_rows"]["DM_HangHoa"].append(dict(d["master_snapshot"]["whitelist_rows"]["DM_HangHoa"][0]))
        r = doc(self.raw, d)
        self.assertIn("KHO_MASTER_GRAPH_CONFLICT", codes(r))
        self.assertIsNone(r.semantic_digest)
        d = ctx_dict("K01")
        d["master_snapshot"]["whitelist_rows"]["DM_Kho"] = []
        self.assertIn("KHO_MASTER_MISSING", codes(doc(self.raw, d)))

    def test_master_order_and_unreferenced_rows_do_not_change_semantic(self):
        d = ctx_dict("K01")
        rows = d["master_snapshot"]["whitelist_rows"]
        rows["DM_HangHoa"].reverse()
        rows["DM_HangHoa"].append({"MaHang": "HH_KHAC", "DVT_Goc": "KG", "DVT_QuyDoi": None})
        rows["DM_HangHoa"].append({"MaHang": "HH_KHAC", "DVT_Goc": "KG", "DVT_QuyDoi": None})
        r = doc(self.raw, d)
        self.assertEqual(r.semantic_digest, self.base.semantic_digest)
        self.assertEqual(r.request_digest, self.base.request_digest)

    def test_whitespace_raw_diff_semantic_equal(self):
        raw = json.dumps(json.loads(self.raw.decode("utf-8")), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        r = doc(raw, ctx_dict("K01"))
        self.assertNotEqual(r.raw_sha256, self.base.raw_sha256)
        self.assertEqual(r.semantic_digest, self.base.semantic_digest)
        self.assertNotEqual(r.request_digest, self.base.request_digest)

    def test_business_changes_change_semantic(self):
        edits = [lambda v: v["lines"].reverse(), lambda v: v["phieu"].__setitem__("TrangThai", "Nháp"),
                 lambda v: v["lines"][0].__setitem__("SoLuong", "9"), lambda v: v["lines"][0].__setitem__("GhiChu", "khac")]
        for i, fn in enumerate(edits):
            with self.subTest(i=i):
                self.assertNotEqual(doc(edit_native(self.raw, fn), ctx_dict("K01")).semantic_digest, self.base.semantic_digest)

    def test_receipt_and_fetch_metadata_do_not_change_digests(self):
        d = ctx_dict("K01")
        d["receipt_id"] = "urn:demo:m5:receipt:khac"
        d["capture_ref"] = "urn:demo:m5:capture:khac"
        d["server_known_at"] = "2026-10-19T00:00:00Z"
        r = doc(self.raw, d)
        self.assertEqual((r.semantic_digest, r.request_digest), (self.base.semantic_digest, self.base.request_digest))

    def test_mapping_or_proof_change_changes_request_only(self):
        changes = [lambda d: d["mapping_revision"].update(phap_nhan="DEMO_PN_X"), lambda d: d["mapping_revision"].update(version=2),
                   lambda d: d["quantity_evidence"].update(approved_conversion_proof_ref="urn:demo:proof:x")]
        seen = {self.base.request_digest}
        for i, fn in enumerate(changes):
            with self.subTest(i=i):
                d = ctx_dict("K01")
                fn(d)
                r = doc(self.raw, d)
                self.assertEqual(r.semantic_digest, self.base.semantic_digest)
                self.assertIsNotNone(r.request_digest)
                self.assertNotIn(r.request_digest, seen)
                seen.add(r.request_digest)

    def test_unknown_optional_measurement_hashable(self):
        d = ctx_dict("K01")
        d["quantity_evidence"] = None
        d["resolved_measurement_facts"] = None
        r = doc(self.raw, d)
        self.assertIsNotNone(r.request_digest)
        self.assertEqual(ra_json(r.request_envelope.get("measurement_refs")), {k: None for k in (
            "profile_ref", "native_encoding_kind", "conversion_kind", "unit_definition_ref", "approved_conversion_proof_ref",
            "prior_unit_definition_ref", "master_revision_ref", "ratio_numerator_text", "ratio_denominator_text")})
        self.assertIn("KHO_MEASUREMENT_UNRESOLVED", codes(r))
        self.assertEqual({ln.normalized_quantity_text for ln in r.lines}, {None})

    def test_resolved_facts_mismatch_hold(self):
        edits = [lambda f: f.update(source_instance="DEMO_KHO_B"), lambda f: f.update(source_profile_ref="urn:khac"),
                 lambda f: f.update(measurement_profile_ref="X"), lambda f: f.update(declared_encoding_kind="JSON_NUMBER_OR_NULL"),
                 lambda f: f["unit_definition"].update(native_unit_code="THUNG"), lambda f: f["unit_definition"].update(reference_id="U2"),
                 lambda f: f["same_unit_ratio_evidence"].update(numerator_text="12"), lambda f: f["quantity_domain"].update(scale=6)]
        for i, fn in enumerate(edits):
            with self.subTest(i=i):
                d = ctx_dict("K01")
                fn(d["resolved_measurement_facts"])
                r = doc(self.raw, d)
                self.assertIn("KHO_CONTEXT_PROOF_MISMATCH", codes(r))
                self.assertIsNone(r.request_digest)
                self.assertEqual(r.semantic_digest, self.base.semantic_digest)
                self.assertEqual({ln.normalized_quantity_text for ln in r.lines}, {None})

    def test_domain_no_rounding(self):
        for q, state in (("1.000000000001", "EXACT_SYNTHETIC_DEMO"), ("1.0000000000001", "OUT_OF_DOMAIN"),
                         ("1" * 27, "OUT_OF_DOMAIN"), ("1" * 26, "EXACT_SYNTHETIC_DEMO"), ("1e3", "UNKNOWN"), (" 8", "UNKNOWN")):
            with self.subTest(q=q):
                r = doc(edit_native(self.raw, lambda v: v["lines"][0].__setitem__("SoLuong", q)), ctx_dict("K01"))
                ln = r.lines[0]
                self.assertEqual(ln.precision_state, state)
                self.assertEqual(ln.normalized_quantity_text, q if state == "EXACT_SYNTHETIC_DEMO" else None)
                self.assertEqual(ln.quantity_text, q)

    def test_number_lexical_tokens(self):
        tokens = ["1e+03", "1000", "1E3", "1.50", "1.5", "-0", "0", "1.0e0"]
        shas = set()
        for t in tokens:
            with self.subTest(token=t):
                raw = self.raw.replace(b'"SoLuong": "8"', b'"SoLuong": ' + t.encode())
                self.assertNotEqual(raw, self.raw)
                r = doc(raw, ctx_dict("K01"))
                self.assertEqual(r.raw_sha256, hashlib.sha256(raw).hexdigest())
                ln = r.lines[0]
                self.assertEqual((ln.quantity_json_kind, ln.quantity_text), ("NUMBER", t))
                self.assertIsNone(ln.normalized_quantity_text)
                self.assertEqual(ln.precision_state, "UNPROVEN")
                self.assertIn("KHO_PRECISION_UNVERIFIED", codes(r))
                shas.add(r.raw_sha256)
        self.assertEqual(len(shas), len(tokens))

    def test_receipt_conflict_and_unbound_history(self):
        d = ctx_dict("K04")
        d["receipt_id"] = ctx_dict("K03")["receipt_id"]
        c =phan_loai_quan_sat(doc(native("K04"), d), hist("K03"))
        self.assertIn("KHO_RECEIPT_CONFLICT", c.reason_codes)
        self.assertNotIn("REPLAY", c.reason_codes)
        self.assertTrue(c.needs_review)
        h = hist_dict("K03")
        h["receipts_seen"][0]["request_digest"] = "NOT_BOUND"
        c = phan_loai_quan_sat(doc(native("K03"), ctx_dict("K03")), KhoHistorySummary.tu_dict(h))
        self.assertIn("HISTORY_UNBOUND", c.reason_codes)
        self.assertEqual(c.history_state, "UNKNOWN")
        self.assertNotIn("REPLAY", c.reason_codes)

    def test_replay_keeps_partial_issue(self):
        h = hist_dict("K01")
        r = doc(native("K07"), ctx_dict("K07"))
        h.update(summary_kind="SYNTHETIC_PRIOR_STATE", seen_content_digests=[r.semantic_digest],
                 receipts_seen=[{"receipt_id": r.receipt_id, "request_digest": r.request_digest, "content_digest": r.semantic_digest,
                                 "content_reference_id": None, "request_reference_id": None, "binding_state": "TEST"}])
        c = phan_loai_quan_sat(r, KhoHistorySummary.tu_dict(h))
        self.assertIn("REPLAY", c.reason_codes)
        self.assertIn("KHO_SOURCE_PARTIAL", c.reason_codes)
        self.assertTrue(c.needs_review)

    def test_immutability_and_caller_mutation(self):
        d = ctx_dict("K01")
        c = KhoReadContext.tu_dict(d)
        d["mapping_revision"]["phap_nhan"] = "X"
        d["master_snapshot"]["whitelist_rows"]["DM_HangHoa"][0]["DVT_Goc"] = "THUNG"
        d["scope"]["sections"].append("X")
        r = doc(self.raw, c)
        self.assertEqual(r.request_digest, self.base.request_digest)
        buf = bytearray(self.raw)
        r2 = doc_phieu_kho(buf, c)
        buf[:] = b"{}"
        self.assertEqual(r2.semantic_digest, self.base.semantic_digest)
        self.assertEqual(r2.lines[0].native_values.get("SoLuong"), "8")
        for obj, attr in ((r, "request_digest"), (r.lines[0], "quantity_text"), (r.native_header, "entries"), (c.scope, "sections")):
            with self.assertRaises(dataclasses.FrozenInstanceError):
                setattr(obj, attr, None)
        self.assertIsInstance(r.lines, tuple)
        self.assertIsInstance(c.scope.sections, tuple)
        issue = Issue("X", "m")
        k = KhoIssue.tu_issue(issue)
        issue.code = "Y"
        self.assertEqual(k.code, "X")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            k.code = "Z"
        self.assertNotEqual(FrozenObject(()), FrozenArray(()))
        h = hist_dict("K05")
        s = KhoHistorySummary.tu_dict(h)
        h["seen_content_digests"].clear()
        self.assertEqual(len(s.seen_content_digests), 2)

    def test_issue_snapshot_type(self):
        r = doc(native("K08"), ctx_dict("K08"))
        self.assertTrue(r.issues)
        self.assertTrue(all(isinstance(i, KhoIssue) for i in r.issues))
        self.assertTrue(all(isinstance(ln.native_values, FrozenObject) for ln in r.lines))
        self.assertIsInstance(r.lines[2].native_values.get("SoLuong"), Decimal)


class D_Repair02(unittest.TestCase):
    """Sửa 02: sáu nhóm counterexample của review root, mỗi nhóm có positive counterpart. Mutation chỉ trong bộ nhớ."""

    def setUp(self):
        self.raw = native("K01")
        self.base = doc(self.raw, ctx_dict("K01"))

    # R1 — header bắt buộc / status
    def test_r1_status_container_and_missing_required(self):
        cases = {"STATUS_OBJECT": lambda v: v["phieu"].__setitem__("TrangThai", {}),
                 "STATUS_ARRAY": lambda v: v["phieu"].__setitem__("TrangThai", []),
                 "STATUS_NULL": lambda v: v["phieu"].__setitem__("TrangThai", None),
                 "MISSING_LoaiPhieu": lambda v: v["phieu"].pop("LoaiPhieu"),
                 "MISSING_TrangThai": lambda v: v["phieu"].pop("TrangThai"),
                 "LoaiPhieu_EMPTY": lambda v: v["phieu"].__setitem__("LoaiPhieu", "")}
        for name, fn in cases.items():
            with self.subTest(case=name):
                r = doc(edit_native(self.raw, fn), ctx_dict("K01"))
                self.assertIsNone(r.semantic_digest)
                self.assertIsNone(r.request_digest)
                self.assertTrue(codes(r) & {"KHO_SHAPE", "INVALID_TEXT_ID"})
                self.assertEqual(r.source_state, "DA_DUYET" if "LoaiPhieu" in name else None)
                self.assertEqual(len(r.lines), 2)
                self.assertIsNotNone(r.native_header)
                c = phan_loai_quan_sat(r, hist("K01"))
                self.assertTrue(c.needs_review)
                self.assertNotIn("FIRST_OBSERVATION_CANDIDATE", c.reason_codes)
        r = doc(edit_native(self.raw, cases["STATUS_ARRAY"]), ctx_dict("K01"))
        self.assertIsInstance(r.native_header.get("TrangThai"), FrozenArray)
        r = doc(edit_native(self.raw, cases["STATUS_OBJECT"]), ctx_dict("K01"))
        self.assertIsInstance(r.native_header.get("TrangThai"), FrozenObject)

    def test_r1_unmapped_status_hold(self):
        r = doc(edit_native(self.raw, lambda v: v["phieu"].__setitem__("TrangThai", "Đã hủy")), ctx_dict("K01"))
        self.assertEqual(r.native_header.get("TrangThai"), "Đã hủy")
        self.assertEqual(r.source_state, "CHUA_MAP")
        self.assertIsNotNone(r.semantic_digest)
        self.assertNotEqual(r.semantic_digest, self.base.semantic_digest)
        self.assertTrue(any(i.locator == "/phieu/TrangThai" and i.severity == "HOLD" for i in r.issues))
        c = phan_loai_quan_sat(r, hist("K01"))
        self.assertTrue(c.needs_review)
        self.assertNotIn("REVERSED", c.reason_codes)
        # positive: K01 Đã duyệt / K04 Đã đảo giữ nguyên
        self.assertEqual(self.base.source_state, "DA_DUYET")
        self.assertFalse(self.base.issues)
        self.assertEqual(doc(native("K04"), ctx_dict("K04")).source_state, "DA_DAO")

    # R2 — chuỗi số lượng phải là thập phân hữu hạn trước H
    def test_r2_nondecimal_quantity_graph(self):
        for q in ("NaN", "abc", "Infinity", "", " 8", "1,5", "0x10"):
            with self.subTest(q=q):
                r = doc(edit_native(self.raw, lambda v: v["lines"][0].__setitem__("SoLuong", q)), ctx_dict("K01"))
                self.assertIn("KHO_FIELD_TYPE", codes(r))
                self.assertIsNone(r.semantic_digest)
                self.assertIsNone(r.request_digest)
                ln = r.lines[0]
                self.assertEqual((ln.quantity_json_kind, ln.quantity_text, ln.native_values.get("SoLuong")), ("STRING", q, q))
                self.assertIsNone(ln.normalized_quantity_text)
        for q in ("0", "2.5", "-0", "1.50", "1e3", "1E-2"):
            with self.subTest(positive=q):
                r = doc(edit_native(self.raw, lambda v: v["lines"][0].__setitem__("SoLuong", q)), ctx_dict("K01"))
                self.assertIsNotNone(r.semantic_digest)
                self.assertIsNotNone(r.request_digest)
                self.assertEqual(r.lines[0].quantity_text, q)

    # Sửa 03 — dấu cộng đầu: graph hợp lệ, không trim/strip dấu/ép Number; _DEC chuẩn hóa không mở rộng
    def test_r2b_plus_sign_text(self):
        raw = edit_native(self.raw, lambda v: v["lines"][0].__setitem__("SoLuong", "+8"))
        r = doc(raw, ctx_dict("K01"))
        self.assertFalse(codes(r) & GRAPH_CODES)
        self.assertIsNotNone(r.semantic_digest)
        self.assertIsNotNone(r.request_digest)
        self.assertNotEqual(r.semantic_digest, self.base.semantic_digest)
        self.assertEqual(r.raw_sha256, hashlib.sha256(raw).hexdigest())
        ln = r.lines[0]
        self.assertEqual((ln.quantity_json_kind, ln.quantity_text, ln.native_values.get("SoLuong")), ("STRING", "+8", "+8"))
        self.assertNotEqual(ln.normalized_quantity_text, "8")
        self.assertEqual(self.base.semantic_digest, EXPECTED["K01"]["semantic_digest"])
        for q in ("++8", "+", " +8"):
            with self.subTest(q=q):
                r = doc(edit_native(self.raw, lambda v: v["lines"][0].__setitem__("SoLuong", q)), ctx_dict("K01"))
                self.assertIn("KHO_FIELD_TYPE", codes(r))
                self.assertIsNone(r.semantic_digest)
                self.assertIsNone(r.request_digest)
                ln = r.lines[0]
                self.assertEqual((ln.quantity_json_kind, ln.quantity_text, ln.native_values.get("SoLuong")), ("STRING", q, q))
                self.assertIsNone(ln.normalized_quantity_text)

    # R3 — Number thực mâu thuẫn khai báo exact-text
    def test_r3_actual_number_contradicts_exact_text(self):
        raw = self.raw.replace(b'"SoLuong": "8"', b'"SoLuong": 8')
        r = doc(raw, ctx_dict("K01"))
        self.assertIn("KHO_CONTEXT_PROOF_MISMATCH", codes(r))
        self.assertIsNotNone(r.semantic_digest)
        self.assertIsNone(r.request_digest)
        self.assertEqual([ln.normalized_quantity_text for ln in r.lines], [None, None])
        self.assertEqual([ln.unit_definition_ref for ln in r.lines], [None, None])
        self.assertEqual((r.lines[0].quantity_json_kind, r.lines[0].quantity_text), ("NUMBER", "8"))
        self.assertEqual((r.lines[1].quantity_json_kind, r.lines[1].quantity_text), ("STRING", "2"))
        # positive: K01 coherent vẫn chuẩn hóa; K08 facts=None vẫn hash request
        self.assertEqual([ln.normalized_quantity_text for ln in self.base.lines], ["8", "2"])
        k08 = doc(native("K08"), ctx_dict("K08"))
        self.assertEqual(k08.request_digest, EXPECTED["K08"]["request_digest"])
        self.assertNotIn("KHO_CONTEXT_PROOF_MISMATCH", codes(k08))
        self.assertEqual({ln.normalized_quantity_text for ln in k08.lines}, {None})

    # R4 — graph history
    def _k05(self, fn=None) -> KhoHistorySummary:
        h = hist_dict("K05")
        if fn:
            fn(h)
        return KhoHistorySummary.tu_dict(h)

    def test_r4_history_ref_and_digest_graph(self):
        r = doc(native("K05"), ctx_dict("K05"))
        a = EXPECTED["K01"]["semantic_digest"]
        cases = {
            "HISTORY_accepted": (lambda h: h["accepted_source"].update(content_digest=a), "HISTORY_MISMATCH"),
            "HISTORY_receipt": (lambda h: h["receipts_seen"][1].update(content_digest=a), "HISTORY_MISMATCH"),
            "HISTORY_raw_null": (lambda h: h["seen_content_references"][0].update(native_raw_sha256=None), "HISTORY_UNBOUND"),
            "HISTORY_master_null": (lambda h: h["seen_content_references"][1].update(master_raw_subtree_sha256=None), "HISTORY_UNBOUND"),
            "HISTORY_semantic_unbound": (lambda h: h["seen_content_references"][0].update(semantic_digest="NOT_BOUND"), "HISTORY_UNBOUND"),
            "HISTORY_duplicate_ref": (lambda h: h["seen_content_references"][1].update(
                reference_id=h["seen_content_references"][0]["reference_id"]), "HISTORY_MISMATCH"),
            "HISTORY_orphan_ref": (lambda h: h["accepted_source"].update(content_reference_id="urn:demo:m5:content-ref:khong-co"),
                                   "HISTORY_MISMATCH"),
            "HISTORY_ref_logical": (lambda h: h["seen_content_references"][0]["logical_source_identity"].update(source_instance="DEMO_KHO_B"),
                                    "HISTORY_MISMATCH"),
            "HISTORY_duplicate_seen": (lambda h: h["seen_content_digests"].append(a), "HISTORY_MISMATCH"),
        }
        for name, (fn, code) in cases.items():
            with self.subTest(case=name):
                c = phan_loai_quan_sat(r, self._k05(fn))
                self.assertEqual(c.history_state, "UNKNOWN")
                self.assertIn(code, c.reason_codes)
                self.assertTrue(c.needs_review)
                for kl in ("REPLAY", "SAME_CONTENT_FRESH_OBSERVATION", "FIRST_OBSERVATION_CANDIDATE", "REAPPEARANCE_HOLD"):
                    self.assertNotIn(kl, c.reason_codes)

    def test_r4_positive_history_controls(self):
        c = phan_loai_quan_sat(doc(native("K05"), ctx_dict("K05")), hist("K05"))
        self.assertEqual((c.history_state, c.reason_codes), ("KNOWN", ("REAPPEARANCE_HOLD",)))
        c = phan_loai_quan_sat(doc(native("K03"), ctx_dict("K03")), hist("K03"))
        self.assertEqual((c.history_state, c.reason_codes), ("KNOWN", ("REPLAY",)))
        c = phan_loai_quan_sat(doc(native("K04"), ctx_dict("K04")), hist("K04"))
        self.assertEqual(c.history_state, "KNOWN")
        self.assertIn("REVERSED", c.reason_codes)
        c = phan_loai_quan_sat(doc(native("K09"), ctx_dict("K09")), hist("K09"))
        self.assertEqual(c.history_state, "KNOWN")
        self.assertIn("KHO_POOL_CONTINUITY_UNPROVEN", c.reason_codes)

        def bo_ref_tuy_chon(h):  # optional content_reference_id vắng: không tra, không bịa
            for x in h["receipts_seen"]:
                x.pop("content_reference_id")
                x["request_reference_id"] = None
            h["accepted_source"].pop("content_reference_id")
            h["seen_content_references"] = []
        h = hist_dict("K03")
        bo_ref_tuy_chon(h)
        c = phan_loai_quan_sat(doc(native("K03"), ctx_dict("K03")), KhoHistorySummary.tu_dict(h))
        self.assertEqual((c.history_state, c.reason_codes), ("KNOWN", ("REPLAY",)))
        self.assertEqual(phan_loai_quan_sat(self.base, None).history_state, "MISSING")
        self.assertEqual(phan_loai_quan_sat(self.base, hist("K01")).history_state, "KNOWN")

    # R5 — null tường minh của reported_capture_errors
    def test_r5_explicit_null_capture_errors(self):
        d = ctx_dict("K01")
        d["reported_capture_errors"] = None
        with self.assertRaises(DataError) as cm:
            KhoReadContext.tu_dict(d)
        self.assertEqual(cm.exception.code, "KHO_FIELD_TYPE")
        d = ctx_dict("K01")
        self.assertNotIn("reported_capture_errors", d)
        self.assertEqual(KhoReadContext.tu_dict(d).reported_capture_errors, ())
        d["reported_capture_errors"] = []
        self.assertEqual(doc(self.raw, d).request_digest, self.base.request_digest)
        d = ctx_dict("K01")
        d["mapping_revision"] = None  # business ref null vẫn candidate+HOLD, không exception
        self.assertIn("KHO_CONTEXT_UNRESOLVED", codes(doc(self.raw, d)))

    # R6 — Digest fullmatch
    def test_r6_exact_digest(self):
        good = ctx_dict("K01")["source_code_sha256"]
        for bad in (good + "\n", good.upper(), " " + good, good[:-1], good + "0"):
            for path in (("source_code_sha256",), ("master_snapshot", "raw_subtree_sha256")):
                with self.subTest(bad=repr(bad), path=path):
                    d = ctx_dict("K01")
                    tgt = d
                    for p in path[:-1]:
                        tgt = tgt[p]
                    tgt[path[-1]] = bad
                    with self.assertRaises(DataError):
                        KhoReadContext.tu_dict(d)
        self.assertEqual(KhoReadContext.tu_dict(ctx_dict("K01")).source_code_sha256, good)
        h = hist_dict("K03")
        h["receipts_seen"][0]["request_digest"] += "\n"
        c = phan_loai_quan_sat(doc(native("K03"), ctx_dict("K03")), KhoHistorySummary.tu_dict(h))
        self.assertIn("HISTORY_UNBOUND", c.reason_codes)
        self.assertEqual(c.history_state, "UNKNOWN")
        self.assertNotIn("REPLAY", c.reason_codes)
        self.assertEqual(self.base.raw_sha256, EXPECTED["K01"]["raw_sha256"])


class ZZ_InputsUnchanged(unittest.TestCase):
    def test_root_inputs_hash_before_after(self):
        self.assertEqual(_sha(FX / "manifest.json"), MANIFEST_SHA)
        manifest = json.loads((FX / "manifest.json").read_text("utf-8"))
        for f in manifest["files"]:
            self.assertEqual(_sha(FX / f["path"]), f["sha256"], f["path"])
        self.assertEqual(len(BEFORE), 43)
        self.assertEqual(_snapshot(), BEFORE)


if __name__ == "__main__":
    unittest.main()
