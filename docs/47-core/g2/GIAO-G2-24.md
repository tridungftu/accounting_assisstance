# G2 · giao G2-24 — kiểm gói và staging của Module Manager (giao sớm: phần đọc gói không cần CSDL)

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `hop-nhat-20261023` (đã có schema G2-17 `src\kho_tri_thuc\core\contract\manifest.json`, `ky_thuat.json`).

## Lát G2-24

**Tệp:** `src\kho_tri_thuc\core\goi.py`; `src\kho_tri_thuc\core\cai_dat.py`; `tests\test_g2_24.py`.

**Căn cứ:**
- Chuẩn SDK §3.9–§3.10 (gói module = thư mục + `module.json` + `contract/`; Core tự suy schema / role / cổng; module không được khai `goi_migration.vai`, `tien_trinh.cong`…);
- Đặc tả SDK §6–§7;
- `CONTRACT-DU-LIEU.md` §15 (schema manifest, ca âm).

**Việc** (chỉ phần **không** cần CSDL — kích hoạt / áp gói là G2-25):
- **`goi.py`** — đọc gói từ thư mục staging:
  - **không chạy mã** khi đọc manifest;
  - chặn path traversal / symlink / junction ra ngoài gói;
  - giới hạn kích thước;
  - kiểm `module.json` theo schema `module.v1` (G2-17, dùng `jsonschema` + checker ngày như `tests\test_g2_17.py`);
  - kiểm `contract/` đủ và hợp lệ: mỗi contract có schema + ví dụ JSON hợp lệ + phiên bản;
  - kiểm trường Core tự suy không được khai;
  - kiểm route trùng trong gói;
  - kiểm tương thích phiên bản Core.
- **`cai_dat.py`** — staging:
  - chép gói vào vùng staging DEMO (`var\core-demo\<ma>\goi\`), tính SHA256 từng tệp và cả gói;
  - trả báo cáo kiểm `DAT` / `KHONG_DAT` kèm lý do tiếng Việt;
  - chưa áp migration, chưa kích hoạt.

**Test** (thuần, gói mẫu DEMO dựng trong thư mục tạm):
- gói hợp lệ đạt;
- traversal / symlink bị chặn;
- khai cổng / role / schema bị bác;
- thiếu `contract/` bị bác;
- contract ví dụ sai schema bị bác;
- route trùng bị bác;
- không chạy mã trong gói (gói có `__init__.py` gây lỗi nếu import → vẫn đọc được manifest).
