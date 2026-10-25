# L0-3a — Sửa nhóm lỗi môi trường N3/N4 của nền test

Bạn là worker Codex, chạy không tương tác (`codex exec`). Anh đã duyệt qua lead: **làm ngay đến hết, không hỏi lại**. Đọc `AGENTS.md`, rồi `docs/46-chuyen-doi-dieu-phoi/NEN-TEST.md` (mục 1 nhóm N2, N3, N4 và bảng module). Mã hóa UTF-8 (đọc bằng `python -X utf8`, `git show`; ghi UTF-8 không BOM).

**Thư mục:** worktree hiện tại, nhánh `lat/l0-3a` (từ `hop-nhat-20261023`). Sandbox không ghi được `.git`: **không git add/commit** — lead commit. `<REPO>` = `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức` (repo chính).

**Việc cụ thể:**
1. **N4a — sys.path:** `from tests.xxx import …` lỗi vì bộ chạy không đặt gốc repo vào `sys.path`. Sửa `tests/run_suite.py` và `tools/chay_test_theo_module.py` để gốc repo (thư mục chứa `tests/`) có trong `sys.path`/`PYTHONPATH` của tiến trình chạy test, giữ nguyên `src`. Không sửa từng file test.
2. **N2 — psycopg:** thêm tùy chọn `--runtime <file runtime.local.json>` cho `tools/chay_test_theo_module.py` (và tham số tương đương cho `test.ps1` nếu gọn): đọc `python` và `duong_dan_phu_thuoc` (danh sách thư mục) trong file đó, chạy test bằng Python đó và thêm các thư mục phụ thuộc vào `PYTHONPATH`. File thật nằm ở `<REPO>\var\web\crm-demo\runtime.local.json` — **chỉ đọc 2 khóa `python`, `duong_dan_phu_thuoc`**; KHÔNG mở `ket-noi.local.json` hay `.env`. Không đặt `KHO_PG_DSN_TEST` (test PostgreSQL phải skip, không lỗi). Kiểm: `test_m2_00b_quyen`, `test_m2_00b_tinh` chạy với `--runtime` → số ERROR do thiếu psycopg về 0 (chuyển thành ok hoặc skip).
3. **N3a — CRLF:** repo dùng `core.autocrlf=true` nên worktree ra CRLF trong khi test ghim SHA trên LF. Tìm các test ghim SHA/byte của file trong repo (grep `sha256`, `hashlib` trong `tests/`), xác định đúng các file/đuôi bị ghim, viết `.gitattributes` (mới) đặt `eol=lf` CHỈ cho các file/đuôi đó (không đặt toàn repo). Kiểm bằng cách chạy lại các module đó trong worktree này sau khi `git checkout -- <file>` để áp thuộc tính — nếu sandbox không cho, ghi rõ để lead làm.
4. **N3b — fixture bị .gitignore:** liệt kê các file `.xml`/`.zip` dưới `<REPO>\tests\fixtures\` có trên đĩa nhưng không có trong git (`git ls-files`), mỗi file: đường dẫn, kích thước, có chữ `DEMO` trong tên hoặc nội dung không, MST/tên người bán trong nội dung có phải giá trị giả (ví dụ dãy `0000…`, `DEMO`) không — **chỉ ghi kết luận GIẢ/NGHI THẬT, không in giá trị**. Không chép file, không sửa `.gitignore` (lead quyết).
5. Chạy lại riêng các module bị N3/N4 trong NEN-TEST.md (mỗi module `python -X utf8 tools/chay_test_theo_module.py . --module <tên>`, có/không `--runtime`) và ghi trước/sau.

**File được sửa/tạo (≤ 5):** `tests/run_suite.py`, `tools/chay_test_theo_module.py`, `.gitattributes` (mới), `test.ps1` (chỉ thêm tham số runtime nếu cần), `docs/46-chuyen-doi-dieu-phoi/L0-3A-KET-QUA.md` (mới, ≤ 1 trang: bảng trước/sau + danh sách fixture bước 4).
**Không làm:** sửa code sản phẩm hay file test; cài thư viện; đặt biến PostgreSQL; đọc `var` ngoài đúng file `runtime.local.json`; xóa file.

**Báo cáo cuối (≤ 1 trang, tiếng Việt):** Đã làm · File đổi (kèm thông điệp commit đề xuất `[L0-3a] …`) · Trước/sau theo module · Fixture: số GIẢ / NGHI THẬT · Rủi ro.
