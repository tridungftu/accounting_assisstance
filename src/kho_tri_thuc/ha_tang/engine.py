"""XS-3A / CD-017: hợp đồng engine thuần Python theo TL 53.

Engine KHÔNG đọc/ghi bảng của module. Mọi đầu vào (snapshot, bytes đã được
cấp quyền) đi qua tham số; module gọi tự lưu đầu ra. Chưa bọc engine thật.
Subclass khai báo kiểu vào/ra và cài ``xu_ly``; caller dùng ``chay`` để nhận
kết quả có bằng chứng. CHO là kết quả hợp lệ, không phải ngoại lệ.
Lỗi lập trình/vi phạm hợp đồng vẫn nổi lên, không tự đổi thành lỗi nghiệp vụ.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
import math
import re
from typing import Any


class TrangThaiEngine(str, Enum):
    XONG = "XONG"
    CHO = "CHO"
    LOI = "LOI"


def _chuoi(value: str, ten: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{ten} phải là chuỗi không rỗng, không có khoảng trắng ngoài.")


@dataclass(frozen=True)
class KhaiBaoEngine:
    """Kiểu vào/ra là lớp Python cụ thể, không phải typing.Any/GenericAlias.

    Adapter chịu trách nhiệm chuyển đổi dữ liệu qua API thành đúng kiểu này.
    Mã và phiên bản là định danh nguyên văn, không suy đoán thứ tự semver.
    """

    ma: str
    phien_ban: str
    dau_vao: type
    dau_ra: type

    def __post_init__(self) -> None:
        _chuoi(self.ma, "Mã engine")
        _chuoi(self.phien_ban, "Phiên bản engine")
        for kieu in (self.dau_vao, self.dau_ra):
            if not isinstance(kieu, type) or kieu is Any:
                raise ValueError("Khai báo vào/ra phải là lớp Python cụ thể.")


@dataclass(frozen=True)
class KetQuaXuLy:
    """Kết quả nghiệp vụ; mọi trạng thái đều có mã và lý do tiếng Việt trung tính.

    CHO/LOI được phép không có dữ liệu; nếu có vẫn phải đúng kiểu đầu ra.
    Không đưa traceback hoặc nội dung nhạy cảm vào lý do hiển thị.
    """

    trang_thai: TrangThaiEngine
    ma: str
    ly_do: str
    du_lieu: Any = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "trang_thai", TrangThaiEngine(self.trang_thai))
        if not isinstance(self.ma, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", self.ma):
            raise ValueError("Mã lý do phải là mã chữ hoa, số hoặc dấu gạch dưới.")
        _chuoi(self.ly_do, "Lý do")


@dataclass(frozen=True)
class BangChungEngine:
    hash_vao: str
    hash_ra: str
    ma_engine: str
    phien_ban_engine: str
    thoi_diem: datetime


@dataclass(frozen=True)
class KetQuaEngine(KetQuaXuLy):
    # kw_only giữ trường bắt buộc dù du_lieu của lớp cha có mặc định.
    bang_chung: BangChungEngine = field(kw_only=True)


def _chuan_hoa(value: Any) -> Any:
    """Cây có nhãn kiểu để hash không lẫn bytes với chuỗi/list với tuple.

    Chỉ nhận dữ liệu thuần: JSON hữu hạn, bytes, Decimal hữu hạn, ngày/giờ,
    dataclass. Dict chỉ nhận khóa str; không dùng repr/default=str vì có thể
    mất thông tin hoặc phụ thuộc địa chỉ bộ nhớ. Không đọc file để tính hash.
    """
    if value is None:
        return ["none"]
    if type(value) in (bool, int, str):
        return [type(value).__name__, value]
    if type(value) is float and math.isfinite(value):
        return ["float", value]
    if type(value) is bytes:
        return ["bytes", value.hex()]
    if isinstance(value, Decimal) and value.is_finite():
        return ["decimal", str(value)]
    if isinstance(value, datetime):
        return ["datetime", value.isoformat()]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if is_dataclass(value) and not isinstance(value, type):
        return ["dataclass", type(value).__module__, type(value).__qualname__,
                [[f.name, _chuan_hoa(getattr(value, f.name))] for f in fields(value)]]
    if type(value) in (list, tuple):
        return [type(value).__name__, [_chuan_hoa(v) for v in value]]
    if type(value) is dict and all(type(k) is str for k in value):
        return ["dict", [[k, _chuan_hoa(value[k])] for k in sorted(value)]]
    raise ValueError("Dữ liệu tính hash không thuộc các kiểu thuần được hỗ trợ.")


def hash_du_lieu(value: Any) -> str:
    """SHA-256 UTF-8: ổn định theo nội dung/kiểu, độc lập thứ tự khóa dict.

    Decimal giữ nguyên độ chính xác/thang số; datetime giữ nguyên offset.
    Dữ liệu phải không có tham chiếu vòng. Cùng nội dung, kiểu và engine
    version cho cùng hash; thời điểm thực thi không tham gia hash vào/ra.
    """
    raw = json.dumps(_chuan_hoa(value), ensure_ascii=False, allow_nan=False,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class Engine(ABC):
    """Lõi tái dùng, không kết nối CSDL hay đọc/ghi bảng của module.

    ``xu_ly`` không được sửa đầu vào. Hash đầu ra gồm cả trạng thái/mã/lý do
    và dữ liệu, do đó bằng chứng phân biệt XONG/CHO/LOI cùng dữ liệu None.
    ``thoi_diem`` có timezone được phép truyền để chạy mẫu tái lập; mặc định
    lấy UTC sau khi xử lý. Không bắt ngoại lệ để che lỗi lập trình.
    """

    def __init__(self, khai_bao: KhaiBaoEngine) -> None:
        if not isinstance(khai_bao, KhaiBaoEngine):
            raise ValueError("Engine phải có khai báo hợp lệ.")
        self._khai_bao = khai_bao

    @property
    def khai_bao(self) -> KhaiBaoEngine:
        return self._khai_bao

    @property
    def ma(self) -> str:
        return self.khai_bao.ma

    @property
    def phien_ban(self) -> str:
        return self.khai_bao.phien_ban

    @abstractmethod
    def xu_ly(self, dau_vao: Any) -> KetQuaXuLy:
        """Nhận tham số, trả dữ liệu và trạng thái có mã/lý do tiếng Việt."""
        raise NotImplementedError

    def chay(self, dau_vao: Any, *, thoi_diem: datetime | None = None) -> KetQuaEngine:
        if not isinstance(dau_vao, self.khai_bao.dau_vao):
            raise ValueError("Đầu vào không đúng kiểu đã khai báo.")
        if thoi_diem is not None and (
            not isinstance(thoi_diem, datetime) or thoi_diem.utcoffset() is None
        ):
            raise ValueError("Thời điểm bằng chứng phải có timezone.")
        hash_vao = hash_du_lieu(dau_vao)
        ket_qua = self.xu_ly(dau_vao)
        if not isinstance(ket_qua, KetQuaXuLy):
            raise ValueError("Engine phải trả KetQuaXuLy.")
        if hash_du_lieu(dau_vao) != hash_vao:
            raise ValueError("Engine không được sửa đầu vào.")
        if (ket_qua.trang_thai == TrangThaiEngine.XONG or ket_qua.du_lieu is not None):
            if not isinstance(ket_qua.du_lieu, self.khai_bao.dau_ra):
                raise ValueError("Đầu ra không đúng kiểu đã khai báo.")
        hash_ra = hash_du_lieu({
            "trang_thai": ket_qua.trang_thai.value, "ma": ket_qua.ma,
            "ly_do": ket_qua.ly_do, "du_lieu": ket_qua.du_lieu,
        })
        bang_chung = BangChungEngine(
            hash_vao, hash_ra, self.ma, self.phien_ban,
            (thoi_diem if thoi_diem is not None else datetime.now(timezone.utc))
            .astimezone(timezone.utc),
        )
        return KetQuaEngine(ket_qua.trang_thai, ket_qua.ma, ket_qua.ly_do,
                           ket_qua.du_lieu, bang_chung=bang_chung)
