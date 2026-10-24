# Giao Claude CRM-42-00 — Ma trận màn hình và delta dữ liệu/API/quyền

**Ngày:** 20/10/2026. **Loại gói:** tài liệu thiết kế thực thi, không phải gói coding/migration. **Trạng thái:** READY_FOR_SEQUENTIAL_HANDOFF; chưa dispatch bằng tài liệu này.

Anh đã giao triển khai dần cả M4 và các phần CRM đã chốt. Gói này chuẩn bị đầu bài cụ thể cho các gói CRM tiếp theo; không yêu cầu Anh cấp lại quyền coding cho phần đã chốt. Chỉ giao tuần tự sau khi lượt M4 đang viết có terminal và baseline được Root kiểm tra; không can thiệp hoặc chạy song song với coder M4. Câu hỏi còn mở chỉ giữ chờ nhánh phụ thuộc, không treo toàn bộ CRM.

## 1. Đầu ra và giới hạn ghi

Chỉ tạo hai file Markdown mới, giữ nguyên nguồn và lịch sử:

1. `docs/CRM-42-00-MA-TRAN-MAN-HINH-VA-CA-KIEM.md`: ma trận coverage, authority, màn hình, trạng thái, quyền và ca kiểm.
2. `docs/CRM-42-00-DELTA-DU-LIEU-API-QUYEN.md`: hiện trạng có căn cứ, delta đề xuất và handoff coding kế tiếp đủ cụ thể để Root giao Claude.

Nếu file đầu ra đã tồn tại, dừng ghi đè và báo Root để chọn tên bản tiếp; không xóa hoặc sửa bản cũ. Không tạo sản phẩm HTML/JS/Python, SQL, migration, controller, settings, fixture hoặc prototype. Không sửa tài liệu 41/42, queue, chương trình tổng, continuity hay tài liệu module khác. Không chạy/import product, AST/compile, tests, SQL/DB, HTTP, AI/cloud, Claude Design hoặc browser; không đọc dữ liệu thật, DB, `.env`, credentials hoặc source app gốc. Đây là gói đọc code/tài liệu và viết hai artifact.

## 2. Căn cứ phải đọc và thẩm quyền

- [41 — CRM-G và engine theo loại](<../../41-crm-g-giao-ket-va-engine-trich-theo-loai-hop-dong.md>), 140 dòng; SHA256 `d192f99c52ddb39058c1a0f31904b6f4d7415c338858fd7b936d6a32a521a6d3`.
- [42 — Màn hình CRM](<../../42-man-hinh-crm-ke-toan-va-giao-ket.md>), 240 dòng; SHA256 `445fd2a161c644ed1650cdd9a21e459915d0fd209fd45edef175e99a11c1546b`.
- [Hàng chờ CRM](HANG-CHO-CRM-41-42.md), bản đã đọc 83 dòng, SHA256 `60b6b0f92dffd9b5b8324f83b9fafb0362971b1e67bfbf5504ff4d34f2fc76fc`. Nếu Root có bản cập nhật sau chỉ đạo tiếp tục M4/CRM, dùng đúng bản Root chỉ định và ghi hash thực; không tự sửa queue.
- [Thiết kế CRM hiện trạng](<../../THIET-KE-MODULE-DE-CHOT-2026-10-20/CRM-CHUC-NANG-VA-THIET-KE.md>); TL32, TL35 §3A, TL37/K5, TL38 và TL40 theo liên kết đã có. Chỉ đọc bản kỹ thuật trong phạm vi Root giao.
- Root cung cấp baseline sau lượt M4: đọc source trung tâm/frozen đã xác định, không lấy file M4 đang viết dở làm contract cuối. Mã cần đối chiếu: `k2/crm.py`, `crm_phan_tich.py`, `loai_hinh_demo.py`, `quyen.py`, reader `nguon/trich_hop_dong_6.py`, phần CRM UI/server và schema liên quan. Không yêu cầu chạy source để lập ma trận.

Mỗi dòng ma trận có cột mức xác nhận: `DA_CHOT_42_4_DIEM`, `DA_GHI_CHOT_41`, `GIU_HIEN_HANH`, `DE_XUAT_CAN_CHOT` hoặc `CAN_DAU_VAO`. Dẫn đúng mục/dòng tài liệu và source khi có. Lệnh giao gói này không biến mọi cột giao diện, giá trị sampling hay câu hỏi trong tài liệu thành policy đã được phê duyệt.

## 3. Các ràng buộc đã rõ

1. Bốn điểm 42 §16 giữ nguyên: Danh sách hợp đồng là trang mở đầu; không có “Việc của tôi” riêng trong CRM; menu riêng “Hợp đồng bán hàng” với sáu mục con; bán hàng thấy hai nhãn thu CRM/công nợ Junsky của khách trong quyền; desktop 1280–1440 px. Hai ý đầu cùng thuộc điểm 1 của đặc tả, tổng cộng vẫn là bốn quyết định.
2. Hai luồng dùng cùng master HĐ/PB/tham số/nghĩa vụ. A: CFO duyệt phiên bản mẫu, KT chỉ làm hiệu lực từng HĐ đủ điều kiện. B ngoài mẫu giữ CFO/V3 hiện hành cho đến khi có quyết định khác; không cấp KT quyền CFO chung hoặc giả danh CFO.
3. Mọi việc quyết định dùng K5 chung; không dựng bộ duyệt hoặc sổ thu riêng trong CRM. Chuẩn bị loại việc, đối tượng tham chiếu và đường mở đúng màn/tab.
4. Mẫu, bộ chuẩn, báo giá đã in, bản xuất và bản ký có version/revision/hash. Hợp đồng đang soạn giữ mẫu đã chọn. Bản ký không mở khóa/ghi đè khi trả lại; nhánh sửa/thay bằng chứng phải bảo toàn bản cũ và còn chờ binding chi tiết.
5. Không đưa BOQ/review đợt/K1–K8/B1–B8/P01–P18 của M4 vào CRM. M1 chỉ tái dùng liên kết tiền đúng scope/currency/budget; M3 chỉ tham chiếu đọc, không tự ghi doanh thu hoặc xuất nhập Junsky.

## 4. Ma trận chức năng bắt buộc — không bỏ G/E nào

Mỗi dòng dưới đây phải được triển khai trong artifact 1 với dữ liệu thiết yếu, API hiện có/đề xuất, quyền/scope, dependency, gate còn mở và ít nhất một ca kiểm cụ thể. Chưa có API thì ghi `DE_XUAT`, không mô tả như endpoint đã chạy.

| ID 41 | Màn/tab/việc liên quan của 42 | Dữ liệu và điểm nối cần làm rõ | Gate chính |
|---|---|---|---|
| G1 Mẫu có phiên bản | S6; K5/V4 | DOCX, placeholder, field map/kiểu/định dạng, PN/loại, version, hiệu lực, người tải/kiểm/duyệt | Placeholder chưa ánh xạ chặn duyệt; trường bắt buộc thiếu trong mẫu là cảnh báo theo 41, không tự nâng thành hardblock. |
| G2 Báo giá/lịch | S3; S1; S2-T3 | Giá/currency, FX người/ngày, lịch bốn cột, số/ngày báo giá, khách/tài sản, bản in | Theo dự án cần G7; theo khách không giả là chuẩn; không tạo nghĩa vụ/công nợ từ báo giá. |
| G3 Soạn HĐ | S4; S2-T2/T3 | Template version, input snapshot, nguồn từng tham số, lịch từ báo giá, revision, DOCX/PDF | Giá trị bắt buộc trống chặn xuất; pin mẫu cũ; PII artifact access là nhánh cần binding. |
| G4 Ký kết | S5; S2-T6 | PDF, ngày ký, khai Có/Không sửa, revision bản in, uploader và evidence hash | Không PDF không ký; cùng evidence replay không trùng; giữ signed revision bất biến. |
| G5 Đối chiếu bản ký | S2-T6; ngăn việc nền; K5/V3 | Expected/generated facts, signed facts, locator, mức lệch, kết quả và quyết định xử lý | Khai Có/được chọn kiểm phải đối chiếu hoặc KT xử lý có căn cứ trước hiệu lực; adaptive policy tách riêng. |
| G6 Kiểm → hiệu lực | S2-T2/T3; K5 | Template approval lineage, kiểm/mapping/Junsky ID, graph/version, kết quả G5, lịch nghĩa vụ | A KT đủ gate; B giữ CFO; chưa hiệu lực không sinh nghĩa vụ hoặc mở nối tiền. |
| G7 Bộ chuẩn dự án | S3/S4 đọc chuẩn; S2-T3 so lệch | PN/dự án/giai đoạn, version lịch chuẩn, KT lập/CFO duyệt, effective dates | Phần tối thiểu phải trước nhánh Theo dự án/G6. Vị trí UI quản trị chưa tường minh: đề xuất trong khung hiện có, không tự thêm menu thứ bảy/màn thứ mười như đã chốt. |
| G8 Báo cáo giao kết | S9; S1/thẻ số; S2-T1 | Count/state/project/PN, lệch chuẩn, sampling configuration, drilldown, file soát | Tổng cùng scope; mẫu/nhánh chưa có dữ liệu hiển thị thiếu, không giả số 0. |
| E1 Catalog theo loại | S7; selector loại/profile S3/S4 | Catalog ID/version/hash, XD/KCN/nhà ở, metadata output | 37 mã là baseline XD; không ép KCN/nhà ở có cùng 37 mã. Giữ khóa nguồn cũ. |
| E2 Logic theo loại | S7; S2-T2/T3/T6 | Rule/profile version, kiểm lịch/tỷ lệ/currency/cơ sở FX, lỗi theo loại | Giữ hành vi XD; quy tắc mới phải có căn cứ, không suy VAT/FX hoặc lịch từ tổng tiền. |
| E3 Tham số dạng bảng | S7; S2-T3; S3/S4 | Dòng lịch, %, tiền/currency, ngày/sự kiện, ghi chú, order, locator mỗi dòng | Bảo toàn raw/source states; mốc chưa có ngày không quá hạn; text TT-20 XD cũ vẫn đọc được. |
| E4 Output tương thích | S7; S2-T2/T6; job | Loại HĐ, template ID/version, chế độ trích/đối chiếu và contract output cũ | Phân biệt schema nguồn thực với DTO đề xuất; không đổi khóa cũ hoặc tự nhận metadata từ browser là authority. |
| E5 Đối chiếu kỳ vọng | G5; S2-T6 | Bộ tham số kỳ vọng bất biến, signed evidence, typed/raw comparison và `lech` | Không lấy output thực làm oracle; UNKNOWN/FAILED không phải MATCH; chấp nhận lệch không đổi DIFF thành MATCH. |
| E6 Ranh giới engine | Toàn module | CRM chỉ gọi trích/đối chiếu dùng chung; source M4/XD được bảo toàn | Không sửa app nguồn thật; không mang nghiệp vụ BOQ/review xây dựng sang CRM; không race file M4 đang viết. |

## 5. Coverage UI phải đủ và truy ngược được

**Sáu menu:** MENU-1 Hợp đồng; MENU-2 Báo giá; MENU-3 Mẫu hợp đồng; MENU-4 Tiếp nhận hợp đồng ký; MENU-5 Thu tiền; MENU-6 Báo cáo & file soát. Đây là ID menu, không phải mã module M1–M6.

**Chín màn:** S1 Danh sách; S2 Chi tiết; S3 Báo giá; S4 Soạn HĐ; S5 Hộp Ký kết; S6 Mẫu/ánh xạ; S7 Tiếp nhận bản ký; S8 Thu tiền; S9 Báo cáo. Map màn con/dialog về menu đúng; không thêm một trang duyệt CRM riêng.

**Bảy tab S2:** T1 Tổng quan; T2 Nguồn & tham số; T3 Lịch nghĩa vụ; T4 Thu tiền; T5 Phụ lục/phiên bản; T6 Bản ký & đối chiếu; T7 Lịch sử. Với từng tab, ghi cột/field, empty/unknown/error/permission states, nguồn dữ liệu, nút theo vai/trạng thái, hành vi sau mutation và ca kiểm.

**17 trạng thái thiết kế của 42 §15:** V01 S1 KCN; V02 S1 nhà ở vai bán hàng; V03 S2-T2 mở ngăn trích dẫn; V04 S2-T3 KCN; V05 S2-T3 nhà ở có mốc sự kiện; V06 S2-T4 hai ô thu; V07 S2-T6 có lệch; V08 S3 KCN tổng % không đủ; V09 bản in báo giá; V10 S4 ba cột có lỗi; V11 S4 nhắc mẫu mới nhưng giữ version; V12 S5 thiếu PDF; V13 S5 đủ điều kiện; V14 S6 placeholder chưa ánh xạ; V15 S7 tiến độ chín bước; V16 S8 nối vượt phần còn lại; V17 S9 tổng kiểm soát. Lập từng dòng, không chỉ ghi “đủ 17”; đây là coverage thiết kế, không phải 17 ca đã chạy.

Ma trận vai bao gồm bán hàng, KT công nợ, CFO, người xem, người tải mẫu/pháp chế. Kiểm scope PN + dự án + khách/người phụ trách; thiết kế backend và quyền tệp, không chỉ bộ lọc/CSS. Công việc CRM cung cấp cho K5 phải map đủ nhóm 42 §3, gồm trả lại/bổ sung, nhắc chờ ký, chờ kiểm, lệch bản ký, tiền chưa rõ/đến hạn, đối tượng mới, mẫu chờ duyệt và lệch chuẩn.

## 6. Delta phải bám code thật

- CRM hiện có master HĐ/PB/tham số/lịch và B: nhận JSON kết quả, KT kiểm, CFO/V3 duyệt. `crm.py:231–258,450–533`; `nguon/trich_hop_dong_6.py:1–9,30–93`. Reader hiện không tự chạy engine trích theo loại.
- `crm_phan_tich.py` có parser theo profile và VND/USD exact minor; không coi đó là nghiệp vụ FX đã hoàn thiện. Profile DEMO ở `loai_hinh_demo.py` không phải mẫu/bộ chuẩn đã CFO duyệt.
- Ghi rõ bảng/field/constraint/RLS/API hiện có được tái dùng, phần đề xuất thêm và consumer bị ảnh hưởng. Không viết SQL hoặc thực thi migration trong gói này. Không tạo master, auth, approval hoặc sổ tiền song song.
- A KT-only effectiveness cần path service/DB riêng, không chỉ đổi nút/quyền Python; B và guards M1/current CRM được giữ. Origin MAU cần template/version/render-input/signed-revision lineage thực, không nhét vào nhãn cũ để vượt guard.
- Bổ sung quote, legal/draft revisions, template/map approvals, bộ chuẩn, signing evidence, comparison/job và quyết định sampling theo grain/version. Nguồn từng tham số và lịch có provenance; quote đã in không bị sửa theo draft HĐ về sau.
- Hai nhãn CRM/Junsky tách grain/currency/as-of. Số dư 131 toàn đối tượng không được gắn nguyên cho từng HĐ; thiếu nguồn khác 0. FX báo giá/VND tham chiếu không tự cho phép nối BANK VND vào nghĩa vụ USD.
- Đề xuất API chỉ ở mức contract: action/read, input/output, actor/scope, preconditions, expected graph/version, client key/replay, audit, file purpose/access, lỗi/unknown outcomes. Đường dẫn vật lý chưa có phải ghi đề xuất; không giả API đang vận hành.
- CCCD/STK dùng kiến trúc bảo vệ chung; tách quyền nhập, xem lại, sinh/preview/tải văn bản và xem PDF ký. Synthetic DEMO không chứng minh bảo mật/accuracy production.

## 7. Câu hỏi chỉ giữ chờ phần phụ thuộc

Q-B giữ CFO hiện hành; chỉ quyết định đổi B mới chờ. Q-SAMPLE giữ chờ các số/cửa sổ/denominator và nhánh tự điều chỉnh; không chặn đối chiếu bắt buộc/thủ công. Q-RETURN giữ chờ unlock/replace/cancel hoặc thay đổi pháp lý ảnh hưởng phần đã thu; không chặn G1/G2 hay đặc tả first-sign immutable. Q-INPUT giữ chờ mẫu/đáp án thực và độ chính xác theo loại; DEMO dùng để thiết kế được. Q-PII giữ chờ chi tiết quyền artifact thật, không chặn mapping/schema preparation. Q-UI bám cột/layout đề xuất, không hỏi lại bốn điểm đã chốt. Không tự lựa chọn policy thay Anh và không biến các điểm này thành gate chung của toàn CRM.

## 8. Tiêu chí hoàn thành và bước giao kế tiếp

1. Ma trận phủ đủ 8 G, 6 E, 9 màn, 7 tab, 17 trạng thái, 6 menu và 4 quyết định đã chốt, có ID truy ngược hai chiều; ghi rõ lỗ hổng nếu một yêu cầu chưa có chỗ đặt UI/API.
2. Mỗi action có quyền/scope/current-state/required-data/immutable-basis/replay/output/error và ca kiểm dương/âm tương ứng. Phân biệt template approve, KT effectiveness A và CFO approve B; không trả lời bằng một dòng “dùng lại duyệt chung”.
3. Ca kiểm bao gồm unknown placeholder/cảnh báo field thiếu; version mẫu/revision ký; thiếu PDF/replay; bắt buộc đối chiếu/OCR fail; origin A/B; lịch/currency/event-date; budget M1; scope/tệp/PII; CRM–Junsky cùng grain; thiếu nguồn khác 0; XD regression và catalog theo loại. Chỉ mô tả, không chạy.
4. Delta có source file:function/line evidence và nhãn HIEN_CO/DE_XUAT/CHO_DAU_VAO, không lấy seed hoặc mock làm khả năng production đã có. Những file có thể bị M4 thay phải đọc từ baseline Root chỉ định sau terminal.
5. Artifact 2 kết thúc bằng ít nhất một handoff coding phần đã chốt: mục tiêu hữu hạn, exact file targets đề xuất, shared primitives tái dùng, contract/API, kiểm độc lập cần có, ngoài scope và dependency thật. Bám queue: E1–E5 chờ interface M4 đã freeze; G1 + G7 tối thiểu; G2/G3; G4/G6 + G5 cơ bản; UI/file và adaptive riêng. Root có thể giao ngay gói đủ điều kiện sau technical review, không xin lại quyền chung hoặc treo vì nhánh policy chưa chốt.
6. Báo tên/hash hai artifact, coverage còn thiếu và nội dung cần Root xem. Kết quả tối đa là `SCREEN_SCHEMA_DELTA_READY_FOR_ROOT_REVIEW`; không ghi CRM đã code/test/nghiệm thu hoặc schema đã được migrate.

Mọi bản cũ được giữ. Trong gói này không đụng source app thật, dữ liệu thật, nghiệp vụ M4 ngoài seam trích dùng chung hoặc M9.
