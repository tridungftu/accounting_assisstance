# MTQ-NEN-2 · Đối tượng thuộc nhiều pháp nhân (A1) — quyết định lead + hai lát

**Căn cứ:**
- A1 (Anh chốt, QD-20261026-08): nguồn gộp nhiều pháp nhân phải đủ quyền ở **mọi** pháp nhân liên quan.
- Câu "Cần lead" của MTQ-4i-b1: resolver M0051 chỉ trả một PN.
- Lead quyết 26/10 22:40 (QD-20261026-10).

## Quyết định thiết kế (lead, kỹ thuật)

1. **Hàm giải tập (mới, nội bộ):**
   - `master.mtq_giai_doi_tuong_tap(p_hanh_dong text, p_doi_tuong jsonb) RETURNS jsonb` = mảng các ngữ cảnh. Mỗi phần tử **cùng dạng** kết quả `mtq_giai_doi_tuong`: pn, hd, da, lh, khach, phong, loai, hop_le, ma, ly_do.
   - `STABLE`, chỉ đọc, `SECURITY DEFINER`, cùng `search_path` với cổng, **không** cấp `app_web`.
   - Nhánh hiện có (một PN) → mảng **một** phần tử = đúng kết quả `mtq_giai_doi_tuong` (gọi lại, không chép logic).
   - Không giải được → mảng một phần tử có `pn` NULL, giữ hành vi hiện tại (`MTQ_CAN_RESOLVER_MTQ4` khi có PN bật).
   - Mảng sắp xếp ổn định theo `pn`, không trùng PN.
2. **Tổng hợp quyết định trên tập PN:**
   - **Không** PN nào trong tập bật ma trận → trả tín hiệu CU như hiện nay (`MTQ_TAT`).
   - **Mọi** PN bật → tính quyết định **từng PN**: phòng, phạm vi, tick, hạn mức với **cùng** số tiền. Chỉ cho khi **tất cả** cho. Từ chối → trả kết quả từ chối của PN **đầu tiên theo thứ tự** không đạt; giữ nguyên dạng jsonb hiện có.
   - **Hỗn hợp** (có PN bật, có PN tắt) → **chặn**: `MTQ_PN_HON_HOP`, lý do "Đối tượng thuộc nhiều pháp nhân, có pháp nhân chưa bật ma trận".
   - `phong_id` từ tham số chỉ dùng khi tập có **một** PN. Tập nhiều PN mà có `phong_id` → `MTQ_PHONG_MO_HO`.
3. **Nhật ký từ chối:**
   - Ghi cho **mỗi** PN không đạt (cùng request ID), để Admin từng PN thấy qua RLS.
   - Bảng nhật ký đang ràng buộc một dòng/request → **không** đổi ràng buộc; ghi PN từ chối đầu tiên và nêu trong báo cáo.
4. **Đối tượng một PN hiện có: kết quả phải giống hệt trước** (cho/chặn, mã, lý do, dạng jsonb). Test so trên ma trận ca cũ.
5. `mtq_duoc_doc` (M0054) theo cùng quy tắc:
   - mọi PN tắt → NULL;
   - hỗn hợp → false;
   - mọi PN bật → true khi tất cả true.

## MTQ-NEN-2a · cổng phiên dùng tập PN

**Tệp (3):**
- `k2/sql_mtq_cong.py`: hằng mới `MTQ_CONG_G_SQL` gồm:
  - tạo `mtq_giai_doi_tuong_tap`;
  - `CREATE OR REPLACE` `master.mtq_quyet_dinh_phien` và `master.mtq_ghi_tu_choi_phien` từ **thân M0051 hiện hành**, đổi sang duyệt tập;
- `ha_tang/pg_migrations.py`: `M00xx_MTQ_CONG_G`, dấu `# MTQ-NEN-2a — CD-012:`;
- `tests/test_mtq_cong_g_sql.py` mới.

**Không** sửa `sql_mtq_nen.py` (lát 2b), `ktt_duoc`/RLS nền, hằng cũ. ACL hai cổng giữ như cũ; hàm tập không cấp `app_web`.

**Test (PG):**
- (a) mọi ca một PN của test cổng hiện có cho kết quả giống hệt. Dùng lại oracle hoặc so với thân M0051 trên cùng dữ liệu.
- (b) Có test-only resolver trả 2 PN: dựng bằng hàm giả trong CSDL test, **không** đưa vào migration. Hai PN bật cùng đạt → cho; một PN thiếu tick → chặn đúng mã của PN đó; hạn mức tính từng PN.
- (c) Hỗn hợp bật/tắt → `MTQ_PN_HON_HOP`; cả hai tắt → CU.
- (d) Nhiều PN + `phong_id` → `MTQ_PHONG_MO_HO`.
- (e) Nhật ký: số dòng theo quyết định 3.
- (f) ACL: `app_web` không gọi được hàm tập.

## MTQ-NEN-2b · quyết định chỉ đọc dùng tập PN (sau khi 2a gộp)

**Tệp (3):**
- `k2/sql_mtq_nen.py`: hằng mới `MTQ_NEN_B_SQL`, `CREATE OR REPLACE master.mtq_duoc_doc(text,jsonb,numeric)` theo quyết định 5;
- `ha_tang/pg_migrations.py`: `M00xx_MTQ_NEN_B`;
- `tests/test_mtq_nen_sql.py`: thêm ca, giữ ca cũ.

Vẫn `STABLE`, chỉ đọc, gọi được trong `READ ONLY`. Ca một PN giữ nguyên kết quả.

## Sau NEN-2a/2b: MTQ-4i-b1 làm tiếp

Thêm nhánh rS/rA vào `mtq_giai_doi_tuong_tap` (`CREATE OR REPLACE`), trả **mọi** PN liên quan:
- nguồn gộp → mọi PN theo phạm vi NGUON (M0049);
- đổi đích ánh xạ → PN cũ ∪ PN mới.
