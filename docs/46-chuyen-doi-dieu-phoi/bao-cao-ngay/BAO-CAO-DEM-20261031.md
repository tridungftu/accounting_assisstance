# Báo cáo đêm 30/10 → 31/10/2026 (lead, 05:45)

Theo quy tắc đêm CD-008, đêm qua lead:
- không gộp vào `chinh`, không đẩy GitHub;
- không xóa tệp: tệp bỏ đi đều chuyển vào `LUU-TRU`;
- không đụng kho thật hay `D:\DU-LIEU-KE-TOAN`.

Mọi lát đều gộp vào nhánh tích hợp `hop-nhat-20261023`.

## 1. Kết quả chính

- **Đã gộp 16 lượt (18 lát) Core / engine trong đêm:**
  - G2-11 → G2-16, kèm G2-13b;
  - G2-18, G2-19, G2-17b;
  - G2-00b;
  - CRM thử: G2-CR1 + CR2 (contract Dự án đang bán, Báo giá theo CD-038 1A / 2B);
  - engine phần thư viện: HD-1 (đọc hóa đơn), TRICH-1a (đọc DOCX, 37 tham số), AI-1a (DTO), MASK-1 (dự thảo 4 schema, chưa kích hoạt).
- **Hồi quy toàn bộ G2 + G3 trên nhánh hợp nhất (03:35, PostgreSQL DEMO, 29 bộ test): 740 ca đạt / 0 lỗi / 2 bỏ qua**, 0 treo.
- **Mọi lát đều qua review chéo Codex.** Các lát cốt lõi tiền / quyền / phiên qua thêm **review Opus**:
  - G2-13: 2 vòng;
  - G2-19;
  - G2-20;
  - G2-21.
  - Review bắt được nhiều lỗi thật trước khi gộp, ví dụ:
    - khóa toàn bộ chứng từ (sẽ hết bộ nhớ khóa khi có dữ liệu thật);
    - phiên chỉ có quyền xem vẫn xác nhận sự kiện được;
    - module mất kiểm tra chủ chứng từ;
    - SDK để lộ kết nối gốc và mật khẩu đăng nhập CSDL;
    - tiến trình module treo khi in nhiều.

## 2. Đang dở (chưa gộp)

| Lát | Trạng thái |
|---|---|
| G2-20 · SDK tối thiểu module / engine | Review Opus: Cần sửa (không Chặn) → vòng 4–5 đã sửa; đang chạy lại PostgreSQL |
| G2-21 · khung tiến trình, chuyển cổng nghe | Review Opus: Cần sửa (không Chặn) → vòng 2 đã sửa; đang chạy lại PostgreSQL |

Gộp xong G2-20 + G2-21 là **đạt mốc N** — mở các lát engine còn lại (khung chạy OCR / Mask / AI / hóa đơn / trích xuất).

## 3. Cần Anh quyết

1. **Cài tác vụ tự khởi động lại phiên lead** (CD-039 / CD-040):
   - hộp thư ghi Anh đã chọn "cho phép cài lâu dài";
   - đây là cấu hình chạy Claude tự động 30 phút / lần trên máy Anh, nên lead xin Anh xác nhận ngay trong phiên lead (nút "Cài đi");
   - hoặc Anh bấm đúp `tools\CAI-TU-KHOI-DONG-LEAD.cmd`.
2. **Thư viện `cryptography`:** chữ ký Ed25519 cho thẻ liên tiến trình (G2-19). Runtime DEMO đã có sẵn, nhưng chưa khai trong `pyproject.toml`. Theo quy tắc, thêm thư viện ngoài cần Anh đồng ý một lần.
3. **Sự kiện "mốc dự án đã xảy ra" (G2-CR3, `moc_da_xay_ra.v1`):** đặc tả còn chặn kích hoạt. Cần Anh chốt:
   - (a) tham chiếu lần ghi nào của mốc;
   - (b) điều kiện coi là đã xác nhận;
   - (c) module nhận;
   - (d) xử lý khi sửa / xóa ngày thực tế.
4. **Engine AI (AI-1b):** mẫu đầu vào `ai.hoi@1` và cờ "chỉ AI nội bộ" — chờ Anh duyệt (đã chờ từ đợt engine).
5. **Danh sách nhân sự đăng nhập** (phiếu CSDL câu 3A): Anh hẹn gửi sau.

## 4. Quyết định lead trong đêm (đã ghi `KE-HOACH-LAT-G2-G3.md`)

- **Ghi phạm vi hệ thống:** route ghi phạm vi hệ thống tạm bị chặn khi đăng ký. Biên nhận phạm vi hệ thống là lát **G2-11c**, giao khi có route quản trị thật.
- **Manifest engine:** chỉ có `engine.json` khi đã có ít nhất một năng lực có bộ chuyển đổi + test. Manifest viết cùng lát bộ chuyển đổi đầu tiên: OCR-2, MASK-2, AI-1b, HD-3a, TRICH-3a.
- **Ngoại lệ có màn hình:** schema manifest cho phép `headless=false` **chỉ** với ngoại lệ Anh đã duyệt (CD-038 engine 2A / 3A).
- **Giao sớm phần thư viện thuần** của engine (HD-1, TRICH-1a, AI-1a, MASK-1) trước mốc N, vì không dùng SDK / cổng / CSDL.
- **Rủi ro chấp nhận (G2-13):** hàm kiểm tiền trả đạt / không theo ngưỡng nên về lý thuyết dò được tổng bằng chia đôi — chỉ role kiểm của chính module dùng được.
- **Nợ đã ghi đích danh:**
  - G2-25: cấp quyền cửa V2 cho module cài sau; wrapper kiểm tiền theo module;
  - G2-22: đối chiếu sổ cổng sau khóa lỗi / restart; trả 503 ngay khi drain; khóa sau lần lỗi thứ 3;
  - đóng gói: `__init__.py` cho `engines/` (wheel).

## 5. Việc tiếp theo (sáng 31/10)

1. Gộp G2-20, G2-21 khi PostgreSQL đạt → mốc N.
2. Giao G2-22 (drain / đánh thức / số đo + nợ đối chiếu), G2-23 (két DEMO / mã hóa — cần chốt adapter), G2-24 đã có → G2-25 (áp gói, Opus).
3. Giao lát engine sau mốc N: OCR-2 / 4a, AI-4a / 5a, HD-2a / 3a, TRICH-3a; chưa tích hợp tiến trình thật khi chưa có G2-22 / 23 / 27 / 33.
