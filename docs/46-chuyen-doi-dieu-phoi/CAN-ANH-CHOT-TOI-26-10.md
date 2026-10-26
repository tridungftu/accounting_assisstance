# Phiếu cần Anh chốt — tối 26/10/2026

Ba nhóm câu, mỗi câu có **đề xuất của lead**. Anh trả lời "Đồng ý toàn bộ", hoặc ghi mã câu muốn đổi.

## I. Công tắc module Tắt / Thử / Vận hành (CD-017)

Chi tiết từng câu S1–S6 ở `XS-4-CAN-CHOT.md`. Tóm tắt đề xuất:

- **S1 · "Thử" nghĩa là gì:** chỉ người được chọn thấy module; không xuất ra ngoài; không đẩy kết quả chính thức sang module khác.
- **S2 · Ai đổi công tắc:** chỉ Admin, có lý do và nhật ký.
- **S3 · Mặc định:** module đang dùng giữ Vận hành; module mới mặc định Tắt.
- **S4 · Tắt khi còn việc:** không nhận việc mới, việc đang chạy chạy nốt, dữ liệu vẫn xem được; module khác hiện "Chờ".
- **S5 · Chuyển Thử → Vận hành:** phải đạt bảng điều kiện go-live; dữ liệu thử không tự thành chính thức.
- **S6 · Thử nghiệm đầu:** tắt M2 → M4 hiện "Chờ hóa đơn M2"; bật lại → hết chờ, không nhân đôi.

## II. Mã hóa và sao lưu (CD-019)

Chi tiết kỹ thuật ở `KK-MA-HOA-LUU-RIENG.md`.

**M1 · Danh sách cột mã hóa.**

*Nhóm A — mã hóa ngay (10 nhóm):*
1. Số CCCD của đối tác cá nhân và nhân viên.
2. Giấy tờ định danh của đối tác (CCCD, số tài khoản, MST cá nhân).
3. Số tài khoản ngân hàng của công ty và nhân viên.
4. MST của đối tác là cá nhân.
5. Số tài khoản trong bảng ánh xạ tài khoản tiền (kho cũ).
6. Số tài khoản đối ứng máy học từ sao kê (kho cũ).
7. Bản sao số tài khoản nằm trong dữ liệu sao kê, chứng từ gốc (kho cũ).
8. SĐT, email cá nhân trong báo giá, bản soạn, bản ký CRM.
9. Địa chỉ, giấy tờ cá nhân trong tham số hợp đồng M4.
10. Giá trị thật trong bảng che dữ liệu của cổng Mask.

*Nhóm B — chờ, xem lại sau (5 nhóm):*
1. MST của pháp nhân và đối tác tổ chức.
2. Tên đối tác, tên nhân viên, Zalo, tên đăng nhập. Mã hóa thì mất tìm gần đúng theo tên.
3. Mô tả chứng từ.
4. Dữ liệu nguồn thô, kết quả review.
5. Nhật ký.

*Nhóm C — không mã hóa (3 nhóm):*
1. Số tiền, kể cả lương.
2. Ngày.
3. Mã nội bộ.

Ba nhóm này được bảo vệ bằng quyền xem. Số tài khoản mã hóa rồi **vẫn khớp sao kê được**: máy so bằng mã băm riêng, không cần giải mã. Màn hình chỉ hiện 4 số cuối; xem đủ cần quyền riêng, có nhật ký.

→ **Đề xuất:** duyệt nhóm A; B chờ; C để nguyên.

**M2 · Giữ khóa ở đâu?**
- **Khóa mã hóa cột:** nằm trên máy, trong `D:\DU-LIEU-KE-TOAN\bi-mat\`, bọc bằng Windows theo tài khoản chạy phần mềm. Chỉ phần mềm đọc được lúc chạy. Không nằm trong CSDL hay thư mục phần mềm.
- **Khóa mở bản sao lưu:** là khóa riêng, cất trên ổ ngoài không cắm thường xuyên, kèm một bản dự phòng.
- **Anh chỉ định người giữ ổ ngoài.** Khóa không gửi qua chat.

→ **Đề xuất:** đồng ý cách giữ này.

**M3 · Lịch sao lưu và mục tiêu khôi phục.**
- Sao lưu mã hóa lúc 23:00 hằng ngày, và trước/sau mỗi lần nâng cấp hoặc nạp dữ liệu.
- Chép sang ổ khác hằng ngày, ra ổ ngoài hằng tuần.
- Giữ 30 bản ngày và 12 bản tháng; không tự xóa bản cũ.
- Mục tiêu: mất tối đa 24 giờ dữ liệu; khôi phục xong trong 2 giờ.
- **Đo BitLocker:** báo Anh nếu sau khi bật, máy chậm hơn 10% (thử tải CSDL) hoặc thao tác lưu chậm hơn 15%.

→ **Đề xuất:** dùng các số này làm mục tiêu cho lần thử đầu. Lead sẽ báo số đo thật trước khi Anh quyết bật BitLocker.

## III. Gom các hàng việc chạy máy riêng (CD-017/CD-019)

> **Anh đã trả lời 26/10 ~22:30 (QD-20261026-09): giữ nguyên cách thức, không gom; chỉ chuyển khi chạm tới; bổ sung cách dọn dữ liệu tạm.** Mục H1 không cần chốt nữa.

**H1.** Hiện có 4 bộ "việc chạy máy" làm riêng, khoảng 23 bảng:
- CRM đối chiếu G5;
- M4 review;
- M4 chứng từ;
- Request.

→ **Đề xuất:** ghi thành mục tiêu của XS-2 (hàng việc nền dùng chung), mỗi bộ chuyển một lát riêng **sau khi XS-2 chạy ổn**. Giảm được khoảng 15–20 bảng và bớt điểm kiểm quyền. Không dừng việc đang chạy.
