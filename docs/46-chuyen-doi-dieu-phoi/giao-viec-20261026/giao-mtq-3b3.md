# MTQ-3b3: Ma trận thẩm quyền, bộ chọn vai DEMO trên màn ma trận (dòng giao diện), nối `/api/demo/vai`

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Đọc `AGENTS.md`, `CLAUDE.md` §4. Giao diện dùng tiếng Việt nghiệp vụ, không mã kỹ thuật.
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-3b3`, dựng từ `lat/ui-ky` **sau khi lead đã nhận hợp nhất** (có MTQ-5b: `GET /api/demo/vai`).

**Đã có:**
- `GET /api/demo/vai`:
  - nhóm "Ma trận thẩm quyền (DEMO)" gồm 5 vai, khóa `cap`;
  - nhóm "Quản trị DEMO" gồm Admin;
  - CRM chưa cấu hình thì trả `{"cau_hinh": false, "nhom": []}`;
  - kho thật thì chặn.
- Đổi vai qua `POST /api/crm/danh-tinh`, cơ chế phiên có sẵn.
- Màn ma trận (`app.js`, MTQ-3b2): dựng lười, chọn màn theo `la_admin` của `GET /api/tham-quyen/cua-toi`.

**Việc:**
1. `src/kho_tri_thuc/giao_dien/assets/app.js`: trên màn "Ma trận thẩm quyền" thêm khối "Vai mô phỏng (DEMO)".
   - Gọi `/api/demo/vai`; hiện 2 nhóm; nút "Dùng vai này" gọi `POST /api/crm/danh-tinh` đúng thân như các bộ chọn vai hiện có.
   - Đổi vai xong thì tải lại màn (gọi lại `cua-toi`, dựng lại Admin hoặc "Quyền của tôi") và hủy phản hồi cũ.
   - `cau_hinh: false` hoặc lỗi → ẩn khối, hiện câu "Chưa có vai mô phỏng cho ma trận ở bản này."
   - Ở kho thật không hiện khối.
   - Mọi chuỗi đi qua `textContent`. **Không** dùng `.after`/`.before`. Chống bấm đúp.
2. Không sửa máy chủ.

**Test:** thêm ca vào `tests/khung_luoi_async.cjs` hoặc tệp mới `tests/mtq_vai_demo_async.cjs`:
- khối hiện đúng 2 nhóm;
- đổi sang Admin thì dựng màn Admin;
- đổi sang vai thường thì dựng "Quyền của tôi";
- `cau_hinh: false` thì ẩn khối;
- không lỗi khi DOM giả thiếu `.after`.

Chạy **toàn bộ** `tests/*.cjs`, báo số đạt; không thêm bộ đỏ so với `lat/ui-ky`.

**Tệp (≤ 2):** `app.js`, 1 test.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[MTQ-3b3] …`.

**Bổ sung (lead, sau khi gộp hợp nhất vào `lat/ui-ky`):**
- Trên dòng giao diện, bộ chọn CRM/M9 dùng `_danh_tinh_demo` (có `string_agg`/JOIN `phan_quyen`, chỉ chạy trên PG), đã thêm lọc `MO_PHONG_MTQ_`.
- Ca `tests/test_mtq_demo_phien.py::MtqDemoPhienTinh::test_crm_m9_m5_khong_co_mtq` dùng CSDL giả SQLite nên lỗi.
- **Sửa ca test này** (tệp thứ 3 được phép): giả lập kết quả `_danh_tinh_demo`, hoặc kiểm câu SQL có điều kiện lọc `MO_PHONG_MTQ_`, giữ ý nghĩa "CRM/M9 không có vai MTQ". Không đổi mã sản phẩm.
- Phần PG của tệp phải chạy được trên PG thật.
