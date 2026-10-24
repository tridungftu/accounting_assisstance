"""Offline readers for declared PLHN source exports.

The adapter never changes a supplied source.  It translates an observed layout
to the internal contract, preserving parser faults as row quarantine candidates
instead of turning a recoverable source defect into a rejected whole batch.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from openpyxl import load_workbook

from ..ha_tang.config import Config
from ..ha_tang.primitives import DataError, instant_utc, normalize_text
from .fixture import Batch, Issue, Record, _manifest, _record, normalized_invoice_number


@dataclass(frozen=True)
class SourceMetadata:
    as_of: str
    exported_at: str
    known_at_basis: str
    coverage_from: str
    coverage_to_exclusive: str
    known_at: str | None = None
    snapshot_id: str | None = None
    source_system: str = "PLHN_OFFLINE_EXPORT"
    scope: str = "offline source supplied by operator"
    posting_evidence_complete: bool = False
    scope_open_items_complete: bool = False
    catalog_valid_from: str | None = None

    def manifest(self, config: Config) -> dict:
        known = self.known_at or self.exported_at
        return {"entity_id": config.entity_id, "source_system": self.source_system,
                "as_of": self.as_of, "coverage_from": self.coverage_from,
                "coverage_to_exclusive": self.coverage_to_exclusive, "exported_at": self.exported_at,
                "known_at": known, "known_at_basis": self.known_at_basis,
                "scope": self.scope, "snapshot_id": self.snapshot_id or ("DECLARED_" + self.as_of.replace("-", "")),
                "posting_evidence_complete": self.posting_evidence_complete,
                "scope_open_items_complete": self.scope_open_items_complete}


def _text(value: Any) -> str:
    """Make spreadsheet scalar values textual without preserving ``123.0`` IDs."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return str(value).strip()


def _norm(value: Any) -> str:
    return normalize_text(_text(value))


def _date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raw = _text(value)
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw[:10], pattern).date().isoformat()
        except ValueError:
            pass
    raise DataError("SOURCE_DATE", "Ngày nguồn không có định dạng được khai báo.")


def _minor(value: Any, *, fractional_code: str = "INEXACT_MONEY") -> str:
    """Return VND integer text; floats are accepted only when exactly integral."""
    if value is None or _text(value) in {"", "-"}:
        return "0"
    try:
        if isinstance(value, float):
            decimal = Decimal(repr(value))
        elif isinstance(value, Decimal):
            decimal = value
        elif isinstance(value, int) and not isinstance(value, bool):
            decimal = Decimal(value)
        else:
            raw = _text(value).replace("₫", "").replace("VND", "").replace("vnd", "").replace(" ", "")
            decimal = Decimal(raw.replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise DataError("MONEY_FORMAT", "Tiền nguồn không đúng định dạng số.") from exc
    if decimal != decimal.to_integral_value():
        raise DataError(fractional_code, "Tiền có phần lẻ ngoài VND scale 0.")
    return str(int(decimal))


def _invoice_minor(value: Any) -> tuple[str, bool]:
    """Invoice sources may hold up to six decimal digits; retain VND by rounding."""
    if value is None or _text(value) in {"", "-"}:
        return "0", False
    try:
        raw = _text(value).replace("₫", "").replace("VND", "").replace("vnd", "").replace(",", "").replace(" ", "")
        decimal = Decimal(raw)
    except InvalidOperation as exc:
        raise DataError("MONEY_FORMAT", "Tiền hóa đơn không đúng định dạng số.") from exc
    rounded = decimal.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return str(int(rounded)), decimal != rounded


def _source_instant(value: Any) -> str:
    """Parse source timestamps; an offset-free ISO time is Vietnam local time."""
    raw = _text(value)
    try:
        return instant_utc(raw)
    except DataError:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise DataError("SOURCE_TIME", "Thời điểm nguồn không đúng ISO.") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone(timedelta(hours=7)))
        return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _header_parts(value: Any) -> set[str]:
    raw = _text(value)
    if not raw:
        return set()
    return {_norm(part) for part in raw.replace("\n", " ").split("/") if _text(part)}


def _matches_header(value: Any, candidates: tuple[str, ...]) -> bool:
    parts = _header_parts(value)
    whole = _norm(value)
    wanted = {_norm(candidate) for candidate in candidates}
    return bool(parts & wanted or whole in wanted)


def _sheet_rows(path: Path, *, sheet: str | None = None, expected: tuple[str, ...] = ()) -> tuple[list[str], list[list[Any]]]:
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[sheet] if sheet else wb[wb.sheetnames[0]]
        rows = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()
    if not rows:
        raise DataError("EMPTY_WORKBOOK", "Workbook không có dữ liệu.")
    wanted = {_norm(item) for item in expected}
    scored = [(sum(1 for value in row if _norm(value) in wanted), index) for index, row in enumerate(rows)] if wanted else []
    header_index = next((index for score, index in scored if score >= 2), None)
    if header_index is None:
        header_index = next((i for i, row in enumerate(rows) if sum(_text(value) != "" for value in row) >= 2), None)
    if header_index is None:
        raise DataError("SOURCE_HEADER", "Không tìm thấy dòng tiêu đề workbook.")
    headers = [_text(value) for value in rows[header_index]]
    return headers, [list(row) for row in rows[header_index + 1:] if any(_text(value) for value in row)]


def _mapped_rows(path: Path, aliases: dict[str, tuple[str, ...]], *, sheet: str | None = None) -> list[dict[str, Any]]:
    expected = tuple(candidate for values in aliases.values() for candidate in values)
    headers, rows = _sheet_rows(path, sheet=sheet, expected=expected)
    columns: dict[str, int] = {}
    for name, candidates in aliases.items():
        index = next((i for i, header in enumerate(headers) if _matches_header(header, candidates)), None)
        if index is not None:
            columns[name] = index
    return [{name: row[index] if index < len(row) else None for name, index in columns.items()} for row in rows]


def _load_external(path: Path, name: str):
    if not path.is_file():
        raise DataError("REUSE_SCRIPT_MISSING", f"Thiếu script tái sử dụng {path.name}.")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DataError("REUSE_SCRIPT_LOAD", f"Không thể nạp script {path.name}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ThatAdapter:
    """Read one declared real source without making it a fixture."""

    version = "that-source-v9b"

    def __init__(self, source: str, source_path: Path, metadata: SourceMetadata, *, reuse_root: Path | None = None,
                 lock_periods: tuple[tuple[str, str, str], ...] = (), journal_paths: tuple[Path, ...] = ()):
        if source not in {"sao_ke", "hoa_don", "bang_ke", "base", "junsky"}:
            raise DataError("SOURCE_KIND", "Nguồn that chỉ nhận sao_ke, hoa_don, bang_ke, base hoặc junsky.")
        self.source, self.source_path, self.metadata = source, Path(source_path), metadata
        self.reuse_root = Path(reuse_root) if reuse_root else None
        self.lock_periods = lock_periods
        self.journal_paths = tuple(Path(path) for path in journal_paths)

    def read(self, _content: bytes, config: Config) -> Batch:
        if config.environment != "that":
            raise DataError("THAT_REQUIRED", "Bộ đọc nguồn thật chỉ dùng với environment=that.")
        manifest, issues = _manifest(self.metadata.manifest(config), config)
        source, rows, reader_issues, controls = self._rows(config)
        if self.source == "junsky" and config.journal_history_extend_coverage:
            journal_dates = sorted(row.get("business_date") for row in rows if row.get("kind") == "JOURNAL" and row.get("business_date"))
            if journal_dates and journal_dates[0] < manifest["coverage_from"]:
                manifest["declared_coverage_from"] = manifest["coverage_from"]
                manifest["coverage_from"] = journal_dates[0]
                reader_issues.append(Issue("JOURNAL_COVERAGE_EXTENDED", "Đã mở coverage về ngày sổ lịch sử sớm nhất; giữ coverage khai báo để truy nguyên.", "$.manifest", "WARNING"))
        if self.source == "base" and self.metadata.known_at is None:
            fetched = sorted({_text(row.get("fetched_at")) for row in rows if isinstance(row, dict) and _text(row.get("fetched_at"))})
            if fetched:
                manifest["known_at"] = max(_source_instant(value) for value in fetched)
                manifest["known_at_basis"] = "max fetched_at of request records; offset-free ISO assumed +07:00"
        issues.extend(reader_issues)
        records: list[Record] = []
        totals: dict[str, int] = {}
        keys: set[tuple[str, str]] = set()
        for ordinal, raw in enumerate(rows):
            if isinstance(raw, dict) and raw.get("__quarantine_issue"):
                detail = raw["__quarantine_issue"]
                issues.append(Issue(detail["code"], detail["message"], f"$.records[{ordinal}]"))
                if raw.get("__quarantine_placeholder"):
                    candidate = {key: value for key, value in raw.items() if not key.startswith("__")}
                    record = _record(candidate, ordinal, source, manifest, config)
                    records.append(record)
                continue
            try:
                record = _record(raw, ordinal, source, manifest, config)
                identity = (record.kind, record.key)
                if identity in keys:
                    issues.append(Issue("DUPLICATE_SOURCE_KEY", "Khóa nghiệp vụ trùng trong nguồn; cách ly bản ghi lặp.", f"$.records[{ordinal}]"))
                    continue
                keys.add(identity)
                records.append(record)
                if record.amount_minor is not None:
                    key = f"{record.kind}/{record.currency}"
                    totals[key] = totals.get(key, 0) + record.amount_minor
            except DataError as exc:
                issues.append(Issue(exc.code, str(exc), f"$.records[{ordinal}]"))
        return Batch(source, manifest, rows, records, totals, issues, controls=controls, allow_record_errors=True)

    def _rows(self, config: Config) -> tuple[str, list[dict], list[Issue], dict]:
        if self.source == "sao_ke":
            rows, issues, controls = self._bank_rows()
            return "sao_ke", rows, issues, controls
        if self.source == "hoa_don":
            rows, issues = self._xml_rows(config)
            return "hoa_don_xml", rows, issues, {}
        if self.source == "bang_ke":
            rows, issues = self._invoice_table_rows(config)
            return "hoa_don_bang_ke", rows, issues, {}
        if self.source == "base":
            return "base", self._base_rows(), [], {}
        rows, issues, controls = self._junsky_rows(config)
        return "junsky_xuat", rows, issues, controls

    def snapshot_paths(self) -> tuple[Path, ...]:
        """Extra files read from the observed Junsky sibling layout.

        Store includes these bytes in the immutable source artifact before the
        reader accesses them, so the journal evidence is not an untracked side
        input merely because the operator supplied the DANH MỤC folder.
        """
        if self.source != "junsky" or self.source_path.name.casefold() != "danh mục":
            return ()
        declared = self.journal_paths or (self.source_path.parent / "dgbList.xlsx", self.source_path.parent / "Sổ NKC có đối ưng.xlsx",
                                          self.source_path.parent / "Ngân Hàng" / "Sổ NKC có đối ưng.xlsx")
        return tuple(path for path in declared if path.is_file())

    # ---- eFAST bank statements -------------------------------------------------

    def _bank_rows(self) -> tuple[list[dict], list[Issue], dict]:
        suffix = self.source_path.suffix.casefold()
        if suffix == ".xls":
            try:
                import xlrd  # type: ignore[import-not-found]
            except ImportError:
                fallback = self.source_path.with_suffix(".xlsx")
                if not fallback.is_file():
                    raise DataError("XLRD_OFFLINE_WHEEL_MISSING", "Không có xlrd==2.0.2 offline và chưa có bản .xlsx cùng tên.")
                rows, issues, controls = self._bank_xlsx_rows(fallback)
                issues.append(Issue("XLRD_OFFLINE_WHEEL_MISSING", "Đã đọc bản .xlsx cùng tên vì thiếu wheel xlrd offline.", "$.source", "WARNING"))
                return rows, issues, controls
            return self._bank_xls_rows(xlrd)
        if suffix == ".pdf":
            return self._bank_pdf_rows(), [], {}
        if suffix != ".xlsx":
            raise DataError("BANK_FILE_TYPE", "Sao kê chỉ nhận .xls, .xlsx hoặc .pdf.")
        return self._bank_xlsx_rows(self.source_path)

    def _bank_xls_rows(self, xlrd) -> tuple[list[dict], list[Issue], dict]:
        book = xlrd.open_workbook(self.source_path)
        names = {_norm(value): value for value in book.sheet_names()}
        name = names.get(_norm("LICH SU GIAO DICH"))
        if not name:
            raise DataError("BANK_SHEET", "Không thấy sheet LICH SU GIAO DICH.")
        sheet = book.sheet_by_name(name)
        values = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
        return self._bank_table(values)

    def _bank_xlsx_rows(self, path: Path) -> tuple[list[dict], list[Issue], dict]:
        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            names = {_norm(value): value for value in wb.sheetnames}
            ws = wb[names.get(_norm("LICH SU GIAO DICH"), wb.sheetnames[0])]
            values = [list(row) for row in ws.iter_rows(values_only=True)]
        finally:
            wb.close()
        return self._bank_table(values)

    def _bank_table(self, values: list[list[Any]]) -> tuple[list[dict], list[Issue], dict]:
        header_index = next((i for i, row in enumerate(values) if any(_norm(value).startswith("STT") for value in row if _text(value))), None)
        if header_index is None:
            raise DataError("BANK_HEADER", "Không tìm thấy dòng STT/No. của sao kê.")
        headers = values[header_index]

        def locate(*names: str) -> int | None:
            return next((i for i, value in enumerate(headers) if _matches_header(value, tuple(names))), None)

        indices = {"date": locate("Ngày hạch toán", "Accounting date", "Ngày giao dịch", "Transaction date", "Ngày"),
                   "description": locate("Mô tả giao dịch", "Transaction description", "Diễn giải"),
                   "debit": locate("Nợ", "Debit", "Ghi nợ"), "credit": locate("Có", "Credit", "Ghi có"),
                   "balance": locate("Số dư TK", "Account Balance", "Số dư"),
                   "reference": locate("Số giao dịch", "Transaction number", "Số chứng từ", "DocsNo"),
                   "mtid_citad": locate("MTID", "CITAD"),
                   "counterparty_account": locate("Số tài khoản đối ứng", "Corresponsive account", "TK thụ hưởng"),
                   "counterparty_name": locate("Tên tài khoản đối ứng", "Corresponsive name", "Tên đối ứng"),
                   "occurred_at": locate("Ngày phát sinh giao dịch", "Transaction date", "Giờ giao dịch")}
        if any(indices[name] is None for name in ("date", "description", "debit", "credit")):
            raise DataError("BANK_COLUMNS", "Sao kê thiếu ngày, diễn giải, Nợ hoặc Có.")
        declared = self._bank_summary(values[:header_index])
        account = self._find_account(values[:header_index])
        result: list[dict] = []
        issues: list[Issue] = []
        credit_rows = debit_rows = credit_total = debit_total = 0
        for source_row in values[header_index + 1:]:
            date_value = source_row[indices["date"]] if indices["date"] is not None and indices["date"] < len(source_row) else None
            try:
                business_date = _date(date_value)
            except DataError:
                continue
            value: dict[str, Any] = {"business_date": business_date, "currency": "VND", "bank": "VIETINBANK", "account": account,
                                     "id_scope": "VIETINBANK_EFAST", "identity_verified": True, "description": _text(source_row[indices["description"]])}
            try:
                debit = int(_minor(source_row[indices["debit"]]))
                credit = int(_minor(source_row[indices["credit"]]))
            except DataError as exc:
                value["__quarantine_issue"] = {"code": exc.code, "message": str(exc)}
                result.append(value)
                continue
            if credit:
                credit_rows += 1; credit_total += credit
            if debit:
                debit_rows += 1; debit_total += debit
            value["amount"] = str(credit - debit)
            if value["amount"] == "0":
                continue
            for name in ("reference", "mtid_citad", "counterparty_account", "counterparty_name", "occurred_at"):
                index = indices[name]
                if index is not None and index < len(source_row) and _text(source_row[index]):
                    value[name] = _text(source_row[index])
            if indices["balance"] is not None and indices["balance"] < len(source_row):
                try:
                    value["balance_after"] = _minor(source_row[indices["balance"]])
                except DataError as exc:
                    value["__quarantine_issue"] = {"code": exc.code, "message": str(exc)}
            result.append(value)
        controls = {"bank": {"credit_rows": credit_rows, "debit_rows": debit_rows, "credit_minor": credit_total, "debit_minor": debit_total, "net_minor": credit_total - debit_total, **declared}}
        def warn_if(key: str, actual: int, code: str) -> None:
            expected = declared.get(key)
            if expected is not None and expected != actual:
                issues.append(Issue(code, "Chỉ số kiểm soát sao kê lệch; lô vẫn được đọc để rà soát.", "$.controls", "WARNING"))
        warn_if("credit_count", credit_rows, "BANK_CONTROL_COUNT_MISMATCH")
        warn_if("debit_count", debit_rows, "BANK_CONTROL_COUNT_MISMATCH")
        warn_if("credit_minor", credit_total, "BANK_CONTROL_VALUE_MISMATCH")
        warn_if("debit_minor", debit_total, "BANK_CONTROL_VALUE_MISMATCH")
        opening, closing = declared.get("opening_minor"), declared.get("closing_minor")
        if opening is not None and closing is not None and opening + credit_total - debit_total != closing:
            issues.append(Issue("BANK_BALANCE_MISMATCH", "Biến động số dư sao kê lệch; cần rà soát nguồn.", "$.controls", "WARNING"))
        period = declared.get("period")
        if period:
            dates = re.findall(r"(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})", period)
            try:
                start, end = _date(dates[0]), _date(dates[-1])
                expected_end = (date.fromisoformat(end) + timedelta(days=1)).isoformat()
                if start < self.metadata.coverage_from or expected_end > self.metadata.coverage_to_exclusive:
                    issues.append(Issue("BANK_COVERAGE_MISMATCH", "Kỳ eFAST vượt coverage khai báo; lô vẫn được đọc để rà soát.", "$.controls", "WARNING"))
            except (DataError, IndexError):
                issues.append(Issue("BANK_PERIOD_UNPARSEABLE", "Không đọc được kỳ kiểm soát eFAST.", "$.controls", "WARNING"))
        return result, issues, controls

    @staticmethod
    def _bank_summary(rows: list[list[Any]]) -> dict[str, Any]:
        labels = {"TONG GIA TRI GHI CO": "credit_minor", "TOTAL CREDITS": "credit_minor", "TONG GIA TRI GHI NO": "debit_minor", "TOTAL DEBITS": "debit_minor",
                  "TONG SO GIAO DICH GHI CO": "credit_count", "TOTAL NUMBER OF CREDIT": "credit_count", "TONG SO GIAO DICH GHI NO": "debit_count", "TOTAL NUMBER OF DEBITS": "debit_count",
                  "SO DU DAU KY": "opening_minor", "OPENING BALANCE": "opening_minor", "SO DU CUOI KY": "closing_minor", "CLOSING BALANCE": "closing_minor",
                  "CHU KY YEU CAU": "period", "FROM DATE- TO DATE": "period"}
        result: dict[str, Any] = {}
        for row in rows:
            for index, cell in enumerate(row):
                label = _norm(cell)
                key = next((target for source, target in labels.items() if source in label), None)
                if key is None or index + 1 >= len(row) or _text(row[index + 1]) == "":
                    continue
                if key == "period":
                    result[key] = _text(row[index + 1])
                else:
                    try:
                        result[key] = int(_minor(row[index + 1]))
                    except DataError:
                        continue
        return result

    @staticmethod
    def _find_account(rows: list[list[Any]]) -> str:
        for row in rows:
            for index, cell in enumerate(row):
                label = _norm(cell)
                if "SO TAI KHOAN" not in label and "ACCOUNT NO" not in label:
                    continue
                if index + 1 >= len(row):
                    continue
                value = _text(row[index + 1]).replace(" ", "")
                if re.fullmatch(r"\d+", value):
                    return value
            # Backward-compatible support for the earlier one-cell synthetic
            # layout.  This expression cannot match eFAST's "Account detail".
            joined = _norm(" ".join(_text(value) for value in row))
            match = re.search(r"(?:tai\s+khoan\s+so|account\s+no\.?)\s*[:：]?\s*(\d+)", joined, re.I)
            if match:
                return match.group(1)
        raise DataError("BANK_ACCOUNT", "Không tìm thấy số tài khoản số trong phần đầu sao kê.")

    def _bank_pdf_rows(self) -> list[dict]:
        if not self.reuse_root:
            raise DataError("PDF_REUSE_ROOT", "Cần khai báo thư mục script bản 1.2 để đọc PDF.")
        module = _load_external(self.reuse_root / "15_doc_pdf_2nam.py", "ktt_reuse_pdf")
        table, header = module.doc_mot_file(self.source_path)
        if table.empty:
            raise DataError("EMPTY_PDF_BANK", "Không đọc được dòng giao dịch từ PDF.")
        if header.get("KHOP_BIEN_DONG") != "OK":
            raise DataError("BANK_BALANCE_MISMATCH", "PDF không qua kiểm soát biến động số dư của script bản 1.2.")
        result = []
        for row in table.to_dict("records"):
            amount = int(round(row.get("so_tien", 0)))
            if amount:
                result.append({"business_date": _date(row.get("ngay")), "currency": "VND", "amount": str(amount), "bank": "VIETINBANK", "account": _text(row.get("so_tk")), "id_scope": "VIETINBANK_PDF", "identity_verified": True, "description": _text(row.get("dien_giai")), "reference": _text(row.get("so_giao_dich")) or None, "mtid_citad": _text(row.get("mtid")) or None, "counterparty_account": _text(row.get("stk_doi_ung")) or None, "counterparty_name": _text(row.get("ten_doi_ung")) or None, "occurred_at": _text(row.get("ngay_phat_sinh")) or None, "balance_after": _minor(row.get("so_du"))})
        return [{key: value for key, value in row.items() if value is not None} for row in result]

    # ---- TCT invoices ----------------------------------------------------------

    def _xml_rows(self, config: Config) -> tuple[list[dict], list[Issue]]:
        if not config.entity_tax_id:
            raise DataError("MISSING_ENTITY_TAX_ID", "Cần [entity].tax_id để lọc hóa đơn nguồn thật.")
        files: list[tuple[bytes, str]] = []
        candidates = [self.source_path] if self.source_path.is_file() else sorted(self.source_path.rglob("*"))
        for path in candidates:
            if path.suffix.casefold() == ".xml":
                files.append((path.read_bytes(), path.name))
            elif path.suffix.casefold() == ".zip":
                with zipfile.ZipFile(path) as archive:
                    files.extend((archive.read(name), f"{path.name}::{name}") for name in archive.namelist() if name.casefold().endswith(".xml"))
        result: list[dict] = []; issues: list[Issue] = []
        for raw, _name in files:
            row, row_issues = parse_invoice_xml(raw, config.entity_tax_id, config.invoice_non_taxable_in_taxable_total, index=len(result))
            issues.extend(row_issues)
            if row is not None:
                result.append(row)
        return result, issues

    def _invoice_table_rows(self, config: Config) -> tuple[list[dict], list[Issue]]:
        aliases = {"model": ("Ký hiệu mẫu số", "Ky hieu mau so"), "series": ("Ký hiệu HD", "Ky hieu HD"), "number": ("Số HD", "So HD"), "date": ("Ngày lập", "Ngay lap"), "seller": ("MST người bán", "MST nguoi ban"), "buyer": ("MST người mua", "MST nguoi mua"), "net": ("Tiền chưa thuế", "Tien chua thue"), "tax": ("Tiền thuế", "Tien thue"), "total": ("Tổng thanh toán", "Tong thanh toan"), "currency": ("Đơn vị tiền tệ", "Don vi tien te"), "status": ("Trạng thái", "Trang thai")}
        result: list[dict] = []; issues: list[Issue] = []
        for value in _mapped_rows(self.source_path, aliases):
            if not _text(value.get("number")): continue
            model = _text(value.get("model")); model = _text(int(float(model))) if re.fullmatch(r"\d+(?:\.0+)?", model) else model
            try:
                total, total_fraction = _invoice_minor(value.get("total"))
                if model == "2": net, tax, tax_status, fractions = total, "0", "NO_VAT_MODEL_2", total_fraction
                else: net, net_fraction = _invoice_minor(value.get("net")); tax, tax_fraction = _invoice_minor(value.get("tax")); tax_status, fractions = "VAT_DECLARED", total_fraction or net_fraction or tax_fraction
            except DataError as exc:
                result.append({"__quarantine_issue": {"code": exc.code, "message": str(exc)}}); continue
            seller, buyer, ttxly = _text(value.get("seller")), _text(value.get("buyer")), _text(value.get("status")) or "1"
            if config.entity_tax_id and seller != config.entity_tax_id and buyer != config.entity_tax_id: continue
            row = {"business_date": _date(value.get("date")), "currency": _text(value.get("currency")) or "VND", "amount": total, "net_amount": net, "tax_amount": tax, "total_amount": total, "seller_tax_id": seller, "buyer_tax_id": buyer, "model": model, "series": _text(value.get("series")), "number": normalized_invoice_number(_text(value.get("number"))), "invoice_type": "GTGT" if model == "1" else "BAN_HANG" if model == "2" else model, "tax_status": tax_status, "direction": "MUA_VAO" if buyer == config.entity_tax_id else "BAN_RA", "source_status": "TAX_GATEWAY", "ttxly": ttxly}
            if config.tax_gateway_statuses and ttxly in config.tax_gateway_statuses: row["ttxly_meaning"] = config.tax_gateway_statuses[ttxly]
            if abs(int(net) + int(tax) - int(total)) > 1:
                row["total_mismatch_warning"] = True; issues.append(Issue("INVOICE_TOTAL_MISMATCH", "Tổng bảng kê lệch tiền nguồn; giữ ba số để đối chiếu.", f"$.records[{len(result)}]", "WARNING"))
            if fractions: issues.append(Issue("INVOICE_FRACTION_MINOR", "Bảng kê có phần lẻ; đã làm tròn VND.", f"$.records[{len(result)}]", "WARNING"))
            result.append(row)
        return result, issues

    # ---- Base request backup ---------------------------------------------------

    def _base_rows(self) -> list[dict]:
        source = self.source_path
        if source.is_file() and source.suffix.casefold() == ".json": files = [source]
        else:
            files = sorted(source.glob("request_*/request_*.json"))
            if not files: files = [path for path in sorted(source.rglob("*.json")) if path.name.casefold() != "attachments_manifest.json"]
        result: list[dict] = []
        for path in files:
            try: value = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError): continue
            if not isinstance(value, dict): continue
            request = value.get("get", {}).get("request", {}) if isinstance(value.get("get"), dict) else {}
            if isinstance(request, dict) and request.get("id") is not None:
                result.append(self._base_request_row(value, request)); continue
            payload = value.get("payload", value)
            if not isinstance(payload, dict): continue
            request_id, amount = _text(payload.get("request_id") or payload.get("ma_de_nghi") or payload.get("code")), payload.get("amount") or payload.get("so_tien")
            if not request_id: continue
            if amount in (None, ""):
                result.append(self._base_missing_amount(request_id)); continue
            result.append({"business_date": _date(payload.get("approved_date") or payload.get("ngay_duyet") or self.metadata.as_of), "currency": "VND", "amount": _minor(amount), "tenant": "PLHN", "request_id": request_id, "source_status": _text(payload.get("status") or payload.get("trang_thai") or "SOURCE"), "request_name": _text(payload.get("name") or payload.get("ten")) or None, "approval_status": _text(payload.get("approval_status") or payload.get("trang_thai")) or None, "project_raw": _text(payload.get("project") or payload.get("ma_du_an")) or None, "attachments": payload.get("attachments", [])})
        return [{key: value for key, value in row.items() if value is not None} for row in result]

    def _base_request_row(self, payload: dict, request: dict) -> dict:
        fields = {_text(item.get("id")): item.get("value") for item in request.get("form", []) if isinstance(item, dict) and _text(item.get("id"))}
        amount_raw, request_id = fields.get("tong_thanh_tien"), _text(request.get("id"))
        if amount_raw in (None, ""): return self._base_missing_amount(request_id)
        tables = payload.get("custom_table", {}).get("custom_table", {}) if isinstance(payload.get("custom_table"), dict) else {}
        beneficiary = tables.get("custom_tai_khoan_thu_huong", {}) if isinstance(tables, dict) else {}
        headers = [_text(value) for value in beneficiary.get("headers", [])] if isinstance(beneficiary, dict) else []
        data = beneficiary.get("data", []) if isinstance(beneficiary, dict) else []
        account_index = next((i for i, header in enumerate(headers) if _matches_header(header, ("Số tài khoản", "So tai khoan", "Tài khoản", "Tai khoan"))), None)
        beneficiary_account = ""
        if account_index is not None:
            for row in data if isinstance(data, list) else []:
                if isinstance(row, list) and account_index < len(row) and _text(row[account_index]): beneficiary_account = _text(row[account_index]); break
        attachments = []
        for item in payload.get("_attachment_results", []):
            if isinstance(item, dict):
                name, size = _text(item.get("name") or item.get("filename") or item.get("file_name")), item.get("size") or item.get("file_size")
                if name: attachments.append({"name": name, "size": size if isinstance(size, int) else None})
        try: business_date = datetime.fromtimestamp(int(float(request.get("last_update"))), timezone(timedelta(hours=7))).date().isoformat()
        except (TypeError, ValueError, OSError): business_date = self.metadata.as_of
        amount_text = _text(amount_raw)
        if amount_text.casefold().endswith(" vnd"): amount_text = amount_text[:-4].strip()
        row = {"business_date": business_date, "currency": "VND", "amount": _minor(amount_text), "tenant": "PLHN", "request_id": request_id, "request_name": _text(request.get("name")) or None, "source_status": _text(request.get("state")) or "SOURCE", "source_state": _text(request.get("state")) or None, "approval_status": _text(request.get("status")) or None, "project_raw": _text(fields.get("du_an")) or None, "expense_raw": _text(fields.get("chi_phi")) or None, "beneficiary_account": beneficiary_account or None, "beneficiary_headers": headers, "beneficiary_rows": data if isinstance(data, list) else [], "attachments": attachments, "fetched_at": _text(payload.get("fetched_at")) or None}
        return {key: value for key, value in row.items() if value is not None}

    def _base_missing_amount(self, request_id: str) -> dict:
        return {"business_date": self.metadata.as_of, "currency": "VND", "amount": "0", "tenant": "PLHN", "request_id": request_id,
                "source_status": "QUARANTINED_SOURCE", "__quarantine_placeholder": True,
                "__quarantine_issue": {"code": "BASE_AMOUNT_MISSING", "message": "Đề nghị Base thiếu tổng thành tiền."}}

    # ---- Junsky exports --------------------------------------------------------

    def _junsky_rows(self, config: Config) -> tuple[list[dict], list[Issue], dict]:
        if not self.source_path.is_dir(): raise DataError("JUNSKY_DIRECTORY", "Nguồn Junsky cần là thư mục DANH MỤC hoặc thư mục kết xuất.")
        all_files = sorted(self.source_path.rglob("*.xlsx"))
        # The observed export keeps the two journals beside the DANH MỤC folder.
        # Include only these declared siblings; Store snapshots them with the input.
        if self.source_path.name.casefold() == "danh mục":
            for sibling in (self.source_path.parent / "dgbList.xlsx", self.source_path.parent / "Sổ NKC có đối ưng.xlsx",
                            self.source_path.parent / "Ngân Hàng" / "Sổ NKC có đối ưng.xlsx"):
                if sibling.is_file() and sibling not in all_files:
                    all_files.append(sibling)
            for declared in self.journal_paths:
                if declared.is_file() and declared not in all_files:
                    all_files.append(declared)
        if not all_files: raise DataError("JUNSKY_FILES", "Không có workbook Junsky .xlsx trong thư mục nguồn.")
        roles: dict[str, list[Path]] = {name: [] for name in ("OPEN_ITEM", "COUNTERPARTY", "EXPENSE", "PROJECT", "COST_CENTER", "ACCOUNT", "JOURNAL")}
        for path in all_files:
            title = _norm(path.stem)
            if title.startswith("DANH SACH CHUNG TU CONG NO"): roles["OPEN_ITEM"].append(path)
            elif title.startswith("DANH MUC KHACH HANG"): roles["COUNTERPARTY"].append(path)
            elif title.startswith("KHOAN MUC CHI PHI"): roles["EXPENSE"].append(path)
            elif title.startswith("MA DU AN"): roles["PROJECT"].append(path)
            elif title.startswith("TRUNG TAM CHI PHI"): roles["COST_CENTER"].append(path)
            elif title.startswith("BANG CAN DOI PHAT SINH"): roles["ACCOUNT"].append(path)
            elif title.startswith("DGBLIST") or title.startswith("SO NKC CO DOI UNG"): roles["JOURNAL"].append(path)
        select = lambda paths: max(paths, key=self._catalog_sort_key)
        rows: list[dict] = []; issues: list[Issue] = []; account_natures: dict[str, str] = dict(config.account_nature or {}); catalog_rows: dict[str, list[dict]] = {}
        for kind in ("COUNTERPARTY", "EXPENSE", "PROJECT", "COST_CENTER", "ACCOUNT"):
            if roles[kind]:
                catalog_rows[kind] = self._catalog_rows(select(roles[kind]), kind, config); rows.extend(catalog_rows[kind])
                if kind == "ACCOUNT":
                    for entry in catalog_rows[kind]:
                        if entry.get("account_nature") in {"DEBIT", "CREDIT"}: account_natures[entry["code"]] = entry["account_nature"]
                issues.append(Issue("SOURCE_FILE_SELECTED", f"Đã chọn file kết xuất theo ngày tên file/mtime cho {kind}.", "$.source", "WARNING"))
        if roles["OPEN_ITEM"]: rows.extend(self._open_items(select(roles["OPEN_ITEM"]), account_natures)); issues.append(Issue("SOURCE_FILE_SELECTED", "Đã chọn file kết xuất theo ngày tên file/mtime cho OPEN_ITEM.", "$.source", "WARNING"))
        if roles["JOURNAL"]:
            # Junsky 2026 is delivered beside the bank folder while dgbList
            # carries prior history.  Keep every workbook whose layout satisfies
            # the journal contract; record natural keys deduplicate overlap at
            # Store level and no longer hide the newer operational ledger.
            journal_paths = [path for path in roles["JOURNAL"] if self._journal_layout_score(path) >= 0]
            for path in sorted(journal_paths, key=self._catalog_sort_key):
                rows.extend(self._journal_rows(path))
            issues.append(Issue("SOURCE_FILE_SELECTED", "Đã đọc các sổ có bố cục hợp đồng; giữ sổ mới và lịch sử để dò trùng.", "$.source", "WARNING"))
        for start, end, scope in self.lock_periods: rows.append({"kind": "LOCK_PERIOD", "business_date": start, "valid_from": start, "valid_to": end, "scope": scope, "source_status": "LOCKED"})
        catalogs = {kind: {row["code"] for row in rows if row.get("kind") == kind and row.get("code")} for kind in ("COUNTERPARTY", "ACCOUNT", "PROJECT", "EXPENSE", "COST_CENTER")}
        references = (("counterparty", "COUNTERPARTY"), ("account", "ACCOUNT"), ("project", "PROJECT"), ("expense", "EXPENSE"), ("cost_center", "COST_CENTER")); outside: Counter[tuple[str, str]] = Counter()
        for ordinal, row in enumerate(rows):
            values = list(row.get("lines", [])) if row.get("kind") == "JOURNAL" else [row]
            for value in values:
                for field, catalog in references:
                    code = _text(value.get(field))
                    if code and code not in catalogs[catalog]: outside[(catalog, code)] += 1; issues.append(Issue("OUTSIDE_CATALOG_CODE", "Mã xuất hiện ngoài danh mục; giữ để kết xuất lại danh mục.", f"$.records[{ordinal}].{field}", "WARNING"))
        controls = {"outside_catalog_codes": [{"catalog": catalog, "code": code, "count": count} for (catalog, code), count in sorted(outside.items())]}
        return rows, issues, controls

    @staticmethod
    def _catalog_sort_key(path: Path) -> tuple[int, int, str]:
        match = re.search(r"(?<!\d)(20\d{2})[-_]?([01]\d)[-_]?([0-3]\d)(?!\d)", path.stem)
        return (int("".join(match.groups())) if match else -1, path.stat().st_mtime_ns, path.name)

    @staticmethod
    def _journal_layout_score(path: Path) -> int:
        try: headers, _ = _sheet_rows(path, expected=("Ngày c.từ", "Số chứng từ", "Ghi nợ", "Ghi có", "Số tiền", "Tài khoản", "Phát sinh nợ", "Phát sinh có"))
        except DataError: return -1
        expected = {_norm(value) for value in ("Ngày c.từ", "Số chứng từ", "Ghi nợ", "Ghi có", "Số tiền", "Tài khoản", "Phát sinh nợ", "Phát sinh có")}
        return len(expected & {_norm(value) for value in headers})

    def _catalog_rows(self, path: Path, kind: str, config: Config) -> list[dict]:
        aliases = {"COUNTERPARTY": {"code": ("Mã đối tượng", "Mã khách hàng", "Mã"), "name": ("Tên đối tượng", "Tên khách hàng", "Tên"), "tax_id": ("Mã số thuế",), "nature": ("Tính chất", "Dư nợ/có")}, "EXPENSE": {"code": ("Mã chi phí", "Mã khoản mục", "Mã"), "name": ("Tên chi phí", "Tên khoản mục", "Tên")}, "PROJECT": {"code": ("Mã dự án", "Mã"), "name": ("Tên dự án", "Tên")}, "COST_CENTER": {"code": ("Mã TTCP", "Mã trung tâm chi phí", "Mã"), "name": ("Tên TTCP", "Tên trung tâm chi phí", "Tên")}, "ACCOUNT": {"code": ("Mã tài khoản", "Mã"), "name": ("Tên tài khoản", "Tên"), "nature": ("Tính chất", "Dư nợ/có")}}[kind]
        result = []
        for row in _mapped_rows(path, aliases):
            code, name = _text(row.get("code")), _text(row.get("name"))
            if not code or not name: continue
            entry = {"kind": kind, "business_date": self.metadata.as_of, "code": code, "version": path.name, "name": name, "source_status": "CATALOG_EXPORT", "valid_from": self.metadata.catalog_valid_from or config.catalog_valid_from, "valid_to": None}
            if kind == "COUNTERPARTY" and _text(row.get("tax_id")): entry["tax_id"] = _text(row.get("tax_id"))
            nature = _norm(row.get("nature"))
            if kind == "ACCOUNT" and nature: entry["account_nature"] = "CREDIT" if "CO" in nature else "DEBIT" if "NO" in nature else None
            result.append({key: value for key, value in entry.items() if value is not None})
        return result

    def _open_items(self, path: Path, account_natures: dict[str, str]) -> list[dict]:
        aliases = {"unit": ("Mã đơn vị",), "item": ("Chứng từ công nợ",), "transaction": ("Mã NV",), "date": ("Ngày",), "party": ("Đối tượng", "Mã đối tượng"), "account": ("Tài khoản",), "amount": ("Số tiền (HT)", "Số tiền"), "project": ("Mã dự án",), "series": ("Ký hiệu hđ", "Ký hiệu HD"), "number": ("Số hóa đơn",), "invoice_date": ("Ngày hóa đơn",), "description": ("Nội dung",), "loan": ("Hợp đồng vay",)}
        rows = []
        for value in _mapped_rows(path, aliases):
            item, party, account = _text(value.get("item")), _text(value.get("party")), _text(value.get("account"))
            if not item or not party or not account: continue
            try: amount = abs(int(_minor(value.get("amount"))))
            except DataError as exc: rows.append({"__quarantine_issue": {"code": exc.code, "message": str(exc)}}); continue
            nature = next((kind for code, kind in sorted(account_natures.items(), key=lambda pair: -len(pair[0])) if account.startswith(code)), "DEBIT")
            number = _text(value.get("number"))
            row = {"kind": "OPEN_ITEM", "business_date": self.metadata.as_of, "currency": "VND", "amount": str(-amount if nature == "CREDIT" else amount), "account": account, "counterparty": party, "item_id": item, "item_type": "INVOICE" if number else "UNBILLED", "invoice_reference": normalized_invoice_number(number) if number else None, "project": _text(value.get("project")) or None, "invoice_series": _text(value.get("series")) or None, "invoice_number": normalized_invoice_number(number) if number else None, "invoice_date": _date(value.get("invoice_date")) if _text(value.get("invoice_date")) else None, "document_date": _date(value.get("date")) if _text(value.get("date")) else None, "description": _text(value.get("description")) or None, "loan_contract": _text(value.get("loan")) or None, "unit_code": _text(value.get("unit")) or None, "transaction_code": _text(value.get("transaction")) or None}
            rows.append({key: item for key, item in row.items() if item is not None})
        return rows

    def _journal_rows(self, path: Path) -> list[dict]:
        return read_journal_rows(path)


def read_journal_rows(path: Path) -> list[dict]:
    """Vouchers of a Junsky ledger workbook (Sổ NKC), grouped and balanced.

    Also used read-only by the scoring replay of a trial kho, whose own
    ledger was cut at the learning date (answer = the full ledger file).
    """
    aliases = {"date": ("Ngày hạch toán", "Ngày chứng từ", "Ngày c.từ", "Ngày"), "book": ("Sổ", "Loại sổ"), "voucher_type": ("Loại chứng từ", "Mã NV"), "voucher": ("Số chứng từ", "Số CT"), "account": ("Tài khoản",), "debit": ("Phát sinh nợ",), "credit": ("Phát sinh có",), "debit_account": ("Ghi nợ",), "credit_account": ("Ghi có",), "amount": ("Số tiền",), "docs": ("Số CT đính kèm", "DocsNo"), "invoice": ("Số hóa đơn",), "description": ("Nội dung", "Diễn giải"), "party": ("Mã đối tượng", "Đối tượng"), "project": ("Mã dự án",), "expense": ("Khoản mục",), "cost_center": ("Mã TTCP", "Trung tâm chi phí"), "unit": ("Mã đơn vị",), "transaction": ("Mã NV",)}
    grouped: dict[tuple[str, str, str, str], list[dict]] = {}
    for row in _mapped_rows(path, aliases):
        voucher = _text(row.get("voucher"))
        if not voucher: continue
        try:
            business_date = _date(row.get("date"))
            if _text(row.get("debit_account")) and _text(row.get("credit_account")):
                amount = _minor(row.get("amount")); lines = [{"account": _text(row.get("debit_account")), "debit": amount, "credit": "0"}, {"account": _text(row.get("credit_account")), "debit": "0", "credit": amount}]
            elif _text(row.get("account")): lines = [{"account": _text(row.get("account")), "debit": _minor(row.get("debit")), "credit": _minor(row.get("credit"))}]
            else: continue
        except DataError: continue
        # A workbook filename is not a Junsky BranchID.  Preserve an
        # absent unit as absent so export can ask for the real code.
        key = (_text(row.get("unit")), business_date, voucher, _text(row.get("book")) or path.stem)
        context = {"docs": _text(row.get("docs")), "invoice": _text(row.get("invoice")), "description": _text(row.get("description")), "party": _text(row.get("party")), "project": _text(row.get("project")), "expense": _text(row.get("expense")), "cost_center": _text(row.get("cost_center")), "unit": _text(row.get("unit")), "transaction": _text(row.get("transaction")), "voucher_type": _text(row.get("voucher_type"))}
        grouped.setdefault(key, []).append({"lines": lines, **context})
    result = []
    for (unit, business_date, voucher, book), rows in grouped.items():
        lines = [line for row in rows for line in row["lines"]]; debit, credit = sum(int(row["debit"]) for row in lines), sum(int(row["credit"]) for row in lines)
        if debit != credit or not debit: continue
        first = rows[0]
        pick = lambda name: next((entry[name] for entry in rows if entry.get(name)), "")
        row = {"kind": "JOURNAL", "business_date": business_date, "currency": "VND", "amount": "0", "book": book, "fiscal_year": business_date[:4], "voucher_type": pick("voucher_type") or "JUNSKY", "voucher_number": voucher, "source_status": "POSTED", "posting_status": "POSTED", "complete_voucher": True, "bank_transaction_number": pick("docs") or None, "invoice_reference": normalized_invoice_number(pick("invoice")) if pick("invoice") else None, "description": pick("description") or None, "counterparty": pick("party") or None, "project": pick("project") or None, "expense": pick("expense") or None, "cost_center": pick("cost_center") or None, "unit_code": unit or None, "transaction_code": pick("transaction") or None, "lines": [{"line_id": str(index), "account": line["account"], "debit": line["debit"], "credit": line["credit"]} for index, line in enumerate(lines, 1)]}
        result.append({key: value for key, value in row.items() if value is not None})
    return result


def parse_invoice_xml(raw: bytes, entity_tax_id: str, non_taxable_in_total: bool = False, *, index: int = 0) -> tuple[dict | None, list[Issue]]:
    """One e-invoice XML (Tổng cục Thuế 2.1.0) → an INVOICE record of the own entity, or None.

    Shared by the source adapter and the invoice history (V12).  A row
    carrying ``__quarantine_issue`` is returned for unreadable money values.
    """
    issues: list[Issue] = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return None, [Issue("INVALID_XML", "Không phân tích được một XML; bỏ qua tệp lỗi.", "$.source", "WARNING")]
    for element in root.iter():
        if isinstance(element.tag, str) and "}" in element.tag:
            element.tag = element.tag.split("}", 1)[1]
    invoice = root.find(".//HDon")
    if invoice is None: invoice = root
    common = invoice.find(".//TTChung")
    if common is None: common = invoice
    seller, buyer, total = invoice.find(".//NBan"), invoice.find(".//NMua"), invoice.find(".//TToan")
    def value(element, *names, default=""):
        if element is not None:
            for tag in names:
                node = element.find(".//" + tag)
                if node is not None and _text(node.text): return _text(node.text)
        return default
    seller_tax, buyer_tax = value(seller, "MST"), value(buyer, "MST")
    if seller_tax != entity_tax_id and buyer_tax != entity_tax_id: return None, issues
    model = _text(value(common, "KHMSHDon")); model = _text(int(float(model))) if re.fullmatch(r"\d+(?:\.0+)?", model) else model
    try:
        series, number = _text(value(common, "KHHDon")), normalized_invoice_number(_text(value(common, "SHDon")))
        total_minor, total_fraction = _invoice_minor(value(total, "TgTTTBSo"))
        if model == "2": net_minor, net_fraction, tax_minor, tax_fraction, tax_status = total_minor, False, "0", False, "NO_VAT_MODEL_2"
        else: net_minor, net_fraction = _invoice_minor(value(total, "TgTCThue")); tax_minor, tax_fraction, tax_status = (*_invoice_minor(value(total, "TgTThue")), "VAT_DECLARED")
        other_minor, other_fraction = _invoice_minor(value(total, "TGTKhac")); non_taxable_minor, non_fraction = _invoice_minor(value(total, "TGTKCThue"))
    except DataError as exc:
        return {"__quarantine_issue": {"code": exc.code, "message": str(exc)}}, issues
    expected = int(net_minor) + int(tax_minor) + int(other_minor) + (0 if non_taxable_in_total else int(non_taxable_minor))
    row: dict[str, Any] = {"business_date": _date(value(common, "NLap", "NgayLap")), "currency": value(common, "DVTTe", default="VND") or "VND", "amount": total_minor, "net_amount": net_minor, "tax_amount": tax_minor, "total_amount": total_minor, "other_amount": other_minor, "non_taxable_amount": non_taxable_minor, "seller_tax_id": seller_tax, "buyer_tax_id": buyer_tax, "model": model, "series": series, "number": number, "invoice_type": "GTGT" if model == "1" else "BAN_HANG" if model == "2" else model, "tax_status": tax_status, "direction": "MUA_VAO" if buyer_tax == entity_tax_id else "BAN_RA", "source_status": "XML_RECEIVED", "lines": []}
    # V12: names identify a counterparty whose tax code is not in the catalogue.
    seller_name, buyer_name = value(seller, "Ten"), value(buyer, "Ten", "HVTNMHang")
    if seller_name: row["seller_name"] = seller_name
    if buyer_name: row["buyer_name"] = buyer_name
    if abs(expected - int(total_minor)) > 1:
        row["total_mismatch_warning"] = True; issues.append(Issue("INVOICE_TOTAL_MISMATCH", "Tổng hóa đơn XML lệch các thành phần nguồn; giữ để đối chiếu.", f"$.records[{index}]", "WARNING"))
    if any((total_fraction, net_fraction, tax_fraction, other_fraction, non_fraction)):
        issues.append(Issue("INVOICE_FRACTION_MINOR", "Tiền XML có phần lẻ; đã làm tròn VND theo cấu hình.", f"$.records[{index}]", "WARNING"))
    relation = invoice.find(".//TTHDLQuan")
    if relation is not None:
        related = {"relation_type": value(relation, "TCHDon"), "model": value(relation, "KHMSHDCLQuan"), "series": value(relation, "KHHDCLQuan"), "number": value(relation, "SHDCLQuan"), "date": value(relation, "NLHDCLQuan")}
        row["related_invoice"] = {key: item for key, item in related.items() if item}
    for line_index, line in enumerate(invoice.findall(".//HHDVu"), 1):
        line_net, line_net_fraction = _invoice_minor(value(line, "ThTien")); line_tax, line_tax_fraction = _invoice_minor(value(line, "TThue"))
        if line_net_fraction or line_tax_fraction: issues.append(Issue("INVOICE_FRACTION_MINOR", "Dòng XML có phần lẻ; đã làm tròn VND theo cấu hình.", f"$.records[{index}].lines[{line_index - 1}]", "WARNING"))
        row["lines"].append({"line_id": value(line, "STT") or str(line_index), "description": value(line, "THHDVu", "TenHang") or "(không mô tả)", "net_amount": line_net, "tax_amount": line_tax, "total_amount": str(int(line_net) + int(line_tax)), "tax_rate": value(line, "TSuat").replace("%", "") or None, "line_nature": "GOODS"})
    if not row["lines"]: row.pop("lines")
    elif abs(sum(int(line["net_amount"]) for line in row["lines"]) - int(net_minor)) > len(row["lines"]):
        row["detail_total_warning"] = True
        issues.append(Issue("DETAIL_TOTAL_MISMATCH", "Tổng dòng XML lệch header nguồn; giữ để đối chiếu.", f"$.records[{index}]", "WARNING"))
    return row, issues


def invoice_months(root: Path) -> list[dict]:
    """Month folders written by the invoice download tool: ``<root>/yyyy-mm/{mua_vao,ban_ra}/*.xml``."""
    result = []
    if not root.is_dir():
        return result
    for folder in sorted(root.iterdir(), reverse=True):
        if not folder.is_dir() or not re.fullmatch(r"\d{4}-\d{2}", folder.name):
            continue
        counts = {side: sum(1 for item in (folder / side).glob("*.xml")) if (folder / side).is_dir() else 0 for side in ("mua_vao", "ban_ra")}
        if counts["mua_vao"] or counts["ban_ra"]:
            result.append({"month": folder.name, **counts})
    return result


def invoice_month_files(root: Path, month: str, sides: tuple[str, ...] = ("mua_vao", "ban_ra")) -> list[Path]:
    if not re.fullmatch(r"\d{4}-\d{2}", str(month or "")):
        raise DataError("INVOICE_MONTH", "Tháng hóa đơn phải có dạng yyyy-mm.")
    folder = root / month
    files = []
    for side in sides:
        if (folder / side).is_dir():
            files.extend(sorted((folder / side).glob("*.xml")))
    return files
