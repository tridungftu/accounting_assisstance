# Trạng thái — lead Claude Code cập nhật khi lát đổi trạng thái

Trạng thái lát: Đang code → Chờ kiểm → Chờ Anh (cổng A/B) → Sửa → Xong · Bị chặn. Kế hoạch và hàng đợi đầy đủ: `4-KE-HOACH-LEAD.md`. Nền test: `NEN-TEST.md` mục 0b — **nền v2** hop-nhat 7b114e2: 1276/34/57/292, 1 treo; so với chinh chỉ 3 module có lỗi mới, đều là test lỗi thời (→ L0-3c).

## Lát đang chạy (tối đa 3 worker)

| Lát | Việc | Worker | Nhánh · worktree | Giao lúc | Trạng thái |
|---|---|---|---|---|---|
| BG-1b | CRM · Báo giá gói 1 màn hình (BG-01…05) → cổng A | Claude Sonnet | `lat/bg-1b` (từ `lat/bg-1a`) · `.claude/worktrees/lat-bg-1b` · DEMO cổng 8784, CSDL riêng `p8784` | 24/10 | Đang code |
| BG-1a | CRM · Báo giá gói 1 máy chủ | Codex (code) · Claude (review) | `lat/bg-1a` (56c46c9) | 24/10 | Sửa vòng 2 — review Claude vòng 1: Đạt, 0 Chặn; lead chọn sửa 4 điểm theo TL 45 §3 (dòng nhập tiền không chặn vì % không tròn; chặn Chuyển ở máy chủ; định dạng tiền thống nhất; ô ghi đè nhận số kiểu Việt) |
| L0-2c | M4 · Nghiệm thu & chi phí dự án: gộp backend duyệt/PDF (lượt 1: 5 file gộp 3 bên) rồi đăng ký migration 26–27 (lượt 2) | Codex | `lat/l0-2c` · `.claude/worktrees/lat-l0-2c` | 24/10 | Đang code (lượt 1) |

## Lát đã xong (24/10)

| Lát | Kết quả | Gộp vào hop-nhat |
|---|---|---|
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
| `src\kho_tri_thuc\giao_dien\server.py` | — |
| `giao_dien\m4.py` | L0-2c |
| `giao_dien\assets\app.js`, `index.html` | — |
| `ha_tang\pg_migrations.py` | L0-2c (lượt 2) |
| `giao_dien\crm_g.py`, `k2\crm_giao_ket.py` | BG-1a (chờ review) |
| `giao_dien\assets\crm_g.js`, `style.css` | BG-1b |
| `m4\*` dùng chung (`duyet_dot.py`, `fixtures_m4.py`, `m4_demo.py`, `xay_dung.py`) | L0-2c |
| `tools\mo_demo_worktree.ps1`, `CLAUDE.md` | lead |

## Màn hình / module chờ Anh

| Màn | Trạng thái |
|---|---|
| CRM · Báo giá (#42, TL 45) | Đang làm gói 1: BG-1a xong code (đang review) · BG-1b màn hình đang code → cổng A trên CSDL DEMO riêng |

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