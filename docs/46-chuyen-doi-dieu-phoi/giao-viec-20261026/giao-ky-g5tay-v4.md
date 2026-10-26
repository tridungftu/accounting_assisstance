# KY-G5TAY vòng 4 — sửa ca test p03 dùng login không có trong seed DEMO (chỉ sửa test)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.** UTF-8 không BOM. Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL. Không xóa file. Worktree hiện tại, nhánh `lat/ky-g5tay` (2163fe1).
**PG lead 26/10 10:41:** mọi ca đạt (p01 kiểm tay → G6 → Hiệu lực, p07, `test_crm_ky_docx` 11/11) trừ `test_crm_g5_tay.G5TayPg.test_p03_vai_ban_hang_ngoai_pn_va_thu_hoi_truoc_replay`:
```
tests/test_crm_g5_tay.py:258  self.assertIn(self.xac_nhan(d, login)[0], (403, 404))
tests/test_crm_g5_tay.py:206  return self.goi(ROUTE, body, self.sid(login))[:2]
tests/test_crm_giao_ket_http.py:174  sid = ck.split(";", 1)[0].split("=", 1)[1]   → AttributeError: 'NoneType' object has no attribute 'split'
```
→ `sid(login)` không nhận được cookie: login ca p03 dùng **không có trong seed DEMO** (hoặc không đổi phiên được). **Việc:** trong `tests/test_crm_g5_tay.py` dùng đúng login DEMO có sẵn cho các vai cần thử (bán hàng cùng pháp nhân, kế toán khác pháp nhân… — xem danh sách người mô phỏng trong `src/kho_tri_thuc/k2/crm_demo.py`, `k2/crm_g_demo.py`, `k2/crm_kiem_demo.py` hoặc cách các ca khác trong tệp chọn login); nếu thật cần vai không tồn tại thì tạo người mô phỏng tạm **trong CSDL test** theo cách test G5/G6 khác đang làm. Không đổi mã sản phẩm, không nới kiểm (vẫn đòi 403/404 cho vai không quyền).
**Chạy (thuần):** `python -X utf8 -m unittest tests.test_crm_g5_tay` (PYTHONPATH=`src;.;tests`). **Báo cáo (≤ 5 dòng)**, thông điệp commit `[KY-G5TAY] vòng 4: …`.
