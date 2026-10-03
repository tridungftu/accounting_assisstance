# Dữ liệu và quyết định cần chốt

Ngày 17/09/2026 · Phục vụ kế hoạch **6 module** và bộ prompt Codex.

## 1. Trạng thái thực tế

Đã đọc `KE-HOACH-PHAN-MEM-KHO-TRI-THUC.md` bản 1.2. Chưa thấy các script, dữ liệu, workbook hay tài liệu dẫn chiếu trong thư mục dự án tại thời điểm kiểm tra. Danh sách dưới đây là **yêu cầu chuẩn bị**, không phải xác nhận dữ liệu đã có.

Không cần thu thập đủ toàn bộ lịch sử để bắt đầu. Trước hết cần mẫu đại diện và định nghĩa nghiệp vụ để chốt hợp đồng; sau đó mới nạp khối lượng lớn và đo backtest.

## 2. Bộ tối thiểu để bắt đầu M1

| Cần có | Nội dung | Người cung cấp | Nếu chưa có |
|---|---|---|---|
| Script hiện có | `15_doc_pdf_2nam.py`, `17_doi_chieu_2nam.py`, `doc_hd.py`, `kho_tri_thuc.py`, `14_xuat_junsky.py`; script bảng kê/Base và dependency nếu có | IT/người khảo sát | Chưa xác minh tái sử dụng; chỉ dựng interface/fixture, ước lượng lại phần đọc nguồn |
| Sao kê mẫu | Mỗi layout ít nhất một file; mẫu qua trang, dòng dài, hai giao dịch cùng ngày/tiền, tổng đầu-cuối | Kế toán | Không nghiệm thu parser PDF thực |
| Hóa đơn | XML đại diện; bảng kê Excel tương ứng; mẫu không mã, điều chỉnh/thay thế nếu có | Kế toán | Không tự đoán schema/trạng thái |
| Base | Chỉ mục Excel, thư mục JSON, mẫu có nội dung giải mã, dự án/chi phí | Kế toán/IT | Chỉ dựng contract, chưa kiểm tra độ đầy đủ |
| Bộ xuất Junsky | Năm nhóm ở mục 3, có kỳ/as-of và tổng để đối chiếu | Kế toán | Không mở phiên vận hành |
| Bằng chứng ghi sổ | Sổ 112/NKC hoặc danh sách chứng từ có ID dòng, trường hạch toán | Kế toán/nhà cung cấp | Giới hạn liên kết lịch sử và xác minh; không tự học từ số dư |
| Mẫu import | File `CB_tmpEntry1/2`, mô tả cột, file đã nhập được và lỗi mẫu | Kế toán/nhà cung cấp | Chưa bật xuất vận hành M4 |

Mẫu cho Codex đọc nên là dữ liệu giả lập hoặc bản đã ẩn thông tin theo quy định nội bộ, giữ được cấu trúc/kiểu/quan hệ/tổng cần kiểm thử. File thực được lưu và xử lý ở môi trường nội bộ được phép; không đưa vào prompt, web hoặc dịch vụ ngoài.

## 3. Hợp đồng cho gói xuất trước mỗi phiên

Đây là **trường khái niệm cần có** để ánh xạ, không phải tên cột Junsky đã được xác minh. P0/M1 lập bảng ánh xạ từ mẫu thật và ghi rõ trường thiếu.

| Nhóm file trong bản 1.2 | Trường/ý nghĩa tối thiểu | Kiểm tra |
|---|---|---|
| 1. Công nợ 131/331 theo hóa đơn | Pháp nhân, as-of, TK chi tiết, mã đối tượng, định danh HĐ đủ phân biệt, ngày HĐ, tiền tệ, số còn mở; phát sinh/đã thanh toán nếu nguồn có | Tổng theo TK/đối tượng; số dư Nợ/Có; phân biệt tạm ứng/không có HĐ; phạm vi file đủ |
| 2. Danh mục đối tượng | Mã nội bộ, tên, MST, số tài khoản/ngân hàng nếu có, trạng thái; ngày hiệu lực nếu nguồn cung cấp | Mã trùng, MST sai kiểu, định danh mâu thuẫn; báo phần đổi so phiên trước |
| 3. Hệ thống tài khoản | Mã TK, tên, cấp/cha, trạng thái, hiệu lực; bảng cũ–mới nếu đổi | Không xuất TK hết hiệu lực; mã giữ số 0 đầu; mốc thay đổi được duyệt |
| 4. Khoản mục và dự án | Mã/tên khoản mục phí, mã/tên dự án/đối tượng chịu chi phí, trạng thái/hiệu lực | Mapping nhóm nghiệp vụ sang danh mục chính thức; không tự đặt mã thiếu |
| 5. Kỳ khóa | Pháp nhân, ngày bắt đầu/kết thúc kỳ, trạng thái khóa, phạm vi nếu có | Chặn đúng ngày/kỳ khi đề xuất, duyệt, xuất |

Năm nhóm có thể tương ứng nhiều sheet/file vật lý theo khả năng Junsky. Manifest cần ánh xạ rõ; không giả định số lượng file vật lý luôn là năm.

**Bổ sung đề xuất để xác minh:** sổ 112/NKC/danh sách bút toán trong khoảng đối soát, bao gồm ID chứng từ/dòng, ngày ghi sổ, số/loại chứng từ, TK Nợ/Có, số tiền, đối tượng, HĐ, dự án/khoản mục nếu có, trạng thái đảo/hủy và tham chiếu batch/giao dịch nếu có. Không nhất thiết Junsky trả kết quả import trực tiếp, nhưng cần chứng cứ đủ để biết trường nào đúng.

### Metadata và nguyên tắc thời điểm

- Ghi pháp nhân, hệ nguồn, kỳ báo cáo, `as_of`, `exported_at`, phạm vi bao phủ và người xuất nếu có; lưu hash file, số dòng và tổng kiểm soát.
- Phân biệt `as_of` (số liệu đến thời điểm nào), `exported_at` (lúc xuất), `known_at` (lúc thông tin thực sự có thể biết), ngày nghiệp vụ và ngày nhập máy. Không thay lẫn chúng.
- Hash đổi không bảo đảm mới, hash giống không bảo đảm cũ. Kiểm tra nội dung/metadata/phạm vi; bản không đổi cần lý do và bằng chứng lần xuất lại theo quy trình đã duyệt.
- Các file một gói phải cùng pháp nhân và phạm vi thời điểm tương thích. Danh mục ít thay đổi vẫn cần phiên bản được xác nhận dùng tại phiên.
- `as_of` lớn hơn ngày sao kê không có nghĩa giao dịch chưa ghi sổ. Phải kiểm tra giao dịch đã tồn tại trước khi phân bổ/xuất.
- Với lịch sử không có bằng chứng `known_at`, ghi giả định và giới hạn backtest; không tạo thời điểm giả rồi gọi là point-in-time đã chứng minh.

Nếu không có công nợ theo HĐ, phương án xuống mức đối tượng cần Anh duyệt lại: giảm độ chính xác phân bổ và thay tiêu chí nghiệm thu. Codex không tự chuyển cấp hoặc suy ra HĐ từ tổng công nợ đối tượng.

## 4. Dữ liệu bổ sung cho M2–M6

| Mục đích | Cần bổ sung | Trước khi |
|---|---|---|
| Khởi tạo tri thức | Từ điển 431 từ khóa; sheet khóa cứng, chờ duyệt, nhật ký; định nghĩa chính xác 3 chỉ số bằng chứng | M2 tích hợp dữ liệu thực |
| Chính sách/mẫu | 10–15 mẫu sao kê do kế toán trưởng duyệt; điều kiện áp dụng, trường bắt buộc, ngoại lệ, ngày hiệu lực | M3 chạy nghiệp vụ thật |
| Khoản mục/dự án | Bộ 28 mã và ánh xạ nhóm G; danh mục dự án/đối tượng chịu chi phí | M2/M3 |
| Mốc đổi TK | Sổ 2026 và bảng cũ–mới; ngày chuyển giai đoạn dự án, chính sách vốn hóa được khai báo | M2/M5/M6 |
| Lịch sử kiểm chứng | 12 tháng theo kế hoạch gốc: nguồn, sổ, snapshot neo và bằng chứng thời điểm có sẵn | M6 backtest thực |
| Nhãn ban đầu | Kho dữ liệu cũ và nhật ký; liên kết, người kiểm, bằng chứng đủ điều kiện | M5; nạp lại qua kiểm tra, không copy bộ đếm |
| Quyết định sửa | Định nghĩa 7 mã lý do và ai được duyệt/sửa/thay thế | M4/M5 |
| Báo cáo kỳ | Định nghĩa 6 phần báo cáo đã thiết kế ở bước Base | M6 báo cáo chính thức |
| Tập đánh giá | Tập vàng 200–300 chứng từ có người xác minh; holdout và mẫu kiểm tra mù riêng | G0/G1 |

“9 loại dữ liệu D.1”, tài liệu “Phản biện vòng 2” và một số đầu ra khảo sát được bản 1.2 dẫn chiếu nhưng chưa có trong thư mục. Danh sách ở đây là bản yêu cầu triển khai đề xuất, không khẳng định đã khôi phục nguyên văn các tài liệu đó.

## 5. Những quyết định cần Anh và kế toán trưởng chốt

Không cần quyết định mọi thứ trước M1; chốt đúng trước phần phụ thuộc để không làm lại.

| ID | Quyết định | Đề xuất để xem xét | Người chốt / hạn |
|---|---|---|---|
| Q1 | Kiến trúc 6 module và phạm vi pilot | Python + SQLite + Excel, runtime offline; không UI/API/AI | Anh / trước coding |
| Q2 | Cấu hình | TOML + tomllib để giữ danh sách dependency; hoặc giữ YAML và duyệt PyYAML | Anh/IT / M1 |
| Q3 | Tiền tệ và quy tắc dấu | Chốt VND-only hay có ngoại tệ; quy tắc thu/chi, Nợ/Có, hoàn/đảo/tạm ứng | Kế toán trưởng / M1–M3 |
| Q4 | Mức công nợ | Ưu tiên theo HĐ; xuống đối tượng chỉ sau đánh giá tác động và phê duyệt | Anh/kế toán trưởng / M1–M3 |
| Q5 | Bằng chứng ghi sổ | Chấp nhận đề xuất D01/D03: thêm sổ/chứng từ; chỉ trường xác minh đủ mới học | Anh/kế toán trưởng / M5 |
| Q6 | Chính sách và thời điểm | Cung cấp mẫu/TK/hiệu lực/mapping; không dùng giá trị ngưỡng trong tài liệu làm quy định mặc định | Kế toán trưởng / M2–M3 |
| Q7 | Nhịp phiên và ghi tay Junsky | Phiên theo đợt sao kê; cửa sổ hạn chế ghi tay hoặc kiểm tra lại dữ liệu trước chốt nếu có thay đổi | Kế toán trưởng / M3–M4 |
| Q8 | Người kiểm tra mù E5 | Chỉ định người, thời gian, cách che đề xuất và xác nhận đáp án | Anh / trước G1 |
| Q9 | Ngưỡng qua cổng | Độ đúng toàn bộ/từng trường, phân bổ, phủ và lỗi theo tiền; chốt sau khi xem Baseline | Anh/kế toán trưởng / G0–G1 |
| Q10 | Khóa tháng | Đối soát sau nhập; không batch chờ/mục chưa xác minh/chênh thuộc kỳ; quy trình xử lý ngoại lệ rõ | Kế toán trưởng / M5–M6 |

Q5/Q10 khác suy luận đơn giản trong bản 1.2 nên phải ghi thành quyết định rõ. Giữ bằng chứng chưa đủ ở trạng thái chờ không ngăn coding lõi, nhưng chặn xác minh/học hoặc khóa kỳ liên quan.

### Các câu cần lấy từ nhà cung cấp Junsky

1. `EntryID`: phạm vi duy nhất, ai sinh, có thể tái dùng khi sửa/import lại không, cách phát hiện import trùng?
2. `DebtID`: liên kết đến đối tượng/HĐ/chứng từ nào, có bắt buộc không, nguồn lấy ID và quy tắc thanh toán một phần/nhiều HĐ?
3. `CB_tmpEntry2`: bắt buộc trong trường hợp nào, quan hệ với Entry1, cột/kiểu/độ dài, thứ tự và kiểm tra import?

Cần file mẫu thành công và kết quả lỗi thực; câu trả lời mô tả không thay hoàn toàn kiểm thử nhập. Yêu cầu cung cấp thông tin không có nghĩa Codex được tự gửi thư hoặc thao tác hệ thống của nhà cung cấp.

## 6. Phiếu nghiệm thu sáu module

| Module | Code + fixture | Mẫu thực | Kế toán nghiệm thu | Cho vận hành | Bằng chứng cần lưu |
|---|---|---|---|---|---|
| M1 | Chưa đánh giá | Chưa có | Chưa | Chưa | Báo cáo nạp, tổng, chống trùng, backup/restore |
| M2 | Chưa đánh giá | Chưa có | Chưa | Chưa | Phiên bản tri thức, mẫu LINK_A/B được kiểm |
| M3 | Chưa đánh giá | Chưa có | Chưa | Chưa | Đề xuất có chứng cứ, test giữ chỗ/phân bổ |
| M4 | Chưa đánh giá | Chưa có | Chưa | Chưa | Round-trip Excel, mapping Junsky và import mẫu, recovery |
| M5 | Chưa đánh giá | Chưa có | Chưa | Chưa | Chứng từ xác minh, nhãn và thống kê tái lập |
| M6 | Chưa đánh giá | Chưa có | Chưa | Chưa | A/B, kiểm tra mù, hai phiên, UAT, restore |

Đây là trạng thái tại lúc lập kế hoạch, không phải kết quả đánh giá phần mềm hiện hữu. Khi bắt đầu coding, cập nhật bảng tiến độ chính ở `docs/TIEN-DO.md`, gắn đường dẫn chứng cứ và người xác nhận.
