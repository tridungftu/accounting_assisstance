"""M4-01B2 (sửa 4) — phát hiện thay đổi chưa chốt (Track Changes) trong DOCX theo NAMESPACE XML, không theo chuỗi literal.

- Phân tích XML thật (ElementTree/expat) mọi phần nội dung WordprocessingML của gói (`word/*.xml`: document, header*, footer*, footnotes,
  endnotes, comments, glossary…). Thẻ được nhận theo URI namespace (Transitional + Strict), nên prefix khác hay xuống dòng sau QName vẫn bị bắt.
- Có DOCTYPE/khai báo ENTITY, XML hỏng, thiếu word/document.xml, không phải ZIP → báo `KHONG_DOC_DUOC` trung thực (không coi là sạch).
- Không mở Word/LibreOffice, không accept-change, không ghi/xóa tệp nào; chỉ đọc bytes trong bộ nhớ. Không dùng mã vendor (không phụ thuộc nạp lõi).
"""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile

NS_W = ("http://schemas.openxmlformats.org/wordprocessingml/2006/main", "http://purl.oclc.org/ooxml/wordprocessingml/main")
# phần tử đánh dấu sửa đổi (ECMA-376 §17.13) — chèn/xóa/di chuyển nội dung, đổi định dạng, đổi bảng/ô/đánh số
THE_SUA_DOI = frozenset({
    "ins", "del", "moveFrom", "moveTo", "moveFromRangeStart", "moveToRangeStart", "moveFromRangeEnd", "moveToRangeEnd",
    "rPrChange", "pPrChange", "sectPrChange", "tblPrChange", "tblPrExChange", "trPrChange", "tcPrChange", "tblGridChange", "numberingChange",
    "cellIns", "cellDel", "cellMerge", "customXmlInsRangeStart", "customXmlDelRangeStart", "customXmlMoveFromRangeStart",
    "customXmlMoveToRangeStart",
})
PHAN_NOI_DUNG = re.compile(r"word/[^/]+\.xml")
TOI_DA_PHAN = 64 * 1024 * 1024


class KhongDocDuoc(ValueError):
    pass


def _dem_phan(raw: bytes) -> int:
    if re.search(rb"<!\s*(DOCTYPE|ENTITY)", raw, re.I):
        raise KhongDocDuoc("XML có DOCTYPE/ENTITY")
    n = 0
    try:
        for _, el in ET.iterparse(io.BytesIO(raw), events=("start",)):
            tag = el.tag
            if isinstance(tag, str) and tag.startswith("{"):
                uri, _, ten = tag[1:].partition("}")
                if uri in NS_W and ten in THE_SUA_DOI:
                    n += 1
    except ET.ParseError as exc:
        raise KhongDocDuoc(f"XML hỏng ({exc.code})") from None
    return n


def dem_sua_doi_docx(raw: bytes) -> dict:
    """{'so_sua_doi': n, 'phan': {tên phần: n}}. Lỗi định dạng → KhongDocDuoc (người gọi báo không hỗ trợ/không đọc được, không coi là sạch)."""
    try:
        z = zipfile.ZipFile(io.BytesIO(bytes(raw)))
    except (zipfile.BadZipFile, ValueError, OSError, EOFError):
        raise KhongDocDuoc("không phải gói ZIP/OOXML") from None
    with z:
        ten = [i.filename for i in z.infolist() if PHAN_NOI_DUNG.fullmatch(i.filename)]
        if "word/document.xml" not in ten:
            raise KhongDocDuoc("thiếu word/document.xml")
        phan = {}
        for t in sorted(ten):
            info = z.getinfo(t)
            if info.file_size > TOI_DA_PHAN:
                raise KhongDocDuoc(f"phần {t} quá lớn")
            try:
                du_lieu = z.read(t)
            except (zipfile.BadZipFile, KeyError, ValueError, OSError, EOFError, RuntimeError):
                raise KhongDocDuoc(f"không giải nén được {t}") from None
            phan[t] = _dem_phan(du_lieu)
    return {"so_sua_doi": sum(phan.values()), "phan": {k: v for k, v in phan.items() if v}}
