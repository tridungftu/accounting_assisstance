# UI-2b — Khung lưới CRM: số trên icon đúng loại việc TL 42 §3; không trả tổng bị cắt (theo review-lat UI-2)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2, §4). UTF-8 không BOM — **ghi tệp bằng UTF-8** (chữ tiếng Việt không được thành `?`). Worktree hiện tại, nhánh `lat/ui-2b` (từ hop-nhat, đã có UI-2 af7c389). Sandbox không ghi `.git`: **không commit**. Không nối CSDL, không mở server (lead chạy test PostgreSQL).

**Căn cứ:** TL 49 §3 (`D:\Claude\Phan mem ho tro ke toan\49-trang-chu-luoi-icon.md`) — số đỏ trên icon dùng **loại việc của TL 42 §3** (`D:\Claude\Phan mem ho tro ke toan\42-man-hinh-crm-ke-toan-va-giao-ket.md` §3); hợp đồng dữ liệu `docs/46-chuyen-doi-dieu-phoi/HOP-DONG-DU-LIEU-KHUNG-LUOI.md` §2b.

**Việc (`src/kho_tri_thuc/giao_dien/khung_khai_bao.py`):**
1. Số trên icon (~:67-84): **Bán hàng** — Hợp đồng = W1 (bị trả lại/cần bổ sung) + W2 (chờ ký), **không** đặt số ở Thu tiền; **Kế toán** — Thu tiền = số HĐ có đợt **đến hạn trong 7 ngày** (W5, cùng điều kiện quyền xem tiền QD-15/22), không dùng quá hạn; **CFO** — Hợp đồng = số HĐ `trang_thai=CHO_DUYET` (S1 có sẵn). Mỗi số vẫn phải bằng đúng số của danh sách mở theo `loc` (cùng service). `qua_han` (nền đỏ) chỉ bật khi thật sự có việc quá hạn/bị chặn (TL 49 §1.5) — thẻ "Mẫu hợp đồng chờ duyệt" của CFO không phải quá hạn.
2. Danh sách báo giá chạm 200 dòng (~:115-117): trả `tong: null` (kèm `day_du: false`), không trả số đã cắt.
3. Vai Người xem: không chạy truy vấn W5 vô ích (~:57) — vai này không bao giờ có quyền xem tiền.
4. Test `tests/test_khung_luoi_crm.py`: cập nhật/ thêm ca cho 1–3 (Bán hàng W1+W2, không số Thu tiền; Kế toán đến hạn 7 ngày; CFO chờ duyệt; báo giá 205 dòng → `tong` null; người xem không gọi W5).

**File được sửa (chỉ 2):** `src/kho_tri_thuc/giao_dien/khung_khai_bao.py`, `tests/test_khung_luoi_crm.py`. Không xóa file.
**Test:** `--module test_khung_luoi_crm` (thuần); sandbox chặn python → ghi "lead chạy test".
**Báo cáo cuối (≤ ⅓ trang):** sửa ở file:dòng · bảng số icon 4 vai trước/sau · ca test · thông điệp commit `[UI-2b] …`.
