# Review độc lập kế hoạch toàn bộ 33 và tái sử dụng

Ngày: 18/10/2026. Đối tượng: hai bản dự thảo `LO-TRINH-TRIEN-KHAI-TOAN-BO-33.md` và `HOP-DONG-TICH-HOP-VA-TAI-SU-DUNG-33.md`, trước lượt Claude sửa tiếp. Đây là findings để xử lý, không phải quy định nghiệp vụ mới. Code chưa được nghiệm thu từ việc đã lập đủ tên gói.

## Các điểm phải sửa trong đầu bài

1. **Gate đúng phụ thuộc.** Không buộc thiết kế/adapter/bridge DEMO độc lập chờ tất cả A1–A6 V13 hay backtest có clean cutoff. Chỉ thao tác dùng PostgreSQL, dữ liệu thật hoặc Junsky mới cần các gate tương ứng.
2. **Bỏ phụ thuộc vòng C1d/C9a.** Sự kiện bàn giao tạo lịch; M10 tiêu thụ lịch để sinh lô. Hai bước không chờ nhau.
3. **Coverage theo nghiệp vụ.** Nhà ở đa pháp nhân phải có gói và acceptance riêng; PLHN không có nhà ở không loại HDNO toàn hệ thống. M9 cần đối chiếu LC/bảo lãnh/đầu tư tài chính với phạm vi đã chốt và có gói tương ứng, không tick M9 bằng hai gói chỉ vay. Không tự thêm covenant/quản lý hạn mức ngoài đặc tả.
4. **Lịch sử sau xuất.** Trước xuất có thể hoàn tác theo quyền; sau xuất/nạp phải giữ lô cũ và lập điều chỉnh có vết. Không tự chuyển dòng treo thành Vàng cuối tháng nếu chưa có căn cứ.
5. **Zalo đầy đủ chương trình.** Soạn câu hỏi chỉ là một phần; còn transport, nhận/gắn trả lời, dedup, nhắc hạn/escalation và mock test. Kích hoạt gửi thật giữ gate riêng.
6. **Nguồn đúng format.** #6 hiện có reader Word DOC/DOCX, không mặc định thả PDF là khả năng sẵn có. #7/#8 tương thích parser hiện tại. #9 có hai version source; #10 đã có CRUD/duyệt/đảo/tồn/API. Nước thải dùng `SM_tmpSelling1/2`, không nhầm `CB_tmpEntry1/2`. Mask chưa tự chứng minh đủ bảy nhóm. Dùng hai hồ sơ audit mới thay nhãn chờ audit đã lỗi thời.
7. **Quyết định mới theo chủ đề.** Điều kiện cloud theo TL35 và cổng AI chung; không lấy TL34 cũ thêm lệnh cấm vĩnh viễn riêng bảng lương. Gửi dữ liệu thật vẫn chưa được phép trước khi cổng được kiểm chứng và được kích hoạt.

## #5 Review xây dựng — điều kiện triển khai bridge

- `da_nap` chỉ là đã nạp vào CSDL review; không có trạng thái nguồn “được phép hạch toán”. Review nguồn và duyệt kế toán là hai trạng thái độc lập.
- Chưa có trường độc lập “số chấp nhận hạch toán”. Giữ đề nghị, giá trị kỳ, lũy kế, VAT, giữ lại và thu hồi tạm ứng riêng. Không lấy `de_nghi - anh_huong` làm số chấp nhận. `giu_lai`/TT-21 không tự thành bảo hành/TT-31.
- Khóa có namespace/instance + `ma_hd` + `dot` + ID review/phiên bản. Mapping pháp nhân/Junsky có xác nhận; không ghép mơ hồ bằng tên. Snapshot tham số/phụ lục tại ngày nghiệm thu; catalog tham số động.
- Bản thay phải có `supersedes`/lý do và giữ quyết định cũ; không sinh hai công nợ cho cùng sự kiện. Nếu bản cũ đã xuất/nạp, tạo việc điều chỉnh.
- M4 không review BOQ lại và không thêm gate tổng nghiệm thu không vượt hợp đồng chung mọi loại giá. Defect B1 đơn giá cố định đã được tài liệu nguồn ghi nhận, không được che bằng giả định dữ liệu đã nạp là đúng.

## Gói R_REV DEMO có thể làm ngay

Tái dùng `Record/Batch/Adapter` → `Store.ingest` (raw/hash/staging/evidence/transaction) → hồ sơ `NGHIEM_THU` → mapping/số được xác nhận → đề xuất noncash cân bằng → file soát trong shell hiện có. Production vẫn qua `giao_tiep` và vai trò riêng theo TL40; DEMO không chứng minh transport production đã chạy.

Không đổi fixture thành `that`, không chạy `Operations` bootstrap nguồn thật. Không giả hồ sơ review thành BANK/INVOICE hoặc dùng nguyên engine/vế tiền/logic học STK. Dùng profile builder/validator riêng; server khóa actor `MO_PHONG_*`, mức 2 vẫn khóa. Số chưa xác nhận hiển thị rõ, không mặc định 0; quyết định kế toán không sửa raw/core nguồn.

Acceptance tối thiểu:

1. JSON đúng source shape → hồ sơ chờ, còn sau restart, raw/hash/provenance giữ nguyên.
2. Đã nạp review nhưng thiếu mapping/số xác nhận → chặn Đồng ý; đổi `anh_huong` không tự đổi số kế toán.
3. Mapping/mã hợp lệ và xác nhận DEMO → một đề xuất noncash cân bằng; file soát ghi Nghiệm thu và nguồn/người xác nhận.
4. Nạp lại không trùng; nội dung thay có revision/cách ly và việc xử lý rõ; không ghi đè quyết định đã có.
5. Sai mã, thiếu đối tượng 331, Nợ khác Có, actor thật hoặc môi trường thật đều bị chặn server.
6. BANK/INVOICE/export hiện tại vẫn hoạt động; không chạy lại ứng dụng review nguồn.

Đạt gói này là bridge DEMO hoạt động; không đồng nghĩa hoàn thành toàn bộ M4 hay toàn bộ cây 33.
