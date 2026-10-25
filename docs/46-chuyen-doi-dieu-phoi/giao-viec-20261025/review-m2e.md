# REVIEW M2e · vòng 1/2 · reviewer Codex (chỉ đọc)

Bạn là reviewer chéo, chạy không tương tác (`codex exec`, sandbox chỉ đọc). Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8. Nếu cần chạy thử dùng `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"` (thiếu psycopg là bình thường — kiểm tĩnh/test không cần CSDL).

**Đối tượng:** nhánh `lat/m2e` (worktree hiện tại), đầu `80a31db`; so với hop-nhat: `git diff hop-nhat-20261023...lat/m2e`. 7 tệp: `src/kho_tri_thuc/giao_dien/m2_tai_hoa_don.py` (mới, route `/api/m2/tai-hoa-don*`), `giao_dien/assets/m2_tai_hoa_don.js` (mới), `giao_dien/assets/index.html`, `giao_dien/server.py`, `ha_tang/config.py` (mục `[tai_hoa_don]`), `tests/test_m2_00e_http.py`, `tests/m2_00e_giao_dien_async.cjs`.
**Căn cứ:** `D:\Claude\Phan mem ho tro ke toan\THIET-KE-MODULE-DE-CHOT-2026-10-20\M2-00-NHAN-NGUON-TU-CONG-THUE.md` §2–§3 (luồng màn hình, quyền K5: chỉ pháp nhân có quyền, mật khẩu không bao giờ hiện), §8 ca M2-00-01/-05/-08. Lớp dùng lại (không được sửa): `src/kho_tri_thuc/m2/tai_hoa_don/*` (`dieu_phoi.py` điều phối theo phiên + quyền hiện hành).

**Kiểm 4 việc, Đạt/Không — trọng tâm AN TOÀN:**
1. **Quyền & lộ dữ liệu:** mọi route kiểm phiên + quyền hiện hành qua `dieu_phoi` (không route nào bỏ qua); danh sách cho phép trường phản hồi; không lộ mật khẩu, token, nonce, capability, đường dẫn profile `.env`; "mở thư mục"/"xem manifest" không cho đọc tệp tùy ý ngoài thư mục tải/gốc tin cậy (thử đường dẫn `..`, tuyệt đối, UNC trong tham số); SSE/log đã che `khóa=giá trị`, bearer, JWT. Mọi tham số từ client được kiểm kiểu/độ dài.
2. **Đường nhận:** gọi `lap_ke_hoach_nhan`/`nhan_vao_k2` có truyền `goc_hoi_cuu_tin_cay` từ cấu hình; không gọi cổng thuế/bộ tải thật trong test; cấu hình vắng → "chưa cấu hình", không lỗi.
3. **Không sửa lớp dùng lại; `server.py`** chỉ thêm đăng ký + allowlist asset (đúng chỗ, không đổi hành vi route khác); lớp con `DieuPhoiApp` gán `_khoa` của điều phối bằng khóa chung của app — đánh giá rủi ro (chặn route khác lâu? deadlock?).
4. **Test & phạm vi:** `python -X utf8 -m unittest tests.test_m2_00e_http` (PYTHONPATH=src) nếu chạy được; diff đúng 7 tệp; không dữ liệu thật; không xóa tệp.

**Báo cáo cuối (≤ 1 trang, tiếng Việt, ≤ 10 điểm):**
```
REVIEW M2e · vòng 1/2 · Codex
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
"Chặn" khi có route bỏ qua quyền, lộ mật khẩu/token, đọc được tệp ngoài phạm vi, có đường gọi cổng thuế thật, hoặc vi phạm ràng buộc cứng.
