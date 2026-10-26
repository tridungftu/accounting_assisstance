# Ma trận thẩm quyền — các điểm cần chốt trước khi nối tiếp MTQ-4 (26/10/2026)

**Căn cứ:** ba bản kiểm kê do Codex lập (chỉ đọc mã): `KK-MTQ4-CRM.md`, `KK-MTQ4-M4.md`, `KK-MTQ4-LIEN-MODULE.md`. Mỗi bản có bảng từng điểm kiểm quyền (tệp:dòng) và chuỗi lát ≤ 3 tệp.

**Tiến độ:**
- Đã nối: CRM luồng B + M1 (MTQ-4a…4a3b, M0045).
- Đang làm: MTQ-4b1a (M0047), resolver cho bảng riêng CRM G1–G7/dự án.
- Còn khoảng 40 lát: CRM 14, M4 14, liên module 13.

**Mặc định an toàn đang áp:** câu nào chưa chốt thì khi pháp nhân **đã bật** ma trận, thao tác đó **bị chặn** (không quay về quyền cũ). Pháp nhân chưa bật vẫn chạy quyền cũ như hiện nay. Không pháp nhân nào bị bật cho tới khi đủ chuỗi.

## A. Chặn cả một nhóm lát (cần chốt sớm)

| # | Câu hỏi | Chặn | Đề xuất của lead |
|---|---|---|---|
| A1 | **Phạm vi nguồn** (M2/M5/L11): một nguồn hóa đơn/kho (instance + profile + công ty nguồn) ứng với pháp nhân/phòng nào; Admin cấp phạm vi nguồn ra sao | Toàn bộ M2/M5/L11/03B (13 lát) | Admin cấp phạm vi nguồn tường minh theo (profile, công ty nguồn) → pháp nhân. Nguồn gộp nhiều pháp nhân phải đủ quyền ở **mọi** pháp nhân liên quan. Thiết kế §5.1 đã nói hướng này; cần Anh xác nhận. |
| A2 | **Phần nền dùng chung** `ktt_duoc / ktt_pn_cho_phep`, RLS nền, lớp ghi nhật ký từ chối ở máy chủ, kiểm "sẵn sàng bật" | Bước cuối mọi nhóm | Lead giữ làm một chuỗi riêng **MTQ-NEN** (chạy tuần tự, sau các resolver). Các nhóm không tự sửa phần nền. |
| A3 | **Cổng đọc/lọc danh sách** trong giao dịch chỉ đọc (cổng hiện tại thử ghi nhật ký rồi hoàn tác, nên không dùng được để lọc hàng) | Màn danh sách/đếm CRM (S1), danh sách M4 | Thêm một hàm SQL **chỉ đọc** dùng cùng lõi quyết định, không ghi nhật ký; ghi từ chối chỉ ở thao tác. Làm trong MTQ-NEN. |

## B. Nghiệp vụ — cần Anh chốt

| # | Câu hỏi | Đề xuất |
|---|---|---|
| B1 | **Tỷ giá mặc định dùng chung** nhiều pháp nhân: sửa tỷ giá cần quyền ở những pháp nhân nào | Cần quyền "Sửa tỷ giá" ở **tất cả** pháp nhân đang dùng tỷ giá đó (theo thiết kế §5.1). Thiếu một pháp nhân → chặn. |
| B2 | **CFO duyệt sau kích hoạt lệch bộ chuẩn (V8)** thuộc ô nào; ô này chưa có trong danh mục | Thêm ô "CRM · Kiểm hợp đồng ký: Duyệt lệch bộ chuẩn" (có tiền = tổng HĐ), hoặc gộp vào "Duyệt" G5/G6. Lead nghiêng **ô riêng**. |
| B3 | **Phạm vi hẹp** người ký/kiểm theo đúng HĐ–dự án–khách (thay bảng phân công cũ) | Admin cấp phạm vi theo HĐ hoặc dự án. Giữ ràng buộc khách hàng và phiên bản. Không nới thành cả pháp nhân. |
| B4 | **M4 ghi PDF hồ sơ đã duyệt** (02C) dùng ô nào (danh mục chỉ có Xem PDF) | Ghi PDF thuộc ô "Duyệt hồ sơ đợt: Sửa" (người lập bộ hồ sơ), không cần ô Duyệt. Seal vẫn đòi quyết định chấp thuận đã có. |
| B5 | **Kế toán 03A xem PDF**: cần cả ô 03A Xem và ô PDF Xem, hay chỉ ô PDF | Cần **cả hai** (quyền đọc nhạy cảm tách riêng, theo §5.1 "mức đọc nhạy cảm"). |
| B6 | **Tải mẫu/bộ chọn master M4** thuộc Xem hay Lập/Sửa; route không có dự án thì lấy ngữ cảnh nào | Thuộc **Lập** của "Hồ sơ" theo dự án được chọn. Không có dự án → chặn khi bật. |
| B7 | **Tỷ giá ghim cho chấp thuận M4 ngoại tệ** chưa thấy lưu ở kết luận | Chặn chấp thuận ngoại tệ khi chưa có tỷ giá ghim. Giao riêng phần lưu tỷ giá ghim. |
| B8 | **L11 xem bằng chứng thô**: ô "M5 · Nguồn thô: Xem" hay đòi cả M2 + M5 | Đòi **cả M2 và M5** như các thao tác L11 khác. |
| B9 | **Khởi động lại / dừng bộ tải M2** (vận hành) thuộc ô nào; chưa có trong danh mục | Thêm ô "M2 · Hóa đơn mua vào: Vận hành bộ tải" chỉ cho kế toán trưởng/Admin, hoặc giữ cho Admin. Lead nghiêng **chỉ Admin**. |
| B10 | **03B ghi nhận đối chiếu chung**: Sửa/Kiểm ở mỗi nguồn | Kiểm theo **từng nguồn** (M4 và M2). Không dùng quyền M4 để đọc M2. |
| B11 | **Đường cũ** (QuickPosting/Store/bridge) còn phục vụ pháp nhân nào khi bật | Pháp nhân còn dùng đường cũ thì **chưa được bật**. Kiểm "sẵn sàng bật" sẽ báo. |

## C. Lead tự quyết (ghi lại, không cần Anh)

- C1: thứ tự migration dùng chung (`pg_migrations.py`): CRM 4b → 4e, rồi M4 4f, rồi liên module 4i, rồi MTQ-NEN; lead đánh số khi gộp.
- C2: điểm nối `giao_dien/m4_request.py` (ngoài danh sách cũ) đưa vào nhóm M4.
- C3: các guard kỹ thuật (chủ bảng, append-only, bất biến) **giữ nguyên**, không phải ô nghiệp vụ, không thành đường vượt cho Admin/CFO.

**ĐÃ CHỐT 26/10 ~19:50 (QD-20261026-08): Anh đồng ý toàn bộ đề xuất A1–A3, B1–B11.**

**Anh trả lời:** chọn đồng ý đề xuất, hoặc ghi lựa chọn khác cho từng dòng A1–A3, B1–B11. Lead giao tiếp các lát theo câu trả lời.
