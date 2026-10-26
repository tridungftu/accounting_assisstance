# M4-DL5b vòng 2: không cộng khối lượng khác ĐVT (chặn) + 2 nên sửa

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì `None` + `INCOMPLETE` và ghi "Cần Anh".
- Ghi UTF-8 không BOM. **Không commit**. Không mở server hay PostgreSQL DEMO. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m4-dl5b` (commit a877282).

**Đọc trước:** `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\review-m4-dl5b.md` và giao việc gốc `giao-m4-dl5b.md`.

**Việc** (`m4/duyet_dot.py`, `m4/review_dot_pg.py`):
1. **Chặn, ĐVT:** trong `gom_lich_su_review_chep`:
   - Chỉ cộng các phần cùng ĐVT với dòng hiện tại (`_dong` có `dvt`); so ĐVT sau khi chuẩn hóa khoảng trắng và hoa/thường.
   - Seal: lấy `dvt` của từng dòng seal (`sql_duyet.py:~479`).
   - Review chép: lấy ĐVT từ `review_chep_boq_dong` cùng bản chụp, HĐ, mã HM (thêm vào `doc_lich_su_chep` trong `review_dot_pg.py`). Nhiều ĐVT khác nhau cho cùng mã HM → chưa rõ.
   - Khác ĐVT, thiếu ĐVT ở bất kỳ phía nào, hoặc ĐVT chưa rõ → `kl_luy_ke_gom_lich_su = None`, `INCOMPLETE`, lý do "Đơn vị tính khác nhau hoặc chưa rõ, không cộng".
2. **Nên sửa 2:** mã HM trùng trong `dong_nt` của đợt hiện tại → mỗi dòng trùng nhận `None` + `CAN_XEM_LAI` ("Mã hạng mục xuất hiện nhiều dòng trong đợt này"), không gán cùng một tổng.
3. **Nên sửa 3:** áp điều kiện ngày như `lich_su_da_duyet`: đợt trước thiếu ngày nghiệm thu, hoặc có ngày nghiệm thu sau đợt này, → `INCOMPLETE`, không cộng. Áp cho đợt `M4_SEAL`; đợt `REVIEW_CHEP` dùng `ngay_nghiem_thu` của dòng chép, quy tắc như trên.
4. Basis, `truoc_da_duyet` và JSON kết luận/seal vẫn **giữ nguyên byte** (test cũ phải còn đạt).

**Test** (`tests/test_m4_dl5b_lich_su.py`, `tests/test_m4_review_dot_pg.py`):
- Ví dụ của review: seal `m2`=100 + seal `m3`=7 + Review 5 → `None`/INCOMPLETE, không 112.
- Cùng ĐVT (khác hoa/thường hoặc khoảng trắng) → cộng đúng.
- Review không có BOQ cho mã HM (ĐVT chưa rõ) → INCOMPLETE.
- Hai dòng cùng mã HM trong đợt hiện tại → cả hai `CAN_XEM_LAI`.
- Đợt trước có ngày nghiệm thu sau đợt này, hoặc thiếu ngày → INCOMPLETE.
- PG: ĐVT lấy từ BOQ chép đúng bản chụp hiện hành.
- Báo đúng số test **và số skip** trước/sau.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m4_dl5b_lich_su tests.test_m4_review_dot_pg`, PYTHONPATH=`src;.;tests`.

**Tệp (4, như vòng 1):** `m4/duyet_dot.py`, `m4/review_dot_pg.py`, `tests/test_m4_dl5b_lich_su.py`, `tests/test_m4_review_dot_pg.py`.

**Báo cáo (≤ ¼ trang)**, "Cần Anh", thông điệp commit `[M4-DL5b] vòng 2: …`.
