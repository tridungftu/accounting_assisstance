# Bản đồ vùng dữ liệu các module đang có — tóm tắt 1 trang (CD-018)

26/10/2026 · lead tóm tắt từ kiểm kê `KK-VUNG-DU-LIEU.md` (Codex, đọc mã, chưa đo trên CSDL đang chạy).

**Kết luận:**
- **M4 và M3 đã có vùng dữ liệu riêng.** CRM, M2, M9 vẫn để bảng của mình chung trong vùng dùng chung.
- **70 chỗ** một module đang đọc thẳng dữ liệu của module khác.
- **47 chỗ** một module đang ghi thẳng vào vùng dùng chung (tệp, chứng từ, việc chờ duyệt, liên kết, nhật ký) mà chưa qua hàm chung.
- Sửa dần khi chạm tới, không dừng việc đang chạy.

| Module | Ghi riêng (dữ liệu của mình) | Ghi chung (phải qua hàm chung) | Đọc danh mục chung | Đang đọc/ghi thẳng của module khác — cần sửa |
|---|---|---|---|---|
| CRM · Hợp đồng & báo giá | 46 bảng: mẫu, báo giá, bản soạn, ký, kiểm tra hợp đồng, dự án đang bán | Tệp, chứng từ, việc chờ duyệt, liên kết, nhật ký | Pháp nhân, đối tác, dự án, loại doanh thu, người dùng | **Đọc** tiền ngân hàng/công nợ (M1): 5 chỗ · **Ghi thẳng** vùng chung: 29 chỗ |
| M2 · Hóa đơn mua vào | 7 bảng hóa đơn, dòng mua, dòng ứng viên | Cổng tiếp nhận nguồn (đã có) | Pháp nhân, nguồn, ánh xạ, đơn vị | **Đọc** liên kết dòng chung: 1 chỗ |
| M3 · Hóa đơn bán ra & doanh thu BĐS | 3 bảng riêng (đã tách vùng) | Nhật ký qua trigger | Pháp nhân, hợp đồng, loại doanh thu | **Đọc** phiên bản hợp đồng CRM 2 chỗ + hóa đơn M2 7 chỗ = 9 chỗ |
| M4 · Nghiệm thu & chi phí dự án | 56 bảng riêng (đã tách vùng) | Đối chiếu qua hàm chung | Hợp đồng, dự án, đối tác, pháp nhân, người dùng | **Ghi thẳng** danh mục hợp đồng chung: 2 chỗ |
| M9 · Vốn vay & đầu tư tài chính | 8 bảng vay, khế ước, lãi suất | Ảnh chụp nguồn, tệp, liên kết, xuất | Tiền tệ, đối tác, dự án, pháp nhân | **Đọc** tiền ngân hàng (M1): 5 chỗ · **Ghi thẳng** vùng chung: 16 chỗ |
| Đối chiếu chung (hóa đơn ↔ nghiệm thu) | 9 bảng đối chiếu | Lưu/xác nhận đối chiếu | Pháp nhân, người dùng | **Đọc** M4: 39 chỗ · **Đọc** M2: 12 chỗ |
| Lõi (M0), quyền, bus sự kiện | Danh mục chung, người dùng, ma trận thẩm quyền, sự kiện | Hàm bus phát/nhận/xác nhận (đã có) | — | Bảng dùng chung nhiều module cần chốt "ai là chủ từng dòng" |

**Cách làm tiếp (nhóm lát XS-5):**
1. Ghi bản đồ này vào khai báo của từng module.
2. Trên DEMO, mỗi module một tài khoản CSDL chỉ được chạm đúng vùng đã khai báo.
3. Test bắt mọi câu lệnh khi chạy và so với bản đồ: lệch là đỏ, không gộp.
4. Làm màn Admin xem bản đồ.

CSDL thật chung (CD-016) chỉ dựng sau bước 2, để có tài khoản theo module ngay từ đầu.

**Lead tự chốt khi làm:**
- Ai là chủ bảng hợp đồng và phiên bản dùng chung giữa CRM và M9.
- Ai là chủ bảng chứng từ, công nợ dùng chung.

Không có câu cần Anh chốt ở bước này.
