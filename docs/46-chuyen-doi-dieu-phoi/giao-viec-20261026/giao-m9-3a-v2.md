# M9-3a vòng 2: ô lỗi Sheet ở mọi cột vào dong_loi (Chặn) + câu trung tính

Bạn là worker Codex, chạy không tương tác. Làm ngay. Ghi UTF-8 không BOM. Không commit. Không mạng/AI/thư viện ngoài, không đọc tệp bí mật. Worktree hiện tại, nhánh `lat/m9-3a` (HEAD f0a9caf). Chỗ chưa rõ: dừng và ghi "Cần lead".

**Đọc:** `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\review-m9-3a.md` (đã lead lọc), giao việc gốc `giao-m9-3a.md`.

**Việc** (`m9/snapshot_sheet.py`):
1. **Chặn:** ô có giá trị lỗi của Sheet (`#N/A`, `#REF!`, `#VALUE!`, `#DIV/0!`, `#NAME?`, `#NUM!`, `#NULL!`, `#ERROR!`, `#CALC!`, `#SPILL!`, `Loading...`) ở **bất kỳ** cột nào → dòng vào `dong_loi` (mã `O_LOI_SHEET`, số dòng + tên cột), không vào `khoan_vay`.
2. `tien_te` phải thuộc danh sách cho phép trong cấu hình (mặc định `VND`, `USD`; so không phân biệt hoa thường, chuẩn hóa về chữ hoa); khác → `dong_loi` (`TIEN_TE_KHONG_HO_TRO`). `cach_tinh` tương tự với `CO_DINH`/`THA_NOI` nếu có giá trị.
3. Câu/ghi chú trong mã (khoảng dòng 173 `ghi_chu`) không chứa "Cần Anh/lead"; dùng câu trung tính (ví dụ "Cấu hình mẫu DEMO; thay bằng tab và tên cột thật khi có Sheet.").

**Test** (`tests/test_m9_snapshot_sheet.py`): `#N/A` ở cột tiền tệ/ngân hàng/mã khoản vay → `dong_loi`, không vào khoản vay, báo cáo M9-4a không có nhóm đồng tiền lạ; `usd` → `USD`; `EUR` (không trong cấu hình) → `dong_loi`; chuỗi "Cần Anh" không còn trong mã. Ca cũ vẫn đạt. **Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_snapshot_sheet tests.test_m9_bao_cao_lai_suat`. **Tệp (2):** `m9/snapshot_sheet.py`, `tests/test_m9_snapshot_sheet.py`. Báo cáo ≤ 5 dòng, thông điệp `[M9-3a] vòng 2: …`.
