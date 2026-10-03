"""V4 human-owned knowledge workbooks.

Excel remains readable and is never an approval authority by itself.  Importing
source workbooks creates pending versions only; importing a reviewed workbook
creates review *requests*, never an APPROVE event.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

from ..ha_tang.primitives import DataError, canonical_json, date_iso, instant_utc, sha256, text_id
from ..ha_tang.runtime import artifact, log, transaction, uid
from ..ha_tang.store import write_immutable
from .service import Knowledge


VISIBLE_HEADERS = ["ID", "Loại", "Mã", "Tên / biểu thức", "TK", "Đối tượng", "Dự án", "Số gặp", "Số đúng", "Hiệu lực từ", "Hiệu lực đến", "Trạng thái", "Anh duyệt", "Ghi chú", "quyet_dinh", "ghi_chu"]
SHEETS = ("NHOM", "TU_KHOA", "KHOA_CUNG", "MAU_DINH_KHOAN", "NGOAI_LE", "CHO_DUYET", "NHAT_KY", "KY_THUAT_AN")


def _safe(value):
    """Convert workbook scalar types before immutable JSON hashing."""
    from datetime import datetime
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            return None
        return str(value)
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    return value


def _value(row: dict, *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _period(value: str, fallback: str) -> str:
    value = str(value or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}", value):
        return value + "-01"
    if re.fullmatch(r"\d{2}/\d{4}", value):
        month, year = value.split("/")
        return f"{year}-{month}-01"
    try:
        return date_iso(value[:10])
    except DataError:
        return fallback


def _rows(path: Path, sheet_name: str) -> list[dict]:
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet_name not in wb.sheetnames:
            return []
        ws = wb[sheet_name]
        raw = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()
    header_index = next((i for i, row in enumerate(raw) if sum(value not in (None, "") for value in row) >= 2), None)
    if header_index is None:
        return []
    headers = [str(value or "").strip() for value in raw[header_index]]
    result = []
    for values in raw[header_index + 1:]:
        row = {headers[index]: values[index] if index < len(values) else None for index in range(len(headers)) if headers[index]}
        if any(value not in (None, "") for value in row.values()):
            result.append(row)
    return result


class HumanKnowledgeWorkbook:
    def __init__(self, store):
        self.store, self.db, self.knowledge = store, store.conn, Knowledge(store)

    def import_sources(self, paths: list[Path], actor: str, at: str, catalog_valid_from: str | None = None) -> dict:
        """Import source workbook rows as pending knowledge with row provenance."""
        at = instant_utc(at)
        catalog_valid_from = date_iso(catalog_valid_from or self.store.config.catalog_valid_from)
        source_rows, items, skipped = [], [], []
        for path in map(Path, paths):
            if not path.is_file() or path.suffix.casefold() != ".xlsx":
                raise DataError("KNOWLEDGE_SOURCE_FILE", "Nguồn tri thức cần là workbook .xlsx hiện có.")
            raw = path.read_bytes(); digest = sha256(raw)
            # Bootstrap may run again whenever the local application starts.
            # The same immutable workbook is evidence already in the store;
            # re-staging it with a later `known_at` would create overlapping
            # PENDING versions of every logical key.  Reuse the existing
            # import batch instead.
            if self.db.execute("SELECT 1 FROM knowledge_import_batches WHERE artifact_hash=? LIMIT 1", (digest,)).fetchone():
                skipped.append({"file": path.name, "sheet": "*", "row": 0, "reason": "Workbook cùng hash đã nạp; không tạo phiên bản trùng."})
                continue
            if "TU-DIEN" in path.name.upper():
                parsed = self._dictionary_items(path, at)
            elif "BO-QUY-TAC" in path.name.upper():
                parsed = self._rulebook_items(path, at, catalog_valid_from)
            elif "HOA-DON-CAY" in path.name.upper():
                parsed = self._invoice_tree_items(path, at, catalog_valid_from)
            else:
                raise DataError("KNOWLEDGE_SOURCE_NAME", "Chỉ nhận TU-DIEN, BO-QUY-TAC hoặc HOA-DON-CAY đã khảo sát.")
            source_rows.extend({"file": path.name, "sheet": source["sheet"], "rows": source["rows"]} for source in parsed[1])
            items.extend(parsed[0]); skipped.extend(parsed[2])
            # Keep each supplied workbook immutable before any DB change.
            with transaction(self.store):
                artifact(self.store, raw)
                self.db.execute("INSERT OR IGNORE INTO knowledge_import_batches VALUES (?,?,?,?,?,?)", (uid(), digest, canonical_json({"file": path.name}), at, text_id(actor), at))
        identifiers = []
        if items:
            identifiers = self.knowledge.stage_many(items, actor, at)
            with transaction(self.store):
                log(self.store, "M2", "IMPORT_KNOWLEDGE_PENDING", None, actor, at, {"versions": len(identifiers), "sources": source_rows, "skipped": len(skipped)})
        return {"imported": len(identifiers), "pending": len(identifiers), "approved": 0, "sources": source_rows,
                "skipped": skipped, "actor_can_approve": False, "meaning": "Mọi hàng đều chờ duyệt; CFO_NTD chỉ có hiệu lực khi Anh ra lệnh duyệt riêng."}

    def _item(self, category: str, key: str, payload: dict, at: str, file: Path, sheet: str, row: int, *, valid_from: str | None = None, valid_to: str | None = None) -> dict:
        start = valid_from or at[:10]
        evidence = [canonical_json({"file": file.name, "sheet": sheet, "row": row, "known_at_basis": "ngày nhập V4; ngày lập nguồn chưa có timestamp đầy đủ"})]
        return {"category": category, "logical_key": f"{file.stem}:{sheet}:{key}:{row}", "payload": _safe(payload), "valid_from": start,
                "valid_to": valid_to, "known_at": at, "evidence": evidence}

    def _dictionary_items(self, path: Path, at: str):
        items, sources, skipped = [], [], []
        for sheet, category, key_column, expression_column in (("1 · NHÓM", "GROUP", "Mã", "Tên nhóm"), ("2 · TỪ KHÓA", "KEYWORD", "Mã nhóm", "Từ khóa (regex)"), ("3 · NGOẠI LỆ", "EXCEPTION", "Mã chứng từ", "Tên / nội dung"), ("3B · KHÓA CỨNG", "HARD_KEY", "Loại khóa", "Giá trị khóa")):
            values = _rows(path, sheet); sources.append({"sheet": sheet, "rows": len(values)})
            for ordinal, row in enumerate(values, 2):
                key, expression = _value(row, key_column), _value(row, expression_column)
                if not key or not expression or expression.startswith("("):
                    skipped.append({"file": path.name, "sheet": sheet, "row": ordinal, "reason": "Thiếu khóa/biểu thức hoặc dòng ví dụ"}); continue
                payload = {"source_contract": "V4", "source_status": _value(row, "Trạng thái", "Đánh giá tự động"), "group": _value(row, "Mã nhóm", "Nhóm"),
                           "name": _value(row, "Tên nhóm"), "expression": expression, "metrics": {"matched_in_group": _value(row, "Khớp trong nhóm"),
                           "only_caught": _value(row, "Chỉ mình nó bắt"), "outside_group": _value(row, "Khớp ngoài nhóm")}, "source_row": row}
                start = _period(_value(row, "Kỳ thêm", "Kỳ tạo"), at[:10])
                end = at[:10] if _value(row, "Trạng thái") == "NGỦ" and start < at[:10] else None
                items.append(self._item(category, key, payload, at, path, sheet, ordinal, valid_from=start, valid_to=end))
        return items, sources, skipped

    def _rulebook_items(self, path: Path, at: str, catalog_valid_from: str):
        items, sources, skipped = [], [], []
        values = _rows(path, "Quy tắc"); sources.append({"sheet": "Quy tắc", "rows": len(values)})
        for ordinal, row in enumerate(values, 2):
            key = _value(row, "ma_quy_tac")
            if not key:
                skipped.append({"file": path.name, "sheet": "Quy tắc", "row": ordinal, "reason": "Thiếu ma_quy_tac"}); continue
            direction = {"CHI": "OUT", "THU": "IN"}.get(_value(row, "chieu"))
            trigger = self._trigger(row)
            tier = next((int(value) for value in re.findall(r"[1-5]", _value(row, "bac"))), None)
            target, party, project = _value(row, "tk_doi_ung"), _value(row, "ma_doi_tuong"), _value(row, "ma_du_an")
            start = _period(_value(row, "lan_dau"), at[:10]); expiry = _value(row, "han_dung")
            end = _period(expiry, at[:10]) if expiry else None
            if end is not None:
                from .matching import expiry_exclusive
                end = expiry_exclusive(end)
            if direction and trigger and tier:
                fields = {"counterparty": party or None, "project": project or None}
                if "|" not in target:
                    fields["debit_account" if direction == "OUT" else "credit_account"] = target or None
                payload = {"contract_version": 2, "template_id": key, "direction": direction, "partition": "PLHN:PAYMENT", "tier": tier,
                           "order": ordinal, "trigger": trigger, "needs_open_item": False, "required_fields": [], "fields": fields,
                           "source_status": _value(row, "trang_thai"), "source_account_raw": target, "source_row": row}
                if "|" in target:
                    payload["requires_multiline_review"] = True
                items.append(self._item("POLICY", key, payload, at, path, "Quy tắc", ordinal, valid_from=start, valid_to=end))
            else:
                items.append(self._item("SOURCE_POLICY_ROW", key, {"source_contract": "V4", "source_status": _value(row, "trang_thai"), "source_row": row}, at, path, "Quy tắc", ordinal, valid_from=start, valid_to=end))
        mapping = _rows(path, "Ánh xạ STK"); sources.append({"sheet": "Ánh xạ STK", "rows": len(mapping)})
        for ordinal, row in enumerate(mapping, 2):
            account, party = _value(row, "stk_doi_ung"), _value(row, "ma_doi_tuong")
            if account and party:
                payload = {"kind": "IDENTIFIER", "code": "BANK_ACCOUNT:" + account, "identifier_type": "BANK_ACCOUNT", "value": account,
                           "counterparty": party, "verified": False, "source_status": _value(row, "trang_thai"), "source_row": row}
                items.append(self._item("CATALOG", account, payload, at, path, "Ánh xạ STK", ordinal, valid_from=catalog_valid_from))
        for sheet, kind in (("DM Đối tượng", "COUNTERPARTY"), ("DM Tài khoản", "ACCOUNT"), ("DM Khoản mục CP", "EXPENSE"), ("DM Dự án", "PROJECT"), ("DM Trung tâm CP", "COST_CENTER")):
            values = _rows(path, sheet); sources.append({"sheet": sheet, "rows": len(values)})
            for ordinal, row in enumerate(values, 2):
                code, name = _value(row, "ma"), _value(row, "ten")
                if code and name:
                    items.append(self._item("CATALOG", code, {"kind": kind, "code": code, "name": name, "source_status": "PENDING_IMPORT", "source_row": row}, at, path, sheet, ordinal, valid_from=catalog_valid_from))
        return items, sources, skipped

    @staticmethod
    def _trigger(row: dict) -> dict | None:
        key, keyword, name = _value(row, "stk_doi_ung"), _value(row, "tu_khoa"), _value(row, "ten_doi_ung")
        if key:
            return {"mode": "KEY_REGEX" if keyword else "KEY", "key_type": "BANK_ACCOUNT", "key_value": key, **({"regex": keyword} if keyword else {})}
        if name:
            return {"mode": "KEY_REGEX" if keyword else "KEY", "key_type": "COUNTERPARTY_NAME", "key_value": name, **({"regex": keyword, "name_normalization": "legacy-chung-v1"} if keyword else {"name_normalization": "legacy-chung-v1"})}
        if keyword:
            return {"mode": "REGEX", "regex": keyword}
        return None

    def _invoice_tree_items(self, path: Path, at: str, catalog_valid_from: str):
        items, sources, skipped = [], [], []
        for sheet in ("1 · Cây MUA VÀO", "2 · Cây BÁN RA", "4 · Khoản mục phí Junsky", "6 · Nhà cung cấp — khóa cứng"):
            values = _rows(path, sheet); sources.append({"sheet": sheet, "rows": len(values)})
            for ordinal, row in enumerate(values, 2):
                key = _value(row, "Mã nhánh", "Mã", "MST")
                if not key:
                    continue
                category = "HARD_KEY" if sheet.startswith("6") else "INVOICE_TREE"
                payload = {"source_contract": "V4", "source_row": row, "source_key": key,
                           "name": _value(row, "Nhánh", "Tên khoản mục phí (Junsky)", "Tên nhà cung cấp"),
                            "approved_hint": _value(row, "Anh duyệt làm khóa cứng?", "Nhóm G tương ứng (đề xuất)")}
                items.append(self._item(category, key, payload, at, path, sheet, ordinal, valid_from=catalog_valid_from if category == "INVOICE_TREE" else None))
        return items, sources, skipped

    def export_human_workbook(self, path: Path, actor: str, at: str) -> dict:
        at = instant_utc(at)
        records = [dict(row) for row in self.db.execute("SELECT * FROM knowledge_versions ORDER BY category,logical_key,revision")]
        rows = [self._visible(row) for row in records]
        baseline = {row["ID"]: sha256(canonical_json(row).encode()) for row in rows}
        workbook_id = uid()
        wb = Workbook(); wb.remove(wb.active)
        for name in SHEETS:
            ws = wb.create_sheet(name)
            if name == "KY_THUAT_AN":
                ws.sheet_state = "hidden"; ws.append(["id", "payload_json", "baseline_hash"])
            else:
                ws.append(VISIBLE_HEADERS); ws.freeze_panes = "A2"
                for cell in ws[1]:
                    cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="1F4E78")
        mapping = {"GROUP": "NHOM", "KEYWORD": "TU_KHOA", "HARD_KEY": "KHOA_CUNG", "POLICY": "MAU_DINH_KHOAN", "EXCEPTION": "NGOAI_LE"}
        for row in rows:
            sheet = mapping.get(row["Loại"], "CHO_DUYET")
            wb[sheet].append([row.get(header, "") for header in VISIBLE_HEADERS])
            wb["KY_THUAT_AN"].append([row["ID"], row["payload_json"], baseline[row["ID"]]])
        for sheet in SHEETS:
            ws = wb[sheet]
            if sheet != "KY_THUAT_AN":
                for column in ws.columns:
                    letter = column[0].column_letter; ws.column_dimensions[letter].width = min(42, max(12, max(len(str(cell.value or "")) for cell in column) + 2))
        raw = self._bytes(wb)
        with transaction(self.store):
            digest = artifact(self.store, raw)
            self.db.execute("INSERT INTO knowledge_workbooks VALUES (?,?,?,?,?)", (workbook_id, sha256(canonical_json(baseline).encode()), digest, at, text_id(actor)))
            log(self.store, "M2", "EXPORT_KNOWLEDGE_HUMAN", workbook_id, actor, at, {"rows": len(rows), "artifact": digest})
        write_immutable(Path(path), raw)
        return {"workbook_id": workbook_id, "path": str(path), "rows": len(rows), "approved": 0}

    def import_review_requests(self, path: Path, actor: str, at: str) -> dict:
        raw, at = Path(path).read_bytes(), instant_utc(at)
        wb = load_workbook(filename=Path(path), read_only=True, data_only=False)
        try:
            if set(wb.sheetnames) != set(SHEETS):
                raise DataError("KNOWLEDGE_WORKBOOK_SHEETS", "Workbook tri thức sai tập sheet.")
            technical = wb["KY_THUAT_AN"]
            values = list(technical.iter_rows(values_only=True))
            if not values or [str(value) for value in values[0]] != ["id", "payload_json", "baseline_hash"]:
                raise DataError("KNOWLEDGE_WORKBOOK_TECHNICAL", "Thiếu sheet kỹ thuật/baseline.")
            baseline = {str(row[0]): str(row[2]) for row in values[1:] if row[0]}
            row = self.db.execute("SELECT * FROM knowledge_workbooks WHERE baseline_hash=?", (sha256(canonical_json(baseline).encode()),)).fetchone()
            if not row:
                raise DataError("STALE_KNOWLEDGE_WORKBOOK", "Workbook cũ hoặc sheet kỹ thuật bị sửa.")
            decisions = []
            for name in SHEETS[:-1]:
                values = list(wb[name].iter_rows(values_only=True))
                if not values or list(values[0]) != VISIBLE_HEADERS:
                    raise DataError("KNOWLEDGE_WORKBOOK_COLUMNS", "Cột workbook tri thức bị sửa.")
                for row_values in values[1:]:
                    view = dict(zip(VISIBLE_HEADERS, row_values))
                    version_id = str(view.get("ID") or "")
                    if version_id:
                        if version_id not in baseline:
                            raise DataError("KNOWLEDGE_WORKBOOK_ROW", "Dòng workbook không có baseline.")
                        current = self.db.execute("SELECT * FROM knowledge_versions WHERE id=?", (version_id,)).fetchone()
                        if not current:
                            raise DataError("STALE_KNOWLEDGE_WORKBOOK", "Phiên bản tri thức trong workbook không còn tồn tại.")
                        expected = self._visible(dict(current))
                        for field in VISIBLE_HEADERS:
                            if field in {"Anh duyệt", "Ghi chú", "quyet_dinh", "ghi_chu"}:
                                continue
                            if str(view.get(field) or "") != str(expected.get(field) or ""):
                                raise DataError("KNOWLEDGE_WORKBOOK_IMMUTABLE", "Chỉ cột Anh duyệt và Ghi chú được sửa trong workbook.")
                    decision = str(view.get("Anh duyệt") or "").strip().upper()
                    if decision in {"YEU CAU DUYET", "YÊU CẦU DUYỆT", "YEU CAU THU HOI", "YÊU CẦU THU HỒI"}:
                        if str(view["ID"]) not in baseline:
                            raise DataError("KNOWLEDGE_WORKBOOK_ROW", "Dòng mới không có baseline không được nhập.")
                        action = "APPROVE_REQUEST" if "DUYET" in decision.replace("Ệ", "E") else "REVOKE_REQUEST"
                        decisions.append((str(view["ID"]), action, str(view.get("Ghi chú") or "")))
                    elif decision:
                        raise DataError("KNOWLEDGE_DECISION", "Cột Anh duyệt chỉ nhận YÊU CẦU DUYỆT hoặc YÊU CẦU THU HỒI.")
            with transaction(self.store):
                digest = artifact(self.store, raw)
                requests = []
                for version_id, action, note in decisions:
                    identifier = uid()
                    self.db.execute("INSERT OR IGNORE INTO knowledge_review_requests VALUES (?,?,?,?,?,?,?)", (identifier, row["id"], version_id, action, note, at, text_id(actor)))
                    if self.db.execute("SELECT changes()").fetchone()[0]:
                        requests.append(identifier)
                log(self.store, "M2", "IMPORT_KNOWLEDGE_REVIEW_REQUEST", row["id"], actor, at, {"requests": requests, "artifact": digest})
            return {"requests": requests, "events": len(requests), "approved": 0, "meaning": "Đây là yêu cầu duyệt; không tự tạo APPROVE event."}
        finally:
            wb.close()

    @staticmethod
    def _bytes(wb: Workbook) -> bytes:
        from io import BytesIO
        output = BytesIO(); wb.save(output); wb.close(); return output.getvalue()

    @staticmethod
    def _visible(row: dict) -> dict:
        payload = json.loads(row["payload_json"])
        fields = payload.get("fields", {})
        metrics = payload.get("metrics", {})
        return {"ID": row["id"], "Loại": row["category"], "Mã": row["logical_key"], "Tên / biểu thức": payload.get("expression") or payload.get("name") or payload.get("template_id") or "",
                "TK": fields.get("debit_account") or fields.get("credit_account") or payload.get("source_account_raw") or "", "Đối tượng": fields.get("counterparty") or payload.get("group") or "",
                "Dự án": fields.get("project") or "", "Số gặp": payload.get("source_row", {}).get("so_lan_gap") or metrics.get("matched_in_group") or "",
                "Số đúng": payload.get("source_row", {}).get("so_lan_dung") or metrics.get("only_caught") or "", "Hiệu lực từ": row["valid_from"], "Hiệu lực đến": row["valid_to"] or "",
                "Trạng thái": payload.get("source_status") or "PENDING", "Anh duyệt": "", "Ghi chú": "", "quyet_dinh": "", "ghi_chu": "", "payload_json": row["payload_json"]}

    def apply_human_decisions(self, path: Path, actor: str, at: str, *, sheets: set[str] | None = None, dry_run: bool = False) -> dict:
        """Apply explicit APPROVE/REJECT cells from a workbook exported by this service.

        The workbook carries only the human decision.  Its hidden identifiers and
        immutable visible values are still checked against the DB before any event.
        """
        at = instant_utc(at)
        workbook = load_workbook(filename=Path(path), read_only=True, data_only=False)
        try:
            if set(workbook.sheetnames) != set(SHEETS):
                raise DataError("KNOWLEDGE_WORKBOOK_SHEETS", "Workbook tri thức sai tập sheet.")
            technical_values = list(workbook["KY_THUAT_AN"].iter_rows(values_only=True))
            if not technical_values or [str(value) for value in technical_values[0]] != ["id", "payload_json", "baseline_hash"]:
                raise DataError("KNOWLEDGE_WORKBOOK_TECHNICAL", "Thiếu sheet kỹ thuật/baseline.")
            baseline = {str(row[0]): str(row[2]) for row in technical_values[1:] if row[0]}
            known = self.db.execute("SELECT id FROM knowledge_workbooks WHERE baseline_hash=?", (sha256(canonical_json(baseline).encode()),)).fetchone()
            if not known:
                raise DataError("STALE_KNOWLEDGE_WORKBOOK", "Workbook cũ hoặc sheet kỹ thuật bị sửa.")
            allowed = set(sheets or {"NHOM", "TU_KHOA", "KHOA_CUNG", "MAU_DINH_KHOAN", "NGOAI_LE"})
            if not allowed <= set(SHEETS):
                raise DataError("KNOWLEDGE_WORKBOOK_SHEETS", "--chi-nhom có sheet tri thức không hợp lệ.")
            operations: list[tuple[str, str, str]] = []
            counters = {name: {"approve": 0, "reject": 0, "skip": 0} for name in SHEETS[:-1]}
            for name in SHEETS[:-1]:
                values = list(workbook[name].iter_rows(values_only=True))
                if not values or list(values[0]) != VISIBLE_HEADERS:
                    raise DataError("KNOWLEDGE_WORKBOOK_COLUMNS", "Cột workbook tri thức bị sửa.")
                for row_values in values[1:]:
                    view = dict(zip(VISIBLE_HEADERS, row_values))
                    identifier = str(view.get("ID") or "")
                    if not identifier:
                        continue
                    if identifier not in baseline:
                        raise DataError("KNOWLEDGE_WORKBOOK_ROW", "Dòng workbook không có baseline.")
                    current = self.db.execute("SELECT * FROM knowledge_versions WHERE id=?", (identifier,)).fetchone()
                    if not current:
                        raise DataError("STALE_KNOWLEDGE_WORKBOOK", "Phiên bản tri thức trong workbook không còn tồn tại.")
                    expected = self._visible(dict(current))
                    for field in VISIBLE_HEADERS:
                        if field not in {"Anh duyệt", "Ghi chú", "quyet_dinh", "ghi_chu"} and str(view.get(field) or "") != str(expected.get(field) or ""):
                            raise DataError("KNOWLEDGE_WORKBOOK_IMMUTABLE", "Chỉ cột quyết định và ghi chú được sửa trong workbook.")
                    decision = str(view.get("quyet_dinh") or "").strip().upper()
                    note = str(view.get("ghi_chu") or "").strip()
                    if not decision:
                        counters[name]["skip"] += 1
                        continue
                    if name not in allowed:
                        raise DataError("KNOWLEDGE_SHEET_NOT_SELECTED", "Workbook có quyết định ngoài --chi-nhom.")
                    if decision not in {"APPROVE", "REJECT"}:
                        raise DataError("KNOWLEDGE_DECISION", "quyet_dinh chỉ nhận APPROVE, REJECT hoặc để trống.")
                    if decision == "REJECT" and not note:
                        raise DataError("KNOWLEDGE_REJECT_REASON", "REJECT cần ghi_chu để lưu lý do.")
                    operations.append((identifier, decision, note))
                    counters[name]["approve" if decision == "APPROVE" else "reject"] += 1
            if not dry_run:
                for identifier, decision, note in operations:
                    if decision == "APPROVE":
                        self.knowledge.approve(identifier, actor, at)
                    else:
                        self.knowledge.revoke(identifier, actor, at, note, allow_pending=True)
            return {"actor": text_id(actor), "at": at, "dry_run": dry_run, "sheets": counters,
                    "approved": sum(value["approve"] for value in counters.values()), "rejected": sum(value["reject"] for value in counters.values()),
                    "skipped": sum(value["skip"] for value in counters.values())}
        finally:
            workbook.close()
