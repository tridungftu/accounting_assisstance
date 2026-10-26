# MTQ-0 — Thiết kế lát "Ma trận thẩm quyền" (CD-012 + CD-010 mục 4) — viết tài liệu thiết kế, chưa code

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.** Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM — ghi tệp bằng UTF-8. Sandbox không ghi `.git`: **không commit**. Không xóa file. Worktree hiện tại, nhánh `lat/mtq-0` (hợp nhất). Đọc hộp thư `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` **CD-010 mục 4** và **CD-012** (Anh đã chốt: bảng ô tick vai × module × hành động; 1 cột giới hạn số tiền VND; chỉ Admin cấp/sửa; nhật ký mỗi lần sửa; Anh tự tick, DEMO có bản mẫu; ma trận là nguồn quyền duy nhất sau khi bật).

**Việc:** đọc mô hình quyền hiện có (`ha_tang/pg_migrations.py`: `master.nguoi_dung`, vai/quyền theo pháp nhân, `master.ktt_duoc`, `master.ktt_co_vai`, quyền module CRM/M2/M4/M1…; `giao_dien/khung_khai_bao.py`; seed DEMO `k2/crm_demo.py`, `k2/crm_g_demo.py`, `k2/m4_demo.py`), rồi viết `docs\46-chuyen-doi-dieu-phoi\THIET-KE-MA-TRAN-THAM-QUYEN.md`:
1. Mô hình dữ liệu: bảng ma trận theo pháp nhân/phòng × vai × module × hành động, cột giới hạn tiền, phiên bản + nhật ký, vai Admin.
2. **5 vai** theo cấp CD-010 (Người thực hiện 1 · Người thực hiện 2 · Trưởng phòng · CFO · đề xuất vai thứ 5, vd Người xem) và **bảng ánh xạ** vai cũ (BAN_HANG, KE_TOAN, KE_TOAN_TRUONG, CFO, XEM, DU_AN…).
3. Danh sách module × hành động (xem · lập · sửa · kiểm · duyệt · hủy) **thực có trong code** (liệt kê hàm/route đang kiểm quyền).
4. Cách **bật ma trận làm nguồn quyền duy nhất** an toàn: chuyển tiếp (ma trận chưa bật = giữ quyền cũ), bật theo pháp nhân, máy chủ kiểm ở một hàm chung; chặn duyệt vượt giới hạn tiền + ghi lý do chặn.
5. Màn hình: bảng tick, gấp/mở theo module, cột giới hạn tiền, chỉ Admin sửa.
6. **Chia lát** ≤ 3–5 tệp: MTQ-1 SQL/migration, MTQ-2 dịch vụ/HTTP, MTQ-3 màn hình, MTQ-4 nối kiểm quyền (rủi ro cao — review Opus), MTQ-5 seed DEMO 5 vai.
7. Mục **"Mặc định lead chọn"** (vd giới hạn tiền áp hành động duyệt; …) để đưa vào phiếu cổng A.

Không sửa mã. **Báo cáo (≤ ¼ trang):** tóm tắt mô hình + lát, thông điệp commit `[MTQ-0] …`.
