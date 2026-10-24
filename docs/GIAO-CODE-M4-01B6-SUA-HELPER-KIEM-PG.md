# M4-01B6 — Sửa helper kiểm PostgreSQL, giữ nguyên nghiệp vụ

Tiếp tục cùng session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`, CODE_ONLY. Anh đã giao M4 và CRM đã chốt; Claude là coder chính, Root kiểm độc lập. B5 đã terminal thành công và Root/peer đóng diff; lượt này chỉ sửa bộ kiểm, không sửa product.

## 1. Kết quả thực tế trước lượt này

- B5: pure50 đã chạy trên host, **50 PASS, 0 fail/error/skip**. Bốn nhóm độc lập đã đạt: retention, cache nguồn, DOCX và BOQ vật lý. Bộ kiểm Decimal so giá trị chính xác, giữ raw cells; không cộng các lát này thành nghiệm thu toàn M4.
- PostgreSQL đã tạo được M17 sau sửa UNIQUE. Native chạy 10 methods: **8 PASS, 2 ERROR TypeError, 0 fail/skip**. Hai ca lỗi T04 và T05 dừng trước khi gọi `tao_hop_dong`; chưa có bằng chứng luồng đầy đủ/replay muộn và đồng thời của hai ca này đạt.
- Nguyên nhân cụ thể ở `tests/test_m4_01b_pg.py`: `def lam(self, login, ten, **kw)` nhận tên phương thức ở positional `ten`, trong khi lệnh tạo hợp đồng còn có business keyword `ten=...`. Python báo nhận nhiều giá trị cho cùng tham số. Ví dụ T04 dòng 267 và T05 dòng 355.
- Bộ kiểm độc lập PG dừng ở đáp án BOQ gắn nhầm dòng: tệp DEMO nguyên gốc là HM_A `2 × 100`, thành tiền cung cấp `999` ở G2; HM_B `3.5 × 20`, thành tiền `70` ở G3. Root sửa verifier riêng theo XML nguồn và manual oracle, không đổi tệp nguồn hoặc product để khớp đáp án sai.
- Chưa có HTTP/GUI, AI/OCR hoặc toàn M4 nghiệm thu. Cổng hồ sơ C và CRM vẫn tiếp tục theo hàng chờ, sau khi khép kiểm backend.

## 2. Chỉ sửa hai tệp hiện có

1. `tests/test_m4_01b_pg.py`: đổi tên tham số nội bộ của helper `lam` từ `ten` sang tên không trùng business field, ví dụ `ten_lenh`. Đổi các tham chiếu ngay trong helper (`getattr`, thông tin assertion, tuple lưu replay) cho nhất quán. Giữ business keyword `ten` gửi service, call sites, body/key/revision và tuple replay đúng như trước.
2. `docs/BAO-CAO-M4-01B.md`: thêm mục B6, ghi đúng các kết quả Root nêu trên và giới hạn; self-test lượt Claude vẫn NOT_RUN, không tự ghi 10/10 hoặc 8 nhóm độc lập đã đạt.

Giữ đủ và đúng 10 test methods; giữ mọi assertion, Barrier(2), hai connection thật của T05, whole snapshots/replay, manual37/source quotes và kiểm current rights. Không skip, catch/suppress TypeError hoặc lỗi nghiệp vụ, không sửa oracle để né lỗi, không xóa ca.

Product, M17/prefix1–16, native pure50, fixture/vendor/reference, store/guard, quyền/master, CRM/M2/M5/L11 và M9 được bảo vệ. Không tạo tệp mới, sửa file khác hoặc dọn DB/role/attempt.

## 3. Cách làm và bàn giao

Chỉ Read/Glob/Grep/Edit/Write trong quyền Root cấp. Không chạy Bash/Python/Node/AST/import/test/SQL/HTTP/browser/Office/AI/cloud/Git mutation/agent con. Không đọc `.env`, `var/`, thông tin đăng nhập hoặc dữ liệu thật. Không xóa/rename/reset/revert/move/cleanup file, SQL DELETE/DROP/TRUNCATE.

Bàn giao đúng hai diff và ghi rõ 10 methods còn nguyên, helper không còn trùng business `ten`; self-test NOT_RUN. Root freeze và chạy lại các ca PG còn thiếu. Các kiểm pure đã đạt chỉ cần kế thừa khi xác nhận toàn bộ product và bộ pure giữ nguyên; không chạy lại không cần thiết.
