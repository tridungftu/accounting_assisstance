# R1 — Review vòng 2 trước đợt nạp dài kỳ

R1 chỉ review. Không sửa mã, không duyệt tri thức, không nạp/import Junsky.

Mốc đối chiếu là `var/thu-nghiem-claude-2026-09-18/BAO-CAO-CHAY-THU-CODEX.md`. Các số tháng 8 trong mốc này được giữ để truy vết; A13 thay yêu cầu so/ngưỡng sau mỗi V bằng hồi quy kỹ thuật hai cột.

## Kết quả kiểm tra

| Phát hiện gốc | Kết luận R1 | Bằng chứng |
|---|---|---|
| F01 — trigger/thứ tự/CASE | Đóng ở mức code/test; vẫn chưa là tri thức vận hành vì kho that chỉ PENDING. | V1b matching tests; [V4](BAO-CAO-VONG-2.md#v4--tri-thức-excel-của-người) |
| F02 — regex/loại trừ | Đóng ở mức code/test. | V1b regression tests |
| F03 — thuế hóa đơn/nhiều dòng | Đóng ở mức contract/code/test; chưa kiểm chứng XML/bảng kê kỳ dài thực. | [V2](BAO-CAO-VONG-2.md#v2--hợp-đồng-nguồn-thuế-và-nhiều-dòng) |
| F04 — gộp XML↔bảng kê | Đóng ở mức code/test; chênh tiền được lưu warning. | V2 tests |
| F05 — tri thức Excel người đọc | Đóng ở mức code/test. Kho thử có 3.846 version PENDING, 0 event APPROVE, integrity đạt. | [V4](BAO-CAO-VONG-2.md#v4--tri-thức-excel-của-người) |
| F06 — workbook công nợ quá lớn | Đóng về cơ chế shortlist/công nợ khác; chưa đo với danh mục thực đầy đủ. | [V5](BAO-CAO-VONG-2.md#v5--hiệu-năng-workbook-duyệt-và-bộ-chấm) |
| F07 — trạng thái fixture | Đóng: logic nghiệp vụ không còn literal fixture; trạng thái posted lấy cấu hình. | Quét mã R1: 0 literal fixture ở engine/học/tri thức |
| F08 — hiệu năng tri thức | Đóng về cache/index; chưa đóng nghiệm thu hiệu năng với danh mục thực đầy đủ. | V1b cache tests, V5 index |
| F09 — NONE bị chấm sai | Đóng ở mức code/test; số đo chất lượng thực để đợt dữ liệu sau. | V5 score test |

Lát cắt tháng 8 có đủ năm file [KET-QUA](../var/vong-2/) của V2–V6. Mỗi file chứa đúng hai cột hồi cứu/không rò rỉ, `integrity_ok=true`; chúng không so ngưỡng và không kết luận chất lượng. Chúng nhất quán về mục đích, không phải bảng đo chất lượng nối tiếp V1b.

Suite cuối đạt 166/166. Quét R1 không tìm thấy dấu hiệu dữ liệu nguồn thật trong `tests/fixtures`; không tìm thấy literal trạng thái/phân vùng fixture trong logic engine/học/tri thức. File/bản sao được bảo vệ của V1/V1b tiếp tục có `changed=[]`, `all_unchanged=true` theo bằng chứng bảo toàn. Cấu hình that vẫn tắt cả hai cờ Junsky; V6 chỉ so cấu trúc Entry1 17/Entry2 37 với file T8 và luôn ghi `SHADOW — CHƯA NHẬP JUNSKY`.

## Kết luận nhận đợt nạp dài kỳ

**Chưa sẵn sàng nạp toàn bộ đợt dài kỳ ngay.** Code và contract đã sẵn sàng nhận hồ sơ, nhưng còn ba điều kiện có ảnh hưởng trực tiếp:

1. Cần wheel offline `xlrd==2.0.2` hoặc bản `.xlsx` kết xuất từ sao kê `.xls`; bộ đọc không tự thay bằng parser `.xls` không được xác minh.
2. Mỗi gói cần metadata người nạp: `as_of`, `exported_at`, `known_at`/basis, coverage, snapshot công nợ và kỳ khóa khai báo. Không có các giá trị này, dữ liệu không đủ điều kiện time-travel.
3. Cần danh mục export mới nhất và lô tri thức vẫn phải được `CFO_NTD` duyệt bằng lệnh riêng trước khi dùng cho đề xuất vận hành.

Sau khi ba điều kiện này được giao, có thể bắt đầu đợt nạp riêng đã nêu: tri thức 09/2024–12/2025, sổ T1–T7/2026, Base 2023–2025 và danh mục mới. Việc đó vẫn không tự mở quyền import Junsky hoặc quyết định vận hành pilot.
