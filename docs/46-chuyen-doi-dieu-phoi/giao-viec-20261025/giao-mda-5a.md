# MDA-5a — Mốc riêng dự án: một quy tắc "+ n ngày" (n 1–3650) cho Báo giá và Danh sách hợp đồng; kiểm mốc khi sửa lịch lúc soạn hợp đồng

Bạn là worker Codex, chạy không tương tác. Đọc `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261025\review-mda-cum.md` (Nên sửa 2, 3). **Làm ngay, không hỏi lại.** UTF-8 không BOM. Worktree hiện tại, nhánh `lat/mda-5a` (từ `lat/mda-gom`). Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL (test PG tự skip — lead chạy).

**Việc:**
1. Một quy tắc mã mốc riêng: `^DAM-<uuid>(?:_([1-9][0-9]{0,3}))?$` với n ≤ 3650 — đặt hằng số dùng chung (một chỗ trong `src/kho_tri_thuc/k2/crm_giao_ket.py`, `crm_s1.py` import lại) cho Python; phần SQL trong `crm_s1.py` (`_sql`, nối mốc) dùng **đúng cùng** biểu thức và chặn n > 3650 (không ép kiểu khi không khớp). Báo giá: `_0007`, `_0`, `_3651`, n quá dài → lỗi theo trường như mã sai. S1: mã không khớp quy tắc → đợt giữ `MOC_CHUA_CO_NGAY`, **không bao giờ** lỗi cả danh sách.
2. `crm_giao_ket.py` `luu_soan` (~:1311, sửa lịch khi soạn hợp đồng) gọi `_kiem_moc_du_an` trong **cùng giao dịch** như đường lưu báo giá (MDA-3s); nếu `GK_SHA256` ghim băm `crm_giao_ket.py` → cập nhật trong `tests/test_crm_ky_ket.py` như MDA-3s đã làm.
**Test:** thêm vào `tests/test_crm_moc_du_an_bao_gia.py` (quy tắc n, `luu_soan` kiểm mốc) và `tests/test_crm_s1_moc_du_an.py` (mã `_0007`/`_99999`/rác → không lỗi danh sách, đợt `MOC_CHUA_CO_NGAY`; SQL không ép kiểu giá trị không khớp — kiểm tĩnh chuỗi SQL + phần PG `skipUnless KHO_PG_DSN_TEST`).
**File:** `k2/crm_giao_ket.py`, `k2/crm_s1.py`, 2 tệp test trên (+ `tests/test_crm_ky_ket.py` chỉ dòng `GK_SHA256`). Không sửa SQL migration. Không xóa file.
**Chạy test:** `python -X utf8 -m unittest tests.test_crm_moc_du_an_bao_gia tests.test_crm_s1_moc_du_an tests.test_crm_ky_ket tests.test_crm_42_s1_http` (đặt `PYTHONPATH` = `src;.` nếu cần) — ghi số trước/sau.
**Báo cáo (≤ ¼ trang):** sửa ở file:dòng · số test · thông điệp commit `[MDA-5a] …`.
