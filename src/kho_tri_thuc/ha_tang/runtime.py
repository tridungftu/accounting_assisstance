from __future__ import annotations

import json
from pathlib import Path
from contextlib import contextmanager
from uuid import uuid4

from .primitives import DataError, canonical_json, instant_utc, local_business_date, now_utc, sha256, text_id
from .store import write_immutable


def uid():
    return str(uuid4())


def run_metadata(store):
    from .database import SCHEMA_VERSION
    root = Path(__file__).resolve().parents[1]
    sources = {path.relative_to(root).as_posix(): sha256(path.read_bytes()) for path in sorted(root.rglob("*.py"))}
    return {"schema_version": SCHEMA_VERSION, "config_hash": store.config.digest, "code_hash": sha256(canonical_json(sources).encode()), "code_files": sources,
            "runtime": "offline-" + store.config.environment}


@contextmanager
def transaction(store):
    if store.conn.in_transaction:
        raise RuntimeError("Nested transaction: use the internal method inside a transaction.")
    store.conn.execute("BEGIN IMMEDIATE")
    try:
        yield
        store.conn.commit()
    except BaseException:
        store.conn.rollback()
        raise


def log(store, module, action, subject, actor, at, details=None):
    store.conn.execute("INSERT INTO activity_log(module,action,subject_id,actor,event_at,recorded_at,details_json) VALUES (?,?,?,?,?,?,?)",
                       (module, action, subject, text_id(actor, "actor"), instant_utc(at), now_utc(), canonical_json(details or {})))


def artifact(store, content):
    digest = sha256(content)
    path = store.root / "raw" / (digest + ".bin")
    if not path.resolve().is_relative_to(store.root):
        raise DataError("UNSAFE_ARTIFACT_PATH", "Artifact nằm ngoài kho.")
    write_immutable(path, content)
    store.conn.execute("INSERT OR IGNORE INTO artifacts VALUES (?,?,?,?)", (digest, f"raw/{digest}.bin", len(content), now_utc()))
    return digest


def artifact_bytes(store, digest):
    row = store.conn.execute("SELECT relative_path FROM artifacts WHERE hash=?", (digest,)).fetchone()
    if not row:
        raise DataError("MISSING_ARTIFACT", "Thiếu artifact trong DB.")
    path = store.root / row[0]
    if not path.resolve().is_relative_to(store.root):
        raise DataError("UNSAFE_ARTIFACT_PATH", "Artifact nằm ngoài kho.")
    raw = path.read_bytes()
    if sha256(raw) != digest:
        raise DataError("ARTIFACT_CHANGED", "Artifact đã thay đổi.")
    return raw


def document(store, doc_id, cutoff=None):
    row = store.conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        raise DataError("DOCUMENT_NOT_FOUND", "Không tìm thấy chứng từ.")
    if cutoff is not None:
        evidence = store.conn.execute("SELECT 1 FROM evidence WHERE document_id=? AND scope_key='header' AND known_at<=? LIMIT 1", (doc_id, instant_utc(cutoff))).fetchone()
        if not evidence:
            raise DataError("FUTURE_OR_UNKNOWN_SOURCE", "Chứng từ chưa có bằng chứng đã biết tại cutoff.")
    result = {**dict(row), **json.loads(row["core_json"])}
    result["id"] = row["id"]
    result["lines"] = [json.loads(r[0]) for r in store.conn.execute("SELECT core_json FROM document_lines WHERE document_id=? ORDER BY line_key", (doc_id,))]
    if cutoff is not None:
        result["lines"] = [line for line in result["lines"] if store.conn.execute("SELECT 1 FROM evidence WHERE document_id=? AND scope_key=? AND known_at<=? LIMIT 1", (doc_id, "line:" + line["line_key"], instant_utc(cutoff))).fetchone()]
    return result


def source_bundle(store, attempt_id, cutoff):
    cutoff = instant_utc(cutoff)
    row = store.conn.execute("SELECT * FROM attempts WHERE id=? AND state='COMMITTED' AND source='junsky_xuat'", (attempt_id,)).fetchone()
    if not row:
        raise DataError("INVALID_SOURCE_BUNDLE", "Cần gói Junsky đã nạp hợp lệ.")
    manifest = json.loads(row["manifest_json"])
    if not row["known_at"] or row["known_at"] > cutoff or row["exported_at"] > cutoff or row["as_of"] > local_business_date(cutoff):
        raise DataError("FUTURE_OR_UNKNOWN_SNAPSHOT", "Snapshot chưa có tại cutoff.")
    ids = [r[0] for r in store.conn.execute("SELECT DISTINCT document_id FROM evidence WHERE attempt_id=? AND scope_key='header'", (attempt_id,))]
    docs = [document(store, i, cutoff) for i in ids]
    roles = {doc["kind"] for doc in docs}
    required = {"OPEN_ITEM", "COUNTERPARTY", "ACCOUNT", "EXPENSE", "PROJECT", "LOCK_PERIOD", "JOURNAL"}
    if not required <= roles:
        raise DataError("INCOMPLETE_BUNDLE", "Thiếu nhóm snapshot/danh mục/sổ bắt buộc.")
    return {"attempt_id": attempt_id, "hash": row["artifact_hash"], "manifest": manifest, "documents": docs}


def ensure_fixture_envelope(value, format_name):
    if not isinstance(value, dict) or value.get("format") != format_name or value.get("synthetic") is not True:
        raise DataError("FIXTURE_ONLY", f"Chỉ nhận {format_name}, synthetic=true.")
