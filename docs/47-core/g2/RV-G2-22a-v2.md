**Biên bản review chéo G2-22a-v2 — Kết luận: Cần sửa**

Nhánh `lat/g2-22`, HEAD `527ed5e`; đối chiếu `hop-nhat-20261023...HEAD` và riêng vòng sửa `67bf132..527ed5e`.

Quy ước: `C = src/kho_tri_thuc/core`, `T = tests`.

**Ba điểm vòng 1:**

- **Reset bộ đếm: Đạt qua kiểm tĩnh.** Reset sau `_gui('nhan_accept')`, trước khi chuyển `ready`; có ca âm lỗi pipe sau readiness và lỗi xác nhận Core. Căn cứ: `C/tien_trinh.py:358–361`, `C/sql/022_vong_doi.sql:63`, `T/test_g2_21.py:440`.
- **Phiên thiếu `ten_job`: Chưa đóng an toàn**, như phát hiện dưới đây.
- **G2-16: Đạt qua kiểm tĩnh.** `_khoa()` tạo ba lần lỗi; cập nhật thế hệ 3/4, giữ các assertion về khóa sau restart, quyền Admin, CAS, audit và rollback. Căn cứ: `T/test_g2_16.py:241`, `:373`, `:385`.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Thiếu `ten_job` khiến PID gốc đã dừng bị coi là cả phiên đã dừng.** Nhánh mới trả `True` khi PID mất, được tái sử dụng hoặc cùng định danh đã terminal, nhưng không chứng minh worker trong Job đã hết. Tình huống cụ thể: Core cũ còn giữ Job, gốc đã chết nhưng worker giữ listener; Core khác đối chiếu dòng phiên cũ thiếu tên Job sẽ bỏ `giu_boi`, chuyển sổ sang `TRONG` dù worker còn sống. Vi phạm yêu cầu chỉ trả cổng sau khi chắc chắn không còn tiến trình giữ. Ngay trạng thái tại test `:773`—gốc chết, worker sống—đầu vào `ten_job=None` sẽ đi vào nhánh trả `True`. Ca thiếu tên Job hiện chỉ được kiểm sau khi worker đã dừng, nên chưa bắt lỗi này. | **Chặn** | `C/tien_trinh.py:101–112`; `T/test_g2_21.py:773`, `:783` |
| **Diff có 4 tệp, vượt whitelist ≤3.** `test_g2_16.py` phục vụ đúng yêu cầu vòng 2, nhưng danh sách tại kế hoạch vẫn chỉ gồm SQL 022, controller và test G2-21. Cần thống nhất hồ sơ phạm vi trước khi đánh dấu mục này đạt. | **Cần sửa** | `T/test_g2_16.py:241`; `docs/47-core/g2/KE-HOACH-LAT-G2-G3.md:232` |

Các mục còn lại đạt qua kiểm tĩnh: dùng lại mã hiện có; không sửa migration 016; owner, `SECURITY DEFINER`, `search_path` và ACL của hàm mới phù hợp; không thấy mở quyền rộng, SQL chéo module, DROP/xóa hoặc ghi bí mật/DSN trong diff. Các ca PG dùng login Core thật; kết nối quản trị phục vụ fixture và điều chỉnh thời gian test.

**Bằng chứng kiểm:** `git diff --check` đạt. Theo lead, PG **146/146, 0 lỗi**. Tôi không chạy lại suite; sandbox từ chối thực thi Python (`Access is denied`), nên phát hiện trên dựa vào kiểm tĩnh, chưa tái hiện bằng runtime. Không sửa tệp, đọc kho thật, tệp bí mật hay `*.local.json`.

**Hỏi Claude:** xác nhận điểm Chặn tại `C/tien_trinh.py:101–112` trước khi xử lý tiếp; đồng thời chốt ngoại lệ whitelist 4 tệp cho vòng 2.