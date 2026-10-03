"""Small explicit migrations; no ORM, no application state from M2-M6."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .primitives import DataError, now_utc, sha256

APPLICATION_ID = 0x4B545431
MIGRATIONS = (
    (
        """CREATE TABLE workspace_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)""",
        """CREATE TABLE config_history (hash TEXT PRIMARY KEY, contents BLOB NOT NULL, captured_at TEXT NOT NULL)""",
        """CREATE TABLE artifacts (
            hash TEXT PRIMARY KEY CHECK(length(hash)=64), relative_path TEXT NOT NULL UNIQUE,
            byte_length INTEGER NOT NULL CHECK(byte_length>=0), received_at TEXT NOT NULL)""",
        """CREATE TABLE attempts (
            id TEXT PRIMARY KEY, artifact_hash TEXT NOT NULL REFERENCES artifacts(hash),
            original_name TEXT NOT NULL, config_hash TEXT NOT NULL REFERENCES config_history(hash),
            parser_version TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN
            ('RECEIVED','STAGED','VALIDATED','COMMITTED','REJECTED')),
            started_at TEXT NOT NULL, finished_at TEXT, source TEXT, entity_id TEXT,
            as_of TEXT, exported_at TEXT, known_at TEXT, manifest_json TEXT, report_json TEXT)""",
        """CREATE TABLE source_records (
            id TEXT PRIMARY KEY, artifact_hash TEXT NOT NULL REFERENCES artifacts(hash),
            locator TEXT NOT NULL, raw_json TEXT NOT NULL, UNIQUE(artifact_hash, locator))""",
        """CREATE TABLE staging (
            attempt_id TEXT NOT NULL REFERENCES attempts(id), ordinal INTEGER NOT NULL,
            source_record_id TEXT NOT NULL REFERENCES source_records(id),
            PRIMARY KEY(attempt_id, ordinal))""",
        """CREATE TABLE documents (
            id TEXT PRIMARY KEY, entity_id TEXT NOT NULL, kind TEXT NOT NULL,
            natural_key TEXT NOT NULL, business_date TEXT NOT NULL, currency TEXT,
            amount_minor INTEGER, core_json TEXT NOT NULL, core_hash TEXT NOT NULL,
            first_attempt_id TEXT NOT NULL REFERENCES attempts(id),
            UNIQUE(entity_id,kind,natural_key))""",
        """CREATE TABLE issues (
            id INTEGER PRIMARY KEY, attempt_id TEXT NOT NULL REFERENCES attempts(id),
            locator TEXT NOT NULL, code TEXT NOT NULL, severity TEXT NOT NULL, message TEXT NOT NULL)""",
        """CREATE TABLE audit_events (
            id INTEGER PRIMARY KEY, at TEXT NOT NULL, action TEXT NOT NULL,
            attempt_id TEXT REFERENCES attempts(id), details_json TEXT NOT NULL)""",
    ),
    (
        """CREATE TABLE document_lines (
            id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
            line_key TEXT NOT NULL, amount_minor INTEGER NOT NULL,
            core_json TEXT NOT NULL, core_hash TEXT NOT NULL, UNIQUE(document_id,line_key))""",
        """CREATE TABLE evidence (
            id INTEGER PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
            source_record_id TEXT NOT NULL REFERENCES source_records(id),
            scope_key TEXT NOT NULL, known_at TEXT, known_at_basis TEXT,
            attempt_id TEXT NOT NULL REFERENCES attempts(id),
            UNIQUE(document_id,source_record_id,scope_key,attempt_id))""",
        "CREATE INDEX evidence_cutoff ON evidence(known_at,document_id)",
        "CREATE INDEX attempts_state ON attempts(state)",
    ),
)
from .feature_migrations import FEATURE_MIGRATIONS

MIGRATIONS = MIGRATIONS + FEATURE_MIGRATIONS
SCHEMA_VERSION = len(MIGRATIONS)


def migrate(conn: sqlite3.Connection, target: int = SCHEMA_VERSION) -> None:
    if not 1 <= target <= SCHEMA_VERSION:
        raise DataError("SCHEMA_VERSION", "Phiên bản schema đích không hỗ trợ.")
    conn.execute("BEGIN IMMEDIATE")
    try:
        app = conn.execute("PRAGMA application_id").fetchone()[0]
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        existing = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if app not in (0, APPLICATION_ID) or (app == 0 and (existing or version)):
            raise DataError("FOREIGN_DATABASE", "Không khởi tạo trên DB không thuộc ứng dụng.")
        if version > target:
            raise DataError("FUTURE_SCHEMA", "DB có schema mới hơn; không hạ phiên bản.")
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)")
        history = dict(conn.execute("SELECT version,checksum FROM schema_migrations"))
        if set(history) != set(range(1, version + 1)):
            raise DataError("MIGRATION_HISTORY", "Lịch sử migration không khớp user_version.")
        for index, statements in enumerate(MIGRATIONS[:target], 1):
            digest = sha256("\n".join(statements).encode())
            if index <= version:
                if history[index] != digest:
                    raise DataError("MIGRATION_CHANGED", "Migration đã áp dụng bị thay đổi.")
                continue
            for statement in statements:
                conn.execute(statement)
            conn.execute("INSERT INTO schema_migrations VALUES (?,?,?)", (index, digest, now_utc()))
            conn.execute(f"PRAGMA user_version={index}")
        conn.execute(f"PRAGMA application_id={APPLICATION_ID}")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=15000")
    try:
        migrate(conn)
        conn.execute("PRAGMA journal_mode=WAL")
    except BaseException:
        conn.close()
        raise
    return conn


def integrity(conn: sqlite3.Connection) -> dict:
    checks = [row[0] for row in conn.execute("PRAGMA integrity_check")]
    foreign_keys = [list(row) for row in conn.execute("PRAGMA foreign_key_check")]
    return {"ok": checks == ["ok"] and not foreign_keys, "integrity": checks, "foreign_keys": foreign_keys}
