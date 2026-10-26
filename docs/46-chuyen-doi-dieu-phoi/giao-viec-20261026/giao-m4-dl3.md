# M4-DL3: M4 · Nghiệm thu & chi phí dự án, lớp đọc/ghi PostgreSQL cho phụ lục, thay đổi tham số, BOQ chép từ Review (CD-011, lát 3 theo kiểm kê)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn và ghi "Cần Anh".
- Đọc `AGENTS.md`, `CLAUDE.md`. Ghi tệp UTF-8 không BOM.
- Sandbox không ghi được `.git`: **không commit**. Không mở server hay PostgreSQL; test PG tự skip. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m4-dl3`, dựng từ `lat/m4-dl2`. DL2 chưa gộp, có thể còn sửa: **không sửa** `m4/review_data_pg.py` hay test của DL2; chỉ import và dùng lại hàm công khai của nó.
- **Không đọc dữ liệu Review thật**; chỉ dữ liệu giả có chữ DEMO.

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\M4-KIEM-KE-CHEP-REVIEW.md`: §3 (các bảng `phu_luc`, `thay_doi_tham_so`, `boq_dong` nguồn → đích), §5 dòng 3 · M4-DL3 (điều kiện xong: hiệu lực theo ngày / THAY-THEM-BO, GT PL, lịch sử hủy đúng bản gốc).
- `src/kho_tri_thuc/m4/sql_review_chep.py`: docstring là hợp đồng dữ liệu (bản hiện hành, NULL có 3 nghĩa, không nạp một phần, replay đối chiếu hash).
- `m4/review_data_pg.py` (DL2): cách ghi một lần chụp, cách băm dòng, cách đọc bản hiện hành, DTO không lộ trường tệp.

**Việc: tệp mới `src/kho_tri_thuc/m4/review_phu_luc_pg.py`.**
1. Ghi các bảng `review_chep_phu_luc`, `review_chep_thay_doi_tham_so`, `review_chep_boq_dong` **trong cùng giao dịch của lần chụp**.
   - Thiết kế hàm nhận con trỏ hoặc giao dịch từ DL2. Nếu DL2 chưa có điểm nối, làm hàm riêng nhận cùng `conn` trong giao dịch đang mở và ghi "Cần lead: nối vào ghi lần chụp DL2".
   - Replay không tăng dòng; cùng khóa mà khác hash thì từ chối; giữ NULL; REAL → `Decimal(repr)`.
2. Đọc cho một HĐ ở bản hiện hành:
   - phụ lục còn hiệu lực và đã hủy (giữ `ly_do_huy`, không đoán ngày/người hủy);
   - thay đổi tham số theo phụ lục;
   - BOQ theo thao tác `GOC/THAY/THEM/BO` tại một **ngày** cho trước, theo `ngay_hieu_luc`;
   - giá trị HĐ sau phụ lục (`gt_hd_sau_pl`) như nguồn ghi, **không tự tính lại**.
3. **BOQ tại ngày:** áp `THAY/THEM/BO` theo thứ tự hiệu lực trên `GOC`.
   - Dòng `BO` biến mất khỏi kết quả.
   - Chưa có quy tắc rõ (ví dụ hai phụ lục cùng ngày) thì trả cờ "cần xem lại", không chọn bừa.
4. DTO không lộ `file_nguon`, đường dẫn, `nhap_boi`, mã nội bộ. Tiền dùng `Decimal`.

**Test, tệp mới `tests/test_m4_review_phu_luc_pg.py`:**
- Phần tĩnh: áp THAY/THEM/BO theo ngày trên dữ liệu thuần; hai phụ lục cùng ngày bật cờ; phụ lục hủy không áp.
- Phần PG (`skipUnless KHO_PG_DSN_TEST`; dựng HĐ DEMO như `tests/test_m4_review_data_pg.py`):
  - ghi lần chụp có phụ lục và BOQ rồi đọc lại;
  - replay không tăng dòng;
  - BOQ tại hai ngày khác nhau ra khác nhau đúng;
  - lần chụp 2 mất phụ lục thì bản hiện hành không còn phụ lục đó.
- Chạy thuần: `python -X utf8 -m unittest tests.test_m4_review_phu_luc_pg tests.test_m4_review_data_pg`, với PYTHONPATH=`src;.;tests`.

**Tệp (2):** `m4/review_phu_luc_pg.py`, `tests/test_m4_review_phu_luc_pg.py`.

**Báo cáo (≤ ¼ trang):** số test, phần "Cần lead/Cần Anh", thông điệp commit `[M4-DL3] …`.
