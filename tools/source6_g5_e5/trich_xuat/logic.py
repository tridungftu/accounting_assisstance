# -*- coding: utf-8 -*-
"""
Nguồn: src/kho_tri_thuc/m4/review_goc/trich_xuat/logic.py
SHA-256 nguồn trước sửa: f7cfcf37ff2293d8f8ea994f1ae0a69f57d1d1d9a844f0620f018a3d285a4452

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


def _lich_xd(g, them, quy_tac):
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


def _phat_xd(g, them, quy_tac):
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


def _co_noi_dung(v):
    return bool(v) and not la_khong_co(v) and not la_khong_ap_dung(v)


def _lich_mua(g, them, quy_tac):
    """Kiểm chuỗi lịch hiện có; không trích bảng E3, không cộng TT-13/TT-21."""
    v = g("TT-20")
    if not _co_noi_dung(v):
        return
    # ty_le() của XD bỏ trùng; lịch mua phải đếm từng lần.
    rates = [Decimal(so_chuan(m.group(1))) for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*%", v)]
    if not rates and re.fullmatch(r"\s*\d+(?:[.,]\d+)?\s*", v) and g("TT-20", "don_vi") in ("", "%"):
        rates = [_mot_so(v)]
    if rates and sum(rates) > 100:
        them("TT-20", f"L2: tổng tỷ lệ lịch thanh toán = {_s(sum(rates))}% > 100% — cần rà soát")
    ctx = bo_dau(v.lower())
    if re.search(r"\b(?:coc|ky quy)\b|\btt\s*-\s*13\b", ctx):
        them("TT-20", "L2: cọc/ký quỹ (TT-13) không nằm trong lịch thanh toán TT-20 — cần rà soát")
    if quy_tac["can_tt80"] and not _co_noi_dung(g("TT-80")):
        msg = "L3: thiếu thời hạn hợp đồng TT-80; chưa thể coi lịch TT-20 hợp lệ — cần rà soát"
        them("TT-20", msg)
        them("TT-80", msg)


def _phat_mua(g, them, quy_tac):
    """Chỉ tính %/ngày × ngày tường minh trong tham số phạt, không lấy TT-80.

    Căn cứ toàn HĐ/không rõ: cảnh báo rà soát, không tự quy đổi phần vi phạm.
    """
    for ma in ("TT-54", "TT-55"):
        v = g(ma)
        if not _co_noi_dung(v):
            continue
        rates = days = []
        # Giá trị ngắn có thể chỉ có mức phạt; câu trích dẫn giữ số ngày/căn cứ.
        for text in (v, g(ma, "trich_dan")):
            ctx = bo_dau(text.lower())
            rates = re.findall(r"(\d+(?:[.,]\d+)?)\s*%\s*(?:/|moi|mot|tren)\s*ngay", ctx)
            days = re.findall(r"(?<![\d.,])(\d+)\s*ngay\b", ctx)
            if rates and days:
                break
        if not rates or not days:
            continue
        if len(rates) != 1 or len(days) != 1 or not re.search(r"phan(?:\s+\w+){0,8}\s+vi pham", ctx):
            them("TT-55", "L5: chưa xác định duy nhất mức phạt/ngày, số ngày và căn cứ phần vi phạm; cần rà soát trần 8%")
            continue
        total = Decimal(so_chuan(rates[0])) * Decimal(days[0])
        if total > 8:
            them("TT-55", f"L5: mức phạt/ngày × số ngày = {_s(total)}% > 8% phần vi phạm — cần rà soát")


# E2: bảng dữ liệu chọn L2/L3/L5; loại chưa đăng ký không được suy thành XD.
QUY_TAC_CHUNG = {"L2_L3": _lich_mua, "L5": _phat_mua, "can_tt80": False}
QUY_TAC_THEO_LOAI = {
    "XD": {"L2_L3": _lich_xd, "L5": _phat_xd, "can_tt80": False},
    "DV": {**QUY_TAC_CHUNG, "can_tt80": True},
    "MUA_HH": {**QUY_TAC_CHUNG},
    "THUE_TS": {**QUY_TAC_CHUNG, "can_tt80": True},
    "NHAP_KHAU": {**QUY_TAC_CHUNG},
}


def kiem_tra_logic(ket_qua, params, rows_by_id=None, loai_hop_dong="XD"):
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

    quy_tac = QUY_TAC_THEO_LOAI.get(loai_hop_dong, QUY_TAC_CHUNG)
    if loai_hop_dong not in QUY_TAC_THEO_LOAI:
        for p in params:
            them(p["ma"], f"E2: loại {loai_hop_dong!r} chưa có quy tắc riêng; dùng quy tắc chung an toàn, cần rà soát")

    # L1
    for p in params:
        it = ket_qua.get(p["ma"]) or {}
        v, q = (it.get("gia_tri") or ""), (it.get("trich_dan") or "")
        if (la_khong_ap_dung(v) or la_khong_co(v)) and q:
            con = re.findall(r"\d+(?:[.,]\d+)*\s*%?", _bo_tham_chieu(q))
            if con:
                them(p["ma"], f"L1: ghi '{v[:30]}' nhưng trích dẫn có số liệu ({', '.join(c.strip() for c in con[:3])})")

    # L2/L3 theo bảng quy tắc đã chọn
    quy_tac["L2_L3"](g, them, quy_tac)

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

    # L5 theo bảng quy tắc đã chọn
    quy_tac["L5"](g, them, quy_tac)
    return loi
