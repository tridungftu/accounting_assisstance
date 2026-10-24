# CRM feedback — sửa test tối thiểu 02

Ưu tiên của Anh: giao diện CRM chạy được để góp ý. CODE ONLY, giữ cùng session, không chạy lệnh/test/SQL/browser/network, không xóa/di chuyển file.

Chỉ sửa `tests/test_crm_neutral_compat.py` và tạo `docs/BAO-CAO-CRM-NEUTRAL-COMPAT-02.md`.
Giữ nguyên toàn bộ production, đặc biệt CRM/server hai hunk đã review, migrations, guard, M9 và app.js.

1. T05 hiện nối BANK2 hai lần vào DOT-1. Guard cũ đúng là cấm hai active link cùng BANK/schedule. Sửa test dùng 100m vào DOT-1, 50m vào DOT-2; vẫn kiểm tổng150m rồi gỡ50m còn100m. Không nới guard, không sửa sản phẩm.
2. setUpClass hiện đọc ROOT/cau_hinh.toml không nằm trong frozen source. Tạo fixture TOML tối thiểu trong chính thư mục temp được giữ lại: environment fixture, entity PLHN_FIXTURE, VND scale0, SQLite, Junsky false. LocalApp dùng file fixture này. Không đọc cấu hình thật/.env/var.
3. Sửa mô tả snapshot trung thực: các bảng nghiệp vụ được chọn so toàn rows; audit chỉ count, sequence chỉ last_value, file chỉ path+size. Không tuyên bố full byte/all audit rows/all sequence fields. Không cần framework snapshot mới.
4. Báo chính xác thay đổi và selftests NOT_RUN do CODE_ONLY. Thoát sau bàn giao để Root chạy kiểm độc lập.
