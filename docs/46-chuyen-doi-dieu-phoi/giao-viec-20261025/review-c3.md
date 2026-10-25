# REVIEW C3 (CRM 42 · S1 `GET /api/crm/hop-dong`) · vòng 1/2 · reviewer Claude (chỉ đọc)

Bạn là reviewer chéo cho code do Codex viết. **Chỉ đọc**: không sửa tệp, không commit. Worktree `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\.claude\worktrees\lat-c3`, nhánh `lat/c3`, commit `5138079`; diff `git -C <worktree> diff hop-nhat-20261023...lat/c3` — `src/kho_tri_thuc/k2/crm_s1.py` (mới), `giao_dien/crm_g.py` (+route), `tests/test_crm_42_s1_tinh.py`, `tests/test_crm_42_s1_http.py`. Lead đã chạy `test_crm_*` với runtime có psycopg: 0 mã lỗi mới so với nền v4 (test PG skip vì chưa có DSN).

**Căn cứ:** `docs/CRM-42-00-MA-TRAN-MAN-HINH-VA-CA-KIEM.md` (D1, D3; § "S1 · Danh sách hợp đồng"; thẻ W1–W5) · `docs/CRM-42-00-DELTA-DU-LIEU-API-QUYEN.md` §1, §3.8, §4 (dòng route `GET /api/crm/hop-dong`: "đọc · theo vai + scope · rỗng không lộ số").

**Kiểm 5 việc, Đạt/Không:**
1. **Phạm vi/quyền:** người dùng chỉ thấy hợp đồng và **số đếm thẻ** trong phạm vi vai (bán hàng: của mình; KT/KTT/CFO theo pháp nhân + module CRM); lọc tham số (pháp nhân, dự án, người phụ trách…) không mở rộng được phạm vi; rỗng không lộ số ngoài phạm vi. Worker ghi "luồng B chưa có binding scope bán hàng tương đương; hiện giữ ẩn với bán hàng" — xác định luồng B là gì, ẩn có đúng hướng an toàn không, có cần lát khác không.
2. **SQL:** truy vấn tham số hóa (không ghép chuỗi giá trị người dùng); giới hạn quyền đặt trong SQL **trước** khi đọc dòng; phân trang sau giới hạn quyền đọc toàn bộ dòng — đánh giá tải với vài nghìn hợp đồng (Nên sửa nếu không chặn); không N+1 nặng.
3. **Ô Junsky "chưa có sổ" (D3) và ô thu theo CRM:** không trả 0 khi chưa có sổ; không gán số dư khách cho từng hợp đồng; tiền là chuỗi đơn vị nhỏ nhất, không float.
4. **PII:** không trả CCCD, số tài khoản, liên hệ, JSON thô; lỗi tham số HTTP 400 tiếng Việt + mã `CRM_S1_THAM_SO_SAI`; tham số lặp/quá dài/sai kiểu bị chặn.
5. **Test:** ca S1-a (phạm vi bán hàng), S1-b ("chưa có sổ"), thẻ W1–W5, lọc, PII theo vai có mặt và đúng nghĩa (không test rỗng); test PG viết đúng mẫu để chạy được khi có DSN.

**Báo cáo cuối (≤ 1 trang, tiếng Việt, ≤ 10 điểm):**
```
REVIEW C3 · vòng 1/2 · Claude
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
"Chặn" khi lộ dữ liệu/số đếm ngoài phạm vi, SQL ghép chuỗi, trả 0 thay "chưa có sổ", hoặc vi phạm ràng buộc cứng (dữ liệu thật, xóa tệp).
