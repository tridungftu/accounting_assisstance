# MASK-2 — Lõi Mask v2: định danh đã biết + kiểm dấu vết (`dau_vet` của AnDanh); đo lại độ phủ

Bạn là worker Claude (Opus) của lead. Anh đã chốt (TL 48 `D:\Claude\Phan mem ho tro ke toan\48-cong-ai-local-luon-co-cloud-qua-mask-v2.md` §3, §4 dòng "Che", §6 dòng MASK-2; hộp thư CD-001; QD-20261025-23/-24): **làm ngay, không hỏi lại**. Làm **chỉ** trong `D:\GPT\Phan mem Mask file\Mask file v2` theo đúng `CLAUDE.md` của Mask v2: không git, không xóa tệp, ghi `CHANGELOG.md`, test + benchmark độ phủ **không giảm**; **không đọc/sửa** `data\`, `..\Mask file\data\`, `*.maskvault`, `*.maskkeep`, `*.key`, `config\mask-api.key`, `.backups\`, `.venv*\`, `File ví dụ\`. Không mạng. Lệnh > 1–2 phút → `run_in_background`. Trước khi sửa: sao lưu các tệp sẽ sửa vào `D:\Claude\Phan mem ho tro ke toan\LUU-TRU\mask2-sao-luu-<giờ>\` kèm SHA (như MASK-1).

**Tham chiếu chỉ đọc (không sửa):** bộ che `AnDanh` + `dau_vet()` của engine #6 — `D:\Claude\Ho tro review ho so xay dung\review_xaydung\trich_xuat\ai_cloud.py` (tìm `class AnDanh`, `dau_vet`). Viết lại logic tương đương trong lõi Mask v2, không import chéo dự án.

**Việc:**
1. **Định danh đã biết vào lõi** (`privacy/core.py`/`detectors.py`, không chỉ ở `auto_api.py`): giá trị khai kèm `nhom` được che **cả khi văn bản viết khác cách** — so theo "bộ khung" (bỏ dấu tiếng Việt, bỏ ký tự không phải chữ/số) cho định danh ≥ 6 ký tự; số có phân cách `[\s.,\-/]{1,3}` (gồm dấu phẩy, 2 dấu cách, xuống dòng giữa số — hay gặp ở PDF/OCR); mã chữ khác dấu ("HĐ-2026/015" ~ "HD 2026/015"). Giá trị khai có dạng giống bí danh (`[ABC] …`) → **từ chối 400** thay vì bỏ qua im lặng.
2. **Kiểm dấu vết vào `verify()`**: gộp phép kiểm `dau_vet` của AnDanh (còn sót mảnh định danh sau khi che) vào bước kiểm trước khi trả `gui_duoc=true`; còn sót → 422 `con_sot`, không tạo lượt.
3. **Không che số tiền** (Anh chốt): số liền 10–19 chữ số **có ngữ cảnh tiền** ("Tổng tiền thanh toán: 1250000000", "…000 đồng", trường hóa đơn tiền) không bị che thành `[TAI_KHOAN_…]`; số tài khoản/định danh khai rõ `nhom` vẫn che. Ghi rõ quy tắc phân biệt.
4. **Giao diện:** nút "Khóa danh mục ngay" gọi thẳng, không bị bỏ qua khi giao diện đang bận (`app.js` hàm `task`/cờ `busy` ~:174-175, 644-647).
5. **Test + đo:** ca DEMO cho 1–4 (gồm "001,234,567,890", số xuống dòng giữa chừng, 2 dấu cách, mã < 8 chữ số, mã chữ khác dấu, số tiền 10 chữ số trong câu tiền); benchmark bộ chính + `held_out` trước/sau (còn lộ, thay nhầm) — **không được giảm**; bảng trước/sau vào `CHANGELOG.md`.

**Không làm:** lưu cụm mới chờ duyệt (MASK-3), đổi định dạng `.maskvault`/`.maskkeep`, cổng AI phía phần mềm kế toán (AI-2).
**Báo cáo cuối (≤ ½ trang):** sửa ở tệp:dòng · bảng test/benchmark trước–sau · ca test mới · việc chưa làm.
