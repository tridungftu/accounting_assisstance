# Kiểm kê nguồn đầu tư tài chính M9/C4d

**19/10/2026. HISTORICAL/INCOMPLETE: chỉ kiểm kê candidate lịch sử tại máy; chưa xác nhận loại đầu tư thực có/đang hoạt động hoặc policy.** Không có yêu cầu triển khai nhánh đầu tư nào từ bảng này.

## 1. Nguồn, mốc và giới hạn

Nguồn `LOCAL_ACCOUNTING_SNAPSHOT_I01`: một CSDL kế toán đã nạp tại máy, 54,562,816 byte, 50 bảng; đọc bằng SQLite URI `mode=ro`, `query_only=ON`, transaction chỉ đọc. SHA256 trước/sau giống nhau: `487a2dc6be14504bdc2ee19c87006dbff88f9aef6fa4049a4c328fb9307cf3f2`. Đường dẫn và metadata chi tiết chỉ giữ private dưới `var/codex-dieu-phoi`; không đưa row, tên đối tác, STK, số tiền hoặc credentials vào tài liệu.

Đã quét 5,908 chứng từ JOURNAL/BANK/OPEN_ITEM đã có trong kho và danh mục ACCOUNT; lỗi JSON 0. Phạm vi ngày sổ lịch sử: 2024-09-01 đến 2026-06-30. Artifact đã nhận trong khoảng 2026-10-12T14:34:38.150951Z đến 2026-10-12T14:35:28.955992Z. Đây là mốc kho đã nạp, không phải ngày gốc của hồ sơ đầu tư hoặc xác nhận số dư hiện tại.

Snapshot không được coi sạch cutoff 30/06/2026; không chạy học/chấm/backtest. Không quét toàn máy, không đọc file hợp đồng/chứng từ nguồn, config nhạy cảm/.env, chạy ứng dụng/WSL/model/network hoặc import/test sản phẩm.

Lượt này dùng CSDL hiện có với transaction chỉ đọc; **chưa chứng minh đây là offline frozen copy hoặc tình trạng WAL/shm**. Hash nêu trên chỉ xác minh file DB chính, không chứng minh cả snapshot/sidecar bất biến. Không chạy checkpoint, thao tác file sidecar hay truy vấn thêm sau kiểm kê. Lần kiểm bổ sung cần frozen offline copy có hash và `immutable=1`; các con số dưới đây chỉ phục vụ chọn candidate cần đối chiếu, không phải bằng chứng current register đầy đủ.

## 2. Aggregate loại × số chứng từ × nguồn × đủ/thiếu

| Loại candidate cố định | Mã TK danh mục gợi ý | Chứng từ duy nhất | Sổ Junsky đã nạp | Sao kê đã nạp | Ảnh công nợ đã nạp | Có mô tả local tường minh | Chỉ context tên TK | Chỉ prefix TK | Đủ/thiếu |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Tiền gửi kỳ hạn — candidate | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | Chỉ đủ làm inventory candidate; thiếu register/hồ sơ gốc/trạng thái hiện tại và xác nhận loại/policy |
| Góp vốn — candidate | 1 | 8 | 0 | 0 | 8 | 3 | 5 | 0 | Chỉ đủ làm inventory candidate; thiếu register/hồ sơ gốc/trạng thái hiện tại và xác nhận loại/policy |
| Đầu tư khác — candidate | 1 | 23 | 17 | 0 | 6 | 20 | 3 | 0 | Chỉ đủ làm inventory candidate; thiếu register/hồ sơ gốc/trạng thái hiện tại và xác nhận loại/policy |
| Candidate chưa đủ căn cứ | 1 | 32 | 26 | 0 | 6 | 0 | 0 | 32 | Chỉ đủ làm inventory candidate; thiếu register/hồ sơ gốc/trạng thái hiện tại và xác nhận loại/policy |

Một chứng từ có thể được xếp nhiều nhóm nếu nội dung có nhiều dấu chỉ; không cộng các hàng thành tổng số sự kiện đầu tư. Đếm record chứng từ đã nạp theo ID bất biến, không phải số hợp đồng/khoản đầu tư, số lượng khoản còn hiệu lực hoặc số dư. Riêng `OPEN_ITEM` là item trong ảnh công nợ đã nạp, **không phải một phát sinh/voucher đầu tư mới**; 1/8/6 item ở ba nhóm không được diễn giải thành 1/8/6 khoản đầu tư.

Cách nhận diện chỉ là bộ lọc candidate: nhóm mã tài khoản liên quan trong sổ/catalog và cụm từ kỹ thuật cố định về tiền gửi kỳ hạn/góp vốn/đầu tư tài chính. Prefix một mình không chứng minh loại thực có. Context tên tài khoản khác căn cứ hồ sơ gốc. Mô tả tường minh được kiểm cục bộ trong process nhưng không trích nội dung ra báo cáo; chưa kiểm rằng mô tả đó đúng/đủ về pháp lý hoặc còn hiệu lực.

Có 0 chứng từ sao kê được nhận diện có lãi tiền gửi nhưng không đủ dấu chỉ kỳ hạn theo bộ lọc; không tự xếp chúng thành tiền gửi kỳ hạn. Lãi đã ở M1 phải nối cùng sự kiện nếu sau này có hồ sơ, không tạo lãi lần hai.

## 3. Phần có thể chuẩn bị và phần còn thiếu

- Có thể dùng số lượng/source aggregate trên để chọn hồ sơ cần đối chiếu local tiếp theo; chưa tạo register/master đầu tư từ prefix hoặc mô tả sổ.
- Với tiền gửi kỳ hạn cần hồ sơ khoản gửi, ngày gửi/đáo hạn, currency/gốc, điều khoản lãi/nguồn báo có và trạng thái; với góp vốn cần hồ sơ/quyết định, đối tượng/mapping, ngày/giá trị/currency và loại quyền/nghĩa vụ. Đây là danh mục dữ liệu cần kiểm, không phải policy mới.
- Nhóm đầu tư khác chỉ giữ candidate, không mặc định mở chứng khoán, phái sinh, định giá hoặc dashboard treasury. Tập rỗng/không tìm thấy từ khóa trong phạm vi này không chứng minh toàn doanh nghiệp không có loại đó.
- CFO còn phải xác nhận loại thực có và mẫu/hồ sơ trước code từng nhánh C4d theo gói M9 §5.3/7/8. Chính sách tài khoản, phân loại kỳ hạn, actual rate/FX/rounding/định giá hoặc ghi nhận chưa được suy từ sổ.
- Chưa có bằng chứng #9 có register đầu tư; giữ khả năng tái sử dụng nguồn vay hiện có, không suy phần đầu tư đã nằm trong #9 hoặc đã hoàn thiện.

## 4. Bằng chứng và trạng thái

Private script/metadata được giữ tại `var/codex-dieu-phoi/investment-inventory-20261019`; SHA256 metadata `f56320973bcac57b057a9cfb32e140994e6939d9297130ef6d121e4d8edfccbc`. Python có no-delete guard và không ghi bytecode; chỉ tạo output inventory tại workspace, không sửa/xóa/chuyển file hoặc DB nguồn.

Trạng thái: **kiểm kê local lịch sử đã thực hiện, HISTORICAL/INCOMPLETE; loại thực có/current register/policy và sample production chưa xác nhận**. Không có claim bridge đầu tư, số dư, nghiệp vụ đầu tư hoặc M9 đã nghiệm thu.
