# Hợp đồng tích hợp và tái sử dụng — 9 bộ tiếp nhận và các app nguồn (file 33)

Ngày lập: 18/10/2026 · sửa lần 2 cùng ngày theo `TAI-SU-DUNG-REVIEW-XAY-DUNG.md` và `DANH-MUC-TAI-SU-DUNG-PHAN-MEM.md` · Người soạn: Claude Code · Codex kiểm độc lập.
Trạng thái: **hợp đồng để triển khai bridge, chưa nghiệm thu**. Mã gói N*/C* theo `LO-TRINH-TRIEN-KHAI-TOAN-BO-33.md`.
Nhãn: **[SRC]** đọc trong repo này · **[AUDIT-RV]** audit #5 · **[AUDIT-DM]** audit các app khác · **[TL]** đã chốt · **[DỰ THẢO]** đề xuất. Audit là kiểm tĩnh: có code ≠ đã triển khai/đúng trên dữ liệu thật; số dòng trích dẫn là của source nguồn theo audit.

## 1. Quy tắc chung

| Mục | Quy tắc | Căn cứ |
|---|---|---|
| Không làm lại | Engine/UI/nghiệp vụ của app nguồn giữ nguyên; kế toán nhận kết quả, map khóa, duyệt kế toán. Lệch engine nguồn sửa tại nguồn có kiểm chứng, không dựng engine cạnh tranh | TL31 §0, TL35 §5.2; [AUDIT-RV §6] |
| Kênh | Trong nhà (#1, #2, #5, #6, #7, #8, #14) → `giao_tiep` role riêng (V14+) hoặc K1 đọc file/JSON đã xuất. Ngoài/Sheets (Junsky, Base SaaS, Frappe HR, #9, #10, #11) → K1/API chỉ đọc. Không mở server nguồn ra LAN, không gọi hàm nguồn có tác dụng ghi (vd `mo_csdl()` của #5) để "đọc" | TL40 §4–6; [AUDIT-RV §2, §4] |
| Hai trạng thái độc lập | Trạng thái của app nguồn (đã nạp, đã kiểm, `TrangThai` phiếu, `status` job) **không** là duyệt kế toán; duyệt kế toán đi workflow M0 (N2) | [AUDIT-RV §3.1, §7]; [AUDIT-DM §2] |
| Khóa chung | pháp nhân · `ObjectID` Junsky · số hóa đơn (ký hiệu+số+MST bán) · mã HĐ chung (namespace theo instance nguồn) · `ProjectID` · mã RQ · mã tài sản · `EntryDM` · mã lô. Junsky cấp mã; mapping nguồn → mã chung **do người có thẩm quyền xác nhận**, không fuzzy theo tên/text | TL35 §3A, §4; [AUDIT-RV §5.3] |
| Phiên bản contract | Mỗi adapter ghi `contract_version` + phiên bản schema nguồn; field lạ/thiếu → cảnh báo, không đoán | [AUDIT-DM §9.3] |
| Idempotency | Khóa nguồn duy nhất theo (pháp nhân, loại, `khoa_nguon`); nhận lại cùng nội dung → 0 bản ghi; nguồn thay thế cùng sự kiện → bản mới `supersedes` + lý do, không thêm công nợ | TL38 §0.3; [AUDIT-RV §5.2] |
| Provenance | `tep_goc` (đường dẫn+hash) hoặc ID kết quả nguồn; ba mốc thời gian; trường LLM có `trich_dan`, tối đa Vàng | TL38 §0.5, §0.9 |
| Quyền | Role theo app, `NOINHERIT`, chỉ view/hàm cần; RLS pháp nhân; bí mật trong `.env` của app đó | TL40 §5, §8 |
| Dữ liệu ra ngoài | Chỉ qua cổng AI sau Mask bảy nhóm; cloud AI đang tắt; đường gọi AI trực tiếp của app nguồn (#14 `brain.py`, #6 Ollama) không dùng cho dữ liệu kế toán ngoài cổng | TL35 §3; [AUDIT-DM §2, §8] |

## 2. Ma trận 9 bộ tiếp nhận

| Bộ tiếp nhận · chứng từ | App nguồn · lớp | Interface / kết quả sẵn có | Bridge tối thiểu vào K2 | Chủ · phiên bản · khóa | Test bắt buộc |
|---|---|---|---|---|---|
| **R_SK** · SK, UNC | Bộ đọc eFAST trong repo · nội bộ | [SRC] `ThatAdapter("sao_ke")` .xlsx/.xls/.pdf, nhận TK, kiểm tổng; `QuickPosting` M1. UNC: chưa có bộ đọc riêng | `chung_tu loai=SAO_KE`; `LENH_CHI` khi chốt nguồn UNC | Kế toán; khóa mã tham chiếu NH + ngày + tiền + TK (D04) | [SRC] chống trùng, coverage, cách ly; UNC cùng giao dịch sao kê → 1 liên kết |
| **R_HD** · XMLM, XMLB, BK | #7 Tải HĐĐT (Node/Playwright) · trong nhà | [AUDIT-DM §3] `job.js:125–158` ghi XML/PDF/bảng kê theo kỳ/chiều, `:226–227` bảng kê; `server.js:41/:64` `/api/start`, `/api/events`. **Tương thích ngay** [SRC] `that.py:459` `_xml_rows`, `:478` `_invoice_table_rows` | Thêm **manifest phiên tải**: pháp nhân, kỳ/chiều, lúc lấy, file/hash, thành công/thiếu/lỗi; kỳ thư mục ≠ thời điểm biết. #7 giữ nguyên, không ghi CSDL, không đưa tài khoản cổng thuế vào kế toán | #7 sinh file; kế toán chủ bản ghi; khóa MST bán + ký hiệu + số | Chạy lại cùng phiên → 0 mới; XML + bảng kê cùng hóa đơn → 1 chứng từ, 2 bằng chứng; phiên thiếu file → cảnh báo, không coi đủ kỳ |
| **R_BASE** · RQ | #8 Backup Base · trong nhà; Base SaaS · ngoài | [AUDIT-DM §3] `backup_requests.py:649–736` bundle `id, fetched_at, get, custom_table, posts, _attachment_results` → `requests/request_<id>/request_<id>.json`, `attachments_manifest.json`; `:853` index Excel. **Parser repo đã khớp** [SRC `that.py:502–549`] | Canonical RQ (TL31) → `chung_tu loai=RQ`; kiểm field form + tiền tệ, thiếu → cách ly; **không dùng cột tiền index Excel** (README nguồn: best-effort, chưa rõ đơn vị). #2 Request sau go-live: adapter mới vào cùng canonical | #8/#2; khóa ID RQ; `known_at` = max `fetched_at` [SRC] | Nạp 2 lần → 0 mới; thiếu tổng → `BASE_AMOUNT_MISSING` [SRC]; Base→#2 cùng RQ không tạo bản thứ hai |
| **R_CRM** · HDKCN, HDNO, BBG | #6 Trích tham số HĐ (Local AI `hop_dong`) · trong nhà | [AUDIT-DM §2] đầu vào là **Word DOC/DOCX** qua `doc_reader.py:292` `read_contract` (thả PDF không phải khả năng mặc định; PDF cần tầng đọc/OCR #12 riêng); `cau_truc_hop_dong.py:62/126/165`; `trich_xuat_v3.py:460` `process`, `:255` kiểm trích dẫn, `:623–638` xuất `*_KET_QUA.json` (`hop_dong, che_do, model, tao_luc, tham_so[], phieu_kiem_tra`; mỗi tham số `ma, nhom, tham_so, gia_tri, don_vi, dieu_khoan, trich_dan, ghi_chu, kiem_tra, vi_tri_do_duoc`); `giao_dien.py` chạy/trạng thái. #5 cũng có engine trích (`trich_xuat.quy_trinh.TrichXuat`) [AUDIT-RV §4] | JSON + hash file nguồn → `hop_dong` + `hop_dong_phien_ban` (CHO_DUYET, `nguon=#6`/`BAN_HANG`) + `hop_dong_tham_so` (`trich_dan` bắt buộc) → V3 CFO → `lich_thu`. `kiem_tra` nguồn chỉ là chất lượng trích, không phải duyệt. Đáp án mẫu không dùng làm nhãn học tự động. Lịch thu theo loại hình là **phần thêm** (nguồn chưa có CRM lịch thu) | Hợp đồng ký → danh mục hệ thống là nguồn duy nhất (TL32 §3.3); phụ lục = phiên bản; khóa (pháp nhân, loại, số HĐ) | Trích lại cùng file (cùng hash) → không phiên bản mới; thiếu trích dẫn → NULL; BAN_HANG không sửa bản đã duyệt; đường AI của #6 không dùng cho cloud ngoài cổng N6 |
| **R_REV** · HDTHAU, NT | #5 Review xây dựng (Python, 127.0.0.1:8600) · trong nhà | [AUDIT-RV §2–4] CSDL SQLite là nguồn (`csdl_hop_dong.py:5`, schema `:76`), đợt PK `(ma_hd, dot)` (`:133`), `ma_hd` tự sinh `HD…` (`:325`), `so_hd` UNIQUE (`:81`); JSON `kiem_tra_dot` (`may_chu/nghiep_vu.py:863`, payload `:898–914`: `ma, loai, luc, tep, hop_dong{ma_hd,so_hd,phan_loai}, dot, dot_truoc, ngay_nghiem_thu, gt_hieu_luc, loai_gia, vat, phu_luc_ap_dung[], de_nghi, o_de_nghi, tong_hop{gt_hd,gt_lk_kt,gt_kn,gt_lk,giu_lai,thu_hoi_tu,tt_ky_nay}, anh_huong, phat_hien[], bang_k…, da_nap, tai{lop1,lop2}`); `doc_ket_qua_kiem_tra` (`:822`); API `GET /api/hop_dong/{ma_hd}?ngay=` (`server.py:311`), `GET /api/kiem_tra/kiem_tra_dot/{ma}` (`:363`); export CSDL 8 sheet gồm `DOT_THANH_TOAN` (`csdl_hop_dong.py:1686`); engine hiệu lực `tham_so_hieu_luc` (`:405`), `phu_luc_ap_dung` (`:352`) | Xem §3 (hợp đồng chi tiết). **Bridge DEMO pha 1 đã có code** [SRC `nguon/review_xay_dung.py`, `de_xuat/nghiem_thu.py`, mục "Hồ sơ nghiệm thu" shell DEMO; `tests/test_nghiem_thu_bridge.py`] — chưa phải production. Pha 1 K1 đọc JSON/export; pha 2 `giao_tiep.v1_ghi_ket_qua_review` (TL40 — **chưa có trong #5**) | #5 chủ HĐ/tham số/review/phụ lục; kế toán chủ quyết định hạch toán; khóa instance + `ma_hd` + `dot` + `ma` | §3.4 |
| **R_VAY** · HDVAY (vay, LC, bảo lãnh) | #9 Theo dõi khoản vay (Sheets + Apps Script) · nguồn đọc | [AUDIT-DM §4] `KHOA-CAU-TRUC-VAY-DAI-HAN.md:13–29` khóa 5 sheet `DaiHan, KheUoc, LichTraGoc, LichLaiSuat, PhatSinh` (khóa `maKV`, `maKheUoc`; phát sinh có `id`, ngày, gốc/lãi/phí, tham chiếu chứng từ); `Code.js:37–60` cột dài/ngắn hạn/LC/HĐ mua/hạn mức, `:110` `load/loadMaster`, `:233–282` trả `longLoans, kheUoc, lichGoc, laiSuat, phatSinh, hopDongMua, vayNganHan, hanMuc`; `Index.html:1719/1760/1807` export Excel/Lãi/JSON. **Hai bộ source khác phiên bản**: `Code.gs` 920 dòng vs deploy `Code.js` 1.203 dòng (deploy thêm `maKheUoc` ở lịch gốc) | Adapter chỉ đọc (Sheets API service account hoặc export whitelist) **khóa một phiên bản schema đã xác nhận đang deploy**; snapshot + hash; whitelist sheet/field (không dùng nguyên response `load`); `maKV/maKheUoc` ↔ `hop_dong` VAY; công ty ↔ pháp nhân; dự án ↔ `ProjectID`; LC/ngắn hạn → hợp đồng tài chính có lịch/phí; hạn mức chỉ đọc làm thông tin, không giám sát covenant | Tài chính/pháp chế chủ Sheet; khóa `maKV` + `maKheUoc`; phiên bản theo thời gian cho lịch/lãi suất | Snapshot sai phiên bản → từ chối "schema không hỗ trợ"; chạy lại không trùng; đổi lịch → phiên bản mới, kỳ đã khớp giữ liên kết; mở mạng Google = cổng vận hành riêng |
| **R_BL** · BL | Đầu ra HR (Excel; Frappe HR #4 khi xuất được) · ngoài | Chưa có bộ đọc; HR chưa có lương [TL31]. Mẫu bảng do Nhân sự cung cấp | `chung_tu loai=BANG_LUONG` + dòng NV; `nhan_vien` (`NV.x`); bảng phân bổ (CFO duyệt) | Nhân sự; khóa pháp nhân + kỳ + phiên bản | Nộp lại cùng kỳ khác nội dung → phiên bản mới; lô cũ chưa xuất thì hoàn tác có nhật ký, đã xuất/nạp thì giữ lô cũ và lập điều chỉnh; kiểm tổng; AI ngoài chỉ theo cổng chung TL35 (chưa kích hoạt), không lệnh cấm riêng cũ |
| **R_KHO** · PNX | #10 Quản lý kho (Sheets + Apps Script, PWA) · nguồn đọc | [AUDIT-DM §5] 9 sheet (`DM_HangHoa, DM_Kho, DM_DoiTac, DM_Nhom, GD_Phieu, GD_Dong, GD_KiemKe, HT_CauHinh, HT_NhatKy`); header `SoPhieu, LoaiPhieu, NgayChungTu, MaKho, MaDoiTac, TrangThai`, người/lúc duyệt, `SoPhieu_Goc`; detail `ID_Dong, SoPhieu, MaHang, SoLuong, GhiChu`; `DM_DoiTac.MaDoiTuong_KT`; `Code.gs:202/246/275` tạo/duyệt/đảo, `:328–360` `{phieu, lines}`, `:419` kiểm kê, `:688` POST action. `exportToExcel` (`:459–507`) trả `{fileName,url}`, **chưa chứng minh bytes XLSX/CSV** | Đọc **phiếu đã duyệt + phiếu đảo** qua Sheets API hoặc `{phieu,lines}` → `chung_tu loai=PHIEU_KHO` + dòng số lượng; bảo toàn `SoPhieu`/`ID_Dong`; `MaDoiTuong_KT` → `ObjectID`; nối HĐ/yêu cầu cấp phát/dự án/bộ phận. Không phụ thuộc `exportToExcel`; không nối Apps Script vào PostgreSQL | Thủ kho chủ phiếu; giá trị ở Junsky (TL35 §8.6); khóa `SoPhieu` (+ `ID_Dong`) | Đọc lại → 0 mới; phiếu đảo → bút trừ số lượng có liên kết `SoPhieu_Goc`; phiếu chưa duyệt → không nhận; kiểm tĩnh: không trường giá trị vào bút toán |
| **R_KH** · KH (khấu hao, 242, 335, lịch DT KCN) | Bảng nội bộ kế toán đã duyệt · nội bộ | Chưa có bộ đọc; mẫu do kế toán cung cấp (TL30 D1–D2) | `chung_tu loai=BANG_KHAU_HAO` (và loại tương ứng) → **lịch lưu** cho C9a; đối chiếu `tai_san` | Kế toán TSCĐ/tổng hợp; khóa pháp nhân + loại bảng + kỳ + phiên bản | Cùng kỳ hai lần → 1 lịch; tổng bảng ≠ tổng dòng → chặn |

## 3. Hợp đồng chi tiết #5 → M4 (C3a, C3b)

### 3.1 Nhận gì
- Chỉ kết quả loại `kiem_tra_dot`; chế độ chỉ toàn vẹn (`toan_ven`) không đủ cho M4 [AUDIT-RV §5.1].
- Snapshot tại đúng `ngay_nghiem_thu`: `gt_hieu_luc`, `loai_gia`, `vat`, `phu_luc_ap_dung[]` và tham số hiệu lực lấy bằng engine nguồn (`tham_so_hieu_luc`, `phu_luc_ap_dung`), không lấy tham số gốc hay "hôm nay" [AUDIT-RV §3.3].
- Catalog tham số **động** theo mã thực (`DS_THAM_SO`, cả mã `Y-*`); không hardcode 36/37 [AUDIT-RV §3.3].

### 3.2 Ý nghĩa số tiền — không đổi nghĩa
| Trường nguồn | Giữ trong hồ sơ M4 | Không được làm |
|---|---|---|
| `de_nghi`, `o_de_nghi` | Số **đề nghị** đọc từ hồ sơ | Coi là số chấp nhận |
| `tong_hop.gt_kn` / `gt_lk` | Giá trị kỳ / lũy kế đọc theo nhãn (`master_hd.py:790–823`) | Thay số không đọc được bằng 0 |
| `tong_hop.giu_lai` | Giữ lại **đợt** — đối chiếu tham số `TT-21` | Gộp với bảo hành |
| tham số `TT-30/31/32/33` | Bảo hành / bảo lãnh bảo hành / thời hạn / bảo lãnh thực hiện — **tách** khỏi giữ lại đợt | Suy từ `giu_lai` |
| `tong_hop.thu_hoi_tu` | Thu hồi tạm ứng (đối chiếu `TT-10/11/12`) | — |
| `tong_hop.tt_ky_nay` | Thanh toán kỳ này đọc từ hồ sơ | Coi là đã duyệt hạch toán |
| `anh_huong`, `phat_hien[]` | Tham chiếu bằng chứng (lũy kế, chưa VAT) | **Tính `de_nghi − anh_huong`** hoặc cộng/trừ findings |
| `da_nap` | Dấu "đã nạp vào CSDL review" | Coi là duyệt kế toán |

**Số được hạch toán** = trường xác nhận riêng (số, cơ sở trước/sau VAT, người xác nhận, thời điểm, căn cứ) gắn với snapshot review. Thiếu → hồ sơ "chờ xác nhận", không mặc định 0, không sinh dòng đủ điều kiện xuất [AUDIT-RV §5.4, §7].

### 3.3 Khóa, phiên bản, mapping
- Khóa nhận: `(instance_nguon, ma_hd, dot, ma)`; `instance_nguon` là namespace cấu hình (một #5 có thể chạy trên 1–2 máy — TL40 §1). `so_hd` chỉ là bằng chứng phụ.
- Nạp lại/thay đợt ở #5 (có lý do theo nguồn) → hồ sơ mới `supersedes` hồ sơ cũ; bản cũ hết hiệu lực; nếu bản cũ đã sinh đề xuất kế toán → việc V1 điều chỉnh, không thêm công nợ.
- Mapping `(instance, ma_hd)` → pháp nhân, mã HĐ chung, `ProjectID`/giai đoạn, `ObjectID` nhà thầu: bảng mapping chờ xác nhận, người có thẩm quyền duyệt một lần; không suy từ `TC-04`/`TC-07`/`ben_b` (text) [AUDIT-RV §3.3, §5.3].
- Không thêm gate "tổng NT ≤ giá trị HĐ" chung mọi loại giá; quy trình đơn giá cố định và lệch engine B1 đã ghi nhận thuộc nguồn [AUDIT-RV §6].

### 3.4 Ca kiểm bắt buộc (DEMO)
1. Nhận mới → hồ sơ có provenance (`ma`, file, `luc`, link báo cáo `tai`).
2. Nhận lại cùng `ma` → 0 bản ghi mới.
3. Nạp thay cùng `(ma_hd, dot)` với `ma` mới → bản mới `supersedes`, bản cũ hết hiệu lực.
4. Thiếu mapping → chờ, không đề xuất bút toán.
5. Thiếu số được hạch toán → chờ, không có số 0, không xuất.
6. `da_nap` có giá trị → trạng thái kế toán vẫn "chờ duyệt".
7. Kiểm tĩnh: không có biểu thức `de_nghi - anh_huong` trong bridge.

## 4. App tái dùng khác

| App | Lớp | Tái dùng | Bridge tối thiểu | Không làm | Xác minh |
|---|---|---|---|---|---|
| Junsky | Ngoài | Danh mục, công nợ mở (có *Hợp đồng vay*), sổ NKC/dgbList | K1 [SRC `_junsky_rows`, `_open_items`, `read_journal_rows`]; `CB_tmpEntry1/2` mức 2 khóa [SRC `xuat/shadow.py`] | Nhập thật, sinh mã | [SRC] |
| #11 Nước thải | Nguồn đọc (Sheets) | Jobs (`batch_id, company_id, period, status, source_fingerprint`) `Code.gs:429`, chống trùng `:453–479`, `MASTER_COLUMNS` có ObjectID `:710`, OCR schema `:587`/`apiIngestOcrBatchFromClient_` `:1719`, SELLING1/2 theo **`SM_tmpSelling1/2`** `:1266–1344`; `AppsScript/Code.gs` = `apps-script-deploy/Code.js` (cùng bytes) [AUDIT-DM §6] | Đọc lô đã soát/SELLING (C1e) → chứng từ bán đề xuất; map pháp nhân/ObjectID/kỳ/HĐ; giữ fingerprint; nối XML chính thức để không ghi nhận hai lần | Không nhầm với `CB_tmpEntry1/2`; không coi template có cảnh báo `EntryID/EntryDate/InvDate/InvSeri` (`:1336–1339`) là đã sẵn sàng production; không tính lại phí | [AUDIT-DM] |
| #13 Local Mask | Dịch vụ nội bộ | `privacy/core.py:46` rules, `:77` suggest, `:306` replace, `:315` verify, `:391/:400` vault AES-GCM; server có phiên/CSRF/revision [AUDIT-DM §7] | Lớp chính sách bảy nhóm **gồm số tiền** (detector nguồn tránh coi số tiền là tài khoản — `detectors.py:151/:165`), map token ↔ mã Junsky/bí danh, kiểm sau khôi phục, log, công tắc (N6) | Coi web API Mask là cổng headless mask→cloud→restore (chưa có); bật cloud | [AUDIT-DM] |
| #14 Trợ lý | Lõi → module | `app.py:30/66/504/616`, `store.py:51/119/156–166/170`, `reminders.py:58/82/193–211` [AUDIT-DM §8] | Transport Zalo thay `tg.py`; nhận và gắn trả lời ↔ câu hỏi/việc K5 (`task_id`, callback 1/2/3 ↔ phương án); dedup; nhắc hạn; escalation; giới hạn nội dung; audit; mock transport cho test (N7). Gửi tin thật là cổng riêng | Giữ `brain.py` gọi AI trực tiếp; coi Zalo đã có | [AUDIT-DM] |
| #1 Kiểm tra đề xuất Base | Trong nhà | Đã có schema YAML hồ sơ loại chi phí (`ho_so_loai/_schema.yaml`), validator `load_profiles`, router `route`, rule version = loại + phiên bản + hash [TAI-SU-DUNG-RQ-VA-NHAN-SU §1] | Crosswalk `loai` → nhóm G → DA/VH → cấu hình kế toán; RQ tham chiếu kết quả #1 bằng request ID + rule version; đọc chung qua `giao_tiep.v1_khoan_muc_phi` | Hỏi lại Anh #1 có schema chưa; coi `group/eligible` là nhóm G hay quyền duyệt; hai danh mục song song | [AUDIT-RQ] |
| #2 Request | Trong nhà | Đã có schema `requests`/`request_values` theo `groupVersionId`, API v1 đọc/nháp/tệp (`capNhatSau`, phân trang, `Idempotency-Key`), webhook HMAC [TAI-SU-DUNG-RQ-VA-NHAN-SU §2] | Adapter canonical RQ DEMO theo contract ngay; production qua `giao_tiep.v1_ghi_rq`/hàng đợi; cursor + dedup + đọc lại chi tiết | Hỏi lại Anh #2 có API chưa; nối nguồn thật khi chưa cấp kết nối; coi `approved` là duyệt bút toán | [AUDIT-RQ] |
| #12 OCR | Dịch vụ nội bộ | OCR khi không có bản mềm | HTTP cục bộ | Dùng mặc định | [TL31] |
| #4 Frappe HR | Ngoài | Bảng lương/tạm ứng khi xuất được | K1 | Chấm công/tính lương | [TL31/40] |

## 5. `giao_tiep` v1 tối thiểu [DỰ THẢO theo TL40 §5]

| Thành phần | Dùng cho | Gói |
|---|---|---|
| `su_kien_cho` (unique nguon, loai, khoa, hash) | Mọi app trong nhà | N4 |
| `v1_ghi_ket_qua_review(jsonb) → uuid` · `v1_nghiem_thu_da_kiem` | #5 pha 2 — payload theo §3, không đổi nghĩa trường | C3a |
| `v1_ghi_rq(jsonb) → uuid` | #8 nâng cấp, #2 | C2a |
| `v1_hop_dong`, `v1_lich_thu`, `v1_cong_no_mo`, `v1_khoan_muc_phi`, `v1_du_an` | CRM phòng bán hàng, #1, #5 tra mã | C1a, C2b, C3a |

## 6. Mẫu test cho mọi bridge
1. Idempotency: cùng đầu vào hai lần → số bản ghi không đổi; vân tay đích dựng lại từ nguồn khớp **mọi cột đã ánh xạ** (cơ chế A5).
2. Thay thế cùng khóa: phiên bản mới/`supersedes`, không ghi đè, liên kết cũ giữ.
3. Provenance: hash file hoặc ID kết quả nguồn + ba mốc thời gian.
4. Phiên bản contract: payload/schema khác phiên bản đã khóa → từ chối có mã, không đoán.
5. Hai trạng thái: trạng thái nguồn không làm dòng thành "đã duyệt" kế toán.
6. Quyền: role app không SELECT bảng thật; RLS; không đọc `bao_mat`.
7. Lỗi không lộ dữ liệu (mẫu A4); báo cáo chỉ số đếm.
8. Ranh giới âm: M5 không giá trị; M8 không bút toán; M7 không tính lương; M4 không khớp BOQ, không `de_nghi − anh_huong`.
Fixture DEMO, actor `MO_PHONG_`; test cần PostgreSQL skip có lý do, Codex chạy PG thật.

## 7. Chưa kiểm chứng (từ audit; không hỏi lại Anh thiết kế đã có)
Phiên bản đang deploy của #9/#10/#11; quyền kết nối thật (Sheets, Base token); lịch tự động; export thực chạy và đúng số; đồng bộ hai lần không trùng trên nguồn thật; nguồn đổi schema; hết phiên/token; phân quyền và hiệu năng [AUDIT-DM §9.5]. Tích hợp #5 với PostgreSQL và nghiệm thu end-to-end M4 chưa có bằng chứng [AUDIT-RV §7].

## 8. Ranh giới
Không xây lại HR/tính lương, review BOQ, tải hóa đơn, tính phí nước thải, sổ cái/BCTC/tờ khai; không sửa source/dữ liệu app nguồn trong nhiệm vụ kế toán; không mở bảng thật cho app nào; cloud AI tắt; không Junsky mức 2/nhập/duyệt thật, không `CFO_NTD`. Tài liệu không tuyên bố tích hợp nào đã chạy ngoài các dòng [SRC] có code trong repo.
