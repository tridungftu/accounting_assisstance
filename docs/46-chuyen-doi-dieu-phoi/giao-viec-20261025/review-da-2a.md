# REVIEW DA-2a (CRM · màn Dự án đang bán — phần xem) · vòng 1/2 · reviewer Claude (chỉ đọc)

Bạn là reviewer chéo cho code Codex viết. **Chỉ đọc**: không sửa tệp, không commit. Worktree `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\.claude\worktrees\lat-da-2`, nhánh `lat/da-2`, commit `b339029`; diff lát: `git -C <worktree> show b339029` — `src/kho_tri_thuc/giao_dien/assets/crm_g.js`, `assets/style.css`, `tests/crm_du_an_ban_async.cjs` (mới). Được chạy: `node tests/crm_du_an_ban_async.cjs`, `node tests/crm_giao_ket_async.cjs` (trong worktree).

**Căn cứ:** `docs/46-chuyen-doi-dieu-phoi/THIET-KE-DU-AN-DANG-BAN.md` (checklist cổng B 1–8); hợp đồng dữ liệu máy chủ trong `src/kho_tri_thuc/giao_dien/crm_g.py` khối `_dieu_huong_da` và `src/kho_tri_thuc/k2/crm_du_an_ban.py`; quy tắc giao diện `CLAUDE.md` §4 (tiếng Việt nghiệp vụ, không mã kỹ thuật, ngày dd/mm/yyyy, tiền có đơn vị). Thuế sẽ đổi theo QD-20261025-20 (lát DA-1c) — chỉ ghi nhận chỗ màn hình đang đọc `co_so_thue`/`vat_phan_tram` để lát sau sửa.

**Kiểm 5 việc, Đạt/Không:**
1. **An toàn DOM:** mọi chuỗi máy chủ/người dùng chèn qua `textContent`/escape; không `innerHTML` với dữ liệu; không URL ngoài.
2. **Đúng dữ liệu:** hiện đúng số/chuỗi máy chủ trả (đơn giá hiển thị, mức phí, diện tích), không tự tính tiền; chọn phiên bản cũ gọi đúng `?phien_ban=`; phản hồi trễ của lần bấm trước không ghi đè lần bấm sau.
3. **Tiếng Việt nghiệp vụ:** không hiện uuid/id/mã enum (`M2_THANG`, `CON_TRONG`…) — dùng nhãn `danh_muc`; ngày dd/mm/yyyy; tiền/diện tích có đơn vị.
4. **Không phá màn Báo giá/G1/G7:** phần thêm là khối riêng, dùng lại helper sẵn có (không viết trùng); `crm_giao_ket_async.cjs` 23/23 nhóm vẫn đạt.
5. **Test:** 13 nhóm ca có nghĩa (không test rỗng), gồm HTML nguyên văn, mã kỹ thuật, phiên bản cũ, phản hồi trễ.

**Báo cáo cuối (≤ ½ trang, tiếng Việt, ≤ 8 điểm):**
```
REVIEW DA-2a · vòng 1/2 · Claude
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
