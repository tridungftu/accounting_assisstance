# M4-DL5a vòng 2: sửa theo review (2 chặn + 8 mã lỗi PG mới). Rủi ro cao.

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn và ghi "Cần lead".
- Ghi UTF-8 không BOM. **Không commit**. Không mở server hay PostgreSQL DEMO. Không xóa file. Không sửa vendor `m4/review_goc/...`.
- Làm trong worktree hiện tại, nhánh `lat/m4-dl5a` (commit 27dd92e).

**Đọc trước:** `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\review-m4-dl5a.md` (đủ dòng/tệp) và giao việc gốc `giao-m4-dl5a.md`.

**Việc:**
1. **Bỏ** thay đổi `_tx_review` (`k2/xay_dung.py:~699`): trả về `yield c` như trước.
   - Đây là nguồn 8 mã lỗi PG mới `test_m4_02b_k2.M4CongBoS1Bien.test_b1/b2/b3_fallback_*` (`AssertionError: 44 != 22`).
   - Sau khi sửa, các ca này phải trở về như nền.
2. **Chặn 1:** `chup_review_l2` **không** gọi `kiem_quyen_doc` với `conn_phien`. Kiểm quyền bằng SQL trên chính kết nối `c` của giao dịch review/02C/03A/03B (danh tính đã đặt, cổng `*_kiem` của luồng gọi đã chạy):
   - chấp nhận mọi vai M4 đã qua cổng gọi;
   - đọc bản chụp hiện hành bằng `m4.review_chep_hien_hanh` trên `c`.

   Nếu không làm được vậy, ghi "Cần lead" và nêu phương án.

   Bỏ tham số `conn_phien` khỏi `_co_so` nếu không còn cần.
3. Không có bản chụp (3 trạng thái NULL) → basis **giữ nguyên byte** như cũ.
4. **Chặn 2:** câu trong `ly_do` (`xay_dung.py:~854`, `nguon_review.py:~679`) đổi thành câu nghiệp vụ trung tính, không "Cần Anh/lead", ví dụ "Cần xem lại nguồn phụ lục/BOQ: <lý do>. Chưa tính.". Sửa test `test_xung_dot_cong_bo_failed…` theo.
5. **Nên sửa 4:** đảm bảo lỗi đọc bản chụp lúc công bố không để lần chạy treo RUNNING (đi vào nhánh `FAILED` có sẵn).
6. **Nên sửa 5:**
   - chỉ chặn **xung đột chéo giữa PL vận hành M4 và PL chép**: trùng số PL, hoặc trùng ngày hiệu lực giữa hai nguồn;
   - trong cùng nguồn chép thì để vendor tự xếp như bản gốc;
   - áp kiểm "thao tác BOQ không khớp hạng mục" (như DL3 `boq_tai_ngay`) trên tập gộp; không khớp → cần xem lại, không bỏ qua im lặng.
7. **Nên sửa 6:** basis/`co_so.json` chỉ giữ cột cần cho tính toán.
   - Bỏ `file_nguon`, `nguoi_nhap`, `phieu`, `ly_do_huy`, đường dẫn và id nguồn không cần.
   - Không lặp dữ liệu hai lần (`review_chep` và `phu_luc`).
   - Parity vẫn phải đạt.

**Test:**
- `tests/test_m4_review_compute.py`:
  - parity vẫn đạt;
  - ca trùng chéo → cần xem lại;
  - ca cùng nguồn chép cùng ngày → không chặn;
  - ca THAY/BO không khớp trên tập gộp → cần xem lại;
  - basis không chứa các cột bị bỏ.
- Thêm ca PG (`skipUnless KHO_PG_DSN_TEST`, tự tạo `kho_test_*`), đặt trong tệp test của lát:
  - người **chỉ có vai DUYET** và người **chỉ có vai KE_TOAN**, khi đợt đã có L2 công bố có `doi_chieu_hm` (có và không có bản chụp);
  - mở 02C/03A không lỗi;
  - SHA basis giống reviewer.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m4_review_compute tests.test_m4_02b_k2 tests.test_m4_02c_pg`, PYTHONPATH=`src;.;tests` (PG sẽ skip; lead chạy PG).

**Tệp (3):** `k2/xay_dung.py`, `m4/nguon_review.py`, `tests/test_m4_review_compute.py`.

**Báo cáo (≤ ⅓ trang)**, thông điệp commit `[M4-DL5a] vòng 2: …`.
