# UI-3c — Trang chủ hệ thống: không phụ thuộc phiên CRM; module tạm dừng hiện với mọi phiên (review dòng giao diện điểm 1–2)

Bạn là worker Codex, chạy không tương tác. Đọc `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261025\review-ui-dem.md` (Nên sửa 1, 2). **Làm ngay, không hỏi lại.** UTF-8 không BOM. Worktree hiện tại, nhánh `lat/ui-3c` (`lat/ui-dem`). Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL.

**Việc — `src/kho_tri_thuc/giao_dien/khung_khai_bao.py` (`dieu_huong`, `HE_THONG`, hàm dựng `/api/khung/he-thong`):**
1. `GET /api/khung/he-thong` **không gọi `app.crm_phien` trước mọi việc**: danh sách module tĩnh + thanh cố định luôn trả được; chỉ phần **số/quyền của CRM** cần phiên CRM — CRM chưa cấu hình / kho thật (lỗi `THAT_UI`, `CRM_CHUA_CAU_HINH`, phiên chưa sẵn sàng) → CRM hiện **không số**, không lỗi cả trang, **không tạo phiên CRM mới** (không để lại phiên mồ côi khi trang làm mới mỗi 60 giây — tìm cách `crm_phien` tạo phiên và chỉ lấy phiên có sẵn từ cookie, hoặc bỏ qua khi chưa có). Các route `/api/khung/module/crm` giữ hành vi cũ.
2. Module `tam_dung: True` (M9) **hiện với mọi phiên** (không lọc quyền), không số, không đường dẫn bấm được (giao diện đã hiện mờ "Tạm dừng"); module khác lọc quyền như cũ.
**Test — `tests/test_khung_he_thong.py`:** (a) CRM báo THAT_UI/chưa cấu hình → 200, có danh sách module + thanh cố định, CRM không số, **không gọi** hàm tạo phiên CRM; (b) M9 hiện với vai không có quyền M9, `tam_dung` true, không `so_viec`; (c) các ca cũ vẫn đạt.
**File (≤ 2):** `khung_khai_bao.py`, `tests/test_khung_he_thong.py` (+ `tests/test_khung_luoi_crm.py` chỉ khi ca cũ buộc đổi). Không sửa giao diện. Không xóa file.
**Chạy test:** `python -X utf8 -m unittest tests.test_khung_he_thong tests.test_khung_luoi_crm` (PYTHONPATH=`src;.;tests`) — ghi số trước/sau.
**Báo cáo (≤ ¼ trang):** sửa ở file:dòng · cách tránh phiên mồ côi · số test · thông điệp commit `[UI-3c] …`.
