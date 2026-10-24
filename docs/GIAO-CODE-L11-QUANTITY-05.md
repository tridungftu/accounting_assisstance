# L11 repair05 — shared role context across M2/M5/L11

Task `L11_QUANTITY_CODE_ONLY05`, tiếp tục cùng Claude session; tận dụng code/fence hiện có. Đây là sửa context UI trong phạm vi đã chốt, không đổi kiến trúc hoặc nghiệp vụ. Đọc `REVIEW-L11-ROOT-ACTUAL-04.md`, handoff/report04 và các public L11 contracts/cases hiện có.

CODE ONLY: không Bash/terminal/runtime/test/SQL/browser/process/launcher/MCP/network, không đọc var/.env/sourceapps/dữ liệu thật/credential; không xóa/đổi tên/di chuyển file. Không làm M9. Root tự kiểm sau actual terminal/freeze/review. Không sửa server, service, API, migration1–16, schema, fixtures20, pure readers, tests, dependency hoặc report/review/handoff cũ.

Exact writes: sửa DUY NHẤT `src/kho_tri_thuc/giao_dien/assets/app.js`; tạo mới DUY NHẤT `docs/BAO-CAO-L11-QUANTITY-05.md`. Không sửa bất kỳ hàm/khối M9 nào. Baseline04 có273 source paths, manifest `d7a2ebb6fc1013b397271ebdeb1c49aec3f4f5c4260124c8c35baf7722217add`; app.js SHA `74b1cce47d95552a130d05b7b9f2b39541dcb2fbe0ec2051d172fb4d03a5623f`;272 file nguồn còn lại phải giữ nguyên. Root binds source/controller riêng; Claude không cần và không được đọc private runtime artifacts.

## Lỗi cần sửa và mức bằng chứng

Root thực sự đổi từ LINK của L11 sang `MO_PHONG_CFO_KHO_A` bằng selector M5, rồi mở ngay L11: DOM đầu còn hàng LINK cũ trong lúc GET chờ; DOM sau hiển thị CFO_M5-only và0links/0FILE. Đây là lỗi stale display đã quan sát. Không tuyên bố đã tải thành công file trái quyền: same-file GET dưới CFO này chưa chạy.

M5 role handler app.js898–904 chỉ gọi m5XoaTrangThai; M2 handler1131–37 chỉ gọi m2XoaTrangThai; L11 handler1433–39 chỉ gọi l11XoaTrangThai. Server dùng chung phiên cookie cho cả ba. L11 hashchange1461 chỉ gọi async load, nên không xóa DOM/cache cũ ngay.14 async cases04 chỉ đổi vai qua L11 handler, chưa phủ chéo module.

Static risk chưa runtime chứng minh: pending L11 FILE/Blob được cấp dưới context trước có thể vẫn qua fence local khi đổi vai ở M5/M2, trước khi GET L11 mới bắt đầu/trả actor khác. Sửa cùng gốc context này; không gọi đó là backend authorization bypass hoặc một file leak đã xảy ra.

## Kết quả bắt buộc

1. Ở CẢ BA selector đổi vai M2/M5/L11, chụp login được chọn rồi invalidate/clear đồng bộ context actor của CẢ BA module trước role POST và trước await đầu tiên: epochs, lựa chọn/form, raw/detail/proof/preview/link/FILE panels và continuation đang chờ. Tái dùng các clear/fence sẵn có hoặc helper chung gọn; không xây framework/auth policy mới. Không xóa lịch sử/receipt/file hoặc reset nghiệp vụ.
2. Không trông vào hash navigation, GET sau cùng hoặc actor comparison muộn để xóa cache. Khi chuyển về module khác đang load,0hàng/nút/dữ liệu nhạy cảm của vai trước ngay lập tức; response cũ dù đến sau cũng không restore cache, render/reset form, toast/status hoặc auto-download.
3. L11 operation giữ original epoch/actor/form/pair/basis/generation qua POST→ownGET→headers→Blob→click như04. Role change qua M5 hoặc M2 phải hủy chính continuation đó; không re-arm bằng context hiện tại. M2/M5 async đọc/raw/capture/detail/FILE cũng phải mất hiệu lực khi đổi vai ở module ngang hàng.
4. Hai thao tác đổi vai liên tiếp qua các selector khác nhau phải có current-operation gate rõ: response/lỗi cũ không ghi đè context mới; UI lấy actual actor từ server response, không tự cấp actor/PN/quyền. Có thể dùng cơ chế serialize/gate gọn phù hợp code hiện có; không đổi giao thức/server. Luồng lỗi/mất kết nối không khẳng định server đã hay chưa đổi vai, không hồi sinh cache cũ.
5. Giữ positive ordinary refresh, newerGET-wins, form/pair fences, current idempotency keys và actual FILE nonempty download đúng vai/basis. Không đổi số lượng/proof/CAS/mapping/route/file format hoặc nội dung source-only FILE. Chỉ sửa M2/M5/L11 context UI; không sửa M9 functions, không UI redesign trong gói này.

## Root kiểm sau bàn giao

- Chạy lại14 async handler cases04 trên hash mới; thêm actual M5/M2 role-handler barriers khi L11 đã có dữ liệu hoặc đang POST/ownGET/headers/Blob pending. Đòi immediate0stale DOM/FILE buttons và0late click/toast/status/render, không chỉ0download.
- Đổi vai L11 cũng phải clear cache M2/M5 đang ẩn; hai response role đến hai thứ tự không restore context cũ. Có đối chứng actual FILE click/bytes dương trong context không đổi.
- Reproduce cross-module stale DOM bằng browser thật và đọc trạng thái mới theo vai hiện hành. Backend current-rights/same-file GET là kiểm riêng, không lấy hidden button thay denial.
- Claude không chạy các kiểm trên trong CODE ONLY. Report05 ghi exact diff/giới hạn/selftests UNRUN, không bịa PASS và không tuyên bố toàn GUI/L11/M2/M5/file33 hoàn tất. Không cần đổi test/product file khác để tạo báo cáo.
