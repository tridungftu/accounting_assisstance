"""Fixture DEMO tổng hợp cho M4-01 (không phải tài liệu thật, không lấy từ app nguồn): dựng bytes DOCX/XLSX/PDF trong bộ nhớ.

- hop_dong_docx(): hợp đồng xây dựng DEMO có phần mở đầu khớp quy tắc thông tin chung của nguồn (master_hd) + ≥5 Điều.
- hop_dong_docx(track_changes=True): cùng nội dung nhưng còn <w:ins> (Track Changes) — lõi nguồn cần Word để Accept All → KHONG_HO_TRO.
- boq_xlsx(...): BOQ DEMO đọc được bằng parser nguồn (tiêu đề 7 cột chuẩn); biến thể lệch số học (phát hiện KHÔNG chặn — M4-01B),
  ô trống vs 0 tường minh, và ô số không đọc được (lỗi chặn).
- pdf_demo(): bytes PDF tối thiểu (chỉ để lưu/nhận diện chữ ký tệp; không trích).
Giá trị tiền chỉ là số DEMO; không có PN/dự án/người thật.
"""

from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape

SO_HD = "HDXD-DEMO-01"
DONG_HOP_DONG = (
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
    "HỢP ĐỒNG THI CÔNG XÂY DỰNG (DEMO)",
    f"Số: {SO_HD}",
    "Gói thầu: Thi công hạ tầng DEMO",
    "Dự án: Khu công nghiệp DEMO A",
    "Địa điểm: Tỉnh DEMO",
    "Căn cứ Luật Xây dựng (văn bản DEMO);",
    "Hôm nay, ngày 05 tháng 01 năm 2026, chúng tôi gồm:",
    "Bên giao thầu (Bên A): Công ty DEMO A",
    "Bên nhận thầu (Bên B): Nhà thầu DEMO B",
    "Điều 1. Nội dung công việc",
    "1.1 Bên B thi công hạng mục hạ tầng theo hồ sơ thiết kế DEMO.",
    "Điều 2. Giá hợp đồng",
    "2.1 Giá trị hợp đồng là 1.000.000.000 đồng, đã bao gồm thuế VAT 8%.",
    "2.2 Hợp đồng trọn gói.",
    "Điều 3. Tạm ứng và thanh toán",
    "3.1 Tạm ứng: Không áp dụng.",
    "3.2 Mỗi đợt thanh toán cho bên B tối đa 90% giá trị khối lượng hoàn thành được nghiệm thu.",
    "3.3 Thời gian thanh toán: Tối đa 30 ngày kể từ ngày nhận đủ hồ sơ hợp lệ.",
    "Điều 4. Bảo hành",
    "4.1 Thời hạn bảo hành là 12 tháng kể từ ngày nghiệm thu bàn giao.",
    "Điều 5. Tiến độ",
    "5.1 Tiến độ thực hiện: 180 ngày kể từ ngày khởi công.",
    "Điều 6. Hiệu lực",
    "6.1 Hợp đồng này có hiệu lực kể từ ngày ký.",
)
BOQ_TIEU_DE = ("STT", "Mã hạng mục", "Tên công việc", "Đơn vị tính", "Khối lượng", "Đơn giá", "Thành tiền")
BOQ_COT = {"stt": "A", "ma_rieng": "B", "ten": "C", "dvt": "D", "kl": "E", "don_gia": "F", "thanh_tien": "G"}
BOQ_GOC = (("A", None, "Phần móng", None, None, None, None),
           (1, "HM-01", "Đào đất hố móng", "m3", 100, 50000, 5000000),
           (2, "HM-02", "Bê tông móng", "m3", 20, 1500000, 30000000),
           (None, None, "Tổng cộng", None, None, None, 35000000))
BOQ_LOI_SO_HOC = (("A", None, "Phần móng", None, None, None, None),
                  (1, "HM-01", "Đào đất hố móng", "m3", 100, 50000, 5000000),
                  (2, "HM-03", "Cốt thép", "kg", 10, 20000, 999))
BOQ_PHU_LUC = ((1, "HM-02", "Bê tông móng", "m3", 25, 1500000, 37500000),
               (2, "HM-04", "Rãnh thoát nước", "m", 50, 200000, 10000000))
# M4-01B (B5): dòng 2 (HM-01) KL bỏ TRỐNG; dòng 3 (HM-02) KL = 0 tường minh — hai trạng thái phải khác nhau trong ô gốc và giá trị typed
BOQ_TRONG_VA_0 = (("A", None, "Phần móng", None, None, None, None),
                  (1, "HM-01", "Đào đất hố móng", "m3", None, 50000, None),
                  (2, "HM-02", "Bê tông móng", "m3", 0, 1500000, 0))
# ô số không đọc được (chữ trong cột Khối lượng) — lỗi ĐỌC (chặn), khác phát hiện số học
BOQ_SO_KHONG_DOC = ((1, "HM-01", "Đào đất hố móng", "m3", "một trăm", 50000, 5000000),)
# M4-01B2: tên hạng mục chứa chuỗi giống thông điệp số học + KL 'abc' (phải CHẶN), cùng một dòng hợp lệ (dòng Excel 3) và một dòng lệch số học
# thật (dòng Excel 4: 10 × 20.000 ≠ 999 — chỉ là phát hiện)
BOQ_TEN_GIA_LOI = ((1, "HM-01", "Lót móng KL × ĐG = 1 khác thành tiền 1", "m3", "abc", 50000, 999),
                   (2, "HM-02", "Bê tông móng", "m3", 20, 1500000, 30000000),
                   (3, "HM-03", "Cốt thép", "kg", 10, 20000, 999))
MEDIA_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MEDIA_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_CONTENT_TYPES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                  '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                  '<Default Extension="xml" ContentType="application/xml"/>'
                  '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                  '</Types>')
_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
         '</Relationships>')


def _zip(parts: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for ten, noi_dung in parts.items():
            info = zipfile.ZipInfo(ten, date_time=(2026, 1, 1, 0, 0, 0))  # cố định để bytes xác định
            z.writestr(info, noi_dung)
    return buf.getvalue()


def hop_dong_docx(dong=DONG_HOP_DONG, *, track_changes: bool = False) -> bytes:
    """DOCX tối thiểu hợp lệ (content types + rels + document.xml). track_changes=True chèn một đoạn <w:ins> chưa chấp nhận."""
    doan = []
    for i, t in enumerate(dong):
        run = f'<w:r><w:t xml:space="preserve">{escape(t)}</w:t></w:r>'
        if track_changes and i == len(dong) - 1:
            run += ('<w:ins w:id="1" w:author="DEMO" w:date="2026-01-01T00:00:00Z"><w:r><w:t xml:space="preserve"> (sửa đổi DEMO)</w:t></w:r></w:ins>')
        doan.append(f"<w:p>{run}</w:p>")
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{_W}"><w:body>' + "".join(doan) + "</w:body></w:document>")
    return _zip({"[Content_Types].xml": _CONTENT_TYPES, "_rels/.rels": _RELS, "word/document.xml": doc})


def boq_xlsx(dong=BOQ_GOC, *, tieu_de=BOQ_TIEU_DE, sheet: str = "BOQ") -> bytes:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(list(tieu_de))
    for r in dong:
        ws.append(list(r))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def pdf_demo(nhan: str = "DEMO") -> bytes:
    return (b"%PDF-1.4\n% " + nhan.encode("ascii", "replace") + b"\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
