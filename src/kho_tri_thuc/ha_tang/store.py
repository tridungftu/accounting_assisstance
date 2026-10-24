"""Atomic promotion, immutable evidence and conservative cross-file identity checks."""

from __future__ import annotations

import sqlite3
import os
import tempfile
import getpass
import io
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from .config import Config
from .database import SCHEMA_VERSION
from .ket_noi import engine_cua_ket_noi, integrity, mo_ket_noi
from .primitives import DataError, canonical_json, instant_utc, now_utc, sha256
from ..nguon.fixture import Adapter, Batch, FixtureAdapter, Issue, Record


STAGING_DIR = ".ktt-staging"


def write_immutable(path: Path, content: bytes) -> None:
    """Atomic, no-overwrite promotion. Tệp staging được GIỮ LẠI (thành công/lỗi/retry) trong `<thư mục đích>/.ktt-staging/` — không unlink;
    staging cùng filesystem nên os.link vẫn nguyên tử, đích không bị ghi đè."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise DataError("UNSAFE_RAW_PATH", "Không ghi artifact qua symbolic link.")
    staging = path.parent / STAGING_DIR
    if staging.is_symlink() or (staging.exists() and not staging.is_dir()):
        raise DataError("UNSAFE_RAW_PATH", "Thư mục staging không an toàn.")
    staging.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=staging, prefix=".raw-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        # Atomic creation without overwriting an existing content-addressed artifact.
        os.link(temporary, path)
    except FileExistsError:
        if path.is_symlink() or path.read_bytes() != content:
            raise DataError("ARTIFACT_CHANGED", "Artifact đã tồn tại nhưng nội dung khác; không ghi đè.")


def source_bytes(path: Path, extra_paths: tuple[Path, ...] = ()) -> bytes:
    """Create a deterministic local snapshot for a supplied file or directory."""
    path = Path(path)
    if path.is_file():
        return path.read_bytes()
    if not path.is_dir():
        raise DataError("SOURCE_PATH", "Đường dẫn nguồn không phải file hoặc thư mục.")
    root = path.resolve()
    entries: list[tuple[Path, str]] = []
    for child in sorted(path.rglob("*")):
        if not child.is_file():
            continue
        if child.is_symlink() or not child.resolve().is_relative_to(root):
            raise DataError("UNSAFE_SOURCE_PATH", "Không đóng gói symbolic link hoặc tệp ngoài thư mục nguồn.")
        entries.append((child, child.relative_to(path).as_posix()))
    sibling_root = path.parent.resolve()
    for child in extra_paths:
        child = Path(child)
        if not child.is_file() or child.is_symlink() or not child.resolve().is_relative_to(sibling_root):
            raise DataError("UNSAFE_SOURCE_PATH", "Tệp phụ thuộc nguồn không an toàn hoặc ngoài thư mục nguồn.")
        entries.append((child, "__dependent__/" + child.name))
    if not entries:
        raise DataError("EMPTY_SOURCE_DIRECTORY", "Thư mục nguồn không có tệp để nạp.")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for child, archive_name in entries:
            info = zipfile.ZipInfo(archive_name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, child.read_bytes())
    return output.getvalue()


class Store:
    def __init__(self, config: Config):
        self.config = config
        self.root = config.data_dir
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "kho.sqlite"
        if self.db_path.is_symlink() or not self.db_path.resolve().is_relative_to(self.root):
            raise DataError("UNSAFE_DATABASE_PATH", "DB không được trỏ ra ngoài kho đã cấu hình.")
        self.conn = mo_ket_noi(config, self.db_path)  # V13: sqlite (kho thật) hoặc postgres (kho thử) theo [storage]
        self.engine = engine_cua_ket_noi(self.conn)
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            existing = self.conn.execute("SELECT value FROM workspace_meta WHERE key='entity_id'").fetchone()
            if existing is not None and existing[0] != config.entity_id:
                raise DataError("WRONG_WORKSPACE", "DB thuộc entity khác; không đổi cấu hình để dùng chung.")
            self.conn.execute("INSERT OR IGNORE INTO workspace_meta VALUES ('entity_id',?)", (config.entity_id,))
            self.conn.execute("INSERT OR IGNORE INTO workspace_meta VALUES ('environment',?)", (config.environment,))
            self.conn.execute("INSERT OR IGNORE INTO config_history VALUES (?,?,?)", (config.digest, config.source_bytes, now_utc()))
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            self.conn.close()
            raise

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *_):
        self.conn.close()

    def _event(self, attempt: str, action: str, details: dict) -> None:
        details = {**details, "actor_os_user": getpass.getuser(), "process_id": os.getpid()}
        self.conn.execute("INSERT INTO audit_events(at,action,attempt_id,details_json) VALUES (?,?,?,?)",
                          (now_utc(), action, attempt, canonical_json(details)))

    def ingest(self, path: Path, adapter: Adapter | None = None) -> dict:
        adapter = adapter or FixtureAdapter()
        extras = tuple(getattr(adapter, "snapshot_paths", lambda: ())())
        content = source_bytes(path, extras)
        digest, attempt = sha256(content), str(uuid4())
        relative = f"raw/{digest}.bin"
        if not (self.root / relative).resolve().is_relative_to(self.root):
            raise DataError("UNSAFE_RAW_PATH", "Artifact không được trỏ ra ngoài kho đã cấu hình.")
        write_immutable(self.root / relative, content)
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            self.conn.execute("INSERT OR IGNORE INTO artifacts VALUES (?,?,?,?)", (digest, relative, len(content), now_utc()))
            self.conn.execute("INSERT INTO attempts(id,artifact_hash,original_name,config_hash,parser_version,state,started_at) VALUES (?,?,?,?,?,'RECEIVED',?)",
                              (attempt, digest, path.name, self.config.digest, adapter.version, now_utc()))
            self._event(attempt, "RECEIVED", {"artifact_hash": digest, "parser": adapter.version})
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise
        try:
            batch = adapter.read(content, self.config)
        except DataError as exc:
            return self._finish(attempt, digest, None, [Issue(exc.code, str(exc), exc.locator)], 0, 0, "REJECTED")
        source_record_ids = {}
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            for ordinal, raw in enumerate(batch.raw_records):
                locator = f"$.records[{ordinal}]"
                existing = self.conn.execute("SELECT id FROM source_records WHERE artifact_hash=? AND locator=?", (digest, locator)).fetchone()
                record_id = existing[0] if existing else str(uuid4())
                if not existing:
                    self.conn.execute("INSERT INTO source_records VALUES (?,?,?,?)", (record_id, digest, locator, canonical_json(raw)))
                self.conn.execute("INSERT INTO staging VALUES (?,?,?)", (attempt, ordinal, record_id))
                source_record_ids[ordinal] = record_id
            self.conn.execute("UPDATE attempts SET state='STAGED',source=?,entity_id=?,as_of=?,exported_at=?,known_at=?,manifest_json=? WHERE id=?",
                              (batch.source, batch.manifest["entity_id"], batch.manifest["as_of"], batch.manifest["exported_at"], batch.manifest["known_at"], canonical_json(batch.manifest), attempt))
            self._event(attempt, "STAGED", {"rows": len(batch.raw_records)})
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise
        record_errors = [issue for issue in batch.issues if issue.severity == "ERROR" and issue.locator.startswith("$.records[")]
        quarantined_ordinals = sorted({int(issue.locator.split("[", 1)[1].split("]", 1)[0]) for issue in record_errors})
        if not batch.valid:
            return self._finish(attempt, digest, batch, batch.issues, 0, 0, "REJECTED")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            for issue in record_errors:
                ordinal = int(issue.locator.split("[", 1)[1].split("]", 1)[0])
                source_record = source_record_ids.get(ordinal)
                if source_record is None:
                    continue
                raw = self.conn.execute("SELECT raw_json FROM source_records WHERE id=?", (source_record,)).fetchone()[0]
                self.conn.execute("INSERT OR IGNORE INTO quarantine_records VALUES (?,?,?,?,?)",
                                  (attempt, ordinal, issue.code, issue.message, sha256(raw.encode("utf-8"))))
            denominator = max(1, len(batch.raw_records))
            if len(quarantined_ordinals) / denominator > self.config.quarantine_max_ratio:
                self.conn.rollback()
                return self._finish(attempt, digest, batch, batch.issues, 0, 0, "REJECTED")
            self.conn.execute("UPDATE attempts SET state='VALIDATED' WHERE id=?", (attempt,))
            self._event(attempt, "VALIDATED", {"totals_minor": batch.totals})
            inserted = duplicate = 0
            for record in batch.records:
                if record.ordinal in quarantined_ordinals:
                    continue
                created = self._promote_record(record, batch, source_record_ids[record.ordinal], attempt)
                inserted += int(created)
                duplicate += int(not created)
            report = self._finish(attempt, digest, batch, batch.issues, inserted, duplicate, "COMMITTED", in_transaction=True)
            self.conn.commit()
            return report
        except Exception as exc:
            self.conn.rollback()
            if isinstance(exc, DataError):
                issue = Issue(exc.code, str(exc), exc.locator)
            else:
                issue = Issue("PROMOTION_FAILED", f"Lỗi {type(exc).__name__} khi promote; dữ liệu chuẩn đã rollback.")
            return self._finish(attempt, digest, batch, batch.issues + [issue], 0, 0, "REJECTED")

    def _promote_record(self, record: Record, batch: Batch, source_record: str, attempt: str) -> bool:
        core_json = canonical_json(record.core)
        core_hash = sha256(core_json.encode())
        existing = self.conn.execute("SELECT id,core_hash,core_json,amount_minor FROM documents WHERE entity_id=? AND kind=? AND natural_key=?",
                                     (self.config.entity_id, record.kind, record.key)).fetchone()
        if existing and existing["core_hash"] != core_hash:
            old_core = __import__("json").loads(existing["core_json"])
            if record.kind == "INVOICE":
                merged, warning = self._merge_invoice(old_core, record.core)
            elif record.kind == "JOURNAL":
                merged, warning = self._merge_journal_enrichment(old_core, record.core)
            else:
                raise DataError("IDENTITY_CONFLICT", "Cùng khóa nguồn nhưng dữ liệu khác; giữ staging để xác minh, không ghi đè.", f"$.records[{record.ordinal}]")
            if merged is None:
                raise DataError("IDENTITY_CONFLICT", "Cùng khóa nguồn có dữ liệu mâu thuẫn ngoài phạm vi bổ sung; giữ staging để xác minh.", f"$.records[{record.ordinal}]")
            core_json = canonical_json(merged)
            core_hash = sha256(core_json.encode())
            self.conn.execute("UPDATE documents SET core_json=?,core_hash=?,amount_minor=? WHERE id=?", (core_json, core_hash, record.amount_minor, existing["id"]))
        document_id = existing["id"] if existing else str(uuid4())
        if not existing:
            self.conn.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?)",
                              (document_id, self.config.entity_id, record.kind, record.key, record.business_date, record.currency,
                               record.amount_minor, core_json, core_hash, attempt))
        self._evidence(document_id, source_record, "header", batch, attempt)
        self._observation(document_id, source_record, batch, record.core, "WARNING_MONEY_CONFLICT" if existing and existing["amount_minor"] != record.amount_minor else "MATCHED")
        old_line_keys = {row[0] for row in self.conn.execute("SELECT line_key FROM document_lines WHERE document_id=?", (document_id,))}
        new_line_keys = {line["line_key"] for line in record.lines}
        if old_line_keys and new_line_keys and old_line_keys != new_line_keys:
            raise DataError("LINE_SET_CONFLICT", "Bộ dòng cùng chứng từ thay đổi; chưa xác minh revision.", f"$.records[{record.ordinal}].lines")
        for line in record.lines:
            line_json = canonical_json(line)
            digest = sha256(line_json.encode())
            old = self.conn.execute("SELECT core_hash FROM document_lines WHERE document_id=? AND line_key=?", (document_id, line["line_key"])).fetchone()
            if old and old[0] != digest:
                raise DataError("LINE_CONFLICT", "Cùng ID dòng nhưng nội dung khác; không ghi đè.", f"$.records[{record.ordinal}].lines")
            if not old:
                self.conn.execute("INSERT INTO document_lines VALUES (?,?,?,?,?,?)", (str(uuid4()), document_id, line["line_key"], line["amount_minor"], line_json, digest))
            self._evidence(document_id, source_record, "line:" + line["line_key"], batch, attempt)
        return existing is None

    @staticmethod
    def _merge_invoice(left: dict, right: dict) -> tuple[dict | None, bool]:
        """Merge XML and table observations only when their business header agrees.

        Source-specific status belongs to observations; no source silently wins.
        """
        identity = ("seller_tax_id", "series", "number", "invoice_type", "buyer_tax_id", "business_date", "currency")
        if any(left.get(k) != right.get(k) for k in identity):
            return None, False
        total_left, total_right = left.get("total_minor", left.get("amount_minor")), right.get("total_minor", right.get("amount_minor"))
        # A positive tolerance is explicit in the record; otherwise monetary differences are warnings, not merged facts.
        tolerance = max(int(left.get("tolerance_minor", 0)), int(right.get("tolerance_minor", 0)))
        warning = total_left != total_right and abs((total_left or 0) - (total_right or 0)) > tolerance
        merged = dict(left)
        for key in ("net_minor", "tax_minor", "total_minor", "tax_currency", "related_invoice_key", "invoice_relation", "tax_evidence"):
            if merged.get(key) is None and right.get(key) is not None:
                merged[key] = right[key]
        statuses = sorted({v for v in (left.get("source_status"), right.get("source_status")) if v})
        merged["source_statuses"] = statuses
        merged["merge_status"] = "WARNING_MONEY_CONFLICT" if warning else "MERGED"
        return merged, warning

    @staticmethod
    def _merge_journal_enrichment(left: dict, right: dict) -> tuple[dict | None, bool]:
        """Permit a reader upgrade to add missing journal evidence only.

        The journal natural key and its accounting lines remain immutable.  A
        later parser may fill formerly absent source columns such as `Nội dung`
        or bank-account metadata, but it must never replace a value already
        observed under the same key.
        """
        merged = dict(left)
        for key, value in right.items():
            if key not in merged or merged[key] in (None, ""):
                merged[key] = value
            elif value not in (None, "") and merged[key] != value:
                return None, False
        return merged, merged != left

    def _observation(self, document_id: str, source_record: str, batch: Batch, core: dict, status: str) -> None:
        self.conn.execute("""INSERT OR IGNORE INTO document_observations
            (document_id,source_record_id,source,observed_core_json,observed_hash,known_at,status) VALUES (?,?,?,?,?,?,?)""",
                          (document_id, source_record, batch.source, canonical_json(core), sha256(canonical_json(core).encode()), batch.manifest.get("known_at"), status))

    def _evidence(self, document_id: str, source_record: str, scope: str, batch: Batch, attempt: str) -> None:
        self.conn.execute("INSERT INTO evidence(document_id,source_record_id,scope_key,known_at,known_at_basis,attempt_id) VALUES (?,?,?,?,?,?)",
                          (document_id, source_record, scope, batch.manifest["known_at"], batch.manifest.get("known_at_basis"), attempt))

    def _finish(self, attempt: str, digest: str, batch: Batch | None, issues: list[Issue], inserted: int, duplicates: int, state: str, *, in_transaction: bool = False) -> dict:
        meta = self.conn.execute("SELECT original_name,parser_version FROM attempts WHERE id=?", (attempt,)).fetchone()
        report = {"attempt_id": attempt, "artifact_hash": digest, "fixture_only": self.config.environment == "fixture", "environment": self.config.environment, "state": state,
                  "original_file": meta["original_name"], "parser_version": meta["parser_version"],
                  "schema_version": SCHEMA_VERSION, "config_hash": self.config.digest,
                  "source": batch.source if batch else None, "input_records": len(batch.raw_records) if batch else None,
                  "inserted_documents": inserted, "duplicate_documents": duplicates,
                  "control_totals_minor": batch.totals if batch else {}, "controls": batch.controls if batch else {},
                  "issues": [asdict(issue) for issue in issues],
                  "quarantine": {"count": len({int(issue.locator.split("[", 1)[1].split("]", 1)[0]) for issue in issues if issue.severity == "ERROR" and issue.locator.startswith("$.records[")}),
                                 "by_code": dict(sorted(Counter(issue.code for issue in issues if issue.severity == "ERROR" and issue.locator.startswith("$.records[")).items())),
                                 "ordinals": sorted({int(issue.locator.split("[", 1)[1].split("]", 1)[0]) for issue in issues if issue.severity == "ERROR" and issue.locator.startswith("$.records[")})},
                  "meaning": "COMMITTED chỉ xác nhận nguồn đã vào kho cục bộ; không phải ghi sổ hoặc cho phép nhập Junsky."}
        if not in_transaction:
            self.conn.execute("BEGIN IMMEDIATE")
        try:
            for issue in issues:
                self.conn.execute("INSERT INTO issues(attempt_id,locator,code,severity,message) VALUES (?,?,?,?,?)",
                                  (attempt, issue.locator, issue.code, issue.severity, issue.message))
            self.conn.execute("UPDATE attempts SET state=?,finished_at=?,report_json=? WHERE id=?", (state, now_utc(), canonical_json(report), attempt))
            self._event(attempt, state, {"inserted": inserted, "duplicates": duplicates, "issue_count": len(issues)})
            if not in_transaction:
                self.conn.commit()
        except BaseException:
            if not in_transaction:
                self.conn.rollback()
            raise
        return report

    def status(self) -> dict:
        totals = defaultdict(int)
        import json
        for row in self.conn.execute("SELECT kind,currency,amount_minor,core_json FROM documents WHERE amount_minor IS NOT NULL"):
            snapshot = json.loads(row[3]).get("snapshot_id")
            totals[(row[0], row[1], snapshot or "")] += row[2]
        return {"fixture_only": self.config.environment == "fixture", "environment": self.config.environment, "schema_version": SCHEMA_VERSION, "entity_id": self.config.entity_id,
                "storage_engine": self.engine,
                "documents_by_kind": dict(self.conn.execute("SELECT kind,COUNT(*) FROM documents GROUP BY kind")),
                "document_amount_totals": [{"kind": kind, "currency": currency, "snapshot_id": snapshot or None, "amount_minor": amount} for (kind, currency, snapshot), amount in sorted(totals.items())],
                "totals_meaning": "Thống kê dữ liệu đã lưu theo loại/tiền tệ/snapshot; không phải số dư công nợ hiện tại.",
                "attempts_by_state": dict(self.conn.execute("SELECT state,COUNT(*) FROM attempts GROUP BY state")),
                "incomplete_attempts": [row[0] for row in self.conn.execute("SELECT id FROM attempts WHERE state NOT IN ('COMMITTED','REJECTED')")],
                "workflow": {
                    "sessions_by_state": dict(self.conn.execute("SELECT state,COUNT(*) FROM sessions GROUP BY state")),
                    "batches_by_state": dict(self.conn.execute("SELECT CASE WHEN cancelled_at IS NOT NULL THEN 'ABORTED_BEFORE_PUBLICATION' ELSE state END AS status,COUNT(*) FROM export_batches GROUP BY status")),
                    "proposals_by_state": dict(self.conn.execute("SELECT state,COUNT(*) FROM proposals GROUP BY state")),
                    "label_versions": self.conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0],
                    "closed_fixture_months": [r[0] for r in self.conn.execute("SELECT month FROM month_closures ORDER BY month")],
                    "real_operation_gate": "NO_GO_REAL_DATA",
                },
                "integrity": integrity(self.conn)}

    def report(self, attempt_id: str | None = None) -> dict:
        row = self.conn.execute("SELECT report_json FROM attempts WHERE id=?", (attempt_id,)).fetchone() if attempt_id else self.conn.execute("SELECT report_json FROM attempts WHERE report_json IS NOT NULL ORDER BY rowid DESC LIMIT 1").fetchone()
        if not row or row[0] is None:
            raise DataError("REPORT_NOT_FOUND", "Chưa có báo cáo hoàn tất cho lần nạp này.")
        import json
        return json.loads(row[0])

    def quarantined(self, attempt_id: str) -> dict:
        if self.config.environment != "that":
            raise DataError("THAT_REQUIRED", "Chỉ xem cách ly trong kho that.")
        rows = self.conn.execute("""SELECT q.ordinal,q.code,q.message,q.raw_hash,s.raw_json
            FROM quarantine_records q JOIN staging st ON st.attempt_id=q.attempt_id AND st.ordinal=q.ordinal
            JOIN source_records s ON s.id=st.source_record_id
            WHERE q.attempt_id=? ORDER BY q.ordinal,q.code""", (attempt_id,)).fetchall()
        import json
        records = []
        for row in rows:
            raw = json.loads(row[4])
            identifier = raw.get("voucher_number") or raw.get("number") or raw.get("request_id") or raw.get("item_id") or raw.get("reference")
            amount = raw.get("amount") or raw.get("total_amount")
            records.append({"ordinal": row[0], "code": row[1], "message": row[2], "raw_hash": row[3],
                            "business_date": raw.get("business_date") or raw.get("document_date"),
                            "document_reference": identifier, "amount": amount})
        return {"attempt_id": attempt_id, "environment": "that", "count": len(records), "records": records}

    def bank_documents(self, start: str, end: str, *, without_proposal: bool = False) -> dict:
        if self.config.environment != "that":
            raise DataError("THAT_REQUIRED", "Chỉ liệt kê sao kê trong kho that.")
        from .primitives import date_iso
        start, end = date_iso(start), date_iso(end)
        if end < start:
            raise DataError("DATE_RANGE", "--den phải không trước --tu.")
        rows = self.conn.execute("""SELECT d.id,d.business_date,d.amount_minor,d.core_json,
            EXISTS(SELECT 1 FROM proposals p WHERE p.bank_id=d.id AND p.state NOT IN ('CANCELLED')) AS has_proposal
            FROM documents d WHERE d.kind='BANK' AND d.business_date>=? AND d.business_date<=?
            ORDER BY d.business_date,d.id""", (start, end)).fetchall()
        import json
        records = []
        for row in rows:
            if without_proposal and row[4]:
                continue
            core = json.loads(row[3])
            records.append({"id": row[0], "business_date": row[1], "reference": core.get("reference"),
                            "direction": "IN" if row[2] > 0 else "OUT", "has_proposal": bool(row[4])})
        return {"environment": "that", "from": start, "to": end, "count": len(records), "records": records}

    def visible_documents(self, cutoff: str) -> list[dict]:
        """M1 evidence availability only; not an approved-knowledge/backtest engine."""
        cutoff = instant_utc(cutoff)
        rows = self.conn.execute("""SELECT d.* FROM documents d WHERE EXISTS
            (SELECT 1 FROM evidence e WHERE e.document_id=d.id AND e.scope_key='header'
             AND e.known_at IS NOT NULL AND e.known_at<=?)""", (cutoff,))
        return [dict(row) for row in rows]
