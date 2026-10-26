**Trả lời lead (Claude) cho MTQ-4i-b1 — làm theo, không hỏi lại (26/10 ~23:20):**

1. **Cổng tiêu thụ phạm vi NGUON** (trong lát này, cùng tệp `k2/sql_mtq_cong.py`):
   - Phần tử của `mtq_giai_doi_tuong_tap` có thêm trường tùy chọn `nguon_khoa`. Đó là khóa phạm vi NGUON theo A1/M0049 (`LOAI|profile/instance|công ty/kho`), resolver rS/rA điền từ CSDL.
   - `CREATE OR REPLACE` **hai cổng phiên** từ thân **M0057**. Thêm điều kiện chọn phạm vi `(s.loai = 'NGUON' AND s.khoa = nguon_khoa)`, ưu tiên **trước** `PHAP_NHAN` (hẹp trước rộng).
   - Mọi nhánh khác giữ nguyên từng bit. Phần tử không có `nguon_khoa` → hành vi cũ.
   - Nhiều PN: mỗi PN có `nguon_khoa` của mình (có thể trùng khóa), kiểm từng PN như M0057.
2. **Đổi đích ánh xạ (retarget):**
   - rA giải **PN hiện tại** của ánh xạ (`master.anh_xa_nguon` dòng hiện hành) — tập PN cũ.
   - **PN mới** được kiểm bằng **một lần gọi cổng thứ hai** với đối tượng `{"bang":"master.phap_nhan","id":<PN đích>}` cho cùng khóa hành động. Thêm cặp whitelist (`master.phap_nhan`, khóa DUYET ánh xạ HĐ/Kho) theo KK-MTQ4-LIEN-MODULE §2 nếu chưa có.
   - Cả hai lần phải cho. Bên ghi gọi hai lần ở lát 4i-d, không phải lát này.
   - Cổng vẫn **không** nhận PN từ tham số; PN đích là đối tượng được kiểm quyền.
3. `mtq_duoc_doc` (chỉ đọc) tiêu thụ NGUON: lát sau **NEN-2c**, không làm ở đây.
4. Tệp 3: `k2/sql_mtq_cong.py` (`MTQ_CONG_H_SQL`), `ha_tang/pg_migrations.py` (`M00xx_MTQ_CONG_H`), `tests/test_mtq_lmod_resolver_sql.py`. Test thêm:
   - oracle một PN không đổi so với M0057 cho đối tượng cũ;
   - quyền chỉ có phạm vi NGUON đúng khóa → cho; khóa khác → chặn;
   - nguồn gộp hai PN cùng bật đủ/ thiếu một PN;
   - hỗn hợp → `MTQ_PN_HON_HOP`;
   - đối tượng `master.phap_nhan` cho khóa ánh xạ.
