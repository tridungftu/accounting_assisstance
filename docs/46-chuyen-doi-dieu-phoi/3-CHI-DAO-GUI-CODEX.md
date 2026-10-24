# Chỉ đạo gửi Codex Root — hợp nhất code, dọn thư mục, đổi vai

**Ngày:** 23/10/2026 · **Người ra lệnh:** Anh Dũng · **Trạng thái:** Anh đã chốt 4 điểm lúc 23/10 tối (dừng ngay tối nay; lưu trữ ở `LUU-TRU`; sao lưu dữ liệu thật cũng chuyển vào `LUU-TRU`; đẩy GitHub sau khi Anh xem kết quả test) — dán cho Codex.

> **Nguyên tắc của Anh: tận dụng tối đa những gì đã code.** Không bỏ một dòng code nào chỉ vì chưa qua kiểm độc lập. Mọi code đã viết phải nằm trong git (nhánh chính hoặc nhánh lưu) trước khi chuyển thư mục; thư mục lưu trữ chỉ bị xóa sau này khi chắc chắn phần mềm không còn dùng tới.
Lệnh này thay cách điều phối từ 19/10 (Codex Root giao Claude qua handoff/freeze/hash). Ràng buộc cũ vẫn giữ: **không xóa file**, kho thật SQLite, M9 dừng, không cloud/Junsky/cổng thuế/Request thật, không đưa dữ liệu thật vào fixture, Source37 không áp.

---

## 0. Lý do và quyết định của Anh

- 5 ngày chưa có màn nào được Anh nghiệm thu; Anh mới được xem giao diện 2 lần, bản ở cổng 64901 là bản cũ. Màn Báo giá lệch thiết kế (TL 45: 6 điểm chặn, 8 điểm khó dùng).
- Quyết định: **giao hết nhưng Anh kiểm chức năng sớm** — mỗi màn có cổng A (Anh thử khung, góp ý sớm) và cổng B (Anh nghiệm thu theo checklist).
- **Claude Code là lead điều phối và lập trình**, worker được tự chạy test/server trong worktree git. **Codex chuyển sang vai reviewer độc lập** và giữ bảng trạng thái một trang.

## 1. Hiện trạng đo được (23/10, Claude đọc trên máy Anh)

| Chỉ số | Giá trị |
|---|---|
| Git của repo | **1 commit** (03/10/2026, V10); 408 file chưa theo dõi + 31 file sửa chưa commit |
| Code mới nhất | Cây chính `src\` + `tests\` sửa lần cuối ngày 22/10; toàn bộ việc ngày 23/10 chỉ nằm trong các thư mục `*-code-frozen-*` |
| `var\codex-dieu-phoi` | 1.584 mục cấp 1 (1.025 thư mục, 559 file); 156 bản `continuity-*.json` (~0,6 MB mỗi bản); 129 thư mục frozen; 113 `before-*`; 297 `*prepared*`; 26 bản sao toàn repo trong `isolated-head-jobs` |
| Dung lượng đã đo | 673/1.584 mục đầu: **2,60 GB, 48.153 file** (riêng `kiem-chung-20261018-101441` 1,36 GB); phần còn lại chưa đo |
| File .md trong `codex-dieu-phoi` | 2.238 (không tính bản sao trong snapshot); `HANG-DOI-YEU-CAU`, `CHANGELOG`, `CHUONG-TRINH…` mỗi file có 55–57 bản sao |
| `docs\` | 323 file; 117 REVIEW, 84 GIAO, 51 BAO-CAO |
| Gốc repo | 36 mục; `README.md` còn mô tả V11; `KE-HOACH-MODULE…`, `DU-LIEU-VA-QUYET-DINH…` từ 17/09 |
| Worker Claude | Chỉ 5 công cụ, **cấm Bash** (`settings01.json`), model `claude-opus-5-5`; handoff CRM42-01 qua 5 bản (19,5→29,4 KB) trong 28 phút trước khi có dòng code nào |

## 2. Bước D0 — dừng (ngay tối 23/10, Anh đã chốt)

1. Không dispatch gói mới. Worker đang chạy: để về terminal; nếu sau 60 phút chưa terminal thì dừng sạch và ghi trạng thái dở.
2. Tắt nhịp báo 30 phút và mọi lịch tự động. Không mở thêm probe Word COM (giữ phương án: hệ thống xuất DOCX, PDF tạm xuất tay).
3. Ghi một file `DUNG-20261023.md` ≤ 1 trang: worker nào dừng ở đâu, gói nào dở.

## 3. Bước H — hợp nhất code về một chỗ (trước mọi việc dọn)

Mục tiêu: sau bước này **cây chính + git là nơi duy nhất có code mới nhất**; mọi thư mục frozen chỉ còn là lịch sử.

1. **H1 · Commit nguyên trạng** cây chính hiện tại thành `chinh` với thông điệp "Nền 22/10 trước hợp nhất". Kiểm `.gitignore` trước: không để `var\`, `.env`, Excel/XML/PDF/SQLite vào commit.
2. **H2 · Bảng head** — một dòng mỗi nhánh việc: nhánh · thư mục frozen cuối · đã terminal chưa · trạng thái kiểm độc lập · đích (chính / nhánh lưu) · lý do. Điểm xuất phát theo `PROGRESS-20261023-ROOT-RESUMED.md`: M4 UI copy `m4-04b-ui-copy-20261023-01-code-frozen-c478b6382bb0`, CRM G5 `crm-g5-doi-chieu-20261023-01-code-frozen-3cb518064b79`, common FIX04, M2-00A FIX02, M2-00B FIX01, master reuse, financial 03B02A, engine E5, Request UI04B. Rà thêm mọi thư mục `*-code-frozen-*` và `isolated-head-jobs\*\workspace` để không sót nhánh nào.
3. **H3 · Đưa code vào git, không bỏ nhánh nào:**
   - Nhánh đã terminal (kể cả chưa kiểm độc lập): áp thành một commit riêng trên nhánh `hop-nhat-20261023`, theo thứ tự phụ thuộc; thông điệp ghi nguồn frozen và trạng thái kiểm ("đã kiểm độc lập" / "chưa kiểm").
   - Nhánh dở hoặc xung đột với nhánh khác: commit nguyên trạng vào nhánh lưu riêng `luu/<ten-nhanh>` từ nền H1, không gộp vào chính. Lead Claude sẽ dùng lại khi tới màn đó.
   - Không sửa code để test qua.
4. **H3b · Bảng tận dụng** `TAN-DUNG-CODE.md` (≤ 2 trang): mỗi màn/chức năng đã có code một dòng — màn · file chính · nhánh git · đã chạy được tới đâu (pure / PostgreSQL / HTTP / giao diện) · thiếu gì so với thiết kế. Đây là đầu vào bắt buộc của lead trước khi giao worker.
5. **H4 · Chạy toàn bộ `test.ps1`** (sqlite; postgres nếu chạy được trên DEMO). Ghi số đạt/lỗi/bỏ qua. Lỗi giữ nguyên, lập danh sách — đây là đầu vào việc đầu tiên của lead.
6. **H5 · Gộp** `hop-nhat-20261023` vào `chinh` khi Anh đồng ý báo cáo H4, rồi **đẩy lên repo GitHub riêng tư hiện có** (Anh đã đồng ý; đẩy cả các nhánh `luu/*`). Trước khi đẩy, kiểm lại không có `.env`, `var\`, Excel/XML/PDF/SQLite trong commit.

## 4. Bước D — dọn thư mục (chỉ di chuyển, không xóa)

### D1 · Lập bảng kê trước khi chuyển
`DON-DEP-BANG-KE.csv`: đường dẫn · loại · dung lượng · số file · ngày sửa cuối · nhóm đề xuất · có được file `.cmd`/`.ps1`/`cau_hinh*.toml` tham chiếu không. Thư mục bị tham chiếu → **giữ**. Anh đã duyệt các nhóm ở D3; mục nào không thuộc nhóm nào, hoặc ghi [CẦN ANH XÁC NHẬN], thì giữ nguyên và hỏi Anh bằng bảng chọn.

### D2 · Đích lưu trữ (Anh đã chốt)
`D:\Claude\Phan mem ho tro ke toan\LUU-TRU\20261023-codex\` — ngoài repo, cùng ổ D nên di chuyển gần như tức thì. Mỗi nhóm một thư mục con + `INDEX.md` ghi nguồn gốc. Sao lưu chứa dữ liệu thật để riêng ở `LUU-TRU\20261023-codex\du-lieu-that\`, không bao giờ vào git.
Thư mục lưu trữ **chỉ bị xóa sau này** khi lead xác nhận code trong đó đã có trong git và phần mềm không còn dùng tới — việc xóa do Anh quyết.
Điều kiện trước khi chuyển: bước H đã xong và mọi thư mục frozen/workspace đã có dòng tương ứng trong bảng H2.

### D3 · Đề xuất phân nhóm

| Nhóm | Gồm | Đề xuất |
|---|---|---|
| Điều phối Codex | toàn bộ `var\codex-dieu-phoi\` sau bước H | Chuyển nguyên thư mục sang lưu trữ; để lại trong repo đúng 3 file: `continuity-current.json`, `PROGRESS-20261023-ROOT-RESUMED.md`, `USER-RESUME-AUTHORIZATION-20261023-01.json` (chuyển sang `docs\luu-tru\dieu-phoi-codex\`) |
| Sao lưu trước nâng cấp | `var\sao-luu-truoc-V10…V13`, `sao-luu-truoc-xoa-T7T8-20261012` | Chuyển vào `du-lieu-that\` (Anh đã chốt). Kiểm không có launcher/cấu hình trỏ tới trước khi chuyển |
| Bản cũ kho thật | `var\plhn-that.cu-20260925-1211`, `var\plhn-that.pre-v9b-…` | Như trên |
| Thử nghiệm/demo cũ | `var\demo-*`, `full-demo-*`, `r5-*`, `ui-check`, `ui-test-input`, `launcher-smoke`, `thu-nghiem-claude-2026-09-18`, `vong-2`, `v13`, `crm-feedback-20261020-…` | Chuyển lưu trữ, trừ thư mục `README.md` đang trỏ tới (`full-demo-final-v2`) — kiểm tham chiếu |
| `var\_to_delete` | đã có sẵn | Chuyển lưu trữ, Anh tự xóa sau nếu muốn |
| **Giữ nguyên** | `var\plhn-that`, `var\web-that`, `var\web`, `var\app-runtime`, `var\kiem-thu-that`, `var\web-thu-T8`, `var\m1-fixture`, `var\test-results` | Không đụng. [CẦN ANH XÁC NHẬN `kiem-thu-that`, `web-thu-T8`] |
| Gốc repo | `BO-PROMPT-CODEX.md`, `BO-PROMPT-CODEX-VONG-2.md`, `KE-HOACH-MODULE-VA-LO-TRINH.md`, `KE-HOACH-PHAN-MEM-KHO-TRI-THUC.md`, `DU-LIEU-VA-QUYET-DINH-CAN-CHOT.md` | `git mv` vào `docs\luu-tru\goc\`. Giữ ở gốc: `README.md` (viết lại ngắn), `CHANGELOG.md`, `HANG-DOI-YEU-CAU.md`, file `.cmd`, `.ps1`, cấu hình. Hai file Excel danh mục đối tác giữ nguyên (dữ liệu thật, không vào git) |
| `docs\` | REVIEW-*, GIAO-*, BAO-CAO-* của các gói đã đóng | `git mv` vào `docs\luu-tru\<module>\`; giữ ở `docs\` tài liệu thiết kế, quyết định, hướng dẫn, `HANG-CHO-CRM-41-42.md`; thêm `docs\INDEX.md` một trang |
| `HANG-DOI-YEU-CAU.md` | 91 KB, phần đầu là các khối trạng thái chồng nhau | Tách: phần lịch sử sang `docs\luu-tru\HANG-DOI-LICH-SU-den-20261023.md`; file gốc chỉ giữ danh sách việc còn mở |

### D4 · Kiểm sau khi chuyển
- Nhấp đúp **MỞ PHẦN MỀM.cmd** và **MỞ BẢN DEMO.cmd**: khởi động bình thường, không báo thiếu thư mục.
- `test.ps1` cho cùng kết quả như H4.
- Báo Anh: số mục/dung lượng trước và sau ở gốc repo, `docs\`, `var\`.

## 5. Vai mới của Codex sau khi chuyển

**Làm:**
- Review độc lập mỗi nhánh lát lead báo xong: đọc diff, chạy lại test, đối chiếu checklist cổng B của màn đó. Kết quả `REVIEW-<ma-lat>.md` ≤ 1 trang: Đạt / Cần sửa (mỗi điểm một dòng, có file:dòng).
- Giữ `TRANG-THAI.md` một trang: mỗi màn một dòng, cột Chưa làm / Đang làm / Chờ Anh cổng A / Chờ Anh cổng B / Anh đã duyệt.

**Không làm:** giao việc hoặc gọi Claude; viết handoff kỹ thuật; tạo thư mục freeze, manifest SHA256, bản sao repo; nhịp báo định kỳ; sửa code sản phẩm (trừ khi Anh giao riêng).

## 6. Báo cáo kết thúc gửi Anh (một trang)

1. D0: worker đã dừng, gói dở.
2. H: bảng head (vào chính / nhánh lưu); `TAN-DUNG-CODE.md`; kết quả test sau hợp nhất (đạt/lỗi/bỏ qua); commit cuối của `chinh`; đã đẩy GitHub chưa.
3. D: số mục và dung lượng trước/sau; nơi lưu trữ; danh sách giữ nguyên.
4. Các điểm cần Anh quyết — đưa dạng bảng chọn.
