"""XS-5a1 / CD-018: bản khai tĩnh theo KK-VUNG-DU-LIEU §2–3 (26/10).

Áp quyết định lead 27/10: bảng chung thuộc M0; XUONG_SONG là chủ riêng.
Dòng nguồn giữ nguyên bản kiểm kê, không phải số dòng tự cập nhật khi sửa mã.
Họ có * chỉ mô tả metadata, tuyệt đối không dùng làm GRANT wildcard.
V4 chưa có hợp đồng công bố thì ghi CHUA_CO, không giả API/sự kiện mới.
Không mở DB, không trace SQL, không kiểm điều kiện chủ theo dòng ở runtime.
"""

from ..ha_tang.khai_bao_module import (
    BangChuaRo, ChuTheoDong, DiemTruyCapDuLieu, DuLieuCongBo,
    KhaiBaoVungDuLieu, chu_bang, kiem_tra_vung_du_lieu,
)


def _bang(schema, ten):
    return tuple(f"{schema}.{t}" for t in ten.split())


def _diem(module, tep, muc, nhom, cac_dong):
    """Mỗi bảng trên cùng dòng là một điểm, đúng định nghĩa KK §1."""
    ly_do = ("ghi chéo đang tồn tại — chuyển dần sang hàm M0/xương sống" if muc == "GHI"
             else "đọc chéo đang tồn tại — cần chuyển dần sang nguồn công bố")
    return tuple(DiemTruyCapDuLieu(module, tep, dong, bang, muc, nhom, ly_do)
                 for dong, bang in cac_dong)


def _nhieu(dong, bang):
    return tuple((n, bang) for n in dong)


_CRM_DOC = (
    _diem("CRM", "k2/crm.py", "DOC", "CRM_M1",
          ((748, "kho.chung_tu"), (930, "kho.chung_tu"), (929, "kho.de_xuat")))
    + _diem("CRM", "k2/crm_s1.py", "DOC", "CRM_M1", _nhieu((225, 232), "kho.cong_no_mo"))
)
_M3_DOC = (
    _diem("M3", "k2/m3.py", "DOC", "M3_CRM_M2", (
        (259, "master.hop_dong_phien_ban"), (274, "kho.hoa_don_phien_ban"),
        (286, "kho.hoa_don_phien_ban"), (288, "kho.hoa_don_danh_tinh"), (290, "kho.hoa_don_quan_sat")))
    + _diem("M3", "k2/sql_m3.py", "DOC", "M3_CRM_M2", (
        (51, "master.hop_dong_phien_ban"), (105, "kho.hoa_don_danh_tinh"),
        (111, "kho.hoa_don_danh_tinh"), (109, "kho.hoa_don_phien_ban")))
)
_M9_DOC = _diem("M9", "k2/vay.py", "DOC", "M9_M1", _nhieu((588, 629, 712, 867, 923), "kho.chung_tu"))
_K2_DOC_M4 = (
    _diem("K2", "k2/sql_ghi_nhan_chung.py", "DOC", "K2_M4", (
        (184, "m4.dot_tep"), (184, "m4.tep"), (186, "m4.tham_so"),
        (188, "m4.phu_luc"), (190, "m4.boq"), (193, "m4.review_manual_map"), (197, "m4.chung_tu_manual_map"),
        (439, "m4.duyet_kt_cho"), (463, "m4.kt_xac_nhan"), (688, "m4.tep"), (693, "m4.nop"),
        (696, "m4.duyet_phien_ban"), (701, "m4.trich_xuat"), (704, "m4.xac_nhan_tham_so"),
        (709, "m4.chung_tu_revision"), (714, "m4.review_run"), (714, "m4.review_result"),
        (720, "m4.chung_tu_run"), (720, "m4.chung_tu_result"), (723, "m4.duyet_kt_cho"),
        (724, "m4.dot"), (725, "m4.ho_so_hop_dong"), (737, "m4.duyet_phien_ban"),
        (740, "m4.kt_xac_nhan"), (741, "m4.kt_xac_nhan"), (745, "m4.duyet_kt_cho"),
        (747, "m4.duyet_kt_phong_bi"), (748, "m4.duyet_seal"), (749, "m4.duyet_ket_luan"),
        (855, "m4.duyet_kt_cho"), (883, "m4.duyet_kt_cho"), (887, "m4.duyet_kt_phong_bi"),
        (888, "m4.duyet_seal"), (892, "m4.kt_xac_nhan"), (893, "m4.kt_xac_nhan")))
    + _diem("K2", "k2/sql_ghi_nhan_so_tien.py", "DOC", "K2_M4", (
        (162, "m4.duyet_kt_cho"), (167, "m4.dot"), (169, "m4.duyet_kt_phong_bi"), (170, "m4.kt_xac_nhan")))
)
_K2_DOC_M2 = (
    _diem("K2", "k2/sql_ghi_nhan_chung.py", "DOC", "K2_M2",
          _nhieu((586, 603, 624, 905, 996), "kho.hoa_don_danh_tinh") + (
              (910, "kho.hoa_don_quan_sat"), (911, "kho.hoa_don_phien_ban"),
              (914, "kho.hoa_don_dong_danh_tinh"), (920, "kho.hoa_don_dong_phien_ban")))
    + _diem("K2", "k2/sql_ghi_nhan_so_tien.py", "DOC", "K2_M2", (
        (196, "kho.hoa_don_danh_tinh"), (197, "kho.hoa_don_quan_sat"), (198, "kho.hoa_don_phien_ban")))
)
_CRM_GHI = (
    _diem("CRM", "k2/crm.py", "GHI", "CRM_CHUNG",
          ((123, "nhat_ky.su_kien"),)
          + _nhieu((152, 155, 159, 346, 430, 464, 609), "kho.viec_can_duyet")
          + ((252, "kho.tep_goc"),) + _nhieu((262, 462), "kho.chung_tu")
          + _nhieu((313, 556, 665), "master.hop_dong")
          + _nhieu((758, 795), "kho.lien_ket_chung_tu") + ((853, "kho.lo_xuat"),))
    + _diem("CRM", "k2/crm_giao_ket.py", "GHI", "CRM_CHUNG",
            _nhieu((886, 887), "master.cau_hinh") + _nhieu((890, 1122, 1133), "nhat_ky.su_kien"))
    + _diem("CRM", "k2/sql_crm_kiem_hd.py", "GHI", "CRM_CHUNG",
            _nhieu((1306, 1323, 1372, 1385, 1475, 1479), "kho.viec_can_duyet") + ((1437, "kho.chung_tu"),))
)
_M9_GHI = _diem("M9", "k2/vay.py", "GHI", "M9_CHUNG",
    _nhieu((54, 57, 489), "kho.viec_can_duyet") + _nhieu((173, 217), "master.anh_xa_nguon")
    + ((277, "kho.tep_goc"), (283, "giao_tiep.tep_tach_phap_nhan"))
    + _nhieu((350, 368, 534), "master.hop_dong") + ((551, "kho.chung_tu"),)
    + _nhieu((665, 700), "kho.lien_ket_chung_tu") + _nhieu((672, 698), "kho.lien_ket_phan_bo")
    + ((791, "kho.lo_xuat"),))
_M4_GHI = (
    _diem("M4", "m4/sql_m17.py", "GHI", "M4_M0", ((567, "master.hop_dong"),))
    + _diem("M4", "m4/sql_master_dung_chung.py", "GHI", "M4_M0", ((509, "master.hop_dong"),))
)
_M2_HO = (
    _diem("M2", "k2/hoa_don.py", "DOC", "CONG_HO", ((569, "kho.lien_ket_dong"),))
    + _diem("M2", "k2/nguon_chung.py", "GHI", "CONG_HO", ((210, "giao_tiep.stage_tin_cay"),))
)
_K2_HO = _diem("K2", "k2/lien_ket_chung.py", "GHI", "CONG_HO", ((42, "kho.bien_nhan_thao_tac"),))
_M3_HO = _diem("M3", "k2/sql_m3.py", "GHI", "CONG_HO", ((149, "nhat_ky.su_kien"),))
_XS_HO = (
    _diem("XUONG_SONG", "k2/ma_tran_tham_quyen.py", "GHI", "CONG_HO",
          ((366, "nhat_ky.mtq_thay_doi"), (399, "nhat_ky.mtq_tu_choi")))
    + _diem("XUONG_SONG", "ha_tang/ket_noi.py", "GHI", "CONG_HO", ((585, "nhat_ky.su_kien"),))
)


_CRM_BANG = _bang("master", """
    crm_danh_muc_truong crm_mau crm_mau_tep crm_mau_phien_ban crm_mau_anh_xa crm_mau_kiem_tra
    crm_bo_chuan crm_bo_chuan_phien_ban crm_bo_chuan_dong crm_g_bien_nhan
    crm_bao_gia crm_bao_gia_dieu_khoan crm_bao_gia_rev crm_hd_soan crm_hd_soan_rev
    crm_gk_xuat crm_gk_lan crm_ky_pham_vi crm_hd_ky crm_hd_ky_g5
    crm_da_ban crm_da_ban_phien_ban crm_da_ban_phi crm_da_ban_lo crm_da_ban_lo_ls crm_bo_chuan_ap_dung
    crm_da_moc crm_da_moc_ls crm_g5_dang_ky crm_g5_nguoi_chay crm_g5_thu_hoi crm_g5_viec
    crm_g5_y_dinh crm_g5_ket_qua crm_g5_su_kien crm_g5_kiem_tay
    crm_kiem_pham_vi crm_kiem_ho_so crm_kiem_rev crm_kiem_check crm_kiem_g5_nguon crm_kiem_g5_chinh_sach
    crm_kiem_g5_ket_qua crm_kiem_xu_ly_lech crm_kiem_quyet_dinh crm_kiem_hieu_luc
""")
_M2_BANG = _bang("kho", """
    hoa_don_danh_tinh hoa_don_phien_ban hoa_don_quan_sat hoa_don_dong_danh_tinh hoa_don_dong_phien_ban mua_dich_dong
""") + ("master.m2_ung_vien_dong",)
_M3_BANG = _bang("m3", "hop_dong_co_so hoa_don_hop_dong policy_hinh_thuc_doanh_thu")
_M4_BANG = _bang("m4", """
    danh_muc_tham_so danh_muc_ho_so_dot quyen_du_an tep ho_so_hop_dong trich_xuat tham_so tham_so_lich_su
    xac_nhan_tham_so phu_luc boq boq_dong dot dot_tep nop bien_nhan nhat_ky
    review_run review_result review_artifact review_manual_map review_giu_khoa
    chung_tu_run chung_tu_result chung_tu_artifact chung_tu_revision chung_tu_manual_map chung_tu_giu_khoa
    duyet_phien_ban duyet_ket_luan duyet_ket_luan_dong duyet_quyet_dinh duyet_pdf duyet_seal duyet_kt_cho duyet_kt_phong_bi
    kt_xac_nhan request_anh_xa request_y_dinh request_su_kien request_bien_nhan master_can_cu master_can_cu_phien_ban
    review_chep_nguon review_chep_hop_dong review_chep_che_do review_chep_tham_so review_chep_phu_luc
    review_chep_thay_doi_tham_so review_chep_boq_dong review_chep_dot_thanh_toan review_chep_kl_thanh_toan
    review_chep_khop_hang_muc review_chep_canh_bao review_chep_nhat_ky review_chep_tham_so_nguon
""")
_M9_BANG = _bang("master", "lich_tra_no vay_dinh_danh_nguon vay_phien_ban khe_uoc_vay khe_uoc_vay_phien_ban lai_suat_vay") + _bang("kho", "su_kien_vay su_kien_vay_phan")
_M0_BANG = _bang("master", """
    phap_nhan phap_nhan_boi_canh cau_hinh nguoi_dung phan_quyen nguon_tu_dong doi_tac doi_tac_ma_junsky
    doi_tac_dinh_danh tai_khoan_ngan_hang du_an ttcp khoan_muc_phi tai_khoan loai_hinh_doanh_thu hop_dong
    tai_san nhan_vien don_vi_tien nguon_instance nguon_profile nguon_pham_vi nang_luc_nguon nguon_master_noi_dung
    nguon_su_kien_do_luong anh_xa_nguon dinh_danh_cong_ty_nguon phan_cong_hanh_dong
    dinh_nghia_don_vi_luong tai_lieu_khai_bao_don_vi hop_dong_phien_ban hop_dong_tham_so lich_thu
""") + _bang("kho", """
    tep_goc chung_tu chung_tu_dong cong_no_mo phien khoa_ky de_xuat de_xuat_dong lien_ket_chung_tu viec_can_duyet
    cau_hoi tri_thuc nhan_hoc canh_bao bien_nhan_thao_tac lien_ket_phan_bo dich_phan_bo_tien
""") + ("kho.lo_xuat*",)


# Chỉ các trường hợp QD-03 đã chốt; không suy thêm owner cho MUA hay nguồn khác.
_CHU_DONG = (
    ChuTheoDong("master.hop_dong", ("module_chu", "loai"), "CRM", "module_chu IS NULL AND loai NOT IN ('VAY','MUA')"),
    ChuTheoDong("master.hop_dong", ("loai",), "M9", "loai = 'VAY'"),
    ChuTheoDong("master.hop_dong", ("module_chu",), "M4", "module_chu = 'M4'"),
    ChuTheoDong("kho.chung_tu", ("loai",), "M1", "loai = 'BANK'"),
    ChuTheoDong("kho.chung_tu", ("loai",), "M9", "loai = 'HO_SO_VAY'"),
)

# Mục KK còn lại chưa được lead phân chủ: giữ CHUA_RO, không coi là quyền ghi.
_LY_DO_K2 = "KK §2: quan hệ đối chiếu/L11 còn chờ lead phân chủ; không gán cho engine, M4 hay M0."
_LY_DO_NGUON = "KK §2: vùng tiếp nhận/snapshot nguồn chưa được lead chốt chủ."
CHUA_RO = tuple(BangChuaRo(b, _LY_DO_K2) for b in _bang("kho", """
    mua_nguon_kinh_te mua_nguon_kinh_te_phien_ban mua_nguon_phan mua_doi_chieu_can_cu
    mua_doi_chieu_can_cu_phien_ban mua_doi_chieu_can_cu_thanh_phan mua_doi_chieu_can_cu_nhat_ky
    mua_doi_chieu_can_cu_tap mua_doi_chieu_chung_thuc_khoa lien_ket_dong
""")) + tuple(BangChuaRo(b, _LY_DO_NGUON) for b in (
    _bang("giao_tiep", "tep_tiep_nhan stage_tin_cay lan_tiep_nhan_nguon ket_qua_cuoi_tiep_nhan tep_tach_phap_nhan")
    + _bang("kho", "anh_chup_nguon anh_chup_nguon_vai_tro ban_ghi_nguon")
)) + tuple(BangChuaRo(b, "KK §2: metadata chỉ quyền triển khai; chưa chốt chủ module.")
           for b in _bang("master", "schema_migrations he_thong migration_tuong_thich")) + tuple(
    BangChuaRo(b, "KK §2: lõi tương thích dùng search_path, chưa chốt schema/chủ; không suy từ cú pháp SQL.")
    for b in """
        knowledge_epoch knowledge_versions knowledge_events historical_links quality_runs
        knowledge_import_batches knowledge_workbooks knowledge_review_requests
        workspace_meta config_history artifacts attempts source_records staging documents issues audit_events
        document_lines evidence schema_migrations activity_log sessions proposals allocations review_workbooks review_imports
        decisions export_batches export_items expected_balances verification_runs field_verifications labels label_events
        learning_runs evaluation_datasets month_closures export_item_lines document_observations shadow_exports
        shadow_verification_runs quarantine_records quick_runs quick_items quick_learning cash_account_mappings
        bank_journal_matches quick_condition_learning export_counters quick_exports
    """.split()
)


_BUS = ("bus.phat", "bus.nhan", "bus.ack")
_NGUON = _bang("giao_tiep", "nguon_tim_lan_nhan nguon_tieu_thu_capture nguon_anh_xa_hien_hanh nguon_danh_sach_lan_nhan nguon_doc_tep")

CAC_VUNG_DU_LIEU = (
    KhaiBaoVungDuLieu(
        "CRM", "Hợp đồng & báo giá", v1=_CRM_BANG, v2=_BUS,
        v3=_bang("master", "phap_nhan doi_tac doi_tac_ma_junsky du_an loai_hinh_doanh_thu nguoi_dung phan_cong_hanh_dong"),
        v4=(DuLieuCongBo("M1", "Tiền BANK/công nợ có PN/quyền/version; sự kiện tiền đã nối; chưa có view/subscription."),),
        dang_ton_tai=_CRM_DOC + _CRM_GHI,
        v2_can_bo_sung=("file/chứng từ/master/duyệt/liên kết/xuất/audit/cấu hình chung",),
        ham_rieng=_bang("master", "crm_g_* crm_gk_* crm_ky_* crm_da_bat_ban crm_da_cap_nhat crm_da_doi_trang_thai crm_da_lo_ghi crm_da_anh_chup crm_da_moc_ghi crm_da_moc_doc crm_da_moc_ls_doc crm_g5_* crm_kiem_*"),
    ),
    KhaiBaoVungDuLieu(
        "M2", "Hóa đơn mua vào", v1=_M2_BANG, v2=_NGUON + _BUS,
        v3=_bang("master", "anh_xa_nguon phap_nhan nguon_profile nang_luc_nguon nguon_pham_vi dinh_nghia_don_vi_luong tai_lieu_khai_bao_don_vi"),
        v4=(DuLieuCongBo("CHUA_RO", "L11: kho.lien_ket_dong cần reader chung; chưa subscription M4."),),
        dang_ton_tai=_M2_HO,
        ham_rieng=_bang("kho", "m2_tieu_thu_quan_sat m2_mapping_cong_ty m2_mapping_dong m2_xem_xet_nguon m2_route"),
        v2_can_bo_sung=("writer stage chung", "reader L11 chung"),
        ghi_chu=("master.tai_lieu_khai_bao_don_vi không có SELECT app; V3 không tự cấp quyền.",
                 "kho.mua_dong_hien_hanh là security_invoker, chưa là hợp đồng công bố độc lập quyền bảng nguồn."),
    ),
    KhaiBaoVungDuLieu(
        "M3", "Hóa đơn bán ra & doanh thu BĐS", v1=_M3_BANG, v2=_BUS,
        v3=_bang("master", "phap_nhan hop_dong loai_hinh_doanh_thu"),
        v4=(DuLieuCongBo("CRM", "Phiên bản hợp đồng đã duyệt; chưa có nguồn công bố thay SQL thẳng."),
            DuLieuCongBo("M2", "Hóa đơn bán công bố; thiếu căn cứ tiếp tục PENDING."),
            DuLieuCongBo("M1", "Sự kiện tiền nối theo TL53 §4; chưa subscription.")),
        dang_ton_tai=_M3_DOC + _M3_HO,
        ham_rieng=_bang("m3", "co_so_kiem lien_ket_kiem policy_tai_ngay lien_ket_mot_xac_nhan ghi_nhat_ky"),
        v2_can_bo_sung=("writer audit chung thay INSERT trong m3.ghi_nhat_ky", "đưa tiện ích master.crm_g_bat_bien về lõi"),
        ghi_chu=("Chưa writer nghiệp vụ ứng dụng; web chỉ SELECT, V1 không tự cấp DML.",),
    ),
    KhaiBaoVungDuLieu(
        "M4", "Nghiệm thu & chi phí dự án", v1=_M4_BANG,
        v2=("kho.dc_luu", "kho.dc_xac_nhan") + _BUS,
        v3=_bang("master", "hop_dong du_an doi_tac doi_tac_ma_junsky phap_nhan nguoi_dung"),
        v4=(DuLieuCongBo("M2", "Hóa đơn công bố qua K2/XS-T1; chưa subscription."),),
        dang_ton_tai=_M4_GHI,
        ham_rieng=_bang("m4", "tao_hop_dong ghi_tep gan_tep_hop_dong ghi_trich_xuat sua_tham_so xac_nhan_tham_so khai_phu_luc them_phu_luc huy_phu_luc ghi_boq tao_dot sua_dot gan_tep_dot nop review_* chung_tu_* duyet_* kt_* request_* master_* nhan_master_hop_dong gan_doi_tac_hop_dong"),
        v2_can_bo_sung=("cổng master M0 cấp danh tính/gán đối tác",),
        ghi_chu=("Hàm m4.* là cổng riêng, không phải hàm xương sống; việc/duyệt m4.* chưa là XS-2 chung.",),
    ),
    KhaiBaoVungDuLieu(
        "M9", "Vốn vay & đầu tư tài chính", v1=_M9_BANG,
        v2=_bang("giao_tiep", "ghi_anh_chup gan_phap_nhan_theo_anh_xa cong_ty_chua_map")
            + _bang("kho", "l11_* luong_con_lai tien_con_lai dich_tien_con_lai") + _BUS,
        v3=_bang("master", "don_vi_tien doi_tac_ma_junsky du_an anh_xa_nguon phap_nhan"),
        v4=(DuLieuCongBo("M1", "BANK công bố; khóa/ngân sách qua cổng chung, giữ thứ tự khóa/proof encoding."),),
        dang_ton_tai=_M9_DOC + _M9_GHI,
        ham_rieng=_bang("master", "m9_chan m9_van_tay m9_phien_ban_hieu_luc"),
        v2_can_bo_sung=("file/master/duyệt/liên kết/xuất chung",),
        ghi_chu=("RAG/Sheet nhận index/snapshot/callback audit; chưa ghi PG, không tự gán bảng.",),
    ),
    KhaiBaoVungDuLieu(
        "M0", "Lõi", v1=_M0_BANG, v2=_BUS + ("master.mtq_quyet_dinh_phien",),
        v3=_bang("master", "phap_nhan nguoi_dung"), chu_theo_dong=_CHU_DONG,
        v2_can_bo_sung=("writer master/file/duyệt chung",),
        ghi_chu=("Chỉ các bảng kho chung được liệt kê, không nhận cả schema kho/master.",
                 "Quy tắc chủ theo dòng chỉ metadata; phần MUA/nguồn còn lại chưa chốt."),
    ),
    # K2 chỉ giữ danh sách seam/cổng, không nhận chủ bảng chưa được lead giao.
    KhaiBaoVungDuLieu(
        "K2", "Đối chiếu & liên kết chung", v2=("kho.dc_doc_hoa_don", "kho.dc_luu", "kho.dc_xac_nhan", "kho.l11_*"),
        v4=(DuLieuCongBo("M4", "Snapshot NT/đồ thị/phiên bản/seal, giữ chứng thực hiện hành."),
            DuLieuCongBo("M2", "Hóa đơn có ID/version/hash/PN/coverage/trạng thái nguồn; không thay thiếu tiền bằng 0.")),
        dang_ton_tai=_K2_DOC_M4 + _K2_DOC_M2 + _K2_HO,
    ),
    KhaiBaoVungDuLieu(
        "XUONG_SONG", "Xương sống",
        v1=("bus.*", "viec.*", "master.module_*", "master.mtq_*", "nhat_ky.*", "bao_mat.mask_*"),
        v2=_BUS + ("master.mtq_cau_hinh_ghi", "master.mtq_quyet_dinh_phien"),
        dang_ton_tai=_XS_HO,
        cong_ho_tro=("cổng AI", "cổng OCR"),
        ham_rieng=_BUS + _bang("master", "module_* mtq_bootstrap_admin mtq_cau_hinh_ghi mtq_quyet_dinh mtq_quyet_dinh_phien ktt_danh_tinh ktt_pn_cho_phep ktt_duoc ktt_co_vai"),
        ghi_chu=("Module chỉ dùng xương sống qua hàm; không nhận quyền ghi bảng/Mask.",
                 "Audit nội bộ gateway là writer dịch vụ; nhật ký không thay bus."),
    ),
)

DIEM_CHEO_DANG_TON_TAI = tuple(d for v in CAC_VUNG_DU_LIEU for d in v.dang_ton_tai)


def tra_ten_nghiep_vu(module: str) -> str:
    """Dùng được cho trang_thai_cho; chưa nối k2/module.py ở lát này."""
    for vung in CAC_VUNG_DU_LIEU:
        if vung.ma == module:
            return vung.ten_nghiep_vu
    return "dữ liệu từ chức năng nguồn"


def tra_chu_bang(bang: str) -> str:
    return chu_bang(bang, CAC_VUNG_DU_LIEU, CHUA_RO)


def kiem_tra_khai_bao(truy_cap=()):
    return kiem_tra_vung_du_lieu(CAC_VUNG_DU_LIEU, chua_ro=CHUA_RO, truy_cap=truy_cap)
