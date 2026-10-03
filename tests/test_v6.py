"""V6 shadow output has the vendor column contract but no import path."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from openpyxl import load_workbook

from test_modules import FeatureCase
from kho_tri_thuc.kiem_chung.fixtures import CUTOFF, REVIEW_AT, VERIFY_AT, bundle_fixture, journal_fixture
from kho_tri_thuc.xuat.shadow import ENTRY1_HEADERS, ENTRY2_HEADERS, ShadowJunskyExport


class V6ShadowTests(FeatureCase):
    def setUp(self):
        super().setUp()
        self.store.conn.close()
        from kho_tri_thuc.ha_tang.store import Store
        # A synthetic fixture is retained only to exercise the isolation guard;
        # real data is never put in this test or its fixtures.
        self.config = replace(self.config, environment="that", junsky_export_enabled=False, junsky_import_enabled=False)
        self.store = Store(self.config)
        from kho_tri_thuc.tri_thuc.service import Knowledge
        from kho_tri_thuc.trang_thai.service import Sessions
        from kho_tri_thuc.xuat.service import ReviewExport
        self.kb, self.sessions, self.review = Knowledge(self.store), Sessions(self.store), ReviewExport(self.store)

    def test_shadow_has_exact_17_37_columns_is_recoverable_and_not_import_evidence(self):
        attempt, bank_ids, _ = self.seed()
        session = self.sessions.open(attempt, [bank_ids[0]], CUTOFF, "TEST_OPERATOR")
        self.sessions.propose(session["id"])
        self.approve(session)
        service = ShadowJunskyExport(self.store)
        result = service.export(session["id"], "MO_PHONG_TEST", REVIEW_AT,
                                {"bank_id_by_source_account": {"00001234": "BANK_TEST"}, "bank_gl_by_source_account": {"00001234": "112_FIXTURE"}, "branch_id": "02"})
        self.assertFalse(result["fixture_only"])
        self.assertTrue(result["no_junsky_import"])
        self.assertEqual((result["entry1_columns"], result["entry2_columns"]), (17, 37))
        for path in (Path(result["thu"]), Path(result["chi"])):
            wb = load_workbook(path, read_only=True, data_only=False)
            try:
                self.assertEqual(tuple(cell.value for cell in wb["CB_tmpEntry1"][1]), ENTRY1_HEADERS)
                self.assertEqual(tuple(cell.value for cell in wb["CB_tmpEntry2"][1]), ENTRY2_HEADERS)
                self.assertEqual(wb.properties.title, "SHADOW — CHƯA NHẬP JUNSKY")
            finally:
                wb.close()
        comparison = service.compare_structure(Path(result["thu"]), Path(result["thu"]))
        self.assertTrue(comparison["reference_structure_only"])
        self.assertTrue(comparison["not_import_evidence"])
        self.assertEqual(service.recover(result["shadow_id"])["shadow_id"], result["shadow_id"])
        payload = json.loads(self.store.conn.execute("SELECT payload_json FROM decisions WHERE action='APPROVE'").fetchone()[0])
        verification_attempt = self.ingest(bundle_fixture(snapshot="SNAP_SHADOW_POSTED", exported="2026-09-16T03:00:00Z", journals=[journal_fixture("V_SHADOW", payload=payload)]))
        verification = service.reconcile(result["shadow_id"], verification_attempt, "MO_PHONG_TEST", VERIFY_AT)
        self.assertTrue(verification["complete"])
        self.assertTrue(verification["label_ids"])
        self.assertTrue(verification["no_junsky_import"])
