# M0/M5 UI05 — closure static của F1

19/10/2026. **STATIC_F1_CLOSED / KHÔNG GUI ACCEPTANCE.** Đọc bản frozen sau actual20501 terminal0 `11d444` do root cung cấp: `var/codex-dieu-phoi/kiem-chung-20261018-101441/m0-m5-ui05-handoff-20261019-180910-058-4d872643/frozen/`. Manifest210 `7d545cbcbcd0942fb3a63db9ca88ee81570789a2d635cdef453f955370d5f059`; so manifest04 `bb25b5d6d0b06403bce04d22a6c239b269d1b024f7b3a493d56f26b7512ec780`: cùng210paths, chỉ app.js đổi. Không lấy source interim hoặc terminal làm UI PASS.

Đã full-read toàn vùng M5 `app.js:672–940`, đối chiếu toàn vùng04 và call paths bị sửa, handoff05 `3d03f56947d95cb2f67693952df4297be42741d85536b1e4b0fa947c3eab0090`, report05 `a620bc46e3c2dfac6f996404b774a0a6fab2af00fddc35ac12ecf1e8791bd010`. Review04 `a7127733d3a4de67c7acd6d185d30203879ac605219b8f360fca639d2740af87` giữ nguyên lịch sử; F1 đã được rebind vào source mới, không lặp finding cũ chưa cập nhật.

| File frozen05 | SHA256 thực đọc | So04 |
|---|---|---|
| `giao_dien/assets/app.js` | `3a55053b5ae212b31c6dd200bdb6ff5aeb0d799e81518280274c1e927ca621f2` | Predicate/neutral notice trong vùng M5 |
| `giao_dien/server.py` | `2e948604576486e1f153e5010ad00685dc11f275390b446eeb0c946be0d19c81` | Bytes nguyên |
| `giao_dien/assets/index.html` | `94d52da8f6a23d28e7b1f87ebf9cd5228397135e1f06c059cffd0a3eec462779` | Bytes nguyên |
| `giao_dien/assets/style.css` | `29a19358c8b3d87c5c88108eaeb0030f8697dceb1ffdf2422a16665c616631b0` | Bytes nguyên |
| `k2/kho_so_luong.py` | `65957db4a85c0c575e36ba06b691642254fcf0d187ed1c07eb69bb5339949bc6` | Bytes nguyên; backend04 riêng |

## Predicate đã đi tới các completion cần bảo vệ

- **`m5Act:705–721`:** sau POST kiểm actor, rồi predicate trước toast/refresh; stale thì neutral+null. Refresh gọi `m5Load(conHieuLuc)`, sau await kiểm lại actor/predicate trước return. Catch cũng kiểm cả hai; không đưa lỗi operation cũ vào form mới.
- **`m5Load:886–895`:** kiểm predicate trước GET, kiểm actor+predicate trước `m5=s`/render và trước error status. Vì vậy form đổi khi POST/GET pending không còn đường assignment/render/error đã thấy04. Predicate được truyền vào renderer.
- **`m5Render:774–816` → `m5Detail:837–883`:** render đồng bộ, không có await giữa guard của load và render; chuyển cùng predicate vào detail async. Detail kiểm trước request, trong catch trước hide/toast, và sau response trước `m5ChiTiet=d`/DOM render. Việc renderer tự xóa lựa chọn nguồn đã biến mất có thể tăng form epoch; detail kế tiếp được guard và thao tác trở về neutral, không tự gắn kết quả vào lựa chọn khác.
- **Default/manual positives:** manual refresh/filter/đổi vai/hash/mở phiếu và các action FILE/MAP/review/nhận mẫu vẫn dùng default predicate=true, giữ actor/lựa chọn epoch. Upload giữ nguyên `fe` closure từ trước FileReader và chỉ summary khi actor+form còn đúng (`914–933`). Form không đổi vẫn đi POST→refresh→summary theo source; không blanket disable hoặc gửi lại capture.
- **Neutral notice:** `702` chỉ mô tả đã có phản hồi, hướng người dùng refresh chủ động. `703–704/719/932` dùng thông báo lỗi/mất kết nối riêng, nói rõ chưa biết server đã ghi hay chưa; không khẳng định commit từ network failure. Đây là nội dung/branch đã đọc static, không suy từ unit Act/Load thành đã chạy mọi nhánh POST rejection.

## Phạm vi được giữ và bằng chứng thực chạy tách riêng

ArrayBuffer→base64 (`723–730`), snapshot claims/File trước await (`914–927`), source/coverage form guards và trusted8actor selector nguyên cơ chế04. Khóa FILE theo actor+PN+phiếu+ba pointers+whole-basis (`740–743/849–857`) sống qua refresh; “Lần xuất mới” là action riêng. Không đổi API/backend/seed/quyền/fixture/reader hoặc thuật toán kho; các chữ Number/JSON của receipt/mapping không được dùng reserialize native bytes.

M9 HTTP/UI preservation có kiểm byte: server/index/style nguyên SHA; **64570bytes JS trước marker M5** cùng SHA `02860d9cc1a0e4fe401a14d48e6f1584d851c840ee10e3767b167d73aee52431` ở04 và05, gồm vùng M9. Không thực hiện M9 calls/resume. So manifest cho thấy209source còn lại nguyên; không biến việc giữ bytes thành acceptance nghiệp vụ M9.

Root thông báo actual async-unit probe391c chạy cùng oracle:4/4PASS,0setup (`74ee6a`, result SHA `1a555722b98af11ceb674cb30d538b3c37e4ff4b9e35327781557145b7923dd7`) và HTTP2PASS (`069a1c`), whole210source không đổi. Đây là thông tin root thực chạy, reviewer không chạy lại; unit chỉ actual extracted Act/Load với spies, **không** detail/real DOM/browser. Backend17migration/36service04 được root giữ component proof theo source pin, không cộng thành test mới05.

Không thấy blocker static còn lại của F1 trong phạm vi05. GUI/picker/delayed-response trên trình duyệt vẫn UNRUN; review này không đưa thêm business policy, không nghiệm thu toàn M5/L11/toàn33. Chỉ tạo tài liệu mới; không product edits/import/test/SQL/HTTP/browser/process bởi reviewer.
