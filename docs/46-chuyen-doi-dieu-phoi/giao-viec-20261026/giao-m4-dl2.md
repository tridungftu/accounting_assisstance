# M4-DL2: M4 · Nghiệm thu & chi phí dự án, lớp đọc/ghi PostgreSQL cho HĐ, tham số và nguồn gốc chép từ Review (CD-011, lát 2 theo kiểm kê)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn và ghi "Cần Anh".
- Đọc `AGENTS.md`, `CLAUDE.md`. Ghi tệp UTF-8 không BOM.
- Sandbox không ghi được `.git`: **không commit**. Không mở server hay PostgreSQL; test PG tự skip. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m4-dl2`, dựng từ `lat/m4-dl1b`.
- **Không đọc dữ liệu Review thật.** Không mở `D:\Claude\Ho tro review ho so xay dung\review_xaydung\co_so_du_lieu\` hay thư mục kết quả. Chỉ dùng dữ liệu giả có chữ DEMO.

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\M4-KIEM-KE-CHEP-REVIEW.md`: §3 (ánh xạ bảng), §4 (repository PG thay `csdl_hop_dong.py`), §5 dòng 2 · M4-DL2.
- `src/kho_tri_thuc/m4/sql_review_chep.py`: docstring là hợp đồng dữ liệu. Có lần chụp, `chup_luc`, hàm `m4.review_chep_hien_hanh`, replay `ON CONFLICT DO NOTHING` sau khi đối chiếu `dong_sha256`, kiểu REAL → numeric bằng `Decimal(repr(x))`.
- `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\review-m4-dl1-v2.md`.
- Mẫu repository/kết nối PG đang có trong M4: các tệp `m4/*.py` dùng kết nối chủ bảng và `_tx`. Xem `m4/ke_toan_nghiem_thu.py`, `k2/xay_dung.py`.

**Việc: tệp mới `src/kho_tri_thuc/m4/review_data_pg.py`.** Lớp `ReviewDataPG` nhận kết nối chủ bảng tin cậy, không tự mở DSN.
1. **Ghi một lần chụp** cho các bảng `review_chep_nguon`, `review_chep_che_do`, `review_chep_hop_dong`, `review_chep_tham_so`, `review_chep_tham_so_nguon`.
   - Đầu vào là dữ liệu đã đọc sẵn (dict theo bảng), kèm `nguon_id`, `chup_luc`, `nhap_boi` và **bảng ánh xạ** `ma_hd → (hop_dong_id, du_an_id)` do người chốt đưa vào.
   - Không suy ánh xạ từ chuỗi; `ma_hd` thiếu trong ánh xạ thì dừng cả lần chụp.
   - Mỗi dòng tính `dong_sha256` theo một cách chuẩn hóa ổn định, ghi rõ trong docstring.
   - Cả lần chụp ghi trong **một giao dịch**; lỗi thì rollback hết.
   - Gọi lại cùng lần chụp với cùng dữ liệu thì không tăng dòng (replay). Cùng khóa mà khác hash thì dừng với lỗi rõ, **không ghi đè**.
2. **Đọc bản hiện hành** của một HĐ qua `m4.review_chep_hien_hanh`. NULL nghĩa là HĐ đã xóa ở nguồn, trả trạng thái rõ ràng.
   - Lấy: thông tin HĐ; 37 tham số; nguồn gốc từng tham số (giá trị AI, giá trị, mức, đã xác nhận, đã sửa tay, người/lúc xác nhận, ghi chú soát).
   - **Giữ xác nhận từng ô** đúng như nguồn. Không tạo bản trích giả, không suy giá trị.
3. **DTO cho màn hình:**
   - Không trả `file_nguon`, `file_hop_dong`, `sha1_file`, đường dẫn, `nhap_boi`/login hay mã kỹ thuật nội bộ.
   - Số tiền trả kiểu `Decimal`, chuỗi giữ nguyên, NULL giữ NULL.
   - Ngày nguồn (TEXT) giữ nguyên, không đoán múi giờ.
4. Không thêm migration. Không sửa `sql_review_chep.py` hay `pg_migrations.py`.

**Test, tệp mới `tests/test_m4_review_data_pg.py`:**
- Phần tĩnh: hàm băm ổn định (cùng dữ liệu, khác thứ tự khóa → cùng hash); DTO không có trường cấm; REAL → `Decimal(repr)`.
- Phần PG (`skipUnless KHO_PG_DSN_TEST`; tạo CSDL `kho_test_*` riêng, migrate, tạo pháp nhân/dự án/HĐ DEMO và `m4.ho_so_hop_dong` như `tests/test_m4_review_chep_schema.py` đang làm):
  - ghi lần chụp 1 rồi đọc lại đủ;
  - replay không tăng dòng; cùng khóa khác hash bị từ chối;
  - thiếu ánh xạ thì dừng và không ghi dòng nào;
  - lần chụp 2 không còn HĐ thì đọc trả trạng thái đã xóa;
  - giữ xác nhận từng ô;
  - lỗi giữa chừng thì không còn dòng nào.
- Chạy thuần: `python -X utf8 -m unittest tests.test_m4_review_data_pg tests.test_m4_review_chep_schema`, với PYTHONPATH=`src;.;tests`.

**Tệp (≤ 2):** `m4/review_data_pg.py`, `tests/test_m4_review_data_pg.py`.

**Báo cáo (≤ ¼ trang):** số test, phần "Cần Anh", thông điệp commit `[M4-DL2] …`.
