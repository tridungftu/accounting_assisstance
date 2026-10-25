# L0-2e — Gộp m2-00b-fix01 (M2-00 · Nhận nguồn từ cổng thuế)

Bạn là worker Codex, chạy không tương tác (`codex exec`). Anh đã duyệt qua lead: **làm ngay đến hết, không hỏi lại**. Đọc `AGENTS.md` ở thư mục hiện tại. Mã hóa UTF-8 (đọc bằng `git show`, `python -X utf8`; ghi UTF-8 không BOM).

**Thư mục:** worktree hiện tại, nhánh `lat/l0-2e` (từ `hop-nhat-20261023`). Sandbox KHÔNG ghi được `.git`: **không git add/commit** — lead commit theo danh sách bạn báo.

**Nguồn:** `luu/m2-00b-fix01` = nền `chinh` 59b7d8e + ảnh chụp NGUYÊN FILE của 4 file: `src/kho_tri_thuc/m2/tai_hoa_don/dieu_phoi.py`, `khach.py`, `tests/test_m2_00b_quyen.py`, `tests/test_m2_00b_tien_trinh.py`. Trên hop-nhat 4 file này chỉ do gói `m2-00b-owned-rpc` (041b1f8) tạo — fix01 là bản kế nhiệm → **lấy nguyên nội dung 4 file từ `luu/m2-00b-fix01`** (`git show luu/m2-00b-fix01:<file>`).
Thêm 1 file bị sót khỏi git: `tools/source7_m2_patch/config.js` — chỉ có trong bản chụp `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\var\codex-dieu-phoi\m2-00b-fix01-code-frozen-d269061a1c29\files\tools\source7_m2_patch\config.js` (được `tools/source7_m2_patch/src/job.js` import). Trước khi chép: kiểm file KHÔNG chứa dữ liệu thật (mã số thuế, tên công ty thật, đường dẫn hồ sơ trình duyệt của người dùng, mật khẩu/token). Có → KHÔNG chép, ghi vào báo cáo.

**Test (mỗi module một lệnh, `PYTHONPATH=src`, `python -X utf8 -m unittest tests.<module>`, giới hạn 180 giây/lệnh):**
- TRƯỚC khi áp: `test_m2_00b_quyen`, `test_m2_00b_tien_trinh`, `test_m2_00b_tinh`. Nền lead đo: quyen 1 ok/21 ERROR, tien_trinh 16 ok, tinh 3 ok/16 ERROR. Cùng `node tests/m2_00a_source7_fix02.cjs` và `node tests/m2_00b_source7_rpc.cjs` nếu chạy được.
- SAU khi áp: chạy lại đúng các lệnh trên.
- Với ERROR còn lại: đọc traceback đầu tiên, gom thành ≤ 3 nguyên nhân gốc (1 dòng mỗi nguyên nhân, ghi môi trường hay code, file:dòng). **Không sửa code để chữa** — chỉ chẩn đoán.

**Không làm:** sửa file ngoài 5 file trên; thêm tính năng; chạy bộ tải #7 thật hay gọi cổng thuế; đọc `var/` ngoài đúng file config.js nêu trên, `.env`, `cau_hinh.*.toml`; xóa gì.

**Báo cáo cuối (≤ 1 trang, tiếng Việt)** — tin nhắn cuối của bạn: Đã làm · File đổi (để lead commit, kèm thông điệp commit đề xuất `[L0-2e] ...`) · Test trước/sau từng module (ok/ERROR/FAIL/skip) · Lỗi mới so với trước: có/không · ≤ 3 nguyên nhân gốc lỗi còn lại · Rủi ro.
