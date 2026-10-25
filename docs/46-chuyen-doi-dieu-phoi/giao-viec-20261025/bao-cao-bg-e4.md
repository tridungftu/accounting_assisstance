Anh, đã sửa `app.js:524` và thêm test tại `tests/khung_luoi_async.cjs:190`: nhãn tiếng Việt, đánh số nhãn trùng, ngày dd/mm/yyyy; giữ đúng login khi đổi vai.
Test khung lưới đạt **19/19**; kiểm tra cú pháp, diff và UTF-8 không BOM đạt.
Kiểm tra bổ sung `m4_01c_async.cjs` lỗi tại dòng 219 vì vẫn đòi hiện login; cần cập nhật file thứ ba, ngoài phạm vi được phép.
Không commit. Thông điệp đề xuất: `[BG-e4] Việt hóa vai mô phỏng CRM và ngày nghiệp vụ`.