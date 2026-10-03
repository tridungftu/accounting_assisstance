# Báo cáo kiểm thử M1–M6

Ngày 17/09/2026; bàn giao v0.2.0, schema SQLite v8. Thực hiện theo A08, kiểm thử tay để sau theo chỉ dẫn của Anh.

## Kết luận

**90/90 tests tự động đạt, không lỗi/failure/skipped. Demo hai phiên hoàn tất trên fixture, backup/restore thành công.** Chưa có parser nguồn thực, mapping Junsky hoặc nghiệp vụ được kế toán ký; chưa cho phép vận hành PLHN.

Chứng cứ máy đọc: [kết quả tests](../var/test-results/latest.json), [demo hai phiên](../var/full-demo-final-v2/reports/SUMMARY.json), [A/B](../var/full-demo-final-v2/reports/BASELINE_AB.json). Tên đầy đủ mỗi test và hash các file code/test nằm trong báo cáo, không chỉ một con số tổng.

## Môi trường và lệnh thực chạy

Windows, Python 3.12.14, openpyxl 3.1.5 có sẵn. Runtime offline; không cài thêm dependency, không gọi API hoặc đọc dữ liệu thực. `test.ps1`/`run.ps1` đã chạy qua PowerShell.

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\test.ps1
```

Demo bàn giao được chạy bằng lệnh dưới khi đích chưa tồn tại. Không chạy lại vào đúng đích này; dùng ví dụ thư mục mới trong README để tái lập:

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\run.ps1 demo-full var/full-demo-final-v2
```

## Phạm vi tests

| Nhóm | Bằng chứng kiểm thử |
|---|---|
| M1: 42 hồi quy | Tiền chính xác/biên INTEGER/locale; mã 0 đầu/Đ–đ; cutoff; năm nhóm fixture; chống trùng/đổi tên/chồng kỳ; HĐ XML–bảng kê; raw/staging/FK; lỗi giữa transaction; nhập song song; Base quét/giải mã; migration và backup/restore |
| M2 | Chờ duyệt không dùng; approve/revoke đúng thời điểm; idempotent; hiệu lực [from,to); chồng lấn cần supersedes; không hồi sinh bản cũ sau thu hồi; Excel giữ mã; định danh xung đột; liên kết lịch sử không tự làm nhãn |
| M3 | Một phiên hoạt động cả khi hai tiến trình yêu cầu; cách ly mode; M:N/chi một phần/chi vượt công nợ; nhiều HĐ cùng điểm không chọn tùy ý; kỳ khóa; snapshot/tri thức đổi; template trực tiếp không ép qua công nợ |
| M4 | Chỉ bản duyệt cuối; workbook cũ/ID/tiền/mã/công thức/sửa tập dòng bị từ chối; reorder an toàn; rollback cả workbook; import/export idempotent; mã chuỗi; chặn target Junsky; lỗi công bố, tiến trình chết sau PREPARING; phục hồi file đã công bố; hủy trước công bố |
| M5 | Đã duyệt/đã xuất/số dư 0 chưa đủ nhãn; sai HĐ cùng tiền, sai dự án/số tiền, nhập một phần, chứng cứ lặp, thiếu field/chứng từ không đầy đủ; không có item nhưng scope chưa đủ; nhãn đúng cutoff, revoke/rebuild, tách policy; hai phiên dùng số dư mới không đếm hai lần |
| M6 | Dataset đóng băng/version; chặn nhóm rò giữa split; A/B cùng nguồn/cutoff; không dùng nhãn của chính tập đánh giá; B có thể bổ sung trường từ nhãn đã xác minh trong ca fixture; quy tắc cần ngưỡng fixture được duyệt + holdout + duyệt riêng; workbook mù trống đáp án; sai số tiền đếm một lần; neo quá khứ; chốt tháng/RECON_B; full CLI và restore artifact |

48 test mới M2–M6 và xuyên module cộng 42 test M1 = 90. Một test có thể gồm nhiều tình huống; không cộng các biến thể thành số bài riêng. Không chạy kiểm thử tải lớn, ma trận phiên bản Excel hoặc kiểm thử parser thật vì chưa có nguồn tương ứng.

## Kết quả demo

- Nạp hai giao dịch chi giả lập, mỗi giao dịch 100 VND; một khoản phải trả 200 VND theo cùng HĐ.
- Nạp bảy version tri thức fixture và ghi phê duyệt mô phỏng, không phải phê duyệt kế toán thực.
- Phiên 1: đề xuất/duyệt/xuất 100; sổ mô phỏng nhập lại, dư phải trả 100; xác minh và tạo một nhãn.
- Phiên 2: bộ nguồn mới, chỉ sử dụng số còn lại 100; đề xuất/duyệt/xuất/xác minh; dư 0 và thêm một nhãn.
- Đối soát lại cả hai batch với cùng bộ cuối tháng; kỳ vọng cộng dồn đúng, không dùng số dư tức thời phiên 1 để so sai với cuối tháng.
- Chốt `CLOSED_FIXTURE`; backup và restore giữ hai nhãn, batch dựng lại nguyên byte/ID, FK/integrity đạt.

Workbook duyệt/chờ duyệt/mù, nguồn và batch nằm trong thư mục demo. Các file `posted-simulation` được **sinh từ export để mô phỏng tích hợp**, không phải dữ liệu thực quan sát từ Junsky. Ground truth hai dòng được định nghĩa riêng trong fixture; đây vẫn không phải tập vàng độc lập do kế toán tạo. A và B đều đúng trên hai dòng đơn giản nên **chưa có căn cứ chọn B tốt hơn A cho PLHN**. Các ca lỗi được tạo độc lập bằng biến đổi có chủ đích và kỳ vọng phải chặn.

Đồng hồ demo bao gồm 01/10/2026, là ngày giả lập. `recorded_at` ghi thời điểm máy chạy thật; báo cáo không coi sự kiện mô phỏng tương lai là việc đã xảy ra ở doanh nghiệp.

## Vấn đề phát hiện và đã sửa trong lượt này

1. Điều kiện nâng schema trong test M1 còn cố định v2: cập nhật kiểm tra v8 và giữ kiểm tra không mất dữ liệu/checksum.
2. Fixture mới khai báo coverage đến cuối tháng khi as_of mới giữa tháng: sửa phạm vi fixture theo ngày thực được khai báo; không nới lỏng kiểm tra nguồn.
3. Đối soát batch đầu với số dư cuối tháng dễ bỏ sót delta của batch sau: cộng các batch sau mốc neo, theo từng open item.
4. Xuất bị ngắt cần phân biệt trước/sau công bố: phục hồi giữ định danh; chỉ cho hủy khi chưa có file công bố; giữ khóa DB trong lúc kiểm tra/công bố để tránh nguồn đổi giữa hai bước.
5. Ngày cutoff UTC có thể khác ngày lịch Việt Nam: dùng UTC+07 khi so ngày nghiệp vụ, vẫn lưu event time UTC.
6. Nhãn cùng policy logic nhưng khác phiên bản không được trộn; nhãn của bank nằm trong dataset không được dùng để chấm chính dataset.
7. Thiếu chứng cứ không phải chứng cứ sai: thiếu field/complete_voucher hoặc công nợ không đủ scope giữ UNRESOLVED và không tạo nhãn.

Các mục này có test hồi quy tương ứng. Không tuyên bố test xanh chứng minh hết lỗi có thể có; kết luận giới hạn ở các hành vi và môi trường đã chạy.

## Phần chưa được kiểm chứng

Parser PDF/XML/Excel/Base/Junsky thực; Entry1/2/EntryID/DebtID; khả năng Junsky import một phần/chống trùng; khóa/cửa sổ thao tác ngoài ứng dụng; chính sách tài khoản/thuế/28 mã/10–15 mẫu; lịch sử 12 tháng và known_at; E2/E5 thực; ba chỉ số từ khóa/bảy mã lý do/sáu phần báo cáo gốc; ngưỡng chất lượng/cỡ mẫu; đăng nhập/xác thực người duyệt; hiệu năng/tải thực; UAT và quyền vận hành. Phát sinh ngoài batch chưa giải quyết vẫn chặn khóa tháng, không có thao tác bỏ qua chênh.

Không có script khảo sát bản 1.2 nào được cung cấp thêm. Bốn file kế hoạch gốc giữ nguyên SHA-256. Các báo cáo M1 trước đây giữ làm lịch sử, không dùng thay báo cáo hiện tại.
