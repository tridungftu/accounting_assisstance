# -*- coding: utf-8 -*-
"""
doc_hop_dong.py — Đọc hợp đồng Word (.docx/.doc) ra văn bản, GIỮ SỐ ĐIỀU/KHOẢN ĐÁNH TỰ ĐỘNG, tách theo Điều,
và lập "phiếu kiểm tra đầu vào". Chỉ dùng thư viện chuẩn Python.

Track Changes: hợp đồng còn sửa đổi chưa chấp nhận → Accept All trên BẢN SAO tạm (Word trên Windows; không có Word
thì Python tự chấp nhận trong XML). File gốc không bị đổi. Phiếu kiểm tra ghi rõ đã chấp nhận bao nhiêu chỗ, bằng cách nào.

    python -m trich_xuat.doc_hop_dong hop_dong.docx      → in phiếu kiểm tra + lưu hop_dong.txt cạnh file
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
import zlib
import xml.etree.ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % W_NS


# ---------------------------------------------------------------- Word (Windows) / LibreOffice
def _ps_quote(s):
    return "'" + str(s).replace("'", "''") + "'"


def _word(src, target, accept_all=True):
    """Mở src bằng Microsoft Word, (Accept All), lưu target dạng .docx. Trả về số sửa đổi đã chấp nhận."""
    ps = ("$ErrorActionPreference='Stop';$w=New-Object -ComObject Word.Application;$w.Visible=$false;"
          "$w.DisplayAlerts=0;try{"
          f"$d=$w.Documents.Open({_ps_quote(src)},$false,$false,$false);"
          "$n=$d.Revisions.Count;"
          + ("$d.TrackRevisions=$false;if($n -gt 0){$d.Revisions.AcceptAll()};" if accept_all else "")
          + f"$d.SaveAs2({_ps_quote(target)},16);$d.Close($false);Write-Output \"REV=$n\""
          "}finally{$w.Quit()}")
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True,
                       timeout=240, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not os.path.exists(target):
        raise RuntimeError("Word không mở/lưu được file: " + (r.stderr or r.stdout or "")[-300:])
    m = re.search(r"REV=(\d+)", r.stdout or "")
    return int(m.group(1)) if m else 0


def _ban_sao_tam(path, duoi):
    """Chép file sang thư mục tạm với tên ASCII (tránh lỗi dấu tiếng Việt trong lệnh PowerShell/LibreOffice)."""
    d = tempfile.mkdtemp(prefix="hd_doc_")
    p = os.path.join(d, "hop_dong" + duoi)
    shutil.copy2(path, p)
    return d, p


def chuyen_docx(path, accept_all=True):
    """.doc (hoặc .docx có Track Changes) → .docx tạm đã Accept All. Trả (đường dẫn .docx tạm, số sửa đổi, cách làm).
    File gốc không bị đụng tới."""
    duoi = os.path.splitext(path)[1].lower()
    d, src = _ban_sao_tam(path, duoi)
    target = os.path.join(d, "hop_dong_da_chap_nhan.docx")
    if os.name == "nt":
        try:
            n = _word(src, target, accept_all)
            return target, n, "Word"
        except Exception as e:                       # không có Word / Word lỗi → thử LibreOffice / Python
            loi_word = str(e)
        else:
            loi_word = ""
    else:
        loi_word = "không chạy trên Windows"
    if duoi == ".docx":
        return src, None, "Python"                   # .docx: Python tự chấp nhận trong XML (read_docx)
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        raise RuntimeError("Cần Microsoft Word (Windows) hoặc LibreOffice để đọc file .doc" +
                           (f" — Word: {loi_word}" if loi_word else ""))
    subprocess.run([exe, "--headless", "--convert-to", "docx", "--outdir", d, src], check=True, timeout=240,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = os.path.join(d, "hop_dong.docx")
    if not os.path.exists(out):
        raise RuntimeError("Chuyển .doc sang .docx thất bại")
    return out, None, "LibreOffice + Python"


# ---------------------------------------------------------------- chấp nhận sửa đổi trong XML
_XOA = {W + t for t in ("del", "moveFrom", "rPrChange", "pPrChange", "sectPrChange", "tblPrChange", "tblPrExChange",
                        "tcPrChange", "trPrChange", "tblGridChange", "numberingChange", "moveFromRangeStart",
                        "moveFromRangeEnd", "moveToRangeStart", "moveToRangeEnd", "customXmlDelRangeStart",
                        "customXmlDelRangeEnd", "customXmlInsRangeStart", "customXmlInsRangeEnd")}
_MO_GOI = {W + "ins", W + "moveTo"}


def dem_sua_doi(xml_text):
    return xml_text.count("<w:ins ") + xml_text.count("<w:del ") + xml_text.count("<w:moveFrom ") \
        + xml_text.count("<w:moveTo ")


def chap_nhan_xml(root):
    """Accept All trên cây XML document.xml: bỏ phần xoá, giữ phần chèn, bỏ dấu đổi định dạng,
    xoá dòng bảng bị xoá, gộp đoạn có dấu xuống dòng bị xoá vào đoạn sau. Sửa trực tiếp root."""
    # 1. dòng bảng bị xoá
    for tbl in root.iter(W + "tbl"):
        for tr in list(tbl.findall(W + "tr")):
            trpr = tr.find(W + "trPr")
            if trpr is not None and trpr.find(W + "del") is not None:
                tbl.remove(tr)
    # 2. đoạn có dấu ¶ bị xoá (w:pPr/w:rPr/w:del) → gộp nội dung vào đoạn kế tiếp
    for parent in list(root.iter()):
        kids = list(parent)
        i = 0
        while i < len(kids):
            p = kids[i]
            if p.tag == W + "p":
                ppr = p.find(W + "pPr")
                rpr = ppr.find(W + "rPr") if ppr is not None else None
                if rpr is not None and rpr.find(W + "del") is not None:
                    nxt = kids[i + 1] if i + 1 < len(kids) and kids[i + 1].tag == W + "p" else None
                    noi_dung = [c for c in p if c.tag != W + "pPr"]
                    if nxt is not None:
                        pos = 1 if nxt.find(W + "pPr") is not None else 0
                        for j, c in enumerate(noi_dung):
                            p.remove(c)
                            nxt.insert(pos + j, c)
                        parent.remove(p)
                        kids.pop(i)
                        continue
                    rpr.remove(rpr.find(W + "del"))
            i += 1

    # 3. bỏ phần xoá / dấu đổi định dạng; mở gói phần chèn
    def lam(el):
        i = 0
        while i < len(el):
            c = el[i]
            if c.tag in _XOA:
                el.remove(c)
                continue
            if c.tag in _MO_GOI:
                lam(c)
                el.remove(c)
                for j, g in enumerate(list(c)):
                    el.insert(i + j, g)
                i += len(c)
                continue
            lam(c)
            i += 1
    lam(root)
    return root


# ---------------------------------------------------------------- E3-01: nạp ZIP/XML có giới hạn
# Giới hạn KỸ THUẬT (không phải chính sách nghiệp vụ): tep = MAX_FILE của nguồn (may_chu/dich_vu.py:39); so_member/member/tong/ty_le
# theo GIOI_HAN central mau_docx (tỷ lệ chỉ xét member > ty_le_tu byte); phần bằng chứng bảng MỚI: so_bang/so_dong/so_o/ky_tu_o/
# json_bang_nguon (UTF-8 JSON gọn của cả bang_nguon) + do_sau_xml. Không có đường cấu hình/trình duyệt nào đè các giá trị này.
E3_GIOI_HAN = {"tep": 60 * 1024 * 1024, "so_member": 400, "member": 30 * 1024 * 1024, "tong": 120 * 1024 * 1024, "ty_le": 120,
               "ty_le_tu": 1024 * 1024, "do_sau_xml": 128, "so_bang": 200, "so_dong": 10000, "so_o": 100000, "ky_tu_o": 20000,
               "json_bang_nguon": 2 * 1024 * 1024}
E3_SCHEMA = "source6-docx-tables/v1"
E3_PHAM_VI = "WORD_DOCUMENT_BODY_TABLES"
_E3_NEN = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
_RE_KHAI_BAO = re.compile(r"\A<\?xml\s[^>]*?\?>")
_RE_MA_KHAI_BAO = re.compile(r"""\bencoding\s*=\s*["']([A-Za-z0-9._-]+)["']""")
_RE_DTD = re.compile(r"<!\s*(DOCTYPE|ENTITY|ELEMENT|ATTLIST|NOTATION)", re.I)


class LoiE3(ValueError):
    """Vi phạm an toàn/giới hạn ZIP-XML: mã E3_* ổn định, báo TRƯỚC khi phân tích/trích kiểu cũ — không có kết quả 'thành công' giả."""
    def __init__(self, ma, thong_diep):
        super().__init__(f"{ma}: {thong_diep}")
        self.ma = ma


def _sha_tep(path):
    """(SHA-256 chữ thường, số byte) của bytes THẬT trong file — đọc dòng, không đổi file."""
    h, n = hashlib.sha256(), 0
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
            n += len(b)
    return h.hexdigest(), n


def _doc_tep_gioi_han(path):
    with open(path, "rb") as f:
        data = f.read(E3_GIOI_HAN["tep"] + 1)
    if not data:
        raise LoiE3("E3_TEP_RONG", "File rỗng")
    if len(data) > E3_GIOI_HAN["tep"]:
        raise LoiE3("E3_TEP_QUA_LON", f"File lớn hơn {E3_GIOI_HAN['tep']:,} byte")
    return data


def _ten_khong_an_toan(n):
    return (not n or n.startswith(("/", "\\")) or "\\" in n or "\x00" in n or re.match(r"^[A-Za-z]:", n) is not None
            or ".." in n.split("/"))


def _kiem_danh_sach(z):
    """Kiểm MỌI member theo ZipInfo trước khi đọc bất kỳ member nào. Trả {tên: ZipInfo}."""
    gh = E3_GIOI_HAN
    infos = z.infolist()
    if len(infos) > gh["so_member"]:
        raise LoiE3("E3_ZIP_QUA_NHIEU_PHAN", f"Gói có hơn {gh['so_member']} phần")
    out, tong = {}, 0
    for i in infos:
        if _ten_khong_an_toan(i.orig_filename) or _ten_khong_an_toan(i.filename):
            raise LoiE3("E3_ZIP_DUONG_DAN", "Gói chứa tên phần không an toàn")
        if i.filename in out:
            raise LoiE3("E3_ZIP_TRUNG_PHAN", f"Gói có hai phần cùng tên {i.filename}")
        out[i.filename] = i
        if i.flag_bits & 0x1:
            raise LoiE3("E3_ZIP_MA_HOA", f"Phần {i.filename} được mã hoá")
        if i.compress_type not in _E3_NEN:
            raise LoiE3("E3_ZIP_KHONG_HO_TRO", f"Phần {i.filename} dùng kiểu nén không hỗ trợ")
        if i.file_size > gh["member"]:
            raise LoiE3("E3_ZIP_BOM_NEN", f"Phần {i.filename} quá lớn sau giải nén")
        if i.file_size > gh["ty_le_tu"] and (i.compress_size <= 0 or i.file_size / i.compress_size > gh["ty_le"]):
            raise LoiE3("E3_ZIP_BOM_NEN", f"Phần {i.filename} có tỷ lệ nén bất thường")
        tong += i.file_size
    if tong > gh["tong"]:
        raise LoiE3("E3_ZIP_BOM_NEN", "Tổng dung lượng giải nén vượt giới hạn")
    return out


def _mo_zip(data):
    """Bytes .docx đã đọc → (ZipFile trong bộ nhớ, {tên: ZipInfo}) sau khi kiểm; bắt buộc có word/document.xml."""
    if bytes(data[:4]) != b"PK\x03\x04":
        raise LoiE3("E3_KHONG_PHAI_ZIP", "Không phải gói ZIP/OOXML .docx")
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, zipfile.LargeZipFile, ValueError, OSError, EOFError, RuntimeError, NotImplementedError):
        raise LoiE3("E3_ZIP_HONG", "Gói ZIP hỏng/không đọc được") from None
    infos = _kiem_danh_sach(z)
    if "word/document.xml" not in infos:
        raise LoiE3("E3_THIEU_DOCUMENT_XML", "Thiếu word/document.xml")
    return z, infos


def _doc_member(z, infos, ten):
    """Đọc DÒNG một member đã kiểm, chặn theo cả ZipInfo lẫn số byte giải nén THẬT (không z.read không giới hạn); CRC do zipfile kiểm ở EOF."""
    i = infos.get(ten)
    if i is None:
        raise LoiE3("E3_THIEU_PHAN", f"Thiếu phần {ten}")
    tran = min(i.file_size, E3_GIOI_HAN["member"])
    out = bytearray()
    try:
        with z.open(i) as f:
            while True:
                b = f.read(min(1 << 16, tran + 1 - len(out)))
                if not b:
                    break
                out += b
                if len(out) > tran:
                    raise LoiE3("E3_ZIP_KICH_THUOC_THAT", f"Phần {ten} giải nén ra nhiều hơn khai báo/giới hạn")
    except LoiE3:
        raise
    except (zipfile.BadZipFile, zlib.error, EOFError, OSError, RuntimeError, NotImplementedError, ValueError):
        raise LoiE3("E3_ZIP_HONG", f"Không giải nén được phần {ten} (hỏng/CRC)") from None
    if len(out) != i.file_size:
        raise LoiE3("E3_ZIP_KICH_THUOC_THAT", f"Phần {ten} giải nén khác kích thước khai báo")
    return bytes(out)


def _giai_ma_xml(raw, ten):
    """Một quy tắc giải mã cho mọi XML được dùng: UTF-8/UTF-16 (BOM hoặc mẫu '<'), strict; khai báo encoding phải cùng họ. UTF-32/mã khác → lỗi."""
    if raw[:4] in (b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff", b"<\x00\x00\x00", b"\x00\x00\x00<"):
        raise LoiE3("E3_XML_MA_HOA", f"Phần {ten} dùng UTF-32 — không nhận")
    if raw[:3] == b"\xef\xbb\xbf":
        ho, ma, than = "utf-8", "utf-8", raw[3:]
    elif raw[:2] == b"\xff\xfe":
        ho, ma, than = "utf-16", "utf-16-le", raw[2:]
    elif raw[:2] == b"\xfe\xff":
        ho, ma, than = "utf-16", "utf-16-be", raw[2:]
    elif raw[:2] == b"<\x00":
        ho, ma, than = "utf-16", "utf-16-le", raw
    elif raw[:2] == b"\x00<":
        ho, ma, than = "utf-16", "utf-16-be", raw
    else:
        ho, ma, than = "utf-8", "utf-8", raw
    try:
        text = than.decode(ma)
    except UnicodeDecodeError:
        raise LoiE3("E3_XML_MA_HOA", f"Phần {ten} không giải mã được theo {ma}") from None
    m = _RE_KHAI_BAO.match(text)
    k = _RE_MA_KHAI_BAO.search(m.group(0)) if m else None
    if k:
        khai = k.group(1).lower().replace("_", "-")
        hop = {"utf-8": {"utf-8", "utf8"}, "utf-16": {"utf-16", "utf16", "utf-16le", "utf-16be", "utf-16-le", "utf-16-be"}}[ho]
        if khai not in hop:
            raise LoiE3("E3_XML_MA_HOA", f"Phần {ten} khai báo mã {k.group(1)} không khớp/không hỗ trợ")
    return text


def _parse_xml(raw, ten):
    """Giải mã → chặn DTD/ENTITY/ELEMENT/ATTLIST/NOTATION trên chuỗi ĐÃ giải mã → phân tích chính chuỗi đó, chặn độ sâu > do_sau_xml."""
    text = _giai_ma_xml(raw, ten)
    if _RE_DTD.search(text):
        raise LoiE3("E3_XML_DTD", f"Phần {ten} có DOCTYPE/ENTITY/khai báo DTD — không nhận")
    m = _RE_KHAI_BAO.match(text)
    if m:
        text = text[m.end():]
    p = ET.XMLPullParser(events=("start", "end"))
    sau, goc, toi_da = 0, None, E3_GIOI_HAN["do_sau_xml"]

    def doc_su_kien():
        nonlocal sau, goc
        for ev, el in p.read_events():
            if ev == "start":
                sau += 1
                if goc is None:
                    goc = el
                if sau > toi_da:
                    raise LoiE3("E3_XML_QUA_SAU", f"Phần {ten} lồng sâu hơn {toi_da} cấp")
            else:
                sau -= 1
    try:
        for i in range(0, len(text), 1 << 16):
            p.feed(text[i:i + (1 << 16)])
            doc_su_kien()
        p.close()
        doc_su_kien()
    except ET.ParseError:
        raise LoiE3("E3_XML_HONG", f"Phần {ten} không phải XML hợp lệ") from None
    if goc is None:
        raise LoiE3("E3_XML_HONG", f"Phần {ten} rỗng")
    return goc


def _xml_trong_zip(z, ten):
    """Đường đọc XML DUY NHẤT cho Numbering (numbering/styles): kiểm danh sách member → đọc có giới hạn → giải mã/phân tích đã kiểm."""
    return _parse_xml(_doc_member(z, _kiem_danh_sach(z), ten), ten)


def _kiem_docx_an_toan(path):
    """read_contract: kiểm ZIP + mọi XML bộ đọc sẽ dùng TRƯỚC _co_sua_doi/chuyển đổi kiểu cũ. Vi phạm → LoiE3."""
    z, infos = _mo_zip(_doc_tep_gioi_han(path))
    for ten in ("word/document.xml", "word/numbering.xml", "word/styles.xml"):
        if ten in infos:
            _parse_xml(_doc_member(z, infos, ten), ten)


# ---------------------------------------------------------------- đánh số tự động
def _roman(n):
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
            (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    s = ""
    for v, r in vals:
        while n >= v:
            s += r
            n -= v
    return s


def _letter(n):
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(97 + r) + s
    return s


def fmt_num(n, fmt):
    if fmt in ("decimal", "decimalZero"):
        return f"{n:02d}" if fmt == "decimalZero" else str(n)
    if fmt == "lowerLetter":
        return _letter(n)
    if fmt == "upperLetter":
        return _letter(n).upper()
    if fmt == "lowerRoman":
        return _roman(n)
    if fmt == "upperRoman":
        return _roman(n).upper()
    if fmt in ("bullet", "none"):
        return ""
    return str(n)


class Numbering:
    def __init__(self, z):
        self.abs, self.num2abs, self.overrides, self.style_num = {}, {}, {}, {}
        self.counters, self.seen_num = {}, set()
        if "word/numbering.xml" in z.namelist():
            root = _xml_trong_zip(z, "word/numbering.xml")          # E3-01: cùng đường giải mã/chặn DTD/độ sâu đã kiểm
            for a in root.findall(f"{W}abstractNum"):
                aid = a.get(f"{W}abstractNumId")
                lv = {}
                for lvl in a.findall(f"{W}lvl"):
                    il = int(lvl.get(f"{W}ilvl"))

                    def g(tag, d=None, lvl=lvl):
                        e = lvl.find(f"{W}{tag}")
                        return e.get(f"{W}val") if e is not None else d
                    lv[il] = {"start": int(g("start", "1")), "fmt": g("numFmt", "decimal"),
                              "text": g("lvlText", ""), "lgl": lvl.find(f"{W}isLgl") is not None}
                self.abs[aid] = lv
            for n in root.findall(f"{W}num"):
                nid = n.get(f"{W}numId")
                self.num2abs[nid] = n.find(f"{W}abstractNumId").get(f"{W}val")
                ov = {}
                for o in n.findall(f"{W}lvlOverride"):
                    so = o.find(f"{W}startOverride")
                    if so is not None:
                        ov[int(o.get(f"{W}ilvl"))] = int(so.get(f"{W}val"))
                self.overrides[nid] = ov
        if "word/styles.xml" in z.namelist():
            st = _xml_trong_zip(z, "word/styles.xml")               # E3-01: cùng đường giải mã/chặn DTD/độ sâu đã kiểm
            based = {}
            for s in st.findall(f"{W}style"):
                sid = s.get(f"{W}styleId")
                b = s.find(f"{W}basedOn")
                based[sid] = b.get(f"{W}val") if b is not None else None
                np_ = s.find(f"{W}pPr/{W}numPr")
                if np_ is not None:
                    ni, il = np_.find(f"{W}numId"), np_.find(f"{W}ilvl")
                    self.style_num[sid] = (ni.get(f"{W}val") if ni is not None else None,
                                           int(il.get(f"{W}val")) if il is not None else None)
            for sid in list(based):
                cur, seen = sid, 0
                while cur and cur not in self.style_num and seen < 10:
                    cur, seen = based.get(cur), seen + 1
                if cur and cur in self.style_num and sid not in self.style_num:
                    self.style_num[sid] = self.style_num[cur]

    def label(self, p):
        ppr = p.find(f"{W}pPr")
        nid, il = None, None
        if ppr is not None:
            ps = ppr.find(f"{W}pStyle")
            if ps is not None and ps.get(f"{W}val") in self.style_num:
                nid, il = self.style_num[ps.get(f"{W}val")]
            np_ = ppr.find(f"{W}numPr")
            if np_ is not None:
                a, b = np_.find(f"{W}numId"), np_.find(f"{W}ilvl")
                if a is not None:
                    nid = a.get(f"{W}val")
                if b is not None:
                    il = int(b.get(f"{W}val"))
        if not nid or nid == "0" or nid not in self.num2abs:
            return ""
        il = il or 0
        aid = self.num2abs[nid]
        levels = self.abs.get(aid, {})
        if il not in levels:
            return ""
        c = self.counters.setdefault(aid, {})
        if nid not in self.seen_num:
            self.seen_num.add(nid)
            for lvl, v in self.overrides.get(nid, {}).items():
                c[lvl] = v - 1
        c[il] = c.get(il, levels[il]["start"] - 1) + 1
        for deeper in [k for k in c if k > il]:
            del c[deeper]
        if levels[il]["fmt"] in ("bullet", "none"):
            return "-" if levels[il]["fmt"] == "bullet" else ""

        def rep(m):
            k = int(m.group(1)) - 1
            if k not in levels:
                return ""
            v = c.get(k, levels[k]["start"])
            return fmt_num(v, "decimal" if levels[il]["lgl"] else levels[k]["fmt"])
        return re.sub(r"%(\d)", rep, levels[il]["text"]).strip()


# ---------------------------------------------------------------- đọc văn bản
def _para_text(p):
    parts = []
    for el in p.iter():
        if el.tag == f"{W}t" and el.text:
            parts.append(el.text)
        elif el.tag in (f"{W}tab", f"{W}br", f"{W}cr"):
            parts.append(" ")
    return re.sub(r"[  ]+", " ", "".join(parts)).strip()


def _is_toc(sdt):
    g = sdt.find(f".//{W}docPartGallery")
    return g is not None and "Contents" in (g.get(f"{W}val") or "")


APPENDIX = re.compile(r"^\s*(?:PHỤ LỤC|Phụ lục|Phụ Lục)\b")
BIG_TABLE_ROWS, BIG_TABLE_CHARS = 50, 10000
MIN_ARTICLES = 5
CHUNK_CHARS = 3000


# ---------------------------------------------------------------- E3-01: bằng chứng bảng thân văn bản (bang_nguon)
# Chỉ phạm vi WORD_DOCUMENT_BODY_TABLES (w:tbl trong w:body của word/document.xml, kể cả bảng lồng); header/footer/footnote… NGOÀI phạm vi.
# Không gọi Numbering.label (có trạng thái), không chuẩn hoá số/ngày/tiền, không suy luận BOQ/tiền/tỷ lệ. Thiếu chắc chắn → INCOMPLETE, bang [].
_E3_SUA_NOI_DUNG = {W + t for t in ("ins", "del", "moveFrom", "moveTo", "cellIns", "cellDel", "cellMerge")}
_E3_SUA_O = {W + "cellIns", W + "cellDel", W + "cellMerge"}
_E3_CAU_TRUC = {W + "tbl", W + "tr", W + "tc"}
_E3_NOI_DUNG = {W + "p", W + "tbl", W + "tr", W + "tc", W + "altChunk", W + "txbxContent"}


def _qn(tag):
    """QName theo namespace (không theo tiền tố trong tệp): WordprocessingML → 'w:x'; namespace khác → '{uri}x'."""
    if tag.startswith("{"):
        uri, _, ten = tag[1:].partition("}")
        return f"w:{ten}" if uri == W_NS else f"{{{uri}}}{ten}"
    return tag


def _ban_do_goc(root):
    """TRƯỚC chap_nhan_xml: phần tử w:body/w:tbl/w:tr/w:tc → (đường dẫn GỐC, thứ tự nguồn). Chỉ số anh em đếm theo cùng QName gốc;
    thứ tự bảng = preorder toàn tài liệu; dòng/ô = thứ tự trong bảng/dòng sở hữu gần nhất. Đồng thời ghi sửa đổi nội dung (theo namespace)
    và cấu trúc sửa đổi bảng KHÔNG hỗ trợ (cellIns/cellDel/cellMerge; bảng/dòng/ô nằm trong w:del/w:moveFrom; dòng xoá không trực tiếp trong w:tbl)."""
    vt, so_dong, so_o = {}, {}, {}
    kt = {"co_sua": False, "loi": None, "so_bang": 0, "so_dong_goc": so_dong}

    def loi(ma, p):
        if kt["loi"] is None:
            kt["loi"] = (ma, p)

    def di(el, path, bang, dong, xoa):
        dem = {}
        for c in el:
            q = _qn(c.tag)
            dem[q] = dem.get(q, 0) + 1
            p = f"{path}/{q}[{dem[q]}]"
            b, d, x = bang, dong, xoa
            if c.tag in _E3_SUA_NOI_DUNG:
                kt["co_sua"] = True
                if c.tag in _E3_SUA_O:
                    loi("E3_SUA_DOI_O_KHONG_HO_TRO", p)
                if c.tag in (W + "del", W + "moveFrom"):
                    x = True
            if c.tag == W + "body" and el is root:
                vt[c] = (p, 1)
            elif c.tag == W + "tbl":
                kt["so_bang"] += 1
                vt[c] = (p, kt["so_bang"])
                b, d = c, None
            elif c.tag == W + "tr" and bang is not None:
                so_dong[bang] = so_dong.get(bang, 0) + 1
                vt[c] = (p, so_dong[bang])
                d = c
                trpr = c.find(W + "trPr")
                if el is not bang and trpr is not None and trpr.find(W + "del") is not None:
                    loi("E3_SUA_DOI_BANG_KHONG_HO_TRO", p)
            elif c.tag == W + "tc" and dong is not None:
                so_o[dong] = so_o.get(dong, 0) + 1
                vt[c] = (p, so_o[dong])
            if c.tag in _E3_CAU_TRUC and xoa:
                loi("E3_SUA_DOI_BANG_KHONG_HO_TRO", p)
            di(c, p, b, d, x)
    di(root, f"/{_qn(root.tag)}[1]", None, None, False)
    return vt, kt


class _ChuaDu(Exception):
    def __init__(self, ma, vi_tri):
        super().__init__(ma)
        self.ma, self.vi_tri = ma, vi_tri


def _chua(el, tags):
    return next((x for x in el.iter() if x.tag in tags), None)


class _GomBang:
    """Duyệt cây ĐÃ chấp nhận sửa đổi; định danh/vị trí luôn lấy từ bản đồ GỐC. Gặp điều không chắc chắn → _ChuaDu (tất cả hoặc không)."""

    def __init__(self, vt, so_dong_goc, doc_sha):
        self.vt, self.so_dong_goc, self.sha, self.gh = vt, so_dong_goc, doc_sha, E3_GIOI_HAN
        self.bang, self.n_dong, self.n_o, self.bo = [], 0, 0, 0

    def id_(self, loai, path):
        return f"{loai}-" + hashlib.sha256(f"{self.sha}:{loai}:{path}".encode("utf-8")).hexdigest()[:32]

    def vi_tri(self, el, cha):
        v = self.vt.get(el)
        if v is None:
            raise _ChuaDu("E3_VI_TRI_KHONG_XAC_DINH", cha)
        return v

    def mot(self, el, tag, path):
        es = el.findall(tag)
        if len(es) > 1:
            raise _ChuaDu("E3_LUOI_MAU_THUAN", path)
        return es[0] if es else None

    def so(self, pr, ten, path, toi_thieu, mac_dinh):
        e = self.mot(pr, W + ten, path) if pr is not None else None
        if e is None:
            return mac_dinh
        v = e.get(W + "val")
        if v is None or not re.fullmatch(r"[0-9]{1,5}", v) or int(v) < toi_thieu:
            raise _ChuaDu("E3_LUOI_KHONG_HOP_LE", path)
        return int(v)

    def cac_con(self, container, tag, bo_qua, cha):
        """Con trực tiếp `tag` (kể cả qua w:sdt/w:sdtContent); vỏ khác có nội dung → không hỗ trợ."""
        out = []
        for el in container:
            if el.tag == tag:
                out.append(el)
            elif el.tag == W + "sdt":
                for c in el:
                    if c.tag == W + "sdtContent":
                        out += self.cac_con(c, tag, (), cha)
                    elif _chua(c, _E3_NOI_DUNG) is not None:
                        raise _ChuaDu("E3_PHAN_TU_KHONG_HO_TRO", cha)
            elif el.tag not in bo_qua and _chua(el, _E3_NOI_DUNG) is not None:
                raise _ChuaDu("E3_PHAN_TU_KHONG_HO_TRO", cha)
        return out

    def khoi(self, container, cha):
        """Nội dung cấp thân (w:body / w:sdtContent của thân): w:tbl → bản ghi; đoạn/phần khác không mang bảng → ngoài phạm vi bảng."""
        for el in container:
            if el.tag == W + "tbl":
                self.bang_(el, None, cha)
            elif el.tag == W + "sdt":
                for c in el:
                    if c.tag == W + "sdtContent":
                        self.khoi(c, cha)
                    elif _chua(c, (W + "tbl", W + "altChunk")) is not None:
                        raise _ChuaDu("E3_BANG_TRONG_VO_KHONG_HO_TRO", cha)
            elif el.tag == W + "altChunk":
                raise _ChuaDu("E3_ALTCHUNK", cha)
            elif _chua(el, (W + "tbl", W + "altChunk")) is not None:
                raise _ChuaDu("E3_BANG_TRONG_VO_KHONG_HO_TRO", cha)

    def bang_(self, tbl, cha_id, cha):
        path, thu_tu = self.vi_tri(tbl, cha)
        trs = self.cac_con(tbl, W + "tr", (W + "tblPr", W + "tblGrid"), path)
        if not trs:
            if self.so_dong_goc.get(tbl, 0):         # mọi dòng gốc đã bị xoá khi chấp nhận sửa đổi → bảng không còn (khoảng trống thứ tự)
                self.bo += 1
                return None
            raise _ChuaDu("E3_BANG_KHONG_DONG", path)
        if len(self.bang) >= self.gh["so_bang"]:
            raise _ChuaDu("E3_QUA_SO_BANG", path)
        grid = self.mot(tbl, W + "tblGrid", path)
        cols = len(grid.findall(W + "gridCol")) if grid is not None else 0
        rec = {"id": self.id_("bang", path), "vi_tri": path, "parent_cell_id": cha_id, "thu_tu_nguon": thu_tu,
               "grid_cols": cols or None, "dong": []}
        self.bang.append(rec)                         # preorder: bảng cha trước bảng lồng
        truoc = None
        for tr in trs:
            r = self.dong_(tr, path, cols or None, truoc)
            rec["dong"].append(r)
            truoc = {o["grid_start"]: (o["grid_span"], o["v_merge"]) for o in r["o"]}
        return rec

    def dong_(self, tr, cha, cols, truoc):
        path, thu_tu = self.vi_tri(tr, cha)
        self.n_dong += 1
        if self.n_dong > self.gh["so_dong"]:
            raise _ChuaDu("E3_QUA_SO_DONG", path)
        trpr = self.mot(tr, W + "trPr", path)
        gb = self.so(trpr, "gridBefore", path, 0, 0)
        ga = self.so(trpr, "gridAfter", path, 0, 0)
        rec = {"id": self.id_("dong", path), "vi_tri": path, "thu_tu_nguon": thu_tu, "grid_before": gb, "grid_after": ga, "o": []}
        vi = gb
        for tc in self.cac_con(tr, W + "tc", (W + "trPr", W + "tblPrEx"), path):
            o = self.o_(tc, path, vi + 1, truoc)
            vi += o["grid_span"]
            rec["o"].append(o)
        if cols is not None and vi + ga > cols:
            raise _ChuaDu("E3_LUOI_MAU_THUAN", path)
        return rec

    def o_(self, tc, cha, gs, truoc):
        path, thu_tu = self.vi_tri(tc, cha)
        self.n_o += 1
        if self.n_o > self.gh["so_o"]:
            raise _ChuaDu("E3_QUA_SO_O", path)
        tcpr = self.mot(tc, W + "tcPr", path)
        span = self.so(tcpr, "gridSpan", path, 1, 1)
        if tcpr is not None and tcpr.find(W + "hMerge") is not None:
            raise _ChuaDu("E3_HMERGE_KHONG_HO_TRO", path)
        vm = "NONE"
        e = self.mot(tcpr, W + "vMerge", path) if tcpr is not None else None
        if e is not None:
            v = e.get(W + "val")
            if v in (None, "continue"):
                vm = "CONTINUE"
            elif v == "restart":
                vm = "RESTART"
            else:
                raise _ChuaDu("E3_VMERGE_KHONG_HOP_LE", path)
        if vm == "CONTINUE" and (not truoc or gs not in truoc or truoc[gs][0] != span or truoc[gs][1] == "NONE"):
            raise _ChuaDu("E3_VMERGE_MAU_THUAN", path)
        cid = self.id_("o", path)
        doan, con = [], []
        self.noi_dung(tc, path, cid, doan, con)
        text = "\n".join(doan)
        if len(text) > self.gh["ky_tu_o"]:
            raise _ChuaDu("E3_O_QUA_DAI", path)
        return {"id": cid, "vi_tri": path, "thu_tu_nguon": thu_tu, "grid_start": gs, "grid_span": span, "v_merge": vm,
                "text": text, "doan": doan, "bang_con": con}

    def noi_dung(self, container, path, cid, doan, con):
        """Chỉ đoạn TRỰC TIẾP của ô (kể cả qua w:sdt), theo thứ tự nguồn; bảng lồng → bản ghi riêng, không lặp chữ của nó."""
        for el in container:
            t = el.tag
            if t == W + "tcPr":
                continue
            if t == W + "p":
                if _chua(el, (W + "txbxContent", W + "tbl", W + "altChunk")) is not None:
                    raise _ChuaDu("E3_HOP_VAN_BAN_TRONG_O", path)
                s = _para_text(el)
                if s:
                    doan.append(s)
            elif t == W + "tbl":
                r = self.bang_(el, cid, path)
                if r is not None:
                    con.append(r["id"])
            elif t == W + "sdt":
                for c in el:
                    if c.tag == W + "sdtContent":
                        self.noi_dung(c, path, cid, doan, con)
                    elif _chua(c, _E3_NOI_DUNG) is not None:
                        raise _ChuaDu("E3_PHAN_TU_KHONG_HO_TRO", path)
            elif t == W + "altChunk":
                raise _ChuaDu("E3_ALTCHUNK", path)
            elif _chua(el, _E3_NOI_DUNG) is not None:
                raise _ChuaDu("E3_PHAN_TU_KHONG_HO_TRO", path)


def _co_json(o):
    return len(json.dumps(o, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _bn_khung(trang_thai, nguon, kieu, so_sua, ly_do, bang):
    return {"schema": E3_SCHEMA, "trang_thai": trang_thai, "pham_vi": E3_PHAM_VI, "nguon": dict(nguon),
            "bien_doi": {"kieu": kieu, "track_changes": int(so_sua or 0)}, "gioi_han": dict(E3_GIOI_HAN), "ly_do": ly_do, "bang": bang}


def _bn_chua_du(nguon, kieu, so_sua, ly_do):
    bn = _bn_khung("INCOMPLETE", nguon, kieu, so_sua, ly_do, [])
    if _co_json(bn) > E3_GIOI_HAN["json_bang_nguon"]:     # chẩn đoán cũng phải trong giới hạn
        bn["ly_do"] = [{"ma": x["ma"], "vi_tri": None} for x in ly_do[:1]]
    return bn


def _bang_nguon_docx(body, vt, kt, data, doc_raw, n_sua):
    """DTO source6-docx-tables/v1 cho bytes .docx đã đọc: DAY_DU chỉ khi đã duyệt TOÀN BỘ phạm vi bảng thân văn bản."""
    sha = hashlib.sha256(data).hexdigest()
    doc_sha = hashlib.sha256(doc_raw).hexdigest()
    nguon = {"source_sha256": sha, "source_bytes": len(data), "docx_sha256": sha, "docx_bytes": len(data), "document_xml_sha256": doc_sha}
    kieu = "ACCEPT_XML" if n_sua else "TRUC_TIEP"
    goc_body = vt[body][0] if body in vt else None
    try:
        if kt["loi"]:
            raise _ChuaDu(*kt["loi"])
        if kt["co_sua"] and not n_sua:                # có sửa đổi (theo namespace) nhưng bộ đếm cũ không thấy → chưa chấp nhận
            raise _ChuaDu("E3_SUA_DOI_CHUA_CHAP_NHAN", goc_body)
        g = _GomBang(vt, kt["so_dong_goc"], doc_sha)
        g.khoi(body, goc_body)
        if sum(1 for _ in body.iter(W + "tbl")) != len(g.bang) + g.bo:
            raise _ChuaDu("E3_BANG_NGOAI_PHAM_VI_DUYET", goc_body)
        bn = _bn_khung("DAY_DU", nguon, kieu, n_sua, [], sorted(g.bang, key=lambda b: b["thu_tu_nguon"]))
        if _co_json(bn) > E3_GIOI_HAN["json_bang_nguon"]:
            raise _ChuaDu("E3_JSON_QUA_LON", None)
        return bn
    except _ChuaDu as e:
        return _bn_chua_du(nguon, kieu, n_sua, [{"ma": e.ma, "vi_tri": e.vi_tri}])


def _bang_nguon_dau_vao(bn, nguon, da_chuyen, so_sua):
    """read_contract: source_* = bytes THẬT của file đầu vào gốc. Bản .docx đã đọc khác bytes gốc: do chuyển đổi → CHUYEN_DOCX + INCOMPLETE
    (dòng dõi chưa xác minh); không chuyển đổi → file đổi giữa hai lần đọc → INCOMPLETE. Không bao giờ coi bản dẫn xuất là bytes gốc."""
    nguon_moi = dict(bn["nguon"], source_sha256=nguon[0], source_bytes=nguon[1])
    if (nguon_moi["docx_sha256"], nguon_moi["docx_bytes"]) == tuple(nguon):
        return dict(bn, nguon=nguon_moi)
    if da_chuyen:
        cu = [{"ma": x["ma"], "vi_tri": None} for x in bn["ly_do"]]
        return _bn_chua_du(nguon_moi, "CHUYEN_DOCX", so_sua, [{"ma": "E3_CHUYEN_DOCX_CHUA_XAC_MINH", "vi_tri": None}] + cu)
    return _bn_chua_du(nguon_moi, bn["bien_doi"]["kieu"], bn["bien_doi"]["track_changes"],
                       [{"ma": "E3_NGUON_THAY_DOI", "vi_tri": None}] + bn["ly_do"])


def bang_nguon_khong_ho_tro(path, ma="E3_PDF_KHONG_HO_TRO", dan_xuat=None):
    """PDF (kể cả scan/OCR) → KHONG_HO_TRO, bang [] theo bytes THẬT của file gốc. dan_xuat = bang_nguon của .docx dẫn xuất (OCR) đã đọc:
    chỉ ghi dòng dõi (docx_*), KHÔNG dùng bảng của nó."""
    sha, n = _sha_tep(path)
    nguon = {"source_sha256": sha, "source_bytes": n, "docx_sha256": None, "docx_bytes": None, "document_xml_sha256": None}
    kieu = "TRUC_TIEP"
    if dan_xuat is not None:
        for k in ("docx_sha256", "docx_bytes", "document_xml_sha256"):
            nguon[k] = dan_xuat["nguon"][k]
        kieu = "CHUYEN_DOCX"
    return _bn_khung("KHONG_HO_TRO", nguon, kieu, 0, [{"ma": ma, "vi_tri": None}], [])


def read_docx(path):
    """Đọc .docx (đã/không có Track Changes — luôn tự chấp nhận trong XML). Trả (văn bản, thống kê).
    E3-01: ZIP/XML kiểm giới hạn trước khi phân tích (LoiE3); bằng chứng bảng thân văn bản đi riêng trong thống kê `_bang_nguon`."""
    data = _doc_tep_gioi_han(path)
    z, infos = _mo_zip(data)
    num = Numbering(z)
    doc_raw = _doc_member(z, infos, "word/document.xml")
    raw_xml = doc_raw.decode("utf-8", "ignore")
    n_sua = dem_sua_doi(raw_xml)
    root = _parse_xml(doc_raw, "word/document.xml")
    if root.tag != f"{W}document" or root.find(f"{W}body") is None:
        raise LoiE3("E3_XML_KHONG_HO_TRO", "word/document.xml không phải WordprocessingML (transitional) có w:body")
    vt, kt = _ban_do_goc(root)                   # E3-01: vị trí/thứ tự GỐC chụp trước khi chấp nhận sửa đổi
    if n_sua:
        chap_nhan_xml(root)
    body = root.find(f"{W}body")
    lines = []
    stats = {"numbered": 0, "tables": 0, "toc_skipped": 0, "appendix_images": 0, "big_tables": []}
    in_appendix = [False]

    def n_img(el):
        return sum(1 for x in el.iter() if x.tag in (f"{W}drawing", f"{W}pict"))

    def walk(container):
        for el in container:
            if el.tag == f"{W}p":
                lab = num.label(el)
                t = _para_text(el)
                if lab and lab != "-":
                    stats["numbered"] += 1
                if t or lab:
                    lines.append(f"{lab} {t}".strip() if lab else t)
                if APPENDIX.match(t) and len(t) < 150:
                    in_appendix[0] = True
                if in_appendix[0]:
                    stats["appendix_images"] += n_img(el)
            elif el.tag == f"{W}tbl":
                stats["tables"] += 1
                n0 = len(lines)
                if in_appendix[0]:
                    stats["appendix_images"] += n_img(el)
                trs = el.findall(f"{W}tr")
                for tr in trs:
                    cells = []
                    for tc in tr.findall(f"{W}tc"):
                        parts = []
                        for p in tc.iter(f"{W}p"):
                            lab, t = num.label(p), _para_text(p)
                            if t:
                                parts.append(f"{lab} {t}".strip() if lab and lab != "-" else t)
                        cells.append(" ".join(parts))
                    cells = [c for c in cells if c]
                    if cells:
                        lines.append(" | ".join(cells))
                chars = sum(len(x) for x in lines[n0:])
                if len(trs) >= BIG_TABLE_ROWS or chars >= BIG_TABLE_CHARS:
                    stats["big_tables"].append((stats["tables"], len(trs), chars))
            elif el.tag == f"{W}sdt":
                if _is_toc(el):
                    stats["toc_skipped"] += 1
                    continue
                c = el.find(f"{W}sdtContent")
                if c is not None:
                    walk(c)

    walk(body)
    # E3-01: SAU lượt văn bản cũ (không gọi lại num.label), TRƯỚC khi bỏ mục lục khỏi cây
    stats["_bang_nguon"] = _bang_nguon_docx(body, vt, kt, data, doc_raw, n_sua)
    for sdt in list(body.findall(f"{W}sdt")):
        if _is_toc(sdt):
            body.remove(sdt)
    raw_words = len(re.findall(r"\w+", "\n".join("".join(e.text or "" for e in p.iter(f"{W}t"))
                                                for p in root.iter(f"{W}p"))))
    stats.update({
        "raw_words": raw_words,
        "track_changes": n_sua,
        "images": raw_xml.count("<w:drawing") + raw_xml.count("<w:pict"),
        "textboxes": raw_xml.count("<w:txbxContent"),
        "embedded_objects": raw_xml.count("<w:object"),
    })
    return "\n".join(lines), stats


ART = re.compile(r"^(?:Điều|ĐIỀU|Article)\s+(\d+)\s*[\.:\-–]?\s*(.*)$")


def split_articles(text):
    """Tách theo 'Điều N'. Bỏ qua mục lục (dòng kết thúc bằng số trang, dòng bảng)."""
    L = text.split("\n")
    pos = {}
    for i, line in enumerate(L):
        m = ART.match(line.strip())
        if m and "|" not in line and not re.search(r"\s\d{1,3}$", line.strip()):
            pos[int(m.group(1))] = (i, m.group(2).strip())
    if not pos:
        return {"preamble": text, "articles": {}}
    ks = sorted(pos, key=lambda k: pos[k][0])
    arts = {}
    for n, k in enumerate(ks):
        j = pos[ks[n + 1]][0] if n + 1 < len(ks) else len(L)
        arts[k] = {"title": pos[k][1], "text": "\n".join(L[pos[k][0]:j])}
    return {"preamble": "\n".join(L[:pos[ks[0]][0]]), "articles": arts}


def _vn(n):
    return f"{n:,}".replace(",", ".")


def chunk_text(text, size=CHUNK_CHARS):
    pieces = []
    for line in text.split("\n"):
        while len(line) > size:
            cut = line.rfind(" ", 0, size)
            cut = cut if cut > size // 2 else size
            pieces.append(line[:cut])
            line = line[cut:].lstrip()
        pieces.append(line)
    chunks, buf, n = [], [], 0
    for p in pieces:
        if buf and n + len(p) > size:
            chunks.append("\n".join(buf))
            buf, n = [], 0
        buf.append(p)
        n += len(p) + 1
    if "\n".join(buf).strip():
        chunks.append("\n".join(buf))
    return [c for c in chunks if c.strip()]


def read_pdf(path):
    """PDF có lớp chữ → văn bản (pdfplumber, không có thì pypdf). PDF scan (ảnh) → lỗi rõ ràng."""
    trang = []
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            trang = [(pg.extract_text() or "") for pg in pdf.pages]
    except ImportError:
        try:
            import pypdf
            trang = [(pg.extract_text() or "") for pg in pypdf.PdfReader(path).pages]
        except ImportError:
            raise RuntimeError("Đọc PDF cần thư viện pdfplumber (pip install pdfplumber)") from None
    lines = []
    for t in trang:
        for ln in t.split("\n"):
            ln = re.sub(r"[ \u00a0]+", " ", ln).strip()
            if not ln or re.fullmatch(r"(trang\s*)?\d{1,3}(\s*/\s*\d{1,3})?", ln, re.I):   # số trang
                continue
            lines.append(ln)
    text = "\n".join(lines)
    n_tu = len(re.findall(r"\w+", text))
    if n_tu < max(80, 20 * len(trang)):
        raise ValueError(f"PDF {len(trang)} trang nhưng chỉ đọc được {n_tu} từ — có thể là bản scan (ảnh). Cần bản Word "
                         "hoặc PDF có chữ, hoặc bật OCR ABBYY trong Cài đặt.")
    return text, {"pages": len(trang), "raw_words": n_tu}


def _co_sua_doi(path):
    try:
        data = _doc_tep_gioi_han(path)
    except OSError:
        return 0
    z, infos = _mo_zip(data)                     # E3-01: không đọc member chưa kiểm (vi phạm → LoiE3, không trả 0)
    return dem_sua_doi(_doc_member(z, infos, "word/document.xml").decode("utf-8", "ignore"))


def read_contract(path):
    """Đọc 1 hợp đồng. Trả dict: text, preamble, articles, chunks, report (phiếu kiểm tra đầu vào), bang_nguon (E3-01)."""
    src = path
    duoi = os.path.splitext(path)[1].lower()
    if duoi == ".pdf":
        return _read_contract_pdf(path)
    if duoi not in (".docx", ".doc"):
        raise ValueError("Chỉ đọc được file Word .docx / .doc hoặc PDF có chữ")
    nguon = _sha_tep(path)                       # E3-01: bytes THẬT của file đầu vào gốc, trước mọi chuyển đổi
    accept = {"so": 0, "cach": ""}
    tam = None
    if duoi == ".doc":
        path, n, cach = chuyen_docx(path)
        tam = os.path.dirname(path)
        accept = {"so": n, "cach": cach}
    else:
        _kiem_docx_an_toan(path)                 # E3-01: ZIP/XML an toàn TRƯỚC khi đọc/chuyển đổi kiểu cũ
        n0 = _co_sua_doi(path)
        if n0:
            path, n, cach = chuyen_docx(path)
            tam = os.path.dirname(path)
            accept = {"so": n if n is not None else n0, "cach": cach}
    try:
        text, st = read_docx(path)
        # chữ tổ hợp (vd "xa" + dấu sắc rời, hay gặp ở file .doc cũ) → dạng dựng sẵn, để trích dẫn của AI khớp nguyên văn
        st["to_hop"] = sum(1 for c in text if unicodedata.combining(c))
        text = unicodedata.normalize("NFC", text)
    finally:
        if tam:
            shutil.rmtree(tam, ignore_errors=True)
    if st["track_changes"] and not accept["so"]:            # sửa đổi còn lại sau Word/LibreOffice → Python chấp nhận
        accept = {"so": st["track_changes"], "cach": accept["cach"] + (" + " if accept["cach"] else "") + "Python"}
    bang_nguon = _bang_nguon_dau_vao(st.pop("_bang_nguon"), nguon, tam is not None, accept["so"])
    sp = split_articles(text)
    words = len(re.findall(r"\w+", text))
    nums = sorted(sp["articles"])
    gaps = [n for n in range(1, (max(nums) if nums else 0) + 1) if n not in nums]
    chunks = [] if nums else chunk_text(text)
    warn = []
    if nums and gaps:
        warn.append(f"Thiếu Điều số: {gaps}")
    if not nums:
        warn.append(f"Không nhận diện được 'Điều N' → đã tự chia thành {len(chunks)} đoạn ~{_vn(CHUNK_CHARS)} ký tự "
                    "(vị trí ghi 'Đoạn k'); nên soát kỹ kết quả")
    elif len(nums) < MIN_ARTICLES:
        warn.append(f"Chỉ nhận diện được {len(nums)} Điều (< {MIN_ARTICLES}) — có thể HĐ không đánh 'Điều N' chuẩn; nên soát kỹ")
    if st["appendix_images"]:
        warn.append(f"Có {st['appendix_images']} ảnh trong phần Phụ lục — nội dung dạng ảnh (bảng giá, tiến độ scan…) "
                    "KHÔNG đọc được")
    for i, nrow, nch in st["big_tables"]:
        warn.append(f"Bảng rất lớn (bảng thứ {i}: {nrow} dòng, {_vn(nch)} ký tự) — AI chỉ nhận tối đa ~14.000 ký tự "
                    "mỗi nhóm nên có thể bị cắt")
    if accept["so"]:
        warn.append(f"Có {accept['so']} chỗ Track Changes → đã Accept All trên bản sao ({accept['cach']}); file gốc không đổi")
    if st["textboxes"]:
        warn.append(f"Có {st['textboxes']} ô chữ nổi (text box)")
    if st["embedded_objects"]:
        warn.append(f"Có {st['embedded_objects']} đối tượng nhúng (vd bảng Excel) — KHÔNG đọc được")
    if words < st["raw_words"] * 0.97:
        warn.append(f"Số từ đọc được ({words}) < 97% số từ trong file ({st['raw_words']})")
    report = {
        "file": os.path.basename(src), "words": words, "raw_words": st["raw_words"],
        "articles": len(nums), "article_range": f"{min(nums)}–{max(nums)}" if nums else "-",
        "numbered_paragraphs": st["numbered"], "tables": st["tables"], "images": st["images"],
        "toc_skipped": st["toc_skipped"], "track_changes_accepted": accept["so"], "accept_by": accept["cach"],
        "warnings": warn,
    }
    if chunks:
        report["chunks"] = len(chunks)
    return {"text": text, "preamble": sp["preamble"], "articles": sp["articles"], "chunks": chunks, "report": report,
            "bang_nguon": bang_nguon}


def _read_contract_pdf(path):
    text, st = read_pdf(path)
    text = unicodedata.normalize("NFC", text)
    sp = split_articles(text)
    words = len(re.findall(r"\w+", text))
    nums = sorted(sp["articles"])
    gaps = [n for n in range(1, (max(nums) if nums else 0) + 1) if n not in nums]
    chunks = [] if nums else chunk_text(text)
    warn = ["File PDF: số tự động và bảng được đọc theo lớp chữ của PDF; nếu có bản Word nên dùng bản Word"]
    if nums and gaps:
        warn.append(f"Thiếu Điều số: {gaps}")
    if not nums:
        warn.append(f"Không nhận diện được 'Điều N' → đã tự chia thành {len(chunks)} đoạn ~{_vn(CHUNK_CHARS)} ký tự")
    elif len(nums) < MIN_ARTICLES:
        warn.append(f"Chỉ nhận diện được {len(nums)} Điều (< {MIN_ARTICLES}) — nên soát kỹ")
    report = {"file": os.path.basename(path), "words": words, "raw_words": st["raw_words"], "pages": st["pages"],
              "articles": len(nums), "article_range": f"{min(nums)}–{max(nums)}" if nums else "-",
              "numbered_paragraphs": 0, "tables": 0, "images": 0, "toc_skipped": 0, "track_changes_accepted": 0,
              "accept_by": "", "warnings": warn}
    if chunks:
        report["chunks"] = len(chunks)
    return {"text": text, "preamble": sp["preamble"], "articles": sp["articles"], "chunks": chunks, "report": report,
            "bang_nguon": bang_nguon_khong_ho_tro(path)}


def print_report(info):
    r = info["report"]
    print(f"\n=== PHIẾU KIỂM TRA ĐẦU VÀO: {r['file']}")
    print(f"  Số từ đọc được / trong file : {r['words']:,} / {r['raw_words']:,}")
    print(f"  Đoạn có số tự động đã dựng  : {r['numbered_paragraphs']}")
    print(f"  Số Điều nhận diện           : {r['articles']} (Điều {r['article_range']})"
          + (f" → tự chia {r['chunks']} đoạn" if r.get("chunks") else ""))
    print(f"  Bảng / ảnh / mục lục bỏ qua : {r['tables']} / {r['images']} / {r['toc_skipped']}")
    print("  Cảnh báo:", "; ".join(r["warnings"]) if r["warnings"] else "không có")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for f in sys.argv[1:]:
        info = read_contract(f)
        print_report(info)
        out = os.path.splitext(f)[0] + ".txt"
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(info["text"])
        print(f"  Đã lưu văn bản: {out}")
