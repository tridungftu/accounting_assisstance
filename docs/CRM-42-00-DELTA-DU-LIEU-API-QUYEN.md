# CRM-42-00 · Delta dữ liệu – API – quyền và handoff coding (artifact 2/2)

**Gói:** CRM-42-00 (DOCS_ONLY). Ngày 20/10/2026.
**Đi kèm:** `docs/CRM-42-00-MA-TRAN-MAN-HINH-VA-CA-KIEM.md` (gọi tắt "A1"). Mọi mã G/E/S/T/V/W/D/MENU dẫn từ đó.
**Căn cứ:** như A1 §0.
- Hàng chờ: bản 92 dòng, SHA256 `6c344ab8b9f9f7cfe61b2a611b9ea3218db5b94e9a7efd1e89fdb26eddaf4c15`.
- Source baseline: đọc tĩnh, không chạy.
- M4: PARTIAL_FROZEN_NOT_ACCEPTED — Root đã freeze 285 file và review tĩnh; interface cuối cần repair/kiểm, chưa nghiệm thu.

**Kết quả tối đa:** `SCREEN_SCHEMA_DELTA_READY_FOR_ROOT_REVIEW`.
- Tài liệu này **không** có SQL chạy được.
- **Không** có migration nào đã được tạo hay chạy cho CRM.
- CRM chưa code, chưa kiểm, chưa nghiệm thu theo 41/42.

**Nhãn:**
- `HIEN_CO`: có trong source baseline, kèm file:dòng hoặc file:hàm.
- `DE_XUAT`: đề xuất cần Root review.
- `CHO_DAU_VAO`: chờ mẫu, quyết định hoặc interface M4 freeze.

Seed, mock và DEMO **không** được coi là khả năng production.

---

## 1. Hiện trạng có căn cứ (HIEN_CO)

### 1.1 Dữ liệu master và kho

| Đối tượng | Bằng chứng | Nội dung đang có | Ghi chú cho delta |
|---|---|---|---|
| `master.hop_dong` | `pg_migrations.py:301–317`; FK cùng PN `1265–1268`; `UNIQUE (phap_nhan_id,id)` `1742`; trigger `hop_dong_kiem` `1296–1319` | PN, loại (XAY_DUNG/THUE_DAT/BAN_NHA/…), mã nội bộ, số HĐ, đối tác, dự án, loại hình, ngày ký, giá trị minor + currency, trạng thái, `phien_ban_hien_hanh` | Chưa có các trường: trạng thái giao kết, origin MAU, version mẫu, người phụ trách, lô/căn. **Lưu ý:** M0017 của M4 (PARTIAL_CODE) thêm `module_chu` và policy RESTRICTIVE trên bảng này. CRM delta phải bind trên baseline sau khi Root freeze M4. |
| `master.hop_dong_phien_ban` | `318–333`; cột thêm `975–984`; nguồn check có `BAN_HANG` `973–974`; trạng thái thêm `THAY_THE` `1252–1254` | Phiên bản gốc/PL, nguồn, trạng thái, kiem_boi/luc/van_tay, người duyệt, valid_from/to, thay_cho, ngày hiệu lực, profile pin trong `tham_so` | Nguồn **chưa** có `MAU`; chưa có liên kết tới mẫu/render/bản ký. |
| Trigger `master.phien_ban_kiem_duyet` | `2469–2558` | Với HĐ không phải VAY: chuyển sang **DA_DUYET/TU_CHOI chỉ khi CFO có V3** (`2555–2558`); kiểm KT qua vân tay | **Đây là guard khiến luồng A không thể chỉ đổi quyền Python** (§3.4). |
| `master.hop_dong_tham_so` | `336–348`; cột thêm `986–1002`; trạng thái căn cứ mở rộng `1256–1260` | Giá trị hiệu lực/thô, typed, Điều/Khoản, trích dẫn, vị trí, trạng thái căn cứ, `nguon` (mặc định TAY), `xac_nhan_thu_cong`, kế thừa | `nguon` hiện ghi `TRICH_6` (`crm.py:252–257`); chưa có giá trị MAU/NHAP_TAY theo từng tham số; chưa có mức quan trọng. |
| `master.lich_thu` | `349–361`; cột thêm `1004–1010` | Đợt, mốc, tiền minor, currency, hạn, loại COC/DOT/PHI_KY, trạng thái thu, khóa nghĩa vụ, `nguon_tham_so[]`, `co_so`, ghi chú | Chưa có %, thứ tự, loại mốc (ngày/sự kiện) tường minh hay FX tham chiếu. |
| `kho.lien_ket_chung_tu` | `550–567` + guard `2964–2967` | Link tiền ↔ đợt; idempotency; guard VUOT_TIEN_KHA_DUNG / VUOT_NGHIA_VU | Giữ nguyên. |
| `kho.viec_can_duyet` (K5) | `569–589` | V1–V8, tham chiếu bảng/id, trạng thái, người duyệt vai, unique một việc mở | Tái dùng cho W1–W9; **không** dựng bộ duyệt riêng. |
| `kho.cong_no_mo` | `261–280` | Sổ Junsky đã nạp: ngày chụp, TK, đối tượng Junsky, số tiền, dự án | Nguồn cho ô "Công nợ ghi sổ Junsky". RLS/grant cho vai Bán hàng **chưa kiểm** trong lượt đọc này → CHO_DAU_VAO Root xác nhận. |
| PII | `master.doi_tac.cccd_hash/cccd_mh` `92–93`; `doi_tac_dinh_danh` `118–133`; `tai_khoan_ngan_hang.stk_mh` `140` | Cột mã hóa (bytea) + hash | Chưa có log truy cập hay chính sách mở theo vai/mục đích. |
| Quyền | `master.nguoi_dung.vai_tro` gồm KE_TOAN, KE_TOAN_TRUONG, CFO, NHAP_JUNSKY, XEM, BAN_HANG, DU_AN (`968`); `master.phan_quyen.module[]` `971`; `ktt_duoc` / `ktt_co_vai` `1236–1246` | Quyền theo PN + module + vai + loại việc | Chưa có cơ chế **gán hành động** tách khỏi vai (cần cho Pháp chế). |

### 1.2 Service, adapter, HTTP, UI

| Thành phần | Bằng chứng | Hành vi |
|---|---|---|
| Nhận kết quả #6 | `crm.py:112–150`; adapter `nguon/trich_hop_dong_6.py:1–98` | Nhận **JSON** `*_KET_QUA.json` (khóa `hop_dong, che_do, tham_so[]…`), giữ raw + hash, envelope (PN, loại hình, mã HĐ, đối tác, dự án). **Không** tự chạy engine. |
| Lập hồ sơ / phiên bản / tham số | `crm.py:152–258` | Tạo `master.hop_dong` CHO_DUYET + phiên bản 1 + tham số; mở việc V4/V3; phụ lục tạo phiên bản mới. Nguồn phiên bản là `BAN_HANG` (vai bán hàng) hoặc `TRICH_6`. |
| Phân tích theo profile | `crm_phan_tich.py:206–289` (`tong_hop`), `297` (`so_sanh_phu_luc`); `SCALE {"VND":0,"USD":2}` dòng 18 | Field chuẩn + lịch tường minh + chặn. VND/USD exact minor. **Không** phải nghiệp vụ FX. Lịch theo % thì chặn `LICH_TY_LE_THIEU_CO_SO`. |
| Profile DEMO | `loai_hinh_demo.py:17–62` | KCN thuê đất / nhà ở, có ghi rõ "giả định mô phỏng". **Không** phải mẫu/bộ chuẩn đã CFO duyệt. |
| Kiểm / duyệt B | `kiem_truoc` `450–472`; `duyet_v4` `474–488`; `duyet` `490–533`; `tu_choi` `535–546` | KT kiểm có vân tay; CFO V3 (+V4 với HĐ mới) duyệt → sinh `lich_thu`, cập nhật hợp đồng hiện hành. |
| Mapping / xác nhận tay | `402–427`, `429–448`; vô hiệu kiểm `300–308` | Đổi mapping/xác nhận thì lần kiểm hết hiệu lực. |
| Fact cho M1 | `555–581` | Chỉ đọc phiên bản **DA_DUYET**, khoảng hiệu lực, phần còn phải thu. |
| Nối / gỡ tiền | `583–650` | Quyền trước replay; khóa HĐ; idempotency; chỉ nối đợt thuộc phiên bản hiệu lực hôm nay. |
| File soát | `661–720` | Một HĐ, 4 sheet; sổ đăng ký `kho.lo_xuat`; hash. |
| Tra cứu | `723–789` | Danh sách theo PN + XEM; tiền chỉ khi XEM_TIEN. |
| Quyền Python | `k2/quyen.py:14–48` | HANH_DONG CRM: XEM, NOP_HOP_DONG, MAPPING, BO_SUNG_HO_SO, KIEM_TRUOC, DUYET (CFO+V3), DUYET_V4, XUAT_FILE_SOAT, XEM_TIEN, NHAN_TIEN, LIEN_KET_TIEN. |
| HTTP | `server.py:159–311` (`crm_phien`, `crm`, `crm_body`, `crm_state`, `_crm_db`, `_crm_action`), `424–433` (file, nhận) | Phiên cookie do máy chủ cấp; cấm actor/PN/trạng thái từ body; DB error → mã. |
| UI | `giao_dien/assets/index.html:70–83` (`#hopdong`) + `app.js` CRM | **Một trang DEMO**, chưa có menu riêng hay 9 màn. |

### 1.3 Engine (seam với M4)

- Baseline M4 (`m4/nguon_review.py`, PARTIAL_CODE) đang bọc `TrichXuat.xu_ly`, catalog 37 mã XD, BOQ, projection.
- Đã freeze partial nhưng chưa kiểm runtime hoặc chốt interface sau repair → mọi nối E1–E5 vẫn **CHO_DAU_VAO**; snapshot không phải interface đã đạt.
- CRM không import file M4 đang viết; không sửa app nguồn.

---

## 2. Nguyên tắc delta (giữ khi code)

1. **Một master.** Luồng A ghi vào cùng `master.hop_dong` / `hop_dong_phien_ban` / `hop_dong_tham_so` / `lich_thu` như luồng B; phân biệt bằng origin và nguồn từng tham số (41 §0, TL35 §5.10 "một nguồn duy nhất").
   - Không tạo master, auth, approval hay sổ thu song song.
2. **Ba path quyết định tách riêng:** TPL-APPROVE (CFO+V4), A-EFF (KT), B-APPROVE (CFO+V3, giữ nguyên).
3. **Bất biến có revision/hash:** mẫu, field map, bộ chuẩn, báo giá đã in, bản xuất, bản ký, kết quả đối chiếu, quyết định chọn mẫu. Lịch sử chỉ thêm (TL35 §3A).
4. **NULL ≠ 0.** Không suy %/VAT/FX từ tổng. Mốc chưa có ngày không quá hạn. FX báo giá không phải căn cứ thanh toán và không mở đường nối BANK VND vào nghĩa vụ USD.
5. **Quyền kiểm ở CSDL và service**, trước replay hay đọc tệp. Trình duyệt không gửi actor/PN/trạng thái/cờ duyệt. PII theo kiến trúc mã hóa chung (TL38 §9.4).
6. **Không nhập policy chưa chốt:**
   - Không hardcode 50/10/20.
   - Không tự đổi luồng B.
   - Không tự chọn đường trả lại/thay bằng chứng.
   - Không tự cấp grant cho tài khoản thật.

---

## 3. Delta dữ liệu (DE_XUAT — mô tả entity, ràng buộc, owner path; không phải SQL)

Số migration bind sau baseline Root freeze. Nếu M4 M0017 được freeze, CRM dùng số kế tiếp (dự kiến 18), append, giữ checksum prefix.

### 3.1 Mẫu và ánh xạ (G1)

| Entity | Field cốt lõi | Ràng buộc | Owner path |
|---|---|---|---|
| `crm_mau` | id, PN, loại HĐ, mã mẫu | unique (PN, mã mẫu) | hàm định nghĩa |
| `crm_mau_phien_ban` | mẫu, version n, file DOCX (đường dẫn content-addressed + hash + bytes), danh sách placeholder phát hiện (tên, số lần, ngữ cảnh) | trạng thái DRAFT / CHO_KIEM / CHO_CFO / HIEU_LUC / HET_HIEU_LUC / TU_CHOI; người tải/kiểm/duyệt + lúc; hiệu lực từ–đến; ghi chú thay đổi | Bản đã HIEU_LUC bất biến (chỉ đóng `den` theo lifecycle có lịch sử). Replay cùng ý định/file/map trả version cũ; cùng DOCX nhưng đổi map sau duyệt phải có version mới, dùng lại blob. |
| `crm_mau_anh_xa` | version mẫu, placeholder, trường (FK danh mục trường), bắt buộc, kiểu (text/số/ngày/tiền/bảng), định dạng hiển thị | revision map; digest | Sửa map chưa duyệt → revision mới/DRAFT và vô hiệu lần kiểm hiện hành; giữ mọi map/check/audit lịch sử, không xóa. Map của version đã duyệt không sửa tại chỗ. |
| `crm_danh_muc_truong` | mã trường, nhóm, kiểu, nguồn dữ liệu (đối tượng/tài sản/giá/lịch/khác), cờ PII | version | seed bởi chủ CSDL |

**Gate CSDL:**
- TPL-APPROVE từ chối khi còn placeholder chưa ánh xạ.
- Trường bắt buộc vắng trong mẫu chỉ sinh **cảnh báo** lưu cùng version.
- CFO phải có V4 trên PN (`ktt_co_vai(pn,['CFO'],'V4')`).

### 3.2 Bộ chuẩn dự án tối thiểu (G7)

- Entity `crm_bo_chuan`: PN, dự án, giai đoạn, version.
- Các dòng lịch chuẩn theo 4 cột + %, loại mốc, thứ tự.
- Trạng thái DRAFT / CHO_CFO / HIEU_LUC; hiệu lực từ–đến; KT lập, CFO+V4 duyệt.
- Phiên bản hiệu lực bất biến.
- Không có chuẩn → các consumer nhận "CHUA_CO", không đánh lệch.

### 3.3 Action assignment chung (cho Pháp chế và hành động không gắn vai)

- Entity `master.phan_cong_hanh_dong`:
  - người dùng, PN, module, hành động (vd `CRM_MAU_TAI`), phạm vi tùy chọn (loại HĐ)
  - cấp bởi, cấp lúc, thu hồi lúc
  - chỉ thêm hoặc thu hồi, không sửa tại chỗ
  - ghi bởi chủ CSDL/quản trị
- Hàm `master.ktt_hanh_dong_duoc(pn, module, hanh_dong)`:
  - SECURITY DEFINER, theo danh tính phiên — cùng mẫu với `ktt_duoc` và `ktt_nguon_duoc` (`pg_migrations.py:3102–3111`).
- **Không** thêm giá trị vào enum `vai_tro`.
- **Cơ chế** làm trong gói CRM-41-02.
- **Cấp grant thật** cho tài khoản nào là CHO_DAU_VAO (quản trị), không chặn implementation. DEMO chỉ cấp cho actor `MO_PHONG_*` mới.

### 3.4 Origin MAU và path A-EFF (G6 luồng A)

**Trên `master.hop_dong`:**
- Thêm `trang_thai_giao_ket`: BAO_GIA… / SOAN_THAO / CHO_KY / DA_KY / KE_TOAN_KIEM / HIEU_LUC / TU_CHOI / HUY. Trạng thái `HIEU_LUC` hiện hành giữ nguyên nghĩa.
- Thêm `origin` (MAU / TRICH / NHAP_TAY); binding hàng CRM cũ theo nguồn thực. Không tự backfill TRICH cho hàng M4/VAY hoặc đổi quyền/hành vi M9.
- Thêm `nguoi_phu_trach_id`; lô/căn (tham chiếu danh mục tài sản/dự án).

**Trên `hop_dong_phien_ban`:**
- Nguồn thêm `MAU`.
- Thêm FK tới `crm_mau_phien_ban`, bản render đã ký (§3.6) và bản ký (§3.7).

**Trên `hop_dong_tham_so`:**
- Nguồn từng tham số: MAU / TRICH / NHAP_TAY, kèm tham chiếu field map hoặc snapshot.

**Path A-EFF (hàm CSDL riêng, SECURITY DEFINER):** `crm_hieu_luc_a(phien_ban, expected_graph)`.
- Kiểm vai **KE_TOAN/KE_TOAN_TRUONG + module CRM** trên PN và scope dự án/khách hiện tại; `KTT` trong ma trận chỉ là viết tắt, không phải enum mới.
- Kiểm origin MAU và version mẫu HIEU_LUC tại thời điểm soạn (đã CFO duyệt).
- Kiểm bản ký bất biến và kết quả đối chiếu: không còn PENDING/FAILED/DIFF chưa xử lý; nếu được chọn hoặc khai Có thì đã có kết quả.
- Kiểm khách có mã Junsky; 0 tham số mức ≥ 2 thiếu căn cứ.
- So lịch bản ký với đúng version bộ chuẩn dự án áp dụng: chưa có chuẩn là CHUA_CO, không giả lệch; có lệch vẫn cho hiệu lực theo 41 G6 nhưng ghi audit và tạo đúng việc CFO. Kết quả so/việc cùng transaction với effectiveness, replay không nhân bản.
- Sau đó sinh `lich_thu` **cùng** cấu trúc với luồng B. Vì vậy `fact_hop_dong_m1`, nối tiền và file soát dùng được ngay.

**Hệ quả với guard hiện có:** trigger `phien_ban_kiem_duyet` (`2555–2558`) chặn DA_DUYET nếu không phải CFO V3. Delta bắt buộc:
- Thay hàm trigger bằng bản thêm **một nhánh** chỉ cho phiên bản origin MAU khi transaction đi qua hàm A-EFF.
  - Bằng chứng = chủ bảng (`master.la_chu_bang`) + đối chiếu lineage. Không dùng GUC tùy ý.
- **Nhánh VAY/M9 và nhánh B giữ nguyên từng dòng.**
- Đây là thay đổi guard CRM, cần Root review riêng, có regression đủ T-G6d/e và test M9 hiện có.
- Không cấp quyền CFO chung cho KT; KT không thể gọi path B.

### 3.5 Báo giá và lịch dùng chung (G2)

| Entity | Field | Ràng buộc |
|---|---|---|
| `crm_bao_gia` | số (theo PN), ngày, người lập, PN, loại, dự án, lô/căn, khách (đối tượng Junsky hoặc đối tượng dự thảo), giá + currency, **FX + ngày + người nhập**, cơ sở giá (gồm/không VAT), tiến độ theo dự án (bộ chuẩn version) / theo khách, trạng thái NHAP / DA_IN / DA_CHUYEN / HUY / HET_HAN, revision | Currency ≠ VND thì bắt buộc FX khi in. Không tạo nghĩa vụ/link. |
| `crm_lich_dong` | owner (báo giá revision / dự thảo HĐ revision / bộ chuẩn version), thứ tự, lần, %, số tiền minor, currency, loại mốc NGAY/SU_KIEN, ngày hoặc mã sự kiện, ghi chú | Tổng % = 100 kiểm khi in/xuất. Giữ raw nhập (% hay tiền) và giá trị tính được, tách riêng. |
| `crm_ban_in` | báo giá revision, file + hash, người, lúc | Bất biến; quote sửa sau không đổi bản in. |

### 3.6 Soạn và xuất (G3)

- **`crm_du_thao`:** HĐ, revision, version mẫu pin, snapshot đầu vào (đối tượng, tài sản, giá, lịch), nguồn từng giá trị.
- **`crm_ban_xuat`:** dự thảo revision, DOCX + PDF + hash, người, lúc, renderer version. Bất biến.
- **Đối tượng dự thảo `crm_doi_tuong_du_thao`:**
  - thông tin khách chờ mã Junsky
  - CCCD/STK lưu cột mã hóa + hash
  - chuyển thành đối tượng khi KT gán mã (không tự sinh mã Junsky — TL35 §3A)

### 3.7 Ký kết, đối chiếu, lấy mẫu (G4, G5)

- **`crm_ban_ky`:**
  - HĐ, bản xuất được ký, PDF hash/bytes, ngày ký, người tải, khai có sửa + mô tả
  - bất biến; unique (HĐ, hash)
  - "Thay bằng chứng" là bản ký mới có `thay_cho` + lý do, **chỉ bật sau khi chốt Q-RETURN**
- **`crm_doi_chieu`:**
  - bản ký, bộ kỳ vọng (snapshot tham số của bản xuất được ký), engine/version
  - trạng thái NOT_SELECTED / PENDING / MATCH / DIFF / FAILED
  - `lech[]` (tham số, kỳ vọng, bản ký, trích dẫn, locator, mức)
  - quyết định KT tách riêng (chấp nhận có lý do / trả lại); không ghi đè trạng thái khách quan
- **`crm_chon_mau`:**
  - quyết định chọn kiểm theo grain (loại HĐ × version mẫu)
  - lý do (BAT_BUOC_KHAI_CO / THU_CONG / NGAU_NHIEN) và tham số policy áp dụng
  - một quyết định cho mỗi bản ký; retry không bốc thăm lại
  - nhánh NGAU_NHIEN **tắt** đến khi chốt Q-SAMPLE

### 3.8 Ô Junsky và báo cáo (D3, G8)

- **View/query đọc `kho.cong_no_mo`** ở grain (PN, đối tượng Junsky, TK, ngày chụp, currency).
  - Không chia hay gán cho từng HĐ.
  - Thiếu snapshot → "chưa có sổ".
  - Chênh lệch chỉ so khi cùng grain, cùng ngày sổ, cùng currency.
- **Nhật ký truy cập PII/PDF:** chỉ thêm (ai, đối tượng, mục đích, lúc).

### 3.9 Không đổi

`kho.lien_ket_chung_tu` và guard liên kết; `kho.viec_can_duyet`; luồng B (`crm.py:112–546`); fact M1; file soát một HĐ; M9.

---

## 4. Contract API đề xuất (DE_XUAT — chưa có endpoint chạy)

### Contract chung cho mọi lệnh ghi

- **Danh tính:** phiên do máy chủ cấp.
- **Input bắt buộc:** `khoa` (client key, `[A-Za-z0-9_.:-]{1,200}`) và expected version/revision.
- **Không nhận** actor/PN/trạng thái/cờ duyệt/đường dẫn.
- **Replay:** cùng khóa + cùng body → kết quả cũ; khác body → `IDEMPOTENCY_KHAC`.
- **Audit:** mọi lệnh ghi vào `nhat_ky.su_kien`.
- **Mã lỗi DB** map qua `_crm_db`:
  - 403: phạm vi
  - 409: version/xung đột
  - 400: dữ liệu
- **Unknown outcome:** việc nền đã nhận có `job_id` bền vững; mất response trước khi nhận ID phải tra bằng client key/intent gốc. Giữ request gốc để retry/đối soát, không tự đổi key hoặc coi không có response là chưa ghi. Không phải timeout nào cũng trả được `job_id`.
- **Chứng cứ máy và receipt:** ordinary SQL/body không tự khai placeholder-discovery/render/DIFF-MATCH/FINAL result. Tái dùng capture/worker tin cậy hẹp, gắn bytes + version/map/render/signed lineage; chỉ command hợp lệ sinh FINAL/result cùng transaction. Giữ lệnh người dùng và quyền hiện tại riêng, không dựng framework mới.
- **Scope Bán hàng:** predicate khách được phân công áp dụng ở list/detail, hai ô CRM/Junsky, tổng/drilldown và FILE, theo 42; không chỉ ẩn UI. Ca âm cùng PN khác khách; dùng assignment có căn cứ, không tự thêm policy owner-only.

### Bảng route

| Route (đề xuất) | Loại | Actor / scope | Precondition | Output | Lỗi / unknown |
|---|---|---|---|---|---|
| `GET /api/crm/hop-dong?…` | đọc | theo vai + scope | — | trang danh sách + thẻ số (W) | rỗng không lộ số |
| `GET /api/crm/hop-dong/{id}` | đọc | scope | — | header + T1–T7 (PII theo vai) | 404 ngoài scope |
| `POST /api/crm/mau/tai` (raw body + header info) | ghi | `CRM_MAU_TAI` | DOCX hợp lệ | version DRAFT + placeholder | MAU_TEP_SAI, macro |
| `POST /api/crm/mau/anh-xa` | ghi | `CRM_MAU_TAI` / KT | DRAFT/CHO_KIEM, expected map revision | map revision + cảnh báo | MAU_REVISION_CU |
| `POST /api/crm/mau/kiem` | ghi | KT | CHO_KIEM | CHO_CFO | MAU_CON_O_CHUA_ANH_XA |
| `POST /api/crm/mau/duyet` | ghi | CFO + V4 | CHO_CFO; 0 ô chưa ánh xạ | HIEU_LUC từ ngày | KHONG_CO_QUYEN_LOAI_VIEC |
| `POST /api/crm/mau/xem-thu` | đọc | `CRM_MAU_TAI` / KT / CFO | — | bản xem trước **dữ liệu giả**, không lưu | — |
| `POST /api/crm/bo-chuan/{lap,duyet}` | ghi | KT / CFO+V4 | — | version | — |
| `POST /api/crm/bao-gia/{luu,in,chuyen,huy}` | ghi | Bán hàng scope | FX/100% khi in; mẫu hiệu lực khi chuyển | revision / bản in / HĐ SOAN_THAO | BAO_GIA_TONG_PT, THIEU_FX |
| `POST /api/crm/soan/{luu,xuat}` | ghi + job | Bán hàng scope | expected draft revision; đủ bắt buộc | revision / job → bản xuất | XUAT_THIEU_TRUONG; job FAILED giữ nguyên trạng thái |
| `POST /api/crm/ky-ket` (raw PDF) | ghi | Bán hàng phụ trách | CHO_KY; khai Có/Không | DA_KY; quyết định chọn kiểm | KY_THIEU_PDF; cùng hash → lap_lai |
| `POST /api/crm/doi-chieu/{chay,xu-ly}` | ghi + job | hệ thống / KT | DA_KY | MATCH/DIFF/FAILED; quyết định KT | FAILED ≠ MATCH |
| `POST /api/crm/hieu-luc-a` | ghi | KT | A-EFF gate (§3.4) | HIEU_LUC + `lich_thu` | A_CHUA_DU_DIEU_KIEN, ORIGIN_KHONG_PHAI_MAU |
| `POST /api/crm/tra-lai` | ghi | KT | KE_TOAN_KIEM | W1; bản ký giữ | chờ Q-RETURN cho phần mở bản làm việc |
| `GET /api/crm/tep/{id}` | đọc tệp | quyền tệp theo mục đích | — | bytes (attachment) + log | 403 trước khi đọc kho |
| `GET /api/crm/bao-cao?…`, `POST /api/crm/file-soat-ky` | đọc / ghi lô | theo scope | — | tổng + drilldown; file soát kỳ | thiếu nguồn → "—" |
| Hiện có (giữ nguyên) | — | — | — | — | — |

Các route hiện có giữ nguyên: `/api/crm/nhan`, `bo-sung`, `trich-lai/*`, `mapping`, `xac-nhan-tham-so`, `kiem`, `duyet`, `duyet-v4`, `tu-choi`, `lien-ket`, `go-lien-ket`, `file-soat` (`server.py:270–311`).

---

## 5. Consumer bị ảnh hưởng

| Consumer | Ảnh hưởng | Yêu cầu |
|---|---|---|
| `crm.danh_sach` / UI `#hopdong` | Thêm trạng thái giao kết, origin, người phụ trách | Hàng cũ hiển thị như trước (origin TRICH). |
| `fact_hop_dong_m1`, M1 engine | Đọc phiên bản DA_DUYET | A-EFF phải sinh phiên bản DA_DUYET cùng hình dạng; regression fact. |
| Nối tiền / guard | Không đổi | Chỉ HĐ đã hiệu lực. |
| `xuat_file_soat` | Có thể thêm cột origin / version mẫu | Giữ contract export một HĐ cũ; export kỳ mới đủ sáu nhóm nghiệp vụ và CANH_BAO theo A1/S9, gồm Liên kết tiền. |
| Trigger `phien_ban_kiem_duyet` | Thêm nhánh MAU | Nhánh B/VAY giữ nguyên; test M9 + CRM regression. |
| M4 M0017 (`module_chu`, policy RESTRICTIVE trên `master.hop_dong`) | Chung bảng | Bind sau khi Root freeze M4; HĐ CRM luôn `module_chu` NULL. |
| M3 | Chỉ đọc | Không ghi doanh thu, không xuất/nhập Junsky. |

---

## 6. Câu hỏi mở — chỉ chặn nhánh phụ thuộc

| Mục | Chặn | Không chặn |
|---|---|---|
| Q-B | Chỉ việc **đổi** luồng B | Mọi thứ của A; B giữ CFO |
| Q-SAMPLE | Nhánh lấy mẫu ngẫu nhiên tự điều chỉnh (CRM-41-06) | Đối chiếu bắt buộc (khai Có) và thủ công trong 41-04 |
| Q-RETURN | "Thay bằng chứng"; mở bản làm việc khi trả lại; hủy sau ký | G1/G2/G3; ký lần đầu bất biến; trả lại ở mức thông báo |
| Q-INPUT | Độ chính xác KCN/nhà ở; catalog thực; câu FX trong mẫu | Khung DEMO, contract, plumbing |
| Q-PII | Xuất/tải tài liệu thật có PII đầy đủ | Schema mã hóa, mask JSON, log truy cập |
| Q-UI | Cột thêm/bớt; hạn n ngày; vị trí UI quản trị G7 | Bốn điểm đã chốt; khung 9 màn |
| M4 freeze | E1–E5, S7 nhận PDF/DOCX | Toàn bộ G1–G4, G6-A, G7, G8, UI |
| Grant Pháp chế thật | Cấp cho tài khoản thật | Cơ chế action assignment + DEMO |

---

## 7. Handoff coding

### Thứ tự gói

Bám hàng chờ 92 dòng §3: 02 → 03 → 04; 01 khi M4 freeze; 05 hoàn thiện; 06 chờ policy. Mỗi gói CODE theo lệnh Root, một product writer, Root kiểm độc lập sau terminal.

### 7.1 CRM-41-02 — Mẫu có phiên bản + bộ chuẩn tối thiểu + action assignment

**Đủ điều kiện giao ngay sau review.** Không phụ thuộc M4 engine.

**Mục tiêu hữu hạn:**
- G1 đầy đủ trên K2: tải mẫu → phát hiện placeholder → ánh xạ → xem thử dữ liệu giả → KT kiểm → CFO+V4 duyệt có hiệu lực từ ngày → so sánh hai version.
- G7 tối thiểu: KT lập, CFO+V4 duyệt bộ chuẩn 4 cột theo dự án/giai đoạn có version; API đọc chuẩn hiệu lực.
- Cơ chế action assignment chung + action `CRM_MAU_TAI`.
- Màn S6 dùng được trong menu "Hợp đồng bán hàng". Khung MENU-1…6 hiển thị đúng; các màn chưa làm ghi "chưa mở ở gói này", không giả chức năng.

**File target đề xuất:**
- Migration append sau baseline freeze, trong `src/kho_tri_thuc/ha_tang/pg_migrations.py`. Số bind theo Root.
- `src/kho_tri_thuc/k2/crm_mau.py` (service mới).
- `src/kho_tri_thuc/nguon/mau_docx.py` (đọc placeholder DOCX, stdlib zipfile/ET, không chạy Word).
- `src/kho_tri_thuc/giao_dien/crm_g.py` (HTTP mỏng).
- Mở rộng có kiểm soát: `server.py` (một điểm dispatch) và `k2/quyen.py` (thêm action, không đổi action cũ).
- `k2/crm_g_demo.py` (seed: mẫu DOCX DEMO, actor `MO_PHONG_PHAP_CHE_A` có `CRM_MAU_TAI`; không sửa actor cũ).
- `tests/test_crm_41_02.py`.
- Tài sản UI mới: đường do Root chỉ định trong allowlist.

**Primitive tái dùng:** `ktt_danh_tinh` / `ktt_duoc` / `ktt_co_vai`; `la_chu_bang`; `kho.viec_can_duyet` (V4); `nhat_ky.su_kien`; `write_immutable`; `_crm_db`; mẫu phiên cookie `crm_phien`; mẫu biên nhận idempotent.

**Contract:** các route `mau/*`, `bo-chuan/*` ở §4. Placeholder chưa ánh xạ là gate CSDL; trường bắt buộc vắng chỉ là cảnh báo.

**Kiểm độc lập cần có:**
- T-G1a–f, T-G7a/b.
- Âm: người không có action tải; KT duyệt; CFO thiếu V4; replay khác body; cùng hash.
- DB bypass: app login INSERT/UPDATE trực tiếp bảng mẫu → bị chặn.
- Luồng B và CRM regression (`test_crm_k2`/neutral compat theo baseline).
- Prefix migration và checksum giữ nguyên.

**Ngoài scope:** báo giá, soạn, render, ký, đối chiếu, A-EFF, engine theo loại, grant tài khoản thật, Claude Design.

**Dependency thật:** baseline sau M4 terminal được Root freeze (vì cùng `pg_migrations.py` / `server.py` / `master.hop_dong`).

### 7.2 CRM-41-03 — Báo giá + soạn/xuất

**Giao sau khi 02 đạt.**

- **Mục tiêu:** G2 + G3.
  - S3 (4 cột, FX tay người/ngày, in bất biến).
  - S4 (pin version mẫu, nguồn từng tham số, xuất DOCX/PDF có revision/hash).
  - "Theo dự án" đọc bộ chuẩn của 02; "theo khách" không gắn nhãn chuẩn.
- **File target:**
  - `k2/crm_bao_gia.py`, `k2/crm_soan.py`.
  - Renderer DOCX trong `nguon/mau_docx.py` (stdlib).
  - **PDF:** kiểm và tái dùng công cụ/runtime đã có trước; thiếu thì trạng thái "PDF chưa sinh được" thật, không giả PDF. Root chọn giải pháp trong phạm vi đã giao; chỉ hỏi Anh nếu cần quyết định/phí/quyền ngoài ủy quyền, không tạo gate xin phép chung cho dependency thường lệ.
  - Migration append; mở rộng `crm_g.py`; `tests/test_crm_41_03.py`.
- **Kiểm:** T-G2a–c, T-G3a–c; PII theo Q-PII (bản xuất DEMO dữ liệu giả).
- **Ngoài scope:** ký, đối chiếu, hiệu lực.

### 7.3 CRM-41-04 — Ký kết, đối chiếu cơ bản, hiệu lực luồng A

**Giao sau 01 (phần E5) và 03. Phần trả lại/thay bằng chứng chờ Q-RETURN.**

- **Mục tiêu:**
  - G4 (PDF bắt buộc, khai Có/Không, bất biến, replay).
  - G5 cơ bản (bắt buộc khi khai Có; đối chiếu tay; kết quả khách quan tách quyết định KT).
  - **A-EFF** qua hàm CSDL riêng + nhánh trigger §3.4.
  - Luồng B giữ nguyên.
- **Kiểm:** T-G4a–d, T-G5a–d, T-G6a–e (gồm âm KT gọi B, KT A-EFF HĐ TRICH), T-M1a–e regression, fact M1 regression, M9 regression.
- **Ngoài scope:** lấy mẫu ngẫu nhiên tự điều chỉnh (06); thay bằng chứng (sau Q-RETURN).

### 7.4 CRM-41-01 — Engine theo loại

**QUEUED_DEPENDENCY_M4_REUSE: CHO_DAU_VAO interface M4 freeze.**

- **Mục tiêu:** E1–E5 trên lõi chung đã freeze.
- **Kiểm:** XD regression 37 mã; KCN/nhà ở chỉ đo độ chính xác khi có mẫu độc lập (Q-INPUT).
- Không sửa file M4 đang viết.

### 7.5 CRM-42-05 — Hoàn thiện màn hình và tra cứu/thu/file

**Sau phần lõi.**

- S1 đầy đủ: thẻ W, bộ lọc lưu theo người, người phụ trách, scope dự án/khách.
- S2 bảy tab; S8; S9 đủ sáu nhóm nghiệp vụ, gồm Liên kết tiền và giữ CANH_BAO; hai ô CRM/Junsky đúng grain (T-J1, P-D3).
- Log PII/PDF; 17 trạng thái ở 1280–1440.
- Cần Root xác nhận RLS `kho.cong_no_mo` cho Bán hàng trước khi code.

### 7.6 CRM-41-06 — Lấy mẫu tự điều chỉnh, G7 quản trị đầy đủ, G8

**QUEUED_POLICY_INPUT (Q-SAMPLE, Q-UI).** Không hardcode 50/10/20.

---

## 8. Cần Root xem

1. **Nhánh trigger MAU trong `phien_ban_kiem_duyet` (§3.4).** Đây là sửa guard CRM bắt buộc để có luồng A; cần duyệt kỹ thuật riêng.
2. **Va chạm với M4 M0017 trên `master.hop_dong`.** Bind số migration và thứ tự sau khi freeze M4.
3. **RLS/grant `kho.cong_no_mo` cho vai Bán hàng** — chưa kiểm trong lượt này.
4. **Vị trí UI quản trị G7** (tab trong S6) và dialog Thay bằng chứng — DE_XUAT_CAN_CHOT.
5. **Đường tài sản UI cho gói CRM** (allowlist ghi file giao diện).
6. **Công cụ sinh PDF ở gói 03**: Root kiểm công cụ/runtime đã có và chốt binding kỹ thuật; chỉ hỏi khi vượt phạm vi ủy quyền thực tế.

**Coverage:** A1 phủ đủ 8 G / 6 E / 9 màn / 7 tab / 17 trạng thái / 6 menu / 4 quyết định. Các lỗ hổng chỗ đặt đã liệt kê ở A1 §4 và §11.
