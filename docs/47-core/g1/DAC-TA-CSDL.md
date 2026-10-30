# DAC-TA-CSDL.md — Phân chia CSDL Core và module

**Lát:** G1a-1 · **Ngày:** 30/10/2026 · **Trạng thái:** dự thảo để review và trình Anh duyệt.

**Đề xuất:** dùng một CSDL PostgreSQL chung, tách quyền sở hữu dữ liệu theo khối; giữ MTQ, bus, hàng việc và cấu trúc nghiệp vụ đã đúng; thay các đường truy cập chéo bằng hàm Core hoặc contract công bố có phiên bản.

Đây là đặc tả đích, **chưa phải trạng thái đã triển khai**. Không sửa mã, kết nối CSDL, chạy SQL, migration hoặc dọn dữ liệu trong lát này. G2 chỉ được bắt đầu sau khi đủ ba phiếu CSDL/API/SDK được Anh duyệt và có chỉ đạo mở lại lập trình theo CD-026–030.

## 1. Phạm vi, căn cứ và sơ đồ sở hữu

Áp dụng TL 54 §3–§4, §9, ưu tiên §14; TL 55 §1, §10; CD-017/018/019/021/026–030; QD-20261026-09; khảo sát KS-A…E và RV-* trong `docs/47-core/g0/`.

Đích lưu trữ là CSDL thật chung tại `D:\DU-LIEU-KE-TOAN\postgresql`; kho file tại `D:\DU-LIEU-KE-TOAN\kho-file`; sao lưu tại `D:\DU-LIEU-KE-TOAN\sao-luu`. Đây là vị trí đã chốt, không xác nhận CSDL thật đã được dựng. Không suy tên database, cổng hoặc thông tin đăng nhập từ đường dẫn.

**Ký hiệu căn cứ:** `P` = `src/kho_tri_thuc/ha_tang/pg_migrations.py`; `H/`, `K/`, `M/` lần lượt là các thư mục `ha_tang/`, `k2/`, `m4/` dưới `src/kho_tri_thuc/`; `J` = `docs/47-core/g0/so-lieu-csdl-demo.json`. Dẫn chiếu `P:21` được hiểu là `tệp:dòng` theo quy ước này.

**Căn cứ vòng 2:** `O` = `docs/47-core/g1/RV-G1A-OPUS.md`; `R` = `docs/47-core/g1/RV-G1A.md`; `Q` = `docs/QUYET-DINH.md`; `C` = `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md`; `E` = `docs/46-chuyen-doi-dieu-phoi/KK-MA-HOA-LUU-RIENG.md`. Các quy tắc đích bổ sung dưới đây dẫn nguồn yêu cầu thiết kế, không khẳng định đã có trong mã.

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
| `loi_tai_lieu` — Core | Metadata tài liệu/tệp, biến thể, quyền, kết quả; lần tiếp nhận, vùng tạm và ảnh chụp nguồn dùng chung (§3.5; `O:64`, `R:14`) | Dịch vụ kho/tiếp nhận Core; engine trả kết quả cho Core lưu | Qua dịch vụ/hàm Core; tải bytes cũng kiểm quyền |
| `danh_muc` — Core | Đối tác, dự án, tài khoản; `hop_dong`, `chung_tu` (đầu chứng từ), `hoa_don_danh_tinh`, `khoa_ky`, liên kết/phân bổ chung (§3.6; `O:25`, `O:34`, `R:13`) | Hàm Core V2 có kiểm quyền, chống trùng, khóa kỳ và kiểm tiền chứng từ | Module đọc tập cột được cấp hoặc hàm đọc danh mục; áp RLS |
| `mod_crm` — CRM | Hợp đồng bán: phiên bản/tham số, báo giá, mẫu, dự án bán, ký, lịch nghĩa vụ | Runtime CRM ghi bảng riêng hoặc hàm riêng | CRM đọc riêng; bên khác qua `cong_bo_crm` |
| `mod_m2` — M2 | Quan sát/phiên bản/dòng hóa đơn, con trỏ `hoa_don_trang_thai`, đích hạch toán, công nợ và ngoại lệ; định danh hóa đơn ở Core (`O:34`, `P:5240`) | Runtime M2 | M2 đọc riêng; bên khác qua `cong_bo_m2` |
| `mod_m4` — M4 | Hồ sơ thầu, phụ lục, BOQ, đợt, kiểm tra, nghiệm thu, đối chiếu, Request nháp | Runtime M4 | M4 đọc riêng; bên khác qua `cong_bo_m4` |
| `mod_m0` — M0 | Chỉ `nguon_tu_dong`/cấu hình lịch lấy nguồn riêng M0; không sở hữu metadata tiếp nhận, stage hay registry nguồn (`P:71`, `O:64`, `R:14`) | Runtime M0 ghi cấu hình riêng; tiếp nhận gọi Core V2 | M0 đọc riêng; bên khác qua `cong_bo_m0`, dữ liệu chung qua Core |
| `mod_m1` — M1 | Sao kê/thu chi và đối chiếu thuộc M1 sau khi xác định chủ | Runtime M1; chưa chuyển phần chưa đủ ánh xạ | M1 đọc riêng; bên khác qua `cong_bo_m1` |
| `mod_m3` — M3 | Cơ sở doanh thu, liên kết hóa đơn–hợp đồng và chính sách nghiệp vụ M3 | Runtime M3 | M3 đọc riêng; bên khác qua `cong_bo_m3` |
| `mod_m5` — M5 | Phiếu kho, số lượng, bằng chứng và liên kết dòng thuộc M5 | Runtime M5 | M5 đọc riêng; bên khác qua `cong_bo_m5` |
| `mod_m9` — M9 | Hợp đồng vay, lịch trả nợ và nghiệp vụ khoản vay | Runtime M9 | M9 đọc riêng; bên khác qua `cong_bo_m9` |
| `cong_bo_<module>` — module nguồn | Khung nhìn/hàm đọc có contract; không phải bản sao toàn bộ bảng | Chỉ migration của khối công bố được đổi định nghĩa; runtime không DML | Module được cấp quyền đọc đúng contract |
| `ke_toan_cu` — chủ chuyển tiếp kế toán | Dòng chứng từ, đề xuất, tri thức, phiên/việc duyệt/lô xuất và đối tượng cũ chưa chuyển; không giữ đầu chứng từ hoặc khóa kỳ (`O:26`, `R:13`) | Adapter cũ ghi phần chuyển tiếp; CRM/M9/M5/M2 ghi đầu chứng từ qua V2, không qua quyền adapter (`K/crm.py:262`, `K/vay.py:551`, `P:4205`, `P:5970`) | Qua adapter, hàm hoặc mặt công bố chuyển tiếp |

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
| `latest_observation_id`, `accepted_source_observation_id`, `eligible_content_id` | `quan_sat_moi_nhat_id`, `quan_sat_nguon_chap_nhan_id`, `noi_dung_du_dieu_kien_id` | Con trỏ đặt tại `mod_m2.hoa_don_trang_thai`, không tạo FK Core → M2 (`P:5249`, `O:34`) |
| `source_instance_id`, `acct_id`, `base_deb/base_crd` | `nguon_cai_dat_id`, `ma_tai_khoan`, `no_co_so/co_co_so` | Giữ kiểu text của khóa nguồn/mã tài khoản và đơn vị tiền hiện có (`P:3037`, `P:5248`, `P:859`, `P:868`; `R:15`) |
| `link_purpose`, `allocation_model`, `amount_minor` | `muc_dich_lien_ket`, `mo_hinh_phan_bo`, `so_tien_minor` | Giữ discriminator và đơn vị nhỏ nhất, không đổi thành tiền đã quy đổi (`P:2642`, `P:2686`; `O:20`) |
| `logical_target_id`, `basis_revision_sha256`, `entry_dm` | `dich_logic_id`, `ma_bam_phien_ban_can_cu`, `muc_danh_muc` | Không biến ID đích thành FK sang nghĩa vụ module (`P:2682`, `P:2693`, `P:535`; `O:20`, `O:28`) |

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
| `phien_xac_thuc` | PK `id`; FK người dùng/pháp nhân/module; băm mã bí mật, login được nhận, hạn dùng, thu hồi; `viec_id`/thế hệ giữ việc khi ủy nhiệm | Core phát mã ngẫu nhiên qua kênh riêng; chỉ lưu băm. Mỗi phạm vi module–pháp nhân một mã; worker dùng mã ủy nhiệm theo việc, không dùng lại phiên người dùng (`O:41`, `O:43`) |
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
| `dang_ky_ham_module` | PK `(module, loai_ham, phien_ban_contract)`; FK registry module | Tên schema/hàm, chữ ký, owner và hash gói đã duyệt; chỉ cài đặt ghi. Resolver MTQ/kiểm nghĩa vụ gọi động theo registry, không nhận tên hàm từ client (`O:57`, `O:58`) |

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

**Invariant:** mỗi module là một tiến trình riêng; trên máy triển khai chỉ một `module_phien_chay` hoạt động cho một mã module. Ràng buộc duy nhất có điều kiện cho phiên hoạt động kết hợp lease/thế hệ và CAS; phiên cũ chỉ được thay sau đối chiếu tiến trình thực (`C:334`, `R:16`).

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

### 3.5. Nền tiếp nhận chung — một chủ cho từng bảng

Bản đồ đích sau hiệu chỉnh M0013_COMMON/M0014/M0016; M0 chỉ còn cấu hình tự động riêng tại §1.1, không có bản sao các bảng sau (`O:64`, `R:14`; định nghĩa nguồn `P:3036`, `P:3173`, `P:3208`):

| Chủ duy nhất | Tên nguồn → tên đích (giữ phần tên không ghi đổi) | Khóa/quan hệ và đường ghi |
|---|---|---|
| `loi` | `nguon_instance` → `nguon_cai_dat`; `nguon_profile` → `ho_so_nguon`; `nguon_pham_vi`, `nang_luc_nguon`, `nguon_su_kien_do_luong` | Giữ khóa nguồn text, ID hồ sơ/phạm vi và hash; quyền nguồn do Core kiểm trước định tuyến (`P:3036`, `P:3040`, `P:3050`, `P:3063`, `P:3088`) |
| `danh_muc` | `nguon_master_noi_dung` → `noi_dung_danh_muc_nguon`; `anh_xa_nguon` | Giữ khóa tham chiếu/hash, ánh xạ nguồn tới pháp nhân/danh mục; chỉ Core ghi (`P:3082`, `P:1897`) |
| `loi_tai_lieu` | `tep_tiep_nhan`, `anh_chup_nguon`, `anh_chup_nguon_vai_tro`, `ban_ghi_nguon` | Giữ ID, khóa ảnh chụp/nguồn/vai trò và hash; metadata tiếp nhận dùng chung (`P:3124`, `P:3139`, `P:3153`, `P:1876`) |
| `loi_tai_lieu` | `stage_tin_cay` → `vung_tam_tin_cay`; `lan_tiep_nhan_nguon`, `ket_qua_cuoi_tiep_nhan`, `bien_nhan_thao_tac` | Giữ stage bất biến, khóa chống trùng theo nguồn/không gian, kết quả cuối một lần; finalizer chung gọi qua Core, tiêu thụ nghiệp vụ ở M2/M5 (`P:3173`, `P:3208`, `P:3237`, `P:2653`; `O:64`) |

### 3.6. Định danh, khóa kỳ và liên kết — schema `danh_muc`

Đây là tách cấu trúc đích, không chuyển nguyên FK/trigger hiện có sang Core (`O:25`, `O:34`; FK cũ `P:550`, `P:1018`, `P:2700`):

| Bảng | Khóa/quan hệ chính và giới hạn chủ |
|---|---|
| `chung_tu` | Giữ UUID; khóa cùng pháp nhân; loại, khóa nguồn chống trùng, số tiền/đơn vị nhỏ nhất, tiền tệ/thang tiền, module chủ. CRM/M9/M5/M2 tạo qua V2; dòng hạch toán cũ ở `ke_toan_cu.chung_tu_dong` FK tới đầu này. Không FK về bảng riêng module (`O:26`, `P:207`, `P:4205`, `P:5970`) |
| `hoa_don_danh_tinh` | Giữ UUID, pháp nhân và UNIQUE bộ định danh hóa đơn từ `P:5240`; chỉ giữ định danh/nguồn chung. Ba con trỏ `P:5249`–`P:5251` chuyển sang `mod_m2.hoa_don_trang_thai` với PK/FK `(phap_nhan_id, hoa_don_id)` về Core; quan sát/phiên bản/dòng và các FK giữa chúng ở M2 (`O:34`) |
| `khoa_ky` | Giữ khóa pháp nhân/kỳ (`P:494`), Core là chủ duy nhất. Guard duyệt đầu chứng từ gọi hàm Core kiểm/khóa kỳ trong cùng transaction; adapter cũ cũng gọi hàm này, không đọc bản sao khóa kỳ (`P:855`, `R:13`) |
| `lien_ket_chung_tu` | Giữ UUID; FK chứng từ A/B cùng pháp nhân tới `danh_muc.chung_tu`; nghĩa vụ là `(module_nghia_vu, loai_nghia_vu, nghia_vu_id)`, không FK tới CRM/M9. Căn cứ phiên bản lưu ID + `ma_bam_phien_ban_can_cu`, kiểm qua contract nguồn khi ghi (`O:28`, `O:36`) |
| `lien_ket_phan_bo` | FK tới liên kết/chứng từ Core cùng pháp nhân; đích nghĩa vụ cũng dùng bộ ba trên, kèm `dich_logic_id`, ID phiên bản và mã băm. Bỏ FK tới `lich_tra_no`/phiên bản M9; module chủ kiểm nghĩa vụ trong transaction (§6.2), không chuyển bảng nghĩa vụ M9 vào Core (`P:2700`, `O:28`, `O:30`) |

## 4. Role PostgreSQL và hàm có đặc quyền

### 4.1. Cặp role cho mỗi khối

Với mỗi khối dữ liệu được cài, tạo hai role cố định; mặt công bố dùng ngoại lệ bên dưới (`O:45`, `O:52`):

| Role | Quyền và thuộc tính |
|---|---|
| `vai_chay_<khoi>` | Role nhóm `NOLOGIN`; không superuser, `BYPASSRLS`, `CREATEROLE`, `CREATEDB`; không sở hữu bảng; không DDL |
| `vai_doi_cau_truc_<khoi>` | `NOLOGIN`; sở hữu schema/đối tượng thuộc khối; chỉ tài khoản cài đặt được nhận quyền sử dụng trong phiên bảo trì |

Áp dụng cặp role cho `loi`, `loi_tai_lieu`, `danh_muc`, `mod_*`, `ke_toan_cu`. `cong_bo_x` do gói `mod_x` dựng; schema do `vai_doi_cau_truc_mod_x` quản lý, view do `vai_doc_cong_bo_x` (`NOLOGIN`) sở hữu. Role này chỉ có SELECT các cột nguồn cần thiết, không sở hữu bảng nguồn/không DML/không BYPASSRLS. Không tạo `vai_chay_cong_bo_x` vì không có tiến trình công bố riêng (`O:52`–`O:56`).

| Loại tiến trình | Login CSDL đích | Membership/quyền |
|---|---|---|
| Core và worker Core nội bộ | `dang_nhap_loi` | Ba role `vai_chay_loi`, `vai_chay_loi_tai_lieu`, `vai_chay_danh_muc`; không role chủ (`O:46`) |
| Mỗi module X | `dang_nhap_mod_x` | Chỉ `vai_chay_mod_x`; thêm SELECT contract công bố và EXECUTE hàm Core đúng bản đồ, không membership của module nguồn (`O:47`) |
| Adapter kế toán chuyển tiếp | `dang_nhap_ke_toan_cu` | Chỉ `vai_chay_ke_toan_cu`, EXECUTE V2 và contract được khai báo; không làm login chung của CRM/M2/M5/M9 (`O:15`, `O:47`) |
| Engine, worker trên máy phụ | Không có | Nhận việc/mã ủy nhiệm và trả kết quả qua API Core; không kết nối PostgreSQL (`O:48`, `C:251`) |
| Cài đặt/bảo trì | `dang_nhap_cai_dat` | Login riêng chỉ mở trong phiên bảo trì; quyền DDL hữu hạn theo gói, không dùng cho request nghiệp vụ (`O:49`) |

Mọi membership trên dùng **`INHERIT TRUE, SET FALSE, ADMIN FALSE`** (PG16): quyền được kế thừa, không `SET ROLE`, không tự cấp tiếp. Runtime không nhận membership owner, role công bố hay role kiểm toàn vẹn. **Thiết kế cài đặt để đáp ứng SET FALSE:** provisioning ban đầu do quản trị dựng role và hàm áp gói DEFINER của từng owner; `dang_nhap_cai_dat` chỉ EXECUTE hàm áp gói đã kiểm nguồn/hash trong cửa sổ bảo trì, không nhận SQL tùy ý từ runtime. DDL chạy trong hàm với đúng owner khối ngay khi tạo, không dựa vào `SET ROLE`/`ALTER OWNER` của login cài đặt. Đối tượng thuộc role kiểm/công bố cũng do provisioning quản trị dựng hoặc hàm áp gói của đúng owner tạo; cài đặt không là superuser (`O:49`, `O:51`; thiết kế đích, chưa có mã).

Mật khẩu do Core đọc từ kho bí mật ngoài thư mục phần mềm tại `D:\DU-LIEU-KE-TOAN\bi-mat\`, bảo vệ theo tài khoản dịch vụ; Core trao đúng mật khẩu login cho tiến trình con qua stdin/handle kế thừa có kiểm soát, không qua biến môi trường, dòng lệnh, manifest hoặc log. Mật khẩu cài đặt chỉ do chức trách bảo trì giữ, không trao module; engine/máy phụ không nhận mật khẩu CSDL (`O:50`, `Q:387`).

View `cong_bo_*` bật `security_barrier`, **không** bật `security_invoker`; quyền bảng nguồn của owner view bị giới hạn bởi policy riêng cho `vai_doc_cong_bo_x`, vẫn xác minh mã phiên, pháp nhân và quyền đọc contract. Module nhận chỉ SELECT view được cấp; hàm công bố cũng kiểm contract, không cho tự đọc bảng nguồn (`O:53`–`O:55`).

Các role `app_web`, `app_doc`, `app_ke_toan`, `app_cong_ai` hiện là role nhóm NOLOGIN; quyền cũ có phạm vi rộng (`J:28`; `P:783`). Chúng chỉ là lớp tương thích trong chuyển tiếp. Phải kiểm cả membership, khả năng `SET ROLE`, quyền kế thừa và owner thực tế trước khi cấp role mới; không dùng `app_web` làm nhóm thừa hưởng mọi module.

### 4.2. Hàm `SECURITY DEFINER` và PUBLIC

Mỗi hàm phải có chủ, chữ ký, người được gọi và tài nguyên chạm tới:

- Chủ hàm là role sở hữu của khối, không phải login runtime hoặc superuser; hàm kiểm toàn vẹn dùng role kiểm riêng tại §5, owner view chỉ đọc theo §4.1 (`O:32`, `O:54`).
- `search_path` cố định: `pg_catalog`, các schema tin cậy tối thiểu, `pg_temp` cuối; định danh đầy đủ đối tượng. Runtime không có `CREATE` trên schema tin cậy.
- Chỉ cấp `EXECUTE` đúng chữ ký cho đúng role. Hàm nội bộ không công khai; wrapper phải kiểm danh tính, module, pháp nhân, hành động và căn cứ.
- Bảng nghiệp vụ thuộc pháp nhân bật RLS và `FORCE ROW LEVEL SECURITY`; không dùng quyền owner để thay kiểm nghiệp vụ. Bảng xác thực/quản trị toàn cục có chính sách riêng, tránh vòng đệ quy khi tra quyền.
- Trong schema đích do hệ thống sở hữu: thu hồi quyền PUBLIC không cần thiết trên schema/bảng/sequence/hàm; thiết lập default privileges theo **từng role tạo đối tượng**. Với schema dùng chung/extension hiện hữu, chỉ thay sau khi kiểm phụ thuộc.

Catalog DEMO ghi 100/128 bảng bật RLS nhưng 0 FORCE, 120 hàm DEFINER và 167 hàm có EXECUTE mặc định PUBLIC; chưa đủ owner/ACL chi tiết để kết luận quyền hiệu lực (`J:2663`, `:2707`, `:2740`, `:2742`). Các số này là đầu vào rà soát, không phải danh sách thu hồi hàng loạt.

CRM G hiện nhận kết nối chủ bảng (`K/crm_mau.py:111`, `:126`). Đường này phải chuyển sang runtime và hàm được cấp quyền trước nghiệm thu Core.

**Core gọi module:** qua `loi.dang_ky_ham_module`, chọn động hàm theo module/loại/phiên bản đã duyệt; registry chỉ cài đặt được sửa. Resolver MTQ và hàm kiểm nghĩa vụ là `SECURITY DEFINER`, owner thuộc module nguồn, không INVOKER để tránh chạy với quyền owner Core. Chỉ cổng Core nội bộ được EXECUTE; không cấp login Core quyền đọc bảng module. Bên nhận kiểm mã phiên/login gốc (`session_user`), module được ủy nhiệm và pháp nhân; không lấy `current_user` sau DEFINER làm danh tính người dùng. Chưa cài/chưa có contract → `CHO`, transaction ghi liên quan không commit dở (`O:57`–`O:60`, `O:43`).

## 5. RLS theo pháp nhân và cùng một cổng kiểm quyền

Mỗi transaction nghiệp vụ phải:

1. Core cấp mã phiên bí mật hoặc mã ủy nhiệm việc theo §3.1; CSDL xác minh trước thao tác (`O:43`).
2. Mở transaction bằng role đúng khối.
3. Đặt ngữ cảnh bằng `SET LOCAL` hoặc `set_config(..., true)`.
4. Thực hiện thao tác qua kiểm phạm vi, quyền module, MTQ và quyền hồ sơ/nội dung.
5. Commit/rollback; không để ngữ cảnh yêu cầu trước rò sang kết nối tái sử dụng.

Giữ các khóa ngữ cảnh `ktt.*` đang dùng khi còn phù hợp, không thêm namespace chỉ để đổi tên. Mẫu transaction-local đã có tại `K/crm_mau.py:135`.

**GUC không tự chứng minh danh tính.** Hàm DEFINER băm mã bí mật nhận qua ngữ cảnh transaction và đối chiếu `loi.phien_xac_thuc`: còn hạn/chưa thu hồi, đúng `session_user`, module, pháp nhân và phạm vi hành động/việc. Runtime không SELECT/DML bảng phiên; mã không vào log/trace/audit. `ktt.nguoi_dung_id`, `ktt.nguoi_dung_dang_nhap` chỉ là thông tin đối chiếu, sửa chúng không đổi danh tính đã xác minh. `ktt.ngay_hieu_luc` do Core xác định từ thời gian/ngày nghiệp vụ được duyệt, hàm CSDL đối chiếu căn cứ phiên; không tin ngày module tự đặt. G2 phải kiểm cả giả mã, đổi login/module/pháp nhân, mã hết hạn/thu hồi và mã việc sai thế hệ (`P:1222`, `P:1245`; `O:41`–`O:44`).

RLS cho cả `USING` và `WITH CHECK`; không cho đổi `phap_nhan_id` để chuyển hồ sơ. Thiếu/sai ngữ cảnh thì từ chối. Dữ liệu toàn cục phải được phân loại rõ; `phap_nhan_id IS NULL` không phải cửa đọc toàn hệ thống.

MTQ tiếp tục quyết định hành động, hạn mức, phạm vi và quy tắc kiểm/duyệt. Đối tượng nhiều pháp nhân phải đạt quyền ở **mọi** pháp nhân; hỗn hợp bật/tắt MTQ bị chặn theo QD-20261026-10 (`docs/QUYET-DINH.md:365`). Đường quyền cũ chỉ được giữ cho đối tượng chuyển tiếp đã khai báo, không tự lan sang module mới.

**Tách RLS và quyền hành động:** RLS lọc theo pháp nhân từ phiên đã xác minh (vùng prePN dùng quyền nguồn); không dùng lại `ktt_duoc(pn,'M1')` làm bộ lọc tính tổng. MTQ là nguồn quyết định hành động/hạn mức/phạm vi; kiểm quyền nội dung bổ sung ở cổng đọc. Không tạo nguồn quyết định hành động thứ hai trong policy (`P:1186`, `O:17`).

**Policy kiểm toàn vẹn C2:** mỗi khối cần tính tổng có `vai_kiem_toan_ven_<khoi>` NOLOGIN, không BYPASSRLS, không membership runtime; chỉ SELECT/khóa dòng cần thiết và sở hữu hàm kiểm hẹp. Policy riêng `TO vai_kiem_toan_ven_<khoi>` trên bảng tham gia tổng chỉ lọc pháp nhân đã xác minh trong ngữ cảnh, **không lọc module/người/quyền M1**, áp cả khi FORCE RLS. Nếu có policy RESTRICTIVE, policy đó cũng chỉ ràng buộc pháp nhân cho role kiểm để không làm thiếu tổng. Hàm nội bộ không trả dòng/tổng nhạy cảm ra caller; chỉ trả kết luận/mã lỗi, EXECUTE chỉ cho cổng ghi/resolver đã duyệt. Core tính đủ tiền chứng từ; module chủ tính đủ nghĩa vụ qua hàm tổng liên kết Core nội bộ cùng policy này, không SELECT bảng chéo (`P:1270`, `O:29`–`O:33`).

**Test âm bắt buộc cho G2:** người không có quyền M1 nhưng có quyền tạo liên kết nghiệp vụ hợp lệ thử nối thêm 30 sau khi đã nối 80 bằng dòng bị che. Chạy hai ca độc lập: chứng từ giới hạn 100/nghĩa vụ đủ lớn, rồi nghĩa vụ giới hạn 100/chứng từ đủ lớn; mỗi ca đều phải từ chối dù chỉ thấy một phần dữ liệu. Ca cạnh tranh riêng bắt đầu từ 0, giới hạn 100: hai transaction 60 + 60 không được cùng commit. Thiếu quyền hành động, sai pháp nhân hoặc giả mã phiên đều từ chối, không lộ dòng/tổng bị che; kiểm cả giảm sức chứa nghĩa vụ và sửa/hủy liên kết dưới cùng khóa (§6.2). Đây là ca cần chạy sau, chưa có kết quả runtime (`O:32`, `O:33`).

Dữ liệu tiếp nhận chưa xác định pháp nhân nằm trong `loi_tai_lieu.vung_tam_tin_cay`/`lan_tiep_nhan_nguon`, kiểm bằng quyền nguồn/lần tiếp nhận; sau định tuyến mới vào dữ liệu nghiệp vụ. Core sở hữu, M0 gọi V2; không áp một policy pháp nhân giả cho toàn bộ đầu vào này (`P:3036`, `P:3063`, `P:3173`, `P:3208`; `O:64`, `R:14`).

**Job/worker:** lưu người tạo, pháp nhân, module và phạm vi ủy nhiệm; kiểm lại quyền khi nhận việc và trước ghi/kết quả/tác động ngoài. Quyền bị thu hồi phải chặn hoặc chuyển chờ có lý do. Máy xử lý phụ chỉ nhận đầu vào/kết quả của việc được giao, không đọc bảng nghiệp vụ hoặc giữ khóa mã hóa.

**Download:** tra tệp từ tài liệu/kết quả được phép, kiểm biến thể và trạng thái duyệt trước trả bytes. Không có đường tắt vì biết ID, hash hoặc đường dẫn.

**Bổ sung lead sau review Opus vòng 2 (a):** mọi role làm chủ hàm DEFINER (`vai_doi_cau_truc_*`, `vai_kiem_toan_ven_*`, resolver module) phải có policy tường minh theo pháp nhân đã xác minh; dưới FORCE RLS, thiếu policy thì role đó thấy 0 dòng.
- **Khóa dòng bằng `SELECT … FOR UPDATE`:** cần quyền UPDATE (một cột kỹ thuật) và policy UPDATE USING.
- **Nếu không cấp được:** dùng `pg_advisory_xact_lock` theo id, đúng thứ tự khóa ở §6.2.

**Bổ sung lead sau review Opus vòng 2 (b):** mã phiên đặt bằng tham số bind; tắt ghi giá trị tham số trong log (`log_parameter_max_length = 0`, `log_parameter_max_length_on_error = 0`).
- Không lưu kết quả xác minh vào GUC hay bảng tạm mà runtime ghi được.
- Mỗi lần cần thì xác minh lại từ băm (hàm STABLE, tra có chỉ mục).

**Xuất riêng một công ty — CD-021:** chỉ Admin khởi tạo với pháp nhân rõ ràng; công cụ xuất qua bản đồ sở hữu, gồm dữ liệu module, file, audit, ánh xạ và phần danh mục cần thiết. Dùng snapshot/mốc nhất quán CSDL–file; đối chiếu số dòng, tổng tiền theo đơn vị, hash và tham chiếu; thử phục hồi vào đích riêng trên DEMO. Không mang dữ liệu công ty khác, khóa hay bí mật phiên vào gói. Không dùng backup cả database rồi coi đó là bản xuất một pháp nhân.

Role xuất `vai_xuat_phap_nhan` là NOLOGIN, chỉ SELECT theo bản đồ sở hữu, không BYPASSRLS/owner/DML. Core mở phiên xuất có mã ủy nhiệm riêng và pháp nhân cố định; mọi policy FORCE RLS của đường xuất xác minh mã này, không tin GUC pháp nhân tùy ý. Chỉ tác vụ xuất Core được kế thừa role trong phiên xuất do quản trị cấp hữu hạn; không cấp module. Ghi audit người yêu cầu, pháp nhân, mốc và kết quả. Đối tượng nhiều pháp nhân phải kiểm quyền **mọi** pháp nhân theo QD-10; gói một công ty chỉ chứa phần tách riêng đã xác định, giữ tham chiếu thiếu và báo chặn nếu không thể tách mà vẫn toàn vẹn, không tự mang toàn bộ đối tượng chung sang (`O:61`–`O:63`, `Q:365`).

### 5.1. Mã hóa cột — phân khối và quyền giải mã

Nhóm A đã được duyệt, B chờ, C (tiền/ngày/mã nội bộ) giữ rõ; không hỏi lại danh sách. Bảng sau ánh xạ 10 nhóm A sang chủ đích; các path JSON phải chốt theo danh mục trường trước G2, chưa khẳng định đã mã hóa (`Q:376`, `Q:386`; `E:13`–`E:32`):

| Nhóm/cột nguồn nhạy cảm | Khối giữ bản mã đích | Quyền lấy bản rõ |
|---|---|---|
| 1–4: `doi_tac.cccd_mh`, `doi_tac_dinh_danh.gia_tri*`, `tai_khoan_ngan_hang.stk_mh`, MST cá nhân | `danh_muc`; riêng `nhan_vien.cccd_mh/stk_mh` giữ `ke_toan_cu` theo M0004 | Chỉ dịch vụ giải mã Core, MTQ cho đúng nghiệp vụ/pháp nhân; không SELECT bản rõ qua V3 (`E:13`–`E:16`) |
| 5–7: tài khoản trong ánh xạ tiền, điều kiện học sao kê, raw/chứng từ/dòng/tri thức kho cũ | `ke_toan_cu`; phần đầu chứng từ đã tách ở `danh_muc.chung_tu`, bản nguồn tiếp nhận ở `loi_tai_lieu` | Core giải mã theo chủ bảng; rà cả bản sao/path, giữ khóa tra và hash logic (`E:17`–`E:19`, `E:25`) |
| 8: SĐT/email trong `crm_bao_gia_phien_ban.du_lieu`, `crm_hd_soan_phien_ban.du_lieu`, `crm_hd_ky.tom_tat` | `mod_crm` | Core giải mã cho yêu cầu CRM có MTQ/quyền hồ sơ; chỉ path cá nhân (`E:20`) |
| 9: địa chỉ/giấy tờ ở `tham_so`, `trich_xuat`, `tham_so_lich_su` | `mod_m4` | Core giải mã cho yêu cầu M4 được phép, gồm bản lịch sử; tiền/ngày giữ rõ (`E:21`) |
| 10: `mask_bi_danh.gia_tri_that_mh` | `ke_toan_cu` cho bảng cũ, chỉ adapter cổng Mask dùng; danh mục Mask v2 vẫn do Mask quản lý ngoài CSDL này | Chỉ cổng Mask hiện có mở che, không sao chép ánh xạ sang Core/engine mới (`E:22`, `O:84`) |

Role `vai_chay_loi` phục vụ cổng giải mã Core được nhận bản mã qua hàm đọc hẹp của khối chủ sau xác thực/MTQ/quyền nội dung và audit ID; role module, `vai_doc_cong_bo_x`, role kiểm toàn vẹn, role xuất và engine/máy phụ không được giải mã tùy ý. PostgreSQL không giữ khóa/không có hàm giải mã nhận khóa SQL; quyền role chỉ cho truy cập bản mã, khả năng giải mã nằm tại dịch vụ Core (riêng mở che tại Mask). Đây là điều chỉnh thiết kế so với phương án bind khóa vào pgcrypto trước đây, để đáp ứng `O:65`–`O:68`; dùng lại cổng mã hóa chung, không tạo bộ che riêng (`E:36`, `E:40`).

Khóa cột bọc DPAPI theo tài khoản dịch vụ, ở `D:\DU-LIEU-KE-TOAN\bi-mat\`, tách khóa backup. **Không truyền khóa qua GUC hoặc tham số SQL**, kể cả bind; mã hóa/giải mã trong cổng hạ tầng Core, khóa chỉ ở RAM của dịch vụ được phép. Lưu bản mã + phiên bản khóa; tra cứu bằng HMAC khóa độc lập, bảo toàn miền UNIQUE/chuẩn hóa, không dùng hash trần cho số tài khoản. Chỉ hiện bốn số cuối; xem đủ cần quyền/audit, log không chứa bản rõ/khóa. G2 phải kiểm canary ở log thành công/lỗi, đổi khóa và khôi phục; thuật toán/adapter của cổng dùng chung cần lead chốt ở lát API/SDK, chưa triển khai (`Q:387`, `E:32`, `E:38`, `O:68`).

## 6. Quy tắc ghi/đọc giữa module và xử lý XS-5a2

### 6.1. Ranh giới truy cập

“Không SQL chéo schema” nghĩa là module không trực tiếp đọc/ghi **bảng riêng** của khối khác. Các giao diện được phép phải khai báo cụ thể: hàm Core V2, danh mục V3 và mặt công bố V4.

- DML chỉ trong V1; dữ liệu chung chỉ ghi qua hàm Core.
- Đọc module khác chỉ qua `cong_bo_*`; không dùng view trong schema mình để che một truy vấn trái phép.
- Hàm công bố do module nguồn quản lý đọc bảng của chính nguồn; không kéo ngược bảng riêng module nhận.
- FK module → định danh Core được phép theo bản đồ. Core không tạo phụ thuộc bắt buộc tới bảng riêng module tùy chọn.
- Không FK giữa hai module: M4/M3 chỉ FK tới `danh_muc.hoa_don_danh_tinh`; phiên bản/quan sát/dòng hóa đơn lưu `(id, ma_bam)` kiểm qua `cong_bo_m2` khi ghi. M3 ghim phiên bản hợp đồng CRM tương tự qua `cong_bo_crm`; kiểm tồn tại, cùng pháp nhân, trạng thái/đơn vị và hash, không tự thay bằng bản mới nhất (`K/sql_ghi_nhan_chung.py:252`, `K/sql_ghi_nhan_chung.py:285`, `K/sql_m3.py:36`, `K/sql_m3.py:81`; `O:34`–`O:37`).
- Thiếu dữ liệu trả `CHO` có lý do; sai quyền trả lỗi quyền. Không đánh đồng hai trường hợp.
- Contract công bố hoạt động bằng dữ liệu bền vững và đối tượng CSDL đã cài, không đòi tiến trình nguồn đang chạy.

Mỗi contract ghi phiên bản, trường/đơn vị/trạng thái, quyền, quy tắc phiên bản hiện hành và điều kiện công bố. Thay đổi phá tương thích dùng phiên bản mới; không thay âm thầm bản cũ.

Hàm công bố hóa đơn hiện có cần được giữ hành vi và chuyển mặt truy cập sang `cong_bo_m2`, không viết lại nội dung: đang công bố qua `master.hoa_don_cong_bo`, có kiểm quyền, `CHO`, phiên bản nguồn và trạng thái thiếu căn cứ tiền (`K/sql_cong_bo_hoa_don.py:15`, `:20`, `:38`, `:56`). Gói M2 sở hữu cả phần công bố và yêu cầu quyền liên quan.

### 6.2. Chốt đề xuất cho bốn bảng CRM đang đếm

CRM đang dùng phiên bản hợp đồng, lịch thu và liên kết chung trong truy vấn/hàm nghiệp vụ; khung gọi lại dịch vụ danh sách (`K/crm_s1.py:87`, `:122`, `:247`; `P:1018`; `src/kho_tri_thuc/giao_dien/khung_khai_bao.py:119`, `:143`).

| Bảng hiện có | Chủ/đích đề xuất | CRM truy cập thế nào; có cần công bố? |
|---|---|---|
| `master.hop_dong` | `danh_muc.hop_dong` giữ định danh chung; trạng thái/thuộc tính bán hàng do CRM quản lý | CRM đọc phần danh mục qua V3, ghi qua V2. Thông tin nghiệp vụ bán hàng công bố cho bên khác qua `cong_bo_crm` |
| `master.hop_dong_phien_ban` | Phiên bản bán hàng → `mod_crm.hop_dong_phien_ban`; dòng chưa phân loại → `ke_toan_cu.hop_dong_phien_ban_chuyen_tiep` | CRM đọc riêng V1; M3/M4/module khác dùng `cong_bo_crm`. Hai bảng đích riêng, mỗi bảng một chủ; không ép dòng chưa rõ vào CRM (`P:286`, `O:15`) |
| `master.lich_thu` | Lịch nghĩa vụ bán hàng → `mod_crm.lich_thu` | CRM đọc V1; bên khác qua `cong_bo_crm`, giữ ID và khóa nghĩa vụ |
| `kho.lien_ket_chung_tu` | `danh_muc.lien_ket_chung_tu`, FK chứng từ chỉ về Core; bộ ba nghĩa vụ không FK (§3.6) | Ghi qua V2; đọc mặt V3/hàm tổng hợp được cấp. CRM/M9 kiểm nghĩa vụ riêng qua registry cùng transaction (`O:28`–`O:30`) |

`mod_crm.hop_dong_tham_so` đi cùng phiên bản CRM; phần chưa phân loại giữ riêng tại `ke_toan_cu.hop_dong_tham_so_chuyen_tiep`. “Chủ theo dòng” chỉ mô tả dữ liệu nguồn cũ, **không** là mô hình sở hữu đích: đối chiếu ID/trạng thái/quan hệ rồi nạp mỗi dòng đúng một bảng chủ, chưa rõ thì cách ly chuyển tiếp và chưa công bố nghiệp vụ. Đây là tách bảo toàn dữ liệu M0004, không sao chép một bảng sang nhiều chủ (`P:286`, `O:15`).

**Transaction liên kết:** (1) cổng Core xác thực/MTQ, kiểm cùng pháp nhân/tiền tệ, khóa các đầu chứng từ theo thứ tự ID; (2) gọi động hàm DEFINER module chủ qua registry để khóa nghĩa vụ theo bộ ba và kiểm ID + mã băm qua `cong_bo_crm`/`cong_bo_m9`; (3) ghi liên kết/phân bổ rồi kiểm cuối trước commit: Core kiểm tổng không vượt tiền chứng từ, module chủ kiểm tổng không vượt nghĩa vụ bằng policy toàn vẹn §5. Mọi bước trong **một transaction/kết nối**, không gọi HTTP để kiểm tiền. Module không có/chưa đủ căn cứ → `CHO` và không commit liên kết. Trình tự khóa chứng từ → nghĩa vụ thống nhất cả tạo/sửa/hủy và giảm sức chứa nghĩa vụ; thao tác giảm không được bỏ qua các liên kết đã có. Hàm tổng Core nội bộ chỉ cấp cho role kiểm của module được registry chỉ định, không trả tổng ẩn cho runtime. Không FK tới `lich_thu`, `hop_dong_phien_ban` hoặc `lich_tra_no`; không tin bộ ba do caller khai khi chưa resolver kiểm chứng (`P:1034`, `P:1057`, `P:1077`, `P:2700`; `O:28`–`O:33`, `O:58`).

**Kết quả cho XS-5a2:** không khai cả bốn bảng thành V1 CRM hoặc V3 chỉ để test qua. Bản đồ đích tách V1 CRM với V3/V2 Core như trên; truy cập cũ được ghi là ngoại lệ chuyển tiếp có điểm kết thúc. Giữ hành vi đếm, lọc quyền và dấu hiệu “tổng không đầy đủ” hiện có (`src/kho_tri_thuc/giao_dien/khung_khai_bao.py:116`, `:145`).

### 6.3. Kiểm tự động nối tiếp XS-5c

Bộ kiểm phải chạy bằng login/role runtime thực; **ACL và tập đối tượng hàm đặc quyền chạm tới là cổng chính**, trace bổ sung theo CD-018 (`O:18`, `C:219`):

1. So catalog ACL/membership (`INHERIT/SET/ADMIN`), owner, DEFINER, `search_path`, policy/FORCE RLS và FK với bản đồ; kiểm tập đối tượng **từng** hàm DEFINER/view/trigger/SQL động có thể chạm. Quyền vượt khai báo → đỏ dù trace chưa chạy tới (`O:18`, `O:51`).
2. Phân biệt quyền caller gọi contract với truy cập nội bộ của owner contract; kiểm registry không nhận tên hàm tùy ý, view công bố chỉ SELECT với `security_barrier` (`O:52`, `O:57`).
3. Ghi trace đối tượng/loại thao tác trong ca kiểm, không ghi tham số/dữ liệu/mã bí mật; đối chiếu với khai báo để tìm đường thiếu trong phân tích tĩnh (`O:18`, `O:43`).
4. Test âm: DML/SELECT bảng module khác, `SET ROLE`/giả phiên, sai pháp nhân, thiếu quyền nguồn, vượt biến thể tệp và worker quá phạm vi bị từ chối; thêm kiểm tiền dưới FORCE RLS §5 và ghim hash sai/contract thiếu không được commit (§6.1; `O:33`, `O:36`).
5. Truy cập mới ngoài khai báo → đỏ. Ngoại lệ cũ khớp chính xác đối tượng/thao tác/lý do; không wildcard schema và không ngoại lệ trong module chuẩn đã nghiệm thu.

Trace chỉ chứng minh các đường đã chạy; phải kết hợp rà soát phụ thuộc và kiểm quyền, không tuyên bố bao phủ mọi truy vấn chỉ từ một lần test.

## 7. Migration theo gói và bảo toàn dữ liệu

**Sổ áp dụng:** `loi.lich_su_doi_cau_truc` lưu `ma_goi`, `so_phien_ban`, `ma_bam`, `ap_dung_luc`, người áp dụng và nguồn lịch sử. Script nằm trong gói sở hữu đối tượng; Core chỉ mang script của `loi*`/`danh_muc`. Việc Core lưu metadata cài đặt module không biến migration module thành migration Core.

Tài khoản cài đặt điều phối qua hàm áp gói của đúng owner theo §4.1, không `SET ROLE`; role module không được ghi trực tiếp sổ Core. Ghi sổ và thay đổi CSDL phải nhất quán trong transaction khi kỹ thuật cho phép; thao tác filesystem dùng staging và bước kích hoạt riêng (`O:49`, `O:51`).

Giữ nguyên số/hash lịch sử 67 migration và các hash tương thích đã được xác định. Không sửa migration cũ để “khớp” thiết kế mới; không coi bản ánh xạ là chứng cứ migration đã chạy. Cơ chế hiện có đã kiểm checksum và từ chối hạ phiên bản (`H/postgres.py:217`, `:229`, `:240`).

**Thứ tự phụ thuộc:**

| Bước | Gói / phạm vi | Điều kiện và cách tổ chức |
|---|---|---|
| 1 | **Core — nền** | Role/login/schema → danh tính/pháp nhân/phiên → audit/lịch sử migration → registry module/engine/hàm. Audit và registry có trước MTQ; chưa gắn FK tới module (`O:19`, `O:45`, `O:58`). |
| 2 | **Core — dịch vụ chung** | MTQ/công tắc → tài liệu/tiếp nhận → danh mục (đầu chứng từ, định danh hóa đơn, khóa kỳ, liên kết không FK nghĩa vụ) → sổ cổng/việc/bus/số đo; dựng policy toàn vẹn và cổng V2. Registry mới chỉ có giao diện, không yêu cầu module đã cài (`O:25`, `O:32`, `O:34`, `O:64`). |
| 3 | **`mod_m4` — mẫu đầu tiên G4** | Dựng phần riêng + `cong_bo_m4`/resolver. FK hóa đơn chỉ về định danh Core; ID + mã băm nguồn kiểm qua công bố khi ghi. Chưa có M2 → `CHO`, không chặn dựng gói (`O:18`, `O:35`, `O:60`). |
| 4 | **`mod_crm`** | Dựng nghiệp vụ bán/phiên bản/lịch thu + `cong_bo_crm`/resolver MTQ/kiểm nghĩa vụ; đăng ký contract sau khi ACL/owner đạt (`O:28`, `O:57`). |
| 5 | **`mod_m2`** | Dựng quan sát/phiên bản/dòng/con trỏ trạng thái + `cong_bo_m2`/resolver; FK định danh về Core. M4 chỉ kích hoạt phần cần M2 sau khi contract đúng phiên bản sẵn sàng (`O:34`, `O:36`). |
| 6 | **Module khác** | `mod_m0`, `mod_m5`, `mod_m3`, `mod_m9`, `mod_ke_toan_cu` theo phụ thuộc contract; M3 ghim CRM/M2, M9 đăng ký kiểm nghĩa vụ. Không đưa lineage M1/M9 ngoài chuỗi vào gói Core (`O:37`, `O:58`; `P:2994`, `P:9596`). |

Thứ tự này giống phụ lục §2. Mỗi gói tự dựng phần công bố/resolver, không trì hoãn mọi công bố đến cuối. Core không FK/phụ thuộc DDL vào module; không còn FK M4 → M2 hoặc liên kết Core → CRM/M9. Thiếu contract chỉ chặn thao tác/kích hoạt liên quan, không phá dựng CSDL mới (`O:19`, `O:28`, `O:34`).

**Migration dấu ★:** tách câu lệnh theo chủ **định nghĩa cuối cùng**, không theo tên lát hoặc module yêu cầu sửa. Ví dụ MTQ sửa writer CRM/M4 thì phần writer thuộc gói CRM/M4, gọi cổng MTQ Core; không cho role migration Core thay thân hàm module.

Phải đối chiếu cả trigger, policy, ACL và khóa phối hợp sau tách. Đặc biệt M0063 lấy writer đã có guard từ lịch sử; không chỉ lấy định nghĩa khai sinh M0017 (`P:11974`, `P:12088`, `P:12490`). Phụ lục `ANH-XA-MIGRATION.md` của G1a-2 cung cấp ánh xạ đủ 67 dòng, không lặp trong thân này.

**Hành vi validator đích M0065/M0067:** giữ đồng thời nhánh NGUON (chuẩn hóa khóa, đúng một ứng viên/ánh xạ hiện hành, kiểm mọi pháp nhân và khóa hàng) của M0067 và ghim/kiểm quan hệ HOP_DONG/DU_AN khi cấp phạm vi của M0065, kể cả chưa tick. Core giữ guard chung; giải/ghim CRM gọi resolver CRM qua registry. Gói đích chứa một định nghĩa hợp nhất, không lấy nguyên bản M0067 dựng từ M0049 để làm mất B3; G2 phải kiểm âm cả nguồn mơ hồ/sai pháp nhân và quan hệ CRM sai/đổi sau ghim. Đây là yêu cầu bảo toàn đích, không kết luận runtime hiện tại đã giữ cả hai (`P:12519`, `P:12525`, `P:12539`; `K/sql_mtq_lien_module.py:24`, `:108`, `:117`; `R:48`).

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

Theo ưu tiên review Opus, chỉ còn ba câu quyết định; cơ chế phiên ở §3–§5 đang đặc tả theo phương án A để review, chưa xem là Anh đã chọn (`O:76`–`O:84`).

| # | Nội dung | Phương án và đánh đổi | Khuyến nghị |
|---|---|---|---|
| 1 | CSDL có phải chặn module chạy riêng tự nhận là người khác? | **A:** có, Core cấp mã phiên bí mật, CSDL kiểm; G2 thêm công. **B:** coi module nội bộ tin cậy, chỉ chặn sai pháp nhân; rủi ro giả người dùng bằng GUC | **A**, cơ chế S1 đã cụ thể ở §5; B nếu chọn phải sửa lại thiết kế trước G2 (`O:78`–`O:80`) |
| 2 | Hạn giữ dữ liệu tạm, số đo và tài nguyên test | **A:** tệp tạm thành công 24 giờ/lỗi 7 ngày; ACK 30 ngày; số đo chi tiết 90 ngày/tổng hợp 1 năm; test thành công 7 ngày/lỗi 14 ngày. **B:** Admin quyết từng đợt, dễ điều tra nhưng tăng tồn đọng | **A**, chỉ dữ liệu tạm, giữ riêng ca điều tra; đợt 303/651 cần kiểm danh sách và giao bảo trì riêng, không phải lệnh xóa (`O:81`, `J:26`, `J:1866`) |
| 3 | Danh tính đăng nhập thật | **A:** Core quản lý tài khoản. **B:** nối hệ danh tính hiện có, Core giữ ánh xạ; giảm quản trị trùng nhưng cần xác định hệ nguồn | **A** nếu chưa có hệ tập trung; **B** khi Anh xác định hệ nguồn (`O:82`) |

**Báo:** ranh giới hợp đồng/phiên bản/nghĩa vụ theo §6.2 và liên kết chung Core đã có căn cứ, không hỏi lại; nguyên tắc thêm dòng giữ nguyên (`C:217`, `Q:357`, `O:83`). **Báo:** ánh xạ mở che tiếp tục do Mask quản lý, Core chỉ tham chiếu; chi tiết vòng đời/quyền mở che chuyển phiếu engine/SDK (`O:84`, `E:22`). Nhóm mã hóa A đã duyệt tại `Q:386`, không đưa thành câu chọn mới.

**Tồn đọng có phạm vi:** phân biệt `lan_thu` (lần thử việc) với `lich_thu` (nghĩa vụ CRM); giữ schema `loi` theo đề gốc, đề nghị lead cân nhắc đổi riêng cột tham số `loi` → `cot_loi` ở lát tên để tránh đọc nhầm. `pgcrypto` nếu còn cần phải ở schema extension riêng có ACL/search_path, chốt trong lát hạ tầng; không dùng để truyền khóa SQL theo §5.1. Tên tiếng Anh được review nêu đã ánh xạ tại §2, thứ tự audit/registry đã sửa §7, không để hai việc này tồn đọng (`O:20`, `O:70`–`O:74`).

**Điều kiện hoàn tất bộ CSDL:** thân đặc tả này được review cùng phụ lục ánh xạ 67 migration; chốt chủ dữ liệu còn mơ hồ, các lựa chọn trên và các giới hạn quyền; lead ghép phiếu duyệt CSDL theo CD-029. Lát này chỉ khảo sát tĩnh và soạn tài liệu, không có kết quả test runtime hoặc xác nhận triển khai.

## Vòng 2 — đã xử lý

| Mã phát hiện → căn cứ | Chỗ sửa trong thân đặc tả |
|---|---|
| C1 — `O:25` | §1.1, §3.6, §6.2: đầu chứng từ Core, bộ ba nghĩa vụ không FK, khóa/kiểm tiền tách chủ cùng transaction |
| C2 — `O:31` | §5: role/policy kiểm toàn vẹn chỉ pháp nhân dưới FORCE RLS; test âm không quyền M1 và cạnh tranh |
| C3 — `O:34` | §3.6, §6.1, §7: định danh hóa đơn Core; ghim ID + mã băm qua công bố, bỏ FK module chéo |
| S1 — `O:41` | §3.1, §5: `loi.phien_xac_thuc`, mã bí mật/ủy nhiệm việc, chống giả GUC và ngày |
| S2 — `O:45` | §4.1: bảng login, membership PG16, giữ/trao mật khẩu |
| S3 — `O:52` | §4.1, §6.3: view barrier, owner chỉ SELECT, policy xác minh phiên; bỏ role chạy công bố |
| S4 — `O:57` | §3.1, §4.2, §6.2: registry gọi động resolver DEFINER module; thiếu module trả `CHO` |
| S5 — `O:61` | §5: role xuất NOLOGIN/pháp nhân cố định/audit, xử lý đối tượng nhiều pháp nhân |
| S6 — `O:64` | §1.1, §3.5, §5: chốt từng bảng tiếp nhận ở Core; M0 chỉ cấu hình riêng |
| S7 — `O:65` | §5.1: 10 nhóm A theo khối, quyền bản rõ, khóa ngoài SQL/GUC |
| Opus mục 5/7 và Để sau — `O:19`, `O:21`, `O:70` | §7 đồng bộ thứ tự; §9 ba câu + dòng báo; §2 tên và §9 tồn đọng còn lại |
| Codex `khoa_ky` — `R:13` | §1.1, §3.6: một chủ `danh_muc`, guard chứng từ/adapter gọi Core |
| Codex M0/Core — `R:14` | §3.5: `vung_tam_tin_cay`, `lan_tiep_nhan_nguon` đều `loi_tai_lieu` |
| Codex tên còn thiếu — `R:15` | §2: con trỏ M2, nguồn, tài khoản, Nợ/Có; phụ lục dùng cùng tên |
| Codex tiến trình riêng — `R:16` | §3.2: một module/một tiến trình, một phiên hoạt động trên máy triển khai |
| Codex validator M0065/M0067 — `R:48` | §7: một định nghĩa hợp nhất giữ cả B3 và NGUON; test âm hai nhánh |
