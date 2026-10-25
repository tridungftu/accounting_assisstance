# M2c — M2-00 · Nhận nguồn từ cổng thuế: nhận hóa đơn theo manifest (intake)

Bạn là worker Codex, chạy không tương tác (`codex exec`). Anh đã chốt thiết kế (20/10) và ra lệnh code (24/10) qua lead: **làm ngay đến hết, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM, giữ dấu tiếng Việt.
**Thư mục:** worktree hiện tại, nhánh `lat/m2c` (từ `hop-nhat-20261023`, đã có M2b). Sandbox không ghi `.git`: **không commit** — lead commit. Nếu sandbox không cho chạy Python, ghi rõ trong báo cáo (lead sẽ chạy test).

**Căn cứ:** `D:\Claude\Phan mem ho tro ke toan\THIET-KE-MODULE-DE-CHOT-2026-10-20\M2-00-NHAN-NGUON-TU-CONG-THUE.md` §6 (quy tắc nhận theo manifest — đọc kỹ từng gạch đầu dòng), §8 ca M2-00-03 (phần nhận: không nhân đôi, revision), -04 (KHONG_XML_GOC → BANG_KE), -05 (lỗi tải → ngoại lệ), -10 (file ngoài manifest); `docs/GIAO-CODE-M2-00-TAI-HOA-DON-TRONG-M2.md` §5 (identity 6 phần = `key_canonical` + pháp nhân từ profile + chiều từ thư mục) và §6 (3 ràng buộc).
**Dùng lại nguyên (không viết lại):**
- `src/kho_tri_thuc/m2/tai_hoa_don/manifest.py` (M2b): `doc_manifest`, `phan_loai_file_tren_dia`, kết quả có `hoa_don_du_khoa`, `hoa_don_thieu_khoa`.
- `src/kho_tri_thuc/m2/tai_hoa_don/chinh_sach_tien_te.py` (M2b): `ap_dung` — policy POLICY-TIENTE-01 v1.
- `src/kho_tri_thuc/nguon/hoa_don_xml.py`: đọc XML (`doc_hoa_don_xml`, `InvoiceReadContext`, `XmlRawRef`…) và identity binding hiện có.
- `src/kho_tri_thuc/k2/hoa_don.py`: lớp `HoaDonK2` (~dòng 75) — đường nhận vào K2 đã có qua hàm CSDL `kho.m2_tieu_thu_quan_sat` (~dòng 424): danh tính / phiên bản / quan sát, chống nhân đôi. **M2c phải đi qua đường này**, không tạo bảng/hàm SQL mới.

**Viết mới:** `src/kho_tri_thuc/m2/tai_hoa_don/nhan.py`:
1. `lap_ke_hoach_nhan(thu_muc_run, *, ma_phap_nhan, ...)` — thuần (không CSDL): đọc manifest (M2b) → với mỗi hóa đơn đủ khóa: đọc XML bằng `nguon/hoa_don_xml.py`, identity 6 phần, áp policy tiền tệ (M2b) khi XML không có `DVTTe`, mức bằng chứng (`XML` hoặc `BANG_KE` khi `xml_status = KHONG_XML_GOC` — không phải lỗi), quan hệ điều chỉnh/thay thế nếu XML có `TTHDLQuan`/`TCHDon` (chỉ ghi quan hệ có căn cứ, không gộp số tiền); `xml_status = LOI` → ngoại lệ "tải lỗi"; hóa đơn thiếu khóa → ngoại lệ; file ngoài manifest → "chưa rõ nguồn", **không vào đề xuất**. `tthai_cong` lưu nguyên giá trị, không diễn giải.
2. `nhan_vao_k2(ke_hoach, hoa_don_k2: HoaDonK2, ...)` — gọi đúng API nhận của `HoaDonK2` hiện có cho từng mục; cùng key + cùng hash → không nhân đôi (thêm quan sát); cùng key + khác hash hoặc khác `tthai_cong` → revision/xung đột để người kiểm — **theo cơ chế sẵn có của `kho.m2_tieu_thu_quan_sat`**; nếu cơ chế sẵn có không làm được điều nào trong §6 thì KHÔNG tự thêm SQL — ghi rõ khoảng thiếu vào báo cáo.
3. Không ghi mật khẩu/credential vào log, nhật ký, kết quả (ràng buộc 3).
**Test mới:** `tests/test_m2_00_nhan_tinh.py` — dữ liệu DEMO tự tạo trong thư mục tạm (MST giả `0000000001`…, tên có `DEMO`; có thể dùng/sao chép mẫu XML DEMO trong `tests/fixtures/m2_invoice_xml/inputs/`), phủ: M2-00-03 (chạy 2 lần cùng manifest → số mục/kết quả không đổi; hai run khác hash cùng key → revision), -04, -05, -10, hóa đơn thiếu khóa → ngoại lệ, credential không xuất hiện trong kết quả. Phần `nhan_vao_k2` test bằng kết nối giả (theo cách các test K2 hiện có làm) hoặc skip có lý do khi không có PostgreSQL.
**File được sửa/tạo (≤ 4):** `src/kho_tri_thuc/m2/tai_hoa_don/nhan.py` (mới), `tests/test_m2_00_nhan_tinh.py` (mới); `k2/hoa_don.py` CHỈ khi cần một hàm mỏng công khai để gọi đường nhận sẵn có (ghi lý do); không sửa SQL/migration.
**Test phải đạt:** `python -X utf8 tools/chay_test_theo_module.py . --module test_m2_00_nhan_tinh --module "test_m2_00*" --module test_m2_k2 --module test_hoa_don_xml` — không mã lỗi mới so với `docs/46-chuyen-doi-dieu-phoi/nen-test-hop-nhat-v2.json`.
**Không làm:** `hoi_cuu.py` (M2d), route/giao diện (M2e), sửa JS #7, schema/migration, gọi cổng thuế, đọc `var/`, `.env`, `cau_hinh.*.toml`, dữ liệu thật; xóa file.

**Báo cáo cuối (≤ 1 trang, tiếng Việt):** Đã làm · File (kèm thông điệp commit `[M2c] …`) · Test đạt/tổng · Ca M2-00-03/-04/-05/-10 + 3 ràng buộc: đã phủ / còn thiếu · Khoảng thiếu của đường nhận K2 sẵn có so với §6 (nếu có) · Rủi ro.
