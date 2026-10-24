"""Policy tiền tệ thuần, không sửa dữ liệu nguồn và không đọc Excel.

XML là mapping: DVTTe, TGia (chỉ bỏ khóa khi thẻ không tồn tại),
mst_ban, mst_mua (chuỗi MST raw). Bảng kê là mapping có dvtte_cong,
hoặc None khi chưa có thông tin. Caller chịu trách nhiệm trích xuất XML.
THEO_XML chỉ có nghĩa tiền tệ được khai báo trong XML; DE_XUAT luôn có cờ
theo policy. Hai trạng thái này không thay thế việc duyệt/intake của M2c.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ...ha_tang.primitives import DataError

DUONG_DAN_QUY_TAC = Path(__file__).with_name("quy_tac") / "POLICY-TIENTE-01.v1.json"


@dataclass(frozen=True)
class KetQua:
    trang_thai: str
    de_xuat_tien_te: str | None
    co_theo_policy: bool
    ly_do: str
    ma_policy: str
    phien_ban: str


def nap_quy_tac(duong_dan: str | Path) -> dict:
    """Nạp lại mỗi lần áp dụng; lỗi cấu hình không được rơi về mặc định ngầm."""
    try:
        q = json.loads(Path(duong_dan).read_text(encoding="utf-8"))
        if not isinstance(q, dict) or set(q) != {
            "ma_policy", "phien_ban", "tien_te_noi_dia", "ty_gia_noi_dia", "mst_vn"
        }:
            raise ValueError
        if any(not isinstance(q[k], str) or not q[k].strip()
               for k in ("ma_policy", "phien_ban", "tien_te_noi_dia")):
            raise ValueError
        if not re.fullmatch(r"[A-Z]{3}", q["tien_te_noi_dia"]):
            raise ValueError
        if isinstance(q["ty_gia_noi_dia"], bool):
            raise ValueError
        ty_gia = Decimal(str(q["ty_gia_noi_dia"]))
        if not ty_gia.is_finite() or ty_gia <= 0:
            raise ValueError
        mst = q["mst_vn"]
        if not isinstance(mst, dict) or set(mst) != {"do_dai", "bo_ky_tu"}:
            raise ValueError
        if not isinstance(mst["do_dai"], list) or not mst["do_dai"] or any(
            type(n) is not int or n <= 0 for n in mst["do_dai"]
        ) or not isinstance(mst["bo_ky_tu"], str):
            raise ValueError
        return q
    except (OSError, UnicodeError, ValueError, InvalidOperation, TypeError):
        raise DataError("M2_00_POLICY_SAI", "Không đọc được quy tắc tiền tệ hợp lệ.") from None


def _mst_vn(v, quy_tac: dict) -> bool:
    if not isinstance(v, str):
        return False
    for ky_tu in quy_tac["bo_ky_tu"]:
        v = v.replace(ky_tu, "")
    return len(v) in quy_tac["do_dai"] and re.fullmatch(r"[0-9]+", v) is not None


def _tien_te(v) -> str | None:
    return v.strip().upper() if isinstance(v, str) and v.strip() else None


def ap_dung(thong_tin_xml, thong_tin_bang_ke, *, duong_dan_quy_tac=None) -> KetQua:
    """Trả đề xuất có provenance; không bao giờ bổ sung DVTTe vào mapping XML.

    DVTTe/TGia rỗng hoặc None nhưng có khóa vẫn là thẻ có mặt, nên không đủ
    điều kiện suy VND. TGia có mặt bằng 1 cũng không đủ điều kiện policy.
    """
    if not isinstance(thong_tin_xml, Mapping) or (
        thong_tin_bang_ke is not None and not isinstance(thong_tin_bang_ke, Mapping)
    ):
        raise DataError("M2_00_POLICY_DAU_VAO", "Thông tin XML/bảng kê phải là mapping.")
    q = nap_quy_tac(DUONG_DAN_QUY_TAC if duong_dan_quy_tac is None else duong_dan_quy_tac)
    xml, bk = thong_tin_xml, thong_tin_bang_ke or {}
    noi_dia = q["tien_te_noi_dia"]

    def ket_qua(trang_thai, ly_do, tien_te=None, co=False):
        return KetQua(trang_thai, tien_te, co, ly_do, q["ma_policy"], q["phien_ban"])

    tien_xml, tien_bk = _tien_te(xml.get("DVTTe")), _tien_te(bk.get("dvtte_cong"))
    if tien_xml is not None and tien_bk is not None and tien_xml != tien_bk:
        return ket_qua("XUNG_DOT", "XML_BANG_KE_KHAC_TIEN_TE")
    if "DVTTe" in xml and tien_xml != noi_dia:
        return ket_qua("CHUA_RO", "DVTTE_KHAC_NOI_DIA_HOAC_KHONG_HOP_LE")
    if "TGia" in xml:
        try:
            if isinstance(xml["TGia"], bool):
                raise ValueError
            ty_gia = Decimal(str(xml["TGia"]))
            if not ty_gia.is_finite() or ty_gia != Decimal(str(q["ty_gia_noi_dia"])):
                return ket_qua("CHUA_RO", "TGIA_KHAC_NOI_DIA")
        except (InvalidOperation, ValueError):
            return ket_qua("CHUA_RO", "TGIA_KHONG_HOP_LE")
    if tien_bk is not None and tien_bk != noi_dia:
        return ket_qua("CHUA_RO", "BANG_KE_KHAC_NOI_DIA")
    if "dvtte_cong" in bk and tien_bk is None:
        # Bảng kê thiếu thông tin tiền tệ không phải chứng cứ ngoại tệ.
        # Giá trị có cấu trúc/sai kiểu thì không được bỏ qua.
        if bk["dvtte_cong"] is not None and not isinstance(bk["dvtte_cong"], str):
            return ket_qua("CHUA_RO", "TIEN_TE_BANG_KE_KHONG_HOP_LE")
    if tien_xml == noi_dia:
        return ket_qua("THEO_XML", "DVTTE_TU_XML", noi_dia)
    if not all(_mst_vn(xml.get(k), q["mst_vn"]) for k in ("mst_ban", "mst_mua")):
        return ket_qua("CHUA_RO", "THIEU_MST_VN_HOP_LE")
    if "DVTTe" not in xml and "TGia" not in xml:
        return ket_qua("DE_XUAT", "THIEU_DVTTE_TGIA_HAI_MST_VN", noi_dia, True)
    return ket_qua("CHUA_RO", "CHUA_DU_DIEU_KIEN_POLICY")
