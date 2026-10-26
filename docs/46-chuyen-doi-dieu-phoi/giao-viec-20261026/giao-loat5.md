# Loạt 5 (27/10 ~00:10) — XS-5a1, XS-T1a, MTQ-NEN-2c, MTQ-4d1b

## Phần chung (mọi lát)

- Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM; `pg_migrations.py` giữ LF.
- **Ghi tệp bằng apply_patch, không qua chuỗi PowerShell nháy kép** (`$$` PL/pgSQL bị mất). Tự kiểm `AS $$`/`$$`.
- Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ hoặc có thể làm rộng quyền: dừng, ghi "Cần lead". Không có `python` thì NOT_RUN; lead chạy test/PG.
- Test PG tự tạo `kho_test_*` (`skipUnless KHO_PG_DSN_TEST`), **chạy dưới vai ứng dụng thật** (`app_web`/danh tính phiên như các test hiện có). Dữ liệu giả đúng trigger/ràng buộc thật; chạy được dưới guard giữ tệp. Không kiểm CRLF/LF.
- Migration: chỉ thêm `M00xx_*` với dấu `# <MÃ LÁT> — …:`; **không tự đặt số**. Không sửa migration cũ (tới M0062). Test không ghim migration cuối.
- QD-20261026-09: không tạo bảng/cột theo từng lần. CD-018: không SQL thẳng bảng module khác; route/dịch vụ không SELECT bảng đã `REVOKE`.

## XS-5a1 · Khai báo vùng dữ liệu theo module (CD-018) + tên nghiệp vụ module

**Căn cứ:** `docs\46-chuyen-doi-dieu-phoi\KK-VUNG-DU-LIEU.md` §1–§3 (bảng/hàm từng module, 4 vùng V1–V4, 70 điểm đọc chéo), §5 dòng 5a1; `ha_tang/khai_bao_module.py` (XS-4a).

**Tệp (3):** `ha_tang/khai_bao_module.py` (mở rộng, giữ API cũ); `k2/vung_du_lieu.py` mới (khai báo dữ liệu của các module đang có); `tests/test_xs5_khai_bao.py` mới.

**Việc:**
1. Kiểu khai báo vùng dữ liệu của một module:
   - V1 ghi riêng (schema/bảng);
   - V2 ghi chung qua hàm xương sống (tên hàm);
   - V3 đọc danh mục chung (bảng);
   - V4 đọc dữ liệu công bố/sự kiện của module khác;
   - danh sách **chỗ đọc/ghi chéo đang tồn tại** (từ KK §3: tệp:dòng, đích, mức) đánh dấu "cần chuyển dần".
2. `vung_du_lieu.py`: khai báo cho CRM, M2, M3, M4, M9, M0, đúng KK §2.
   - Kèm **tên nghiệp vụ** từng module: "Hợp đồng & báo giá", "Hóa đơn mua vào", "Hóa đơn bán ra & doanh thu BĐS", "Nghiệm thu & chi phí dự án", "Vốn vay & đầu tư tài chính", "Lõi".
   - Thêm hàm tra tên dùng được cho `k2/module.py` `trang_thai_cho` (không sửa `module.py` ở lát này).
3. Kiểm hợp lệ:
   - mỗi bảng đúng **một** chủ;
   - V1 của module không trùng V1 module khác;
   - ghi vào bảng của module khác mà không nằm trong danh sách "đang tồn tại" → **đỏ**;
   - chỗ trong danh sách tồn tại → cảnh báo (không đỏ, để chuyển dần).
4. Chưa dựng role PG (XS-5b), chưa nối test SQL thực (XS-5c).

**Test:**
- khai báo hiện có hợp lệ;
- trùng chủ / ghi chéo mới → đỏ;
- tên nghiệp vụ tra được;
- số điểm đọc chéo khớp KK §3 (đếm).

## XS-T1a · Hợp đồng dữ liệu hóa đơn công bố chỉ đọc (CD-017, pilot S6)

**Căn cứ:**
- `KK-XUONG-SONG.md` §2 dòng XS-T1a, §3 (pilot M2→M4);
- `KK-VUNG-DU-LIEU.md` §3 dòng "K2 đối chiếu → M2; 12";
- `XS-4-CAN-CHOT.md` S1/S4/S6;
- M0056 công tắc;
- bảng M2 `kho.hoa_don_*` (P:5240–5492).

**Tệp (3):** `k2/sql_cong_bo_hoa_don.py` mới (hằng `CONG_BO_HOA_DON_SQL`); `ha_tang/pg_migrations.py` (`M00xx_CONG_BO_HOA_DON`, dấu `# XS-T1a — CD-017:`); `tests/test_xst1_cong_bo.py` mới.

**Việc:**
1. Hàm đọc công bố (`STABLE`, `SECURITY DEFINER`, `search_path` cố định, cấp `app_web`). Ví dụ `master.hoa_don_cong_bo(p_pn uuid, p_hoa_don_ids uuid[])` hoặc theo khóa nghiệp vụ hiện có; chọn chữ ký phù hợp nơi tiêu thụ ở `k2/sql_ghi_nhan_chung.py`.
   - Trả: định danh hóa đơn, **phiên bản hiện hành** (id + số phiên bản), **mã băm** nội dung, PN, các trường đầu hóa đơn đang được đối chiếu đọc (số, ký hiệu, ngày, MST bán/mua, tổng tiền giữ nguyên kiểu), trạng thái nguồn/coverage.
   - **Không** trả dòng thô hay nội dung tệp.
2. Kiểm:
   - PN được phép của phiên;
   - **công tắc M2 ở PN đó** (`master.module_trang_thai('M2', pn)`): không `cong_bo_chinh_thuc` → **không trả dòng** mà trả trạng thái `CHO` có lý do "Chờ hóa đơn mua vào" (S4/S6). Người dùng module khác thấy "Chờ", không lỗi.
3. **Không** mở quyền bảng M2 cho `app_web` hay module khác; **không** sửa nơi tiêu thụ (`sql_ghi_nhan_chung.py`) ở lát này (XS-T1b/c).

**Test (PG, vai `app_web`):**
- M2 Vận hành → trả đúng trường + mã băm ổn định;
- M2 Tắt/Thử ở PN A → `CHO`, PN B vẫn trả;
- sai PN không thấy;
- `app_web` không SELECT được bảng `kho.hoa_don_*` qua đường mới;
- gọi được trong `READ ONLY`.

## MTQ-NEN-2c · `mtq_duoc_doc` tiêu thụ phạm vi NGUON (lead giữ nền)

**Căn cứ:**
- `tra-loi-lead-mtq-4i-b1.md` mục 3;
- `tra-loi-lead-mtq-4i-b1-v5.md` (hàm `master.mtq_nguon_ung_vien`, khóa mơ hồ → chỉ PHAP_NHAN);
- M0058 `mtq_duoc_doc` theo tập PN.

**Nhánh này dựng trên `lat/mtq-4i-b1`** (đã có `MTQ_CONG_H_SQL` + helper NGUON, chưa gộp).

**Tệp (3):** `k2/sql_mtq_nen.py` (hằng `MTQ_NEN_C_SQL`); `ha_tang/pg_migrations.py` (`M00xx_MTQ_NEN_C`, dấu `# MTQ-NEN-2c — CD-012:`); `tests/test_mtq_nen_sql.py` (thêm ca).

**Việc:**
- `CREATE OR REPLACE master.mtq_duoc_doc(text,jsonb,numeric)` từ thân **M0058**.
- Chọn phạm vi khớp `NGUON` theo `nguon_khoa` của phần tử tập, **giống hệt** cổng phiên `MTQ_CONG_H_SQL`: ưu tiên trước PHAP_NHAN; khóa mơ hồ → không có NGUON.
- Ca cũ giữ nguyên từng bit. `STABLE`, chỉ đọc, ACL như cũ.

**Test:**
- so `mtq_duoc_doc` với cổng phiên trên cùng ca NGUON (chỉ phạm vi NGUON đúng khóa / sai khóa / mơ hồ / nhiều PN);
- oracle ca cũ;
- `READ ONLY`.

## MTQ-4d1b · CRM · nối ma trận cho phần Python G1 mẫu / G7 bộ chuẩn (KK-MTQ4-CRM §2–§3 dòng 4d1b)

**Căn cứ:**
- `giao-mtq4-chung.md`;
- `KK-MTQ4-CRM.md` §2 các dòng `k2/crm_mau.py`;
- SQL guard đã có: M0050 (G1/G7), M0054/M0058 `mtq_duoc_doc`.

**Tệp (2):** `k2/crm_mau.py`; `tests/test_mtq_giao_ket.py` mới.

**Việc:**
1. **Cờ năng lực** hiện tính bằng `master.crm_g_duoc(...)`/`crm_g_chuan_doc_duoc` (`crm_mau.py` ~dòng 178, 224, 442–452).
   - Khi PN của đối tượng **bật** ma trận → tính bằng `master.mtq_duoc_doc(<khóa CRM:G1_MAU:*/G7_CHUAN:*>, <đối tượng>)` (true/false). Khóa theo KK §2.
   - Khi PN **tắt** (`mtq_duoc_doc` trả NULL) → giữ nguyên `crm_g_duoc` cũ.
   - Không `cũ OR mới`.
2. **Đọc/tải mẫu** (`tep_mau`, `chi_tiet`): kiểm quyền trước khi đọc blob/replay theo cùng quy tắc. SQL M0050 đã chặn ở máy chủ; Python chỉ không để lộ cờ sai và không đọc blob trước kiểm.
3. Không đổi SQL, không đổi route. Câu từ chối tiếng Việt nghiệp vụ.

**Test (PG):**
- PN tắt: cờ và kết quả như cũ (oracle);
- PN bật: người có/không có ô → cờ đúng;
- tải mẫu bị chặn trước khi đọc blob;
- PN A bật không đổi PN B tắt.

**Báo cáo (≤ ¼ trang) mỗi lát**, "Cần lead", thông điệp commit `[<MÃ LÁT>] …`.
