# Điều phối worker và trạng thái kiểm độc lập — 22/10/2026

Quy ước Anh vừa yêu cầu: một worker Claude kết thúc thì giao đầu việc kế tiếp đủ điều kiện trong lúc Codex/worker khác kiểm độc lập phần vừa bàn giao. Không chờ cả nhóm. Duy trì tối đa 3 lượt coding đồng thời theo tài nguyên hiện tại; mỗi lượt có phạm vi file riêng và workspace riêng. Root chỉ ghép phần đã kiểm; không để hai người cùng sửa một file. Đây là cách điều phối hiện hành, chưa có dịch vụ tự điều phối chạy nền.

## Trạng thái đã kiểm bằng tiến trình và bằng chứng

| Đầu việc | Code / kiểm độc lập | Tiếp theo |
|---|---|---|
| M4 kiểm thử ranh giới L3 | Đạt độc lập 44/44; đã ghép đúng phạm vi test và báo cáo | Giữ kết quả; không suy là toàn M4 đạt |
| M4 Duyệt & PDF | Code đã bàn giao; 12/12 native FakeDOM đạt. Addendum độc lập 6/6 phát hiện lỗi, setup 0: phiên bản cũ/ABA; quyền hiện hành khi gửi lại; asset về muộn sau rời màn hình | Giao UI-FIX01, giữ native tests, sửa và kiểm lại |
| M4 Review: xem BOQ/phụ lục căn cứ | Code đã bàn giao. Native chạy 32 ca: 31 đạt, 1 assertion C18 bắt nhầm chính câu phủ định “không coi là 0 dòng”; setup 0. Chưa coi là đạt cả bộ | Sửa đúng predicate test và thêm negative control, giữ product/C18b; kiểm lại một lượt sau thay đổi |
| M4 backend Duyệt/PDF | Claude dừng do session quota; phần code đang có đã lưu snapshot riêng. Còn ba file test, báo cáo và hoàn thiện fixture/approver | Tiếp tục đúng session và phạm vi đã giao; không viết lại từ đầu |
| CRM G6A: kế toán kiểm → hiệu lực | Gói full G6A đã stage, Root đọc phạm vi, AST controller và kiểm 520 input pins không lệch; chưa chạy Claude | Giao ngay khi quota cho phép, song song M4. Thiếu proof G5 thật phải HOLD; synthetic positive không thay nghiệm thu |
| Engine trích tham số dùng chung #6 | TC01 DEMO tạo được nguồn offline nhưng HTTP lấy kết quả còn timeout; một diagnostic xác nhận chờ headers, chưa xác định lỗi nguồn | Giữ NOT_VERIFIED; không lặp chạy mù hoặc dựng engine khác |

Claude báo session limit, dự kiến reset **00:50 ngày 23/10/2026 (Asia/Ho_Chi_Minh)**. Thời điểm này không có head Claude cũ còn chạy. Không đổi model hoặc gọi lặp để né hạn mức; các worker Codex tiếp tục review/preparation trong lúc chờ.

## Các nhánh coding sẽ tiếp tục

1. M4 backend 02C: giữ session đang làm, hoàn thiện gói và kiểm độc lập.
2. CRM G6A: kiểm kế toán, mapping/checklist/K5 và activation có điều kiện vào master/PB/lịch thu hiện có; không tạo master/engine mới.
3. M4 UI-FIX01: sửa ba lỗi đã tái hiện. Khi một slot trống, nhận sửa test C18 hoặc đầu việc đã chốt tiếp theo, không chờ các slot khác.

M2-00 vẫn sau CRM; E1-MUA sau M2-00. M9 tiếp tục dừng code/test/runtime. Kho thật vẫn SQLite; không duyệt dữ liệu thật, bật cloud, nhập Junsky hoặc xóa file. Chưa có kết luận hoàn tất/nghiệm thu toàn M4 hoặc CRM; chỉ mời Anh xem module sau khi có kiểm độc lập và kiểm giao diện thật.

Điểm tiếp tục máy đọc: `var/codex-dieu-phoi/continuity-current.json`. Bản sao các trạng thái trước khi cập nhật được giữ tại `var/codex-dieu-phoi/pipeline-checkpoint-905afd03872f/`.

## Bổ sung kiểm tĩnh backend M4 — 23/10

Review độc lập xác định ba lỗi cần sửa trong đúng gói đang làm: DTO chưa khớp UI thật; PDF ứng viên thiếu ràng buộc với graph/kết luận; thay BOQ/phụ lục sau khi nộp có đường command cho phép dùng căn cứ mới trên phiên bản cũ. Đây là kết luận kiểm tĩnh có đường nhân quả và tham chiếu source, chưa phải tái hiện runtime. Chưa ghép code này vào sản phẩm.

Addendum giao tiếp đã lưu tại `var/codex-dieu-phoi/m4-02c-partial-static-review-20261023-agent-01/REVIEW-AND-CODE-ONLY-ADDENDUM.md`; phải đưa vào lượt tiếp tục backend cùng session, đồng thời hoàn thiện test/báo cáo còn thiếu. Hai gói CRM G6A và UI-FIX01 đều đã stage và Root kiểm input/controller; chưa khởi chạy Claude vì quota.
