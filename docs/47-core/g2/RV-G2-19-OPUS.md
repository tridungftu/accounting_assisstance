# Review Opus G2-19 — Kết luận: Đạt, 6 Nên sửa (31/10 ~01:50)

Nhánh `lat/g2-19` (`4e1a54b`, trên `lat/g2-18`). PG: test_g2_19 24/24; G2-11/14/15/18 đạt.

| Mức | Phát hiện | Tệp:dòng | Xử lý |
|---|---|---|---|
| Nên sửa | Nonce chỉ giữ trong RAM tiến trình; thẻ gắn `instance_id`. Nếu `instance_id` dùng lại khi restart hoặc một instance có nhiều tiến trình → phát lại thẻ cũ trong 30 giây. Buộc thẻ vào thế hệ sở hữu / nonce khởi động, hoặc ít nhất ghi bất biến "instance mới mỗi lần khởi động" + test. | ngu_canh.py:187-194 | v2 |
| Nên sửa | Dọn kết nối trước khi trả pool còn sót: advisory lock cấp phiên, GUC phiên khác, LISTEN. Thêm `RESET ALL`, `pg_advisory_unlock_all()`, `UNLISTEN *`. | giao_dich.py:39-51 | v2 |
| Nên sửa | `tx.execute` trả cursor thật (`.connection` vượt cổng); `tx.info` lộ `.password`. Bọc cursor; chỉ trả `transaction_status`. | giao_dich.py:70-73, 84 | v2 |
| Nên sửa | Lỗi handler khác `LoiViec/LoiTiepNhan/LoiSuKien` gộp thành 500 (`LoiMTQ` 42501 nên 403, `LoiPhien`, 404/422…). Không còn dấu vết đã khử bí mật (loại lỗi + `request_id`). | giao_dich.py:162-175 | v2 |
| Nên sửa | Thiếu `sdk_core/__init__.py`; `packages.find` không gom namespace package vào wheel. | sdk_core/ | v2 (lead cho thêm tệp thứ 4) |
| Nên sửa | Test pool đặt sẵn `ktt.ma_phien` trùng mã dùng → không chứng minh. Thiếu ca A rồi B cùng kết nối, `set_config(...,false)`, advisory lock. | test_g2_19.py:420-434 | v2 |
| Để sau | Test cần `cryptography` (chưa khai báo trong `pyproject.toml`); thiếu → 24 ca skip. Runtime DEMO có sẵn. **Thư viện mới — chờ Anh duyệt.** | test:110, 220, 369 | Hỏi Anh |
| Để sau | Chưa hỗ trợ phạm vi hệ thống trong thẻ (`phap_nhan_id` bắt buộc UUID) — phối hợp G2-18 vòng 2. | ngu_canh.py:183-186 | G2-19 v2 nếu G2-18 v2 cần |

**Đạt:**
- thẻ: hạn / TTL ≤ 30 giây / chữ ký khóa công khai từ bootstrap, tiền tố miền / `compare_digest` / ràng buộc đủ trường;
- hash sai không tiêu thụ nonce;
- transaction đúng login, xác minh phiên, GUC cục bộ, chung `tx`;
- bí mật không lộ qua repr / pickle / traceback;
- đồng thời thật (barrier).
