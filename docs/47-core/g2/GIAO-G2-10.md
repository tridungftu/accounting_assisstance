# G2 · giao G2-10 — bọc kho tệp và bàn giao kết quả có quyền / provenance

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `lat/g2-09` (G2-00…G2-09). Quy ước như cũ.

**Lưu ý:** tên thuộc tính test không được trùng phương thức `TestCase` (`id`, `run`…).

## Lát G2-10

**Tệp:** `src\kho_tri_thuc\core\tep.py`; `src\kho_tri_thuc\core\ket_qua.py`; `tests\test_g2_10.py`.

**Căn cứ:**
- Kế hoạch G2-10;
- Chuẩn API: tải lên ≤ 20 MiB (20.971.520 byte, đếm khi nhận luồng); tải xuống kiểm quyền mỗi lần;
- Chuẩn SDK (`tep`, `ket_qua`; nguồn do Core gắn; bàn giao kết quả trước khi engine giải phóng RAM);
- metadata G2-09.
- **Bọc (không viết lại)** kho tệp hiện có: `src\kho_tri_thuc\ha_tang\store.py` (bất biến, hash), `giao_dien\intake.py`.

**Việc:**
- **`tep.py`:**
  - nhận luồng bytes → kho tệp DEMO (`var\core-demo\<ma>\kho-file\`): hash SHA256, bất biến; cùng hash dùng lại bytes nhưng quyền theo metadata;
  - vượt 20 MiB → lỗi ngay khi đếm;
  - đọc bytes chỉ sau kiểm quyền nội dung (G2-09) + phiên;
  - ghi metadata G2-09 cùng giao dịch;
  - crash giữa CSDL – tệp → phục hồi được (staging + bước kích hoạt; không mất / không mồ côi).
- **`ket_qua.py`:** bàn giao kết quả engine. Core gắn nguồn (engine / phiên bản / việc) và ghi kết quả + tệp; engine không tự khai nguồn.

**Test** (PG + tệp tạm DEMO):
- hash bất biến;
- cùng hash khác quyền;
- 20 MiB + 1 byte bị chặn;
- đọc sai quyền bị chặn;
- giả lập crash sau ghi tệp trước commit → phục hồi;
- nguồn do Core gắn.
