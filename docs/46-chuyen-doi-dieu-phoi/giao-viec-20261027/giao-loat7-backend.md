# Loạt 7 — backend cho CD-022/023/024: DA-B1, TEN-B1, BG-B1

## Phần chung

- Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM; `pg_migrations.py` giữ LF. **Ghi tệp bằng apply_patch, không qua chuỗi PowerShell nháy kép**; tự kiểm `AS $$`/`$$`.
- Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ: dừng, ghi "Cần lead". Không có `python` thì NOT_RUN; lead chạy test/PG.
- Test PG tự tạo `kho_test_*` (`skipUnless KHO_PG_DSN_TEST`); chỉ dùng quyền setup cho DDL/fixture; **ca nghiệp vụ chạy dưới vai ứng dụng thật** (`app_web` + danh tính phiên), không đóng giả bằng admin. Dữ liệu giả đúng trigger. Chạy được dưới guard giữ tệp. Không kiểm CRLF/LF.
- Migration: chỉ thêm `M00xx_*` với dấu `# <MÃ LÁT> — CD-02x:`. **Không tự đặt số**; không sửa migration cũ (tới M0064); test không ghim migration cuối.
- QD-20261026-09: thêm dòng, không tạo bảng/cột theo từng lần. CD-018/021: phân quyền pháp nhân hai lớp (máy chủ + RLS/hàm), không SQL thẳng bảng module khác.

**Căn cứ bắt buộc đọc:**
- `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` mục **CD-022, CD-023, CD-024** (Anh đã chốt);
- `docs\46-chuyen-doi-dieu-phoi\KK-UI-DA-BG.md` (§1–§4 hiện trạng/đề xuất, §5 dòng của lát, §7);
- `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261027\tra-loi-lead-kk-ui-da-bg.md` (quyết định lead).

**Lưu ý:** KK được viết trên nhánh giao diện `lat/ui-dem`. Số dòng ở nhánh hợp nhất có thể lệch — đọc mã hiện tại để định vị.

## DA-B1 · Dự án đang bán: lệnh lưu một lượt (CD-022 mục 1–3, CD-023 mục 1, 4)

**Tệp (3):** `k2/sql_crm_du_an_mot_luot.py` mới; `ha_tang/pg_migrations.py` (`M00xx_CRM_DA_MOT_LUOT`); `tests/test_crm_du_an_mot_luot_pg.py` mới.

**Việc** (theo KK §5 dòng 1 và §4):
- Lệnh SQL **lưu một lượt** cả dự án (thông tin chung, giá & thuế, phí, mốc riêng, tiến độ % + mốc, lô/căn) trong **một giao dịch**, **một phiên bản** cho cả lượt. Có CAS (`expected_version`) và chống lặp (replay không thêm bản).
- **Tiến độ chuẩn = Lần · % · Mốc · Ghi chú**; Σ% phải = 100%; mốc từ mốc cơ bản + mốc riêng dự án.
- **Bỏ "giai đoạn tiến độ mặc định"** khỏi đầu vào; mã nội bộ máy tự giữ.
- **Tạo mới không cần lý do. Sửa** bản đã lưu → bắt buộc **một** "Ghi chú thay đổi" cho cả lượt; nhật ký tự động ai/lúc nào/cũ → mới.
- Tên do người dùng gõ (phí, mốc, mô tả) nhận **tiếng Việt có dấu, khoảng trắng**; quy tắc ký tự hạn chế chỉ cho mã nội bộ máy sinh.
- Giữ guard ma trận/CU hiện có của dự án đang bán (M0047 resolver D, guard M0050…); không mở quyền mới.

**Test (PG, vai ứng dụng):**
- lưu lượt đầy đủ;
- lỗi ở dòng cuối → rollback toàn bộ;
- hai người sửa → CAS chặn người sau;
- replay không thêm bản;
- Σ% ≠ 100 → lỗi;
- sửa thiếu ghi chú → lỗi; tạo mới không cần;
- tên có dấu/khoảng trắng lưu được;
- sai pháp nhân/quyền bị chặn.

## TEN-B1 · Tên hiển thị tiếng Việt tách khỏi mã máy sinh (CD-022 mục 4)

**Tệp (3):** `k2/sql_crm_ten_hien_thi.py` mới; `ha_tang/pg_migrations.py` (`M00xx_CRM_TEN_HIEN_THI`); `tests/test_crm_ten_hien_thi_pg.py` mới.

**Việc** (KK §5 dòng 5 và §2 — danh sách mọi chỗ áp quy tắc "chỉ gồm chữ/số/_ . -" lên ô người dùng gõ):
- Tách **tên hiển thị** (Unicode có dấu) khỏi **mã nội bộ** (máy sinh, ổn định, giữ quy tắc ký tự cũ) cho các đối tượng KK liệt kê ở phía SQL (G1 mẫu, G7 bộ chuẩn, sự kiện dòng lịch…).
- Đọc G7 tự resolve chuẩn hiện hành; giữ bản cũ đọc được. Không sửa SQL migration cũ.
- Mã sinh ổn định với cùng đầu vào; replay không đổi mã.

**Test:**
- tên có dấu lưu/đọc được;
- mã sinh ổn định;
- dữ liệu cũ (chỉ có mã) vẫn hiển thị;
- không còn câu lỗi ký tự cho ô tên.

## BG-B1 · Một engine tính lịch thanh toán (CD-024 BG-27, CD-019)

**Tệp (3):** `k2/sql_crm_thanh_toan.py` mới; `ha_tang/pg_migrations.py` (`M00xx_CRM_THANH_TOAN`); `tests/test_crm_thanh_toan_pg.py` mới.

**Việc** (KK §4 công thức, §5 dòng 7):
- **Một** hàm tính dùng chung (SQL; nếu KK đề xuất cả bản Python thì phải cùng một nguồn và có test đối chiếu từng ca).
- Đầu vào:
  - giá trước VAT;
  - thuế suất / phần không chịu thuế (cách tính hiện có);
  - danh sách đợt (%, cờ cọc, mốc).
- Đầu ra mỗi đợt:
  - % (tính trên giá trước VAT);
  - giá trị thanh toán **gồm VAT**;
  - **trong đó VAT**.
- **Quy tắc:**
  - đợt cọc **không** VAT;
  - VAT của phần cọc **cộng vào đợt kế tiếp**;
  - các đợt sau: phần + VAT;
  - chênh làm tròn dồn **đợt cuối**;
  - cọc ở dòng cuối / lịch một dòng → lỗi rõ (quyết định lead mục 2);
  - gõ tiền → suy % (đợt cọc không VAT).
- Ví dụ bắt buộc (TL 45 §9): 1.000.000.000 VND trước VAT, 10%, 10/30/60% (đợt 1 cọc) → **100.000.000 · 340.000.000 · 660.000.000**; Σ **1.100.000.000 VND**.
- Chưa nối Báo giá/Soạn/in (BG-B2, BG-IN). Bản ghi báo giá cũ không đổi.

**Test:**
- ví dụ trên;
- VAT 0;
- phần không chịu thuế;
- làm tròn;
- cọc dòng 2;
- cọc dòng cuối → lỗi;
- suy tiền → %;
- USD (nếu cách tính hiện có hỗ trợ — không thì ghi "Cần lead").

**Báo cáo (≤ ¼ trang) mỗi lát**, "Cần lead", thông điệp commit `[DA-B1] …` / `[TEN-B1] …` / `[BG-B1] …`.
