# review-lat UI-2 (vòng 1/2, CHỈ ĐỌC) — máy chủ khung lưới icon CRM

Lát Codex: nhánh `lat/ui-2`, commit `95ef025` (`git show 95ef025`). Handoff `giao-viec-20261025/giao-ui-2.md`; báo cáo `bao-cao-ui-2.md`; hợp đồng dữ liệu `docs/46-chuyen-doi-dieu-phoi/HOP-DONG-DU-LIEU-KHUNG-LUOI.md`; căn cứ TL 49 `D:\Claude\Phan mem ho tro ke toan\49-trang-chu-luoi-icon.md` §1–§3, TL 42 §1 (ma trận vai) `D:\Claude\Phan mem ho tro ke toan\42-man-hinh-crm-ke-toan-va-giao-ket.md`; `docs/QUYET-DINH.md` QD-20261025-15, -22 (quyền xem tiền). Đã qua `kiem-nhanh` (Đạt 5/5). Test lead chạy có PostgreSQL: test mới 16/16; `test_crm_*` không thêm mã lỗi so với nền.

Kiểm thêm:
1. **Quyền ở máy chủ:** phần/thẻ lọc theo vai + module ngay tại máy chủ; người không có module CRM → `khong_quyen`; không thẻ/số nào lộ ngoài vai; người không có quyền xem tiền không suy ra được tiền hay đợt thu qua số đếm (QD-15/22).
2. **Số trên thẻ = số danh sách:** mỗi `loc` gọi đúng danh sách cho ra cùng con số (cùng service, cùng phạm vi); thẻ nguồn chưa có thì bỏ, không bịa.
3. **Thay đổi hành vi route cũ:** `crm_g.py` nay chuyển `GET /api/crm/bao-gia` và `/api/crm/mau` có tham số `trang_thai` sang khung (trước đây bỏ qua tham số; nay giá trị lạ → 400). Có phá màn/test nào đang gọi kèm `trang_thai` không (grep `crm_g.js`, `app.js`, tests)? Có lọc đúng phạm vi như route gốc không?
4. Lỗi CSDL → 503 có cấu trúc; không trả mã kỹ thuật trong `ten`/`nhan`; hiệu năng: không quét toàn bộ dữ liệu cho mỗi lần làm mới 60 giây (báo giá chạm 200 dòng → không trả tổng cắt).

Kết luận Đạt / Không đạt; ≤ 10 điểm, mức **Chặn / Nên sửa / Để sau**, tệp:dòng, tiếng Việt, ≤ 1 trang.
