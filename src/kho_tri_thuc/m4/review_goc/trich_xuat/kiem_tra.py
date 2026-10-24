# -*- coding: utf-8 -*-
"""
kiem_tra.py — Python tự kiểm kết quả AI (bước 5) và so đáp án.
  - Trích dẫn phải có NGUYÊN VĂN trong HĐ (khớp gần đúng nếu chỉ khác dấu câu/khoảng trắng).
  - Mọi số trong giá trị phải nằm trong trích dẫn (trừ giá trị "Suy ra").
  - Điều/Khoản do PYTHON suy lại từ trích dẫn (không tin nhãn AI ghi).
  - Giá trị ≥ 8 ký tự có chữ và có nguyên văn trong HĐ → "OK (giá trị có nguyên văn trong HĐ)".
"""
import glob
import os
import re
import unicodedata
from decimal import Decimal, InvalidOperation

from .cau_truc import bo_dau, vi_tri

KHONG_CO = ("không quy định", "không tìm thấy")


def norm(s):
    """Chuẩn hoá để so nguyên văn: Unicode NFC (chữ tổ hợp = chữ dựng sẵn), ngoặc kép thẳng, gộp khoảng trắng, chữ thường."""
    s = unicodedata.normalize("NFC", s or "")
    return re.sub(r"\s+", " ", s.replace("“", '"').replace("”", '"').replace("’", "'")).strip().lower()


def loose(s):
    """Bỏ mọi dấu câu/khoảng trắng (giữ chữ có dấu và số) — để so trích dẫn gần đúng."""
    return re.sub(r"[\W_]+", "", norm(s))


def so_chuan(tok):
    """7.915.563.292 = 7,915,563,292 → '7915563292'; 0,15 = 0.15 → '0.15'."""
    t = tok.strip(".,")
    seps = [c for c in t if c in ".,"]
    if len(set(seps)) == 2:
        dec = t[max(t.rfind("."), t.rfind(","))]
        t = t.replace("," if dec == "." else ".", "").replace(dec, ".")
    elif len(seps) > 1:
        t = t.replace(seps[0], "")
    elif len(seps) == 1:
        a, b = re.split(r"[.,]", t)
        t = a + b if (len(b) == 3 and 1 <= len(a) <= 3 and not a.startswith("0")) else a + "." + b
    try:
        return format(Decimal(t).normalize(), "f")
    except InvalidOperation:
        return tok


def cac_so(s):
    return {so_chuan(n) for n in re.findall(r"\d[\d\.,]*\d|\d", s or "")}


def la_khong_co(v):
    return (v or "").strip().lower().startswith(KHONG_CO)


def la_khong_ap_dung(v):
    return (v or "").strip().lower().startswith(("không áp dụng", "khong ap dung"))


def khop_dieu_khoan(dk, sent_rows):
    """dieu_khoan có trỏ tới ít nhất một đoạn đã gửi không."""
    if not sent_rows:
        return True
    for part in re.split(r"[;,]|\bvà\b", (dk or "").lower()):
        part = part.strip()
        if not part:
            continue
        khoans = re.findall(r"\d+(?:\.\d+)+", part)
        dieus = [int(x) for x in re.findall(r"điều\s*(\d+)", part)]
        doans = [int(x) for x in re.findall(r"đoạn\s*(\d+)", part)]
        for r in sent_rows:
            if r.get("doan"):
                if r["doan"] in doans or (r["doan"] == 1 and not (khoans or dieus or doans)):
                    return True
                continue
            d, k = int(r["dieu"]), r["khoan"]
            if khoans:
                if any(int(x.split(".")[0]) == d and (not k or x == k or x.startswith(k + ".") or k.startswith(x + "."))
                       for x in khoans):
                    return True
            elif dieus:
                if d in dieus:
                    return True
            elif d == 0:
                return True
    return False


def gia_tri_nguyen_van(v, full_norm):
    """Giá trị ≥ 8 ký tự, có chữ cái, có nguyên văn trong HĐ (không tính 'Không quy định/áp dụng')."""
    n = norm(v)
    return (len(n) >= 8 and re.search(r"[^\W\d_]", n) is not None and not la_khong_co(v) and not la_khong_ap_dung(v)
            and n in full_norm)


def check(item, full_norm, full_loose=None, sent_rows=None):
    """Tự kiểm 1 kết quả → chuỗi bắt đầu bằng 'OK' (xanh) hoặc 'KIỂM TRA: …' / 'THIẾU …' (vàng)."""
    q = item.get("trich_dan", "") or ""
    v = item.get("gia_tri", "") or ""
    if not v:
        return "THIẾU giá trị"
    if la_khong_co(v):
        return "KIỂM TRA: AI báo HĐ không quy định"
    if full_loose is None:
        full_loose = loose(full_norm)
    parts = [p for p in re.split(r"\.\.\.|…", q) if p.strip()]
    if parts and all(norm(p) in full_norm for p in parts):
        khop = "OK"
    elif parts and all(loose(p) and loose(p) in full_loose for p in parts):
        khop = "OK (khớp gần đúng)"
    else:
        khop = None
    suy_ra = "suy ra" in (item.get("ghi_chu") or "").lower()
    if not q:
        kq = "KIỂM TRA: giá trị suy ra" if suy_ra else "KIỂM TRA: thiếu trích dẫn"
    elif not khop:
        kq = "KIỂM TRA: trích dẫn không khớp nguyên văn"
    elif not suy_ra and not cac_so(v) <= cac_so(q):
        kq = "KIỂM TRA: số liệu không có trong trích dẫn"
    elif not khop_dieu_khoan(item.get("dieu_khoan", ""), sent_rows):
        kq = "KIỂM TRA: điều khoản không thuộc các đoạn đã gửi"
    else:
        return khop
    if gia_tri_nguyen_van(v, full_norm):
        return "OK (giá trị có nguyên văn trong HĐ)"
    return kq


def la_ok(ck):
    return str(ck or "").startswith("OK")


def gan_dieu_khoan(it, rows):
    """Python tự xác định Điều/Khoản từ TRÍCH DẪN: đoạn đã gửi chứa câu trích → nhãn chuẩn của đoạn đó."""
    if not it or not rows:
        return it
    parts = [x for x in re.split(r"\.\.\.|…", it.get("trich_dan") or "") if x.strip()]
    if not parts:
        return it
    qn, ql = norm(parts[0]), loose(parts[0])
    for r in rows:
        txt = "\n".join(x for x in (r.get("tieu_de_dieu", ""), r["tieu_de_khoan"], r["noi_dung"]) if x)
        if (qn and qn in norm(txt)) or (len(ql) >= 8 and ql in loose(txt)):
            it["dieu_khoan"], it["_row"] = vi_tri(r), r["id"]
            return it
    return it


# ------------------------------------------------------------------ so đáp án (kiểm thử chất lượng)
def _gon(s):
    return re.sub(r"[^a-z0-9]", "", bo_dau(s or "").lower())


def tim_dap_an(name, thu_muc):
    """DAP_AN_<tên>.tsv; không có thì DAP_AN_<X>.tsv mà X (bỏ dấu/ký tự) nằm trong tên HĐ."""
    if not thu_muc:
        return None
    for p in (os.path.join(thu_muc, f"DAP_AN_{name}.tsv"), os.path.join(thu_muc, f"DAP_AN_{name.replace(' ', '_')}.tsv")):
        if os.path.exists(p):
            return p
    ten = _gon(name)
    ung = []
    for p in glob.glob(os.path.join(thu_muc, "DAP_AN_*.tsv")):
        x = _gon(os.path.basename(p)[7:-4])
        if len(x) >= 4 and x in ten:
            ung.append((len(x), p))
    return max(ung)[1] if ung else None


def load_key(path):
    if not path:
        return None
    key = {}
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh.read().splitlines():
            c = line.rstrip("\r\n").split("\t")
            if len(c) >= 4 and re.match(r"^(TC|TT)-\d+$", c[0]):
                key[c[0]] = c[3]
    return key


def _ngay(s):
    def f(m):
        return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"
    s = re.sub(r"(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", f, s)
    return re.sub(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", f, s)


def compare(gold, got):
    g, a = _ngay(norm(gold)).replace("kí", "ký"), _ngay(norm(got)).replace("kí", "ký")

    def strip(s):
        return re.sub(r"[\s\.\,%;:\"'()\-–]", "", s)
    if strip(g) == strip(a) or (strip(g) and strip(g) in strip(a)) or (strip(a) and strip(a) in strip(g)):
        return "ĐÚNG"
    return "SAI / cần xem"


def giong_nhau(a, b):
    return compare(a, b) == "ĐÚNG" or compare(b, a) == "ĐÚNG"
