Anh, đã hoàn tất PDF-1, chưa commit.

- `nguon/crm_docx.py:356`: mặc định tắt, trả `PDF_CHUA_SAN_SANG` + `PDF_XUAT_TAY`, giữ DOCX, không tạo worker/Word. Chỉ `KHO_CRM_WORD_PDF == "1"` mới chạy nhánh cũ.
- `giao_dien/assets/crm_g.js:614`: thêm câu tiếng Việt theo yêu cầu vì trước đó chỉ hiện mã lý do. Không sửa K2 hoặc ghim SHA.
- `tests/test_crm_giao_ket_http.py:75,467,660`: cập nhật kỳ vọng, thêm kiểm tra không tạo tiến trình và nhánh bật bằng mock.

Test: **4/4 ca thuần đạt**, 11 ca HTTP skip; không lỗi mới trong phần đã chạy. JavaScript, diff và UTF-8 không BOM đều đạt. Không nối CSDL, mở server hay khởi chạy Word.

Thông điệp commit: `[PDF-1] Mặc định tắt Word → PDF, giữ DOCX và hướng dẫn xuất tay`