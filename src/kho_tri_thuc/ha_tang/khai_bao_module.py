"""XS-4A / CD-017: dữ liệu khai báo module, chưa nối SQL, HTTP hay UI.

Mã phần duy nhất trong module; mã thẻ duy nhất trong từng nhóm vai (CRM
dùng lại cùng thẻ ở nhiều vai). Thứ tự khai báo được giữ, không tự sắp xếp
theo ``thu_tu``. Quyền/hành động là metadata, không tự cấp quyền.
Module mới mặc định TAT; CRM đang chạy chuyển từ tam_dung=False thành
VAN_HANH chỉ ở metadata, không bật công tắc hay đăng ký module thật.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
import warnings
from typing import Any

from .danh_ba_engine import DanhBaEngine


HANH_DONG = frozenset({"XEM", "LAP", "SUA", "KIEM", "DUYET", "HUY"})


class CheDoModule(str, Enum):
    TAT = "TAT"
    THU = "THU"
    VAN_HANH = "VAN_HANH"


def _chuoi(value: str, ten: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{ten} phải là chuỗi không rỗng, không có khoảng trắng ngoài.")


def _duy_nhat(cac_ma, ten: str) -> None:
    da_co = set()
    for ma in cac_ma:
        _chuoi(ma, ten)
        if ma in da_co:
            raise ValueError(f"{ten} bị trùng: {ma}.")
        da_co.add(ma)


def _thu_tu(value: int) -> None:
    if type(value) is not int:
        raise ValueError("Thứ tự phải là số nguyên.")


@dataclass
class PhanModule:
    """Một phần/màn; quyen_xem giữ nguyên hợp đồng quyền của module cũ.

    hanh_dong là các cột cho MTQ đọc sau này, không suy từ danh sách vai.
    bo_sung giữ trường nguồn chưa biết để adapter không làm mất dữ liệu.
    """

    ma: str
    ten: str
    duong_dan: str
    quyen_xem: dict[str, Any]
    icon: str = ""
    nhom_mau: str = ""
    thu_tu: int = 0
    dem: str | None = None
    hanh_dong: tuple[str, ...] = ()
    bo_sung: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.hanh_dong = tuple(self.hanh_dong)
        self.quyen_xem = deepcopy(self.quyen_xem)
        self.bo_sung = deepcopy(self.bo_sung)
        self.kiem_tra()

    def kiem_tra(self) -> None:
        _chuoi(self.ma, "Mã phần")
        _chuoi(self.ten, "Tên phần")
        _chuoi(self.duong_dan, "Đường dẫn")
        if not self.duong_dan.startswith("#"):
            raise ValueError("Đường dẫn phải bắt đầu bằng #.")
        _thu_tu(self.thu_tu)
        if not isinstance(self.quyen_xem, dict):
            raise ValueError("Quyền xem phải là khai báo dạng dict.")
        if self.dem is not None:
            _chuoi(self.dem, "Mã bộ đếm")
        _duy_nhat(self.hanh_dong, "Hành động")
        if set(self.hanh_dong) - HANH_DONG:
            raise ValueError("Hành động phải thuộc XEM, LAP, SUA, KIEM, DUYET, HUY.")


@dataclass
class TheDem:
    ma: str
    nhan: str
    dem: str
    giai_thich: str
    loc: dict[str, Any]
    canh_bao_khi_lon_hon: int | None = None
    bo_sung: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.loc = deepcopy(self.loc)
        self.bo_sung = deepcopy(self.bo_sung)
        self.kiem_tra()

    def kiem_tra(self) -> None:
        for ten in ("ma", "nhan", "dem", "giai_thich"):
            _chuoi(getattr(self, ten), f"Thẻ đếm: {ten}")
        if not isinstance(self.loc, dict):
            raise ValueError("Bộ lọc thẻ phải là dict.")
        _chuoi(self.loc.get("phan"), "Phần của thẻ")
        if not isinstance(self.loc.get("tham_so"), dict):
            raise ValueError("Tham số lọc thẻ phải là dict.")
        if self.canh_bao_khi_lon_hon is not None and type(self.canh_bao_khi_lon_hon) is not int:
            raise ValueError("Ngưỡng cảnh báo phải là số nguyên hoặc None.")


@dataclass
class KhaiBaoModule:
    """Dữ liệu thuần, có thể chỉnh rồi gọi kiem_tra() trước khi công bố.

    engine_dung chỉ tham chiếu mã, không tự chọn hay gọi phiên bản engine.
    Kiểm tồn tại bằng kiem_tra_engine với snapshot danh bạ XS-3a.
    """

    ma: str
    ten: str
    icon: str
    nhom_mau: str
    thu_tu: int
    phan: tuple[PhanModule, ...] = ()
    the: dict[str, tuple[TheDem, ...]] = field(default_factory=dict)
    engine_dung: tuple[str, ...] = ()
    mac_dinh_cong_tac: CheDoModule = CheDoModule.TAT
    bo_sung: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.phan = tuple(self.phan)
        self.the = {vai: tuple(cac_the) for vai, cac_the in self.the.items()}
        self.engine_dung = tuple(self.engine_dung)
        self.bo_sung = deepcopy(self.bo_sung)
        self.mac_dinh_cong_tac = CheDoModule(self.mac_dinh_cong_tac)
        self.kiem_tra()

    def kiem_tra(self) -> None:
        for ten in ("ma", "ten", "icon", "nhom_mau"):
            _chuoi(getattr(self, ten), f"Module: {ten}")
        _thu_tu(self.thu_tu)
        CheDoModule(self.mac_dinh_cong_tac)
        for phan in self.phan:
            if not isinstance(phan, PhanModule):
                raise ValueError("Phần phải là PhanModule.")
            phan.kiem_tra()
        _duy_nhat((p.ma for p in self.phan), "Mã phần")
        cac_phan = {p.ma for p in self.phan}
        for vai, cac_the in self.the.items():
            _chuoi(vai, "Nhóm thẻ")
            for the in cac_the:
                if not isinstance(the, TheDem):
                    raise ValueError("Thẻ phải là TheDem.")
                the.kiem_tra()
                if the.loc["phan"] not in cac_phan:
                    raise ValueError("Thẻ đếm tham chiếu phần chưa khai báo.")
            _duy_nhat((t.ma for t in cac_the), "Mã thẻ trong nhóm")
        _duy_nhat(self.engine_dung, "Mã engine")

    def danh_muc_hanh_dong(self) -> dict[str, tuple[str, ...]]:
        """Giữ thứ tự màn và hành động; chưa nối resolver/cấp quyền MTQ."""
        self.kiem_tra()
        return {p.ma: tuple(p.hanh_dong) for p in self.phan}

    def kiem_tra_engine(self, danh_ba: DanhBaEngine, *, nghiem_ngat: bool = True) -> tuple[str, ...]:
        """Thiếu mã: từ chối mặc định, hoặc UserWarning và trả các mã thiếu.

        Một mã có nhiều version trong danh bạ vẫn là một tham chiếu hợp lệ;
        việc ghim version khi thực thi thuộc caller, không nằm ở XS-4A.
        """
        self.kiem_tra()
        if type(nghiem_ngat) is not bool:
            raise ValueError("Cờ nghiêm ngặt phải là bool.")
        da_co = {e.ma for e in danh_ba.liet_ke()}
        thieu = tuple(ma for ma in self.engine_dung if ma not in da_co)
        if thieu:
            noi_dung = "Engine chưa có trong danh bạ: " + ", ".join(thieu)
            if nghiem_ngat:
                raise ValueError(noi_dung)
            warnings.warn(noi_dung, UserWarning, stacklevel=2)
        return thieu


def kiem_tra_danh_sach_module(cac_module: tuple[KhaiBaoModule, ...]) -> None:
    """Kiểm mã module duy nhất trước khi các lát sau lập catalog chung."""
    for module in cac_module:
        if not isinstance(module, KhaiBaoModule):
            raise ValueError("Module phải là KhaiBaoModule.")
        module.kiem_tra()
    _duy_nhat((m.ma for m in cac_module), "Mã module")


_TRUONG_MODULE = {"ma", "ten", "icon", "nhom_mau", "thu_tu", "tam_dung", "phan", "the"}
_TRUONG_PHAN = {"ma", "ten", "icon", "nhom_mau", "thu_tu", "quyen", "dem", "duong_dan"}
_TRUONG_THE = ("ma", "nhan", "dem", "giai_thich", "loc", "canh_bao_khi_lon_hon")


def tu_khai_bao_crm() -> KhaiBaoModule:
    """Chỉ import/đọc MODULE['crm']; không gọi service quyền/đếm hay sửa nguồn.

    Import lười để các module khác dùng mô hình thuần không cần nạp CRM.
    Không suy hành động/engine từ code nghiệp vụ: nguồn chưa có thì để rỗng.
    """
    from ..giao_dien.khung_khai_bao import MODULE

    nguon = deepcopy(MODULE["crm"])
    if type(nguon["tam_dung"]) is not bool:
        raise ValueError("tam_dung CRM phải là bool.")
    phan = tuple(PhanModule(
        ma=p["ma"], ten=p["ten"], duong_dan=p["duong_dan"], quyen_xem=p["quyen"],
        icon=p["icon"], nhom_mau=p["nhom_mau"], thu_tu=p["thu_tu"], dem=p["dem"],
        bo_sung={k: v for k, v in p.items() if k not in _TRUONG_PHAN},
    ) for p in nguon["phan"])
    the = {vai: tuple(TheDem(
        **{k: t[k] for k in _TRUONG_THE},
        bo_sung={k: v for k, v in t.items() if k not in _TRUONG_THE},
    ) for t in cac_the) for vai, cac_the in nguon["the"].items()}
    return KhaiBaoModule(
        **{k: nguon[k] for k in ("ma", "ten", "icon", "nhom_mau", "thu_tu")},
        phan=phan, the=the,
        mac_dinh_cong_tac=CheDoModule.TAT if nguon["tam_dung"] else CheDoModule.VAN_HANH,
        bo_sung={k: v for k, v in nguon.items() if k not in _TRUONG_MODULE},
    )


def ve_khai_bao_crm(module: KhaiBaoModule) -> dict[str, Any]:
    """Xuất bản sao dữ liệu theo shape CRM cũ để đối chiếu round-trip.

    CRM cũ không biểu diễn THU, engine hay hành động: từ chối nếu có, tránh
    âm thầm làm mất metadata mới. Không ghi lại vào khung_khai_bao.MODULE.
    """
    module.kiem_tra()
    if (module.mac_dinh_cong_tac == CheDoModule.THU or module.engine_dung
            or any(p.hanh_dong for p in module.phan)):
        raise ValueError("Khai báo CRM cũ không biểu diễn được metadata mới.")
    return deepcopy({
        **module.bo_sung,
        **{k: getattr(module, k) for k in ("ma", "ten", "icon", "nhom_mau", "thu_tu")},
        "tam_dung": module.mac_dinh_cong_tac == CheDoModule.TAT,
        "phan": [{
            **p.bo_sung,
            **{k: getattr(p, k) for k in ("ma", "ten", "icon", "nhom_mau", "thu_tu", "dem", "duong_dan")},
            "quyen": p.quyen_xem,
        } for p in module.phan],
        "the": {vai: [{**t.bo_sung, **{k: getattr(t, k) for k in _TRUONG_THE}}
                      for t in cac_the] for vai, cac_the in module.the.items()},
    })
