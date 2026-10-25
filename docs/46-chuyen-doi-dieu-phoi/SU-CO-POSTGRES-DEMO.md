# Sự cố cụm PostgreSQL DEMO (127.0.0.1:5432) — rà soát 25/10/2026

Cụm: `D:\Claude\Phan mem ho tro ke toan\var\postgresql-ktt-16\data` (PostgreSQL 16.15, chạy tay bằng `pg_ctl`, **không phải dịch vụ Windows**). Chỉ chứa CSDL DEMO/test — kho thật vẫn SQLite.

## 1. Ba lần cụm bị mất

| # | Lúc dừng | Dấu hiệu trong nhật ký | Nguyên nhân (bằng chứng) | Mất bao lâu |
|---|---|---|---|---|
| 1 | 18/10 sau 17:25 | Nhật ký dừng giữa chừng, không có dòng tắt; lần khởi động 19/10 06:01 báo "database system was interrupted" | **Windows tắt/khởi động lại máy lúc 01:49 ngày 19/10** (System: Kernel-Power 109 "initiated a shutdown transition", Kernel-General 13 → 12). PostgreSQL không phải dịch vụ nên không được báo tắt, bị cắt ngang. | Tới 06:01 ngày 19/10 |
| 2 | 23/10 ~11:33 | Dòng cuối "could not reserve shared memory region … error code 487", rồi im; lần sau báo "last known up at 11:18:29" | **Ứng dụng Codex tự cập nhật** (AppXDeploymentServer: đăng ký gói `OpenAI.Codex_26.1016.8120.0` lúc 11:34:33; dịch vụ `CodexSandboxService` ghi sự kiện 1001/1002/1000 lúc 11:34:28–33). Tiến trình PostgreSQL lúc đó do một phiên Codex khởi động **bên trong sandbox Codex** → bị dừng cùng sandbox. | ~2 giờ (khôi phục 13:03–13:42; lần thử 02 bị dừng vì tưởng treo — thực ra đang fsync) |
| 3 | 25/10 13:12:41 | "terminating connection due to unexpected postmaster exit" ở mọi kết nối — tiến trình chính bị cắt đột ngột | **Ứng dụng Codex tự cập nhật lần nữa** (gói `26.1016.8120` → `26.1021.3705` hoàn tất 13:13:21; `CodexSandboxService` 1001/1002/1000 lúc 13:13:18–21; conhost bị đóng 13:13:18). Tiến trình PostgreSQL (pid 37548) là bản Codex Root khởi động trong sandbox ngày 23/10 (`pg-cluster-recovery-20261023-03`). | ~1 giờ 45 (lead khởi động lại 14:29, sẵn sàng 14:57) |

**Vì sao khôi phục lâu (18–28 phút):** sau mỗi lần dừng đột ngột, PostgreSQL phải fsync toàn bộ thư mục dữ liệu; cụm đang có **~337 CSDL, trong đó 323 CSDL test cũ `kho_test_*`** (sinh trước khi có bộ dọn L0-8). Lần 25/10 riêng bước fsync mất ~28 phút.

## 2. Cách khắc phục

| Việc | Ai | Trạng thái |
|---|---|---|
| **Cấm khởi động/dừng PostgreSQL hoặc server DEMO trong sandbox Codex** (Codex tự cập nhật sẽ giết mọi tiến trình con); chỉ lead khởi động, ngoài sandbox | lead (quy tắc `CLAUDE.md` §2 + mọi tệp giao Codex) | Làm ngay 25/10 |
| Tiến trình hiện tại (pid 14736) do lead khởi động bằng `pg_ctl` ngoài Codex; nhật ký `var\pg-cluster-recovery-20261025-01\postgres.log` | lead | Xong 25/10 14:57 |
| Lead kiểm cổng 5432 trước khi báo Anh mở DEMO | lead | Làm ngay |
| **Chạy cụm như dịch vụ Windows** (tự khởi động cùng máy, tắt sạch khi Windows tắt/cập nhật — xử lý luôn lần #1) — cần quyền quản trị, lead không tự đổi cài đặt hệ thống | Anh chọn (bảng chọn) | Chờ Anh |
| **Dọn 323 CSDL test cũ `kho_test_*`** (rút thời gian khôi phục còn vài phút) — xóa dữ liệu vĩnh viễn nên lead chỉ soạn lệnh, Anh quyết | Anh chọn (bảng chọn) | Chờ Anh |
| Lỗi Windows "error code 487" (giữ vùng nhớ chung cho tiến trình con): lỗi đã biết của PostgreSQL trên Windows, tự thử lại; theo dõi, chưa cần xử lý | lead | Theo dõi |
