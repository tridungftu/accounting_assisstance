"""
xlsx_mini.py — Ghi file Excel .xlsx chỉ bằng thư viện chuẩn Python (không cần cài openpyxl).
    write_xlsx(path, {"Ten_sheet": {"rows": [[...], ...], "widths": [10, 40, ...]}, ...})
Dòng đầu mỗi sheet là tiêu đề (in đậm, nền xanh nhạt, cố định khi cuộn). Ô tự xuống dòng.
Ô có giá trị bắt đầu bằng "KIỂM TRA" hoặc "SAI" được tô vàng; "ĐÚNG"/"OK" tô xanh.
"""
import zipfile
from xml.sax.saxutils import escape


def _col(n):
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell(ref, v, style):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return f'<c r="{ref}" s="{style}"><v>{v}</v></c>'
    t = escape(str(v if v is not None else ""))[:32000]
    t = "".join(ch for ch in t if ch in "\t\n\r" or ord(ch) >= 32)
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{t}</t></is></c>'


def _sheet(rows, widths):
    cols = "".join(f'<col min="{i+1}" max="{i+1}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths or []))
    out = []
    for r, row in enumerate(rows):
        cells = []
        for c, v in enumerate(row):
            style = 1 if r == 0 else 2
            sv = str(v) if v is not None else ""
            if r > 0 and (sv.startswith("KIỂM TRA") or sv.startswith("SAI") or sv.startswith("THIẾU")):
                style = 3
            elif r > 0 and sv in ("OK", "ĐÚNG"):
                style = 4
            cells.append(_cell(f"{_col(c)}{r+1}", v, style))
        out.append(f'<row r="{r+1}">{"".join(cells)}</row>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
            + (f"<cols>{cols}</cols>" if cols else "") + f'<sheetData>{"".join(out)}</sheetData></worksheet>')


STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
          '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
          '<fills count="5"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
          '<fill><patternFill patternType="solid"><fgColor rgb="FFDDEBF7"/></patternFill></fill>'
          '<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/></patternFill></fill>'
          '<fill><patternFill patternType="solid"><fgColor rgb="FFE2EFDA"/></patternFill></fill></fills>'
          '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
          '<cellXfs count="5"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
          '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
          '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
          '<xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
          '<xf numFmtId="0" fontId="0" fillId="4" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
          '</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')


def write_xlsx(path, sheets):
    names = list(sheets)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                   + "".join(f'<Override PartName="/xl/worksheets/sheet{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(len(names)))
                   + "</Types>")
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + "".join(f'<sheet name="{escape(n[:31])}" sheetId="{i+1}" r:id="rId{i+1}"/>' for i, n in enumerate(names))
                   + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(f'<Relationship Id="rId{i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i+1}.xml"/>' for i in range(len(names)))
                   + f'<Relationship Id="rId{len(names)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                   + "</Relationships>")
        z.writestr("xl/styles.xml", STYLES)
        for i, n in enumerate(names):
            z.writestr(f"xl/worksheets/sheet{i+1}.xml", _sheet(sheets[n]["rows"], sheets[n].get("widths")))


def read_xlsx(path, sheet_index=0):
    """Đọc sheet (mặc định sheet đầu) của file .xlsx → list các dòng (list chuỗi). Dùng cho file do Excel lưu."""
    import re as _re
    import xml.etree.ElementTree as ET
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rel = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(f"{ns}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{ns}t")))
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rid = wb.find(f"{ns}sheets")[sheet_index].get(f"{rel}id")
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        target = [r.get("Target") for r in rels if r.get("Id") == rid][0].lstrip("/")
        target = target if target.startswith("xl/") else "xl/" + target
        sh = ET.fromstring(z.read(target))
    rows = []
    for row in sh.iter(f"{ns}row"):
        vals = {}
        for c in row.findall(f"{ns}c"):
            ref = c.get("r", "")
            letters = _re.match(r"[A-Z]+", ref).group(0) if ref else _col(len(vals))
            idx = 0
            for ch in letters:
                idx = idx * 26 + ord(ch) - 64
            t = c.get("t")
            if t == "s":
                v = shared[int(c.find(f"{ns}v").text)]
            elif t == "inlineStr":
                v = "".join(x.text or "" for x in c.iter(f"{ns}t"))
            else:
                ve = c.find(f"{ns}v")
                v = ve.text if ve is not None else ""
                if v and _re.fullmatch(r"-?\d+\.0", v):
                    v = v[:-2]
            vals[idx - 1] = v or ""
        if vals:
            rows.append([vals.get(i, "") for i in range(max(vals) + 1)])
    return rows
