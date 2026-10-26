# MTQ-5a: Ma trận thẩm quyền, seed DEMO 5 vai (CD-010 mục 4, CD-012; thiết kế MTQ-0 dòng MTQ-5a)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn và ghi "Cần Anh".
- Đọc `AGENTS.md`, `CLAUDE.md`. Ghi tệp UTF-8 không BOM.
- Sandbox không ghi được `.git`: **không commit**. Không mở server hay PostgreSQL; test PG tự skip. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-5a`, dựng từ hợp nhất. Đã có MTQ-1 = M0039 (`k2/sql_ma_tran_tham_quyen.py`). MTQ-2 (dịch vụ) chưa gộp, **không dùng**.

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\THIET-KE-MA-TRAN-THAM-QUYEN.md`: §2 (năm vai và Admin, ánh xạ cũ → mới), §7 (dòng MTQ-5a và đoạn "Mẫu DEMO đề xuất" ngay dưới bảng).
- Hộp thư `CHI-DAO-TU-ANH.md`, CD-010 mục 4 và CD-012.
- Seed DEMO hiện có: `k2/crm_demo.py`, `k2/crm_g_demo.py`, `k2/crm_kiem_demo.py` và nơi gọi chúng trong `k2/crm_khoi_dong.py`.
- Quy tắc dự án: actor mô phỏng có tiền tố `MO_PHONG_`.

**Việc:**
1. Tệp mới `src/kho_tri_thuc/k2/mtq_demo.py`: seed mẫu ma trận cho **DEMO**.
   - Tái dùng master (pháp nhân, phòng, dự án) từ các seed đã có; không tạo master thứ hai.
   - Thêm actor `MO_PHONG_MTQ_*` riêng cho 5 vai (Người thực hiện 1/2, Trưởng phòng, CFO, Người xem) và một **Admin DEMO** riêng.
   - Gán vai và phạm vi theo bảng MTQ-1.
   - Mẫu tick theo đoạn "Mẫu DEMO đề xuất":
     - Người thực hiện 1 lập/sửa; Người thực hiện 2 kiểm; Người xem chỉ xem.
     - Trưởng phòng duyệt tối đa **500.000.000 VND**; CFO duyệt không giới hạn.
     - Tick cụ thể theo màn/phòng, không cấp mọi module cho mọi vai. M9 không tick ("Tạm dừng").
   - Ghi bằng lệnh/hàm SQL MTQ-1 qua kết nối chủ bảng tin cậy, đúng cách bootstrap tin cậy MTQ-1 mô tả. Có nhật ký.
   - Ma trận ở trạng thái **đã lưu/công bố nhưng chưa bật** (bật thuộc MTQ-4).
   - Seed **một lần**: chạy lại không ghi đè và không cấp lại quyền đã thu hồi; có dấu đã seed.
   - Chỉ chạy khi DEMO, theo cùng điều kiện các seed DEMO khác đang dùng. **Không bao giờ** chạy trên dữ liệu thật.
2. `src/kho_tri_thuc/k2/crm_khoi_dong.py`: gọi seed MTQ sau các seed DEMO đang có, đúng chỗ và đúng điều kiện DEMO.
   - Seed lỗi thì ghi nhật ký và không chặn khởi động CRM, trừ khi các seed khác đang làm khác.

**Test, tệp mới `tests/test_mtq_demo.py`:**
- Phần tĩnh: không có nhánh chạy ngoài DEMO; tên actor có tiền tố `MO_PHONG_MTQ_`; hạn mức Trưởng phòng 500.000.000; CFO không giới hạn; Người xem chỉ có ô Xem; M9 không tick.
- Phần PG (`skipUnless KHO_PG_DSN_TEST`, theo cách các test PG khác tạo CSDL `kho_test_*` riêng):
  - seed lần 1 tạo đủ;
  - seed lần 2 không đổi gì (so số dòng và revision);
  - thu hồi một ô rồi seed lại thì ô vẫn bị thu hồi;
  - ma trận chưa bật;
  - có nhật ký.
- Chạy thuần: `python -X utf8 -m unittest tests.test_mtq_demo tests.test_mtq_sql`, với PYTHONPATH=`src;.;tests`.

**Tệp (≤ 3):** `k2/mtq_demo.py`, `k2/crm_khoi_dong.py`, `tests/test_mtq_demo.py`.

**Báo cáo (≤ ¼ trang):** số test, phần "Cần Anh", thông điệp commit `[MTQ-5a] …`.
