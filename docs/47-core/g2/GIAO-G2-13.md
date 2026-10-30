# G2 · giao G2-13 — kiểm toàn vẹn liên kết tiền dưới FORCE RLS (lát cốt lõi, review Opus bắt buộc)

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `hop-nhat-20261023` (đã có G2-00…G2-12; bảng `danh_muc.lien_ket_chung_tu`, `lien_ket_phan_bo` và cửa ghi V2 ở `012_danh_muc.sql`).

Quy ước như cũ:
- login thật + phiên xác minh;
- không DROP;
- sổ migration số tăng, cho phép bỏ số;
- **không sửa migration đã phát hành (001–012)**: thay đổi hàm cũ thì `CREATE OR REPLACE` trong 013;
- test tự áp chuỗi SQL theo số.

## Lát G2-13

**Tệp:**
- `src\kho_tri_thuc\core\sql\013_lien_ket.sql`
- `src\kho_tri_thuc\core\lien_ket.py`
- `tests\test_g2_13.py`

**Căn cứ (đọc kỹ):**
- `docs\47-core\chuan\CHUAN-CORE-CSDL-v1.0.md` §3.7 (đặc biệt §3.7.2 transaction liên kết, bảng ca âm quanh dòng 329–332);
- `docs\47-core\g1\DAC-TA-CSDL.md`:
  - dòng 250–251 (bộ ba nghĩa vụ, không FK chéo);
  - dòng 318–328 (policy kiểm toàn vẹn C2, `vai_kiem_toan_ven_<khoi>`, test âm bắt buộc, policy tường minh cho role chủ hàm DEFINER);
  - dòng 387 (transaction liên kết, thứ tự khóa, `CHO`);
  - dòng 480 (S4 registry gọi resolver DEFINER module).
- Mẫu K2 cũ: `src\kho_tri_thuc\ha_tang\pg_migrations.py` quanh `P:1034`, `P:1057`, `P:1077`, `P:1270`, `P:2700` — chỉ đọc để giữ ngữ nghĩa.

**Việc:**
1. **Vai và policy toàn vẹn:**
   - tạo `vai_kiem_toan_ven_danh_muc` NOLOGIN, không BYPASSRLS, không membership runtime;
   - policy riêng chỉ lọc pháp nhân đã xác minh, áp cả khi FORCE RLS;
   - hàm kiểm tổng nội bộ chỉ trả kết luận / mã lỗi, không trả dòng hay tổng bị che.
2. **Transaction liên kết trong một kết nối:**
   - cổng V2 xác thực / MTQ, cùng pháp nhân / tiền tệ;
   - khóa đầu chứng từ theo thứ tự ID;
   - gọi resolver DEFINER của module chủ nghĩa vụ **qua registry (G2-05)** để khóa và kiểm nghĩa vụ theo bộ ba `(module, loai, id)` + ID + mã băm phiên bản;
   - ghi liên kết / phân bổ;
   - kiểm cuối trước commit: tổng ≤ tiền chứng từ (Core); tổng ≤ nghĩa vụ (module chủ, qua hàm tổng Core nội bộ cấp cho role kiểm của module).
3. **Thiếu module / resolver / căn cứ** → `CHO` có lý do, không commit liên kết. Không tin bộ ba do caller khai khi resolver chưa xác minh.
4. **Thứ tự khóa** chứng từ → nghĩa vụ thống nhất cho tạo / sửa / hủy liên kết và **giảm sức chứa nghĩa vụ**. Giảm không bỏ qua liên kết đã có.
5. Thêm dòng / hết hiệu lực; không xóa.

**Module nghĩa vụ trong test:** chưa có CRM thật. Test dựng **module DEMO** (schema `mod_demo_nv`, bảng nghĩa vụ, resolver DEFINER, role kiểm, đăng ký registry) bằng SQL trong test, không đưa vào gói Core.

**Test PG bắt buộc (login thật, FORCE RLS):**
- **Ca A:** người không có quyền M1 nhưng được tạo liên kết. Đã nối 80 bằng dòng bị che; chứng từ giới hạn 100, nghĩa vụ đủ lớn; thêm 30 → từ chối, không lộ tổng.
- **Ca B:** như A nhưng nghĩa vụ giới hạn 100, chứng từ đủ lớn → từ chối.
- **Ca C (cạnh tranh):** từ 0, giới hạn 100; hai transaction 60 + 60 trên hai kết nối song song → không cùng commit.
- **Sửa / hủy / giảm sức chứa:**
  - đồng thời giữ đúng giới hạn;
  - giảm sức chứa dưới tổng đã nối → từ chối.
- **Lỗi đầu vào:**
  - thiếu quyền hành động / sai pháp nhân / mã phiên giả → từ chối, không lộ dòng hay tổng;
  - module chưa đăng ký hoặc resolver thiếu → `CHO`, 0 dòng ghi;
  - bộ ba sai mã băm → từ chối.
- **Kiểm quyền:**
  - runtime không ghi thẳng bảng;
  - không FK sang schema module;
  - role kiểm không trả tổng cho runtime.

Báo cáo ≤ 3 dòng. Lead sẽ chạy PG và gọi review Opus trước khi gộp.
