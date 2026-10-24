# -*- coding: utf-8 -*-
"""
chung_tu.py — Lớp 3: CHỨNG TỪ của một đợt thanh toán (quy trình mục 4 B4, mục 5 B5).

Tài liệu: BB nghiệm thu KL đợt, BB giao nhận vật tư / thiết bị, packing list, CO (xuất xứ), CQ (chất lượng),
BB lắp đặt / chạy thử. PDF / ảnh scan → OCR ABBYY trên máy; Word, Excel đọc trực tiếp.

Python làm: phân loại theo tiêu đề, đọc số / ngày, đọc bảng dòng hàng (tên, model, quy cách, ĐVT, số lượng, số lô /
serial, xuất xứ, nhà sản xuất), ghép với hạng mục của hồ sơ thanh toán, đối chiếu số lượng, đối chiếu chéo các chứng
từ, ngày tháng. Local AI chỉ đọc dòng hàng khi chứng từ không có bảng (vd CO dạng form), có trích dẫn nguyên văn để
Python tìm lại; dòng AI đọc ghi rõ nguồn và cần anh xác nhận.

Mã phát hiện:
  C01 KL kỳ này trong hồ sơ ≠ / không có trong BB nghiệm thu    C02 Ngày BB nghiệm thu ≠ ngày nghiệm thu của đợt
  C03 Σ số lượng giao < KL lũy kế đề nghị                          C04 Dòng hàng không ghép được hạng mục HĐ
  C05 Thiếu CO / CQ / packing list cho dòng hàng đã giao           C06 Số lượng / model / số lô lệch giữa các chứng từ
  C07 Ngày tháng bất hợp lý (CO/CQ sau giao, giao sau nghiệm thu, lắp đặt trước giao…)
  C08 Chứng từ ghi số hợp đồng khác                               C09 Thiếu số / ngày chứng từ, không đọc được dòng hàng
"""
import datetime
import difflib
import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path

from trich_xuat import cau_hinh as ch
from trich_xuat import ocr_abbyy as ocr

LOAI = {"BB_NT": "BB nghiệm thu khối lượng", "BB_GN": "BB giao nhận vật tư / thiết bị", "PL": "Packing list",
        "CO": "CO — chứng nhận xuất xứ", "CQ": "CQ — chứng nhận chất lượng", "BB_LD": "BB lắp đặt / chạy thử",
        "KHAC": "Khác / chưa phân loại"}
DUOI = (".pdf", ".docx", ".doc", ".xlsx", ".xlsm", ".xls", ".jpg", ".jpeg", ".png", ".tif", ".tiff")
SCHEMA_CT = {"type": "object", "properties": {"dong": {"type": "array", "items": {"type": "object", "properties": {
    k: {"type": "string"} for k in ("ten", "model", "quy_cach", "dvt", "so_luong", "lo", "xuat_xu", "nsx", "trich_dan")},
    "required": ["ten", "so_luong", "trich_dan"]}}}, "required": ["dong"]}


def _bd(s):
    from master_hd import bo_dau
    return bo_dau(s)


def _gon(s):
    return re.sub(r"[^0-9a-z]+", "", _bd(s))


def thu_muc_kq():
    p = ch.thu_muc_du_lieu() / "chung_tu"
    p.mkdir(parents=True, exist_ok=True)
    return p


# ================================================================== đọc file
def doc_file(path, tien_do=None, dung=None, ghi_log=None):
    """→ {dong: [câu], bang: [[[ô]]], ocr: info|None, canh_bao: []}"""
    from trich_xuat.doc_hop_dong import chuyen_docx, read_docx, read_pdf
    import unicodedata
    duoi = os.path.splitext(path)[1].lower()
    info_ocr, canh, tam = None, [], None
    if duoi == ".xls":                                   # Excel 97-2003 → .xlsx (chỉ cần giá trị)
        from .doi_xls import LoiXls, chuan_hoa
        try:
            path, _ = chuan_hoa(path)
        except LoiXls as e:
            raise ValueError(str(e)) from None
        duoi = ".xlsx"
    if duoi in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        bang, dong = [], []
        for ws in wb.worksheets:
            rows = []
            for r in ws.iter_rows(max_row=400, max_col=30, values_only=True):
                cells = ["" if v is None else (v.strftime("%d/%m/%Y") if isinstance(v, (datetime.date, datetime.datetime))
                                                else str(v)).strip() for v in r]
                if any(cells):
                    rows.append(cells)
                    dong.append(" | ".join(c for c in cells if c))
            if rows:
                bang.append(rows)
        wb.close()
        return {"dong": [unicodedata.normalize("NFC", x) for x in dong], "bang": bang, "ocr": None, "canh_bao": canh}
    docx = None
    if duoi in (".jpg", ".jpeg", ".png", ".tif", ".tiff"):
        docx, info_ocr = ocr.ocr_docx(path, tien_do=tien_do, dung=dung, ghi_log=ghi_log)
    elif duoi == ".pdf":
        p2, info_ocr = ocr.chuan_bi_pdf(path, tien_do=tien_do, dung=dung, ghi_log=ghi_log)
        if info_ocr:
            docx = p2
        else:
            text, _ = read_pdf(path)
            canh.append("PDF có lớp chữ: bảng đọc theo lớp chữ không tách được cột — dòng hàng đọc bằng Local AI.")
            return {"dong": [unicodedata.normalize("NFC", x) for x in text.split("\n") if x.strip()], "bang": [],
                    "ocr": None, "canh_bao": canh}
    elif duoi == ".docx":
        docx = path
    elif duoi == ".doc":
        docx, _, _ = chuyen_docx(path)
        tam = os.path.dirname(docx)
    else:
        raise ValueError(f"Chưa đọc được loại file {duoi}")
    try:
        text, _ = read_docx(docx)
        bang = ocr.docx_bang(docx)[1]
    finally:
        if tam:
            shutil.rmtree(tam, ignore_errors=True)
    text = unicodedata.normalize("NFC", text)
    bang = [[[unicodedata.normalize("NFC", c) for c in r] for r in b] for b in bang]
    return {"dong": [x for x in text.split("\n") if x.strip()], "bang": bang, "ocr": info_ocr, "canh_bao": canh}


# ================================================================== phân loại, số, ngày
_MAU_LOAI = [
    ("BB_LD", r"bien ban (nghiem thu )?(lap dat|chay thu|van hanh thu|thu nghiem|hieu chinh)|commissioning|installation"),
    ("BB_NT", r"bien ban nghiem thu (khoi luong|cong viec|hoan thanh|giai doan|ky|dot)|xac nhan khoi luong|bang xac nhan khoi luong"),
    ("BB_GN", r"bien ban (giao nhan|ban giao)|phieu (giao hang|xuat kho|nhap kho)|delivery (note|record)|bien ban nghiem thu vat (lieu|tu)|nghiem thu (vat lieu|vat tu|thiet bi) dau vao"),
    ("PL", r"packing list|phieu dong goi|chi tiet dong goi|danh sach dong goi"),
    ("CO", r"certificate of origin|chung nhan xuat xu|giay chung nhan xuat xu|\bc/o\b|\bform (ak|aj|ai|e|d|vk|vj|b)\b"),
    ("CQ", r"certificate of (quality|conformity|analysis)|mill test|chung (nhan|chi) chat luong|phieu (kiem tra|ket qua) (chat luong|thu nghiem)|chung nhan hop (chuan|quy)|\bc/q\b|test certificate"),
]


def phan_loai(dong, ten_file=""):
    for loai, pat in _MAU_LOAI:
        for ln in dong[:30]:
            if re.search(pat, _bd(ln)):
                return loai, "tiêu đề: “" + " ".join(ln.split())[:80] + "”"
    ten = _bd(ten_file)
    for loai, pat in [("CO", r"\bco\b"), ("CQ", r"\bcq\b"), ("PL", r"packing|\bpl\b"), ("BB_GN", r"giao nhan|ban giao"),
                      ("BB_LD", r"lap dat|chay thu"), ("BB_NT", r"nghiem thu")] + _MAU_LOAI:
        if re.search(pat, ten):
            return loai, "tên file"
    return "KHAC", ""


THANG = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11,
         "dec": 12}


def _iso(d, m, y):
    try:
        return datetime.date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return None


def tim_ngay(dong):
    """Ngày của chứng từ: 'ngày … tháng … năm …' → 'Date: dd/mm/yyyy' → dd/mm/yyyy đầu tiên. → (iso, câu)"""
    for pat, lim in ((r"ngay\s*(\d{1,2})\s*thang\s*(\d{1,2})\s*nam\s*(\d{4})", 60),
                     (r"(?:date|ngay)\s*(?:of issue|cap|lap)?\s*[:.]?\s*(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]\s*(\d{4})", 60),
                     (r"(?<!\d)(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]\s*(\d{4})(?!\d)", 80)):
        for ln in dong[:lim]:
            m = re.search(pat, _bd(ln))
            if m and _iso(*m.groups()):
                return _iso(*m.groups()), ln.strip()[:200]
    for ln in dong[:80]:
        m = re.search(r"(\d{1,2})\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s*(\d{4})", _bd(ln))
        if m and _iso(m.group(1), THANG[m.group(2)], m.group(3)):
            return _iso(m.group(1), THANG[m.group(2)], m.group(3)), ln.strip()[:200]
        m = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(\d{1,2}),?\s*(\d{4})", _bd(ln))
        if m and _iso(m.group(2), THANG[m.group(1)], m.group(3)):
            return _iso(m.group(2), THANG[m.group(1)], m.group(3)), ln.strip()[:200]
    return None, ""


def tim_so(dong):
    for ln in dong[:25]:
        b = _bd(ln)
        for m in re.finditer(r"(?:^|[\s(])(?:so|no\.?|number|ref)\s*[:.]?\s*([a-z0-9][\w/.\-]{1,30})", b):
            g = m.group(1).strip(" .:")
            if not re.search(r"\d", g) or re.fullmatch(r"\d{1,2}", g):
                continue
            if re.search(r"(hop dong|contract|hd)\s+(so|no\.?|number)\s*[:.]?\s*$", b[:m.start(1)]):
                continue                                   # "hợp đồng số …" là số HĐ, không phải số chứng từ
            raw = re.search(re.escape(g).replace("\\-", "[\\-–]"), ln, re.I)
            return (raw.group(0) if raw else g).strip(" .:"), ln.strip()[:200]
    return "", ""


def so_hop_dong(dong):
    """Các số hợp đồng 'NNNN/YYYY' được nhắc (để biết chứng từ thuộc HĐ nào)."""
    out = []
    for ln in dong[:80]:
        b = _bd(ln)
        if "hop dong" in b or "contract" in b or "hd" in b.split():
            for a, y in re.findall(r"(?<!\d)0*(\d{1,4})\s*/\s*(\d{4})(?!\d)", b):
                if (a, y) not in out:
                    out.append((a, y))
    return out


# ================================================================== dòng hàng từ bảng
def _cot(t):
    from master_hd import bo_dau_tieu_de
    t = re.sub(r"\s+", " ", bo_dau_tieu_de(t)).strip()             # chịu lỗi OCR ở tiêu đề cột
    if not t:
        return None
    if re.search(r"(khoi luong|\bkl\b).*(ky nay|dot nay)", t):
        return "kl_kn"
    if re.search(r"(khoi luong|\bkl\b).*luy ke", t):
        return "kl_lk"
    if re.search(r"(khoi luong|\bkl\b).*(hop dong|\bhd\b|ky truoc)", t):
        return "bo"
    if re.search(r"so luong|quantity|\bqty\b|khoi luong|\bkl\b|q'?ty", t):
        return "sl"
    if re.search(r"so lo|\blot\b|batch|serial|\bs/?n\b|so seri|so hieu san xuat|heat no", t):
        return "lo"
    if re.search(r"xuat xu|origin|country", t):
        return "xuat_xu"
    if re.search(r"nha san xuat|hang san xuat|manufactur|\bmaker\b|\bhang\b$", t):
        return "nsx"
    if re.search(r"^(model|ma hieu|ky hieu|ma hang|part ?no|type|code|ma so)\b|model|ma hieu", t):
        return "model"
    if re.search(r"quy cach|thong so|specification|\bspec", t):
        return "quy_cach"
    if re.search(r"^(dvt|don vi|unit|uom|d\.? ?vt)\b", t):
        return "dvt"
    if re.search(r"^(stt|tt|no\.?|item|so tt)$", t):
        return "stt"
    if re.search(r"ghi chu|remark|note", t):
        return "ghi_chu"
    if re.search(r"ten|noi dung|description|mo ta|hang muc|vat tu|thiet bi|hang hoa|goods|commodity|cong viec", t):
        return "ten"
    return None


def _tieu_de(row):
    cot = {}
    for j, c in enumerate(row):
        k = _cot(c)
        if k and k not in cot:
            cot[k] = j
    ok = ("ten" in cot or "model" in cot) and any(k in cot for k in ("sl", "kl_kn", "kl_lk"))
    return cot if ok else None


def dong_hang(bangs, loai):
    """Các bảng của chứng từ → [{ten, model, quy_cach, dvt, so_luong, kl_lk, lo, xuat_xu, nsx, nhom, vi_tri}]."""
    out = []
    for bi, b in enumerate(bangs, 1):
        cot, h = None, 0
        for h in range(min(4, len(b))):
            cot = _tieu_de(b[h])
            if cot:
                break
        if not cot:
            continue
        nhom = ""
        for r, row in enumerate(b[h + 1:], h + 2):
            g = lambda k: (row[cot[k]] if k in cot and cot[k] < len(row) else "").strip()  # noqa: E731
            ten = g("ten") or g("model")
            if not ten:
                continue
            if re.fullmatch(r"[\s()\d.,=x*+/\-]+", ten) and not g("model"):
                continue                                         # dòng đánh số cột
            low = _bd(ten)
            if re.match(r"^(tong|cong|total|sum)\b", low) and not g("dvt"):
                break
            sl = ocr.so_vn(g("kl_kn") or g("sl")) if (g("kl_kn") or g("sl")) else None
            if sl is None and not g("dvt") and not g("model"):
                nhom = re.sub(r"\s+", " ", ten).strip()
                continue
            out.append({"ten": re.sub(r"\s+", " ", g("ten") or ten).strip(), "model": g("model"), "quy_cach": g("quy_cach"),
                        "dvt": g("dvt"), "so_luong": sl, "kl_lk": ocr.so_vn(g("kl_lk")) if g("kl_lk") else None,
                        "lo": g("lo"), "xuat_xu": g("xuat_xu"), "nsx": g("nsx"), "nhom": nhom, "stt": g("stt"),
                        "vi_tri": f"bảng {bi} dòng {r}", "nguon": "bảng", "trich_dan": " | ".join(x for x in row if x)[:300]})
    return out


def doc_dong_ai(ai, dong, loai, ghi_log=None):
    """Chứng từ không có bảng (vd CO dạng form): Local AI đọc dòng hàng, mỗi dòng kèm câu trích nguyên văn."""
    from trich_xuat.ai_local import CTX_TRICH, DaDung
    text = "\n".join(dong)[:10000]
    prompt = (f"CHỨNG TỪ CẦN ĐỌC (loại: {LOAI.get(loai, loai)}; văn bản OCR, có thể sai chính tả):\n{text}\n\n"
              "YÊU CẦU: liệt kê các dòng hàng (vật tư, thiết bị, hàng hoá) ghi trong chứng từ. Mỗi dòng: ten, model (mã hiệu),"
              " quy_cach, dvt, so_luong (giữ nguyên cách viết số), lo (số lô / serial nếu có), xuat_xu, nsx (nhà sản xuất),"
              " trich_dan = đoạn NGUYÊN VĂN trong chứng từ chứa dòng đó. Không suy diễn; không có thì để trống.")
    try:
        data, _, _ = ai.chat_json(prompt, SCHEMA_CT, "dong", CTX_TRICH, "chứng từ")
    except DaDung:
        raise
    except Exception as e:  # noqa: BLE001
        if ghi_log:
            ghi_log(f"  {getattr(ai, 'ten', 'Local AI')} lỗi khi đọc chứng từ: {type(e).__name__}: {str(e)[:120]}")
        return [], f"Không hỏi được {getattr(ai, 'ten', 'Local AI')} ({type(e).__name__})"
    from .phu_luc_ai import kiem_trich
    tg = _gon(text)
    out = []
    for i, x in enumerate(data.get("dong") or [], 1):
        if not isinstance(x, dict) or not str(x.get("ten") or x.get("model") or "").strip():
            continue
        sl = ocr.so_vn(str(x.get("so_luong") or "").strip())
        kt = kiem_trich(x.get("trich_dan"), tg)
        if not kt and sl is not None and _gon(str(x.get("so_luong"))) not in _gon(x.get("trich_dan")):
            kt = "Số lượng không có trong trích dẫn"
        out.append({"ten": str(x.get("ten") or "").strip(), "model": str(x.get("model") or "").strip(),
                    "quy_cach": str(x.get("quy_cach") or "").strip(), "dvt": str(x.get("dvt") or "").strip(),
                    "so_luong": sl, "kl_lk": None, "lo": str(x.get("lo") or "").strip(),
                    "xuat_xu": str(x.get("xuat_xu") or "").strip(), "nsx": str(x.get("nsx") or "").strip(), "nhom": "",
                    "stt": str(i), "vi_tri": f"{getattr(ai, 'ten', 'Local AI')} dòng {i}", "nguon": getattr(ai, "ten", "Local AI"),
                    "trich_dan": str(x.get("trich_dan") or "")[:300], "kiem_tra": kt})
    return out, ""


# ================================================================== ghép & đối chiếu
def _model(s):
    g = re.sub(r"[^0-9a-z]", "", _bd(s))
    return g if len(g) >= 3 else ""


def _lo(s):
    return {x for x in re.split(r"[,;/\s]+", re.sub(r"[^0-9a-z,;/\s\-]", "", _bd(s))) if len(x) >= 3}


def _giong_ten(a, b):
    a, b = _bd(a)[:120], _bd(b)[:120]
    if not a or not b:
        return 0.0
    r = difflib.SequenceMatcher(None, a, b).ratio()
    n = min(len(a), len(b))
    if n >= 15:
        r = max(r, 0.97 * difflib.SequenceMatcher(None, a[:n], b[:n]).ratio())
    return r


def ghep_hang_muc(dong, hm):
    """Ghép một dòng chứng từ với hạng mục hồ sơ (hm: {khoá: {ten, dvt, stt, model?}}) → (khoá, độ khớp)."""
    from .phu_luc_ai import khop_hang_muc
    it = {"ten": " ".join(x for x in (dong.get("ten"), dong.get("model"), dong.get("quy_cach")) if x)[:200],
          "dvt": dong.get("dvt") or "", "stt": ""}
    k, r = khop_hang_muc(it, hm)
    if not k:
        k, r = khop_hang_muc({"ten": dong.get("ten") or "", "dvt": dong.get("dvt") or "", "stt": ""}, hm)
    if not k and dong.get("model"):
        mm = _model(dong["model"])
        c = [kk for kk, v in hm.items() if mm and mm in _gon(v["ten"])]
        if len(c) == 1:
            return c[0], 0.9
    if not k:
        # tên trên chứng từ thường ngắn hơn tên hạng mục BOQ ("Ống HDPE D110 PN10" ↔ "Cung cấp, lắp đặt ống HDPE D110"):
        # ghép theo từ khoá đặc trưng (có chữ số hoặc ≥ 4 chữ cái) trùng
        a = _tu(" ".join(x for x in (dong.get("ten"), dong.get("model"), dong.get("quy_cach")) if x))
        if a:
            diem = []
            for kk, v in hm.items():
                b = _tu(v["ten"])
                chung = a & b
                if not any(re.search(r"\d", x) or len(x) >= 4 for x in chung):
                    continue
                s = len(chung) / len(a) + 0.15 * sum(1 for x in chung if re.search(r"\d", x))
                if dong.get("dvt") and v.get("dvt") and _gon(dong["dvt"]) != _gon(v["dvt"]):
                    s -= 0.3
                diem.append((s, kk))
            diem.sort(reverse=True)
            if diem and diem[0][0] >= 0.6 and (len(diem) == 1 or diem[0][0] - diem[1][0] >= 0.15):
                return diem[0][1], round(min(0.95, diem[0][0]), 3)
    return k, r


_TU_BO = {"va", "cac", "cua", "cho", "the", "and", "for", "of", "loai", "bang", "cung", "cap", "lap", "dat", "thi", "cong",
          "vat", "tu", "thiet", "bi", "hang", "hoa"}


def _tu(s):
    return {x for x in re.findall(r"[0-9a-z]+", _bd(s)) if len(x) >= 2 and x not in _TU_BO}


def _cung_hang(a, b):
    """Hai dòng chứng từ là cùng một mặt hàng? model trùng → lô trùng → tên gần đúng."""
    ma, mb = _model(a.get("model")), _model(b.get("model"))
    if ma and mb:
        return ma == mb or ma in mb or mb in ma
    if _lo(a.get("lo")) & _lo(b.get("lo")):
        return True
    return _giong_ten(a.get("ten"), b.get("ten")) >= 0.85


def doi_chieu(kq):
    """Tính ma trận hạng mục × chứng từ và các phát hiện C01–C09. Ghi vào kq."""
    hm = {h["khoa"]: h for h in kq["hang_muc"]}
    ngay_nt = kq.get("ngay_nt")
    ngay_ky = kq.get("ngay_ky_hd")
    vat = kq.get("vat") or 0
    ph = []

    def them(code, level, title, detail, item="", tai_lieu="", amount=None):
        ph.append({"id": "", "code": code, "layer": 3, "level": level, "title": title, "detail": detail,
                   "amount": amount, "item": item, "tai_lieu": tai_lieu})
    docs = [d for d in kq["tai_lieu"] if not d.get("bo")]
    m_hd = re.match(r"\s*0*(\d+)\s*/\s*(\d{4})", str(kq.get("so_hd") or ""))
    sn = {(m_hd.group(1), m_hd.group(2))} if m_hd else set()
    # ghép từng dòng với hạng mục
    for d in docs:
        for ln in d["dong"]:
            ln["khoa"], ln["khop"] = (None, 0.0)
            if d["loai"] in ("BB_NT", "BB_GN", "BB_LD", "PL", "CO", "CQ") and hm:
                k, r = ghep_hang_muc(ln, hm)
                ln["khoa"], ln["khop"] = k, round(r or 0, 3)
        if not d.get("so") and d["loai"] != "KHAC":
            them("C09", "Thấp", f"{d['ten']}: không đọc được số chứng từ", "Kiểm tra bản scan; ghi số chứng từ tay nếu cần.",
                 tai_lieu=d["ten"])
        if not d.get("ngay") and d["loai"] != "KHAC":
            them("C09", "Trung bình", f"{d['ten']}: không đọc được ngày chứng từ",
                 "Chứng từ không có ngày thì không đối chiếu được mốc thời gian.", tai_lieu=d["ten"])
        if not d["dong"] and d["loai"] != "KHAC":
            them("C09", "Trung bình", f"{d['ten']}: không đọc được dòng hàng nào",
                 "Không có bảng dòng hàng (hoặc bảng dạng ảnh); Local AI cũng không đọc được.", tai_lieu=d["ten"])
        lech = [x for x in d.get("hd_ref") or [] if sn and tuple(x) not in sn]
        if lech and sn and not any(tuple(x) in sn for x in d.get("hd_ref") or []):
            them("C08", "Cao", f"{d['ten']} ghi hợp đồng {'/'.join(lech[0])}, không phải {kq.get('so_hd')}",
                 "Chứng từ có thể thuộc hợp đồng khác — kiểm tra lại.", tai_lieu=d["ten"])
    # ma trận
    mt = {k: {"khoa": k, "ma_hm": h.get("ma_hm"), "ten": h["ten"], "dvt": h["dvt"], "kl_kn": h.get("kl_kn"),
              "kl_lk": h.get("kl_lk"), "don_gia": h.get("don_gia"), "nt": None, "nt_docs": [], "gn": 0.0, "gn_docs": [],
              "co": [], "cq": [], "pl": [], "ld": []} for k, h in hm.items()}
    for d in docs:
        for ln in d["dong"]:
            r = mt.get(ln["khoa"])
            if not r:
                continue
            if d["loai"] == "BB_NT":
                r["nt"] = (r["nt"] or 0) + (ln.get("so_luong") or 0)
                r["nt_docs"].append(d["ten"])
            elif d["loai"] == "BB_GN":
                r["gn"] += ln.get("so_luong") or 0
                r["gn_docs"].append(d["ten"])
            elif d["loai"] in ("CO", "CQ", "PL", "BB_LD"):
                lst = r[{"CO": "co", "CQ": "cq", "PL": "pl", "BB_LD": "ld"}[d["loai"]]]
                if d["ten"] not in lst:
                    lst.append(d["ten"])
    nt_docs = [d for d in docs if d["loai"] == "BB_NT"]
    gn_docs = [d for d in docs if d["loai"] == "BB_GN"]
    # CO / CQ / packing list / BB lắp đặt thường ghi tên khác (tiếng Anh): gắn vào hạng mục qua dòng BB giao nhận cùng hàng
    for d in gn_docs:
        for ln in d["dong"]:
            r = mt.get(ln["khoa"])
            if not r:
                continue
            for d2 in docs:
                if d2["loai"] in ("CO", "CQ", "PL", "BB_LD") and any(_cung_hang(ln, l2) for l2 in d2["dong"]):
                    lst = r[{"CO": "co", "CQ": "cq", "PL": "pl", "BB_LD": "ld"}[d2["loai"]]]
                    if d2["ten"] not in lst:
                        lst.append(d2["ten"])
    # C01 / C02: BB nghiệm thu KL ↔ KL kỳ này của hồ sơ
    if nt_docs:
        for r in mt.values():
            kn = r["kl_kn"] or 0
            if kn <= 1e-9:
                continue
            if r["nt"] is None:
                them("C01", "Cao", f"{r['ten'][:70]}: KL kỳ này {kn:g} {r['dvt']} không có trong BB nghiệm thu",
                     "Hạng mục có KL kỳ này trong hồ sơ thanh toán nhưng không có trong BB nghiệm thu khối lượng đã nạp.",
                     item=r["ma_hm"] or r["ten"][:60],
                     amount=round(kn * (r["don_gia"] or 0) * (1 + vat)) if r["don_gia"] else None)
            elif kn - r["nt"] > max(1e-3, abs(r["nt"]) * 1e-6):
                them("C01", "Cao", f"{r['ten'][:70]}: KL kỳ này {kn:g} > KL nghiệm thu {r['nt']:g} {r['dvt']}",
                     f"Theo {', '.join(r['nt_docs'])}.", item=r["ma_hm"] or r["ten"][:60],
                     amount=round((kn - r["nt"]) * (r["don_gia"] or 0) * (1 + vat)) if r["don_gia"] else None)
            elif r["nt"] - kn > max(1e-3, abs(kn) * 1e-6):
                them("C01", "Thấp", f"{r['ten'][:70]}: KL kỳ này {kn:g} < KL nghiệm thu {r['nt']:g} {r['dvt']}",
                     "Hồ sơ đề nghị ít hơn khối lượng đã nghiệm thu (có thể chuyển sang đợt sau).",
                     item=r["ma_hm"] or r["ten"][:60])
        for d in nt_docs:
            if ngay_nt and d.get("ngay") and d["ngay"] != ngay_nt:
                them("C02", "Trung bình", f"{d['ten']}: ngày nghiệm thu {_vn(d['ngay'])} ≠ ngày nghiệm thu của đợt {_vn(ngay_nt)}",
                     "Mốc áp phụ lục / BOQ hiệu lực tính theo ngày nghiệm thu của đợt — kiểm tra lại ngày đã nhập.",
                     tai_lieu=d["ten"])
            for ln in d["dong"]:
                if not ln["khoa"]:
                    them("C04", "Trung bình", f"{d['ten']}: '{ln['ten'][:60]}' không ghép được hạng mục nào của hồ sơ",
                         f"{ln['vi_tri']}. Kiểm tra tên hạng mục (chữ OCR có thể sai).", tai_lieu=d["ten"])
    # C03 / C04: vật tư thiết bị đã giao ↔ KL lũy kế
    for r in mt.values():
        if r["gn_docs"] and r["kl_lk"] is not None and r["kl_lk"] - r["gn"] > max(1e-3, abs(r["gn"]) * 1e-6):
            thieu = r["kl_lk"] - r["gn"]
            them("C03", "Cao", f"{r['ten'][:70]}: giao {r['gn']:g} < KL lũy kế đề nghị {r['kl_lk']:g} {r['dvt']}",
                 f"Theo {', '.join(sorted(set(r['gn_docs'])))}. Thiếu {thieu:g} {r['dvt']} chưa có BB giao nhận.",
                 item=r["ma_hm"] or r["ten"][:60],
                 amount=round(thieu * (r["don_gia"] or 0) * (1 + vat)) if r["don_gia"] else None)
    for d in gn_docs:
        for ln in d["dong"]:
            if hm and not ln["khoa"]:
                them("C04", "Thấp", f"{d['ten']}: '{ln['ten'][:60]}' không ghép được hạng mục nào",
                     f"{ln['vi_tri']}. Hàng giao không thuộc hạng mục trong hồ sơ, hoặc tên khác.", tai_lieu=d["ten"])
    # C05 / C06 / C07: đối chiếu chéo các chứng từ của từng dòng hàng đã giao
    co_loai = {t: [d for d in docs if d["loai"] == t] for t in ("CO", "CQ", "PL", "BB_LD")}
    for d in gn_docs:
        for ln in d["dong"]:
            ten = ln.get("model") or ln["ten"]
            for t, ds in co_loai.items():
                cap = [(d2, l2) for d2 in ds for l2 in d2["dong"] if _cung_hang(ln, l2)]
                if not cap:
                    if ds or t in ("CO", "CQ"):
                        them("C05", "Trung bình" if t in ("CO", "CQ") else "Thấp",
                             f"Thiếu {LOAI[t].split(' —')[0]} cho '{ten[:60]}' ({d['ten']})",
                             f"Dòng hàng đã giao ({ln['vi_tri']}) chưa có {LOAI[t]} tương ứng trong bộ chứng từ.",
                             tai_lieu=d["ten"], item=hm.get(ln["khoa"], {}).get("ma_hm") or "")
                    continue
                tong_sl = sum(l2.get("so_luong") or 0 for _, l2 in cap)
                sl = ln.get("so_luong") or 0
                if t in ("CO", "CQ", "PL") and sl and tong_sl and tong_sl + 1e-9 < sl:
                    them("C06", "Trung bình", f"'{ten[:60]}': số lượng trên {t} {tong_sl:g} < số lượng giao {sl:g}",
                         f"{d['ten']} ↔ {', '.join(sorted({d2['ten'] for d2, _ in cap}))}.", tai_lieu=d["ten"])
                if t == "PL" and sl and tong_sl and abs(tong_sl - sl) > 1e-9 and tong_sl > sl:
                    them("C06", "Thấp", f"'{ten[:60]}': packing list {tong_sl:g} ≠ giao {sl:g}",
                         f"{d['ten']} ↔ {', '.join(sorted({d2['ten'] for d2, _ in cap}))}.", tai_lieu=d["ten"])
                lo = _lo(ln.get("lo"))
                if lo and t in ("CO", "CQ"):
                    lo2 = set().union(*[_lo(l2.get("lo")) for _, l2 in cap])
                    if lo2 and not (lo & lo2):
                        them("C06", "Cao", f"'{ten[:60]}': số lô / serial trên BB giao nhận không có trên {t}",
                             f"BB giao nhận: {ln.get('lo')}; {t}: {', '.join(sorted(lo2))[:120]}.", tai_lieu=d["ten"])
                for d2, _ in cap:
                    if not (d.get("ngay") and d2.get("ngay")):
                        continue
                    if t in ("CO", "CQ") and d2["ngay"] > d["ngay"]:
                        them("C07", "Trung bình", f"{d2['ten']} ({t}) ngày {_vn(d2['ngay'])} sau ngày giao {_vn(d['ngay'])}",
                             f"'{ten[:60]}': chứng nhận cấp sau khi hàng đã giao — kiểm tra tính hợp lệ.", tai_lieu=d2["ten"])
                    if t == "BB_LD" and d2["ngay"] < d["ngay"]:
                        them("C07", "Trung bình", f"BB lắp đặt / chạy thử {d2['ten']} ngày {_vn(d2['ngay'])} trước ngày giao "
                             f"{_vn(d['ngay'])}", f"'{ten[:60]}'.", tai_lieu=d2["ten"])
    for d in docs:
        if not d.get("ngay"):
            continue
        if ngay_nt and d["loai"] in ("BB_GN", "BB_LD") and d["ngay"] > ngay_nt:
            them("C07", "Cao", f"{d['ten']} ngày {_vn(d['ngay'])} sau ngày nghiệm thu của đợt {_vn(ngay_nt)}",
                 "Hàng giao / lắp đặt sau ngày nghiệm thu thì chưa đủ căn cứ thanh toán ở đợt này.", tai_lieu=d["ten"])
        if ngay_ky and d["loai"] in ("BB_NT", "BB_GN", "BB_LD") and d["ngay"] < ngay_ky:
            them("C07", "Trung bình", f"{d['ten']} ngày {_vn(d['ngay'])} trước ngày ký hợp đồng {_vn(ngay_ky)}",
                 "Kiểm tra chứng từ có thuộc hợp đồng này không.", tai_lieu=d["ten"])
    thu_tu = {"Cao": 0, "Trung bình": 1, "Thấp": 2}
    ph.sort(key=lambda f: (thu_tu.get(f["level"], 3), f["code"]))
    dem = {}
    for f in ph:
        dem[f["code"]] = dem.get(f["code"], 0) + 1
        f["id"] = f"{f['code']}-{dem[f['code']]:02d}"
    kq["ma_tran"] = [r for r in mt.values() if (r["kl_kn"] or 0) > 0 or r["nt_docs"] or r["gn_docs"] or r["co"] or r["cq"]
                     or r["pl"] or r["ld"]]
    kq["phat_hien"] = ph
    kq["dem"] = {m: sum(1 for f in ph if f["level"] == m) for m in ("Cao", "Trung bình", "Thấp")}
    return kq


def _vn(iso):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else str(iso or "—")


# ================================================================== tạo bộ chứng từ
def hang_muc_tu_dot(ma_kq):
    """Hạng mục của hồ sơ thanh toán (từ kết quả Kiểm tra đợt) → (thông tin, [hạng mục])."""
    import openpyxl
    from . import nghiep_vu as nv
    d = nv.doc_ket_qua_kiem_tra("kiem_tra_dot", ma_kq)
    cs, con = nv._cs()
    try:
        hd = cs.tim_hd(con, d["hop_dong"]["ma_hd"])
        p = d.get("duong_dan_tep")
        if not p or not os.path.exists(p):
            raise ValueError("Không còn file hồ sơ thanh toán của lần kiểm tra này — kiểm tra lại đợt.")
        k = cs.tinh_doi_chieu_dot(con, hd["ma_hd"], p, d["ngay_nghiem_thu"], d.get("dot"),
                                  wv=openpyxl.load_workbook(p, data_only=True))
        hm = []
        for i, x in enumerate(k["rows"], 1):
            it, m = x["it"], x["m"] or {}
            hm.append({"khoa": m.get("ma_hm") or f"D{it['dong']}", "ma_hm": m.get("ma_hm") or "", "ten": it["ten"],
                       "dvt": it["dvt"], "stt": str(it.get("stt") or ""), "kl_kn": it.get("kl_kn"), "kl_lk": it.get("kl_lk"),
                       "kl_hd": it.get("kl_hd"), "don_gia": m.get("don_gia") or it.get("don_gia"), "dong": it["dong"]})
        info = {"ma_kq": ma_kq, "ma_hd": hd["ma_hd"], "so_hd": hd["so_hd"], "ngay_nt": k["ngay"], "dot": k.get("dot"),
                "vat": k["vat"], "ngay_ky_hd": hd["ngay_ky"], "tep_hstt": d.get("tep")}
        return info, hm
    finally:
        con.close()


def hang_muc_tu_boq(ma_hd, ngay_nt):
    from . import nghiep_vu as nv
    cs, con = nv._cs()
    try:
        hd = cs.tim_hd(con, ma_hd)
        ngay = cs.ngay_iso(ngay_nt)
        hl, _ = cs.boq_hieu_luc(con, hd["ma_hd"], pls=cs.phu_luc_ap_dung(con, hd["ma_hd"], ngay))
        hm = [{"khoa": ma, "ma_hm": ma, "ten": v["ten"], "dvt": v["dvt"], "stt": str(v.get("stt") or ""), "kl_kn": None,
               "kl_lk": None, "kl_hd": v["kl"], "don_gia": v["don_gia"], "dong": None} for ma, v in hl.items()]
        info = {"ma_kq": None, "ma_hd": hd["ma_hd"], "so_hd": hd["so_hd"], "ngay_nt": ngay, "dot": None,
                "vat": hd["vat"] or 0, "ngay_ky_hd": hd["ngay_ky"], "tep_hstt": None}
        return info, hm
    finally:
        con.close()


def doc_mot_tai_lieu(path, ai=None, tien_do=None, dung=None, ghi_log=None):
    ten = os.path.basename(path)
    doc = doc_file(path, tien_do=tien_do, dung=dung, ghi_log=ghi_log)
    loai, ly_do = phan_loai(doc["dong"], ten)
    ngay, ngay_c = tim_ngay(doc["dong"])
    so, so_c = tim_so(doc["dong"])
    dong = dong_hang(doc["bang"], loai)
    canh, loi_ai = list(doc["canh_bao"]), ""
    if not dong and loai != "KHAC" and ai is not None and doc["dong"]:
        if tien_do:
            tien_do(f"Local AI đọc dòng hàng {ten}")
        dong, loi_ai = doc_dong_ai(ai, doc["dong"], loai, ghi_log)
        if loi_ai:
            canh.append(loi_ai)
    elif not dong and loai != "KHAC" and ai is None:
        canh.append("Không có bảng dòng hàng và chưa có Local AI để đọc.")
    return {"id": hashlib.sha1(Path(path).read_bytes()).hexdigest()[:12], "ten": ten, "loai": loai,
            "loai_ten": LOAI[loai], "ly_do_loai": ly_do, "so": so, "so_trich": so_c, "ngay": ngay, "ngay_trich": ngay_c,
            "hd_ref": so_hop_dong(doc["dong"]), "ocr": (doc["ocr"] or {}).get("trang") if doc["ocr"] else None,
            "dong": dong, "canh_bao": canh, "van_ban": doc["dong"][:400], "bo": False}


def tao_bo(body, files, ai=None, tien_do=None, dung=None, ghi_log=None):
    """body: {ma_kq} (kết quả Kiểm tra đợt) hoặc {ma_hd, ngay_nt}; them_vao: id bộ đã có. files: đường dẫn."""
    def td(p, m):
        if tien_do:
            tien_do(p, m)
    if body.get("them_vao"):
        kq = doc(body["them_vao"])
    else:
        if body.get("ma_kq"):
            info, hm = hang_muc_tu_dot(body["ma_kq"])
        elif body.get("ma_hd") and body.get("ngay_nt"):
            info, hm = hang_muc_tu_boq(body["ma_hd"], body["ngay_nt"])
        else:
            raise ValueError("Chọn một lần Kiểm tra đợt, hoặc hợp đồng + ngày nghiệm thu")
        kq = {"id": time.strftime("%Y%m%d%H%M%S") + "_" + hashlib.sha1(os.urandom(8)).hexdigest()[:8],
              "tao_luc": time.time(), **info, "hang_muc": hm, "tai_lieu": [], "loi": []}
    if ai is not None and kq.get("ma_hd") and hasattr(ai, "dat_dinh_danh"):   # Claude: che tên các bên / số HĐ
        import csdl_hop_dong as cs
        from trich_xuat.ai_cloud import dat_che_theo_hd
        con = cs.mo_csdl(str(ch.file_csdl()))
        try:
            dat_che_theo_hd(ai, con, kq["ma_hd"])
        finally:
            con.close()
    co = {d["id"] for d in kq["tai_lieu"]}
    for i, p in enumerate(files):
        if dung is not None and dung.is_set():
            break
        td(i / max(1, len(files)), f"Đọc {os.path.basename(p)} ({i + 1}/{len(files)})")
        try:
            d = doc_mot_tai_lieu(p, ai=ai, tien_do=lambda m: td((i + 0.5) / max(1, len(files)), m), dung=dung,
                                 ghi_log=ghi_log)
        except Exception as e:  # noqa: BLE001
            from trich_xuat.ai_local import DaDung
            if isinstance(e, DaDung):
                raise
            kq["loi"].append({"ten": os.path.basename(p), "loi": getattr(e, "thong_diep", None) or f"{type(e).__name__}: {e}"})
            continue
        if d["id"] in co:
            continue
        co.add(d["id"])
        kq["tai_lieu"].append(d)
    doi_chieu(kq)
    luu(kq)
    td(1.0, f"Xong: {len(kq['tai_lieu'])} chứng từ, {len(kq['phat_hien'])} phát hiện")
    return kq


# ================================================================== lưu / đọc / sửa
def _duong_dan(id_):
    if not re.fullmatch(r"\d{14}_[0-9a-f]{8}", str(id_ or "")):
        raise KeyError("Mã bộ chứng từ không hợp lệ")
    return thu_muc_kq() / f"{id_}.json"


def luu(kq):
    p = _duong_dan(kq["id"])
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(kq, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    os.replace(tmp, p)


def doc(id_):
    p = _duong_dan(id_)
    if not p.exists():
        raise KeyError("Không có bộ chứng từ này")
    return json.loads(p.read_text(encoding="utf-8"))


def danh_sach():
    out = []
    for p in sorted(thu_muc_kq().glob("*.json"), reverse=True):
        try:
            k = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.append({"id": k["id"], "so_hd": k.get("so_hd"), "ma_hd": k.get("ma_hd"), "ngay_nt": k.get("ngay_nt"),
                    "dot": k.get("dot"), "tep_hstt": k.get("tep_hstt"), "tao_luc": k.get("tao_luc"),
                    "so_tai_lieu": len(k.get("tai_lieu") or []), "dem": k.get("dem") or {}})
    return out


def cap_nhat(id_, body):
    """{tai_lieu: [{id, loai?, bo?, so?, ngay?}]} → đối chiếu lại."""
    kq = doc(id_)
    by = {d["id"]: d for d in kq["tai_lieu"]}
    for s in body.get("tai_lieu") or []:
        d = by.get(s.get("id"))
        if not d:
            continue
        if s.get("loai") in LOAI:
            d["loai"], d["loai_ten"], d["ly_do_loai"] = s["loai"], LOAI[s["loai"]], "Anh chọn"
        if "bo" in s:
            d["bo"] = bool(s["bo"])
        if "so" in s:
            d["so"] = str(s["so"] or "").strip()
        if "ngay" in s:
            import csdl_hop_dong as cs
            try:
                d["ngay"] = cs.ngay_iso(s["ngay"]) if s["ngay"] else None
            except ValueError:
                raise ValueError(f"Ngày không hợp lệ: {s['ngay']}") from None
    doi_chieu(kq)
    luu(kq)
    return kq


def xoa(id_):
    p = _duong_dan(id_)
    if p.exists():
        p.unlink()
