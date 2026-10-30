# G1a · Đặc tả phân chia CSDL (CD-027 mục 1, CD-029 mục 2a) — Codex soạn nháp, chỉ tài liệu

## Phần chung

- Bạn là worker Codex, sandbox **chỉ đọc**. **Làm ngay.**
- Câu trả lời cuối = **toàn văn tài liệu** của lát; lead lưu nguyên văn.
- **DỪNG LẬP TRÌNH** (CD-026): không SQL chạy thật, không migration, không sửa mã. SQL trong tài liệu chỉ là **minh họa**.
- **Căn cứ:**
  - TL 54 §3–§4, §9 và **§14** (thắng các mục khác: tên tiếng Việt không dấu snake_case; CSDL thật chung `D:\DU-LIEU-KE-TOAN`);
  - TL 55 §1, §10;
  - CD-017/018/019/021/026–030 trong `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md`;
  - QD-20261026-09 (ít tài nguyên: thêm dòng, không tạo bảng/cột theo từng lần) trong `docs\QUYET-DINH.md`.
- **Khảo sát G0** ở `docs\47-core\g0\`: KS-A (Core hiện có), **KS-B (CSDL + 67 migration — đầu vào chính)**, KS-C, KS-D, KS-E và biên bản RV-*.
- Khẳng định về mã hiện có phải kèm `tệp:dòng`.
- **Không viết lại cái đã đúng:** giữ tên/cấu trúc hiện có khi đã đúng quy ước, chỉ đặc tả phần chênh lệch.
- Không đọc `var\plhn-that`, `var\web-that`, `.env`, `*.local.json`; không in DSN/khóa/dữ liệu thật.

## Lát G1a-1 · `DAC-TA-CSDL.md` (thân đặc tả)

Gồm:

1. **Sơ đồ khối dữ liệu** (schema) và chủ sở hữu:
   - `loi`, `loi_tai_lieu`, `danh_muc`;
   - `mod_crm`, `mod_m2`, `mod_m4`, các `mod_*` khác KS-B nêu (M0, M1, M3, M9…);
   - `cong_bo_<module>`;
   - vùng chuyển tiếp lõi cũ (KS-B gọi `ke_toan_cu`).

   Mỗi khối ghi: nội dung, ai ghi, ai đọc, qua đâu (bảng / hàm / khung nhìn công bố). Đối chiếu bốn vùng V1–V4 của XS-5a1.
2. **Bảng tên tiếng Việt không dấu**, ba cột: tên tiếng Anh trong TL 54 / tên hiện có → tên đề xuất → lý do. Phạm vi: schema, bảng Core chính, role, cột chuẩn (`phap_nhan_id`, `row_version`, `tao_luc`…), bảng migration (`master.schema_migrations` → ?).
3. **Mô hình dữ liệu Core** (khối `loi`, `loi_tai_lieu`), mỗi bảng ghi khóa và quan hệ chính:
   - người dùng, pháp nhân (= workspace), thành viên, vai;
   - ma trận thẩm quyền (dùng lại MTQ hiện có);
   - module, phiên bản, cấp quyền;
   - **sổ cổng** (CD-028);
   - engine định nghĩa / hồ sơ chạy / phiên chạy, kèm số đo khởi động CD-028 mục 3b;
   - quy trình;
   - việc / bước / lần thử (dùng lại hàng việc XS-2);
   - sự kiện (bus);
   - nhật ký kiểm toán;
   - tài liệu, tệp, kết quả xử lý.
4. **Role PostgreSQL:**
   - mỗi khối một role chạy + một role migration;
   - role chạy không là chủ bảng, không BYPASSRLS, NOLOGIN khi phù hợp;
   - quan hệ với `app_web`, `app_doc`… hiện có;
   - hàm DEFINER: chủ, `search_path`, quyền EXECUTE;
   - thu hồi quyền PUBLIC.
5. **RLS theo pháp nhân:**
   - ngữ cảnh đặt theo transaction (`SET LOCAL`);
   - quan hệ với MTQ;
   - job/worker và tải tệp cũng qua cùng kiểm;
   - công cụ xuất riêng một công ty (CD-021).
6. **Quy tắc ghi/đọc giữa module:**
   - không SQL chéo schema;
   - ghi chung qua hàm Core;
   - đọc module khác chỉ qua `cong_bo_*`, có phiên bản contract;
   - cách kiểm tự động (test so truy cập thực với khai báo — nối tiếp XS-5c);
   - trả lời câu XS-5a2 vướng: CRM đang đếm qua `master.hop_dong`, `master.hop_dong_phien_ban`, `master.lich_thu`, `kho.lien_ket_chung_tu`. Các bảng này thuộc khối nào? Có cần khung công bố không?
7. **Migration theo gói module:**
   - số phiên bản + checksum;
   - Core chỉ giữ migration `loi*` / `danh_muc`;
   - thứ tự phụ thuộc giữa gói;
   - cách xử lý migration thay thân hàm của khối khác (★ trong KS-B);
   - nâng cấp/tắt module không mất dữ liệu.
8. **Dọn dẹp và ít tài nguyên** (QD-09): CSDL/role test tồn đọng (303 / 651); dữ liệu tạm có cách dọn.
9. **Câu cần Anh chọn:** dạng bảng phương án + khuyến nghị, tối đa 6 câu.

Tối đa khoảng 8 trang.

## Lát G1a-2 · `ANH-XA-MIGRATION.md` (phụ lục)

1. **Bảng 67 migration hiện có → gói đích** (chỉ bảng ánh xạ). Mỗi dòng gồm:
   - số / tên;
   - đối tượng;
   - khối hiện tại → khối đích;
   - gói migration đích (Core / `mod_*`);
   - đánh dấu ★ nếu chạm nhiều khối, kèm cách tách;
   - **tên đối tượng mới** nếu đổi tên.

   Lấy KS-B làm nguồn; mọi dòng KS-B ghi chưa chắc thì đọc lại mã (tệp:dòng).
2. **Thứ tự dựng** CSDL thật chung mới:
   - gói Core trước;
   - các gói module theo thứ tự G4 (M4, CRM, M2);
   - module khác sau.

   Cách nạp dữ liệu DEMO cũ (23 migration) sang cấu trúc mới chỉ ở mức nguyên tắc.
3. Danh sách **hàm/trigger** phải đổi chủ hoặc tách khi chia khối, nhóm theo khối.

Tối đa khoảng 6 trang, phần lớn là bảng.
