# KK-MTQ4-<nhóm>: kiểm kê (chỉ đọc) và đề xuất chia lát cho phần còn lại của MTQ-4 — chỉ tài liệu

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- **Chỉ tạo một tệp tài liệu** (tên ở cuối). Không sửa mã, không commit, không mở server/PostgreSQL. Không xóa file.
- Không đọc `var\`, tệp bí mật hay dữ liệu thật.
- Chỗ chưa rõ: ghi vào mục "Cần lead", không tự quyết.

**Căn cứ (đọc):**
- Thiết kế `docs\46-chuyen-doi-dieu-phoi\THIET-KE-MA-TRAN-THAM-QUYEN.md`: §4.1 bảng ô, §4.2 điểm nối, §5.1–5.3, §7 bảng lát MTQ-4b…4m.
- Phần đã làm (đọc mã để biết mẫu):
  - lõi M0039 `k2/sql_ma_tran_tham_quyen.py` (catalog `_CATALOG`);
  - cổng phiên `k2/sql_mtq_cong.py`: M0041, M0043, **M0045 `MTQ_CONG_C_SQL`** gồm resolver whitelist theo bảng: `master.hop_dong`, `master.du_an`, `master.phap_nhan`, `kho.chung_tu`, `kho.lien_ket_chung_tu`, `kho.lo_xuat`;
  - adapter `k2/quyen.py:kiem_tham_quyen`;
  - các điểm CRM luồng B/M1 đã nối trong `k2/crm.py`;
  - QD-20261026-03 (HĐ thuộc CRM) trong `docs/QUYET-DINH.md`.
- Mẫu chia lát đã làm: `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\giao-mtq-4a3a.md` (SQL resolver) và `giao-mtq-4a3b.md` (nối Python).

**Việc:** cho **nhóm được giao** (dưới), lập bảng **từng điểm kiểm quyền hiện có** gồm các cột:
- tệp:dòng;
- hàm/route/hàm SQL;
- kiểm hiện tại (`quyen.kiem(...)` / vai / `ktt_*` / RLS / trigger);
- khóa catalog `MODULE:MAN:HANH_DONG` tương ứng theo §4.1 (không có trong `_CATALOG` thì ghi "THIẾU CATALOG");
- đối tượng `{bang,id}` dựng được từ dòng thật;
- **resolver SQL còn thiếu** trong cổng phiên;
- loại tiền (`PHI_TIEN` / `TONG_HOP_DONG` / `XIN_THANH_TOAN`) và nguồn số tiền đã khóa nếu cần;
- ghi chú tách nhiệm / phạm vi hẹp cần giữ.

Sau bảng:
1. Đề xuất **chuỗi lát** theo mẫu 4a3a/4a3b, mỗi lát ≤ 3 tệp kể cả test.
   - Lát SQL đi tuần tự vì cùng giữ `pg_migrations.py`.
   - Ghi phụ thuộc giữa các lát.
   - Đánh dấu lát nào chỉ cần nối Python với resolver đã có.
2. Mục **"Rủi ro"**: điểm có thể làm rộng quyền, fallback, tiền, tách nhiệm.
3. Mục **"Cần lead"**: câu hỏi cụ thể.

Không viết mã, không đề xuất ngoài thiết kế. Dài tối đa khoảng 3 trang.
