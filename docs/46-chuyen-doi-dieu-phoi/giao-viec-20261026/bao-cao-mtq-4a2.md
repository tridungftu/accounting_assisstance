Anh, đã nối `cap_nhat_mapping`, `xac_nhan_tham_so`, `kiem_truoc` và sửa đủ 3 ý review. Chỉ đổi 3 tệp được giao, UTF-8 không BOM; không commit, không bật ma trận, không sửa SQL.

- **Điểm bỏ:** `trich_tu_docx`, `nhan_ket_qua_6`, `bo_sung_ho_so`, `_trich_lai`, `kiem_nhan_tien`, `lien_ket`, `go_lien_ket`, `xuat_file_soat`, `tep_file_soat` — cần resolver ngoài phạm vi cổng SQL hiện có.
- **Test:** MTQ-CRM **31 đạt/32**, 1 skip PG; MTQ liên quan **56 đạt/89**, 33 skip. CRM trước/sau đều **690 ca**, cùng mã lỗi nền: 16 ERROR/37 FAIL, **không lỗi mới**. Không mở server/PostgreSQL.
- **Cần Anh:** tách lát bổ sung resolver cho 9 điểm còn lại. Catalog hiện dùng `PHI_TIEN` tương ứng trường hợp không áp dụng tiền.
- **Thông điệp commit đề xuất:** `[MTQ-4a2] Nối mapping, xác nhận và kiểm CRM; sửa adapter thẩm quyền`