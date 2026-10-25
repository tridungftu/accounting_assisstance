# REVIEW DA-1 (CRM · Dự án đang bán — máy chủ + M0031) · vòng 1/2 · reviewer Codex (chỉ đọc)

Bạn là reviewer chéo, chạy không tương tác (`codex exec`, sandbox chỉ đọc). Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8. Python (nếu cần, test thuần): `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module test_crm_du_an_ban` (thiếu psycopg là bình thường).

**Đối tượng:** worktree hiện tại, nhánh `lat/da-1` (3 commit `95f1169`, `bc48ac2`, `b9adfe7`); diff `git diff hop-nhat-20261023...lat/da-1` — `ha_tang/pg_migrations.py` (append M0031), `k2/sql_crm_du_an_ban.py` (mới), `k2/crm_du_an_ban.py` (mới), `k2/crm_mau.py`, `giao_dien/crm_g.py` (khối `_dieu_huong_da`), `tools/chuan_bi_crm_demo.py`, `tests/test_crm_du_an_ban.py`, `tests/test_crm_du_an_ban_pg.py`. Worker báo: test thuần 29/29; PG 12/12 trên CSDL DEMO riêng; 0 mã lỗi mới.
**Căn cứ:** `docs/46-chuyen-doi-dieu-phoi/THIET-KE-DU-AN-DANG-BAN.md`; `docs/QUYET-DINH.md` QD-20261025-05…09 (dự án chọn từ `master.du_an`; **bán hàng tự sửa, hiệu lực ngay, có phiên bản + nhật ký, kể cả tiến độ G7 — bỏ CFO duyệt**; lưu đơn giá niêm yết + tiền tệ, loại hình + thuế, lô/căn, tiến độ, phí; báo giá sửa riêng → "khác tiêu chuẩn").

**Kiểm 5 việc, Đạt/Không:**
1. **M0031 an toàn:** chỉ APPEND (M0001–M0030 trùng byte với hop-nhat — tự kiểm SHA phần đầu); thay đổi trên bảng cũ duy nhất là nới CHECK `valid_to > valid_from` → `>=` của bộ chuẩn G7 — đánh giá: khoảng rỗng có thể bị chọn nhầm ở chỗ nào đang đọc bộ chuẩn (`crm_g_chuan_doc`, `crm_kiem_g7`, `crm_kiem_lich_ky` M0030, tính thử báo giá)? Không DROP/đổi nghĩa hàm cũ.
2. **Bất biến + nhật ký:** phiên bản đã tạo không sửa được (trigger), chỉ đóng `hieu_luc_den` một lần; sửa = đóng cũ + thêm mới + `nhat_ky.su_kien` trong cùng giao dịch; khóa lạc quan `expected_phien_ban` / `expected_lan` chống ghi đè đồng thời; idempotent `khoa`.
3. **G7 áp dụng ngay:** `crm_g_chuan_ap_dung` đóng bản đang hiệu lực đúng hôm nay, không sửa trạng thái/người duyệt của bản CFO cũ; không áp chồng bản CFO có ngày hiệu lực tương lai; mọi nơi đọc "bộ chuẩn hiệu lực" nhận bản mới; đọc theo ngày quá khứ ra bản cũ.
4. **Quyền:** đọc cần module CRM; ghi chỉ BAN_HANG/KE_TOAN/KE_TOAN_TRUONG có CRM, theo pháp nhân của dự án; kiểm ở CSDL theo phiên trước khi tra biên nhận; người XEM hoặc khác pháp nhân không ghi/đọc được qua bất kỳ route nào.
5. **Tiền + tham số:** đơn giá, mức phí, diện tích parse chặt (chữ số ASCII, miền khớp SQL, không float); lỗi theo `truong`; route `GET/POST /api/crm/du-an-ban…` kiểm tham số lạ/lặp/quá dài; ảnh chụp `anh_chup_sha256` ổn định (không phụ thuộc ngày gọi) và đủ cho DA-3 so lại.

**Báo cáo cuối (≤ 1 trang, tiếng Việt, ≤ 10 điểm):**
```
REVIEW DA-1 · vòng 1/2 · Codex
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
"Chặn" khi M0031 đổi byte 1–30 hoặc phá nghĩa bộ chuẩn cũ, người không có quyền ghi/đọc được, phiên bản sửa được tại chỗ, tiền parse sai, hoặc vi phạm ràng buộc cứng.
