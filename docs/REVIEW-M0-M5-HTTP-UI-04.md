# M0/M5 HTTP/UI — review static final04

19/10/2026. **STATIC_REVIEW / CÒN F1-P2 / KHÔNG RUNTIME ACCEPTANCE.** Root cung cấp actual Claude72850 terminal0 `7ee109`, receipt `0298adc39c5b10456094139ce02f6f89bddc5e517775189ef777f69fa15b2269`; bản review đọc frozen04, không đọc source interim. Manifest210 SHA `bb25b5d6d0b06403bce04d22a6c239b269d1b024f7b3a493d56f26b7512ec780`, thư mục `var/codex-dieu-phoi/kiem-chung-20261018-101441/m0-m5-intake-ui04-handoff-20261019-175226-626-cf1d4eda/frozen/`.

Đã full-read handoff04 `aedd9f87b9f78a0b7dea0c511e2bfad76348b2379befdf9c8b4dd1fe56fd539e`, root-report03 `352b50644d9efc3a31dff33ae32a259f4d2c17aa2e38ddb4a0406e127b3d7ff6`, report04 `a3bdee18051e8db9e4830a567d0347d3d6614b7ee17f333f72ce96f8b967c613`; toàn vùng JS M5:672–930, service:74–110/516–558 và callgraph FILE đã review03. Root review tests/SQL riêng; reviewer không import/chạy product/test/SQL/HTTP/browser/process hoặc sửa product.

| Frozen04 file | SHA256 thực đọc | So frozen03 |
|---|---|---|
| `giao_dien/assets/app.js` | `bdc3b5a8f9e94cf2f2928ad4a4bd887d85c926de668cc1bdf120f728a248a0c9` | Đổi predicate/completion của upload |
| `giao_dien/server.py` | `2e948604576486e1f153e5010ad00685dc11f275390b446eeb0c946be0d19c81` | Toàn bytes và text nguyên |
| `giao_dien/assets/index.html` | `94d52da8f6a23d28e7b1f87ebf9cd5228397135e1f06c059cffd0a3eec462779` | Toàn bytes và text nguyên |
| `giao_dien/assets/style.css` | `29a19358c8b3d87c5c88108eaeb0030f8697dceb1ffdf2422a16665c616631b0` | Toàn bytes và text nguyên |
| `k2/kho_so_luong.py` | `65957db4a85c0c575e36ba06b691642254fcf0d187ed1c07eb69bb5339949bc6` | Thêm `_tx_doc`; detail dùng snapshot đọc |

## F1 — P2: predicate form chưa đi vào refresh/render

**Anchors:** `app.js:700–714`, `768–789`, `877–884`, `917–923`. Upload giữ `fe`, tạo `formCon`, truyền vào `m5Act` và kiểm lại trước summary. `m5Act` đã kiểm actor sau POST, chỉ toast khi predicate còn đúng, suppress kết quả/lỗi của upload cũ và dùng ghi chú trung tính. Đây là cải thiện thật so03; không lặp finding actor epoch đã đóng.

Tuy nhiên `m5Act:707` vẫn luôn gọi `await m5Load()` không truyền predicate. `m5Load:877–884` chỉ kiểm **actor epoch** rồi gán `m5=s`, gọi `m5Render()` hoặc ghi lỗi. `m5Render:782–789` còn thay source/scope/coverage/key controls; `809` gọi detail async tiếp. Predicate chỉ được xét ở `709`, sau khi refresh đã render. Form thay source/coverage/file/key chỉ tăng `m5FormEpoch`, không tăng actor epoch, nên không loại đường này.

**Finite control chưa chạy:** cùng actor, submit native/master và claims A; giữ POST hoặc GET refresh còn pending; đổi form sang claims B để `fe` khác; thả completion cũ. Source cho phép refresh của operation A thực hiện assignment/render/error trên màn hình B trước khi đổi sang `M5_FORM_DA_DOI`. Đây là gap của yêu cầu handoff04 “predicate xuyên refresh/render”, không chứng minh body B bị gửi với bytes A, không khẳng định mọi refresh đều ghi đè lựa chọn B: hiện renderer cố giữ lựa chọn còn hợp lệ. Capture đã commit vẫn giữ nguyên và có thể xuất hiện trong lần refresh chủ động sau đó.

**Sửa hữu hạn:** truyền cùng predicate vào refresh/load và kiểm trước assignment/render/error của response; nếu đường refresh kéo detail thì cùng guard tại completion detail, hoặc tách refresh nền không đụng form. Flow khóa form tới completion cũng là phương án nếu diễn đạt rõ. Chỉ đặt thêm check sau `await m5Load` chưa đủ. Giữ positive form không đổi vẫn refresh/summary bình thường; form đổi sau POST và trong refresh không gắn old success/error/result vào form mới; không rollback/delete capture.

## Các phần đã cải thiện hoặc giữ nguyên

- **Display/token coherence — structural closure, runtime pending.** `kho_so_luong.py:99–110` từ chối connection đang có transaction (`M5_DOC_NHAT_QUAN`), mở transaction và đặt `REPEATABLE READ, READ ONLY` trước GUC SELECT; `chi_tiet:519–536` đọc graph hiển thị và `m5_co_so_file` trong cùng snapshot. Không còn late-token READ COMMITTED shape đã thấy03. Đây chưa là kết quả actual interleave/outer-transaction positive/negative; root chạy riêng. FILE vẫn phải kiểm basis/kỳ/quyền hiện hành, vì snapshot đọc nhất quán có thể đã cũ.
- **FILE key/expected basis giữ contract03.** JS `734–737/842–850` giữ khóa theo actor+PN+phiếu+ba pointers+whole-basis, refresh cùng context không tạo khóa mới; nút “Lần xuất mới” riêng. Server bytes không đổi nên expected-pointer/token whitelist và service FILE call signature vẫn như03. Immutable old GET/download tách khỏi current action; không suy structural closure thành actual same-lô/download/cells PASS04.
- **Native/master pickers và actor scope giữ source03.** Raw `FileReader.readAsArrayBuffer`→Uint8Array/base64 (`717–724`), snapshot claims/File objects trước await (`904–916`), guard trước POST; không JSON-parse/Number/re-serialize native bytes. Exact8 actor list dùng trusted server registry như03; VIEW/M1/source-only authorization vẫn do server/DB, không lấy disable UI làm guard. Browser picker/bigNumber/NULL/delayed actor/form và full action matrix vẫn UNRUN trong review này.
- **M9 byte preservation của phần HTTP/UI:** toàn server/index/style có SHA và full text bằng03; prefix JS trước marker M5 (bao gồm vùng M9) full-text bằng03. Không có M9 execution/call bởi reviewer. Không mở rộng kết luận này thành whole-M9 SQL acceptance hoặc resume tracking.

Kết luận: F1 còn một gap static hữu hạn trong propagation tới refresh/render; snapshot detail có structural fix cần actual verification. Counts/code-only report04 và terminal không được dùng làm GUI/HTTP/runtime PASS.
