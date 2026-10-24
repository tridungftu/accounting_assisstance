# M4-01C4 — kiểm độc lập ngày 21/10/2026

**Hai lỗi upload đã qua 5 contracts độc lập. Native đạt 12 nhóm và còn một lỗi setup test đã xác định; chưa nghiệm thu toàn M4.**

Claude kết thúc cùng session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`, owned handle69281/output59ecd1, exit0/success. Root đối chiếu source352/runtime418, đúng ba file thay đổi, không thêm file; 349 file được bảo vệ giữ nguyên. Root và agent không tham gia triển khai đọc thay đổi trước khi chạy.

## Bằng chứng thực tế

- Freeze: `var/codex-dieu-phoi/m4c4-runtime-frozen-5c522ed647e8`; source SHA `a6aa7f3c0bdb323a85f8d6dc2b936a7784531d8fb6ef6ccc8f788d4baa3f5c29`, runtime SHA `47c292d919ce3a11164bfa5a0d786aef93f43c0df0194dce61daf79821a65965`.
- Runtime độc lập: `var/codex-dieu-phoi/m4c4-root-finite-actual-01/attempt-08cfc9c2d3e5/summary.json`, SHA `47e3d0918ea19685175d0ba4fbd0681bd60e756139ae62106de56463f24dc088`, actual output0df328.
- Hai Node child đã dừng; toàn live352/frozen418 được kiểm hash trước/sau, không đổi. Không thực thi SQL hoặc nghiệp vụ thật.

| Contract độc lập | Kết quả |
|---|---|
| Tải mẫu không rỗng, đúng bytes/dự án và refresh hiện hàng nguồn mới | Đạt |
| Upload A chưa rõ → chuyển sang HĐ/dự án B → không POST lại tệp A | Đạt; nút retry cũ đã gỡ |
| Bấm mẫu liên tiếp khi GET chờ → một GET/một POST, completion một lần | Đạt |
| GET mẫu đang chờ → đổi HĐ/dự án → phản hồi cũ không POST | Đạt |
| Gửi lại cùng context giữ File/bytes/header/key gốc, không lấy mẫu lại; completion một lần | Đạt |

Native chạy nguyên file đóng băng: 10 nhóm cũ và C4-01a/C4-01b đạt. C4-02 đi qua phần upload đầu, rồi dừng vì test chưa chọn lại mẫu sau refresh; không có GET thứ hai để assertion đợi. Đây là **12 nhóm đạt + một lỗi setup**, không phải native13 đạt.

Root và peer đối chiếu thấy selector mới có giá trị rỗng; handler đúng khi không gửi nếu chưa chọn mẫu. Diagnostic riêng chỉ thêm hai câu lệnh chọn mẫu và phát `change`, giữ nguyên mọi assertion và file gốc: 13 nhóm qua, không lỗi. Bằng chứng diagnostic: `var/codex-dieu-phoi/m4c4-root-finite-actual-01/setup-probe-62e6b6c7580d/summary.json`, SHA `109e55ca0aed3b3cab0fdd70b1f2e7add9954c4a99941c3443bc08b6d8db806b`, actual output7ef663. **Diagnostic này không thay kết quả native gốc.**

## Sửa setup và bước tiếp theo

Giao Claude sửa đúng 87 byte setup trong `tests/m4_01c_async.cjs` ở lượt CRM kế tiếp. SHA file sau sửa phải `f77bdfe66772a2494d36f40cb1f2119d27af351ae8f101b1a3dc42bd9274a9d2`; mọi assertion giữ nguyên. Scope CRM vì vậy là 14 targets nghiệp vụ cộng một test setup: 15 targets, 7 existing +8 new, bảo vệ345 existing. M4 product JS giữ nguyên. Root phải chạy lại native thật sau Claude terminal và kiểm regression với APP mới.

16 pure tests từ C3 và 8 HTTP/PG tests từ C2 được giữ làm bằng chứng hữu hạn cho các file backend/test/fixture không đổi, không ghi thành lượt chạy C4 mới.

Quan sát browser C3 trước đó mới kiểm tạo HĐ, upload/gắn DOCX, trích37 mã, đợt nháp và chặn Nộp khi thiếu căn cứ. Chưa khép đủ18 ca GUI, wheel/install hoặc toàn Cổng hồ sơ. Các phần Review L1–L3, OCR/jobs/báo cáo, duyệt/PDF, nghiệm thu–công nợ và Request tiếp tục trong phạm vi M4. CRM G1/G7/S6 được giao xen kẽ; không chờ hoàn thành toàn Review M4 mới triển khai CRM. M9 tiếp tục không sửa code.
