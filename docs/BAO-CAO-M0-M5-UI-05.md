# Báo cáo sửa M0–M5 UI05 — predicate form xuyên refresh/detail (CODE ONLY)

**19/10/2026 — CODE ONLY / RUNTIME_UNRUN / CHƯA NGHIỆM THU GUI.**

- **Phiên:** cùng session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`.
- **Baseline:** frozen210 `bb25b5d6…ec780` (actual 72850, terminal `7ee109`).
- **Căn cứ:** `docs/GIAO-SUA-M0-M5-UI-05.md` (root pin `3d03f569…b0090`), `REVIEW-M0-M5-ROOT-TEST-04.md`, `REVIEW-M0-M5-HTTP-UI-04.md`.
- **Công cụ:** coder chỉ dùng Read/Glob/Grep/Edit/Write.
- **Không chạy:** không chạy/import JS hay Python, test, SQL/PG, HTTP, GUI, process, network, Bash.
- **Không đọc:** var/.env/secret/source app/dòng thật.
- **Không sửa:** backend/tests/schema/seed/quyền/reader/fixture/checksum, M9, M2/L11.
- **Runtime:** mọi hành vi dưới đây là **UNRUN**. Kết quả backend04 (migration17/service36/HTTP2) là của root cho candidate04, không phải bằng chứng GUI.

## 1. File

| File | Thay đổi |
|---|---|
| `src/kho_tri_thuc/giao_dien/assets/app.js` | Chỉ vùng M5 (xem §2). |
| `docs/BAO-CAO-M0-M5-UI-05.md` | Báo cáo này. |

Server, service, tests, HTML, CSS và vùng JS trước marker M5 (gồm M9) không đổi.

## 2. Sửa F1 còn lại

### `m5Act(path, body, ok, conHieuLuc)`

- Sau POST: kiểm actor epoch, rồi kiểm predicate.
- **Predicate đã sai:** không toast, không refresh, ghi chú trung tính `M5_FORM_DA_DOI`, trả `null`.
- **Predicate còn đúng:** toast rồi gọi `m5Load(conHieuLuc)`. Sau đó kiểm lại actor + predicate trước khi trả kết quả cho caller.
- **Nhánh lỗi (form đã đổi):** dùng ghi chú riêng `M5_FORM_DA_DOI_LOI`. Ghi chú này nói rõ "chưa xác định máy chủ đã ghi hay chưa", không khẳng định commit khi chỉ nhận lỗi hoặc mất kết nối. Upload `catch` ngoài cũng dùng ghi chú này.

### `m5Load(conHieuLuc = () => true)`

Kiểm predicate ở ba chỗ:

- trước khi GET (sai thì bỏ refresh đó);
- **trước** `m5 = s` / `m5Render`;
- **trước** khi ghi lỗi refresh.

Predicate được chuyển tiếp vào `m5Render(conHieuLuc)`.

### `m5Render(conHieuLuc = () => true)`

Đồng bộ (không có await bên trong). Predicate chỉ được chuyển tiếp vào `m5Detail(conHieuLuc)` cho detail async do refresh kéo theo.

### `m5Detail(conHieuLuc = () => true)`

- Kiểm predicate trước khi tải.
- Kiểm predicate cùng actor epoch và phiếu đang chọn **trước** cache `m5ChiTiet` và trước render.
- Trong nhánh lỗi: kiểm trước khi ẩn panel hoặc toast.

### Caller giữ mặc định (luôn đúng)

Làm mới thủ công, lọc, đổi vai, hashchange, nút "Mở", nhận mẫu, mapping, review, FILE: hành vi như cũ, kèm actor epoch.

### Giữ nguyên

- Form không đổi: POST → refresh → summary như trước.
- Capture đã commit không bị rollback/xóa/gửi lại.
- Raw `ArrayBuffer` → base64.
- Snapshot claims/File trước FileReader.
- 8 actor trusted.
- Khóa FILE theo actor/PN/phiếu/con trỏ/token basis, sống qua refresh; nút "Lần xuất mới".
- Không disable form, không thêm test hook vào product.

## 3. Ca kiểm root nên chạy (controlled-async unit + GUI; chưa chạy)

1. **Form không đổi** → summary + bảng nguồn cập nhật.
2. **Form đổi khi POST còn pending:**
   - không toast/summary;
   - không GET refresh của thao tác;
   - ghi chú trung tính.
3. **Form đổi khi GET refresh còn pending:**
   - không `m5 = s`, không render, không lỗi refresh;
   - ghi chú trung tính.
4. **Form đổi khi detail do refresh kéo theo còn pending:** detail không cache/render/toast.
5. **POST lỗi mạng sau khi form đổi:** chỉ ghi chú `…_LOI`, không khẳng định đã ghi.
6. **Làm mới thủ công / đổi vai / mở phiếu** vẫn hoạt động.
7. **Actor đổi** ở bất kỳ await nào → bỏ.

## 4. Giới hạn thật

- **Chưa chạy gì:** chưa có unit JS, browser, picker hay delayed-response. Root kiểm sau; unit không được coi là browser PASS.
- **Màn hình có thể giữ dữ liệu cũ:** khi predicate sai, refresh của thao tác bị bỏ, nên danh sách/detail đang hiển thị (cùng actor) có thể là dữ liệu trước thao tác cho tới khi người dùng bấm Làm mới. Đây là chủ ý, không tự refresh vào form mới.
- **Render tự làm form đổi:** nếu chính `m5Render` của refresh phải xóa lựa chọn nguồn đã biến mất (`m5XoaForm`), predicate trở thành sai. Detail của refresh đó bị bỏ và thao tác kết thúc bằng ghi chú trung tính.
- **Predicate chỉ bám form epoch:** việc đổi phiếu/vai vẫn do actor epoch xử lý như trước.

Kết thúc phạm vi UI05. Root freeze → review → runtime/GUI riêng.
