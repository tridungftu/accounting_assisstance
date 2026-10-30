# Soạn 3 chuẩn Core v1.0 (CD-034) — Codex, chỉ tài liệu

## Phần chung

- Bạn là worker Codex, sandbox **chỉ đọc**. **Làm ngay.**
- Câu trả lời cuối = **toàn văn tệp chuẩn**; lead lưu nguyên văn.
- **Người đọc** là người lập trình module mới (nội bộ hoặc AI worker): đọc là làm được, **không cần đọc phiếu hay biên bản review**.
- **Chỉ chép quyết định đã duyệt, không thêm quyết định mới.** Chỗ đặc tả còn "chờ Anh" thì ghi "chờ Anh", không tự chốt.
- **Nguồn đã duyệt:**
  - `docs\47-core\PHIEU-DUYET-CSDL.md` (Anh duyệt 1A, 2A, 3A);
  - `docs\47-core\PHIEU-DUYET-API.md` (Anh duyệt 1A, 2A);
  - đặc tả `docs\47-core\g1\DAC-TA-CSDL.md`, `ANH-XA-MIGRATION.md`, `DAC-TA-API.md` (gồm OpenAPI), `ANH-XA-ROUTE.md`;
  - `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` CD-026…CD-036.
- **Khuôn tệp:**
  1. Tiêu đề, **phiên bản v1.0**, ngày Anh duyệt (30/10/2026), căn cứ (phiếu + CD).
  2. Mục **"Thay đổi"** (v1.0: bản đầu).
  3. **Kết luận** ≤ 10 dòng.
  4. Phần **Bắt buộc** và phần **Khuyến nghị** tách rõ.
  5. Ví dụ dùng **module mẫu giả định** `mau_demo`: không dữ liệu thật, không tên công ty thật.
  6. Mục **"Module được làm / không được làm"**.
  7. **Checklist trước khi nộp gói.**
  8. Phụ lục: **trỏ tới** đặc tả chi tiết (`docs\47-core\g1\…`), không chép nguyên OpenAPI/JSON Schema.
- Tiếng Việt, tên kỹ thuật tiếng Việt không dấu. Khoảng 6–10 trang.

## Lát CHUAN-CSDL · `CHUAN-CORE-CSDL-v1.0.md`

Nội dung:
- **Khối dữ liệu:** `loi`, `loi_tai_lieu`, `danh_muc`, `mod_<ma>`, `cong_bo_<ma>`, `ke_toan_cu` (chuyển tiếp), kèm ai ghi / ai đọc / qua đâu;
- quy tắc đặt tên tiếng Việt không dấu;
- **kiểu dữ liệu:** UUID, numeric + cột đơn vị, timestamptz, `row_version`;
- cặp role chạy / đổi cấu trúc, login từng loại tiến trình, membership PG16;
- RLS theo pháp nhân + **mã phiên bí mật** (câu 1A), mã ủy nhiệm việc;
- kiểm toàn vẹn tiền dưới FORCE RLS;
- không FK chéo module: bộ ba nghĩa vụ, ghim ID + mã băm qua `cong_bo_*`;
- mã hóa cột nhóm A (qua cổng Core);
- migration trong gói module (sổ, checksum, thứ tự cài);
- dọn dữ liệu tạm theo câu 2A (nêu các hạn);
- tài khoản người dùng do Core quản (câu 3A).

## Lát CHUAN-API · `CHUAN-CORE-API-v1.0.md`

Nội dung:
- `/api/v1/` và namespace `/api/v1/module/{ma}/…` (route module phải khai báo);
- xác thực phiên, CSRF/Origin, TLS ngoài loopback;
- **lỗi chuẩn** tiếng Việt (`ma`, `thong_diep`, `request_id`, `thu_lai_duoc`, `chi_tiet`);
- **việc lâu:** 202 + `viec_id`; hủy là đề nghị; `interrupted`;
- **chống trùng:** route Core do Core giữ; `/module/*` do module giữ vĩnh viễn trong `loi_tai_lieu.bien_nhan_thao_tac`;
- `row_version` / 409; phân trang;
- tải lên **≤ 20 MB** (câu 2A); tải xuống kiểm quyền;
- **cổng Core giữ/nhả** (CD-028), module tự đóng sau **5 phút** rảnh (câu 1A); trạng thái tiến trình, chống vòng khởi động lỗi;
- thẻ liên tiến trình + mã ủy nhiệm + credential instance;
- danh sách route Core module được dùng;
- 3 ví dụ request/response;
- lớp chuyển tiếp route cũ.

## Lát ENGINE-1 · Bản giao việc engine `e_ocr`, `e_mask`, `e_hoi_ai` (CD-035, CD-036)

Viết **ba bản giao việc**, mỗi bản ≤ 1 trang, theo đúng CD-035 và CD-036. Tham khảo khảo sát `docs\47-core\g0\KS-D.md`, `KS-E.md`, `KS-A.md` và đặc tả `docs\47-core\g1\DAC-TA-SDK.md`, `CONTRACT-DU-LIEU.md`.

**Mỗi bản giao việc gồm:**
- **Mục tiêu và capability:**
  - `ocr.trich_van_ban@1`, `ocr.trich_bang@1`;
  - `mask.phat_hien@1`, `mask.che_van_ban@1`, `mask.che_tai_lieu@1`, `mask.mo_che@1`;
  - `ai.hoi@1` (Local luôn có, Cloud chỉ qua `e_mask`, cờ "chỉ Local").
- **Contract vào/ra:** lớp kỹ thuật.
- **Nguồn dùng lại chính thức (CD-036)**, có đường dẫn + `tệp:dòng`:
  - `D:\GPT\OCR\ocr-abbyy-ai` (+ `abbyy-hotfolder`, `mask_ocr`);
  - `D:\GPT\Phan mem Mask file\Mask file v2`;
  - cổng AI trong repo `src\kho_tri_thuc\tri_thuc\cong_ai.py` (AI-1/AI-2).
- **Bảng "dùng lại nguyên / bọc / sửa / viết mới"** theo từng phần, kèm lý do cho phần viết mới. Viết mới chỉ cho: adapter theo contract, khung chạy (cổng, sẵn sàng, dừng — CD-028), lớp vận hành Core.
- **Không sửa bản gốc** chưa hỏi Anh. Mask v2 nếu cần sửa thì theo `CLAUDE.md` của Mask v2.
- **Tài khoản hạn chế (CD-033).** ABBYY cần tài khoản riêng → ghi **ngoại lệ, hỏi Anh**.
- **Test gốc của nguồn phải đạt khi chạy qua engine** (dữ liệu giả).
- **Chia lát nhỏ** ≤ 3 tệp, Codex làm chính, thứ tự lát.
- Không gọi Cloud trực tiếp; không che tiền/ngày.

## Lát ENGINE-2 · Bản giao việc engine `e_trich_xuat`, `e_hoa_don` (CD-035, CD-036)

Khuôn như ENGINE-1.

**Nguồn:**
- `D:\Claude\Ho tro review ho so xay dung\review_xaydung` (phần `trich_xuat`, 37 tham số, Local AI). **Đóng băng (CD-011): chỉ bọc, không sửa**;
- danh mục theo loại E1-MUA;
- `D:\Claude\Phan mem download hoa don` + `src\kho_tri_thuc\nguon\hoa_don_xml.py` (đọc XML/ZIP thành contract `hoa_don`).

**Capability:**
- `trich.tham_so_hop_dong@1`, `trich.bang@1`;
- `hoa_don.tai_cong_thue@1`, `hoa_don.doc_xml@1`, `hoa_don.doc_zip_bang_ke@1`.

**Gọi cổng thuế thật** chỉ khi Anh ra lệnh riêng: mặc định chỉ chạy với tệp mẫu.

**Không mở** `co_so_du_lieu\*.db` của review.
