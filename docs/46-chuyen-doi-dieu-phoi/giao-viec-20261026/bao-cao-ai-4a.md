Đã hoàn thành AI-4a, Anh. Cloud vẫn **TẮT mặc định**, không commit.

- **Đã làm:** lấy mẫu theo loại việc, kiểm Cloud qua Mask, ghi đúng/sai theo trường bằng metadata; thống kê cửa sổ N, giảm/tăng tỷ lệ và hàm chỉ đọc `CongAI.thong_ke()`. Không cần migration.
- **File đổi:** `src/kho_tri_thuc/tri_thuc/cong_ai.py` và `tests/test_ai4a_kiem_xac_suat.py`; UTF-8 không BOM.
- **Test:** 39 đạt/44, 5 PG skip; không lỗi mới trong nhóm đã chạy. Đã thử Cloud tắt, kiểm 100%, giảm/tăng tỷ lệ, chặn định danh sót và không ghi văn bản. Chưa chạy toàn bộ nền.
- **Cần Anh:** chốt lịch tỷ lệ/cửa sổ; chưa cấu hình thì giữ 0%. Độ chính xác hiện là độ khớp với Cloud, chưa có chấm từ người duyệt/đáp án mẫu. SQL PG mới kiểm bằng kết nối giả.

Thông điệp commit đề xuất: `[AI-4a] Kiểm xác suất và đo độ chính xác Local theo loại việc`.