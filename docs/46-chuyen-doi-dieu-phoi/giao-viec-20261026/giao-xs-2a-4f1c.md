# Loạt 4 — XS-2a (hàng việc nền dùng chung) và MTQ-4f1c (M4 đọc/master + B6)

Phần chung cho cả hai lát:
- Ghi UTF-8 không BOM; `pg_migrations.py` giữ LF. **Ghi tệp bằng apply_patch, không qua chuỗi PowerShell nháy kép** (`$$` PL/pgSQL bị mất).
- Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ hoặc có thể làm rộng quyền: dừng, ghi "Cần lead". Không có `python` thì NOT_RUN; lead chạy PG.
- Test PG tự tạo `kho_test_*` (`skipUnless KHO_PG_DSN_TEST`), dữ liệu giả đúng trigger/ràng buộc thật, chạy được dưới guard giữ tệp. Không kiểm CRLF/LF trên tệp nguồn.
- Migration: chỉ thêm `M00xx_*` với dấu `# <MÃ LÁT> — …:`. Không sửa migration cũ (tới M0057). Test không ghim migration cuối.
- QD-20261026-09: không tạo bảng/cột theo từng lần; dữ liệu tạm có hạn giữ khai báo được.

## XS-2a · SQL hàng việc nền dùng chung (CD-017)

**Căn cứ:**
- TL 53;
- `KK-XUONG-SONG.md` §1 dòng XS-2 (mẫu sẵn có: G5 CRM `k2/sql_crm_doi_chieu.py:183,484,511,637,688` — SKIP LOCKED, lease, CAS, thử lại) và §5 rủi ro;
- `KK-DON-DEP.md` §1 (lease/việc xong: hạn giữ, không xóa việc mở/`CHUA_RO`);
- M0052 bus, M0056 công tắc module.

**Tệp (3):** `k2/sql_hang_viec.py` mới (hằng `HANG_VIEC_SQL`); `ha_tang/pg_migrations.py` (`M00xx_HANG_VIEC`, dấu `# XS-2a — CD-017:`); `tests/test_xs2_sql.py` mới.

**Việc:**
1. **Một bộ bảng chung** (schema gợi ý `viec`; ghi rõ docstring):
   - việc gồm: module chủ, loại việc + phiên bản, pháp nhân, khóa chống trùng do bên tạo cấp, tham chiếu/ID (không chứa nội dung chứng từ), trạng thái, số lần thử, hạn thử lại, lease (người giữ, hạn), tiến độ, yêu cầu dừng, kết quả tham chiếu, mã lỗi;
   - trạng thái: `CHO` / `DANG_CHAY` / `XONG` / `LOI` / `DA_DUNG` / `CHUA_RO`;
   - nhật ký chuyển trạng thái dùng cơ chế nhật ký có sẵn, hoặc một bảng sự kiện việc chung nếu cần. Không tạo bảng theo module.
2. **Hàm SQL** (`SECURITY DEFINER`, `search_path` cố định, ACL `REVOKE PUBLIC` + `EXECUTE` cho `app_web`):
   - tạo việc **trong giao dịch của bên gọi**, chống trùng theo khóa;
   - nhận việc `FOR UPDATE SKIP LOCKED` có lease, **không nhận khi công tắc module (M0056) không cho ghi ở PN đó**;
   - gia hạn lease; cập nhật tiến độ; kết thúc bằng CAS theo lease (lease hết/khác người giữ → từ chối);
   - yêu cầu dừng hợp tác;
   - thử lại có giới hạn/khoảng chờ;
   - lease hết hạn → chuyển việc về trạng thái có thể nhận lại **hoặc** `CHUA_RO` nếu việc đánh dấu "có tác động ngoài" (không tự chạy lại việc có thể đã gây tác động).
3. Pháp nhân theo RLS/hàm sẵn có; **không sửa** `ktt_duoc`/`ktt_pn_cho_phep`. Không đụng các hàng việc cũ (G5, M4 review/chứng từ, Request, bộ tải M2). Chuyển chúng là việc khi chạm tới (QD-09).
4. Có cột/khai báo phục vụ hạn giữ (thời điểm kết thúc) để lát dọn dẹp sau dùng; **không** viết lệnh xóa.

**Test (PG):**
- tạo trong giao dịch rollback → không có;
- trùng khóa → một việc;
- hai worker tranh nhận → một người được;
- lease hết → người khác nhận được, người cũ kết thúc bị từ chối;
- việc "có tác động ngoài" hết lease → `CHUA_RO`;
- dừng hợp tác;
- thử lại đến giới hạn → `LOI`;
- module TẮT ở PN A → không nhận việc mới của A, PN B vẫn nhận;
- sai PN không thấy;
- ACL.

## MTQ-4f1c · M4 · Nghiệm thu & chi phí dự án — SQL đọc/master + B6 (KK-MTQ4-M4 §2–§3 dòng 4f1c)

**Căn cứ:**
- `giao-mtq4-chung.md` (nguyên tắc quyền: PN tắt giữ CU từng bit; PN bật chỉ theo ma trận; không `cũ OR mới`);
- `KK-MTQ4-M4.md` §1–§3;
- QD-20261026-08 **B6** (tải mẫu/bộ chọn master = `M4:HO_SO:LAP` theo dự án; không dự án → chặn);
- đã có: M0048 resolver M4, M0054 `mtq_duoc_doc` (chỉ đọc, có số tiền), M0055 guard lệnh hồ sơ (`m4/sql_mtq.py`), M0057 cổng tập PN.

**Tệp (3):** `m4/sql_mtq.py` (thêm hằng `MTQ_M4_B_SQL`, không đổi `MTQ_M4_A_SQL`); `ha_tang/pg_migrations.py` (`M00xx_MTQ_M4_B`, dấu `# MTQ-4f1c — CD-012:`); `tests/test_mtq_m4_doc_sql.py` mới.

**Việc:**
1. **Đọc khi PN bật:** RLS/hàm đọc M17 (hồ sơ, tệp, tham số, phụ lục, BOQ, đợt), RLS restrictive HĐ, hàm master M28 (`mc_co_ho_so`, `master_hop_dong_ds`, `master_doi_tac_ds`, `master_can_cu_doc`), review chép M38/M40 → lọc từng dòng bằng `master.mtq_duoc_doc` với đúng khóa `M4:*:XEM` theo KK §2.
   - Danh sách, số đếm, chi tiết cùng một quy tắc.
   - **Không** mở HĐ CRM.
   - PN tắt → giữ nguyên đường cũ.
2. **B6:** bộ chọn master và tải mẫu = `M4:HO_SO:LAP` theo dự án; không có dự án → chặn.
3. Policy/RLS **của bảng m4** được đổi qua migration mới (DROP/CREATE POLICY có tên). **Không** sửa `ktt_duoc`/`ktt_pn_cho_phep`/RLS nền dùng chung.
   - Phần nào chỉ làm được bằng cách đổi RLS nền → "Cần lead".
   - Phần "bộ chọn" chưa rõ khóa → "Cần lead", không đoán.
4. Thông báo từ chối: tiếng Việt nghiệp vụ, không khóa kỹ thuật.

**Test (PG):**
- PN tắt: so oracle đường cũ (số dòng, chi tiết, số đếm);
- PN bật: người có/không có `M4:HO_SO:XEM` theo phạm vi dự án/HĐ thấy đúng tập dòng, số đếm khớp danh sách;
- B6 có/không dự án;
- HĐ CRM không lộ;
- PN A bật không đổi PN B tắt;
- gọi được trong `READ ONLY`.

**Báo cáo (≤ ⅓ trang) mỗi lát**, "Cần lead", thông điệp commit `[XS-2a] …` / `[MTQ-4f1c] …`.
