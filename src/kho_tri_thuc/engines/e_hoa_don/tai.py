"""HD-2a: tải qua portal GIẢ, không mạng, Chromium, mật khẩu hoặc I/O.

CD-036 — dùng lại nguyên: doc.doc_xml (HD-1); bọc: kỳ tháng/năm của
H/src/job.js:55, trạng thái nhóm của H/src/portal.js:223; viết mới: seam
giả và giữ kết quả chờ ACK. Chỉ đối chiếu nguồn, không chép/sửa thuật toán
tải. Nguồn thật nuốt lỗi nhóm nên chưa chứng minh coverage cho tải thật.

Các dataclass là DTO nội bộ trong RAM, không phải contract JSON mới, đặc
biệt không phải báo cáo ZIP. Core giả cấp tham chiếu, lưu XML + JSON chi
tiết nguồn + hoa_don.v1 và chống trùng cùng ACK. IPC/SDK/Windows Job thuộc
HD-3a; profile/ACL/bí mật thật thuộc HD-2c/3b, không công bố capability.
Trạng thái này không bền qua restart: Core phải giữ việc interrupted và
đối chiếu trước khi tạo phiên mới, không tự tải lại từ trạng thái RAM mất.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date
from threading import Lock
from typing import Protocol
from uuid import uuid4

from . import doc
from ...ha_tang.primitives import DataError, date_iso, sha256, text_id
from ...nguon.hoa_don_xml import InvoiceReadContext


@dataclass(frozen=True)
class KyThang:
    nam: int
    thang: int

    @property
    def tu_ngay(self) -> str:
        return f"{self.nam:04d}-{self.thang:02d}-01"

    @property
    def den_ngay(self) -> str:
        return f"{self.nam:04d}-{self.thang:02d}-{monthrange(self.nam, self.thang)[1]:02d}"


def chia_ky(tu_ngay: str, den_ngay: str) -> tuple[KyThang, ...]:
    """Chỉ nhận các tháng liên tiếp nguyên vẹn, không tự nới kỳ."""
    dau = date.fromisoformat(date_iso(tu_ngay))
    cuoi = date.fromisoformat(date_iso(den_ngay))
    if (dau > cuoi or dau.day != 1
            or cuoi.day != monthrange(cuoi.year, cuoi.month)[1]):
        raise DataError("HOADON_KY_KHONG_TRON_THANG", "Kỳ tải phải gồm trọn tháng.")
    result = []
    nam, thang = dau.year, dau.month
    while (nam, thang) <= (cuoi.year, cuoi.month):
        result.append(KyThang(nam, thang))
        nam, thang = (nam + 1, 1) if thang == 12 else (nam, thang + 1)
    return tuple(result)


@dataclass(frozen=True)
class PhienGia:
    phap_nhan_id: str
    nguon_id: str
    phien_id: str = field(default_factory=lambda: str(uuid4()))
    profile_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class TepTai:
    raw: bytes = field(repr=False)
    context: InvoiceReadContext | None = field(default=None, repr=False)


@dataclass(frozen=True)
class NhomTai:
    """Giữ tệp đã nhận cả khi nhóm chỉ tải được một phần."""
    tep: tuple[TepTai, ...] = ()
    day_du: bool = True


@dataclass(frozen=True)
class Coverage:
    ky: KyThang
    nhom: str
    trang_thai: str
    so_tep_nhan: int
    ma_loi: str | None = None


@dataclass(frozen=True)
class ThamChieu:
    tep_xml_id: str
    chi_tiet_nguon_tep_id: str


class PortalGia(Protocol):
    """Seam test; không có backend thật hay lựa chọn mặc định mở mạng."""
    def nhom_truy_van(self, huong: str) -> tuple[str, ...]: ...
    def da_dang_nhap(self, phien: PhienGia) -> bool: ...
    def tai_nhom(self, phien: PhienGia, ky: KyThang,
                 huong: str, nhom: str) -> NhomTai: ...


class CoreGia(Protocol):
    """Seam bàn giao giả, không thay SDKEngine hay tạo giao thức IPC.

    cap_tham_chieu phải trả cùng ID theo (phien, khoa) khi gọi lại.
    nhan_hoa_don lưu đủ bytes/chi tiết nguồn/contract và biên nhận trước
    khi trả True; ACK lặp cũng trả True nếu biên nhận đã tồn tại. Core
    phải kiểm phạm vi phiên/pháp nhân ở mỗi lời gọi. Không ACK giả chỉ vì
    đã nhận lời gọi. nhan_phien lưu coverage riêng, không xác nhận thuế.
    """
    def cap_tham_chieu(self, phien: PhienGia, khoa: str) -> ThamChieu: ...
    def nhan_hoa_don(self, phien: PhienGia, khoa: str,
                     ket_qua: doc.KetQuaDocHoaDon) -> bool: ...
    def nhan_phien(self, phien: PhienGia, coverage: tuple[Coverage, ...],
                   ket_luan: str) -> bool: ...


@dataclass(frozen=True)
class TienDo:
    trang_thai_viec: str
    ket_luan_tai: str | None
    coverage: tuple[Coverage, ...]
    so_tep_duy_nhat: int
    so_tep_da_ack: int
    da_ack_phien: bool


class TaiHoaDonGia:
    """Một phiên giả tuần tự; retry bàn giao không lặp truy vấn/tải.

    Core đã kiểm nguon_id thuộc phap_nhan_id trước khởi tạo. Dedupe bytes
    chỉ trong phiên này; không gộp khác pháp nhân, không chọn bản thắng
    khi cùng định danh hóa đơn có nội dung khác. Không giữ sổ nghiệp vụ.
    """

    def __init__(self, *, phap_nhan_id: str, nguon_id: str, tu_ngay: str,
                 den_ngay: str, huong: str, portal: PortalGia):
        self._ky = chia_ky(tu_ngay, den_ngay)
        if huong not in ("mua_vao", "ban_ra"):
            raise DataError("HOADON_HUONG_INVALID", "Hướng phải là mua_vao hoặc ban_ra.")
        self.phien = PhienGia(text_id(phap_nhan_id), text_id(nguon_id))
        self._portal, self._huong = portal, huong
        nhom = portal.nhom_truy_van(huong)
        if (not isinstance(nhom, tuple) or not nhom
                or any(not isinstance(n, str) or not n.strip() for n in nhom)
                or len(set(nhom)) != len(nhom)):
            raise DataError("HOADON_COVERAGE_THIEU", "Portal giả cần danh sách nhóm đầy đủ, duy nhất.")
        self._nhom = nhom
        self._coverage: list[Coverage] = []
        self._tep: dict[str, TepTai] = {}
        self._doc: dict[str, doc.KetQuaDocHoaDon] = {}
        self._ack: set[str] = set()
        self._da_tai = False
        self._ack_phien = False
        self._trang_thai = "running"
        self._ket_luan: str | None = None
        self._khoa = Lock()

    def _tien_do(self) -> TienDo:
        return TienDo(self._trang_thai, self._ket_luan, tuple(self._coverage),
                      len(self._tep), len(self._ack), self._ack_phien)

    def tiep_tuc(self) -> TienDo:
        """Poll đăng nhập giả; không block/sleep, không nhận credential."""
        with self._khoa:
            if self._da_tai or self._trang_thai == "interrupted":
                return self._tien_do()
            if self._portal.da_dang_nhap(self.phien) is not True:
                self._trang_thai = "waiting_input"
                return self._tien_do()
            self._trang_thai = "running"
            for ky in self._ky:
                for nhom in self._nhom:
                    try:
                        result = self._portal.tai_nhom(self.phien, ky, self._huong, nhom)
                    except Exception:
                        # Không phản chiếu lỗi portal vào log/kết quả.
                        self._coverage.append(Coverage(ky, nhom, "FAILED", 0,
                                                       "HOADON_NHOM_LOI"))
                        continue
                    except BaseException:
                        # Ngắt phiên khác lỗi nhóm: không biết tác động của
                        # truy vấn đang chạy, phải để Core đối chiếu.
                        self._trang_thai = "interrupted"
                        raise
                    if (not isinstance(result, NhomTai) or type(result.day_du) is not bool
                            or not isinstance(result.tep, tuple)
                            or any(not isinstance(t, TepTai) or not isinstance(t.raw, bytes)
                                   for t in result.tep)):
                        self._coverage.append(Coverage(ky, nhom, "FAILED", 0,
                                                       "HOADON_NHOM_SAI_DINH_DANG"))
                        continue
                    for tep in result.tep:
                        # Không dedupe theo số hóa đơn hoặc semantic hash:
                        # cùng định danh nhưng XML khác vẫn giữ cả hai bản.
                        self._tep.setdefault(sha256(tep.raw), tep)
                    self._coverage.append(Coverage(
                        ky, nhom, "COMPLETE" if result.day_du else "PARTIAL",
                        len(result.tep), None if result.day_du else "HOADON_NHOM_CHUA_DU"))
            self._da_tai = True
            self._ket_luan = ("COMPLETE" if all(c.trang_thai == "COMPLETE"
                                              for c in self._coverage) else "PARTIAL")
            return self._tien_do()

    def ban_giao(self, core: CoreGia) -> TienDo:
        """Một lượt thử ACK; giữ nguyên tệp/kết quả khi lỗi hay mất ACK.

        Không bắt lease/IPC ở đây. Seam Core giả lỗi sẽ nổi lên cho caller;
        gọi lại ban_giao an toàn theo cùng khóa, không gọi lại portal.
        COMPLETE chỉ là coverage portal giả, khác trạng thái đọc từng XML.
        """
        with self._khoa:
            if not self._da_tai:
                raise DataError("HOADON_CHUA_TAI", "Chưa kết thúc lượt tải giả.")
            if self._ack_phien:
                return self._tien_do()
            for khoa, tep in self._tep.items():
                if khoa in self._ack:
                    continue
                if khoa not in self._doc:
                    ref = core.cap_tham_chieu(self.phien, khoa)
                    self._doc[khoa] = doc.doc_xml(
                        tep.raw, tep.context, tep_xml_id=ref.tep_xml_id,
                        chi_tiet_nguon_tep_id=ref.chi_tiet_nguon_tep_id)
                if core.nhan_hoa_don(self.phien, khoa, self._doc[khoa]) is not True:
                    return self._tien_do()
                self._ack.add(khoa)
            if core.nhan_phien(self.phien, tuple(self._coverage), self._ket_luan) is True:
                self._ack_phien = True
                self._trang_thai = "succeeded" if self._ket_luan == "COMPLETE" else "failed"
            return self._tien_do()
