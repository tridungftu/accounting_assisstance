"""Đọc số thành chữ tiếng Việt — tiêu chí #5 của Giai đoạn 0 (Mục 13).

Đây là lý do cả bộ lọc |chu tồn tại. Mục 7 của đặc tả:

    "|chu là đọc số thành chữ tiếng Việt — thay cho việc người dùng gõ tay,
     xóa hẳn nguy cơ lệch giữa số và chữ trên chứng từ."

Bản kiểm chứng trong tools/render_base_template.py có hai lỗi ở mốc nghìn tỷ:

    1.500.000.000.000  ->  "Năm trăm tỷ đồng"   SAI SỐ, không báo lỗi gì
    2.000.000.000.000  ->  IndexError, chết chương trình

Với tập đoàn có mảng bất động sản, đề xuất trên 1.000 tỷ là chuyện có thật, và
lỗi loại này nguy hiểm nhất trong các loại: chứng từ in ra số bằng chữ sai mà
không ai được cảnh báo.

--------------------------------------------------------------------------
CÁCH TIẾNG VIỆT ĐỌC SỐ LỚN

Tiếng Việt KHÔNG có tên riêng cho 10^12. Trên mốc tỷ, nó lặp lại chính cách
đọc cũ rồi thêm chữ "tỷ":

    1.234.000.000.000  =  1234 "tỷ"  =  "một nghìn hai trăm ba mươi tư tỷ"
    10^18              =  10^9 "tỷ"  =  "một tỷ tỷ"

Nên thuật toán đúng là ĐỆ QUY THEO MỐC TỶ, không phải chia nhóm ba chữ số
phẳng rồi gán tên cho từng nhóm. Chia phẳng cho ra "một nghìn tỷ hai trăm ba
mươi tư tỷ" — vừa sai vừa vô nghĩa.
"""

from __future__ import annotations

import re
from decimal import Decimal

CHU_SO = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]

TY = 10**9
NHOM_DUOI_TY = ["", " nghìn", " triệu"]

# Ngưỡng chặn. Trên mức này gần như chắc chắn là dữ liệu sai, và đọc ra một
# chuỗi dài vô nghĩa còn tệ hơn là báo lỗi.
GIOI_HAN = 10**21


class SoQuaLon(ValueError):
    """Số vượt ngoài khả năng đọc. Thà báo lỗi còn hơn đọc sai."""


def _doc_ba_chu_so(tram: int, chuc: int, donvi: int, day_du: bool) -> str:
    """Đọc một nhóm ba chữ số.

    day_du = True khi nhóm này KHÔNG phải nhóm dẫn đầu, nên phải đọc cả
    "không trăm" để giữ đúng vị trí: 1.000.050 là "một triệu không trăm năm
    mươi", không phải "một triệu năm mươi".
    """
    phan = []

    if tram > 0:
        phan.append(f"{CHU_SO[tram]} trăm")
    elif day_du and (chuc > 0 or donvi > 0):
        phan.append("không trăm")

    if chuc > 1:
        phan.append(f"{CHU_SO[chuc]} mươi")
        if donvi == 1:
            phan.append("mốt")  # hai mươi mốt, không phải "hai mươi một"
        elif donvi == 4:
            phan.append("tư")  # hai mươi tư
        elif donvi == 5:
            phan.append("lăm")  # hai mươi lăm
        elif donvi > 0:
            phan.append(CHU_SO[donvi])
    elif chuc == 1:
        phan.append("mười")
        if donvi == 5:
            phan.append("lăm")  # mười lăm
        elif donvi > 0:
            phan.append(CHU_SO[donvi])
    elif donvi > 0:
        # Hàng chục bằng 0 mà có hàng đơn vị thì cần chữ "lẻ": một trăm lẻ một
        if tram > 0 or day_du:
            phan.append("lẻ")
        phan.append(CHU_SO[donvi])

    return " ".join(phan)


def _doc_duoi_ty(n: int, day_du: bool) -> str:
    """Đọc phần nhỏ hơn một tỷ. day_du áp cho nhóm dẫn đầu của chính phần này."""
    nhom = []
    con = n
    while con > 0:
        nhom.append(con % 1000)
        con //= 1000

    phan = []
    cao_nhat = len(nhom) - 1
    for i in range(cao_nhat, -1, -1):
        ba = nhom[i]
        # Nhóm rỗng ở giữa không được đọc thành "không triệu không nghìn"
        if ba == 0:
            continue
        doc = _doc_ba_chu_so(
            ba // 100,
            (ba // 10) % 10,
            ba % 10,
            day_du=day_du or i != cao_nhat,
        )
        phan.append(doc + NHOM_DUOI_TY[i])

    return " ".join(phan)


def _doc(n: int, day_du: bool) -> str:
    if n < TY:
        return _doc_duoi_ty(n, day_du)

    cao = n // TY
    du = n % TY

    chu = _doc(cao, day_du) + " tỷ"
    if du > 0:
        # Phần dư luôn đọc đầy đủ: 1.000.000.001 là "một tỷ không trăm lẻ một"
        chu += " " + _doc_duoi_ty(du, day_du=True)
    return chu


def doc_so(n: int) -> str:
    """Đọc một số nguyên thành chữ, chưa kèm đơn vị."""
    if n < 0:
        return "âm " + doc_so(-n)
    if n == 0:
        return "không"
    if n >= GIOI_HAN:
        raise SoQuaLon(
            f"Số {n} vượt quá {GIOI_HAN - 1}, ngoài khả năng đọc thành chữ. "
            f"Kiểm tra lại số liệu trước khi in chứng từ."
        )
    return re.sub(r"\s+", " ", _doc(n, day_du=False)).strip()


def so_thanh_chu(gia_tri, don_vi: str = "đồng") -> str:
    """Đọc số tiền thành chữ, viết hoa chữ đầu và kèm đơn vị.

    Nhận số nguyên, chuỗi thập phân hoặc Decimal.

    KHÔNG xoá khoảng trắng bên trong chuỗi. "1 000 000" có thể là một triệu mà
    cũng có thể là gõ nhầm; trên chứng từ chi tiền, đoán ý người nhập là cách
    tạo ra sai sót không ai phát hiện được. Việc bóc dấu phân cách nghìn là
    việc của ô nhập liệu, trước khi tới đây.
    """
    if isinstance(gia_tri, str):
        s = gia_tri.strip()
        if not re.fullmatch(r"-?\d+(\.\d+)?", s):
            raise ValueError(f"Không đọc được số tiền: {gia_tri!r}")
        d = Decimal(s)
    elif isinstance(gia_tri, Decimal):
        d = gia_tri
    elif isinstance(gia_tri, bool) or not isinstance(gia_tri, (int, float)):
        raise ValueError(f"Không đọc được số tiền: {gia_tri!r}")
    else:
        d = Decimal(str(gia_tri))

    am = d < 0
    d = abs(d)

    nguyen = int(d)
    le = d - nguyen

    chu = doc_so(nguyen)

    if le > 0:
        # Phần lẻ đọc theo từng chữ số sau dấu phẩy: 1,25 -> "một phẩy hai lăm"
        phan_le = format(le, "f").split(".", 1)[1].rstrip("0")
        if phan_le:
            doc_le = []
            for i, c in enumerate(phan_le):
                cuoi = i == len(phan_le) - 1
                doc_le.append("lăm" if (cuoi and c == "5" and len(phan_le) > 1) else CHU_SO[int(c)])
            chu += " phẩy " + " ".join(doc_le)

    if am:
        chu = "âm " + chu

    chu = chu[0].upper() + chu[1:]
    return f"{chu} {don_vi}".strip()
