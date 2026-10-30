# G3 · đợt 2 — OCR-1, MASK-1, AI-1a (khai báo engine, không khung chạy)

**Quyết định lead 31/10 02:30:**
- Ba lát này chỉ khai báo manifest / schema / DTO theo chuẩn SDK §3.9 (engine manifest mẫu) và sổ contract G2-17, cùng test.
- Không dựng khung chạy, cổng hay tiến trình (thuộc OCR-4a / MASK-5 / AI-4a, chờ mốc N = G2-20 + G2-21).

**Phần chung:**
- như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung", và `docs\47-core\engine\GIAO-ENGINE-1.md` (bảng dùng lại / bọc / sửa / viết mới — CD-036);
- không sửa nguồn ngoài repo (`D:\GPT\OCR`, `D:\GPT\Phan mem Mask file\Mask file v2`): chỉ đọc để khai đúng năng lực đã có;
- không gọi ABBYY / Mask / AI thật;
- không công bố capability hay schema chưa kiểm (manifest chỉ quảng bá phần đã có và đã test).

## OCR-1 · `e_ocr`
**Tệp:**
- `src\kho_tri_thuc\engines\e_ocr\engine.json`
- `tests\test_g3_ocr_1.py`

**Căn cứ:** `GIAO-ENGINE-1.md` phần `e_ocr` (dòng ~13–60); chuẩn SDK §3.9 và §3.7; contract kỹ thuật G2-17.

**Việc:** manifest đúng schema G2-17; không quảng bá backend hoặc năng lực chưa kiểm.

**Test:** manifest đạt meta-schema; mọi `$ref` phân giải offline; không có capability ngoài danh sách đã có.

## MASK-1 · `e_mask`
**Tệp:**
- `src\kho_tri_thuc\engines\e_mask\engine.json`
- `src\kho_tri_thuc\engines\e_mask\contract\du_thao.json`
- `tests\test_g3_mask_1.py`

**Căn cứ:** `GIAO-ENGINE-1.md` phần `e_mask` (dòng ~70–125).

**Việc:**
- manifest phần đã có;
- `du_thao.json` là **dự thảo** 4 schema ánh xạ đúng trường MASK-1/2 để Anh duyệt, đánh dấu chưa kích hoạt.

**Test:** schema nháp không được kích hoạt hoặc đăng ký; manifest không quảng bá phát hiện / che tài liệu (MASK-3/4 còn chờ).

## AI-1a · `e_hoi_ai`
**Tệp:**
- `src\kho_tri_thuc\engines\e_hoi_ai\engine.json`
- `src\kho_tri_thuc\engines\e_hoi_ai\dto.py`
- `tests\test_g3_ai_1a.py`

**Căn cứ:** `GIAO-ENGINE-1.md` phần `e_hoi_ai` (dòng ~135–175); cổng AI trong repo (`src\kho_tri_thuc\tri_thuc\` — tìm `YeuCauAI`, `TruongAI`, `KetQuaAI`, `CongAI`).

**Việc:** giữ `YeuCauAI / TruongAI / KetQuaAI` (tái dùng, không định nghĩa lại); không DB, không client AI mới.

**Test:** DTO là chính lớp gốc (identity); manifest đạt schema; không import client mạng.

Báo cáo mỗi lát ≤ 3 dòng.
