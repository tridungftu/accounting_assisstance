**Trả lời lead (Claude) cho MTQ-4i-a — làm theo, không hỏi lại:**
Cấu trúc phạm vi NGUON (theo A1 đã chốt):
- `khoa` = chuỗi chuẩn hóa `<LOAI>|<id profile hoặc instance>|<mã công ty nguồn hoặc mã kho>` (chữ hoa, bỏ khoảng trắng thừa). `LOAI` ∈ `INVOICE_SET`, `KHO10_PHIEU`. `L11_EVIDENCE_SET` đã typed theo pháp nhân → **không** dùng NGUON, xét bằng phạm vi PN như hiện có.
- Xác minh khi Admin cấp: (công ty nguồn / kho) phải **đã có ánh xạ hiện hành → đúng pháp nhân** của dòng phạm vi trong bảng ánh xạ mà hệ thống đang dùng để định tuyến chứng từ nguồn về pháp nhân (tìm trong mã M2/M5 bảng ánh xạ công ty→PN, kho→PN; dùng đúng bảng đó, không tạo bảng mới). Không có ánh xạ → từ chối cấp. Phòng phải thuộc pháp nhân đó.
- Nguồn gộp nhiều pháp nhân: mỗi pháp nhân liên quan cần một dòng phạm vi riêng; validator chỉ kiểm một dòng — việc "đủ mọi PN" là trách nhiệm caller ở 4i-c (ghi rõ trong docstring).
- Loại nguồn nào **không tìm thấy** bảng ánh xạ → để loại đó tiếp tục bị chặn (không cho cấp) và ghi "Cần lead" trong báo cáo; vẫn làm các loại còn lại.
Môi trường không có `python` thì ghi NOT_RUN.

