Anh, đã sửa **2 file**, không đổi mã sản phẩm, không commit.

- **Gốc lỗi:** `tools/chay_test_theo_module.py:892` bỏ qua `thu_muc_khoi_dong`; `:936` thay `PYTHONPATH`; `:682` thay user base nhưng chưa chuyển tiếp `.pth` gốc. Các bước này làm mất đường nạp hook. Bộ chạy không tự bật `CODEX_NO_DELETE_FILES`.
- **Cách sửa:** nhận provider khởi động từ runtime, giữ đường `sitecustomize` của caller và chuyển tiếp user site gốc qua `.pth` tạm.
- **Bảo vệ giữ nguyên:** tiến trình thật thiếu hook vẫn thoát mã **4 / `GUARD_KHONG_NAP`**, chưa tạo thư mục dữ liệu. Provider thử sai SHA vẫn bị host từ chối; không sửa pin A517 hay kiểm guard.
- **Test:** 7 ca mới: **6 đạt, 1 skip** do thiếu A517 thật. `test_trich6_host` trước/sau đều **17 đạt / 3 ERROR / 3 skip**, cùng mã lỗi. Module bộ chạy cuối: **39 đạt / 1 FAIL / 1 skip**; FAIL timeout đã tái hiện trước sửa. Không thêm mã lỗi. Hai file UTF-8 không BOM, `git diff --check` đạt.
- **Còn thiếu:** lead chạy lại với runtime DEMO có provider A517 thật; chưa xác nhận host thật hoặc 31 ca PostgreSQL.

Thông điệp commit đề xuất: `[L0-8e] Giữ đường nạp hook bảo vệ tệp cho tiến trình con và cháu`