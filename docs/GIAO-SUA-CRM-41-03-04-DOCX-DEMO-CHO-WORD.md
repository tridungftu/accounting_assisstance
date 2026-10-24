# CRM-41-03 FIX04 — Sửa DOCX DEMO để kiểm Word thật

22/10/2026 · CODE_ONLY / ROOT_RELEASE_REQUIRED. Cùng session Claude hiện hành; chỉ sửa hai file hiện có bên dưới. Không chạy lệnh, import, test, SQL, Office, network, cài đặt hoặc xóa file.

## Bằng chứng hiện hành và phạm vi lỗi

- F18 sau FIX03: source377, runtime446; actual terminal20182/551b5d, source manifest55fd8c7b72c92ac8917b66d9f514970f54cc1df7e23a940bb13c69f6b51cc209. Root kiểm độc lập: nonWord51/51, async18 nhóm, privateUI3/3, PG5/5 (Python0skip); GUI thật Save→Convert→Save revision2→reload/reopen giữ đúng fields/lịch40–60. Đây chưa là toàn CRM/M4 đạt.
- Native Word nguyên gốc chạy thực tế: 2 ca = timeout1PASS, xuất PDF positive1SKIP trước `WordThat.chuan_bi`. Guard, owned stop/Jobempty và toàn source posthash đạt; Word có sẵn giữ nguyên PID/start/exe.
- Diagnostic trên nguyên code frozen xác định `_control` tại `crm_docx.py:987`, `w.app.Documents.Open(...)` báo `com_error`, HRESULT -2147352567, scode -2146822496, mô tả **The file appears to be corrupted.** Word đã được tạo và chứng minh ownership trước Open; child dừng xác nhận. Đây là DOCX control do `mau_docx()` trong test tạo, không phải tài liệu thật của Anh.
- `tests/test_crm_giao_ket_http.py:40,191` cũng dùng cùng `mau_docx`; chỉ sửa riêng test native để bỏ qua fixture chung sẽ không khép đường DEMO thực. Worker chuyển PDF positive chưa chạy, nên chưa kết luận renderer product có lỗi và không sửa product trong lượt này.

## Hai file được sửa

1. `tests/test_crm_giao_ket.py` — sửa bộ tạo DOCX tổng hợp `mau_docx(than_them='')` thành DOCX hợp lệ với Microsoft Word, giữ nguyên signature, ý nghĩa và dữ liệu kiểm.
2. `docs/BAO-CAO-CRM-41-03.md` — ghi FIX04 và bằng chứng Root ở trên; lượt này vẫn CODE_ONLY/NOT_RUN, không tự ghi Word/PDF đã đạt.

Không có file mới. Giữ nguyên mọi file product, HTTP test, CJS, SQL1–21, engine nguồn, M4 và M9. Không đọc private var/cấu hình/credentials hoặc sửa tài liệu nguồn.

## Yêu cầu sửa và kiểm lại

- Reuse python-docx/OPC tooling đã có hoặc bổ sung markup OPC/WordprocessingML hợp lệ trong fixture hiện tại; không thêm dependency, provider hay renderer. Giữ split placeholder có run đầu in đậm, bảng lồng, header/footer có tham chiếu, giá trị và tên ô hiện hành, `than_them`, đủ các assertion/locator hiện có. Không đổi test oracle để hợp thức hóa file không đọc được.
- Giữ toàn bộ 51 test nonWord và hai test Word, các assertion, skip/capability semantics và kiểm nội dung PDF hiện có. Không bỏ bớt ca, không biến skip thành PASS, không bỏ bảo vệ ownership/Job/guard hoặc Word control. Các ca malformed/unsupported vẫn phải giữ mục tiêu kiểm ban đầu.
- Cùng fixture phải phục vụ được pure DOCX, HTTP template và native Word; không repair ngầm tài liệu người dùng, không đổi cấu hình Word/Normal.dotm, không gắn vào Word có sẵn, không đọc tài liệu đang mở.
- Sau terminal Root sẽ đóng băng code và kiểm nonWord, native Word positive/timeout, nội dung PDF và hình hiển thị. Khi đạt mới chuyển tiếp M4-02B reuse L3 và các gói CRM41–42 còn lại; CRM→M2-00→E1-MUA giữ hàng chờ, M9 vẫn dừng.
