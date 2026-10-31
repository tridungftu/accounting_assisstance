**Biên bản review chéo AI-4a-v2 — Kết luận: Đạt.**

Nhánh `lat/g3-ai-4a`, HEAD `be36dfa`; đối chiếu `hop-nhat-20261023...HEAD` và riêng bản sửa `124ea44..be36dfa`. Phạm vi vòng 2: điểm Chặn tại `RV-AI-4a.md` và lỗi phát sinh từ bản sửa.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Đã đóng điểm Chặn mất kết quả khi bàn giao lỗi.** Giữ `BytesIO` trong vòng retry, tua về đầu trước mỗi lần gửi, giữ nguyên kết quả và không gọi lại provider. Ngoại lệ từ kênh Core được SDK chuyển thành `LoiEngine`, đúng loại được bắt. | Chặn — đã đóng | `src/kho_tri_thuc/engines/e_hoi_ai/chay.py:60`; `tests/test_g3_ai_4a.py:168` |
| **Đã đóng điểm Chặn tiến trình thoát khi drain chưa xong.** Callback chờ tới khi worker hoàn tất, báo `drain_chua_xong`, không trả `False` ra bootstrap để gây thoát như trước. | Chặn — đã đóng | `src/kho_tri_thuc/engines/e_hoi_ai/chay.py:127`, `:144`, `:160` |

Không phát hiện Chặn hoặc Cần sửa mới trong diff vòng sửa.

- **Phạm vi: Đạt.** Đúng hai tệp whitelist, không tạo `engine.json`; worktree sạch.
- **Yêu cầu drain/retry: Đạt.** Test tiến trình con thật gây lỗi sau khi transport đã đọc hết luồng; kiểm cùng luồng còn mở, dữ liệu không đổi, retry, tiến trình/Windows Job còn sống, chưa trả quyền accept. Sau ACK mới xác nhận thu hồi và thoát mã 0 (`tests/test_g3_ai_4a.py:65`, `:330`). Ca ACK chậm 6 giây vẫn được giữ (`:281`).
- **An toàn và quyền: Đạt qua kiểm tĩnh.** Không thấy DROP/xóa, truy cập kho thật, gọi AI/dịch vụ ngoài hoặc ghi bí mật/DSN. Không thêm SQL/login CSDL nên role/RLS/DEFINER/`search_path`, SQL chéo module và test login PostgreSQL không áp dụng. Không thấy thay đổi mở rộng quyền.
- **Dùng lại mã: Đạt.** Tiếp tục dùng bootstrap G2-21, SDKEngine G2-20 và DTO AI-1a; không dựng cổng AI riêng hay tự chạy Local.
- **Test kiểm đúng điều tuyên bố: Đạt qua đọc mã.** Ca mới kiểm trạng thái tiến trình thực và vòng đời bộ đệm, khắc phục điểm yếu của test mock trước.

**Đối chiếu riêng OCR-4a:** HEAD `e68a43d`. OCR bắt ngoại lệ rộng hơn tại `e_ocr/chay.py:53` và xử lý `DRAIN_CHUA_XONG` bên ngoài bootstrap tại `:141`; AI giữ vòng chờ trong callback. Cả hai đều giữ kết quả, retry và chờ ACK trước kết thúc; không phát hiện sai khác gây lỗi trong nhánh đang xét. OCR cũng có ca tiến trình con tương ứng (`tests/test_g3_ocr_4a.py:292`).

**Kiểm chứng:** `git diff --check` đạt ở cả hai nhánh. Không chạy runtime trong lượt review chỉ đọc theo mẫu; kết quả **AI 13/13, OCR 12/12, G2-21 đạt** do lead cung cấp. Chưa xác minh độc lập regression toàn bộ so với nền.