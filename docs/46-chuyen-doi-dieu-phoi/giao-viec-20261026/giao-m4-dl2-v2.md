# M4-DL2 vòng 2: lớp đọc/ghi dữ liệu Review, sửa điểm Chặn của review và lớp đọc tự kiểm quyền (lead chốt)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server hay PostgreSQL; test PG tự skip. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m4-dl2` (đã nhận hợp nhất có M0040).
- Hợp đồng dữ liệu: docstring `src/kho_tri_thuc/m4/sql_review_chep.py` bản hiện hành.

**1. Chặn — NULL có 3 nghĩa** (`m4/review_data_pg.py` khoảng dòng 115–117, 255, 260–261):
- Khi `m4.review_chep_hien_hanh` trả NULL, trong **cùng giao dịch** chạy 2 câu `EXISTS`:
  - có dòng nào trong `m4.review_chep_nguon` không;
  - có dòng nào trong `m4.review_chep_hop_dong WHERE hop_dong_id = %s::uuid` không.
- Trả đúng 1 trong 3 trạng thái: `CHUA_CO_LAN_CHUP` / `CHUA_CO_TRONG_NGUON` / `DA_XOA_O_NGUON`.
- `dto_man_hinh` nhận trạng thái này và hiện câu tiếng Việt tương ứng:
  - "Chưa nạp dữ liệu Review.";
  - "Hợp đồng chưa có trong dữ liệu Review.";
  - "Hợp đồng đã bị xóa ở dữ liệu Review (lần chụp mới nhất).".
- Sửa docstring.

**2. Lớp đọc tự kiểm quyền M4** (lead chốt phương án (a), khớp hợp đồng dữ liệu):
- Hàm đọc bản hiện hành (`doc_hien_hanh` hoặc tên tương ứng) nhận **bắt buộc** đối số kiểm quyền: danh tính phiên, hoặc hàm kiểm quyền do tầng gọi truyền vào.
- Trước khi trả dữ liệu, kiểm `XEM` **hoặc** `REVIEW` theo **dự án của HĐ** trên **kết nối thường** (login của người dùng), theo mẫu `m4/ke_toan_nghiem_thu.py` dòng 7–8 và hàm `master.m4_duoc(du_an_id, 'XEM'|'REVIEW')`.
- Không quyền → `DataError` mã 404 hoặc không thấy. Không lộ sự tồn tại của HĐ.
- Đọc bảng chép vẫn qua kết nối chủ bảng, **sau** khi đã kiểm quyền.
- Sửa câu docstring đầu module dòng 3–4 cho khớp.

**3. Nên sửa:**
- Kiểm sớm trong `_chuan_bi`: hai `ma_hd` ánh xạ vào cùng `hop_dong_id` → `DataError` rõ, không để lỗi UNIQUE thô của CSDL.
- `_chuan_hash`: chuẩn hóa `Decimal('-0')` thành `0`.
- Thông báo `M4_REVIEW_REPLAY_KHAC` nói rõ **trường nào khác**: `chup_luc`, hash dòng, ánh xạ hay người nạp.

**4. Giữ tương thích cho các lát đang dựng trên DL2** (DL3 `review_phu_luc_pg.py`, CD1 công cụ chuyển):
- **Không đổi tên hay chữ ký các hàm ghi.**
- Hàm đọc đổi chữ ký thì ghi rõ trong báo cáo.

**Test `tests/test_m4_review_data_pg.py`:**
- PG: 3 trạng thái NULL, mỗi trạng thái một ca.
- Người không có XEM/REVIEW trên dự án → 404, không trả dữ liệu.
- Người có XEM → đọc được.
- Ánh xạ trùng `hop_dong_id` → `DataError`.
- Tĩnh: -0 cùng hash với 0.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m4_review_data_pg`, với PYTHONPATH=`src;.;tests`.

**Tệp (2):** `m4/review_data_pg.py`, `tests/test_m4_review_data_pg.py`.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[M4-DL2] vòng 2: …`.
