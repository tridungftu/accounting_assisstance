"""Build and verify an isolated F4 candidate store without exposing source rows.

This is a V9b handoff helper, not an application migration.  It never writes
to the configured operational database or to an input source.  The candidate
is built beneath ``var/vong-2/V9-giao-viec`` and its JSON report contains only
counts, booleans, schema state, and integrity results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import threading
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from kho_tri_thuc.giao_dien.operations import Operations
from kho_tri_thuc.ha_tang.config import Config
from kho_tri_thuc.ha_tang.primitives import canonical_json, now_utc
from kho_tri_thuc.ha_tang.store import Store
from kho_tri_thuc.tri_thuc.service import Knowledge


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAFE_PARENT = (PROJECT_ROOT / "var" / "vong-2" / "V9-giao-viec").resolve()
DEFAULT_OUTPUT = SAFE_PARENT / "F4-main-candidate"
DEFAULT_MAIN_WEB = PROJECT_ROOT / "var" / "web-that"


def _under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _scalar(conn: sqlite3.Connection, sql: str, default: int = 0) -> int:
    row = conn.execute(sql).fetchone()
    return int(row[0] if row and row[0] is not None else default)


def _grouped(conn: sqlite3.Connection, sql: str) -> dict[str, int]:
    return {str(row[0]): int(row[1]) for row in conn.execute(sql)}


def _integrity(conn: sqlite3.Connection) -> dict[str, Any]:
    integrity_rows = [str(row[0]) for row in conn.execute("PRAGMA integrity_check")]
    foreign_key_count = sum(1 for _ in conn.execute("PRAGMA foreign_key_check"))
    return {"ok": integrity_rows == ["ok"] and foreign_key_count == 0,
            "integrity_row_count": len(integrity_rows),
            "foreign_key_violation_count": foreign_key_count}


def _aggregate_database(db_path: Path) -> dict[str, Any]:
    """Read aggregate-only state from a DB; never trigger a migration."""
    if not db_path.is_file():
        return {"exists": False}
    uri = db_path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        tables = _table_names(conn)
        result: dict[str, Any] = {
            "exists": True,
            "schema_version": _scalar(conn, "PRAGMA user_version"),
            "table_count": len(tables),
            "integrity": _integrity(conn),
        }
        if "documents" in tables:
            result["documents_by_kind"] = _grouped(conn, "SELECT kind,COUNT(*) FROM documents GROUP BY kind ORDER BY kind")
        if "attempts" in tables:
            result["attempts_by_source_state"] = _grouped(conn, "SELECT COALESCE(source,'UNSPECIFIED') || ':' || state,COUNT(*) FROM attempts GROUP BY source,state ORDER BY source,state")
        if "knowledge_versions" in tables:
            result["knowledge_versions_by_category"] = _grouped(conn, "SELECT category,COUNT(*) FROM knowledge_versions GROUP BY category ORDER BY category")
            result["knowledge_versions_total"] = _scalar(conn, "SELECT COUNT(*) FROM knowledge_versions")
            result["knowledge_duplicate_logical_groups"] = _scalar(conn, """
                SELECT COUNT(*) FROM (
                    SELECT category,logical_key,valid_from,COALESCE(valid_to,''),COUNT(*) AS n
                    FROM knowledge_versions
                    GROUP BY category,logical_key,valid_from,COALESCE(valid_to,'')
                    HAVING n>1
                )
            """)
            result["knowledge_duplicate_logical_rows"] = _scalar(conn, """
                SELECT COALESCE(SUM(n),0) FROM (
                    SELECT COUNT(*) AS n FROM knowledge_versions
                    GROUP BY category,logical_key,valid_from,COALESCE(valid_to,'')
                    HAVING n>1
                )
            """)
            result["knowledge_duplicate_content_groups"] = _scalar(conn, """
                SELECT COUNT(*) FROM (
                    SELECT category,logical_key,content_hash,COUNT(*) AS n
                    FROM knowledge_versions GROUP BY category,logical_key,content_hash HAVING n>1
                )
            """)
            if "knowledge_events" in tables:
                result["knowledge_events_by_action"] = _grouped(conn, "SELECT action,COUNT(*) FROM knowledge_events GROUP BY action ORDER BY action")
                result["knowledge_approve_by_actor_class"] = _grouped(conn, """
                    SELECT CASE WHEN actor='CFO_NTD' THEN 'CFO_NTD'
                                WHEN actor='HE_THONG_JUNSKY' THEN 'HE_THONG_JUNSKY'
                                ELSE 'OTHER' END,COUNT(*)
                    FROM knowledge_events WHERE action='APPROVE'
                    GROUP BY CASE WHEN actor='CFO_NTD' THEN 'CFO_NTD'
                                  WHEN actor='HE_THONG_JUNSKY' THEN 'HE_THONG_JUNSKY'
                                  ELSE 'OTHER' END
                    ORDER BY 1
                """)
                result["knowledge_nonrevoked_overlap_pairs"] = _scalar(conn, """
                    SELECT COUNT(*) FROM knowledge_versions AS a
                    JOIN knowledge_versions AS b
                      ON a.category=b.category AND a.logical_key=b.logical_key AND a.id<b.id
                    WHERE (a.valid_to IS NULL OR b.valid_from<a.valid_to)
                      AND (b.valid_to IS NULL OR a.valid_from<b.valid_to)
                      AND NOT EXISTS (SELECT 1 FROM knowledge_events er WHERE er.version_id=a.id AND er.action='REVOKE')
                      AND NOT EXISTS (SELECT 1 FROM knowledge_events er WHERE er.version_id=b.id AND er.action='REVOKE')
                """)
        if "knowledge_import_batches" in tables:
            result["knowledge_import_batches"] = _scalar(conn, "SELECT COUNT(*) FROM knowledge_import_batches")
        if "quick_items" in tables:
            result["quick_items_by_state"] = _grouped(conn, "SELECT state,COUNT(*) FROM quick_items GROUP BY state ORDER BY state")
        if "quick_runs" in tables:
            result["quick_runs"] = _scalar(conn, "SELECT COUNT(*) FROM quick_runs")
        if "quick_learning" in tables:
            result["quick_learning"] = _scalar(conn, "SELECT COUNT(*) FROM quick_learning")
        if "quick_condition_learning" in tables:
            result["quick_condition_learning"] = _scalar(conn, "SELECT COUNT(*) FROM quick_condition_learning")
        if "decisions" in tables:
            result["legacy_decisions"] = _scalar(conn, "SELECT COUNT(*) FROM decisions")
        if "cash_account_mappings" in tables:
            result["cash_account_mappings_by_source"] = _grouped(conn, "SELECT source,COUNT(*) FROM cash_account_mappings GROUP BY source ORDER BY source")
        if "export_batches" in tables:
            result["legacy_export_batches"] = _scalar(conn, "SELECT COUNT(*) FROM export_batches")
        if "shadow_exports" in tables:
            result["shadow_exports"] = _scalar(conn, "SELECT COUNT(*) FROM shadow_exports")
        if "workspace_meta" in tables:
            result["workspace_meta_key_count"] = _scalar(conn, "SELECT COUNT(*) FROM workspace_meta")
        return result
    finally:
        conn.close()


def _semantic_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    """Fields that must remain stable on a no-change bootstrap."""
    keys = (
        "documents_by_kind", "attempts_by_source_state", "knowledge_versions_by_category",
        "knowledge_versions_total", "knowledge_duplicate_logical_groups",
        "knowledge_duplicate_logical_rows", "knowledge_duplicate_content_groups",
        "knowledge_events_by_action", "knowledge_approve_by_actor_class",
        "knowledge_nonrevoked_overlap_pairs", "knowledge_import_batches", "quick_items_by_state",
        "quick_runs", "quick_learning", "quick_condition_learning", "legacy_decisions",
        "cash_account_mappings_by_source", "legacy_export_batches", "shadow_exports",
    )
    return {key: report.get(key) for key in keys if key in report}


def _fingerprint(paths: Iterable[Path]) -> str:
    """Private source-change check.  The digest is intentionally never emitted."""
    digest = hashlib.sha256()
    for root in sorted({path.resolve() for path in paths}, key=lambda value: str(value).casefold()):
        entries = [root] if root.is_file() else sorted((item for item in root.rglob("*") if item.is_file()), key=lambda value: str(value).casefold())
        for item in entries:
            digest.update(str(item.relative_to(root.parent)).encode("utf-8", "surrogatepass"))
            digest.update(hashlib.sha256(item.read_bytes()).digest())
    return digest.hexdigest()


def _candidate_operations(config_path: Path, config: Config, web_root: Path) -> Operations:
    """Create the facade without starting a background worker."""
    operations = object.__new__(Operations)
    operations.config_path = config_path.resolve()
    operations.config = config
    operations.root = web_root.resolve()
    operations.staging = operations.root / "nguon-da-chon"
    operations._mutation_lock = threading.RLock()
    operations._jobs = {}
    operations._jobs_lock = threading.RLock()
    return operations


def _knowledge_query_check(config: Config) -> dict[str, int]:
    """Exercise the public query path without exposing logical keys."""
    errors = 0
    with Store(config) as store:
        categories = [str(row[0]) for row in store.conn.execute("SELECT DISTINCT category FROM knowledge_versions ORDER BY category")]
        knowledge = Knowledge(store)
        cutoff = now_utc()
        for category in categories:
            try:
                knowledge.query("2026-08-15", cutoff, category, include_pending=True)
            except Exception:
                errors += 1
    return {"categories_checked": len(categories), "errors": errors}


def _handoff_clean(report: dict[str, Any]) -> bool:
    states = report.get("quick_items_by_state", {})
    return (
        report.get("legacy_decisions", 0) == 0
        and report.get("quick_runs", 0) == 0
        and report.get("quick_learning", 0) == 0
        and report.get("quick_condition_learning", 0) == 0
        and sum(int(value) for value in states.values()) == 0
        and report.get("legacy_export_batches", 0) == 0
        and report.get("shadow_exports", 0) == 0
    )


def _prepare_candidate(output: Path, source_settings: Path, replace: bool) -> Path:
    if not _under(output, SAFE_PARENT) or output == SAFE_PARENT:
        raise RuntimeError("Đích F4 phải là thư mục con của var/vong-2/V9-giao-viec.")
    if output.exists():
        if not replace:
            raise RuntimeError("Đích F4 đã tồn tại; cần dùng --replace sau khi đã kiểm tra đích.")
        # This deletion is limited by the checked path above and never targets a source or main store.
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=False)
    web_root = output / "web"
    web_root.mkdir()
    if source_settings.is_file():
        shutil.copy2(source_settings, web_root / "source-settings.json")
    return web_root


def _source_inputs(operations: Operations, config_path: Path) -> list[Path]:
    settings = operations.source_settings()["paths"]
    catalog = Path(settings["junsky_catalog"])
    root = catalog.parent
    values = [catalog, Path(settings["junsky_dgblist"]), Path(settings["junsky_ledger"])]
    values.extend(root / "bo_quy_tac" / "ket_qua" / name for name in (
        "TU-DIEN-NHOM-NGHIEP-VU.xlsx", "BO-QUY-TAC.xlsx", "HOA-DON-CAY-PHAN-NHANH.xlsx"))
    values.append(config_path.parent / "DANH MUC DOI TAC PLHN - BO SUNG STK VA DICH VU (nhap 24-09-2026).xlsx")
    if not all(path.exists() for path in values):
        raise RuntimeError("Thiếu ít nhất một nguồn bắt buộc để dựng kho F4.")
    return values


def _compact_bootstrap(result: dict[str, Any]) -> dict[str, Any]:
    # Bootstrap already returns aggregate counts/statuses; preserve no file paths or records.
    return {"junsky": str(result.get("junsky", "")), "knowledge": int(result.get("knowledge", 0)), "partners": int(result.get("partners", 0))}


def build(config_path: Path, output: Path, main_web: Path, replace: bool) -> dict[str, Any]:
    operational_config = Config.load(config_path)
    main_before = _aggregate_database(operational_config.data_dir / "kho.sqlite")
    web_root = _prepare_candidate(output, main_web / "source-settings.json", replace)
    candidate_config = Config.load(config_path, output / "data")
    operations = _candidate_operations(config_path, candidate_config, web_root)
    source_inputs = _source_inputs(operations, config_path)
    source_before = _fingerprint(source_inputs)

    first = _compact_bootstrap(operations.bootstrap())
    after_first = _aggregate_database(candidate_config.data_dir / "kho.sqlite")
    query_check = _knowledge_query_check(candidate_config)
    second = _compact_bootstrap(operations.bootstrap())
    after_second = _aggregate_database(candidate_config.data_dir / "kho.sqlite")
    source_unchanged = source_before == _fingerprint(source_inputs)

    idempotent = _semantic_snapshot(after_first) == _semantic_snapshot(after_second)
    report = {
        "status": "OK",
        "mode": "offline-candidate-copy-only",
        "source_files_unchanged": source_unchanged,
        "source_settings_copied": (main_web / "source-settings.json").is_file(),
        "source_input_roots": len(source_inputs),
        "main_before": main_before,
        "candidate": {
            "bootstrap_first": first,
            "bootstrap_second": second,
            "after_first": after_first,
            "after_second": after_second,
            "idempotent_no_change": idempotent,
            "knowledge_query_2026_08_15": query_check,
            "handoff_has_no_posting_decisions": _handoff_clean(after_second),
            "no_active_knowledge_overlap": after_second.get("knowledge_nonrevoked_overlap_pairs", 0) == 0,
            "no_duplicate_logical_knowledge": after_second.get("knowledge_duplicate_logical_groups", 0) == 0,
        },
    }
    (output / "KET-QUA-F4-CLEAN.json").write_text(canonical_json(report), encoding="utf-8")
    return report


def _public_summary(report: dict[str, Any]) -> dict[str, Any]:
    candidate = report.get("candidate", {})
    final = candidate.get("after_second", {})
    return {
        "status": report.get("status"),
        "source_files_unchanged": report.get("source_files_unchanged"),
        "candidate_idempotent_no_change": candidate.get("idempotent_no_change"),
        "candidate_integrity_ok": final.get("integrity", {}).get("ok"),
        "candidate_no_posting_decisions": candidate.get("handoff_has_no_posting_decisions"),
        "candidate_no_duplicate_logical_knowledge": candidate.get("no_duplicate_logical_knowledge"),
        "candidate_no_active_knowledge_overlap": candidate.get("no_active_knowledge_overlap"),
        "knowledge_query_errors": candidate.get("knowledge_query_2026_08_15", {}).get("errors"),
        "candidate_schema_version": final.get("schema_version"),
        "main_exists": report.get("main_before", {}).get("exists"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="V9b F4 clean candidate builder (aggregate-only).")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "cau_hinh.that.toml")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--main-web", type=Path, default=DEFAULT_MAIN_WEB)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    try:
        report = build(args.config.resolve(), args.output.resolve(), args.main_web.resolve(), args.replace)
    except Exception as exc:
        # Do not allow a parser/source exception to leak any row or source content to stdout.
        print(canonical_json({"status": "FAILED", "error_type": type(exc).__name__}))
        return 1
    print(canonical_json(_public_summary(report)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
