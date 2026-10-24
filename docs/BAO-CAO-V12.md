# Báo cáo V12 — Đề xuất bút toán từ hóa đơn điện tử (15/10/2026)

## 1. Quyết định của anh Dũng
- Thử cả hai chiều hóa đơn, **chấm riêng** Mua vào và Bán ra.
- **Chọn tháng, máy tự lấy** XML trong thư mục công cụ tải hóa đơn (`<thư mục>\yyyy-mm\mua_vao|ban_ra\*.xml`).
- Dự án **theo lịch sử nhà cung cấp / khách hàng**.
- **Chỉ học đến 06/2026**; các tháng sau để chạy thử.

## 2. Cách máy đề xuất
1. **Học (chỉ tháng ≤ mốc học):** đọc hóa đơn của 12 tháng đến mốc (30/06/2026), ghép từng hóa đơn với chứng từ Junsky đã hạch toán nó theo **tiền chưa thuế + tiền thuế** (Sổ NKC phần lớn ghi số hóa đơn là "0"), trong khoảng 20 ngày trước đến 75 ngày sau ngày hóa đơn, ưu tiên cùng đối tượng rồi gần ngày nhất. Hóa đơn bán ra không ghép với chứng từ thu tiền (có Nợ 111/112/113).
2. **Đề xuất TK** — thử lần lượt, căn cứ đầu tiên đủ mạnh được dùng:
   - cùng người bán/mua **và** tên hàng tương tự (bỏ phần "theo hợp đồng…");
   - tên hàng tương tự ở các đối tác khác;
   - toàn bộ hóa đơn của người bán/mua này.
   Mạnh (Xanh) khi 100 % và ≥ 3 hóa đơn (≥ 4 nếu chỉ dựa trên tên hàng của đối tác khác); Vàng khi 100 % hoặc ≥ 75 % (đo trên T7–T8: ngưỡng 60 % làm tăng đề xuất sai).
3. **Dự án:** dự án mà chứng từ của đối tác này **luôn** ghi (12 tháng đến mốc); không có thì lấy theo hóa đơn tương tự. Chỉ Xanh khi hai nguồn trùng nhau; khác nhau → Vàng + ghi chú.
4. **Nhân viên mua hộ:** nếu ≥ 30 % hóa đơn trước của người bán này được Junsky ghi đối tượng là nhân viên (NV.x) → đối tượng chỉ là gợi ý (không Xanh), ghi chú "cần chọn nhân viên".
5. **Bút toán:** Mua vào: Nợ TK chi phí/hàng (chưa thuế) + Nợ 1331 / Có TK công nợ (tổng). Bán ra: Nợ TK phải thu (tổng) / Có TK doanh thu (chưa thuế) + Có 33311. Dự án, khoản mục gắn vào dòng chi phí/doanh thu.
6. Duyệt hóa đơn **không** tạo tri thức điều kiện như sao kê: hóa đơn học từ Junsky sau khi kế toán nhập.
7. File soát: cột "Thu/Chi · Mua/Bán", thêm tổng hóa đơn mua vào / bán ra. Không tạo file nhập Junsky cho hóa đơn.

## 3. Số đo (kho học đến 30/06/2026; đáp án: Sổ NKC đầy đủ)
Nguồn: XML hóa đơn PLHN 07/2025–08/2026 (bản sao từ `var\vong-2\du-lieu-thu\hoa-don-PLHN-2025-07_2026-08.zip`); kho thử cắt sổ ở 30/06; đáp án `Sổ NKC có đối ưng.xlsx`. Học: 350 hóa đơn bán ra (ghép được 295) và 468 hóa đơn mua vào (ghép được 435) trong 07/2025–06/2026. "TK đúng" = TK chi phí/doanh thu; "Công nợ" = TK 331/131. Tỷ lệ tính trên số hóa đơn ghép được với chứng từ Junsky.

**Tháng 8/2026 (75 hóa đơn)**

| Mức | Hóa đơn | Ghép được | TK đúng | Công nợ đúng | Đối tượng đúng | Dự án đúng |
|---|---|---|---|---|---|---|
| Xanh · Bán ra | 11 | 11 | 11/11 | 11/11 | 11/11 | 10/11 |
| Vàng · Bán ra | 20 | 20 | 20/20 | 18/20 | 20/20 | 15/20 |
| Đỏ · Bán ra | 5 | 5 | 0/5 | — | 4/4 | 1/1 |
| Vàng · Mua vào | 22 | 14 | 13/14 | 14/14 | 5/14 | 11/14 |
| Đỏ · Mua vào | 17 | 6 | 0/6 | 6/6 | 2/2 | 3/3 |

**Tháng 7/2026 (76 hóa đơn)**

| Mức | Hóa đơn | Ghép được | TK đúng | Công nợ đúng | Đối tượng đúng | Dự án đúng |
|---|---|---|---|---|---|---|
| Xanh · Bán ra | 8 | 8 | 8/8 | 8/8 | 8/8 | 8/8 |
| Vàng · Bán ra | 10 | 10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Đỏ · Bán ra | 1 | 0 | — | — | — | — |
| Xanh · Mua vào | 1 | 1 | 1/1 | 1/1 | 1/1 | 1/1 |
| Vàng · Mua vào | 35 | 35 | 29/35 | 35/35 | 14/35 | 35/35 |
| Đỏ · Mua vào | 21 | 21 | 1/21 | 21/21 | 10/16 | 11/15 |

Các bước sửa trong V12 (đo trên T8):
- Dự án lấy theo chứng từ của đối tác: dự án đúng (Mua vào, Vàng) 4/11 → 11/14; bán ra Xanh 11/14 → 10/11 (dòng Xanh ít hơn nhưng đúng hơn).
- Chuỗi căn cứ + ngưỡng 75 %: trên T7+T8, hóa đơn mua vào có đề xuất TK tăng 40 → 51 (đúng 34 → 44, sai 6 → 7).
- Nhân viên mua hộ: 5 hóa đơn xăng T7 trước đây Xanh sai TK (Junsky ghi 1547, lịch sử 12/12 là 6427) nay là Vàng.

## 4. Giới hạn còn lại
- **Mua vào lẻ do nhân viên mua hộ:** Junsky ghi đối tượng là nhân viên; hóa đơn không cho biết nhân viên nào (đúng 5/14 ở T8). Cần nối với đề nghị thanh toán Base để biết người mua.
- **TK chi phí của mua lẻ** (6427/6423/6428/1547…) phụ thuộc mục đích sử dụng, không phụ thuộc người bán → nhiều dòng Vàng/Đỏ.
- **Đỏ · Mua vào T8: 11/17 chưa ghép được** với chứng từ Junsky (có thể chưa nhập, hoặc gộp nhiều hóa đơn một chứng từ).
- **Khách hàng mới** chưa có chứng từ: dự án theo hóa đơn tương tự của khách khác — luôn Vàng.
- Đỏ · Bán ra T8 (5): nghiệp vụ một lần (chuyển nhượng…) không có lịch sử.

## 5. Kiểm thử
258/258 test (249 cũ + 9 V12, dữ liệu tổng hợp) trên Python 3.13 và 3.11. Kiểm giao diện bằng trình duyệt tự động: chọn tháng, lọc Mua/Bán, Đồng ý một hóa đơn, So với Junsky — không lỗi JavaScript.

## 6. Cách dùng
Định khoản → khung **Hóa đơn theo tháng** → bấm **Đề xuất bút toán** ở tháng cần làm. Tháng ≤ mốc học hiện là "dùng để học", không có nút chạy. Thư mục hóa đơn khai ở Nguồn dữ liệu (mục Hóa đơn).
