# Tiến độ sáu module

Cập nhật sau V9b/F4. Các trạng thái dưới đây giữ đúng sáu module M1–M6. Import Junsky vẫn tắt.

| Module | Trạng thái | Phạm vi V9b đã hoàn tất | Điều kiện còn lại | Giới hạn hiện hành |
|---|---|---|---|---|
| **M1 — Nền tảng và dữ liệu** | Hoàn tất kỹ thuật V9b | Sổ BR/BP, metadata, mapping TK tiền và migration v18 | Mapping TK tiền thực cần kế toán xác nhận | Không sửa file nguồn; không tự bỏ qua cách ly |
| **M2 — Kho tri thức** | Hoàn tất V9b | Nhãn PENDING, mã chính đơn vị, ưu tiên danh bạ/máy và tri thức điều kiện | Rà tri thức/mapping cụ thể sau khi Anh nạp bổ sung | PENDING chỉ dùng cho đề xuất nhanh; không tự duyệt |
| **M3 — Phiên và đề xuất** | Hoàn tất kỹ thuật; F chưa đạt | Vế tiền, mẫu BR/BP, trigger đối tượng, hóa đơn nhiều dòng | Bổ sung căn cứ TK tiền/MST → TK rồi chấm lại F | Thiếu căn cứ thuế/đối tượng vẫn chờ hoặc Đỏ |
| **M4 — Duyệt và xuất** | Hoàn tất V9b | Chỉ xuất dòng Anh Đồng ý, số chứng từ nối tiếp, DOI_UNG/DAY_DU, mẫu dự phòng và tải file | Cần mẫu/mapping nghiệp vụ Junsky để UAT nhập tay | Không nhập Junsky; BankID/CashflowID chưa được tự dựng |
| **M5 — Đối soát và học** | Hoàn tất V9b | Ghép duy nhất, loại mặc định, học sau Đồng ý/Sửa | Xác nhận mapping thực trước khi dùng tỷ lệ đúng làm cổng | Không kết luận trùng khi ghép mơ hồ; Bỏ không học |
| **M6 — Kiểm chứng và vận hành** | Hoàn tất V9b/F4; chất lượng chưa đạt | 198 test, F1–F2, kho chính sạch schema v18 | Chạy lại F sau khi có mapping/căn cứ còn thiếu | Không đưa dữ liệu thật vào tests/fixtures hoặc chat |

Quyết định và giả định V9b ở [QUYET-DINH.md](QUYET-DINH.md); số đo ở [BAO-CAO-V9b.md](BAO-CAO-V9b.md).
