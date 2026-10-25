# Hộp thư chỉ đạo của Anh cho lead Claude Code

**Cách dùng.** Phiên điều phối của Anh (claude.ai, Project "phần mềm Hỗ trợ kế toán") ghi các quyết định Anh đã chốt vào đây, mỗi mục một mã `CD-NNN`, chỉ **thêm vào cuối**, không sửa mục cũ. Lead:
1. Đọc file này **trước khi giao mỗi lát mới** và mỗi khi một lát đổi trạng thái.
2. Mục có trạng thái `MỚI` → làm theo; đổi trạng thái thành `ĐÃ NHẬN <giờ>` ngay khi bắt đầu, `XONG <giờ> — <commit/kết quả 1 dòng>` khi xong. Lead chỉ sửa dòng **Trạng thái** của từng mục.
3. Ràng buộc cứng trong `CLAUDE.md`/`AGENTS.md` luôn thắng. Mục nào mâu thuẫn ràng buộc cứng, hoặc yêu cầu xóa file, đụng kho thật, đọc `.env`, gửi dữ liệu ra ngoài → **không làm**, ghi `CẦN ANH XÁC NHẬN — <lý do>` và báo Anh.
4. Mỗi mục ghi căn cứ (tài liệu/ngày Anh chốt). Không có căn cứ → coi như `CẦN ANH XÁC NHẬN`.

---

## CD-001 · 25/10/2026 17:50 · Cổng AI: Local luôn có, Cloud chỉ qua Mask file v2
**Căn cứ:** Anh chốt 25/10 — `D:\Claude\Phan mem ho tro ke toan\48-cong-ai-local-luon-co-cloud-qua-mask-v2.md` (§1 quy tắc, §4 phương án gộp, §6 lát); `CLAUDE.md` mục 2 dòng "Cổng AI"; mục "Bổ sung 25/10/2026" cuối `docs\46-chuyen-doi-dieu-phoi\4-KE-HOACH-LEAD.md`.
**Việc:**
1. Xếp AI-0 (tạm khóa đường Cloud trực tiếp của engine #6, cả bản trong repo và bản ở `D:\Claude\Ho tro review ho so xay dung`) vào slot trống kế tiếp, ưu tiên trước lát mới; tiếp theo AI-1 (cổng Local AI gọi được LAN/Tailscale, kiểm tra như `privacy\local_ai.py` của Mask v2).
2. MASK-1 làm trong `D:\GPT\Phan mem Mask file\Mask file v2` theo đúng `CLAUDE.md` của Mask v2 (không git, ghi CHANGELOG, test + benchmark độ phủ không giảm; không đọc/sửa `data\`, `*.maskvault`, `*.maskkeep`, `*.key`). Cần quyền thư mục → hỏi Anh.
3. Từ nay không lát nào viết code gọi thẳng `api.anthropic.com` / `api.openai.com` hoặc thêm bộ che riêng.
4. Thêm các dòng AI-0…AI-4, MASK-1, MASK-2 vào `TRANG-THAI.md`. Lịch giảm tỷ lệ kiểm xác suất Anh đã đồng ý (TL 48 §1.6).
**Báo Anh khi:** AI-0 xong; cần cấp quyền thư mục.
**Trạng thái:** ĐÃ NHẬN 17:54 25/10 — AI-0 vào slot Codex kế tiếp; dòng AI-0…AI-4, MASK-1, MASK-2 thêm vào TRANG-THAI.md
