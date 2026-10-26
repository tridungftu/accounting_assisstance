# KK-MA-HOA-LUU-RIENG · CD-019 — bản trình duyệt

26/10/2026 · **Chỉ thiết kế; chưa bật mã hóa, sao lưu, khôi phục, di chuyển hay đo.** Đề xuất mã hóa định danh + sao lưu trước; giữ số tiền/ngày nguyên dạng; BitLocker chờ số đo và Anh quyết. Một CSDL thật chung sau XS-5b; go-live M0/M2/M3/M4/M9 cùng đợt khi đủ cổng B (CD-016/018).

**Căn cứ đã đọc:** [CD-016/018/019](CHI-DAO-TU-ANH.md); TL 53 §8 (`D:\Claude\Phan mem ho tro ke toan\53-kien-truc-xuong-song-engine-module.md`); [kế hoạch chuyển kho](KE-HOACH-CHUYEN-KHO-THAT-SQLITE-PG.md), [checklist phát hành](CHECKLIST-PHAT-HANH.md), [bản đồ dữ liệu](KK-VUNG-DU-LIEU.md). Nguồn mã dưới `src/kho_tri_thuc/`: **P**=`ha_tang/pg_migrations.py`; **D/F**=`ha_tang/database.py,feature_migrations.py`; đã rà **22 tệp** `k2/sql_*.py`, `m4/sql_*.py`. Kiểm kê từ schema/caller, không từ dữ liệu. `v12` là schema đích **đề xuất** của kho SQLite cũ, tên thực chờ lead; SQLite nguồn chưa có schema này.

## 1. Danh sách để Anh duyệt

**18 nhóm duyệt: 10 A / 5 B / 3 C**, không phải số cột hay số dòng thực tế. A=mã hóa ngay sau duyệt; B=cân nhắc phạm vi; C=không mã hóa. Dấu `{a,b}` liệt kê cột. P có **6 cột bytea** dự kiến giữ bí mật và 6 cột hash tương ứng; tên cột không chứng minh runtime đã mã hóa/HMAC.

| schema.bảng.cột | Module | Loại dữ liệu | Mức | Lý do; tìm/khớp/khóa hiện có → cách giữ chức năng |
|---|---|---|---|---|
| `master.doi_tac.cccd_mh`, `master.nhan_vien.cccd_mh` | M0 | bytea; CCCD | A | `doi_tac.cccd_hash` UNIQUE có điều kiện; HMAC thay hash trần, giữ UUID để JOIN. P:93–103,401. |
| `master.doi_tac_dinh_danh.{gia_tri,gia_tri_mh}` | M0/M1 | text/bytea; CCCD/STK/MST cá nhân | A | CHECK buộc STK/CCCD chỉ có bản mã; UNIQUE `(loai,gia_tri_hash)` khi còn hiệu lực. MST hiện vẫn text → bổ sung đường mã hóa + HMAC, không phá CHECK. P:117–134. |
| `master.tai_khoan_ngan_hang.stk_mh`, `master.nhan_vien.stk_mh` | M0/M1 | bytea; số tài khoản | A | `stk_hash` dự kiến tra chính xác, chưa chứng minh caller đang dùng; UNIQUE nội bộ `(phap_nhan_id,tk_ke_toan)`/nhân viên `(phap_nhan_id,ma_junsky)` giữ nguyên. P:135–147,399. |
| `master.doi_tac.mst` với `loai='CN'` | M0 | text; MST cá nhân | A | Hiện UNIQUE toàn cột MST khác NULL. Token phải giữ miền duy nhất hiện hành, không tự thu hẹp theo PN. P:92,102. |
| `v12.cash_account_mappings.bank_account` | M1/lõi | TEXT; STK | A | PK, WHERE và ON CONFLICT trong `giao_dien/quick.py:143–151`, `de_xuat/engine.py:105` → HMAC làm khóa tra, bản mã riêng; không đổi cách chuẩn hóa. F:187–193. |
| `v12.quick_condition_learning.condition_value` khi `BANK_ACCOUNT` | M1/lõi | TEXT; STK đối ứng | A | UNIQUE `(condition_type,condition_value,revision)` + index lookup → token cùng revision; `quick.py:210–224,810–813`. |
| `v12.source_records.raw_json`, `v12.documents.core_json`, `v12.document_lines.core_json`, `v12.knowledge_versions.{payload_json,logical_key}` | Lõi/M1 | TEXT JSON/khóa; định danh | A | Bản sao STK có trong account/counterparty_account, catalog BANK_ACCOUNT; logical_key UNIQUE theo category/revision có thể chứa STK (`quick.py:1069–1077`). Tách phần nhạy cảm, token hóa khóa; so khớp sao kê vẫn dùng giá trị chuẩn hóa/token. D:25–36,46; F:5. |
| `master.crm_bao_gia_rev.du_lieu`, `master.crm_hd_soan_rev.du_lieu`, `master.crm_hd_ky.tom_tat` | CRM | jsonb; liên hệ cá nhân | A | SĐT/email cá nhân nếu trường khai báo `pii=true`; chưa thấy cột scalar SĐT/email trong DDL đã rà. Dùng danh mục `master.crm_danh_muc_truong` (P:9671–9685), chốt JSON path; giữ revision/hash nội dung logic. |
| `m4.tham_so.{gia_tri,gia_tri_may,trich_dan}`, `m4.trich_xuat.{phieu,ket_qua}`, `m4.tham_so_lich_su.{truoc,sau}` | M4 | text/jsonb; địa chỉ/giấy tờ cá nhân | A | Chỉ phần định danh/địa chỉ cá nhân khi có; không mã hóa giá trị tiền/ngày. PK `(hop_dong_id,ma)` không đổi; bản sao lịch sử phải cùng phạm vi. P:8852–8930; `m4/sql_m17.py`. |
| `bao_mat.mask_bi_danh.gia_tri_that_mh` | Cổng Mask | bytea; bảng ánh xạ | A | UNIQUE `(loai,gia_tri_hash)`; giữ quyền gateway, không tạo bộ che mới. P:467–477; không đưa tiền/ngày vào tập che (TL48; `tri_thuc/cong_ai.py:283`). |
| `master.phap_nhan.mst`, `master.doi_tac.mst` tổ chức; `kho.hoa_don_danh_tinh.mst_ban` | M0/M2 | text; MST/ĐKDN tổ chức | B | Đề xuất mã hóa sau duyệt; MST bán thuộc UNIQUE bộ danh tính hóa đơn (P:5240–5255) → HMAC thay đúng thành phần. Chưa thấy cột ĐKDN riêng; không suy MST luôn là số ĐKDN. |
| `master.doi_tac.{ten_phap_ly,ten_chuan_hoa}`, `master.nhan_vien.{ten,zalo_id}`, `master.nguoi_dung.{ten,dang_nhap}` | M0 | text; tên/liên hệ | B | Tên CN nhạy cảm; tên chuẩn có GIN trigram, đăng nhập UNIQUE. HMAC chỉ tìm chính xác; tìm gần đúng phải reader được quyền hoặc Anh chấp nhận giảm chức năng. |
| `kho.chung_tu.{doi_tac_tho,mo_ta,du_lieu}`, `kho.chung_tu_dong.{mo_ta,du_lieu}` | M1/chung | text/jsonb | B | Có khả năng chứa định danh lẫn tiền; rà writer/JSON path, định danh xác nhận được nâng A. Giữ khóa nguồn/UUID; không mã hóa cả khối có tiền/ngày. P:207–259. |
| `kho.ban_ghi_nguon.row_raw`, `kho.hoa_don_phien_ban.raw_header_states`, `m4.review_result.ket_qua` | M2/M4 | jsonb; nguồn/kết quả | B | Kho chứa linh hoạt, chưa xác minh trường cá nhân. Nếu có phải theo A và xử lý cả raw/file; giữ semantic hash, seal, replay. P:1876,5266; `m4/sql_review.py:108`. |
| `nhat_ky.su_kien.{truoc,sau,can_cu}`, `v12.audit_events.details_json`, `v12.activity_log.details_json`, `v12.quick_items.{proposal_json,decision_json}` | Chung/lõi | jsonb/TEXT JSON | B | Bản sao phát sinh; chỉ ghi ID/version/mã lỗi ở luồng mới, tách định danh nếu có. Rà thêm payload xuất/learning/quan sát tại F; không tuyên bố bảng A đã sạch khi bản sao còn plaintext. |
| `kho.chung_tu.so_tien_minor`, `kho.chung_tu_dong.{no_minor,co_minor}`, `v12.documents.amount_minor`; giá trị lương/thu nhập | Chung/M1 | bigint/INTEGER/numeric | C | **Không mã hóa số tiền**, kể cả lương cá nhân (TL48 theo yêu cầu lát). Không thấy scalar lương/thu nhập riêng; `BANG_LUONG` là loại chứng từ. Bảo vệ bằng quyền/RLS và tách danh tính A. |
| `kho.chung_tu.ngay_nghiep_vu`, `kho.hoa_don_phien_ban.ngay_lap`, `master.nhan_vien.{valid_from,valid_to}` | Chung | date/timestamptz | C | Không mã hóa/che ngày; giữ lọc, sắp xếp, đối chiếu. |
| Các PK/FK `id,phap_nhan_id,doi_tac_id,hop_dong_id,du_an_id` trên bảng tương ứng | Chung | uuid | C | JOIN/RLS dựa ID, PN/dự án, danh tính/quyền (`master.ktt_*`), không dựa ciphertext. Không biến token thành căn cứ cấp quyền. |

**Khoảng trống:** chưa thấy cột CMND/hộ chiếu riêng hay loại định danh tương ứng trong CHECK của `doi_tac_dinh_danh`; đề xuất đưa cùng A, bổ sung loại bằng migration sau duyệt, không nhận vơ đã hỗ trợ. SĐT/email/địa chỉ cá nhân phải chốt path theo danh mục/caller; `mst_ban` của cá nhân phải theo A, không theo nhóm tổ chức B. HMAC chuẩn hóa theo loại, không bỏ số 0 đầu; STK dùng lại `bank_account` (`giao_dien/v9b.py:25`), ngân hàng/PN chỉ thêm vào miền nếu đúng hợp đồng khớp/UNIQUE. UUID JOIN và RLS giữ nguyên; token lộ quan hệ bằng nhau, không là dữ liệu công khai. UI chỉ hiện cuối 4 ký tự hoặc che email/SĐT; xem đủ cần quyền riêng có audit ID, không audit giá trị.

## 2. pgcrypto và vòng đời khóa

**Một cổng mã hóa hạ tầng dùng chung**, Python đọc khóa lúc chạy; SQL gọi `pgp_sym_encrypt(text,key,'cipher-algo=aes256,compress-algo=0')` → `bytea` OpenPGP nhị phân (không armor), `pgp_sym_decrypt(bytea,key)` → text. Không dùng mã hóa deterministic/`encrypt()` thô. Truyền giá trị/khóa bằng **bind server-side psycopg**, tuyệt đối không f-string/literal SQL. Thêm `<truong>_key_ver smallint` và CHECK bản mã/version cùng NULL hoặc cùng có; JSON chỉ tách path nhạy cảm sang kho bản mã gắn row-ID/revision/path, để tiền/ngày ngoài. Metadata chỉ chứa số phiên bản. Python chuẩn `secrets` sinh 32 byte ngẫu nhiên (khóa PGP biểu diễn base64url); `hmac`/`hashlib` tạo HMAC-SHA256, lưu hex 64 ký tự tại `<truong>_lookup` + `lookup_ver`, khóa HMAC độc lập. Không thêm thư viện/engine thứ hai.

**Khóa:** đề xuất `D:\DU-LIEU-KE-TOAN\bi-mat\cot\vNN.dpapi`, khóa lookup tại `bi-mat\tra-cuu\`; ngoài CSDL, repo, kho file và sao lưu. NTFS tắt inheritance, chỉ tài khoản dịch vụ **ứng dụng** đọc, người quản khóa ghi, SYSTEM quản trị; PostgreSQL service và Users/Everyone không đọc. Đề xuất **DPAPI CurrentUser** gắn tài khoản chạy ứng dụng (qua Windows API/`ctypes` chuẩn); không chọn LocalMachine vì phạm vi giải mã rộng hơn. Cần kiểm profile dịch vụ. Bản cứu hộ khóa nguyên gốc được mã hóa riêng, giữ offline ở ổ khác; DPAPI không tự chuyển được sang máy/tài khoản mới. Không đưa khóa vào cấu hình kết nối, dòng lệnh, GUC/custom setting, bảng, hàm SQL hoặc log; chỉ giữ RAM trong vòng đời worker.

**Chống lọt khóa:** bind giữ placeholder trong `pg_stat_activity`, không bảo vệ khi driver nội suy phía client. DBA chốt cho session/role crypto: `log_statement=none`, `log_min_duration_statement=-1`, `log_min_duration_sample=-1`, `log_transaction_sample_rate=0`, `log_parameter_max_length=0`, `log_parameter_max_length_on_error=0`, `log_min_error_statement=panic`; rà audit/auto_explain/pool/tracing không ghi tham số, lỗi/CONTEXT. Log ứng dụng chỉ SQLSTATE+mã thao tác; không traceback/`DETAIL` chứa giá trị. Reader/writer theo XS-5b, không cấp hàm giải mã tùy ý cho module/AI. DEFINER nếu cần phải cố định search_path, kiểm PN/quyền, owner tách runtime, REVOKE EXECUTE PUBLIC. Kiểm bằng **khóa canary giả** ở ca thành công/lỗi, log/pg_stat_activity; chưa đạt thì chưa bật. pgcrypto không chống được superuser/OS admin; kết nối local hoặc TLS khi qua mạng. XML/PDF/raw gốc vẫn có thể chứa định danh: cần ACL/kho file chung và phương án bảo vệ riêng, không suy mã hóa cột đã mã hóa toàn kho.

**Xoay:** thêm v2, writer chỉ ghi v2, reader chấp nhận v1/v2; khóa hàng/batch 500 theo PK, transaction từng lô, retry idempotent/CAS tránh ghi đè cập nhật. Kiểm số đủ điều kiện = đã đổi + còn lại + lỗi, NULL giữ nguyên; giải mã so bằng trong RAM, kiểm HMAC/UNIQUE/replay và tiền/ngày không đổi; không in giá trị. Lookup xoay độc lập: giữ token cũ/mới, dual-read/write, lấp đủ rồi đổi index nguyên tử; bảo toàn UNIQUE toàn miền, không chỉ thêm `lookup_ver` vào unique để né trùng. Chỉ ngừng dùng khóa cũ sau kiểm 100%, restore thử và hết nhu cầu đọc backup cũ; không tự xóa khóa/backup. Với revision/trigger bất biến CRM/M2/M4, lead phải duyệt migration đổi **biểu diễn lưu trữ**, bảo toàn hash nội dung logic/seal; không tắt trigger hàng loạt. Plaintext lịch sử, heap/WAL và bản sao cũ còn tồn tại → chưa được báo “đã bảo vệ toàn bộ”.

## 3. Sao lưu mã hóa và khôi phục một lần

**Đã xác minh máy (chỉ binary/phiên bản):** `C:\Program Files\Git\usr\bin\gpg.exe` **2.4.9**, có `openssl.exe`, `tar.exe`; PostgreSQL 16 có `pgbench.exe`, `pg_dumpall.exe`. **Chưa tìm thấy `pg_dump.exe`/`pg_restore.exe` trong PATH và `C:\Program Files\PostgreSQL\16\bin`**: lead xác nhận vị trí/bộ client tương thích trước chạy; không giả định cài mới. `tools/cai_postgres.ps1` khai báo PG16 + pgcrypto, không chứng minh cụm hiện tại đã có. `tools/sao_luu_pg.py` chỉ là `LEGACY_DB_FALLBACK` PG→SQLite DB-only; `ha_tang/backup.py` là bundle legacy + raw; cả hai chưa thay được full dump K2 mã hóa.

**Luồng đề xuất:** runner dùng `subprocess` binary pipe `pg_dump --format=custom --no-password` → GPG public-key encryption (AES256, recipient fingerprint ghim cố định, keyring riêng ngoài repo) → tệp mới độc quyền `.partial.gpg` dưới `D:\DU-LIEU-KE-TOAN\sao-luu\<mã-lần>\`. Không pipe nhị phân qua PowerShell text, không tạo dump plaintext. Không mật khẩu/DSN trên argv/log; runner nhận cấu hình kết nối qua cơ chế hiện có. Chỉ công bố khi cả hai exit=0, SHA256 ciphertext và kiểm giải mã/restore đạt; lỗi giữ partial, báo mã đã làm sạch. Checksum và số đếm ghi vào biên bản hiện có, không lập manifest hash/quy trình kiểm riêng.

Khóa sao lưu **khác khóa cột/HMAC**: máy chỉ giữ public key tại `bi-mat\sao-luu-public\`; private key có passphrase trên ổ ngoài offline do Anh/người giữ khóa giữ, dự phòng bản thứ hai riêng. Một bộ phục hồi cần private backup key **và mọi phiên bản khóa cột/lookup**; không bỏ các khóa đó vào cùng bundle dữ liệu. Đề xuất 23:00 mỗi ngày và trước/sau nâng/nạp; chép ciphertext sang ổ vật lý khác hằng ngày, ổ ngoài hằng tuần, kiểm SHA sau chép. Lịch giữ đề xuất 30 ngày + 12 bản tháng; chỉ phân loại giữ, **không tự xóa bản cũ**. Một ổ D không là dự phòng mất ổ/ransomware.

**Thử một lần trên CSDL thử mới, chỉ DEMO giả; runbook cũng áp dụng khi được phép phục hồi thật ở vùng cách ly:**

1. Lead cấp cụm/cổng riêng ngoài cụm cổng A, CSDL đích mới trống, ngắt mọi job/kết nối ra ngoài; ghi giờ bắt đầu. Chuẩn bị cùng major PG/extensions, role/owner/GRANT/RLS (globals dùng `pg_dumpall --globals-only --no-role-passwords`, cũng mã hóa); không mang mật khẩu role cũ.
2. Tạm ngừng writer/job, đợi transaction xong; chụp dump và kho file cùng mốc. Tar kho file → GPG không ghi tar rõ; ghi riêng bản phần mềm/migration, cấu hình phục hồi được phép, số bảng/dòng, tổng Nợ/Có/tiền theo PN/tiền tệ/kỳ. Giữ writer dừng tới khi chụp đủ; `pg_dump` không bao gồm file/role/config ngoài DB.
3. Người giữ khóa kiểm SHA ciphertext, mở private key qua pinentry (không argv); đưa khóa cột/lookup cứu hộ vào vùng khóa đích và bọc DPAPI cho tài khoản mới. Không ghi đè nguồn hoặc CSDL đang dùng.
4. GPG giải mã **stream** → `pg_restore --exit-on-error --single-transaction --no-owner` vào DB trống, không `--clean`. Precreate role/restore owner theo mapping đã duyệt; kiểm lại ACL/RLS, không chỉ dựa `--no-owner`. Giữ DB cách ly cho tới khi GPG xác nhận toàn vẹn/giải mã thành công và pg_restore exit=0; lỗi cuối stream không được coi restore đạt. Kho file giải mã/giải nén vào thư mục phục hồi mới, chặn đường dẫn thoát thư mục.
5. So **100%** số bảng/dòng từng bảng, PK/FK/UNIQUE, tổng kiểm soát; kiểm file đủ/hash đúng, giải mã các phiên bản khóa, quyền sai PN bị chặn. Chạy lưu/đọc lại XML–M4–CRM giả và khớp STK, replay không tăng dòng. Lệch bất kỳ → dừng, giữ đích cách ly, không sửa tay.
6. Ghi phút dump/mã hóa/chép/giải mã/restore/kiểm và tổng tới sẵn sàng, dung lượng, số dòng lệch, tổng lệch, kết luận/người kiểm vào biên bản đợt. **Hiện 0 lần thử, chưa có RTO đo được**; mục tiêu đề xuất RPO ≤24 giờ, RTO ≤2 giờ chờ Anh chốt. Backup thật chỉ thử ở vùng phục hồi được cấp quyền, tuyệt đối không đưa vào DEMO/fixture.

## 4. Bộ đo trước/sau BitLocker — lead chạy sau, không phải kết quả

Chỉ dùng cụm DEMO tạm/bản sao **dữ liệu giả**, data+WAL+kho-file dưới `D:\DU-LIEU-KE-TOAN\do-bitlocker\`, cổng do lead cấp, không chạm cụm DEMO đang phục vụ cổng A. Lead xác minh trạng thái ổ D/thuật toán/progress bằng `manage-bde -status D:`; chưa mã hóa thì lấy baseline. Nếu đã bật, không tự tắt để lấy baseline. BitLocker mã hóa **volume**: di chuyển benchmark vào D không cô lập ảnh hưởng lên dữ liệu khác trên D; Anh quyết cửa sổ bật sau đo.

| Phép đo cố định | Quy mô và số lần mỗi trạng thái |
|---|---|
| pgbench PG16, DB riêng `kk_cd019_bench` | Khởi tạo **một lần trên DB mới** `pgbench -i -s 100`; warm-up 60s; `pgbench -b tpcb-like -c 1 -j 1 -T 180 -P 10 -r`, rồi `-c 8 -j 4` cùng tham số. Mỗi cấu hình **5 lượt**; giữ fsync/synchronous_commit/full_page_writes bật, không chạy test khác song song. Host/port/user/db qua cấu hình riêng, không DSN trong báo cáo. |
| Lưu thật bằng luồng phần mềm, dữ liệu DEMO | **30 lượt/luồng**, 3 lô ×10: nhập XML giả 1 hóa đơn/10 dòng; lưu M4 1 hồ sơ/10 tham số + 1 tệp giả 1 MiB; lưu CRM 1 báo giá/10 dòng/4 đợt, đọc lại. Mỗi lượt ID mới, dữ liệu/quyền tương đương, không Word COM/Cloud/thuế/Junsky. Đo từ nhận yêu cầu đến commit và đến đọc lại thành công. |

Ghi vào biên bản đợt: commit/migrations, PG/config, máy/CPU/RAM/ổ/dung lượng trống, trạng thái khóa cột, số dòng trước/sau, giờ, lượt; pgbench TPS/latency/error, thao tác phần mềm median/p95/max/ms, CPU/disk latency. Giữ cấu hình, quy mô, cách warm-up, snapshot giả tương đương trước/sau; dùng DB mới cho bộ ứng dụng khi cần, không xóa/reset DB cũ. Sau BitLocker **mã hóa xong**, máy rảnh, cùng điện năng/cache rule, chạy lại toàn bộ. Báo Anh nếu TPS giảm **>10%** hoặc median/p95 lưu tăng **>15% và >20ms** qua ít nhất 3/5 lượt (nghiệp vụ: 2/3 lô); mọi lỗi/mất dòng/lệch tiền báo ngay. Nếu biến thiên giữa lượt >10%, đánh dấu chưa kết luận và đo lại lúc rảnh. Ngưỡng là đề xuất; không suy kết quả từ pgbench thay luồng lưu.

## 5. Chuyển DEMO lưu riêng, giữ cổng A

Không gấp. Đích DEMO đề xuất `D:\DU-LIEU-KE-TOAN\postgresql-demo\data`, **tách** cụm thật `postgresql\`, kho file thật `kho-file\`, sao lưu `sao-luu\`. Không di chuyển SQLite thật trong lát này.

1. Lead kiểm kê service/port/version/config/file-path/tablespace đang dùng (vị trí DEMO cũ theo CD-019, không tự đọc `var`). Chờ cửa sổ ngoài cổng A; thiếu lịch/backup/restore đạt → dừng. Đồng bộ đường sao lưu cũ `LUU-TRU` trong kế hoạch/checklist sang CD-019 ở lát tài liệu riêng.
2. Dựng cụm mới/service riêng/port riêng, ACL tài khoản dịch vụ; restore bản DEMO giả + file, thử quyền/lưu/replay tại URL tạm khi cụm cũ vẫn phục vụ. Không copy nóng thư mục data. Chưa đủ đối chiếu → giữ nguyên cổng A.
3. Lead chốt cửa sổ ngắn khi Anh không thử cổng A: dừng nhận ghi/job, đợi hết giao dịch, dump cuối/file cùng mốc → restore **đích mới trống** → đối chiếu. Chuyển cấu hình ứng dụng và service đã thử; cổng web/URL cổng A giữ nguyên, smoke test rồi mở ghi. Cần quyền quản trị Windows cho service thì lead xin đúng bước; không hứa zero downtime khi chưa có replication.
4. Trước ghi mới, lỗi → trả kết nối cụm cũ. Sau có ghi mới, **không trỏ ngược ngay**: dừng ghi, giữ cả hai cụm, chụp phát sinh, đối soát/lead quyết. Cụm/data cũ giữ nguyên, không xóa. CSDL thật chỉ dựng sau XS-5b và lệnh chuyển kho riêng theo CD-016.

**Dòng đề nghị thêm checklist chuyển máy chủ:** `[ ] PostgreSQL bật TLS; client sslmode=verify-full, CA/hostname hợp lệ, pg_hba chỉ hostssl và quyền tối thiểu; kiểm kết nối sai chứng thư bị chặn trước đổi kết nối.`

## 6. Chia lát triển khai — đề xuất, chưa cấp mã migration

Mỗi hàng **≤3 tệp kể cả test**, đường mã dưới `src/kho_tri_thuc/`; tên mới là đề xuất cần handoff. **P★** dùng chung phải khóa lịch; SQL chỉ append `M00xx_*` (hiện thấy tới M0052, lead cấp số kế tiếp), không sửa lịch sử. Không cấp một lát “toàn bộ cột”.

| Thứ tự/lát | Tối đa 3 tệp | Phụ thuộc; điều kiện đạt |
|---|---|---|
| MH-1 khóa/cổng | `ha_tang/ma_hoa_cot.py`; `tests/test_ma_hoa_cot.py` | Anh duyệt nhóm A; DPAPI/khóa thiếu từ chối, canary không vào log. |
| MH-2 schema/API, lặp từng seam | `ha_tang/sql_ma_hoa.py`; P★; `tests/test_ma_hoa_pg.py` | MH-1 + XS-5b; mỗi lượt một nhóm bảng + `M00xx_MA_HOA_*`, kiểm version/HMAC/UNIQUE/âm quyền; không gom mọi module. |
| MH-3 nối từng writer | **Mỗi lượt** 1 caller hiện có; `ha_tang/ma_hoa_cot.py`; 1 test caller | MH-2; chọn một seam từ trace XS-5c (M0, rồi M1, CRM/M4/M2). Lead ghi đích chính xác trước giao; test khớp STK/đọc che/replay, không gộp nhiều caller thành một lát. |
| MH-4 biểu diễn JSON bất biến | **Mỗi module/lượt** 1 SQL module; P★; 1 test PG module | MH-3 + lead chốt hash/seal/raw; append `M00xx_*`, tiền/ngày và nội dung logic không đổi. |
| MH-5 backfill/xoay | `tools/xoay_khoa_cot.py`; `ha_tang/ma_hoa_cot.py`; `tests/test_xoay_khoa_cot.py` | MH-4; lô dở/chạy lại/cạnh tranh/đủ version; chỉ DEMO trước. |
| SL-1 dump mã hóa | `tools/sao_luu_ma_hoa.py`; `tests/test_sao_luu_ma_hoa.py` | Có client PG, public key; fake subprocess kiểm lỗi từng đầu pipe, không plaintext/công bố partial. |
| SL-2 restore | `tools/khoi_phuc_ma_hoa.py`; `tests/test_khoi_phuc_ma_hoa.py` | SL-1 + MH-5; CSDL mới, GPG hỏng/thiếu key/sai tổng phải chặn; lead chạy thử thật một lần bằng DEMO giả. |
| DO-1 bộ đo | `tools/do_bitlocker.py`; `tests/test_do_bitlocker.py` | Cụm/port do lead cấp, SL-2; baseline đủ và ngưỡng lặp lại được. |

SL-1 có thể làm trước MH-2; XS-5b bắt buộc trước bật giải mã module/dựng PG thật chung. Theo kế hoạch chuyển: bản sao giả → mã hóa/restore đạt → Anh duyệt kế hoạch và ra lệnh nguồn thật → M4 trước, kho lõi sau; không dùng test giả thay biên bản đối chiếu nguồn được cấp quyền. Các lát runtime phải so lỗi/skip với nền `NEN-TEST`, XS-5c bắt SQL thực; lát tài liệu không chạy test sản phẩm.

## 7. Cần lead

- Chốt caller/JSON path cho giấy tờ, SĐT/email/địa chỉ, bản sao raw/audit/export/learning; phân loại MST CN/tổ chức và bổ sung CMND/hộ chiếu. Giải quyết dữ liệu bất biến/plaintext cũ, không tuyên bố A hoàn tất chỉ vì có `*_mh`.
- Xác nhận client pg_dump/restore, pgcrypto/GUC/audit thực tế; tài khoản ứng dụng/DPAPI/NTFS và người giữ khóa cứu hộ; chốt unique-domain/HMAC qua các schema legacy. Chưa kiểm hệ thống dịch vụ/khóa/volume.
- Cấp DB/service/port/lịch đo–restore–đổi DEMO tách cổng A; cập nhật đường sao lưu + dòng SSL vào checklist bằng handoff riêng, không sửa ngoài tệp này. Cấp ordinal/khóa P★ và tên caller ≤3 tệp trước giao code.

**Câu cần Anh chốt (tách quyết định kỹ thuật của lead):**

1. Duyệt **10 nhóm A**, 5 B giữ chờ, 3 C giữ rõ? Đề xuất duyệt A, xác nhận thêm ĐKDN tổ chức B trước bật; tiền/lương/ngày giữ rõ theo yêu cầu.
2. Duyệt DPAPI theo tài khoản ứng dụng và khóa sao lưu offline riêng? Đề xuất có; Anh chỉ định người giữ và ổ ngoài, không gửi khóa qua chat.
3. Duyệt lịch 23:00, RPO 24h/RTO 2h và ngưỡng đo ở §4? Đề xuất dùng làm mục tiêu thử; lead báo số đo trước khi Anh quyết BitLocker và cửa sổ chuyển DEMO.

**Tự kiểm lát này:** 1 tệp mới, 18 nhóm duyệt; 0 lần chạy CSDL/benchmark/restore/test sản phẩm; không đọc `var`, bí mật hay dữ liệu thật, không DSN, không commit. Số đo/biên bản khôi phục còn chờ lead, không coi là đã đạt.
