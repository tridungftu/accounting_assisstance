**Biên bản review chéo TRICH-1a — Kết luận: Cần sửa**

Nhánh `lat/g3-trich-1a`, commit `cf273d5`; đối chiếu `hop-nhat-20261023...HEAD`.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| Kiểm UUID chưa bảo đảm contract và tính riêng biệt của tệp nguồn. **Đã tái hiện:** `tep_id` dạng 32 ký tự không có dấu `-` được `UUID(value)` chấp nhận, nhưng đầu ra bị bộ kiểm schema từ chối với lỗi `uuid`. Đồng thời, `abcdef00-0000-4000-8000-000000000001` và bản viết hoa được chấp nhận làm hai ID riêng dù cùng một UUID. Vi phạm `CONTRACT-DU-LIEU.md` §2 về kiểm format/đầu ra và §2.1 về ID riêng cho tệp gốc, phản hồi nguồn. Cần kiểm đúng format và so sánh theo giá trị UUID; bổ sung hai ca âm tương ứng. | **Chặn** | `src/kho_tri_thuc/engines/e_trich_xuat/tham_so.py:89`, `:93`; `tests/test_g3_trich_1a.py:204` |

Kết quả các mục kiểm:

- **Phạm vi — Đạt:** diff đúng 3 tệp trong whitelist, không sửa/xóa tệp khác.
- **Yêu cầu — Cần sửa tại phát hiện trên.** Nguồn, phiên bản và SHA256 khớp các bản đã đối chiếu; ghi rõ khác biệt hash giữa nguồn độc lập và bản repo. Danh mục đủ **37 tham số**, khớp định nghĩa gốc và XLSX.
- **An toàn/quyền — Đạt trong phạm vi lát:** không thêm SQL, login CSDL, role/RLS/DEFINER hoặc mở quyền; kiểm bằng login PostgreSQL không áp dụng cho thư viện thuần này. Không thấy đường ghi bí mật/DSN vào log/audit, thao tác xóa hoặc sửa nguồn gốc.
- **Dùng lại mã — Đạt:** bọc parser và pipeline hiện có, giữ globals nguồn; DOCX đi XML Python, xử lý Track Changes; chặn Word/COM, PDF/OCR và Cloud.
- **Test — Còn thiếu ca âm UUID nêu trên:** có đúng 18 test method; các assertion chính kiểm nội dung Track Changes, danh mục/hash, bảo toàn đầu vào và số lần gọi bằng 0 đối với các đường bị cấm.

**Xác minh:** 18/18 là kết quả lead cung cấp. Tôi không chạy lại suite có tạo tệp trong sandbox chỉ đọc; đã tái hiện lỗi bằng kiểm tra trong RAM với chặn ghi tệp và gọi mạng/process. Không đọc kho thật, tệp bí mật hay `*.local.json`; không sửa tệp.

**Hỏi Claude:** Lead xác nhận điểm Chặn trên trước khi giao vòng sửa; hai ca tái hiện hiện đều vượt qua kiểm đầu vào của adapter.