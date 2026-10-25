# MDA-1a vòng 2 — sửa điểm Chặn review: chuẩn hóa tên mốc đúng khi PostgreSQL chạy locale C

Bạn là worker Codex, chạy không tương tác. Đọc `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261025\review-mda-1a.md` (điểm 1 Chặn, điểm 3–4) và handoff gốc `giao-mda-1a.md`. **Làm ngay, không hỏi lại.** UTF-8 không BOM — ghi tệp bằng UTF-8. Worktree hiện tại, nhánh `lat/mda-1b` (đã có MDA-1a + MDA-1b). Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL.

**Việc:**
1. `src/kho_tri_thuc/k2/sql_crm_du_an_moc.py`, hàm `master.crm_da_moc_ten_chuan`: **không phụ thuộc locale** — `translate` TRƯỚC với chuỗi nguồn gồm **đủ chữ thường và chữ hoa dựng sẵn tiếng Việt** (a ă â e ê i o ô ơ u ư y với 5 dấu + không dấu, cả hoa lẫn thường) và `đ`/`Đ` → chữ **hoa** không dấu tương ứng; bỏ dấu tổ hợp (U+0300, U+0301, U+0303, U+0309, U+0323, U+0306, U+0302, U+031B); rồi mới `upper()` (chỉ còn ASCII) + gộp khoảng trắng/`btrim`. Hai chuỗi nguồn/đích phải cùng độ dài ký tự — thêm kiểm tĩnh trong test.
2. `tests/test_crm_du_an_moc_pg.py`: test tĩnh mô phỏng `translate` + `upper` **chỉ đổi ASCII** (như locale C), kiểm "Xong chứng nhận đầu tư", "XONG CHỨNG NHẬN ĐẦU TƯ", "xong chung nhan dau tu", dạng NFD → cùng một khóa; thêm ca PostgreSQL (skipUnless DSN) `SELECT master.crm_da_moc_ten_chuan(...)` cho 3 dạng trên bằng nhau. Điểm 3 review: bỏ khóa cứng `PG_MIGRATIONS[-2] is M0034…` và chuỗi `"# 0035 — MDA-1a:"` — thay bằng kiểm "migration mốc là phần tử sau M0034 và các migration trước giữ nguyên" (để lead đánh lại số 35/36 khi gộp sau KY-DOCX không phải sửa test).
3. Điểm 4 review: lỗi khi gửi `ngay_du_kien: null` ở nhánh sửa mốc cũ → câu riêng "Ngày dự kiến không được để trống".
**File (≤ 2):** `src/kho_tri_thuc/k2/sql_crm_du_an_moc.py`, `tests/test_crm_du_an_moc_pg.py`. Không sửa migration cũ. Không xóa file.
**Chạy test:** `python -X utf8 -m unittest tests.test_crm_du_an_moc_pg tests.test_crm_du_an_moc` — ghi số.
**Báo cáo (≤ ⅓ trang):** sửa ở file:dòng · số test · thông điệp commit `[MDA-1a] vòng 2: …`.
