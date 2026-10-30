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
**Trạng thái:** XONG phần lập trình 26/10 00:58 — BG-e1…e7 (BG-18…24) trên dòng giao diện `lat/ui-dem`, review-lat Đạt; **phiếu cổng A lần 2 sẵn**: `docs\46-chuyen-doi-dieu-phoi\PHIEU-CONG-A-BAO-GIA-LAN-2.md`, DEMO cổng 8798. Chờ Anh thử.

## CD-006 · 25/10/2026 22:15 · Gộp BG-1d + DA-2 ngay; mốc thanh toán do từng dự án tự khai
**Căn cứ:** Anh chốt 25/10 22:10 qua bảng lựa chọn (Anh nhận xét "chưa thấy phần danh mục dự án bán hàng" trên DEMO; mốc "Xong CNDT" = **Xong chứng nhận đầu tư**); TL 45 §7 mục 4 và §8 BG-23 (cập nhật 22:15); `THIET-KE-DU-AN-DANG-BAN.md`.
**Việc:**
1. **Gộp ngay `lat/bg-1d` + `lat/da-2`** vào nhánh hợp nhất, khởi động lại DEMO để Anh thấy màn **Dự án đang bán** (sáng 26/10). Không chờ BG-18…24; 7 điểm của CD-005 làm tiếp trên nền đã gộp. Ghi trong `TRANG-THAI.md`: cổng A BG-1d chưa đạt, gộp theo lệnh Anh.
2. **Mốc thanh toán theo dự án (lát mới, ≤ 3 file mỗi lát):** màn Dự án đang bán thêm mục **"Mốc thanh toán của dự án"** — dự án tự khai tên mốc (vd "Xong chứng nhận đầu tư"), có phiên bản + nhật ký như các thông số khác của dự án; dự án chưa khai chỉ có **mốc cơ bản** (Ký · Bàn giao · Sổ · Sau ký + n ngày · ngày cố định). Không thêm mốc riêng vào danh mục chung.
3. Báo giá: ô Mốc thời gian lấy danh sách **mốc cơ bản + mốc của dự án đã chọn**; nhận gõ tắt không dấu khớp tên mốc của dự án (vd `cndt`/`CNĐT` → "Xong chứng nhận đầu tư" nếu dự án đã khai); báo lỗi theo BG-23.
4. DEMO: khai mẫu mốc "Xong chứng nhận đầu tư" cho một dự án KCN DEMO để Anh thử.
**Báo Anh khi:** DEMO đã có màn Dự án đang bán; lát mốc dự án sẵn sàng thử.
**Trạng thái:** Mục 1 XONG 25/10 23:40 (gộp `lat/da-2` + T-DA2 vào hợp nhất 6998a79; lưới CRM thêm ô Dự án đang bán — DA-4, trên dòng giao diện). Mục 2–4: máy chủ mốc dự án gộp hợp nhất 26/10 00:31 (7ce0344, M0035), giao diện (MDA-2/3u/4b/4c) trên DEMO 8798; seed DEMO mốc "Xong chứng nhận đầu tư" cho KCN DEMO. Chờ Anh thử (phiếu cổng A lần 2 mục B).

## CD-007 · 25/10/2026 22:20 · Mốc dự án có ngày dự kiến và ngày thực tế (bổ sung CD-006 mục 2)
**Căn cứ:** Anh chốt 25/10 22:10: "nếu mốc chưa có ngày thì không đếm được quá hạn, khi đó nêu ngày dự kiến, khi hết ngày dự kiến vẫn chưa làm xong thì sẽ cho chỉnh ngày dự kiến đó"; TL 45 §7 mục 5.
**Việc (gộp vào lát mốc dự án của CD-006):**
1. Mỗi mốc dự án có **ngày dự kiến** (bắt buộc khi khai) và **ngày thực tế** (ghi khi xảy ra).
2. Chưa có ngày thực tế: đợt gắn mốc hiện "dự kiến dd/mm/yyyy" ở Báo giá, Lịch nghĩa vụ, Danh sách hợp đồng (cột Đợt kế tiếp); **không đếm quá hạn**.
3. Qua ngày dự kiến mà chưa có ngày thực tế: tạo việc chờ "Chỉnh ngày dự kiến mốc …" cho người phụ trách dự án (đếm vào số trên icon theo TL 49); chỉnh ngày dự kiến bắt buộc lý do, ghi nhật ký cũ → mới, ai, lúc nào.
4. Ghi ngày thực tế: đợt gắn mốc có ngày đến hạn = ngày thực tế (+ n ngày nếu đợt khai) → đếm đến hạn/quá hạn như đợt ngày cố định; ghi nhật ký.
5. Test: mốc chưa có ngày thực tế không vào danh sách quá hạn; qua ngày dự kiến sinh đúng 1 việc chờ; ghi ngày thực tế → đợt đổi trạng thái đúng.
**Trạng thái:** XONG lập trình 26/10 00:31 (máy chủ gộp hợp nhất; giao diện trên DEMO 8798): ngày dự kiến/thực tế, chỉnh dự kiến bắt buộc lý do + nhật ký, việc chờ tính khi đọc, danh sách hợp đồng "dự kiến dd/mm/yyyy" không đếm quá hạn; test PG mốc 21+15+8+10 đạt. Chờ Anh thử (phiếu mục B).

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
**Trạng thái:** XONG 26/10 05:36 — báo cáo `docs\46-chuyen-doi-dieu-phoi\bao-cao-ngay\BAO-CAO-DEM-20261026.md`; DEMO cổng 8798; phiếu cổng A lần 2 `PHIEU-CONG-A-BAO-GIA-LAN-2.md`; 7 việc Cần Anh ở §4.

## CD-009 · 26/10/2026 06:25 · Không được dừng vì "hết việc ưu tiên" — quy tắc chạy đêm và lấp chỗ trống
**Căn cứ:** Anh chốt 26/10 06:24 sau khi hỏi vì sao 02:45 → 05:30 bỏ trống. Bằng chứng: git không có commit 02:41 → 05:36; `BAO-CAO-DEM-20261026.md` §6 "02:45 → 05:36 không còn việc ưu tiên, chỉ đọc hộp thư mỗi giờ"; khung 5 giờ Claude đặt lại 03:50 (05:36 dùng 0%), Codex không chạm hạn mức; `BAO-CAO-DEM-20261026-doi-chieu.md` điểm 4. Hàng đợi lúc 02:45 còn M2k, E1-4 giao diện, M4-3, AI-4, MASK-3, sửa ca k10 của KY-DOCX, các điểm Nên sửa/Để sau, T-NEN-c2 — báo cáo không nêu lý do chặn.
**Việc:**
1. **Sáng nay:** trả lời trong `TRANG-THAI.md` (mục "Cần điều tra") vì sao AI-4, MASK-3, M2k, E1-4 giao diện, M4-3 không giao đêm qua; việc nào không bị chặn → **giao ngay**. KY-DOCX: giao một lát mới chỉ sửa ca test k10 (luật "đỏ 2 lần" áp cho lát cũ, không cấm lát sửa test).
2. **Cấm lý do dừng "hết việc ưu tiên".** Trước khi để trống chỗ worker, lead rà **toàn bộ** hàng đợi (`4-KE-HOACH-LEAD.md` + `TRANG-THAI.md`) và ghi cho **từng việc không giao** một dòng: mã · lý do chặn cụ thể (chờ Anh quyết gì / chờ lát nào / chạm hạn mức gì). Còn việc không bị chặn → phải giao.
3. **Danh sách lấp chỗ trống** (khi hết việc chính, theo thứ tự): (a) điểm "Nên sửa" rồi "Để sau" từ các báo cáo review; (b) sửa test đỏ/treo so nền; (c) test còn thiếu cho code đã gộp; (d) soạn checklist + bảng câu hỏi cho module chưa chốt (M3 · Hóa đơn bán ra & doanh thu BĐS trước) để Anh chốt — chỉ soạn, không code; (e) cập nhật `TRANG-THAI.md` cho đúng thực tế.
4. **Trước khi Anh nghỉ** (khi có lệnh chạy đêm): báo Anh danh sách **≥ 6 việc không bị chặn** cho đêm đó; không đủ 6 → hỏi Anh ngay lúc đó (bảng chọn), không để tới sáng.
5. **Nhịp khi rảnh:** 20 phút rà lại hàng đợi một lần (không chỉ đọc hộp thư); mỗi lần rà ghi 1 dòng nhật ký (giờ · số việc không bị chặn · đã giao gì).
6. Báo cáo đêm/ngày thêm mục **"Việc không làm + lý do chặn"** (đủ mọi việc trong hàng đợi) và **thời gian trống của worker** (từ giờ nào đến giờ nào, vì sao).
**Áp dụng:** từ ngay hôm nay, cho cả chạy ngày và chạy đêm.
**Trạng thái:** ĐÃ NHẬN 26/10 09:10 — mục 1 trả lời trong `TRANG-THAI.md` (26/10 09:10); KY-DOCX lát sửa test riêng đã gộp (3dd1661); áp quy tắc rà hàng đợi 20 phút + mục "Việc không làm + lý do chặn" từ nay.

## CD-010 · 26/10/2026 06:35 · Anh trả lời 7 việc "Cần Anh quyết" của báo cáo đêm
**Căn cứ:** `bao-cao-ngay\BAO-CAO-DEM-20261026.md` §4; Anh chốt qua bảng chọn 26/10 06:30–06:34.
**Quyết định và việc:**
1. **Ký trên bản chỉ có DOCX:** thêm đường **"Kế toán xác nhận đã kiểm tay"** cho bước đối chiếu bản ký G5 — bắt buộc lý do, ghi nhật ký (ai, lúc nào), hợp đồng sang được Hiệu lực. **Không** nới hợp đồng dữ liệu E5 nhận hash DOCX. Xác nhận: PDF lỗi vẫn được sang Chờ ký. Gộp vào lát sửa KY-DOCX (CD-009 việc 1).
2. **Mốc dự án:** đồng ý cả 3 mặc định lead đã chọn (việc "Chỉnh ngày dự kiến" giao vai Bán hàng; mốc vẫn hiện khi dự án ngừng bán; gõ tắt theo tên tắt + chữ cái đầu).
3. **Trang chủ hệ thống:**
   - Thanh cố định 4 mục **khác nhau theo vai**: lead đề xuất 4 mục cho từng vai, đưa vào phiếu cổng A UI-1/UI-3 để Anh duyệt.
   - **Giữ tiền tố** "M2 ·", "M4 ·" trong tên module; M9 hiện mờ "Tạm dừng" với mọi vai.
4. **Vai mô phỏng (DEMO) và ma trận thẩm quyền — yêu cầu mới:**
   - Rút danh sách vai còn **khoảng 5 vai** theo cấp: **Người thực hiện 1 · Người thực hiện 2 · Trưởng phòng · CFO** (Anh nêu 4; lead đề xuất vai thứ 5 nếu cần, vd Người xem) — áp theo từng phòng/pháp nhân.
   - **Thêm phần "Ma trận thẩm quyền"** (yêu cầu mới, **chưa chốt thiết kế → chưa code**): lead soạn checklist ngắn `THIET-KE-MA-TRAN-THAM-QUYEN.md` — vai × hành động (lập, sửa, kiểm, duyệt, hủy, xem) × module/màn × giới hạn (số tiền, pháp nhân, dự án) × ai cấp/sửa ma trận × nhật ký; dùng lại quyền đã có (TL 42 §1, kiểm quyền ở máy chủ) — rồi hỏi Anh bằng bảng chọn. Việc này vào danh sách lấp chỗ trống mục (d) của CD-009 nếu chưa tới lượt.
5. **Báo giá USD:** **bỏ cột "VND quy đổi"** trùng với cột Giá trị; bằng chữ **giữ nguyên** "đồng".
6. **`test_source6_lazy_excel`:** Anh không có bản lazy Excel đã duyệt → **bỏ bộ test khỏi nền**, ghi lý do trong `NEN-TEST.md`; mở lại khi có bản duyệt.
7. **M4 · khối 03B:** kế toán **không** có đường tải tệp căn cứ riêng; kế toán dùng **"Yêu cầu bổ sung"** gửi phòng dự án. Giữ quyền tải như hiện tại.
**Báo Anh khi:** checklist ma trận thẩm quyền sẵn sàng để chốt; phiếu cổng A có thanh cố định theo vai.
**Trạng thái:** ĐÃ NHẬN 26/10 09:10 — mục 1 giao lát KY-G5TAY; mục 3, 5 lát giao diện; mục 6 ghi `NEN-TEST.md`; mục 4 thay bằng CD-012; mục 7 lát nhỏ M4.

## CD-011 · 26/10/2026 07:00 · M4 = phần mềm review hồ sơ xây dựng: chép đủ 8 màn + chuyển dữ liệu SQLite → PostgreSQL thật riêng
**Căn cứ:** Anh yêu cầu 26/10 06:56 ("chép lại hết các chức năng, copy luôn phần code, chỉ đẩy phần liên kết dữ liệu sang PostgreSQL") và chốt qua bảng chọn 06:58–07:00: (1) là **M4 · Nghiệm thu & chi phí dự án** (giữ M2 là Mua hàng/Hóa đơn mua vào); (2) **chép nguyên 8 màn "Bàn kiểm soát" vào khung icon M4**; (3) dữ liệu chuyển **vào kho thật** — cụ thể **tạo CSDL PostgreSQL thật riêng, nạp dữ liệu M4 trước**; (4) **đóng băng code bản gốc**, vẫn dùng tới khi M4 qua cổng B. Thiết kế M4 20/10 (`THIET-KE-MODULE-DE-CHOT-2026-10-20\M4-XAY-DUNG-VA-NGHIEM-THU.md` §1: "M4 bao gồm đầy đủ chức năng của review_xaydung, dùng lại lõi xử lý và giao diện"). `CLAUDE.md` mục kho thật đã thêm ngoại lệ (07:00).
**Hiện trạng (phiên điều phối đọc README/API.md 26/10):** bản gốc `D:\Claude\Ho tro review ho so xay dung\review_xaydung` có 8 màn (Tổng quan · Trích tham số · Danh mục hợp đồng · Phụ lục · BOQ · Kiểm tra đợt · Chứng từ · Cài đặt), CSDL **SQLite** `co_so_du_lieu\hop_dong.db` qua `csdl_hop_dong.py`; repo mới chép lõi ở `m4\review_goc` + màn 02C/03A/03B/04.
**Việc:**
1. **Kiểm kê chênh lệch (lát đầu, chỉ đọc):** bảng màn × nút/chức năng × API (theo `API.md` bản gốc) → đã có ở M4 / thiếu / khác; bảng SQLite (`hop_dong.db`) ↔ bảng PostgreSQL M4 hiện có (`sql_review.py`, `sql_master_dung_chung.py`…). Ghi `docs\46-chuyen-doi-dieu-phoi\M4-KIEM-KE-CHEP-REVIEW.md`.
2. **Chép nguyên code + giao diện** 8 màn vào M4, mỗi màn một icon trong khung lưới (TL 49); dùng chung đăng nhập, quyền, pháp nhân, thanh trên; **giữ** các màn M4 đã làm (02C, 03A kế toán nghiệm thu, 03B, 04 Request). **Chỉ thay lớp dữ liệu**: `csdl_hop_dong.py` (SQLite) → PostgreSQL qua migration mới; nghiệp vụ/thuật toán (K1–K8, B1–B8, C01–C09, P01–P18, trích 37 tham số) giữ nguyên, test gốc của bản review phải đạt trên bản chép. Đường AI theo cổng AI (Local luôn có, Cloud chỉ qua Mask v2 — CD-001). Lát nhỏ ≤ 3 file theo CD-004 (nhiều lát song song theo màn).
3. **Công cụ chuyển dữ liệu** SQLite → PostgreSQL: chạy lại được (idempotent, khóa theo id gốc), báo cáo đối chiếu trước–sau: **số dòng từng bảng, tổng giá trị hợp đồng, tổng BOQ, tổng từng đợt** (đơn vị tiền ghi rõ), danh sách dòng lỗi.
4. **Chạy thật — theo thứ tự, ghi biên bản từng bước:** (a) sao lưu `hop_dong.db` + SHA256 vào `LUU-TRU\m4-hop-dong-db-<ngày giờ>`; (b) chạy thử trên **bản sao** vào một CSDL PostgreSQL tạm → đối chiếu khớp 100%; (c) tạo **CSDL PostgreSQL thật riêng cho M4** (tên/role khác DEMO; file kết nối `*.that.local.json` ngoài git) → migration → nạp → đối chiếu → `pg_dump` sao lưu; (d) báo Anh biên bản. Lệch bất kỳ → dừng ở bước đó, không sửa tay dữ liệu.
5. **Đóng băng bản gốc:** không sửa code `review_xaydung` từ nay (chỉ đọc). Anh vẫn dùng bản gốc tới cổng B M4; trước khi chuyển hẳn, chạy công cụ lần cuối để nạp phần dữ liệu phát sinh.
6. Dữ liệu thật **không** vào test/fixture/DEMO, không gửi Cloud; test dùng dữ liệu giả.
**Báo Anh khi:** bảng kiểm kê xong; biên bản chạy thật (bước 4); phiếu cổng A M4 (8 màn trong khung icon).
**Trạng thái:** ĐÃ NHẬN 26/10 09:10 — lát 1 kiểm kê (chỉ đọc) giao trước; chạy thật bước 4 chỉ sau khi kiểm kê + công cụ chuyển dữ liệu qua review.

## CD-012 · 26/10/2026 07:00 · Ma trận thẩm quyền — Anh chốt cách làm (thay CD-010 mục 4 phần "chưa chốt")
**Căn cứ:** Anh 26/10 06:57: "Ma trận thẩm quyền tạo ra một bảng với các nút tick ở các module, tôi sẽ tự tick vào ma trận thẩm quyền, có 1 cột giới hạn số tiền, cấp và sửa ma trận chỉ có admin".
**Đã chốt → được code (không cần hỏi thêm trước khi code):**
1. Một màn **"Ma trận thẩm quyền"** dạng **bảng ô tick**: dòng = vai (theo CD-010: Người thực hiện 1 · Người thực hiện 2 · Trưởng phòng · CFO …) theo phòng/pháp nhân; cột = **module × hành động** (xem · lập · sửa · kiểm · duyệt · hủy), nhóm cột theo module, gấp/mở được.
2. **Một cột "Giới hạn số tiền"** (VND, để trống = không giới hạn) cho mỗi dòng; máy chủ chặn hành động duyệt vượt giới hạn và ghi lý do chặn.
3. **Chỉ vai Admin** được cấp/sửa ma trận; người khác chỉ xem phần của mình. Mỗi lần sửa ghi nhật ký (ô nào, cũ → mới, ai, lúc nào). Quyền kiểm ở máy chủ, ẩn nút chỉ là lớp hiển thị.
4. Anh tự tick: máy **không** tự điền ma trận thật; DEMO có bản mẫu để thử.
**Mặc định lead tự chọn, ghi vào phiếu cổng A để Anh xem:** giới hạn tiền áp cho hành động **duyệt** (và lập nếu module cần); cách nối ma trận với quyền đã có (TL 42 §1) — ma trận là nguồn quyền duy nhất sau khi bật.
**Báo Anh khi:** phiếu cổng A màn Ma trận thẩm quyền.
**Trạng thái:** ĐÃ NHẬN 26/10 09:10 — soạn thiết kế lát + giao MTQ-1 (máy chủ).

## CD-013 · 26/10/2026 11:45 · Bắt đầu M3 · Hóa đơn bán ra & doanh thu BĐS theo thiết kế v2 (+ phần tách sang M10)
**Căn cứ:** Anh ra lệnh 26/10 11:34 "đọc file M3 v2 để tiến hành làm M3"; thiết kế `D:\Claude\Phan mem ho tro ke toan\THIET-KE-MODULE-DE-CHOT-2026-10-20\M3-HOA-DON-BAN-VA-DOANH-THU-v2-20261026.md` (Anh chốt hướng; **mục 16 = trả lời của Anh 11:40, thắng các mục trước khi mâu thuẫn**). Bản này **thay** `CHECKLIST-M3-HOA-DON-BAN-RA.md` (M3-CL) và bản M3 20/10.
**Việc:**
1. Đọc v2 (mục 0, 5–10, 13, 16). Thêm M3 và M10-1 vào `4-KE-HOACH-LEAD.md` + `TRANG-THAI.md`; chuyển bản M3 20/10 vào lưu trữ, sửa liên kết trong `00-DANH-MUC-VA-THU-TU-CHOT.md`; đánh dấu M3-CL "đã thay bằng v2".
2. **Lát (v2 mục 16):** M3-1 tách cơ sở doanh thu/thuế + 3 đẳng thức + màn hóa đơn–hợp đồng · M3-2 hình thức doanh thu (ghi nhận luôn / phân bổ) dạng policy · M3-3 đợt thu KCN theo lớp tài khoản cọc / người mua trả trước / 131 + máy trạng thái + K5 + màn 4 trường · M3-4 sự kiện bàn giao (biên bản tải lên CRM theo hợp đồng/lô → đề xuất bút toán bàn giao; nhà ở ghi nhận doanh thu tại bàn giao, khung chung) · M3-5 lưu tham số phân bổ (thuê đất; phí hạ tầng theo tháng) + lưới icon M3 + tuổi hồ sơ chờ · **M10-1** engine lịch tính A/B **chỉ để kiểm chéo** + nguồn sổ 3387 Junsky + mapping + bảng lệch + cảnh báo. Lát nhỏ ≤ 3 file, theo CD-004; xếp sau CD-011/CD-012 đang chạy nhưng **không để worker trống** (CD-009).
3. **Không tự quyết trong code** các điểm còn [CHỜ CHỐT] #7 (cơ sở thuế), #8 (ánh xạ đối tượng Junsky), #10 (file xuất — chỉ làm bản hiển thị), #11 (nguồn biên bản/policy nhà ở), #12 (mẫu K0); chọn mặc định A/B chờ K0. Gặp → dừng phần đó, ghi `CẦN ANH XÁC NHẬN`.
4. Tài khoản chi tiết trong mẫu bút toán là **dữ liệu policy** (kế toán trưởng điền); code không gắn cứng số tài khoản. Phần mềm **không phân bổ** thay Junsky, chỉ lưu tham số và kiểm chéo (Anh, #9).
5. Test dùng dữ liệu giả; ví dụ 7.4 (600 / 60 tháng; cách A năm 1 = 120, cách B ≈ 93,3) làm test đơn vị cho M10-1.
**Báo Anh khi:** phiếu cổng A M3 (lưới icon + màn hóa đơn–hợp đồng + đợt thu KCN); cần trả lời các [CHỜ CHỐT].
**Trạng thái:** ĐÃ NHẬN 12:05 26/10 — mục 1 xong (M3 + M10-1 vào `4-KE-HOACH-LEAD.md` và TRANG-THAI; bản M3 20/10 chuyển `LUU-TRU\thiet-ke-m3-ban-20261020\` kèm SHA256; liên kết trong `00-DANH-MUC-VA-THU-TU-CHOT.md` và `CRM-CHUC-NANG-VA-THIET-KE.md` trỏ v2; M3-CL đánh dấu đã thay). Mục 2: giao **M10-1a** (engine lịch A/B, test ví dụ 7.4) 12:10; M3-0 (mô hình dữ liệu + bảng lớp/mốc + phiếu cổng A M3) chờ mục 17 trong v2 (chưa thấy trong tệp lúc 12:05). Không tự quyết #7, #8, #10, #11, #12.

## CD-014 · 26/10/2026 11:55 · M3: làm theo MỐC thay đổi cách ghi nhận; tài khoản để bước sau (bổ sung CD-013)
**Căn cứ:** Anh 26/10 11:49: "Hãy quan tâm đến các mốc làm thay đổi cách ghi nhận, còn ghi nhận vào tài khoản nào sẽ nằm ở bước sau." Thiết kế M3 v2 **mục 17** (thêm 11:55).
**Việc:**
1. M3-3, M3-4 làm **máy chuyển lớp theo mốc**: lớp ghi nhận (Đặt cọc · Người mua trả trước · Phải thu chưa đến hạn/đến hạn · Doanh thu chờ phân bổ · Doanh thu đã ghi nhận · Đã đảo/điều chỉnh); bảng mốc → nguồn quyết định → chuyển lớp (v2 §17) là **dữ liệu cấu hình** theo hình thức/loại nghiệp vụ, không cứng code.
2. Mốc dùng lại cơ chế **ngày dự kiến / ngày thực tế** của mốc dự án (CD-006/007); thiếu nguồn quyết định → không chuyển lớp, hồ sơ chờ.
3. **Không** sinh bút toán có số tài khoản ở giai đoạn này; các tài khoản trong v2 §7.2/§16 chỉ để bước sau (bảng ánh xạ lớp → tài khoản do kế toán trưởng điền). Đề xuất hiển thị: mốc · ngày · căn cứ · lớp trước → lớp sau · giá trị.
4. Bảng mốc §17 là đề xuất: đưa vào phiếu cổng A M3 để Anh sửa.
**Trạng thái:** ĐÃ NHẬN 12:05 26/10 — áp vào M3-0/M3-3/M3-4: máy chuyển lớp theo mốc, bảng mốc là cấu hình, dùng ngày dự kiến/thực tế của mốc dự án; không sinh số tài khoản. Lead chờ mục 17 của thiết kế v2 để soạn bảng mốc cho phiếu cổng A M3.

## CD-015 · 26/10/2026 13:45 · Mở lại M9 với phạm vi mới: kho hợp đồng vay + hỏi đáp (RAG, chỉ Local AI) + báo cáo lãi suất
**Căn cứ:** Anh 26/10 13:28 và chốt qua bảng chọn 13:30–13:40; thiết kế `D:\Claude\Phan mem ho tro ke toan\THIET-KE-MODULE-DE-CHOT-2026-10-20\M9-KHO-HOP-DONG-VAY-HOI-DAP-20261026.md` (**mục 8 = phần đã chốt**). `CLAUDE.md` dòng M9 đã sửa (13:45): M9 mở lại theo phạm vi này. Thiết kế M9 20/10 đổi hướng, giữ làm tham khảo cách lấy dữ liệu.
**Việc:**
1. Thêm M9-1…M9-5 vào kế hoạch + `TRANG-THAI.md`, theo CD-004/CD-009; xếp sau CD-011 (M4), CD-012 (ma trận thẩm quyền), CD-013/014 (M3) nhưng dùng làm việc lấp chỗ trống khi các lát kia bị chặn.
2. **AI: chỉ Local AI** cho chỉ mục và hỏi đáp — **không** gửi Cloud, kể cả qua Mask v2 (ngoại lệ chặt hơn TL 48 cho M9). Lead kiểm bằng grep ở cổng kiểm soát.
3. Hỏi đáp phải có trích dẫn (file · trang · điều/khoản · câu nguyên văn); số dư/lãi suất chỉ từ snapshot Sheet có mốc; không trích dẫn được thì không trả lời bằng số.
4. M9-3 (Google Sheets API): khóa chỉ trong `.env` (không đọc `.env` qua công cụ — chỉ code đọc lúc chạy), quyền chỉ đọc; làm và test với Sheet giả; **chờ Anh cung cấp Sheet/tab/tài khoản dịch vụ** để nối thật.
5. Báo cáo lãi suất hằng tháng: "lãi cao" = cao hơn bình quân gia quyền theo dư nợ của danh mục cùng mốc; cảnh báo trước kỳ điều chỉnh lãi 30 ngày; không tự gửi ra ngoài.
6. OCR bản scan: dùng lại cách ABBYY Hot Folder của phần mềm review (chép code, không sửa bản gốc đang đóng băng — CD-011).
**Báo Anh khi:** cần thông tin Sheet; phiếu cổng A M9.
**Trạng thái:** ĐÃ NHẬN 14:05 26/10 — M9-1…M9-5 vào `4-KE-HOACH-LEAD.md` + TRANG-THAI, xếp sau CD-011/012/013/014, dùng lấp chỗ trống. Chưa giao lát: hạn mức Claude tuần 88% (lead đang chậm lại, xử lý nốt hàng chờ). Cổng kiểm soát M9: grep không có đường Cloud/Mask. M9-3 chờ Anh cung cấp Sheet/tab/tài khoản dịch vụ.

## CD-016 · 26/10/2026 20:25 · Kho vận hành: một CSDL PostgreSQL thật chung; phát hành tối thứ Sáu; 5 module vận hành cùng lúc
**Căn cứ:** Anh chốt 26/10 20:20 (bảng chọn); Project TL 52 `52-gan-module-lien-tuc-va-phat-hanh.md` §4–§5. `CLAUDE.md` ngoại lệ kho thật đã sửa (20:25).
**Việc:**
1. **CD-011 bước 4(c) đổi:** tạo **một CSDL PostgreSQL thật chung cho mọi module** (không tạo CSDL riêng M4); M4 nạp trước theo đúng các bước sao lưu/chạy thử bản sao/đối chiếu/biên bản của CD-011. Nếu đã tạo CSDL riêng M4 → ghi lại, đề xuất cách gộp, không tự xóa.
2. **Kho thật SQLite (`var\plhn-that`, `var\web-that`) — chưa đụng.** Lead chỉ **soạn kế hoạch chuyển** sang CSDL PostgreSQL thật chung (bảng nguồn → đích, công cụ, biên bản đối chiếu, sao lưu, đường lùi) → báo Anh duyệt; chạy khi Anh ra lệnh riêng.
3. **Phát hành hằng tuần tối thứ Sáu** lên nhánh `chinh`/kho thật; sửa khẩn đi đường riêng. Lead soạn `CHECKLIST-PHAT-HANH.md` (sao lưu → nâng dữ liệu chỉ thêm → test → bật → đường lùi).
4. **Go-live: M0, M2, M3, M4, M9 cùng một lần phát hành**, khi cả 5 qua cổng B. Lead lập bảng điều kiện go-live từng module (cổng B, điểm chờ chốt, dữ liệu thật cần nạp) trong `TRANG-THAI.md`; không phát hành từng module lẻ.
5. **Không làm** khung cắm module tổng quát (TL 52 §2) — Anh đang nghiên cứu; module mới vẫn khai báo theo cách hiện có của TL 49.
**Báo Anh khi:** kế hoạch chuyển kho thật SQLite sẵn sàng; bảng điều kiện go-live 5 module.
**Trạng thái:** ĐÃ NHẬN 20:30 26/10 — (1) chưa tạo CSDL thật riêng M4 nào → không cần gộp, CSDL thật chung tạo theo CD-011 khi có ánh xạ `ma_hd`; (2)(3)(4) giao Codex soạn tài liệu (chỉ đọc mã, không đọc kho thật), lead duyệt rồi báo Anh; (5) không làm khung cắm tổng quát.

## CD-017 · 26/10/2026 20:35 · Kiến trúc Xương sống – Engine – Module (thay CD-016 mục 5)
**Căn cứ:** Anh 26/10 20:21: dữ liệu ở PostgreSQL; mỗi module gắn vào **khung xương sống chung**, nối CSDL và nối module khác **không phụ thuộc module khác có chạy hay không**; phát triển **theo từng engine**, engine có rồi thì cắm lại vào module; cách kỹ thuật tùy chọn "nhưng phải ra kết quả và module đó dùng được". Thiết kế `D:\Claude\Phan mem ho tro ke toan\53-kien-truc-xuong-song-engine-module.md` (Project TL 53). CD-016 mục 5 ("không làm khung cắm module") **bỏ**.
**Việc (theo TL 53 §6 — chuyển đổi dần, không viết lại, không dừng việc đang chạy):**
1. **Xương sống còn thiếu (lát nhỏ, ưu tiên ngay sau các lát đang chạy):** XS-1 bus sự kiện bền trong PostgreSQL (`su_kien` outbox/inbox, idempotent, chạy lại không nhân đôi) · XS-2 hàng việc nền dùng chung (tiến độ, dừng, thử lại, nhật ký) — tận dụng cơ chế việc nền đã có · XS-3 danh bạ engine + hợp đồng engine (mã, phiên bản, vào/ra, trạng thái xong/chờ/lỗi có mã, bằng chứng) + bộ test mẫu chuẩn · XS-4 khai báo module tổng quát từ `khung_khai_bao.py` (CRM) cho mọi module + công tắc Tắt/Thử/Vận hành theo module × pháp nhân; ma trận thẩm quyền đọc cột từ khai báo.
2. **Engine gọi được hai cách cùng một hợp đồng:** trong tiến trình (Python) và qua API nội bộ + hàng việc nền cho việc nặng. Engine không đọc/ghi bảng của module.
3. **Module mới làm theo engine ngay:** M9 = E-OCR + E-RAG + E-SHEETS; M3 = E-HOADON + E-MOC (+ E-PHANBO ở M10). Năng lực mới → làm engine trước, có test mẫu riêng.
4. **Code cũ bọc dần** thành engine khi chạm tới (E-OCR từ ABBYY review, E-TRICH từ #6/E1, E-KIEMTRA-DOT từ review xây dựng khi làm CD-011, E-HOADON từ M2-00, E-AI = cổng AI). Không đổi hành vi; test cũ phải đạt.
5. **Độc lập module:** thiếu dữ liệu từ module khác → trạng thái **chờ có lý do**, không lỗi, không suy đoán; trao đổi chỉ qua danh mục chung, bus sự kiện, dữ liệu công bố chỉ đọc.
6. Ghi danh bạ engine vào `TRANG-THAI.md` (engine · phiên bản · module dùng · trạng thái test).
**Báo Anh khi:** XS-1…XS-4 xong (kèm ví dụ: tắt một module, module kia vẫn chạy và hiện "chờ"); engine đầu tiên được cắm lại vào module thứ hai.
**Trạng thái:** ĐÃ NHẬN 20:40 26/10 · 22:50 Anh chốt công tắc S1–S6 (QD-20261026-11), giao XS-4b → XS-4c → XS-2 → pilot · — giao Codex kiểm kê + chia lát XS-1…XS-4 theo TL 53 (chỉ tài liệu) rồi giao code từng lát; các lát MTQ-4/CD-016 đang chạy giữ nguyên.

## CD-018 · 26/10/2026 20:30 · Mỗi module khai báo vùng dữ liệu ghi/đọc — nguyên tắc triển khai toàn phần mềm
**Căn cứ:** Anh 26/10 20:26: "mỗi module vào phải xác định được vùng chức năng của cơ sở dữ liệu để ghi nhận hoặc lấy thông tin từ cơ sở dữ liệu… triển khai phần mềm với nguyên tắc như vậy." TL 53 §7 (đã thêm 20:30). `CLAUDE.md` đã thêm dòng "Kiến trúc" (ràng buộc cứng).
**Việc:**
1. Thêm **XS-5** vào nhóm xương sống của CD-017: "bản đồ vùng dữ liệu" trong khai báo module (vùng ghi riêng = schema của module; vùng ghi chung chỉ qua hàm xương sống — sự kiện, liên kết chứng từ, việc chờ/duyệt, kho file; vùng đọc danh mục chung; vùng đọc dữ liệu công bố của module khác + sự kiện đăng ký nhận).
2. **PostgreSQL:** mỗi module một role, GRANT đúng bản đồ; module không ghi/đọc thẳng bảng của module khác. Làm trên DEMO trước; CSDL thật chung (CD-016) tạo theo cách này ngay từ đầu.
3. **Test bắt buộc:** so mọi bảng/khung nhìn mà module chạm tới (bắt từ SQL chạy test) với bản đồ khai báo; lệch → đỏ, không gộp. Thêm vào 4 kiểm tự động của mỗi lát.
4. **Áp dụng:** module mới (M3, M9, M10-1) khai báo ngay; module đang có (CRM, M2, M4, M0) lập bản đồ từ code hiện tại, ghi chỗ đang đọc chéo trực tiếp → chuyển dần sang dữ liệu công bố khi chạm tới (không dừng việc đang chạy).
5. Màn quản trị (chỉ Admin): xem bản đồ vùng dữ liệu từng module (ghi gì, đọc gì, từ module nào).
**Báo Anh khi:** bản đồ vùng dữ liệu của các module đang có (bảng tóm tắt 1 trang: module × ghi × đọc × chỗ đọc chéo cần sửa).
**Trạng thái:** ĐÃ NHẬN 21:10 26/10 — thêm XS-5 vào chuỗi xương sống (KK-XUONG-SONG); giao Codex kiểm kê bản đồ vùng dữ liệu CRM/M2/M4/M0 (+M3, M9) từ mã → `KK-VUNG-DU-LIEU.md` (bảng 1 trang báo Anh). Sau đó: XS-5a khai báo vùng trong mô hình XS-4a; XS-5b role PG theo module trên DEMO; XS-5c test so truy cập thực với bản đồ (vào 4 kiểm tự động); màn quản trị Admin. CSDL thật chung (CD-016) chỉ dựng sau XS-5b để có role theo bản đồ ngay từ đầu.

## CD-019 · 26/10/2026 20:45 · Engine/cổng dùng chung; CSDL lưu riêng `D:\DU-LIEU-KE-TOAN`; mã hóa
**Căn cứ:** Anh 26/10 20:30 ("engine tái sử dụng qua các module, cổng chung để xử lý chung nhằm tiết kiệm dung lượng phần mềm cũng như hoạt động; CSDL phải được lưu trữ riêng chứ không nằm trong phần mềm"); Anh chốt 20:35–20:45: lưu trên máy này tại **`D:\DU-LIEU-KE-TOAN`**, sau chuyển lên máy chủ; mã hóa **cột nhạy cảm + file sao lưu ngay, BitLocker sau khi đo**. TL 53 §8; `CLAUDE.md` đã thêm dòng "Dùng chung & lưu riêng".
**Việc:**
1. **Dùng chung:** mỗi năng lực một engine; cổng chung một bản (AI, OCR, file, tải hóa đơn, Google API, xuất Junsky). Thêm kiểm ở cổng kiểm soát: lát không được thêm thư viện/mô hình/kết nối trùng cái đã có trong danh bạ engine/cổng (CD-017 XS-3).
2. **CSDL thật chung (CD-016) tạo tại `D:\DU-LIEU-KE-TOAN\postgresql\`** (dịch vụ Windows riêng, cổng riêng, tách DEMO); kho file thật tại `D:\DU-LIEU-KE-TOAN\kho-file\`; sao lưu tại `D:\DU-LIEU-KE-TOAN\sao-luu\` + đề xuất cách chép thêm ra ổ khác/ổ ngoài định kỳ. Phần mềm chỉ giữ cấu hình kết nối (ngoài git). Thư mục chưa có → lead tạo (cần quyền thì hỏi Anh).
3. Cụm DEMO đang ở `D:\Claude\Phan mem ho tro ke toan\var\postgresql-ktt-16\data`: chuyển ra ngoài thư mục phần mềm khi tiện (không gấp, không làm gián đoạn cổng A). Kho thật SQLite `var\plhn-that`: theo kế hoạch chuyển của CD-016 mục 2.
4. **Mã hóa ngay:** (a) cột nhạy cảm bằng pgcrypto — lead lập danh sách cột (CCCD/ĐKDN, số tài khoản ngân hàng, …) để Anh duyệt trước khi bật; khóa nằm ngoài CSDL và ngoài thư mục phần mềm, chỉ code đọc lúc chạy; có cách xoay khóa; (b) file sao lưu mã hóa, khóa giữ riêng, có hướng dẫn khôi phục và thử khôi phục một lần.
5. **BitLocker:** đo trước — chạy bộ đo (pgbench + vài thao tác lưu thật của phần mềm trên DEMO) trên `D:\DU-LIEU-KE-TOAN` khi chưa mã hóa, ghi số; khi Anh bật BitLocker, đo lại cùng bộ, báo chênh lệch để Anh quyết giữ hay dùng mã hóa phần cứng.
6. SSL: ghi vào checklist chuyển lên máy chủ.
**Báo Anh khi:** danh sách cột nhạy cảm cần duyệt; số đo trước BitLocker; biên bản thử khôi phục bản sao lưu mã hóa.
**Trạng thái:** ĐÃ NHẬN 21:10 26/10 · 22:50 Anh duyệt danh sách cột nhóm A, cách giữ khóa, lịch sao lưu (M1–M3, QD-20261026-11); giao MH-1, SL-1; người giữ ổ ngoài Anh chỉ định khi tới bước tạo khóa · — (1) thêm kiểm "không trùng engine/thư viện/mô hình/kết nối" vào `MAU-REVIEW-CODEX.md` và cổng lead; (2) lead tạo `D:\DU-LIEU-KE-TOAN\{postgresql,kho-file,sao-luu}` (thư mục rỗng); cụm PG thật dựng sau XS-5b và khi Anh duyệt kế hoạch chuyển kho — đăng ký dịch vụ Windows cần quyền quản trị: sẽ hỏi Anh đúng bước đó; (3) giao Codex lập danh sách cột nhạy cảm + thiết kế pgcrypto/xoay khóa/sao lưu mã hóa/thử khôi phục + bộ đo trước BitLocker (tài liệu `KK-MA-HOA-LUU-RIENG.md`) → gửi Anh duyệt danh sách cột trước khi bật.

## CD-020 · 27/10/2026 06:25 · Lead chạy LIÊN TỤC ngày đêm (mặc định), chạy đêm mỗi đêm không cần lệnh riêng
**Căn cứ:** Anh hỏi 27/10 06:12 vì sao đêm 26→27 không chạy; nguyên nhân (git, `TRANG-THAI.md` 00:50, `bao-cao-ngay\BAO-CAO-DEM-20261027-tu-lap.md`): không có lệnh chạy đêm (CD-008 chỉ cho đêm 25→26), `/loop` cũ đã dừng 26/10 05:45, lead kết thúc lượt lúc 00:50 và không tự thức dậy; 5 lát review dở chưa gộp. Anh chốt 06:20: **chạy liên tục ngày đêm, mặc định**.
**Việc:**
1. **Ngay sáng nay:** thu và gộp/xử lý 5 lát dở đêm qua (MTQ-4b2b, MTQ-4i-b1 v5, MTQ-NEN-2c, MTQ-4d1b, XS-5a1) theo quy trình review; báo vào TRANG-THAI.
2. **Chạy liên tục:** khi Anh dán lệnh `/loop` (không hẹn giờ dừng), mỗi lượt: đọc hộp thư → rà toàn bộ hàng đợi (CD-009) → thu lát xong → kiểm/gộp → giao lát mới tới mức worker CD-004 → cập nhật TRANG-THAI. Còn việc đang chạy: lượt kế sau ~5–10 phút; rảnh hoàn toàn: 20 phút rà lại một lần. **Không tự dừng vòng lặp**; chỉ dừng khi Anh bảo.
3. **Chạy đêm mỗi đêm, không cần CD riêng:** áp quy tắc CD-008 (việc cần Anh → ghi "Cần Anh", không chờ; đỏ 2 lần → dừng lát; không gộp `chinh`, không push, không xóa, không đụng kho thật; không khởi động lại máy) cho khung 22:00 → 05:30; **05:45 mỗi ngày viết `bao-cao-ngay\BAO-CAO-DEM-<yyyymmdd>.md`** gồm cả mục "Việc không làm + lý do chặn" và "thời gian worker trống".
4. **Trước 22:00 mỗi tối:** ghi vào TRANG-THAI danh sách việc không bị chặn cho đêm đó; < 6 việc → ghi rõ ở đầu báo cáo đêm và trong mục "Cần Anh" (Anh đọc sáng hôm sau), dùng danh sách lấp chỗ trống CD-009 mục 3.
5. **Hạn mức:** Claude gần đầy (tuần ≥ 90% hoặc khung 5 giờ chạm) → review chuyển Codex theo QD-20261026-04, Claude chỉ kiểm xác suất; ghi giờ và số `/usage` vào `bao-cao-ngay\USAGE-<yyyymmdd>.md` mỗi tối. Codex vẫn chạy đủ suất.
**Trạng thái:** ĐÃ NHẬN 15:40 27/10 — /loop đã chạy (tự nhịp: ~5–10 phút khi còn việc, 20 phút khi rảnh; không tự dừng). Đang thu 5 lát dở: 4b2b (review chặn: ghim quan_he phụ thuộc tick → vòng 4), 4i-b1 (review Đạt nhưng ca NEN-2c lộ thêm trường hợp va chạm UUID/instance → vòng 6), NEN-2c (chờ 4i-b1), 4d1b (vòng 2 xong, chờ gate PG), XS-5a1 (review Đạt → gộp). Đêm: áp CD-008, 05:45 BAO-CAO-DEM; trước 22:00 ghi danh sách việc không bị chặn; USAGE mỗi tối.

## CD-021 · 27/10/2026 09:50 · Triển khai một bản trung tâm qua trình duyệt; CSDL chung tách theo pháp nhân + công cụ xuất riêng một công ty
**Căn cứ:** Anh 27/10 09:39 (engine lớn gồm mọi module/công cụ, CSDL theo từng công ty, bộ phận lấy dữ liệu được phân quyền) và chốt 09:45: **một bản trung tâm, bộ phận dùng trình duyệt**; **CSDL phương án A**. TL 53 §9; `CLAUDE.md` thêm dòng "Triển khai".
**Việc:**
1. Giữ mô hình web hiện có làm cách triển khai duy nhất; không làm bản cài trên máy bộ phận. "Cài cho bộ phận" = công tắc module theo pháp nhân (XS-4) + ma trận thẩm quyền (CD-012).
2. **Máy xử lý phụ:** dựa trên worker chung XS-2b — gói chạy engine trên máy khác, nhận việc qua hàng việc chung bằng tài khoản giới hạn (không quyền đọc bảng nghiệp vụ, không giữ khóa mã hóa); ghi vào kế hoạch, làm sau XS-1…XS-5.
3. **Phân quyền pháp nhân hai lớp** (máy chủ + tầng CSDL) là bắt buộc cho mọi bảng nghiệp vụ mới; test dưới vai ứng dụng (như bài học XS-4c2).
4. **Công cụ xuất riêng một công ty (lát mới XUAT-PN):** xuất toàn bộ dữ liệu của một pháp nhân (kể cả kho file, nhật ký) ra CSDL/tệp riêng, có biên bản đối chiếu số dòng/tổng tiền; chỉ Admin chạy; thử trên DEMO.
5. Checklist chuyển lên máy chủ: thêm SSL, mở truy cập trong mạng nội bộ, sao lưu, giám sát.
**Trạng thái:** ĐÃ NHẬN 15:40 27/10 — (1) giữ mô hình web trung tâm; (2) máy xử lý phụ: ghi vào kế hoạch sau XS-1…5 (dựa worker XS-2b, tài khoản giới hạn); (3) phân quyền PN hai lớp + test dưới vai ứng dụng: đã là kiểm bắt buộc trong mẫu review; (4) lát XUAT-PN xếp sau XS-5b (cần bản đồ vùng dữ liệu để biết bảng của PN); (5) bổ sung checklist chuyển máy chủ (SSL, mạng nội bộ, sao lưu, giám sát) — lát tài liệu.

## CD-022 · 27/10/2026 14:45 · Dự án đang bán: tiến độ thanh toán % + mốc; bỏ ô "Giai đoạn tiến độ"; "Lý do" chỉ khi sửa
**Căn cứ:** Anh thử màn Dự án đang bán 27/10 14:33 (ảnh: ô "Giai đoạn tiến độ mặc định" báo lỗi "chỉ gồm chữ/số/_ . - (1–80)" khi gõ "Cấp giấy CN Đầu tư"; ô "Lý do (bắt buộc)") và chốt 14:40 qua bảng chọn. Mã nguồn liên quan: `giao_dien\assets\crm_g.js` ~390, ~542, ~570; `k2\crm_du_an_ban.py` ~120, ~541; `k2\crm_giao_ket.py` ~289.
**Quyết định của Anh:**
1. **Tiến độ thanh toán tiêu chuẩn của dự án = chỉ % và mốc** — bảng `Lần · % · Mốc thanh toán · Ghi chú`, bố cục giống bảng lịch của Báo giá (BG-20/21): ô nhập nhanh `10%, 30%, 40%, 20%` hoặc số lần; dòng tổng Σ% phải = 100%; **Mốc chọn từ danh sách mốc cơ bản + mốc riêng của dự án** (CD-006/007, có ngày dự kiến/thực tế). Không có cột số tiền ở cấp dự án (số tiền tính ở Báo giá khi đã có giá lô/căn). Báo giá chọn dự án → nạp bảng này (DA-3a).
2. **Mỗi dự án chỉ một tiến độ chuẩn** → **bỏ ô "Giai đoạn tiến độ mặc định"** khỏi màn; máy tự giữ mã nội bộ; bỏ điều kiện "phải đặt giai đoạn trước khi sửa tiến độ".
3. **Ô "Lý do": khai báo ban đầu không có; chỉ khi SỬA** (thông tin, đơn giá, thuế, phí, lô/căn, tiến độ, mốc) mới hiện ô **"Ghi chú thay đổi"** (bắt buộc khi sửa) — lưu cùng nhật ký tự động (ai, lúc nào, cũ → mới).
4. **Mọi ô tên do người dùng gõ** (tên mốc, tên phí, mô tả…) nhận **tiếng Việt có dấu và khoảng trắng**; quy tắc "chỉ gồm chữ/số/_ . -" chỉ áp cho mã nội bộ máy tự sinh, không bao giờ hiện cho người dùng. Rà cả `crm_giao_ket.py` (sự kiện dòng lịch) và các màn khác có câu lỗi tương tự.
**Báo Anh khi:** sửa xong trên DEMO 8798 (Anh thử lại: khai mốc "Cấp giấy CN Đầu tư", lập tiến độ 10/30/40/20% gắn mốc, sửa một dòng thấy ô Ghi chú thay đổi).
**Trạng thái:** ĐÃ NHẬN 15:40 27/10 — làm cùng CD-023/024 trên dòng giao diện; giao Codex kiểm kê mã hiện có (crm_g.js, crm_du_an_ban.py, crm_giao_ket.py) + chia lát ≤3 tệp, rồi code; báo Anh khi sẵn sàng thử trên DEMO 8798.

## CD-023 · 27/10/2026 14:55 · Dự án đang bán: khai báo MỘT LƯỢT + sao chép từ dự án khác / mẫu theo loại
**Căn cứ:** Anh 27/10 14:49: "khi khai báo lại phải khai dòng phí riêng rất mất thời gian: khi khai báo dự án thì khai báo hết tất cả thông tin 1 lượt; ngoài ra có template cho nhà ở hoặc KCN hoặc cho thuê riêng (hoặc có thể không cần nhưng có nút copy từ dự án khác để sửa)". Làm cùng CD-022.
**Việc:**
1. **Một màn khai báo một lượt** (thay các hộp thoại riêng từng phần): các khối trên cùng một trang, gấp/mở được — Thông tin chung · Giá & thuế (đơn giá niêm yết, tiền tệ, loại hình, thuế mặc định) · **Phí** (bảng nhiều dòng sửa trực tiếp: tên phí · mức · đơn vị tính · tiền tệ · cơ sở tính; thêm dòng bằng Enter) · **Mốc thanh toán của dự án** (bảng: tên mốc · ngày dự kiến · ngày thực tế) · **Tiến độ thanh toán** (Lần · % · Mốc · Ghi chú — CD-022) · **Lô/căn** (bảng; cho **dán nhiều dòng từ Excel**). Một nút **Lưu** cho cả trang; kiểm lỗi hiện tại chỗ từng ô; lưu một phiên bản cho cả lượt.
2. **Nút "Sao chép từ dự án khác":** chọn dự án nguồn → điền sẵn mọi khối (trừ lô/căn, tên/mã dự án, ngày thực tế của mốc) để sửa rồi Lưu; ghi nhật ký "sao chép từ dự án X phiên bản n".
3. **Mẫu theo loại** (Nhà ở · KCN · Cho thuê): làm bằng cơ chế **"Lưu làm mẫu"** — một dự án đã khai có thể lưu thành mẫu có tên; tạo dự án mới chọn "Từ mẫu" hoặc "Từ dự án khác". Không gắn cứng nội dung mẫu trong code; Anh/kế toán tự lưu 3 mẫu từ dự án thật.
4. Ô "Ghi chú thay đổi" (CD-022 mục 3) chỉ hiện khi sửa dự án đã lưu, **một ô chung cho cả lượt sửa**, không hỏi từng dòng.
5. Đo trước/sau ghi CHANGELOG: số lần bấm và số hộp thoại để khai một dự án KCN có 3 phí, 4 mốc, tiến độ 4 đợt.
**Báo Anh khi:** sẵn sàng thử trên DEMO 8798 cùng CD-022.
**Trạng thái:** ĐÃ NHẬN 15:40 27/10 — cùng đợt CD-022 (màn khai báo một lượt, sao chép từ dự án khác, Lưu làm mẫu).

## CD-024 · 27/10/2026 15:05 · Báo giá: nút cạnh tiêu đề; Tổng có VAT; VAT đợt cọc dồn vào đợt kế tiếp
**Căn cứ:** Anh thử màn Báo giá 27/10 14:56 (ảnh: nút "+ Báo giá mới" nằm ở khối Danh sách báo giá) và chốt 15:00 qua bảng chọn; TL 45 §9 (BG-25…BG-28, đã thêm 15:05).
**Việc:**
1. **BG-25:** nút "+ Báo giá mới" ngay sau tiêu đề "Báo giá" ở đầu trang.
2. **BG-26:** Tổng giá trị (chữ to) = **giá đã có VAT**; dưới: trước VAT · VAT · bằng chữ tổng có VAT.
3. **BG-27 (phương án A):** % tính trên giá trước VAT; **đợt đặt cọc không VAT**; VAT của cọc **cộng vào đợt kế tiếp**; các đợt sau phần + VAT; đợt cọc = dòng đánh dấu "Đặt cọc" (mặc định dòng 1); VAT theo cách tính hiện có (thuế suất, phần không chịu thuế nếu có); chênh làm tròn dồn đợt cuối. Test đơn vị bằng ví dụ giả định TL 45 §9 (1.000.000.000 VND trước VAT, 10%, 10/30/60% → 100.000.000 · 340.000.000 · 660.000.000; Σ 1.100.000.000 VND).
4. **BG-28:** bảng lịch Lần · **% (chữ to, cùng cỡ với Giá trị — Anh 14:57)** · **Giá trị thanh toán (gồm VAT, chữ to)** · **trong đó VAT** · Mốc · Ghi chú; dòng tổng khớp khối Tổng; gõ tiền ở cột thanh toán → máy suy % (đợt cọc không VAT). Bản in cho khách và chuyển sang Soạn hợp đồng giữ đúng các cột này.
5. Áp cùng quy tắc VAT cọc cho tiến độ dự án nạp vào Báo giá (dự án chỉ có % + mốc — CD-022).
**Báo Anh khi:** sẵn sàng thử trên DEMO 8798 (gộp chung đợt với CD-022/023).
**Trạng thái:** ĐÃ NHẬN 15:40 27/10 — cùng đợt CD-022/023 (BG-25…BG-28, VAT đợt cọc dồn đợt kế; test ví dụ TL 45 §9).

## CD-025 · 27/10/2026 15:40 · Tổng hợp token Claude + Codex từ đầu đến nay
**Căn cứ:** Anh hỏi 27/10 15:35 "từ đầu đến giờ đã dùng bao nhiêu token của cả Codex và Claude". Hiện chỉ có `bao-cao-ngay\USAGE-20261025.md` (Codex 24/10: 16 lượt 1.460.372 token; 25/10 đến 19:20: 47 lượt 4.662.077 token; Claude chỉ có % hạn mức) và các mốc % hạn mức tuần Claude trong báo cáo đêm/TRANG-THAI.
**Việc (ưu tiên thấp, làm khi có chỗ trống, chỉ đọc):**
1. Codex: cộng dòng "tokens used" trong mọi nhật ký `codex exec` của lead từ 24/10 đến nay, theo ngày × lát × mức suy luận; ghi rõ ngày nào thiếu nhật ký.
2. Claude: ghi chuỗi % hạn mức (5 giờ, tuần mọi model, tuần Fable) theo các mốc đã ghi; số token theo model của từng worker/subagent nếu công cụ trả về; nếu Anh chạy `/usage` trong terminal thì dán vào.
3. Ghi `bao-cao-ngay\USAGE-TONG-HOP.md`; từ nay mỗi tối cập nhật thêm một dòng (CD-020 mục 5).
**Trạng thái:** ĐÃ NHẬN 16:00 27/10 — đã ghi `bao-cao-ngay/USAGE-TONG-HOP.md`: Codex 377 lượt ≈ 33,2 triệu token (24–27/10); Claude tuần mọi model **100%** (đặt lại 29/10) → lead chỉ giữ gate/gộp, review giao Codex, tạm dừng Claude tự đọc khi rút thăm; mỗi tối thêm một dòng.

## CD-026 · 30/10/2026 09:30 · ĐỊNH HƯỚNG LẠI: Core chung theo KE_HOACH_CORE_DATABASE_API_V1 — DỪNG LẬP TRÌNH, làm khảo sát + đặc tả
**Căn cứ:** Anh gửi `KE_HOACH_CORE_DATABASE_API_V1.md` (29/10) ngày 30/10 09:16 và chốt 09:25 qua bảng chọn; lưu tại `D:\Claude\Phan mem ho tro ke toan\54-ke-hoach-core-database-api-v1.md` (TL 54, §14 = quyết định của Anh). `CLAUDE.md` đã thêm dòng "DỪNG LẬP TRÌNH" (ràng buộc cứng).
**Quyết định của Anh:** (1) **Core chung cho mọi công cụ**, phần mềm kế toán là các module trên Core (cùng OCR, Mask, Tra cứu tài liệu, Phân tích tài chính); (2) **dừng hẳn mọi lập trình** tới khi Anh duyệt đặc tả; (3) database = **CSDL thật chung `D:\DU-LIEU-KE-TOAN`**; (4) **tên schema/bảng/cột tiếng Việt không dấu**.
**Việc:**
1. **Dừng ngay:** không giao lát code mới, không gộp, không migration. Lát đang dở (XS-5a2, dòng giao diện CD-022/023/024, MTQ-NEN-2c…) giữ nguyên nhánh; ghi bảng "trạng thái khi dừng" trong `TRANG-THAI.md` (nhánh, commit, đã review chưa, còn gì). Tạm hoãn CD-022/023/024 và go-live CD-016 (không phát hành tối thứ Sáu 30/10). `/loop` vẫn chạy nhưng chỉ cho việc khảo sát/đặc tả.
2. **Giai đoạn 1 — Khảo sát (chỉ đọc), ghi `docs\47-core\KHAO-SAT-CORE.md`:**
   (a) **Đối chiếu từng khối Core TL 54 §9** với cái đã có trong `hop-nhat-20261023` (XS-1…XS-5, MTQ, cổng AI, OCR-1, MASK-1/2, khung khai báo module, công tắc, kho file, sao lưu/mã hóa): có / một phần / chưa, kèm tệp:dòng;
   (b) **database:** cụm DEMO và `D:\DU-LIEU-KE-TOAN` — phiên bản, schema, role, quyền PUBLIC/kế thừa, 67 migration hiện có thuộc module nào;
   (c) **các công cụ ngoài phần mềm kế toán** mà Core phải chứa: Engine Studio (`engine-console`), OCR đối chiếu (`ocr-dual-release`), Mask v2, phần mềm review xây dựng (đóng băng), phần mềm theo dõi khoản vay — thư mục, API thực tế, cách khởi động, cổng, dữ liệu. **Thư mục chưa có quyền → liệt kê và hỏi Anh** (Anh chưa cho biết vị trí `engine-console`, `ocr-dual-release`);
   (d) trả lời các mục TL 54 §12 đã biết từ tài liệu; mục chưa biết ghi "chờ Anh".
3. **Giai đoạn 2 — Đặc tả chênh lệch** (không viết lại cái đã đúng), ghi `docs\47-core\DAC-TA-CORE-V1.md`: bảng **tên tiếng Việt không dấu** cho schema/bảng/role (thay `platform_core`, `platform_mod_*`, `users`, `jobs`…); mô hình dữ liệu Core; ma trận quyền (dùng lại MTQ, pháp nhân ↔ workspace); `module.json`; JSON Schema các contract (§5.2); OpenAPI `/api/v1/` nhóm §6.2; vòng đời job/workflow; Engine Manager + Adapter cho OCR và Mask; cách chuyển 67 migration chung sang migration theo module; **module mẫu đề xuất** để thử Core (gợi ý M9 hoặc Tra cứu tài liệu — nhỏ, dùng OCR + AI); kế hoạch chuyển từng module kế toán.
4. Worker: được dùng Codex/Claude **chỉ đọc** cho khảo sát; tài liệu đặc tả do lead soạn, review chéo một vòng.
5. Báo Anh bằng **một phiếu duyệt** (≤ 2 trang tóm tắt + các câu chốt dạng bảng chọn) khi xong giai đoạn 1–2. Anh duyệt xong mới mở lại lập trình bằng CD mới.
**Trạng thái:** ĐÃ NHẬN 30/10 10:30.
- Đã dừng lập trình; bảng trạng thái khi dừng ở TRANG-THAI 30/10.
- G0 giao 4 Codex chỉ đọc (KS-A…D, `docs\47-core\g0\`); lead đã lấy số liệu catalog DEMO.
- CSDL thật `D:\DU-LIEU-KE-TOAN\postgresql` còn rỗng.
- Engine Studio, OCR đối chiếu: lead tìm thấy ở `D:\GPT\Local AI\`, chờ Anh xác nhận.

## CD-027 · 30/10/2026 09:40 · Kế hoạch chuẩn hóa Core (API · CSDL · SDK) rồi dựng lại M4, CRM, M2 và 4 engine (bổ sung CD-026)
**Căn cứ:** Anh 30/10 09:31 ("chuẩn hóa cấu trúc API, chuẩn hóa CSDL — chia khối dữ liệu cho từng module, chuẩn hóa SDK của Core; sau đó tạo từng module M2, M4, CRM, đồng thời tạo lại engine OCR, Mask, trích xuất, hóa đơn điện tử"); chốt 09:35: engine hóa đơn = **tải + đọc hóa đơn điện tử (XML/ZIP, cổng thuế)**; thứ tự **Core → 4 engine → M4, CRM, M2 song song**. Kế hoạch: `D:\Claude\Phan mem ho tro ke toan\55-ke-hoach-chuan-hoa-core-va-dung-lai-module-engine.md` (TL 55).
**Việc:**
1. Làm theo TL 55: **G0 Khảo sát** (= CD-026 mục 2) → **G1 Chuẩn hóa** G1a CSDL (khối `loi`, `loi_tai_lieu`, `danh_muc`, `mod_crm`, `mod_m2`, `mod_m4`, `cong_bo_*`; role chạy/migration riêng; migration theo gói module; bảng ánh xạ 67 migration), G1b API (`/api/v1/`, 202 + việc, lỗi chuẩn, idempotency, row_version, OpenAPI, bảng ánh xạ route cũ), G1c SDK (Python + JS, contract JSON Schema, mẫu `module.json`, bộ kiểm tuân thủ) → **phiếu cổng C** cho Anh.
2. **Lệnh dừng lập trình CD-026 giữ tới cổng C.** Sau khi Anh duyệt cổng C, Anh sẽ mở lại bằng CD mới cho G2 (dựng Core) → G3 (e_ocr, e_mask, e_trich_xuat, e_hoa_don) → G4 (M4 mẫu đầu tiên, CRM, M2 song song).
3. Tên đề xuất trong TL 55 là nháp; lead chốt sau khảo sát, giữ tiếng Việt không dấu.
4. Việc đang dở (CD-022/023/024, XS-5a2, MTQ-NEN-2c) giữ nhánh; ở G4 chuyển vào module mới.
5. G0/G1 ghi vào `docs\47-core\` (KHAO-SAT-CORE.md, DAC-TA-CSDL.md, DAC-TA-API.md + OpenAPI, DAC-TA-SDK.md + JSON Schema, PHIEU-CONG-C.md).
**Trạng thái:** ĐÃ NHẬN 30/10 10:30 — G0 đang chạy; G1a → G1b → G1c theo thứ tự, phiếu nào xong gửi trước (CD-029).

## CD-028 · 30/10/2026 09:45 · Nguyên tắc cổng: Core giữ cổng của từng engine/module, khi cần thì nhả cho engine/module chiếm
**Căn cứ:** Anh 30/10 09:33 ("mỗi engine hoặc module chạy 1 cổng, Core giữ cổng đó ở máy chủ; khi cần gọi engine hoặc vào module thì Core tự nhả cổng để engine hay module chiếm lại cổng đó"). TL 55 §10.
**Việc (đưa vào đặc tả G1 — DAC-TA-API/DAC-TA-SDK; dựng ở G2):**
1. Sổ cổng trong `loi`: Core cấp một cổng cố định cho mỗi engine/module khi đăng ký/cài; chỉ nghe trên máy chủ.
2. Core giữ ổ nghe khi engine/module chưa chạy; có yêu cầu → khởi động và **chuyển giao ổ nghe** (Windows `socket.share()`/`fromshare()`), không khoảng hở; kiểm danh tính/phiên bản/readiness.
3. Rảnh quá thời gian cấu hình → dừng có kiểm soát → Core giữ lại cổng. **Không engine/module nào mặc định "luôn chạy", kể cả OCR, AI** (Anh 09:38).
3b. **Đo và đề xuất chế độ chạy (Anh 09:38):** Core ghi mỗi lần khởi động (giờ yêu cầu, thời gian tới sẵn sàng, thời gian chạy việc, thời gian rảnh trước khi đóng, số lần/ngày, RAM/CPU); hằng tuần **đề xuất** cho từng engine/module: tự kích hoạt + tự đóng (mặc định) / giữ lâu hơn / luôn chạy, kèm số liệu căn cứ; **chỉ Admin bấm áp dụng**, Core không tự đổi. TL 55 §10 mục 8.
4. Engine cũ không nhận ổ nghe chuyển giao: đóng rồi khởi động ngay với tham số cổng; cổng bị chiếm → báo lỗi, không dừng ứng dụng lạ.
5. Người dùng chỉ dùng địa chỉ Core; Core chuyển tiếp tới cổng nội bộ. **Mỗi module là tiến trình riêng** (thay TL 54 §4.2) — SDK/khung module phải hỗ trợ chạy độc lập và nhận ổ nghe từ Core.
6. Làm thử nghiệm kỹ thuật nhỏ (chỉ đọc/tài liệu ở G1; code thử ở G2): đo thời gian khởi động + chuyển giao cổng cho 1 engine Python.
**Trạng thái:** ĐÃ NHẬN 30/10 10:30 — đưa vào đặc tả API/SDK (G1b/G1c); KS-A đánh giá chỗ phải tách tiến trình trong server.py.

## CD-029 · 30/10/2026 09:55 · Anh đồng ý hướng triển khai TL 55; bộ API, phân chia CSDL, SDK phải gửi Anh duyệt trước
**Căn cứ:** Anh 30/10 09:53: "ok về hướng triển khai, nhưng khi có bộ API, bộ phân chia CSDL và SDK thì gửi tôi xem để duyệt trước".
**Việc:**
1. Hướng TL 55 (G0 → G5) **đã được Anh đồng ý**; tiếp tục G0–G1 theo CD-026/027/028.
2. **Cổng C tách thành 3 phiếu duyệt riêng, gửi Anh ngay khi từng bộ xong (không chờ đủ cả ba):** (a) **Phân chia CSDL** — sơ đồ khối dữ liệu theo module, bảng tên tiếng Việt không dấu, role, quy tắc ghi/đọc, bảng ánh xạ 67 migration cũ; (b) **Bộ API** — danh sách route `/api/v1/` theo nhóm, quy ước chung, ví dụ request/response cho 2–3 route tiêu biểu, bảng ánh xạ route cũ; (c) **SDK** — danh sách dịch vụ SDK Python/JS và hàm chính, contract dữ liệu, mẫu `module.json`, bộ kiểm tuân thủ.
3. Mỗi phiếu: tóm tắt ≤ 2 trang bằng tiếng Việt, kết luận trước, các điểm cần Anh chọn ở dạng bảng (phương án + khuyến nghị); chi tiết kỹ thuật (OpenAPI, JSON Schema) để phụ lục. Ghi `docs\47-core\PHIEU-DUYET-CSDL.md`, `PHIEU-DUYET-API.md`, `PHIEU-DUYET-SDK.md` và ghi một dòng "Cần Anh duyệt" vào TRANG-THAI.
4. **Không bắt đầu G2 (lập trình Core)** khi chưa có đủ 3 phiếu được Anh duyệt.
**Trạng thái:** ĐÃ NHẬN 30/10 10:30 — 3 phiếu riêng: PHIEU-DUYET-CSDL, PHIEU-DUYET-API, PHIEU-DUYET-SDK; không vào G2 khi chưa đủ 3 phiếu được duyệt.

## CD-030 · 30/10/2026 10:00 · Bắt đầu triển khai TL 55 — dùng tối đa Codex, tiết kiệm Claude, vẫn giữ chất lượng
**Căn cứ:** Anh 30/10 09:56: "cho lead triển khai, lưu ý sử dụng tối đa Codex, và dùng tiết kiệm với Claude nhưng phải đảm bảo chất lượng". Thực hiện CD-026…CD-029 ngay.
**Phân công (thay CD-004 cho giai đoạn này):**
1. **Codex làm phần lớn:** khảo sát chỉ đọc (G0), soạn nháp đặc tả CSDL/API/SDK, OpenAPI, JSON Schema, bảng ánh xạ migration/route, review chéo lẫn nhau giữa các worker Codex. Chạy **tối đa 4 Codex** song song, lát nhỏ, handoff ≤ 1 trang.
2. **Claude chỉ ở các điểm quyết định chất lượng:** lead (Opus) chia lát, ghép và **viết phần tóm tắt + câu chốt của 3 phiếu duyệt**; review Opus **chỉ** cho: thiết kế khối dữ liệu/role/RLS, quy ước API chung, contract SDK cốt lõi, nguyên tắc cổng — mỗi phần một lượt, tối đa 2 vòng. Kiểm nhanh nhẹ dùng Haiku. Không dùng Claude cho việc soạn nháp, liệt kê, đếm, chuyển định dạng.
3. **Giữ chất lượng:** mỗi tài liệu Codex soạn phải qua 1 vòng review chéo Codex + kiểm xác suất của lead (~1/4 lát, chọn trước rồi mới gộp — bài học 27/10); mọi khẳng định về code hiện có phải kèm tệp:dòng; Opus review bắt buộc trước khi gửi Anh mỗi phiếu.
4. **Hạn mức:** ghi `/usage` đầu ngày và cuối ngày vào `USAGE-TONG-HOP.md`; Claude tuần ≥ 80% → lead chỉ giữ ghép phiếu + review Opus của phiếu, còn lại chuyển Codex; Codex báo hết công suất → giảm còn 3 worker, không giao lại dồn.
5. Thứ tự: G0 khảo sát (song song 4 Codex: (a) xương sống/Core hiện có, (b) database + 67 migration, (c) route/API hiện có, (d) công cụ ngoài: Mask v2, OCR-1, bộ tải hóa đơn, #6/E1; Engine Studio/OCR đối chiếu chờ Anh cho vị trí) → G1a CSDL → G1b API → G1c SDK; phiếu nào xong gửi Anh trước (CD-029).
6. Lệnh dừng lập trình (CD-026) vẫn giữ: G0–G1 chỉ tài liệu; không code, không gộp code, không migration.
**Trạng thái:** ĐÃ NHẬN 30/10 10:30 — 4 Codex chỉ đọc; Claude chỉ ghép phiếu + review Opus điểm cốt lõi; kiểm xác suất chọn trước (G0: KS-B); /usage đầu ngày đã ghi (tuần 1%).

## CD-031 · 30/10/2026 13:45 · Phiếu SDK — contract dữ liệu: JSON hai lớp, bổ sung contract NGHIỆP VỤ theo module
**Căn cứ:** Anh trao đổi 30/10 13:28–13:45 về mục 5 `docs\47-core\PHIEU-DUYET-SDK.md`: "không hiểu tại sao không trao đổi dữ liệu dạng JSON và bao gồm tất cả các thông tin yêu cầu; việc thể hiện tiền dạng chữ số hoặc mã tiền tệ chỉ là yếu tố rất nhỏ, không đại diện cho tất cả các loại nghiệp vụ". Anh chốt: **JSON hai lớp, bổ sung contract nghiệp vụ theo module**.
**Việc:**
1. **Sửa cách trình bày trong phiếu SDK:** nói rõ dữ liệu trao đổi là **JSON**; contract (JSON Schema) chỉ là bản mô tả gói JSON phải có những thông tin gì để Core kiểm tự động. Không nhấn mạnh chi tiết định dạng tiền ở phần tóm tắt (để phụ lục).
2. **Lớp kỹ thuật** (Core định nghĩa — giữ 9 contract hiện có): tệp, văn bản tài liệu, bảng, tham số, nội dung đã che, trả lời AI, hóa đơn (đọc từ XML), lỗi, việc.
3. **Lớp nghiệp vụ** (module sở hữu dữ liệu định nghĩa, Anh duyệt) — lập **danh mục + ví dụ JSON đầy đủ** cho từng contract, trường lấy từ thiết kế đã chốt (TL 42, 45, 49, 50; thiết kế M4 20/10 + CD-011; TL 43 M2-00; CD-022…024), mỗi trường ghi nguồn:
   - **CRM:** `hop_dong_ban` (phiên bản, tham số, lịch thanh toán % + giá trị gồm VAT + VAT, mốc dự kiến/thực tế), `bao_gia`, `du_an_dang_ban` (thông tin, giá & thuế, phí, mốc, tiến độ %, lô/căn);
   - **M4:** `hop_dong_thau`, `phu_luc`, `boq`, `dot_thanh_toan`, `ket_qua_kiem_dot`, `nghiem_thu`;
   - **M2:** `hoa_don_mua_vao` (đã nhận, đích hạch toán, trạng thái), `cong_no_phai_tra`;
   - **Chung:** `doi_tuong`, `du_an`, `but_toan_de_xuat`, `tep_nhap_junsky`;
   - **Sự kiện:** `tien_da_noi_dot`, `ban_giao_da_duyet`, `moc_da_xay_ra`, `hop_dong_hieu_luc`, `hoa_don_da_nhan`.
4. Mỗi contract nghiệp vụ: mục đích · module sở hữu · module được đọc · danh sách trường (tên tiếng Việt không dấu, nghĩa, bắt buộc/tùy chọn, đơn vị) · một ví dụ JSON DEMO đầy đủ · trạng thái/phiên bản. Phần tóm tắt cho Anh ≤ 2 trang; chi tiết để phụ lục `docs\47-core\g1\CONTRACT-NGHIEP-VU.md`.
5. Codex soạn nháp (tối đa song song theo module), Codex review chéo; Opus review một lượt phần quy tắc chung + 3 contract cốt lõi (`hop_dong_ban`, `dot_thanh_toan`, `but_toan_de_xuat`). Gửi lại Anh **phiếu SDK bản 2** (câu 1–3 cũ giữ nguyên + mục contract mới).
**Trạng thái:** ĐÃ NHẬN 30/10 14:00 — 4 Codex soạn contract nghiệp vụ (CRM, M4, M2, Chung+sự kiện; đề `docs/47-core/g1/GIAO-G1C-NV.md`) → Codex review chéo → Opus quy tắc chung + 3 contract cốt lõi → phiếu SDK bản 2.

## CD-032 · 30/10/2026 13:50 · Quy tắc: mỗi module phải tạo lớp dữ liệu giao tiếp có cấu trúc để gắn vào Core (sổ contract)
**Căn cứ:** Anh 30/10 13:42: "contract Core sẽ phải thường xuyên cập nhật khi có module mới vì có nguồn dữ liệu khác nhau; phải ghi quy tắc để mỗi module khi tạo cũng phải hình thành lớp dữ liệu giao tiếp một cách có cấu trúc để gắn vào Core". TL 55 §11; `CLAUDE.md` thêm dòng "Lớp dữ liệu giao tiếp".
**Việc (đưa vào phiếu SDK bản 2 cùng CD-031 và đặc tả G1c):**
1. Gói module bắt buộc có `contract/` (dữ liệu công bố, sự kiện phát/nhận, đầu vào nguồn); mỗi contract: mục đích, sở hữu, được đọc, trường (tên tiếng Việt không dấu, nghĩa, bắt buộc, đơn vị, nguồn), ví dụ JSON đầy đủ, JSON Schema, phiên bản; `module.json` liệt kê. Thiếu/không hợp lệ → không cài.
2. **Sổ đăng ký contract** trong `loi`: cài/nâng cấp module → Core kiểm và đăng ký thêm, không sửa code Core; ghi mã, phiên bản, module sở hữu, module đang dùng, trạng thái (nháp / Anh duyệt / đang dùng / ngừng); màn quản trị xem sổ.
3. Bộ kiểm tuân thủ thêm: contract mới trùng nghĩa contract đã có → đỏ (phải dùng lại/mở rộng contract chung); module đọc dữ liệu module khác ngoài contract đã đăng ký + cấp quyền → đỏ.
4. Contract nghiệp vụ mới hoặc phiên bản mới của contract đang được dùng → Anh duyệt trước khi kích hoạt; xuất danh mục dạng bảng (như `Danh-muc-contract-du-lieu.xlsx` phiên điều phối đã gửi Anh) để duyệt.
5. Phiên bản cũ giữ cho module đang dùng; sổ cảnh báo module còn dùng phiên bản sắp ngừng.
6. Áp ngay cho M4, CRM, M2 ở G4: mỗi module làm `contract/` trước khi làm màn hình.
**Trạng thái:** ĐÃ NHẬN 30/10 14:00 — đưa `contract/` + sổ contract trong `loi` + kiểm trùng nghĩa vào đặc tả SDK/CSDL và phiếu SDK bản 2.

## CD-033 · 30/10/2026 13:55 · Anh trả lời 3 câu phiếu SDK
**Căn cứ:** `docs\47-core\PHIEU-DUYET-SDK.md` mục 2; Anh trả lời 30/10 13:44–13:51 trong phiên điều phối (câu 2 sau khi được giải thích kỹ: tài khoản máy tính phụ trên cùng máy chủ, như thẻ ra vào khác nhau trong cùng tòa nhà; Core giữ "két" `D:\DU-LIEU-KE-TOAN\bi-mat\`).
**Quyết định:**
1. **Câu 1 — Module thử Core ở G2: CRM** (Anh chọn, khác khuyến nghị A). Dùng **dữ liệu DEMO**; phạm vi thử đủ đi qua: tệp, engine (trích xuất/OCR), việc lâu, công bố + sự kiện, `contract/` (CD-032), cài/tắt qua giao diện, ma trận thẩm quyền, cổng do Core giữ/nhả (CD-028). Lead đề xuất phạm vi CRM tối thiểu cho G2 (vd: Dự án đang bán + Báo giá) để Anh xem cùng phiếu SDK bản 2; G4 thứ tự M4 → CRM → M2 giữ nguyên, phần CRM đã thử ở G2 được dùng tiếp.
2. **Câu 2 — A:** module/engine chạy dưới **tài khoản máy tính phụ có quyền hạn chế** (vd `ktt_module`), Core dưới tài khoản riêng (vd `ktt_core`); áp **ngay từ giai đoạn thử trên máy Anh**, không chạy chung tài khoản. Script tạo tài khoản + cấp quyền thư mục, chạy lại được khi chuyển máy chủ; Anh chỉ bấm đồng ý quyền quản trị. Engine cũ cần tài khoản riêng (vd ABBYY Hot Folder) → ghi ngoại lệ, hỏi Anh, không tự nới quyền. Bộ kiểm tuân thủ kiểm tiến trình module/engine không đọc được thư mục bí mật.
3. **Câu 3 — A:** module đang tự đóng mà có việc chờ → Core bật ngay; Admin đổi theo số đo (CD-028 mục 3b); không tự bật module Anh đã tắt.
**Việc:** cập nhật `PHIEU-DUYET-SDK.md` thành bản 2 gồm 3 câu trên (đã chốt) + phần contract JSON hai lớp (CD-031) + quy tắc lớp dữ liệu giao tiếp và sổ contract (CD-032); gửi Anh duyệt toàn phiếu. Sau khi Anh duyệt phiếu SDK bản 2, chờ CD mở lại lập trình (G2).
**Trạng thái:** ĐÃ NHẬN 30/10 14:00 — ghi 1 CRM, 2A, 3A vào phiếu SDK; lead đề xuất phạm vi CRM tối thiểu cho G2 trong phiếu bản 2.

## CD-034 · 30/10/2026 14:00 · Xuất BẢN CUỐI 3 chuẩn Core (API · CSDL · SDK) dạng md để hướng dẫn lập trình module khác
**Căn cứ:** Anh 30/10 13:54: "Sau khi chỉnh lại và chốt lại API, CSDL và SDK, hãy cho tôi file md bản cuối của 3 mục này để tôi hướng dẫn lập trình của module khác". Đã duyệt: phiếu API (1A, 2A), phiếu CSDL (1A, 2A, 3A). SDK: chờ bản 2 (CD-031, CD-032, CD-033).
**Việc (làm ngay sau khi Anh duyệt phiếu SDK bản 2; API và CSDL có thể soạn trước):**
1. Ba file **bản chuẩn v1.0 đã duyệt**, viết cho **người lập trình module mới** (nội bộ hoặc AI worker) đọc là làm được, không cần đọc phiếu/biên bản review:
   - `CHUAN-CORE-CSDL-v1.0.md` — khối dữ liệu (`loi`, `loi_tai_lieu`, `danh_muc`, `mod_<ma>`, `cong_bo_<ma>`), quy tắc đặt tên tiếng Việt không dấu, kiểu dữ liệu (UUID, numeric + đơn vị, timestamptz, row_version), role chạy/migration, RLS theo pháp nhân + mã phiên bí mật (câu 1A), mã hóa cột nhóm A, migration trong gói module, việc module **được/không được** làm, checklist trước khi nộp gói.
   - `CHUAN-CORE-API-v1.0.md` — `/api/v1/` và namespace `/api/v1/module/{ma}/…`, xác thực, lỗi chuẩn tiếng Việt, 202 + việc, idempotency, row_version/409, phân trang, cổng do Core giữ/nhả (CD-028), danh sách route Core module được dùng, ví dụ request/response, checklist.
   - `CHUAN-CORE-SDK-v1.0.md` — dịch vụ SDK Python/JS + hàm chính + ví dụ dùng; khung chạy module/engine (nhận cổng, sẵn sàng, dừng); tài khoản máy tính hạn chế (CD-033 câu 2); `module.json` mẫu đầy đủ; **lớp dữ liệu giao tiếp `contract/`** + sổ contract (CD-031, CD-032) kèm mẫu contract nghiệp vụ và ví dụ JSON; bộ kiểm tuân thủ (danh sách KT); checklist.
2. Mỗi file: phiên bản, ngày Anh duyệt, căn cứ (phiếu + CD); kết luận đầu file; phần "Bắt buộc" / "Khuyến nghị" tách rõ; ví dụ dùng module mẫu giả định (không dữ liệu thật, không tên công ty thật); phụ lục trỏ tới đặc tả chi tiết `docs\47-core\g1\` (OpenAPI, JSON Schema) thay vì chép nguyên.
3. Lưu tại `docs\47-core\chuan\` **và** bản sao tại `D:\Claude\QUY-TRINH-CHUNG\CHUAN-CORE\` (để Anh dùng cho dự án/module khác). Mọi thay đổi sau này → tăng phiên bản, ghi mục "Thay đổi" đầu file.
4. Codex soạn từ đặc tả đã duyệt; Opus review một lượt (đúng với phiếu đã duyệt, không thêm quyết định mới — quyết định mới phải hỏi Anh). Báo Anh khi xong (ghi TRANG-THAI "Cần Anh xem: 3 chuẩn Core v1.0").
**Trạng thái:** ĐÃ NHẬN 30/10 14:30 — Codex đang soạn CHUAN-CORE-CSDL và CHUAN-CORE-API v1.0 (đề `docs/47-core/chuan/GIAO-CHUAN-V1.md`); CHUAN-CORE-SDK soạn sau khi Anh duyệt phiếu SDK bản 2.

## CD-035 · 30/10/2026 14:10 · Bước sau 3 chuẩn Core: dựng Core + 5 engine song song, rồi module
**Căn cứ:** Anh 30/10 14:01 và chốt 14:05 qua bảng chọn; TL 55 §12 (thay bảng engine §5).
**Thứ tự:** CD-034 (3 chuẩn Core v1.0) → **G2 dựng Core và G3 năm engine song song** → cắm engine vào Core, thử bằng CRM (CD-033) → G4 module M4, CRM, M2. Lệnh dừng lập trình CD-026 vẫn giữ tới khi Anh duyệt phiếu SDK bản 2 và ra CD mở lại.
**5 engine:**
1. `e_ocr` — lõi **ABBYY FineReader, Hot Folder** (OCR-1, cách của phần mềm review); Core quản lý thư mục in/out; ABBYY cần tài khoản riêng → ghi ngoại lệ, hỏi Anh.
2. `e_mask` — **Mask file v2** (API MASK-1/2); không che tiền/ngày.
3. `e_trich_xuat` — **phần trích xuất theo tham số của phần mềm review xây dựng** (37 tham số, Local AI) + danh mục theo loại E1-MUA.
4. `e_hoi_ai` (**mới**) — tách cổng AI hiện có (`tri_thuc/cong_ai.py`, AI-1/AI-2) thành engine chung: Local luôn có, Cloud chỉ qua `e_mask`, đo độ chính xác Local, kiểm xác suất (TL 48); hỗ trợ cờ "chỉ Local" cho M9.
5. `e_hoa_don` — **tải hóa đơn từ cổng hóa đơn điện tử + đọc XML/ZIP thành contract `hoa_don`** (bộ tải #7/M2-00, `nguon/hoa_don_xml.py`); gọi cổng thuế thật chỉ khi Anh ra lệnh riêng.
**Mỗi engine:** contract vào/ra, adapter, test mẫu dữ liệu giả chạy độc lập, tài khoản hạn chế (CD-033), Core giữ/nhả cổng + số đo khởi động (CD-028), không giữ mật khẩu/khóa. Chuẩn bị ngay (chỉ tài liệu, trong lúc chờ SDK bản 2): bản giao việc từng engine (≤ 1 trang, lát nhỏ ≤ 3 tệp, Codex làm chính) để mở lại lập trình là chạy được ngay.
**Trạng thái:** ĐÃ NHẬN 30/10 14:30 — Codex soạn bản giao việc 5 engine (ENGINE-1: e_ocr, e_mask, e_hoi_ai; ENGINE-2: e_trich_xuat, e_hoa_don), chỉ tài liệu.

## CD-036 · 30/10/2026 14:15 · Engine phải DÙNG LẠI code đã có — 4 thư mục nguồn chính thức
**Căn cứ:** Anh 30/10 14:04: "vẫn phải lưu ý Claude Code sử dụng lại những gì đã có, hạn chế code lại hoàn toàn từ đầu". Phiên điều phối kiểm 14:10: khảo sát G0 của lead (`docs\47-core\g0\KS-D.md`, `KS-E.md`) **đã đọc được cả 4 thư mục**, có dẫn chiếu tệp:dòng (review_xaydung 22 chỗ, download hóa đơn 26, Mask v2 39, `D:\GPT\OCR\ocr-abbyy-ai\ocr_web\app.py:25`, `:315`).
**Nguồn chính thức cho từng engine:**
| Engine | Nguồn dùng lại |
|---|---|
| `e_ocr` | `D:\GPT\OCR\ocr-abbyy-ai` (và thư viện nó dùng trong `D:\GPT\OCR`: `abbyy-hotfolder`, `mask_ocr`) |
| `e_mask` | `D:\GPT\Phan mem Mask file\Mask file v2` |
| `e_trich_xuat` | `D:\Claude\Ho tro review ho so xay dung\review_xaydung` (phần `trich_xuat`) |
| `e_hoa_don` | `D:\Claude\Phan mem download hoa don` (+ `nguon/hoa_don_xml.py` trong repo) |
| `e_hoi_ai` | cổng AI trong repo (`tri_thuc/cong_ai.py`, AI-1/AI-2) |
**Quy tắc:**
1. **Ưu tiên bọc (adapter) quanh code gốc**, giữ nguyên thuật toán và test gốc; chỉ chép code vào gói engine khi bắt buộc — ghi nguồn + SHA256 + phiên bản bản gốc.
2. **Không sửa bản gốc** nếu chưa hỏi Anh; riêng Mask v2 nếu cần sửa thì theo `CLAUDE.md` của Mask v2 (không git, CHANGELOG, test + độ phủ không giảm); review_xaydung đang đóng băng (CD-011).
3. Mỗi bản giao việc engine (CD-035) có bảng **"dùng lại nguyên / bọc / sửa / viết mới"** theo từng phần, kèm lý do cho phần viết mới; Opus review kiểm bảng này. Phần viết mới chỉ cho: adapter theo contract, khung chạy (cổng, sẵn sàng, dừng — CD-028), lớp vận hành Core.
4. Test gốc của từng nguồn phải đạt khi chạy qua engine (cùng dữ liệu giả).
5. Áp dụng tương tự cho module G4 (M4 dùng lại review_xaydung + M4 hiện có; CRM, M2 dùng lại code `hop-nhat`).
**Trạng thái:** ĐÃ NHẬN 30/10 14:30 — bảng "dùng lại nguyên / bọc / sửa / viết mới" bắt buộc trong mỗi bản giao việc engine; Opus review kiểm bảng này.

## CD-037 · 30/10/2026 14:20 · Để phiên điều phối chỉ đạo lead liên tục: bật Remote Control + tác vụ tự khởi động lại
**Căn cứ:** Anh 30/10 14:06: "hãy chỉ đạo lead một cách liên tục". Phiên điều phối đã đặt tác vụ giám sát 2 giờ/lần (đọc git, hộp thư, TRANG-THAI; nhắn lead nếu nhắn được; báo Anh khi lead dừng hoặc có việc cần Anh). Lead đã dừng 27/10 16:23 → 30/10 (nghi hết hạn mức tuần, `/loop` không tự chạy lại sau hạn mức, `/loop` hết hạn sau 7 ngày — tài liệu Claude Code).
**Việc (việc vận hành, không phải lập trình sản phẩm — được làm dù CD-026 còn hiệu lực):**
1. Cấu hình phiên lead **nhận tin từ phiên Claude khác** (cross-session messaging, cài `crossSessionInbound` cho nhận thẳng, không giữ chờ duyệt) và ghi hướng dẫn 1 dòng để Anh gõ `/remote-control` khi mở phiên lead. Ghi phiên bản Claude Code đang dùng (`claude --version`; cần ≥ 2.1.234 trên Windows).
2. **Tác vụ tự khởi động lại** bằng Windows Task Scheduler (tài khoản của Anh, không cần quyền quản trị nếu được): 30 phút/lần kiểm tra — nếu không có phiên lead nào đang chạy (khóa tệp/PID) thì chạy `claude -c -p "Đọc docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md, làm một lượt theo CD-020" --permission-mode auto` trong thư mục repo; có khóa chống chạy trùng với cửa sổ lead; ghi nhật ký mỗi lần chạy vào `var\nhat-ky-tu-khoi-dong.log`. Thử một lần, báo Anh kết quả (đặc biệt: chế độ `-p` có chạy được bằng đăng nhập gói Max không).
3. Script đặt trong `tools\`, có tệp `.cmd` để Anh bấm đúp cài/gỡ tác vụ; không đụng kho thật, không đọc `.env`.
**Báo Anh khi:** thử xong tác vụ tự khởi động lại; cần Anh bấm `/remote-control`.
**Trạng thái:** CẦN ANH XÁC NHẬN 30/10 14:30 — Claude Code 2.1.300 (đạt); thử `claude -p` bằng gói Max: chạy được. Script `tools/lead_tu_khoi_dong.ps1` + `tools/CAI-TU-KHOI-DONG-LEAD.cmd` / `GO-TU-KHOI-DONG-LEAD.cmd` đã viết, thử nhánh "lead còn sống" đạt (nhịp `var/lead-nhip.txt`); tác vụ Windows **chưa cài** — Anh bấm đúp CAI để cài. `crossSessionInbound` (nhận tin phiên khác không chờ duyệt) là đổi cài đặt an ninh: chờ Anh xác nhận trong chat.

## CD-038 · 30/10/2026 17:30 · Anh duyệt phiếu SDK bản 2 + trả lời 3 câu engine + cho nhận tin; MỞ LẠI LẬP TRÌNH khi chuẩn SDK v1.0 xong
**Căn cứ:** Anh trả lời qua bảng chọn 30/10 17:20–17:28 trong phiên điều phối: `docs\47-core\PHIEU-DUYET-SDK.md` (bản 2) và `docs\47-core\engine\PHIEU-CAU-HOI-ENGINE.md`; CD-037 (nhận tin phiên khác).
**Quyết định:**
1. **Duyệt phiếu SDK bản 2** và **phạm vi CRM thử Core ở G2** như mục 3 của phiếu.
2. **SDK câu 1 — A:** lịch nghĩa vụ hợp đồng bán bản đầu chỉ gồm **giá bán chia %** (Σ% = 100 cho phần giá bán); phí theo dõi riêng, thêm sau không phá phiên bản.
3. **SDK câu 2 — B (Anh chọn khác khuyến nghị):** **cho phép** cọc là đợt cuối hoặc nhiều đợt cọc; **VAT của đợt cọc dồn vào đợt KHÔNG cọc gần nhất phía sau; hết đợt phía sau thì dồn ngược về đợt không cọc gần nhất phía trước**. Lịch toàn đợt cọc (không có đợt không cọc) → báo lỗi. Cập nhật contract `bao_gia`/`hop_dong_ban`, engine tính lịch, test (thêm ca: cọc đợt cuối; 2 đợt cọc liền nhau; cọc xen giữa), và TL 45 §9 BG-27 (bỏ ràng buộc "đợt cọc = dòng 1").
4. **Engine câu 1 — C (Anh chọn khác khuyến nghị):** **đổi câu hỏi của bản trích xuất review sang mẫu của cổng AI chung** (không gọi thẳng máy AI, không thêm đường riêng). Vì đổi thuật toán: (a) chép phần trích xuất vào `e_trich_xuat` (ghi nguồn + SHA, **không sửa bản gốc** review đang đóng băng); (b) **đo lại độ chính xác** trên bộ đáp án hiện có (`DAP_AN_*.tsv`, 37 tham số) trước/sau — **không được thấp hơn bản gốc**; thấp hơn → dừng, báo Anh kèm số liệu; (c) test gốc được sửa phải ghi rõ ca nào đổi và vì sao.
5. **Engine câu 2 — A:** phần tải hóa đơn chạy trong **phiên Windows riêng có màn hình** (ngoại lệ như ABBYY) để người gõ CAPTCHA; mỗi pháp nhân một hồ sơ trình duyệt, xóa sau phiên; mật khẩu lấy từ két Core. Gọi cổng thuế thật vẫn chỉ khi Anh ra lệnh riêng.
6. **Engine câu 3 — A:** Anh mở khóa danh mục Mask tại máy chủ; Mask **không tự đóng** khi danh mục đang mở (ngoại lệ của CD-028 mục 3); engine giữ bí mật (Mask, AI Cloud, tải hóa đơn, ABBYY) **mỗi engine một tài khoản máy riêng**, khác tài khoản module.
7. **CD-037 — cho phép** cài `crossSessionInbound` để phiên lead **nhận tin từ phiên điều phối không chờ Anh duyệt từng tin** (tin là thông tin; không thay Anh duyệt quyền, không đổi cài đặt; ràng buộc `CLAUDE.md` vẫn thắng). Anh sẽ tự bấm đúp `tools\CAI-TU-KHOI-DONG-LEAD.cmd`.
8. **Mở lại lập trình:** soạn ngay `CHUAN-CORE-SDK-v1.0.md` (CD-034), Opus review; **khi chuẩn SDK v1.0 xong thì lệnh dừng CD-026 hết hiệu lực** — bắt đầu **G2 dựng Core + G3 năm engine song song** theo TL 55, CD-035, CD-036 và bản giao việc engine đã sửa theo các câu trên. Giữ: tối đa Codex (CD-030), lát nhỏ, review chéo + kiểm xác suất, Opus ở điểm cốt lõi; cổng D (cài thử module CRM) báo Anh. Cập nhật dòng "DỪNG LẬP TRÌNH" trong `CLAUDE.md` thành "đã mở lại <giờ> theo CD-038".
**Trạng thái:** XONG phần tài liệu 30/10 17:52 — chuẩn SDK v1.0 Opus Đạt; 3 chuẩn chép sang QUY-TRINH-CHUNGCHUAN-CORE; **lập trình mở lại 17:52** (CLAUDE.md đã ghi); giao G2 đợt A. crossSessionInbound: lead bị chặn tự sửa cài đặt → Anh tự bật.

## CD-039 · 30/10/2026 17:30 · Lead tự cài tác vụ tự khởi động lại (Anh không ngồi máy)
**Căn cứ:** Anh 30/10 17:25: "đang không ngồi trên máy tính nên không bấm đúp được". `tools\CAI-TU-KHOI-DONG-LEAD.cmd` ghi "Không cần quyền quản trị" (schtasks cho tài khoản hiện tại).
**Việc:** Anh cho phép lead **tự cài** tác vụ `KTT-Lead-Tu-Khoi-Dong` bằng đúng lệnh `schtasks /Create …` trong tệp `.cmd` (bỏ `pause`); kiểm bằng `schtasks /Query /TN "KTT-Lead-Tu-Khoi-Dong"`; ghi kết quả vào TRANG-THAI và `var\nhat-ky-tu-khoi-dong.log`. Nếu Windows đòi quyền quản trị/hộp xác nhận → không ép, ghi "Cần Anh bấm đúp khi về máy". Không sửa script ngoài phạm vi CD-037.
**Trạng thái:** MỚI
