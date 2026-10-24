# M4 — Kế hoạch đã được Anh yêu cầu triển khai ngày 20/10/2026

**IMPLEMENTATION_AUTHORIZED_M4_ONLY.** User đã gửi nguyên kế hoạch dưới lệnh “PLEASE IMPLEMENT THIS PLAN”. Lệnh thực hiện này mở lại triển khai M4 và phần dùng chung cần thiết, thay trạng thái dừng code M4 trước đó. Các module khác/M9 giữ dừng; automation báo30phút vẫn PAUSED. Không coi câu cuối “chưa sửa code” trong kế hoạch được trích lại là lệnh dừng mới đối nghịch với yêu cầu triển khai.

## 1. Mục tiêu và trách nhiệm đã chốt

M4 bao gồm đầy đủ chức năng của `D:\Claude\Ho tro review ho so xay dung\review_xaydung`, dùng lại lõi xử lý và giao diện, bổ sung Cổng hồ sơ nội bộ phòng dự án. Bản vẽ/CAD và tài khoản nhà thầu ngoài để sau.

| Việc | Người thực hiện |
|---|---|
| Upload tài liệu, trích và xác nhận tham số HĐ xây dựng | Nhân viên phòng dự án được phân quyền đúng dự án |
| Review và duyệt hồ sơ đợt thanh toán | Anh hoặc sếp Anh; khi kiểm thử dùng actor mô phỏng có quyền duyệt M4 |
| Xác nhận nghiệm thu và ghi nhận công nợ | Kế toán đúng phạm vi |

Phòng dự án chịu trách nhiệm cung cấp đủ căn cứ và xác nhận bộ tham số trước khi nộp đợt. Không cần CFO duyệt tham số M4. Không thay quyền duyệt tham số CRM.

## 2. Điều kiện nộp hồ sơ — kiểm cả backend

- Hợp đồng: có bytes tài liệu nguồn, hash/phiên bản, kết quả trích đúng nguồn và bộ tham số đã được phòng dự án soát/xác nhận; giữ người/thời điểm/căn cứ. Không nhận cờ “đã trích/đã xác nhận” do browser tự khai làm bằng chứng.
- Phụ lục: phân biệt khai không có, có và đã cung cấp đủ, chưa khai/chưa đủ. Giữ nguồn/quan hệ; chỉ PL đã ký và hiệu lực tại ngày liên quan tham gia tính.
- BOQ: gắn đúng HĐ; đọc và map được sheet/cột/hạng mục; giữ BOQ gốc và thay đổi PL. Có một file không đồng nghĩa đã parse/map thành công.
- Đợt thanh toán: có bộ hồ sơ theo checklist, đúng HĐ/đợt/ngày nghiệm thu; tài liệu/currency/số tiền thiếu không biến thành0.
- Luôn cho lưu nháp/upload từng phần. Thiếu mục nào chỉ rõ mục đó và đường bổ sung; chặn Nộp hồ sơ chính thức. Không chuyển thiếu căn cứ sang Anh để Anh tự tìm tài liệu.
- Dùng lại HĐ/PL/BOQ đã có cho đợt sau. Đổi căn cứ ảnh hưởng đợt đang xử lý tạo revision và yêu cầu kiểm/xác nhận lại; không vô hiệu hóa lịch sử hàng loạt.
- Tham số không áp dụng ghi rõ; không dùng số0 hoặc `van_nap` legacy để vượt gate. Tồn tại finding nghiệp vụ không tự chặn nộp cho reviewer; thiếu/mơ hồ căn cứ bắt buộc phải chặn.

## 3. Luồng duyệt và hai nhánh độc lập

Nháp/bổ sung căn cứ → đủ HĐ đã xác nhận/PL/BOQ → Nộp → Review và xử lý phát hiện → Anh/sếp duyệt trên phần mềm.

Đã duyệt nhưng thiếu **PDF hồ sơ đợt được duyệt**: CHO_PDF, cả hai nhánh chưa được chuyển. PDF này khác tài liệu hợp đồng. Duyệt khóa nội dung review; PDF bổ sung gắn đúng lần duyệt. Khi đủ PDF đóng gói bàn giao bất biến. Thay nội dung/PDF sau chuyển phải có bản bổ sung/điều chỉnh, không ghi đè.

Sau đủ điều kiện:

1. Tự chuyển hồ sơ nghiệm thu sang kế toán CHO_XAC_NHAN đúng một lần, không chờ tạo Request. Chỉ kế toán xác nhận giá trị/căn cứ thuế mới ghi nhận công nợ nội bộ; chưa nhập Junsky.
2. Mở nút Tạo nháp Request cho nhân viên. Người bấm là người tạo Request, do server map từ phiên đăng nhập; không nhận người tạo tùy ý từ body. Nhân viên tự kiểm và Gửi tại ứng dụng Request; M4 không gửi/duyệt thay chuỗi đó.

Request lấy số đề nghị thanh toán kỳ này được review xác nhận. Công nợ dùng giá trị nghiệm thu/căn cứ thuế do kế toán xác nhận. Tạm ứng, thu hồi, giữ lại giữ riêng. Không mặc định công nợ = thanh toán, hoặc số chấp nhận = đề nghị - ảnh hưởng review.

Request bị trả lại/từ chối không tự hủy nghiệm thu/công nợ. Hóa đơn và nghiệm thu cùng sự kiện dùng một ghi nhận chung M2/M4, không ghi nợ hai lần theo thứ tự nguồn đến.

## 4. Tái sử dụng đầy đủ, phần làm mới và giao diện

Giữ các nhóm chức năng nguồn: Tổng quan; trích/soát tham số; danh mục HĐ; phụ lục; BOQ; kiểm toàn vẹn Excel K1–K8; review đợt L2 B1–B8; chứng từ L3 C01–C09; ghép hạng mục/chạy lại; nguồn/trích dẫn/lịch sử; OCR; báo cáo, tác vụ nền và cài đặt. Tận dụng phân loại/checklist/tra cứu căn cứ từ công cụ legacy trong luồng phù hợp; không dựng app Streamlit thứ hai.

Giao diện giữ phong cách Bàn kiểm soát: font Be Vietnam Pro, sidebar theo công việc, bảng dữ liệu và chi tiết nguồn. Bổ sung Cổng hồ sơ, checklist thiếu, upload/trích/xác nhận/import, trạng thái riêng Review/PDF/Kế toán/Request và hành động đúng vai. Không đưa thuật ngữ migration/schema/receipt vào luồng người dùng.

Tái sử dụng code; thích nghi lớp lưu trữ/quyền/cấu hình/đường dẫn qua adapter. Không mở server nguồn không đăng nhập trong iframe, không dùng `X-HD:1` thay quyền, không tạo master HĐ song song hoặc cho nhân viên sửa authority thông qua đường legacy.

## 5. Hợp đồng kỹ thuật và điều kiện tích hợp

- Hệ thống dùng K1–K5/master/kho/nhật ký và quyền chung. Master HĐ/PB/tham số đã có; M4 bổ sung scope M4, project/dossier và provenance cần thiết. Không cấp CRM rộng cho phòng dự án để vượt quyền.
- Migration mới nối sau COMMON13→14→15→16; giữ prefix1–16, không khôi phục full-M9. Cổng typed/constraint/RLS và phân loại chứng từ phải nhận diện M4 thật.
- Source owner/app nguồn không sửa; kỹ thuật tham chiếu được lọc riêng, không đọc/chuyển DB, config, keys, file thật, kết quả AI hoặc tài liệu nội bộ.
- Request nguồn `D:\Claude\Phan mem duyet kieu base` có APIv1 tạo/sửa nháp, upload tệp, đọc status. Tái dùng GET nhóm/danh mục, POST nháp, upload và link UI. Không thêm API tự gửi/duyệt.
- Mapping nhóm/trường/tài khoản nguồn phải được cấu hình và kiểm hợp lệ. Chưa có kết nối/quyền/mapping thì báo CHUA_CAU_HINH, không giả là đã nối production.
- Lưu ID Request/phiên bản/digest và trạng thái mỗi nhánh lâu dài. API Request cache chống trùng24h không đủ; M4 cần cross-reference bền. Timeout không rõ kết quả → chờ đối soát, không mù quáng tạo lại sau24h.
- Có ca song song và stale-source thực; kiểm quyền trước trả receipt/file. Mọi file phải được giữ, không xóa/tự cleanup; các thao tác bỏ/hủy giữ lịch sử và bytes.
- Dùng DEMO/actor MO_PHONG_; không CFO_NTD thật, không nhập Junsky, không đổi kho thật SQLite, không tự bật cloud AI hoặc gửi dữ liệu ra ngoài.

## 6. Thứ tự các gói có điểm kết thúc

1. M4-01: tái sử dụng Review, cổng hồ sơ, dữ liệu căn cứ HĐ/PL/BOQ, trích/đọc thực, phòng dự án xác nhận và gate nộp; màn hình phải có thao tác được, không chỉ placeholder.
2. M4-02: review L1–L3, người duyệt có quyền, đóng băng revision và PDF gate; tái dùng engine/báo cáo nguồn, không bịa kết quả.
3. M4-03: nhận nghiệm thu/công nợ chung M2–M4, kế toán xác nhận, cross-source/event không trùng.
4. M4-04: Request nháp/attachments/creator/quyền, đối soát lỗi và cross-reference lâu dài; chưa có endpoint nguồn thật vẫn phải có contract tests và thông báo phần chưa kết nối.
5. M4-05: kiểm độc lập xuyên suốt, UI/nút mở bản DEMO, kiểm nguồn/file/số, quyền, lặp/song song/khởi động lại. Đóng gói không yêu cầu Anh gõ lệnh.

Các gói được phép kết hợp khi dependency rõ, nhưng kiểm độc lập sau actual terminal/freeze và không chạy runtime trên source Claude đang sửa. Không tạo gói nền tảng vô hạn hoặc quay lại M9/Q09.

## 7. Ma trận nghiệm thu bắt buộc

| Mã | Tiêu chí |
|---|---|
| A1 | Thiếu HĐ/chưa trích/chưa dự án xác nhận → không nộp được; lưu nháp vẫn được. |
| A2 | Dự án upload/chạy trích/xác nhận trong quyền, không cần CFO; giả actor/khác project/PN bị chặn cả backend. |
| A3 | Khai PL có/không đầy đủ; BOQ đọc/map đúng HĐ và effective date, không coi file tồn tại là đủ. |
| A4 | Dùng lại HĐ/căn cứ cho đợt sau, không tạo master trùng; thay căn cứ giữ lịch sử và làm lần kiểm liên quan hết hiệu lực. |
| A5 | Đủ căn cứ nộp để review; finding nghiệp vụ chưa xử lý không tự đồng nghĩa hồ sơ thiếu căn cứ. |
| A6 | Duyệt thiếu PDF →0 Request và0 hồ sơ kế toán chuyển; không tự upload bản giả hoặc lấy PDF HĐ làm PDF đợt. |
| A7 | PDF đúng revision → hồ sơ kế toán CHO_XAC_NHAN đúng1 và nút Request mở; chưa tự ghi công nợ. |
| A8 | Hai nhánh độc lập: người tạo/tiền/tệp đúng; kế toán xác nhận tách Request; Request returned không tự đảo AP. |
| A9 | Bấm lặp/concurrent/stale/timeout/restart không trùng, không ghi đè lịch sử, không báo thành công giả. |
| A10 | Người ngoài quyền không xác nhận/duyệt/xem/tải tệp; không lộ raw/tệp pháp nhân hoặc dự án khác. |

Code/self-test/kiểm độc lập/GUI/nghiệm thu từng gói được báo riêng. Bất kỳ lát DEMO hoặc ma trận còn chưa chạy đều không chứng minh toàn M4 hoàn tất.
