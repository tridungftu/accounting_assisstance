# M4-01B5 — Khép lỗi phát hiện khi kiểm thực tế trên Windows

Lượt CODE_ONLY tiếp nối cùng session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`. Anh đã giao triển khai M4 và CRM đã chốt. B5 thay lượt sửa B4 chưa dispatch; giữ tài liệu B4 làm lịch sử, không triển khai B4 riêng.

## 1. Căn cứ kiểm thực tế

- Pure50 chạy thực tế sau B3: 47 PASS, 3 ERROR, 0 failure, 0 skip. Child đã dừng, frozen413 không thay đổi. Bốn nhóm độc lập chưa chạy; không gọi B hay toàn M4 PASS.
- Ca `BoNapGhim.test_dung_pin_nap_duoc` ghi fixture bằng `Path.write_text` mặc định, Windows tạo CRLF trong khi SHA mong đợi là literal LF. `nap_ghim` chặn đúng; chỉ sửa cách tạo fixture, giữ kiểm pin nghiêm ngặt.
- Hai ca GiuStaging báo WinError5 tại `os.link`. Kiểm riêng cùng bytes DEMO: sandbox chặn, host Windows tạo được, original no-delete guard hoạt động, nguồn và hardlink được giữ. Không sửa store/guard hoặc hạ oracle. Root chạy lại trên host; kiểm hardlink riêng không đồng nghĩa bộ test đã PASS.
- Native PostgreSQL10 và independent8 đã khởi chạy trên database DEMO mới giữ lại. Native dừng tại setUpClass: 0 method nghiệp vụ, InvalidForeignKey/SQLSTATE42830. Independent cũng dừng trước các nhóm nghiệp vụ. Không ghi nhận PASS hoặc skip thành đạt.
- Root kiểm chẩn đoán riêng: dựng neutral16 thành công, nâng M17 lỗi `REFERENCED_KEYS_NOT_UNIQUE`, bảng tham chiếu `hop_dong`. Child dừng, source347 live/frozen413 giữ nguyên. Hai agent độc lập cùng khoanh đúng FK bên dưới; không phải lỗi PostgreSQL chưa cài.

## 2. Sửa tối thiểu — chỉ ba tệp hiện có

### A. `src/kho_tri_thuc/m4/sql_m17.py`

M17 đang tạo `m4.ho_so_hop_dong` với FK `(phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong(phap_nhan_id,id)`. NeutralCOMMON1–16 chưa có matching UNIQUE; UNIQUE đó chỉ nằm trong nhánh M13 legacy đầy đủ không thuộc chuỗi COMMON hiện hành. UNIQUE `(id,du_an_id)` M17 hiện có không thay cho cặp trên.

Thêm một constraint UNIQUE `(phap_nhan_id,id)` cho `master.hop_dong` trong M17, trước khi tạo bảng chứa FK. Dùng tên constraint mới rõ thuộc M4, tránh trùng tên legacy. Giữ FK hai cột, discriminator/module quyền, các FK khác và thứ tự phụ thuộc. Không đổi `pg_migrations.py`, byte prefix1–16, registryCOMMON, checksum lịch sử, schema M9, seed hoặc master song song. Không thay FK bằng id đơn để né lỗi.

M17 này chưa qua cổng kiểm: mọi lần dựng thất bại đã rollback transaction, DB/role/files được giữ. Không sửa database lịch sử hoặc buộc ghi checksum đã áp dụng; Root sẽ kiểm trên DB DEMO mới.

### B. `tests/test_m4_01b_tinh.py`

Helper `_goi`: ghi `__init__.py` và `con.py` bằng UTF-8 bytes xác định rõ LF, ví dụ `write_bytes(text.encode('utf-8'))`. Giữ literal SHA mong đợi và positive/negative khác nhau, đủ 50 methods và mọi assertion. Không lấy hash file vừa ghi thay đáp án; không skip/catch/suppress lỗi, monkeypatch `os.link`, quyền, no-delete guard hoặc loader.

Không cần thêm test mô phỏng SQL để thay bằng chứng runtime. Bộ PG10 hiện có cùng independent16→17 sẽ kiểm lỗi migration thực sự; giữ nguyên các định nghĩa đó cho Root chạy.

### C. `docs/BAO-CAO-M4-01B.md`

Thêm mục B5 tách rõ code sửa, 47/50 pure, lỗi môi trường sandbox/host, PostgreSQL thất bại trước nghiệp vụ và các phần NOT_RUN. Self-test của Claude vẫn NOT_RUN. Giữ lịch sử B3 và giới hạn native/fake-AI/GUI; không gọi nguồn hoàn chỉnh hoặc toàn module đã nghiệm thu.

## 3. Giới hạn và bàn giao

Chỉ ba tệp trên được sửa, không tạo file mới. Mọi product/test khác, nguồn vendor/reference, store/guard, PG suite, prefix1–16, CRM/M2/M5/L11 và M9 được bảo vệ. Không xóa/rename/reset/revert/cleanup, SQL DELETE/DROP/TRUNCATE hoặc bật cloud/Office/network.

Chỉ dùng file tools Root cấp; không Bash/Python/Node/AST/product import/test/SQL/browser/Git mutation/agent con. Không đọc `.env`, `var/`, credentials hoặc dữ liệu thật. Handoff này đủ căn cứ chẩn đoán, không cần đọc artifact kiểm riêng.

Bàn giao delta ba tệp, nêu đúng vị trí UNIQUE trước FK và fixture LF, giữ 50 methods; không tự khai PASS. Root freeze, review độc lập, chạy lại pure/native PostgreSQL/independent rồi mới giao Cổng hồ sơ GUI. Toàn bộ Review/PDF/nghiệm thu–công nợ/Request và CRM vẫn trong hàng chờ đã được Anh giao.
