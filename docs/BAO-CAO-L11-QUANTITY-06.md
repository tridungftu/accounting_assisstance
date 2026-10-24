# BÁO CÁO L11 QUANTITY — REPAIR06 (CODE_ONLY)

**Căn cứ:** `docs/GIAO-CODE-L11-QUANTITY-06.md`, `docs/REVIEW-L11-ROOT-ACTUAL-05.md`, report05.

**Chế độ CODE_ONLY:**
- Không chạy lệnh/process/Node/Python/browser/test/SQL/network.
- Không đọc var/.env/.git/sourceapps/dữ liệu thật/credentials.
- Không xóa/đổi tên/di chuyển/reset tệp.
- Mọi self-test **UNRUN**; không tuyên bố đã kiểm hay nghiệm thu.

## 1. Tệp

- Sửa duy nhất `src/kho_tri_thuc/giao_dien/assets/app.js`.
- Tạo duy nhất `docs/BAO-CAO-L11-QUANTITY-06.md`.
- Không chạm M9/CRM, backend, SQL, service, tests, fixtures.

## 2. Đoạn sửa (app.js)

1. **Khai báo trạng thái chung trước khối M5** (`vaiGen`, `vaiCho`, `vaiChan`, `vaiChoTai`). Lý do: `m5Load`/`m2Load`/`l11Load` có thể chạy ngay khi khởi tạo trang (hash). Khai báo muộn sẽ gây TDZ. Dòng `let vaiGen…` cũ ở khối L11 được thay bằng ghi chú.
2. **`doiVaiChung()`:** ngoài việc tăng `vaiGen` và xóa đồng bộ M5/M2/L11 (giữ như 05), đặt thêm `vaiChan = vaiGen`. Barrier thuộc **ý định mới nhất**, dựng trong cùng tick với click, trước mọi await.
3. **`vaiDangChan(ten)`:** khi barrier đang chặn, ghi tên module vào `vaiChoTai` và trả `true`. Không await gì.
4. **`moChanVaNap(ve, khoiTao)`:** chỉ chạy khi `ve === vaiGen && vaiChan === ve`. Khi đó:
   - mở barrier (`vaiChan = 0`) **trước**, rồi gọi loader;
   - nạp lại module khởi tạo + mọi module đã xin nạp trong lúc chặn.
5. **`doiVaiTuanTu(gui, statusId, khoiTao)`:** nhận tên module khởi tạo (`"m5"`/`"m2"`/`"l11"`) thay vì callback loader. Thành công hay lỗi của ý định mới nhất đều đi qua `moChanVaNap`.
6. **Loader:**
   - `m5Load` và `m2Load`: dòng đầu `if (vaiDangChan(...)) return;`.
   - `l11Load`: `if (vaiDangChan("l11")) return ++l11Gen;`. Vẫn cấp vé thế hệ mới để vô hiệu GET/continuation cũ hơn. Thao tác sở hữu nhận vé này nhưng fence gốc đã sai (epoch/vai đổi), nên không render/tải.
7. **Ba selector `m5/m2/l11-doi-vai`** gọi `doiVaiTuanTu(..., "m5"|"m2"|"l11")`. Login vẫn được chụp đồng bộ lúc click.

## 3. Vòng đời

**Click đổi vai (bất kỳ selector):** chạy đồng bộ các bước sau:
1. Tăng `vaiGen`.
2. Đặt `vaiChan`.
3. Xóa cache/DOM/epoch/form của cả ba module.
4. Nối vào chuỗi POST tuần tự `vaiCho`.

**Trong lúc chờ:**
- Mọi điều hướng (hashchange), nút ↻, refresh sau thao tác và "Lọc" của M2/M5/L11 **không gửi GET**. Do đó máy chủ chưa xử lý xong POST không thể trả vai cũ để khôi phục cache/DOM.
- Màn hình giữ trạng thái đã xóa ("Đang tải…"): 0 hàng/nút LINK/FILE của vai trước.
- GET/continuation khởi tạo **trước** click vẫn bị chặn bởi epoch/thế hệ/vai gốc như 03–05.

**Chuỗi nhiều ý định:**
- Ý định cũ chưa gửi: thấy `ve !== vaiGen` thì không gửi.
- Ý định cũ đã gửi: phản hồi/lỗi của nó thấy `ve !== vaiGen` thì không toast, không mở barrier, không load.
- `finally` cũ chỉ nhả chuỗi `vaiCho` để POST mới nhất được gửi, **không** chạm barrier.
- Barrier luôn thuộc ý định mới nhất.

**Ý định mới nhất thành công:**
1. Toast.
2. `moChanVaNap` mở barrier.
3. Nạp lại module khởi tạo + các module đã xin nạp (vd người dùng đã chuyển sang L11 trong lúc chờ), đọc vai **thật** do máy chủ trả.
- Module chưa xin nạp đã bị xóa cache; khi được mở sẽ nạp bình thường (barrier đã mở).

**Ý định mới nhất lỗi / mất kết nối:**
- Toast/status lỗi.
- Không khẳng định máy chủ đã hay chưa đổi vai.
- Mở barrier và nạp lại như trên để hiển thị vai thật hiện hành. Cache cũ không hồi sinh; giao diện dùng tiếp được.

**Không deadlock:**
- Loader trong barrier trả ngay, không chờ promise đổi vai.
- `moChanVaNap` mở barrier trước khi gọi loader, nên loader không chờ chính lần đổi vai của nó.
- Chuỗi `vaiCho` luôn được nhả ở `finally`.

**Action/FILE đang chờ:**
- Giữ fence gốc như 04/05: epoch + vai + form/cặp/basis + vé thế hệ, qua POST → GET riêng → headers → Blob → click.
- Đổi vai làm fence sai, nên 0 render/toast/status/tải. Không re-arm bằng ngữ cảnh mới.

**Không đổi:**
- Kiểm quyền máy chủ, token/version/capacity/CAS, khóa idempotency.
- Luồng FILE hợp lệ khi không đổi vai; làm mới thường khi không có đổi vai pending.

## 4. Giới hạn

- Selector CRM và M9 dùng chung phiên nhưng ngoài phạm vi (không sửa M9/CRM). Đổi vai qua chúng không dựng barrier và không xóa M2/M5/L11.
- Barrier chỉ trong một tab. Tab khác cùng cookie đổi vai thì tab này chỉ biết qua GET kế tiếp.
- Trong lúc barrier, các thao tác đọc phụ không qua loader (raw/chi tiết) không có nút hiển thị vì DOM đã xóa. Chúng không được gắn barrier riêng.
- Nếu POST đổi vai treo không trả (không lỗi, không timeout phía trình duyệt), barrier giữ đến khi request kết thúc. Không thêm timeout phía client trong gói này.

## 5. Chưa chạy

Tất cả **UNRUN**:
- Bộ 23 ca của 05 (gồm 9 tổ hợp selector × module khi POST pending).
- Bộ 14 ca async của 04.
- Regression liên quan, kiểm browser thật, kiểm backend same-file GET dưới vai mới.

Không tuyên bố hoàn tất L11/Q09/file33.
