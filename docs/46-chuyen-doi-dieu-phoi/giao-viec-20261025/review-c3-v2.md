# REVIEW C3 vòng 2/2 (CRM 42 · S1 `GET /api/crm/hop-dong`) · reviewer Claude (chỉ đọc)

Bạn là reviewer chéo cho bản sửa do Codex viết. **Chỉ đọc**: không sửa tệp, không commit, không nối CSDL. Worktree `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\.claude\worktrees\lat-c3`, nhánh `lat/c3`. Vòng 2 = commit `4bba86b` (`git -C <worktree> show 4bba86b`); vòng 1 = `5138079`. Lead đã chạy: PostgreSQL thật (CSDL tạm có bảng G5 M0032) `test_crm_42_s1_http` + `test_crm_42_s1_tinh` **34/34**, 0 skip.

**Review vòng 1 (của bạn, tóm tắt):** #1 SQL chưa chạy PG (nay đã chạy 34/34); #2 thiếu ca dương bán hàng có binding, BH khác không binding, khác dự án/khách, PII theo vai thật, ca "có sổ" Junsky; #3 luồng B ẩn với bán hàng (để lát C3b, chờ Anh); #4 ô tiền phải theo `XEM_TIEN` hoặc bán hàng trong binding (QD-20261025-15), vai XEM nhận null + nhãn; #5 tải: lọc đẩy vào CTE phạm vi, phần nặng chỉ cho trang ≤ 100, Junsky một lần, không giữ `mutation_lock` lâu; #8 `DataError` → 503, `khong_quyen`, bỏ `patcher.temp_original`; #7 đơn vị thẻ.

**Kiểm, Đạt/Không:**
1. #4 đúng QD-15 ở **mọi** đường trả tiền (giá trị HĐ, thu CRM, Junsky, chênh, đợt kế tiếp, W5) — không đường nào lộ tiền cho vai XEM/thiếu M1; kiểm trong SQL hoặc ngay sau phạm vi, không chỉ ở giao diện.
2. #5: phạm vi vẫn đóng **trước** khi đọc; lọc người dùng chỉ thu hẹp; phân trang không làm lệch thẻ đếm; kết nối đọc riêng không giữ `mutation_lock` suốt truy vấn dài; không SQL ghép chuỗi giá trị người dùng.
3. #2 test có nghĩa (ca dương BH có binding + thẻ đúng; BH khác 0; khác dự án/khách ẩn; JSON thật không CCCD/STK/`du_lieu`; có sổ Junsky: ngày chụp mới nhất, `con_lai` NULL, hai HĐ cùng khách).
4. #8, #7 đúng; không hồi quy route CRM khác trong `crm_g.py` (C3 vừa trộn hop-nhat có khối Dự án đang bán — khối S1 tách biệt).

**Báo cáo cuối (≤ ½ trang, tiếng Việt, ≤ 6 điểm):**
```
REVIEW C3 · vòng 2/2 · Claude
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
Vòng cuối: chỉ "Chặn" khi lộ dữ liệu/tiền/số đếm ngoài phạm vi hoặc SQL ghép chuỗi.
