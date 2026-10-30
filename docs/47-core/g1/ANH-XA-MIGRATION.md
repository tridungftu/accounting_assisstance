# ANH-XA-MIGRATION.md — Phụ lục G1a-2

**Trạng thái:** Nháp đặc tả ngày 30/10/2026, chờ ghép với `DAC-TA-CSDL.md` và duyệt cổng C. Chỉ tài liệu; không thực thi SQL, migration hoặc chuyển dữ liệu.

**Nguyên tắc:** phân chia theo đối tượng và định nghĩa hàm cuối cùng, không chuyển nguyên migration sang một module. Giữ cấu trúc và tên tiếng Việt không dấu đã đúng; phần nghiệp vụ riêng thuộc gói module. CSDL đích là PostgreSQL thật chung tại `D:\DU-LIEU-KE-TOAN`, theo TL 54 §14.

**Căn cứ:** TL 54 §3–§4, §9, §14; TL 55 §1, §10; CD-017/018/019/021/026–030; QD-20261026-09; KS-B và RV-B, đối chiếu KS-A/C/D/E, RV-AD, RV-C.

**Quy ước đọc bảng:**

- `P` = `src/kho_tri_thuc/ha_tang/pg_migrations.py`; `H`, `K`, `M` lần lượt là các thư mục `ha_tang`, `k2`, `m4` dưới `src/kho_tri_thuc/`.
- **Core** là gói quản lý `loi`, `loi_tai_lieu`, `danh_muc`. Gói `mod_x` quản lý schema `mod_x` và `cong_bo_x`. Đề xuất gói `mod_ke_toan_cu` quản lý vùng chuyển tiếp `ke_toan_cu`.
- ★: cần tách phần định nghĩa/quyền theo nhiều khối, hoặc tách lát tích hợp MTQ khỏi nghiệp vụ module. Việc gọi contract Core không có nghĩa gói module được sửa đối tượng Core.
- `*` chỉ toàn bộ họ tên tương ứng. Cột tên mới ghi phần đổi tên ngoài việc chuyển schema đã thể hiện ở cột khối; **giữ** nghĩa là giữ tên đối tượng.
- Mọi khối, gói và tên đích dưới đây là **đề xuất**, không phải hiện trạng đã triển khai.

## 1. Ánh xạ đủ 67 migration

| Số / tên | Đối tượng hiện có — căn cứ | Khối hiện tại → khối đích | Gói đích | ★ Cách tách | Tên đối tượng mới nếu đổi |
|---|---|---|---|---|---|
| M0001 | Schema nền; `phap_nhan*`, `cau_hinh`, `nguoi_dung`, `phan_quyen`, `nguon_tu_dong`. `P:13` | `master` → `loi`, `mod_m0`; các schema rỗng phân lại theo chủ | Core; `mod_m0` | ★ Danh tính/cấu hình chung vào Core; cấu hình nguồn tự động riêng M0 vào M0 | Giữ tên bảng |
| M0002 | `doi_tac*`, `tai_khoan_ngan_hang`, `du_an`, `ttcp`, `khoan_muc_phi`, `tai_khoan`. `P:86` | `master` → `danh_muc` | Core | — | Giữ |
| M0003 | `tep_goc`, `chung_tu`, `chung_tu_dong`, `cong_no_mo`. `P:195` | `kho` → `loi_tai_lieu`, `ke_toan_cu` | Core; `mod_ke_toan_cu` | ★ Metadata tệp dùng chung tách khỏi chứng từ/hạch toán cũ; chưa coi toàn bộ `cong_no_mo` là công nợ M2 | Giữ |
| M0004 | `loai_hinh_doanh_thu`, `hop_dong*`, `lich_thu`, `lich_tra_no`, `tai_san`, `nhan_vien`. `P:286` | `master` → `danh_muc`, `mod_crm`, `mod_m9`, `ke_toan_cu` | Core; `mod_crm`; `mod_m9`; `mod_ke_toan_cu` | ★ Khóa hợp đồng chung vào danh mục; dữ liệu bán/phiên bản/tham số/lịch thu vào CRM; lịch trả nợ vào M9; phần còn lại giữ chuyển tiếp | `danh_muc.hop_dong` và phần riêng `mod_crm.hop_dong`; giữ các tên còn lại |
| M0005 | `su_kien`, `cong_ai_goi`, `tin_zalo`, `mask_bi_danh`; trigger chỉ ghi thêm. `P:412` | `nhat_ky`, `bao_mat` → `loi`, `ke_toan_cu` | Core; `mod_ke_toan_cu` | ★ Audit/AI chung vào Core; tin nhắn và ánh xạ Mask cũ giữ chuyển tiếp, chưa tự nạp vào kho Mask mới | Audit `su_kien` → `nhat_ky_kiem_toan`, tránh trùng sự kiện bus |
| M0006 | Phiên nghiệp vụ, khóa kỳ, đề xuất, liên kết, việc duyệt, tri thức, lô xuất. `P:483` | `kho` → `danh_muc`, `ke_toan_cu` | Core; `mod_ke_toan_cu` | ★ `lien_ket_chung_tu`, `khoa_ky` vào danh mục; phần nghiệp vụ cũ giữ riêng; không đổi phiên thành phiên đăng nhập hoặc việc duyệt thành job Core | Giữ |
| M0007 | Guard chứng từ/đề xuất/nhãn học; `chuan_hoa_ten`. `P:683`, `P:742`, `P:755`, `P:774` | `kho`, `master` → `ke_toan_cu`, `danh_muc` | Core; `mod_ke_toan_cu` | ★ Guard theo bảng chủ; chuẩn hóa tên thuộc danh mục | Giữ |
| M0008 | ACL cho `app_ke_toan`, `app_doc`, `app_cong_ai`. `P:783` | Quyền `master/kho/nhat_ky/bao_mat` → từng khối đích | Core và từng `mod_*` liên quan | ★ Thay quyền schema rộng bằng quyền theo khối; mỗi gói cấp quyền đối tượng mình sở hữu | Role chạy/migration theo thân đặc tả; không sao chép nguyên ACL cũ |
| M0009 | Chặn TRUNCATE audit; guard chứng từ, CHECK tri thức, default privileges. `P:812`, `P:894`, `P:897` | `nhat_ky`, `kho` → `loi`, `ke_toan_cu` | Core; `mod_ke_toan_cu` | ★ Tách audit, guard nghiệp vụ và quyền mặc định theo chủ tạo đối tượng | Giữ tên hàm; audit dùng tên M0005 |
| M0010 | Vai/module, phiên bản/tham số/lịch thu, liên kết/việc; role web, RLS. `P:964`, `P:1165` | `master`, `kho` → `loi`, `danh_muc`, `mod_crm`, `ke_toan_cu` | Core; `mod_crm`; `mod_ke_toan_cu` | ★ Danh tính ở Core; hợp đồng bán ở CRM; liên kết chung ở danh mục; việc cũ giữ chuyển tiếp | Giữ tên nghiệp vụ |
| M0011 | `ktt_*`; guard/FK hợp đồng, lịch thu; liên kết, việc, RLS. `P:1222`, `P:1455` | `master`, `kho` → các khối M0010 | Core; `mod_crm`; `mod_ke_toan_cu` | ★ Tách hàm quyền chung khỏi guard CRM; Core không giữ FK ngược đến phiên bản riêng CRM | Giữ |
| M0012 | Duyệt phiên bản, ACL hàm nội bộ; wrapper `crm_*`. `P:1548`, `P:1616` | `master` → `mod_crm`, `danh_muc` | `mod_crm`; Core | ★ Hàm phiên bản thuộc CRM; đọc liên kết chung qua cổng danh mục | Giữ |
| M0013_COMMON | Registry/quyền/ánh xạ nguồn; tiếp nhận, vùng tạm, ảnh chụp, bản ghi, biên nhận; discriminator chứng từ. `P:3021`, `P:3431` | `master/giao_tiep/kho` → `loi`, `loi_tai_lieu`, `danh_muc`, `mod_m0`, `ke_toan_cu` | Core; `mod_m0`; `mod_ke_toan_cu` | ★ Đề xuất hiệu chỉnh KS-B: nền tiếp nhận dùng chung vào Core để M4/CRM/M2 không phụ thuộc M0; chỉ nghiệp vụ riêng M0 ở M0 | `nguon_instance` → `nguon_cai_dat`; `nguon_profile` → `ho_so_nguon`; `nguon_master_noi_dung` → `noi_dung_danh_muc_nguon`; `stage_tin_cay` → `vung_tam_tin_cay` |
| M0014_M5 | Năm bảng `phieu_kho_*`, hàm M5; thay finalizer tiếp nhận. `P:3881`, `P:4302` | `kho`, `giao_tiep` → `mod_m5`, nền tiếp nhận Core | `mod_m5`; Core | ★ Bảng/tiêu thụ phiếu vào M5; chốt tiếp nhận chung ở Core, gọi qua contract | Giữ |
| M0015_M2_BRIDGE | Đơn vị lượng, ứng viên dòng; `hoa_don_*`, `mua_dich_dong`, view; mapping/capture/finalizer/guard. `P:4783`, `P:5240`, `P:5518`, `P:6029` | `master/kho/giao_tiep` → `danh_muc`, `mod_m2`, nền tiếp nhận Core, `ke_toan_cu` | Core; `mod_m2`; `mod_ke_toan_cu` | ★ Đơn vị dùng chung vào danh mục; hóa đơn/ứng viên/đích vào M2; tiếp nhận chung vào Core; guard chứng từ cũ giữ chuyển tiếp | Giữ; `mua_dong_hien_hanh` thuộc M2 |
| M0016_L11_QUANTITY | Bằng chứng/quy đổi lượng, đích/lưu nguồn/liên kết dòng; phạm vi nguồn, stage, liên kết chứng từ. `P:8232`, `P:8240`, `P:8244`, `P:8299`, `P:8658` | `master/giao_tiep/kho` → `mod_m5`, `mod_m2`, Core | `mod_m5`; `mod_m2`; Core | ★ Liên kết chứng từ vào danh mục; nguồn/stage vào Core; nghiệp vụ lượng và nhánh M2/M5 về module tương ứng; giữ giao thức khóa | Giữ; stage theo M0013 |
| M0017_M4 | Hồ sơ, quyền dự án, tệp/trích xuất/tham số, BOQ/đợt; mở rộng hợp đồng chung. `M/sql_m17.py:134`, `:237`, `:259` | `m4`, `master` → `mod_m4`, `danh_muc`, `loi_tai_lieu` | `mod_m4`; Core | ★ Khóa hợp đồng do Core quản lý; hồ sơ thuộc M4; metadata tệp chung qua Core, liên kết tệp theo hồ sơ giữ M4 | Giữ tên bảng; `digest_tham_so` → `ma_bam_tham_so` |
| M0018_CRM_G | Mẫu/bộ chuẩn/phiên bản/ánh xạ/kiểm/biên nhận CRM; phân công hành động. `P:9645`, `P:9691`, `P:9741` | `master` → `mod_crm`, `loi` | `mod_crm`; Core | ★ Mẫu/bộ chuẩn thuộc CRM; phân công quyền dùng chung thuộc Core | Giữ |
| M0019_M4_REVIEW | `review_run/result/artifact/manual_map/giu_khoa`, hàm kiểm. `M/sql_review.py:44` | `m4` → `mod_m4` | `mod_m4` | — | Lần lượt `lan_kiem_tra`, `ket_qua_kiem_tra`, `tep_ket_qua_kiem_tra`, `anh_xa_thu_cong_kiem_tra`, `giu_khoa_kiem_tra`; hàm `review_*` → `kiem_tra_*` |
| M0020_M4_REVIEW_QUYEN | Thay `review_quyen`. `P:10582` | `m4` → `mod_m4` | `mod_m4` | — | `kiem_tra_quyen` |
| M0021_CRM_G2G3 | Báo giá/bản soạn/phiên bản/giao kết; trạng thái trên hợp đồng chung. `P:10605`, `P:10689` | `master` → `mod_crm`, `danh_muc` | `mod_crm`; Core | ★ Trạng thái bán/giao kết thuộc CRM; danh mục chỉ giữ khóa chung | `crm_bao_gia_rev` → `crm_bao_gia_phien_ban`; `crm_hd_soan_rev` → `crm_hd_soan_phien_ban` |
| M0022_M4_CHUNG_TU | `chung_tu_run/result/artifact/revision/manual_map/giu_khoa`, hàm L3. `M/sql_chung_tu.py:59` | `m4` → `mod_m4` | `mod_m4` | — | Lần lượt `lan_kiem_chung_tu`, `ket_qua_kiem_chung_tu`, `tep_ket_qua_kiem_chung_tu`, `phien_ban_kiem_chung_tu`, `anh_xa_thu_cong_chung_tu`, `giu_khoa_chung_tu` |
| M0023_CRM_KY | Phạm vi ký, bản ký, guard ký/xuất, CHECK hợp đồng. `P:11303`, `P:11313` | `master` → `mod_crm`, `danh_muc` | `mod_crm`; Core | ★ Ký và khóa sau ký ở CRM; danh mục chỉ kiểm định danh chung | Giữ |
| M0024_M4_DUYET | `duyet_*`, PDF, seal, kế toán chờ/phong bì. `M/sql_duyet.py:107`, `:116` | `m4`, helper `master` → `mod_m4` | `mod_m4` | Helper quyền riêng M4 đi cùng module | `duyet_seal` → `duyet_dau_chung_thuc`; `_duyet_seal` → `_duyet_dau_chung_thuc` |
| M0025_CRM_G6A | Hồ sơ kiểm CRM; guard hợp đồng/phiên bản; thay chủ sở hữu việc. `K/sql_crm_kiem_hd.py:67`, `:1491`, `:1550` | `master`, `kho` → `mod_crm`, `danh_muc`, `ke_toan_cu` | `mod_crm`; Core; `mod_ke_toan_cu` | ★ Guard riêng CRM ở CRM; liên kết/định danh chung ở Core; việc cũ dùng contract chủ thể | `crm_kiem_rev` → `crm_kiem_phien_ban`; `crm_kiem_check` → `crm_kiem_ket_qua` |
| M0026_M4_KT | `kt_xac_nhan`, hàm kiểm/xác nhận nghiệm thu, helper quyền. `M/sql_ke_toan_nghiem_thu.py:155`, `:165` | `m4`, helper `master` → `mod_m4` | `mod_m4` | — | Giữ |
| M0027_M4_REQUEST | Ánh xạ, ý định, sự kiện, biên nhận Request nháp. `M/sql_request_nhap.py:57` | `m4` → `mod_m4` | `mod_m4` | Không tự nhập hàng việc riêng này vào hàng việc Core | Tiền tố bảng/hàm `request_` → `yeu_cau_`; `_request_` → `_yeu_cau_` |
| M0028_M4_MASTER_DUNG_CHUNG | `master_can_cu*`, hàm nhận/gắn danh mục; policy hợp đồng chung. `M/sql_master_dung_chung.py:86`, `:542` | `m4`, `master` → `mod_m4`, `danh_muc` | `mod_m4`; Core | ★ Căn cứ/snapshot riêng ở M4; quyền và cổng danh mục ở Core | Tiền tố `master_` của bảng/hàm M4 → `danh_muc_` |
| M0029_M4_GHI_NHAN_CHUNG | `mua_nguon_kinh_te*`, `mua_nguon_phan`, `mua_doi_chieu_can_cu*`, khóa chứng thực; biên nhận chung. `K/sql_ghi_nhan_chung.py:202`, `:240`, `:312`, `:408` | `kho` → `danh_muc`, `mod_m4`, `loi` | Core; `mod_m4` | ★ Định danh/nguồn chung vào danh mục; đối chiếu và khóa chứng thực vào M4; biên nhận chung qua Core, giữ namespace M2/M4 | Giữ |
| M0030_CRM_BG1C | Thay `crm_kiem_lich_ky`. `P:11857` | `master` → `mod_crm` | `mod_crm` | — | Giữ |
| M0031_CRM_DU_AN_BAN | Dự án bán, phí/lô/lịch sử, bộ chuẩn áp dụng. `K/sql_crm_du_an_ban.py:59` | `master` → `mod_crm` | `mod_crm` | — | Giữ |
| M0032_CRM_G5 | Registry, quyền chạy, việc, ý định, kết quả/sự kiện G5. `K/sql_crm_doi_chieu.py:60` | `master` → `mod_crm` | `mod_crm` | Giữ hàng việc nghiệp vụ hiện có | Giữ |
| M0033_M4_03B_SO_TIEN | Tiền đối chiếu; `dc_luu`, `dc_xac_nhan`, guard/gợi ý. `K/sql_ghi_nhan_so_tien.py:21`, `:55` | `kho` → `mod_m4` | `mod_m4` | Đọc hóa đơn qua công bố M2 | Giữ |
| M0034_CONG_AI_NHAT_KY | Metadata/CHECK/index/ACL `cong_ai_goi`. `P:11905` | `nhat_ky` → `loi` | Core | — | Giữ |
| M0035_CRM_DU_AN_MOC | Mốc dự án/lịch sử/hàm đọc ghi. `K/sql_crm_du_an_moc.py:17` | `master` → `mod_crm` | `mod_crm` | — | Giữ |
| M0036_KY_DOCX | Vá hàm xuất/ký/G5 cho bản ký DOCX/PDF. `P:12067` | `master` → `mod_crm` | `mod_crm` | Giữ toàn bộ thay đổi trên định nghĩa cuối | Giữ |
| M0037_CRM_G5_TAY | Kiểm tay G5; vá guard hồ sơ/việc. `K/sql_crm_g5_tay.py:33`; `P:12110` | `master` → `mod_crm` | `mod_crm` | — | Giữ |
| M0038_M4_REVIEW_CHEP | 13 bảng bản chép Review, FK/constraint/policy. `M/sql_review_chep.py:71` | `m4` → `mod_m4` | `mod_m4` | Giữ mô hình bản chép và bằng chứng nguồn | `review_chep_*` → `ban_chep_kiem_tra_*` |
| M0039_MA_TRAN_THAM_QUYEN | `mtq_*`, audit thay đổi/từ chối, hàm/trigger MTQ. `K/sql_ma_tran_tham_quyen.py:60` | `master`, `nhat_ky` → `loi` | Core | — | `mtq_bootstrap_admin` → `mtq_khoi_tao_admin`; giữ tên còn lại |
| M0040_M4_REVIEW_CHEP_B | Thời điểm chụp, UNIQUE/index, hàm bản chép hiện hành. `M/sql_review_chep.py:236` | `m4` → `mod_m4` | `mod_m4` | Dữ liệu cũ cần xử lý riêng điểm chặn nạp | `review_chep_hien_hanh` → `ban_chep_kiem_tra_hien_hanh` |
| M0041_MTQ_CONG | Cổng quyết định và ghi từ chối phiên. `K/sql_mtq_cong.py:1` | `master` → `loi`, dùng danh mục Core | Core | Tách truy cập danh mục qua cổng Core | Giữ |
| M0042_M3_CO_SO | Hợp đồng cơ sở, hóa đơn–hợp đồng, chính sách doanh thu; hàm/RLS. `K/sql_m3.py:8`, `:158` | `m3` → `mod_m3` | `mod_m3` | Bỏ phụ thuộc helper bất biến riêng CRM bằng helper chung hoặc nội bộ M3 | `policy_hinh_thuc_doanh_thu` → `chinh_sach_hinh_thuc_doanh_thu`; `policy_tai_ngay` → `chinh_sach_tai_ngay` |
| M0043_MTQ_CONG_B | Ghi từ chối, chống tái dùng request khác nội dung. `K/sql_mtq_cong.py:162` | `master` → `loi` | Core | — | Giữ |
| M0044_M3_CO_SO_B | Trigger một xác nhận hiện hành mỗi hóa đơn. `K/sql_m3.py:188` | `m3` → `mod_m3` | `mod_m3` | — | Giữ |
| M0045_MTQ_CONG_C | Cổng/resolver/từ chối cho CRM, chứng từ/liên kết/lô xuất cũ. `K/sql_mtq_cong.py:226`, `:275`, `:294` | `master`, đọc `kho` → `loi`, resolver module/chuyển tiếp | Core; `mod_crm`; `mod_ke_toan_cu` | ★ Chính sách MTQ ở Core; giải đối tượng nghiệp vụ về gói chủ | Giữ tên cổng; resolver riêng đặt trong schema gói chủ |
| M0046_M3_CO_SO_C | Thay `lien_ket_mot_xac_nhan`, namespace khóa. `K/sql_m3.py:211` | `m3` → `mod_m3` | `mod_m3` | — | Giữ |
| M0047_MTQ_CONG_D | Resolver/cổng/từ chối mở rộng CRM G1–G4/G7/dự án. `K/sql_mtq_cong.py:473`, `:521` | `master` → `loi`, `mod_crm`, chuyển tiếp | Core; `mod_crm`; `mod_ke_toan_cu` | ★ Nhánh đọc bảng CRM thuộc resolver CRM; Core nhận kết quả đã kiểm chứng | Theo M0045 |
| M0048_MTQ_CONG_E | Thêm phạm vi M4 vào resolver/cổng. `K/sql_mtq_cong.py:843`, `:1021` | `master`, đọc `m4` → `loi`, `mod_crm`, `mod_m4`, chuyển tiếp | Core; các gói resolver tương ứng | ★ Tách nhánh M4 về M4; giữ cổng chung Core | Theo M0045 |
| M0049_MTQ_LMOD_A | Vá nhánh nguồn trong `mtq_kiem_ghi`. `K/sql_mtq_lien_module.py:91` | `master` → `loi`, dùng nền nguồn Core | Core | Phần kiểm nguồn dùng cổng registry/ánh xạ chung | Giữ |
| M0050_MTQ_CRM_A | Guard G1/G7; vá đọc/duyệt bộ chuẩn. `P:12207` | Lát MTQ sửa `master.crm_*` → `mod_crm` | `mod_crm` | ★ Vá nghiệp vụ nằm trong CRM; quyết định quyền gọi Core, không để gói Core thay hàm CRM | Giữ |
| M0051_MTQ_CONG_F | Tách `mtq_giai_doi_tuong`; thay quyết định/từ chối. `K/sql_mtq_cong.py:1354`, `:1396`, `:1526` | `master`, đọc module → `loi` và resolver module | Core; `mod_crm`; `mod_m4`; `mod_ke_toan_cu` | ★ Resolver tổng không chứa SQL đọc bảng riêng module | Theo M0045 |
| M0052_BUS_SU_KIEN | `su_kien`, `inbox`, RLS, phát/nhận/ACK. `K/sql_bus_su_kien.py:21` | `bus` → `loi` | Core | Phân biệt sự kiện trao đổi với audit M0005 | `inbox` → `hop_nhan_su_kien`; `payload_hop_le` → `noi_dung_su_kien_hop_le`; `ack` → `xac_nhan` |
| M0053_MTQ_CRM_B | Guard G2/G3; vá ghim mẫu, hiệu lực, tệp. `P:12240` | Lát MTQ sửa `master.crm_*` → `mod_crm` | `mod_crm` | ★ Hàm CRM giữ ở CRM; quyền chung gọi Core | Giữ |
| M0054_MTQ_NEN_A | `mtq_tinh_doc`, `mtq_duoc_doc`, ACL. `K/sql_mtq_nen.py:6` | `master` → `loi` | Core | — | Giữ |
| M0055_MTQ_M4_A | Helper MTQ hồ sơ; vá writer/digest/thiếu/nộp/biên nhận M4. `P:12325` | Lát MTQ sửa `m4` → `mod_m4` | `mod_m4` | ★ Giữ guard và nghiệp vụ tại M4; gọi cổng Core | `digest_tham_so` → `ma_bam_tham_so`; `_mtq_ho_so_digest` → `_mtq_ho_so_ma_bam` |
| M0056_MODULE_CONG_TAC | Danh mục module, công tắc, người thử, hàm quản trị. `K/sql_module.py:7` | `master` → `loi` | Core | Giữ công tắc theo module × pháp nhân | Giữ |
| M0057_MTQ_CONG_G | Cổng phiên hỗ trợ tập pháp nhân; quyết định/từ chối. `K/sql_mtq_cong.py:1858` | `master` → `loi` | Core | Resolver nghiệp vụ đã tách theo M0051 | Giữ |
| M0058_MTQ_NEN_B | Thay `mtq_duoc_doc`, kiểm mọi pháp nhân. `K/sql_mtq_nen.py:103` | `master` → `loi` | Core | — | Giữ |
| M0059_M4_BOQ_BO | CHECK BOQ và `boq_hieu_luc`. `M/sql_boq_bo.py:8` | `m4` → `mod_m4` | `mod_m4` | Giữ thêm dòng THEМ/THAY/BO theo QD-09 | Giữ |
| M0060_HANG_VIEC | Hàng việc, RLS, lease/retry/dừng/audit. `K/sql_hang_viec.py:22` | `viec` → `loi` | Core | Đổi tên hàm ngắn để không trùng nhóm bus | `tao/nhan/phuc_hoi/gia_han/tien_do/ket_thuc/thu_lai/yeu_cau_dung` thêm tiền tố `hang_viec_`; `_giu` → `_hang_viec_giu` |
| M0061_MTQ_M4_B | Reader/helper M4, bản chép; policy hợp đồng chung. `P:12452`; `M/sql_mtq.py:185` | `m4`, `master` → `mod_m4`, `danh_muc` | `mod_m4`; Core | ★ Reader ở M4; policy/cổng hợp đồng chung do Core sở hữu | Áp dụng các tên M0017/M0028/M0040 |
| M0062_HANG_VIEC_B | Hàm trạng thái lease, ACL. `K/sql_hang_viec.py:311` | `viec` → `loi` | Core | — | `trang_thai_lease` → `hang_viec_trang_thai_giu_viec` |
| M0063_M4_BOQ_BO_B | Thay writer `ghi_boq` đã có guard M0055. `P:12490` | `m4` → `mod_m4` | `mod_m4` | Giữ cả guard MTQ và hành vi BOQ cuối cùng | Giữ |
| M0064_CONG_BO_HOA_DON | Hàm công bố hóa đơn, chưa tạo schema/view công bố. `K/sql_cong_bo_hoa_don.py:14` | `master` → `cong_bo_m2`, phần đọc nội bộ `mod_m2` | `mod_m2` | Chuyển helper kiểm quyền M2 khỏi phụ thuộc bộ đối chiếu M4 | `cong_bo_m2.hoa_don_cong_bo`; khung công bố chỉ đọc theo thân đặc tả |
| M0065_MTQ_CRM_C | Vá ký/đọc/phạm vi G4, quan hệ B3; sửa cả `mtq_kiem_ghi`. `P:12517`, `P:12523`, `P:12595` | `master` → `mod_crm`, `loi` | `mod_crm`; Core | ★ Guard MTQ chung ở Core; giải/ghim quan hệ CRM ở CRM qua contract; đối chiếu xung đột M0067 | Giữ |
| M0066_MTQ_CONG_H | Resolver tập pháp nhân nguồn/ánh xạ; quyết định/từ chối. `K/sql_mtq_cong.py:2098` | `master` → `loi`, dùng nền nguồn Core | Core | Giữ kiểm tập pháp nhân; không nhập dữ liệu nguồn chưa phân quyền vào phạm vi chung | Giữ |
| M0067_MTQ_LMOD_B | `mtq_nguon_ung_vien`; dựng lại validator từ M0049. `K/sql_mtq_lien_module.py:115`, `:124` | `master` → `loi`, dùng nền nguồn Core | Core | Kiểm xung đột M0065; không mặc định hai bản vá validator cùng tồn tại | Giữ tên hàm; `profile_id` → `ho_so_nguon_id` |

## 2. Thứ tự dựng CSDL thật chung mới

Đây là thứ tự **đề xuất cho giai đoạn sau duyệt**, không phải lệnh triển khai. CD-029 yêu cầu đủ ba phiếu CSDL/API/SDK được duyệt trước G2.

| Bước | Gói / phạm vi | Điều kiện và cách tổ chức |
|---|---|---|
| 1 | **Core — nền** | Dựng role chạy/migration, `loi`, `loi_tai_lieu`, `danh_muc`; danh tính, pháp nhân, audit và lịch sử migration theo gói. Runtime không tự chạy migration. |
| 2 | **Core — dịch vụ chung** | Dựng MTQ, công tắc module, bus, hàng việc, tài liệu/tệp, danh mục và nền tiếp nhận nguồn chung. Bổ sung registry module/engine, sổ cổng và số đo vận hành theo TL 55 §10/CD-028; đây là phần mới, không được ghi là đã có trong 67 migration. |
| 3 | **`mod_m4` — mẫu đầu tiên G4** | Hồ sơ/BOQ/đợt → kiểm tra/chứng từ → duyệt/xác nhận → đối chiếu/Request; nhận đầy đủ các vá MTQ/BOQ cuối cùng. Đọc danh mục/tệp qua Core. Chưa có M2 thì phần cần hóa đơn ở trạng thái chờ có lý do. |
| 4 | **`mod_crm`** | Hợp đồng bán/phiên bản/tham số/lịch thu → mẫu/bộ chuẩn → báo giá/soạn/ký → kiểm/G5/dự án/mốc; tích hợp resolver MTQ của CRM. |
| 5 | **`mod_m2`** | Hóa đơn/quan sát/dòng/đích → tiếp nhận theo contract Core → `cong_bo_m2`. Phần M4 cần hóa đơn được nối sau khi contract công bố M2 sẵn sàng. Nghiệp vụ M2 cần được Anh chốt trước G4 theo TL 55 §6. |
| 6 | **Module khác** | Đóng gói `mod_m0`, `mod_m5`, `mod_m3`, `mod_m9` và phần chuyển tiếp khi cần. `mod_m1` chưa có migration riêng trong chuỗi này; không tự tạo nền M1/M9 từ lineage ngoài chuỗi. |

Thứ tự trên là thứ tự dựng và nghiệm thu gói; không cấm phát triển CRM/M2 song song ở G4. **Core không phụ thuộc ngược vào schema module.** Phần tiếp nhận chung của M0013 được đề xuất nâng lên Core; M0 giữ nghiệp vụ riêng. Đây là chênh lệch cần lead thống nhất với thân đặc tả.

### Quy tắc giữ lịch sử và phụ thuộc

| Nội dung | Nguyên tắc |
|---|---|
| Hai lineage dễ nhầm | Ordinal 13 dùng `M0013_COMMON`; ordinal 17 dùng bản import từ `M/sql_m17.py`, không dùng full-M9 lịch sử hoặc M17 partial. Căn cứ `P:2994`, `P:9594`, `P:9596`. |
| Lịch sử cũ | Giữ nguyên số/checksum nguồn; không sửa checksum để hợp thức hóa gói mới. Mỗi gói đích có phiên bản/checksum riêng và liên hệ nguồn M0001–M0067. Cơ chế hiện có kiểm checksum và ghi tương thích tại `H/postgres.py:217`, `:236`, `:244`. |
| Định nghĩa cuối | Gói mới chứa định nghĩa hoàn chỉnh sau các vá của đối tượng mình sở hữu; không import toàn bộ lịch sử module khác để tìm/thay chuỗi SQL. Cơ chế quét/thay hiện có nằm tại `P:11974`, `P:12088`, `P:12490`. |
| Xung đột validator | M0065 vá `mtq_kiem_ghi` từ hàm hiện hành (`P:12523`), nhưng M0067 dựng lại từ `MTQ_LMOD_A_SQL[0]` (`K/sql_mtq_lien_module.py:115`). Lead phải xác định phần hành vi cần giữ; không tuyên bố bản vá B3 M0065 còn nguyên sau M0067 khi chưa đối chiếu. |
| Quan hệ giữa khối | Core chỉ giữ khóa/liên kết chung; FK và guard phiên bản riêng chuyển về module. Ghi chung qua Core; đọc module khác qua `cong_bo_*`. Không giải vòng phụ thuộc bằng quyền SQL chéo hoặc bỏ kiểm quyền. |
| Ít tài nguyên | Giữ bảng cố định; mỗi kỳ/đợt/phụ lục thêm dòng, không tạo bảng/cột theo lần phát sinh. Không gom các hàng việc nghiệp vụ đang đúng chỉ để thống nhất tên. Theo `docs/QUYET-DINH.md:357`. |

### Nguyên tắc nạp DEMO cũ

| Bước | Nguyên tắc |
|---|---|
| Xác nhận nguồn | Catalog chỉ ghi `migration_da_chay = "23 23"`, chưa có danh sách version/checksum để chứng minh đúng 23 migration đầu chuỗi hiện tại (`docs/47-core/g0/so-lieu-csdl-demo.json:2764`). Phải xác nhận lineage trước khi lập phương án chuyển. |
| Dựng đích | Dựng cấu trúc mới từ các gói đích, thử nạp trong môi trường DEMO tách biệt. Không mặc định nâng thẳng nguồn từ 23 lên 67. M0040 có điểm chặn khi bảng nguồn đã có dòng (`M/sql_review_chep.py:239`). |
| Ánh xạ dữ liệu | Nạp pháp nhân/danh tính/danh mục và tệp trước, nghiệp vụ module sau; giữ UUID khi hợp lệ, quan hệ phiên bản, chứng cứ nguồn và lịch sử duyệt. Trường hợp phải đổi ID có ánh xạ đối chiếu. |
| Bảo toàn ý nghĩa | Không tự suy thời điểm chụp, tiền còn thiếu, đơn vị hoặc trạng thái duyệt. Đối chiếu số dòng, khóa/liên kết, tổng tiền theo đơn vị và mã băm tệp; không lấy việc chạy xong làm bằng chứng đã duyệt. |
| Sang CSDL thật | DEMO dùng để diễn tập. Không tự chuyển tài khoản mô phỏng, quyền thử, việc đang chạy hoặc dữ liệu DEMO thành dữ liệu thật. Chỉ nạp tập dữ liệu được xác định và nghiệm thu theo kế hoạch G5; bảo toàn bản nguồn và khả năng khôi phục. |

## 3. Hàm/trigger phải đổi chủ hoặc tách theo khối

**Chủ đích** là role migration/chủ sở hữu của khối tương ứng; role chạy không sở hữu hàm/bảng và không có BYPASSRLS. Hàm `SECURITY DEFINER` phải chốt chữ ký, owner, `search_path` tin cậy và EXECUTE theo thân đặc tả. Trigger được quản lý cùng bảng đích; không có owner runtime riêng cho trigger.

| Khối đích | Hàm/trigger hiện có — căn cứ | Thay đổi sở hữu hoặc tách bắt buộc |
|---|---|---|
| **`loi` — danh tính/quyền** | `master.ktt_danh_tinh`, `ktt_pn_cho_phep`, `ktt_duoc`, `ktt_co_vai`, `ktt_ngay`, các helper kiểm chủ bảng. `P:1224`, `P:1249`, `P:3030` | Hàm danh tính/quyền chung về Core. Thay điều kiện “runtime là chủ bảng” bằng quyền chạy được cấp và cổng ghi có kiểm soát; không chuyển yêu cầu chủ bảng cũ thành quyền runtime mới. |
| **`loi` — MTQ** | Họ `master.mtq_*`; trigger `mtq_kiem_ghi`, `mtq_ghi_vet`, `mtq_bat_bien`, `mtq_chan_truncate`. `K/sql_ma_tran_tham_quyen.py:151`, `:296`; resolver/cổng tại `K/sql_mtq_cong.py:1355`, `:1859`, `:2099` | Chính sách, quyết định, kiểm tập pháp nhân và audit về Core. Tách nhánh giải đối tượng riêng CRM/M4/chuyển tiếp về module; không nhận nguyên thông tin pháp nhân do client tự khai. Xử lý xung đột M0065/M0067 trước khi chốt validator. |
| **`loi` — audit/bus/module** | `nhat_ky.chi_ghi_them`, `chan_truncate`; `bus.payload_hop_le`, `phat`, `nhan`, `ack`; họ `master.module_*` và trigger chống xóa/TRUNCATE. `P:458`, `P:813`; `K/sql_bus_su_kien.py:24`, `:84`; `K/sql_module.py:47`, `:55` | Đổi chủ Core; tách audit khỏi bus; đổi tên theo bảng ánh xạ. Trigger audit của `tin_zalo` giữ theo bảng chuyển tiếp, dùng helper chung nếu được cấp rõ. |
| **`loi` — hàng việc** | `viec._kiem_quyen`, `_nhat_ky`, `tao`, `phuc_hoi`, `nhan`, `_giu`, `gia_han`, `tien_do`, `ket_thuc`, `thu_lai`, `yeu_cau_dung`, `trang_thai_lease`; `hang_viec_nhat_ky`. `K/sql_hang_viec.py:71`, `:101`, `:103`, `:312` | Đổi chủ Core và thêm namespace tên hàm khi nhập vào `loi`; giữ lease, chống trùng, retry/dừng và ngữ cảnh pháp nhân/module. |
| **Core — nguồn/tài liệu** | `ktt_nguon_*`, `nang_luc_nguon_khong_sua`, `anh_xa_nguon_*`; `giao_tiep.chi_ghi_them`, `stage_kiem`, `ket_qua_cuoi_kiem`, `nguon_*`; `kho.bien_nhan_*`. `P:3024`, `P:3076`, `P:3102`, `P:3190`, `P:3319`, `P:3397` | Phần registry/quyền ở `loi`, metadata tiếp nhận ở `loi_tai_lieu`, ánh xạ danh mục ở `danh_muc`. Tách capture/finalizer chung khỏi tiêu thụ nghiệp vụ M2/M5; không mất khóa, namespace biên nhận hoặc kiểm nguồn trước xác định pháp nhân. |
| **`danh_muc`** | `master.chuan_hoa_ten`; guard định danh hợp đồng; `kho.lien_ket_kiem`, `lien_ket_l11_kiem`; guard nguồn kinh tế/phần nguồn. `P:774`, `P:1296`, `P:1455`, `P:8256`; `K/sql_ghi_nhan_chung.py:434`, `:478` | Chỉ giữ quy tắc danh mục/liên kết chung. Các kiểm tra phiên bản bán, lịch thu, ký hoặc nghiệp vụ lượng phải gọi contract hoặc nằm trong module chủ, không đọc bảng riêng trực tiếp. |
| **`mod_crm`** | `phien_ban_chen`, `phien_ban_kiem_duyet`, `tham_so_kiem`, `lich_thu_kiem`; họ `crm_*`, guard giao kết/ký/kiểm. `P:1321`, `P:1549`, `P:1389`, `P:1403`, `P:10690`, `P:11488`; `K/sql_crm_kiem_hd.py:580` | Đổi chủ CRM. Guard hiện gắn vào hợp đồng chung phải tách phần trạng thái riêng CRM về bảng CRM; danh mục chỉ giữ guard định danh. Các vá MTQ M0050/M0053/M0065 nằm trong gói CRM và gọi Core. |
| **`mod_m4`** | Toàn bộ hàm/trigger `m4.*`; helper `master.m4_duoc`, `m4_duyet_duoc`, `m4_kt_duoc`; guard `hop_dong_m4_chi_chu`. `M/sql_m17.py:136`, `:225`, `:243`; `M/sql_duyet.py:107`; `M/sql_ke_toan_nghiem_thu.py:155`; `P:12325`, `P:12452` | Helper quyền riêng và nghiệp vụ về M4; phần bảo vệ khóa hợp đồng chung do Core sở hữu. Tách lưu tệp chung khỏi liên kết hồ sơ; giữ guard M0055/M0061/M0063. Đổi các họ tên Review/Request theo bảng ánh xạ. |
| **`mod_m4` — đối chiếu** | `kho.dc_*`, `_dc_*`, trigger `mua_doi_chieu_can_cu_*`; constraint trigger hoàn tất; `bien_nhan_dc_chi_chu`. `K/sql_ghi_nhan_chung.py:214`, `:499`, `:1158`, `:1266`, `:1376` | Đối chiếu và chứng thực thuộc M4; định danh nguồn chung qua danh mục, biên nhận qua Core. Tách kiểm nguồn chung khỏi thuật toán đối chiếu; đọc hóa đơn qua công bố M2. |
| **`mod_m2` / `cong_bo_m2`** | `m2_*`, guard hóa đơn/con trỏ/dòng/đích; `master.m2_ung_vien_dong_kiem`; `master.hoa_don_cong_bo`. `P:5021`, `P:5523`, `P:5551`, `P:5611`, `P:5912`; `K/sql_cong_bo_hoa_don.py:15` | Hàm và trigger nghiệp vụ về M2; cổng công bố do M2 sở hữu. Tách helper quyền khỏi `kho._dc_m2_doc` của bộ đối chiếu; không cấp quyền đọc bảng hóa đơn cho M4/M3. |
| **`mod_m5`** | `m5_*`, `phieu_kho_con_tro_kiem`; họ `l11_*`, guard quy đổi/liên kết dòng. `P:4017`, `P:4036`, `P:4144`, `P:8542`, `P:8556`, `P:8587` | Phiếu và nghiệp vụ lượng về M5; nhánh M2 về M2; liên kết chứng từ chung về danh mục; finalizer tiếp nhận về Core. Giữ thứ tự khóa và bất biến bằng chứng. |
| **`mod_m3`** | `co_so_kiem`, `lien_ket_kiem`, `policy_tai_ngay`, `ghi_nhat_ky`, `lien_ket_mot_xac_nhan` và trigger tương ứng. `K/sql_m3.py:47`, `:97`, `:139`, `:146`, `:189`, `:212` | Đổi chủ M3; đổi tên chính sách. Trigger đang dùng `master.crm_g_bat_bien`/`nhat_ky.chan_truncate` phải dùng helper chung được cấp hoặc helper nội bộ, tránh phụ thuộc gói CRM (`K/sql_m3.py:158`). |
| **`ke_toan_cu`** | Guard trạng thái chứng từ, khóa đề xuất/nhãn học, `chung_tu_chu_so_huu_common`, `chung_tu_dong_kiem_common`, việc duyệt/lô xuất và guard M2 trên chứng từ cũ. `P:683`, `P:742`, `P:755`, `P:3440`, `P:3470`, `P:5211`; `K/sql_crm_kiem_hd.py:1550` | Giữ hành vi cũ trong gói chuyển tiếp; không cấp quyền rộng từ Core. Tách nhánh nghiệp vụ CRM/M2/M5 qua contract, không biến toàn bộ kho cũ thành Core. |

**Giới hạn xác nhận:** phụ lục dựa trên khảo sát tĩnh và catalog G0; chưa xác nhận owner/ACL/search_path từng hàm đang triển khai. Không chạy test, migration hoặc kết nối CSDL trong lát này.