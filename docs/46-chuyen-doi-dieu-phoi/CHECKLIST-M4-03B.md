# M4 · Nghiệm thu & chi phí dự án — màn 03B "Đối chiếu căn cứ nghiệm thu ↔ hóa đơn" (checklist lead soạn 25/10/2026, **Anh duyệt 25/10**)

**Căn cứ:** kế hoạch M4 đã chốt 20/10 (`THIET-KE-MODULE-DE-CHOT-2026-10-20\M4-XAY-DUNG-VA-NGHIEM-THU.md` dòng 13, 35, 40, 65: "Hóa đơn và nghiệm thu cùng sự kiện dùng một ghi nhận chung M2/M4, không ghi nợ hai lần"); phần máy chủ 03B đã có trên hop-nhat (`k2\ghi_nhan_chung.py`, `m4\ghi_nhan_nghiem_thu.py`, migration M0029).
**Quy tắc máy chủ đã khóa (màn hình phải theo):** kế toán chọn nguồn **tường minh** (đợt nghiệm thu, hóa đơn mua) — máy **không tự ghép, không chấm điểm khớp**; "một phần" là khai báo thô của kế toán; kết quả **chỉ là căn cứ**, chưa ghi công nợ (công nợ nội bộ là gói sau, chưa thiết kế); thêm/bớt nguồn = phiên bản mới của cùng đối chiếu; hóa đơn đã thuộc đối chiếu khác bị từ chối.

## Checklist (dự kiến cho cổng B)
1. Trong màn **Kế toán nghiệm thu** (M4), mỗi đợt đã được kế toán xác nhận (03A) có khối **"Đối chiếu căn cứ với hóa đơn"**.
2. Kế toán **chọn hóa đơn mua** từ M2 trong danh sách lọc theo pháp nhân + đối tác của hợp đồng; máy không tự chọn.
3. Ghép **nhiều–nhiều**: một đợt ↔ nhiều hóa đơn, một hóa đơn ↔ nhiều đợt; mỗi liên kết khai **toàn bộ** hoặc **một phần** (một phần bắt buộc khai mức).
4. Đính kèm **tệp căn cứ** (biên bản, bảng đối chiếu…).
5. **Lưu nháp → Xác nhận**; sau xác nhận thì khóa; sửa = **phiên bản mới**, xem được **lịch sử**.
6. Danh sách **"còn thiếu"**: đợt chưa có hóa đơn, hóa đơn chưa gắn đợt, phần khai còn thiếu.
7. Hóa đơn đã gắn ở đối chiếu khác → báo rõ "đã gắn ở …", không cho gắn trùng.
8. Nguồn đổi sau khi xác nhận (hóa đơn có bản mới, nghiệm thu đổi) → trạng thái **"Cần kiểm lại"**.
9. **Không hiện, không ghi số công nợ** ở màn này.
10. Quyền: chỉ kế toán phụ trách dự án thấy/sửa; người không có quyền đọc hóa đơn M2 không thấy hóa đơn.
11. Tiếng Việt, ngày dd/mm/yyyy, tiền có đơn vị, không mã kỹ thuật.

**Không làm ở màn này:** ghi công nợ, đề nghị thanh toán (Request), bút toán, gợi ý khớp tự động.

## Anh đã chốt (25/10, QD-20261025-13)
- Vị trí: **khối trong màn Kế toán nghiệm thu**, dưới mỗi đợt đã xác nhận.
- **Có xếp hạng gợi ý**: danh sách hóa đơn lọc theo đối tác + kỳ, xếp hóa đơn gần với đợt lên đầu (kỳ; số tiền khi hóa đơn có số đọc được); vẫn do kế toán bấm chọn — dòng 2 sửa thành "lọc + xếp hạng gợi ý".
- "Một phần" **khai bằng số tiền** (máy chủ 03B hiện khai tỷ lệ → sửa bằng migration mới, M4-5a).
