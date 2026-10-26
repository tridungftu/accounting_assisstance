# MTQ-4b1a: Ma trận thẩm quyền, resolver SQL cho đối tượng CRM G1/G2/G3/G4/G7/dự án (theo KK-MTQ4-CRM, lát 4b1a). Rủi ro cao: SECURITY DEFINER + migration.

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM. `pg_migrations.py` giữ LF. Không commit. Không mở server/PostgreSQL DEMO. Không xóa file.
- Test PG tự tạo `kho_test_*`, không đọc `KHO_PG_DEMO_*`.
- **Chỗ chưa rõ: dừng, ghi "Cần lead".**
- Làm trong worktree hiện tại, nhánh `lat/mtq-4b1a`, dựng từ hợp nhất. Migration cuối hiện là **M0046**.

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\KK-MTQ4-CRM.md`: §2 bảng điểm kiểm quyền và ký hiệu đối tượng LH/M/C/BG/S/K/X/D/G7/H; §3 dòng **4b1a**; §4 rủi ro.
- Mẫu đã làm: `k2/sql_mtq_cong.py` hằng `MTQ_CONG_C_SQL` (M0045), cùng giao việc `giao-viec-20261026/giao-mtq-4a3a.md` và review `review-mtq-4a3a.md` (bài học: không làm rộng sang đối tượng ngoài module; PN tắt → CU; bật → không fallback).
- Thiết kế `THIET-KE-MA-TRAN-THAM-QUYEN.md` §4.1, §5.1.

**Việc:** migration mới, tên tạm `M00xx_MTQ_CONG_D`, dấu `# MTQ-4b1a — CD-012:`. Dùng `CREATE OR REPLACE` cả hai hàm cổng (`mtq_quyet_dinh_phien`, `mtq_ghi_tu_choi_phien`), giữ chữ ký/ACL/search_path.
1. Thêm resolver whitelist cho các đối tượng CRM ở dòng 4b1a: mẫu G1, báo giá G2, bản soạn/ký G3/G4, bộ chuẩn G7, dự án đang bán/lô/mốc, hợp đồng giao kết (H) đọc theo màn.
   - Mỗi resolver suy `pn` và HĐ/DA/LH/khách từ dòng thật.
   - **Mỗi bảng chỉ ghép với đúng các khóa catalog §4.1 của màn đó.** Cặp sai → `MTQ_CAN_RESOLVER_MTQ4`.
2. **Không làm trong lát này** (chờ Anh/lead chốt, KK-MTQ4-CRM §5):
   - tỷ giá chung (`TY_GIA`) và mọi đối tượng ảnh hưởng nhiều PN;
   - quan hệ phạm vi hẹp HĐ–dự án–khách thay `crm_ky_pham_vi/crm_kiem_pham_vi` (§5 câu 1);
   - V8;
   - cổng đọc/lọc trong giao dịch READ ONLY.

   Các cặp này giữ `MTQ_CAN_RESOLVER_MTQ4` khi bật.
3. PN chưa bật → `CU` như cũ cho mọi bảng. Bật → không fallback. `pn IS NULL` mà có PN khác bật → chặn.
4. `mtq_ghi_tu_choi_phien` suy `pn` cho các bảng mới.

**Test, tệp mới `tests/test_mtq_crm_resolver_sql.py`** (PG `skipUnless KHO_PG_DSN_TEST`, tự tạo CSDL; phần tĩnh không cần PG):
- Từng cặp bảng × khóa catalog được whitelist:
  - PN bật + phạm vi đúng → cho phép;
  - sai phòng/không phạm vi → từ chối có mã.
- Cặp sai → `MTQ_CAN_RESOLVER_MTQ4`.
- PN tắt → `CU`.
- Id không tồn tại → chặn khi có PN bật.
- `TY_GIA` vẫn `MTQ_CAN_RESOLVER_MTQ4`.
- ACL không đổi.
- Không ghim migration cuối hoặc hash byte.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_crm_resolver_sql tests.test_mtq_cong_c_sql tests.test_mtq_cong_sql`. Không có `python` thì ghi NOT_RUN; lead chạy PG.

**Tệp (3):** `k2/sql_mtq_cong.py` (thêm hằng `MTQ_CONG_D_SQL`, không đổi hằng cũ), `ha_tang/pg_migrations.py`, `tests/test_mtq_crm_resolver_sql.py`.

**Báo cáo (≤ ⅓ trang)**, "Cần lead". Thông điệp commit `[MTQ-4b1a] …`.
