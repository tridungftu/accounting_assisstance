# Loạt 6 (27/10 ~15:45) — KK-UI-DA-BG (CD-022/023/024) và MTQ-4f2

## Phần chung

- Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM; `pg_migrations.py` giữ LF.
- **Ghi tệp bằng apply_patch, không qua chuỗi PowerShell nháy kép** (`$$` PL/pgSQL bị mất). Tự kiểm `AS $$`/`$$`.
- Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ hoặc có thể làm rộng quyền: dừng, ghi "Cần lead". Không có `python` thì NOT_RUN; lead chạy test/PG.
- Test PG tự tạo `kho_test_*`, **chạy dưới vai ứng dụng thật**, dữ liệu giả đúng trigger/ràng buộc, chạy được dưới guard giữ tệp. Không kiểm CRLF/LF.
- Migration: chỉ thêm `M00xx_*` với dấu `# <MÃ LÁT> — …:`; **không tự đặt số**; không sửa migration cũ; test không ghim migration cuối.

## KK-UI-DA-BG · Kiểm kê + chia lát cho CD-022, CD-023, CD-024 (chỉ tài liệu)

**Nhánh:** worktree này dựng từ `lat/ui-dem` (dòng giao diện mà DEMO 8798 của Anh đang chạy). **Chỉ tạo một tệp** `docs\46-chuyen-doi-dieu-phoi\KK-UI-DA-BG.md`; không sửa mã.

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` mục **CD-022, CD-023, CD-024** (quyết định Anh đã chốt — không bàn lại);
- `D:\Claude\Phan mem ho tro ke toan\45-*.md` (TL 45 Báo giá, §9 BG-25…BG-28) nếu có;
- CD-006/007 (mốc dự án).
- Mã: `src\kho_tri_thuc\giao_dien\assets\crm_g.js` (~390, ~542, ~570), `src\kho_tri_thuc\k2\crm_du_an_ban.py` (~120, ~541), `src\kho_tri_thuc\k2\crm_giao_ket.py` (~289), `k2\sql_crm_du_an_ban.py`, `k2\sql_crm_du_an_moc.py`, các SQL báo giá (`crm_gk_*` trong `ha_tang\pg_migrations.py`), test node/py hiện có của các màn này.

**Việc:** tài liệu gồm:
1. **Hiện trạng** từng yêu cầu: chỗ mã đang làm (tệp:dòng), cái gì dùng lại được, cái gì phải đổi. Gồm:
   - CD-022: bảng % + mốc; bỏ "Giai đoạn tiến độ mặc định"; "Ghi chú thay đổi" chỉ khi sửa; tên tiếng Việt có dấu;
   - CD-023: một màn một lượt; sao chép từ dự án khác; Lưu làm mẫu;
   - CD-024: BG-25…BG-28, VAT cọc dồn đợt kế.
2. **Câu lỗi "chỉ gồm chữ/số/_ . -"**: liệt kê **mọi** chỗ áp quy tắc này lên ô người dùng gõ (cả ngoài màn Dự án), đề xuất chuyển sang mã nội bộ máy sinh.
3. **Dữ liệu:** schema hiện tại có đủ không (tiến độ %, mốc, mẫu dự án, sao chép, nhật ký "cũ → mới")? Thiếu gì → đề xuất migration append (QD-09: thêm dòng, không tạo bảng/cột theo lần). Mẫu dự án dùng cơ chế "Lưu làm mẫu", **không** gắn cứng nội dung mẫu.
4. **Tính VAT cọc (BG-27):** viết công thức + ví dụ kiểm (1.000.000.000 VND trước VAT, 10%, 10/30/60% → 100.000.000 · 340.000.000 · 660.000.000; Σ 1.100.000.000), làm tròn dồn đợt cuối, phần không chịu thuế; chỗ đặt hàm tính (Python/SQL) để Báo giá, bản in, chuyển Soạn hợp đồng dùng chung một chỗ (CD-019 một engine).
5. **Chia lát** — mỗi lát ≤ 3 tệp kể cả test; ghi rõ tệp dùng chung (`crm_g.js`, `crm_g.py`, `server.py`, `pg_migrations.py`); thứ tự; lát nào backend trước UI.
6. **Kịch bản Anh thử** trên DEMO 8798 cho mỗi CD (bước bấm cụ thể, như "Báo Anh khi" trong CD), và chỉ số đo CD-023 mục 5 (số lần bấm/số hộp thoại trước–sau).
7. **"Cần lead"** — chỉ những gì thật sự chưa rõ sau khi đọc CD.

Tối đa khoảng 4 trang. Không in dữ liệu thật.

## MTQ-4f2 · M4 · Nghiệm thu & chi phí dự án — SQL review 02A / chứng từ 02B theo ma trận (KK-MTQ4-M4 §2–§3 dòng 4f2)

**Nhánh:** dựng từ `hop-nhat-20261023` (đã có M0055 lệnh hồ sơ, M0061 đọc/master, M0058 `mtq_duoc_doc`, M0057 cổng tập PN).

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\giao-mtq4-chung.md` (PN tắt giữ CU từng bit; PN bật chỉ theo ma trận; không `cũ OR mới`);
- `KK-MTQ4-M4.md` §1–§3 (dòng `sql_review.py:489,192,215,232,268,321`, `xay_dung.py:978…`; M20 `review_quyen`, `review_kiem/tra/giu/tao_run/cong_bo/ghi_map/ghep`; M22 chứng từ tương ứng);
- mẫu đã làm: `m4/sql_mtq.py` (`MTQ_M4_A_SQL`, `MTQ_M4_B_SQL`).

**Tệp (3):** `m4/sql_mtq.py` (thêm hằng `MTQ_M4_C_SQL`, không đổi hằng cũ); `ha_tang/pg_migrations.py` (`M00xx_MTQ_M4_C`, dấu `# MTQ-4f2 — CD-012:`); `tests/test_mtq_m4_review_sql.py` mới.

**Việc:**
- Khi PN bật, các lệnh review 02A và chứng từ 02B kiểm cổng phiên theo **đúng ô** `M4:02A_REVIEW:{XEM,SUA,KIEM}`, `M4:02B_*` (KK §2):
  - chạy / chạy lại → KIEM;
  - ghép / ghi map → SUA;
  - công bố → KIEM;
  - đọc kết quả → XEM.
- **Kiểm trước** replay / run / công bố. Thân hàm lấy **bản mới nhất theo thứ tự migration**.
- Giữ trạng thái `CANCELLED` nội bộ và đường lưu bằng chứng sau thu hồi (không biến thành lệnh nghiệp vụ thành công).
- Giữ ràng buộc "đợt đã nộp" như 4f1c.
- PN tắt: đường cũ từng bit (oracle).
- Thông báo từ chối tiếng Việt, không lộ khóa.

**Test (PG, vai ứng dụng):**
- oracle PN tắt cho từng lệnh;
- PN bật: có/không ô đúng từng lệnh;
- replay sau thu hồi bị chặn;
- CANCELLED giữ;
- PN A bật không đổi PN B.

**Báo cáo (≤ ⅓ trang) mỗi lát**, "Cần lead", thông điệp commit `[KK-UI-DA-BG] …` / `[MTQ-4f2] …`.
