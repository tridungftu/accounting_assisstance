**Biên bản review chéo G2-CR1 — Kết luận: Cần sửa**

Nhánh `lat/g2-cr1`, commit `f855fea`; đối chiếu `hop-nhat-20261023`, đề giao, chuẩn Core v1.0 và đặc tả nghiệp vụ.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Mốc riêng có thể thiếu toàn bộ bộ tham chiếu phiên bản mà vẫn qua schema.** Từ DEMO, bỏ đồng thời `moc_du_an_id`, `lan_moc`, `ngay_du_kien`, `ngay_thuc_te` khỏi `tien_do[1].moc`, giữ `su_kien="DAM-10000000-0000-4000-8000-000000000031"`: payload vẫn thỏa các trường bắt buộc và không kích hoạt `dependentRequired`. Vi phạm yêu cầu “đúng ràng buộc đặc tả” trong đề giao và các trường bắt buộc có điều kiện tại `CONTRACT-NGHIEP-VU.md:692–695`; dữ liệu mất căn cứ phiên bản mốc. Cần buộc đủ bộ khi dùng mốc riêng và thêm ca âm bỏ đồng thời cả bộ. Test hiện chỉ bỏ từng trường nên không bắt được trường hợp này. | **Chặn** | `src/kho_tri_thuc/modules/crm/contract/du_an_dang_ban.schema.json:94` và `:97`; `tests/test_g2_cr1.py:149` |

Kết quả theo các trọng tâm:

1. **Phạm vi — Đạt:** diff chỉ thêm đúng 3 tệp whitelist; worktree sạch. DEMO khớp nguyên ví dụ trong đặc tả.
2. **Chuẩn và đặc tả — Chưa đạt:** có lỗ hổng điều kiện mốc riêng nêu trên. Tên trường, kiểu tiền, đơn vị, nullable và vỏ chung phù hợp; các điểm chờ Anh được giữ trong mô tả.
3. **An toàn — Đạt trong phạm vi lát:** không có SQL, DROP/xóa, thay đổi quyền, log/audit chứa bí mật hoặc truy cập kho thật. Role/RLS/DEFINER/`search_path` và test dưới login thật **không áp dụng**, vì đề giao chỉ yêu cầu test thuần, không PG.
4. **Dùng lại — Đạt:** dùng kiểu chung qua URN, resolver/fallback G2-17 và `_bo_schema()` của G2-24; không viết bộ kiểm mới.
5. **Test — Chưa đủ:** có ca âm về thiếu trường, đơn vị, nguồn rỗng/trùng, kiểu và định dạng; thiếu ca bỏ cả bộ tham chiếu mốc riêng. Test tổng tỷ lệ/grain chỉ kiểm DEMO, đúng phạm vi mà test tự công bố.

**Kiểm chứng:** đã đối chiếu JSON và truy vết điều kiện schema trong bộ nhớ, không sửa tệp. Reviewer **chưa chạy lại Python test** vì `python`/`py` không có trên PATH. Kết quả lead cung cấp: CR1 **17/17**, G2-17 **22/22**, G2-24 **42/42**.

**Hỏi Claude:** xác nhận phân loại và xử lý điểm Chặn tại schema dòng 94–98 trước khi giao vòng sửa, theo mẫu review.