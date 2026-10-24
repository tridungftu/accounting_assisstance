# CRM-01 — đối chiếu phạm vi và tái sử dụng sau bàn giao đầu

Ngày 19/10/2026. Codex đọc bản bàn giao sau Claude CLI exit 0; đây là review độc lập về độ đầy đủ, không phải kết quả bấm GUI hoặc nghiệm thu M1.

## Chưa nối luồng M1 hiện có

`k2/crm.py::nhan_tien_demo` chèn trực tiếp `kho.chung_tu` SAO_KE và một header `kho.de_xuat` VANG, `nguon_suy_luan=CFO`. Hàm không gọi engine M1, không giữ định danh BANK/quick_item legacy và không thêm dòng đề xuất/căn cứ policy. Báo cáo bàn giao cũng xác nhận không chiếu legacy. Ca không tăng số đề xuất khi nối chỉ chứng minh khoản thu DEMO vừa tạo không bị nhân đôi ở đường riêng này; chưa chứng minh sao kê/đề xuất M1 đã có được nhận diện và tái sử dụng khi hợp đồng đến trước hoặc sau.

Đầu bài §4 yêu cầu BANK/đề xuất M1 DEMO trong cùng PostgreSQL, provenance/khóa nối legacy–K2 nếu chiếu legacy, một sự kiện tiền logic. Cần dùng lại ingestion/engine/projection hiện hữu ở phần phù hợp, nối đúng chứng từ/đề xuất đã có, không viết engine hạch toán thứ hai. Phải đo BANK, chứng từ K2, đề xuất, dòng đề xuất, lô và link trước/sau nhận hợp đồng, phụ lục, nối/gỡ/retry. Không sửa kho thật hoặc mở Junsky mức 2.

Mã CFO cũng cần đối chiếu đúng phiên bản: JSON hiện có `CFO-02` là LUU_Y "344 chỉ dùng cho lần đặt cọc ban đầu, các lần thu sau ghi 131"; TL37 và TL39 gọi quy tắc tiền về chưa rõ cọc/đợt là CFO-03, trong khi TL35 cũ ghi CFO-02. Không tự đổi file policy thật hay coi header VANG trống là bút toán theo policy đã chạy. Giữ provenance quyết định và phân biệt ca thiếu mã tài khoản/mapping với đề xuất đầy đủ.

## Chưa đủ thao tác giao diện được giao

Đã đọc toàn bộ các route `/api/crm/*` và thao tác tương ứng trong server/assets ở bản bàn giao đầu:

- Chưa có export/tải file soát CRM/lịch nghĩa vụ như đầu bài §3–4; chưa có căn cứ tuyên bố đã xuất được file soát CRM.
- Hồ sơ CHO_KHOA/CHO_MAPPING không có thao tác tiếp tục đúng artifact sau bổ sung khóa/profile; retry cùng raw bị TRUNG_RAW (probe service độc lập đã tái hiện). Cần thao tác server và nút bấm có audit, không đổi raw/namespace giả để lách dedup.
- Trích lại cùng Word mới mở việc chờ; chưa có màn đối chiếu, lựa chọn và tiếp tục có vết. Đầu bài yêu cầu xử lý revision kết quả trích, không chỉ lưu việc chờ vĩnh viễn.
- `LocalApp.crm_nguoi` là biến dùng chung của app; trình chọn vai là DEMO, nhưng chưa gắn danh tính theo phiên như đầu bài. HTTP probe riêng sẽ phân biệt bằng chứng runtime với quan sát này. GET CRM có `mutation_lock`; không kết luận race kết nối chỉ từ ThreadingHTTPServer.

GUI thực tế chưa kiểm vì công cụ điều khiển browser của phiên hiện không khả dụng. HTTP và đọc code không được ghi thành đã bấm GUI. Các khoảng trống trên là công việc trong lát cắt đã giao, không phải lý do loại M1, export hoặc phục hồi hồ sơ khỏi phạm vi toàn cây 33.
