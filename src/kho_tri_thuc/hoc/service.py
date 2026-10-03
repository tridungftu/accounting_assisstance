from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from ..de_xuat.engine import FIELDS, item_key
from ..ha_tang.primitives import DataError, canonical_json, instant_utc, sha256, text_id, valid_interval
from ..ha_tang.runtime import document, log, run_metadata, source_bundle, transaction, uid
from ..tri_thuc.service import Knowledge


def observed(journal):
    """Derive account and money evidence from ledger lines, never header claims."""
    debit, credit = defaultdict(int), defaultdict(int)
    for line in journal["lines"]:
        debit[line["account"]] += line["debit_minor"]
        credit[line["account"]] += line["credit_minor"]
    debit, credit = {k: v for k, v in debit.items() if v}, {k: v for k, v in credit.items() if v}
    total = sum(debit.values())
    balanced = total > 0 and total == sum(credit.values())
    fields = {f: journal.get(f) for f in FIELDS}
    fields["debit_account"] = next(iter(debit)) if len(debit) == 1 else None
    fields["credit_account"] = next(iter(credit)) if len(credit) == 1 else None
    return fields, total, balanced


def allocation_signature(values):
    result = defaultdict(int)
    for value in values:
        result[value["invoice_reference"]] += value["amount_minor"]
    return dict(result)


class Learning:
    def __init__(self, store):
        self.store, self.db = store, store.conn

    def _record(self, bank, fields, verified, context, evidence, known_at, at, actor, origin):
        at, known_at = instant_utc(at), instant_utc(known_at)
        if known_at > at or not evidence or not any(verified.values()):
            raise DataError("LABEL_EVIDENCE", "Nhãn cần bằng chứng đã biết và ít nhất một trường được xác minh.")
        if set(context) != {"partition", "pattern", "policy_version", "direction", "bank_account", "counterparty"}:
            raise DataError("LABEL_CONTEXT", "Thiếu ngữ cảnh phân vùng nhãn.")
        safe_fields = {field: fields.get(field) for field in FIELDS if verified.get(field) is True and fields.get(field) is not None}
        previous = self.db.execute("SELECT * FROM labels WHERE bank_id=? ORDER BY revision DESC LIMIT 1", (bank["id"],)).fetchone()
        if previous and json.loads(previous["fields_json"]) == safe_fields and json.loads(previous["evidence_json"]) == evidence:
            last = self.db.execute("SELECT action FROM label_events WHERE label_id=? ORDER BY event_at DESC,id DESC LIMIT 1", (previous["id"],)).fetchone()
            if last and last[0] == "ACTIVATE":
                return previous["id"]
        if previous:
            self.db.execute("INSERT INTO label_events(label_id,action,event_at,actor,reason) VALUES (?,'SUPERSEDE',?,?,?)", (previous["id"], at, text_id(actor), "Phiên bản xác minh mới"))
        identifier = uid()
        self.db.execute("INSERT INTO labels VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (identifier, bank["id"], previous["revision"] + 1 if previous else 1,
            canonical_json(safe_fields), canonical_json(verified), canonical_json(context), bank["amount_minor"], known_at, at, at,
            bank["business_date"], None, canonical_json(evidence), origin, text_id(actor)))
        self.db.execute("INSERT INTO label_events(label_id,action,event_at,actor,reason) VALUES (?,'ACTIVATE',?,?,?)", (identifier, at, actor, "Có bằng chứng sổ và người xác minh fixture"))
        log(self.store, "M5", "LABEL_ACTIVATE", identifier, actor, at, {"origin": origin, "verified_fields": verified})
        return identifier

    def from_journal(self, bank_id, journal_id, context, actor, at):
        at = instant_utc(at)
        with transaction(self.store):
            bank, journal = document(self.store, bank_id, at), document(self.store, journal_id, at)
            if bank["kind"] != "BANK" or journal["kind"] != "JOURNAL" or journal.get("source_status") not in self.store.config.posted_journal_statuses or journal.get("bank_reference") != bank["reference"] or journal.get("bank_account") != bank["account"] or journal["business_date"] != bank["business_date"]:
                raise DataError("LABEL_LINK_NOT_PROVEN", "Nhãn lịch sử cần sổ đã ghi có mã ngân hàng/tài khoản/ngày khớp trực tiếp.")
            fields, amount, balanced = observed(journal)
            if journal.get("complete_voucher") is not True or not balanced or amount != abs(bank["amount_minor"]):
                raise DataError("LABEL_AMOUNT", "Bằng chứng số tiền không khớp sao kê.")
            policies = Knowledge(self.store).query(bank["business_date"], at, "POLICY")
            if not any(p["id"] == context.get("policy_version") and p["payload"]["partition"] == context.get("partition") and p["payload"]["template_id"] == context.get("pattern") and p["payload"]["direction"] == context.get("direction") for p in policies):
                raise DataError("LABEL_PARTITION", "Phân vùng nhãn chưa có chính sách được duyệt.")
            if context["bank_account"] != bank["account"] or context["direction"] != ("IN" if bank["amount_minor"] > 0 else "OUT") or context["counterparty"] != (fields["counterparty"] or ""):
                raise DataError("LABEL_CONTEXT", "Ngữ cảnh không khớp bằng chứng.")
            known = self.db.execute("SELECT MAX(known_at) FROM evidence WHERE document_id IN (?,?) AND scope_key='header' AND known_at<=?", (bank_id, journal_id, at)).fetchone()[0]
            return self._record(bank, fields, {f: fields[f] is not None for f in FIELDS}, context, [journal_id], known, at, actor, "HISTORICAL_LEDGER_FIXTURE")

    def revoke(self, label_id, actor, at, reason):
        with transaction(self.store):
            row = self.db.execute("SELECT eligible_at FROM labels WHERE id=?", (label_id,)).fetchone()
            if not row or instant_utc(at) < row[0]:
                raise DataError("LABEL_TIME", "Nhãn không tồn tại hoặc thời gian thu hồi không hợp lệ.")
            self.db.execute("INSERT INTO label_events(label_id,action,event_at,actor,reason) VALUES (?,'REVOKE',?,?,?)", (label_id, instant_utc(at), text_id(actor), text_id(reason)))
            log(self.store, "M5", "LABEL_REVOKE", label_id, actor, at, {"reason": reason})

    def eligible(self, context, cutoff, business_date):
        cutoff = instant_utc(cutoff)
        valid_interval(business_date, None)
        rows = self.db.execute("SELECT * FROM labels WHERE context_json=? AND known_at<=? AND verified_at<=? AND eligible_at<=? AND valid_from<=? AND (valid_to IS NULL OR valid_to>?) ORDER BY bank_id,revision", (canonical_json(context), cutoff, cutoff, cutoff, business_date, business_date))
        selected = {}
        for row in rows:
            last = self.db.execute("SELECT action FROM label_events WHERE label_id=? AND event_at<=? ORDER BY event_at DESC,id DESC LIMIT 1", (row["id"], cutoff)).fetchone()
            if last and last[0] == "ACTIVATE":
                selected[row["bank_id"]] = dict(row)
        return list(selected.values())

    def suggest(self, context, cutoff, business_date, settings, *, excluded_bank_ids=()):
        if not settings or not {"min_count", "min_share"} <= settings.keys():
            return {}
        count = settings["min_count"]
        share = Decimal(str(settings["min_share"]))
        half_life = Decimal(str(settings.get("half_life_days", "365")))
        if isinstance(count, bool) or not isinstance(count, int) or count < 1 or not Decimal("0.5") < share <= 1 or half_life <= 0:
            raise DataError("STATISTICS_POLICY", "Tham số thống kê phải được khai báo hợp lệ trong policy.")
        labels = [label for label in self.eligible(context, cutoff, business_date) if label["bank_id"] not in excluded_bank_ids]
        totals = {f: defaultdict(lambda: {"count": 0, "weight_count": Decimal(0), "weight_money": Decimal(0), "label_ids": []}) for f in FIELDS}
        cutoff_date = datetime.fromisoformat(instant_utc(cutoff).replace("Z", "+00:00")).date()
        for label in labels:
            age = max(0, (cutoff_date - datetime.fromisoformat(label["eligible_at"].replace("Z", "+00:00")).date()).days)
            weight = Decimal(1) / (Decimal(1) + Decimal(age) / half_life)
            for field, value in json.loads(label["fields_json"]).items():
                entry = totals[field][value]
                entry["count"] += 1
                entry["weight_count"] += weight
                entry["weight_money"] += weight * abs(label["amount_minor"])
                entry["label_ids"].append(label["id"])
        result = {}
        for field, values in totals.items():
            total_count = sum(v["weight_count"] for v in values.values())
            total_money = sum(v["weight_money"] for v in values.values())
            for value, stats in values.items():
                if stats["count"] >= count and total_count and total_money and stats["weight_count"] / total_count >= share and stats["weight_money"] / total_money >= share:
                    result[field] = {"value": value, "count": stats["count"], "share_count": str(stats["weight_count"] / total_count), "share_money": str(stats["weight_money"] / total_money), "label_ids": stats["label_ids"]}
        return result

    def rebuild(self, context, cutoff, business_date, settings):
        report = {"cutoff": instant_utc(cutoff), "business_date": business_date, "context": context, "settings": settings,
                  "labels": [row["id"] for row in self.eligible(context, cutoff, business_date)], "suggestions": self.suggest(context, cutoff, business_date, settings), "fixture_only": True, "provenance": run_metadata(self.store)}
        fingerprint = sha256(canonical_json(report).encode())
        with transaction(self.store):
            existing = self.db.execute("SELECT id FROM learning_runs WHERE fingerprint=?", (fingerprint,)).fetchone()
            identifier = existing[0] if existing else uid()
            if not existing:
                self.db.execute("INSERT INTO learning_runs VALUES (?,?,?,?,?,?)", (identifier, report["cutoff"], canonical_json(context), fingerprint, canonical_json(report), report["cutoff"]))
        return {"id": identifier, **report}

    def propose_rule(self, item, actor, at):
        item = {**item, "category": "RULE", "payload": {**item["payload"], "requires_evaluation": True}}
        return Knowledge(self.store).stage_many([item], actor, at)


class Reconciliation:
    def __init__(self, store):
        self.store, self.db = store, store.conn

    def reconcile(self, batch_id, source_attempt_id, actor, at):
        at = instant_utc(at)
        with transaction(self.store):
            batch = self.db.execute("SELECT * FROM export_batches WHERE id=? AND state<>'PREPARING'", (batch_id,)).fetchone()
            if not batch:
                raise DataError("BATCH_NOT_EXPORTED", "Batch chưa xuất hoàn tất.")
            bundle = source_bundle(self.store, source_attempt_id, at)
            if bundle["manifest"]["exported_at"] <= batch["exported_at"] or bundle["manifest"].get("posting_evidence_complete") is not True:
                raise DataError("STALE_VERIFICATION_SOURCE", "Cần sổ xuất lại sau batch, đủ phạm vi kiểm chứng.")
            prior = self.db.execute("SELECT id,report_json FROM verification_runs WHERE batch_id=? AND source_hash=?", (batch_id, bundle["hash"])).fetchone()
            if prior:
                return {"run_id": prior[0], **json.loads(prior[1]), "replayed": True}
            latest = self.db.execute("SELECT MAX(a.exported_at) FROM verification_runs v JOIN attempts a ON a.id=v.source_attempt_id WHERE v.batch_id=?", (batch_id,)).fetchone()[0]
            if latest and bundle["manifest"]["exported_at"] <= latest:
                raise DataError("OLDER_VERIFICATION_SOURCE", "Không dùng bộ cũ/cùng mốc để ghi đè kết quả đối soát mới; cần bản xuất mới có thời điểm rõ.")
            anchor_time = self.db.execute("SELECT a.exported_at FROM sessions s JOIN attempts a ON a.id=s.source_attempt_id WHERE s.id=?", (batch["session_id"],)).fetchone()[0]
            snapshots = {item_key(d): d for d in bundle["documents"] if d["kind"] == "OPEN_ITEM"}
            balances = []
            for expected in self.db.execute("SELECT * FROM expected_balances WHERE batch_id=?", (batch_id,)):
                item = snapshots.get(expected["item_key"])
                actual = item["amount_minor"] if item else 0 if bundle["manifest"].get("scope_open_items_complete") is True else None
                # Include subsequent batches since this batch's anchor. Comparing an old
                # batch's immediate closing balance to month-end would flag valid payments.
                movements = self.db.execute("SELECT e.batch_id,e.delta_minor FROM expected_balances e JOIN export_batches b ON b.id=e.batch_id WHERE e.item_key=? AND b.exported_at>? AND b.exported_at<=?", (expected["item_key"], anchor_time, bundle["manifest"]["exported_at"])).fetchall()
                closing = expected["before_minor"] + sum(m["delta_minor"] for m in movements)
                balances.append({"item_key": expected["item_key"], "expected_minor": closing, "batch_immediate_expected_minor": expected["expected_minor"], "actual_minor": actual,
                                 "movement_batch_ids": [m["batch_id"] for m in movements], "status": "MATCHED" if actual == closing else "UNRESOLVED" if actual is None else "RECON_C"})
            by_key = {b["item_key"]: b for b in balances}
            journals = [d for d in bundle["documents"] if d["kind"] == "JOURNAL" and d.get("source_status") in self.store.config.posted_journal_statuses]
            items, label_requests = [], []
            for entry in self.db.execute("SELECT * FROM export_items WHERE batch_id=? ORDER BY id", (batch_id,)).fetchall():
                payload = json.loads(entry["payload_json"])
                matches = [j for j in journals if j.get("export_item_id") == entry["id"] or (j.get("bank_reference") == payload["bank_reference"] and j.get("bank_account") == payload["bank_account"])]
                field_checks = {f: False for f in FIELDS}
                money_ok, allocation_ok, identity_ok, evidence, actual_fields = False, False, False, [], {}
                if len(matches) == 1:
                    journal = matches[0]
                    evidence = [journal["id"]]
                    actual_fields, amount, balanced = observed(journal)
                    identity_ok = journal.get("bank_reference") == payload["bank_reference"] and journal.get("bank_account") == payload["bank_account"] and journal["business_date"] == payload["business_date"] and journal["currency"] == payload["currency"]
                    money_ok = journal.get("complete_voucher") is True and balanced and amount == abs(payload["amount_minor"])
                    field_checks = {f: actual_fields.get(f) is not None and actual_fields[f] == payload["fields"][f] for f in FIELDS}
                    allocation_ok = (not payload["allocations"] and not journal.get("invoice_allocations")) or ("invoice_allocations" in journal and allocation_signature(journal["invoice_allocations"]) == allocation_signature(payload["allocations"]))
                required = set(payload["required_fields"]) | {"debit_account", "credit_account"} | {f for f, value in payload["fields"].items() if value is not None}
                posting_ok = identity_ok and money_ok and allocation_ok and all(field_checks[f] for f in required)
                balance_ok = all(by_key[a["item_key"]]["status"] == "MATCHED" for a in payload["allocations"])
                status = "MATCHED" if posting_ok and balance_ok else "RECON_A" if not matches else "UNRESOLVED" if len(matches) > 1 else "RECON_C"
                if len(matches) == 1 and status != "MATCHED":
                    # Missing proof is not proof of a wrong entry. Keep it unresolved;
                    # RECON_C requires observed contradictory values.
                    missing_proof = (journal.get("complete_voucher") is not True or not journal["lines"]
                        or any(actual_fields.get(f) is None for f in required)
                        or not journal.get("bank_reference") or not journal.get("bank_account")
                        or (payload["allocations"] and "invoice_allocations" not in journal)
                        or any(by_key[a["item_key"]]["actual_minor"] is None for a in payload["allocations"]))
                    if missing_proof:
                        status = "UNRESOLVED"
                items.append({"export_item_id": entry["id"], "bank_id": payload["bank_id"], "status": status, "verified_fields": field_checks,
                              "identity_verified": identity_ok, "money_verified": money_ok, "allocations_verified": allocation_ok, "balance_verified": balance_ok, "evidence": evidence})
                self.db.execute("UPDATE export_items SET verification_state=? WHERE id=?", (status, entry["id"]))
                self.db.execute("UPDATE proposals SET state=? WHERE id=?", ("RECONCILED" if status == "MATCHED" else "VERIFIED" if posting_ok else "EXPORTED", entry["proposal_id"]))
                self.db.execute("UPDATE allocations SET state=? WHERE proposal_id=? AND state<>'CANCELLED'", ("POSTED" if posting_ok else "EXPORTED", entry["proposal_id"]))
                if status == "MATCHED":
                    label_requests.append((document(self.store, payload["bank_id"]), actual_fields, field_checks, payload["context"], evidence))
                else:
                    for label in self.db.execute("SELECT id FROM labels WHERE bank_id=?", (payload["bank_id"],)).fetchall():
                        self.db.execute("INSERT INTO label_events(label_id,action,event_at,actor,reason) VALUES (?,'REVOKE',?,?,?)", (label["id"], at, text_id(actor), "Nguồn đối soát mới chưa khớp"))
            all_exported = {(p["bank_reference"], p["bank_account"]) for r in self.db.execute("SELECT payload_json FROM export_items") for p in [json.loads(r[0])]}
            outside = [{"journal_id": j["id"], "status": "RECON_B", "learning_eligible": False} for j in journals if j.get("bank_reference") and (j["bank_reference"], j.get("bank_account")) not in all_exported]
            complete = bool(items) and all(i["status"] == "MATCHED" for i in items) and all(b["status"] == "MATCHED" for b in balances)
            identifier = uid()
            report = {"batch_id": batch_id, "source_attempt_id": source_attempt_id, "items": items, "balances": balances, "outside_batch": outside, "complete": complete, "fixture_only": True}
            self.db.execute("INSERT INTO verification_runs VALUES (?,?,?,?,?,?,?)", (identifier, batch_id, source_attempt_id, bundle["hash"], at, text_id(actor), canonical_json(report)))
            for item in items:
                self.db.execute("INSERT INTO field_verifications VALUES (?,?,?,?,?)", (identifier, item["export_item_id"], canonical_json(item["verified_fields"]), canonical_json(item["evidence"]), item["status"]))
            self.db.execute("UPDATE export_batches SET state=? WHERE id=?", ("VERIFIED" if complete else "PARTIALLY_VERIFIED", batch_id))
            learner = Learning(self.store)
            labels = [learner._record(bank, fields, mask, context, evidence, bundle["manifest"]["known_at"], at, actor, "RECONCILED_BATCH_FIXTURE") for bank, fields, mask, context, evidence in label_requests]
            report["label_ids"] = labels
            self.db.execute("UPDATE verification_runs SET report_json=? WHERE id=?", (canonical_json(report), identifier))
            log(self.store, "M5", "RECONCILE", batch_id, actor, at, {"run_id": identifier, "complete": complete, "labels": labels})
        return {"run_id": identifier, **report, "replayed": False}
