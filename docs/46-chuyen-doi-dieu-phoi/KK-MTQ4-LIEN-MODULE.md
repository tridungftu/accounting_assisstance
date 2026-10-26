# KK-MTQ4-LMOD — kiểm kê liên module và chuỗi lát đề xuất

26/10/2026 · nhánh `lat/kk-mtq4-lmod` · chỉ đọc mã, chỉ tạo tài liệu này. **Chưa thể coi nhóm MTQ-4i…4m đã được bao phủ:** catalog đã có ô nghiệp vụ, nhưng thiếu resolver, phạm vi NGUON còn bị chặn và SQL/service vẫn dùng quyền cũ.

Căn cứ: [thiết kế §4.1–4.2, §5.1–5.3, §7](THIET-KE-MA-TRAN-THAM-QUYEN.md), [4a3a SQL](giao-viec-20261026/giao-mtq-4a3a.md), [4a3b Python](giao-viec-20261026/giao-mtq-4a3b.md), [QD-20261026-03](../QUYET-DINH.md). Đã đọc `_CATALOG` (`k2/sql_ma_tran_tham_quyen.py:43–56`), adapter (`k2/quyen.py:144`), mẫu kiểm trước replay (`k2/crm.py:740`). M0045 chỉ whitelist cặp bảng/lệnh CRM/M1 (`k2/sql_mtq_cong.py:260–350`), chưa dùng được cho L11/M5 dù cùng bảng.

## 1. Từng điểm kiểm quyền

Đường dẫn mã tính từ `src/kho_tri_thuc/`. Viết gọn: **HD**=`k2/hoa_don.py`, **KS**=`k2/kho_so_luong.py`, **PG**=`ha_tang/pg_migrations.py`, **DC**=`k2/sql_ghi_nhan_chung.py`, **DT**=`k2/sql_ghi_nhan_so_tien.py`, **GN**=`k2/ghi_nhan_chung.py`, **NT**=`m4/ghi_nhan_nghiem_thu.py`, **DP**=`m2/tai_hoa_don/dieu_phoi.py`, **UI**=`giao_dien/m2_tai_hoa_don.py`, **SV**=`giao_dien/server.py`, **OP**=`giao_dien/operations.py`.

Trong cột đối tượng, `b(x)` nghĩa chính xác `{"bang":"b","id":x}`; các ID phải lấy/đối chiếu từ dòng DB trong phiên tin cậy. **H**=`kho.hoa_don_danh_tinh`; **K**=`kho.phieu_kho_danh_tinh`; **S**=`master.nguon_pham_vi`; **R**=`giao_tiep.lan_tiep_nhan_nguon`; **A**=`master.anh_xa_nguon`; **B**=`kho.bang_chung_ung_vien`; **Q**=`kho.bang_chung_quy_doi_luong`; **C**=`kho.lien_ket_dong`; **L**=`kho.lien_ket_chung_tu`; **F**=`kho.lo_xuat`; **N**=`m4.duyet_kt_cho`; **G**=`kho.mua_doi_chieu_can_cu`.

Khóa rút gọn **HĐ:a**=`M2:HOA_DON:a`, **Kho:a**=`M5:KHO:a`, **L11:a**=**cả** `M2:L11:a` và `M5:L11:a`; **03B:a**=`M4:03B_DOI_CHIEU:a` cho từng NT, `M2:03B_DOI_CHIEU:a` cho từng hóa đơn. **Raw:a**=`M2:NGUON_THO:a`/`M5:NGUON_THO:a` theo profile. Đây là ô tương ứng theo thiết kế, chưa phải lời gọi đã triển khai. **P**=`PHI_TIEN`, không truyền tiền để so hạn mức; mọi ô được ánh xạ bên dưới đều là P trong catalog hiện tại, kể cả 03B có nhập số tiền. Không dùng `TONG_HOP_DONG`/`XIN_THANH_TOAN` cho các ô này.

Resolver còn thiếu: **rS**=nguồn/scope/profile→toàn bộ PN/phòng và scope NGUON (chưa chốt hợp đồng); **rH/rK**=gốc hóa đơn/phiếu→PN, nguồn và quan hệ phạm vi; **rA**=mapping cũ+mới, subject nguồn và PN đích xác thực; **rL**=đồ thị L11, kiểm hai module cùng phạm vi; **rD**=từng ref NT/hóa đơn và closure các revision. Các resolver này **đều chưa có** ở cổng phiên; phải bổ sung cả cổng hỏi và cổng audit từ chối.

| Tệp:dòng | Hàm/route/hàm SQL | Kiểm hiện tại | Khóa catalog | Đối tượng dựng từ dòng thật | Resolver thiếu | Tiền | Phạm vi/tách nhiệm cần giữ |
|---|---|---|---|---|---|---|---|
| HD:394; KS:281,789 | `nhan`, `l11_nhan_bang_chung` | `kiem_nguon(INTAKE)` | HĐ:LAP; Kho:LAP; L11:LAP | S(scope.id); sau nhận R(receipt.id) | rS | P | Trước blob/replay; scope đúng profile/SHA; L11 scope có PN typed. |
| HD:457,463,472; KS:434,439,447 | `nguon_danh_sach/chi_tiet/raw` | SQL nguồn; `READ_SOURCE`, list còn OR INTAKE | Xem danh sách nguồn: HĐ:XEM/Kho:XEM; raw/chi tiết chứa raw: Raw:XEM | R(id), dẫn snapshot/artifact | rS | P | Không lấy ô Xem hồ sơ thay ô raw; bundle nhiều PN kiểm đủ trước trả bytes. |
| HD:481,490; KS:455,462; KS:851 | `nang_luc_cua_toi`, `pham_vi_cua_toi`, `_l11_bang_chung_trong` | RLS capability; INTAKE OR READ_SOURCE | Theo ô nguồn thực có; **THIẾU CATALOG** nếu coi quản trị capability là hành động riêng | S(id), `master.nguon_profile(id)` | rS | P / chưa phân loại hành động riêng | Metadata phải theo phạm vi hiện hành; không lấy capability làm grant sau bật. |
| HD:507,541,600 | `danh_sach`, `chi_tiet`, DTO `duoc/_nguoi` | `pham_vi/kiem/duoc(M2_READ/M2_*)` | HĐ:XEM; HĐ:DUYET cho nút thao tác | H(d.id), từng dòng list | rH | P | Lọc trước count/phân trang; nút theo cùng snapshot. |
| HD:623; PG:6367,6392; PG:5386 | `mapping_company`, `m2_mapping_cong_ty`, trigger `anh_xa_nguon_kiem` | M2_MAP; M2+CFO V4+SOURCE_MAP cả PN cũ/mới | HĐ:DUYET | A(hien.id); S(scope.id)+`master.phap_nhan(pn.id)` khi tạo mapping | rA+rS | P | Chưa có mapping mới thì không bịa ID; không chỉ kiểm PN mới khi retarget/replay. |
| HD:637; PG:6153,6158 | `mapping_line`, `m2_mapping_dong` | M2_MAP; CFO V4+M2+SOURCE_MAP | HĐ:DUYET | H(d.id), `kho.ban_ghi_nguon(r.id)`→snapshot | rH+rS | P | Bằng chứng literal/revision, dòng nguồn và graph token phải khớp. |
| HD:648; PG:6105 | `xem_xet_nguon`, `m2_xem_xet_nguon` | M2_SOURCE_REVIEW; CFO V4+M2 | HĐ:DUYET | H(d.id), quan sát thuộc H | rH | P | Quyền hiện hành trước cached result; giữ CAS/eligible. |
| HD:659; PG:6293 | `route`, `m2_route` | M2_ROUTE; CFO V4+M2 | HĐ:DUYET | H(d.id), cầu nối/tuyến DB | rH | P | Không biến chọn tuyến thành xác nhận tiền; giữ expected route/basis. |
| KS:475,525,562,605 | `danh_sach/chi_tiet/kiem_ke/ton_nguon`, DTO | M5_READ qua `pham_vi/kiem/duoc` | Kho:XEM | K(d.id); kiểm kê/tồn chưa có producer, không có dòng thật | rK; list theo scope | P | Giữ trạng thái chưa có snapshot, không tạo dữ liệu tồn giả. |
| KS:580; PG:4366 | `kiem_lai_nguon`, `m5_xem_xet_nguon` | M5_SOURCE_REVIEW_V8; CFO V8+M5 | Kho:DUYET | K(d.id) | rK | P | Chỉ quan sát mới nhất; expected ba con trỏ; kỳ khóa. |
| KS:596; PG:4438; PG:5409,5421 | `cap_nhat_mapping`, `m5_anh_xa_v4`, trigger mapping | M5_MAP_V4; CFO V4+M5+SOURCE_MAP | Kho:DUYET | A(hien.id); S(id)+PN DB khi tạo | rA+rS | P | Cả PN cũ/mới; closure L11 bị ảnh hưởng trước đóng mapping. |
| KS:628,630; PG:4588,4604,4681 | `xuat_file_soat`, `m5_co_so_file/file_bat_dau/file_tieu_thu` | M5_READ+M5_FILE_SOAT; M5+KT/KTT/CFO | Kho:XEM | K(d.id), stage DB | rK | P | Kiểm ở cả hai pha và trước replay; hash, kỳ, token toàn đồ thị. |
| KS:729,732 | `tep_file_soat` | `kiem_l11(FILE)` hoặc M5_FILE_SOAT | L11:XEM hoặc Kho:XEM | F(lo.id)→parent L/phieu K | rL/rK, mở riêng F cho M5 | P | Giữ module/mục đích/chế độ, đường dẫn, SHA/độ dài trước bytes. |
| PG:3102,3113; 3838–3849 | `ktt_nguon_duoc/co_nang_luc`, RLS instance/profile/scope/capability | Actor+capability+instance hoạt động | INTAKE→HĐ/Kho:LAP; READ_SOURCE→Raw:XEM; SOURCE_MAP→HĐ/Kho:DUYET | Profile(id), S(id), A(id); instance có khóa text | rS | P | Hai hàm hiện thiếu scope/company trong chữ ký; không sửa thành ANY PN được phép. |
| PG:3592,3605; 3728; 3748,3771,3784 | `nguon_tim_lan_nhan/tieu_thu_capture/anh_xa_hien_hanh/doc_lan_nhan/danh_sach_lan_nhan/doc_tep` | `_KIEM_NGUON`; capability INTAKE/READ_SOURCE/SOURCE_MAP | Như các dòng nguồn trên | S/R/A(id), stage đã ghim | rS+rA | P | Mapping reader còn đọc trực tiếp `nang_luc_nguon` (:3737); thay caller lẫn predicate. |
| PG:4078,4156,4276,4312; 5924,6039; 6841 | `m5_khoa_phieu/tieu_thu_quan_sat/giu_cho_anh_huong`, `nguon_chot_ket_qua`, `m2_tieu_thu_quan_sat`, `l11_tieu_thu_bang_chung` | Actor/stage+INTAKE | Kho:LAP; HĐ:LAP; L11:LAP | Stage→R/S, K/H/B nếu đã có | rS+rK/rH/rL | P | Kiểm trước promote/HOLD/kết quả cuối; không chỉ kiểm ở HTTP. |
| PG:3532,3535; 3857,3861; 4760,6460,6468; 6475–6497 | RLS core/dòng, phieu/hoa_don, derivative, biên nhận, mapping | `ktt_duoc`; mapping OR SOURCE_MAP; ACL vai DB cũ | Xem đúng HĐ/Kho/Raw; ghi theo lệnh cụ thể | Dòng→H/K/R/A/F | rS/rH/rK/rA | P | Có module không đồng nghĩa ô Xem; không nới GRANT/đường chủ bảng. |
| KS:921,928,960; PG:6694,6824,7310,7974 | Tổng quan L11, `luong_con_lai/co_so_ma_hoa/co_so_file` | Python BOTH READ; SQL `l11_quyen_noi_bo(READ)` | L11:XEM | H/K và dòng phiên bản/pool/L(id) | rL | P | Đủ cả hai module cùng phạm vi; không OR tick hai phía. |
| KS:845,851; PG:6955,6969 | `l11_bang_chung/trang`, `l11_danh_sach_bang_chung` | BOTH READ; candidate thêm READ_SOURCE; scope INTAKE OR READ_SOURCE | L11:XEM; raw theo ô nguồn cần lead chốt | B/Q/R/S(id) | rL+rS | P | Trang có nhánh chỉ candidate khi thiếu BOTH; không giữ nhánh này bằng capability cũ. |
| KS:883; PG:6979,6983 | `l11_xac_nhan_bang_chung` | BOTH+CFO V4+SOURCE_MAP | L11:DUYET | B(u.id)→R | rL+rS | P | Giữ proof/hash/revision/đơn vị/căn cứ. |
| KS:890; PG:7200,7205 | `l11_huy_bang_chung` | Guard CFO V4+SOURCE_MAP | **L11:HUY** | Q(q.id)→B/R | rL+rS | P | Không tái dùng DUYET chỉ vì guard cũ tên CFO. |
| KS:897; PG:7331 | `l11_ma_hoa` | BOTH+CFO V4 | L11:DUYET | `kho.hoa_don_dong_phien_ban(b.id)` / `kho.phieu_kho_dong_phien_ban(lw.id)` | rL | P | side DB, proof hợp lệ, hệ số exact; không nhận authority từ body. |
| KS:906; PG:7708,7744,7834 | `lien_ket`; `l11_xem_truoc/xac_nhan/huy` | READ; LINK=KT/KTT/CFO V2 cho cả xác nhận và hủy | L11:XEM / L11:LAP / **L11:HUY** | Hai dòng phiên bản cho preview/lập; C(c.id)→L cho hủy | rL | P | Không dùng LINK chung sau bật; giữ gốc→pool, ngân sách confirmed+held, event đảo. |
| KS:977,979; PG:7989,8032; 8093,8101,8106 | `l11_xuat_file/file_bat_dau/file_tieu_thu`, RLS proof/pool/child/parent/file | BOTH READ+FILE; RLS mới chỉ BOTH module | L11:XEM | L(k.id), F(id), từng bảng con→parent | rL | P | Mỗi pha/replay kiểm hiện hành; parent HD_PHIEU_KHO/chủ M5; không qua resolver M1. |
| DP:156,174,190,386 | `_guard/_quyet_dinh/_tap_profiles` | ID/login nạp lại; INTAKE+READ_SOURCE+M2_READ+ktt_duoc | HĐ:LAP + Raw:XEM + HĐ:XEM theo bước | S(scope.id)+A(mapping.id)→PN | rS+rA; chưa có run DB | P | Kiểm company thuộc scope và mapping duy nhất, không lấy PN từ selection. |
| DP:207,414,458,471,496,506,523,534; UI:481,492,739,914,929,1004 | Start/queue; status/reconcile/SSE/folder/nhận/manifest/hóa đơn lần tải | Binding chủ phiên; kiểm trước/sau I/O, mỗi chunk, trước ghi | Bắt đầu/nhận HĐ:LAP; đọc HĐ:XEM/Raw:XEM theo payload | Binding máy chủ→S/A; nhận xong R/H | rS+rA/rH | P | Không dùng chung LAP cho mọi GET; ghim quyền hiện hành khi trả/replay/nhận. |
| UI:225,241; 1078 | `trang_thai_hang_doi/huy_hang_doi` | Đúng chủ; trạng thái lọc qua profiles; hủy chưa kiểm ô MTQ | HĐ:XEM / HĐ:HUY | q.muc[].chon→S/A DB; queue chỉ trong RAM | rS+rA; resolver queue chưa có | P | Hủy vẫn phải đúng chủ và khóa đúng job; không chọn PN đầu tiên. |
| UI:874,364,394; 1070–1073 | `khoi_dong`, `_kiem_quyen_khoi_dong_lai/khoi_dong_lai` | Có profile; restart còn `vai_tro in KE_TOAN`, chọn mục đầu | Khởi động gắn tải: HĐ:LAP (cần chốt); restart **THIẾU CATALOG** riêng | Profile→S/A; tiến trình chung không có UUID nghiệp vụ | rS; tập PN chịu tác động chưa chốt | Chưa phân loại restart | Không lấy một PN được phép để tác động job của PN khác. |
| GN:504,517; NT:22,27; DC:575,580,584,588,618 | `_kiem_som/_ghim`, NT adapter; `_dc_m2_doc/_dc_kt_toan_cuc/dc_doc_hoa_don/_dc_quyen/_dc_doc_duoc` | NT `kt_kiem/kt_doc_cho`; hóa đơn M2+vai; ghi thêm KT/KTT | 03B:XEM; nguồn NT còn cổng 03A:XEM, hóa đơn HĐ:XEM | N(occurrence_id); H(occurrence_id), version đối chiếu DB | rD+rH; phụ thuộc SQL 03A | P | Mọi nguồn, không bắc cầu M4→M2; NT-only không đòi M2. |
| GN:548,559; DC:1077,1111,1138; DT:122,163,179 | `xem_doi_chieu/lich_su/goi_y_hoa_don`, `_dc_nguon_cua/_dc_xem/_dc_lich_su/_dc_hd_da_gan/_dc_dot_goi_y/_dc_goi_y_hoa_don` | Quyền toàn refs; gợi ý mới kiểm M2 ở cấp PN | 03B:XEM + Xem nguồn tương ứng | G(id)→mọi revision refs; đợt→N; từng H(id) | rD+rH | P | Lọc từng H trước gợi ý; không lộ nguồn của đối chiếu khác qua `da_gan_o`. |
| GN:580; DC:1183,1202 | `luu_doi_chieu/dc_luu` | `_dc_quyen(hop,true)` | 03B:SUA | N/H từng nguồn mới ∪ closure G(id) | rD | P | Trước replay, giữ nguồn bị bỏ khỏi revision mới trong tập kiểm. |
| GN:598; DC:1283,1366; NT:33,37 | `xac_nhan_doi_chieu/dc_xac_nhan`, trigger `_dc_phien_ban_hoan_tat` | Cũng `_dc_quyen(hop,true)`; khóa/producer 03A | 03B:KIEM | G(id), revision chỉ định ∪ hiện hành→N/H | rD | P | Boolean `p_ghi` không phân biệt SUA/KIEM; trigger không được vô tình đòi cả hai tick. |
| SV:598,615,664,771,784,839; 918,980,1285; UI:1091 | Dispatcher M2/M5/L11, raw, bắt lỗi | Token/origin+phiên; service/SQL cũ; catch DataError | Theo từng lệnh trên | Theo service, không tin body | Như trên; audit sau rollback | P | Chưa thấy wrapper ghi `mtq_tu_choi` ở các catch này; token không thay quyền nghiệp vụ. |
| SV:129,172,177,182,187; 1259–1273 | Legacy `/api/nghiem-thu/*` | DEMO-only, actor cố định; gọi Store/NghiemThu | **THIẾU CATALOG** cho bridge riêng; không đồng nhất M4 typed | SQLite id, chưa có ánh xạ N/G | Chưa có | Chưa xác định | Rà/khóa theo readiness §5.3; không tự gán ô 03B cho bridge. |
| OP:615,674,693,697,701,705,719,730,756,771; SV:1037,1045,1158,1162,1166 | Legacy quick: upload/tháng/repropose/rows/AI/score/decide/export/file | Validate/path/lock; actor cố định hoặc tham số; export chỉ cờ cấu hình | **THIẾU CATALOG** cho QuickPosting riêng | SQLite run/item/document; chưa có H/R | Chưa có | Chưa xác định | Có đường hóa đơn; không tự coi APPROVE là HĐ:DUYET phi tiền. |
| OP:846,873,893,900,926,932,1015,1032,1036,1040,1044; SV:1020,1041,1205–1219 | Legacy receive/ingest/job/report/quarantine/session/proposal/shadow | Validate, Store/lock; job lookup ID, actor từ request | **THIẾU CATALOG** cho Store/session riêng | batch/attempt/session/shadow SQLite; chưa có PN DB tin cậy | Chưa có | Chưa xác định | Job không có owner/MTQ tại facade; cần khóa hoặc chia lát riêng trước bật PN liên quan. |

## 2. Chuỗi lát đề xuất (không phải handoff)

Mỗi dòng **≤3 tệp kể cả test**; tên test mới là đề xuất. SQL chạy **tuần tự theo bảng và với 4b/4e/4f** vì chung `pg_migrations.py`; lead đánh số khi gộp. Append migration/hằng mới, không sửa byte migration cũ; giữ chữ ký/ACL cổng phiên. Thay M2/M5 từ bản **đã có closure lock M16** (`PG:8185–8226`).

| Lát | Tệp sửa/tạo (đúng danh sách, gốc mã như trên; test ở `tests/`) | Kết quả, phụ thuộc |
|---|---|---|
| 4i-a | `k2/sql_mtq_lien_module.py`; `ha_tang/pg_migrations.py`; `test_mtq_nguon_scope_sql.py` | Sau lead chốt NGUON: append validator phạm vi nguồn (M0039 hiện chặn NGUON ở :247–249); giữ cấp/thu hồi/audit. |
| 4i-b1…b4 (4 lát tuần tự) | Mỗi lát: `k2/sql_mtq_cong.py`; `ha_tang/pg_migrations.py`; `test_mtq_lmod_resolver_sql.py` | Sau a: b1=rS/rA; b2=rH/rK; b3=rL; b4=rD. Cổng hỏi+audit cùng đối tượng; giữ QD-03. |
| 4i-c | `k2/sql_mtq_lien_module.py`; `ha_tang/pg_migrations.py`; `test_mtq_nguon_cong_sql.py` | Sau b: nguồn/common/RLS/reader mapping, bỏ capability làm nguồn quyền khi bật; khóa/kiểm mọi PN. |
| 4i-d | `k2/sql_mtq_lien_module.py`; `ha_tang/pg_migrations.py`; `test_mtq_m2_sql.py` | Sau c: M2 intake/map/source review/route, trigger mapping và RLS M2; PN cũ+mới trước replay. |
| 4i-e | `k2/sql_mtq_lien_module.py`; `ha_tang/pg_migrations.py`; `test_mtq_m5_sql.py` | Sau d: M5 intake/V4/V8/file hai pha/RLS; giữ closure L11. |
| 4i-f | `k2/sql_mtq_lien_module.py`; `ha_tang/pg_migrations.py`; `test_mtq_l11_sql.py` | Sau e: L11 BOTH, tách LINK→LAP/HUY, CFO→DUYET/HUY theo caller; RLS/FILE. |
| 4i-g | `k2/sql_mtq_lien_module.py`; `ha_tang/pg_migrations.py`; `test_mtq_03b_sql.py` | Sau f **và MTQ-4f/4h**: cổng từng nguồn 03B, SUA/KIEM tường minh, gợi ý/tiền/trigger closure; không giữ vai 03A làm veto sau bật. |
| 4j-a | `k2/hoa_don.py`; `k2/kho_so_luong.py`; `test_mtq_nguon.py` | Sau c–f: **chỉ Python, resolver từ 4i-b1…b3**; nguồn/raw, list/count/DTO/file/intake. |
| 4j-b | `k2/kho_so_luong.py`; `k2/quyen.py`; `test_mtq_l11_service.py` | Sau f và j-a: **chỉ nối Python với resolver đã có**, thay lọc BOTH/FILE/DTO bằng quyết định hiện hành; legacy callback giữ nguyên lúc tắt. |
| 4k | `m2/tai_hoa_don/dieu_phoi.py`; `giao_dien/m2_tai_hoa_don.py`; `test_mtq_m2_tai.py` | Sau c,d,j-a và lead chốt queue/restart: **nối Python với resolver đã có**; phân biệt LAP/XEM/HUY, mọi pha job/SSE/nhận/audit; toàn bộ mock. |
| 4l | `k2/ghi_nhan_chung.py`; `m4/ghi_nhan_nghiem_thu.py`; `test_mtq_doi_chieu.py` | Sau g, 4h: **nối Python với resolver đã có**, mọi nguồn và retry/closure; giữ producer/khóa 03A. |
| 4m | `giao_dien/server.py`; `giao_dien/operations.py`; `test_mtq_bao_phu.py` | Sau j/k/l và các nhóm MTQ-4 còn lại: audit HTTP + khóa đường legacy chưa giải được phạm vi; readiness không cho bật khi còn lỗ. Nếu cần Store/service/readiness ở tệp khác, lead giao lát riêng ≤3 tệp, không mở rộng ngầm. |

**Không có điểm lmod nào chỉ nối Python là xong trên M0045 hiện tại.** Nhãn “chỉ Python” áp sau các phụ thuộc SQL. Test các lát sau: tắt giữ oracle; bật tick/vai cũ trái nhau; PN khác chế độ; thiếu một phía L11/nguồn 03B; retarget/replay sau thu hồi; raw gộp PN; SQL trực tiếp bằng app; audit sau rollback. Worker thuần/mock, lead chạy PG so `NEN-TEST.md`; skip không phải đạt PG.

## 3. Rủi ro

- **Rộng quyền/fallback:** M0045 chưa chọn scope NGUON (:360–368). “Có một ô” ở `ktt_duoc` không đủ cho RLS đọc; cần ô Xem đúng màn. Không lấy PN tắt bù PN bật.
- **Tách nhiệm/phạm vi:** LINK/CFO và `p_ghi` gộp khác ô; giữ BOTH, closure, nguồn/profile/SHA/company, đã nộp, producer/proof và khóa gốc→pool. Bỏ grant vai cũ khi bật, giữ điều kiện nghiệp vụ.
- **Tiền:** ô nhóm này PHI_TIEN; tiền 03B vẫn validate/ghim revision/căn cứ qua `sql_ghi_nhan_so_tien.py`, không phải duyệt thanh toán. Legacy APPROVE chưa rõ; không tự gán PHI_TIEN hay tin tiền client.
- **Job/raw/audit:** owner/cache không thay quyền hiện hành. Kiểm trước replay/blob/chunk/công bố/nhận; ghi từ chối riêng sau rollback, audit lỗi thì chặn. SQLite chưa giải được PN/đối tượng K2.

## 4. Cần lead

1. Chốt NGUON `khoa/quan_he` (instance/profile/SHA/company/kho→PN/phòng) và `{bang,id}` cho mapping mới, một company trong scope gộp. S/Profile có UUID; instance chỉ text. Ai giữ validator NGUON và `ktt_duoc/ktt_pn_cho_phep` chung?
2. Raw/candidate proof L11 dùng `M5:NGUON_THO:XEM` hay thêm BOTH L11? Trang hiện có nhánh chỉ candidate khi thiếu BOTH.
3. Chốt ô khởi động/restart/reconcile vận hành, tập PN bị restart/stop và tham chiếu queue RAM. Restart **THIẾU CATALOG** riêng; không tự đặt bảng giả/chọn PN đầu tiên.
4. Chốt hành động SUA/KIEM ở caller/trigger 03B; phân công thay `kt_kiem/kt_khoa` giữa 4f/4h và 4i-g/4l, giữ ACL/producer.
5. Legacy QuickPosting/Store/bridge còn phục vụ PN nào khi bật? Lead chốt đường khóa/readiness §5.3; chưa tự ánh xạ catalog/tiền hoặc đề xuất ô ngoài thiết kế.

**Đã tự kiểm:** đối chiếu tĩnh thiết kế/catalog/cổng phiên/service/SQL/RLS/trigger và dispatcher; không đọc `var/`, bí mật hay dữ liệu thật; không gọi dịch vụ, mở server/PostgreSQL, sửa mã hoặc commit. Test nghiệp vụ: không chạy (chỉ tài liệu); đạt/tổng và lỗi mới so nền: chưa đo, không tuyên bố xanh.
