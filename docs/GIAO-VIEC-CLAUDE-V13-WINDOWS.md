# Giao việc Claude Code — kiểm chứng và sửa V13 trên Windows

Ngày: 18/10/2026. Căn cứ: goal hiện hành, TL 35/37/38/39/40, phương án C đã chốt. Codex điều phối và kiểm tra độc lập; Claude Code sửa mã chính. Chỉ triển khai V14 sau khi hoàn tất gate V13. Phạm vi tiếp theo: `PHAM-VI-UY-QUYEN-CODEX.md`.

## Ranh giới

- Không reset, checkout đè, clean hoặc commit thay đổi chưa rõ nguồn; working tree có công việc V11–V13 từ trước.
- Giữ phương án C trong V13; không chuyển lõi sang K2 trước V14, không chuyển kho thật sang PostgreSQL.
- Không đọc hoặc gửi `var/`, `.env`, backup, chứng từ, giao dịch, tên đối tác, số tài khoản hay secrets vào Claude. Dữ liệu thật do Codex xử lý cục bộ trên snapshot. Claude tự chạy test DEMO; actor cho mô phỏng có tiền tố `MO_PHONG_`.
- Không bật cloud AI của ứng dụng, mở mức 2 Junsky, nhập Junsky, duyệt nghiệp vụ hoặc tri thức thật. Không dùng `CFO_NTD` thay người dùng.
- Không thêm thư viện ngoài các dependency đã chốt nếu chưa có quyết định; PostgreSQL/psycopg thuộc V13 đã chốt.

## Đầu vào đã có

- Bản baseline mã và tài liệu đã chép/kiểm SHA-256; snapshot SQLite bằng backup API: 50 bảng, 104.719 dòng, integrity `ok`. Toàn bộ ở `var/codex-dieu-phoi/`; Claude không đọc thư mục này.
- Windows Python 3.13.14: 296 bài được runner liệt kê; 268 thực chạy đạt, 28 bài PostgreSQL bị skip khi thiếu môi trường. Không gọi đây là 296 bài đã đạt.
- Sao kê trên snapshot: 105 WAIT, đã recompute đủ 105; cutoff 30/06/2026, scoring mode bật. Lần đo đầu 31,942 giây, chưa đạt ngưỡng 10 giây. Mức 62/33/10; chấm được 105, chưa ghép đáp án 17. Đây là số đo hiện tại, không phải tiêu chí chất lượng đã được phê duyệt.
- Có đủ file đáp án Junsky và 75 XML T8 trên máy. Kho thử đang giữ đường dẫn XML cũ; Codex sửa cấu hình chỉ trên bản sao kiểm chứng.

## Đợt 1 — sửa cổng kiểm chứng, an toàn dữ liệu và phục hồi

| Việc | Đầu vào / file liên quan | Đầu ra | Tiêu chí đạt |
|---|---|---|---|
| A1 — Cổng parity không đạt giả | `tools/song_song_t8.py`, `tools/song_song_t8.ps1`, `QuickPosting.repropose/score` | Phân biệt PASS/FAIL/NOT_VERIFIED; khóa run/tháng/cutoff, đếm eligible và thực recompute; tách timing khỏi đáp án | Tập rỗng, thiếu dữ liệu, cùng lỗi chấm, skip, không recompute đủ đều không PASS; lệch dòng/đáp án hoặc quá 10 giây làm gate chưa đạt; test DEMO tình huống biên |
| A2 — Parity hóa đơn và grading từng dòng | Cùng công cụ, reader hóa đơn V12 | Nhận bộ 105 sao kê + 75 hóa đơn; chấm riêng mua/bán; chỉ in aggregate | So cả mức/TK/đối tượng/dự án/TTCP/dòng bút toán và kết quả chấm từng dòng; không so thời gian như nội dung đáp án; báo unmatched đúng |
| A3 — Restore schema cố định | `ha_tang/backup.py`, `ha_tang/ket_noi.py`, test restore hiện dùng schema auto | Restore snapshot vào đích tách biệt đúng hoặc từ chối rõ trước khi mở kho | DEMO: backup trước, thêm dòng sau, restore bằng config schema cố định; không được âm thầm mở dữ liệu hiện hành. Kiểm count/hash sau mở lại |
| A4 — Không lộ dữ liệu qua lỗi | `tools/chuyen_sqlite_sang_pg.py` phần bắt `psycopg.Error` | Chỉ sqlstate/mã chung, không `diag.message_primary` chứa giá trị | Test chuỗi DEMO nhạy cảm gây lỗi ép kiểu; stdout/stderr/report không chứa chuỗi đó |
| A5 — Đối chiếu bộ chuyển | `tools/chep_v12_sang_pg.py`, `ha_tang/sao_chep_bang.py`, `tools/chuyen_sqlite_sang_pg.py` | Tách metadata marker do migration thêm; tái tính hash dữ liệu nguồn/đích, không chỉ chép giá trị hash | DEMO nguồn V12 không marker nạp thành công, dữ liệu nghiệp vụ đủ; sửa một giá trị đích phải phát hiện; chạy lại không trùng |
| A6 — Sao lưu/phục hồi K2 | `tools/sao_luu_pg.py`, `tools/dong_bo_dem.ps1` | `pg_dump` + restore kiểm chứng toàn bộ K2 và nhật ký, ngoài backup V12 | Thiếu schema không exit 0; backup/restore DB tạm, count/hash khớp, quyền ứng dụng và audit append-only giữ nguyên |

Claude sửa A1–A6 theo nhóm file không trùng bên kiểm tra. Tự chạy test DEMO và báo file thay đổi, test đã thực chạy, skip và giới hạn. Codex đọc diff, tự kiểm tra, giao sửa tiếp trong cùng session. Review độc lập cuối V bởi agent không triển khai; 0 lỗi chặn mới được kết luận gate.

## Đợt 2 — kiểm chứng trên dữ liệu tại máy

Codex thực hiện trên snapshot riêng sau khi đợt 1 đạt: hai engine, migration hai lần, count/hash, 105+75 từng dòng, grading Junsky, cutoff/leakage, hiệu năng, quyền ứng dụng/audit, backup/restore, rollback, GUI DEMO. Không gửi dữ liệu từng dòng cho Claude; chỉ aggregate và lỗi đã làm sạch. Tối ưu hiệu năng theo profile, giữ kết quả từng dòng; không hạ tiêu chí để đạt.

## Điểm tiếp tục

1. Hoàn tất đăng nhập Claude Code và quyền gửi mã nội bộ tới Anthropic theo auto-review; kiểm chứng bằng nhiệm vụ chỉ đọc trước.
2. Giữ session đã kiểm chứng, giao A1–A6 với ranh giới ở trên; chưa thay mã khi chưa có baseline.
3. Tiếp tục kiểm chứng môi trường PostgreSQL và các phần độc lập; chưa đánh dấu V13 hoàn thành.
