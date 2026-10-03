from __future__ import annotations

import json

from ..de_xuat.engine import Engine, FIELDS, item_key
from ..ha_tang.primitives import DataError, canonical_json, instant_utc, money_minor, text_id
from ..ha_tang.runtime import document, log, source_bundle, transaction, uid


class Sessions:
    def __init__(self, store):
        self.store, self.db, self.engine = store, store.conn, Engine(store)

    def get(self, session_id, active=False):
        row = self.db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        if not row or (active and row["state"] != "OPEN"):
            raise DataError("SESSION_NOT_OPEN", "Phiên không tồn tại hoặc không còn mở.")
        return dict(row)

    def open(self, attempt_id, bank_ids, cutoff, actor, mode="fixture"):
        cutoff = instant_utc(cutoff)
        if mode not in {"fixture", "shadow", "backtest"} or not isinstance(bank_ids, list) or not bank_ids or len(set(bank_ids)) != len(bank_ids):
            raise DataError("SESSION_ARGUMENTS", "Mode/danh sách sao kê không hợp lệ.")
        with transaction(self.store):
            if self.db.execute("SELECT 1 FROM sessions WHERE state IN ('OPEN','PREPARING')").fetchone():
                raise DataError("SESSION_ALREADY_OPEN", "Phiên trước chưa chốt/hủy hoặc đang phục hồi xuất.")
            bound_mode = self.db.execute("SELECT value FROM workspace_meta WHERE key='run_mode'").fetchone()
            if bound_mode and bound_mode[0] != mode:
                raise DataError("MODE_ISOLATION", "Dùng kho dữ liệu riêng cho fixture/shadow/backtest.")
            records = [document(self.store, i, cutoff) for i in bank_ids]
            if not self.db.execute("SELECT 1 FROM attempts WHERE id=? AND state='COMMITTED'", (attempt_id,)).fetchone():
                raise DataError("INVALID_SOURCE_ATTEMPT", "Lần nạp nguồn của phiên chưa COMMITTED.")
            if any(record["kind"] not in {"BANK", "INVOICE", "BASE"} for record in records):
                raise DataError("SESSION_DOCUMENT_KIND", "Phiên chỉ nhận sao kê, hóa đơn hoặc đề nghị Base.")
            has_bank = any(record["kind"] == "BANK" for record in records)
            bundle = source_bundle(self.store, attempt_id, cutoff) if has_bank else None
            if bundle and bundle["manifest"].get("posting_evidence_complete") is not True:
                raise DataError("POSTING_SCOPE_UNKNOWN", "Chưa xác nhận phạm vi sổ đủ kiểm tra đã ghi sổ.")
            previous = self.db.execute("SELECT closed_at FROM sessions WHERE state='CLOSED' ORDER BY closed_at DESC LIMIT 1").fetchone()
            if bundle and previous and bundle["manifest"]["exported_at"] < previous[0]:
                raise DataError("STALE_BUNDLE", "Cần xuất lại bộ nguồn sau phiên đã chốt.")
            if bundle and any(record["kind"] == "BANK" and record["business_date"] > bundle["manifest"]["as_of"] for record in records):
                raise DataError("BANK_SCOPE", "Snapshot không bao phủ ngày sao kê.")
            for record in records:
                if self.db.execute("SELECT 1 FROM month_closures WHERE month=?", (record["business_date"][:7],)).fetchone():
                    raise DataError("MONTH_CLOSED", "Tháng đã khóa trong kho fixture.")
                if self.db.execute("SELECT 1 FROM proposals WHERE bank_id=? AND state IN ('EXPORTED','VERIFIED','RECONCILED')", (record["id"],)).fetchone():
                    raise DataError("BANK_ALREADY_EXPORTED", "Giao dịch đã xuất ở phiên trước; cần xác minh/điều chỉnh, không xuất lại.")
            cat = self.engine.catalog(max(record["business_date"] for record in records), cutoff)
            if bundle:
                for entry in bundle["documents"]:
                    if entry["kind"] in {"COUNTERPARTY", "ACCOUNT", "EXPENSE", "PROJECT"}:
                        approved = cat.get((entry["kind"], entry["code"]))
                        if not approved or approved["payload"].get("name") != entry["name"]:
                            raise DataError("CATALOG_CHANGE_PENDING", "Mã mới/đổi tên trong snapshot chưa khớp danh mục được duyệt.")
            knowledge_ids = sorted({r["id"] for record in records for r in self.engine.knowledge.query(record["business_date"], cutoff)})
            identifier = uid()
            self.db.execute("INSERT OR IGNORE INTO workspace_meta VALUES ('run_mode',?)", (mode,))
            snapshot_id = bundle["manifest"]["snapshot_id"] if bundle else "DOCUMENTS_" + attempt_id
            self.db.execute("INSERT INTO sessions VALUES (?,?, 'OPEN',?,?,?,?,?,?,?,NULL,NULL)", (identifier, mode, cutoff, attempt_id, snapshot_id, canonical_json(bank_ids), canonical_json(knowledge_ids), text_id(actor), cutoff))
            log(self.store, "M3", "OPEN_SESSION", identifier, actor, cutoff, {"source_attempt": attempt_id, "mode": mode, "document_count": len(bank_ids), "document_kinds": sorted({record["kind"] for record in records})})
        return self.get(identifier)

    def assert_current(self, session, at):
        at = instant_utc(at)
        if at < session["cutoff"]:
            raise DataError("TIME_REVERSED", "Thời điểm thao tác trước cutoff phiên.")
        newer = self.db.execute("SELECT 1 FROM attempts WHERE source='junsky_xuat' AND state='COMMITTED' AND rowid>(SELECT rowid FROM attempts WHERE id=?) AND artifact_hash<>(SELECT artifact_hash FROM attempts WHERE id=?)", (session["source_attempt_id"], session["source_attempt_id"])).fetchone()
        changed = self.db.execute("SELECT 1 FROM knowledge_events WHERE event_at>? AND event_at<=?", (session["cutoff"], at)).fetchone()
        if newer or changed:
            raise DataError("SESSION_INPUT_CHANGED", "Nguồn/tri thức đã thay đổi; rà soát và mở lại phiên với bộ mới trước duyệt/xuất.")

    def available(self, item, session, exclude_proposal=None):
        consumed = 0
        for row in self.db.execute("""SELECT a.amount_minor,a.state,p.id,p.state AS proposal_state,s.snapshot_id
            FROM allocations a JOIN proposals p ON p.id=a.proposal_id JOIN sessions s ON s.id=p.session_id
            WHERE a.item_key=? AND a.state<>'CANCELLED'""", (item_key(item),)):
            if row["id"] == exclude_proposal:
                continue
            if row["state"] == "POSTED" and row["proposal_state"] == "RECONCILED" and row["snapshot_id"] != session["snapshot_id"]:
                continue
            consumed += row["amount_minor"]
        return max(0, abs(item["amount_minor"]) - consumed)

    def propose(self, session_id, baseline="A"):
        if baseline not in {"A", "B"}:
            raise DataError("BASELINE", "Baseline phải là A hoặc B.")
        with transaction(self.store):
            session = self.get(session_id, True)
            document_ids = json.loads(session["bank_ids_json"])
            records = [document(self.store, document_id, session["cutoff"]) for document_id in document_ids]
            bundle = source_bundle(self.store, session["source_attempt_id"], session["cutoff"]) if any(record["kind"] == "BANK" for record in records) else {"manifest": {}, "documents": []}
            results = []
            for record in records:
                existing = self.db.execute("SELECT * FROM proposals WHERE session_id=? AND bank_id=?", (session_id, record["id"])).fetchone()
                if existing:
                    results.append({"id": existing["id"], **json.loads(existing["payload_json"])})
                    continue
                payload = self.engine.preview(record, bundle, session["cutoff"], baseline, lambda item: self.available(item, session))
                identifier = uid()
                self.db.execute("INSERT INTO proposals(id,session_id,bank_id,revision,state,payload_json,created_at,lines_json) VALUES (?,?,?,1,'PROPOSED',?,?,?)", (identifier, session_id, record["id"], canonical_json(payload), session["cutoff"], canonical_json(payload.get("lines", []))))
                for allocation in payload["allocations"]:
                    self.db.execute("INSERT INTO allocations VALUES (?,?,?,?,?,'RESERVED')", (uid(), identifier, allocation["open_item_id"], allocation["item_key"], allocation["amount_minor"]))
                log(self.store, "M3", "PROPOSE", identifier, session["actor"], session["cutoff"], {"completeness": payload["completeness"]})
                results.append({"id": identifier, **payload})
        return results

    def validate_decision(self, proposal, fields, allocations, at):
        session = self.get(proposal["session_id"], True)
        self.assert_current(session, at)
        record = document(self.store, proposal["bank_id"], session["cutoff"])
        bundle = source_bundle(self.store, session["source_attempt_id"], session["cutoff"]) if record["kind"] == "BANK" else {"manifest": {}, "documents": []}
        original = json.loads(proposal["payload_json"])
        hard = {"LOCKED_PERIOD", "ALREADY_POSTED_OR_DUPLICATE_REFERENCE", "POSTING_EVIDENCE_AMBIGUOUS", "IDENTIFIER_CONFLICT", "ZERO_AMOUNT", "NO_UNIQUE_APPROVED_TEMPLATE",
                "TEMPLATE_IDENTIFIER_CONFLICT", "CASE_CONFLICT", "POLICY_ORDER_COLLISION", "POLICY_PARTITION_CONFLICT", "MIXED_POLICY_CONTRACTS", "MULTILINE_TEMPLATE_REQUIRES_REVIEW", "MULTILINE_TAX_EVIDENCE_WAIT", "MULTILINE_UNBALANCED"}
        if hard.intersection(original["constraints"]) or (record["kind"] == "BANK" and "policy" not in original):
            raise DataError("HARD_CONSTRAINT", "Đề xuất có ràng buộc chặn; không thể duyệt bằng sửa Excel.")
        required = original.get("policy", {}).get("required_fields") or (["counterparty", "debit_account", "credit_account"] if record["kind"] != "BANK" else [])
        errors = self.engine.validate_fields(fields, record["business_date"], at, required)
        if errors:
            raise DataError("INVALID_DECISION_FIELDS", ", ".join(errors))
        if set(fields) != set(FIELDS):
            raise DataError("DECISION_FIELDS", "Bộ trường quyết định không đúng contract.")
        if record["kind"] != "BANK":
            if allocations:
                raise DataError("NON_BANK_ALLOCATION", "Hóa đơn/Base không dùng phân bổ công nợ của sao kê.")
            return {"bank_id": record["id"], "document_id": record["id"], "source_kind": record["kind"], "business_date": record["business_date"], "amount_minor": record["amount_minor"], "currency": record["currency"],
                    "fields": fields, "allocations": [], "context": original.get("context", {}), "template_id": original.get("template_id"), "required_fields": required,
                    "lines": original.get("lines", []), "contract_version": original.get("contract_version", 3)}
        direction = "OUT" if record["amount_minor"] < 0 else "IN"
        expected_account = fields["debit_account"] if direction == "OUT" else fields["credit_account"]
        item_ids = set()
        validated = []
        for request in allocations:
            item = next((d for d in bundle["documents"] if d["id"] == request["open_item_id"] and d["kind"] == "OPEN_ITEM"), None)
            value = money_minor(request["amount_minor"])
            if not item or item["id"] in item_ids or value <= 0 or item["currency"] != record["currency"] or item["counterparty"] != fields["counterparty"] or item["account"] != expected_account or item["item_type"] != "INVOICE":
                raise DataError("INVALID_ALLOCATION", "Phân bổ sai công nợ/đối tượng/TK/tiền tệ hoặc bị lặp.")
            if (direction == "OUT" and item["amount_minor"] >= 0) or (direction == "IN" and item["amount_minor"] <= 0):
                raise DataError("ALLOCATION_DIRECTION", "Sai chiều công nợ.")
            if value > self.available(item, session, proposal["id"]):
                raise DataError("OVER_ALLOCATION", "Phân bổ vượt số còn mở sau giữ chỗ.")
            item_ids.add(item["id"])
            validated.append({"open_item_id": item["id"], "item_key": item_key(item), "invoice_reference": item["invoice_reference"], "amount_minor": value})
        total = sum(a["amount_minor"] for a in validated)
        if (original["policy"]["needs_open_item"] and total != abs(record["amount_minor"])) or (not original["policy"]["needs_open_item"] and total != 0):
            raise DataError("ALLOCATION_TOTAL", "Tiền phân bổ chưa khớp sao kê hoặc mẫu không dùng công nợ.")
        return {"bank_id": record["id"], "business_date": record["business_date"], "amount_minor": record["amount_minor"], "currency": record["currency"],
                "bank_reference": record["reference"], "bank_account": record["account"], "fields": fields, "allocations": validated,
                "context": original["context"], "template_id": original["template_id"], "required_fields": original["policy"]["required_fields"],
                "lines": original.get("lines", []), "contract_version": original.get("contract_version", 2)}

    def cancel(self, session_id, actor, at, reason):
        with transaction(self.store):
            session = self.get(session_id, True)
            self.db.execute("UPDATE sessions SET state='CANCELLED',closed_at=?,reason=? WHERE id=?", (instant_utc(at), text_id(reason), session_id))
            self.db.execute("UPDATE allocations SET state='CANCELLED' WHERE proposal_id IN (SELECT id FROM proposals WHERE session_id=?)", (session_id,))
            self.db.execute("UPDATE proposals SET state='CANCELLED' WHERE session_id=?", (session_id,))
            log(self.store, "M3", "CANCEL_SESSION", session_id, actor, at, {"reason": reason})
        return self.get(session_id)
