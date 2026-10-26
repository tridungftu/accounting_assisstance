# Loạt 2 sau chốt MTQ-4 — phần riêng (ghép với `giao-mtq4-chung.md`)

## MTQ-NEN-1 · Luồng NỀN (lead giữ, A3) · hàm quyết định chỉ đọc

**Tệp (3):**
- `k2/sql_mtq_nen.py` mới (hằng `MTQ_NEN_A_SQL`);
- `ha_tang/pg_migrations.py`: `M00xx_MTQ_NEN_A`;
- `tests/test_mtq_nen_sql.py` mới.

**Đã có:** **M0051** tách resolver thành `master.mtq_giai_doi_tuong(text,jsonb)` (`STABLE`, nội bộ, **không** cấp cho `app_web`).

**Việc:**
- Thêm hàm `master.mtq_duoc_doc(p_hanh_dong text, p_doi_tuong jsonb) RETURNS boolean`:
  - `STABLE SECURITY DEFINER`, cùng `search_path` với cổng;
  - **không** INSERT/UPDATE; gọi được trong `SET TRANSACTION READ ONLY` và trong hàm `STABLE`/RLS.
- Logic:
  - danh tính từ GUC phiên như cổng;
  - giải đối tượng bằng `master.mtq_giai_doi_tuong`;
  - tính quyết định **giống lõi M0039 `mtq_quyet_dinh`** (gán vai, phạm vi, ô tick, hạn mức) nhưng không ghi nhật ký. Tách phần tính thuần thành hàm mới nếu cần; **không** đổi hàm cũ.
- Hợp đồng trả về:
  - PN chưa bật ma trận → `NULL` (bên gọi dùng đường cũ CU);
  - bật → `true`/`false`;
  - không giải được/không hợp lệ → `false`.
- Chỉ trả boolean: không lộ pn/hd/phạm vi.
- ACL: `REVOKE PUBLIC`, `EXECUTE` cho `app_web`.
- **Không** sửa `ktt_duoc`/RLS nền ở lát này (nối vào RLS là lát sau).

**Test:**
- So `mtq_duoc_doc` với quyết định của cổng phiên (`cho_phep`) trên ma trận ca: bật/tắt, đúng/sai phạm vi, thiếu tick, khác PN, đối tượng không tồn tại.
- Gọi trong `READ ONLY` được; không có dòng nhật ký mới.
- `app_web` gọi được; không lộ thông tin ngoài boolean.
- `app_web` vẫn **không** gọi được `mtq_giai_doi_tuong`.

## MTQ-4b2a · Luồng CRM · guard SQL G2 báo giá / G3 soạn (KK-MTQ4-CRM §3 dòng 4b2a)

**Tệp (3):**
- `k2/sql_mtq_crm.py`: thêm hằng `MTQ_CRM_B_SQL`, **không** đổi `MTQ_CRM_A_SQL` (M0050);
- `ha_tang/pg_migrations.py`: `M00xx_MTQ_CRM_B`;
- `tests/test_mtq_crm_sql.py`: thêm ca, giữ ca cũ.

**Việc:**
- Thay kiểm vai cũ trong các hàm/trigger SQL của **G2 báo giá và G3 bản soạn** (picker/mẫu ghim, in/xuất/công bố/tải theo KK-MTQ4-CRM §2) bằng gọi cổng phiên khi PN bật. Giữ đường cũ khi tắt.
- Dùng resolver M0047/M0048 sẵn có (bảng `master.crm_bao_gia`, `master.crm_hd_soan`, `master.crm_gk_xuat`…).
- Không đụng G4 ký/G5/G6, tỷ giá (B1 làm lát riêng), phạm vi hẹp (B3, lát 4b2b).
- PN tắt → so oracle đường cũ (cho/chặn + mã); bật ở A không đổi kết quả PN B tắt (bài học 4b1b).
