# BÁO CÁO M4-02A — Review L1/L2 (first slice) · NOT_RUN_CODE_ONLY

**21/10/2026 · Trạng thái: NOT_RUN_CODE_ONLY.** Coder chỉ viết source/test/report bằng Read/Glob/Grep/Edit/Write. **Không** chạy lệnh, import, AST,
Python/Node, tests, SQL, migrate, server, browser, Office, AI/OCR, cloud hay subprocess. Không có self-test, GUI hay Root acceptance nào được thực hiện
hoặc được suy ra. Không có mục nào trong báo cáo này là PASS.

Căn cứ:
- Handoff gốc `docs/GIAO-VIEC-M4-02A-REVIEW-L1-L2.md` (SHA256 `19b208e5…572c`).
- Ưu tiên `docs/M4-UU-TIEN-DUNG-LAI-BAN-GOC-20261021.md`.
- Bản sửa `docs/GIAO-VIEC-M4-02A-TIEP-TUC-DUNG-LAI-REVIEW.md` (SHA256 `99914a11…affdac`).

## 0. Lần trước và lần này

| Lần | Kết quả |
|---|---|
| Lần trước (53961/fabfff) | Hết timeout 900 s, exit 1, result null, không có report. Root đã dừng phiên, kiểm phạm vi và posthash (true). Còn dở: 362 source, 430 runtime; chưa hoàn tất, chưa nghiệm thu. |
| Lần này | Kế thừa các tệp dở: compute, SQL, `nguon_review`, PG. Chỉ sửa lỗi nguồn hữu hạn và hoàn thiện service/route/UI. Không viết lại phần đã có, không dựng bộ tính mới. |

## 1. Đúng 13 đích ghi

| # | Đích | Loại | Nội dung |
|---|---|---|---|
| 1 | `src/kho_tri_thuc/ha_tang/pg_migrations.py` | existing | Giữ nguyên **toàn bộ 868.867 byte** (H `d95a14dd…0244`), chỉ thêm M19 sau EOF (xem dưới bảng) |
| 2 | `src/kho_tri_thuc/m4/nguon_review.py` | existing | Đường nối pin/projection: `REVIEW_PIN`, `ENGINE_REVIEW(_SHA)`, `kiem_o_dich`, `ma_hd_projection`, `projection_l2` |
| 3 | `src/kho_tri_thuc/k2/xay_dung.py` | existing | Điều phối `review_chay / review_chay_lai / review_ghep / review_ds / review_chi_tiet / review_tai` |
| 4 | `src/kho_tri_thuc/giao_dien/m4.py` | existing | Route mỏng + đúng một tài sản `/m4/review.js` |
| 5 | `src/kho_tri_thuc/m4/giao_dien/m4.js` | existing | Tab "Review L1/L2" mount `review.js`; cập nhật LO_TRINH |
| 6 | `src/kho_tri_thuc/m4/giao_dien/m4.css` | existing | Style `.m4 .m4-rv*` (scoped) |
| 7 | `src/kho_tri_thuc/m4/review_compute.py` | existing (dở) | Worker tiến trình con + coverage companion + báo cáo |
| 8 | `src/kho_tri_thuc/m4/sql_review.py` | existing (dở) | `M0019_M4_REVIEW` (chỉ hằng SQL) |
| 9 | `src/kho_tri_thuc/m4/giao_dien/review.js` | NEW | Port DOM của bố cục/render/helper `checks.js` nguồn |
| 10 | `tests/test_m4_review_compute.py` | NEW | Tĩnh + thuần |
| 11 | `tests/test_m4_review_k2.py` | NEW | PG thật (skip = NOT_RUN) |
| 12 | `tests/test_m4_review_http.py` | NEW | HTTP thật (skip = NOT_RUN) |
| 13 | `docs/BAO-CAO-M4-02A.md` | NEW | Báo cáo này |

Ba dòng được thêm vào `pg_migrations.py` (#1):

```python
from ..m4.sql_review import M0019_M4_REVIEW
PG_MIGRATIONS = (*PG_MIGRATIONS, M0019_M4_REVIEW)
PG_SCHEMA_VERSION = len(PG_MIGRATIONS)
```

**Không sửa:**
- `pyproject`, master/quyen/seed, CRM, `server.py`, `index.html`, `app.js`, M9, guard, runtime Root.
- `sql_m17.py`, M1–18.
- `tests/m4_01c_async.cjs` (f77…).
- Vendor `review_goc` và reference 65 (giữ nguyên byte).

`pyproject` không đổi vì `review.js` đã nằm trong glob package-data có sẵn `"kho_tri_thuc.m4" = ["giao_dien/*.js", …]`.

## 2. Tái dùng nguyên (gọi vendor qua bộ nạp ghim `NR._m`)

**L1:**
- `toan_ven.KiemTra(path, o_dich).chay()` chạy K1–K8 với ngưỡng nguồn.
- `may_chu.nghiep_vu._lop1` tạo findings, `bang_k` và cây.
- `toan_ven.ghi` ghi báo cáo nguồn.

**L2:**
- `csdl_hop_dong.tinh_doi_chieu_dot` chạy trên projection `:memory:` theo đúng `cs.SCHEMA`.
- Sau đó lần lượt: `nghiep_vu._lop2` → `bang_kiem_lop2` → `_lop2b(bang=…)`.
- Thứ tự giống `kiem_tra_dot` nguồn, nhưng **không** gọi `cs.kiem_dot` (hàm này ghi nhật ký + commit).
- Ghép hạng mục dùng `master_hd.khoa` / `khop_hang_muc` gốc. Ghép tay chỉ nạp vào bảng `khop_hang_muc` của projection, không đổi thuật toán.

**Báo cáo L2:** `bao_cao_lop2` là builder workbook của `kiem_dot`, chép thành hàm thuần đọc kết quả đã tính. Không journal, không commit, không đọc lại PG.

**UI:** `review.js` chuyển bố cục/render/helper của `checks.js` nguồn sang DOM: stat-strip, chọn chế độ, phạm vi, coverage, bảng phát hiện, lưới K/B, đối chiếu hạng mục, cây truy vết, bằng chứng, xuất, lịch sử.
- Nguồn dùng chuỗi HTML; bản port dựng DOM qua `textContent`, không có `innerHTML`.
- Không chép nút **"Nạp đợt đã duyệt"**.
- Bản `checks.js` gốc giữ nguyên byte để so độ trung thành.

**Receipt:** dùng lại `m4.bien_nhan` / `_bn_tra` / `_bn_ghi`. Review có hàm tra riêng `m4.review_tra`, kiểm quyền và phạm vi hiện hành **trước** `_bn_tra`.

## 3. Đường nối đã viết (seams)

### Luồng dịch vụ (`_review_khoi`)
1. Khóa tư vấn mức phiên theo đúng khóa biên nhận (actor + khóa).
2. `m4.review_tra`: kiểm quyền/phạm vi hiện hành → tra biên nhận. Replay đúng body trả FINAL **trước** mọi tính toán; body khác → 409 `M4_IDEMPOTENCY_KHAC`.
3. **Một** giao dịch REPEATABLE READ: `review_kiem` → `_co_so` (basis đầy đủ) → so `expected_basis` (khác → 409 `M4_REVIEW_CO_SO_DOI`) → `review_tao_run` (RUNNING). Đóng giao dịch trước khi tính.
4. Worker tiến trình con: `python -m kho_tri_thuc.m4.review_compute <thư mục chạy>`.
   - Môi trường tối thiểu, **không** DSN/PG/credential.
   - Timeout 900 s; `subprocess.run` kill rồi chờ tiến trình con dừng hẳn.
   - Lỗi hoặc timeout → FAILED, không bao giờ PASS.
5. Công bố trong giao dịch READ COMMITTED:
   - Khóa `ho_so_hop_dong` FOR SHARE.
   - Chạy lại `review_kiem` theo quyền hiện hành.
   - Chụp lại basis và so **toàn token**: khác → STALE (giữ bằng chứng, không công bố, không gắn hiện hành).
   - Ghi FINAL và biên nhận.
   - Nếu mất quyền: `review_huy` → CANCELLED (giữ kết quả không công bố + artifact), rồi raise lỗi quyền.

### Quyền
- `review_quyen`:
  - SOAN đúng dự án.
  - **hoặc** REVIEW + đợt `DA_NOP` + tệp gắn đúng đợt (`dot_tep`).
  - Tệp phải là HO_SO_DOT `.xlsx`.
  - Reviewer không cần và **không được cấp** SOAN.
- `review_doc_duoc`: XEM dự án, hoặc REVIEW trên đợt đã nộp + đúng tệp. RLS SELECT của 4 bảng Review dùng hàm này.

### Lưu trữ
- Kết quả, artifact và map chỉ ghi thêm (trigger `m4.chi_ghi_them` của M17).
- Lần chạy chỉ ghi được qua hàm trên kết nối chủ bảng, không xóa.
- Artifact content-addressed `m4-review/<sha>` (`write_immutable`, không ghi đè). Mỗi lần chạy có thư mục riêng, tạo mới với `exist_ok=False`.

### Ghép tay
- Giữ `khoa_hstt` gốc.
- Đích là đúng **một** dòng BOQ typed của bản BOQ hiện hành cùng HĐ.
- Mỗi lần ghép là một revision theo (HĐ, khóa).
- Kết quả trả phạm vi ảnh hưởng: "các lần chạy sau, cùng HĐ, dòng cùng khóa; không áp HĐ khác".
- Không sửa kết quả lần chạy cũ. Chạy lại dùng **cùng tệp gốc**, sinh run con (`parent_run_id`).

### HTTP
- GET `/api/m4/review` (danh sách + basis), `/api/m4/review/{run}` (chi tiết), `/api/m4/review/{run}/tep/{artifact}` (tải; quyền hiện hành kiểm trước khi tra registry/kho).
- POST `review/chay`, `review/chay-lai`, `review/ghep`.
- Tài sản đúng một route `/m4/review.js`.
- Dùng lại token/cookie/lỗi/`mutation_lock` hiện hành. Thêm `M4_REVIEW_PHAM_VI` → 403, `M4_REVIEW_KHONG_THAY` → 404, các mã xung đột Review → 409.

### UI
- `review.js` tham gia cổng đổi vai chung với tên `m4_review` (`K.dangKyVai`, `vaiDangChan`).
- Có rào thế hệ (`ep/genDs/genCt/genForm`) trước mọi await/DOM.
- `khoaMap` giữ khóa khi kết quả chưa rõ, kèm nút "Gửi lại y nguyên (cùng khóa)".
- `m4.js` truyền ngữ cảnh do máy chủ trả (HĐ, các đợt, vai). Không nhập UUID tay, không chọn đường dẫn tệp.

## 4. Các sửa theo bản correction

**RC01 — raw NULL khác explicit 0.**
- `trang_thai_tho` quan sát trong đúng phạm vi `tim_so_tong_hop` (80 × 12, ≤ 6 ô bên phải nhãn) và không đổi ngưỡng. Năm trạng thái: RECOGNIZED / OBSERVED_ZERO / NOT_RECOGNIZED / RAW_NULL / MISSING.
- RAW_NULL hoặc MISSING → INCOMPLETE. 0 vật lý hoặc |v| ≤ 1 → LIMITED. Thiếu dữ liệu không bao giờ được coverage tốt hơn 0 quan sát được.
- Vắng mà HĐ khai **tường minh** KHONG_AP_DUNG (TT-21, TT-10; bộ tham số đã xác nhận còn hiệu lực) → KHONG_AP_DUNG có căn cứ. *(FIX01 R1: bản trước gộp cả KHONG_QUY_DINH — đã sửa, xem §8.)*
- Lỗi provider tham số (`_lop2b` nuốt thành None) được quan sát lại bằng chính `cs.tham_so_hieu_luc` trên projection chỉ-đọc → phụ thuộc ghi "provider ERROR".

**RC02 — K2 theo số đếm.** Dùng `n ≥ 10` và `n / len ≥ 0.7` từ cột số đếm, không dùng cột tỷ lệ đã `round(…, 3)`. Ví dụ: 6999/10000 là NOT_ELIGIBLE.

**Đợt đầu / đợt trước đã duyệt luôn INCOMPLETE.**
- Phụ thuộc `TRUOC` luôn `ok = False`. Số thứ tự đợt (vd 1) không chứng minh "không có đợt trước", và DA_NOP không phải "đã duyệt".
- `dot_thanh_toan` / `kl_thanh_toan` của projection để trống.
- Hệ quả: lần chạy L1+L2 ở gói này **luôn PARTIAL** (B5 INCOMPLETE).

**Map theo quyền đọc lần chạy gốc.**
- Policy `review_manual_map_web` dùng `USING (m4.review_doc_duoc(run_id))`.
- `_co_so` chỉ nạp map có `m4.review_doc_duoc(m.run_id)` (DISTINCT ON bản mới nhất).

**Đủ 8 yêu cầu §10:**
- K7 thiếu đích → INCOMPLETE và K6 LIMITED.
- K8 không có bảng → INCOMPLETE.
- K7 bị cắt độ sâu → LIMITED, và giữ B7 ở LIMITED.
- K7 rỗng → B7 INCOMPLETE.
- TT-10 CHUA_CO → B8 INCOMPLETE.
- Phân biệt CHECKED / NOT_ELIGIBLE / LIMITED / NOT_AVAILABLE / ERROR.
- Nguồn đích K7 tách "NGUOI_CHON" khỏi "TU_DONG".
- Kết quả nguồn giữ nguyên ở `ket_qua_nguon`; nhãn hiển thị lấy theo companion; báo cáo tải về có sheet "Pham vi kiem" cùng semantics.
- Ước tính tiền của nguồn được ghi rõ là ước tính.

**Lỗi nguồn hữu hạn sửa thêm lượt này:** `RE_O_DICH` trước đây nhận tên sheet chứa ký tự Excel cấm (`\ / ? * [ ] :`), nên `C:\x!A1` lọt qua. Nay các ký tự này bị chặn ngay ở cú pháp.

## 5. Chưa nối (giữ nghĩa vụ full M4, không gạch scope)

- **Kiểu dữ liệu PL:** GT/tham số/BO theo PL chưa có kiểu ở M17 → PL áp dụng làm `PL_GT`, `PL_THAM_SO`, `PL_BOQ` INCOMPLETE. Không parse lời mô tả.
- **Provider lịch sử đợt đã được reviewer duyệt:** chưa có → TRUOC / B5 INCOMPLETE.
- **Chưa làm:**
  - L3 C01–09 + đối chiếu tài liệu.
  - OCR/provider jobs.
  - Quyết định reviewer / số tiền chấp nhận / PDF ký duyệt.
  - AP + Request.
  - Catalogue export.
- **Định dạng tệp:** `.xls/.xlsm`/converter chưa hỗ trợ; chỉ nhận HO_SO_DOT `.xlsx`.
- First slice **không** phải full Review/L3/OCR/approvalPDF PASS. Nộp/DU_AN/reviewer giữ đúng kế hoạch.

## 6. Lưu ý đã biết (Root cần biết khi chạy)

1. ~~**Tính dưới `mutation_lock`.**~~ Đã sửa ở FIX01 R3 (§8): lệnh Review chạy ngoài lock toàn cục, trên cặp kết nối riêng.
2. **Test CRM-41-02 cũ lệch.** `tests/test_crm_41_02.py` khẳng định `len(PG_MIGRATIONS) == 18` và đuôi tệp kết thúc bằng dòng M18; sau khi thêm M19, hai khẳng định này sẽ lệch. Tệp này được bảo vệ, không thuộc 13 đích, nên không sửa. `test_m4_01b_tinh` dùng `>= 17` nên không ảnh hưởng.
3. **Môi trường worker:** bản trước làm rơi cờ khởi động giữ tệp và đường dẫn phụ thuộc; đã sửa ở FIX01 R2 (§8). Python dùng `sys.executable` của máy chủ. Chưa có bằng chứng chạy thật.
4. **Checksum M19** và binding nguồn cuối là RootTO_BIND. Coder không tự tính hash.
5. **Lỗi worker nhẹ:** `review_compute.main` có `except BaseException` ghi `ket_qua.json` FAILED kể cả khi bị ngắt. Khi timeout, kill có thể xảy ra trước khi ghi; máy chủ lúc đó tự ghi FAILED "không tạo ket_qua.json".

## 7. Tests đã viết (NOT_RUN — chưa chạy lần nào)

**`tests/test_m4_review_compute.py`**
- **Migration:**
  - Prefix 868.867 byte = `d95a14dd…`, M19 nối cuối, 1–18 giữ nguyên identity.
  - Không có DELETE FROM / DROP / TRUNCATE.
  - Không GRANT EXECUTE; chỉ `review_quyen` / `review_doc_duoc` là SECURITY DEFINER.
  - RLS bốn bảng (gồm policy map); `review_kiem` đứng trước `_bn_tra`.
- **Coverage L1:** K2 theo số đếm (6999/10000), K7/K6/K8, K1 cache, lỗi nguồn → ERROR, "Đạt" nguồn không thành nhãn Đạt.
- **Coverage L2:** RC01 bốn trạng thái, KHONG_AP_DUNG tường minh vs CHUA_CO, TT-10 → B8, TRUOC, B7 theo K7, "Không có số liệu", L2 lỗi → ERROR.
- **`trang_thai_tho`:** workbook openpyxl trong bộ nhớ + bảng nhãn giả; kiểm cả ngoài 80 dòng và sheet ẩn.
- **Khác:** `kiem_o_dich`, `ma_hd_projection`, NaN → null, worker luôn ghi `ket_qua.json` khi lỗi.
- **Cần lõi nguồn:** `phu_thuoc` typed, projection query_only, NULL ≠ 0.
- **`review.js` tĩnh:** không `innerHTML`; participant; không "Nạp đợt đã duyệt"; chỉ `/api/m4/*`; CSS scoped.

**`tests/test_m4_review_k2.py`** (R01–R08)
- Dựng hồ sơ thật đến Nộp.
- SOAN L1: replay trả FINAL khi worker và `_co_so` đều bị cấm; đổi body → 409; 0 delta.
- L1+L2 luôn PARTIAL.
- Reviewer chỉ có REVIEW: chạy thành công + replay. Ca âm (nháp / không đợt / tệp lẻ) → phạm vi, 0 delta.
- CO_SO_DOI / STALE.
- Ghép tay + đích mơ hồ + chạy lại: run cũ giữ nguyên hash. Ca này skip trung thực nếu nguồn không tạo dòng đối chiếu.
- Đồng thời hai kết nối.
- Thu hồi giữa lúc tính → CANCELLED, sau đó chặn replay/đọc/tải.

**`tests/test_m4_review_http.py`** (H01–H04)
- Tài sản đúng một route.
- Token/tham số/authority/o_dich.
- SOAN L1 qua HTTP: chạy, replay, 409, chi tiết, tải đúng hash, chạy lại.
- Ngoài phạm vi (B1 / reviewer) → 403/404, không lộ dữ liệu.
- Reviewer positive qua HTTP chưa viết; đã phủ ở tầng dịch vụ (R04).

## 8. FIX01 — khép runtime và vòng đời Review UI (NOT_RUN_CODE_ONLY)

Căn cứ: `docs/GIAO-SUA-M4-02A-01-KHEP-RUNTIME-VA-UI.md` (SHA256 `0e346cba…681ac`).

Phạm vi lượt này:
- Chỉ sửa trong 13 đích **đã có**; không thêm, xóa hay đổi tên tệp nào.
- Không sửa `m4.css` (không cần) và không đụng prefix 868.867 byte của `pg_migrations.py`; mọi thay đổi SQL nằm trong hằng `M0019_M4_REVIEW` ở `sql_review.py`, M19 vẫn **chưa áp** vào PG thật.
- Vendor/reference, M1–18, `pyproject`, CRM/server/index/app, guard, runtime Root không đổi.

Bối cảnh do Root cung cấp, không phải coder tự chạy:
- Native pure 30 PASS / 0 skip.
- Một ca độc lập FAIL: KHONG_QUY_DINH + rawNULL ra KHONG_AP_DUNG thay vì INCOMPLETE.
- PG/HTTP/worker chưa chạy.

| Mục | Vấn đề | Sửa | Tệp |
|---|---|---|---|
| R1 | `phu_thuoc` gộp KHONG_QUY_DINH vào cờ "tường minh không áp dụng", nên số vắng/NULL thành KHONG_AP_DUNG | Cờ chỉ bật khi tham số là **KHONG_AP_DUNG** và bộ tham số đã xác nhận còn hiệu lực. KHONG_QUY_DINH ghi rõ "không phải căn cứ không áp dụng, không suy 0"; số thô RAW_NULL/MISSING → INCOMPLETE. Giữ nguyên RC02, TRUOC, K7→B7, 0 vật lý → LIMITED | `review_compute.py` |
| R2 | Allowlist env của worker làm rơi PYTHONUSERBASE/CODEX_NO_DELETE_FILES và đường dẫn phụ thuộc/guard | `XayDungK2._env_worker`: giữ cờ khởi động không bí mật, PYTHONPATH launcher đặt (phụ thuộc + thư mục guard), nguồn gốc `openpyxl` đang dùng, thư mục `sitecustomize` đang nạp (`KTT_REVIEW_GUARD_DIR`), không bytecode. Loại mọi tên dạng DSN/PASSWORD/SECRET/TOKEN/PG*/CREDENTIAL. Worker kiểm `guard_dang_nap()` **đầu `main()`**, trước vendor/OpenPyXL/I-O: thiếu guard hoặc guard khác thư mục → thoát mã 4, không ghi gì; máy chủ ghi FAILED `GUARD_KHONG_NAP` | `xay_dung.py`, `review_compute.py` |
| R3 | Lệnh Review giữ `mutation_lock` toàn cục suốt lúc tính | Lock chỉ bao bước chụp danh tính phiên + service. Lệnh chạy trong `_review_lenh` trên **cặp kết nối riêng của thao tác** (login ứng dụng đã `kiem_role_ung_dung` + kết nối chủ bảng đã `kiem_ket_noi_chu` cùng máy chủ/DB), đóng trong `finally`. Không dùng chung GUC/giao dịch, không nhận actor/DSN từ body. GET/đổi vai không chờ CPU; đổi vai không đổi danh tính của thao tác đang chạy; quyền hiện hành vẫn kiểm lại trước tra biên nhận và trước công bố | `giao_dien/m4.py` |
| R4 | `mkdir`/raw/bản làm việc/đầu vào nằm ngoài nhánh lỗi sau khi RUNNING đã commit | Mọi bước dựng nằm trong nhánh kết thúc `SETUP_LOI` → FAILED có bằng chứng (BASIS/LOG; `ket_qua.json` nếu có thì vẫn giữ làm RESULT kể cả khi timeout). Lỗi bất ngờ trong bước tính → FAILED. Lỗi lưu báo cáo → FAILED, không công bố kết quả thiếu báo cáo. Lỗi công bố không phải mất quyền → thử **một** lần đóng FAILED. Thử lại đúng khóa/body đọc cùng FINAL đã kết thúc | `xay_dung.py` |
| R5 | Khóa phiên Review dùng namespace `m4:bien_nhan:` rồi mới khóa HĐ, ngược thứ tự M17 → có thể vòng khóa | Khóa phiên đổi sang namespace riêng `m4:review:`. Thứ tự toàn cục: [m4:review] → HĐ → [m4:bien_nhan giao dịch], trùng M17. Ghép tay và `review_ghi_map` khóa HĐ **trước** biên nhận. Xung đột cùng actor+khóa khác hành động bị chặn chính xác trước hiệu lực: `review_tra` kiểm giữ chỗ `review_run`; trigger M19 `bien_nhan_review_khoa` (BEFORE INSERT trên `m4.bien_nhan`) chặn lệnh M17 dùng khóa đã giữ chỗ, trong cùng giao dịch hiệu lực. Không sửa hàm/bảng M17 | `xay_dung.py`, `sql_review.py` |
| R6 | Đích ghép chỉ kiểm BOQ DA_MAP mới nhất cùng HĐ | Máy chủ phân giải đích bằng `csdl_hop_dong.phu_luc_ap_dung` + `boq_hieu_luc` của vendor trên projection của **cùng snapshot** (ngày NT của đợt). Phải đúng BOQ nguồn hiệu lực, không thì `M4_REVIEW_DICH_KHONG_HIEU_LUC` (409). SQL kiểm lại thêm: ghim dòng `p_boq_dong`; PL đích phải ĐÃ KÝ và hiệu lực ≤ ngày NT; không bị PL hiệu lực sau (ngày hiệu lực, ngày ký, số PL) thêm/thay cùng mã; dòng gốc không bị PL hiệu lực nào thay. Mọi từ chối nằm trước map/nhật ký/biên nhận. Worker gắn `nguon_boq` = đúng dòng engine dùng (mọi nguồn ở `nguon_boq_tat_ca`). PL delta chưa có kiểu vẫn INCOMPLETE | `xay_dung.py`, `sql_review.py`, `review_compute.py`, `review.js` |
| R7 | GET lịch sử/POST ghép về muộn đóng form/đổi lựa chọn/xóa nháp mới; shell không vô hiệu Review lúc đổi tab/HĐ/đợt | Chi tiết bên dưới bảng | `review.js`, `m4.js` |

Chi tiết R7:
- `moRun`, `ghep`, `chay`, `chayLai` và nút gửi lại chụp `genForm` + lựa chọn lúc **vào**. Kết quả về muộn khi đã có nháp mới thì chỉ báo trạng thái: không đóng form, không đổi lựa chọn, không xóa mã/lý do, không vẽ đè.
- Ghép chỉ xóa mã/lý do của đúng dòng khi giá trị vẫn là giá trị đã gửi.
- Lệnh chưa rõ kết quả giữ body/khóa gốc, không dựng lại request.
- Thêm `kttM4Review.tat()`. Shell gọi **đồng bộ** lúc ý định đổi tab, đổi HĐ/vai (`boChon`), đổi đợt (`moDot`), `moHd` sang tab khác và `denBoSung`.
- `tat()` tăng epoch/thế hệ và tắt vùng. Fence kiểm vùng đang hoạt động + epoch + vai + HĐ trước request, sau headers và sau blob; tải báo cáo A muộn không click/không báo.
- `khoaMap` giữ nguyên qua `tat()`: bấm lại đúng lệnh cũ dùng lại khóa cũ và nhận FINAL.
- Không đổi bố cục port từ `checks.js`, không thêm nút "Nạp đợt đã duyệt".

### Tests FIX01 (viết thêm, **NOT_RUN**)

**`test_m4_review_compute.py`**
- **R1:** KHONG_QUY_DINH + RAW_NULL/MISSING → INCOMPLETE, đặt cạnh đối chứng dương KHONG_AP_DUNG tường minh và 0 vật lý → LIMITED. Có thêm bản đầu-cuối `phu_thuoc` → `coverage_l2`, cần lõi nguồn.
- **R2:** `guard_dang_nap` các nhánh; `main` dừng mã 4 không ghi gì; `_env_worker` giữ cờ/guard/đường dẫn và loại DSN/mật khẩu.
- **Tĩnh R3/R5/R6/R7:**
  - Lệnh Review ngoài khối lock, đóng kết nối trong `finally`.
  - Thứ tự HĐ → biên nhận, trigger, namespace `m4:review:`.
  - Các kiểm hiệu lực PL nằm trước ghi.
  - `tat()`/fence/thế hệ form trong `review.js`; `tatReview()` trong `m4.js`.

**`test_m4_review_k2.py`**
- **R03:** R1 trên dữ liệu thật — TT-21 KHONG_QUY_DINH + không có dòng giữ lại → INCOMPLETE, B8 không đạt; TT-10 KHONG_AP_DUNG là đối chứng.
- **R02:** không có DSN trong `vao.json`/`worker.log`/`co_so.json`.
- **R06:** đích không hiệu lực/sai BOQ → 0 delta.
- **R07b:** raw hỏng → FAILED + thử lại cùng FINAL; guard không nạp → FAILED, không `ket_qua.json`.
- **R07c:** Review↔M17 cùng khóa, tuần tự và đồng thời, không treo.
- **R07d:** HĐ có PL-01 đã ký thay HM-02/thêm HM-04 — đợt sau ngày hiệu lực lấy dòng PL; đợt trước lấy dòng gốc; HM-04 tương lai bị từ chối.

**`test_m4_review_http.py`**
- **H05:** worker được giữ bằng Event, sau đó chạy thật. Trong lúc đó GET `/api/m4`, GET danh sách và đổi vai cùng phiên phải trả trong 60 s; lần chạy giữ `tao_boi = A1`.
- **H06:** tài sản có `tat()` và `tatReview()`.
- Fence DOM thật (late A / form B / tab / blob) vẫn cần GUI do Root kiểm; test tĩnh không thay được.

### Giới hạn còn lại sau FIX01
- R02 nonfinite → NULL vẫn chỉ là ghi chú source-state, chưa tái hiện vật lý (theo handoff, không mở thêm).
- Lần chạy RUNNING mà tiến trình máy chủ chết giữa chừng (mất điện/kill) vẫn ở RUNNING. Gói này không có reaper/lease; thử lại đúng khóa trả `dang_chay`. Đây là giới hạn đã biết, không báo thành công.
- Thứ tự khóa và xung đột đã viết theo phân tích tĩnh; chưa có bằng chứng tái hiện runtime.
- Checksum M19 mới (đổi chữ ký `review_ghi_map`, thêm trigger) là RootTO_BIND.

## 8b. FIX02 — guard, receipt và mount Review (NOT_RUN_CODE_ONLY)

Căn cứ: `docs/GIAO-SUA-M4-02A-02-GUARD-MOUNT-VA-RECEIPT.md` (SHA256 `d2bf9686…de6b`).

Phạm vi lượt này:
- Chỉ sửa trong 13 đích đã có, NEW = 0. `m4.css` và `pg_migrations.py` không đổi.
- Thay đổi SQL chỉ nằm trong M19 (`sql_review.py`), vẫn **chưa áp** vào PG thật.
- Guard gốc A517, vendor/reference, M1–18 và mọi path khác không đổi.

Bằng chứng Root trước FIX02 (do Root cung cấp, không phải coder chạy):
- Native pure 38 lượt chạy: 36 PASS / 1 FAIL / 1 ERROR / 0 skip.
  - FAIL: worker trả 4 thay vì 3 dù guard thật đang active (không có sitecustomize).
  - ERROR: NameError do ba assertion đặt nhầm test.
- Bốn kiểm độc lập QD/NA/rawNULL/0 vật lý: PASS.
- Public-DOM: 12 ca NOT_VERIFIED vì setup chưa tới positive; không phải 12 ca sản phẩm FAIL.
- PG/HTTP/worker ngoài: NOT_RUN.

| Mục | Vấn đề | Sửa | Tệp |
|---|---|---|---|
| F1 | Guard bị nhận diện qua module `sitecustomize` → từ chối nhầm guard thật không có sitecustomize; nhận nhầm khi chỉ có marker | Xem chi tiết F1 bên dưới bảng | `review_compute.py`, `xay_dung.py` |
| F2 | Ba assertion của test worker lỗi nằm nhầm trong test env (NameError) | Chuyển nguyên ba assertion (`FAILED`, `bao_cao == []`, sau `main(...) == 3`) về `test_worker_luon_ghi_ket_qua_khi_loi`, dùng đúng thư mục của chính test đó. Không đổi expected, không bắt NameError | `test_m4_review_compute.py` |
| F3 | Exit khác 0 nhưng có `ket_qua.json` SUCCEEDED/PARTIAL đúng raw/basis vẫn có thể được công bố | Chỉ nhận thành công khi tiến trình con đã kết thúc với **exit 0**. Exit khác 0 → `WORKER_EXIT_<mã>` FAILED. Thêm `_hinh_dang_ok`: đúng chế độ, ô đích; đủ mã coverage; trạng thái mỗi mã thuộc danh mục; trạng thái tổng khớp coverage; `lop1` là object, `lop2` có đúng khi L1+L2. JSON/stdout/stderr/đầu vào vẫn giữ làm bằng chứng (RESULT/LOG/INPUT/BASIS); thử lại đúng khóa trả cùng FINAL | `xay_dung.py` |
| F4 | Giữa lần tra biên nhận đầu và lúc tạo lần chạy trong snapshot RR, lệnh M17 cùng khóa có thể commit mà RR không thấy → đến lúc công bố mới va khóa, lần chạy RUNNING mồ côi | Xem chi tiết F4 bên dưới bảng | `sql_review.py`, `xay_dung.py` |
| F5 | `veHd` gọi `veReview` trước khi khung gắn vào document, nên fence `isConnected` chặn GET → không có form | `veHd` mount Review **sau** `box.replaceChildren(card)`. `veReview` bỏ qua nếu vùng đã bị thay trước khi mount. Callback nạp script chỉ vẽ lại theo tab/HĐ/vai hiện hành. Fence connected/active/actor/HĐ/đợt của `review.js` giữ nguyên | `m4.js` |
| F6 | Bên trong `lenh`, toast/status/lỗi/làm mới chỉ kiểm ngữ cảnh, chưa kiểm thế hệ form | Xem chi tiết F6 bên dưới bảng | `review.js` |

Chi tiết F1:
- Bằng chứng mới là **hook xóa/ghi đè thật đang cài**, đọc qua `dau_van_guard()`.
- Với 13 điểm vào (`os.remove/unlink/rmdir/removedirs/replace/rename/renames`, `shutil.rmtree/move`, `pathlib.Path.unlink/rmdir/replace/rename`), kiểm đối tượng đang cài là bản gốc Python (builtin trùng hàm của `nt`/`posix`, hoặc hàm Python trong thư mục stdlib) hay là hook; nếu là hook thì ghi module/qualname/tệp nguồn của nó.
- Máy chủ tự tính dấu vân của chính nó và gửi cho tiến trình con qua `KTT_REVIEW_GUARD_DAU`. Đây là dữ kiện không bí mật; đường dẫn sitecustomize chỉ còn là provenance.
- Tiến trình con, ngay đầu `main()` và trước vendor/OpenPyXL/I-O:
  - yêu cầu ít nhất một hook đang cài;
  - nếu có dấu vân của cha, yêu cầu trùng provenance với cha;
  - không đạt thì dừng mã 4.
- Hook thật đang cài mà **không có** sitecustomize vẫn được nhận. Chỉ có marker/module hoặc hook khác ràng buộc thì bị từ chối.
- Không copy/vá/tắt guard, không gỡ env giữ tệp.

Chi tiết F4:
- Thêm `m4.review_giu_khoa`: bảng giữ chỗ (actor, khóa), chỉ ghi thêm, bật RLS, không cấp cho web.
- Thêm `m4.review_giu`, chạy trong giao dịch READ COMMITTED **ngắn** và **commit trước** khi mở RR. Thứ tự trong hàm: quyền/phạm vi hiện hành → khóa giao dịch biên nhận (namespace M17, qua `_bn_tra`) → đúng body thì trả FINAL, khác hành động/body thì `M4_IDEMPOTENCY_KHAC` → ghi giữ chỗ.
- Trigger biên nhận và `review_tra`/`review_ghi_map` giờ kiểm **hàng giữ chỗ đã commit** thay cho `review_run` được tạo trong RR. Vì vậy lệnh M17 commit sau snapshot RR vẫn bị chặn chính xác trong chính giao dịch hiệu lực của nó, và Review thấy biên nhận M17 đã commit trước khi giữ chỗ.
- Không giữ khóa biên nhận xuyên CPU. Thứ tự [m4:review phiên] → HĐ → [m4:bien_nhan giao dịch] của R5 giữ nguyên. Prefix 1–18 không sửa.

Chi tiết F6:
- `lenh(path, body, ok, f, gf)` nhận thế hệ form chụp tại **ý định gốc** (lúc bấm).
- Mọi toast, trạng thái, lỗi, `napDs`, nút gửi lại và giá trị trả về cho continuation đều đặt sau `ui() = f() && gf === genForm`.
- Các nơi gọi (`chay`, `chayLai`, `ghep`, gửi lại) truyền `gf`.
- `moSauLenh` và `moRun` không còn báo trạng thái A vào nháp B; GET A về muộn thì bị bỏ.
- Bản ghi khóa chưa rõ kết quả giữ nguyên trong `khoaMap`: bấm lại đúng lệnh cũ sẽ dùng lại khóa cũ.

### Tests FIX02 (viết thêm, **NOT_RUN**)

**`test_m4_review_compute.py`**
- **F1:**
  - Dương tính thật: chỉ chạy khi môi trường đang dưới guard thật, nếu không thì skip (NOT_RUN). Dấu vân của chính tiến trình có hook và được nhận.
  - Quyết định: hook thật không có sitecustomize → nhận; chỉ marker → từ chối; thiếu → từ chối; sai provenance → từ chối; dấu vân hỏng → từ chối.
  - Dấu vân đọc đối tượng thật; `guard_dang_nap` không dựa vào sitecustomize; kiểm guard nằm trước I/O.
  - Env của worker mang dấu vân của cha.
- **F2:** ba assertion đã về đúng test.
- **F3:** `_hinh_dang_ok` có đối chứng dương L1/L1+L2 và các ca âm; tĩnh: exit ≠ 0, kết quả chỉ được đọc khi exit 0, RESULT vẫn được lưu.
- **F4 (tĩnh):** thứ tự trong `review_giu`; bảng/PK/trigger; service gọi giữ chỗ trước RR.
- **F5 (tĩnh):** mount sau attach; bỏ qua khi vùng đã mất.
- **F6 (tĩnh):** kiểm `ui()` đứng trước mọi callback ở cả nhánh thành công lẫn lỗi; 4 nơi gọi truyền `gf`; `moSauLenh` không báo trạng thái.

**`test_m4_review_k2.py`**
- **R07b:** dấu vân hook sai ràng buộc → FAILED, không có `ket_qua.json`. Worker thật exit 0 nhưng mã báo 5 kèm JSON trông như thành công → FAILED, không công bố, bằng chứng vẫn giữ, thử lại trả cùng FINAL.
- **R07e (F4, rào có kiểm soát qua `_co_so`, không dựa timing):**
  - (a) M17 cùng khóa commit khi Review đang trong RR → M17 bị `M4_IDEMPOTENCY_KHAC`, không tạo đợt; Review thắng duy nhất.
  - (b) Ngược thứ tự → Review bị chặn ở bước giữ chỗ, 0 delta.
  - (c) Đúng body → FINAL trước khi chụp basis.

**`test_m4_review_http.py`**
- **H06:** tài sản thật `/m4.js` mount sau attach; `/m4/review.js` truyền `gf` vào `lenh`.

### Giới hạn còn lại sau FIX02
- **F1 giả định** guard gốc cài hook bằng cách thay các điểm vào xóa/ghi đè. Nếu A517 chỉ dùng audit hook (`sys.addaudithook`), Python không có API liệt kê hook, nên kiểm này sẽ từ chối và cần Root xác nhận cơ chế. Coder không đọc guard riêng tư.
- **Thứ tự khóa F4** đã viết theo phân tích tĩnh; chưa có tái hiện runtime.
- **Tiến trình con trên Windows:** `subprocess.run` hết giờ thì kill và chờ tiến trình con trực tiếp. Worker không sinh tiến trình cháu, nhưng chưa có bằng chứng runtime.
- **Luồng DOM thật** (mount positive có form/GET, A muộn sau nháp B, tab/blob): NOT_VERIFIED.
- `tests/test_crm_41_02.py` vẫn lệch (khẳng định 18 migration).
- Checksum M19 mới (thêm bảng `review_giu_khoa`, hàm `review_giu`, trigger kiểm giữ chỗ): RootTO_BIND.

## 8c. FIX03 — guard child, refresh GET và nút báo cáo (NOT_RUN_CODE_ONLY)

Căn cứ: `docs/GIAO-SUA-M4-02A-03-GUARD-CHILD-VA-REFRESH.md` (SHA256 `35fd54af…dc9abdd`).

Phạm vi lượt này:
- Chỉ sửa trong 13 đích đã có, NEW = 0.
- Source thay đổi: `review_compute.py` (F1) và `review.js` (F2, F3). SQL/M19, `pg_migrations.py`, `m4.css`, `m4.js`, guard gốc, vendor không đổi.

Bằng chứng Root trước FIX03 (do Root cung cấp, không phải coder chạy):
- Native pure 45/45 PASS; 4 kiểm độc lập QD/NA/rawNULL/0 vật lý PASS.
- Guard-CWD độc lập: FAIL.
- UI07: 5 PASS / 2 CONTRACT_FAIL (late-refresh) / 7 NOT_VERIFIED. 7 ca tải NOT_VERIFIED vì không thấy nút; không phải 7 lỗi hành vi tải.
- P02 header: PASS.
- PG/HTTP/worker ngoài: NOT_RUN.

| Mục | Vấn đề | Sửa | Tệp |
|---|---|---|---|
| F1 | `dau_van_guard` đưa `co_filename` = `<frozen os>` (của `os.removedirs`/`os.renames`) qua `abspath` → thành đường dẫn theo CWD, `goc=False`. Cha (CWD máy chủ) và con (thư mục lần chạy) có dấu vân khác nhau nên worker bị từ chối dù hook gốc đang active; sentinel còn có thể bị đếm là hook | `_nguon_ma` nhận diện nguồn **trước** khi chuẩn hóa. Chỉ coi là stdlib frozen khi sentinel `<frozen M>` trùng đúng module định nghĩa hàm **và** module đó thật sự nạp từ frozen (`__spec__.origin == "frozen"`); trường hợp này `goc=True`, `tep=None`, không phụ thuộc CWD. Sentinel khác giữ nguyên chuỗi (không `abspath`) và không được coi là stdlib. `hook_hoat_dong` chỉ đếm hook có **tệp mã nguồn tuyệt đối**; sentinel/đường dẫn tương đối/không nguồn không phải bằng chứng. Giữ nguyên: hook thật không có sitecustomize được nhận; marker-only/thiếu hook/sai provenance bị từ chối; con fail closed trước I/O; allowlist env không credential | `review_compute.py` |
| F2 | `napDs`: thành công gán `ds`/`dsLoi`/`sel.tep` rồi mới kiểm thế hệ form và còn ghi trạng thái cảnh báo; lỗi xóa `ds/kq/runChon` và ghi lỗi/trạng thái trước khi kiểm form | Thế hệ form chụp lúc vào được đưa vào **fence chung** `dung()` (epoch, vùng đang hoạt động, thế hệ GET, lựa chọn, thế hệ form). Fence kiểm sau headers, sau body, và ở đầu nhánh lỗi, **trước** mọi gán dữ liệu/lựa chọn, xóa, lỗi, trạng thái, vẽ. Bỏ thông báo "Dữ liệu mới đã về…" (trạng thái A vào B). Làm mới đúng ngữ cảnh hiện hành vẫn cập nhật dữ liệu/lỗi; 403/404 hiện hành vẫn có hiệu lực | `review.js` |
| F3 | `exportButtons` truyền mảng lồng hai mức vào `el()`, mà `el()` chỉ làm phẳng một mức → nút bị biến thành chuỗi, không có nút thật | `.map` → `.flatMap`: mỗi artifact đã đăng ký thành đúng một nút gọi `tai(a)`. Thứ tự loại/nhãn/kiểu giữ nguyên; `el()` và các khối khác không đổi (đã kiểm các chỗ truyền con chỉ một mức mảng) | `review.js` |

### Tests FIX03 (viết thêm, **NOT_RUN**)

**`test_m4_review_compute.py`**
- **F1:**
  - Hàm stdlib frozen thật là bản gốc, `tep=None`; tính lại sau khi đổi CWD cho cùng dấu vân.
  - Sentinel `<frozen os>` gắn vào hàm không thuộc `os` → `sentinel`.
  - "Hook" chỉ có sentinel hoặc đường dẫn tương đối → không phải bằng chứng, bị từ chối.
  - **Tiến trình con thật** (cùng Python, env worker do máy chủ dựng, cwd riêng): tính ra cùng dấu vân với cha và chấp nhận guard. Chỉ đọc thuộc tính hàm, không thử xóa tệp.
  - Fixture FIX02 chuyển sang đường dẫn tuyệt đối thật; các ca dương/âm cũ giữ nguyên.
- **F2 (tĩnh):** fence gồm thế hệ form; hai lần kiểm trước `ds = r`/`sel.tep`; nhánh lỗi kiểm trước mọi hiệu ứng; không còn thông báo A vào B.
- **F3 (tĩnh):** `flatMap`, `tai(a)`.

**`test_m4_review_k2.py`**
- **R02:** worker thật chạy với cwd = thư mục lần chạy (khác cwd máy chủ) không bị `GUARD_KHONG_NAP`.

**`test_m4_review_http.py`**
- **H06:** tài sản thật mang fence F2 và nút F3.
- **H07:** lần chạy L1 thật có artifact báo cáo đăng ký; mỗi artifact tải qua route quyền hiện hành ra bytes không rỗng đúng hash/độ dài.

### Giới hạn còn lại sau FIX03
- Luồng DOM thật (late success/error sau nháp B, nút báo cáo → tải → blob, tab/vai/unmount) chỉ có kiểm tĩnh và kiểm HTTP dữ liệu nền; GUI vẫn NOT_VERIFIED cho tới khi Root chạy shell thật.
- F1 vẫn giả định guard A517 thay các điểm vào xóa/ghi đè (đã khớp với mô tả "original A517 hooks đang active" của Root). Audit-hook-only vẫn là giới hạn đã nêu ở §8b.
- F4 (FIX02) mới khép tĩnh; PG causal verification vẫn pending. Checksum M19: RootTO_BIND. `tests/test_crm_41_02.py` vẫn lệch.

## 8d. FIX04 — lỗi phạm vi (M20) và hai lỗi kiểm thử (NOT_RUN_CODE_ONLY)

Căn cứ:
- `docs/GIAO-SUA-M4-02A-04-PHAM-VI-VA-KIEM-THU.md` (SHA256 `bce83444…babf0145`).
- Quyết định engine dùng chung `docs/QUYET-DINH-ENGINE-TRICH-THAM-SO-DUNG-CHUNG.md` (SHA256 `54be96e9…e17e811dfadb`). Chỉ đọc làm tài liệu đã pin: lượt này **không** mở engine/API trích chung, không đổi thuật toán vendor hay Review L1/L2.

Bằng chứng Root trước FIX04 (do Root cung cấp, không phải coder chạy):
- Native pure 49 và public DOM 14 ca: đạt.
- Native PG 12 ca: 11 đạt, 1 lỗi fixture (R07d).
- Native HTTP 7 ca: 5 đạt, 2 không đạt (H04, H01).
- H04 trả 400/CSDL_TU_CHOI. Sáu owner connection mới (READONLY) xác nhận SQLSTATE 55000 tại `review_quyen` dòng 18; A1 SOAN dương.

| # | Nguyên nhân | Sửa | Tệp |
|---|---|---|---|
| 1 | M19 `m4.review_quyen` khai `d record`, chỉ `SELECT INTO d` khi có đợt, nhưng biểu thức REVIEW tham chiếu `d.trang_thai`. PL/pgSQL dựng tham số cho cả biểu thức nên trên backend mới, khi không có đợt (B1 ngoài dự án, reviewer không đợt), gặp SQLSTATE 55000 thay vì mã domain | Xem chi tiết M20 bên dưới bảng | `m4/sql_review.py` (append sau EOF), `ha_tang/pg_migrations.py` (append sau EOF) |
| 2 | R07d dùng cùng khóa cho TẢI tệp BOQ và NHẬP BOQ của cùng tệp → xung đột idempotency đúng nghiệp vụ, không phải lỗi sản phẩm | Khóa tải đổi thành `pl-tep-boq-goc`/`pl-tep-boq-pl`, khác khóa nhập. Không nới idempotency; giữ nguyên expected resolver và mọi kiểm THAY/THEM/trước ngày hiệu lực/đích không hợp lệ | `tests/test_m4_review_k2.py` |
| 3 | H01 cấm chuỗi `innerHTML` trên toàn tệp, trùng cả chú thích hợp lệ "không innerHTML" | Kiểm **việc dùng** thật: `.innerHTML`/`.outerHTML` (cả `["innerHTML"]`), `insertAdjacentHTML(`, `document.write(`. Có đối chứng: biểu thức dùng thật bị bắt, chú thích không bị bắt. Giữ kiểm bytes/no-store/route đơn, thêm kiểm `textContent`. Không sửa chú thích, không skip | `tests/test_m4_review_http.py` |

Chi tiết M20 (`M0020_M4_REVIEW_QUYEN`):
- **Một** câu `CREATE OR REPLACE FUNCTION m4.review_quyen(...)`, cùng chữ ký/STABLE/SECURITY DEFINER/search_path.
- Biến kiểu xác định `t m4.tep%ROWTYPE`, `d_du_an`/`d_trang_thai` `%TYPE`. Nhánh không đợt trả NULL **trước** khi đụng dữ liệu đợt.
- Ngữ nghĩa giữ nguyên: SOAN đúng dự án; REVIEW chỉ trên tệp gắn đúng đợt DA_NOP; tệp HO_SO_DOT .xlsx đúng dự án.
- Không GRANT/REVOKE/bảng/policy/hàm khác. CREATE OR REPLACE giữ chủ sở hữu/ACL. Không sửa mapper lỗi chung.
- M19 và toàn bộ 1–19 **không đổi byte**: `pg_migrations.py` 869.545 byte đầu = `73975e09…dd30e`; `sql_review.py` 37.415 byte đầu = `64bd3f9d…48f0`, kể cả các helper dùng chung. M20 là phần tử **cuối**.

### Tests FIX04 (viết thêm, **NOT_RUN**)

**`test_m4_review_compute.py`**
- **Prefix:**
  - Prefix 869.545 byte của `pg_migrations.py` và 37.415 byte của `sql_review.py` khớp SHA của bản đã áp dụng.
  - Đuôi `pg_migrations.py` không đụng M19 và kết thúc bằng đăng ký M20.
  - Đuôi `sql_review.py` không định nghĩa lại M19 hay helper.
- **Registry:** `len == PG_SCHEMA_VERSION == 20`; 17/18/19 identity; `[19]` và `[-1]` là M20.
- **Nội dung M20:**
  - Đúng một câu; không GRANT/REVOKE/ALTER/DROP/DELETE/INSERT/UPDATE/POLICY/TABLE.
  - Đầu hàm trùng M19 (chữ ký/STABLE/SECURITY DEFINER/search_path).
  - Không còn `d record`/`d.`; nhánh không đợt đứng trước `d_trang_thai`; đủ điều kiện phạm vi.

**`test_m4_review_k2.py`**
- **R00:** DB riêng migrate tới 19 + seed rồi nâng lên 20.
  - Lịch sử 1–19 (version/checksum/applied_at) nguyên trạng; checksum 20 đúng M20.
  - Số dòng dữ liệu cũ không đổi; ACL/chủ/SECURITY DEFINER/STABLE/proconfig của hàm giữ nguyên.
  - Migrate lại không đổi; định nghĩa thật trên DB là bản M20.
- **R01:** DB mới lên đúng 1–20.
- **R01b:** mỗi ca trên cặp kết nối app/owner **mới**, không đợt.
  - A1 → `SOAN`; B1 → `M4_KHONG_CO_QUYEN_DU_AN`; reviewer → `M4_REVIEW_PHAM_VI`.
  - Qua dịch vụ cũng đúng mã, 0 delta (gồm `review_giu_khoa`).
  - Hàm thật trên DB là bản M20.
- **R07d:** khóa tải ≠ khóa nhập.
- Giữ nguyên ca REVIEW dương trên đợt đã nộp và ca âm đợt nháp/tệp không gắn đợt (R04).

**`test_m4_review_http.py`**
- **H01:** kiểm việc dùng HTML thật, có đối chứng; `version == 20`.
- **H04:** mã chính xác theo actor — B1 `403/M4_KHONG_CO_QUYEN_DU_AN`, reviewer `403/M4_REVIEW_PHAM_VI`, không chấp nhận lẫn mã hay 400.

### Giới hạn sau FIX04
- M20 chưa áp vào DB DEMO retained (Root áp và kiểm).
- PG causal F4 (FIX02) vẫn pending.
- GUI vẫn NOT_VERIFIED.
- `tests/test_crm_41_02.py` vẫn lệch (18 migration).
- Checksum M20: RootTO_BIND.
- Engine trích dùng chung: theo hàng đợi CRM → M2-00 → E1-MUA, không thuộc lượt này.

## 8e. FIX05 — fixture nâng migration 19 → 20 (test-only, NOT_RUN_CODE_ONLY)

Căn cứ: `docs/GIAO-SUA-M4-02A-05-FIXTURE-MIGRATION.md` (SHA256 `3494959b…bdebdb43b`).

**Bằng chứng Root** (do Root cung cấp, coder không chạy):
- Native K2: 14 ca, 13 PASS / 1 FAIL — duy nhất R00.
- HTTP: 7/7 PASS.
- Kiểm độc lập M20: PASS.
- Không gọi là cả 21 ca PASS.

**Nguyên nhân:** lỗi fixture, không phải lỗi product hay migration. R00 gọi `pg.migrate(c, 19)` rồi `crm_demo.khoi_tao(c)`, mà helper này tự migrate mặc định lên 20. Vì vậy "lịch sử tại 19" chụp sau đó thực tế đã có dòng 20.

**Đã sửa:** chỉ phần setup của `test_r00_nang_19_len_20` trong `tests/test_m4_review_k2.py`.
- Bỏ seed CRM (và import cục bộ `crm_demo`); không gọi helper nào có thể tự migrate.
- Sau `migrate(c, 19)`: kiểm `schema_version == 19` và lịch sử đúng 1..19.
- Dựng đúng hai pháp nhân `PN_DEMO_A`/`PN_DEMO_B` (nhãn DEMO) bằng schema hiện có. Không seed CRM/M9, không hồ sơ đã duyệt, không quyền giả.
- Gọi `m4_demo.khoi_tao(c)` thật, assert `DU`.
- Kiểm lại schema 19 / lịch sử 1..19 **sau seed**, trước khi chụp lịch sử, số dòng và ACL.
- Mọi oracle nâng 20 phía sau giữ nguyên:
  - checksum/identity/applied_at của 1–19 bất biến;
  - migrate mặc định lên 20, checksum dòng 20 đúng M20;
  - số dòng, ACL/chủ/SECURITY DEFINER/STABLE/proconfig giữ nguyên;
  - migrate lại không đổi;
  - hàm thật trên DB là bản M20.

**Không đổi:**
- 13 method K2 khác, HTTP, pure/DOM, guard.
- Product, SQL, migrations 1–20, vendor, CRM/M9.
- NEW = 0. Tệp sửa: `tests/test_m4_review_k2.py` và báo cáo này.

**Self-test:** NOT_RUN_CODE_ONLY — Root kiểm diff/hash rồi quyết định chạy lại.

## 9. Tách bạch trạng thái (sau FIX05)

| Hạng mục | Trạng thái |
|---|---|
| Code (13 đích; FIX01–FIX04 sửa trong các đích đã có, NEW = 0; FIX04 thêm M20 append-only) | Đã viết, **chưa chạy** |
| Self-test (3 tệp test, gồm phần FIX01–FIX05) | NOT_RUN_CODE_ONLY |
| Bằng chứng Root trước FIX05 (do Root cung cấp) | K2 14 ca: 13 PASS / 1 FAIL (R00 fixture); HTTP 7/7 PASS; M20 độc lập PASS; FIX05 chỉ sửa setup R00, chưa chạy lại |
| Bằng chứng Root trước FIX04 (do Root cung cấp) | Native pure 49 + public DOM 14 đạt; PG 12 ca: 11 đạt / 1 lỗi fixture (R07d); HTTP 7 ca: 5 đạt / 2 không đạt (H04 SQLSTATE 55000 → 400, H01 kiểm chuỗi trong chú thích); đã sửa trong code/test, chưa chạy lại |
| Bằng chứng Root trước FIX03 (do Root cung cấp) | Native pure 45/45 PASS; 4 enum độc lập PASS; guard-CWD độc lập FAIL (F1, đã sửa trong code, chưa chạy lại); UI07 5 PASS / 2 CONTRACT_FAIL (F2) / 7 NOT_VERIFIED (F3 nút); P02 header PASS; PG/HTTP/worker ngoài NOT_RUN |
| Bằng chứng Root trước FIX01 (do Root cung cấp) | Native pure 30 PASS / 0 skip; một ca độc lập FAIL (R1) |
| Bằng chứng Root trước FIX02 (do Root cung cấp) | Native pure 38 lượt: 36 PASS / 1 FAIL (guard, F1) / 1 ERROR (F2) / 0 skip — **không phải 38 PASS**; 4 kiểm độc lập QD/NA đều PASS; public-DOM 12 NOT_VERIFIED; PG/HTTP/worker ngoài NOT_RUN. F1/F2 đã sửa trong code, chưa chạy lại |
| Root independent | Chưa có — Root kiểm sau khi phiên này terminal/freeze |
| GUI 1280–1440 | NOT_VERIFIED |
| Mức tối đa có thể đạt sau khi Root chạy | `M4_02A_L1_L2` hữu hạn. Full Review/L3/OCR/approvalPDF/AP/Request chưa tự PASS |
