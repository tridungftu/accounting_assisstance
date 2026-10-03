# Mẫu nhiều dòng — đề xuất trong V1, chưa triển khai

**A12/QĐ-V1b-6:** Anh đã duyệt hướng thiết kế, đưa vào phạm vi V2 cùng trường thuế khi Anh giao V2. V1b chưa triển khai mẫu nhiều dòng; xuất danh sách phần tiền bị chặn để theo dõi. Những xác nhận về căn cứ tách thuế và mapping Entry2 bên dưới vẫn cần hoàn tất trước xuất thực.

Theo QV08/A11, V1 chỉ trình thiết kế. Quy tắc nguồn chứa `1331|6427` hoặc các tổ hợp khác được giữ raw và đánh dấu `requires_multiline_review`, không biến thành mã tài khoản, không tự chia tiền, không có đề xuất FULL và không vượt cổng duyệt bằng sửa Excel.

## Phương án khuyến nghị

Thêm version hợp đồng proposal có `lines[]`, mỗi dòng có `line_id` ổn định trong revision, account, debit_minor, credit_minor, currency, counterparty/project/expense khi cần, tham chiếu hóa đơn và bằng chứng từng giá trị. Giữ header cho giao dịch ngân hàng; tổng Nợ = tổng Có, vế ngân hàng bằng trị tuyệt đối tiền sao kê. Tham chiếu thuế và tiền thuế lấy từ hóa đơn hoặc chứng từ có căn cứ, không mặc định tỷ lệ VAT từ mô tả phí.

POLICY nhiều dòng là mẫu cấu trúc, không chứa sẵn tỷ lệ tách chưa được kế toán duyệt. Thiếu căn cứ tiền thuế/tiền trước thuế hoặc nhiều nguồn lệch nhau thì WAIT. Ngay cả khi mã TK được biết, không gọi hai chuỗi TK là một bút toán đủ điều kiện.

## Ảnh hưởng trong sáu module hiện có

| Nơi thay đổi | Thay đổi dự kiến |
|---|---|
| M1 | Contract V2 cung cấp tiền trước thuế/thuế/tổng và bằng chứng; tiền dùng minor units chính xác, giữ mã text |
| M2 | Payload POLICY có version và các vai trò dòng; quyền duyệt mẫu/hiệu lực riêng; không tự sinh dòng khi nhập Excel |
| M3 | Proposal/decision giữ lines và tổng kiểm soát theo revision; ràng buộc công nợ chỉ gắn dòng đúng nghiệp vụ |
| M4 | Workbook có sheet dòng liên kết header; duyệt trọn chứng từ sau khi kiểm từng dòng; file cũ vẫn theo version cũ |
| M4 — export_items | Giữ export_items là chứng từ ngân hàng/batch, thêm export_item_lines có ID dòng, ordinal, giá trị và hash; header manifest chứa hash tập dòng. Không tách thành các export_items rời khiến hạch toán trùng giao dịch |
| M4 — Entry1/Entry2 | Entry1 một header, đúng 17 cột. Entry2 nhiều dòng chung EntryID; chỉ xuất vế đối ứng hay cả hai vế theo xác nhận của NCC/kế toán ở V6. Chưa tự quyết DebtID/EntryDM hoặc sinh EntryID có thể trùng |
| M5 | Xác minh từng dòng/từng trường, phân biệt đủ/một phần/sai; nhãn học không chỉ dựa tổng tiền khớp |
| M6 | So sánh cấp chứng từ và cấp dòng; backup/restore và recovery tái tạo đúng manifest/file |

## Migration và tương thích

Chỉ thêm migration mới sau schema đang triển khai; không sửa checksum lịch sử. Lưu contract_version trong payload, bảng dòng có khóa ngoại về export_items. Không suy ngược các file cũ thành nhiều dòng từ dấu `|`; cần dữ liệu và quyết định mới. Backfill chỉ những bản một dòng có đủ dữ kiện và bằng chứng; còn lại giữ version cũ. Thực hiện trên bản sao, đối chiếu số chứng từ/tổng/hash trước và sau; chạy lại không nhân đôi.

## Kiểm thử và thông tin phải có trước khi giao thực hiện

- Phí có thuế, không thuế, hóa đơn điều chỉnh âm, khác tiền tệ ngoài phạm vi, lệch làm tròn trong/ngoài dung sai.
- Một chứng từ nhiều dòng: cân tiền, giữ số 0 đầu, ID ổn định; sửa/xóa dòng làm workbook cũ bị chặn; không xuất một phần chứng từ chưa duyệt.
- Nhiều dòng cùng TK vẫn giữ riêng nếu bằng chứng/dimension khác; thứ tự không được dùng thay khóa nghiệp vụ.
- Import một phần, retry, lỗi sau chuẩn bị batch; khôi phục phải giữ quan hệ header–line và không tạo giao dịch trùng.
- Có mẫu hóa đơn/biên lai làm căn cứ tách tiền; kế toán xác nhận mapping dòng và quy tắc làm tròn; NCC xác nhận chế độ Entry2. Quyền triển khai phần này phải được Anh giao riêng; V1 chưa thực hiện.
