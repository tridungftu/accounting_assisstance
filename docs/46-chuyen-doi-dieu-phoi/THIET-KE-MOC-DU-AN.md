# Thiết kế lát — Mốc thanh toán theo dự án (CD-006 mục 2–4, CD-007)

Lead soạn 25/10/2026 23:20 cho chạy đêm CD-008. Căn cứ: hộp thư CD-006, CD-007; TL 45 §7 mục 4–5 và §8 BG-23; mã hiện có `k2/sql_crm_du_an_ban.py` (M0031, mẫu lô/căn `crm_da_ban_lo` + `_lo_ls`), `k2/crm_du_an_ban.py`, `k2/crm_giao_ket.py` (`danh_muc_moc_chuan`, `nhan_moc_su_kien`), `giao_dien/khung_khai_bao.py` (số việc trên icon, TL 49).
Các điểm **[Mặc định lead]** là lựa chọn của lead khi Anh vắng (CD-008: không chờ) — ghi vào báo cáo đêm mục "Cần Anh" để Anh xác nhận; đổi được mà không đổi dữ liệu đã có.

## 1. Nghiệp vụ

- Mỗi **dự án đang bán** tự khai danh sách **mốc riêng** (vd "Xong chứng nhận đầu tư"). Dự án chưa khai → chỉ có **mốc cơ bản** (Ký · Bàn giao · Sổ · Sau ký + n ngày · Xây xong tầng n · ngày cố định). Không thêm mốc riêng vào danh mục chung.
- Mốc riêng có: **tên** (bắt buộc, ≤ 120 ký tự, không trùng tên mốc đang dùng khác của cùng dự án — so không phân biệt hoa thường/dấu), **tên tắt** (tùy chọn, ≤ 20, vd "CNĐT"), **ngày dự kiến** (bắt buộc khi khai), **ngày thực tế** (ghi khi xảy ra), **đang dùng** (bỏ dùng = ngừng, không xóa).
- **Phiên bản + nhật ký** như lô/căn: mỗi thay đổi = dòng lịch sử mới (`lan` + 1), dòng cũ đóng hiệu lực một lần; nhật ký `nhat_ky.su_kien` ghi cũ → mới, ai, lúc nào, lý do. Lệnh sửa cần `expected_lan` = lần hiện hành (khác → xung đột 409).
- **Chỉnh ngày dự kiến bắt buộc lý do.** Đổi ngày thực tế đã ghi cũng bắt buộc lý do. Ngày thực tế không được sau hôm nay (ngày máy chủ `master.ktt_ngay()`).
- **Trạng thái mốc** (tính khi đọc, theo ngày máy chủ): `DA_XONG` (có ngày thực tế) · `CHUA_DEN` (dự kiến ≥ hôm nay) · `QUA_DU_KIEN` (dự kiến < hôm nay, chưa có thực tế).
- **Việc chờ:** mỗi mốc `QUA_DU_KIEN` = đúng **1 việc chờ** "Chỉnh ngày dự kiến mốc …" — tính khi đọc (không lưu bảng việc, không cần tác vụ nền); hết khi chỉnh ngày dự kiến ≥ hôm nay hoặc ghi ngày thực tế. Đếm vào số trên icon phần **Dự án đang bán** của lưới CRM (TL 49). **[Mặc định lead]** "người phụ trách dự án" = người có quyền ghi dự án đang bán (Bán hàng / Kế toán / Kế toán trưởng có module CRM trên pháp nhân dự án) — số việc hiện cho vai **Bán hàng**; chưa có trường "phụ trách" riêng cho từng dự án.
- **Mã sự kiện** dùng ở lịch thanh toán: `DAM-<uuid mốc>` (đúng ngày mốc) và `DAM-<uuid mốc>_<n>` (mốc + n ngày, n 1–3650) — khớp `RE_MA` hiện có (`[A-Za-z0-9_.-]{1,80}`), ổn định qua đổi tên. Nhãn hiển thị luôn lấy tên mốc hiện hành; mã không bao giờ hiện cho người dùng.
- **Hạn của đợt gắn mốc riêng** (Lịch nghĩa vụ, Danh sách hợp đồng cột Đợt kế tiếp, Báo giá): có ngày thực tế → **hạn = ngày thực tế (+ n)** → đếm đến hạn/quá hạn như đợt ngày cố định; chưa có → hiện **"dự kiến dd/mm/yyyy"** (= dự kiến + n), **không đếm quá hạn**.

## 2. Gõ mốc ở Báo giá (CD-006 mục 3, BG-23)

- Danh sách mốc của ô Mốc = mốc cơ bản + mốc riêng của **dự án đã chọn** (`GET /api/crm/bao-gia/moc-chuan?du_an_id=<uuid>`; không có dự án → chỉ mốc cơ bản).
- Khớp khi gõ (không dấu, không phân biệt hoa thường, `đ`→`d`): đúng tên; đúng tên tắt; **chữ cái đầu** của tên hoặc của một dãy ≥ 2 từ liền nhau trong tên (vd `cndt`/`CNĐT` → "Xong chứng nhận đầu tư"); "<tên> + n ngày". Khớp > 1 mốc → báo lỗi kèm danh sách các mốc khớp để bấm chọn. Không khớp → lỗi BG-23 kèm danh sách bấm chọn.
- Máy chủ kiểm khi lưu báo giá: mã `DAM-…` phải thuộc đúng dự án của báo giá và đang dùng; sai → lỗi theo trường dòng lịch.

## 3. Lát (≤ 3 tệp mỗi lát, CD-004)

| Lát | Nội dung | Tệp | Nền |
|---|---|---|---|
| MDA-1a | Bảng + hàm SQL + migration kế tiếp + test PostgreSQL | `k2/sql_crm_du_an_moc.py` (mới), `ha_tang/pg_migrations.py`, `tests/test_crm_du_an_moc_pg.py` (mới) | hop-nhat + da-2 |
| MDA-1b | Dịch vụ + HTTP (đọc danh sách mốc, ghi mốc, danh mục mốc theo dự án) + test | `k2/crm_du_an_ban.py`, `giao_dien/crm_g.py`, `tests/test_crm_du_an_moc.py` (mới) | MDA-1a |
| MDA-2 | Màn Dự án đang bán: mục "Mốc thanh toán của dự án" (danh sách, khai, chỉnh dự kiến có lý do, ghi thực tế, lịch sử) | `crm_g.js`, `style.css`, `tests/crm_du_an_ban_async.cjs` | dòng giao diện (sau BG-e3, DA-4) |
| MDA-3 | Báo giá: danh mục mốc theo dự án + khớp tên tắt/chữ đầu; máy chủ kiểm mã `DAM-…` khi lưu | `crm_g.js`, `tests/crm_giao_ket_async.cjs` / `k2/crm_giao_ket.py`, `tests/test_crm_giao_ket*.py` | MDA-1b + MDA-2 |
| MDA-4 | Hạn đợt gắn mốc ở Lịch nghĩa vụ / Danh sách hợp đồng ("dự kiến …", không đếm quá hạn) + số việc chờ trên icon | `k2/crm_s1.py` (+ SQL đọc), `giao_dien/khung_khai_bao.py`, test | MDA-1b |
| DA-4 | Lưới CRM thêm phần thứ 7 **"Dự án đang bán"** (`#crm/du-an-ban` mở thẳng màn đang có) | `khung_khai_bao.py`, `app.js`, `crm_g.js` | dòng giao diện |

DEMO: seed khai mốc "Xong chứng nhận đầu tư" (tên tắt "CNĐT", ngày dự kiến = hôm nay + 30, chưa có thực tế) cho dự án KCN DEMO (`DA_KCN_DEMO`) — trong MDA-1b (`khoi_tao_demo`).
