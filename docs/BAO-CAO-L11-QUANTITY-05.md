# BÁO CÁO L11 QUANTITY — REPAIR05 (CODE_ONLY)

**Căn cứ:**
- `docs/GIAO-CODE-L11-QUANTITY-05.md`
- `docs/REVIEW-L11-ROOT-ACTUAL-04.md`
- handoff/report04

**Chế độ:** CODE_ONLY.
- Không chạy lệnh/test/SQL/browser/process/network, không MCP.
- Không đọc var/.env/.git/sourceapps/dữ liệu thật/credentials.
- Không xóa, đổi tên hay di chuyển tệp. Không sửa migration, fixture, M9, server, service hay test.
- Mọi selftest/kiểm tra **UNRUN**. Không tuyên bố PASS, và không tuyên bố hoàn tất GUI/L11/M2/M5/file33.

## 1. Tệp

- **Sửa duy nhất** `src/kho_tri_thuc/giao_dien/assets/app.js`.
- **Tạo duy nhất** `docs/BAO-CAO-L11-QUANTITY-05.md`.
- Không chạm hàm/khối M9 hay CRM. Không đổi nội dung các hàm xóa trạng thái có sẵn (`m5XoaTrangThai`, `m2XoaTrangThai`, `l11XoaTrangThai`); chỉ gọi lại chúng.

## 2. Thay đổi

### 2.1. Helper chung (khối L11, ngay sau `l11XoaTrangThai`)

**`doiVaiChung()`:**
- Tăng `vaiGen`, rồi gọi **đồng bộ** `m5XoaTrangThai()`, `m2XoaTrangThai()`, `l11XoaTrangThai()`.
- Kết quả trên cả ba module: epoch tăng, form epoch tăng (M5/M2 qua `XoaForm`, L11 trực tiếp), cache/lựa chọn bị xóa, các panel raw/chi tiết/nguồn/mapping/ứng viên/bằng chứng/dòng/cặp/xem trước/liên kết/nút FILE được làm rỗng, và hiện "Đang tải…".

**`doiVaiTuanTu(gui, statusId, tai)`:**
1. Gọi `doiVaiChung()` **trước await đầu tiên**.
2. Nối vào chuỗi `vaiCho`, để POST đổi vai từ mọi selector chạy tuần tự, không chồng chéo trên phiên cookie chung.
3. Chờ lần đổi vai trước kết thúc. Nếu trong lúc đó đã có lần đổi vai mới hơn (`vaiGen` khác) thì **không gửi** POST cũ.
4. Sau POST, chỉ lần đổi vai mới nhất mới toast và tải lại module của nó.
5. Nhánh lỗi/mất kết nối:
   - Không khẳng định máy chủ đã hay chưa đổi vai.
   - Nếu vẫn là lần mới nhất: toast/status lỗi, rồi đọc lại vai **thật** từ máy chủ qua GET của module.
   - Cache cũ đã xóa nên không bị hồi sinh.
6. `finally` mở cổng cho lần kế tiếp.

### 2.2. Ba selector dùng helper chung

| Selector | POST | Ô status | Tải lại |
|---|---|---|---|
| `m5-doi-vai` | `m5Post("danh-tinh")` | `m5-status` | `m5Load` |
| `m2-doi-vai` | `m2Post("danh-tinh")` | `m2-status` | `m2Load` |
| `l11-doi-vai` | `l11Post("l11/danh-tinh")` | `l11-status` | `l11Load` |

- Login được chụp đồng bộ lúc click.
- Body/giao thức máy chủ không đổi. UI không tự cấp actor/PN/quyền; vai hiển thị lấy từ GET của máy chủ.

## 3. Vì sao đóng các yêu cầu

- **Yêu cầu 1–2:** đổi vai ở M5 hoặc M2 nay xóa ngay DOM/cache L11, và ngược lại.
  - Mở L11 sau khi đổi vai ở M5 sẽ thấy "Đang tải…", 0 hàng/nút LINK/FILE cũ trong lúc GET chờ. Không còn trông vào hashchange, GET sau cùng hay so actor muộn.
  - Phản hồi cũ đến sau bị chặn bởi epoch (M5/M2/L11), thế hệ GET (`m2DocGen`, `m2CtGen`, `l11Gen`) và vai gốc. Nó không gán cache, không render/reset form, không toast/status.
- **Yêu cầu 3:** continuation L11 (POST → GET riêng → headers → Blob → click) giữ fence gốc như 04: `ep === l11Epoch && actor === l11Actor() && predicate form/cặp/basis && vé === l11Gen`.
  - Đổi vai ở M5/M2 tăng `l11Epoch` và đặt `l11 = null`, nên fence của chính continuation đó sai.
  - Kết quả: 0 click/toast/status. Không có đường nào re-arm bằng ngữ cảnh hiện tại.
  - Tương tự, tác vụ M5 (`m5Tai` raw/file, detail, nhận tệp) và M2 (`m2Tai`, detail, nhận) mất hiệu lực khi đổi vai ở module ngang hàng, vì epoch của chúng được tăng.
- **Yêu cầu 4:** hai lần đổi vai liên tiếp qua hai selector khác nhau được serialize. Lần cũ chưa gửi thì bị bỏ; đã gửi thì phản hồi/lỗi của nó không ghi đè.
- **Yêu cầu 5 — giữ nguyên:**
  - làm mới thường, GET mới hơn thắng, fence form/cặp, khóa idempotency hiện hành;
  - luồng FILE hợp lệ khi ngữ cảnh không đổi;
  - lượng/proof/CAS/mapping/tuyến/định dạng file.
- **Không phải** sửa lỗ hổng phân quyền backend. Không tuyên bố đã có file rò rỉ; quyền hiện hành phía máy chủ vẫn là kiểm riêng.

## 4. Giới hạn

- Selector CRM (`crm-doi-vai`) và M9 (`m9-doi-vai`) cũng dùng phiên chung nhưng **không** được sửa (gói này loại M9, chỉ phạm vi M2/M5/L11). Đổi vai qua hai selector đó chưa xóa cache M2/M5/L11. Ghi nhận là giới hạn đã biết, cần quyết định riêng.
- Chuỗi `vaiCho` chỉ tuần tự trong một tab trình duyệt. Hai tab dùng chung cookie vẫn có thể đổi vai chéo; khi đó vai hiển thị theo GET của máy chủ.
- Khi ngữ cảnh mất hiệu lực, panel giữ trạng thái rỗng tới khi module tải lại (điều hướng/↻). Đây là chủ ý: không hiển thị dữ liệu vai cũ.

## 5. Chưa chạy (root kiểm sau)

- 14 async handler cases của 04 trên hash mới.
- Barrier vai M5/M2 khi L11 đã có dữ liệu hoặc đang POST/GET riêng/headers/Blob.
- Đổi vai L11 xóa cache M2/M5 đang ẩn.
- Hai phản hồi đổi vai hai thứ tự; đối chứng FILE click/bytes dương khi ngữ cảnh không đổi.
- Browser thật cho stale DOM chéo module; backend same-file GET dưới vai mới.

Tất cả **UNRUN**.
