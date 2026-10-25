# AI-3 vòng 2 — lead trả lời điểm dừng mục 5 (ghim SHA-256 lõi Review)

Bạn là worker Codex, chạy không tương tác. Làm **toàn bộ việc trong `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261025\giao-ai-3.md`** (đọc lại đủ), với quyết định của lead về điểm dừng mục 5:

- Cơ chế ghim `src/kho_tri_thuc/m4/nguon_review.py` (`PIN`, dòng ~45 và ~48) **được cập nhật theo tiền lệ AI-0b** (commit `393dc15` "[AI-0b] Tạm khóa Cloud trực tiếp…": đã đổi băm của chính `trich_xuat/ai_cloud.py` và `trich_xuat/cloud.py` kèm chú thích). Lát này: sau khi sửa xong 2 tệp engine, **thay đúng 2 giá trị băm đó** bằng SHA-256 mới của tệp đã sửa (byte trên đĩa), chú thích `# AI-3 26/10/2026: Cloud qua cổng AI dùng chung (TL 48)`. **Không đổi** cơ chế so băm, không đổi băm tệp khác, không thêm tệp mới vào `PIN` trừ khi engine #6 import một tệp mới trong `review_goc` (không nên — cổng AI ở ngoài `review_goc`, import bình thường).
- Tính băm bằng `python -X utf8 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <tệp>` hoặc PowerShell `Get-FileHash -Algorithm SHA256`. Nếu sandbox không chạy được cả hai → để nguyên `PIN`, ghi rõ trong báo cáo "lead cập nhật băm" (lead làm khi commit).
- Tệp được sửa thành: `ai_cloud.py`, `cloud.py`, `nguon_review.py` (chỉ 2 dòng `PIN`), một tệp test (+ `cong_ai.py` chỉ khi buộc thêm 1 loại việc). Test phải chạy cả `tests.test_m4_nguon_review*`/test nạp lõi Review có sẵn (tìm theo `nguon_review`) để chứng minh lõi vẫn nạp được với băm mới.
- Không commit; báo cáo như handoff gốc.
