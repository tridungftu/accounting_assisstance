# L0-9 — Dấu xuống dòng của fixture ghim SHA: mọi worktree mới phải ra đúng byte như bản của Anh

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8. Worktree hiện tại, nhánh `lat/l0-9` (từ hop-nhat). Sandbox không ghi `.git`: **không commit, không `git add`** — chỉ sửa tệp và đọc git (`git ls-files --eol`, `git check-attr`, `git show HEAD:<tệp>`).

**Vấn đề (L0-8 báo):** khoảng 24 tệp `tests/fixtures/**` có SHA-256 ghim (trong manifest/test/mã) theo byte **CRLF** như bản làm việc của Anh ở thư mục chính; nhưng worktree mới checkout ra LF vì `.gitattributes` đặt `eol=lf` (hoặc thiếu luật) → test kiểm SHA hỏng và bản sao DEMO (`m2_demo`, `l11_demo`) không dựng được ở worktree; `tools/mo_demo_worktree.ps1` đang chữa cháy bằng cách chép `tests/fixtures` từ repo chính. Ngược lại có tệp (vd `tests/fixtures/junsky_xuat.json`, `regex_patterns.json`) lệch chiều kia. Ví dụ tên: `tests/fixtures/l11_quantity/**`, `tests/fixtures/m2_bridge/{declarations,manifest,workflow}.json`.

**Việc:**
1. Lập bảng mọi tệp trong `tests/fixtures/**` (và `src/kho_tri_thuc/m4/review_goc/**` nếu có ghim) mà có SHA-256 được ghim ở đâu đó trong repo: tệp · nơi ghim (file:dòng) · SHA ghim · SHA của byte LF (`git show HEAD:<tệp>`) · SHA của byte CRLF (chuyển LF→CRLF trong bộ nhớ) · byte nào khớp ghim · luật `.gitattributes` hiện hành (`git check-attr text eol -- <tệp>`).
2. Sửa **chỉ `.gitattributes`** để checkout mới cho đúng byte khớp ghim (vd `eol=crlf` cho nhóm ghim theo CRLF; giữ `-text`/`eol=lf` cho nhóm ghim theo LF). Dùng luật theo thư mục khi cả nhóm cùng kiểu, luật từng tệp khi lẫn. Không đổi SHA ghim, không sửa fixture, không sửa test.
3. Ghi `docs/46-chuyen-doi-dieu-phoi/L0-9-FIXTURE-EOL.md` (≤ 1 trang): bảng ở bước 1 (rút gọn), luật đã thêm, và **lệnh lead phải chạy** sau khi gộp để worktree/thư mục chính nhận đúng byte (vd `git add --renormalize` cho nhóm nào, rồi kiểm bằng một worktree mới). Nêu rõ tệp nào ghim không khớp cả LF lẫn CRLF (nếu có) — không đoán.

**File được sửa/tạo (chỉ):** `.gitattributes`, `docs/46-chuyen-doi-dieu-phoi/L0-9-FIXTURE-EOL.md`.
**Không làm:** sửa fixture/test/mã, `git add`/commit, xóa file, dữ liệu thật.
**Báo cáo cuối (≤ ½ trang):** số tệp mỗi nhóm (ghim CRLF / ghim LF / không khớp) · diff `.gitattributes` · lệnh lead chạy · thông điệp commit `[L0-9] …`.
