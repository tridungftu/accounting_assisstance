**(a) Không — Chặn:** `src/kho_tri_thuc/giao_dien/module_cong_tac.py:54` áp dụng danh sách vai CRM (`VAI`) cho mọi module. **Vi phạm:** bổ sung lead mục 1 yêu cầu trả mọi PN phiên được phép. **Tình huống hỏng:** phiên `MO_PHONG_DU_AN_A1`, vai `DU_AN`, đã được cấp M4 tại PN A → GET `trang-thai?module=M4` truyền mảng vai rỗng vào `ktt_co_vai` → trả `200 []`, thiếu PN A. Quyền mẫu này có tại `k2/m4_demo.py:33`. Phần từ chối PN client đúng tại `module_cong_tac.py:71`; chưa thấy đường trả cờ PN ngoài phạm vi.

**(b) Đạt:** `module_cong_tac.py:91`, `:94`, `:102`, `:114` có `authorize(private=True)`, `mutation_lock`, gọi dịch vụ với SQL kiểm Admin và ánh xạ 403/409/400/503. Thông báo nghiệp vụ tiếng Việt; không thêm log người thử.

**(c) Đạt:** `src/kho_tri_thuc/giao_dien/server.py:986` chỉ bắt `/api/cong-tac-module/`, nằm ngay sau nhánh MTQ; không đổi thứ tự các nhánh cũ.

**(d) Đạt:** diff chỉ thêm route riêng và test; không gắn chặn vào module khác, không sửa JS hoặc thêm thư viện.

| Kiểm tra | Kết luận |
|---|---|
| 1. Phạm vi | **Đạt:** đúng ba tệp được giao; fixture giả. Có 26 test, khớp báo cáo worker ghi NOT_RUN. |
| 2. Đúng yêu cầu | **Không:** thiếu PN hợp lệ trong tình huống ở (a). |
| 3. Tiền, số liệu, quyền | **Không:** lọc quyền đọc thiếu vai `DU_AN`; quyền Admin kiểm tại SQL đúng. Không có phép tính tiền mới. |
| 4. Không phá phần cũ | **Đạt trong diff:** dùng lại factory MTQ; không thêm engine, bảng/cột, SQL chéo dữ liệu nghiệp vụ hoặc gọi API AI trực tiếp. |
| 5. Giao diện/câu người dùng | **Đạt trong phần mới:** câu thông báo tiếng Việt; không thêm giao diện ngày/tiền. |

**Kết luận: Chưa Đạt — 1 Chặn.** Tôi không chạy test; gate 27 HTTP và 6 MTQ là kết quả lead cung cấp.

**Hỏi Claude**

- Xin xác nhận GET cho M4 phải bao gồm PN của phiên vai `DU_AN` đã được cấp M4? `module_cong_tac.py:54` hiện loại toàn bộ vai này; cần xác nhận vì chỉ dẫn tái dùng nguồn khung CRM đang đi kèm bộ lọc vai riêng của CRM.