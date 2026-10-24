# -*- coding: utf-8 -*-
"""
doc_hop_dong.py — Đọc hợp đồng Word (.docx/.doc) ra văn bản, GIỮ SỐ ĐIỀU/KHOẢN ĐÁNH TỰ ĐỘNG, tách theo Điều,
và lập "phiếu kiểm tra đầu vào". Chỉ dùng thư viện chuẩn Python.

Track Changes: hợp đồng còn sửa đổi chưa chấp nhận → Accept All trên BẢN SAO tạm (Word trên Windows; không có Word
thì Python tự chấp nhận trong XML). File gốc không bị đổi. Phiếu kiểm tra ghi rõ đã chấp nhận bao nhiêu chỗ, bằng cách nào.

    python -m trich_xuat.doc_hop_dong hop_dong.docx      → in phiếu kiểm tra + lưu hop_dong.txt cạnh file
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
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
            root = ET.fromstring(z.read("word/numbering.xml"))
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
            st = ET.fromstring(z.read("word/styles.xml"))
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


def read_docx(path):
    """Đọc .docx (đã/không có Track Changes — luôn tự chấp nhận trong XML). Trả (văn bản, thống kê)."""
    z = zipfile.ZipFile(path)
    num = Numbering(z)
    raw_xml = z.read("word/document.xml").decode("utf-8", "ignore")
    n_sua = dem_sua_doi(raw_xml)
    root = ET.fromstring(z.read("word/document.xml"))
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
        with zipfile.ZipFile(path) as z:
            return dem_sua_doi(z.read("word/document.xml").decode("utf-8", "ignore"))
    except (OSError, KeyError, zipfile.BadZipFile):
        return 0


def read_contract(path):
    """Đọc 1 hợp đồng. Trả dict: text, preamble, articles, chunks, report (phiếu kiểm tra đầu vào)."""
    src = path
    duoi = os.path.splitext(path)[1].lower()
    if duoi == ".pdf":
        return _read_contract_pdf(path)
    if duoi not in (".docx", ".doc"):
        raise ValueError("Chỉ đọc được file Word .docx / .doc hoặc PDF có chữ")
    accept = {"so": 0, "cach": ""}
    tam = None
    if duoi == ".doc":
        path, n, cach = chuyen_docx(path)
        tam = os.path.dirname(path)
        accept = {"so": n, "cach": cach}
    else:
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
    return {"text": text, "preamble": sp["preamble"], "articles": sp["articles"], "chunks": chunks, "report": report}


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
    return {"text": text, "preamble": sp["preamble"], "articles": sp["articles"], "chunks": chunks, "report": report}


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
