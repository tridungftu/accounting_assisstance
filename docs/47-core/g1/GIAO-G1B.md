# G1b · Đặc tả bộ API (CD-027 mục 1, CD-028, CD-029 mục 2b) — Codex soạn nháp, chỉ tài liệu

## Phần chung

Giống `docs\47-core\g1\GIAO-G1A.md` phần chung:
- chỉ đọc;
- câu trả lời cuối là toàn văn tài liệu;
- dừng lập trình;
- khẳng định có `tệp:dòng`;
- tên tiếng Việt không dấu;
- không lộ dữ liệu cấm.

**Đầu vào chính:**
- `docs\47-core\g0\KS-C.md` (route hiện có), cùng KS-A, KS-D, KS-E;
- TL 54 §6, §8, §9;
- TL 55 §2, §10;
- CD-028 (Core giữ cổng, nhả cho engine/module; mỗi module một tiến trình).

Phân chia CSDL đang được soạn song song (`DAC-TA-CSDL.md`). Chỗ API phụ thuộc tên khối dữ liệu thì dùng tên nháp TL 55 và ghi "theo phiếu CSDL".

## Lát G1b-1 · `DAC-TA-API.md` (thân) + `openapi-v1.yaml` (phụ lục trong cùng câu trả lời, khối ```yaml)

1. **Quy ước chung:**
   - tiền tố `/api/v1/`;
   - phiên và xác thực, Origin/CSRF;
   - ngữ cảnh pháp nhân (đặt ở đâu, Core kiểm lại ở backend cho cả API, tải xuống, việc nền);
   - **dạng lỗi** `{ma, thong_diep, request_id, thu_lai_duoc}` (thông điệp tiếng Việt, không lộ khóa) và bảng mã HTTP;
   - **khóa chống trùng** (header, phạm vi, thời hạn);
   - `row_version` → 409;
   - phân trang;
   - việc lâu: **202 + `viec_id`**, theo dõi `/api/v1/viec/{id}`, hủy = đề nghị;
   - tải lên/tải xuống tệp;
   - phiên bản API;
   - ngày giờ, tiền + đơn vị;
   - JSON Schema cho mọi đầu vào/đầu ra.
2. **Danh sách route theo nhóm:**
   - Core: `phien`, `toi`, `phap-nhan`, `tai-lieu`, `tep`, `ket-qua`, `module`, `engine`, `quy-trinh`, `viec`, `quan-tri/module`, `quan-tri/engine`, `quan-tri/cap-quyen`, `/healthz`, `/readyz`;
   - nghiệp vụ `/api/v1/module/{ma_module}/...`.

   Mỗi route ghi: method · đường dẫn · mục đích · quyền · đồng bộ hay 202.
3. **Chuyển tiếp tới tiến trình module/engine (CD-028):**
   - **API Dispatcher** chuyển `/api/v1/module/{ma}/…` tới cổng nội bộ;
   - truyền danh tính/pháp nhân/request_id sang tiến trình module (ký hay tin cậy cục bộ? → câu chốt);
   - module chưa chạy → Core khởi động, chuyển ổ nghe, chờ readiness, rồi phục vụ;
   - thời gian chờ tối đa và lỗi trả về.
4. **API quản trị engine/module:**
   - trạng thái `stopped/starting/ready/busy/failed`;
   - số đo khởi động và đề xuất chế độ chạy hằng tuần (CD-028 mục 3b, Admin bấm áp dụng).
5. **Ví dụ request/response đầy đủ** cho 3 route tiêu biểu:
   - một route Core đồng bộ;
   - một việc lâu 202 (ví dụ OCR một tài liệu);
   - một route module có `row_version` (ví dụ lưu báo giá CRM).
6. **Câu cần Anh chọn:** bảng phương án + khuyến nghị, tối đa 6 câu.

Thân ≤ 8 trang; OpenAPI ở cuối, có thể dài.

## Lát G1b-2 · `ANH-XA-ROUTE.md` (phụ lục)

1. **Bảng route cũ → route mới.**
   - Nguồn: mọi route trong KS-C, gộp nhóm cùng mẫu.
   - Mỗi dòng: route cũ · tệp:dòng · module chủ · route `/api/v1/` mới · thay đổi hợp đồng (nếu có) · giữ chuyển tiếp tạm hay bỏ.
2. Route **vi phạm** nguyên tắc (KS-C mục 4): cách sửa trong route mới.
3. Nguyên tắc **lớp chuyển tiếp** route cũ và điều kiện gỡ.
