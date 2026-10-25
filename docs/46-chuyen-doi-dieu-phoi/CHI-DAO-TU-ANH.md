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
**Trạng thái:** ĐÃ NHẬN — cập nhật 18:51 25/10: **AI-0 XONG cả hai phần** — AI-0b bản trong repo gộp 06fa717; AI-0a bản độc lập xong (worker Claude; 18 ca test không gọi mạng; 9 test Cloud cũ của engine thất bại đúng thiết kế → xử lý ở AI-3). MASK-1, AI-1 bị dừng khi Anh mở lại phiên → giao lại (xem BAN-GIAO-PHIEN-20261025.md); dòng AI/MASK trong TRANG-THAI.md

## CD-002 · 25/10/2026 18:15 · Trang chủ dạng lưới icon (phương án B) — khung dùng chung, áp CRM trước
**Căn cứ:** Anh chốt 25/10 — `D:\Claude\Phan mem ho tro ke toan\49-trang-chu-luoi-icon.md` (§1 quy tắc, §2 CRM, §3 đặc tả khung, §4 lát + cổng A); TL 42 §0, §2, §16.2 đã sửa cùng ngày (`..\42-man-hinh-crm-ke-toan-va-giao-ket.md`); bản mẫu canvas "Trang chủ lưới icon — CRM" (bảng 1, 3, 5).
**Việc:**
1. Thêm các lát UI-1 (khung dùng chung + áp CRM, worker Claude), UI-2 (máy chủ trả icon/thẻ đã lọc quyền + đếm việc chờ CRM, worker Codex, song song UI-1 sau khi thống nhất dạng dữ liệu), UI-3 (trang chủ hệ thống), UI-4 (áp M2, M4, K5 sau cổng A của UI-1) vào kế hoạch và `TRANG-THAI.md`.
2. Tận dụng code CRM đã có: chỉ thay menu trái chữ bằng thanh icon và thêm trang chủ module; các màn bên trong (danh sách hợp đồng, Báo giá BG-1…) không viết lại. Phối hợp với lát Báo giá đang/ sắp làm để không sửa chồng `crm_g.py`/`crm_g.js` (khóa file chung theo `TRANG-THAI.md`).
3. Bộ icon: mã nguồn mở, ghi giấy phép vào CHANGELOG; không dùng icon của Apple.
4. Xong UI-1 + UI-2: gửi Anh phiếu cổng A theo TL 49 §4 (6 bước thử, 4 vai DEMO).
**Ưu tiên:** sau AI-0 (CD-001); trước các lát mới chưa bắt đầu của CRM.
**Báo Anh khi:** phiếu cổng A của UI-1 sẵn sàng; cần quyết thêm về thẻ tổng quan.
**Trạng thái:** ĐÃ NHẬN 18:46 25/10 — xếp UI-1…UI-4 vào kế hoạch + TRANG-THAI; UI-1 bắt đầu khi có chỗ trống (sau AI-0)


## CD-003 · 25/10/2026 19:20 · Nhật ký lát để báo cáo hiệu quả hằng ngày
**Căn cứ:** Anh yêu cầu 25/10 — phân tích hiệu quả công việc hằng ngày; báo cáo mẫu `docs\46-chuyen-doi-dieu-phoi\bao-cao-ngay\BAO-CAO-NGAY-20261025.md` §3.
**Việc:**
1. Mỗi lát giao/đóng: ghi 1 dòng vào `TRANG-THAI.md` gồm mã lát · worker (Claude/Codex) · model · giờ bắt đầu · giờ kết thúc · số vòng review · kết quả test (xanh/đỏ so NEN-TEST).
2. Cuối ngày (trước 19:30): chạy `/usage`, ghi 1 dòng tổng token/model vào `bao-cao-ngay\USAGE-YYYYMMDD.md`.
3. Không khởi động postgres trong sandbox Codex; lát cần chạy pytest giao worker Claude hoặc ghi "lead chạy test".
4. Giữ tối đa 3 worker cùng lúc.
**Báo Anh khi:** không ghi được model của Codex (cần Anh xem cài đặt Codex).
**Trạng thái:** ĐÃ NHẬN 18:59 25/10 — mở bảng "Nhật ký lát (CD-003)" trong TRANG-THAI.md; model Codex lấy từ cấu hình Codex (gpt-6.1-sol) + mức suy luận ghi theo từng lần giao

## CD-004 · 25/10/2026 19:15 · Nâng lên 6 worker: 2 Claude (thiên về review, Opus) + 4 Codex lát nhỏ
**Căn cứ:** Anh chốt 25/10 19:10–19:15 trong phiên điều phối: "chọn 2 Claude, 4 Codex, nhưng thiên về hướng Claude review và dùng model tốt để review. Giao cho Codex càng nhiều worker càng tốt nhưng lát cắt nhỏ, có kiểm soát." `CLAUDE.md` dòng Worker đã sửa cùng giờ; `D:\Claude\QUY-TRINH-CHUNG\DIEU-PHOI-CLAUDE-CODE-VA-CODEX.md` v1.2 §1.
**Việc (áp dụng từ 26/10):**
1. Tối đa 6 worker cùng lúc = 2 suất Claude + 4 Codex. Sửa tiêu đề "tối đa 3 worker" trong `TRANG-THAI.md` theo mức mới.
2. Chép `docs\46-chuyen-doi-dieu-phoi\cai-dat-claude\agents\review-lat.md` vào `.claude\agents\` (subagent Opus, chỉ đọc). Mọi lát Codex: `kiem-nhanh` (Haiku) → `review-lat` (Opus) → gộp; tối đa 2 vòng review. 2 suất Claude ưu tiên chạy review; còn trống mới nhận lát rủi ro cao (tiền, quyền, xóa dữ liệu) hoặc lát cần pytest.
3. Lát Codex nhỏ: ≤ 3 file sửa, handoff ≤ 1 trang, tiêu chí đạt viết theo nghiệp vụ; mỗi lát ghi nhật ký theo CD-003.
4. Điều kiện chạy song song: mỗi worker worktree + nhánh `lat/` riêng, **CSDL test và cổng web riêng theo mã lát**; khóa file chung trong `TRANG-THAI.md`; không khởi động postgres trong sandbox Codex.
5. **Ngừng giao thêm** khi > 2 lát chờ review, chạm hạn mức gói (Claude hoặc Codex), hoặc test giữa các lát xung đột. Tăng Codex quá 4 chỉ khi Anh duyệt (đề xuất trong báo cáo ngày).
**Báo Anh khi:** CSDL DEMO chưa chạy dịch vụ Windows (điều kiện bắt buộc trước khi lên 4 Codex); hàng chờ review dồn > 2 trong ngày.
**Trạng thái:** ĐÃ NHẬN 19:19 25/10 — đã chép `review-lat` vào `.claude\agents\`; tiêu đề TRANG-THAI sửa theo mức mới (25/10 vẫn 3 worker; từ 26/10: 2 Claude + 4 Codex); từ nay lát Codex chưa gộp (M4-5a v3, UI-2, DA-3a v2, T-MIG2) qua `kiem-nhanh` → `review-lat` trước khi gộp; AI-1, C3c đã gộp 18:58–19:03 (trước CD-004) → review-lat sau gộp. **Báo Anh:** dịch vụ Windows PostgreSQL DEMO **chưa cài** (Anh chưa bấm `CÀI DỊCH VỤ POSTGRES DEMO.cmd`) → chưa lên 4 Codex
