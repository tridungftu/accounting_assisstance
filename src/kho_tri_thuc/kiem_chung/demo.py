"""Reproducible two-session demonstration, strictly within a newly created fixture directory."""
from __future__ import annotations

import json
from pathlib import Path

from ..ha_tang.backup import create_backup, restore_backup, verify_backup
from ..ha_tang.config import Config
from ..ha_tang.primitives import DataError
from ..ha_tang.runtime import run_metadata
from ..ha_tang.store import Store
from ..hoc.service import Learning, Reconciliation
from ..trang_thai.service import Sessions
from ..tri_thuc.service import Knowledge
from ..xuat.service import ReviewExport
from .fixtures import (CUTOFF, EXPORT_AT, FIELD_VALUES, KNOWN, REVIEW_AT, VERIFY_AT, approved_review,
                       bank_fixture, bundle_fixture, knowledge_fixture, postings_for_batch, write_json)
from .service import Quality


def run_demo(config_path, destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise DataError("DESTINATION_EXISTS", "Demo chỉ chạy vào thư mục chưa tồn tại, không ghi đè kết quả cũ.")
    destination.mkdir(parents=True)
    with Store(Config.load(Path(config_path), destination / "data")) as store:
        kb, sessions, review = Knowledge(store), Sessions(store), ReviewExport(store)
        recon, learning, quality = Reconciliation(store), Learning(store), Quality(store)
        steps, journals, batches = [], [], []

        def ingest(name, value):
            report = store.ingest(write_json(destination / "inputs" / name, value))
            write_json(destination / "reports" / name, report)
            if report["state"] != "COMMITTED":
                raise DataError("DEMO_INGEST_FAILED", "Fixture demo không nạp được; xem reports.")
            steps.append({"step": "ingest", "file": name, "attempt_id": report["attempt_id"], "state": report["state"]})
            return report["attempt_id"]

        ingest("01-bank.json", bank_fixture())
        attempt = ingest("02-snapshot.json", bundle_fixture())
        kb_input = knowledge_fixture()
        write_json(destination / "inputs" / "knowledge-stage.json", {"items": kb_input, "actor": "DEMO_FIXTURE_AUTHOR", "at": KNOWN})
        ids = kb.stage_many(kb_input, "DEMO_FIXTURE_AUTHOR", KNOWN)
        kb.export_pending(destination / "TRI_THUC_CHO_DUYET_FIXTURE.xlsx", "DEMO_FIXTURE_AUTHOR", KNOWN)
        for identifier in ids:
            kb.approve(identifier, "AUTOMATED_FIXTURE_APPROVAL", KNOWN)
        steps.append({"step": "knowledge", "approved_fixture_versions": len(ids), "is_real_accountant_approval": False})
        banks = [row[0] for row in store.conn.execute("SELECT id FROM documents WHERE kind='BANK' ORDER BY natural_key")]
        value = {"format": "ktt-evaluation-fixture-v1", "synthetic": True, "id": "DEMO_BANK_PAYMENTS", "version": "1", "records": [
            {"bank_id": bank_id, "source_attempt_id": attempt, "cutoff": CUTOFF, "group_id": "FIXTURE_PAYMENTS", "split": "BLIND",
             "truth": {"fields": dict(FIELD_VALUES), "allocations": [{"invoice_reference": "HD_FIXTURE_001", "amount_minor": 100}],
                       "reviewer": "HAND_DEFINED_FIXTURE_AUTHOR", "evidence": ["Defined fixture: two payments of 100 on one payable of 200"]}} for bank_id in banks]}
        dataset_id = quality.register(write_json(destination / "inputs" / "gold-fixture.json", value))
        ab = quality.evaluate(dataset_id, "DEMO_TEST_RUNNER", CUTOFF)
        write_json(destination / "reports" / "BASELINE_AB.json", ab)
        quality.blind_workbook(dataset_id, destination / "DANH_GIA_MU_FIXTURE.xlsx", "DEMO_TEST_RUNNER", CUTOFF)
        for index, bank_id in enumerate(banks):
            cutoff = CUTOFF if index == 0 else VERIFY_AT
            review_at = REVIEW_AT if index == 0 else "2026-09-16T04:30:00Z"
            export_at = EXPORT_AT if index == 0 else "2026-09-16T05:00:00Z"
            source_at = "2026-09-16T03:00:00Z" if index == 0 else "2026-09-16T06:00:00Z"
            verify_at = VERIFY_AT if index == 0 else "2026-09-16T07:00:00Z"
            session = sessions.open(attempt, [bank_id], cutoff, "DEMO_TEST_RUNNER")
            proposals = sessions.propose(session["id"], "A")
            if proposals[0]["completeness"] != "FULL" or proposals[0]["allocations"][0]["amount_minor"] != 100:
                raise DataError("DEMO_PROPOSAL_FAILED", "Đề xuất khác đáp án fixture đã định nghĩa.")
            write_json(destination / "reports" / f"PROPOSAL_{index + 1}.json", proposals)
            workbook = review.review_workbook(session["id"], "DEMO_TEST_RUNNER", review_at)
            approved = approved_review(workbook["path"], destination / f"DA_DUYET_TU_DONG_FIXTURE_{index + 1}.xlsx")
            decisions = review.import_review(approved, "AUTOMATED_FIXTURE_APPROVAL", review_at)
            batch = review.export(session["id"], "DEMO_TEST_RUNNER", export_at)
            # This is a simulator for integration tests, not independently observed Junsky output.
            journals.extend(postings_for_batch(store, batch["batch_id"]))
            attempt = ingest(f"0{index + 3}-posted-simulation.json", bundle_fixture(-100 if index == 0 else 0, snapshot=f"POSTED_{index + 1}_FIXTURE", exported=source_at, journals=journals))
            report = recon.reconcile(batch["batch_id"], attempt, "AUTOMATED_FIXTURE_VERIFIER", verify_at)
            if not report["complete"]:
                raise DataError("DEMO_RECONCILIATION_FAILED", "Đối soát demo chưa khớp; xem dữ liệu fixture.")
            write_json(destination / "reports" / f"RECON_SESSION_{index + 1}.json", report)
            batches.append(batch)
            steps.append({"step": f"session_{index + 1}", "session_id": session["id"], "batch": batch, "review_decisions": decisions["applied"], "verified": report["complete"], "labels": report["label_ids"]})
        final = ingest("05-month-end-simulation.json", bundle_fixture(0, snapshot="MONTH_END_FIXTURE", exported="2026-10-01T00:00:00Z", as_of="2026-09-30", journals=journals))
        for index, batch in enumerate(batches):
            report = recon.reconcile(batch["batch_id"], final, "AUTOMATED_FIXTURE_VERIFIER", "2026-10-01T01:00:00Z")
            write_json(destination / "reports" / f"RECON_FINAL_{index + 1}.json", report)
            if not report["complete"]:
                raise DataError("DEMO_MONTH_RECONCILIATION_FAILED", "Đối soát cộng dồn cuối tháng chưa khớp.")
        close = quality.close_month("2026-09", final, "AUTOMATED_FIXTURE_CLOSER", "2026-10-01T02:00:00Z")
        write_json(destination / "reports" / "MONTH_CLOSE.json", close)
        context = json.loads(store.conn.execute("SELECT context_json FROM labels LIMIT 1").fetchone()[0])
        statistics = learning.rebuild(context, "2026-10-01T02:00:00Z", "2026-09-30", {"min_count": 1, "min_share": "0.75"})
        write_json(destination / "reports" / "STATISTICS_FIXTURE.json", statistics)
        history = kb.link_history("2026-10-01T02:00:00Z")
        write_json(destination / "reports" / "HISTORY_LINKS.json", history)
        backup = create_backup(store, destination / "backup")
        verify_backup(destination / "backup")
        restore_backup(destination / "backup", destination / "restored")
        with Store(Config.load(Path(config_path), destination / "restored")) as restored:
            for batch in batches:
                rebuilt = ReviewExport(restored).recover(batch["batch_id"], "DEMO_RESTORE_TEST", "2026-10-01T03:00:00Z")
                if Path(rebuilt["path"]).read_bytes() != Path(batch["path"]).read_bytes():
                    raise DataError("DEMO_RESTORE_FAILED", "Batch sau restore không trùng nội dung gốc.")
            restored_labels = restored.conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0]
        summary = {"status": "PASS_FIXTURE", "fixture_only": True, "real_operation_gate": "NO_GO_REAL_DATA", "directory": str(destination),
                   "modules": ["M1", "M2", "M3", "M4", "M5", "M6"], "sessions": 2, "bank_rows": 2, "payment_total_minor": 200,
                   "closing_payable_minor": 0, "label_versions": store.conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0], "restored_label_versions": restored_labels,
                   "month_close": close["state"], "backup_verified": backup["verified"], "baseline_ab_report": str(destination / "reports" / "BASELINE_AB.json"),
                   "verification_source": "SIMULATED_FROM_EXPORT_NOT_REAL_JUNSKY", "real_accountant_approval": False, "manual_testing": "DEFERRED_BY_USER",
                   "provenance": run_metadata(store), "steps": steps}
        write_json(destination / "reports" / "SUMMARY.json", summary)
        return summary
