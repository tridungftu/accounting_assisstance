# review-lat sau gộp: AI-1 + C3c (vòng 1/2, CHỈ ĐỌC)

Hai lát Codex đã gộp vào `hop-nhat-20261023` lúc 18:58–19:03 25/10, trước khi CD-004 yêu cầu `review-lat` trước khi gộp → review bù. Đọc `CLAUDE.md` (repo + thư mục cha). Chỉ đọc; Bash chỉ cho `git diff/log/show`, chạy test thuần, tìm chuỗi. Không sửa code, không commit, không khởi động PostgreSQL/server, không gọi mạng.

## AI-1 — Cổng Local AI qua LAN/Tailscale (commit `2bac0bc`, gộp `cfdf33c`)
Handoff: `docs/46-chuyen-doi-dieu-phoi/giao-viec-20261025/giao-ai-1.md`; báo cáo worker `bao-cao-ai-1.md`; căn cứ TL 48 `D:\Claude\Phan mem ho tro ke toan\48-cong-ai-local-luon-co-cloud-qua-mask-v2.md` §1.2. Diff: `git show 2bac0bc`.
Kiểm thêm: (1) không đường nào tra DNS/đi proxy/theo chuyển hướng (kể cả `/v1/models`, `/api/tags`); (2) IP ngoài loopback/RFC1918/Tailscale bị từ chối, kể cả IPv6 ánh xạ IPv4, `0.0.0.0`, link-local; (3) đích Tailscale bắt buộc nguồn Tailscale; (4) model cloud/`remote_host` bị từ chối trước khi gửi nội dung kế toán; (5) cấu hình cũ `http://localhost:…` nay bị tắt — thông báo có dẫn người dùng sửa không; (6) lỗi Local AI không làm hỏng đề xuất (`choose_counterparty` trả `None`).

## C3c — S1 che cờ QUÁ HẠN/THIẾU CĂN CỨ khi không có quyền xem tiền (commit `f3b7814`, gộp `2ea1258`)
Handoff: `giao-c3c.md`; báo cáo `bao-cao-c3c.md`; căn cứ `docs/QUYET-DINH.md` QD-20261025-15, -22 và TL 42 §1 `D:\Claude\Phan mem ho tro ke toan\42-man-hinh-crm-ke-toan-va-giao-ket.md`. Diff: `git show f3b7814`.
Kiểm thêm: (1) người không có quyền xem tiền không suy ra được tiền/lịch thu qua cờ, thẻ W1–W5, bộ lọc `co=QUA_HAN|THIEU_CAN_CU`, số đếm `tong`, thứ tự sắp xếp; (2) người có quyền vẫn thấy đủ như trước; (3) trộn phạm vi (có quyền ở pháp nhân này, không ở pháp nhân kia) đúng từng dòng; (4) test đã chạy có PostgreSQL 43/43 — ca nào còn thiếu.

**Kết luận:** mỗi lát Đạt / Không đạt; ≤ 10 điểm/lát, mức **Chặn / Nên sửa / Để sau** (đã gộp nên "Chặn" = phải sửa ngay bằng lát sửa), tệp:dòng, tiếng Việt, ≤ 1 trang.
