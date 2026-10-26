# M4-DL5b: M4 · Nghiệm thu & chi phí dự án, hiển thị lịch sử đợt chép từ Review cạnh lũy kế đã duyệt của đợt trước (CD-011, lát 6 theo kiểm kê). Rủi ro: tiền/khối lượng.

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn (không cộng, trả "cần xem lại") và ghi "Cần Anh/lead".
- Đọc `AGENTS.md`, `CLAUDE.md`. Ghi tệp UTF-8 không BOM.
- **Không commit**. Không mở server hay PostgreSQL DEMO. Không xóa file.
- Test PG tự tạo CSDL `kho_test_*` từ DSN quản trị như `tests/test_m4_review_dot_pg.py`; **không** đọc `KHO_PG_DEMO_*`.
- Không sửa vendor `m4/review_goc/...`. Không đọc dữ liệu Review thật.
- Làm trong worktree hiện tại, nhánh `lat/m4-dl5b`, dựng từ hợp nhất (đã có DL1–DL4, DL3b, CD1).

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\M4-KIEM-KE-CHEP-REVIEW.md` §5 dòng 6 · M4-DL5b. Điều kiện xong:
  - không cộng trùng legacy + seal M4;
  - dữ liệu thiếu không thành 0;
  - đối chiếu theo mã HM.
- `m4/duyet_dot.py:lich_su_da_duyet` (khoảng dòng 160–210): lũy kế từ seal M4 của các đợt trước. Được gọi ở `_xem` (dòng ~448, DTO màn 02C) và `ket_luan` (~632, ghi vào kết luận). `k2/xay_dung.py:785` đưa kết quả vào **căn cứ review** (`co["truoc_da_duyet"]`, đi vào basis hash).
- DL4 `m4/review_dot_pg.py`:
  - đợt/KL chép: `review_chep_dot_thanh_toan`, `review_chep_kl_thanh_toan` (`kl_ky`, `kl_luy_ke` theo `ma_hm`), `m4_dot_id` có thể NULL;
  - Review gốc **không có trạng thái duyệt** cho đợt. Không suy "đã duyệt".

**Việc:**
1. **Không đổi** `lich_su_da_duyet` và **không đổi** `co["truoc_da_duyet"]` hay căn cứ review: basis giữ nguyên byte, test hiện có không đổi.
2. Thêm hàm đọc lịch sử chép cho một HĐ ở bản hiện hành (`m4.review_chep_hien_hanh`) trong `review_dot_pg.py`.
   - Đọc bằng **đúng kết nối/giao dịch phiên** mà provider đang dùng. Nếu bảng chép có RLS thì dựa RLS; **không** mở kết nối tin cậy để lách quyền.
   - Không có bản chụp (3 trạng thái NULL) → `None`.
3. Trong DTO `_xem` của 02C, thêm khóa **riêng** `lich_su_review_chep` (không vào basis, không vào JSON kết luận/seal):
   - **Từng đợt trước** (`dot < so_dot` hiện tại):
     - đợt M4 cùng số **đã seal** → nguồn `M4_SEAL`; legacy của đợt đó **bỏ qua**, đếm vào `bo_qua_trung`;
     - đợt chỉ có trong Review chép → nguồn `REVIEW_CHEP`;
     - có cả hai nhưng M4 chưa seal, hoặc `m4_dot_id` trỏ sang đợt khác số → `CAN_XEM_LAI`, không cộng.
   - **Theo mã HM:**
     - `kl_luy_ke_gom_lich_su` = lũy kế seal + tổng `kl_ky` của đợt `REVIEW_CHEP`, bằng `Decimal`;
     - bất kỳ giá trị thiếu (NULL), đợt `CAN_XEM_LAI`, hoặc dòng không có mã HM → `None` kèm trạng thái `INCOMPLETE`, **không** 0.
   - **Đối chiếu nội bộ Review:** tổng `kl_ky` các đợt chép phải bằng `kl_luy_ke` của đợt chép cuối cùng cho cùng mã HM. Lệch → `LECH_LUY_KE_REVIEW`, giữ cả hai số, không chọn.
   - **Gắn vào từng dòng NT:** `_dong(kq)` có `ma_hm`. Thêm `lich_su_review_chep` cạnh `truoc_da_duyet`; dòng không có `ma_hm` → `None`.
   - **Nhãn trung tính:** "Gồm lịch sử Review đã chép — chưa qua duyệt M4". Có tính vào lũy kế chính thức hay không: ghi "Cần Anh" trong báo cáo.
4. Giữ shape cũ của `truoc_da_duyet`.
   - Kiểm validator JS `m4/giao_dien/review.js` (`voHet`) và `m4_duyet_pdf.js`: khóa mới không làm vỡ.
   - **Không** sửa JS ở lát này; hiển thị cột mới để lát giao diện sau.

**Test** (thêm vào `tests/test_m4_review_dot_pg.py`; nếu cần test provider 02C riêng thì thêm tệp `tests/test_m4_dl5b_lich_su.py`):
- Phần thuần, dữ liệu dựng sẵn:
  - seal thắng legacy cùng đợt, không cộng trùng;
  - đợt chỉ có legacy được cộng vào `kl_luy_ke_gom_lich_su`;
  - NULL ra `None`/INCOMPLETE, không 0;
  - `m4_dot_id` lệch số đợt → `CAN_XEM_LAI`;
  - lệch `kl_ky` với `kl_luy_ke` → `LECH_LUY_KE_REVIEW`;
  - dòng không có mã HM → `None`.
- Phần PG:
  - ghi lần chụp DEMO (dùng hàm ghi DL4), đọc qua phiên có quyền: đúng;
  - phiên không quyền: không lộ;
  - không có bản chụp → `None`.
- Hồi quy: basis (`co["truoc_da_duyet"]`) và JSON kết luận **không đổi byte** khi có dữ liệu chép.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m4_review_dot_pg` (+ tệp mới nếu có) và các test M4 02C hiện có (tìm `duyet_dot` trong `tests/`). PYTHONPATH=`src;.;tests`. Báo số trước/sau.

**Tệp (≤ 4):** `m4/duyet_dot.py`, `m4/review_dot_pg.py`, test (1 hoặc 2 tệp). Không sửa tệp nào khác.

**Báo cáo (≤ ⅓ trang)**: quy tắc đã áp, "Cần Anh", thông điệp commit `[M4-DL5b] …`.
