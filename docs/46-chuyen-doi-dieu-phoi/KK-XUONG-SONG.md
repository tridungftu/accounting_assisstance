# KK-XS · Kiểm kê và chia lát Xương sống

26/10/2026 · `lat/kk-xs`, HEAD `3393a60` · **Chỉ khảo sát tĩnh; chưa triển khai/chưa nghiệm thu.**

**Kết luận:** tận dụng G5 cho mẫu hàng việc bền, khung CRM cho khai báo, các cổng OCR/AI và adapter hiện có cho engine; bổ sung bus và hợp đồng chung. Không thay đồng loạt luồng cũ. Căn cứ: TL 53 §1–6 (`D:/Claude/Phan mem ho tro ke toan/53-kien-truc-xuong-song-engine-module.md`); `CHI-DAO-TU-ANH.md:191` (CD-016), `:202` (CD-017). CD-017 chỉ thay CD-016 mục 5; giữ một PG chung, chuyển kho thật cần lệnh riêng, go-live M0/M2/M3/M4/M9 cùng đợt qua cổng B.

## 1. Hiện trạng XS-1…XS-4

Đường dẫn mã dưới đây tính từ `src/kho_tri_thuc/`; `T/` = `tests/` từ gốc repo. “Chưa thấy” giới hạn trong mã được khảo sát, không khẳng định trạng thái hệ thống đang vận hành.

| XS | Đã có, bằng chứng tệp:dòng | Dùng lại đến đâu; còn thiếu |
|---|---|---|
| **XS-1 · Bus PG** | `ha_tang/pg_migrations.py:413`: `nhat_ky.su_kien`, dữ liệu trước/sau, pháp nhân; `:464`: trigger chỉ thêm. `ha_tang/ket_noi.py:570`: helper ghi nhật ký. `k2/sql_crm_doi_chieu.py:378`: sự kiện G5; `m4/sql_request_nhap.py:176`: sự kiện Request; `ha_tang/pg_migrations.py:2196`: sự kiện vay, unique khóa nguồn + revision. | Dùng lại giao dịch PG, danh tính/pháp nhân, audit và cách khóa nguồn. **Nhật ký không phải bus**: chưa thấy subscription/inbox, ACK từng bên nhận, retry giao nhận và khóa idempotency xuyên module. Cần outbox cùng giao dịch nghiệp vụ, unique `(pháp nhân, module phát, event_key)`, payload version/hash; cùng khóa khác nội dung phải từ chối. Inbox unique `(pháp nhân, bên nhận, event_id)`, ghi kết quả/ACK cùng giao dịch. Không sửa/xóa nhật ký để đánh dấu đã nhận. |
| **XS-2 · Việc nền** | `k2/sql_crm_doi_chieu.py:183,484,511,637,688`: việc G5, `SKIP LOCKED`, nhận lease, CAS công bố/kết thúc, thử lại; `k2/crm_doi_chieu.py:371`: worker đánh thức/poll, phục hồi sau hết lease. `m2/tai_hoa_don/dieu_phoi.py:255,408,471,496,506,534`: binding bền bằng file, start/status/reconcile/events, tải tuần tự; `m2/tai_hoa_don/tien_trinh.py:70,197`: sở hữu/dừng Node. `giao_dien/m2_tai_hoa_don.py:158,213`: queue tải tất cả trong RAM. | Tái dùng **mẫu** G5 về lease/thế hệ/CAS, kiểm quyền lại; bọc vòng đời/tiến độ/dừng M2. G5 gắn CRM, M2 gắn phiên/profile/file và queue RAM; chưa là bảng việc PG dùng chung. Thiếu schema việc chung, engine+version, tiến độ, yêu cầu dừng hợp tác, retry có lịch, nhật ký, đối soát kết quả chưa rõ. Không chuyển việc đang chạy sang queue mới. |
| **XS-3 · Engine** | `ha_tang/cong_ocr.py:127,339`: cổng OCR; `tri_thuc/cong_ai.py:275,305,979,1236`: DTO và cổng AI; `nguon/trich_chung_6.py:38,117,536,662,817`: common/v1, khóa yêu cầu/hash, trích dẫn; `m4/review_compute.py:1`: compute tiến trình con, không PG; XML reader `nguon/hoa_don_xml.py:1183,1191`. Có test riêng, ví dụ `T/test_cong_ocr.py:49`, `T/test_cong_ai.py:271`, `T/test_m4_review_compute.py:221`. | Bọc code đã có; giữ raw, hash, coverage/trích dẫn và mã lỗi cũ. Chưa thấy danh bạ engine thống nhất, hợp đồng trạng thái chung và bộ test mẫu chạy độc lập cho hai đường gọi. `de_xuat/engine.py:30` là engine nghiệp vụ hiện hữu, không phải danh bạ chung. M2 orchestration giữ quyền/phiên ở module; không đưa nguyên lớp đọc/ghi module vào engine. |
| **XS-4 · Module/công tắc/MTQ** | `giao_dien/khung_khai_bao.py:42,98,132,176`: khai báo **CRM**, adapter quyền/đếm, route chỉ CRM; `tam_dung=False` ở `:44`. `ha_tang/pg_migrations.py:1236`: quyền người × pháp nhân × module, chưa phải chế độ vận hành. MTQ `_CATALOG` cố định: `k2/sql_ma_tran_tham_quyen.py:30,75`; validator Python nhập catalog ở `k2/ma_tran_tham_quyen.py:21`, trả catalog PG ở `:264`. UI còn whitelist nhãn ở `giao_dien/assets/ma_tran_tham_quyen.js:14,99`. | Giữ adapter quyền/đếm và các resolver MTQ máy chủ. Thiếu khai báo chung mọi module, engine/sự kiện/dữ liệu công bố, metadata màn/hành động; trạng thái bền **module × pháp nhân** Tắt/Thử/Vận hành; guard cả HTTP lẫn worker. MTQ phải sinh cột từ khai báo đã kiểm, không tự cấp quyền. Cần catalog phiên bản mới; không đổi `_CATALOG` đang tạo migration cũ. |

## 2. Chuỗi lát đề xuất (mỗi hàng là một lát, tối đa 3 tệp)

Tên tệp mới là đề xuất để lead lập handoff. Viết tắt: `H/` = `ha_tang/`, `K/` = `k2/`, `G/` = `giao_dien/`, `A/` = `giao_dien/assets/`, `P` = `H/pg_migrations.py`, `T/` như trên. Mọi lát SQL khai báo **migration mới `M00xx_*`**, nối cuối `PG_MIGRATIONS`; lead đánh số lúc gộp, không sửa migration đã có. Cột tệp liệt kê đủ cả test; dấu **★** là tệp dùng chung cần lead xếp lịch gộp.

| Lát | Kết quả / tiêu chí test chính | Tệp (đề xuất) | Phụ thuộc |
|---|---|---|---|
| XS-1a | SQL outbox/inbox, phân pháp nhân, unique/replay, rollback không phát | `K/sql_bus_su_kien.py`; **P★**; `T/test_xs1_sql.py` | — |
| XS-1b | Phát/nhận/ACK, nhận lại không nhân đôi; hai bên nhận độc lập | `H/bus_su_kien.py`; `T/test_xs1_bus.py` | 1a |
| XS-3a | Hợp đồng + registry mã/version; mẫu xong/chờ/lỗi có mã, bằng chứng; từ chối trùng/khác version | `H/engine.py`; `H/danh_ba_engine.py`; `T/test_xs3_engine.py` | — |
| XS-4a | Tách dữ liệu khai báo thuần dùng cho mọi module; giữ adapter CRM và kết quả cũ | `H/khai_bao_module.py`; **`G/khung_khai_bao.py`★**; `T/test_xs4_khai_bao.py` | 3a |
| XS-4b | SQL công tắc × pháp nhân, revision/audit; catalog MTQ mới từ khai báo, giữ bản cũ | `K/sql_module.py`; **P★**; `T/test_xs4_sql.py` | 4a |
| XS-4c | Dịch vụ công tắc/khung chung; guard HTTP theo PN máy chủ; không nhận actor/PN tự khai | `K/module.py`; **`G/server.py`★**; `T/test_xs4_http.py` | 4b |
| XS-2a | SQL bảng việc/lease/CAS/tiến độ/dừng/retry/audit, chống claim trùng | `K/sql_hang_viec.py`; **P★**; `T/test_xs2_sql.py` | 1a, 3a, 4b |
| XS-2b | Worker chung, phục hồi lease, dừng hợp tác; module tắt không nhận việc mới | `H/hang_viec.py`; `H/chay_engine.py`; `T/test_xs2_worker.py` | 1b, 2a, 3a, 4c |
| XS-3b | Bọc OCR/AI qua cổng có sẵn; mẫu giả không ABBYY/mạng; bảo toàn kết quả và lỗi gốc | `H/engine_cong.py`; `H/danh_ba_engine.py`; `T/test_xs3_cong.py` | 3a |
| XS-3c | API nội bộ → queue; Python/API dùng cùng hợp đồng; kiểm quyền, version, replay | `G/engine.py`; **`G/server.py`★**; `T/test_xs3_http.py` | 2b, 3b, 4c |
| XS-4d | Validator/đọc metadata MTQ theo catalog phiên bản đã công bố; bản cũ vẫn đọc được | `K/ma_tran_tham_quyen.py`; `T/test_xs4_mtq.py` | 4b; MTQ-4 hiện hành |
| XS-4e | UI MTQ lấy tên/cột/hành động từ metadata; không whitelist chặn module mới | `A/ma_tran_tham_quyen.js`; `T/xs4_mtq.cjs` | 4d |
| XS-4f | Khung/icon/chế độ theo khai báo và PN, bảo toàn barrier đổi vai | **`A/app.js`★**; `A/index.html`; `T/xs4_khung.cjs` | 4c |
| XS-T1a | Hợp đồng dữ liệu hóa đơn công bố chỉ đọc (version/hash/PN), không mở quyền bảng M2 | `K/sql_cong_bo_hoa_don.py`; **P★**; `T/test_xst1_cong_bo.py` | 1b, 4c |
| XS-T1b | Hook phát trong giao dịch nhận M2; consumer M4 + ACK cùng giao dịch, replay không trùng | `K/hoa_don.py`; `m4/nhan_su_kien.py`; `T/test_xst1_bus_pg.py` | T1a, 2b |
| XS-T1c | Nối consumer M4 vào worker; trả chờ khi thiếu hóa đơn, đọc qua hợp đồng công bố | `G/m4.py`; `m4/ghi_nhan_nghiem_thu.py`; `T/test_xst1_http.py` | T1b |
| XS-T1d | Màn M4 hiện “Chờ hóa đơn M2”; bật lại cập nhật, không mất nội dung khi đổi vai | `m4/giao_dien/m4_ke_toan.js`; `T/xst1_cho.cjs` | T1c, 4f |
| XS-3d | Bọc reader E-HOADON, mẫu XML/ZIP độc lập | `H/engine_hoa_don.py`; `H/danh_ba_engine.py`; `T/test_xs3_hoa_don.py` | 3a |
| XS-3e | Cắm cùng E-HOADON vào M2 rồi M3; cùng input → cùng kết quả/bằng chứng | `K/hoa_don.py`; `K/m3.py`; `T/test_xs3_tai_dung.py` | 3d; sau T1b |

Thứ tự ưu tiên: 1a→1b; 3a→4a→4b→4c; hợp hai nhánh vào 2a→2b; rồi pilot T1a…d. 3b→3c và 4d→4e hoàn tất trước báo XS-1…4 xong. 3d→3e là bằng chứng cắm lại engine vào module thứ hai, không tính registry hay mock caller là đã cắm. Các engine khác chỉ bọc khi chạm tới theo TL 53 §6; mỗi engine giao lát riêng ≤3 tệp, không gom viết lại. Không sửa `TRANG-THAI.md` trong KK-XS; lead cập nhật danh bạ khi gộp.

## 3. Thử nghiệm đầu tiên: M2 tắt, M4 vẫn chạy và hiện chờ

**Đề xuất XS-T1a…d**, dùng hai pháp nhân giả A/B trên PG DEMO khi lead giao code/test. Cặp này có seam thật: `k2/ghi_nhan_chung.py:1,292` đã đối chiếu NT ↔ hóa đơn, thiếu có `THIEU_HOA_DON`/`CHO_MAPPING_M2`; `giao_dien/m4.py:370` ghép dữ liệu và `m4/giao_dien/m4_ke_toan.js:534` có nhãn thiếu. M2 có giao dịch nhận tại `k2/hoa_don.py:390,428`; hook outbox đặt trước commit trên **chính kết nối đó**, không phát sau khi trả HTTP.

1. M2 A=Tắt, M4 A=Thử, chưa có hóa đơn công bố: M4 vẫn mở/kiểm hồ sơ độc lập, phần cần hóa đơn trả `chờ` + lý do và hiện “Chờ hóa đơn M2”; không suy số, không gọi dịch vụ M2. M2 B không bị tắt theo A.
2. Bật M2 A=Thử, nhận XML giả → công bố snapshot + outbox. Tắt M4 trước nhận: event vẫn ở PG qua restart worker. Bật M4 → nhận, ACK, gửi lại cùng event không thêm kết quả. Lỗi giữa ghi kết quả và ACK phải rollback cả hai. Hai consumer/worker tranh nhận không nhân đôi.
3. Chỉ hết **lý do chờ hóa đơn** khi có dữ liệu hợp lệ; không tự ghép/duyệt/ghi sổ. Giữ `CHO_CAN_CU_GHI_NHAN`, `UNPROVEN_NO_MINOR`, quyền và các điều kiện khác của 03B. Dữ liệu đã công bố vẫn đọc được khi M2 tắt, nếu người dùng đủ quyền; tắt module không xóa bằng chứng. Ca mất quyền/khác PN phải bị chặn, không giả thành “chờ”.

Đây là pilot độc lập module, không đủ riêng nó để báo XS-1…4 hoàn tất; cần đủ các lát nền, hai đường gọi engine và MTQ từ khai báo. Không chạy pilot hay mở PG/server trong lần kiểm kê này.

## 4. Danh bạ engine ban đầu đề xuất

**Phiên bản wrapper đề xuất `v1-dự-thảo` cho cả 8 engine**, chưa đăng ký/chưa đạt test hợp đồng chung; không đồng nhất với version code gốc. “Module dùng” phân biệt đường mã đã thấy và đích TL 53. Test hiện có chỉ là nguồn mẫu, **chưa chạy trong lần này**.

| Mã / version | Vào → ra; bằng chứng | Trạng thái, nguồn mã/test | Module dùng |
|---|---|---|---|
| **E-OCR / v1-dự-thảo** | PDF/ảnh bytes + định dạng → DOCX; hash gốc/kết quả, mã việc | Có cổng, cache SHA, hủy/hạn mức; chưa envelope engine. `ha_tang/cong_ocr.py:339`; `T/test_cong_ocr.py:49`. Không khai đã có text/bảng riêng. | Đã nối M9: `m9/ocr_hot_folder.py:19`; đích M4, CRM |
| **E-AI / v1-dự-thảo** | `YeuCauAI` → `KetQuaAI`, trường/trích dẫn nguyên văn, nguồn Local/Cloud, mã yêu cầu/lý do | Có cổng, chưa wrapper; `tri_thuc/cong_ai.py:275,305,1236`; `T/test_cong_ai.py:271`. Local luôn có; Cloud chỉ Mask v2, M9 chỉ Local. | Đã dùng M9: `m9/hoi_dap_vay.py:40`; đích mọi engine dùng AI |
| **E-TRICH / v1-dự-thảo** | bytes + loại/catalog/hash + mã tham số/request → tham số/trạng thái/trích dẫn/vị trí/raw hash | Có common/v1 và projection-v1 (`nguon/trich_chung_6.py:38,40,536,817`); không tự coi mọi catalog E1 là đã được client hỗ trợ. Mẫu E1: `T/test_e1_mua_trich_phien_ban.py:14`. | CRM/#6 có adapter; đích CRM, M2, M4 |
| **E-RAG / v1-dự-thảo** | Tài liệu được phép + câu hỏi → câu trả lời/trích dẫn file/trang/điều/mã đoạn, trạng thái | Có BM25 bộ nhớ (`m9/chi_muc_vay.py:95,134`) và hỏi đáp (`m9/dich_vu_hoi_dap.py:10`); chưa engine chung/lưu chỉ mục PG. Mẫu `T/test_m9_chi_muc_vay.py`. Caller phải lọc quyền trước. | M9; sau tái dùng kho văn bản |
| **E-SHEETS / v1-dự-thảo** | Hiện có values + mapping + giờ/nguồn → snapshot, lỗi dòng, SHA; đích kéo API chỉ đọc → snapshot | **Mới một phần:** `m9/snapshot_sheet.py:1,142` không kéo API/ghi dữ liệu. Mẫu `T/test_m9_snapshot_sheet.py`. Chưa chứng minh connector hay tài khoản/Sheet thật. | M9-3 |
| **E-HOADON / v1-dự-thảo** | XML/ZIP + context → kết quả hóa đơn/coverage/lỗi/locator/hash; nhánh tải → artifact/manifest/trạng thái | Reader có: `nguon/hoa_don_xml.py:542,1183,1191`, `T/test_hoa_don_xml.py`; tải có M2-00 (`m2/tai_hoa_don/dieu_phoi.py:408`). Nhánh tải chưa tách khỏi phiên/quyền module; wrapper không tự truy cập bảng M2. | M2 hiện có; đích M3, M8 |
| **E-MOC / v1-dự-thảo** | Snapshot mốc dự kiến/thực tế + lớp/mốc áp dụng → đề xuất chuyển lớp hoặc chờ, kèm ID/version/ngày làm căn cứ | Có lưu/lịch sử/trạng thái mốc: `k2/sql_crm_du_an_moc.py:18,29,183`; chưa thấy engine chuyển lớp độc lập. Mẫu `T/test_crm_du_an_moc.py`. Không bọc nguyên SQL đọc bảng CRM thành engine. | CRM hiện quản mốc; đích CRM, M3 |
| **E-KIEMTRA-DOT / v1-dự-thảo** | Snapshot căn cứ + XLSX/tệp hồ sơ + pin → findings, coverage, báo cáo/hash/vị trí | Có compute bọc thuật toán review (`m4/review_compute.py:1,31`), mẫu `T/test_m4_review_compute.py:221`; nhánh L3 ở `:11`. Phải kiểm đủ phạm vi K/B/C/P theo nguồn trước đăng ký đủ năng lực. | M4 |

Envelope chung dự kiến: mã/version, request/idempotency key, input hash → `xong/chờ/lỗi`, kết quả, bằng chứng, lý do chờ hoặc mã lỗi; giữ trạng thái nghiệp vụ gốc bên trong. Engine nhận snapshot/bytes đã được cấp quyền, **không tự đọc/ghi bảng module**. Cùng bộ mẫu giả kiểm Python trực tiếp và API nội bộ/queue, không chỉ kiểm shape DTO.

## 5. Rủi ro và điều kiện giữ hành vi

- Giao nhận tối thiểu một lần + inbox/idempotency, không hứa “exactly once” cho tác động ngoài PG. Hết lease chưa chứng minh job tải/trích đã dừng; giữ UNKNOWN/chưa rõ, đối soát trước retry. Giữ binding/session/profile của M2 và CAS/thế hệ của G5.
- Công tắc mặc định phải bảo toàn module cũ; module mới chưa khai/bật không tự hoạt động. Tắt chặn nhận việc mới, không kill việc cũ/mất kết quả; chính sách hoàn tất/thu hồi quyền cần lead chốt. Thử không được tự mở đường ghi vận hành. Không thay quyền bằng công tắc hay mở quyền vì sinh thêm cột MTQ.
- Migration chỉ append, giữ catalog lịch sử; lead nối tuần tự các lát đụng P/server/khung/app và tránh xung đột MTQ-4, CD-016 đang chạy. Không đổi thuật toán, ngưỡng, dữ liệu gốc hay kết quả cũ khi bọc engine; hạn mức/khóa sổ OCR hiện hữu vẫn có giới hạn với Review cũ (`ha_tang/cong_ocr.py:8`).
- Lát code chạy test mẫu + hồi quy phần chạm; PG integration trên DEMO do lead bố trí, không dùng dữ liệu thật. “Xanh” theo `NEN-TEST.md` §0 v4 (1501 đạt, 23 ERROR, 44 FAIL, 362 skip): so **mã lỗi**, không thêm lỗi/treo/lỗi nạp; không coi thiếu môi trường là đã đạt. KK-XS chỉ kiểm tài liệu, không có kết quả test sản phẩm mới.

## 6. Cần lead

1. Chốt schema/tên bảng bus/việc/công tắc và đánh số `M00xx_*`; cấp danh sách tệp từng handoff ≤3, thứ tự gộp tệp chung, nền test hiện hành sau các lát đang chạy.
2. Chốt quyền đổi công tắc, mặc định/backfill bảo toàn hiện trạng; nghĩa chính xác của **Thử**, cách chuyển chế độ khi còn việc đang chạy, quan hệ với MTQ-4 readiness và catalog phiên bản cũ. Không worker nào tự bật vận hành.
3. Duyệt cặp pilot M2→M4, sự kiện/version/khóa dedupe, hợp đồng hóa đơn công bố và nơi lưu kết quả nhận; cấp PG DEMO/lệnh kiểm thử khi giao code. Sau pilot, rà từng seam cũ khi chạm tới; chưa tuyên bố mọi module đã hết gọi trực tiếp nhau.
4. Chốt version/năng lực thực được đăng ký từng engine (nhất là catalog E1, phạm vi C/P review, E-MOC); xác nhận reuse E-HOADON M2→M3. E-SHEETS còn thiếu connector/thông tin Sheet; không đọc bí mật để lấp chỗ trống. Lead ghi engine/version/module/test vào `TRANG-THAI.md` và chỉ báo Anh theo đủ điều kiện CD-017.
