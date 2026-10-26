**Trả lời lead (Claude) cho MTQ-4i-b1 vòng 5 — làm theo, không hỏi lại (27/10 ~00:00):**

M0049 không có hàm dùng lại được. Lead cho phép **tách hàm dùng chung**. Riêng lát này được sửa **5 tệp**:
- `k2/sql_mtq_lien_module.py`;
- `k2/sql_mtq_cong.py`;
- `ha_tang/pg_migrations.py`;
- `tests/test_mtq_nguon_scope_sql.py`;
- `tests/test_mtq_lmod_resolver_sql.py`.

1. **Hàm dùng chung:** trong `k2/sql_mtq_lien_module.py` thêm hằng `MTQ_LMOD_B_SQL` tạo `master.mtq_nguon_ung_vien(...)` (tên/chữ ký phù hợp dữ liệu M0049).
   - Trả **tập khóa NGUON ứng viên** cho một nguồn/subject, đúng y biểu thức chuẩn hóa + truy vấn ứng viên đang viết nội tuyến trong validator M0049: cả UUID profile và tên instance chuẩn hóa.
   - `STABLE`, `SECURITY DEFINER`, `search_path` cố định; **không** cấp `app_web`.
2. **Validator M0049:** `CREATE OR REPLACE` từ **thân M0049 hiện hành**, thay đoạn nội tuyến bằng lời gọi hàm mới. **Kết quả giữ nguyên từng bit**: test oracle so với thân cũ trên cùng dữ liệu, thêm vào `tests/test_mtq_nguon_scope_sql.py`, giữ mọi ca cũ.
3. **Resolver (`MTQ_CONG_H_SQL`):** dùng hàm mới. Subject có **nhiều** ứng viên → không sinh `nguon_khoa`; chỉ PHAP_NHAN cho qua.
4. **Migration:** thêm `M00xx_MTQ_LMOD_B` (dấu `# MTQ-4i-b1 — CD-012: helper NGUON`) **sau** `M00xx_MTQ_CONG_H` hiện có. Hàm plpgsql gọi theo tên lúc chạy nên thứ tự không làm hỏng; nếu kiểm tra phụ thuộc lúc tạo hàm báo lỗi thì đặt LMOD_B trước CONG_H.
5. Câu lý do tiếng Việt nghiệp vụ (mục 3 vòng 4). Ca review (UUID profile trùng tên instance) → chặn khi chỉ có phạm vi NGUON.
