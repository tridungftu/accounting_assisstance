# M4-01C2 — Sửa vòng đời giao diện Cổng hồ sơ

20/10/2026 · CODE_ONLY, cùng session Claude. Anh đã cho tiếp tục M4 và CRM; đây là sửa code sau kiểm độc lập trong phạm vi Cổng đã chốt, không đổi kiến trúc/nghiệp vụ. Không chạy test/lệnh/SQL/browser hoặc tạo agent/session khác. Giữ tất cả file và lịch sử.

## 1. Baseline và kết quả thật

M4-01C đã terminal thực tế owned handle 13247 / f879b8, exit 0, stop/scope confirmed. Frozen `var/codex-dieu-phoi/m4c-runtime-frozen-767a0d5197a7`: source352 SHA `9edb7cb864037d78d398a794cf8407d1b9c5c7d44316340b64e272cf3e51cc52`; runtime418 SHA `ec0b485937cf65d77731d18951f04f91bfe98c94ecae3dfeac7d0e8c95cb070f`; Root receipt SHA `8512037d073a78cb19d10166b81e46f1a5cc9187e574ae0516ea04323fb39856`. Đây là code-only, self-test NOT_RUN, chưa HTTP/GUI/wheel PASS.
B6 finite gate 50+4/10+8 đã đạt, business core/SQL/vendor nguồn giữ nguyên. Không chạy lại những bộ đó trong gói này. Full M4 Review/PDF/AP/Request và CRM vẫn giữ đủ hàng chờ theo public C handoff, không thu phạm vi hay gắn đã hoàn tất.

## 2. Chỉ sửa 5 file existing

- `src/kho_tri_thuc/giao_dien/assets/app.js` — seam role queue/fences hẹp, giữ nguyên byte block M9.
- `src/kho_tri_thuc/m4/giao_dien/m4.js` — ownership của pending intents và vòng đời form/preview.
- `tests/m4_01c_async.cjs` — ca bất đồng bộ có ý nghĩa trên actual source.
- `tests/test_m4_01c.py` — chỉ điều chỉnh assertion cấu trúc bị sửa, không thêm test mirror để che race.
- `docs/BAO-CAO-M4-01C.md` — giữ nội dung/lịch sử, thêm sửa C2 và trạng thái trung thực.

Không thêm file. Không sửa HTTP/bootstrap/pyproject/CSS/index, backend/service/schema/SQL, vendor, guard, M9, nguồn app gốc hoặc chứng cứ Root trong var. Chỉ đọc source đã pin; không đọc var/env/secrets/config thật.

## 3. Các lỗi đã đối chiếu độc lập

1. **Late POST xóa pending intent mới.** `m4.js:108–125`: k chỉ gồm path/body; `m4Xoa:257` clears map/set. Request A còn chờ → role B → trở lại A → gửi same body bằng key mới. Old success xóa `khoaMap` trước fence, finally xóa `dangGui` vô điều kiện; lần gửi mới mất ownership. Upload `170–188` cùng lỗi. Cần record/ticket ownership cho mỗi incarnation; success/catch/finally chỉ dọn đúng record mình sở hữu. Chỉ đổi vị trí `if(f)` không đủ cho request mới cùng context. Giữ exact original key/body khi chưa rõ kết quả; không tự tạo key để né conflict. HTTP thành công nhưng đọc JSON/body lỗi cũng có thể chưa rõ kết quả.
2. **BOQ đổi tệp/sheet vẫn dùng form cũ.** `620–640`: không file/sheet request generation; response cũ có thể kéo selector/preview về tệp hoặc sheet cũ. Đổi sheet640 đặt `xem=null` nhưng form Nhập cũ vẫn ở DOM; nút662 dùng closure `xv.sheet` cũ khi preview mới pending. Cần ticket cho file/sheet selection, latest-preview wins/error-fence, vô hiệu form Nhập ngay khi lựa chọn đổi; không import sheet A trong lúc selector B. Giữ ô raw/map/header đúng preview đang chọn.
3. **Form selection chưa được fence.** `fence:48–50` chỉ role/HĐ/đợt. Save tham số A pending → mở Sửa B503 → success A519 có thể đóng/ghi đè form B. Dùng mẫu426–433 pending → đổi sample/file rồi bytes về có thể tiếp tục upload lựa chọn cũ. Dùng generation/selection context cho form/tab/parameter/file/sample/BOQ; kiểm lại sau các await trước continuation/UI/đọc form. Không dùng debounce hoặc delay để tránh race. Request đã được gửi vẫn có thể commit hợp lệ; việc đổi form chỉ ngăn continuation/lựa chọn cũ ghi đè UI mới, giữ draft mới.
4. **Role POST queue bị giữ bởi reload GET.** `app.js:1276–1283`: chờ toàn bộ reloads trước release queue; nếu một GET reload treo, ý định role mới bị chặn dù POST trước đã xong. Chỉ serialize role POST; release ownership khi POST settle, mọi reload/error completion vẫn generation-fenced. Không để old POST/error/finally mở barrier của ý định mới; không GET role cũ trong barrier. Áp cùng seam CRM/M4/M2/M5/L11; giữ M9 nguyên byte.

## 4. Bộ kiểm phải bổ sung (chỉ viết, không chạy)

- Actual pending POST và upload: đổi vai vòng A→B→A, gửi same body/key namespace mới; giải old trước new. Old completion không xóa/nhả key/inflight mới; duplicate click mới vẫn chỉ một POST; unknown result retry exact body+key. Thêm ca body JSON bị đứt sau HTTP 200.
- BOQ actual controls: chọn B trong khi A preview pending; response B trước A; chọn file khác khi GET cũ pending; old error không vẽ. Nhập bị khóa trong lúc sheet pending, positive import dùng chính sheet/header/map đang hiện.
- Save A pending rồi mở form B; response A không đóng/xóa draft B. Lấy sample pending rồi đổi sample/file: không gửi old upload. Positive current selection vẫn đi được.
- Role POST1 settle → một reload GET còn pending → role intent2; POST2 phải gửi được trước GET cũ settle. Cả hai chiều và latest-wins; late GET/error/raw blob không render/click.
- Coverage seam cần current positive không rỗng cho CRM/M4/M2/M5/L11, rồi pending-role GET barrier và late completion; không dùng `cau_hinh:false` ở mọi positive để giả đã kiểm.
- DOM giả phải xử lý đúng connected nodes/ID khi replaceChildren, không dùng stale detached element để che bug. Không bỏ qua toàn bộ `unhandledRejection`; lỗi ngoài ca phải xử lý có chủ đích, lỗi ca làm fail. Không filesystem write/delete/real network/subprocess trong Node harness; Python mới không setup dữ liệu thật.

Giữ các ca HTTP thật đã viết (không sửa/chạy), scope/current authority, draft/revision/checklist và 18 ca GUI đã mô tả. Không dựng thêm framework, auth, master hoặc API.

## 5. Kết thúc

Báo cáo ghi từng sửa và case tương ứng; self-test NOT_RUN, Root static/runtime/GUI/wheel NOT_RUN cho bản sửa tới khi có chứng cứ thực tế. Không nhận CODE_ONLY thành GUI hoặc toàn M4 PASS. Root freeze/review/kiểm sau khi native terminal; sau C ổn định sẽ giao CRM G1/G7/S6 và full Review M4 theo hàng chờ.
