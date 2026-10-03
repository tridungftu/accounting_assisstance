from __future__ import annotations

import json
from pathlib import Path

from . import excel
from ..de_xuat.engine import FIELDS
from ..ha_tang.primitives import DataError, canonical_json, instant_utc, money_minor, sha256, text_id
from ..ha_tang.runtime import artifact, artifact_bytes, document, log, source_bundle, transaction, uid
from ..ha_tang.store import write_immutable
from ..trang_thai.service import Sessions

FIELD_COLUMNS = {"counterparty": "doi_tuong", "debit_account": "tk_no", "credit_account": "tk_co", "project": "du_an", "expense": "khoan_muc"}
IMMUTABLE = ["proposal_id", "bank_id", "proposal_revision", "decision_revision", "ngay", "dien_giai", "so_tien", "goi_y"]
REVIEW_HEADERS = IMMUTABLE + list(FIELD_COLUMNS.values()) + ["quyet_dinh", "ly_do"]
ALLOC_IMMUTABLE = ["proposal_id", "open_item_id", "so_hoa_don", "doi_tuong", "tai_khoan", "so_con_mo"]
ALLOC_HEADERS = ALLOC_IMMUTABLE + ["tien_duyet"]
OTHER_ALLOC_HEADERS = ["proposal_id", "open_item_id", "tien_duyet"]


class ReviewExport:
    def __init__(self, store):
        self.store, self.db, self.sessions = store, store.conn, Sessions(store)

    def ui_rows(self, session_id: str, at: str) -> list[dict]:
        """Return review-safe rows for the local UI from the same proposal data as Excel."""
        session = self.sessions.get(session_id, True)
        self.sessions.assert_current(session, at)
        rows = []
        for proposal in self.db.execute("SELECT * FROM proposals WHERE session_id=? ORDER BY bank_id", (session_id,)):
            source = document(self.store, proposal["bank_id"], session["cutoff"])
            payload = json.loads(proposal["payload_json"])
            latest = self.db.execute("SELECT * FROM decisions WHERE proposal_id=? ORDER BY revision DESC LIMIT 1", (proposal["id"],)).fetchone()
            display = source.get("description") or source.get("request_name") or "; ".join(str(line.get("description", "")) for line in source.get("lines", [])[:3])
            rows.append({"proposal_id": proposal["id"], "revision": proposal["revision"], "decision_revision": latest["revision"] if latest else 0,
                         "state": proposal["state"], "document_id": source["id"], "source_kind": source["kind"], "business_date": source["business_date"],
                         "display_text": display or "(không có diễn giải nguồn)", "amount_minor": source.get("amount_minor"),
                         "fields": json.loads(latest["payload_json"])["fields"] if latest and latest["action"] == "APPROVE" else payload["fields"],
                         "lines": payload.get("lines", []), "constraints": payload.get("constraints", []), "warnings": payload.get("warnings", []),
                         "confidence": payload.get("confidence", {}), "why": {"template_id": payload.get("template_id"), "stages": payload.get("stages", [])}})
        return rows

    def decide_from_ui(self, session_id: str, items: list[dict], actor: str, at: str) -> dict:
        """Apply explicit browser decisions through the same session validation as Excel.

        The UI supplies codes selected from the approved catalog; this method
        never creates a decision for a row the reviewer left untouched.
        """
        at = instant_utc(at)
        if not isinstance(items, list) or not items:
            raise DataError("EMPTY_UI_DECISION", "Chọn ít nhất một dòng có quyết định rõ.")
        with transaction(self.store):
            session = self.sessions.get(session_id, True)
            self.sessions.assert_current(session, at)
            applied = []
            seen = set()
            for item in items:
                if not isinstance(item, dict) or set(item) - {"proposal_id", "action", "fields", "reason"}:
                    raise DataError("UI_DECISION_FORMAT", "Dòng duyệt trên màn hình không đúng cấu trúc.")
                proposal_id, action = item.get("proposal_id"), item.get("action")
                if not isinstance(proposal_id, str) or proposal_id in seen or action not in {"APPROVE", "REJECT"}:
                    raise DataError("UI_DECISION_FORMAT", "Mỗi dòng chỉ có một quyết định Duyệt hoặc Từ chối.")
                seen.add(proposal_id)
                proposal = self.db.execute("SELECT * FROM proposals WHERE id=? AND session_id=?", (proposal_id, session_id)).fetchone()
                if not proposal:
                    raise DataError("UNKNOWN_PROPOSAL", "Dòng đề xuất không thuộc phiên đang mở.")
                previous = self.db.execute("SELECT COALESCE(MAX(revision),0) FROM decisions WHERE proposal_id=?", (proposal_id,)).fetchone()[0]
                fields = item.get("fields")
                if not isinstance(fields, dict) or set(fields) != set(FIELDS):
                    raise DataError("DECISION_FIELDS", "Cần đủ đúng năm trường định khoản khi duyệt trên màn hình.")
                if any(value is not None and not isinstance(value, str) for value in fields.values()):
                    raise DataError("TEXT_CODE_REQUIRED", "Mã chọn trên màn hình phải là chuỗi từ danh mục đã duyệt.")
                original = json.loads(proposal["payload_json"])
                reason = item.get("reason", "")
                if not isinstance(reason, str):
                    raise DataError("REASON_REQUIRED", "Ghi chú quyết định phải là văn bản.")
                changed = fields != original["fields"]
                if (action == "REJECT" or changed) and not reason.strip():
                    raise DataError("REASON_REQUIRED", "Sửa hoặc từ chối cần nêu lý do.")
                self.db.execute("UPDATE allocations SET state='CANCELLED' WHERE proposal_id=?", (proposal_id,))
                payload = self.sessions.validate_decision(proposal, fields, [], at) if action == "APPROVE" else {"fields": fields, "allocations": [], "bank_id": proposal["bank_id"]}
                decision_id = uid()
                self.db.execute("""INSERT INTO decisions(id,proposal_id,revision,action,payload_json,reason,actor,decided_at,lines_json)
                    VALUES (?,?,?,?,?,?,?,?,?)""", (decision_id, proposal_id, previous + 1, action, canonical_json(payload), reason.strip(), text_id(actor), at, canonical_json(payload.get("lines", []))))
                self.db.execute("UPDATE proposals SET state=? WHERE id=?", ("APPROVED" if action == "APPROVE" else "REJECTED", proposal_id))
                log(self.store, "M4", "UI_REVIEW_DECISION", decision_id, actor, at, {"proposal_id": proposal_id, "revision": previous + 1, "action": action, "changed": changed})
                applied.append(decision_id)
        return {"session_id": session_id, "decision_ids": applied, "applied": len(applied), "fixture_only": self.store.config.environment == "fixture"}

    def review_workbook(self, session_id, actor, at):
        at = instant_utc(at)
        with transaction(self.store):
            session = self.sessions.get(session_id, True)
            self.sessions.assert_current(session, at)
            proposals = list(self.db.execute("SELECT * FROM proposals WHERE session_id=? ORDER BY bank_id", (session_id,)))
            if len(proposals) != len(json.loads(session["bank_ids_json"])):
                raise DataError("MISSING_PROPOSALS", "Cần tạo đề xuất cho các dòng sao kê trước khi xuất workbook duyệt.")
            bundle = source_bundle(self.store, session["source_attempt_id"], session["cutoff"])
            review_rows, allocation_rows = [], []
            for proposal in proposals:
                bank = document(self.store, proposal["bank_id"])
                payload = json.loads(proposal["payload_json"])
                previous = self.db.execute("SELECT * FROM decisions WHERE proposal_id=? ORDER BY revision DESC LIMIT 1", (proposal["id"],)).fetchone()
                selected = json.loads(previous["payload_json"])["fields"] if previous and previous["action"] == "APPROVE" else payload["fields"]
                row = dict(zip(IMMUTABLE, [proposal["id"], bank["id"], str(proposal["revision"]), str(previous["revision"] if previous else 0), bank["business_date"], bank["description"], str(bank["amount_minor"]), canonical_json(payload["fields"])]))
                row.update({column: selected.get(field) or "" for field, column in FIELD_COLUMNS.items()})
                row.update(quyet_dinh="WAIT", ly_do="")
                review_rows.append(row)
                reserved = {r["open_item_id"]: r["amount_minor"] for r in self.db.execute("SELECT * FROM allocations WHERE proposal_id=? AND state<>'CANCELLED'", (proposal["id"],))}
                ranked = [candidate["open_item_id"] for candidate in payload.get("candidates", [])]
                shortlist = set(ranked[:self.store.config.review_candidate_limit]) | set(reserved)
                for item in sorted((d for d in bundle["documents"] if d["kind"] == "OPEN_ITEM" and d["id"] in shortlist), key=lambda d: (ranked.index(d["id"]) if d["id"] in ranked else len(ranked), d["id"])):
                    allocation_rows.append(dict(zip(ALLOC_HEADERS, [proposal["id"], item["id"], item.get("invoice_reference") or "", item["counterparty"], item["account"], str(item["amount_minor"]), str(reserved.get(item["id"], 0))])))
            identifier = uid()
            meta = {"format": "ktt-review-v2", "workbook_id": identifier, "session_id": session_id, "entity_id": self.store.config.entity_id,
                    "candidate_limit": str(self.store.config.review_candidate_limit), "warning": "KHÔNG DÙNG IMPORT JUNSKY"}
            wb = excel.workbook()
            excel.table(wb, "META", ["key", "value"], list(meta.items()))
            ws = excel.table(wb, "DUYET", REVIEW_HEADERS, [[row[h] for h in REVIEW_HEADERS] for row in review_rows])
            for column in ("A", "B", "C", "D", "H"):
                ws.column_dimensions[column].hidden = True
            from openpyxl.worksheet.datavalidation import DataValidation
            selector = DataValidation(type="list", formula1='"WAIT,APPROVE,REJECT"', allow_blank=False)
            selector.errorTitle = "Quyết định không hợp lệ"
            selector.error = "Chọn WAIT, APPROVE hoặc REJECT cho từng chứng từ."
            selector.showErrorMessage = True
            ws.add_data_validation(selector)
            selector.add(f"N2:N{len(review_rows) + 1}")
            excel.table(wb, "PHAN_BO", ALLOC_HEADERS, [[row[h] for h in ALLOC_HEADERS] for row in allocation_rows])
            excel.table(wb, "CONG_NO_KHAC", OTHER_ALLOC_HEADERS, [])
            raw = excel.to_bytes(wb)
            digest = artifact(self.store, raw)
            baseline = {"meta": meta, "rows": review_rows, "allocations": allocation_rows, "other_allocations": []}
            self.db.execute("INSERT INTO review_workbooks VALUES (?,?,?,?,?,?)", (identifier, session_id, canonical_json(baseline), digest, at, text_id(actor)))
            log(self.store, "M4", "REVIEW_WORKBOOK", identifier, actor, at, {"session_id": session_id, "artifact": digest})
        path = self.store.root / "reviews" / (identifier + ".xlsx")
        write_immutable(path, raw)
        return {"workbook_id": identifier, "path": str(path), "fixture_only": self.store.config.environment == "fixture", "rows": len(review_rows), "candidate_limit": self.store.config.review_candidate_limit}

    def import_review(self, path, actor, at):
        raw, at = Path(path).read_bytes(), instant_utc(at)
        digest = sha256(raw)
        old = self.db.execute("SELECT result_json FROM review_imports WHERE artifact_hash=?", (digest,)).fetchone()
        if old:
            return {**json.loads(old[0]), "replayed": True}
        wb = excel.load(raw)
        try:
            if set(wb.sheetnames) != {"META", "DUYET", "PHAN_BO", "CONG_NO_KHAC"}:
                raise DataError("WORKBOOK_SHEETS", "Workbook sai tập sheet.")
            metadata_rows = excel.rows(wb, "META", ["key", "value"])
            meta = {r["key"]: r["value"] for r in metadata_rows}
            row = self.db.execute("SELECT * FROM review_workbooks WHERE id=?", (meta.get("workbook_id"),)).fetchone()
            if not row:
                raise DataError("UNKNOWN_WORKBOOK", "Workbook không được tạo từ kho hiện tại.")
            baseline = json.loads(row["baseline_json"])
            if meta != baseline["meta"] or len(meta) != len(metadata_rows):
                raise DataError("WORKBOOK_METADATA", "Metadata/ID phiên của workbook bị sửa.")
            decisions = excel.rows(wb, "DUYET", REVIEW_HEADERS)
            allocations = excel.rows(wb, "PHAN_BO", ALLOC_HEADERS)
            other_allocations = excel.rows(wb, "CONG_NO_KHAC", OTHER_ALLOC_HEADERS)
            def same_immutable(current, original, keys, identity):
                a = {tuple(r[k] for k in identity): r for r in current}
                b = {tuple(r[k] for k in identity): r for r in original}
                if len(a) != len(current) or set(a) != set(b) or any(any(a[key][field] != b[key][field] for field in keys) for key in a):
                    raise DataError("WORKBOOK_IMMUTABLE", "Dòng bị thêm/xóa/lặp hoặc cột khóa/bất biến bị sửa.")
            same_immutable(decisions, baseline["rows"], IMMUTABLE, ["proposal_id"])
            same_immutable(allocations, baseline["allocations"], ALLOC_IMMUTABLE, ["proposal_id", "open_item_id"])
            if any(not row["proposal_id"] or not row["open_item_id"] for row in other_allocations):
                raise DataError("OTHER_ALLOCATION_FIELDS", "CONG_NO_KHAC cần proposal_id và open_item_id cho từng dòng.")
            with transaction(self.store):
                session = self.sessions.get(row["session_id"], True)
                self.sessions.assert_current(session, at)
                actions = []
                for decision in decisions:
                    action = decision["quyet_dinh"]
                    if action not in {"WAIT", "APPROVE", "REJECT"}:
                        raise DataError("INVALID_DECISION", "Quyết định phải là WAIT/APPROVE/REJECT từng chứng từ.")
                    proposal = self.db.execute("SELECT * FROM proposals WHERE id=? AND session_id=?", (decision["proposal_id"], session["id"])).fetchone()
                    latest = self.db.execute("SELECT COALESCE(MAX(revision),0) FROM decisions WHERE proposal_id=?", (proposal["id"],)).fetchone()[0]
                    if str(latest) != decision["decision_revision"] or str(proposal["revision"]) != decision["proposal_revision"]:
                        raise DataError("STALE_WORKBOOK", "Workbook cũ so với phiên bản đề xuất/quyết định hiện tại.")
                    if action != "WAIT":
                        actions.append((decision, proposal, latest + 1))
                # Release all edited rows first, then validate the new allocation set atomically.
                for _, proposal, _ in actions:
                    self.db.execute("UPDATE allocations SET state='CANCELLED' WHERE proposal_id=?", (proposal["id"],))
                applied = []
                for decision, proposal, revision in actions:
                    fields = {}
                    for field, column in FIELD_COLUMNS.items():
                        value = decision[column]
                        if value != "" and not isinstance(value, str):
                            raise DataError("TEXT_CODE_REQUIRED", "Mã trong Excel phải là chuỗi, giữ số 0 đầu.")
                        fields[field] = value or None
                    requested = []
                    for allocation in allocations + other_allocations:
                        if allocation["proposal_id"] == proposal["id"]:
                            value = money_minor(allocation["tien_duyet"] or "0")
                            if value < 0:
                                raise DataError("NEGATIVE_ALLOCATION", "Tiền phân bổ phải không âm.")
                            if value:
                                requested.append({"open_item_id": allocation["open_item_id"], "amount_minor": value})
                    original = json.loads(proposal["payload_json"])
                    changed = fields != original["fields"] or [(a["open_item_id"], a["amount_minor"]) for a in requested] != [(a["open_item_id"], a["amount_minor"]) for a in original["allocations"]]
                    reason = decision["ly_do"]
                    if (changed or decision["quyet_dinh"] == "REJECT") and not reason:
                        raise DataError("REASON_REQUIRED", "Sửa/từ chối cần lý do; không tự dựng bộ bảy mã lý do gốc.")
                    if not isinstance(reason, str):
                        raise DataError("REASON_REQUIRED", "Lý do phải là văn bản.")
                    payload = self.sessions.validate_decision(proposal, fields, requested, at) if decision["quyet_dinh"] == "APPROVE" else {"fields": fields, "allocations": [], "bank_id": proposal["bank_id"]}
                    decision_id = uid()
                    self.db.execute("""INSERT INTO decisions(id,proposal_id,revision,action,payload_json,reason,actor,decided_at,lines_json)
                        VALUES (?,?,?,?,?,?,?,?,?)""", (decision_id, proposal["id"], revision, decision["quyet_dinh"], canonical_json(payload), reason, text_id(actor), at, canonical_json(payload.get("lines", []))))
                    if decision["quyet_dinh"] == "APPROVE":
                        for allocation in payload["allocations"]:
                            self.db.execute("""INSERT INTO allocations VALUES (?,?,?,?,?,'APPROVED')
                                ON CONFLICT(proposal_id,open_item_id) DO UPDATE SET amount_minor=excluded.amount_minor,state='APPROVED'""",
                                            (uid(), proposal["id"], allocation["open_item_id"], allocation["item_key"], allocation["amount_minor"]))
                    self.db.execute("UPDATE proposals SET state=? WHERE id=?", ("APPROVED" if decision["quyet_dinh"] == "APPROVE" else "REJECTED", proposal["id"]))
                    log(self.store, "M4", "REVIEW_DECISION", decision_id, actor, at, {"proposal_id": proposal["id"], "revision": revision, "action": decision["quyet_dinh"], "reason": reason})
                    applied.append(decision_id)
                artifact(self.store, raw)
                result = {"fixture_only": self.store.config.environment == "fixture", "workbook_id": row["id"], "decision_ids": applied, "applied": len(applied), "pending": len(decisions) - len(applied), "replayed": False}
                self.db.execute("INSERT INTO review_imports VALUES (?,?,?,?,?)", (digest, row["id"], canonical_json(result), at, actor))
                return result
        finally:
            wb.close()

    def export(self, session_id, actor, at, target="fixture"):
        if target != "fixture":
            raise DataError("JUNSKY_MAPPING_MISSING", "Chưa có template/EntryID/DebtID/Entry2 xác nhận; xuất Junsky thật bị chặn.")
        at = instant_utc(at)
        existing = self.db.execute("SELECT id FROM export_batches WHERE session_id=?", (session_id,)).fetchone()
        if existing:
            return self.recover(existing[0], actor, at)
        with transaction(self.store):
            session = self.sessions.get(session_id, True)
            self.sessions.assert_current(session, at)
            proposals = list(self.db.execute("SELECT * FROM proposals WHERE session_id=?", (session_id,)))
            if not proposals or any(p["state"] not in {"APPROVED", "REJECTED"} for p in proposals):
                raise DataError("REVIEW_INCOMPLETE", "Cần duyệt/từ chối từng chứng từ trước chốt phiên.")
            batch_id, export_rows, pending, expected = uid(), [], [], {}
            for proposal in proposals:
                if proposal["state"] == "REJECTED":
                    continue
                decision = self.db.execute("SELECT * FROM decisions WHERE proposal_id=? ORDER BY revision DESC LIMIT 1", (proposal["id"],)).fetchone()
                if decision["decided_at"] > at:
                    raise DataError("EXPORT_BEFORE_APPROVAL", "Không thể xuất ở thời điểm trước quyết định duyệt.")
                payload = json.loads(decision["payload_json"])
                payload = self.sessions.validate_decision(proposal, payload["fields"], payload["allocations"], at)
                item_id = uid()
                pending.append((item_id, proposal, decision, payload))
                export_rows.append([item_id, payload["bank_reference"], str(abs(payload["amount_minor"])), *[payload["fields"][field] or "" for field in FIELDS], canonical_json(payload["allocations"])])
                for allocation in payload["allocations"]:
                    source = document(self.store, allocation["open_item_id"])
                    movement = allocation["amount_minor"] if payload["amount_minor"] < 0 else -allocation["amount_minor"]
                    entry = expected.setdefault(allocation["item_key"], {"id": source["id"], "before": source["amount_minor"], "delta": 0})
                    entry["delta"] += movement
            if not pending:
                raise DataError("NOTHING_TO_EXPORT", "Không có chứng từ được duyệt; có thể hủy phiên với lý do.")
            wb = excel.workbook()
            excel.table(wb, "CANH_BAO", ["noi_dung"], [["FIXTURE — KHÔNG IMPORT JUNSKY"], ["Không phải schema CB_tmpEntry1/2"], [batch_id]])
            excel.table(wb, "FIXTURE_HEADER", ["item_id", "bank_reference", "amount_minor", *FIELDS, "allocations_json"], export_rows)
            ledger_rows = []
            for item_id, _, _, payload in pending:
                if payload.get("lines"):
                    ledger_rows += [[item_id, line["line_id"], line["account"], str(line["debit_minor"]), str(line["credit_minor"])] for line in payload["lines"]]
                else:
                    amount = str(abs(payload["amount_minor"]))
                    ledger_rows += [[item_id, "1", payload["fields"]["debit_account"], amount, "0"], [item_id, "2", payload["fields"]["credit_account"], "0", amount]]
            excel.table(wb, "FIXTURE_LINES", ["item_id", "line_id", "account", "debit_minor", "credit_minor"], ledger_rows)
            raw = excel.to_bytes(wb)
            check = excel.load(raw)
            try:
                lines = excel.rows(check, "FIXTURE_LINES", ["item_id", "line_id", "account", "debit_minor", "credit_minor"])
                if sum(money_minor(r["debit_minor"]) - money_minor(r["credit_minor"]) for r in lines) != 0:
                    raise DataError("UNBALANCED_EXPORT", "Batch fixture không cân Nợ/Có.")
            finally:
                check.close()
            digest = artifact(self.store, raw)
            manifest = {"format": "ktt-export-fixture-v1", "batch_id": batch_id, "session_id": session_id, "fixture_only": True,
                        "xlsx_sha256": digest, "items": [p[0] for p in pending], "count": len(pending), "mapping": "INTERNAL_FIXTURE_NOT_JUNSKY"}
            manifest_hash = artifact(self.store, canonical_json(manifest).encode())
            relative = f"exports/{batch_id}/FIXTURE_KHONG_IMPORT_JUNSKY.xlsx"
            self.db.execute("INSERT INTO export_batches(id,session_id,state,target,artifact_hash,manifest_hash,relative_path,prepared_at,exported_at,actor) VALUES (?,?,'PREPARING','fixture',?,?,?,?,NULL,?)", (batch_id, session_id, digest, manifest_hash, relative, at, text_id(actor)))
            for item_id, proposal, decision, payload in pending:
                lines = payload.get("lines", [])
                line_checksum = sha256(canonical_json(lines).encode())
                self.db.execute("INSERT INTO export_items(id,batch_id,proposal_id,decision_id,payload_json,line_checksum) VALUES (?,?,?,?,?,?)", (item_id, batch_id, proposal["id"], decision["id"], canonical_json(payload), line_checksum))
                for ordinal, line in enumerate(lines, 1):
                    self.db.execute("""INSERT INTO export_item_lines
                        (id,export_item_id,line_no,account,debit_minor,credit_minor,tax_rate,tax_basis,state,payload_json,line_hash)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (uid(), item_id, ordinal, line["account"], line["debit_minor"], line["credit_minor"], line.get("tax_rate"), line.get("tax_basis"), line.get("state", "READY"), canonical_json(line), sha256(canonical_json(line).encode())))
            for key, value in expected.items():
                self.db.execute("INSERT INTO expected_balances VALUES (?,?,?,?,?,?)", (batch_id, key, value["id"], value["before"], value["delta"], value["before"] + value["delta"]))
            self.db.execute("UPDATE sessions SET state='PREPARING' WHERE id=?", (session_id,))
            log(self.store, "M4", "PREPARE_EXPORT", batch_id, actor, at, manifest)
        return self.recover(batch_id, actor, at)

    def _publish(self, batch):
        target = self.store.root / batch["relative_path"]
        if not target.resolve().is_relative_to(self.store.root):
            raise DataError("UNSAFE_EXPORT_PATH", "Đường dẫn xuất nằm ngoài kho.")
        write_immutable(target, artifact_bytes(self.store, batch["artifact_hash"]))
        write_immutable(target.parent / "manifest.json", artifact_bytes(self.store, batch["manifest_hash"]))
        return target

    def recover(self, batch_id, actor, at):
        batch = self.db.execute("SELECT * FROM export_batches WHERE id=?", (batch_id,)).fetchone()
        if not batch:
            raise DataError("BATCH_NOT_FOUND", "Không tìm thấy batch.")
        source_changed = False
        with transaction(self.store):
            current = self.db.execute("SELECT * FROM export_batches WHERE id=?", (batch_id,)).fetchone()
            if current["cancelled_at"]:
                raise DataError("EXPORT_CANCELLED", "Batch đã hủy trước công bố; không phục hồi/xuất lại batch này.")
            if instant_utc(at) < current["prepared_at"]:
                raise DataError("EXPORT_TIME", "Thời điểm phục hồi trước lúc chuẩn bị batch.")
            if current["state"] == "PREPARING":
                session = self.sessions.get(batch["session_id"])
                try:
                    self.sessions.assert_current(session, at)
                except DataError as exc:
                    published = self.store.root / current["relative_path"]
                    if exc.code != "SESSION_INPUT_CHANGED" or not published.is_file() or sha256(published.read_bytes()) != current["artifact_hash"]:
                        raise
                    # The exact original workbook already exists: finish bookkeeping,
                    # preserve identity, and require reconciliation. No new decisions.
                    source_changed = True
            path = self._publish(current)
            if sha256(path.read_bytes()) != current["artifact_hash"]:
                raise DataError("EXPORT_CHECKSUM", "File xuất không khớp checksum.")
            if current["state"] == "PREPARING":
                self.db.execute("UPDATE export_batches SET state='EXPORTED',exported_at=? WHERE id=?", (instant_utc(at), batch_id))
                self.db.execute("UPDATE proposals SET state='EXPORTED' WHERE id IN (SELECT proposal_id FROM export_items WHERE batch_id=?)", (batch_id,))
                self.db.execute("UPDATE allocations SET state='EXPORTED' WHERE state='APPROVED' AND proposal_id IN (SELECT proposal_id FROM export_items WHERE batch_id=?)", (batch_id,))
                self.db.execute("UPDATE sessions SET state='CLOSED',closed_at=? WHERE id=?", (instant_utc(at), batch["session_id"]))
                log(self.store, "M4", "EXPORT_COMPLETED", batch_id, actor, at, {"artifact": batch["artifact_hash"], "source_changed_after_publication": source_changed})
        return {"batch_id": batch_id, "state": self.db.execute("SELECT state FROM export_batches WHERE id=?", (batch_id,)).fetchone()[0], "path": str(path), "fixture_only": True, "export_does_not_confirm_posting": True, "source_changed_after_publication": source_changed}

    def cancel_prepared(self, batch_id, actor, at, reason):
        at, actor, reason = instant_utc(at), text_id(actor), text_id(reason)
        with transaction(self.store):
            batch = self.db.execute("SELECT * FROM export_batches WHERE id=?", (batch_id,)).fetchone()
            if not batch or batch["state"] != "PREPARING" or at < batch["prepared_at"]:
                raise DataError("CANNOT_CANCEL_EXPORT", "Chỉ hủy batch chưa hoàn tất công bố.")
            path = self.store.root / batch["relative_path"]
            if path.exists() or (path.parent / "manifest.json").exists():
                raise DataError("EXPORT_ALREADY_PUBLISHED", "Đã có file công bố; giữ ID batch và phục hồi/đối soát, không giải phóng để xuất lại.")
            if batch["cancelled_at"]:
                return {"batch_id": batch_id, "state": "ABORTED_BEFORE_PUBLICATION", "fixture_only": True}
            self.db.execute("UPDATE export_batches SET cancelled_at=?,cancelled_by=?,cancellation_reason=? WHERE id=?", (at, actor, reason, batch_id))
            self.db.execute("UPDATE allocations SET state='CANCELLED' WHERE proposal_id IN (SELECT id FROM proposals WHERE session_id=?)", (batch["session_id"],))
            self.db.execute("UPDATE proposals SET state='CANCELLED' WHERE session_id=?", (batch["session_id"],))
            self.db.execute("UPDATE sessions SET state='CANCELLED',closed_at=?,reason=? WHERE id=?", (at, reason, batch["session_id"]))
            log(self.store, "M4", "ABORT_BEFORE_PUBLICATION", batch_id, actor, at, {"reason": reason})
        return {"batch_id": batch_id, "state": "ABORTED_BEFORE_PUBLICATION", "fixture_only": True}
