# CLAUDE.md — Phần mềm kho tri thức (bản nháp 23/10/2026, chờ Anh duyệt)

> **Cách dùng bản nháp:** sau khi Codex hợp nhất code và commit (tài liệu 3, bước H), đổi tên file này thành `CLAUDE.md` đặt ở gốc thư mục `Phần mềm kho tri thức`. Không đặt trước bước đó: các worker Codex đang chạy trong `var\codex-dieu-phoi\...` sẽ tự nạp file này.
> File này **bổ sung** cho `CLAUDE.md` ở thư mục cha `Phan mem ho tro ke toan` và cho quy ước Project `claude/00`. Chỗ nào trùng thì file cha thắng, trừ phần "Điều phối" bên dưới (thay cách Codex Root điều phối từ 19/10).

## 1. Vai trò

| Vai | Ai | Làm gì | Không làm |
|---|---|---|---|
| Người duyệt | Anh Dũng | Duyệt checklist; kiểm chức năng ở cổng A; nghiệm thu ở cổng B; quyết định nghiệp vụ | Không gõ lệnh, không đọc log kỹ thuật |
| Lead | Phiên Claude Code chính, model **Opus** | Đọc thiết kế, viết checklist, chia lát, giao worker, gộp nhánh, báo Anh | Không tự viết code lớn khi worker đang làm cùng file |
| Worker | Subagent `worker-lat-man-hinh`, model **Sonnet**, worktree riêng | Viết code + test, **tự chạy test và server**, sửa đến khi xanh | Không đổi phạm vi; không đụng file ngoài danh sách được giao |
| Kiểm nhanh | Subagent `kiem-nhanh`, model **Haiku**, chỉ đọc | Soát lỗi hiển thị, phạm vi diff, kết quả test | Không sửa code |
| Reviewer độc lập | **Codex** (gói thuê bao riêng, không tốn hạn mức Claude) | Đọc diff nhánh, chạy lại test, đối chiếu checklist; giữ `TRANG-THAI.md` | Không giao việc cho Claude, không viết handoff, không freeze/hash |

Tối đa **3 worker chạy cùng lúc**. Khi hết hạn mức phiên: lead dừng giao việc mới, ghi trạng thái, không tự hạ model.

## 2. Ràng buộc cứng (không có ngoại lệ)

- **Không xóa file.** Cần bỏ → chuyển vào thư mục lưu trữ do Anh chỉ định. Không `git clean`, không `git reset --hard`, không `push --force`.
- **Kho thật** `var\plhn-that`, `var\web-that`, `cau_hinh.that.toml`: chỉ đọc qua phần mềm; không sửa, không chép dữ liệu thật vào `tests\fixtures`. Kho thật vẫn SQLite tới khi Anh quyết.
- **Không đọc/in `.env`**, mật khẩu, MST, STK, tên đối tác, số tiền thật trong chat, log, báo cáo.
- M9 · Vốn vay & đầu tư tài chính: **dừng**. Không bật cloud, không nhập Junsky thật, không gọi cổng thuế thật, không bật Request thật.
- Dữ liệu thử: chỉ DEMO/giả lập, người duyệt giả có tiền tố `MO_PHONG_` hoặc `DEMO_`.

## 3. Nguồn yêu cầu

- Yêu cầu chuẩn là tài liệu thiết kế trong Project `phần mềm Hỗ trợ kế toán` (`claude/NN-…`); bản đĩa ở `docs\` là bản sao. Trước khi làm một màn: đọc đúng mục thiết kế (ví dụ Báo giá: TL 42 §6, TL 45).
- Gọi tên module luôn kèm tên chu trình: "M4 · Nghiệm thu & chi phí dự án", không viết trống "M4".
- Giao diện: tiếng Việt nghiệp vụ; **không hiện mã kỹ thuật** (chuỗi có `_`, mã viết hoa liền); ngày `dd/mm/yyyy`; số có dấu chấm hàng nghìn; tiền luôn kèm đơn vị (TL 37 §12, TL 45 BG-05).

## 4. Điều phối: vòng lặp theo màn hình

**Tận dụng tối đa code đã có (Anh yêu cầu 23/10).** Trước mỗi màn, lead đọc `TAN-DUNG-CODE.md` và các nhánh `luu/*`, ghi rõ trong lệnh giao worker: phần nào dùng lại nguyên, phần nào sửa, phần nào viết mới và vì sao. Không viết lại một chức năng đã có code chạy được nếu chỉ để đổi cách tổ chức. Sửa màn hiện có (ví dụ Báo giá theo TL 45) là sửa trên code cũ, không dựng màn mới.

0. **Kiểm kê** — lead liệt kê code đã có cho màn: file, nhánh, đã chạy được tới đâu, thiếu gì so với thiết kế.
1. **Checklist** — lead viết 10–20 dòng kiểm theo ngôn ngữ nghiệp vụ, lấy từ thiết kế; gửi Anh duyệt bằng bảng chọn. Checklist là tiêu chí duy nhất của cổng B.
2. **Khung đi được** — worker dựng luồng mở màn → nhập → lưu → xem lại → in/xuất trên DEMO. Mỗi lát ≤ 1 ngày làm việc, ≤ ~10 file; lớn hơn thì lead chia.
3. **Cổng A · Anh kiểm chức năng** — lead gửi Anh phiếu (tài liệu 2): cách mở, 5–10 bước thử, điểm đã biết chưa làm. Nhận xét của Anh → lead đổi thành task ngay.
4. **Sửa** — worker sửa theo nhận xét; test xanh; `kiem-nhanh` soát; Codex review diff.
5. **Cổng B · Anh nghiệm thu** theo checklist bước 1. Qua cổng B mới làm phần cứng hóa (bảo mật, đồng thời, Word/PDF, hiệu năng) và sang màn kế.

Quy tắc dừng: một lỗi đã sửa **2 lần** chưa xong → worker dừng, lead báo Anh kèm 2–3 phương án. Không lặp chẩn đoán hạ tầng quá 2 lượt khi chưa có giả thuyết mới.

## 5. Định nghĩa "xong" của một lát (worker)

- Test liên quan xanh **và** toàn bộ `test.ps1` không có lỗi mới so với trước lát.
- Đã tự mở server DEMO, tự đi hết các bước thử của phiếu; có ảnh chụp màn hình.
- Báo cáo ≤ 1 trang: làm gì, file đổi, test (số đạt/tổng), điểm còn thiếu, số đo trước/sau nếu có.
- Commit trên nhánh của lát; lead gộp vào nhánh chính sau khi Codex review đạt.

## 6. Git

- Nhánh chính: `chinh`. Mỗi lát một nhánh `lat/<ma-man>-<so>` trong worktree riêng.
- Commit nhỏ, thông điệp tiếng Việt: `[CRM-G2] BG-01 lịch 4 cột`. Gộp bằng merge, không rebase lịch sử đã chia sẻ.
- `.gitignore` giữ nguyên: `var\`, dữ liệu Excel/XML/PDF, `.env` không bao giờ vào git.
- Thay manifest SHA256/thư mục freeze bằng commit + diff. Không tạo thư mục bản sao repo.

## 7. Báo cáo cho Anh

- Theo sự kiện, không định kỳ: "Màn X sẵn sàng kiểm (cổng A/B)", "Cần Anh quyết", "Bị chặn".
- Mỗi quyết định → **bảng chọn** 2–4 phương án, khuyến nghị đặt đầu (quy ước TL 00).
- Trạng thái chung: `TRANG-THAI.md` một trang, ba cột trạng thái: Chưa làm / Đang làm / Anh đã duyệt.

## 8. Lệnh thường dùng

> [LEAD ĐIỀN SAU KHI KIỂM TRÊN MÁY ANH] — lệnh chạy toàn bộ test (`test.ps1`, engine sqlite/postgres), lệnh mở server DEMO cho một worktree (cổng riêng mỗi worker), cách tạo DB DEMO sạch cho worker. Không ghi lệnh mở kho thật vào đây.
