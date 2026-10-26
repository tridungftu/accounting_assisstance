# XS-3d · Bọc bộ đọc hóa đơn XML/ZIP thành engine E-HOADON (CD-017, CD-019)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM. Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ: dừng, ghi "Cần lead". Không có `python` thì ghi NOT_RUN; lead chạy test.
- Test chạy được dưới guard giữ tệp `CODEX_NO_DELETE_FILES`; chỉ dùng mẫu DEMO trong `tests/fixtures` (ví dụ `m2_invoice_xml\`, `m2_ban_ra.xml`) hoặc XML/ZIP giả tự sinh trong test.

**Căn cứ:** TL 53 `D:\Claude\Phan mem ho tro ke toan\53-kien-truc-xuong-song-engine-module.md` (§8 dùng chung); `docs\46-chuyen-doi-dieu-phoi\KK-XUONG-SONG.md` §2 dòng XS-3d, §4 (E-HOADON).

**Đã có (chỉ import, KHÔNG sửa):**
- `ha_tang/engine.py` (`Engine`, `KhaiBaoEngine`, `KetQuaXuLy`, XONG/CHO/LOI, `hash_du_lieu`);
- `ha_tang/danh_ba_engine.py` (`DanhBaEngine.dang_ky`);
- `nguon/hoa_don_xml.py`: `doc_hoa_don_xml(raw, context, artifact_name=...)` → `InvoiceReadResult`; `doc_goi_hoa_don_zip(raw_zip, contexts, archive_name=...)` → `InvoiceZipReadResult`;
- bộ test mẫu `tests/test_xs3_engine.py` (`kiem_tra_mau_engine`, `BoTestHopDongEngine`).

**Tệp (2):** `ha_tang/engine_hoa_don.py` mới; `tests/test_xs3_hoa_don.py` mới.
**Không sửa** `danh_ba_engine.py`, `hoa_don_xml.py`, `engine.py` (lát XS-3b song song cũng đăng ký engine → mỗi lát có hàm đăng ký riêng).

**Việc:**
1. `EngineHoaDon` (mã `E-HOADON`, phiên bản `v1`): vào = bytes XML hoặc ZIP + ngữ cảnh đọc hiện có (`InvoiceReadContext`/tuple contexts) + tên tệp; ra = **nguyên kết quả** của bộ đọc hiện có (hóa đơn, coverage, lỗi, locator, hash) ở dạng dữ liệu thuần có thể băm ổn định. Chỉ nhánh **đọc**; không làm nhánh tải hóa đơn (M2-00), không gọi cổng thuế/mạng.
2. Ánh xạ trạng thái: đọc được → `XONG` (kể cả khi kết quả có lỗi nghiệp vụ dòng mà bộ đọc đã trả có cấu trúc — giữ nguyên lỗi đó trong kết quả, không tự sửa/suy số). Thiếu ngữ cảnh bắt buộc mà bộ đọc báo rõ → `CHO` kèm mã lý do. Tệp không đọc được/ngoại lệ → `LOI` kèm mã, giữ loại ngoại lệ gốc, không đưa nội dung hóa đơn vào lý do.
3. **Không** đổi thuật toán, ngưỡng, làm tròn, tiền của bộ đọc; cùng vào → cùng kết quả như gọi thẳng `doc_hoa_don_xml`/`doc_goi_hoa_don_zip`.
4. `dang_ky_engine_hoa_don(danh_ba)`.
5. Engine **không** đọc/ghi bảng M2 hay module nào, không thêm thư viện/kết nối (ghi rõ docstring). Đây là bước chuẩn bị cho XS-3e (cắm cùng engine vào M2 rồi M3) — chưa nối vào M2/M3 ở lát này.

**Test (thuần):**
- `BoTestHopDongEngine`/`kiem_tra_mau_engine` chạy cho engine;
- XML hợp lệ, ZIP nhiều tệp, XML hỏng → XONG/LOI; ca CHO nếu bộ đọc có tình huống thiếu ngữ cảnh rõ ràng (không có thì ghi lý do trong báo cáo);
- kết quả qua engine **bằng** gọi thẳng bộ đọc (so từng trường quan trọng: số hóa đơn, tổng tiền, coverage, lỗi, locator);
- bằng chứng ổn định: cùng bytes + ngữ cảnh → cùng hash; đổi 1 byte → hash khác;
- đăng ký trùng bị từ chối như danh bạ hiện có.

**Báo cáo (≤ ¼ trang)**, "Cần lead", thông điệp commit `[XS-3d] …`.
