# KY-G5TAY vòng 2 — chưa khép lỗi 400 G6

- Đã sửa ca so thân hàm theo định nghĩa cuối chuỗi migration; N1 bật RLS + assertion PG; N2 ghim vị trí 37; D2 chặn control trong SQL/Python, gồm DEL/C1 phía Python.
- **400 chưa xác định nguyên nhân/chưa sửa:** `src/kho_tri_thuc/k2/sql_crm_kiem_hd.py:1288` không đọc G5/E5; p01 lưu G6 **trước** xác nhận tay (`tests/test_crm_g5_tay.py:200`). `giao_dien/server.py:293` che ngoại lệ PG. Đã thêm chẩn đoán service cùng khóa và ca PG cho cả hai thứ tự G5/G6. Lead cần chạy để lấy SQLSTATE/context; chưa có căn cứ thay guard G6.
- File đổi: `k2/sql_crm_g5_tay.py`, `k2/crm_ky_ket.py`, `tests/test_crm_g5_tay.py`, `tests/test_crm_ky_docx.py`. E5, migration 1–36 nguyên byte.
- Test: **53 đạt/71, 18 skip, 0 ERROR/FAIL**; không lỗi mới trong nhóm thuần. PG chưa chạy. UTF-8 không BOM, `diff --check` đạt. Không mở server/PG, không commit.
- Commit đề xuất: `[KY-G5TAY] vòng 2: sửa kiểm migration hiện hành, RLS và lý do; bổ sung chẩn đoán G6`.
