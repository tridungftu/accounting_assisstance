# M4-DL5a: M4 · Nghiệm thu & chi phí dự án, nối phụ lục/BOQ đã chép từ Review vào snapshot tính toán review (CD-011, lát 5 theo kiểm kê)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn (không tự áp, trả trạng thái chờ) và ghi "Cần Anh/lead".
- Đọc `AGENTS.md`, `CLAUDE.md`. Ghi tệp UTF-8 không BOM.
- **Không commit**. Không mở server hay PostgreSQL. Không xóa file.
- Test PG tự tạo CSDL `kho_test_*`.
- **Không sửa mã vendor đã ghim** (`m4/review_goc/...`). Không đọc dữ liệu Review thật.
- Làm trong worktree hiện tại, nhánh `lat/m4-dl5a`, dựng từ hợp nhất (đã có DL2, DL3, DL4, CD1).

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\M4-KIEM-KE-CHEP-REVIEW.md` §4 (hàng `csdl_hop_dong.py` → PG, "Hàm nghiệp vụ đang nhận `con` SQLite"), §5 dòng 5 · M4-DL5a.
  - Điều kiện xong: regression parity P/B, không sửa vendor PIN, snapshot chứa đủ thay đổi PL.
- `src/kho_tri_thuc/m4/nguon_review.py`:
  - docstring đầu tệp;
  - `projection_l2` (khoảng dòng 604): projection SQLite `:memory:` theo đúng SCHEMA nguồn, nạp từ snapshot K2;
  - seam PL/BOQ hiệu lực (khoảng dòng 529–563).
- `k2/xay_dung.py`: nơi gọi tính toán review.
- DL3 `m4/review_phu_luc_pg.py`: đọc PL/thay đổi tham số/BOQ của bản chụp hiện hành, có kiểm quyền.

**Việc:**
1. Khi dựng projection cho một HĐ, nếu **có bản chụp Review hiện hành** (DL2 trạng thái `HIEN_HANH`), nạp **thêm** các dòng `phu_luc`, `thay_doi_tham_so`, `boq_dong` từ bản chụp vào projection, đúng schema nguồn.
   - Thuật toán nguồn (`phu_luc_ap_dung`, `boq_hieu_luc`, P01–P26, B1–B8) chạy được trên lịch sử PL đầy đủ như ở phần mềm Review gốc.
   - **Không** trộn với PL vận hành của M4 khi có trùng khóa. Trùng hoặc mâu thuẫn thì đánh dấu "cần xem lại" trong kết quả, không chọn bừa.
   - Không có bản chụp (3 trạng thái NULL) thì giữ nguyên hành vi hiện tại.
   - Đọc bản chụp phải qua kiểm quyền: truyền `conn_phien` từ tầng gọi. Không có `conn_phien` thì không nạp phần chép.
2. `k2/xay_dung.py`: truyền những gì cần cho bước 1. Không đổi DTO hay quyền hiện có.

**Test, tệp mới `tests/test_m4_review_compute.py`:**
- **Parity:** dữ liệu giả DEMO gồm HĐ có 2 phụ lục (THAY/THEM/BO).
  - Kết quả P/B và BOQ hiệu lực tại 2 ngày khi chạy thuật toán vendor trên SQLite giả trực tiếp phải **giống hệt** khi chạy qua projection nạp từ bản chụp PG (phần PG `skipUnless KHO_PG_DSN_TEST`).
  - Phần thuần dùng dữ liệu dựng sẵn.
- Không có bản chụp → hành vi cũ không đổi (so kết quả trước và sau).
- Không `conn_phien` → không nạp phần chép.
- Trùng khóa với PL vận hành → "cần xem lại".

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m4_review_compute` và các test M4 review hiện có (`tests/test_m4_review*.py`), PYTHONPATH=`src;.;tests`. Báo số trước và sau.

**Tệp (3):** `m4/nguon_review.py`, `k2/xay_dung.py`, `tests/test_m4_review_compute.py`.

**Báo cáo (≤ ⅓ trang)**, thông điệp commit `[M4-DL5a] …`.
