# G3 · đợt 5 — OCR-3, HD-3a, AI-5a

**Phần chung:** như `GIAO-G3-DOT-4.md`:
- mẫu khung chạy `engines\e_ocr\chay.py` (chờ ACK, giữ kết quả chưa ACK, không thoát khi drain);
- quy tắc manifest (chỉ khai capability đã có test, schema G2-17b);
- không gọi dịch vụ thật; DEMO;
- nguồn ngoài repo chỉ đọc.

## OCR-3 · `e_ocr` — bảng DOCX bảo toàn cấu trúc
**Tệp:**
- `src\kho_tri_thuc\engines\e_ocr\bang.py`
- `tests\test_g3_ocr_3.py`

**Việc:**
- bọc `word_layout(embedded_pages=[])` của `mask_ocr`; định vị nguồn như `van_ban.py` (OCR-2 vòng 2, đã có cơ chế `KTT_NGUON_OCR`);
- ra `du_lieu_bang.v1`;
- giữ ô rỗng / ô gộp, hàng / cột / vị trí;
- **không** suy bảng từ chuỗi văn bản.

**Test:** DOCX DEMO có ô rỗng, ô gộp, bảng dài; contract đạt.

## HD-3a · `e_hoa_don` — khung engine + Node giả trong cây Job
**Tệp:**
- `src\kho_tri_thuc\engines\e_hoa_don\engine.json`
- `src\kho_tri_thuc\engines\e_hoa_don\chay.py`
- `tests\test_g3_hd_3a.py`

**Việc:**
- khung chạy theo mẫu `e_ocr\chay.py`;
- tiến trình Node giả (stub) thuộc Job của engine (chết cùng);
- cổng bị chiếm → lỗi, không dò;
- stub **không** chứng minh protocol nguồn thật.
- **Manifest:** chỉ capability đã test (`hoa_don.doc_xml@1` từ HD-1; tải giả **không** quảng bá như năng lực thật). Phần tải cần màn hình khai ở lát sau (HD-2c) với `CD-038-ENGINE-2A`.

## AI-5a · `e_hoi_ai` — nhật ký / thống kê qua Core, sống qua restart
**Tệp:**
- `src\kho_tri_thuc\engines\e_hoi_ai\nhat_ky.py`
- `tests\test_g3_ai_5a.py`

**Việc:**
- bọc `BoGhiNhatKy` / thống kê hiện có (`tri_thuc\cong_ai.py`);
- metadata lưu qua Core (SDK engine `ket_qua` / audit G2-20), không chỉ RAM;
- thống kê / kiểm xác suất không mất khi engine tự đóng.

**Test:** ghi → dừng engine → khởi động lại → đọc lại đúng.

Báo cáo mỗi lát ≤ 3 dòng.
