# G2 · giao G2-22 — drain, đánh thức, số đo / chế độ chạy + nợ G2-21

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** `hop-nhat-20261023` (đã đạt mốc N: G2-00…G2-21).

## Lát G2-22

**Tệp:**
- `src\kho_tri_thuc\core\vong_doi.py`
- `src\kho_tri_thuc\core\so_do.py`
- `tests\test_g2_22.py`

Nếu bắt buộc sửa `core\tien_trinh.py` để trả nợ G2-21: dừng, ghi "Cần lead", nêu đúng dòng.

**Căn cứ:**
- `CHUAN-CORE-API-v1.0.md` §3.10 (§3.10a / b: rảnh 300 giây, drain, `503` + `Retry-After`, giãn 2 giây / 4 giây, lần 3 khóa);
- `CHUAN-CORE-SDK-v1.0.md` §3.6;
- kế hoạch dòng G2-22;
- **nợ G2-21** trong `docs\47-core\g2\RV-G2-21-OPUS.md` và cuối `KE-HOACH-LAT-G2-G3.md`.
- **Dùng lại:**
  - `core\tien_trinh.py` (G2-21);
  - `core\so_cong.py` (G2-16);
  - `core\viec.py` (G2-14);
  - `core\su_kien.py` (G2-15);
  - `core\cong_tac.py` (G2-08, `TAT` / `THU` / `VAN_HANH`).

**Việc:**
- **`vong_doi.py`** — vòng đời trên `tien_trinh`:
  - rảnh 300 giây → drain;
  - drain quá hạn giữ trạng thái (không diệt mù);
  - việc trong hàng / inbox đánh thức **một** instance (không hai);
  - module `TAT` không bao giờ được bật;
  - lỗi khởi động giãn 2 giây / 4 giây, **lần 3 mới khóa** (§3.10b);
  - trong lúc drain, dispatch nhận ngay `503 TIEN_TRINH_DANG_DUNG` + `Retry-After: 2`: **không giữ khóa suốt drain** (nợ G2-21).
- **Đối chiếu sổ cổng** (nợ G2-21) — dòng `CON_GIU` mồ côi sau `loi_khoi_dong` / Admin `mo_khoa` / Core restart:
  - đối chiếu với OS (PID + thời điểm tạo, Job);
  - chỉ trả cổng khi chắc chắn không còn tiến trình giữ;
  - dùng `doi_chieu_id` theo `016_so_cong.sql`.
- **`so_do.py`:**
  - số đo bền vững (G2-16): thời gian khởi động / sẵn sàng / số lần lỗi / số lần drain;
  - Admin áp dụng chế độ đề xuất qua CAS.

**Test:**
- tiến trình Windows thật như G2-21, cổng thử do sổ cấp;
- PG (login thật):
  - rảnh → drain;
  - hai sự kiện cùng lúc → một instance;
  - `TAT` không bật;
  - 3 lỗi mới khóa;
  - 503 + `Retry-After` khi drain, không chờ khóa;
  - đối chiếu dòng mồ côi sau restart giả lập;
  - Admin CAS lệch → 409.

Báo cáo ≤ 3 dòng.
