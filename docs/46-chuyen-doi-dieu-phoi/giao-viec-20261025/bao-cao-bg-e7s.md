Đã sửa BG-22, Anh. Bản in/DOCX dùng tên hiển thị đọc trong cùng giao dịch; thiếu tên thì dùng nhãn an toàn, không dùng login.

- Nguồn tên: `ha_tang/pg_migrations.py:61` — `master.nguoi_dung.ten`.
- Sửa: `k2/crm_giao_ket.py:1353,1410`; thêm test tại `tests/test_crm_moc_du_an_bao_gia.py:199`; cập nhật ghim `tests/test_crm_ky_ket.py:43`. Cả 3 tệp UTF-8 không BOM.
- Test đúng lệnh: **71 đạt, 3 skip, 1 lỗi import có sẵn**. Chạy bổ sung đường dẫn `tests`: **104/113 đạt, 9 skip, không lỗi**. Đã kiểm DOCX không chứa `MO_PHONG_`.
- Không commit. Thông điệp đề xuất: `[BG-e7s] Dùng tên hiển thị người lập trên bản in báo giá`.