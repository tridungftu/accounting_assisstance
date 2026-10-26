# Phần chung cho các lát MTQ-4 sau chốt QD-20261026-08 (đọc trước phần riêng của lát)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM. `pg_migrations.py` giữ LF. Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- **Chỗ chưa rõ hoặc có thể làm rộng quyền: dừng, ghi "Cần lead"; không đoán.** Môi trường không có `python` thì ghi NOT_RUN; lead chạy test và PG.
- Test PG tự tạo CSDL `kho_test_*` từ DSN quản trị, không đọc `KHO_PG_DEMO_*`. Dữ liệu giả phải đúng mọi trigger/ràng buộc thật: đọc định nghĩa trigger trước khi dựng fixture (bài học MTQ-4b1a: đối tác phải gắn pháp nhân). Không tắt trigger trừ khi bắt buộc.
- **Migration:** chỉ **thêm** migration mới, tên tạm `M00xx_<TÊN>`, có dòng đánh dấu `# <MÃ LÁT> — CD-012:`. Lead đánh số khi gộp. **Không sửa** hằng/migration cũ (M0039…M0053). Test không ghim migration cuối hay hash byte tệp.
- **Không đụng tệp của luồng khác** đang chạy song song:
  - `k2/sql_mtq_cong.py` (cổng phiên) chỉ lát luồng cổng được sửa;
  - `k2/sql_mtq_crm.py`, `m4/sql_mtq.py`, `k2/sql_mtq_lien_module.py`, `k2/sql_mtq_nen.py` mỗi tệp thuộc đúng một luồng;
  - **không sửa** `master.ktt_duoc`, `master.ktt_pn_cho_phep`, RLS nền dùng chung (thuộc chuỗi MTQ-NEN do lead giữ — A2). Cần đổi các thứ này thì ghi "Cần lead".
- **Nguyên tắc quyền:**
  - pháp nhân chưa bật ma trận → hành vi cũ không đổi một bit (CU);
  - đã bật → chỉ theo ma trận, không fallback, không `cũ OR mới`, không `cũ AND mới`;
  - đối tượng/pháp nhân không giải được → chặn;
  - giữ tách nhiệm và guard kỹ thuật (chủ bảng, bất biến, append-only);
  - không làm rộng quyền ra ngoài module hoặc pháp nhân.
- **Căn cứ chung:**
  - `docs\46-chuyen-doi-dieu-phoi\THIET-KE-MA-TRAN-THAM-QUYEN.md` §4.1, §5.1–5.3;
  - `docs\46-chuyen-doi-dieu-phoi\MTQ-4-CAN-CHOT.md` (đã chốt, QD-20261026-08);
  - bản kiểm kê của nhóm (`KK-MTQ4-CRM.md` / `KK-MTQ4-M4.md` / `KK-MTQ4-LIEN-MODULE.md`);
  - mẫu đã làm: `k2/sql_mtq_cong.py` (M0045, M0047) và review `giao-viec-20261026/review-mtq-4a3a.md`, `review-mtq-4b1a.md`.
- **Báo cáo (≤ ⅓ trang):** đã làm, "Cần lead", thông điệp commit `[<MÃ LÁT>] …`.
