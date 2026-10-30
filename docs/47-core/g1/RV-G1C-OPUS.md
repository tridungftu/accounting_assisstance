# Review Opus — G1c (contract SDK cốt lõi), vòng 1 (30/10/2026)

**Kết luận: Chặn. Có 3 điểm Chặn** (1 trùng RV-G1C, 2 mới); chưa gửi Anh. Bốn điểm Cần sửa của RV-G1C giữ nguyên:
- schema manifest;
- `dau_ra` việc lâu;
- `chi_tiet` lỗi;
- câu M4.

S = `docs\47-core\g1\DAC-TA-SDK.md`, D = `docs\47-core\g1\CONTRACT-DU-LIEU.md`.

| # | Kết luận | Lý do, chỗ sửa |
|---|---|---|
| 1 Ranh giới SDK, rò rỉ | **Chặn** | (a) Module giữ login `dang_nhap_mod_x` nên gọi thẳng psycopg là bỏ qua được SDK. Ranh giới thật là role + RLS + Core. Ghi rõ SDK không phải ranh giới an ninh (S:56 "truy vấn ngoài đăng ký: 403").<br>(b) **Tài khoản Windows của tiến trình con chưa quy định.** Bí mật và khóa cột bọc DPAPI theo tài khoản dịch vụ (CSDL:267, :345). Module/engine chạy cùng tài khoản Core thì đọc được `D:\DU-LIEU-KE-TOAN\bi-mat\` (mật khẩu mọi login, khóa cột) và bộ nhớ Core; "engine không login CSDL" khi đó chỉ trên giấy.<br>(c) **Thiếu dịch vụ mã hóa cột.** CSDL:345, ANH-XA-MIGRATION:189 giao lát API/SDK chốt nhưng chưa có. Module có cột nhóm A không ghi/tra HMAC/hiện 4 số cuối được mà không tự chép mã mã hóa (trái CD-019).<br>(d) SDK chưa có hàm nhận request kiểm token theo API:216–218 (chữ ký, đúng instance, TTL 30 giây, nonce một lần, hash method/path/body). Module nghe loopback nên tiến trình cục bộ gọi thẳng được.<br>(e) `uy_nhiem_viec(ctx, viec_id)` (S:52) nhận ngữ cảnh request, dễ xin ủy nhiệm rồi giữ cho việc nền. Core cấp ủy nhiệm theo việc + thế hệ lease khi nhận việc → chuyển vào `GiuViec` (API:135, :220).<br>(f) `ket_qua.ghi(..., nguon: dict)` (S:55) cho bên gọi tự khai nguồn, giả được kết quả OCR. Nguồn engine/việc do Core tự gắn.<br>Thêm: không dựng DSN chuỗi có mật khẩu; truyền `password=` riêng. |
| 2 Khung tiến trình | Cần sửa | Core bind với `SO_EXCLUSIVEADDRUSE`, không thì `SO_REUSEADDR` cướp được cổng.<br>(i) "Không gì luôn chạy" chỉ đánh thức bằng HTTP; việc `queued`/sự kiện bus cho module đang tắt không ai đánh thức (S:58, :61). Core kích hoạt khi có việc/sự kiện chờ. "Rảnh" = không request, không lease, hộp nhận rỗng.<br>(ii) Readiness kiểm login CSDL và `phien_ban_du_lieu` khớp `loi.lich_su_doi_cau_truc`; lệch thì không báo sẵn sàng.<br>(iii) Job Windows `KILL_ON_JOB_CLOSE`; RAM/CPU do Core đo bằng Job accounting, không tin module tự báo. |
| 3 `module.json` | Cần sửa | Chưa cài được M4 qua giao diện mà không sửa Core. Manifest thiếu:<br>• khai báo hàm Core gọi sang module (`loi.dang_ky_ham_module`: resolver MTQ, kiểm nghĩa vụ — CSDL:287, §7);<br>• vùng V3 đọc danh mục (`ham_core_dung` đang lẫn đọc/ghi V2; đủ 4 loại CD-017);<br>• cột mã hóa nhóm A.<br>Bỏ trường hoặc đặt `const` cho `tien_trinh.cong`. Core tự suy, gói không được khai:<br>• `goi_migration.vai` (lỗ leo quyền);<br>• `schema` = `mod_<ma>`;<br>• `cong_bo[].doi_tuong` thuộc `cong_bo_<ma>`.<br>Mã quyền có tiền tố mã module (S:198 lệch S:249). Engine manifest khai kết nối ngoài (mặc định rỗng). |
| 4 Contract | Cần sửa | Tiền, ngày: đạt.<br>**Phiên bản mâu thuẫn:**<br>• `vo_noi_dung.phien_ban` const "1.0.0" trong `chung.v1` dùng chung (D:131) → nâng một contract phá cả bảy;<br>• D:44 cấm đổi dưới cùng `$id`, còn `unevaluatedProperties:false` khiến thêm trường cũng bị bên nhận cũ từ chối.<br>Một quy tắc: hằng phiên bản riêng từng contract; mọi thay đổi tạo `$id` mới; bên phát trả bản bên nhận đã ghim trong manifest.<br>**`tra_loi_ai.v1`:** `duong: CLOUD` vẫn hợp lệ khi không có lượt che và `mo_che: khong_ap_dung`. Có CLOUD thì bắt buộc `luot_che_id` và `mo_che` ∈ {`dat`, `khong_dat`}. `truong.gia_tri` cần có kiểu (tiền "1.000.000" dễ đọc thành 1,0).<br>**`noi_dung_da_che.v1`:** thêm quy tắc và ca kiểm "không che tiền/ngày".<br>**`hoa_don.v1`:**<br>• thêm thuế suất dòng (`TSuat`, `hoa_don_xml.py:45`);<br>• `truoc_thue` = `TgTCThue` gồm cả phần không chịu thuế (:459) → cấm dùng làm cơ sở chịu thuế;<br>• `dong[].tien_chuan` không mang dấu → không cộng dòng (chiết khấu TChat=3) ra tổng, tổng lấy `tong_tien`. |
| 5 Bộ kiểm tuân thủ | Cần sửa (nhỏ) | Chạy lại KT01/KT03 mỗi lần kích hoạt và mỗi lần Core khởi động; lệch quyền (GRANT tay) → module về chưa kích hoạt.<br>Thêm ca:<br>• tiến trình con mở `bi-mat`/đọc bộ nhớ Core phải thất bại;<br>• cổng bị bind lại;<br>• gọi thẳng cổng module không token bị từ chối;<br>• KT09 quét log PostgreSQL và kiểm `log_parameter_max_length*=0`;<br>• tiền/ngày không bị che;<br>• `tra_loi_ai` CLOUD không lượt che = C0. |
| 6 Câu cho Anh | Cần sửa | Câu 1 (S:349) nhầm hai việc:<br>• M4 = module mẫu đầu tiên G4 đã chốt (TL 55 §6, CD-027) → dòng báo;<br>• câu cần hỏi là **module thử Core ở G2** (CD-026 mục 3).<br>Phương án C "thêm logic khoản vay" trái CD-015. Câu 2 (retention OCR) trùng phiếu CSDL câu 2 → bỏ. Thiếu câu tài khoản Windows. |

## Ưu tiên sửa

- **Chặn 1 (trùng RV-G1C):** module giữ biên nhận chống trùng vĩnh viễn, cùng transaction (S:118, :343). Lưu vào `loi_tai_lieu.bien_nhan_thao_tac` qua hàm V2, khớp DAC-TA-API §2.4 vòng 2.
- **Chặn 2:** mục "Danh tính hệ điều hành" ở S §4:
  - tiến trình con chạy bằng token hạn chế suy từ token Core (`CreateProcessAsUser`, không cần thêm đặc quyền);
  - ACL `bi-mat` chỉ tài khoản Core;
  - chặn đọc bộ nhớ Core;
  - thử ở G2 cùng CD-028 mục 6.

  Hoặc ghi mô hình đe dọa chấp nhận và hỏi Anh.
- **Chặn 3:** dịch vụ thứ 12 `ma_hoa` qua cổng Core (`ma_hoa`, `tra_hmac`, `hien_thi_rut_gon`, giải mã có quyền + audit); khai cột nhóm A trong `module.json`.
- **Cần sửa theo thứ tự:**
  1. hàm nhận request kiểm token/nonce;
  2. đánh thức khi có việc/sự kiện chờ + ủy nhiệm việc theo lease;
  3. `module.json` (hàm Core gọi module, V3, tách đọc/ghi, trường Core tự suy, tiền tố quyền);
  4. quy tắc phiên bản contract;
  5. `tra_loi_ai` gắn CLOUD với lượt che; `noi_dung_da_che` giữ tiền/ngày;
  6. `hoa_don` (thuế suất dòng, nghĩa `truoc_thue`, dấu chiết khấu);
  7. readiness kiểm phiên bản dữ liệu, `SO_EXCLUSIVEADDRUSE`, Job accounting;
  8. nguồn kết quả do Core gắn, không DSN chuỗi, kiểm lại khi kích hoạt;
  9. câu cho Anh.

## Ba câu đề xuất cho phiếu SDK

| Câu | Phương án | Khuyến nghị |
|---|---|---|
| 1. **Module thử Core ở G2** (khác M4 mẫu G4 đã chốt) | A. Tra cứu tài liệu DEMO<br>B. M9 theo phạm vi CD-015<br>C. Không có, thử thẳng bằng M4 ở G4 | **A**: nhỏ, đi qua đủ tệp, OCR, việc lâu, công bố, cài/tắt; không dữ liệu thật |
| 2. **Tài khoản Windows của tiến trình module/engine** | A. Token hạn chế/tài khoản riêng, không đọc được `bi-mat`<br>B. Cùng tài khoản Core; tách login chỉ chống nhầm lẫn | **A** (tốn công lập ACL, thử ở G2) |
| 3. **Có việc/sự kiện chờ cho module đang tắt** | A. Core khởi động ngay<br>B. Gom theo lịch (15 phút)<br>C. Chỉ khi người dùng mở màn | **A** mặc định; Admin đổi theo số đo (CD-028 mục 3b) |
