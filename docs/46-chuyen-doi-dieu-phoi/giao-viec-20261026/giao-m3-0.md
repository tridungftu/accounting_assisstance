# M3-0: M3 · Hóa đơn bán ra & doanh thu BĐS, mô hình dữ liệu + bản nháp phiếu cổng A (CD-013, CD-014). Chỉ soạn tài liệu, không code.

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không xóa file. Không đọc kho thật hay tệp bí mật.
- Làm trong worktree hiện tại, nhánh `lat/m3-0`, dựng từ hợp nhất.

**Đọc:**
- `D:\Claude\Phan mem ho tro ke toan\THIET-KE-MODULE-DE-CHOT-2026-10-20\M3-HOA-DON-BAN-VA-DOANH-THU-v2-20261026.md` (toàn bộ; **mục 16 thắng**).
- Hộp thư `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md`: CD-013, CD-014.
- CRM đã có: hợp đồng/phiên bản, lịch nghĩa vụ thu, mốc dự án có ngày dự kiến/thực tế (CD-006/007). Xem `src/kho_tri_thuc/k2/sql_crm*.py` (đặc biệt phần mốc dự án, M0035) và `k2/crm*.py`.
- M2 (hóa đơn), M1 (đợt thu): xem `k2/hoa_don.py`, `docs\46-chuyen-doi-dieu-phoi\4-KE-HOACH-LEAD.md` mục M3.
- Chuẩn giao diện lưới icon hai cấp: `docs\46-chuyen-doi-dieu-phoi\PHIEU-CONG-A-BAO-GIA-LAN-2.md` (mẫu phiếu).

**Viết `docs\46-chuyen-doi-dieu-phoi\THIET-KE-M3-DU-LIEU.md` (≤ 3 trang):**
1. **Thực thể và trường**, kèm nguồn (CRM/M1/M2/biên bản/policy), phiên bản, khóa ổn định:
   - hợp đồng-cơ sở (giá trị trước VAT, giá đất được trừ, phần chịu thuế, VAT, tổng; currency);
   - liên kết hóa đơn–hợp đồng;
   - đợt thu (mã đợt, 2 lớp trường theo §7.2 và §16 #5);
   - sự kiện bàn giao (biên bản tải lên CRM theo hợp đồng/lô);
   - tham số phân bổ;
   - "hình thức doanh thu" (ghi nhận luôn / phân bổ), là policy theo loại hình.
2. **Lớp ghi nhận và máy chuyển lớp theo mốc (CD-014):**
   - Các lớp: Đặt cọc · Người mua trả trước · Phải thu chưa đến hạn/đến hạn · Doanh thu chờ phân bổ · Doanh thu đã ghi nhận · Đã đảo/điều chỉnh.
   - Bảng "mốc → nguồn quyết định → lớp trước → lớp sau" là **dữ liệu cấu hình**.
   - Mốc dùng lại ngày dự kiến/thực tế của mốc dự án; thiếu nguồn quyết định thì không chuyển lớp, hồ sơ chờ.
   - **Bảng mốc cụ thể: để mục "chờ mục 17 của thiết kế v2"**, chỉ nêu cấu trúc cột. Không tự điền mốc.
3. Ba đẳng thức §6: dữ liệu vào, cách báo lệch, không tự sửa.
4. **Không có số tài khoản** trong mô hình (CD-014). Ánh xạ lớp → tài khoản là bảng policy do kế toán trưởng điền, ở bước sau.
5. Điểm [CHỜ CHỐT] #7, #8, #10, #11, #12: chỗ nào trong mô hình bị ảnh hưởng và giá trị tạm khi chưa chốt (PENDING, không đoán).

**Viết `docs\46-chuyen-doi-dieu-phoi\PHIEU-CONG-A-M3.md` (bản nháp để lead hoàn thiện khi có bảng mốc), theo mẫu phiếu Báo giá:**
- Lưới icon M3: Hóa đơn bán · Hợp đồng/bàn giao · Đợt thu KCN · Tham số phân bổ · Đề xuất/duyệt · Lịch sử; số đỏ là việc chờ.
- Màn danh sách và chi tiết hóa đơn–hợp đồng, có ba đẳng thức.
- Màn đợt thu KCN 4 trường: pháp nhân · số tiền trước VAT · ngày bàn giao mặt bằng · ngày kết thúc thuê.
- Hiển thị chuyển lớp theo CD-014: mốc · ngày · căn cứ · lớp trước → lớp sau · giá trị.
- Ô "Anh sửa bảng mốc" (để trống chờ §17).

Dùng tiếng Việt nghiệp vụ, ngày dd/mm/yyyy, tiền có đơn vị, **chỉ dữ liệu giả DEMO**.

**Báo cáo (≤ ¼ trang):** số thực thể, các điểm mâu thuẫn tìm thấy giữa v2 và code CRM hiện có, thông điệp commit `[M3-0] …`.
