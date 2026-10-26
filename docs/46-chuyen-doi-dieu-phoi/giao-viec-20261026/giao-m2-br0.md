# M2-BR0: kiểm kê đường nhận hóa đơn BÁN RA trong M2 phục vụ M3 (chỉ đọc, chỉ báo cáo; CD-013)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không sửa mã. Không mở server. Không xóa file.
- Không đọc kho thật, tệp bí mật, `var\`.
- Làm trong worktree hiện tại, nhánh `lat/m2-br0`, dựng từ hợp nhất.

**Bối cảnh:** M3-1a (`k2/sql_m3.py`, chưa gộp, đọc bằng `git show lat/m3-1a:src/kho_tri_thuc/k2/sql_m3.py`) liên kết hóa đơn M2 với hợp đồng. Worker M3-1a báo "M2 hiện chỉ hỗ trợ `MUA_VAO`; cần lát promote `BAN_RA`". Thiết kế M3 v2 §4 cho dùng lại bộ đọc XML/ZIP và cơ chế nguồn của M2; **không** tạo kho hóa đơn M3 song song.

**Việc: viết `docs\46-chuyen-doi-dieu-phoi\M2-BAN-RA-KIEM-KE.md` (≤ 2 trang).**
1. Chỗ nào trong M2 cố định chiều `MUA_VAO`: enum, CHECK SQL, RLS, mapping công ty, route, giao diện, bộ tải cổng thuế. Ghi tệp:dòng.
2. Những gì dùng lại nguyên được cho hóa đơn bán ra:
   - bộ đọc XML;
   - danh tính hóa đơn (MST bán/mua, ký hiệu, số);
   - nguồn có phiên bản, raw, receipt;
   - các trường net chịu thuế, không chịu thuế, VAT, tổng;
   - hóa đơn điều chỉnh/thay thế.
3. Những gì phải thêm hoặc đổi để nhận `BAN_RA`:
   - xác định chiều theo MST pháp nhân là người bán;
   - quyền xem theo kế toán bán hàng/doanh thu;
   - không lẫn với tải mua vào;
   - chống trùng.
4. **Đề xuất chia lát ≤ 3 tệp/lát**, thứ tự, tệp dùng chung bị đụng (`pg_migrations.py`, `server.py`…), rủi ro.
5. Ghi rõ điểm "Cần Anh", ví dụ: nguồn hóa đơn bán ra lấy từ cổng thuế hay xuất từ phần mềm hóa đơn của tập đoàn.

Không chạy test, không sửa mã. **Báo cáo (≤ 5 dòng)**, thông điệp commit `[M2-BR0] …`.
