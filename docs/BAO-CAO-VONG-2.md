# Báo cáo vòng 2 — V2 đến V6

Các mục dưới đây là báo cáo kỹ thuật. Không mục nào là xác nhận nhập Junsky, duyệt tri thức bởi CFO_NTD hoặc sẵn sàng vận hành. Lát cắt tháng 8 sau mỗi V chỉ là hồi quy kỹ thuật hai chế độ; không dùng ngưỡng chất lượng làm cổng theo A13.

## V9 — Định khoản nhanh (thay V8b)

**Đã làm:** thay luồng phiên/duyệt tri thức bằng Định khoản nhanh: thả sao kê, XML hoặc bảng kê để nhận đề xuất. PENDING được dùng cho đề xuất, nhưng chỉ một bút toán có quyết định **Đồng ý** mới có thể vào file xuất. Nền Junsky, ba workbook tri thức và danh bạ được nạp nền cục bộ; `CFO_NTD` chưa có quyết định nào trong kho chính. Bộ xuất sao kê dùng mẫu Junsky khi có, đúng Entry1 17/Entry2 37; hóa đơn chỉ ra file soát. Import Junsky luôn tắt.

**Kiểm thử:** toàn suite synthetic 178/178 PASS, migration v16, khởi động lại UI và kiểm tra trang đầu là Định khoản. Chấm F2 chạy trong kho sao chép: 105 sao kê đều Đỏ; chưa có hóa đơn T8. Tỷ lệ đúng và chống trùng là không đo được do sổ thiếu mã tham chiếu sao kê. Xem tổng hợp tại [BAO-CAO-V9.md](BAO-CAO-V9.md), chứng cứ máy tại `var/vong-2/V9-giao-viec/`.

**Chưa xác minh:** khóa ghép sao kê↔sổ, hóa đơn T8, BankID/CashflowID và UAT kế toán. **Giả định:** GIẢ ĐỊNH-V9-1, V9-2.

## V2 — Hợp đồng nguồn, thuế và nhiều dòng

**Đã làm:** mở rộng INVOICE với tiền chưa thuế/thuế/tổng, dòng thuế và quan hệ điều chỉnh; hợp nhất XML/bảng kê theo khóa hóa đơn nhưng giữ từng bằng chứng/known_at; mở rộng Base, OPEN_ITEM, JOURNAL và BANK; thêm lines cho proposal/decision/export item và checksum theo dòng. Thiếu căn cứ thuế/cân tiền luôn giữ WAIT.

**Kiểm thử:** unit test hợp nhất hai nguồn, dung sai, mâu thuẫn tiền, định dạng VND, khóa sao kê dự phòng, nhiều dòng cân tiền/chờ thuế, và khóa that. Hồi quy kỹ thuật: [KET-QUA.json](../var/vong-2/V2/KET-QUA.json).

**Lệnh:** `python -m kho_tri_thuc --config cau_hinh.that.toml nap-nguon --nguon ...`; không chạy `.xls` khi thiếu wheel offline.

**Chưa xác minh:** tiền/tỷ lệ thuế thực, Base 2026, trạng thái nguồn và ý nghĩa mã Junsky. **Giả định:** GIẢ ĐỊNH-V2-1, V2-2.

## V3 — Adapter nguồn và kho that

**Đã làm:** adapter `that` cho sao kê `.xlsx`/`.xls`/PDF, XML, bảng kê, Base, danh mục/công nợ/sổ; metadata bắt buộc; source artifact bất biến; chọn danh mục mới nhất theo vai trò, cảnh báo mã ngoài danh mục và không tự bổ sung. `that` có DB riêng, hai cờ Junsky tắt.

**Kiểm thử:** reader `.xlsx`, XML thuế, Base VND, công nợ snapshot, idempotence, thiếu `xlrd`; hồi quy kỹ thuật: [KET-QUA.json](../var/vong-2/V3/KET-QUA.json).

**Lệnh:** `python -m kho_tri_thuc --config cau_hinh.that.toml nap-nguon --nguon sao_ke|hoa_don|bang_ke|base|junsky --duong-dan ... --as-of ... --exported-at ... --known-at-basis ...`.

**Chưa xác minh:** wheel offline `xlrd==2.0.2` không có trong cache; vì vậy chưa đọc sao kê `.xls` thực và không tự viết reader thay thế. Chưa chạy nạp kỳ dài. **Giả định:** GIẢ ĐỊNH-V3-1 đến V3-3.

## V4 — Tri thức Excel của người

**Đã làm:** nhập ba workbook tri thức với evidence file/sheet/row; mọi phiên bản PENDING; workbook người đọc/sửa có JSON kỹ thuật ẩn; nhập ngược chỉ tạo yêu cầu duyệt. Đã đọc từ điển bản 9 sheet, có `0B` và `3B · KHÓA CỨNG`; kho thử that lưu tri thức chờ duyệt, không có event APPROVE.

**Kiểm thử:** import PENDING, export/import nguyên trạng không event, yêu cầu duyệt có audit, sửa cột nghiệp vụ bị chặn; hồi quy kỹ thuật: [KET-QUA.json](../var/vong-2/V4/KET-QUA.json).

**Lệnh:** `python -m kho_tri_thuc --config cau_hinh.that.toml nap-tri-thuc ...`, `xuat-tri-thuc ...`, `nhap-yeu-cau-duyet ...`.

**Chưa xác minh:** không có lệnh duyệt thực; `CFO_NTD` chưa được gọi. **Giả định:** GIẢ ĐỊNH-V4-1.

## V5 — Hiệu năng, workbook duyệt và bộ chấm

**Đã làm:** thêm index lookup tri thức/công nợ; workbook duyệt chỉ giữ shortlist cấu hình và `CONG_NO_KHAC`; kiểm tra lại toàn bộ điều kiện khi chọn công nợ khác; tách không đề xuất khỏi đề xuất sai, thêm phủ theo tiền; bỏ trạng thái posted fixture khỏi logic nghiệp vụ.

**Kiểm thử:** 165/165 test đạt tại thời điểm V5, gồm test mã Excel dạng text, shortlist/công nợ khác và cách chấm NONE; [TESTS.json](../var/vong-2/V5/TESTS.json). Hồi quy kỹ thuật: [KET-QUA.json](../var/vong-2/V5/KET-QUA.json).

**Chưa xác minh:** chưa có danh mục thật đầy đủ và không ghi số đo/so ngưỡng tháng 8 theo A13. **Giả định:** GIẢ ĐỊNH-V5-1.

## V6 — Shadow và đối soát có bằng chứng

**Đã làm:** tạo workbook shadow hai sheet `CB_tmpEntry1`/`CB_tmpEntry2`, kiểm header 17/37 gồm `ErrorText`, recovery từ artifact, đối soát ngược với sổ đã ghi và nhãn chỉ từ trường có evidence. Tệp mang tiêu đề `SHADOW — CHƯA NHẬP JUNSKY`; actor shadow bắt buộc bắt đầu `MO_PHONG_`.

**Kiểm thử:** 166/166 test đạt sau V6, gồm test cấu trúc/recovery/đối soát/nhãn synthetic: [TESTS.json](../var/vong-2/V6/TESTS.json). So cấu trúc header với hai file T8 được chỉ định — đều khớp, chỉ so cấu trúc và không coi là bằng chứng import: [DOI-CHIEU-CAU-TRUC.json](../var/vong-2/V6/DOI-CHIEU-CAU-TRUC.json). Migration v10–v14 đã chạy trên bản sao DB that, integrity đạt: [MIGRATION-CHECK.json](../var/vong-2/V6/MIGRATION-CHECK.json). Hồi quy kỹ thuật: [KET-QUA.json](../var/vong-2/V6/KET-QUA.json).

**Chưa xác minh:** chưa có sao kê `.xls` nạp được, tri thức thực chưa được duyệt, mapping/ý nghĩa EntryID, EntryDM/DebtID, BankID, CashflowID và Base 2026 chưa có. Không có import Junsky. **Giả định:** GIẢ ĐỊNH-V6-1, V6-2.

## V7 — Bộ đọc nguồn thật, cách ly và lệnh vận hành

**Đã làm:** sửa eFAST header song ngữ/số tài khoản/kiểm soát tổng; XML TCT mẫu 1–2, hóa đơn liên quan và khóa chung bảng kê; Base `get.request`/form/custom table; đủ danh mục, công nợ và hai bố cục sổ Junsky. Migration v15 thêm quarantine theo ordinal. Thêm `duyet-tri-thuc`, `xem-cach-ly`, `liet-ke-sao-ke`, `mo-phien-that` và `run-that.ps1`. Không sửa nguồn, không nhập Junsky, không tự duyệt.

**Kiểm thử:** `test_v7.py` dựng tệp synthetic đúng cấu trúc quan sát, gồm fallback `.xls/.xlsx`, mẫu 2, Base cách ly, bảy vai trò Junsky, quyết định workbook chạy thử/thật. Toàn suite 172/172 test đạt; migration v15 đã chạy trên bản sao DB, `integrity_check` và foreign key check đạt: [TESTS.json](../var/vong-2/V7/TESTS.json), [MIGRATION-CHECK.json](../var/vong-2/V7/MIGRATION-CHECK.json). Kiểm tra đọc thật chỉ ghi số đếm/tổng hợp vào [KIEM-TRA-BO-DOC.json](../var/vong-2/V7/KIEM-TRA-BO-DOC.json); [MA-NGOAI-DANH-MUC.json](../var/vong-2/V7/MA-NGOAI-DANH-MUC.json) là danh sách mã/tần suất phục vụ kết xuất lại danh mục.

**Lệnh:** dùng `run-that.ps1` theo [Hướng dẫn vận hành](HUONG-DAN-VAN-HANH.md#6-vận-hành-kho-that-sau-v7). Không dùng `run.ps1` cho kho that.

**Chưa xác minh:** máy chưa có wheel offline `xlrd==2.0.2` và chưa có `.xlsx` cạnh sao kê T8, nên riêng sao kê `.xls` chưa đọc trực tiếp. Mẫu nhiều dòng nguồn vẫn cần cấu trúc `journal_lines` được kế toán xác nhận; thiếu căn cứ thuế giữ WAIT. **Giả định:** GIẢ ĐỊNH-V7-1 đến V7-5.

## V9b — Sửa đề xuất sao kê và chấm lại F

**Phạm vi giao:** thực hiện S1–S12 của V9b: vế tiền, nhãn PENDING, lọc mã chính đơn vị, thứ tự ưu tiên nhận diện, học BR/BP, ghép sao kê↔sổ, hóa đơn tháng 8, xuất theo cấu hình, học tình huống, test synthetic và chạy lại F. Quy tắc ghép duy nhất/chống trùng S7 là quyết định Anh đã duyệt, xem [QUYET-DINH.md](QUYET-DINH.md#v9b--quyết-định-và-giả-định-thực-thi-s1s12).

**Đã làm:** đủ S1–S12, gồm mapping vế tiền theo cấu hình, nhãn PENDING, lọc mã chính đơn vị, bảy bậc nhận diện, học mẫu BR/BP nhiều dòng, chống trùng S7, đọc hóa đơn tháng 8, export theo đơn vị/tháng, học theo tình huống và UI tải file qua token cục bộ. Kho chính F4 đã thay bằng kho sạch schema v18, có backup và rollback cục bộ.

**Kiểm thử:** full suite **198/198 PASS**; migration bản sao v16 → v18 integrity/FK đạt; `.xls` được test độc lập với trạng thái có/không có `xlrd`; UI/API local khởi động và health check đạt. F1–F2 chạy trong kho sao chép: sao kê 105 dòng đều Đỏ, ghép duy nhất 57; hóa đơn mua 39 Đỏ, hóa đơn bán 36 Đỏ. Không có mẫu Xanh để đo mục tiêu 98%; tỷ lệ sao kê đủ bút toán 0,0%, chưa đạt mốc 23%. Số liệu tổng hợp và nguyên nhân xem [BAO-CAO-V9b.md](BAO-CAO-V9b.md).

**Giới hạn giữ nguyên:** không sửa file nguồn; không đưa dữ liệu thật vào tests/fixtures/chat; không dùng AI/dịch vụ ngoài; không nhập Junsky. Cần kế toán xác nhận mapping TK tiền và chứng cứ MST → TK trước khi đo lại F. Các giả định V9b được tham số hóa trong `QUYET-DINH.md`.
