# M2k-b: M2 · Hóa đơn mua, nút "Khởi động lại bộ tải" (2 điểm nên sửa của review M2k vòng 2)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Đọc `AGENTS.md`, `CLAUDE.md`. Ghi tệp UTF-8 không BOM.
- Sandbox không ghi được `.git`: **không commit**. Không mở server. Không gọi cổng thuế. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m2k-b`, dựng từ hợp nhất (đã gộp M2k).
- Căn cứ: `docs/QUYET-DINH.md` QD-20261026-01; giao việc M2k và M2k vòng 2 trong `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\` (`giao-m2k.md`, `giao-m2k-v2.md`).

**Việc trong `src/kho_tri_thuc/giao_dien/m2_tai_hoa_don.py` (route khởi động lại, khoảng dòng 400–430 và 850–860):**
1. **Không gọi bộ tải trong lúc giữ khóa chung.**
   - Hiện lệnh `config()` (GET `/api/config` tới bộ tải) chạy khi đang giữ `_khoa` (= `app.mutation_lock`) và trong giao dịch PG `_guard`. Ghi chú của `_KhoaChung` cấm điều này.
   - Hậu quả: khi bộ tải treo, cả ứng dụng đứng tới `rpc_s` giây.
   - Sửa theo thứ tự:
     1. Kiểm quyền dưới `_khoa` + `_guard`, rồi nhả.
     2. Gọi `config()` khi chỉ giữ `_khoa_hang_doi` và `khoa_job`.
     3. Vào lại `_khoa` + `_guard`: kiểm quyền lần nữa, tính `bi_ngat`, ghi nhật ký YEU_CAU.
     4. Dừng và mở lại như hiện tại.
   - Thứ tự lấy khóa phải nhất quán, không tạo khả năng treo khóa.
2. **"Treo" phải hiểu giống nhau ở màn hình và máy chủ.**
   - Chỉ đánh dấu `treo: True` khi lỗi là `KHACH_QUA_HAN` hoặc `KHACH_KHONG_KET_NOI`. Không đánh dấu với `KHACH_TU_CHOI`, `DTO_SAI` hay các `NODE_KHACH_*` khác.
   - Route khởi động lại chấp nhận đúng các trường hợp mà nút được hiện.
   - Nút không được hiện ở trường hợp mà máy chủ sẽ từ chối.

**Test `tests/test_m2k_khoi_dong_lai.py`:**
- Ca bộ tải treo (config chậm): trong lúc chờ `config()`, một luồng khác lấy được `app.mutation_lock` ngay (dùng `threading.Lock()` thật, không phải RLock).
- Ca `KHACH_TU_CHOI` / `DTO_SAI`: không có `treo`, route trả câu tiếng Việt, không có nút.
- Giữ mọi ca cũ.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m2k_khoi_dong_lai tests.test_m2_00e_http tests.test_m2_tai_tat_ca` (PYTHONPATH=`src;.;tests`); `node tests/m2_khoi_dong_lai.cjs`.

**Tệp (≤ 3):** `giao_dien/m2_tai_hoa_don.py`, `tests/test_m2k_khoi_dong_lai.py`. `giao_dien/assets/m2_tai_hoa_don.js` chỉ sửa nếu điều kiện hiện nút cần đổi.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[M2k-b] …`.
