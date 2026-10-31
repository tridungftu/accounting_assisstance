**Biên bản review chéo G2-31a-v2 — Kết luận: Đạt**

Nhánh `lat/g2-31a`, HEAD `f50e70c`, commit sửa vòng 2 `46dc85c`. Đối chiếu `hop-nhat-20261023...HEAD` và diff từ `796e2f0`; tập trung hai lỗi Chặn vòng trước và ảnh hưởng của bản sửa.

Đường dẫn rút gọn: SDK = `src/kho_tri_thuc/sdk_core/trinh_duyet.js`; Shell = `src/kho_tri_thuc/core/ui/index.html`; test = `tests/g2_31a.cjs`.

| Phát hiện / kết quả xác minh | Mức | `tệp:dòng` |
|---|---|---|
| **Đã đóng lỗi lộ nháp:** đổi người/pháp nhân làm bỏ nội dung nháp; `doc_nhap` kiểm người, pháp nhân và module sở hữu. Ca âm kiểm riêng từng thay đổi, đăng xuất và quay lại context cũ. | Chặn vòng 1 — **đã đóng** | SDK`:54`, `:124`, `:194`; test`:109`, `:124` |
| **Đã đóng lỗi chặn đăng xuất:** `DELETE /api/v1/phien` được miễn khóa chống trùng theo chuẩn API §3.6, vẫn yêu cầu CSRF. Test kiểm cả query string, thiếu CSRF và route/method gần giống không được hưởng ngoại lệ. | Chặn vòng 1 — **đã đóng** | SDK`:110`, `:113`; test`:258`, `:275` |
| Shell tham chiếu CSS dùng chung, renderer vẫn dựng riêng. Theo quyết định lead, chấp nhận tạm trong khi `lat/ui-1` chưa gộp; test đã đổi tên để chỉ khẳng định nhận khai báo UI-2. | **Để sau — không chặn** | Shell`:8`; SDK`:244`; test`:347`, `:401` |

**Kết quả kiểm**

- **Phạm vi: Đạt.** Diff chỉ thêm đúng ba tệp trong whitelist; không sửa asset dùng chung.
- **Yêu cầu, chuẩn và đặc tả: Đạt trong phạm vi vòng 2.** Hai lỗi được sửa đúng; các test về `/api/v1/`, CSRF, polling/Retry-After, CAS giữ nháp, bỏ phản hồi cũ và nhãn DEMO tiếp tục đạt.
- **Quyền và an toàn: Đạt trong diff.** Không có SQL/migration, đối tượng CSDL mới, thay đổi role/RLS/DEFINER/`search_path`, SQL chéo module hoặc mở rộng quyền. Kiểm login PostgreSQL thật **không áp dụng** cho lát frontend này. Không phát hiện DROP/xóa dữ liệu, đọc kho thật, gọi dịch vụ ngoài hay ghi bí mật/DSN vào log/audit.
- **Tái sử dụng: Chấp nhận theo quyết định lead.** Phần renderer UI-1 ghi Để sau như trên.
- **Test: Đạt.** Tôi chạy lại `node --test tests/g2_31a.cjs`: **37/37 đạt, 0 lỗi, 0 skip**; `git diff --check` đạt. Ca mới kiểm hành vi và số lần gọi transport, không chỉ kiểm chuỗi mã nguồn.

**Không còn điểm Chặn hoặc Cần sửa trong phạm vi vòng 2.** Chưa kiểm trực quan trên trình duyệt hoặc tích hợp backend thật. Không sửa tệp, không đọc kho thật/tệp bí mật/`*.local.json`.