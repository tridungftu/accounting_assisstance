"""Quyền dùng chung K2: actor – hành động – pháp nhân – module, đọc từ master.nguoi_dung / master.phan_quyen (TL38/TL40).

Lớp chung cho mọi module K2 (CRM là module đầu tiên dùng), không phải hệ quyền riêng của CRM. CSDL ép lại cùng quy tắc: RLS theo
pháp nhân + module (master.ktt_duoc), trigger kiểm danh tính phiên (ID + login khớp) cho kiểm/duyệt/hoàn tất việc V3/V4.
Danh tính do máy chủ giữ theo phiên (không nhận actor/pháp nhân từ trình duyệt). DEMO chỉ chấp nhận danh tính `mo_phong` (MO_PHONG_*);
trình chọn vai DEMO KHÔNG phải hệ đăng nhập production (TL40 §8 còn phải đạt trước khi mở thật).
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation
from uuid import UUID

from ..ha_tang.primitives import DataError
from .sql_ma_tran_tham_quyen import _CATALOG

# Cùng cách khai loai_tien khi sinh catalog SQL; KHONG_AP_DUNG ở nghiệp vụ
# tương ứng PHI_TIEN trong catalog v1 (chỉ DUYET mới có thể mang tiền).
_LOAI_TIEN_MTQ = {
    f"{module}:{man}:{action}": money if action == "DUYET" else "PHI_TIEN"
    for module, man, actions, money in _CATALOG for action in actions.split()
}

KE_TOAN = {"KE_TOAN", "KE_TOAN_TRUONG"}
HANH_DONG = {  # hành động → (vai trò được phép, module cần)
    "XEM": ({"KE_TOAN", "KE_TOAN_TRUONG", "CFO", "BAN_HANG", "XEM"}, "CRM"),
    "NOP_HOP_DONG": ({"BAN_HANG", "KE_TOAN", "KE_TOAN_TRUONG"}, "CRM"),
    "MAPPING": (KE_TOAN, "CRM"),
    "BO_SUNG_HO_SO": (KE_TOAN, "CRM"),
    "DOI_CHIEU_TRICH_LAI": (KE_TOAN, "CRM"),
    "KIEM_TRUOC": (KE_TOAN, "CRM"),
    "DUYET": ({"CFO"}, "CRM"),
    "DUYET_V4": ({"CFO"}, "CRM"),
    "XUAT_FILE_SOAT": ({"KE_TOAN", "KE_TOAN_TRUONG", "CFO"}, "CRM"),
    "XEM_TIEN": ({"KE_TOAN", "KE_TOAN_TRUONG", "CFO"}, "M1"),
    "NHAN_TIEN": (KE_TOAN, "M1"),
    "LIEN_KET_TIEN": (KE_TOAN, "M1"),
    # M9 vay (binding §5 mục 5): allowlist hành động theo vai trò/module/PN; nối tiền cần cả M9 (đích) và M1 (BANK)
    "M9_READ": ({"KE_TOAN", "KE_TOAN_TRUONG", "CFO", "XEM"}, "M9"),
    "M9_INTAKE": (KE_TOAN, "M9"),
    "M9_STAGE": (KE_TOAN, "M9"),
    "M9_MAP_APPROVE": ({"CFO"}, "M9"),
    "M9_CHECK": (KE_TOAN, "M9"),
    "M9_APPROVE": ({"CFO"}, "M9"),
    "M9_APPROVE_V4": ({"CFO"}, "M9"),
    "M9_MATCH": (KE_TOAN, "M9"),
    "M9_MATCH_M1": (KE_TOAN, "M1"),
    "M9_EXPORT": ({"KE_TOAN", "KE_TOAN_TRUONG", "CFO"}, "M9"),
    # M5 phiếu kho (ma trận DEMO root chốt, không phải policy production): nghiệp vụ theo PN + module M5
    "M5_READ": ({"KE_TOAN", "KE_TOAN_TRUONG", "CFO", "XEM"}, "M5"),
    "M5_FILE_SOAT": ({"KE_TOAN", "KE_TOAN_TRUONG", "CFO"}, "M5"),
    "M5_MAP_V4": ({"CFO"}, "M5"),
    "M5_SOURCE_REVIEW_V8": ({"CFO"}, "M5"),
    # M2 hóa đơn mua XML (R15, ma trận DEMO root chốt — không phải policy production): đọc theo PN + M2; mapping/tuyến/chọn nguồn kỹ thuật cần CFO + V4
    "M2_READ": ({"KE_TOAN", "KE_TOAN_TRUONG", "CFO", "XEM"}, "M2"),
    "M2_MAP": ({"CFO"}, "M2"),
    "M2_ROUTE": ({"CFO"}, "M2"),
    "M2_SOURCE_REVIEW": ({"CFO"}, "M2"),
}
LOAI_VIEC_CAN = {"DUYET": "V3", "DUYET_V4": "V4", "M9_APPROVE": "V3", "M9_APPROVE_V4": "V4", "M9_MAP_APPROVE": "V4",
                 "M5_MAP_V4": "V4", "M5_SOURCE_REVIEW_V8": "V8", "M2_MAP": "V4", "M2_ROUTE": "V4", "M2_SOURCE_REVIEW": "V4"}
HANH_DONG_NGUON = ("INTAKE", "READ_SOURCE", "SOURCE_MAP")
# CRM-41-02 G1/G7 (A2 + DEMO inputs): mã hành động kỹ thuật → (vai được phép hoặc None = theo phân công, loại việc cần, phân công thay thế vai?).
# Cổng thật ở CSDL (master.crm_g_duoc/ktt_hanh_dong_duoc trên kết nối chủ bảng, quyền hiện hành của phiên); bảng này chỉ là registry đọc/kiểm.
HANH_DONG_CRM_G = {
    "CRM_MAU_TAI": (None, None, "CHI_PHAN_CONG"),
    "CRM_MAU_MAP": (KE_TOAN, None, "PHAN_CONG_HOAC_VAI"),
    "CRM_MAU_GUI_KIEM": (KE_TOAN, None, "PHAN_CONG_HOAC_VAI"),
    "CRM_MAU_KIEM": (KE_TOAN, None, "CHI_VAI"),
    "CRM_MAU_TRA_LAI": (KE_TOAN, None, "CHI_VAI"),
    "CRM_MAU_DUYET_V4": ({"CFO"}, "V4", "CHI_VAI"),
    "CRM_MAU_TU_CHOI": ({"CFO"}, "V4", "CHI_VAI"),
    "CRM_CHUAN_LAP": (KE_TOAN, None, "CHI_VAI"),
    "CRM_CHUAN_GUI_DUYET": (KE_TOAN, None, "CHI_VAI"),
    "CRM_CHUAN_DUYET_V4": ({"CFO"}, "V4", "CHI_VAI"),
}
# L11 số lượng (R16): mọi thao tác cần CẢ module M2 VÀ M5 trên cùng PN (một phía không đủ); cùng quy tắc với kho.l11_quyen_noi_bo ở CSDL
L11_THAO_TAC = {
    "READ": ({"KE_TOAN", "KE_TOAN_TRUONG", "CFO", "XEM"}, None),
    "LINK": ({"KE_TOAN", "KE_TOAN_TRUONG", "CFO"}, "V2"),
    "CFO": ({"CFO"}, "V4"),
    "FILE": ({"KE_TOAN", "KE_TOAN_TRUONG", "CFO"}, None),
}


def nap_danh_tinh(conn, dang_nhap: str, *, chi_mo_phong: bool) -> dict:
    if not isinstance(dang_nhap, str) or not dang_nhap:
        raise DataError("DANH_TINH", "Chưa có danh tính phiên.")
    row = conn.execute("SELECT id, dang_nhap, ten, vai_tro, mo_phong, trang_thai FROM master.nguoi_dung WHERE dang_nhap = %s", (dang_nhap,)).fetchone()
    if not row or row["trang_thai"] != "HOAT_DONG":
        raise DataError("DANH_TINH", "Không có người dùng hoạt động với danh tính này.")
    if chi_mo_phong and not row["mo_phong"]:
        raise DataError("DANH_TINH_MO_PHONG", "Bản DEMO chỉ dùng danh tính mô phỏng MO_PHONG_*; không dùng tài khoản thật.")
    quyen = {}
    for q in conn.execute("""SELECT q.phap_nhan_id, p.ma, q.duyet_loai_viec, q.module FROM master.phan_quyen q
                             JOIN master.phap_nhan p ON p.id = q.phap_nhan_id WHERE q.nguoi_dung_id = %s""", (row["id"],)):
        quyen[str(q["phap_nhan_id"])] = {"ma": q["ma"], "duyet": list(q["duyet_loai_viec"]), "module": list(q["module"])}
    return {**row, "id": str(row["id"]), "quyen": quyen}


def duoc(dt: dict, hanh_dong: str, phap_nhan_id) -> bool:
    try:
        kiem(dt, hanh_dong, phap_nhan_id)
        return True
    except DataError:
        return False


def pham_vi(dt: dict, hanh_dong: str) -> list[str]:
    """Các pháp nhân actor được thực hiện hành động (dùng cho đọc danh sách)."""
    return [pn for pn in dt["quyen"] if duoc(dt, hanh_dong, pn)]


def kiem(dt: dict, hanh_dong: str, phap_nhan_id) -> None:
    vai, module = HANH_DONG[hanh_dong]
    pn = dt["quyen"].get(str(phap_nhan_id))
    if pn is None:
        raise DataError("KHONG_CO_QUYEN_PHAP_NHAN", "Người dùng không có quyền trên pháp nhân này.")
    if module not in pn["module"]:
        raise DataError("KHONG_CO_QUYEN_MODULE", f"Người dùng chưa được cấp module {module}.")
    if dt["vai_tro"] not in vai:
        raise DataError("KHONG_CO_QUYEN_HANH_DONG", f"Vai trò {dt['vai_tro']} không được thực hiện {hanh_dong}.")
    can = LOAI_VIEC_CAN.get(hanh_dong)
    if can and can not in pn["duyet"]:
        raise DataError("KHONG_CO_QUYEN_LOAI_VIEC", f"Chưa được giao duyệt loại việc {can}.")


class TuChoiThamQuyen(DataError):
    """Biên nhận nội bộ để caller rollback rồi ghi bằng cổng phiên M0041.

    Không giữ snapshot/revision trong lỗi gửi ra ngoài. Caller phải bắt lỗi này
    ở NGOÀI giao dịch nghiệp vụ; không tự biến lỗi ghi nhật ký thành thành công.
    """

    def __init__(self, ma, ly_do, hanh_dong, doi_tuong, so_tien):
        super().__init__(ma, ly_do)
        self.hanh_dong = hanh_dong
        self.doi_tuong = dict(doi_tuong) if isinstance(doi_tuong, dict) else None
        self.so_tien = so_tien


def kiem_tham_quyen(conn, hanh_dong_ky_thuat, doi_tuong, ngu_canh_tin_cay):
    """Cổng trong transaction đã đặt GUC danh tính ID/login từ phiên máy chủ.

    `doi_tuong` là {bang, id, phong_id?} dựng từ bản ghi thật. Ngữ cảnh chỉ
    chứa callback `kiem_cu`, resolver `so_tien_vnd` và lỗi `khong_thay` của
    service; tuyệt đối không truyền body/header làm ngữ cảnh. SQL xác thực
    danh tính/phạm vi hiện hành, kể cả khi trả CU. Resolver tiền được gọi
    sau kiểm phạm vi và chỉ ở nhánh ma trận (không đổi đường cũ khi tắt).
    """
    obj = dict(doi_tuong) if isinstance(doi_tuong, dict) else None
    tien = None
    loai_tien = _LOAI_TIEN_MTQ.get(hanh_dong_ky_thuat)
    can_tien = loai_tien in {"TONG_HOP_DONG", "XIN_THANH_TOAN"}

    def chan(ma, ly_do):
        # Mã gốc SQL vẫn được giữ khi ghi qua mtq_ghi_tu_choi_phien.
        if ma == "MTQ_THIEU_TIEN":
            ma = "MTQ_THIEU_CO_SO_TIEN"
        if ma in {"MTQ_GAN_VAI", "MTQ_PHAM_VI", "MTQ_PHAP_NHAN"}:
            ma, ly_do = ngu_canh_tin_cay.get(
                "khong_thay", ("HOP_DONG", "Không thấy hợp đồng (hoặc ngoài quyền)."))
        raise TuChoiThamQuyen(ma, ly_do, hanh_dong_ky_thuat, obj, tien) from None

    def hoi():
        try:
            row = conn.execute(
                "SELECT master.mtq_quyet_dinh_phien(%s,%s::jsonb,%s) AS q",
                (hanh_dong_ky_thuat, json.dumps(obj, ensure_ascii=False), tien)).fetchone()
            q = row["q"]
            if not isinstance(q, dict) or q.get("nguon") not in {"CU", "MA_TRAN"}:
                raise ValueError("Quyết định không đúng hợp đồng")
            if any(not isinstance(q.get(k), str) or not q[k] for k in ("ma", "ly_do")):
                raise ValueError("Thiếu quyết định")
            if q["nguon"] == "MA_TRAN":
                if type(q.get("cho_phep")) is not bool:
                    raise ValueError("Thiếu quyết định")
                if q["cho_phep"]:
                    if (q["ma"] != "MTQ_CHO_PHEP" or type(q.get("revision")) is not int
                            or q["revision"] < 1 or "gioi_han_vnd" not in q
                            or [q.get(k) for k in ("module", "man", "hanh_dong")] != hanh_dong_ky_thuat.split(":")):
                        raise ValueError("Thiếu snapshot/ô áp dụng")
                    UUID(q["phien_ban_id"])
                    UUID(q["dong_id"])
            return q
        except Exception:
            logging.getLogger(__name__).error("MTQ_LOI_QUYET_DINH hành động=%s", hanh_dong_ky_thuat, exc_info=True)
            chan("MTQ_LOI_QUYET_DINH", "Không xác định được thẩm quyền; thao tác bị chặn. Báo quản trị.")

    q = hoi()
    try:
        if not isinstance(obj, dict) or set(obj) - {"bang", "id", "phong_id"}:
            raise ValueError("Sai tham chiếu")
        if not isinstance(obj.get("bang"), str) or not obj["bang"]:
            raise ValueError("Thiếu bảng")
        UUID(obj["id"])
        if obj.get("phong_id") is not None:
            UUID(obj["phong_id"])
    except (ValueError, TypeError, KeyError, AttributeError):
        chan("MTQ_DOI_TUONG", "Cần tham chiếu đối tượng thật hợp lệ từ máy chủ; thao tác bị chặn.")
    if q["nguon"] == "CU":
        # Không bắt/đổi lỗi, không kết hợp OR/AND với quyết định ma trận.
        ngu_canh_tin_cay["kiem_cu"]()
        return {"nguon": "CU", "cho_phep": True, "revision": None, "o_ap_dung": None,
                "gioi_han_vnd": None, "so_tien_vnd": None, "ma": q["ma"], "ly_do": q["ly_do"]}
    if not q["cho_phep"] and q["ma"] != "MTQ_THIEU_TIEN":
        chan(q["ma"], q["ly_do"])
    if loai_tien is None:
        chan("MTQ_HANH_DONG", "Hành động chưa có trong catalog thẩm quyền; thao tác bị chặn.")

    resolver = ngu_canh_tin_cay.get("so_tien_vnd")
    try:
        value = (resolver() if callable(resolver) else resolver) if can_tien else None
        # Không đi qua float; VND phải nguyên, hữu hạn, không âm như lõi SQL.
        if value is not None and not isinstance(value, (bool, float)):
            tien = Decimal(value)
            if not tien.is_finite() or tien < 0 or tien != tien.to_integral_value():
                tien = None
    except DataError:
        # DataError kế thừa ValueError: giữ mã/locator không thấy HĐ/bản
        # đã đọc qua RLS, không biến thành lỗi thiếu tiền.
        raise
    except (ValueError, TypeError, InvalidOperation):
        tien = None
    except Exception:
        logging.getLogger(__name__).error("MTQ_LOI_QUYET_DINH đọc tiền hành động=%s", hanh_dong_ky_thuat, exc_info=True)
        chan("MTQ_LOI_QUYET_DINH", "Không đọc được căn cứ tiền đã khóa; thao tác bị chặn. Báo quản trị.")
    q = hoi()
    if q["nguon"] != "MA_TRAN":
        chan("MTQ_LOI_QUYET_DINH", "Chế độ thẩm quyền thay đổi trong thao tác; không thực hiện.")
    if not q["cho_phep"]:
        chan(q["ma"], q["ly_do"])
    if can_tien and tien is None:
        chan("MTQ_THIEU_CO_SO_TIEN", "Chưa có tổng giá trị hợp đồng VND từ phiên bản đã khóa; chưa thể duyệt.")
    try:
        han_muc = None if q.get("gioi_han_vnd") is None else Decimal(str(q["gioi_han_vnd"]))
        if han_muc is not None and (not han_muc.is_finite() or han_muc < 0):
            raise ValueError("Hạn mức sai")
    except (ValueError, TypeError, InvalidOperation):
        chan("MTQ_LOI_QUYET_DINH", "Hạn mức thẩm quyền không hợp lệ; thao tác bị chặn.")
    if can_tien and tien is not None and han_muc is not None and tien > han_muc:
        chan("MTQ_VUOT_HAN_MUC", "Số tiền duyệt vượt giới hạn tiền VND của dòng.")
    return {**q, "so_tien_vnd": tien, "gioi_han_vnd": han_muc,
            "o_ap_dung": {k: q.get(k) for k in ("dong_id", "module", "man", "hanh_dong")}}


def ghi_tu_choi_tham_quyen(conn, request_id, loi):
    """Gọi trong transaction RIÊNG sau rollback, đã đặt lại GUC phiên."""
    try:
        row = conn.execute("SELECT master.mtq_ghi_tu_choi_phien(%s::uuid,%s,%s::jsonb,%s) AS id",
                           (request_id, loi.hanh_dong, json.dumps(loi.doi_tuong, ensure_ascii=False),
                            loi.so_tien)).fetchone()
        if not row or not row["id"]:
            raise ValueError("Không có biên nhận nhật ký")
    except Exception:
        raise DataError("MTQ_NHAT_KY_LOI", "Chưa ghi được nhật ký thẩm quyền, thao tác không được thực hiện. Báo quản trị.") from None


def kiem_l11(dt: dict, loai: str, phap_nhan_id) -> None:
    """Kiểm sớm phía máy chủ cho L11 (CSDL vẫn là cổng quyết định): BOTH M2 + M5 trên PN, vai trò và loại việc theo thao tác."""
    vai, viec = L11_THAO_TAC[loai]
    pn = dt["quyen"].get(str(phap_nhan_id))
    if pn is None:
        raise DataError("KHONG_CO_QUYEN_PHAP_NHAN", "Người dùng không có quyền trên pháp nhân này.")
    for module in ("M2", "M5"):
        if module not in pn["module"]:
            raise DataError("KHONG_CO_QUYEN_MODULE", f"Liên kết số lượng cần cả M2 và M5 — chưa được cấp module {module}.")
    if dt["vai_tro"] not in vai:
        raise DataError("KHONG_CO_QUYEN_HANH_DONG", f"Vai trò {dt['vai_tro']} không được thực hiện thao tác L11 {loai}.")
    if viec and viec not in pn["duyet"]:
        raise DataError("KHONG_CO_QUYEN_LOAI_VIEC", f"Chưa được giao loại việc {viec}.")


def duoc_l11(dt: dict, loai: str, phap_nhan_id) -> bool:
    try:
        kiem_l11(dt, loai, phap_nhan_id)
        return True
    except DataError:
        return False


def kiem_nguon(conn, source_instance: str, profile_ref: str, profile_sha256: str, hanh_dong: str, phap_nhan_id=None) -> None:
    """Guard nguồn trước PN (không phải hệ quyền riêng M5): phải gọi TRONG giao dịch đã đặt danh tính phiên (ID + login). CSDL quyết định qua
    `master.ktt_nguon_duoc` — năng lực lưu tại DB theo actor + đúng instance + profile ref/SHA bất biến + action (+ PN đích cho SOURCE_MAP);
    không dùng `kiem` với PN giả cho capture/raw và không nhận boolean từ trình duyệt."""
    if hanh_dong not in HANH_DONG_NGUON:
        raise DataError("HANH_DONG_NGUON", "Hành động nguồn không hợp lệ.")
    if (hanh_dong == "SOURCE_MAP") != (phap_nhan_id is not None):
        raise DataError("HANH_DONG_NGUON", "SOURCE_MAP cần PN đích; INTAKE/READ_SOURCE không có PN.")
    row = conn.execute("SELECT master.ktt_nguon_duoc(%s, %s, %s, %s, %s::uuid) AS ok",
                       (source_instance, profile_ref, profile_sha256, hanh_dong, phap_nhan_id)).fetchone()
    if not (row["ok"] if isinstance(row, dict) else row[0]):
        raise DataError("NGUON_KHONG_CO_QUYEN", f"Phiên không có năng lực nguồn {hanh_dong} trên instance/profile này.")
