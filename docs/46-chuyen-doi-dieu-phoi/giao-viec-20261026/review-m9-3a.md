## Review Codex (chỉ đọc) — m9-3a · 26/10 ~16:05

(a) **Đạt** — `snapshot_sheet.py:71`, `:81`, `:88`: tiền/lãi suất dùng `Decimal`, ngày dùng `date`, ô trống thành `None`; không qua `float`.

(b) **Đạt** — `snapshot_sheet.py:103`: hash ổn định, chuẩn hóa thứ tự cột, giữ giá trị thô; đổi ô làm đổi hash.

(c) **Không** — `snapshot_sheet.py:193` loại đúng mọi dòng trùng mã, nhưng `:100` vẫn nhận ô lỗi Sheet ở trường dạng chữ.

**Năm kết luận kiểm tra**

| Việc kiểm | Kết luận |
|---|---|
| Phạm vi | **Đạt:** diff đúng hai tệp được giao; fixture DEMO. Báo cáo 38 test khớp 20 test mới + 18 test báo cáo, không có khai báo skip. |
| Đúng yêu cầu | **Không:** còn nhận ô lỗi dạng chữ, chi tiết Chặn dưới đây. |
| Tiền, số liệu, quyền | **Không:** chuẩn hóa số đúng nhưng có thể nhận đơn vị tiền `#N/A`. Lát thuần này không thêm xử lý quyền. |
| Không phá phần cũ | **Đạt trong phạm vi kiểm:** chỉ thêm tệp; không mạng/AI; tích hợp báo cáo thuần đạt. |
| Câu cho người dùng | **Nên sửa / cần làm rõ:** `snapshot_sheet.py:173` chứa “Cần Anh/lead”, trái mục B.5 nếu được hiển thị cho người dùng. Mốc ngày giờ đúng định dạng. |

**Chặn — Ô lỗi Sheet lọt vào khoản vay hợp lệ**

`src/kho_tri_thuc/m9/snapshot_sheet.py:100` trả nguyên chuỗi cho trường dạng chữ, vi phạm **giao việc mục 2: ô không đọc được phải vào `dong_loi`, không vào `khoan_vay`**.

Đã tái hiện bằng DEMO: `tien_te="#N/A"`, `du_no="1.234.567.890"`, lãi suất hợp lệ → `dong_loi=[]`, dòng vẫn vào `khoan_vay`; báo cáo ghi `DU_DU_LIEU` và tổng dư nợ `{"#N/A": Decimal("1234567890")}`.

**Kiểm chứng:** tôi chạy đạt **20/20** test snapshot và **13/13** test báo cáo thuần, không skip. Năm test Excel gặp lỗi quyền tạo tệp tạm trong sandbox chỉ đọc; chưa xác nhận lại gate 38/38 của lead.

**Kết luận: chưa đạt để gộp; còn 1 điểm Chặn và mục Hỏi Claude.**

**Hỏi Claude**

- Claude xác nhận ô `#N/A` tại cột Tiền tệ thuộc yêu cầu loại ô lỗi của mục 2? `snapshot_sheet.py:100` — tình huống hỏng đã tái hiện; cần xác nhận phạm vi xử lý lỗi Sheet ở trường dạng chữ.
- `ghi_chu` tại `snapshot_sheet.py:173` có hiển thị trực tiếp cho người dùng không? Chưa rõ vì giao việc yêu cầu ghi “Cần Anh/lead”, còn mục B.5 cấm câu này trên giao diện.
---
**Lead lọc (Claude):**
- Chặn ô lỗi Sheet (`#N/A`…) ở trường chữ lọt vào khoản vay: **giữ Chặn** → vòng 2.
- `ghi_chu` "Cần Anh/lead" tại :173: **Nên sửa, làm cùng vòng 2** (câu trung tính; ghi chú cấu hình không phải chỗ ghi việc cần Anh).

## Review Codex VÒNG 2 (chỉ đọc) · 26/10 ~16:15

- **Ô lỗi Sheet — Đạt:** `src/kho_tri_thuc/m9/snapshot_sheet.py:202`, `:204`, `:237` nhận đủ 11 loại lỗi được giao ở mọi cột, ghi `O_LOI_SHEET` kèm dòng/cột và loại khỏi `khoan_vay`. Test tại `tests/test_m9_snapshot_sheet.py:164`, `:202` kiểm cả trường chữ và báo cáo không sinh nhóm tiền tệ lỗi.
- **Ghi chú trung tính — Đạt:** `src/kho_tri_thuc/m9/snapshot_sheet.py:195`; toàn tệp không còn “Cần Anh”/“Cần lead”.
- **Diff vòng sửa — Đạt trong phạm vi kiểm:** `src/kho_tri_thuc/m9/snapshot_sheet.py:84`, `:215` chuẩn hóa chữ hoa và kiểm danh sách tiền tệ/cách tính theo giao việc v2; chưa thấy hồi quy do phần sửa gây ra.

| Việc kiểm | Kết luận vòng 2 |
|---|---|
| Phạm vi | **Đạt:** đúng hai tệp được giao; dữ liệu test DEMO; báo cáo khớp nội dung diff và số lượng 48 test, không khai báo skip. |
| Đúng yêu cầu | **Đạt:** điểm Chặn vòng 1 đã sửa; đáp ứng các yêu cầu bổ sung trong giao việc v2. |
| Tiền, số liệu, quyền | **Đạt:** dòng lỗi bị loại trước báo cáo; tiền tệ ngoài cấu hình bị loại; diff không đổi phép tính hoặc quyền. |
| Không phá phần cũ | **Đạt trong phạm vi kiểm:** không đổi đường tính Decimal/date/hash; không thêm mạng hay AI. |
| Câu cho người dùng | **Đạt:** câu thông báo trung tính; định dạng ngày và đơn vị tiền không bị thay đổi. |

**Kiểm chứng:** đối chiếu mã nhánh bằng `git show`, diff đúng `f0a9caf → lat/m9-3a`. Không chạy lại test được vì sandbox từ chối thực thi Python; **48/48 đạt** là kết quả gate máy lead Anh cung cấp.

**Kết luận: Đạt để gộp trong phạm vi vòng 2.** Không còn **Chặn**; không có **Nên sửa / Để sau**.

**Hỏi Claude:** Không có mục cần làm rõ.
**Lead lọc (Claude):** Đạt, không lọc. Kiểm xác suất: khong.
