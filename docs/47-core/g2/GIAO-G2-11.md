# G2 · giao G2-11 — tiếp nhận, vùng tạm và hai loại biên nhận chống trùng

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `lat/g2-10` (G2-00…G2-10). Quy ước như cũ; không đặt thuộc tính test trùng tên phương thức `TestCase`.

## Lát G2-11

**Tệp:** `src\kho_tri_thuc\core\sql\011_tiep_nhan.sql`; `src\kho_tri_thuc\core\tiep_nhan.py`; `tests\test_g2_11.py`.

**Căn cứ:**
- Đặc tả CSDL §3.5 (nền tiếp nhận chung; Core sở hữu; vùng tạm chưa xác định pháp nhân kiểm bằng quyền nguồn/lần tiếp nhận) và §5;
- Chuẩn API §3.6:
  - **biên nhận module** vĩnh viễn, bất biến, trong `loi_tai_lieu.bien_nhan_thao_tac`, ghi qua hàm V2 **cùng transaction và cùng kết nối** của module; UNIQUE `(phap_nhan_id, module, operation, client_key)`; fingerprint = operation + body chuẩn hóa (không gồm path / method / khóa); kiểm quyền hành động trước khi tra biên nhận, quyền đọc kết quả trước khi phát lại;
  - **biên nhận operation Core** giữ 24 giờ, lưu **tách riêng**;
- Phiếu CSDL câu 2A (hạn giữ).
- **Mẫu K2 đang chạy:** `ha_tang\pg_migrations.py` quanh dòng 3385–3395 và `k2\crm_mau.py` (biên nhận vĩnh viễn) — đọc để giữ ngữ nghĩa.

**Việc:**
- **Bảng:**
  - lần tiếp nhận nguồn;
  - vùng tạm tin cậy;
  - `bien_nhan_thao_tac` (vĩnh viễn; trigger chặn UPDATE / DELETE);
  - biên nhận Core (có hạn 24 giờ từ kết quả cuối; giữ khi việc còn chạy / chưa rõ).
- **Hàm V2:**
  - ghi biên nhận cùng transaction;
  - tra / phát lại có kiểm quyền;
  - cùng khóa khác fingerprint → lỗi `KHOA_CHONG_TRUNG_KHAC_NOI_DUNG`.

**Test PG:**
- cùng khóa cùng nội dung → phát lại;
- khác nội dung → lỗi;
- rollback nghiệp vụ → biên nhận cũng rollback;
- biên nhận module không hết hạn, không xóa được;
- biên nhận Core hết hạn đúng 24 giờ;
- người khác không quyền đọc kết quả → 404 tương đương;
- tiếp nhận chưa có pháp nhân kiểm quyền nguồn.
