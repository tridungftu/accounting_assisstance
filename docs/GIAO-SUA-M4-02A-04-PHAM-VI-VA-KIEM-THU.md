# M4-02A FIX04 — Khép lỗi phạm vi và hai lỗi kiểm thử

**Phạm vi đã được Anh giao; lượt sửa hữu hạn, CODE_ONLY.** Kế thừa Review hiện có, không xây lại engine/UI. Không phải full M4 đã hoàn tất.

## 1. Căn cứ đã chạy thực

- FIX03 đã kết thúc và dừng; 49 native pure và 14 public DOM case đạt. Các kết quả này không thay kiểm PostgreSQL/HTTP hay GUI thực.
- Native PostgreSQL 12 ca: 11 đạt, 1 lỗi fixture. Native HTTP 7 ca: 5 đạt, 2 không đạt; không skip. Tất cả process/thread đã dừng, source trước/sau nguyên hash.
- HTTP H04 trả 400/CSDL_TU_CHOI thay mã 403 đúng phạm vi. Diagnostic read-only sáu owner connection mới xác nhận SQLSTATE 55000, ObjectNotInPrerequisiteState tại review_quyen dòng 18; review_kiem gọi lại lỗi này. Actor soạn đúng dự án trả SOAN; actor khác dự án và reviewer không có đợt cùng gặp lỗi record.
- Nguyên nhân source: review_quyen khai báo d record, chỉ SELECT INTO d khi p_dot khác NULL, nhưng biểu thức IF sau đó tham chiếu d.trang_thai. Không được dựa vào thứ tự đánh giá AND để né record chưa có cấu trúc. Native test hiện dùng lại backend đã có lần chạy có đợt; chưa bảo vệ riêng tình huống kết nối mới.

## 2. Ba sửa chữa

1. **Sửa phạm vi bằng M20 corrective migration.** Giữ nguyên M19; thay định nghĩa review_quyen qua migration mới, dùng row type xác định hoặc nhánh điều kiện không tham chiếu record trước khi khởi tạo. Giữ nguyên quyền SOAN đúng dự án, REVIEW chỉ đúng tệp gắn đợt DA_NOP, security/search_path và ACL hiện có. Không nới quyền, không cấp quyền ghi/web mới, không sửa generic mapper để nuốt SQLSTATE. Kết nối mới phải trả mã domain đã có: B1 ngoài dự án → 403/M4_KHONG_CO_QUYEN_DU_AN; reviewer không đợt → 403/M4_REVIEW_PHAM_VI. Đọc/tải ngoài phạm vi vẫn giữ hành vi hiện hành.
2. **R07d:** đổi khóa fixture upload BOQ gốc/BOQ phụ lục để khác khóa import của từng tệp. Không nới idempotency, không đổi expected resolver theo hiệu lực phụ lục, giữ toàn bộ kiểm tra THAY/THEM/trước ngày hiệu lực/đích không hợp lệ.
3. **H01:** kiểm việc sử dụng thuộc tính innerHTML thực sự thay cho cấm chuỗi xuất hiện cả trong comment. Giữ kiểm tài sản tải đúng bytes, no-store, phạm vi static và bảo vệ DOM. Không chỉ xóa assertion, sửa comment hợp lệ để làm xanh, skip hoặc bắt lỗi chung.

## 3. Migration và kiểm thử phải bổ sung

- M19 đã áp dụng vào DEMO retained: toàn bộ pg_migrations.py hiện 869545 byte, SHA256 73975e09a4b1a1f8e7229a684919ee9db34f525ee8e1731239c48ea3b87dd30e là prefix bất biến. sql_review.py hiện 37415 byte, SHA256 64bd3f9d1a96bec27e7abece2b5cf5688f1d2b12c58a8f5f157ff8181ac348f0 cũng là prefix bất biến. Chỉ append sau EOF; không đổi tuple/SQL/checksum migration 1–19, kể cả gián tiếp qua helper.
- M20 chỉ sửa đúng hàm có lỗi; không bảng nghiệp vụ/approval/AP/Request/schema khác. CREATE OR REPLACE phải giữ quyền đã có, không GRANT mới.
- Cập nhật assertions registry/default version để bảo vệ identity/checksum/prefix 1–19 và M20 ở cuối. Kiểm cả DB mới lên 20 lẫn DB đã 19 nâng lên 20; dữ liệu/hồ sơ/lịch sử cũ nguyên trạng, chạy migrate lại không đổi.
- Bổ sung regression dùng owner connection thực sự mới cho mỗi trường hợp không đợt: SOAN đúng dự án dương; ngoài dự án âm; REVIEW không đợt âm. Đường HTTP thật vẫn kiểm chính xác 403 + domain enum, không chấp nhận generic 400/404. Giữ positive REVIEW trên đợt đã nộp và negative đợt nháp/tệp không gắn đợt.
- Không dùng tập rỗng, cùng lỗi, skip, worker giả hay timeout/deadlock làm kết quả đạt. Root kiểm độc lập sau khi coder dừng và freeze.

## 4. Phạm vi file và cách làm

Giữ đúng 13 existing targets trong handoff M4-02A và controller, NEW0; chỉ sửa file cần cho ba lỗi và report. Không thêm framework hay thư viện. Không sửa vendor/reference, guard, master/quyen/seed, CRM/M9, server/index/app hoặc các file được bảo vệ.

Đọc [quyết định dùng chung engine](QUYET-DINH-ENGINE-TRICH-THAM-SO-DUNG-CHUNG.md): extractor #6 tại source qua API chung cho M4/CRM/M2, từng lượt yêu cầu bộ tham số riêng. Lượt FIX04 không mở thêm engine hoặc thực hiện migration API này; giữ nguyên thuật toán Review L1/L2.

Chỉ dùng Read/Glob/Grep/Edit/Write. Không chạy lệnh, import, AST, test, SQL, HTTP, network, browser hay launcher ở lượt CODE_ONLY. Không đọc var/.env, dữ liệu thật, credentials hoặc oracle riêng của Root. Không xóa/rename/move/reset/cleanup file hay dữ liệu.

Cập nhật BAO-CAO-M4-02A với FIX04: phần đã sửa, ca kiểm đã viết, self-test NOT_RUN_CODE_ONLY. Không tuyên bố runtime, GUI hoặc module hoàn tất. Root kiểm lại source/migration/native/độc lập và giao diện trước khi bàn giao.
