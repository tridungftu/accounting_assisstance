## Review Codex (chỉ đọc) — mtq-4a3b · 26/10 ~16:05

(a) **Đạt:** 9 callback CU giữ đúng lệnh/tham số cũ và vị trí so với side effect — `k2/crm.py:184,248,448,495,696,743,790,821,869`. Riêng trích DOCX, quyền kiểm trước engine (`:182` → `:222`).

(b) **Không đạt đầy đủ:** các đối tượng hồ sơ/HĐ/liên kết/lô lấy từ dòng đã đọc trong `_tx`. Ba điểm dùng PN lấy ID qua `_pn()` **trước** `_tx`, chưa đáp ứng nguyên văn “qua RLS” — `k2/crm.py:183,247,695`; `_pn` tại `:127`.

(c) **Đạt:** `trich_tu_docx` và `kiem_nhan_tien` chỉ bọc phần kiểm trong `_tx`; engine #6 ngoài giao dịch — `k2/crm.py:181,222,693`.

(d) **Đạt:** thông báo trung tính giữ nguyên mã lỗi; `exc_info=True` ghi qua logger máy chủ, không đưa chi tiết exception vào thông báo client — `k2/quyen.py:189,228,236`.

| Việc kiểm | Kết luận |
|---|---|
| Phạm vi | **Đạt:** đúng 3 tệp; fixture mới dùng dữ liệu DEMO/UUID. Báo cáo khớp: thêm 20 test method, 32→52; CRM giữ 690. |
| Đúng yêu cầu | **Chưa đạt:** có điểm giao dịch cần chặn bên dưới và vướng mắc RLS tại (b). |
| Tiền, số liệu, quyền | **Chưa đạt về quyền:** đủ 8 khóa `PHI_TIEN`, không truyền tiền; nhưng quyền nhận kết quả chưa giữ tới giao dịch ghi. |
| Không phá phần cũ | **Đạt qua diff:** giữ callback CU; không thêm gọi API AI trực tiếp, không chạm M9. |
| Câu cho người dùng | **Đạt trong phần đổi:** bỏ “Cần Anh”, không thêm ngày/tiền hiển thị sai định dạng. |

**Chặn — `k2/crm.py:245`:** `nhan_ket_qua_6` commit giao dịch kiểm quyền trước khi mở giao dịch ghi tại `:252`, làm nhả khóa thẩm quyền. Vi phạm thiết kế **§5.1** được giao việc dẫn chiếu: khóa quyền phải giữ cùng giao dịch nghiệp vụ. Tình huống: người có quyền CRM cũ và ô LAP được bật → gate cho phép → Admin thu hồi quyền MTQ và commit → giao dịch thứ hai vẫn ghi hồ sơ bằng quyền RLS cũ, không kiểm lại LAP. Đây là lỗi của cách nối mới.

**Nên sửa — `k2/crm.py:183,247,695`:** chưa đủ căn cứ kết luận ba đối tượng PN đã đọc qua RLS. Chưa xác lập được tình huống vượt quyền vì gate vẫn kiểm PN/phạm vi, nên không nâng thành Chặn.

Đã kiểm `git diff --check`, đạt. Tôi không chạy lại unittest vì môi trường không tìm thấy Python; gate thuần/28 skip PG là thông tin Anh cung cấp, PG chưa được tôi xác minh.

**Hỏi Claude**

- Có bước kiểm lại `CRM:TIEP_NHAN:LAP` nào ngăn tình huống thu hồi trên tại `k2/crm.py:245`? Cần xác nhận vì giao dịch ghi sau đó không gọi lại gate.
- Ba điểm PN tại `k2/crm.py:183,247,695` có được chấp nhận là ngoại lệ yêu cầu “qua RLS” không? `_pn()` chạy trước GUC và `master.phap_nhan` không nằm trong danh sách RLS đã đối chiếu.

**Kết luận: chưa đạt để gộp; còn 1 Chặn và các câu hỏi cần Claude xác nhận.**
---
**Lead lọc (Claude):**
- Chặn `crm.py:245` (nhan_ket_qua_6 kiểm quyền ở giao dịch riêng rồi commit trước giao dịch ghi): **giữ Chặn** (§5.1, TOCTOU khi MTQ bật) → vòng 2.
- Hỏi 2 (`_pn()` trước GUC ở :183,:247,:695): **bỏ** — chỉ tra mã PN → UUID (danh mục không bí mật), quyền do cổng SQL quyết theo PN/phạm vi; chấp nhận ngoại lệ.

## Review Codex VÒNG 2 (chỉ đọc) · 26/10 ~16:15

1. **Đạt — Chặn vòng 1 đã sửa:** gate `CRM:TIEP_NHAN:LAP` nằm trong cùng `_tx` với các INSERT và `_lap_ho_so`; không còn commit giao dịch kiểm riêng trước giao dịch ghi. Đáp ứng §5.1 — `src/kho_tri_thuc/k2/crm.py:245,246,252,262,274`.
2. **Đạt — không thấy lỗi mới do diff vòng sửa:** callback CU giữ nguyên lệnh/tham số và chạy trước adapter/ghi kho. Test mới kiểm cả CU/MTQ × commit/rollback, xác nhận không có commit giữa gate và ghi — `src/kho_tri_thuc/k2/crm.py:248,250`; `tests/test_mtq_crm.py:635,681,685`.

| Việc kiểm | Kết luận trong phạm vi vòng 2 |
|---|---|
| Phạm vi | **Đạt:** đúng 2 tệp được giao; fixture thêm dùng DEMO/UUID. Báo cáo khớp thay đổi; đếm tĩnh có 53 test method, gồm 5 test PG. |
| Đúng yêu cầu | **Đạt:** kiểm quyền và ghi cùng giao dịch; bổ sung test hồi quy theo giao việc vòng 2. |
| Tiền, số liệu, quyền | **Đạt:** khắc phục việc nhả khóa quyền trước ghi; diff không đổi phép tính hay truyền tiền. |
| Không phá phần cũ | **Đạt qua diff:** giữ callback CU; không đổi luồng engine #6, không thêm gọi API AI trực tiếp. |
| Giao diện/câu người dùng | **Đạt:** diff không thay đổi thông báo, ngày hay tiền hiển thị. |

`git diff --check a3a635a lat/mtq-4a3b` đạt. Tôi không chạy unittest/PostgreSQL trong phiên chỉ đọc; kết quả gate thuần OK, 28 skip PG là thông tin lead cung cấp. Số **48 đạt/53, 5 skip PG** của worker khớp cấu trúc test, chưa được tôi chạy xác minh.

**Chặn / Nên sửa / Để sau:** không có phát hiện trong phạm vi vòng 2.

**Hỏi Claude:** không có.

**Kết luận: đạt review vòng 2; điểm Chặn vòng 1 đã được xử lý.**
**Lead lọc (Claude):** Đạt, không lọc. Kiểm xác suất: khong.
