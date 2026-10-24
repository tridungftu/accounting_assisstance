# BÁO CÁO M4-02B — Chứng từ L3 · FIX02A (UI, ý định đang chờ, gửi lại) · CODE_ONLY · NOT_RUN_CODE_ONLY

Trạng thái: **CODE_ONLY — NOT_RUN_CODE_ONLY**. Lượt này chỉ sửa mã và viết regression. Không chạy Node, test, SQL, launcher, GUI hay provider.
Căn cứ: `docs/GIAO-SUA-M4-02B-02A-UI-VA-RETRY.md` (U-A..U-D) và lệnh giao của Root cho phần UNKNOWN còn lại R5/R6. Gói này không phải L3 hay M4 đầy đủ.

## Không kế thừa kết quả trước

- Các kết quả trước (FIX01: 28/28 kiểm thuần, 7/7 native, U1–U7 async; các probe trên baseline) chỉ đúng với **mã baseline**. Mã sau lượt
  này **chưa được chạy**, nên các kết quả đó không áp dụng cho nó. Lượt này không ghi bất kỳ ca nào là đạt.
- Theo Root: private2 trên baseline vẫn FAIL2, còn private5/official-old-async chỉ đạt trên baseline. Lượt này không đọc probe/golden private
  và không khẳng định đã sửa được các ca đó. Việc xác nhận thuộc về Root, sau terminal.

## Phạm vi file (đúng 3 file có sẵn, không tạo file mới)

| File | Thay đổi |
|---|---|
| `src/kho_tri_thuc/m4/giao_dien/chung_tu.js` | Sửa R5/R6 (xem dưới). Đọc lại và giữ nguyên U-A, U-B (token), U-C (treo theo phạm vi), U-D. |
| `tests/m4_02b_async.cjs` | Giữ nguyên toàn bộ U1–U7, không nới hay xóa assertion nào. Thêm U8–U11. |
| `docs/BAO-CAO-M4-02B.md` | Báo cáo này (thay stub IN_PROGRESS). |

Không sửa app.js, shell m4.js, adapter, vendor, review_goc, HTTP, service, SQL/migration, `m4/sql_review.py`, CRM, master, quyền, source37.

## Kiểm lại U-A..U-D (mã đã có trước lượt này)

- **U-A**: `moSau` kiểm fence gốc `f` trước GET làm mới, truyền `f` vào `napDs`, rồi kiểm lại `f` sau await trước khi `moRun(run_id, fc)`.
  `moRun` và `napDs` nhận fence gốc `ngoai` và kiểm trước request cũng như sau mỗi await. Khớp handoff. Lượt này không đổi logic.
- **U-B**: `dangGui` dùng Map giữa đích có phạm vi và token riêng của từng lần gửi; chỉ chủ token mới nhả. `lenh` tự chặn trùng, không dựa vào
  `button.disabled`. Khớp handoff. Lượt này mở rộng thêm (xem R6).
- **U-C**: `treo` giữ route/body/khóa/đích/phạm vi/hoàn tất gốc. Dòng Gửi lại chỉ hiện đúng phạm vi. Còn hai lỗ R5/R6 → đã sửa ở dưới.
- **U-D**: `tol = max(1e-3, |x|·1e-6)` khớp nguồn `review_goc/may_chu/chung_tu.py` dòng 460 (C01: `kn − nt > max(1e-3, |nt|·1e-6)`) và dòng
  479 (C03: `kl_lk − gn > max(1e-3, |gn|·1e-6)`). Toán hạng lấy từ so sánh typed (`chung_tu_adapter._ss` phát `kl_kn/nt`, `kl_lk/gn` khi
  SO_DUOC). Chỉ hiện dấu khi trạng thái là SO_DUOC. Lượt này không đổi logic, chỉ thêm test biên U11.

## Sửa R5/R6 trong `chung_tu.js`

Nguyên nhân gốc:
1. R5: Gửi lại xóa ý định khỏi `treo` ngay lúc bắt đầu gửi. Đổi đợt/vai lại `dangGui.clear()`. Quay về A trong lúc Gửi lại đang bay thì không còn gì
   chặn, nên bodyY phát được khóa mới.
2. R6: `xoa()` gọi `khoaMap.clear()` + `dangGui.clear()`, đổi đợt và `huy()` cũng `dangGui.clear()`. Đi A→B→A với cùng đích/body khi POST1
   còn bay thì sinh khóa2. Ngoài ra `treo` được khóa theo đích + route + body (không theo khóa), nên hai UNKNOWN ghi đè nhau và chỉ khóa về sau
   còn đường đối soát.

Thay đổi:
- **Không xóa `dangGui` khi đổi đợt (`onchange` chọn đợt), khi đổi vai/ngữ cảnh (`xoa`) hay khi rời tab (`huy`).** Khóa đích đã chứa đủ
  vai|PN|dự án|HĐ|đợt|run, nên B không bị chặn. Quay lại đúng A (ABA đầy đủ ngữ cảnh) thì A vẫn bị khóa an toàn: không phát POST2/khóa2 cho
  cùng đích, kể cả cùng body hay body R2. Các fence `ep/genForm/...` vẫn tăng như cũ, nên continuation cũ không vẽ/toast/dọn nháp.
- **`khoaMap` khóa theo `đích có phạm vi + route + body`** và không còn bị xóa trong `xoa()`. Hai vai gửi cùng body nhận hai khóa khác nhau,
  không tái dùng khóa giữa các vai.
- **`treo` khóa theo `đích + route + body + khóa`.** Mỗi khóa đã phát có bản ghi riêng; không ghi đè và không gộp ý định khác khóa chỉ vì
  cùng body.
- **Gửi lại không còn gỡ ý định khỏi `treo` lúc bắt đầu.** Thay vào đó đặt `t.bay = token` của lần gửi lại.
  - Kết quả RÕ (ACK hoặc lỗi 4xx rõ): chỉ khi `t.bay === token` và `treo.get(t.kt) === t` thì mới gỡ đúng ý định đó. Completion cũ không gỡ
    ý định mới hơn.
  - Lại CHƯA RÕ: giữ nguyên bản ghi gốc (route/body/khóa/đích/`xong`), chỉ trả `bay = null`.
  - `guiLaiTreo` và `lenh` chặn Gửi lại lặp khi `t.bay` còn. Dòng ý định đang Gửi lại hiện ghi chú "Đang gửi lại y nguyên … — lệnh mới bị
    chặn" và không có nút.
- **Kết quả về khi fence gốc đã đổi**: không toast, không chạy `xong`. Nếu đang mở đúng vai/PN/dự án/HĐ/đợt của ý định thì vẽ lại để
  hiện/gỡ dòng Gửi lại (nháp hiện tại lấy từ `ui`, nên giữ được). Khác phạm vi thì chỉ `capNhatNut()`, không hiện gì của A trong B.
- `luuSua` báo "đang gửi — chờ kết quả" khi đích đang bay, và "bấm Gửi lại y nguyên" khi còn ý định chưa rõ.

Bất biến giữ nguyên: không tự tạo khóa mới khi chưa rõ; 0/5xx/200 + JSON đứt là CHƯA RÕ; 403/404 là thu hồi có chủ ý; `xong` chỉ dọn đúng giá trị
đã gửi; không đổi body/receipt/key gửi server; không thêm generic queue hay framework.

## Regression viết thêm (NOT_RUN_CODE_ONLY — chưa chạy)

`tests/m4_02b_async.cjs` (Root chạy: `node tests/m4_02b_async.cjs`, Node ≥ 18). Dùng mã thật app.js + chung_tu.js, DOM giả có kết nối, fetch là
Promise do test điều khiển. Assert trên route/body/khóa/số POST/GET thật và DOM, không regex mã nguồn.

- **U8 (U-A)**: ACK chạy → giữ GET làm mới → (a) đổi đợt, (b) cùng vai đổi pháp nhân qua `ve` của shell, (c) tab away/back qua `huy` + `ve`
  → nhả GET cũ. Kiểm: 0 GET chi tiết run r3/r4/r5, không có "Đang xem"/"Đang tải kết quả" dưới ngữ cảnh mới, đúng 3 POST chạy.
- **U9 (R5)**: sửa bodyX UNKNOWN (khóa1) → Gửi lại 1 đang bay → đợt B. Kiểm B không thấy dòng nào của A; B chạy được (POST dot-2, lỗi rõ).
  Về A: không có nút Gửi lại thứ hai, có ghi chú; bodyY bị chặn (0 POST). Gửi lại 1 về 503 muộn → bản ghi gốc còn, nháp Y giữ, Lưu Y vẫn bị
  chặn, Gửi lại 2 = body/khóa1, bấm lặp khi đang bay = 0 POST. ACK (lap_lai) → dòng chưa rõ biến mất, nháp/lý do Y giữ; sau đó bodyY gửi với
  revision/basis mới và khóa ≠ khóa1. Tổng số POST đúng.
- **U10 (R6)**: POST1 (khóa1) đang bay → vai B cùng HĐ/đợt/run. Kiểm B không thấy gì; B gửi cùng body → được gửi với khóa ≠ khóa1. Về A (ABA):
  cùng body và body R2 đều 0 POST, có báo; ghép dòng (đích khác) gửi được. POST1 UNKNOWN muộn → Gửi lại hiện ở A, nháp R2 giữ. Ghép UNKNOWN →
  hai dòng riêng. Gửi lại ghép/sửa đúng body/khóa từng ý định; ACK ghép không gỡ ý định sửa đang Gửi lại. 200 + JSON đứt → giữ, Gửi lại 2 →
  ACK. Mọi POST đích sửa của A = [b1, b1, b1] (một khóa). R2 sau khi rõ → khóa mới. Thứ tự ngược: UNKNOWN về khi đang ở đợt B → B không thấy;
  về A còn Gửi lại; cùng body bị chặn; Gửi lại đúng b5.
- **U11 (U-D)**: hai phía ngưỡng tuyệt đối (10 ± 0,0005 / 0,002) và tương đối (10⁶ ± 0,5 / 1,5) cho NT/KL kỳ này và GN/KL lũy kế. Toán
  hạng typed thắng trường dòng. NULL / khác ĐVT / KHONG_AP_DUNG không có dấu; 0 tường minh hiện "0" và ✓; KL > 0 mà nt NULL → ✗.
- U1–U7 giữ nguyên văn. Mã mới không xóa `dangGui/khoaMap` khi đổi vai, nên đường U4 (ACK muộn sau đổi vai) vẫn nhả đúng chủ token. Đây
  mới là dò tay, chưa chạy.

## Gate còn mở (không đóng trong gói này)

- Chạy `tests/m4_02b_async.cjs` (U1–U11) và mọi suite M4/L3 liên quan: **OPEN — NOT_RUN**.
- Probe/golden private của Root (gồm private2 FAIL2 trên baseline): **OPEN**, chưa xác minh trên mã mới.
- Backend/service, adapter, HTTP thật, PostgreSQL thật, quyền hiện hành, provenance, idempotency phía máy chủ theo khóa/vai, gate #6: **OPEN**.
- GUI thật trên trình duyệt / shell M4 thật, Word/Office: **OPEN**.
- Toàn M4 (duyệt reviewer + PDF 02C, kế toán/công nợ, Request, OCR/Local AI): **OPEN**, ngoài gói.

## Điểm worker khác / Root cần biết (API/DTO)

- Không đổi API/DTO và không đổi payload POST (`{...body, khoa}`). Khóa vẫn sinh ở client (`m4ct-<uuid>`). Server phải idempotent theo khóa
  (và vai). Hai vai gửi cùng body sẽ có hai khóa khác nhau.
- Ma trận dùng các khóa SO_DUOC của `so_sanh.C01 {kl_kn, nt}` và `so_sanh.C03 {kl_lk, gn}` từ `chung_tu_adapter._ss`. Thiếu khóa thì lấy
  trường dòng. Nếu adapter đổi tên khóa, phần trình bày sẽ lệch.
- Cầu nối shell giữ nguyên: `window.kttM4ChungTu.ve(vùng, {hdId, dots, dotId, nguoi, duAnId, phapNhan})`, `huy`/`tat`.
  `huy` không còn xóa khóa đích đang bay.

## Rủi ro còn lại / chưa xong

- Khóa đích đang bay giữ tới khi fetch kết thúc; client không có timeout. Nếu request treo vô hạn, đích đó (chỉ trong đúng phạm vi) bị chặn tới
  khi tải lại trang. Đây là chủ ý chọn chặn an toàn thay vì phát khóa thứ hai.
- ACK về sau khi đã đổi ngữ cảnh không làm mới danh sách (fence cũ). Lần Lưu kế tiếp có thể nhận 409 REVISION_CU, mà nhánh đó đã có làm mới.
- Khi UNKNOWN về muộn mà đang ở đúng phạm vi, màn được vẽ lại để hiện Gửi lại. Nháp giữ nhưng có thể mất focus ô đang gõ.
- `treo`/`khoaMap` của ý định chưa rõ sống trong phiên trang, không lưu bền. Tải lại trang thì mất đường Gửi lại phía client; đối soát khi đó
  dựa vào biên nhận phía máy chủ.
- U8–U11 khớp hành vi mã chỉ qua dò tay, **chưa chạy**. Có thể còn sai ở harness (thứ tự call/nhãn DOM) và cần Root chạy để xác nhận.

---

## Mốc 2026-10-22 — L3 BACKEND6 (S1 + A1/A2), vòng song song CODE_ONLY trên baseline 2a4b1bf55d3f

**Trạng thái: NOT_RUN_CODE_ONLY.**
- Lead đã join đủ 3 worker (crm-data, m4-ui, crm-ui); cả 3 đều trả kết quả, không ai lỗi hay dừng dở.
- Handoff: `docs/GIAO-SUA-M4-L3-BACKEND6.md`.
- Không ai chạy test, runtime, SQL, #6, Node, Office hay GUI. Không file mới, không xóa.
- Nội dung bên dưới là phần worker tự khai; lead chưa đọc lại mã.
- Phần FIX02A UI phía trên (U-A..U-D, R5/R6, U1–U11, ý định UNKNOWN/Gửi lại) giữ nguyên làm lịch sử, mốc này không sửa.
- PASS của baseline hay mốc trước **không** chuyển thành PASS cho mốc này.

### S1 — fallback công bố phải ra UNKNOWN (worker crm-data)

**`src/kho_tri_thuc/k2/xay_dung.py`, hàm `XayDungK2._chung_tu_cong_bo`, nhánh fallback (khoảng dòng 1408–1425).** Trước đây nhánh này nuốt mọi lỗi của fallback rồi raise lại lỗi đầu, nên che mất `M4_KET_QUA_CHUA_RO`. Nay xử lý theo từng loại lỗi:

| Lỗi trong fallback | Kết quả |
|---|---|
| `M4_KET_QUA_CHUA_RO` | Raise lại nguyên vẹn; không có khóa, run, compute hay retry mới. |
| Lỗi quyền/phạm vi (đã `chung_tu_huy`, run CANCELLED) | Raise lỗi quyền rõ. |
| Lỗi kết nối thoát ra (ví dụ mất ACK commit của hủy) | `M4_KET_QUA_CHUA_RO`. |
| Lỗi khác | Raise lại lỗi đầu như cũ (đã rollback rõ). |

- Helper mới: `_MA_QUYEN_PHAM_VI` và `_ma_loi_pg`.
- Không đổi SQL, migration, các luồng khác hay guard `trich6 is None`.

**`tests/test_m4_02b_k2.py`**

- **Gate #6 dùng chung (`_gate_trich6`, trong `setUpClass`):**
  - Một `Trich6Host` và một client cho cả class.
  - Kiểm `suc_khoe`, `nang_luc("XD")` (RULE_ONLY và catalog XD đã ghim), và một DOCX DEMO qua endpoint thật với seal khớp bytes.
  - Lỗi thì `SkipTest` NOT_READY/NOT_VERIFIED. Không có host giả.
- **`_svc_moi`:** truyền `trich6` dùng chung cho mọi service.
- **K01, K10:** thêm assert về client dùng chung, host lượt +1 và intent +1.
- **K08c / K08d (PG thật, tiêm lỗi biên commit):**
  - K08c: mất kết nối trước commit thì ra UNKNOWN và RUNNING; gửi lại cùng khóa đối soát về đúng run, không compute lại.
  - K08d: mất ACK sau commit thì ra UNKNOWN, nhưng CSDL đã FAILED; retry cùng khóa trả FAILED, không ghi mới.
- **Class `M4CongBoS1Bien`:** ca b1–b8, nhãn MOCK_BOUNDARY, không phải bằng chứng PG.
- K08b giữ nguyên.

### A1/A2 — alias, provenance trước/sau alias, locator (worker m4-ui)

**`src/kho_tri_thuc/m4/chung_tu_adapter.py`**

- **A1 — alias:** `RE_TEN_HANG` giờ khớp toàn tiêu đề (fullmatch). Tiêu đề ghép như "Tên hàng / Nhà sản xuất" hay "Tên hàng (Hãng…)" không còn được alias.
- **Ghi vết alias:** `thich_nghi_cot` có một bản ghi cho mỗi vị trí tiêu đề (bảng/sheet riêng), kèm ô vật lý.
- **A2 — tầng trước alias:** `nguon_truoc_alias` / `provenance.truoc_alias` chạy đúng mã nguồn `dong_hang` và `_cot` gốc trên bản sao bảng đã chụp.
- **Locator:**
  - `vi_tri_o` cho XLSX trả sheet/ô/vùng gộp; cho DOCX trả `w:tr`/`w:tc`/gridSpan/vMerge.
  - Khi chưa xác định được thì trả NOT_AVAILABLE hoặc LIMITED kèm lý do, không bao giờ trả CHECKED.
  - `gan_vi_tri` thêm `dong_tieu_de`.
- **Giữ nguyên:** `row_id`, rule, ngưỡng, coverage và report XLSX.

**`src/kho_tri_thuc/m4/nguon_review.py`**
- `l3_vi_tri_xlsx`: thêm `o_gop`. Phải mở file thêm một lần ở chế độ không read-only; nếu lỗi thì `o_gop` là None kèm lý do.
- `l3_vi_tri_docx`: thêm map `o` theo quy tắc gridSpan/vMerge của `ocr_abbyy._bang`.

**`tests/test_m4_02b_pure.py`**
- `AdapterThat` có 4 ca l3a: alias, 2 sheet có offset và ô gộp, tiêu đề gộp/không dấu, DOCX gridSpan/vMerge. Các ca này cần vendor; thiếu thì skip và ghi NOT_RUN.
- Class mới `L3ViTriThuan` (pure).
- Expected viết tay từ ô đầu vào và quy tắc nguồn, không lấy từ output sản phẩm.

### Worker crm-ui (tham chiếu)
Lượt này worker crm-ui chỉ sửa phía CRM G4. Chi tiết nằm ở `docs/BAO-CAO-CRM-41-04A.md` mục "Mốc 3":
- microfix hiển thị khi đổi File;
- K12;
- sửa capture digest ở native33;
- chẩn đoán K10/K11 vẫn OPEN.

Không file M4 nào bị đụng.

### Điều kiện tiên quyết / gate còn OPEN (việc của Root)

- **#6 thật cho toàn bộ K2.** Cần có:
  - nguồn `H.NGUON_MAC_DINH` ngoài repo, chỉ đọc;
  - bằng chứng file-guard cho `Trich6Host.start`;
  - Windows Job.

  Thiếu thì cả class PG skip với nhãn NOT_READY, không phải PASS. Gate để lại một intent và một host run dưới DataRoot DEMO.
- **Giả định của K08c/K08d cần xác minh khi chạy:**
  - biên nhận L3 nằm ở `m4.bien_nhan` theo `khoa`;
  - worker trên dot2 thoát 0 (SUCCEEDED/PARTIAL);
  - `_chung_tu_gom` không ghi đè file đã có.
- **Giả định của A1/A2:**
  - openpyxl read-only `iter_rows` bắt đầu từ A1;
  - `merge()` của python-docx tạo gridSpan/vMerge;
  - mở XLSX thêm một lần không read-only tốn bộ nhớ với workbook lớn.
- **Tác dụng phụ:** cột report hiện có có thể lặp tên tiêu đề do `thich_nghi_cot` giờ có một bản ghi cho mỗi vị trí. Report nằm ngoài phạm vi nên chưa sửa.
- **Chưa chạy gì:** `test_m4_02b_k2.py`, `test_m4_02b_pure.py`, U1–U11 và các suite M4/L3 liên quan; probe private; HTTP/PG thật với quyền hiện hành; provenance; GUI/Word.
- **Chưa nghiệm thu toàn bộ M4:** 02C, kế toán/công nợ, Request, OCR.
