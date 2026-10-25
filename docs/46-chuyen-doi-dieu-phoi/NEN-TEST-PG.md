# NEN-TEST-PG — test PostgreSQL trên cụm DEMO (L0-8, 25/10/2026, QD-20261025-10)

Đo bằng `tools/chay_test_theo_module.py --pg-demo` (lệnh ở `CLAUDE.md` mục 5) trên `lat/l0-8` (= hop-nhat `8ff21a2` + công cụ). Dạng máy đọc: `nen-test-hop-nhat-pg.json` (106 module, worktree), `nen-test-hop-nhat-pg-fixture-crlf.json` (45 module PG, bản chép có fixture CRLF), nền cùng commit không PG: `nen-test-hop-nhat-v5.json`.

## 1. Cách đặt biến và bảo vệ DROP (không lộ bí mật)
- DSN đọc **bằng chương trình** từ `ket-noi.local.json`; chỉ đặt `KHO_PG_DSN_TEST` (URI, DSN quản trị trỏ CSDL `postgres`) vào môi trường **tiến trình con của test**. Không in/log/ghi DSN; cuối lần chạy quét nhật ký và kết quả tìm mật khẩu: **0 tệp**. Từ chối DSN không loopback hoặc có khóa lạ.
- Module cần bản sao DEMO (`*_CLONE_*`): công cụ dựng riêng `kho_test_pgd_<hex>` bằng `k2.crm_khoi_dong.chuan_bi` (migrate + seed), ghi dấu nguồn/checksum lên `master.he_thong`, đặt biến, xóa sau module. Dựng được 4 họ: 02C, 04A, master dùng chung, G6A. **Chưa dựng: 03A/03B** (cần login kế toán có vai dự án KE_TOAN do Root cấp) — giữ skip như cũ.
- DROP chỉ khi: tên khớp `^kho_test_[a-z0-9_]+$` **và** không có trong ảnh chụp danh sách CSDL trước khi chạy **và** thuộc sổ "đã tạo" (`pg-demo-so-ghi.json`, ghi trước khi tạo); không FORCE (còn phiên → chờ rồi báo); khóa tệp chặn hai lần chạy song song (đã thử: lần hai thoát ngay); DROP chạy sau MỖI module (kể cả lỗi/treo) và cuối cùng. Kiểm thử âm: `kho_crm_demo_lt_*`, `postgres`, tên có ký tự lạ, chữ hoa → bị từ chối trước khi chạm CSDL. Không DROP vai trò. Lần chạy chết giữa chừng: `--pg-demo-don-so <sổ>`.

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

## 4. Bằng chứng không sót CSDL tạm (lần chạy cuối, cụm DEMO loopback)
- Worktree: CSDL trước/sau 337 / 338; **tạo 66, xóa 66, sót 0**; CSDL có sẵn mất 0. Bản chép CRLF: 338 / 338, tạo 66, xóa 66, sót 0. Một CSDL lạ xuất hiện (`kho_crm_demo_lt_p8793`, do worker khác mở DEMO) — **không đụng**.
- Toàn phiên: tổng CSDL 335 → 337 (+2 `kho_crm_demo_lt_*` của người khác), `kho_test_*` 323 → 323. Một CSDL lỗi `kho_test_pgd_dbg0001` do **tôi** gọi tay lúc gỡ lỗi đã được xóa (đúng tên, có tiền tố).
- **Còn lại: vai trò** `ktt_test_*`/`kho_test_*` do test tạo (cấp cụm, công cụ **không** xóa theo quyết định): 94 → 159 (+65 qua 5 lần chạy có test tạo vai trò; 13 mỗi lần cả bộ worktree, 19 mỗi lần 45 module). Tên của hai lần cuối nằm trong `pg-demo-so-ghi.json` (khóa `vai_tro_test_de_lai`) ở thư mục nhật ký. Cần quyết: dọn tay hay thêm lệnh `--pg-demo-don-vai-tro`.

## 5. Đề xuất
1. Quyết A (ghim lại SHA fixture hoặc `-text`) trước khi tin số ở worktree; 2. lát sửa B (+D); 3. lát điều tra E; 4. M4-03A/03B cần Root cấp login KT để bật; 5. giữ `--gioi-han 900` (cả bộ ~16 phút; `test_v13_backup_safety_pg` ~160 s).
