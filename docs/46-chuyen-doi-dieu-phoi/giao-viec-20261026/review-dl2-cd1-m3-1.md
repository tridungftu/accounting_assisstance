# Review 26/10 ~12:40–13:10 (review-lat, Opus): M4-DL2 vòng 1–2, M4-CD1, MTQ-4a0 vòng 2, M3-1a, M3-1b

## M4-DL2: vòng 1 KHÔNG ĐẠT → vòng 2 ĐẠT, lead đã gộp (663ac63)
- **Vòng 1, điểm Chặn:** trả NULL thì luôn báo "đã xóa ở nguồn". Hợp đồng dữ liệu đổi sau khi giao việc, không do worker.
- **Vòng 2 đạt:**
  - 3 trạng thái NULL, kèm câu tiếng Việt cho từng trạng thái.
  - **Lớp đọc tự kiểm quyền M4** (lead chốt phương án (a)): kiểm trên kết nối phiên, dự án lấy từ `master.hop_dong`. Người không quyền không phân biệt được gì.
  - Chặn ánh xạ trùng; chuẩn hóa -0; báo đúng trường làm replay khác.
- **Nên sửa (đưa vào DL3 vòng 2):**
  - Gộp 3 câu SELECT thành 1, tránh trạng thái sai thoáng qua.
  - `hop_dong_id` sai định dạng thì trả 404.
  - Mã lỗi theo quy ước `M4_REVIEW_KHONG_THAY`.

## M4-CD1 (công cụ chuyển Review): KHÔNG ĐẠT → vòng 2 đang chạy PG
- **Đạt:**
  - Nguồn chỉ đọc (`mode=ro&immutable=1`, `query_only`); kiểm SHA256 3 lần.
  - Một giao dịch; `--thu` không kết nối PG; chạy lại không trùng.
  - Báo cáo chỉ có số đếm; đủ 12 bảng; mọi tham số đều bắt buộc.
- **Chặn:** khi stdout không phải UTF-8, nhánh lỗi in traceback kèm exception gốc, có thể lộ một đoạn mật khẩu DSN. Đã sửa ở vòng 2.
- **Lead chốt:** chỉ đòi ánh xạ cho `ma_hd` có trong bảng `hop_dong`. HĐ mồ côi lưu NULL và đếm riêng.
- **Khi lead chạy thật:**
  - chạy `python -X utf8`;
  - báo cáo ghi vào `LUU-TRU`, không dán vào chat;
  - `ma_hd` dạng `HD0001` là mã nội bộ, ít nhạy cảm.

## MTQ-4a0 vòng 2: ĐẠT, lead đã gộp (e9553d4, M0041)
- Đã hết Chặn: test không còn ghim migration cuối.
- Pháp nhân chưa bật thì mọi đối tượng trả CU; đối tượng không xác định được pháp nhân bị chặn ngay khi có một pháp nhân bật.
- Nhật ký từ chối chống trùng theo request.
- **Lưu ý cho MTQ-4a:**
  - dựng `{bang,id}` từ đối tượng thật;
  - đặt GUC danh tính trước khi gọi;
  - `request_id` do máy chủ sinh.

## M3-1a: ĐẠT, lead đã gộp (0258fbd, M0042)
- Cơ sở HĐ:
  - lưu **tổng** giá đất được trừ, không nhân từ mức/m²;
  - ràng buộc phần chịu thuế;
  - xác nhận đòi phiên bản CRM `DA_DUYET`;
  - bất biến.
- Liên kết tham chiếu thẳng bảng hóa đơn M2, chặn chiều khác `BAN_RA`. M2 hiện chỉ có `MUA_VAO`, nên bảng chỉ chứa được ứng viên.
- Policy theo ngày hiệu lực; RLS chỉ đọc.
- **Để sau:**
  - revision chưa bắt nối tiếp;
  - người ghi nhật ký phải lấy từ danh tính phiên khi có hàm ghi;
  - policy gắn vào id một dòng loại hình có phiên bản (xử lý ở M3-2).

## M3-1b: KHÔNG ĐẠT → vòng 2 đang chạy
- Phần nghiệp vụ đúng: ba đẳng thức, `CHUA_DU_DOT`, PENDING khi thiếu căn cứ, chỉ tính liên kết đã xác nhận, Decimal, không tự sửa.
- **Chặn:** lớp test PG tự skip, nên SQL của `M3K2` chưa từng chạy thật.
- **Nên sửa (lát M3-1c sau):**
  - câu hiện cho người dùng không chứa "Cần Anh"/"policy thuế số 7";
  - tách lý do "thiếu đơn vị tiền";
  - hóa đơn đã bị thay thế/hủy phải trả PENDING;
  - chặn một hóa đơn xác nhận vào 2 HĐ, hoặc thêm cột phần giá trị chia.

## Cần Anh mới (thêm vào danh sách)
1. **M3 #7:** bộ phận thuế xác nhận cách thể hiện giá đất được trừ. Chưa có thì đẳng thức 2 và 3 luôn ở "Chờ đủ căn cứ".
2. **M3 "đã xuất đủ đợt":** ai hay nguồn nào xác nhận? Lịch thu CRM, hay kế toán bấm xác nhận theo HĐ/lô?
3. **M2 hóa đơn bán ra** (`M2-BAN-RA-KIEM-KE.md` §5):
   - nguồn ưu tiên: cổng thuế, XML/ZIP từ phần mềm hóa đơn tập đoàn, hay cả hai;
   - ai được nhận và xem hóa đơn bán ra theo pháp nhân;
   - bộ XML mẫu giả lập.
4. **M4-DL3:** hai phụ lục cùng ngày hiệu lực thì thứ tự áp thế nào? Hiện bật cờ "cần xem lại".
