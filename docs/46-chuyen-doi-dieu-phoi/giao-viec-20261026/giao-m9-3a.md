# M9-3a: M9 · Vốn vay & đầu tư tài chính, chuẩn hóa bảng số dư/lãi suất kéo từ Sheet thành snapshot có mốc (thuần, chưa gọi Google API)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn (dòng lỗi, không đoán) và ghi "Cần Anh/lead".
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server. Không xóa file.
- **Không mạng, không gọi Google API, không đọc `.env`**, không AI, không thư viện ngoài.
- Làm trong worktree hiện tại, nhánh `lat/m9-3a`, dựng từ hợp nhất. Đã có `m9/bao_cao_lai_suat.py` (M9-4a); đầu vào snapshot của nó xem docstring `lap_bao_cao`.

**Căn cứ:**
- CD-015 mục 3–4 (`docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md`):
  - số dư/lãi suất chỉ từ snapshot Sheet có mốc;
  - Sheet chỉ đọc; khóa trong `.env` (lát sau);
  - **chờ Anh cung cấp Sheet/tab** nên lát này dùng cấu hình cột và Sheet giả.
- Thiết kế M9 §2, §5.1: `D:\Claude\Phan mem ho tro ke toan\THIET-KE-MODULE-DE-CHOT-2026-10-20\M9-KHO-HOP-DONG-VAY-HOI-DAP-20261026.md`. Hai nguồn lệch thì báo lệch, không tự chọn.

**Việc: tệp mới `src/kho_tri_thuc/m9/snapshot_sheet.py`.**
1. `CAU_HINH_MAU`: dict mô tả một tab, đặt là cấu hình giả DEMO.
   - `ten_tab`, `dong_tieu_de`;
   - ánh xạ **tên cột tiêu đề** → trường: `phap_nhan`, `ngan_hang`, `ma_khoan_vay`, `tien_te`, `du_no`, `lai_suat_nam`, `cach_tinh`, `lai_co_so`, `bien_do`, `ky_dieu_chinh_ke_tiep`, `ngay_dao_han`.
2. `lap_snapshot(gia_tri: list[list[str]], *, cau_hinh: dict, keo_luc: datetime, nguon_id: str) -> dict`.
   - `gia_tri` là ô dạng chuỗi như Sheets API `values.get` trả về.
   - Tìm cột theo **tên tiêu đề**, không theo vị trí. Thiếu cột bắt buộc → lỗi `M9_SHEET_THIEU_COT`, nêu tên cột.
   - Chuẩn hóa:
     - tiền dạng VN `1.234.567.890` hoặc `1,234,567,890.50` (nhận biết theo cấu hình `dau_thap_phan`, mặc định `,`) → `Decimal`;
     - lãi suất `8,5%` / `8.5` → `Decimal` % / năm;
     - ngày dd/mm/yyyy → `date`;
     - ô trống → `None`, **không 0**;
     - ô không đọc được → dòng vào `dong_loi` với số dòng + tên cột + mã lỗi, **không** đưa vào `khoan_vay`.
   - Trùng `ma_khoan_vay` → cả hai dòng vào `dong_loi` (`TRUNG_MA`), không chọn.
   - Kết quả:
     - `{"moc": keo_luc định dạng "dd/mm/yyyy hh:mm", "nguon": "Sheet", "nguon_id", "tab", "sha256"}`;
     - `sha256` của **giá trị thô đã chuẩn hóa thứ tự**, ổn định giữa hai lần chạy;
     - `"khoan_vay": [...]` đúng shape đầu vào của `bao_cao_lai_suat.lap_bao_cao`;
     - `"dong_loi": [...]`, `"so_dong_doc"`.
3. Không ghi đĩa, không log nội dung ô.

**Test, tệp mới `tests/test_m9_snapshot_sheet.py`** (Sheet giả **DEMO**, tên ngân hàng/pháp nhân giả):
- Cột đảo thứ tự vẫn đọc đúng; thiếu cột → `M9_SHEET_THIEU_COT`.
- `1.234.567.890` → `Decimal('1234567890')`; `8,5%` → `Decimal('8.5')`; ô trống → `None`.
- Ngày sai (`31/02/2026`) → `dong_loi`.
- Trùng mã → cả hai vào `dong_loi`.
- `sha256` giống nhau giữa hai lần chạy; đổi một ô thì khác.
- Đầu ra đưa thẳng vào `lap_bao_cao` chạy được (tích hợp với M9-4a).
- Không có float trong kết quả.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_snapshot_sheet tests.test_m9_bao_cao_lai_suat`, PYTHONPATH=`src;.;tests`.

**Tệp (2):** `m9/snapshot_sheet.py`, `tests/test_m9_snapshot_sheet.py`.

**Báo cáo (≤ ¼ trang)**, "Cần Anh", thông điệp commit `[M9-3a] …`.
