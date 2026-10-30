# KS-B · Cơ sở dữ liệu và 67 migration

**Kết luận:** cần phân chia theo **quyền sở hữu từng đối tượng**, không chuyển nguyên các schema hiện tại thành khối Core. `master` và `kho` đang chứa đồng thời dữ liệu chung, nghiệp vụ nhiều module và phần kho cũ. Một số migration thay lại hàm của phần khác; tách gói phải giữ cả thứ tự phụ thuộc và hành vi cuối cùng.

Mã khảo sát thuộc nhánh `hop-nhat-20261023`. Chuỗi mặc định có **67 migration**; catalog DEMO ghi **23 migration**, chênh 44 bậc. CSDL thật chung chưa dựng theo đầu vào lead và CD-026. Đây là khảo sát tĩnh: không sửa tệp, không kết nối CSDL, không chạy test, migration hoặc công cụ dọn.

Căn cứ: TL 54, đặc biệt §14; TL 55 §1; `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:297`, `:316`, `:338`, `:347`.

**Quy ước dẫn chiếu:**

- `P` = `src/kho_tri_thuc/ha_tang/pg_migrations.py`.
- `H`, `K`, `M` lần lượt là `src/kho_tri_thuc/ha_tang`, `src/kho_tri_thuc/k2`, `src/kho_tri_thuc/m4`.
- `J` = `docs/47-core/g0/so-lieu-csdl-demo.json`.
- `★` = migration sửa đối tượng thuộc nhiều khối đích, hoặc lát tích hợp thay thân hàm của module khác; không đánh dấu chỉ vì có đọc/tham chiếu.
- `*` trong tên đối tượng biểu thị một họ cùng tiền tố. Bảng liệt kê nhóm đối tượng chính, gộp chỉ mục, trigger và constraint theo đối tượng.
- Khối đích là **đề xuất**, chưa phải schema đã triển khai. `ke_toan_cu` là vùng chuyển tiếp cho nền kế toán cũ; các phần riêng ngoài phạm vi TL 55 đề xuất `mod_m0`, `mod_m1`, `mod_m3`, `mod_m5`, `mod_m9`.

## 1. Bảng ánh xạ 67 migration

**Hai phân biệt bắt buộc:** ordinal 13 mặc định là `M0013_COMMON`, không phải bản full-M9 lịch sử; ordinal 17 dùng SQL import từ `M/sql_m17.py`, không phải bản partial còn lưu trong P. Căn cứ `P:2994`, `P:8748`, `P:9594`, `P:9596`. Chuỗi nối tới ordinal 67 tại `P:12689`.

| Migration · dấu lát/ngày nếu có | Schema, đối tượng tạo/sửa · căn cứ | Chủ hiện tại → khối đích đề xuất |
|---|---|---|
| ★ M0001 · nền V13 | Tạo `master/kho/nhat_ky/bao_mat`, extension; `master.phap_nhan*`, `cau_hinh`, `nguoi_dung`, `phan_quyen`, `nguon_tu_dong`. `P:13` | Nền chung → `loi`, `mod_m0`; schema còn lại chia theo đối tượng |
| M0002 · danh mục | `master.doi_tac*`, `tai_khoan_ngan_hang`, `du_an`, `ttcp`, `khoan_muc_phi`, `tai_khoan`. `P:86` | Danh mục chung → `danh_muc` |
| ★ M0003 · kho | `kho.tep_goc`, `chung_tu`, `chung_tu_dong`, `cong_no_mo`. `P:195` | Kho chung → `loi_tai_lieu`, `ke_toan_cu`; phân nghiệp vụ tiếp theo chủ dòng |
| ★ M0004 · master nghiệp vụ | `master.loai_hinh_doanh_thu`, `hop_dong*`, `lich_thu`, `lich_tra_no`, `tai_san`, `nhan_vien`. `P:286` | CRM/vay/danh mục cũ → `danh_muc`, `mod_crm`, `mod_m9`, `ke_toan_cu` |
| ★ M0005 · nhật ký/bảo mật | `nhat_ky.su_kien`, `cong_ai_goi`, `tin_zalo`; `bao_mat.mask_bi_danh`. `P:412` | Audit/AI/Mask/tin nhắn → `loi`, `ke_toan_cu`; nơi giữ ánh xạ Mask chờ chốt |
| ★ M0006 · kho nghiệp vụ | `kho.phien`, `khoa_ky`, `de_xuat*`, `lien_ket_chung_tu`, `viec_can_duyet`, `cau_hoi`, `tri_thuc`, `nhan_hoc`, `lo_xuat*`, `canh_bao`. `P:483` | Kho cũ chung → `ke_toan_cu`, `danh_muc`; không đồng nhất phiên/việc này với đăng nhập/job Core |
| ★ M0007 · ràng buộc | Hàm/trigger trạng thái chứng từ, khóa dòng đề xuất, kiểm nhãn học; `master.chuan_hoa_ten`. `P:683`, `P:742`, `P:755`, `P:774` | Kho cũ/danh mục → `ke_toan_cu`, `danh_muc` |
| ★ M0008 · ACL ứng dụng | Cấp/thu quyền các schema cho `app_ke_toan`, `app_doc`, `app_cong_ai` nếu role tồn tại. `P:783` | Quyền chung → tách theo các khối đích, quản lý bởi `loi` |
| ★ M0009 · review 16/10 | Chặn TRUNCATE nhật ký; sửa trạng thái/kiểm tài khoản chứng từ, CHECK tri thức và default privileges. `P:812` | Audit/kho/danh mục → `loi`, `ke_toan_cu`, `danh_muc` |
| ★ M0010 · CRM-01, dấu 19/10 | Vai/module; phiên bản/tham số HĐ, lịch thu; liên kết/việc; tạo `app_web`, RLS. `P:961`, `P:964`, `P:1165` | CRM + quyền/nền chung → `mod_crm`, `loi`, `danh_muc`, `ke_toan_cu` |
| ★ M0011 · CRM-01 review 02 | `master.ktt_*`; guard/FK HĐ, tham số/lịch; `kho.lien_ket_kiem`, việc/lô và RLS bổ sung. `P:1222`, `P:1455`, `P:1530` | CRM + nền chung → cùng các khối M0010 |
| ★ M0012 · CRM-01 review 03 | Sửa duyệt/đóng hiệu lực; thu EXECUTE hàm nội bộ, thêm wrapper đọc `master.crm_*`. `P:1548`, `P:1615` | CRM + liên kết chung → `mod_crm`, `danh_muc` |
| ★ M0013_COMMON · M0–M5/01 | `master.nguon_*`, `nang_luc_nguon`, `anh_xa_nguon`; `giao_tiep.*`; ảnh chụp/dòng nguồn/biên nhận, discriminator chứng từ. `P:3021`, `P:3431` | Tiếp nhận chung/M0, nền kho → `mod_m0`, `danh_muc`, `loi_tai_lieu`, `ke_toan_cu` |
| ★ M0014_M5 · M5 | Năm bảng `kho.phieu_kho_*`, hàm M5; tạo lại `giao_tiep.nguon_chot_ket_qua`. `P:3881`, `P:4302` | M5 + tiếp nhận chung → `mod_m5`, `mod_m0` |
| ★ M0015_M2_BRIDGE · R15 | `master.tai_lieu_khai_bao_don_vi`, `dinh_nghia_don_vi_luong`, `m2_ung_vien_dong`; `kho.hoa_don_*`, `mua_dich_dong`, view; sửa mapping/capture/finalizer/guard chung. `P:4783`, `P:5518`, `P:5639`, `P:6029` | M2 + danh mục/tiếp nhận/kho chung → `mod_m2`, `danh_muc`, `mod_m0`, `ke_toan_cu` |
| ★ M0016_L11_QUANTITY · R16 | `kho.bang_chung_*`, `dich_so_luong`, `ma_hoa_luong_nguon`, `lien_ket_dong`; sửa scope/stage và đường M2/M5 cũ. `P:8229`, `P:8299`, `P:8658` | L11/M5 × M2 → `mod_m5`, `mod_m2`, `mod_m0`; giữ giao thức khóa chung |
| ★ M0017_M4 · M4-01B | `m4` hồ sơ, quyền dự án, tệp/trích/tham số, phụ lục/BOQ/đợt, biên nhận/nhật ký; sửa `master.hop_dong`, thêm policy M4. `M/sql_m17.py:134`, `:237`, `:259` | M4 + khóa HĐ chung → `mod_m4`, `danh_muc`; ánh xạ tệp sang `loi_tai_lieu` |
| ★ M0018_CRM_G · CRM-41-02 | Mẫu/phiên bản/ánh xạ/kiểm, bộ chuẩn dự án, biên nhận CRM; `master.phan_cong_hanh_dong`. `P:9645`, `P:9691`, `P:9741` | CRM + phân công chung → `mod_crm`, `loi` |
| M0019_M4_REVIEW · M4-02A | `m4.review_run/result/artifact/manual_map/giu_khoa`, hàm review. `P:10576`; `M/sql_review.py:44` | M4 → `mod_m4` |
| M0020_M4_REVIEW_QUYEN · FIX04 | Chỉ tạo lại `m4.review_quyen`. `P:10582` | M4 → `mod_m4` |
| ★ M0021_CRM_G2G3 · CRM-41-03 | `master.crm_bao_gia*`, `crm_hd_soan*`, `crm_gk_*`; thêm trạng thái giao kết trên HĐ chung. `P:10605`, `P:10689` | CRM + HĐ chung → `mod_crm`, `danh_muc` |
| M0022_M4_CHUNG_TU · M4-02B | `m4.chung_tu_run/result/artifact/revision/manual_map/giu_khoa`, hàm L3. `P:11278`; `M/sql_chung_tu.py:59` | M4 → `mod_m4` |
| ★ M0023_CRM_KY · CRM-41-04A | `master.crm_ky_pham_vi`, `crm_hd_ky*`; guard ký/xuất, sửa CHECK HĐ chung. `P:11303`, `P:11313` | CRM + HĐ chung → `mod_crm`, `danh_muc` |
| M0024_M4_DUYET · M4-02C | `m4.duyet_*`: phiên bản, kết luận, quyết định, PDF, seal, KT chờ/phong bì. `P:11796`; `M/sql_duyet.py:116` | M4 → `mod_m4` |
| ★ M0025_CRM_G6A · CRM-41-06A | `master.crm_kiem_*`, sửa HĐ/phiên bản; thay `kho.viec_chu_so_huu`, policy việc kiểm. `K/sql_crm_kiem_hd.py:67`, `:1550`, `:1601` | CRM + nền duyệt/HĐ → `mod_crm`, `danh_muc`, `ke_toan_cu` |
| M0026_M4_KT · M4-03A | `m4.kt_xac_nhan`, hàm kiểm/xác nhận nguồn nghiệm thu. `P:11819`; `M/sql_ke_toan_nghiem_thu.py:165` | M4 → `mod_m4` |
| M0027_M4_REQUEST · M4-04C | `m4.request_anh_xa/y_dinh/su_kien/bien_nhan`, hàm Request nháp. `P:11830`; `M/sql_request_nhap.py:57` | M4 → `mod_m4` |
| ★ M0028_M4_MASTER_DUNG_CHUNG | `m4.master_can_cu*`, hàm nhận/gắn master; policy SELECT `master.hop_dong`. `M/sql_master_dung_chung.py:86`, `:542` | M4 + danh mục → `mod_m4`, `danh_muc` |
| ★ M0029_M4_GHI_NHAN_CHUNG · M4-03B | `kho.mua_nguon_kinh_te*`, `mua_nguon_phan`, `mua_doi_chieu_can_cu*`; sửa biên nhận chung. `K/sql_ghi_nhan_chung.py:202`, `:240`, `:312` | Chung M2–M4 → `danh_muc` cho định danh/liên kết chung; `mod_m4` cho đối chiếu |
| M0030_CRM_BG1C · BG-1c | Tạo lại `master.crm_kiem_lich_ky`. `P:11857` | CRM → `mod_crm` |
| M0031_CRM_DU_AN_BAN · DA-1, QĐ 25/10 | `master.crm_da_ban*`, phí/lô/lịch sử, `crm_bo_chuan_ap_dung`; sửa CHECK bộ chuẩn. `K/sql_crm_du_an_ban.py:59` | CRM → `mod_crm` |
| M0032_CRM_G5 · G5-B, cấp số 25/10 | `master.crm_g5_*`: registry, quyền chạy, việc, ý định, kết quả/sự kiện; thay hàm kiểm G5. `P:11879`; `K/sql_crm_doi_chieu.py:60` | CRM → `mod_crm` |
| M0033_M4_03B_SO_TIEN | Thêm tiền khai vào thành phần đối chiếu; thay `kho.dc_luu/dc_xac_nhan`, guard và gợi ý. `K/sql_ghi_nhan_so_tien.py:21`, `:55` | Đối chiếu M4 → `mod_m4` |
| M0034_CONG_AI_NHAT_KY · AI-2b | Thêm metadata, CHECK/index/ACL `nhat_ky.cong_ai_goi`. `P:11905` | Cổng AI/audit → `loi` |
| M0035_CRM_DU_AN_MOC · MDA-1a | `master.crm_da_moc`, `crm_da_moc_ls`, hàm đọc/ghi. `P:11949`; `K/sql_crm_du_an_moc.py:17` | CRM → `mod_crm` |
| M0036_KY_DOCX · QĐ 25/10-27 | Nới cặp PDF bản ký; thay thân các hàm xuất/ký/G5 hiện hành. `P:11953`, `P:12067` | CRM → `mod_crm` |
| M0037_CRM_G5_TAY · CD-010 | `master.crm_g5_kiem_tay`; thay kiểm G5 và guard hồ sơ/việc CRM. `P:12084`, `P:12107`; `K/sql_crm_g5_tay.py:33` | CRM → `mod_crm` |
| M0038_M4_REVIEW_CHEP · M4-DL1, 26/10 | 13 bảng `m4.review_chep_*`, FK/constraint/policy bản chép. `P:12115`; `M/sql_review_chep.py:71` | M4 → `mod_m4` |
| M0039_MA_TRAN_THAM_QUYEN · MTQ-1, 26/10 | `master.mtq_*`, `nhat_ky.mtq_thay_doi/mtq_tu_choi`, hàm/guard MTQ. `K/sql_ma_tran_tham_quyen.py:60` | MTQ → `loi` |
| M0040_M4_REVIEW_CHEP_B · M4-DL1b, 26/10 | Thêm `chup_luc`, UNIQUE/index; `m4.review_chep_hien_hanh`. `M/sql_review_chep.py:236` | M4 → `mod_m4` |
| M0041_MTQ_CONG · MTQ-4a0, 26/10 | `master.mtq_quyet_dinh_phien`, `mtq_ghi_tu_choi_phien`. `P:12139`; `K/sql_mtq_cong.py:1` | MTQ → `loi` |
| M0042_M3_CO_SO · M3-1a, 26/10 | Tạo `m3`; `hop_dong_co_so`, `hoa_don_hop_dong`, `policy_hinh_thuc_doanh_thu`, RLS/hàm. `K/sql_m3.py:8` | M3 → `mod_m3` |
| M0043_MTQ_CONG_B · MTQ-4a0b, 26/10 | Sửa ghi từ chối, chống dùng lại request khác nội dung. `K/sql_mtq_cong.py:162` | MTQ → `loi` |
| M0044_M3_CO_SO_B · M3-1c, 26/10 | Hàm/trigger một liên kết xác nhận hiện hành cho hóa đơn. `K/sql_m3.py:188` | M3 → `mod_m3` |
| M0045_MTQ_CONG_C · MTQ-4a3a, 26/10 | Thay resolver/quyết định và ghi từ chối cho CRM/M1/file soát. `K/sql_mtq_cong.py:226` | MTQ → `loi`; phụ thuộc contract các module |
| M0046_M3_CO_SO_C · M3-1d | Tạo lại `m3.lien_ket_mot_xac_nhan`, tách namespace khóa. `K/sql_m3.py:211` | M3 → `mod_m3` |
| M0047_MTQ_CONG_D · MTQ-4b1a | Thay resolver/quyết định và ghi từ chối, mở các đối tượng G1–G4/G7/dự án. `K/sql_mtq_cong.py:473` | MTQ → `loi` |
| M0048_MTQ_CONG_E · MTQ-4f1a | Thay resolver/quyết định và ghi từ chối, thêm phạm vi M4. `K/sql_mtq_cong.py:843` | MTQ → `loi` |
| M0049_MTQ_LMOD_A · MTQ-4i-a | Thay nhánh NGUON trong `master.mtq_kiem_ghi` của M0039. `K/sql_mtq_lien_module.py:91` | MTQ → `loi` |
| ★ M0050_MTQ_CRM_A · MTQ-4b1b | Thay hàm CRM G1/G7 và thân đọc/duyệt bộ chuẩn hiện hành. `P:12207`; `K/sql_mtq_crm.py:1` | Lát MTQ sửa CRM → `mod_crm`, gọi cổng `loi` |
| M0051_MTQ_CONG_F · MTQ-NEN-0 | Tách `master.mtq_giai_doi_tuong`; thay cổng quyết định/ghi từ chối. `K/sql_mtq_cong.py:1354` | MTQ → `loi` |
| M0052_BUS_SU_KIEN · XS-1a | Tạo `bus.su_kien/inbox`, RLS, hàm phát/nhận/ACK. `K/sql_bus_su_kien.py:21` | Bus chung → `loi` |
| ★ M0053_MTQ_CRM_B · MTQ-4b2a | Thay guard CRM G2/G3, hàm mẫu đã ghim/hiệu lực/tệp. `P:12240` | Lát MTQ sửa CRM → `mod_crm`, gọi `loi` |
| M0054_MTQ_NEN_A · MTQ-NEN-1 | `master.mtq_tinh_doc`, `mtq_duoc_doc`, ACL. `K/sql_mtq_nen.py:6` | MTQ → `loi` |
| ★ M0055_MTQ_M4_A · MTQ-4f1b | Helper MTQ hồ sơ; tạo lại các writer, digest/thieu/nộp/biên nhận M17. `P:12325` | Lát MTQ sửa M4 → `mod_m4`, gọi `loi` |
| M0056_MODULE_CONG_TAC · XS-4b | `master.module_danh_muc/cong_tac/nguoi_thu`, hàm công tắc. `K/sql_module.py:7` | Công tắc chung → `loi` |
| M0057_MTQ_CONG_G · MTQ-NEN-2a | Cổng phiên dùng tập pháp nhân, thay quyết định/ghi từ chối. `K/sql_mtq_cong.py:1858` | MTQ → `loi` |
| M0058_MTQ_NEN_B · MTQ-NEN-2b | Tạo lại `master.mtq_duoc_doc`, kiểm mọi pháp nhân. `K/sql_mtq_nen.py:103` | MTQ → `loi` |
| M0059_M4_BOQ_BO · BO-1a, QĐ-09 | Nới CHECK BOQ, thêm `m4.boq_hieu_luc`. `M/sql_boq_bo.py:8` | M4 → `mod_m4` |
| M0060_HANG_VIEC · XS-2a | Tạo `viec.hang_viec`, RLS, lease/retry/dừng/audit. `K/sql_hang_viec.py:22` | Hàng việc chung → `loi` |
| ★ M0061_MTQ_M4_B · MTQ-4f1c | Thay reader/helper M4, bản chép hiện hành; policy M4 trên `master.hop_dong`. `P:12452`; `M/sql_mtq.py:183` | MTQ/M4 + HĐ chung → `mod_m4`, `danh_muc`, gọi `loi` |
| M0062_HANG_VIEC_B · XS-2a2 | Thêm `viec.trang_thai_lease`, ACL. `K/sql_hang_viec.py:311` | Hàng việc chung → `loi` |
| M0063_M4_BOQ_BO_B · BO-1b | Tạo lại writer `m4.ghi_boq` đang có guard M0055. `P:12490` | M4 → `mod_m4` |
| M0064_CONG_BO_HOA_DON · XS-T1a | Hàm đọc `master.hoa_don_cong_bo`; không tạo schema/view công bố. `K/sql_cong_bo_hoa_don.py:14` | Công bố M2 → `cong_bo_m2` |
| ★ M0065_MTQ_CRM_C · MTQ-4b2b | Tạo lại hàm ký/đọc/phạm vi G4 và quan hệ B3 CRM. `P:12517`, `P:12595` | Lát MTQ sửa CRM → `mod_crm`, gọi `loi` |
| M0066_MTQ_CONG_H · MTQ-4i-b1 | Resolver tập pháp nhân nguồn/ánh xạ; thay quyết định/ghi từ chối. `K/sql_mtq_cong.py:2098` | MTQ → `loi` |
| M0067_MTQ_LMOD_B · MTQ-4i-b1 | `master.mtq_nguon_ung_vien`; thay truy vấn nguồn trong validator M0049. `K/sql_mtq_lien_module.py:115`, `:123` | MTQ → `loi` |

**Hệ quả cho việc tách gói:** phải lưu bản đồ tới **định nghĩa cuối cùng**, không chỉ tới migration khai sinh. Ví dụ M0063 lấy writer hiện hành bằng `_m37_ham`; cơ chế này quét ngược chuỗi đã đăng ký, còn `_m36_thay` yêu cầu mỗi vị trí thay xuất hiện đúng một lần (`P:11974`, `P:12088`, `P:12490`). Các gói độc lập không thể tiếp tục dựa ngầm vào việc import toàn bộ lịch sử module khác.

M9 typed đầy đủ là lineage lịch sử bị loại khỏi chuỗi mặc định; không đưa các bảng vay của lineage đó vào hiện trạng DEMO. M1 có mặt trong discriminator nền chung, nhưng không thấy migration riêng mang tên M1 trong chuỗi 67 (`P:2994`, `P:3434`, `P:9596`).

## 2. Schema, role, RLS và quyền

### 2.1. Catalog DEMO thực tế

Phiên bản **16.15** (`J:2`). Trường `migration_da_chay` là `"23 23"`; catalog không cung cấp danh sách version/checksum để xác nhận lineage từng migration (`J:2764`).

| Schema | Bảng / bật RLS / FORCE | Hàm / DEFINER | Chủ schema, ACL schema · căn cứ |
|---|---:|---:|---|
| `bao_mat` | 1 / 0 / 0 | 0 / 0 | `postgres`; không cấp `app_web`. `J:2663` |
| `giao_tiep` | 5 / 5 / 0 | 10 / 6 | `postgres`; `app_web` có USAGE. `J:2674` |
| `kho` | 36 / 28 / 0 | 89 / 62 | Như trên; có 1 view. `J:2685` |
| `m4` | 28 / 28 / 0 | 51 / 21 | Như trên. `J:2696` |
| `master` | 55 / 39 / 0 | 98 / 31 | Như trên. `J:2707` |
| `nhat_ky` | 3 / 0 / 0 | 2 / 0 | Như trên. `J:2718` |
| `public` | 0 / 0 / 0 | 71 / 0 | `pg_database_owner`; PUBLIC có USAGE, ACL này không cấp CREATE cho PUBLIC. `J:2729` |

Tổng cộng **128 bảng, 100 bật RLS, 0 FORCE RLS, 120 hàm DEFINER**. Catalog tổng hợp 68 policy trên bốn schema; đối tượng policy hướng tới `app_web` và/hoặc `public` (`J:2742`). **Policy TO PUBLIC không đồng nghĩa đã GRANT quyền bảng cho PUBLIC.**

Không thấy `m3`, `bus`, `viec` trong catalog này; chúng được tạo ở M0042, M0052, M0060. Chưa thấy schema `cong_bo_*`; M0064 hiện công bố bằng hàm trong `master` (`K/sql_m3.py:9`; `K/sql_bus_su_kien.py:22`; `K/sql_hang_viec.py:23`; `K/sql_cong_bo_hoa_don.py:15`).

### 2.2. Role và rủi ro quyền

| Nội dung | Theo mã và catalog | Đánh giá |
|---|---|---|
| Role ứng dụng | Catalog: `app_web`, `app_doc`, `app_ke_toan`, `app_cong_ai` đều NOLOGIN, không superuser/BYPASSRLS/CREATEROLE/CREATEDB; riêng `app_web` NOINHERIT (`J:28`). | Đây là thuộc tính role nhóm, chưa chứng minh quyền hiệu lực của mọi login thành viên. |
| Login DEMO | Login ứng dụng có INHERIT, không đặc quyền nêu trên; là thành viên `app_web` (`J:66`, `J:2020`). | Cần kiểm cả đường kế thừa; không lấy NOINHERIT của `app_web` làm bằng chứng login không hưởng quyền. |
| Quyền legacy | M0008 cấp kế toán SELECT/INSERT/UPDATE master–kho; cổng AI đọc master–kho và ghi ánh xạ Mask; role đọc có SELECT rộng (`P:783`). | Phạm vi rộng hơn mô hình role riêng từng khối của TL 55. |
| RLS legacy | M0010/M0011 có nhánh policy `USING(true)` cho vai cũ nếu tồn tại; M0015 thu hẹp các dòng M2/M5 (`P:938`, `P:1193`, `P:6473`). | Catalog hiện không liệt kê policy legacy đó. Không khẳng định nhánh cấp quyền có điều kiện đã thực sự chạy. |
| Runtime là chủ bảng | CRM G nhận kết nối chủ bảng; thiếu thì báo chưa sẵn sàng; writer kiểm `master.la_chu_bang` (`K/crm_mau.py:111`, `:126`; `P:9620`, `P:3030`). | **Chênh lệch trực tiếp với chuẩn mới.** Luồng nghiệp vụ dùng quyền chủ có thể đi ngoài RLS; không thể nghiệm thu chỉ bằng số bảng bật RLS. |
| PUBLIC | Catalog đánh dấu 167 hàm có EXECUTE mặc định PUBLIC; default privileges rỗng (`J:2740`). M0009 có nhánh ALTER DEFAULT PRIVILEGES theo role tồn tại (`P:897`). | Cần tên/chữ ký/ACL từng hàm và chủ tạo để xác định quyền thừa. Không kết luận cả 167 hàm đều nguy hiểm hoặc thu hồi hàng loạt. |
| DEFINER/search_path | Các định nghĩa trực tiếp DEFINER đã rà trong P và SQL của K/M không thấy thiếu `SET search_path`; ví dụ `P:1225`, `K/sql_mtq_cong.py:4`, `K/sql_cong_bo_hoa_don.py:16`. | Catalog thiếu cấu hình từng hàm nên **chưa xác nhận trạng thái triển khai**. G1 phải chốt owner, EXECUTE, schema được tin cậy và `search_path` từng hàm. |

**Giới hạn bằng chứng:** catalog hiện có chủ **schema**, chưa có chủ từng **bảng**, ACL bảng/hàm chi tiết, chủ hàm, quyền database và đầy đủ thuộc tính quan hệ thành viên. Vì vậy chưa thể xác nhận login DEMO có sở hữu bảng nào, hoặc toàn bộ quyền PUBLIC đã an toàn.

**RLS cần ngoại lệ được đặc tả rõ:** dữ liệu tiếp nhận trước khi xác định pháp nhân dùng registry/năng lực nguồn và stage tin cậy (`P:3036`, `P:3063`, `P:3173`, `P:3835`). Không áp máy móc một policy `phap_nhan_id` cho toàn bộ dữ liệu trước định tuyến. Ngữ cảnh giao dịch đã có mẫu `set_config(..., true)`; có thể tận dụng, nhưng phải kiểm trên các factory kết nối mới (`K/crm_mau.py:135`).

## 3. Quy ước tên: giữ tên đúng, đổi tên chưa đúng

**Đúng quy ước ở phần tên nghiệp vụ:** `bao_mat`, `giao_tiep`, `kho`, `nhat_ky`, `viec`; các tên `phap_nhan`, `nguoi_dung`, `phan_quyen`, `doi_tac`, `du_an`, `tai_khoan`, `tep_goc`, `chung_tu`, `hoa_don_danh_tinh`, `hop_dong_phien_ban`, `tham_so`, `phu_luc`, `dot`, `bien_nhan`, `hang_viec` và các cột Việt tương ứng. **Tên đúng không có nghĩa đang nằm đúng khối sở hữu** (`P:13`, `P:86`, `P:195`, `P:286`, `P:5240`; `M/sql_m17.py:314`; `K/sql_hang_viec.py:25`).

Các mã module/viết tắt nghiệp vụ như CRM, M4, MTQ, BOQ cần ghi trong từ điển tên; không đổi chỉ để mở rộng chữ viết tắt. Đối tượng PostgreSQL/extension như `public`, `pgcrypto`, `pg_trgm`, `unaccent` giữ theo hệ quản trị (`P:18`).

| Nhóm phải chuẩn hóa | Tên mới đề xuất | Căn cứ tên hiện có |
|---|---|---|
| Schema `master`, `bus`, `m4`, `m3` | Chia `master` theo `loi/danh_muc/mod_crm/mod_m2/...`; `bus` vào `loi`; `m4/m3` → `mod_m4/mod_m3` | `P:14`; `K/sql_bus_su_kien.py:22`; `M/sql_m17.py:134`; `K/sql_m3.py:9` |
| `schema_migrations(version,checksum,applied_at)` | `lich_su_doi_cau_truc(so_phien_ban,ma_bam,ap_dung_luc)` | `H/postgres.py:236`; `H/database.py:78` |
| `migration_tuong_thich`; `he_thong.key/value` | `tuong_thich_doi_cau_truc`; `khoa/gia_tri` | `H/postgres.py:238`, `:244` |
| `nguon_instance`, `nguon_profile`, `nguon_master_noi_dung`, `stage_tin_cay` | `nguon_cai_dat`, `ho_so_nguon`, `noi_dung_danh_muc_nguon`, `vung_tam_tin_cay` | `P:3036`, `P:3040`, `P:3082`, `P:3173` |
| `bus.inbox`, `payload`, `khoa_dedupe`, `ack_*` | `hop_nhan_su_kien`, `noi_dung_su_kien`, `khoa_chong_trung`, `xac_nhan_*` | `K/sql_bus_su_kien.py:49`, `:64` |
| `review_run/result/artifact/manual_map`, `chung_tu_run/result/...`, `review_chep_*`, `request_*` | Họ `lan_kiem_tra/ket_qua_kiem_tra/tep_ket_qua/anh_xa_thu_cong`, `lan_kiem_chung_tu/...`, `ban_chep_kiem_tra_*`, `yeu_cau_*` | `M/sql_review.py:44`; `M/sql_chung_tu.py:59`; `M/sql_review_chep.py:72`; `M/sql_request_nhap.py:57` |
| `crm_bao_gia_rev`, `crm_hd_soan_rev`, `m3.policy_*` | `crm_bao_gia_phien_ban`, `crm_hd_soan_phien_ban`, `chinh_sach_*` | `P:10668`, `P:10755`; `K/sql_m3.py:119` |
| `created_at/by`, `valid_from/to`, `latest_observation_id`, `revision`, `lease_*` | `tao_luc/boi`, `hieu_luc_tu/den`, `quan_sat_moi_nhat_id`, `so_sua_doi`, `giu_viec_*` | `P:129`, `P:5248`; `K/sql_module.py:19`; `K/sql_hang_viec.py:41` |
| Cột xuất kế toán `acct_id`, `base_deb/crd`, `project_id`, `remark`, `inv_*` | Họ `ma_tai_khoan`, `no/co_quy_doi`, `du_an_id`, `dien_giai`, `hoa_don_*`; giữ tên ngoài trong adapter | `P:521` |
| Role `app_web/doc/ke_toan/cong_ai` | `vai_web/doc/ke_toan/cong_ai`; đích mới theo khối: `vai_chay_loi`, `vai_doi_cau_truc_loi`, tương tự từng module | `P:783`, `P:1145`; `J:28` |
| Kho V12 tiếng Anh: `documents`, `document_lines`, `artifacts`, `attempts`, `source_records`, `audit_events`, `knowledge_*`… | Họ `chung_tu`, `dong_chung_tu`, `tep_nguon`, `lan_tiep_nhan`, `ban_ghi_nguon`, `nhat_ky_kiem_toan`, `tri_thuc_*` | `H/database.py:13`; `H/feature_migrations.py:5` |

Bảng trên là ánh xạ theo họ tên. G1 cần từ điển đầy đủ từng cột/hàm/constraint và kiểm trùng trong schema đích. Không đổi tên lịch sử migration hoặc diễn giải lại dữ liệu chỉ theo tên; chẳng hạn `artifacts` V12 chứa metadata tệp theo hash, không mặc nhiên tương đương kết quả xử lý Core (`H/database.py:15`).

## 4. Lõi cũ, `search_path` và SQLite

| Phần | Kết luận từ mã |
|---|---|
| Kho V12 qua `Store` | **Còn đường dùng thực tế**, chưa phải mã chết: CLI mở `Store`; `Store` gọi `mo_ket_noi`; nhánh SQLite gọi `database.connect`. Không xác nhận cấu hình kho thật vì không đọc cấu hình thật. `src/kho_tri_thuc/cli.py:148`; `H/store.py:89`; `H/ket_noi.py:480` |
| V12 chạy trên PostgreSQL | **Lớp tương thích còn được chọn qua cấu hình**: `KetNoiPG` dịch SQL SQLite và đặt `search_path` vào schema V12, mặc định `v12`. Đây là chuỗi migration khác với 67 migration typed. Catalog DEMO đang xét không có schema V12. `H/ket_noi.py:1`, `:184`, `:279`, `:473`; `J:2661` |
| Hàm tương thích V12 | `knowledge_epoch_bump` giữ `search_path FROM CURRENT`; SQL không định danh schema phụ thuộc schema lúc dựng. `H/dich_sqlite_pg.py:163` |
| SQLite trong M4 typed | **Vẫn dùng để tính projection trong RAM**, nạp snapshot PostgreSQL rồi bật `query_only`; không phải CSDL authority mới. `M/nguon_review.py:533`, `:706`, `:724`, `:771` |
| SQLite để đối chiếu/chuyển Review | Có reader mở SQLite `mode=ro&immutable=1`, kiểm WAL/journal. Các bảng `review_chep_*` vẫn được reader PostgreSQL sử dụng; không coi “đã chép” là đủ để dọn. `M/review_doi_chieu.py:91`; `M/review_phu_luc_pg.py:292` |

Hai điểm phải giữ trong kế hoạch nâng cấp:

- API `H/postgres.py:66` mặc định `migrate_on_connect=True`. Runtime mới cần tách khỏi quyền và thời điểm đổi cấu trúc.
- M0040 từ chối nâng cấp nếu `m4.review_chep_nguon` đã có dòng, thay vì tự suy `chup_luc` (`M/sql_review_chep.py:239`). Vì vậy không xem việc nâng DEMO từ 23 lên 67 là thao tác có thể chạy ngay.

## 5. Đề xuất dọn CSDL/role test — không thực thi

Catalog ghi **303 CSDL `kho_test_*`** và **651 role `ktt_test_*`**; chưa cung cấp danh sách đầy đủ cùng quan hệ sở hữu/phụ thuộc (`J:26`, `J:1866`). QD-20261026-09 yêu cầu dữ liệu tạm có hạn giữ/cách dọn, giữ cấu trúc bảng cố định và bảo toàn dữ liệu nghiệp vụ (`docs/QUYET-DINH.md:357`).

Đề xuất thực hiện sau bằng một phiên bảo trì tuần tự:

1. **Lập tập ứng viên chính xác từ catalog mới**, đối chiếu sổ lần test, cụm, chủ sở hữu và phiên kết nối. Dùng prefix để lọc ứng viên; mục chưa rõ nguồn tiếp tục giữ.
2. **Dọn CSDL trước, role sau**; giữ CSDL đang có phiên. Giữ riêng DEMO của Anh, database hệ thống và cụm thật. Hạn giữ test cần phân biệt lần thành công đã đối soát với lần lỗi/treo cần điều tra.
3. **Xử lý lô nhỏ, một worker**, ghi số đã xử lý/bỏ qua/lỗi và đo thời gian, dung lượng thực thu hồi; chưa có số liệu để hứa số GB hoặc đặt kích thước lô tối ưu.
4. **Role chỉ đủ điều kiện khi hết phụ thuộc trên các database còn giữ**; role còn sở hữu hoặc được tham chiếu tiếp tục giữ để lead xử lý riêng.
5. **Ngăn tái tồn đọng:** mỗi lần test có mã lần, tập tài nguyên sở hữu và đối soát sau kết thúc; lỗi dọn phải được ghi nhận để bảo trì tiếp.

Có thể tận dụng công cụ hiện có: `tools/don_csdl_test_cu.py:24` lọc prefix, `:41` kiểm số phiên, `:58` có xem trước, `:74` dọn tuần tự, `:82` thử dọn role. **Chưa đủ để dùng nguyên trạng làm chính sách mới:** lựa chọn CSDL hiện dựa tên và số phiên, chưa đối chiếu sổ sở hữu; role chưa kiểm phụ thuộc trước khi thử dọn. Công cụ cũng đọc cấu hình kết nối cục bộ, nên không được chạy trong khảo sát này (`tools/don_csdl_test_cu.py:26`).

## Chờ Anh

- Chốt ranh giới định danh/liên kết chung M2–M4, phần kho kế toán cũ và nơi giữ ánh xạ Mask.
- Chốt hạn giữ cùng quyền thực thi dọn tập CSDL/role test đã được lead xác minh; chưa coi số đếm là danh sách được phép dọn.

## Gợi ý cho đặc tả G1

- Ánh xạ từng đối tượng tới chủ và khối đích; giữ lịch sử checksum cũ, lập đồ thị phụ thuộc cho migration theo gói.
- Đặc tả hai role mỗi khối, ACL/default privileges, owner và `search_path` từng hàm DEFINER; bổ sung catalog còn thiếu.
- Tách quyền nguồn trước pháp nhân khỏi RLS nghiệp vụ; resolver MTQ dùng contract module.
- Chuẩn hóa UUID, thời điểm, tiền và phiên bản dòng; giữ trạng thái thiếu tiền M2, không tự quy đổi các cột minor đang bắt buộc NULL (`P:5271`).
- Nghiệm thu riêng dựng mới và nâng cấp DEMO 23 bậc, gồm điểm chặn M0040, quyền khác pháp nhân và khả năng đọc/replay dữ liệu cũ.