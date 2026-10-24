# Trạng thái — lead Claude Code cập nhật khi lát đổi trạng thái

Trạng thái lát: Đang code → Chờ kiểm → Chờ Anh (cổng A/B) → Sửa → Xong · Bị chặn. Kế hoạch và hàng đợi đầy đủ: `4-KE-HOACH-LEAD.md`. Nền test: `NEN-TEST.md` mục 0b — **nền v3** (mục 0a, sau L0-3c): 1408/22/44/360, 1 treo.

## Lát đang chạy (tối đa 3 worker)

| Lát | Việc | Worker | Nhánh · worktree | Giao lúc | Trạng thái |
|---|---|---|---|---|---|
| BG-1b | CRM · Báo giá gói 1 màn hình (BG-01…05) | Claude Sonnet | `lat/bg-1b` (86d5b5b) · DEMO http://127.0.0.1:8784 | 24/10 | **Chờ Anh cổng A** — phiếu `PHIEU-CONG-A-BAO-GIA-GOI-1.md`; lead đã tự thử (lịch 4 cột, dòng tổng, Σ 90% chặn In/Chuyển); ô/dòng 9→3, nút tính 1→0 |
| M4-4/7 | M4 · đăng ký M0028 (master dùng chung) + M0029 (03B ghi nhận chung), chỉ append; chứng minh migrate 0→29 trên CSDL DEMO riêng | Claude Sonnet | `lat/m4-47` · DEMO 8789 | 25/10 | Đang code |
| M2e | M2-00 · nút "Tải từ cổng thuế" trong M2: route mỏng + giao diện, nối `dieu_phoi`/`khach`/`nhan`; tự thử với bộ tải giả | Claude Sonnet | `lat/m2e` · DEMO 8787 | 24/10 | Đang code — bị ngắt 1 lần, đã nối lại (đã có route mỏng, đăng ký server, cấu hình; còn giao diện, test) |
| L0-7 | Sửa trong sản phẩm: engine #6 nạp sẵn openpyxl/numpy ở luồng chính tiến trình con; `.gitattributes` cho review_goc; seed duyệt viên DEMO | Claude Sonnet | `lat/l0-7` · DEMO 8788 | 24–25/10 | Đang code — bị ngắt 1 lần (đứng 600 giây), đã nối lại |

## Lát đã xong (24/10)

| Lát | Kết quả | Gộp vào hop-nhat |
|---|---|---|
| M2d | M2-00 · manifest hồi cứu HOI_CUU (chỉ đọc thư mục cũ); review Đạt (~45 ca tấn công đường dẫn bị chặn); vòng 2: gốc hồi cứu tin cậy, junction, run_id theo tên thật, chặn chuỗi quá dài; 173/0/0/1 | da3d666 |
| L0-6 | Engine #6 DEMO: nguyên nhân gốc — openpyxl tự import numpy (Python hệ thống) lần đầu ở luồng worker khi tiến trình con đang phục vụ → kẹt, timeout 60s. Vá tạm ở launcher worktree (chặn numpy), đồng bộ byte-pin review_goc; dựng 2 đợt DEMO M4 (cổng 8786). **DEMO của Anh và `MỞ PHẦN MỀM.cmd` có thể treo 60s ở lệnh trích đầu** → sửa sản phẩm ở L0-7 | 1d1c12f |
| L0-3b | Hết treo `test_source6_g5_e5`: mock dùng chung tham chiếu yêu cầu làm lệch niêm phong → client chờ 30 phút không nghỉ; sửa mock (deepcopy, đồng hồ giả) + 2 test sai đầu vào; module 16/0/0/2 | 146a28b |
| E1-1 | E1-MUA · sổ đăng ký 6 danh mục tham số hợp đồng mua trong bản vá #6, ghim SHA, không fallback XD; 13 test mới đạt; tệp .xlsx áp vào #6 thật ở E1-5 | d5fe3cc |
| L0-3c | 12 test lỗi thời N5 cập nhật (không nới ý nghĩa); pin crm_giao_ket theo BG-1a; toàn bộ test: ok 1276→1408, ERROR 34→22, FAIL 57→44 → **nền v3** | ad7d3d4 |
| M2c | M2-00 · nhận hóa đơn theo manifest qua đường K2 sẵn có; review Đạt, vòng 2 sửa 4 điểm (độ phủ, giữ chờ theo mục, thiếu bảng kê, số 0 đầu SHDon); 141/141 | b190569 |
| M4-2 | M4 · giao diện Duyệt đợt & PDF: hop-nhat đã có logic fix01 (3 lỗi); thêm 15 dòng style + test hồi quy fix01 12/12 (chứng minh bắt lỗi trên bản chưa sửa). Chưa chụp được màn có dữ liệu: engine #6 DEMO ngắt sau lệnh trích đầu (→ L0-6) | ff9503f |
| L0-2c | M4 · Nghiệm thu & chi phí dự án: gộp backend duyệt/PDF (13 xung đột, giữ HN mới hơn) + đăng ký M0026/M0027 (27 migration, chỉ append); ok 728→757, ERROR 27→18; Request M4 103/0 | c4deb00 |
| BG-1a | CRM · Báo giá gói 1 máy chủ: ô thông minh, ghi đè tổng có cảnh báo + nhật ký, nhãn tên, mốc chuẩn; vòng 2: % xấp xỉ cho dòng nhập tiền, chặn Chuyển ở máy chủ, định dạng tiền, số kiểu Việt; 85 đạt, 0 lỗi mới | 5a8042a |
| M2b | M2-00 · đọc/kiểm manifest + POLICY-TIENTE-01 v1 (ca M2-00-06, -10, 3 ràng buộc); review Claude Đạt, vòng 2 sửa 2 điểm lệch TL 43 §6; 67/67 | 4e1f6bb |
| L0-4b | CSDL CRM DEMO riêng cho lập trình (`-CsdlRieng`); CSDL DEMO của Anh không đổi (schema 23, băm trước = sau) | 550f573 |
| P0 | Khôi phục 24 file chưa vào git (CRM G6A/G5-B, M4 duyệt/Request/03A); `pg_migrations` nạp được (25); module lỗi nạp 29 → 1; ok 501 → 1067; không test vốn đạt nào hỏng | 1c5c67a |
| L0-3a | Runner: gốc repo vào sys.path + `--runtime` (Python có psycopg); `.gitattributes` cho file bị ghim byte; 19 fixture DEMO vào git; trên nhánh lát: ERROR 112 → 62, FAIL 20 → 6 | 7b114e2 |
| L0-4 | `tools\mo_demo_worktree.ps1`: mở DEMO cho worktree, chặn khi CSDL CRM DEMO dùng chung có thể hỏng | 7cbc41b |
| L0-1 | Nền test: chinh 711/25/31/272 · 0 treo; hop-nhat 501/112/20/140 · 1 treo; 5 nhóm nguyên nhân | a1da3d4 |
| L0-2a | Common identity fix01→04, khớp byte bản fix | 73deacb |
| L0-2d | CRM m4-three + G5; khôi phục hồi quy H3 (M0023 về đúng checksum `chinh`) | b2fd07c |
| L0-2e | M2-00 fix01 + `config.js` bị sót | 3a2b083 |
| L0-2f | Source6 ordered-fix01; không hết treo → L0-3b | d07117a |
| L0-2i | 27 file chưa vào git, 26 file có bản mới hơn ngoài git | 8b4670f |

Worktree đo nền: `.claude/worktrees/nen-chinh-59b7d8e` (chinh) · `.claude/worktrees/nen-hop-nhat-v2` (hop-nhat 7b114e2).

## Khóa file dùng chung (mỗi lúc một lát)

| File | Lát giữ |
|---|---|
| `src\kho_tri_thuc\giao_dien\server.py` | M2e |
| `giao_dien\m4.py` | — |
| `nguon\trich6_host.py`, `tools\chuan_bi_crm_demo.py`, `.gitattributes` | L0-7 |
| `giao_dien\assets\app.js`, `index.html`, `ha_tang\config.py` | M2e |
| `ha_tang\pg_migrations.py` | M4-4/7 (chỉ append M0028, M0029) |
| `giao_dien\crm_g.py`, `k2\crm_giao_ket.py` | — |
| `giao_dien\assets\crm_g.js`, `style.css` | BG-1b |
| `m4\*` dùng chung | — |
| `tests\` (chỉ test lỗi thời N5) | — |
| `m4\giao_dien\m4_duyet_pdf.js`, `m4.js`, `m4.css` | — |
| `tools\mo_demo_worktree.ps1`, `CLAUDE.md` | lead |

## Màn hình / module chờ Anh

| Màn | Trạng thái |
|---|---|
| CRM · Báo giá (#42, TL 45) | **Chờ Anh cổng A gói 1** (24/10) — phiếu `PHIEU-CONG-A-BAO-GIA-GOI-1.md` |

## Việc phụ (lead làm, ghi để Anh biết)

- 24/10, khi L0-4 chạy thử trên bản sao `chinh`, CSDL CRM DEMO dùng chung của Anh đã được nâng lên schema 23 (đúng bản `chinh`) và nạp thêm dữ liệu mẫu DEMO. Từ L0-4b trở đi lập trình dùng CSDL riêng.

---

# Trạng thái hợp nhất — 24/10/2026 (bàn giao từ Codex, giữ làm lịch sử)

| Phần | Đã có | Còn pending / kết luận |
|---|---|---|
| Nền Git | `chinh` giữ H1 `59b7d8e`; `hop-nhat-20261023` giữ H2/H3; không push, không xóa tệp | H5 chờ Anh xem báo cáo H4; không gộp vào `chinh` |
| M2 | 00A Source7 và 00B owned-RPC đã nhập; FIX01 còn ở `luu/m2-00b-fix01` do xung đột | H4 có lỗi nhiều ở các test M2-00B; chưa nghiệm thu |
| M4 | Căn cứ, master reuse, 03A, common identity gốc, 04A/04B/UI copy và một số registration đã nhập; các gói xung đột nằm trên `luu/*` | M4B2/B3 chưa terminal; UI/Review chưa kiểm độc lập hoặc xác minh GUI; chưa nghiệm thu |
| CRM | G4 và G6A-M25 registration đã nhập; G5, CRM-M4-three giữ riêng trên `luu/*` | CRM chưa kiểm độc lập trên head hợp nhất; chưa xác minh GUI; chưa nghiệm thu |
| Shared extraction Source6 | Lazy Excel, DOCX tables, G5/E5 đã nhập | Ordered fix còn `luu/*`; toàn engine chưa nghiệm thu |
| M0/M1/M3/M5/M6–M10 | Không có gói code mới được H3 nhập riêng trong đợt này | H1 là nền cũ; không có căn cứ để kết luận các module này hoàn tất. H4 có lỗi M1 và bridge tests |
| H4 | SQLite log ghi 625 kết quả: 206 ok, 275 ERROR, 4 FAIL, 140 skipped; tiến trình treo trước footer/report | H4 không đạt/không hoàn tất; PostgreSQL chưa chạy; không sửa và không chạy lại |

H3 phân loại 36 đầu việc: 19 gói đã nhập `hop-nhat`, 13 xung đột giữ ở `luu/*`, 2 gói chưa xác nhận terminal giữ ở `luu/*`, 2 dòng không có code delta mới (report-only/bản trùng). Không có path xóa trong diff `chinh..hop-nhat`; working tree sạch tại thời điểm ghi.

**Thời gian đo được:** từ commit H1 lúc 07:16:48 đến commit H3 cuối lúc 07:45:03 là khoảng 28 phút 15 giây; tới log H4 cuối lúc 07:47:29 là khoảng 30 phút 41 giây. Đây là khoảng giữa mốc commit/log, không phải tổng thời gian lịch sử của dự án hay thời gian chạy từng worker.

**Agent:** tại lần kiểm tra hiện tại không có tiến trình Claude Code đang chạy. Trong cây Codex có 1 root và 3 subagent ở trạng thái interrupted; không có subagent hoạt động. 36 dòng frozen là 36 đầu việc, không chứng minh có 36 agent. Sổ theo dõi không có số phút hoặc danh tính worker đầy đủ cho toàn bộ lịch sử.

**Tiếp theo:** Anh xem các nhánh `hop-nhat` và `luu/*`, cùng log H4; sau đó chốt hướng phân tích lại. Chưa làm H5, không push GitHub và không di chuyển thư mục.