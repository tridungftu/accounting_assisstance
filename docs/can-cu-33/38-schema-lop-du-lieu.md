# 38 · Schema lớp dữ liệu — bảng, trường, khóa (thiết kế, chưa code)

**Ngày lập:** 16/10/2026 · **Trạng thái:** **ĐÃ CHỐT 16/10/2026 (chiều)** — anh trả lời 4 câu §9: danh mục Junsky ở master có phiên bản · sổ Junsky cùng bảng `chung_tu` · bí danh: tên pháp nhân trong `bao_mat`, KH/NCC dùng mã Junsky làm bí danh, MST/địa chỉ thành «MST_n»/«DC_n» · STK/CCCD lưu master mã hóa cột. Hàng đợi #29 → chờ lệnh code · **Vị trí trong kiến trúc:** K2 "Bóc tách → Lớp dữ liệu" (TL 35 §1, §3A) — hai kho + một nhật ký.
**Căn cứ:** TL 35 §3A (hai kho + nhật ký, Junsky cấp mã, trạng thái chứng từ), §3 (PostgreSQL, Mask, bối cảnh), §4 (khóa chung A1), §8.3 (nhiều pháp nhân); TL 36 (14 mục bối cảnh); TL 37 (cột dòng, 8 loại việc, hành động, máy trạng thái); TL 32 (`lien_ket_chung_tu`, CRM kế toán, loại hình doanh thu); TL 08 (37 cột `CB_tmpEntry2`); TL 12 §4 (mô hình tối thiểu cũ); `docs/QUYET-DINH.md` D01–D10 (point-in-time, khóa nguồn, raw bất biến); schema `kho.sqlite` V12 hiện có (50 bảng — ánh xạ ở §6).
**Sơ đồ quan hệ:** `38-schema-lop-du-lieu.drawio` (mở bằng draw.io) + `.png`/`.svg` + `.sinh-so-do.py` — `D:\Claude\Phan mem ho tro ke toan\`.
**Quy ước viết:** tên bảng/trường tiếng Việt không dấu, snake_case; trường tiền `*_minor` là số nguyên đơn vị nhỏ nhất kèm `tien_te` (VND scale 0; USD scale 2); `→` là khóa ngoại. Không có dữ liệu thật.

---

## 0. Mười nguyên tắc của schema

1. **`phap_nhan_id` trên mọi bảng** của cả bốn schema (trừ bảng dùng chung tập đoàn ghi `NULL` = chung: `doi_tac`, `tri_thuc` nhóm CFO/quy tắc chung, `cau_hinh` chung). Phân quyền = lọc theo cột này (TL 35 §8.3).
2. **Một CSDL PostgreSQL, bốn schema**: `master` (Kho 1 danh mục có phiên bản) · `kho` (Kho 2 chứng từ, đề xuất, liên kết, việc, tri thức, lô) · `nhat_ky` (chỉ INSERT) · `bao_mat` (bí danh Mask — chỉ cổng AI đọc).
3. **Khóa nội bộ + khóa nguồn**: mọi bảng có `id` (UUID) do hệ thống sinh; chứng từ có `khoa_nguon` duy nhất theo (pháp nhân, loại) để chống nhập trùng (D04: sao kê = mã tham chiếu NH + ngày + tiền + TK; hóa đơn = MST bán + ký hiệu + số; Base = ID RQ; sổ = số chứng từ Junsky). Ngày–tiền–tên chỉ để tìm ứng viên, không làm khóa.
4. **Junsky cấp mã, hệ thống giữ thông tin mở rộng**: mã Junsky (`object_id_junsky`, `ma_junsky`) là **thuộc tính** gắn vào bản ghi nội bộ, có ánh xạ theo pháp nhân; hệ thống không tự sinh mã Junsky (TL 35 §3A).
5. **Ba mốc thời gian** trên dữ liệu quan trọng (D09): `ngay_nghiep_vu` (business_date) · `nhan_luc` (known_at — lúc hệ thống biết) · `duyet_luc`/`eligible_at` (lúc đủ điều kiện dùng). Học và chấm điểm chỉ dùng bản ghi có `eligible_at ≤ mốc học`.
6. **Phiên bản thay cho sửa đè** ở master: `phien_ban`, `valid_from`, `valid_to`, `supersedes_id`, `nguoi_duyet`; bản cũ không xóa. Lịch thu đã khớp tiền giữ liên kết với phiên bản cũ (TL 32 §1.4).
7. **File gốc ngoài CSDL, bất biến**: `tep_goc` chỉ giữ đường dẫn + hash; dữ liệu bóc tách vào JSONB `du_lieu` kèm hash để phát hiện đổi (D02).
8. **Trạng thái nằm trên bản ghi gốc** (`chung_tu.trang_thai`, `viec_can_duyet.trang_thai`); **nhật ký là vết** (một dòng mỗi thao tác, có `truoc`/`sau`), không tính lại trạng thái từ nhật ký trong vận hành (TL 35 §3A; TL 37 §5.2).
9. **Kết quả LLM luôn ở trạng thái chờ duyệt, có trích dẫn**: `hop_dong_tham_so.trich_dan` bắt buộc; `de_xuat.nguon_suy_luan = LLM` ⇒ `muc ≤ VANG`; mỗi lượt gọi ghi `nhat_ky.cong_ai_goi` (TL 35 §3).
10. **Chỉ dòng đã đối chiếu khớp là nhãn học** (`nhan_hoc.trang_thai = du_dieu_kien`); Bỏ qua, Đã có Junsky, dòng lệch không học (TL 37 §5.2).

---

## 1. Sơ đồ tổng
Xem `38-schema-lop-du-lieu.png`: cột trái = `master` (16 bảng), cột giữa = `kho` (15 bảng), cột phải = `nhat_ky` (3 bảng) + `bao_mat` (1 bảng). Mũi tên = khóa ngoại chính; nét đứt = tham chiếu mềm theo loại (ví dụ `viec_can_duyet.tham_chieu` trỏ tới bảng khác nhau tùy loại việc).

---

## 2. Schema `master` — Kho 1 (9 danh mục TL 35 §3A + danh mục Junsky + người dùng + cấu hình)

| Bảng | Trường chính | Khóa / ràng buộc | Nguồn điền | Phiên bản / duyệt |
|---|---|---|---|---|
| `phap_nhan` | id · ma (PLHN) · ten · mst · ma_don_vi_junsky (02) · che_do_ke_toan (TT200) · nam_tai_chinh · tien_te · bi_danh_ai («PN_02») · moc_hoc · trang_thai | unique(ma); unique(ma_don_vi_junsky) | CFO | có |
| `phap_nhan_boi_canh` | id · phap_nhan_id → · phien_ban · muc (0–13 theo TL 36 §1) · noi_dung (text/JSONB) · gui_ai (bool) · nguon · nguoi_duyet · duyet_luc · valid_from/to | unique(phap_nhan_id, muc, phien_ban) | TL 36 | CFO_NTD |
| `doi_tac` | id · ten_phap_ly · ten_chuan_hoa (không dấu, bỏ viết tắt CT/CTCP/TNHH… — bảng D3 TL 25) · mst · cccd · loai (TC/CN/NHA_NUOC/NGAN_HANG/NOI_BO) · vai_tro[] (KH, NCC, NV, NH, NOI_BO) · trang_thai · phien_ban · ghi_chu | unique(mst) khi có; unique(cccd) khi có; **phap_nhan_id = NULL** (dùng chung tập đoàn) | danh mục Junsky + TL 19 danh bạ | kế toán; CFO với đối tác mới |
| `doi_tac_ma_junsky` | id · doi_tac_id → · phap_nhan_id → · object_id_junsky · tien_to (DVA1./NV./NH./331.…) · khoa · dong · valid_from/to | unique(phap_nhan_id, object_id_junsky) | danh mục Junsky từng cơ sở | tự nạp; thay đổi có phiên bản |
| `doi_tac_dinh_danh` | id · doi_tac_id → · loai (STK/MST/CCCD/BIEN_SO/TEN_BI_DANH/SO_HD/TEN_CHU_TK) · gia_tri (chuẩn hóa) · nguon (sao_ke/base/hoa_don/so/anh_duyet) · do_tin_cay (CAO/TB/THAP) · lan_gap · xung_dot (bool) · valid_from/to · nguoi_duyet | unique(loai, gia_tri) toàn tập đoàn — một STK không thuộc hai đối tác (TL 19) | quy tắc STK 25/09 | kế toán (CFO với STK mới) |
| `tai_khoan_ngan_hang` | id · phap_nhan_id → · ngan_hang · chi_nhanh · stk (xem §9 câu 4) · tk_ke_toan (112111…) · bank_id_junsky · tien_te · co_sao_ke (bool) · nguon_sao_ke | unique(phap_nhan_id, tk_ke_toan) | `cash_account_mappings` V12 + danh mục BankID (chờ NCC Junsky) | kế toán trưởng |
| `du_an` | id · phap_nhan_id → · ma_junsky (KCN-DVI0/1/2) · ten · cha_id → · giai_doan · trang_thai (DAU_TU/VAN_HANH) · ngay_chuyen_van_hanh · valid_from/to | unique(phap_nhan_id, ma_junsky) | danh mục Junsky | kế toán trưởng (mốc chuyển: CFO) |
| `ttcp` · `khoan_muc_phi` · `tai_khoan` | cùng mẫu: id · phap_nhan_id (NULL = chung tập đoàn, vì danh mục Junsky dùng chung — TL 36 §2.3) · ma_junsky · ten · nhom · du_an_id → (ttcp) · tk_cong_no (bool, tai_khoan) · cap · valid_from/to | unique(ma_junsky, phap_nhan_id) | danh mục Junsky | tự nạp; `tk_cong_no` CFO xác nhận (= `DEBT_ACCOUNTS`) |
| `loai_hinh_doanh_thu` | id · phap_nhan_id → · ma (DT-KCN-DAT…) · ten · cau_hinh (JSONB: bộ tham số, mẫu bút toán, đáp án mẫu — TL 32) · tk_cong_no · tk_dt_chua_th · tk_doanh_thu · tk_gia_von · phien_ban · valid_from/to | unique(phap_nhan_id, ma, phien_ban) | TL 36 §2.4 | CFO |
| `hop_dong` | id · phap_nhan_id → · loai (XAY_DUNG/THUE_DAT/BAN_NHA/VAY/MUA/DICH_VU) · ma_noi_bo · so_hop_dong · doi_tac_id → · du_an_id → · loai_hinh_dt_id → · ngay_ky · gia_tri_minor · tien_te · trang_thai · phien_ban_hien_hanh → | unique(phap_nhan_id, loai, so_hop_dong); **một mã dùng chung với #5 và #9** (TL 35 §4) | #5 (xây dựng), #6 (thuê đất/bán), #9 Sheet (vay) | theo §9 câu 2 → CFO duyệt tham số |
| `hop_dong_phien_ban` | id · hop_dong_id → · phien_ban · loai (GOC/PHU_LUC) · so_phu_luc · ngay · tham_so (JSONB) · tep_goc_id → · nguon (LLM/#5/#6/SHEET/TAY) · trang_thai (CHO_DUYET/DA_DUYET/TU_CHOI) · nguoi_duyet · duyet_luc · valid_from/to | unique(hop_dong_id, phien_ban) | K2 bóc tách | CFO (chốt 16/10) |
| `hop_dong_tham_so` | id · phien_ban_id → · ten · gia_tri · don_vi · **trich_dan** · trang · do_tin_cay · nguon | check: nguon = LLM ⇒ trich_dan not null | K2 | cùng phiên bản |
| `lich_thu` · `lich_tra_no` | id · phien_ban_id → · dot/ky · moc (KY/XAY_XONG/BAN_GIAO/SO/THANG) · ty_le · so_tien_minor · tien_te · han · loai (COC/DOT/PHI_KY/GOC/LAI) · trang_thai (CHUA_THU/DA_THU/MOT_PHAN/QUA_HAN) · da_thu_minor | unique(phien_ban_id, dot) | sinh từ tham số | theo phiên bản |
| `tai_san` | id · phap_nhan_id → · ma_junsky · ten · loai (TSCD/CCDC/BDSDT) · nguyen_gia_minor · ngay_su_dung · bo_phan · du_an_id → · nguon_241 (chung_tu_id) · trang_thai · valid_from/to | unique(phap_nhan_id, ma_junsky) | bảng khấu hao Excel + hóa đơn (M6) | kế toán TSCĐ |
| `nhan_vien` | id · phap_nhan_id → · ma_junsky (NV.…) · ten · bo_phan · zalo_id · da_quet_qr · vai_tro_tra_loi (KINH_DOANH/MUA_HANG/QLDA/THU_KHO…) · trang_thai · (stk, cccd: xem §9 câu 4) | unique(phap_nhan_id, ma_junsky) | HR / danh mục Junsky | kế toán |
| `nguoi_dung` · `phan_quyen` | nguoi_dung: id · ten · dang_nhap · vai_tro (KE_TOAN/KE_TOAN_TRUONG/CFO/NHAP_JUNSKY/XEM); phan_quyen: nguoi_dung_id → · phap_nhan_id → · duyet_loai_viec[] (V1–V8) | unique(nguoi_dung_id, phap_nhan_id) | CFO | — |
| `cau_hinh` | khoa · phap_nhan_id (NULL = chung) · gia_tri (JSONB) · mo_ta · valid_from/to · nguoi_duyet | unique(khoa, phap_nhan_id, valid_from) | ngưỡng, `DEBT_ACCOUNTS`, loại việc tự hỏi, hạn Zalo, cổng AI (loại chứng từ được gửi, model theo loại việc) | CFO |
| `nguon_tu_dong` | id · phap_nhan_id → · loai (#7 HOA_DON/#8 BASE/#5 REVIEW/#9 SHEET_VAY/THU_MUC_SAO_KE) · cau_hinh (JSONB: đường dẫn/API, không chứa khóa — khóa ở `.env`) · lich · lan_cuoi · so_moi · trang_thai | unique(phap_nhan_id, loai) | TL 31 | kế toán |

---

## 3. Schema `kho` — Kho 2 (chứng từ mọi trạng thái, đề xuất, liên kết, việc, tri thức, lô)

| Bảng | Trường chính | Khóa / ràng buộc | Ghi chú |
|---|---|---|---|
| `tep_goc` | id · phap_nhan_id → · loai_nguon · duong_dan (ngoài CSDL) · hash · kich_thuoc · nhan_luc · nguon (TAY / nguon_tu_dong_id →) · nguoi | unique(hash) | thay `artifacts` + `source_records`; file không bao giờ sửa |
| `chung_tu` | id · phap_nhan_id → · loai (SAO_KE/HD_MUA/HD_BAN/BANG_KE_THUE/RQ/NGHIEM_THU/HOP_DONG_TEP/BANG_LUONG/BANG_KHAU_HAO/PHIEU_KHO/LENH_CHI/**SO_JUNSKY**/**CONG_NO_MO**/BUT_TOAN_DIEU_CHINH) · khoa_nguon · ngay_nghiep_vu · nhan_luc · tien_te · so_tien_minor · chieu (THU/CHI) · doi_tac_id → · doi_tac_tho (text) · du_an_id → · mo_ta · du_lieu (JSONB bóc tách) · hash · tep_goc_id → · ky · **trang_thai** (DANG_XU_LY/CHO_DUYET/DANG_HOI/CHO_BO_SUNG/DA_DUYET/DA_XUAT/DA_NAP/DA_DOI_CHIEU/BO_QUA/DA_CO_JUNSKY) · voucher_type (sổ Junsky: BR/BP/GJ/SI/PI/IE/FA/FC/CR/CP) · so_chung_tu_junsky | unique(phap_nhan_id, loai, khoa_nguon); check trạng thái chuyển đúng máy trạng thái TL 37 §5.2 (trigger) | thay `documents`; **chứng từ kỳ hiện tại và sổ quá khứ cùng bảng** (anh chốt 16/10) |
| `chung_tu_dong` | id · chung_tu_id → · stt · mo_ta · so_luong · don_gia_minor · tien_truoc_thue_minor · thue_suat · tien_thue_minor · tai_khoan · no_minor · co_minor · doi_tac_id → · du_an_id → · ttcp · khoan_muc · **dich** (CHI_PHI/241/TAI_SAN/KHO — nguyên tắc 2 TL 32) · du_lieu (JSONB) | unique(chung_tu_id, stt) | thay `document_lines` |
| `cong_no_mo` | id · phap_nhan_id → · ngay_chup · tai_khoan · doi_tac_id → · item_key (khóa Junsky) · loai (UNBILLED/INVOICE) · so_tien_minor · con_lai_minor · tien_te · hoa_don_ref · du_an_id → · ngay_chung_tu · ngay_hoa_don | unique(phap_nhan_id, ngay_chup, item_key) | ảnh chụp dgbList trước mỗi phiên (TL 12 §4.1, bậc 0 TL 07); không ghi đè ảnh cũ |
| `de_xuat` | id · chung_tu_id → · phien_ban · hien_hanh (bool) · chu_trinh (M1–M10) · nhan_nghiep_vu · dich · muc (XANH/VANG/DO) · vi_sao · so_do (JSONB: n/n, m tháng, độ ổn định) · can_cu (JSONB: id chứng từ cũ, tri_thuc_id) · phuong_an (JSONB[]) · nguon_suy_luan (KHOA_CUNG/TU_KHOA/LICH_SU/CONG_NO/CFO/LLM/NGUOI) · cong_ai_goi_id → · tao_luc · tao_boi | unique(chung_tu_id, phien_ban); check nguon = LLM ⇒ muc ≠ XANH | thay `proposals` + `quick_items.proposal_json`; Đề xuất lại = phiên bản mới |
| `de_xuat_dong` | id · de_xuat_id → · offset · no_co · acct_id · bank_id · orgl_id · orgl_rate · orgl_deb/crd · base_deb/crd (minor) · object_id_junsky · entry_dm · cashflow_id · precost_id · project_id · center_id · cost_id · remark · vat_id · vat_acct_id · base_bef_vat · base_amt_vat · inv_name/addr/code/form/seri/no/date/mode/text/look | tên trường **theo đúng 37 cột `CB_tmpEntry2`** (TL 08) để xuất không phải ánh xạ; check Σbase_deb = Σbase_crd khi Đồng ý | thay `export_item_lines` |
| `lien_ket_chung_tu` | id · phap_nhan_id → · chung_tu_a_id → · chung_tu_b_id → · loai (TIEN_CONG_NO/HD_NGHIEM_THU/HOP_DONG_DOT_TIEN/HD_TAI_SAN/241_TAI_SAN/NHIEU_LAN_CHUYEN/HD_RQ/HD_PHIEU_KHO) · so_tien_khop_minor · trang_thai (CHO/DA_KHOP/HUY) · nguon_suy_luan · do_tin_cay · nguoi_duyet · duyet_luc · entry_dm | unique(chung_tu_a_id, chung_tu_b_id, loai); check a ≠ b | thay `bank_journal_matches`, `allocations`, `historical_links` (TL 32 nguyên tắc 3) |
| `viec_can_duyet` | id · phap_nhan_id → · loai (V1…V8) · chu_trinh · tham_chieu_bang · tham_chieu_id · muc · **trang_thai** (CHO_DUYET/DANG_HOI/CHO_BO_SUNG/DA_DUYET/BO_QUA/DONG) · nguoi_phu_trach → (nhan_vien) · nguoi_duyet_vai_tro · han · ngay_ton · uu_tien · tom_tat · so_tien_minor · tien_te · tao_luc · cap_nhat_luc | unique(tham_chieu_bang, tham_chieu_id) khi còn mở | mỗi dòng màn hình K5 = một bản ghi; trạng thái chứng từ đồng bộ bằng trigger |
| `cau_hoi` | id · phap_nhan_id → · viec_id → · kenh (ZALO) · nguoi_nhan → (nhan_vien) · noi_dung · phuong_an (JSONB[]) · gui_luc · han · tu_dong (bool) · loai_tu_dong · trang_thai (DA_GUI/DA_TRA_LOI/QUA_HAN/NHAC_LAI/TU_QUYET) · tra_loi_tho · phuong_an_chon · tra_loi_luc · cong_ai_goi_id → | — | TL 37 §7; nội dung gửi đi **không chứa STK/MST** |
| `tri_thuc` | id · phap_nhan_id (NULL = chung) · nhom (DINH_DANH/TU_KHOA/KHOA_CUNG/MAU_LICH_SU/CFO/DAP_AN_MAU/ANH_XA_NHOM_G/LOAI_HINH_DT/BOI_CANH) · khoa_logic · phien_ban · noi_dung (JSONB) · bang_chung (JSONB) · so_do (lan_gap, nhat_quan) · trang_thai (NHAP/CHO_DUYET/DA_DUYET/THU_HOI) · actor · valid_from/to · known_at · supersedes_id → | unique(nhom, khoa_logic, phien_ban) | thay `knowledge_versions`; tri thức CFO vẫn nạp từ `TRI-THUC-CFO.json` vào đây với actor `CFO_NTD` |
| `nhan_hoc` | id · chung_tu_id → · de_xuat_id → (bản cuối) · trang_thai (DU_DIEU_KIEN/NGOAI_LE/BI_THAY_THE) · ly_do · business_date · known_at · eligible_at | unique(chung_tu_id) hiệu lực | thay `labels`; chỉ ghi khi `DA_DOI_CHIEU` khớp |
| `lo_xuat` · `lo_xuat_dong` | lo: id · phap_nhan_id → · ky · ma_lo (PLHN-2608-01) · loai (FILE_SOAT/JUNSKY_THU/JUNSKY_CHI) · duong_dan · hash · so_dong · tong_no/co_minor · tien_te · trang_thai (DA_XUAT/DA_NAP/DA_DOI_CHIEU/HUY) · nguoi · xuat_luc · nap_luc · nguoi_nap; dong: lo_id → · de_xuat_id → · entry_id_junsky · doi_chieu (KHOP/LECH_GIA_TRI/THIEU_JUNSKY/THUA_JUNSKY) · chenh_minh_hoa | unique(ma_lo); de_xuat chỉ thuộc một lô JUNSKY | thay `export_batches/items`; 4 nhóm đối chiếu (TL 02) |
| `khoa_ky` · `phien` | khoa_ky: phap_nhan_id → · ky · khoa_luc · nguoi · bang_chung; phien: id · phap_nhan_id → · mode (THAT/THU/CHAM_DIEM) · cutoff · snapshot_cong_no_id → · opened/closed · actor | PK(phap_nhan_id, ky) | thay `month_closures`, `sessions` |
| `canh_bao` | id · phap_nhan_id → · ma · muc · thong_diep · viec_can_lam · man_hinh_xu_ly · trang_thai · tao_luc | — | thay `issues`, `quarantine_records` (việc V8) |

---

## 4. Schema `nhat_ky` — chỉ INSERT (thu hồi quyền UPDATE/DELETE ở mức CSDL)

| Bảng | Trường chính | Ghi chú |
|---|---|---|
| `su_kien` | id · phap_nhan_id → · luc · nguoi (actor) · phien_id → · loai (QUYET_DINH/SUA_DANH_MUC/PHU_LUC/TRI_THUC/LO/DIEU_CHINH/HE_THONG/NGUON_TU_DONG) · doi_tuong_bang · doi_tuong_id · hanh_dong (DONG_Y/SUA/HOI/YEU_CAU_BO_SUNG/BO_QUA/HOAN_TAC/DUYET_LAI/DOI_DICH/XAC_NHAN_LK/GO_LK/DA_NAP/XU_LY_LECH/DUYET_TRI_THUC/TU_DUYET_THEO_LOAI…) · **truoc** (JSONB) · **sau** (JSONB) · ly_do · can_cu (JSONB) · ghi_nho (bool) | thay `decisions`, `label_events`, `knowledge_events`, `activity_log`, `audit_events`; một chỗ tra mọi vết; `truoc/sau` là bản chụp bản ghi |
| `cong_ai_goi` | id · phap_nhan_id → · luc · loai_viec · model · nha_cung_cap · cloud (bool) · dau_vao_mask_hash · token_vao · token_ra · chi_phi_uoc · ket_qua_tom_tat · trich_dan_hop_le (bool) · viec_id → · de_xuat_id → · thoi_gian_ms · loi | nội dung đã Mask lưu file ngoài CSDL theo hash (đối chiếu khi cần); là số đo để cắm Jev Router sau (TL 35 §3) |
| `tin_zalo` | id · luc · chieu (GUI/NHAN) · zalo_id · noi_dung · cau_hoi_id → · trang_thai_gui | thô, để kiểm toán agent |

## 4b. Schema `bao_mat` — chỉ vai trò `cong_ai` đọc được

| Bảng | Trường chính | Ghi chú |
|---|---|---|
| `mask_bi_danh` | id · phap_nhan_id → · loai (TEN_PHAP_NHAN/TEN_KHU/MST/DIA_CHI/STK/CCCD/SO_HD/TIEN) · gia_tri_that (**mã hóa cột**) · bi_danh («PN_02», «KCN_1», «MST_017», «DC_017», «STK_4», «TIỀN_3»…) · tao_luc · dung_lan_cuoi | unique(loai, gia_tri_that); bí danh nhất quán, đảo ngược được (TL 35 §3; TL 36 §3). **Anh chốt 16/10:** tên pháp nhân → bí danh trong bảng này; **tên khách hàng / nhà cung cấp → dùng chính mã đối tượng Junsky** (`doi_tac_ma_junsky.object_id_junsky`) làm bí danh, không cần bản ghi riêng (đảo ngược qua master); **MST → «MST_n», địa chỉ → «DC_n»** để AI vẫn nhận diện được cùng một đối tác. Lưu ý đã nêu: mã Junsky có thể chứa chữ viết tắt tên (tiền tố + vài chữ cái) — anh chấp nhận; nếu sau này cần siết thì chuyển sang bí danh số, không đổi schema |

---

## 5. Khóa chung (A1 — TL 35 §4) nằm ở đâu

| Khóa chung | Bảng · cột |
|---|---|
| Mã đối tượng Junsky (+ MST/CCCD, STK) | `doi_tac_ma_junsky.object_id_junsky` · `doi_tac.mst/cccd` · `doi_tac_dinh_danh` (STK) |
| Số hóa đơn (ký hiệu + số + MST bán) | `chung_tu.khoa_nguon` (loại HD_MUA/HD_BAN) |
| Mã hợp đồng (thầu / mua bán / thuê / vay — dùng chung #5, #9) | `hop_dong.ma_noi_bo` + `so_hop_dong` |
| Mã dự án · giai đoạn · hạng mục | `du_an.ma_junsky`, `du_an.cha_id`, `ttcp` |
| Mã tài sản | `tai_san.ma_junsky` |
| Mã RQ | `chung_tu.khoa_nguon` (loại RQ) |
| Mã chứng từ công nợ (`EntryDM`) | `de_xuat_dong.entry_dm` ← `lien_ket_chung_tu.entry_dm` |
| Mã lô đẩy + mã bút toán nguồn | `lo_xuat.ma_lo` · `lo_xuat_dong.de_xuat_id` · `entry_id_junsky` |
| Mã pháp nhân | `phap_nhan.ma` → `phap_nhan_id` mọi bảng |

---

## 6. Ánh xạ `kho.sqlite` V12 (50 bảng) → schema mới

| V12 (SQLite) | Mới (PostgreSQL) | Cách chuyển |
|---|---|---|
| `documents` (8.121: JOURNAL, COUNTERPARTY, OPEN_ITEM, BANK, ACCOUNT, EXPENSE, COST_CENTER, PROJECT) | JOURNAL/BANK → `kho.chung_tu` (SO_JUNSKY / SAO_KE); OPEN_ITEM → `kho.cong_no_mo`; COUNTERPARTY → `master.doi_tac` + `doi_tac_ma_junsky`; ACCOUNT/EXPENSE/COST_CENTER/PROJECT → `master.tai_khoan/khoan_muc_phi/ttcp/du_an` | bộ chuyển một lần, giữ `natural_key` → `khoa_nguon` |
| `document_lines` (20.382) | `kho.chung_tu_dong` | 1–1 |
| `source_records` · `artifacts` · `staging` · `evidence` | `kho.tep_goc` + `chung_tu.tep_goc_id/nhan_luc` | hash giữ nguyên |
| `knowledge_versions` (7.848) · `knowledge_events` (3.714) · `knowledge_workbooks/import_batches/review_requests` | `kho.tri_thuc` + `nhat_ky.su_kien` (loai TRI_THUC) | category → nhom |
| `quick_runs` · `quick_items` (105) · `proposals` | `kho.phien` · `kho.de_xuat` + `de_xuat_dong` · `kho.viec_can_duyet` (V1) | `proposal_json` tách thành dòng |
| `decisions` · `quick_items.decision_*` · `label_events` · `activity_log` (11.568) · `audit_events` | `nhat_ky.su_kien` | append |
| `bank_journal_matches` · `allocations` · `historical_links` | `kho.lien_ket_chung_tu` | loại TIEN_CONG_NO / NHIEU_LAN_CHUYEN |
| `export_batches` · `export_items` · `export_item_lines` · `shadow_*` · `quick_exports` | `kho.lo_xuat` · `lo_xuat_dong` (dòng bút toán đã ở `de_xuat_dong`) | — |
| `labels` · `quick_learning` · `learning_runs` · `evaluation_datasets` · `quality_runs` | `kho.nhan_hoc` · `tri_thuc` nhóm DAP_AN_MAU · bảng chấm điểm giữ nguyên tên | — |
| `sessions` · `month_closures` · `knowledge_epoch` | `kho.phien` · `khoa_ky` · `phap_nhan.moc_hoc` | — |
| `cash_account_mappings` | `master.tai_khoan_ngan_hang` | — |
| `issues` · `quarantine_records` | `kho.canh_bao` (V8) | — |
| `config_history` · `workspace_meta` · `schema_migrations` | `master.cau_hinh` · bảng hệ thống giữ | — |
| `quick_items.ai_note` | `kho.viec_can_duyet` + `su_kien` loai GHI_CHU_AI | — |

Bộ chuyển chạy **một lần** khi bắt đầu K2 (hàng đợi #23/#26); V12 SQLite giữ làm sao lưu chỉ đọc.

---

## 7. Ràng buộc và quy tắc cài ở mức CSDL (không phụ thuộc màn hình)
1. Mọi bảng (trừ dùng chung) `phap_nhan_id NOT NULL`; chính sách hàng (row-level security) theo `phan_quyen`.
2. `nhat_ky.*`: thu hồi UPDATE/DELETE với mọi vai trò ứng dụng.
3. `chung_tu.trang_thai` chỉ đổi theo máy trạng thái TL 37 §5.2 (trigger từ chối chuyển trái phép; sau DA_XUAT chỉ được sang DA_NAP/DA_DOI_CHIEU).
4. Đồng ý một `de_xuat`: Σ`base_deb` = Σ`base_crd` > 0; mọi `acct_id` là TK chi tiết (`tai_khoan.cap` cao nhất); `acct_id ∈ DEBT_ACCOUNTS` ⇒ `object_id_junsky NOT NULL`; `ky` chưa khóa (`khoa_ky`).
5. `hop_dong_tham_so`: `nguon = LLM` ⇒ `trich_dan NOT NULL`; không trích dẫn → giá trị `NULL` ("Không quy định").
6. `de_xuat.nguon_suy_luan = LLM` ⇒ `muc ∈ {VANG, DO}`.
7. `doi_tac_dinh_danh` loại STK: unique toàn tập đoàn; sinh tự động chỉ khi `lan_gap ≥ 2` nhất quán hoặc cặp cùng ngày (TL 25 D2).
8. `nhan_hoc`: chỉ INSERT khi `chung_tu.trang_thai = DA_DOI_CHIEU` và `lo_xuat_dong.doi_chieu = KHOP`; học/chấm điểm lọc `eligible_at ≤ phap_nhan.moc_hoc` (khi chấm) — chống rò rỉ hồi cứu.
9. `lo_xuat_dong`: một `de_xuat` chỉ thuộc một lô JUNSKY; sửa sau khi xuất = `chung_tu` loại BUT_TOAN_DIEU_CHINH mới + liên kết tới bản gốc.
10. Tự duyệt theo loại (phí NH, lãi TG, lương, định kỳ): cờ trong `cau_hinh`, chỉ có hiệu lực khi `cau_hinh.muc_2_mo = true`; mỗi lần ghi `su_kien` hanh_dong TU_DUYET_THEO_LOAI.

---

## 8. Kích thước và vận hành (từ số đếm PLHN — TL 36)
- Sổ 09/2024–06/2026: 4.222 chứng từ / 20.382 dòng; đối tác 2.027; công nợ mở 1.581; tri thức 7.848 phiên bản; sao kê ~105 dòng/tháng; hóa đơn ~110/tháng; RQ ~150/tháng. Hai pháp nhân × 5 năm vẫn dưới vài trăm nghìn dòng → PostgreSQL trên máy anh đủ; không cần phân mảnh.
- Mở rộng dùng: `unaccent`, `pg_trgm` (so tên không dấu, viết tắt — H12 TL 25), JSONB (dữ liệu bóc tách, tham số, trước/sau), `pgvector` để sau (tìm chứng từ tương tự thay ngưỡng giống 0,8).
- Sao lưu: `pg_dump` theo lịch vào `var\sao-luu\`; `tep_goc` sao lưu cùng; chuyển máy chủ nội bộ = phục hồi bản dump (TL 35 §3).

---

## 9. Điểm cần anh chốt

**Đã chốt 16/10/2026 (chiều) — bảng chọn:**
1. **Danh mục Junsky ở master, có phiên bản** (mỗi lần nạp = phiên bản mới, valid_from/to).
2. **Sổ Junsky cùng bảng `chung_tu`**, loại SO_JUNSKY (một khóa, một bảng liên kết, một cơ chế đối chiếu).
3. **Bí danh Mask**: tên pháp nhân → `bao_mat.mask_bi_danh`; **khách hàng / nhà cung cấp → mã đối tượng Junsky** làm bí danh; **MST → «MST_n», địa chỉ → «DC_n»** (địa chỉ bổ sung vào danh sách Mask — nay là **bảy thứ**: tên, MST, địa chỉ, số tiền, STK, CCCD, số hợp đồng; tên khu → «KCN_1»).
4. **STK/CCCD nhân viên và STK đối tác lưu trong master, mã hóa cột** (pgcrypto); không bao giờ ra cloud.

**Trả lời sau / kỹ thuật (Claude tự quyết, báo lại):** kiểu khóa UUID; đặt tên schema/bảng tiếng Việt không dấu như trên; cách mã hóa cột (pgcrypto); row-level security hay lọc ở ứng dụng; chỉ mục pg_trgm trên `ten_chuan_hoa`.

## 10. Sau khi chốt
- Hàng đợi #29 "schema lớp dữ liệu" → trạng thái "chờ lệnh code"; #23/#24/#26 nhận điều kiện "theo TL 38".
- Thứ tự khi anh ra lệnh code (một V riêng cho xương sống, review độc lập cuối V): cài PostgreSQL trên máy anh (#26) → tạo 4 schema + migration có số phiên bản → **bộ chuyển kho.sqlite → PostgreSQL** (chạy thử trên bản sao, so số đếm trước/sau: 4.222 chứng từ, 20.382 dòng, 2.027 đối tác, 1.581 công nợ, 7.848 tri thức) → nối V12 đọc từ PostgreSQL (kết quả đề xuất phải trùng V12 trên T8: 105 dòng) → mới mở K3 và màn hình K5.
- Tài liệu 36 §1 (14 mục) ánh xạ vào `phap_nhan_boi_canh.muc`; tài liệu 37 §3 cột ↔ `viec_can_duyet`; TL 08 cột ↔ `de_xuat_dong`.
