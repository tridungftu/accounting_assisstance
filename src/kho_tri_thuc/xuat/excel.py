from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment

from ..ha_tang.primitives import DataError


def table(wb, name, headers, rows):
    ws = wb.create_sheet(name)
    ws.append(headers)
    for row in rows:
        ws.append(row)
    for row in ws:
        for cell in row:
            if isinstance(cell.value, str):
                # Keep untrusted descriptions/IDs as strings, including '=...', '+', '-', '@'.
                cell.data_type = "s"
                cell.number_format = "@"
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="17365D")
        cell.font = Font(color="FFFFFF", bold=True)
    for index, header in enumerate(headers, 1):
        from openpyxl.utils import get_column_letter
        ws.column_dimensions[get_column_letter(index)].width = min(42, max(18, len(header) + 3))
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    return ws


def workbook():
    wb = Workbook()
    wb.remove(wb.active)
    wb.properties.title = "FIXTURE — KHÔNG DÙNG IMPORT JUNSKY"
    return wb


def to_bytes(wb):
    buffer = BytesIO()
    wb.save(buffer)
    wb.close()
    return buffer.getvalue()


def load(raw):
    try:
        wb = load_workbook(BytesIO(raw), data_only=False, keep_links=False)
    except Exception as exc:
        raise DataError("INVALID_WORKBOOK", "Không đọc được workbook xlsx.") from exc
    for ws in wb:
        for row in ws:
            if any(cell.data_type == "f" for cell in row):
                wb.close()
                raise DataError("FORMULA_FORBIDDEN", "Workbook duyệt không nhận công thức Excel.")
    return wb


def rows(wb, sheet, headers):
    if sheet not in wb.sheetnames:
        raise DataError("MISSING_SHEET", f"Thiếu sheet {sheet}.")
    ws = wb[sheet]
    if [cell.value for cell in ws[1]] != list(headers):
        raise DataError("WORKBOOK_SCHEMA", f"Sai cột/thứ tự cột trong {sheet}.")
    return [dict(zip(headers, [cell.value if cell.value is not None else "" for cell in row])) for row in ws.iter_rows(min_row=2)]
