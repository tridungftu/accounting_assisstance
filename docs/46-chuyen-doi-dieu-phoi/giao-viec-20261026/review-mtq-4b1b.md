## Review Codex (chỉ đọc) — mtq-4b1b · 26/10 ~20:30

- **(a) Đạt — PN tắt giữ đường cũ:** biểu thức quyền và mã từ chối được giữ; có oracle so trước/sau và ca PN khác đã bật. `src/kho_tri_thuc/k2/sql_mtq_crm.py:50`; `tests/test_mtq_crm_sql.py:305,452`.
- **(b) Đạt — PN bật chỉ theo ma trận:** gọi M0047, yêu cầu nguồn `MA_TRAN`, trả ngay trước nhánh quyền cũ; không OR/AND hoặc fallback. `src/kho_tri_thuc/k2/sql_mtq_crm.py:40–49`.
- **(c) Đạt — tách nhiệm và kiểm trước replay:** giữ duyệt mẫu khác người kiểm; bổ sung duyệt bộ chuẩn khác cả người lập và người gửi khi bật; guard chạy trước tra biên nhận. `src/kho_tri_thuc/ha_tang/pg_migrations.py:12204`; `src/kho_tri_thuc/k2/sql_mtq_crm.py:87–88`; `tests/test_mtq_crm_sql.py:371,391`.
- **(d) Đạt — giữ ranh giới nền:** chỉ append migration G1/G7; không sửa `ktt_duoc`, `ktt_pn_cho_phep`, policy/RLS nền, G2–G6 hoặc tỷ giá. `src/kho_tri_thuc/ha_tang/pg_migrations.py:12188–12207`; `tests/test_mtq_crm_sql.py:71`.

| Việc kiểm | Kết luận |
|---|---|
| **1. Phạm vi** | **Đạt.** Đúng ba tệp được giao; fixture tự sinh, không thấy dữ liệu thật. Báo cáo khớp **22 test = 7 tĩnh + 15 PG**, ghi đúng NOT_RUN tại máy worker. |
| **2. Đúng yêu cầu** | **Đạt.** Ánh xạ đúng từng lệnh G1/G7; dùng đối tượng/FK thật. Giữ chặn nháp/lịch sử và đọc typed khi bật theo quyết định lead. |
| **3. Tiền, số liệu, quyền** | **Đạt.** G1/G7 thuộc `PHI_TIEN`, truyền NULL đúng hợp đồng; quyền kiểm tại SQL. Khóa cấu hình và danh tính được giữ trước quyết định/replay. |
| **4. Không phá phần cũ** | **Đạt.** Migration cũ nguyên vẹn; giữ guard chủ bảng, CAS, digest và bất biến. Không thêm lời gọi API AI trực tiếp. |
| **5. Giao diện/câu người dùng** | **Đạt trong phạm vi lát.** Không đổi UI hay định dạng ngày/tiền; “Cần lead” chỉ nằm trong comment. |

**Chặn: 0 · Nên sửa: 0 · Để sau: 0.**

**Kết luận: Đạt để gộp trong phạm vi MTQ-4b1b**, dựa trên review tĩnh và gate lead cung cấp: module 22 test OK, các module CRM khác không thêm lỗi so v5. Tôi không chạy PostgreSQL/test; `git diff --check` đạt. Kết luận này không chứng nhận sẵn sàng bật PN.

**Hỏi Claude:** Không có điểm cần làm rõ.
**Lead lọc (Claude):** Đạt. Kiểm xác suất: khong.
