# Bảng điều kiện go-live — M0, M2, M3, M4, M9

Ngày đối chiếu: 26/10/2026 · CD016-PH. **Chưa đủ căn cứ xác nhận go-live.** Cả năm module phải qua cổng B và vận hành cùng một lần phát hành tối thứ Sáu lên `chinh`/kho thật; không bật module lẻ. Đích là **một CSDL PostgreSQL thật chung**, M4 nạp trước (`CHI-DAO-TU-ANH.md:194–197`). Đây là bảng tổng hợp cho lead duyệt, chưa phải lệnh nạp dữ liệu, bật quyền hay phát hành.

Quy ước nguồn: đường dẫn ngắn thuộc `docs/46-chuyen-doi-dieu-phoi/`; `CLAUDE.md` ở gốc; tài liệu ngoài thư mục này ghi đường dẫn từ gốc repo. `tệp:dòng` chỉ dòng bắt đầu căn cứ; số dòng theo bản repo khi soạn. Không đọc kho thật; danh mục/số lượng thực tế cần nạp **chưa kiểm kê**. Chưa có bản TL 52 trong tài liệu repo đã tra, chỉ áp phần CD-016 được ghi tại `CHI-DAO-TU-ANH.md:191–200`.

Cổng A là kiểm chức năng sớm, cổng B là nghiệm thu theo checklist; test đạt hay phiếu nháp không thay biên bản cổng B (`2-PHIEU-KIEM-TRA-CHUC-NANG.md:3–6`, `47–56`). “Chưa rõ” nghĩa là chưa có bằng chứng đủ trong nguồn đã đối chiếu, không khẳng định phần đó chưa từng được làm. Khi có cập nhật mới, lead phải bổ sung nguồn/phiên bản và kết luận của Anh.

## M0

| Điều kiện | Hiện trạng / việc cần hoàn tất | Nguồn (tệp:dòng) |
|---|---|---|
| Phạm vi | M0 thuộc đợt go-live chung; phạm vi nghiệm thu M0 riêng **chưa rõ**, không đồng nhất M0 với CRM hay trang chủ lưới icon. | `CHI-DAO-TU-ANH.md:197`; `TRANG-THAI.md:186` |
| Cổng A / cổng B | **Chưa rõ / chưa rõ**: chưa có phiếu và kết luận của Anh cho toàn M0 trong căn cứ đã đọc. Dòng lịch sử chỉ cho biết M0 không có gói nhập riêng và không đủ cơ sở kết luận hoàn tất. | `TRANG-THAI.md:186`; `2-PHIEU-KIEM-TRA-CHUC-NANG.md:47` |
| Cần Anh/lead | Lead xác định phạm vi M0, checklist và bằng chứng hai cổng; xác nhận phần nguồn chung/danh mục/mapping nào thuộc M0 trong lần phát hành. A1–A3 về nguồn/phần nền đã được Anh chốt, không hỏi lại như điểm chưa quyết. | `TRANG-THAI.md:186`; `docs/BINDING-M2-CORE-SAU-CRM03.md:24`; `docs/QUYET-DINH.md:337` |
| Dữ liệu thật cần nạp | **Chưa rõ** gói nạp M0 cụ thể. Tài liệu binding mô tả raw/receipt/snapshot/derivative và ánh xạ nguồn dùng chung; cần lead xác nhận danh mục thật, chủ dữ liệu, profile/công ty nguồn → pháp nhân trước nạp. Không suy có dữ liệu thật chỉ từ schema. | `docs/BINDING-M2-CORE-SAU-CRM03.md:26`; `docs/QUYET-DINH.md:340`; `CHI-DAO-TU-ANH.md:195` |
| Việc còn lại | Xác định phần đã tích hợp và phần phải nghiệm thu trên commit phát hành; hoàn thành đường quyền nguồn/raw/mapping và kiểm chuỗi MTQ-NEN, sau đó lập phiếu A/B cho đúng phạm vi M0. Trạng thái hoàn thành toàn M0 **chưa rõ**. | `TRANG-THAI.md:186`; `KK-MTQ4-LIEN-MODULE.md:32`; `docs/QUYET-DINH.md:341` |
| Ma trận thẩm quyền | **Chưa bật pháp nhân nào** tới khi đủ chuỗi. Phạm vi nguồn do Admin cấp tường minh; nguồn nhiều pháp nhân phải đủ quyền tất cả. Cần MTQ-NEN và readiness bao phủ nguồn chung/đường legacy, không chỉ giao diện. | `MTQ-4-CAN-CHOT.md:10`; `docs/QUYET-DINH.md:340–342`; `docs/QUYET-DINH.md:354` |

## M2 · Mua hàng / Hóa đơn mua vào và nguồn bán ra cho M3

| Điều kiện | Hiện trạng / việc cần hoàn tất | Nguồn (tệp:dòng) |
|---|---|---|
| Phạm vi | Giữ M2 là Mua hàng/Hóa đơn mua vào; bổ sung đường nguồn hóa đơn bán ra cho M3, dùng kho chung. Không coi reader đọc được chiều bán là đã promote/kiểm quyền xong. | `CHI-DAO-TU-ANH.md:136`; `M2-BAN-RA-KIEM-KE.md:3`; `M2-BAN-RA-KIEM-KE.md:60` |
| Cổng A / cổng B | **Chưa rõ / chưa rõ** biên bản toàn M2. M2e đã thử bộ tải giả; M2f trên cổng thuế thật vẫn là việc của Anh cần lệnh riêng. Test/code các lát không chứng minh đã qua cổng B M2. | `TRANG-THAI.md:116`; `TRANG-THAI.md:313`; `4-KE-HOACH-LEAD.md:83` |
| Cần Anh/lead | Nguồn bán ưu tiên (thuế/XML/ZIP/cả hai), người nhận/xem và quyền raw theo pháp nhân; mẫu XML/căn cứ thuế, điều chỉnh/thay thế/hủy/ngoại tệ và nguồn quyết định khi lệch. Lead xác nhận phần công nợ/đường nhận K2 còn thiếu trong kiểm kê cũ. Quyền vận hành bộ tải: **chỉ Admin đã chốt**, phải áp theo QD-08 thay quy tắc M2k trước đó. | `M2-BAN-RA-KIEM-KE.md:54–58`; `TRANG-THAI.md:479`; `4-KE-HOACH-LEAD.md:115`; `docs/QUYET-DINH.md:300`; `docs/QUYET-DINH.md:352` |
| Dữ liệu thật cần nạp | Nguồn hóa đơn mua/bán, XML/bảng kê và liên kết nguồn/phiên bản; profile, công ty nguồn, mapping pháp nhân; thành phần tiền/tiền tệ, quan hệ hóa đơn đủ cho M3. Bộ nguồn, kỳ và số lượng thật **chưa rõ**; chỉ nạp khi phạm vi/lệnh được duyệt, không tự gọi thuế. Hồi cứu: kế hoạch yêu cầu thử một tháng trước 33 tháng. | `M2-BAN-RA-KIEM-KE.md:42–49`; `M2-BAN-RA-KIEM-KE.md:56–58`; `4-KE-HOACH-LEAD.md:114`; `CHI-DAO-TU-ANH.md:195` |
| Việc còn lại | BR4/BR4b reader đã gộp; cần lead cập nhật BR1/2/3/5/6/7/8/9 theo thứ tự quyền → SQL/capture → tiền/quan hệ → bộ tải/API/UI, không coi kế hoạch BR0 là kết quả. Hoàn thiện cổng A/B và ca thật do Anh thực hiện khi có lệnh. | `TRANG-THAI.md:409`; `TRANG-THAI.md:464`; `M2-BAN-RA-KIEM-KE.md:36–52`; `4-KE-HOACH-LEAD.md:83` |
| Ma trận thẩm quyền | **Chưa bật pháp nhân nào**. Còn chuỗi MTQ nguồn/M2, resolver scope/company, RLS và service/raw; nguồn nhiều pháp nhân phải kiểm đủ. 03B kiểm từng nguồn, không dùng quyền M4 để đọc M2. A1/B9/B10 đã chốt; còn triển khai và kiểm chứng. | `MTQ-4-CAN-CHOT.md:10`; `KK-MTQ4-LIEN-MODULE.md:62–69`; `docs/QUYET-DINH.md:340`; `docs/QUYET-DINH.md:352–353` |

## M3 · Hóa đơn bán ra & doanh thu BĐS

| Điều kiện | Hiện trạng / việc cần hoàn tất | Nguồn (tệp:dòng) |
|---|---|---|
| Phạm vi | Theo thiết kế v2/CD-013 và bổ sung CD-014: tách cơ sở doanh thu/thuế, ba đẳng thức, chuyển lớp theo mốc. Chưa sinh bút toán có số tài khoản; lịch phân bổ chỉ kiểm chéo thuộc M10. | `CHI-DAO-TU-ANH.md:159–176`; `PHIEU-CONG-A-M3.md:22` |
| Cổng A / cổng B | **Cổng A: nháp, chưa nghiệm thu**; phiếu ghi chưa có màn để thử và thiếu bảng mốc §17. **Cổng B: chưa rõ**, không có biên bản nghiệm thu trong căn cứ này. | `PHIEU-CONG-A-M3.md:3`; `PHIEU-CONG-A-M3.md:82–86`; `TRANG-THAI.md:477` |
| Cần Anh/lead | Bảng mốc §17; #7 cơ sở thuế, #8 mapping Junsky (phụ thuộc M10), #10 file xuất, #11 nguồn/ID biên bản và policy nhà ở, #12 mẫu K0/phương pháp A/B. Thêm tiêu chí “đủ đợt”, hóa đơn chung nhiều HĐ và phân chia giá trị. Không dùng 15 câu checklist M3 cũ thay các điểm mở v2. | `PHIEU-CONG-A-M3.md:75`; `PHIEU-CONG-A-M3.md:83`; `TRANG-THAI.md:406`; `CHI-DAO-TU-ANH.md:160–165` |
| Dữ liệu thật cần nạp | Hóa đơn bán qua M2; hợp đồng/phiên bản/cơ sở thuế, lô, khách; đợt thu/tiền liên kết; mốc dự kiến/thực tế và biên bản bàn giao CRM đúng HĐ/lô; policy và tham số phân bổ đã duyệt. Mapping Junsky và K0 còn chờ; danh sách/số lượng thực **chưa rõ**. | `PHIEU-CONG-A-M3.md:26–28`; `PHIEU-CONG-A-M3.md:50–58`; `PHIEU-CONG-A-M3.md:69`; `CHI-DAO-TU-ANH.md:164–165` |
| Việc còn lại | M3-1a/1b/1c/1d đã gộp qua M0042/44/46; còn bảng mốc, máy chuyển lớp/sự kiện bàn giao, tham số/phần màn hình và nối nguồn bán M2, cập nhật phiếu A rồi nghiệm thu B. Cần lead xác nhận phạm vi M3-2/M3-3/M3-4/M3-5 thực tế ở commit phát hành. | `TRANG-THAI.md:387`; `TRANG-THAI.md:409`; `TRANG-THAI.md:451`; `TRANG-THAI.md:477`; `4-KE-HOACH-LEAD.md:243–246`; `PHIEU-CONG-A-M3.md:84` |
| Ma trận thẩm quyền | **Chưa bật pháp nhân nào**. Phải nối quyền M3/K5 và phạm vi nguồn M2/CRM, thử vai chỉ xem không duyệt/xuất và pháp nhân B không thấy hồ sơ/số chờ A; danh mục ô quyền M3 và readiness triển khai đầy đủ **chưa rõ**. | `MTQ-4-CAN-CHOT.md:10`; `PHIEU-CONG-A-M3.md:69–71`; `THIET-KE-MA-TRAN-THAM-QUYEN.md:189` |

## M4 · Nghiệm thu & chi phí dự án

| Điều kiện | Hiện trạng / việc cần hoàn tất | Nguồn (tệp:dòng) |
|---|---|---|
| Phạm vi | Chép đủ tám màn Review trong khung icon, giữ 02C/03A/03B/04 đang có; chỉ đổi lớp dữ liệu sang PG. M4 nạp trước vào PG thật **chung** thay đích riêng trong CD-011 cũ. | `CHI-DAO-TU-ANH.md:137–140`; `CHI-DAO-TU-ANH.md:194` |
| Cổng A / cổng B | 03B có checklist đã được Anh duyệt; **cổng A toàn M4 tám màn: chưa rõ/chưa có phiếu hoàn chỉnh trong căn cứ**, UI0 còn chờ cổng A trang chủ. **Cổng B: chưa rõ**; Review gốc vẫn dùng tới cổng B M4. Duyệt checklist 03B không thay nghiệm thu toàn M4. | `TRANG-THAI.md:169`; `TRANG-THAI.md:481`; `CHI-DAO-TU-ANH.md:143–145` |
| Cần Anh/lead | Ánh xạ `ma_hd → hợp đồng/pháp nhân/dự án` chặn nạp thật; chốt phạm vi tệp đính kèm CD3; xử lý hai phụ lục cùng ngày hiệu lực (lead từng khuyến nghị giữ cờ “cần xem lại”). Lũy kế lịch sử Review và sổ trang OCR **đã chốt**, không còn là câu hỏi mở. | `TRANG-THAI.md:482`; `TRANG-THAI.md:480`; `TRANG-THAI.md:390`; `docs/QUYET-DINH.md:313–329` |
| Dữ liệu thật cần nạp | `hop_dong.db` Review: hợp đồng, phụ lục/BOQ, đợt/khối lượng/lịch sử theo công cụ đã review và mapping được duyệt; tệp đính kèm còn chờ phạm vi. Trước chuyển hẳn nạp lần cuối phần phát sinh. Số dòng/tổng thực **chưa rõ**; đối chiếu từng bảng, tổng HĐ/BOQ/từng đợt, đơn vị và dòng lỗi, lệch thì dừng. | `CHI-DAO-TU-ANH.md:137–143`; `TRANG-THAI.md:380`; `TRANG-THAI.md:465`; `CHI-DAO-TU-ANH.md:194` |
| Việc còn lại | CD1/CD2 đã gộp nhưng chưa có biên bản nạp thật; thực hiện sao lưu + SHA → thử bản sao → nạp/đối chiếu/pg_dump theo CD-011 khi đủ mapping và quyền. Hoàn thành CD3/UI0/tám màn, kiểm parity và quyền, phiếu A/B. DL5c đã gộp: kiểm seal thắng, không cộng trùng, đúng đơn vị/ngày, nguồn REVIEW_CHEP. | `TRANG-THAI.md:387`; `TRANG-THAI.md:424–425`; `CHI-DAO-TU-ANH.md:142–146`; `CHI-DAO-TU-ANH.md:200`; `TRANG-THAI.md:480–482`; `TRANG-THAI.md:495`; `docs/QUYET-DINH.md:313–319` |
| Ma trận thẩm quyền | **Chưa bật pháp nhân nào**. Còn MTQ-4f/4h và liên module 03B/readiness; triển khai các quyết định đã chốt: PDF 02C theo ô Sửa, 03A xem PDF cần hai ô, tải mẫu cần dự án, ngoại tệ thiếu tỷ giá ghim bị chặn, 03B kiểm từng nguồn. | `MTQ-4-CAN-CHOT.md:10`; `THIET-KE-MA-TRAN-THAM-QUYEN.md:224–227`; `KK-MTQ4-LIEN-MODULE.md:68`; `docs/QUYET-DINH.md:347–353` |

## M9 · Vốn vay & đầu tư tài chính — phạm vi kho hợp đồng vay

| Điều kiện | Hiện trạng / việc cần hoàn tất | Nguồn (tệp:dòng) |
|---|---|---|
| Phạm vi | Đã mở lại theo CD-015: kho HĐ vay, hỏi đáp chỉ Local AI, snapshot Sheet và báo cáo lãi suất; không dùng trạng thái “M9 dừng” của các tài liệu cũ. Không tính lại sổ vay/lịch trả/lãi. | `CHI-DAO-TU-ANH.md:179–186`; `CLAUDE.md:21` |
| Cổng A / cổng B | **Cổng A: phiếu nháp**, chưa có màn/CSDL theo thiết kế mới, lưu trữ/màn vẫn chờ duyệt. **Cổng B: chưa rõ**, chưa có biên bản nghiệm thu trong nguồn; duyệt bố cục nháp không phải nghiệm thu phần mềm. | `PHIEU-CONG-A-M9.md:3`; `PHIEU-CONG-A-M9.md:95`; `TRANG-THAI.md:511` |
| Cần Anh/lead | Phiếu C1: loại tài liệu, quyền Hỏi/Kéo ngay/Lập–Xuất báo cáo/ghi nhận Anh duyệt gửi, lịch/giờ kéo, Sheet/tab/tài khoản dịch vụ và mapping, ngày/giờ báo cáo tháng, danh mục nhiều đồng tiền, tiêu chí đủ hồ sơ/việc chờ. Lead chốt cách ký JWT (thư viện hay thuần Python). Câu gộp sổ ABBYY trong phiếu cũ **đã được QD-06 thay thế**. | `PHIEU-CONG-A-M9.md:64–77`; `TRANG-THAI.md:512`; `docs/QUYET-DINH.md:323–329` |
| Dữ liệu thật cần nạp | HĐ tín dụng/khế ước/phụ lục/bảo đảm/thông báo lãi theo danh mục được Anh duyệt; tệp gốc/phiên bản, pháp nhân/ngân hàng/mã khoản vay, trích dẫn; snapshot Sheet có mốc và nguồn chỉ đọc. Chưa rõ bộ hồ sơ/số lượng, Sheet/tab/tài khoản cụ thể. Khóa chỉ ứng dụng đọc lúc chạy, không đọc qua công cụ; không nạp thật vào DEMO/test. | `PHIEU-CONG-A-M9.md:28–31`; `PHIEU-CONG-A-M9.md:38–48`; `PHIEU-CONG-A-M9.md:70–73`; `CHI-DAO-TU-ANH.md:185`; `CLAUDE.md:23` |
| Việc còn lại | Đã gộp các phần thuần OCR/tìm/hỏi/snapshot/báo cáo; M9-2d lấy số dư/lãi suất từ snapshot có mốc, không qua AI. Còn kho bền/CSDL, sáu màn/API/quyền, Google API chỉ đọc/lịch kéo và lịch báo cáo, trích dẫn mở đúng trang/nguồn; cập nhật phiếu vì OCR chung và hỏi số liệu đã tiến thêm sau nháp. Hoàn thiện A rồi B. | `PHIEU-CONG-A-M9.md:83–93`; `TRANG-THAI.md:454`; `TRANG-THAI.md:492–494`; `TRANG-THAI.md:503`; `TRANG-THAI.md:511–512` |
| Ma trận thẩm quyền | **Chưa bật pháp nhân nào**. Anh tick vai theo phòng/pháp nhân; chỉ Admin quản trị, không tự cấp CFO mọi pháp nhân. Ánh xạ Hỏi/Kéo ngay/báo cáo còn chờ C1; phải kiểm quyền cả thẻ/danh sách/tệp/trích dẫn và tích hợp readiness, không dùng quyền vay cũ làm bằng chứng thiết kế mới đã xong. | `MTQ-4-CAN-CHOT.md:10`; `PHIEU-CONG-A-M9.md:25`; `PHIEU-CONG-A-M9.md:71`; `PHIEU-CONG-A-M9.md:89`; `THIET-KE-MA-TRAN-THAM-QUYEN.md:189` |

## Các điều kiện chung và cách cập nhật

| Điều kiện | Hiện trạng / tiêu chí đóng | Nguồn (tệp:dòng) |
|---|---|---|
| Năm cổng B | Chưa có đủ bộ biên bản M0/M2/M3/M4/M9. Lead điền đúng commit, checklist/phạm vi, ngày và kết luận Anh cho từng module; thiếu căn cứ giữ “chưa rõ”, không suy từ test. | `CHI-DAO-TU-ANH.md:197`; `2-PHIEU-KIEM-TRA-CHUC-NANG.md:47–56` |
| Ma trận | A1–A3/B1–B11 **đã chốt 19:50**, nhưng chưa có căn cứ hoàn tất chuỗi còn lại/readiness. Không pháp nhân nào được bật trước đủ chuỗi, Anh tick và Admin công bố. M9/đích CSDL M4 theo quyết định mới, không lấy giới hạn cũ trong thiết kế MTQ làm trạng thái hiện hành. | `docs/QUYET-DINH.md:337–355`; `MTQ-4-CAN-CHOT.md:10`; `CHI-DAO-TU-ANH.md:154`; `THIET-KE-MA-TRAN-THAM-QUYEN.md:187–192`; `CHI-DAO-TU-ANH.md:179`, `194` |
| Nền test | PG mới nhất được công bố: **v5, 3214 ok / 20 ERROR / 63 FAIL / 78 skip / 0 treo**. Không có mã lỗi mới và không mất độ phủ/skip; test không thay cổng B. Ca timeout phát sinh ở lượt sau đã chạy lại 51/51 lúc máy rảnh, chưa có công bố nền PG v6. | `NEN-TEST-PG.md:71–75`; `CLAUDE.md:40`; `TRANG-THAI.md:496–499`; `TRANG-THAI.md:515` |
| Nạp/đối chiếu/đường lùi | PG thật chung; M4 trước theo CD-011. Kho SQLite thật khác chỉ có kế hoạch, chạy bằng lệnh riêng. Sao lưu CSDL+tệp/SHA, thử bản sao, đối chiếu, đường lùi và biên bản theo [checklist phát hành](CHECKLIST-PHAT-HANH.md); chưa xác nhận đã thực hiện. | `CHI-DAO-TU-ANH.md:141–144`; `CHI-DAO-TU-ANH.md:194–196` |

## Cần Anh/lead

1. **Lead:** xác định phạm vi M0 và điền bằng chứng cổng A/B của cả năm module; không dùng phiếu CRM/Báo giá hay kết quả test để thay cổng riêng M0.
2. **Anh:** chốt các điểm nghiệp vụ/nguồn còn mở trong từng bảng; các quyết định lũy kế Review, OCR chung và A1–A3/B1–B11 đã có, chỉ cần triển khai/kiểm chứng.
3. **Lead:** cập nhật hàng đợi sau QD-08 (TRANG-THAI còn ghi các điểm đó bị chặn trước lúc Anh duyệt), hoàn thành MTQ/readiness và thu bằng chứng đủ năm cổng B trước đề nghị bật. Chưa có căn cứ xác nhận pháp nhân đã bật.
4. **Anh/lead:** chốt gói dữ liệu/pháp nhân thật và lệnh nạp đúng phạm vi; tổng số dòng/tổng tiền, tên PG/role thật và thời điểm go-live cụ thể **chưa rõ**. Không suy các thông tin này từ dữ liệu DEMO hoặc mã schema.
