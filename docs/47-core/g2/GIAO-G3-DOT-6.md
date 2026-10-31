# G3 · đợt 6 — MASK-5 (khung chạy Mask, phần không cần tài khoản riêng); sửa test CR1

## MASK-5a · `e_mask` khung chạy (giả lập)
**Tệp:**
- `src\kho_tri_thuc\engines\e_mask\chay.py`
- `tests\test_g3_mask_5.py`

**Căn cứ:** `docs\47-core\engine\GIAO-ENGINE-1.md` phần `e_mask` (dòng ~70–125); mẫu `engines\e_ocr\chay.py`.

**Việc:**
- chạy nguyên `run_privacy.py` của Mask v2 bằng `--port` đúng cổng do Core cấp — **trong test dùng tiến trình Mask giả**, không chạy Mask v2 thật;
- không nới Host / Origin / proxy UI;
- **phát hiện thiếu seam cấp khóa** trước khi chạy nguồn → báo lỗi, không chạy;
- chờ ACK khi drain như mẫu.
- **Không** tài khoản Windows riêng (MASK-5b, chờ G2-33b).
- Không `engine.json` (chưa có capability đã kiểm — MASK-2 chờ Anh duyệt schema).

## CR1-T · sửa test CR1 đọc bảng theo tiêu đề
**Tệp:** `tests\test_g2_cr1.py`

**Việc:** thay đọc bảng đặc tả theo số dòng cứng bằng tìm theo tiêu đề mục (`### 3. \`du_an_dang_ban.v1\`` → bảng kế tiếp). Không đổi assertion.
