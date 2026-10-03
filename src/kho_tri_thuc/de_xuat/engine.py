from __future__ import annotations

import json
from datetime import date, timedelta

from ..ha_tang.primitives import DataError, natural_key, normalize_text, money_minor
from ..tri_thuc.service import Knowledge
from ..tri_thuc.matching import case_matches, choose, matches
from ..giao_dien.v9b import bank_account, journal_suggestion, match_bank_to_journal, materialize_journal_pattern

FIELDS = ("counterparty", "debit_account", "credit_account", "project", "expense")


def item_key(item):
    return natural_key(item["account"], item["counterparty"], item["currency"], item["item_id"])


class Engine:
    def __init__(self, store, *, include_pending=False):
        self.store = store
        self.knowledge = Knowledge(store)
        self.include_pending = include_pending
        self.cash_overrides: dict[str, dict] = {}

    def _runtime_settings(self):
        defaults = {"object_learning_from": "2026-07-01", "description_similarity_threshold": 0.8,
                    "own_counterparty_codes": [], "learning_cutoff": ""}
        row = self.store.conn.execute("SELECT value FROM workspace_meta WHERE key='v9b_runtime_settings'").fetchone()
        if row:
            try:
                loaded = json.loads(row[0])
                if isinstance(loaded, dict):
                    defaults.update({key: value for key, value in loaded.items() if key in defaults})
            except json.JSONDecodeError:
                pass
        return defaults

    def _own_codes(self):
        settings = self._runtime_settings()
        values = set(str(value) for value in settings.get("own_counterparty_codes", []) if value)
        row = self.store.conn.execute("SELECT value FROM workspace_meta WHERE key='v9b_derived_own_codes'").fetchone()
        if row:
            try:
                values.update(str(value) for value in json.loads(row[0]) if value)
            except (TypeError, json.JSONDecodeError):
                pass
        return values

    def _cash_mapping(self, bank):
        account = bank_account(bank.get("account"))
        if account and account in self.cash_overrides:
            value = self.cash_overrides[account]
            if value.get("cash_account"):
                return value["cash_account"], value.get("source", "JOURNAL_UNIQUE")
            return None, "CONFLICT"
        row = self.store.conn.execute("SELECT cash_account,source FROM cash_account_mappings WHERE bank_account=?", (account,)).fetchone()
        return (row["cash_account"], row["source"]) if row else (None, "MISSING")

    @staticmethod
    def _pending_level(row, prefix="PENDING_RULE"):
        payload, source = row.get("payload", {}), row.get("payload", {}).get("source_row", {})
        def number(*names):
            for name in names:
                value = payload.get(name, source.get(name))
                try:
                    return int(str(value).strip())
                except (TypeError, ValueError):
                    continue
            return 0
        seen = number("occurrences", "so_lan_gap", "so_lan_gap")
        correct = number("correct_occurrences", "so_lan_dung", "so_lan_dung")
        return prefix + "_STRONG" if seen >= 3 and seen == correct else prefix + "_WEAK"

    @staticmethod
    def _counterparty_trigger_allows(payload):
        trigger = payload.get("trigger")
        return isinstance(trigger, dict) and trigger.get("mode") in {"KEY", "KEY_REGEX"} and trigger.get("key_type") in {"BANK_ACCOUNT", "COUNTERPARTY_NAME"}

    @staticmethod
    def _identifier_rank(match):
        status = str(match.get("source_status") or "").upper()
        if status == "QUICK_DECISION": return 1, "ANH_DA_DUYET"
        if status in {"DIRECTORY_CORRECT", "DIRECTORY_ENTERED", "JUNSKY_CATALOG"}: return 2, "VERIFIED_IDENTIFIER"
        if status == "DIRECTORY_HIGH": return 3, "DIRECTORY_HIGH"
        if status == "DIRECTORY_MEDIUM": return 4, "DIRECTORY_MEDIUM"
        if status == "MACHINE_CHAC_CHAN": return 5, "MACHINE_CHAC_CHAN"
        if status == "DIRECTORY_LOW": return 6, "DIRECTORY_LOW"
        if status == "MACHINE_NHAP": return 7, "MACHINE_NHAP"
        # Legacy approved mappings predate V9b status fields.  Preserve their
        # former explicit verification without treating PENDING as approved.
        if match.get("verified") and match.get("approval_state") == "APPROVED": return 2, "VERIFIED_IDENTIFIER"
        reliability = str(match.get("reliability") or "").upper()
        return {"HIGH": (3, "DIRECTORY_HIGH"), "MEDIUM": (4, "DIRECTORY_MEDIUM"), "LOW": (6, "DIRECTORY_LOW")}.get(reliability, (7, "PENDING_IDENTIFIER"))

    def _identify_counterparty(self, bank, cutoff):
        candidates = []
        pairs = [(kind, value) for kind, value in (("BANK_REFERENCE", bank.get("reference")), ("BANK_ACCOUNT", bank.get("counterparty_account")),
                 ("COUNTERPARTY_NAME", bank.get("counterparty_name")), ("TAX_ID", bank.get("counterparty_tax_id"))) if value]
        resolved = self.knowledge.resolve_identifiers(pairs, bank["business_date"], cutoff, include_pending=self.include_pending) if pairs else {}
        for kind, value in pairs:
            candidates.extend({**match, "identifier_type": kind} for match in resolved[(kind, value)]["matches"])
        own = self._own_codes()
        candidates = [match for match in candidates if match.get("counterparty") not in own]
        if not candidates:
            return None, {"level": "UNKNOWN", "evidence": []}, None, []
        ranked = [(self._identifier_rank(match), match) for match in candidates]
        best = min(rank for rank, _ in ranked)
        same = [match for rank, match in ranked if rank == best]
        parties = {match["counterparty"] for match in same}
        if len(parties) != 1:
            return None, {"level": "UNKNOWN", "evidence": [match["knowledge_id"] for match in same]}, "IDENTIFIER_CONFLICT", same
        return next(iter(parties)), {"level": best[1], "evidence": [match["knowledge_id"] for match in same]}, None, same

    def _apply_cash_leg(self, bank, fields, confidence, constraints, result):
        account, source = self._cash_mapping(bank)
        direction, field = ("IN", "debit_account") if bank["amount_minor"] > 0 else ("OUT", "credit_account")
        side = "DEBIT" if direction == "IN" else "CREDIT"
        if not account:
            # Legacy generated fixtures intentionally encode their 112 leg in
            # an approved template and have no source-account mapping table.
            # Keep those historical contracts executable in the *fixture*
            # environment only.  The operational `that` configuration never
            # takes this branch: it must have a configured or uniquely learned
            # mapping, as required by S1.
            legacy = str(fields.get(field) or "")
            if self.store.config.environment == "fixture" and legacy.startswith("112"):
                result["cash_leg"] = {"account": legacy, "side": side, "source": "FIXTURE_LEGACY_TEMPLATE"}
                return
            constraints.append("CASH_ACCOUNT_MAPPING_CONFLICT" if source == "CONFLICT" else "CASH_ACCOUNT_MAPPING_MISSING")
            return
        if fields.get(field) and fields[field] != account:
            constraints.append("CASH_ACCOUNT_CONFLICT")
            return
        fields[field] = account
        confidence[field] = {"level": "CAU_HINH_TK_TIEN", "evidence": ["CASH:" + bank_account(bank.get("account"))]}
        result["cash_leg"] = {"account": account, "side": side, "source": source}

    def _learning_cutoff(self):
        """Last ledger day the machine may learn from ("" = up to the bank date).

        A replay (for example: learn to 30/06, test on August) must not see
        rules first observed after that day.  Imported rule workbooks carry
        their first-seen day in ``source_row.lan_dau``.
        """
        if not hasattr(self, "_learning_cutoff_value"):
            value = str(self._runtime_settings().get("learning_cutoff") or "").strip()[:10]
            try:
                self._learning_cutoff_value = date.fromisoformat(value).isoformat() if value else ""
            except ValueError:
                self._learning_cutoff_value = ""
        return self._learning_cutoff_value

    @staticmethod
    def _first_seen(value) -> str:
        """ISO day of a rule's first sighting from its workbook cell ('' if unknown)."""
        import re as _re
        text = str(value or "").strip()
        found = _re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
        if found:
            return found.group(0)
        found = _re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if found:
            return f"{found.group(3)}-{int(found.group(2)):02d}-{int(found.group(1)):02d}"
        found = _re.match(r"(\d{1,2})/(\d{4})$", text) or _re.match(r"(\d{4})-(\d{2})$", text)
        if found:
            year, month = (found.group(2), found.group(1)) if "/" in text else (found.group(1), found.group(2))
            return f"{year}-{int(month):02d}-01"
        return ""

    def _query(self, business_date, cutoff, category=None):
        rows = self.knowledge.query(business_date, cutoff, category, include_pending=self.include_pending)
        limit = self._learning_cutoff() if category in ("POLICY", "RULE") else ""
        if limit:
            rows = [row for row in rows if self._first_seen((row.get("payload", {}).get("source_row") or {}).get("lan_dau")) <= limit]
        return rows

    def catalog(self, date, cutoff):
        # Read-only membership map; memoized per Engine (one proposal run)
        # because validate_fields() is called several times per row.
        memo = self.__dict__.setdefault("_catalog_memo", {})
        epoch = self.store.conn.execute("SELECT revision FROM knowledge_epoch WHERE id=1").fetchone()[0]
        key = (date, cutoff, epoch)
        if key not in memo:
            if len(memo) > 64:
                memo.clear()
            memo[key] = {(r["payload"]["kind"], r["payload"]["code"]): r for r in self._query(date, cutoff, "CATALOG") if r["payload"]["kind"] != "IDENTIFIER"}
        return memo[key]

    def validate_fields(self, fields, date, cutoff, required):
        errors = []
        catalog = self.catalog(date, cutoff)
        for field, kind in (("counterparty", "COUNTERPARTY"), ("debit_account", "ACCOUNT"), ("credit_account", "ACCOUNT"), ("project", "PROJECT"), ("expense", "EXPENSE")):
            value = fields.get(field)
            if field in set(required) | {"debit_account", "credit_account"} and not value:
                errors.append("MISSING_" + field.upper())
            if value and (kind, value) not in catalog:
                errors.append("INVALID_" + field.upper())
        return errors

    def preview(self, record, bundle, cutoff, baseline="A", available=None, *, candidate_rules=(), excluded_label_bank_ids=()):
        """Preview one supported source document without creating an approval.

        BANK keeps the proven V1–V7 flow.  INVOICE and BASE use their own
        evidence paths and deliberately return waiting constraints when a
        required relation has not been approved.
        """
        if record["kind"] == "BANK":
            return self._preview_bank(record, bundle, cutoff, baseline, available, candidate_rules=candidate_rules, excluded_label_bank_ids=excluded_label_bank_ids)
        if record["kind"] == "INVOICE":
            return self._preview_invoice(record, cutoff)
        if record["kind"] == "BASE":
            return self._preview_base(record, cutoff)
        raise DataError("UNSUPPORTED_PROPOSAL_DOCUMENT", "Chỉ đề xuất sao kê, hóa đơn hoặc đề nghị Base.")

    def _preview_bank(self, bank, bundle, cutoff, baseline="A", available=None, *, candidate_rules=(), excluded_label_bank_ids=()):
        if bundle["manifest"].get("as_of") and bank["business_date"] > bundle["manifest"]["as_of"]:
            raise DataError("BANK_SCOPE", "Snapshot chưa bao phủ ngày sao kê.")
        direction = "IN" if bank["amount_minor"] > 0 else "OUT"
        fields = {name: None for name in FIELDS}
        confidence = {name: {"level": "UNKNOWN", "evidence": []} for name in FIELDS}
        stages = []
        constraints = []
        result = {"bank_id": bank["id"], "business_date": bank["business_date"], "amount_minor": bank["amount_minor"],
                  "direction": direction, "fields": fields, "confidence": confidence, "stages": stages,
                  "constraints": constraints, "candidates": [], "allocations": [], "completeness": "NONE",
                  "unallocated_minor": abs(bank["amount_minor"]), "score_is_probability": False, "baseline": baseline,
                  "lines": [], "contract_version": 3}
        if not bank["amount_minor"]:
            constraints.append("ZERO_AMOUNT")
        for lock in (d for d in bundle["documents"] if d["kind"] == "LOCK_PERIOD"):
            if lock["source_status"] == "LOCKED" and lock["valid_from"] <= bank["business_date"] < lock["valid_to"]:
                constraints.append("LOCKED_PERIOD")
        journals = [d for d in bundle["documents"] if d["kind"] == "JOURNAL" and d.get("source_status") in self.store.config.posted_journal_statuses]
        matched_postings = [d for d in journals if d.get("bank_reference") == bank.get("reference") and d.get("bank_account") == bank.get("account")]
        if matched_postings:
            constraints.append("ALREADY_POSTED_OR_DUPLICATE_REFERENCE")
        settings = self._runtime_settings()
        threshold = float(settings.get("description_similarity_threshold", 0.8))
        journal_match = match_bank_to_journal(bank, journals, threshold)
        result["journal_match"] = journal_match
        result["potential_existing"] = journal_match["status"] == "UNIQUE"
        if journal_match["status"] == "AMBIGUOUS":
            result["warnings"] = ["JOURNAL_MATCH_AMBIGUOUS"]
        party, party_confidence, identification_failure, identification = self._identify_counterparty(bank, cutoff)
        if identification_failure:
            constraints.append(identification_failure)
        elif party:
            fields["counterparty"] = party
            confidence["counterparty"] = party_confidence
        stages.append({"step": "nhan_dien", "matches": identification})
        normalized = normalize_text(bank.get("description", ""))
        cases = [r for r in self._query(bank["business_date"], cutoff, "CASE") if r["payload"].get("contract_version") == 2 and case_matches(r["payload"], bank, self.store.config.entity_id)]
        policies = [r for r in self._query(bank["business_date"], cutoff, "POLICY") if matches(r["payload"], bank, fields)]
        expired = [r["id"] for r in self.knowledge.expired(bank["business_date"], cutoff) if matches(r["payload"], bank, fields)]
        result["matching_evidence"] = {"case_ids": [r["id"] for r in cases], "policy_ids": [r["id"] for r in policies], "expired_policy_ids": expired}
        if len(cases) > 1:
            selected, failure = None, "CASE_CONFLICT"
        elif cases:
            selected, failure = cases[0], None
        else:
            selected, failure = choose(policies)
        learning = None
        if failure:
            # V9b S6 is deliberately a pending evidence path.  It may propose
            # from earlier BR/BP vouchers when no imported rule applies; it
            # never converts that evidence into an approved template.
            if failure == "NO_UNIQUE_APPROVED_TEMPLATE":
                cutoff_day = min(bank["business_date"], cutoff[:10])
                if self._learning_cutoff():
                    cutoff_day = min(cutoff_day, (date.fromisoformat(self._learning_cutoff()) + timedelta(days=1)).isoformat())
                learning = journal_suggestion(bank, journals, cutoff_day=cutoff_day, own_codes=self._own_codes(),
                                               object_learning_from=str(settings.get("object_learning_from", "2026-07-01")), threshold=threshold)
            if not learning:
                constraints.append(failure)
                stages.extend([{ "step": s, "status": "BLOCKED"} for s in ("doi_chieu", "rang_buoc", "xep_hang", "tin_cay")])
                return result
            selected = None
            policy = {"partition": "JOURNAL_LEARNING", "template_id": "JOURNAL_PATTERN", "direction": direction,
                      "needs_open_item": False, "required_fields": ["debit_account", "credit_account"], "fields": learning["fields"]}
            result.update(template_id="JOURNAL_PATTERN", policy=policy, learning=learning)
            for name, value in learning["fields"].items():
                if name in fields and fields[name] is None and value:
                    fields[name] = value
                    confidence[name] = {"level": learning["strength"], "evidence": learning["source_ids"]}
        else:
            policy = selected["payload"]
            if policy.get("requires_multiline_review") and not policy.get("journal_lines"):
                constraints.append("MULTILINE_TEMPLATE_REQUIRES_REVIEW")
            result.update(template_id=selected["id"], policy=policy)
            for name, value in policy.get("fields", {}).items():
                if name == "counterparty":
                    # A CASE is a scoped, exact operator decision, not a
                    # generic rule.  S4 restricts rule-driven counterparty
                    # filling, while preserving the older CASE conflict gate.
                    if (not cases and not self._counterparty_trigger_allows(policy)) or value in self._own_codes():
                        continue
                    if value and fields[name] and value != fields[name] and policy.get("contract_version") == 2:
                        constraints.append("TEMPLATE_IDENTIFIER_CONFLICT")
                if name in fields and fields[name] is None and value:
                    level = "APPROVED_TEMPLATE" if selected.get("approval_state") == "APPROVED" else self._pending_level(selected)
                    confidence[name] = {"level": level, "evidence": [selected["id"]]}
                    fields[name] = value
            if selected.get("approval_state") != "APPROVED":
                result["why"] = "Tri thức chờ duyệt được dùng ở chế độ đề xuất; chưa được tự duyệt."
        rule_values = {}
        for rule in ([] if cases else self._query(bank["business_date"], cutoff, "RULE") + list(candidate_rules)):
            p = rule["payload"]
            if p.get("partition") and p["partition"] != policy["partition"]:
                continue
            if p.get("pattern") and p["pattern"] != policy["template_id"]:
                continue
            if p.get("direction") and p["direction"] != direction:
                continue
            if (p.get("contract_version") == 2 or p.get("keywords")) and matches(p, bank, fields):
                for name, value in p.get("fields", {}).items():
                    if name == "counterparty" and (not self._counterparty_trigger_allows(p) or value in self._own_codes()):
                        continue
                    if value:
                        rule_values.setdefault(name, []).append((value, rule))
        for name, values in rule_values.items():
            if name in fields and fields[name] is None:
                if len({value for value, _ in values}) == 1:
                    value, first = values[0]
                    level = "APPROVED_KEYWORD" if first.get("approval_state") == "APPROVED" else self._pending_level(first)
                    fields[name] = value
                    confidence[name] = {"level": level, "evidence": [entry["id"] for _, entry in values]}
                else:
                    constraints.append("KEYWORD_CONFLICT_" + name.upper())
        self._apply_cash_leg(bank, fields, confidence, constraints, result)
        context = {"partition": policy["partition"], "pattern": policy["template_id"], "policy_version": selected["id"] if selected else "JOURNAL_PATTERN", "direction": direction, "bank_account": bank["account"], "counterparty": fields["counterparty"] or ""}
        result["context"] = context
        if baseline == "B" and not cases:
            from ..hoc.service import Learning
            suggestion = Learning(self.store).suggest(context, cutoff, bank["business_date"], policy.get("statistics", {}), excluded_bank_ids=excluded_label_bank_ids)
            for name, info in suggestion.items():
                if name in fields and fields[name] is None:
                    fields[name] = info["value"]
                    confidence[name] = {"level": "ELIGIBLE_STATISTICS", "evidence": info["label_ids"]}
        candidates = []
        if policy["needs_open_item"]:
            expected_account = fields["debit_account"] if direction == "OUT" else fields["credit_account"]
            for item in bundle["documents"]:
                if item["kind"] != "OPEN_ITEM" or item["currency"] != bank["currency"] or item["counterparty"] != fields["counterparty"] or item["account"] != expected_account:
                    continue
                if (direction == "OUT" and item["amount_minor"] >= 0) or (direction == "IN" and item["amount_minor"] <= 0) or item["item_type"] != "INVOICE":
                    continue
                remaining = available(item) if available else abs(item["amount_minor"])
                if remaining > 0:
                    candidates.append({"open_item_id": item["id"], "item_key": item_key(item), "invoice_reference": item.get("invoice_reference"), "available_minor": remaining, "score": 100 if item.get("invoice_reference") in bank.get("invoice_references", []) else 10})
            result["candidates"] = sorted(candidates, key=lambda r: (-r["score"], r["invoice_reference"] or ""))
            explicit = [c for c in candidates if c["score"] == 100]
            chosen = explicit if explicit else candidates if len(candidates) == 1 else []
            if len(chosen) > 1 and sum(c["available_minor"] for c in chosen) != abs(bank["amount_minor"]):
                chosen = []
            if chosen:
                remaining = abs(bank["amount_minor"])
                for candidate in chosen:
                    value = min(candidate["available_minor"], remaining)
                    if value:
                        result["allocations"].append({**candidate, "amount_minor": value})
                        remaining -= value
                result["unallocated_minor"] = remaining
            if result["unallocated_minor"]:
                constraints.append("ALLOCATION_REQUIRES_REVIEW")
        else:
            result["unallocated_minor"] = 0
        if policy.get("journal_lines"):
            proposal_lines, line_failure = self._proposal_lines(policy, bank, cutoff)
            result["lines"] = proposal_lines
            if line_failure:
                constraints.append(line_failure)
        elif learning and learning.get("pattern_lines"):
            cash = result.get("cash_leg", {}).get("account")
            learned_lines = materialize_journal_pattern(learning["pattern_lines"], direction=direction,
                                                        cash_account=cash or "", amount_minor=abs(bank["amount_minor"]),
                                                        currency=bank["currency"], dimensions={**learning.get("fields", {}), **learning.get("dimensions", {})})
            if learned_lines:
                result["lines"] = learned_lines
            else:
                constraints.append("JOURNAL_PATTERN_MULTILINE_WAIT")
        stages.append({"step": "doi_chieu", "candidates": result["candidates"]})
        constraints.extend(self.validate_fields(fields, bank["business_date"], cutoff, policy["required_fields"]))
        stages.append({"step": "rang_buoc", "failures": list(constraints)})
        stages.append({"step": "xep_hang", "policy_version": selected["id"] if selected else "JOURNAL_PATTERN", "scores_are_probabilities": False})
        stages.append({"step": "tin_cay", "fields": confidence})
        result["completeness"] = "FULL" if not constraints else "PARTIAL" if any(fields.values()) else "NONE"
        if any(c in constraints for c in ("LOCKED_PERIOD", "ALREADY_POSTED_OR_DUPLICATE_REFERENCE", "POSTING_EVIDENCE_AMBIGUOUS", "IDENTIFIER_CONFLICT", "TEMPLATE_IDENTIFIER_CONFLICT", "MULTILINE_TEMPLATE_REQUIRES_REVIEW", "ZERO_AMOUNT")):
            result["completeness"] = "NONE"
            result["allocations"] = []
        return result

    def _document_result(self, record, source_kind, direction):
        fields = {name: None for name in FIELDS}
        return {"bank_id": record["id"], "document_id": record["id"], "source_kind": source_kind,
                "business_date": record["business_date"], "amount_minor": record["amount_minor"], "currency": record["currency"],
                "direction": direction, "fields": fields,
                "confidence": {name: {"level": "UNKNOWN", "evidence": []} for name in FIELDS},
                "stages": [], "constraints": [], "warnings": [], "candidates": [], "allocations": [],
                "completeness": "NONE", "unallocated_minor": 0, "score_is_probability": False,
                "baseline": "A", "lines": [], "contract_version": 3}

    def _catalog_counterparty(self, tax_id, business_date, cutoff):
        if not tax_id:
            return None, []
        resolved = self.knowledge.resolve_identifier("TAX_ID", tax_id, business_date, cutoff, include_pending=self.include_pending)
        parties = {entry["counterparty"] for entry in resolved["matches"]}
        return next(iter(parties)) if len(parties) == 1 else None, resolved["matches"]

    def _invoice_keyword_fields(self, invoice, cutoff):
        text = " ".join(str(line.get("description", "")) for line in invoice.get("lines", []))
        text = normalize_text(text)
        selected = []
        for row in self._query(invoice["business_date"], cutoff, "INVOICE_KEYWORD"):
            payload = row["payload"]
            if payload.get("direction") and payload["direction"] != invoice.get("direction"):
                continue
            terms = payload.get("keywords", [])
            if isinstance(terms, str):
                terms = [terms]
            if not isinstance(terms, list) or not terms or not all(isinstance(term, str) and term for term in terms):
                continue
            if all(normalize_text(term) in text for term in terms):
                selected.append(row)
        values = {}
        for row in selected:
            for field, value in row["payload"].get("fields", {}).items():
                if field in FIELDS and value:
                    values.setdefault(field, []).append((value, row))
        fields, evidence, conflicts, levels = {}, {}, [], {}
        for field, values_for_field in values.items():
            options = {value for value, _ in values_for_field}
            if len(options) == 1:
                fields[field] = next(iter(options))
                evidence[field] = [row["id"] for _, row in values_for_field]
                levels[field] = "APPROVED_INVOICE_KEYWORD" if all(row.get("approval_state") == "APPROVED" for _, row in values_for_field) else "PENDING_INVOICE_KEYWORD"
            else:
                conflicts.append("INVOICE_KEYWORD_CONFLICT_" + field.upper())
        return fields, evidence, conflicts, levels

    def _invoice_policy(self, invoice, fields, cutoff):
        """Match only explicit, effective invoice policies; no static MST mapping."""
        candidates = []
        for row in self._query(invoice["business_date"], cutoff, "INVOICE_POLICY"):
            payload = row["payload"]
            if payload.get("direction") and payload["direction"] != invoice.get("direction"):
                continue
            if payload.get("seller_tax_id") and payload["seller_tax_id"] != invoice.get("seller_tax_id"):
                continue
            if payload.get("expense") and payload["expense"] != fields.get("expense"):
                continue
            if payload.get("project") and payload["project"] != fields.get("project"):
                continue
            threshold = payload.get("min_total_minor")
            if threshold is not None and (type(threshold) is not int or invoice["amount_minor"] < threshold):
                continue
            candidates.append(row)
        if len(candidates) != 1:
            return None, "INVOICE_POLICY_CONFLICT" if len(candidates) > 1 else "INVOICE_ACCOUNT_EVIDENCE_MISSING"
        return candidates[0], None

    @staticmethod
    def _account_from_value(value):
        import re
        matches = re.findall(r"(?<!\d)(\d{3,8})(?!\d)", str(value or ""))
        return matches[0] if matches else None

    @staticmethod
    def _hard_key_value(payload):
        """Recover the business key, never the provenance-shaped logical key."""
        source = payload.get("source_row", {})
        if not isinstance(source, dict):
            source = {}
        return str(payload.get("source_key") or source.get("MST") or source.get("Mã số thuế") or "").strip()

    def _hard_key_account(self, payload):
        """Read an account only from a declared hard-key source column."""
        source = payload.get("source_row", {})
        if not isinstance(source, dict):
            return None
        preferred = ("TK hay dùng", "Tài khoản hay dùng", "Tài khoản", "Bút toán", "TK Nợ", "TK Có")
        for name in preferred:
            account = self._account_from_value(source.get(name))
            if account:
                return account
        # Workbook revisions have changed the visible column label.  Restrict
        # this fallback to labels that explicitly mean an account, so numeric
        # tax IDs, row numbers and provenance are never interpreted as GLs.
        for name, value in source.items():
            normalized = normalize_text(str(name))
            if "TAI KHOAN" in normalized or normalized.startswith("TK "):
                account = self._account_from_value(value)
                if account:
                    return account
        return None

    def _invoice_mst_account_fields(self, invoice, cutoff, purchase):
        """Collect account evidence from posted invoice journals and hard MST keys.

        Imported trees remain PENDING, so this function never calls them an
        approved policy.  It simply exposes their provenance to the quick
        proposal and leaves accounting review explicit.
        """
        tax_id = invoice.get("seller_tax_id") if purchase else invoice.get("buyer_tax_id")
        number = str(invoice.get("number") or "")
        values, evidence = {"debit_account": [], "credit_account": []}, {"debit_account": [], "credit_account": []}
        for row in self.store.conn.execute("SELECT id FROM documents WHERE kind='JOURNAL'"):
            journal = __import__('kho_tri_thuc.ha_tang.runtime', fromlist=['document']).document(self.store, row[0], cutoff)
            if number and str(journal.get("invoice_reference") or "") != number:
                continue
            for line in journal.get("lines", []):
                account = str(line.get("account") or "")
                if purchase and int(line.get("debit_minor", 0) or 0) and not account.startswith("1331"):
                    values["debit_account"].append(account); evidence["debit_account"].append(journal["id"])
                if not purchase and int(line.get("credit_minor", 0) or 0) and not account.startswith("33311"):
                    values["credit_account"].append(account); evidence["credit_account"].append(journal["id"])
        for row in self._query(invoice["business_date"], cutoff, "HARD_KEY"):
            if not tax_id or self._hard_key_value(row["payload"]) != str(tax_id).strip():
                continue
            account = self._hard_key_account(row["payload"])
            field = "debit_account" if purchase else "credit_account"
            if account:
                values[field].append(account); evidence[field].append(row["id"])
        result = {}
        for field, candidates in values.items():
            options = set(candidates)
            if len(options) == 1:
                result[field] = {"value": next(iter(options)), "evidence": evidence[field],
                                 "level": "PENDING_INVOICE_JOURNAL" if any(identifier for identifier in evidence[field]) else "UNKNOWN"}
        return result

    def _invoice_lines(self, invoice, fields, *, purchase: bool):
        net, tax, total = invoice.get("net_minor"), invoice.get("tax_minor"), invoice.get("total_minor", invoice["amount_minor"])
        if not isinstance(net, int) or not isinstance(tax, int) or not isinstance(total, int) or net + tax != total:
            return [], "INVOICE_LINE_TOTAL_UNRESOLVED"
        debit, credit = fields["debit_account"], fields["credit_account"]
        if not debit or not credit:
            return [], "INVOICE_ACCOUNT_EVIDENCE_MISSING"
        lines = []
        if purchase:
            detail = [line for line in invoice.get("lines", []) if isinstance(line.get("net_minor"), int) and line["net_minor"]]
            if detail and sum(line["net_minor"] for line in detail) == net:
                for index, line in enumerate(detail, 1):
                    lines.append({"line_id": "NET-" + str(index), "account": debit, "currency": invoice["currency"], "debit_minor": line["net_minor"], "credit_minor": 0,
                                  "tax_rate": line.get("tax_rate"), "tax_basis": "INVOICE_LINE:" + str(line.get("line_id", index)), "state": "READY", "dimensions": {"project": fields.get("project"), "expense": fields.get("expense")}})
            else:
                lines.append({"line_id": "NET", "account": debit, "currency": invoice["currency"], "debit_minor": net, "credit_minor": 0, "tax_basis": "INVOICE_HEADER", "state": "READY", "dimensions": {"project": fields.get("project"), "expense": fields.get("expense")}})
            if tax:
                lines.append({"line_id": "VAT", "account": "1331", "currency": invoice["currency"], "debit_minor": tax, "credit_minor": 0, "tax_basis": "INVOICE_HEADER", "state": "READY", "dimensions": {}})
            lines.append({"line_id": "PAYABLE", "account": credit, "currency": invoice["currency"], "debit_minor": 0, "credit_minor": total, "tax_basis": "INVOICE_HEADER", "state": "READY", "dimensions": {}})
        else:
            lines.append({"line_id": "RECEIVABLE", "account": debit, "currency": invoice["currency"], "debit_minor": total, "credit_minor": 0, "tax_basis": "INVOICE_HEADER", "state": "READY", "dimensions": {}})
            lines.append({"line_id": "REVENUE", "account": credit, "currency": invoice["currency"], "debit_minor": 0, "credit_minor": net, "tax_basis": "INVOICE_HEADER", "state": "READY", "dimensions": {"project": fields.get("project"), "expense": fields.get("expense")}})
            if tax:
                lines.append({"line_id": "VAT", "account": "33311", "currency": invoice["currency"], "debit_minor": 0, "credit_minor": tax, "tax_basis": "INVOICE_HEADER", "state": "READY", "dimensions": {}})
        if sum(line["debit_minor"] for line in lines) != sum(line["credit_minor"] for line in lines):
            return [], "MULTILINE_UNBALANCED"
        return lines, None

    def _preview_invoice(self, invoice, cutoff):
        direction = invoice.get("direction") or ("MUA_VAO" if invoice.get("buyer_tax_id") == self.store.config.entity_tax_id else "BAN_RA")
        purchase = direction == "MUA_VAO"
        result = self._document_result(invoice, "INVOICE", direction)
        fields, constraints, warnings = result["fields"], result["constraints"], result["warnings"]
        if invoice.get("related_invoice") or invoice.get("invoice_relation") in {"ADJUSTMENT", "REPLACEMENT", "CANCELLED"}:
            constraints.append("RELATED_INVOICE_REVIEW")
        tax_id = invoice.get("seller_tax_id") if purchase else invoice.get("buyer_tax_id")
        counterparty, evidence = self._catalog_counterparty(tax_id, invoice["business_date"], cutoff)
        if counterparty:
            fields["counterparty"] = counterparty
            result["confidence"]["counterparty"] = {"level": "VERIFIED_IDENTIFIER", "evidence": [item["knowledge_id"] for item in evidence]}
        else:
            constraints.append("OUTSIDE_CATALOG_TAXID")
        if purchase and invoice.get("buyer_tax_id") and invoice.get("buyer_tax_id") != self.store.config.entity_tax_id:
            fields.update(debit_account="1388", credit_account="33111")
            constraints.append("CHI_HO_REVIEW")
            result["stages"].append({"step": "M7_chi_ho", "status": "WAIT_REVIEW"})
        else:
            mst_fields = self._invoice_mst_account_fields(invoice, cutoff, purchase)
            for name, info in mst_fields.items():
                if fields.get(name) is None:
                    fields[name] = info["value"]
                    result["confidence"][name] = {"level": info["level"], "evidence": info["evidence"]}
            keyword_fields, keyword_evidence, conflicts, keyword_levels = self._invoice_keyword_fields(invoice, cutoff)
            constraints.extend(conflicts)
            for name, value in keyword_fields.items():
                if fields[name] is None:
                    fields[name] = value
                    result["confidence"][name] = {"level": keyword_levels[name], "evidence": keyword_evidence[name]}
            policy, failure = self._invoice_policy(invoice, fields, cutoff)
            if policy:
                for name, value in policy["payload"].get("fields", {}).items():
                    if name in fields and fields[name] is None:
                        fields[name] = value
                        level = "APPROVED_INVOICE_POLICY" if policy.get("approval_state") == "APPROVED" else "PENDING_INVOICE_POLICY"
                        result["confidence"][name] = {"level": level, "evidence": [policy["id"]]}
            else:
                constraints.append(failure)
            if purchase:
                fields["credit_account"] = fields["credit_account"] or "33111"
                if not fields.get("project"):
                    constraints.append("PROJECT_EVIDENCE_MISSING")
            else:
                fields["debit_account"] = fields["debit_account"] or "131"
        if purchase and self.store.config.vat_payment_evidence_threshold_minor and invoice["amount_minor"] >= self.store.config.vat_payment_evidence_threshold_minor:
            warnings.append("VAT_PAYMENT_EVIDENCE_PENDING")
        lines, failure = self._invoice_lines(invoice, fields, purchase=purchase)
        result["lines"] = lines
        if failure:
            constraints.append(failure)
        required = ["counterparty", "debit_account", "credit_account"]
        constraints.extend(self.validate_fields(fields, invoice["business_date"], cutoff, required))
        result["stages"].extend([{ "step": "nhan_dien_doi_tuong", "evidence": len(evidence)}, {"step": "tu_khoa_hoa_don", "status": "DONE"}, {"step": "mau_hoa_don", "status": "DONE"}])
        result["completeness"] = "FULL" if not constraints else "PARTIAL" if any(fields.values()) else "NONE"
        return result

    def _preview_base(self, base, cutoff):
        result = self._document_result(base, "BASE", "MUA_VAO")
        fields, constraints = result["fields"], result["constraints"]
        party, evidence = self._catalog_counterparty(base.get("beneficiary_tax_id"), base["business_date"], cutoff)
        if not party and base.get("beneficiary_account"):
            resolved = self.knowledge.resolve_identifier("BANK_ACCOUNT", base["beneficiary_account"], base["business_date"], cutoff, include_pending=self.include_pending)
            parties = {item["counterparty"] for item in resolved["matches"]}
            party = next(iter(parties)) if len(parties) == 1 else None
            evidence = resolved["matches"]
        if party:
            fields["counterparty"] = party
            result["confidence"]["counterparty"] = {"level": "VERIFIED_IDENTIFIER", "evidence": [item["knowledge_id"] for item in evidence]}
        else:
            constraints.append("OUTSIDE_CATALOG_BASE_COUNTERPARTY")
        catalog = self.catalog(base["business_date"], cutoff)
        for field, kind, source in (("project", "PROJECT", "project_raw"), ("expense", "EXPENSE", "expense_raw")):
            value = base.get(source)
            if value and (kind, value) in catalog:
                fields[field] = value
                result["confidence"][field] = {"level": "BASE_SOURCE_AND_APPROVED_CATALOG", "evidence": [catalog[(kind, value)]["id"]]}
            elif value:
                constraints.append("OUTSIDE_CATALOG_" + kind)
            else:
                constraints.append("BASE_" + source.upper() + "_MISSING")
        fields["credit_account"] = "33111"
        # Account selection remains evidence-based; a Base code alone cannot invent it.
        policy, failure = self._invoice_policy({**base, "direction": "MUA_VAO", "seller_tax_id": None}, fields, cutoff)
        if policy:
            fields["debit_account"] = policy["payload"].get("fields", {}).get("debit_account")
            result["confidence"]["debit_account"] = {"level": "APPROVED_INVOICE_POLICY", "evidence": [policy["id"]]}
        else:
            constraints.append(failure)
        if all(fields.get(key) for key in ("counterparty", "debit_account", "credit_account", "project", "expense")) and base["amount_minor"] > 0:
            amount = base["amount_minor"]
            result["lines"] = [{"line_id": "BASE_NET", "account": fields["debit_account"], "currency": base["currency"], "debit_minor": amount, "credit_minor": 0, "tax_basis": "BASE_NO_VAT", "state": "READY", "dimensions": {"project": fields["project"], "expense": fields["expense"]}},
                               {"line_id": "BASE_PAYABLE", "account": fields["credit_account"], "currency": base["currency"], "debit_minor": 0, "credit_minor": amount, "tax_basis": "BASE_NO_VAT", "state": "READY", "dimensions": {}}]
        else:
            constraints.append("BASE_EVIDENCE_INCOMPLETE")
        constraints.extend(self.validate_fields(fields, base["business_date"], cutoff, ["counterparty", "debit_account", "credit_account", "project", "expense"]))
        result["stages"].append({"step": "base_cong_no", "status": "WAIT_REVIEW" if constraints else "READY"})
        result["completeness"] = "FULL" if not constraints else "PARTIAL" if any(fields.values()) else "NONE"
        return result

    def _proposal_lines(self, policy, bank, cutoff):
        """Materialize an approved line structure only from invoice evidence or its declared tax rate."""
        evidence = self._invoice_tax_evidence(bank, cutoff)
        lines, debit, credit = [], 0, 0
        for definition in policy["journal_lines"]:
            source = definition["amount_source"]
            if source == "BANK_TOTAL":
                amount = abs(bank["amount_minor"])
                basis = "BANK_AMOUNT"
            elif evidence:
                amount = evidence["net_minor"] if source == "INVOICE_NET" else evidence["tax_minor"]
                basis = evidence["basis"]
            elif definition.get("tax_rate") is not None:
                try:
                    rate = int(definition["tax_rate"].replace("%", ""))
                    if not 0 <= rate <= 100:
                        raise ValueError
                except (AttributeError, ValueError):
                    return [], "MULTILINE_TAX_EVIDENCE_WAIT"
                total = abs(bank["amount_minor"])
                amount = total * 100 // (100 + rate) if source == "INVOICE_NET" else total - (total * 100 // (100 + rate))
                basis = "TEMPLATE_TAX_RATE"
            else:
                return [], "MULTILINE_TAX_EVIDENCE_WAIT"
            line = {"line_id": definition["line_id"], "account": definition["account"], "currency": bank["currency"],
                    "debit_minor": amount if definition["side"] == "DEBIT" else 0,
                    "credit_minor": amount if definition["side"] == "CREDIT" else 0,
                    "tax_rate": definition.get("tax_rate"), "tax_basis": basis,
                    "state": "READY", "dimensions": definition.get("dimensions", {})}
            debit += line["debit_minor"]; credit += line["credit_minor"]; lines.append(line)
        if debit != credit or debit != abs(bank["amount_minor"]):
            return [], "MULTILINE_UNBALANCED"
        return lines, None

    def _invoice_tax_evidence(self, bank, cutoff):
        references = set(bank.get("invoice_references") or [])
        rows = self.store.conn.execute("SELECT id,core_json FROM documents WHERE kind='INVOICE'").fetchall()
        found = []
        from ..ha_tang.runtime import document
        for row in rows:
            invoice = document(self.store, row["id"], cutoff)
            if references and invoice.get("number") not in references and invoice.get("natural_key") not in references:
                continue
            if invoice.get("net_minor") is not None and invoice.get("tax_minor") is not None:
                found.append(invoice)
        if len(found) != 1:
            return None
        invoice = found[0]
        return {"net_minor": invoice["net_minor"], "tax_minor": invoice["tax_minor"], "basis": "JOINED_INVOICE:" + invoice["id"]}
