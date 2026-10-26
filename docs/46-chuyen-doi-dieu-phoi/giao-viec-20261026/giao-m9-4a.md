# M9-4a: M9 · Vốn vay & đầu tư tài chính, báo cáo lãi suất định kỳ: tính "lãi cao" + xuất Excel (thuần, CD-015 mục 5)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn (không tính, đánh dấu thiếu) và ghi "Cần Anh/lead".
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server. Không xóa file. Không mạng, không AI.
- Chỉ dùng thư viện đã có (`openpyxl` cho Excel).
- Làm trong worktree hiện tại, nhánh `lat/m9-4a`, dựng từ hợp nhất (đã có gói `src/kho_tri_thuc/m9/`).

**Căn cứ:**
- CD-015 mục 5 (`docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md`):
  - báo cáo lãi suất hằng tháng;
  - "lãi cao" = **cao hơn bình quân gia quyền theo dư nợ của danh mục cùng mốc**;
  - cảnh báo trước kỳ điều chỉnh lãi 30 ngày;
  - không tự gửi ra ngoài.
- Thiết kế M9 §4, §5: `D:\Claude\Phan mem ho tro ke toan\THIET-KE-MODULE-DE-CHOT-2026-10-20\M9-KHO-HOP-DONG-VAY-HOI-DAP-20261026.md`.
- Số dư/lãi suất **chỉ** từ snapshot Sheet có mốc (M9-3 làm sau). Lát này nhận snapshot đã chuẩn hóa làm đầu vào.

**Việc: tệp mới `src/kho_tri_thuc/m9/bao_cao_lai_suat.py`.**
1. `lap_bao_cao(snapshot: dict, *, ngay_bao_cao: date) -> dict`.
   - `snapshot` = `{"moc": "dd/mm/yyyy hh:mm", "nguon": "Sheet", "khoan_vay": [...]}`.
   - Mỗi khoản vay: `phap_nhan`, `ngan_hang`, `ma_khoan_vay`, `tien_te` (`VND`/`USD`…), `du_no` (`Decimal`), `lai_suat_nam` (`Decimal`, % / năm), `cach_tinh` (`CO_DINH` / `THA_NOI` + `lai_co_so`, `bien_do` nếu có), `ky_dieu_chinh_ke_tiep` (date | None), `ngay_dao_han` (date | None).
2. **Bình quân gia quyền theo dư nợ**, tách **theo từng đồng tiền** (không quy đổi, không trộn VND với USD):
   - công thức: `Σ(du_no × lai_suat) / Σ du_no`;
   - chỉ tính trên khoản có đủ `du_no > 0` và `lai_suat_nam`;
   - khoản thiếu số liệu → trạng thái `THIEU_DU_LIEU`, **không** tính vào bình quân, **không** coi là 0.
3. Mỗi khoản đủ số liệu:
   - `chenh_lech` = `lai_suat − binh_quan` (điểm %);
   - `lai_cao` = `chenh_lech > 0`;
   - `lai_tra_them_uoc_tinh_nam` = `du_no × chenh_lech / 100`, **chỉ khi lãi cao**; ghi nhãn "ước tính", có đơn vị tiền tệ;
   - làm tròn **chỉ khi hiển thị/xuất**, theo đơn vị tiền: VND 0 số lẻ, USD 2 số lẻ; giữ `Decimal` đầy đủ trong dict.
4. Cảnh báo `SAP_DIEU_CHINH` khi `ngay_bao_cao ≤ ky_dieu_chinh_ke_tiep ≤ ngay_bao_cao + 30 ngày`. Thêm `DA_QUA_KY` khi kỳ điều chỉnh < ngày báo cáo.
5. Sắp xếp:
   - theo đồng tiền, rồi chênh lệch giảm dần;
   - trong cùng đồng tiền, khoản `THIEU_DU_LIEU` xếp cuối.
6. Kết quả có:
   - `moc` và `nguon` (bắt buộc);
   - tổng dư nợ theo đồng tiền;
   - số khoản lãi cao;
   - danh sách cảnh báo.
7. `xuat_excel(bao_cao) -> bytes` bằng `openpyxl`:
   - một sheet;
   - tiêu đề có mốc dữ liệu "Nguồn: Sheet theo dõi khoản vay, mốc dd/mm/yyyy hh:mm";
   - cột tiếng Việt có đơn vị;
   - ngày dd/mm/yyyy;
   - số tiền dạng số (không chuỗi) với định dạng hiển thị;
   - không công thức;
   - ghi chú cuối: "Lãi trả thêm là ước tính; không gửi ra ngoài khi chưa duyệt."
8. Cột "điều khoản liên quan tới đàm phán" để trống, ghi chú "chờ nối trích dẫn hợp đồng (M9-2)". Không đoán.

**Test, tệp mới `tests/test_m9_bao_cao_lai_suat.py`** (dữ liệu giả **DEMO**, tên ngân hàng/pháp nhân giả):
- Ví dụ số tay 3 khoản VND:
  - bình quân đúng tới `Decimal` đầy đủ;
  - khoản cao nhất đứng đầu;
  - lãi trả thêm đúng.
- Khoản USD tách nhóm riêng, không ảnh hưởng bình quân VND.
- Khoản thiếu lãi suất → `THIEU_DU_LIEU`, không vào bình quân, không là 0.
- Biên 30 ngày:
  - ngày thứ 30 → cảnh báo;
  - ngày 31 → không;
  - quá kỳ → `DA_QUA_KY`.
- Không có khoản đủ số liệu → bình quân `None`, không chia cho 0.
- Excel đọc lại bằng `openpyxl`:
  - tiêu đề có mốc;
  - ô tiền là số;
  - ngày đúng định dạng;
  - không có công thức.
- Không có float trong dict kết quả (duyệt đệ quy).

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_bao_cao_lai_suat`, PYTHONPATH=`src;.;tests`.

**Tệp (2):** `m9/bao_cao_lai_suat.py`, `tests/test_m9_bao_cao_lai_suat.py`.

**Báo cáo (≤ ¼ trang)**, "Cần Anh", thông điệp commit `[M9-4a] …`.
