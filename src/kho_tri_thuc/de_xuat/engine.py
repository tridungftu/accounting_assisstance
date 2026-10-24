from __future__ import annotations

import json
from collections import Counter
from datetime import date, timedelta

from ..ha_tang.primitives import DataError, natural_key, normalize_text, money_minor
from ..tri_thuc.service import Knowledge
from ..tri_thuc.matching import case_matches, choose, matches
from ..giao_dien.v9b import bank_account, journal_suggestion, match_bank_to_journal, materialize_journal_pattern, _opposite_accounts
from ..tri_thuc.ten_doi_tuong import NameIndex, identify_by_name, names_compatible
from ..tri_thuc.ai_cuc_bo import choose_counterparty, local_ai_settings
from ..tri_thuc.lich_su_hoa_don import suggest as invoice_suggest

# Identification levels whose source is a person's or Junsky's explicit record.
# Counterparty identifications good enough to let a single covering open
# item decide the offset account (V11.4).
_CERTAIN_PARTY_LEVELS = frozenset({"VERIFIED_IDENTIFIER", "DIRECTORY_HIGH", "ANH_DA_DUYET", "CATALOG_NAME", "JUNSKY_POSTED", "MACHINE_CHAC_CHAN"})
_TRUSTED_IDENTIFIER_LEVELS = {"ANH_DA_DUYET", "VERIFIED_IDENTIFIER", "DIRECTORY_HIGH", "DIRECTORY_MEDIUM"}
# Keywords the rulebook itself marks as too broad to conclude on their own.
_BROAD_KEYWORDS = {"PHI", "THUE", "THANH TOAN", "CHUYEN TIEN", "HOAN", "HOP DONG", "DICH VU", "TIEN THUE", "NOP TIEN"}

FIELDS = ("counterparty", "debit_account", "credit_account", "project", "expense")


def item_key(item):
    return natural_key(item["account"], item["counterparty"], item["currency"], item["item_id"])


class Engine:
    def __init__(self, store, *, include_pending=False):
        self.store = store
        self.knowledge = Knowledge(store)
        self.include_pending = include_pending
        self.cash_overrides: dict[str, dict] = {}
        # V11: many-rows-to-one-voucher matches computed per run by QuickPosting.
        self.group_matches: dict[str, dict] = {}
        # V11: total of the same day's transfers of one counterparty (≥ 2 rows).
        self.group_totals: dict[str, int] = {}
        # V11: a row found in Junsky shows the voucher's own posting unless the
        # run is a scoring replay (then the voucher is the hidden answer).
        self.fill_from_match = True
        # V11.4 (quick posting only): with no rule and no learned pattern, a
        # certain counterparty's single covering open item may still decide.
        self.open_item_single = False
        # V12 (quick posting): links of earlier invoices to their vouchers, and
        # every posted voucher for the "already in Junsky" check.
        self.invoice_history = None
        self.invoice_answer = None
        # V12: projects of each party's posted vouchers (last 12 months up to
        # the learning cutoff) — the site/zone of the party.
        self.party_projects: dict = {}
        # CRM-01 (TL32 §3.2): fact hợp đồng/lịch có hiệu lực theo đối tượng, do lớp gọi cung cấp từ K2 kèm provenance —
        # {counterparty: [{hop_dong_id, phien_ban_id, hieu_luc_tu, hieu_luc_den, currency, tai_khoan, du_an, dot: [...], provenance}]}.
        self.contract_facts: dict[str, list[dict]] = {}

    def _runtime_settings(self):
        defaults = {"object_learning_from": "2026-07-01", "description_similarity_threshold": 0.8,
                    "own_counterparty_codes": [], "learning_cutoff": "", "scoring_mode": False, "local_ai": {}}
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

    def own_words(self) -> frozenset:
        """Distinctive words of the own entity's name (never evidence of similarity)."""
        cached = getattr(self, "_own_words_cache", None)
        if cached is None:
            from ..tri_thuc.ten_doi_tuong import distinctive_tokens
            codes, words = self._own_codes(), set()
            if codes:
                for (core,) in self.store.conn.execute("SELECT core_json FROM documents WHERE kind='COUNTERPARTY'"):
                    try:
                        value = json.loads(core)
                    except (TypeError, json.JSONDecodeError):
                        continue
                    if str(value.get("code") or "") in codes:
                        words.update(distinctive_tokens(str(value.get("name") or "")))
            cached = self._own_words_cache = frozenset(words)
        return cached

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

    def name_index(self, date, cutoff):
        """NameIndex over the counterparty catalog, memoized like catalog()."""
        memo = self.__dict__.setdefault("_name_index_memo", {})
        epoch = self.store.conn.execute("SELECT revision FROM knowledge_epoch WHERE id=1").fetchone()[0]
        key = (date, cutoff, epoch)
        if key not in memo:
            if len(memo) > 8:
                memo.clear()
            entries = [(code, row["payload"].get("name") or "") for (kind, code), row in self.catalog(date, cutoff).items() if kind == "COUNTERPARTY"]
            memo[key] = NameIndex(entries)
        return memo[key]

    def _catalog_name(self, code, date, cutoff):
        row = self.catalog(date, cutoff).get(("COUNTERPARTY", str(code or "")))
        return (row["payload"].get("name") or "") if row else ""

    def _party_usage(self, bundle):
        """code → (count, last day) over BR/BP vouchers; memoized per bundle."""
        memo = self.__dict__.setdefault("_party_usage_memo", {})
        key = id(bundle)
        if key not in memo:
            from ..giao_dien.v9b import _is_bank_journal
            usage: dict[str, list] = {}
            limit = self._learning_cutoff()
            for journal in bundle["documents"]:
                if journal["kind"] != "JOURNAL" or not _is_bank_journal(journal):
                    continue
                if limit and str(journal.get("business_date") or "") > limit:
                    continue
                code = str(journal.get("counterparty") or "")
                if not code:
                    continue
                entry = usage.setdefault(code, [0, ""])
                entry[0] += 1
                entry[1] = max(entry[1], str(journal.get("business_date") or ""))
            memo.clear()
            memo[key] = usage
        return memo[key]

    def _prefer_used_code(self, party, statement_name, bundle, date, cutoff):
        """Same name under several codes: keep the one the ledger actually uses."""
        if not party or not statement_name:
            return party, None
        twins = self.name_index(date, cutoff).exact(statement_name)
        if len(twins) < 2 or party not in twins:
            return party, None
        usage = self._party_usage(bundle)
        ranked = sorted(twins, key=lambda code: (usage.get(code, [0, ""])[0], usage.get(code, [0, ""])[1]), reverse=True)
        best = ranked[0]
        if best != party and usage.get(best, [0, ""])[0] > usage.get(party, [0, ""])[0]:
            return best, {"from": party, "to": best, "twins": twins, "used": usage.get(best, [0, ""])[0]}
        return party, None

    @staticmethod
    def _weak_rule(selected):
        """A rulebook row that may not outrank evidence learned from the ledger.

        Keyword-only rules (bậc 5), draft rows below 0.9 stability or seen
        fewer than three times are suggestions, not knowledge (V11, H4/C).
        """
        if not selected or selected.get("approval_state") == "APPROVED":
            return False
        payload = selected.get("payload", {})
        source = payload.get("source_row") or {}
        if not source:
            return False  # not a rulebook row: nothing measured, nothing to demote on
        try:
            stability = float(str(source.get("do_on_dinh", "1")).replace(",", "."))
        except ValueError:
            stability = 1.0
        try:
            seen = int(str(source.get("so_lan_gap", "0")).strip() or 0)
        except ValueError:
            seen = 0
        if stability < 0.9 or seen < 3 or str(source.get("trang_thai") or "").upper() == "NHAP":
            return True
        # A single over-broad word ("PHI", "THANH TOAN"…) needs a spotless,
        # well-populated record before it may stand on its own.
        keyword = str(source.get("tu_khoa") or "").strip().upper()
        if int(payload.get("tier") or 0) == 5 and keyword in _BROAD_KEYWORDS and (stability < 1.0 or seen < 5):
            return True
        return False

    def _fill_from_voucher(self, bank, journal_id, cutoff, fields, confidence, result, direction):
        """E1: a row already in Junsky shows that voucher's posting (V11)."""
        from ..ha_tang.runtime import document
        try:
            journal = document(self.store, journal_id, cutoff)
        except DataError:
            return False
        own = self._own_codes()
        party = str(journal.get("counterparty") or "")
        evidence = [journal_id]
        if party and party not in own and not fields.get("counterparty"):
            fields["counterparty"] = party
            confidence["counterparty"] = {"level": "JUNSKY_POSTED", "evidence": evidence}
        for name in ("project", "expense"):
            value = str(journal.get(name) or "")
            if value and not fields.get(name):
                fields[name] = value
                confidence[name] = {"level": "JUNSKY_POSTED", "evidence": evidence}
        primary, lines = _opposite_accounts(journal, direction)
        if primary:
            field = "credit_account" if direction == "IN" else "debit_account"
            if not fields.get(field):
                fields[field] = primary
                confidence[field] = {"level": "JUNSKY_POSTED", "evidence": evidence}
            result["posted_pattern"] = {"lines": lines, "cost_center": journal.get("cost_center") or None, "voucher_number": journal.get("voucher_number") or ""}
        return True

    def _open_item_evidence(self, bank, bundle, fields, confidence, result, direction, group_total=None, *, exact_only=False):
        """B3: open receivables/payables of the identified counterparty as offset-account evidence."""
        party = fields.get("counterparty")
        if not group_total:
            group_total = self.group_totals.get(bank["id"])
        field = "credit_account" if direction == "IN" else "debit_account"
        current_level = (confidence.get(field) or {}).get("level", "UNKNOWN")
        weak = current_level in {"UNKNOWN", "PENDING_PATTERN_WEAK", "PENDING_RULE_WEAK", "ELIGIBLE_STATISTICS"}
        # V11.4 (CFO 13/10, phương án 2): even a unanimous pattern learned from
        # old vouchers yields to the counterparty's own open item.
        history = current_level == "PENDING_PATTERN_STRONG"
        if not party or (fields.get(field) and not weak and not history):
            return
        amount = abs(int(bank.get("amount_minor", 0) or 0))
        items = [item for item in bundle["documents"] if item["kind"] == "OPEN_ITEM" and item.get("counterparty") == party
                 and item.get("currency") == bank.get("currency") and item.get("item_type") == "INVOICE"
                 and ((direction == "IN" and int(item.get("amount_minor", 0) or 0) > 0) or (direction == "OUT" and int(item.get("amount_minor", 0) or 0) < 0))]
        if not items:
            return
        accounts = {}
        for item in items:
            accounts.setdefault(str(item.get("account") or ""), []).append(item)
        accounts.pop("", None)
        if not accounts:
            return
        exact = [account for account, rows in accounts.items() if any(abs(int(row.get("amount_minor", 0) or 0)) in {amount, group_total or -1} for row in rows)]
        # An account whose open total cannot cover this payment is not the one.
        covering = [account for account, rows in accounts.items() if sum(abs(int(row.get("amount_minor", 0) or 0)) for row in rows) >= amount]
        if not exact and len(covering) == 1 and len(accounts) > 1:
            accounts = {covering[0]: accounts[covering[0]], **{account: rows for account, rows in accounts.items() if account != covering[0]}}
            exact = []
            single_cover = covering[0]
        else:
            single_cover = None
        options = [{"account": account, "count": len(rows), "open_minor": sum(abs(int(row.get("amount_minor", 0) or 0)) for row in rows)} for account, rows in accounts.items()]
        options.sort(key=lambda item: (-item["open_minor"], item["account"]))
        previous = fields.get(field)
        if previous and previous not in accounts:
            options.append({"account": previous, "count": 0, "open_minor": 0, "note": "theo chứng từ cũ"})
        result["account_options"] = options
        chosen, level = None, None
        if len(exact) == 1:
            chosen, level = exact[0], "OPEN_ITEM_LEVEL_0"
        elif len(accounts) == 1 or single_cover:
            chosen = single_cover or next(iter(accounts))
            # V11.4: a counterparty identified for certain whose only open
            # account can cover the amount is as good as a learned pattern
            # (customer paying its receivable, supplier being paid).
            party_level = (confidence.get("counterparty") or {}).get("level")
            covers = sum(abs(int(row.get("amount_minor", 0) or 0)) for row in accounts[chosen]) >= amount
            level = "OPEN_ITEM_SINGLE" if covers and party_level in _CERTAIN_PARTY_LEVELS else "OPEN_ITEM_HINT"
        if exact_only and not (level == "OPEN_ITEM_LEVEL_0" or (level == "OPEN_ITEM_SINGLE" and self.open_item_single)):
            chosen = None
        if chosen and history and level not in ("OPEN_ITEM_LEVEL_0", "OPEN_ITEM_SINGLE"):
            chosen = None  # a mere hint never beats a unanimous pattern
        if chosen and (not previous or weak or history):
            if previous and previous != chosen:
                result.setdefault("warnings", []).append("OPEN_ITEM_OVERRIDES_PATTERN")
                result["lines"] = []
            fields[field] = chosen
            confidence[field] = {"level": level, "evidence": [row["id"] for row in accounts[chosen]][:5]}
            if level in ("OPEN_ITEM_LEVEL_0", "OPEN_ITEM_SINGLE"):
                # V11.4 (CFO 13/10): the open item also carries the project; it
                # beats a project borrowed from older, differently booked vouchers.
                source_rows = accounts[chosen]
                if level == "OPEN_ITEM_LEVEL_0":
                    source_rows = [row for row in source_rows if abs(int(row.get("amount_minor", 0) or 0)) in {amount, group_total or -1}] or source_rows
                projects = {str(row.get("project") or "") for row in source_rows} - {""}
                project_level = (confidence.get("project") or {}).get("level", "UNKNOWN")
                if len(projects) == 1 and (not fields.get("project") or project_level in {"UNKNOWN", "PENDING_PATTERN_WEAK", "PENDING_PATTERN_STRONG", "PENDING_RULE_WEAK", "ELIGIBLE_STATISTICS"}):
                    fields["project"] = next(iter(projects))
                    confidence["project"] = {"level": level, "evidence": [row["id"] for row in source_rows][:5]}

    def _contract_evidence(self, bank, fields, confidence, result, constraints, direction):
        """TL32 §3.2 (CFO): tiền về chưa rõ — có hợp đồng hiệu lực NGÀY TIỀN VỀ của đúng đối tượng → TK phải thu theo hợp đồng (131),
        đợt gần nhất còn phải thu làm bằng chứng; chưa có → giữ nhánh trước hợp đồng (344). Chỉ thay mức yếu/chờ duyệt (không vượt
        mẫu đã duyệt, chứng từ Junsky hay công nợ khớp đúng số). Không phân bổ: tiền vượt phần còn lại của đợt / nhiều hợp đồng → chờ hỏi."""
        party = fields.get("counterparty")
        if direction != "IN" or not party or not self.contract_facts.get(party):
            return
        day = bank["business_date"]
        facts = [f for f in self.contract_facts[party] if f.get("currency") == bank.get("currency")
                 and f["hieu_luc_tu"] <= day and (not f.get("hieu_luc_den") or day < f["hieu_luc_den"])]
        if not facts:
            return
        field = "credit_account"
        level = (confidence.get(field) or {}).get("level", "UNKNOWN")
        if fields.get(field) and level not in {"UNKNOWN", "PENDING_PATTERN_WEAK", "PENDING_RULE_WEAK", "PENDING_RULE_STRONG", "ELIGIBLE_STATISTICS", "OPEN_ITEM_HINT"}:
            result["contract_evidence"] = {"applied": False, "reason": "STRONGER_EVIDENCE:" + level, "contracts": [f["hop_dong_id"] for f in facts]}
            return
        accounts = {f["tai_khoan"] for f in facts}
        if len(accounts) != 1:
            constraints.append("CONTRACT_ACCOUNT_CONFLICT")
            return
        account = next(iter(accounts))
        amount = abs(int(bank.get("amount_minor", 0) or 0))
        evidence, nearest_all = [], []
        for fact in facts:
            open_rows = [d for d in fact.get("dot", []) if int(d.get("con_lai_minor") or 0) > 0]
            open_rows.sort(key=lambda d: (d.get("han") is None, d.get("han") or "", d.get("loai") != "COC", int(d.get("dot") or 0)))
            nearest = open_rows[0] if open_rows else None
            nearest_all.append(nearest)
            evidence.append({"hop_dong_id": fact["hop_dong_id"], "phien_ban_id": fact.get("phien_ban_id"), "dot_gan_nhat": nearest, "provenance": fact.get("provenance")})
        previous = fields.get(field)
        if previous and previous != account:
            result.setdefault("warnings", []).append("CONTRACT_FACT_OVERRIDES_PENDING_RULE")
            result["lines"] = []
        fields[field] = account
        confidence[field] = {"level": "CONTRACT_FACT", "evidence": ["HOP_DONG:" + str(f["hop_dong_id"]) for f in facts][:5]}
        projects = {f.get("du_an") for f in facts} - {None, ""}
        if len(projects) == 1 and (not fields.get("project") or (confidence.get("project") or {}).get("level") in {"UNKNOWN", "PENDING_PATTERN_WEAK", "PENDING_RULE_WEAK", "ELIGIBLE_STATISTICS"}):
            fields["project"] = next(iter(projects))
            confidence["project"] = {"level": "CONTRACT_FACT", "evidence": confidence[field]["evidence"]}
        if len(facts) > 1:
            constraints.append("CONTRACT_MULTIPLE_WAIT")
        elif nearest_all[0] is None:
            constraints.append("CONTRACT_NO_OPEN_INSTALLMENT_WAIT")
        elif amount > int(nearest_all[0]["con_lai_minor"]):
            constraints.append("CONTRACT_AMOUNT_EXCEEDS_INSTALLMENT_WAIT")
        result["contract_evidence"] = {"applied": True, "account": account, "previous_account": previous, "auto_allocate": False, "facts": evidence}
        result["why"] = ("Đã có hợp đồng hiệu lực ngày tiền về → Có " + account + " theo đợt gần nhất (đề xuất chờ duyệt, chưa phân bổ vào đợt; "
                         "nối tiền–đợt làm ở CRM).")

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
        if journal_match["status"] != "UNIQUE" and bank["id"] in self.group_matches:
            # V11 (H8): several transfers of one day ↔ one voucher.
            journal_match = dict(self.group_matches[bank["id"]])
        result["journal_match"] = journal_match
        result["potential_existing"] = journal_match["status"] == "UNIQUE"
        if journal_match["status"] == "AMBIGUOUS":
            result["warnings"] = ["JOURNAL_MATCH_AMBIGUOUS"]
        group_total = (journal_match.get("group") or {}).get("total_minor") if journal_match["status"] == "UNIQUE" else None
        party, party_confidence, identification_failure, identification = self._identify_counterparty(bank, cutoff)
        # V11 (H11/D1): an identifier learned from one doubtful pair must not
        # override a statement name that plainly says someone else.
        statement_name = str(bank.get("counterparty_name") or "")
        if party and statement_name and party_confidence.get("level") not in _TRUSTED_IDENTIFIER_LEVELS:
            catalog_name = self._catalog_name(party, bank["business_date"], cutoff)
            if catalog_name and not names_compatible(statement_name, catalog_name):
                # Only set the mapping aside when the statement name itself
                # points at someone else in the catalog; a director paying from a
                # personal account keeps the (weak) mapping, with a note.
                index = self.name_index(bank["business_date"], cutoff)
                other = identify_by_name(index, statement_name, "")
                if other.get("code") and other["code"] != party and other.get("level") in {"CATALOG_NAME", "CATALOG_NAME_FUZZY"}:
                    result["identifier_conflict"] = {"code": party, "name": catalog_name, "level": party_confidence.get("level"), "evidence": party_confidence.get("evidence", [])}
                    party, party_confidence, identification_failure = None, {"level": "UNKNOWN", "evidence": []}, None
                else:
                    result["identifier_note"] = {"code": party, "name": catalog_name}
            elif catalog_name:
                # Same words, another code fits the statement name better
                # (for example two water companies sharing most of a name).
                index = self.name_index(bank["business_date"], cutoff)
                current = index.affinity(statement_name, party)
                better = [item for item in index.fuzzy(statement_name) if item["code"] != party and item["score"] >= 0.8 and item["score"] > current + 0.04]
                if len(better) == 1 or (better and better[0]["score"] - better[1]["score"] >= 0.2):
                    result["identifier_conflict"] = {"code": party, "name": catalog_name, "level": party_confidence.get("level"), "evidence": party_confidence.get("evidence", []), "replaced_by": better[0]["code"]}
                    party = better[0]["code"]
                    # The statement name equal to the better code's catalog name
                    # (bracketed trade name aside) is a certain identification.
                    exact = index.exact(statement_name)
                    party_confidence = {"level": "CATALOG_NAME" if exact == [party] else "CATALOG_NAME_FUZZY", "evidence": ["NAME:" + party]}
        if party and party_confidence.get("level") not in _TRUSTED_IDENTIFIER_LEVELS:
            party, switched = self._prefer_used_code(party, statement_name, bundle, bank["business_date"], cutoff)
            if switched:
                result["code_switched"] = switched
                party_confidence = {"level": "CATALOG_NAME", "evidence": party_confidence.get("evidence", []) + ["NAME:" + party]}
        if identification_failure:
            constraints.append(identification_failure)
        elif party:
            fields["counterparty"] = party
            confidence["counterparty"] = party_confidence
        stages.append({"step": "nhan_dien", "matches": identification})
        if not fields.get("counterparty") and not identification_failure:
            # V11 (H7/H13): the catalog name itself, then the name inside the narrative.
            index = self.name_index(bank["business_date"], cutoff)
            named = identify_by_name(index, statement_name, bank.get("description", ""))
            if named.get("options"):
                result["name_options"] = [{"code": item["code"], "name": item.get("name", ""), "score": item.get("score")} for item in named["options"][:5]]
                result["name_basis"] = named.get("basis")
            if not named.get("code") and len(named.get("options") or []) >= 2:
                chosen = choose_counterparty(local_ai_settings(settings), statement_name, bank.get("description", ""), named["options"])
                if chosen:
                    named = {**named, "code": chosen["code"], "level": "AI_CUC_BO", "ai_reason": chosen.get("reason", "")}
                    result["ai_reason"] = chosen.get("reason", "")
            if named.get("code") and named["code"] not in self._own_codes():
                fields["counterparty"] = named["code"]
                confidence["counterparty"] = {"level": named["level"], "evidence": ["NAME:" + named["code"]]}
        if journal_match["status"] == "UNIQUE" and self.fill_from_match:
            # V11 (H14/E1): the voucher is the answer; show it instead of re-guessing.
            self._fill_from_voucher(bank, journal_match["journal_id"], cutoff, fields, confidence, result, direction)
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
        posted = result.get("posted_pattern")
        if posted and posted.get("lines"):
            # E1: already in Junsky — the voucher's own structure is the proposal.
            selected, failure = None, None
            cash = (self._cash_mapping(bank)[0]) or ""
            policy = {"partition": "JUNSKY_POSTED", "template_id": "JUNSKY_VOUCHER", "direction": direction,
                      "needs_open_item": False, "required_fields": ["debit_account", "credit_account"], "fields": dict(fields)}
            result.update(template_id="JUNSKY_VOUCHER", policy=policy)
            lines = materialize_journal_pattern(posted["lines"], direction=direction, cash_account=cash, amount_minor=abs(bank["amount_minor"]),
                                                currency=bank["currency"], dimensions={"project": fields.get("project"), "expense": fields.get("expense"), "cost_center": posted.get("cost_center")})
            if lines:
                result["lines"] = lines
            result["why"] = "Đã có trong Junsky – số CT " + str(posted.get("voucher_number") or "") + "; bút toán hiển thị theo chính chứng từ đó."
        demoted = None
        if failure == "NO_UNIQUE_APPROVED_TEMPLATE" or (selected and not cases and self._weak_rule(selected)):
            # V9b S6 is deliberately a pending evidence path.  It may propose
            # from earlier BR/BP vouchers when no imported rule applies; it
            # never converts that evidence into an approved template.
            # V11 (H4/C): a weak keyword rule no longer blocks this path; the
            # ledger evidence wins when it is at least as strong.
            cutoff_day = min(bank["business_date"], cutoff[:10])
            if self._learning_cutoff():
                cutoff_day = min(cutoff_day, (date.fromisoformat(self._learning_cutoff()) + timedelta(days=1)).isoformat())
            learning = journal_suggestion(bank, journals, cutoff_day=cutoff_day, own_codes=self._own_codes(),
                                           object_learning_from=str(settings.get("object_learning_from", "2026-07-01")), threshold=threshold,
                                           cash_account=self._cash_mapping(bank)[0] or "", counterparty_code=str(fields.get("counterparty") or ""),
                                           ignore_words=self.own_words())
            if selected and learning:
                offset = "credit_account" if direction == "IN" else "debit_account"
                if learning.get("strength") == "PENDING_PATTERN_STRONG" or (self._weak_rule(selected) and learning.get("fields", {}).get(offset)):
                    # Measured ledger evidence (unanimous, or a clear majority
                    # against a weak rule) replaces the rule; the rule remains a hint.
                    demoted, selected, failure = selected, None, "NO_UNIQUE_APPROVED_TEMPLATE"
                else:
                    learning = None
            elif selected:
                learning = None
        if failure == "NO_UNIQUE_APPROVED_TEMPLATE" and not learning:
            # V11 (B3): no rule, no ledger pattern — an open invoice of the
            # counterparty for exactly this amount (or this day's transfers)
            # names the offset account; a mere hint stays a clickable option.
            offset = "credit_account" if direction == "IN" else "debit_account"
            self._open_item_evidence(bank, bundle, fields, confidence, result, direction, group_total, exact_only=True)
            if fields.get(offset):
                selected, failure = None, None
                policy = {"partition": "OPEN_ITEMS", "template_id": "OPEN_ITEM_EVIDENCE", "direction": direction,
                          "needs_open_item": False, "required_fields": ["debit_account", "credit_account"], "fields": {}}
                result.update(template_id="OPEN_ITEM_EVIDENCE", policy=policy)
        if failure:
            if not learning:
                constraints.append(failure)
                stages.extend([{ "step": s, "status": "BLOCKED"} for s in ("doi_chieu", "rang_buoc", "xep_hang", "tin_cay")])
                return result
            selected = None
            policy = {"partition": "JOURNAL_LEARNING", "template_id": "JOURNAL_PATTERN", "direction": direction,
                      "needs_open_item": False, "required_fields": ["debit_account", "credit_account"], "fields": learning["fields"]}
            result.update(template_id="JOURNAL_PATTERN", policy=policy, learning=learning)
            if demoted:
                source = demoted.get("payload", {}).get("source_row") or {}
                result["demoted_rule"] = {"id": demoted["id"], "code": source.get("ma_quy_tac") or demoted.get("payload", {}).get("template_id"),
                                          "keyword": source.get("tu_khoa") or "", "account": source.get("tk_doi_ung") or "",
                                          "seen": source.get("so_lan_gap"), "right": source.get("so_lan_dung")}
            for name, value in learning["fields"].items():
                if name in fields and fields[name] is None and value:
                    fields[name] = value
                    confidence[name] = {"level": learning["strength"], "evidence": learning["source_ids"]}
        elif (posted and posted.get("lines")) or result.get("template_id") == "OPEN_ITEM_EVIDENCE":
            pass
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
            prefix = policy.get("confirms_counterparty_prefix")
            if prefix and selected.get("approval_state") == "APPROVED":
                # V11.4 (CFO rule): the rule holds only for a recognised employee
                # ("có mã nhân viên"); it then also confirms that identification.
                party = str(fields.get("counterparty") or "")
                if party.startswith(prefix):
                    confidence["counterparty"] = {"level": "APPROVED_TEMPLATE", "evidence": [selected["id"]] + list((confidence.get("counterparty") or {}).get("evidence", []))[:3]}
                else:
                    for name in ("debit_account", "credit_account", "project", "expense"):
                        if (confidence.get(name) or {}).get("evidence") == [selected["id"]]:
                            confidence[name] = {"level": "CFO_RULE_INCOMPLETE", "evidence": [selected["id"]]}
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
        if not (posted and posted.get("lines")):
            self._open_item_evidence(bank, bundle, fields, confidence, result, direction, group_total)
            self._contract_evidence(bank, fields, confidence, result, constraints, direction)
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

    def _invoice_history_fields(self, invoice, fields, result, purchase):
        """V12: account, partner account and dimensions from earlier invoices of the party."""
        suggestion = invoice_suggest(invoice, self.invoice_history or [], ignore_words=self.own_words())
        if not suggestion:
            self._invoice_project(fields, result, None, None)
            return
        account_field, partner_field = ("debit_account", "credit_account") if purchase else ("credit_account", "debit_account")
        result["suggest_accounts"] = [item["account"] for item in suggestion["alternatives"]]
        level = {"STRONG": "PENDING_PATTERN_STRONG", "WEAK": "PENDING_PATTERN_WEAK"}.get(suggestion["strength"])
        learning = {"why": suggestion["why"], "stats": suggestion["stats"], "source_ids": suggestion["source_ids"],
                    "source_vouchers": suggestion["source_vouchers"], "match_basis": "INVOICE_" + suggestion["basis"], "no_stage": True,
                    "fields": {account_field: suggestion["account"], partner_field: suggestion["partner_account"]}}
        result["learning"] = learning
        result["stats"] = suggestion["stats"]
        payer = suggestion.get("employee_payer")
        if purchase and payer and payer["count"] / max(payer["total"], 1) >= 0.3:
            # Junsky books these against the employee who bought them; which
            # employee is not on the invoice, so the counterparty is a guess.
            result["warnings"].append("INVOICE_EMPLOYEE_PAYER")
            result.setdefault("invoice_notes", []).append(
                f"Người bán này thường do nhân viên mua hộ: {payer['count']}/{payer['total']} hóa đơn trước Junsky ghi đối tượng là nhân viên ("
                + ", ".join(payer["codes"][:3]) + ") — cần chọn nhân viên")
            if fields.get("counterparty") and result["confidence"].get("counterparty", {}).get("level") not in (None, "PENDING_PATTERN_WEAK"):
                result["confidence"]["counterparty"] = {"level": "PENDING_PATTERN_WEAK", "evidence": result["confidence"]["counterparty"].get("evidence", [])}
        if not level:
            self._invoice_project(fields, result, suggestion, None)
            return
        evidence = suggestion["source_ids"] or ["INVOICE_HISTORY"]
        fields[account_field] = suggestion["account"]
        result["confidence"][account_field] = {"level": level, "evidence": evidence}
        partner = suggestion["partner_account"]
        if purchase and suggestion["paid_directly"]:
            # The earlier invoices of this seller were posted on the bank
            # payment itself (Nợ chi phí / Có 112); a separate invoice entry
            # would post them twice.
            result["warnings"].append("INVOICE_PAID_DIRECTLY")
            result.setdefault("invoice_notes", []).append(
                f"Hóa đơn trước của người bán này được hạch toán thẳng trên chứng từ chi tiền (Có {partner}) — đề xuất ghi công nợ 33111, xem có trùng khi chi không")
            fields[partner_field] = "33111"
            result["confidence"][partner_field] = {"level": "PENDING_PATTERN_WEAK", "evidence": evidence}
        elif partner:
            fields[partner_field] = partner
            result["confidence"][partner_field] = {"level": level, "evidence": evidence}
        for name, info in suggestion["dimensions"].items():
            if name in ("cost_center", "project") or fields.get(name):
                continue
            fields[name] = info["value"]
            strong = level == "PENDING_PATTERN_STRONG" and info["unanimous"] and info["total"] >= 3
            result["confidence"][name] = {"level": "PENDING_PATTERN_STRONG" if strong else "PENDING_PATTERN_WEAK", "evidence": evidence}
        self._invoice_project(fields, result, suggestion, level)

    def _invoice_project(self, fields, result, suggestion, level):
        """Project of an invoice entry.

        Measured on T8 with learning cut at 30/06: the project the party's own
        vouchers always carry (its site) is right more often than the project
        of similar invoices; the latter is the fallback.  Strong only when both
        agree.
        """
        if fields.get("project"):
            return
        found = Counter(self.party_projects.get(fields.get("counterparty") or "", {}))
        party_project = next(iter(found)) if len(found) == 1 else None
        info = ((suggestion or {}).get("dimensions") or {}).get("project")
        item_project = info["value"] if info else None
        value = party_project or item_project
        if not value:
            return
        fields["project"] = value
        strong = bool(level == "PENDING_PATTERN_STRONG" and party_project and item_project == party_project and info.get("unanimous"))
        evidence = ((suggestion or {}).get("source_ids") or []) or ["INVOICE_HISTORY"]
        if party_project:
            evidence = evidence + ["PARTY_PROJECT:" + party_project]
        result["confidence"]["project"] = {"level": "PENDING_PATTERN_STRONG" if strong else "PENDING_PATTERN_WEAK", "evidence": evidence}
        similar = f"{info['count']}/{info['total']} hóa đơn trước tương tự" if info else ""
        if party_project:
            own = f"chứng từ của đối tác này luôn ghi dự án này ({found[party_project]} chứng từ trong 12 tháng)"
            result["project_why"] = own + (f", {similar} cũng vậy" if item_project == party_project and similar else "")
        else:
            result["project_why"] = "theo " + similar
        if party_project and item_project and item_project != party_project:
            result["warnings"].append("INVOICE_PROJECT_DIFFERS")
            result.setdefault("invoice_notes", []).append(
                f"Dự án: chứng từ của đối tác này luôn ghi {party_project}; hóa đơn tương tự ghi {item_project} — cần xem")
        elif not party_project and found:
            result.setdefault("invoice_notes", []).append(
                "Dự án: chứng từ của đối tác này ghi nhiều dự án (" + ", ".join(sorted(found)) + ") — cần xem")

    def _single_open_account(self, party, prefix):
        if not party:
            return None
        accounts = set()
        for row in self.store.conn.execute("SELECT core_json FROM documents WHERE kind='OPEN_ITEM'"):
            try:
                value = json.loads(row[0])
            except (TypeError, json.JSONDecodeError):
                continue
            if value.get("counterparty") == party and str(value.get("account") or "").startswith(prefix):
                accounts.add(str(value["account"]))
        return next(iter(accounts)) if len(accounts) == 1 else None

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
        elif self.invoice_history is not None and (invoice.get("seller_name") if purchase else invoice.get("buyer_name")):
            # V12: the tax code is not in the catalogue; the name on the invoice may be.
            party_name = invoice.get("seller_name") if purchase else invoice.get("buyer_name")
            named = identify_by_name(self.name_index(invoice["business_date"], cutoff), party_name, "")
            if named.get("code") and named["code"] not in self._own_codes():
                fields["counterparty"] = named["code"]
                result["confidence"]["counterparty"] = {"level": named["level"], "evidence": ["NAME:" + named["code"]]}
                result["name_options"] = named.get("options", [])[:5]
                warnings.append("TAXID_NOT_IN_CATALOG")
                result.setdefault("invoice_notes", []).append("MST trên hóa đơn chưa có trong danh mục — đối tượng tìm theo tên, cần xác nhận")
            else:
                if named.get("options"):
                    result["name_options"] = named["options"][:5]
                constraints.append("OUTSIDE_CATALOG_TAXID")
        else:
            constraints.append("OUTSIDE_CATALOG_TAXID")
        if self.invoice_answer is not None:
            # V12: an invoice whose amounts already sit in a posted voucher is in Junsky.
            posted = self.invoice_answer.link(invoice, fields.get("counterparty") or "")
            if posted:
                result["journal_match"] = {"status": "UNIQUE", "journal_id": posted["journal_id"], "voucher_number": posted["voucher"], "similarity": 1.0, "basis": "INVOICE_AMOUNTS"}
                result["potential_existing"] = True
        if purchase and invoice.get("buyer_tax_id") and invoice.get("buyer_tax_id") != self.store.config.entity_tax_id:
            fields.update(debit_account="1388", credit_account="33111")
            constraints.append("CHI_HO_REVIEW")
            result["stages"].append({"step": "M7_chi_ho", "status": "WAIT_REVIEW"})
        else:
            if self.invoice_history is not None:
                self._invoice_history_fields(invoice, fields, result, purchase)
            # The historical scan by invoice number is slow and, in quick
            # posting, superseded by the measured history above.
            mst_fields = {} if self.invoice_history is not None else self._invoice_mst_account_fields(invoice, cutoff, purchase)
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
            elif not (self.invoice_history is not None and failure == "INVOICE_ACCOUNT_EVIDENCE_MISSING"
                      and fields["debit_account" if purchase else "credit_account"]):
                # V12: the measured invoice history already gave the account;
                # a missing imported policy is not a gap any more.
                constraints.append(failure)
            if purchase:
                fields["credit_account"] = fields["credit_account"] or "33111"
                if not fields.get("project"):
                    constraints.append("PROJECT_EVIDENCE_MISSING")
            elif self.invoice_history is not None:
                # V12: a bare "131" is not a Junsky account; leave it to the
                # customer's history or open items, else ask.
                if not fields["debit_account"]:
                    single = self._single_open_account(fields.get("counterparty"), "131")
                    if single:
                        fields["debit_account"] = single
                        result["confidence"]["debit_account"] = {"level": "OPEN_ITEM_HINT", "evidence": ["OPEN_ITEM:" + single]}
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
