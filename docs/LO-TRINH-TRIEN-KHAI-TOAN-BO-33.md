# Lộ trình triển khai toàn bộ file 33 — M0 + M1–M10 · 8 nguồn · 15 chứng từ · 9 bộ tiếp nhận · L1–L12

Ngày lập: 18/10/2026 · sửa lần 2 cùng ngày theo hai audit tái sử dụng và review của Codex · Người soạn: Claude Code (sửa mã chính) · Codex kiểm độc lập.
Trạng thái: **backlog triển khai, chưa nghiệm thu**. Không module nào được coi là đã nghiệm thu chỉ vì có mặt trong tài liệu này.
Căn cứ: `CHUONG-TRINH-HOAN-THIEN-PHAN-MEM-KE-TOAN.md`, `COVERAGE-33.json`, `docs/can-cu-33/` (TL29–35, 37–40), **`TAI-SU-DUNG-REVIEW-XAY-DUNG.md`** (audit #5), **`DANH-MUC-TAI-SU-DUNG-PHAN-MEM.md`** (audit các app khác), source repo này. Hợp đồng từng bộ tiếp nhận: `HOP-DONG-TICH-HOP-VA-TAI-SU-DUNG-33.md`.

## 0. Nhãn mức xác minh

| Nhãn | Nghĩa |
|---|---|
| **[SRC]** | Claude đọc trong source repo này (file:dòng/hàm). |
| **[AUDIT-RV]** | Fact trong `TAI-SU-DUNG-REVIEW-XAY-DUNG.md` (audit tĩnh source #5; số dòng là của source nguồn theo audit). |
| **[AUDIT-DM]** | Fact trong `DANH-MUC-TAI-SU-DUNG-PHAN-MEM.md` (audit tĩnh các app khác). |
| **[TL]** | Thiết kế đã chốt trong TL29–40. |
| **[DỰ THẢO]** | Đề xuất của tài liệu này, chưa chốt. |

Audit là kiểm tra tĩnh code/tài liệu: **có code không đồng nghĩa đã triển khai hay đúng trên dữ liệu thật** ([AUDIT-DM] mở đầu; [AUDIT-RV] §0). Mọi bridge vẫn phải có ca DEMO và kiểm runtime riêng.

M1–M6 trong báo cáo legacy (`BAO-CAO-KIEM-THU-M1-M6.md`, `src/kho_tri_thuc/workflow.py`) là **6 gói kỹ thuật**, không phải phần hành M1–M6 của file 33.

## 1. Baseline

### 1.1 Trong repo này [SRC]

| Năng lực | Bằng chứng | Trạng thái thật |
|---|---|---|
| Bộ đọc nguồn 5 loại | `nguon/that.py::ThatAdapter` (`sao_ke` .xlsx/.xls/.pdf; `hoa_don` XML/zip `_xml_rows`:459; `bang_ke` `_invoice_table_rows`:478; `base` `_base_rows`/`_base_request_row`:502–549; `junsky` `_junsky_rows`:557, công nợ mở có cột *Hợp đồng vay* `_open_items`:637) | Có code + test DEMO |
| Kho V12, chống trùng, raw bất biến | `ha_tang/store.py` (`core_hash` = sha256(canonical_json)), `backup.py` | Có |
| M1 đề xuất sao kê | `giao_dien/quick.py::QuickPosting` (propose/repropose/decide/export/score), `de_xuat/engine.py` | Đang dùng thử trên TK go-live theo báo cáo V10–V12; **chưa nghiệm thu Windows**. Thiếu khớp đa nguồn (L1/L2/L8/L10) |
| M2/M3 đề xuất hóa đơn | `tri_thuc/lich_su_hoa_don.py` (`JournalIndex.link`, `build_history`, `suggest`) | Có đề xuất V12; chưa nối RQ/nghiệm thu/CRM |
| 6 gói kỹ thuật legacy | `workflow.py` ACTIONS; `xuat/shadow.py` (`CB_tmpEntry1/2`, mức 2 khóa) | Có (fixture/shadow) |
| K2 PostgreSQL | `ha_tang/pg_migrations.py` (4 schema; bảng `hop_dong*`, `lich_thu`, `lich_tra_no`, `tai_san`, `nhan_vien`, `lien_ket_chung_tu`, `viec_can_duyet`, `cau_hoi`, `lo_xuat*`, `khoa_ky`…), `ket_noi.py` (phương án C), bộ chuyển `tools/chuyen_sqlite_sang_pg.py`, `tools/chep_v12_sang_pg.py` | **V13 NOT_VERIFIED**. Review A4/A5 nêu 2 lỗi chặn (đối chiếu bỏ cột typed; biên lỗi CLI hở) — đã sửa mã lượt này, **test chưa chạy được** (xem báo cáo lượt), PG runtime chưa kiểm. Không có mã nghiệp vụ nào dùng các bảng hợp đồng/lịch/tài sản/liên kết/việc |
| Chưa có | `giao_tiep`, bridge #5/#6/#9/#10/#11, bộ đọc lương, khấu hao/242/335; K5 đa loại việc; cổng AI/Mask; Zalo; đăng nhập | — |

### 1.2 App nguồn đã có (theo audit — tái dùng, không làm lại)

| App | Đã có (audit) | Đường dùng lại |
|---|---|---|
| #5 Review xây dựng | CSDL SQLite là nguồn nghiệp vụ; hợp đồng/tham số/phụ lục/BOQ/đợt/KL/nhật ký; JSON kết quả `kiem_tra_dot`; API HĐ chi tiết có `tham_so[]` + provenance; export CSDL 8 sheet; engine hiệu lực theo ngày nghiệm thu [AUDIT-RV §2, §4] | Bridge nhận kết quả + mapping; **không** review lại BOQ |
| #6 Trích tham số HĐ (Local AI) | `read_contract`, cấu trúc Điều/Khoản, kiểm trích dẫn, `*_KET_QUA.json` (`tham_so[]`: `ma, nhom, tham_so, gia_tri, don_vi, dieu_khoan, trich_dan, ghi_chu, kiem_tra, vi_tri_do_duoc`) [AUDIT-DM §2] | Đọc JSON kết quả → tham số chờ duyệt |
| #7 Tải hóa đơn | Node/Playwright theo kỳ/chiều, XML/PDF/bảng kê [AUDIT-DM §3] | **Tương thích ngay** `ThatAdapter` `_xml_rows`/`_invoice_table_rows`; chỉ thêm manifest phiên tải |
| #8 Backup Base | bundle `request_<id>.json` (`get`, `custom_table`, `_attachment_results`, `fetched_at`), manifest đính kèm, index Excel [AUDIT-DM §3] | **Parser repo đã khớp format** (`that.py:502–549`); không dùng cột tiền index (best-effort) |
| #9 Khoản vay | Apps Script: `DaiHan`, `KheUoc`, `LichTraGoc`, `LichLaiSuat`, `PhatSinh` (khóa `maKV`, `maKheUoc`); ngắn hạn/LC/hợp đồng mua/hạn mức; `load/loadMaster`; export Excel/Lãi/JSON. **Hai bộ source khác phiên bản** (`Code.gs` 920 dòng vs deploy `Code.js` 1.203 dòng) [AUDIT-DM §4] | Contract adapter khóa theo **một** phiên bản schema được xác nhận |
| #10 Kho | Không chỉ thiết kế: CRUD/duyệt/đảo phiếu, tồn số lượng, kiểm kê, PWA/API; header `SoPhieu, LoaiPhieu, NgayChungTu, MaKho, MaDoiTac, TrangThai, SoPhieu_Goc`; detail `ID_Dong, SoPhieu, MaHang, SoLuong`; `MaDoiTuong_KT`; `{phieu, lines}`. Export XLSX **chưa chứng minh** [AUDIT-DM §5] | Đọc phiếu đã duyệt/đảo qua Sheets API/`{phieu,lines}` |
| #11 Nước thải | Jobs (`batch_id, company_id, period, status, source_fingerprint`), chống trùng lô, MASTER_COLUMNS có ObjectID, OCR schema, sinh `SELLING1/2` theo template **`SM_tmpSelling1/2` (không phải `CB_tmpEntry1/2`)**; nguồn tự cảnh báo `EntryID/EntryDate/InvDate/InvSeri` còn template thử [AUDIT-DM §6] | Bridge lô đã soát/SELLING → M3, nối XML chính thức để không ghi nhận hai lần |
| #13 Local Mask | Lõi suggest/replace/verify, rule schema, vault AES-GCM; web có phiên/CSRF; **không có API headless mask→cloud→restore**; detector không mask số tiền [AUDIT-DM §7] | Chỉ dùng lõi; lớp chính sách bảy nhóm là phần phải viết |
| #14 Trợ lý | Telegram transport, webhook, task↔message binding, dedup, reminder, logbook; `brain.py` gọi AI trực tiếp [AUDIT-DM §8] | Chỉ dùng lõi máy việc/nhắc; transport Zalo chưa có; AI phải qua cổng chung |

## 2. Nguyên tắc lập gói

1. **Một gói một chuỗi đầy đủ**: nguồn → K1 → K2 → K3 → K4 → K5 → file soát/lô (mức 2 khóa) → đối chiếu. Không giao gói chỉ schema/test.
2. **Tái dùng engine/UI nguồn nguyên trạng**: kế toán nhận kết quả, map khóa (pháp nhân, mã HĐ chung, `ProjectID`, `ObjectID` Junsky) có xác nhận của người có thẩm quyền; **không fuzzy theo tên**, không suy mã Junsky từ text ([AUDIT-RV §5.3]).
3. **Kênh theo TL40**: app trong nhà → `giao_tiep` role riêng (khi có) hoặc K1 đọc file/JSON; app ngoài/Sheets → K1/API chỉ đọc. Không mở server nguồn ra LAN, không gọi `mo_csdl()` của #5 (có thể ghi schema) [AUDIT-RV §2].
4. **Cổng theo thao tác, không cổng toàn cục**:
   - Thiết kế, adapter và bridge **DEMO** không phụ thuộc V13 A1–A6 hay backtest clean-cutoff; chạy được trên SQLite/DEMO.
   - Thao tác **K2 runtime** (ghi/đọc PostgreSQL) cần PG sẵn sàng và phần đối chiếu liên quan (A3–A5) đã kiểm.
   - **Chấm điểm/backtest** cần clean-cutoff; thiếu thì không dùng số đo đó, nhưng không chặn việc khác.
   - **Nhập/đối chiếu Junsky thật** cần cổng vận hành Junsky riêng; mức 2 khóa.
5. **Kho thật vẫn SQLite** (phương án C); dữ liệu thật chỉ Codex chạy trên snapshot.
6. Nghiệm thu bấm trên DEMO (actor `MO_PHONG_`), sau đó Codex lặp lại trên snapshot; skip/tập rỗng/cùng lỗi không tính đạt.

## 3. Gói nền M0 (chỉ phần các chuỗi cần)

| Gói | Phủ | Tái dùng | Nối/viết thêm | Thiết kế còn hoàn thiện | Cổng thật | Nghiệm thu bấm |
|---|---|---|---|---|---|---|
| **N1 · Liên kết là dữ liệu** | M0; nền L1–L12 | `lien_ket_chung_tu` [SRC schema]; bậc 0 tiền↔công nợ + `EntryDM` của M1 [SRC] | Dịch vụ đề xuất/xác nhận/gỡ, một–nhiều, một phần; M1 ghi kết quả bậc 0 vào bảng; chuyển `bank_journal_matches/allocations/historical_links` | Thêm `loai`: `NT_HOP_DONG`, `HD_LICH_VAY`, `BL_LENH_CHI`, `BAN_GIAO_GIA_VON`, `SELLING_HD_BAN` [DỰ THẢO] | DEMO trên SQLite trước; bản K2 cần PG | 9 lần chuyển = 1 hóa đơn → 1 liên kết; xác nhận/gỡ có nhật ký; chạy lại không trùng |
| **N2 · Việc cần duyệt + K5 bản 1** | M0 K5; V1–V8 | Màn Định khoản V11/V12 [SRC]; TL37 | Danh sách gộp V1–V8, chuỗi chứng từ, trạng thái tới Đã đối chiếu, **trạng thái duyệt kế toán tách khỏi trạng thái nguồn** (vd `da_nap` #5) | Prompt Claude Design v2 | N1 | Dòng V1 M1 có chuỗi; V3 có trích dẫn; Đồng ý chặn khi thiếu đối tượng TK công nợ |
| **N3 · Đăng ký bộ tiếp nhận + manifest** | M0 bóc tách; 9 bộ tiếp nhận | `ThatAdapter` [SRC]; `master.nguon_tu_dong` | Lớp đăng ký adapter có **phiên bản contract**, manifest (pháp nhân, kỳ/chiều, lúc lấy, file/hash, thành công/thiếu/lỗi) → `chung_tu` theo `loai` TL38 | — | Không (DEMO) | Nạp lại cùng file → 0 bản ghi mới; mỗi bản ghi có hash + `nhan_luc` |
| **N4 · `giao_tiep` v1 + role theo app** | M0 tích hợp | Mẫu REVOKE V13 [SRC] | `su_kien_cho`, view/hàm `v1_*`, role `app_review/app_base/app_request/app_kiem_tra_dx` | Tên schema `du_an`/`rq` | V14 + PG | Role app không SELECT bảng thật; ghi 2 lần → 1 dòng hàng đợi |
| **N5 · Kỳ, khóa kỳ, lô** | M0; tiền đề M10 | `month-close`, `shadow-export/reconcile` [SRC] | Khóa kỳ + lô + 4 nhóm đối chiếu | Mẫu xuất sổ Junsky | Đối chiếu thật: cổng Junsky | Kỳ khóa chặn Đồng ý; lô DEMO ra 4 nhóm đúng |
| **N6 · Cổng AI + Mask** | M0 AI | Lõi #13 [AUDIT-DM §7]; `bao_mat.mask_bi_danh`, `cong_ai_goi` [SRC schema] | Lớp chính sách bảy nhóm **gồm số tiền** (detector nguồn không mask tiền), bí danh đảo ngược khớp mã Junsky, kiểm sau khôi phục, log, công tắc | Đáp án mẫu từng loại | **Cloud tắt** đến khi đủ điều kiện TL35 | Payload DEMO chỉ còn bí danh; công tắc tắt → 0 lượt gọi |
| **N7 · Agent Zalo** | M0 Zalo; V5 | Lõi #14: binding, dedup, reminder, logbook [AUDIT-DM §8] | Gói đủ chương trình: transport Zalo (adapter thay `tg.py`), nhận và gắn trả lời vào đúng câu hỏi/việc K5 (`task_id`, callback 1/2/3 ↔ phương án), dedup tin, nhắc hạn, escalation sang kế toán, nhật ký; bỏ đường gọi AI trực tiếp; mock transport cho test | Thử bot nhắn trước/tần suất | **Gửi tin thật là cổng riêng** (chưa kích hoạt); DEMO chỉ mock | Mock: Đỏ → câu hỏi đánh số; trả lời "2" gắn đúng phương án; tin lặp không xử lý hai lần; quá hạn → nhắc rồi escalation; không có tin thật nào gửi |
| **N8 · Web đa người dùng** | M0 quyền | `nguoi_dung/phan_quyen` [SRC schema] | Đăng nhập, RLS pháp nhân, `[modules]`, LAN+HTTPS | SSO | V14 | Pháp nhân A không thấy B |

## 4. Chuỗi nghiệp vụ

### C1 · Thu tiền — CRM kế toán ↔ hóa đơn bán ↔ tiền về (M3, M1, L1; sản xuất lịch DT KCN cho M10)

**Đa pháp nhân, đa loại hình** (TL32 §3.2, TL35 §8.3): làm cả thuê đất/hạ tầng KCN **và** mua bán nhà ở; loại hình là cấu hình. Việc PLHN hiện chỉ có loại hình KCN (TL35 §6) chỉ quyết định **thứ tự DEMO/dữ liệu thật đầu tiên**, không loại HDNO.

| Gói | Phủ | Tái dùng | Nối/viết thêm | Thiết kế còn hoàn thiện | Phụ thuộc | Nghiệm thu bấm |
|---|---|---|---|---|---|---|
| **C1a · CRM kế toán nạp hợp đồng bán** | M3; HDKCN, HDNO; R_CRM | #6 `*_KET_QUA.json` (`tham_so[]` có `trich_dan`, `kiem_tra`) [AUDIT-DM §2]; engine trích của #5 khi phù hợp [AUDIT-RV §4]; `hop_dong*`, `lich_thu`, `loai_hinh_doanh_thu` [SRC schema] | JSON + hash file → `hop_dong_phien_ban` (CHO_DUYET) + `hop_dong_tham_so.trich_dan` → V3 CFO → sinh `lich_thu`; phụ lục = phiên bản mới; phòng bán hàng nhập chờ duyệt (TL40 §7). Trạng thái `kiem_tra` của nguồn **không thay** duyệt | Bộ tham số + mẫu bút toán cho từng loại hình (KCN và nhà ở) theo hợp đồng mẫu | N1, N2, N3 | Hợp đồng DEMO dạng DOC/DOCX (reader `read_contract` hiện có của #6; PDF chỉ khi có tầng đọc PDF/OCR #12, không mặc định) → V3 tham số có trích dẫn; thiếu trích dẫn → "Không quy định"; CFO MO_PHONG duyệt → lịch n đợt; phụ lục → phiên bản 2, đợt đã khớp giữ liên kết; chạy cho **hai pháp nhân DEMO, mỗi loại hình một hợp đồng** |
| **C1b · L1 tiền về ↔ đợt/hóa đơn** | M1, M3, L1 | M1 bậc 0 + CFO-02 [SRC/TL] | Ứng viên theo mã HĐ/đợt/khách; thu trước → Vàng 344/131 theo CFO; nạp HĐ/đợt sau chỉ nối liên kết; thu một phần cập nhật `da_thu_minor` | CFO-03 vào tri thức | C1a, N1 | Thu đúng đợt → Xanh + liên kết; thu trước HĐ → Vàng, sau chỉ nối, số bút toán không đổi; thu thiếu → MOT_PHAN |
| **C1c · Hóa đơn bán ↔ hợp đồng/đợt** | M3; XMLB; R_HD | `parse_invoice_xml`, `suggest` [SRC] | Nối hóa đơn ↔ HĐ/đợt; đề xuất theo loại hình; USD thu VND hai đồng tiền + tỷ giá | Thời điểm ghi nhận, Nợ 138 | C1a | Hóa đơn đợt 2 → liên kết đợt 2; điều chỉnh giữ chuỗi |
| **C1d · Bàn giao + lịch phân bổ DT** | M3 BBG; **sản xuất lịch cho C9a** | `lich_thu.moc=BAN_GIAO` [SRC schema] | Sự kiện bàn giao có căn cứ → đề xuất ghi nhận; **sinh và lưu lịch phân bổ** doanh thu nhận trước (bảng đã duyệt). Không chờ bộ sinh lô định kỳ | Chính sách phân bổ (CFO) | C1a | Bàn giao lô → 1 sự kiện; lịch 12 kỳ không trùng; lịch được C9a đọc mà không cần C1d chạy lại |
| **C1e · Phí dịch vụ KCN từ #11** | M3 doanh thu dịch vụ | #11 Jobs/fingerprint/MASTER/SELLING1-2 (`SM_tmpSelling1/2`) [AUDIT-DM §6] | Đọc lô đã soát/SELLING → chứng từ bán **đề xuất** + liên kết `SELLING_HD_BAN` với XML chính thức đến sau → không ghi nhận hai lần; map pháp nhân/ObjectID/kỳ | Cảnh báo template `EntryID/EntryDate/InvDate/InvSeri` của nguồn phải xử lý ở nguồn trước khi dùng production | N3, C1c | Lô DEMO + XML cùng hóa đơn → 1 doanh thu; chạy lại lô cùng fingerprint → 0 mới |

### C2 · Chi tiền — RQ ↔ hóa đơn mua ↔ lệnh chi (M2, M1, L2)

| Gói | Phủ | Tái dùng | Nối/viết thêm | Thiết kế còn hoàn thiện | Phụ thuộc | Nghiệm thu bấm |
|---|---|---|---|---|---|---|
| **C2a · RQ vào kho chung** | RQ; R_BASE | #8 bundle JSON + parser repo đã khớp [AUDIT-DM §3; SRC `that.py:502–549`] | Canonical RQ (Dự án, Chi phí DA/VH, nội dung, STK, nhóm G, hóa đơn — TL31) → `chung_tu loai=RQ`; kiểm field/tiền tệ, thiếu → cách ly; #2 Request đã có schema RQ theo phiên bản nhóm, API v1 đọc/nháp/tệp, webhook [TAI-SU-DUNG-RQ-VA-NHAN-SU §2] → adapter DEMO theo contract làm được ngay, không hỏi lại; nối nguồn thật chỉ khi được cấp kết nối/quyền vận hành | Crosswalk `fieldCode` → canonical; `approved` của Request ≠ duyệt bút toán | N3 | Nạp 2 lần không trùng; thiếu tổng → `BASE_AMOUNT_MISSING` [SRC]; không đọc tiền từ index Excel |
| **C2b · Hóa đơn mua ↔ RQ, một dòng một đích** | M2; XMLM | `suggest` V12 [SRC]; #1 đã có schema YAML hồ sơ loại chi phí, validator, router và rule version [TAI-SU-DUNG-RQ-VA-NHAN-SU §1] — dùng lại, không hỏi lại | Liên kết HD_RQ; crosswalk `loai` #1 → nhóm G → DA/VH (chồng lấn/chưa phân loại = việc cần xử lý); đích dòng (CHI_PHI/241/TAI_SAN/KHO) = tri thức học → kiểm nhóm G × DA/VH × ngưỡng TSCĐ; đổi đích trước xuất = hoàn tác có nhật ký, sau xuất/nạp = bút toán điều chỉnh, giữ lô cũ | Hai bảng ánh xạ nhóm G; chủ danh mục với #1 | C2a, N1 | Mua lẻ có RQ → Vàng đúng TK; HĐ 2 dòng → 2 đích; một dòng không vào hai module |
| **C2c · L2 lệnh chi ↔ phải trả** | M1, M2, L2; UNC | M1 bậc 0 [SRC] | Mã RQ/số HĐ trong nội dung → khớp cứng; tạm ứng → 331 dư Nợ/141 + liên kết chờ; trả nhiều HĐ/một phần | Nguồn UNC (file lô eFAST hay chỉ qua sao kê) | C2b, N1 | Chi 1 lần cho 3 HĐ → 3 liên kết; tạm ứng rồi HĐ về → chỉ nối |

### C3 · Dự án — kết quả review #5 ↔ hóa đơn thầu ↔ XDCB (M4, L3, L5, L6, L7)

Hợp đồng bridge theo [AUDIT-RV] — **không** review BOQ, không thêm gate trùng nghiệp vụ nguồn:

- #5 **không có** trạng thái "được phép hạch toán" và **không có** trường giá trị kế toán được duyệt. `da_nap` chỉ chứng minh đã nạp vào CSDL review [AUDIT-RV §3.1, §3.2]. Kế toán có **trạng thái duyệt riêng** (N2); hai trạng thái độc lập.
- Số tiền: giữ nguyên số nguồn kèm nghĩa (`gt_kn`, `gt_lk`, `giu_lai`, `thu_hoi_tu`, `tt_ky_nay`, `de_nghi`, cơ sở VAT) [AUDIT-RV §3.1–3.2]. **Tuyệt đối không tính `de_nghi − anh_huong`** (khác cơ sở: ảnh hưởng là lũy kế, chưa VAT) [AUDIT-RV §3.1]. Số được hạch toán là trường **xác nhận riêng** của người có thẩm quyền; thiếu → chờ, không mặc định 0, không tự "đã duyệt".
- Tách **giữ lại đợt (TT-21)** và **bảo hành/bảo lãnh bảo hành (TT-31)**; tham số/phụ lục lấy **snapshot đúng ngày nghiệm thu** qua engine hiệu lực của nguồn (`tham_so_hieu_luc`, `phu_luc_ap_dung`) [AUDIT-RV §3.3, §4].
- **Không** thêm gate M4 "tổng nghiệm thu ≤ giá trị HĐ" chung cho mọi loại giá: nguồn đã có quy trình riêng cho đơn giá cố định và đã ghi nhận lệch engine B1 [AUDIT-RV §6]; sửa (nếu cần) ở engine nguồn có kiểm chứng.
- Khóa: **instance nguồn + `ma_hd` + `dot` + `ma` lần review**; `ma_hd` tự sinh `HD…` chỉ là khóa trong instance → cần namespace; `so_hd` là bằng chứng phụ, không tìm mơ hồ; nạp thay/chạy lại → quan hệ `supersedes` + lý do, không thêm công nợ mới cho cùng sự kiện [AUDIT-RV §3.1, §5.2].
- Mapping instance/HĐ → pháp nhân, mã HĐ chung, `ProjectID`/giai đoạn, `ObjectID` nhà thầu **do người có thẩm quyền xác nhận một lần**; `TC-04`/`TC-07` là text, không phải mã [AUDIT-RV §3.3, §5.3]. Không fuzzy tên.
- Catalog tham số đọc **động** từ rows/mã thực (`DS_THAM_SO`, mã `Y-*`), không hardcode 36/37 [AUDIT-RV §3.3].

| Gói | Phủ | Tái dùng | Nối/viết thêm | Thiết kế còn hoàn thiện | Phụ thuộc | Nghiệm thu bấm |
|---|---|---|---|---|---|---|
| **C3a · Bridge kết quả review #5 (DEMO đầy đủ)** | M4; HDTHAU, NT; R_REV | JSON `kiem_tra_dot` (`ma, hop_dong{ma_hd,so_hd,phan_loai}, dot, ngay_nghiem_thu, gt_hieu_luc, loai_gia, vat, phu_luc_ap_dung, de_nghi, tong_hop, da_nap, tai`); `chi_tiet_hop_dong` `tham_so[]`+provenance; export `DOT_THANH_TOAN` làm fallback [AUDIT-RV §3–4] | Adapter đọc JSON/export (pha 1, K1), chuẩn hóa thành hồ sơ nghiệm thu có provenance + snapshot; bảng mapping chờ xác nhận; trường "số được hạch toán" + người xác nhận; quan hệ thay thế. Pha 2 (V16): `giao_tiep.v1_ghi_ket_qua_review` → `v1_nghiem_thu_da_kiem` (thiết kế TL40, chưa có ở #5) | Ai là người có thẩm quyền xác nhận số hạch toán (vai trò, không phải cơ chế) | N2, N3 (DEMO trên SQLite); pha 2 cần N4 | 6 ca DEMO: nhận mới; nhận lại cùng `ma` → 0 mới; nạp lại thay → bản mới `supersedes`, bản cũ không còn hiệu lực; thiếu mapping → chờ; thiếu số xác nhận → chờ, không có số 0; `da_nap=true` không làm dòng thành "đã duyệt" |
| **C3b · M4 đề xuất bút toán + L3** | M4, M2, L3 | C3a; C2b đích 241 | Đề xuất 241/154 + 1331 / 331; thu hồi tạm ứng theo `thu_hoi_tu`, giữ lại đợt (TT-21) và bảo hành (TT-31) tách dòng; hóa đơn nhà thầu chỉ Xanh khi có liên kết NT_HOP_DONG/HD_NGHIEM_THU đã xác nhận | 241 hay 154 theo loại dự án | C3a, C2b, N1 | HĐ thầu trước NT → tối đa Vàng; NT xác nhận về → liên kết, nâng mức; không dùng `anh_huong` |
| **C3c · L7 lãi vay vốn hóa** | M9→M4, L7 | C4a lịch lãi | Lãi kỳ của khoản vay gắn dự án → 241 theo chính sách đã duyệt; không tự đặt tỷ lệ | Chính sách vốn hóa | C4a, C3b | Chưa có chính sách → không vốn hóa, ghi lý do |
| **C3d · L5 XDCB → tài sản; L6 bàn giao → giá vốn** | M4→M6, M4→M3 | `tai_san.nguon_241` [SRC schema]; C1d | 241→211 theo quyết toán, mã tài sản duy nhất; giá vốn mức dự án khi bàn giao | Cách phân bổ giá vốn mức dự án | C3b, C6a, C1d | Quyết toán → 1 tài sản; nhận lần 2 bị chặn |

### C4 · Vốn vay & đầu tư tài chính (M9, L8; cấp L7)

Phạm vi theo TL29 §10, TL31 #9, TL33 (HDVAY: "HĐ vay / LC / bảo lãnh — lịch trả gốc, lãi; gắn dự án"), TL29 §10.2 (covenant, hạn mức, bảo lãnh **theo dõi** ngoài đợt). Không tự mở giám sát covenant/hạn mức.

| Gói | Phủ | Tái dùng | Nối/viết thêm | Thiết kế còn hoàn thiện | Phụ thuộc | Nghiệm thu bấm |
|---|---|---|---|---|---|---|
| **C4a · Contract #9 vay dài hạn** | M9; HDVAY; R_VAY | `DaiHan`, `KheUoc`, `LichTraGoc`, `LichLaiSuat`, `PhatSinh` (khóa `maKV`, `maKheUoc`) [AUDIT-DM §4] | Adapter chỉ đọc (Sheets API/export whitelist) **khóa một phiên bản schema** (`Code.gs` vs deploy `Code.js`), snapshot+hash → `hop_dong loai=VAY` + `lich_tra_no`; map công ty → pháp nhân, dự án → `ProjectID`; không dùng nguyên response `load` (có dữ liệu phụ) | Xác nhận phiên bản deploy thực dùng | N3; mở mạng Google = cổng vận hành | Snapshot DEMO hai phiên bản: chỉ phiên bản đã khóa được nhận, phiên bản kia báo "schema không hỗ trợ"; chạy lại không trùng; lịch đổi → phiên bản mới |
| **C4b · L8 lịch ↔ sao kê** | M9, M1, L8 | M1 [SRC]; `PhatSinh` có tham chiếu chứng từ [AUDIT-DM §4] | Khớp giải ngân/gốc/lãi/phí theo NH + tiền + kỳ; lệch → Vàng có phân loại | — | C4a, N1 | Trả gốc đúng lịch → Xanh 341/112; lãi lệch → Vàng có lý do |
| **C4c · Vay ngắn hạn, LC, bảo lãnh** | M9; HDVAY (LC/bảo lãnh) | Bảng ngắn hạn/LC/hợp đồng mua/hạn mức trong #9 [AUDIT-DM §4] | Nhận khế ước ngắn hạn và LC như hợp đồng tài chính có lịch/phí; khớp phát sinh (mở LC, ký quỹ, phí, thanh toán LC, phí bảo lãnh) với sao kê → đề xuất M1; hạn mức chỉ đọc làm thông tin | Mẫu bút toán LC/ký quỹ/phí bảo lãnh (CFO) | C4a | DEMO: mở LC + ký quỹ + phí → 3 dòng sao kê khớp đúng loại; không có cảnh báo covenant/hạn mức |
| **C4d · Đầu tư tài chính** | M9 "đầu tư tài chính" | Sổ Junsky lịch sử (đối chiếu TK liên quan) [SRC `read_journal_rows`]; lãi tiền gửi đã là loại tự duyệt M1 (TL29 §1.5) | **Hoàn thiện đặc tả trước khi code**: kiểm kê từ sổ lịch sử các nghiệp vụ đầu tư tài chính thực có (tiền gửi có kỳ hạn, góp vốn…) và nguồn hồ sơ; lập contract cho loại có nguồn | Danh sách loại nghiệp vụ và nguồn chứng từ (từ kiểm kê, CFO xác nhận) | N3 | Bảng kiểm kê loại × số chứng từ × nguồn (aggregate) được duyệt; mỗi loại đã duyệt có ca DEMO khớp sao kê |

### C5 · Thuế (M8, L9)

| Gói | Phủ | Tái dùng | Nối/viết thêm | Thiết kế còn hoàn thiện | Phụ thuộc | Nghiệm thu bấm |
|---|---|---|---|---|---|---|
| **C5a · XML ↔ bảng kê ↔ sổ** | M8; BK, XMLM, XMLB | `bang_ke` + `ttxly` [SRC]; #7 nguyên trạng [AUDIT-DM §3] | Đối chiếu 3 chiều, thiếu/trùng/hủy/thay thế; **không bút toán** | Phương pháp Check VAT Excel (TL31 mục C) | N3 | XML không trên bảng kê → "thiếu"; hóa đơn hủy có bút toán → "lệch" |
| **C5b · L9 điều kiện khấu trừ** | L9 | N1 (C2c) | Cờ đủ điều kiện khi có thanh toán không tiền mặt ≥ ngưỡng hiện hành | Văn bản hiện hành | C5a, C2c | Thiếu liên kết thanh toán → "chờ chứng từ thanh toán" |

### C6 · Tài sản (M6, L4, L5)

| Gói | Phủ | Tái dùng | Nối/viết thêm | Thiết kế còn hoàn thiện | Phụ thuộc | Nghiệm thu bấm |
|---|---|---|---|---|---|---|
| **C6a · Hồ sơ tài sản + L4** | M6, L4 | `master.tai_san` [SRC schema]; C2b đích TAI_SAN | Dòng đích tài sản → ghi tăng 211/213/153 + mã tài sản; nguồn ghi tăng duy nhất | Ngưỡng TSCĐ hiện hành | C2b | Không ghi tăng lần 2 cùng dòng |
| **C6b · Bộ đọc khấu hao/242 (R_KH)** | KH; R_KH; L12 | `chung_tu loai=BANG_KHAU_HAO` [SRC schema] | Bộ đọc mẫu cố định theo kỳ, kiểm tổng, đối chiếu tài sản; **lưu lịch** cho C9a | Mẫu bảng (TL30 D1) | N3, C6a | Bảng kỳ DEMO tổng khớp; tài sản lạ → cảnh báo |

### C7 · Lương (M7, L10)

| Gói | Phủ | Tái dùng | Nối/viết thêm | Thiết kế còn hoàn thiện | Phụ thuộc | Nghiệm thu bấm |
|---|---|---|---|---|---|---|
| **C7a · Bộ đọc bảng lương (R_BL)** | M7; BL | `nhan_vien`, `chung_tu loai=BANG_LUONG` [SRC schema] | Đọc đầu ra HR: tổng, mã `NV.x`, phân bổ → TTCP/dự án; **không tính lương**; gửi AI ngoài chỉ theo cổng chung TL35 (Mask, loại chứng từ được duyệt) — cổng chưa kích hoạt nên hiện không gửi; không áp lệnh cấm riêng cũ của TL34 | Mẫu bảng lương + phân bổ (TL30 E) | N3 | Tổng khớp; mã NV lạ chặn |
| **C7b · L10 lương ↔ chi lương** | L10 | M1 [SRC] | Khớp tổng thực lĩnh ↔ lệnh chi lô/nhiều lệnh | — | C7a, N1 | Thiếu 1 NV → "thanh toán chưa đủ" |

### C8 · Kho vận hành KCN — chỉ số lượng (M5, L11)

| Gói | Phủ | Tái dùng | Nối/viết thêm | Thiết kế còn hoàn thiện | Phụ thuộc | Nghiệm thu bấm |
|---|---|---|---|---|---|---|
| **C8a · Đọc phiếu #10 (R_KHO)** | M5; PNX | Code vận hành phiếu: tạo/duyệt/đảo, `{phieu,lines}`, kiểm kê, `MaDoiTuong_KT` [AUDIT-DM §5] | Đọc **phiếu đã duyệt và phiếu đảo** (`SoPhieu_Goc`) qua Sheets API/`{phieu,lines}`; bảo toàn khóa phiếu/dòng; số lượng; **không dựa vào `exportToExcel`** (chưa chứng minh bytes) | Mapping kho/bộ phận/dự án | N3 | Phiếu nhập 10, xuất 4, đảo 1 → tồn đúng; không cột/bút toán giá trị |
| **C8b · L11 phiếu nhập ↔ hóa đơn vật tư** | L11 | C2b đích KHO | Liên kết HD_PHIEU_KHO theo NCC/`MaDoiTuong_KT`/số lượng; phiếu trước HĐ → Vàng | — | C8a, C2b | HĐ 10 ↔ phiếu 8 → lệch số lượng |

### C9 · Định kỳ, đóng sổ, đối chiếu ngược (M10, L12)

| Gói | Phủ | Tái dùng | Nối/viết thêm | Thiết kế còn hoàn thiện | Phụ thuộc | Nghiệm thu bấm |
|---|---|---|---|---|---|---|
| **C9a · Bộ sinh lô định kỳ** | M10, L12 | **Đọc lịch đã lưu** từ C1d (DT), C6b (khấu hao/242), C4a (lãi dự trả), 335 | Lô 02GJ theo kỳ; so kỳ trước; khóa chống lặp kỳ | Bộ đọc lịch 335 (TL30 D2) | Lịch tương ứng có sẵn (không ngược lại), N5 | Chạy kỳ 2 lần → 1 lô; kỳ khóa → từ chối |
| **C9b · Checklist đóng sổ** | M10 | `khoa_ky`, `month-close` [SRC] | Checklist việc/người/hạn | Checklist hiện dùng | N2, N5 | Còn dòng treo → liệt kê, không khóa kỳ; **không tự chuyển treo → Vàng** khi chưa có căn cứ/quy tắc CFO đã duyệt |
| **C9c · Đối chiếu ngược mọi lô** | M10, L12 | `shadow-reconcile` [SRC], N5 | Sổ sau nạp ↔ lô; 4 nhóm; lệch → V1 điều chỉnh | Mẫu xuất sổ + `EntryID` | N5; **thật: cổng Junsky** | DEMO 5 dòng: THIEU 1, THUA 1; chỉ KHOP được học |

## 5. Ma trận coverage

**Module:** M0 N1–N8 · M1 hiện có + C1b, C2c, C4b, C4c, C7b · M2 C2a–C2c, C3b, C6a, C8b · M3 C1a–C1e, C3d · M4 C3a–C3d · M5 C8a–C8b · M6 C6a–C6b, C3d · M7 C7a–C7b · M8 C5a–C5b · M9 C4a–C4d, C3c · M10 C9a–C9c, N5.

| Nguồn | Chứng từ | Bộ tiếp nhận | Gói |
|---|---|---|---|
| Ngân hàng | SK | R_SK [SRC] | hiện có; N3 |
| Ngân hàng | UNC | R_SK | C2c |
| Cổng thuế | XMLM / XMLB / BK | R_HD — #7 tương thích [AUDIT-DM §3] | C2b / C1c / C5a |
| Base | RQ | R_BASE — #8 tương thích [AUDIT-DM §3] | C2a |
| Hợp đồng | HDKCN, HDNO | R_CRM (#6) | C1a |
| Hợp đồng | BBG | R_CRM | C1d |
| Hợp đồng | HDTHAU | R_REV (#5) | C3a |
| Hợp đồng | HDVAY (vay/LC/bảo lãnh) | R_VAY (#9) | C4a, C4c |
| Ban QLDA | NT | R_REV (#5) | C3a |
| Nhân sự | BL | R_BL (mới) | C7a |
| Kho KCN | PNX | R_KHO (#10) | C8a |
| Kế toán | KH (khấu hao · 242 · 335 · lịch DT KCN) | R_KH (mới) | C6b, C9a, C1d |

**Liên kết:** L1 C1b · L2 C2c · L3 C3b · L4 C6a · L5 C3d · L6 C3d · L7 C3c · L8 C4b · L9 C5b · L10 C7b · L11 C8b · L12 C9a–C9c.

## 6. Phụ thuộc thật (đồ thị không vòng)

```
N3 ─┬─► C2a ─► C2b ─┬─► C2c ─► C5b
    │               ├─► C6a ─► C6b ─┐
    │               └─► C8a ─► C8b  │
    ├─► C1a ─► C1b, C1c ; C1a ─► C1d ┼─► C9a ─► C9b      (C1d, C6b, C4a SẢN XUẤT lịch; C9a chỉ đọc)
    ├─► C3a ─► C3b ─► C3d (cần C6a, C1d)  │
    ├─► C4a ─► C4b, C4c ; C4a ─► C3c ─────┘
    ├─► C5a ; C4d ; C7a ─► C7b
N1 ─► mọi gói có liên kết L* ; N2 ─► mọi gói có duyệt ; N5 ─► C9a, C9c
N4 (V14, PG) ─► pha 2 của C3a/C2a ; N6 ─► chỉ khi cần LLM ; N7 ─► mọi "Hỏi"
```

- Không còn phụ thuộc vòng C1d ↔ C9a: C1d sản xuất và lưu lịch đã duyệt; C9a chỉ đọc lịch.
- V13 A1–A6, backtest clean-cutoff, V14, cloud AI, mức 2 **không** là cổng của thiết kế/adapter/bridge DEMO; chúng chỉ chặn đúng thao tác liên quan (§2.4).
- Thứ tự đã chốt sau M1–M3 (M4 → M9 → M8) giữ trong C3 → C4 → C5; M5/M6/M7/M10 chạy song song khi có mẫu/nguồn.

## 7. Quyết định nghiệp vụ còn thiếu thật sự (gom một lần; không hỏi lại kiến trúc hay thông tin đã có trong source)

1. Bộ tham số + mẫu bút toán theo từng loại hình doanh thu (KCN, nhà ở), chính sách ghi nhận/phân bổ (C1a, C1c, C1d); trường hợp Nợ 138 (C1c).
2. Vai trò người có thẩm quyền xác nhận **số được hạch toán** và mapping #5 (C3a); 241 hay 154 theo loại dự án (C3b).
3. Chính sách vốn hóa lãi vay (C3c); mẫu bút toán LC/ký quỹ/phí bảo lãnh (C4c); danh sách nghiệp vụ đầu tư tài chính sau kiểm kê (C4d).
4. Hai bảng ánh xạ nhóm G và chủ danh mục loại chi phí với #1 (C2b); `DEBT_ACCOUNTS` (N2).
5. Phiên bản schema #9 đang deploy (C4a) — xác nhận vận hành, không thiết kế lại.

Mẫu do phòng ban cung cấp (không phải quyết định): bảng lương + phân bổ, khấu hao/242/335/lịch DT, checklist đóng sổ, mẫu xuất sổ Junsky + 3 câu nhà cung cấp, hợp đồng mẫu mỗi loại hình.

## 8. Gói kế tiếp

1. **C3a · Bridge kết quả review #5 → M4, DEMO đầy đủ theo contract đã audit** (§4 C3): adapter JSON/export pha 1, hồ sơ nghiệm thu có provenance + snapshot, mapping chờ xác nhận, số hạch toán xác nhận riêng, khóa instance+`ma_hd`+`dot`+`ma`, `supersedes`, 6 ca DEMO. Không chờ V14/PG.
2. **N1 + C1b-lõi · Liên kết là dữ liệu cho M1** — hết hạch toán lặp khi chứng từ đến sau, nền mọi L.
3. **C2a + C2b · RQ ↔ hóa đơn mua, một dòng một đích** — giảm Đỏ/Vàng mua lẻ, tạo đích dòng cho M4/M6/M5.

## 9. Ranh giới
Phương án C V13, kho thật SQLite, K2 core ở V14; K1–K5; 9 master; M5 chỉ số lượng; Sheets theo TL40; không xây lại HR/tính lương, review BOQ, tải hóa đơn, sổ cái/BCTC/tờ khai; engine/UI nguồn giữ nguyên; app trong nhà qua `giao_tiep` role riêng, app ngoài qua K1/API; cloud AI tắt; không Junsky mức 2/nhập/duyệt thật, không `CFO_NTD`; DEMO actor `MO_PHONG_`. Tài liệu không tuyên bố phần mềm hoàn thành.
