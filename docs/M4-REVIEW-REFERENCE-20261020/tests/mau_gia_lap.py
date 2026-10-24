# -*- coding: utf-8 -*-
"""
mau_gia_lap.py — Hợp đồng GIẢ LẬP (tên, số liệu hư cấu) + đáp án, dùng cho kiểm thử trong kho mã công khai.
    tao_hop_dong(thu_muc) → (đường dẫn .docx, đường dẫn DAP_AN_*.tsv)
    tao_docx(path, doan, theo_doi_sua=False)  — dựng .docx tối thiểu từ danh sách đoạn văn
"""
import os
import zipfile
from xml.sax.saxutils import escape

DOAN = [
    "HỢP ĐỒNG THI CÔNG XÂY DỰNG",
    "Số: 15/2026/HĐXD/MA-TN",
    "Gói thầu: Thi công đường nội bộ khu A",
    "Dự án: Khu dân cư Mẫu Thử",
    "Địa điểm: Xã Mẫu, Tỉnh Thử",
    "Hôm nay, ngày 10 tháng 02 năm 2026, chúng tôi gồm:",
    "BÊN GIAO THẦU (Bên A): Công ty Cổ phần Mẫu An",
    "Mã số thuế: 0101234567",
    "Điện thoại: 0912 345 678",
    "Đại diện: Ông Nguyễn Văn Thử",
    "BÊN NHẬN THẦU (Bên B): Công ty TNHH Xây dựng Thử Nghiệm",
    "Tài khoản số: 123456789012 tại Ngân hàng Mẫu",
    "Điều 1. Nội dung công việc",
    "1.1 Phạm vi công việc",
    "Bên B thi công xây dựng hoàn thiện đường nội bộ khu A theo hồ sơ thiết kế được duyệt.",
    "Điều 2. Giá hợp đồng",
    "2.1 Giá trị hợp đồng",
    "Giá trị hợp đồng là 5.000.000.000 đồng (đã bao gồm thuế VAT 8%).",
    "2.2 Loại hợp đồng",
    "Hợp đồng theo đơn giá cố định.",
    "2.3 Khối lượng thanh toán",
    "Khối lượng thanh toán theo khối lượng nghiệm thu thực tế.",
    "Điều 3. Tạm ứng",
    "3.1 Mức tạm ứng",
    "Bên A tạm ứng 15% giá trị hợp đồng sau khi ký.",
    "3.2 Thu hồi tạm ứng",
    "Thu hồi dần qua các đợt thanh toán, mỗi đợt 20% giá trị thanh toán đợt đó.",
    "3.3 Bảo lãnh tạm ứng",
    "Bên B nộp bảo lãnh tạm ứng bằng giá trị tạm ứng.",
    "Điều 4. Thanh toán",
    "4.1 Tỷ lệ thanh toán",
    "Mỗi đợt thanh toán 90% giá trị khối lượng hoàn thành được nghiệm thu.",
    "4.2 Giữ lại",
    "Giữ lại 10% giá trị khối lượng hoàn thành mỗi đợt.",
    "4.3 Thời hạn thanh toán",
    "Thanh toán trong vòng 15 ngày làm việc kể từ ngày Bên A nhận đủ hồ sơ hợp lệ.",
    "4.4 Hồ sơ thanh toán",
    "Hồ sơ thanh toán mỗi đợt gồm: biên bản nghiệm thu; bảng xác nhận khối lượng; hoá đơn VAT.",
    "4.5 Số lượng hồ sơ",
    "Bên B nộp 04 bộ hồ sơ thanh toán.",
    "Điều 5. Quyết toán và bảo hành",
    "5.1 Quyết toán",
    "Khi quyết toán Bên A thanh toán đến 95% giá trị quyết toán.",
    "5.2 Bảo hành",
    "Bảo hành công trình bằng 5% giá trị hợp đồng.",
    "5.3 Thời hạn bảo hành",
    "Thời hạn bảo hành là 12 tháng kể từ ngày nghiệm thu.",
    "5.4 Bảo lãnh thực hiện hợp đồng",
    "Bảo lãnh thực hiện hợp đồng bằng 10% giá trị hợp đồng.",
    "5.5 Hồ sơ quyết toán",
    "Hồ sơ quyết toán gồm: biên bản nghiệm thu hoàn thành; bảng tính giá trị quyết toán.",
    "Điều 6. Điều chỉnh giá hợp đồng",
    "6.1 Điều kiện điều chỉnh",
    "Điều chỉnh đơn giá khi giá vật liệu chính biến động trên 10% so với giá gốc.",
    "6.2 Khối lượng phát sinh",
    "Khối lượng phát sinh được hai bên lập phụ lục bổ sung.",
    "Điều 7. Tiến độ và phạt vi phạm",
    "7.1 Tiến độ thực hiện",
    "Thời gian thực hiện hợp đồng là 180 ngày kể từ ngày khởi công.",
    "7.2 Phạt vi phạm chất lượng",
    "Phạt vi phạm chất lượng tối đa 12% giá trị phần hợp đồng bị vi phạm.",
    "7.3 Chậm tiến độ giai đoạn",
    "Chậm tiến độ giai đoạn bị tạm giữ 0,1%/ngày trong 07 ngày đầu và 0,2%/ngày từ ngày thứ 08.",
    "7.4 Chậm tổng tiến độ",
    "Phạt chậm tổng tiến độ 0,15%/ngày tính trên giá trị phần chậm.",
    "7.5 Mức phạt tối đa",
    "Tổng mức phạt không quá 12% giá trị hợp đồng.",
    "7.6 Khấu trừ tiền phạt",
    "Tiền phạt được khấu trừ vào đợt thanh toán gần nhất.",
    "Điều 8. Hiệu lực hợp đồng",
    "8.1 Hiệu lực",
    "Hợp đồng có hiệu lực kể từ ngày ký.",
]

# mã, nhóm, tham số, giá trị, đơn vị, điều khoản, trích dẫn, ghi chú
DAP_AN = [
    ("TC-01", "Số hợp đồng", "15/2026/HĐXD/MA-TN", "", "Phần mở đầu", "Số: 15/2026/HĐXD/MA-TN", ""),
    ("TC-02", "Ngày ký", "10/02/2026", "", "Phần mở đầu", "Hôm nay, ngày 10 tháng 02 năm 2026, chúng tôi gồm:", ""),
    ("TC-03", "Gói thầu", "Thi công đường nội bộ khu A", "", "Phần mở đầu", "Gói thầu: Thi công đường nội bộ khu A", ""),
    ("TC-04", "Dự án", "Khu dân cư Mẫu Thử", "", "Phần mở đầu", "Dự án: Khu dân cư Mẫu Thử", ""),
    ("TC-05", "Địa điểm", "Xã Mẫu, Tỉnh Thử", "", "Phần mở đầu", "Địa điểm: Xã Mẫu, Tỉnh Thử", ""),
    ("TC-06", "Bên A", "Công ty Cổ phần Mẫu An", "", "Phần mở đầu", "BÊN GIAO THẦU (Bên A): Công ty Cổ phần Mẫu An", ""),
    ("TC-07", "Bên B", "Công ty TNHH Xây dựng Thử Nghiệm", "", "Phần mở đầu",
     "BÊN NHẬN THẦU (Bên B): Công ty TNHH Xây dựng Thử Nghiệm", ""),
    ("TC-08", "Hiệu lực", "Kể từ ngày ký", "", "Điều 8 – Khoản 8.1", "Hợp đồng có hiệu lực kể từ ngày ký.", ""),
    ("TC-09", "Loại HĐ", "Thi công xây dựng", "", "Điều 1 – Khoản 1.1",
     "Bên B thi công xây dựng hoàn thiện đường nội bộ khu A theo hồ sơ thiết kế được duyệt.", ""),
    ("TT-01", "Loại hợp đồng", "Đơn giá cố định", "", "Điều 2 – Khoản 2.2", "Hợp đồng theo đơn giá cố định.", ""),
    ("TT-02", "Giá trị HĐ", "5.000.000.000", "đồng", "Điều 2 – Khoản 2.1",
     "Giá trị hợp đồng là 5.000.000.000 đồng (đã bao gồm thuế VAT 8%).", ""),
    ("TT-03", "Gồm VAT", "Có", "", "Điều 2 – Khoản 2.1", "Giá trị hợp đồng là 5.000.000.000 đồng (đã bao gồm thuế VAT 8%).", ""),
    ("TT-04", "Thuế suất", "8", "%", "Điều 2 – Khoản 2.1", "Giá trị hợp đồng là 5.000.000.000 đồng (đã bao gồm thuế VAT 8%).", ""),
    ("TT-05", "Cơ sở TT", "KL nghiệm thu thực tế", "", "Điều 2 – Khoản 2.3",
     "Khối lượng thanh toán theo khối lượng nghiệm thu thực tế.", ""),
    ("TT-10", "Tạm ứng", "15", "%", "Điều 3 – Khoản 3.1", "Bên A tạm ứng 15% giá trị hợp đồng sau khi ký.", ""),
    ("TT-11", "Thu hồi", "Mỗi đợt 20% giá trị thanh toán đợt đó", "", "Điều 3 – Khoản 3.2",
     "Thu hồi dần qua các đợt thanh toán, mỗi đợt 20% giá trị thanh toán đợt đó.", ""),
    ("TT-12", "Bảo lãnh tạm ứng", "Bằng giá trị tạm ứng", "", "Điều 3 – Khoản 3.3",
     "Bên B nộp bảo lãnh tạm ứng bằng giá trị tạm ứng.", ""),
    ("TT-20", "Tỷ lệ TT", "90", "%", "Điều 4 – Khoản 4.1",
     "Mỗi đợt thanh toán 90% giá trị khối lượng hoàn thành được nghiệm thu.", ""),
    ("TT-21", "Giữ lại", "10", "%", "Điều 4 – Khoản 4.2", "Giữ lại 10% giá trị khối lượng hoàn thành mỗi đợt.", ""),
    ("TT-22", "Thời hạn TT", "15 ngày làm việc", "ngày", "Điều 4 – Khoản 4.3",
     "Thanh toán trong vòng 15 ngày làm việc kể từ ngày Bên A nhận đủ hồ sơ hợp lệ.", ""),
    ("TT-30", "Quyết toán", "95", "%", "Điều 5 – Khoản 5.1", "Khi quyết toán Bên A thanh toán đến 95% giá trị quyết toán.", ""),
    ("TT-31", "Bảo hành", "5", "%", "Điều 5 – Khoản 5.2", "Bảo hành công trình bằng 5% giá trị hợp đồng.", ""),
    ("TT-32", "Thời hạn BH", "12 tháng", "tháng", "Điều 5 – Khoản 5.3", "Thời hạn bảo hành là 12 tháng kể từ ngày nghiệm thu.", ""),
    ("TT-33", "BL thực hiện", "10% giá trị hợp đồng", "%", "Điều 5 – Khoản 5.4",
     "Bảo lãnh thực hiện hợp đồng bằng 10% giá trị hợp đồng.", ""),
    ("TT-40", "Điều chỉnh", "Giá vật liệu chính biến động trên 10% so với giá gốc", "", "Điều 6 – Khoản 6.1",
     "Điều chỉnh đơn giá khi giá vật liệu chính biến động trên 10% so với giá gốc.", ""),
    ("TT-41", "Ngưỡng", "10", "%", "Điều 6 – Khoản 6.1",
     "Điều chỉnh đơn giá khi giá vật liệu chính biến động trên 10% so với giá gốc.", ""),
    ("TT-42", "Phát sinh", "Hai bên lập phụ lục bổ sung", "", "Điều 6 – Khoản 6.2",
     "Khối lượng phát sinh được hai bên lập phụ lục bổ sung.", ""),
    ("TT-50", "Tiến độ", "180 ngày", "ngày", "Điều 7 – Khoản 7.1", "Thời gian thực hiện hợp đồng là 180 ngày kể từ ngày khởi công.", ""),
    ("TT-51", "Phạt chất lượng", "12", "%", "Điều 7 – Khoản 7.2",
     "Phạt vi phạm chất lượng tối đa 12% giá trị phần hợp đồng bị vi phạm.", ""),
    ("TT-52", "Mức 1", "0,1", "%/ngày", "Điều 7 – Khoản 7.3",
     "Chậm tiến độ giai đoạn bị tạm giữ 0,1%/ngày trong 07 ngày đầu và 0,2%/ngày từ ngày thứ 08.", ""),
    ("TT-53", "Mức 2", "0,2", "%/ngày", "Điều 7 – Khoản 7.3",
     "Chậm tiến độ giai đoạn bị tạm giữ 0,1%/ngày trong 07 ngày đầu và 0,2%/ngày từ ngày thứ 08.", ""),
    ("TT-54", "Phạt tổng tiến độ", "0,15", "%/ngày", "Điều 7 – Khoản 7.4",
     "Phạt chậm tổng tiến độ 0,15%/ngày tính trên giá trị phần chậm.", ""),
    ("TT-55", "Trần phạt", "12", "%", "Điều 7 – Khoản 7.5", "Tổng mức phạt không quá 12% giá trị hợp đồng.", ""),
    ("TT-56", "Khấu trừ phạt", "Khấu trừ vào đợt thanh toán gần nhất", "", "Điều 7 – Khoản 7.6",
     "Tiền phạt được khấu trừ vào đợt thanh toán gần nhất.", ""),
    ("TT-60", "Hồ sơ TT", "Biên bản nghiệm thu; bảng xác nhận khối lượng; hoá đơn VAT", "", "Điều 4 – Khoản 4.4",
     "Hồ sơ thanh toán mỗi đợt gồm: biên bản nghiệm thu; bảng xác nhận khối lượng; hoá đơn VAT.", ""),
    ("TT-61", "Hồ sơ QT", "Biên bản nghiệm thu hoàn thành; bảng tính giá trị quyết toán", "", "Điều 5 – Khoản 5.5",
     "Hồ sơ quyết toán gồm: biên bản nghiệm thu hoàn thành; bảng tính giá trị quyết toán.", ""),
    ("TT-62", "Số bộ", "04 bộ", "bộ", "Điều 4 – Khoản 4.5", "Bên B nộp 04 bộ hồ sơ thanh toán.", ""),
]

CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/word/document.xml" '
      'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>')
NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def p(text):
    return f'<w:p><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def tao_docx(path, doan_xml):
    """doan_xml: list chuỗi — đoạn văn bản thường (tự bọc <w:p>) hoặc XML đoạn bắt đầu bằng '<w:'."""
    body = "".join(x if x.startswith("<w:") else p(x) for x in doan_xml)
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {NS}><w:body>{body}</w:body></w:document>'
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", doc)
    return path


def tao_hop_dong(thu_muc, ten="HD_GIA_LAP"):
    os.makedirs(thu_muc, exist_ok=True)
    docx = tao_docx(os.path.join(thu_muc, f"{ten}.docx"), DOAN)
    tsv = os.path.join(thu_muc, f"DAP_AN_{ten}.tsv")
    with open(tsv, "w", encoding="utf-8") as f:
        f.write("Mã\tNhóm\tTham số\tGiá trị\tĐơn vị\tĐiều khoản\tTrích dẫn nguyên văn\tGhi chú\n")
        for ma, ts, v, dv, dk, q, gc in DAP_AN:
            f.write("\t".join([ma, "", ts, v, dv, dk, q, gc]) + "\n")
    return docx, tsv
