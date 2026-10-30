# DAC-TA-SDK.md — SDK Core và mẫu gói module

**Lát G1c-1 · Ngày 30/10/2026 · Dự thảo chờ review và Anh duyệt**

**Đề xuất:** SDK bọc lại MTQ, hợp đồng engine, hàng việc, bus và khai báo module hiện có; bổ sung giao tiếp liên tiến trình, quản lý gói và các dịch vụ Core còn thiếu. Module giữ nghiệp vụ và dữ liệu riêng; Core quản lý danh tính, quyền, tài liệu, điều phối và vòng đời tiến trình.

Đây là đặc tả đích, chưa phải chức năng đã triển khai. Vòng 2 chỉ sửa hai tài liệu được giao và kiểm tĩnh JSON/schema; không lập trình, chạy ứng dụng, SQL, migration hoặc dịch vụ.

## 1. Căn cứ và quy ước

Áp dụng TL 54 §5.2, §7, §8, ưu tiên §14; TL 55 §3, §5, §10; CD-026–029; KS-A, KS-D, KS-E; hai bản nháp CSDL/API và review Opus.

Các quyết định chi phối:

- Mỗi module/engine chạy tiến trình riêng; Core cấp và giữ cổng, mặc định **tự kích hoạt + tự đóng** (`docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:329`).
- Engine không có login CSDL. Module nhận mật khẩu qua stdin/handle, chỉ dùng role runtime đúng khối; mã phiên bí mật và ủy nhiệm phải được kiểm chứng (`docs/47-core/g1/RV-G1A-OPUS.md:41`).
- G2 chỉ mở sau khi đủ ba phiếu CSDL/API/SDK được duyệt (`docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:342`).

**Quy ước dẫn chiếu:** `ha_tang/`, `k2/`, `giao_dien/`, `nguon/` và `workflow.py` tính từ `src/kho_tri_thuc/`; `tests/`, `docs/` tính từ gốc repo.

Tên mới dùng tiếng Việt không dấu, `snake_case`. Giữ tên giao thức và tên đang đúng như `module.json`, `socket.fromshare`, `row_version`, `Idempotency-Key`. Nhãn/thông báo cho người dùng dùng tiếng Việt có dấu.

Mọi chữ ký SDK mới dưới đây là **đề xuất**. Tên khối, login, xác minh phiên, biên nhận và trạng thái tuân `DAC-TA-CSDL.md` vòng 2 §3–6 và `DAC-TA-API.md` vòng 2 §2.4, §4–5; tên/chữ ký hàm SQL bổ sung phải đăng ký trước G2, không coi là mã đã có. Quy ước mã review ở bảng cuối: `O` = `RV-G1C-OPUS.md` (Chặn 1–3, CS1–CS9 theo mục Ưu tiên sửa; R1–R6 theo bảng review), `C` = `RV-G1C.md` (C1–C5 theo thứ tự bảng).

## 2. Hợp đồng chung của SDK Python

SDK Python phục vụ backend module và adapter phía Core. Tiến trình engine chỉ nhận phần giao tiếp công việc, tệp được ủy nhiệm và báo trạng thái; không nhận `du_lieu_rieng` hoặc kết nối PostgreSQL.

| Kiểu/quy ước | Nội dung |
|---|---|
| `ctx: NguCanh` | Bất biến, do SDK dựng sau xác thực Core; chứa định danh người, module, pháp nhân, operation và trace. Mã bí mật nằm trong đối tượng bảo vệ, không xuất qua `repr`, JSON hay log |
| `tx: GiaoDich` | Transaction của module, đúng login/role/schema và pháp nhân; ngữ cảnh transaction được xác minh từ mã phiên/ủy nhiệm |
| `Ma` | UUID, trừ khóa kiểm toán hiện hữu được giữ và trả dạng chuỗi |
| `Trang[T]` | `danh_sach`, `con_tiep`, `con_tro_tiep`; phân trang theo phiếu CSDL/API |
| `BienNhanViec` | Body theo `urn:ktt:contract:viec.v1#/$defs/da_nhan`: `viec_id`, `trang_thai`, `request_id`; địa chỉ theo dõi nằm ở header `Location`; chỉ trả sau commit |
| `GiuViec` | Handle bảo vệ do Core cấp khi nhận việc: `viec_id`, thế hệ lease và mã ủy nhiệm bí mật riêng đúng lease; không serialize/log, không chứa token HTTP được giữ lại |
| `ThamChieuTep` | Contract `tham_chieu_tep.v1`; không có đường dẫn vật lý hoặc URL tùy ý |
| Dữ liệu | Tiền/tỷ lệ dùng `Decimal` trong Python, chuỗi decimal trên JSON; ngày nghiệp vụ ISO; thời điểm có múi giờ |
| Lỗi | `LoiSDK(ma, thong_diep, request_id, thu_lai_duoc, http_status, chi_tiet=None)`; `chi_tiet` chỉ gồm `{truong, ma}` đã đăng ký, không chứa giá trị; không lộ SQL, khóa, mật khẩu hoặc nội dung nguồn |

Các hàm nhận `ctx` đều có thể lỗi 401/403; đối tượng ngoài phạm vi nhìn thấy trả 404. Schema sai trả 422; CAS/chống trùng/trạng thái xung đột trả 409; dữ liệu tạm hết hạn trả 410; phụ thuộc chưa sẵn sàng trả 503 — **theo phiếu CSDL/API** (`docs/47-core/g1/DAC-TA-API.md:83`).

`row_version` trên JSON là chuỗi số nguyên. Không đồng nhất nó với revision nghiệp vụ hoặc hash căn cứ (`docs/47-core/g1/DAC-TA-API.md:118`).

**Ranh giới giao dịch:** lời gọi HTTP tới Core có transaction riêng. Khi cần ghi dữ liệu module cùng bus, hàng việc hoặc hàm Core trong một transaction, SDK dùng cửa hàm CSDL được cấp trên chính `tx`; không mô phỏng tính nguyên tử bằng hai lời gọi HTTP. Các hàm nhận `tx` không tự commit.

**Ranh giới an ninh:** SDK kiểm khai báo để phát hiện sai sót; module có login vẫn có thể gọi thẳng driver. Quyền thực được cưỡng chế bằng role/ACL + RLS + hàm Core xác minh mã ủy nhiệm, và cách ly tiến trình tại §4.4. Với module X: `dang_nhap_mod_x` chỉ kế thừa `vai_chay_mod_x`, `INHERIT TRUE, SET FALSE, ADMIN FALSE`, không owner/BYPASSRLS; V1 riêng, V2 ghi chung qua hàm Core, V3 đọc danh mục, V4 đọc `cong_bo_<nguon>` (CSDL §4.1, §6.1). Không dựng DSN chứa mật khẩu: truyền `password=` riêng cho driver, không xuất tham số kết nối vào exception/log.

**Biên nhận operation module:** Core chỉ khóa request đang chạy. SDK trên chính transaction nghiệp vụ gọi hàm Core **V2** để tra/ghi `loi_tai_lieu.bien_nhan_thao_tac`, bất biến và **giữ vĩnh viễn**, cùng commit dữ liệu hoặc tạo việc; rollback thì không có biên nhận hoàn tất. Không có bản biên nhận hoàn tất thứ hai ở Core, không commit tạo việc riêng qua HTTP. UNIQUE `(phap_nhan_id, module, operation, client_key)`; lưu người tạo, fingerprint và kết quả/`viec_id`. Fingerprint = operation ổn định + body logic chuẩn hóa (gồm ID đích, pháp nhân, hash bytes tệp nếu có), không gồm route, method hoặc khóa. Alias cũ/v1 dùng chung operation/body/khóa. Kiểm quyền hành động trước tra và quyền đọc kết quả trước replay, kể cả khác người tạo; không được thấy trả 404. Cùng khóa khác fingerprint: 409 `KHOA_CHONG_TRUNG_KHAC_NOI_DUNG`; đang xử lý: 409 `YEU_CAU_DANG_XU_LY`, `Retry-After: 2`. Crash sau commit/trước response, restart, replay sau 24 giờ vẫn dùng biên nhận này; thời hạn 24 giờ chỉ thuộc biên nhận operation Core tách riêng (API §2.4). Tác động ngoài CSDL cần đối chiếu, không tuyên bố exactly-once.

## 3. Dịch vụ SDK Python

Trong bảng, lỗi ghi cạnh chữ ký bổ sung cho lỗi chung tại §2. Các tham số `loc`, `tham_so`, `du_lieu` phải khớp schema đã đăng ký.

| Dịch vụ · mục đích | Hàm chính, đầu vào → đầu ra; lỗi | Cửa gọi và phần tái dùng |
|---|---|---|
| **`danh_tinh`** · danh tính và quyền được xác thực | `hien_tai(ctx) -> DanhTinh`.<br>`kiem_quyen(ctx, hanh_dong: str, doi_tuong: dict) -> None`; thiếu quyền: 403.<br>`nhan_request(request: YeuCauTho, instance: PhienTienTrinh) -> NguCanh`; kiểm token theo §4.2, thiếu/sai/replay: 401, không gọi handler | Đọc qua `/toi`, `/phap-nhan`; xác thực request tại SDK và kiểm quyền tại Core/CSDL. Không có hàm xin ủy nhiệm việc từ `ctx` request. Giữ logic nạp danh tính/quyền tại `k2/quyen.py:88`, `:116`; quyết định đọc MTQ không thay cổng thực hiện hành động (`k2/sql_mtq_nen.py:1`) |
| **`tai_lieu`** · quản lý metadata hồ sơ | `liet_ke(ctx, loc: dict, con_tro: str\|None=None) -> Trang[TaiLieu]`; lọc sai: 422.<br>`lay(ctx, tai_lieu_id: Ma) -> TaiLieu`; 404.<br>`tao(ctx, tep_id: Ma, thong_tin: dict, khoa: str) -> TaiLieu`; tệp chưa hợp lệ: 422, trùng khác nội dung: 409 | GET/POST `/tai-lieu`, GET `/tai-lieu/{id}` **theo phiếu CSDL/API**. Bọc nền tiếp nhận/hash/phiếu nhận hiện hữu, không tạo kho tiếp nhận thứ hai (`giao_dien/intake.py:75`; khảo sát `docs/47-core/g0/KS-A.md:20`) |
| **`tep`** · nhận và đọc bytes qua kho Core | `tai_len(ctx, luong: BinaryIO, ten: str, mime: str, khoa: str) -> ThamChieuTep`; 413/415/422/409.<br>`tham_chieu(ctx, tep_id: Ma) -> ThamChieuTep`; 404/410.<br>`mo_doc(ctx, tep_id: Ma) -> BinaryIO`; 404/410; SDK đóng luồng khi thoát phạm vi sử dụng | POST `/tep`, GET `/tep/{id}`, GET `/tep/{id}/noi-dung` **theo phiếu CSDL/API**. Giữ ghi bất biến/chống ghi đè tại `ha_tang/store.py:26`. Kiểm quyền trước mở luồng; cùng hash không đồng nghĩa cùng quyền |
| **`ket_qua`** · kết quả có phiên bản và nguồn | `lay(ctx, ket_qua_id: Ma) -> KetQua`; 404/410.<br>`ghi(tx, tep_id: Ma, contract: str, khoa: str, giu_viec: GiuViec\|None=None) -> Ma`; schema/tham chiếu sai: 422, xung đột/mất lease: 409.<br>`tao_revision(tx, ket_qua_id: Ma, revision_truoc: str, tep_id: Ma, ly_do: str, khoa: str) -> KetQua`; 409/422 | GET `/ket-qua/{id}`; ghi/revision qua hàm Core được cấp, chưa có route ghi tương ứng. Core tự gắn module/engine/function/version, việc/bước/lần thử từ instance và lease đã xác minh; caller chỉ gửi tham chiếu nguồn để Core kiểm quyền/hash/revision, không tự khai provenance OCR. Giữ bằng chứng hash/engine/version tại `ha_tang/engine.py:77`, `:165`; mẫu lưu kết quả + kết thúc việc cùng CAS tại `ha_tang/chay_engine.py:159`. Không tự phê duyệt nghiệp vụ |
| **`du_lieu_rieng`** · repository đúng khối module | `giao_dich(ctx) -> ContextManager[GiaoDich]`; 403/503.<br>`doc(tx, ma_truy_van: str, tham_so: dict) -> Trang[dict]`; SDK từ chối truy vấn chưa đăng ký: 403, tham số sai: 422; đây không phải ranh giới an ninh.<br>`ghi(tx, ma_lenh: str, tham_so: dict, row_version: str\|None, khoa: str) -> BienNhan`; 409/422, bao gồm biên nhận V2 tại §2 | Repository module chỉ chạm V1; V2/V3/V4 đúng quyền cưỡng chế tại CSDL, kể cả khi bỏ qua SDK. Tái dùng `KhaiBaoVungDuLieu` tại `ha_tang/khai_bao_module.py:144` và bản khai `k2/vung_du_lieu.py:182`. Bộ kiểm hiện mới kiểm khai báo/điểm được truyền vào (`ha_tang/khai_bao_module.py:225`) |
| **`cong_bo`** · đọc contract module khác công bố | `liet_ke(ctx) -> list[KhaiBaoCongBo]`.<br>`doc(tx, contract: str, tham_so: dict) -> KetQuaCongBo`; sai quyền: 403, tham số: 422.<br>`kiem_phien_ban(tx, contract: str, doi_tuong_id: Ma, phien_ban: str, ma_bam: str) -> CanCu`; nguồn đã đổi: 409 | Registry và mặt đọc `cong_bo_<nguon>` **theo phiếu CSDL/API**. Giữ phép chiếu hóa đơn hiện tại `master.hoa_don_cong_bo`, gồm kiểm quyền trước tra cứu, phiên bản/hash và `CHO` (`k2/sql_cong_bo_hoa_don.py:15`, `:20`, `:38`). `CHO` là thiếu nguồn/công bố, không thay lỗi quyền. Đọc dữ liệu bền vững không đòi tiến trình nguồn đang chạy |
| **`su_kien`** · outbox/inbox có chống trùng | `phat(tx, loai: str, phien_ban: int, tham_chieu: dict, khoa: str) -> Ma`; 409/422.<br>`nhan(tx, loai: str\|None=None, gioi_han: int=100) -> list[SuKien]`; 422.<br>`xac_nhan(tx, su_kien_id: Ma) -> bool`; chưa nhận: 409; ACK lặp trả `False` | Bọc nguyên `bus.phat/nhan/ack`; tên/schema đích **theo phiếu CSDL/API**. Wrapper tại `ha_tang/bus_su_kien.py:30`, `:49`, `:64`. Payload chỉ tham chiếu UUID, bên phát/nhận suy từ module đã xác thực. Ghi nghiệp vụ và ACK cùng transaction; giao ít nhất một lần |
| **`engine`** · gửi capability qua Core/adapter | `liet_ke(ctx) -> list[KhaNang]`.<br>`kha_nang(ctx, capability: str) -> KhaNang`; không có/không được thấy: 404.<br>`gui_viec(ctx, capability: str, dau_vao: dict, khoa: str) -> BienNhanViec`; 409/422/429/503 | GET `/engine`, GET `/engine/{ma}`, POST `/engine/{ma}/viec` **theo phiếu CSDL/API**. Core ánh xạ capability sang engine/adapter đã ghim. Giữ `Engine.chay` và danh bạ tra đúng version, không tự chọn mới nhất (`ha_tang/engine.py:165`; `ha_tang/danh_ba_engine.py:33`). Giữ cổng OCR/AI được tiêm (`ha_tang/engine_cong.py:127`, `:154`) |
| **`quy_trinh`** · chạy phiên bản quy trình cố định | `liet_ke(ctx) -> list[QuyTrinh]`.<br>`bat_dau(ctx, ma: str, phien_ban: str, dau_vao: dict, khoa: str) -> BienNhanViec`; 409/422/503.<br>`tiep_tuc(ctx, lan_chay_id: Ma, buoc: str, revision_truoc: str, du_lieu: dict, khoa: str) -> BienNhanViec`; 409/422 | GET `/quy-trinh`, POST `/quy-trinh/{id}/lan-chay`; cửa tiếp tục **theo phiếu CSDL/API**, chưa có route tương ứng trong nháp. Dùng hàng việc XS-2 làm nền; giữ nghiệp vụ hiện hữu làm handler bước. Chưa có runner chung theo khảo sát `docs/47-core/g0/KS-A.md:23`; không coi bảng dispatch `workflow.py:15` là runner hoàn chỉnh |
| **`viec`** · theo dõi, hủy và báo tiến độ | `lay(ctx, viec_id: Ma) -> Viec`; 404.<br>`ket_qua(ctx, viec_id: Ma) -> list[KetQua]`; 404, vẫn kiểm từng kết quả.<br>`huy(ctx, viec_id: Ma, khoa: str) -> BienNhanViec`; 409.<br>`bao_tien_do(tx, giu_viec: GiuViec, muc: int) -> bool`; mức sai: 422, mất lease: từ chối cập nhật | GET `/viec/{id}`, GET `/viec/{id}/ket-qua`, POST `/viec/{id}/huy` **theo phiếu CSDL/API**. Giữ wrapper tạo/nhận/gia hạn/kết thúc tại `ha_tang/hang_viec.py:21`, `:31`, `:43`, `:55`; giữ lease/token và `SKIP LOCKED` (`k2/sql_hang_viec.py:161`). Engine báo qua Core, không gọi các hàm SQL này |
| **`kiem_toan`** · audit và số đo vận hành | `ghi(tx, hanh_dong: str, doi_tuong: dict, ket_luan: dict) -> str`; metadata không cho phép: 422.<br>`tra_cuu(ctx, loc: dict, con_tro: str\|None=None) -> Trang[BanGhiKiemToan]`; 403/422.<br>`ghi_so_do(ctx_tien_trinh, so_do: dict) -> BienNhan`; sai instance: 403, dữ liệu sai: 422 | Ghi/tra audit và nhận số đo qua cửa Core nội bộ **theo phiếu CSDL/API**; đọc quản trị số đo qua `/quan-tri/so-do`. Giữ audit hiện hữu (`ha_tang/pg_migrations.py:413`; đối chiếu `docs/47-core/g0/KS-A.md:25`). Core tự gắn actor/trace/thời điểm; báo cáo module không được giả thành kết luận đã xác minh của Core |
| **`ma_hoa`** · cổng Core cho cột nhóm A, dịch vụ thứ 12 | `ma_hoa(ctx, cot: CotDaDangKy, gia_tri: str) -> BanMa`; 403/422/503.<br>`tra_hmac(ctx, cot: CotDaDangKy, gia_tri: str) -> DauTraCuu`; 403/422/503.<br>`hien_thi_rut_gon(ctx, cot: CotDaDangKy, ban_ma: BanMa) -> str`; tối đa bốn số cuối, 403/422.<br>`giai_ma(ctx, cot: CotDaDangKy, doi_tuong_id: Ma, ly_do: str) -> str`; quyền xem đủ + audit trước trả, 403/404/503 | Kênh SDK nội bộ đã xác thực tới Core, không phải SQL nhận khóa hoặc route công khai mới. Core kiểm cột/module/pháp nhân/hành động; khóa chỉ trong RAM Core, bọc DPAPI theo CSDL §5.1 (`docs/47-core/g1/DAC-TA-CSDL.md:345`). Thiết kế adapter chung: AEAD AES-256-GCM, nonce riêng mỗi lần, AAD ràng buộc pháp nhân/module/bảng/cột/ID dòng; bản mã có phiên bản khóa. HMAC-SHA-256 dùng khóa độc lập + miền/chuẩn hóa đã đăng ký; không hash trần. Thuật toán/adapter cần lead chốt trước G2 theo CSDL §5.1; không chép bộ mã hóa/Mask vào module |

**Quy tắc thực thi giữ lại:**

- Bộ worker Core dùng lại `nhan`, `gia_han`, `trang_thai_lease`, `ket_thuc`, `thu_lai`; mất lease thì rollback phần lưu kết quả (`ha_tang/chay_engine.py:102`, `:159`).
- Kết quả tác động ngoài chưa rõ phải giữ `CHUA_RO`, không tự retry. Adapter giữ trạng thái nguồn; ánh xạ ra API **theo phiếu CSDL/API**, không làm mất dấu chưa rõ (`k2/sql_hang_viec.py:12`, `:137`).
- `XONG/CHO/LOI` của engine, trạng thái việc và trạng thái duyệt là ba lớp khác nhau (`ha_tang/engine.py:24`; `docs/47-core/g1/DAC-TA-CSDL.md:219`).
- AI đi qua cổng AI phần mềm; luôn có đường Local, Cloud qua Mask v2. Adapter không tạo cổng hoặc bộ che thứ hai (`ha_tang/engine_cong.py:1`).
- Core cấp `GiuViec` khi nhận lease sau kiểm quyền, gắn mã ủy nhiệm với `viec_id` + thế hệ lease; gia hạn qua kênh instance với lease còn hiệu lực, không kéo dài quyền vượt hạn/thu hồi. Mất lease/restart/đổi quyền: thu hồi mã cũ; chỉ cấp mã mới sau đối chiếu tác động và nhận lease mới (API §2.6, §4.2). Các hàm worker `nhan_viec(instance) -> GiuViec|None`, `gia_han(giu_viec) -> GiuViec`, `ket_thuc(giu_viec, ket_qua) -> bool` dùng kênh Core; engine không gọi SQL. Đây là adapter đích quanh hàng việc đã dẫn ở bảng.

## 4. Khung tiến trình module/engine

### 4.1. Khởi động và nhận listener

1. Core khóa phối hợp theo chủ chạy/máy chủ, lấy cổng cố định và thế hệ sở hữu từ sổ cổng **theo phiếu CSDL/API**. Core bind loopback với `SO_EXCLUSIVEADDRUSE` trước bind, không dùng `SO_REUSEADDR`; các request đang chờ dùng chung một lần khởi động.
2. Core khởi động headless từ hồ sơ đã duyệt. Tiến trình con nhận cấu hình qua stdin hoặc handle riêng có giới hạn quyền; không nhận mật khẩu/token qua dòng lệnh, biến môi trường hoặc tệp cấu hình gói.
3. Với Python hỗ trợ chuyển giao: sau khi có PID thật, Core gửi dữ liệu `socket.share(pid)`; SDK nhận bằng `socket.fromshare`. Core giữ bản handle để thu hồi, nhưng chỉ một bên có quyền accept theo trạng thái bàn giao.
4. Với engine cũ: Core đóng listener rồi truyền đúng cổng bằng tham số. Nếu bind thất bại, báo `CONG_BI_CHIEM`; không dò cổng khác hoặc dừng ứng dụng lạ. Đây là phương án chuyển tiếp có khoảng hở.
5. SDK gửi thông điệp sẵn sàng gồm: mã chủ, instance, PID và định danh lần tạo tiến trình, nonce khởi động, phiên bản, capability/contract thực có, cổng và kết quả kiểm readiness. Module phải thử đúng login runtime, xác minh ngữ cảnh/role, và `phien_ban_du_lieu` + checksum gói khớp `loi.lich_su_doi_cau_truc`; lệch thì không báo `ready`, không tự migrate. Engine không thử login CSDL, phải thử model/capability thực. Core xác minh xong mới chuyển request.

Thông điệp bootstrap/readiness là contract nội bộ mới, **theo phiếu CSDL/API**. Không đánh đồng listener hoạt động, `/healthz` thành công và capability thực sự sẵn sàng.

Tái dùng bắt tay/readiness và quản lý Windows Job của host #6; thay phần tự chọn cổng (`nguon/trich6_host.py:240`, `:280`, `:607`; đối chiếu `docs/47-core/g0/KS-A.md:75`). Việc chuyển giao/thu hồi socket không khoảng hở cần thử ở G2, chưa được xác nhận vận hành trong lát này.

### 4.2. Phiên, ủy nhiệm và CSDL

Phân biệt ba loại:

| Loại | Phạm vi |
|---|---|
| Danh tính tiến trình | Core cấp khi bootstrap; xác thực module/engine và instance |
| Ngữ cảnh request | Token ký TTL tối đa 30 giây theo API §4.2; module/instance nhận, operation, pháp nhân, mã ủy nhiệm bí mật (không SID), `request_id`, khóa chống trùng nếu ghi, nonce và hash method/path/body |
| Mã phiên/ủy nhiệm CSDL | Bí mật do Core cấp, CSDL kiểm phiên còn hạn, đúng login/module/pháp nhân và việc được giao; không dùng UUID người dùng hoặc GUC tự khai làm bằng chứng |

Module nhận credential runtime riêng qua stdin/handle; không nhận credential migration. SDK đặt ngữ cảnh theo transaction và làm sạch khi trả kết nối về pool.

`danh_tinh.nhan_request` chạy trước mọi handler trên listener, kể cả loopback: kiểm chữ ký bằng khóa kiểm chứng bootstrap (khóa ký chỉ Core giữ), issuer/audience đúng module + instance hiện hành, thời điểm phát hành/hết hạn và TTL ≤ 30 giây, operation, hash method/path/body bytes thực nhận và khóa chống trùng. Nonce được tiêu thụ nguyên tử một lần trong instance, giữ đến hết hạn; hai request đồng thời cùng nonce chỉ một request được vào. Nonce vận chuyển khác khóa chống trùng nghiệp vụ: retry Core ký token/nonce mới nhưng giữ khóa/fingerprint. Không token/sai chữ ký/sai instance/hết hạn/nonce lặp/hash lệch đều 401 trước handler. Core lọc header nội bộ từ client; SDK không nhận `ctx` do module/frontend tự dựng. CSDL vẫn xác minh mã ủy nhiệm theo `session_user`, module, pháp nhân, hành động và lease (API §4.2; CSDL §5).

Engine không nhận login CSDL. Engine chỉ nhận bytes/tham chiếu có quyền theo việc; yêu cầu đọc tệp hoặc bàn giao kết quả đều qua Core. Token HTTP ngắn hạn không được lưu làm ủy nhiệm cho việc nền dài hạn (`docs/47-core/g1/DAC-TA-API.md:221`; `docs/47-core/g1/RV-G1A-OPUS.md:43`).

### 4.3. Thu hồi và đo khởi động

Khi Core yêu cầu thu hồi, SDK ngừng nhận việc mới, tiếp tục heartbeat cho việc đang giữ, chờ kết thúc hoặc điểm dừng an toàn, bàn giao kết quả rồi xác nhận dừng. Với listener chia sẻ, tiến trình con đóng handle của mình; không gọi `shutdown` làm hỏng listener Core giữ.

Không đóng engine khi còn kết quả chưa bàn giao, luồng tải hoặc ánh xạ Mask còn cần dùng. Nếu không drain được trong hạn, báo trạng thái/lý do; không tự coi việc đã hủy. Core chỉ xử lý tiến trình đã xác minh thuộc mình.

Core ghi từng lần khởi động: giờ yêu cầu, bắt đầu, sẵn sàng/thất bại, thời gian xử lý, thời gian rảnh trước đóng, số lần/ngày, RAM và CPU kèm cửa sổ đo. Thiếu số đo ghi “chưa đo”. Hằng tuần chỉ đề xuất thay chế độ; **Admin bấm áp dụng**, có CAS và audit (`docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:332`).

Core gắn toàn bộ cây con vào Windows Job với `KILL_ON_JOB_CLOSE`; RAM/CPU và giới hạn lấy từ Job accounting do Core đo, báo cáo tự khai chỉ bổ trợ. Cờ này xử lý Core crash/đóng Job, không thay drain thông thường. Trạng thái tiến trình đúng API §5: `stopped/starting/ready/busy/dang_dung/failed`, độc lập công tắc và trạng thái việc. `dang_dung` không nhận request mới: 503 `TIEN_TRINH_DANG_DUNG`, `Retry-After: 2`; quá 300 giây vẫn drain, giữ cổng cho Admin xử lý, không tự hủy việc.

Core còn đánh thức module **đang được phép hoạt động** khi có việc `queued` hoặc sự kiện trong hộp nhận chờ, không chỉ khi có HTTP; cùng khóa phối hợp để không tạo instance thứ hai. Module đang `TAT`/chưa kích hoạt không bị tự bật; giữ hàng chờ. “Rảnh” = không request/luồng tải/kết quả hoặc lượt Mask đang dùng, không lease, hộp nhận rỗng và không việc chờ được phép nhận; quyết định đóng cùng khóa dispatch. Theo CD-033 câu 3 đã chốt A, mặc định Core khởi động ngay; Admin đổi sau số đo theo CD-028 mục 3b.

### 4.4. Danh tính hệ điều hành

**CD-033 câu 2 — đã chốt A, áp ngay từ giai đoạn thử trên máy Anh:** Core chạy dưới tài khoản Windows riêng, ví dụ `ktt_core`; module/engine chạy dưới tài khoản máy có quyền hạn chế, ví dụ `ktt_module`, khác tài khoản Core. Không chạy chung tài khoản rồi chỉ hạn chế token của Core. Bộ khởi chạy dùng danh tính hạn chế đã cấp, chỉ kế thừa allowlist handle bootstrap/listener, không handle kho bí mật/process Core; bỏ quyền debug/impersonate và khả năng thoát Job. ACL `D:\DU-LIEU-KE-TOAN\bi-mat\` chỉ cho tài khoản dịch vụ Core đọc ở lớp runtime; module/engine không đọc được credential hoặc khóa DPAPI. Mỗi module chỉ nhận credential của chính mình, engine không nhận login CSDL.

Core process/handle phải chặn con mở/đọc/ghi bộ nhớ, duplicate handle/token hoặc sửa ACL để lấy lại quyền Core; không truyền handle process đặc quyền. Cùng SID người dùng hoặc chỉ đặt `headless` không chứng minh cách ly. G2 kiểm tài khoản thực của tiến trình, ACL thư mục/process, DPAPI, socket và Job cùng CD-028 mục 6 bằng bí mật DEMO; mọi đường đọc bí mật/nhớ Core phải thất bại. Nếu chưa chứng minh được cách ly thì **không kích hoạt**. Đây là yêu cầu thiết kế cần chứng minh tại G2, chưa phải khả năng Windows host đã được xác nhận.

Phải có script tạo tài khoản và cấp quyền thư mục, chạy lại được trên máy Anh và khi chuyển máy chủ; kiểm trạng thái hiện có, không cấp rộng thêm khi chạy lại. Anh chỉ bấm đồng ý quyền quản trị; runtime không giữ quyền quản trị. Engine cũ cần tài khoản riêng, ví dụ ABBYY Hot Folder, phải ghi rõ tài khoản/quyền/lý do ngoại lệ và hỏi Anh duyệt trước; không tự nới quyền. Bộ kiểm chạy bằng chính tiến trình module/engine phải chứng minh không liệt kê/đọc được `D:\DU-LIEU-KE-TOAN\bi-mat\` (môi trường thử dùng bí mật DEMO).

**Bổ sung lead sau Opus vòng 2:**
- Khóa và mật khẩu trong `bi-mat` bọc DPAPI **phạm vi người dùng** của tài khoản dịch vụ Core, không dùng phạm vi máy (`CRYPTPROTECT_LOCAL_MACHINE`).
- G2 phải kiểm được rằng token con không giải được các bí mật này.

## 5. SDK giao diện JavaScript

| Thành phần/chữ ký đề xuất | Hành vi bắt buộc |
|---|---|
| `api.goi({phuong_thuc, duong_dan, phap_nhan_id, module, du_lieu, khoa, signal})` | Chỉ gọi cùng nguồn `/api/v1/`; tự gắn CSRF, ngữ cảnh pháp nhân/module và trace theo phiếu CSDL/API. Không cho caller tùy ý đổi sang host engine |
| `viec.theo_doi(viec_id, {khi_doi, signal})` | Poll theo `Retry-After`; ngừng khi kết thúc, rời màn hoặc đổi ngữ cảnh. `waiting_input` hiển thị yêu cầu bổ sung; không báo thành công giả |
| `viec.huy(viec_id, khoa)` | Gửi đề nghị hủy; tiếp tục theo dõi tới trạng thái xác nhận |
| `khung.dung(root, khai_bao_da_loc_quyen)` | Dựng lưới module, lưới phần, thẻ tổng quan và thanh icon trái theo TL 49 |
| `bang.dung(root, {cot, dong, row_version, khi_sua})` | Bảng nhập liệu chung; giữ nháp khi vẽ lại; định dạng và kiểm theo schema trường |
| `thong_bao.loi(root, loi)` | Thông báo tiếng Việt, hành động phục hồi rõ; `request_id` nằm trong phần chi tiết để sao chép |

**Chống trùng và 409.** Mỗi ý định ghi giữ nguyên khóa, body và ngữ cảnh cho đến khi biết kết quả. Mất mạng/timeout không tạo khóa mới. CAS cũ: giữ nháp, tải bản mới để người dùng đối chiếu; khóa khác nội dung: dừng gửi lại; request đang xử lý: chờ theo `Retry-After`. Khi đổi người/pháp nhân/màn, hủy theo dõi và bỏ phản hồi cũ; không tự gửi lại bằng ngữ cảnh mới.

Frontend giữ khóa không thay biên nhận bền vững §2. Lỗi trường lấy `chi_tiet[].truong` để gắn đúng ô schema; chỉ hiện mã đã đăng ký, không phản chiếu giá trị nguồn. Mã lỗi module chưa đăng ký hoặc payload không hợp lệ bị Core đổi thành 502 `PHAN_HOI_SAI_CONTRACT` theo API §2.3.

**Khung icon.** Hai cấp lưới; trang module có 2–4 thẻ bấm mở đúng danh sách đã lọc. Badge chỉ đếm việc chờ của người đăng nhập; số 0 ẩn, quá hạn có màu kèm chữ. Server lọc quyền và trả số; tổng chưa đầy đủ không trình bày như tổng chính xác. Giữ breadcrumb, tìm nhanh, thanh mục hay dùng và thanh icon trái theo TL 49 (`../49-trang-chu-luoi-icon.md:11`, `:19`, `:41`).

**Bảng nhập liệu.**

- Tiền: chuỗi decimal cùng đơn vị; không đi qua `Number`/float. Trường `_minor` cũ chuyển đổi theo số chữ số đơn vị đã khai báo.
- Tỷ lệ: cột phải khai đơn vị. Đề xuất nhập `12,5%` → `"12.5"` đơn vị `phan_tram`; không âm thầm đổi thành tỷ phần.
- Ngày: nhập/hiện `dd/mm/yyyy`, kiểm ngày lịch thực rồi gửi `YYYY-MM-DD`.
- Ô sai có lỗi tại ô và nhãn truy cập; giữ nháp, không làm tròn hoặc điền 0 khi thiếu căn cứ.

**Tái dùng có giới hạn:**

| Mã hiện có | Giữ và bổ sung |
|---|---|
| `giao_dien/assets/crm_g.js:28`, `:76`, `:107` | Giữ thế hệ ngữ cảnh, nháp ghi xuyên và giữ khóa khi kết quả chưa rõ; chuyển khóa sang header chuẩn |
| `giao_dien/assets/ma_tran_tham_quyen.js:26`, `:36`, `:54` | Giữ xử lý tiền bằng chuỗi, DOM `textContent`, nhãn và trạng thái lỗi; mở rộng decimal theo schema |
| `giao_dien/assets/that.js:15`, `:21`, `:33` | Giữ tiện ích hiển thị/nguyên tắc polling; thay transport, trạng thái và chu kỳ cũ. Hàm ngày hiện chỉ kiểm mẫu nên cần thêm kiểm lịch |
| `giao_dien/assets/that.js:47`, `:264` | Tận dụng icon và thông báo có hướng xử lý; chuẩn hóa lỗi và rà giấy phép asset |
| `giao_dien/khung_khai_bao.py:113`, `:132`; `ha_tang/khai_bao_module.py:283` | Giữ metadata phần/thẻ, đếm từ danh sách đã kiểm quyền và dấu hiệu tổng không đầy đủ |

Chưa coi các asset trên là SDK v1 đã có; wrapper hiện vẫn dùng route/token/lỗi cũ.

## 6. Mẫu `module.json` và engine manifest

**CD-032 — lớp dữ liệu giao tiếp bắt buộc:** mọi gói module có thư mục `contract/` gồm dữ liệu công bố, sự kiện phát/nhận và đầu vào nguồn. `module.json.contract` liệt kê đủ bốn nhóm; nhóm không dùng ghi mảng rỗng, không bỏ thư mục hoặc bỏ nhóm. Mỗi contract có mục đích, module sở hữu, module được đọc, danh sách trường (tên tiếng Việt không dấu, nghĩa, bắt buộc/tùy chọn, đơn vị, nguồn), ví dụ JSON DEMO đầy đủ, JSON Schema và phiên bản. Contract nhận từ nguồn khác phải ghim bản đã đăng ký, không tự nhận sở hữu hoặc định nghĩa lại. Chi tiết kiểm tại `CONTRACT-DU-LIEU.md` §15; thiếu hoặc không hợp lệ thì **không cài**. M4, CRM, M2 ở G4 phải làm `contract/` trước màn hình.

### 6.1. Mẫu module nhỏ

Ví dụ minh họa cấu trúc gói **Tra cứu tài liệu DEMO**; module thử Core G2 đã chốt là **CRM (DEMO)** theo CD-033, **M4 là module mẫu G4 đã chốt** (TL 55 §6, CD-027). Các đường dẫn là thành phần gói dự kiến, chưa được tạo. `thao_tac` tương ứng operation. Schema chính thức draft 2020-12: `urn:ktt:manifest:module.v1` và `urn:ktt:manifest:engine.v1`, phiên bản 1.0.0, tại `CONTRACT-DU-LIEU.md` §15; Core đăng ký offline, kiểm cả schema lẫn ràng buộc ngữ nghĩa §15.3 trước cài.

```json
{
  "phien_ban_manifest": 1,
  "loai": "module",
  "ma": "mau_tai_lieu_demo",
  "ten": "Tra cứu tài liệu DEMO",
  "phien_ban": "0.1.0-demo.1",
  "tuong_thich": {
    "core": ">=1.0.0 <2.0.0",
    "api": "v1",
    "sdk_python": ">=1.0.0 <2.0.0",
    "sdk_js": ">=1.0.0 <2.0.0",
    "contract": ["tham_chieu_tep.v1", "van_ban_tai_lieu.v1", "viec.v1"]
  },
  "goi": {
    "tep_kiem_ke": "goi/kiem_ke.json",
    "thuat_toan_ma_bam": "sha256",
    "phu_thuoc_module": []
  },
  "contract": {
    "cong_bo": [
      {"ma": "ghi_chu", "phien_ban": "1", "module_so_huu": "mau_tai_lieu_demo",
       "tep_mo_ta": "contract/cong_bo_ghi_chu.v1.json",
       "schema": "contract/cong_bo_ghi_chu.v1.schema.json",
       "vi_du": "contract/cong_bo_ghi_chu.v1.vi_du.json"}
    ],
    "su_kien_phat": [
      {"ma": "mau_tai_lieu_demo.ghi_chu_doi", "phien_ban": "1", "module_so_huu": "mau_tai_lieu_demo",
       "tep_mo_ta": "contract/ghi_chu_doi.v1.json",
       "schema": "contract/ghi_chu_doi.v1.schema.json", "vi_du": "contract/ghi_chu_doi.v1.vi_du.json"}
    ],
    "su_kien_nhan": [
      {"ma": "tai_lieu.cap_nhat", "phien_ban": "1", "module_so_huu": "loi",
       "tep_mo_ta": "contract/tai_lieu_cap_nhat.v1.json",
       "schema": "contract/tai_lieu_cap_nhat.v1.schema.json", "vi_du": "contract/tai_lieu_cap_nhat.v1.vi_du.json"}
    ],
    "dau_vao_nguon": [
      {"ma": "tham_chieu_tep.v1", "phien_ban": "1.0.0", "module_so_huu": "loi",
       "tep_mo_ta": "contract/tham_chieu_tep.v1.json",
       "schema": "contract/tham_chieu_tep.v1.schema.json", "vi_du": "contract/tham_chieu_tep.v1.vi_du.json"},
      {"ma": "van_ban_tai_lieu.v1", "phien_ban": "1.0.0", "module_so_huu": "loi",
       "tep_mo_ta": "contract/van_ban_tai_lieu.v1.json",
       "schema": "contract/van_ban_tai_lieu.v1.schema.json", "vi_du": "contract/van_ban_tai_lieu.v1.vi_du.json"}
    ]
  },
  "backend": {"diem_vao": "mau_tai_lieu_demo.chay"},
  "giao_dien": {
    "diem_vao": "giao_dien/chinh.js",
    "tai_nguyen": ["giao_dien/chinh.js", "giao_dien/chinh.css"],
    "icon": "file",
    "nhom_mau": "bao_cao",
    "thu_tu": 100,
    "trang_dau": "#mau_tai_lieu_demo/tai_lieu",
    "thao_tac_khung": "tong_quan",
    "phan": [
      {"ma": "tai_lieu", "ten": "Tài liệu", "icon": "folder", "thu_tu": 1,
       "duong_dan": "#mau_tai_lieu_demo/tai_lieu", "quyen_xem": "mau_tai_lieu_demo.tai_lieu.doc"},
      {"ma": "ket_qua", "ten": "Kết quả", "icon": "file", "thu_tu": 2,
       "duong_dan": "#mau_tai_lieu_demo/ket_qua", "quyen_xem": "mau_tai_lieu_demo.ket_qua.doc",
       "dem": "cho_kiem"}
    ],
    "the": [
      {"ma": "cho_kiem", "nhan": "Kết quả chờ kiểm", "dem": "cho_kiem",
       "loc": {"phan": "ket_qua", "tham_so": {"trang_thai_duyet": "cho_kiem"}}},
      {"ma": "co_ghi_chu", "nhan": "Tài liệu có ghi chú", "dem": "co_ghi_chu",
       "loc": {"phan": "tai_lieu", "tham_so": {"co_ghi_chu": true}}}
    ]
  },
  "thao_tac": [
    {"ma": "danh_sach", "phuong_thuc": "GET", "duong_dan": "/tai-lieu",
     "dau_vao": "schema/loc.v1.json", "dau_ra": "schema/danh_sach.v1.json",
     "quyen": "mau_tai_lieu_demo.tai_lieu.doc", "kieu": "dong_bo", "chong_trung": false},
    {"ma": "tong_quan", "phuong_thuc": "GET", "duong_dan": "/tong-quan",
     "dau_vao": "schema/khung_vao.v1.json", "dau_ra": "schema/khung_ra.v1.json",
     "quyen": "mau_tai_lieu_demo.tai_lieu.doc", "kieu": "dong_bo", "chong_trung": false},
    {"ma": "luu_ghi_chu", "phuong_thuc": "PUT", "duong_dan": "/ghi-chu/{id}",
     "dau_vao": "schema/ghi_chu_vao.v1.json", "dau_ra": "schema/ghi_chu_ra.v1.json",
     "quyen": "mau_tai_lieu_demo.ghi_chu.sua", "kieu": "dong_bo", "chong_trung": true,
     "kiem_row_version": true},
    {"ma": "nhan_dang", "phuong_thuc": "POST", "duong_dan": "/nhan-dang",
     "dau_vao": "schema/nhan_dang_vao.v1.json", "dau_ra": "urn:ktt:contract:viec.v1#/$defs/da_nhan",
     "quyen": "mau_tai_lieu_demo.engine.goi", "kieu": "viec", "chong_trung": true,
     "quy_trinh": "nhan_dang_demo@1"}
  ],
  "du_lieu_rieng": {
    "bang": ["ghi_chu"],
    "ham": ["giai_pham_vi_demo", "kiem_nghia_vu_demo"],
    "phan_vung": "phap_nhan_id",
    "goi_migration": {
      "ma": "mau_tai_lieu_demo",
      "phien_ban_du_lieu": 1,
      "tep_kiem_ke": "migration/kiem_ke.json",
      "thu_muc": "migration"
    },
    "v2_ghi_chung": ["bien_nhan_thao_tac", "tao_viec", "ghi_ket_qua"],
    "v3_danh_muc": [{"doi_tuong": "danh_muc.doi_tac", "truong": ["id", "ten"]}],
    "v4_cong_bo_doc": [],
    "cot_nhom_a": [{"bang": "ghi_chu", "cot": "tai_khoan_demo",
      "cot_ban_ma": "tai_khoan_ban_ma", "cot_phien_ban_khoa": "tai_khoan_phien_ban_khoa",
      "cot_hmac": "tai_khoan_hmac", "mien_hmac": "mau_tai_lieu_demo.ghi_chu.tai_khoan_demo",
      "chuan_hoa": "so_tai_khoan_v1", "quyen_xem_du": "mau_tai_lieu_demo.tai_khoan.xem_du"}]
  },
  "ham_core_goi": [
    {"loai_ham": "resolver_mtq", "phien_ban_contract": "1",
     "ham": "giai_pham_vi_demo", "chu_ky": "schema/resolver_mtq.v1.json"},
    {"loai_ham": "kiem_nghia_vu", "phien_ban_contract": "1",
     "ham": "kiem_nghia_vu_demo", "chu_ky": "schema/kiem_nghia_vu.v1.json"}
  ],
  "ma_loi": [{"ma": "DEMO_GHI_CHU_KHONG_HOP_LE", "http": 422,
               "truong": ["ghi_chu"]}],
  "quyen_yeu_cau": [
    {"tai_nguyen": "tai_lieu", "hanh_dong": ["doc"],
     "truong": ["id", "ten"], "bien_the": [], "pham_vi": "phap_nhan_va_ho_so_duoc_cap"},
    {"tai_nguyen": "tep", "hanh_dong": ["doc", "tai_xuong"],
     "truong": ["id", "mime", "kich_thuoc", "ma_bam"],
     "bien_the": ["goc"], "pham_vi": "tep_cua_tai_lieu_duoc_cap"},
    {"tai_nguyen": "ket_qua", "hanh_dong": ["doc"],
     "truong": ["id", "contract", "nguon", "trang_thai_duyet"],
     "bien_the": ["ocr_tho"], "pham_vi": "ket_qua_duoc_cap"},
    {"tai_nguyen": "engine", "hanh_dong": ["goi"],
     "capability": ["ocr.trich_van_ban@1"], "pham_vi": "viec_cua_module"},
    {"tai_nguyen": "ghi_chu", "hanh_dong": ["doc", "sua"],
     "pham_vi": "du_lieu_rieng_cung_phap_nhan"},
    {"tai_nguyen": "su_kien", "hanh_dong": ["phat", "nhan"],
     "loai": ["mau_tai_lieu_demo.ghi_chu_doi@1", "tai_lieu.cap_nhat@1"],
      "pham_vi": "cung_phap_nhan_duoc_cap"}
  ],
  "engine_dung": [
    {"capability": "ocr.trich_van_ban@1", "bat_buoc": true,
     "dau_vao": "tham_chieu_tep.v1", "dau_ra": "van_ban_tai_lieu.v1"}
  ],
  "quy_trinh": [
    {"ma": "nhan_dang_demo", "phien_ban": "1",
     "tep": "quy_trinh/nhan_dang_demo.v1.json"}
  ],
  "cong_bo": [
    {"ma": "ghi_chu", "phien_ban": "1",
      "ham": "ghi_chu_v1",
     "schema": "contract/cong_bo_ghi_chu.v1.schema.json",
     "truong": ["tai_lieu_id", "row_version"],
     "quyen_doc": "mau_tai_lieu_demo.ghi_chu.doc"}
  ],
  "su_kien": {
    "phat": [{"loai": "mau_tai_lieu_demo.ghi_chu_doi", "phien_ban": 1,
              "tham_chieu": ["ghi_chu_id", "tai_lieu_id"]}],
    "nhan": [{"loai": "tai_lieu.cap_nhat", "phien_ban": 1,
              "xu_ly": "danh_dau_can_lam_moi"}]
  },
  "tien_trinh": {
    "cong": {"nguon": "core_cap", "pham_vi": "loopback"},
    "nhan_listener": "socket.fromshare",
    "readiness": "kenh_dieu_khien",
    "thu_hoi": "drain_va_xac_nhan",
    "bi_mat": "stdin_hoac_handle",
    "che_do_mac_dinh": "tu_kich_hoat_tu_dong",
    "ranh_giay_de_xuat": 300
  },
  "cong_tac": {"mac_dinh": "TAT"}
}
```

Core ghép route operation dưới `/api/v1/module/mau_tai_lieu_demo/`; không nhận wildcard. `tong_quan` trả dữ liệu đã lọc quyền; `danh_sach` nhận cùng bộ lọc để số/thẻ khớp chi tiết.

Các tệp kiểm kê phải chứa đường dẫn, phiên bản và SHA-256 thực do bước đóng gói tạo; Core đối chiếu bytes trước cài. `v2_ghi_chung` là mã cửa ghi Core trong registry, ánh xạ tới chữ ký SQL được duyệt, không phải tên SDK đọc hoặc quyền SQL tự tạo. Core tự suy schema `mod_<ma>`, owner `vai_doi_cau_truc_mod_<ma>`, runtime `vai_chay_mod_<ma>` và đối tượng công bố `cong_bo_<ma>.<ham>`; gói không được khai `du_lieu_rieng.schema`, `goi_migration.vai` hoặc `cong_bo[].doi_tuong`. `tien_trinh.cong`/`ho_so_chay_mau.cong` chỉ nhận hằng `{nguon: core_cap, pham_vi: loopback}`, không nhận số cổng.

Khi cài/nâng cấp, Core kiểm `contract/` và ghi sổ `loi.dang_ky_contract` theo CSDL §3.1, không sửa code Core khi thêm module. Đăng ký không đồng nghĩa được đọc: vẫn phải cấp quyền thực tế. Contract nghiệp vụ mới hoặc phiên bản mới của contract đang dùng phải xuất danh mục dạng bảng và được Anh duyệt trước kích hoạt. Giữ phiên bản cũ cho module đang dùng, cảnh báo module còn ghim bản sắp ngừng. Màn quản trị đọc sổ: **bổ sung route quản trị sổ contract khi mở G2**; không thay phiếu API đã duyệt.

`ham_core_goi` đăng ký vào `loi.dang_ky_ham_module` khi cài, gồm loại/phiên bản/chữ ký, owner và hash gói do Core suy và kiểm. Resolver MTQ/kiểm nghĩa vụ là DEFINER đúng owner module và policy FORCE RLS, chỉ cổng Core nội bộ EXECUTE; không cho Core SELECT bảng riêng, không nhận tên hàm từ client. Chưa cài/chưa có contract trả `CHO`, không commit ghi liên quan dở (CSDL §4.2). Module có thể khai mảng rỗng nếu không có nghiệp vụ tương ứng; M4 khai resolver/kiểm nghĩa vụ qua gói, không vá Core.

Mọi mã quyền module có tiền tố `<ma>.`; quyền Core trong `quyen_yeu_cau` là yêu cầu độc lập, cần đủ quyền Core và MTQ khi gọi, không bị tiền tố module thay thế. `cot_nhom_a` khai cột logic, cột bản mã/phiên bản khóa/HMAC, miền/chuẩn hóa và quyền xem đủ. `CotDaDangKy` tại §3 gồm định danh cột đã đăng ký, ID dòng và pháp nhân được xác minh; Core tự chọn khóa, không nhận khóa từ caller. Các schema phụ, chữ ký hàm, contract sự kiện/công bố phải có trong gói; mẫu chưa phải gói cài được.

Quy trình mẫu chỉ gồm nhận tham chiếu → gọi OCR → bàn giao kết quả nháp. Quyền yêu cầu không đồng nghĩa quyền đã cấp; schema/role và mọi binding CSDL **theo phiếu CSDL/API**.

### 6.2. Mẫu engine manifest

Đây là mẫu đích của adapter DEMO sau hiệu chỉnh, không khẳng định OCR hiện có đã nhận socket hoặc có readiness chuẩn Core.

```json
{
  "phien_ban_manifest": 1,
  "loai": "engine",
  "ma": "e_ocr_demo",
  "ten": "Nhận dạng văn bản DEMO",
  "phien_ban": "0.1.0-demo.1",
  "tuong_thich": {"core": ">=1.0.0 <2.0.0", "api": "v1"},
  "adapter": {"ma": "bo_thich_ung_ocr_demo", "phien_ban": "1"},
  "capability": [
    {"ma": "ocr.trich_van_ban@1",
     "dau_vao": "tham_chieu_tep.v1",
     "dau_ra": "van_ban_tai_lieu.v1",
     "mime": ["application/pdf", "image/png", "image/jpeg"],
     "tep_toi_da_mib": 20,
     "trang_toi_da": 60,
     "thoi_han_giay": 900}
  ],
  "ho_so_chay_mau": {
    "ma_moi_truong": "ocr_cuc_bo",
    "diem_vao": "bo_thich_ung_ocr_demo.chay",
    "headless": true,
    "cong": {"nguon": "core_cap", "pham_vi": "loopback"},
    "nhan_listener": ["socket.fromshare", "tham_so_cong"],
    "tham_so_cong": "--port",
    "bi_mat": "stdin_hoac_handle",
    "login_csdl": false,
    "che_do_mac_dinh": "tu_kich_hoat_tu_dong",
    "ranh_giay_de_xuat": 300
  },
  "readiness": {
    "kenh": "dieu_khien_noi_bo",
    "kiem": ["instance", "phien_ban", "capability", "model_san_sang"],
    "thoi_han_giay": 120
  },
  "tai_nguyen": {
    "so_viec_dong_thoi": 1,
    "ram_toi_da_mib_de_xuat": 2048,
    "cpu_phan_tram_toi_da_de_xuat": 50
  },
  "ket_noi_ngoai": [],
  "ban_giao_ket_qua": "core_xac_nhan_truoc_giai_phong",
  "thu_hoi": "drain_va_xac_nhan"
}
```

Manifest công bố năng lực; **hồ sơ triển khai thực** do Core lưu riêng: máy chạy, executable, thư mục làm việc, đối số được duyệt, tham chiếu bí mật và giới hạn đã áp dụng. Gói không mang đường dẫn Python cố định hoặc khóa engine (`../54-ke-hoach-core-database-api-v1.md:259`).

`ket_noi_ngoai` mặc định rỗng: thiếu allowlist được Admin duyệt thì không kết nối ngoài. Mỗi mục chỉ khai mã dịch vụ trong registry Core và mục đích; không nhận URL/credential tùy ý. AI vẫn chỉ qua cổng AI của phần mềm, Cloud qua Mask v2; allowlist không tạo đường gọi API AI trực tiếp.

Các ngưỡng tài nguyên trên chỉ là đề xuất DEMO, chưa đo. Core kiểm khả năng cưỡng chế giới hạn trước kích hoạt. Adapter chỉ công bố capability thực đạt; không suy rằng OCR văn bản đồng nghĩa trích bảng, hoặc Mask hiện đã có API che tài liệu độc lập (`docs/47-core/g0/KS-D.md:53`; `docs/47-core/g0/KS-E.md:134`).

## 7. Vòng đời qua Module Manager

| Bước | Trách nhiệm Core/SDK và điều kiện hoàn tất |
|---|---|
| **Kiểm gói** | Nhận gói vào staging; chặn đường dẫn thoát thư mục, symlink và kích thước bất thường. Kiểm manifest, kiểm kê/hash, schema, trùng mã/route, tương thích Core/SDK/contract, phụ thuộc và capability. Không chạy mã gói trong bước đọc manifest |
| **Xem trước/cấp quyền** | Giao diện hiển thị phiên bản, quyền mới, thay đổi dữ liệu và phụ thuộc. Admin cấp quyền thực tế riêng với yêu cầu. Module không tự thêm dependency vào môi trường Core |
| **Cài migration gói** | Khóa cài theo module; dùng quyền migration đúng khối. Kiểm số phiên bản/checksum, chạy phần chưa áp dụng và ghi sổ **theo phiếu CSDL/API**. Không cho gói sửa bảng/hàm riêng module khác |
| **Kích hoạt** | Chỉ sau khi dữ liệu và asset đã chuẩn bị thành công: đăng ký route, giao diện, quy trình, công bố, sự kiện, hàm Core gọi module, cột nhóm A và cổng. Mỗi lần kích hoạt và mỗi lần Core khởi động chạy lại KT01/KT03 kiểm catalog/quyền hiệu lực, cùng readiness/kiểm tuân thủ; lệch quyền kể cả GRANT tay thì về chưa kích hoạt, không phục vụ |
| **Nâng cấp** | Ngừng nhận việc mới phù hợp phạm vi; ghim version cho việc đang chạy. Drain hoặc giữ runtime cũ khi đã có cơ chế hỗ trợ; nếu chưa hỗ trợ thì chờ hết việc. Ưu tiên mở rộng dữ liệu tương thích, đối chiếu rồi chuyển truy cập |
| **Tắt** | Công tắc nghiệp vụ theo pháp nhân về `TAT`, chặn tạo/nhận việc mới; cho việc đang giữ lease hoàn tất theo quyền hợp lệ. Công bố chính thức có thể trả `CHO`; lịch sử vẫn đọc theo quyền. Khi rảnh mới drain/thu hồi listener con; Core giữ cổng cố định, không trả cổng cho ứng dụng khác |
| **Phục hồi lỗi** | Migration lỗi không kích hoạt một phần. Transaction SQL không hoàn tác filesystem: dùng staging và bước kích hoạt riêng. Quay lại mã cũ chỉ khi tương thích dữ liệu; không rollback bằng xóa schema/bảng |

Giữ cơ chế checksum/transaction và chặn hạ phiên bản của `ha_tang/postgres.py:217`; điều chỉnh điều phối theo gói **theo phiếu CSDL/API**. Runtime không tự migrate khi khởi động.

Công tắc `TAT/THU/VAN_HANH` tách khỏi trạng thái tiến trình và chính sách tự đóng. Giữ cổng kiểm trong transaction, quyền xem lịch sử và quy tắc công bố hiện hữu (`k2/module.py:62`, `:99`). Tắt hoặc nâng cấp không xóa dữ liệu, tệp nguồn, lịch sử và biên nhận chống trùng.

## 8. Quyết định Anh đã chốt và điều kiện chuyển tiếp

| Câu đã chốt theo CD-033 | Quyết định | Yêu cầu áp dụng |
|---|---|---|
| **1. Module thử Core ở G2 — đã chốt CRM (DEMO)** | Dùng dữ liệu DEMO; lead đề xuất phạm vi CRM tối thiểu trong phiếu SDK bản 2 | Bao phủ tệp, engine trích xuất/OCR, việc lâu, công bố + sự kiện, `contract/`, cài/tắt qua giao diện, MTQ và cổng Core giữ/nhả theo CD-028; G4 vẫn M4 → CRM → M2, dùng tiếp phần CRM đã thử |
| **2. Tài khoản Windows — đã chốt A** | Core tài khoản riêng, module/engine tài khoản máy hạn chế, áp ngay khi thử trên máy Anh | Script tạo tài khoản/cấp quyền thư mục chạy lại được khi chuyển máy chủ; Anh chỉ đồng ý quyền quản trị. Ngoại lệ engine cũ phải hỏi Anh; không tự nới quyền. Bộ kiểm §4.4 phải chặn đọc `D:\DU-LIEU-KE-TOAN\bi-mat\` |
| **3. Việc/sự kiện chờ khi module tự đóng — đã chốt A** | Core khởi động ngay module được phép hoạt động | Admin đổi sau số đo theo CD-028 mục 3b; không tự bật module Anh đã tắt |

**Câu 2 là tài khoản Windows chạy tiến trình**, khác câu 3 phiếu CSDL (tài khoản người dùng do Core quản). §3 `danh_tinh`/`ma_hoa` và §4.2 dựa trên mã phiên bí mật/mã ủy nhiệm theo phiếu CSDL/API đã được Anh duyệt; vòng 3 chỉ bổ sung yêu cầu CD-031/032/033.

**Thông báo, không hỏi lại:** M4 là module mẫu đầu tiên G4. Retention/snapshot OCR giữ trong phiếu CSDL, không hỏi trùng tại đây.

**Nối tiếp kiểm hiện có:** giữ các ca XS-5 về chủ vùng/truy cập chéo/ngoại lệ tại `tests/test_xs5_khai_bao.py:37`, `:72`, `:93`; giữ kiểm MTQ đọc và cổng HTTP tại `tests/test_mtq_nen_sql.py:26`, `tests/test_mtq_http_dispatch.py:48`. Đưa chúng thành đầu vào bộ kiểm tuân thủ của G1c-2; không coi kiểm metadata là bằng chứng cách ly runtime.

Trước G2, lead cần ghép với contract và bộ kiểm G1c-2, chốt các cửa Core nội bộ còn thiếu với phiếu CSDL/API và review ranh giới phiên/quyền/socket. Khi được mở lập trình, nghiệm thu tối thiểu phải chứng minh: cài qua giao diện, tắt/nâng cấp giữ dữ liệu, hai người không chạy trùng việc, giả ngữ cảnh bị chặn, engine không có login CSDL và kết quả OCR được bàn giao trước giải phóng.

**Kiểm vòng 2:** 24/24 khối JSON parse; 12 tài nguyên schema có `$id` riêng, mọi `$ref` giải được offline; 12/12 ví dụ và 52/52 ca đúng/âm đạt kiểm tĩnh các keyword đang dùng; hai tệp UTF-8 không BOM, `git diff --check` đạt. Môi trường không có validator meta-schema draft 2020-12 chính thức nên chưa chạy bước đó; không cài thêm dependency/tạo tệp kiểm. Không chạy test ứng dụng hoặc runtime G2, không suy kiểm tĩnh thành đã cách ly Windows hay “xanh” regression; nền triển khai vẫn là `docs/46-chuyen-doi-dieu-phoi/NEN-TEST.md:3`.

## Vòng 2 — đã xử lý

Mã `O`/`C` được gán theo quy ước §1 để bao phủ từng dòng của hai review, không thay mã bộ kiểm KT.

| Mã phát hiện | Chỗ sửa |
|---|---|
| O-Chặn1; C1 | §2 biên nhận V2 vĩnh viễn tại `loi_tai_lieu.bien_nhan_thao_tac`, transaction/fingerprint/replay; §5, §7; contract/bộ kiểm KT05 |
| O-Chặn2; O-R1a,b | §2 ranh giới role/RLS/Core; §4.4 danh tính Windows và kiểm G2; §8 câu 2 |
| O-Chặn3; O-R1c | §3 dịch vụ thứ 12 `ma_hoa`; §6.1 cột nhóm A và schema manifest tại contract §15 |
| O-CS1; O-R1d | §3 `nhan_request`; §4.2 chữ ký/instance/TTL/nonce/hash |
| O-CS2; O-R1e; O-R2i | §2 `GiuViec`, §3 cấp mã theo lease; §4.3 đánh thức từ hàng việc/bus, định nghĩa rảnh |
| O-CS3; O-R3; C2 | §6 mẫu module/engine; contract §15 schema/version, tham chiếu, ca âm; V1–V4, registry hàm, quyền có tiền tố, Core suy role/schema/công bố, kết nối ngoài |
| O-CS4; O-R4 phiên bản | §6 ghim schema; contract §2–3 và hằng riêng từng contract |
| O-CS5; O-R4 AI/Mask | Contract §8–9 schema và kiểm CLOUD/lượt che, typed value, giữ tiền/ngày |
| O-CS6; O-R4 hóa đơn | Contract §10 schema thuế suất, nghĩa tổng, dấu chiết khấu; bộ kiểm §5 |
| O-CS7; O-R2ii,iii | §4.1 readiness/login/phiên bản, exclusive bind; §4.3 Windows Job/accounting |
| O-CS8; O-R1f và DSN; O-R5 | §2 `password=` riêng; §3 Core gắn nguồn; §7 kiểm lại KT01/KT03; contract KT08/KT09/KT10 và ca âm |
| O-CS9; O-R6; C5 | §8 đúng ba câu; thông báo M4 G4, bỏ retention trùng và logic khoản vay |
| C3 | §2, §6.1 `dau_ra` việc lâu trỏ `$defs/da_nhan`; schema manifest cưỡng chế |
| C4 | §2, §5, §6.1 `ma_loi`; contract §11 `chi_tiet` an toàn/đăng ký mã lỗi |

## Vòng 3 — CD-031/032/033

Kiểm tĩnh vòng 3: 24/24 khối JSON parse, 12 tài nguyên schema không trùng `$id`, 145/145 `$ref` giải được offline; 2/2 manifest ví dụ và 19/19 ca âm của phần manifest đạt kiểm các keyword đang dùng. Cả ba tệp UTF-8 không BOM; `git diff --check` đạt. Chưa kiểm bằng validator meta-schema draft 2020-12 chính thức (môi trường không có); không chạy test ứng dụng, tài khoản Windows hoặc runtime G2.

| Việc | Chỗ sửa |
|---|---|
| CD-031/032: lớp dữ liệu giao tiếp, gói `contract/` và manifest | §6, §6.1; dẫn chiếu JSON hai lớp và schema tại `CONTRACT-DU-LIEU.md` §1, §15 |
| CD-032: sổ contract, duyệt, giữ bản cũ và màn quản trị | §6.1; sổ `loi.dang_ky_contract` theo CSDL §3.1, ghi chú route đọc khi mở G2 |
| CD-033 câu 2: tài khoản Windows riêng ngay từ thử máy Anh | §4.4, §8: script chạy lại, ngoại lệ engine cũ, kiểm bí mật/DPAPI/bộ nhớ |
| CD-033 câu 1, 3: CRM DEMO và khởi động ngay | §4.3, §6.1, §8: ba câu đã chốt |
