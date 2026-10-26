"""Báo cáo thuần từ một snapshot Sheet; không kéo dữ liệu, không gửi báo cáo."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP, localcontext
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


_ZERO = Decimal(0)
_CHO_TRICH_DAN = "chờ nối trích dẫn hợp đồng (M9-2)"
_GHI_CHU = "Lãi trả thêm là ước tính; không gửi ra ngoài khi chưa duyệt."
_SO_LE_TIEN = {"VND": 0, "USD": 2}
_CHU_DE_DAM_PHAN = (
    "biên độ lãi suất", "điều chỉnh lãi suất", "phí trả nợ trước hạn",
)
_KHONG_THAY = "Không thấy trong hợp đồng"


def _so(gia_tri) -> Decimal | None:
    # Không chuyển float hoặc chuỗi thành số: đầu vào phải được chuẩn hóa ở M9-3.
    if isinstance(gia_tri, Decimal) and gia_tri.is_finite():
        return gia_tri
    return None


def _chu(gia_tri) -> str | None:
    return gia_tri if isinstance(gia_tri, str) and gia_tri.strip() else None


def _ngay(gia_tri) -> date | None:
    return gia_tri if type(gia_tri) is date else None


def _kiem_nguon(du_lieu: dict) -> None:
    if du_lieu.get("nguon") != "Sheet":
        raise ValueError("Cần Anh/lead: chỉ nhận nguồn Sheet có mốc dữ liệu.")
    moc = du_lieu.get("moc")
    try:
        if not isinstance(moc, str):
            raise ValueError
        da_doc = datetime.strptime(moc, "%d/%m/%Y %H:%M")
        if da_doc.strftime("%d/%m/%Y %H:%M") != moc:
            raise ValueError
    except ValueError:
        raise ValueError("Cần Anh/lead: mốc Sheet phải có dạng dd/mm/yyyy hh:mm.") from None


def lap_bao_cao(snapshot: dict, *, ngay_bao_cao: date, chi_muc=None,
                tai_lieu_theo_khoan_vay: dict[str, set[str]] | None = None) -> dict:
    """Lập báo cáo, giữ Decimal theo precision hiện hành, không quantize.

    binh_quan_theo_tien_te chỉ dùng khoản có dư nợ dương và đủ lãi suất.
    tong_du_no_theo_tien_te cộng dư nợ không âm đã biết, kể cả thiếu lãi;
    None nghĩa là không có dư nợ hợp lệ, không thay thiếu dữ liệu bằng 0.
    Khoản không đủ số liệu có lai_cao/chenh_lech/ước tính = None.
    Trường tài chính sai kiểu/không hữu hạn được coi là thiếu, không suy đoán.
    Có chỉ mục và ánh xạ thì trích tối đa một câu gốc cho mỗi chủ đề,
    chỉ trong tài liệu của khoản vay; mã chưa ánh xạ dùng bộ lọc rỗng.
    """
    _kiem_nguon(snapshot)
    if type(ngay_bao_cao) is not date:
        raise ValueError("ngay_bao_cao phải là date.")
    if not isinstance(snapshot.get("khoan_vay"), list):
        raise ValueError("Cần Anh/lead: thiếu danh sách khoản vay đã chuẩn hóa.")

    cac_khoan = []
    tong_du_no = {}
    tu_so = {}
    mau_so = {}
    can_anh = []
    for dau_vao in snapshot["khoan_vay"]:
        if not isinstance(dau_vao, dict):
            raise ValueError("Cần Anh/lead: khoản vay phải là dict đã chuẩn hóa.")
        tien_te = _chu(dau_vao.get("tien_te"))
        du_no = _so(dau_vao.get("du_no"))
        if du_no is not None and du_no < 0:
            du_no = None
        lai_suat = _so(dau_vao.get("lai_suat_nam"))
        thieu = []
        if tien_te is None:
            thieu.append("tien_te")
        if du_no is None or du_no <= 0:
            thieu.append("du_no > 0")
        if lai_suat is None:
            thieu.append("lai_suat_nam")

        khoan = {
            "phap_nhan": _chu(dau_vao.get("phap_nhan")),
            "ngan_hang": _chu(dau_vao.get("ngan_hang")),
            "ma_khoan_vay": _chu(dau_vao.get("ma_khoan_vay")),
            "tien_te": tien_te,
            "du_no": du_no,
            "lai_suat_nam": lai_suat,
            "cach_tinh": _chu(dau_vao.get("cach_tinh")),
            "lai_co_so": _so(dau_vao.get("lai_co_so")),
            "bien_do": _so(dau_vao.get("bien_do")),
            "ky_dieu_chinh_ke_tiep": _ngay(dau_vao.get("ky_dieu_chinh_ke_tiep")),
            "ngay_dao_han": _ngay(dau_vao.get("ngay_dao_han")),
            "trang_thai": "THIEU_DU_LIEU" if thieu else "DU_DU_LIEU",
            "thieu_truong": thieu,
            "binh_quan": None,
            "chenh_lech": None,
            "lai_cao": None,
            "lai_tra_them_uoc_tinh_nam": None,
            "don_vi_lai_tra_them": tien_te,
            "nhan_lai_tra_them": "Lãi trả thêm ước tính một năm",
            "canh_bao": [],
            "dieu_khoan_lien_quan_toi_dam_phan": "",
            "ghi_chu": _CHO_TRICH_DAN,
        }
        if chi_muc is not None and tai_lieu_theo_khoan_vay is not None:
            tai_lieu = tai_lieu_theo_khoan_vay.get(khoan["ma_khoan_vay"], set())
            dieu_khoan = []
            for chu_de in _CHU_DE_DAM_PHAN:
                ket_qua = chi_muc.tim(chu_de, so_ket_qua=1, loc_tai_lieu=tai_lieu)
                trich = ket_qua[0]["trich_dan"] if ket_qua else {
                    "ten_tep": None, "trang": None, "dieu": None,
                    "khoan": None, "cau": _KHONG_THAY,
                }
                dieu_khoan.append({"chu_de": chu_de, **{
                    truong: trich[truong]
                    for truong in ("ten_tep", "trang", "dieu", "khoan", "cau")
                }})
            khoan["dieu_khoan_lien_quan_toi_dam_phan"] = dieu_khoan
            khoan["ghi_chu"] = ""
        if thieu:
            khoan["ghi_chu"] += (("; " if khoan["ghi_chu"] else "")
                                 + "Cần Anh/lead: bổ sung " + ", ".join(thieu))
            can_anh.append(khoan["ghi_chu"])
        # Ngày sai kiểu không được âm thầm coi là không có cảnh báo.
        for truong in ("ky_dieu_chinh_ke_tiep", "ngay_dao_han"):
            if dau_vao.get(truong) is not None and khoan[truong] is None:
                ghi_chu = "Cần Anh/lead: chuẩn hóa " + truong + " thành date."
                khoan["ghi_chu"] += ("; " if khoan["ghi_chu"] else "") + ghi_chu
                can_anh.append(ghi_chu)
        ky = khoan["ky_dieu_chinh_ke_tiep"]
        if ky is not None:
            if ky < ngay_bao_cao:
                khoan["canh_bao"].append("DA_QUA_KY")
            elif (ky - ngay_bao_cao).days <= 30:
                khoan["canh_bao"].append("SAP_DIEU_CHINH")
        if tien_te is not None:
            tong_du_no.setdefault(tien_te, None)
            tu_so.setdefault(tien_te, _ZERO)
            mau_so.setdefault(tien_te, _ZERO)
            if du_no is not None:
                tong_du_no[tien_te] = (tong_du_no[tien_te] or _ZERO) + du_no
            if not thieu:
                tu_so[tien_te] += du_no * lai_suat
                mau_so[tien_te] += du_no
        cac_khoan.append(khoan)

    binh_quan = {
        tien: tu_so[tien] / mau_so[tien] if mau_so[tien] > 0 else None
        for tien in sorted(tong_du_no)
    }
    for khoan in cac_khoan:
        khoan["binh_quan"] = binh_quan.get(khoan["tien_te"])
        if khoan["trang_thai"] == "DU_DU_LIEU":
            chenh = khoan["lai_suat_nam"] - khoan["binh_quan"]
            khoan["chenh_lech"] = chenh
            khoan["lai_cao"] = chenh > 0
            if khoan["lai_cao"]:
                khoan["lai_tra_them_uoc_tinh_nam"] = khoan["du_no"] * chenh / 100
    cac_khoan.sort(key=lambda k: (
        k["tien_te"] is None, k["tien_te"] or "",
        k["trang_thai"] == "THIEU_DU_LIEU",
        -k["chenh_lech"] if k["chenh_lech"] is not None else _ZERO,
    ))
    canh_bao = [
        {"phap_nhan": k["phap_nhan"], "ngan_hang": k["ngan_hang"],
         "ma_khoan_vay": k["ma_khoan_vay"], "tien_te": k["tien_te"],
         "ky_dieu_chinh_ke_tiep": k["ky_dieu_chinh_ke_tiep"], "loai": loai}
        for k in cac_khoan for loai in k["canh_bao"]
    ]
    for tien in sorted(tong_du_no):
        if tien not in _SO_LE_TIEN:
            can_anh.append("Cần Anh/lead: chốt số lẻ tiền " + tien + "; xuất chưa làm tròn.")
    return {
        "moc": snapshot["moc"], "nguon": snapshot["nguon"],
        "ngay_bao_cao": ngay_bao_cao,
        "tong_du_no_theo_tien_te": dict(sorted(tong_du_no.items())),
        "binh_quan_theo_tien_te": binh_quan,
        "so_khoan_lai_cao": sum(k["lai_cao"] is True for k in cac_khoan),
        "khoan_vay": cac_khoan, "canh_bao": canh_bao,
        "ghi_chu": _GHI_CHU, "can_anh": can_anh,
    }


def _tien_excel(gia_tri: Decimal | None, tien_te: str) -> Decimal | None:
    if gia_tri is None or tien_te not in _SO_LE_TIEN:
        return gia_tri
    with localcontext() as ctx:
        ctx.prec = max(ctx.prec, len(gia_tri.as_tuple().digits) + abs(gia_tri.adjusted()) + 4)
        return gia_tri.quantize(Decimal(1).scaleb(-_SO_LE_TIEN[tien_te]), rounding=ROUND_HALF_UP)


def _dinh_dang_tien(tien_te: str) -> str:
    if tien_te in _SO_LE_TIEN:
        so_le = _SO_LE_TIEN[tien_te]
        return "#,##0" + ("." + "0" * so_le if so_le else "")
    return "#,##0.################"


def _dieu_khoan_excel(dieu_khoan) -> str:
    if not dieu_khoan:
        return ""
    cac_dong = []
    for muc in dieu_khoan:
        nguon = []
        for truong, nhan in (("ten_tep", ""), ("trang", "trang "),
                             ("dieu", "Điều "), ("khoan", "Khoản ")):
            if muc[truong] is not None:
                nguon.append(nhan + str(muc[truong]))
        dong = muc["chu_de"] + ": " + muc["cau"]
        if nguon:
            dong += " (" + ", ".join(nguon) + ")"
        cac_dong.append(dong)
    return "\n".join(cac_dong)


def xuat_excel(bao_cao: dict) -> bytes:
    """Xuất một sheet trong bộ nhớ; VND 0, USD 2 số lẻ, ROUND_HALF_UP.

    Lãi suất là số phần trăm/năm (8 nghĩa là 8%); chênh lệch là điểm %.
    Các đồng tiền khác giữ số, chờ chốt quy tắc làm tròn. Không ghi công thức.
    """
    _kiem_nguon(bao_cao)
    wb = Workbook()
    ws = wb.active
    ws.title = "Báo cáo lãi suất"

    def them_hang(gia_tri):
        ws.append(gia_tri)
        for o in ws[ws.max_row]:
            if isinstance(o.value, str):
                o.data_type = "s"  # Kể cả tên/mã nguồn bắt đầu bằng '='.

    def tieu_de_hang(so_hang, so_cot):
        for hang in ws.iter_rows(min_row=so_hang, max_row=so_hang, max_col=so_cot):
            for o in hang:
                o.fill = PatternFill("solid", fgColor="18364B")
                o.font = Font(color="FFFFFF", bold=True)
                o.alignment = Alignment(wrap_text=True, vertical="center")
        ws.row_dimensions[so_hang].height = 56

    them_hang(["BÁO CÁO LÃI SUẤT HẰNG THÁNG"])
    ws.merge_cells("A1:S1")
    ws["A1"].font = Font(size=16, bold=True, color="18364B")
    them_hang(["Nguồn: Sheet theo dõi khoản vay, mốc " + bao_cao["moc"]])
    ws.merge_cells("A2:S2")
    them_hang(["Ngày báo cáo", bao_cao["ngay_bao_cao"]])
    ws["B3"].number_format = "dd/mm/yyyy"
    them_hang(["Số khoản lãi cao", bao_cao["so_khoan_lai_cao"]])
    them_hang(["Tổng dư nợ gồm dư nợ đã biết; bình quân chỉ gồm khoản đủ dữ liệu, dư nợ > 0."])
    ws.merge_cells("A5:S5")
    them_hang(["Đồng tiền", "Tổng dư nợ (đồng tiền)", "Bình quân gia quyền (%/năm)"])
    tieu_de_hang(6, 3)
    for tien, tong in bao_cao["tong_du_no_theo_tien_te"].items():
        them_hang([tien, _tien_excel(tong, tien), bao_cao["binh_quan_theo_tien_te"][tien]])
        ws.cell(ws.max_row, 2).number_format = _dinh_dang_tien(tien)
        ws.cell(ws.max_row, 3).number_format = "0.0000"
    them_hang([None])
    them_hang([
        "Pháp nhân", "Ngân hàng", "Mã khoản vay", "Đồng tiền",
        "Dư nợ (đồng tiền)", "Lãi suất áp dụng (%/năm)", "Cách tính lãi",
        "Lãi cơ sở (%/năm)", "Biên độ (điểm %)", "Bình quân gia quyền (%/năm)",
        "Chênh lệch (điểm %)", "Lãi cao", "Lãi trả thêm ước tính một năm (đồng tiền)",
        "Kỳ điều chỉnh kế tiếp", "Ngày đáo hạn", "Trạng thái", "Cảnh báo",
        "Điều khoản liên quan tới đàm phán", "Ghi chú",
    ])
    dong_tieu_de = ws.max_row
    tieu_de_hang(dong_tieu_de, 19)
    for k in bao_cao["khoan_vay"]:
        tien = k["tien_te"]
        them_hang([
            k["phap_nhan"], k["ngan_hang"], k["ma_khoan_vay"], tien,
            _tien_excel(k["du_no"], tien), k["lai_suat_nam"],
            {"CO_DINH": "Cố định", "THA_NOI": "Thả nổi"}.get(k["cach_tinh"], k["cach_tinh"]),
            k["lai_co_so"], k["bien_do"], k["binh_quan"], k["chenh_lech"],
            None if k["lai_cao"] is None else ("Có" if k["lai_cao"] else "Không"),
            _tien_excel(k["lai_tra_them_uoc_tinh_nam"], tien),
            k["ky_dieu_chinh_ke_tiep"], k["ngay_dao_han"], k["trang_thai"],
            ", ".join(k["canh_bao"]),
            _dieu_khoan_excel(k["dieu_khoan_lien_quan_toi_dam_phan"]), k["ghi_chu"],
        ])
        dong = ws.max_row
        for cot in (5, 13):
            ws.cell(dong, cot).number_format = _dinh_dang_tien(tien)
        for cot in (6, 8, 9, 10, 11):
            ws.cell(dong, cot).number_format = "0.0000"
        for cot in (14, 15):
            ws.cell(dong, cot).number_format = "dd/mm/yyyy"
        for o in ws[dong]:
            o.alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[dong].height = 60
    if bao_cao["khoan_vay"]:
        ws.auto_filter.ref = f"A{dong_tieu_de}:S{ws.max_row}"
    ws.freeze_panes = f"E{dong_tieu_de + 1}"
    them_hang([None])
    for ghi_chu in bao_cao.get("can_anh", []):
        them_hang([ghi_chu])
        ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=19)
    if not bao_cao["khoan_vay"] or any(
            k["dieu_khoan_lien_quan_toi_dam_phan"] == "" for k in bao_cao["khoan_vay"]):
        them_hang([_CHO_TRICH_DAN])
        ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=19)
    them_hang([_GHI_CHU])
    ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=19)
    for cot in range(1, 20):
        ws.column_dimensions[get_column_letter(cot)].width = 22
    for cot, rong in {"A": 28, "B": 28, "C": 28, "D": 14, "M": 30, "R": 38, "S": 64}.items():
        ws.column_dimensions[cot].width = rong
    bo_dem = BytesIO()
    wb.save(bo_dem)
    wb.close()
    return bo_dem.getvalue()
