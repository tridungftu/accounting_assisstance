Anh, DA-4b đã hoàn tất trong đúng 4 tệp:

- `app.js:1702,2042`: thêm icon và ánh xạ phần Dự án đang bán.
- `style.css:123,132`: icon Lucide `building-2`, bảo đảm ẩn hàng thẻ.
- `crm_g.js:355,738,970`: mở đúng thẻ theo hash, bỏ phản hồi cũ; `#hopdong` giữ đủ 3 thẻ.
- `tests/khung_luoi_async.cjs:268,724`: kiểm 7 ô, điều hướng và phản hồi trễ.

Node trước/sau: lưới **20/20 → 22/22**; Dự án **10/10 → 10/10**; Giao kết đều đạt. Toàn bộ **12/20 → 12/20**, giữ nguyên 8 lỗi nền, **không lỗi mới**.

UTF-8 không BOM; `git diff --check` đạt. Chỉ kiểm mock DOM, chưa thử browser thật. Không commit.

Thông điệp đề xuất: `[DA-4b] Mở trực tiếp Dự án đang bán từ lưới CRM`.