# REVIEW C1a (M0032 — gắn SQL G5-B đối chiếu bản ký ↔ bản sinh) · vòng 1/2 · reviewer Codex (chỉ đọc)

Bạn là reviewer chéo cho phần lead (Claude) làm, chạy không tương tác (`codex exec`, sandbox chỉ đọc). Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8.

**Đối tượng:** worktree hiện tại, nhánh `lat/c1a`, commit `0b636d1` (+12 dòng cuối `src/kho_tri_thuc/ha_tang/pg_migrations.py`: `from ..k2.sql_crm_doi_chieu import CRM_G5_SQL`; `M0032_CRM_G5 = CRM_G5_SQL`). SQL G5 có sẵn trong `src/kho_tri_thuc/k2/sql_crm_doi_chieu.py` (gói G5-B, docstring: "owner cấp ordinal và APPEND"). Lead đã áp thật trên CSDL DEMO mới (schema 32, không lỗi) và chạy `test_crm_*` với PostgreSQL: 0 mã lỗi mới so với nền PostgreSQL.

**Kiểm 4 việc, Đạt/Không:**
1. M0001–M0031 trùng byte với hop-nhat; M0032 chỉ append; `CRM_G5_SQL` không trùng/định nghĩa lại hàm, bảng, trigger đã có ở M0001–M0031 (tìm `CREATE OR REPLACE` chạm hàm cũ — nếu có, kiểm chữ ký/kiểu trả giữ nguyên).
2. **Ảnh hưởng luồng ký hợp đồng:** trigger AFTER INSERT trên `master.crm_hd_ky` (ghi việc G5 trong cùng giao dịch ký) — có thể làm ký thất bại trong trường hợp nào (thiếu đăng ký engine/người chạy)? G5 VAN_HANH vẫn HOLD như ghi chú M0025: xác nhận không có đường tự seed đăng ký engine, không tự cấp vai/phạm vi, không gọi engine thật khi chưa đăng ký.
3. Quyền/RLS: bảng mới có quyền đọc/ghi đúng mẫu G6A (vai ứng dụng không ghi trực tiếp; chủ CSDL ghi qua hàm).
4. Thứ tự: G5 cần các đối tượng G6A (M0025)/M0026 — tham chiếu đều có trước M0032.

**Báo cáo cuối (≤ ½ trang, tiếng Việt, ≤ 6 điểm):**
```
REVIEW C1a · vòng 1/2 · Codex
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
"Chặn" khi M0032 có thể làm hỏng việc ký hợp đồng đang chạy, đổi nghĩa đối tượng cũ, hoặc tự kích hoạt G5 vận hành.
