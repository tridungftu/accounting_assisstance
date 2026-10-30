**Biên bản review OCR-4a — Kết luận: Cần sửa.**  
Nhánh `lat/g3-ocr-4a`, commit `deab5fb`; hai tệp được review không đổi sau merge tại HEAD `469e055`.

Các điểm kiểm trọng tâm:

- **Phạm vi: Đạt.** Chỉ thêm đúng 2 tệp trong whitelist; không tạo `engine.json`.
- **Chuẩn và đặc tả: Chưa đạt phần drain**, xem phát hiện 1. Không thêm SQL, login CSDL, role/RLS/DEFINER hoặc thay đổi `search_path`; không mở quyền.
- **An toàn: Đạt qua kiểm tĩnh.** Không thấy DROP/xóa, đọc kho thật, bí mật/DSN trong log/audit, gọi ABBYY hoặc mạng ngoài. Test chỉ dùng loopback và dữ liệu DEMO. Kiểm login PostgreSQL không áp dụng cho lát này; tài khoản Windows riêng được đề giao sang OCR-4b.
- **Dùng lại mã: Đạt.** Dùng bootstrap G2-21 và SDK engine G2-20 tại `chay.py:15`, `:16`, `:112`; không dựng launcher/Job/IPC thay thế.
- **Test kiểm đúng điều tuyên bố: Chưa đạt**, xem phát hiện 2.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Timeout 5 giây làm đứt bàn giao khi drain.** Với `DEMO_OCR4A_GIU`, yêu cầu thu hồi rồi để Core ACK sau 6 giây: `recv()` trong kênh giả hết hạn, worker thoát, `drain()` trả `False`; `chay()` vẫn đóng socket và thoát qua `finally` khi kết quả chưa bàn giao. Vi phạm yêu cầu OCR-4a về drain và chuẩn SDK §3.6.4, đặc tả SDK §4.3: tiếp tục chờ bàn giao, không tự đóng vì hết hạn. Test hiện chỉ chờ ngắn trước ACK nên không bắt ca này. | **Chặn** | `src/kho_tri_thuc/engines/e_ocr/chay.py:87`, `:90`, `:124`; `tests/test_g3_ocr_4a.py:65`, `:216`, `:227` |
| **Ca “lỗi bàn giao” thực tế gây lỗi ở bước nhận việc.** `nhan = MagicMock(side_effect=loi)` khiến chương trình chưa tới `SDKEngine.ghi_ket_qua`. Test cũng chỉ gọi `_VongNhan`, nên assertion socket chưa đóng không kiểm được nhánh `finally` của `chay()`. Cần gây lỗi tại operation `ghi_ket_qua` và kiểm hành vi qua entrypoint để chứng minh điều tên test tuyên bố. | **Cần sửa** | `tests/test_g3_ocr_4a.py:129`, `:135`, `:140`; `src/kho_tri_thuc/engines/e_ocr/chay.py:125` |

**Kiểm chứng:** `git diff --check` đạt. Tôi không chạy lại runtime trong lượt review chỉ đọc. Kết quả lead cung cấp: OCR-4a **11/11**; G2-21 **27 đạt, 2 skip PG**. Các kết quả này chưa bao phủ tình huống ACK chậm nêu trên.

**Hỏi Claude:** Điểm 1 có được giữ mức **Chặn** theo tiêu chí “Core xác nhận trước khi dừng” không (`chay.py:87`)? Luồng lỗi xác định được bằng đọc mã; chưa có kết quả runtime cho ca ACK sau 6 giây để đối chiếu gate.