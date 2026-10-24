# CRM-41-01-06B — Đủ hook bảo vệ và kiểm đúng hai đường khởi động

CODE_ONLY; cùng session Claude hiện hành; không tự chạy product/test/SQL/launcher. Đây là sửa hữu hạn trước khi tiếp tục CRM41-03 và M4-02B, không đổi kiến trúc engine dùng chung.

## Phạm vi chính xác
Chỉ sửa 3 file hiện có, NEW=0: `src/kho_tri_thuc/nguon/trich6_host.py`, `tests/test_trich6_host.py`, `docs/BAO-CAO-CRM-41-01.md`. Giữ mọi file khác, source #6 thật, staged patch, catalog/thuật toán, client, SQL/master/quyền, callers, launcher và M9 byte-exact. Không xóa file, không tắt/sửa/import bù guard, không thêm framework/provider.

Baseline F13: source372/runtime440; FIX06A đã terminal/stop/scope đúng. Root kiểm source native25/25 đạt; pure32/32 của client/callers giữ bằng chứng riêng. Owned host có17PASS/1ERROR `ChuaRo` ở ca DOCX ALL37/subset/replay; KHÔNG coi18PASS. Đọc lại đúng lượt đã lưu qua ownedhost cho status200 done và raw200 đúng50151bytes/hash; toàn DataRoot giữ nguyên. Hai phép so đường dẫn và literal seal/DTO đều đạt trên artifact hiện có. CHƯA chứng minh lỗi do Windows prefix; không thêm sửa đường dẫn theo suy đoán. Không đổi expected/fixture để che lỗi; Root sẽ kiểm lại ca thật với error-code witness.

## Hai sửa bắt buộc
1. `guard_hop_le`: ngoài module có sẵn, bytes A517, cờ bật và bytecode tắt, phải có ĐỦ BA hook thực `os.unlink`, `os.remove`, `shutil.rmtree` do chính tệp guard định nghĩa. Nonempty subset hiện tại chưa đủ. Giữ nhận diện hook thực/co_filename và fail closed; không yêu cầu toàn bộ13 tên trong HAM_XOA vì guard gốc chỉ trực tiếp cài ba điểm này. MOCK chứng minh từng thiếu/một-hai hook không được chấp nhận; child từ chối trước mkdir/HD_*/source import; parent không spawn khi thiếu.
2. Sửa giả định startup: đường USERBASE thật trên máy là `Python313/site-packages/zz-codex-no-delete.pth` với `import codex_no_delete_guard`; không có `usercustomize.py`. Đường còn lại là PYTHONPATH/sitecustomize. Không dùng điều kiện `'usercustomize' in sys.modules` để lặng bỏ USERBASE. Unit guard thật cũng không được bắt buộc sitecustomize/usercustomize nếu guard đã nạp hợp lệ từ .pth. Giữ kiểm startup có sẵn, A517/flag/ba hook/bytecode trước khi mở nguồn; không import guard bù trong code hoặc test để biến thiếu startup thành đạt.

## Kiểm phải viết và giới hạn báo cáo
- Tách ca thật USERBASE/.pth-only và PYTHONPATH/sitecustomize-only thành HAI test method riêng trong file hiện có; giữ toàn bộ ý nghĩa của ca kết hợp cũ. USERBASE-only bỏ mọi PYTHONPATH directory cung cấp sitecustomize nhưng giữ src/deps cần chạy; sitecustomize-only bỏ PYTHONUSERBASE và chứng minh guard của con vẫn hợp lệ. Provider không tồn tại ở máy khác phải skip riêng có lý do, không biến nhánh chưa chạy thành PASS. Máy Root hiện có cả hai provider; Root sẽ yêu cầu chạy cả hai.
- Giữ nguyên ca DOCX thật ALL37, subsetTC-01/TT-02, TC-01=0001/2026/trích dẫn input, catalog/implementation/seal/raw hash+length, replay không thêm lượt, từ chối route/token, instanceB không đổi và stop có xác nhận. Không bỏ ca, không đổi thành mock, không nới guard/auth/ref niêm phong để lấy xanh. Không đổi lifecycle Job/EOF/confirmed-empty đã sửa06A.
- Báo cáo ghi đúng code đã sửa và self-test NOT_RUN_CODE_ONLY; sửa mô tả USERBASE/usercustomize sai thành .pth. Bằng chứng Root cũ phân loại source25/pure32/owned17+1/recoveryGET riêng, không nâng thành GUI/full module/độ chính xác37 tham số.

Đầu ra: đúng3file, không file mới; không product runtime. Sau terminal Root đọc diff và kiểm độc lập hữu hạn rồi tiếp tục phần nghiệp vụ CRM báo giá–soạn hợp đồng và M4 Review chứng từL3.