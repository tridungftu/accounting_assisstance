# M4-5b vòng 2 — sửa sau kiểm nhanh

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.** UTF-8 không BOM — ghi tệp bằng UTF-8. Worktree hiện tại, nhánh `lat/m4-5b`. Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL.

1. `src/kho_tri_thuc/m4/giao_dien/m4_ke_toan.js` ~:723: câu "Cần Anh: đường tải tệp mới hiện chỉ cấp cho phòng dự án…" là ghi chú nội bộ đang hiện trên màn kế toán → đổi thành câu trung tính cho người dùng, vd "Chọn tệp căn cứ đã có trong hồ sơ nghiệm thu. Tải tệp mới do phòng dự án thực hiện." (không chữ "Anh", không mã quyền).
2. Xác minh khóa chặn gắn trùng mà giao diện dùng (`da_gan_o[].doi_chieu_id` hoặc tương tự) khớp đúng tên trường máy chủ trả (đọc `src/kho_tri_thuc/k2/ghi_nhan_chung.py` + `k2/sql_ghi_nhan_chung.py` dựng DTO); lệch → sửa giao diện + test node cho khớp; khớp → ghi tệp:dòng chứng minh.
3. Cập nhật `tests/m4_03b_async.cjs`: DOM không chứa "Cần Anh"; (nếu sửa ở mục 2) ca chặn gắn trùng dùng đúng tên trường máy chủ.
**File (≤ 2):** `m4_ke_toan.js`, `tests/m4_03b_async.cjs`. Không xóa file.
**Chạy:** `node tests/m4_03b_async.cjs`; `python -X utf8 -m unittest tests.test_m4_03b_http` (PYTHONPATH=src;.) — ghi số.
**Báo cáo (≤ 8 dòng):** sửa ở file:dòng · tên trường khớp (tệp:dòng) · số test · thông điệp commit `[M4-5b] vòng 2: …`.
