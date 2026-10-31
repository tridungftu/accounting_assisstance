# Review Opus G2-25 — Kết luận: Cần sửa, **1 Chặn** (31/10 ~12:00)

Nhánh `lat/g2-25`. PG: G2-25 + 11 bộ liên quan 355 ok / 0 lỗi.

| Mức | Phát hiện | Tệp:dòng | Xử lý |
|---|---|---|---|
| **Chặn** | **Gói leo quyền superuser:** `loi.ap_goi` SECURITY DEFINER do **superuser** sở hữu (trái CSDL §3.10). Migration của gói chạy `SET search_path = mod_x, pg_catalog` (SET thường vẫn hiệu lực sau khi hàm con thoát) và tạo hàm / toán tử / view "bóng" (`mod_x.pg_get_userbyid` …). Các lệnh sau dòng 182 của `ap_goi` dò tên theo đường tìm đã đổi → mã module chạy dưới superuser. G2-24 không kiểm nội dung SQL. | 025:75-77, 176-180, 182-289 | v6 |
| Cần sửa | Kích hoạt chỉ đăng ký contract `cong_bo`; **không** đăng ký `su_kien_phat`, `su_kien_nhan` (subscription), `dung_contract` / `dau_vao_nguon`; 025 lại thu hồi `ghi_dang_ky` / `su_kien_dang_ky_nhan` khỏi login cài đặt → module mới không có đường nhận sự kiện / khai contract / đăng ký engine (ngoài DML superuser). Cần xong trước CR7. | 025:335-339; kich_hoat.py:82 | v6 |
| Cần sửa | Login cài đặt còn EXECUTE `loi.so_cong_tao_ho_so`, `loi.demo_gan_rao_chan(regclass)` (bảng bất kỳ), `doc_dang_ky` — trái CSDL §3.5.3 mục 2. Thêm test liệt kê toàn bộ quyền EXECUTE / USAGE của `dang_nhap_cai_dat` so với danh sách cho phép. | 016:475; 023:215; test:460-469 | v6 |
| Nên sửa | Hàm tạm `loi.ap_<id>()` chứa toàn văn migration, owner module, nằm vĩnh viễn trong `loi`. | 025:174-180 | v6 — lead cho phép DROP **chính hàm tạm vừa tạo trong cùng giao dịch** (đối tượng tạm của giao dịch, không phải dữ liệu); hoặc đặt ngoài `loi` |
| Nên sửa | Hậu kiểm quyền chỉ REVOKE PUBLIC / login cài đặt; migration có thể GRANT bảng module cho vai module khác / `dang_nhap_loi`. Kiểm ACL chỉ gồm owner / chạy / kiểm / `vai_kiem_demo` / `vai_doi_cau_truc_loi`. | 025:191-196, 215 | v6 |
| Để sau | Nâng cấp từ chối khi còn việc; việc mới liên tục có thể chặn mãi → quy trình: Admin chuyển TAT trước (G2-31b). | 025:106-111 | G2-31b |
| Để sau | Kiểm vai cấm mọi membership `vai_chay_mod_<ma>` (sau này cấp đọc công bố bằng membership sẽ vướng); chưa kiểm lại `tgenabled='O'` của `aaa_demo_lien_ket` sau migration nâng cấp. | 025:123-129, 200-202 | Ghi nợ |

**Đạt:**
- Thử → Dùng / Tắt qua CAS + audit; Tắt giữ dữ liệu;
- lỗi mọi bước rollback + trả tệp về staging; mất phản hồi COMMIT có xử lý;
- nợ (a) / (b) / (c) đạt;
- không sửa 001–024;
- fixture owner không xanh giả.
