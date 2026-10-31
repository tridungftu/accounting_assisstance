**Biên bản review AI-4a — Kết luận: Cần sửa.**

Nhánh `lat/g3-ai-4a`, HEAD `124ea44`; đối chiếu `hop-nhat-20261023...HEAD`, gồm bản sửa `9649457`.

- **Phạm vi: Đạt.** Chỉ thêm đúng hai tệp whitelist; không tạo `engine.json`.
- **Drain/ACK: Đạt nhánh ACK chậm; chưa đạt nhánh bàn giao lỗi**, xem bảng dưới. Đã bỏ timeout sau khi nhận SDK và có test ACK sau 6 giây (`chay.py:105`; `tests/test_g3_ai_4a.py:276`).
- **An toàn: Đạt qua kiểm tĩnh.** Không thấy DROP/xóa, truy cập kho thật, bí mật/DSN trong log/audit hoặc gọi AI/mạng ngoài. Test dùng dữ liệu DEMO và loopback. Không thêm SQL/login CSDL nên role/RLS/DEFINER/`search_path`, SQL chéo module và test login PostgreSQL không áp dụng.
- **Dùng lại mã: Đạt.** Dùng bootstrap G2-21, SDK engine G2-20 và DTO AI-1a (`chay.py:17`, `:18`, `:20`, `:125`). Import không khởi chạy Local; readiness không quảng bá capability thật.
- **Test: Chưa đủ cho nhánh lỗi.** Có ca âm lease hết hạn, DTO sai, preflight lỗi, phiên bản/capability sai và cổng bị chiếm; thiếu kiểm tiến trình còn sống khi bàn giao thất bại.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Lỗi bàn giao vẫn làm mất kết quả chưa được Core ACK và có thể kết thúc engine.** Tình huống: `KenhCore.goi('ghi_ket_qua')` phát sinh lỗi trước xác nhận; context đóng `BytesIO`, worker bắt lỗi rồi kết thúc. Khi thu hồi, `drain()` trả `False`, bootstrap ném `DRAIN_CHUA_XONG` ra khỏi `chay()`. Theo entrypoint hiện có, ngoại lệ không được bắt nên tiến trình thoát; bỏ lời gọi `socket.close()` không giữ tiến trình sống. Vi phạm yêu cầu drain của AI-4a, chuẩn SDK §3.6.4 và đặc tả SDK §4.3: không đóng engine khi kết quả chưa bàn giao. Test hiện bắt ngoại lệ trong tiến trình test và chỉ kiểm mock socket chưa đóng, nên không phát hiện tình huống này. | **Chặn** | `src/kho_tri_thuc/engines/e_hoi_ai/chay.py:60`, `:107`, `:133`, `:137`; `tests/test_g3_ai_4a.py:95`, `:173`, `:186`, `:191` |

**Kiểm chứng:** `git diff --check` đạt. Tôi không chạy lại runtime trong lượt chỉ đọc; lead cung cấp **12/12**. Chưa xác minh độc lập regression so với nền.

**Hỏi Claude:** Đề nghị lead phân xử phát hiện Chặn trên theo yêu cầu “không đóng engine khi còn kết quả chưa bàn giao”. Luồng lỗi xác định qua mã; cần ca tiến trình thật gây lỗi tại `ghi_ket_qua` để đối chiếu hành vi và gate.