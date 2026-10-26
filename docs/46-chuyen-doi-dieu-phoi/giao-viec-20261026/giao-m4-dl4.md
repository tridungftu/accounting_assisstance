# M4-DL4: M4 · Nghiệm thu & chi phí dự án, lớp đọc/ghi đợt thanh toán, khối lượng, ghép hạng mục, cảnh báo, nhật ký legacy chép từ Review (CD-011, lát 4 theo kiểm kê)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn và ghi "Cần Anh".
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server hay PostgreSQL. Không xóa file.
- Test PG tự tạo CSDL `kho_test_*` riêng từ DSN quản trị như `tests/test_m4_review_data_pg.py`; **không** đọc biến `KHO_PG_DEMO_*`, **không** đòi DSN đã trỏ sẵn vào `kho_test_*`.
- Làm trong worktree hiện tại, nhánh `lat/m4-dl4`, dựng từ `lat/m4-dl3` (đã có DL2 và DL3 vòng 2: kiểm quyền dùng chung, 3 trạng thái NULL, mã `M4_REVIEW_KHONG_THAY`).
- **Không sửa** `review_data_pg.py` hay `review_phu_luc_pg.py`; chỉ import hàm công khai.
- **Không đọc dữ liệu Review thật.**

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\M4-KIEM-KE-CHEP-REVIEW.md`: §3 (bảng `dot_thanh_toan`, `kl_thanh_toan`, `khop_hang_muc`, `canh_bao`, `nhat_ky`), §5 dòng 4 · M4-DL4 (dữ liệu nguồn đủ, audit bất biến, **không suy duyệt từ DA_NOP**).
- Docstring `m4/sql_review_chep.py`: lần chụp, NULL 3 nghĩa, không nạp một phần.
- CD1 đã chốt: dòng mồ côi (`ma_hd` không còn trong `hop_dong`) có `hop_dong_id` NULL.

**Việc: tệp mới `src/kho_tri_thuc/m4/review_dot_pg.py`.**
1. Ghi 5 bảng `review_chep_dot_thanh_toan`, `review_chep_kl_thanh_toan`, `review_chep_khop_hang_muc`, `review_chep_canh_bao`, `review_chep_nhat_ky` **trong cùng giao dịch của lần chụp**, theo cách DL3 đã nối với DL2.
   - Replay không tăng dòng; cùng khóa mà khác hash thì từ chối.
   - REAL → `Decimal(repr)`; NULL giữ NULL; ngày và JSON nguồn giữ TEXT.
2. Đọc cho một HĐ ở bản hiện hành, **tự kiểm quyền M4** bằng hàm dùng chung của DL2. Thiếu `conn_phien` hoặc không quyền → 404 như DL2.
   - Đợt (giữ nguyên số liệu nguồn): giá trị kỳ, lũy kế, giữ lại, thu hồi, giá trị thanh toán kỳ.
   - Khối lượng theo hạng mục.
   - Ghép hạng mục: người xác nhận lịch sử chỉ là chữ, **không** suy thành actor hệ thống.
   - Cảnh báo cũ.
   - Nhật ký legacy: giữ nguyên chuỗi, không đoán múi giờ.
   - **Không** suy "đã duyệt" từ trạng thái nộp.
   - Số thiếu không thành 0.
3. DTO không lộ `file_nguon`, đường dẫn, `nhap_boi` hay mã nội bộ; tiền dùng `Decimal`.

**Test, tệp mới `tests/test_m4_review_dot_pg.py`:**
- Phần thuần: chuẩn hóa dòng; thiếu số không thành 0; không có trường cấm trong DTO.
- Phần PG:
  - ghi lần chụp có đợt, KL, ghép, cảnh báo, nhật ký (cả dòng mồ côi) rồi đọc lại;
  - replay không tăng dòng;
  - không quyền → 404;
  - lần chụp 2 mất đợt thì bản hiện hành không còn đợt đó;
  - nhật ký giữ nguyên chuỗi.
- Chạy thuần: `python -X utf8 -m unittest tests.test_m4_review_dot_pg`, với PYTHONPATH=`src;.;tests`.

**Tệp (2):** `m4/review_dot_pg.py`, `tests/test_m4_review_dot_pg.py`.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[M4-DL4] …`.
