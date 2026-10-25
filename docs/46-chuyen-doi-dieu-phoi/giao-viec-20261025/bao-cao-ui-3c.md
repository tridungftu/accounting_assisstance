Anh, đã sửa đúng 2 file, UTF-8 không BOM:

- [khung_khai_bao.py:131](src/kho_tri_thuc/giao_dien/khung_khai_bao.py#L131): CRM chưa sẵn sàng → trang vẫn 200, CRM không số; M9 luôn hiện, không số, giao diện giữ trạng thái không bấm được.
- [khung_khai_bao.py:312](src/kho_tri_thuc/giao_dien/khung_khai_bao.py#L312): chỉ tra phiên có sẵn bằng cookie; không gọi `crm_phien`, không tạo phiên mồ côi. Route module CRM giữ hành vi cũ.
- [test_khung_he_thong.py:107](tests/test_khung_he_thong.py#L107): bổ sung kiểm tra quyền M9, lỗi CRM và làm mới nhiều lần.

Test yêu cầu: **trước 41/41 → sau 43/43**, không lỗi mới; `git diff --check` đạt. Không commit, không mở server/PostgreSQL.

Thiếu `review-ui-dem.md` trong worktree.

Thông điệp commit đề xuất: `[UI-3c] Trang chủ độc lập phiên CRM, luôn hiện module tạm dừng`