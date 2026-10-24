# Kiểm độc lập CRM-41-03 F17 — 22/10/2026

Trạng thái: CẦN SỬA; chưa nghiệm thu CRM hoặc M4. Claude FIX02 đã terminal91571/4cd6ca, bản F17 được đóng băng; không còn writer của lượt đó.

| Phạm vi | Kết quả thực tế | Giới hạn |
|---|---|---|
| AST Python | 6 file hợp lệ | Chỉ cú pháp, không import sản phẩm |
| Giao diện bất đồng bộ mô phỏng | 16 nhóm gốc đạt, không bỏ assertions | Fake DOM/fetch, không phải browser |
| Tính toán/DOCX/mock PDF và lifecycle | 47 ca:44 đạt/3 lỗi/0 error/0 skip | Gồm7 kiểm tĩnh và40 non-Word; không gọi Word/SQL/GUI |
| Probe UI độc lập | 1 positive đạt,2 lỗi tái hiện;0 chưa xác minh | Same-newdraft ACK giữ ID/revision đạt; reset Mới→Mới và retry sau khi gõ còn lỗi |
| PostgreSQL CRM DEMO | 5 ca:4 đạt/1 lỗi/0 error/0 skip | g05 dừng ở assertion quyền cuối; không phải toàn bộ11 ca HTTP |
| Đối soát g05 trên DB DEMO mới | Không context:0 dòng thấy/0 cập nhật; context BH hợp lệ:thấy1 dòng và P0001/CRM_G_CHI_CHU | Full-row hash và trạng thái owner không đổi ở cả2 mode. Cần tăng kiểm chứng test, không sửa SQL |
| GUI thật | Đã mở phiên riêng và nhập một phần form báo giá DEMO | Chưa Lưu→Chuyển→Lưu/mở lại; không coi luồng GUI đạt. Phiên đã hết hạn và dừng sạch |
| Word/PDF thật | Chưa chạy | Mock/metadata không thay cho chuyển Word→PDF và visual QA |
| M4 Lớp3 | 6 tệp DEMO đã có, kiểm cấu trúc/nội dung gốc | Chưa chạy bộ đọc/tiếp nhận M4; chưa nghiệm thu module |

Các lượt native đã có stop/Job-empty và posthash; phiên GUI có server/thread/connections đã đóng. Không xóa file, không can thiệp giao diện riêng hiện có của Anh.

## Findings chuyển Claude sửa

1. ACK của báo giá Mới A có thể gán ID A sang báo giá Mới B vừa reset; cần new-draft identity riêng nhưng giữ ACK recovery khi gõ tiếp cùng draft.
2. Retry sau khi gõ tiếp còn đổi trạng thái/nút retry của form hiện hành trước POST; cần giữ original visible-form fence cả trước và sau await.
3. Số trang PDF bị biến occurrence count ghi đè; ba ca KiemPdfDem hiện có đều phát hiện lỗi này.
4. JSON protocol không phải object hoặc exception bất ngờ có thể bỏ qua bước xác nhận dừng; cần structured error và stop witness/UNKNOWN trên mọi nhánh.
5. HTTP g05 cần chứng minh riêng RLS zero-row và trigger denial trong đúng actor context; giữ nguyên SQL/product guard và toàn bộ kiểm Convert trước đó.

Bàn giao: docs/GIAO-SUA-CRM-41-03-03-GUI-VA-PDF.md,6 file existing/NEW0, CODE_ONLY. Sau terminal mới kiểm bản mới bằng test và GUI/Word phù hợp. Giữ full CRM41–42, full M4, engine dùng chung; M2-00 rồi E1-MUA xếp sau CRM; M9 dừng.

## Dấu vết bằng chứng

- F17: crm-41-03-fix02-frozen-224a441d3c93; source377 SHA61a46a81d814f92032be1430e433a329c86cf5282858bd8891236581112fbf96; runtime446 SHA987dbcc6e41e164ffa916a0031d068c5d0ff4b524f5605f5200327272d00b6d1.
- AST: crm4103-f17-ast-root-20261021-01/syntax-receipt.json.
- Node16: crm4103-f17-async-root-20261021-01/parent-receipt.json; actualdf050a.
- Non-Word47: crm4103-f17-nonword47-root-20261021-01/child-receipt.json; actuale0ce4c/c7a07c.
- UI riêng: crm4103-f17-ui-private-root-actual-20261021-01/stdout.log; actual699480/575b88/0f7f52.
- PG5: crm4103-f17-pg5-actual-root-20261021-01/child-receipt.json; actualffad77/8dbd0d/431107.
- g05: crm4103-f17-g05-rls-actual-root-20261021-01/child-receipt.json; actual96c69b/9f0adb/653ff3.
- GUI: crm4103-gui-readiness-prep-20261021-m9-01/actual-f17-root01/parent-stopped.json; actual7c4b4b; Save/Convert browser verification=false.
