**Lead (Claude) quyết sau review BO-1a (26/10 ~23:10) — làm theo, không hỏi lại:**

`m4.boq_hieu_luc` phải theo **đúng** ngữ nghĩa projection bản chép Review đang chạy: `src/kho_tri_thuc/m4/review_phu_luc_pg.py` hàm `boq_tai_ngay`, khoảng dòng 115–148.
1. Phụ lục áp dụng: `DA_KY`, không `DA_HUY`, `ngay_hieu_luc <= ngày`; thứ tự ngày hiệu lực rồi lần (giữ như hiện tại).
2. Trong từng phụ lục:
   - `THEM` chỉ khi `ma_hm` **chưa** hiệu lực → thêm;
   - `THAY` chỉ khi `ma_hm` **đang** hiệu lực → chỉ ghi đè các trường **có giá trị** (không rỗng/NULL), giữ các trường khác của dòng đang hiệu lực, cập nhật nguồn truy vết;
   - `BO` chỉ khi **đang** hiệu lực → loại;
   - trùng `ma_hm` trong cùng phụ lục → lý do "trùng mã hạng mục".
3. Thao tác không khớp trạng thái (THEM mã đã có, THAY/BO mã chưa có), hoặc dòng BOQ thiếu phụ lục nguồn → **không** RAISE.
   - Trả kết quả "cần xem lại" kèm danh sách lý do tiếng Việt (ví dụ "Phụ lục <số>: thao tác BOQ không khớp hạng mục đang hiệu lực.");
   - khi có lý do thì **không** trả tập dòng (giống `boq: None`).
   - Hàm đọc không làm vỡ màn hình vì dữ liệu nguồn sai.
4. Dạng trả: `RETURNS jsonb` = `{"boq": [ {...dòng + nguồn truy vết...} ] | null, "can_xem_lai": bool, "ly_do": [...]}`, cùng dạng projection Review để lát sau thống nhất đọc typed/chép (BO-3). Giữ `STABLE SECURITY INVOKER`, ACL như hiện tại. Tiền/khối lượng giữ `text` nguyên.
5. Test:
   - ca review nêu (gốc không có B → PL1 THEM B → PL2 THAY B → hủy PL1) → `can_xem_lai` true, `boq` null;
   - THAY chỉ ghi đè trường có giá trị;
   - trùng mã trong một phụ lục;
   - các ca cũ chỉnh theo dạng trả mới.
