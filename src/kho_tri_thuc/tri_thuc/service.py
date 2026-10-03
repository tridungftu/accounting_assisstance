from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from ..ha_tang.primitives import DataError, canonical_json, date_iso, instant_utc, intervals_overlap, natural_key, normalize_text, sha256, text_id, valid_interval
from ..ha_tang.runtime import artifact, document, log, transaction, uid
from ..ha_tang.store import write_immutable
from ..xuat import excel
from .matching import expiry_exclusive, validate_payload
from .expiry import configured_valid_to

CATEGORIES = {"CATALOG", "POLICY", "CASE", "STATISTICS", "RULE", "GROUP", "KEYWORD", "HARD_KEY", "EXCEPTION", "INVOICE_TREE", "SOURCE_POLICY_ROW", "INVOICE_KEYWORD", "INVOICE_POLICY"}
KB_HEADERS = ["category", "logical_key", "valid_from", "valid_to", "known_at", "payload_json", "evidence_json", "supersedes_id"]


class Knowledge:
    def __init__(self, store, *, cache_enabled=True):
        self.store, self.db = store, store.conn
        self.cache_enabled = cache_enabled
        self._cache = {}
        self._cache_epoch = None

    def _snapshot(self, category, cutoff):
        # Epoch is transactional: also detects other connections and rollback.
        epoch = self.db.execute("SELECT revision FROM knowledge_epoch WHERE id=1").fetchone()[0]
        if epoch != self._cache_epoch:
            self._cache.clear()
            self._cache_epoch = epoch
        key = (category, cutoff)
        if self.cache_enabled and key in self._cache:
            return self._cache[key]
        if category is None:
            rows = [dict(r) for r in self.db.execute("SELECT * FROM knowledge_versions ORDER BY category,logical_key,revision")]
        else:
            rows = [dict(r) for r in self.db.execute("SELECT * FROM knowledge_versions WHERE category=? ORDER BY logical_key,revision", (category,))]
        events = {r[0]: (bool(r[1]), bool(r[2])) for r in self.db.execute("""SELECT version_id,
            MAX(action='APPROVE'), MAX(action='REVOKE') FROM knowledge_events WHERE event_at<=? GROUP BY version_id""", (cutoff,))}
        for row in rows:
            row['payload'] = json.loads(row['payload_json'])
        value = (rows, events, {r['id']: r for r in rows})
        if self.cache_enabled:
            if len(self._cache) >= 64:
                self._cache.clear()
            self._cache[key] = value
        return value

    def _stage(self, item, actor, at):
        category = text_id(item.get("category"), "category")
        if category not in CATEGORIES:
            raise DataError("KNOWLEDGE_CATEGORY", "Nhóm tri thức không hợp lệ.")
        key = text_id(item.get("logical_key"), "logical_key")
        start, end = valid_interval(item.get("valid_from"), item.get("valid_to"))
        known = instant_utc(item.get("known_at"))
        if known > instant_utc(at):
            raise DataError("FUTURE_KNOWLEDGE", "Không nạp tri thức được biết sau thời điểm khai báo thao tác.")
        payload, evidence = item.get("payload"), item.get("evidence")
        if not isinstance(payload, dict) or not isinstance(evidence, list) or not evidence or any(not isinstance(e, str) or not e for e in evidence):
            raise DataError("KNOWLEDGE_EVIDENCE", "Tri thức cần payload object và bằng chứng.")
        validate_payload(category, payload)
        if 'expiry_policy' in payload and configured_valid_to(payload) != end:
            raise DataError('EXPIRY_MAPPING', 'valid_to không khớp cấu hình hạn dùng và lần cuối.')
        if 'expiry_policy' not in payload and payload.get("contract_version") == 2 and "expiry_raw" in payload and expiry_exclusive(payload["expiry_raw"]) != end:
            raise DataError("EXPIRY_MAPPING", "valid_to phải là ngày kế tiếp hạn dùng gốc.")
        if category == "CATALOG":
            for name in ("kind", "code"):
                text_id(payload.get(name), name)
        if category == "POLICY":
            for name in ("template_id", "direction", "partition"):
                text_id(payload.get(name), name)
            if payload["direction"] not in ("IN", "OUT") or type(payload.get("needs_open_item")) is not bool:
                raise DataError("POLICY_CONTRACT", "Mẫu thiếu chiều thu/chi hoặc needs_open_item.")
            if not isinstance(payload.get("required_fields"), list) or not set(payload["required_fields"]) <= {"counterparty", "debit_account", "credit_account", "project", "expense"}:
                raise DataError("POLICY_CONTRACT", "Trường bắt buộc của mẫu không hợp lệ.")
        digest = sha256(canonical_json({"payload": payload, "from": start, "to": end, "known": known, "evidence": evidence, "supersedes": item.get("supersedes_id")}).encode())
        existing = self.db.execute("SELECT id FROM knowledge_versions WHERE category=? AND logical_key=? AND content_hash=?", (category, key, digest)).fetchone()
        if existing:
            return existing[0]
        if category == "POLICY" and payload.get("contract_version") == 2:
            for other in self.db.execute("""SELECT valid_from,valid_to FROM knowledge_versions
                WHERE category='POLICY' AND json_extract(payload_json,'$.contract_version')=2
                AND json_extract(payload_json,'$.partition')=? AND json_extract(payload_json,'$.tier')=?
                AND json_extract(payload_json,'$.order')=? AND logical_key<>?""",
                (payload['partition'], payload['tier'], payload['order'], key)):
                if intervals_overlap((start, end), (other["valid_from"], other["valid_to"])):
                    raise DataError("POLICY_ORDER_COLLISION", "Hai mẫu có cùng thứ tự trong phân vùng và khoảng hiệu lực chồng nhau.")
        supersedes = item.get("supersedes_id")
        if supersedes:
            previous = self.db.execute("SELECT * FROM knowledge_versions WHERE id=?", (supersedes,)).fetchone()
            if not previous or previous["category"] != category or previous["logical_key"] != key:
                raise DataError("INVALID_SUPERSESSION", "Bản thay thế phải cùng nhóm/khóa tri thức.")
        revision = self.db.execute("SELECT COALESCE(MAX(revision),0)+1 FROM knowledge_versions WHERE category=? AND logical_key=?", (category, key)).fetchone()[0]
        identifier = uid()
        self.db.execute("INSERT INTO knowledge_versions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (identifier, category, key, revision, canonical_json(payload), digest, start, end, known, canonical_json(evidence), supersedes, instant_utc(at), text_id(actor)))
        log(self.store, "M2", "STAGE", identifier, actor, at, {"category": category, "key": key, "revision": revision})
        return identifier

    def stage_many(self, items, actor, at):
        if not isinstance(items, list) or not items:
            raise DataError("EMPTY_KNOWLEDGE", "Cần danh sách tri thức không rỗng.")
        with transaction(self.store):
            return [self._stage(item, actor, at) for item in items]

    def _approved(self, row, cutoff):
        approved = self.db.execute("SELECT event_at FROM knowledge_events WHERE version_id=? AND action='APPROVE' AND event_at<=? ORDER BY event_at LIMIT 1", (row["id"], cutoff)).fetchone()
        revoked = self.db.execute("SELECT 1 FROM knowledge_events WHERE version_id=? AND action='REVOKE' AND event_at<=?", (row["id"], cutoff)).fetchone()
        return bool(approved and not revoked and row["known_at"] <= cutoff)

    def query(self, business_date, cutoff, category=None, *, include_pending=False):
        business_date, cutoff = date_iso(business_date), instant_utc(cutoff)
        all_rows, events, by_id = self._snapshot(category, cutoff)
        eligible = [r for r in all_rows if r["valid_from"] <= business_date and (r["valid_to"] is None or business_date < r["valid_to"]) and r['known_at'] <= cutoff and (events.get(r['id']) == (True, False) or (include_pending and r['id'] not in events))]
        # An approved replacement carves out its validity interval even if later revoked.
        replaced = set()
        for row in all_rows:
            if row["known_at"] <= cutoff and row["valid_from"] <= business_date and (row["valid_to"] is None or business_date < row["valid_to"]) and events.get(row['id'], (False, False))[0]:
                ancestor = row["supersedes_id"]
                while ancestor:
                    replaced.add(ancestor)
                    prior = by_id.get(ancestor)
                    ancestor = prior["supersedes_id"] if prior else None
        # Never mutate a cached snapshot.  `approval_state` is a view value;
        # adding it in place made later calls such as `expired()` depend on
        # whether `query()` had already been called on this Knowledge object.
        # Every value of a version row is a scalar except ``payload``.  A fresh
        # payload parsed from its stored JSON is the same independent copy
        # deepcopy() produced, at a fraction of the cost (V10: deepcopy of the
        # whole catalogue dominated proposal time).
        results = []
        for r in eligible:
            if r["id"] in replaced:
                continue
            row = dict(r)
            row["payload"] = json.loads(r["payload_json"])
            results.append(row)
        identities = [(r["category"], r["logical_key"]) for r in results]
        if len(identities) != len(set(identities)):
            raise DataError("KNOWLEDGE_OVERLAP", "Nhiều phiên bản tri thức cùng có hiệu lực.")
        for row in results:
            row["approval_state"] = "APPROVED" if events.get(row["id"]) == (True, False) else "PENDING"
        return results

    def approve(self, identifier, actor, at):
        at = instant_utc(at)
        with transaction(self.store):
            row = self.db.execute("SELECT * FROM knowledge_versions WHERE id=?", (identifier,)).fetchone()
            if not row or row["known_at"] > at:
                raise DataError("UNKNOWN_KNOWLEDGE", "Không có phiên bản đủ điều kiện duyệt.")
            if self.db.execute("SELECT 1 FROM knowledge_events WHERE version_id=? AND action='REVOKE'", (identifier,)).fetchone():
                raise DataError("REVOKED_VERSION", "Bản thu hồi không được duyệt lại; tạo phiên bản mới.")
            if self.db.execute("SELECT 1 FROM knowledge_events WHERE version_id=? AND action='APPROVE'", (identifier,)).fetchone():
                return identifier
            payload = json.loads(row["payload_json"])
            if payload.get("requires_evaluation"):
                reports = [json.loads(r[0]) for r in self.db.execute("SELECT report_json FROM quality_runs WHERE created_at<=?", (at,))]
                if not any(identifier in r.get("evaluated_candidate_ids", []) and r.get("candidate_gate_passed") is True for r in reports):
                    raise DataError("CANDIDATE_NOT_EVALUATED", "Đề cử học chưa có kiểm chứng tác động đạt điều kiện.")
            ancestors = set()
            ancestor = row["supersedes_id"]
            while ancestor:
                ancestors.add(ancestor)
                previous = self.db.execute("SELECT supersedes_id FROM knowledge_versions WHERE id=?", (ancestor,)).fetchone()
                ancestor = previous[0] if previous else None
            for other in self.db.execute("SELECT * FROM knowledge_versions WHERE category=? AND logical_key=? AND id<>?", (row["category"], row["logical_key"], identifier)):
                if self._approved(other, at) and intervals_overlap((row["valid_from"], row["valid_to"]), (other["valid_from"], other["valid_to"])):
                    if other["id"] not in ancestors:
                        raise DataError("KNOWLEDGE_OVERLAP", "Hiệu lực chồng lấn; cần khai báo bản được thay thế.")
            self.db.execute("INSERT INTO knowledge_events(version_id,action,event_at,actor,reason) VALUES (?,'APPROVE',?,?,?)", (identifier, at, text_id(actor), "Phê duyệt thủ công trong môi trường fixture"))
            log(self.store, "M2", "APPROVE", identifier, actor, at)
        return identifier

    def expired(self, business_date, cutoff, category="POLICY"):
        """Only approved, already-known expired versions are explanatory evidence."""
        business_date, cutoff = date_iso(business_date), instant_utc(cutoff)
        rows, events, _ = self._snapshot(category, cutoff)
        return deepcopy([r for r in rows if r['valid_to'] is not None and r['valid_to'] <= business_date and r['known_at'] <= cutoff and events.get(r['id']) == (True, False)])

    def revoke(self, identifier, actor, at, reason, allow_pending=False):
        at, reason = instant_utc(at), text_id(reason, "reason")
        with transaction(self.store):
            row = self.db.execute("SELECT * FROM knowledge_versions WHERE id=?", (identifier,)).fetchone()
            if not row or row["known_at"] > at:
                raise DataError("NOT_APPROVED", "Phiên bản không tồn tại hoặc chưa được biết tại thời điểm thu hồi.")
            if not allow_pending and not self._approved(row, at):
                raise DataError("NOT_APPROVED", "Phiên bản chưa được duyệt tại thời điểm thu hồi.")
            if self.db.execute("SELECT 1 FROM knowledge_events WHERE version_id=? AND action='REVOKE'", (identifier,)).fetchone():
                return identifier
            self.db.execute("INSERT INTO knowledge_events(version_id,action,event_at,actor,reason) VALUES (?,'REVOKE',?,?,?)", (identifier, at, actor, reason))
            log(self.store, "M2", "REVOKE", identifier, actor, at, {"reason": reason})

    def resolve_identifier(self, identifier_type, value, business_date, cutoff, *, include_pending=False):
        value = normalize_text(value) if identifier_type == "ALIAS" else value
        matches = []
        for row in self.query(business_date, cutoff, "CATALOG", include_pending=include_pending):
            p = row["payload"]
            if p.get("kind") == "IDENTIFIER" and p.get("identifier_type") == identifier_type and (p.get("verified") is True or include_pending):
                candidate = normalize_text(p.get("value", "")) if identifier_type == "ALIAS" else p.get("value")
                if candidate == value:
                    matches.append({"counterparty": p["counterparty"], "knowledge_id": row["id"],
                                    "verified": p.get("verified") is True, "reliability": p.get("reliability"),
                                    "source_status": p.get("source_status"), "approval_state": row.get("approval_state", "PENDING")})
        parties = {m["counterparty"] for m in matches}
        return {"status": "UNIQUE" if len(parties) == 1 else "CONFLICT" if parties else "UNKNOWN", "matches": matches}

    def resolve_identifiers(self, pairs, business_date, cutoff, *, include_pending=False):
        """resolve_identifier() for several (type, value) pairs with one catalogue query."""
        wanted = {}
        for identifier_type, value in pairs:
            wanted.setdefault(identifier_type, set()).add(normalize_text(value) if identifier_type == "ALIAS" else value)
        found = {(identifier_type, value): [] for identifier_type, values in wanted.items() for value in values}
        for row in self.query(business_date, cutoff, "CATALOG", include_pending=include_pending):
            p = row["payload"]
            identifier_type = p.get("identifier_type")
            if p.get("kind") != "IDENTIFIER" or identifier_type not in wanted or not (p.get("verified") is True or include_pending):
                continue
            candidate = normalize_text(p.get("value", "")) if identifier_type == "ALIAS" else p.get("value")
            if candidate in wanted[identifier_type]:
                found[(identifier_type, candidate)].append({"counterparty": p["counterparty"], "knowledge_id": row["id"],
                                                             "verified": p.get("verified") is True, "reliability": p.get("reliability"),
                                                             "source_status": p.get("source_status"), "approval_state": row.get("approval_state", "PENDING")})
        result = {}
        for identifier_type, value in pairs:
            key = (identifier_type, normalize_text(value) if identifier_type == "ALIAS" else value)
            matches = found.get(key, [])
            parties = {m["counterparty"] for m in matches}
            result[(identifier_type, value)] = {"status": "UNIQUE" if len(parties) == 1 else "CONFLICT" if parties else "UNKNOWN", "matches": [dict(m) for m in matches]}
        return result

    def export_pending(self, path, actor, at):
        data = [r for r in self.db.execute("SELECT * FROM knowledge_versions") if not self.db.execute("SELECT 1 FROM knowledge_events WHERE version_id=?", (r["id"],)).fetchone()]
        wb = excel.workbook()
        excel.table(wb, "META", ["key", "value"], [["format", "ktt-knowledge-fixture-v1"], ["warning", "FIXTURE — KHÔNG PHẢI TỪ ĐIỂN GỐC"]])
        excel.table(wb, "CHO_DUYET", KB_HEADERS, [[r["category"], r["logical_key"], r["valid_from"], r["valid_to"] or "", r["known_at"], r["payload_json"], r["evidence_json"], r["supersedes_id"] or ""] for r in data])
        content = excel.to_bytes(wb)
        with transaction(self.store):
            digest = artifact(self.store, content)
            log(self.store, "M2", "EXPORT_PENDING", digest, actor, at, {"count": len(data)})
        write_immutable(Path(path), content)
        return {"path": str(path), "rows": len(data), "fixture_only": True}

    def import_workbook(self, path, actor, at):
        raw = Path(path).read_bytes()
        wb = excel.load(raw)
        try:
            meta = {r["key"]: r["value"] for r in excel.rows(wb, "META", ["key", "value"])}
            if meta.get("format") != "ktt-knowledge-fixture-v1" or set(wb.sheetnames) != {"META", "CHO_DUYET"}:
                raise DataError("KNOWLEDGE_WORKBOOK", "Không phải workbook tri thức fixture.")
            items = []
            for row in excel.rows(wb, "CHO_DUYET", KB_HEADERS):
                try:
                    items.append({"category": row["category"], "logical_key": row["logical_key"], "valid_from": row["valid_from"], "valid_to": row["valid_to"] or None,
                                  "known_at": row["known_at"], "payload": json.loads(row["payload_json"]), "evidence": json.loads(row["evidence_json"]), "supersedes_id": row["supersedes_id"] or None})
                except (ValueError, TypeError) as exc:
                    raise DataError("KNOWLEDGE_JSON", "Payload/bằng chứng trong Excel không hợp lệ.") from exc
            with transaction(self.store):
                digest = artifact(self.store, raw)
                ids = [self._stage(item, actor, at) for item in items]
                log(self.store, "M2", "IMPORT_PENDING", digest, actor, at, {"ids": ids})
            return {"ids": ids, "approved": False, "fixture_only": True}
        finally:
            wb.close()

    def link_history(self, cutoff, checker=None):
        cutoff = instant_utc(cutoff)
        docs = [document(self.store, r["id"], cutoff) for r in self.store.visible_documents(cutoff)]
        journals = [d for d in docs if d["kind"] == "JOURNAL" and d.get("source_status") in self.store.config.posted_journal_statuses]
        results = []
        with transaction(self.store):
            for source in sorted((d for d in docs if d["kind"] in {"INVOICE", "BANK", "BASE"}), key=lambda d: {"INVOICE": 0, "BANK": 1, "BASE": 2}[d["kind"]]):
                candidates = []
                for target in journals:
                    strong = source["kind"] == "BANK" and target.get("bank_reference") == source.get("reference") and target.get("bank_account") == source.get("account")
                    strong = strong or (source["kind"] == "INVOICE" and target.get("invoice_key") == source["natural_key"])
                    total = sum(line.get("debit_minor", 0) for line in target["lines"])
                    same_amount = abs(source.get("amount_minor") or 0) == total
                    if strong or (same_amount and source["business_date"] == target["business_date"]):
                        candidates.append((target, "LINK_A" if strong and same_amount else "LINK_B"))
                if len(candidates) > 1:
                    candidates = [(target, "LINK_B") for target, _ in candidates]
                if not candidates:
                    results.append({"source_id": source["id"], "source_kind": source["kind"], "level": "UNLINKED", "direction": "IN" if (source.get("amount_minor") or 0) > 0 else "OUT", "amount_minor": abs(source.get("amount_minor") or 0)})
                for target, level in candidates:
                    if source["kind"] == "BASE":
                        level = "LINK_C"
                    evidence = {"source_id": source["id"], "target_id": target["id"], "method": "explicit_reference_or_amount_date", "ambiguous_candidates": len(candidates)}
                    self.db.execute("INSERT OR IGNORE INTO historical_links VALUES (?,?,?,?,?,?,?,?)", (uid(), source["id"], target["id"], level, canonical_json(evidence), cutoff, cutoff if checker else None, checker))
                    results.append({**evidence, "level": level, "source_kind": source["kind"], "amount_minor": abs(source.get("amount_minor") or 0), "direction": "IN" if (source.get("amount_minor") or 0) > 0 else "OUT"})
        bank_rows = [r for r in results if r["source_kind"] == "BANK"]
        direct_refs = {d["id"] for d in docs if d["kind"] == "BANK" and any(j.get("bank_reference") == d.get("reference") and j.get("bank_account") == d.get("account") for j in journals)}
        return {"fixture_only": True, "links": results, "independent_accuracy": None,
                "e2": {"bank_documents": len({r["source_id"] for r in bank_rows}), "with_explicit_reference": len(direct_refs), "meaning": "Sự hiện diện của tham chiếu trên sổ fixture, không phải độ đúng của liên kết"},
                "note": "LINK_A là mức bằng chứng theo fixture, chưa phải độ đúng đã nghiệm thu kế toán."}
