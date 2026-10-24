# M4-01C2 — Kết quả kiểm độc lập

21/10/2026. **Bản Cổng hồ sơ chưa sẵn sàng nghiệm thu giao diện; còn hai P2 cần sửa.** Kết quả dưới đây là kiểm trên bản C2 đã đóng băng, không phải tuyên bố hoàn tất toàn M4.

## Bản được kiểm

Claude cùng session đã terminal thực tế handle19047/chunk9881f1, exit0; Root xác nhận dừng và giới hạn sửa. Source352/runtime418 trong `var/codex-dieu-phoi/m4c2-runtime-frozen-ddabd91d10a5`; SHA source `af149b19ea39db681a63abdbd3cae3486758245167beeca9d9cffe3e655e85d5`, runtime `14ad78af4d0f95c4c4dbf4a33e9fa87cc5bb28f49fedee72a203f250341f392f`. Chỉ đúng5 file được sửa,347 file nguồn bảo vệ giữ nguyên; không thêm/xóa file. M9 giữ nguyên.

## Bằng chứng đã chạy

| Lớp | Kết quả thực tế | Bằng chứng |
|---|---|---|
| Native Python | 16/16, zero failure/error/skip; import từ frozen | `var/codex-dieu-phoi/m4c2-root-native-actual-b66a71c48255/summary.json` SHA176bf304…8cbf242, actuala07c73 |
| Native async Node | 6 nhóm P0/C2-1a/C2-1b/C2-2/C2-3/C2-4 đạt | Cùng summary trên; VM/DOM giả, chưa phải browser |
| Độc lập hai lỗi cũ | Old POST không xóa ownership mới; preview B không bị response A về muộn thay thế | `var/codex-dieu-phoi/m4c-independent-async-diagnostic-20261020-l11-01/actual-c2-9ee765b2c304/summary.json` SHA19214c3a…74ca3a, actuale4c73a |
| HTTP/PG thật | 8/8, zero failure/error/skip, một DB DEMO mới; owned server/connections đã đóng, source pre/post khớp | `var/codex-dieu-phoi/m4c2-http8-owned-prep-0ea1bd4718e0/actual-dd9f8c7b8d22/parent-summary.json`, actual318f4d |

HTTP đã đi qua assets/state/current authority, fixture whitelist/raw bytes, tạo HĐ/replay/conflict, cross-scope, Track Changes, xác nhận tham số/phụ lục/BOQ/checklist/ngày đợt, nộp và reviewer, thu hồi dự án và sai role. Bài kiểm dùng tài khoản DEMO và backend thực; không phát sinh Request hoặc công nợ thật. Các DB/role/file đều được giữ.

## Hai P2 còn lại

1. **C2UI-01:** POST thành công rồi refresh GET/BOQ preview đang chờ; người dùng mở/nhập form mới; callback cuối vẫn có thể render lại và làm mất nháp mới. Guard ở await đầu chưa bảo vệ tới tác động DOM cuối. Cần bao gồm revision restoration và GET đợt.
2. **C2UI-02:** upload mẫu có kết quả chưa rõ chưa có retry giữ original File/bytes/key; bấm lại tạo File/timestamp mới, có thể tạo namespace khác. Cần giữ cả continuation để gắn tệp/preview hoàn tất đúng một lần.

Root cùng hai peer đã đối chiếu actual source. Diagnostic bổ sung lần01 gặp lỗi setup ReferenceError trước positive control, được ghi **NOT_VERIFIED**, không coi là tái hiện lỗi sản phẩm. Lần02 chỉ bổ sung primitive môi trường bị thiếu và diagnostic hữu hạn; đã tái hiện cả hai lỗi trong3 cửa sổ, với2 positive controls đạt: refresh GET làm rỗng nháp B, BOQ preview làm rỗng nháp PL, retry mẫu giữ bytes nhưng đổi header/key và fetch mẫu lần nữa. Đây là **bằng chứng lỗi, không phải product PASS**. Actuald2b2f3, `var/codex-dieu-phoi/m4c2-residual-independent-async-20261021-m9-01/actual-02-527322fe8fac/summary.json` SHA601fb62a…1ce6cff; owned child đã dừng, whole418 posthash khớp. Lần01 và toàn bộ lịch sử được giữ.

Lượt sửa C3 được giới hạn đúng5 file trong [brief](GIAO-CODE-M4-01C3-GIU-NHAP-VA-GUI-LAI-TEP.md); đã native init thực tế handle48960/chunke42d33 cùng session Claude, đúng5 filetools/emptyMCP. C3 chưa terminal, chưa kiểm sản phẩm; trạng thái mới nhất theo continuity.

## Phần chưa đạt nghiệm thu

Chưa chạy kiểm giao diện browser18ca/1280–1440, build wheel và isolated installed smoke của bản cuối. Full Review L1–L3/OCR/ghép–chạy lại/lịch sử/báo cáo, duyệt/PDF, nghiệm thu–công nợ và Request vẫn là phạm vi phải triển khai tiếp, không được coi bản Cổng này là toàn module hoàn tất. CRM41–42 có đặc tả/hàng chờ và fixture độc lập đang chuẩn bị; chưa phải CRM-G đã lập trình hoặc nghiệm thu.
