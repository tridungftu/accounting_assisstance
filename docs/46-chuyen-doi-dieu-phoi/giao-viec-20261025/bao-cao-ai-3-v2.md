Anh, đã hoàn tất phần sửa AI-3 vòng 2; **không commit**.

- **Đường gọi:** engine #6 → `CongAI.goi(YeuCauAI)` → Local trước; Cloud qua Mask v2 → mở che → kiểm trích dẫn trên bản gốc.
- **Bốn tệp đổi:** `ai_cloud.py`, `cloud.py`, `nguon_review.py` và `tests/test_ai0_khoa_cloud.py`. Không sửa `cong_ai.py`.
- **PIN:** cập nhật đúng hai SHA-256 từ byte trên đĩa, kèm chú thích lead yêu cầu. Cơ chế kiểm băm và các băm khác giữ nguyên; lõi Review nạp thành công.
- **Test:** trước **87/87**; sau **102/102**, cộng **23/23** test thuần engine #6 — tổng **125/125**, không skip, không lỗi mới trong phạm vi chạy. `git diff --check` đạt.
- **Đã tự thử:** Cloud tắt không gọi Mask/Cloud; còn sót bị chặn; gửi bản đã che; mở che và loại trích dẫn sai; Local tiếp tục xử lý.

**Giới hạn:** chưa thử dịch vụ thật. Host vận hành cần tiêm cổng gắn `BoGhiPostgres`; mặc định độc lập dùng bộ ghi bộ nhớ. Token vẫn được ghi tại cổng; bộ đếm legacy trả 0 vì `KetQuaAI` không trả usage.

Thông điệp commit đề xuất: `[AI-3] Chuyển Cloud engine 6 qua cổng AI dùng chung và cập nhật hai băm Review`.