# KK-XS: kiểm kê mã hiện có và đề xuất chia lát XS-1…XS-4 (Xương sống, CD-017) — chỉ tài liệu

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- **Chỉ tạo một tệp** `docs\46-chuyen-doi-dieu-phoi\KK-XUONG-SONG.md` trong worktree hiện tại (nhánh `lat/kk-xs`).
- Không sửa mã, không commit, không mở server/PostgreSQL. Không xóa file.
- Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ: ghi mục "Cần lead".

**Căn cứ (đọc):**
- `D:\Claude\Phan mem ho tro ke toan\53-kien-truc-xuong-song-engine-module.md` (TL 53, nhất là §6 chuyển đổi dần).
- `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` mục **CD-017** (và CD-016).
- Mã hiện có. Tìm cơ chế sẵn có, ví dụ:
  - outbox/sự kiện (`nhat_ky.su_kien`, các bảng `*su_kien*`, hàng đợi);
  - việc nền (job/lease/worker, bộ tải M2 `m2/tai_hoa_don/dieu_phoi.py`, G5 queue, `hang_doi`);
  - khai báo khung `giao_dien/khung_khai_bao.py` (CRM, TL 49);
  - cổng AI `tri_thuc/cong_ai.py`;
  - cổng OCR `ha_tang/cong_ocr.py`;
  - các "engine" hiện có (#6 trích chung, review xây dựng, M2-00).

**Việc:** tài liệu gồm:
1. **Hiện trạng** cho từng XS:
   - XS-1: bus sự kiện bền trong PG, outbox/inbox idempotent;
   - XS-2: hàng việc nền dùng chung;
   - XS-3: danh bạ engine + hợp đồng engine + bộ test mẫu;
   - XS-4: khai báo module tổng quát + công tắc Tắt/Thử/Vận hành theo module × pháp nhân; ma trận thẩm quyền đọc cột từ khai báo.

   Mỗi XS ghi: cái gì **đã có**, ở đâu (tệp:dòng), dùng lại được đến đâu, thiếu gì.
2. **Chuỗi lát đề xuất:**
   - mỗi lát ≤ 3 tệp kể cả test;
   - lát SQL dùng migration mới (append; tên tạm `M00xx_*`, lead đánh số);
   - ghi phụ thuộc giữa các lát;
   - ghi lát nào đụng tệp dùng chung (`server.py`, `pg_migrations.py`, `khung_khai_bao.py`, `app.js`).
3. **Lát thử nghiệm đầu tiên** đề xuất cho "tắt một module, module kia vẫn chạy và hiện 'chờ'" (điều kiện báo Anh của CD-017).
4. **Đề xuất danh bạ engine ban đầu**:
   - E-OCR (đã có `cong_ocr`), E-AI (cổng AI), E-TRICH (#6), E-RAG (M9), E-SHEETS (M9-3), E-HOADON, E-MOC, E-KIEMTRA-DOT;
   - mỗi engine ghi: mã, phiên bản, vào/ra, trạng thái, bằng chứng, module dùng.
5. **Rủi ro**: không dừng việc đang chạy, không đổi hành vi, test cũ phải đạt.
6. **"Cần lead"**.

Tối đa khoảng 3 trang. Không đề xuất ngoài TL 53/CD-017.
