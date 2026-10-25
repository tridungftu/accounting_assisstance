# L0-10 — `pg_cum` nhận cụm PostgreSQL DEMO chạy bằng dịch vụ Windows (chặn mở DEMO có CRM)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại** (ưu tiên cao). Đọc `AGENTS.md`, `CLAUDE.md` (§2 — không khởi động/dừng PostgreSQL trong sandbox). UTF-8 không BOM — **ghi tệp bằng UTF-8**. Worktree hiện tại, nhánh `lat/l0-10` (từ hop-nhat). Sandbox không ghi `.git`: **không commit**. **Không gọi pg_ctl/sc/net thật, không nối CSDL** — test bằng `HeDieuHanh` giả.

**Sự cố (lead đo 25/10 20:35):** từ 19:46 cụm DEMO chạy bằng dịch vụ Windows `ktt-postgres-demo` (tài khoản NetworkService; tệp `tools/cai_dich_vu_postgres_demo.ps1`). Dưới tài khoản người dùng:
- `pg_ctl status -D <data>` trả **mã 3 "no server running"** dù cụm đang chạy;
- `Win32_Process` của tiến trình đang nghe 5432 trả `ExecutablePath`/`CommandLine` **rỗng** (không đủ quyền đọc tiến trình dịch vụ);
- nhưng đọc được: `<data>\postmaster.pid` (dòng 1 PID = PID đang nghe 127.0.0.1:5432; dòng 2 thư mục data; dòng 4 cổng; dòng 6 host; dòng 8 `ready`) và `Win32_Service.PathName` của `ktt-postgres-demo` (`"<pg_ctl.exe>" runservice -N "ktt-postgres-demo" -D "<data>" -w -o "-h 127.0.0.1 -p 5432 …"`, trạng thái RUNNING).
→ `src/kho_tri_thuc/ha_tang/pg_cum.py` `bao_dam_cum` (~:226-245) coi là cụm dừng mà cổng bị chiếm → `CUM_CONG_BI_CHIEM`; `xac_minh_dang_chay` (~:203-212) cũng sẽ fail vì không đọc được exe/cmd. Hệ quả: `tools\mo_demo_worktree.ps1`, `MỞ BẢN DEMO.cmd` của Anh, `tools/chuan_bi_crm_demo.py` đều không chuẩn bị được CRM.

**Việc (`pg_cum.py`):**
1. Thêm nhận diện "cụm đã định danh chạy bằng dịch vụ": khi `pg_ctl status` = 3 **hoặc** không đọc được exe/cmd của PID đang nghe, chấp nhận là ĐÚNG cụm chỉ khi **đủ cả**: (a) `postmaster.pid` của `cum.data_dir` đọc được, PID dòng 1 = PID đang nghe `cum.host:cum.port`, dòng 2 chuẩn hóa = `cum.data_dir`, dòng 4 = `cum.port`, dòng 8 = `ready`; (b) có dịch vụ Windows đang RUNNING mà `PathName` chứa đúng `cum.pg_ctl` + `runservice` + `-D` trỏ đúng `cum.data_dir` (đọc qua lớp `HeDieuHanh`, thêm phương thức mới, ví dụ `dich_vu_pg(data_dir)`). Kết quả `{"ket_qua": "DUNG_LAI", "pid", "endpoint", "che_do": "DICH_VU"}`.
2. Thiếu bất kỳ bằng chứng nào → giữ nguyên lỗi hiện có (`CUM_CONG_BI_CHIEM` / `CUM_KHONG_XAC_MINH`). **Không** dừng/khởi động/giành dịch vụ hay tiến trình; không đổi hành vi khi cụm chạy tay như trước.
3. Test trong `tests/test_crm_khoi_dong.py` (dùng `HeDieuHanh` giả như các ca hiện có): dịch vụ đúng → DUNG_LAI/DICH_VU; PID postmaster.pid ≠ PID nghe → lỗi; data dir khác → lỗi; dịch vụ trỏ data khác/không RUNNING → lỗi; postmaster.pid không phải `ready` → lỗi; cụm chạy tay vẫn như cũ.

**File được sửa (chỉ 2):** `src/kho_tri_thuc/ha_tang/pg_cum.py`, `tests/test_crm_khoi_dong.py`. Không xóa file.
**Test:** `--module test_crm_khoi_dong`; sandbox chặn python → ghi "lead chạy test". Lead thử thật bằng mở DEMO worktree cổng 8798.
**Báo cáo cuối (≤ ⅓ trang):** sửa ở file:dòng · bằng chứng nhận diện · ca test · thông điệp commit `[L0-10] …`.
