# G2 · Đợt A — giao lát G2-00, G2-01, G2-33 (CD-038 mở lại lập trình, 30/10/2026 17:52)

## Phần chung (mọi lát G2/G3)

- Bạn là worker Codex, làm trong worktree riêng của lát (nhánh `lat/<ma>` từ `hop-nhat-20261023`). **Làm ngay.**
- **Kế hoạch:** `docs\47-core\g2\KE-HOACH-LAT-G2-G3.md`. Đọc §1 (phương án, gói mới, quy tắc nghiệm thu), §5 (khóa bắt buộc) và đúng dòng lát của bạn ở §2.
- **Chuẩn phải theo:**
  - `docs\47-core\chuan\CHUAN-CORE-CSDL-v1.0.md`, `CHUAN-CORE-API-v1.0.md`, `CHUAN-CORE-SDK-v1.0.md`;
  - đặc tả chi tiết `docs\47-core\g1\`.
  - Chỗ chuẩn ghi "chờ Anh" → dừng, ghi "Cần lead", không tự chốt.
- **Chỉ sửa/tạo đúng các tệp** ghi ở dòng lát (≤ 3 tệp kể cả test).
  - Cần tệp khác → dừng, ghi "Cần lead".
  - Không sửa `giao_dien/server.py`, `ha_tang/pg_migrations.py`, `crm_g.py`, asset cũ.
- **Ghi tệp:**
  - bằng apply_patch, UTF-8 không BOM;
  - SQL PL/pgSQL tự kiểm `AS $$`/`$$`;
  - không ghi qua chuỗi PowerShell nháy kép.
- **Không được:**
  - commit, xóa file;
  - **khởi động/dừng PostgreSQL hay server DEMO**;
  - đọc `var\plhn-that`, `var\web-that`, `cau_hinh.that.toml`, `.env`, `*.local.json`, `D:\DU-LIEU-KE-TOAN`.
- **CSDL DEMO riêng của Core:** `kho_core_demo_g2_<ma>` (lead dựng). Vùng dữ liệu DEMO: `var\core-demo\<ma>\`, ngoài git. Script phải từ chối đích thật.
- **Test:**
  - test thuần/mock tự chạy được nếu có python, không có thì ghi NOT_RUN;
  - test PG viết `skipUnless KHO_PG_DSN_TEST`, tự tạo `kho_test_*`; **ca nghiệp vụ chạy dưới vai chạy thật**, không đóng giả bằng owner;
  - không kiểm CRLF/LF.
- **Tên** schema/bảng/cột/role tiếng Việt không dấu, đúng bảng tên chuẩn CSDL §2.
- **Báo cáo** ≤ ¼ trang, gồm "Cần lead". Thông điệp commit đề xuất `[G2-xx] …`.

## Lát G2-00 · Chuẩn bị đường dựng Core DEMO rỗng có kiểm môi trường

**Tệp:** `src\kho_tri_thuc\core\__init__.py`; `tools\tao_core_demo.py`; `tests\test_g2_00.py`.

**Việc:**
- Công cụ tạo CSDL DEMO rỗng `kho_core_demo_g2_<ma>` cùng cụm PostgreSQL DEMO. Đọc DSN admin DEMO bằng chương trình từ `var\web\crm-demo\ket-noi.local.json` như `tools\tao_ket_noi_demo_rieng.py`: **không in DSN**, chỉ thay tên CSDL.
- Tạo `var\core-demo\<ma>\` (kho tệp, cấu hình kết nối, két DEMO).
- **Từ chối:**
  - tên CSDL không khớp `^kho_core_demo_g2_[a-z0-9_]+$`;
  - đường dẫn thuộc `D:\DU-LIEU-KE-TOAN`, `var\plhn-that`, `var\web-that`;
  - cụm không phải DEMO.
- Không DROP gì. Chạy lại được (đã có thì báo, không tạo đè).

**Test:** từ chối đích thật / tên sai / đường dẫn cấm; không in credential (bắt stdout/stderr); chạy lại idempotent (mock kết nối).

## Lát G2-01 · Role / login / schema và provisioning đúng owner

**Tệp:** `src\kho_tri_thuc\core\sql\001_vai.sql`; `tests\test_g2_01.py`.

**Việc** (chuẩn CSDL §3, đặc tả CSDL §4.1–§4.2):
- **Schema:** `loi`, `loi_tai_lieu`, `danh_muc`.
- **Role theo khối** `loi`, `loi_tai_lieu`, `danh_muc`:
  - cặp `vai_chay_<khoi>` (NOLOGIN, không owner, không BYPASSRLS / CREATEROLE / CREATEDB, không DDL);
  - `vai_doi_cau_truc_<khoi>` (NOLOGIN, owner khối).
- **Login DEMO:** `dang_nhap_loi`, `dang_nhap_cai_dat`. Membership PG16 `INHERIT TRUE, SET FALSE, ADMIN FALSE`. Mật khẩu **không** nằm trong SQL: tham số do công cụ dựng truyền vào, hoặc để lead đặt.
- Thu hồi quyền PUBLIC trên schema mới; default privileges theo từng role tạo đối tượng.
- **Provisioning chạy lại được:** `IF NOT EXISTS`, không DROP.

**Test PG:**
- membership đúng thuộc tính;
- runtime không owner, không DDL, không BYPASSRLS;
- PUBLIC không có quyền;
- `SET ROLE` sang owner bị chặn;
- chạy lại không lỗi, không nới quyền.

## Lát G2-33 · Script tài khoản Windows / ACL chạy lại được (CD-033, CD-038 engine 3A)

**Tệp:** `tools\tao_tai_khoan_core.ps1`; `tools\CAI-TAI-KHOAN-CORE.cmd`; `tests\test_g2_33.py`.

**Việc:**
- **Tài khoản máy cục bộ:**
  - `ktt_core`;
  - `ktt_module`;
  - tài khoản riêng cho từng engine giữ bí mật: Mask, AI Cloud, tải hóa đơn, ABBYY. Tên đề xuất `ktt_e_mask`, `ktt_e_ai`, `ktt_e_hoa_don`, `ktt_e_ocr`.
- **ACL:**
  - két `D:\DU-LIEU-KE-TOAN\bi-mat\` **chỉ** `ktt_core`;
  - thư mục engine / kho tệp DEMO theo nguyên tắc tối thiểu.
- **Chế độ xem trước (mặc định):** in danh sách việc sẽ làm, **không thay đổi gì**. Chỉ áp khi có tham số `-ApDung` và đang chạy quyền quản trị.
- Chạy lại không nới quyền; không xóa tài khoản / thư mục; không in mật khẩu (mật khẩu tài khoản sinh ngẫu nhiên, lưu vào két bằng DPAPI phạm vi người dùng `ktt_core`, hoặc ghi "Cần lead" nếu chưa làm được an toàn).
- `.cmd`: Anh bấm đúp → xem trước → hỏi xác nhận → tự nâng quyền quản trị khi áp.
- **Không chạy áp thật trong sandbox.**

**Test:** test thuần kiểm script ở chế độ xem trước bằng mock / phân tích tĩnh:
- không có lệnh xóa;
- có kiểm quyền quản trị trước khi áp;
- ACL két chỉ `ktt_core`;
- không in mật khẩu.
