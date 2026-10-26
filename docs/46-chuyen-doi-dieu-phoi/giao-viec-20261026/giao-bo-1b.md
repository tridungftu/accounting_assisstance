# BO-1b · M4 · Nghiệm thu & chi phí dự án — bên ghi BOQ nhận thao tác tường minh, có "bỏ dòng" (QD-20261026-09)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM; `pg_migrations.py` giữ LF. **Ghi tệp bằng apply_patch, không qua chuỗi PowerShell; tự kiểm `AS $$`/`$$`.**
- Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ: dừng, ghi "Cần lead". Không có `python` thì NOT_RUN; lead chạy PG.
- Test PG tự tạo `kho_test_*`, chạy dưới vai ứng dụng như test M4 hiện có, dữ liệu giả, chạy được dưới guard. Không kiểm CRLF/LF.
- Migration: chỉ thêm `M00xx_M4_BOQ_BO_B`, dấu `# BO-1b — QD-09:`. Không sửa migration cũ (tới M0060).

**Đã có:**
- **M0059** (BO-1a): CHECK `m4.boq_dong.thao_tac` có `BO`; hàm đọc `m4.boq_hieu_luc` theo ngữ nghĩa projection Review (THEM khi chưa hiệu lực, THAY khi đang hiệu lực — chỉ ghi đè trường có giá trị, BO khi đang hiệu lực; sai → cần xem lại). Xem `m4/sql_boq_bo.py`.
- Bên ghi `m4.ghi_boq`: định nghĩa gốc ở `m4/sql_m17.py` ~dòng 966, **đã được thay thân ở M0055** (`m4/sql_mtq.py` `MTQ_M4_A_SQL`, guard ma trận lệnh hồ sơ). Hiện **suy** `thao_tac`: không phụ lục → `GOC`; có phụ lục → mã có trong BOQ gốc là `THAY`, ngược lại `THEM`. Chưa có `BO`.

**Tệp (3):** `m4/sql_boq_bo.py` (thêm hằng `M4_BOQ_BO_B_SQL`, không đổi hằng cũ); `ha_tang/pg_migrations.py`; `tests/test_m4_boq_bo_pg.py` (thêm ca, giữ ca cũ).

**Việc:**
1. `CREATE OR REPLACE m4.ghi_boq` dựa trên **thân hiện hành mới nhất theo thứ tự migration** (bản M0055 có guard). Lấy đúng như 4f1b đã làm; không lấy thân cũ hơn. Chữ ký giữ nguyên.
2. Mỗi phần tử `p_dong` được có thêm khóa tùy chọn `thao_tac`:
   - Có `thao_tac` (chỉ hợp lệ khi `p_pl` không NULL): nhận `THEM`/`THAY`/`BO` đúng như gửi. `GOC` chỉ khi không có phụ lục. Giá trị khác → lỗi dữ liệu có mã, câu tiếng Việt.
   - Không có `thao_tac` ở **mọi** dòng → giữ **nguyên** cách suy luận hiện tại (không đổi hành vi caller cũ). Lẫn lộn có/không trong cùng lần → lỗi có mã.
   - Dòng `BO`: chỉ cần `ma_hm`. Nếu thiếu `ten`/`dvt` (cột NOT NULL), chép từ dòng đang hiệu lực của `ma_hm` đó **trước phụ lục này** (dùng `m4.boq_hieu_luc` hoặc logic tương đương). Không có dòng hiệu lực → lỗi có mã. Không đổi tiền/khối lượng.
3. Không kiểm tính hợp lệ nghiệp vụ toàn BOQ ở bên ghi (hàm đọc đã báo "cần xem lại"). Chỉ chặn đầu vào sai định dạng.
4. Giữ nguyên guard ma trận, replay/biên nhận, nhật ký, trạng thái.

**Test (PG):**
- caller cũ không gửi `thao_tac` → kết quả giống hệt trước (oracle);
- gửi `BO` cho mã đang hiệu lực → dòng BO ghi đúng, `ten`/`dvt` chép đúng, `m4.boq_hieu_luc` sau ngày hiệu lực không còn mã đó;
- `BO` mã không hiệu lực → lỗi có mã;
- `thao_tac` lạ / lẫn lộn → lỗi;
- `GOC` khi có phụ lục → lỗi;
- replay cùng biên nhận không nhân đôi;
- PN bật/tắt: guard M0055 vẫn chạy như cũ.

**Báo cáo (≤ ¼ trang)**, "Cần lead", thông điệp commit `[BO-1b] …`.
