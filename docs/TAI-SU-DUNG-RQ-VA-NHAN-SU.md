# Tái sử dụng RQ và nhân sự — kiểm tra tĩnh bổ sung 18/10/2026

**Kết luận:** nguồn #1 đã có hồ sơ loại chi phí có schema/version và engine kiểm tra; nguồn #2 đã có schema Request, API v1 đọc/nháp/tệp và webhook. Không cần hỏi lại Anh hai phần mềm này có định nghĩa loại chi phí hoặc API/schema RQ hay chưa. Phần còn làm là crosswalk, adapter có phiên bản, provenance và liên kết tới nghiệp vụ kế toán. Nguồn #4 mới xác minh được hồ sơ kỹ thuật trên Windows; source WSL và đầu ra bảng lương chưa kiểm chứng.

Phạm vi chỉ đọc tài liệu kỹ thuật, schema và source/interface. Không chạy ứng dụng/test/module ứng dụng, không gọi mạng, không đọc `.env`, credentials, dữ liệu/chứng từ, cache, golden cases hoặc giá trị YAML hồ sơ đang dùng; không sửa dự án nguồn. Đường dẫn được xác định từ TL31/TL40 và danh mục mà TL31 dẫn tới (`D:\Claude\DANH-MUC-DU-AN.md:14–17`), không tìm toàn ổ đĩa. Source hiện có không chứng minh deploy/go-live hoặc chất lượng trên dữ liệu thật.

## 1. #1 — Phần mềm kiểm tra đề xuất Base

**Path:** `D:\Claude\Phần mềm kiểm tra đề xuất`.

| Căn cứ source/schema | Interface hoặc dữ liệu kỹ thuật đã có | Ý nghĩa tái sử dụng |
|---|---|---|
| `ho_so_loai/_schema.yaml:22–77` | `loai`, `ten`, `phien_ban`, `nguoi_xac_nhan`, `ngay_hieu_luc`, `ma_cu`; nhận diện theo mẫu form/từ khóa/loại trừ/pháp nhân/người duyệt trước; chứng từ bắt buộc/thay thế/hỗ trợ; đối chiếu, kiểm tra, ngưỡng, định mức/plugin, lưu ý CFO | Có contract hồ sơ loại chi phí; không cần Anh mô tả lại các trường này |
| `src/engine/profiles.py:146/:151/:183–205` | `load_schema`, `validate_text`, `load_profiles`; schema lỗi hoặc `loai` trùng thì từ chối nạp; kết quả là dict theo `loai`, kèm `_path`, `_rule_version` | Dùng lại validator, định danh và version; không nạp YAML thẳng vào bảng quy tắc kế toán mà bỏ kiểm tra |
| `src/engine/profiles.py:201` | Version là loại + phiên bản + hash nội dung | Có sẵn cách phát hiện quy tắc đổi và kiểm lại kết quả |
| `src/check/category_router.py:69–102` | `route(detail,profiles)` trả trạng thái phân loại/thiếu người duyệt/chồng lấn/chưa phân loại, loại đã chọn, danh sách khớp và lý do | Dùng lại kết quả nhận diện/căn cứ; không viết classifier cạnh tranh cùng loại chi phí |
| `src/engine/runner.py:109/:212/:259–275` | Runner tạo các bước kiểm, lý do, rule version; `to_final` có `group`, `eligible`, `checks`, `reason`, `rule_version`; cache gắn mốc nguồn và phiên bản | Có thể nhận kết quả kiểm tra đề xuất như evidence của RQ, không chạy lại toàn bộ nghiệp vụ nguồn trong M2 |

Chỉ đếm metadata thấy **5 file hồ sơ YAML không bắt đầu bằng `_`**; không mở giá trị của chúng. Đây không phải bằng chứng đã có đủ 33 nhóm G hoặc đã có mapping kế toán.

**Các khái niệm phải phân biệt:** `group/eligible` của kết quả kiểm tra không tự là nhóm G, mức Xanh/Vàng/Đỏ hoặc quyền duyệt bút toán. `loai` của hồ sơ và `ma_cu.policy_type/utility_type` là khóa nguồn/crosswalk khả dụng, chưa có bằng chứng tự trùng danh mục nhóm G. Schema đã xem không định nghĩa bộ TK/khoản mục/TTCP tương đương bảng ánh xạ kế toán.

**Bridge cần làm:** danh mục dùng chung giữ khóa nội bộ, mã loại nguồn, version/hash và hiệu lực; crosswalk `loai` → nhóm G → Dự án/Vận hành → cấu hình kế toán; RQ tham chiếu kết quả nguồn bằng source request ID + rule version. Giữ kết quả chồng lấn/chưa phân loại thành việc cần xử lý, không tự chọn. Theo TL40, #1 dùng view `giao_tiep.v1_khoan_muc_phi` bằng vai trò chỉ đọc khi danh mục chung được công bố; không cho #1 quyền sửa bảng master.

**Chưa xác minh:** giá trị/độ phủ hồ sơ thực, từng mapping G, người sở hữu danh mục liên hệ thống và trạng thái công bố. Field `nguoi_xac_nhan` tồn tại không chứng minh ai đã được giao quyền chủ danh mục chung. Có thể lập crosswalk và báo sai khác bằng kỹ thuật trước; chỉ đưa Anh quyết định ownership hoặc xung đột nghiệp vụ cụ thể còn lại, không hỏi lại cấu trúc đã có.

## 2. #2 — Request thay Base

**Path:** `D:\Claude\Phan mem duyet kieu base`. Source xác nhận Next.js/TypeScript và Drizzle/PostgreSQL; không chỉ là suy luận từ tên file.

### Schema nguồn đã có

- `src/db/schema/requests.ts:75–162`: `requests` có UUID/code, `groupId`, **`groupVersionId`**, người tạo, **`companyId`**, tiêu đề/trạng thái, tiền/tiền tệ, số tiền/tiền tệ lúc gửi, attempt và các mốc tạo/cập nhật/gửi/quyết định.
- `requests.ts:183–192`: `request_values` giữ `requestId`, **`fieldCode`**, **`valueJson`**. Trường nghiệp vụ là động theo phiên bản nhóm, không giả định tên cột SQL cố định cho dự án, chi phí, người hưởng hoặc hóa đơn.
- `requests.ts:201` có chứng cứ từng bước/lần duyệt. Enum `:56–62`: `draft`, `in_review`, `returned`, `approved`, `rejected`. Trạng thái `approved` là hoàn tất chuỗi Request, không thay approval của bút toán kế toán.
- `src/db/schema/groups.ts:32/:68/:101`: nhóm, phiên bản và định nghĩa trường; có mã/nhãn/kiểu/bắt buộc/cấu hình field; nhóm có `amountFieldCode` và `companyFieldCode`. Có thể đọc định nghĩa để tạo mapping, không bắt Anh kê lại từng loại field.

### API và webhook đã có source

| Cửa/interface | Contract đã xác minh | Căn cứ |
|---|---|---|
| `GET /api/v1/nhom`, danh mục theo mã | Đọc định nghĩa nhóm, field và mã chọn để điền/mapping | `src/lib/api/doc.ts:53–113`; route trong `src/app/api/v1/nhom` và `danh-muc/[ma]` |
| `GET /api/v1/de-xuat` | Lọc nhóm, trạng thái, ngày tạo, **`capNhatSau`**, phân trang; `soDong` tối đa 200; trả `trang/soDong/tongSo/duLieu` | `src/app/api/v1/de-xuat/route.ts:8–59` |
| Dòng danh sách | `id`, `ma`, `tieuDe`, nhóm, trạng thái, người tạo, `tongTien={amount,currency}`, tạo/gửi/cập nhật, link chi tiết | `src/lib/api/doc.ts:193–235` |
| `GET /api/v1/de-xuat/{id}` | Field definitions + `giaTri`, chuỗi duyệt/lần gửi/bước/người/thời điểm, file metadata, trạng thái ô máy điền | `src/app/api/v1/de-xuat/[id]/route.ts:8–17`; `src/lib/api/doc.ts:268–335` |
| Nhật ký/tệp | Có route nhật ký và tệp; link tải chỉ trả cho tệp đã quét sạch | `src/app/api/v1/de-xuat/[id]/nhat-ky/route.ts`; `doc.ts:325–333` |
| POST/PATCH nháp | Tạo/sửa nháp với nhóm, tiêu đề, người tạo, giá trị và ô máy điền; có `Idempotency-Key`; đã gửi thì không sửa qua cửa này | `de-xuat/route.ts:62–97`; `[id]/route.ts:20–44`; `src/lib/api/ghi.ts` |
| Webhook trạng thái | Hàng đợi sau giao dịch thành công, payload tối thiểu `id/ma/suKien/trangThai/luc/chiTiet`, ký HMAC-SHA256; retry theo lịch | `src/lib/api/webhook.ts:150–204` |

API nguồn đã cố ý **không cung cấp Gửi/Duyệt/Từ chối/Hoàn trả** qua cửa công cụ (`docs/api/huong-dan.md:8–18`). Giữ giới hạn này. Đã có migration schema cho API/idempotency/webhook, nhưng không suy rằng migration đã chạy hoặc máy chủ đã mở cửa.

**Mapping canonical RQ có thể bắt đầu ngay:**

| Trường kế toán | Nguồn Request | Cần kiểm khi làm adapter |
|---|---|---|
| Khóa RQ và provenance | `id`, `ma`, nguồn/version, mốc cập nhật | Unique theo nguồn + ID; không gộp với Base chỉ vì mã/tên giống |
| Pháp nhân | `companyId`, định nghĩa `companyFieldCode` | Map sang pháp nhân kế toán; không dùng nhãn tự do thay ID |
| Trạng thái/duyệt nguồn | `trangThai`, `chuoiDuyet`, lần gửi và mốc | Phân biệt đã duyệt RQ với đã duyệt bút toán; giữ lần gửi/trạng thái mới |
| Tiền | `{amount,currency}` | Decimal → minor units có kiểm tra; không ngầm mặc định currency |
| Dự án/chi phí/người hưởng/nhóm G/hóa đơn | `giaTri[fieldCode]` theo phiên bản nhóm và danh mục | Draft crosswalk từ field definitions; nhóm Request không mặc định là nhóm G |
| Tệp/căn cứ | Metadata field + link tệp sạch + nhật ký | Hash, trạng thái quét và quyền đọc; không nạp file chưa sạch |
| Đồng bộ | `capNhatSau`, phân trang, webhook hoặc hàng đợi | Cursor/checkpoint, overlap/dedup và đọc lại chi tiết; không lấy webhook làm toàn bộ chứng từ |

Webhook hiện có source là bằng chứng có thành phần phát sự kiện, **không tự đổi đường tích hợp đã chốt**. Theo TL40, producer/bridge trong nhà khi ghi về PostgreSQL kế toán chỉ dùng hàm/view `giao_tiep` bằng vai trò riêng. Tái dùng API đọc/contract/webhook hiện có hoặc nối producer vào hàng đợi; không cấp quyền bảng thật hoặc tạo thêm gateway ngoài vào chỉ vì tiện.

**Chưa xác minh:** deployment/go-live, key/quyền mạng hiện hành, giá trị các định nghĩa nhóm đang công bố, mapping field thực và khả năng tạo lệnh chi/UNC hoàn chỉnh. Có API nháp/field động không chứng minh đã có nghiệp vụ UNC. Không cần hỏi Anh “Request đã có API/schema chưa”; chỉ xử lý thông tin kết nối và các mapping không suy ra được sau khi dùng contract nguồn.

## 3. #4 — HR/Frappe `hcns_vn`

**Path hồ sơ Windows:** `D:\Claude\Phan mem HR`. Tại phạm vi đã kiểm kê chỉ thấy tài liệu, không có source ứng dụng/schema DocType để xác minh trực tiếp.

`CLAUDE.md:11/:17–18` xác định code nằm trong WSL tại `~/hcns/frappe-bench/apps/hcns_vn`; thay đổi qua Custom Field/Property Setter/Workflow/fixtures và `doc_events`. Tài liệu môi trường chỉ dẫn đường UNC dạng `\\wsl$\Ubuntu-24.04\home\<user>\hcns`, chưa cho một path user cụ thể. Không khởi động WSL/dịch vụ hoặc tìm rộng để truy code trong nhiệm vụ này.

**Đã xác minh từ đặc tả, chưa phải source:** `docs/KE_HOACH_TRIEN_KHAI.md:9–29` giới hạn giai đoạn 1 vào chấm công/ca/nghỉ và công tác/tạm ứng/quyết toán. **Cầu Excel hạch toán và tính lương/PIT/BHXH nằm ngoài giai đoạn 1.** Tài liệu có các document `Employee Advance`, `Expense Claim`, `Travel Request`, dự kiến overrides/hooks và báo cáo, nhưng chưa kiểm source/schema hoặc export đang hoạt động.

**Hướng tái sử dụng:** giữ HR làm nguồn nhân viên/tạm ứng/quyết toán; K1 đọc export/API được cấp riêng rồi map mã nhân viên Junsky, pháp nhân, kỳ, loại khoản, tiền tệ, trạng thái nguồn. Không xây lại chấm công/tính lương trong kế toán; không nối Frappe thẳng PostgreSQL kế toán. Khi kiểm được source mới chốt field contract và ánh xạ DocType thực, không tự dựa hoàn toàn vào schema Frappe mặc định vì có tùy biến.

**Còn thiếu thật:** source WSL được chỉ định chính xác hoặc gói schema/interface kỹ thuật xuất từ đó; đầu ra bảng lương đã được duyệt hiện dùng để nạp M7. Hồ sơ hiện có chưa trả lời “bảng lương hiện được lập ở đâu”, và không chứng minh HR đã có payroll export; không yêu cầu Anh thiết kế lại HR.

## 4. Thay câu hỏi cũ bằng việc thực hiện cụ thể

| Câu hỏi/giả định cũ | Kết luận sau kiểm tra | Việc còn làm |
|---|---|---|
| #1 đã có schema loại chi phí chưa? | **Có schema, validator, router, rule version** | Dùng lại schema; lập crosswalk/version và báo xung đột |
| #1 đã tương đương đủ 33 nhóm G chưa? | **Chưa chứng minh**; chỉ đếm metadata năm profile, không đọc giá trị | Đối chiếu cục bộ được phép và lập mapping; chỉ đưa quyết định ownership/xung đột cụ thể |
| #2 còn thiếu API/schema RQ để thiết kế từ đầu? | **Không**: source có schema phiên bản, API đọc/nháp/tệp và webhook | Viết adapter canonical RQ; giữ Base và Request là hai nguồn |
| Có cần chờ go-live mới thiết kế mọi bridge #2? | **Không cần chờ** để làm adapter/ca DEMO theo contract hiện có | Kết nối nguồn thật chỉ sau xác minh triển khai và quyền vận hành |
| Có thể lấy HR giai đoạn 1 làm nguồn bảng lương sẵn dùng? | **Chưa đủ bằng chứng**, đặc tả còn loại payroll/cầu hạch toán khỏi giai đoạn 1 | Kiểm source/schema/export WSL và nguồn bảng lương đã duyệt; không suy từ tên Frappe HR |

Chốt kiểm tra tĩnh tại đây. Không có tuyên bố đã deploy/go-live, đã đọc đủ danh mục thật, đã hoàn tất crosswalk hoặc đã chạy integration test.
