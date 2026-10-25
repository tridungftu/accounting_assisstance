Đã sửa `src/kho_tri_thuc/giao_dien/assets/crm_g.js:1065`: 3 trường dùng `nguoi`, ưu tiên tên máy chủ; còn 0 chỗ in login thô.
Test: thêm tại `tests/crm_giao_ket_async.cjs:194`, cập nhật assertion tại `tests/crm_du_an_ban_async.cjs:309`.
Trước/sau: 4/4 bộ đạt → 4/4 bộ đạt, thêm 1 ca DS-1; không lỗi mới.
UTF-8 không BOM; `git diff --check` đạt.
Thông điệp commit: `[DS-1] Ẩn login người lập, gửi và duyệt trong Bộ chuẩn dự án` — chưa commit theo yêu cầu.