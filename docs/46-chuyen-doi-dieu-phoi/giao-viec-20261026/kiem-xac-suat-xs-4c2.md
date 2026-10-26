**Kiểm xác suất XS-4c2 (Claude, rút 0,201, 26/10 ~23:45) — Chặn, sửa vòng 4:**

`giao_dien/module_cong_tac.py` `kiem_danh_muc` chạy `SELECT ma FROM master.module_danh_muc` bằng kết nối ứng dụng. M0056 (`k2/sql_module.py:196–215`) `REVOKE ALL` trên các bảng `module_*`, bật RLS không policy, chỉ cấp EXECUTE hàm cho `app_web`. Khi chạy thật mọi GET/POST sẽ lỗi quyền → 400 "Chưa thực hiện được thao tác". Test HTTP dùng mock nên không bắt được.

**Sửa:**
1. Bỏ `kiem_danh_muc` đọc bảng. Chỉ kiểm định dạng mã (chuỗi không rỗng, không khoảng trắng ngoài, chỉ chữ hoa/số/gạch dưới).
   - GET với mã không có trong danh mục → hàm `module_trang_thai` trả chế độ TẮT (cờ false) — chấp nhận.
   - POST với mã không có → SQL M0056 từ chối (FK/mã lỗi) → 400 câu tiếng Việt.
2. Dịch vụ/HTTP **không** SELECT trực tiếp bảng `master.module_*`. Thêm test tĩnh quét `module_cong_tac.py` và `k2/module.py`.
3. Thêm **test PG** (`skipUnless KHO_PG_DSN_TEST`, dựng như `tests/test_xs4_dich_vu.py`): chạy `_CongTacHttpK2.phap_nhan` + `trang_thai` và một POST đổi chế độ bằng Admin, **dưới vai ứng dụng thật** (`app_web`/danh tính phiên như test dịch vụ) → không lỗi quyền.
