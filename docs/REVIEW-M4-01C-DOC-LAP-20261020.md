# M4-01C — kiểm độc lập trước khi mở giao diện

20/10/2026. **Chưa đạt điều kiện mở GUI để nghiệm thu.** Code Cổng đã terminal và đóng băng (source352/runtime418); đây chưa phải toàn M4.

Bộ kiểm thực tế ban đầu đạt 16 ca Python và 6 ca Node. Các ca này chủ yếu kiểm cấu trúc/tệp nguồn và một số tình huống role/replay; không bao phủ hết các race. Root chạy diagnostic độc lập trên nguyên function slices của code đã pin và tái hiện hai lỗi: phản hồi POST cũ xóa key/inflight của request mới sau vòng đổi vai A→B→A; phản hồi sheet A cũ ghi đè sheet B được chọn sau.

Review tĩnh Root và ba agent còn xác nhận thiếu form/selection fence, form Import BOQ cũ vẫn bấm được khi preview sheet mới đang chờ, và hàng role POST đang chờ cả reload GET. Các lỗi này phải sửa trước GUI. HTTP adapter/bootstrap/khai báo package và 35 tài nguyên nguồn đã qua rà soát tĩnh; chưa chạy HTTP hoặc build/cài wheel.

Bằng chứng native: `var/codex-dieu-phoi/m4c-root-pure-actual-828d258942df/summary.json`, SHA `f6777a0bfaf02abecef0eb67ff349c24ce3b2c5ccd0ca8762b85fccb078efde6`. Diagnostic: `var/codex-dieu-phoi/m4c-independent-async-diagnostic-20261020-l11-01/actual-497f66c24e8f/summary.json`, SHA `8af97abddd7438a5a6ba223defe1d6002372c39674cb71c9947cfa390d8db688`. Exit 0 của diagnostic nghĩa tái hiện đúng lỗi, không phải product PASS. Các tiến trình kiểm đã dừng và nguồn post-hash khớp.

[Handoff sửa C2](GIAO-CODE-M4-01C2-SUA-VONG-DOI-GIAO-DIEN.md) giới hạn 5 file, đã phát thực tế cùng Claude session (owned handle19047). Claude chỉ viết code; self-test NOT_RUN. Sau terminal sẽ freeze, kiểm các race, HTTP, packaging và GUI thực tế trên DEMO. Full Review/PDF/nghiệm thu–công nợ/Request và CRM tiếp tục theo hàng chờ. Không xóa file hoặc chạy M9/dữ liệu vận hành.
