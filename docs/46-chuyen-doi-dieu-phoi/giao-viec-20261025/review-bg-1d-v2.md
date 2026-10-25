# REVIEW BG-1b + BG-1d (màn Báo giá) · vòng 2/2 · reviewer Codex (chỉ đọc)

Bạn là reviewer chéo, chạy không tương tác (`codex exec`, sandbox chỉ đọc). Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8. Có thể chạy `node tests/crm_giao_ket_async.cjs` (không ghi tệp).

**Đối tượng:** worktree hiện tại, nhánh `lat/bg-1d`. Vòng 2 = commit `f904fcc` trên `efa74b9`: `git diff efa74b9 f904fcc` (`assets/crm_g.js`, `assets/style.css`, `tests/crm_giao_ket_async.cjs`, `CHANGELOG.md`). Toàn bộ lát: `git diff hop-nhat-20261023...lat/bg-1d`.
**Vòng 1 của bạn (nguyên văn):** `C:\Users\Admin\AppData\Local\Temp\claude\D--Claude-Phan-mem-ho-tro-ke-toan-Ph-n-m-m-kho-tri-th-c\c7ce96c2-538a-4331-bac6-4382c44a8688\scratchpad\bao-cao-review-bg-1d.md` — 3 Chặn (Chuyển ở bản thiếu `ly_do_chan_chuyen`; nạp G7 so sai tiền tệ → 100 USD thành 100 VND; xóa tỷ giá làm xem trước ≠ Lưu) + 2 Nên sửa (ngày dd/mm/yyyy, tên kỹ thuật; test A8/A14).
**Lead thêm ở vòng 2:** (4) dòng "Tỷ giá USD mặc định" cho mọi vai, nút Sửa theo `duoc_sua` của máy chủ, lý do bắt buộc, `POST /api/crm/bao-gia/ty-gia-mac-dinh {ty_gia, ly_do}`; (5) thông báo lỗi tải cũ tự xóa khi tải thành công.
**Worker tự khai giới hạn:** sau khi lưu tỷ giá mặc định tường minh, máy chủ ghi là tỷ giá "nhập" → mở lại nhãn "đã sửa 26.000" (số đúng); tên người lập giữ tên đăng nhập vì máy chủ không trả tên hiển thị.

**Kiểm, Đạt/Không:**
1. Ba điểm Chặn vòng 1 đã hết (tự tái hiện lại như vòng 1, kể cả bằng harness trong bộ nhớ).
2. Phần mới (4), (5): chèn DOM an toàn (textContent/escape), không lộ mã kỹ thuật, lỗi máy chủ hiện tiếng Việt; không tự gửi POST khi chưa bấm; số gửi đi là chuỗi, không float.
3. Phần sửa không tạo lỗi mới: tiền hiện = số máy chủ trả; luồng 2 bước; báo giá cũ mở được; vòng thử lại tỷ giá mặc định (3 lần/5 giây) không lặp vô hạn, không gửi Lưu khi chưa có tỷ giá.
4. Test A8 viết lại, A15 mới bắt đúng các lỗi vòng 1 (gỡ sửa thì ca đỏ); `node tests/crm_giao_ket_async.cjs` đạt.

**Báo cáo cuối (≤ 1 trang, tiếng Việt, ≤ 8 điểm):**
```
REVIEW BG-1b+1d · vòng 2/2 · Codex
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
Đây là vòng cuối: chỉ nêu "Chặn" khi thật sự sai tiền, Chuyển/In không bị chặn đúng, chèn DOM không an toàn, hoặc vi phạm ràng buộc cứng; còn lại ghi "Để sau".
