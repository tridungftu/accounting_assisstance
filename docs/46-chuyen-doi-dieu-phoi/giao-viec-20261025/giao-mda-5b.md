# MDA-5b — Mốc riêng vẫn hiện và vẫn sinh việc chờ khi dự án ngừng bán (review cụm MDA điểm 4, lead quyết)

Bạn là worker Codex, chạy không tương tác. Đọc `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261025\review-mda-cum.md` (Nên sửa 4 + "Lead quyết điểm 4"). **Làm ngay, không hỏi lại.** UTF-8 không BOM. Worktree hiện tại, nhánh `lat/mda-5b` (từ `lat/mda-5a`). Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL (test PG tự skip — lead chạy).

**Việc — `src/kho_tri_thuc/k2/sql_crm_du_an_moc.py` (M0035 chưa gộp nơi nào — sửa trực tiếp, không thêm migration):**
1. `master.crm_da_moc_doc(p_du_an, p_ngay)`: trả mốc **đang dùng** của dự án **đã có trong danh mục dự án đang bán** (`crm_da_ban` có dòng — đang bán **hoặc ngừng bán**), bỏ điều kiện chỉ khi `dang_ban`. Dự án chưa từng bật bán → mảng rỗng (như cũ). Thêm vào mỗi phần tử trường `du_an_dang_ban` (boolean) để giao diện biết.
2. Không đổi quyền, không đổi `crm_da_moc_ghi`.
**Test — `tests/test_crm_du_an_moc_pg.py`:** sửa ca `test_du_an_chua_bat_ban_ngung_ban…` theo hành vi mới: chưa bật bán → rỗng; **ngừng bán → vẫn trả mốc**, `du_an_dang_ban = false`, mốc quá dự kiến vẫn `QUA_DU_KIEN`. Kiểm tĩnh SQL không còn điều kiện `dang_ban` trong `crm_da_moc_doc`.
**Kiểm thêm (chỉ đọc, báo cáo):** `k2/crm_du_an_ban.py` `danh_muc_moc` (Báo giá) — Báo giá mới chỉ chọn dự án đang bán nên không cần đổi; nếu `danh_muc_moc` của dự án ngừng bán đang trả mốc riêng cho báo giá → giữ nguyên (bản in báo giá cũ vẫn ra tên mốc), ghi rõ trong báo cáo.
**File (≤ 2):** `k2/sql_crm_du_an_moc.py`, `tests/test_crm_du_an_moc_pg.py`. Không xóa file.
**Chạy test:** `python -X utf8 -m unittest tests.test_crm_du_an_moc_pg tests.test_crm_du_an_moc` — ghi số trước/sau.
**Báo cáo (≤ ¼ trang):** sửa ở file:dòng · số test · thông điệp commit `[MDA-5b] …`.
