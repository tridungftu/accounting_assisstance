# CRM-01 — yêu cầu sửa sau kiểm chứng độc lập lần đầu

Ngày 19/10/2026. Claude bàn giao đầu đã terminal exit 0. **Chưa nghiệm thu.** Codex/agent đã kiểm bản source frozen, không sửa product. Trạng thái toàn cây 33 vẫn giữ nguyên; không chuyển đích thành xây backend hoặc chỉ lưu hồ sơ chờ.

Đọc ba review chi tiết: `REVIEW-CRM-K2-MIGRATION-01.md`, `REVIEW-CRM-NGUON-VA-PARSER-01.md`, `REVIEW-CRM-HTTP-01.md`; đọc thêm `REVIEW-CRM-PHAM-VI-VA-TAI-SU-DUNG-01.md` về phần còn thiếu. Tất cả fixture trong review là DEMO; không đọc evidence riêng/var hoặc dữ liệu thật. Không cần quyền hay quyết định nghiệp vụ mới để sửa các lỗi này.

## 1. Kết quả đã chạy, không thay bằng tự báo cáo test xanh

- SQL/schema: 26 ca = **7 control đạt, 19 vi phạm**, 0 setup error/skip. Có fresh và upgrade v9 thực; ID/login GUC, RLS/FK/immutability và quyền app_web thực.
- Service: 8 ca = **1 positive control đạt, 7 vi phạm**, 0 setup error/skip. Login PostgreSQL thường NOSUPERUSER/NOBYPASSRLS, hai PN/hai profile; nghĩa vụ expected 100+400+500. Race có barrier và hai connection, không chạy tuần tự để gọi là concurrency.
- HTTP thật: 12 ca = **8 control đạt, 4 vi phạm**, hai CookieJar độc lập, không mock service; global identity bleed tái hiện đọc và duyệt sai cửa sổ. GET CRM có mutation_lock; không có finding GET connection race từ các ca này.
- Source/parser: 20 criterion probes = **12 đạt phạm vi hẹp, 6 fail, 2 capability gap**; riêng 18 JSON source-format được parser đọc chỉ chứng minh định dạng, không phải 18 workflow đạt. Xem review chi tiết/binding và phạm vi.

Không xóa file hoặc DB/role để làm kiểm thử xanh. Backup trước sửa lần này gồm 181 file source/test/tool/doc và hash copy khớp. Mọi bằng chứng/DB lần đầu được giữ.

## 2. Sửa quyền, tính bất biến và migration trước

1. Chặn app_web INSERT thẳng phiên bản DA_DUYET; khóa nội dung bản/tham số/lịch đã duyệt. Chỉ cho thay metadata vòng đời cụ thể qua đường được cấp quyền, không dùng nhánh return khi trạng thái không đổi để bỏ kiểm nội dung.
2. Thiếu login hoặc ID/login khác nhau phải fail closed. Giữ `_tx` GUC LOCAL đã đạt; không thay bằng biến connection lâu dài. Chặn đọc dòng đề xuất/chứng từ/nhân viên khác PN và không để BAN_HANG đọc đề xuất kế toán cùng PN. Thực thi quyền module cho đọc service và CSDL theo thiết kế chung; không chỉ ẩn menu.
3. Ràng buộc FK cả PN lẫn quan hệ: profile/project cùng PN; current version/replacement cùng hợp đồng; lịch đúng PN/version và replacement cùng nghĩa vụ/hợp đồng. Có ca cùng PN nhưng sai hợp đồng, không chỉ cross-tenant.
4. Upgrade v9 có link HUY cũ hợp lệ hiện lỗi23514. Không xóa lịch sử, không bịa người/thời điểm hủy. M0001–M0009 giữ nguyên checksum. M0010 là bản mới chưa nghiệm thu nhưng đã tồn tại trong DB thử: xử lý có chủ ý cả DBv9 và DBv10 bản bàn giao đầu; không chỉ thêm M11 rồi bỏ qua thực tế v9 chết ở M10. Nếu cần sửa M10 chưa phát hành, phải nêu phương án tương thích cụ thể, nhận diện chính xác hash M10 cũ, lưu nguyên checksum đã ghi/nhật ký chuyển tiếp và chạy upgrade trên cả hai đường. Không reset/recreate DB, không tùy tiện cho qua mismatch hoặc rewrite schema_migrations để làm xanh.

## 3. Sửa nghiệp vụ lịch, duyệt và concurrency

1. `danh_sach` phải kiểm quyền XEM/module/entity; actor có PN mà không có CRM không được nhận raw/hợp đồng/toàn bộ sao kê. BAN_HANG chỉ nhận dữ liệu phù hợp công việc, không biến CRM thành cửa đọc M1.
2. Phụ lục hiệu lực2099 không được lập tức thay bản hiện hành ở19/10/2026. Giữ xem được bản đã duyệt sắp có hiệu lực, lịch cũ tiếp tục áp trước ngày; tới ngày dùng bản đúng mà không cần sửa dữ liệu thủ công. Test clock/as-of rõ ràng, không hardcode ngày chạy fixture để lách.
3. Quyền V3 không tự đóng V4. Duyệt/khởi hoạt hợp đồng mới cần đúng quyền V3/V4 hoặc hai bước tương ứng; actor chỉ V3 không được hoàn tất việc ngoài quyền.
4. Đổi mapping hoặc nội dung ảnh hưởng sau KT kiểm phải vô hiệu lần kiểm hiện hành, giữ vết kiểm cũ và bắt kiểm lại trước CFO. Không chỉ kiểm `kiem_boi IS NOT NULL`.
5. Duyệt phụ lục đổi nghĩa vụ và nối tiền phải khóa/serialize cùng contract/chuỗi nghĩa vụ, thứ tự khóa nhất quán, rồi tính lại trong transaction. Race hiện cả hai thành công làm lịch400 nhưng link500. Kiểm hai thứ tự thắng: phụ lục trước thì link cũ bị từ chối; tiền trước thì đổi nghĩa vụ đã thu phải chờ. Không chuyển tiền/xóa lịch sử tự động.
6. Hai retry đồng thời cùng idempotency/payload phải trả cùng kết quả, một link; hiện request2 lỗi23505. Kiểm quyền trước nhánh trả retry; khác payload từ chối; hủy/retry/nối lại có semantics và audit rõ.

## 4. Sửa parser theo đúng nguồn và căn cứ

1. Quote có trong văn bản không tự chứng minh giá trị. Ca raw45triệu/quote40triệu hiện vẫn CO_CAN_CU và ra lịch45+55; `ghi_chu=Suy ra` với quote không chứa40triệu vẫn ra40. Giữ raw, chỉ hiệu lực khi có căn cứ trực tiếp hoặc xác nhận thủ công rõ nghĩa/ghi vết; không tự nâng suy diễn thành trích trực tiếp. Điều/khoản99 sai không được ghi đã đối chiếu nguồn chỉ vì substring tồn tại. Không viết lại DOCX/OCR/model nguồn.
2. So sánh nghĩa vụ phải xét `co_so`, `loai` và định danh đợt bên cạnh amount/currency/date/event. Đợt đã thu đổi trước/sauVAT hay DOT→COC hiện vẫn GIU; phải chờ xử lý đúng căn cứ, không chuyển tiền tự động.
3. Catalog nguồn có các tham số optional chưa có giá trị. Dòng D3 tiền/hạn/% rỗng không phải nghĩa vụ thực và không chặn lịch40+60 đã đủ căn cứ. Dòng có giá trị nhưng thiếu cơ sở/quote vẫn phải chặn đúng lý do; không bỏ toàn bộ optional errors.
4. Profile cấu hình cần xử lý đơn vị nguồn `đồng` qua mapping/alias có provenance, giữ nguyên raw, không rewrite fixture sang VND để gọi đạt. Kiểm `%` theo value/unit thực, NULL, duplicate mã/mâu thuẫn và precision. Profile version/hash/căn cứ Word cần giữ đúng mức đã chứng minh; không dùng hash của chuỗi tưởng tượng như hash tệp Word thực.

## 5. Hoàn tất thao tác và tái sử dụng đã giao

1. Danh tính MO_PHONG_ gắn riêng phiên server. A chọn KT_A, B chọn KT_B/CFO không đổi actor/scope/action của A. Từ body không nhận actor; trình chọn vai DEMO vẫn ghi đúng giới hạn, không cần mở production login để sửa lỗi này. Dữ liệu/khả năng duyệt theo session token/cookie phù hợp shell, không globalactor.
2. Cho bổ sung khóa/profile/mapping đúng artifact CHO_KHOA/CHO_MAPPING và tiếp tục có audit, không tạo raw/bản hợp đồng lần2, không đổi namespace để lách dedup. Hiện nhận lại cùng raw sau bổ sung profile chỉ TRUNG_RAW/0contract.
3. Có màn đối chiếu revision kết quả trích cùng Word và thao tác tiếp tục có kiểm/duyệt; không tự thành phụ lục pháp lý và không chỉ tạo việc chờ vĩnh viễn.
4. File soát CRM/lịch nghĩa vụ và nút tải, có phiên bản/căn cứ/tiền/đợt, dùng export chung phù hợp; không giả file thu/chi hoặc Junsky mức2. Kiểm HTTP bytes/nội dung/quyền và restart. Không ghi đã bấm GUI khi browser tool chưa có.
5. Nối M1 thực trong DEMO theo đầu bài §4: tái sử dụng ingestion/engine/projection hiện có, một BANK logic và đúng chứng từ/đề xuất K2 đã có, cả tiền trước/sau hợp đồng. `nhan_tien_demo` tạo SAO_KE+headerVANG trống không chứng minh đã nối M1. Không viết engine hạch toán mới, không nhân sao kê/đề xuất, không dùng policy production giả. Đối chiếu CFO-02/03 theo review phạm vi và căn cứ mới; giữ file policy thật nguyên. Đo số/hashes BANK, chứng từ/đề xuất/dòng/lô/link trước–sau và khi lặp/gỡ; actor MO_PHONG_ và dữ liệu DEMO.

## 6. Regression và bàn giao lại

Độc lập converter positive đã chạy cùng SQLite DEMO hợp lệ (14documents/2lines/5quickstates/2knowledge revisions): baseline schema9 và current10 đều lần đầu/repeat exit0; 16 bảng theo dõi không drift; nguồn saihash0, nguồn không đổi. Tamper core_hash riêng exit1/sai1 đúng; tiền header tamper phát hiện1lệch. Vì vậy không gán lỗi t16 hash giả thành regression M10; test diagnostic exit1 không phải bằng chứng positive. A5 `line_key` phi số/sửa stt vẫn false-match ở cả hai bản, cùng các gap A5 đã ghi vẫn chưa đạt; không tự ghi A5/V13 hoàn thành trong gói này.

Tự thêm regression có ý nghĩa cho từng lỗi, dùng positive controls đúng vai/nguồn. Chạy unit/PG qua helper được cấp; giữ guard, PYTHONDONTWRITEBYTECODE=1 và DB/file/role. Không chạy t15 cleanup DROP OWNED/DROP ROLE; sửa test để retain hoặc dùng ca tương đương với login thường và retention đã kiểm. Không thay assertion lỗi thành pass để che ca dương. Cập nhật báo cáo CRM với kết quả thực, file/hash/schema mới, phần chưa kiểm; giữ đoạn review độc lập chưa nghiệm thu cho đến Codex chạy lại.

Sửa xong bàn giao cả lát cắt theo đầu bài, không hỏi lại kiến trúc hoặc tự bỏ phần khó. Không commit Git. Không đọc/gửi dữ liệu thật, không cloud/AI/Zalo thật/CFO_NTD, không đổi kho thật SQLite hoặc mở Junsky. Tiếp theo vẫn là tái sử dụng khoản vay M9 và các module còn lại của cây33 sau khi lõi CRM này qua cổng kiểm.
