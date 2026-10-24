# Review độc lập khởi động CRM — lượt 05

Ngày 19/10/2026. Reviewer `/root/m1_recheck03` không sửa product. Lượt này đọc actual evidence do root chạy sau release; không chạy lại product, test, SQL hoặc host, không đọc credentials.

**Kết luận:** phần pure/stub có 40 PASS, 1 sai khác mã lỗi B05 và 1 NOT_VERIFIED PowerShell; không có SETUP_ERROR hoặc functional/security FAIL trong các ca đã chọn. Đề nghị root chấp nhận B05 như compatibility deviation có ghi nhận, giữ nguyên raw FAIL và expected cũ. Chưa nghiệm thu launcher/host/GUI từ kết quả này.

## Căn cứ cố định

Các đường dẫn dưới đây tính từ repository `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức`.

| Artifact | SHA256 |
|---|---|
| `var/codex-dieu-phoi/crm-launcher-recheck05/pure-run-1792376889168763300/result.json` | `5af368b802b4b8b95396f055a29695ff1154909d0befe64a2c659ecd5f7e2cc0` |
| `var/codex-dieu-phoi/crm-launcher-recheck05/binding-release.json` | `706c84d4c6287f7ad871d75af7cc18d86ab3bd5d6c98cbf631e7a893dd1ac75f` |
| `binding_final_32050.py` trong cùng thư mục recheck05 | `03cd8db2bb58e2c7fd277455941c74c42465df30e187d8530fa05657d41ff1f2` |
| `run_pure05.py` | `f01c65af3b8d676fc50ba3922c26428099d44be6af520f200413ad734440b2b8` |
| `gate_preflight05.py` | `4fc016cbabc9ff5daf96b6a3bd54fce7abfae510f23f268461cc94820a6c3756` |
| `original-28-expectations.json` | `e4f1a33ba8df43c0332e8e05131cacb268836e3412498de10581729a4e361fb6` |
| `new-chain-runtime-expectations.json` | `3079df752e86effd1f278caeb8dd0addf7bf047ccc3712bdbc6a2ccd4836efa2` |

Authoritative receipt: `var/codex-dieu-phoi/kiem-chung-20261018-101441/crm05-handoff-20261019-091858-019/terminal-confirmation.json`, handle 32050, exit 0, product execution true, host execution false. Manifest cùng thư mục SHA `b9bd8c6dd61af2df17ebc5ab4257681bd28caafdee7654406a6a015f835fde82`, 125 file. Guard SHA `a517c5359ceada062900edd34280d4dc7daa2a001d5e05c84a9eae174813a229`. Root release ghi `ROOT_COORDINATOR`, `final_api_reviewed=true`, `mode=pure`.

`result.json#/before` và `/after` đều kiểm 125 file, cùng manifest; `/source_unchanged=true`. Các cờ `product_imported=false` bên trong before/after mô tả riêng preflight; binding thực tế có import và gọi API product qua stub, không phải một lượt chỉ đọc.

## Actual facts và đánh giá

| Nhóm | Actual facts đã đối chiếu | Đánh giá |
|---|---|---|
| Original28 | 27 PASS, B05 strict FAIL; 0 SETUP_ERROR | Expected/id/kind cũ giữ nguyên |
| B05 remote hostaddr | `outcome=REJECTED`, actual `KET_NOI_KHOA_KHONG_HO_TRO`; expected `KET_NOI_KHONG_LOCAL` | Semantic denial đạt; compatibility discrepancy |
| E01/E02/E03 | Thiếu endpoint: `KET_NOI_THIEU_ENDPOINT`; service-only: `KET_NOI_KHOA_KHONG_HO_TRO` | Fail closed, không nhận endpoint kế thừa |
| C04; D02–D05 | Port khác: `KET_NOI_KHAC_ENDPOINT`; remote admin/app: `KET_NOI_KHONG_LOCAL`; DB khác: `KET_NOI_KHAC_DB`. Cả bốn D negative có connector/seed/schema/query đều 0 | Reject trước mutation/seed, không phải lỗi sau kết nối |
| D01 positive | `SAN_SANG`, 2 connector, 1 seed, 2 schema, 5 query stub; hai đích explicit loopback/5432/cùng DB fixture | Positive control đi đến đủ bước stub |
| S01/S02/S03 | Không cấu hình/remote/nonDEMO đều reject; connector 0 | Server validation trước connector |
| R01–R04 | Ordinary member được nhận; superuser/BYPASSRLS/nonmember bị `ROLE_UNG_DUNG_SAI` | Chỉ chứng minh logic nhận metadata stub; không xác minh login/ownership SQL thật |

**B05:** source frozen `src/kho_tri_thuc/k2/crm_khoi_dong.py:74` từ chối `hostaddr` không khớp literal loopback trong `chuan_hoa_dsn`, trước các connector của `chuan_bi` (`:146`). Actual denial cùng global `blocked_external_api_attempts=0` phù hợp với boundary này. Không có bằng chứng network escape hay mutation. Static search toàn bộ frozen125 không thấy consumer production rẽ nhánh theo hai mã lỗi này ngoài chỗ phát sinh lỗi; các tham chiếu khác là test. Đề nghị chấp nhận deviation cho phạm vi hiện tại, giữ raw expected/FAIL và ghi mapping khi duy trì contract lỗi; không yêu cầu một lượt sửa chỉ để đổi nhãn. Kết luận này không xác nhận contract của consumer ngoài frozen125.

**N01 normalization:** cả ba đầu vào 127.0.0.1 / localhost / ::1 có `first == second`; hai đầu tiên hostaddr 127.0.0.1, đầu cuối ::1, đều port 5432 và cùng DB fixture. Binding `:237` truyền PGHOST/PGHOSTADDR/PGPORT/PGSERVICE bất lợi nhưng normalized target không đổi. Chứng minh idempotency của API thật, không chỉ kiểm output tự dựng.

**N02 JSON → bootstrap:** binding `:246` gọi `doc_ket_noi` thật, chuyển nguyên kết quả sang `chuan_bi` thật, rồi ghi lại normalized strings vào JSON bộ nhớ và lặp chain. Actual: hai `SAN_SANG`, `normalized_equal=true`, 4 connector, 2 seed, 4 schema, 10 query stub. Cả bốn target đều host=hostaddr=127.0.0.1, port=5432, cùng DB fixture. Normalizer/pair validation không bị mock; JSON file, connector, schema/seed và query response được stub. Đây là bằng chứng sửa được chain từng lỗi `KET_NOI_KHOA_KHONG_HO_TRO` sau JSON normalization; chưa chứng minh migration/seed thật hoặc persistence idempotent.

**N03 env → server:** raw DSN và normalized DSN đều qua `LocalApp.crm` thật (`server.py:175`, `_crm_ket_noi:207`), mỗi ca đến đúng 1 connector cùng target và nhận service. `actual.db=null` là trường tóm tắt không lấy DB từ đối tượng CrmK2, không phải NULL DB trong kết nối; target metadata ghi rõ cùng DB fixture. CrmK2 constructor và validation chạy với fake connection/dumper adapters; chưa có HTTP request.

**RUNTIME01–04:** resolver `tools/chon_runtime.py:125` và environment builder `:74` là API thật; file metadata, JSON và probe process được stub (`binding:268`). Default chọn `nguon=runtime_local`, override chọn `tuong_minh`; mỗi ca chỉ 1 argv probe với đường dẫn có dấu cách được giữ thành một phần tử. PYTHONPATH đúng thứ tự src/deps/guard, không giữ PYTHONPATH riêng của caller; no-bytecode=UTF8=1, biến unrelated giữ nguyên và parent map không đổi. Missing driver trả `ok_app=true, crm=false, RUNTIME_THIEU_DRIVER`; isolated trả `ok_app=true, crm=false, RUNTIME_ISOLATED`, không đổi ứng viên. Chứng minh resolver xử lý probe response và dựng child environment; probe thật và quyết định bootstrap/server của PowerShell chưa chạy trong lượt này.

**RUNTIME05:** phần Python environment PASS; status tổng vẫn NOT_VERIFIED. Quan sát static có Set/Restore và cùng selected executable ở bootstrap/server không chứng minh child inheritance hoặc parent restoration trên PowerShell thật.

**Cluster6:** `bao_dam_cum` thật (`ha_tang/pg_cum.py:228`) nhận OS/metadata/lock/log stub. CL01 reuse: 1 status, 0 start. CL02 stopped/free: 2 status, đúng 1 start. CL03 status4 → `CUM_KHONG_TRUY_CAP`, CL04 port occupied → `CUM_CONG_BI_CHIEM`, CL05 wrong owner executable → `CUM_KHONG_XAC_MINH`; mỗi ca 0 start. CL06 start trả -1 nhưng recheck nhận đúng process: 2 status, 1 start, `DA_KHOI_DONG`; không respawn. Captured argv không có stop/kill/initdb/register/restart/delete. Vì khóa được thay bằng nullcontext, không suy ra file lock, concurrency hai process, binary hash hoặc OS ownership thật đã đạt.

## Giới hạn nghiệm thu

Raw result ghi 0 real network, SQL, launcher/cluster actions, credential-file reads/creates và 0 blocked external attempts; `cleanup_performed=false`. Root xác nhận process exit 1 do strict B05, phù hợp runner giữ exact-code predicate; không đổi thành báo toàn bộ PASS.

Chưa kiểm chứng ở đây: clean default NoBrowser first/reopen, actual app dependencies/guard import dưới child runtime, PowerShell environment restore, web-process restart giữ cùng endpoint/DB, ordinary nonowner login SQL, cluster thật/locks/concurrency, cold host, HTTP negative, GUI hoặc toàn bộ M1. Cold host chỉ thực hiện khi tự nhiên quan sát đúng cluster đã dừng; không dừng PG để tạo ca. Root bổ sung bằng chứng host riêng. Không đọc hoặc sao chép secret config vào review.
