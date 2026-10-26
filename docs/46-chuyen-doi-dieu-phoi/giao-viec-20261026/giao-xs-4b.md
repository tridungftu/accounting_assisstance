# XS-4b · SQL công tắc module × pháp nhân (CD-017, QD-20261026-11 S1–S5)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM; `pg_migrations.py` giữ LF. Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ hoặc có thể làm rộng quyền: dừng, ghi "Cần lead". Không có `python` thì NOT_RUN; lead chạy test PG.
- Test PG tự tạo `kho_test_*` (`skipUnless KHO_PG_DSN_TEST`), không đọc `KHO_PG_DEMO_*`. Dữ liệu giả đúng trigger/ràng buộc thật. Chạy được dưới guard giữ tệp.
- Migration: chỉ thêm `M00xx_MODULE_CONG_TAC`, dấu `# XS-4b — CD-017:`. Không sửa migration cũ (tới M0054). Test không ghim migration cuối.

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\XS-4-CAN-CHOT.md` (S1–S6, Anh đã chốt);
- `docs\QUYET-DINH.md` mục QD-20261026-09 (ít tài nguyên) và QD-20261026-11;
- TL 53;
- `KK-XUONG-SONG.md` §2 dòng XS-4b, §5;
- mô hình khai báo `ha_tang/khai_bao_module.py` (XS-4a, có "mặc định công tắc").

**Tệp (3):** `k2/sql_module.py` mới (hằng `MODULE_CONG_TAC_SQL`); `ha_tang/pg_migrations.py`; `tests/test_xs4_sql.py` mới.

**Việc:**
1. **Dữ liệu** — ít bảng, thêm dòng, không tạo bảng theo từng module (QD-09):
   - danh mục module: mã, chế độ mặc định. Seed: `CRM`, `M2`, `M4`, `M0` = `VAN_HANH` (S3, module đang dùng); `M3`, `M9`, `M10` = `TAT`. Mã không có trong danh mục → coi như `TAT`.
   - công tắc (module, pháp nhân) → chế độ `TAT`/`THU`/`VAN_HANH`, `revision`, lý do, người đổi, lúc đổi. Chưa có dòng → chế độ mặc định của danh mục.
   - người thử (module, pháp nhân, người dùng), cấp/thu hồi có dấu thời gian. Không xóa dòng; thu hồi = đánh dấu.
   - Nhật ký đổi chế độ: dùng **cơ chế nhật ký có sẵn** (`nhat_ky.su_kien` hoặc helper hiện có). Không tạo bảng nhật ký mới nếu cơ chế sẵn có đủ.
2. **Hàm đọc** `master.module_trang_thai(p_module text, p_pn uuid) RETURNS jsonb`, `STABLE`, chỉ đọc, danh tính từ GUC phiên như các hàm MTQ. Trả cờ:
   - `che_do`, `hien_luoi`, `cho_xem`, `cho_ghi`, `cho_xuat_ngoai`, `cong_bo_chinh_thuc`, `dai_dang_thu`.
   - **VAN_HANH:** mọi cờ true (quyền chi tiết vẫn do ma trận thẩm quyền).
   - **THU:** người thử hoặc Admin → `hien_luoi`, `cho_xem`, `cho_ghi` true; `cho_xuat_ngoai` false; `cong_bo_chinh_thuc` false; `dai_dang_thu` true. Người khác → mọi cờ false.
   - **TAT:** `hien_luoi` false, `cho_ghi` false, `cho_xuat_ngoai` false, `cong_bo_chinh_thuc` false. `cho_xem` true (chỉ đọc dữ liệu đã có, quyền chi tiết vẫn theo ma trận) (S4).
   - `app_web` được EXECUTE; không lộ danh sách người thử.
3. **Hàm đổi** `master.module_doi_che_do(p_module text, p_pn uuid, p_che_do text, p_ly_do text, p_revision_cu bigint) RETURNS bigint`, `SECURITY DEFINER`, `search_path` cố định:
   - chỉ **Admin** đổi, theo cơ chế Admin ma trận hiện có (`master.mtq_admin` hiện hành); không tạo khái niệm Admin mới (S2);
   - lý do bắt buộc; CAS theo revision; ghi nhật ký (ai, lúc nào, từ → sang, lý do).
   - **S5 (bước này):** chuyển sang `VAN_HANH` chỉ được khi module có chế độ mặc định `VAN_HANH`, hoặc ở pháp nhân đó đã từng `VAN_HANH`. Ngoài ra chặn với mã `MODULE_CHUA_DU_DIEU_KIEN_GO_LIVE`. Kiểm bảng điều kiện go-live là lát sau (XS-4b2); không tự mở lối tắt.
   - Hàm cấp/thu hồi người thử: chỉ Admin, có lý do, có nhật ký.
4. **ACL:** `REVOKE PUBLIC`. `app_web` chỉ EXECUTE các hàm, không DML trực tiếp lên bảng mới. RLS hoặc SECURITY DEFINER đúng mẫu repo.
5. **Không** nối Python/HTTP/UI (XS-4c), không đụng bus (cờ "thử" cho sự kiện là lát sau), không sửa `ktt_duoc`/RLS nền/MTQ.

**Test (PG):**
- mặc định S3 cho từng mã;
- ba chế độ × (Admin / người thử / người khác) → đúng từng cờ;
- chỉ Admin đổi được; thiếu lý do / sai revision bị chặn;
- S5: `M9` từ `THU` sang `VAN_HANH` bị chặn đúng mã; `CRM` từ `TAT` về `VAN_HANH` được;
- nhật ký có đủ dòng;
- người thử bị thu hồi mất quyền thấy;
- pháp nhân B không bị ảnh hưởng khi đổi ở A;
- `app_web` không DML được bảng;
- gọi được trong `READ ONLY`.

**Báo cáo (≤ ⅓ trang)**, "Cần lead", thông điệp commit `[XS-4b] …`.
