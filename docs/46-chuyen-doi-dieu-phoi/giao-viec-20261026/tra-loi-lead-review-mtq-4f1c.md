**Lead (Claude) quyết sau review MTQ-4f1c (26/10 ~23:35) — làm theo, không hỏi lại:**

1. **Chặn — sửa test:** các ca dương truyền `p_limit` trong khoảng hợp lệ (≤ 50) theo `_Q` của hàm bộ chọn. Thêm một ca `p_limit=100` → `M4_THAM_SO_SAI` để giữ kiểm biên.
2. **Ràng buộc trạng thái dữ liệu khi PN bật — phải giữ, theo ô thẩm quyền:**
   - các điều kiện nghiệp vụ hiện chỉ nằm ở nhánh CU (`m4/sql_mtq.py:135,139`: đợt đã nộp, loại tài liệu `HO_SO_DOT`) **không phải** kiểm vai, mà là giới hạn dữ liệu được thấy;
   - khi PN bật, giữ nguyên các giới hạn này, ánh xạ theo ô: người **chỉ** có ô của bước review/chứng từ/duyệt/kế toán (`M4:02A_*`, `M4:02B_*`, `M4:02C_*`, `M4:03A_*` mức XEM) chỉ thấy đợt **đã nộp** và tài liệu đợt đã nộp; người có `M4:HO_SO:XEM` thấy cả đợt nháp và tài liệu chưa nộp của hồ sơ trong phạm vi;
   - ánh xạ đối chiếu KK-MTQ4-M4 §1–§2. Mục nào không rõ ô → giữ giới hạn chặt hơn (chỉ đã nộp) và ghi "Cần lead";
   - test: hai người cùng phạm vi, một chỉ có ô review, một có HO_SO:XEM → tập dòng khác nhau đúng như trên.
3. **CD-018:** đọc `master.du_an`, `master.hop_dong` = đọc danh mục chung (vùng V3), được phép. Đọc `master.mtq_kich_hoat` để kiểm PN bật: chấp nhận tạm như các guard M0050/M0053/M0055 đang làm. **Để sau:** thay bằng hàm xương sống khi XS-5 có. Không đổi trong lát này.
