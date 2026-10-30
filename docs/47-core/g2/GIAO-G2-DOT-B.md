# G2 · giao tiếp: G2-02, G2-17 (30/10/2026)

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung (mọi lát G2/G3)". Đọc trước khi làm.

**Đã gộp vào `hop-nhat-20261023`:**
- G2-00: `tools\tao_core_demo.py`;
- G2-01: `src\kho_tri_thuc\core\sql\001_vai.sql` — role/login/schema `loi`, `loi_tai_lieu`, `danh_muc`; tiền tố vai test qua `set_config`; chỉ CSDL `kho_test_*` mới được tiền tố;
- G2-33: script tài khoản (chỉ xem trước).

Dùng lại cách viết SQL / test PG của `001_vai.sql` và `tests\test_g2_01.py`. Đặc biệt: test dùng tiền tố vai, chạy dưới login thật, không DROP ROLE.

## Lát G2-02 · Nâng danh tính, pháp nhân và thành viên thành nguồn chung

**Tệp:** `src\kho_tri_thuc\core\sql\002_danh_tinh.sql`; `src\kho_tri_thuc\core\danh_tinh.py`; `tests\test_g2_02.py`.

**Việc** (chuẩn CSDL §3; đặc tả CSDL §3.1; phiếu CSDL câu 3A — Core tự quản tài khoản):
- Bảng `loi` cho người dùng, pháp nhân (= workspace), thành viên, vai nghiệp vụ. Tên đúng bảng tên chuẩn CSDL §2.
- Owner là `vai_doi_cau_truc_loi`; `vai_chay_loi` chỉ quyền tối thiểu; RLS / FORCE RLS theo chuẩn.
- **Dùng lại** nghiệp vụ/ràng buộc của bảng hiện có (`master.nguoi_dung`, `master.phap_nhan*`, `master.phan_quyen` — xem `ha_tang\pg_migrations.py` M0001 và `docs\47-core\g1\ANH-XA-MIGRATION.md`). Chỉ lấy **định nghĩa cuối**, không chạy chuỗi cũ.
- Không nhận actor từ client; không tạo bản sao thành viên.
- Python `danh_tinh.py`: hàm tạo/tra người dùng, pháp nhân, thành viên qua kết nối truyền vào (không tự mở kết nối, không in DSN). Chưa làm phiên — phiên là G2-03.

**Test PG** (tiền tố vai như G2-01):
- tạo người dùng / pháp nhân / thành viên;
- duy nhất;
- sai pháp nhân bị chặn ở RLS;
- `vai_chay_loi` không DDL;
- chạy lại SQL idempotent.

## Lát G2-17 · Đưa schema kỹ thuật / manifest đã chốt vào bộ phân giải offline (giao sớm, không phụ thuộc CSDL)

**Tệp:** `src\kho_tri_thuc\core\contract\ky_thuat.json`; `src\kho_tri_thuc\core\contract\manifest.json`; `tests\test_g2_17.py`.

**Việc:**
- Chép **nguyên văn** các JSON Schema đã chốt trong `docs\47-core\g1\CONTRACT-DU-LIEU.md`:
  - `ky_thuat.json` gồm `chung.v1` và 9 contract kỹ thuật (`tham_chieu_tep`, `van_ban_tai_lieu`, `du_lieu_bang`, `tham_so`, `noi_dung_da_che`, `tra_loi_ai`, `hoa_don`, `loi_chuan`, `viec`);
  - `manifest.json` gồm `module.v1` và `engine.v1` (đã có `contract/` theo CD-032).
- Mỗi tệp là một mảng hoặc object chứa các schema theo `$id`.
- **Không thêm schema còn "chờ Anh"** (schema riêng Mask/AI nếu đặc tả ghi chờ).

**Test** (dùng `jsonschema` nếu có trong runtime DEMO; không có thì bộ kiểm tối thiểu, ghi rõ):
- mọi schema hợp lệ meta-schema 2020-12;
- mọi `$ref` giải offline được;
- các ví dụ hợp lệ trong `CONTRACT-DU-LIEU.md` qua;
- các ca âm (trong đó `tra_loi_ai` CLOUD thiếu lượt che) bị bác;
- nội dung schema trùng khớp từng ký tự với khối JSON trong tài liệu (so bằng parse JSON).
