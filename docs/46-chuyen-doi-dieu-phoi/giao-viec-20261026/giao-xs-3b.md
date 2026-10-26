# XS-3b · Bọc OCR và AI thành engine qua cổng có sẵn (CD-017, CD-019)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM. Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ: dừng, ghi "Cần lead". Không có `python` thì ghi NOT_RUN; lead chạy test.
- Test chạy được dưới guard giữ tệp `CODEX_NO_DELETE_FILES` (thư mục tạm riêng mỗi test, không phụ thuộc việc xóa tệp).

**Căn cứ:** TL 53 `D:\Claude\Phan mem ho tro ke toan\53-kien-truc-xuong-song-engine-module.md` (§8 dùng chung); `docs\46-chuyen-doi-dieu-phoi\KK-XUONG-SONG.md` §2 dòng XS-3b và §4 (E-OCR, E-AI).

**Đã có (chỉ import, KHÔNG sửa):**
- `ha_tang/engine.py` (`Engine`, `KhaiBaoEngine`, `KetQuaXuLy`, `TrangThaiEngine` XONG/CHO/LOI, `hash_du_lieu`);
- `ha_tang/danh_ba_engine.py` (`DanhBaEngine.dang_ky`);
- `ha_tang/cong_ocr.py` (`CongOCR.ocr(raw, duoi, huy=...)`, sổ trang dùng chung);
- `tri_thuc/cong_ai.py` (`CongAI.goi(YeuCauAI)` → `KetQuaAI`; Local trước, Cloud chỉ qua Mask v2; loại việc `HOI_DAP_VAY` chỉ Local);
- bộ test mẫu `tests/test_xs3_engine.py` (`kiem_tra_mau_engine`, `BoTestHopDongEngine`).

**Tệp (2):** `ha_tang/engine_cong.py` mới; `tests/test_xs3_cong.py` mới.
**Không sửa** `danh_ba_engine.py`, `cong_ocr.py`, `cong_ai.py`, `engine.py` (lát XS-3d song song cũng đăng ký engine → mỗi lát tự có hàm đăng ký riêng).

**Việc:**
1. `EngineOCR` (mã `E-OCR`, phiên bản `v1`): nhận một `CongOCR` đã khởi tạo (tiêm qua hàm dựng). Vào: bytes + đuôi tệp. Ra: DOCX bytes. Gọi đúng `CongOCR.ocr`, không tự gọi ABBYY, không tạo thư mục/sổ trang thứ hai.
2. `EngineAI` (mã `E-AI`, phiên bản `v1`): nhận một `CongAI` đã khởi tạo. Vào: `YeuCauAI`. Ra: nội dung `KetQuaAI` (giữ nguyên trường, trích dẫn, nguồn Local/Cloud, mã yêu cầu/lý do). Gọi đúng `CongAI.goi`; **không** tự chọn Cloud, không đổi loại việc, không có đường gọi nhà cung cấp trực tiếp.
3. Ánh xạ trạng thái: kết quả cổng bình thường → `XONG`. Tình huống "chưa làm được, cần chờ" mà cổng đã có mã/ngoại lệ riêng (ví dụ hết hạn mức trang, máy OCR/Local chưa sẵn, bị hủy) → `CHO` kèm mã lý do và câu tiếng Việt trung tính. Lỗi khác → `LOI` kèm mã; giữ **loại ngoại lệ gốc** trong kết quả để bên gọi phân biệt, không đưa nội dung văn bản/tệp vào lý do. Đọc mã cổng để lấy đúng ngoại lệ hiện có; không phát minh trạng thái mới cho cổng.
4. `dang_ky_engine_cong(danh_ba, *, cong_ocr=None, cong_ai=None)`: chỉ đăng ký engine có cổng được truyền vào.
5. Engine **không** đọc/ghi bảng của module, không thêm thư viện/kết nối/mô hình (ghi rõ docstring).

**Test (thuần, dùng lớp giả cùng chữ ký, không ABBYY/mạng/PG):**
- `BoTestHopDongEngine`/`kiem_tra_mau_engine` chạy cho cả hai engine;
- XONG/CHO/LOI cho mỗi engine; kết quả qua engine giống gọi cổng trực tiếp (cùng bytes / cùng trường KetQuaAI);
- bằng chứng ổn định (cùng vào → cùng hash);
- AI: cổng giả ghi lại lời gọi → engine gọi `goi` đúng một lần, không đổi `loai_viec`;
- đăng ký: chỉ engine có cổng; đăng ký trùng bị từ chối như danh bạ hiện có.

**Báo cáo (≤ ¼ trang)**, "Cần lead", thông điệp commit `[XS-3b] …`.
