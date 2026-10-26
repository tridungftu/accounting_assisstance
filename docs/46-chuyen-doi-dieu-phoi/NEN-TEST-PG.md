# NEN-TEST-PG — test PostgreSQL trên cụm DEMO (L0-8, 25/10/2026, QD-20261025-10)

Đo bằng `tools/chay_test_theo_module.py --pg-demo` (lệnh ở `CLAUDE.md` mục 5) trên `lat/l0-8` (= hop-nhat `8ff21a2` + công cụ). Dạng máy đọc: `nen-test-hop-nhat-pg.json` (106 module, worktree), `nen-test-hop-nhat-pg-fixture-crlf.json` (45 module PG, bản chép có fixture CRLF), nền cùng commit không PG: `nen-test-hop-nhat-v5.json`.

## 1. Cách đặt biến và bảo vệ DROP (không lộ bí mật)
- **Vòng 2 (25/10/2026): chỉ kiểm bằng test thuần/mock, không kết nối PostgreSQL, không chạy lại số đo PG.** Các bảng mục 2–4 là lịch sử vòng 1, không phải bằng chứng an toàn của phiên bản đã sửa.
- DSN đọc **bằng chương trình** từ `ket-noi.local.json`; đặt `KHO_PG_DSN_TEST` (URI quản trị) trong môi trường **tiến trình con của test**. Lọc URI `postgres://`/`postgresql://`, `password=…`, DSN đầy đủ và mật khẩu thật (kể cả ngắn, dạng URL/JSON escape) **trước khi ghi/in**: tiến độ từng test, traceback, stdout/stderr qua pipe trong RAM, log module, JSON kết quả/chi tiết và console. Quét cuối chỉ là lưới an toàn. Từ chối DSN không loopback, khóa lạ hoặc admin/app khác host:port.
- Module cần bản sao DEMO (`*_CLONE_*`): công cụ dựng riêng `kho_test_pgd_<hex>` bằng `k2.crm_khoi_dong.chuan_bi` (migrate + seed), ghi dấu nguồn/checksum lên `master.he_thong`, đặt biến, xóa sau module. Dựng được 4 họ: 02C, 04A, master dùng chung, G6A. **Chưa dựng: 03A/03B** (cần login kế toán có vai dự án KE_TOAN do Root cấp) — giữ skip như cũ.
- Một lớp `_SoHuuPg` thực thi DROP cho cả test con, đường nội bộ `--pg xoa` và `--pg-demo-don-so`. Tại nơi DROP kiểm đủ: tên khớp `^kho_test_[a-z0-9_]+$` (tối đa 63 ký tự), mục chưa hoàn tất thuộc **đúng mã lần chạy ngẫu nhiên và cụm nguồn host:port**, tên **không có trong ảnh chụp trước** lưu nguyên danh sách trong sổ. Đối chiếu cả host:port của kết nối thực thi. Không suy sở hữu từ chênh lệch danh sách; CSDL mới của tiến trình khác không bị nhận vào sổ/xóa.
- Sổ v2 ghi bền (`flush` + `fsync` + thay tệp) **trước CREATE** qua hook `psycopg.Cursor.execute`; khóa sổ giữa các tiến trình con. Sau từng DROP thành công ghi bền `da_xoa` ngay; tên đã hoàn tất/hủy không tái sử dụng. CREATE trùng tên bị hủy quyền sở hữu. Tên không còn tồn tại cũng được đóng mục, tránh xóa nhầm tên được tạo lại sau đó. SQL dùng `psycopg.sql.Identifier`, không FORCE, không ngắt phiên. Sổ v1 thiếu thông tin hoặc sổ khác cụm/lần chạy bị từ chối. Dọn phiên chết: `--pg-demo-don-so <sổ-v2>`; chạy lại không DROP mục đã hoàn tất.
- `test_ket_noi` và `test_pg_schema` nhận `KHO_PG_DEMO_DB` do runner tạo; không tự CREATE/DROP dưới `--pg-demo`. Ca `test_t15_vai_tro_ke_toan_khong_thay_bao_mat` skip rõ lý do vì thao tác vai trò cấp cụm chưa qua sổ; ngoài chế độ này chỉ DROP vai trò `ktt_test_*` tự CREATE thành công ngay trong test. Runner không DROP ROLE.
- `PYTHONUSERBASE` tạm có `.pth` cho phụ thuộc và hook trong Python con do test tự sinh. Probe returncode khác 0/stdout rỗng phải dừng; đường dẫn sau `resolve()` phải nằm trong nhật ký lần chạy trước khi tạo thư mục/ghi `.pth`. Hook khởi tạo lỗi phải dừng Python con. Không sửa runtime.
- Test thuần: `tests/test_chay_test_pg_demo.py` dùng psycopg/subprocess giả; kiểm CSDL người khác, chết sau CREATE/dọn đúng một lần, sổ/cụm sai, trạng thái bền từng DROP, trích dẫn identifier/bỏ FORCE, bí mật trong traceback/stdout/JSON/console, probe lỗi/rỗng/ngoài nhật ký. Hai module cũ giữ skip khi thiếu PostgreSQL; ba module không `--pg-demo` được so trước/sau theo kết quả, bỏ thời gian chạy.

## 2. Số đo
| | module | ok | ERROR | FAIL | skip | chạy thật* | thời gian |
|---|---|---|---|---|---|---|---|
| Nền không PG, cùng commit (v5) | 106 | 1560 | 22 | 42 | 362 | 1624 | 320 s |
| **`--pg-demo`, worktree** | 106 | **1691** | 57 | 69 | **137** | 1817 | 956 s |
| 45 module PG — nền / worktree / bản chép CRLF | 45 | 229 / 360 / 396 | 14 / 49 / 44 | 40 / 67 / 67 | 323 / 98 / 78 | 283 / 476 / 507 | — |

\*ok+ERROR+FAIL. **skip giảm 225 (362 → 137), nhưng chỉ thêm 193 test chạy thật**: một lớp bị skip ở `setUpClass` chỉ tính 1 skip. Test CSDL mới **đạt +131** (ERROR +35, FAIL +27). So với v4 (103 module): cùng kết luận (v4 = 362 skip).
Đạt mới đáng kể: `test_m5_k2` +26, `test_pg_schema` +16, `test_crm_41_02_http` +12, `test_ket_noi` +11, `test_v13_backup_safety_pg` +11 (chạy lâu, ~100–160 s), `test_crm_k2` +18, `test_m4_01b_pg` +8, `test_m4_01c_http` +7, `test_crm_ky_ket` +4. Bản chép CRLF thêm: `test_l11_k2` 2 → 23, `test_l11_http` 0 → 2, `test_m2_http` 1 → 3, `test_m4_master_dung_chung_http` 0 → 3.

## 3. Mã lỗi MỚI so với nền cùng commit (62 ở worktree; 58 ở bản chép CRLF)
| Nhóm | Ca | Loại | Ghi chú / việc |
|---|---|---|---|
| A. Fixture bị chuẩn hóa LF, SHA ghim theo CRLF (`FIXTURE_PIN`) | 7 (`test_l11_k2` 4, `l11_http`, `m2_http`, `crm_k2`) | **môi trường** | Chỉ ở worktree mới checkout (`.gitattributes` `eol=lf`); 24 tệp fixture lệch byte so với bản làm việc CRLF của Anh. Ở bản chép CRLF: **0 ca**. **Chặn cả việc dựng bản sao DEMO ở worktree** (`m2_demo`/`l11_demo` kiểm SHA) → 10 lần dựng thất bại, nên ở worktree các họ 02C/04A/MC/G6A vẫn thiếu biến. Cần quyết: ghim lại SHA hoặc `-text` cho các fixture đó |
| B. Test cứng số migration cũ (assert 13…25 ≠ 29 hiện hành) | 18 (12 module: `m0_m5_migrations` 5, `l11_migrations` 2, `m2_migrations` 2, `crm_*`, `m4_*`…) | **test cũ** | Cần cập nhật hằng số trong test (lát riêng); gây tiếp nhóm D |
| C. M9 (đã dừng): DEMO không cấp module M9, thiếu bảng `kho.chung_tu_tien_encoding`, v.v. | 18 (toàn `test_m9_k2`, gồm cả ca kiểu B/D/E của module này) | **quyết định M9 dừng** | Bỏ qua cho tới khi mở M9 |
| D. Dây chuyền: test trước hỏng → `KeyError` ở trạng thái dùng chung | 11 (`crm_ky_ket_http` 4, `crm_neutral_compat` 4, `crm_giao_ket_http` 3) | hệ quả của B | Tự hết khi sửa B |
| E. Chưa xác định (cần xem từng ca) | 8: `crm_giao_ket_http` 3 (G04 FX, G08/G10), `crm_k2` 2 (T01b/T01c), `crm_ky_ket_http` K07, `m5_http` (400 ≠ 501), `pg_schema` T16 (bộ chuyển exit 1, không stderr) | **có thể code** | Lát điều tra riêng |
| F. Bản chép CRLF: gate cứng schema 24 (`m4_02c`, 2), `TypeError expected_master` (`m4_master_dung_chung_pg`, 1) | +3 | test cũ / mã–test lệch | Lộ ra khi bản sao dựng được |
Còn lại là lỗi đã có ở nền (37 ca G6A "thiếu KTT_G6A_CLONE_*" ở worktree; ở bản chép CRLF G6A tới cổng và dừng vì "cần schema 25, hiện 29"; 13 ca `go_request_nhap`…). Sửa công cụ trong lúc đo: tiến trình con do test tự sinh (`PYTHONPATH=src` ghi đè đường dẫn phụ thuộc) không thấy `psycopg` (`PG_DRIVER`) → công cụ thêm `PYTHONUSERBASE` tạm có `.pth` (+7 ok, −9 FAIL).

## 4. Số liệu dọn CSDL tạm vòng 1 (lịch sử, chưa chứng minh sở hữu)
- Review vòng 1 phát hiện cơ chế nhận nhầm CSDL mới và sổ thiếu bằng chứng sở hữu. Các số dưới đây không đủ để kết luận an toàn; vòng 2 thay cơ chế, không thực hiện lại trên cụm thật.
- Worktree: CSDL trước/sau 337 / 338; **tạo 66, xóa 66, sót 0**; CSDL có sẵn mất 0. Bản chép CRLF: 338 / 338, tạo 66, xóa 66, sót 0. Một CSDL lạ xuất hiện (`kho_crm_demo_lt_p8793`, do worker khác mở DEMO) — **không đụng**.
- Toàn phiên: tổng CSDL 335 → 337 (+2 `kho_crm_demo_lt_*` của người khác), `kho_test_*` 323 → 323. Một CSDL lỗi `kho_test_pgd_dbg0001` do **tôi** gọi tay lúc gỡ lỗi đã được xóa (đúng tên, có tiền tố).
- **Còn lại: vai trò** `ktt_test_*`/`kho_test_*` do test tạo (cấp cụm, công cụ **không** xóa theo quyết định): 94 → 159 (+65 qua 5 lần chạy có test tạo vai trò; 13 mỗi lần cả bộ worktree, 19 mỗi lần 45 module). Tên của hai lần cuối nằm trong `pg-demo-so-ghi.json` (khóa `vai_tro_test_de_lai`) ở thư mục nhật ký. Cần quyết: dọn tay hay thêm lệnh `--pg-demo-don-vai-tro`.

## 5. Đề xuất
1. Quyết A (ghim lại SHA fixture hoặc `-text`) trước khi tin số ở worktree; 2. lát sửa B (+D); 3. lát điều tra E; 4. M4-03A/03B cần Root cấp login KT để bật; 5. giữ `--gioi-han 900` (cả bộ ~16 phút; `test_v13_backup_safety_pg` ~160 s).

## Nền PG v2 — 25/10/2026 22:05 · hop-nhat `ec3d7d2` (sau L0-8e/8f, AI-2a, T-MIG2, C3d, M4-5a)
Lệnh: `--runtime var\web\crm-demo\runtime.local.json --pg-demo …ket-noi.local.json --gioi-han 900` (bộ chạy có hook bảo vệ cho tiến trình con/cháu — L0-8e). Kết quả: **126 module · 2327 ok / 21 ERROR / 66 FAIL / 67 skip · 0 treo · 1134 s**; CSDL tạm tạo 74 / xóa 74, không sót. Dạng máy đọc: `nen-test-hop-nhat-pg-v2.json`. So nền PG cũ (`nen-test-hop-nhat-pg.json`, 8ff21a2): 12 mã lỗi "mới", lead phân loại:
| Nhóm | Mã | Hướng |
|---|---|---|
| Ghim byte helper `test_m4_02c_pg.py` (L0-8f sửa helper) | `test_m4_03a_m26_integration`, `test_m4_04c_m27_integration` `…helper_m4_02c_pg_nguyen_byte` | cập nhật ghim (T-NEN-a) |
| Test ghim số migration cũ | `test_m4_02b_k2.k01` (22), `test_m4_02c_http/pg setUpClass` (24) | kiểm M00xx có mặt, không ghim tổng (T-NEN-a) |
| Hook "không xóa" trong tiến trình test (giống DEMO thật) | `test_e1_mua_danh_muc_sua`, `test_e1_mua_trich_phien_ban` (thư mục tạm giữ lại), `test_m1.test_backup_does_not_succeed_without_referenced_raw` | test nhận biết guard (T-NEN-b) |
| Cần điều tra | `test_m4_master_dung_chung_pg.g02` (TypeError `expected_master`, thấy từ 19:36), `test_source6_lazy_excel` ×3 (bố cục đóng băng) | T-NEN-c |
| Chập chờn đã biết | `test_trich6_host.HandlerSoHuuTests.test_cong_chan_truoc_handler_goc` | — |

## Nền PG v3 — 26/10/2026 01:28 · hop-nhat 7e9b915 (sau gộp đêm: da-2 + T-DA2, AI-3, MDA M0035, M4-5b)

Lệnh: `tools\chay_test_theo_module.py --runtime … --pg-demo … --gioi-han 900` trên bản tách `kiem-hn-dem` (có 2 tệp ghim lõi Review). Tệp số đo: `nen-test-hop-nhat-pg-v3.json`.

| | ok | ERROR | FAIL | skip | module | TREO |
|---|---|---|---|---|---|---|
| PG v2 (25/10 22:05, ec3d7d2) | 2327 | 21 | 66 | 67 | 126 | 0 |
| **PG v3 (26/10 01:28, 7e9b915)** | **2433** | **20** | **66** | **66** | **132** | **0** |

So v2: **0 mã lỗi mới**; +106 ok (module mới: mốc dự án, 03B HTTP, AI-3…). Node: 13 bộ đạt (v2: 11; T-DA2 sửa `crm_ky_ket_async`). Lỗi còn lại như triage v2 (thiếu `KTT_G6A_CLONE_*`, `test_source6_lazy_excel` thiếu bản candidate — T-NEN-c2 bị chặn, `test_web` chập chờn…). Từ 26/10: so lát mới với **PG v3**.

## Nền PG v4 — 26/10/2026 14:15 (hop-nhat fd9b991 + M2-BR4b 2b634ed)
- Cả bộ `--pg-demo` trên thư mục chính (sau M0037–M0043, M3-1a/1b, MTQ-1…4a0b, M4-DL1…DL3, CD1, M2-BR4): 149 module, ok 2877 / ERROR 21 / FAIL 67 / skip 65, 0 module treo, 1553 giây.
- Mục `test_hoa_don_xml` lấy từ lần chạy sau khi gộp M2-BR4b (4 FAIL do test BR4 đọc fixture CRLF trên thư mục chính đã hết). `test_trich6_host.HandlerSoHuuTests.test_cong_chan_truoc_handler_goc` lỗi mạng chập chờn (đã biết, CLAUDE.md §4) — giữ trong nền.
- Tệp: `nen-test-hop-nhat-pg-v4.json`. So các lát sau với **v4**.
