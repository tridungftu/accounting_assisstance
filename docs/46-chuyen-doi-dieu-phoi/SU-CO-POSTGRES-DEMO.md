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
| **Dọn 323 CSDL test cũ `kho_test_*` + 160 vai trò test** (Anh chọn 25/10) — bấm đúp `DỌN CSDL TEST CŨ.cmd` (thư mục phần mềm), đọc hộp xác nhận rồi chọn Yes; CSDL đang có kết nối được giữ lại; biên nhận `var\pg-don-csdl-test-*.json`. Lead đã chạy thử chế độ chỉ liệt kê: 323 CSDL, 160 vai trò, 0 đang kết nối | **Anh bấm (làm trước)** | Chờ Anh |
| **Chạy cụm như dịch vụ Windows `ktt-postgres-demo`** (Anh chọn 25/10) — bấm đúp `CÀI DỊCH VỤ POSTGRES DEMO.cmd`, chọn Yes khi Windows hỏi quyền; tệp tắt sạch cụm đang chạy, cấp quyền thư mục cho NetworkService, đăng ký dịch vụ tự khởi động, chờ cổng 5432; nhật ký `var\pg-dich-vu-*.txt` | **Anh bấm (sau khi dọn — ít tệp thì cấp quyền nhanh)** | **Xong 25/10 19:46** — Anh bấm 19:40 (chưa dọn CSDL test cũ); tắt sạch 19:40:39, cấp quyền ~5,5 phút, dịch vụ `ktt-postgres-demo` RUNNING, cổng 5432 sẵn sàng 19:46:13 (gián đoạn ~6 phút, không phải khôi phục sau sập); nhật ký `..ar\pg-dich-vu-20261025-194037.txt` |

## 3. Khi dữ liệu thật lớn lên thì sao? (số đo 25/10)

- Cụm DEMO: **268.673 tệp, 4,8 GB**. Lần 25/10: bước fsync từng tệp 14:29:10 → 14:57:11 (**28 phút**); bước phát lại dữ liệu thật (redo) **0,00 giây**. Thời gian khôi phục tỷ lệ với **số tệp**, gần như không phụ thuộc lượng dữ liệu.
- Mỗi CSDL dù trống cũng có ~790 tệp danh mục hệ thống → 340 CSDL ≈ 268 nghìn tệp. Kho thật chỉ là **1 CSDL** (vài schema, vài trăm bảng): vài nghìn tệp; dữ liệu tăng thì tệp tăng chậm (mỗi 1 GB của một bảng thêm 1 tệp) → fsync tính bằng giây.
- Bước fsync **chỉ xảy ra sau khi bị cắt ngang**. Chạy bằng dịch vụ thì Windows báo tắt → PostgreSQL ghi checkpoint và tắt sạch → lần sau khởi động trong vài giây.
- Khi lên vận hành thật (chưa làm): dịch vụ + sao lưu định kỳ + tách cụm test khỏi cụm thật; cân nhắc loại thư mục dữ liệu khỏi quét thời gian thực của Windows Defender (đổi cài đặt bảo mật — Anh quyết, lead không tự làm).
| Lỗi Windows "error code 487" (giữ vùng nhớ chung cho tiến trình con): lỗi đã biết của PostgreSQL trên Windows, tự thử lại; theo dõi, chưa cần xử lý | lead | Theo dõi |
