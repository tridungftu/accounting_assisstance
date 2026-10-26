# Review 26/10 12:30–12:50 (review-lat, Opus): MTQ-3b1, MTQ-2c, MTQ-4a0

## MTQ-3b1 (ba0272e): ĐẠT, lead đã gộp (38ddd08)
- Nhánh `/api/tham-quyen/` đặt ngay sau `authorize` (token, Origin, Host), nên không bị nhánh khác chặn trước.
- Không giữ `mutation_lock`. Whitelist chỉ thêm đúng 1 asset.
- Ở chế độ kho thật, route trả 400 `THAT_UI` trước khi mở PostgreSQL, không lộ stack.
- **Nên sửa (đã đưa vào MTQ-2d):** test âm CSRF ở tầng dispatcher.

## MTQ-2c (756b18b): ĐẠT, PG 80 ok, lead đã gộp (637df66)
- Admin được kiểm 3 lớp. Bảo vệ Admin cuối nằm ở **SQL** (trigger) dưới cùng khóa.
- Thu hồi bằng UPDATE, không DELETE. Pháp nhân suy từ phòng hoặc gán vai, không nhận từ thân yêu cầu.
- **Nên sửa (đã đưa vào MTQ-2d):**
  - lỗi trùng hoặc khóa ngoại hiện mã kỹ thuật;
  - `MTQ_DANH_TINH` dùng lẫn nghĩa;
  - câu báo lỗi lệch ngữ cảnh;
  - ghi chú "khôi phục" chưa chính xác (ghép được từ NHAP + CONG_BO);
  - `ly_do` của nhật ký từ chối chỉ lặp mã.

## MTQ-4a0 (530d528): KHÔNG ĐẠT, 1 điểm Chặn ở test; phần bảo mật SQL đạt cả 7 mục
- **Đạt:**
  - `search_path` an toàn, `pg_temp` cuối; danh tính chỉ qua `ktt_danh_tinh()`.
  - Không nhận actor, pháp nhân hay vai; chỉ đọc 2 bảng trong danh sách cho phép.
  - REVOKE PUBLIC, chỉ cấp EXECUTE cho app_web.
  - Lệnh hỏi không để lại dòng nhật ký.
- **GUC danh tính:** `app_web` tự đặt được, ở cùng mức tin cậy các hàm DEFINER sẵn có (`ktt_duoc`, `crm_*`). Không leo thang mới, nhưng đây là giới hạn chung của kiến trúc: không ký phiên.
- **Chặn:** test ghim "migration cuối" và tên `M00xx`.
- **Ca PG đỏ:** do cách viết test (CSDL dùng chung trong lớp), không phải lỗi sản phẩm.
- **Nên sửa (vòng 2):**
  - pháp nhân chưa bật phải trả `CU` cả với HĐ M4 và đối tượng chưa có resolver, nếu không đường cũ M1/M4 sẽ hỏng khi nối MTQ-4a;
  - hàm ghi từ chối chống trùng theo `request_id`, kiểm `hanh_dong` thuộc danh mục, không ghi khi thiếu danh tính;
  - test `has_function_privilege` cho các vai khác.
- **Để sau (MTQ-4a):** adapter phải che `phien_ban_id`/`revision` của pháp nhân khác và sự khác nhau giữa CU và MTQ_CAN_RESOLVER (dò sự tồn tại của HĐ), trả 404 hoặc bỏ trường.

### Lead chốt tạm 3 câu reviewer đề "Cần Anh" (đưa vào danh sách Anh xác nhận, không chặn)
- **A. Phòng áp dụng cho một thao tác:**
  - Máy chủ suy từ đối tượng hoặc phiên.
  - `phong_id` trong yêu cầu chỉ được chọn trong các phòng người dùng **đang có vai** và gắn với pháp nhân của đối tượng.
  - Mơ hồ (nhiều phòng, không chọn) thì chặn `MTQ_PHONG_MO_HO`.
  - Hệ quả: người có vai ở 2 phòng dùng được quyền của phòng họ chọn cho thao tác đó. Không cộng quyền 2 phòng trong cùng một quyết định.
- **B. Số tiền so hạn mức:** do máy chủ tính từ phiên bản nghiệp vụ đã khóa (CRM V3/G6A: tổng HĐ của phiên bản quyết định; M4: số xin thanh toán của kết luận). Không lấy từ trình duyệt. Resolver SQL làm ở MTQ-4b.
- **C. Hợp đồng JSON đối tượng:** `{bang, id, phong_id?}`. Danh sách bảng mở rộng dần theo các lát MTQ-4.
