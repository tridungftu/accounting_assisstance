# Loạt 3 sau chốt MTQ-4 — phần riêng (ghép với `giao-mtq4-chung.md`)

**Đã có trên nhánh hợp nhất (migration cuối M0053):**
- M0047 resolver CRM;
- M0048 resolver M4 (4f1a);
- M0049 phạm vi NGUON (4i-a);
- M0050 guard CRM G1/G7 (4b1b);
- **M0051**: resolver cổng đã tách thành hàm nội bộ `master.mtq_giai_doi_tuong(text,jsonb)`, `STABLE`, **không** cấp `app_web`. Hai cổng phiên gọi hàm này;
- M0052 bus sự kiện;
- M0053 guard CRM G2/G3 (4b2a).

Thêm nhánh resolver từ nay = `CREATE OR REPLACE master.mtq_giai_doi_tuong` dựa trên **thân M0051 hiện hành**. Giữ `STABLE`, chỉ đọc, ACL như cũ, không cấp `app_web`. Không chép lại thân hai cổng phiên nếu không cần.

## MTQ-4f1b · Luồng M4 · SQL hồ sơ/lệnh M17 (KK-MTQ4-M4 §2–§3 dòng 4f1b)

**Tệp (3):**
- `m4/sql_mtq.py` mới (hằng `MTQ_M4_A_SQL`);
- `ha_tang/pg_migrations.py`: `M00xx_MTQ_M4_A`, dấu `# MTQ-4f1b — CD-012:`;
- `tests/test_mtq_m4_ho_so_sql.py` mới.

**Việc:**
- Thay kiểm vai/`m4_duoc` cũ trong **từng lệnh hồ sơ M17** bằng gọi cổng phiên khi PN bật. Lệnh: tạo hồ sơ HĐ, ghi/gắn tệp, trích xuất, sửa/xác nhận tham số, phụ lục, BOQ, đợt, nộp. Phạm vi lệnh lấy từ KK-MTQ4-M4 §2.
- Phủ cả đường ghi tin cậy **và replay**: kiểm trước replay/CAS/ghi.
- Khi bật, không giữ `_SOAN` hay vai cũ làm nguồn quyền thứ hai. Không `cũ OR mới`.
- Dùng resolver M0048 (DA/HD/T/D…). HĐ chỉ `module_chu='M4'`, không mở HĐ CRM.
- **Không** đụng RLS đọc/master (lát 4f1c), 02A/02B (4f2), 02C (4f3).
- **Không** thêm Duyệt có tiền.
- PN tắt → so oracle đường cũ (cho/chặn + mã lỗi). Bật ở PN A không đổi kết quả PN B đang tắt.

## MTQ-4i-b1 · Luồng CỔNG · resolver nguồn rS và ánh xạ rA (KK-MTQ4-LIEN-MODULE §1–§3 dòng 4i-b1)

**Tệp (3):**
- `k2/sql_mtq_cong.py`: hằng mới `MTQ_CONG_G_SQL`, `CREATE OR REPLACE master.mtq_giai_doi_tuong` từ thân M0051;
- `ha_tang/pg_migrations.py`: `M00xx_MTQ_CONG_G`, dấu `# MTQ-4i-b1 — CD-012:`;
- `tests/test_mtq_lmod_resolver_sql.py` mới.

**Việc:**
- Thêm hai nhánh resolver, mỗi nhánh whitelist **đúng cặp (bảng, khóa catalog)** theo KK-MTQ4-LIEN-MODULE §2:
  - **rS** = phạm vi nguồn/profile (`master.nguon_pham_vi`, `master.nguon_profile`) → pháp nhân/phòng + phạm vi NGUON theo **A1 / M0049**;
  - **rA** = ánh xạ nguồn (`master.anh_xa_nguon`) → PN đích xác thực, gồm cả PN cũ và mới khi đổi đích.
- Nguồn hoặc ánh xạ chạm **nhiều pháp nhân** phải đủ quyền ở **mọi** pháp nhân liên quan (A1).
  - Hàm giải hiện chỉ trả một PN và không biểu diễn được nhiều PN → **dừng, ghi "Cần lead"** kèm phương án. Không tự chọn một PN.
- Cổng hỏi và cổng ghi từ chối dùng **cùng** đối tượng giải được (audit đúng PN).
- Giữ QD-03: HĐ thuộc CRM không bị mở qua nhánh mới.
- Chưa nối caller M2/M5/L11 (để 4i-c…).
- Các nhánh cũ (M0045/M0047/M0048/M0051) giữ nguyên. Test so thân nhánh cũ không đổi.
- `app_web` vẫn không EXECUTE hàm giải.

## MTQ-4b2b · Luồng CRM · G4 ký/đọc bản ký + phạm vi hẹp B3 (KK-MTQ4-CRM §2–§3 dòng 4b2b)

**Tệp (3):**
- `k2/sql_mtq_crm.py`: thêm hằng `MTQ_CRM_C_SQL`, **không** đổi `MTQ_CRM_A_SQL`/`MTQ_CRM_B_SQL`;
- `ha_tang/pg_migrations.py`: `M00xx_MTQ_CRM_C`, dấu `# MTQ-4b2b — CD-012:`;
- `tests/test_mtq_crm_sql.py`: thêm ca, giữ ca cũ.

**Việc:**
- Khi PN bật, thay kiểm vai/assignment cũ trong các hàm sau bằng gọi cổng phiên:
  - `crm_ky_dich/tra/ket` (ký) → `CRM:G3_G4_SOAN_KY:LAP`;
  - `crm_ky_doc` (metadata) → `CRM:G3_G4_SOAN_KY:XEM`;
  - `crm_ky_tep` (bản ký) → `CRM:BAN_KY:XEM`;
  - các trigger liên quan, theo KK-MTQ4-CRM §2.
- **B3 (Anh đã chốt):** phạm vi người ký/đọc bản ký do Admin cấp theo **HĐ hoặc dự án**. Giữ ràng buộc khách hàng và phiên bản (digest đúng revision). **Không nới thành cả pháp nhân.**
  - Phạm vi MTQ hiện có không biểu diễn được HĐ/dự án → **dừng, ghi "Cần lead"** kèm phương án. Không tự thêm loại phạm vi mới vào lõi M0039.
- Không suy `BAN_KY:XEM` từ quyền ký hay XEM hồ sơ. Ghi nhật ký truy cập trước khi trả hash/bytes.
- Dùng resolver S/K của M0047.
- Không đụng G5/G6 (4e1a…), tỷ giá (B1), V8 (B2).
- **Thêm (lead, sau review 4f1b):** thông báo từ chối khi PN bật của helper guard M0050/M0053 (`RAISE EXCEPTION '%: không có quyền hiện hành cho %', …, lenh`) đang đưa khóa catalog (ví dụ `CRM:G2_BAO_GIA:SUA`) ra người dùng.
  - Trong `MTQ_CRM_C_SQL`, `CREATE OR REPLACE` các helper đó.
  - Giữ tiền tố mã máy đọc. Phần câu chuyển sang tiếng Việt nghiệp vụ, không chứa khóa/tên bảng/UUID.
  - **Không** đổi thông báo của đường cũ khi PN tắt (CU giữ nguyên từng bit).
  - Test thông báo.
- PN tắt → so oracle đường cũ (cho/chặn + mã lỗi). Bật ở PN A không đổi kết quả PN B tắt.
