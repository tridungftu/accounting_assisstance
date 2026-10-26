**Lead (Claude) quyết sau review XS-4b (26/10 ~22:25):**

1. **Chặn — đúng, sửa:** nhật ký cấp/thu hồi người thử **không** ghi `nguoi_dung_id` của người được cấp, cũng không ghi `to_jsonb` cả dòng. Payload chỉ gồm:
   - ID dòng `module_nguoi_thu`;
   - module, pháp nhân;
   - hành động (CAP/THU_HOI);
   - lý do; người thực hiện (Admin).

   Thêm hàm `SECURITY DEFINER` chỉ Admin MTQ hiện hành gọi được để xem danh sách người thử của (module, PN). Không Admin → lỗi có mã. `app_web` EXECUTE nhưng hàm tự kiểm Admin.
   Nhật ký đổi chế độ giữ như hiện tại, vì không chứa người thử.
2. **S5 và chủ bảng:** không yêu cầu chặn DML của chủ bảng/DBA. Chủ bảng là bên tin cậy như mọi bảng khác; thay đổi qua migration có review. Vai ứng dụng đã bị khóa là đủ. Ghi một dòng chú thích trong mã.
3. **CSDL `kho_test_xs4_*`:** đúng mẫu repo. Bộ chạy `tools/chay_test_theo_module.py --pg-demo` tự DROP CSDL test mới sau mỗi module. Không đổi.
