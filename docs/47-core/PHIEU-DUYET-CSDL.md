# Phiếu duyệt 1/3 · Phân chia cơ sở dữ liệu (CD-029 mục 2a)

**Lập:** 30/10/2026, lead. **Trạng thái:** chờ Anh duyệt.
**Đây là tài liệu, chưa lập trình.** Chưa tạo bảng, chưa chạy gì trên CSDL. Lệnh dừng lập trình CD-026 vẫn giữ.
**Đã kiểm:**
- Codex soạn, Codex review chéo: đủ 67/67 migration, kiểm mẫu đúng 94,7%.
- Opus review hai vòng: vòng 1 có 3 điểm Chặn; vòng 2 không còn Chặn.

## 1. Kết luận (đề nghị Anh duyệt)

1. **Một CSDL PostgreSQL chung** tại `D:\DU-LIEU-KE-TOAN`, chia thành **khối**, mỗi khối một chủ:
   - **Core giữ ba khối:**
     - `loi`: người dùng, pháp nhân, ma trận thẩm quyền, module, engine, sổ cổng, việc nền, nhật ký;
     - `loi_tai_lieu`: tài liệu, tệp, kết quả OCR/che;
     - `danh_muc`: đối tác, dự án, tài khoản, hợp đồng (khóa chung), đầu chứng từ, định danh hóa đơn, khóa kỳ, liên kết chứng từ.
   - **Mỗi module giữ khối riêng** `mod_crm`, `mod_m2`, `mod_m4`, `mod_m3`, `mod_m9`…
   - **Dữ liệu cho module khác đọc** chỉ qua khối công bố `cong_bo_<module>` (chỉ đọc, có phiên bản).
   - **Phần kế toán cũ** tạm ở `ke_toan_cu` cho tới khi chuyển xong.
2. **Không module nào đọc/ghi thẳng bảng của module khác.** Đi qua hàm Core hoặc khối công bố; có test tự động, lệch là đỏ (CD-018).
3. **Mỗi khối hai vai trò CSDL:**
   - **một vai để chạy:** không làm chủ bảng, không vượt phân quyền;
   - **một vai để đổi cấu trúc:** chỉ dùng khi cài/nâng cấp.
   - **Đăng nhập CSDL:**
     - Core và mỗi module có tên đăng nhập riêng;
     - engine (OCR, Mask…) và máy xử lý phụ **không** có đăng nhập CSDL.
   - **Mật khẩu** ở `D:\DU-LIEU-KE-TOAN\bi-mat\`, ngoài thư mục phần mềm.
4. **Phân quyền hai tầng theo pháp nhân** (CD-021):
   - máy chủ kiểm;
   - CSDL lọc dòng theo pháp nhân, áp cả việc nền, tải tệp và công cụ xuất riêng một công ty.
   - Quyền **hành động** (xem/sửa/duyệt, hạn mức) vẫn do ma trận thẩm quyền quyết, chỉ một nguồn.
5. **Kiểm tiền không bị sai vì phân quyền:** "không vượt tiền chứng từ" và "không vượt nghĩa vụ" tính trên đủ dòng của pháp nhân, kể cả dòng người dùng không được xem. Có test âm bắt buộc ở bước dựng.
6. **Migration theo gói:** Core chỉ giữ phần Core; mỗi module mang migration của mình. 67 migration cũ được ánh xạ đủ sang khối mới (phụ lục). Không sửa lịch sử cũ.
7. **Ít tài nguyên** (QD-09): bảng cố định, mỗi lần phát sinh là thêm dòng; dữ liệu tạm và tài nguyên test có hạn giữ và cách dọn.

## 2. Ba điểm thay đổi lớn so với hiện nay (Anh nên biết)

| Điểm | Hiện nay | Sau chuẩn hóa |
|---|---|---|
| **Liên kết tiền:** chứng từ ↔ lịch thu CRM / lịch trả nợ M9 | Bảng liên kết chung gắn cứng vào bảng của CRM, M9 | Liên kết ở Core, trỏ nghĩa vụ bằng mã. Core kiểm tiền chứng từ, module chủ kiểm nghĩa vụ, cùng một giao dịch |
| **Hóa đơn M2 dùng ở M4, M3** | M4, M3 gắn cứng vào bảng hóa đơn của M2 | Định danh hóa đơn lên Core. M4, M3 ghim phiên bản hóa đơn qua khối công bố của M2. **Dựng được M4 trước M2** (đúng thứ tự TL 55) |
| **Danh tính người thao tác** | CSDL tin biến "người dùng" do phần mềm tự đặt | Core cấp **mã phiên bí mật**; CSDL tự kiểm mã → một module không thể tự nhận là người khác |

## 3. Câu cần Anh chọn

| # | Câu hỏi | A | B | Khuyến nghị |
|---|---|---|---|---|
| 1 | Module chạy tiến trình riêng (CD-028). CSDL có chặn cả trường hợp **một module tự nhận là người dùng khác** không? | **Có:** Core cấp mã phiên, CSDL kiểm; bước dựng Core tốn thêm ít công | **Không:** coi module nội bộ là tin cậy, CSDL chỉ chặn sai pháp nhân | **A** |
| 2 | **Hạn giữ dữ liệu tạm** (gồm kết quả OCR/Mask tạm) **và tài nguyên test** | Tệp tạm: thành công 24 giờ / lỗi 7 ngày. Dấu chống trùng 30 ngày. Số đo vận hành: chi tiết 90 ngày, tổng hợp 1 năm. CSDL/role test: thành công 7 ngày / lỗi 14 ngày | Admin quyết từng đợt | **A**. Bản gốc, kết quả đã duyệt, nhật ký nghiệp vụ **không** bị dọn. 303 CSDL + 651 role test tồn đọng hiện nay: chỉ dọn khi Anh giao lát bảo trì riêng, có xem trước |
| 3 | **Tài khoản đăng nhập thật** | Core tự quản tài khoản người dùng | Nối hệ tài khoản sẵn có (Anh cho biết hệ nào); Core giữ ánh xạ | **A**, trừ khi công ty đã có hệ tài khoản tập trung |

**Báo, không cần chọn** (đã có căn cứ Anh chốt trước):
- Hợp đồng: khóa chung ở `danh_muc`, phiên bản/lịch nghĩa vụ ở CRM (TL 55 §1).
- Liên kết chứng từ ghi qua Core (CD-018).
- Ánh xạ mở che vẫn do Mask quản lý.
- Mã hóa cột theo nhóm A đã duyệt (QD-20261026-11).

## 4. Anh duyệt bằng cách

Trả lời một dòng, ví dụ: **"Duyệt CSDL; câu 1 A, câu 2 A, câu 3 A"**, hoặc ghi điểm cần đổi. Phiếu 2 (API) và phiếu 3 (SDK) gửi riêng khi xong (CD-029). **Bước dựng Core (G2) chỉ bắt đầu khi đủ cả ba phiếu được duyệt.**

## Phụ lục (chi tiết kỹ thuật)

- Đặc tả đầy đủ: `docs\47-core\g1\DAC-TA-CSDL.md`, gồm:
  - bảng tên tiếng Việt;
  - mô hình bảng Core;
  - vai trò và đăng nhập;
  - phân quyền theo pháp nhân;
  - mã hóa cột;
  - thứ tự dựng gói;
  - dọn dẹp.
- Ánh xạ 67 migration cũ → khối mới: `docs\47-core\g1\ANH-XA-MIGRATION.md`.
- Khảo sát hiện trạng: `docs\47-core\g0\KHAO-SAT-CORE.md`, `KS-B.md`.
- Biên bản review:
  - `g1\RV-G1A.md` (Codex);
  - `g1\RV-G1A-OPUS.md` (Opus vòng 1);
  - vòng 2: không còn Chặn, hai bổ sung nhỏ đã ghi vào §5 của đặc tả.

## Kết quả Anh trả lời (30/10/2026)

- **Câu 2: A.** Hạn giữ dữ liệu tạm, gồm kết quả OCR/Mask tạm, và tài nguyên test theo phương án A.
- **Câu 3: A.** Core tự quản tài khoản. Anh sẽ gửi danh sách nhân sự đăng nhập sau.
- **Câu 1: Anh hỏi lại** "trường hợp nào module tự nhận là người dùng khác được?". Lead đã giải thích bằng ví dụ trong phiên làm việc; chờ Anh chọn A/B.
- **Duyệt toàn phiếu:** chờ câu 1.
- **ANH ĐÃ DUYỆT CẢ PHIẾU (30/10/2026):** "Duyệt CSDL 1 A".
  - Câu 1: A. Core cấp mã phiên bí mật, CSDL tự kiểm.
  - Câu 2: A.
  - Câu 3: A (danh sách nhân sự Anh gửi sau).
