# Review độc lập CRM host 06 — đạt phạm vi khởi động và lưu giữ DEMO đã kiểm

19/10/2026. Reviewer `/root/m1_recheck03` đọc artifact root thực thi và đọc XLSX bằng .NET ZIP/XML; không chạy product, test, HTTP, SQL, launcher hoặc process action, không đọc credentials. Kết luận áp dụng cho **freeze06 handle51883**, không áp dụng cho source M9 đang được sửa sau đó.

**Chấp nhận phạm vi đã kiểm:** machine JSON qua Windows PowerShell5.1, default CMD mở app, reopen dùng lại process, workflow DEMO KT→CFO→export/download, khôi phục bốn biến caller và giữ nguyên dữ liệu/file sau owned web-process restart. Không nghiệm thu toàn CRM/M1 hoặc mục tiêu toàn33 từ các ca này.

## Căn cứ và actual facts

Đường dẫn tính từ repository `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức`; viết tắt **R06** = `var/codex-dieu-phoi/crm-launcher-recheck06/`.

Authoritative terminal51883 exit0, frozen125 manifest SHA `c828d1fff9593a0dce6d47e079df8adf76a4609cb936e2f1a627cf1a9948dd08`. Chỉ hai tool stdout và test liên quan khác05; schema/start-web/server/CRM không đổi trong lượt06. Root release after ghi `ROOT_COORDINATOR`, host/root-only/final-api true, count125, đúng observer rev3 SHA `641872a66a26cd965ae4bb71103d7eb23ef4a9323c8871d584203b7a9990e46b`, baseline SHA đúng first PASS. Cả hai lượt observer kiểm125 trước/sau và báo source unchanged. Đây là kiểm ở thời điểm freeze06, không kiểm source interim M9.

| Hạng mục | Actual evidence đã đối chiếu | Kết luận |
|---|---|---|
| Windows5.1 transport | `R06/windows-ps-encoding-after-20261019-095241-617.json`: PS5.1.26100.9711, Console437/pipeline20127, crm=true, decoded pythonpath bằng expected; decoded3/3 và expected3/3 path tồn tại; probe không SQL/server | PASS; before05 decoded0/3 được giữ trong REVIEW-CRM-HOST-05 |
| Default CMD first | `var/codex-dieu-phoi/crm-launcher-host06-first-20261019-095315-430/launch-result.json`: default_cmd=true, no_python_override=true, private_python_env_cleared=true; health PID26276/root var/web; stdout xác nhận schema12, PostgreSQL DUNG_LAI | PASS server readiness/bootstrapping; artifact first ghi CMD chưa exit, không suy diễn first CMD exit0 |
| Default CMD reopen | `.../crm-launcher-host06-reopen-20261019-095508-265/reopen-result.json`: exit0, cùng PID26276/started_at1792378399/root; private env cleared, không Python override | PASS reuse; không tạo server khác |
| Workflow HTTP thật | `R06/host-http-first-51883/result.json`:17/17 HTTP200, gồm nhận mẫu/KT kiểm/đổi MO identity/CFO duyệt/xuất/download; workflow=ACTUAL_KT_CHECK_AND_CFO_APPROVAL, export_action=ACTUAL_HTTP_EXPORT | Workflow đã chạy; overall FAIL là lỗi typed assertion của harness, giữ raw FAIL |
| Baseline rev3 | `R06/host-http-first-rev3-51883/result.json`: PASS;9 GET/0 POST, REUSED_ALREADY_APPROVED_NO_REAPPROVAL, REUSED_EXISTING | Không nhận/duyệt/xuất lại để làm xanh |
| Owned restart | `R06/owned-shutdown-before-restart-1792378613072149100.json` accepted, cùng health26276; `owned-web-os-absence-26276.json` xác nhận OS process vắng; PostgreSQL không stop | Có restart thực, không chỉ tạo đối tượng mới trong test |
| PowerShell thực và caller restore | `R06/actual-ps-env-restore-20261019-095707-419.json`: launcher_error_type=null, PID mới17108/started_at1792378632/cùng root; private_userbase_absent=true, no override; PYTHONPATH/PYTHONUTF8/PYTHONDONTWRITEBYTECODE/sentinel đều restore; Console437→437 | PASS cho bốn biến được đo và Console encoding |
| Sau restart | `R06/host-http-after-rev3-51883/result.json`: PASS;8 GET/0 POST, cookie mới, cùng toàn snapshot; PID/started_at khác baseline | PASS lưu giữ dữ liệu/export trong phạm vi snapshot |

Lỗi harness cũ so UUID `ho_so.id` với enum `pb.nguon`; frozen `k2/crm.py:231` tạo `TRICH_6`/`BAN_HANG`, API trả enum này. Rev3 kiểm `nguon=TRICH_6` và đúng một envelope PN_DEMO_A/GOC/mã HĐ/namespace/loại hình/Word DEMO đã biết; lưu actual source ID/hash/envelope. Các expected tiền, hạn, workbook và workflow giữ nguyên. Không sửa product hoặc coi enum là source FK. Initial500 do retention boundary và failure transport05 vẫn giữ trong báo cáo05.

## Đối chiếu dữ liệu và file độc lập

Reviewer so toàn snapshot JSON first/after: giống hệt. Cùng contract/PB/source/export ID; cùng các ID sets theo quyền KT:1 hồ sơ,1 HĐ,1 PB,3 lịch,1 export,0 tiền; số ID duy nhất bằng số dòng từng nhóm. Không thêm bản trùng trong các tập quan sát sau restart. Trạng thái HĐ HIEU_LUC/PB DA_DUYET/V4 DA_DUYET, KT=`MO_PHONG_KT_A`, CFO=`MO_PHONG_CFO` được giữ.

Source hash cùng `e68ad2564ff8feaeb49a646ad167d046a1fa77bc08aac8538e4757306a5c8ff3`. Profile `DT-KCN-THUE-DAT-DEMO` v2/hash `ec1d4b62f63ede6f77e257eca4463a425aeda9e62272581f374d9459d334a380`;11 tham số, canonical parameters SHA `1f28c1698547b3f4f00a1438386118dc28730d0702b8f1582cdf564a48ec9dd3`; source envelope và profile/parameter digest giống nhau sau restart.

Hai file `downloaded-DEMO-CRM.xlsx` thực tải ở first-rev3 và after-rev3 đều9161 bytes, SHA `f1d4ba770b4a17cdda303d35302d40da75e0a5bb11f122a2e9913f9f55ed78b8`. Snapshot cells SHA cùng `56f7d3fcc7cf72f9ea7e6538d97a7eaa4bbc8ae7471d5e005a1afa3703e54d17`. Reviewer kiểm hash cả hai file và đọc ZIP/XML độc lập: đúng4 sheet;3 dòng lịch với số tiền300m/1.2b/1.5b VND;0 formula; ô HĐ/PN/GOC v1/DA_DUYET/KT/CFO/profile v2 khớp expected. Không dựa riêng vào bool PASS của observer.

## Hash các bằng chứng chính

| Artifact | SHA256 |
|---|---|
| Windows encoding after | `246ec3b045e15aedf93b2ccd04d2e609c46a2562513714694f8130413178dcbf` |
| Default first launch-result | `66abbcb6759c6e7f794a6f73cfcb1fca07deca7a41592a6bebbb4c8161e5615c` |
| Default reopen-result | `e9ea78be1ce26ece451fa1da905acc13395492b5c2a4969ea492c7732941ff13` |
| Initial workflow/harness FAIL | `725fb0d379d7fb5a38e00d6a3f87d439115e58e7ba7abb7e8a18c11924e79b3d` |
| Rev3 first PASS | `b307e6fbfcf8229043261af2ebcd5ca081d3a44f04ded691b714b3dcad0821c7` |
| Rev3 after PASS | `0d5569fe93493527514b6e432eadbf897d25cd215d96f3cb746cd85e23ce98b6` |
| OS absence26276 | `c13704e6951b54bf0df3e3e658b46e6e2bd3b6ad05a8b881e57cd9eb50d4d970` |
| Actual PS caller restore | `26208915ccfcccf7989c21d1b8abc0cf73c640dc67f4f33ddab90b826ba4188a` |

## Giới hạn còn giữ

DB provenance FK: **NOT_VERIFIED qua HTTP** vì API không trả PB.chung_tu_id; source envelope match và source ID ổn định không chứng minh FK đó. Không gộp phạm vi SQL03 trước đây vào chứng minh HTTP này. Không kiểm đầy đủ RLS/atomicity/domain/corpus trong lượt06.

GUI, cold cluster và two-process cluster-lock/concurrency: **NOT_RUN**; không stop PostgreSQL tạo cold case. Full M1/G10 protected approval/period: **NOT_VERIFIED**, không suy ra từ workflow CRM. Không tuyên bố nghiệm thu toàn CRM hoặc toàn33 module/receiver. B05 vẫn là compatibility deviation đã root chấp nhận trong review05, không bị đổi raw expected/FAIL.

Readiness ở trên là kết quả dưới freeze06 tại thời điểm kiểm. Root báo đã shutdown PID17108 và xác nhận OS absent trước khi dispatch M9 handle88862; không tuyên bố app hiện đang chạy hoặc M9 đã nghiệm thu. Giữ file/DB/role/evidence, không xóa hoặc reset.
