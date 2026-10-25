# L0-2i — Tìm code/test chỉ có trong bản chụp Codex cũ, chưa vào git

Bạn là worker Codex, chạy không tương tác (`codex exec`). Lát này Anh đã duyệt qua lead: **làm ngay đến hết, không hỏi lại**. Đọc trước `AGENTS.md` ở thư mục hiện tại.

**Mã hóa:** mọi file là UTF-8; đọc bằng `python -X utf8`, ghi UTF-8 không BOM.

**Bối cảnh:** đợt hợp nhất H3 tuyên bố "mọi code đã vào git" (nhánh `hop-nhat-20261023` + các nhánh `luu/*`). Lead vừa phát hiện `tests/test_m4_03a_pg.py` (được `tests/test_m4_03b_common_pg.py` import) KHÔNG có ở nhánh nào, chỉ có trong các bản chụp ở `<REPO>\var\codex-dieu-phoi\`. Cần biết còn bao nhiêu file như vậy.
`<REPO>` = `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức` (repo chính). Thư mục hiện tại là worktree `lat/l0-2i` của repo đó (cùng kho git, dùng `git` ở đây để đọc mọi nhánh).

**Việc cụ thể (CHỈ ĐỌC dữ liệu, chỉ ghi 3 file đầu ra bên dưới):**
1. Liệt kê các bản chụp code trong `<REPO>\var\codex-dieu-phoi\`: thư mục có tên chứa `frozen` và có thư mục con `files\`, và `isolated-head-jobs\*\workspace\`. Với mỗi bản chụp lấy thời điểm sửa đổi mới nhất.
2. Chỉ xét file dưới `src\`, `tests\`, `tools\` có đuôi `.py .js .css .html .sql .json .tsv .md` (bỏ `__pycache__`, `.pyc`, `tests\fixtures\` có đuôi khác, mọi file `.xlsx .xls .xml .pdf .docx .sqlite .db .zip`). KHÔNG mở thư mục `var\` lồng bên trong bản chụp, không mở `.env*`, `cau_hinh*.toml`, `TRI-THUC-CFO.json`. Không in nội dung file ra báo cáo.
3. Lập tập blob của mọi nhánh: `git ls-tree -r <nhánh>` cho `hop-nhat-20261023`, `chinh` và mọi `luu/*`. So nội dung **sau khi bỏ `\r`** (repo dùng core.autocrlf=true) — tính SHA1 kiểu blob git trên nội dung đã chuẩn hóa, hoặc tự so chuỗi.
4. Phân loại:
   - **A — đường dẫn không có ở nhánh nào** (như `tests/test_m4_03a_pg.py`). Với mỗi đường dẫn: các bản chụp chứa nó, bản mới nhất, số phiên bản nội dung khác nhau, file nào trên `hop-nhat` import/tham chiếu tới nó (grep tên module).
   - **B — đường dẫn có ở git nhưng nội dung bản chụp MỚI NHẤT của một gói không khớp nhánh nào**. Chỉ xét các bản chụp "code-frozen" là head trong `docs\46-chuyen-doi-dieu-phoi\TAN-DUNG-CODE.md` (cột Frozen head) — không xét mọi bản cũ.
5. Đề xuất cho mỗi file nhóm A: nên đưa vào nhánh nào (gói nào sở hữu, theo tên bản chụp) — chỉ đề xuất, không commit.

**Đầu ra (ghi trong worktree hiện tại):**
- `tools/do_file_chua_vao_git.py` — script làm bước 1–4, chạy lại được, tham số đường dẫn repo.
- `docs/46-chuyen-doi-dieu-phoi/FILE-CHUA-VAO-GIT.csv` — nhóm, đường dẫn, bản chụp mới nhất, số phiên bản, ai tham chiếu, đề xuất nhánh.
- `docs/46-chuyen-doi-dieu-phoi/FILE-CHUA-VAO-GIT.md` — ≤ 1 trang: số file nhóm A/B, 10 file quan trọng nhất (được code trên hop-nhat import), đề xuất.

**Không làm:** git add/commit (sandbox không ghi được `.git`, lead sẽ commit); sửa code; chép file vào `src`/`tests`; xóa gì; đọc kho thật hay dữ liệu.

**Báo cáo cuối (≤ 1 trang, tiếng Việt)** — tin nhắn cuối của bạn: Đã làm · File đầu ra · Số liệu A/B · 10 file quan trọng nhất · Rủi ro/điểm chưa chắc.
