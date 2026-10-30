# G2 · giao G2-05 — registry module, engine, adapter, hàm và contract

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `lat/g2-04` (G2-00…G2-04).

Dùng lại cách viết SQL/test các lát trước:
- tiền tố vai;
- login thật;
- phiên xác minh G2-03;
- audit G2-04;
- sổ `doi_cau_truc.py`;
- không DROP.

## Lát G2-05

**Tệp:** `src\kho_tri_thuc\core\sql\005_dang_ky.sql`; `src\kho_tri_thuc\core\dang_ky.py`; `tests\test_g2_05.py`.

**Căn cứ:**
- Chuẩn CSDL §3 (registry; `loi.dang_ky_ham_module`: Core gọi resolver động, owner module, thiếu → `CHO`);
- Chuẩn SDK §3.10 (sổ contract: mã, phiên bản, module sở hữu, module đang dùng, trạng thái `nhap` / `anh_duyet` / `dang_dung` / `ngung`; phiên bản cũ giữ cho module còn dùng);
- Đặc tả CSDL §3.1–§3.2, §4.2 (Core gọi module);
- `module.v1` / `engine.v1` trong `src\kho_tri_thuc\core\contract\manifest.json` (G2-17).

**Việc:**
- **Bảng `loi`:**
  - module, phiên bản module;
  - engine định nghĩa, adapter / capability;
  - đăng ký hàm module (`loi.dang_ky_ham_module`);
  - sổ contract (`loi.so_contract` hoặc tên đúng bảng tên chuẩn) + module dùng contract.
- **Registry không cần module đã cài** (chỉ giao diện). Chỉ chức trách cài đặt sửa binding (hàm DEFINER), runtime chỉ đọc qua hàm.
- **Sổ contract:**
  - không cho xóa phiên bản còn module dùng;
  - chuyển trạng thái hợp lệ;
  - contract nghiệp vụ mới / phiên bản mới của contract đang dùng phải ở `anh_duyet` trước `dang_dung`.
- **Phân giải hàm module:** trả `CHO` khi module chưa cài / chưa có hàm; không gọi `current_user` làm danh tính.
- Ghi audit cho mọi thay đổi registry.

**Test PG:**
- đăng ký / đọc;
- runtime không ghi được;
- `CHO` khi thiếu;
- không xóa phiên bản contract còn người dùng;
- chuyển trạng thái sai bị chặn;
- audit có dòng.
