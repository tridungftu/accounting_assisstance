(a) **Đạt qua đọc mã:** chỉ `NULL` mới fallback; PN bật dùng kết quả ma trận, khóa G1/G7 đúng KK §2. Xem [crm_mau.py:166](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-mtq-4d1b/src/kho_tri_thuc/k2/crm_mau.py:166>), dòng 183–196, 244–249 và 466–491.

(b) **Không đủ căn cứ xác nhận toàn bộ — Nên sửa/làm rõ:** tại [crm_mau.py:213](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-mtq-4d1b/src/kho_tri_thuc/k2/crm_mau.py:213>), `SELECT v.*` lấy metadata phiên bản và tính token dù `mtq_duoc_doc=false`; Python mới từ chối ở dòng 220. Metadata **tệp**, blob và replay được chặn trước khi đọc. Chưa thấy dữ liệu bị trả ra ngoài nên chưa xếp **Chặn**.

(c) **Đạt qua đọc mã:** không đổi migration/hàm SQL hay route; câu từ chối mới bằng tiếng Việt, không lộ khóa catalog ([crm_mau.py:357](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-mtq-4d1b/src/kho_tri_thuc/k2/crm_mau.py:357>)). Có test PN A bật/B tắt tại [test_mtq_giao_ket.py:321](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-mtq-4d1b/tests/test_mtq_giao_ket.py:321>); chưa có kết quả PG.

| Kiểm tra | Kết luận |
|---|---|
| **1. Phạm vi** | Đạt: đúng hai tệp giao; fixture tổng hợp. Báo cáo khớp **17 test** (2 unit, 15 PG), ghi rõ **NOT_RUN**. |
| **2. Đúng yêu cầu** | Logic cờ/fallback đúng qua đọc mã; phần metadata ở (b) cần Claude xác nhận. |
| **3. Tiền, số liệu, quyền** | Không đổi phép tính tiền. Quyền kiểm tại service/SQL; còn điểm (b). |
| **4. Không phá phần cũ** | Chưa thấy hồi quy trong diff; không thêm engine/kết nối, bảng/cột hay truy cập chéo module mới; không gọi API AI trực tiếp. |
| **5. Giao diện/câu chữ** | Đạt trong diff: câu từ chối nghiệp vụ phù hợp; không thêm hiển thị ngày/tiền. |

`git diff --check` đạt. Không chạy test hoặc PostgreSQL; chưa xác định lỗi mới so nền. **Chưa kết luận Đạt cho lát**, còn câu hỏi dưới đây và gate PG đang chờ.

**Hỏi Claude**

- “Metadata” ở D(b) có bao gồm metadata phiên bản/token tại `crm_mau.py:213,217` không? Với PN bật, thiếu XEM, truy vấn vẫn lấy `v.*` và tính token trước khi Python từ chối; giao việc §2 chỉ nêu blob/replay nên ranh giới này chưa rõ.