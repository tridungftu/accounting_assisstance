"""Fixture DEMO cho CRM-01: kết quả `*_KET_QUA.json` đúng shape #6 + văn bản đối chiếu DEMO (mục Điều/Khoản) + envelope + sao kê
M1 DEMO (định dạng nguồn V12 hiện có). Mọi giá trị là giả lập có nhãn DEMO, không lấy từ hợp đồng/đáp án/kết quả thật.
Bản DEMO không có tệp Word thật: envelope dùng `word_tham_chieu` (định danh), KHÔNG dùng hash của chuỗi tưởng tượng làm hash Word."""

from __future__ import annotations

from ..ha_tang.primitives import canonical_json


def _p(ma, ten, gia_tri, trich_dan, *, don_vi=None, dieu=None, nhom="DEMO", ghi_chu=None):
    return {"ma": ma, "nhom": nhom, "tham_so": ten, "gia_tri": gia_tri, "don_vi": don_vi, "dieu_khoan": dieu, "trich_dan": trich_dan,
            "ghi_chu": ghi_chu, "kiem_tra": "OK", "vi_tri_do_duoc": dieu}


def ket_qua(ten_file, tham_so, *, che_do="co_AI", model="DEMO-MODEL-KHONG-THAT"):
    return {"hop_dong": ten_file, "che_do": che_do, "model": model, "tao_luc": "2026-10-01T09:00:00", "tham_so": tham_so,
            "phieu_kiem_tra": {"canh_bao": []}, "so_tham_so": len(tham_so), "so_ok_tu_kiem": len(tham_so)}


VB_KCN = [
    {"dieu_khoan": "Phần đầu", "noi_dung": "HỢP ĐỒNG THUÊ ĐẤT DEMO. Hợp đồng số HD-KCN-DEMO/01 ký ngày 01/09/2026."},
    {"dieu_khoan": "Điều 2", "noi_dung": "Diện tích thuê 10.000 m2."},
    {"dieu_khoan": "Điều 3", "noi_dung": "Tổng tiền thuê đất là 3.000.000.000 đồng (chưa gồm VAT)."},
    {"dieu_khoan": "Điều 4", "noi_dung": "Bên thuê đặt cọc 300.000.000 đồng trước ngày 15/09/2026. Đợt 1 thanh toán 1.200.000.000 đồng trước ngày 15/10/2026. "
                                         "Đợt 2 thanh toán 1.500.000.000 đồng khi bàn giao đất."},
]
VB_KCN_PL = "PHỤ LỤC DEMO số PL01-KCN-DEMO có hiệu lực từ ngày 01/10/2026. Đợt 2 thanh toán trước ngày 20/12/2026."
VB_NHA = ("HỢP ĐỒNG MUA BÁN NHÀ Ở DEMO. Hợp đồng số HD-NHA-DEMO/07 ký ngày 05/09/2026. Căn hộ A-12-DEMO. Giá bán 2.000.000.000 đồng chưa gồm VAT. "
          "Đặt cọc 100.000.000 đồng trước ngày 10/09/2026. Đợt 1 thanh toán 900.000.000 đồng trước ngày 10/11/2026. Đợt 2 thanh toán 1.000.000.000 đồng khi bàn giao căn hộ.")
VB_NHA_PL = "PHỤ LỤC DEMO số PL01-NHA-DEMO có hiệu lực từ ngày 01/11/2026. Đợt 2 thanh toán trước ngày 15/01/2027."
VB_NHA_PL_MO_HO = "PHỤ LỤC DEMO số PL02-NHA-DEMO có hiệu lực từ ngày 20/10/2026. Đợt 1 thanh toán 800.000.000 đồng."


def kcn_goc(model="DEMO-MODEL-KHONG-THAT"):
    """Đơn vị tiền giữ đúng nguồn #6 (`đồng`), profile chuyển qua alias có provenance."""
    return ket_qua("HD_THUE_DAT_DEMO_01.docx", [
        _p("TC-01", "Số hợp đồng", "HD-KCN-DEMO/01", "Hợp đồng số HD-KCN-DEMO/01", dieu="Phần đầu"),
        _p("TC-02", "Ngày ký", "01/09/2026", "ký ngày 01/09/2026", dieu="Phần đầu"),
        _p("TT-02", "Giá trị hợp đồng", "3.000.000.000", "Tổng tiền thuê đất là 3.000.000.000 đồng (chưa gồm VAT)", don_vi="đồng", dieu="Điều 3"),
        _p("KCN-01", "Diện tích", "10.000", "Diện tích thuê 10.000 m2", don_vi="m2", dieu="Điều 2"),
        _p("LT-COC-TIEN", "Tiền cọc", "300.000.000", "Bên thuê đặt cọc 300.000.000 đồng", don_vi="đồng", dieu="Điều 4"),
        _p("LT-COC-HAN", "Hạn cọc", "15/09/2026", "trước ngày 15/09/2026", dieu="Điều 4"),
        _p("LT-D1-TIEN", "Đợt 1", "1.200.000.000", "Đợt 1 thanh toán 1.200.000.000 đồng", don_vi="đồng", dieu="Điều 4"),
        _p("LT-D1-HAN", "Hạn đợt 1", "15/10/2026", "trước ngày 15/10/2026", dieu="Điều 4"),
        _p("LT-D2-TIEN", "Đợt 2", "1.500.000.000", "Đợt 2 thanh toán 1.500.000.000 đồng", don_vi="đồng", dieu="Điều 4"),
        _p("LT-D2-MOC", "Mốc đợt 2", "Bàn giao đất", "khi bàn giao đất", dieu="Điều 4"),
        # dòng mẫu optional của catalog nguồn chưa có giá trị: không phải nghĩa vụ thực
        {"ma": "LT-D3-TYLE", "nhom": "DEMO", "tham_so": "Đợt 3 (%)", "gia_tri": None, "don_vi": None, "dieu_khoan": None, "trich_dan": None,
         "ghi_chu": None, "kiem_tra": "THIẾU giá trị", "vi_tri_do_duoc": None},
    ], model=model)


def kcn_phu_luc(ngay_hieu_luc="01/10/2026"):
    vb = VB_KCN_PL.replace("01/10/2026", ngay_hieu_luc)
    return ket_qua("PL01_THUE_DAT_DEMO_01.docx", [
        _p("PL-01", "Số phụ lục", "PL01-KCN-DEMO", "PHỤ LỤC DEMO số PL01-KCN-DEMO"),
        _p("PL-02", "Ngày hiệu lực", ngay_hieu_luc, f"có hiệu lực từ ngày {ngay_hieu_luc}"),
        _p("LT-D2-HAN", "Hạn đợt 2", "20/12/2026", "Đợt 2 thanh toán trước ngày 20/12/2026"),
    ]), vb


def nha_goc():
    return ket_qua("HD_MUA_BAN_NHA_DEMO_07.docx", [
        _p("TC-01", "Số hợp đồng", "HD-NHA-DEMO/07", "Hợp đồng số HD-NHA-DEMO/07"),
        _p("TC-02", "Ngày ký", "05/09/2026", "ký ngày 05/09/2026"),
        _p("NO-01", "Mã căn", "A-12-DEMO", "Căn hộ A-12-DEMO"),
        _p("TT-02", "Giá bán", "2.000.000.000", "Giá bán 2.000.000.000 đồng chưa gồm VAT", don_vi="VND"),
        _p("LT-COC-TIEN", "Tiền cọc", "100.000.000", "Đặt cọc 100.000.000 đồng", don_vi="VND"),
        _p("LT-COC-HAN", "Hạn cọc", "10/09/2026", "trước ngày 10/09/2026"),
        _p("LT-D1-TIEN", "Đợt 1", "900.000.000", "Đợt 1 thanh toán 900.000.000 đồng", don_vi="VND"),
        _p("LT-D1-HAN", "Hạn đợt 1", "10/11/2026", "trước ngày 10/11/2026"),
        _p("LT-D2-TIEN", "Đợt 2", "1.000.000.000", "Đợt 2 thanh toán 1.000.000.000 đồng", don_vi="VND"),
        _p("LT-D2-MOC", "Mốc đợt 2", "Bàn giao căn hộ", "khi bàn giao căn hộ"),
    ])


def nha_phu_luc():
    return ket_qua("PL01_MUA_BAN_NHA_DEMO_07.docx", [
        _p("PL-01", "Số phụ lục", "PL01-NHA-DEMO", "PHỤ LỤC DEMO số PL01-NHA-DEMO"),
        _p("PL-02", "Ngày hiệu lực", "01/11/2026", "có hiệu lực từ ngày 01/11/2026"),
        _p("LT-D2-HAN", "Hạn đợt 2", "15/01/2027", "Đợt 2 thanh toán trước ngày 15/01/2027"),
    ])


def nha_phu_luc_mo_ho():
    """Phụ lục đổi số tiền đợt 1 (đợt đã thu một phần) mà không nêu cách chuyển nghĩa vụ — phải giữ chờ."""
    return ket_qua("PL02_MUA_BAN_NHA_DEMO_07.docx", [
        _p("PL-01", "Số phụ lục", "PL02-NHA-DEMO", "PHỤ LỤC DEMO số PL02-NHA-DEMO"),
        _p("PL-02", "Ngày hiệu lực", "20/10/2026", "có hiệu lực từ ngày 20/10/2026"),
        _p("LT-D1-TIEN", "Đợt 1", "800.000.000", "Đợt 1 thanh toán 800.000.000 đồng", don_vi="VND"),
    ])


def env(pn, loai_hinh, loai_ban, word, **kw):
    return {"namespace": "TRICH_6_DEMO", "phap_nhan": pn, "loai_hinh": loai_hinh, "loai_ban": loai_ban, "word_tham_chieu": "DEMO:" + word, **kw}


MAU = {
    "kcn_goc": (kcn_goc, VB_KCN, dict(pn="PN_DEMO_A", loai_hinh="DT-KCN-THUE-DAT-DEMO", loai_ban="GOC", word="HD_THUE_DAT_DEMO_01",
                                      ma_hop_dong_chung="HDC-KCN-DEMO-01", doi_tac_object_id="KH_DEMO.A01", du_an="DA_KCN_DEMO")),
    "kcn_phu_luc": (lambda: kcn_phu_luc()[0], VB_KCN_PL, dict(pn="PN_DEMO_A", loai_hinh="DT-KCN-THUE-DAT-DEMO", loai_ban="PHU_LUC",
                                                              word="PL01_THUE_DAT_DEMO_01", hop_dong_goc="HDC-KCN-DEMO-01")),
    "nha_goc": (nha_goc, VB_NHA, dict(pn="PN_DEMO_B", loai_hinh="DT-NHA-O-DEMO", loai_ban="GOC", word="HD_MUA_BAN_NHA_DEMO_07",
                                      ma_hop_dong_chung="HDC-NHA-DEMO-07", doi_tac_object_id="KH_DEMO.B01", du_an="DA_NHA_DEMO")),
    "nha_phu_luc": (nha_phu_luc, VB_NHA_PL, dict(pn="PN_DEMO_B", loai_hinh="DT-NHA-O-DEMO", loai_ban="PHU_LUC", word="PL01_MUA_BAN_NHA_DEMO_07",
                                                 hop_dong_goc="HDC-NHA-DEMO-07")),
    "nha_phu_luc_mo_ho": (nha_phu_luc_mo_ho, VB_NHA_PL_MO_HO, dict(pn="PN_DEMO_B", loai_hinh="DT-NHA-O-DEMO", loai_ban="PHU_LUC",
                                                                   word="PL02_MUA_BAN_NHA_DEMO_07", hop_dong_goc="HDC-NHA-DEMO-07")),
}


def mau(ten: str) -> tuple[bytes, dict, object]:
    """(raw bytes #6, envelope input, văn bản đối chiếu) của một mẫu DEMO."""
    fn, van_ban, e = MAU[ten]
    e = dict(e)
    return canonical_json(fn()).encode("utf-8"), env(e.pop("pn"), e.pop("loai_hinh"), e.pop("loai_ban"), e.pop("word"), **e), van_ban


# Sao kê M1 DEMO theo định dạng nguồn V12 (ktt-fixture-v1 / sao_ke) — đi qua Store.ingest + QuickPosting như M1 hiện có.
SAO_KE_M1 = {
    "PN_DEMO_A": {
        "truoc_hop_dong": [("DEMO-A-0001", "2026-08-25", 300_000_000, "DEMO CK DAT COC THUE DAT")],
        "sau_hop_dong": [("DEMO-A-0002", "2026-10-10", 500_000_000, "DEMO CK DOT 1 LAN 1"),
                         ("DEMO-A-0003", "2026-10-14", 900_000_000, "DEMO CK DOT 1 LAN 2 VA DOT 2")],
        "hop_dong_khac": [("DEMO-A-0004", "2026-10-16", 2_000_000_000, "DEMO CK HOP DONG KCN KHAC")],
    },
    "PN_DEMO_B": {
        "truoc_hop_dong": [("DEMO-B-0001", "2026-09-08", 100_000_000, "DEMO CK COC CAN HO")],
        "sau_hop_dong": [("DEMO-B-0002", "2026-10-05", 300_000_000, "DEMO CK DOT 1 MOT PHAN")],
    },
}
