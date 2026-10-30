# G2 · giao G2-03 — phiên bí mật và mã ủy nhiệm được CSDL xác minh (rủi ro cao, Opus review bắt buộc)

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `lat/g2-02` (đã có G2-00, G2-01, G2-02). Dùng lại cách viết SQL/test của `001_vai.sql`, `002_danh_tinh.sql` (tiền tố vai test, login thật, không DROP ROLE).

## Lát G2-03

**Tệp:** `src\kho_tri_thuc\core\sql\003_phien.sql`; `src\kho_tri_thuc\core\phien.py`; `tests\test_g2_03.py`.

**Căn cứ:**
- Phiếu CSDL câu 1A: Core cấp mã phiên bí mật, CSDL tự kiểm.
- Chuẩn CSDL §3.6.
- Đặc tả CSDL §3.1, §5 kèm bổ sung (b):
  - mã đặt bằng tham số bind;
  - không lưu kết quả xác minh vào GUC/bảng tạm runtime ghi được;
  - mỗi lần cần thì xác minh lại từ băm, hàm STABLE tra có chỉ mục.
- Chuẩn API §3.11 (mã ủy nhiệm, thế hệ lease).

**Việc:**
- **Bảng `loi.phien_xac_thuc`:**
  - chỉ lưu **băm** mã (không lưu mã gốc);
  - gắn người dùng, module, pháp nhân, phạm vi hành động, `session_user` / login được ủy nhiệm, hạn, thời điểm thu hồi;
  - loại: phiên người dùng / ủy nhiệm việc (`viec_id` + thế hệ).
  - Runtime **không** SELECT/DML bảng này; chỉ qua hàm.
- **Hàm DEFINER** (owner `vai_doi_cau_truc_loi`, `search_path` cố định):
  - cấp phiên/ủy nhiệm: chỉ cho chức trách Core;
  - thu hồi;
  - xác minh: STABLE; nhận mã qua tham số; đối chiếu băm + `session_user` + module + pháp nhân + hạn + chưa thu hồi + thế hệ; trả danh tính đã xác minh.
- Mã ủy nhiệm theo phiên **không dài hơn phiên**; bị thu hồi khi đăng xuất / phiên thu hồi / quyền đổi.
- `ktt.nguoi_dung_id` và `ktt.ngay_hieu_luc` **không** được dùng làm danh tính.
- **Python `phien.py`:**
  - sinh mã ngẫu nhiên an toàn (`secrets`);
  - gọi hàm cấp/thu hồi/xác minh bằng **bind**;
  - không ghi mã vào log/`repr`/exception.

**Test PG** (dưới login thật, tiền tố vai) — **bắt buộc đủ ca âm:**
- giả GUC;
- sai login;
- sai module;
- sai pháp nhân;
- hết hạn;
- đã thu hồi;
- mã việc sai thế hệ;
- mã ủy nhiệm dài hơn phiên;
- runtime SELECT trực tiếp bảng phiên bị chặn;
- bảng không chứa mã gốc;
- `repr` không lộ mã.

Ca nghiệp vụ còn skip ở G2-02 (tạo/tra/trùng dưới login thật) nếu nay chạy được bằng phiên thì bật lên — được sửa `tests\test_g2_02.py`? **Không**: ngoài whitelist. Ghi "Cần lead" để lead mở lát nhỏ sau.
