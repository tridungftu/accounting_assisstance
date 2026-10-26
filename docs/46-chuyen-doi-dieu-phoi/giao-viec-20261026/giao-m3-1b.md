# M3-1b: M3 · Hóa đơn bán ra & doanh thu BĐS, dịch vụ ba đẳng thức hóa đơn ↔ hợp đồng (v2 §6; mô hình `THIET-KE-M3-DU-LIEU.md`)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì PENDING và ghi "Cần Anh".
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server hay PostgreSQL; test PG tự skip. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m3-1b`, dựng từ `lat/m3-1a` (đã có `k2/sql_m3.py`: `m3.hop_dong_co_so`, `m3.hoa_don_hop_dong`, `m3.policy_hinh_thuc_doanh_thu`). **Không sửa** SQL hay migration.

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\THIET-KE-M3-DU-LIEU.md` (mục ba đẳng thức).
- Thiết kế v2 §6, §10 (quy tắc 3, 7, 9).
- Hóa đơn M2: `k2/hoa_don.py` (các trường net chịu thuế / không chịu thuế / VAT / tổng).

**Việc: tệp mới `src/kho_tri_thuc/k2/m3.py`, dịch vụ chỉ đọc.**
1. Cho một hợp đồng/phiên bản, tính **ba đẳng thức**, mỗi đẳng thức trả vế trái, vế phải, chênh (= trái − phải), danh sách nguồn kèm phiên bản, và trạng thái:
   - (1) Σ tổng thanh toán các hóa đơn tiến độ đã liên kết **xác nhận** = tổng thanh toán hợp đồng. Chỉ kết luận khi có căn cứ "đã xuất đủ đợt"; chưa có thì trạng thái `CHUA_DU_DOT`.
   - (2) Σ phần không chịu thuế trên hóa đơn = giá đất được trừ theo hợp đồng.
   - (3) Σ net chịu thuế trên hóa đơn = phần chịu thuế theo hợp đồng.
2. Trạng thái: `KHOP` / `LECH` / `PENDING`.
   - `PENDING` khi cơ sở hợp đồng chưa xác nhận, có liên kết hóa đơn chỉ là ứng viên, hoặc policy #7 chưa có (đẳng thức 2 và 3).
   - **Không** kết luận khớp khi thiếu căn cứ. Số thiếu **không thành 0**.
3. **Không tự sửa** gì; không ghi CSDL; không tính lại số hóa đơn; doanh thu không lấy từ net hóa đơn.
4. Tiền dùng `Decimal`, không dung sai; mọi chênh khác 0 là `LECH`. Không trộn currency khác nhau: khác currency thì `PENDING` kèm lý do.
5. DTO cho màn hình: câu tiếng Việt, tiền có đơn vị, không mã kỹ thuật.

**Test, tệp mới `tests/test_m3_dang_thuc.py`:**
- Phần thuần (dữ liệu giả DEMO): khớp; lệch đẳng thức 2 (hóa đơn xuất sai cơ sở); thiếu xác nhận thì PENDING; ứng viên không tính; khác currency thì PENDING; số thiếu không thành 0; Decimal chính xác.
- Phần PG (`skipUnless KHO_PG_DSN_TEST`): dựng HĐ DEMO, cơ sở và hóa đơn liên kết; kiểm 3 đẳng thức đọc đúng từ bảng.
- Chạy thuần: `python -X utf8 -m unittest tests.test_m3_dang_thuc tests.test_m3_sql`, với PYTHONPATH=`src;.;tests`.

**Tệp (2):** `k2/m3.py`, `tests/test_m3_dang_thuc.py`.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[M3-1b] …`.
