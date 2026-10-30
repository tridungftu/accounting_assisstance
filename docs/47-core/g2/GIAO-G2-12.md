# G2 · giao G2-12 — danh mục và cửa ghi V2 từ định nghĩa cuối đã phân chủ

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `lat/g2-11` (G2-00…G2-11). Quy ước như cũ: tiền tố vai, login thật, phiên xác minh, không DROP, không đè `TestCase.id`. Sổ migration cho phép khoảng trống số.

## Lát G2-12

**Tệp:** `src\kho_tri_thuc\core\sql\012_danh_muc.sql`; `src\kho_tri_thuc\core\danh_muc.py`; `tests\test_g2_12.py`.

**Căn cứ:**
- Đặc tả CSDL §3.6 (schema `danh_muc`: đối tác, dự án, tài khoản; `hop_dong` khóa chung; `chung_tu` đầu chứng từ; `hoa_don_danh_tinh`; `khoa_ky`; liên kết / phân bổ chung — liên kết trỏ nghĩa vụ bằng bộ ba `(module, loai, id)`, không FK chéo module) và §6.1–§6.2;
- Phiếu CSDL (Anh duyệt);
- `ANH-XA-MIGRATION.md` (định nghĩa cuối của M0002, M0003…, khóa kỳ `P:494`, guard `P:855`).
- **Chỉ lấy định nghĩa cuối**, không chạy chuỗi cũ. Không mang dòng cũ hay trạng thái riêng module vào Core.
- **Phần kiểm toàn vẹn tiền liên kết là G2-13** (Opus) — lát này chỉ dựng bảng / cửa ghi V2 và khóa kỳ, chưa dựng resolver nghĩa vụ.

**Việc:**
- Bảng `danh_muc` với RLS theo phiên (G2-06).
- **Cửa ghi V2** (hàm Core có kiểm MTQ, chống trùng qua biên nhận G2-11, khóa kỳ): ghi đối tác / dự án / hợp đồng khóa chung / đầu chứng từ / định danh hóa đơn.
- Khóa kỳ chặn ghi chứng từ trong kỳ đã khóa.
- Thêm dòng / hết hiệu lực, không xóa.

**Test PG:**
- ghi qua V2 đúng quyền / sai quyền;
- trùng khóa → phát lại;
- kỳ đã khóa chặn ghi;
- sai pháp nhân bị chặn;
- runtime không ghi thẳng bảng;
- không FK sang schema module.
