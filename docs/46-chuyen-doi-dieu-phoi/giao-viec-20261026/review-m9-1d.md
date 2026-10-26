## Review Codex (chỉ đọc) — M9-1d · 26/10 ~16:06

- **(a) Đạt:** nhãn đứng riêng mở Điều/Chương mới; lấy đoạn ngoài bảng kế tiếp khi ≤120 ký tự, không có nhãn cấp và không kết dấu câu; tiêu đề gộp không sinh câu riêng. `src/kho_tri_thuc/m9/tai_lieu_vay.py:43`, `:190`, `:176`.
- **(b) Đạt:** “Điều 5 của hợp đồng này…” vẫn không thành đầu điều; cũng không bị nuốt làm tiêu đề sau nhãn đứng riêng. `src/kho_tri_thuc/m9/tai_lieu_vay.py:21`, `:26`, `:185`; `tests/test_m9_tai_lieu_vay.py:235`.
- **(c) Đạt qua đối chiếu mã:** đường xử lý tài liệu cũ giữ cách gom nguồn, băm `ma_doan`, shape và tách câu; câu nội dung mới giữ nguyên văn. `src/kho_tri_thuc/m9/tai_lieu_vay.py:178`, `:222`; `tests/test_m9_tai_lieu_vay.py:209`, `:273`.

| Việc kiểm | Kết luận |
|---|---|
| **1. Phạm vi** | **Đạt:** đúng hai tệp được giao; test dùng DOCX DEMO trong bộ nhớ. Báo cáo khớp diff; đếm được 29 + 30 = 59 test, không có khai báo skip. |
| **2. Đúng yêu cầu** | **Đạt:** đủ nhận nhãn, lọc/gộp tiêu đề, giữ khoản thuộc điều mới và dùng tiêu đề làm ngữ cảnh chỉ mục. |
| **3. Tiền, số liệu, quyền** | **Đạt trong phạm vi:** diff không thêm tính toán tiền, làm tròn hoặc thay đổi kiểm quyền; giữ nguyên câu chứa số liệu. |
| **4. Không phá phần cũ** | **Đạt qua đối chiếu mã:** thay đổi tập trung vào nhãn đứng riêng; không thêm gọi mạng/API/AI. |
| **5. Giao diện/câu người dùng** | **Đạt trong phạm vi:** không thêm giao diện hay thông báo; không biến đổi ngày, tiền trong câu trích. |

**Chặn / Nên sửa / Để sau:** không có phát hiện.

**Kiểm chứng:** gate lead cung cấp **59/59 đạt**; `git diff --check` sạch. Tôi chưa chạy lại test vì môi trường không có Python khả dụng. Không sửa tệp, commit hoặc chuyển nhánh.

**Hỏi Claude:** không có.

**Kết luận: Đạt, có thể gộp M9-1d theo gate lead đã cung cấp.**
**Lead lọc (Claude):** Đạt, không lọc. Kiểm xác suất: khong.
