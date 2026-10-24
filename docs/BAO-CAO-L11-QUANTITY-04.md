# BÁO CÁO L11 QUANTITY — REPAIR04 (CODE_ONLY)

- **Căn cứ:** `docs/GIAO-CODE-L11-QUANTITY-04.md`, `REVIEW-L11-ROOT-ACTUAL-03.md`, `REVIEW-L11-HTTP-UI-03.md`, report03.
- **Chế độ:** CODE_ONLY. Không chạy lệnh/test/SQL/browser/process/network. Không đọc var/.env/.git/sourceapps/dữ liệu thật/credentials. Không xóa, đổi tên hay di chuyển tệp. Không sửa migration/fixture/M9.
- **Selftests:** mọi selftest **UNRUN**. Không tuyên bố PASS native/async/GUI và không tuyên bố module hoàn tất.

## 1. Tệp

Chỉ hai tệp được sửa:

- `src/kho_tri_thuc/giao_dien/assets/app.js`
- `tests/test_l11_k2.py`

Tạo mới tệp `docs/BAO-CAO-L11-QUANTITY-04.md` (chính báo cáo này). Không sửa tệp nào khác.

## 2. UI03-1 — refresh sở hữu bởi thao tác kiểm ngữ cảnh gốc TRƯỚC hiệu ứng DOM

**`l11Load(conGoc = null)` (app.js ~`1421`):**

- Thêm tham số `conGoc` là ngữ cảnh gốc của thao tác sở hữu lần làm mới. Hàm tính `conHop()` gồm ba điều kiện:
  - role epoch vẫn như lúc bắt đầu GET;
  - vé thế hệ của chính GET vẫn là mới nhất;
  - `conGoc()` còn đúng, nếu có.
- `conHop()` được kiểm ngay khi phản hồi về, **trước** các việc: gán `l11`, xóa xem trước, `l11Render()` (dựng lại picker cặp/lượng, `l11RenderCap`), status.
- Nếu `conHop()` sai thì phản hồi không gây hiệu ứng nào: lựa chọn, ô nhập và xem trước mới của người dùng được giữ nguyên.
- `catch` cũng chỉ ghi status khi `conHop()` còn đúng.

**`l11Act` (~`1205`):** gọi `l11Load(ctx)`. `ctx` = epoch gốc + vai gốc + predicate do người gọi chụp:

| Thao tác | Predicate |
|---|---|
| FILE | form epoch + liên kết + `co_so_sha256` lúc bấm (repair03) |
| Xác nhận | form epoch |
| Còn lại | mặc định `true` |

- Thao tác đã mất hiệu lực (đổi cặp/lượng/form trong lúc GET chờ) thì không vẽ phản hồi, không status/toast cũ, không tải file.
- Fence trả về vẫn là `ctx() && ve === l11Gen` để giữ cho headers, Blob và click như 03.

**Giữ nguyên:**

- Làm mới thường (nút ↻, `hashchange`, đổi vai) gọi `l11Load()` không có `conGoc`, nên vẫn vẽ như cũ.
- GET mới hơn thắng giữ như cũ (so vé thế hệ).
- Fence đổi vai trước POST/GET/headers/Blob giữ như cũ; lỗi muộn không đẩy sang vai/lựa chọn mới.
- Luồng FILE dương hợp lệ: ngữ cảnh còn đúng thì làm mới vẽ bình thường, rồi tải dưới fence gốc.

**Giới hạn:**

- Khi ngữ cảnh đã mất hiệu lực, `l11` giữ snapshot trước đó. Người dùng bấm ↻ (làm mới riêng, hợp lệ) để lấy trạng thái mới.
- Hành vi DOM này chưa được kiểm bằng handler thật/trình duyệt (**UNRUN**). Test chuỗi asset không đóng ca này.

## 3. Q09-TEST-1 — chọn đúng tuyến HIỆN HÀNH của đúng dòng nguồn

**`L11Q09TuyenXacNhanPg.tuyen_hien_hanh(ct)` (mới):** đọc DTO thật `HoaDonK2.chi_tiet`:

1. `cau_noi`: phải có đúng một phần tử có `id` = cầu nối đang thử. Lấy `source_dong_id` của nó.
2. `tuyen`: lọc `source_dong_id` khớp, `hien_hanh = true`, `trang_thai = 'DA_DUYET'`. Phải còn **đúng một** tuyến, nếu không thì fail rõ là lỗi dựng test, không phải kết quả race.

**Các chỗ sử dụng:**

- `route_body` dùng ID đó cho `expected_route_id`, không còn `tuyen[0]`. Nguyên nhân lỗi: DTO sắp `ORDER BY source_dong_id, phien_ban`, nên sau KHO→CHI_PHI thì `tuyen[0]` là bản lịch sử cũ.
- `expected_graph` vẫn lấy nguyên từ DTO, không tự tính token.
- `route_tuan_tu` (bước tuần tự riêng, token mới) assert thành công thật: `lap_lai = false`, đích đúng, `predecessor_route_id` = tuyến hiện hành đã chọn. Sau đó DTO phải còn đúng một tuyến hiện hành, chính là tuyến vừa tạo, với đích yêu cầu.
- q02 và q03 assert tiền điều kiện tuyến hiện hành = KHO trước race. Nếu việc khôi phục KHO của q02 không thành công, q03 fail ở tiền điều kiện thay vì chạy race trên trạng thái sai.

**Không đổi:**

- Hai phiên app thật, giao dịch mở và UDF trả về trước COMMIT.
- `pg_blocking_pids` đúng PID kẻ thắng; watchdog (lock_timeout + join timeout).
- Mã từ chối exact: q02 `L11_VERSION_CHANGED` với 0 child/parent/biên nhận; q03 `L11_CLOSURE_MO_RONG` với 0 tuyến mới.
- Bước tuần tự tách riêng khỏi kết quả đồng thời.
- Không nới CAS/guard, không đổi race thành tuần tự.

## 4. Chưa chạy / chưa có

- **K2 suite:** toàn bộ UNRUN, kể cả q02/q03 sau sửa.
- **Root kiểm lại:** 14 async cases, Q09 và các luồng liên quan trên hash cuối.
- **Vẫn thiếu như report03 §8:**
  - causal revoke↔confirm và undo-held↔confirm;
  - hai batch đồng thời / late-visible identity / cùng gốc LINE mới / multipool;
  - A→B→A có liên kết sống;
  - ngưng login / kỳ khóa;
  - GUI thật và cells FILE.
- **Test cũ ngoài phạm vi vẫn đổi kết quả** như các báo cáo trước.
