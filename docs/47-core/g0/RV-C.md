**Biên bản review chéo G0 — KS-C: CẦN SỬA.** Nội dung kiểm mẫu phần lớn đúng; cần hoàn thiện ánh xạ route và thông tin ghi/chạy lâu của server Review cũ. Không phát hiện dữ liệu cấm trong tài liệu.

Đối tượng: `docs/47-core/g0/KS-C.md`, đối chiếu phần chung và mục KS-C của `GIAO-G0.md`. Chỉ đọc mã, không chạy ứng dụng/test, không truy cập các đường dẫn bị cấm. Các tệp mã được đối chiếu dưới đây không thay đổi giữa commit khảo sát `6feb66d` và HEAD `5823f1a`.

Quy ước căn cứ: **C** = `docs/47-core/g0/KS-C.md`; đường dẫn mã tính từ `src/kho_tri_thuc/`; **GD** = `giao_dien/`; **RV** = `m4/review_goc/may_chu/`. Mức “Gợi ý” ở các dòng Đúng chỉ ghi nhận kết quả kiểm mẫu, không yêu cầu sửa.

| Phát hiện | Mức | Căn cứ tệp:dòng |
|---|---|---|
| **Đúng:** cổng H kiểm Host, Origin và `Sec-Fetch-Site`, chưa xác thực người dùng. | Gợi ý | C:15 → GD/server.py:918 |
| **Đúng:** mọi POST và `/api/*` trừ health phải có token chung. | Gợi ý | C:16 → GD/server.py:928, GD/server.py:980 |
| **Đúng:** cookie `ktt_crm` ánh xạ SID vào dictionary trong RAM. | Gợi ý | C:17 → GD/server.py:193, GD/server.py:196 |
| **Đúng:** POST `/api/upload` gọi `Intake.receive`, nhận metadata qua header. | Gợi ý | C:36 → GD/server.py:1143 |
| **Đúng:** GET `/api/nghiem-thu` có gọi đồng bộ dữ liệu, không thuần đọc. | Gợi ý | C:45 → GD/server.py:1128, GD/server.py:137 |
| **Đúng:** GET `/api/crm/hop-dong` gọi `CrmDanhSachK2.danh_sach` sau lấy danh tính phiên. | Gợi ý | C:62 → GD/crm_g.py:480 |
| **Đúng:** POST `/api/m4/tep` lấy danh tính phiên rồi gọi service tải tệp. | Gợi ý | C:89 → GD/m4.py:547 |
| **Đúng:** danh mục route công tắc module khớp GET/POST trong mã. | Gợi ý | C:76 → GD/module_cong_tac.py:12 |
| **Đúng:** `tai-tat-ca` của M2 trả HTTP 200 và gọi bộ điều phối. | Gợi ý | C:115, C:168 → GD/m2_tai_hoa_don.py:1076 |
| **Đúng:** cổng owned #6 kiểm token và giới hạn download vào kết quả đã niêm phong. | Gợi ý | C:125 → nguon/trich6_host.py:431, nguon/trich6_host.py:484 |
| **Đúng:** client Mask dùng Bearer và ba endpoint đã liệt kê. | Gợi ý | C:156 → tri_thuc/cong_ai.py:635, :660, :669, :683 |
| **Đúng:** CRM S1 mặc định 25 bản ghi/trang, tối đa 100. | Gợi ý | C:171 → k2/crm_s1.py:52, k2/crm_s1.py:72 |
| **Đúng:** duyệt knowledge chỉ so actor gửi vào với cấu hình; state trả `approval_actor`. | Gợi ý | C:201 → GD/server.py:1211, GD/operations.py:972, GD/operations.py:844 |
| **Sai một phần:** “Mọi route qua `Handler._xu_ly`” bỏ qua ngoại lệ POST `/api/tat`, được xử lý trực tiếp trong `do_POST`. Kiểm Host/Origin và `X-HD` vẫn có. Sửa phạm vi câu khẳng định. | Cần sửa | C:134 → RV/server.py:462, RV/server.py:489 |
| **Sót ánh xạ:** bảng `/api/v1/` chưa chỉ rõ đích hoặc quyết định giữ/ngừng cho các nhóm Review cũ như `/api/cai_dat`, `/api/csdl/*`, `/api/hop_dong/*`, `/api/boq/*`. Việc chỉ ánh xạ Review `/api/viec` và lời gọi engine chưa bao phủ các nhóm này. | Cần sửa | C:138, C:140, C:146, C:148 so với C:180–193; yêu cầu tại `docs/47-core/g0/GIAO-G0.md:89` |
| **Thiếu thông tin theo từng nhóm route Review:** bảng chỉ có route và handler; đoạn tổng hợp phía sau chưa xác định rõ ghi/chạy lâu cho các nhánh như `kiem_tra_ai`, `thu_cloud`, `boq/tai_len`. Riêng BOQ upload có thể gọi chuyển PDF/DOCX qua OCR đồng bộ, cần đánh dấu khả năng chạy lâu. | Cần sửa | C:139, C:148, C:150 → RV/dich_vu.py:267, :276, :919; yêu cầu tại `docs/47-core/g0/GIAO-G0.md:72` |

**Tỉ lệ kiểm mẫu:** 13/14 khẳng định đúng đầy đủ = **92,9%**; 1 sai một phần; 0 lệch dòng. Đây là tỉ lệ của mẫu đã kiểm, không đại diện thống kê cho toàn tài liệu. Hai thiếu sót về độ bao phủ được tính riêng.

Trong phạm vi đối chiếu, chưa xác nhận thêm route shell bị bỏ sót. Migration thuộc KS-B; khảo sát chi tiết công cụ ngoài thuộc KS-D/E, không tính là thiếu của KS-C.

**Kết luận: Cần sửa**, tập trung vào ba dòng yêu cầu sửa trong bảng. Không có phát hiện mức **Chặn**.