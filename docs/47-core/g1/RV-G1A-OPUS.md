# Review Opus — DAC-TA-CSDL.md (G1a), vòng 1 (30/10/2026)

**Kết luận: chưa gửi Anh được — 3 điểm Chặn** (cả ba làm vỡ việc dựng CSDL thật mới từ đầu hoặc làm sai kiểm tiền). Khung đúng hướng:
- tên tiếng Việt;
- cặp role;
- FORCE RLS;
- ngữ cảnh đặt theo transaction;
- contract công bố;
- ★ tách theo định nghĩa cuối.

Ký hiệu: `P` = `src\kho_tri_thuc\ha_tang\pg_migrations.py`, `K/` = `src\kho_tri_thuc\k2\`.

| # | Kết luận | Lý do | Sửa |
|---|---|---|---|
| 1 Ranh giới, XS-5a2 | **Chặn** | `hop_dong`, `hop_dong_phien_ban`, `lich_thu`: chia hợp lý (§6.2). Riêng `kho.lien_ket_chung_tu` → `danh_muc` là sai, vì bảng này mang FK và trigger sang module:<br>• FK `lich_thu_id`/`hop_dong_id` tới CRM (P:1018–1020);<br>• FK `chung_tu_a/b` tới `ke_toan_cu` (P:550–553);<br>• trigger `lien_ket_kiem` khóa `lich_thu`, đọc `hop_dong_phien_ban` (P:1049–1085);<br>• `lien_ket_phan_bo` FK tới `lich_tra_no` M9 (P:2700).<br>Điều này trái §6.1/§7. Ngoài ra `chung_tu` do CRM, M9, M5, M2 cùng ghi (`K/crm.py:262`, `K/vay.py:551`, P:4205, P:5970) nhưng lại xếp vào `ke_toan_cu` "chỉ adapter cũ", mâu thuẫn §1.1. | C1 |
| 2 Role, DEFINER, PUBLIC | **Cần sửa** | Cặp role chạy/đổi cấu trúc, không BYPASSRLS, `search_path` cố định, thu hồi PUBLIC: đạt. Còn thiếu:<br>• mỗi tiến trình (Core, module, engine, máy phụ, cài đặt) đăng nhập bằng login nào;<br>• ai giữ mật khẩu và trao bằng cách nào;<br>• membership PG16 `SET FALSE`;<br>• cách Core gọi resolver module mà không leo quyền. | S2, S4 |
| 3 RLS pháp nhân | **Chặn** | Tính tổng dưới FORCE RLS sẽ sai:<br>• §4.2 bắt FORCE RLS;<br>• nhưng kiểm chống vượt tiền hiện dựa vào hàm DEFINER chủ bảng bỏ qua RLS ("bỏ qua RLS để mọi người tính cùng một số", P:1270), và policy lọc theo module `ktt_duoc(pn,'M1')` (P:1186);<br>• khi bật FORCE, tổng chỉ gồm dòng người gọi thấy → có thể vượt nghĩa vụ mà không ai biết.<br>Thêm:<br>• xuất một công ty chưa chỉ định role;<br>• chưa nói rõ RLS chỉ lọc pháp nhân, quyết định hành động chỉ do MTQ → hai nguồn quyền. | C2, S5 |
| 4 Đọc chéo qua `cong_bo_*` | **Chặn** | FK chéo module hiện có:<br>• M4 có FK tới bảng hóa đơn M2 (`K/sql_ghi_nhan_chung.py:252`, `:285–307`);<br>• M3 có FK tới hóa đơn M2 và `hop_dong_phien_ban` CRM (`K/sql_m3.py:36`, `:81–85`).<br>§6.1 chưa có quy tắc thay FK này. Kiểm tự động §6.3 khả thi, nhưng cổng chính nên là so ACL thực (kèm đối tượng mỗi hàm DEFINER chạm tới); trace là phụ. | C3; §6.3 đổi thứ tự |
| 5 Migration theo gói | **Chặn** (hệ quả C1, C3) + Cần sửa | Thứ tự cài vỡ vì FK chéo:<br>• §7 cài M4 trước M2, nhưng FK M4 → M2 không tạo được;<br>• Core trước CRM/M9 thì FK của `lien_ket` không tạo được.<br>Resolver MTQ cần gọi động qua registry (S4). Thứ tự Core §7 bước 2 lệch phụ lục §2 bước 1 (audit và registry module phải trước MTQ). | Theo C1, C3, S4 |
| 6 Ít tài nguyên, tên | **Đạt** (ghi chú) | Không có bảng/cột theo lần. Tên còn tiếng Anh chưa vào §2: `link_purpose`, `allocation_model`, `amount_minor`, `logical_target_id`, `basis_revision_sha256`, `entry_dm`. Dễ nhầm:<br>• `lan_thu` với `lich_thu`;<br>• `loi` đọc thành "lỗi" (đã có cột `loi` ở `hop_dong_tham_so`) → cân nhắc `cot_loi`. | Để sau |
| 7 §9 câu hỏi Anh | **Cần sửa** | • Câu 1 gần như đã chốt (TL 55 §1; CD-018) → chuyển thành "báo".<br>• Câu 4 gộp vào câu 3 (QD-09 đã chốt nguyên tắc).<br>• Thiếu câu về mô hình tin cậy module (S1).<br>• Câu 2, câu 5 giữ. | Xem câu chốt |

## Chặn

- **C1 – Chứng từ và liên kết tiền.**
  - Đầu chứng từ (pháp nhân, loại, khóa nguồn, số tiền, tiền tệ, module chủ) đưa vào `danh_muc`, ghi qua hàm V2.
  - `ke_toan_cu` chỉ giữ dòng chứng từ, đề xuất, lô xuất.
  - Liên kết vẫn ở Core (CD-018), nhưng trỏ tới đối tượng nghĩa vụ bằng bộ (module, loại, id), **không FK**.
  - Core chỉ kiểm "không vượt tiền chứng từ" và giữ khóa trên chứng từ.
  - Kiểm "không vượt nghĩa vụ" chuyển về module chủ (CRM "thu tiền đã nối", M9), chạy trong cùng transaction.
- **C2 – FORCE RLS và kiểm tiền.**
  - Ghi rõ cơ chế cho hàm kiểm toàn vẹn: policy riêng cho role chủ/kiểm, chỉ lọc pháp nhân trong ngữ cảnh, không lọc theo module/người.
  - Test âm: người không có quyền M1 không làm vượt nghĩa vụ hay vượt tiền chứng từ được.
- **C3 – FK giữa module.**
  - Định danh hóa đơn (`hoa_don_danh_tinh`) nâng lên `danh_muc`: FK từ module vào Core được phép.
  - Phiên bản, quan sát, dòng hóa đơn: ghim bằng (id + mã băm), kiểm qua `cong_bo_m2` lúc ghi.
  - M3 → phiên bản CRM cũng vậy, qua `cong_bo_crm`.

## Cần sửa

- **S1 – Giả danh qua GUC.**
  - Vấn đề: `ktt.nguoi_dung_id` và `ktt.nguoi_dung_dang_nhap` không bí mật (P:1222–1227). Với CD-028, tiến trình có login tự đặt được danh tính bất kỳ.
  - Đề xuất: Core trao mã phiên bí mật; hàm DEFINER băm và đối chiếu `loi.phien_xac_thuc` (còn hạn, đúng module và pháp nhân); việc nền dùng mã ủy nhiệm theo việc.
  - `ktt.ngay_hieu_luc` (P:1245) không để module tự đặt khi chạy thật.
- **S2 – Bảng login.**
  - **Core:** một login, thuộc ba role chạy `loi*`/`danh_muc`.
  - **Mỗi module:** một login, chỉ có `vai_chay_mod_x`, quyền đọc công bố được cấp và EXECUTE hàm Core.
  - **Engine và máy phụ:** không login CSDL, chỉ đi qua API Core.
  - **Cài đặt:** login riêng, chỉ trong phiên bảo trì.
  - **Mật khẩu:** để ngoài thư mục phần mềm (CD-019); Core trao cho tiến trình con qua stdin/handle, không qua biến môi trường hay dòng lệnh.
  - **Membership:** `INHERIT TRUE, SET FALSE, ADMIN FALSE`.
- **S3 – Mặt công bố.**
  - View `cong_bo_*` dùng `security_barrier`, không `security_invoker`.
  - Chủ view là role chỉ SELECT, không phải chủ bảng nguồn.
  - Policy bảng nguồn có nhánh cho role này, vẫn kiểm danh tính.
  - Bỏ `vai_chay_cong_bo_*` nếu không có tiến trình chạy bằng nó.
- **S4 – Core gọi module.**
  - Resolver MTQ và kiểm nghĩa vụ gọi qua registry (gọi động).
  - Hàm resolver là DEFINER do role module sở hữu; nếu INVOKER sẽ chạy với quyền chủ Core.
  - Module chưa cài → `CHO`.
- **S5 – Xuất một công ty (CD-021).**
  - Role xuất: NOLOGIN, SELECT theo bản đồ sở hữu, không BYPASSRLS, FORCE RLS với pháp nhân cố định, có audit.
  - Nêu cách xử lý đối tượng thuộc nhiều pháp nhân (QD-10).
- **S6 – Tiếp nhận M0.** Mâu thuẫn: §1.1 để `mod_m0` giữ "lần tiếp nhận, vùng tạm", còn phụ lục (M0013/14/16) đưa lên Core. Nên chốt Core.
- **S7 – Mã hóa cột.** Thêm phần còn thiếu (CD-019 mục 4, QD-20261026-11 đã duyệt cột nhóm A):
  - cột nằm ở khối nào;
  - role nào được giải mã;
  - khóa không truyền qua GUC/tham số SQL (bị ghi log).

## Để sau

- Thứ tự Core §7 (audit và registry module trước MTQ).
- Tên ở mục 6.
- pgcrypto ở schema riêng.

## Câu chốt nên đưa vào phiếu (tối đa 3)

1. **Module chạy tiến trình riêng: CSDL có phải chặn cả trường hợp một module tự nhận là người khác?**
   - A (khuyến nghị): có. Core cấp mã phiên, CSDL kiểm; G2 tốn thêm ít công.
   - B: coi module nội bộ là tin cậy (TL 54 §4.2); CSDL chỉ chặn sai pháp nhân.
2. **Hạn giữ dữ liệu tạm và tài nguyên test** (gộp câu 3 + 4).
3. **Danh tính đăng nhập thật** (câu 5).
   - Câu 1 chuyển thành dòng "báo".
   - Câu 2 (ánh xạ mở che) chuyển sang phiếu engine/SDK hoặc giữ dạng "báo".

Vòng 2 (nếu có) chỉ xem C1–C3.
