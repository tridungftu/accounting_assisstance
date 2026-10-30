# Review Opus — CHUAN-CORE-CSDL-v1.0 và CHUAN-CORE-API-v1.0 (CD-034 mục 4), 30/10/2026

**Kết luận: cả hai bản Đạt, không Chặn.**
- Chép đúng phiếu đã duyệt (CSDL 1A, 2A, 3A; API 1A, 2A), đặc tả G1 và CD-026…036. Không có quyết định mới, không có chỗ ngược phiếu.
- Mọi con số đã dò lại từng cái với đặc tả, đều có nguồn.
- Còn **7 Cần sửa nhỏ**, sửa trước khi gửi Anh.

## Cần sửa (ưu tiên; câu trong ngoặc kép chép nguyên được)

- **C1 · API §3.9a + checklist §7.4.** OpenAPI ghi tối đa 20971520 bytes (`DAC-TA-API.md:1781`), tức 20 MiB. Thay bằng: "Mỗi tệp không quá 20 MB (= 20 MiB = 20.971.520 byte theo OpenAPI của đặc tả; Core đếm byte khi nhận luồng)."
- **C2 · Đầu cả hai tệp.** Đổi "**Ngày Anh duyệt:** 30/10/2026" thành: "**Ngày Anh duyệt phiếu CSDL/API:** 30/10/2026 · **Văn bản chuẩn:** chờ Anh xem (CD-034 mục 4)".
- **C3 · API §3.6a**, thêm sau câu "Biên nhận operation Core lưu tách…": "Biên nhận operation Core giữ 24 giờ từ kết quả cuối (đặc tả API §2.4); giữ tiếp khi việc còn hoạt động hoặc kết quả chưa xác định; hết hạn không cho phép tạo trùng nghiệp vụ."
- **C4 · §8 cả hai bản**, thêm dòng chờ: "Cách gọi cụ thể (hàm SDK cho biên nhận V2, File Store, mã ủy nhiệm, credential instance) nằm ở `CHUAN-CORE-SDK-v1.0.md`, **chưa ban hành, chờ Anh duyệt phiếu SDK bản 2**. Chưa có SDK thì không tự viết lớp thay thế."
- **C5 · Đường dẫn phụ lục (CSDL §8.1, API §8).** Bản sao chép sang `D:\Claude\QUY-TRINH-CHUNG\CHUAN-CORE\` thì link tương đối `../g1/…` sẽ hỏng. Ghi đường dẫn từ gốc repo, ví dụ "repo `accounting_assisstance`, `docs\47-core\g1\DAC-TA-CSDL.md`".
- **C6 · CSDL §3: tách việc Core / việc module.**
  - Thêm câu đầu mục 3: "Mục gắn [Core] do Core dựng — module chỉ cần không vi phạm; mục gắn [Module] là việc người lập trình module phải làm."
  - Gắn [Core] cho §3.5.3, §3.5.4, §3.6.1 (phát mã), §3.7.1, §3.11 mục 2 và 4–6, §3.14, §3.15.
  - Thêm vào checklist §7.3: "[ ] Nếu module là chủ nghĩa vụ tiền: có resolver `SECURITY DEFINER` đăng ký ở `loi.dang_ky_ham_module`, khóa theo thứ tự chứng từ → nghĩa vụ, `vai_kiem_toan_ven_mod_<ma>` với policy chỉ lọc pháp nhân; đạt ca nghĩa vụ 80 + 30."
- **C7 · CSDL §3.2**, thêm dưới bảng V1–V4: "Biên nhận chống trùng của operation module ghi qua hàm V2 vào `loi_tai_lieu.bien_nhan_thao_tac`, cùng transaction và cùng kết nối với thay đổi nghiệp vụ; bất biến, giữ vĩnh viễn (chi tiết CHUAN-CORE-API §3.6b)."

## Để sau

- **D1.** Ví dụ CSDL §5.1 đổi `phap_nhan_id` thành `…0001` cho trùng ví dụ API.
- **D2.** API §8 thêm "Route quản trị sổ contract: bổ sung khi mở G2". Bảng 503 ở API §3.5 thêm "thiếu chính sách bắt buộc" (`DAC-TA-API.md:97`).
- **D3.** API dài khoảng 1.000 dòng, vượt khung 6–10 trang của đề; không cần cắt.
