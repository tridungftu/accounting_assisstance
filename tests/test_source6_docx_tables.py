# -*- coding: utf-8 -*-
"""
test_source6_docx_tables.py — SOURCE6-E3-01: bằng chứng bảng thân văn bản Word (`bang_nguon`, schema source6-docx-tables/v1)
+ chặn ZIP/XML có giới hạn trong bản vá tools/source6_docx_tables/{doc_hop_dong,quy_trinh}.py.

TRẠNG THÁI: WRITTEN_NOT_RUN (tác giả không chạy; Root chạy sau khi dựng overlay đã ghim).

Cách chạy (Root): dựng OVERLAY = bản sao đóng băng docs/SOURCE6-E3-01-REFERENCE/source-actual/ (trich_xuat/, master_hd.py …) trong đó
trich_xuat/doc_hop_dong.py và trich_xuat/quy_trinh.py được THAY bằng đúng bytes hai artifact; đặt KTT_SOURCE6_E3_OVERLAY=<OVERLAY>;
chạy bằng chính trình thông dịch đã có guard khởi động A517:  python -B -X utf8 -m unittest tests.test_source6_docx_tables -v
Không -I/-E/-S/-s, không tiêm guard. Tệp này KHÔNG tạo tiến trình con; nếu sau này cần, tiến trình con phải dùng sys.executable với
cùng -B -X utf8 và kế thừa nguyên môi trường (để guard A517 khởi động gốc được kế thừa).

Nguyên tắc: fixture là XML/bytes TỔNG HỢP viết tay ngay trong tệp; giá trị mong đợi viết tay theo đặc tả (không lấy từ đầu ra làm "golden");
không skip; không import mã nguồn sống; không xoá gì (thư mục tạm được GIỮ làm bằng chứng); chỉ patch hằng nhỏ cho fixture biên.
Track Changes đi qua read_docx trực tiếp (read_contract sẽ gọi Word + rmtree — ngoài phạm vi kiểm thử này).
"""
import copy
import hashlib
import io
import itertools
import json
import os
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest import mock
from xml.sax.saxutils import escape

GOC = Path(__file__).resolve().parent.parent
ARTIFACT = GOC / "tools" / "source6_docx_tables"
THAM_CHIEU = GOC / "docs" / "SOURCE6-E3-01-REFERENCE"
NGUON_SONG = r"D:\Claude\Ho tro review ho so xay dung\review_xaydung"
TMP = tempfile.mkdtemp(prefix="test_source6_e3_")      # giữ lại làm bằng chứng — không xoá
_DEM = itertools.count(1)

dhd = qt = danh_muc = None                              # gán trong setUpModule từ OVERLAY đã kiểm


def _chuan(p):
    return os.path.normcase(os.path.realpath(os.path.abspath(str(p))))


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def setUpModule():
    global dhd, qt, danh_muc
    ov = os.environ.get("KTT_SOURCE6_E3_OVERLAY")
    if not ov:
        raise RuntimeError("Thiếu KTT_SOURCE6_E3_OVERLAY (overlay đóng băng + hai artifact) — không skip, không tự tìm nguồn")
    ov, song = _chuan(ov), _chuan(NGUON_SONG)
    if ov == song or ov.startswith(song + os.sep) or song.startswith(ov + os.sep):
        raise RuntimeError("OVERLAY trỏ vào/bao nguồn sống — cấm")
    for ten in ("doc_hop_dong.py", "quy_trinh.py"):
        if (Path(ov) / "trich_xuat" / ten).read_bytes() != (ARTIFACT / ten).read_bytes():
            raise RuntimeError(f"OVERLAY trich_xuat/{ten} khác bytes artifact tools/source6_docx_tables/{ten}")
    ghim = {x["id"]: x for x in json.loads((THAM_CHIEU / "INPUT-PINS-01.json").read_text(encoding="utf-8"))["inputs"]}
    for ma, ten in (("baseline-doc_hop_dong", "doc_hop_dong.py"), ("baseline-quy_trinh", "quy_trinh.py")):
        b = (THAM_CHIEU / "source-actual" / "trich_xuat" / ten).read_bytes()
        if (_sha(b), len(b)) != (ghim[ma]["sha256"], ghim[ma]["bytes"]):
            raise RuntimeError(f"Bản tham chiếu {ten} lệch ghim {ma}")
    goc_tc = THAM_CHIEU / "source-actual"
    for p in list((goc_tc / "trich_xuat").iterdir()) + [goc_tc / "master_hd.py"]:
        if p.is_file() and p.name not in ("doc_hop_dong.py", "quy_trinh.py"):
            if (Path(ov) / p.relative_to(goc_tc)).read_bytes() != p.read_bytes():
                raise RuntimeError(f"OVERLAY {p.relative_to(goc_tc)} khác bản tham chiếu đóng băng")
    for m in ("trich_xuat", "master_hd"):
        if m in sys.modules:
            raise RuntimeError(f"{m} đã được import trước overlay — chạy trong tiến trình sạch")
    os.environ.update(HD_DU_LIEU=os.path.join(TMP, "du_lieu"), HD_OUT_DIR=os.path.join(TMP, "du_lieu", "ket_qua"),
                      HD_DANH_MUC_HD=os.path.join(TMP, "du_lieu", "danh_muc_hd"),
                      HD_CSDL=os.path.join(TMP, "du_lieu", "hop_dong.db"), HD_THU_MUC_KHOA=os.path.join(TMP, "khoa"))
    for k in ("OLLAMA_URL", "AI_MODEL", "HD_RA_LAI", "HD_CLOUD", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        os.environ.pop(k, None)
    sys.path.insert(0, ov)
    import trich_xuat.danh_muc as _dm
    import trich_xuat.doc_hop_dong as _dhd
    import trich_xuat.quy_trinh as _qt
    for m in (_dhd, _qt, _dm):
        if not _chuan(m.__file__).startswith(ov + os.sep):
            raise RuntimeError(f"{m.__name__} không nạp từ OVERLAY: {m.__file__}")
    dhd, qt, danh_muc = _dhd, _qt, _dm


# ================================================================== fixture tổng hợp (viết tay)
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = f'xmlns:w="{W_NS}"'
NS_V = ' xmlns:v="urn:schemas-microsoft-com:vml"'
NS_MC = ' xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"'
KHAI_BAO = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/word/document.xml" '
      'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>').encode("utf-8")
RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>').encode("utf-8")
REV = 'w:id="{}" w:author="Gia lap" w:date="2026-01-01T00:00:00Z"'
B = "/w:document[1]/w:body[1]"
GH = {"tep": 62914560, "so_member": 400, "member": 31457280, "tong": 125829120, "ty_le": 120, "ty_le_tu": 1048576,
      "do_sau_xml": 128, "so_bang": 200, "so_dong": 10000, "so_o": 100000, "ky_tu_o": 20000, "json_bang_nguon": 2097152}

# Hợp đồng XD giả lập (tên/số liệu hư cấu, cùng nội dung mẫu với tests/mau_gia_lap.DOAN của nguồn) — 8 Điều
DOAN_XD = [
    "HỢP ĐỒNG THI CÔNG XÂY DỰNG", "Số: 15/2026/HĐXD/MA-TN", "Gói thầu: Thi công đường nội bộ khu A", "Dự án: Khu dân cư Mẫu Thử",
    "Địa điểm: Xã Mẫu, Tỉnh Thử", "Hôm nay, ngày 10 tháng 02 năm 2026, chúng tôi gồm:", "BÊN GIAO THẦU (Bên A): Công ty Cổ phần Mẫu An",
    "Mã số thuế: 0101234567", "Điện thoại: 0912 345 678", "Đại diện: Ông Nguyễn Văn Thử",
    "BÊN NHẬN THẦU (Bên B): Công ty TNHH Xây dựng Thử Nghiệm", "Tài khoản số: 123456789012 tại Ngân hàng Mẫu",
    "Điều 1. Nội dung công việc", "1.1 Phạm vi công việc",
    "Bên B thi công xây dựng hoàn thiện đường nội bộ khu A theo hồ sơ thiết kế được duyệt.",
    "Điều 2. Giá hợp đồng", "2.1 Giá trị hợp đồng", "Giá trị hợp đồng là 5.000.000.000 đồng (đã bao gồm thuế VAT 8%).",
    "2.2 Loại hợp đồng", "Hợp đồng theo đơn giá cố định.", "2.3 Khối lượng thanh toán",
    "Khối lượng thanh toán theo khối lượng nghiệm thu thực tế.",
    "Điều 3. Tạm ứng", "3.1 Mức tạm ứng", "Bên A tạm ứng 15% giá trị hợp đồng sau khi ký.", "3.2 Thu hồi tạm ứng",
    "Thu hồi dần qua các đợt thanh toán, mỗi đợt 20% giá trị thanh toán đợt đó.", "3.3 Bảo lãnh tạm ứng",
    "Bên B nộp bảo lãnh tạm ứng bằng giá trị tạm ứng.",
    "Điều 4. Thanh toán", "4.1 Tỷ lệ thanh toán", "Mỗi đợt thanh toán 90% giá trị khối lượng hoàn thành được nghiệm thu.",
    "4.2 Giữ lại", "Giữ lại 10% giá trị khối lượng hoàn thành mỗi đợt.", "4.3 Thời hạn thanh toán",
    "Thanh toán trong vòng 15 ngày làm việc kể từ ngày Bên A nhận đủ hồ sơ hợp lệ.", "4.4 Hồ sơ thanh toán",
    "Hồ sơ thanh toán mỗi đợt gồm: biên bản nghiệm thu; bảng xác nhận khối lượng; hoá đơn VAT.", "4.5 Số lượng hồ sơ",
    "Bên B nộp 04 bộ hồ sơ thanh toán.",
    "Điều 5. Quyết toán và bảo hành", "5.1 Quyết toán", "Khi quyết toán Bên A thanh toán đến 95% giá trị quyết toán.",
    "5.2 Bảo hành", "Bảo hành công trình bằng 5% giá trị hợp đồng.", "5.3 Thời hạn bảo hành",
    "Thời hạn bảo hành là 12 tháng kể từ ngày nghiệm thu.", "5.4 Bảo lãnh thực hiện hợp đồng",
    "Bảo lãnh thực hiện hợp đồng bằng 10% giá trị hợp đồng.", "5.5 Hồ sơ quyết toán",
    "Hồ sơ quyết toán gồm: biên bản nghiệm thu hoàn thành; bảng tính giá trị quyết toán.",
    "Điều 6. Điều chỉnh giá hợp đồng", "6.1 Điều kiện điều chỉnh",
    "Điều chỉnh đơn giá khi giá vật liệu chính biến động trên 10% so với giá gốc.", "6.2 Khối lượng phát sinh",
    "Khối lượng phát sinh được hai bên lập phụ lục bổ sung.",
    "Điều 7. Tiến độ và phạt vi phạm", "7.1 Tiến độ thực hiện", "Thời gian thực hiện hợp đồng là 180 ngày kể từ ngày khởi công.",
    "7.2 Phạt vi phạm chất lượng", "Phạt vi phạm chất lượng tối đa 12% giá trị phần hợp đồng bị vi phạm.",
    "7.3 Chậm tiến độ giai đoạn", "Chậm tiến độ giai đoạn bị tạm giữ 0,1%/ngày trong 07 ngày đầu và 0,2%/ngày từ ngày thứ 08.",
    "7.4 Chậm tổng tiến độ", "Phạt chậm tổng tiến độ 0,15%/ngày tính trên giá trị phần chậm.", "7.5 Mức phạt tối đa",
    "Tổng mức phạt không quá 12% giá trị hợp đồng.", "7.6 Khấu trừ tiền phạt", "Tiền phạt được khấu trừ vào đợt thanh toán gần nhất.",
    "Điều 8. Hiệu lực hợp đồng", "8.1 Hiệu lực", "Hợp đồng có hiệu lực kể từ ngày ký.",
]


def p(t=""):
    return f'<w:p><w:r><w:t xml:space="preserve">{escape(t)}</w:t></w:r></w:p>' if t else "<w:p/>"


def tc(*noi, pr=""):
    than = "".join(x if x.startswith("<") else p(x) for x in noi) or "<w:p/>"
    return f"<w:tc>{f'<w:tcPr>{pr}</w:tcPr>' if pr else ''}{than}</w:tc>"


def tr(*o, pr=""):
    return f"<w:tr>{f'<w:trPr>{pr}</w:trPr>' if pr else ''}{''.join(o)}</w:tr>"


def tbl(*dong, cot=None):
    luoi = ("<w:tblGrid>" + '<w:gridCol w:w="1000"/>' * cot + "</w:tblGrid>") if cot else ""
    return f"<w:tbl><w:tblPr/>{luoi}{''.join(dong)}</w:tbl>"


def tai_lieu(than, ns_them="", khai_bao=KHAI_BAO):
    return f"{khai_bao}<w:document {NS}{ns_them}><w:body>{than}</w:body></w:document>".encode("utf-8")


def goi(phan, nen=zipfile.ZIP_DEFLATED):
    """phan: [(tên, bytes) | (tên, bytes, kiểu nén)] → bytes ZIP tất định (ngày giờ cố định)."""
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for x in phan:
            zi = zipfile.ZipInfo(x[0], date_time=(2026, 1, 1, 0, 0, 0))
            zi.compress_type = x[2] if len(x) > 2 else nen
            z.writestr(zi, x[1])
    return b.getvalue()


def phan_docx(doc, numbering=None, them=()):
    ph = [("[Content_Types].xml", CT), ("_rels/.rels", RELS), ("word/document.xml", doc)]
    if numbering is not None:
        ph.append(("word/numbering.xml", numbering))
    return ph + list(them)


def ghi(ten, data):
    """Tệp MỚI trong TMP (mở 'xb' — không bao giờ ghi đè/xoá)."""
    path = os.path.join(TMP, f"{next(_DEM):03d}_{ten}")
    with open(path, "xb") as f:
        f.write(data)
    return path


def lam(than, ten="hd.docx", ns_them="", numbering=None, them=()):
    """→ (đường dẫn .docx, bytes document.xml, bytes tệp)."""
    doc = tai_lieu(than, ns_them)
    data = goi(phan_docx(doc, numbering, them))
    return ghi(ten, data), doc, data


def ma_id(doc, loai, path):
    """Công thức định danh theo đặc tả: '<loai>-' + 32 hex đầu SHA-256('<sha document.xml>:<loai>:<vi_tri>')."""
    return f"{loai}-" + _sha(f"{_sha(doc)}:{loai}:{path}".encode("utf-8"))[:32]


def o_(doc, path, thu_tu, gs, doan=(), span=1, vm="NONE", con=()):
    return {"id": ma_id(doc, "o", path), "vi_tri": path, "thu_tu_nguon": thu_tu, "grid_start": gs, "grid_span": span,
            "v_merge": vm, "text": "\n".join(doan), "doan": list(doan), "bang_con": list(con)}


def dong_(doc, path, thu_tu, o, gb=0, ga=0):
    return {"id": ma_id(doc, "dong", path), "vi_tri": path, "thu_tu_nguon": thu_tu, "grid_before": gb, "grid_after": ga, "o": o}


def bang_(doc, path, thu_tu, cot, dong, cha=None):
    return {"id": ma_id(doc, "bang", path), "vi_tri": path, "parent_cell_id": cha, "thu_tu_nguon": thu_tu, "grid_cols": cot,
            "dong": dong}


def dto(data, doc, bang, trang_thai="DAY_DU", kieu="TRUC_TIEP", so_sua=0, ly_do=(), gh=None):
    return {"schema": "source6-docx-tables/v1", "trang_thai": trang_thai, "pham_vi": "WORD_DOCUMENT_BODY_TABLES",
            "nguon": {"source_sha256": _sha(data), "source_bytes": len(data), "docx_sha256": _sha(data), "docx_bytes": len(data),
                      "document_xml_sha256": _sha(doc)},
            "bien_doi": {"kieu": kieu, "track_changes": so_sua}, "gioi_han": dict(gh or GH), "ly_do": list(ly_do), "bang": bang}


def json_gon(o):
    return len(json.dumps(o, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _cd(data, ten):
    """Vị trí bản ghi central directory của member `ten` (đọc cấu trúc ZIP thật, không đoán)."""
    i = data.find(b"PK\x01\x02")
    while i >= 0:
        n, m, k = (int.from_bytes(data[i + a:i + a + 2], "little") for a in (28, 30, 32))
        if data[i + 46:i + 46 + n] == ten.encode("ascii"):
            return i
        i = data.find(b"PK\x01\x02", i + 46 + n + m + k)
    raise AssertionError(f"không thấy central directory của {ten}")


def _va(data, vi_tri, gia_tri):
    return data[:vi_tri] + gia_tri + data[vi_tri + len(gia_tri):]


class _Co(unittest.TestCase):
    def loi(self, ma, ham, *a):
        with self.assertRaises(dhd.LoiE3) as cm:
            ham(*a)
        self.assertIsInstance(cm.exception, ValueError)
        self.assertEqual(cm.exception.ma, ma, str(cm.exception))
        self.assertTrue(str(cm.exception).startswith(ma + ": "), str(cm.exception))

    def loi_ca_hai(self, ma, path):
        """Cả read_contract (đường chính) và read_docx (đường gọi trực tiếp, vd chung_tu) cùng từ chối, cùng mã."""
        for ham in (dhd.read_contract, dhd.read_docx):
            with self.subTest(ham=ham.__name__):
                self.loi(ma, ham, path)

    def bn(self, path):
        return dhd.read_contract(path)["bang_nguon"]

    def bn_docx(self, path):
        text, st = dhd.read_docx(path)
        return text, st["_bang_nguon"], st


# ================================================================== bằng chứng bảng: nội dung/lưới/lồng
class BangChungTests(_Co):
    def test_dong_lap_o_rong_so_0_va_vi_tri(self):
        than = p("Trước") + tbl(tr(tc("A"), tc("0")), tr(tc("A"), tc("0")), tr(tc(), tc()), tr(), cot=2)
        path, doc, data = lam(than)
        T = B + "/w:tbl[1]"
        mong = dto(data, doc, [bang_(doc, T, 1, 2, [
            dong_(doc, T + "/w:tr[1]", 1, [o_(doc, T + "/w:tr[1]/w:tc[1]", 1, 1, ["A"]), o_(doc, T + "/w:tr[1]/w:tc[2]", 2, 2, ["0"])]),
            dong_(doc, T + "/w:tr[2]", 2, [o_(doc, T + "/w:tr[2]/w:tc[1]", 1, 1, ["A"]), o_(doc, T + "/w:tr[2]/w:tc[2]", 2, 2, ["0"])]),
            dong_(doc, T + "/w:tr[3]", 3, [o_(doc, T + "/w:tr[3]/w:tc[1]", 1, 1), o_(doc, T + "/w:tr[3]/w:tc[2]", 2, 2)]),
            dong_(doc, T + "/w:tr[4]", 4, []),
        ])])
        info = dhd.read_contract(path)
        self.assertEqual(info["bang_nguon"], mong)
        d = info["bang_nguon"]["bang"][0]["dong"]
        self.assertNotEqual(d[0]["id"], d[1]["id"])                       # dòng lặp y hệt vẫn hai bản ghi khác định danh
        self.assertEqual((d[0]["o"][1]["text"], d[2]["o"][0]["text"], d[2]["o"][0]["doan"]), ("0", "", []))
        self.assertEqual(info["text"], "Trước\nA | 0\nA | 0")              # văn bản kiểu cũ giữ nguyên
        self.assertEqual(info["report"]["tables"], 1)

    def test_gridbefore_after_span_vmerge_khong_dien(self):
        than = tbl(tr(tc("Gộp ngang", pr='<w:gridSpan w:val="2"/>'), pr='<w:gridBefore w:val="1"/><w:gridAfter w:val="1"/>'),
                   tr(tc("Gộp dọc", pr='<w:vMerge w:val="restart"/>'), tc("B", pr='<w:gridSpan w:val="3"/>')),
                   tr(tc(pr="<w:vMerge/>"), tc("C", pr='<w:gridSpan w:val="3"/>')),
                   tr(tc(pr='<w:vMerge w:val="continue"/>'), tc("D", pr='<w:gridSpan w:val="3"/>')), cot=4)
        path, doc, data = lam(than)
        T = B + "/w:tbl[1]"
        mong = dto(data, doc, [bang_(doc, T, 1, 4, [
            dong_(doc, T + "/w:tr[1]", 1, [o_(doc, T + "/w:tr[1]/w:tc[1]", 1, 2, ["Gộp ngang"], span=2)], gb=1, ga=1),
            dong_(doc, T + "/w:tr[2]", 2, [o_(doc, T + "/w:tr[2]/w:tc[1]", 1, 1, ["Gộp dọc"], vm="RESTART"),
                                           o_(doc, T + "/w:tr[2]/w:tc[2]", 2, 2, ["B"], span=3)]),
            dong_(doc, T + "/w:tr[3]", 3, [o_(doc, T + "/w:tr[3]/w:tc[1]", 1, 1, [], vm="CONTINUE"),
                                           o_(doc, T + "/w:tr[3]/w:tc[2]", 2, 2, ["C"], span=3)]),
            dong_(doc, T + "/w:tr[4]", 4, [o_(doc, T + "/w:tr[4]/w:tc[1]", 1, 1, [], vm="CONTINUE"),
                                           o_(doc, T + "/w:tr[4]/w:tc[2]", 2, 2, ["D"], span=3)]),
        ])])
        info = dhd.read_contract(path)
        self.assertEqual(info["bang_nguon"], mong)                        # CONTINUE giữ "" — không chép "Gộp dọc" xuống
        self.assertEqual(info["text"], "Gộp ngang\nGộp dọc | B\nC\nD")

    def test_bang_long_lien_ket_o_cha_khong_lap_chu(self):
        trong = tbl(tr(tc("N1")), tr(tc("N2")), cot=1)
        ngoai = tbl(tr(f"<w:tc>{p('Ngoài')}{trong}{p('Sau')}</w:tc>", tc("X")), cot=2)
        path, doc, data = lam(ngoai + p("Giữa") + tbl(tr(tc("Bảng 2")), cot=1))
        T1 = B + "/w:tbl[1]"
        C11 = T1 + "/w:tr[1]/w:tc[1]"
        T2, T3 = C11 + "/w:tbl[1]", B + "/w:tbl[2]"
        mong = dto(data, doc, [
            bang_(doc, T1, 1, 2, [dong_(doc, T1 + "/w:tr[1]", 1, [
                o_(doc, C11, 1, 1, ["Ngoài", "Sau"], con=[ma_id(doc, "bang", T2)]), o_(doc, T1 + "/w:tr[1]/w:tc[2]", 2, 2, ["X"])])]),
            bang_(doc, T2, 2, 1, [dong_(doc, T2 + "/w:tr[1]", 1, [o_(doc, T2 + "/w:tr[1]/w:tc[1]", 1, 1, ["N1"])]),
                                  dong_(doc, T2 + "/w:tr[2]", 2, [o_(doc, T2 + "/w:tr[2]/w:tc[1]", 1, 1, ["N2"])])],
                  cha=ma_id(doc, "o", C11)),
            bang_(doc, T3, 3, 1, [dong_(doc, T3 + "/w:tr[1]", 1, [o_(doc, T3 + "/w:tr[1]/w:tc[1]", 1, 1, ["Bảng 2"])])]),
        ])
        info = dhd.read_contract(path)
        self.assertEqual(info["bang_nguon"], mong)
        self.assertEqual(info["text"], "Ngoài N1 N2 Sau | X\nGiữa\nBảng 2")    # văn bản cũ (gộp chữ bảng lồng) giữ nguyên
        self.assertEqual(info["report"]["tables"], 2)

    def test_bang_trong_sdt_than_van_ban(self):
        path, doc, data = lam(f"<w:sdt><w:sdtPr/><w:sdtContent>{tbl(tr(tc('Trong sdt')), cot=1)}</w:sdtContent></w:sdt>")
        T = B + "/w:sdt[1]/w:sdtContent[1]/w:tbl[1]"
        self.assertEqual(self.bn(path), dto(data, doc, [bang_(doc, T, 1, 1, [
            dong_(doc, T + "/w:tr[1]", 1, [o_(doc, T + "/w:tr[1]/w:tc[1]", 1, 1, ["Trong sdt"])])])]))

    def test_khong_co_bang_day_du_rong(self):
        path, doc, data = lam(p("Chỉ có chữ"))
        self.assertEqual(self.bn(path), dto(data, doc, []))

    def test_dinh_danh_on_dinh_va_doi_theo_bytes(self):
        than = tbl(tr(tc("Cố định")), cot=1)
        doc = tai_lieu(than)
        data = goi(phan_docx(doc))
        a, b = self.bn(ghi("a.docx", data)), self.bn(ghi("b.docx", data))
        self.assertEqual(a, b)                                              # cùng bytes → cùng DTO, cùng định danh
        doc2 = tai_lieu(tbl(tr(tc("Cố định!")), cot=1))
        c = self.bn(ghi("c.docx", goi(phan_docx(doc2))))
        self.assertNotEqual(c["nguon"]["document_xml_sha256"], a["nguon"]["document_xml_sha256"])
        self.assertEqual(c["bang"][0]["vi_tri"], a["bang"][0]["vi_tri"])
        for x, y in ((a["bang"][0], c["bang"][0]), (a["bang"][0]["dong"][0], c["bang"][0]["dong"][0]),
                     (a["bang"][0]["dong"][0]["o"][0], c["bang"][0]["dong"][0]["o"][0])):
            self.assertNotEqual(x["id"], y["id"])                           # định danh theo không gian tên SHA document.xml
        self.assertEqual(a["bang"][0]["id"], ma_id(doc, "bang", B + "/w:tbl[1]"))

    def test_so_tu_dong_khong_goi_lai_label(self):
        num = (f'{KHAI_BAO}<w:numbering {NS}><w:abstractNum w:abstractNumId="0">'
               '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="Điều %1."/></w:lvl>'
               '<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1.%2"/></w:lvl>'
               '</w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>').encode("utf-8")

        def pn(il, t):
            return (f'<w:p><w:pPr><w:numPr><w:ilvl w:val="{il}"/><w:numId w:val="1"/></w:numPr></w:pPr>'
                    f'<w:r><w:t>{escape(t)}</w:t></w:r></w:p>')
        than = pn(0, "Giá hợp đồng") + pn(1, "Giá trị tạm tính") + tbl(tr(tc(pn(1, "Hạng mục")), tc("100")), cot=2) \
            + pn(0, "Tạm ứng") + pn(1, "Mức tạm ứng")
        path, doc, data = lam(than, numbering=num)
        goc = dhd.Numbering.label
        with mock.patch.object(dhd.Numbering, "label", autospec=True, side_effect=goc) as m:
            text, bn, st = self.bn_docx(path)
        self.assertEqual(text, "Điều 1. Giá hợp đồng\n1.1 Giá trị tạm tính\n1.2 Hạng mục | 100\nĐiều 2. Tạm ứng\n2.1 Mức tạm ứng")
        self.assertEqual(st["numbered"], 4)
        self.assertEqual(m.call_count, 6)                                   # 4 đoạn thân + 2 đoạn trong ô: chỉ lượt văn bản cũ
        T = B + "/w:tbl[1]"
        self.assertEqual(bn, dto(data, doc, [bang_(doc, T, 1, 2, [dong_(doc, T + "/w:tr[1]", 1, [
            o_(doc, T + "/w:tr[1]/w:tc[1]", 1, 1, ["Hạng mục"]), o_(doc, T + "/w:tr[1]/w:tc[2]", 2, 2, ["100"])])])]))


# ================================================================== Track Changes (read_docx trực tiếp — không Word/rmtree)
class SuaDoiTests(_Co):
    def test_chap_nhan_xml_dong_xoa_va_bang_xoa_la_khoang_trong(self):
        t1 = tbl(tr(tc("Giữ")),
                 tr(f'<w:tc><w:p><w:del {REV.format(1)}><w:r><w:delText>Bỏ</w:delText></w:r></w:del></w:p></w:tc>',
                    pr=f"<w:del {REV.format(2)}/>"),
                 tr(f'<w:tc><w:p><w:ins {REV.format(3)}><w:r><w:t>Mới</w:t></w:r></w:ins></w:p></w:tc>'), cot=1)
        t2 = tbl(tr(tc("Xoá cả bảng"), pr=f"<w:del {REV.format(4)}/>"), cot=1)
        t3 = tbl(tr(tc("Sau xoá")), cot=1)
        path, doc, data = lam(t1 + p("Giữa") + t2 + t3)
        text, bn, st = self.bn_docx(path)
        T1, T3 = B + "/w:tbl[1]", B + "/w:tbl[3]"
        self.assertEqual(bn, dto(data, doc, [
            bang_(doc, T1, 1, 1, [dong_(doc, T1 + "/w:tr[1]", 1, [o_(doc, T1 + "/w:tr[1]/w:tc[1]", 1, 1, ["Giữ"])]),
                                  dong_(doc, T1 + "/w:tr[3]", 3, [o_(doc, T1 + "/w:tr[3]/w:tc[1]", 1, 1, ["Mới"])])]),
            bang_(doc, T3, 3, 1, [dong_(doc, T3 + "/w:tr[1]", 1, [o_(doc, T3 + "/w:tr[1]/w:tc[1]", 1, 1, ["Sau xoá"])])]),
        ], kieu="ACCEPT_XML", so_sua=4))
        self.assertEqual(text, "Giữ\nMới\nGiữa\nSau xoá")
        self.assertEqual((st["tables"], st["track_changes"]), (3, 4))

    def test_bang_trong_movefrom_chua_du(self):
        path, doc, data = lam(f"<w:moveFrom {REV.format(1)}>{tbl(tr(tc('Chuyển')), cot=1)}</w:moveFrom>" + p("Sau"))
        text, bn, _ = self.bn_docx(path)
        self.assertEqual(bn, dto(data, doc, [], "INCOMPLETE", "ACCEPT_XML", 1,
                                 [{"ma": "E3_SUA_DOI_BANG_KHONG_HO_TRO", "vi_tri": B + "/w:moveFrom[1]/w:tbl[1]"}]))
        self.assertEqual(text, "Sau")

    def test_dong_xoa_khong_truc_tiep_trong_bang_chua_du(self):
        T = B + "/w:tbl[1]"
        than = (f'<w:tbl><w:tblPr/><w:tblGrid><w:gridCol w:w="1000"/></w:tblGrid>{tr(tc("Giữ"))}<w:sdt><w:sdtContent>'
                f'{tr(tc("Xoá"), pr=f"<w:del {REV.format(1)}/>")}</w:sdtContent></w:sdt></w:tbl>')
        path, doc, data = lam(than)
        text, bn, _ = self.bn_docx(path)
        self.assertEqual(bn, dto(data, doc, [], "INCOMPLETE", "ACCEPT_XML", 1,
                                 [{"ma": "E3_SUA_DOI_BANG_KHONG_HO_TRO", "vi_tri": T + "/w:sdt[1]/w:sdtContent[1]/w:tr[1]"}]))
        self.assertEqual(text, "Giữ")


# ================================================================== INCOMPLETE: cấu trúc không chắc chắn (văn bản cũ giữ nguyên)
class ChuaDuTests(_Co):
    T = B + "/w:tbl[1]"
    O = T + "/w:tr[1]/w:tc[1]"
    CA = [
        # (tên, thân, ns thêm, mã, vị trí, văn bản cũ)
        ("cellDel", tbl(tr(tc("Ô", pr=f"<w:cellDel {REV.format(1)}/>")), cot=1), "", "E3_SUA_DOI_O_KHONG_HO_TRO",
         O + "/w:tcPr[1]/w:cellDel[1]", "Ô"),
        ("textbox", tbl(tr('<w:tc><w:p><w:r><w:pict><v:shape><v:textbox><w:txbxContent>' + p("Hộp")
                           + '</w:txbxContent></v:textbox></v:shape></w:pict></w:r></w:p></w:tc>'), cot=1), NS_V,
         "E3_HOP_VAN_BAN_TRONG_O", O, "Hộp Hộp"),
        ("altChunk_o", tbl(tr(f"<w:tc><w:altChunk/>{p('Có')}</w:tc>"), cot=1), "", "E3_ALTCHUNK", O, "Có"),
        ("altChunk_than", tbl(tr(tc("A")), cot=1) + "<w:altChunk/>", "", "E3_ALTCHUNK", B, "A"),
        ("mc", p("Trước") + f'<mc:AlternateContent><mc:Choice Requires="w14">{tbl(tr(tc("Ẩn")), cot=1)}</mc:Choice>'
         "<mc:Fallback/></mc:AlternateContent>", NS_MC, "E3_BANG_TRONG_VO_KHONG_HO_TRO", B, "Trước"),
        ("gridSpan_hong", tbl(tr(tc("A", pr='<w:gridSpan w:val="x2"/>')), cot=2), "", "E3_LUOI_KHONG_HOP_LE", O, "A"),
        ("gridSpan_0", tbl(tr(tc("A", pr='<w:gridSpan w:val="0"/>')), cot=2), "", "E3_LUOI_KHONG_HOP_LE", O, "A"),
        ("continue_mo_coi", tbl(tr(tc("A", pr="<w:vMerge/>")), cot=1), "", "E3_VMERGE_MAU_THUAN", O, "A"),
        ("continue_lech_span", tbl(tr(tc("A", pr='<w:vMerge w:val="restart"/>'), tc("B")),
                                   tr(tc(pr='<w:vMerge/><w:gridSpan w:val="2"/>')), cot=2), "", "E3_VMERGE_MAU_THUAN",
         T + "/w:tr[2]/w:tc[1]", "A | B"),
        ("vMerge_la", tbl(tr(tc("A", pr='<w:vMerge w:val="foo"/>')), cot=1), "", "E3_VMERGE_KHONG_HOP_LE", O, "A"),
        ("tran_luoi", tbl(tr(tc("A"), tc("B")), cot=1), "", "E3_LUOI_MAU_THUAN", T + "/w:tr[1]", "A | B"),
        ("hMerge", tbl(tr(tc("A", pr='<w:hMerge w:val="restart"/>')), cot=1), "", "E3_HMERGE_KHONG_HO_TRO", O, "A"),
        ("tcPr_trung", tbl(tr(f"<w:tc><w:tcPr/><w:tcPr/>{p('A')}</w:tc>"), cot=1), "", "E3_LUOI_MAU_THUAN", O, "A"),
        ("bang_khong_dong", tbl(cot=1) + p("Sau"), "", "E3_BANG_KHONG_DONG", T, "Sau"),
        ("o_trong_vo_la", tbl(f"<w:tr><w:customXml>{tc('A')}</w:customXml></w:tr>", cot=1), "", "E3_PHAN_TU_KHONG_HO_TRO",
         T + "/w:tr[1]", ""),
        ("tien_to_khac", tbl(tr(f'<w:tc><w:p><x:ins x:id="1" x:author="a" x:date="2026-01-01T00:00:00Z"><w:r><w:t>Chèn</w:t>'
                                "</w:r></x:ins></w:p></w:tc>"), cot=1), f' xmlns:x="{W_NS}"', "E3_SUA_DOI_CHUA_CHAP_NHAN", B, "Chèn"),
    ]

    def test_cac_ca_chua_du(self):
        for ten, than, ns, ma, vt, van_ban in self.CA:
            with self.subTest(ca=ten):
                path, doc, data = lam(than, ten=f"{ten}.docx", ns_them=ns)
                info = dhd.read_contract(path)                              # không ca nào có '<w:ins '/'<w:del ' → không gọi Word
                self.assertEqual(info["bang_nguon"], dto(data, doc, [], "INCOMPLETE", ly_do=[{"ma": ma, "vi_tri": vt}]))
                self.assertEqual(info["text"], van_ban)                     # văn bản/vô hướng kiểu cũ không đổi

    def test_document_khong_ho_tro_bao_loi(self):
        strict = (f'{KHAI_BAO}<w:document xmlns:w="http://purl.oclc.org/ooxml/wordprocessingml/main"><w:body>{p("A")}'
                  "</w:body></w:document>").encode("utf-8")
        thieu_body = f"{KHAI_BAO}<w:document {NS}/>".encode("utf-8")
        for ten, doc in (("strict", strict), ("thieu_body", thieu_body)):
            with self.subTest(ca=ten):
                self.loi_ca_hai("E3_XML_KHONG_HO_TRO", ghi(f"{ten}.docx", goi(phan_docx(doc))))


# ================================================================== giới hạn bằng chứng (patch hằng nhỏ cho fixture biên)
class GioiHanBangChungTests(_Co):
    def bien(self, than, khoa, gia_tri, ma, vt):
        path, doc, data = lam(than, ten=f"{khoa}.docx")
        with mock.patch.dict(dhd.E3_GIOI_HAN, {khoa: gia_tri}):
            dat = self.bn(path)
        with mock.patch.dict(dhd.E3_GIOI_HAN, {khoa: gia_tri - 1}):
            vuot = self.bn(path)
        self.assertEqual(dat["trang_thai"], "DAY_DU", dat["ly_do"])
        self.assertEqual(dat["gioi_han"][khoa], gia_tri)
        self.assertEqual(vuot, dto(data, doc, [], "INCOMPLETE", ly_do=[{"ma": ma, "vi_tri": vt}], gh=dict(GH, **{khoa: gia_tri - 1})))
        return dat

    def test_so_bang(self):
        dat = self.bien("".join(tbl(tr(tc(f"B{i}")), cot=1) for i in (1, 2, 3)), "so_bang", 3, "E3_QUA_SO_BANG", B + "/w:tbl[3]")
        self.assertEqual(len(dat["bang"]), 3)

    def test_so_dong(self):
        dat = self.bien(tbl(tr(tc("1")), tr(tc("2")), tr(tc("3")), cot=1), "so_dong", 3, "E3_QUA_SO_DONG", B + "/w:tbl[1]/w:tr[3]")
        self.assertEqual(len(dat["bang"][0]["dong"]), 3)

    def test_so_o(self):
        dat = self.bien(tbl(tr(tc("1"), tc("2"), tc("3")), cot=3), "so_o", 3, "E3_QUA_SO_O", B + "/w:tbl[1]/w:tr[1]/w:tc[3]")
        self.assertEqual(len(dat["bang"][0]["dong"][0]["o"]), 3)

    def test_ky_tu_o(self):
        dat = self.bien(tbl(tr(tc("ab", "cd")), cot=1), "ky_tu_o", 5, "E3_O_QUA_DAI", B + "/w:tbl[1]/w:tr[1]/w:tc[1]")
        self.assertEqual(dat["bang"][0]["dong"][0]["o"][0]["text"], "ab\ncd")     # "\n" giữa đoạn được tính

    def test_json_bang_nguon(self):
        path, doc, data = lam(tbl(tr(tc("Một"), tc("Hai")), tr(tc("Ba"), tc("Bốn")), cot=2), ten="json.docx")
        with mock.patch.dict(dhd.E3_GIOI_HAN, {"json_bang_nguon": 9999}):
            do = self.bn(path)
        self.assertEqual(do["trang_thai"], "DAY_DU")
        s = json_gon(do)                                                    # đo với giới hạn 4 chữ số → S cũng dùng 4 chữ số
        self.assertTrue(1001 <= s <= 9999, s)
        with mock.patch.dict(dhd.E3_GIOI_HAN, {"json_bang_nguon": s}):
            dat = self.bn(path)
        with mock.patch.dict(dhd.E3_GIOI_HAN, {"json_bang_nguon": s - 1}):
            vuot = self.bn(path)
        self.assertEqual((dat["trang_thai"], json_gon(dat)), ("DAY_DU", s))
        self.assertEqual(vuot, dto(data, doc, [], "INCOMPLETE", ly_do=[{"ma": "E3_JSON_QUA_LON", "vi_tri": None}],
                                   gh=dict(GH, json_bang_nguon=s - 1)))


# ================================================================== ZIP: từ chối LoiE3 trước khi phân tích
class ZipTests(_Co):
    def test_member_trung_ten(self):
        doc = tai_lieu(p("A"))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            data = goi(phan_docx(doc) + [("word/document.xml", doc)])
        self.loi_ca_hai("E3_ZIP_TRUNG_PHAN", ghi("trung.docx", data))

    def test_ten_member_khong_an_toan(self):
        goc = goi(phan_docx(tai_lieu(p("A")), them=[("AAAAAAAAAA", b"x")]))
        self.assertEqual(goc.count(b"AAAAAAAAAA"), 2)                       # local header + central directory
        for xau in ("../evil.xm", "/evil.xmlx", "C:evil.xml", "a\\evil.xml", "evil\x00x.xml"):
            with self.subTest(ten=repr(xau)):
                self.assertEqual(len(xau), 10)
                self.loi_ca_hai("E3_ZIP_DUONG_DAN", ghi("ten.docx", goc.replace(b"AAAAAAAAAA", xau.encode("ascii"))))

    def test_co_ma_hoa(self):
        data = goi(phan_docx(tai_lieu(p("A"))))
        i = _cd(data, "word/document.xml") + 8
        co = int.from_bytes(data[i:i + 2], "little") | 0x1
        self.loi_ca_hai("E3_ZIP_MA_HOA", ghi("ma_hoa.docx", _va(data, i, co.to_bytes(2, "little"))))

    def test_kieu_nen_khong_ho_tro(self):
        data = goi(phan_docx(tai_lieu(p("A"))))
        i = _cd(data, "word/document.xml") + 10
        self.loi_ca_hai("E3_ZIP_KHONG_HO_TRO", ghi("nen.docx", _va(data, i, (12).to_bytes(2, "little"))))   # 12 = bzip2

    def test_crc_sai(self):
        doc = tai_lieu(p("CRCMARK"))
        data = goi([("[Content_Types].xml", CT), ("_rels/.rels", RELS), ("word/document.xml", doc, zipfile.ZIP_STORED)])
        self.assertEqual(data.count(b"CRCMARK"), 1)
        self.loi_ca_hai("E3_ZIP_HONG", ghi("crc.docx", data.replace(b"CRCMARK", b"CRCMARX")))

    def test_bom_nen_ty_le(self):
        bom = goi(phan_docx(tai_lieu(p("A")), them=[("word/media/zero.bin", b"\0" * (2 * 1024 * 1024))]))
        self.loi_ca_hai("E3_ZIP_BOM_NEN", ghi("bom.docx", bom))
        path, doc, data = lam(p("A"), them=[("word/media/zero.bin", b"\0" * (1024 * 1024))])   # đúng ngưỡng ty_le_tu: không xét tỷ lệ
        self.assertEqual(self.bn(path), dto(data, doc, []))

    def test_so_member(self):
        than = tai_lieu(p("A"))
        du = goi(phan_docx(than, them=[(f"word/x{i}.xml", b"<x/>") for i in range(397)]))      # 3 + 397 = 400
        self.assertEqual(self.bn(ghi("400.docx", du))["trang_thai"], "DAY_DU")
        qua = goi(phan_docx(than, them=[(f"word/x{i}.xml", b"<x/>") for i in range(398)]))     # 401
        self.loi_ca_hai("E3_ZIP_QUA_NHIEU_PHAN", ghi("401.docx", qua))

    def test_member_tong_tep_bien(self):
        doc = tai_lieu(p("Biên"))
        ph = phan_docx(doc)
        lon, tong = max(len(x[1]) for x in ph), sum(len(x[1]) for x in ph)
        data = goi(ph)
        path = ghi("bien.docx", data)
        for khoa, gia_tri, ma in (("member", lon, "E3_ZIP_BOM_NEN"), ("tong", tong, "E3_ZIP_BOM_NEN"),
                                  ("tep", len(data), "E3_TEP_QUA_LON")):
            with self.subTest(khoa=khoa):
                with mock.patch.dict(dhd.E3_GIOI_HAN, {khoa: gia_tri}):
                    self.assertEqual(self.bn(path)["trang_thai"], "DAY_DU")
                with mock.patch.dict(dhd.E3_GIOI_HAN, {khoa: gia_tri - 1}):
                    self.loi_ca_hai(ma, path)

    def test_khong_phai_zip_hong_rong_thieu_document(self):
        self.loi_ca_hai("E3_KHONG_PHAI_ZIP", ghi("pdf.docx", b"%PDF-1.4 gia lap\n"))
        self.loi_ca_hai("E3_TEP_RONG", ghi("rong.docx", b""))
        self.loi_ca_hai("E3_ZIP_HONG", ghi("hong.docx", b"PK\x03\x04" + b"\x00" * 40))
        self.loi_ca_hai("E3_THIEU_DOCUMENT_XML", ghi("thieu.docx", goi([("[Content_Types].xml", CT), ("_rels/.rels", RELS)])))


# ================================================================== XML: mã hoá, DTD, độ sâu
class XmlTests(_Co):
    def test_dtd_utf8_utf16_va_entity_numbering(self):
        dtd = '<!DOCTYPE w:document [<!ENTITY x "y">]>'
        u8 = f'{KHAI_BAO}{dtd}<w:document {NS}><w:body>{p("A")}</w:body></w:document>'.encode("utf-8")
        u16 = f'<?xml version="1.0" encoding="UTF-16"?>{dtd}<w:document {NS}><w:body>{p("A")}</w:body></w:document>'.encode("utf-16")
        num = f'{KHAI_BAO}<!DOCTYPE w:numbering [<!ENTITY a "b">]><w:numbering {NS}/>'.encode("utf-8")
        for ten, ph in (("u8", phan_docx(u8)), ("u16", phan_docx(u16)), ("numbering", phan_docx(tai_lieu(p("A")), numbering=num))):
            with self.subTest(ca=ten):
                self.loi_ca_hai("E3_XML_DTD", ghi(f"dtd_{ten}.docx", goi(ph)))

    def test_ma_hoa(self):
        than = f'<w:document {NS}><w:body>{p("A")}</w:body></w:document>'
        ca = {
            "khai_bao_lech_u8": (f'<?xml version="1.0" encoding="ISO-8859-1"?>{than}').encode("utf-8"),
            "khai_bao_lech_u16": (f'<?xml version="1.0" encoding="UTF-8"?>{than}').encode("utf-16"),
            "utf32": (f'<?xml version="1.0" encoding="UTF-32"?>{than}').encode("utf-32"),
            "utf8_hong": KHAI_BAO.encode("utf-8") + f"<w:document {NS}><w:body>".encode("utf-8") + b"<w:p><w:r><w:t>\xc3\x28</w:t>"
                         b"</w:r></w:p></w:body></w:document>",
        }
        for ten, doc in ca.items():
            with self.subTest(ca=ten):
                self.loi_ca_hai("E3_XML_MA_HOA", ghi(f"{ten}.docx", goi(phan_docx(doc))))

    def test_utf16_hop_le_va_xml_hong(self):
        doc = (f'<?xml version="1.0" encoding="UTF-16"?><w:document {NS}><w:body>'
               f'{tbl(tr(tc("Mười sáu")), cot=1)}</w:body></w:document>').encode("utf-16")
        data = goi(phan_docx(doc))
        bn = self.bn(ghi("u16.docx", data))
        T = B + "/w:tbl[1]"
        self.assertEqual(bn, dto(data, doc, [bang_(doc, T, 1, 1, [dong_(doc, T + "/w:tr[1]", 1,
                                                                        [o_(doc, T + "/w:tr[1]/w:tc[1]", 1, 1, ["Mười sáu"])])])]))
        hong = f"{KHAI_BAO}<w:document {NS}><w:body><w:p></w:body></w:document>".encode("utf-8")
        self.loi_ca_hai("E3_XML_HONG", ghi("hong.docx", goi(phan_docx(hong))))

    def test_do_sau_128_dat_129_tu_choi(self):
        def sau(k):                                                         # document(1) + body(2) + k customXml + p = k + 3
            return '<w:customXml w:element="x">' * k + "<w:p/>" + "</w:customXml>" * k
        path, doc, data = lam(sau(125), ten="sau128.docx")
        self.assertEqual(self.bn(path), dto(data, doc, []))
        self.loi_ca_hai("E3_XML_QUA_SAU", lam(sau(126), ten="sau129.docx")[0])


# ================================================================== dòng dõi / PDF
class DongDoiPdfTests(_Co):
    def test_dong_doi_bang_nguon_dau_vao(self):
        path, doc, data = lam(tbl(tr(tc("A")), cot=1))
        _, bn, _ = self.bn_docx(path)
        truoc = copy.deepcopy(bn)
        self.assertEqual(dhd._bang_nguon_dau_vao(bn, (_sha(data), len(data)), False, 0), bn)
        chuyen = dhd._bang_nguon_dau_vao(bn, ("a" * 64, 123), True, 7)
        mong = dto(data, doc, [], "INCOMPLETE", "CHUYEN_DOCX", 7, [{"ma": "E3_CHUYEN_DOCX_CHUA_XAC_MINH", "vi_tri": None}])
        mong["nguon"].update(source_sha256="a" * 64, source_bytes=123)
        self.assertEqual(chuyen, mong)
        doi = dhd._bang_nguon_dau_vao(bn, ("b" * 64, 9), False, 0)
        mong2 = dto(data, doc, [], "INCOMPLETE", ly_do=[{"ma": "E3_NGUON_THAY_DOI", "vi_tri": None}])
        mong2["nguon"].update(source_sha256="b" * 64, source_bytes=9)
        self.assertEqual(doi, mong2)
        self.assertEqual(bn, truoc)                                         # không sửa DTO đầu vào
        cd = dict(copy.deepcopy(bn), trang_thai="INCOMPLETE", bang=[], ly_do=[{"ma": "E3_ALTCHUNK", "vi_tri": B}])
        self.assertEqual(dhd._bang_nguon_dau_vao(cd, ("c" * 64, 1), True, 0)["ly_do"],
                         [{"ma": "E3_CHUYEN_DOCX_CHUA_XAC_MINH", "vi_tri": None}, {"ma": "E3_ALTCHUNK", "vi_tri": None}])

    def test_pdf_khong_ho_tro(self):
        raw = b"%PDF-1.4 gia lap\n"
        path = ghi("hd.pdf", raw)
        with mock.patch.object(dhd, "read_pdf", return_value=("\n".join(DOAN_XD), {"pages": 1, "raw_words": 500})):
            bn = self.bn(path)
        self.assertEqual(bn, {"schema": "source6-docx-tables/v1", "trang_thai": "KHONG_HO_TRO", "pham_vi": "WORD_DOCUMENT_BODY_TABLES",
                              "nguon": {"source_sha256": _sha(raw), "source_bytes": len(raw), "docx_sha256": None, "docx_bytes": None,
                                        "document_xml_sha256": None},
                              "bien_doi": {"kieu": "TRUC_TIEP", "track_changes": 0}, "gioi_han": GH,
                              "ly_do": [{"ma": "E3_PDF_KHONG_HO_TRO", "vi_tri": None}], "bang": []})


# ================================================================== pipeline thật TrichXuat RULE_ONLY → *_KET_QUA.json
BANG_XD = tbl(tr(tc("STT"), tc("Hạng mục"), tc("Giá trị (đồng)")), tr(tc("1"), tc("Đường nội bộ"), tc("5.000.000.000")),
              tr(tc("2"), tc("Dự phòng"), tc("0")), tr(tc(), tc(), tc()), cot=3)


class PipelineTests(_Co):
    @classmethod
    def setUpClass(cls):
        cat = Path(str(danh_muc.CATALOG_COMMON["XD"]["path"]))
        if _sha(cat.read_bytes()) != danh_muc.CATALOG_COMMON["XD"]["sha256"]:
            raise RuntimeError("Catalog XD trong OVERLAY lệch SHA đã ghim")
        cls.params = danh_muc.load_params_ban_chup(str(cat))
        cls.ma = [x["ma"] for x in cls.params]

    def chay(self, path):
        out = os.path.join(TMP, f"{next(_DEM):03d}_out")
        os.makedirs(out)
        tx = qt.TrichXuat(self.params, ai=None, out_dir=out, cloud=None, che_do="RULE_ONLY")
        kq = tx.xu_ly(path)
        ten = qt.ten_an_toan(os.path.splitext(os.path.basename(path))[0])
        tep = os.path.join(out, ten, f"{ten}_KET_QUA.json")
        with open(tep, encoding="utf-8") as f:
            raw = json.load(f)
        self.assertEqual(raw["bang_nguon"], kq["bang_nguon"])
        return raw

    def kiem_rule_only(self, raw):
        self.assertEqual(raw["che_do"], "RULE_ONLY")
        self.assertEqual([d["ma"] for d in raw["bang"]], self.ma)
        tc_ = [d for d in raw["bang"] if d["nguon"] == "Quy tắc"]
        self.assertTrue(tc_, "RULE_ONLY phải giữ positive quy tắc TC của nguồn")
        for d in raw["bang"]:
            if d["nguon"] != "Quy tắc":
                self.assertEqual(d["gia_tri"], "", d["ma"])
        if "master_hd" in sys.modules:
            self.assertTrue(_chuan(sys.modules["master_hd"].__file__).startswith(_chuan(os.environ["KTT_SOURCE6_E3_OVERLAY"]) + os.sep))

    def test_xd_docx_ket_qua_json_that(self):
        path, doc, data = lam("".join(p(x) for x in DOAN_XD) + BANG_XD, ten="HD_XD_BANG.docx")
        raw = self.chay(path)
        self.kiem_rule_only(raw)
        self.assertEqual((raw["phieu_kiem_tra"]["articles"], raw["phieu_kiem_tra"]["tables"]), (8, 1))
        T = B + "/w:tbl[1]"

        def d(i, *gt):
            r = f"{T}/w:tr[{i}]"
            return dong_(doc, r, i, [o_(doc, f"{r}/w:tc[{j}]", j, j, [g] if g else []) for j, g in enumerate(gt, 1)])
        mong = dto(data, doc, [bang_(doc, T, 1, 3, [d(1, "STT", "Hạng mục", "Giá trị (đồng)"), d(2, "1", "Đường nội bộ", "5.000.000.000"),
                                                   d(3, "2", "Dự phòng", "0"), d(4, "", "", "")])])
        self.assertEqual(raw["bang_nguon"], mong)
        self.assertEqual(raw["bang_nguon"], dhd.read_contract(path)["bang_nguon"])

    def test_pdf_lop_chu_ket_qua_json(self):
        raw_pdf = b"%PDF-1.4 gia lap lop chu\n"
        path = ghi("HD_PDF.pdf", raw_pdf)
        with mock.patch.object(qt.TrichXuat, "ocr_pdf", autospec=True, return_value=(path, None)), \
                mock.patch.object(dhd, "read_pdf", return_value=("\n".join(DOAN_XD), {"pages": 1, "raw_words": 500})):
            raw = self.chay(path)
        self.kiem_rule_only(raw)
        self.assertEqual(raw["bang_nguon"]["trang_thai"], "KHONG_HO_TRO")
        self.assertEqual(raw["bang_nguon"]["ly_do"], [{"ma": "E3_PDF_KHONG_HO_TRO", "vi_tri": None}])
        self.assertEqual((raw["bang_nguon"]["nguon"]["source_sha256"], raw["bang_nguon"]["nguon"]["docx_sha256"]), (_sha(raw_pdf), None))
        self.assertEqual(raw["bang_nguon"]["bang"], [])

    def test_pdf_ocr_ket_qua_json_khong_ho_tro(self):
        docx, doc, data = lam("".join(p(x) for x in DOAN_XD) + BANG_XD, ten="ocr_ra.docx")
        raw_pdf = b"%PDF-1.4 gia lap scan\n"
        pdf = ghi("HD_SCAN.pdf", raw_pdf)
        ocr = {"trang": 1, "giay": 0, "tu_luu_dem": False, "ly_do": "gia lap", "sha1": "0" * 40}
        with mock.patch.object(qt.TrichXuat, "ocr_pdf", autospec=True, return_value=(docx, ocr)) as m:
            raw = self.chay(pdf)
        self.assertEqual(m.call_args.args[1:], (pdf, os.path.basename(pdf)))
        self.kiem_rule_only(raw)
        self.assertEqual(raw["bang_nguon"], {
            "schema": "source6-docx-tables/v1", "trang_thai": "KHONG_HO_TRO", "pham_vi": "WORD_DOCUMENT_BODY_TABLES",
            "nguon": {"source_sha256": _sha(raw_pdf), "source_bytes": len(raw_pdf), "docx_sha256": _sha(data), "docx_bytes": len(data),
                      "document_xml_sha256": _sha(doc)},
            "bien_doi": {"kieu": "CHUYEN_DOCX", "track_changes": 0}, "gioi_han": GH,
            "ly_do": [{"ma": "E3_PDF_OCR_KHONG_HO_TRO", "vi_tri": None}], "bang": []})


if __name__ == "__main__":
    unittest.main()
