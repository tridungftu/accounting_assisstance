# M9-4c: câu hiện cho người dùng trong báo cáo lãi suất M9 phải trung tính (bỏ "Cần Anh/lead")

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM. Không commit. Không mạng/AI. Không xóa file.
- Chỗ chưa rõ: dừng, ghi "Cần lead".
- Làm trong worktree hiện tại, nhánh `lat/m9-4c`, dựng từ hợp nhất (đã có M9-4a, M9-4b).

**Phát hiện khi lead kiểm xác suất:** `src/kho_tri_thuc/m9/bao_cao_lai_suat.py` có 7 chuỗi "Cần Anh/lead: …" ở thông báo lỗi (`ValueError`), `ghi_chu` của khoản vay và danh sách `can_anh` của kết quả. Các chuỗi này hiện ra màn hình/Excel. Quy ước giao diện: tiếng Việt nghiệp vụ trung tính, không "Cần Anh", không mã kỹ thuật.

**Việc** (`m9/bao_cao_lai_suat.py`):
1. Đổi các chuỗi sang câu trung tính, giữ đúng nghĩa. Ví dụ:
   - "Chỉ nhận dữ liệu từ Sheet có mốc thời gian."
   - "Mốc dữ liệu phải có dạng dd/mm/yyyy hh:mm."
   - "Thiếu dữ liệu: dư nợ, lãi suất."
   - "Ngày kỳ điều chỉnh chưa đúng định dạng."
   - "Chưa có quy tắc làm tròn cho đồng tiền USD; số xuất chưa làm tròn."

   Tên trường kỹ thuật như `ky_dieu_chinh_ke_tiep` đổi sang nhãn tiếng Việt.
2. Khóa `can_anh` trong kết quả đổi thành `can_xem_lai`. Giữ khóa cũ làm bí danh **chỉ khi** có chỗ khác trong `src/` đang đọc (grep); không có thì đổi hẳn.
3. Không đổi số liệu, thứ tự hay logic.

**Test** (`tests/test_m9_bao_cao_lai_suat.py`):
- Không chuỗi nào trong kết quả và Excel chứa "Cần Anh", "lead" hay tên trường có `_`.
- Các ca cũ vẫn đạt; sửa kỳ vọng chuỗi theo câu mới.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_bao_cao_lai_suat`, PYTHONPATH=`src;.;tests`. Không có `python` thì ghi NOT_RUN.

**Tệp (2):** `m9/bao_cao_lai_suat.py`, `tests/test_m9_bao_cao_lai_suat.py`.

**Báo cáo (≤ 4 dòng)**, thông điệp commit `[M9-4c] …`.
