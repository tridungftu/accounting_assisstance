# M4-DL5c: M4 · Nghiệm thu & chi phí dự án, tính lịch sử đợt chép từ Review vào lũy kế chính thức (QD-20261026-05). Rủi ro cao: căn cứ/kết luận duyệt.

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi tệp UTF-8 không BOM. Không commit. Không mở server/PostgreSQL DEMO. Không xóa file.
- Test PG tự tạo `kho_test_*`, không đọc `KHO_PG_DEMO_*`.
- **Chỗ chưa rõ hoặc có thể làm hỏng căn cứ đã duyệt: dừng, ghi "Cần lead", không đoán.**
- Làm trong worktree hiện tại, nhánh `lat/m4-dl5c`, dựng từ hợp nhất. Đã có:
  - DL5a: `chup_review_l2` kiểm quyền trên giao dịch chụp;
  - DL5b: `gom_lich_su_review_chep`, `doc_lich_su_chep` với quy tắc ĐVT/mã trùng/ngày, đang chỉ hiển thị riêng.

**Quyết định Anh (QD-20261026-05):** lịch sử đợt chép từ Review **tính vào lũy kế chính thức**, điều kiện:
- seal M4 luôn thắng, không cộng trùng;
- chỉ áp cho đợt **không có seal M4**;
- cùng đơn vị tính;
- mã hạng mục trùng → cần xem lại;
- ngày nghiệm thu hợp lệ (không thiếu, không sau đợt hiện tại);
- nguồn ghi rõ `REVIEW_CHEP`.

**Việc** (`m4/duyet_dot.py`; nếu cần đọc chép thì dùng hàm sẵn có của `m4/review_dot_pg.py`):
1. `lich_su_da_duyet(xd, c, d)`. Đợt trước **chưa seal**:
   - có đợt chép cùng số (hoặc `m4_dot_id` trỏ đúng đợt đó) và mọi quy tắc trên đều thỏa → coi là đợt đã có căn cứ, `trang_thai="DA_DUYET_REVIEW_CHEP"`, `nguon="REVIEW_CHEP"`;
   - cộng khối lượng theo **từng dòng hiện tại** (row_id ↔ mã HM + ĐVT của dòng `_dong` hoặc BOQ hiện hành; đọc mã để tìm nơi có ánh xạ này);
   - không thỏa → `INCOMPLETE` như cũ.
2. **Giữ nguyên byte** khi HĐ không có bản chụp Review, hoặc không có đợt nào chỉ có ở Review: không thêm khóa, không đổi thứ tự, không đổi chữ.
3. Đọc dữ liệu chép **trên cùng kết nối/giao dịch** `c` của luồng gọi, kiểm quyền như DL5a/DL5b. Không mở kết nối tin cậy để lách quyền.
4. JSON kết luận/seal ghi lại `truoc_da_duyet` như hiện có, nên sẽ chứa nguồn `REVIEW_CHEP` khi áp dụng. Không đổi shape các khóa cũ.
5. `lich_su_review_chep` (DTO DL5b) giữ nguyên để người duyệt so; thêm cờ `da_tinh_vao_luy_ke` (true/false) theo đúng kết quả mục 1.

**Test** (thêm vào `tests/test_m4_dl5b_lich_su.py`; PG trong `tests/test_m4_review_dot_pg.py` nếu cần):
- Đợt 1 chỉ có ở Review, cùng ĐVT → lũy kế đợt 2 = khối lượng Review, nguồn `REVIEW_CHEP`.
- Đợt 1 có seal M4 và cũng có ở Review → chỉ lấy seal.
- Khác ĐVT, mã trùng hoặc ngày sai → `INCOMPLETE`, không cộng.
- Đợt M4 cùng số đang mở chưa seal → không dùng Review, `INCOMPLETE`/`CAN_XEM_LAI`.
- HĐ không có bản chụp → `co`/`truoc_da_duyet`/JSON kết luận **giữ nguyên byte** (test byte hiện có vẫn đạt).
- JS 02C (`m4/giao_dien/m4_duyet_pdf.js`) không vỡ với trạng thái mới; chỉ cần đọc mã xác nhận, không sửa JS.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m4_dl5b_lich_su tests.test_m4_review_dot_pg tests.test_m4_02c_dto_ui`, PYTHONPATH=`src;.;tests`.

**Tệp (≤ 3):** `m4/duyet_dot.py`, `m4/review_dot_pg.py` (nếu cần), một tệp test.

**Báo cáo (≤ ⅓ trang):** "Cần lead" nếu có. Thông điệp commit `[M4-DL5c] …`.
