# M4-01C3 — Giữ nháp qua toàn bộ lượt tải và gửi lại đúng tệp

21/10/2026 · CODE_ONLY · Tiếp tục cùng session Claude hiện có. Anh đã chốt triển khai M4 và CRM; đây là hai sửa giao diện trong phạm vi đó, không thay kiến trúc hay nghiệp vụ. Chỉ viết code/test/report; không chạy lệnh, test, SQL, browser hoặc tạo agent/session mới. Giữ mọi file và lịch sử.

## Căn cứ đã kiểm

C2 đã terminal thực tế handle19047/chunk9881f1, exit0, stop/scope confirmed. Frozen `var/codex-dieu-phoi/m4c2-runtime-frozen-ddabd91d10a5`: source352 SHA `af149b19ea39db681a63abdbd3cae3486758245167beeca9d9cffe3e655e85d5`, runtime418 SHA `14ad78af4d0f95c4c4dbf4a33e9fa87cc5bb28f49fedee72a203f250341f392f`.

Root đã chạy 16 pure tests và 6 nhóm async native, tất cả đạt, zero skip/error; hai ca độc lập về old POST ownership và reverse BOQ preview cũng đạt trên C2 thực tế. Đây là bằng chứng hữu hạn, chưa phải GUI hay toàn M4 nghiệm thu. Hai residual dưới đây được Root và peer đối chiếu actual source; diagnostic bổ sung được Root quản lý riêng. Không sửa để che hoặc bỏ ca kiểm.

B6 finite backend gate giữ nguyên. Toàn bộ full Review M4, duyệt/PDF, nghiệm thu–công nợ, Request và CRM41–42 vẫn nằm trong phạm vi đã chốt; gói sửa này không thu hẹp mục tiêu.

## Chỉ được sửa 5 file existing

- `src/kho_tri_thuc/giao_dien/assets/app.js`: chỉ nếu cần seam hẹp; giữ byte nguyên block M9.
- `src/kho_tri_thuc/m4/giao_dien/m4.js`: sửa vòng đời refresh/preview/form và upload retry.
- `tests/m4_01c_async.cjs`: mở rộng actual-handler tests cho các cửa sổ còn thiếu.
- `tests/test_m4_01c.py`: chỉ điều chỉnh assertion cấu trúc bị thay đổi; không dùng source assertion thay bằng chứng race.
- `docs/BAO-CAO-M4-01C.md`: giữ lịch sử, bổ sung C3 và trạng thái trung thực.

NEW0. Không sửa backend/HTTP/service/schema/SQL, bootstrap, pyproject, index/CSS, vendor, guard, M9, app nguồn, chứng cứ Root hoặc file khác. Không đọc dữ liệu thật, var, env, secret, cấu hình thật. Chỉ đọc source/docs đã pin trong controls.

## C2UI-01 — Guard tới tác động DOM cuối cùng

`sauLenh` kiểm `fc()` trước `await napLai(false)`; các GET bên trong `m4Nap/napHd/napDot` chỉ kiểm role/object/GET generation. Khi POST đã thành công rồi refresh GET đang chờ, người dùng có thể mở hoặc nhập form B; GET về vẫn `veHd/veDot` và làm mất nháp B. Save tham số trực tiếp, retry JSON và xử lý revision cũng phải được rà theo cùng nguyên tắc. Không khôi phục một snapshot cũ lên phần người dùng vừa nhập sau khi GET bắt đầu.

BOQ `docSheet/xemSheet` có file/sheet generation nhưng callback vẫn có thể render sau khi người dùng đổi tab và nhập form khác. Giữ nháp hoặc chặn continuation cũ tới cuối chuỗi await/DOM; chỉ kiểm trước khi gọi loader chưa đủ. Áp cho success/error/refresh/revision-restoration và preview. Đổi vai hoặc bị thu hồi quyền vẫn phải xóa dữ liệu không còn được phép; không giữ nháp trái scope. Không bỏ refresh hiện hành vô điều kiện: luồng không có sửa mới vẫn nhận dữ liệu/revision và hiển thị bình thường. Không dùng delay/debounce để né race.

## C2UI-02 — Unknown upload retry giữ nguyên intent

`layMau` tạo `new File` với timestamp mặc định, trong khi namespace của `taiLen` chứa `file.lastModified`. Nếu POST upload mẫu đã gửi nhưng kết quả/body JSON bị đứt, bấm Dùng mẫu lần nữa fetch/tạo File mới và có thể sinh key khác; bytes XLSX do máy chủ tạo lại cũng có thể khác. Không dùng timestamp cố định đơn thuần để coi đã giải quyết.

Giữ original File/bytes, metadata, operation key và continuation của lần upload chưa rõ kết quả. Cung cấp thao tác gửi lại đúng intent đã giữ, không fetch mẫu lại để retry. Tệp thật cũng phải có cùng bảo đảm. Không gửi client hash/authority mới hoặc thay server DTO. Duplicate click khi pending chỉ một POST. Giữ ownership A→B→A đã sửa ở C2; retry hoặc completion cũ không được tác động lựa chọn/vai mới. Khi kết quả rõ, hoàn tất attachment/selection đúng một lần; không chỉ upload thành công rồi bỏ mất bước gắn tệp/preview.

## Ca cần viết thêm, không chạy

1. POST A thành công → giữ refresh GET → mở và nhập form B → trả GET: B và nội dung mới còn nguyên. Bao gồm GET HĐ và GET đợt, cùng positive không sửa nháp vẫn refresh được.
2. Revision refresh bắt đầu → nhập thêm sau lúc bắt đầu → response về: giữ giá trị mới nhất, không ghi đè bằng snapshot cũ.
3. BOQ preview pending → đổi tab PL/form khác và nhập → trả response/error cũ: không dựng lại hay mất nháp mới. Current sheet/file vẫn preview/import đúng.
4. Mẫu upload nhận HTTP200 nhưng JSON đứt hoặc network chưa rõ → retry qua UI: cùng original File/bytes, cùng X-M4-Info/key, không GET mẫu lần nữa. Mock File mặc định phải tạo lastModified thay đổi như browser; không hardcode1 để che lỗi. Positive retry hoàn tất bước gắn tệp/preview một lần.
5. Giữ các ca pending ownership, JSON-cut, role queue chỉ serialize POST, latest wins, raw download scope và current-role positives của CRM/M4/M2/M5/L11. Không đổi M9.

Harness dùng actual handlers, DOM connected IDs đúng, setup assertions và kết luận quan sát được; generic exception/timeout không được coi là tái hiện lỗi. Không nuốt unhandled rejection; không filesystem write/delete, real network hay subprocess. Không thêm framework mới. Các HTTP tests đã có giữ nguyên.

## Bàn giao

Ghi rõ từng sửa và ca tương ứng, self-test NOT_RUN. Root kiểm độc lập sau native terminal/freeze. GUI/wheel/HTTP chỉ được ghi đạt khi có bằng chứng thực tế của chính lớp đó; không nhận CODE_ONLY thành module đã hoàn tất. Khi ổn định, tiếp tục CRM G1/G7/S6 và full Review M4 theo hàng chờ.
