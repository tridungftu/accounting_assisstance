"""M10 · Định kỳ & đóng sổ: lịch tham chiếu, chỉ để kiểm chéo Junsky.

Không tạo bút toán, không xuất sang Junsky, không chọn bên thắng khi lệch.
Policy phải được hiệu chuẩn K0; module không chọn mặc định A/B.

Quy ước cần kiểm với K0: ngày đầu/cuối đều tính; THEO_NGAY dùng số ngày
thực tế / số ngày lịch của tháng. B bắt đầu tại max(bàn giao, ghi 3387).
A catch-up bằng tổng các kỳ đã làm tròn tới tháng ghi. Chấm dứt không đổi
mẫu số ban đầu; tháng chấm dứt áp dụng quy tắc tháng lẻ cuối. Chỉ dồn phần
lẻ ở tháng kết thúc thuê gốc, không tất toán số dư khi chấm dứt sớm.
Nếu không dồn phần lẻ, giữ nguyên số dư (kể cả chênh do làm tròn), không
tự xóa chênh lệch. Không chấp nhận đợt ghi sau kết thúc/chấm dứt.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Context, Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP, localcontext
from hashlib import sha256
import json


def _chuoi(value: object, ten: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{ten} phải là chuỗi không rỗng")


def _ngay(value: object, ten: str) -> None:
    if type(value) is not date:
        raise TypeError(f"{ten} phải là date")


@dataclass(frozen=True)
class HopDong:
    ma_hop_dong: str
    phien_ban: str
    ngay_ban_giao: date
    ngay_ket_thuc_thue: date
    currency: str
    ngay_cham_dut: date | None = None

    def __post_init__(self) -> None:
        for ten in ("ma_hop_dong", "phien_ban", "currency"):
            _chuoi(getattr(self, ten), ten)
        _ngay(self.ngay_ban_giao, "ngay_ban_giao")
        _ngay(self.ngay_ket_thuc_thue, "ngay_ket_thuc_thue")
        if self.ngay_ket_thuc_thue < self.ngay_ban_giao:
            raise ValueError("ngay_ket_thuc_thue phải từ ngày bàn giao trở đi")
        if self.ngay_cham_dut is not None:
            _ngay(self.ngay_cham_dut, "ngay_cham_dut")
            if not self.ngay_ban_giao <= self.ngay_cham_dut <= self.ngay_ket_thuc_thue:
                raise ValueError("ngay_cham_dut phải nằm trong thời hạn thuê")


@dataclass(frozen=True)
class DotThu:
    ma_dot: str
    gia_tri_truoc_vat: Decimal
    ngay_ghi_3387: date

    def __post_init__(self) -> None:
        _chuoi(self.ma_dot, "ma_dot")
        _ngay(self.ngay_ghi_3387, "ngay_ghi_3387")
        if not isinstance(self.gia_tri_truoc_vat, Decimal):
            raise TypeError("gia_tri_truoc_vat phải là Decimal; không nhận float")
        if not self.gia_tri_truoc_vat.is_finite() or self.gia_tri_truoc_vat < 0:
            raise ValueError("gia_tri_truoc_vat phải hữu hạn và không âm")


@dataclass(frozen=True)
class QuyTacLamTron:
    so_chu_so: int
    kieu_lam_tron: str
    don_phan_le_ky_cuoi: bool

    def __post_init__(self) -> None:
        if type(self.so_chu_so) is not int or self.so_chu_so < 0:
            raise ValueError("so_chu_so phải là số nguyên không âm")
        if self.kieu_lam_tron not in (ROUND_HALF_UP, ROUND_HALF_EVEN):
            raise ValueError("kieu_lam_tron phải là ROUND_HALF_UP hoặc ROUND_HALF_EVEN")
        if type(self.don_phan_le_ky_cuoi) is not bool:
            raise TypeError("don_phan_le_ky_cuoi phải là bool, cần chọn rõ")


@dataclass(frozen=True)
class Policy:
    phuong_phap: str
    don_vi_ky: str
    thang_le_dau: str
    thang_le_cuoi: str
    lam_tron: QuyTacLamTron

    def __post_init__(self) -> None:
        if self.phuong_phap not in ("A", "B"):
            raise ValueError("Thiếu/sai phuong_phap: phải chọn A hoặc B sau hiệu chuẩn K0")
        if self.don_vi_ky != "THANG":
            raise ValueError("don_vi_ky bắt buộc là THANG")
        for ten in ("thang_le_dau", "thang_le_cuoi"):
            if getattr(self, ten) not in ("TRON_THANG", "THEO_NGAY"):
                raise ValueError(f"{ten} bắt buộc là TRON_THANG hoặc THEO_NGAY")
        if not isinstance(self.lam_tron, QuyTacLamTron):
            raise ValueError("Thiếu/sai quy tắc lam_tron; không có mặc định")


@dataclass(frozen=True)
class DongLich:
    nam: int
    thang: int
    doanh_thu_ky: Decimal
    luy_ke: Decimal
    so_du_3387_cuoi_ky: Decimal

    @property
    def ky(self) -> str:
        return f"{self.nam:04d}-{self.thang:02d}"


@dataclass(frozen=True)
class LichDotThu:
    ma_dot: str
    cac_ky: tuple[DongLich, ...]
    so_du_3387_con_lai: Decimal


@dataclass(frozen=True)
class LichPhanBo:
    ma_hop_dong: str
    phien_ban: str
    currency: str
    hash_dau_vao: str
    lich_tung_dot: tuple[LichDotThu, ...]
    tong_hop_dong: tuple[DongLich, ...]
    so_du_3387_con_lai: Decimal


def _chi_so_thang(ngay: date) -> int:
    return (ngay.year - 1) * 12 + ngay.month - 1


def _nam_thang(chi_so: int) -> tuple[int, int]:
    nam, thang = divmod(chi_so, 12)
    return nam + 1, thang + 1


# Bội chung nhỏ nhất của 28, 29, 30, 31: trọng số nguyên, tránh xấp xỉ
# 1/29 hay 1/31 trước khi tính tiền Decimal.
_TRONG_SO_THANG = 377580


def _trong_so(ky: int, dau: date, cuoi: date, policy: Policy) -> int:
    nam, thang = _nam_thang(ky)
    so_ngay = monthrange(nam, thang)[1]
    ngay_dau = dau.day if ky == _chi_so_thang(dau) and policy.thang_le_dau == "THEO_NGAY" else 1
    ngay_cuoi = cuoi.day if ky == _chi_so_thang(cuoi) and policy.thang_le_cuoi == "THEO_NGAY" else so_ngay
    return (ngay_cuoi - ngay_dau + 1) * (_TRONG_SO_THANG // so_ngay)


def _hash_dau_vao(hop_dong: HopDong, cac_dot: tuple[DotThu, ...], policy: Policy) -> str:
    def chuyen(value: object) -> str:
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        raise TypeError(f"Không thể mã hóa {type(value).__name__}")

    du_lieu = {"schema": "M10-1a-v1", "hop_dong": asdict(hop_dong),
               "cac_dot": [asdict(dot) for dot in cac_dot], "policy": asdict(policy)}
    noi_dung = json.dumps(du_lieu, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), default=chuyen)
    return sha256(noi_dung.encode("utf-8")).hexdigest()


def tinh_lich_phan_bo(
    hop_dong: HopDong, cac_dot_thu: tuple[DotThu, ...], policy: Policy
) -> LichPhanBo:
    """Tính lịch tham chiếu bất biến; không I/O, không thay đổi đầu vào.

    Tổng 3387 theo kỳ chỉ gồm các đợt đã ghi tới kỳ đó. Đợt ghi trước bàn
    giao bắt đầu hiển thị ở kỳ bàn giao. Dồn phần lẻ có thể tạo dòng kỳ
    cuối khác mức thường (kể cả âm nếu policy làm tròn quá thô); giữ đúng
    policy để kiểm chéo, không tự sửa/đặt dung sai.
    """
    if not isinstance(hop_dong, HopDong) or not isinstance(policy, Policy):
        raise TypeError("Cần HopDong và Policy đầy đủ")
    if not isinstance(cac_dot_thu, tuple) or not cac_dot_thu:
        raise ValueError("cac_dot_thu phải là tuple bất biến, có ít nhất một đợt")
    if any(not isinstance(dot, DotThu) for dot in cac_dot_thu):
        raise TypeError("Mọi đợt phải là DotThu")
    if len({dot.ma_dot for dot in cac_dot_thu}) != len(cac_dot_thu):
        raise ValueError("ma_dot không được trùng trong một hợp đồng/phiên bản")
    ngay_dung = hop_dong.ngay_cham_dut or hop_dong.ngay_ket_thuc_thue
    if any(dot.ngay_ghi_3387 > ngay_dung for dot in cac_dot_thu):
        raise ValueError("ngay_ghi_3387 không được sau ngày kết thúc thuê/chấm dứt")

    # Đủ chữ số cho cả phần nguyên, phần lẻ, tích trọng số và cộng dồn;
    # không phụ thuộc precision/traps của Decimal context phía gọi.
    do_lon = max(len(dot.gia_tri_truoc_vat.as_tuple().digits)
                 + abs(dot.gia_tri_truoc_vat.as_tuple().exponent) for dot in cac_dot_thu)
    precision = do_lon + policy.lam_tron.so_chu_so + len(str(len(cac_dot_thu))) + 40
    with localcontext(Context(prec=precision)):
        return _tinh(hop_dong, cac_dot_thu, policy, ngay_dung)


def _tinh(hop_dong: HopDong, cac_dot: tuple[DotThu, ...], policy: Policy,
          ngay_dung: date) -> LichPhanBo:
    dau = _chi_so_thang(hop_dong.ngay_ban_giao)
    cuoi = _chi_so_thang(hop_dong.ngay_ket_thuc_thue)
    dung = _chi_so_thang(ngay_dung)
    luong_tu = Decimal(1).scaleb(-policy.lam_tron.so_chu_so)
    lich_dot = []
    doanh_thu = {ky: Decimal(0) for ky in range(dau, dung + 1)}

    for dot in cac_dot:
        ngay_dau = (hop_dong.ngay_ban_giao if policy.phuong_phap == "A"
                    else max(hop_dong.ngay_ban_giao, dot.ngay_ghi_3387))
        ky_dau = _chi_so_thang(ngay_dau)
        ky_ghi = max(dau, _chi_so_thang(dot.ngay_ghi_3387))
        mau_so = sum(_trong_so(ky, ngay_dau, hop_dong.ngay_ket_thuc_thue, policy)
                     for ky in range(ky_dau, cuoi + 1))
        cac_ky = []
        luy_ke = Decimal(0)
        catch_up = Decimal(0)
        for ky in range(ky_dau, dung + 1):
            trong_so = _trong_so(ky, ngay_dau, ngay_dung, policy)
            tien = (dot.gia_tri_truoc_vat * trong_so / mau_so).quantize(
                luong_tu, rounding=policy.lam_tron.kieu_lam_tron)
            if ky < ky_ghi:
                catch_up += tien
                continue
            if ky == ky_ghi:
                tien += catch_up
            if ky == cuoi and ngay_dung == hop_dong.ngay_ket_thuc_thue and policy.lam_tron.don_phan_le_ky_cuoi:
                tien = dot.gia_tri_truoc_vat - luy_ke
            luy_ke += tien
            doanh_thu[ky] += tien
            nam, thang = _nam_thang(ky)
            cac_ky.append(DongLich(nam, thang, tien, luy_ke, dot.gia_tri_truoc_vat - luy_ke))
        lich_dot.append(LichDotThu(dot.ma_dot, tuple(cac_ky), dot.gia_tri_truoc_vat - luy_ke))

    tong = []
    luy_ke = Decimal(0)
    for ky, tien in doanh_thu.items():
        luy_ke += tien
        da_ghi = sum((dot.gia_tri_truoc_vat for dot in cac_dot
                      if _chi_so_thang(dot.ngay_ghi_3387) <= ky), Decimal(0))
        nam, thang = _nam_thang(ky)
        tong.append(DongLich(nam, thang, tien, luy_ke, da_ghi - luy_ke))
    return LichPhanBo(hop_dong.ma_hop_dong, hop_dong.phien_ban, hop_dong.currency,
                     _hash_dau_vao(hop_dong, cac_dot, policy), tuple(lich_dot), tuple(tong),
                     tong[-1].so_du_3387_cuoi_ky)
