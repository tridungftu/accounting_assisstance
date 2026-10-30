# G1c · Đặc tả SDK Core (CD-027 mục 1, CD-028, CD-029 mục 2c) — Codex soạn nháp, chỉ tài liệu

## Phần chung

Giống `docs\47-core\g1\GIAO-G1A.md` phần chung:
- chỉ đọc;
- câu trả lời cuối là toàn văn tài liệu;
- dừng lập trình;
- khẳng định có `tệp:dòng`;
- tên tiếng Việt không dấu;
- không lộ dữ liệu cấm.

**Đầu vào:**
- TL 54 §5.2, §7, §8;
- TL 55 §3, §5, §10;
- CD-028;
- khảo sát `docs\47-core\g0\KS-A.md`, `KS-D.md`, `KS-E.md`;
- nháp `docs\47-core\g1\DAC-TA-CSDL.md`, `DAC-TA-API.md`;
- review `RV-G1A-OPUS.md` (mã phiên bí mật, engine không login CSDL, module gọi Core qua hàm/API).

Chỗ phụ thuộc phiếu CSDL/API chưa duyệt: ghi "theo phiếu CSDL/API".

**Tận dụng mã hiện có** (kèm tệp:dòng), không thiết kế lại cái đã đúng:
- hợp đồng engine `ha_tang\engine.py`, `danh_ba_engine.py`, `engine_cong.py`;
- hàng việc `ha_tang\hang_viec.py`, `k2\sql_hang_viec.py`;
- bus `ha_tang\bus_su_kien.py`;
- khai báo vùng `ha_tang\khai_bao_module.py`, `k2\vung_du_lieu.py`;
- công tắc `k2\module.py`;
- các test kiểm rời rạc hiện có (XS-5, MTQ).

## Lát G1c-1 · `DAC-TA-SDK.md` + mẫu `module.json`

1. **SDK Python** (module backend, engine adapter):
   - **Dịch vụ:** `danh_tinh` · `tai_lieu` · `tep` · `ket_qua` · `du_lieu_rieng` · `cong_bo` · `su_kien` · `engine` · `quy_trinh` · `viec` · `kiem_toan`.
   - **Mỗi dịch vụ ghi:** mục đích; 3–6 hàm chính (chữ ký, đầu vào/ra, lỗi); dựa trên API hay hàm CSDL nào; phần tái dùng mã hiện có.
2. **Khung tiến trình module/engine (CD-028):**
   - nhận ổ nghe chuyển giao từ Core (`socket.fromshare`) hoặc tham số cổng;
   - báo readiness;
   - dừng có kiểm soát khi Core thu hồi;
   - nhận mã phiên/ủy nhiệm từ Core;
   - nhận mật khẩu CSDL qua stdin/handle (module), engine không có login CSDL;
   - ghi số đo khởi động.
3. **SDK giao diện (JS):**
   - gọi `/api/v1/` (lỗi chuẩn, khóa chống trùng, 409);
   - theo dõi việc;
   - khung lưới icon (TL 49);
   - bảng nhập liệu chuẩn (ô %/tiền, ngày dd/mm/yyyy, tiền có đơn vị);
   - thông báo lỗi chuẩn.

   Tái dùng gì từ `giao_dien\assets\*.js`.
4. **Mẫu `module.json`:** đầy đủ trường, ví dụ cho một module mẫu nhỏ, gồm:
   - danh tính, phiên bản, tương thích Core;
   - giao diện/menu;
   - operation;
   - khối dữ liệu riêng + gói migration;
   - quyền yêu cầu;
   - capability engine dùng;
   - quy trình;
   - công bố cho module khác;
   - sự kiện phát/nhận;
   - cổng do Core cấp (module không tự chọn);
   - chế độ chạy mặc định "tự kích hoạt + tự đóng".

   Thêm mẫu **engine manifest** (capability, launch profile, readiness, giới hạn tài nguyên).
5. **Vòng đời cài / nâng cấp / tắt module qua giao diện** (Module Manager) ở mức SDK: kiểm gói, chạy migration gói, không mất dữ liệu.
6. **Câu cần Anh chọn:** bảng phương án + khuyến nghị, tối đa 5 câu. Trong đó có câu **module mẫu đầu tiên** (TL 55 gợi ý M4; CD-026 gợi ý M9/Tra cứu tài liệu).

Thân ≤ 8 trang.

## Lát G1c-2 · `CONTRACT-DU-LIEU.md` (JSON Schema) + `BO-KIEM-TUAN-THU.md`

1. **JSON Schema (draft 2020-12)** cho 7 contract:
   - `tham_chieu_tep.v1`, `van_ban_tai_lieu.v1`, `du_lieu_bang.v1`, `tham_so.v1`;
   - `noi_dung_da_che.v1`, `tra_loi_ai.v1`, `hoa_don.v1`.

   Thêm `loi_chuan.v1` và `viec.v1` nếu API cần. Tiền: số thập phân dạng chuỗi + đơn vị. Ngày ISO trong dữ liệu. Có `$id` và phiên bản. Mỗi contract kèm một ví dụ hợp lệ (dữ liệu giả có chữ DEMO).

   Đối chiếu với đầu ra thực tế của OCR (`KS-E`), Mask (`KS-D`), trích xuất #6/E1, hóa đơn XML (`nguon\hoa_don_xml.py`): trường nào lấy từ đâu.
2. **Bộ kiểm tuân thủ** cho mỗi module/engine. Danh sách kiểm tự động:
   - đúng khối dữ liệu, không SQL chéo;
   - quyền thực tế so với khai báo;
   - route đúng chuẩn;
   - contract hợp lệ;
   - `module.json` hợp lệ;
   - readiness / nhận ổ nghe;
   - không ghi khóa vào log.

   Mỗi kiểm ghi: cách làm, thay kiểm rời rạc hiện có nào (tệp test), mức chặn phát hành.
