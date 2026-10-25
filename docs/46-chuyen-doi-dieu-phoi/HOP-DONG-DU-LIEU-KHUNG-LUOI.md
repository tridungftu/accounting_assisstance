# Hợp đồng dữ liệu khung lưới icon (UI-1 ↔ UI-2) — lead chốt 25/10/2026 theo TL 49 §3 (CD-002)

Mục đích: UI-1 (giao diện, Claude) và UI-2 (máy chủ, Codex) làm song song trên cùng dạng dữ liệu. **Máy chủ quyết quyền và đếm; trình duyệt chỉ vẽ.**

## 1. Khai báo module (một chỗ, phía máy chủ)
Tệp `src/kho_tri_thuc/giao_dien/khung_khai_bao.py` (UI-2 tạo): mỗi module một mục
```python
{"ma": "crm", "ten": "CRM · Hợp đồng bán hàng", "icon": "crm", "nhom_mau": "ban_hang", "thu_tu": 20, "tam_dung": False,
 "phan": [ {"ma": "hop_dong", "ten": "Hợp đồng", "icon": "hop-dong", "nhom_mau": "ban_hang", "thu_tu": 10,
            "quyen": {"module": "CRM", "vai": ["BAN_HANG","KE_TOAN","KE_TOAN_TRUONG","CFO","XEM"]},
            "dem": "<tên hàm đếm>", "duong_dan": "#crm/hop-dong"}, … ],
 "the": {"BAN_HANG": [ {"ma": "hd_cho_ky_qua_han", "nhan": "Hợp đồng chờ ký quá hạn", "dem": "<hàm>", "giai_thich": "…",
                        "loc": {"phan": "hop_dong", "tham_so": {"the": "W2"}}, "canh_bao_khi_lon_hon": 0}, … ], "KE_TOAN": […], …}}
```
Nhóm màu cố định (TL 49 §3): `ban_hang` xanh dương · `tien` xanh ngọc · `danh_muc` xám · `bao_cao` cam · `tiep_nhan` tím · `duyet` hổ phách · `thue` đỏ rượu. Thứ tự: Tổng quan → nghiệp vụ theo luồng → danh mục/báo cáo/cài đặt cuối.

## 2. API (đọc, theo phiên + vai; lỗi tiếng Việt + mã)
`GET /api/khung/module/<ma>` →
```json
{"module": {"ma": "crm", "ten": "CRM · Hợp đồng bán hàng"},
 "the": [{"ma": "hd_cho_ky_qua_han", "nhan": "Hợp đồng chờ ký quá hạn", "so": 2, "giai_thich": "Đã quá hạn ký theo báo giá",
          "canh_bao": true, "loc": {"phan": "hop_dong", "tham_so": {"the": "W2"}}}],
 "phan": [{"ma": "hop_dong", "ten": "Hợp đồng", "icon": "hop-dong", "nhom_mau": "ban_hang", "so_viec": 3, "qua_han": true,
           "duong_dan": "#crm/hop-dong"}],
 "lam_moi_sau_giay": 60}
```
- Chỉ trả phần/thẻ người đăng nhập **được dùng** (lọc ở máy chủ); `so_viec = 0` → giao diện không hiện số; `qua_han` quyết nền đỏ/xám của số.
- **Số trên thẻ phải khớp danh sách mở ra** khi bấm (`loc` là đúng tham số của danh sách đó — vd `GET /api/crm/hop-dong?the=W2`).
- `GET /api/khung/he-thong` (UI-3): `{"module": [{"ma","ten","icon","nhom_mau","so_viec","qua_han","tam_dung","duong_dan"}], "thanh_co_dinh": [...]}`.

### 2b. Bổ sung sau UI-2 (gộp af7c389, 25/10)
- Danh sách lọc cho `loc` của thẻ: `GET /api/crm/bao-gia?trang_thai=<NHAP|…>` và `GET /api/crm/mau?trang_thai=<CHO_KIEM|CHO_CFO>` do khung xử lý (`khung_khai_bao.py`), dùng cùng service với route gốc; khác route gốc: không có `ly_do_chua_san_sang` (báo giá) và `ghi_nguon.ly_do` (mẫu); kèm `as_of` hoặc giá trị lạ → 400; người xem → 403. Gọi không có `trang_thai` → route gốc như cũ.
- Danh sách báo giá chạm 200 dòng: `day_du: false` — giao diện **không** hiện con số như tổng đủ (UI-2b sẽ trả `tong: null` khi chưa đủ).
- Số trên icon theo loại việc TL 42 §3 (UI-2b chỉnh): Bán hàng — Hợp đồng = W1 + W2, không số ở Thu tiền; Kế toán — Thu tiền = đợt đến hạn 7 ngày; CFO — Hợp đồng = HĐ chờ duyệt (`trang_thai=CHO_DUYET`).

## 3. CRM (TL 49 §2) — 6 phần
Hợp đồng · Báo giá · Mẫu hợp đồng · Tiếp nhận hợp đồng ký · Thu tiền · Báo cáo & file soát. Thẻ theo vai: Bán hàng / Kế toán / CFO / Người xem như TL 49 §2 (con số lấy từ nguồn sẵn có — thẻ W1–W5 của `GET /api/crm/hop-dong` (C3), báo giá nháp, mẫu chờ duyệt…; nguồn nào chưa có → **không hiện thẻ đó** và ghi trong báo cáo, không bịa số).

## 4. Icon
Bộ icon mã nguồn mở nhúng nội tuyến SVG (không CDN — ứng dụng chạy cục bộ), ví dụ Lucide (ISC) hoặc Tabler (MIT); ghi tên + giấy phép vào `CHANGELOG.md`. **Không dùng icon của Apple.** Hình nét trắng trên nền màu nhóm, tương phản ≥ 4,5:1.
