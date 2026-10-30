# Review Opus G2-13 — Kết luận: Cần sửa (30/10 ~23:50)

Nhánh `lat/g2-13`. PG: test_g2_13 24/24; toàn bộ G2 439 ok / 0 lỗi.

| Mức | Phát hiện | Tệp:dòng |
|---|---|---|
| **Chặn** | `khoa_lien_ket_noi_bo` khóa advisory **mọi** `chung_tu` của pháp nhân (kể cả hết hiệu lực), giữ tới commit. Vài nghìn chứng từ / năm → "out of shared memory" (khoảng 6.400 khóa mặc định), hỏng cả phiên khác. Thừa vì khóa pháp nhân (dòng 141) đã tuần tự hóa. Chỉ khóa `p_ids` đã sắp xếp. | 013:143-146 |
| Cần sửa | `tong_nghia_vu_noi_bo` trả **con số tổng**, trái "chỉ trả kết luận". Không ràng `p_module` với role gọi → role kiểm module X đọc tổng của module Y. Đổi thành hàm kiểm trả boolean, ràng module ↔ role. | 013:149-163 |
| Cần sửa | **Mở cửa khi mất ngữ cảnh:** `mtq_phien_rls()` rỗng → role kiểm thấy 0 dòng → kiểm tiền trả TRUE / tổng 0; ca A, B lọt. Phải buộc `p_pn ∈ mtq_phien_rls()`, sai thì RAISE. | 013:149-182 |
| Cần sửa | **Hủy / sửa liên kết cũ bị chặn sai.** K2 P:1040 cho hủy bất kỳ lúc nào:<br>(a) kiểm tiền áp cho chứng từ cũ đã hết hiệu lực;<br>(b) mục tiêu cũ bị so mã băm nên module nâng phiên bản căn cứ là không hủy được.<br>Chỉ kiểm tiền / mã băm cho mục tiêu **mới**; mục tiêu cũ chỉ khóa. | 013:169, 248-250, 325-328, 82-86 |
| Nên sửa | Sửa liên kết: đọc `cu` trước, rồi khóa hợp cũ + mới đã sắp xếp. Hiện được che nhờ vòng khóa toàn bộ — **thành bắt buộc khi bỏ vòng đó**. | 013:238-248 |
| Nên sửa | `ghi_v2` cho chứng từ hết hiệu lực không lấy khóa liên kết; FK `KEY SHARE` không xung đột UPDATE cột thường → liên kết có thể commit trên chứng từ vừa hết hiệu lực song song. | 012:352-358 / 013:276-278 |
| Nên sửa | Tra resolver dùng `p_contract` của người gọi làm phiên bản contract resolver đích; khác phiên bản → `CHO` mãi. Lấy phiên bản đang dùng từ registry. | 013:63 |
| Nên sửa | Ca âm quá rộng có thể xanh giả: `assertRaises(psycopg.Error)` / `LoiLienKet` không kiểm mã; hết thời gian chờ khóa cũng tính đạt. Kiểm `LIEN_KET_VUOT_NGHIA_VU` / `VUOT_CHUNG_TU`. | test:395-398, 420-421, 437-441 |
| Để sau | Khóa cả pháp nhân đúng, nhưng giữ tới commit của transaction ngoài. Khóa hẹp: chứng từ (sắp ID) → advisory theo bộ ba nghĩa vụ. Thiếu test cạnh tranh phía chứng từ (60+60 trên chứng từ 100) và test policy RESTRICTIVE thêm sau cài. | 013:141, 110-113 |

**Đạt:**
- ca 80+30 chặn cả hai phía;
- role kiểm NOLOGIN / NOBYPASSRLS, kiểm membership hai chiều, DEFINER `search_path` cố định, REVOKE PUBLIC;
- resolver qua registry, thiếu → `CHO` 0 dòng;
- giảm sức chứa;
- không sửa 001–012;
- test PG thật, login thật, FORCE RLS, ca C hai kết nối.
