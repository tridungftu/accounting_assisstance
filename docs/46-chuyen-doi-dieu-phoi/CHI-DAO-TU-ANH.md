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
**Trạng thái:** ĐÃ NHẬN — cập nhật 18:51 25/10: **AI-0 XONG cả hai phần** — AI-0b bản trong repo gộp 06fa717; AI-0a bản độc lập xong (worker Claude; 18 ca test không gọi mạng; 9 test Cloud cũ của engine thất bại đúng thiết kế → xử lý ở AI-3). cập nhật 19:53: **AI-1 XONG** (gộp cfdf33c; review Opus Đạt → AI-1b đang sửa 3 điểm nhỏ); **MASK-1 XONG** (Mask v2 2.7.0, review Opus vòng 2 Đạt; QD-23/24 Anh chốt); cập nhật 21:25: **MASK-2 XONG** (Mask v2 2.7.1, review Opus Đạt); **AI-2a XONG** 21:30 (gộp 1cf32eb; review Opus độc lập Đạt; Cloud mặc định tắt); AI-2b (nhật ký PG) đang làm; tiếp theo AI-3, MASK-3 (QD-23); dòng AI/MASK trong TRANG-THAI.md

## CD-002 · 25/10/2026 18:15 · Trang chủ dạng lưới icon (phương án B) — khung dùng chung, áp CRM trước
**Căn cứ:** Anh chốt 25/10 — `D:\Claude\Phan mem ho tro ke toan\49-trang-chu-luoi-icon.md` (§1 quy tắc, §2 CRM, §3 đặc tả khung, §4 lát + cổng A); TL 42 §0, §2, §16.2 đã sửa cùng ngày (`..\42-man-hinh-crm-ke-toan-va-giao-ket.md`); bản mẫu canvas "Trang chủ lưới icon — CRM" (bảng 1, 3, 5).
**Việc:**
1. Thêm các lát UI-1 (khung dùng chung + áp CRM, worker Claude), UI-2 (máy chủ trả icon/thẻ đã lọc quyền + đếm việc chờ CRM, worker Codex, song song UI-1 sau khi thống nhất dạng dữ liệu), UI-3 (trang chủ hệ thống), UI-4 (áp M2, M4, K5 sau cổng A của UI-1) vào kế hoạch và `TRANG-THAI.md`.
2. Tận dụng code CRM đã có: chỉ thay menu trái chữ bằng thanh icon và thêm trang chủ module; các màn bên trong (danh sách hợp đồng, Báo giá BG-1…) không viết lại. Phối hợp với lát Báo giá đang/ sắp làm để không sửa chồng `crm_g.py`/`crm_g.js` (khóa file chung theo `TRANG-THAI.md`).
3. Bộ icon: mã nguồn mở, ghi giấy phép vào CHANGELOG; không dùng icon của Apple.
4. Xong UI-1 + UI-2: gửi Anh phiếu cổng A theo TL 49 §4 (6 bước thử, 4 vai DEMO).
**Ưu tiên:** sau AI-0 (CD-001); trước các lát mới chưa bắt đầu của CRM.
**Báo Anh khi:** phiếu cổng A của UI-1 sẵn sàng; cần quyết thêm về thẻ tổng quan.
**Trạng thái:** ĐÃ NHẬN 18:46 25/10 — xếp UI-1…UI-4 vào kế hoạch + TRANG-THAI; UI-1 bắt đầu khi có chỗ trống (sau AI-0); cập nhật 21:15: **UI-2 + UI-2b đã gộp**, UI-1 + UI-1b xong (DEMO 8798, lead thử 4 vai đạt) → **phiếu cổng A gửi Anh**: `docs\46-chuyen-doi-dieu-phoi\PHIEU-CONG-A-TRANG-CHU-LUOI-ICON.md`


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
**Trạng thái:** ĐÃ NHẬN 19:19 25/10 — đã chép `review-lat` vào `.claude\agents\`; tiêu đề TRANG-THAI sửa theo mức mới (25/10 vẫn 3 worker; từ 26/10: 2 Claude + 4 Codex); từ nay lát Codex chưa gộp (M4-5a v3, UI-2, DA-3a v2, T-MIG2) qua `kiem-nhanh` → `review-lat` trước khi gộp; AI-1, C3c đã gộp 18:58–19:03 (trước CD-004) → review-lat sau gộp. cập nhật 19:47: dịch vụ Windows `ktt-postgres-demo` **đã chạy** (Anh bấm 19:40, sẵn sàng 19:46) → đủ điều kiện lên 4 Codex từ 26/10

## CD-005 · 25/10/2026 22:05 · Báo giá — kết quả cổng A bản BG-1d: chưa đạt, 7 điểm sửa BG-18…BG-24
**Căn cứ:** Anh rà màn Báo giá trên DEMO 25/10 21:55 và chốt qua bảng lựa chọn; `D:\Claude\Phan mem ho tro ke toan\45-review-man-bao-gia-sau-lap-trinh.md` §8 (đã cập nhật 25/10 22:05).
**Việc:**
1. BG-18: nút "+ Báo giá mới" to, nổi, ở **đầu** màn danh sách.
2. BG-19: giá trị từng lần thanh toán và dòng tổng Σ chữ to, đậm như khối Tổng giá trị hiện tại.
3. BG-20: lịch 5 cột Lần · **%** · **Giá trị** · Mốc · Ghi chú (hẹp); gõ % → tiền, gõ tiền → %, ô gõ là ô gốc; máy chủ tính khi rời ô; đổi tổng → giữ ô gốc, tính lại ô kia. Thay quy tắc "một ô thông minh" ở TL 45 §3.
4. BG-21: ô "Nhập nhanh lịch": số nguyên `4` → 4 dòng; dãy `10%, 30%, 40%, 10%` → 4 dòng đúng %; bảng có sẵn dòng → hỏi thay.
5. BG-22: khung vai mô phỏng bỏ mã kỹ thuật, ngày dd/mm/yyyy. BG-23: báo lỗi mốc bỏ "(thay n bằng số)", hiện danh sách mốc bấm chọn. BG-24: đơn vị thống nhất "VND".
6. Lát nhỏ ≤ 3 file theo CD-004; review `kiem-nhanh` → `review-lat`; tiêu chí đạt theo bảng TL 45 §8. Phối hợp khóa `crm_g.js`/`style.css` với UI-1.
**Báo Anh khi:** phiếu cổng A lần 2 sẵn sàng (ca thử: 26.500.000.000 VND, nhập nhanh 10/30/40/10%).
**Trạng thái:** ĐÃ NHẬN 22:06 25/10 — chia lát BG-e1…BG-e4 theo thứ tự TL 45 §8 (BG-20, BG-21, BG-19 → BG-18, BG-24 → BG-22, BG-23), làm trên dòng giao diện CRM `lat/ui-1` (= BG-1d + DA-2 + UI-1/UI-2) để không sửa chồng `crm_g.js`/`style.css`; các lát chạm `crm_g.js` làm tuần tự

## CD-006 · 25/10/2026 22:15 · Gộp BG-1d + DA-2 ngay; mốc thanh toán do từng dự án tự khai
**Căn cứ:** Anh chốt 25/10 22:10 qua bảng lựa chọn (Anh nhận xét "chưa thấy phần danh mục dự án bán hàng" trên DEMO; mốc "Xong CNDT" = **Xong chứng nhận đầu tư**); TL 45 §7 mục 4 và §8 BG-23 (cập nhật 22:15); `THIET-KE-DU-AN-DANG-BAN.md`.
**Việc:**
1. **Gộp ngay `lat/bg-1d` + `lat/da-2`** vào nhánh hợp nhất, khởi động lại DEMO để Anh thấy màn **Dự án đang bán** (sáng 26/10). Không chờ BG-18…24; 7 điểm của CD-005 làm tiếp trên nền đã gộp. Ghi trong `TRANG-THAI.md`: cổng A BG-1d chưa đạt, gộp theo lệnh Anh.
2. **Mốc thanh toán theo dự án (lát mới, ≤ 3 file mỗi lát):** màn Dự án đang bán thêm mục **"Mốc thanh toán của dự án"** — dự án tự khai tên mốc (vd "Xong chứng nhận đầu tư"), có phiên bản + nhật ký như các thông số khác của dự án; dự án chưa khai chỉ có **mốc cơ bản** (Ký · Bàn giao · Sổ · Sau ký + n ngày · ngày cố định). Không thêm mốc riêng vào danh mục chung.
3. Báo giá: ô Mốc thời gian lấy danh sách **mốc cơ bản + mốc của dự án đã chọn**; nhận gõ tắt không dấu khớp tên mốc của dự án (vd `cndt`/`CNĐT` → "Xong chứng nhận đầu tư" nếu dự án đã khai); báo lỗi theo BG-23.
4. DEMO: khai mẫu mốc "Xong chứng nhận đầu tư" cho một dự án KCN DEMO để Anh thử.
**Báo Anh khi:** DEMO đã có màn Dự án đang bán; lát mốc dự án sẵn sàng thử.
**Trạng thái:** MỚI

## CD-007 · 25/10/2026 22:20 · Mốc dự án có ngày dự kiến và ngày thực tế (bổ sung CD-006 mục 2)
**Căn cứ:** Anh chốt 25/10 22:10: "nếu mốc chưa có ngày thì không đếm được quá hạn, khi đó nêu ngày dự kiến, khi hết ngày dự kiến vẫn chưa làm xong thì sẽ cho chỉnh ngày dự kiến đó"; TL 45 §7 mục 5.
**Việc (gộp vào lát mốc dự án của CD-006):**
1. Mỗi mốc dự án có **ngày dự kiến** (bắt buộc khi khai) và **ngày thực tế** (ghi khi xảy ra).
2. Chưa có ngày thực tế: đợt gắn mốc hiện "dự kiến dd/mm/yyyy" ở Báo giá, Lịch nghĩa vụ, Danh sách hợp đồng (cột Đợt kế tiếp); **không đếm quá hạn**.
3. Qua ngày dự kiến mà chưa có ngày thực tế: tạo việc chờ "Chỉnh ngày dự kiến mốc …" cho người phụ trách dự án (đếm vào số trên icon theo TL 49); chỉnh ngày dự kiến bắt buộc lý do, ghi nhật ký cũ → mới, ai, lúc nào.
4. Ghi ngày thực tế: đợt gắn mốc có ngày đến hạn = ngày thực tế (+ n ngày nếu đợt khai) → đếm đến hạn/quá hạn như đợt ngày cố định; ghi nhật ký.
5. Test: mốc chưa có ngày thực tế không vào danh sách quá hạn; qua ngày dự kiến sinh đúng 1 việc chờ; ghi ngày thực tế → đợt đổi trạng thái đúng.
**Trạng thái:** MỚI

## CD-008 · 25/10/2026 22:25 · CHẠY ĐÊM 25→26/10 (không có Anh), báo cáo lúc 05:45
**Căn cứ:** Anh yêu cầu 25/10 22:13 "điều phối máy chạy đêm nay, các module và lát cắt thực hiện tuần tự, sáng mai 6h báo cáo điều phối, việc đã làm và chưa làm"; Anh chốt 22:20 dùng **mức 6 worker như CD-004** cả đêm.
**Khung:** từ khi nhận đến **05:30 26/10** giao lát; 05:30–05:45 chỉ thu lát đang chạy, kiểm, gộp; **05:45 viết báo cáo**; sau đó dừng giao việc.
**Thứ tự ưu tiên (làm theo thứ tự, mỗi module lát nối tiếp theo phụ thuộc; các module khác nhau chạy song song tới mức CD-004):**
1. **DEMO mở được có CRM** (L0-10) — để 6h Anh kiểm cổng A Báo giá và Trang chủ lưới icon.
2. CD-006 bước 1: gộp `lat/bg-1d` + `lat/da-2` vào hợp nhất; DEMO có màn Dự án đang bán.
3. CD-005: BG-e1…BG-e4 (BG-18…24) → **phiếu cổng A lần 2 Báo giá sẵn trước 6h**.
4. CD-006 bước 2–4 + CD-007: mốc thanh toán theo dự án (ngày dự kiến / thực tế).
5. UI-2b; UI-3 dựng trên `lat/ui-1` (**không gộp UI-1/UI-3** khi Anh chưa qua cổng A).
6. Hàng đợi còn lại trong `4-KE-HOACH-LEAD.md` theo thứ tự (AI-3, M4-5b, …).
**Quy tắc đêm:**
- Việc cần Anh quyết → **không chờ**: ghi vào báo cáo mục "Cần Anh", chuyển lát kế.
- Mỗi lát: `kiem-nhanh` → `review-lat` (Opus) → gộp **nhánh hợp nhất** chỉ khi xanh so nền; đỏ → giữ nhánh, ghi lý do. Không gộp `chinh`, không push GitHub, không xóa file, không đụng kho thật (ràng buộc `CLAUDE.md`).
- Một lát lỗi/không đạt **2 lần** → dừng lát đó, ghi lý do, sang lát khác (không quay vòng).
- Ngừng giao thêm khi > 2 lát chờ review, xung đột test giữa lát, hoặc chạm hạn mức gói: Claude chạm hạn mức → ghi giờ, để Codex chạy hết lát đã giao, chỉ giao Codex lát không cần review Opus ngay (review dồn sáng); Codex chạm hạn mức → ghi giờ, chuyển lát cho Claude Sonnet nếu còn hạn mức.
- Không khởi động lại máy, không cập nhật phần mềm, không dừng dịch vụ PostgreSQL.
- Nhật ký CD-003 đủ từng lát (worker, model, giờ, vòng review, test).
**05:45 viết `docs\46-chuyen-doi-dieu-phoi\bao-cao-ngay\BAO-CAO-DEM-20261026.md`:** §1 Kết luận (≤ 5 dòng) · §2 Đã xong (lát, commit, test so nền, gộp chưa) · §3 Chưa xong / bị chặn + lý do · §4 Cần Anh quyết · §5 Anh kiểm gì lúc 6h (cổng A nào, DEMO cổng nào, phiếu nào) · §6 Số liệu (giờ chạy từng khối, số worker cao nhất, Claude/Codex, model, vòng review, `/usage` nếu có). Cập nhật dòng Trạng thái của CD-005…CD-008.
**Trạng thái:** MỚI
