from __future__ import annotations

import calendar
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from ..de_xuat.engine import Engine, FIELDS, item_key
from ..ha_tang.primitives import DataError, canonical_json, date_iso, instant_utc, local_business_date, money_minor, sha256, text_id
from ..ha_tang.runtime import artifact, document, ensure_fixture_envelope, log, run_metadata, source_bundle, transaction, uid
from ..ha_tang.store import write_immutable
from ..hoc.service import allocation_signature
from ..nguon.fixture import read_json
from ..xuat import excel


def ratio(numerator, denominator):
    return str(Decimal(numerator) / Decimal(denominator)) if denominator else None


def score(predictions, records):
    counts = Counter(p["completeness"] for p in predictions)
    fields = {f: {"assessed": 0, "correct": 0} for f in FIELDS}
    full_correct = full_assessed = wrong_money = assessed_money = allocation_assessed = allocation_correct = 0
    proposed_count = proposed_minor = total_minor = 0
    slices = defaultdict(lambda: {"count": 0, "proposed_count": 0, "total_minor": 0, "proposed_minor": 0, "assessed_minor": 0, "wrong_minor": 0})
    for proposal, record in zip(predictions, records):
        truth = record.get("truth", {})
        known = truth.get("fields", {})
        has_proposal = proposal["completeness"] != "NONE"
        outcomes = []
        if has_proposal:
            for field in FIELDS:
                if field in known:
                    ok = proposal["fields"].get(field) == known[field]
                    fields[field]["assessed"] += 1
                    fields[field]["correct"] += int(ok)
                    outcomes.append(ok)
            if "allocations" in truth:
                allocation_assessed += 1
                ok = allocation_signature(proposal["allocations"]) == allocation_signature(truth["allocations"])
                allocation_correct += int(ok)
                outcomes.append(ok)
        complete_truth = set(known) == set(FIELDS) and "allocations" in truth
        if has_proposal and proposal["completeness"] == "FULL" and complete_truth:
            full_assessed += 1
            full_correct += int(all(outcomes))
        amount = abs(proposal["amount_minor"])
        total_minor += amount
        if has_proposal:
            proposed_count += 1
            proposed_minor += amount
        band = "LT_1M" if amount < 1000000 else "1M_TO_100M" if amount < 100000000 else "GE_100M"
        group = slices[proposal["direction"] + ":" + band]
        group["count"] += 1
        group["total_minor"] += amount
        if has_proposal:
            group["proposed_count"] += 1
            group["proposed_minor"] += amount
        if has_proposal and outcomes:
            assessed_money += amount
            group["assessed_minor"] += amount
            if not all(outcomes):
                wrong_money += amount
                group["wrong_minor"] += amount
    return {"count": len(records), "coverage": {k: {"count": counts[k], "share": ratio(counts[k], len(records))} for k in ("FULL", "PARTIAL", "NONE")},
            "all_fields": {"assessed": full_assessed, "correct": full_correct, "accuracy": ratio(full_correct, full_assessed)},
            "per_field": {f: {**value, "accuracy": ratio(value["correct"], value["assessed"])} for f, value in fields.items()},
            "allocations": {"assessed": allocation_assessed, "correct": allocation_correct, "accuracy": ratio(allocation_correct, allocation_assessed)},
            "proposal": {"count": proposed_count, "share": ratio(proposed_count, len(records)), "minor": proposed_minor,
                         "money_coverage": ratio(proposed_minor, total_minor), "not_proposed_count": len(records) - proposed_count,
                         "not_proposed_minor": total_minor - proposed_minor},
            "amount": {"assessed_minor": assessed_money, "wrong_minor": wrong_money, "wrong_share": ratio(wrong_money, assessed_money), "counted_once_per_bank": True},
            "unknown_truth_count": len(records) - full_assessed, "slices": dict(slices), "acceptance_is_accuracy": False,
            "scoring_rule": "NONE không tính là đề xuất sai; tiền sai chỉ tính khi có đề xuất và có ground truth được chấm."}


def reconstruct_open_items(anchors, movements, as_of, cutoff):
    """Replay forward from an available anchor; never subtract from future balances."""
    as_of, cutoff = date_iso(as_of), instant_utc(cutoff)
    eligible = [a for a in anchors if a.get("known_at") and instant_utc(a["known_at"]) <= cutoff and date_iso(a["as_of"]) <= as_of]
    if not eligible:
        raise DataError("NO_PAST_ANCHOR", "Không có số dư gốc đã biết tại thời điểm kiểm chứng.")
    latest = max(a["as_of"] for a in eligible)
    choices = [a for a in eligible if a["as_of"] == latest]
    if len({canonical_json(a["balances"]) for a in choices}) != 1:
        raise DataError("ANCHOR_CONFLICT", "Các số dư cùng mốc không khớp.")
    anchor = choices[0]
    balances = {key: money_minor(value) for key, value in anchor["balances"].items()}
    used, unavailable, unique = [], [], {}
    for movement in movements:
        if not latest < date_iso(movement["business_date"]) <= as_of:
            continue
        if not movement.get("known_at") or instant_utc(movement["known_at"]) > cutoff:
            unavailable.append(movement["id"])
            continue
        prior = unique.get(movement["id"])
        if prior and canonical_json(prior) != canonical_json(movement):
            raise DataError("MOVEMENT_CONFLICT", "Một bút toán có nhiều nội dung.")
        if prior:
            continue
        unique[movement["id"]] = movement
        balances[movement["item_key"]] = money_minor(balances.get(movement["item_key"], 0) + money_minor(movement["delta_minor"]))
        used.append(movement["id"])
    return {"anchor_id": anchor["id"], "as_of": as_of, "cutoff": cutoff, "balances": balances, "movement_ids": used, "unavailable_movements": unavailable, "complete": not unavailable}


class Quality:
    def __init__(self, store):
        self.store, self.db = store, store.conn

    def register(self, path):
        raw = Path(path).read_bytes()
        value = read_json(raw)
        ensure_fixture_envelope(value, "ktt-evaluation-fixture-v1")
        name, version = text_id(value["id"]), text_id(value["version"])
        identifier = canonical_json([name, version])
        records = value.get("records")
        if not isinstance(records, list) or not records or len({r["bank_id"] for r in records}) != len(records):
            raise DataError("EVALUATION_ROWS", "Mỗi sao kê chỉ có một hàng trong dataset đã đóng băng.")
        groups = {}
        for record in records:
            split = record.get("split")
            if split not in {"DEV", "HOLDOUT", "BLIND"}:
                raise DataError("EVALUATION_SPLIT", "Cần chỉ rõ DEV/HOLDOUT/BLIND.")
            group = text_id(record["group_id"])
            if group in groups and groups[group] != split:
                raise DataError("GROUP_LEAKAGE", "Cùng nhóm chứng từ bị chia sang nhiều tập.")
            groups[group] = split
            instant_utc(record["cutoff"])
            truth = record.get("truth", {})
            if not isinstance(truth, dict) or set(truth.get("fields", {})) - set(FIELDS):
                raise DataError("TRUTH_SCHEMA", "Ground truth có trường ngoài hợp đồng.")
            if truth and (not truth.get("reviewer") or not truth.get("evidence")):
                raise DataError("TRUTH_EVIDENCE", "Ground truth cần người kiểm tra và bằng chứng fixture.")
            for allocation in truth.get("allocations", []):
                if money_minor(allocation["amount_minor"]) <= 0:
                    raise DataError("TRUTH_AMOUNT", "Tiền ground truth không hợp lệ.")
        with transaction(self.store):
            existing = self.db.execute("SELECT artifact_hash FROM evaluation_datasets WHERE id=?", (identifier,)).fetchone()
            if existing and existing[0] != sha256(raw):
                raise DataError("DATASET_FROZEN", "Dataset/version đã đóng băng; cần version mới.")
            digest = artifact(self.store, raw)
            self.db.execute("INSERT OR IGNORE INTO evaluation_datasets VALUES (?,?,?,?)", (identifier, version, digest, canonical_json(value)))
        return identifier

    def evaluate(self, dataset_id, actor, at):
        row = self.db.execute("SELECT * FROM evaluation_datasets WHERE id=?", (dataset_id,)).fetchone()
        if not row:
            raise DataError("DATASET_NOT_FOUND", "Không có dataset.")
        value = json.loads(row["manifest_json"])
        excluded_label_bank_ids = {r["bank_id"] for r in value["records"]}
        reports, evidence = {}, []
        engine = Engine(self.store)
        for split in ("DEV", "HOLDOUT", "BLIND"):
            records = sorted([r for r in value["records"] if r["split"] == split], key=lambda r: (instant_utc(r["cutoff"]), r["bank_id"]))
            if not records:
                continue
            reports[split] = {}
            for baseline in ("A", "B"):
                predictions, used = [], defaultdict(int)
                for record in records:
                    cutoff = instant_utc(record["cutoff"])
                    if cutoff > instant_utc(at):
                        raise DataError("FUTURE_EVALUATION", "Chưa đến thời điểm của mẫu đánh giá.")
                    bank = document(self.store, record["bank_id"], cutoff)
                    bundle = source_bundle(self.store, record["source_attempt_id"], cutoff)
                    def available(item):
                        return max(0, abs(item["amount_minor"]) - used[(record["source_attempt_id"], item_key(item))])
                    prediction = engine.preview(bank, bundle, cutoff, baseline, available, excluded_label_bank_ids=excluded_label_bank_ids)
                    for allocation in prediction["allocations"]:
                        used[(record["source_attempt_id"], allocation["item_key"])] += allocation["amount_minor"]
                    predictions.append(prediction)
                    evidence.append({"bank_id": bank["id"], "source_hash": bundle["hash"], "cutoff": cutoff, "baseline": baseline, "prediction": prediction})
                reports[split][baseline] = score(predictions, records)
        report = {"dataset_id": dataset_id, "dataset_hash": row["artifact_hash"], "splits": reports, "fixture_only": True,
                  "real_operation_gate": "NO_GO_REAL_DATA", "reasons": ["Chưa có dữ liệu thực, ground truth độc lập và mẫu Junsky được xác nhận"],
                  "candidate_gate_passed": False, "evaluated_candidate_ids": [], "replay": evidence, "provenance": run_metadata(self.store), "excluded_training_bank_ids": sorted(excluded_label_bank_ids)}
        # Only approved rules are active in A/B. Pending rules require an explicit impact experiment.
        fingerprint = sha256(canonical_json(report).encode())
        with transaction(self.store):
            existing = self.db.execute("SELECT id FROM quality_runs WHERE fingerprint=?", (fingerprint,)).fetchone()
            identifier = existing[0] if existing else uid()
            if not existing:
                self.db.execute("INSERT INTO quality_runs VALUES (?,?,?,?,?)", (identifier, dataset_id, fingerprint, canonical_json(report), instant_utc(at)))
                log(self.store, "M6", "EVALUATE", identifier, actor, at, {"dataset": dataset_id, "fixture_only": True})
        return {"run_id": identifier, **report}

    def blind_workbook(self, dataset_id, path, actor, at):
        row = self.db.execute("SELECT manifest_json FROM evaluation_datasets WHERE id=?", (dataset_id,)).fetchone()
        if not row:
            raise DataError("DATASET_NOT_FOUND", "Không có dataset.")
        data = json.loads(row[0])
        wb = excel.workbook()
        excel.table(wb, "HUONG_DAN", ["noi_dung"], [["ĐÁNH GIÁ MÙ — FIXTURE; tự xác định đáp án từ nguồn"], [dataset_id]])
        rows = []
        for record in data["records"]:
            if record["split"] != "BLIND":
                continue
            bank = document(self.store, record["bank_id"], record["cutoff"])
            rows.append([bank["id"], bank["business_date"], bank["description"], str(bank["amount_minor"]), bank["account"], bank["reference"], *["" for _ in FIELDS], "", "", ""])
        excel.table(wb, "DANH_GIA_MU", ["bank_id", "ngay", "dien_giai", "so_tien", "tai_khoan_ngan_hang", "ma_ngan_hang", *FIELDS, "allocations_json", "nguoi_kiem_tra", "bang_chung"], rows)
        raw = excel.to_bytes(wb)
        with transaction(self.store):
            digest = artifact(self.store, raw)
            log(self.store, "M6", "BLIND_WORKBOOK", dataset_id, actor, at, {"artifact": digest, "count": len(rows)})
        write_immutable(Path(path), raw)
        return {"path": str(Path(path).resolve()), "count": len(rows), "contains_suggestions": False}

    def evaluate_candidate(self, candidate_id, dataset_id, gate_id, actor, at):
        """Explicit counterfactual impact experiment; does not activate the candidate."""
        at = instant_utc(at)
        candidate = self.db.execute("SELECT * FROM knowledge_versions WHERE id=? AND category='RULE'", (candidate_id,)).fetchone()
        dataset = self.db.execute("SELECT * FROM evaluation_datasets WHERE id=?", (dataset_id,)).fetchone()
        if not candidate or candidate["known_at"] > at or not dataset:
            raise DataError("CANDIDATE_INPUT", "Thiếu đề cử/dataset hoặc tri thức chưa được biết.")
        if self.db.execute("SELECT 1 FROM knowledge_events WHERE version_id=?", (candidate_id,)).fetchone():
            raise DataError("CANDIDATE_NOT_PENDING", "Thí nghiệm chỉ dành cho đề cử đang chờ duyệt.")
        engine = Engine(self.store)
        gates = [g for g in engine.knowledge.query(local_business_date(at), at, "STATISTICS") if g["id"] == gate_id and g["payload"].get("kind") == "QUALITY_GATE_FIXTURE"]
        if not gates:
            raise DataError("GATE_NOT_APPROVED", "Cần cấu hình ngưỡng fixture có phiên bản, đã được duyệt.")
        gate = gates[0]["payload"]
        minimum = gate.get("min_assessed")
        try:
            accuracy, error_share = Decimal(str(gate["min_accuracy"])), Decimal(str(gate["max_wrong_money_share"]))
        except (KeyError, ValueError, ArithmeticError) as exc:
            raise DataError("GATE_CONFIG", "Ngưỡng fixture không hợp lệ.") from exc
        if type(minimum) is not int or minimum < 1 or not 0 <= accuracy <= 1 or not 0 <= error_share <= 1:
            raise DataError("GATE_CONFIG", "Ngưỡng fixture không hợp lệ.")
        records = sorted([r for r in json.loads(dataset["manifest_json"])["records"] if r["split"] == "HOLDOUT"], key=lambda r: (r["cutoff"], r["bank_id"]))
        if not records:
            raise DataError("HOLDOUT_REQUIRED", "Đề cử cần tập holdout; không duyệt bằng tập phát triển hoặc mẫu mù.")
        predictions = {"baseline": [], "candidate": []}
        candidate_row = {**dict(candidate), "payload": json.loads(candidate["payload_json"])}
        for mode in predictions:
            used = defaultdict(int)
            for record in records:
                cutoff = instant_utc(record["cutoff"])
                if cutoff > at:
                    raise DataError("FUTURE_EVALUATION", "Chưa đến thời điểm của mẫu đánh giá.")
                bank = document(self.store, record["bank_id"], cutoff)
                bundle = source_bundle(self.store, record["source_attempt_id"], cutoff)
                eligible_date = candidate["valid_from"] <= bank["business_date"] and (candidate["valid_to"] is None or bank["business_date"] < candidate["valid_to"])
                preview = engine.preview(bank, bundle, cutoff, "A", lambda item: max(0, abs(item["amount_minor"]) - used[(record["source_attempt_id"], item_key(item))]),
                                         candidate_rules=[candidate_row] if mode == "candidate" and eligible_date else [])
                predictions[mode].append(preview)
                for allocation in preview["allocations"]:
                    used[(record["source_attempt_id"], allocation["item_key"])] += allocation["amount_minor"]
        baseline, impact = score(predictions["baseline"], records), score(predictions["candidate"], records)
        passed = impact["all_fields"]["assessed"] >= minimum and impact["all_fields"]["accuracy"] is not None and impact["amount"]["wrong_share"] is not None
        passed = bool(passed and Decimal(impact["all_fields"]["accuracy"]) >= max(accuracy, Decimal(baseline["all_fields"]["accuracy"] or "0"))
                      and Decimal(impact["amount"]["wrong_share"]) <= min(error_share, Decimal(baseline["amount"]["wrong_share"] or "1")))
        report = {"experiment": "COUNTERFACTUAL_FIXTURE_RULE_IMPACT", "not_historical_replay": True, "fixture_only": True,
                  "evaluated_candidate_ids": [candidate_id], "candidate_hash": candidate["content_hash"], "candidate_gate_passed": passed,
                  "gate_id": gate_id, "gate_hash": gates[0]["content_hash"], "dataset_id": dataset_id, "dataset_hash": dataset["artifact_hash"],
                  "baseline": baseline, "candidate": impact, "automatic_activation": False, "real_operation_gate": "NO_GO_REAL_DATA", "provenance": run_metadata(self.store)}
        fingerprint = sha256(canonical_json(report).encode())
        with transaction(self.store):
            previous = self.db.execute("SELECT id FROM quality_runs WHERE fingerprint=?", (fingerprint,)).fetchone()
            identifier = previous[0] if previous else uid()
            if not previous:
                self.db.execute("INSERT INTO quality_runs VALUES (?,?,?,?,?)", (identifier, dataset_id, fingerprint, canonical_json(report), at))
                log(self.store, "M6", "EVALUATE_CANDIDATE", candidate_id, actor, at, {"run_id": identifier, "passed": passed, "gate_id": gate_id})
        return {"run_id": identifier, **report}

    def close_month(self, month, source_attempt_id, actor, at):
        first = date_iso(month + "-01")
        year, number = map(int, month.split("-"))
        last = f"{month}-{calendar.monthrange(year, number)[1]:02d}"
        at = instant_utc(at)
        with transaction(self.store):
            bundle = source_bundle(self.store, source_attempt_id, at)
            if bundle["manifest"]["as_of"] < last or bundle["manifest"]["coverage_from"] > first or bundle["manifest"]["coverage_to_exclusive"] <= last or bundle["manifest"].get("scope_open_items_complete") is not True or bundle["manifest"].get("posting_evidence_complete") is not True:
                raise DataError("MONTH_SCOPE", "Bộ chốt tháng chưa bao phủ đủ kỳ và công nợ.")
            if self.db.execute("SELECT 1 FROM sessions WHERE state IN ('OPEN','PREPARING')").fetchone():
                raise DataError("ACTIVE_SESSION", "Còn phiên chưa chốt.")
            banks = [d for d in self.store.visible_documents(at) if d["kind"] == "BANK" and d["business_date"][:7] == month]
            if not banks:
                raise DataError("EMPTY_MONTH", "Không chốt một tháng chưa có sao kê.")
            for bank in banks:
                entry = self.db.execute("SELECT e.batch_id FROM proposals p JOIN export_items e ON e.proposal_id=p.id WHERE p.bank_id=? AND p.state='RECONCILED'", (bank["id"],)).fetchone()
                if not entry:
                    raise DataError("UNRESOLVED_BANK", "Còn sao kê chưa được xác minh và đối soát.")
                run = self.db.execute("SELECT report_json FROM verification_runs WHERE batch_id=? AND source_attempt_id=?", (entry[0], source_attempt_id)).fetchone()
                if not run or not json.loads(run[0])["complete"]:
                    raise DataError("FINAL_RECONCILIATION_REQUIRED", "Mỗi batch cần đối soát với chính bộ chốt cuối tháng.")
                outside = json.loads(run[0])["outside_batch"]
                if outside:
                    raise DataError("OUTSIDE_BATCH_UNREVIEWED", "Còn phát sinh ngoài batch cần điều tra; chưa được chốt.")
            existing = self.db.execute("SELECT * FROM month_closures WHERE month=?", (month,)).fetchone()
            if existing and existing["source_attempt_id"] != source_attempt_id:
                raise DataError("MONTH_ALREADY_CLOSED", "Tháng đã chốt với bộ khác; cần quy trình điều chỉnh.")
            self.db.execute("INSERT OR IGNORE INTO month_closures VALUES (?,?,?,?,?)", (month, source_attempt_id, text_id(actor), at, canonical_json({"source_hash": bundle["hash"], "bank_count": len(banks), "fixture_only": True})))
            log(self.store, "M6", "CLOSE_MONTH_FIXTURE", month, actor, at, {"source_attempt_id": source_attempt_id})
        return {"month": month, "state": "CLOSED_FIXTURE", "bank_count": len(banks), "real_operation_gate": "NO_GO_REAL_DATA"}
