# G2 · giao G2-21 — khung tiến trình và chuyển giao / thu hồi socket (lát cốt lõi, review Opus bắt buộc)

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `lat/g2-20` (G2-00…G2-20; sổ cổng G2-16; SDK G2-19 / G2-20).

## Lát G2-21

**Tệp:**
- `src\kho_tri_thuc\core\tien_trinh.py`
- `src\kho_tri_thuc\sdk_core\bootstrap.py`
- `tests\test_g2_21.py`

**Căn cứ:**
- `docs\47-core\chuan\CHUAN-CORE-API-v1.0.md` §3.10 (Core giữ / nhả cổng, vòng đời tiến trình; dòng ~469–560) và §3.11;
- `CHUAN-CORE-SDK-v1.0.md` §3.6 (khung chạy: khóa phối hợp, cổng cố định + thế hệ sở hữu từ sổ cổng, readiness);
- CD-028 (giữ cổng bằng `socket.share` / `fromshare`, tài khoản Windows riêng).
- **Dùng lại host #6:** `src\kho_tri_thuc\nguon\trich6_host.py` (+ `tests\test_trich6_host.py`) và mẫu `m2\tai_hoa_don\tien_trinh.py`. Chỉ đọc; bọc / trích phần dùng chung, không viết lại khác nghĩa.
- **Dùng lại:**
  - sổ cổng `core\so_cong.py` (G2-16): cấp cổng, nhận sở hữu CAS, gia hạn, sẵn sàng, khóa lỗi;
  - `sdk_core\ngu_canh.py`: `nonce_khoi_dong`.

**Việc:**
- **`tien_trinh.py`** (phía Core):
  - giữ ổ nghe trên cổng cố định từ sổ cổng;
  - khởi động tiến trình con với `nonce_khoi_dong` mới mỗi lần;
  - chuyển socket qua kênh khởi động riêng (`socket.share(pid)` → `fromshare`), **chỉ một bên accept** tại một thời điểm;
  - thu hồi khi con chết / drain;
  - readiness chỉ chấp nhận khi khớp PID + thời điểm tạo tiến trình + nonce + phiên bản, rồi gọi `so_cong.san_sang`.
- **Cổng bị chiếm:** không dò cổng khác, **không diệt tiến trình lạ**; ghi khóa lỗi khởi động (G2-16) và báo lỗi.
- **`bootstrap.py`** (phía module / engine):
  - nhận socket + thông số khởi động qua stdin / handle (không qua args / env / đĩa);
  - dựng `BoDocNguCanh` với `nonce_khoi_dong`;
  - báo readiness.
- **Không tạo tài khoản Windows hay đổi quyền hệ thống** trong lát / test. Phần chạy dưới tài khoản riêng là G2-33 / G2-33b, chờ.

**Test:**
- **Thuần / cục bộ** (tiến trình con Python thật trên loopback, cổng 0 hoặc cổng thử do sổ cấp; không cổng 8766 / 8767 / 8768):
  - share / fromshare chuyển được, một bên accept;
  - readiness sai PID / nonce / version → từ chối;
  - cổng bị chiếm → lỗi, không diệt tiến trình chiếm, không đổi cổng;
  - con chết → Core thu hồi, cổng trả về đúng trạng thái;
  - thông số không qua args / env.
- **PG:** sổ cổng ghi sẵn sàng / khóa lỗi đúng thế hệ.

**Lưu ý môi trường:** lead chạy test ngoài sandbox Codex. Trong sandbox, chỉ chạy phần thuần không mở tiến trình con nếu bị chặn; ghi rõ ca nào chưa chạy.

Báo cáo ≤ 3 dòng.
