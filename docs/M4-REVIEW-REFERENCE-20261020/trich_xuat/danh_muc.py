# -*- coding: utf-8 -*-
"""
danh_muc.py — Danh mục tham số cần trích (37 tham số chuẩn, sửa/thêm bằng Excel hoặc trên giao diện).

DANH_MUC_THAM_SO.xlsx (trong thư mục trich_xuat), cột đọc theo TÊN tiêu đề:
  Mã | Nhóm | Mô tả cho AI | Từ khoá tiêu đề | Từ khoá nội dung | Dùng (Có/Không)
  | Mức quan trọng (0–3) | Từ khoá bắt buộc (L4) | Từ khoá loại trừ (L4) | Luôn hỏi Claude (Có/Không)
- Từ khoá cách nhau bằng dấu ; — để trống thì AI tự tìm vị trí qua mục lục Điều/Khoản.
- "@mo_dau" trong Từ khoá tiêu đề = ưu tiên phần mở đầu (thông tin các Bên, số HĐ…).
- Mức quan trọng: 0 = thông tin chung, 1 = thấp, 2 = trung bình, 3 = ảnh hưởng trực tiếp tới số tiền thanh toán.
  Dùng để chọn ô gửi kiểm tra chéo trên cloud (ô vàng mức 2–3; ô OK mức 3 lấy ngẫu nhiên x%, mức 2 lấy x/2%).
- L4: trích dẫn phải có ít nhất một "từ khoá bắt buộc" (so cả tiêu đề Khoản) và không chứa "từ khoá loại trừ".
- Luôn hỏi Claude = Có: khi bật kiểm tra chéo cloud, tham số này luôn được gửi (tham số khó), dù local báo OK.
Tham số hỏi thêm cho một lượt (giao diện / YEU_CAU_THEM.txt) được đánh mã Y-01, Y-02… và AI tự tìm vị trí.
"""
import datetime
import os
import re
import shutil

from .cau_hinh import DANH_MUC_THAM_SO
from .xlsx_mini import read_xlsx, write_xlsx

HEADER = ["Mã", "Nhóm", "Mô tả cho AI", "Từ khoá tiêu đề", "Từ khoá nội dung", "Dùng (Có/Không)",
          "Mức quan trọng (0–3)", "Từ khoá bắt buộc (L4)", "Từ khoá loại trừ (L4)", "Luôn hỏi Claude (Có/Không)"]
KHOA = ["ma", "nhom", "mo_ta", "tk", "bk", "dung", "muc", "bat_buoc", "loai_tru", "luon_cloud"]
DO_RONG = [8, 22, 80, 28, 36, 10, 10, 30, 30, 14]
# Tham số khó (điều kiện, nhiều mức, dễ lấy nhầm khoản): khi bật kiểm tra chéo cloud thì luôn gửi Claude dù máy local báo OK
LUON_CLOUD_MAC_DINH = {"TT-11", "TT-40", "TT-41", "TT-52", "TT-53", "TT-54", "TT-56"}
KHONG = ("không", "khong", "no", "0", "x", "false")

# (mã, nhóm, mô tả cho AI, từ khoá tiêu đề, từ khoá nội dung, mức, bắt buộc L4, loại trừ L4)
MAC_DINH = [
    ("TC-01", "Thông tin chung", "Số hợp đồng", "@mo_dau", "số:", 0, "", ""),
    ("TC-02", "Thông tin chung", "Ngày ký", "@mo_dau", "hôm nay; ngày", 0, "", ""),
    ("TC-03", "Thông tin chung", 'Gói thầu (tên gói thầu trên trang bìa/phần mở đầu; nếu HĐ không có dòng "Gói thầu" '
     'thì lấy nội dung "Về việc", không có thì lấy "Hạng mục", và ghi_chu ghi rõ "Lấy từ Về việc" hoặc "Lấy từ Hạng mục")',
     "@mo_dau", "gói thầu; về việc; hạng mục", 0, "", ""),
    ("TC-04", "Thông tin chung", "Dự án", "@mo_dau", "dự án", 0, "", ""),
    ("TC-05", "Thông tin chung", "Địa điểm", "@mo_dau", "địa điểm", 0, "", ""),
    ("TC-06", "Thông tin chung", "Bên A (bên giao thầu / chủ đầu tư)", "@mo_dau; định nghĩa", "bên giao thầu; bên a", 0, "", ""),
    ("TC-07", "Thông tin chung", "Bên B (bên nhận thầu / nhà thầu)", "@mo_dau; định nghĩa", "bên nhận thầu; bên b", 0, "", ""),
    ("TC-08", "Thông tin chung", "Hiệu lực hợp đồng", "hiệu lực", "hiệu lực", 0, "", ""),
    ("TC-09", "Thông tin chung", "Loại hợp đồng theo phạm vi công việc — chọn đúng MỘT trong: Thi công xây dựng; EPC; "
     "Cung cấp vật tư, thiết bị; Tư vấn; Dịch vụ; Khác. trich_dan là câu nêu nội dung/phạm vi công việc của HĐ",
     "@mo_dau; nội dung; phạm vi", "thi công; cung cấp; lắp đặt; thiết kế; tư vấn; dịch vụ", 0, "", ""),
    ("TT-01", "Giá hợp đồng", "Loại hợp đồng (trọn gói / đơn giá cố định / đơn giá điều chỉnh / theo thời gian / kết hợp)",
     "loại hợp đồng", "trọn gói; đơn giá cố định; đơn giá điều chỉnh", 2, "trọn gói; đơn giá; theo thời gian; kết hợp", ""),
    ("TT-02", "Giá hợp đồng", "Giá trị hợp đồng (đồng)", "giá trị hợp đồng; giá hợp đồng", "giá trị hợp đồng; bằng chữ", 3,
     "giá; giá trị", "tạm ứng; bảo lãnh"),
    ("TT-03", "Giá hợp đồng", "Giá trị hợp đồng đã gồm VAT hay chưa (Có / Không)", "giá trị hợp đồng; giá hợp đồng",
     "vat; gtgt", 3, "vat; gtgt; thuế", ""),
    ("TT-04", "Giá hợp đồng", "Thuế suất GTGT (%)", "giá trị hợp đồng; giá hợp đồng", "vat; gtgt; thuế suất", 3,
     "vat; gtgt; thuế", ""),
    ("TT-05", "Giá hợp đồng", "Cơ sở thanh toán khối lượng (KL nghiệm thu thực tế / KL hợp đồng / % hoàn thành)",
     "loại hợp đồng; khối lượng", "nghiệm thu thực tế; khối lượng thực tế", 2, "khối lượng; nghiệm thu; hoàn thành", ""),
    ("TT-10", "Tạm ứng", "Tỷ lệ tạm ứng (%), tính trên giá trị trước hay sau VAT", "tạm ứng", "tạm ứng", 3, "tạm ứng", ""),
    ("TT-11", "Tạm ứng", 'Cách thu hồi tạm ứng (bắt đầu khi nào, mỗi đợt thu bao nhiêu, thu hết khi nào); nếu HĐ không có '
     'tạm ứng / tạm ứng "Không áp dụng" thì ghi "Không áp dụng"', "tạm ứng", "thu hồi; tạm ứng", 3, "thu hồi; tạm ứng; khấu trừ", ""),
    ("TT-12", "Tạm ứng", "Bảo lãnh tạm ứng", "bảo lãnh", "tạm ứng", 2, "bảo lãnh; tạm ứng", "bảo lãnh thực hiện"),
    ("TT-20", "Thanh toán đợt", "Tỷ lệ thanh toán mỗi đợt (% giá trị hoàn thành / nghiệm thu). Nếu HĐ chia nhiều giai đoạn "
     "/ loại đợt với tỷ lệ khác nhau thì liệt kê TỪNG giai đoạn, vd 'Giai đoạn 1: 80%; Giai đoạn 2: 90%'",
     "thanh toán", "giá trị hoàn thành; mỗi đợt", 3, "thanh toán", ""),
    ("TT-21", "Thanh toán đợt", 'Tỷ lệ giữ lại mỗi đợt (%). Nếu HĐ không ghi trực tiếp thì TÍNH = 100% trừ tỷ lệ thanh toán '
     'mỗi đợt; gia_tri ghi CON SỐ (vd 10), ghi_chu ghi "Suy ra"', "thanh toán", "giữ lại; giá trị hoàn thành", 3,
     "giữ lại; thanh toán", ""),
    ("TT-22", "Thanh toán đợt", "Thời hạn thanh toán (số ngày kể từ khi nhận đủ hồ sơ hợp lệ); ghi rõ là NGÀY LÀM VIỆC hay "
     "ngày (lịch) đúng như HĐ ghi", "thanh toán", "thời gian thanh toán; thời hạn thanh toán", 3, "ngày", ""),
    ("TT-30", "Quyết toán - bảo hành", "Tỷ lệ thanh toán khi quyết toán (%)", "quyết toán", "quyết toán", 3, "quyết toán", ""),
    ("TT-31", "Quyết toán - bảo hành", "Tỷ lệ bảo hành hoặc bảo lãnh bảo hành (%)", "bảo hành; bảo lãnh", "bảo hành", 3,
     "bảo hành", ""),
    ("TT-32", "Quyết toán - bảo hành", "Thời hạn bảo hành", "bảo hành; bảo lãnh", "thời hạn bảo hành", 2, "bảo hành", ""),
    ("TT-33", "Quyết toán - bảo hành", "Bảo lãnh thực hiện hợp đồng", "bảo lãnh", "bảo lãnh thực hiện", 2,
     "thực hiện", "tạm ứng"),
    ("TT-40", "Điều chỉnh - phát sinh", "Điều kiện điều chỉnh đơn giá / giá hợp đồng", "điều chỉnh giá",
     "điều chỉnh; biến động", 2, "điều chỉnh", ""),
    ("TT-41", "Điều chỉnh - phát sinh", "Ngưỡng biến động để điều chỉnh giá (%), giá gốc làm căn cứ nếu có",
     "điều chỉnh giá", "biến động; giá gốc; giá dầu", 2, "biến động; điều chỉnh; giá gốc", ""),
    ("TT-42", "Điều chỉnh - phát sinh", "Cách xử lý khối lượng phát sinh, vượt hợp đồng", "điều chỉnh giá; phát sinh",
     "phát sinh", 2, "phát sinh; vượt; ngoài", ""),
    ("TT-50", "Tiến độ - phạt", "Tiến độ / thời gian thực hiện hợp đồng", "tiến độ thực hiện",
     "tiến độ thực hiện; thời gian thực hiện", 2, "tiến độ; thời gian; hoàn thành; ngày", ""),
    ("TT-51", "Tiến độ - phạt", "Mức phạt vi phạm CHẤT LƯỢNG (% tối đa, tính trên giá trị nào). Không lấy mức phạt chậm "
     "tiến độ vào đây", "chất lượng; phạt", "phạt vi phạm", 3, "chất lượng", "chậm tiến độ"),
    ("TT-52", "Tiến độ - phạt", "Tạm giữ hoặc phạt chậm tiến độ giai đoạn - mức 1: chỉ ghi mức ĐẦU TIÊN/thấp hơn (%/ngày) "
     "và áp dụng khi nào (vd chậm 07 ngày đầu); không ghi mức thứ hai vào đây", "tiến độ; phạt", "tạm giữ; chậm", 3,
     "chậm; tiến độ; tạm giữ", ""),
    ("TT-53", "Tiến độ - phạt", "Tạm giữ hoặc phạt chậm tiến độ giai đoạn - mức 2: mức THỨ HAI/cao hơn (%/ngày) áp dụng "
     "khi chậm lâu hơn (vd từ ngày thứ 08); thường nằm cùng câu với mức 1 — lấy phần sau. Nếu HĐ chỉ có MỘT mức thì "
     "ghi 'Không quy định'", "tiến độ; phạt", "tạm giữ; chậm", 3, "chậm; tiến độ; tạm giữ", ""),
    ("TT-54", "Tiến độ - phạt", "Phạt chậm hoàn thành TỔNG tiến độ của Bên B (%/ngày, tính trên giá trị nào). Không lấy "
     "phạt chậm quyết toán, không lấy lãi/phạt Bên A chậm thanh toán", "tiến độ; phạt", "tổng tiến độ; ngày chậm", 3,
     "chậm; tiến độ; hoàn thành", "chậm thanh toán; chậm quyết toán; lãi suất; bên a chậm"),
    ("TT-55", "Tiến độ - phạt", "Trần tổng mức phạt (% giá trị HĐ hoặc phần vi phạm). HĐ không ghi mức trần thì ghi "
     "'Không quy định'", "phạt", "tổng giá trị phạt; không quá", 3, "tổng; tối đa; không quá; không vượt", ""),
    ("TT-56", "Tiến độ - phạt", "Cách khấu trừ tiền phạt vào thanh toán", "phạt", "khấu trừ; trừ vào", 3,
     "khấu trừ; trừ", ""),
    ("TT-60", "Hồ sơ theo HĐ", "Hồ sơ thanh toán mỗi đợt (liệt kê, cách nhau bằng dấu ;)", "thanh toán", "hồ sơ thanh toán",
     2, "hồ sơ; biên bản; hoá đơn; hóa đơn", ""),
    ("TT-61", "Hồ sơ theo HĐ", "Hồ sơ quyết toán (liệt kê, cách nhau bằng dấu ;)", "quyết toán", "hồ sơ", 2,
     "hồ sơ; quyết toán", ""),
    ("TT-62", "Hồ sơ theo HĐ", "Số bộ hồ sơ thanh toán phải nộp", "thanh toán", "số lượng hồ sơ", 1, "bộ", ""),
]


def _split(s):
    return [x.strip().lower() for x in re.split(r"[;\n]", s or "") if x.strip()]


def _muc(v, ma=""):
    try:
        m = int(float(str(v).strip()))
        return min(3, max(0, m))
    except ValueError:
        return 0 if ma.startswith("TC-") else 2


def ten_ngan(mo_ta):
    return re.split(r"[(:;—]", mo_ta)[0].strip()[:60]


def to_param(ma, nhom, mo_ta, tk="", bk="", muc=None, bat_buoc="", loai_tru="", luon_cloud=False):
    """Một dòng danh mục → dict tham số dùng trong quy trình."""
    def kws(x):
        return _split(x) if isinstance(x, str) else [str(k).strip().lower() for k in (x or []) if str(k).strip()]
    ma = str(ma).strip()
    return {"ma": ma, "nhom": (nhom or "").strip() or "Khác", "mo_ta": str(mo_ta).strip(), "ten": ten_ngan(str(mo_ta)),
            "tieu_de_kws": kws(tk), "noi_dung_kws": kws(bk), "muc": _muc(muc if muc is not None else "", ma),
            "bat_buoc": kws(bat_buoc), "loai_tru": kws(loai_tru), "luon_cloud": bool(luon_cloud)}


def default_rows():
    return [{"ma": c, "nhom": g, "mo_ta": m, "tk": tk, "bk": bk, "dung": True, "muc": lv, "bat_buoc": bb, "loai_tru": lt,
             "luon_cloud": c in LUON_CLOUD_MAC_DINH} for c, g, m, tk, bk, lv, bb, lt in MAC_DINH]


def create_catalog(path=None):
    path = str(path or DANH_MUC_THAM_SO)
    _ghi(path, default_rows())
    return path


def _ghi(path, rows):
    data = [HEADER] + [[r["ma"], r["nhom"], r["mo_ta"], r["tk"], r["bk"], "Có" if r["dung"] else "Không", r["muc"],
                        r["bat_buoc"], r["loai_tru"], "Có" if r.get("luon_cloud") else "Không"] for r in rows]
    write_xlsx(path, {"Danh_muc": {"rows": data, "widths": DO_RONG}})


def read_catalog(path=None):
    """Toàn bộ danh mục (kể cả dòng Dùng = Không) → list dict theo KHOA. File cũ 6 cột vẫn đọc được."""
    path = str(path or DANH_MUC_THAM_SO)
    if not os.path.exists(path):
        create_catalog(path)
    rows = read_xlsx(path)
    if not rows:
        return []
    head = [str(h).strip().lower() for h in rows[0]]

    def idx(*names):
        for i, h in enumerate(head):
            if any(h.startswith(n) for n in names):
                return i
        return None
    pos = {"ma": idx("mã"), "nhom": idx("nhóm"), "mo_ta": idx("mô tả"), "tk": idx("từ khoá tiêu đề", "từ khóa tiêu đề"),
           "bk": idx("từ khoá nội dung", "từ khóa nội dung"), "dung": idx("dùng"), "muc": idx("mức"),
           "bat_buoc": idx("từ khoá bắt buộc", "từ khóa bắt buộc"), "loai_tru": idx("từ khoá loại trừ", "từ khóa loại trừ"),
           "luon_cloud": idx("luôn hỏi")}
    mac_dinh = {c: (lv, bb, lt) for c, _, _, _, _, lv, bb, lt in MAC_DINH}
    out = []
    for r in rows[1:]:
        g = lambda k: str(r[pos[k]]).strip() if pos[k] is not None and pos[k] < len(r) else ""  # noqa: E731
        ma, mo_ta = g("ma"), g("mo_ta")
        if not (ma or mo_ta):
            continue
        lv, bb, lt = mac_dinh.get(ma, (None, "", ""))
        out.append({"ma": ma, "nhom": g("nhom"), "mo_ta": mo_ta, "tk": g("tk"), "bk": g("bk"),
                    "dung": g("dung").lower() not in KHONG,
                    "muc": _muc(g("muc"), ma) if pos["muc"] is not None and g("muc") != "" else (lv if lv is not None else _muc("", ma)),
                    "bat_buoc": g("bat_buoc") if pos["bat_buoc"] is not None else bb,
                    "loai_tru": g("loai_tru") if pos["loai_tru"] is not None else lt,
                    "luon_cloud": (g("luon_cloud").lower() in ("có", "co", "x", "1", "yes", "true"))
                    if pos["luon_cloud"] is not None else ma in LUON_CLOUD_MAC_DINH})
    return out


def load_params(path=None, them=None):
    """Tham số đang dùng (theo thứ tự danh mục) + tham số hỏi thêm `them` (list mô tả hoặc 'Nhóm | Mô tả')."""
    params, seen = [], set()
    for r in read_catalog(path):
        if not r["ma"] or not r["mo_ta"] or not r["dung"] or r["ma"] in seen:
            continue
        seen.add(r["ma"])
        params.append(to_param(r["ma"], r["nhom"], r["mo_ta"], r["tk"], r["bk"], r["muc"], r["bat_buoc"], r["loai_tru"],
                               r["luon_cloud"]))
    n = 0
    for line in them or []:
        line = str(line).strip()
        if not line or line.startswith("#"):
            continue
        n += 1
        grp, desc = (x.strip() for x in line.split("|", 1)) if "|" in line else ("Yêu cầu thêm", line)
        params.append(to_param(f"Y-{n:02d}", grp, desc, muc=2))
    return params


def doc_yeu_cau_them(in_dir):
    p = os.path.join(in_dir, "YEU_CAU_THEM.txt") if in_dir else None
    if not p or not os.path.exists(p):
        return []
    with open(p, encoding="utf-8-sig") as fh:
        return fh.read().splitlines()


def save_catalog(rows, path=None):
    """Ghi lại danh mục từ list dict (sao lưu bản cũ vào danh_muc_sao_luu\\). Trả đường dẫn bản sao lưu."""
    path = str(path or DANH_MUC_THAM_SO)
    seen, clean = set(), []
    for r in rows:
        ma, mo_ta = str(r.get("ma", "")).strip(), str(r.get("mo_ta", "")).strip()
        if not ma or not mo_ta:
            raise ValueError(f"Dòng thiếu Mã hoặc Mô tả: {ma or mo_ta or '(trống)'}")
        if ma in seen:
            raise ValueError(f"Trùng mã tham số: {ma}")
        seen.add(ma)
        clean.append({"ma": ma, "nhom": str(r.get("nhom", "")).strip(), "mo_ta": mo_ta, "tk": str(r.get("tk", "")).strip(),
                      "bk": str(r.get("bk", "")).strip(), "dung": bool(r.get("dung", True)), "muc": _muc(r.get("muc", ""), ma),
                      "bat_buoc": str(r.get("bat_buoc", "")).strip(), "loai_tru": str(r.get("loai_tru", "")).strip(),
                      "luon_cloud": bool(r.get("luon_cloud"))})
    bak = None
    if os.path.exists(path):
        d = os.path.join(os.path.dirname(path), "danh_muc_sao_luu")
        os.makedirs(d, exist_ok=True)
        bak = os.path.join(d, f"DANH_MUC_THAM_SO_{datetime.datetime.now():%Y%m%d_%H%M%S}.xlsx")
        shutil.copy2(path, bak)
    _ghi(path, clean)
    return bak


if __name__ == "__main__":
    print("Đã tạo:", create_catalog())
