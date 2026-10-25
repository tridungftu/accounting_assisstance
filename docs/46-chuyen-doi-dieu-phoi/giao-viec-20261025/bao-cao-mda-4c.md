Anh, đã hoàn tất MDA-4c trong đúng hai tệp:

- [app.js:2101](src/kho_tri_thuc/giao_dien/assets/app.js): hiển thị đủ ba trạng thái; “dự kiến dd/mm/yyyy” in nghiêng, không tô đỏ; giữ nguyên logic quá hạn.
- [khung_luoi_async.cjs:367](tests/khung_luoi_async.cjs): thêm ba ca kiểm tra chữ, ngày và không lộ `MOC_`.
- Node trước/sau: khung lưới **30/30 → 33/33**; toàn bộ **13/20 → 13/20 bộ đạt**, giữ nguyên 7 bộ lỗi nền. Hai bộ `crm_giao_ket_async`, `crm_du_an_ban_async` đều đạt.
- UTF-8 không BOM; không commit, không mở server.

Thông điệp commit đề xuất: `[MDA-4c] Hiển thị ngày dự kiến cho đợt kế tiếp gắn mốc riêng`.