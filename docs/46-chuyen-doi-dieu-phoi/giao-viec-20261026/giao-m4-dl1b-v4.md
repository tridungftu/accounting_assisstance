# M4-DL1b vòng 4: thay phép kiểm hash byte tệp M0038 bằng phép kiểm hash nội dung SQL (lead chốt)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở PostgreSQL. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m4-dl1b`. Các thay đổi vòng 2 và vòng 3 đang chờ commit; giữ nguyên chúng.

**Việc:**
- Trong `tests/test_m4_review_chep_schema.py`, hàm `test_dl1b_chi_sql_va_khong_doi_byte_migration_da_phat_hanh`, thay hai dòng đọc `SQL_PATH.read_bytes()`, tách tiền tố và so `"d5ffb04f…"` bằng:
  ```python
  self.assertEqual(hashlib.sha256("\x00".join(SQL).encode("utf-8")).hexdigest(),
                   "a908f99c1c8d063d2a9b7993bd38aecdb3f82cf896f3f2b64ae40f6ba9c14404")
  ```
  `SQL` là `M4_REVIEW_CHEP_SQL` (M0038) đã import trong tệp. Lead đã tính giá trị này từ bản M0038 đã phát hành trên hợp nhất, 73 câu lệnh; kết quả như nhau dù tệp checkout CRLF hay LF.
- Thêm chú thích một dòng: ghim nội dung câu lệnh SQL M0038, không ghim byte tệp, vì byte tệp đổi theo kiểu xuống dòng khi checkout.
- Không đổi phép kiểm nào khác.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m4_review_chep_schema`, với PYTHONPATH=`src;.;tests`. Phần thuần phải đạt hết.

**Báo cáo (≤ 3 dòng)**, thông điệp commit `[M4-DL1b] vòng 4: …`.
