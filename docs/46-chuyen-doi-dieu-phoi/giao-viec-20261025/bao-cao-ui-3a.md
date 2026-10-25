Anh, đã xong UI-3a trong **3 file**, chưa commit/gộp.

- [khung_khai_bao.py:78](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-ui-3a/src/kho_tri_thuc/giao_dien/khung_khai_bao.py:78>): khai báo module, lọc quyền, cộng số CRM, fallback CSDL.
- [crm_g.py:141](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-ui-3a/src/kho_tri_thuc/giao_dien/crm_g.py:141>): đăng ký route GET.
- [test_khung_he_thong.py:42](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-ui-3a/tests/test_khung_he_thong.py:42>): thêm 15 test.

**Module/hash:** Nhập `#nhap`; CRM `#crm`; M2 `#hoadonmua`; M4 `#nghiemthu`; Cổng M4 `#m4`; M5 `#phieukho`; L11 `#lienketsoluong`; M9 `#khoanvay` (tạm dừng); Hồ sơ `#hoso`; Mẫu `#mau`; Khả năng `#khanang`; Hướng dẫn `#huongdan`.

**Test:** trước **26/26**, sau **41/41**, không lỗi mới trong bộ đã chạy. UTF-8 không BOM; `git diff --check` đạt. Icon mới: **không**.

**Cần Anh:** tạm chọn 4 mục khả dụng đầu sau lọc quyền; giữ hai trang M4 riêng. Các trang `nhap/nghiemthu/hoso/mau/khanang/huongdan` chưa có nguồn quyền rõ, hiện cho mọi phiên đăng nhập. Khi mất CSDL, CRM hiện không số; module K2 khác chưa kiểm được quyền sẽ ẩn.

Commit đề xuất: `[UI-3a] Khai báo module và API trang chủ hệ thống theo quyền`.