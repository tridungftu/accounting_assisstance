Anh, đã sửa đúng 3 tệp được giao, không commit.

- Thêm resolver PN, hồ sơ CRM, liên kết tiền, lô file soát; mở rộng HĐ cho M1/file soát. Giữ `CU` khi PN chưa bật; trường hợp không hợp lệ trả `MTQ_CAN_RESOLVER_MTQ4`.
- “HĐ thuộc CRM”: `module_chu IS NULL AND loai NOT IN ('VAY','MUA')`, theo `crm_s1.py:93`. Nhánh `TIEP_NHAN` giữ điều kiện cũ.
- Migration mới thay cả hai hàm, giữ chữ ký/ACL và các hằng SQL cũ. UTF-8 không BOM; migration giữ LF.
- **Test:** 13 đạt/46, 31 skip PG, **2 lỗi mới** do test cũ ghim đúng hai hằng SQL. Test mới: 4 đạt, 14 skip. `git diff --check` đạt.
- **Cần Anh/lead:** cập nhật hai test cũ ngoài phạm vi 3 tệp, đánh số migration và chạy PG. Chưa thể kết luận xanh.

Thông điệp commit đề xuất: `[MTQ-4a3a] Bổ sung resolver thẩm quyền CRM/M1 và nhật ký từ chối`