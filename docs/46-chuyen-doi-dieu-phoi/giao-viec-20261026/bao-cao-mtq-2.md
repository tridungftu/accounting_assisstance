Anh, đã triển khai MTQ-2 trong **3 file**, UTF-8 không BOM:

- `k2/ma_tran_tham_quyen.py`
- `giao_dien/ma_tran_tham_quyen.py`
- `tests/test_mtq_dich_vu.py`

Có kiểm Admin, lọc quyền của mình tại SQL, lưu nháp/CAS, công bố, retry không ghi trùng, audit và ghi từ chối sau rollback. Tham số lạ trả 400; CAS trả 409. Không có route bootstrap; kích hoạt vẫn bị readiness MTQ-4 chặn.

**Test:** 5 module đạt 126, skip 26, không ERROR/FAIL. Riêng MTQ-2: 15 đạt, 4 PG skip. Chưa đối chiếu toàn bộ nền v4.

**Cần Anh/lead:** chạy test PG ngoài sandbox; nối dispatcher tại MTQ-3b đúng thiết kế.

Không commit. Thông điệp đề nghị: `[MTQ-2] Thêm dịch vụ và HTTP cấu hình ma trận thẩm quyền`