# Trạng thái — lead Claude Code cập nhật khi lát đổi trạng thái

Trạng thái lát: Đang code → Chờ kiểm → Chờ Anh (cổng A/B) → Sửa → Xong · Bị chặn. Kế hoạch và hàng đợi đầy đủ: `4-KE-HOACH-LEAD.md`. Nền test: `NEN-TEST.md`.

## Lát đang chạy (tối đa 3 worker)

| Lát | Việc | Worker | Nhánh · worktree | Giao lúc | Trạng thái |
|---|---|---|---|---|---|
| P0 | Khôi phục file chưa vào git để hop-nhat import được (CRM G6A/G5-B, M4 duyệt/Request/03A) | Claude Opus | `lat/p0` · `.claude/worktrees/lat-p0` | 24/10 | Đang code |
| L0-4 | Lệnh mở DEMO cho worktree, có CRM PostgreSQL | Claude Sonnet | `lat/l0-4` · `.claude/worktrees/lat-l0-4` | 24/10 | Đang code |
| L0-3a | Lỗi môi trường N3/N4 + bộ chạy test dùng Python có psycopg | Codex + lead | `lat/l0-3a` (b20019d) | 24/10 | Chờ kiểm — lead đang chạy toàn bộ test có `--runtime`; 19 fixture DEMO đã vào git (ngoại lệ .gitignore hẹp) |
| M2b | M2-00 · đọc/kiểm manifest + POLICY-TIENTE-01 v1 (ca M2-00-06, -10) | Codex | `lat/m2b` · `.claude/worktrees/lat-m2b` | 24/10 | Đang code |

## Lát đã xong (24/10)

| Lát | Kết quả | Gộp vào hop-nhat |
|---|---|---|
| L0-1 | Nền test: chinh 711/25/31/272 · 0 treo; hop-nhat 501/112/20/140 · 1 treo (`test_source6_g5_e5`); 5 nhóm nguyên nhân | a1da3d4 |
| L0-2a | Common identity fix01→04, khớp byte bản fix | 73deacb |
| L0-2d | CRM m4-three + G5; khôi phục hồi quy H3 (crm-g4 ghi đè bản cũ, M0023 về đúng checksum `chinh`); review Codex vòng 1: 2 điểm Chặn lead giải bằng bằng chứng | b2fd07c |
| L0-2e | M2-00 fix01 + `config.js` bị sót; không nguyên nhân lỗi mới | 3a2b083 |
| L0-2f | Source6 ordered-fix01; không hết treo → L0-3b | d07117a |
| L0-2i | 27 file chưa vào git (8 đang bị import), 26 file có bản mới hơn ngoài git | 8b4670f |

Worktree đo nền `chinh`: `.claude/worktrees/nen-chinh-59b7d8e` (tách rời ở 59b7d8e, chỉ chạy test).

## Khóa file dùng chung (mỗi lúc một lát)

| File | Lát giữ |
|---|---|
| `src\kho_tri_thuc\giao_dien\server.py` | — |
| `giao_dien\m4.py`, `giao_dien\assets\app.js`, `index.html`, `style.css` | — |
| `ha_tang\pg_migrations.py` | — (P0 không sửa; chỉ khôi phục module nó import) |
| `giao_dien\crm_g.py`, `giao_dien\assets\crm_g.js` | P0 (thay `crm_g.js` bằng bản 27a0d3db) |
| `m4\*` dùng chung | P0 (chỉ thêm file thiếu) |
| `tests\run_suite.py`, `tools\chay_test_theo_module.py`, `.gitattributes`, `.gitignore` | L0-3a (chờ gộp) |
| `CLAUDE.md` mục 5 | L0-4 |

## Màn hình / module chờ Anh

| Màn | Trạng thái |
|---|---|
| CRM · Báo giá (#42, TL 45) | Chưa làm — BG-1a sau P0; cổng A cần L0-4 (lệnh mở DEMO có CRM) |

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