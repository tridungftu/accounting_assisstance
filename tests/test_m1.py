from __future__ import annotations

import copy
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from kho_tri_thuc.ha_tang.backup import create_backup, restore_backup, verify_backup
from kho_tri_thuc.ha_tang.config import Config
from kho_tri_thuc.ha_tang.database import MIGRATIONS, SCHEMA_VERSION, migrate
from kho_tri_thuc.ha_tang.primitives import (
    DataError, MAX_INT64, MIN_INT64, date_iso, instant_utc, intervals_overlap,
    money_minor, natural_key, normalize_text, valid_interval,
)
from kho_tri_thuc.ha_tang.store import Store
from kho_tri_thuc.nguon.base_inventory import scan_fixture_base
from kho_tri_thuc.nguon.fixture import FixtureAdapter, check_junsky_bundle, read_json

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


class PrimitiveTests(unittest.TestCase):
    def test_money_exact_boundaries_and_sign(self):
        self.assertEqual(money_minor(str(MAX_INT64)), MAX_INT64)
        self.assertEqual(money_minor(str(MIN_INT64)), MIN_INT64)
        self.assertEqual(money_minor(Decimal("0.29"), 2), 29)
        self.assertEqual(money_minor("-100"), -100)

    def test_money_declared_locale(self):
        self.assertEqual(money_minor("1.234,56", 2, decimal_sep=",", group_sep="."), 123456)
        self.assertEqual(money_minor("1,234.00", group_sep=","), 1234)
        with self.assertRaises(DataError):
            money_minor("12,34", group_sep=",")

    def test_money_rejects_float_rounding_overflow_and_ambiguous_format(self):
        for value in (1.0, True, "0.1", str(MAX_INT64 + 1), str(MIN_INT64 - 1), "1,000", "NaN", "1e3", " 100"):
            with self.subTest(value=value), self.assertRaises(DataError):
                money_minor(value)

    def test_normalization_preserves_vietnamese_d(self):
        self.assertEqual(normalize_text("  ĐIỆN\tđường\n "), "DIEN DUONG")

    def test_natural_key_keeps_zeroes_and_cannot_collide_on_delimiters(self):
        self.assertIn("00001", natural_key("00001"))
        self.assertNotEqual(natural_key("a|b", "c"), natural_key("a", "b|c"))
        for value in (None, "", 123):
            with self.assertRaises(DataError):
                natural_key(value)

    def test_dates_refuse_ambiguous_and_nonexistent_dates(self):
        self.assertEqual(date_iso("2024-02-29"), "2024-02-29")
        for value in ("01/02/2026", "2026-02-29", "20260917", "2026-9-17"):
            with self.assertRaises(DataError):
                date_iso(value)

    def test_times_convert_timezone_and_require_precision(self):
        self.assertEqual(instant_utc("2026-09-17T08:00:00+07:00"), "2026-09-17T01:00:00.000000Z")
        for value in ("2026-09-17", "2026-09-17T08:00:00", "2026-09-17T08:00Z"):
            with self.assertRaises(DataError):
                instant_utc(value)

    def test_half_open_intervals_and_open_end(self):
        self.assertFalse(intervals_overlap(("2026-01-01", "2026-02-01"), ("2026-02-01", None)))
        self.assertTrue(intervals_overlap(("2026-01-01", None), ("2026-02-01", None)))
        with self.assertRaises(DataError):
            valid_interval("2026-02-01", "2026-01-01")


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ktt-m1-")
        self.root = Path(self.temp.name)
        self.config = Config.load(ROOT / "cau_hinh.toml", self.root / "data")

    def tearDown(self):
        self.temp.cleanup()

    def write(self, value: dict, name: str = "input.json") -> Path:
        path = self.root / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def read(self, value: dict):
        return FixtureAdapter().read(json.dumps(value).encode(), self.config)

    def test_config_does_not_allow_real_runtime(self):
        path = self.root / "config.toml"
        path.write_text((ROOT / "cau_hinh.toml").read_text(encoding="utf-8").replace('environment = "fixture"', 'environment = "production"'), encoding="utf-8")
        with self.assertRaisesRegex(DataError, "fixture"):
            Config.load(path)

    def test_all_five_fixture_sources_validate(self):
        for name in ("sao_ke", "hoa_don_xml", "hoa_don_bang_ke", "base", "junsky_xuat"):
            with self.subTest(name=name):
                batch = self.read(fixture(name))
                self.assertTrue(batch.valid, batch.issues)

    def test_json_duplicate_fields_nonfinite_and_real_pdf_rejected(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'%PDF-1.7\n'):
            with self.assertRaises(DataError):
                read_json(raw)
        value = fixture("sao_ke"); value["synthetic"] = False
        with self.assertRaises(DataError):
            self.read(value)

    def test_wrong_entity_missing_metadata_and_stale_asof(self):
        for key, value in (("entity_id", "OTHER_FIXTURE"), ("as_of", "2026-09-10"), ("exported_at", "2026-09-17")):
            obj = fixture("sao_ke"); obj["manifest"][key] = value
            with self.subTest(key=key), self.assertRaises(DataError):
                self.read(obj)

    def test_bad_row_keeps_file_invalid_and_reports_locator(self):
        obj = fixture("sao_ke"); obj["records"][1]["currency"] = "USD"
        result = self.read(obj)
        self.assertFalse(result.valid)
        issue = next(i for i in result.issues if i.code == "WRONG_CURRENCY")
        self.assertEqual(issue.locator, "$.records[1]")

    def test_ambiguous_identity_and_unmapped_fields_block(self):
        for change in ({"identity_verified": False}, {"unknown_source_field": "x"}):
            obj = fixture("sao_ke"); obj["records"][0].update(change)
            self.assertFalse(self.read(obj).valid)

    def test_source_count_and_balance_must_match(self):
        for field, value in (("count", 99), ("closing_balance", "799"), ("totals", {"BANK/VND": "-199"})):
            obj = fixture("sao_ke"); obj["controls"][field] = value
            self.assertFalse(self.read(obj).valid)

    def test_duplicate_key_inside_file_is_rejected(self):
        obj = fixture("sao_ke"); obj["records"][1] = copy.deepcopy(obj["records"][0])
        self.assertIn("DUPLICATE_SOURCE_KEY", [i.code for i in self.read(obj).issues])

    def test_junsky_bundle_missing_role_and_mismatched_asof(self):
        full = self.read(fixture("junsky_xuat"))
        self.assertTrue(check_junsky_bundle([full])["valid"])
        partial = copy.deepcopy(full)
        partial.records = [r for r in partial.records if r.kind != "JOURNAL"]
        self.assertFalse(check_junsky_bundle([partial])["valid"])
        newer = copy.deepcopy(full); newer.manifest["as_of"] = "2026-09-17"
        self.assertFalse(check_junsky_bundle([full, newer])["valid"])

    def test_same_file_renamed_and_overlapping_export_are_idempotent(self):
        path = self.write(fixture("sao_ke"))
        with Store(self.config) as store:
            first = store.ingest(path)
            self.assertEqual(first["inserted_documents"], 2)
            renamed = self.root / "renamed.json"; shutil.copyfile(path, renamed)
            repeated = store.ingest(renamed)
            self.assertEqual(repeated["inserted_documents"], 0)
            self.assertEqual(repeated["duplicate_documents"], 2)
            overlap = fixture("sao_ke"); overlap["records"][1]["reference"] = "000003"
            report = store.ingest(self.write(overlap, "overlap.json"))
            self.assertEqual((report["inserted_documents"], report["duplicate_documents"]), (1, 1))
            self.assertEqual(store.status()["documents_by_kind"], {"BANK": 3})
            self.assertEqual(store.conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0], 2)
            self.assertIn('"account":"00001234"', store.conn.execute("SELECT core_json FROM documents LIMIT 1").fetchone()[0])

    def test_conflicting_key_rolls_back_other_new_rows(self):
        with Store(self.config) as store:
            store.ingest(FIXTURES / "sao_ke.json")
            obj = fixture("sao_ke")
            obj["records"][0]["reference"] = "NEW"
            obj["records"][1]["description"] = "Changed same identity"
            report = store.ingest(self.write(obj))
            self.assertEqual(report["state"], "REJECTED")
            self.assertIn("IDENTITY_CONFLICT", [i["code"] for i in report["issues"]])
            self.assertEqual(store.status()["documents_by_kind"], {"BANK": 2})
            self.assertEqual(store.conn.execute("SELECT COUNT(*) FROM evidence WHERE attempt_id=?", (report["attempt_id"],)).fetchone()[0], 0)
            self.assertEqual(store.conn.execute("SELECT COUNT(*) FROM staging WHERE attempt_id=?", (report["attempt_id"],)).fetchone()[0], 2)

    def test_invoice_two_sources_one_header_preserves_details_and_evidence(self):
        with Store(self.config) as store:
            store.ingest(FIXTURES / "hoa_don_bang_ke.json")
            second = store.ingest(FIXTURES / "hoa_don_xml.json")
            self.assertEqual(second["duplicate_documents"], 1)
            self.assertEqual(store.status()["documents_by_kind"], {"INVOICE": 1})
            self.assertEqual(store.conn.execute("SELECT COUNT(*) FROM document_lines").fetchone()[0], 2)
            self.assertEqual(store.conn.execute("SELECT amount_minor FROM documents").fetchone()[0], 200)
            self.assertEqual(store.conn.execute("SELECT COUNT(DISTINCT source_record_id) FROM evidence").fetchone()[0], 2)
            store.ingest(FIXTURES / "hoa_don_bang_ke.json")
            self.assertEqual(store.conn.execute("SELECT COUNT(*) FROM document_lines").fetchone()[0], 2)

    def test_invoice_money_conflict_is_preserved_as_warning_not_file_rejection(self):
        with Store(self.config) as store:
            store.ingest(FIXTURES / "hoa_don_xml.json")
            obj = fixture("hoa_don_bang_ke"); obj["records"][0]["amount"] = "201"; obj["controls"]["totals"]["INVOICE/VND"] = "201"
            self.assertEqual(store.ingest(self.write(obj))["state"], "COMMITTED")
            self.assertEqual(store.conn.execute("SELECT amount_minor FROM documents").fetchone()[0], 201)
            self.assertEqual(store.conn.execute("SELECT status FROM document_observations ORDER BY rowid DESC LIMIT 1").fetchone()[0], "WARNING_MONEY_CONFLICT")

    def test_invoice_replacement_keeps_reference_without_inventing_original(self):
        obj = fixture("hoa_don_bang_ke")
        obj["records"][0].update(number="000002", source_status="REPLACEMENT", related_invoice_key=["000001_FIXTURE", "1C26FIXTURE", "000001", "FIXTURE"])
        with Store(self.config) as store:
            self.assertEqual(store.ingest(self.write(obj))["state"], "COMMITTED")
            self.assertEqual(store.status()["documents_by_kind"], {"INVOICE": 1})
            core = json.loads(store.conn.execute("SELECT core_json FROM documents").fetchone()[0])
            self.assertIn("related_invoice_key", core)

    def test_invoice_detail_total_and_duplicate_line_fail(self):
        for change in ({"amount": "47"}, {"line_id": "02"}):
            obj = fixture("hoa_don_xml"); obj["records"][0]["lines"][0].update(change)
            self.assertFalse(self.read(obj).valid)

    def test_late_detail_cannot_change_known_header_or_early_cutoff(self):
        with Store(self.config) as store:
            store.ingest(FIXTURES / "hoa_don_bang_ke.json")
            obj = fixture("hoa_don_xml"); obj["manifest"]["known_at"] = "2026-09-20T00:00:00Z"
            store.ingest(self.write(obj))
            early = store.visible_documents("2026-09-17T02:00:00Z")
            self.assertEqual(len(early), 1)
            self.assertNotIn("lines", json.loads(early[0]["core_json"]))
            self.assertEqual(store.conn.execute("SELECT COUNT(*) FROM evidence WHERE scope_key LIKE 'line:%' AND known_at<=?", ("2026-09-17T02:00:00.000000Z",)).fetchone()[0], 0)

    def test_unknown_knownat_stays_null_and_excluded_from_cutoff(self):
        obj = fixture("sao_ke"); obj["manifest"]["known_at"] = None
        with Store(self.config) as store:
            report = store.ingest(self.write(obj))
            self.assertEqual(report["state"], "COMMITTED")
            self.assertEqual(store.visible_documents("2030-01-01T00:00:00Z"), [])
            self.assertIn("UNKNOWN_KNOWN_AT", [i["code"] for i in report["issues"]])

    def test_injected_write_failure_is_atomic_and_retry_safe(self):
        with Store(self.config) as store:
            original = store._promote_record
            calls = 0
            def fail_second(*args):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError("simulated crash")
                return original(*args)
            with patch.object(store, "_promote_record", side_effect=fail_second):
                report = store.ingest(FIXTURES / "sao_ke.json")
            self.assertEqual(report["state"], "REJECTED")
            self.assertEqual(store.status()["documents_by_kind"], {})
            self.assertEqual(store.conn.execute("SELECT COUNT(*) FROM staging").fetchone()[0], 2)
            self.assertEqual(store.ingest(FIXTURES / "sao_ke.json")["inserted_documents"], 2)

    def test_process_exit_during_transaction_rolls_back_and_retry_works(self):
        with Store(self.config):
            pass
        script = """import os,sys
from pathlib import Path
from kho_tri_thuc.ha_tang.config import Config
from kho_tri_thuc.ha_tang.store import Store
c=Config.load(Path(sys.argv[1]),Path(sys.argv[2]))
s=Store(c)
original=s._promote_record
def crash(*args):
 original(*args)
 os._exit(73)
s._promote_record=crash
s.ingest(Path(sys.argv[3]))
"""
        completed = subprocess.run([sys.executable, "-c", script, str(ROOT / "cau_hinh.toml"), str(self.config.data_dir), str(FIXTURES / "sao_ke.json")], capture_output=True, timeout=20)
        self.assertEqual(completed.returncode, 73, completed.stderr)
        with Store(self.config) as store:
            self.assertEqual(store.status()["documents_by_kind"], {})
            self.assertEqual(len(store.status()["incomplete_attempts"]), 1)
            self.assertEqual(store.ingest(FIXTURES / "sao_ke.json")["inserted_documents"], 2)

    def test_parallel_ingestion_does_not_duplicate(self):
        with Store(self.config):
            pass
        def run_one(_):
            with Store(self.config) as store:
                return store.ingest(FIXTURES / "sao_ke.json")
        with ThreadPoolExecutor(max_workers=2) as pool:
            reports = list(pool.map(run_one, range(2)))
        self.assertTrue(all(r["state"] == "COMMITTED" for r in reports))
        self.assertEqual(sum(r["inserted_documents"] for r in reports), 2)

    def test_corrupt_raw_is_not_overwritten(self):
        with Store(self.config) as store:
            report = store.ingest(FIXTURES / "sao_ke.json")
            raw = self.config.data_dir / "raw" / (report["artifact_hash"] + ".bin")
            raw.write_bytes(b"tampered")
            with self.assertRaises(DataError):
                store.ingest(FIXTURES / "sao_ke.json")
            self.assertEqual(raw.read_bytes(), b"tampered")

    def test_foreign_key_rejects_orphan_line(self):
        with Store(self.config) as store:
            with self.assertRaises(sqlite3.IntegrityError):
                store.conn.execute("INSERT INTO document_lines VALUES ('x','missing','1',1,'{}','h')")

    def test_all_sources_roundtrip_has_expected_entity_counts(self):
        with Store(self.config) as store:
            for name in ("sao_ke", "hoa_don_xml", "hoa_don_bang_ke", "base", "junsky_xuat"):
                self.assertEqual(store.ingest(FIXTURES / f"{name}.json")["state"], "COMMITTED")
            self.assertEqual(sum(store.status()["documents_by_kind"].values()), 12)
            for name in ("sao_ke", "hoa_don_xml", "hoa_don_bang_ke", "base", "junsky_xuat"):
                self.assertEqual(store.ingest(FIXTURES / f"{name}.json")["inserted_documents"], 0)
            self.assertTrue(store.status()["integrity"]["ok"])

    def test_base_directory_decodes_all_and_reports_missing_extra_bad_data(self):
        directory = self.root / "base"; shutil.copytree(FIXTURES / "base_directory", directory)
        good = scan_fixture_base(directory, FIXTURES / "base_index.json")
        self.assertTrue(good["valid"]); self.assertEqual(good["decoded_count"], 2)
        (directory / "RQ0001.json").rename(directory / "extra.json")
        (directory / "RQ0002.json").write_text('{"format":"ktt-base-item-v1","synthetic":true,"payload_base64":"!!!!"}', encoding="utf-8")
        result = scan_fixture_base(directory, FIXTURES / "base_index.json")
        self.assertFalse(result["valid"])
        self.assertEqual(result["missing"], ["RQ0001.json"])
        self.assertEqual(result["extra"], ["extra.json"])
        self.assertEqual(result["issues"][0]["code"], "BASE_DECODE_ERROR")

    def test_base_duplicate_id_and_unsafe_index(self):
        directory = self.root / "base"; shutil.copytree(FIXTURES / "base_directory", directory)
        shutil.copyfile(directory / "RQ0001.json", directory / "RQ0002.json")
        result = scan_fixture_base(directory, FIXTURES / "base_index.json")
        self.assertEqual(result["issues"][0]["code"], "DUPLICATE_BASE_ID")
        index = self.write({"format": "ktt-base-index-v1", "synthetic": True, "files": ["../escape.json"]})
        with self.assertRaises(DataError):
            scan_fixture_base(directory, index)

    def test_backup_restore_preserves_snapshot_raw_and_config(self):
        backup, restore = self.root / "backup", self.root / "restore"
        with Store(self.config) as store:
            store.ingest(FIXTURES / "sao_ke.json")
            self.assertTrue(create_backup(store, backup)["verified"])
            store.ingest(FIXTURES / "base.json")
        self.assertTrue(verify_backup(backup)["verified"])
        self.assertTrue(restore_backup(backup, restore)["verified"])
        with Store(replace(self.config, data_dir=restore)) as restored:
            self.assertEqual(restored.status()["documents_by_kind"], {"BANK": 2})
            self.assertEqual(restored.ingest(FIXTURES / "sao_ke.json")["inserted_documents"], 0)
            self.assertEqual(restored.conn.execute("SELECT contents FROM config_history").fetchone()[0], self.config.source_bytes)
        self.assertEqual(len(list((restore / "raw").glob("*.bin"))), 1)

    def test_backup_rejects_missing_raw_tampering_unsafe_paths_and_overwrite(self):
        backup = self.root / "backup"
        with Store(self.config) as store:
            store.ingest(FIXTURES / "sao_ke.json")
            create_backup(store, backup)
            with self.assertRaises(DataError):
                create_backup(store, backup)
        with self.assertRaises(DataError):
            restore_backup(backup, self.config.data_dir)
        raw = next((backup / "raw").glob("*.bin")); original = raw.read_bytes(); raw.write_bytes(b"tamper")
        with self.assertRaises(DataError):
            verify_backup(backup)
        raw.write_bytes(original)
        path = backup / "manifest.json"; manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["files"]["../outside"] = {"sha256": "x", "bytes": 0}
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(DataError):
            verify_backup(backup)

    def test_backup_does_not_succeed_without_referenced_raw(self):
        with Store(self.config) as store:
            result = store.ingest(FIXTURES / "sao_ke.json")
            raw = store.root / "raw" / (result["artifact_hash"] + ".bin")
            raw.unlink()
            with self.assertRaises(OSError):
                create_backup(store, self.root / "incomplete-backup")
            self.assertFalse((self.root / "incomplete-backup").exists())

    def test_snapshot_balances_are_reported_separately(self):
        with Store(self.config) as store:
            store.ingest(FIXTURES / "junsky_xuat.json")
            obj = fixture("junsky_xuat"); obj["manifest"]["snapshot_id"] = "SNAPSHOT_FIXTURE_SECOND"
            store.ingest(self.write(obj))
            totals = [t for t in store.status()["document_amount_totals"] if t["kind"] == "OPEN_ITEM"]
            self.assertEqual(len(totals), 2)
            self.assertTrue(all(t["amount_minor"] == -200 for t in totals))

    def cli(self, *args):
        result = subprocess.run([sys.executable, "-X", "utf8", "-m", "kho_tri_thuc", "--config", str(ROOT / "cau_hinh.toml"),
                                 "--data-dir", str(self.config.data_dir), *map(str, args)], capture_output=True, text=True, encoding="utf-8", timeout=20)
        return result.returncode, json.loads(result.stdout)

    def test_cli_validate_does_not_initialize_and_rejects_bad_input(self):
        code, report = self.cli("validate", FIXTURES / "sao_ke.json")
        self.assertEqual(code, 0); self.assertTrue(report["valid"])
        self.assertFalse(self.config.data_dir.exists())
        obj = fixture("sao_ke"); obj["controls"]["count"] = 999
        code, report = self.cli("validate", self.write(obj))
        self.assertEqual(code, 2); self.assertFalse(report["valid"])
        self.assertFalse(self.config.data_dir.exists())

    def test_cli_init_ingest_report_and_backup_restore(self):
        self.assertEqual(self.cli("status")[0], 2)
        self.assertEqual(self.cli("init")[0], 0)
        code, report = self.cli("ingest", FIXTURES / "sao_ke.json")
        self.assertEqual(code, 0); self.assertEqual(report["inserted_documents"], 2)
        code, fetched = self.cli("report", "--attempt-id", report["attempt_id"])
        self.assertEqual(code, 0); self.assertEqual(fetched, report)
        self.assertEqual(self.cli("backup", self.root / "cli-backup")[0], 0)
        self.assertEqual(self.cli("restore", self.root / "cli-backup", self.root / "cli-restore")[0], 0)


class MigrationTests(unittest.TestCase):
    def test_upgrade_preserves_data_and_is_idempotent(self):
        with sqlite3.connect(":memory:", isolation_level=None) as conn:
            migrate(conn, target=1)
            conn.execute("INSERT INTO workspace_meta VALUES ('sentinel','preserved')")
            migrate(conn)
            migrate(conn)
            self.assertEqual(conn.execute("SELECT value FROM workspace_meta WHERE key='sentinel'").fetchone()[0], "preserved")
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], SCHEMA_VERSION)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0], SCHEMA_VERSION)

    def test_migration_failure_rolls_back_schema_and_version(self):
        with sqlite3.connect(":memory:", isolation_level=None) as conn:
            migrate(conn, target=1)
            broken = (MIGRATIONS[0], MIGRATIONS[1] + ("THIS IS NOT SQL",))
            with patch("kho_tri_thuc.ha_tang.database.MIGRATIONS", broken), self.assertRaises(sqlite3.Error):
                migrate(conn)
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertIsNone(conn.execute("SELECT name FROM sqlite_master WHERE name='document_lines'").fetchone())

    def test_foreign_database_and_future_version_are_rejected(self):
        with sqlite3.connect(":memory:", isolation_level=None) as conn:
            conn.execute("CREATE TABLE unrelated(x)")
            with self.assertRaises(DataError):
                migrate(conn)
        with sqlite3.connect(":memory:", isolation_level=None) as conn:
            migrate(conn)
            conn.execute("PRAGMA user_version=99")
            with self.assertRaises(DataError):
                migrate(conn)


if __name__ == "__main__":
    unittest.main()
