# MTQ-0 · Thiết kế Ma trận thẩm quyền

Ngày: 26/10/2026 · Nhánh khảo sát: `lat/mtq-0` (hợp nhất). **Lát này chỉ viết thiết kế, chưa sửa mã/migration, chưa bật quyền.**

## 1. Phạm vi và căn cứ

Áp dụng [CD-010 mục 4 và CD-012](CHI-DAO-TU-ANH.md): bảng tick **vai theo phòng/pháp nhân × module/màn × hành động**, một cột giới hạn tiền VND mỗi dòng; để trống = không giới hạn; chỉ Admin cấp/sửa; ghi nhật ký từng lần sửa; Anh tự tick dữ liệu thật, DEMO có mẫu. CD-012 thay phần “chưa chốt” của CD-010; các lựa chọn bổ sung dưới đây là **mặc định lead đề xuất**, đưa vào phiếu cổng A, không ghi thành quyết định Anh đã chốt.

Dùng lại nguyên tắc máy chủ kiểm quyền của [TL 42 §1](../CRM-41-42-REFERENCE-20261020/42-man-hinh-crm-ke-toan-va-giao-ket.md). Không viết lại nghiệp vụ đang chạy. Khi một pháp nhân chưa bật ma trận, giữ nguyên toàn bộ đường kiểm cũ. Khi bật, **ma trận quyết định toàn bộ quyền hành động**; vai cũ, mảng module/V3/V4 và phân công hành động cũ không được cấp thêm quyền hoặc phủ quyết ô đã tick. Danh tính, phạm vi đối tượng và điều kiện nghiệp vụ vẫn bắt buộc.

Không triển khai M9 · Vốn vay & đầu tư tài chính (đang dừng); không gọi cổng thuế, Request thật, Junsky, dịch vụ ngoài hoặc đọc kho thật trong MTQ. M4 · Nghiệm thu & chi phí dự án ở CSDL riêng phải có cùng phiên bản cơ chế quyền trước khi được bật tại CSDL đó; MTQ không tự nối/chép dữ liệu thật giữa các CSDL.

### 1.1. Hiện trạng đã đối chiếu trong code

Đường dẫn trong tài liệu tính từ `src/kho_tri_thuc/`, trừ khi ghi khác. Số dòng là mốc khảo sát, tên hàm là khóa tra cứu lâu dài.

| Nguồn hiện có | Quy tắc thực tế / tác động tới MTQ |
|---|---|
| `ha_tang/pg_migrations.py:59–70, 966–971` | `master.nguoi_dung.vai_tro` là **một vai toàn cục**, chưa phải vai theo phòng/pháp nhân. `master.phan_quyen` có một dòng người × pháp nhân, `duyet_loai_viec[]`, bổ sung `module[]`; có `mo_phong`. |
| Cùng tệp, M0011 `ktt_danh_tinh`, `ktt_pn_cho_phep`, `ktt_duoc`, `ktt_co_vai` (`1224–1245`) | ID + login phải khớp người hoạt động. `ktt_duoc` kiểm pháp nhân/module; `ktt_co_vai` kiểm vai cũ và loại việc; RLS/trigger dùng lại các hàm này. Chỉ sửa Python sẽ không đủ. |
| Cùng tệp, M0018 `master.phan_cong_hanh_dong`, `ktt_hanh_dong_duoc`, `crm_g_duoc`, `crm_g_ghim_quyen` | Phân công có phạm vi loại hình, dấu thu hồi; quyền G1/G7 có cả nhánh theo vai và theo phân công. Một số hàm ghi chạy bằng kết nối chủ bảng, kiểm danh tính phiên bên trong. |
| `k2/quyen.py` | Registry `HANH_DONG`, `LOAI_VIEC_CAN`, `HANH_DONG_CRM_G`, `L11_THAO_TAC`; `kiem/duoc/pham_vi`, `kiem_l11`, `kiem_nguon`. Đây là điểm thích hợp làm adapter chung, nhưng nhiều service gọi SQL trực tiếp. |
| `m4/sql_m17.py` → `sql_duyet.py` → `sql_ke_toan_nghiem_thu.py` | `m4.quyen_du_an`: `PHU_TRACH/XEM/REVIEW`, sau thêm `DUYET/KE_TOAN`. `master.m4_duoc`, `m4_duyet_duoc`, `m4_kt_duoc` kết hợp module, dự án và có chỗ kiểm vai cũ. Không thể biến tất cả thành một tick M4 rộng. |
| `giao_dien/khung_khai_bao.py` | `VAI`, `MODULE`, `CrmKhungK2.quyen/module` còn lọc theo vai cũ; số đếm gọi S1/G1/G2 và còn giới hạn quyền xem tiền. Phải dùng quyền hiệu lực từ máy chủ để cả menu lẫn số đếm khớp ma trận. |
| `k2/crm_demo.py`, `crm_g_demo.py`, `m4_demo.py` | Seed một lần, chỉ thêm; không tự cấp lại quyền đã thu hồi. CRM-G có ca âm theo phân công/V4; M4 tách reviewer và duyệt viên. Mẫu MTQ mới không ghi đè các actor/fixture này. |

Trong các nguồn đã khảo sát chưa có vai ứng dụng Admin trong CHECK vai cũ, cũng chưa có mô hình phòng trong các bảng quyền trên. `admin_conn`/chủ CSDL là đặc quyền kỹ thuật, **không phải** danh tính Admin đăng nhập ứng dụng.

## 2. Năm vai nghiệp vụ và Admin

### 2.1. Năm vai theo cấp, không kế thừa quyền tự động

| Mã đề xuất | Tên hiển thị | Ý nghĩa để Anh tick, không phải quyền mặc nhiên |
|---|---|---|
| `THUC_HIEN_1` | Người thực hiện 1 | Tiếp nhận/lập hồ sơ của phòng. |
| `THUC_HIEN_2` | Người thực hiện 2 | Xử lý, bổ sung, kiểm theo phân công của phòng. |
| `TRUONG_PHONG` | Trưởng phòng | Kiểm/duyệt theo ô tick và hạn mức của phòng. |
| `CFO` | CFO | Quyết định tài chính trong phạm vi được cấp. Không tự có quyền mọi pháp nhân. |
| `NGUOI_XEM` | Người xem | Vai thứ năm đề xuất; mẫu DEMO chỉ tick xem. Ở dữ liệu thật, quyền vẫn theo ma trận Anh tick. |

Mã vai không chứa tên phòng. Cùng `THUC_HIEN_1` tại phòng Kinh doanh và phòng Dự án có thể có hai bộ tick khác nhau. Không có quy tắc “CFO bao gồm Trưởng phòng”; không tick = không được. Không suy quyền từ chức danh, người tạo hồ sơ hay nhãn hiển thị.

### 2.2. Bảng ánh xạ cũ → mới để Admin đối chiếu

**Chỉ là đề xuất chuyển đổi**, không chạy UPDATE, không tự sinh ma trận thật hay tự cấp vai mới từ bảng này.

| Vai/khái niệm cũ | Vai mới gợi ý | Phòng/phạm vi cần xác định |
|---|---|---|
| `BAN_HANG` | Người thực hiện 1 | Kinh doanh; giữ đúng pháp nhân, dự án/khách/hợp đồng được giao. |
| `KE_TOAN` | Người thực hiện 2 | Kế toán; tick riêng việc lập, kiểm, nối tiền, xác nhận nghiệp vụ. |
| `KE_TOAN_TRUONG` | Trưởng phòng | Kế toán; không tự nhận quyền duyệt CFO. |
| `CFO` | CFO | Từng pháp nhân; reviewer M4 cũ mang vai CFO không vì thế nhận tick duyệt. |
| `XEM` | Người xem | Phòng/pháp nhân cụ thể; actor tải mẫu có phân công cũ cần tick lập tại màn mẫu nếu muốn tiếp tục tải. |
| `DU_AN` | Người thực hiện 1 | Phòng Dự án; phạm vi dự án phải được Admin xác nhận. |
| `NHAP_JUNSKY` | Không tự ánh xạ/cấp | Luồng nhập Junsky đang cấm; không đưa vào mẫu MTQ đang hoạt động. |
| M4 `PHU_TRACH/REVIEW/DUYET/KE_TOAN/XEM` | Không ánh xạ 1:1 thành năm vai | Đây là nhiệm vụ/phạm vi dự án, không phải cấp bậc. Admin chọn cấp mới và phạm vi; REVIEW không tương đương DUYET. |
| `master.phan_cong_hanh_dong`, `duyet_loai_viec` V1…V8 | Không tạo vai thứ sáu | Đối chiếu sang ô tick tương ứng; V3/V4 là loại việc, không phải cấp người dùng. |

### 2.3. Admin

Admin là **vai quản trị hệ thống tách khỏi năm vai nghiệp vụ**, lưu trong bảng quản trị riêng tham chiếu `master.nguoi_dung`; không nới mọi allowlist cũ thành “có Admin là cho qua”. Chỉ Admin hoạt động được tạo/sửa phòng, cấp/thu hồi gán vai/phạm vi, sửa tick/hạn mức, lưu/kích hoạt phiên bản và xem toàn bộ nhật ký ma trận. Người khác chỉ xem quyền hiệu lực của chính mình.

Bootstrap Admin đầu tiên bằng thao tác quản trị tin cậy của lead trên danh tính được chỉ định, có nhật ký; không tự chọn CFO, không dùng bộ chọn vai DEMO làm đăng nhập thật. Cấp/thu hồi Admin cũng phải có nhật ký, không cho tự bỏ Admin hoạt động cuối cùng. Admin muốn duyệt nghiệp vụ phải được gán một trong năm vai và có tick/hạn mức như người dùng khác; không có đường bỏ qua ma trận.

## 3. Mô hình dữ liệu đề xuất

Tên bảng dưới đây là **thiết kế mới**, chưa tồn tại và chưa ấn định số migration. Dùng schema `master` cho cấu hình, `nhat_ky` cho sổ chỉ ghi thêm; tái sử dụng danh tính và khóa pháp nhân/dự án hiện có. Migration mới append cuối chuỗi thực tế khi triển khai; không sửa byte migration đã áp dụng, không đoán số kế tiếp.

| Bảng đề xuất | Trường chính và ràng buộc |
|---|---|
| `master.mtq_phong` | `id`, `phap_nhan_id`, `ma`, `ten`, trạng thái; UNIQUE `(phap_nhan_id, ma)` và `(id, phap_nhan_id)` để FK không lẫn pháp nhân. |
| `master.mtq_admin` | Người dùng, thời điểm/người cấp, dấu thu hồi/người thu hồi/lý do. Một cấp Admin hiện hành/người; không xóa lịch sử. Phạm vi quản trị toàn hệ thống là mặc định đề xuất. |
| `master.mtq_danh_muc_hanh_dong` | Phiên bản catalog, module/màn/hành động chuẩn và mã lệnh kỹ thuật, loại đối tượng, resolver phạm vi/tiền được whitelist trong mã. Không có danh sách vai được phép; không cho nhập biểu thức SQL/resolver tùy ý từ UI. |
| `master.mtq_phien_ban` | `id`, `phap_nhan_id`, `so_phien_ban`, `revision` bản nháp, `duoc_tao_tu`, trạng thái `NHAP/DA_CONG_BO`, phiên bản danh mục hành động, người/thời điểm tạo/công bố, lý do. UNIQUE pháp nhân × số; bản công bố bất biến. |
| `master.mtq_dong` | `id`, `phien_ban_id`, `phap_nhan_id`, `phong_id`, `vai` thuộc đúng 5 mã, **`gioi_han_vnd numeric(20,0) NULL`**. UNIQUE phiên bản × phòng × vai, CHECK hạn mức NULL hoặc ≥ 0. Đây là nơi duy nhất lưu hạn mức của một dòng, không lặp hạn mức ở mỗi module/ô. |
| `master.mtq_o` | `dong_id`, `module`, `man`, `hanh_dong`, `cho_phep boolean`; UNIQUE dòng × module × màn × hành động, FK tới danh mục hành động đã hỗ trợ. Ô thiếu = false; không wildcard “tất cả hành động tương lai”. |
| `master.mtq_gan_vai` | Người dùng × pháp nhân × phòng × một trong 5 vai; người/thời điểm cấp, dấu thu hồi/lý do. Một vai hiện hành/người/phòng/pháp nhân; một người có thể có vai khác ở phòng/pháp nhân khác. Cấp/thu hồi phải do Admin, ghi nhật ký trong cùng giao dịch. |
| `master.mtq_pham_vi` | Tham chiếu gán vai, loại phạm vi `PHAP_NHAN/DU_AN/LOAI_HINH/HOP_DONG/KHACH/NGUON`, khóa đối tượng và quan hệ cần ghim; người cấp, dấu thu hồi/lý do. Dự án/hợp đồng/khách phải đúng pháp nhân. Phạm vi loại này **không chứa quyền xem/lập/duyệt**. |
| `master.mtq_kich_hoat` | PK `phap_nhan_id`, cờ bật, con trỏ phiên bản công bố hiệu lực, `revision` chống ghi đè, người/thời điểm bật. Chưa có dòng tương đương tắt; bật mà thiếu/hỏng con trỏ thì từ chối, không quay về quyền cũ. |
| `nhat_ky.mtq_thay_doi` | Request ID, pháp nhân, bản trước/sau, dòng/ô hoặc đối tượng quản trị, giá trị cũ/mới JSONB, actor ID + login, thời điểm máy chủ, lý do, loại sự kiện (sửa tick/hạn mức/gán vai/phạm vi/Admin/công bố/bật/khôi phục). |
| `nhat_ky.mtq_tu_choi` | Request ID, actor, pháp nhân/phòng/vai, phiên bản hiệu lực, module/màn/hành động kỹ thuật/đối tượng, mã + lý do chặn, hạn mức và số tiền VND dùng so khi có. Không ghi payload hồ sơ/bí mật vào nhật ký. |

**Phiên bản và lưu:** Admin sửa bản nháp dựa trên phiên bản đang hiệu lực. Mỗi lần bấm Lưu tạo một revision nháp và diff nhật ký atomically, kể cả khi chưa công bố. Khi công bố, chốt snapshot bất biến và đổi con trỏ trong một giao dịch sau khi so `expected_revision`. Gán vai/phạm vi/Admin là dữ liệu cấp quyền hiện hành, mỗi thay đổi có revision và sự kiện riêng; không đợi công bố tick để thu hồi người dùng. Nhật ký quyết định lưu cả revision gán vai/phạm vi để tái dựng được tại thời điểm kiểm.

Một pháp nhân có một snapshot công bố bao trùm tất cả phòng, không có hai bản hiệu lực từng phần. Không bắt buộc mọi tick phải bật, nhưng mỗi phòng hoạt động phải có đủ năm dòng rõ ràng; tất cả false là cấu hình hợp lệ sau khi Admin xác nhận. Thêm màn/hành động về sau mặc định tắt và phải cập nhật danh mục có phiên bản.

**Giải phạm vi:** máy chủ suy pháp nhân/dự án/khách/hợp đồng từ đối tượng thật, không tin actor/phòng/quyền/số tiền trong body. Với tạo mới, xác thực pháp nhân và phòng theo phiên/gán vai, đối chiếu FK của đối tượng cha. Khi đối tượng dùng chung nhiều phòng, ngữ cảnh phòng phải gắn với gán vai/phạm vi được máy chủ xác minh; thiếu hoặc mơ hồ thì chặn, không tự thử phòng khác để lấy hạn mức cao nhất. Không gộp tick ở phòng A với hạn mức của phòng B. Các quy tắc này phải áp dụng giống nhau cho danh sách, chi tiết, số đếm, tải tệp và lệnh ghi.

## 4. Danh mục module/màn × hành động có căn cứ trong code

Sáu hành động chuẩn: **Xem · Lập · Sửa · Kiểm · Duyệt · Hủy**. Bảng dưới là ánh xạ thiết kế từ thao tác thực có; tên chuẩn chưa đồng nghĩa code hiện đã kiểm tách từng hành động. Đặc biệt G2/G3 và M4 SOAN hiện gom nhiều lệnh cùng một quyền, MTQ-4 phải tách theo lệnh. “—” = chưa thấy chức năng tương ứng trong phạm vi khảo sát, UI không có ô tick khả dụng; không tạo API nghiệp vụ mới cho đủ sáu cột.

### 4.1. Ô khả dụng

| Module / nhóm màn đề xuất | Xem | Lập | Sửa | Kiểm | Duyệt | Hủy |
|---|---|---|---|---|---|---|
| CRM · Tiếp nhận hợp đồng ký (luồng B) | Danh sách/chi tiết | Nộp, trích/nhận #6 | Bổ sung, mapping | Xác nhận tham số, kiểm trước, đối chiếu/trích lại | V3, V4, từ chối | — |
| CRM · Mẫu hợp đồng G1 | Mẫu/tệp/so sánh/xem thử | Tải mẫu | Ánh xạ, gửi kiểm | Kiểm, trả lại | Duyệt V4, từ chối | — |
| CRM · Bộ chuẩn dự án G7 | Danh sách/bộ chuẩn | Lập | Gửi duyệt; áp dụng tiến độ hiện có | — | Duyệt V4 (đường cũ còn có) | — |
| CRM · Báo giá G2 | Danh sách/chi tiết/in/xuất | Tạo báo giá, xem trước tính toán | Lưu revision | — | — | Hủy báo giá |
| CRM · Soạn/Ký kết G3–G4 | Bản soạn/tệp/bản ký | Chuyển báo giá thành bản soạn, ghi nhận ký | Lưu bản soạn | — | — | — |
| CRM · Kiểm hợp đồng ký G5–G6A | Inbox/chi tiết/tệp/đối chiếu | — | Lưu checklist, bổ sung | Check, xử lý lệch, trả lại, chạy/đối soát G5 | Kích hoạt Hiệu lực | — |
| CRM · Dự án đang bán/mốc/phí | Danh sách/chi tiết/lịch sử/ảnh chụp | Bật bán, tạo lô/mốc | Cập nhật, phí, lô/mốc, ngừng/mở bán | — | — | — |
| CRM · Tỷ giá mặc định | Đọc tỷ giá | — | Cập nhật tỷ giá | — | — | — |
| CRM · Báo cáo & file soát | Tạo/tải file soát | — | — | — | — | — |
| M1 · Tiền về / tiền đi (đường CRM đã nối) | Xem tiền/fact thu | Nhận sao kê DEMO | Nối tiền | — | — | Gỡ liên kết tiền |
| M2 · Mua hàng/Hóa đơn mua vào | Danh sách/chi tiết/nguồn | Nhận nguồn/tải hóa đơn | — | — | Mapping công ty/dòng, chọn nguồn, định tuyến (V4 hiện tại) | Hủy hàng đợi tải của mình |
| M5 · Kho & số lượng | Phiếu/nguồn/kiểm kê/tồn/file soát | Nhận nguồn | — | — | Mapping V4, xem xét nguồn V8 | — |
| M2 + M5 · Liên kết số lượng L11 | Tổng quan/bằng chứng/xem trước/file | Xác nhận liên kết | — | — | Xác nhận bằng chứng/mã hóa theo nhánh CFO hiện có | Hủy liên kết/bằng chứng |
| M4 · Nghiệm thu & chi phí dự án / Hồ sơ, tham số, phụ lục, BOQ, đợt | Hợp đồng/đợt/tệp/mẫu | Tạo hợp đồng/đợt, nhận master/tải tệp, thêm phụ lục/nhập BOQ | Gắn tệp/đối tác, sửa tham số/đợt, khai phụ lục, trích tham số, nộp | Xác nhận tham số | — | Hủy phụ lục |
| M4 · Review đợt 02A | Run/tệp kết quả | — | Ghép BOQ | Chạy/chạy lại review | — | — |
| M4 · Chứng từ 02B | Bộ chứng từ/kết quả | — | Sửa/ghép | Chạy/chạy lại kiểm chứng từ | — | — |
| M4 · Duyệt hồ sơ đợt 02C | Hồ sơ/PDF theo phạm vi | Tạo phiên bản sau | Nộp phiên bản | Ghi kết luận | Chấp thuận | — |
| M4 · Kế toán nghiệm thu 03A | Inbox/phong bì/PDF | — | Lưu ghi nhận | Xác nhận kế toán | — | — |
| M4/M2 · Ghi nhận đối chiếu 03B dùng chung | Đợt/lịch sử/còn thiếu | — | Lưu đối chiếu | Xác nhận | — | — |
| M4 · Request nháp 04 | Trạng thái/lịch sử | Tạo nháp | — | Đối soát | — | — |

**Cách nhóm cần nói rõ tại cổng A:** từ chối quyết định nằm trong Duyệt, trả lại khi kiểm nằm trong Kiểm, ngừng bán nằm trong Sửa, hủy liên kết là Hủy (ghi sự kiện đảo, không DELETE). In/xuất/tải file soát thuộc Xem nhưng vẫn kiểm phạm vi và nhật ký hiện có. “Ký kết” là ghi nhận bản ký ở Lập, không phải ký số hoặc quyền đại diện pháp lý mới. Kích hoạt Hiệu lực G6A đưa vào Duyệt để không lách hạn mức bằng nút tên khác; không tự sửa nghiệp vụ G6A thành phải có CFO.

G7 có cả đường duyệt cũ và `crm_g_chuan_ap_dung` áp dụng ngay cho bán hàng theo QD-07 trong `sql_crm_du_an_ban.py`; liệt kê cả hai vì code đang có, không tự đưa CFO trở lại luồng áp dụng ngay. Nếu sau này áp dụng tiến độ được xác định là quyết định tài chính phải kiểm hạn mức, phải đổi phân loại trong catalog và review trước khi mở.

### 4.2. Hàm/route đang kiểm quyền — điểm nối cụ thể

| Nhóm | Hàm/route thực có và cổng đang dùng |
|---|---|
| CRM luồng B, M1, file soát | `k2/crm.py`: `trich_tu_docx`, `nhan_ket_qua_6` → `NOP_HOP_DONG`; `bo_sung_ho_so` → `BO_SUNG_HO_SO`; `_trich_lai` → `DOI_CHIEU_TRICH_LAI`; `cap_nhat_mapping` → `MAPPING`; `xac_nhan_tham_so/kiem_truoc` → `KIEM_TRUOC`; `duyet/duyet_v4/tu_choi` → `DUYET/DUYET_V4`; `kiem_nhan_tien`, `lien_ket`, `go_lien_ket`, `xuat_file_soat/tep_file_soat` → `quyen.kiem`. `danh_sach` dùng `pham_vi(XEM/XEM_TIEN)`. `giao_dien/server.py:_crm_action`: POST `/api/crm/{mau,bo-sung,mapping,xac-nhan-tham-so,kiem,duyet,duyet-v4,tu-choi,m1-sao-ke,lien-ket,go-lien-ket,file-soat}`; `/api/crm/trich6`, `/api/crm/nhan` tách riêng. |
| M1 đường nhận | `server.py:crm_m1_sao_ke` gọi `CrmK2.kiem_nhan_tien` trước `m1_demo.nhan_sao_ke/chieu_sang_k2`, `fact_hop_dong_m1` kiểm CRM XEM. Không có căn cứ để khẳng định toàn bộ M1 SQLite đã có cùng cổng hành động; mọi đường Store/ingest khác phải được khóa hoặc nối trước khi bật PN có sử dụng đường đó. |
| CRM G1/G7 | `k2/crm_mau.py:CrmMauK2` (`danh_sach`, `chi_tiet`, `luu_anh_xa`, `_don_gian`, `lap_bo_chuan`, `danh_sach_bo_chuan`) gọi SQL `master.crm_g_mau_doc`, `crm_g_duoc`, `crm_g_dich`, `crm_g_chuan_doc_duoc`, `ktt_hanh_dong_duoc`; registry `HANH_DONG_CRM_G` nêu mã từng lệnh. `giao_dien/crm_g.py:dieu_huong/_lenh`: GET `/api/crm/mau…`, `/api/crm/bo-chuan`; POST `/api/crm/mau/{tai,anh-xa,gui-kiem,kiem,tra-lai,duyet,tu-choi,xem-thu}`, `/api/crm/bo-chuan/{lap,gui-duyet,duyet}`. |
| CRM G2/G3/G4 | `k2/crm_giao_ket.py:CrmGiaoKetK2` dùng `master.crm_gk_duoc/crm_gk_dich` cho nhóm `CRM_BAO_GIA/CRM_SOAN`; `_quyen_ty_gia/ty_gia_mac_dinh/sua_ty_gia_mac_dinh` trong service kiểm quyền cấu hình tỷ giá chung; `k2/sql_crm_bg1c.py` thay phép chiếu lịch ký dùng tỷ giá đã ghim; `crm_ky_pham_vi_hd`, `crm_ky_pham_vi_duoc`, `crm_ky_doc_duoc`, `crm_ky_dich` trong `pg_migrations.py` kiểm ký/đọc tách riêng, phạm vi hợp đồng/khách/dự án và phân công `CRM_KY_KET/CRM_KY_DOC`. `k2/crm_ky_ket.py:kiem_quyen/tep`; route GET `/api/crm/{bao-gia,soan/…}`, `/api/crm/giao-ket/{ky/…,ban-ky/…/tep,tep/…/docx}`; POST `/api/crm/bao-gia/{luu,huy,chuyen,in,ty-gia-mac-dinh}`, `/api/crm/soan/{luu,xuat}`, `/api/crm/giao-ket/ky-ket`. |
| CRM G5/G6A | `k2/sql_crm_kiem_hd.py:master.crm_kiem_pham_vi_duoc/crm_kiem_dich` kiểm vai KT/KTT, `CRM_HD_KIEM`, phạm vi hiện hành, người ký khác người kiểm/kích hoạt. `k2/crm_kiem_hd.py` gọi `crm_kiem_luu/chay_check/xu_ly_lech/bo_sung/tra_lai/hieu_luc`; `k2/crm_doi_chieu.py`, `sql_crm_doi_chieu.py` tái dùng cổng đích/phạm vi cho G5. GET `/api/crm/giao-ket/kiem…`, `/doi-chieu/{ky_id}`; POST `/api/crm/giao-ket/kiem/{luu,check,xu-ly-lech,bo-sung,tra-lai,hieu-luc,tim-junsky}`, `/doi-chieu/{chay,doi-soat}` (tiền tố đầy đủ `/api/crm/giao-ket`). `tim-junsky` chỉ tra mã có sẵn, không gọi Junsky. |
| CRM dự án/S1/khung | `k2/sql_crm_du_an_ban.py:crm_da_duoc_doc/ghi`, `crm_da_vao`; `sql_crm_du_an_moc.py:crm_da_moc_ghi` dùng lại preflight; `k2/crm_du_an_ban.py:bat_ban/cap_nhat/sua_phi/ghi_lo/moc_ghi/_doi_trang_thai/ap_dung_tien_do`. GET `/api/crm/du-an-ban…`; POST `/api/crm/du-an-ban/{bat-ban,cap-nhat,phi,lo,moc,ngung-ban,mo-ban-lai,tien-do}`. `crm_s1.py` có SQL vai/phạm vi ký và quyền xem tiền riêng; GET `/api/crm/hop-dong`. `CrmKhungK2.quyen/module`, GET `/api/khung/module/crm` phải nối cùng quyền. |
| M2 | `k2/hoa_don.py:HoaDonK2.danh_sach/chi_tiet` → `M2_READ`; `mapping_company/mapping_line` → `M2_MAP`; `xem_xet_nguon` → `M2_SOURCE_REVIEW`; `route` → `M2_ROUTE`; `nhan` → `kiem_nguon(INTAKE)`. SQL `kho.m2_mapping_cong_ty/mapping_dong/xem_xet_nguon/route` trong `pg_migrations.py` còn kiểm ở CSDL. `server.py:_m2_action`: POST `/api/m2/{nhan,mapping,mapping-line,nguon/kiem-lai,route}`, GET `/api/m2…`. |
| M2 tải hóa đơn | `m2/tai_hoa_don/dieu_phoi.py:_guard/_quyet_dinh`, cổng năng lực INTAKE + READ_SOURCE, mapping công ty→PN, `M2_READ`, `ktt_duoc`; `giao_dien/m2_tai_hoa_don.py:dieu_huong`: `/api/m2/tai-hoa-don/{bat-dau,tai-tat-ca,nhan,hang-doi,huy-hang-doi,trang-thai,su-kien,doi-soat,manifest,mo-thu-muc}`. Hủy hàng đợi vẫn cần đúng chủ hàng đợi. MTQ chỉ test mock, không kích hoạt bộ tải thật. |
| M5/L11 | `k2/kho_so_luong.py:KhoSoLuongK2`: `danh_sach/chi_tiet/kiem_ke` → `M5_READ`; `cap_nhat_mapping` → `M5_MAP_V4`; `kiem_lai_nguon` → `M5_SOURCE_REVIEW_V8`; `xuat_file_soat/tep_file_soat` → `M5_FILE_SOAT` hoặc `kiem_l11(FILE)`; `nhan/l11_nhan_bang_chung` → năng lực nguồn. `lien_ket`, `l11_xac_nhan_bang_chung/l11_huy_bang_chung/l11_ma_hoa` gọi SQL; `kho.l11_quyen_noi_bo` đòi cả M2+M5, LINK cần V2, CFO cần V4. `server.py:_m5_action/_l11_action`: `/api/m5/lien-ket/{xem-truoc,xac-nhan,huy}`, `/api/m5/l11/…`, `/api/m5/{mapping,nguon/kiem-lai,xuat-file-soat}`. |
| M4 hồ sơ | `k2/xay_dung.py:XayDungK2` gọi `master.m4_duoc`, đoạn guard `_SOAN` cùng các SQL command trong `m4/sql_m17.py`. `giao_dien/m4.py:_lenh/dieu_huong`: POST `/api/m4/tep`, `/hop-dong/{tao,nhan-master,gan-doi-tac,gan-tep,trich}`, `/tham-so/{sua,xac-nhan}`, `/phu-luc/{khai,them,huy}`, `/boq/{xem,nhap}`, `/dot/{tao,sua,gan-tep,nop}` (các hậu tố sau đều dưới `/api/m4`). GET `/api/m4/{hop-dong,dot,tep}/{id}` và bộ chọn master kiểm phạm vi soạn/đọc. |
| M4 02A/02B | `m4/sql_review.py:m4.review_quyen/review_kiem/review_doc_duoc` (bản sửa M20 có hiệu lực); `sql_chung_tu.py:m4.chung_tu_quyen/chung_tu_doc_dot/chung_tu_doc_duoc`. SOAN trong dự án hoặc REVIEW trên đợt đã nộp, còn ràng buộc loại tệp/đợt. POST `/api/m4/review/{chay,chay-lai,ghep}`, `/api/m4/chung-tu/{chay,chay-lai,sua,ghep}`; GET các run và tệp con. |
| M4 02C/03A | `m4/sql_duyet.py:master.m4_duyet_duoc`, `m4.duyet_doc_dot/duyet_quyen/duyet_kiem/duyet_khoa`; `m4/duyet_dot.py:DuyetDot._thay/_lenh` kiểm lại trước biên nhận và lệnh. POST `/api/m4/duyet/{ket-luan,chap-thuan,phien-ban,phien-ban/nop,pdf}`. `sql_ke_toan_nghiem_thu.py:master.m4_kt_duoc`, `m4.kt_kiem/kt_doc_cho`; `ke_toan_nghiem_thu.py:luu/xac_nhan`, POST `/api/m4/ke-toan/{luu,xac-nhan}`; GET inbox/phong bì/PDF. |
| M4/M2 03B | `k2/sql_ghi_nhan_chung.py:kho._dc_m2_doc/_dc_kt_toan_cuc/_dc_quyen/_dc_doc_duoc` và `sql_ghi_nhan_so_tien.py`; `k2/ghi_nhan_chung.py:GhiNhanChungK2.luu_doi_chieu`; `m4/ghi_nhan_nghiem_thu.py:NguonNghiemThu`. `/api/m4/doi-chieu/{dot,lich-su,con-thieu}/{id}`, POST `/api/m4/doi-chieu/{xem,luu,xac-nhan}`; kiểm từng nguồn NT/hóa đơn, không chỉ PN ở màn hình. |
| M4 Request nháp | `m4/sql_request_nhap.py:m4.request_quyen/request_kiem` dùng quyền đọc/tải PDF đợt và mapping nhân viên→Request hiện hành; `m4/request_nhap.py:_quyen/_lenh`, `giao_dien/m4_request.py:dieu_huong`: GET `/api/m4-request`, POST `/api/m4-request/{tao,doi-soat}`. Tạo nháp không phải quyền duyệt thanh toán; vẫn giữ cổng cấu hình tích hợp, chỉ dùng mock/DEMO. |

### 4.3. Giới hạn kiểm kê và điều kiện bao phủ

M9 có `M9_READ/INTAKE/STAGE/MAP_APPROVE/CHECK/APPROVE/APPROVE_V4/MATCH/MATCH_M1/EXPORT` trong `quyen.py` và `vay.py`, nhưng giữ mờ “Tạm dừng”, không seed/tick mở. M7 xuất hiện trong RLS nhân viên; không vì có tên RLS mà khẳng định đã có đủ sáu thao tác màn hình. Các module/màn chưa có command được kiểm chứng và tám màn review M4 đang chép theo CD-011 chưa tự trở thành ô khả dụng.

Danh sách trên là kiểm kê mã tĩnh tại worktree, **không phải chứng nhận đã chạy từng route trên PostgreSQL**. Trước khi bật, lead rà thêm dispatcher chung/legacy (`giao_dien/operations.py`, `server.py`, Store/ingest, job nền) và mọi đường ghi/tải tệp đang được cung cấp cho pháp nhân đó. Đường còn chưa nối phải từ chối ở chế độ ma trận, hoặc khiến kiểm tra sẵn sàng không cho bật; không cho phép rơi về quyền cũ. Chức năng giao diện có mà chưa có kiểm máy chủ là khoảng trống cần sửa, không phải quyền sẵn có để kế thừa.

## 5. Một cổng quyết định và cách bật an toàn

### 5.1. Hợp đồng cổng chung

Đề xuất mở rộng `k2/quyen.py` làm adapter máy chủ: `kiem_tham_quyen(conn, hanh_dong_ky_thuat, doi_tuong, ngu_canh_tin_cay)` trả quyết định gồm nguồn `CU/MA_TRAN`, bản quyền/revision, gán vai/phạm vi, ô áp dụng, hạn mức/số tiền, mã và lý do. Không dùng dictionary danh tính nạp từ lần mở màn làm thẩm quyền cho lần ghi sau.

Lõi quyết định SQL dùng chung đề xuất `master.mtq_quyet_dinh(...)`; Python và các hàm SQL/RLS gọi cùng lõi trong giao dịch có ID + login của phiên. Catalog whitelist ánh xạ `(hành động kỹ thuật, loại đối tượng)` sang `(module, màn, hành động chuẩn, cách lấy phạm vi, loại tiền)`. Catalog không chứa allowlist vai. Quyền không nhận từ trình duyệt, header tự khai hay actor do job payload truyền tùy ý.

Trình tự: **danh tính hoạt động → suy đối tượng/pháp nhân/phạm vi tin cậy → trạng thái bật → quyền → hạn mức → điều kiện nghiệp vụ → side effect**. Kiểm lại quyền trước trả replay, trước đọc blob và trước công bố kết quả job/render. Khóa dòng kích hoạt, gán vai/phạm vi liên quan theo thứ tự cố định cùng giao dịch nghiệp vụ; thao tác công bố/thu hồi dùng khóa xung đột tương ứng. Việc bắt đầu sau khi thu hồi commit phải bị chặn; giao dịch đã giữ khóa được hoàn tất theo revision đã ghim, được thể hiện rõ trong nhật ký.

| Trạng thái PN | Hành vi bắt buộc |
|---|---|
| Chưa bật/không có cấu hình | Adapter gọi đúng đường cũ; không đổi allowlist/V3/V4/assignment hiện có. |
| Đã bật, đủ cấu hình | Chỉ đọc gán vai/phạm vi và snapshot MTQ; không `legacy OR matrix`, cũng không `legacy AND matrix`. |
| Đã bật nhưng lỗi/thiếu ô/thiếu vai/không rõ đối tượng | Từ chối có mã và nhật ký; tuyệt đối không fallback. |

**Nối RLS/trigger:** `ktt_duoc` khi bật phải suy quyền truy cập module từ MTQ (có ít nhất một ô hợp lệ) để không chặn các lệnh chỉ có quyền ghi; quyền Xem từng bảng/đối tượng vẫn kiểm ô Xem đúng màn. `ktt_pn_cho_phep` suy từ gán vai/phạm vi MTQ. Không sửa `ktt_co_vai(vai[], loai_viec)` thành hàm đoán hành động: chữ ký đó thiếu module/màn/đối tượng/tiền. Từng caller và nhánh SQL inline phải được thay bằng cổng có hành động tường minh; khi PN bật không còn kiểm vai cũ/V3/V4 để quyết quyền. Trigger/RLS vẫn giữ các ràng buộc dữ liệu, trạng thái, tính bất biến và tách nhiệm.

**Phạm vi cũ sau bật:** không tiếp tục dùng `m4.quyen_du_an.vai`, `phan_cong_hanh_dong` hay vai cũ làm nguồn chức năng thứ hai. Admin xác nhận gán vai/phạm vi MTQ mới, có thể dùng màn đối chiếu để tham khảo các phạm vi hẹp cũ. Các quan hệ ký/kiểm đúng HĐ/dự án/khách và snapshot còn đúng phải được bảo toàn bằng phạm vi MTQ có khóa tham chiếu tương ứng; không làm rộng thành toàn PN. Xem bản ký, soạn, review và duyệt là các ô/màn khác nhau, không suy từ nhau. Kiểm người lập/người ký khác người kiểm, bước kiểm trước duyệt, hồ sơ đã nộp, revision/hash/căn cứ còn khớp vẫn là điều kiện nghiệp vụ.

**Nguồn trước pháp nhân (M2/M5/L11):** `ktt_nguon_duoc`, `ktt_nguon_co_nang_luc` và raw metadata/bytes là điểm bắt buộc của MTQ-4. Cần phạm vi nguồn MTQ được Admin cấp tường minh theo instance + profile ref/SHA + phạm vi công ty nguồn → PN/phòng; hành động INTAKE→Lập, READ_SOURCE→Xem, SOURCE_MAP→Duyệt tại nhóm nguồn. Không chỉ giữ capability cũ rồi tuyên bố nguồn duy nhất. Nguồn gộp nhiều PN phải được tách và kiểm đủ từng PN liên quan trước trả dữ liệu; không rõ PN/phạm vi thì chặn khi dùng ma trận, không suy từ một PN bất kỳ mà actor có quyền. Khi còn đường raw/capture không giải được phạm vi, chưa cho bật PN liên quan. Điều kiện profile/instance hợp lệ và bí mật kết nối vẫn được giữ như điều kiện kỹ thuật.

**Liên module:** L11 đòi ô phù hợp trên cả M2 và M5 của cùng phạm vi; 03B kiểm mọi nguồn NT/hóa đơn, không dùng một tick M4 để đọc M2. Nếu một giao dịch liên quan nhiều PN, mỗi PN dùng đúng chế độ của mình, không lấy quyền PN tắt bù PN đã bật; không đủ bất kỳ phía nào thì chặn toàn bộ. Tích hợp Request vẫn cần mapping tài khoản, cấu hình cho phép và hồ sơ hợp lệ, tick không tự bật dịch vụ ngoài.

**Cấu hình chung không có PN:** tỷ giá mặc định trong `CrmGiaoKetK2.sua_ty_gia_mac_dinh` đang ghi `master.cau_hinh.phap_nhan_id = NULL`, quyền cũ chỉ cần KT/KTT có CRM ở ít nhất một PN. Đây là trường hợp không thể chọn PN tùy ý rồi cấp quyền. Khi chưa PN liên quan nào bật, giữ hành vi cũ. Khi có PN đã bật, lệnh sửa chung phải giải tập PN chịu tác động từ registry máy chủ và kiểm Sửa cấu hình ở tất cả PN đó theo chế độ tương ứng; thiếu quyền hoặc không xác định được tập ảnh hưởng thì chặn. Không lấy một PN còn tắt làm đường sửa cấu hình ảnh hưởng PN đã bật. Mặc định này chặt hơn và cần thể hiện trong cổng A; chưa tách tỷ giá chung thành tỷ giá riêng từng PN trong MTQ.

**Mức đọc nhạy cảm:** không gộp ô Xem hồ sơ với quyền tải PDF thanh toán/bản ký/raw nguồn hoặc xem tiền. Catalog và UI phải có nhóm màn con tương ứng (ví dụ M4 · PDF hồ sơ đã duyệt, CRM · Bản ký, M1 · Xem tiền, M2/M5 · Nguồn thô), mỗi nhóm chỉ có các hành động thực có. Điều kiện đợt đã nộp/có PDF seal và phạm vi tài liệu vẫn giữ; không dùng vai dự án cũ để cấp quyền tải sau bật. Cột tổng quan ở mục 4.1 được bung thành các nhóm con này khi hiện bảng tick, không tự tick kèm Xem hồ sơ. Tránh việc tick xem rộng vô tình cấp tải tài liệu mà người đó trước đây chỉ được thấy metadata.

### 5.2. Giới hạn tiền và lý do chặn

- Một hạn mức/dòng, áp cho **Duyệt** tại mọi màn có duyệt. Chưa áp cho Lập trong MTQ đầu; chỉ mở thêm sau khi có căn cứ module và được ghi rõ ở cổng A. `NULL` = không giới hạn, `0` = chỉ giá trị bằng 0; tiền âm không được dùng để né hạn mức.
- Lõi lấy tiền từ phiên bản nghiệp vụ đã khóa: CRM duyệt V3/kích hoạt G6A dùng **tổng giá trị hợp đồng của phiên bản quyết định**, không lấy một đợt nhỏ; M4 chấp thuận dùng **số xin thanh toán của kết luận đang chấp thuận** (`so_xin_thanh_toan`), không dùng số client tự khai lại hoặc số net tự tính khác. Duyệt mapping/mẫu/bộ chuẩn không mang một giao dịch tiền cụ thể là loại `KHONG_AP_DUNG`, phải khai tường minh trong catalog, không đồng nhất với tiền bị thiếu. Nhánh nào phát sinh giao dịch có tiền thì phải khai resolver tương ứng trước khi được mở.
- Đối tượng tiền tệ phải có số tiền hợp lệ dù hạn mức không giới hạn. VND so chính xác bằng numeric/Decimal; USD và ngoại tệ phải có tỷ giá quy đổi được ghim vào phiên bản/căn cứ đáng tin cậy, lưu số tiền gốc, tỷ giá và VND dùng so. Không lấy tỷ giá hiện tại trên màn làm thay đổi quyết định quá khứ, không gọi dịch vụ tỷ giá. Chưa có resolver/tỷ giá phù hợp → `MTQ_THIEU_CO_SO_TIEN`, chặn. So sánh chính xác trước làm tròn hiển thị.
- `so_tien_vnd > gioi_han_vnd` → `MTQ_VUOT_HAN_MUC`; bằng hạn mức được qua. Không tự tách chứng từ, cộng hạn mức nhiều vai, nâng quyền CFO/Admin hay chuyển sang quyền cũ. Kiểm lại khi retry/job công bố và khi tiền/revision thay đổi.
- Lý do nghiệp vụ trả cho người có quyền thấy đối tượng, ví dụ: “Không thể duyệt: giá trị 600.000.000 VND vượt giới hạn 500.000.000 VND của Trưởng phòng”. Ngoài phạm vi trả 404/lý do chung theo hợp đồng hiện có, không lộ số tiền. Các số trên chỉ là ví dụ giả.

**Nhật ký chặn phải sống qua rollback:** không INSERT rồi RAISE trong cùng giao dịch và cho rằng đã lưu. HTTP/service bắt mã từ chối, rollback giao dịch nghiệp vụ, ghi sự kiện vào `nhat_ky.mtq_tu_choi` bằng giao dịch máy chủ riêng trước khi trả lỗi; job nền đi cùng đường. Sự kiện lấy từ quyết định tin cậy, không từ body client; request ID nối với lần thử. Lỗi ghi nhật ký không được chuyển thành cho phép; trả lỗi hệ thống và ghi kênh sự cố máy chủ hiện có. SQL boolean dùng cho lọc danh sách không ghi một sự kiện cho mỗi hàng bị ẩn; lệnh duyệt trực tiếp phải có wrapper trả/thu quyết định để ghi chặn bền vững. Không mở quyền gọi trực tiếp các hàm ghi chủ bảng cho vai app thông thường để né wrapper.

### 5.3. Bật theo pháp nhân

1. Deploy SQL/service/UI và toàn bộ adapter cần dùng trong trạng thái **tắt**; quyền cũ giữ nguyên. Không có auto-seed ma trận thật trong migration/startup.
2. Admin khai phòng, gán vai/phạm vi và tự tick, nhập hạn mức; đối chiếu quyền trước/sau trên danh tính, đối tượng DEMO tương ứng. Không tự chép quyền cũ thành ma trận thật. Lưu nháp chưa đổi quyền hiệu lực.
3. Máy chủ kiểm sẵn sàng: snapshot hợp lệ, Admin còn hoạt động, đủ gán vai/phạm vi, mọi route/job/RLS/SQL/raw/legacy liên quan đã nối cùng catalog; module chưa nối bị khóa rõ. Đặc biệt không bật chỉ CRM nếu M1/M2/M4 cùng PN vẫn có đường bỏ qua. CSDL M4 riêng chưa được nâng cơ chế thì chưa bật tại đó.
4. Admin công bố và bật đúng PN bằng `expected_revision`, trong một giao dịch ghi con trỏ + nhật ký; snapshot rỗng toàn false có cảnh báo/xác nhận riêng để tránh khóa việc ngoài ý muốn. Chỉ Admin đã đăng nhập và có token hợp lệ được làm; không mở endpoint không xác thực cho bootstrap.
5. Các lần kiểm mới đọc revision hiệu lực, làm mất hiệu lực cache menu/quyền; job nền phải kiểm lại. Thử ca âm gọi API trực tiếp, PN khác, dự án khác, vai cũ cho phép nhưng tick tắt, vai cũ cấm nhưng tick bật, vượt tiền và thu hồi giữa hai pha.
6. Sau bật, sửa bằng snapshot mới. Khôi phục mặc định là **công bố bản MTQ trước đó như phiên bản mới**, có audit; không tự tắt để khôi phục quyền cũ rộng hơn. Tắt chế độ sau bật chỉ là thao tác vận hành Admin có lý do, màn xác nhận rõ quyền cũ sẽ quay lại và nhật ký riêng, không fallback do lỗi.

## 6. Màn hình và HTTP đề xuất

Một màn “Ma trận thẩm quyền” trong quản trị: chọn **pháp nhân → phòng**, trạng thái Chưa bật/Đang dùng, số phiên bản, lần sửa/người sửa. Bảng có năm dòng; ghim cột Vai và **một cột Giới hạn số tiền (VND)**; nhóm cột theo module rồi màn, mỗi nhóm sáu hành động, gấp/mở được. Ô chưa có chức năng hiện “—” và không tick. Tiền canh phải, dấu chấm phân nhóm; để trống hiện “Không giới hạn”, 0 hiển thị “0 VND”. Gấp nhóm không làm mất tick, không có nút “tick hết mọi module tương lai”.

Chỉ Admin có Lưu nháp/Công bố/Bật/Khôi phục, giao diện gán vai/phạm vi và nhật ký chi tiết. Lưu cho xem diff ô và hạn mức cũ→mới, cần lý do, báo xung đột khi revision cũ; không ghi đè thay đổi Admin khác. Mọi lần lưu nháp/công bố/gán/thu hồi đều có audit. Mẫu thật mở trống; nút mẫu chỉ xuất hiện tại DEMO và không tự áp khi mở lại.

Người không phải Admin chỉ mở “Quyền của tôi”: các dòng/phòng của chính mình, phiên bản/hạn mức đang áp và lý do không được thao tác; không tải toàn ma trận về rồi ẩn bằng JavaScript. Menu/nút/số đếm của `khung_khai_bao.py` dùng quyền hiệu lực, đổi vai DEMO phải nạp lại; quyền máy chủ vẫn kiểm tại từng thao tác.

| API mới dự kiến, chưa có trong code | Quy tắc |
|---|---|
| GET `/api/tham-quyen/cua-toi` | Phiên hiện hành; chỉ quyền/phạm vi của chính mình. |
| GET `/api/tham-quyen/ma-tran`, `/nhat-ky` | Chỉ Admin; lọc PN/phòng/phiên bản hợp lệ phía máy chủ. |
| POST `/api/tham-quyen/{luu-nhap,cong-bo,kich-hoat,khoi-phuc}` | Chỉ Admin, token theo server hiện có, `expected_revision`, lý do, request key; máy chủ dựng actor và diff. |
| POST `/api/tham-quyen/{phong,gan-vai,pham-vi,admin}` | Chỉ Admin; cấp/thu hồi tường minh, không DELETE, bảo vệ Admin cuối cùng. |

## 7. Chia lát triển khai và kiểm thử

Đây là **phân rã thiết kế theo yêu cầu MTQ-0**, không phải handoff mới. Lead khóa file dùng chung và chốt danh sách khi giao. Mỗi dòng dưới ≤ 3 tệp sửa (tính cả test); nhóm MTQ-4 phải tách nhiều lát vì không thể nối an toàn toàn hệ thống trong 3–5 tệp. Tệp mới chỉ là dự kiến cho các lát sau; MTQ-0 chỉ tạo tài liệu này.

| Lát | Tệp dự kiến (gốc `src/kho_tri_thuc/`, test ở `tests/`) | Kết quả và kiểm bắt buộc |
|---|---|---|
| MTQ-1 · SQL/migration | Mới `k2/sql_ma_tran_tham_quyen.py`; `ha_tang/pg_migrations.py`; mới `tests/test_mtq_sql.py` | Bảng/constraint, danh mục, lõi quyết định, ghi cấu hình/audit, bootstrap tin cậy; mặc định tắt. Test identity, khác PN/phòng, Admin, immutable/audit, version CAS. PG thật do lead chạy ngoài sandbox. |
| MTQ-2 · Dịch vụ/HTTP | Mới `k2/ma_tran_tham_quyen.py`; mới `giao_dien/ma_tran_tham_quyen.py`; mới `tests/test_mtq_http.py` | CRUD có kiểm Admin, của tôi, công bố/bật có readiness, ghi chặn sau rollback. Test giả mạo actor, non-Admin, CSRF/token, stale revision, idempotency và audit failure. Chưa nối dispatcher/chưa cho bật. |
| MTQ-3a · Bảng tick | Mới `giao_dien/assets/ma_tran_tham_quyen.js`; `giao_dien/assets/style.css`; mới `tests/test_mtq_ui.py` | Bảng 5 vai, gấp/mở, 1 cột VND, diff, chỉ đọc, xung đột. Không gọi API ngoài. |
| MTQ-3b · Nối màn/route | `giao_dien/server.py`; `giao_dien/assets/app.js`; `giao_dien/assets/index.html` | Nối HTTP/static/menu vào khung hiện có; kiểm cổng A trên DEMO bởi lead. Không tự bật PN từ UI mới. |
| MTQ-4a · Adapter chung, CRM luồng B/M1 | `k2/quyen.py`; `k2/crm.py`; mới `tests/test_mtq_crm.py` | Nhánh tắt giữ cũ; bật bỏ allowlist cũ, hạn mức V3/V4, nối/gỡ tiền, tải tệp. |
| MTQ-4b · SQL CRM cốt lõi | Mới `k2/sql_mtq_crm.py`; `ha_tang/pg_migrations.py`; mới `tests/test_mtq_crm_sql.py` | Append thay caller/trigger/RLS G1/G2/G3/G4, phạm vi, replay/ghim quyền và tiền; không sửa migration cũ. |
| MTQ-4c · Đọc/khung | `giao_dien/khung_khai_bao.py`; `k2/crm_s1.py`; mới `tests/test_mtq_khung.py` | Menu/số đếm/danh sách và quyền xem tiền dùng cùng snapshot; không lộ dữ liệu chéo PN/khách. |
| MTQ-4d · CRM mẫu/giao kết | `k2/crm_mau.py`; `k2/crm_giao_ket.py`; mới `tests/test_mtq_giao_ket.py` | Không còn lọc role cũ ở service; tách đọc/lập/sửa/hủy/xuất theo catalog; tỷ giá. |
| MTQ-4e · SQL CRM G5/G6/dự án | Mới `k2/sql_mtq_crm_kiem.py`; `ha_tang/pg_migrations.py`; mới `tests/test_mtq_crm_kiem_sql.py` | Append thay quyền trong `sql_crm_kiem_hd`, `sql_crm_doi_chieu`, `sql_crm_du_an_ban/moc`, `sql_crm_bg1c`; giữ tách nhiệm, snapshot và luồng QD-07. |
| MTQ-4f · SQL M4 | Mới `m4/sql_mtq.py`; `ha_tang/pg_migrations.py`; mới `tests/test_mtq_m4_sql.py` | Append thay guard/RLS trong M17/20/22/24/26/27/master; bỏ nguồn quyền vai dự án cũ khi bật, giữ phạm vi/đã nộp. |
| MTQ-4g · M4 hồ sơ/review | `k2/xay_dung.py`; `m4/duyet_dot.py`; mới `tests/test_mtq_m4.py` | Quyền theo từng lệnh; hạn mức chấp thuận; job/render/tải PDF kiểm lại, ca reviewer không duyệt. |
| MTQ-4h · M4 kế toán/Request | `m4/ke_toan_nghiem_thu.py`; `m4/request_nhap.py`; mới `tests/test_mtq_m4_ke_toan.py` | Xác nhận KT theo tick; không có đường tải căn cứ riêng trái CD-010.7; Request mock, giữ cổng tích hợp. |
| MTQ-4i · SQL M2/M5/L11/nguồn/03B | Mới `k2/sql_mtq_lien_module.py`; `ha_tang/pg_migrations.py`; mới `tests/test_mtq_lien_module_sql.py` | Append thay kiểm quyền nguồn, mapping, V2/V4/V8, BOTH M2+M5, mọi nguồn 03B và SQL tiền; không để capability/role cũ cấp quyền. |
| MTQ-4j · M2/M5 service | `k2/hoa_don.py`; `k2/kho_so_luong.py`; mới `tests/test_mtq_nguon.py` | Danh sách/chi tiết/raw, intake, hành động và file không còn dùng quyền cũ khi bật. |
| MTQ-4k · Bộ tải M2 | `m2/tai_hoa_don/dieu_phoi.py`; `giao_dien/m2_tai_hoa_don.py`; mới `tests/test_mtq_m2_tai.py` | Job, SSE, nhận kết quả, hủy queue kiểm đúng phiên/phạm vi/quyền hiện hành; toàn bộ mock. |
| MTQ-4l · 03B service | `k2/ghi_nhan_chung.py`; `m4/ghi_nhan_nghiem_thu.py`; mới `tests/test_mtq_doi_chieu.py` | Không cho quyền M4 bắc cầu sang M2; retry/đối chiếu không đổi quyền giữa các nguồn. |
| MTQ-4m · Rà cuối/đường legacy | `giao_dien/server.py`; `giao_dien/operations.py`; mới `tests/test_mtq_bao_phu.py` | Readiness không cho bật khi đường legacy/job/raw còn bỏ qua. Nếu cần sửa thêm Store/service khác, lead tách lát con ≤3 tệp và review rồi mới đánh dấu bao phủ. |
| MTQ-5a · Seed DEMO 5 vai | Mới `k2/mtq_demo.py`; `k2/crm_khoi_dong.py`; mới `tests/test_mtq_demo.py` | Tái dùng master từ 3 seed đã khảo sát, thêm actor `MO_PHONG_MTQ_*` riêng và mẫu MTQ; chỉ ở DEMO, seed một lần, không cấp lại/ghi đè thu hồi, không tự bật dữ liệu thật. |
| MTQ-5b · Chọn vai DEMO chung | `giao_dien/server.py`; `giao_dien/m4.py`; mới `tests/test_mtq_demo_phien.py` | Bộ chọn hiển thị đúng 5 cấp theo phòng/PN cho chế độ MTQ; Admin DEMO tách ở quản trị. Registry cũ còn dùng cho test âm/PN chưa bật, không bị xóa hay đổi vai. |

**Mọi lát MTQ-4: rủi ro cao, kiểm nhanh rồi review Opus trước gộp.** Các lát SQL đụng `pg_migrations.py` chạy tuần tự, đăng ký migration mới và rà checksum cũ. Nếu một lát con vượt 3 tệp, lead chia tiếp theo nhóm hàm, không mở rộng file âm thầm. Không bật sau MTQ-1/2/3; chỉ bật khi đủ chuỗi MTQ-4 cho phạm vi sử dụng và mẫu MTQ-5 đã thử.

Mẫu DEMO đề xuất: Người thực hiện 1 lập/sửa; Người thực hiện 2 kiểm; Trưởng phòng duyệt tối đa **500.000.000 VND**; CFO duyệt không giới hạn; Người xem chỉ xem. Tick cụ thể theo màn/phòng của mẫu, không cấp mọi module cho mọi vai; Admin DEMO là tài khoản quản trị riêng. Có hai PN, hai dự án cùng PN và ca không đủ BOTH M2+M5; các số đều giả. Giữ actor review-only M4, actor thiếu V4/phạm vi/đã thu hồi của seed cũ để đo hồi quy chế độ tắt, không “sửa cho đủ quyền”.

### 7.1. Điều kiện nghiệm thu/kiểm thử cho các lát code

- Chế độ tắt: test quyền cũ giữ kết quả, seed cũ không thay đổi; đối chiếu `ids_loi` và số skip theo [NEN-TEST.md](NEN-TEST.md) nền v4. Không tuyên bố xanh chỉ vì test mới đạt.
- Chế độ bật: vai cũ cho phép/tick tắt bị chặn; vai cũ cấm/tick bật vẫn đi được nếu đúng phạm vi/trạng thái; CFO/Admin không bypass; thiếu ô/role/scope/PN và hành động không có catalog bị chặn.
- Tiền: thấp hơn/bằng/cao hơn hạn mức, NULL, 0, số âm/sai kiểu/giả số client, đổi tiền sau mở màn, tổng HĐ khác tiền đợt, M4 số xin thanh toán khác nghiệm thu, USD có/thiếu tỷ giá ghim; nonmonetary khai tường minh.
- Phạm vi: khác phòng/PN/dự án/khách/hợp đồng, nguồn nhiều PN, L11 thiếu một phía, 03B nguồn hỗn hợp; giữ tách người ký/kiểm và hồ sơ đã nộp; không tự cấp lại assignment đã thu hồi.
- Giao dịch: hai Admin cùng sửa, thu hồi/kích hoạt trong lúc job chạy, trả replay sau thu hồi, audit chặn vẫn còn khi nghiệp vụ rollback, lỗi audit không cho duyệt, snapshot trước/sau tái dựng được. Kiểm SQL trực tiếp bằng vai app để phát hiện RLS/GRANT hoặc hàm SECURITY DEFINER còn bypass.
- UI/API: non-Admin không sửa qua API và không nhận dữ liệu người khác; diff/audit đủ ô cũ→mới; menu/số đếm/tải tệp thống nhất. Lead thử PostgreSQL/DEMO/trình duyệt ngoài sandbox; worker chỉ test thuần/mock, không khởi động/dừng dịch vụ.

## 8. Mặc định lead chọn — đưa nguyên vào phiếu cổng A

| Điểm | Mặc định đề xuất và trade-off |
|---|---|
| Vai thứ năm | Người xem; năm vai không có kế thừa tự động. Cấp cao vẫn cần tick, dễ kiểm soát nhưng Admin phải cấu hình rõ. |
| Admin | Vai quản trị riêng toàn hệ thống, không phải CFO và không tự có quyền duyệt; bootstrap tin cậy, audit và bảo vệ Admin cuối. |
| Hạn mức | Một cột/dòng, chỉ Duyệt; NULL không giới hạn, 0 chỉ duyệt 0. Chưa hạn Lập. Ít cột, đổi lại chưa có hạn mức khác nhau theo module. |
| Số tiền so | CRM tổng HĐ; M4 số xin thanh toán; ngoại tệ dùng tỷ giá ghim. Không có cơ sở thì chặn; không tự dùng tỷ giá mới để nới hạn. |
| Phân loại hành động | In/xuất là Xem; từ chối là Duyệt; trả lại là Kiểm; ký kết ghi nhận bản ký là Lập; Hiệu lực G6A là Duyệt. Nút hủy chỉ bật nếu code có nghiệp vụ đảo/hủy thực. |
| Module/màn | Cho phép nhóm con dưới module để tránh tick “M4 duyệt” mở toàn bộ chức năng; ô chưa có chức năng là “—”. Không tạo quyền tương lai bằng wildcard. |
| Phòng và nhiều vai | Một vai hiện hành/người/phòng/PN; ngữ cảnh được xác minh, không hợp nhất tick/hạn mức giữa phòng; mơ hồ thì chặn. |
| Dữ liệu thật | Admin/Anh tự khai vai/phạm vi và tick; bảng ánh xạ chỉ trợ giúp đối chiếu. Không tự sinh từ quyền cũ, không tự nhận mẫu DEMO. |
| Bật/khôi phục | Bật nguyên PN sau readiness toàn đường truy cập; bản nháp chưa hiệu lực. Khôi phục bằng phiên bản MTQ mới từ bản cũ, tránh vô tình trở lại quyền legacy. |
| Nhật ký | Mỗi lần Lưu/Công bố/Bật/cấp-thu hồi có diff, ai, lúc nào, lý do; chặn duyệt ghi bền sau rollback. Không lưu payload hồ sơ trong sổ quyền. |
| Phạm vi đặc biệt | Giữ độ hẹp dự án/khách/HĐ/nguồn bằng scope MTQ; bỏ role/action grant cũ khi bật, giữ trạng thái/căn cứ/tách nhiệm. Cần nhiều lát nối nhưng đáp ứng một nguồn quyền. |

Phiếu cổng A dùng các lựa chọn này cho Anh xem trực tiếp: gấp/mở module, tick và nhập hạn mức, Lưu nháp rồi Công bố/Bật một PN DEMO, đổi qua đủ năm vai, thử bằng/vượt hạn mức, non-Admin gọi API sửa, xem audit cũ→mới và ca khác dự án. Các mặc định không phải lý do dừng MTQ-0 để hỏi lại.

## 9. Trạng thái bàn giao MTQ-0

Đã khảo sát mã tĩnh và seed DEMO, viết mô hình/ánh xạ/điểm nối/rủi ro/chia lát và mặc định cổng A. Chỉ thay tệp tài liệu này; không chạy migration, không gọi PostgreSQL/dịch vụ ngoài, không sửa code, không commit. Chưa chạy test nghiệp vụ vì không đổi mã; các tiêu chí/test ở mục 7 dành cho lát triển khai, không phải kết quả đã đạt.

Thông điệp commit đề nghị để lead dùng sau review: **`[MTQ-0] Thiết kế ma trận thẩm quyền và chia lát triển khai`**.
