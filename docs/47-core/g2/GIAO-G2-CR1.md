# G2 · giao G2-CR1 — contract `du_an_dang_ban.v1` của CRM thử Core

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `hop-nhat-20261023` (đã có G2-00…G2-11, G2-17 sổ contract kỹ thuật, G2-24 kiểm gói).

## Lát G2-CR1

**Tệp:**
- `src\kho_tri_thuc\modules\crm\contract\du_an_dang_ban.schema.json`
- `src\kho_tri_thuc\modules\crm\contract\du_an_dang_ban.demo.json`
- `tests\test_g2_cr1.py`

**Căn cứ:**
- `docs\47-core\g1\CONTRACT-NGHIEP-VU.md` §3 `du_an_dang_ban.v1` (dòng ~1002), phần "Quy ước áp dụng cho NV-CRM", "Từ điển trường dùng chung", "Grain và khóa dòng đăng ký", "Đăng ký gói CRM";
- quy tắc nhập tay có `nguon_tep_ids` (dòng ~49);
- CD-032 (contract trong gói, JSON Schema 2020-12 + ví dụ + phiên bản);
- CD-038 (phạm vi CRM thử G2).
- **Dùng lại** bộ phân giải / meta-schema của G2-17 (`src\kho_tri_thuc\core\contract\ky_thuat.json`, `manifest.json` và mã kiểm ở test G2-17 / G2-24) — chỉ đọc. Không tạo bộ kiểm schema mới.

**Việc:**
- Viết đúng các trường, nguồn, đơn vị, ràng buộc của đặc tả; **không thêm nghiệp vụ**.
- Ví dụ DEMO đầy đủ (chữ DEMO, không dữ liệu thật). Mọi `$ref` tới contract kỹ thuật phân giải offline qua URN của G2-17.
- Chỗ đặc tả ghi "chờ Anh" (ví dụ bên đọc ngoài CRM): giữ đúng như đặc tả, ghi "Cần lead" trong báo cáo, không tự chốt.

**Test** (thuần, không PG):
- schema hợp lệ meta-schema 2020-12;
- ví dụ DEMO đạt schema;
- thiếu trường bắt buộc / sai đơn vị / `nguon_tep_ids` rỗng hoặc trùng → đỏ;
- mọi `$ref` phân giải offline;
- trường khớp danh sách ở đặc tả (đọc bảng trong tài liệu hoặc liệt kê có trích dòng).

Báo cáo ≤ 3 dòng.
