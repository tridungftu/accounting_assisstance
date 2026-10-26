"""Tra cứu thuần trên snapshot Sheet đã chuẩn hóa, không suy diễn từ hợp đồng."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import re
import unicodedata


_TRUONG = (
    ("du_no", ("du no", "so du"), "Dư nợ"),
    ("lai_suat_nam", ("lai suat",), "Lãi suất hiện hành"),
    ("ky_dieu_chinh_ke_tiep", ("ky dieu chinh",), "Kỳ điều chỉnh kế tiếp"),
    ("ngay_dao_han", ("dao han",), "Ngày đáo hạn"),
)
_DINH_DANH = ("ma_khoan_vay", "ngan_hang", "phap_nhan")
_NHAN = re.compile(
    r"(?<![\w./-])(?:(?P<ma_khoan_vay>ma khoan vay|ma khoan|khoan vay|khoan|ma)"
    r"|(?P<ngan_hang>ngan hang|nh)|(?P<phap_nhan>phap nhan))(?![\w./-])"
)
_DUNG = re.compile(
    r"(?<![\w./-])(?:la bao nhieu|bao nhieu|la gi|hien hanh|hien tai|hien nay|hom nay"
    r"|bay gio|dang|du no|so du|lai suat|ky dieu chinh|ngay dao han|dao han|cua|tai|thuoc)(?![\w./-])"
)
_HIEN_TAI = re.compile(
    r"(?<![\w./-])(?:hien nay|hien tai|hien hanh|bay gio|dang)(?![\w./-])"
)
# Chỉ khoản đánh số là dấu hiệu hợp đồng; mã như A, A-1 để bộ lọc snapshot xử lý.
_HOP_DONG = re.compile(
    r"(?<![\w./-])(?:theo hop dong|hop dong quy dinh|dieu khoan|quy dinh"
    r"|(?:dieu|khoan) \d+(?:[./]\d+)*)(?![\w./-])"
)


def _chuan(chu: str) -> str:
    chu = unicodedata.normalize("NFD", chu.casefold().replace("đ", "d"))
    chu = "".join(c for c in chu if unicodedata.category(c) != "Mn")
    # Giữ dấu bên trong mã: A không được khớp A-1, A/1 hay A.1.
    return " ".join(re.findall(r"\w+(?:[-./]\w+)*", chu))


def _mau(chu: str):
    return re.compile(r"(?<![\w./-])" + re.escape(chu) + r"(?![\w./-])")


def _bo_loc(cau: str, cac_khoan: list[dict]) -> dict[str, set[str]]:
    """Nhãn rõ mà giá trị lạ vẫn tạo bộ lọc rỗng, không trả nhầm mọi khoản."""
    gia_tri = {
        t: {_chuan(k[t]) for k in cac_khoan if isinstance(k.get(t), str) and k[t].strip()}
        for t in _DINH_DANH
    }
    loc = {}
    nhan = list(_NHAN.finditer(cau))
    con_lai = list(cau)
    for i, muc in enumerate(nhan):
        cuoi = nhan[i + 1].start() if i + 1 < len(nhan) else len(cau)
        sau = cau[muc.end():cuoi].strip()
        sau = _DUNG.split(sau, maxsplit=1)[0].strip()
        if not sau:  # Ví dụ: "dư nợ các khoản vay là bao nhiêu".
            continue
        truong = muc.lastgroup
        ung_vien = {sau, muc.group() + " " + sau}
        # Nhiều mã/tên cùng trường là phép OR; các trường khác nhau là AND.
        # Thử nguyên chuỗi trước để tên có chữ "và" không bị tách.
        if not gia_tri[truong] & ung_vien:
            ung_vien = {v.strip() for v in re.split(
                r"(?<![\w./-])(?:va|hoac)(?![\w./-])", sau,
            ) if v.strip()}
            ung_vien |= {muc.group() + " " + v for v in tuple(ung_vien)}
        loc.setdefault(truong, set()).update(gia_tri[truong] & ung_vien)
        het = cau.index(sau, muc.end(), cuoi) + len(sau)
        con_lai[muc.start():het] = " " * (het - muc.start())

    # Tên/mã được nêu trực tiếp cũng phải trùng nguyên chuỗi, có ranh giới.
    chu = "".join(con_lai)
    for truong in _DINH_DANH:
        if truong in loc:
            continue
        khop = [(m.start(), m.end(), v) for v in gia_tri[truong]
                for m in _mau(v).finditer(chu)]
        if khop:
            loc[truong] = {v for dau, cuoi, v in khop if not any(
                d <= dau and c >= cuoi and (d, c) != (dau, cuoi)
                for d, c, _ in khop
            )}
    # Mã lạ không có nhãn cũng phải tạo bộ lọc, không rơi về cả danh mục.
    # Loại tên ngân hàng/pháp nhân đã biết trước khi nhận diện token giống mã.
    chu_ma = chu
    for truong in ("ngan_hang", "phap_nhan"):
        for ten in sorted(gia_tri[truong], key=len, reverse=True):
            chu_ma = _mau(ten).sub(" ", chu_ma)
    ma_truc_tiep = {tu for tu in chu_ma.split()
                   if re.search(r"[a-z]", tu) and re.search(r"[\d./-]", tu)}
    if ma_truc_tiep:
        loc.setdefault("ma_khoan_vay", set()).update(
            gia_tri["ma_khoan_vay"] & ma_truc_tiep,
        )
    return loc


def _kiem_snapshot(snapshot: dict) -> None:
    if snapshot.get("nguon") != "Sheet":
        raise ValueError("Chỉ nhận snapshot nguồn Sheet có mốc.")
    moc = snapshot.get("moc")
    try:
        if not isinstance(moc, str):
            raise ValueError
        if datetime.strptime(moc, "%d/%m/%Y %H:%M").strftime("%d/%m/%Y %H:%M") != moc:
            raise ValueError
    except ValueError:
        raise ValueError("Mốc snapshot phải có dạng dd/mm/yyyy hh:mm.") from None
    if (not isinstance(snapshot.get("khoan_vay"), list)
            or any(not isinstance(k, dict) for k in snapshot["khoan_vay"])):
        raise ValueError("Thiếu danh sách khoản vay đã chuẩn hóa.")


def _gia_tri(khoan: dict, truong: str) -> tuple:
    gia_tri = khoan.get(truong)
    if truong in ("du_no", "lai_suat_nam"):
        don_vi = khoan.get("tien_te") if truong == "du_no" else "%/năm"
        if (not isinstance(don_vi, str) or not don_vi.strip()
                or not isinstance(gia_tri, Decimal) or not gia_tri.is_finite()):
            return None, don_vi, "Chưa có dữ liệu hợp lệ trong snapshot"
        chu = format(gia_tri, "f").replace(".", ",")
        return gia_tri, don_vi, chu + " " + don_vi
    if type(gia_tri) is not date:
        return None, "ngày", "Chưa có dữ liệu hợp lệ trong snapshot"
    return gia_tri, "ngày", gia_tri.strftime("%d/%m/%Y")


def tra_so_du(cau_hoi: str, snapshot: dict) -> dict | None:
    """Trả số liệu gốc Decimal/date, liệt kê từng khoản, không tính lãi/tổng.

    Snapshot phải là đầu ra lap_snapshot (Sheet, mốc và các dòng chuẩn hóa).
    Thiếu số/ngày/đồng tiền thì báo thiếu; không chuyển float hay suy đoán.
    Lãi suất cần từ chỉ hiện tại hoặc định danh khớp snapshot.
    Dấu hiệu hợp đồng tường minh luôn trả None để tầng gọi xử lý hợp đồng.
    """
    cau = _chuan(cau_hoi)
    if _HOP_DONG.search(cau):
        return None
    truong_hoi = [(t, nhan) for t, tu_khoa, nhan in _TRUONG
                  if any(_mau(tu).search(cau) for tu in tu_khoa)]
    if not truong_hoi:
        return None
    _kiem_snapshot(snapshot)
    loc = _bo_loc(cau, snapshot["khoan_vay"])
    cac_khoan = [k for k in snapshot["khoan_vay"] if all(
        isinstance(k.get(t), str) and _chuan(k[t]) in ds for t, ds in loc.items()
    )]
    if not _HIEN_TAI.search(cau) and not (loc and cac_khoan):
        truong_hoi = [(t, nhan) for t, nhan in truong_hoi if t != "lai_suat_nam"]
        if not truong_hoi:
            return None
    dong = []
    cau_tra_loi = []
    for khoan in cac_khoan:
        dinh_danh = {t: khoan.get(t) for t in _DINH_DANH}
        ten = " / ".join(str(v) for v in dinh_danh.values() if v) or "Khoản vay chưa có mã"
        noi_dung = []
        for truong, nhan in truong_hoi:
            gia_tri, don_vi, chu = _gia_tri(khoan, truong)
            dong.append({**dinh_danh, "truong": truong,
                         "gia_tri": gia_tri, "don_vi": don_vi})
            noi_dung.append(nhan + ": " + chu)
        cau_tra_loi.append(ten + " — " + "; ".join(noi_dung))
    return {
        "trang_thai": "TU_SNAPSHOT" if cac_khoan else "KHONG_THAY_TRONG_SNAPSHOT",
        "tra_loi": ("\n".join(cau_tra_loi) if cac_khoan else "Không thấy khoản vay trong snapshot.")
                   + " (nguồn Sheet, mốc " + snapshot["moc"] + ")",
        "dong": dong, "nguon": "Sheet", "moc": snapshot["moc"],
    }
