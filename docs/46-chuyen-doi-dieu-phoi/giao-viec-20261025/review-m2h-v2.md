# REVIEW M2h vòng 2/2 ("Tải tất cả công ty") · reviewer Claude (chỉ đọc)

Bạn là reviewer chéo cho bản sửa do Codex viết. **Chỉ đọc**: không sửa tệp, không commit, không mở server, không gọi mạng/cổng thuế. Worktree `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\.claude\worktrees\lat-m2h`, nhánh `lat/m2h`; vòng 2 = commit HEAD (`git -C <worktree> show HEAD`), toàn lát `git -C <worktree> diff hop-nhat-20261023...lat/m2h`. Được chạy: `node tests/m2_tai_tat_ca.cjs`; `python -X utf8 tools\chay_test_theo_module.py . --runtime "D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\var\web\crm-demo\runtime.local.json" --module test_m2_tai_tat_ca`.

**Vòng 1 (review Claude):** (1) **Chặn** — vòng chờ job không có hạn, nhánh `except Exception` return mà `dang_chay` vẫn True → kẹt 409 tới khi khởi động lại máy chủ, không có hủy; (2) cờ `_dang_chay` cũ chặn "Tải tất cả" dù bộ tải rảnh; (3) `trang_thai_hang_doi` gọi `profiles()` (DB + RPC 15 giây) trong khóa hàng đợi; (4) JS poll vô hạn khi 400/503; (5) thiếu hộp xác nhận/hủy.

**Kiểm, Đạt/Không:**
1. Chặn #1 hết: mọi đường thoát của luồng nền (xong, lỗi, quá hạn, ngoại lệ bất kỳ, hủy) đều mở khóa (`finally`) và dừng bộ tải khi cần; quá hạn dùng `cho_moi_job_s`; hủy chỉ chủ hàng đợi, người khác 403; không còn trạng thái kẹt.
2. Không thêm race mới: hai request đồng thời, tải lẻ chen ngang, hủy trong lúc chuyển sang công ty kế; khóa nhất quán thứ tự, không deadlock; không giữ `mutation_lock` lâu.
3. (2), (3), (4), (5) đã sửa đúng ý; DOM vẫn an toàn (textContent).
4. Test mới có nghĩa (job treo, ngoại lệ, hủy/403, cờ cũ, poll dừng).

**Báo cáo cuối (≤ ½ trang, tiếng Việt, ≤ 6 điểm):**
```
REVIEW M2h · vòng 2/2 · Claude
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
Vòng cuối: chỉ "Chặn" khi còn kẹt khóa/chồng job/gọi thật.
