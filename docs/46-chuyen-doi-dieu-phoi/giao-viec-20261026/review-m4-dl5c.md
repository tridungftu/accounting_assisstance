## Review Codex (chỉ đọc) — m4-dl5c · 26/10 ~17:37

1. **(a) Đạt:** seal M4 được ưu tiên trước kiểm liên kết Review; mỗi đợt chỉ chọn một nguồn — `src/kho_tri_thuc/m4/duyet_dot.py:218`.
2. **(b) Không — còn điểm cần xác nhận:** ĐVT, mã trùng, ngày và hai ca liên kết cùng số được kiểm; nhưng Review khác số dù `m4_dot_id` trỏ đúng đợt M4 vẫn bị loại — `duyet_dot.py:223`. Giao việc mục 1 dùng điều kiện “cùng số **hoặc** `m4_dot_id` trỏ đúng”; trả lời lead chỉ mô tả cùng số.
3. **(c) Đạt qua đọc mã:** khi không có đợt riêng từ Review, giữ đường tính cũ — `duyet_dot.py:180`; có test so byte khi Review chỉ trùng đợt đã seal — `tests/test_m4_dl5b_lich_su.py:494`.
4. **(d) Đạt:** đọc chép bằng chính `c` — `duyet_dot.py:178`; hàm đọc kiểm quyền XEM và quyền SELECT, không đổi kết nối — `src/kho_tri_thuc/m4/review_dot_pg.py:70`.
5. **(e) Đạt:** nguồn `REVIEW_CHEP` nằm trong `truoc_da_duyet`, được ghi vào JSON kết luận theo cấu trúc hiện hữu — `duyet_dot.py:328`, `duyet_dot.py:906`.

**Năm kiểm tra bắt buộc:**

- **Phạm vi — Đạt:** chỉ đổi hai tệp được giao; fixture DEMO; báo cáo khớp diff và ghi đúng `NOT_RUN`.
- **Đúng yêu cầu — Chưa kết luận:** còn cách hiểu tại (b), mức **Nên sửa**, chưa đủ căn cứ ghi Chặn.
- **Tiền, số liệu, quyền — Đạt qua đọc mã:** cộng KL kỳ bằng Decimal, giữ thiếu khác 0; quyền kiểm tại máy chủ.
- **Không phá phần cũ — Đạt qua đọc diff:** giữ nhánh cũ khi không áp dụng Review; không thêm lời gọi AI trực tiếp.
- **Giao diện/câu chữ — Đạt trong diff:** không sửa JS, không thêm cách hiển thị ngày/tiền; các lý do mới bằng tiếng Việt.

`git diff --check` đạt. Unittest **NOT_RUN** vì môi trường không có Python; chưa xác nhận gate test/PG. **Không phát hiện Chặn; chưa kết luận Đạt toàn lát vì còn “Hỏi Claude”.**

**Hỏi Claude**

Review đợt 1 liên kết `m4_dot_id` đúng tới M4 đợt 2, xét trước đợt 3: phải tính hay `CAN_XEM_LAI`? — `src/kho_tri_thuc/m4/duyet_dot.py:223`; chưa rõ vì giao việc cho phép “hoặc liên kết đúng”, còn bổ sung của lead chỉ nói trường hợp cùng số.
**Lead lọc (Claude):** Hỏi Claude → Review đợt khác số dù m4_dot_id trỏ đúng: **CAN_XEM_LAI** (lệch số = đánh số lại, chưa chắc cùng đợt; thà bỏ sót còn hơn nhập sai) — giữ hành vi hiện tại. Đạt. PG 183 ok, 0 mã mới so v5. Kiểm xác suất: khong.
