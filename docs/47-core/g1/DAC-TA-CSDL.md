# DAC-TA-CSDL.md — Phân chia CSDL Core và module

**Lát:** G1a-1 · **Ngày:** 30/10/2026 · **Trạng thái:** dự thảo để review và trình Anh duyệt.

**Đề xuất:** dùng một CSDL PostgreSQL chung, tách quyền sở hữu dữ liệu theo khối; giữ MTQ, bus, hàng việc và cấu trúc nghiệp vụ đã đúng; thay các đường truy cập chéo bằng hàm Core hoặc contract công bố có phiên bản.

Đây là đặc tả đích, **chưa phải trạng thái đã triển khai**. Không sửa mã, kết nối CSDL, chạy SQL, migration hoặc dọn dữ liệu trong lát này. G2 chỉ được bắt đầu sau khi đủ ba phiếu CSDL/API/SDK được Anh duyệt và có chỉ đạo mở lại lập trình theo CD-026–030.

## 1. Phạm vi, căn cứ và sơ đồ sở hữu

Áp dụng TL 54 §3–§4, §9, ưu tiên §14; TL 55 §1, §10; CD-017/018/019/021/026–030; QD-20261026-09; khảo sát KS-A…E và RV-* trong `docs/47-core/g0/`.

Đích lưu trữ là CSDL thật chung tại `D:\DU-LIEU-KE-TOAN\postgresql`; kho file tại `D:\DU-LIEU-KE-TOAN\kho-file`; sao lưu tại `D:\DU-LIEU-KE-TOAN\sao-luu`. Đây là vị trí đã chốt, không xác nhận CSDL thật đã được dựng. Không suy tên database, cổng hoặc thông tin đăng nhập từ đường dẫn.

**Ký hiệu căn cứ:** `P` = `src/kho_tri_thuc/ha_tang/pg_migrations.py`; `H/`, `K/`, `M/` lần lượt là các thư mục `ha_tang/`, `k2/`, `m4/` dưới `src/kho_tri_thuc/`; `J` = `docs/47-core/g0/so-lieu-csdl-demo.json`. Dẫn chiếu `P:21` được hiểu là `tệp:dòng` theo quy ước này.

### 1.1. Sơ đồ khối đích

```text
                    CSDL PostgreSQL chung
 ┌──────────────────────────────────────────────────────────┐
 │ Core sở hữu                                              │
 │ loi             loi_tai_lieu             danh_muc         │
 │ danh tính/MTQ    tài liệu/tệp/kết quả     định danh chung  │
 │ module/engine   quyền nội dung           liên kết chung   │
 │ quy trình/việc  nguồn kết quả            danh mục         │
 │ bus/audit/cổng                                            │
 ├──────────────────────────────────────────────────────────┤
 │ Module sở hữu                                            │
 │ mod_crm · mod_m2 · mod_m4 · mod_m0 · mod_m1 · mod_m3        │
 │ mod_m5 · mod_m9 · các mod_* được đăng ký tiếp theo         │
 │         ↓ công bố phần dữ liệu được phép đọc              │
 │ cong_bo_crm · cong_bo_m2 · cong_bo_m4 · cong_bo_<module>    │
 ├──────────────────────────────────────────────────────────┤
 │ ke_toan_cu: vùng chuyển tiếp có chủ, không phải Core mới   │
 └──────────────────────────────────────────────────────────┘
```

Sơ đồ thể hiện ranh giới đích. Không chuyển nguyên schema `master` hoặc `kho` vào Core: các schema này đang chứa cả dữ liệu chung và dữ liệu nghiệp vụ. Căn cứ phân chia theo đối tượng: `P:21`, `P:195`, `P:286`, `P:483`; bảng kiểm kê tại `docs/47-core/g0/KS-B.md:24`.

| Khối — chủ nghiệp vụ | Nội dung | Ai ghi, qua đâu | Ai đọc, qua đâu |
|---|---|---|---|
| `loi` — Core | Danh tính, MTQ, module, engine, sổ cổng, quy trình, hàng việc, bus, audit, lịch sử đổi cấu trúc | Dịch vụ Core; module gọi hàm được cấp quyền, không ghi bảng | Core đọc bảng theo chức trách; module gọi hàm đọc Core |
| `loi_tai_lieu` — Core | Metadata tài liệu/tệp, biến thể, phiên bản, quyền, kết quả và nguồn | Dịch vụ kho Core; engine trả kết quả cho Core lưu | Qua dịch vụ/hàm Core; tải bytes cũng kiểm quyền |
| `danh_muc` — Core | Đối tác, dự án, tài khoản, định danh hợp đồng/chứng từ, liên kết và phân bổ chung | Hàm Core có kiểm quyền, chống trùng và kiểm căn cứ | Module đọc tập cột được cấp hoặc hàm đọc danh mục; áp RLS |
| `mod_crm` — CRM | Hợp đồng bán: phiên bản/tham số, báo giá, mẫu, dự án bán, ký, lịch nghĩa vụ | Runtime CRM ghi bảng riêng hoặc hàm riêng | CRM đọc riêng; bên khác qua `cong_bo_crm` |
| `mod_m2` — M2 | Hóa đơn mua, quan sát/phiên bản/dòng, đích hạch toán, công nợ và ngoại lệ thuộc M2 | Runtime M2 | M2 đọc riêng; bên khác qua `cong_bo_m2` |
| `mod_m4` — M4 | Hồ sơ thầu, phụ lục, BOQ, đợt, kiểm tra, nghiệm thu, đối chiếu, Request nháp | Runtime M4 | M4 đọc riêng; bên khác qua `cong_bo_m4` |
| `mod_m0` — M0 | Tiếp nhận nguồn, cấu hình nguồn, lần tiếp nhận, vùng tạm trước định tuyến | Runtime tiếp nhận M0, qua hàm tiếp nhận | M0 đọc riêng; phần dùng chung qua Core hoặc `cong_bo_m0` |
| `mod_m1` — M1 | Sao kê/thu chi và đối chiếu thuộc M1 sau khi xác định chủ | Runtime M1; chưa chuyển phần chưa đủ ánh xạ | M1 đọc riêng; bên khác qua `cong_bo_m1` |
| `mod_m3` — M3 | Cơ sở doanh thu, liên kết hóa đơn–hợp đồng và chính sách nghiệp vụ M3 | Runtime M3 | M3 đọc riêng; bên khác qua `cong_bo_m3` |
| `mod_m5` — M5 | Phiếu kho, số lượng, bằng chứng và liên kết dòng thuộc M5 | Runtime M5 | M5 đọc riêng; bên khác qua `cong_bo_m5` |
| `mod_m9` — M9 | Hợp đồng vay, lịch trả nợ và nghiệp vụ khoản vay | Runtime M9 | M9 đọc riêng; bên khác qua `cong_bo_m9` |
| `cong_bo_<module>` — module nguồn | Khung nhìn/hàm đọc có contract; không phải bản sao toàn bộ bảng | Chỉ migration của khối công bố được đổi định nghĩa; runtime không DML | Module được cấp quyền đọc đúng contract |
| `ke_toan_cu` — chủ chuyển tiếp kế toán | Chứng từ/đề xuất/khóa kỳ/tri thức/việc duyệt/lô xuất còn chưa chuyển | Chỉ adapter cũ được chỉ định, theo quyền hữu hạn | Qua adapter, hàm hoặc mặt công bố chuyển tiếp |

`mod_m0` không tiếp tục làm chủ mọi bảng chung như nhãn M0 trước đây: chức trách dùng chung được nâng vào Core. Quyết định cũ nằm tại `docs/46-chuyen-doi-dieu-phoi/giao-viec-20261026/tra-loi-lead-xs-5a1.md:3`; đây là chênh lệch đóng gói theo TL 54 §14.

M1 chưa có migration riêng mang tên M1 trong chuỗi 67; full-M9 lịch sử không thuộc chuỗi mặc định. Vì vậy hai khối này là **đích phân loại**, không xác nhận đã có đủ bảng tương ứng (`P:2994`, `P:3434`, `P:9596`). M6/M7/M8/M10 và công cụ mới chỉ được cấp schema khi có gói và bản đồ dữ liệu được duyệt.

### 1.2. Đối chiếu XS-5a1

| Vùng | Quy tắc đích |
|---|---|
| **V1 — riêng** | Bảng/hàm của `mod_<mình>`; quyền đọc/ghi theo nghiệp vụ và pháp nhân |
| **V2 — ghi chung** | Hàm Core trong `loi`, `loi_tai_lieu`, `danh_muc`; không DML trực tiếp bảng chung |
| **V3 — danh mục chung** | Chỉ đọc danh mục được cấp; không dùng V3 để hợp thức hóa bảng nghiệp vụ module khác |
| **V4 — công bố** | Chỉ đọc contract của `cong_bo_<nguồn>`; đăng ký sự kiện riêng qua bus Core |

Mô hình khai báo bốn vùng đã có; bộ kiểm hiện kiểm metadata và điểm truy cập được truyền vào, chưa trace SQL thực (`H/khai_bao_module.py:144`, `H/khai_bao_module.py:225`; `K/vung_du_lieu.py:1`). G1 giữ mô hình này và bổ sung kiểm thực thi ở §6.

## 2. Bảng tên tiếng Việt không dấu

Tên dưới đây là tên đích. Đổi schema không đồng nghĩa viết lại bảng. Giữ UUID, khóa nghiệp vụ, trạng thái và cấu trúc đúng; chỉ đổi phần lệch quy ước hoặc lệch chủ.

| Tên TL 54 / tên hiện có | Tên đề xuất | Lý do |
|---|---|---|
| `platform_core` | `loi`, `loi_tai_lieu`, `danh_muc` | Tách ba chức trách chung |
| `platform_mod_document_search` | `mod_tra_cuu_tai_lieu` | Việt hóa nghiệp vụ |
| `platform_mod_masking` | `mod_che_du_lieu` nếu có module nghiệp vụ | Phân biệt module với engine `e_mask` |
| `platform_mod_financial_analysis` | `mod_phan_tich_tai_chinh` | Việt hóa nghiệp vụ |
| `master`, `m4`, `m3` | Chia `master` theo chủ; `mod_m4`, `mod_m3` | Không coi schema cũ là một chủ |
| `bus`, `viec`, `nhat_ky` | Chuyển từng đối tượng vào `loi` | Hợp nhất chức trách Core, giữ tên bảng phù hợp |
| `users`, `workspaces` / `nguoi_dung`, `phap_nhan` | `loi.nguoi_dung`, `loi.phap_nhan` | Giữ tên đúng; pháp nhân là workspace |
| `memberships` / `phan_quyen` | `loi.phan_quyen`; mặt đọc `thanh_vien` | Dùng lại quan hệ người–pháp nhân, không tạo nguồn quyền thứ hai |
| `business_roles` | `loi.vai_nghiep_vu` | Danh mục mã vai dùng bởi MTQ |
| `modules` / `module_danh_muc` | `loi.module_danh_muc` | Giữ bảng registry đã có |
| `module_versions`, `module_grants` | `phien_ban_module`, `cap_quyen_module` | Phần bổ sung cho quản lý gói/quyền |
| `engine_definitions/profiles/instances` | `engine_dinh_nghia`, `engine_ho_so_chay`, `engine_phien_chay` | Phân biệt định nghĩa, cấu hình, lần chạy |
| `workflows/workflow_versions` | `quy_trinh`, `phien_ban_quy_trinh` | Việt hóa |
| `jobs` / `viec.hang_viec` | `loi.hang_viec` | Dùng XS-2; không thêm bảng `viec` trùng chức năng |
| `job_steps/job_attempts` | `buoc_viec`, `lan_thu` | Bổ sung chi tiết thực thi |
| `bus.su_kien`, `bus.inbox` | `loi.su_kien`, `loi.hop_nhan_su_kien` | Giữ tên sự kiện; Việt hóa hộp nhận |
| `audit_events` / `nhat_ky.su_kien` | `loi.nhat_ky_kiem_toan` | Tránh trùng tên sự kiện bus |
| `documents`, `files` / `kho.tep_goc` | `loi_tai_lieu.tai_lieu`, `loi_tai_lieu.tep_goc` | Dùng lại metadata tệp bất biến; không thêm bảng tệp tương đương |
| `document_permissions` | `quyen_tai_lieu` | Việt hóa |
| `artifacts/artifact_sources` | `ket_qua_xu_ly`, `nguon_ket_qua` | Phân biệt kết quả với tệp vật lý |
| `master.schema_migrations` | `loi.lich_su_doi_cau_truc` | Sổ áp dụng theo gói; bảo toàn lịch sử cũ |
| `version/checksum/applied_at` của migration | `so_phien_ban/ma_bam/ap_dung_luc` | Không đổi ý nghĩa checksum |
| `migration_tuong_thich`; `he_thong.key/value` | `tuong_thich_doi_cau_truc`; `he_thong.khoa/gia_tri` | Việt hóa, giữ chứng cứ tương thích |
| `workspace_id` | `phap_nhan_id` | Một định danh phạm vi thống nhất |
| `row_version`, `revision` dùng cho CAS dòng | `phien_ban_dong` | Tên CSDL theo §14; API có thể ánh xạ `row_version` |
| `created_at/by`, `updated_at/by` | `tao_luc/tao_boi`, `cap_nhat_luc/cap_nhat_boi` | Chuẩn truy vết |
| `valid_from/to` | `hieu_luc_tu/hieu_luc_den` | Phân biệt hiệu lực với lúc tạo |
| `payload`, `khoa_dedupe`, `lease_*` | `noi_dung_su_kien`, `khoa_chong_trung`, `giu_viec_*` | Việt hóa, giữ cơ chế hiện có |
| `app_web/doc/ke_toan/cong_ai` | Tên chuyển tiếp; đích theo mẫu `vai_chay_<khoi>` | Không thay tên rồi giữ nguyên quyền rộng |
| Role migration | `vai_doi_cau_truc_<khoi>` | Tách DDL khỏi runtime |

Căn cứ tên/cấu trúc hiện có: `P:21`, `P:59`, `P:65`; `K/sql_module.py:8`; `K/sql_hang_viec.py:25`; `K/sql_bus_su_kien.py:49`; `H/postgres.py:236`, `:238`, `:244`.

`phien_ban_dong` chỉ là bộ đếm CAS, không thay số phiên bản hồ sơ, revision kết quả hoặc hash căn cứ. Các token nghiệp vụ đang khác nhau phải được giữ qua adapter (`docs/47-core/g0/KS-C.md:170`). Mã CRM, M2, MTQ, UUID và tên PostgreSQL/extension được giữ như mã kỹ thuật có định nghĩa.

## 3. Mô hình dữ liệu Core

**Quy ước chung:** ID nghiệp vụ mới dùng UUID; thời điểm dùng `timestamptz`, ngày nghiệp vụ dùng `date`; tiền/tỷ lệ dùng `numeric` có độ chính xác và đơn vị rõ; thuộc tính JSON có phiên bản cấu trúc. Không đổi cơ học các cột tiền `_minor` hiện hữu hoặc biến trạng thái thiếu căn cứ thành số 0.

Bảng sửa đồng thời có `phien_ban_dong > 0`; cập nhật phải khớp phiên bản mong đợi. Bảng ghi thêm không bắt buộc có cột cập nhật. Quan hệ cha–con thuộc pháp nhân dùng khóa ghép hoặc kiểm tương đương để ngăn gắn chéo pháp nhân. Không mặc định `ON DELETE CASCADE` cho hồ sơ nghiệp vụ.

Các bảng bổ sung dưới đây là cấu trúc cố định; mỗi phiên bản/lần chạy phát sinh bằng **thêm dòng**.

### 3.1. Danh tính, thẩm quyền và module — schema `loi`

| Bảng/mặt đọc | Khóa và quan hệ chính | Quy tắc |
|---|---|---|
| `nguoi_dung` | PK `id`; UNIQUE `dang_nhap`; ánh xạ nguồn xác thực production | Giữ người dùng hiện có; tài khoản mô phỏng không dùng làm đăng nhập thật |
| `phap_nhan` | PK `id`; UNIQUE `ma` | Chính là workspace; không tạo thêm bảng workspace song song |
| `phan_quyen` | PK `id`; UNIQUE `(nguoi_dung_id, phap_nhan_id)`; FK hai bảng trên | Dùng lại làm quan hệ thành viên; `thanh_vien` là mặt đọc, không lưu bản sao |
| `vai_nghiep_vu` | PK `ma` | Danh mục mã vai; không tự cấp quyền khi thêm mã |
| `phien_xac_thuc` | PK `id`; FK người dùng; hạn dùng, thu hồi, nguồn xác thực | Chỉ lưu định danh/băm bí mật phiên; ngữ cảnh ủy nhiệm phải kiểm chứng được |
| `mtq_phong` | PK `id`; UNIQUE `(phap_nhan_id, ma)` | Giữ phòng thuộc pháp nhân |
| `mtq_admin` | PK `id`; FK người được cấp/người cấp; một cấp hiện hành/người | Giữ lịch sử cấp/thu hồi |
| `mtq_danh_muc_hanh_dong` | Khóa phiên bản danh mục + module + màn + hành động | Chuẩn hóa tên cột tiếng Anh; giữ mã hành động |
| `mtq_phien_ban` | PK `id`; UNIQUE `(phap_nhan_id, so_phien_ban)` | Bản công bố bất biến |
| `mtq_dong` | PK `id`; FK phiên bản/phòng cùng pháp nhân | Vai và hạn mức tiền |
| `mtq_o` | PK `(dong_id, module, man, hanh_dong)` | Quyền cho phép của từng ô |
| `mtq_gan_vai` | PK `id`; FK người dùng/phòng/pháp nhân/vai | Một nguồn gán vai hiệu lực |
| `mtq_pham_vi` | PK `id`; FK gán vai cùng pháp nhân | Giữ phạm vi dự án/hợp đồng/khách/nguồn |
| `mtq_kich_hoat` | PK `phap_nhan_id`; FK phiên bản cùng pháp nhân | Điều khiển đường chuyển tiếp đã được duyệt |
| `mtq_thay_doi`, `mtq_tu_choi` | Mỗi bảng PK `id`; liên kết yêu cầu, người, pháp nhân và phiên bản MTQ | Giữ bảng audit chuyên biệt, không thay bằng log tự do |
| `module_danh_muc` | PK `ma`; ánh xạ schema, role và gói | Giữ khóa mã module hiện có |
| `phien_ban_module` | PK `id`; UNIQUE `(module, so_phien_ban)` | Hash gói, yêu cầu tương thích, trạng thái cài; không chứa bí mật |
| `cap_quyen_module` | PK `id`; FK module/phiên bản; phạm vi pháp nhân và tài nguyên | Quyền **đã cấp**, tách yêu cầu trong manifest; ghi lịch sử thu hồi |
| `module_cong_tac` | PK `(module, phap_nhan_id)` | Giữ `TAT/THU/VAN_HANH`; không thay MTQ |
| `module_nguoi_thu` | PK `id`; FK module/người/pháp nhân | Giữ danh sách thử và lịch sử |
| `lich_su_doi_cau_truc` | PK `(ma_goi, so_phien_ban)` | Hash, thời điểm, người áp dụng, nguồn lịch sử |
| `tuong_thich_doi_cau_truc` | Khóa gói/phiên bản/hash cũ/hash mới | Chỉ ghi trường hợp tương thích được xác định chính xác |

Nguồn tái sử dụng: danh tính/thành viên `P:59`, `P:65`; MTQ `K/sql_ma_tran_tham_quyen.py:61`, `:87`, `:97`, `:106`, `:113`, `:122`, `:132`, `:138`; công tắc `K/sql_module.py:8`, `:15`, `:26`.

Không xây một bảng “ma trận thẩm quyền” thứ hai. Quyền thành viên, quyền module và MTQ là các lớp kiểm khác nhau, không phải ba nguồn cho cùng một quyết định.

### 3.2. Engine, sổ cổng và số đo — schema `loi`

| Bảng | Khóa và quan hệ chính | Nội dung bắt buộc |
|---|---|---|
| `engine_dinh_nghia` | PK `id`; UNIQUE `(ma, so_phien_ban)` | Capability, contract vào/ra, phiên bản adapter, giới hạn thực có |
| `engine_ho_so_chay` | PK `id`; FK định nghĩa engine | Máy thực thi, executable/đối số được kiểm soát, tham chiếu bí mật, concurrency, timeout và thời gian rảnh |
| `so_cong` | PK `id`; FK module **hoặc** hồ sơ engine; UNIQUE `(may_chu_id, dia_chi_nghe, cong)` và chủ được cấp | Cổng cố định, bên đang giữ, thế hệ sở hữu, lease, trạng thái, `phien_ban_dong` |
| `engine_phien_chay` | PK `id`; FK hồ sơ và sổ cổng | Định danh instance, PID **kèm định danh lần tạo tiến trình**, phiên bản thực, readiness, heartbeat, bắt đầu/kết thúc |
| `module_phien_chay` | PK `id`; FK phiên bản module và sổ cổng | Thông tin tiến trình tương đương cho module độc lập |
| `so_do_phien_chay` | PK `id`; FK đúng một phiên engine/module | Các mốc và số đo CD-028 mục 3b |
| `de_xuat_che_do_chay` | PK `id`; FK chủ chạy; UNIQUE chủ/kỳ/phiên bản đề xuất | Cửa sổ số liệu, đề xuất, lý do, Admin áp dụng/từ chối và thời điểm |

`so_cong` là sổ quản lý; **dòng CSDL không thay việc hệ điều hành thực sự giữ socket**. Một chủ có một cổng cố định trên máy triển khai được chỉ định. Dùng lease/thế hệ sở hữu và CAS để chống hai tiến trình Core khởi động cùng chủ.

Trạng thái sổ cổng phân biệt Core đang giữ, đang bàn giao, tiến trình con đang giữ, đang thu hồi và lỗi. Chỉ đánh dấu sẵn sàng sau khi kiểm danh tính, phiên bản và readiness. Sau gián đoạn phải đối chiếu tiến trình/socket thực tế; không tin PID hoặc dòng trạng thái cũ đơn lẻ.

Mỗi lần khởi động ghi: giờ nhận yêu cầu, bắt đầu khởi động, lúc sẵn sàng hoặc thất bại; thời gian chạy việc; thời gian rảnh trước đóng; lúc đóng; RAM đỉnh/trung bình, CPU time và cửa sổ đo. Số lần/ngày được tổng hợp từ các dòng này. Số đo thiếu ghi “chưa đo”, không ghi 0.

Mặc định tự kích hoạt/tự đóng cho mọi engine/module, kể cả OCR/AI. Hằng tuần chỉ **đề xuất** giữ lâu hơn hoặc luôn chạy; chỉ Admin áp dụng. Không tự đổi chính sách từ thống kê. Việc chuyển giao socket và đo thực tế thuộc G2.

Danh bạ engine hiện là cấu trúc RAM; host #6 có cơ chế nhận diện/readiness nhưng đang để con mở cổng rồi báo về (`H/danh_ba_engine.py:12`; `src/kho_tri_thuc/nguon/trich6_host.py:240`, `:607`). Đặc tả bổ sung registry bền vững, không yêu cầu viết lại thuật toán engine.

### 3.3. Quy trình, việc, sự kiện và audit — schema `loi`

| Bảng | Khóa và quan hệ chính | Quy tắc |
|---|---|---|
| `quy_trinh` | PK `id`; UNIQUE `(module, ma)` | Danh tính quy trình ổn định |
| `phien_ban_quy_trinh` | PK `id`; UNIQUE `(quy_trinh_id, so_phien_ban)` | Định nghĩa bước/phụ thuộc/nhánh/mapping có hash; bản công bố bất biến |
| `hang_viec` | Giữ PK UUID; UNIQUE `(phap_nhan_id, module, khoa_chong_trung)` | Dùng XS-2; bổ sung liên kết phiên bản quy trình, người tạo và phạm vi ủy nhiệm |
| `buoc_viec` | PK `id`; FK việc cùng pháp nhân; UNIQUE `(viec_id, ma_buoc)` | Trạng thái bước, phụ thuộc, đầu vào/kết quả, căn cứ chờ duyệt |
| `lan_thu` | PK `id`; FK bước cùng pháp nhân; UNIQUE `(buoc_viec_id, so_lan)` | Worker/instance, thời điểm, thế hệ giữ việc, lỗi, kết quả và kết luận an toàn retry |
| `su_kien` | Giữ PK UUID; UNIQUE pháp nhân/bên phát/khóa chống trùng | Outbox bất biến, phiên bản contract, hash nội dung |
| `hop_nhan_su_kien` | PK `(phap_nhan_id, ben_nhan, su_kien_id)`; FK sự kiện cùng pháp nhân | Trạng thái nhận/xác nhận và thời điểm |
| `nhat_ky_kiem_toan` | Giữ khóa kỹ thuật cũ; liên kết pháp nhân, người, yêu cầu, việc/bước/lần thử | Chỉ ghi thêm; lọc nội dung nhạy cảm |
| `cong_ai_goi` | Giữ PK UUID; liên kết pháp nhân/việc | Nhật ký chuyên biệt của cổng AI; không lưu khóa hoặc toàn văn mặc định |

Hàng việc đã có dedupe, lease/token, tiến độ, dừng và trạng thái `CHUA_RO` (`K/sql_hang_viec.py:25`). Wrapper không tự commit và yêu cầu caller xác định danh tính/pháp nhân/module từ máy chủ (`H/hang_viec.py:1`, `:21`). Giữ các cơ chế này; `buoc_viec`/`lan_thu` bổ sung chi tiết, không tạo một hàng đợi thay thế.

Bus hiện chỉ nhận tham chiếu UUID, giao ít nhất một lần và có thể ghi kết quả cùng ACK trong một transaction PostgreSQL (`K/sql_bus_su_kien.py:1`, `:49`, `:64`). Giữ đặc tính đó. Không tuyên bố exactly-once cho tác động bên ngoài; việc chưa rõ kết quả phải đối soát trước retry.

Audit hiện dùng khóa `bigserial`; giữ khóa này, không chuyển sang UUID chỉ để đồng dạng (`P:413`). Không đồng nhất bus với audit, hoặc `kho.phien`/`viec_can_duyet` cũ với phiên đăng nhập/hàng việc Core.

### 3.4. Tài liệu, tệp và kết quả — schema `loi_tai_lieu`

| Bảng | Khóa và quan hệ chính | Quy tắc |
|---|---|---|
| `tai_lieu` | PK `id`; FK pháp nhân | Danh tính hồ sơ, loại, module quản lý, trạng thái và CAS |
| `tep_goc` | Giữ PK UUID; FK pháp nhân | Metadata tệp bất biến: mã băm, kích thước, MIME, khóa lưu trữ nội bộ; giữ ID tệp cũ |
| `tai_lieu_tep` | PK `id`; FK tài liệu/tệp cùng pháp nhân; UNIQUE tài liệu/biến thể/số phiên bản | Liên kết bản gốc, OCR, bản đã che và các bản kế tiếp |
| `quyen_tai_lieu` | PK `id`; FK tài liệu cùng pháp nhân và chủ thể được cấp | Hành động, biến thể được đọc, hiệu lực, cấp/thu hồi; không vượt MTQ |
| `ket_qua_xu_ly` | PK `id`; FK tài liệu, việc/bước/lần thử cùng pháp nhân khi có | Contract/version, engine/module/function tạo, revision, trạng thái xử lý và trạng thái duyệt riêng |
| `nguon_ket_qua` | PK `id`; FK kết quả; tham chiếu tệp/kết quả nguồn | Trang/vùng/trích dẫn/hash và phiên bản nguồn; ngăn chu trình nguồn |
| `anh_xa_dinh_danh_cu` | PK `id`; UNIQUE hệ nguồn/loại/ID cũ | Ánh xạ tới ID Core để đối chiếu, không cấp quyền bằng ID cũ |

`tep_goc` hiện có UUID, pháp nhân, hash và đường dẫn (`P:196`). Giữ định danh và dữ liệu đúng; mở rộng có kiểm soát để phục vụ kho chung. Không coi cùng hash là cùng quyền: metadata và kiểm quyền phải theo pháp nhân; dedupe bytes vật lý, nếu dùng, nằm dưới dịch vụ kho.

Module nhận ID, không nhận đường dẫn để tự mở kho. Core xác nhận metadata và tệp đã ghi/kiểm hash trước khi công bố kết quả; có trạng thái chờ/lỗi để phục hồi khi CSDL và filesystem không hoàn tất cùng lúc.

Thành công xử lý, hết mục cần soát và phê duyệt nghiệp vụ là ba trạng thái khác nhau. Kết quả OCR API hiện có TTL 600 giây và `/result` không tự chặn bản chưa duyệt; Core phải tiếp nhận theo chính sách được duyệt trước khi xác nhận bàn giao (`docs/47-core/g0/KS-E.md:81`, `:93`, `:95`). Không mặc định biến dữ liệu RAM-only hoặc bảng mở che thành dữ liệu lưu lâu dài.

## 4. Role PostgreSQL và hàm có đặc quyền

### 4.1. Cặp role cho mỗi khối

Với mỗi schema được cài, tạo hai role cố định:

| Role | Quyền và thuộc tính |
|---|---|
| `vai_chay_<khoi>` | Role nhóm `NOLOGIN`; không superuser, `BYPASSRLS`, `CREATEROLE`, `CREATEDB`; không sở hữu bảng; không DDL |
| `vai_doi_cau_truc_<khoi>` | `NOLOGIN`; sở hữu schema/đối tượng thuộc khối; chỉ tài khoản cài đặt được nhận quyền sử dụng trong phiên bảo trì |

Áp dụng cả `loi`, `loi_tai_lieu`, `danh_muc`, `mod_*`, `cong_bo_*` và `ke_toan_cu`. Role chạy công bố chỉ có quyền đọc/EXECUTE, không DML. Chủ công bố được module nguồn cấp đúng quyền đọc cần cho contract, chịu RLS và kiểm quyền tường minh; không được quyền sửa bảng nguồn.

Login dịch vụ được gắn đúng role chạy của tiến trình. Không cấp cho một login module khả năng chuyển sang role module khác, role migration hoặc role chủ. Engine không giữ mật khẩu PostgreSQL. Tài khoản provisioning/backup là chức trách quản trị riêng, không dùng trong yêu cầu nghiệp vụ.

Các role `app_web`, `app_doc`, `app_ke_toan`, `app_cong_ai` hiện là role nhóm NOLOGIN; quyền cũ có phạm vi rộng (`J:28`; `P:783`). Chúng chỉ là lớp tương thích trong chuyển tiếp. Phải kiểm cả membership, khả năng `SET ROLE`, quyền kế thừa và owner thực tế trước khi cấp role mới; không dùng `app_web` làm nhóm thừa hưởng mọi module.

### 4.2. Hàm `SECURITY DEFINER` và PUBLIC

Mỗi hàm phải có chủ, chữ ký, người được gọi và tài nguyên chạm tới:

- Chủ hàm là role sở hữu của khối, không phải login runtime hoặc superuser.
- `search_path` cố định: `pg_catalog`, các schema tin cậy tối thiểu, `pg_temp` cuối; định danh đầy đủ đối tượng. Runtime không có `CREATE` trên schema tin cậy.
- Chỉ cấp `EXECUTE` đúng chữ ký cho đúng role. Hàm nội bộ không công khai; wrapper phải kiểm danh tính, module, pháp nhân, hành động và căn cứ.
- Bảng nghiệp vụ thuộc pháp nhân bật RLS và `FORCE ROW LEVEL SECURITY`; không dùng quyền owner để thay kiểm nghiệp vụ. Bảng xác thực/quản trị toàn cục có chính sách riêng, tránh vòng đệ quy khi tra quyền.
- Trong schema đích do hệ thống sở hữu: thu hồi quyền PUBLIC không cần thiết trên schema/bảng/sequence/hàm; thiết lập default privileges theo **từng role tạo đối tượng**. Với schema dùng chung/extension hiện hữu, chỉ thay sau khi kiểm phụ thuộc.

Catalog DEMO ghi 100/128 bảng bật RLS nhưng 0 FORCE, 120 hàm DEFINER và 167 hàm có EXECUTE mặc định PUBLIC; chưa đủ owner/ACL chi tiết để kết luận quyền hiệu lực (`J:2663`, `:2707`, `:2740`, `:2742`). Các số này là đầu vào rà soát, không phải danh sách thu hồi hàng loạt.

CRM G hiện nhận kết nối chủ bảng (`K/crm_mau.py:111`, `:126`). Đường này phải chuyển sang runtime và hàm được cấp quyền trước nghiệm thu Core.

## 5. RLS theo pháp nhân và cùng một cổng kiểm quyền

Mỗi transaction nghiệp vụ phải:

1. Xác thực phiên, module và pháp nhân ở Core.
2. Mở transaction bằng role đúng khối.
3. Đặt ngữ cảnh bằng `SET LOCAL` hoặc `set_config(..., true)`.
4. Thực hiện thao tác qua kiểm phạm vi, quyền module, MTQ và quyền hồ sơ/nội dung.
5. Commit/rollback; không để ngữ cảnh yêu cầu trước rò sang kết nối tái sử dụng.

Giữ các khóa ngữ cảnh `ktt.*` đang dùng khi còn phù hợp, không thêm namespace chỉ để đổi tên. Mẫu transaction-local đã có tại `K/crm_mau.py:135`.

**GUC không tự chứng minh danh tính.** Nếu module có quyền tự đặt giá trị, hàm kiểm phải xác minh ủy nhiệm từ Core, ràng buộc với phiên còn hiệu lực, login/module gọi, pháp nhân và thao tác. Không chấp nhận UUID người dùng do client hoặc module tự khai làm bằng chứng quyền.

RLS cho cả `USING` và `WITH CHECK`; không cho đổi `phap_nhan_id` để chuyển hồ sơ. Thiếu/sai ngữ cảnh thì từ chối. Dữ liệu toàn cục phải được phân loại rõ; `phap_nhan_id IS NULL` không phải cửa đọc toàn hệ thống.

MTQ tiếp tục quyết định hành động, hạn mức, phạm vi và quy tắc kiểm/duyệt. Đối tượng nhiều pháp nhân phải đạt quyền ở **mọi** pháp nhân; hỗn hợp bật/tắt MTQ bị chặn theo QD-20261026-10 (`docs/QUYET-DINH.md:365`). Đường quyền cũ chỉ được giữ cho đối tượng chuyển tiếp đã khai báo, không tự lan sang module mới.

Dữ liệu M0 chưa xác định pháp nhân nằm trong vùng tiếp nhận riêng, kiểm bằng quyền nguồn/lần tiếp nhận; sau định tuyến mới vào dữ liệu nghiệp vụ. Cơ chế registry/vùng tạm đã có tại `P:3036`, `P:3063`, `P:3173`; không áp một policy pháp nhân giả cho toàn bộ đầu vào này.

**Job/worker:** lưu người tạo, pháp nhân, module và phạm vi ủy nhiệm; kiểm lại quyền khi nhận việc và trước ghi/kết quả/tác động ngoài. Quyền bị thu hồi phải chặn hoặc chuyển chờ có lý do. Máy xử lý phụ chỉ nhận đầu vào/kết quả của việc được giao, không đọc bảng nghiệp vụ hoặc giữ khóa mã hóa.

**Download:** tra tệp từ tài liệu/kết quả được phép, kiểm biến thể và trạng thái duyệt trước trả bytes. Không có đường tắt vì biết ID, hash hoặc đường dẫn.

**Xuất riêng một công ty — CD-021:** chỉ Admin khởi tạo với pháp nhân rõ ràng; công cụ xuất qua bản đồ sở hữu, gồm dữ liệu module, file, audit, ánh xạ và phần danh mục cần thiết. Dùng snapshot/mốc nhất quán CSDL–file; đối chiếu số dòng, tổng tiền theo đơn vị, hash và tham chiếu; thử phục hồi vào đích riêng trên DEMO. Không mang dữ liệu công ty khác, khóa hay bí mật phiên vào gói. Không dùng backup cả database rồi coi đó là bản xuất một pháp nhân.

## 6. Quy tắc ghi/đọc giữa module và xử lý XS-5a2

### 6.1. Ranh giới truy cập

“Không SQL chéo schema” nghĩa là module không trực tiếp đọc/ghi **bảng riêng** của khối khác. Các giao diện được phép phải khai báo cụ thể: hàm Core V2, danh mục V3 và mặt công bố V4.

- DML chỉ trong V1; dữ liệu chung chỉ ghi qua hàm Core.
- Đọc module khác chỉ qua `cong_bo_*`; không dùng view trong schema mình để che một truy vấn trái phép.
- Hàm công bố do module nguồn quản lý đọc bảng của chính nguồn; không kéo ngược bảng riêng module nhận.
- FK module → định danh Core được phép theo bản đồ. Core không tạo phụ thuộc bắt buộc tới bảng riêng module tùy chọn.
- Thiếu dữ liệu trả `CHO` có lý do; sai quyền trả lỗi quyền. Không đánh đồng hai trường hợp.
- Contract công bố hoạt động bằng dữ liệu bền vững và đối tượng CSDL đã cài, không đòi tiến trình nguồn đang chạy.

Mỗi contract ghi phiên bản, trường/đơn vị/trạng thái, quyền, quy tắc phiên bản hiện hành và điều kiện công bố. Thay đổi phá tương thích dùng phiên bản mới; không thay âm thầm bản cũ.

Hàm công bố hóa đơn hiện có cần được giữ hành vi và chuyển mặt truy cập sang `cong_bo_m2`, không viết lại nội dung: đang công bố qua `master.hoa_don_cong_bo`, có kiểm quyền, `CHO`, phiên bản nguồn và trạng thái thiếu căn cứ tiền (`K/sql_cong_bo_hoa_don.py:15`, `:20`, `:38`, `:56`). Gói M2 sở hữu cả phần công bố và yêu cầu quyền liên quan.

### 6.2. Chốt đề xuất cho bốn bảng CRM đang đếm

CRM đang dùng phiên bản hợp đồng, lịch thu và liên kết chung trong truy vấn/hàm nghiệp vụ; khung gọi lại dịch vụ danh sách (`K/crm_s1.py:87`, `:122`, `:247`; `P:1018`; `src/kho_tri_thuc/giao_dien/khung_khai_bao.py:119`, `:143`).

| Bảng hiện có | Chủ/đích đề xuất | CRM truy cập thế nào; có cần công bố? |
|---|---|---|
| `master.hop_dong` | `danh_muc.hop_dong` giữ định danh chung; trạng thái/thuộc tính bán hàng do CRM quản lý | CRM đọc phần danh mục qua V3, ghi qua V2. Thông tin nghiệp vụ bán hàng công bố cho bên khác qua `cong_bo_crm` |
| `master.hop_dong_phien_ban` | Dòng phiên bản bán hàng → `mod_crm.hop_dong_phien_ban`; dòng chủ khác theo module nguồn | CRM đọc riêng qua V1; M3/M4/module khác phải dùng `cong_bo_crm`. Không chuyển toàn bảng sang CRM chỉ vì tên |
| `master.lich_thu` | Lịch nghĩa vụ bán hàng → `mod_crm.lich_thu` | CRM đọc V1; bên khác qua `cong_bo_crm`, giữ ID và khóa nghĩa vụ |
| `kho.lien_ket_chung_tu` | `danh_muc.lien_ket_chung_tu` | Ghi qua hàm Core; đọc mặt V3/hàm tổng hợp được cấp. Không cần giả thành công bố CRM |

`hop_dong_tham_so` đi cùng chủ phiên bản. Dòng không xác định được chủ giữ tại `ke_toan_cu`, không suy từ tên hoặc ép về CRM. Trong chuyển tiếp, bảng dùng chung vẫn giữ “chủ theo dòng”; chỉ tách khi đối chiếu được ID, trạng thái và quan hệ.

Hàm liên kết Core cần kiểm phiên bản/lịch nghĩa vụ qua contract nguồn có căn cứ phiên bản, giữ kiểm cùng pháp nhân, tiền tệ, chống vượt tiền và khóa phối hợp trong transaction. Không thay FK cũ bằng UUID không được kiểm. Cơ chế kiểm hiện tại là đầu vào cần bảo toàn (`P:1034`, `P:1057`, `P:1077`).

**Kết quả cho XS-5a2:** không khai cả bốn bảng thành V1 CRM hoặc V3 chỉ để test qua. Bản đồ đích tách V1 CRM với V3/V2 Core như trên; truy cập cũ được ghi là ngoại lệ chuyển tiếp có điểm kết thúc. Giữ hành vi đếm, lọc quyền và dấu hiệu “tổng không đầy đủ” hiện có (`src/kho_tri_thuc/giao_dien/khung_khai_bao.py:116`, `:145`).

### 6.3. Kiểm tự động nối tiếp XS-5c

Bộ kiểm phải chạy bằng login/role runtime thực, đối chiếu truy cập quan sát được với khai báo:

1. Ghi nhận đối tượng và loại thao tác, không ghi tham số/dữ liệu; bao phủ SQL trực tiếp, hàm, view, trigger và SQL động trong ca kiểm.
2. Phân biệt caller chỉ được gọi contract với truy cập nội bộ hợp lệ của chủ contract; so cả hai với khai báo tương ứng.
3. Kiểm catalog ACL, membership, owner, DEFINER, `search_path` và phụ thuộc để phát hiện đường quyền chưa được ca test đi qua.
4. Test âm: DML/SELECT bảng module khác, giả ngữ cảnh, sai pháp nhân, thiếu quyền nguồn, vượt biến thể tệp và worker quá phạm vi phải bị từ chối.
5. Truy cập mới ngoài khai báo → đỏ. Ngoại lệ cũ khớp chính xác đối tượng/thao tác/lý do; không wildcard schema và không ngoại lệ trong module chuẩn đã nghiệm thu.

Trace chỉ chứng minh các đường đã chạy; phải kết hợp rà soát phụ thuộc và kiểm quyền, không tuyên bố bao phủ mọi truy vấn chỉ từ một lần test.

## 7. Migration theo gói và bảo toàn dữ liệu

**Sổ áp dụng:** `loi.lich_su_doi_cau_truc` lưu `ma_goi`, `so_phien_ban`, `ma_bam`, `ap_dung_luc`, người áp dụng và nguồn lịch sử. Script nằm trong gói sở hữu đối tượng; Core chỉ mang script của `loi*`/`danh_muc`. Việc Core lưu metadata cài đặt module không biến migration module thành migration Core.

Tài khoản cài đặt điều phối dùng role migration đúng khối; role module không được ghi trực tiếp sổ Core. Ghi sổ và thay đổi CSDL phải nhất quán trong transaction khi kỹ thuật cho phép. Thao tác filesystem dùng staging và bước kích hoạt riêng.

Giữ nguyên số/hash lịch sử 67 migration và các hash tương thích đã được xác định. Không sửa migration cũ để “khớp” thiết kế mới; không coi bản ánh xạ là chứng cứ migration đã chạy. Cơ chế hiện có đã kiểm checksum và từ chối hạ phiên bản (`H/postgres.py:217`, `:229`, `:240`).

**Thứ tự phụ thuộc:**

1. Provisioning schema/role/extension được phép.
2. Core: danh tính/MTQ nền → tài liệu, danh mục → module/engine, việc/bus/audit.
3. Gói module dựng phần riêng trên contract Core; G4 triển khai M4 mẫu trước, rồi CRM/M2 theo kế hoạch.
4. Cài mặt công bố và tích hợp sau khi đủ phiên bản phụ thuộc. Phần M4 cần hóa đơn chờ M2, không ngăn cài phần M4 độc lập.
5. Module khác và chuyển dữ liệu theo kế hoạch riêng.

Không tạo vòng phụ thuộc bằng FK từ Core vào schema module. Gói chưa đủ phụ thuộc chưa được kích hoạt phần liên quan.

**Migration dấu ★:** tách câu lệnh theo chủ **định nghĩa cuối cùng**, không theo tên lát hoặc module yêu cầu sửa. Ví dụ MTQ sửa writer CRM/M4 thì phần writer thuộc gói CRM/M4, gọi cổng MTQ Core; không cho role migration Core thay thân hàm module.

Phải đối chiếu cả trigger, policy, ACL và khóa phối hợp sau tách. Đặc biệt M0063 lấy writer đã có guard từ lịch sử; không chỉ lấy định nghĩa khai sinh M0017 (`P:11974`, `P:12088`, `P:12490`). Phụ lục `ANH-XA-MIGRATION.md` của G1a-2 cung cấp ánh xạ đủ 67 dòng, không lặp trong thân này.

**Dựng mới và nâng cấp là hai đường nghiệm thu:** catalog DEMO chỉ ghi 23 migration, chưa đủ version/checksum xác nhận lineage (`J:2764`). M0040 có chặn khi bảng nguồn đã có dữ liệu; không tự điền thời điểm chụp để vượt chặn (`M/sql_review_chep.py:239`). M0013 phải theo COMMON và M0017 theo SQL import hiện hành, không dùng nhầm lineage lịch sử (`P:2994`, `P:8748`, `P:9594`).

Nâng cấp phải kiểm tương thích dữ liệu và việc đang chạy; dùng thay đổi mở rộng, đối chiếu rồi chuyển truy cập. Tắt module giữ dữ liệu, ngừng việc mới và cho xử lý việc đang chạy theo chính sách. Đọc lịch sử vẫn qua quyền; công bố chính thức tuân công tắc, có thể trả `CHO`. Không rollback bằng xóa schema/bảng. Runtime chỉ kiểm tương thích, không tự migrate khi kết nối; cần tách mặc định hiện có tại `H/postgres.py:66`.

## 8. Dọn dẹp và ít tài nguyên

Áp dụng QD-20261026-09: giữ bảng cố định; mỗi phụ lục, BOQ, đợt, phiên bản hoặc lần chạy là thêm dòng. Dòng bị thay thế hết hiệu lực, không sửa đè/xóa bằng chứng. Không đặt mục tiêu gom các hàng việc riêng về XS-2 chỉ để giảm số bảng (`docs/QUYET-DINH.md:357`).

| Loại | Điều kiện dọn trong thiết kế tương lai |
|---|---|
| Lease/khóa giữ | Hết hạn, đã đối chiếu worker/tiến trình; thu hồi có thế hệ, không mở lại việc mù quáng |
| Việc/bước/lần thử kỹ thuật | Đã kết thúc, qua hạn giữ, không còn tranh chấp hoặc tham chiếu bằng chứng; giữ kết luận/audit cần thiết |
| Hộp nhận đã ACK | Qua cửa sổ replay; giữ dấu chống trùng tối thiểu để ACK cũ không thành việc mới |
| Tệp trung gian/cache | Hết hạn, không còn lượt xử lý/duyệt/backup tham chiếu; đối chiếu metadata trước dọn |
| Bản gốc, kết quả được duyệt, audit nghiệp vụ | Không áp chính sách dọn dữ liệu tạm |
| Số đo vận hành | Tổng hợp theo ngày/tuần; dọn chi tiết theo hạn giữ được duyệt |
| CSDL/role test | Xác định chính xác lần test, chủ sở hữu, cụm và phụ thuộc; có xem trước, đối soát và nhật ký |

Catalog ghi **303 CSDL `kho_test_*`, 651 role `ktt_test_*`**, không phải danh sách được phép xóa (`J:26`, `J:1866`). Khi có lát bảo trì được giao: lấy catalog mới; giữ mục không rõ nguồn, có phiên hoặc còn phụ thuộc; xử lý CSDL trước, role sau; chạy tuần tự lô nhỏ, báo đã xử lý/bỏ qua/lỗi và dung lượng thực thu hồi.

Công cụ hiện có mới lọc tên/phiên và thử dọn role, chưa đủ đối chiếu sở hữu/phụ thuộc (`tools/don_csdl_test_cu.py:24`, `:41`, `:74`, `:82`). Không chạy công cụ trong G1; việc thực thi phải tuân ràng buộc không xóa và thẩm quyền bảo trì được giao riêng.

Mỗi lượt test tương lai phải ghi nhận tài nguyên đã tạo và kết quả thu hồi. Pool, worker, concurrency, chỉ mục và hạn giữ chọn theo số đo; không thêm hệ hàng đợi, database hay bảng theo từng lần phát sinh.

## 9. Các điểm cần Anh chọn

Các lựa chọn dưới đây chưa được xem là quyết định đã áp dụng.

| # | Nội dung | Phương án và đánh đổi | Khuyến nghị |
|---|---|---|---|
| 1 | Ranh giới hợp đồng và nghĩa vụ | **A:** khóa hợp đồng chung ở `danh_muc`, phiên bản/tham số/lịch bán ở CRM; độc lập module nhưng cần contract. **B:** giữ các bảng phiên bản/lịch dùng chung; ít chuyển dữ liệu ban đầu nhưng Core giữ nhiều nghiệp vụ | **A**, giữ chủ theo dòng trong giai đoạn chuyển tiếp |
| 2 | Nơi giữ ánh xạ mở che | **A:** tiếp tục do Mask quản lý theo cơ chế hiện có; Core giữ tham chiếu và trạng thái. **B:** đưa vào Core mã hóa, cần thiết kế quyền/khóa/retention riêng | **A** đợt đầu; không sao chép bảng mở che vào Core mặc định |
| 3 | Hạn giữ dữ liệu tạm và số đo | **A:** cấu hình theo loại, đề xuất ban đầu: tệp tạm thành công 24 giờ; lỗi 7 ngày; ACK 30 ngày; số đo chi tiết 90 ngày, tổng hợp 1 năm. **B:** giữ đến khi Admin xử lý; dễ điều tra nhưng tăng tồn đọng | **A**, chỉ cho dữ liệu tạm; không áp vào hồ sơ/bằng chứng nghiệp vụ |
| 4 | Tài nguyên test cũ | **A:** sau xác minh, đề xuất giữ test thành công 7 ngày, lỗi/treo 14 ngày; mục cần điều tra giữ riêng. **B:** Admin quyết từng đợt | **A** cho chính sách tương lai; đợt 303/651 phải kiểm danh sách mới và giao bảo trì riêng |
| 5 | Danh tính production | **A:** tài khoản do Core quản lý. **B:** nối hệ danh tính hiện có, Core giữ ánh xạ người dùng/thành viên | **A** nếu chưa có hệ danh tính tập trung; chọn **B** khi Anh xác định được hệ nguồn |

**Điều kiện hoàn tất bộ CSDL:** thân đặc tả này được review cùng phụ lục ánh xạ 67 migration; chốt chủ dữ liệu còn mơ hồ, các lựa chọn trên và các giới hạn quyền; lead ghép phiếu duyệt CSDL theo CD-029. Lát này chỉ khảo sát tĩnh và soạn tài liệu, không có kết quả test runtime hoặc xác nhận triển khai.