# M4-01B4 — Sửa fixture bộ kiểm trên Windows

Phạm vi đã được Anh giao: tiếp tục M4 và CRM đã chốt, Claude Code là coder chính. Đây là lượt sửa nhỏ tiếp nối B3 trong cùng session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`.

## 1. Kết quả thực tế và nguyên nhân

- Root đã chạy bộ pure50 sau B3: 50 ca chạy, 47 PASS, 3 ERROR, 0 skip. Child đã dừng; bản frozen413 giữ nguyên SHA trước/sau. Bốn nhóm độc lập, PostgreSQL và GUI chưa chạy trong lượt này. Không được gọi B hoặc toàn M4 hoàn tất.
- `BoNapGhim.test_dung_pin_nap_duoc`: helper `_goi` ghi `GIA_TRI = 1\n` bằng `Path.write_text` mặc định. Windows đổi LF thành CRLF, trong khi test so SHA với literal LF. Lõi `nap_ghim` từ chối đúng bytes sai pin; không sửa hoặc nới bộ nạp.
- Hai ca `GiuStaging` lỗi tại `store.write_immutable → os.link`, WinError 5. Root đã kiểm riêng cùng tệp DEMO: sandbox từ chối, chạy trên host tạo hardlink thành công, bytes khớp và original no-delete guard vẫn hoạt động. Chưa phải bằng chứng bộ test đã PASS trên host. Không sửa store, guard hoặc oracle để né lỗi môi trường.
- Root sẽ chạy lại bộ kiểm trên host sau khi đóng sửa fixture; giữ toàn bộ nguồn, staging, attempts và tệp chẩn đoán.

## 2. Chỉ sửa hai tệp

1. `tests/test_m4_01b_tinh.py`: ghi fixture Python trong `_goi` bằng bytes UTF-8 xác định rõ LF (ví dụ `write_bytes(text.encode('utf-8'))`). Cả `__init__.py` và `con.py` nên có bytes xác định. Giữ literal SHA mong đợi trong test, positive và negative riêng, đủ 50 test methods và toàn bộ assertion. Không sửa test thành hash chính file vừa ghi để che lỗi, không skip, không catch/suppress lỗi sản phẩm, không monkeypatch quyền/guard/`os.link`.
2. `docs/BAO-CAO-M4-01B.md`: thêm mục B4, phân biệt lỗi fixture, lỗi quyền sandbox và kết quả Root thực tế nêu trên; self-test của lượt Claude vẫn NOT_RUN. Giữ báo cáo lịch sử và mọi giới hạn B3.

Mọi tệp khác được bảo vệ, gồm product, PG test, migrations, vendor/reference, store, guard và tài liệu CRM. Không tạo tệp mới ngoài hai tệp đã có; không xóa/đổi tên tệp, cleanup hoặc SQL DELETE/DROP/TRUNCATE.

## 3. Cách làm và bàn giao

CODE_ONLY: chỉ dùng file tools được Root cấp. Không Bash, Python, Node, AST, product import, test, SQL, browser, network, Office/AI, Git mutation hoặc agent con. Không đọc `.env`, `var/`, thông tin đăng nhập hay dữ liệu thật. Căn cứ nguồn đã có trong workspace và handoff này đủ cho sửa nhỏ.

Bàn giao chính xác delta hai tệp; báo 50 methods còn giữ và self-test NOT_RUN. Root sẽ freeze, kiểm diff và chạy độc lập; không lấy tự khai của Claude thay bằng chứng kiểm.
