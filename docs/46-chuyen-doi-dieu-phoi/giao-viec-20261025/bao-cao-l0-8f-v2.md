Anh, đã sửa 3 file; **chưa xanh hoàn toàn** do một mock cũ cần cập nhật ngoài phạm vi cho phép.

- `tests/test_m4_02c_pg.py:148`: thêm `gan_doi_tac=None`; có giá trị thì gắn bằng actor DEMO và CAS trước trích/nộp. Mặc định giữ luồng cũ.
- `tests/test_m4_03b_common_pg.py:53,107`: truyền `KHO_M4_03B_DOI_TAC`; thiếu biến → skip `NOT_VERIFIED`.
- `tools/pg_demo_ho_03a.py:101,149`: seed MST `DEMO_M2_SUPPLIER` và mapping `PN_DEMO_A` qua bộ nhập danh mục hiện có; trả biến mới. Runner tự chuyển tiếp, không cần sửa.

**Kiểm tra:** 7/7 test thuần mới đạt; 40 ca PG skip vì không cấp clone. UTF-8 không BOM, syntax và diff-check đạt. Runner có **1 ERROR mới** tại `tests/test_chay_test_pg_demo.py:665` vì mock thiếu bước seed; lỗi timeout còn lại tái hiện trên HEAD. Tôi dừng tại ranh giới file được giao, chưa nối PG, chưa commit.

Thông điệp commit đề xuất: `[L0-8f] Gắn đối tác DEMO trước khi nộp hồ sơ test 03B`