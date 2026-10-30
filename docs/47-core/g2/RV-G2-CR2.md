**BIÊN BẢN REVIEW CHÉO G2-CR2 — Kết luận: Đạt**

Nhánh `lat/g2-cr2`, commit `5e87a6b`; nền trực tiếp `lat/g2-cr1` (`f855fea`). Review chỉ đọc theo `MAU-REVIEW-CODEX.md`.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| Không phát hiện lỗi cần sửa trong diff G2-CR2. | — | — |

1. **Phạm vi — Đạt.** So với CR1, chỉ thêm đúng 3 tệp whitelist: `bao_gia.schema.json`, `bao_gia.demo.json`, `tests/test_g2_cr2.py`. Sáu tệp trong diff từ nhánh hợp nhất gồm cả ba tệp kế thừa CR1; chúng không bị CR2 sửa.

2. **Chuẩn và đặc tả — Đạt.** Trường nghiệp vụ dùng tiếng Việt không dấu; kế thừa vỏ chung, ghim phiên bản/hash dự án, tách phí khỏi lịch giá bán. Các điểm “chờ Anh” được giữ nguyên, không tự chốt catalog hoặc kích hoạt contract. Căn cứ: `bao_gia.schema.json:6`, `:8`, `:28`, `:37`; `tests/test_g2_cr2.py:431`.

3. **Tiền và VAT — Đạt.** Hàm kiểm dùng `Decimal`, phân bổ và làm tròn trước khi dồn VAT; chọn đích theo `lan`, ưu tiên không cọc phía sau rồi phía trước. Có kiểm tổng %, tổng tiền/VAT và VAT cọc bằng 0. DEMO có hai cọc liền nhau và cọc cuối. Căn cứ: `tests/test_g2_cr2.py:27`, `:215`, `:244`; `bao_gia.demo.json:34`.

4. **An toàn và dùng lại — Đạt.** Diff không có SQL, DROP, thao tác xóa tệp, truy cập kho thật, ghi DSN/bí mật hay gọi dịch vụ ngoài. Role/RLS/DEFINER/`search_path` và test dưới login thật **không áp dụng** cho lát contract/test thuần này. Dùng lại kiểu chung, nhóm CR1, helper G2-17 và registry hiện có.

5. **Chất lượng test — Đạt qua đọc mã.** Có kiểm meta-schema, `$ref` offline và ca âm: sai tổng %, toàn cọc, phí chen vào lịch, sai tiền tệ/thang tiền; đặc biệt có ca dồn VAT sai đích dù các tổng vẫn khớp. Căn cứ: `tests/test_g2_cr2.py:140`, `:169`, `:228`, `:259`, `:266`, `:290`.

**Bằng chứng chạy:** Lead cung cấp CR1 **17/17**, CR2 **23/23** với `jsonschema`. Reviewer **NOT_RUN** vì không có Python trên PATH; chưa độc lập xác nhận kết quả chạy hoặc regression toàn bộ so với nền. `git diff --check` không báo lỗi.

**Hỏi Claude:** Không có.