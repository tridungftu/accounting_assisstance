# KK-DON-DEP: dữ liệu tạm, hạn giữ, cách dọn, chỗ lưu trùng (QD-20261026-09) — chỉ tài liệu

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- **Chỉ tạo một tệp** `docs\46-chuyen-doi-dieu-phoi\KK-DON-DEP.md` trong worktree hiện tại (nhánh `lat/kk-don-dep`).
- Không sửa mã, không commit, không mở server/PostgreSQL. **Không xóa file, không chạy lệnh dọn nào.**
- Không đọc `var\`, tệp bí mật, dữ liệu thật, `.env`. Không in DSN.
- Chỗ chưa rõ: ghi mục "Cần lead".

**Căn cứ:**
- `docs\QUYET-DINH.md` mục **QD-20261026-09**: lời Anh nguyên văn và các ý đã chốt.
- `docs\46-chuyen-doi-dieu-phoi\KK-VUNG-DU-LIEU.md`.
- `KK-XUONG-SONG.md` (XS-2 hàng việc nền).
- `KK-MA-HOA-LUU-RIENG.md` (sao lưu, lịch giữ).
- `CLAUDE.md` mục 2: "Không xóa file; cần bỏ thì chuyển vào `LUU-TRU`".
- Mã: `ha_tang/pg_migrations.py`, `k2/sql_*.py`, `m4/sql_*.py`, `ha_tang/cong_ocr.py`, `tri_thuc/cong_ai.py`, `tools/chay_test_theo_module.py`, `tools/mo_demo_worktree.ps1`.

**Số đo lead đã có (26/10 22:30):**
- cụm PostgreSQL DEMO 4,72 GB, 327 CSDL, trong đó ~303 CSDL test `kho_test_*` còn sót từ các lần chạy cũ;
- 209 worktree, ~4,5 GB;
- ổ D trống 174 GB.

**Việc:** tài liệu gồm:
1. **Phân loại mọi bảng/kho có dữ liệu tạm hoặc tăng không giới hạn:**
   - khóa giữ/lease;
   - việc chạy máy đã xong: G5 CRM, review/chứng từ M4, Request, bộ tải M2;
   - hộp nhận/ACK bus đã xử lý;
   - biên nhận chống bấm trùng;
   - cache OCR/AI;
   - tệp trung gian (Hot Folder, tạm);
   - nhật ký cổng AI;
   - bản nháp đã hủy;
   - bản chép Review (`m4.review_chep_*`) sau khi nạp và đối chiếu xong.

   Mỗi dòng ghi: tệp:dòng định nghĩa, ai ghi, có ai còn cần đọc lại không (replay, chứng thực, kiểm toán), **đề xuất hạn giữ**, **cách dọn**. Cách dọn chọn một trong ba:
   - chuyển sang bảng/tệp lưu trữ;
   - gộp thành dòng tổng hợp;
   - xóa dòng tạm — chỉ khi không phải bằng chứng, và ghi rõ cần Anh cho phép.
2. **Dữ liệu KHÔNG được dọn**: chứng từ, phiên bản, bằng chứng duyệt, seal, PDF đã duyệt, nhật ký kiểm toán. Ghi rõ ranh giới.
3. **Chỗ lưu trùng** (cùng thông tin lưu hai nơi) và đề xuất giữ một. Ví dụ cần kiểm:
   - `m4.boq_dong` vừa có cột đã đọc vừa có `o_goc` (ô gốc) trong khi tệp gốc + hash đã ở kho file;
   - `m4.review_chep_*` song song bảng M4 gốc;
   - JSON lặp lại trong bảng phiên bản.

   Chỉ đề xuất; nêu rõ mất gì nếu bỏ (định vị ô, chứng cứ).
4. **Đối chiếu nguyên tắc QD-09** trên M4 BOQ/đợt/phụ lục:
   - đợt và khối lượng có đang là dòng trong bảng cố định không (không tạo bảng/cột mới mỗi đợt);
   - phụ lục có đủ `THEM`/`THAY`/**`BO`** không. `m4.boq_dong` hiện chỉ có `GOC/THEM/THAY` trong khi bản Review có `BO` — nêu thiếu sót và đề xuất lát sửa.

   Tương tự cho CRM (bảng phiên bản) và M3/M9 nếu có mẫu "tạo mới thay vì thêm dòng".
5. **Dọn môi trường làm việc:**
   - CSDL test sót trên cụm DEMO;
   - worktree của lát đã gộp;
   - thư mục `var\demo-*` trong worktree;
   - log/thư mục tạm của runner.

   Đề xuất cách an toàn: chỉ đúng mẫu tên, chỉ lát đã gộp vào `hop-nhat-20261023`, nhánh git vẫn giữ nên khôi phục được, chạy khi không có test/Codex. Ghi rõ việc nào là **xóa** (cần Anh cho phép vì trái quy tắc "không xóa file") và việc nào chỉ là chuyển vào `LUU-TRU`.
6. **Cơ chế dọn chung:**
   - một việc nền định kỳ dùng hàng việc XS-2 khi có, chạy sau sao lưu;
   - mỗi bảng tạm khai báo hạn giữ trong khai báo module (XS-4a/XS-5a);
   - có nhật ký số dòng đã dọn và dung lượng thu hồi;
   - VACUUM/giới hạn WAL cho PostgreSQL.
7. **Chia lát** (mỗi lát ≤ 3 tệp kể cả test, SQL append `M00xx_*`) và thứ tự.
8. **"Cần lead"** và **câu cần Anh chốt** (ngắn, có phương án đề xuất).

Tối đa khoảng 3 trang. Nêu số đếm, không in dữ liệu.
