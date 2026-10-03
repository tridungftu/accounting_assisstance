"""Local HTML intake uses test bytes only; no real accounting data or external network."""
from __future__ import annotations

import http.client
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
from unittest.mock import patch

from kho_tri_thuc.giao_dien.intake import Intake
from kho_tri_thuc.giao_dien.operations import Operations
from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
from kho_tri_thuc.ha_tang.primitives import DataError, sha256

ROOT = Path(__file__).resolve().parents[1]
META = {"name": "Sao kê KIỂM THỬ.csv", "source": "sao_ke", "entity": "TEST_ONLY", "period": "2026-09", "note": "Dữ liệu kiểm thử, không phải sao kê thật"}
RAW = b"TEST ONLY - not accounting data\r\nid,amount\r\nTEST,100\r\n"


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ktt-intake-")
        self.root = Path(self.temp.name)
        self.intake = Intake(self.root / "inbox")

    def tearDown(self):
        self.temp.cleanup()

    def test_round_trip_survives_restart_without_claiming_normalization(self):
        receipt = self.intake.receive(RAW, {**META, "modified_at": 0})
        restarted = Intake(self.root / "inbox")
        restored, content = restarted.download(receipt["id"])
        self.assertEqual(RAW, content)
        self.assertEqual(receipt["sha256"], sha256(RAW))
        self.assertEqual(restored["state"], "RECEIVED_WAITING_ADAPTER")
        self.assertFalse(restored["normalized"])
        self.assertFalse(restored["posted"])
        self.assertIsNone(restored["known_at"])
        self.assertIsNone(restored["known_at_basis"])
        self.assertTrue(restored["received_at"].endswith("Z"))
        self.assertEqual(restarted.listing()["total"], 1)

    def test_duplicate_bytes_ignore_filename_but_keep_original_receipt(self):
        first = self.intake.receive(RAW, META)
        again = self.intake.receive(RAW, {**META, "name": "renamed.csv", "note": "changed"})
        self.assertTrue(again["duplicate"])
        self.assertEqual(first["id"], again["id"])
        self.assertEqual(META["name"], again["name"])
        self.assertEqual(META["note"], again["note"])
        self.assertEqual(1, self.intake.listing()["total"])

    def test_same_name_changed_content_preserves_both_versions(self):
        first = self.intake.receive(RAW, META)
        second = self.intake.receive(RAW + b"TEST2,200\n", META)
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(2, self.intake.listing()["total"])
        self.assertEqual(RAW, self.intake.download(first["id"])[1])

    def test_scope_changes_receipt_not_raw_storage_size(self):
        self.intake.receive(RAW, META)
        for metadata in ({"entity": "OTHER_TEST"}, {"period": "2026-08"}, {"source": "base"}):
            self.assertFalse(self.intake.receive(RAW, {**META, **metadata})["duplicate"])
        listing = self.intake.listing()
        self.assertEqual(4, listing["total"])
        self.assertEqual(len(RAW), listing["total_bytes"])
        self.assertEqual(1, len(list((self.intake.root / "raw").glob("*"))))

    def test_invalid_metadata_cannot_write_any_receipt(self):
        changes = [{"name": "../escape.csv"}, {"name": "C:\\escape.csv"}, {"name": "bad\n.csv"},
                   {"name": "program.exe"}, {"entity": ""}, {"period": "2026-13"}, {"period": "2026-1"},
                   {"source": "unknown"}, {"source": []}, {"known_at": "2020-01-01"}, {"note": 9}, {"modified_at": True}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(DataError):
                self.intake.receive(RAW, {**META, **change})
        self.assertEqual(0, self.intake.listing()["total"])

    def test_empty_and_oversize_files_rejected(self):
        with self.assertRaises(DataError):
            self.intake.receive(b"", META)
        with patch("kho_tri_thuc.giao_dien.intake.MAX_FILE_SIZE", 4), self.assertRaises(DataError):
            self.intake.receive(RAW, META)

    def test_relative_path_is_metadata_never_a_write_path(self):
        r = self.intake.receive(RAW, {**META, "relative_path": "../../elsewhere/evil.csv"})
        self.assertEqual("../../elsewhere/evil.csv", r["original_relative_path"])
        self.assertFalse((self.root / "elsewhere").exists())
        self.assertEqual(RAW, self.intake.download(r["id"])[1])

    def test_explicit_fixture_cannot_be_received_as_real_but_unknown_json_can(self):
        with self.assertRaises(DataError) as exc:
            self.intake.receive(b'{"synthetic": true}', {**META, "name": "fixture.json"})
        self.assertEqual("FIXTURE_IN_REAL_INBOX", exc.exception.code)
        r = self.intake.receive(b'{"unknown_source":123}', {**META, "name": "source.json"})
        self.assertFalse(r["normalized"])

    def test_corrupt_blob_cannot_be_downloaded_or_acknowledged_as_duplicate(self):
        r = self.intake.receive(RAW, META)
        (self.intake.root / "raw" / (r["sha256"] + ".bin")).write_bytes(b"tampered")
        for operation in (lambda: self.intake.download(r["id"]), lambda: self.intake.receive(RAW, META)):
            with self.assertRaises(DataError) as exc:
                operation()
            self.assertEqual("INTAKE_CHECKSUM", exc.exception.code)

    def test_corrupt_receipt_is_reported_not_silently_counted(self):
        r = self.intake.receive(RAW, META)
        path = self.intake.root / "receipts" / (r["id"] + ".json")
        for content in ("[]", "{bad", json.dumps({"id": r["id"]}), json.dumps({**r, "entity": "ALTERED"})):
            path.write_text(content, encoding="utf-8")
            listing = self.intake.listing()
            self.assertEqual(1, listing["damaged_receipts"])
            self.assertEqual(0, listing["total"])

    def test_concurrent_duplicate_submissions_create_one_receipt(self):
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(lambda _: self.intake.receive(RAW, META), range(12)))
        self.assertEqual(1, sum(not r["duplicate"] for r in results))
        self.assertEqual(1, self.intake.listing()["total"])

    def test_failed_receipt_publish_is_retryable_without_false_success(self):
        from kho_tri_thuc.giao_dien import intake
        real_write = intake.write_immutable
        def fail_receipt(path, data):
            if path.suffix == ".json":
                raise OSError("test disk error")
            return real_write(path, data)
        with patch.object(intake, "write_immutable", side_effect=fail_receipt), self.assertRaises(OSError):
            self.intake.receive(RAW, META)
        self.assertEqual(0, self.intake.listing()["total"])
        self.assertFalse(self.intake.receive(RAW, META)["duplicate"])
        self.assertEqual(1, self.intake.listing()["total"])


class LocalHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ktt-web-")
        self.app = LocalApp(ROOT / "cau_hinh.toml", Path(self.temp.name) / "web")
        self.server = LocalServer(self.app, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.temp.cleanup()

    def request(self, path, method="GET", body=None, headers=None, token=True):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        auth = {"X-KTT-Token": self.app.token} if token else {}
        connection.request(method, path, body=body, headers={**auth, **(headers or {})})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def json_request(self, *args, **kwargs):
        status, headers, body = self.request(*args, **kwargs)
        return status, json.loads(body)

    def upload(self, metadata=None, raw=RAW, **kwargs):
        return self.json_request("/api/upload", "POST", raw, {"X-File-Info": quote(json.dumps(metadata or META, ensure_ascii=False))}, **kwargs)

    def test_static_page_assets_and_local_health(self):
        status, headers, body = self.request("/", token=False)
        self.assertEqual(200, status)
        self.assertIn(self.app.token.encode(), body)
        self.assertIn(b"frame-ancestors 'none'", headers["Content-Security-Policy"].encode())
        self.assertEqual("no-store", headers["Cache-Control"])
        self.assertNotIn(b"https://", body)
        for asset in ("/app.js", "/style.css", "/mark.svg"):
            self.assertEqual(200, self.request(asset, token=False)[0])
        status, health = self.json_request("/api/health", token=False)
        self.assertEqual(200, status)
        self.assertEqual(self.app.root_id, health["root_id"])
        self.assertNotIn("storage_path", health)
        self.assertEqual("127.0.0.1", self.server.server_address[0])

    def test_upload_list_download_and_restart(self):
        status, receipt = self.upload()
        self.assertEqual(201, status)
        self.assertEqual(200, self.upload()[0])
        status, state = self.json_request("/api/state")
        self.assertEqual(1, state["total"])
        self.assertFalse(state["real_processing"])
        self.assertFalse(state["ai_required"])
        self.assertEqual({}, state["demo"]["documents_by_kind"])
        status, headers, content = self.request(f"/api/files/{receipt['id']}/download")
        self.assertEqual(200, status)
        self.assertEqual(RAW, content)
        self.assertIn("attachment; filename*=UTF-8''", headers["Content-Disposition"])
        restarted = LocalApp(ROOT / "cau_hinh.toml", self.app.root)
        self.assertEqual(1, restarted.state()["total"])
        self.assertNotEqual(restarted.token, self.app.token)

    def test_missing_wrong_token_and_cross_site_cannot_write_or_read_private_state(self):
        self.assertEqual(403, self.json_request("/api/state", token=False)[0])
        for headers in ({"X-KTT-Token": "bad"}, {"Origin": "https://external.example"}, {"Sec-Fetch-Site": "cross-site"}, {"Host": "external.example"}):
            status, result = self.json_request("/api/upload", "POST", RAW, {"X-File-Info": quote(json.dumps(META)), **headers})
            self.assertEqual(403, status, result)
            self.assertEqual(403, self.request("/api/state", headers=headers)[0])
        self.assertEqual(403, self.upload(token=False)[0])
        self.assertEqual(0, self.app.intake.listing()["total"])

    def test_cors_and_path_traversal_expose_no_files(self):
        self.assertEqual(403, self.request("/api/upload", "OPTIONS")[0])
        for path in ("/../cau_hinh.toml", "/%2e%2e/cau_hinh.toml", "/assets/../../cau_hinh.toml", "/raw/unknown.bin"):
            self.assertEqual(404, self.request(path)[0])
        self.assertEqual(400, self.request("/api/files/invalid/download")[0])

    def test_that_quick_export_download_needs_token_and_stays_in_its_run_directory(self):
        operation = object.__new__(Operations)
        operation.root = self.app.root
        run_id = "RUN_SYNTHETIC"
        output = operation.root / "xuat-junsky" / run_id
        output.mkdir(parents=True)
        raw = b"SYNTHETIC EXPORT WORKBOOK"
        name = "SOAT-RUN_SYNTHETIC.xlsx"
        (output / name).write_bytes(raw)
        self.app.is_that, self.app.operations = True, operation
        path = f"/api/that/quick/{run_id}/download?file={quote(name)}"
        status, headers, content = self.request(path)
        self.assertEqual(200, status)
        self.assertEqual(raw, content)
        self.assertIn("attachment; filename*=UTF-8''", headers["Content-Disposition"])
        self.assertEqual(403, self.request(path, token=False)[0])
        self.assertEqual(400, self.request(f"/api/that/quick/{run_id}/download?file={quote('../outside.xlsx')}")[0])

    def test_v10_routes_need_token_and_keep_scripts_self_only(self):
        for path in ("/api/that/overview", "/api/that/runs", "/api/that/history", "/api/that/knowledge-cards?q=331"):
            with self.subTest(path=path):
                self.assertEqual(403, self.request(path, token=False)[0])
                status, result = self.json_request(path)
                self.assertEqual(400, status)
                self.assertEqual("THAT_UI", result["error"])
        for path in ("/api/that/reload", "/api/that/learning-settings", "/api/that/cash-mapping", "/api/that/open", "/api/that/quick/repropose"):
            with self.subTest(path=path):
                self.assertEqual(403, self.request(path, "POST", b"{}", {"Content-Type": "application/json"}, token=False)[0])
        csp = self.request("/", token=False)[1]["Content-Security-Policy"]
        self.assertIn("script-src 'self';", csp)
        self.assertNotIn("script-src 'self' 'unsafe-inline'", csp)

    def test_oversize_request_rejected_before_reading_bytes(self):
        status, result = self.json_request("/api/upload", "POST", b"", {"Content-Length": str(50 * 1024 * 1024 + 1), "X-File-Info": quote(json.dumps(META))})
        self.assertEqual(413, status)
        self.assertEqual("FILE_TOO_LARGE", result["error"])
        self.assertEqual(0, self.app.intake.listing()["total"])

    def test_bad_request_returns_explained_error_without_crashing_server(self):
        for metadata in ("bad-json", "[]", '{"source": []}', '{"name":"x.csv","known_at":"invented"}'):
            status, result = self.json_request("/api/upload", "POST", RAW, {"X-File-Info": quote(metadata)})
            self.assertEqual(400, status)
            self.assertIn("message", result)
        self.assertEqual(200, self.request("/api/state")[0])

    def test_demo_validate_does_not_ingest_and_ingest_deduplicates(self):
        status, headers, sample = self.request("/api/sample?source=sao_ke")
        self.assertEqual(200, status)
        status, report = self.json_request("/api/demo/validate", "POST", sample)
        self.assertEqual("VALIDATED", report["state"])
        self.assertEqual({}, self.app.state()["demo"]["documents_by_kind"])
        status, first = self.json_request("/api/demo/ingest", "POST", sample)
        status, again = self.json_request("/api/demo/ingest", "POST", sample)
        self.assertEqual("COMMITTED", first["state"])
        self.assertEqual(2, first["inserted_documents"])
        self.assertEqual(0, again["inserted_documents"])
        self.assertEqual(2, again["duplicate_documents"])
        self.assertEqual(0, self.app.state()["total"])
        status, report = self.upload({**META, "name": "fixture.json"}, sample)
        self.assertEqual(400, status)
        self.assertEqual("FIXTURE_IN_REAL_INBOX", report["error"])

    def test_real_unknown_source_cannot_normalize_through_demo(self):
        status, report = self.json_request("/api/demo/ingest", "POST", b'{"bank_rows": [{"amount": 100}]}')
        self.assertIn(status, (200, 400))
        if status == 200:
            self.assertEqual("REJECTED", report["state"])
        self.assertEqual({}, self.app.state()["demo"]["documents_by_kind"])
        self.assertEqual(0, self.app.state()["total"])

    def test_shutdown_requires_token_then_stops_server(self):
        self.assertEqual(403, self.request("/api/shutdown", "POST", b"{}", token=False)[0])
        self.assertTrue(self.thread.is_alive())
        self.assertEqual(200, self.request("/api/shutdown", "POST", b"{}")[0])
        self.thread.join(3)
        self.assertFalse(self.thread.is_alive())


if __name__ == "__main__":
    unittest.main()
