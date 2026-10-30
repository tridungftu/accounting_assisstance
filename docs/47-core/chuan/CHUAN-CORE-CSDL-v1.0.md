# CHUẨN CORE — CƠ SỞ DỮ LIỆU

**Tệp:** `CHUAN-CORE-CSDL-v1.0.md`  
**Phiên bản:** v1.0  
**Ngày Anh duyệt phiếu CSDL/API:** 30/10/2026 · **Văn bản chuẩn:** chờ Anh xem (CD-034 mục 4)

**Phạm vi:** cấu trúc, sở hữu, truy cập, phân quyền, toàn vẹn, mã hóa và migration CSDL của Core và các module.

**Căn cứ:**

- `docs\47-core\PHIEU-DUYET-CSDL.md`: Anh duyệt câu **1A, 2A, 3A**.
- `docs\47-core\PHIEU-DUYET-API.md`: Anh duyệt câu **1A, 2A**; áp dụng các quy tắc liên quan đến danh tính, transaction, chống trùng và cập nhật đồng thời.
- `docs\47-core\g1\DAC-TA-CSDL.md`, `ANH-XA-MIGRATION.md`, `DAC-TA-API.md`, `ANH-XA-ROUTE.md`.
- CD-026 đến CD-036 trong `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md`, trong phạm vi liên quan.

Đây là bản chuẩn thiết kế đích tập hợp các quyết định CSDL từ phiếu đã duyệt; văn bản chuẩn chờ Anh xem, **không phải xác nhận hệ thống đã triển khai**. Việc ban hành chuẩn không thay thế điều kiện duyệt đủ ba phiếu CSDL/API/SDK và CD mở lại lập trình.

## 1. Thay đổi

| Phiên bản | Ngày | Nội dung |
|---|---|---|
| v1.0 | 30/10/2026 | Bản đầu; tập hợp các quyết định đã duyệt thành hướng dẫn cho người lập trình module. |

v1.0 (sửa trước khi gửi Anh): theo review Opus + Codex

Mọi thay đổi sau bản này phải tăng phiên bản và ghi rõ nội dung thay đổi.

## 2. Kết luận

1. Dùng một CSDL PostgreSQL chung, chia khối theo chủ sở hữu dữ liệu.
2. Core giữ `loi`, `loi_tai_lieu`, `danh_muc`; module giữ `mod_<ma>`.
3. Module ghi dữ liệu chung qua hàm Core, đọc module khác qua `cong_bo_<ma>`.
4. Runtime không sở hữu bảng, không DDL, không `BYPASSRLS`.
5. CSDL tự xác minh mã phiên bí mật; biến danh tính tự đặt không tạo quyền.
6. RLS bảo vệ pháp nhân; MTQ quyết định hành động, hạn mức và phạm vi.
7. Kiểm tiền phải tính đủ dữ liệu cùng pháp nhân, kể cả dòng người thao tác không được xem.
8. Không FK chéo module; tham chiếu nghiệp vụ ghim ID và mã băm qua contract công bố.
9. Migration thuộc gói sở hữu đối tượng; dữ liệu nhóm A mã hóa qua cổng Core.
10. Hạn dọn tạm không áp dụng cho bản gốc, kết quả đã duyệt, audit nghiệp vụ hoặc biên nhận nghiệp vụ module.

## 3. Bắt buộc

Mục gắn [Core] do Core dựng — module chỉ cần không vi phạm; mục gắn [Module] là việc người lập trình module phải làm.

### 3.1. Khối dữ liệu, chủ sở hữu và đường truy cập

“Khối” trong chuẩn này là ranh giới sở hữu và cấp quyền CSDL, được tổ chức bằng schema PostgreSQL.

| Khối | Chủ và nội dung | Ai ghi, qua đâu | Ai đọc, qua đâu |
|---|---|---|---|
| `loi` | Core: người dùng, pháp nhân, MTQ, registry module/engine/contract, sổ cổng, quy trình, hàng việc, bus, audit, lịch sử migration | Dịch vụ Core; module gọi hàm Core được cấp quyền | Core theo chức trách; module qua hàm đọc Core |
| `loi_tai_lieu` | Core: tài liệu, tệp, biến thể, quyền nội dung, kết quả, nguồn kết quả, metadata tiếp nhận, vùng tạm, biên nhận thao tác | Dịch vụ kho/tiếp nhận Core; module gọi hàm Core; engine trả kết quả cho Core lưu | Qua dịch vụ/hàm Core; tải bytes phải kiểm quyền |
| `danh_muc` | Core: đối tác, dự án, tài khoản, định danh hợp đồng, đầu chứng từ, định danh hóa đơn, khóa kỳ, liên kết/phân bổ chung | Qua hàm Core V2 có kiểm quyền và toàn vẹn | Tập cột danh mục hoặc hàm đọc được cấp; áp RLS |
| `mod_<ma>` | Module tương ứng: bảng, trạng thái, phiên bản và quy tắc nghiệp vụ riêng | Runtime của chính module, theo quyền được cấp, bằng bảng/hàm riêng | Chính module; bên khác qua `cong_bo_<ma>` |
| `cong_bo_<ma>` | Module nguồn: view/hàm đọc có contract và phiên bản | Gói migration của module dựng định nghĩa; runtime không DML trên mặt công bố | Module được cấp quyền đọc đúng contract |
| `ke_toan_cu` | Chủ chuyển tiếp kế toán: phần nghiệp vụ cũ chưa chuyển | Adapter chuyển tiếp trong phạm vi đã khai báo; dữ liệu chung vẫn ghi qua Core | Qua adapter, hàm hoặc mặt công bố chuyển tiếp được cấp |

Các ranh giới sau phải được giữ:

- Định danh hợp đồng chung ở `danh_muc`; phiên bản bán hàng, tham số và lịch nghĩa vụ thuộc CRM.
- Đầu chứng từ ở `danh_muc.chung_tu`; dòng chứng từ kế toán cũ còn ở `ke_toan_cu`.
- `danh_muc.khoa_ky` là nguồn khóa kỳ duy nhất. Adapter cũ cũng phải gọi Core để kiểm khóa kỳ.
- Định danh hóa đơn ở `danh_muc.hoa_don_danh_tinh`; quan sát, phiên bản, dòng và các con trỏ trạng thái thuộc M2.
- Metadata tiếp nhận, lần tiếp nhận và vùng tạm dùng chung thuộc Core. M0 chỉ giữ cấu hình tự động lấy nguồn riêng.
- Không chuyển nguyên schema cũ `master` hoặc `kho` vào Core; phải phân loại từng đối tượng theo chủ.
- Dữ liệu cũ chưa xác định được chủ phải giữ ở phần chuyển tiếp tương ứng, chưa công bố thành dữ liệu nghiệp vụ chính thức.

Khối `ke_toan_cu` phục vụ chuyển tiếp, không phải nơi đặt chức năng mới của module.

### 3.2. Khai báo bốn vùng truy cập

Module phải khai báo cụ thể tài nguyên và thao tác cần dùng.

| Vùng | Nội dung được phép |
|---|---|
| V1 — riêng | Bảng/hàm của `mod_<ma>` thuộc chính module |
| V2 — ghi chung | Hàm Core được cấp trong `loi`, `loi_tai_lieu`, `danh_muc`; không ghi trực tiếp bảng chung |
| V3 — danh mục chung | Chỉ đọc phần danh mục chung được cấp |
| V4 — công bố | Chỉ đọc contract được cấp của `cong_bo_<nguon>`; sự kiện đi qua bus Core |

Biên nhận chống trùng của operation module ghi qua hàm V2 vào `loi_tai_lieu.bien_nhan_thao_tac`, cùng transaction và cùng kết nối với thay đổi nghiệp vụ; bất biến, giữ vĩnh viễn (chi tiết CHUAN-CORE-API §3.6b).

Không được khai bảng nghiệp vụ của module khác thành V3 để hợp thức hóa truy cập. Không dùng view hoặc hàm trong schema của mình để che việc đọc bảng riêng của bên khác.

Khai báo nhu cầu trong gói không đồng nghĩa đã được cấp quyền. Quyền truy cập phải khớp đồng thời bản đồ truy cập, quyền thực tế được Core cấp, ACL, RLS và MTQ.

### 3.3. Quy tắc đặt tên

Tên schema, bảng, cột và tên kỹ thuật nghiệp vụ dùng tiếng Việt không dấu, dạng `snake_case`. Giữ các mã kỹ thuật đã được định nghĩa và tên chuẩn của PostgreSQL, API, thư viện hoặc protocol.

| Nội dung | Tên hoặc mẫu tên |
|---|---|
| Schema nghiệp vụ module | `mod_<ma>` |
| Schema công bố | `cong_bo_<ma>` |
| Phạm vi pháp nhân | `phap_nhan_id` |
| Người dùng | `nguoi_dung_id` |
| Phiên bản dòng trong CSDL | `phien_ban_dong` |
| Phiên bản dòng trên API | `row_version` |
| Truy vết tạo/cập nhật | `tao_luc`, `tao_boi`, `cap_nhat_luc`, `cap_nhat_boi` |
| Khoảng hiệu lực | `hieu_luc_tu`, `hieu_luc_den` |
| Chống trùng | `khoa_chong_trung` |
| Nội dung sự kiện | `noi_dung_su_kien` |
| Sổ migration | `loi.lich_su_doi_cau_truc` |
| Thông tin migration | `ma_goi`, `so_phien_ban`, `ma_bam`, `ap_dung_luc` |
| Vai chạy | `vai_chay_<khoi>` |
| Vai đổi cấu trúc | `vai_doi_cau_truc_<khoi>` |

Không đổi tên rồi giữ nguyên quyền rộng của mô hình cũ. Đổi schema cũng không đồng nghĩa viết lại bảng hoặc thay UUID, trạng thái và khóa nghiệp vụ đang đúng.

Phải phân biệt:

- `lan_thu`: lần thử thực thi một bước việc.
- `lich_thu`: lịch nghĩa vụ thu thuộc CRM.
- `phien_ban_dong`: bộ đếm CAS của dòng.
- Phiên bản hồ sơ, revision kết quả, phiên bản contract và mã băm căn cứ: các khái niệm riêng, không thay bằng `phien_ban_dong`.

Trường JSON dùng tiếng Việt không dấu theo quy ước chung; các tên kỹ thuật đã chốt như `row_version`, `request_id` được giữ nguyên.

### 3.4. Kiểu dữ liệu và quan hệ cùng pháp nhân

| Loại dữ liệu | Quy tắc |
|---|---|
| ID nghiệp vụ mới | Dùng UUID |
| Khóa cũ | Giữ kiểu và ý nghĩa hợp lệ; không ép toàn bộ khóa text hoặc khóa kỹ thuật sang UUID |
| Tiền, tỷ lệ | Dùng `numeric`; đặc tả rõ độ chính xác, giới hạn, đơn vị và cách làm tròn |
| Đơn vị tiền | Có thông tin đơn vị đi cùng số tiền; API dùng `don_vi_tien` |
| Thời điểm | Dùng `timestamptz` |
| Ngày nghiệp vụ | Dùng `date` |
| JSON | Có phiên bản cấu trúc và contract kiểm tra tương ứng |
| Dòng sửa đồng thời | Có `phien_ban_dong > 0`; cập nhật phải khớp phiên bản mong đợi |

Không dùng số thực dấu phẩy động để biểu diễn tiền. API trao đổi tiền bằng chuỗi decimal; `row_version` là chuỗi số nguyên để tránh mất chính xác trong JavaScript.

Cập nhật CAS phải so sánh và ghi nguyên tử. Sai phiên bản trả xung đột 409; không ghi đè. Nếu nghiệp vụ còn yêu cầu `expected_revision`, phiên bản mẫu hoặc mã băm căn cứ thì phải giữ các kiểm tra đó.

Không chuyển cơ học các cột `_minor` hiện hữu sang tiền đã quy đổi. Phải giữ đơn vị nhỏ nhất, tiền tệ và thang tiền của dữ liệu nguồn. Không biến dữ liệu thiếu căn cứ thành số 0.

Quan hệ cha–con thuộc pháp nhân phải dùng khóa ghép hoặc kiểm tương đương để ngăn gắn chéo pháp nhân. Không mặc định `ON DELETE CASCADE` cho hồ sơ nghiệp vụ.

Bảng chỉ ghi thêm không bắt buộc có cột cập nhật. Khóa kỹ thuật `bigserial` của audit cũ được giữ, không đổi sang UUID chỉ để đồng dạng.

### 3.5. Role PostgreSQL và login theo tiến trình

#### 3.5.1. Cặp role của khối

Mỗi khối dữ liệu được cài có hai role cố định:

| Role | Quyền và giới hạn |
|---|---|
| `vai_chay_<khoi>` | `NOLOGIN`; không superuser, `BYPASSRLS`, `CREATEROLE`, `CREATEDB`; không sở hữu bảng; không DDL |
| `vai_doi_cau_truc_<khoi>` | `NOLOGIN`; sở hữu schema/đối tượng của khối; chỉ dùng qua cơ chế cài đặt/bảo trì |

Áp dụng cho `loi`, `loi_tai_lieu`, `danh_muc`, `mod_*`, `ke_toan_cu`.

Ngoại lệ của mặt công bố:

- Schema `cong_bo_<ma>` do `vai_doi_cau_truc_mod_<ma>` quản lý.
- View công bố do `vai_doc_cong_bo_<ma>` sở hữu.
- `vai_doc_cong_bo_<ma>` là `NOLOGIN`, chỉ có SELECT các cột nguồn cần thiết; không sở hữu bảng nguồn, không DML, không `BYPASSRLS`.
- Không tạo `vai_chay_cong_bo_<ma>` và không có tiến trình công bố riêng.

#### 3.5.2. Login từng loại tiến trình

| Tiến trình | Login CSDL | Phạm vi |
|---|---|---|
| Core và worker Core nội bộ | `dang_nhap_loi` | Ba role chạy Core: `vai_chay_loi`, `vai_chay_loi_tai_lieu`, `vai_chay_danh_muc` |
| Module X | `dang_nhap_mod_x` | Chỉ role chạy riêng; thêm SELECT/EXECUTE đúng danh mục, contract và hàm Core được cấp |
| Adapter kế toán chuyển tiếp | `dang_nhap_ke_toan_cu` | Role chạy chuyển tiếp và giao diện đã khai báo; không làm login chung cho module |
| Engine và worker máy phụ | Không có login CSDL | Nhận việc, đầu vào và trả kết quả qua API Core |
| Cài đặt/bảo trì | `dang_nhap_cai_dat` | Login riêng, chỉ phục vụ phiên bảo trì và áp gói đã kiểm |

Mỗi module là một tiến trình riêng. Trên một máy triển khai chỉ có một phiên hoạt động cho một mã module; dùng lease, thế hệ sở hữu và CAS để chống chạy trùng.

#### 3.5.3. [Core] Membership PG16 và cài đặt

Membership dùng:

```text
INHERIT TRUE, SET FALSE, ADMIN FALSE
```

Runtime không được nhận membership của owner, role đọc công bố hoặc role kiểm toàn vẹn. Không được dùng nhóm quyền cũ rộng để mọi module cùng thừa hưởng.

Cơ chế cài đặt phải đáp ứng `SET FALSE`:

1. Quản trị provisioning role và hàm áp gói `SECURITY DEFINER` của từng owner.
2. `dang_nhap_cai_dat` chỉ được EXECUTE hàm áp gói đã kiểm nguồn và mã băm trong phiên bảo trì.
3. Không nhận SQL tùy ý do runtime cung cấp.
4. Đối tượng được tạo ngay dưới đúng owner; không dựa vào `SET ROLE` hoặc `ALTER OWNER` của login cài đặt.
5. Đối tượng thuộc role kiểm toàn vẹn hoặc role công bố cũng phải được provisioning hay tạo qua hàm của đúng owner.

Login cài đặt không phải superuser và không xử lý request nghiệp vụ.

#### 3.5.4. [Core] Giữ và trao mật khẩu

Mật khẩu ở `D:\DU-LIEU-KE-TOAN\bi-mat\`, ngoài thư mục phần mềm, bảo vệ theo tài khoản dịch vụ.

Core trao đúng mật khẩu login cho tiến trình module qua stdin hoặc handle kế thừa được kiểm soát. Không đưa mật khẩu vào biến môi trường, dòng lệnh, manifest hay log.

Mật khẩu cài đặt do chức trách bảo trì giữ. Engine và máy phụ không nhận mật khẩu CSDL.

Theo CD-033, Core chạy dưới tài khoản Windows riêng; module/engine chạy dưới tài khoản hạn chế, áp dụng ngay từ giai đoạn thử. Bộ kiểm phải xác nhận tiến trình module/engine không đọc được thư mục bí mật.

### 3.6. Mã phiên bí mật, mã ủy nhiệm và RLS

#### 3.6.1. Danh tính phải do Core xác lập

[Core] Core tự quản tài khoản người dùng và cấp mã phiên bí mật. CSDL không tin danh tính chỉ vì module đã đặt biến ngữ cảnh.

`loi.phien_xac_thuc` lưu:

- Băm mã bí mật, không lưu nguyên mã.
- Người dùng, pháp nhân, module và login CSDL được nhận.
- Hạn dùng, trạng thái thu hồi và phạm vi hành động.
- `viec_id` và thế hệ giữ việc khi là mã ủy nhiệm việc.

Mỗi phạm vi module–pháp nhân có mã tương ứng. Worker dùng mã riêng theo việc, không dùng lại phiên người dùng.

Hàm xác minh phải đối chiếu băm mã với phiên và kiểm:

- Còn hạn, chưa thu hồi.
- Đúng `session_user`, module và pháp nhân.
- Đúng hành động/phạm vi được ủy nhiệm.
- Đúng việc và thế hệ giữ việc, nếu có.

Runtime không được SELECT/DML bảng phiên.

Các biến `ktt.nguoi_dung_id`, `ktt.nguoi_dung_dang_nhap` chỉ dùng đối chiếu. Thay chúng không được làm thay đổi danh tính đã xác minh. Ngày hiệu lực cũng phải có căn cứ do Core xác định, không tin ngày module tự đặt.

#### 3.6.2. Vòng đời transaction

[Module] Mỗi transaction nghiệp vụ phải:

1. Dùng kết nối của đúng login module/Core.
2. Nhận mã phiên hoặc mã ủy nhiệm hợp lệ do Core cấp.
3. Đặt ngữ cảnh bằng `SET LOCAL` hoặc `set_config(..., true)`.
4. CSDL xác minh mã trước truy cập; kiểm phạm vi, quyền module, MTQ và quyền nội dung.
5. Commit hoặc rollback; không để ngữ cảnh rò sang request sau khi tái sử dụng kết nối.

Giữ namespace `ktt.*` đang dùng khi phù hợp; không tạo namespace khác chỉ để đổi tên.

Mã phiên phải truyền bằng tham số bind. Không ghi giá trị tham số trong log:

```text
log_parameter_max_length = 0
log_parameter_max_length_on_error = 0
```

Không lưu kết quả xác minh vào GUC hoặc bảng tạm mà runtime có thể ghi. Mỗi lần cần phải xác minh lại từ băm; hàm xác minh dùng `STABLE` và tra cứu có chỉ mục theo đặc tả.

#### 3.6.3. Phân biệt thẻ chuyển tiếp và mã CSDL

Core chuyển tiếp request sang module bằng thẻ ký có TTL tối đa 30 giây, mang mã ủy nhiệm bí mật và các ràng buộc request. Module phải kiểm chữ ký, đối tượng nhận, thời hạn, nonce và ràng buộc request.

Thẻ ký không thay việc CSDL kiểm mã ủy nhiệm. Không chuyển cookie/SID người dùng sang module.

Mã ủy nhiệm theo phiên không dài hơn phiên người dùng; phải thu hồi khi đăng xuất, thu hồi phiên hoặc thay đổi quyền. Việc nền dùng mã gắn việc và thế hệ lease, không giữ token HTTP để dùng về sau.

#### 3.6.4. Chính sách RLS

Bảng nghiệp vụ thuộc pháp nhân phải bật RLS và `FORCE ROW LEVEL SECURITY`, có kiểm cho cả `USING` và `WITH CHECK`.

- Thiếu hoặc sai ngữ cảnh phải từ chối.
- Không cho đổi `phap_nhan_id` để chuyển hồ sơ.
- `phap_nhan_id IS NULL` không phải cửa đọc toàn hệ thống.
- Bảng xác thực/quản trị toàn cục có chính sách riêng, tránh vòng đệ quy khi tra quyền.
- Mọi owner của hàm `SECURITY DEFINER` phải có policy tường minh phù hợp; dưới FORCE RLS, thiếu policy sẽ không thấy dòng.

RLS lọc theo pháp nhân từ phiên đã xác minh. MTQ là nguồn quyết định hành động, hạn mức và phạm vi; không tạo ma trận quyền thứ hai trong policy.

Đối tượng nhiều pháp nhân phải đạt quyền ở mọi pháp nhân. Trường hợp hỗn hợp bật/tắt MTQ phải bị chặn theo quyết định đã duyệt.

Dữ liệu tiếp nhận chưa xác định pháp nhân được Core giữ trong vùng tiếp nhận/vùng tạm, kiểm bằng quyền nguồn và lần tiếp nhận. Không gắn pháp nhân giả để đi qua RLS.

#### 3.6.5. Việc nền và tải tệp

Việc nền phải lưu người tạo, pháp nhân, module, phiên bản contract và phạm vi ủy nhiệm. Kiểm lại quyền khi nhận việc, trước bước nhạy cảm, trước ghi và trước công bố kết quả.

Quyền bị thu hồi phải chặn hoặc chuyển chờ có lý do. Sau gián đoạn, mã thế hệ cũ phải bị thu hồi trước khi cấp lần thử mới.

Tải tệp phải kiểm tài liệu/kết quả, pháp nhân, biến thể và trạng thái duyệt trước khi trả bytes. Biết ID, hash hoặc đường dẫn không tạo quyền.

### 3.7. Kiểm toàn vẹn tiền dưới FORCE RLS

Hai ràng buộc phải được kiểm độc lập:

- Tổng liên kết/phân bổ không vượt tiền chứng từ.
- Tổng liên kết/phân bổ không vượt nghĩa vụ.

Phép tính phải dùng **đủ các dòng liên quan trong pháp nhân đã xác minh**, kể cả dòng người thao tác không có quyền xem.

#### 3.7.1. [Core] Role và policy kiểm riêng

Khối cần tính tổng có `vai_kiem_toan_ven_<khoi>`:

- `NOLOGIN`, không `BYPASSRLS`, không membership cho runtime.
- Chỉ có quyền SELECT và khóa dòng cần thiết.
- Sở hữu hàm kiểm hẹp.
- Có policy riêng chỉ lọc pháp nhân đã xác minh; không lọc module, người dùng hoặc quyền M1.
- Policy `RESTRICTIVE`, nếu có, cũng không được làm thiếu tổng của role kiểm.

Hàm nội bộ chỉ trả kết luận/mã lỗi cần thiết; không trả dòng hoặc tổng bị che cho runtime.

Core kiểm tiền chứng từ. [Module] Module chủ kiểm nghĩa vụ; khi cần tổng liên kết chung, dùng hàm tổng Core nội bộ được cấp cho role kiểm đã đăng ký, không SELECT bảng chéo.

Khóa bằng `SELECT … FOR UPDATE` cần quyền UPDATE trên một cột kỹ thuật và policy UPDATE USING. Nếu không cấp được, dùng `pg_advisory_xact_lock` theo ID, giữ đúng thứ tự khóa.

#### 3.7.2. Transaction liên kết

Toàn bộ các bước sau phải nằm trong **một transaction và một kết nối**:

1. Core xác thực, kiểm MTQ, cùng pháp nhân và tiền tệ.
2. Khóa các đầu chứng từ theo thứ tự ID.
3. Gọi resolver module chủ qua registry để khóa nghĩa vụ và kiểm căn cứ.
4. Ghi liên kết/phân bổ.
5. Kiểm cuối: Core kiểm giới hạn chứng từ; module chủ kiểm giới hạn nghĩa vụ.
6. Chỉ commit khi mọi kiểm tra đạt.

Không gọi HTTP để kiểm tiền giữa transaction. Không commit riêng một phần rồi kiểm phần còn lại.

Thứ tự khóa chứng từ → nghĩa vụ phải thống nhất cho tạo, sửa, hủy và giảm sức chứa nghĩa vụ. Giảm sức chứa không được bỏ qua các liên kết đã tồn tại.

Thiếu module hoặc chưa đủ căn cứ trả `CHO` có lý do và không commit liên kết.

#### 3.7.3. Ca kiểm bắt buộc

| Ca | Điều kiện | Kết quả |
|---|---|---|
| Giới hạn chứng từ | Người không có quyền M1 nhưng được phép tạo liên kết; đã nối 80 bằng dòng bị che; chứng từ 100, nghĩa vụ đủ lớn; thêm 30 | Từ chối |
| Giới hạn nghĩa vụ | Cùng tình huống quyền; nghĩa vụ 100, chứng từ đủ lớn; đã nối 80 bị che; thêm 30 | Từ chối |
| Cạnh tranh | Bắt đầu từ 0, giới hạn 100; hai transaction cùng nối 60 | Không được cùng commit |
| Sửa/hủy/giảm sức chứa | Có liên kết hiện hữu và thao tác đồng thời | Giữ đúng giới hạn và thứ tự khóa |
| Sai quyền/phạm vi | Thiếu quyền hành động, sai pháp nhân hoặc giả mã phiên | Từ chối, không lộ dòng/tổng bị che |

### 3.8. Không FK chéo module; ghim căn cứ qua công bố

FK từ module về định danh Core được phép theo bản đồ dữ liệu. Không tạo FK giữa hai module và không tạo FK từ Core tới bảng nghĩa vụ riêng của module tùy chọn.

Nghĩa vụ được nhận diện bằng bộ ba:

```text
(module_nghia_vu, loai_nghia_vu, nghia_vu_id)
```

Bộ ba không tự chứng minh nghĩa vụ tồn tại hay hợp lệ. Resolver của module chủ phải xác minh.

Khi sử dụng phiên bản, quan sát hoặc dòng nghiệp vụ của module khác, phải lưu ID căn cứ và mã băm tương ứng, trong đó có `ma_bam_phien_ban_can_cu` khi áp dụng. Kiểm qua `cong_bo_<nguon>` lúc ghi:

- Đúng contract và phiên bản đã ghim.
- Căn cứ tồn tại, cùng pháp nhân.
- Trạng thái và đơn vị phù hợp.
- ID và mã băm khớp.

Không tự thay căn cứ bằng bản mới nhất.

Mặt công bố phải:

- Có phiên bản, trường, nghĩa, đơn vị, trạng thái, quyền và điều kiện công bố.
- Dùng dữ liệu bền vững và đối tượng CSDL đã cài; không đòi tiến trình nguồn đang chạy.
- Tiếp tục tuân công tắc module và quyền hiện hành.
- Đổi phiên bản khi phá tương thích, không thay âm thầm bản cũ.

View công bố bật `security_barrier`, không bật `security_invoker`. Policy bảng nguồn của owner view phải xác minh phiên, pháp nhân và quyền contract; module nhận không có quyền bảng nguồn.

[Module] Resolver là hàm `SECURITY DEFINER` của module chủ, được Core gọi động qua `loi.dang_ky_ham_module`. Registry lưu chữ ký, owner và mã băm gói; chỉ chức trách cài đặt được sửa. Không nhận tên hàm tùy ý từ client.

Thiếu dữ liệu/contract trả `CHO`; sai quyền trả lỗi quyền. Hai trường hợp không được đánh đồng.

### 3.9. Sổ contract và lớp dữ liệu giao tiếp

Gói module phải có `contract/`, được liệt kê trong `module.json`, gồm dữ liệu công bố, sự kiện phát/nhận và đầu vào nguồn thuộc phạm vi module.

Mỗi contract có mục đích, chủ sở hữu, bên được đọc, phiên bản, danh sách trường, nghĩa, tính bắt buộc, đơn vị, nguồn, JSON Schema và ví dụ JSON đầy đủ. Thiếu hoặc không hợp lệ thì không cài.

Core giữ một bảng cố định `loi.dang_ky_contract`:

- Khóa mã và phiên bản.
- Chủ sở hữu Core/module.
- Binding module và phiên bản module đang dùng.
- Trạng thái `nhap`, `anh_duyet`, `dang_dung`, `ngung`.
- Metadata, schema/mã băm, bằng chứng duyệt và mốc sắp ngừng.

Mỗi contract/phiên bản mới là thêm dòng, không tạo bảng theo contract hoặc lần cài.

Core kiểm và đăng ký khi cài/nâng cấp bằng cơ chế chung; module không ghi trực tiếp sổ và không yêu cầu sửa code Core theo từng module mới.

Contract nghiệp vụ mới hoặc phiên bản mới của contract đang dùng phải được **Anh duyệt trước khi kích hoạt**. Admin cấp quyền không thay thế việc Anh duyệt contract.

Đăng ký contract không tự cấp quyền đọc. Truy cập chéo chỉ hợp lệ khi có contract đúng phiên bản đã đăng ký **và** quyền thực tế đã cấp.

Giữ phiên bản cũ cho module, module tạm tắt và việc còn ghim bản đó. Không chuyển ngầm sang bản mới; chưa hết binding thì chưa ngừng hoặc thu hồi mặt đọc. Contract trùng nghĩa hoặc truy cập ngoài contract/quyền phải làm bộ kiểm đỏ.

### 3.10. Hàm đặc quyền và quyền PUBLIC

Mỗi hàm đặc quyền phải xác định được owner, chữ ký, caller được phép và tập tài nguyên có thể chạm tới.

- Owner không phải login runtime hoặc superuser; hàm kiểm toàn vẹn dùng role kiểm riêng.
- `search_path` cố định với `pg_catalog`, các schema tin cậy tối thiểu, `pg_temp` cuối; định danh đầy đủ đối tượng.
- Runtime không có `CREATE` trên schema tin cậy.
- Chỉ cấp EXECUTE đúng chữ ký cho đúng role; hàm nội bộ không công khai.
- Wrapper phải kiểm danh tính, module, pháp nhân, hành động và căn cứ.
- Thu hồi quyền PUBLIC không cần thiết trên schema, bảng, sequence và hàm của hệ thống.
- Thiết lập default privileges theo từng role tạo đối tượng.
- Với schema dùng chung hoặc extension hiện hữu, chỉ thay quyền sau khi kiểm phụ thuộc.

Không coi `SECURITY DEFINER` là cách bỏ qua RLS hay kiểm nghiệp vụ.

### 3.11. Mã hóa cột nhóm A qua cổng Core

Nhóm A đã duyệt phải mã hóa. Nhóm B **chờ Anh**. Nhóm C gồm tiền, ngày và mã nội bộ giữ rõ theo quyết định đã duyệt.

| Nhóm dữ liệu nhạy cảm | Khối giữ bản mã |
|---|---|
| A1–A4: CCCD, định danh cá nhân, số tài khoản ngân hàng, MST cá nhân | `danh_muc`; riêng phần nhân viên cũ còn ở `ke_toan_cu` |
| A5–A7: tài khoản trong ánh xạ tiền, điều kiện học sao kê, dữ liệu nhạy cảm trong nguồn/chứng từ/dòng/tri thức cũ | `ke_toan_cu`; rà cả phần đầu chứng từ ở `danh_muc` và nguồn tiếp nhận ở `loi_tai_lieu` |
| A8: SĐT/email cá nhân trong dữ liệu báo giá, soạn và tóm tắt hợp đồng CRM | `mod_crm` |
| A9: địa chỉ/giấy tờ trong tham số, trích xuất và lịch sử M4 | `mod_m4` |
| A10: giá trị thật trong ánh xạ mở che cũ | `ke_toan_cu`, chỉ adapter cổng Mask dùng; ánh xạ Mask v2 vẫn do Mask quản lý ngoài CSDL này |

Quy tắc thực hiện:

1. Mã hóa/giải mã qua cổng hạ tầng Core dùng chung; riêng mở che qua cổng Mask hiện có.
2. [Core] `vai_chay_loi` phục vụ cổng giải mã nhận bản mã qua hàm đọc hẹp sau xác thực, MTQ, quyền nội dung và audit ID.
3. Module, view công bố, role kiểm, role xuất, engine và máy phụ không được giải mã tùy ý.
4. [Core] Khóa được bọc DPAPI theo tài khoản dịch vụ, giữ ngoài phần mềm/CSDL tại `bi-mat`; chỉ ở RAM dịch vụ được phép, tách khóa backup.
5. [Core] Không truyền khóa qua GUC hoặc tham số SQL, **kể cả bind**. Không có hàm giải mã PostgreSQL nhận khóa SQL.
6. [Core] Lưu bản mã và phiên bản khóa; tra cứu bằng HMAC có khóa độc lập, giữ miền UNIQUE và quy tắc chuẩn hóa. Không dùng hash trần cho số tài khoản.
7. Chỉ hiện bốn số cuối; xem đủ cần quyền và audit. Log không chứa bản rõ hoặc khóa.
8. Rà cả bản sao, JSON path và lịch sử; không chỉ mã hóa bảng chính.

Mã phiên dùng bind theo §3.6; **khóa mã hóa không được truyền qua SQL**. Đây là hai loại bí mật có cách xử lý khác nhau.

Các JSON path cụ thể phải chốt theo danh mục trường trước G2. Thuật toán/adapter cổng mã hóa còn chờ lead chốt trong lát API/SDK; chuẩn này không tự chọn thêm. G2 phải kiểm canary trong log thành công/lỗi, đổi khóa và phục hồi.

### 3.12. Migration trong gói module

Migration nằm trong gói sở hữu đối tượng. Core chỉ mang migration của `loi`, `loi_tai_lieu`, `danh_muc`; module mang migration của phần riêng và mặt công bố/resolver của mình.

#### 3.12.1. Sổ, checksum và kích hoạt

`loi.lich_su_doi_cau_truc` ghi:

```text
ma_goi, so_phien_ban, ma_bam, ap_dung_luc
```

Sổ còn ghi người áp dụng và nguồn lịch sử theo đặc tả CSDL §7; chuẩn này chỉ mô tả ý nghĩa, không ấn định tên cột khi đặc tả chưa định nghĩa.

Khóa sổ là `(ma_goi, so_phien_ban)`. Module không ghi trực tiếp sổ Core.

- Kiểm checksum và tương thích; không hợp thức hóa sai khác bằng sửa hash lịch sử.
- Giữ nguyên số/hash của 67 migration cũ và các trường hợp tương thích đã xác định.
- Gói đích có phiên bản/checksum riêng, liên hệ được nguồn lịch sử.
- Ghi sổ và thay đổi CSDL phải nhất quán trong transaction khi kỹ thuật cho phép.
- Thao tác filesystem dùng staging và bước kích hoạt riêng.
- Đăng ký contract phải nhất quán với cài/kích hoạt; thất bại không để contract hoạt động một phần.
- Runtime chỉ kiểm tương thích, không tự migrate khi kết nối.

#### 3.12.2. Thứ tự cài phụ thuộc

| Bước | Phạm vi | Yêu cầu |
|---|---|---|
| 1 | Core nền | Role/login/schema → danh tính/pháp nhân/phiên → audit/sổ migration → registry module/engine/hàm |
| 2 | Core dịch vụ chung | MTQ/công tắc → tài liệu/tiếp nhận → danh mục → sổ cổng/việc/bus/số đo; có policy toàn vẹn và cổng V2 |
| 3 | M4, mẫu đầu tiên G4 | Dựng phần riêng và công bố/resolver; chưa có M2 thì thao tác phụ thuộc trả `CHO`, không chặn dựng gói |
| 4 | CRM | Dựng nghiệp vụ riêng, công bố và resolver |
| 5 | M2 | Dựng quan sát/phiên bản/dòng/con trỏ và công bố/resolver |
| 6 | Module khác và gói chuyển tiếp | Theo phụ thuộc contract |

Core không được có phụ thuộc DDL bắt buộc vào module tùy chọn. Mỗi gói dựng mặt công bố của mình, không trì hoãn mọi công bố đến cuối.

Đây là thứ tự phụ thuộc CSDL. Lựa chọn CRM làm module thử Core ở G2 theo CD-033/CD-035 không đổi M4 là mẫu đầu tiên của G4. Theo CD-035, G2 Core và G3 năm engine được tổ chức song song sau khi đủ điều kiện mở lập trình.

#### 3.12.3. Bảo toàn khi tách lịch sử

Tách migration theo chủ của **định nghĩa cuối cùng**, gồm trigger, policy, ACL và khóa phối hợp. Không lấy riêng định nghĩa khai sinh rồi làm mất các guard đã vá sau đó. Role migration Core không sửa thân hàm module.

Khi chuyển lịch sử phải giữ:

- M0013 theo lineage `COMMON`, không dùng nhầm full-M9 lịch sử.
- M0017 theo SQL import hiện hành, không dùng bản partial khác.
- Validator đích giữ cả nhánh NGUON của M0067 và ghim/kiểm HOP_DONG–DU_AN của M0065, kể cả khi chưa tick; Core giữ guard chung, phần giải CRM qua resolver.
- Test âm cả nguồn mơ hồ/sai pháp nhân và quan hệ sai hoặc đổi sau khi ghim.

Dựng mới và nâng cấp là hai đường nghiệm thu riêng. Không mặc định nguồn DEMO ghi 23 migration là 23 bản đầu đúng lineage của chuỗi hiện hành.

Nạp chuyển đổi phải bảo toàn UUID hợp lệ, căn cứ, đơn vị, phiên bản và lịch sử duyệt; không tự suy thời điểm chụp hoặc tiền thiếu. Tắt module giữ dữ liệu. Không rollback bằng xóa schema/bảng.

### 3.13. Hạn giữ và dọn dữ liệu tạm — câu 2A

| Loại | Hạn đã duyệt |
|---|---|
| Tệp tạm, gồm kết quả OCR/Mask tạm, xử lý thành công | 24 giờ |
| Tệp tạm của lần xử lý lỗi | 7 ngày |
| Dấu chống trùng tạm/hộp nhận đã ACK | 30 ngày |
| Số đo vận hành chi tiết | 90 ngày |
| Số đo vận hành tổng hợp | 1 năm |
| CSDL/role test của lần test thành công | 7 ngày |
| CSDL/role test của lần test lỗi | 14 ngày |

Hết hạn không có nghĩa được dọn khi dữ liệu còn được xử lý, duyệt, backup, điều tra hoặc tham chiếu làm bằng chứng. Phải đối chiếu metadata và phụ thuộc.

Các ngoại lệ phải giữ rõ:

- Bản gốc, kết quả đã duyệt và audit nghiệp vụ không áp chính sách dọn tạm.
- Biên nhận nghiệp vụ module tại `loi_tai_lieu.bien_nhan_thao_tac` bất biến, giữ vĩnh viễn; không dọn dòng nào theo hạn 24 giờ hoặc 30 ngày.
- Biên nhận operation Core có chính sách riêng 24 giờ từ kết quả cuối, tiếp tục giữ nếu việc còn hoạt động hoặc kết quả chưa xác định; lưu tách khỏi biên nhận nghiệp vụ module.
- Hết hạn biên nhận Core không cho phép tạo trùng nghiệp vụ.
- Lease chỉ thu hồi sau đối chiếu worker/tiến trình và thế hệ; không mở lại việc mù quáng.
- Chưa cấu hình chính sách retention bắt buộc thì từ chối tiếp nhận tương ứng.

Số liệu khảo sát 303 CSDL test và 651 role test tồn đọng không phải danh sách được phép xóa. Chỉ xử lý khi Anh giao lát bảo trì riêng, có xem trước và đối soát.

Trong lát bảo trì đó phải xác minh đúng tài nguyên, chủ sở hữu, cụm, phiên và phụ thuộc; giữ mục chưa rõ; xử lý CSDL trước, role sau, tuần tự lô nhỏ và có nhật ký kết quả.

Giữ bảng cố định; mỗi kỳ, đợt, phụ lục, phiên bản hoặc lần chạy là thêm dòng. Không tạo bảng/cột/CSDL theo từng lần phát sinh.

### 3.14. [Core] Tài khoản người dùng do Core quản — câu 3A

Core tự quản tài khoản đăng nhập người dùng. Module không tự mở hệ tài khoản hoặc ma trận quyền song song.

- `loi.nguoi_dung`: danh tính người dùng, đăng nhập duy nhất.
- `loi.phap_nhan`: pháp nhân, đồng thời là phạm vi workspace.
- `loi.phan_quyen`: quan hệ người dùng–pháp nhân; mặt đọc `thanh_vien` không giữ bản sao.
- Các bảng MTQ: nguồn quyết định vai, hành động, hạn mức và phạm vi.
- Quyền module: phần quyền được Core cấp, không tự phát sinh từ manifest.

Tài khoản người dùng, login PostgreSQL và tài khoản Windows là ba lớp riêng. Có login CSDL không đồng nghĩa được tự chọn người dùng thao tác.

Danh sách nhân sự đăng nhập thật: **chờ Anh cung cấp**. Không đưa tài khoản mô phỏng, quyền thử hoặc dữ liệu DEMO thành dữ liệu thật.

### 3.15. [Core] Tệp và xuất riêng một pháp nhân

Module nhận ID tài liệu/tệp, không nhận đường dẫn để tự mở kho. Core quản metadata, hash, biến thể và quan hệ nguồn; cùng hash không đồng nghĩa cùng quyền.

Core chỉ công bố kết quả sau khi kiểm metadata và tệp đã ghi/kiểm hash; phải có trạng thái chờ/lỗi để phục hồi khi CSDL và filesystem chưa hoàn tất cùng lúc.

Xuất riêng một công ty chỉ do Admin khởi tạo, qua tác vụ Core và bản đồ sở hữu:

- Bao gồm dữ liệu module, tệp, audit, ánh xạ và phần danh mục cần thiết.
- Dùng mốc/snapshot nhất quán CSDL–tệp; đối chiếu số dòng, tiền theo đơn vị, hash và tham chiếu.
- Dùng `vai_xuat_phap_nhan` `NOLOGIN`, chỉ SELECT, không owner, DML hoặc `BYPASSRLS`.
- Có mã ủy nhiệm xuất riêng, cố định pháp nhân, FORCE RLS và audit; quyền role xuất được cấp hữu hạn cho tác vụ Core, không cấp module.
- Không mang dữ liệu pháp nhân khác, khóa hoặc bí mật phiên.
- Đối tượng nhiều pháp nhân chỉ xuất phần tách được; không tách toàn vẹn thì báo chặn.
- Thử phục hồi vào đích riêng trên DEMO.

Không dùng backup toàn database làm bản xuất một pháp nhân.

## 4. Khuyến nghị

Các khuyến nghị này không thay thế phần bắt buộc:

- Ưu tiên mở rộng cấu trúc và code đang đúng; đổi phần lệch chủ hoặc lệch chuẩn thay vì viết lại toàn bộ.
- Dùng lại hàng việc, bus, audit và cổng mã hóa hiện có; không tạo hệ tương đương chỉ để thống nhất tên.
- Chọn pool, concurrency, worker và chỉ mục theo số đo.
- Khi nâng cấp, ưu tiên mở rộng, đối chiếu rồi chuyển truy cập; kiểm cả việc đang chạy và dữ liệu lịch sử.
- Đặt phần mô tả trường/đơn vị/căn cứ gần contract của module để người dùng dữ liệu tra cứu được.

## 5. Ví dụ module giả định `mau_demo`

Ví dụ chỉ minh họa cách áp chuẩn, không phải một contract nghiệp vụ mới đã được duyệt.

### 5.1. Bản đồ sở hữu

| Thành phần | Áp dụng cho `mau_demo` |
|---|---|
| Schema riêng | `mod_mau_demo` |
| Schema công bố | `cong_bo_mau_demo` |
| Role chạy | `vai_chay_mod_mau_demo` |
| Role đổi cấu trúc | `vai_doi_cau_truc_mod_mau_demo` |
| Owner view công bố | `vai_doc_cong_bo_mau_demo` |
| Login module | `dang_nhap_mod_mau_demo` |
| Bảng riêng minh họa | `mod_mau_demo.ho_so` |

Một hồ sơ giả định có ID UUID, `phap_nhan_id`, số tiền `numeric` với đơn vị rõ, thời điểm `timestamptz` và `phien_ban_dong`.

Trên API, dữ liệu minh họa có thể biểu diễn:

```json
{
  "id": "10000000-0000-4000-8000-000000000001",
  "phap_nhan_id": "10000000-0000-4000-8000-000000000001",
  "so_tien": "100.00",
  "don_vi_tien": "VND",
  "row_version": "3"
}
```

Độ chính xác và quy tắc làm tròn phải được contract của hồ sơ xác định; ví dụ không ấn định kiểu `numeric(p,s)` chung cho mọi nghiệp vụ.

### 5.2. Luồng lưu hồ sơ

1. Core xác thực người dùng và cấp mã ủy nhiệm cho `mau_demo` trong đúng pháp nhân.
2. Module dùng `dang_nhap_mod_mau_demo`, mở transaction và đặt ngữ cảnh transaction-local.
3. CSDL xác minh mã, login, module, pháp nhân và quyền.
4. Module cập nhật bảng riêng bằng CAS; ghi dữ liệu chung hoặc biên nhận qua hàm Core V2 trên chính kết nối.
5. Nếu ghim căn cứ bên ngoài, module kiểm ID và mã băm qua contract công bố được cấp.
6. Mọi kiểm tra đạt mới commit; sai phiên bản trả 409, thiếu căn cứ trả `CHO` và không commit phần liên kết.

Module không tự phát mã phiên, không ghi bảng phiên, không giữ khóa mã hóa và không mở trực tiếp kho tệp.

## 6. Module được làm / không được làm

| Module được làm | Module không được làm |
|---|---|
| Đọc/ghi bảng riêng theo ACL, RLS và nghiệp vụ | Đọc/ghi bảng riêng của module khác |
| Gọi hàm Core V2 được cấp | DML trực tiếp bảng Core/danh mục chung |
| Đọc danh mục V3 đúng tập cột | Đổi nhãn bảng nghiệp vụ bên khác thành danh mục chung |
| Đọc contract công bố đúng phiên bản và quyền | Tự tạo view/hàm để che truy cập trái phép |
| FK về định danh Core theo bản đồ | FK chéo module hoặc buộc Core FK tới bảng module tùy chọn |
| Ghim ID và mã băm căn cứ | Tự đổi sang phiên bản mới nhất |
| Mang migration, công bố và resolver trong gói | Tự migrate khi runtime kết nối hoặc sửa đối tượng của khối khác |
| Dùng mã phiên/ủy nhiệm do Core cấp | Tự đặt GUC để nhận là người khác, tự cấp hoặc mở rộng ủy nhiệm |
| Yêu cầu Core xử lý dữ liệu mã hóa đúng quyền | Giữ khóa, truyền khóa SQL hoặc tự xây bộ che |
| Dùng tài liệu/tệp qua ID và dịch vụ Core | Tự mở kho bằng đường dẫn hoặc coi biết hash là có quyền |
| Khai báo contract và quyền cần dùng | Tự ghi sổ contract hoặc coi đăng ký là đã có quyền |
| Dùng dữ liệu giả trong test | Đưa dữ liệu thật hoặc tài khoản thật vào test |

## 7. Checklist trước khi nộp gói

Checklist là yêu cầu kiểm trước khi nộp, không phải tuyên bố các kiểm tra đã được chạy.

### 7.1. Cấu trúc và kiểu dữ liệu

- [ ] Có bản đồ chủ sở hữu và khai báo V1–V4 cụ thể.
- [ ] Tên kỹ thuật đúng quy ước; không tạo bảng trùng chức trách Core.
- [ ] UUID, tiền/đơn vị, thời điểm, ngày nghiệp vụ và CAS đúng chuẩn.
- [ ] Quan hệ cùng pháp nhân được bảo vệ; không có FK chéo module.
- [ ] JSON và mặt công bố có phiên bản; không làm mất căn cứ khi thiếu dữ liệu.

### 7.2. Quyền và danh tính

- [ ] Login runtime chỉ có role riêng và giao diện đã cấp; không owner/DDL/`BYPASSRLS`.
- [ ] Membership PG16 đúng `INHERIT TRUE, SET FALSE, ADMIN FALSE`.
- [ ] Owner, EXECUTE, `search_path`, PUBLIC/default privileges và policy của từng hàm/view đúng bản đồ.
- [ ] RLS/FORCE RLS và `USING`/`WITH CHECK` được kiểm bằng login runtime thực.
- [ ] Giả mã, sai login/module/pháp nhân, hết hạn, thu hồi và sai thế hệ việc đều bị chặn.
- [ ] Không rò ngữ cảnh qua pool; không cache xác minh ở nơi runtime ghi được.
- [ ] Mật khẩu/mã ủy nhiệm không vào env, dòng lệnh, manifest, response hoặc log.
- [ ] Tiến trình module/engine không đọc được thư mục bí mật.

### 7.3. Toàn vẹn và công bố

- [ ] Nếu module là chủ nghĩa vụ tiền: có resolver `SECURITY DEFINER` đăng ký ở `loi.dang_ky_ham_module`, khóa theo thứ tự chứng từ → nghĩa vụ, `vai_kiem_toan_ven_mod_<ma>` với policy chỉ lọc pháp nhân; đạt ca nghĩa vụ 80 + 30.
- [ ] Kiểm đủ hai giới hạn tiền dưới FORCE RLS, gồm hai ca 80 + 30 độc lập.
- [ ] Ca cạnh tranh 60 + 60, sửa/hủy và giảm sức chứa giữ đúng giới hạn.
- [ ] Resolver dùng registry, đúng owner/chữ ký; không nhận tên hàm tùy ý.
- [ ] Ghim ID/mã băm sai, contract thiếu hoặc căn cứ khác pháp nhân không được commit.
- [ ] View công bố chỉ đọc, có `security_barrier`, không `security_invoker`; runtime không có quyền bảng nguồn.
- [ ] Hàm kiểm không lộ dòng/tổng bị che.
- [ ] ACL và tập đối tượng của từng DEFINER/view/trigger/SQL động khớp khai báo; quyền vượt khai báo làm kiểm đỏ dù trace chưa chạy tới.
- [ ] Trace bổ sung không ghi giá trị dữ liệu hoặc bí mật.

### 7.4. Migration, contract và vòng đời

- [ ] Gói chứa migration, `contract/`, mặt công bố/resolver của mình.
- [ ] Sổ/checksum và trạng thái kích hoạt nhất quán; runtime không tự migrate.
- [ ] Dựng được khi module nguồn tùy chọn chưa cài; thao tác phụ thuộc trả `CHO`.
- [ ] Có kiểm dựng mới và nâng cấp phù hợp; bảo toàn guard và lineage lịch sử khi chuyển đổi.
- [ ] Contract đúng phiên bản đã đăng ký và quyền đã cấp; bản nghiệp vụ mới có bằng chứng Anh duyệt trước kích hoạt.
- [ ] Giữ bản contract còn binding; không chuyển ngầm hoặc ngừng sớm.
- [ ] Tắt module giữ dữ liệu; không rollback bằng xóa schema/bảng.

### 7.5. Mã hóa, retention và kiểm thử

- [ ] Nhóm A, bản sao, JSON path và lịch sử được rà; chỉ dùng cổng Core/Mask đúng chức trách.
- [ ] Không có khóa trong CSDL/GUC/tham số SQL; kiểm log, đổi khóa và phục hồi khi thuộc phạm vi.
- [ ] Hạn tạm đúng câu 2A; biên nhận nghiệp vụ module được giữ vĩnh viễn.
- [ ] Tài nguyên test được ghi nhận và xử lý theo thẩm quyền; không tự dọn tồn đọng.
- [ ] Test dùng dữ liệu giả, gồm test âm quyền, pháp nhân và truy cập chéo.
- [ ] Báo đạt/tổng và lỗi mới so với nền tại `docs\46-chuyen-doi-dieu-phoi\NEN-TEST.md`; không coi lỗi nền là lỗi mới.

## 8. Phụ lục — đặc tả chi tiết và điểm còn chờ

### 8.1. Tài liệu tra cứu

Các đường dẫn dưới đây tính từ gốc repo `accounting_assisstance`, để vẫn tra cứu được khi sao chép chuẩn sang `D:\Claude\QUY-TRINH-CHUNG\CHUAN-CORE\`.

| Tài liệu | Nội dung tra cứu |
|---|---|
| `docs\47-core\g1\DAC-TA-CSDL.md` | §1–3: sở hữu, tên và mô hình bảng; §4–5: role, phiên, RLS, mã hóa; §6–8: truy cập, migration, dọn dữ liệu |
| `docs\47-core\g1\ANH-XA-MIGRATION.md` | Ánh xạ 67 migration, chủ đích, hàm/trigger và điều kiện quyền khi đóng gói |
| `docs\47-core\g1\DAC-TA-API.md` | §2.4: biên nhận/CAS; §2.5: kiểu trao đổi; §4.2: ngữ cảnh liên tiến trình; phụ lục OpenAPI |
| `docs\47-core\g1\ANH-XA-ROUTE.md` | Chuyển tiếp route cũ và các điều kiện bảo vệ |
| `docs\47-core\PHIEU-DUYET-CSDL.md` | Kết quả duyệt cuối: 1A, 2A, 3A |
| `docs\47-core\PHIEU-DUYET-API.md` | Kết quả duyệt 1A, 2A và các quy ước API liên quan |
| `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` | CD-026…CD-036: phạm vi, cổng duyệt, contract, tài khoản tiến trình và chuẩn v1.0 |

Không chép lại toàn bộ OpenAPI hoặc JSON Schema trong chuẩn CSDL. Khi hiện thực, dùng định nghĩa chi tiết đúng phiên bản đã đăng ký và duyệt.

### 8.2. Điểm còn chờ, không tự chốt

Cách gọi cụ thể (hàm SDK cho biên nhận V2, File Store, mã ủy nhiệm, credential instance) nằm ở `CHUAN-CORE-SDK-v1.0.md` — **đã ban hành (CD-038, 30/10/2026)**.

| Nội dung | Trạng thái |
|---|---|
| Danh sách nhân sự đăng nhập thật | **Chờ Anh cung cấp** |
| Mã hóa nhóm B | **Chờ Anh** |
| Phiếu SDK bản 2 và điều kiện mở lại lập trình | **Chờ Anh duyệt và CD mở lại**, theo trạng thái chỉ đạo tại thời điểm ban hành |
| Contract nghiệp vụ mới hoặc phiên bản mới của contract đang dùng | **Chờ Anh duyệt trước kích hoạt** nếu chưa có bằng chứng duyệt |
| JSON path cụ thể của dữ liệu nhóm A | Chờ chốt danh mục trường trước G2 |
| Thuật toán/adapter cổng mã hóa dùng chung | Chờ lead chốt trong lát API/SDK |
| Ngoại lệ engine cần tài khoản Windows riêng | Ghi rõ ngoại lệ và **chờ Anh**, không tự nới quyền |
| Dọn CSDL/role test tồn đọng | **Chờ Anh giao lát bảo trì riêng**, có xem trước |

Ba lựa chọn CSDL về mã phiên bí mật, hạn giữ tạm và Core quản tài khoản **đã được duyệt A**; không còn là câu hỏi chờ chọn.

## 9. Đã xử lý review

Mã C/D theo `RV-CHUAN-OPUS.md`; mã CX dưới đây định danh theo thứ tự các phát hiện trong `RV-CHUAN.md`.

| Mã | Chỗ sửa |
|---|---|
| C2 | Đầu tệp: phân biệt ngày duyệt phiếu với văn bản chuẩn còn chờ Anh xem. |
| C4 | §8.2: ghi rõ chuẩn SDK chưa ban hành, chờ Anh duyệt phiếu bản 2. |
| C5 | §8.1: dùng đường dẫn từ gốc repo cho toàn bộ tài liệu tra cứu. |
| C6 | §3: giải thích [Core]/[Module]; gắn trách nhiệm tại §3.5.3–3.5.4, §3.6.1–3.6.2, §3.7.1, §3.8, §3.11 mục 2 và 4–6, §3.14–3.15; §7.3 thêm checklist chủ nghĩa vụ tiền. |
| C7 | §3.2: ghi rõ biên nhận module qua V2, cùng transaction/kết nối, bất biến và vĩnh viễn. |
| D1 | §5.1: đồng bộ UUID pháp nhân với ví dụ API, đuôi `…0001`. |
| CX-1 — tên cột migration | §3.12.1: giữ tên kỹ thuật đã có căn cứ; người áp dụng và nguồn lịch sử chỉ mô tả ý nghĩa. |
