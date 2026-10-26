# XS-4 — Công tắc module × pháp nhân: các điểm cần Anh chốt

26/10/2026 · lead soạn từ TL 53, CD-017, `KK-XUONG-SONG.md` §5–§6. Mỗi dòng có **đề xuất của lead**. Anh chỉ cần trả lời "Đồng ý toàn bộ", hoặc ghi mã dòng muốn đổi.

Công tắc có 3 chế độ **Tắt / Thử / Vận hành**, đặt riêng cho từng module ở từng pháp nhân. Công tắc **không thay** ma trận thẩm quyền:
- module đang Vận hành nhưng người dùng không có quyền thì vẫn không thấy, không làm được;
- công tắc chỉ quyết định module có đang hoạt động ở pháp nhân đó hay không.

| Mã | Câu cần chốt | Đề xuất của lead | Phương án khác |
|---|---|---|---|
| S1 | **"Thử" nghĩa là gì?** | Module hiện **chỉ cho người được chọn thử** (Admin và người Admin chỉ định), làm đủ thao tác trong module. Nhưng: **không xuất ra ngoài** (file nhập Junsky, gửi tin, cổng thuế); **không đẩy kết quả chính thức sang module khác** (module khác coi như chưa có). Màn hình có dải "Đang thử". | Thử = mọi người có quyền đều thấy, có dải "Đang thử", thao tác như Vận hành. |
| S2 | **Ai được đổi công tắc?** | **Chỉ Admin.** Mỗi lần đổi phải ghi lý do, lưu nhật ký (ai, lúc nào, từ chế độ nào sang chế độ nào). | Admin đề xuất, Kế toán trưởng duyệt (hai người). |
| S3 | **Mặc định khi bắt đầu có công tắc?** | Module **đang dùng** (CRM, M2, M4, lõi) giữ đúng như hiện nay: **Vận hành** ở các pháp nhân đang dùng. Module **mới** (M3, M9, M10-1 và sau này) mặc định **Tắt** cho tới khi Admin bật. | Mọi module mặc định Thử. |
| S4 | **Tắt khi còn việc đang chạy?** | Tắt thì không nhận việc mới và ẩn khỏi lưới icon. **Việc nền đang chạy được chạy nốt và lưu kết quả**, không hủy giữa chừng. Dữ liệu đã có **vẫn xem được (chỉ đọc)** cho người có quyền. Module khác cần dữ liệu của nó hiện **"Chờ …"**, không báo lỗi. | Tắt = dừng ngay việc đang chạy. |
| S5 | **Chuyển Thử → Vận hành có cần kiểm gì?** | Có. Phải qua bảng điều kiện go-live của module (`BANG-DIEU-KIEN-GO-LIVE.md`). Còn ô chưa đạt thì máy **không cho chuyển** và nêu ô thiếu. Dữ liệu tạo trong lúc Thử **không tự thành chính thức**, phải làm lại hoặc Admin chọn chuyển từng lô có nhật ký. | Chuyển được ngay, chỉ cảnh báo. |
| S6 | **Thử nghiệm đầu tiên** để báo Anh XS-1…4 xong | Tắt M2 ở pháp nhân giả A: M4 vẫn mở được, phần cần hóa đơn hiện **"Chờ hóa đơn M2"**. Bật lại M2: hóa đơn về, M4 tự hết "chờ", không nhân đôi, pháp nhân B không bị ảnh hưởng. Làm trên DEMO. | Chọn cặp module khác. |

Sau khi Anh chốt, lead giao các lát: XS-4b (bảng công tắc trong CSDL), XS-4c (máy chủ kiểm công tắc), XS-2 (hàng việc nền), pilot XS-T1. Mỗi lát nhỏ, có Codex review chéo.
