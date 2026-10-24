# 33 · Sơ đồ cây toàn bộ nghiệp vụ — đầu vào → chứng từ → bộ tiếp nhận → chu trình → bút toán → Junsky

**Ngày lập:** 16/10/2026 · **Yêu cầu:** anh Dũng muốn một cây toàn bộ nghiệp vụ, bắt đầu từ đầu vào, để nhìn thấy linking trong xử lý toàn hệ thống.
**File trên máy anh:** `D:\Claude\Phan mem ho tro ke toan\33-cay-nghiep-vu.drawio` (mở bằng draw.io, kéo thả được; mỗi cạnh gắn vào nút nên di chuyển nút thì cạnh đi theo), kèm `.png`, `.svg` (xem trước) và `.sinh-so-do.py` (sinh lại khi đổi nội dung — việc chạy script giao Claude/Codex).
**Căn cứ:** tài liệu 29 (10 module), 31 (dự án sẵn có), 32 (CRM kế toán, liên kết chéo L1–L12, ba nguyên tắc đã chốt 16/10).

## Cách đọc (trái → phải = đường đi của một chứng từ)
| Cột | Nội dung | Bước đường ống (tài liệu 01) |
|---|---|---|
| Gốc | Toàn bộ nghiệp vụ kế toán — đơn vị thí điểm PLHN | — |
| 1 · Nguồn đầu vào (8) | Ngân hàng · Cổng thuế · Base · Hợp đồng đã ký · Ban QLDA · Nhân sự · Kho KCN · Kế toán (bảng tính nội bộ) | — |
| 2 · Chứng từ (15) | sao kê, lệnh chi, XML mua/bán, bảng kê cổng thuế, RQ, HĐ thuê đất KCN, HĐ mua bán nhà ở, biên bản bàn giao, HĐ thầu, HĐ vay, nghiệm thu, bảng lương, phiếu nhập/xuất, bảng khấu hao/phân bổ | Bước 1 tiếp nhận |
| 3 · Bộ tiếp nhận (9) | màu xanh lá = dự án sẵn có (#7 tải hóa đơn, #8 backup Base, #5 review xây dựng, #9 Sheet khoản vay, bộ đọc sao kê); tím = mở rộng (#6 trích tham số hợp đồng → CRM kế toán); xanh dương = mới (bảng lương, bảng khấu hao); xám nét đứt = chờ khảo sát (#10 kho 9 sheet) | Bước 2 bóc tách |
| 4 · Chu trình (10) | M1 · Tiền về / tiền đi từ sao kê · M2 · Hóa đơn mua vào → phải trả · M3 · Hóa đơn bán ra & doanh thu BĐS · M8 · Bảng kê thuế · M4 · Nghiệm thu & chi phí dự án · M9 · Vốn vay · M7 · Lương · M5 · Kho vận hành KCN · M6 · TSCĐ & CCDC · M10 · Định kỳ, đóng sổ & đối chiếu ngược (mỗi nút ghi trạng thái: đang chạy thật / V12 / tiếp theo 1-2-3 / chờ khảo sát) | Bước 3–6 khớp, kiểm tra, sinh bút toán, duyệt |
| Làn cam | Liên kết chéo L1–L11 vẽ nét đứt: mỗi liên kết là một đường dọc trong làn, nối hai chu trình; chú giải ở cuối sơ đồ; L12 (mọi chu trình → M10) ghi bằng chữ | Nguyên tắc liên kết (tài liệu 32) |
| 5 · Bút toán (10) | bút toán đề xuất của từng chu trình (M8 ra bảng kê, không phải bút toán) | Bước 5 |
| 6 · Junsky + bước 8 | file Excel nhập theo lô, chỉ dòng đã duyệt → sổ chính thức → đối chiếu ngược quay về M10 (nét đứt xanh dưới cùng) | Bước 7–8 |
| Dải xám | M0 · Xương sống dùng chung: danh mục & khóa chung, quy tắc + tri thức CFO + tri thức học, màn hình duyệt, bảng liên kết chứng từ, agent Zalo, xuất Excel, nhật ký, lịch chạy | Dùng cho mọi chu trình |

## Ba nguyên tắc liên kết chéo đã chốt 16/10/2026 (ghi trên sơ đồ)
1. **Công nợ trước, tiền sau.** Chiều chi: tạm ứng trước hóa đơn → hạch toán ngay 331 dư Nợ / 141 theo RQ, liên kết chờ hóa đơn. Chiều thu: tiền về chưa xếp được vào cọc hay đợt → **đề xuất Vàng ngay theo quy tắc CFO** (khách chưa có hợp đồng → 344 cọc; có hợp đồng → 131 đợt gần nhất; lệch số tiền → agent Zalo hỏi phòng kinh doanh); khi hợp đồng/đợt nạp sau, máy chỉ nối liên kết, không sinh bút toán mới. Không treo. → Trả lời luôn câu hỏi 2 còn mở ở tài liệu 23.
2. **Một dòng hóa đơn một đích** (chi phí / 241 / tài sản / kho): **máy đề xuất theo tri thức học từ sổ quá khứ** (cùng đối tác + tên hàng, như V12), quy tắc nhóm G × Dự án/Vận hành × ngưỡng TSCĐ là tầng kiểm tra; người duyệt; đổi đích sau duyệt = hoàn tác có nhật ký.
3. **Liên kết là dữ liệu**: bảng `lien_ket_chung_tu` dùng chung, **làm ngay trong V kế tiếp của xương sống, trước M4 · Nghiệm thu & chi phí dự án**.

## Những gì sơ đồ chưa thể hiện (cố ý)
- Chi tiết bên trong từng chu trình (phễu 6 bước, Xanh/Vàng/Đỏ) — xem tài liệu 23, 29.
- Giai đoạn lập trình: sơ đồ chỉ ghi trạng thái; chia giai đoạn sau khi có kết quả khảo sát (tài liệu 30).
- Phần đã bỏ: giá thành sản xuất, kho sản xuất, hợp nhất.

## Sửa sơ đồ
- Đổi chữ/màu một ô: sửa trực tiếp trong draw.io.
- Thêm nguồn, chứng từ, chu trình hoặc liên kết: sửa các bảng `SOURCES`, `RECEIVERS`, `MODULES`, `OUTPUTS`, `LINKS` đầu file `.sinh-so-do.py` rồi sinh lại để giữ bố cục đều.
