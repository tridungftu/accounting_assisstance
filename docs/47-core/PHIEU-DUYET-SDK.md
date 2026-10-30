# Phiếu duyệt 3/3 · SDK của Core (CD-029 mục 2c)

**Lập:** 30/10/2026, lead. **Trạng thái:** chờ Anh duyệt.
**Đây là tài liệu, chưa lập trình.**
**Đã kiểm:**
- Codex soạn, Codex review chéo (vòng 1: 1 Chặn).
- Opus review hai vòng: vòng 1 có 3 Chặn; vòng 2 không còn Chặn.
- Lead tự kiểm 12/12 JSON Schema hợp lệ chuẩn draft 2020-12.

## 1. Kết luận (đề nghị Anh duyệt)

**SDK là bộ công cụ chung** mà mọi module và engine dùng để nói chuyện với Core. Nhờ có SDK, module mới không tự viết lại phần đăng nhập, tệp, OCR, mã hóa… (CD-019: mỗi năng lực một chỗ).

1. **SDK Python** (cho phần máy chủ của module và adapter engine) gồm **12 dịch vụ**:

   | Dịch vụ | Dùng để |
   |---|---|
   | `danh_tinh` | Biết ai đang thao tác, kiểm quyền |
   | `tai_lieu`, `tep`, `ket_qua` | Hồ sơ, tải lên/xuống tệp, kết quả OCR/che/trích xuất. Nguồn kết quả do Core tự gắn, module không khai thay được |
   | `du_lieu_rieng` | Đọc/ghi đúng khối dữ liệu của module (theo phiếu CSDL) |
   | `cong_bo` | Đọc dữ liệu module khác đã công bố |
   | `su_kien` | Phát/nhận sự kiện giữa module, chống trùng |
   | `engine` | Gọi OCR, Mask, trích xuất, hóa đơn qua Core |
   | `quy_trinh`, `viec` | Chạy quy trình, theo dõi/hủy việc lâu |
   | `kiem_toan` | Ghi nhật ký, số đo vận hành |
   | **`ma_hoa`** | Mã hóa/tra cứu cột nhạy cảm nhóm A (CCCD, số tài khoản…) qua cổng Core. Khóa chỉ nằm ở Core |

2. **SDK giao diện (JS):**
   - gọi `/api/v1/`, hiện lỗi chuẩn tiếng Việt;
   - theo dõi việc;
   - khung lưới icon (TL 49);
   - ô nhập chuẩn: %, tiền có đơn vị, ngày dd/mm/yyyy.
3. **Khung chạy module/engine (CD-028, đúng phiếu API Anh đã duyệt):**
   - nhận cổng do Core chuyển giao; báo sẵn sàng (kiểm cả phiên bản dữ liệu);
   - dừng có kiểm soát khi Core thu hồi;
   - Core tự đánh thức module khi có việc chờ;
   - Core đo RAM/CPU từng lần chạy.
4. **Gói module = thư mục + tệp `module.json`.** Tệp khai báo:
   - tên, phiên bản;
   - menu, thao tác, quyền (có tiền tố tên module);
   - khối dữ liệu, migration, phần công bố;
   - engine cần dùng, sự kiện, cột mã hóa.

   Core **tự suy** tên khối, vai CSDL và cổng; module không được tự khai, để không leo quyền. Đủ để **cài module qua giao diện mà không sửa Core** (tiêu chí TL 54).
5. **Chuẩn dữ liệu trao đổi (contract)**, có phiên bản. Mọi thay đổi tạo bản mới, không sửa bản cũ:
   - `tham_chieu_tep`, `van_ban_tai_lieu`, `du_lieu_bang`, `tham_so`;
   - `noi_dung_da_che`: không che tiền/ngày;
   - `tra_loi_ai`: đi Cloud bắt buộc có lượt che Mask (TL 48);
   - `hoa_don`: có thuế suất dòng; không cộng dòng chiết khấu ra tổng;
   - `loi_chuan`, `viec`.

   Tiền ghi dạng số thập phân + mã tiền tệ.
6. **Bộ kiểm tuân thủ tự động** cho mỗi module/engine. Chạy khi cài, mỗi lần kích hoạt và mỗi lần Core khởi động; lệch là đỏ, module không được kích hoạt. Kiểm:
   - đúng khối dữ liệu, không đọc/ghi chéo;
   - quyền thực tế so với khai báo;
   - route đúng chuẩn, contract hợp lệ;
   - không lộ khóa/mật khẩu vào log;
   - gọi thẳng cổng module mà không có thẻ thì bị từ chối;
   - tiến trình con không đọc được kho mật khẩu.

## 2. Câu cần Anh chọn

| # | Câu hỏi | Phương án | Khuyến nghị |
|---|---|---|---|
| 1 | **Module nào dùng để thử Core ở bước dựng Core (G2)?** Khác với M4, module mẫu đầu tiên ở G4 đã chốt | **A.** Tra cứu tài liệu, chỉ dữ liệu DEMO<br>**B.** M9 theo đúng phạm vi CD-015<br>**C.** Không thử riêng, thử thẳng bằng M4 ở G4 | **A**: nhỏ nhưng đi qua đủ tệp, OCR, việc lâu, công bố, cài/tắt; không có dữ liệu thật. C làm lỗi Core lộ muộn |
| 2 | **Tài khoản Windows chạy module/engine.** Khác câu 3 phiếu CSDL: câu đó là tài khoản người dùng | **A.** Tài khoản hạn chế: module/engine **không đọc được** kho mật khẩu `D:\DU-LIEU-KE-TOAN\bi-mat\` và bộ nhớ Core; tốn thêm công thiết lập, thử ở G2<br>**B.** Chạy chung tài khoản với Core: dễ vận hành, nhưng một thư viện lỗi/độc trong module hay engine (ví dụ thư viện OCR) đọc được mật khẩu mọi tài khoản CSDL và khóa mã hóa | **A** |
| 3 | **Module đang tự đóng mà có việc chờ** (ví dụ việc OCR xếp hàng) | **A.** Core bật module ngay để làm việc<br>**B.** Gom, 15 phút bật một lần<br>**C.** Chỉ bật khi có người mở màn hình module | **A** mặc định; Admin đổi theo số đo (CD-028 mục 3b). Không tự bật module Anh đã tắt |

**Báo, không cần chọn:**
- M4 là module mẫu đầu tiên ở G4 (TL 55, CD-027).
- Hạn giữ kết quả OCR tạm theo phiếu CSDL câu 2 (Anh đã chọn A).
- Phần danh tính và mã hóa của SDK dựa trên **mã phiên bí mật** (phiếu CSDL câu 1, đang chờ Anh). Nếu Anh chọn B ở câu đó, hai phần này sửa theo.

## 3. Anh duyệt bằng cách

Trả lời một dòng, ví dụ: **"Duyệt SDK; 1A, 2A, 3A"**, hoặc ghi điểm cần đổi.

**Còn chờ trước khi dựng Core (G2):**
- phiếu CSDL câu 1;
- phiếu SDK này;
- **CD mới của Anh mở lại lập trình** (CD-026/029).

## Phụ lục (chi tiết kỹ thuật)

- Đặc tả: `docs\47-core\g1\DAC-TA-SDK.md`:
  - 12 dịch vụ và hàm chính §3;
  - khung tiến trình, danh tính hệ điều hành §4;
  - SDK JS §5;
  - mẫu `module.json` và engine manifest §6;
  - vòng đời cài/nâng cấp/tắt §7.
- Contract và bộ kiểm: `docs\47-core\g1\CONTRACT-DU-LIEU.md`:
  - 12 JSON Schema kèm ví dụ;
  - đối chiếu trường với OCR/Mask/hóa đơn XML thực tế;
  - danh sách kiểm KT01–KT16.
- Biên bản review:
  - `g1\RV-G1C.md` (Codex);
  - `g1\RV-G1C-OPUS.md` (Opus vòng 1);
  - vòng 2: không còn Chặn, ba câu bổ sung đã ghi vào đặc tả.
