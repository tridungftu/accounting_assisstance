"""Run the actual suite and save machine-readable evidence; no production data used."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    suite = unittest.defaultTestLoader.discover(str(root / "tests"), pattern="test_*.py")
    identifiers = []
    def collect(items):
        for item in items:
            if isinstance(item, unittest.TestSuite):
                collect(item)
            else:
                identifiers.append(item.id())
    collect(suite)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {"status": "PASS" if result.wasSuccessful() else "FAIL", "fixture_only": True,
              "finished_at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(), "platform": platform.platform(),
              "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
              "test_ids": identifiers, "failure_details": [(case.id(), detail) for case, detail in result.failures + result.errors],
              "source_hashes": {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for folder in (root / "src", root / "tests") for path in sorted(folder.rglob("*.py"))},
              "interface_hashes": {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in
                                   [*sorted((root / "src" / "kho_tri_thuc" / "giao_dien" / "assets").glob("*")), root / "start-web.ps1", root / "MỞ BẢN DEMO.cmd", root / "MỞ PHẦN MỀM.cmd"] if path.is_file()},
              "raw_intake_test_bytes_only": True,
              "real_data_validated": False, "accountant_acceptance": False, "manual_testing": "DEFERRED_BY_USER"}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(args.report.resolve()), "tests_run": result.testsRun, "status": report["status"]}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
