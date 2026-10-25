# review-lat MDA-1a vòng 1 (Opus, 25/10 23:19) — KHÔNG ĐẠT (1 Chặn)

1. **Chặn — `crm_da_moc_ten_chuan` hỏng khi PostgreSQL chạy locale C** (cụm DEMO 5432: `lc_* = C`, không ICU; CSDL test tạo từ `template0`). Hàm gọi `upper()` trước rồi `translate` với nguồn chỉ có chữ HOA dựng sẵn + dấu tổ hợp; locale C `upper()` chỉ đổi ASCII → "Xong chứng nhận đầu tư" thành `XONG CHứNG NHậN đầU Tư`; trùng tên khác hoa thường/dấu không bị bắt, `đ→d` không hiệu lực. Test tĩnh xanh giả vì mô phỏng bằng `str.upper()` của Python. Sửa: nguồn `translate` gồm cả chữ thường dựng sẵn + `đ`/`Đ` (→ chữ hoa không dấu), `translate` trước rồi `upper`; test tĩnh mô phỏng `upper` chỉ đổi ASCII.
2. Để sau — race trùng tên: trigger + khóa dòng `crm_da_ban` chỉ an toàn ở READ COMMITTED; giữ RC ở đường ghi (MDA-1b).
3. Để sau — test tĩnh khóa `PG_MIGRATIONS[-2] is M0034_CONG_AI_NHAT_KY` và chuỗi `"# 0035 — MDA-1a:"`: đổi cùng lúc khi đánh lại số sau KY-DOCX.
4. Để sau — báo cáo thiếu danh sách ca; câu lỗi "cần ngày dự kiến khi khai mốc" hiện cả ở nhánh sửa khi gửi `ngay_du_kien: null`.
Đạt: quyền/biên nhận/khóa dòng/RLS/REVOKE/INVOKER + search_path; migration chỉ append; test PG phủ đủ ca handoff, có assert thật.
