# G2 · giao G2-CR3 — contract sự kiện `moc_da_xay_ra.v1` (Anh chốt CD-041 mục 2)

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`. **Nền:** `hop-nhat-20261023` (có CR1 / CR2, G2-15 bus, G2-17 sổ contract). Làm theo mẫu `test_g2_cr1.py`, `test_g2_cr2.py`.

**Tệp:**
- `src\kho_tri_thuc\modules\crm\contract\moc_da_xay_ra.schema.json`
- `src\kho_tri_thuc\modules\crm\contract\moc_da_xay_ra.demo.json`
- `tests\test_g2_cr3.py`

**Căn cứ:**
- `docs\47-core\g1\CONTRACT-NGHIEP-VU.md` §5.3: phần gốc và khối **"Anh chốt 31/10/2026"** ngay cuối mục;
- bus G2-15: payload chỉ UUID tham chiếu + loại + phiên bản;
- CD-041.

**Việc:**
- **Payload:** chỉ tham chiếu.
  - `moc_id` và tham chiếu **bản ghi lịch sử ngày thực tế mới nhất** (UUID của lần ghi, không thêm số `lan` vào payload nếu bus chỉ nhận UUID — dùng UUID bản ghi lịch sử);
  - loại sự kiện **phát lần đầu** / **điều chỉnh**; sự kiện điều chỉnh tham chiếu UUID lần ghi cũ;
  - `khoa_dedupe` theo loại + bản ghi lịch sử.
- **Bên nhận khai trong contract:** CRM, M3, M10.
- **Ví dụ DEMO:** một sự kiện phát lần đầu và một sự kiện điều chỉnh.

**Test** (thuần):
- schema hợp lệ meta-schema; ví dụ đạt; `$ref` offline;
- payload có trường dữ liệu ngoài tham chiếu → đỏ;
- sự kiện điều chỉnh thiếu tham chiếu lần ghi cũ → đỏ;
- bên nhận đúng danh sách.

Báo cáo ≤ 3 dòng.
