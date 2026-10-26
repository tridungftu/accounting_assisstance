Anh, đã triển khai XS-4A, chỉ thêm:

- [khai_bao_module.py](src/kho_tri_thuc/ha_tang/khai_bao_module.py): mô hình, validator, chuyển đổi CRM hai chiều, kiểm engine theo cờ.
- [test_xs4_khai_bao.py](tests/test_xs4_khai_bao.py): 18 test về hợp lệ, round-trip, thứ tự và danh bạ.

Đã kiểm UTF-8 không BOM và whitespace. Không sửa khung hiện có; không commit.

**Test: NOT_RUN (0/18)** vì không có Python trên PATH; chưa xác định lỗi mới so với nền.

**Cần lead:** chạy test mới và hồi quy CRM.

Thông điệp commit đề xuất: `[XS-4a] Thêm mô hình khai báo module và bộ chuyển đổi CRM`.