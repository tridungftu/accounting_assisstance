"""V9b local quick posting: evidence may propose; only an explicit decision exports."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook, load_workbook

from ..de_xuat.engine import Engine, FIELDS
from ..ha_tang.primitives import DataError, canonical_json, instant_utc, normalize_text, now_utc, sha256, text_id
from ..ha_tang.runtime import document, documents_bulk, log, transaction, uid
from ..tri_thuc.service import Knowledge
from ..xuat.shadow import ENTRY1_HEADERS, ENTRY2_HEADERS
from .v9b import bank_account, infer_cash_mappings, is_cash_detail, offset_account_ranking, match_bank_groups_to_journal, match_bank_to_journal, _opposite_accounts, fingerprint
from ..nguon.that import parse_invoice_xml
from ..tri_thuc.lich_su_hoa_don import JournalIndex as InvoiceJournalIndex, build_history as build_invoice_history, history_files, invoice_text, month_bounds


STRONG_LEVELS = {
    "APPROVED_TEMPLATE", "APPROVED_KEYWORD", "VERIFIED_IDENTIFIER", "DIRECTORY_HIGH",
    "OPEN_ITEM_LEVEL_0", "CAU_HINH_TK_TIEN", "ANH_DA_DUYET", "PENDING_RULE_STRONG",
    "PENDING_PATTERN_STRONG", "MACHINE_CHAC_CHAN",
    # V11
    "JUNSKY_POSTED", "CATALOG_NAME",
    # V11.4
    "OPEN_ITEM_SINGLE",
}


# Accounts that need a counterparty before an entry can be approved.  The list
# is a setting (``debt_accounts``) awaiting the CFO's confirmation; matching is
# by prefix on numeric chart accounts (e.g. 1388 covers 13881).
DEFAULT_DEBT_ACCOUNTS = ("131", "331", "141", "344", "1388", "3388")
LINE_KEYS = ("side", "account", "amount", "counterparty", "project", "expense", "cost_center")
FIELD_WORDS = {"counterparty": "đối tượng", "debit_account": "Nợ", "credit_account": "Có", "project": "dự án", "expense": "khoản mục"}
LEVEL_WORDS = {
    "VERIFIED_IDENTIFIER": "theo danh bạ/danh mục đã xác nhận",
    "DIRECTORY_HIGH": "theo danh bạ STK (độ tin cậy Cao)",
    "DIRECTORY_MEDIUM": "theo danh bạ STK (độ tin cậy Trung bình)",
    "DIRECTORY_LOW": "theo danh bạ STK (độ tin cậy Thấp)",
    "MACHINE_CHAC_CHAN": "theo nhận diện máy (chắc chắn)",
    "MACHINE_NHAP": "theo nhận diện máy (nháp)",
    "PENDING_IDENTIFIER": "theo định danh chưa xác nhận",
    "ANH_DA_DUYET": "theo lần Anh đã duyệt trước",
    "CAU_HINH_TK_TIEN": "theo cấu hình tài khoản ngân hàng",
    "APPROVED_TEMPLATE": "theo quy tắc đã duyệt",
    "APPROVED_KEYWORD": "theo từ khóa đã duyệt",
    "ELIGIBLE_STATISTICS": "theo thống kê chứng từ cũ",
    # V11
    "JUNSKY_POSTED": "theo chính chứng từ đã có trong Junsky",
    "CATALOG_NAME": "tên trên sao kê trùng tên trong danh mục đối tượng",
    "CATALOG_NAME_FUZZY": "tên trên sao kê gần giống tên trong danh mục (cần xem)",
    "CATALOG_NAME_DESC": "tên tìm thấy trong diễn giải, khớp danh mục (cần xem)",
    "AI_CUC_BO": "AI cục bộ chọn trong các tên gần giống (cần xem)",
    "OPEN_ITEM_LEVEL_0": "khớp hóa đơn/công nợ đang mở của đối tượng",
    "OPEN_ITEM_HINT": "đối tượng đang có công nợ mở trên tài khoản này (cần xem)",
    "OPEN_ITEM_SINGLE": "đối tượng chỉ còn công nợ mở trên tài khoản này và đủ số tiền",
    "CFO_RULE_INCOMPLETE": "theo quy tắc Anh duyệt nhưng chưa nhận ra mã nhân viên trong diễn giải (cần xem)",
}
ERROR_WORDS = {
    "MISSING_DEBIT_ACCOUNT": "thiếu TK Nợ", "MISSING_CREDIT_ACCOUNT": "thiếu TK Có", "MISSING_COUNTERPARTY": "thiếu đối tượng",
    "MISSING_PROJECT": "thiếu dự án", "MISSING_EXPENSE": "thiếu khoản mục",
    "INVALID_DEBIT_ACCOUNT": "TK Nợ không có trong danh mục", "INVALID_CREDIT_ACCOUNT": "TK Có không có trong danh mục",
    "INVALID_COUNTERPARTY": "mã đối tượng không có trong danh mục", "INVALID_PROJECT": "mã dự án không có trong danh mục",
    "INVALID_EXPENSE": "mã khoản mục không có trong danh mục", "INVALID_COST_CENTER": "mã TTCP không có trong danh mục",
    "CASH_ACCOUNT_MAPPING_MISSING": "chưa khai TK kế toán cho tài khoản ngân hàng (màn hình Nguồn dữ liệu)",
    "CASH_ACCOUNT_MAPPING_CONFLICT": "tài khoản ngân hàng ứng với nhiều TK 112 — cần khai ở Nguồn dữ liệu",
    "CASH_ACCOUNT_CONFLICT": "TK tiền đề xuất khác TK đã cấu hình", "LINES_UNBALANCED": "tổng Nợ ≠ tổng Có",
    "LINES_CASH_AMOUNT": "dòng TK tiền phải đúng số tiền sao kê", "LINES_MISSING_ACCOUNT": "có dòng chưa chọn tài khoản",
    "LOCKED_PERIOD": "kỳ đã khóa sổ", "ZERO_AMOUNT": "số tiền bằng 0",
    "CASH_FIELD_NOT_112": "vế tiền phải là TK 112 chi tiết",
}


def _khong_phai_profile(run) -> None:
    """Run hồ sơ nghiệm thu (de_xuat/nghiem_thu.py) không đi qua luồng tiền/Thu-Chi/học STK của QuickPosting."""
    if run is not None and run["source_kind"] == "NGHIEM_THU":
        raise DataError("QUICK_PROFILE", "Lần này là hồ sơ nghiệm thu; xử lý ở mục Hồ sơ nghiệm thu, không qua định khoản tiền.")


def _vn_date(value: str) -> str:
    value = str(value or "")[:10]
    return f"{value[8:10]}/{value[5:7]}/{value[:4]}" if len(value) == 10 else value


def _entry_words(lines) -> str:
    """'Nợ 6427 + 1331 / Có 112111' from UI lines (side N/C)."""
    debit = [line["account"] or "?" for line in lines if line["side"] == "N"]
    credit = [line["account"] or "?" for line in lines if line["side"] == "C"]
    return "Nợ " + " + ".join(dict.fromkeys(debit)) + " / Có " + " + ".join(dict.fromkeys(credit))


def explain_errors(codes) -> str:
    words = []
    for code in codes:
        if code.startswith("MISSING_COUNTERPARTY_FOR_"):
            words.append("TK công nợ " + code.rsplit("_", 1)[-1] + " cần đối tượng")
        else:
            words.append(ERROR_WORDS.get(code, code))
    return "; ".join(dict.fromkeys(words))


class QuickPosting:
    def __init__(self, store):
        self.store, self.db = store, store.conn

    def _bundle(self, cutoff):
        # V13: nạp hàng loạt (4 câu SQL) — cùng kết quả với document() từng chứng từ, thứ tự rowid
        rows = documents_bulk(self.store, ("JOURNAL", "OPEN_ITEM", "LOCK_PERIOD"), cutoff)
        return {"manifest": {"as_of": "9999-12-31", "posting_evidence_complete": True}, "documents": rows}

    def _settings(self):
        defaults = {
            "description_similarity_threshold": 0.8, "export_mode": "DOI_UNG", "bank_ids": {},
            "template_thu": "", "template_chi": "", "learning_cutoff": "", "debt_accounts": list(DEFAULT_DEBT_ACCOUNTS),
            "scoring_mode": False, "local_ai": {}, "answer_ledger": "", "invoice_root": "",
        }
        row = self.db.execute("SELECT value FROM workspace_meta WHERE key='v9b_runtime_settings'").fetchone()
        if row:
            try:
                settings = json.loads(row[0])
                if isinstance(settings, dict):
                    defaults.update({key: value for key, value in settings.items() if key in defaults})
            except json.JSONDecodeError:
                pass
        return defaults

    @staticmethod
    def _evidence(payload):
        sources = sorted({identifier for item in payload.get("confidence", {}).values() for identifier in item.get("evidence", [])})
        missing = []
        for code in payload.get("constraints", []):
            if code.startswith(("MISSING_", "INVALID_", "OUTSIDE_", "INVOICE_ACCOUNT", "BASE_", "ALLOCATION_", "CASH_ACCOUNT_")):
                missing.append(code)
        return sources, missing

    def set_cash_mapping(self, account, cash_account, actor="CFO_NTD", source="MANUAL", evidence=()):
        """Persist an explicit or uniquely documentary mapping for S1."""
        account, cash_account = bank_account(account), str(cash_account or "").strip()
        if not account or not is_cash_detail(cash_account):
            raise DataError("CASH_ACCOUNT_MAPPING", "Ánh xạ TK tiền cần STK ngân hàng và TK 112 chi tiết.")
        if source not in {"MANUAL", "JOURNAL_UNIQUE"}:
            raise DataError("CASH_ACCOUNT_MAPPING", "Nguồn ánh xạ TK tiền không hợp lệ.")
        self.db.execute("""INSERT INTO cash_account_mappings(bank_account,cash_account,source,evidence_json,updated_at,actor)
                           VALUES (?,?,?,?,?,?)
                           ON CONFLICT(bank_account) DO UPDATE SET cash_account=excluded.cash_account,source=excluded.source,
                           evidence_json=excluded.evidence_json,updated_at=excluded.updated_at,actor=excluded.actor""",
                        (account, cash_account, source, canonical_json(list(evidence)), now_utc(), text_id(actor, "actor")))

    def _record_match(self, record, payload, actor, at):
        match = payload.get("journal_match") or {}
        if match.get("status") != "UNIQUE":
            return False
        self.db.execute("""INSERT INTO bank_journal_matches(bank_document_id,journal_document_id,similarity,state,excluded_from_export,matched_at,actor)
                           VALUES (?,?,?,?,?,?,?)
                           ON CONFLICT(bank_document_id) DO UPDATE SET journal_document_id=excluded.journal_document_id,
                           similarity=excluded.similarity,state=excluded.state,excluded_from_export=excluded.excluded_from_export,
                           matched_at=excluded.matched_at,actor=excluded.actor""",
                        (record["id"], match["journal_id"], float(match["similarity"]), "UNIQUE", 1, at, actor))
        return True

    def _machine_existing(self, record, actor, at):
        """Did the machine find this row in Junsky (last built payload, unmasked)?"""
        seen = getattr(self, "_last_seen", None) or {}
        return self._record_match(record, {"journal_match": seen.get("match") or {}}, actor, at) or bool(seen.get("posted_reference"))

    def _stage_pending_pattern(self, payload, record, at):
        learning = payload.get("learning")
        if not learning or learning.get("no_stage"):
            return
        condition = {"basis": learning.get("match_basis"), "source_ids": learning.get("source_ids", []),
                     "fields": learning.get("fields", {}), "lines": learning.get("pattern_lines", []),
                     "direction": payload.get("direction")}
        key = "JOURNAL_PATTERN:" + sha256(canonical_json(condition).encode())[:32]
        if self.db.execute("SELECT 1 FROM knowledge_versions WHERE category='RULE' AND logical_key=?", (key,)).fetchone():
            return
        item = {"category": "RULE", "logical_key": key, "valid_from": record["business_date"], "valid_to": None,
                "known_at": at, "payload": {"kind": "JOURNAL_PATTERN", "contract_version": 1, "state": "PENDING",
                                                 "fields": learning.get("fields", {}), "dimensions": learning.get("dimensions", {}),
                                                 "journal_lines": learning.get("pattern_lines", []), "strength": learning.get("strength"),
                                                 "sample_vouchers": learning.get("source_vouchers", []),
                                                 "why": learning.get("why", ""), "match_basis": learning.get("match_basis")},
                "evidence": learning.get("source_ids", [])}
        # `propose()` already owns one atomic Store transaction for the run
        # and its quick items.  Calling stage_many() here opens a second
        # SQLite transaction and fails precisely when S6 first finds a usable
        # pattern.  `_stage` is the transaction-free primitive behind
        # stage_many; using it keeps the proposal and its PENDING provenance
        # atomic without approving anything.
        Knowledge(self.store)._stage(item, "HE_THONG_JUNSKY", at)

    @staticmethod
    def _primary_keyword(value):
        words = re.findall(r"[A-Z0-9À-Ỵ]+", normalize_text(value))
        return next((word for word in words if len(word) >= 4 and not word.isdigit()), "")

    @staticmethod
    def _numeric_keys(record):
        """Long numbers in a narrative that identify a contract/loan (V11, F4).

        A loan account or contract number repeats month after month while the
        amount changes; once Anh approves a row, the number becomes the key.
        The bank's own account, the counterparty account, the amount itself,
        dates and anything shorter than 10 digits are ignored.
        """
        own = bank_account(record.get("account"))
        counter = bank_account(record.get("counterparty_account"))
        amount = str(abs(int(record.get("amount_minor", 0) or 0)))
        keys = []
        for value in re.findall(r"\d{10,}", str(record.get("description") or "")):
            if value in (own, counter, amount) or value in keys or value.startswith(("19", "20")) and len(value) in (12, 14):
                continue
            keys.append(value)
        return keys[:2]

    def _condition_for(self, record, cutoff):
        candidates = []
        account = bank_account(record.get("counterparty_account"))
        if account:
            candidates.append(("BANK_ACCOUNT", account))
        name = normalize_text(record.get("counterparty_name", ""))
        if name:
            candidates.append(("COUNTERPARTY_NAME", name))
        for key in self._numeric_keys(record):
            candidates.append(("KEYWORD", "SO:" + key))
        keyword = self._primary_keyword(record.get("description", ""))
        if keyword:
            candidates.append(("KEYWORD", keyword))
        for kind, value in candidates:
            row = self.db.execute("""SELECT fields_json,knowledge_id FROM quick_condition_learning
                                    WHERE condition_type=? AND condition_value=? AND active=1 AND valid_from<=? AND created_at<=?
                                    ORDER BY revision DESC LIMIT 1""", (kind, value, record["business_date"], instant_utc(cutoff))).fetchone()
            if row:
                return kind, value, json.loads(row["fields_json"]), row["knowledge_id"]
        return None

    def _apply_condition(self, payload, record, engine, cutoff):
        match = self._condition_for(record, cutoff)
        if not match:
            return
        kind, value, selected, knowledge_id = match
        cash_field = "debit_account" if record["amount_minor"] > 0 else "credit_account"
        own_codes = engine._own_codes()
        for field, field_value in selected.items():
            if field == "counterparty" and field_value in own_codes:
                continue
            if field in FIELDS and field_value and field != cash_field:
                payload["fields"][field] = field_value
                payload["confidence"][field] = {"level": "ANH_DA_DUYET", "evidence": [knowledge_id] if knowledge_id else []}
        # Anh's decision outranks a learned/template split: reuse its own
        # line structure when it had one, otherwise the plain two-line entry.
        cash = (payload.get("cash_leg") or {}).get("account") or ""
        pattern = selected.get("__lines__") if isinstance(selected.get("__lines__"), list) else []
        payload["lines"] = self._materialize_decision_pattern(pattern, record, cash) if pattern and cash else []
        payload.pop("options", None)
        payload["constraints"] = [entry for entry in payload.get("constraints", []) if not entry.startswith(("MISSING_", "INVALID_", "KEYWORD_CONFLICT_", "NO_UNIQUE_", "JOURNAL_PATTERN_MULTILINE_"))]
        required = payload.get("policy", {}).get("required_fields", ["debit_account", "credit_account"])
        payload["constraints"].extend(engine.validate_fields(payload["fields"], record["business_date"], cutoff, required))
        payload["completeness"] = "FULL" if not payload["constraints"] else "PARTIAL" if any(payload["fields"].values()) else "NONE"
        payload["why"] = "Dùng phương án Anh đã duyệt trước đó theo " + {"BANK_ACCOUNT": "STK đối ứng", "COUNTERPARTY_NAME": "tên đối ứng", "KEYWORD": "từ khóa chính"}[kind] + "."
        payload["condition"] = {"type": kind, "value": value, "knowledge_id": knowledge_id}

    @staticmethod
    def _materialize_decision_pattern(pattern, record, cash_account):
        """Scale Anh's earlier multi-line decision to a new bank amount (integers only)."""
        amount = abs(int(record["amount_minor"]))
        direction = "IN" if record["amount_minor"] > 0 else "OUT"
        other = "CREDIT" if direction == "IN" else "DEBIT"
        total = sum(int(item.get("amount_minor", 0) or 0) for item in pattern)
        if total <= 0 or amount <= 0:
            return []
        result, allocated = [], 0
        for index, item in enumerate(pattern, 1):
            share = amount - allocated if index == len(pattern) else amount * int(item.get("amount_minor", 0) or 0) // total
            allocated += share
            if not share:
                continue
            dims = {key: item.get(key) for key in ("project", "expense", "cost_center", "counterparty") if item.get(key)}
            result.append({"line_id": f"ANH-{index:03d}", "account": item.get("account") or "", "currency": record.get("currency", "VND"),
                           "debit_minor": share if other == "DEBIT" else 0, "credit_minor": share if other == "CREDIT" else 0,
                           "tax_basis": "ANH_DA_DUYET", "state": "READY", "dimensions": dims})
        result.append({"line_id": "ANH-CASH", "account": cash_account, "currency": record.get("currency", "VND"),
                       "debit_minor": amount if direction == "IN" else 0, "credit_minor": amount if direction == "OUT" else 0,
                       "tax_basis": "BANK_AMOUNT", "state": "READY", "dimensions": {}})
        return result

    # ------------------------------------------------------------------
    # Proposal construction (shared by propose and repropose)
    # ------------------------------------------------------------------
    def _context(self, records, cutoff, actor, kind):
        engine, bundle = Engine(self.store, include_pending=True), self._bundle(cutoff)
        hints = {}
        if kind == "BANK":
            settings = self._settings()
            journals = [row for row in bundle["documents"] if row["kind"] == "JOURNAL"]
            inferred = infer_cash_mappings(records, journals, float(settings["description_similarity_threshold"]))
            for source_account, mapping in inferred.items():
                manual = self.db.execute("SELECT source FROM cash_account_mappings WHERE bank_account=?", (source_account,)).fetchone()
                if mapping.get("cash_account") and (not manual or manual["source"] != "MANUAL"):
                    self.set_cash_mapping(source_account, mapping["cash_account"], actor, "JOURNAL_UNIQUE", mapping.get("evidence_ids", [entry["journal_id"] for entry in mapping["matches"]]))
            # A MANUAL mapping is Anh's explicit configuration and wins over
            # an inferred conflict (several historical 112 accounts).
            overrides = {}
            for key, value in inferred.items():
                manual = self.db.execute("SELECT cash_account FROM cash_account_mappings WHERE bank_account=? AND source='MANUAL'", (key,)).fetchone()
                overrides[key] = {"cash_account": manual["cash_account"], "source": "MANUAL"} if manual else {**value, "source": "JOURNAL_UNIQUE"}
            engine.cash_overrides = overrides
            first_day = min((record["business_date"] for record in records), default=cutoff[:10])
            limit = engine._learning_cutoff()
            if limit:
                first_day = min(first_day, (date.fromisoformat(limit) + timedelta(days=1)).isoformat())
            # V11: hints are ranked per row against its own description (F3).
            hints = {"journals": journals, "first_day": first_day}
            posted = [row for row in journals if row.get("source_status") in self.store.config.posted_journal_statuses]
            engine.group_matches = match_bank_groups_to_journal(records, posted, float(settings["description_similarity_threshold"]))
            groups: dict[tuple, list] = {}
            for record in records:
                key_value = bank_account(record.get("counterparty_account")) or normalize_text(str(record.get("counterparty_name") or ""))
                if key_value:
                    groups.setdefault((record["business_date"], record["amount_minor"] > 0, key_value), []).append(record)
            engine.group_totals = {member["id"]: sum(abs(int(item["amount_minor"])) for item in members) for members in groups.values() if len(members) >= 2 for member in members}
            engine.fill_from_match = not bool(settings.get("scoring_mode"))
            engine.hide_answer = bool(settings.get("scoring_mode"))
            engine.open_item_single = True
        elif kind == "INVOICE":
            self._invoice_context(engine, bundle, records, cutoff)
        return engine, bundle, hints

    def _invoice_context(self, engine, bundle, records, cutoff):
        """V12: earlier invoices of the last 12 months linked to their vouchers."""
        settings = self._settings()
        engine.fill_from_match = not bool(settings.get("scoring_mode"))
        engine.hide_answer = bool(settings.get("scoring_mode"))
        posted = [row for row in bundle["documents"] if row["kind"] == "JOURNAL" and row.get("source_status") in self.store.config.posted_journal_statuses]
        limit = engine._learning_cutoff()
        first_record = min((record["business_date"] for record in records), default=cutoff[:10])
        invoice_last = limit or (date.fromisoformat(first_record) - timedelta(days=1)).isoformat()
        journal_last = limit or cutoff[:10]
        first = month_bounds(invoice_last, 12)
        known = [row for row in posted if str(row.get("business_date") or "") <= journal_last]
        invoices = self._history_invoices(Path(str(settings.get("invoice_root") or "")), first, invoice_last)
        taxes = self._tax_codes(first_record, cutoff)
        engine.invoice_history = build_invoice_history(invoices, known, party_of=lambda tax: taxes.get(tax, ""),
                                                       first_day=first, last_day=invoice_last, journal_last_day=journal_last)
        projects: dict[str, dict[str, int]] = {}
        for row in known:
            party, project = str(row.get("counterparty") or ""), str(row.get("project") or "")
            if party and project and str(row.get("business_date") or "") >= first:
                bucket = projects.setdefault(party, {})
                bucket[project] = bucket.get(project, 0) + 1
        engine.party_projects = projects
        engine.invoice_answer = InvoiceJournalIndex(posted)

    def _tax_codes(self, day, cutoff):
        codes: dict[str, set] = {}
        for row in Knowledge(self.store).query(day, cutoff, "CATALOG", include_pending=True):
            value = row["payload"]
            if value.get("kind") == "IDENTIFIER" and value.get("identifier_type") == "TAX_ID" and value.get("counterparty"):
                codes.setdefault(str(value.get("value") or "").strip(), set()).add(value["counterparty"])
        return {tax: next(iter(found)) for tax, found in codes.items() if len(found) == 1}

    _HISTORY_CACHE: dict = {}

    def _history_invoices(self, root: Path, first: str, last: str) -> list[dict]:
        files = history_files(root, first, last) if str(root) not in ("", ".") else []
        key = (str(root), first, last, len(files), max((path.stat().st_mtime for path in files), default=0))
        cached = QuickPosting._HISTORY_CACHE.get(key)
        if cached is not None:
            return cached
        result = []
        for path in files:
            try:
                row, _issues = parse_invoice_xml(path.read_bytes(), self.store.config.entity_tax_id, self.store.config.invoice_non_taxable_in_taxable_total)
            except OSError:
                continue
            if row and "__quarantine_issue" not in row:
                result.append(row)
        if len(QuickPosting._HISTORY_CACHE) > 8:
            QuickPosting._HISTORY_CACHE.clear()
        QuickPosting._HISTORY_CACHE[key] = result
        return result

    def _build_payload(self, record, engine, bundle, cutoff, source_kind, hints):
        payload = engine.preview(record, bundle, cutoff)
        # What the machine saw before any masking: used only to keep a row that
        # is already in Junsky out of the export, never shown in scoring mode.
        self._last_seen = {"match": dict(payload.get("journal_match") or {}),
                           "posted_reference": "ALREADY_POSTED_OR_DUPLICATE_REFERENCE" in (payload.get("constraints") or [])}
        if record.get("kind") in ("BANK", "INVOICE") and not engine.fill_from_match:
            # Scoring replay (or a row Anh cleared as "không trùng"): the matched
            # voucher is the hidden answer and must not surface anywhere on screen.
            payload["journal_match"] = {"status": "UNMATCHED", "candidate_count": 0}
            payload["potential_existing"] = False
            if getattr(engine, "hide_answer", False):
                payload["constraints"] = [item for item in payload.get("constraints") or [] if item != "ALREADY_POSTED_OR_DUPLICATE_REFERENCE"]
                if payload.get("warnings"):
                    payload["warnings"] = [item for item in payload["warnings"] if item != "JOURNAL_MATCH_AMBIGUOUS"]
        if record.get("kind") == "BANK" and not payload.get("cash_leg"):
            # The engine stops early when no rule fits; the bank leg is still
            # known from the account mapping, so show it (Anh then only picks
            # the offset account).  A missing mapping stays a visible gap.
            probe = []
            engine._apply_cash_leg(record, payload["fields"], payload["confidence"], probe, payload)
            payload.setdefault("constraints", [])
            payload["constraints"].extend(code for code in probe if code not in payload["constraints"])
        self._apply_condition(payload, record, engine, cutoff)
        sources, missing = self._evidence(payload)
        payload["knowledge_ids"], payload["missing"] = sources, missing
        payload.setdefault("why", "Đủ căn cứ từ tri thức/danh mục." if not missing else "Cần bổ sung: " + ", ".join(missing[:3]))
        payload["source_kind"] = source_kind
        payload["source_reference"] = record.get("reference", "")
        payload["source_description"] = record.get("description", "")
        payload["source_counterparty_name"] = record.get("counterparty_name", "")
        payload["source_bank_account"] = record.get("account", "")
        if record.get("kind") == "INVOICE":
            # V12: what Anh reads on an invoice row: items, the other party, the invoice number.
            payload["source_description"] = invoice_text(record) or "(hóa đơn không có tên hàng)"
            payload["source_counterparty_name"] = record.get("seller_name" if record.get("direction") == "MUA_VAO" else "buyer_name") or ""
            payload["source_reference"] = "HĐ " + str(record.get("series") or "") + "-" + str(record.get("number") or "")
            payload["invoice_direction"] = record.get("direction") or ""
            payload["invoice_amounts"] = {"net": record.get("net_minor"), "tax": record.get("tax_minor"), "total": record.get("total_minor")}
            try:
                self._enrich(payload, record, cutoff)
            except (DataError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                payload.setdefault("basis", [])
        if record.get("kind") == "BANK":
            direction = "IN" if record["amount_minor"] > 0 else "OUT"
            if hints.get("journals") is not None:
                payload["suggest_accounts"] = offset_account_ranking(hints["journals"], direction, hints["first_day"], description=record.get("description", ""),
                                                                     ignore_words=engine.own_words())
            else:
                payload["suggest_accounts"] = list(hints.get(direction, []))
            try:
                self._enrich(payload, record, cutoff)
            except (DataError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                # Explanations are an aid; a malformed historical sample must
                # never block the proposal itself.
                payload.setdefault("basis", [])
        return payload

    def propose(self, attempt_id, source_kind, actor, cutoff=None, *, source_name=None, source_hash=None, source_info=None, progress=None, contract_facts=None):
        cutoff = instant_utc(cutoff or now_utc()); actor = text_id(actor, "actor")
        kinds = {"sao_ke": "BANK", "hoa_don": "INVOICE", "bang_ke": "INVOICE", "base": "BASE"}
        kind = kinds.get(source_kind)
        if not kind:
            raise DataError("QUICK_SOURCE", "Tệp này chưa phải sao kê, hóa đơn, bảng kê hoặc Base.")
        with transaction(self.store):
            existing = self.db.execute("SELECT id FROM quick_runs WHERE source_attempt_id=? AND source_kind=?", (attempt_id, source_kind)).fetchone()
            if existing:
                return self.rows(existing[0])
            run_id = uid()
            self.db.execute("INSERT INTO quick_runs(id,source_attempt_id,source_kind,created_at,actor,source_name,source_hash,source_info_json) VALUES (?,?,?,?,?,?,?,?)",
                            (run_id, attempt_id, source_kind, cutoff, actor, source_name, source_hash, canonical_json(source_info) if source_info else None))
            records = [document(self.store, row[0], cutoff) for row in self.db.execute("SELECT id FROM documents WHERE first_attempt_id=? AND kind=? ORDER BY business_date,id", (attempt_id, kind))]
            engine, bundle, hints = self._context(records, cutoff, actor, kind)
            engine.contract_facts = dict(contract_facts or {})  # CRM-01: fact HĐ hiệu lực (K2) cho nhánh TL32 §3.2; mặc định rỗng = như cũ
            scoring = bool(self._settings().get("scoring_mode"))
            for index, record in enumerate(records, 1):
                payload = self._build_payload(record, engine, bundle, cutoff, source_kind, hints)
                is_existing = self._machine_existing(record, actor, cutoff)
                # Scoring replay: vouchers after the learning cutoff are the hidden
                # answer.  The row waits like any other (not shown as "đã có"), but
                # it stays out of every export file.
                state = "EXISTING" if is_existing and not scoring else "WAIT"
                self.db.execute("INSERT INTO quick_items(id,run_id,document_id,proposal_json,state,excluded_from_export) VALUES (?,?,?,?,?,?)",
                                (uid(), run_id, record["id"], canonical_json(payload), state, int(is_existing)))
                self._stage_pending_pattern(payload, record, cutoff)
                if progress:
                    progress(index, len(records))
            log(self.store, "V9B", "QUICK_PROPOSE", run_id, actor, cutoff, {"source": source_kind, "count": len(records), "pending_knowledge": True})
        return self.rows(run_id)

    def repropose(self, run_id, actor, cutoff=None, *, document_ids=None, progress=None):
        """Recompute rows still waiting (after new learning, mapping or cutoff).

        Decided rows (APPROVE/SKIP/EXPORTED) are never touched.  Rows marked as
        already in Junsky are kept, except in scoring mode: there every
        undecided row is recomputed (the mark would reveal the answer); the row
        stays out of export so it cannot be posted twice.
        """
        run_id, actor = text_id(run_id, "run_id"), text_id(actor, "actor")
        cutoff = instant_utc(cutoff or now_utc())
        run = self.db.execute("SELECT * FROM quick_runs WHERE id=?", (run_id,)).fetchone()
        if not run:
            raise DataError("QUICK_RUN", "Không thấy lần đề xuất này.")
        _khong_phai_profile(run)
        kind = {"sao_ke": "BANK", "hoa_don": "INVOICE", "bang_ke": "INVOICE", "base": "BASE"}[run["source_kind"]]
        scoring = bool(self._settings().get("scoring_mode"))
        states = ("WAIT", "EXISTING") if scoring else ("WAIT",)
        items = [dict(row) for row in self.db.execute(f"SELECT id,document_id FROM quick_items WHERE run_id=? AND state IN ({','.join('?' * len(states))}) ORDER BY id",
                                                      (run_id, *states))]
        if document_ids is not None:
            wanted = set(document_ids)
            items = [item for item in items if item["document_id"] in wanted]
        if not items:
            return self.rows(run_id)
        with transaction(self.store):
            records = [document(self.store, item["document_id"], cutoff) for item in items]
            engine, bundle, hints = self._context(records, cutoff, actor, kind)
            for index, (item, record) in enumerate(zip(items, records), 1):
                cleared = self.db.execute("SELECT 1 FROM bank_journal_matches WHERE bank_document_id=? AND excluded_from_export=0", (record["id"],)).fetchone()
                if cleared:
                    # Anh said "không trùng": do not copy that voucher's posting either.
                    engine.fill_from_match = False
                payload = self._build_payload(record, engine, bundle, cutoff, run["source_kind"], hints)
                engine.fill_from_match = not scoring
                # Anh's "Không trùng" decision is kept; a re-proposal never re-marks it.
                is_existing = False if cleared else self._machine_existing(record, actor, cutoff)
                if scoring:
                    self.db.execute("UPDATE quick_items SET proposal_json=?,state='WAIT',excluded_from_export=MAX(excluded_from_export,?) WHERE id=? AND state IN ('WAIT','EXISTING')",
                                    (canonical_json(payload), int(is_existing), item["id"]))
                else:
                    self.db.execute("UPDATE quick_items SET proposal_json=?,state=?,excluded_from_export=? WHERE id=? AND state='WAIT'",
                                    (canonical_json(payload), "EXISTING" if is_existing else "WAIT", int(is_existing), item["id"]))
                self._stage_pending_pattern(payload, record, cutoff)
                if progress:
                    progress(index, len(items))
            log(self.store, "V10", "QUICK_REPROPOSE", run_id, actor, cutoff, {"count": len(items), "scoring_mode": scoring})
        return self.rows(run_id)

    def similar_waiting(self, run_id, document_id, cutoff=None):
        """Waiting rows of the run that share the decided row's condition key."""
        cutoff = instant_utc(cutoff or now_utc())
        base = document(self.store, document_id, cutoff)
        account, name = bank_account(base.get("counterparty_account")), normalize_text(base.get("counterparty_name", ""))
        if not account and not name:
            return []
        result = []
        for row in self.db.execute("SELECT document_id FROM quick_items WHERE run_id=? AND state='WAIT' AND document_id<>?", (run_id, document_id)):
            other = document(self.store, row[0], cutoff)
            if (account and bank_account(other.get("counterparty_account")) == account) or (not account and name and normalize_text(other.get("counterparty_name", "")) == name):
                result.append(row[0])
        return result

    # ------------------------------------------------------------------
    # Explanation for the screen: why, basis (old vouchers), options
    # ------------------------------------------------------------------
    def _knowledge_payload(self, identifier):
        row = self.db.execute("SELECT payload_json FROM knowledge_versions WHERE id=?", (identifier,)).fetchone()
        return json.loads(row[0]) if row else {}

    @staticmethod
    def _journal_entry_words(journal):
        lines = []
        for line in journal.get("lines", []):
            debit, credit = int(line.get("debit_minor", 0) or 0), int(line.get("credit_minor", 0) or 0)
            if debit:
                lines.append({"side": "N", "account": str(line.get("account") or "")})
            if credit:
                lines.append({"side": "C", "account": str(line.get("account") or "")})
        return _entry_words(lines) if lines else ""

    def _cfo_notes(self):
        row = self.db.execute("SELECT value FROM workspace_meta WHERE key='cfo_notes'").fetchone()
        try:
            notes = json.loads(row[0]) if row else []
        except (TypeError, json.JSONDecodeError):
            return []
        return [note for note in notes if isinstance(note, dict) and note.get("lich_su_tk") and note.get("de_xuat_tk") and note.get("ma")]

    def _enrich(self, payload, record, cutoff):
        fields, confidence = payload.get("fields", {}), payload.get("confidence", {})
        learning = payload.get("learning") or {}
        groups: dict[str, list[str]] = {}
        basis = []
        seen_basis = set()

        def add_basis(item):
            key = (item.get("no"), item.get("d"), item.get("desc"))
            if key not in seen_basis and len(basis) < 10:
                seen_basis.add(key); basis.append(item)

        offset = "credit_account" if int(payload.get("amount_minor", 0) or 0) > 0 else "debit_account"
        pattern_owns_offset = str((confidence.get(offset) or {}).get("level", "")).startswith("PENDING_PATTERN")
        pattern_conflict = False
        for field in FIELDS:
            value, info = fields.get(field), confidence.get(field) or {}
            level = info.get("level", "UNKNOWN")
            if not value or level == "UNKNOWN":
                continue
            phrase = LEVEL_WORDS.get(level)
            if level.startswith("PENDING_PATTERN") and not pattern_owns_offset and field not in ("debit_account", "credit_account") and learning.get("stats"):
                # V11.4: the offset account came from stronger evidence (open
                # item, rule); the old vouchers only lend this dimension, and
                # their own account is reported as a caution below.
                stats = learning["stats"]
                span = stats["from"] if stats["from"] == stats["to"] else f"{stats['from']}–{stats['to']}"
                phrase = f"theo {stats['window']} chứng từ trước tương tự ({span}) (mẫu học từ sổ, chờ duyệt)"
                learned_offset = (learning.get("fields") or {}).get(offset)
                pattern_conflict = bool(learned_offset and learned_offset != fields.get(offset))
            elif level.startswith("PENDING_PATTERN"):
                phrase = (learning.get("why") or "theo chứng từ cũ có diễn giải tương tự").rstrip(".") + " (mẫu học từ sổ, chờ duyệt)"
            elif level.startswith("PENDING_RULE") or level in {"APPROVED_TEMPLATE", "APPROVED_KEYWORD"}:
                rule = self._knowledge_payload((info.get("evidence") or [""])[0])
                source = rule.get("source_row") or {}
                if source:
                    seen, right = source.get("so_lan_gap"), source.get("so_lan_dung")
                    code = source.get("ma_quy_tac") or "quy tắc"
                    pending = "" if level.startswith("APPROVED") else "chờ duyệt"
                    detail = "; ".join(value for value in ((f"gặp {seen} lần, đúng {right}" if seen not in (None, "") else ""), pending) if value)
                    phrase = f"theo quy tắc {code}" + (f" ({detail})" if detail else "")
                    if source.get("vi_du_dien_giai"):
                        accounts = [{"side": "N", "account": fields.get("debit_account") or "?"}, {"side": "C", "account": fields.get("credit_account") or "?"}]
                        add_basis({"d": _vn_date(source.get("lan_cuoi")), "no": "Quy tắc " + str(code), "desc": str(source.get("vi_du_dien_giai")),
                                   "hk": _entry_words(accounts), "note": f"gặp {seen} lần, đúng {right}" if seen not in (None, "") else ""})
                else:
                    phrase = phrase or "theo bộ quy tắc học từ sổ (chờ duyệt)"
            elif level == "ANH_DA_DUYET":
                condition = payload.get("condition") or {}
                origin = self.db.execute("SELECT evidence_json,created_at FROM quick_condition_learning WHERE knowledge_id=?", ((info.get("evidence") or [""])[0],)).fetchone()
                if origin:
                    for doc_id in json.loads(origin["evidence_json"])[:1]:
                        try:
                            prior = document(self.store, doc_id)
                            add_basis({"d": _vn_date(prior.get("business_date")), "no": "Anh đã duyệt", "desc": prior.get("description", ""),
                                       "hk": "", "note": "duyệt lúc " + _vn_date(origin["created_at"])})
                        except DataError:
                            pass
                phrase = {"BANK_ACCOUNT": "theo lần Anh đã duyệt trước (cùng STK đối ứng)", "COUNTERPARTY_NAME": "theo lần Anh đã duyệt trước (cùng tên đối ứng)",
                          "KEYWORD": "theo lần Anh đã duyệt trước (cùng từ khóa)"}.get(condition.get("type"), phrase)
            if field == "project" and payload.get("project_why"):
                phrase = str(payload["project_why"]) + (" (mẫu học từ sổ, chờ duyệt)" if level.startswith("PENDING_PATTERN") else "")
            phrase = phrase or level
            label = (FIELD_WORDS[field] + " " + str(value)) if field != "counterparty" else "đối tượng " + str(value)
            groups.setdefault(phrase, []).append(label)
        parts = [", ".join(labels)[:1].upper() + ", ".join(labels)[1:] + ": " + phrase for phrase, labels in groups.items()]
        learned_offset = (learning.get("fields") or {}).get(offset)
        if not pattern_owns_offset and learned_offset and fields.get(offset) and learned_offset != fields.get(offset) and learning.get("why"):
            pattern_conflict = True
        if pattern_conflict and learning.get("why"):
            note = "Lưu ý: " + learning["why"].rstrip(".") + " — khác TK đang đề xuất"
            for cfo in self._cfo_notes():
                # Tri thức CFO (TRI-THUC-CFO.json, loại LƯU Ý), e.g. 344 → 131.
                if str(learned_offset or "").startswith(cfo["lich_su_tk"]) and str(fields.get(offset) or "").startswith(cfo["de_xuat_tk"]):
                    note += f" ({cfo['noi_dung']} — {cfo['ma']})"
            parts.append(note)
        if parts:
            payload["why"] = ". ".join(parts) + "."
        extras = []
        conflict = payload.get("identifier_conflict") or {}
        if conflict.get("code"):
            extras.append(f"Danh bạ STK đang gắn mã {conflict['code']} nhưng tên trên sao kê không khớp — đã bỏ qua, cần Anh xác nhận")
        demoted = payload.get("demoted_rule") or {}
        if demoted.get("code"):
            seen = f", gặp {demoted.get('seen')} đúng {demoted.get('right')}" if demoted.get("seen") not in (None, "") else ""
            extras.append(f"Quy tắc từ khóa {demoted['code']} (“{demoted.get('keyword')}” → {demoted.get('account')}{seen}) chỉ làm gợi ý vì chứng từ cũ có căn cứ mạnh hơn")
        if payload.get("ai_reason"):
            extras.append("AI cục bộ: " + str(payload["ai_reason"]))
        extras.extend(str(note).rstrip(".") for note in payload.get("invoice_notes") or [])
        if extras:
            payload["why"] = (payload.get("why") or "").rstrip(".") + (". " if payload.get("why") else "") + ". ".join(extras) + "."
        for identifier in learning.get("source_ids", [])[:8]:
            try:
                journal = document(self.store, identifier, cutoff)
            except DataError:
                continue
            add_basis({"d": _vn_date(journal.get("business_date")), "no": journal.get("voucher_number") or "", "desc": journal.get("description") or "",
                       "hk": self._journal_entry_words(journal), "note": ""})
        match = payload.get("journal_match") or {}
        if match.get("status") == "UNIQUE":
            try:
                journal = document(self.store, match["journal_id"], cutoff)
                basis.insert(0, {"d": _vn_date(journal.get("business_date")), "no": journal.get("voucher_number") or "", "desc": journal.get("description") or "",
                                 "hk": self._journal_entry_words(journal), "note": "chứng từ có thể trùng trong Junsky"})
            except DataError:
                pass
        payload["basis"] = basis
        # Options: several historical structures disagree -> let Anh choose.
        signatures = learning.get("signatures") or []
        if len(signatures) >= 2:
            cash = (payload.get("cash_leg") or {}).get("account") or ""
            total = sum(item["count"] for item in signatures)
            options = []
            for item in signatures:
                pattern = [{"account": line["account"], "amount_minor": line["amount_minor"], "project": fields.get("project"), "expense": fields.get("expense"),
                            "cost_center": (learning.get("dimensions") or {}).get("cost_center"), "counterparty": fields.get("counterparty")} for line in item["lines"]]
                lines = self._materialize_decision_pattern(pattern, record, cash)
                if not lines:
                    continue
                vouchers = [value for value in item.get("source_vouchers", []) if value][:4]
                options.append({"label": f"Theo {item['count']}/{total} chứng từ cũ", "note": ("Số CT: " + ", ".join(vouchers)) if vouchers else "",
                                "lines": self._ui_lines(lines, fields, cash), "count": item["count"]})
            if len(options) >= 2:
                payload["options"] = options

    @staticmethod
    def _ui_lines(lines, fields, cash_account):
        result = []
        for line in lines or []:
            debit, credit = int(line.get("debit_minor", 0) or 0), int(line.get("credit_minor", 0) or 0)
            account = str(line.get("account") or "")
            dims = line.get("dimensions") if isinstance(line.get("dimensions"), dict) else {}
            is_cash = bool(account) and (account == cash_account or account.startswith("112"))
            result.append({"side": "N" if debit else "C", "account": account, "amount": debit or credit,
                           "counterparty": str(dims.get("counterparty") or fields.get("counterparty") or ""),
                           "project": "" if is_cash else str(dims.get("project") or ""),
                           "expense": "" if is_cash else str(dims.get("expense") or ""),
                           "cost_center": "" if is_cash else str(dims.get("cost_center") or "")})
        return result

    @staticmethod
    def _engine_lines(ui_lines):
        return [{"account": line["account"], "debit_minor": line["amount"] if line["side"] == "N" else 0,
                 "credit_minor": line["amount"] if line["side"] == "C" else 0,
                 "dimensions": {key: line.get(key) for key in ("project", "expense", "cost_center", "counterparty") if line.get(key)}}
                for line in ui_lines]

    @staticmethod
    def _proposal_level(payload):
        if payload.get("missing") or payload.get("completeness") != "FULL":
            return "Đỏ"
        evidenced = [item.get("level", "UNKNOWN") for item in payload.get("confidence", {}).values() if item.get("evidence")]
        if not evidenced:
            return "Vàng"
        return "Xanh" if all(level in STRONG_LEVELS for level in evidenced) else "Vàng"

    @classmethod
    def _row_level(cls, row, payload):
        # V9b contract: a decided row counts as Green.  The V10 screen uses
        # ``proposal_level`` instead so a row keeps its level after approval.
        if row["decision_json"]:
            return "Xanh"
        return cls._proposal_level(payload)

    def _debt_prefixes(self):
        values = self._settings().get("debt_accounts")
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            return list(DEFAULT_DEBT_ACCOUNTS)
        return [value.strip() for value in values if value.strip()]

    def rows(self, run_id):
        run_id = text_id(run_id, "run_id")
        run = self.db.execute("SELECT * FROM quick_runs WHERE id=?", (run_id,)).fetchone()
        _khong_phai_profile(run)
        rows = []
        debt_prefixes = self._debt_prefixes()
        hide_answer = bool(self._settings().get("scoring_mode"))
        for row in self.db.execute("SELECT * FROM quick_items WHERE run_id=? ORDER BY id", (run_id,)):
            payload = json.loads(row["proposal_json"])
            fields = json.loads(row["decision_json"]) if row["decision_json"] else payload["fields"]
            learned_center = payload.get("learning", {}).get("dimensions", {}).get("cost_center")
            line_centers = {line.get("dimensions", {}).get("cost_center") for line in payload.get("lines", []) if isinstance(line.get("dimensions"), dict) and line.get("dimensions", {}).get("cost_center")}
            cost_center = row["decision_cost_center"] if "decision_cost_center" in row.keys() and row["decision_cost_center"] is not None else learned_center
            if not cost_center and len(line_centers) == 1:
                cost_center = next(iter(line_centers))
            why = payload.get("why", "Chờ căn cứ.")
            if row["excluded_from_export"]:
                match = payload.get("journal_match", {})
                if match.get("status") == "UNIQUE":
                    group = match.get("group") or {}
                    note = (f" ({group['size']} lần chuyển cùng ngày = 1 chứng từ, tổng {group['total_minor']:,} VND)".replace(",", ".") if group else "")
                    if not why.startswith("Đã có trong Junsky"):
                        why = "Có thể đã có trong Junsky – số CT " + str(match.get("voucher_number") or "") + note + ". " + why
                    elif note:
                        why = why.rstrip(".") + note + "."
            direction = "IN" if payload["amount_minor"] > 0 else "OUT"
            cash_account = fields.get("debit_account" if direction == "IN" else "credit_account") or ""
            decision_lines = json.loads(row["decision_lines_json"]) if "decision_lines_json" in row.keys() and row["decision_lines_json"] else None
            invoice = self._is_invoice(payload)
            if invoice:
                cash_account = ""
            if decision_lines:
                entry_lines = decision_lines
            elif invoice:
                entry_lines = self._ui_lines(self._invoice_effective_lines(payload, fields, cost_center), fields, "")
            else:
                effective = self._effective_lines({"lines": payload.get("lines", []), "cost_center": cost_center}, fields, cash_account or None,
                                                  "THU" if direction == "IN" else "CHI", abs(payload["amount_minor"]))
                entry_lines = self._ui_lines(effective, fields, cash_account)
            match = payload.get("journal_match") or {}
            proposal_level = self._proposal_level(payload)
            if proposal_level == "Xanh" and any(re.fullmatch(r"\d+", line["account"] or "") and any(line["account"].startswith(prefix) for prefix in debt_prefixes) and not line["counterparty"] for line in entry_lines):
                # A debt account without its counterparty is not "đủ căn cứ".
                proposal_level = "Vàng"
            if proposal_level == "Đỏ" and payload.get("options") and not any(code.startswith("CASH_ACCOUNT_") for code in payload.get("constraints", [])):
                # Old vouchers disagree but do offer concrete options: "Cần xem".
                proposal_level = "Vàng"
            rows.append({"id": row["id"], "document_id": row["document_id"], "state": row["state"], "business_date": payload["business_date"],
                         "amount_minor": payload["amount_minor"], "fields": fields, "lines": payload.get("lines", []),
                         "level": self._row_level(row, payload), "proposal_level": proposal_level, "why": why, "missing": payload.get("missing", []),
                         "source_kind": payload.get("source_kind", ""), "source_reference": payload.get("source_reference", ""),
                         "source_description": payload.get("source_description", ""), "potential_existing": bool(row["excluded_from_export"]) and not hide_answer,
                         "invoice_direction": payload.get("invoice_direction", ""),
                         "journal_match": payload.get("journal_match"), "cash_leg": payload.get("cash_leg"), "cost_center": cost_center,
                         "direction": direction, "cash_account": cash_account, "entry_lines": entry_lines, "decision_lines": decision_lines,
                         "basis": payload.get("basis", []), "options": payload.get("options"), "suggest_accounts": payload.get("suggest_accounts", []),
                         "levels": {name: (info or {}).get("level", "UNKNOWN") for name, info in (payload.get("confidence") or {}).items()},
                         "name_options": payload.get("name_options") or [], "account_options": payload.get("account_options") or [],
                         "identifier_conflict": payload.get("identifier_conflict"), "group": (payload.get("journal_match") or {}).get("group"),
                         "stats": (payload.get("learning") or {}).get("stats"), "demoted_rule": payload.get("demoted_rule"),
                         "ai_note": row["ai_note"] if "ai_note" in row.keys() else None,
                         "source_counterparty_name": payload.get("source_counterparty_name", ""), "reason": row["reason"] or "",
                         "decided_at": row["decided_at"], "actor": row["actor"], "junsky_voucher": match.get("voucher_number") if match.get("status") == "UNIQUE" else "",
                         "constraints": payload.get("constraints", [])})
        counts = Counter(row["level"] for row in rows)
        totals = {level: sum(abs(row["amount_minor"]) for row in rows if row["level"] == level) for level in ("Xanh", "Vàng", "Đỏ")}
        info = {}
        if run is not None:
            info = {"id": run["id"], "source_kind": run["source_kind"], "created_at": run["created_at"],
                    "source_name": run["source_name"] if "source_name" in run.keys() else None,
                    "source_info": json.loads(run["source_info_json"]) if "source_info_json" in run.keys() and run["source_info_json"] else {}}
        return {"run_id": run_id, "rows": rows, "counts": dict(counts), "totals": totals, "approved": sum(row["state"] == "APPROVE" for row in rows),
                "exported": sum(row["state"] == "EXPORTED" for row in rows), "run": info, "debt_accounts": debt_prefixes}

    def _create_condition_learning(self, record, fields, at, lines=None, condition=None):
        account = bank_account(record.get("counterparty_account"))
        name = normalize_text(record.get("counterparty_name", ""))
        keyword = self._primary_keyword(record.get("description", ""))
        kind, value = condition or (("BANK_ACCOUNT", account) if account else ("COUNTERPARTY_NAME", name) if name else ("KEYWORD", keyword))
        if not value:
            return
        own_codes = Engine(self.store)._own_codes()
        selected = {field: fields.get(field) for field in FIELDS if fields.get(field) and not (field == "counterparty" and fields.get(field) in own_codes)}
        if not selected:
            return
        pattern = self._decision_pattern(record, fields, lines or [], own_codes)
        if pattern:
            selected["__lines__"] = pattern
        old = self.db.execute("SELECT * FROM quick_condition_learning WHERE condition_type=? AND condition_value=? AND active=1", (kind, value)).fetchall()
        for item in old:
            self.db.execute("UPDATE quick_condition_learning SET active=0 WHERE id=?", (item["id"],))
            if item["knowledge_id"]:
                try:
                    Knowledge(self.store).revoke(item["knowledge_id"], "CFO_NTD", at, "Được thay bởi phương án Anh mới duyệt.", allow_pending=True)
                except DataError:
                    pass
        revision = self.db.execute("SELECT COALESCE(MAX(revision),0)+1 FROM quick_condition_learning WHERE condition_type=? AND condition_value=?", (kind, value)).fetchone()[0]
        logical_key = "QUICK_DECISION:" + kind + ":" + value
        prior = self.db.execute("SELECT knowledge_id FROM quick_condition_learning WHERE condition_type=? AND condition_value=? ORDER BY revision DESC LIMIT 1", (kind, value)).fetchone()
        item = {"category": "RULE", "logical_key": logical_key, "valid_from": record["business_date"], "valid_to": None, "known_at": at,
                "payload": {"kind": "QUICK_DECISION_PATTERN", "contract_version": 1, "condition_type": kind, "condition_value": value, "fields": selected},
                "evidence": ["QUICK_DECISION"], "supersedes_id": prior[0] if prior and prior[0] else None}
        identifier = Knowledge(self.store).stage_many([item], "CFO_NTD", at)[0]
        Knowledge(self.store).approve(identifier, "CFO_NTD", at)
        self.db.execute("INSERT INTO quick_condition_learning VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (uid(), kind, value, revision, canonical_json(selected), identifier, 1, record["business_date"], at, "CFO_NTD", canonical_json([record["id"]])))

    @staticmethod
    def _decision_pattern(record, fields, lines, own_codes):
        """Reusable split of an approved entry (only when it has several offset lines or own dimensions)."""
        direction = "IN" if record["amount_minor"] > 0 else "OUT"
        cash = fields.get("debit_account" if direction == "IN" else "credit_account") or ""
        other = "C" if direction == "IN" else "N"
        offsets = [line for line in lines if line.get("account") != cash]
        if not offsets or any(line.get("side") != other for line in offsets):
            return []
        distinct = len(offsets) >= 2 or any(line.get(key) and line.get(key) != fields.get(key) for line in offsets for key in ("project", "expense", "counterparty")) or any(line.get("cost_center") for line in offsets)
        if not distinct:
            return []
        return [{"account": line["account"], "amount_minor": int(line["amount"]),
                 "counterparty": line.get("counterparty") if line.get("counterparty") not in own_codes else "",
                 "project": line.get("project") or "", "expense": line.get("expense") or "", "cost_center": line.get("cost_center") or ""} for line in offsets]

    @staticmethod
    def _normalize_lines(lines):
        if not isinstance(lines, list) or not 2 <= len(lines) <= 40:
            raise DataError("QUICK_LINES", "Bút toán cần từ 2 đến 40 dòng.")
        result = []
        for line in lines:
            if not isinstance(line, dict) or set(line) - set(LINE_KEYS):
                raise DataError("QUICK_LINES", "Dòng bút toán không hợp lệ.")
            side, amount = line.get("side"), line.get("amount")
            if side not in ("N", "C"):
                raise DataError("QUICK_LINES", "Mỗi dòng phải là Nợ hoặc Có.")
            if not isinstance(amount, int) or isinstance(amount, bool) or not 0 < amount <= 10 ** 15:
                raise DataError("QUICK_LINES", "Số tiền mỗi dòng phải là số nguyên dương (VND).")
            clean = {"side": side, "amount": amount}
            for key in ("account", "counterparty", "project", "expense", "cost_center"):
                value = line.get(key) or ""
                if not isinstance(value, str) or len(value) > 200:
                    raise DataError("QUICK_LINES", "Mã trên dòng bút toán không hợp lệ.")
                clean[key] = value.strip()
            result.append(clean)
        return result

    @staticmethod
    def _fields_from_lines(lines, direction, cash_account):
        other = "C" if direction == "IN" else "N"
        offsets = [line for line in lines if line["account"] != cash_account]
        opposite = [line for line in offsets if line["side"] == other] or offsets
        main = max(opposite, key=lambda line: line["amount"]) if opposite else {}
        fields = {name: None for name in FIELDS}
        fields["debit_account" if direction == "IN" else "credit_account"] = cash_account or None
        fields["credit_account" if direction == "IN" else "debit_account"] = main.get("account") or None
        fields["counterparty"] = main.get("counterparty") or next((line["counterparty"] for line in lines if line["counterparty"]), "") or None
        fields["project"] = main.get("project") or None
        fields["expense"] = main.get("expense") or None
        return fields, (main.get("cost_center") or None)

    def _line_errors(self, lines, record, cash_account, engine, at, debt_prefixes, *, check_cash):
        errors = []
        catalog = engine.catalog(record["business_date"], at)
        amount = abs(int(record["amount_minor"]))
        debit = sum(line["amount"] for line in lines if line["side"] == "N")
        credit = sum(line["amount"] for line in lines if line["side"] == "C")
        if debit != credit or debit <= 0:
            errors.append("LINES_UNBALANCED")
        if check_cash:
            cash_side = "N" if record["amount_minor"] > 0 else "C"
            net = sum(line["amount"] if line["side"] == cash_side else -line["amount"] for line in lines if line["account"] == cash_account)
            if not cash_account:
                errors.append("CASH_ACCOUNT_MAPPING_MISSING")
            elif net != amount:
                errors.append("LINES_CASH_AMOUNT")
        for line in lines:
            if not line["account"]:
                errors.append("LINES_MISSING_ACCOUNT")
                continue
            for key, kind, code in (("account", "ACCOUNT", "INVALID_ACCOUNT"), ("counterparty", "COUNTERPARTY", "INVALID_COUNTERPARTY"),
                                    ("project", "PROJECT", "INVALID_PROJECT"), ("expense", "EXPENSE", "INVALID_EXPENSE"), ("cost_center", "COST_CENTER", "INVALID_COST_CENTER")):
                if line.get(key) and (kind, line[key]) not in catalog:
                    errors.append(code if key != "account" else "INVALID_DEBIT_ACCOUNT" if line["side"] == "N" else "INVALID_CREDIT_ACCOUNT")
            if re.fullmatch(r"\d+", line["account"]) and any(line["account"].startswith(prefix) for prefix in debt_prefixes) and not line.get("counterparty"):
                errors.append("MISSING_COUNTERPARTY_FOR_" + line["account"])
        return errors

    def decide(self, run_id, items, actor, at):
        actor, at = text_id(actor, "actor"), instant_utc(at)
        if not isinstance(items, list) or not items:
            raise DataError("QUICK_DECISION", "Chọn ít nhất một bút toán.")
        _khong_phai_profile(self.db.execute("SELECT source_kind FROM quick_runs WHERE id=?", (run_id,)).fetchone())
        approved_records, revoke = [], []
        debt_prefixes = self._debt_prefixes()
        with transaction(self.store):
            for item in items:
                if not isinstance(item, dict):
                    raise DataError("QUICK_DECISION", "Quyết định không hợp lệ.")
                row = self.db.execute("SELECT * FROM quick_items WHERE id=? AND run_id=?", (item.get("id"), run_id)).fetchone()
                if not row:
                    raise DataError("QUICK_ITEM", "Không thấy bút toán cần xử lý.")
                action = item.get("action")
                if action == "CLEAR_EXISTING":
                    # Clearing the "already in Junsky" marker never creates an
                    # approval: an approved row stays approved, a skipped row
                    # stays skipped, a marked row becomes an ordinary waiting
                    # row.  An exported row cannot be cleared (no re-export).
                    if row["state"] == "EXPORTED":
                        raise DataError("QUICK_EXPORTED", "Giao dịch đã xuất file; không đổi được đánh dấu.")
                    if not row["excluded_from_export"] and row["state"] != "EXISTING":
                        continue
                    state = {"EXISTING": "WAIT", "APPROVE": "APPROVE", "SKIP": "SKIP", "WAIT": "WAIT"}[row["state"]]
                    self.db.execute("UPDATE quick_items SET state=?,excluded_from_export=0 WHERE id=?", (state, row["id"]))
                    self.db.execute("UPDATE bank_journal_matches SET excluded_from_export=0,matched_at=?,actor=? WHERE bank_document_id=?", (at, actor, row["document_id"]))
                    continue
                if action == "REOPEN":
                    if row["state"] not in ("APPROVE", "SKIP"):
                        raise DataError("QUICK_REOPEN", "Chỉ mở lại được giao dịch đã đồng ý hoặc đã bỏ qua và chưa xuất file.")
                    self.db.execute("UPDATE quick_items SET state='WAIT',decision_json=NULL,decision_lines_json=NULL,decision_cost_center=NULL,reason='',decided_at=?,actor=? WHERE id=?",
                                    (at, actor, row["id"]))
                    revoke.extend(self._forget_decision(row["document_id"]))
                    continue
                if action == "SKIP" and row["state"] == "EXISTING":
                    raise DataError("QUICK_EXISTING", "Giao dịch đang đánh dấu “đã có trong Junsky”; bỏ đánh dấu trước nếu muốn xử lý.")
                if action not in {"APPROVE", "SKIP"}:
                    raise DataError("QUICK_DECISION", "Chỉ nhận Đồng ý, Bỏ qua, Mở lại hoặc bỏ đánh dấu Junsky.")
                if row["state"] == "EXPORTED":
                    raise DataError("QUICK_EXPORTED", "Giao dịch đã xuất file; không đổi được quyết định.")
                payload = json.loads(row["proposal_json"])
                direction = "IN" if payload["amount_minor"] > 0 else "OUT"
                lines = item.get("lines")
                cost_center = item.get("cost_center")
                if cost_center is not None and (not isinstance(cost_center, str) or len(cost_center) > 200):
                    raise DataError("QUICK_COST_CENTER", "Mã TTCP không hợp lệ.")
                cost_center = cost_center.strip() if isinstance(cost_center, str) and cost_center.strip() else None
                invoice = self._is_invoice(payload)
                if lines is not None:
                    lines = self._normalize_lines(lines)
                    if invoice:
                        fields, line_center = self._invoice_fields_from_lines(lines, payload.get("invoice_direction") == "MUA_VAO")
                    else:
                        proposal_cash = (payload.get("cash_leg") or {}).get("account") or payload["fields"].get("debit_account" if direction == "IN" else "credit_account") or ""
                        fields, line_center = self._fields_from_lines(lines, direction, proposal_cash)
                    cost_center = cost_center or line_center
                else:
                    fields = item.get("fields", payload["fields"])
                if not isinstance(fields, dict) or set(fields) != set(FIELDS) or any(value is not None and not isinstance(value, str) for value in fields.values()):
                    raise DataError("QUICK_FIELDS", "Bộ trường bút toán không hợp lệ.")
                ui_lines = lines
                if action == "APPROVE":
                    record = document(self.store, row["document_id"], at)
                    engine = Engine(self.store, include_pending=True)
                    required = payload.get("policy", {}).get("required_fields", ["debit_account", "credit_account"])
                    errors = engine.validate_fields(fields, record["business_date"], at, required)
                    if cost_center and ("COST_CENTER", cost_center) not in engine.catalog(record["business_date"], at):
                        errors.append("INVALID_COST_CENTER")
                    hard = [code for code in payload.get("constraints", []) if code.startswith(("LOCKED_", "ZERO_", "IDENTIFIER_CONFLICT", "TEMPLATE_IDENTIFIER_CONFLICT", "CASH_ACCOUNT_", "MULTILINE_", "JOURNAL_PATTERN_MULTILINE_"))]
                    cash_account = "" if invoice else (fields.get("debit_account" if direction == "IN" else "credit_account") or "")
                    proposal_cash = (payload.get("cash_leg") or {}).get("account") or ""
                    if payload.get("source_kind", "sao_ke") in {"", "sao_ke"}:
                        if not cash_account or not is_cash_detail(cash_account):
                            errors.append("CASH_ACCOUNT_MAPPING_MISSING" if not cash_account else "CASH_FIELD_NOT_112")
                        elif proposal_cash and cash_account != proposal_cash:
                            errors.append("CASH_ACCOUNT_CONFLICT")
                    if ui_lines is None and invoice:
                        ui_lines = self._ui_lines(self._invoice_effective_lines(payload, fields, cost_center), fields, "")
                        errors.extend(code for code in self._line_errors(ui_lines, record, "", engine, at, debt_prefixes, check_cash=False)
                                      if code.startswith(("MISSING_COUNTERPARTY_FOR_", "LINES_")))
                    elif ui_lines is None:
                        effective = self._effective_lines({"lines": payload.get("lines", []), "cost_center": cost_center or payload.get("learning", {}).get("dimensions", {}).get("cost_center")},
                                                          fields, cash_account or None, "THU" if direction == "IN" else "CHI", abs(payload["amount_minor"]))
                        ui_lines = self._ui_lines(effective, fields, cash_account)
                        is_bank = payload.get("source_kind", "sao_ke") in {"", "sao_ke"}
                        errors.extend(code for code in self._line_errors(ui_lines, record, cash_account, engine, at, debt_prefixes, check_cash=is_bank)
                                      if code.startswith(("MISSING_COUNTERPARTY_FOR_", "LINES_")))
                    else:
                        errors.extend(self._line_errors(ui_lines, record, cash_account, engine, at, debt_prefixes, check_cash=not invoice))
                    if errors or hard:
                        codes = sorted(set(hard + errors))
                        raise DataError("QUICK_APPROVAL_EVIDENCE", "Chưa thể Đồng ý: " + explain_errors(codes) + " (" + ", ".join(codes) + ")")
                    # Invoices learn from Junsky once posted (V12 history), not
                    # from the conditions used for bank lines.
                    approved_records.append((record, fields, ui_lines, item.get("remember", True) is not False and not invoice))
                self.db.execute("UPDATE quick_items SET state=?,decision_json=?,decision_cost_center=?,decision_lines_json=?,reason=?,decided_at=?,actor=? WHERE id=?",
                                (action, canonical_json(fields), cost_center, canonical_json(lines) if lines is not None and action == "APPROVE" else None,
                                 str(item.get("reason", "") or "")[:500], at, actor, row["id"]))
            log(self.store, "V9B", "QUICK_DECIDE", run_id, actor, at, {"count": len(items)})
        for identifier in revoke:
            try:
                Knowledge(self.store).revoke(identifier, "CFO_NTD", at, "Anh mở lại giao dịch.", allow_pending=True)
            except DataError:
                pass
        for record, fields, ui_lines, remember in approved_records:
            if not remember:
                continue
            # Knowledge.service owns its own transaction.  Do not wrap it in
            # another SQLite transaction here: a decision must remain durable
            # even when it supersedes an earlier conditional pattern.
            self._create_condition_learning(record, fields, at, ui_lines)
            # V11 (F4): a loan/contract number in the narrative is a key of its own.
            if not bank_account(record.get("counterparty_account")):
                for key in self._numeric_keys(record):
                    self._create_condition_learning(record, fields, at, ui_lines, condition=("KEYWORD", "SO:" + key))
            self._learn_bank_account(record, fields.get("counterparty"), at)
        return self.rows(run_id)

    def _forget_decision(self, document_id):
        """Undo/Mở lại: learning created from this row's approval stops applying.

        Returns knowledge ids to revoke once the caller's transaction ends.
        """
        revoke = []
        for item in self.db.execute("SELECT id,knowledge_id,evidence_json FROM quick_condition_learning WHERE active=1").fetchall():
            try:
                sources = json.loads(item["evidence_json"])
            except json.JSONDecodeError:
                continue
            if document_id in sources:
                self.db.execute("UPDATE quick_condition_learning SET active=0 WHERE id=?", (item["id"],))
                if item["knowledge_id"]:
                    revoke.append(item["knowledge_id"])
        # The STK → counterparty identifier learned from the same approval.
        for item in self.db.execute("""SELECT id,evidence_json FROM knowledge_versions WHERE category='CATALOG'
                                       AND json_extract(payload_json,'$.source_status')='QUICK_DECISION'
                                       AND NOT EXISTS (SELECT 1 FROM knowledge_events e WHERE e.version_id=knowledge_versions.id AND e.action='REVOKE')""").fetchall():
            try:
                if document_id in json.loads(item["evidence_json"]):
                    revoke.append(item["id"])
            except (TypeError, json.JSONDecodeError):
                continue
        return revoke

    def clear_existing(self, run_id, item_id, actor="CFO_NTD", at=None):
        return self.decide(run_id, [{"id": item_id, "action": "CLEAR_EXISTING"}], actor, at or now_utc())

    def _learn_bank_account(self, record: dict, counterparty: str | None, at: str) -> None:
        account = bank_account(record.get("counterparty_account"))
        if not account or not counterparty or counterparty in Engine(self.store)._own_codes():
            return
        knowledge = Knowledge(self.store)
        key = "BANK_ACCOUNT:" + account
        prior = self.db.execute("SELECT id FROM knowledge_versions WHERE category='CATALOG' AND logical_key=? ORDER BY revision DESC LIMIT 1", (key,)).fetchone()
        item = {"category": "CATALOG", "logical_key": key, "valid_from": record["business_date"], "valid_to": None, "known_at": at,
                "payload": {"kind": "IDENTIFIER", "code": key, "identifier_type": "BANK_ACCOUNT", "value": account, "counterparty": counterparty,
                            "verified": True, "source_status": "QUICK_DECISION", "reliability": "HIGH"},
                "evidence": ["QUICK_DECISION", record["id"]], "supersedes_id": prior[0] if prior else None}
        try:
            identifier = knowledge.stage_many([item], "CFO_NTD", at)[0]
            knowledge.approve(identifier, "CFO_NTD", at)
        except DataError:
            pass

    def _unit_code(self, document_id, cutoff):
        row = self.db.execute("SELECT journal_document_id FROM bank_journal_matches WHERE bank_document_id=?", (document_id,)).fetchone()
        if row:
            journal = document(self.store, row["journal_document_id"], cutoff)
            if journal.get("unit_code"):
                return str(journal["unit_code"])
        units = {str(document(self.store, row[0], cutoff).get("unit_code") or "") for row in self.db.execute("SELECT id FROM documents WHERE kind='JOURNAL'")}
        units.discard("")
        if len(units) == 1:
            return next(iter(units))
        raise DataError("JUNSKY_UNIT_CODE_MISSING", "Không xác định duy nhất mã đơn vị Junsky từ sổ đã nạp.")

    def _next_voucher_numbers(self, unit, direction, business_date, count, cutoff):
        prefix = unit + ("BR" if direction == "THU" else "BP") + business_date[2:4] + business_date[5:7]
        pattern = re.compile(re.escape(prefix) + r"-(\d{4,})$")
        existing = 0
        for row in self.db.execute("SELECT id FROM documents WHERE kind='JOURNAL'"):
            voucher = str(document(self.store, row[0], cutoff).get("voucher_number") or "")
            found = pattern.fullmatch(voucher)
            if found:
                existing = max(existing, int(found.group(1)))
        counter = self.db.execute("SELECT last_number FROM export_counters WHERE prefix_month=?", (prefix,)).fetchone()
        start = max(existing, int(counter["last_number"]) if counter else 0) + 1
        self.db.execute("INSERT INTO export_counters(prefix_month,last_number,updated_at,actor) VALUES (?,?,?,?) ON CONFLICT(prefix_month) DO UPDATE SET last_number=excluded.last_number,updated_at=excluded.updated_at,actor=excluded.actor",
                        (prefix, start + count - 1, now_utc(), "CFO_NTD"))
        return [f"{prefix}-{number:04d}" for number in range(start, start + count)]

    @staticmethod
    def _write_workbook(template: Path, output: Path, items):
        if template.is_file():
            wb = load_workbook(template, data_only=False, keep_links=False)
        else:
            wb = Workbook(); wb.remove(wb.active)
        try:
            for name, headers in (("CB_tmpEntry1", ENTRY1_HEADERS), ("CB_tmpEntry2", ENTRY2_HEADERS)):
                ws = wb[name] if name in wb.sheetnames else wb.create_sheet(name)
                if ws.max_row == 1 and ws.cell(1, 1).value is None:
                    # ``append`` on a fresh openpyxl worksheet writes row 2:
                    # the required fallback header must be exactly row 1.
                    for column, header in enumerate(headers, 1):
                        ws.cell(1, column, header)
                actual = tuple(ws.cell(1, column).value for column in range(1, len(headers) + 1))
                if actual != headers:
                    raise DataError("JUNSKY_TEMPLATE", "Mẫu Junsky không đúng cấu trúc Entry1 17 cột và Entry2 37 cột ở hàng 1.")
                for one, two in items:
                    for value in ([one] if name.endswith("1") else two):
                        ws.append([value.get(header, "") for header in headers])
                for column in ws.iter_cols():
                    for cell in column:
                        if isinstance(cell.value, str):
                            cell.number_format = "@"
            wb.save(output)
        finally:
            wb.close()

    @staticmethod
    def _effective_lines(row, fields, cash_account, direction, amount):
        """Keep a learned/template split while applying editable header fields."""
        lines = deepcopy(row.get("lines") or [])
        if not lines:
            return [{"account": fields.get("debit_account"), "debit_minor": amount, "credit_minor": 0, "dimensions": {}},
                    {"account": fields.get("credit_account"), "debit_minor": 0, "credit_minor": amount, "dimensions": {}}]
        cash_side = "DEBIT" if direction == "THU" else "CREDIT"
        for line in lines:
            account = str(line.get("account") or "")
            side = "DEBIT" if int(line.get("debit_minor", 0) or 0) else "CREDIT"
            if account.startswith("112") or (side == cash_side and account == cash_account):
                line["account"] = cash_account
        counterpart = fields.get("credit_account" if direction == "THU" else "debit_account")
        if counterpart:
            other_side = "CREDIT" if direction == "THU" else "DEBIT"
            candidates = [line for line in lines if ("DEBIT" if int(line.get("debit_minor", 0) or 0) else "CREDIT") == other_side and not str(line.get("account") or "").startswith("112")]
            if candidates:
                max(candidates, key=lambda line: max(int(line.get("debit_minor", 0) or 0), int(line.get("credit_minor", 0) or 0)))["account"] = counterpart
        for line in lines:
            dimensions = dict(line.get("dimensions") or {})
            if line.get("account") != cash_account:
                for key in ("project", "expense"):
                    if fields.get(key):
                        dimensions[key] = fields[key]
                if row.get("cost_center"):
                    dimensions["cost_center"] = row["cost_center"]
            line["dimensions"] = dimensions
        return lines

    @staticmethod
    def _is_invoice(payload) -> bool:
        return payload.get("source_kind") in {"hoa_don", "bang_ke"} or bool(payload.get("invoice_direction"))

    @staticmethod
    def _invoice_effective_lines(payload, fields, cost_center=None):
        """V12: lines of an invoice entry with the editable header fields applied.

        Mua vào: Nợ TK chi phí/hàng (tiền chưa thuế) + Nợ 1331 / Có TK công nợ
        (tổng).  Bán ra: Nợ TK phải thu (tổng) / Có TK doanh thu (chưa thuế)
        + Có 33311.  Dự án, khoản mục chỉ gắn vào dòng chi phí / doanh thu.
        """
        purchase = payload.get("invoice_direction") == "MUA_VAO"
        main_field, partner_field = ("debit_account", "credit_account") if purchase else ("credit_account", "debit_account")
        lines = deepcopy(payload.get("lines") or [])
        amounts = payload.get("invoice_amounts") or {}
        net, tax, total = amounts.get("net"), amounts.get("tax"), amounts.get("total")
        if not lines:
            if not all(isinstance(value, int) for value in (net, tax, total)) or net + tax != total:
                net, tax, total = abs(int(payload["amount_minor"])), 0, abs(int(payload["amount_minor"]))
            if purchase:
                lines = [{"line_id": "NET", "account": None, "debit_minor": net, "credit_minor": 0}]
                if tax:
                    lines.append({"line_id": "VAT", "account": "1331", "debit_minor": tax, "credit_minor": 0})
                lines.append({"line_id": "PAYABLE", "account": None, "debit_minor": 0, "credit_minor": total})
            else:
                lines = [{"line_id": "RECEIVABLE", "account": None, "debit_minor": total, "credit_minor": 0},
                         {"line_id": "REVENUE", "account": None, "debit_minor": 0, "credit_minor": net}]
                if tax:
                    lines.append({"line_id": "VAT", "account": "33311", "debit_minor": 0, "credit_minor": tax})
        for line in lines:
            kind = str(line.get("line_id") or "")
            dimensions = {}
            if kind.startswith("NET") or kind == "REVENUE":
                line["account"] = fields.get(main_field) or line.get("account")
                dimensions = {key: fields[key] for key in ("project", "expense") if fields.get(key)}
                if cost_center:
                    dimensions["cost_center"] = cost_center
            elif kind in ("PAYABLE", "RECEIVABLE"):
                line["account"] = fields.get(partner_field) or line.get("account")
            line["dimensions"] = dimensions
        return lines

    @staticmethod
    def _invoice_fields_from_lines(lines, purchase):
        """Header fields of an invoice entry from the lines Anh approved."""
        tax_prefix = "1331" if purchase else "3331"
        main_side, partner_side = ("N", "C") if purchase else ("C", "N")
        mains = [line for line in lines if line["side"] == main_side and not str(line["account"] or "").startswith(tax_prefix)]
        partners = [line for line in lines if line["side"] == partner_side]
        main = max(mains, key=lambda line: line["amount"]) if mains else {}
        partner = max(partners, key=lambda line: line["amount"]) if partners else {}
        fields = {name: None for name in FIELDS}
        fields["debit_account" if purchase else "credit_account"] = main.get("account") or None
        fields["credit_account" if purchase else "debit_account"] = partner.get("account") or None
        fields["counterparty"] = partner.get("counterparty") or main.get("counterparty") or next((line["counterparty"] for line in lines if line["counterparty"]), "") or None
        fields["project"] = main.get("project") or None
        fields["expense"] = main.get("expense") or None
        return fields, (main.get("cost_center") or None)

    def _names(self, business_date, cutoff):
        names = {}
        for (kind, code), row in Engine(self.store).catalog(business_date, cutoff).items():
            names[(kind, code)] = str(row["payload"].get("name") or "")
        return names

    def export(self, run_id, root: Path, *, junsky_files=True, actor="CFO_NTD"):
        """Write the review workbook (always) and, at level 2, the Junsky files.

        Only rows Anh approved are written.  Rows that may already exist in
        Junsky stay out until he clears that marker.  Nothing is imported.
        """
        run_id = text_id(run_id, "run_id")
        if self._settings().get("scoring_mode"):
            raise DataError("QUICK_SCORING_MODE", "Đang bật Chế độ chấm điểm: tắt ở màn Nguồn dữ liệu và bấm “Đề xuất lại” trước khi xuất File soát.")
        with transaction(self.store):
            # One transaction: voucher counters, EXPORTED marks and history
            # commit together, or not at all (a retry reuses the same numbers
            # and file names).
            return self._export(run_id, Path(root), junsky_files=junsky_files, actor=actor)

    def _export(self, run_id, root: Path, *, junsky_files, actor):
        all_rows = self.rows(run_id)["rows"]
        approved_all = [row for row in all_rows if row["state"] == "APPROVE"]
        # A row that may already be in Junsky stays out of every file (and
        # unmarked) until Anh clears that marker.
        review_rows = [row for row in approved_all if not row["potential_existing"]]
        approved = [row for row in review_rows if row["source_kind"] in {"", "sao_ke"}]
        if not junsky_files and not review_rows:
            raise DataError("QUICK_EXPORT_EMPTY", "Chưa có giao dịch Đã đồng ý để xuất.")
        output = Path(root) / "xuat-junsky" / run_id; output.mkdir(parents=True, exist_ok=True)
        settings, cutoff = self._settings(), now_utc()
        by_batch = defaultdict(list); voucher_ids, paths = [], []
        if junsky_files:
            for row in approved:
                direction = "THU" if row["amount_minor"] > 0 else "CHI"
                unit = self._unit_code(row["document_id"], cutoff)
                by_batch[(direction, unit, row["business_date"][:7])].append(row)
        template_key = {"THU": "template_thu", "CHI": "template_chi"}
        for (direction, unit, month), entries in sorted(by_batch.items()):
            entries.sort(key=lambda item: (item["business_date"], item["id"]))
            numbers = self._next_voucher_numbers(unit, direction, entries[0]["business_date"], len(entries), cutoff)
            workbook_items = []
            for entry, row in zip(numbers, entries):
                record = document(self.store, row["document_id"], cutoff)
                amount, fields = abs(row["amount_minor"]), row["fields"]
                cash_account = fields["debit_account"] if direction == "THU" else fields["credit_account"]
                if not cash_account or not is_cash_detail(cash_account):
                    raise DataError("JUNSKY_CASH_ACCOUNT", "Bút toán xuất thiếu vế TK tiền đã cấu hình.")
                source_account = bank_account(record.get("account"))
                bank_id = str(settings["bank_ids"].get(source_account, settings["bank_ids"].get(record.get("account", ""), settings["bank_ids"].get(record.get("bank", ""), ""))))
                one = {"EntryID": entry, "EntryDate": date.fromisoformat(row["business_date"]), "BankID": bank_id, "AcctID": cash_account,
                       "OrglID": "VND", "OrglRate": 1, "OrglAmt": amount, "BaseAmt": amount, "ObjectID": fields.get("counterparty") or "",
                       "PayerID": "", "PayerText": record.get("counterparty_name") or "", "BranchID": unit, "Memo": row.get("source_description", ""),
                       "DocsNo": row.get("source_reference", ""), "MRowID": "", "PeriodID": "", "ErrorText": ""}
                if row.get("decision_lines"):
                    lines = self._engine_lines(row["decision_lines"])
                else:
                    lines = self._effective_lines(row, fields, cash_account, direction, amount)
                if sum(int(line.get("debit_minor", 0) or 0) for line in lines) != sum(int(line.get("credit_minor", 0) or 0) for line in lines):
                    raise DataError("JUNSKY_UNBALANCED", "Bút toán xuất không cân Nợ = Có.")
                two = []
                for offset, line in enumerate(lines, 1):
                    entry_bank = bank_id if settings["export_mode"] == "DAY_DU" and line.get("account") == cash_account else ""
                    dimensions = line.get("dimensions") if isinstance(line.get("dimensions"), dict) else {}
                    two.append({"EntryID": entry, "Offset": offset, "AcctID": line.get("account") or "", "BankID": entry_bank, "OrglID": "VND", "OrglRate": 1,
                                "OrglDeb": line.get("debit_minor", 0), "OrglCrd": line.get("credit_minor", 0), "BaseDeb": line.get("debit_minor", 0),
                                "BaseCrd": line.get("credit_minor", 0), "ObjectID": dimensions.get("counterparty") or fields.get("counterparty") or "", "EntryDM": "", "CashflowID": "", "PrecostID": "",
                                "ProjectID": dimensions.get("project") or fields.get("project") or "", "CenterID": dimensions.get("cost_center") or row.get("cost_center") or "", "CostID": dimensions.get("expense") or fields.get("expense") or "", "Remark": "", "VatID": "", "VatAcctID": "",
                                "BaseBefVat": "", "BaseAmtVat": "", "InvName": "", "InvAddr": "", "InvCode": "", "InvForm": "", "InvSeri": "", "InvNo": "",
                                "InvDate": "", "InvMode": "", "InvText": "", "InvLook": "", "iRow": offset, "DRowID": "", "MRowID": "", "DebtID": "", "ErrorText": ""})
                workbook_items.append((one, two)); voucher_ids.append(entry)
            safe_unit = re.sub(r"[^A-Za-z0-9_-]", "_", unit)
            path = output / f"JUNSKY-{direction}-{safe_unit}-{month.replace('-', '')}-{run_id[:8]}.xlsx"
            self._write_workbook(Path(settings[template_key[direction]]), path, workbook_items)
            paths.append(str(path))
        number = self.db.execute("SELECT COUNT(*) FROM quick_exports WHERE run_id=?", (run_id,)).fetchone()[0] + 1
        months = sorted({row["business_date"][:7] for row in review_rows}) or [cutoff[:7]]
        period = months[0] if len(months) == 1 else months[0] + "_" + months[-1]
        review_path = output / f"SOAT-DINH-KHOAN-{period}-lan{number}-{run_id[:8]}.xlsx"
        self._write_review(review_path, review_rows, cutoff, actor)
        # Every row written to this export (review workbook, and at level 2
        # the Junsky files) is marked once, so no later export repeats it.
        exported_ids = [row["id"] for row in review_rows]
        total = sum(abs(row["amount_minor"]) for row in review_rows)
        if exported_ids:
            placeholders = ",".join("?" for _ in exported_ids)
            self.db.execute(f"UPDATE quick_items SET state='EXPORTED' WHERE id IN ({placeholders}) AND state='APPROVE'", exported_ids)
        export_id = uid()
        files = [review_path.name] + [Path(path).name for path in paths]
        self.db.execute("INSERT INTO quick_exports(id,run_id,exported_at,actor,item_count,total_minor,files_json) VALUES (?,?,?,?,?,?,?)",
                        (export_id, run_id, cutoff, text_id(actor, "actor"), len(review_rows), total, canonical_json(files)))
        log(self.store, "V10", "QUICK_EXPORT", run_id, actor, cutoff, {"count": len(review_rows), "junsky_files": bool(junsky_files), "no_auto_import": True})
        return {"files": paths, "review": str(review_path), "approved": len(approved), "reviewed": len(review_rows), "voucher_ids": voucher_ids,
                "no_auto_import": True, "export_id": export_id, "total_minor": total, "junsky_files": bool(junsky_files)}

    @staticmethod
    def _kind_word(row) -> str:
        direction = row.get("invoice_direction")
        if direction:
            return "Mua vào" if direction == "MUA_VAO" else "Bán ra"
        return "Thu" if row["amount_minor"] > 0 else "Chi"

    def _write_review(self, path: Path, rows, cutoff, actor):
        """Line-level review workbook the accountant keys into Junsky (mức 1)."""
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
        names = self._names(cutoff[:10], cutoff)
        book = Workbook(); sheet = book.active; sheet.title = "BUT TOAN"
        headers = ["STT", "Ngày", "Thu/Chi · Mua/Bán", "Số tiền giao dịch (VND)", "Diễn giải ngân hàng / tên hàng hóa đơn", "Số tham chiếu NH / số hóa đơn", "Nợ/Có", "Tài khoản", "Tên tài khoản",
                   "Số tiền dòng (VND)", "Mã đối tượng", "Tên đối tượng", "Dự án", "Khoản mục", "TTCP", "Mức đề xuất", "Vì sao", "Người duyệt", "Thời điểm duyệt"]
        sheet.append(headers)
        base, bold = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True)
        fill = PatternFill("solid", start_color="E8EFFB")
        for cell in sheet[1]:
            cell.font, cell.fill = bold, fill
            cell.alignment = Alignment(wrap_text=True, vertical="center")
        rows = sorted(rows, key=lambda item: (item["business_date"], item["id"]))
        for index, row in enumerate(rows, 1):
            first = True
            for line in row["entry_lines"]:
                sheet.append([index if first else None, date.fromisoformat(row["business_date"]) if first else None,
                              self._kind_word(row) if first else None, abs(row["amount_minor"]) if first else None,
                              row.get("source_description", "") if first else None, row.get("source_reference", "") if first else None,
                              "Nợ" if line["side"] == "N" else "Có", line["account"], names.get(("ACCOUNT", line["account"]), ""), line["amount"],
                              line.get("counterparty") or "", names.get(("COUNTERPARTY", line.get("counterparty") or ""), ""),
                              line.get("project") or "", line.get("expense") or "", line.get("cost_center") or "",
                              row.get("proposal_level", "") if first else None, row.get("why", "") if first else None,
                              row.get("actor") or "" if first else None, _vn_date(row.get("decided_at")) if first else None])
                first = False
        widths = [6, 11, 8, 18, 46, 18, 7, 11, 30, 18, 16, 34, 12, 14, 10, 12, 60, 12, 14]
        for column, width in enumerate(widths, 1):
            sheet.column_dimensions[get_column_letter(column)].width = width
        for line in sheet.iter_rows(min_row=2):
            for cell in line:
                cell.font = base
            line[1].number_format = "DD/MM/YYYY"
            line[3].number_format = "#,##0"
            line[9].number_format = "#,##0"
            for position in (7, 10):
                line[position].number_format = "@"
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(1, sheet.max_row)}"
        summary = book.create_sheet("TONG HOP")
        last = max(2, sheet.max_row)
        summary.append(["Chỉ tiêu", "Giá trị"])
        summary.append(["Số giao dịch đã đồng ý", f"=COUNT('BUT TOAN'!A2:A{last})"])
        summary.append(["Tổng thu (VND)", f"=SUMIFS('BUT TOAN'!D2:D{last},'BUT TOAN'!C2:C{last},\"Thu\")"])
        summary.append(["Tổng chi (VND)", f"=SUMIFS('BUT TOAN'!D2:D{last},'BUT TOAN'!C2:C{last},\"Chi\")"])
        summary.append(["Tổng hóa đơn mua vào (VND)", f"=SUMIFS('BUT TOAN'!D2:D{last},'BUT TOAN'!C2:C{last},\"Mua vào\")"])
        summary.append(["Tổng hóa đơn bán ra (VND)", f"=SUMIFS('BUT TOAN'!D2:D{last},'BUT TOAN'!C2:C{last},\"Bán ra\")"])
        summary.append(["Tổng Nợ các dòng (VND)", f"=SUMIFS('BUT TOAN'!J2:J{last},'BUT TOAN'!G2:G{last},\"Nợ\")"])
        summary.append(["Tổng Có các dòng (VND)", f"=SUMIFS('BUT TOAN'!J2:J{last},'BUT TOAN'!G2:G{last},\"Có\")"])
        summary.append(["Kiểm tra Nợ = Có", "=IF(B7=B8,\"Khớp\",\"LỆCH\")"])
        summary.append(["Thời điểm xuất (UTC)", cutoff])
        summary.append(["Người xuất", actor])
        summary.append(["Ghi chú", "Phần mềm không tự nhập Junsky. Kế toán nhập tay theo file này; chỉ gồm giao dịch Đã đồng ý."])
        for line in summary.iter_rows():
            for cell in line:
                cell.font = base
        for cell in summary[1]:
            cell.font, cell.fill = bold, fill
        for position in range(3, 9):
            summary.cell(position, 2).number_format = "#,##0"
        summary.column_dimensions["A"].width, summary.column_dimensions["B"].width = 28, 70
        book.calculation.fullCalcOnLoad = True
        book.save(path); book.close()

    def history(self, limit=50):
        result = []
        for row in self.db.execute("""SELECT e.*, r.source_name FROM quick_exports e JOIN quick_runs r ON r.id=e.run_id
                                      ORDER BY e.exported_at DESC LIMIT ?""", (int(limit),)):
            result.append({"id": row["id"], "run_id": row["run_id"], "at": row["exported_at"], "actor": row["actor"], "count": row["item_count"],
                           "total_minor": row["total_minor"], "files": json.loads(row["files_json"]), "source_name": row["source_name"] or ""})
        return result

    def runs(self, limit=12):
        result = []
        for row in self.db.execute("""SELECT r.id, r.source_kind, r.created_at, r.source_name, r.source_info_json,
                                             COUNT(i.id) n, SUM(i.state='APPROVE') approved, SUM(i.state='EXPORTED') exported,
                                             SUM(i.state='WAIT') waiting, SUM(i.state='SKIP') skipped, SUM(i.state='EXISTING') existing,
                                             MIN(json_extract(i.proposal_json,'$.business_date')) first_day, MAX(json_extract(i.proposal_json,'$.business_date')) last_day
                                      FROM quick_runs r LEFT JOIN quick_items i ON i.run_id=r.id
                                      WHERE r.source_kind NOT IN ('NGHIEM_THU')
                                      GROUP BY r.id ORDER BY r.created_at DESC LIMIT ?""", (int(limit),)):
            result.append({"id": row["id"], "source_kind": row["source_kind"], "created_at": row["created_at"], "source_name": row["source_name"] or "",
                           "source_info": json.loads(row["source_info_json"]) if row["source_info_json"] else {}, "count": row["n"] or 0,
                           "approved": row["approved"] or 0, "exported": row["exported"] or 0, "waiting": row["waiting"] or 0,
                           "skipped": row["skipped"] or 0, "existing": row["existing"] or 0, "first_day": row["first_day"], "last_day": row["last_day"]})
        return result

    def run_for_hash(self, digest):
        row = self.db.execute("SELECT id FROM quick_runs WHERE source_hash=? ORDER BY created_at DESC LIMIT 1", (digest,)).fetchone()
        return row[0] if row else None

    # ------------------------------------------------------------------
    # V11 — ghi chú AI, gói ngữ cảnh cho Claude, chấm điểm so với Junsky
    # ------------------------------------------------------------------
    def set_ai_note(self, run_id, item_id, note, actor="CFO_NTD", at=None):
        run_id, item_id = text_id(run_id, "run_id"), text_id(item_id, "item_id")
        at = instant_utc(at or now_utc())
        if not isinstance(note, str) or len(note) > 4000:
            raise DataError("AI_NOTE", "Ghi chú tối đa 4.000 ký tự.")
        with transaction(self.store):
            row = self.db.execute("SELECT id FROM quick_items WHERE id=? AND run_id=?", (item_id, run_id)).fetchone()
            if not row:
                raise DataError("QUICK_ITEM", "Không thấy giao dịch cần ghi chú.")
            self.db.execute("UPDATE quick_items SET ai_note=?,ai_note_at=? WHERE id=?", (note.strip() or None, at if note.strip() else None, item_id))
            log(self.store, "V11", "AI_NOTE", item_id, text_id(actor, "actor"), at, {"run_id": run_id, "length": len(note.strip())})
        return {"id": item_id, "ai_note": note.strip(), "ai_note_at": at if note.strip() else None}

    def ai_context(self, run_id, item_ids=None, cutoff=None):
        """Markdown package of the rows Anh annotated, for a Claude session to read.

        Contains the transaction as the screen shows it, the machine's reasons
        and evidence, the matched Junsky voucher when any, Anh's note, and the
        measured history behind the proposal.  No credentials, no file paths of
        other systems; bank account numbers are masked.
        """
        run_id = text_id(run_id, "run_id")
        cutoff = instant_utc(cutoff or now_utc())
        wanted = set(item_ids or [])
        rows = [row for row in self.rows(run_id)["rows"] if (row["id"] in wanted) or (not wanted and row.get("ai_note"))]
        if not rows:
            raise DataError("AI_CONTEXT", "Chưa có giao dịch nào được ghi chú cho AI.")
        run = self.db.execute("SELECT * FROM quick_runs WHERE id=?", (run_id,)).fetchone()
        names = self._names(cutoff[:10], cutoff)
        lines = [f"# Ghi chú AI — {run['source_name'] or run['source_kind']} ({len(rows)} giao dịch)", "",
                 f"Lập lúc: {_vn_date(cutoff)} · Lần đề xuất: {run_id[:8]} · Mỗi mục: giao dịch → máy đề xuất → vì sao → ghi chú của Anh.", ""]
        for index, row in enumerate(rows, 1):
            direction = "Thu" if row["amount_minor"] > 0 else "Chi"
            lines.append(f"## {index}. {_vn_date(row['business_date'])} · {direction} {abs(row['amount_minor']):,} VND".replace(",", "."))
            lines.append(f"- Diễn giải: {row.get('source_description') or ''}")
            if row.get("source_counterparty_name"):
                lines.append(f"- Tên đối ứng trên sao kê: {row['source_counterparty_name']}")
            lines.append(f"- Trạng thái: {row['state']} · Mức: {row.get('proposal_level')}")
            entry = "; ".join(f"{'Nợ' if l.get('side') == 'N' else 'Có'} {l.get('account') or '?'} {int(l.get('amount') or 0):,}".replace(",", ".")
                              + (f" [{l.get('counterparty')}]" if l.get("counterparty") else "") + (f" DA={l.get('project')}" if l.get("project") else "")
                              for l in row.get("entry_lines") or [])
            lines.append(f"- Máy đề xuất: {entry or '(trống)'}")
            if row.get("fields", {}).get("counterparty"):
                code = row["fields"]["counterparty"]
                lines.append(f"- Đối tượng: {code} – {names.get(('COUNTERPARTY', code), '')}")
            lines.append(f"- Vì sao: {row.get('why') or ''}")
            if row.get("stats"):
                stats = row["stats"]
                lines.append(f"- Số đo: {stats.get('consistent')}/{stats.get('window')} chứng từ cùng mẫu ({stats.get('from')}–{stats.get('to')}), {stats.get('total')} chứng từ tương tự")
            if row.get("name_options"):
                lines.append("- Tên gần giống trong danh mục: " + "; ".join(f"{o['code']} ({o.get('name', '')})" for o in row["name_options"][:5]))
            if row.get("identifier_conflict"):
                conflict = row["identifier_conflict"]
                lines.append(f"- Mâu thuẫn danh bạ STK: mã {conflict.get('code')} ({conflict.get('name')}) — đã bỏ qua")
            if row.get("demoted_rule"):
                rule = row["demoted_rule"]
                lines.append(f"- Quy tắc bị hạ quyền: {rule.get('code')} “{rule.get('keyword')}” → {rule.get('account')} (gặp {rule.get('seen')}, đúng {rule.get('right')})")
            if row.get("junsky_voucher"):
                lines.append(f"- Chứng từ Junsky khớp: {row['junsky_voucher']}" + (f" ({row['group']['size']} lần chuyển = 1 chứng từ)" if row.get("group") else ""))
            if row.get("basis"):
                lines.append("- Căn cứ (chứng từ cũ):")
                for item in row["basis"][:6]:
                    lines.append(f"  - {item.get('d')} · {item.get('no')} · {item.get('desc')} · {item.get('hk') or ''}")
            if row.get("constraints"):
                lines.append("- Mã ràng buộc: " + ", ".join(row["constraints"][:8]))
            lines.append(f"- **Ghi chú của Anh:** {row.get('ai_note') or '(chưa ghi)'}")
            lines.append("")
        lines.append("---")
        lines.append("Yêu cầu cho Claude: với mỗi giao dịch, phân tích vì sao máy đề xuất như vậy, cách hạch toán đúng theo ghi chú, và cần sửa cách tạo tri thức (quy tắc / mẫu học / danh bạ) thế nào để các giao dịch cùng loại ra đúng ở lần sau.")
        return {"run_id": run_id, "count": len(rows), "markdown": "\n".join(lines)}

    def score(self, run_id, cutoff=None):
        """So đề xuất của máy với chứng từ Junsky (đáp án) cho từng dòng.

        Dùng mọi chứng từ trong sổ (kể cả sau mốc học): khớp một dòng ↔ một
        chứng từ theo ngày + số tiền (gộp dòng 112), hoặc nhiều dòng cùng ngày
        cùng đối tượng ↔ một chứng từ.  So TK đối ứng, đối tượng, dự án.
        """
        run_id = text_id(run_id, "run_id")
        cutoff = instant_utc(cutoff or now_utc())
        run = self.db.execute("SELECT source_kind FROM quick_runs WHERE id=?", (run_id,)).fetchone()
        if not run:
            raise DataError("QUICK_RUN", "Không thấy lần đề xuất này.")
        rows = self.rows(run_id)["rows"]
        stale = sum(1 for row in rows if row["state"] == "EXISTING")
        if stale:
            raise DataError("QUICK_SCORE_STALE", f"Còn {stale} giao dịch đang đánh dấu “Đã có trong Junsky” từ lần chạy trước. Bật Chế độ chấm điểm, bấm “Đề xuất lại” rồi chấm.")
        journals, answer_source = self._answer_journals(cutoff)
        if run["source_kind"] in ("hoa_don", "bang_ke"):
            return self._score_invoices(run_id, rows, journals, answer_source, cutoff)
        records = {row["document_id"]: document(self.store, row["document_id"], cutoff) for row in rows}
        groups = match_bank_groups_to_journal(list(records.values()), journals)
        by_id = {journal["id"]: journal for journal in journals}
        names = self._names(cutoff[:10], cutoff)
        results, summary = [], Counter()
        for row in rows:
            record = records[row["document_id"]]
            match = match_bank_to_journal(record, journals, require_description=False)
            if match["status"] != "UNIQUE" and record["id"] in groups:
                match = groups[record["id"]]
            level = row.get("proposal_level") or "Đỏ"
            summary[(level, "n")] += 1
            direction = "IN" if row["amount_minor"] > 0 else "OUT"
            entry = {"id": row["id"], "business_date": row["business_date"], "amount_minor": row["amount_minor"], "level": level, "state": row["state"],
                     "description": row.get("source_description") or "", "proposed": "", "actual": "", "voucher": "", "group": bool((match.get("group") or {})),
                     "account_ok": None, "counterparty_ok": None, "project_ok": None, "counterparty": row.get("fields", {}).get("counterparty") or "",
                     "actual_counterparty": "", "project": row.get("fields", {}).get("project") or "", "actual_project": ""}
            proposed = sorted({str(l.get("account") or "") for l in row.get("entry_lines") or [] if l.get("account") and not str(l.get("account")).startswith("112")})
            entry["proposed"] = "+".join(proposed)
            if match["status"] != "UNIQUE":
                entry["note"] = "Không ghép được với chứng từ Junsky"
                summary[(level, "unmatched")] += 1
                results.append(entry); continue
            journal = by_id.get(match["journal_id"])
            primary, lines = _opposite_accounts(journal, direction) if journal else (None, [])
            actual = sorted({line["account"] for line in lines})
            entry.update(actual="+".join(actual), voucher=match.get("voucher_number") or "", actual_counterparty=str(journal.get("counterparty") or ""), actual_project=str(journal.get("project") or ""))
            entry["account_ok"] = bool(actual) and proposed == actual
            entry["counterparty_ok"] = (entry["counterparty"] == entry["actual_counterparty"]) if entry["counterparty"] else None
            entry["project_ok"] = (entry["project"] == entry["actual_project"]) if entry["project"] else None
            summary[(level, "matched")] += 1
            summary[(level, "account_ok")] += int(bool(entry["account_ok"]))
            if entry["counterparty"]:
                summary[(level, "counterparty_given")] += 1
                summary[(level, "counterparty_ok")] += int(bool(entry["counterparty_ok"]))
            if entry["project"]:
                summary[(level, "project_given")] += 1
                summary[(level, "project_ok")] += int(bool(entry["project_ok"]))
            results.append(entry)
        table = []
        for level in ("Xanh", "Vàng", "Đỏ"):
            table.append({"level": level, "rows": summary[(level, "n")], "matched": summary[(level, "matched")], "unmatched": summary[(level, "unmatched")],
                          "account_ok": summary[(level, "account_ok")], "counterparty_given": summary[(level, "counterparty_given")], "counterparty_ok": summary[(level, "counterparty_ok")],
                          "project_given": summary[(level, "project_given")], "project_ok": summary[(level, "project_ok")]})
        return {"run_id": run_id, "rows": results, "summary": table, "answer_source": answer_source,
                "names": {code: name for (kind, code), name in names.items() if kind == "COUNTERPARTY"}}

    def _score_invoices(self, run_id, rows, journals, answer_source, cutoff):
        """V12: each invoice ↔ the voucher that posted it (amounts), compared per direction."""
        index = InvoiceJournalIndex(journals)
        names = self._names(cutoff[:10], cutoff)
        results, summary = [], Counter()
        for row in rows:
            record = document(self.store, row["document_id"], cutoff)
            purchase = record.get("direction") == "MUA_VAO"
            side = "Mua vào" if purchase else "Bán ra"
            level = (row.get("proposal_level") or "Đỏ") + " · " + side
            summary[(level, "n")] += 1
            fields = row.get("fields") or {}
            lines = row.get("entry_lines") or []
            if purchase:
                proposed = sorted({l["account"] for l in lines if l.get("side") == "N" and l.get("account") and not str(l["account"]).startswith("1331")})
                partner = sorted({l["account"] for l in lines if l.get("side") == "C" and l.get("account")})
            else:
                proposed = sorted({l["account"] for l in lines if l.get("side") == "C" and l.get("account") and not str(l["account"]).startswith("3331")})
                partner = sorted({l["account"] for l in lines if l.get("side") == "N" and l.get("account")})
            entry = {"id": row["id"], "business_date": row["business_date"], "amount_minor": row["amount_minor"], "level": level, "state": row["state"],
                     "description": row.get("source_description") or "", "proposed": "+".join(proposed), "actual": "", "voucher": "", "group": False,
                     "partner": "+".join(partner), "actual_partner": "", "partner_ok": None,
                     "account_ok": None, "counterparty_ok": None, "project_ok": None, "counterparty": fields.get("counterparty") or "",
                     "actual_counterparty": "", "project": fields.get("project") or "", "actual_project": ""}
            link = index.link(record, fields.get("counterparty") or "")
            if not link:
                entry["note"] = "Không ghép được với chứng từ Junsky"
                summary[(level, "unmatched")] += 1
                results.append(entry); continue
            entry.update(actual=link["account"], voucher=link["voucher"], actual_partner=link["partner_account"],
                         actual_counterparty=link["journal_party"], actual_project=link["project"])
            entry["account_ok"] = bool(proposed) and proposed == [link["account"]]
            entry["partner_ok"] = (partner == [link["partner_account"]]) if partner and link["partner_account"] else None
            entry["counterparty_ok"] = (entry["counterparty"] == entry["actual_counterparty"]) if entry["counterparty"] else None
            entry["project_ok"] = (entry["project"] == entry["actual_project"]) if entry["project"] else None
            summary[(level, "matched")] += 1
            summary[(level, "account_ok")] += int(bool(entry["account_ok"]))
            summary[(level, "partner_ok")] += int(bool(entry["partner_ok"]))
            for name in ("counterparty", "project"):
                if entry[name]:
                    summary[(level, name + "_given")] += 1
                    summary[(level, name + "_ok")] += int(bool(entry[name + "_ok"]))
            results.append(entry)
        table = []
        for side in ("Mua vào", "Bán ra"):
            for colour in ("Xanh", "Vàng", "Đỏ"):
                level = colour + " · " + side
                if not summary[(level, "n")]:
                    continue
                table.append({"level": level, "rows": summary[(level, "n")], "matched": summary[(level, "matched")], "unmatched": summary[(level, "unmatched")],
                              "account_ok": summary[(level, "account_ok")], "partner_ok": summary[(level, "partner_ok")], "counterparty_given": summary[(level, "counterparty_given")], "counterparty_ok": summary[(level, "counterparty_ok")],
                              "project_given": summary[(level, "project_given")], "project_ok": summary[(level, "project_ok")]})
        return {"run_id": run_id, "rows": results, "summary": table, "answer_source": answer_source, "kind": "INVOICE",
                "names": {code: name for (kind, code), name in names.items() if kind == "COUNTERPARTY"}}

    def _answer_journals(self, cutoff):
        """Vouchers that grade a scoring run, and where they come from.

        Normally the kho's own posted journals.  A trial kho whose Junsky
        ledger was physically cut at the learning date names the full ledger
        workbook in ``settings.answer_ledger``; it is read here only, never
        stored, so nothing after the cut can become knowledge.
        """
        path = str(self._settings().get("answer_ledger") or "").strip()
        if not path:
            bundle = self._bundle(cutoff)
            return [row for row in bundle["documents"] if row["kind"] == "JOURNAL" and row.get("source_status") in self.store.config.posted_journal_statuses], "Sổ Junsky trong kho"
        from ..nguon.that import read_journal_rows
        ledger = Path(path)
        if not ledger.is_file():
            raise DataError("QUICK_ANSWER_LEDGER", "Không thấy file sổ Junsky đầy đủ để chấm: " + ledger.name)
        journals = []
        for row in read_journal_rows(ledger):
            key = "|".join(str(row.get(name) or "") for name in ("unit_code", "business_date", "voucher_number", "book"))
            journals.append({**row, "id": "DAP_AN:" + key,
                             "lines": [{"account": line["account"], "debit_minor": int(line["debit"]), "credit_minor": int(line["credit"])} for line in row["lines"]]})
        return journals, "File " + ledger.name

    def write_score_workbook(self, path: Path, scored: dict):
        from openpyxl.styles import Font, PatternFill
        invoice = scored.get("kind") == "INVOICE"
        book = Workbook(); sheet = book.active; sheet.title = "TONG HOP"
        bold, fill = Font(name="Arial", bold=True), PatternFill("solid", fgColor="DDE7F5")
        head = ["Mức", "Số dòng", "Ghép được chứng từ", "Không ghép", "TK chi phí/doanh thu đúng" if invoice else "TK đối ứng đúng"]
        head += (["TK công nợ đúng"] if invoice else []) + ["Có đối tượng", "Đối tượng đúng", "Có dự án", "Dự án đúng"]
        sheet.append(head)
        for cell in sheet[1]:
            cell.font = bold; cell.fill = fill
        for item in scored["summary"]:
            sheet.append([item["level"], item["rows"], item["matched"], item["unmatched"], item["account_ok"]] + ([item.get("partner_ok", 0)] if invoice else [])
                         + [item["counterparty_given"], item["counterparty_ok"], item["project_given"], item["project_ok"]])
        total_row = sheet.max_row + 1
        letters = "BCDEFGHIJ" if invoice else "BCDEFGHI"
        sheet.append(["Tổng"] + [f"=SUM({letter}2:{letter}{total_row - 1})" for letter in letters])
        sheet.cell(total_row, 1).font = bold
        if scored.get("answer_source"):
            sheet.append([])
            sheet.append(["Đáp án lấy từ", scored["answer_source"]])
        if invoice:
            sheet.append(["Cách ghép", "Hóa đơn ↔ chứng từ Junsky theo tiền chưa thuế + tiền thuế, 20 ngày trước đến 75 ngày sau ngày hóa đơn"])
        detail = book.create_sheet("CHI TIET")
        columns = ["Ngày", "Mua vào/Bán ra" if invoice else "Thu/Chi", "Số tiền (VND)", "Diễn giải", "Mức", "Trạng thái", "Máy: TK đối ứng", "Junsky: TK đối ứng", "TK đúng?"]
        if invoice:
            columns += ["Máy: TK công nợ", "Junsky: TK công nợ", "TK công nợ đúng?"]
        columns += ["Máy: đối tượng", "Junsky: đối tượng", "Đối tượng đúng?", "Máy: dự án", "Junsky: dự án", "Dự án đúng?", "Số CT Junsky", "Nhiều dòng = 1 CT", "Ghi chú"]
        detail.append(columns)
        for cell in detail[1]:
            cell.font = bold; cell.fill = fill
        yes = lambda value: "" if value is None else ("Đúng" if value else "Sai")
        for row in scored["rows"]:
            kind = row["level"].split(" · ")[-1] if invoice else ("Thu" if row["amount_minor"] > 0 else "Chi")
            values = [_vn_date(row["business_date"]), kind, abs(row["amount_minor"]), row["description"], row["level"], row["state"],
                      row["proposed"], row["actual"], yes(row["account_ok"])]
            if invoice:
                values += [row.get("partner", ""), row.get("actual_partner", ""), yes(row.get("partner_ok"))]
            values += [row["counterparty"], row["actual_counterparty"], yes(row["counterparty_ok"]),
                       row["project"], row["actual_project"], yes(row["project_ok"]), row["voucher"], "Có" if row.get("group") else "", row.get("note", "")]
            detail.append(values)
        detail_widths = (12, 10, 16, 50, 14, 10, 16, 16, 9) + ((14, 14, 12) if invoice else ()) + (18, 18, 13, 12, 12, 10, 16, 10, 30)
        for ws, widths in ((sheet, (14, 10, 18, 12, 16, 14, 12, 14, 10, 12)), (detail, detail_widths)):
            for index, width in enumerate(widths, 1):
                ws.column_dimensions[ws.cell(1, index).column_letter].width = width
            for row in ws.iter_rows():
                for cell in row:
                    if not cell.font.b:
                        cell.font = Font(name="Arial", size=10)
        for row in detail.iter_rows(min_row=2):
            row[2].number_format = "#,##0"
        path.parent.mkdir(parents=True, exist_ok=True)
        book.save(path)
        return path
