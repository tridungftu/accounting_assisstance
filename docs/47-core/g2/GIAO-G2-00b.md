# G2 · giao G2-00b — chẩn đoán lỗi áp đổi cấu trúc mà không lộ bí mật

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** `hop-nhat-20261023`.

**Tệp:**
- `src\kho_tri_thuc\core\doi_cau_truc.py`
- `tests\test_g2_00b.py`

**Lý do:** `ap_doi_cau_truc` gộp mọi lỗi driver thành `DOI_CAU_TRUC_THAT_BAI`, cố ý để không giữ `__context__` có DSN. Hệ quả: lỗi cú pháp SQL ở G2-12 và G2-13 phải chẩn đoán bằng tay.

**Việc:**
- Khi lỗi xảy ra lúc chạy một tệp, `LoiDoiCauTruc` mang thêm thông tin an toàn:
  - số phiên bản / tên tệp;
  - `sqlstate`;
  - `diag.context` đã lọc;
  - `message_primary` **chỉ khi** sqlstate thuộc lớp 42 (cú pháp / đối tượng). Lớp khác chỉ giữ sqlstate.
- Không bao giờ chứa DSN, mật khẩu, giá trị tham số. Lọc mọi chuỗi giống `postgresql://`, `password=`, `host=`.
- Vẫn raise ngoài `except` (không `__context__`).
- `str(exc)` vẫn bắt đầu bằng mã cũ để không phá test đang so mã.

**Test:**
- thuần (giả lỗi driver có sqlstate / diag): đúng trường, lọc bí mật, không có `__context__`;
- PG (nếu có DSN): áp một tệp SQL lỗi cú pháp giả → thông báo có số tệp + 42601.

Báo cáo ≤ 2 dòng.
