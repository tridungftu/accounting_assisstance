# KẾ HOẠCH LÁT G2 — DỰNG CORE + G3 — NĂM ENGINE

**Ngày:** 30/10/2026 · **Trạng thái:** danh sách lát để lead giao khi đủ điều kiện CD-038 mục 8.  
**Phạm vi:** dựng mới trên CSDL DEMO riêng; nâng/bọc mã hiện có; tích hợp năm engine; cài CRM thử qua giao diện tại cổng D.  
**Lát tài liệu này:** chỉ đọc; chưa sửa tệp, chạy test, migration hoặc dịch vụ.

## 1. Phương án dựng và điều kiện giao

**Đề xuất:** dựng gói Core mới trong repo, dùng lại các lõi đã đúng; giữ đường chạy cũ để đối chiếu. G2 và G3 xen kẽ sau mốc SDK/khung tiến trình tối thiểu. CRM thử G2 dùng tiếp ở G4; M4 vẫn là mẫu đầu tiên của G4.

| Nội dung | Quyết định triển khai |
|---|---|
| Điều kiện mở lập trình | Lead xác nhận chuẩn SDK v1.0 đã hoàn tất và qua Opus review theo CD-038 §8; cập nhật trạng thái mở lại trong `CLAUDE.md`. Không coi kế hoạch này là bằng chứng điều kiện đã đạt. |
| CSDL DEMO | Lead dựng CSDL rỗng riêng, đề xuất `kho_core_demo_g2_<ma>`, cùng PostgreSQL DEMO nhưng tách CSDL/credential/kho tệp khỏi DEMO đang dùng. Không mặc định nâng nguồn “23 migration” lên 67. |
| Vùng dữ liệu | Đề xuất `var/core-demo/<ma>/` cho kho tệp, cấu hình kết nối và bí mật **DEMO**, ngoài git. Script phải kiểm đúng môi trường, từ chối đường dẫn thật. |
| CSDL thật | Không đọc, dựng hoặc migrate `D:\DU-LIEU-KE-TOAN`; chỉ làm ở G5 khi Anh ra lệnh. Không đụng các đường dẫn thật và `.env` bị cấm. |
| Gói mới | `src/kho_tri_thuc/core/`: dịch vụ, SQL Core, Dispatcher, quản lý gói/tiến trình và giao diện; `src/kho_tri_thuc/sdk_core/`: SDK; `src/kho_tri_thuc/engines/`: năm engine; `src/kho_tri_thuc/modules/crm/`: gói CRM thử. |
| Quan hệ mã cũ | Import/bọc lõi còn phù hợp; SQL đích lấy **định nghĩa cuối** rồi điều chỉnh schema, owner, phiên và quyền. Không chạy nguyên chuỗi cũ để dựng Core; không sửa checksum lịch sử hoặc chuyển nguyên `master/kho` vào Core. |
| Phụ thuộc dữ liệu | Core chỉ sở hữu `loi`, `loi_tai_lieu`, `danh_muc`; không phụ thuộc DDL vào module tùy chọn. Resolver đăng ký động; thiếu contract trả `CHO`, không tạo FK chéo module. |

**Mã nền phải dùng lại**, theo KS-A; các dẫn chiếu dưới đây là căn cứ khảo sát, chưa phải nghiệm thu vận hành:

| Nền | Căn cứ trong `src/kho_tri_thuc/` | Cách nâng |
|---|---|---|
| Database Manager | `ha_tang/postgres.py:66–76,217–260` | Giữ kết nối/checksum/transaction; bổ sung quản lý gói, pool và login đúng khối. |
| MTQ/công tắc | `k2/sql_mtq_cong.py:2262–2307`; `k2/sql_module.py:115–193` | Giữ quyết định quyền và công tắc; thay danh tính bằng mã phiên xác minh; tách resolver nghiệp vụ. |
| Hàng việc/bus | `ha_tang/hang_viec.py:21–77`; `ha_tang/bus_su_kien.py:30–74` | Giữ lease, CAS, dedupe, ACK cùng transaction; bổ sung bước/lần thử và giao tiếp liên tiến trình. |
| Kho tệp | `ha_tang/store.py:26–46`; `giao_dien/intake.py:75–128` | Giữ bất biến/hash; thêm metadata, biến thể, quyền nội dung và phục hồi CSDL–file. |
| Tiến trình/engine | `nguon/trich6_host.py:240–365`; `ha_tang/engine.py:35–53,165–191` | Dùng lại bắt tay, readiness, Windows Job và bằng chứng; thay tự chọn cổng bằng sổ cổng Core. |
| Shell/mã hóa/backup | `giao_dien/khung_khai_bao.py:103–167`; `ha_tang/ma_hoa_cot.py:142–204`; `ha_tang/backup.py:40–147` | Bọc vào dịch vụ chung; bổ sung phần thiếu, không tuyên bố đã đủ từ mã hiện hữu. |

**Quy ước đường dẫn trong bảng:** `C` = `src/kho_tri_thuc/core`; `S` = `src/kho_tri_thuc/sdk_core`; `E` = `src/kho_tri_thuc/engines`; `M` = `src/kho_tri_thuc/modules/crm`; `T` = `tests`. Đây là tiền tố chính xác, không phải wildcard. Tất cả đường dẫn mới là **đề xuất whitelist** để lead khóa khi giao; mỗi hàng tối đa ba tệp, **kể cả test**.

**Quy tắc nghiệm thu chung:** Codex tự chạy test thuần/mock theo module; lead chạy PostgreSQL, Windows account/process và trình duyệt ngoài sandbox. Test chưa chạy là `CHUA_KIEM`. Mỗi lát qua review chéo Codex; lead chọn trước khoảng 1/4 lát để kiểm xác suất, Opus giữ điểm cốt lõi role/RLS/phiên/cổng. So `ids_loi` và skip với nền v4 trong `NEN-TEST.md`; C0/C1 mới phải đạt, không được miễn bằng lỗi nền.

## 2. Danh sách lát G2 — Core

Trong cột phụ thuộc, số viết gọn thuộc G2; dấu `+` nghĩa phải đủ tất cả. Thứ tự DDL bắt buộc: role/schema → danh tính/phiên → audit → registry → MTQ/công tắc → tài liệu/tiếp nhận → danh mục → việc/bus/sổ cổng.

| Mã · ai làm | Mục tiêu một câu | Tệp được sửa/tạo, ≤3 | Phụ thuộc | Test chứng minh |
|---|---|---|---|---|
| **G2-00 · Codex** | Chuẩn bị đường dựng Core DEMO rỗng có kiểm môi trường. | `C/__init__.py`; `tools/tao_core_demo.py`; `T/test_g2_00.py` | Điều kiện mở | Từ chối đích thật/sai môi trường; không in credential; lead dựng DEMO riêng. |
| **G2-01 · Claude** | Dựng role/login/schema và provisioning đúng owner. | `C/sql/001_vai.sql`; `T/test_g2_01.py` | 00 | PG16 membership `INHERIT TRUE, SET FALSE, ADMIN FALSE`; runtime không owner/DDL/BYPASSRLS; PUBLIC/default privileges đúng. |
| **G2-02 · Codex** | Nâng danh tính, pháp nhân và quan hệ thành viên thành nguồn chung. | `C/sql/002_danh_tinh.sql`; `C/danh_tinh.py`; `T/test_g2_02.py` | 01 | Core quản tài khoản; pháp nhân là workspace; không tạo bản sao thành viên hoặc nhận actor client. |
| **G2-03 · Claude** | Dựng phiên bí mật và mã ủy nhiệm được CSDL xác minh. | `C/sql/003_phien.sql`; `C/phien.py`; `T/test_g2_03.py` | 02 | Giả GUC, sai login/module/pháp nhân, hết hạn/thu hồi/sai thế hệ đều bị chặn; bảng phiên không lộ mã gốc. |
| **G2-04 · Codex** | Nâng audit và sổ migration theo gói. | `C/sql/004_kiem_toan.sql`; `C/doi_cau_truc.py`; `T/test_g2_04.py` | 03 | Audit bất biến; checksum lệch bị chặn; lỗi SQL rollback cả sổ; nguồn M0013 COMMON/M0017 đúng lineage. |
| **G2-05 · Codex** | Dựng registry module, engine, adapter, hàm và contract. | `C/sql/005_dang_ky.sql`; `C/dang_ky.py`; `T/test_g2_05.py` | 04 | Registry không cần module đã cài; chỉ chức trách cài đặt sửa binding; giữ bản contract còn người dùng. |
| **G2-06 · Claude** | Nâng MTQ và RLS dùng phiên xác minh, resolver động. | `C/sql/006_mtq.sql`; `C/mtq.py`; `T/test_g2_06.py` | 05 | FORCE RLS, USING/WITH CHECK; sai pháp nhân bị chặn; thiếu resolver trả `CHO`; không SQL bảng riêng module trong Core. |
| **G2-07 · Codex** | Hợp nhất validator NGUON và HOP_DONG/DU_AN từ M0065/M0067. | `C/sql/007_pham_vi.sql`; `T/test_g2_07.py` | 06 | Nguồn mơ hồ/sai pháp nhân; quan hệ sai/đổi sau ghim; cấp phạm vi chưa tick vẫn kiểm đủ hai nhánh. |
| **G2-08 · Codex** | Nâng công tắc module theo pháp nhân và người thử. | `C/sql/008_cong_tac.sql`; `C/cong_tac.py`; `T/test_g2_08.py` | 07 | `TAT/THU/VAN_HANH`, CAS/audit; THU không xuất chính thức; TAT giữ lịch sử, không tự bật. |
| **G2-09 · Codex** | Dựng metadata tài liệu, tệp, biến thể và kết quả. | `C/sql/009_tai_lieu.sql`; `C/tai_lieu.py`; `T/test_g2_09.py` | 08 | Quan hệ cùng pháp nhân; revision và trạng thái duyệt riêng; không công bố kết quả thiếu tệp/hash. |
| **G2-10 · Codex** | Bọc kho tệp và bàn giao kết quả có quyền/provenance. | `C/tep.py`; `C/ket_qua.py`; `T/test_g2_10.py` | 09 | Hash bất biến; cùng hash khác quyền; upload vượt 20 MiB bị chặn; crash CSDL–file phục hồi được; nguồn do Core gắn. |
| **G2-11 · Codex** | Nâng tiếp nhận, vùng tạm và hai loại biên nhận chống trùng. | `C/sql/011_tiep_nhan.sql`; `C/tiep_nhan.py`; `T/test_g2_11.py` | 10 | Tiếp nhận chưa có pháp nhân kiểm quyền nguồn; biên nhận module cùng commit, vĩnh viễn; Core 24 giờ tách riêng. |
| **G2-12 · Codex** | Dựng danh mục và cửa ghi V2 từ định nghĩa cuối đã phân chủ. | `C/sql/012_danh_muc.sql`; `C/danh_muc.py`; `T/test_g2_12.py` | 11 | Định danh hợp đồng/hóa đơn, đầu chứng từ, khóa kỳ đúng chủ; không mang dòng cũ hoặc trạng thái riêng module vào Core. |
| **G2-13 · Claude** | Dựng kiểm toàn vẹn liên kết tiền dưới FORCE RLS. | `C/sql/013_lien_ket.sql`; `C/lien_ket.py`; `T/test_g2_13.py` | 12 | Hai ca riêng “đã nối 80 bị che, thêm 30” bị chặn theo chứng từ/nghĩa vụ; cạnh tranh 60+60/100 không cùng commit; kiểm sửa/hủy/giảm sức chứa. |
| **G2-14 · Codex** | Nâng hàng việc bền vững thành việc–bước–lần thử. | `C/sql/014_viec.sql`; `C/viec.py`; `T/test_g2_14.py` | 13 | Hai worker, lease/token cũ, heartbeat/CAS/rollback; restart thành interrupted; `CHUA_RO` không retry mù. |
| **G2-15 · Codex** | Nâng bus với outbox/inbox và ACK cùng transaction. | `C/sql/015_su_kien.sql`; `C/su_kien.py`; `T/test_g2_15.py` | 14 | Giao lại không nhân tác động; rollback nghiệp vụ/ACK cùng nhau; payload chỉ UUID tham chiếu. |
| **G2-16 · Codex** | Dựng sổ cổng, instance, thế hệ sở hữu và số đo bền vững. | `C/sql/016_so_cong.sql`; `C/so_cong.py`; `T/test_g2_16.py` | 15 | Unique chủ/cổng; CAS chống hai instance; khóa lỗi khởi động còn sau restart; không có login engine. |
| **G2-17 · Codex** | Đưa schema kỹ thuật/manifest đã chốt vào bộ phân giải offline. | `C/contract/ky_thuat.json`; `C/contract/manifest.json`; `T/test_g2_17.py` | 16 | Chín contract kỹ thuật, meta-schema 2020-12, `$id/$ref` offline, format/ví dụ/ca âm; không thêm schema còn chờ. |
| **G2-18 · Codex** | Dựng HTTP boundary và Dispatcher `/api/v1/` theo registry. | `C/http.py`; `C/dispatcher.py`; `T/test_g2_18.py` | 17 | Phiên/Origin/CSRF; envelope/lỗi; JSON 1 MiB; 202 sau commit; CAS/409; phân trang; response sai contract thành 502. |
| **G2-19 · Claude** | Dựng SDK context và transaction đúng login/ủy nhiệm. | `S/ngu_canh.py`; `S/giao_dich.py`; `T/test_g2_19.py` | 18 | Thẻ ≤30 giây; chữ ký/instance/hash; nonce đồng thời chỉ một vào handler; pool không rò context; bí mật không qua repr/log. |
| **G2-20 · Codex** | Cung cấp SDK tối thiểu cho module và engine. | `S/dich_vu.py`; `S/engine.py`; `T/test_g2_20.py` | 19 | Tệp/kết quả/việc/audit/engine hoạt động; biên nhận/bus dùng cùng `tx`, không tự commit; engine không nhận SQL/credential DB. |
| **G2-21 · Claude** | Dựng khung tiến trình và chuyển giao/thu hồi socket. | `C/tien_trinh.py`; `S/bootstrap.py`; `T/test_g2_21.py` | 20; thử thật cần 33 | Dùng lại host #6; `share/fromshare`, một bên accept; readiness PID+lần tạo+nonce+version; cổng bị chiếm không dò cổng/diệt tiến trình lạ. |
| **G2-22 · Codex** | Hoàn thiện drain, đánh thức và số đo/chế độ chạy. | `C/vong_doi.py`; `C/so_do.py`; `T/test_g2_22.py` | 21 | Rảnh 300 giây; drain quá hạn giữ trạng thái; queue/inbox đánh thức một instance; TAT không bật; 3 lỗi khóa; Admin CAS áp dụng đề xuất. |
| **G2-23 · Codex** | Bọc két DEMO và cổng mã hóa hiện có. | `C/bi_mat.py`; `C/ma_hoa.py`; `T/test_g2_23.py` | 19 + 33; chốt adapter/path nhóm A | DPAPI CurrentUser Core; chỉ stdin/handle; khóa không qua SQL; canary/log, HMAC, quyền xem đủ/audit, đổi khóa/restore. |
| **G2-24 · Codex** | Dựng kiểm gói và staging của Module Manager. | `C/goi.py`; `C/cai_dat.py`; `T/test_g2_24.py` | 17 + 20 | Không chạy mã khi đọc manifest; chặn traversal/symlink; kiểm tương thích, dependency, route trùng và `contract/`. |
| **G2-25 · Claude** | Dựng áp gói đúng owner và kích hoạt nhất quán. | `C/sql/025_ap_goi.sql`; `C/kich_hoat.py`; `T/test_g2_25.py` | 21 + 24 | Login cài đặt chỉ EXECUTE gói đã kiểm; không SQL tùy ý/SET ROLE; lỗi migration/filesystem không kích hoạt một phần; nâng cấp giữ việc/bản cũ. |
| **G2-26 · Codex** | Đóng bộ kiểm tĩnh KT05/06/07/14/15 dùng chung. | `C/kiem_tra_goi.py`; `tools/kiem_core.py`; `T/test_g2_26.py` | 25 | Contract trùng nghĩa, thiếu duyệt, schema/route sai bị đỏ; xuất DAT/KHONG_DAT/CHUA_KIEM/KHONG_AP_DUNG đúng mức C0/C1/C2. |
| **G2-27 · Codex** | Đóng bộ kiểm quyền và tiến trình KT01–04/08–13/16. | `C/kiem_tra_quyen.py`; `C/kiem_tra_tien_trinh.py`; `T/test_g2_27.py` | 22 + 23 + 26 | Catalog→quyền hiệu lực→phụ thuộc→trace; GRANT tay làm mất kích hoạt; kiểm lúc cài/kích hoạt/Core startup; ca âm từ chính tài khoản con. |
| **G2-28 · Codex** | Dựng Workflow Runner trên hàng việc hiện có. | `C/sql/028_quy_trinh.sql`; `C/quy_trinh.py`; `T/test_g2_28.py` | 20 + 22 | Dependency/nhánh/mapping/chờ duyệt; ghim phiên bản; mất lease không ghi kết quả; SDK không để stub khi công bố dịch vụ. |
| **G2-29 · Codex** | Cưỡng chế retention bằng metadata và phụ thuộc. | `C/luu_giu.py`; `T/test_g2_29.py` | 11 + 16 + 28 | Đúng hạn 24 giờ/7/30/90 ngày và 1 năm; giữ dữ liệu đang dùng/bằng chứng; biên nhận module không hết hạn; thiếu policy từ chối nhận. |
| **G2-30 · Codex** | Bọc backup/restore và xuất một pháp nhân trên DEMO. | `C/sao_luu.py`; `C/xuat_phap_nhan.py`; `T/test_g2_30.py` | 23 + 27 + 29 | Mốc CSDL–file nhất quán; phục hồi vào đích riêng; đối chiếu hash/dòng/đơn vị; không xuất bí mật hoặc dữ liệu pháp nhân khác. |
| **G2-31a · Codex** | Dựng SDK JS và Shell theo khai báo đã lọc quyền. | `S/trinh_duyet.js`; `C/ui/index.html`; `T/g2_31a.cjs` | 18 + 20 | Chỉ gọi Core; polling/Retry-After; giữ khóa/nháp; đổi context bỏ response cũ; lưới hai cấp, badge đúng quyền. |
| **G2-31b · Codex** | Dựng giao diện quản trị và vận hành Core đủ thử cổng D. | `C/ui/quan_tri.js`; `C/ui/van_hanh.js`; `T/g2_31b.cjs` | 25 + 27 + 31a | Xem trước quyền/cài/tắt; sổ contract, engine/cổng, MTQ, tài liệu/kết quả, việc/audit/số đo; không lộ URL nội bộ/bí mật. |
| **G2-32 · Codex** | Ghép entry point Core DEMO và dịch vụ đã hoàn tất. | `C/ung_dung.py`; `tools/mo_core_demo.ps1`; `T/test_g2_32.py` | 28 + 30 + 31b | Health/ready đúng nền; route theo OpenAPI; chưa đạt KT không phục vụ; đủ 12 dịch vụ SDK trước cổng D. |
| **G2-33 · Codex** | Viết script tài khoản Windows/ACL chạy lại được. | `tools/tao_tai_khoan_core.ps1`; `tools/CAI-TAI-KHOAN-CORE.cmd`; `T/test_g2_33.py` | 00; lead chạy trước thử tiến trình thật | `ktt_core`, `ktt_module`; tài khoản riêng cho Mask/AI Cloud/tải hóa đơn/ABBYY; chạy lại không nới quyền; con không đọc két/DPAPI/Core memory/handle. |

**Hai lưu ý giao lát:** G2-33 có thể làm sớm, dù được liệt kê cuối nhóm hạ tầng; mọi thử tiến trình thật phải chờ nó. G2-23 chỉ triển khai sau khi lead chốt adapter mã hóa và JSON path nhóm A theo chuẩn CSDL §3.11; không tự chọn thuật toán mới.

G2-29 chỉ dựng cơ chế lựa chọn/kiểm retention và kiểm bằng DEMO giả lập; không dọn tài nguyên hiện hữu. Việc dọn/xóa phải tuân quyền riêng và ràng buộc không xóa của repo.

## 3. Danh sách lát G3 — năm engine

**Mốc N = G2-17 + G2-20 + G2-21.** Mọi lát code engine dưới đây phụ thuộc N; tích hợp tiến trình thật còn cần G2-22/23/27/33. Các test Codex dùng provider, transport, ABBYY, Mask và portal giả; lead giữ việc thử host thực đã được phép.

Nguồn dùng lại đúng `GIAO-ENGINE-1/2`: ABBYY/Hot Folder từ `D:\GPT\OCR`; Mask file v2; phần trích xuất review xây dựng; bộ tải hóa đơn; cổng AI trong repo. Không sửa nguồn ngoài repo. Phần bắt buộc chép ghi nguồn, phiên bản, SHA256 trong mã/báo cáo lát; không tạo manifest hash hay bản sao repo riêng.

**Codex làm tất cả lát G3**; Claude chỉ review/giữ cổng an ninh liên quan.

| Mã | Mục tiêu một câu | Tệp đích, ≤3 | Phụ thuộc thêm N | Test chứng minh |
|---|---|---|---|---|
| **OCR-1** | Khai báo capability OCR đã có contract. | `E/e_ocr/engine.json`; `T/test_g3_ocr_1.py` | — | Manifest/schema; không quảng bá backend hoặc năng lực chưa kiểm. |
| **OCR-2** | Bọc ABBYY→DOCX thành văn bản có vị trí/nguồn. | `E/e_ocr/van_ban.py`; `T/test_g3_ocr_2.py` | OCR-1 | Dùng `HotFolderClient.convert`, `extract_docx`; không import `app.py`, hiệu đính hay OCR ảnh nhúng khác. |
| **OCR-3** | Bọc bảng DOCX bảo toàn cấu trúc. | `E/e_ocr/bang.py`; `T/test_g3_ocr_3.py` | OCR-2 | `word_layout(embedded_pages=[])`; ô rỗng/gộp, hàng/cột/vị trí; không suy bảng từ chuỗi văn bản. |
| **OCR-4a** | Ghép khung tiến trình OCR bằng backend giả. | `E/e_ocr/chay.py`; `T/test_g3_ocr_4a.py` | OCR-1 | Cổng/readiness/Job/drain; không gọi ABBYY. |
| **OCR-4b** | Ghép ABBYY với tài khoản và phiên Windows riêng. | `E/e_ocr/abbyy.py`; `T/test_g3_ocr_4b.py` | OCR-4a; G2-33 | Ngoại lệ có màn hình đã duyệt; đúng tài khoản/ACL; không tự đọc cấu hình/bí mật nguồn. |
| **OCR-5a** | Nối một chủ Hot Folder và một sổ hạn mức. | `E/e_ocr/ban_giao.py`; `T/test_g3_ocr_5a.py` | OCR-2/3/4a | Dùng lại `ha_tang/cong_ocr.py`; tương tranh đường cũ/mới; crash sau wait không gửi lại/hoàn hạn mức mù. |
| **OCR-5b** | Nghiệm thu bàn giao OCR và cách ly thực. | `T/test_g3_ocr_5b.py` | OCR-4b/5a; G2-27 | Core nhận/hash/provenance trước dừng; bí mật DEMO không lộ; quyền tải kết quả đúng. |
| **MASK-1** | Khai báo phần đã có và dự thảo schema còn thiếu để duyệt. | `E/e_mask/engine.json`; `E/e_mask/contract/du_thao.json`; `T/test_g3_mask_1.py` | — | Schema nháp không được kích hoạt; ánh xạ đúng MASK-1/2, không lấy mapping nội bộ. |
| **MASK-2** | Bọc HTTP che/mở văn bản của Mask v2. | `E/e_mask/van_ban.py`; `T/test_g3_mask_2.py` | MASK-1; **schema liên quan được Anh duyệt** | Danh mục khóa/còn sót/lượt hết hạn/mở che lỗi bị chặn; không che tiền/ngày. |
| **MASK-3** | Bọc phát hiện độc lập khi có contract và API nguồn. | `E/e_mask/phat_hien.py`; `T/test_g3_mask_3.py` | **CHỜ schema + bằng chứng nguồn/API** | Không dùng thuật toán/endpoint tự viết để lấp thiếu. |
| **MASK-4** | Bọc che tài liệu khi có contract và API độc lập. | `E/e_mask/tai_lieu.py`; `T/test_g3_mask_4.py` | **CHỜ schema + bằng chứng nguồn/API** | Không dùng UI session/revision làm API độc lập hoặc suy từ che văn bản. |
| **MASK-5** | Ghép khung chạy và tài khoản riêng của Mask. | `E/e_mask/chay.py`; `T/test_g3_mask_5.py` | MASK-1; G2-33 | `--port` đúng cổng; không nới Host/Origin/proxy UI; phát hiện thiếu seam cấp khóa trước chạy nguồn. |
| **MASK-6** | Nối vòng đời danh mục và bàn giao với Core. | `E/e_mask/vong_doi.py`; `T/test_g3_mask_6.py` | MASK-5; thực cần MASK-2 | Anh mở khóa tại máy chủ; danh mục đang mở không tự đóng; lượt đang dùng/kết quả chưa nhận không drain. |
| **AI-1a** | Khai báo engine và tái dùng DTO cổng AI. | `E/e_hoi_ai/engine.json`; `E/e_hoi_ai/dto.py`; `T/test_g3_ai_1a.py` | — | Giữ `YeuCauAI/TruongAI/KetQuaAI`; không DB hoặc client AI mới. |
| **AI-1b** | Đóng schema đầu vào và cờ chỉ Local sau duyệt. | `E/e_hoi_ai/contract/dau_vao.schema.json`; `E/e_hoi_ai/contract/vi_du.json`; `T/test_g3_ai_1b.py` | **CHỜ Anh duyệt schema/cờ** | Không tự chốt tên trường hoặc coi CD-038 đã duyệt điểm này. |
| **AI-2** | Bọc `CongAI.goi` và chế độ chỉ Local theo request. | `E/e_hoi_ai/hoi.py`; `T/test_g3_ai_2.py` | AI-1a/1b | Chỉ Local tạo 0 Cloud calls; không đổi trạng thái instance chung; không fallback env/tệp. |
| **AI-3** | Nối che/mở qua `e_mask` trước nhánh Cloud. | `E/e_hoi_ai/mask.py`; `T/test_g3_ai_3.py` | AI-2 + MASK-2 | Che dữ liệu/chỉ dẫn; còn sót hoặc mở che/dẫn chứng sai không trả thành công. |
| **AI-4a** | Ghép tiến trình AI bằng provider/Mask giả. | `E/e_hoi_ai/chay.py`; `T/test_g3_ai_4a.py` | AI-1a | Readiness/cổng/Job/drain; Local không mặc định luôn chạy. |
| **AI-4b** | Nhận bí mật RAM dưới tài khoản AI Cloud riêng. | `E/e_hoi_ai/bi_mat.py`; `T/test_g3_ai_4b.py` | AI-4a; G2-23/33 | Dùng seam `moi_truong/mask`; không env/args/đĩa; không đọc két hoặc mang `BoGhiPostgres` vào engine. |
| **AI-5a** | Bọc nhật ký/thống kê qua Core để sống qua restart. | `E/e_hoi_ai/nhat_ky.py`; `T/test_g3_ai_5a.py` | AI-1a | Metadata được Core lưu; thống kê/kiểm xác suất không mất khi tự đóng; không chỉ dùng bộ nhớ. |
| **AI-5b** | Nghiệm thu luồng Cloud/vận hành bằng cổng giả. | `T/test_g3_ai_5b.py` | AI-3/4b/5a; G2-27 | Giữ Local trước, đo chính xác/kiểm xác suất theo TL48; lỗi Mask không vượt cổng. |
| **AI-6** | Kiểm trích xuất dùng đúng mẫu cổng AI chung. | `T/test_g3_ai_6.py` | AI-2 + TRICH-1b | Không đường AI riêng; phối hợp phép đo TRICH-4b; mock không thay số đo thực. |
| **TRICH-1a** | Bọc đọc DOCX và ánh xạ 37 tham số bằng AI giả. | `E/e_trich_xuat/docx.py`; `E/e_trich_xuat/tham_so.py`; `T/test_g3_trich_1a.py` | — | Chặn `_word` thực; XML Python xử lý Track Changes; không COM/OCR/Cloud; PDF qua e_ocr. |
| **TRICH-4a** | Chuẩn bị phép đo và lấy số trước hợp lệ. | `E/e_trich_xuat/do_chinh_xac.py`; `T/test_g3_trich_4a.py` | TRICH-1a; đường chạy gốc được phép | `DAP_AN_*.tsv`, đủ 37 tham số; ghi nguồn/SHA/model/cấu hình/cách chấm; thiếu phép đo ghi chưa đo. |
| **TRICH-1b** | Chép phần trích có sửa câu hỏi sang mẫu cổng chung. | `E/e_trich_xuat/quy_trinh.py`; `E/e_trich_xuat/ai_chung.py`; `T/test_g3_trich_1b.py` | TRICH-4a; AI-2 khi tích hợp | CD-038 1C; không sửa review gốc; nguồn/SHA; ghi ca test đổi/lý do; `cloud=None`, không client AI trực tiếp. |
| **TRICH-2a** | Bọc trích bảng khi nguồn và contract được xác nhận. | `E/e_trich_xuat/bang.py`; `T/test_g3_trich_2a.py` | **CHỜ Anh + nguồn/test bảo toàn bảng** | Chưa công bố `trich.bang@1`; không viết thuật toán bù thiếu. |
| **TRICH-2b** | Đưa danh mục E1-MUA theo loại vào bản chép được phép. | `E/e_trich_xuat/danh_muc.py`; `E/e_trich_xuat/danh_muc_theo_loai.xlsx`; `T/test_g3_trich_2b.py` | **CHỜ Anh cho phép bản chép có vá/danh mục** | Nguồn/hash/vị trí XLSX đúng; thiếu/sai loại không fallback XD; không sửa X. |
| **TRICH-3a** | Đóng manifest và khung tiến trình trích xuất giả lập. | `E/e_trich_xuat/engine.json`; `E/e_trich_xuat/chay.py`; `T/test_g3_trich_3a.py` | TRICH-1a | Cổng/readiness/bàn giao; không ready capability chưa đạt. |
| **TRICH-3b** | Ghép trích xuất qua Core và cổng AI chung. | `E/e_trich_xuat/tich_hop.py`; `T/test_g3_trich_3b.py` | TRICH-1b/3a + AI-6; PDF cần OCR-5b | Nguồn/danh mục/hash/dẫn chứng đủ; không OCR riêng; nghiệm thu chờ TRICH-4b. |
| **TRICH-4b** | Đo sau và đối chiếu với bản gốc. | `E/e_trich_xuat/do_chinh_xac.py`; `T/test_g3_trich_4b.py` | TRICH-4a + TRICH-3b | Cùng bộ/điều kiện/cách chấm; tổng và từng tham số có số liệu; sau thấp hơn gốc phải dừng/báo Anh. |
| **HD-1** | Bọc parser XML/ZIP hiện có sang contract hóa đơn. | `E/e_hoa_don/doc.py`; `T/test_g3_hd_1.py` | — | Decimal/ID/số 0 đầu/hash/context; XML hỏng/profile lạ/ZIP CRC/trùng entry/partial; giữ test parser gốc. |
| **HD-2a** | Bọc tải hóa đơn với portal giả. | `E/e_hoa_don/tai.py`; `T/test_g3_hd_2a.py` | HD-1 | Chờ đăng nhập giả, PARTIAL/coverage, bàn giao/dedupe; kỳ trọn tháng, tháng nhuận/đổi năm; không Chromium/thuế thật. |
| **HD-2b** | Bọc `build.js` xuất bảng kê. | `E/e_hoa_don/bang_ke.cjs`; `T/g3_hd_2b.cjs` | HD-1 | Test nguồn build/parse/PDF bằng DEMO; không dùng parser hiển thị thay parser strict. |
| **HD-3a** | Ghép khung engine và Node giả vào cây Job. | `E/e_hoa_don/engine.json`; `E/e_hoa_don/chay.py`; `T/test_g3_hd_3a.py` | HD-2a | Node/Chromium thuộc Job; cổng bị chiếm lỗi, không dò; stub không chứng minh protocol nguồn thật. |
| **HD-2c** | Bọc job/portal cho phiên Windows có màn hình. | `E/e_hoa_don/portal.cjs`; `T/g3_hd_2c.cjs` | HD-2a/2b/3a; G2-23/33 | Mật khẩu stdin/handle→object RAM; profile từng pháp nhân/phiên; không chạy server nguồn/.env; không gọi thuế thật. |
| **HD-3b** | Kiểm tài khoản riêng, profile và bàn giao trong môi trường DEMO. | `E/e_hoa_don/phien.py`; `T/test_g3_hd_3b.py` | HD-2c; G2-27 | Xong/lỗi/hủy/crash không dùng lại profile; dọn thất bại chặn phiên mới; thiếu seam coverage/profile phải báo, không tự sửa nguồn. |

Các tệp `.xlsx` trong lát chờ là tài nguyên cần được xác nhận cụ thể trước giao; chưa được tự tạo danh mục nghiệp vụ mới. Báo cáo ZIP thiếu schema giữ chờ. Các thao tác kết thúc vòng đời profile chỉ triển khai trong phạm vi được lead xác nhận theo CD-038 và ràng buộc repo.

## 4. CRM thử G2 và cổng D

Phạm vi đã được CD-038 duyệt: **Dự án đang bán; Báo giá/lịch giá bán/VAT cọc/in DOCX; tải mẫu G1 và trích/OCR; công bố/sự kiện; cài/tắt qua giao diện**. Không đưa soạn hợp đồng, ký kết hoặc thu tiền vào G2.

| Mã · ai làm | Mục tiêu một câu | Tệp đích, ≤3 | Phụ thuộc | Test chứng minh |
|---|---|---|---|---|
| **G2-CR1 · Codex** | Đóng contract dự án đang bán theo bản đã duyệt. | `M/contract/du_an_dang_ban.schema.json`; `M/contract/du_an_dang_ban.demo.json`; `T/test_g2_cr1.py` | G2-17 | Trường/nguồn/đơn vị/ví dụ và bằng chứng duyệt; không thêm nghiệp vụ. |
| **G2-CR2 · Codex** | Đóng contract báo giá theo CD-038 1A/2B. | `M/contract/bao_gia.schema.json`; `M/contract/bao_gia.demo.json`; `T/test_g2_cr2.py` | G2-CR1 | Giá bán chia đủ 100%; phí riêng; cọc cuối/nhiều cọc được biểu diễn đúng. |
| **G2-CR3 · Codex** | Đóng contract sự kiện mốc dự án. | `M/contract/moc_da_xay_ra.schema.json`; `M/contract/moc_da_xay_ra.demo.json`; `T/test_g2_cr3.py` | G2-CR1 | Payload tham chiếu; phiên bản và chủ/bên đọc đúng sổ contract. |
| **G2-CR4 · Codex** | Nâng dữ liệu dự án/mốc và công bố CRM tối thiểu. | `M/sql/001_du_an.sql`; `M/du_an.py`; `T/test_g2_cr4.py` | G2-25/27 + CR1/3 | Dùng lại `crm_du_an_ban`/SQL hiện có; V1/V2/V3/V4, owner view/resolver đúng; CAS/dedupe; nghiệp vụ+bus cùng commit. |
| **G2-CR5 · Codex** | Nâng lõi tính lịch giá bán và lưu báo giá thử. | `M/sql/002_bao_gia.sql`; `M/bao_gia.py`; `T/test_g2_cr5.py` | CR2/4 | Dùng lại lõi `k2/crm_giao_ket.py`; VAT cọc dồn sau rồi trước; cọc cuối/liền/xen giữa/toàn cọc; tổng tiền/VAT/% và làm tròn đúng. |
| **G2-CR6 · Codex** | Bọc in DOCX thành việc lâu, lưu/tải qua Core. | `M/xuat_docx.py`; `M/api.py`; `T/test_g2_cr6.py` | CR5; G2-20/28 | Tái dùng xuất hiện có; 202 sau commit; mất mạng/replay không nhân việc; tệp có quyền và provenance. |
| **G2-CR7 · Codex** | Đóng gói CRM thành tiến trình độc lập cài được. | `M/module.json`; `M/chay.py`; `T/test_g2_cr7.py` | CR6; G2-25/27 | Contract/migration/asset/version khớp; login riêng; readiness không tự migrate; giữ/nhả đúng cổng. |
| **G2-CR8 · Codex** | Nối màn CRM thử vào Shell/SDK JS. | `M/ui/index.html`; `M/ui/crm.js`; `T/g2_cr8.cjs` | CR7; G2-31a | Bọc luồng giao diện hiện có; xem/sửa đúng MTQ; giữ nháp/CAS; tạo dự án/báo giá và tải DOCX. |
| **G2-CR9 · Codex** | Nối tải mẫu G1 và gọi trích/OCR qua Core. | `M/tai_lieu.py`; `M/ui/crm.js`; `T/test_g2_cr9.py` | CR8; OCR-5b + TRICH-3b/4b | Upload ≤20 MiB; việc lâu/kết quả có nguồn; không gọi cổng engine trực tiếp hoặc tự coi kết quả là đã duyệt. |
| **G2-CR10 · Codex** | Đóng kịch bản tự động phục vụ cổng D. | `T/test_g2_cong_d.py`; `T/g2_cong_d.cjs` | CR9; G2-32; KT áp dụng đạt | Chạy đủ luồng cài→dùng→tắt→khởi động lại; quyền âm/replay/sự kiện/cổng; lead tự thử trình duyệt. |

**Checklist cổng D — lead chạy và báo Anh:**

| Bước qua giao diện | Bằng chứng phải có |
|---|---|
| Admin tải gói CRM, xem trước quyền và bấm cài | Manifest/contract hợp lệ; migration đúng owner; sổ contract/quyền/cổng đăng ký nhất quán; lỗi cài không hoạt động một phần. |
| Đăng nhập hai người, hai pháp nhân DEMO | MTQ xem/sửa khác nhau; giả actor/pháp nhân không vượt quyền; tải tệp ngoài phạm vi bị chặn. |
| Tạo dự án, sửa cạnh tranh, công bố và phát mốc | CAS/409, chống trùng; đọc công bố bền vững khi tiến trình nguồn ngủ; bus giao lại không nhân tác động. |
| Lập báo giá và in DOCX | Đủ ca VAT cọc CD-038; 202/poll; kho tệp Core; tải theo quyền; retry sau timeout/restart không tạo bản thứ hai. |
| Tải mẫu G1, gọi trích/OCR | Capability thực đạt; kết quả có nguồn/hash; phép đo trích xuất không giảm; không biến “xử lý xong” thành “đã duyệt”. |
| Để CRM tự ngủ rồi có việc/sự kiện; sau đó Admin tắt CRM | Tự ngủ giữ cổng; việc đánh thức đúng một instance; `TAT` giữ hàng chờ và không tự bật; dữ liệu/lịch sử/biên nhận còn nguyên. |

**Chỉ thông qua D khi các C0/C1 áp dụng đều DAT, không tăng lỗi regression và lead đã thử giao diện.** Stub/mocks chỉ chứng minh từng lát; không thay nghiệm thu tích hợp. Engine còn chờ schema/phép đo làm phần tương ứng của D chưa đạt, không được bỏ khỏi checklist để tuyên bố xong.

## 5. Bảng giao song song và khóa tuần tự

Tối đa **bốn Codex đang làm**, tính cả reviewer; hàng dưới là các nhóm công việc có thể lấy khi **đủ phụ thuộc**, không phải cho phép chạy cả nhóm ngay. Claude/lead giữ các lát rủi ro cao và gate máy.

| Đợt | Codex 1 | Codex 2 | Codex 3 | Codex 4 / review | Claude/lead |
|---|---|---|---|---|---|
| A — nền CSDL | 00→02→04→05 | 33 | Review chỉ đọc lát đã xong | Rà nguồn/test lát kế tiếp | 01→03→06; dựng PG DEMO |
| B — dịch vụ Core | 07→08→09→10→11 | 17 khi đủ 16 | CR1→CR2→CR3 khi đủ 17 | Review; 24 khi đủ 20 | 13; chốt mã hóa/path; kiểm 12–16 |
| C — mở mốc N | 12→14→15→16 theo phụ thuộc | 18→20 | 24→26 khi đủ 25 | CR4→CR5 khi đủ điều kiện | 19→21; 25 |
| D — G2/G3 xen kẽ | OCR-1→2→3→4a→5a | MASK-1→5; AI-1a/4a/5a | HD-1→2a→2b→3a | G2-22→23→27; luân phiên review | Kiểm socket/Windows/PG; quyết định schema thiếu |
| E — tích hợp | OCR-4b→5b; MASK-2→6 | AI-1b→2→3→4b→5b khi mở chặn | TRICH-1a→4a→1b→3a; HD-2c→3b | G2-28→29→30→31a→31b→32 | Review điểm cốt lõi; cấp môi trường thực |
| F — cổng D | AI-6/TRICH-3b→4b | CR6→CR7→CR8→CR9 | CR10 | Review cuối, thay slot trống | Chạy tích hợp tuần tự; thử trình duyệt; báo Anh |

**Khóa bắt buộc:**

- Mỗi lát một worktree/nhánh do lead tạo từ `hop-nhat-20261023`, đã chứa phụ thuộc được gộp; commit tiếng Việt `[MÃ LÁT] mô tả`.
- Áp SQL Core đúng thứ tự mục 2; chỉ **một lượt PostgreSQL DEMO** do lead chạy tại một thời điểm.
- `C/dispatcher.py`, `C/dang_ky.py`, `C/ung_dung.py`, các bundle schema dùng chung: một lát giữ tệp tại một thời điểm; đăng ký khóa trong `TRANG-THAI.md`.
- `E/e_trich_xuat/do_chinh_xac.py`: TRICH-4a hoàn tất trước TRICH-4b; `M/ui/crm.js`: CR8 hoàn tất trước CR9.
- Nguồn cũ dùng chung chỉ đọc trong các lát adapter. Nếu phải sửa `giao_dien/server.py`, `ha_tang/pg_migrations.py`, `crm_g.py` hoặc asset cũ, dừng và xin lead sửa whitelist/chia lát; không tự mở rộng.
- Codex không khởi động/dừng PG hoặc server DEMO. Handoff ngoài whitelist hoặc cần hơn ba tệp phải trả lead chia lại; cùng lỗi sửa hai lần chưa xong thì dừng báo.

## 6. Điểm báo Anh và rủi ro chính

| Thời điểm | Lead báo Anh |
|---|---|
| Chuẩn SDK xong + Opus review | Ghi điều kiện CD-038 §8 đã đủ, thời điểm mở G2/G3; không xin lại quyết định đã duyệt. |
| Trước setup Windows cần quyền quản trị | Đưa script/preview tài khoản–ACL cụ thể để Anh đồng ý quyền quản trị; không yêu cầu Anh gõ lệnh. |
| Mốc N được kiểm thật | Báo giữ/chuyển giao/thu hồi cổng Python, khởi động đồng thời, readiness và cách ly tài khoản; nêu rõ nhánh engine cũ có khoảng hở. |
| Còn thiếu contract hoặc seam nguồn | Trình schema Mask/AI còn chờ; trích bảng, E1-MUA, báo cáo ZIP thiếu schema; phạm vi sửa nguồn nếu bắt buộc. Không hỏi lại CD-038 1C/2A/3A. |
| Trích xuất giảm chính xác hoặc chưa có số trước hợp lệ | Dừng nghiệm thu; gửi số tổng/từng tham số và điều kiện đo, không thay bằng test xanh. |
| Cổng D sẵn sàng | Gửi bản DEMO mở được, gói/phiên bản, checklist mục 4, test và giới hạn; báo kết quả cài CRM qua giao diện theo CD-038. |
| Thuế thật hoặc G5 | Chỉ thực hiện khi có lệnh riêng của Anh; không suy quyền từ việc mở lập trình hoặc cổng D. |

**Rủi ro chính — tối đa năm dòng:**

1. Tách schema nhưng mất guard cuối hoặc sai lineage M0013/M0017/M0065–67 có thể làm test đơn vị xanh mà sai toàn vẹn.
2. Chuyển socket khác tài khoản, Job/handle/DPAPI cần chứng minh trên Windows thực; mock không đủ mở kích hoạt.
3. Schema Mask/AI và capability chưa có bằng chứng nguồn có thể chặn tích hợp; không tự bổ sung contract/thuật toán.
4. Đổi câu hỏi trích xuất có thể giảm chất lượng; thiếu số đo trước/sau 37 tham số thì chưa đủ nghiệm thu.
5. CSDL–filesystem–nguồn ngoài không có một transaction chung; phải giữ staging, biên nhận, bàn giao và trạng thái chưa rõ, không retry mù.
## Ghi chú lead khi giao (31/10)
- **G2-13b (Codex, nhỏ):**
  - tra resolver phải ra đúng một dòng `dang_dung`, nếu không → `CHO` / `LIEN_KET_RESOLVER`;
  - thêm `LIEN_KET_CAN_READ_COMMITTED` vào bảng mã lỗi `danh_muc.py`.
  - Nguồn: `RV-G2-13-OPUS-v2.md`.
- **G2-25 phải thêm:**
  - cấp wrapper kiểm cố định module (ABI 013) với REVOKE EXECUTE PUBLIC / login;
  - `vai_kiem_toan_ven_mod_<ma>` không có thành viên;
  - cấp `USAGE loi` + EXECUTE `mtq_phien_rls()` cho role kiểm module.
  - Test kiểm cả ba.
- **Rủi ro chấp nhận (G2-13):** hàm kiểm boolean theo ngưỡng dò được tổng bằng chia đôi, chỉ với role kiểm của chính module.
