# Loạt 1 sau chốt MTQ-4 — phần riêng từng lát (ghép với `giao-mtq4-chung.md`)

## MTQ-4f1a · Luồng CỔNG · resolver phạm vi M4 (KK-MTQ4-M4 §2 dòng 4f1a)

**Tệp (3):**
- `k2/sql_mtq_cong.py`: thêm hằng `MTQ_CONG_E_SQL`, **CREATE OR REPLACE** hai cổng phiên dựa trên thân **M0047** hiện tại;
- `ha_tang/pg_migrations.py`: `M00xx_MTQ_CONG_E`;
- `tests/test_mtq_m4_resolver.py` mới.

**Việc:**
- Thêm whitelist đối tượng M4 theo KK-MTQ4-M4 §1 (ký hiệu DA/HD/T/D/R/C/V/K/P/A/Q). Mỗi đối tượng giải qua FK thật, chỉ ghép với khóa catalog `M4:*` của màn sở hữu.
- **Không** mở HĐ CRM. **Không** mở cặp mới trên `master.hop_dong` ngoài HĐ `module_chu='M4'`.
- K (kết luận) chỉ giải phạm vi, **chưa** cho Duyệt có tiền (để 4f3a).
- B6: tải mẫu/bộ chọn master = `M4:HO_SO:LAP` theo dự án; không có dự án → chặn.
- Các nhánh M0045/M0047 giữ nguyên. Test so thân hàm.

## MTQ-4b1b · Luồng CRM · guard SQL G1/G7 (KK-MTQ4-CRM §3 dòng 4b1b)

**Tệp (3):**
- `k2/sql_mtq_crm.py` mới (hằng `MTQ_CRM_A_SQL`);
- `ha_tang/pg_migrations.py`: `M00xx_MTQ_CRM_A`;
- `tests/test_mtq_crm_sql.py` mới.

**Việc:**
- Thay kiểm vai cũ trong các hàm/trigger SQL của **G1 mẫu và G7 bộ chuẩn** (KK-MTQ4-CRM §2) bằng gọi cổng phiên khi pháp nhân bật; giữ đường cũ khi tắt.
- Dùng resolver M0047 sẵn có.
- Giữ tách nhiệm: người duyệt mẫu khác người kiểm; người duyệt bộ chuẩn khác người lập/gửi.
- RLS đọc theo màn **chỉ** nếu không phải RLS nền dùng chung. Đụng RLS nền thì "Cần lead".
- Không đụng G2/G3/G4/G5/G6, tỷ giá.

## MTQ-4i-a · Luồng LIÊN MODULE · phạm vi nguồn (A1) (KK-MTQ4-LIEN-MODULE §2 dòng 4i-a)

**Tệp (3):**
- `k2/sql_mtq_lien_module.py` mới (hằng `MTQ_LMOD_A_SQL`);
- `ha_tang/pg_migrations.py`: `M00xx_MTQ_LMOD_A`;
- `tests/test_mtq_nguon_scope_sql.py` mới.

**Việc:**
- Theo **A1 đã chốt**: phạm vi loại NGUON do Admin cấp tường minh theo (profile/instance, công ty nguồn) → pháp nhân/phòng. Hiện M0039 chặn NGUON ở khoảng `sql_ma_tran_tham_quyen.py:247–249`.
- Append validator cho phép cấp/thu hồi phạm vi NGUON có kiểm hợp lệ, có audit.
- Nguồn gộp nhiều pháp nhân phải có phạm vi ở **mọi** pháp nhân liên quan.
- Không sửa hằng M0039; dùng `CREATE OR REPLACE` hàm validator trong migration mới nếu cần, giữ ACL.
- Chưa nối caller M2/M5 (để 4i-c…).

## MTQ-NEN-1 · Luồng NỀN (lead giữ, A2/A3) · hàm quyết định chỉ đọc

**Tệp (3):**
- `k2/sql_mtq_nen.py` mới (hằng `MTQ_NEN_A_SQL`);
- `ha_tang/pg_migrations.py`: `M00xx_MTQ_NEN_A`;
- `tests/test_mtq_nen_sql.py` mới.

**Việc:**
- Theo **A3**: thêm hàm quyết định **chỉ đọc**, không INSERT nhật ký, dùng được trong giao dịch `READ ONLY` và trong hàm `STABLE`, để lọc danh sách/RLS. Kết quả phải **cùng** quyết định với lõi M0039 cho cùng đầu vào.
- Cách làm đề xuất: tách phần tính quyết định thuần của lõi `master.mtq_quyet_dinh` thành hàm mới (CREATE FUNCTION mới, **không** đổi hành vi hàm cũ), rồi hàm boolean `master.mtq_duoc_doc(hanh_dong text, doi_tuong jsonb)`.
  - Danh tính lấy từ GUC phiên như cổng.
  - Đối tượng giải bằng **cùng whitelist** với cổng. Không chép logic resolver: nếu không gọi lại được mà không ghi thì "Cần lead" và nêu phương án.
- PN tắt → trả kết quả theo nguyên tắc CU do bên gọi xử lý (ghi rõ hợp đồng trả về).
- Test: trong `SET TRANSACTION READ ONLY` gọi được; kết quả khớp lõi trên ma trận ca; không ghi dòng nhật ký nào.
- **Không** sửa `ktt_duoc`/RLS nền ở lát này.
