# CRM-41-03 F16 · Kết quả kiểm độc lập ngày 21/10/2026

**FIX_REQUIRED; chưa nghiệm thu G2/G3 hoặc toàn CRM/M4.** Claude FIX01 đã dừng sạch, terminal `20504/be34f9`. Root đóng băng F16 source377/runtime446, protected drift0, engine nguồn37 và SQL1–20 giữ nguyên. Báo cáo coder chỉ CODE_ONLY, không dùng làm bằng chứng chạy đạt.

| Phép kiểm do Root chạy | Kết quả | Phạm vi bằng chứng |
|---|---|---|
| AST 6 file Python đổi | 6 đạt | Cú pháp, không import nghiệp vụ |
| 31 ca tính toán/DOCX/provider giả lập | 31 PASS, 0 fail/error/skip | Tính chính xác, DOCX bytes, lỗi/stop/đếm PDF giả lập; không SQL/Word/GUI thật |
| Native Node P0+A1–A10 | 11 PASS | Actual app.js/crm_g.js với fake DOM/fetch; A3 cũ giữ nguyên và đã qua; không browser thật |
| Ba kịch bản UI bổ sung độc lập | 3 lỗi tái hiện | Convert held + edit + nested list mất nháp; lost ACK→pending409→In lại đổi khóa; sửa amount vẫn nhìn thấy derived cũ |
| PostgreSQL DEMO21 + HTTP thật, subset5 | 2 PASS, 2 FAIL, 1 ERROR, 0 skip | g03 authority/number và g09 cancellation/permission đạt; g01 sai fixture upload; g04 thiếu G7 và g05 thiếu v1 bị dây chuyền |

Các lượt Root trên đã dừng; Job rỗng và frozen posthash đạt. Lượt PG cũng đóng server/thread/kết nối, không còn extra thread. Giữ DB/role/thư mục/file; không seed hoặc chạy M9, không full bootstrap, không Word thật.

## Lỗi cần sửa tiếp

- UI: giữ original key qua đúng pending409; original form fence qua Convert/retry/toast/error; chọn đổi mẫu phải dirty trước Xuất; invalidate derived ngay trên DOM khi input đổi. Review nguồn và ba kịch bản bổ sung tách khỏi 11 ca của coder đã đạt.
- HTTP fixture: `mau_hieu_luc` ghép human label `MAU V1/V2` vào khóa thao tác, trái `KHOA_RE`; `_khoa()` từ chối trước đọc DOCX/SQL. Tách machine key khỏi nội dung hiển thị, giữ product regex, mẫu v1/v2 và toàn assertions. Cần chạy lại subset5; chưa được suy toàn backend đạt.
- Renderer: giữ success-stop gate đã sửa; bổ sung stop witness mọi exception, native Word test có ownership/Job/deadline từ setup, cộng multiplicity khi nhiều field cùng displayed text. Word thật chưa chạy; test Word F16 còn thiếu bounded containment.

## Handoff kế tiếp và phạm vi còn lại

Root đã lập `GIAO-SUA-CRM-41-03-02-GUI-VA-WORD.md` và binding `CRM-41-03-WORD-OWNERSHIP-FIX02.md`. FIX02 dự kiến đúng6 existing files, NEW0, CODE_ONLY; SQL/service/route/host/engine/M4/M9 protected. Chưa coi việc có handoff là Claude đã chạy; cần actual handle/init trước khi báo active.

Ưu tiên kiểm và mở DEMO màn Báo giá/Soạn hợp đồng sau sửa, báo giới hạn PDF riêng. Chưa có GUI mới được xác minh. CRM catalog KCN/NHA/E3/E5/G4–G6 còn; full M4 L3/duyệt-PDF/kế toán/công nợ/Request còn; M2-00 rồi E1-MUA tiếp sau CRM. Engine chung vẫn có lỗi timeout GET status chưa khép. Không đổi mục tiêu toàn hệ thống theo file33.

Bằng chứng được giữ trong `var/codex-dieu-phoi`: `crm4103-f16-ast-root-20261021-01`, `crm4103-f16-pure31-root-20261021-01`, `crm4103-f16-async-root-20261021-01`, `crm4103-f16-private-ui-root-20261021-01/02/03`, `crm4103-f16-pg5-actual-root-20261021-01`, và ba review `crm4103-review-f16-kho-01/l11-01/m9-01`. Hai private probes đầu có lỗi setup hoặc quan sát trước nested GET được giữ là NOT_VERIFIED; chỉ các ca đã tái hiện đúng assertion sau điều chỉnh fixture được tính là lỗi sản phẩm.
