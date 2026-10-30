# G2 · giao G2-20 — SDK tối thiểu cho module và engine

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `hop-nhat-20261023` (G2-00…G2-19, G2-17b; `sdk_core/ngu_canh.py`, `giao_dich.py` đã có).

## Lát G2-20

**Tệp:**
- `src\kho_tri_thuc\sdk_core\dich_vu.py`
- `src\kho_tri_thuc\sdk_core\engine.py`
- `tests\test_g2_20.py`

**Căn cứ:**
- `docs\47-core\chuan\CHUAN-CORE-SDK-v1.0.md`:
  - §3.3 (12 dịch vụ — lát này làm phần tối thiểu: tệp, kết quả, việc, audit, biên nhận, bus);
  - §3.4 (cùng `tx`, không tự commit);
  - §3.7 (quy tắc riêng engine: engine chỉ dùng phần giao tiếp Core cấp cho công việc, **không nhận SQL / credential DB**);
  - §3.9 (engine manifest);
  - §7.
- `docs\47-core\g1\DAC-TA-SDK.md`.
- **Dùng lại, chỉ bọc:**
  - `core\tep.py` / `ket_qua.py` (G2-10);
  - `core\viec.py` (G2-14);
  - `core\tiep_nhan.py` (G2-11);
  - `core\su_kien.py` (G2-15);
  - audit G2-04;
  - `sdk_core\giao_dich.py` (`tx`);
  - `sdk_core\ngu_canh.py`.
- Không viết lại logic Core.

**Việc:**
- **`dich_vu.py`** — mặt SDK cho module:
  - `tep`, `ket_qua`, `viec`, `audit`, `bien_nhan`, `su_kien`;
  - mọi lời gọi chạy trên `tx` hiện hành, không tự commit;
  - quyền / phiên lấy từ ngữ cảnh đã xác minh, không nhận tham số danh tính tự khai.
- **`engine.py`** — mặt SDK cho engine:
  - nhận `GiuViec` (lease + mã ủy nhiệm theo việc);
  - đọc đầu vào / tệp được cấp, bàn giao kết quả qua Core (Core gắn nguồn), heartbeat;
  - **không có đường tới SQL / kết nối / DSN**;
  - mất lease → từ chối, không ghi.
- Bí mật không lộ qua repr / log / pickle (theo mẫu G2-19).

**Test:**
- **Thuần:**
  - engine API không có thuộc tính / phương thức chạm SQL (kiểm cả `__dict__` / `dir`);
  - repr không lộ bí mật.
- **PG (login thật):**
  - module ghi kết quả + biên nhận + việc + sự kiện trong một `tx`, rollback → không còn gì;
  - SDK không tự commit;
  - engine bàn giao kết quả bằng lease hợp lệ → Core gắn nguồn đúng;
  - lease hết → từ chối;
  - module không tạo được nguồn kết quả tự khai.

Báo cáo ≤ 3 dòng.
