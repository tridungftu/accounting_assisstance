"""Bộ lọc định dạng cho mã trộn — Mục 7 và docs/02 mục 5.

    ${tong_thanh_tien}          116636850
    ${tong_thanh_tien|tien}     116.636.850
    ${tong_thanh_tien|tien_dv}  116.636.850 VND
    ${tong_thanh_tien|chu}      Một trăm mười sáu triệu ... đồng
    ${ngay_tao|ngay}            12/08/2025
    ${ngay_tao|ngay_du}         ngày 12 tháng 08 năm 2025

Bộ lọc |chu là lý do cả nhóm này tồn tại: nó thay cho việc người tạo gõ tay số
tiền bằng chữ, xoá hẳn nguy cơ lệch giữa số và chữ trên chứng từ.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .so_chu import so_thanh_chu

# Số chữ số thập phân theo tập quán từng đồng tiền. VND không có phần lẻ.
SO_LE = {"VND": 0, "JPY": 0, "KRW": 0}


class LocKhongHieu(ValueError):
    """Mẫu dùng một bộ lọc không tồn tại."""


class GiaTriKhongHopLe(ValueError):
    """Giá trị không đúng kiểu mà bộ lọc cần."""


def _lay_so(gia_tri) -> Decimal:
    """Rút số ra khỏi giá trị, chấp nhận cả kiểu tiền {amount, currency}."""
    if isinstance(gia_tri, dict):
        gia_tri = gia_tri.get("amount")
    if gia_tri is None or gia_tri == "":
        raise GiaTriKhongHopLe("không có giá trị")
    if isinstance(gia_tri, Decimal):
        return gia_tri
    if isinstance(gia_tri, (int, float)):
        return Decimal(str(gia_tri))
    s = str(gia_tri).strip()
    try:
        return Decimal(s)
    except InvalidOperation as e:
        raise GiaTriKhongHopLe(f"không phải một số: {gia_tri!r}") from e


def _lay_ma_tien(gia_tri, mac_dinh=None) -> str | None:
    if isinstance(gia_tri, dict):
        return gia_tri.get("currency") or mac_dinh
    return mac_dinh


def dinh_dang_tien(so: Decimal, ma_tien: str | None = None) -> str:
    """Ngăn nghìn bằng dấu chấm, thập phân bằng dấu phẩy — quy ước Việt Nam."""
    le = SO_LE.get(ma_tien or "", 2 if so != so.to_integral_value() else 0)

    am = so < 0
    so = abs(so)
    nguyen = int(so)
    phan_le = so - nguyen

    chuoi = f"{nguyen:,}".replace(",", ".")
    if le > 0:
        s_le = format(phan_le, "f").split(".", 1)[1] if phan_le else ""
        s_le = (s_le + "0" * le)[:le]
        chuoi = f"{chuoi},{s_le}"

    return f"-{chuoi}" if am else chuoi


def _doc_ngay(gia_tri) -> date:
    if isinstance(gia_tri, datetime):
        return gia_tri.date()
    if isinstance(gia_tri, date):
        return gia_tri
    if isinstance(gia_tri, dict):
        # Trường ngày của biểu mẫu: {"date": "2026-10-15"} hoặc khoảng ngày
        gia_tri = gia_tri.get("date") or gia_tri.get("from")
    s = str(gia_tri or "").strip()
    if not s:
        raise GiaTriKhongHopLe("không có ngày")
    # Chấp nhận cả ISO đầy đủ lẫn chỉ ngày
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if not m:
        raise GiaTriKhongHopLe(f"không phải một ngày: {gia_tri!r}")
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


# --------------------------------------------------------------- từng bộ lọc

def loc_tien(gia_tri, ngu_canh=None) -> str:
    return dinh_dang_tien(_lay_so(gia_tri), _lay_ma_tien(gia_tri))


def loc_tien_dv(gia_tri, ngu_canh=None) -> str:
    ma = _lay_ma_tien(gia_tri) or (ngu_canh or {}).get("__ma_tien") or ""
    so = dinh_dang_tien(_lay_so(gia_tri), ma or None)
    return f"{so} {ma}".strip()


def loc_chu(gia_tri, ngu_canh=None) -> str:
    """Đọc số thành chữ. Đơn vị lấy theo mã tiền tệ, không mặc định VND ngầm.

    Mục 15.4 cấm mặc định VND ở bất kỳ đâu. Ở đây nếu không biết mã tiền tệ thì
    đọc không kèm đơn vị, thay vì đoán là đồng.
    """
    so = _lay_so(gia_tri)
    ma = _lay_ma_tien(gia_tri) or (ngu_canh or {}).get("__ma_tien")
    don_vi = {"VND": "đồng", "USD": "đô la Mỹ", "EUR": "euro"}.get(ma or "", ma or "")
    return so_thanh_chu(so, don_vi)


def loc_ngay(gia_tri, ngu_canh=None) -> str:
    d = _doc_ngay(gia_tri)
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def loc_ngay_du(gia_tri, ngu_canh=None) -> str:
    d = _doc_ngay(gia_tri)
    return f"ngày {d.day:02d} tháng {d.month:02d} năm {d.year}"


BO_LOC = {
    "tien": loc_tien,
    "tien_dv": loc_tien_dv,
    "chu": loc_chu,
    "ngay": loc_ngay,
    "ngay_du": loc_ngay_du,
}


def ap_loc(ten_loc: str, gia_tri, ngu_canh=None) -> str:
    ham = BO_LOC.get(ten_loc)
    if ham is None:
        raise LocKhongHieu(
            f'Không có bộ lọc "{ten_loc}". Các bộ lọc dùng được: '
            + ", ".join(sorted(BO_LOC))
        )
    return ham(gia_tri, ngu_canh)
