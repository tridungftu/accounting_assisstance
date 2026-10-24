# L11 repair04 — refresh context và oracle tuyến hiện hành

Tiếp tục cùng Claude session hiện tại; tận dụng toàn bộ code M2 XML/ZIP, M5 và L11 đã có. Kiến trúc và phạm vi nghiệp vụ giữ quyết định đã chốt. Đọc `REVIEW-L11-ROOT-ACTUAL-03.md`, `REVIEW-L11-HTTP-UI-03.md` và report03 trước khi sửa.

Đây là CODE ONLY. Không Bash/terminal, không runtime/test/SQL/launcher/browser/process, không gọi MCP/network. Root sẽ tự kiểm runtime trên bản cố định sau terminal thật. Không đọc `var/`, `.env`, source apps, dữ liệu thật hoặc credential. Không xóa, đổi tên hoặc di chuyển bất kỳ file nào. Không làm M9. Không thêm fixture/source file hoặc thay dependencies/migration/source schema.

Chỉ được sửa hai file có sẵn:

- `src/kho_tri_thuc/giao_dien/assets/app.js`
- `tests/test_l11_k2.py`

Chỉ được tạo thêm báo cáo `docs/BAO-CAO-L11-QUANTITY-04.md`. Không ghi đè report/review/handoff cũ. Nếu cần đổi file ngoài hai file này, báo rõ và dừng ở phạm vi đã thực hiện; không lách permission.

1. Sửa UI03-1: FILE refresh GET phải kiểm original operation context (epoch, form/pair/basis, owned generation) trước render/reset picker/status/toast. Một operation đã bị đổi form/pair không được ghi đè lựa chọn hiện tại. Duy trì current positive FILE flow, ordinary refresh/newer GET wins, role change trước POST/GET/headers/Blob và late-error fences đã có. Không chỉ thêm check sau khi DOM đã đổi. Không lấy việc 0 download làm đủ khi DOM vẫn bị phản hồi cũ ghi đè.
2. Sửa Q09-TEST-1 trong `route_body`: chọn đúng current route của đúng source line từ actual DTO; không `tuyen[0]`, không giả current token, không nới mã từ chối/guard. Khôi phục KHO tuần tự phải thành công thật để q03 chạy với trạng thái hợp lệ. Giữ actual two-session transaction/barrier/blocking-PID/timeout và exact denials; tách kết quả concurrent với fresh-token sequential follow-up. Test phải fail rõ nếu không có duy nhất một current route hợp lệ. Không bỏ qua hoặc đổi race thành tuần tự để lấy PASS.

Tiêu chí bàn giao: diff gọn chỉ hai file; mô tả chính xác context checks và route DTO selection; báo cáo những test chưa chạy là UNRUN. Không tự tuyên bố native suites/independent async/GUI PASS. Không tuyên bố cả module hoàn tất. Root sẽ kiểm lại 14 async cases, Q09 và các luồng liên quan trên hash cuối.
