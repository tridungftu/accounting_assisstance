"""Quyền dùng chung K2: actor – hành động – pháp nhân – module, đọc từ master.nguoi_dung / master.phan_quyen (TL38/TL40).

Lớp chung cho mọi module K2 (CRM là module đầu tiên dùng), không phải hệ quyền riêng của CRM. CSDL ép lại cùng quy tắc: RLS theo
pháp nhân + module (master.ktt_duoc), trigger kiểm danh tính phiên (ID + login khớp) cho kiểm/duyệt/hoàn tất việc V3/V4.
Danh tính do máy chủ giữ theo phiên (không nhận actor/pháp nhân từ trình duyệt). DEMO chỉ chấp nhận danh tính `mo_phong` (MO_PHONG_*);
trình chọn vai DEMO KHÔNG phải hệ đăng nhập production (TL40 §8 còn phải đạt trước khi mở thật).
"""

from __future__ import annotations

from ..ha_tang.primitives import DataError

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
