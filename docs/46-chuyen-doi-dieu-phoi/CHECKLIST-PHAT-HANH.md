# Checklist phát hành — CD016-PH

Ngày soạn: 26/10/2026. **Bản để Anh/lead duyệt; chưa thực hiện phát hành hay thao tác kho thật.** Phát hành thường lệ **tối thứ Sáu** lên `chinh`/kho thật. Go-live **M0, M2, M3, M4, M9 cùng một lần**, chỉ khi cả năm qua cổng B; không bật module lẻ. Sửa khẩn dùng đường riêng ở cuối tài liệu. Căn cứ: `CHI-DAO-TU-ANH.md:191–200` (CD-016).

Các bước dưới đây dành cho lead/người vận hành được giao quyền khi có lệnh thực hiện. Checklist không cấp thêm quyền đọc kho thật. SQLite thật chỉ chuyển khi Anh ra lệnh riêng; ngoại lệ nạp Review M4 theo CD-011 không mở rộng sang kho SQLite thật khác (`CLAUDE.md:19–24`; `CHI-DAO-TU-ANH.md:194–195`). Không thấy bản TL 52 trong các tài liệu repo đã tra; quy tắc phát hành lấy từ CD-016, không suy thêm nội dung TL 52.

Quy ước nguồn: đường dẫn ngắn thuộc `docs/46-chuyen-doi-dieu-phoi/`; `CLAUDE.md` ở gốc repo; `docs/QUYET-DINH.md` ghi đủ đường dẫn. Những yêu cầu vận hành chi tiết dưới đây là **checklist đề xuất**, không phải bằng chứng đã làm hoặc đã nghiệm thu.

## 1. Chốt gói và điều kiện trước cửa sổ phát hành

- [ ] Ghi mã đợt, ngày/giờ tối thứ Sáu (giờ Việt Nam), người thực hiện, người quyết định bật/đường lùi; ghi commit đang vận hành và commit ứng viên lên `chinh`. Giờ bắt đầu/kết thúc cụ thể: **chưa rõ**, Anh/lead chốt.
- [ ] Đối chiếu [bảng điều kiện go-live](BANG-DIEU-KIEN-GO-LIVE.md): đủ biên bản cổng B của **cả năm module**, đúng phiên bản/phạm vi phát hành; phiếu cổng A hoặc test xanh không thay cổng B. Thiếu một module → dừng go-live cả gói (`CHI-DAO-TU-ANH.md:197`; `2-PHIEU-KIEM-TRA-CHUC-NANG.md:47–56`).
- [ ] Chốt danh sách pháp nhân sử dụng, dữ liệu cần nạp, phương án quyền, phụ thuộc liên module và mọi điểm còn chờ. **Chưa bật pháp nhân nào** cho tới khi đủ chuỗi ma trận; phải có readiness cho toàn bộ đường truy cập và ma trận do Anh tự tick, Admin công bố (`MTQ-4-CAN-CHOT.md:10`; `THIET-KE-MA-TRAN-THAM-QUYEN.md:185–192`; `CHI-DAO-TU-ANH.md:151–155`).
- [ ] Review đúng phạm vi; lead kiểm diff, chữ Việt, test/skip; áp quy trình review hiện hành, không lấy quy trình review cũ làm điều kiện thay thế (`docs/QUYET-DINH.md:309–311`).
- [ ] Xác nhận đích là **một CSDL PostgreSQL thật chung**, tên CSDL/role khác DEMO. M4 nạp trước; bản Review gốc vẫn dùng tới cổng B M4. Kế hoạch chuyển các kho SQLite thật khác phải được Anh duyệt và ra lệnh chạy riêng (`CHI-DAO-TU-ANH.md:142–144`, `194–195`; `CLAUDE.md:20`).

## 2. Sao lưu trước — CSDL, tệp và SHA256

- [ ] Chọn mốc nhất quán trước phát hành: tạm ngừng nhận mới/job ghi và chờ giao dịch đang chạy kết thúc; ghi thời điểm ngừng ghi. Phạm vi tệp phải đi cùng mốc CSDL, không chỉ sao lưu mã nguồn.
- [ ] Người có quyền sao lưu CSDL PostgreSQL bằng `pg_dump` vào `D:\Claude\Phan mem ho tro ke toan\LUU-TRU\<mã-đợt>\`; lưu đủ thông tin phiên bản/migration và quyền cần khôi phục, không in DSN/mật khẩu. Sao lưu tệp gốc, tệp đính kèm, bản xuất, cấu hình vận hành được phép và bản phần mềm đang chạy; danh mục chính xác **chờ lead chốt**.
- [ ] Tính SHA256 từng bản sao CSDL/tệp, ghi dung lượng, mốc chụp và người thực hiện vào biên bản nội bộ của đợt; kiểm đọc được và thử khôi phục trên môi trường tách biệt. Bản sao có dữ liệu thật không đưa vào test/fixture/DEMO hoặc Cloud (`CLAUDE.md:20–23`). Không tích ô nếu mới chỉ có tệp backup mà chưa thử khôi phục.
- [ ] Nếu đợt có nạp M4: làm đúng CD-011 bước 4 — sao lưu `hop_dong.db` + SHA256 vào `LUU-TRU\m4-hop-dong-db-<ngày giờ>`; chạy thử **bản sao** vào PG tạm, đối chiếu khớp 100%; sau đó mới migration/nạp vào **PG thật chung**, đối chiếu và `pg_dump` sau nạp. Lệch bất kỳ → dừng tại bước đó, không sửa tay (`CHI-DAO-TU-ANH.md:141–144`, `194`).
- [ ] Nếu dự kiến chuyển SQLite thật ngoài ngoại lệ M4: kiểm lệnh riêng của Anh và kế hoạch chuyển đã duyệt. Chưa có → dừng phần chuyển, không tự mở kho nguồn (`CHI-DAO-TU-ANH.md:195`).

## 3. Nâng dữ liệu chỉ thêm

- [ ] Lead xác nhận chuỗi migration đang vận hành là tiền tố nguyên vẹn của chuỗi ứng viên: giữ nguyên byte/định nghĩa/checksum migration cũ, chỉ append migration mới; không sửa lịch sử để khớp môi trường (`THIET-KE-MA-TRAN-THAM-QUYEN.md:67`; `M2-BAN-RA-KIEM-KE.md:38`).
- [ ] Chạy thử toàn bộ chuỗi nâng trên bản sao tách biệt; kiểm khóa, tổng tiền/đơn vị, số dòng, tham chiếu và khả năng dùng lại bản ứng dụng trước. Ghi kết quả tương thích làm căn cứ chọn đường lùi; không mặc định migration chỉ thêm đồng nghĩa bản cũ chắc chắn chạy được.
- [ ] Khi được phép chạy thật, ghi migration trước/sau và kết quả từng bước. Không xóa bảng/cột/dòng, không chạy down migration. Nạp dữ liệu theo công cụ/kế hoạch đã review; đối chiếu sai → dừng (`CHI-DAO-TU-ANH.md:141–142`; `CLAUDE.md:18`).
- [ ] Không seed DEMO, không tự điền ma trận thật, không đổi cấu hình kết nối ngoài phạm vi được giao (`THIET-KE-MA-TRAN-THAM-QUYEN.md:187–190`).

## 4. Test trước khi bật — theo CLAUDE.md mục 5

Lead chạy trên môi trường DEMO/test tách kho thật. Codex worker không mở server/PostgreSQL (`CLAUDE.md:24`). Đây là **lệnh tham chiếu**, chưa chạy trong lát tài liệu này:

```powershell
# Bộ test theo module, dùng runtime DEMO; lưu kết quả riêng mỗi lượt.
python -X utf8 tools\chay_test_theo_module.py . --runtime "D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\var\web\crm-demo\runtime.local.json" --ra "$env:TEMP\kq.json"

# Bộ test PostgreSQL trên cụm DEMO, thêm tham số theo CLAUDE.md:48.
python -X utf8 tools\chay_test_theo_module.py . --runtime "D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\var\web\crm-demo\runtime.local.json" --pg-demo "D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\var\web\crm-demo\ket-noi.local.json" --gioi-han 900 --ra "$env:TEMP\kq-pg.json"
```

- [ ] Chạy nền qua cơ chế của lead cho lệnh dài. Chỉ **một lượt `--pg-demo`** và không chạy bộ PG khác song song trên cùng cụm; giữ nguyên cơ chế sổ sở hữu CSDL test của runner, không dọn tay CSDL/role (`CLAUDE.md:47–48`; `NEN-TEST-PG.md:9–11`).
- [ ] Ghi ok/ERROR/FAIL/skip/TREO theo module và so **`ids_loi`**, độ phủ, số skip với nền PG mới nhất. Tại lúc soạn: **v5**, `nen-test-hop-nhat-pg-v5.json`, **3214 ok / 20 ERROR / 63 FAIL / 78 skip / 0 treo**; v5 là kết quả cả bộ có thay ba module bằng lượt chạy lại đã ghi rõ. Trước mỗi đợt phải đọc lại `NEN-TEST-PG.md` để lấy nền hiện hành (`NEN-TEST-PG.md:71–75`).
- [ ] Không có mã lỗi mới; không tăng skip/thiếu fixture làm mất kiểm chứng. Xử lý từng mã chập chờn bằng lượt chạy lại có ghi nhận; không tự thêm lỗi mới vào nền để cho qua. Lượt cả bộ sau v5 chưa thay nền v5; ca timeout runner chạy lại lúc máy rảnh đã đạt 51/51 (`TRANG-THAI.md:496–499`, `514–515`; `CLAUDE.md:40`).
- [ ] Lead tự thử luồng nghiệp vụ và ca âm về quyền/pháp nhân, xem/tải raw, trích dẫn, hạn mức, replay/thu hồi quyền, đối chiếu liên module. M9 chỉ Local AI; không Cloud kể cả Mask. Không gọi thuế/Junsky/Request thật hoặc Word COM bằng bước test này (`THIET-KE-MA-TRAN-THAM-QUYEN.md:191`; `CHI-DAO-TU-ANH.md:183–185`; `CLAUDE.md:21–24`).
- [ ] Lưu kết quả đúng commit ứng viên, đối chiếu lại cổng B năm module; còn lỗi chặn hoặc bằng chứng thiếu → dừng trước bật.

## 5. Bật cả gói và kiểm sau bật

- [ ] Lead xác nhận sao lưu/khôi phục thử, migration, đối chiếu nạp, test và cổng B đều đủ; ghi quyết định phát hành. Cập nhật `chinh` đúng commit đã kiểm và triển khai nguyên gói M0/M2/M3/M4/M9 (`CHI-DAO-TU-ANH.md:196–197`).
- [ ] Kiểm đúng PG thật chung, quyền và bản cấu hình được duyệt; Admin chỉ bật ma trận cho pháp nhân đã đủ readiness và snapshot do Anh tick. Nếu readiness chưa đủ thì dừng, không bật một phần đường quyền hoặc quay về fallback cũ (`THIET-KE-MA-TRAN-THAM-QUYEN.md:185–192`; `docs/QUYET-DINH.md:337–355`).
- [ ] Mở lại nhận mới/job theo phạm vi đã duyệt. Kiểm cả năm module mở được; số việc chờ/danh sách đúng phạm vi; vai khác pháp nhân không đọc/tải được; nhật ký và tệp căn cứ truy được. Kiểm M3 hóa đơn–hợp đồng/đợt thu, M4 lịch sử/seal, M9 trích dẫn và snapshot có mốc theo cổng B đã duyệt.
- [ ] Đối chiếu lại số dòng, tổng tiền theo đơn vị, khóa và mốc nguồn sau bật; không nhân đôi khi nạp/replay. Với M4: chạy nạp cuối phần phát sinh trước khi chuyển hẳn khỏi Review gốc, đối chiếu và lưu biên bản (`CHI-DAO-TU-ANH.md:141–143`).
- [ ] Theo dõi trong cửa sổ do lead chốt: lỗi truy cập, job, dữ liệu thiếu/lệch, log chứa bí mật; ghi giờ kiểm, người kiểm, kết quả. Sai quyền, sai đích CSDL hoặc lệch tiền/khóa → ngừng ghi và áp đường lùi; không mở một module riêng để tiếp tục go-live.

## 6. Đường lùi — không phá dữ liệu

- [ ] **Trước bật:** nếu backup, migration, đối chiếu hoặc test không đạt, giữ gói cũ vận hành theo phương án tương thích đã thử; không đánh dấu phát hành thành công, không hạ schema.
- [ ] **Sau bật:** tạm ngừng ghi/job của cả gói, ghi mốc và giữ bản sao trạng thái phát sinh sau bật cùng nhật ký; xác định phạm vi ảnh hưởng. Không trỏ bản cũ vào schema mới khi chưa chứng minh tương thích.
- [ ] Nếu tương thích đã thử: đưa cả gói ứng dụng về commit trước, giữ schema chỉ thêm và kiểm lại quyền/dữ liệu trước mở ghi. Nếu chưa tương thích: giữ ngừng ghi; khôi phục CSDL + tệp cùng mốc backup vào **đích phục hồi tách biệt**, kiểm SHA/đối chiếu rồi mới chuyển kết nối theo quyết định của Anh/lead. Giữ nguyên CSDL gặp lỗi, không DROP/ghi đè; không `reset --hard`/force push (`CLAUDE.md:18`).
- [ ] Giao dịch sinh sau backup phải được đối soát và xử lý có biên bản trước mở lại; **không tự nhập lại hoặc chấp nhận mất dữ liệu**. Thời gian phục hồi tối đa/mốc mất dữ liệu được chấp nhận: **chưa rõ**, cần Anh/lead chốt.
- [ ] Ma trận đã bật: ưu tiên công bố snapshot trước như **phiên bản mới có audit**; không tự tắt để quay về quyền legacy rộng hơn (`THIET-KE-MA-TRAN-THAM-QUYEN.md:192`).
- [ ] SQLite nguồn giữ nguyên, chỉ đọc; bản Review gốc đóng băng code và vẫn được dùng tới cổng B M4. Không coi việc trỏ lại SQLite cũ là phục hồi đầy đủ sau khi đã phát sinh ghi ở PG; chưa có cách đối soát phần phát sinh → dừng và ghi “Cần Anh/lead” (`CHI-DAO-TU-ANH.md:143`, `195`).

## 7. Biên bản và sửa khẩn

- [ ] Ghi trong biên bản nội bộ đợt: mã đợt/giờ/người duyệt và thực hiện; commit trước/sau; năm kết luận cổng B; phạm vi pháp nhân/phiên bản ma trận; migration trước/sau; vị trí backup + SHA256 + kết quả khôi phục thử; số dòng/tổng tiền/khóa trước–sau; lệnh test/nền/`ids_loi`/skip/TREO; kết quả kiểm sau bật; quyết định tiếp tục/đường lùi và phần phát sinh đã xử lý. Không dán DSN, mật khẩu hay dữ liệu thật vào repo/chat (`TRANG-THAI.md:382`; `CLAUDE.md:20–23`).
- [ ] Lead cập nhật trạng thái, điểm tồn đọng và người phụ trách. Checklist còn ô chưa hoàn tất phải ghi lý do và quyết định, không mặc định đã đạt.
- [ ] **Sửa khẩn — đường riêng:** ghi sự cố và lý do không chờ thứ Sáu; lead chuẩn bị bản vá nhỏ/commit riêng, review, sao lưu + SHA, migration append nếu có, test so nền, triển khai và kiểm sau bật, đường lùi, biên bản. Người cho phép, tiêu chí “khẩn”, nhánh và giờ thực hiện **chưa rõ**, cần Anh/lead chốt. Sửa khẩn không miễn các cổng dữ liệu/quyền và không dùng để go-live module lẻ trước khi đủ năm cổng B (`CHI-DAO-TU-ANH.md:196–197`).

## Cần Anh/lead

- Chốt giờ/cửa sổ tối thứ Sáu, người quyết định bật/đường lùi, thời gian kiểm sau bật và mục tiêu phục hồi; chốt cơ chế sửa khẩn.
- Chốt danh sách tệp/cấu hình cần sao lưu, công cụ/lệnh triển khai–phục hồi thực tế và bằng chứng đã thử. Tài liệu này không xác nhận đã có các công cụ đó.
- Bổ sung bằng chứng cổng A/B và checklist M0; hoàn thành các điểm mở ở bảng go-live. Xác nhận readiness ma trận đủ cho năm module trước khi bật pháp nhân đầu tiên.
- Lệnh chuyển kho SQLite thật ngoài ngoại lệ CD-011 vẫn phải riêng; bản kế hoạch và checklist không thay lệnh chạy.
