# Xương sống (CD-017) loạt 1: XS-1a và XS-3a — phần riêng theo mã lát

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM. `pg_migrations.py` giữ LF. Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ: dừng, ghi "Cần lead". Môi trường không có `python` thì ghi NOT_RUN; lead chạy test và PG.
- Test PG tự tạo CSDL `kho_test_*` từ DSN quản trị (`skipUnless KHO_PG_DSN_TEST`), không đọc `KHO_PG_DEMO_*`.
- Dữ liệu giả phải đúng mọi trigger/ràng buộc thật.
- Chạy được dưới guard giữ tệp của runner (`CODEX_NO_DELETE_FILES`).

**Căn cứ:**
- `D:\Claude\Phan mem ho tro ke toan\53-kien-truc-xuong-song-engine-module.md` (TL 53).
- `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` CD-017.
- `docs\46-chuyen-doi-dieu-phoi\KK-XUONG-SONG.md` (§1 hiện trạng, §2 dòng của lát, §5 rủi ro).

Nguyên tắc: **không đổi hành vi hiện có**; chỉ thêm. Test cũ phải đạt.

## XS-1a · SQL bus sự kiện bền (outbox/inbox)

**Tệp (3):**
- `k2/sql_bus_su_kien.py` mới (hằng `BUS_SU_KIEN_SQL`);
- `ha_tang/pg_migrations.py`: migration mới tên tạm `M00xx_BUS_SU_KIEN`, dấu `# XS-1a — CD-017:`;
- `tests/test_xs1_sql.py` mới.

**Việc:**
- Thêm bảng outbox (sự kiện phát) và inbox/ACK (theo từng bên nhận) trong PostgreSQL. Có:
  - `pháp nhân`, `loai_su_kien` + `phien_ban`;
  - khóa chống trùng (dedupe) **do bên phát cấp**;
  - payload jsonb **chỉ tham chiếu/ID**, không chứa nội dung chứng từ;
  - thời điểm, trạng thái.
- Phát trong cùng giao dịch nghiệp vụ: rollback thì không phát.
- Nhận: mỗi bên nhận ghi ACK **một lần**. Nhận lại cùng sự kiện không nhân đôi. Hai bên nhận độc lập nhau.
- Hàm SQL phát/nhận/ACK `SECURITY DEFINER`, `search_path` cố định. ACL: `REVOKE PUBLIC`, `EXECUTE` cho `app_web`.
- RLS/ghi theo pháp nhân của phiên: dùng hàm có sẵn, **không sửa** `ktt_duoc`/`ktt_pn_cho_phep`.
- Tên schema/bảng: theo quy ước repo (gợi ý schema `bus`), ghi rõ trong docstring.
- Không sửa migration cũ. Test không ghim migration cuối hay hash byte.

**Test:**
- phát + rollback → không có;
- phát trùng khóa dedupe → một dòng;
- hai bên nhận cùng sự kiện, mỗi bên ACK một lần, ACK lại không nhân đôi;
- sai PN không thấy/không ACK được;
- ACL.

## XS-3a · Hợp đồng engine + danh bạ (thuần Python)

**Tệp (3):**
- `ha_tang/engine.py` mới;
- `ha_tang/danh_ba_engine.py` mới;
- `tests/test_xs3_engine.py` mới.

**Việc:**
- Hợp đồng engine theo TL 53: `ma`, `phien_ban`, khai báo vào/ra, hàm chạy.
- Kết quả chuẩn: `trang_thai` ∈ `XONG` / `CHO` / `LOI`; `ma` lý do có mã; `ly_do` tiếng Việt trung tính; `bang_chung` (hash vào/ra, phiên bản engine, thời điểm).
- `CHO` là trạng thái hợp lệ có lý do (ví dụ thiếu dữ liệu module khác), không phải lỗi.
- Danh bạ:
  - đăng ký theo (`ma`, `phien_ban`);
  - từ chối trùng hoặc khác phiên bản cho cùng mã đã đăng ký, trừ khi đăng ký phiên bản mới tường minh;
  - tra cứu, liệt kê để ghi `TRANG-THAI.md`.
- Engine **không** đọc/ghi bảng của module (ghi rõ trong docstring); vào/ra chỉ qua tham số.
- Chưa bọc engine thật nào (để XS-3b/3d). Có **bộ test mẫu chuẩn** dùng lại được cho mọi engine: hàm/khung kiểm hợp đồng mà lát sau gọi.
- Không thêm thư viện ngoài.

**Test:**
- engine giả XONG/CHO/LOI;
- bằng chứng ổn định;
- đăng ký trùng → từ chối;
- phiên bản mới tường minh → được;
- khung test mẫu chạy được cho engine giả.

**Báo cáo (≤ ⅓ trang)** mỗi lát, "Cần lead", thông điệp commit `[XS-1a] …` / `[XS-3a] …`.
