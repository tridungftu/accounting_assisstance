# Gói tiếp theo — tận dụng review xây dựng, nối hồ sơ kế toán DEMO

Theo yêu cầu trực tiếp của Anh ngày 18/10/2026: làm đủ cây 33 và tận dụng tối đa phần mềm đã có để tránh trao đổi/lập trình lại. Gói này thực hiện phần nhỏ đầu tiên của R_REV/M4; không phải phạm vi cuối của chương trình. Kiến trúc K1–K5 và TL40 giữ nguyên, không xin lại quyết định đã chốt.

Claude Code sửa chính; Codex/agent đọc, kiểm chứng độc lập. Trước khi sửa, đọc:

- `CHUONG-TRINH-HOAN-THIEN-PHAN-MEM-KE-TOAN.md` và hai hồ sơ `TAI-SU-DUNG-REVIEW-XAY-DUNG.md`, `DANH-MUC-TAI-SU-DUNG-PHAN-MEM.md`.
- `REVIEW-KE-HOACH-33-VA-TAI-SU-DUNG.md`; sửa điểm còn sót trong hai bản kế hoạch, không viết thêm một kế hoạch thay cho code gói này.
- Source kế toán hiện có: `nguon/fixture.py`, `ha_tang/store.py`, `giao_dien/server.py`, `giao_dien/quick.py`, assets shell DEMO, tests tương ứng.

## Đích bàn giao

Trong **cùng ứng dụng, cùng Store và cùng shell DEMO**: bấm nhận JSON giả đúng shape kết quả review #5 → xem hồ sơ nghiệm thu và căn cứ → bổ sung mapping/số kế toán còn thiếu → xác nhận bằng actor `MO_PHONG_` → một đề xuất noncash cân bằng → tải file soát. Có ca nhận lại và bản thay. Giữ Junsky mức 2 khóa.

Đây là bước K1/DEMO của bridge. Production từ #5 giữ kiến trúc `giao_tiep.v1_ghi_ket_qua_review`/vai trò riêng theo TL40, chưa được gọi đã tích hợp hoặc nghiệm thu nếu chỉ adapter DEMO chạy. Không sửa/chạy/import code dự án nguồn, không đọc dữ liệu thật/.env/backup, không gọi cloud/API hoặc gửi tin.

## Tái sử dụng và ranh giới file

1. Thêm adapter nguồn riêng đọc đúng shape JSON trong hồ sơ audit. Dùng `Record`/`Batch`/`Adapter`, `Store.ingest` để giữ raw bất biến/hash/staging/evidence/audit/transaction. Kind `NGHIEM_THU`, không giả thành BANK/INVOICE. Không thêm một kho/ứng dụng độc lập.
2. Dùng các bảng `quick_runs/quick_items`, nhật ký và file soát hiện có nếu tái dùng được an toàn. Có builder/validator noncash riêng; nếu cần façade nhỏ cho review thì vẫn dùng chính Store, không dựng cơ chế duyệt/tri thức ngân hàng thứ hai. Không tự học STK/từ khóa từ hồ sơ review.
3. `LocalApp` nối vào `demo_config` và cùng token/mutation lock. `Operations` chỉ cho `that` và có bootstrap nguồn thật, không dùng nó bằng cách đổi DEMO thành `that`. Server khóa môi trường/actor, không tin actor hoặc trạng thái do client gửi.
4. Thêm mục “Hồ sơ nghiệm thu” vào shell hiện có; dùng CSS/table/form/dialog đang có. Có mẫu DEMO nạp bằng nút, tải/nhận JSON, danh sách, chi tiết, phần xác nhận và file soát. Tiêu đề người dùng là Hỗ trợ kế toán; không làm lại UI review/BOQ của #5. Không dùng menu placeholder để tuyên bố đã đủ 10 module.
5. Thay đổi source/tests/assets cần thiết và ghi tài liệu bằng chứng ngắn; không sửa migration đã có checksum, không đụng dữ liệu/kho thật, không commit/reset. Không thêm thư viện mới.

## Hợp đồng dữ liệu và bảo toàn nghĩa

- Nhận loại `kiem_tra_dot`; giữ `ma`, `hop_dong.ma_hd/so_hd/phan_loai`, `dot`, `ngay_nghiem_thu`, `luc`, `de_nghi`, `tong_hop`, findings, `da_nap` và tham chiếu báo cáo. Khóa có namespace/instance nguồn. Giữ snapshot tham số/phụ lục hiệu lực tại ngày nghiệm thu khi được cung cấp; thiếu phải ghi thiếu, không gọi #5 hoặc suy thành đã có.
- Không giả định có số chấp nhận hạch toán trong JSON nguồn. `de_nghi`, giá trị kỳ, lũy kế, giữ lại đợt, tạm ứng và số chấp nhận/VAT là các trường khác nhau. Không tính `de_nghi - anh_huong`, không coi `da_nap` là duyệt kế toán, không đổi toàn bộ giữ lại thành bảo hành.
- Số chưa xác nhận là NULL/chưa xác nhận, không thành 0. Chỉ sau khi người có quyền DEMO xác nhận số/cơ sở VAT/mapping mới dùng làm đề xuất. Quyết định nằm trong metadata/audit, không sửa raw/core nguồn.
- Mapping instance/HĐ → pháp nhân, mã HĐ chung, ProjectID và ObjectID Junsky dựa trên catalog; không fuzzy tên. Tài khoản và mẫu bút toán của acceptance là **cấu hình DEMO công khai**, không quyết thay chính sách 241/154/VAT thật.
- Hai trạng thái nguồn/kế toán độc lập. Chưa nạp review hoặc thiếu mapping/số xác nhận thì vẫn có hồ sơ chờ, không vào xuất. Không dùng cutoff lịch sử để giấu hồ sơ mới thiếu known_at; điều kiện học là việc riêng.
- Nhận lại cùng bytes/nội dung không tạo chứng từ/quyết định trùng. Cùng event nội dung thay: revision/supersedes hoặc cách ly có việc xử lý rõ; không sinh công nợ lần hai hoặc ghi đè bản đã duyệt/xuất. Sau xuất giữ lô cũ và tạo điều chỉnh có vết.
- Không thêm kiểm tra/review BOQ, quy trình phụ lục, tính giữ lại/tạm ứng hoặc gate tổng NT<=HĐ thay phần mềm nguồn.

## Ca kiểm bắt buộc

1. JSON đúng shape #5 nhận vào cùng Store; restart vẫn thấy; provenance/raw hash giữ nguyên. Mẫu fixture có chữ DEMO, không chép payload thật.
2. `da_nap` có nhưng thiếu mapping/số chấp nhận/VAT → backend chặn Đồng ý và xuất. Thay `anh_huong` không tự đổi số kế toán đã xác nhận.
3. Xác nhận DEMO đủ → đề xuất noncash Nợ= Có, đúng mã danh mục/đối tượng 331/dự án; file soát ghi Nghiệm thu, nguồn và actor, không ghi Thu/Chi hoặc vế tiền.
4. Nhận lại → không trùng; bản sửa → có quan hệ thay hoặc cách ly/việc xử lý, giữ quyết định/bằng chứng cũ. Phân biệt giữ lại và bảo hành.
5. Actor thật, môi trường `that`, sai token, sai mã Junsky, thiếu đối tượng, Nợ khác Có hoặc yêu cầu mức 2 đều bị server chặn; strings nguồn hiển thị an toàn.
6. Regression BANK/INVOICE/export hiện tại theo các test có liên quan; không chạy lặp full GUI nếu không có lý do. CLI/test skip phải báo thật, Codex kiểm lại runtime và GUI bằng DEMO.

Handoff nêu file đổi, test pass/skip/error và cách mở bằng nút bấm. Không gọi toàn M4 hoàn thành từ gói bridge này. Các M0–M10 và L1–L12 còn lại vẫn nằm trong chương trình, tiếp tục theo phụ thuộc thật.
