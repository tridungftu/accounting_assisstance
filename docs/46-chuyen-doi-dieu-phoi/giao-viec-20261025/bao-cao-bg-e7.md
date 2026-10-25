Anh, đã sửa **10 chỗ hiển thị**, dùng chung `nguoi`, ưu tiên `*_ten`; không đổi dữ liệu gửi máy chủ.

- `crm_g.js`: hàm chung dòng 3; các chỗ đổi tại 951, 1013, 1015, 1016, 2090, 2332, 2363, 2594, 2600, 3278.
- `tests/crm_giao_ket_async.cjs:227`: thêm 6 ca Người lập và kiểm DOM không chứa `MO_PHONG_`.
- Test đạt: Giao kết **47/47 nhóm**, Dự án **39/39**, Ký kết **14/14**, Khung lưới **33/33**. Không còn lỗi trong bốn bộ.
- Hai file UTF-8 không BOM. Chưa commit theo yêu cầu. Thông điệp đề xuất: `[BG-e7] Chuẩn hóa tên người thao tác trên màn giao kết`.
- Ngoài phạm vi: `k2/crm_giao_ket.py:1405` vẫn đưa `tao_boi` vào `nguoi_lap` bản in sơ bộ; chưa sửa.