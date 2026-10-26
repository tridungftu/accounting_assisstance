# M4-DL4 vòng 2: lớp đọc đợt/KL/ghép/cảnh báo/nhật ký chỉ cho quyền XEM (không REVIEW). Điểm Chặn của review.

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở PostgreSQL; test PG tự tạo CSDL `kho_test_*`. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m4-dl4` (1536939 + merge hợp nhất).

**Lỗi:** `m4/review_dot_pg.py` (khoảng dòng 202) dùng kiểm quyền DL2 "XEM **hoặc** REVIEW". Lược đồ DL1 cố ý để 5 bảng này **chỉ XEM**: `sql_review_chep.py` khoảng dòng 223–232, "Lịch sử đợt chưa nộp chỉ XEM, không cho REVIEW đọc như đợt đã nộp". Quy tắc M4 hiện hành cũng chỉ cho REVIEW thấy đợt `DA_NOP` (`sql_m17.py:762`). Repository đọc bằng kết nối chủ bảng, nên đi vòng qua RLS.

**Sửa (chỉ 2 tệp của lát):**
1. Làm như DL3: dùng `reader._kiem_quyen_doc` rồi `reader._nguon_hien_hanh` của DL2, không gọi cả lớp đọc đầy đủ. Bỏ đoạn SQL 3 trạng thái NULL bị chép lại (khoảng dòng 205–211).
2. **Kiểm thêm quyền XEM.** Sau khi qua kiểm chung, chạy trên `conn_phien`:
   `SELECT EXISTS (SELECT 1 FROM master.hop_dong h WHERE h.id = %s::uuid AND h.module_chu = 'M4' AND master.m4_duoc(h.du_an_id, 'XEM'))`
   Sai → `M4_REVIEW_KHONG_THAY` (404), **trước** mọi lần đọc bằng kết nối chủ bảng.
3. Sửa docstring (khoảng dòng 192): lớp này chỉ cho XEM, kèm lý do.

**Test `tests/test_m4_review_dot_pg.py`:**
- Thêm ca PG: tác nhân chỉ có `vai='REVIEW'` trên dự án → 404, không gọi đọc chủ bảng.
- Tác nhân XEM vẫn đọc được.
- Sửa ca tĩnh đang khẳng định REVIEW đọc được (khoảng dòng 214–215).

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m4_review_dot_pg`, với PYTHONPATH=`src;.;tests`.

**Tệp (2):** `m4/review_dot_pg.py`, `tests/test_m4_review_dot_pg.py`.

**Báo cáo (≤ 3 dòng)**, thông điệp commit `[M4-DL4] vòng 2: …`.
