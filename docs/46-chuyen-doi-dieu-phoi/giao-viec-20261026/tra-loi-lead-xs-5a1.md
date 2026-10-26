**Trả lời lead (Claude) cho XS-5a1 — làm theo, không hỏi lại (27/10 ~00:25):**

1. **Bảng dùng chung nhiều module → chủ bảng = `M0` (lõi).** Gồm:
   - `master.hop_dong`, `master.hop_dong_phien_ban`, `master.hop_dong_tham_so`, `master.lich_thu`;
   - kho chung `kho.chung_tu`, `kho.chung_tu_dong`, `kho.cong_no_mo`, `kho.tep_goc`, `kho.viec_can_duyet`, `kho.lien_ket_chung_tu`, `kho.lo_xuat*`, `kho.bien_nhan_thao_tac`, `kho.lien_ket_phan_bo`, `kho.dich_phan_bo_tien`, các bảng `kho.*` khác KK §2 ghi là "kho chung";
   - danh mục `master.*` (pháp nhân, đối tác, dự án, tài khoản…).
   - Mô hình hỗ trợ **"chủ theo dòng"** khai báo bằng cột phân biệt sẵn có: `master.hop_dong.module_chu` (QD-03: `module_chu IS NULL AND loai NOT IN ('VAY','MUA')` = CRM; `VAY` = M9; `module_chu='M4'` = M4), nguồn/loại chứng từ ở `kho.chung_tu`. Chỉ khai báo; không kiểm runtime ở lát này.
   - Ghi của CRM/M9/M1/M4 vào các bảng này → khai báo **"ghi chéo đang tồn tại — chuyển dần sang hàm M0/xương sống"** (cảnh báo, không đỏ), lấy đúng danh sách KK §3.
2. **Xương sống là chủ riêng `XUONG_SONG`** (không phải M0): `bus.*`, `viec.*`, `master.module_*`, `master.mtq_*`, `nhat_ky.*`, `bao_mat.mask_*`, cổng AI/OCR. Module dùng xương sống qua hàm (V2), không ghi bảng.
3. Không tự quyết thêm ngoài hai điểm trên; mục còn lại chưa rõ chủ → khai báo `CHUA_RO` kèm lý do (không đỏ), để lead chốt sau.
