Anh, đã sửa đúng **2 tệp**, UTF-8 không BOM; chưa đạt cổng “không thêm lỗi”.

- [crm_g.js](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-ky-ui/src/kho_tri_thuc/giao_dien/assets/crm_g.js:1146>): chữ/trạng thái `:1146`, ký theo DOCX `:2424`, ACK `:2509`, hash/tải tệp và nhãn G5.
- [crm_ky_ket_async.cjs:621](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-ky-ui/tests/crm_ky_ket_async.cjs:621>): thêm ca DOCX thuần, PDF tùy chọn, ACK thiếu PDF, xuất tay và G5.
- **Schema khớp máy chủ:** gửi `expected_xuat_id`, `expected_revision` trong `X-CRM-G-Info`; body là PDF **bản đã ký**. `g3` nội bộ ghim `docx_sha256`; máy chủ tự resolve hash.
- **Node trước → sau:** ký **14→16 nhóm đạt**; bốn bộ bắt buộc **4/4→3/4**; toàn bộ 20 bộ **13/20→12/20**. Giữ 7 lỗi nền; thêm lỗi selector cũ tại `crm_giao_ket_async.cjs:842` tìm “Xuất DOCX”. Không sửa tệp thứ ba.
- **Còn thiếu:** DTO G6A máy chủ chưa trả `xuat_id`/hash DOCX; nút tải DOCX hiện khi có dữ liệu.

Không commit, không mở server. Thông điệp commit: `[KY-UI] Cho ký theo DOCX, PDF tùy chọn và nhãn G5 kiểm tay`.