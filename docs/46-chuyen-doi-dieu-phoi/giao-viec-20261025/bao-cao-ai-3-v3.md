Anh, đã hoàn tất vòng 3, **không commit**. Chỉ đổi bốn file, UTF-8 không BOM.

- `cloud.py:181,287`: chỉ truyền hai nhóm cấu hình; nhóm lỗi ghi lý do vào `khong_gui`, tiếp tục nhóm sau.
- `ai_cloud.py:88`: `so_khong_gui` chỉ tăng khi bị chặn trước gửi Cloud.
- `tests/test_ai0_khoa_cloud.py:289,368,427`: thêm regression cấu hình, ba tình huống lỗi nhóm đầu và điều kiện skip.
- `nguon_review.py:45,48`: cập nhật đúng hai PIN theo byte trên đĩa.

**Test:** 54/54 AI/cổng + 50/50 `test_m4_01b_tinh` + 23/23 test thuần engine #6 = **127/127**, không skip, không lỗi mới; `git diff --check` đạt.

**Giới hạn còn lại:** `chat_json` chỉ nhận `ket_qua`/`vi_tri`; `thay_doi`/`dong` báo lỗi khi bật Cloud, bên gọi đã bắt. Tìm vị trí còn một ID/tham số thay vì tối đa ba. Cloud không giữ `don_vi`/`dieu_khoan`/`ghi_chu`. “Không quy định” không vượt kiểm giá trị nằm trong trích dẫn.

Thông điệp commit: `[AI-3] vòng 3: sửa cấu hình cổng, tiếp tục nhóm lỗi và cập nhật PIN Review`.