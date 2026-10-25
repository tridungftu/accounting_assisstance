Anh, đã sửa B1 đúng hai file được giao:

- [crm_giao_ket.py:871](src/kho_tri_thuc/k2/crm_giao_ket.py:871): cho lưu nháp cũ cùng dự án Ngừng bán, không `lo_id`; giữ tiền/phí, ghi `khac_tieu_chuan`. Tạo mới, đổi dự án hoặc có lô vẫn bị chặn. Nạp mặc định giữ nguyên.
- [test_crm_bao_gia_mac_dinh.py:291](tests/test_crm_bao_gia_mac_dinh.py:291): thêm đủ bốn ca (a)–(d), đều đạt.

Đã chạy ba module: **60 đạt / 1 FAIL / 18 skip**. FAIL mới duy nhất là `test_crm_ky_ket.PrefixVaPhamVi.test_crm_giao_ket_nguyen_byte`, do hash nguồn thay đổi. Lead cần cập nhật hash tại `tests/test_crm_ky_ket.py:43`—file ngoài phạm vi được sửa. PostgreSQL chưa kiểm chứng.

UTF-8 không BOM; `git diff --check` đạt; chưa commit.

Thông điệp commit: `[DA-3a] vòng 2: cho lưu nháp cũ cùng dự án ngừng bán không chọn lô`