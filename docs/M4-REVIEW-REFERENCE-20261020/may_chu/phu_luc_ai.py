# -*- coding: utf-8 -*-
"""
phu_luc_ai.py — Trích nội dung thay đổi từ FILE PHỤ LỤC (Word / PDF; PDF scan → OCR ABBYY trên máy) rồi kiểm tra
bằng đúng 18 kiểm tra P01–P18 của phiếu phụ lục, chờ anh duyệt trước khi nạp CSDL.

Ai làm gì:
- QUY TẮC (không AI): nhận hợp đồng (số HĐ "NNNN/YYYY" trong văn bản / tên file), số PL, ngày ký ("Hôm nay, ngày …"),
  ngày hiệu lực, bảng khối lượng / đơn giá (cũ → mới, Tổng cộng, VAT, Tổng sau VAT), phân loại THAY / THEM / BO so với
  BOQ hiện hành (khớp tên gần đúng vì chữ OCR có thể sai), khoảng thời gian áp đơn giá.
- LOCAL AI: tham số hợp đồng bị sửa (mã, giá trị mới, trích dẫn nguyên văn) và nội dung thay đổi không thuộc tham số
  (vd tài khoản ngân hàng). Giá trị CŨ lấy từ CSDL, không do AI điền. Trích dẫn không khớp nguyên văn → ô vàng.
Kết quả lưu <dữ liệu>\\phu_luc_ai\\<mã>.json; nạp CSDL qua csdl_hop_dong.kiem_tra_phu_luc + ghi_phu_luc.
"""
import copy
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

CHE_DO_BOQ = {"khong": "Không đổi BOQ (chỉ ghi nhận)", "thay_doi": "Chỉ hạng mục thay đổi",
              "toan_bo": "Toàn bộ BOQ sau phụ lục"}
TRANG_THAI_TS = ("Chưa xác nhận", "Đã xác nhận", "Đã sửa tay")
KHOP_TOI_THIEU = 0.80
BO_QUA_TS = {"TT-02", "TC-01"}          # TT-02 tự tính từ giá trị tăng/giảm; TC-01 số HĐ không đổi qua phụ lục

SCHEMA_PL = {"type": "object", "properties": {
    "thay_doi": {"type": "array", "items": {"type": "object", "properties": {
        k: {"type": "string"} for k in ("ma", "gia_tri_moi", "dieu", "trich_dan", "ghi_chu")},
        "required": ["ma", "gia_tri_moi", "dieu", "trich_dan", "ghi_chu"]}},
    "khac": {"type": "array", "items": {"type": "object", "properties": {
        k: {"type": "string"} for k in ("noi_dung", "dieu", "trich_dan")}, "required": ["noi_dung", "dieu", "trich_dan"]}}},
    "required": ["thay_doi", "khac"]}


def _cs():
    import csdl_hop_dong as cs
    return cs, cs.mo_csdl(str(ch.file_csdl()))


def _bd(s):
    from master_hd import bo_dau
    return bo_dau(s)


def _gon(s):
    """Chuẩn hoá để so nguyên văn: không dấu, bỏ mọi ký tự không phải chữ/số."""
    return re.sub(r"[^0-9a-z]+", "", _bd(s))


def thu_muc_kq():
    p = ch.thu_muc_du_lieu() / "phu_luc_ai"
    p.mkdir(parents=True, exist_ok=True)
    return p


# ================================================================== đọc file
def doc_file(path, tien_do=None, dung=None, ghi_log=None):
    """→ dict(text, dong[], bang[], ocr, docx). PDF scan → OCR; .doc → chuyển .docx."""
    from trich_xuat.doc_hop_dong import chuyen_docx, read_contract
    tb = (lambda m: tien_do(m)) if tien_do else None
    duoi = os.path.splitext(path)[1].lower()
    info_ocr, docx, tam = None, None, None
    if duoi == ".pdf":
        p2, info_ocr = ocr.chuan_bi_pdf(path, tien_do=tb, dung=dung, ghi_log=ghi_log)
        if info_ocr:
            docx = p2
    elif duoi == ".docx":
        docx = path
    elif duoi == ".doc":
        docx, _, _ = chuyen_docx(path)
        tam = os.path.dirname(docx)
    else:
        raise ValueError("Chỉ nhận phụ lục .docx / .doc / .pdf")
    try:
        info = read_contract(docx or path)
        bang = ocr.docx_bang(docx)[1] if docx else []
    finally:
        if tam:
            shutil.rmtree(tam, ignore_errors=True)
    text = info["text"]
    dong = [ln for ln in text.split("\n") if ln.strip()]
    canh = []
    if duoi == ".pdf" and not docx:
        canh.append("PDF có lớp chữ: bảng đọc theo lớp chữ không tách được cột — nên dùng bản Word hoặc bật Luôn OCR.")
    if info["report"].get("images"):
        canh.append(f"File có {info['report']['images']} ảnh (chữ ký, con dấu…) và {len(bang)} bảng đọc được"
                    + (" — nội dung trong ảnh không đọc được; nếu phụ lục có bảng dạng ảnh thì đối chiếu bản scan."
                       if not bang else "."))
    return {"text": text, "dong": dong, "bang": bang, "ocr": info_ocr, "canh_bao": canh}


# ================================================================== nhận hợp đồng & thông tin chung
def _so_nam(so_hd):
    m = re.match(r"\s*0*(\d+)\s*/\s*(\d{4})", str(so_hd or ""))
    return (m.group(1), m.group(2)) if m else None


def nhan_hop_dong(text, ten_file, ds_hd):
    """ds_hd: [(ma_hd, so_hd)]. Trả (ma_hd, so_hd, nguồn) nếu đúng 1 hợp đồng khớp, không thì (None, None, '')."""
    for nguon, chu in (("văn bản phụ lục", text[:6000]), ("tên file", ten_file)):
        dem = {}
        for ma, so in ds_hd:
            sn = _so_nam(so)
            if not sn:
                continue
            n = len(re.findall(rf"(?<!\d)0*{sn[0]}\s*[/.\-_]\s*{sn[1]}(?!\d)", chu))
            if n:
                dem[ma] = (n, so)
        if len(dem) == 1:
            ma, (n, so) = next(iter(dem.items()))
            return ma, so, nguon
        if len(dem) > 1:
            best = sorted(dem.items(), key=lambda x: -x[1][0])
            if best[0][1][0] > best[1][1][0]:
                return best[0][0], best[0][1][1], nguon
    return None, None, ""


def _ngay(d, m, y):
    try:
        import datetime
        return datetime.date(int(y), int(m), int(d)).strftime("%d/%m/%Y")
    except ValueError:
        return None


def thong_tin_chung(dong, ten_file):
    """→ (info{so_pl, ngay_ky, ngay_hieu_luc, trang_thai, noi_dung, can_cu}, trich{khoá: câu nguyên văn}, nguon{khoá: …})."""
    info, trich, nguon = {"trang_thai": "Đã ký"}, {}, {}
    for ln in dong[:30]:
        m = re.search(r"\bphu\s*luc(?:\s+hop\s+dong)?(?:\s+so)?\s*[:.]?\s*0*(\d{1,3})\b", _bd(ln))
        if m:
            info["so_pl"] = f"PL{int(m.group(1)):02d}"
            trich["so_pl"], nguon["so_pl"] = ln.strip()[:200], "văn bản"
            break
    if "so_pl" not in info:
        m = re.search(r"PL\s*0*(\d{1,3})", ten_file, re.I)
        if m:
            info["so_pl"], nguon["so_pl"] = f"PL{int(m.group(1)):02d}", "tên file"
    for ln in dong[:60]:
        m = re.search(r"hom\s*nay,?\s*ngay\s*(\d{1,2})\s*thang\s*(\d{1,2})\s*nam\s*(\d{4})", _bd(ln))
        if m and _ngay(*m.groups()):
            info["ngay_ky"] = _ngay(*m.groups())
            trich["ngay_ky"], nguon["ngay_ky"] = ln.strip()[:200], "văn bản"
            break
    if "ngay_ky" not in info:
        m = re.search(r"(?<!\d)(\d{2})[.\-_](\d{2})[.\-_](\d{4})(?!\d)", ten_file)
        if m and _ngay(*m.groups()):
            info["ngay_ky"], nguon["ngay_ky"] = _ngay(*m.groups()), "tên file"
    for ln in dong:
        b = _bd(ln)
        m = re.search(r"co\s*hieu\s*luc\s*(?:ke\s*)?tu\s*ngay\s*(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})", b)
        if m and _ngay(*m.groups()):
            info["ngay_hieu_luc"], trich["ngay_hieu_luc"], nguon["ngay_hieu_luc"] = _ngay(*m.groups()), ln.strip()[:240], "văn bản"
            break
        if re.search(r"co\s*hieu\s*luc\s*(?:ke\s*)?tu\s*ngay\s*ky", b):
            info["ngay_hieu_luc"] = info.get("ngay_ky")
            trich["ngay_hieu_luc"], nguon["ngay_hieu_luc"] = ln.strip()[:240], "văn bản (kể từ ngày ký)"
            break
    if any(re.search(r"\bdu\s*thao\b", _bd(ln)) for ln in dong[:15]):
        info["trang_thai"], nguon["trang_thai"] = "Dự thảo", "văn bản ghi Dự thảo"
    dieu = []
    for ln in dong:
        m = re.match(r"\s*(dieu\s*\d+)\s*[:.]\s*(.+)", _bd(ln))
        if m and not re.search(r"thi hanh|hieu luc", m.group(2)):
            dieu.append(re.sub(r"\s+", " ", ln.strip()).rstrip(":"))
    if dieu:
        info["noi_dung"] = "; ".join(d[:120] for d in dieu)[:500]
        nguon["noi_dung"] = "tiêu đề các Điều"
    for ln in dong:
        if re.search(r"can\s*cu\s*(dieu|khoan|muc)\s*\d", _bd(ln)):
            info["can_cu"], trich["can_cu"], nguon["can_cu"] = ln.strip()[:300], ln.strip()[:300], "văn bản"
            break
    return info, trich, nguon


def gia_tri_van_ban(dong):
    """Giá trị ghi bằng số trong câu văn: {'gt_hd_sau_pl' | 'gt_sau_vat': (số, câu)}."""
    out = {}
    for ln in dong:
        if " | " in ln:
            continue
        b = _bd(ln)
        if "gia tri" not in b:
            continue
        so = [ocr.so_vn(x) for x in re.findall(r"\d{1,3}(?:\.\d{3}){2,}(?:,\d+)?", ln)]
        so = [x for x in so if x and x >= 1e6]
        if not so:
            continue
        if re.search(r"gia tri hop dong (sau (dieu chinh|phu luc|khi)|la|moi)", b) and "gt_hd_sau_pl" not in out:
            out["gt_hd_sau_pl"] = (so[-1], ln.strip()[:240])
        elif re.search(r"gia tri (hop dong )?(tang|giam|bo sung|phat sinh)|(tang|giam) (gia tri|them)", b) and "gt_sau_vat" not in out:
            out["gt_sau_vat"] = ((-1 if re.search(r"\bgiam\b", b) else 1) * so[-1], ln.strip()[:240])
    return out


def thoi_han_don_gia(dong):
    """Đơn giá áp cho KL thực hiện trong một khoảng ngày → {tu, den, trich} | None."""
    for ln in dong:
        b = _bd(ln)
        m = re.search(r"tu\s*ngay\s*(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})\s*(?:den|toi)\s*(?:het\s*)?ngay\s*(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})", b)
        if m and re.search(r"don\s*gia|khoi\s*luong", b):
            return {"tu": _ngay(*m.groups()[:3]), "den": _ngay(*m.groups()[3:]), "trich": ln.strip()[:300]}
    return None


# ================================================================== bảng khối lượng / đơn giá
_CU = r"\b(cu|truoc|hop dong|hd|ban dau|goc)\b"
_MOI = r"\b(moi|sau|dieu chinh|phu luc|pl)\b"


def _tieu_de(row):
    """Dòng tiêu đề bảng → {trường: chỉ số cột} (stt, ten, dvt, kl, kl_cu, dg, dg_cu, tt, ghi_chu) hoặc None."""
    from master_hd import bo_dau_tieu_de
    cot = {}
    for j, c in enumerate(row):
        t = re.sub(r"\s+", " ", bo_dau_tieu_de(c)).strip()        # chịu lỗi OCR: "Nội duug", "Đơn qia"
        if not t:
            continue
        if re.search(r"don gia|^dg\b", t):
            k = "dg_cu" if re.search(_CU, t) and not re.search(_MOI, t) else "dg"
        elif re.search(r"khoi luong|^kl\b", t):
            k = "kl_cu" if re.search(_CU, t) and not re.search(_MOI, t) else "kl"
        elif re.search(r"thanh tien|gia tri|thanh gia", t):
            k = "tt"
        elif re.search(r"^(stt|tt|so tt)$", t):
            k = "stt"
        elif re.search(r"^(don vi|dvt|d\.? ?vt|dv)\b", t):
            k = "dvt"
        elif re.search(r"ghi chu", t):
            k = "ghi_chu"
        elif re.search(r"noi dung|ten cong viec|ten cong tac|hang muc|cong viec|dien giai", t):
            k = "ten"
        else:
            continue
        cot.setdefault(k, j)
    return cot if "ten" in cot and ("dg" in cot or "kl" in cot) else None


def _la_dong_so_cot(row):
    o = [str(c).strip() for c in row if str(c).strip()]
    return len(o) >= 3 and all(re.fullmatch(r"\(?\d{1,2}\)?([=x*+/\-\d()]*)", x) for x in o)


def doc_bang(bangs):
    """Bảng KL/đơn giá của phụ lục → dict(loai: 'moi' | 'doi_chieu', items[], tong{truoc_vat, vat, ty_le_vat, sau_vat},
    trich_tong, bang: số thứ tự bảng) — chọn bảng có nhiều hạng mục nhất; None nếu không có."""
    best = None
    i = 0
    while i < len(bangs):
        b = bangs[i]
        cot, h = None, 0
        for h in range(min(3, len(b))):
            cot = _tieu_de(b[h])
            if cot:
                break
        if not cot:
            i += 1
            continue
        rows = list(b[h + 1:])
        j = i + 1
        while j < len(bangs) and max(len(r) for r in bangs[j]) == max(len(r) for r in b):  # bảng ngắt trang
            nxt = bangs[j]
            rows += nxt[1:] if _tieu_de(nxt[0]) else nxt
            j += 1
        items, tong, trich_tong, nhom = [], {}, {}, ""
        for r, row in enumerate(rows, h + 2):
            g = lambda k: (row[cot[k]] if k in cot and cot[k] < len(row) else "").strip()  # noqa: E731
            ten = g("ten") or next((c for c in row if re.search(r"[A-Za-zÀ-ỹ]{3}", c or "")), "")
            if not ten or _la_dong_so_cot(row):
                continue
            low = _bd(ten)
            so_dong = [ocr.so_vn(c) for c in row if ocr.so_vn(c) is not None and c != g("stt")]
            if not g("dvt") and re.match(r"^(tong|cong|thue|gia tri sau thue|vat)", low):
                v = ocr.so_vn(g("tt")) if g("tt") else (so_dong[-1] if so_dong else None)
                if re.search(r"thue|vat", low) and not re.search(r"(da |sau |bao gom )", low):
                    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", ten)
                    tong["vat"] = v
                    if m:
                        tong["ty_le_vat"] = float(m.group(1).replace(",", ".")) / 100
                    trich_tong["vat"] = " | ".join(x for x in row if x)
                elif re.search(r"(da |sau |bao gom )\s*(thue|vat)|sau thue", low):
                    tong["sau_vat"], trich_tong["sau_vat"] = v, " | ".join(x for x in row if x)
                else:
                    tong.setdefault("truoc_vat", v)
                    trich_tong.setdefault("truoc_vat", " | ".join(x for x in row if x))
                continue
            if tong:                                  # sau dòng tổng: hết bảng
                continue
            kl, dg = ocr.so_vn(g("kl")), ocr.so_vn(g("dg"))
            if not g("dvt") and kl is None and dg is None:
                nhom = re.sub(r"\s+", " ", ten).strip()
                continue
            items.append({"dong": r, "stt": g("stt"), "nhom": nhom, "ten": re.sub(r"\s+", " ", ten).strip(), "dvt": g("dvt"),
                          "kl": kl, "don_gia": dg, "kl_cu": ocr.so_vn(g("kl_cu")), "dg_cu": ocr.so_vn(g("dg_cu")),
                          "thanh_tien_ghi": ocr.so_vn(g("tt")), "ghi_chu": g("ghi_chu")})
        if items and (best is None or len(items) > len(best["items"])):
            best = {"loai": "doi_chieu" if ("dg_cu" in cot or "kl_cu" in cot) else "moi", "items": items, "tong": tong,
                    "trich_tong": trich_tong, "bang": i + 1, "cot": sorted(cot, key=cot.get)}
        i = j
    return best


# ================================================================== khớp với BOQ hiện hành
def _dvt(s):
    return re.sub(r"[^0-9a-z]", "", _bd(s).replace("³", "3").replace("²", "2"))


def khop_hang_muc(it, hl, da_dung=()):
    """→ (ma_hm, độ khớp 0..1) theo tên (chịu lỗi OCR) + ĐVT + STT; None nếu không chắc."""
    a = _bd(it["ten"])[:160]
    cands = []
    for ma, d in hl.items():
        if ma in da_dung:
            continue
        b = _bd(d["ten"])[:160]
        r = difflib.SequenceMatcher(None, a, b).ratio()
        n = min(len(a), len(b))
        if n >= 25:
            r = max(r, 0.97 * difflib.SequenceMatcher(None, a[:n], b[:n]).ratio())
        if it.get("dvt") and d.get("dvt") and _dvt(it["dvt"]) != _dvt(d["dvt"]):
            r -= 0.15
        if it.get("stt") and d.get("stt") and str(it["stt"]).strip() == str(d["stt"]).strip():
            r += 0.03
        cands.append((r, ma))
    cands.sort(reverse=True)
    if not cands or cands[0][0] < KHOP_TOI_THIEU:
        return None, cands[0][0] if cands else 0.0
    if len(cands) > 1 and cands[1][0] > cands[0][0] - 0.04:
        return None, cands[0][0]
    return cands[0][1], min(1.0, cands[0][0])


def phan_loai_boq(bang, hl, che_do, ten_file):
    """→ (b_rows cho kiem_tra_phu_luc, bảng hiển thị so sánh, ghi chú [(mức, nội dung)])."""
    if not bang or che_do == "khong":
        return [], [], []
    rows, hien, note, dung = [], [], [], set()
    for it in bang["items"]:
        ma, r = khop_hang_muc(it, hl, dung)
        cu = hl.get(ma) if ma else None
        vi_tri = f"{ten_file} bảng {bang['bang']} dòng {it['dong']}"
        h = {**it, "ma_hm": ma or "", "do_khop": round(r, 3), "ten_csdl": cu["ten"] if cu else "",
             "dvt_csdl": cu["dvt"] if cu else "", "kl_csdl": cu["kl"] if cu else None,
             "dg_csdl": cu["don_gia"] if cu else None, "thao_tac": ""}
        if cu:
            dung.add(ma)
            if re.sub(r"\s+", " ", _bd(it["ten"])).strip() != re.sub(r"\s+", " ", _bd(cu["ten"])).strip():
                note.append(("VÀNG", f"{vi_tri}: '{it['ten'][:60]}' khớp gần đúng ({r:.0%}) với {ma} '{cu['ten'][:60]}' — kiểm tra."))
            if it.get("dg_cu") is not None and cu["don_gia"] is not None and abs(it["dg_cu"] - cu["don_gia"]) > 0.5:
                note.append(("VÀNG", f"{vi_tri}: đơn giá cũ ghi trên PL {it['dg_cu']:,.0f} ≠ đơn giá hiện hành {ma} {cu['don_gia']:,.0f}."))
            if it.get("kl_cu") is not None and cu["kl"] is not None and abs(it["kl_cu"] - cu["kl"]) > 1e-6:
                note.append(("VÀNG", f"{vi_tri}: KL cũ ghi trên PL {it['kl_cu']:g} ≠ KL hiện hành {ma} {cu['kl']:g}."))
            kl = it["kl"] if it.get("kl") is not None else None
            dg = it["don_gia"] if it.get("don_gia") is not None else None
            doi = (kl is not None and abs(kl - (cu["kl"] or 0)) > 1e-9) or (dg is not None and abs(dg - (cu["don_gia"] or 0)) > 0.5)
            if doi:
                h["thao_tac"] = "THAY"
                rows.append(dict(thao_tac="THAY", ma_hm=ma, stt=it.get("stt") or cu.get("stt"), nhom=cu.get("nhom") or "",
                                 ten=cu["ten"], dvt=cu["dvt"], kl=kl, don_gia=dg, thanh_tien_ghi=it.get("thanh_tien_ghi"),
                                 vi_tri=vi_tri, ghi_chu=f"Trích từ phụ lục (khớp tên {r:.0%})"))
            else:
                h["thao_tac"] = "Không đổi"
        else:
            h["thao_tac"] = "THEM"
            rows.append(dict(thao_tac="THEM", ma_hm="", stt=it.get("stt"), nhom=it.get("nhom") or "", ten=it["ten"],
                             dvt=it.get("dvt") or "", kl=it.get("kl"), don_gia=it.get("don_gia"),
                             thanh_tien_ghi=it.get("thanh_tien_ghi"), vi_tri=vi_tri,
                             ghi_chu="Trích từ phụ lục: không khớp hạng mục hiện hành"))
            if hl:
                note.append(("VÀNG", f"{vi_tri}: '{it['ten'][:60]}' không khớp hạng mục nào (khớp nhất {r:.0%}) → THÊM mới. "
                                     "Nếu là hạng mục đang có, chữ OCR có thể sai."))
        hien.append(h)
    if che_do == "toan_bo":
        for ma, d in hl.items():
            if ma not in dung:
                rows.append(dict(thao_tac="BO", ma_hm=ma, nhom=d.get("nhom") or "", ten=d["ten"], dvt=d["dvt"], kl=None,
                                 don_gia=None, thanh_tien_ghi=None, vi_tri=f"{ten_file} (không có trong bảng)",
                                 ghi_chu="Không còn trong BOQ sau phụ lục"))
                hien.append({"dong": "", "ten": "", "ma_hm": ma, "ten_csdl": d["ten"], "dvt_csdl": d["dvt"], "kl_csdl": d["kl"],
                             "dg_csdl": d["don_gia"], "thao_tac": "BO", "do_khop": None})
    return rows, hien, note


# ================================================================== Local AI: tham số sửa + thay đổi khác
def _van_ban_ai(dong):
    """Phần nội dung sửa đổi (từ câu 'Sau khi xem xét…' / Điều 1), bỏ dòng bảng và khối chữ ký."""
    bd = [_bd(x) for x in dong]
    i0 = next((i for i, b in enumerate(bd) if re.search(r"sau khi xem xet|thong nhat ky phu luc", b)), None)
    if i0 is None:
        i0 = next((i for i, b in enumerate(bd) if re.match(r"\s*dieu\s*1\b", b)), 0)
    out = [x for x in dong[i0:] if " | " not in x]
    return "\n".join(out)[:12000]


def hoi_ai(ai, dong, ts_hien_hanh, ghi_log=None):
    """ts_hien_hanh: [(mã, tên, giá trị hiện hành)] → (thay_doi[], khac[], lỗi)."""
    from trich_xuat.ai_local import CTX_TRICH
    ds = "\n".join(f"- {m} | {t} | {v if v not in (None, '') else '(chưa có)'}" for m, t, v in ts_hien_hanh)
    prompt = ("PHỤ LỤC HỢP ĐỒNG CẦN PHÂN TÍCH (văn bản OCR / Word, có thể sai chính tả):\n" + _van_ban_ai(dong) +
              "\n\nTHAM SỐ HỢP ĐỒNG HIỆN HÀNH (mã | tên | giá trị hiện hành trước phụ lục):\n" + ds +
              "\n\nYÊU CẦU:\n"
              "1. \"thay_doi\": chỉ các tham số trong danh sách mà phụ lục SỬA hoặc BỔ SUNG. ma = mã tham số; "
              "gia_tri_moi = giá trị sau phụ lục, viết ngắn gọn cùng kiểu với giá trị hiện hành; dieu = Điều của phụ lục; "
              "trich_dan = câu NGUYÊN VĂN trong phụ lục (chép đúng từng chữ, kể cả lỗi chính tả); ghi_chu = giải thích ngắn.\n"
              "2. KHÔNG đưa giá trị hợp đồng (TT-02), KHÔNG đưa thay đổi khối lượng / đơn giá từng hạng mục "
              "(phần mềm tự đọc bảng), KHÔNG đưa điều khoản thi hành của chính phụ lục.\n"
              "3. \"khac\": nội dung thay đổi không thuộc tham số nào (vd tài khoản ngân hàng, người đại diện, địa chỉ).\n"
              "4. Không suy diễn. Không có thay đổi thì trả mảng rỗng.")
    try:
        data, _, _ = ai.chat_json(prompt, SCHEMA_PL, "thay_doi", CTX_TRICH, "phụ lục")
    except Exception as e:  # noqa: BLE001
        from trich_xuat.ai_local import DaDung
        if isinstance(e, DaDung):
            raise
        if ghi_log:
            ghi_log(f"  {getattr(ai, 'ten', 'Local AI')} lỗi: {type(e).__name__}: {str(e)[:150]}")
        return [], [], (f"Không hỏi được {getattr(ai, 'ten', 'Local AI')} ({type(e).__name__}: {str(e)[:120]}) — mục tham số "
                        "để trống, Anh tự thêm nếu có.")
    td = [x for x in data.get("thay_doi") or [] if isinstance(x, dict)]
    kh = [x for x in data.get("khac") or [] if isinstance(x, dict)]
    return td, kh, ""


def _ket_qua_ai(ai, dong, ts_hh, ghi_log=None):
    """Hỏi AI và chuẩn hoá: → (tham_so[], khac[], lỗi). Mã ngoài danh sách bị bỏ; giá trị cũ lấy từ CSDL."""
    td_ai, kh, loi = hoi_ai(ai, dong, ts_hh, ghi_log)
    ten_ts = {m: (t, v) for m, t, v in ts_hh}
    text_gon = _gon("\n".join(dong))
    tham_so, thay = [], set()
    for x in td_ai:
        m = str(x.get("ma") or "").strip().upper()
        if m not in ten_ts or m in thay:
            continue
        thay.add(m)
        tham_so.append({"ma_ts": m, "ten": ten_ts[m][0], "cu": ten_ts[m][1], "moi": str(x.get("gia_tri_moi") or "").strip(),
                        "trich": str(x.get("trich_dan") or "").strip(), "dieu": str(x.get("dieu") or "").strip(),
                        "ghi_chu": str(x.get("ghi_chu") or "").strip(),
                        "kiem_tra_trich": kiem_trich(x.get("trich_dan"), text_gon), "trang_thai": "Chưa xác nhận",
                        "nguon": getattr(ai, "ten", "Local AI"), "lich_su": []})
    khac = [{"noi_dung": str(k.get("noi_dung") or "").strip(), "dieu": str(k.get("dieu") or "").strip(),
             "trich": str(k.get("trich_dan") or "").strip(), "kiem_tra_trich": kiem_trich(k.get("trich_dan"), text_gon)}
            for k in kh if str(k.get("noi_dung") or "").strip()]
    return tham_so, khac, loi


def hoi_lai_ai(id_, ai, ghi_log=None):
    """Hỏi lại Local AI (vd sau khi chọn hợp đồng). Giữ các tham số Anh đã xác nhận / sửa / thêm."""
    kq = doc(id_)
    if kq.get("nap"):
        raise ValueError("Phụ lục đã nạp CSDL — không sửa được bản trích này.")
    if not kq.get("ma_hd"):
        raise ValueError("Chọn hợp đồng trước khi hỏi Local AI.")
    cs, con = _cs()
    try:
        ts_hh = _ts_hien_hanh(cs, con, kq["ma_hd"], _ngay_iso(kq["info"].get("ngay_ky")))
        from trich_xuat.ai_cloud import dat_che_theo_hd
        dat_che_theo_hd(ai, con, kq["ma_hd"])
    finally:
        con.close()
    moi, khac, loi = _ket_qua_ai(ai, kq.get("van_ban") or [], ts_hh, ghi_log)
    giu = [r for r in kq["tham_so"] if r.get("trang_thai") != "Chưa xác nhận" or r.get("nguon") == "Anh thêm"]
    co = {r["ma_ts"] for r in giu}
    kq["tham_so"] = giu + [r for r in moi if r["ma_ts"] not in co]
    kq["khac"], kq["loi_ai"], kq["model"] = khac, loi, getattr(ai, "model", None)
    kiem_tra(kq)
    luu(kq)
    return kq


def kiem_trich(trich, text_gon):
    g = _gon(trich)
    if len(g) < 8:
        return "Chưa có trích dẫn nguyên văn"
    if g in text_gon:
        return ""
    # cho phép AI bỏ/đổi vài chữ đầu cuối: tìm đoạn dài nhất trùng
    sm = difflib.SequenceMatcher(None, g, text_gon, autojunk=False)
    m = sm.find_longest_match(0, len(g), 0, len(text_gon))
    return "" if m.size >= 0.9 * len(g) else "Trích dẫn không khớp nguyên văn phụ lục"


# ================================================================== tổng hợp, kiểm tra
def _ts_hien_hanh(cs, con, ma_hd, ngay_iso):
    out = []
    for _, ds in cs.DS_THAM_SO:
        for m, t in ds:
            if m in BO_QUA_TS:
                continue
            v, _ = cs.tham_so_hieu_luc(con, ma_hd, m, ngay_iso)
            out.append((m, t, v))
    return out


def _ngay_iso(v):
    import csdl_hop_dong as cs
    try:
        return cs.ngay_iso(v)
    except (ValueError, TypeError):
        return None


def kiem_tra(kq):
    """(Tính lại) phân loại BOQ + 18 kiểm tra P01–P18 + kiểm tra riêng của bản trích. Ghi vào kq, trả kq."""
    cs, con = _cs()
    try:
        tc = []                                          # kiểm tra riêng [(mã, mức, nội dung)]
        for w in kq.get("canh_bao_doc") or []:
            tc.append(("P20", "THÔNG TIN", w))
        if kq.get("ocr"):
            o = kq["ocr"]
            tc.append(("P20", "THÔNG TIN", f"Văn bản lấy từ OCR ABBYY ({o.get('trang', '?')} trang) — chữ và số do máy nhận dạng."))
        if kq.get("loi_ai"):
            tc.append(("P22", "VÀNG", kq["loi_ai"]))
        if not kq.get("ma_hd"):
            kq["kiem_tra"] = [("P01", "CHẶN", "Chưa xác định được hợp đồng — chọn hợp đồng của phụ lục.")] + tc
            kq["boq"]["dong"], kq["boq"]["so_sanh"] = [], []
            return kq
        try:
            hd = cs.tim_hd(con, kq["ma_hd"])
        except SystemExit as e:
            kq["kiem_tra"] = [("P01", "CHẶN", str(e))] + tc
            return kq
        kq["so_hd"] = hd["so_hd"]
        info = dict(kq["info"])
        ngay_hl = _ngay_iso(info.get("ngay_hieu_luc")) or _ngay_iso(info.get("ngay_ky"))
        so_pl = str(info.get("so_pl") or "").upper()
        truoc = [p for p in cs.phu_luc_ap_dung(con, hd["ma_hd"]) if ngay_hl and (p["ngay_hieu_luc"], p["so_pl"]) <= (ngay_hl, so_pl)]
        hl, _ = cs.boq_hieu_luc(con, hd["ma_hd"], pls=truoc)
        gt_truoc = cs.gt_hd_hieu_luc(con, hd["ma_hd"], pls=truoc)
        kq["gt_truoc_pl"] = gt_truoc
        bq = kq["boq"]
        if bq.get("bang") and not hl and bq["che_do"] != "khong":
            tc.append(("P21", "CHẶN", "Hợp đồng chưa có BOQ gốc trong CSDL mà phụ lục đổi BOQ → nạp BOQ gốc trước "
                                      "(BOQ → Import BOQ), rồi nạp phụ lục. Hoặc chọn 'Không đổi BOQ (chỉ ghi nhận)'."))
            b_rows, so_sanh, note = [], [], []
        else:
            b_rows, so_sanh, note = phan_loai_boq(bq.get("bang"), hl, bq["che_do"], kq["ten"])
        bq["dong"], bq["so_sanh"] = b_rows, so_sanh
        tc += [("P23", md, nd) for md, nd in note]
        if bq.get("thoi_han") and bq["che_do"] != "khong":
            th = bq["thoi_han"]
            tc.append(("P24", "ĐỎ", f"Phụ lục chỉ áp đơn giá cho KL thực hiện từ {th['tu']} đến {th['den']}, nhưng đang chọn "
                                    f"'{CHE_DO_BOQ[bq['che_do']]}' → đơn giá mới áp cho mọi đợt từ ngày hiệu lực về sau."))
        elif bq.get("thoi_han"):
            th = bq["thoi_han"]
            tc.append(("P24", "VÀNG", f"Đơn giá điều chỉnh chỉ áp cho KL thực hiện từ {th['tu']} đến {th['den']}: phần mềm "
                                      "chưa áp đơn giá theo khoảng thời gian → chỉ ghi nhận, BOQ không đổi. Khi kiểm tra đợt "
                                      "có KL trong khoảng này cần đối chiếu tay."))
        # giá trị: theo số ghi trên phụ lục; GT HĐ sau PL có mà không ghi tăng/giảm → tự tính, ghi rõ
        if info.get("gt_sau_vat") in (None, "") and info.get("gt_hd_sau_pl") not in (None, ""):
            gs = ocr.so_vn(info["gt_hd_sau_pl"]) if isinstance(info["gt_hd_sau_pl"], str) else info["gt_hd_sau_pl"]
            if gs is not None:
                info["gt_sau_vat"] = round(gs - gt_truoc)
                tc.append(("P25", "THÔNG TIN", f"Phụ lục không ghi giá trị tăng/giảm: tự tính = GT HĐ sau PL {gs:,.0f} − GT "
                                               f"trước PL {gt_truoc:,.0f} = {gs - gt_truoc:+,.0f}."))
        info["doi_boq"] = "Có" if b_rows else "Không"
        info["so_hd"] = hd["so_hd"]
        info["file_nguon"] = kq["ten"]
        a_rows = [dict(dong=i + 1, ma_ts=r["ma_ts"], ten=r["ten"], cu=r.get("cu"), moi=r.get("moi"), trich=r.get("trich"))
                  for i, r in enumerate(kq["tham_so"]) if not r.get("bo")]
        for r in kq["tham_so"]:
            if r.get("bo"):
                continue
            if r.get("kiem_tra_trich") and r.get("trang_thai") == "Chưa xác nhận":
                tc.append(("P22", "VÀNG", f"{r['ma_ts']}: {r['kiem_tra_trich']}."))
        cho = [r["ma_ts"] for r in kq["tham_so"] if not r.get("bo") and r.get("trang_thai") == "Chưa xác nhận"]
        if cho:
            tc.append(("P22", "VÀNG", f"{len(cho)} tham số chưa xác nhận: {', '.join(cho)} — xác nhận hoặc bỏ trước khi nạp."))
        for k in kq.get("khac") or []:
            tc.append(("P26", "THÔNG TIN", f"Thay đổi khác (không thuộc tham số, chỉ ghi nhận): {k.get('noi_dung', '')[:200]}"))
        kt, pl, dong, dong_ts = cs.kiem_tra_phu_luc(con, hd, info, a_rows, copy.deepcopy(b_rows), [])
        kq["pl"] = {k: v for k, v in pl.items()}
        kq["info_tinh"] = {"gt_sau_vat": pl.get("gt_sau_vat"), "gt_truoc_vat": pl.get("gt_truoc_vat"),
                           "doi_boq": pl.get("doi_boq")}
        kq["kiem_tra"] = [tuple(x) for x in kt] + tc
        return kq
    finally:
        con.close()


def trich_phu_luc(path, ai=None, tien_do=None, dung=None, ghi_log=None):
    """Một file phụ lục → kết quả (dict) đã kiểm tra, lưu JSON."""
    def td(pct, msg):
        if tien_do:
            tien_do(pct, msg)
    ten = os.path.basename(path)
    data = Path(path).read_bytes()
    sha = hashlib.sha1(data).hexdigest()
    td(0.05, f"Đọc {ten}")
    doc = doc_file(path, tien_do=lambda m: td(0.1, m), dung=dung, ghi_log=ghi_log)
    cs, con = _cs()
    try:
        ds_hd = [(r["ma_hd"], r["so_hd"]) for r in con.execute("SELECT ma_hd, so_hd FROM hop_dong")]
        ma_hd, so_hd, nguon_hd = nhan_hop_dong(doc["text"], ten, ds_hd)
        info, trich, nguon = thong_tin_chung(doc["dong"], ten)
        gtv = gia_tri_van_ban(doc["dong"])
        for k, (v, c) in gtv.items():
            info[k], trich[k], nguon[k] = v, c, "văn bản"
        bang = doc_bang(doc["bang"])
        if bang and bang["tong"].get("sau_vat") and "gt_hd_sau_pl" not in info and bang["loai"] == "moi":
            info["gt_hd_sau_pl"] = bang["tong"]["sau_vat"]
            trich["gt_hd_sau_pl"], nguon["gt_hd_sau_pl"] = bang["trich_tong"].get("sau_vat", ""), "dòng tổng của bảng"
        th = thoi_han_don_gia(doc["dong"])
        che_do = "khong"
        if bang:
            che_do = "thay_doi"
            if bang["loai"] == "moi" and ma_hd:
                hl, _ = cs.boq_hieu_luc(con, ma_hd)
                if hl:
                    co = sum(1 for it in bang["items"] if khop_hang_muc(it, hl)[0])
                    if co >= 0.6 * len(hl):
                        che_do = "toan_bo"
            if th:
                che_do = "khong"
        ts_hh = _ts_hien_hanh(cs, con, ma_hd, _ngay_iso(info.get("ngay_ky"))) if ma_hd else []
        if ai is not None and ma_hd:
            from trich_xuat.ai_cloud import dat_che_theo_hd
            dat_che_theo_hd(ai, con, ma_hd)              # Claude: che tên các bên / số HĐ trước khi gửi
    finally:
        con.close()
    tham_so, khac, loi_ai = [], [], ""
    if ai is not None and ma_hd:
        td(0.4, f"Hỏi {getattr(ai, 'ten', 'Local AI')}: tham số {ten} sửa đổi")
        tham_so, khac, loi_ai = _ket_qua_ai(ai, doc["dong"], ts_hh, ghi_log)
    elif ai is None:
        loi_ai = "Chưa hỏi Local AI (máy AI chưa sẵn sàng) — mục tham số để trống; bấm Hỏi lại Local AI khi máy AI sẵn sàng."
    else:
        loi_ai = "Chưa xác định được hợp đồng nên chưa hỏi Local AI — chọn hợp đồng rồi bấm Hỏi lại Local AI."
    td(0.85, "Kiểm tra P01–P18")
    kq = {"id": time.strftime("%Y%m%d%H%M%S") + "_" + sha[:8], "ten": ten, "sha1": sha, "tao_luc": time.time(),
          "ocr": doc["ocr"], "canh_bao_doc": doc["canh_bao"], "ma_hd": ma_hd, "so_hd": so_hd, "nhan_hd": nguon_hd,
          "info": info, "trich": trich, "nguon": nguon, "tham_so": tham_so, "khac": khac, "loi_ai": loi_ai,
          "boq": {"che_do": che_do, "bang": bang, "thoi_han": th, "dong": [], "so_sanh": []},
          "model": getattr(ai, "model", None), "nap": None, "van_ban": doc["dong"]}
    kiem_tra(kq)
    luu(kq)
    td(1.0, f"Xong {ten}")
    return kq


# ================================================================== lưu / đọc / sửa / nạp
def _duong_dan(id_):
    if not re.fullmatch(r"\d{14}_[0-9a-f]{8}", str(id_ or "")):
        raise KeyError("Mã kết quả không hợp lệ")
    return thu_muc_kq() / f"{id_}.json"


def luu(kq):
    p = _duong_dan(kq["id"])
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(kq, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    os.replace(tmp, p)


def doc(id_):
    p = _duong_dan(id_)
    if not p.exists():
        raise KeyError("Không có kết quả trích phụ lục này")
    return json.loads(p.read_text(encoding="utf-8"))


def tom_tat(kq):
    kt = kq.get("kiem_tra") or []
    dem = lambda m: sum(1 for x in kt if x[1] == m)  # noqa: E731
    i = kq.get("info") or {}
    return {"id": kq["id"], "ten": kq["ten"], "ma_hd": kq.get("ma_hd"), "so_hd": kq.get("so_hd"), "so_pl": i.get("so_pl"),
            "ngay_ky": i.get("ngay_ky"), "tao_luc": kq.get("tao_luc"), "ocr": bool(kq.get("ocr")),
            "so_tham_so": sum(1 for r in kq.get("tham_so") or [] if not r.get("bo")),
            "so_boq": len((kq.get("boq") or {}).get("dong") or []), "so_khac": len(kq.get("khac") or []),
            "chan": dem("CHẶN"), "do": dem("ĐỎ"), "vang": dem("VÀNG"),
            "chua_xac_nhan": sum(1 for r in kq.get("tham_so") or [] if not r.get("bo") and r.get("trang_thai") == "Chưa xác nhận"),
            "nap": kq.get("nap")}


def danh_sach():
    out = []
    for p in sorted(thu_muc_kq().glob("*.json"), reverse=True):
        try:
            out.append(tom_tat(json.loads(p.read_text(encoding="utf-8"))))
        except (OSError, ValueError, KeyError):
            continue
    return out


SUA_INFO = ("so_pl", "ngay_ky", "ngay_hieu_luc", "trang_thai", "loai", "noi_dung", "can_cu", "gt_sau_vat", "gt_hd_sau_pl")


def cap_nhat(id_, body):
    """Anh sửa: ma_hd, info{…}, tham_so[{ma_ts, moi?, trang_thai?, bo?}], them_ts{ma_ts, moi, trich}, boq_che_do."""
    kq = doc(id_)
    if kq.get("nap"):
        raise ValueError("Phụ lục đã nạp CSDL — không sửa được bản trích này.")
    if "ma_hd" in body and (body["ma_hd"] or None) != kq.get("ma_hd"):
        kq["ma_hd"] = body["ma_hd"] or None
        kq["nhan_hd"] = "Anh chọn"
        if kq["ma_hd"]:
            cs_, con = _cs()
            try:
                for r in kq["tham_so"]:
                    r["cu"], _ = cs_.tham_so_hieu_luc(con, kq["ma_hd"], r["ma_ts"], _ngay_iso(kq["info"].get("ngay_ky")))
            finally:
                con.close()
    for k, v in (body.get("info") or {}).items():
        if k in SUA_INFO:
            if k in ("gt_sau_vat", "gt_hd_sau_pl"):
                v = None if v in (None, "") else (ocr.so_vn(v) if isinstance(v, str) else float(v))
            kq["info"][k] = v
            kq["nguon"][k] = "Anh sửa"
    by = {r["ma_ts"]: r for r in kq["tham_so"]}
    for s in body.get("tham_so") or []:
        r = by.get(str(s.get("ma_ts") or "").upper())
        if not r:
            continue
        if "moi" in s and str(s["moi"]).strip() != str(r.get("moi") or ""):
            r["lich_su"].append({"luc": time.time(), "cu": r.get("moi"), "moi": s["moi"]})
            r["moi"] = str(s["moi"]).strip()
            r["trang_thai"] = "Đã sửa tay"
        if s.get("trang_thai") in TRANG_THAI_TS:
            r["trang_thai"] = s["trang_thai"]
        if "bo" in s:
            r["bo"] = bool(s["bo"])
    t = body.get("them_ts")
    if t:
        import csdl_hop_dong as cs
        ma = str(t.get("ma_ts") or "").strip().upper()
        ten = {m: n for _, ds in cs.DS_THAM_SO for m, n in ds}
        if ma not in ten:
            raise ValueError(f"Mã tham số không hợp lệ: {ma}")
        if ma in by:
            raise ValueError(f"{ma} đã có trong danh sách")
        cu = None
        if kq.get("ma_hd"):
            cs_, con = _cs()
            try:
                cu, _ = cs_.tham_so_hieu_luc(con, kq["ma_hd"], ma, _ngay_iso(kq["info"].get("ngay_ky")))
            finally:
                con.close()
        if not str(t.get("moi") or "").strip():
            raise ValueError("Nhập giá trị mới của tham số")
        kq["tham_so"].append({"ma_ts": ma, "ten": ten[ma], "cu": cu, "moi": str(t.get("moi") or "").strip(),
                              "trich": str(t.get("trich") or "").strip(), "dieu": "", "ghi_chu": "Anh thêm",
                              "kiem_tra_trich": kiem_trich(t.get("trich"), _gon("\n".join(kq.get("van_ban") or []))),
                              "trang_thai": "Đã sửa tay", "nguon": "Anh thêm", "lich_su": []})
    if body.get("boq_che_do") in CHE_DO_BOQ:
        kq["boq"]["che_do"] = body["boq_che_do"]
    kiem_tra(kq)
    luu(kq)
    return kq


def nap(id_):
    """Ghi phụ lục vào CSDL (kiểm tra lại với CSDL hiện tại). Còn CHẶN / tham số chưa xác nhận → ValueError."""
    kq = doc(id_)
    if kq.get("nap"):
        raise ValueError(f"Đã nạp lúc {kq['nap'].get('luc')}")
    cho = [r["ma_ts"] for r in kq["tham_so"] if not r.get("bo") and r.get("trang_thai") == "Chưa xác nhận"]
    if cho:
        raise ValueError(f"Còn {len(cho)} tham số chưa xác nhận: {', '.join(cho)}")
    kiem_tra(kq)
    chan = [x for x in kq["kiem_tra"] if x[1] == "CHẶN"]
    if chan:
        luu(kq)
        raise ValueError("Còn lỗi CHẶN: " + "; ".join(x[2] for x in chan[:3]))
    cs, con = _cs()
    try:
        hd = cs.tim_hd(con, kq["ma_hd"])
        info = dict(kq["info"], doi_boq="Có" if kq["boq"]["dong"] else "Không", so_hd=hd["so_hd"], file_nguon=kq["ten"])
        if info.get("gt_sau_vat") in (None, "") and (kq.get("info_tinh") or {}).get("gt_sau_vat") is not None:
            info["gt_sau_vat"] = kq["info_tinh"]["gt_sau_vat"]
        a_rows = [dict(dong=i + 1, ma_ts=r["ma_ts"], ten=r["ten"], cu=r.get("cu"), moi=r.get("moi"),
                       trich=(r.get("trich") or "") + (f" [{r['dieu']}]" if r.get("dieu") else ""))
                  for i, r in enumerate(kq["tham_so"]) if not r.get("bo")]
        kt, pl, dong, dong_ts = cs.kiem_tra_phu_luc(con, hd, info, a_rows, copy.deepcopy(kq["boq"]["dong"]), [])
        if any(x[1] == "CHẶN" for x in kt):
            raise ValueError("Còn lỗi CHẶN: " + "; ".join(x[2] for x in kt if x[1] == "CHẶN"))
        if kq.get("khac"):
            pl["noi_dung"] = ((pl.get("noi_dung") or "") + " | Thay đổi khác: " +
                              "; ".join(k["noi_dung"] for k in kq["khac"]))[:1000]
        rieng = [tuple(x) for x in kq["kiem_tra"] if x[0] in ("P21", "P22", "P23", "P24")]
        pl_id = cs.ghi_phu_luc(con, pl, dong, dong_ts, [tuple(x) for x in kt] + rieng,
                               f"Trích AI {kq['id']} ({kq['ten']})", kq["ten"])
        con.commit()
    finally:
        con.close()
    kq["nap"] = {"pl_id": pl_id, "luc": time.strftime("%Y-%m-%d %H:%M:%S"), "so_pl": pl["so_pl"], "ma_hd": pl["ma_hd"]}
    luu(kq)
    return kq


def xoa(id_):
    p = _duong_dan(id_)
    if p.exists():
        p.unlink()
