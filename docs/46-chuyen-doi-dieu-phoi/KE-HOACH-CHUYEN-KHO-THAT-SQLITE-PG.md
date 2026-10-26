# CD016-KH · Kế hoạch chuyển kho thật SQLite → PostgreSQL

**Bản kế hoạch 26/10/2026 — chưa thực hiện. Chỉ chạy khi Anh ra lệnh riêng.** Đích là **một CSDL PostgreSQL thật chung**, tên CSDL/role tách DEMO; M4 nạp trước, các module khác sau. Chuyển dữ liệu không phải bật vận hành: M0, M2, M3, M4, M9 chỉ go-live cùng lần phát hành khi cả năm qua cổng B. Căn cứ: `CHI-DAO-TU-ANH.md:135–146,191–200`, `CLAUDE.md:19–24`. CD-016 thay yêu cầu “CSDL riêng M4” tại CD-011 bước 4(c).

Tài liệu chỉ suy từ mã/tài liệu; không đọc hay liệt kê kho thật, cấu hình thật, `.env`; chưa biết số kho/tệp, phiên bản schema, số dòng hoặc tổng tiền thực tế. Không thấy TL 52 trong `docs`; không suy thêm nội dung TL 52. Đường dẫn tài liệu điều phối dưới đây tương đối với thư mục này. Ký hiệu mã nguồn: **D** = `src/kho_tri_thuc/ha_tang/database.py`; **F** = `src/kho_tri_thuc/ha_tang/feature_migrations.py`; **K** = `src/kho_tri_thuc/ha_tang/ket_noi.py`; **P** = `src/kho_tri_thuc/ha_tang/pg_migrations.py`; **R** = `src/kho_tri_thuc/m4/review_goc/csdl_hop_dong.py`; **Q** = `src/kho_tri_thuc/m4/sql_review_chep.py`. Ví dụ D:13 là tệp D, dòng 13.

## 1. Bảng nguồn → đích theo schema trong mã

**Kho lõi: 50 bảng, kể cả lịch sử migration.** Đề xuất bảo toàn đầy đủ vào schema tương thích `v12` trong CSDL chung, rồi chỉ chuyển phần nghiệp vụ K2 đã xác minh. Đây là phương án chờ lead chốt, không khẳng định các kho thật hiện dùng đủ 50 bảng. Mỗi cột SQLite `c` → PG `c` cùng tên, gồm các cột ALTER về sau (F:106–108,120–122,202,227,233–236,250–251). Kiểu INTEGER → bigint, TEXT → text COLLATE "C", REAL → double precision, BLOB → bytea; thêm/giữ `rowid` theo bộ chép (`dich_sqlite_pg.py:171–197`, cùng thư mục D).

`Vn` dưới đây là phần tử n của `database.MIGRATIONS`, được dịch khi tạo PG qua **K:184–211,434–436**, không phải migration `M000n` trong P. Đích mặc định `v12`; nếu có nhiều kho độc lập, cần schema riêng đã chốt cho từng kho trong **cùng CSDL**, tránh trùng ID (`K:473–477`).

| SQLite (tệp:dòng) | Bảng PG; toàn bộ cột cùng tên | Migration tạo |
|---|---|---|
| workspace_meta (D:13) | v12.workspace_meta | V1 |
| config_history (D:14) | v12.config_history | V1 |
| artifacts (D:15) | v12.artifacts | V1 |
| attempts (D:18) | v12.attempts | V1 |
| source_records (D:25) | v12.source_records | V1 |
| staging (D:28) | v12.staging | V1 |
| documents (D:32) | v12.documents | V1 |
| issues (D:38) | v12.issues | V1 |
| audit_events (D:41) | v12.audit_events | V1 |
| document_lines (D:46) | v12.document_lines | V2 |
| evidence (D:50) | v12.evidence | V2 |
| schema_migrations (D:78) | v12.schema_migrations: version,checksum,applied_at | Bootstrap K:195 |
| knowledge_versions (F:5) | v12.knowledge_versions | V3 |
| knowledge_events (F:10) | v12.knowledge_events | V3 |
| historical_links (F:14) | v12.historical_links | V3 |
| activity_log (F:18) | v12.activity_log | V3 |
| sessions (F:23) | v12.sessions | V4 |
| proposals (F:30) | v12.proposals | V4 |
| allocations (F:34) | v12.allocations | V4 |
| review_workbooks (F:42) | v12.review_workbooks | V5 |
| review_imports (F:46) | v12.review_imports | V5 |
| decisions (F:49) | v12.decisions | V5 |
| export_batches (F:54) | v12.export_batches | V5 |
| export_items (F:60) | v12.export_items | V5 |
| expected_balances (F:64) | v12.expected_balances | V5 |
| verification_runs (F:71) | v12.verification_runs | V6 |
| field_verifications (F:76) | v12.field_verifications | V6 |
| labels (F:80) | v12.labels | V6 |
| label_events (F:86) | v12.label_events | V6 |
| learning_runs (F:90) | v12.learning_runs | V6 |
| evaluation_datasets (F:95) | v12.evaluation_datasets | V7 |
| quality_runs (F:98) | v12.quality_runs | V7 |
| month_closures (F:101) | v12.month_closures | V7 |
| knowledge_epoch (F:114) | v12.knowledge_epoch | V9 |
| export_item_lines (F:123) | v12.export_item_lines | V10 |
| document_observations (F:128) | v12.document_observations | V10 |
| knowledge_import_batches (F:136) | v12.knowledge_import_batches | V11 |
| knowledge_workbooks (F:139) | v12.knowledge_workbooks | V11 |
| knowledge_review_requests (F:142) | v12.knowledge_review_requests | V11 |
| shadow_exports (F:154) | v12.shadow_exports | V13 |
| shadow_verification_runs (F:160) | v12.shadow_verification_runs | V14 |
| quarantine_records (F:166) | v12.quarantine_records | V15 |
| quick_runs (F:173) | v12.quick_runs | V16 |
| quick_items (F:176) | v12.quick_items | V16 |
| quick_learning (F:181) | v12.quick_learning | V16 |
| cash_account_mappings (F:187) | v12.cash_account_mappings | V17 |
| bank_journal_matches (F:194) | v12.bank_journal_matches | V17 |
| quick_condition_learning (F:203) | v12.quick_condition_learning | V17 |
| export_counters (F:217) | v12.export_counters | V17 |
| quick_exports (F:238) | v12.quick_exports | V19 |

**K2 chưa thay thế toàn bộ V12.** Công cụ `tools/chuyen_sqlite_sang_pg.py` (gọi tắt **C**) đã có các phép chuyển dưới; đây là ánh xạ có điều kiện, không phải sao chép 1:1. Migration dưới ghi nơi tạo bảng; khi triển khai phải áp đủ chuỗi append hiện hành.

| Nguồn từ bảng trên | Đích/cột PG chính; migration; mã chuyển |
|---|---|
| workspace_meta.entity_id | master.phap_nhan.ma; M0001 (P:21); C:160. Không dùng giá trị mặc định thay ánh xạ pháp nhân được duyệt. |
| documents, theo kind ACCOUNT/EXPENSE/COST_CENTER/PROJECT/COUNTERPARTY | master.tai_khoan/khoan_muc_phi/ttcp/du_an (ma_junsky,ten), master.doi_tac + doi_tac_ma_junsky + doi_tac_dinh_danh; M0002 (P:86); C:176,208. |
| artifacts | kho.tep_goc: hash→hash, relative_path→duong_dan, byte_length→kich_thuoc, received_at→nhan_luc; M0003 (P:196); C:266. |
| documents BANK/JOURNAL; document_lines | kho.chung_tu: natural_key→khoa_nguon, business_date→ngay_nghiep_vu, currency→tien_te, amount_minor→so_tien_minor; kho.chung_tu_dong: line_key→stt, core_json→du_lieu, no_minor/co_minor theo nghiệp vụ; M0003 (P:207,238); C:279,319. source_records/evidence chỉ hỗ trợ lấy bằng chứng, chưa chuyển đầy đủ riêng. |
| documents OPEN_ITEM | kho.cong_no_mo: amount_minor→so_tien_minor, các khóa/số dư từ core_json; M0003 (P:261); C:340. |
| quick_items | kho.de_xuat/can_cu, kho.de_xuat_dong/acct_id,base_deb,base_crd, kho.viec_can_duyet; M0006 (P:501,521,569); C:362. Có nhánh bỏ qua bản đã xuất, không được coi là nạp đủ lịch sử. |
| knowledge_versions + knowledge_events | kho.tri_thuc: logical_key→khoa_logic, revision→phien_ban, payload_json→noi_dung, sự kiện→bang_chung.events/trang_thai; M0006 (P:607); C:436. |
| activity_log + audit_events; issues + quarantine_records; cash_account_mappings | nhat_ky.su_kien (luc,hanh_dong,sau), M0005 (P:413), C:463; kho.canh_bao (ma,thong_diep), M0006 (P:666), C:490; master.tai_khoan_ngan_hang (stk_hash,tk_ke_toan), M0002 (P:135), C:507. |

**Chưa có đích chuyển K2 đầy đủ trong công cụ hiện có — cần lát mới nếu yêu cầu vận hành thay V12:** config_history, attempts, source_records, staging, evidence, schema_migrations, historical_links, sessions, proposals, allocations, review_workbooks, review_imports, decisions, export_batches, export_items, expected_balances, verification_runs, field_verifications, labels, label_events, learning_runs, evaluation_datasets, quality_runs, month_closures, knowledge_epoch, export_item_lines, document_observations, knowledge_import_batches, knowledge_workbooks, knowledge_review_requests, shadow_exports, shadow_verification_runs, quick_runs, quick_learning, bank_journal_matches, quick_condition_learning, export_counters, quick_exports. Một số bảng K2 có tên/nghiệp vụ gần giống không đủ chứng minh ánh xạ. Các bảng này vẫn có đích bảo toàn `v12.*` ở trên; không bỏ dữ liệu để đạt số đếm.

**M4 · Nghiệm thu & chi phí dự án: 12 bảng nguồn Review.** Mọi cột nguồn → cột cùng tên trong bảng chép; REAL → numeric bằng Decimal(repr(x)), INTEGER → bigint, ngày/JSON giữ TEXT, giữ NULL/rỗng. Thêm `nguon_id`, hash dòng, metadata nạp; khóa đích = `(nguon_id, PK nguồn)`. `boq_dong.ma_rieng` được bổ sung ở R:204; nguồn cũ thiếu cột này được công cụ nhận thành NULL. DDL đích thuộc **M0038**, đăng ký P:12119–12122; **M0040** thêm `chup_luc`/hàm hiện hành (P:12133–12136; Q:247–249).

| SQLite (tệp:dòng) | Bảng PG (DDL đích Q:dòng); PK nguồn |
|---|---|
| che_do (R:78) | m4.review_chep_che_do (Q:88); id |
| hop_dong (R:81) | m4.review_chep_hop_dong (Q:77); ma_hd |
| tham_so (R:94) | m4.review_chep_tham_so (Q:93); ma_hd,ma_ts |
| phu_luc (R:99) | m4.review_chep_phu_luc (Q:101); id |
| thay_doi_tham_so (R:115) | m4.review_chep_thay_doi_tham_so (Q:116); pl_id,ma_ts |
| boq_dong (R:120) | m4.review_chep_boq_dong (Q:127); id |
| dot_thanh_toan (R:133) | m4.review_chep_dot_thanh_toan (Q:145); ma_hd,dot |
| kl_thanh_toan (R:140) | m4.review_chep_kl_thanh_toan (Q:155); ma_hd,dot,ma_hm |
| khop_hang_muc (R:146) | m4.review_chep_khop_hang_muc (Q:165); ma_hd,khoa_hstt |
| canh_bao (R:151) | m4.review_chep_canh_bao (Q:177); id |
| nhat_ky (R:155) | m4.review_chep_nhat_ky (Q:190); id |
| tham_so_nguon (R:158) | m4.review_chep_tham_so_nguon (Q:201); ma_hd,ma_ts |

Không bảng Review nào thiếu đích chứng cứ. Chưa tự tạo seal, run, BOQ vận hành hay quyền từ `che_do.sua`; `master.hop_dong`/`m4.ho_so_hop_dong` phải tồn tại đúng pháp nhân/dự án trước nạp (Q:3–10,39–45). Tệp được các cột đường dẫn tham chiếu **chưa được công cụ này chuyển**; phạm vi M4-CD3 còn chờ (`TRANG-THAI.md:465–467,480–482`).

## 2. Công cụ và điều kiện an toàn

Dùng lại **M4 CD1/CD2**: `tools/chuyen_review_sqlite_sang_pg.py:75–128,131–145,289–310,381–397` mở nguồn chỉ đọc, từ chối WAL/journal chưa đóng, kiểm SHA trước/sau và ngay trước commit; nạp đủ trong một giao dịch. Cùng `nguon_id` chỉ replay khi khóa/nội dung/metadata khớp; ảnh chụp phát sinh dùng ID mới, không ghi đè (Q:12–25). `--thu` chỉ kiểm nguồn/ánh xạ và tổng, **không thay thế** lần nạp vào PG tạm. CD2 `src/kho_tri_thuc/m4/review_doi_chieu.py:1–7,176–269` đọc PG cùng snapshot READ ONLY, so từng ô độc lập với hash của bộ nạp.

Kho lõi: tái dùng bộ chép `ha_tang/sao_chep_bang.py:137–196` dưới `src/kho_tri_thuc/` (một transaction, FK, hash nội dung, rowid/sequence). **Cần lát bổ sung wrapper chỉ đọc + SHA + replay kiểm chứng**, theo cách CD1/CD2. Không chạy nguyên `tools/chep_v12_sang_pg.py`: dòng 89 gọi D.connect có migrate/WAL nguồn (D:99–106), cờ `--lam-lai` có DROP SCHEMA (dòng 79–87). Không dùng cờ này. Công cụ C có upsert, tắt trigger và đối chiếu phạm vi hẹp (C:119–156); phải review trên schema hiện hành trước nạp CSDL chung. Không tự suy ID/pháp nhân, không sửa tay dữ liệu lệch.

## 3. Sao lưu, chạy thử và thứ tự thực hiện khi được lệnh

1. Lead chốt danh sách nguồn/đích, ánh xạ, thời điểm dừng ghi và người nghiệm thu. Sao lưu SQLite **nhất quán**, các tệp liên quan và cấu hình phục hồi bởi người được phép vào `D:\Claude\Phan mem ho tro ke toan\LUU-TRU\<mã-lần>-<ngày-giờ>`, kèm SHA256, giờ chụp, phiên bản phần mềm/schema. Không copy riêng `.db` đang có WAL; không checkpoint/sửa nguồn để phục vụ thử. Giữ nguyên nguồn.
2. **M4 trước:** sao lưu Review theo CD-011 bước 4(a); chạy thử trên bản sao vào PG tạm **tách DEMO/test, kiểm soát như dữ liệu thật**; đủ migration → nạp → CD2 khớp 100% → thử replay. Bản sao có dữ liệu thật không được dùng làm test/fixture/DEMO hoặc gửi Cloud.
3. Tạo CSDL thật chung, role riêng, kết nối `*.that.local.json` ngoài git; áp đủ migration append → nạp M4 → đối chiếu độc lập → `pg_dump` + SHA → biên bản báo Anh. Theo CD-016:200, tài liệu ghi chưa tạo CSDL riêng M4; nếu thực tế khác, giữ lại và trình phương án gộp, không xóa.
4. **Kho lõi/các module khác sau, bằng lệnh riêng của Anh** mở quyền đúng nguồn: lặp sao lưu → bản sao/PG tạm → nạp vào CSDL chung → đối chiếu → dump. Trong mỗi nguồn: metadata/master/pháp nhân → bảng cha → bảng con theo FK; không trộn hai kho có ID trùng hoặc chạy hai bộ nạp vào cùng đích. Migration và kiểm nguồn tách bước; phần nạp mỗi nguồn phải nguyên tử, không hứa một transaction xuyên SQLite/PG/tệp.
5. Trước chuyển hẳn: dừng ghi nguồn ở mốc đã chốt, chụp cuối và nạp phần phát sinh (M4 dùng ảnh đầy đủ mới), đối chiếu lại, sao lưu PG. Chỉ đổi cấu hình/bật theo lần phát hành chung khi đủ cổng B; không bật module lẻ (`CHI-DAO-TU-ANH.md:141–144,194–197`).

## 4. Biên bản đối chiếu và điều kiện đạt

Mỗi lần lưu trong LUU-TRU: mã lần/chụp, SHA nguồn trước–sau, SHA backup/dump/tệp, bản mã và migration, đích/role (không DSN/mật khẩu), bảng ánh xạ đã duyệt, người thực hiện/kiểm, thời điểm, kết quả và lỗi. Mẫu cột: **bảng · số nguồn · số đích trong phạm vi lần nạp · thiếu/thừa/trùng khóa · lệch nội dung · tổng tiền/đơn vị · kết luận**; số thực tế để trống tới khi được phép đo.

- **Dòng/khóa:** đủ 50 bảng lõi/12 bảng Review theo schema được xác nhận; PK, UNIQUE, FK và từng ô/hash nội dung khớp. V12 kiểm cả rowid, sequence và ngoại lệ duy nhất là khóa `workspace_meta.v13_nap_tu_sqlite` do bộ nạp thêm (`sao_chep_bang.py:176–192,201–237`). K2 dùng tập khóa nguồn đã ánh xạ trong CSDL chung, không so toàn bộ tổng đích với riêng một nguồn.
- **Tiền:** M4 so tổng `gia_tri_hd`, BOQ tách GOC/THAY/THEM/BO (cả `thanh_tien_ghi` và `kl × don_gia`), từng HĐ/đợt: `gt_ky,gt_luy_ke,giu_lai,thu_hoi_tu,gt_tt_ky`, khối lượng × đơn giá; không coi tổng thay đổi là BOQ hiệu lực (`tools/chuyen_review_sqlite_sang_pg.py:233–257`). Tool gắn VND; cần xác nhận đơn vị nguồn. Kho lõi so amount_minor, Nợ/Có và số dư theo pháp nhân/tiền tệ/kỳ; không cộng khác tiền tệ, không bù lệch giữa dòng, giữ NULL khác 0.
- **Đạt:** 100% phần nguồn trong phạm vi đã duyệt, không dòng lỗi/bỏ qua chưa giải thích; SHA không đổi; replay không thêm dòng/đổi số liệu. Lệch bất kỳ → dừng bước đó. CD2 chạy sau commit: lỗi đối chiếu **không tự rollback** phần đã nạp (`tools/chuyen_review_sqlite_sang_pg.py:387–412`); giữ đích cách ly, chưa bật. Báo cáo có số tiền/khóa chỉ lưu nội bộ, không dán chat (`TRANG-THAI.md:382`).

## 5. Đường lùi, rủi ro và Cần Anh/lead

**Đường lùi:** SQLite gốc giữ nguyên; từ lúc chốt chuyển, chỉ đọc. Trước khi PG có ghi nghiệp vụ mới, lead dừng bản PG, trả cấu hình/bản ứng dụng về SQLite tại mốc sao lưu; chỉ mở lại quyền ghi sau khi Anh/lead chốt và bảo đảm một nguồn ghi. Sau khi PG đã ghi mới, SQLite đã cũ: dừng ghi, dump + SHA PG, kiểm kê chênh lệch; chưa có công cụ đồng bộ ngược đầy đủ nên không tự quay lại hoặc ghi đè. Phục hồi PG vào đích mới từ backup đã thử, hoặc trình phương án xử lý phát sinh; giữ nguyên cả hai kho, không DROP/xóa.

**Rủi ro chính:** bản sao thiếu WAL; trùng ID/khóa dùng chung giữa kho; chuyển K2 thiếu lịch sử; nguồn đổi sau khi chụp; REAL/đơn vị/ngày không rõ; đường dẫn tệp không còn hợp lệ; quyền/RLS sai pháp nhân. M4 hàm hiện hành lấy lần chụp mới nhất toàn bộ của **một CSDL Review**: nhiều nguồn cần thiết kế thêm (Q:23–37). M0040 từ chối nâng khi bảng nguồn đã có dữ liệu chưa chốt `chup_luc` (Q:239–247).

**Cần Anh/lead (chặn bước phụ thuộc, không đoán):**

- Anh ra lệnh riêng cho chuyển kho lõi; xác nhận danh sách nguồn/pháp nhân, vai trò người được đọc, phạm vi tệp, lịch dừng ghi, tiêu chí nghiệm thu/đường lùi. Lead chốt tên CSDL/role và cách bảo toàn `v12.*` hay chuyển K2 đầy đủ; nhiều kho phải có ánh xạ schema/ID rõ.
- Chốt `ma_hd → HĐ/pháp nhân/dự án` và tạo hồ sơ vận hành trước nạp M4 (`TRANG-THAI.md:326,406,467`); CSV tool dùng `ma_hd,hop_dong_id,du_an_id`, pháp nhân kiểm qua hồ sơ, không tự thêm cột (`tools/chuyen_review_sqlite_sang_pg.py:131–145`). Chốt một/nhiều CSDL Review, đơn vị tiền, tệp đính kèm/CD3 và cách xử lý các bảng chưa có đích K2 đầy đủ.
- Lead giao lát wrapper nguồn chỉ đọc/SHA/replay và đối chiếu kho lõi; nguồn khác phiên bản chỉ nâng **bản sao làm việc** bằng lát được duyệt. Chốt quyền/RLS/ma trận thẩm quyền trước bật; QD-20261026-08, B11 tại `docs/QUYET-DINH.md` yêu cầu pháp nhân còn đường cũ chưa được bật.
- Lead kiểm bằng dữ liệu giả theo `CLAUDE.md` mục 5; nền PG mới nhất trong repo là **v5: 3214 ok / 20 ERROR / 63 FAIL / 78 skip, 0 treo** (`NEN-TEST-PG.md:71–75`), so mã lỗi và skip, không coi toàn bộ đã xanh. Lát tài liệu này không chạy test, server hay PostgreSQL; chạy thử bản sao thật là bước vận hành riêng. `4-KE-HOACH-LEAD.md:133–139` cũng tách việc test thuần khỏi kho thật.
