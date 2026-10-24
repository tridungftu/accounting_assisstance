# L11 quantity03 — kiểm độc lập trên bản cố định

Ngày 20/10/2026 (Asia/Saigon). Đây là kết quả kiểm hữu hạn bằng DEMO, chưa phải nghiệm thu toàn M2/M5/L11 hoặc file33.

Claude session giữ nguyên `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`, đợt code03 đã kết thúc exit0. Bản cố định có 273 file nguồn, 5 file thay đổi trong phạm vi cho phép; không thêm/xóa file nguồn, không drift fixture hoặc 259 file được bảo vệ. Manifest SHA256 `09d6589358501f7feea479c0e277bdfde008cdd02d1328c78bce0bba8447914e`.

Root đã đọc toàn bộ 5 diff và báo cáo; các reviewer độc lập đã đối chiếu sửa khóa R1, native length R2 và UI. Hai sửa khóa đã khép ở mức static: namespace của toàn batch lấy trước khi tạo/resolve identities và canonical roots; helper/revoke đọc lại exact child closure trước khi lấy pool locks. Native length được kiểm với actual source capture trước approval, lưu bất biến và kiểm lại khi encoding. Đây chưa thay cho kiểm giao dịch đồng thời toàn phần.

## Runtime độc lập đã chạy

| Phần | Kết quả | Giới hạn |
|---|---|---|
| L11 migration | 14/14 PASS, 0 skip | Bao gồm lỗi oracle cũ đã sửa đúng mã; không phải chứng minh mọi lịch giao dịch |
| L11 HTTP | 2/2 PASS, 0 skip | Luồng API hữu hạn, không phải kiểm trình duyệt |
| L11 K2 | 21/23 PASS, 1 error + 1 fail, 0 skip | Q09 reset tuyến bị lỗi chọn lịch sử; ca sau bị phụ thuộc trạng thái chưa phục hồi |
| M2 K2 regression | 18/18 PASS, 0 skip | Tập hiện có |
| M2 HTTP regression | 3/3 PASS, 0 skip | Tập hiện có |
| M5 K2 regression | 36/36 PASS, 0 skip | Tập hiện có |
| Nâng bản 15→16 | Hai child riêng exit0; dữ liệu 15 không rỗng, old projection/sequence/files giữ nguyên | Post-upgrade app replay và GUI chưa kiểm trong phép nâng bản này |
| Async JS độc lập | 12/14 PASS, 2 FAIL, 0 setup error | Actual L11 handlers trong VM/DOM adapter; không phải browser/HTTP/XLSX acceptance |

Mỗi bộ native và regression chạy trên PostgreSQL DEMO mới, giữ database/role/file; guard không xóa file bật; toàn 273 file nguồn được kiểm hash trước/sau và không đổi. Không thay kho thật SQLite, không xử lý M9.

## Việc phải sửa

**UI03-1, P2 — phản hồi refresh cũ ghi đè lựa chọn mới.** Actual FILE handler đã chặn tải file khi role/pair/form/basis/generation thay đổi, kể cả khi headers hoặc Blob đang chờ. Tuy nhiên `l11Act` chờ `l11Load()`; `l11Load` chỉ kiểm epoch/gen rồi render/reset picker trước khi `l11Act` kiểm predicate gốc. Khi đổi pair hoặc nhập amount trong lúc GET refresh chờ, response cũ vẫn render. Hai ca độc lập xác nhận điều này với 0 download clicks/0 object URLs; không mô tả nhầm thành lỗi tải nhầm file. Cần kiểm nguyên operation context trước mọi DOM/status/toast side effect của refresh gắn với operation; vẫn giữ refresh thông thường và refresh sau thao tác hợp lệ.

**Q09-TEST-1 — chọn tuyến lịch sử trong test.** `L11Q09TuyenXacNhanPg.route_body()` lấy `ct["tuyen"][0]["id"]`. Sau route KHO→CHI_PHI, reset tuần tự về KHO dùng ID cũ, bị `M2_ROUTE_STALE`. Ca q03 tiếp theo vì thế nhận `L11_TUYEN_KHONG_PHAI_KHO`/`L11_POOL_HOA_DON_BI_CHAN` trước khi chạy race. Chưa tính hai ca này đạt; chưa coi lỗi dựng test là bằng chứng race sản phẩm sai. Phải lấy đúng current route của source line cần thử, không dựa thứ tự mảng hoặc nới CAS/guard. Giữ đối chứng thực sự hai ordinary sessions, UDF return trước commit, actual `pg_blocking_pids`, mã từ chối exact, và bước tuần tự riêng.

## Còn phải kiểm

C1 nonidentity native→pool, C2 coverage/errors với whole-row auditors, causal route/proof-revoke/undo-held hai thứ tự, batch namespace concurrency, GUI thật và FILE bytes/cells/current-rights vẫn cần bằng chứng riêng. Kiểm thu hồi quyền/current source, ABA/held và multi-pool phải giữ đúng mức đã kiểm, không lấy một lát DEMO làm toàn module hoàn tất. Không sửa lại báo cáo cũ thành PASS và không xóa attempt thất bại.
