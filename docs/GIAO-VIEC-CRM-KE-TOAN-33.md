# Gói nghiệp vụ kế tiếp — CRM kế toán từ kết quả trích hợp đồng #6

**Ngày:** 18/10/2026. **Đích:** triển khai lát cắt C1a/C1b của toàn cây 33, nối M3–M1/L1 và chuẩn bị nguồn cho L6/M10. Đây không phải phạm vi hoàn thành toàn chương trình. Giữ K1–K5, schema TL38 và tích hợp TL40; không hỏi lại kiến trúc đã chốt.

**Cập nhật điều phối 19/10/2026:** R_REV đã qua 27 probe độc lập, 21 unit test và GUI nhận/xác nhận/duyệt/xuất DEMO. Regression liên quan 165 pass, 2 fail do chế độ giữ file, có thêm 2 probe tương đương kiểm invariant đạt; bước xác nhận tệp tải qua browser sau sửa chưa kiểm chứng. Được triển khai gói CRM này trong cùng session Claude. Đây là CRM-01 của toàn chương trình, không phải thay đích hoàn thành bằng một DEMO.

**Tái sử dụng đúng phần đã có:** raw/hash/staging/evidence, transaction/audit, migration checksum, hai engine legacy, shell UI/token/mutation lock. R_REV dùng quick_items và actor cố định, **chưa phải** framework profile, V3/V4 hoặc quyền chung. Không gọi những phần chưa có runtime là đã tái sử dụng. Hoàn thiện typed K2 và quyền dùng chung ngay trong lát cắt hợp đồng này; không tạo kho, tiến trình web hay ứng dụng CRM thứ hai, không sao chép bộ duyệt riêng cho từng module.

### Ràng buộc kỹ thuật đã đối chiếu với code — phải giải quyết trong gói

1. `Store` V12 khóa workspace vào một entity (`ha_tang/store.py:88–91`) và promote luôn gán entity cấu hình. Giữ nguyên bảo vệ legacy; không đổi config/giấu pháp nhân thứ hai trong JSON để vượt khóa. Typed K2 PostgreSQL V14 là đích đã chốt, **không xây K2 SQLite mới**. SQLite thật và V13 option C vẫn giữ nguyên; kiểm regression phần legacy liên quan.
2. DDL `master.hop_dong*`, `loai_hinh_doanh_thu`, `lich_thu`, `kho.viec_can_duyet` đã có trong `pg_migrations.py`, nhưng chưa có runtime CRM. Bổ sung repository/service typed theo đúng các bảng này trong **cùng PostgreSQL và kiến trúc bốn schema**, migration mới có số phiên bản, không sửa checksum cũ. Không lưu lịch/master authoritative vào `quick_items.proposal_json/decision_json`, không tạo bảng CRM song song để né K2.
3. `nguoi_dung/phan_quyen` và V1–V8 mới có schema; cần kiểm quyền dùng chung actor–hành động–pháp nhân/module ở server và RLS. Bổ sung các role/field TL40 như BAN_HANG đúng lớp dùng chung; không tin actor/entity do client gửi, không coi token local là phân quyền. DEMO chỉ dùng danh tính MO_PHONG_ được server xác thực/gắn phiên; không gọi trình chọn vai DEMO là hệ đăng nhập production đã hoàn thiện. Cổng đăng nhập/vận hành thật còn phải đạt TL40 trước khi mở thật.
4. Link hiện chỉ FK hai chứng từ, unique theo cặp/loại, chưa trỏ tới đợt thu và chưa đủ biểu diễn chia nhiều đợt của cùng hợp đồng. Mở rộng **link/phân bổ chung** với ràng buộc tham chiếu đúng, pháp nhân/currency/số tiền, idempotency và hoàn tác có vết; không dùng ID lịch như ID chứng từ giả, không tạo bảng link riêng chỉ cho CRM. Giữ đường dùng chung cho các link L1–L12 sau này.
5. Một DB DEMO PostgreSQL phải chạy được hai pháp nhân, KCN và nhà ở, cùng luồng nguồn #6 → chờ duyệt → CFO mô phỏng → lịch/phụ lục → link tiền. Legacy BANK nếu được chiếu sang K2 phải có đối chiếu khóa/nguồn rõ, một sự kiện tiền logic; không tạo khoản thu/đề xuất hạch toán lần hai để làm ca link đạt. Hoàn thiện phần nền tảng vừa đủ cho luồng này rồi tiếp tục module, không tách thành dự án backend vô hạn.

Kiểm actual PG mới và upgrade DB DEMO đã có dữ liệu, migration lặp giữ dữ liệu, FK/RLS và vai ứng dụng thật (không chỉ superuser). Không drop/recreate DB để vượt lỗi; giữ mọi DB/file kiểm thử. Claude tự chạy unit và PG integration qua helper điều phối đã lọc bí mật; Codex kiểm độc lập. Test skip/không chạy không tính đạt.

Claude Code sửa chính; Codex/agent kiểm độc lập. Nhiệm vụ chuẩn bị tài liệu này chỉ đọc; chưa coding, chưa chạy app/test. **Không xóa bất kỳ file nào**, kể cả fixture, file tạm và output kiểm thử; bước triển khai phải dùng chế độ giữ file/thư mục riêng có tên phiên bản, không cleanup/unlink/rmtree.

## 1. Căn cứ bắt buộc và thứ tự ưu tiên

- `CHUONG-TRINH-HOAN-THIEN-PHAN-MEM-KE-TOAN.md`, `LO-TRINH-TRIEN-KHAI-TOAN-BO-33.md` C1a–C1d, `HOP-DONG-TICH-HOP-VA-TAI-SU-DUNG-33.md` R_CRM.
- `docs/can-cu-33/32-crm-ke-toan-tu-hop-dong-va-lien-ket-cheo-module.md` §1, **§3 quyết định đã chốt**; TL35 §3A/§5/§8; TL37 V3/V4, §5–8; TL38 hợp đồng/phiên bản/tham số/lịch thu/liên kết; TL40 §5/§7.
- `DANH-MUC-TAI-SU-DUNG-PHAN-MEM.md` §2 và source interface #6 bên dưới. Không gửi dữ liệu thật hoặc đọc/chạy source ngoài phạm vi được giao.

Ưu tiên quyết định mới: **tham số hợp đồng do CFO duyệt**, kế toán kiểm trước, bán hàng chỉ nộp/xác nhận. Tiền về chưa rõ khoản **đề xuất Vàng ngay theo CFO đã chốt**, không áp lại khuyến nghị treo 5 ngày ở phần thảo luận cũ TL32. Hợp đồng ký → master của hệ thống là một nguồn duy nhất; Excel lịch thu kinh doanh không phải master song song.

## 2. Interface thực của #6 — dùng kết quả, không xây lại bộ trích

Root nguồn: `D:\Claude\Local AI\hop_dong`.

- `doc_reader.py:292–327` chuyển `.doc` khi cần rồi đọc DOCX; trả text/cấu trúc/phiếu cảnh báo. Không có nhánh đọc PDF tại interface này. **Đầu vào nguồn đã biết là Word DOC/DOCX**, không mặc định PDF/OCR đã có.
- `trich_xuat_v3.py:618–638` là hợp đồng xuất `*_KET_QUA.json` thực, đã đối chiếu lại với source trong lần chuẩn bị này. Không mở file kết quả thật để làm fixture.

| Lớp | Shape nguồn phải giữ |
|---|---|
| Ngoài | `hop_dong`, `che_do`, `model`, `tao_luc`, `tham_so[]`, `phieu_kiem_tra`; các số đo `so_tham_so`, `so_ok_tu_kiem`, token/thời gian và kết quả so đáp án nếu có |
| Mỗi tham số | `ma`, `nhom`, `tham_so`, `gia_tri`, `don_vi`, `dieu_khoan`, `trich_dan`, `ghi_chu`, `kiem_tra`, `vi_tri_do_duoc`; có thể có `dap_an`, `so_voi_dap_an` |
| Chưa chạy AI | `che_do=chua_chay_AI`; có thể thêm `doan_lien_quan` theo tham số — không coi đoạn gợi ý là giá trị đã trích/đã duyệt |

`hop_dong` là tên/tham chiếu file, **không phải UUID hợp đồng, mã pháp nhân hoặc khóa pháp lý**. `gia_tri` là nội dung bảng tham số, không mặc định đã là số/ngày/đợt có cấu trúc. Output chưa có `lich_thu` chuẩn, loại doanh thu, mapping mã Junsky hoặc approval CFO. `kiem_tra`/số tự kiểm/đáp án nguồn không thay trạng thái duyệt; `tao_luc` nguồn không thay `known_at/eligible_at`. Không suy trang trích dẫn từ Điều/Khoản hoặc tự điền trang 1.

Không sửa/chạy reader, OCR, model, UI upload/trích của #6 trong gói này. Giữ raw output và hash; nhận kết quả JSON qua K1 là đủ để hoàn thiện lát cắt DEMO.

## 3. Luồng bàn giao bằng nút bấm trong cùng ứng dụng

**Nhận JSON #6 DEMO → hồ sơ hợp đồng/phiên bản/tham số chờ duyệt → kiểm mapping và trích dẫn → CFO mô phỏng duyệt → lịch thu theo cấu hình → nhận phụ lục đổi phần lịch chưa thu → lịch sử giữ nguyên → nối tiền về trước/sau, không tạo bút toán trùng.**

Phải có cả **thuê đất/hạ tầng KCN** và **mua bán nhà ở**, trên ít nhất **hai pháp nhân DEMO**, mỗi loại hình có một hợp đồng và phụ lục. Đây là phạm vi chung đã chốt; không gán nghiệp vụ nhà ở cho hồ sơ PLHN thật. Dùng catalog, đối tác và mã Junsky DEMO, actor `MO_PHONG_`; không dùng `CFO_NTD` hoặc duyệt dữ liệu thật.

### K1 — Nhận và định danh

1. Adapter JSON riêng tái dùng `Record/Batch/Adapter` và primitives raw/hash/staging/evidence/transaction/audit của ingestion hiện hành, nối repository typed K2 đã triển khai ở trên. Nếu mở rộng Store thì dùng cùng hợp đồng lưu trữ; không ép đa pháp nhân đi qua Store V12 đang khóa một entity. Loại hồ sơ hợp đồng, không giả thành BANK/INVOICE/NGHIEM_THU.
2. Envelope nội bộ tách khỏi raw nguồn: version contract adapter; namespace/instance nguồn; artifact/hash kết quả; hash/tham chiếu Word gốc khi có; thời điểm thực nhận; mapping hồ sơ nguồn → pháp nhân/loại hình/khóa hợp đồng; loại bản gốc/phụ lục và quan hệ tới bản gốc. Trường chưa biết giữ NULL/chờ xác nhận, không suy từ filename hoặc model.
3. Cùng artifact/raw hash nhận lại không tạo hợp đồng/phiên bản pháp lý/quyết định mới. Cùng Word trích lại ra JSON khác là **revision kết quả trích cần đối chiếu**, không mặc nhiên là phụ lục/phiên bản pháp lý mới. Khóa nguồn không đủ hoặc mâu thuẫn thì cách ly thành việc có lý do; không fuzzy tự gộp hợp đồng.

### K2 — Hồ sơ master có phiên bản và provenance

Theo tên/ý nghĩa TL38: `hop_dong`, `hop_dong_phien_ban`, `hop_dong_tham_so`, `loai_hinh_doanh_thu`, `lich_thu`; raw hợp đồng tại `chung_tu` loại `HOP_DONG_TEP`/`tep_goc`; mọi phần có pháp nhân và lịch sử. Dùng storage/migration có số phiên bản của ứng dụng hiện có, không viết đường dữ liệu song song hoặc sửa migration có checksum.

- Mỗi tham số giữ mã nguồn, nội dung thô, nội dung typed khi parse được, đơn vị, Điều/Khoản/trích dẫn/vị trí, cảnh báo tự kiểm và liên kết artifact. Thiếu trích dẫn → **“Không quy định/chưa có căn cứ”**, giá trị hiệu lực NULL; không biến thành 0 hoặc tự điền mặc định.
- Chỉ nhận một giá trị typed khi parser cấu hình không mơ hồ; giữ số tiền bằng Decimal/minor units, currency rõ, phần trăm/diện tích/đơn giá là các đơn vị riêng. Parse sai hoặc hai tham số cùng nghĩa mâu thuẫn → chờ xử lý, không chọn hàng cuối.
- JSON chỉ có citation không đủ chứng minh citation nằm trong Word gốc. DEMO có văn bản/cấu trúc và manifest câu trích do fixture cung cấp để kiểm đối chiếu. Nếu không có nguồn đối chiếu thì hiển thị giới hạn đó và yêu cầu người kiểm; không ghi trạng thái đã kiểm nguồn chỉ vì `kiem_tra` nói đạt.
- Hồ sơ V3/V4 mới nhận luôn CHO_DUYET; chưa được bộ lọc/chu trình coi là master đã có hiệu lực.

### K3 — Mapping và liên kết dùng chung

Mapping dựa trên ID/catalog: namespace nguồn + hồ sơ → pháp nhân, đối tác chung, ObjectID Junsky **theo pháp nhân**, ProjectID và mã hợp đồng chung. Không tự tạo mã Junsky; thiếu mã → việc chờ và hướng dẫn tạo ở Junsky trước. Cùng tên đối tác/số hợp đồng ở pháp nhân khác không được nhập nhằng hoặc nhìn thấy chéo quyền.

Mỗi loại hình doanh thu là profile cấu hình có version: danh sách mã tham số → field chuẩn, kiểu/đơn vị/bắt buộc, mẫu lịch nghĩa vụ và kiểm tra tương ứng. Thêm loại hình không sửa code nghiệp vụ; không dùng nhãn tự do làm luật. Profile DEMO phải ghi rõ **giả định để mô phỏng**, không được đổi trạng thái thành policy thật chỉ vì test xanh.

### K4 — Lịch thu là nghĩa vụ hợp đồng, không tự là doanh thu/thuế

1. Lát cắt tối thiểu sinh lịch từ **các đợt, số tiền, currency, hạn/mốc được nêu rõ trong hợp đồng DEMO và được duyệt**. Kết quả có khóa đợt ổn định, số tiền/đơn vị, loại cọc/đợt/phí nếu có căn cứ, hạn hoặc sự kiện và provenance tới phiên bản/tham số.
2. Mốc sự kiện chưa xảy ra/không có ngày thì giữ mốc và ngày NULL; không tự dùng ngày nhận/ký làm hạn hoặc tính quá hạn. Lịch `%` phải có căn cứ về cơ sở tính, VAT/phí, rounding và chênh phân bổ; thiếu thì lưu tham số/chờ xác nhận, không tự áp công thức. Lưu/hiển thị kiểu % trong gói này, không gọi chế độ chưa đủ cơ sở là đã sinh lịch đạt.
3. Việc tổng lịch khác tổng hợp đồng chỉ được đánh giá khi **cùng cơ sở số tiền/currency/phạm vi đã xác nhận**. Không cộng lẫn giá chưa thuế, VAT, phí bảo trì, cọc và tiền định kỳ rồi báo cân giả. DEMO dùng một cơ sở công khai đã định, đồng thời có ca thiếu cơ sở bị chặn.
4. Sinh lịch không tự tạo 131, bút toán doanh thu, VAT, hóa đơn, giá vốn hoặc lịch phân bổ doanh thu KCN. Lưu sự kiện/mốc theo cấu hình đã duyệt để các gói M3/M4/M8/M10 dùng tiếp; không bịa quy tắc ghi nhận của hai loại hình.

### K5 — Duyệt, phụ lục và tra cứu

- Thêm mục/luồng “Hợp đồng & lịch thu” vào **shell hiện có**, dùng bảng/form/ngăn chi tiết/chuỗi chứng từ chung; không làm lại màn hình bóc tách #6. Nút nhận mẫu/JSON, xem chờ duyệt, xem trích dẫn, mapping, duyệt tham số, lịch thu, lịch sử, phụ lục và liên kết tiền đều bấm được.
- Kế toán công nợ kiểm trước; CFO mô phỏng duyệt tham số; BAN_HANG chỉ nhập/phụ lục chờ duyệt và xem phần được cấp quyền. Actor/quyền/pháp nhân kiểm ở backend, không tin body. Nếu hạ tầng quyền production chưa có thì chỉ công bố DEMO và ghi phần chưa kiểm, không tạo cơ chế bảo mật thứ hai để làm đẹp trạng thái.
- Phụ lục có căn cứ riêng, ngày/quan hệ và tham số thay đổi → phiên bản mới chờ duyệt. Chưa duyệt không đổi lịch hiệu lực. Duyệt thì bản hiện hành thay theo ngày hiệu lực đã xác nhận; bản cũ và các mốc duyệt giữ nguyên.
- **Đợt đã khớp tiền giữ link tới đúng phiên bản/đợt cũ.** Ca DEMO đổi lịch chỉ tác động phần chưa thu/chưa khớp; có khóa nghĩa vụ nối giữa phiên bản để không cộng cả lịch cũ và mới vào phải thu còn lại. Đổi đợt đã thu một phần, chia/gộp/đánh lại số đợt không rõ mapping → việc đối chiếu chờ xác nhận, không tự chuyển tiền hoặc xóa lịch sử.
- File soát CRM/lịch thu dùng đường export chung nếu phù hợp, ghi đây là hồ sơ/lịch nghĩa vụ, không giả phiếu Thu/Chi hoặc file nhập Junsky. Giữ mức 2 khóa.

## 4. Nối tiền về mà không hạch toán lặp

Chuẩn bị BANK/đề xuất M1 DEMO trong cùng kho PostgreSQL dùng cho luồng CRM: một khoản đến trước hợp đồng và một khoản đến sau lịch đã duyệt, có provenance/khóa nối legacy–K2 nếu dùng lại đường M1 legacy. Tiền đến trước đi theo quy tắc CFO hiện có (Vàng và liên kết chờ theo căn cứ), không tự đặt một policy tài khoản mới cho CRM.

- Nối qua `lien_ket_chung_tu` chung, loại `HOP_DONG_DOT_TIEN`/quan hệ tương ứng TL38; không dựng bảng link riêng trong mỗi module. Lịch là nghĩa vụ thuộc phiên bản, liên kết vẫn truy được chứng từ tiền, hợp đồng và đúng đợt/phiên bản. Cách tham chiếu lịch theo storage hiện hành phải thống nhất với schema chung, không biến số đợt thành UUID chứng từ giả.
- Khi hợp đồng/đợt đến sau, chỉ bổ sung/xác nhận link và trạng thái thu; **không tạo BANK, phiếu thu, đề xuất hạch toán hoặc công nợ ghi sổ lần hai**. Đo số trước/sau để chứng minh, không chỉ kiểm dòng UI.
- Có phân bổ một phần/nhiều lần chuyển theo cơ chế chung và phần đã được đặc tả; tổng liên kết hiệu lực không vượt tiền khả dụng hoặc nghĩa vụ cùng cơ sở. Không tự bù trừ khác currency, pháp nhân hoặc đổi số tiền theo tỷ giá phỏng đoán.
- Khớp cùng số tiền nhưng nhiều ứng viên → V2 chờ chọn; tiền lệch lịch → hỏi/việc chờ theo cấu hình hiện có. Hủy/gỡ link có nhật ký, không xóa chứng từ gốc. Dòng đã xuất/nạp nếu cần đổi hạch toán thì theo đường điều chỉnh đã chốt, không sửa lô cũ.

## 5. Ca nghiệm thu DEMO và bằng chứng bắt buộc

| Ca | Kết quả phải chứng minh |
|---|---|
| Hai loại hình/hai pháp nhân | Nhận JSON đúng shape #6, cùng Store; KCN và nhà ở đều có tham số/citation, mapping và lịch; không lẫn mã Junsky/quyền giữa pháp nhân |
| Thiếu căn cứ | Citation thiếu/sai, chưa chạy AI, giá trị không parse được, thiếu số hợp đồng/mapping/currency/cơ sở tính → hồ sơ còn chờ; không tự có lịch hiệu lực hoặc số 0 |
| Nhận lại/trích lại | Cùng raw hash → 0 hợp đồng/phiên bản/link/quyết định mới; extraction revision khác cùng nguồn không tự thành phụ lục pháp lý |
| Duyệt đúng vai trò | Người nộp/kế toán không thay CFO duyệt V3; CFO MO_PHONG duyệt được ca đủ; actor thật/môi trường thật/sai token/cross-entity bị chặn |
| Lịch rõ và lịch chưa rõ | Các đợt số tiền/hạn tường minh ra đúng expected DEMO; % thiếu cơ sở và mốc sự kiện thiếu ngày còn chờ, không tự suy công thức/ngày |
| Phụ lục | Bản 2 chờ duyệt không đổi bản 1; duyệt chỉ thay phần nghĩa vụ hợp lệ; link của đợt đã thu còn trỏ bản cũ; lịch sử và căn cứ xem lại được |
| Phụ lục mơ hồ | Đổi đợt đã thu một phần/chia gộp chưa xác định mapping → chờ xử lý; không nhân đôi nghĩa vụ/phân bổ |
| Tiền trước và sau | Nối đúng hợp đồng/đợt; nhận lại/gỡ/nối lại có vết; chỉ thêm link, số BANK/đề xuất hạch toán/lô cũ không tăng do bổ sung hợp đồng |
| Không sinh doanh thu giả | Import/duyệt hợp đồng/sinh lịch/nhận phụ lục không tự sinh bút toán doanh thu/VAT/giá vốn hoặc mở Junsky mức 2 |
| Restart, GUI và regression | Dữ liệu/version/provenance còn sau restart; hoàn thành luồng bằng nút bấm; giữ các ca BANK/INVOICE/R_REV đang dùng; báo pass/fail/skip thật |

Expected DEMO được viết độc lập, nhãn giả rõ ràng; không lấy `dap_an` nguồn, snapshot thật hoặc output hệ thống làm expected. Không dùng việc số lịch trùng một tổng tùy ý để chứng minh chính sách kế toán. Handoff có file thay đổi, schema/profile version, số đếm/hash/idempotency trước–sau, ảnh GUI DEMO và hạn chế; review độc lập xử lý lỗi chặn trước kết luận.

## 6. Đã chốt, DEMO làm được và phần còn thiếu thật

**Không hỏi lại:** làm cả KCN và nhà ở, nhiều pháp nhân; loại hình doanh thu mở theo cấu hình; một nguồn hợp đồng; phụ lục có phiên bản; CFO duyệt tham số; giữ link lịch cũ; tiền về trước xử lý theo CFO; K1–K5, Store/UI chung và kiến trúc `giao_tiep`.

**Có thể code DEMO/cấu hình ngay:** adapter đúng JSON nguồn; envelope/provenance/idempotency; hồ sơ chờ và typed mapping có lỗi; hai profile DEMO; workflow V3/V4; lịch nghĩa vụ tường minh; phụ lục đổi phần chưa thu; liên kết tiền, lịch sử và ca bảo vệ. Không cần hỏi Anh công thức thật để dựng được các thành phần này, nhưng không gọi profile giả là policy đã phê duyệt.

**Chỉ đề nghị quyết định sau khi lập bảng căn cứ cụ thể, không hỏi mở lại toàn quy trình:**

1. **Bộ tham số/profile production từng loại hình** và mapping chưa chứng minh được từ 2–3 hợp đồng/phụ lục mẫu mỗi loại: trường nào bắt buộc, cơ sở tiền/VAT/phí, tỷ giá nếu có, hạn theo sự kiện, cách xử lý phần trăm/rounding. Tận dụng mẫu và cấu hình đã có tại nguồn trước; chỉ đưa phần thiếu/xung đột để CFO xác nhận, không tự tạo tham số/đáp án chuẩn từ dữ liệu thật.
2. **Phụ lục tác động phần đã thu/thu một phần** nếu văn bản chưa nêu cách chuyển nghĩa vụ: phân bổ giữ nguyên, cấn trừ hoặc chuyển đợt cần căn cứ/duyệt cụ thể. Ca DEMO phức tạp được giữ chờ, không tự chọn chính sách.
3. **Điều kiện và cơ sở ghi nhận doanh thu/thuế/giá vốn/phân bổ KCN** đủ chi tiết để viết mẫu bút toán production. Hướng mốc bàn giao/theo kỳ đã nằm trong loại hình; không suy thành ngày phát hành hóa đơn hoặc cách tính VAT/FX cụ thể. Gói tiếp theo chỉ tiêu thụ policy đã xác nhận.
4. **Đáp án mẫu trước khi dùng AI cho loại hình mới** là cổng đánh giá riêng (TL34/35), không tự tạo/đặt nhãn từ hợp đồng thật và không chặn phần adapter/workflow DEMO không gọi AI. Kích hoạt AI thật, nguồn thật và Junsky vẫn cần cổng vận hành tương ứng.

## 7. Production và ranh giới kết thúc gói

DEMO nhận file qua K1 là pha đầu. Khi #6/app trong nhà ghi vào kho production, giữ vai trò riêng và hàm có phiên bản qua schema `giao_tiep`/hàng đợi theo TL40; không cấp quyền bảng master/kho/bao_mat cho source. Mapping/duyệt/provenance dùng cùng core, không viết lại lúc chuyển từ DEMO sang production. Không gọi model, cloud, Zalo thật, không đọc hoặc thay kho thật trong gói DEMO.

Chỉ kết luận **lát cắt CRM kế toán DEMO đã đạt** khi đủ ca trên và review độc lập; không gọi toàn M3/L6/M10 hay tích hợp production hoàn thành từ việc đã có bảng hợp đồng hoặc giao diện lịch thu. Các hạng mục còn lại của toàn cây 33 tiếp tục giữ nguyên phạm vi.
