**Biên bản review chéo G1b · 30/10/2026 — Kết luận: Cần sửa.**

Phạm vi: chỉ đọc tài liệu và mã nguồn liên quan; không đọc kho thật, tệp bí mật hoặc `*.local.json`; không sửa tệp, chạy ứng dụng hay gọi dịch vụ.

Quy ước căn cứ: **A** = `docs/47-core/g1/DAC-TA-API.md`; **R** = `docs/47-core/g1/ANH-XA-ROUTE.md`.

| Phát hiện | Mức | Căn cứ và yêu cầu sửa |
|---|---|---|
| **Hai tài liệu công bố tên route khác nhau.** Bảng ánh xạ dùng `tai_lieu`, `ket_qua`, `quan_tri`, `bao_gia`; thân/OpenAPI dùng `tai-lieu`, `ket-qua`, `quan-tri`, `bao-gia`. Client làm theo bảng sẽ gọi sai API. | **Chặn** | R:44, R:75, R:145 ↔ A:28, A:150, A:174. Thống nhất theo danh mục của TL 55:27–28 và handoff; sửa đồng thời bảng ánh xạ, ví dụ và OpenAPI. |
| **Một số đích Core trong bảng ánh xạ chưa có contract.** Có API danh sách việc, SSE, tải nội dung kết quả và lệnh khởi động riêng, trong khi thân/OpenAPI chỉ khai báo tập route khác. | **Chặn** | R:75, R:217–220, R:232 ↔ A:159–173, A:705, A:872. Ví dụ thiếu `GET /viec`, luồng sự kiện việc và endpoint tải nội dung kết quả. Đổi ánh xạ sang operation đã khai báo hoặc bổ sung method/path, quyền, schema, status và chính sách SSE. |
| **Luồng tải kết quả quản trị toàn hệ thống chưa nhất quán về pháp nhân.** Kết quả cho phép `phap_nhan_id: null`, nhưng tệp bắt buộc pháp nhân UUID và route tải bắt buộc header pháp nhân. | **Cần sửa** | A:714–716, A:1350–1364, A:1585–1596, A:1621, A:1649–1652. Chốt cách lưu và tải tệp hệ thống; dùng phạm vi hệ thống cùng kiểm quyền Admin rõ ràng, tránh yêu cầu chọn một pháp nhân không liên quan. |
| **Bảng câu hỏi chưa bao quát các quyết định đang treo trong phụ lục.** C1–C6 đủ phương án và khuyến nghị, nhưng chưa xử lý chủ sở hữu nghiệp vụ `V` và phương án duy trì/ngừng alias. | **Cần sửa** | A:390–395; R:100, R:420. Ghép các ngưỡng kỹ thuật thành nhóm để dành chỗ cho quyết định phân ranh module và chuyển tiếp; vẫn giữ tối đa 6 câu. Không hỏi lại các nguyên tắc cổng, tiến trình riêng hoặc Admin áp dụng đã chốt. |
| **Một số dẫn nguồn KS-E không chứng minh nhận định.** Nhận định về RAM, duyệt và revision/TTL có căn cứ ở nơi khác, nhưng các dòng được dẫn không phù hợp. | **Cần sửa** | A:26 dẫn KS-E:79, :93; R:332 dẫn KS-E:93, :95, :123, :124. Trong đó :93 là dòng phân cách bảng, :123 trống. Đổi sang KS-E:110–116 và các dòng tương ứng từng nhận định. |
| OpenAPI dùng `default` chung cho lỗi; chưa khai báo response `409` riêng tại các operation CAS/chống trùng. Điều này không tự làm OpenAPI sai, nhưng giảm khả năng kiểm contract tự động. | **Gợi ý** | A:1251, A:1267, A:1412–1429. Khai báo rõ `409` tại các operation liên quan, kèm ví dụ `XUNG_DOT_PHIEN_BAN`, khóa khác nội dung và yêu cầu đang xử lý. |

**Độ đầy đủ và độ phủ**

- **Cấu trúc đủ 9/9 mục:** G1b-1 đủ 6 mục; G1b-2 đủ 3 mục. Các thiếu sót nội dung nằm trong bảng trên.
- **Route cũ: 392/392 mẫu có dòng ánh xạ — 100%.** Đếm theo dịch vụ + method + mẫu path, mở rộng `{a,b}`, gồm tài sản tĩnh, OPTIONS, mẫu chưa phát hành và endpoint phía client. Đã kiểm riêng shell, host #6 và Review cũ. Có dòng ánh xạ không đồng nghĩa đích mới đã đủ contract.
- **Thân ↔ OpenAPI:** 39/39 operation khớp method/path; 32 path; không trùng `operationId`; 210 `$ref` đều có đích; các YAML alias đều có anchor.

**Kiểm mẫu 20 khẳng định có dẫn nguồn**

Tên tệp mã nguồn viết gọn dưới đây thuộc `src/kho_tri_thuc/`; `server.py`, `crm_g.py`, `m2_tai_hoa_don.py` thuộc `giao_dien/`.

| Mẫu | Khẳng định và căn cứ đã đối chiếu | Kết quả |
|---|---|---|
| 1–7 | Kiểm Host/Origin — `server.py:918`; token chung — `server.py:928`; phiên DEMO/RAM — `server.py:193`, :196; trường revision báo giá — `crm_g.py:75`; nhóm lỗi 409 — `crm_g.py:83`; tạo/dedupe trong transaction — `ha_tang/hang_viec.py:21`; đề nghị dừng — `ha_tang/hang_viec.py:69`. | 7/7 đúng |
| 8–12 | Route health — `server.py:1003`; tài sản tĩnh — :1010; upload raw/header metadata — :1143; download intake — :1019; OPTIONS trả 403 — :973. Đối chiếu R:87–96. | 5/5 đúng |
| 13–17 | Quick trả 201/202 khác nhau — `server.py:1161`, :1169; quick nhận actor client — :1170; knowledge nhận actor client — :1211; mở thư mục — :1196; tải tất cả M2 trả 200 — `m2_tai_hoa_don.py:1076`. Đối chiếu R:112–116, R:221, R:313, R:319. | 5/5 đúng |
| 18–20 | Ba nhận định/dẫn nguồn về RAM, phê duyệt và revision/TTL tại A:26, R:332, nêu trong phát hiện phía trên. | 0/3 đủ căn cứ tại dòng dẫn |

**Tỉ lệ dẫn nguồn đúng trong mẫu: 17/20 = 85%.** Đây là tỉ lệ mẫu kiểm, không phải điểm chất lượng tổng thể.

**An toàn và quyết định của Anh:** đặc tả đã yêu cầu Core kiểm quyền cho API, download và việc nền (A:50–56); token ngữ cảnh có chữ ký, ràng buộc instance/request, khóa ký chỉ Core giữ (A:197–203); lỗi không lộ khóa (A:76). Các vi phạm cũ có hướng sửa tại R:313–328. Cơ chế giữ/chuyển giao/thu hồi cổng, mỗi module một tiến trình, mặc định tự kích hoạt rồi tự đóng và chỉ Admin áp dụng đề xuất phù hợp CD-028 (A:188–191, A:232–238).

**Giới hạn kiểm chứng:** đã rà tĩnh YAML/OpenAPI 3.1, `202 + viec_id`, khóa chống trùng và mô tả CAS → 409; chưa chạy được YAML/OpenAPI validator vì môi trường thiếu công cụ tương ứng. Vì vậy chưa chứng nhận hợp lệ bằng parser. Cần xử lý hai điểm chặn và bổ sung kết quả validator trước khi trình duyệt bộ API.