# -*- coding: utf-8 -*-
"""
logic.py — Bước 7: kiểm tra LOGIC giữa các tham số (luôn chạy, không gọi AI). Mỗi lỗi → ô vàng kèm lý do.
  L1  Giá trị "Không áp dụng"/"Không quy định" nhưng trích dẫn lại có số liệu.
  L2  Tỷ lệ thanh toán mỗi đợt (TT-20) + tỷ lệ giữ lại (TT-21) ≠ 100%.
  L3  HĐ nhiều giai đoạn / nhiều loại đợt với tỷ lệ thanh toán khác nhau → nhắc kiểm tra đợt đang xét dùng tỷ lệ nào.
  L4  Trích dẫn thiếu từ khoá bắt buộc của tham số, hoặc chứa từ khoá loại trừ (danh mục tham số) → có thể lấy nhầm khoản.
  L5  Nhiều mức phạt trong cùng một câu (TT-52/53/54) → kiểm tra đã tách đúng mức.
"""
import re
from decimal import Decimal

from .cau_truc import bo_dau
from .kiem_tra import la_khong_ap_dung, la_khong_co, so_chuan

_THAM_CHIEU = re.compile(r"(điều|khoản|mục|điểm|phụ lục|chương|phần)\s*[\dIVXLC]+(?:\.\d+)*[a-zđ]?", re.I)
_NGAY = re.compile(r"\d{1,2}\s*[/.-]\s*\d{1,2}\s*[/.-]\s*\d{2,4}|ngày\s*\d{1,2}\s*tháng\s*\d{1,2}\s*năm\s*\d{4}", re.I)
_SO_HD = re.compile(r"\b\d+/\d{2,4}/[\w\-/Đđ]+")


def _bo_tham_chieu(s):
    return _SO_HD.sub(" ", _NGAY.sub(" ", _THAM_CHIEU.sub(" ", s or "")))


def ty_le(s):
    """Các tỷ lệ % trong chuỗi (Decimal), giữ thứ tự, bỏ trùng."""
    out = []
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*%", s or ""):
        try:
            d = Decimal(so_chuan(m.group(1)))
        except Exception:  # noqa: BLE001
            continue
        if d not in out:
            out.append(d)
    return out


def _mot_so(v):
    """Giá trị chỉ là một con số / một tỷ lệ (vd '10', '10%', '90 %') → Decimal; ngược lại None."""
    t = ty_le(v)
    if len(t) == 1:
        return t[0]
    m = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*", v or "")
    if m:
        try:
            return Decimal(so_chuan(m.group(1)))
        except Exception:  # noqa: BLE001
            return None
    return None


def _s(d):
    return format(d.normalize(), "f").replace(".", ",")


def kiem_tra_logic(ket_qua, params, rows_by_id=None):
    """ket_qua: {mã: item AI (gia_tri, trich_dan, ghi_chu, _row…)}; params: danh sách tham số.
    Trả {mã: [lý do…]} chỉ gồm tham số có lỗi."""
    rows_by_id = rows_by_id or {}
    loi = {}

    def them(ma, msg):
        loi.setdefault(ma, [])
        if msg not in loi[ma]:
            loi[ma].append(msg)

    def g(ma, k="gia_tri"):
        return ((ket_qua.get(ma) or {}).get(k) or "").strip()

    # L1
    for p in params:
        it = ket_qua.get(p["ma"]) or {}
        v, q = (it.get("gia_tri") or ""), (it.get("trich_dan") or "")
        if (la_khong_ap_dung(v) or la_khong_co(v)) and q:
            con = re.findall(r"\d+(?:[.,]\d+)*\s*%?", _bo_tham_chieu(q))
            if con:
                them(p["ma"], f"L1: ghi '{v[:30]}' nhưng trích dẫn có số liệu ({', '.join(c.strip() for c in con[:3])})")

    # L2 + L3
    v20, v21, q20 = g("TT-20"), g("TT-21"), g("TT-20", "trich_dan")
    r20 = [x for x in ty_le(v20) if x != 100]
    r20q = [x for x in ty_le(q20) if x != 100]
    nhieu = len(r20) >= 2
    if nhieu:
        msg = (f"L3: HĐ có nhiều tỷ lệ thanh toán ({' | '.join(_s(x) + '%' for x in r20)}) — kiểm tra đợt đang xét "
               "thuộc giai đoạn nào")
        them("TT-20", msg)
        if v21:
            them("TT-21", msg)
    elif len(r20q) >= 2 and re.search(r"giai đoạn|đợt|lần", q20, re.I):
        them("TT-20", f"L3: trích dẫn có nhiều tỷ lệ ({' | '.join(_s(x) + '%' for x in r20q)}) nhưng giá trị chỉ ghi một")
    if not nhieu and v20 and v21 and not la_khong_co(v21) and not la_khong_ap_dung(v20):
        a, b = _mot_so(v20), _mot_so(v21)
        if a is not None and b is not None and a + b != 100:
            msg = f"L2: TT-20 ({_s(a)}%) + TT-21 ({_s(b)}%) = {_s(a + b)}% ≠ 100%"
            them("TT-20", msg)
            them("TT-21", msg)

    # L4
    for p in params:
        it = ket_qua.get(p["ma"]) or {}
        v, q = (it.get("gia_tri") or ""), (it.get("trich_dan") or "")
        if not v or not q or la_khong_co(v) or la_khong_ap_dung(v):
            continue
        r = rows_by_id.get(it.get("_row")) or {}
        ctx = bo_dau((q + " " + (r.get("tieu_de_dieu") or "") + " " + (r.get("tieu_de_khoan") or "")).lower())
        qk = bo_dau(q.lower())
        bb = p.get("bat_buoc") or []
        if bb and not any(bo_dau(k) in ctx for k in bb):
            them(p["ma"], f"L4: trích dẫn thiếu từ khoá ({' / '.join(bb[:4])}) — có thể lấy nhầm khoản")
        lt = [k for k in (p.get("loai_tru") or []) if bo_dau(k) in qk]
        if lt:
            them(p["ma"], f"L4: trích dẫn chứa '{lt[0]}' — có thể lấy nhầm khoản")

    # L5
    q52, q53, q54 = g("TT-52", "trich_dan"), g("TT-53", "trich_dan"), g("TT-54", "trich_dan")
    v52, v53 = g("TT-52"), g("TT-53")
    m52 = ty_le(q52)
    if len(ty_le(v52)) >= 2:
        them("TT-52", f"L5: giá trị gộp nhiều mức phạt ({' | '.join(_s(x) + '%' for x in ty_le(v52))}) — chỉ ghi mức 1")
    if len(m52) >= 2:
        if not v53 or la_khong_co(v53) or la_khong_ap_dung(v53):
            them("TT-53", f"L5: câu trích TT-52 có {len(m52)} mức phạt ({' | '.join(_s(x) + '%' for x in m52)}) "
                          "nhưng TT-53 không có giá trị")
        elif ty_le(v52) and ty_le(v52) == ty_le(v53):
            them("TT-53", "L5: TT-52 và TT-53 cùng một mức phạt dù câu có nhiều mức")
    if len(ty_le(q53)) >= 2 and len(ty_le(v53)) >= 2:
        them("TT-53", "L5: giá trị gộp nhiều mức phạt — chỉ ghi mức 2")
    if len(ty_le(q54)) >= 2:
        them("TT-54", f"L5: câu có nhiều mức phạt ({' | '.join(_s(x) + '%' for x in ty_le(q54))}) — kiểm tra đúng mức "
                      "phạt chậm tổng tiến độ")
    return loi
