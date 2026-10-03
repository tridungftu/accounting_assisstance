"""Promote the verified V9b F4 candidate after a reversible local backup.

This helper only operates below the project ``var`` directory.  It never
touches a Junsky/source workbook and reports aggregate state only.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

from kho_tri_thuc.ha_tang.primitives import canonical_json, sha256


PROJECT = Path(__file__).resolve().parents[1]
VAR = (PROJECT / "var").resolve()
SAFE = (VAR / "vong-2" / "V9-giao-viec").resolve()
DEFAULT_CANDIDATE = SAFE / "F4-main-candidate"
DEFAULT_MAIN = VAR / "plhn-that"
DEFAULT_BACKUP = SAFE / "F4-backup-pre-v9b"


def _under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _db_state(path: Path) -> dict[str, int | bool]:
    uri = path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        return {
            "schema_version": int(conn.execute("PRAGMA user_version").fetchone()[0]),
            "integrity_ok": [str(row[0]) for row in conn.execute("PRAGMA integrity_check")] == ["ok"],
            "foreign_key_violations": sum(1 for _ in conn.execute("PRAGMA foreign_key_check")),
        }
    finally:
        conn.close()


def _referenced_artifacts(root: Path, db: Path) -> int:
    uri = db.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        rows = list(conn.execute("SELECT hash,relative_path,byte_length FROM artifacts"))
    finally:
        conn.close()
    for digest, relative, size in rows:
        path = (root / str(relative)).resolve()
        if not path.is_file() or not _under(path, root) or path.stat().st_size != int(size):
            raise RuntimeError("Artifact của kho ứng viên không đầy đủ.")
        if sha256(path.read_bytes()) != str(digest):
            raise RuntimeError("Artifact của kho ứng viên không khớp checksum.")
    return len(rows)


def _copy_database(source: Path, target: Path) -> None:
    uri = source.resolve().as_uri() + "?mode=ro"
    read = sqlite3.connect(uri, uri=True)
    write = sqlite3.connect(target)
    try:
        read.backup(write)
    finally:
        write.close()
        read.close()


def _backup_main(main: Path, backup: Path) -> dict[str, int | bool]:
    if backup.exists():
        raise RuntimeError("Đích backup đã tồn tại; không ghi đè.")
    staging = backup.with_name(backup.name + ".partial-" + uuid4().hex)
    staging.mkdir(parents=True)
    try:
        _copy_database(main / "kho.sqlite", staging / "kho.sqlite")
        for child in main.iterdir():
            if child.name in {"kho.sqlite", "kho.sqlite-wal", "kho.sqlite-shm"}:
                continue
            target = staging / child.name
            if child.is_dir():
                shutil.copytree(child, target)
            elif child.is_file():
                shutil.copy2(child, target)
        state = _db_state(staging / "kho.sqlite")
        if not state["integrity_ok"] or state["foreign_key_violations"]:
            raise RuntimeError("Backup không qua kiểm tra SQLite.")
        _referenced_artifacts(staging, staging / "kho.sqlite")
        staging.rename(backup)
        return state
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _check_candidate(candidate: Path) -> tuple[Path, dict[str, object]]:
    report_path = candidate / "KET-QUA-F4-CLEAN.json"
    data = candidate / "data"
    db = data / "kho.sqlite"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Không đọc được báo cáo F4 của kho ứng viên.") from exc
    status = report.get("candidate", {})
    required = (
        report.get("status") == "OK",
        bool(status.get("idempotent_no_change")),
        bool(status.get("handoff_has_no_posting_decisions")),
        bool(status.get("no_active_knowledge_overlap")),
        bool(status.get("no_duplicate_logical_knowledge")),
        bool(status.get("after_second", {}).get("integrity", {}).get("ok")),
    )
    if not all(required) or not db.is_file():
        raise RuntimeError("Kho ứng viên chưa đạt điều kiện F4 để chuyển.")
    candidate_state = _db_state(db)
    if not candidate_state["integrity_ok"] or candidate_state["foreign_key_violations"]:
        raise RuntimeError("Kho ứng viên không qua kiểm tra SQLite cuối.")
    _referenced_artifacts(data, db)
    return data, candidate_state


def promote(candidate: Path, main: Path, backup: Path) -> dict[str, object]:
    candidate, main, backup = candidate.resolve(), main.resolve(), backup.resolve()
    if not _under(candidate, SAFE) or not _under(backup, SAFE) or not _under(main, VAR):
        raise RuntimeError("Đường dẫn chuyển kho nằm ngoài phạm vi cho phép.")
    if not main.is_dir() or not (main / "kho.sqlite").is_file():
        raise RuntimeError("Kho chính hiện hữu không hợp lệ.")
    data, candidate_state = _check_candidate(candidate)
    main_before = _db_state(main / "kho.sqlite")
    backup_state = _backup_main(main, backup)
    staging = main.with_name(main.name + ".candidate-" + uuid4().hex)
    archived = main.with_name(main.name + ".pre-v9b-" + uuid4().hex)
    try:
        shutil.copytree(data, staging)
        staged_state = _db_state(staging / "kho.sqlite")
        if staged_state != candidate_state:
            raise RuntimeError("Bản sao kho ứng viên thay đổi khi chuẩn bị chuyển.")
        _referenced_artifacts(staging, staging / "kho.sqlite")
        main.rename(archived)
        try:
            staging.rename(main)
        except BaseException:
            archived.rename(main)
            raise
        # The canonical backup is retained under V9-giao-viec.  The transient
        # old workspace is kept as a second rollback point until a later,
        # explicit cleanup; no historical evidence is deleted here.
        result = {
            "status": "OK",
            "main_schema_before": main_before["schema_version"],
            "main_schema_after": candidate_state["schema_version"],
            "backup_integrity_ok": backup_state["integrity_ok"],
            "candidate_integrity_ok": candidate_state["integrity_ok"],
            "foreign_key_violations": candidate_state["foreign_key_violations"],
            "backup_created": True,
            "old_workspace_retained": True,
        }
        (candidate / "KET-QUA-F4-PROMOTE.json").write_text(canonical_json(result), encoding="utf-8")
        return result
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise


def main_cli() -> int:
    parser = argparse.ArgumentParser(description="V9b F4 clean-store promotion")
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--main", type=Path, default=DEFAULT_MAIN)
    parser.add_argument("--backup", type=Path, default=DEFAULT_BACKUP)
    args = parser.parse_args()
    try:
        result = promote(args.candidate, args.main, args.backup)
    except Exception as exc:
        print(canonical_json({"status": "FAILED", "error_type": type(exc).__name__}))
        return 1
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
