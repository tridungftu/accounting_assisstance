# MTQ-NEN-0 · Luồng CỔNG (lead giữ, A2/A3) · tách resolver của cổng phiên thành hàm dùng chung chỉ đọc

(Đọc trước `giao-mtq4-chung.md`. Lát này giữ `k2/sql_mtq_cong.py`.)

**Lý do:** MTQ-NEN-1 cần quyết định **chỉ đọc** cho lọc danh sách (A3). Resolver (bảng → `pn`/HĐ/DA/LH/khách + whitelist cặp bảng–lệnh) đang nằm trong thân `master.mtq_quyet_dinh_phien` (M0048). Lõi M0039 có INSERT nhật ký rồi hoàn tác, nên không dùng được trong `READ ONLY`.

**Việc:** migration mới, tên tạm `M00xx_MTQ_CONG_F`, `CREATE OR REPLACE` dựa trên thân **M0048**.
1. Hàm mới `master.mtq_giai_doi_tuong(p_hanh_dong text, p_doi_tuong jsonb) RETURNS jsonb`:
   - `LANGUAGE plpgsql STABLE SECURITY DEFINER`, cùng `search_path` với cổng;
   - **không** ghi gì;
   - trả `{pn, hd, da, lh, khach, phong, hop_le (bool), ma, ly_do, loai, man, module}`;
   - chứa **nguyên** phần giải đối tượng + whitelist đang có trong `mtq_quyet_dinh_phien` (M0045/M0047/M0048), không đổi logic;
   - ACL: `REVOKE PUBLIC`; `EXECUTE` cho `app_web` giống cổng.
2. `mtq_quyet_dinh_phien` và `mtq_ghi_tu_choi_phien` gọi `mtq_giai_doi_tuong` thay cho khối giải nội tuyến. **Kết quả phải giống hệt từng bit** với M0048 trên mọi ca (cùng `ma`/`ly_do`/`nguon`).
3. Không đổi lõi M0039, catalog, chữ ký/ACL hai hàm cổng.

**Test, tệp mới `tests/test_mtq_cong_f_sql.py`:**
- PG, tự tạo CSDL: chạy lại **toàn bộ ca** của `test_mtq_cong_c_sql`, `test_mtq_crm_resolver_sql`, `test_mtq_m4_resolver` (import và chạy lại, hoặc so bảng kết quả trước/sau trên cùng dữ liệu). Kết quả cổng không đổi.
- `mtq_giai_doi_tuong` gọi được trong `SET TRANSACTION READ ONLY`, không tạo dòng nhật ký.
- Phần tĩnh: không SQL động; ACL.

**Tệp (3):** `k2/sql_mtq_cong.py` (hằng `MTQ_CONG_F_SQL`), `ha_tang/pg_migrations.py`, `tests/test_mtq_cong_f_sql.py`.

**Mã lát:** MTQ-NEN-0, nhánh `lat/mtq-nen-0`.
