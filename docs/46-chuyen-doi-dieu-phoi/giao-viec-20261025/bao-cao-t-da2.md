Anh, đã sửa đúng hai file test:

- `tests/crm_ky_ket_async.cjs:208,494–495`: cập nhật ba nhãn tìm nút, giữ nguyên assert.
- `tests/test_crm_41_02.py:443`: thay kiểm route CFO duyệt bằng kiểm route ghép `du-an-ban/tien-do`, ghi căn cứ QD-20261025-07.

Kết quả trước → sau: Node **0/14 → 14/14 ca**; Python **28/29 → 29/29 test**. Không phát sinh lỗi mới; UTF-8 không BOM, `git diff --check` đạt.

Không commit. Thông điệp đề xuất: `[T-DA2] Cập nhật test theo giao diện BG-1d và DA-2`.