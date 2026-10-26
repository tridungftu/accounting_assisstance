# XS-2a2 · Hàm đọc trạng thái lease/yêu cầu dừng cho worker (CD-017) — mở chặn XS-2b

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM; `pg_migrations.py` giữ LF. **Ghi tệp bằng apply_patch, không qua chuỗi PowerShell; tự kiểm `AS $$`/`$$`.**
- Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không có `python` thì NOT_RUN; lead chạy PG.
- Test PG dưới vai ứng dụng (`app_web`) như `tests/test_xs2_sql.py`; dữ liệu giả; chạy được dưới guard.
- Migration: chỉ thêm `M00xx_HANG_VIEC_B`, dấu `# XS-2a2 — CD-017:`. Không sửa M0060.

**Lý do:** XS-2b (worker) dừng "Cần lead": M0060 (`k2/sql_hang_viec.py`) không có hàm công khai để người giữ lease đọc `yeu_cau_dung`. `gia_han`/`tien_do` trả boolean; `viec._giu` không cấp `app_web`. Worker không được SQL thẳng bảng.

**Tệp (3):** `k2/sql_hang_viec.py` (thêm hằng `HANG_VIEC_B_SQL`, không đổi `HANG_VIEC_SQL`); `ha_tang/pg_migrations.py`; `tests/test_xs2_sql.py` (thêm ca, giữ ca cũ).

**Việc:**
- Hàm `viec.trang_thai_lease(p_pn uuid, p_id uuid, p_worker uuid, p_token uuid) RETURNS jsonb`, `STABLE`, `SECURITY DEFINER`, `search_path` cố định, cùng kiểm quyền/PN như các hàm M0060 (`viec._kiem_quyen`).
- Trả `{"con_giu": bool, "yeu_cau_dung": bool, "het_han_luc": timestamptz|null, "trang_thai": text}`.
  - Chỉ người giữ đúng (worker, token) còn hạn mới nhận `con_giu=true` và cờ dừng thật.
  - Người khác/token sai → `con_giu=false`, các trường khác NULL. Không lộ thông tin việc của người khác.
- Không ghi, không lấy khóa. ACL: `REVOKE PUBLIC`, `EXECUTE` cho `app_web`.

**Test (PG, vai `app_web`):**
- người giữ thấy `yeu_cau_dung` sau khi `viec.yeu_cau_dung` được gọi;
- token sai / worker khác / lease hết → `con_giu=false`, không lộ;
- sai PN → bị chặn như M0060;
- gọi được trong `READ ONLY`.

**Báo cáo (≤ ¼ trang)**, "Cần lead", thông điệp commit `[XS-2a2] …`.
