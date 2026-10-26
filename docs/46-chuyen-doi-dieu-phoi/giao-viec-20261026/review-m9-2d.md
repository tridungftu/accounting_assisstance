## Review Codex (chỉ đọc) — m9-2d · 26/10 ~19:15

(a) **Đạt** — Có snapshot: trả trước khi gọi AI; số liệu kèm mốc, đơn vị và liệt kê từng khoản, không cộng khác tiền tệ. `dich_vu_hoi_dap.py:21–29`; `so_du_snapshot.py:98–109,131–145`.

(b) **Không — Chặn 1** — `src/kho_tri_thuc/m9/so_du_snapshot.py:72–79,125–128`. Vi phạm giao việc §1 và D(b): lọc đúng mã, không lấy nhầm khoản. Với snapshot DEMO trong test có A, A-1, C, hỏi **“dư nợ A-10”** → không nhận ra bộ lọc nào → trả cả ba khoản dù A-10 không tồn tại.

(c) **Không — Chặn 2** — `src/kho_tri_thuc/m9/so_du_snapshot.py:120–125`. Vi phạm giao việc §2, D(c) và thiết kế §5.1: điều khoản phải đi luồng hợp đồng. Hỏi **“Theo hợp đồng, kỳ điều chỉnh khoản vay A là bao nhiêu?”**, hợp đồng quy định mỗi 3 tháng, snapshot có ngày điều chỉnh 01/11/2026 → trả ngày từ snapshot, bỏ qua hợp đồng. Riêng không truyền snapshot: luồng cũ được giữ tại `dich_vu_hoi_dap.py:21–29`.

(d) **Đạt** — Nhật ký không ghi câu trả lời hoặc số liệu lấy từ snapshot; chỉ ghi câu hỏi và metadata. `dich_vu_hoi_dap.py:30–40`.

Năm kết luận kiểm tra:

| Việc kiểm | Kết luận |
|---|---|
| Phạm vi | **Đạt**: đúng 3 tệp; fixture DEMO; đúng 21 test mới. Worker ghi NOT_RUN, không nhận đã chạy. Gate lead cung cấp: 60 đạt, 0 lỗi, 0 skip. |
| Đúng yêu cầu | **Không đạt**: hai điểm Chặn trên. |
| Tiền, số liệu, quyền | **Tiền đạt**: giữ Decimal, không tính lãi/tổng. **Quyền chưa rõ — Nên sửa**: cần xác nhận hợp đồng đầu vào snapshot. |
| Không phá phần cũ | **Không đạt khi có snapshot** do Chặn 2; không snapshot giữ luồng cũ. Diff không thêm đường gọi API trực tiếp/Cloud. |
| Giao diện/câu người dùng | **Đạt về định dạng**: tiếng Việt, ngày dd/mm/yyyy, tiền có đơn vị; nội dung sai đã ghi tại hai điểm Chặn. |

Tôi chỉ đọc; không chạy lại test vì môi trường không có Python khả dụng.

**Hỏi Claude**

- Xác nhận Chặn 1: “dư nợ A-10” phải trả không tìm thấy? `so_du_snapshot.py:72–79,125–128` — hiện bộ lọc rỗng khiến trả toàn danh mục.
- Xác nhận Chặn 2: câu hỏi kỳ điều chỉnh **theo hợp đồng** phải đi luồng hợp đồng? `so_du_snapshot.py:120–125` — hiện chỉ cần chứa từ khóa là bị chuyển sang snapshot.
- Snapshot có được lọc quyền pháp nhân trước khi truyền vào không? `dich_vu_hoi_dap.py:21` — nhánh mới bỏ qua `loc_tai_lieu`, kể cả tập rỗng; giao việc chưa nêu trách nhiệm lọc snapshot.

**Kết luận: Chưa đạt, chưa gộp; còn 2 điểm Chặn và các câu hỏi cần Claude xác nhận.**
**Lead lọc (Claude):** giữ cả 2 Chặn; trả lời Hỏi Claude: (1) mã/định danh nêu trong câu không khớp khoản nào → KHONG_THAY_TRONG_SNAPSHOT, KHÔNG trả cả danh mục; chỉ khi câu không nêu định danh nào mới liệt kê toàn bộ. (2) câu có dấu hiệu hợp đồng ('theo hợp đồng', 'hợp đồng quy định', 'điều khoản', 'quy định', 'điều', 'khoản' kèm số…) → đi luồng hợp đồng (tra_so_du trả None); snapshot chỉ cho câu về số liệu hiện hành.
