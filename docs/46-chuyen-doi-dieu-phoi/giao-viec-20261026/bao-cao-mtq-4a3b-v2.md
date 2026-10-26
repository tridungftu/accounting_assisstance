[MTQ-4a3b] vòng 2: Đã đưa kiểm quyền vào cùng giao dịch ghi `nhan_ket_qua_6`, giữ khóa tới commit.
Chỉ đổi `src/kho_tri_thuc/k2/crm.py` và `tests/test_mtq_crm.py`; UTF-8 không BOM, không commit.
Test: 48/53 đạt, 5 skip PG, không lỗi; test mới phát hiện lỗi trên HEAD cũ ở cả 4 subtest.
Đã rà các điểm còn lại; giữ kiểm trước engine của `trich_tu_docx`.
`git diff --check` đạt; chưa kiểm chứng bằng PostgreSQL thật.