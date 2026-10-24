# CRM — nguồn thuật toán DOCX/PDF để đối chiếu

Trạng thái: `FILTERED_TECHNICAL_REFERENCE_ONLY / NOT_RUN`; chưa cấp quyền cho coder đọc hay triển khai.

- Năm file giữ nguyên byte nguồn đã audit; `manifest.json` ghi đường dẫn tương đối, SHA256 và số byte.
- Chỉ tham khảo thuật toán bytes/run-map/replacement; không mang Request/Base context, API, auth, approval hay dữ liệu sang CRM.
- CRM tiếp tục dùng quyền, version, approved template bytes, mapping và output registry hiện hành.
- Adapter `${...}` → `{{...}}` phải xử lý cả regex và precheck, bám TẤT CẢ G1 occurrences đã được xác định; không sửa byte mẫu đã duyệt.
- Các channel OOXML engine chưa duyệt đủ phải có disposition rõ; render được bytes không chứng minh đủ occurrences hoặc fidelity.
- Không mặc nhiên bật condition, table-loop, signer hoặc QR; không coi token signer là bằng chứng ký/duyệt.
- Formatter không tạo chính sách precision, currency, FX, nghĩa vụ hoặc thanh toán cho CRM/M1.
- `docgen/requirements.txt` là tài liệu dependency nguyên bản, không phải lệnh cài hoặc kích hoạt FastAPI/Request shell.
- PDF còn chờ xác nhận LibreOffice/fonts/layout và retained-owned process/temp adapter; không gọi nguyên cleanup của nguồn dưới no-delete guard.
- Chưa import, render, chạy Office/process, kiểm PDF, cài dependency hay nghiệm thu G2/G3.
- Không có app, config, .env, DB, mẫu thật, credentials hoặc customer data trong gói này.