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
**Trạng thái:** ĐÃ NHẬN 20:40 26/10 — giao Codex kiểm kê + chia lát XS-1…XS-4 theo TL 53 (chỉ tài liệu) rồi giao code từng lát; các lát MTQ-4/CD-016 đang chạy giữ nguyên.
