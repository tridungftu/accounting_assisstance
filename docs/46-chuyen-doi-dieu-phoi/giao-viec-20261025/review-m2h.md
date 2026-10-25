# REVIEW M2h (M2-00 · "Tải tất cả công ty") · vòng 1/2 · reviewer Claude (chỉ đọc)

Bạn là reviewer chéo cho code Codex viết. **Chỉ đọc**: không sửa tệp, không commit. Worktree `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\.claude\worktrees\lat-m2h`, nhánh `lat/m2h`; diff `git -C <worktree> show HEAD` — `src/kho_tri_thuc/giao_dien/m2_tai_hoa_don.py`, `assets/m2_tai_hoa_don.js`, `tests/test_m2_tai_tat_ca.py`, `tests/m2_tai_tat_ca.cjs`. Được chạy: `node tests/m2_tai_tat_ca.cjs`; Python test thuần (`python -X utf8 tools\chay_test_theo_module.py . --runtime "D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\var\web\crm-demo\runtime.local.json" --module test_m2_tai_tat_ca`, chạy nền nếu > 1 phút).

**Căn cứ:** `D:\Claude\Phan mem ho tro ke toan\43-M2-00-nhan-nguon-tu-cong-thue.md` dòng ~43, ~60, ~144 (ca M2-00-02: hai pháp nhân, hai profile, đúng tài khoản/thư mục/hồ sơ; "Tải tất cả" tuần tự, không chồng job). Ràng buộc cứng: **không gọi cổng thuế thật**, không đọc `.env`.

**Kiểm 5 việc, Đạt/Không:**
1. **Đồng thời:** hàng đợi thật sự tuần tự (một job một lúc) dưới mọi đường: hai request "tải tất cả" gần như đồng thời, "tải lẻ" chen ngang, job treo/không bao giờ kết thúc (có hạn chờ hay kẹt vĩnh viễn?), server dừng giữa chừng; khóa/biến trạng thái dùng chung có được bảo vệ (lock) không; luồng nền có giữ khóa chung của app (`mutation_lock`) lâu không.
2. **Quyền:** chỉ pháp nhân người bấm có quyền (cùng hàm kiểm của M2e) và có profile; kiểm lại quyền mỗi job; người khác không xem/hủy được hàng đợi của người này (hoặc nêu rõ thiết kế dùng chung).
3. **Không gọi thật:** chỉ đi qua RPC bộ tải đã có; không đường nào bật cổng thật ngoài cấu hình hiện hành.
4. **Màn hình:** chèn DOM an toàn (textContent), tên pháp nhân (không mã kỹ thuật), trạng thái tiếng Việt, lỗi hiện lý do.
5. **Test:** ca M2-00-02 có nghĩa (không chồng job đo được, đúng profile/thư mục từng pháp nhân, lỗi giữa chừng, bấm lần hai bị từ chối).

**Báo cáo cuối (≤ ½ trang, tiếng Việt, ≤ 8 điểm):**
```
REVIEW M2h · vòng 1/2 · Claude
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
