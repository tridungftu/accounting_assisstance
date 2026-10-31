**Biên bản review chéo OCR-3 — Kết luận: Cần sửa.**

Nhánh `lat/g3-ocr-3`, HEAD `45862fb`; commit triển khai `27ae061`. Đối chiếu với `hop-nhat-20261023`, đề OCR-3 và contract G1.

| Nội dung kiểm | Kết quả |
|---|---|
| Đúng whitelist ≤3 tệp | **Đạt:** chỉ thêm `src/kho_tri_thuc/engines/e_ocr/bang.py` và `tests/test_g3_ocr_3.py`. |
| Bọc mã hiện có | **Đạt:** gọi `extract_docx`, `word_layout(embedded_pages=[])`, không viết lại parser — `bang.py:126–127`. |
| Giữ ô rỗng/gộp, hàng/cột/vị trí | **Chưa đạt:** hai tình huống mất dữ liệu bên dưới. |
| Không suy bảng từ văn bản | **Đạt:** chỉ chuyển block `table`; có test tương ứng — `bang.py:141–143`, `test_g3_ocr_3.py:139`. |
| Chuẩn và an toàn | Tên payload theo contract; không thêm SQL, quyền, log/audit, thao tác xóa hay dịch vụ ngoài. Role/RLS/DEFINER/`search_path` và test login PostgreSQL **không áp dụng** cho diff này. |

Trong bảng sau, `bang.py` là tệp triển khai nêu trên.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Nội dung chưa đọc bị biến thành ô rỗng.** DOCX có ô chứa `<w:sdt><w:sdtContent>…DEMO 123.456…</w:sdtContent></w:sdt>`: `extract_docx` đọc được nội dung nhưng layout không có unit; adapter vẫn trả `gia_tri=""`, `ma_vung_nguon=[]`. Vi phạm `CONTRACT-DU-LIEU.md:2094`: “vùng chưa đọc không thành rỗng”. | **Chặn** | `bang.py:161–166` |
| **Mất cột cuối khi hàng có `gridAfter`.** DOCX có `tblGrid` gồm 3 cột, hàng chứa 2 ô và `gridAfter=1`: adapter trả danh sách chỉ **2 cột**. Vi phạm yêu cầu OCR-3 giữ hàng/cột/vị trí. | **Chặn** | `bang.py:144–148`, `bang.py:172–173` |

**Kiểm chứng:** Lead báo **19/19**. Reviewer không chạy lại gate; đã tái hiện hai ca DEMO hoàn toàn trong RAM bằng runtime OCR, bật `-B` và guard chặn ghi/xóa, kết nối mạng. Cả hai payload sai vẫn **qua validator contract**. Test hiện có chưa bao phủ Content Control trong ô và `gridAfter`. Không sửa tệp, không đọc kho thật, bí mật hay `*.local.json`.

**Hỏi Claude:** Tại hai vị trí trên, lead xác nhận cách xử lý đầu vào khi parser nguồn trả thiếu nội dung/cột. Nguyên nhân nằm ở giới hạn parser có sẵn; điểm chặn của lát là adapter mới vẫn trả thành công kết quả thiếu. Cần lead quyết định trước khi giao sửa, giữ nguyên ràng buộc nguồn ngoài repo chỉ đọc.