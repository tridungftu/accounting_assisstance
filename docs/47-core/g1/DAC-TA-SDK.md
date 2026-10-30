# DAC-TA-SDK.md — SDK Core và mẫu gói module

**Lát G1c-1 · Ngày 30/10/2026 · Dự thảo chờ review và Anh duyệt**

**Đề xuất:** SDK bọc lại MTQ, hợp đồng engine, hàng việc, bus và khai báo module hiện có; bổ sung giao tiếp liên tiến trình, quản lý gói và các dịch vụ Core còn thiếu. Module giữ nghiệp vụ và dữ liệu riêng; Core quản lý danh tính, quyền, tài liệu, điều phối và vòng đời tiến trình.

Đây là đặc tả đích, chưa phải chức năng đã triển khai. Lát này chỉ đọc và soạn tài liệu; không sửa tệp, chạy test, SQL, migration hoặc dịch vụ.

## 1. Căn cứ và quy ước

Áp dụng TL 54 §5.2, §7, §8, ưu tiên §14; TL 55 §3, §5, §10; CD-026–029; KS-A, KS-D, KS-E; hai bản nháp CSDL/API và review Opus.

Các quyết định chi phối:

- Mỗi module/engine chạy tiến trình riêng; Core cấp và giữ cổng, mặc định **tự kích hoạt + tự đóng** (`docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:329`).
- Engine không có login CSDL. Module nhận mật khẩu qua stdin/handle, chỉ dùng role runtime đúng khối; mã phiên bí mật và ủy nhiệm phải được kiểm chứng (`docs/47-core/g1/RV-G1A-OPUS.md:41`).
- G2 chỉ mở sau khi đủ ba phiếu CSDL/API/SDK được duyệt (`docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:342`).

**Quy ước dẫn chiếu:** `ha_tang/`, `k2/`, `giao_dien/`, `nguon/` và `workflow.py` tính từ `src/kho_tri_thuc/`; `tests/`, `docs/` tính từ gốc repo.

Tên mới dùng tiếng Việt không dấu, `snake_case`. Giữ tên giao thức và tên đang đúng như `module.json`, `socket.fromshare`, `row_version`, `Idempotency-Key`. Nhãn/thông báo cho người dùng dùng tiếng Việt có dấu.

Mọi chữ ký SDK mới dưới đây là **đề xuất**. Route, hàm SQL đích, role, cách xác minh phiên và trạng thái chưa duyệt đều **theo phiếu CSDL/API**. Không suy từ một chữ ký trong tài liệu rằng hàm đó đã tồn tại.

## 2. Hợp đồng chung của SDK Python

SDK Python phục vụ backend module và adapter phía Core. Tiến trình engine chỉ nhận phần giao tiếp công việc, tệp được ủy nhiệm và báo trạng thái; không nhận `du_lieu_rieng` hoặc kết nối PostgreSQL.

| Kiểu/quy ước | Nội dung |
|---|---|
| `ctx: NguCanh` | Bất biến, do SDK dựng sau xác thực Core; chứa định danh người, module, pháp nhân, operation và trace. Mã bí mật nằm trong đối tượng bảo vệ, không xuất qua `repr`, JSON hay log |
| `tx: GiaoDich` | Transaction của module, đúng login/role/schema và pháp nhân; ngữ cảnh transaction được xác minh từ mã phiên/ủy nhiệm |
| `Ma` | UUID, trừ khóa kiểm toán hiện hữu được giữ và trả dạng chuỗi |
| `Trang[T]` | `danh_sach`, `con_tiep`, `con_tro_tiep`; phân trang theo phiếu CSDL/API |
| `BienNhanViec` | `viec_id`, trạng thái và địa chỉ theo dõi; chỉ trả sau khi ghi bền vững |
| `ThamChieuTep` | Contract `tham_chieu_tep.v1`; không có đường dẫn vật lý hoặc URL tùy ý |
| Dữ liệu | Tiền/tỷ lệ dùng `Decimal` trong Python, chuỗi decimal trên JSON; ngày nghiệp vụ ISO; thời điểm có múi giờ |
| Lỗi | `LoiSDK(ma, thong_diep, request_id, thu_lai_duoc, http_status)`; không lộ SQL, khóa, mật khẩu hoặc nội dung nguồn |

Các hàm nhận `ctx` đều có thể lỗi 401/403; đối tượng ngoài phạm vi nhìn thấy trả 404. Schema sai trả 422; CAS/chống trùng/trạng thái xung đột trả 409; dữ liệu tạm hết hạn trả 410; phụ thuộc chưa sẵn sàng trả 503 — **theo phiếu CSDL/API** (`docs/47-core/g1/DAC-TA-API.md:61`).

`row_version` trên JSON là chuỗi số nguyên. Không đồng nhất nó với revision nghiệp vụ hoặc hash căn cứ (`docs/47-core/g1/DAC-TA-API.md:111`).

**Ranh giới giao dịch:** lời gọi HTTP tới Core có transaction riêng. Khi cần ghi dữ liệu module cùng bus, hàng việc hoặc hàm Core trong một transaction, SDK dùng cửa hàm CSDL được cấp trên chính `tx`; không mô phỏng tính nguyên tử bằng hai lời gọi HTTP. Các hàm nhận `tx` không tự commit.

## 3. Dịch vụ SDK Python

Trong bảng, lỗi ghi cạnh chữ ký bổ sung cho lỗi chung tại §2. Các tham số `loc`, `tham_so`, `du_lieu` phải khớp schema đã đăng ký.

| Dịch vụ · mục đích | Hàm chính, đầu vào → đầu ra; lỗi | Cửa gọi và phần tái dùng |
|---|---|---|
| **`danh_tinh`** · danh tính và quyền được xác thực | `hien_tai(ctx) -> DanhTinh`.<br>`kiem_quyen(ctx, hanh_dong: str, doi_tuong: dict) -> None`; thiếu quyền: 403.<br>`uy_nhiem_viec(ctx, viec_id: Ma) -> UyNhiem`; sai chủ/phạm vi: 403/404, việc không hợp lệ: 409. Core giới hạn ủy nhiệm theo việc và quyền hiện tại | Đọc qua `/toi`, `/phap-nhan`; kiểm quyền/ủy nhiệm qua cửa Core nội bộ **theo phiếu CSDL/API**. Giữ logic nạp danh tính/quyền tại `k2/quyen.py:88`, `:116`; quyết định đọc MTQ không thay cổng thực hiện hành động (`k2/sql_mtq_nen.py:1`) |
| **`tai_lieu`** · quản lý metadata hồ sơ | `liet_ke(ctx, loc: dict, con_tro: str\|None=None) -> Trang[TaiLieu]`; lọc sai: 422.<br>`lay(ctx, tai_lieu_id: Ma) -> TaiLieu`; 404.<br>`tao(ctx, tep_id: Ma, thong_tin: dict, khoa: str) -> TaiLieu`; tệp chưa hợp lệ: 422, trùng khác nội dung: 409 | GET/POST `/tai-lieu`, GET `/tai-lieu/{id}` **theo phiếu CSDL/API**. Bọc nền tiếp nhận/hash/phiếu nhận hiện hữu, không tạo kho tiếp nhận thứ hai (`giao_dien/intake.py:75`; khảo sát `docs/47-core/g0/KS-A.md:20`) |
| **`tep`** · nhận và đọc bytes qua kho Core | `tai_len(ctx, luong: BinaryIO, ten: str, mime: str, khoa: str) -> ThamChieuTep`; 413/415/422/409.<br>`tham_chieu(ctx, tep_id: Ma) -> ThamChieuTep`; 404/410.<br>`mo_doc(ctx, tep_id: Ma) -> BinaryIO`; 404/410; SDK đóng luồng khi thoát phạm vi sử dụng | POST `/tep`, GET `/tep/{id}`, GET `/tep/{id}/noi-dung` **theo phiếu CSDL/API**. Giữ ghi bất biến/chống ghi đè tại `ha_tang/store.py:26`. Kiểm quyền trước mở luồng; cùng hash không đồng nghĩa cùng quyền |
| **`ket_qua`** · kết quả có phiên bản và nguồn | `lay(ctx, ket_qua_id: Ma) -> KetQua`; 404/410.<br>`ghi(tx, tep_id: Ma, contract: str, nguon: dict, khoa: str) -> Ma`; nguồn/schema sai: 422, xung đột: 409.<br>`tao_revision(tx, ket_qua_id: Ma, revision_truoc: str, tep_id: Ma, ly_do: str, khoa: str) -> KetQua`; 409/422 | GET `/ket-qua/{id}`; ghi/revision qua hàm Core được cấp **theo phiếu CSDL/API**, chưa có route ghi tương ứng trong nháp API. Giữ bằng chứng hash/engine/version tại `ha_tang/engine.py:77`, `:165`; giữ mẫu lưu kết quả và kết thúc việc cùng CAS tại `ha_tang/chay_engine.py:159`. Các hàm này không tự phê duyệt nghiệp vụ |
| **`du_lieu_rieng`** · repository đúng khối module | `giao_dich(ctx) -> ContextManager[GiaoDich]`; 403/503.<br>`doc(tx, ma_truy_van: str, tham_so: dict) -> Trang[dict]`; truy vấn ngoài đăng ký: 403, tham số sai: 422.<br>`ghi(tx, ma_lenh: str, tham_so: dict, row_version: str\|None, khoa: str) -> BienNhan`; 409/422 | Repository module chỉ chạm V1; gọi hàm Core V2 và đọc V3/V4 đúng quyền. Role/RLS và hàm thiết lập phiên **theo phiếu CSDL/API**. Tái dùng `KhaiBaoVungDuLieu` tại `ha_tang/khai_bao_module.py:144` và bản khai `k2/vung_du_lieu.py:182`. Bộ kiểm hiện mới kiểm khai báo/điểm được truyền vào (`ha_tang/khai_bao_module.py:225`) |
| **`cong_bo`** · đọc contract module khác công bố | `liet_ke(ctx) -> list[KhaiBaoCongBo]`.<br>`doc(tx, contract: str, tham_so: dict) -> KetQuaCongBo`; sai quyền: 403, tham số: 422.<br>`kiem_phien_ban(tx, contract: str, doi_tuong_id: Ma, phien_ban: str, ma_bam: str) -> CanCu`; nguồn đã đổi: 409 | Registry và mặt đọc `cong_bo_<nguon>` **theo phiếu CSDL/API**. Giữ phép chiếu hóa đơn hiện tại `master.hoa_don_cong_bo`, gồm kiểm quyền trước tra cứu, phiên bản/hash và `CHO` (`k2/sql_cong_bo_hoa_don.py:15`, `:20`, `:38`). `CHO` là thiếu nguồn/công bố, không thay lỗi quyền. Đọc dữ liệu bền vững không đòi tiến trình nguồn đang chạy |
| **`su_kien`** · outbox/inbox có chống trùng | `phat(tx, loai: str, phien_ban: int, tham_chieu: dict, khoa: str) -> Ma`; 409/422.<br>`nhan(tx, loai: str\|None=None, gioi_han: int=100) -> list[SuKien]`; 422.<br>`xac_nhan(tx, su_kien_id: Ma) -> bool`; chưa nhận: 409; ACK lặp trả `False` | Bọc nguyên `bus.phat/nhan/ack`; tên/schema đích **theo phiếu CSDL/API**. Wrapper tại `ha_tang/bus_su_kien.py:30`, `:49`, `:64`. Payload chỉ tham chiếu UUID, bên phát/nhận suy từ module đã xác thực. Ghi nghiệp vụ và ACK cùng transaction; giao ít nhất một lần |
| **`engine`** · gửi capability qua Core/adapter | `liet_ke(ctx) -> list[KhaNang]`.<br>`kha_nang(ctx, capability: str) -> KhaNang`; không có/không được thấy: 404.<br>`gui_viec(ctx, capability: str, dau_vao: dict, khoa: str) -> BienNhanViec`; 409/422/429/503 | GET `/engine`, GET `/engine/{ma}`, POST `/engine/{ma}/viec` **theo phiếu CSDL/API**. Core ánh xạ capability sang engine/adapter đã ghim. Giữ `Engine.chay` và danh bạ tra đúng version, không tự chọn mới nhất (`ha_tang/engine.py:165`; `ha_tang/danh_ba_engine.py:33`). Giữ cổng OCR/AI được tiêm (`ha_tang/engine_cong.py:127`, `:154`) |
| **`quy_trinh`** · chạy phiên bản quy trình cố định | `liet_ke(ctx) -> list[QuyTrinh]`.<br>`bat_dau(ctx, ma: str, phien_ban: str, dau_vao: dict, khoa: str) -> BienNhanViec`; 409/422/503.<br>`tiep_tuc(ctx, lan_chay_id: Ma, buoc: str, revision_truoc: str, du_lieu: dict, khoa: str) -> BienNhanViec`; 409/422 | GET `/quy-trinh`, POST `/quy-trinh/{id}/lan-chay`; cửa tiếp tục **theo phiếu CSDL/API**, chưa có route tương ứng trong nháp. Dùng hàng việc XS-2 làm nền; giữ nghiệp vụ hiện hữu làm handler bước. Chưa có runner chung theo khảo sát `docs/47-core/g0/KS-A.md:23`; không coi bảng dispatch `workflow.py:15` là runner hoàn chỉnh |
| **`viec`** · theo dõi, hủy và báo tiến độ | `lay(ctx, viec_id: Ma) -> Viec`; 404.<br>`ket_qua(ctx, viec_id: Ma) -> list[KetQua]`; 404, vẫn kiểm từng kết quả.<br>`huy(ctx, viec_id: Ma, khoa: str) -> BienNhanViec`; 409.<br>`bao_tien_do(tx, giu_viec: GiuViec, muc: int) -> bool`; mức sai: 422, mất lease: từ chối cập nhật | GET `/viec/{id}`, GET `/viec/{id}/ket-qua`, POST `/viec/{id}/huy` **theo phiếu CSDL/API**. Giữ wrapper tạo/nhận/gia hạn/kết thúc tại `ha_tang/hang_viec.py:21`, `:31`, `:43`, `:55`; giữ lease/token và `SKIP LOCKED` (`k2/sql_hang_viec.py:161`). Engine báo qua Core, không gọi các hàm SQL này |
| **`kiem_toan`** · audit và số đo vận hành | `ghi(tx, hanh_dong: str, doi_tuong: dict, ket_luan: dict) -> str`; metadata không cho phép: 422.<br>`tra_cuu(ctx, loc: dict, con_tro: str\|None=None) -> Trang[BanGhiKiemToan]`; 403/422.<br>`ghi_so_do(ctx_tien_trinh, so_do: dict) -> BienNhan`; sai instance: 403, dữ liệu sai: 422 | Ghi/tra audit và nhận số đo qua cửa Core nội bộ **theo phiếu CSDL/API**; đọc quản trị số đo qua `/quan-tri/so-do`. Giữ audit hiện hữu (`ha_tang/pg_migrations.py:413`; đối chiếu `docs/47-core/g0/KS-A.md:25`). Core tự gắn actor/trace/thời điểm; báo cáo module không được giả thành kết luận đã xác minh của Core |

**Quy tắc thực thi giữ lại:**

- Bộ worker Core dùng lại `nhan`, `gia_han`, `trang_thai_lease`, `ket_thuc`, `thu_lai`; mất lease thì rollback phần lưu kết quả (`ha_tang/chay_engine.py:102`, `:159`).
- Kết quả tác động ngoài chưa rõ phải giữ `CHUA_RO`, không tự retry. Adapter giữ trạng thái nguồn; ánh xạ ra API **theo phiếu CSDL/API**, không làm mất dấu chưa rõ (`k2/sql_hang_viec.py:12`, `:137`).
- `XONG/CHO/LOI` của engine, trạng thái việc và trạng thái duyệt là ba lớp khác nhau (`ha_tang/engine.py:24`; `docs/47-core/g1/DAC-TA-CSDL.md:210`).
- AI đi qua cổng AI phần mềm; luôn có đường Local, Cloud qua Mask v2. Adapter không tạo cổng hoặc bộ che thứ hai (`ha_tang/engine_cong.py:1`).

## 4. Khung tiến trình module/engine

### 4.1. Khởi động và nhận listener

1. Core khóa phối hợp theo chủ chạy/máy chủ, lấy cổng cố định và thế hệ sở hữu từ sổ cổng **theo phiếu CSDL/API**. Các request đang chờ dùng chung một lần khởi động.
2. Core khởi động headless từ hồ sơ đã duyệt. Tiến trình con nhận cấu hình qua stdin hoặc handle riêng có giới hạn quyền; không nhận mật khẩu/token qua dòng lệnh, biến môi trường hoặc tệp cấu hình gói.
3. Với Python hỗ trợ chuyển giao: sau khi có PID thật, Core gửi dữ liệu `socket.share(pid)`; SDK nhận bằng `socket.fromshare`. Core giữ bản handle để thu hồi, nhưng chỉ một bên có quyền accept theo trạng thái bàn giao.
4. Với engine cũ: Core đóng listener rồi truyền đúng cổng bằng tham số. Nếu bind thất bại, báo `CONG_BI_CHIEM`; không dò cổng khác hoặc dừng ứng dụng lạ. Đây là phương án chuyển tiếp có khoảng hở.
5. SDK gửi thông điệp sẵn sàng gồm: mã chủ, instance, PID và định danh lần tạo tiến trình, nonce khởi động, phiên bản, capability/contract thực có, cổng và kết quả kiểm readiness. Core xác minh xong mới chuyển request.

Thông điệp bootstrap/readiness là contract nội bộ mới, **theo phiếu CSDL/API**. Không đánh đồng listener hoạt động, `/healthz` thành công và capability thực sự sẵn sàng.

Tái dùng bắt tay/readiness và quản lý Windows Job của host #6; thay phần tự chọn cổng (`nguon/trich6_host.py:240`, `:280`, `:607`; đối chiếu `docs/47-core/g0/KS-A.md:75`). Việc chuyển giao/thu hồi socket không khoảng hở cần thử ở G2, chưa được xác nhận vận hành trong lát này.

### 4.2. Phiên, ủy nhiệm và CSDL

Phân biệt ba loại:

| Loại | Phạm vi |
|---|---|
| Danh tính tiến trình | Core cấp khi bootstrap; xác thực module/engine và instance |
| Ngữ cảnh request | Token ngắn hạn ràng buộc nơi nhận, operation, pháp nhân, trace, nonce và nội dung request; chữ ký/TTL **theo phiếu CSDL/API** |
| Mã phiên/ủy nhiệm CSDL | Bí mật do Core cấp, CSDL kiểm phiên còn hạn, đúng login/module/pháp nhân và việc được giao; không dùng UUID người dùng hoặc GUC tự khai làm bằng chứng |

Module nhận credential runtime riêng qua stdin/handle; không nhận credential migration. SDK đặt ngữ cảnh theo transaction và làm sạch khi trả kết nối về pool.

Engine không nhận login CSDL. Engine chỉ nhận bytes/tham chiếu có quyền theo việc; yêu cầu đọc tệp hoặc bàn giao kết quả đều qua Core. Token HTTP ngắn hạn không được lưu làm ủy nhiệm cho việc nền dài hạn (`docs/47-core/g1/DAC-TA-API.md:199`; `docs/47-core/g1/RV-G1A-OPUS.md:43`).

### 4.3. Thu hồi và đo khởi động

Khi Core yêu cầu thu hồi, SDK ngừng nhận việc mới, tiếp tục heartbeat cho việc đang giữ, chờ kết thúc hoặc điểm dừng an toàn, bàn giao kết quả rồi xác nhận dừng. Với listener chia sẻ, tiến trình con đóng handle của mình; không gọi `shutdown` làm hỏng listener Core giữ.

Không đóng engine khi còn kết quả chưa bàn giao, luồng tải hoặc ánh xạ Mask còn cần dùng. Nếu không drain được trong hạn, báo trạng thái/lý do; không tự coi việc đã hủy. Core chỉ xử lý tiến trình đã xác minh thuộc mình.

Core ghi từng lần khởi động: giờ yêu cầu, bắt đầu, sẵn sàng/thất bại, thời gian xử lý, thời gian rảnh trước đóng, số lần/ngày, RAM và CPU kèm cửa sổ đo. Thiếu số đo ghi “chưa đo”. Hằng tuần chỉ đề xuất thay chế độ; **Admin bấm áp dụng**, có CAS và audit (`docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:332`).

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

### 6.1. Mẫu module nhỏ

Ví dụ minh họa gói **Tra cứu tài liệu DEMO**, chưa chọn thay module mẫu chính thức ở §8. Các đường dẫn là thành phần gói dự kiến, chưa được tạo. `thao_tac` tương ứng operation. Nhãn giao diện có dấu; mã kỹ thuật không dấu.

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
       "duong_dan": "#mau_tai_lieu_demo/tai_lieu", "quyen_xem": "tai_lieu.doc"},
      {"ma": "ket_qua", "ten": "Kết quả", "icon": "file", "thu_tu": 2,
       "duong_dan": "#mau_tai_lieu_demo/ket_qua", "quyen_xem": "ket_qua.doc",
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
     "quyen": "tai_lieu.doc", "kieu": "dong_bo", "chong_trung": false},
    {"ma": "tong_quan", "phuong_thuc": "GET", "duong_dan": "/tong-quan",
     "dau_vao": "schema/khung_vao.v1.json", "dau_ra": "schema/khung_ra.v1.json",
     "quyen": "tai_lieu.doc", "kieu": "dong_bo", "chong_trung": false},
    {"ma": "luu_ghi_chu", "phuong_thuc": "PUT", "duong_dan": "/ghi-chu/{id}",
     "dau_vao": "schema/ghi_chu_vao.v1.json", "dau_ra": "schema/ghi_chu_ra.v1.json",
     "quyen": "ghi_chu.sua", "kieu": "dong_bo", "chong_trung": true,
     "kiem_row_version": true},
    {"ma": "nhan_dang", "phuong_thuc": "POST", "duong_dan": "/nhan-dang",
     "dau_vao": "schema/nhan_dang_vao.v1.json", "dau_ra": "viec.v1",
     "quyen": "engine.goi", "kieu": "viec", "chong_trung": true,
     "quy_trinh": "nhan_dang_demo@1"}
  ],
  "du_lieu_rieng": {
    "schema": "mod_mau_tai_lieu_demo",
    "bang": ["ghi_chu"],
    "phan_vung": "phap_nhan_id",
    "goi_migration": {
      "ma": "mau_tai_lieu_demo",
      "phien_ban_du_lieu": 1,
      "tep_kiem_ke": "migration/kiem_ke.json",
      "thu_muc": "migration",
      "vai": "doi_cau_truc_module"
    },
    "ham_core_dung": ["tai_lieu.lay", "ket_qua.lay"],
    "cong_bo_doc": []
  },
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
     "pham_vi": "cung_phap_nhan_va_doi_tuong_duoc_cap"}
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
     "doi_tuong": "cong_bo_mau_tai_lieu_demo.ghi_chu_v1",
     "schema": "schema/cong_bo_ghi_chu.v1.json",
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

Các tệp kiểm kê phải chứa đường dẫn, phiên bản và SHA-256 thực do bước đóng gói tạo; Core đối chiếu bytes trước cài. `ham_core_dung` là mã dịch vụ SDK, không tự tạo quyền SQL. Các schema phụ của mẫu, contract sự kiện và mặt công bố phải có trong gói; mẫu manifest không thay thế chúng.

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
  "ban_giao_ket_qua": "core_xac_nhan_truoc_giai_phong",
  "thu_hoi": "drain_va_xac_nhan"
}
```

Manifest công bố năng lực; **hồ sơ triển khai thực** do Core lưu riêng: máy chạy, executable, thư mục làm việc, đối số được duyệt, tham chiếu bí mật và giới hạn đã áp dụng. Gói không mang đường dẫn Python cố định hoặc khóa engine (`../54-ke-hoach-core-database-api-v1.md:259`).

Các ngưỡng tài nguyên trên chỉ là đề xuất DEMO, chưa đo. Core kiểm khả năng cưỡng chế giới hạn trước kích hoạt. Adapter chỉ công bố capability thực đạt; không suy rằng OCR văn bản đồng nghĩa trích bảng, hoặc Mask hiện đã có API che tài liệu độc lập (`docs/47-core/g0/KS-D.md:53`; `docs/47-core/g0/KS-E.md:134`).

## 7. Vòng đời qua Module Manager

| Bước | Trách nhiệm Core/SDK và điều kiện hoàn tất |
|---|---|
| **Kiểm gói** | Nhận gói vào staging; chặn đường dẫn thoát thư mục, symlink và kích thước bất thường. Kiểm manifest, kiểm kê/hash, schema, trùng mã/route, tương thích Core/SDK/contract, phụ thuộc và capability. Không chạy mã gói trong bước đọc manifest |
| **Xem trước/cấp quyền** | Giao diện hiển thị phiên bản, quyền mới, thay đổi dữ liệu và phụ thuộc. Admin cấp quyền thực tế riêng với yêu cầu. Module không tự thêm dependency vào môi trường Core |
| **Cài migration gói** | Khóa cài theo module; dùng quyền migration đúng khối. Kiểm số phiên bản/checksum, chạy phần chưa áp dụng và ghi sổ **theo phiếu CSDL/API**. Không cho gói sửa bảng/hàm riêng module khác |
| **Kích hoạt** | Chỉ sau khi dữ liệu và asset đã chuẩn bị thành công: đăng ký route, giao diện, quy trình, công bố, sự kiện và cổng. Chạy readiness/kiểm tuân thủ rồi chuyển phiên bản hoạt động; lỗi thì giữ trạng thái chưa kích hoạt |
| **Nâng cấp** | Ngừng nhận việc mới phù hợp phạm vi; ghim version cho việc đang chạy. Drain hoặc giữ runtime cũ khi đã có cơ chế hỗ trợ; nếu chưa hỗ trợ thì chờ hết việc. Ưu tiên mở rộng dữ liệu tương thích, đối chiếu rồi chuyển truy cập |
| **Tắt** | Công tắc nghiệp vụ theo pháp nhân về `TAT`, chặn tạo/nhận việc mới; cho việc đang giữ lease hoàn tất theo quyền hợp lệ. Công bố chính thức có thể trả `CHO`; lịch sử vẫn đọc theo quyền. Khi rảnh mới thu hồi tiến trình/cổng |
| **Phục hồi lỗi** | Migration lỗi không kích hoạt một phần. Transaction SQL không hoàn tác filesystem: dùng staging và bước kích hoạt riêng. Quay lại mã cũ chỉ khi tương thích dữ liệu; không rollback bằng xóa schema/bảng |

Giữ cơ chế checksum/transaction và chặn hạ phiên bản của `ha_tang/postgres.py:217`; điều chỉnh điều phối theo gói **theo phiếu CSDL/API**. Runtime không tự migrate khi khởi động.

Công tắc `TAT/THU/VAN_HANH` tách khỏi trạng thái tiến trình và chính sách tự đóng. Giữ cổng kiểm trong transaction, quyền xem lịch sử và quy tắc công bố hiện hữu (`k2/module.py:62`, `:99`). Tắt hoặc nâng cấp không xóa dữ liệu, tệp nguồn, lịch sử và biên nhận chống trùng.

## 8. Điểm cần Anh chọn và điều kiện chuyển tiếp

| Câu cần Anh chọn | Phương án và đánh đổi | Khuyến nghị |
|---|---|---|
| **1. Module mẫu chính thức đầu tiên?** | **A. M4 phạm vi hẹp:** bám TL 55/CD-027, kiểm tích hợp nghiệp vụ thực nhưng nhiều phụ thuộc. **B. Tra cứu tài liệu:** nhỏ, dễ kiểm SDK/kho/OCR, ít bao phủ nghiệp vụ kế toán. **C. M9:** có OCR/AI nhưng thêm logic khoản vay | **A**, chọn một luồng M4 nhỏ, độc lập phần hóa đơn. Mẫu Tra cứu DEMO ở §6 dùng giải thích cấu trúc gói, chưa thay thứ tự G4. Căn cứ: `../55-ke-hoach-chuan-hoa-core-va-dung-lai-module-engine.md:61`; `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:307` |
| **2. Tiếp tục soát OCR sau khi engine đóng?** | **A. Core giữ snapshot có kiểm quyền và hạn lưu được duyệt:** tiếp tục soát được, tăng lưu trữ. **B. Giữ RAM-only:** ít lưu trữ, hết phiên phải tải/chạy lại | **A** cho luồng cần soát; loại nội dung và hạn giữ **theo phiếu CSDL/API**. Chưa có chính sách thì không tự lưu lâu dài. OCR hiện có TTL kết quả 600 giây (`docs/47-core/g0/KS-E.md:112`) |

**Nối tiếp kiểm hiện có:** giữ các ca XS-5 về chủ vùng/truy cập chéo/ngoại lệ tại `tests/test_xs5_khai_bao.py:37`, `:72`, `:93`; giữ kiểm MTQ đọc và cổng HTTP tại `tests/test_mtq_nen_sql.py:26`, `tests/test_mtq_http_dispatch.py:48`. Đưa chúng thành đầu vào bộ kiểm tuân thủ của G1c-2; không coi kiểm metadata là bằng chứng cách ly runtime.

Trước G2, lead cần ghép với contract và bộ kiểm G1c-2, chốt các cửa Core nội bộ còn thiếu với phiếu CSDL/API và review ranh giới phiên/quyền/socket. Khi được mở lập trình, nghiệm thu tối thiểu phải chứng minh: cài qua giao diện, tắt/nâng cấp giữ dữ liệu, hai người không chạy trùng việc, giả ngữ cảnh bị chặn, engine không có login CSDL và kết quả OCR được bàn giao trước giải phóng.

**Đã tự đối chiếu:** tài liệu nguồn, chữ ký và vị trí mã nêu trên; không sửa tệp hoặc chạy test/runtime. Chưa có kết quả đạt/tổng hay kết luận “xanh”; khi triển khai sẽ so lỗi mới với `docs/46-chuyen-doi-dieu-phoi/NEN-TEST.md:3`.