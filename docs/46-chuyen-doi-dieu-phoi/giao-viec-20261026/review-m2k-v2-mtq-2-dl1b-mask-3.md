# Review 26/10 11:30–11:45 (review-lat, Opus): M2k vòng 2, MTQ-2, M4-DL1b, MASK-3

## M2k vòng 2 (`lat/m2k` 9ef507d): ĐẠT, lead đã gộp hợp nhất (789607f)
- Điểm Chặn vòng 1 đã hết: chỉ thêm `treo` khi treo.
- Đã có 409 `M2K_DANG_TAI` khi bộ tải còn phản hồi mà đang có lần tải. Quyền là kế toán có hồ sơ tải. Nhật ký ghi lần tải và hàng đợi bị ngắt. Nút ẩn khi bộ tải chưa mở.
- **Nên sửa (lát M2k-b):**
  1. `config()` gọi bộ tải trong lúc giữ `app.mutation_lock` và giao dịch PG: cả ứng dụng đứng khi bộ tải treo.
  2. Màn hình và máy chủ hiểu "treo" khác nhau (`NODE_KHACH_*`).
- **Cần Anh:** khi bộ tải không phản hồi, kế toán pháp nhân A khởi động lại sẽ ngắt cả lần tải của pháp nhân B. Nhật ký chỉ gắn pháp nhân A.

## MTQ-2 (`lat/mtq-2` 67461ed): ĐẠT, lead đã gộp hợp nhất (5424efb)
- Danh tính chỉ từ phiên. Quyền Admin kiểm 3 lớp. CAS và idempotency đúng. Không có bootstrap. Kích hoạt bị chặn (`mtq_san_sang` false). Nhật ký từ chối được ghi sau rollback. Không lấy lại `mutation_lock`.
- **Nên sửa (lát MTQ-2b):**
  1. Đọc thân yêu cầu trước khi lấy khóa.
  2. Test phải dùng `Lock` thật.
  3. Lỗi ghi nhật ký trả 503.
  4. Bỏ qua ô không đổi.
  5. GET ma trận chỉ Admin; nhật ký có giới hạn và không trả `boi_csdl`; bỏ đọc N+1; bỏ `LIKE`.
  6. Câu chữ không dùng từ kỹ thuật.
- **Lead chốt:** revision tăng theo từng thay đổi như SQL MTQ-1; không đổi SQL.
- **Cần Anh:** thiết kế §6 có các route khai phòng, gán vai, phạm vi, Admin, khôi phục; MTQ-2 chưa có. Cần lát MTQ-2c trước cổng A ma trận.

## M4-DL1b (`lat/m4-dl1b` 4f11ba7): KHÔNG ĐẠT, 1 điểm Chặn ở test
- SQL đạt cả 6 mục: M0038 không đổi byte; UNIQUE; `chup_luc` NOT NULL; LOCK cùng giao dịch migrate; hàm bản hiện hành đúng; test hành vi thật.
- **Chặn:** 2 dòng kiểm trong test ghim vị trí (DL1b phải là migration cuối; sha256 phần đầu `pg_migrations.py`). Giao vòng 2 bỏ 2 dòng này.
- **Nên sửa (docstring, vòng 2):**
  - app_web gọi hàm bị từ chối, nên DL2 dùng kết nối chủ bảng và tự lọc quyền.
  - NULL có 3 nghĩa.
  - Nạp lại phải đối chiếu `chup_luc`.
  - Không nạp một phần.
- Câu "nhiều CSDL Review": CD-011 chỉ có một tệp `hop_dong.db`, không cần hỏi Anh.

## MASK-3 (Mask file v2 2.7.2): KHÔNG ĐẠT, 1 điểm Chặn
- Đổi hành vi API theo đúng hướng an toàn:
  - Chưa có danh mục mà lượt có cụm mới thì trả 423.
  - Hàng chờ lỗi thì trả 503.
  - Mọi lỗi đều `gui_duoc:false` và không tạo lượt.
  - Phần mềm kho tri thức (`cong_ai.py`) đã chỉ gọi khi danh mục `da_mo`, nên không bị ảnh hưởng. Không có đường nào gửi văn bản chưa che.
- Mã hóa `.maskpending` đạt: AES-256-GCM, Scrypt, ghi nguyên tử, có giới hạn. Không đổi định dạng `.maskvault`/`.maskkeep`. Màn duyệt hiển thị bằng text.
- **Chặn:** tự tải lại `/api/pending` mỗi 15 giây làm phiên giao diện không bao giờ hết hạn (trái QD-24).
- **Nên sửa (gộp vòng 2):**
  - Tạo danh mục mới thì đặt tệp chờ cũ sang bên.
  - Không lưu ngữ cảnh bí danh lượt.
  - Mã riêng `danh_muc_chua_co`.
  - Bỏ `import httpx` ở tiến trình con trong test.
  - CHANGELOG ghi số lead đo: pytest 469 đạt; benchmark bộ chính 1/101, held_out 6/51, đều giữ nguyên.
- **Cần Anh:**
  - Có hộp xác nhận cho "Đánh dấu không phải định danh" không? (cụm được gửi Cloud dạng rõ từ lượt sau)
  - Chấp nhận việc lượt có cụm mới khi chưa có danh mục bị từ chối thay vì che bằng bộ nhận diện?
  - Màn duyệt chỉ hiện cụm, không có câu xung quanh?
