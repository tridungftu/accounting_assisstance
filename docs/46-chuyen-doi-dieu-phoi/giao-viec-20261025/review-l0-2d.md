# REVIEW L0-2d · vòng 1/2 · reviewer Codex (chỉ đọc)

Bạn là reviewer chéo, chạy không tương tác (`codex exec`, sandbox chỉ đọc). Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md` ở thư mục hiện tại. Mã hóa UTF-8 (đọc bằng `git show`, `python -X utf8`).

**Đối tượng:** nhánh `lat/l0-2d` (worktree hiện tại), 2 commit trên nền `1502fe7`: `859b9ad [L0-2d] gộp crm-m4-three`, `e69e9eb [L0-2d] gộp crm-g5-doi-chieu`. Handoff gốc: `docs/46-chuyen-doi-dieu-phoi/4-KE-HOACH-LEAD.md` mục 4.

**Worker báo (cần kiểm, đừng tin sẵn):**
1. Gói `crm-g4` trên hop-nhat (commit 906c95a) đã ghi đè bản CŨ HƠN lên nền `chinh` (59b7d8e) cho `crm_g.py`, `crm_g.js`, `pg_migrations.py`, `k2/crm_ky_ket.py`, 3 test `crm_ky_ket` — mất khoảng 700 dòng so với `chinh`. Chuỗi đúng: crm-g4 → crm-m4-three → (U2 trên nền chinh).
2. Vì vậy worker gộp theo dòng dõi: crm-m4-three TRƯỚC, G5 SAU (ngược thứ tự handoff), nền 3 bên = bản crm-g4.
3. Kết quả: `crm_g.py` = bản G5; `crm_g.js`, `test_crm_ky_ket.py`, `crm_ky_ket_async.cjs` = bản nền chinh; `k2/crm_ky_ket.py`, `test_crm_ky_ket_http.py` = bản m4-three; `pg_migrations.py` merge 3 bên không xung đột, trùng byte với bản của crm-g6a-m25-registration; thêm `test_crm_doi_chieu_tinh.py`, `test_crm_doi_chieu_http.py`. 9 file. Không đổi số migration.

**Kiểm 4 việc (quy trình mục 7), mỗi việc kết luận Đạt/Không:**
1. **Không mất hành vi:** với từng file trong 9 file, so `lat/l0-2d` với `chinh`, `hop-nhat-20261023` (1502fe7), `luu/crm-g4`, `luu/crm-m4-three`, `luu/crm-g5-doi-chieu-20261023-01` (dùng `git diff`, liệt kê hàm/route/test có ở một bản nguồn mà KHÔNG có ở `lat/l0-2d`). Xác nhận hoặc bác điểm 1 của worker bằng số dòng/hàm cụ thể.
2. **Migration:** danh sách số migration trong `pg_migrations.py` ở `lat/l0-2d` liên tục, không trùng số, không đổi nội dung số đã dùng so với `hop-nhat`.
3. **Diff đúng phạm vi:** `git diff 1502fe7..lat/l0-2d --stat` chỉ gồm file CRM/migration/test nêu trên; `k2/crm_ky_ket.py` ngoài danh sách handoff — có hợp lý không.
4. **Ràng buộc cứng:** không dữ liệu thật trong test/fixture mới (tên công ty, MST, STK, số tiền thật), không xóa file, không đụng `var/`.
Không chạy server, không sửa file. Có thể chạy `python -X utf8 -m py_compile` để kiểm cú pháp.

**Báo cáo cuối (≤ 1 trang, tiếng Việt, ≤ 10 điểm)** theo mẫu:
```
REVIEW L0-2d · vòng 1/2 · Codex
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
Chỉ "Chặn" khi có hành vi bị mất, migration sai số, hoặc vi phạm ràng buộc cứng.
