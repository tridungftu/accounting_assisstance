Anh, **AI-3 dừng theo mục 5 của handoff**: đã phát hiện cơ chế ghim SHA-256 bao gồm cả hai tệp cần sửa.

- [nguon_review.py:45](src/kho_tri_thuc/m4/nguon_review.py:45) ghim `trich_xuat/ai_cloud.py`; [dòng 48](src/kho_tri_thuc/m4/nguon_review.py:48) ghim `trich_xuat/cloud.py`.
- [nguon_review.py:130](src/kho_tri_thuc/m4/nguon_review.py:130) so băm trước khi nạp; khác băm sẽ báo `M4_NGUON_REVIEW_SAI_PIN` và từ chối dùng lõi.

**Chưa sửa tệp, chưa thay đường gọi, chưa chạy test, không commit.** Vì vậy chưa có số test trước/sau.

Lead cần xử lý phạm vi cơ chế ghim trước khi giao tiếp lát này. Thông điệp commit dự kiến khi hoàn tất: `[AI-3] Chuyển Cloud engine #6 qua cổng AI dùng chung`.