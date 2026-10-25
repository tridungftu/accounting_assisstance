# DA-1c — CRM · Dự án đang bán: thuế theo QD-20261025-20 (sửa M0031 trước khi gộp)

Bạn là worker Codex, chạy không tương tác. Anh đã chốt (bảng chọn 25/10): **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM. Worktree hiện tại, nhánh `lat/da-1` (commit `f31e012`, **chưa gộp** — M0031 còn sửa được). Sandbox không ghi `.git`: **không commit**. Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module test_crm_du_an_ban` (PG skip; lead chạy PG sau).

**Quyết định (đọc `docs/QUYET-DINH.md` QD-20261025-20):**
- Đơn giá niêm yết và mức phí **luôn là giá chưa gồm VAT** → bỏ lựa chọn "đã gồm/chưa gồm" (`co_so_thue` NET/GROSS) khỏi thông tin bán hàng.
- Mức thuế: **danh mục cố định** `10` / `8` / `5` / `0` / `KCT` (Không chịu thuế) / `KKKNT` (Không kê khai, nộp thuế) — **mặc định 10**; thay `vat_phan_tram` tự do. Nhãn tiếng Việt trong `danh_muc` trả cho màn hình.
- Một mức thuế chung của dự án áp cho giá chính và các phí.
- **Phần giá đất được trừ**: `gia_dat_tru` = đơn giá đất/m² (cùng tiền tệ với đơn giá niêm yết, ≥ 0, ≤ đơn giá niêm yết, mặc định 0) — không tính VAT. Giá tính VAT của giá chính = (đơn giá − giá đất được trừ) × diện tích (công thức để DA-3 dùng; DA-1c chỉ lưu và trả trong ảnh chụp).

**Việc:**
1. Sửa SQL M0031 trong `k2/sql_crm_du_an_ban.py` (bảng phiên bản thông tin bán hàng): bỏ `co_so_thue`, đổi `vat_phan_tram` → `thue_suat text NOT NULL DEFAULT '10' CHECK (thue_suat IN (...))`, thêm `gia_dat_tru numeric NOT NULL DEFAULT 0` với CHECK miền (≥ 0, ≤ `don_gia_niem_yet`), chữ số ASCII theo mẫu `_RE_SO` hiện có. Cập nhật hàm SQL đọc/ghi + `master.crm_da_anh_chup` (ảnh chụp có `thue{thue_suat, nhan, gia_chua_gom_vat: true}`, `gia_dat_tru`); `anh_chup_sha256` vẫn không phụ thuộc ngày gọi.
2. Service `k2/crm_du_an_ban.py` + route `crm_g.py` (chỉ khối `_dieu_huong_da`): nhận/kiểm `thue_suat` (ngoài danh mục → 400 kèm `truong`), `gia_dat_tru` (parse chặt, > đơn giá → 400); bỏ nhận `co_so_thue`/`vat_phan_tram` (gửi lên → 400 trường lạ). `danh_muc.thue_suat` có nhãn tiếng Việt.
3. Seed DEMO `tools/chuan_bi_crm_demo.py`: dự án KCN DEMO có `gia_dat_tru` > 0 (vd 20% đơn giá), dự án nhà ở DEMO `thue_suat` 10, `gia_dat_tru` 0.
4. Test: cập nhật `tests/test_crm_du_an_ban.py` + `tests/test_crm_du_an_ban_pg.py` — mặc định 10, ngoài danh mục bị từ chối, giá đất > đơn giá bị từ chối, ảnh chụp có thuế + giá đất, sửa thuế → phiên bản mới.

**File được sửa (chỉ):** `src/kho_tri_thuc/k2/sql_crm_du_an_ban.py`, `src/kho_tri_thuc/k2/crm_du_an_ban.py`, `src/kho_tri_thuc/giao_dien/crm_g.py` (chỉ khối `_dieu_huong_da`), `tools/chuan_bi_crm_demo.py`, `tests/test_crm_du_an_ban.py`, `tests/test_crm_du_an_ban_pg.py`. **Không** sửa `pg_migrations.py`, phần khác của `crm_g.py`, màn hình; không xóa file; không dữ liệu thật.
**Test phải đạt:** `--module test_crm_du_an_ban --module "test_crm_*"` không thêm mã lỗi so với trước khi sửa.
**Báo cáo cuối (≤ ½ trang):** cột/CHECK đổi gì · contract JSON đổi gì (DA-2b/DA-3 dùng) · file đã sửa · test đạt/tổng · thông điệp commit `[DA-1] thuế theo QD-20261025-20: …`.
