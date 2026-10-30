# G3 · đợt 3 (sau mốc N) — OCR-4a, AI-4a: khung chạy engine bằng backend giả

**Phần chung:**
- như `GIAO-G2-DOT-A.md`, mục "Phần chung", và `docs\47-core\engine\GIAO-ENGINE-1.md` (bảng dùng lại / bọc / sửa / viết mới — CD-036);
- dùng khung G2-21 (`core\tien_trinh.py`, `sdk_core\bootstrap.py`) và SDK engine G2-20 (`sdk_core\engine.py`);
- **không gọi ABBYY / AI thật**, không bí mật thật, không tài khoản Windows riêng (OCR-4b / AI-4b chờ G2-23 / G2-33);
- manifest `engine.json` chỉ viết khi lát có năng lực đã kiểm (xem `KE-HOACH-LAT-G2-G3.md`). Khung giả lập **không** là năng lực, nên **không tạo `engine.json`** ở hai lát này.

## OCR-4a · `e_ocr` khung chạy giả lập
**Tệp:**
- `src\kho_tri_thuc\engines\e_ocr\chay.py`
- `tests\test_g3_ocr_4a.py`

**Việc:** cổng / readiness / Job / drain qua bootstrap G2-21; backend OCR giả; không gọi ABBYY.

**Test:** tiến trình thật khởi động qua khung, báo sẵn sàng, nhận việc giả, drain sạch.

## AI-4a · `e_hoi_ai` khung chạy giả lập
**Tệp:**
- `src\kho_tri_thuc\engines\e_hoi_ai\chay.py`
- `tests\test_g3_ai_4a.py`

**Việc:** readiness / cổng / Job / drain; provider AI giả; **Local không mặc định luôn chạy**; dùng DTO AI-1a.

**Test:** như OCR-4a; không mở kết nối mạng thật.

Báo cáo mỗi lát ≤ 3 dòng.
